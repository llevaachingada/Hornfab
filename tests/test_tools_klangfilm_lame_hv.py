"""Phase A Klangfilm-Lame H/V throat-core contracts (math + materialised geometry, CPU only).

Acceptance here is geometric, not acoustic: exact legacy nesting, independent H/V throat tangents on a
round rim, C2-at-the-join deformation, no silent constriction, and convergence under refinement.
"""
import copy
import hashlib
import math

import numpy as np
import pytest

from tools.geometry import klangfilm_lame as K
from tools.geometry import klangfilm_lame_hv as H

BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}}

#: Canonical incumbent from runs/20261116T205942Z-screen-8b22b5/best.json (unrounded).
BASE = dict(fc_hz=494.4393461867, aspect=2.0759495982, lame_p=5.0063549541, end_frac=1.7953432921,
            rim_sweep_ratio=0.004898754, morph_frac=0.3, source_blend_ratio=0.0,
            entry_half_angle_deg=2.0, wall_thickness_mm=3.0, n_phi=19, n_s=64)
INERT = dict(cd_core_blend=0.0, theta_h0_deg=9.4, theta_v0_deg=9.4, h_mid_gain_mm=0.0,
             v_mid_gain_mm=0.0, core_join_fraction=0.65)

SEEDS = {
    "a1": dict(theta_h0_deg=10.0, theta_v0_deg=5.0, h_mid_gain_mm=0.0, v_mid_gain_mm=0.0,
               core_join_fraction=0.65),
    "a2": dict(theta_h0_deg=14.0, theta_v0_deg=5.0, h_mid_gain_mm=0.0, v_mid_gain_mm=0.0,
               core_join_fraction=0.65),
    "a3b": dict(theta_h0_deg=9.0, theta_v0_deg=6.0, h_mid_gain_mm=18.0, v_mid_gain_mm=0.0,
                core_join_fraction=0.75),
    "a4b": dict(theta_h0_deg=9.0, theta_v0_deg=4.0, h_mid_gain_mm=8.0, v_mid_gain_mm=0.0,
                core_join_fraction=0.65),
    "a5": dict(fc_hz=400.0, aspect=1.65, lame_p=4.0, end_frac=1.20, rim_sweep_ratio=0.10,
               theta_h0_deg=11.0, theta_v0_deg=6.0, h_mid_gain_mm=12.0, v_mid_gain_mm=6.0,
               core_join_fraction=0.65),
}


def shape(core="a1", **over):
    out = dict(BASE)
    out.update(INERT)
    out["cd_core_blend"] = 1.0
    out.update(SEEDS[core])
    out.update(over)
    return out


# ---------------------------------------------------------------- pure kernel
def test_delta_is_c1_exact_at_throat_and_c2_zero_at_join():
    L, base, target = 120.0, 9.3669, 15.0
    dm = math.tan(math.radians(target)) - math.tan(math.radians(base))
    d0 = H.cd_hv_delta(np.array([0.0]), L, base, target, 0.0, 1.0)[0]
    assert d0 == 0.0
    h = 1e-7
    slope = H.cd_hv_delta(np.array([h]), L, base, target, 0.0, 1.0)[0] / h
    assert slope == pytest.approx(dm, rel=1e-5, abs=1e-9)
    # value, first and second derivative vanish at the join (C2)
    z = np.linspace(0.0, L, 20001)
    d = H.cd_hv_delta(z, L, base, target, 25.0, 1.0)
    assert abs(d[-1]) < 1e-9
    assert abs((d[-1] - d[-2]) / (z[-1] - z[-2])) < 1e-6   # O(dz) forward-difference truncation
    eps = 1e-3
    d2 = (H.cd_hv_delta(np.array([L]), L, base, target, 25.0, 1.0)[0]
          - 2 * H.cd_hv_delta(np.array([L - eps]), L, base, target, 25.0, 1.0)[0]
          + H.cd_hv_delta(np.array([L - 2 * eps]), L, base, target, 25.0, 1.0)[0]) / eps ** 2
    assert abs(d2) < 1e-4
    # exactly zero outside the interval (rollback safety)
    outside = H.cd_hv_delta(np.array([-1.0, L + 1e-6, 400.0]), L, base, target, 25.0, 1.0)
    assert np.array_equal(outside, np.zeros(3))


