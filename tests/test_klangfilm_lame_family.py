import copy

import numpy as np
import pytest

from hornlab_search.design.generators import klangfilm_lame_family as family
from hornlab_search.design.generators.registry import GeneratorError

BRIEF = {'driver': {'exit_radius_mm': 18.0, 'exit_angle_deg': 2.0}}
SHAPE = dict(fc_hz=560.0, aspect=1.6, lame_p=3.5, end_frac=1.5,
             rim_sweep_ratio=0.12, morph_frac=0.3, source_blend_ratio=0.0,
             entry_half_angle_deg=2.0, wall_thickness_mm=3.0, n_phi=19, n_s=64)
SPEC = {'rows': {'type': family.KIND}, 'span': 'quarter',
        **{k: SHAPE[k] for k in family.GRID_KEYS}}
KNOBS = {'g_'+k: v for k, v in SHAPE.items() if k not in family.GRID_KEYS}


def test_recipe_binds_geometry_and_replays_deterministically():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    first = family.resolve_grid(block, BRIEF)
    second = family.resolve_grid(copy.deepcopy(block), copy.deepcopy(BRIEF))
    assert np.array_equal(first['inner_points'], second['inner_points'])
    assert np.array_equal(first['outer_points'], second['outer_points'])
    assert first['meta']['outer_offset'] == 'sampled 3D surface normal'
    assert block['rows']['implementation_sha256'] == family.implementation_digest()
    assert np.isfinite(first['outer_points']).all()


def test_recipe_rejects_identity_and_driver_drift():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    stale = copy.deepcopy(block)
    stale['rows']['implementation_sha256'] = '0'*64
    with pytest.raises(GeneratorError, match='implementation'):
        family.resolve_grid(stale, BRIEF)
    with pytest.raises(GeneratorError, match='driver differs'):
        family.resolve_grid(block, {'driver': {'exit_radius_mm': 19, 'exit_angle_deg': 2}})
    with pytest.raises(GeneratorError, match='knob mismatch'):
        family.design_params(SPEC, {**KNOBS, 'g_unknown': 1}, BRIEF)


def test_kernel_and_shell_are_in_identity(monkeypatch):
    baseline = family.implementation_digest()
    monkeypatch.setattr(family.lame_cap, '__file__', family.__file__)
    assert family.implementation_digest() != baseline


def test_frozen_kernel_matches_research_source():
    from tools.geometry import klangfilm_lame as research
    canonical, _ = family.kernel.make_grid(SHAPE, BRIEF)
    original, _ = research.make_grid(SHAPE, BRIEF)
    assert np.array_equal(canonical, original)


def test_zero_source_angle_is_refused():
    with pytest.raises(GeneratorError, match='invalid driver'):
        family.design_params(SPEC, KNOBS, {'driver': {'exit_radius_mm': 18, 'exit_angle_deg': 0}})


def test_self_approach_refusal_is_propagated(monkeypatch):
    from hornlab_search.design.generators import grid
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    def refuse(inner, outer, thickness):
        assert inner.shape == outer.shape and thickness == SHAPE['wall_thickness_mm']
        raise GeneratorError('grid self-approach: test refusal')
    monkeypatch.setattr(grid, 'check_self_approach', refuse)
    with pytest.raises(GeneratorError, match='self-approach'):
        family.resolve_grid(block, BRIEF)


def test_runtime_versions_are_bound_to_identity(monkeypatch):
    baseline = family.implementation_digest()
    monkeypatch.setattr(family.np, '__version__', 'different-test-version')
    assert family.implementation_digest() != baseline
    monkeypatch.undo()
    monkeypatch.setattr(family.scipy, '__version__', 'different-test-version')
    assert family.implementation_digest() != baseline
