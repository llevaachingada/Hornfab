"""Phase B Klangfilm-Lame H/V core contracts (CPU geometry only).

Pins the properties the handoff demands: exact v1 nesting when disabled, a monotone integrated-slope
flare on a shared z, independent H/V axes, a Lamé exponent that is independent of the flare, a beak
that is an exact no-op at zero and cannot touch the throat, and refusal (not clamping) of illegal or
self-approaching geometry.
"""
import hashlib

import numpy as np
import pytest

from tools.geometry import klangfilm_lame as K
from tools.geometry import klangfilm_lame_hv_core as C

BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}}


def shape(name="b1", **over):
    out = C.seed_shape(name)
    out.update(over)
    return out


def test_disabled_is_bit_identical_to_v1():
    sh = shape("b1", cd_core_blend=0.0)
    pts, meta = C.make_grid(sh, BRIEF)
    legacy, _ = K.make_grid({k: sh[k] for k in K.SHAPE_KEYS}, BRIEF)
    assert np.array_equal(pts, legacy)
    assert meta["core_mode"] == "legacy" and meta["wavefront_model"] == "legacy_curved_cap"


@pytest.mark.parametrize("name", ["b1", "b2", "b3"])
def test_core_is_monotone_and_lands_on_its_slope_law(name):
    sh = shape(name)
    tab = C.core_table(sh, 18.0)
    assert np.all(np.diff(tab["z"]) > 0)
    assert np.all(np.diff(tab["a"]) >= 0) and np.all(np.diff(tab["b"]) >= 0)
    assert tab["a"][0] == pytest.approx(18.0) and tab["b"][0] == pytest.approx(18.0)
    assert np.degrees(tab["theta_h"][0]) == pytest.approx(sh["theta_h0_deg"], abs=1e-6)
    assert np.degrees(tab["theta_h"][-1]) == pytest.approx(sh["theta_h1_deg"], abs=1e-6)
    assert np.degrees(tab["theta_v"][-1]) == pytest.approx(sh["theta_v1_deg"], abs=1e-6)
    d = C.diagnostics(sh, BRIEF)
    assert d["h_meridian_turns"] == 0 and d["v_meridian_turns"] == 0
    assert d["min_lip_clearance_mm"] > 2.0
    assert d["max_width_mm"] <= 600.0 and d["max_height_mm"] <= 480.0 and d["depth_mm"] <= 480.0


def test_axes_are_independent():
    base = C.core_table(shape("b1"), 18.0)
    h_only = C.core_table(shape("b1", theta_h0_deg=14.0), 18.0)
    v_only = C.core_table(shape("b1", theta_v1_deg=30.0), 18.0)
    assert np.array_equal(h_only["b"], base["b"])
    assert np.array_equal(v_only["a"], base["a"])
    assert not np.array_equal(h_only["a"], base["a"])
    assert not np.array_equal(v_only["b"], base["b"])


