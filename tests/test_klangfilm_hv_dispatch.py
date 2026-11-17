"""Dispatch a canonical Klangfilm-Lame H/V block through the public rows route, in-process only."""
import numpy as np
import pytest

from hornlab_search.design.generators import grid
from hornlab_search.design.generators import klangfilm_lame_hv_family as family
from hornlab_search.design.generators.registry import GeneratorError

BRIEF = {'driver': {'exit_radius_mm': 18.0, 'exit_angle_deg': 2.0}}
HV_SHAPE = dict(fc_hz=560.0, aspect=1.6, lame_p=3.5, end_frac=1.5,
                rim_sweep_ratio=0.12, morph_frac=0.3, source_blend_ratio=0.0,
                entry_half_angle_deg=2.0, wall_thickness_mm=3.0, n_phi=19, n_s=64,
                cd_core_blend=0.0, theta_h0_deg=9.4, theta_v0_deg=9.4,
                h_mid_gain_mm=0.0, v_mid_gain_mm=0.0, core_join_fraction=0.65)
SPEC = {'rows': {'type': family.KIND}, 'span': 'quarter',
        **{k: HV_SHAPE[k] for k in family.GRID_KEYS}}
KNOBS = {'g_' + k: v for k, v in HV_SHAPE.items() if k not in family.GRID_KEYS}


def test_dispatch_rows_grid_points_is_finite_and_identity_matches():
    block = family.design_params(SPEC, KNOBS, BRIEF)['grid']
    grid.validate_grid_params(block)
    inner, meta = grid.rows_grid_points(block, block['knobs'], BRIEF)
    assert np.isfinite(inner).all()
    assert meta['implementation_sha256'] == block['rows']['implementation_sha256']


def test_unknown_family_spec_still_raises():
    bogus = {'rows': {'type': 'no_such_family'}, 'n_phi': 19, 'n_s': 64,
             'wall_thickness_mm': 3.0, 'knobs': {}}
    with pytest.raises(GeneratorError, match='unknown rows type'):
        grid.rows_grid_points(bogus, bogus['knobs'], BRIEF)