def test_delta_is_linear_in_blend_and_gain_peaks_at_mid_span():
    L = 100.0
    full = H.cd_hv_delta(np.array([50.0]), L, 9.0, 12.0, 10.0, 1.0)[0]
    half = H.cd_hv_delta(np.array([50.0]), L, 9.0, 12.0, 10.0, 0.5)[0]
    assert half == pytest.approx(0.5 * full, rel=1e-12)
    # the B2 term alone reaches exactly mid_gain at t = 1/2 and is zero at both ends
    only_gain = H.cd_hv_delta(np.array([0.0, 50.0, L]), L, 9.0, 9.0, 10.0, 1.0)
    assert np.allclose(only_gain[[0, 2]], 0.0, atol=1e-12) and only_gain[1] == pytest.approx(10.0)


def test_delta_rejects_bad_inputs():
    with pytest.raises(ValueError):
        H.cd_hv_delta(np.array([1.0]), 0.0, 9.0, 12.0)
    with pytest.raises(ValueError):
        H.cd_hv_delta(np.array([1.0]), 10.0, 9.0, 12.0, core_blend=1.5)


# ---------------------------------------------------------------- legacy nesting
def test_a0_is_bit_identical_to_the_legacy_parent():
    legacy, _ = K.make_grid(BASE, BRIEF)
    hv, meta = H.make_grid(dict(BASE, **INERT), BRIEF)
    assert np.array_equal(hv, legacy)
    assert meta["core_mode"] == "legacy" and meta["area_mode"] == "curved_cap_ratio_locked"
    assert meta["core_join_fraction"] == 0.65


def test_a0_ignores_inert_angle_and_gain_values():
    zero = H.make_grid(dict(BASE, **INERT), BRIEF)[0]
    loud = H.make_grid(dict(BASE, **dict(INERT, theta_h0_deg=20.0, theta_v0_deg=0.0,
                                        h_mid_gain_mm=30.0, v_mid_gain_mm=-30.0)), BRIEF)[0]
    assert np.array_equal(zero, loud)


# ---------------------------------------------------------------- H/V independence
@pytest.mark.parametrize("name", sorted(SEEDS))
def test_targets_are_hit_and_measured_on_the_dense_table(name):
    sh = shape(name)
    d = H.diagnostics(sh, BRIEF)
    assert d["theta_model_h_deg"] == pytest.approx(sh["theta_h0_deg"], abs=1e-9)
    assert d["theta_model_v_deg"] == pytest.approx(sh["theta_v0_deg"], abs=1e-9)
    # finite-difference chord over the first dense station (known O(dz) bias, not a tolerance escape)
    assert abs(d["wall_halfangle_h_deg"] - sh["theta_h0_deg"]) < 0.6
    assert abs(d["wall_halfangle_v_deg"] - sh["theta_v0_deg"]) < 0.6
    assert d["q_at_0"] == pytest.approx(1.0, abs=1e-12)
    assert d["throat_radius_spread_mm"] < 1e-9
    assert d["throat_radius_mm"] == pytest.approx(18.0, abs=1e-9)
    assert d["lame_p_at_throat"] == 2.0


def test_each_axis_responds_alone():
    h_only = dict(shape("a1"), theta_h0_deg=16.0)
    v_only = dict(shape("a1"), theta_v0_deg=3.0)
    tab_h = H.profile(h_only, 18.0)
    tab_v = H.profile(v_only, 18.0)
    # H-only: V semi-axis array untouched; V-only: H untouched
    assert np.array_equal(tab_h["b"], H.profile(shape("a1"), 18.0)["b"])
    assert np.array_equal(tab_v["a"], H.profile(shape("a1"), 18.0)["a"])
    dh = H.diagnostics(h_only, BRIEF)
    dv = H.diagnostics(v_only, BRIEF)
    assert dh["theta_model_v_deg"] == pytest.approx(5.0, abs=1e-9)
    assert dv["theta_model_h_deg"] == pytest.approx(10.0, abs=1e-9)
    assert dh["theta_model_h_deg"] > dv["theta_model_h_deg"]
    # a stronger H entrance widens the early section aspect ratio
    assert dh["q_at_5mm"] > dv["q_at_5mm"]


