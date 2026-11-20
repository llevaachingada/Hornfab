"""Split-plane OS-SE knobs ``g_k_v`` / ``g_s_v`` on ``rows: {type: osse_rollback}`` (P1, 2026-11-20).

Checkable properties from docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md s2 P1:
absent keys are byte-identical; k_v = k and s_v = s reproduce the parent; the H row (phi 0) never moves;
the V row equals the parent law evaluated with (k_v, s_v); every row starts at the round coupling r0.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("hornlab_mesher")

from hornlab_search.design.generators import grid  # noqa: E402
from hornlab_search.design.generators.registry import GeneratorError  # noqa: E402

SPEC = {"name": "grid", "rows": {"type": "osse_rollback"}, "n_phi": 25, "n_s": 40,
        "wall_thickness_mm": 3.0, "span": "quarter"}
BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}}
# FAV-001 (design 4140768780f0, runs/20261120T084006Z-screen-fc4e18) knobs, rounded.
FAV = {"g_L_mm": 260.313, "g_a_h_deg": 34.893, "g_a_v_deg": 26.757, "g_k": 1.0, "g_n": 2.5627,
       "g_q": 0.996, "g_r_lip_mm": 18.214, "g_s": 0.43706, "g_sf_ab": 0.83076, "g_sf_amt": 0.18804,
       "g_sf_m": 4.0, "g_sf_n1": 1.8, "g_sf_n2": 7.0, "g_sf_start": 0.25, "g_wrap_deg": 81.39}


def _pts(knobs):
    return grid.rows_grid_points(SPEC, knobs, BRIEF)


def test_absent_split_keys_leave_meta_unchanged():
    _, meta = _pts(FAV)
    assert "split_plane" not in meta
    assert "k_v" not in meta and "s_v" not in meta


def test_equal_split_values_reproduce_parent_exactly():
    p0, _ = _pts(FAV)
    p1, meta = _pts({**FAV, "g_k_v": FAV["g_k"], "g_s_v": FAV["g_s"]})
    np.testing.assert_allclose(p0, p1, atol=1e-9)        # cos^2 + sin^2 rounds at 1 ulp, not exactly 1
    assert meta["split_plane"] == {"k_v": FAV["g_k"], "s_v": FAV["g_s"]}


def test_h_row_never_moves():
    p0, _ = _pts(FAV)
    p1, _ = _pts({**FAV, "g_k_v": 3.0, "g_s_v": 0.30})
    np.testing.assert_array_equal(p0[0], p1[0])          # phi = 0 row (H plane)
    assert not np.allclose(p0[-1], p1[-1])               # V row did change


def test_v_row_equals_parent_law_with_v_values():
    p_split, _ = _pts({**FAV, "g_k_v": 3.0, "g_s_v": 0.30})
    p_parent, _ = _pts({**FAV, "g_k": 3.0, "g_s": 0.30})
    np.testing.assert_allclose(p_split[-1], p_parent[-1], atol=1e-9)   # phi = 90 deg row


def test_every_row_starts_at_round_coupling():
    pts, meta = _pts({**FAV, "g_k_v": 4.0, "g_s_v": 0.2})
    r_start = np.hypot(pts[:, 0, 0], pts[:, 0, 1])
    np.testing.assert_allclose(r_start, meta["throat_radius_mm"], atol=1e-9)


@pytest.mark.parametrize("bad", [{"g_k_v": 0.0}, {"g_k_v": -1.0}, {"g_s_v": -0.1},
                                 {"g_k_v": float("nan")}])
def test_illegal_values_refused(bad):
    with pytest.raises(GeneratorError):
        _pts({**FAV, **bad})


def test_k_v_and_throat_hv_ratio_are_exclusive():
    with pytest.raises(GeneratorError, match="two per-azimuth k laws"):
        _pts({**FAV, "g_k_v": 2.0, "g_throat_hv_ratio": 2.0})


# --- SplitCore variant (owner fixture HornFab_SplitCore_Analytic_Reference_Fixture.py, 2026-11-20) ---

def test_log_k_interpolation_matches_fixture_at_45deg():
    import math
    k_h, k_v = 1.0, 3.0
    c2 = s2 = 0.5
    assert math.exp(c2 * math.log(k_h) + s2 * math.log(k_v)) == pytest.approx(math.sqrt(3.0), abs=1e-14)
    p_lin, _ = _pts({**FAV, "g_k_v": 3.0})
    p_log, meta = _pts({**FAV, "g_k_v": 3.0, "g_k_v_log": 1.0})
    np.testing.assert_array_equal(p_lin[0], p_log[0])                      # H row: k_h either way
    np.testing.assert_allclose(p_lin[-1], p_log[-1], atol=1e-9)            # V row: k_v either way
    assert not np.allclose(p_lin[12], p_log[12])                           # diagonal differs
    assert meta["split_plane"]["k_v_log"] == 1.0


def test_v_exp_blend_keeps_h_row_and_rejoins_base_beyond_le():
    # The output grid is arc-length resampled and the superformula window is arc-fraction based, so compare
    # the V meridian r(z) by interpolation with the morph off (sf_amt 0) instead of station by station.
    plain = {**FAV, "g_sf_amt": 0.0, "g_sf_m": 0.0, "g_k_v": 3.0}
    base, _ = _pts(plain)
    new, _ = _pts({**plain, "g_v_exp_mm": 50.0})
    np.testing.assert_array_equal(base[0], new[0])                         # H meridian untouched
    zb, rb = base[-1][:, 2], base[-1][:, 1]
    zn, rn = new[-1][:, 2], new[-1][:, 1]
    mono = np.argmax(zb)                                                   # before the lip rolls back
    probe = np.linspace(55.0, 0.9 * zb[mono], 20)
    np.testing.assert_allclose(np.interp(probe, zn[:mono + 1], rn[:mono + 1]),
                               np.interp(probe, zb[:mono + 1], rb[:mono + 1]), atol=0.2)   # 0.2 mm fidelity rule
    inside = np.linspace(5.0, 45.0, 9)
    assert np.all(np.interp(inside, zn, rn) < np.interp(inside, zb, rb))  # slower V throat inside L_e
    np.testing.assert_allclose(np.hypot(new[:, 0, 0], new[:, 0, 1]), 18.0, atol=1e-9)


@pytest.mark.parametrize("bad", [{"g_k_v_log": 1.0}, {"g_k_v": 2.0, "g_k_v_log": 0.5},
                                 {"g_v_exp_mm": -1.0}, {"g_v_exp_mm": 500.0}])
def test_splitcore_illegal_values_refused(bad):
    with pytest.raises(GeneratorError):
        _pts({**FAV, **bad})


# --- Ridge (radial diagonal angle) + beak (axial lip offset), 2026-11-20 ---

def test_ridge_beak_absent_leaves_meta_unchanged():
    _, meta = _pts(FAV)
    assert "ridge_beak" not in meta


def test_diagonal_ridge_opens_only_the_diagonal_angle():
    _, m0 = _pts(FAV)
    p1, m1 = _pts({**FAV, "g_a_d_deg": 8.0})
    a0, a1 = np.array(m0["row_a_deg"]), np.array(m1["row_a_deg"])
    assert a1[0] == pytest.approx(a0[0], abs=1e-9) and a1[-1] == pytest.approx(a0[-1], abs=1e-9)
    assert a1[12] - a0[12] == pytest.approx(8.0, abs=1e-6)            # phi = 45 deg: full +a_d
    assert m1["ridge_beak"] == {"a_d_deg": 8.0}


def test_beak_moves_only_axially_after_start():
    plain = {**FAV, "g_sf_amt": 0.0, "g_sf_m": 0.0, "g_wrap_deg": 0.0, "g_r_lip_mm": 0.0}
    p0, _ = _pts(plain)
    p1, _ = _pts({**plain, "g_beak_h_mm": 20.0, "g_beak_v_mm": -10.0, "g_beak_start": 0.6})
    np.testing.assert_allclose(p1[:, 0], p0[:, 0], atol=1e-9)        # first station (throat) unchanged
    zmax0, zmax1 = p0[:, :, 2].max(axis=1), p1[:, :, 2].max(axis=1)
    assert zmax1[0] - zmax0[0] == pytest.approx(20.0, abs=0.5)       # H lip projects forward 20 mm
    assert zmax1[-1] - zmax0[-1] == pytest.approx(-10.0, abs=0.5)    # V lip sets back 10 mm


@pytest.mark.parametrize("bad", [{"g_a_d_deg": 40.0}, {"g_beak_start": 0.5}, {"g_beak_h_mm": 99.0}])
def test_ridge_beak_illegal_values_refused(bad):
    with pytest.raises(GeneratorError):
        _pts({**FAV, **bad})
