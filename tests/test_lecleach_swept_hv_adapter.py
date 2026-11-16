import numpy as np
import pytest
from hornlab_search.design.generators import lecleach_swept_hv as L, lame_shell
from hornlab_search.design.generators.registry import GeneratorError

PARAMS = dict(g_fc_hz=500., g_T=.5, g_stop_deg=118., g_ar_m=1.5, g_ar_p=1.,
              g_lame_p_mouth=2., g_lip_radius_mm=0., g_rim_sweep_mm=0., g_axial_length_factor=1.)
SPEC = dict(rows=dict(L.ROW_FIELDS), n_phi=25, n_s=96, span='quarter', wall_thickness_mm=3.)
BRIEF = dict(driver=dict(exit_radius_mm=18., exit_angle_deg=2.))


def test_recipe_resolves_and_binds_source_and_implementation():
    block = L.design_params(SPEC, PARAMS, BRIEF)['grid']
    resolved = L.resolve_grid(block, BRIEF)
    assert block['rows']['implementation_sha256'] == L.implementation_digest()
    assert block['knobs'] == PARAMS
    inner, outer = resolved['inner_points'], resolved['outer_points']
    assert np.allclose(np.linalg.norm(outer-inner, axis=-1), 3.)
    assert np.allclose(inner[0, :, 1], 0) and np.allclose(outer[-1, :, 0], 0)
    assert resolved['meta']['shell_and_validity']['global_self_intersection'] == 'not_checked'
    with pytest.raises(GeneratorError, match='driver differs'):
        L.resolve_grid(block, dict(driver=dict(exit_radius_mm=17., exit_angle_deg=2.)))
    block['rows']['implementation_sha256'] = '0' * 64
    with pytest.raises(GeneratorError, match='implementation differs'):
        L.validate_grid_params(block)


def test_strict_contract_rejects_unknown_and_missing_fields():
    with pytest.raises(GeneratorError):
        L.design_params({**SPEC, 'rows': {**L.ROW_FIELDS, 'area_mode': 'wavefront'}}, PARAMS, BRIEF)
    with pytest.raises(GeneratorError):
        L.design_params(SPEC, {**PARAMS, 'typo': 1}, BRIEF)
    with pytest.raises(GeneratorError):
        L.design_params({**SPEC, 'span': 'full'}, PARAMS, BRIEF)


def test_normal_offset_detects_degenerate_surface():
    with pytest.raises(ValueError, match='degenerate'):
        lame_shell.offset_quarter_surface(np.zeros((4, 4, 3)), 3.)


def test_sweep_produces_true_three_dimensional_normal():
    inner, _ = L.make_grid({**PARAMS, 'g_rim_sweep_mm': 20., 'g_lame_p_mouth': 3.},
                            throat_radius_mm=18., throat_half_angle_deg=2., n_phi=25, n_s=96)
    outer, _ = lame_shell.offset_quarter_surface(inner, 3.)
    delta = outer-inner
    tangent_phi = np.gradient(inner, axis=0)
    tangent_s = np.gradient(inner, axis=1)
    assert np.max(np.abs(np.sum(delta[1:-1, 1:-1] * tangent_phi[1:-1, 1:-1], axis=-1))) < 1e-9
    assert np.max(np.abs(np.sum(delta[1:-1, 1:-1] * tangent_s[1:-1, 1:-1], axis=-1))) < 1e-9


def test_search_validation_rejects_dormant_and_invalid_bounds():
    from types import SimpleNamespace
    def bound(lo, hi, search=False, log=False):
        return SimpleNamespace(lo=lo, hi=hi, search=search, log=log)
    fixed = {k: bound(v, v) for k, v in PARAMS.items()}
    L.validate_search_config(SPEC, PARAMS, fixed, BRIEF)
    with pytest.raises(GeneratorError, match='explicit matching bound'):
        L.validate_search_config(SPEC, PARAMS, {k: v for k, v in fixed.items() if k != 'g_T'}, BRIEF)
    with pytest.raises(GeneratorError, match='dormant'):
        L.validate_search_config(SPEC, PARAMS, {**fixed, 'g_ar_m': bound(1., 2., True),
                                               'g_ar_p': bound(1., 2., True)}, BRIEF)
    with pytest.raises(GeneratorError, match='fixed bound'):
        L.validate_search_config(SPEC, PARAMS, {**fixed, 'g_T': bound(.4, .6)}, BRIEF)
    with pytest.raises(GeneratorError, match='invalid search bound'):
        L.validate_search_config(SPEC, PARAMS, {**fixed, 'g_lame_p_mouth': bound(2., 7., True)}, BRIEF)
    with pytest.raises(GeneratorError, match='positive width'):
        L.validate_search_config(SPEC, PARAMS, {**fixed, 'g_T': bound(.5, .5, True)}, BRIEF)
    L.validate_search_config(SPEC, PARAMS, {**fixed, 'g_ar_m': bound(1.2, 2., True),
                                           'g_ar_p': bound(1., 2., True)}, BRIEF)
