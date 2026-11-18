"""CPU contracts for the shared near-throat H/V block in the rolled family."""
import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import load_config
from hornlab_search.design import throat_hv
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generators import rolled_family as rf
from hornlab_search.design.generators.registry import GeneratorError


@pytest.fixture(params=['rect', 'section'])
def family(request):
    cfg = load_config(REPO / 'examples/typologies/rolled_family_2026-11-15' /
                      f'rf__{request.param}_radial_v7.yaml')
    return DesignSpace.from_config(cfg)


def resolve(space, knobs=None):
    if knobs is None:
        block = space.seed.params['grid']
    else:
        block = rf.design_params(space.gen, knobs, space.brief)['grid']
    return rf.resolve_grid(block, space.brief)


def neutral(space):
    knobs = dict(space.seed_knobs)
    knobs['g_inward_h_mm'] = knobs['g_inward_v_mm'] = 0.0
    return knobs


def with_onset(space, onset):
    knobs = dict(space.seed_knobs)
    del knobs['g_relief_start_s']
    knobs['g_hv_onset_frac'] = onset
    return knobs


def test_absent_keys_leave_geometry_meta_and_knobs_unchanged(family):
    assert not any(('g_'+k) in family.seed_knobs for k in throat_hv.KEYS)
    assert throat_hv.is_active(rf._throat_knobs(family.seed_knobs)) is False
    treated = resolve(family)
    assert 'throat_hv' not in treated['meta']
    assert throat_hv.STATUS['rolled'] not in treated['meta'].get('notes', [])
    # Neutral ratio is the identity: an explicit 1.0 must not change any point.
    knobs = dict(family.seed_knobs, g_throat_hv_ratio=1.0)
    explicit = resolve(family, knobs)
    np.testing.assert_array_equal(explicit['inner_points'], treated['inner_points'])
    np.testing.assert_array_equal(explicit['outer_points'], treated['outer_points'])
    assert 'throat_hv' not in explicit['meta']


def test_onset_half_leaves_stations_before_it_undeformed(family):
    parent = resolve(family, neutral(family))
    treated = resolve(family, with_onset(family, 0.5))
    station = np.array(treated['meta']['stations'])
    before = station < 0.5
    assert before.any() and (~before).any()
    np.testing.assert_array_equal(treated['inner_points'][:, before],
                                  parent['inner_points'][:, before])
    np.testing.assert_array_equal(treated['outer_points'][:, before],
                                  parent['outer_points'][:, before])
    assert not np.array_equal(treated['inner_points'][:, ~before],
                              parent['inner_points'][:, ~before])


def test_active_block_is_labelled(family):
    treated = resolve(family, with_onset(family, 0.5))
    assert treated['meta']['throat_hv'] == {'hv_onset_frac': 0.5}
    assert throat_hv.STATUS['rolled'] in treated['meta']['notes']


def test_section_ramp_alone_keeps_family_start_and_labels(family):
    knobs = dict(family.seed_knobs, g_section_exp_ramp=2.0)
    treated = resolve(family, knobs)
    assert treated['meta']['throat_hv'] == {'section_exp_ramp': 2.0}
    assert throat_hv.STATUS['rolled'] in treated['meta']['notes']


def test_onset_zero_is_accepted_by_the_knob_parser(family):
    block = rf._throat_knobs(with_onset(family, 0.0))
    assert block['hv_onset_frac'] == 0.0


def test_onset_with_relief_start_is_refused(family):
    knobs = dict(family.seed_knobs, g_hv_onset_frac=0.5)
    with pytest.raises(GeneratorError, match='replaces relief_start_s'):
        rf.design_params(family.gen, knobs, family.brief)


def test_zero_relief_amplitude_makes_the_block_inert_and_is_refused(family):
    knobs = with_onset(family, 0.5)
    knobs['g_inward_h_mm'] = knobs['g_inward_v_mm'] = 0.0
    with pytest.raises(GeneratorError, match='amplitudes are zero'):
        rf.design_params(family.gen, knobs, family.brief)


def test_non_neutral_ratio_is_refused_until_the_family_maps_it(family):
    knobs = dict(family.seed_knobs, g_throat_hv_ratio=2.0)
    with pytest.raises(GeneratorError, match='throat_hv_ratio not supported by rolled family yet'):
        rf.design_params(family.gen, knobs, family.brief)


@pytest.mark.parametrize('onset', [-0.1, 0.95, float('nan')])
def test_out_of_range_onset_is_refused(family, onset):
    with pytest.raises(GeneratorError):
        rf.design_params(family.gen, with_onset(family, onset), family.brief)


def test_onset_past_peak_is_refused(family):
    with pytest.raises(GeneratorError, match='hv_onset_frac < peak'):
        rf.design_params(family.gen, with_onset(family, 0.9), family.brief)


def test_onset_and_ramp_are_searchable(family):
    """The shared knobs take the place of relief_start_s in the search box."""
    from hornlab_search.design.space import Bound
    seed = {k: v for k, v in family.seed_knobs.items() if k != 'g_relief_start_s'}
    peak = family.bounds['g_relief_peak_s']
    seed.update(g_hv_onset_frac=0.0, g_section_exp_ramp=2.0)
    bounds = {k: v for k, v in family.bounds.items() if k != 'g_relief_start_s'}
    bounds['g_hv_onset_frac'] = Bound(0.0, min(0.1, peak.lo - 0.01))
    bounds['g_section_exp_ramp'] = Bound(1.0, 3.0)
    ih = bounds['g_inward_h_mm']                     # strength away from zero: position is live
    lo = max(ih.lo, 0.25 * ih.hi)
    bounds['g_inward_h_mm'] = Bound(lo, ih.hi)
    seed['g_inward_h_mm'] = min(max(seed['g_inward_h_mm'], lo), ih.hi)
    rf.validate_search_config(family.gen, seed, bounds, family.brief)
    # and a box that lets every strength reach zero still refuses the dormant position search
    with pytest.raises(GeneratorError, match='dormant'):
        rf.validate_search_config(family.gen, seed, {**bounds, 'g_inward_h_mm': ih}, family.brief)


def test_missing_bound_for_shared_knob_is_refused(family):
    seed = {k: v for k, v in family.seed_knobs.items() if k != 'g_relief_start_s'}
    seed['g_hv_onset_frac'] = 0.0
    bounds = {k: v for k, v in family.bounds.items() if k != 'g_relief_start_s'}
    with pytest.raises(GeneratorError, match='explicit matching bound'):
        rf.validate_search_config(family.gen, seed, bounds, family.brief)
