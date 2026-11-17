import copy

import numpy as np
import pytest

from hornlab_search.design.generators import klangfilm_lame_family
from hornlab_search.design.generators import klangfilm_lame_hv_family as family
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.design.space import Bound

BRIEF = {'driver': {'exit_radius_mm': 18.0, 'exit_angle_deg': 2.0}}

LEGACY_SHAPE = dict(fc_hz=560.0, aspect=1.6, lame_p=3.5, end_frac=1.5,
                    rim_sweep_ratio=0.12, morph_frac=0.3, source_blend_ratio=0.0,
                    entry_half_angle_deg=2.0, wall_thickness_mm=3.0, n_phi=19, n_s=64)
HV_SHAPE = dict(LEGACY_SHAPE, cd_core_blend=0.0, theta_h0_deg=9.4, theta_v0_deg=9.4,
                h_mid_gain_mm=0.0, v_mid_gain_mm=0.0, core_join_fraction=0.65)
SPEC = {'rows': {'type': family.KIND}, 'span': 'quarter',
        **{k: HV_SHAPE[k] for k in family.GRID_KEYS}}
KNOBS = {'g_' + k: v for k, v in HV_SHAPE.items() if k not in family.GRID_KEYS}


def _fixed_bounds(seed):
    return {key: Bound(value, value, search=False) for key, value in seed.items()}


def test_recipe_binds_geometry_and_replays_deterministically():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    first = family.resolve_grid(block, BRIEF)
    second = family.resolve_grid(copy.deepcopy(block), copy.deepcopy(BRIEF))
    assert np.array_equal(first['inner_points'], second['inner_points'])
    assert np.array_equal(first['outer_points'], second['outer_points'])
    assert first['meta']['schema'] == family.SCHEMA
    assert first['meta']['outer_offset'] == 'sampled 3D surface normal'
    assert block['rows']['implementation_sha256'] == family.implementation_digest()
    assert np.isfinite(first['outer_points']).all()


def test_a0_parity_with_legacy_kernel():
    hv, _ = family.kernel.make_grid(HV_SHAPE, BRIEF)
    legacy, _ = klangfilm_lame_family.kernel.make_grid(LEGACY_SHAPE, BRIEF)
    assert np.array_equal(hv, legacy)


def test_recipe_rejects_identity_driver_and_unknown_knob():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    stale = copy.deepcopy(block)
    stale['rows']['implementation_sha256'] = '0' * 64
    with pytest.raises(GeneratorError, match='implementation'):
        family.resolve_grid(stale, BRIEF)
    with pytest.raises(GeneratorError, match='driver differs'):
        family.resolve_grid(block, {'driver': {'exit_radius_mm': 19, 'exit_angle_deg': 2}})
    with pytest.raises(GeneratorError, match='knob mismatch'):
        family.design_params(SPEC, {**KNOBS, 'g_unknown': 1}, BRIEF)


def test_digest_covers_parent_and_cap_math(monkeypatch):
    baseline = family.implementation_digest()
    monkeypatch.setattr(family.lame_cap, '__file__', family.__file__)
    assert family.implementation_digest() != baseline
    monkeypatch.undo()
    monkeypatch.setattr(family.parent, '__file__', family.__file__)
    assert family.implementation_digest() != baseline


def test_dormant_phase_a_knobs_refused_when_blend_fixed_at_zero():
    bounds = _fixed_bounds(KNOBS)
    bounds['g_theta_h0_deg'] = Bound(6.0, 17.0, search=True)
    with pytest.raises(GeneratorError,
                       match='phase A knobs are inert when cd_core_blend is fixed at 0'):
        family.validate_search_config(SPEC, dict(KNOBS), bounds, BRIEF)


def test_inert_lower_bound_refused_when_blend_can_reach_zero():
    bounds = _fixed_bounds(KNOBS)
    bounds['g_cd_core_blend'] = Bound(0.0, 1.0, search=True)
    bounds['g_theta_h0_deg'] = Bound(6.0, 17.0, search=True)
    with pytest.raises(GeneratorError,
                       match='inert lower bound: cd_core_blend can reach 0 while phase A knobs are searched'):
        family.validate_search_config(SPEC, dict(KNOBS), bounds, BRIEF)


def test_active_blend_accepts_searched_phase_a_knobs():
    seed = dict(KNOBS, g_cd_core_blend=1.0)
    bounds = _fixed_bounds(seed)
    bounds['g_theta_h0_deg'] = Bound(6.0, 17.0, search=True)
    bounds['g_theta_v0_deg'] = Bound(3.0, 13.0, search=True)
    family.validate_search_config(SPEC, seed, bounds, BRIEF)


def test_report_only_size_policy_records_instead_of_refusing():
    # a legal shape that exceeds a deliberately tight envelope: enforce refuses, report_only records
    tight = {'driver': {'exit_radius_mm': 18.0, 'exit_angle_deg': 2.0},
             'envelope': {'max_mouth_w_mm': 400.0, 'max_mouth_h_mm': 200.0, 'max_depth_mm': 200.0}}
    spec = {**SPEC, 'size_policy': 'report_only'}
    block = family.design_params(spec, KNOBS, tight)['grid']
    out = family.resolve_grid(block, tight)
    assert out['meta']['size_policy'] == 'report_only' and out['meta']['envelope_ok'] is False
    keys = {v['key'] for v in out['meta']['envelope_violations']}
    assert {'max_mouth_w_mm', 'max_mouth_h_mm'} <= keys
    with pytest.raises(GeneratorError):
        family.design_params(SPEC, KNOBS, tight)
    with pytest.raises(GeneratorError, match='size_policy'):
        family.design_params({**SPEC, 'size_policy': 'ignore'}, KNOBS, BRIEF)
    # fixed-seed lane is allowed; a searched knob under report_only is refused
    active = dict(KNOBS, g_cd_core_blend=1.0)
    family.validate_search_config(spec, active, _fixed_bounds(active), BRIEF)
    loose = _fixed_bounds(active)
    loose['g_theta_h0_deg'] = Bound(6.0, 17.0)
    with pytest.raises(GeneratorError, match='report_only'):
        family.validate_search_config(spec, active, loose, BRIEF)