def test_mid_gain_changes_the_interior_only():
    same_join = dict(shape("a1"), theta_h0_deg=9.0, theta_v0_deg=6.0, core_join_fraction=0.75)
    plain = H.diagnostics(same_join, BRIEF)
    spread = H.diagnostics(shape("a3b"), BRIEF)
    j = H.forward_slice(H.profile(shape("a3b"), 18.0))
    tab_plain = H.profile(same_join, 18.0)
    tab_spread = H.profile(shape("a3b"), 18.0)
    join = tab_spread["hv"]["core_join_mm"]
    beyond = tab_spread["z"][: j + 1] > join
    assert beyond.any()
    assert np.array_equal(tab_plain["a"][: j + 1][beyond], tab_spread["a"][: j + 1][beyond])
    assert np.array_equal(tab_plain["b"][: j + 1][beyond], tab_spread["b"][: j + 1][beyond])
    # the interior really moved in opposite directions
    assert spread["semi_axes_by_z"]["20"]["a_mm"] > plain["semi_axes_by_z"]["20"]["a_mm"] + 0.5
    assert spread["semi_axes_by_z"]["20"]["b_mm"] == plain["semi_axes_by_z"]["20"]["b_mm"]
    # a POSITIVE V gain is the admissible direction: it lifts the slow axis and stays monotone
    wide_v = H.profile(dict(shape("a5"), v_mid_gain_mm=0.0), 18.0)
    with_v = H.profile(shape("a5"), 18.0)
    assert H._semi_axes_at(with_v, 60.0)[1] > H._semi_axes_at(wide_v, 60.0)[1] + 3.0
    assert H._semi_axes_at(with_v, 60.0)[0] == pytest.approx(H._semi_axes_at(wide_v, 60.0)[0])


# ---------------------------------------------------------------- refusal / no clamping
@pytest.mark.parametrize("core,gain_v", [("a3b", -8.0), ("a4b", -14.0), ("a3b", -4.0)])
def test_constriction_is_refused_not_clamped(core, gain_v):
    sh = dict(shape(core), v_mid_gain_mm=gain_v)
    with pytest.raises(ValueError, match="shrinks below the throat radius|not non-decreasing"):
        H.make_grid(sh, BRIEF)


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_accepted_forward_branch_is_monotone_and_rollback_is_legacy(name):
    sh = shape(name)
    tab = H.profile(sh, 18.0)
    base = K.profile(H.legacy_view(sh), 18.0)
    turn = H.forward_slice(tab)
    z = tab["z"]
    assert np.all(np.diff(z[: turn + 1]) > 0)
    assert np.all(np.diff(tab["a"][: turn + 1]) >= 0)
    assert np.all(np.diff(tab["b"][: turn + 1]) >= 0)
    assert np.all(tab["a"][turn:] == base["a"][turn:]) and np.all(tab["b"][turn:] == base["b"][turn:])
    assert H.diagnostics(sh, BRIEF)["axial_turns_whole_profile"] == 1


def test_phase_a_does_not_touch_lame_exponent_progression():
    tab = H.profile(shape("a2"), 18.0)
    base = K.profile(BASE, 18.0)
    assert np.array_equal(tab["p"], base["p"])
    assert np.array_equal(tab["h"], base["h"])


# ---------------------------------------------------------------- convergence / determinism
def test_mesh_chord_converges_towards_the_model_tangent():
    sh = shape("a2")
    coarse = H.diagnostics(sh, BRIEF)
    fine = H.diagnostics(dict(sh, n_s=256), BRIEF)
    model_h, model_v = sh["theta_h0_deg"], sh["theta_v0_deg"]
    assert model_h > 12.0 and model_v < 6.0
    err_c = max(abs(coarse["mesh_halfangle_h_deg"] - model_h),
                abs(coarse["mesh_halfangle_v_deg"] - model_v))
    err_f = max(abs(fine["mesh_halfangle_h_deg"] - model_h),
                abs(fine["mesh_halfangle_v_deg"] - model_v))
    assert err_f < err_c
    # azimuth refinement must not move the wall field (the section is analytic, not sampled radially)
    base_pts = H.make_grid(sh, BRIEF)[0]
    wide = H.make_grid(dict(sh, n_phi=37), BRIEF)[0]
    assert np.array_equal(wide[0], base_pts[0]) and np.array_equal(wide[-1], base_pts[-1])


def test_deterministic_and_validated():
    a = H.make_grid(shape("a1"), BRIEF)[0]
    b = H.make_grid(copy.deepcopy(shape("a1")), BRIEF)[0]
    assert hashlib.sha256(a.tobytes()).hexdigest() == hashlib.sha256(b.tobytes()).hexdigest()
    for bad in (dict(shape("a1"), cd_core_blend=1.5), dict(shape("a1"), core_join_fraction=0.01),
                dict(shape("a1"), theta_h0_deg=40.0), dict(shape("a1"), bogus=1)):
        with pytest.raises(ValueError):
            H.validate_shape(bad)
    with pytest.raises(ValueError):
        H.validate_shape({k: v for k, v in shape("a1").items() if k != "cd_core_blend"})


def test_driver_angle_is_not_used_as_a_wall_tangent():
    other = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 12.0}}
    assert np.array_equal(H.make_grid(shape("a1"), BRIEF)[0], H.make_grid(shape("a1"), other)[0])
    assert H.make_grid(shape("a1"), other)[1]["angle_provenance"] == "assumed_legacy"
