"""rows type ``osse_rollback`` (owner-directed hybrid 2026-10-28): per-azimuth OS/OSSE wall (Magnus's
profile_points) + the even-lobe flute ripple + the tangent-continuous curled lip. Offline, CPU only.

Pinned: the coupling plane (first station of every row) is round at the driver exit radius; the flutes
are absent until the ripple window opens; with no ripple and no lip every row IS the OSSE wall; the lip
adds ``wrap_deg`` of turning and, with ``wrap_cos_amp``, the wrap follows cos(N phi); illegal knobs are
refused; the persisted block validates.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("hornlab_mesher")

from hornlab_search.design.generators import grid, registry  # noqa: E402

BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0},
         "envelope": {"max_mouth_w_mm": 740.0, "max_mouth_h_mm": 740.0, "max_depth_mm": 650.0}}
SPEC = {"rows": {"type": "osse_rollback"}, "n_phi": 25, "n_s": 40, "wall_thickness_mm": 3.0,
        "span": "quarter"}
SEED = {"g_a_h_deg": 45.0, "g_a_v_deg": 45.0, "g_k": 1.0, "g_L_mm": 200.0, "g_r_lip_mm": 40.0,
        "g_wrap_deg": 120.0, "g_ripple_lobes": 10, "g_ripple_amp_mm": 14.0, "g_ripple_start": 0.35}


def marches(knobs=None, spec=None):
    return grid._rows_marches(spec or SPEC, {**SEED, **(knobs or {})}, BRIEF)


def test_coupling_plane_is_round_and_flutes_start_in_the_window():
    ms = marches()
    starts = [(m["x"][0], m["y"][0]) for m in ms]
    assert all(x == pytest.approx(0.0) and y == pytest.approx(18.0, abs=1e-6) for x, y in starts)
    # rows at phi = 0 and phi = pi/10 (flute crest vs trough for N = 10) agree before the window
    a, b = ms[0], ms[4]                     # quarter span, 25 rows: row 4 is phi = 15 deg (N phi = 150)
    n_pre = 60                              # well inside the first 35 % of the arc
    np.testing.assert_allclose(a["y"][:n_pre], b["y"][:n_pre], rtol=1e-9)


def test_without_ripple_or_lip_each_row_is_the_osse_wall():
    from hornlab_mesher.profile_formulas import profile_points
    ms = marches({"g_ripple_lobes": 0, "g_ripple_amp_mm": 0.0, "g_ripple_start": 0.0, "g_r_lip_mm": 0.0})
    prm = {"type": "OSSE", "r0": 18.0, "a0": 2.0, "L": 200.0, "a": 45.0, "k": 1.0, "s": 0.0, "n": 4.0,
           "q": 0.996}
    ref = np.asarray(profile_points(prm, grid.ROWS_OSSE_ROLL_SAMPLES, 0.0), dtype=float)
    np.testing.assert_allclose(ms[0]["y"], ref[:, 1], rtol=1e-12)
    np.testing.assert_allclose(ms[0]["x"], ref[:, 0] - ref[0, 0], rtol=1e-12, atol=1e-12)


def test_lip_turns_by_wrap_and_wrap_can_follow_the_flutes():
    ms = marches()
    for m in ms:
        assert m["march"]["stop_deg"] - m["march"]["wall_end_deg"] == pytest.approx(120.0)
    ruf = marches({"g_wrap_cos_amp": 0.3})
    phi = np.array([m["phi"] for m in ruf])
    turn = np.array([m["march"]["stop_deg"] - m["march"]["wall_end_deg"] for m in ruf])
    np.testing.assert_allclose(turn, 120.0 * (1.0 + 0.3 * np.cos(10 * phi)), rtol=1e-12)


@pytest.mark.parametrize("bad, msg", [
    ({"g_a_h_deg": 90.0}, "a_h_deg"),
    ({"g_wrap_deg": 250.0}, "wrap_deg"),
    ({"g_wrap_cos_amp": 0.3, "g_ripple_lobes": 0, "g_ripple_amp_mm": 0.0}, "wrap_cos_amp"),
    ({"g_ripple_lobes": 9}, "EVEN"),
    ({"g_x_amp": 0.1}, "foreign"),
])
def test_illegal_knobs_are_refused(bad, msg):
    with pytest.raises(registry.GeneratorError, match=msg):
        marches(bad)


def test_grid_points_and_persisted_block_validate():
    pts, meta = grid.rows_grid_points(SPEC, SEED, BRIEF)
    assert meta["rows_type"] == "osse_rollback" and meta["ripple_lobes"] == 10
    assert meta["throat_radius_mm"] == pytest.approx(18.0, abs=1e-6)
    assert np.all(np.isfinite(pts))
    params = grid.design_params(SPEC, SEED, BRIEF)
    grid.validate_grid_params(params["grid"])
    assert math.isfinite(meta["mouth_w_mm"]) and meta["mouth_w_mm"] > 2 * 18.0


SF_X = {"g_ripple_lobes": 0, "g_ripple_amp_mm": 0.0, "g_ripple_start": 0.0,
        "g_sf_m": 4, "g_sf_n1": 1.2, "g_sf_n2": 8.0, "g_sf_amt": 0.75, "g_sf_start": 0.3}


def test_superformula_x_points_on_the_diagonals_and_starts_round():
    ms = marches(SF_X)
    phi = np.array([m["phi"] for m in ms])
    i0, i45 = int(np.argmin(np.abs(phi))), int(np.argmin(np.abs(phi - math.pi / 4)))
    assert ms[i45]["y"].max() > 1.5 * ms[i0]["y"].max()          # the X arm reaches far past the axis
    assert all(m["y"][0] == pytest.approx(18.0, abs=1e-6) for m in ms)  # coupling plane stays round
    np.testing.assert_allclose(ms[i0]["y"][:60], ms[i45]["y"][:60], rtol=1e-9)  # no morph before sf_start


def test_superformula_stretch_makes_a_tall_mouth():
    k = {**SF_X, "g_sf_n1": 2.0, "g_sf_n2": 2.0, "g_sf_ab": 2.5, "g_sf_amt": 1.0}
    _pts, meta = grid.rows_grid_points(SPEC, {**SEED, **k}, BRIEF)
    assert meta["mouth_h_mm"] > 1.4 * meta["mouth_w_mm"]


@pytest.mark.parametrize("bad, msg", [
    ({"g_sf_m": 5}, "EVEN"),
    ({"g_sf_m": 6, "g_sf_ab": 2.0}, "multiple of 4"),
    ({"g_sf_m": 0, "g_sf_amt": 0.5}, "needs sf_m"),
])
def test_superformula_refusals(bad, msg):
    with pytest.raises(registry.GeneratorError, match=msg):
        marches({**SF_X, **bad})
