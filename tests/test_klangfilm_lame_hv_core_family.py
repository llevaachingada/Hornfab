"""Canonical Phase B family: recipe identity, class-separation guards, size policy, config route."""
import copy

import numpy as np
import pytest

from hornlab_search.config import load_config
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid
from hornlab_search.design.generators import klangfilm_lame_hv_core_family as family
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.design.space import Bound
from hornlab_search.types import Design
from tools.geometry import klangfilm_lame as K
from tools.geometry import klangfilm_lame_hv_core as C

BRIEF = {'driver': {'exit_radius_mm': 18.0, 'exit_angle_deg': 2.0}}
SHAPE = C.seed_shape('b1')
SPEC = {'rows': {'type': family.KIND}, 'span': 'quarter',
        **{k: SHAPE[k] for k in family.GRID_KEYS}}
KNOBS = {'g_' + k: v for k, v in SHAPE.items() if k not in family.GRID_KEYS}
ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'examples/typologies/klangfilm_hv_2026-11-16/configs/b1_balanced.yaml'


def _fixed(seed):
    return {k: Bound(v, v, search=False) for k, v in seed.items()}


def test_recipe_binds_and_replays_deterministically():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    first = family.resolve_grid(block, BRIEF)
    second = family.resolve_grid(copy.deepcopy(block), copy.deepcopy(BRIEF))
    assert np.array_equal(first['inner_points'], second['inner_points'])
    assert np.array_equal(first['outer_points'], second['outer_points'])
    assert first['meta']['schema'] == family.SCHEMA
    assert block['rows']['implementation_sha256'] == family.implementation_digest()
    assert np.isfinite(first['outer_points']).all()


def test_blend_zero_is_bit_identical_to_v1():
    sh = dict(SHAPE, cd_core_blend=0.0)
    canonical, _ = family.kernel.make_grid(sh, BRIEF)
    legacy, _ = K.make_grid({k: sh[k] for k in K.SHAPE_KEYS}, BRIEF)
    assert np.array_equal(canonical, legacy)


def test_digest_is_identity_bound():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    stale = copy.deepcopy(block)
    stale['rows']['implementation_sha256'] = '0' * 64
    with pytest.raises(GeneratorError, match='implementation'):
        family.resolve_grid(stale, BRIEF)
    with pytest.raises(GeneratorError, match='driver differs'):
        family.resolve_grid(block, {'driver': {'exit_radius_mm': 19, 'exit_angle_deg': 2}})
    with pytest.raises(GeneratorError, match='knob mismatch'):
        family.design_params(SPEC, {**KNOBS, 'g_unknown': 1}, BRIEF)


def test_blend_must_be_fixed():
    bounds = _fixed(KNOBS)
    bounds['g_cd_core_blend'] = Bound(0.0, 1.0)
    with pytest.raises(GeneratorError, match='cd_core_blend must be fixed'):
        family.validate_search_config(SPEC, KNOBS, bounds, BRIEF)


def test_inactive_class_knobs_must_be_fixed():
    # hv_core mode: the legacy parent genes are inert
    bounds = _fixed(KNOBS)
    bounds['g_aspect'] = Bound(1.5, 2.5)
    with pytest.raises(GeneratorError, match='inert in hv_core mode'):
        family.validate_search_config(SPEC, KNOBS, bounds, BRIEF)
    # legacy mode: the Phase B core knobs are inert
    legacy_knobs = dict(KNOBS, g_cd_core_blend=0.0)
    lb = _fixed(legacy_knobs)
    lb['g_theta_h0_deg'] = Bound(6.0, 17.0)
    with pytest.raises(GeneratorError, match='inert in legacy mode'):
        family.validate_search_config(SPEC, legacy_knobs, lb, BRIEF)


def test_hv_core_mode_accepts_a_four_knob_box():
    bounds = _fixed(KNOBS)
    seed = dict(KNOBS)
    for key in ('g_theta_h0_deg', 'g_theta_v0_deg', 'g_core_length_mm', 'g_lame_p_mouth'):
        lo, hi = {'g_theta_h0_deg': (6.0, 17.0), 'g_theta_v0_deg': (3.0, 13.0),
                  'g_core_length_mm': (200.0, 420.0), 'g_lame_p_mouth': (2.0, 6.0)}[key]
        bounds[key] = Bound(lo, hi)
        seed[key] = 0.5 * (lo + hi)
    family.validate_search_config(SPEC, seed, bounds, BRIEF)


def test_report_only_is_recorded_but_not_searchable():
    tight = {'driver': dict(BRIEF['driver']),
             'envelope': {'max_mouth_w_mm': 300.0, 'max_mouth_h_mm': 200.0, 'max_depth_mm': 200.0}}
    spec = {**SPEC, 'size_policy': 'report_only'}
    block = family.design_params(spec, KNOBS, tight)['grid']
    out = family.resolve_grid(block, tight)
    assert out['meta']['size_policy'] == 'report_only' and out['meta']['envelope_ok'] is False
    assert {v['key'] for v in out['meta']['envelope_violations']} >= {'max_mouth_w_mm', 'max_mouth_h_mm'}
    with pytest.raises(GeneratorError):
        family.design_params(SPEC, KNOBS, tight)
    loose = _fixed(KNOBS)
    loose['g_core_length_mm'] = Bound(300.0, 400.0)
    with pytest.raises(GeneratorError, match='report_only'):
        family.validate_search_config(spec, dict(KNOBS, g_core_length_mm=350.0), loose, tight)


def test_shipped_config_materialises_and_replays():
    cfg = load_config(CONFIG)
    space = GeneratedSpace.from_config(cfg)
    block = space.seed.params['grid']
    grid.validate_grid_params(block)
    inner, meta = grid.rows_grid_points(block, block['knobs'], cfg.brief)
    assert inner.shape == (19, 65, 3) and np.isfinite(inner).all()
    assert meta['core_mode'] == 'hv_core' and meta['wavefront_model'] == 'independent_hv_core'
    assert meta['implementation_sha256'] == block['rows']['implementation_sha256']
    again = GeneratedSpace.from_config(cfg)
    assert again.knobs_for(Design('FREEFORM', space.seed.params)) == space.seed_knobs
