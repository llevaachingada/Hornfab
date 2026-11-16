"""CPU contracts for the Klangfilm-Lame geometry (math invariants, throat provenance, grid sanity, determinism)."""
import copy
import hashlib
import math

import numpy as np
import pytest

from tools.geometry import klangfilm_lame as K
from tools.geometry import lame_cap as L

BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}}
SHAPE = dict(fc_hz=560.0, aspect=1.6, lame_p=3.5, end_frac=1.5, rim_sweep_ratio=0.12, morph_frac=0.3,
             source_blend_ratio=0.0, entry_half_angle_deg=2.0, wall_thickness_mm=3.0, n_phi=19, n_s=64)


def test_sphere_cap_analytic():
    for c in (0.03, 0.14, 0.25):
        for h in (0.03 * c, 0.3 * c, c, 1.8 * c):
            assert L.lame_cap_area(c, c, c, h, 2, 24) == pytest.approx(2 * math.pi * c * h, rel=1e-11)


def test_p2_matches_independent_ellipsoid_integrand():
    for a, b, c, h in ((.2, .13, .19, .09), (.08, .06, .17, .03), (.14, .2, .31, .45)):
        assert L.lame_cap_area(a, b, c, h, 2.0, 64) == pytest.approx(L.legacy_ellipsoid_cap_area(a, b, c, h), rel=1e-10)


def test_flat_area_and_p_monotone():
    assert L.flat_lame_area(.12, .08, 2) == pytest.approx(math.pi * .12 * .08, rel=1e-12)
    assert L.flat_lame_area(.12, .08, 6) > L.flat_lame_area(.12, .08, 2)


@pytest.mark.parametrize("p", [2, 2.5, 4, 6, 8])
def test_quadrature_converges_and_area_lock(p):
    assert L.lame_cap_area(.2, .13, .19, .09, p, 48) == pytest.approx(L.lame_cap_area(.2, .13, .19, .09, p, 96), rel=1e-5)
    target = 2 * math.pi * .19 * .09
    a, b = L.area_locked_axes(target, 1.8, .19, .09, p, 48)
    assert a / b == pytest.approx(1.8, rel=1e-12)
    assert L.lame_cap_area(a, b, .19, .09, p, 48) == pytest.approx(target, rel=1e-8)


def test_quintic_is_c2_gate():
    assert L.quintic(0) == 0 and L.quintic(1) == 1 and L.quintic(-3) == 0 and L.quintic(9) == 1
    e = 1e-4
    assert abs(L.quintic(e)) < 1e-9 and abs(1 - L.quintic(1 - e)) < 1e-9


def test_raw_parent_halfangle_is_derived_not_two_degrees():
    assert K.parent_wall_halfangle_deg(560.0, 18.0) == pytest.approx(10.617223, abs=1e-5)
    assert K.parent_wall_halfangle_deg(450.0, 18.0) == pytest.approx(8.521, abs=2e-3)
    assert K.parent_wall_halfangle_deg(800.0, 18.0) == pytest.approx(15.224, abs=2e-3)


def test_grid_throat_round_area_locked_finite():
    pts, meta = K.make_grid(SHAPE, BRIEF)
    assert pts.shape == (19, 65, 3) and np.isfinite(pts).all()
    ring = np.hypot(pts[:, 0, 0], pts[:, 0, 1])
    assert np.ptp(ring) < 1e-9 and ring.mean() == pytest.approx(18.0)
    assert meta["cap_area_resid_max"] < 1e-8
    assert meta["angle_provenance"] == "assumed_legacy" and meta["source_auto_angle_deg"] == 2.0
    # no forced 2 deg: raw tangent stays ~10.6 deg
    d = K.diagnostics(SHAPE, BRIEF)
    assert 10.0 < d["wall_halfangle_h_deg"] < 12.0 and 10.0 < d["wall_halfangle_v_deg"] < 12.0
    assert d["min_radius_ratio_to_throat"] >= 1.0 - 1e-6


def test_p2_q1_reduces_to_round_parent():
    sh = dict(SHAPE, aspect=1.0, lame_p=2.0, rim_sweep_ratio=0.0)
    pts, _ = K.make_grid(sh, BRIEF)
    r = np.hypot(pts[..., 0], pts[..., 1])
    assert np.ptp(r, axis=0).max() < 1e-6


def test_aspect_and_exponent_take_effect_and_h_is_wider():
    pts, _ = K.make_grid(SHAPE, BRIEF)
    wid, hei = np.abs(pts[0, :, 0]).max(), np.abs(pts[-1, :, 1]).max()
    assert wid / hei > 1.2
    sq, _ = K.make_grid(dict(SHAPE, lame_p=2.0), BRIEF)          # p=2 diagonal sits inside the squarer p=3.5 one
    mid = pts.shape[0] // 2
    j = int(pts.shape[1] * 0.6)
    assert np.hypot(*pts[mid, j, :2]) > np.hypot(*sq[mid, j, :2])


def test_rim_sweep_sets_back_h_side_only():
    flat, _ = K.make_grid(dict(SHAPE, rim_sweep_ratio=0.0), BRIEF)
    sw, _ = K.make_grid(SHAPE, BRIEF)
    assert np.allclose(sw[0, 0], flat[0, 0])                       # throat unchanged
    assert np.allclose(sw[-1, :, 2], flat[-1, :, 2])               # V axis (cos^2 = 0) unchanged
    assert (flat[0, -1, 2] - sw[0, -1, 2]) > 5.0                   # H rim set back


def test_source_blend_off_by_default_and_hits_target_when_on():
    base = K.diagnostics(SHAPE, BRIEF)
    off = K.diagnostics(dict(SHAPE, entry_half_angle_deg=5.0), BRIEF)
    assert off["wall_halfangle_h_deg"] == base["wall_halfangle_h_deg"]       # angle ignored while blend is 0
    on = K.diagnostics(dict(SHAPE, source_blend_ratio=0.8, entry_half_angle_deg=5.0), BRIEF)
    assert abs(on["wall_halfangle_h_deg"] - 5.0) < 0.6 and abs(on["wall_halfangle_v_deg"] - 5.0) < 0.6
    assert on["throat_radius_spread_mm"] < 1e-9
    pts_on, _ = K.make_grid(dict(SHAPE, source_blend_ratio=0.8, entry_half_angle_deg=5.0), BRIEF)
    pts_off, _ = K.make_grid(SHAPE, BRIEF)
    assert np.allclose(pts_on[:, -1], pts_off[:, -1], atol=2.0)    # far field of the horn is not disturbed


def test_deterministic_hash_and_validation():
    h = [hashlib.sha256(K.make_grid(copy.deepcopy(SHAPE), BRIEF)[0].tobytes()).hexdigest() for _ in range(2)]
    assert h[0] == h[1]
    for bad in (dict(SHAPE, lame_p=1.5), dict(SHAPE, aspect=0.5), dict(SHAPE, end_frac=2.5), dict(SHAPE, n_phi=3)):
        with pytest.raises(ValueError):
            K.validate_shape(bad)
    extra = dict(SHAPE, bogus=1)
    with pytest.raises(ValueError):
        K.validate_shape(extra)
    with pytest.raises(ValueError):
        K.make_grid(dict(SHAPE, fc_hz=150.0), {"driver": {"exit_radius_mm": 5000.0, "exit_angle_deg": 2.0}})