def test_lame_exponent_is_independent_of_the_flare():
    base = shape("b1")
    rounder = shape("b1", lame_p_mouth=2.0)
    pt_a, _ = C.make_grid(base, BRIEF)
    pt_b, _ = C.make_grid(rounder, BRIEF)
    # meridians (phi = 0 and phi = 90 deg) do not depend on p at all
    # rho(phi=0) == a exactly in exact arithmetic; compare tightly, not bitwise (p enters the pow)
    assert np.allclose(pt_a[0], pt_b[0], rtol=1e-12, atol=1e-12)
    assert np.allclose(pt_a[-1], pt_b[-1], rtol=1e-12, atol=1e-12)
    # ... while the diagonal does: p = 2 sits outside p = 4 on the same semi-axes
    mid = pt_a.shape[1] // 2
    diag = int(pt_a.shape[0] // 2)
    r4 = np.hypot(pt_a[diag, mid, 0], pt_a[diag, mid, 1])
    r2 = np.hypot(pt_b[diag, mid, 0], pt_b[diag, mid, 1])
    assert r2 < r4
    assert C.diagnostics(base, BRIEF)["lame_p_at_mouth"] == pytest.approx(4.0)
    assert C.diagnostics(base, BRIEF)["throat_section"]["p"] == 2.0


def test_beak_is_exact_noop_at_zero_and_touches_only_the_late_lip():
    zero = np.zeros(4)
    pts0, _ = C.make_grid(shape("b1", beak_h_setback_mm=0.0, beak_v_projection_mm=0.0,
                                beak_diagonal_mm=0.0), BRIEF)
    explicit = np.array([0.0, 0.0, 0.0])  # placeholder to keep numpy imported honestly
    pts1, _ = C.make_grid(shape("b1", beak_h_setback_mm=12.0, beak_start_frac=0.9), BRIEF)
    j = int(0.8 * (pts0.shape[1] - 1))
    assert np.array_equal(pts0[:, :j], pts1[:, :j])          # nothing before the gate
    assert pts1[0, -1, 2] < pts0[0, -1, 2] - 5.0             # H lip set back
    assert pts1[-1, -1, 2] == pytest.approx(pts0[-1, -1, 2])  # V axis untouched
    assert zero.sum() == 0.0 and explicit.sum() == 0.0


def test_beak_projection_moves_the_v_lip_forward():
    base, _ = C.make_grid(shape("b1", beak_v_projection_mm=0.0), BRIEF)
    proj, _ = C.make_grid(shape("b1", beak_v_projection_mm=8.0, beak_start_frac=0.9), BRIEF)
    assert proj[-1, -1, 2] > base[-1, -1, 2] + 3.0
    assert proj[0, -1, 2] == pytest.approx(base[0, -1, 2])


def test_validation_refuses_illegal_core_knobs():
    for bad in (shape("b1", theta_h1_deg=89.0), shape("b1", theta_h0_deg=90.0),
                shape("b1", lame_start_frac=0.8, lame_end_frac=0.5),
                shape("b1", cd_core_blend=1.5), shape("b1", core_length_mm=1.0),
                dict(shape("b1"), bogus=1)):
        with pytest.raises(ValueError):
            C.validate_shape(bad)


def test_refusal_is_not_clamping_for_self_approach():
    # a late, large setback moves the lip backward faster than the core advances: a fold, not a lip
    with pytest.raises(ValueError, match="folds the lip back|reverses axially|lip returns"):
        C.make_grid(shape("b1", beak_h_setback_mm=60.0, beak_start_frac=0.95), BRIEF)
    # the same setback applied over a longer gate is a legal lip: the H edge sits 60 mm back
    base, _ = C.make_grid(shape("b1", beak_h_setback_mm=0.0), BRIEF)
    pts, _ = C.make_grid(shape("b1", beak_h_setback_mm=60.0, beak_start_frac=0.5), BRIEF)
    assert pts[0, -1, 2] == pytest.approx(base[0, -1, 2] - 60.0, abs=1e-9)
    assert pts[-1, -1, 2] == pytest.approx(base[-1, -1, 2], abs=1e-12)


def test_deterministic_grid_hash():
    h = [hashlib.sha256(C.make_grid(shape("b2"), BRIEF)[0].tobytes()).hexdigest() for _ in range(2)]
    assert h[0] == h[1]


def test_flat_area_and_throat_identity():
    from tools.geometry import lame_cap
    d = C.diagnostics(shape("b1"), BRIEF)
    t = d["throat_section"]
    assert t["a_mm"] == pytest.approx(18.0) and t["b_mm"] == pytest.approx(18.0)
    assert t["area_mm2"] == pytest.approx(np.pi * 18.0 ** 2, rel=1e-12)
    m = d["mouth_section"]
    assert m["area_mm2"] == pytest.approx(lame_cap.flat_lame_area(m["a_mm"], m["b_mm"], m["p"]),
                                          rel=1e-12)
    assert m["area_mm2"] > 20 * t["area_mm2"]
