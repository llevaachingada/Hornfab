"""WP9b rows machinery in ``design/generators/grid.py`` (dossier section 2.4 ship bar).

Pure tests (no mesher): P1-P5 are the checkable properties of the per-azimuth
``spherical_salmon`` rows and the T5 X-shape modulation.  Offline, CPU only.

P3 interpretation (stated here because it is easy to misread): the base cross-section is
an ELLIPSE with fc_h != fc_v, so the quarter is mirror-symmetric about the cardinal planes
(x=0, y=0) but NOT about the 45-degree diagonal.  The exact symmetry of this family is
H<->V transposition: row phi of (fc_h, fc_v) equals row 90-phi of (fc_v, fc_h) after
swapping x and y.  The T5 term cos(4(phi-45)) IS even under phi -> 90-phi, and with
fc_h == fc_v the rows match directly.  Both are proven below.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry
from hornlab_search.types import Design

R0_MM = 12.7
A0_DEG = 5.0
T = 0.8
FC_H = 800.0
FC_V = 1100.0
STOP = 140.0
N_PHI = 15
N_S = 32

BRIEF = {
    "driver": {"exit_radius_mm": R0_MM, "exit_angle_deg": A0_DEG},
    "envelope": {"max_mouth_w_mm": 520.0, "max_mouth_h_mm": 420.0, "max_depth_mm": 260.0},
}


def spec(kind: str = "salmon_elliptical", **extra) -> dict:
    out = {"name": "grid", "rows": {"type": kind}, "n_phi": N_PHI, "n_s": N_S,
           "wall_thickness_mm": 3.0}
    out.update(extra)
    return out


def knobs(**extra) -> dict:
    out = {"g_fc_h_hz": FC_H, "g_fc_v_hz": FC_V, "g_T": T, "g_stop_deg": STOP,
           "g_x_amp": 0.0, "g_x_fc": 0.0}
    out.update(extra)
    return out


def row_profiles(grid):
    return [(grid[i, :, 2].copy(), np.hypot(grid[i, :, 0], grid[i, :, 1])) for i in range(grid.shape[0])]


# ------------------------------------------------------------------ P1


def test_p1_equal_fc_rows_equal_the_single_axisymmetric_march():
    xs, ys, _th, _areas, _m = P.salmon_march_core(R0_MM, FC_H, T, A0_DEG, STOP)
    axisym, axisym_meta = G.rows_axisym((xs, ys), N_PHI, n_s=N_S,
                                        source_auto_angle_deg=A0_DEG)
    rows, meta = G.rows_per_azimuth(spec(), knobs(g_fc_v_hz=FC_H), BRIEF)
    assert rows.shape == axisym.shape == (N_PHI, N_S + 1, 3)
    assert np.abs(rows - axisym).max() <= 1e-9
    # every row carries the same meridian at its own azimuth
    base = row_profiles(axisym)[0]
    for i, (xr, yr) in enumerate(row_profiles(rows)):
        assert np.abs(xr - base[0]).max() <= 1e-9
        assert np.abs(yr - base[1]).max() <= 1e-9
    assert meta["rows_type"] == "salmon_elliptical"
    assert axisym_meta["rows_type"] == "axisym"


# ------------------------------------------------------------------ P2


def test_p2_x_amp_zero_reproduces_the_elliptical_rows_exactly():
    plain, _ = G.rows_per_azimuth(spec(), knobs(), BRIEF)
    # x_fc is nonzero here on purpose: it is gated on x_amp > 0, so P2 still holds.
    x_zero, meta = G.rows_per_azimuth(spec(), knobs(g_x_amp=0.0, g_x_fc=0.15), BRIEF)
    assert np.abs(x_zero - plain).max() <= 1e-9
    assert meta["x_amp"] == 0.0 and meta["x_fc"] == pytest.approx(0.15)
    # the modulation helper itself says fc_scale == 1 when x_amp == 0
    _stop, scale = G.x_shape_modulation(STOP, 0.0, 0.15, np.linspace(0.0, 0.5 * math.pi, N_PHI))
    assert np.allclose(scale, 1.0, rtol=0.0, atol=0.0)

    # a nonzero x_amp does change the rows (sanity: P2 is not vacuous)
    x_on, _ = G.rows_per_azimuth(spec(), knobs(g_x_amp=0.25, g_x_fc=0.15), BRIEF)
    assert np.abs(x_on - plain).max() > 1.0


# ------------------------------------------------------------------ P3


def test_p3_x_shape_modulation_is_even_under_phi_to_90_minus_phi():
    phis = np.linspace(0.0, 0.5 * math.pi, N_PHI)
    stop, scale = G.x_shape_modulation(STOP, 0.25, 0.15, phis)
    stop, scale = np.asarray(stop), np.asarray(scale)
    np.testing.assert_allclose(stop, stop[::-1], rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(scale, scale[::-1], rtol=0.0, atol=1e-12)
    # maxima on the quarter diagonal, minima on the cardinal planes (T5 verbatim)
    mid = N_PHI // 2
    assert stop[mid] > stop[0] and stop[mid] > stop[-1]


def test_p3_x_shape_rows_mirror_directly_when_fc_h_equals_fc_v():
    grid, _ = G.rows_per_azimuth(spec(), knobs(g_fc_v_hz=FC_H, g_x_amp=0.25, g_x_fc=0.15),
                                 BRIEF)
    prof = row_profiles(grid)
    for i in range(N_PHI):
        xi, yi = prof[i]
        xj, yj = prof[N_PHI - 1 - i]
        assert np.abs(xi - xj).max() <= 1e-9
        assert np.abs(yi - yj).max() <= 1e-9


def test_p3_elliptical_family_is_hv_transpose_symmetric():
    """Row phi of (fc_h, fc_v) == row 90-phi of (fc_v, fc_h) after swapping x and y."""
    a, _ = G.rows_per_azimuth(spec(), knobs(), BRIEF)
    b, _ = G.rows_per_azimuth(spec(), knobs(g_fc_h_hz=FC_V, g_fc_v_hz=FC_H), BRIEF)
    for i in range(N_PHI):
        ai = a[i, :, :].copy()
        bi = b[N_PHI - 1 - i, :, :].copy()
        swapped = ai[:, [1, 0, 2]]
        assert np.abs(swapped - bi).max() <= 1e-9


def test_p3_x_shape_rows_are_hv_transpose_symmetric_too():
    a, _ = G.rows_per_azimuth(spec(), knobs(g_x_amp=0.25, g_x_fc=0.15), BRIEF)
    b, _ = G.rows_per_azimuth(
        spec(), knobs(g_fc_h_hz=FC_V, g_fc_v_hz=FC_H, g_x_amp=0.25, g_x_fc=0.15), BRIEF)
    prof_a, prof_b = row_profiles(a), row_profiles(b)
    for i in range(N_PHI):
        assert np.abs(prof_a[i][0] - prof_b[N_PHI - 1 - i][0]).max() <= 1e-9
        assert np.abs(prof_a[i][1] - prof_b[N_PHI - 1 - i][1]).max() <= 1e-9


# ------------------------------------------------------------------ P4


def test_p4_self_approach_guard_refuses_a_folded_rows_like_shell():
    t = 3.0
    theta = np.linspace(0.0, 1.5 * math.pi, N_S + 1)     # 270 deg arc, radius 3 mm
    rho = 10.0 + 3.0 * np.cos(theta)
    z = 3.0 * np.sin(theta)
    phis = np.linspace(0.0, 0.5 * math.pi, N_PHI)
    curled = np.stack([np.stack([rho * math.cos(p), rho * math.sin(p), z], axis=-1)
                       for p in phis])
    assert G.min_self_approach_mm(curled, limit_mm=2 * t + 2) < 2 * t + 2
    with pytest.raises(registry.GeneratorError, match="self-approach"):
        G.grid_outer_points(curled, t)


def test_p4_seed_self_approach_is_above_the_refusal_limit():
    grid, meta = G.rows_per_azimuth(spec(), knobs(), BRIEF)
    outer = G.grid_outer_points(grid, 3.0)
    limit = 2.0 * 3.0 + G.SELF_APPROACH_MARGIN_MM
    assert meta["min_self_approach_mm"] >= limit
    assert G.min_self_approach_mm(grid, outer, limit_mm=limit) >= limit
    assert meta["min_cross_row_distance_mm"] == pytest.approx(
        meta["min_cross_row_distance_mm"])                     # finite, report-only
    assert "REPORT ONLY" in meta["min_cross_row_distance_scope"]


# ------------------------------------------------------------------ P5


def test_p5_arc_resampling_keeps_endpoints_exactly():
    xs, ys, _th, _areas, _m = P.salmon_march_core(R0_MM, FC_H, T, A0_DEG, STOP)
    grid, meta = G.rows_axisym((xs, ys), N_PHI, n_s=N_S)
    phis = np.linspace(0.0, 0.5 * math.pi, N_PHI)
    for i, phi in enumerate(phis):
        assert grid[i, 0, 2] == xs[0]
        assert grid[i, 0, 0] == pytest.approx(ys[0] * math.cos(phi), abs=1e-12)
        assert grid[i, -1, 2] == xs[-1]
        assert np.hypot(grid[i, -1, 0], grid[i, -1, 1]) == pytest.approx(ys[-1], abs=1e-12)
        # every resampled station lies on the original march polyline (arc resampling)
        xr = grid[i, :, 2]
        yr = np.hypot(grid[i, :, 0], grid[i, :, 1])
        for xq, yq in zip(xr, yr):
            seg = np.hypot(xs[1:] - xs[:-1], ys[1:] - ys[:-1])
            t = np.clip(((xq - xs[:-1]) * (xs[1:] - xs[:-1])
                         + (yq - ys[:-1]) * (ys[1:] - ys[:-1])) / np.maximum(seg ** 2, 1e-30),
                        0.0, 1.0)
            dist = np.hypot(xq - (xs[:-1] + t * (xs[1:] - xs[:-1])),
                            yq - (ys[:-1] + t * (ys[1:] - ys[:-1])))
            assert dist.min() <= 1e-9
    # both quarter endpoints sit on the mirror planes exactly
    assert np.all(grid[0, :, 1] == 0.0) and np.all(grid[-1, :, 0] == 0.0)
    assert meta["quarter"] is True and meta["n_phi"] == N_PHI


# ------------------------------------------------------------------ contract / validation


def test_rows_params_carry_the_recipe_and_do_not_require_l_mm():
    params = G.design_params(spec(), knobs(), BRIEF)
    block = params["grid"]
    assert set(block) == set(G.ROWS_BLOCK_KEYS)
    assert block["rows"] == {"type": "salmon_elliptical"}
    assert "L_mm" not in block and "L_mm" not in block["knobs"]   # march derives length
    json.dumps(params)                                           # no arrays / numpy scalars
    families.validate(Design("FREEFORM", params))
    G.validate_grid_params(block)
    # provenance label travels with the recipe
    _grid, meta = G.rows_grid_points({k: v for k, v in block.items() if k != "knobs"},
                                     block["knobs"], BRIEF)
    assert "LABELED HYPOTHESIS-SHAPE EXPERIMENT" in meta["hypothesis_label"]
    assert meta["rows_type"] == "salmon_elliptical"
    assert len(meta["rows"]) == N_PHI and "mouth_y_mm" in meta["rows"][0]


@pytest.mark.parametrize("bad, match", [
    ({"rows": {"type": "bogus"}}, "unknown rows type"),
    ({"rows": {"type": "salmon_elliptical", "extra": 1}}, "unknown key"),
    ({"profile_h": {"type": "conical"}}, "unknown key"),
    ({"n_phi": 12}, "n_phi"),
    ({"n_s": 4}, "n_s"),
    ({"wall_thickness_mm": 20.0}, "wall_thickness_mm"),
])
def test_validate_rows_rejects_foreign_or_illegal_blocks(bad, match):
    block = {**G.design_params(spec(), knobs(), BRIEF)["grid"]}
    block.update(bad)
    with pytest.raises(registry.GeneratorError, match=match):
        G.validate_grid_params(block)


@pytest.mark.parametrize("bad, match", [
    ({"g_stop_deg": 180.0}, "asymptote"),
    ({"g_stop_deg": 400.0}, "stop_deg"),
    ({"g_x_amp": 0.5}, "x_amp"),
    ({"g_x_fc": 0.4}, "x_fc"),
    ({"g_fc_h_hz": 0.0}, "fc_h_hz"),
])
def test_rows_knob_bounds_are_refused(bad, match):
    with pytest.raises(registry.GeneratorError, match=match):
        G.rows_per_azimuth(spec(), knobs(**bad), BRIEF)


def test_rows_envelope_extents_are_conservative_and_track_the_mouth():
    spec_ = spec()
    k = knobs()
    w, h, d = G.envelope_extents(spec_, k, BRIEF)
    grid, meta = G.rows_grid_points(spec_, k, BRIEF)
    assert w >= 2.0 * meta["mouth_radius_h_mm"]
    assert h >= 2.0 * meta["mouth_radius_v_mm"]
    assert d >= meta["x_span_mm"]
    assert (w, h, d) == pytest.approx(G._rows_envelope_extents(spec_, k, BRIEF))
    # the example seeds fit the brief envelope
    assert w <= BRIEF["envelope"]["max_mouth_w_mm"]
    assert h <= BRIEF["envelope"]["max_mouth_h_mm"]
    assert d <= BRIEF["envelope"]["max_depth_mm"]


def test_example_configs_load_as_grid_rows_spaces():
    from hornlab_search.design.generated import GeneratedSpace
    from hornlab_search.design.space import DesignSpace

    for name, expected_keys in (
        ("salmon_elliptical", {"g_fc_h_hz", "g_fc_v_hz", "g_T", "g_stop_deg"}),
        ("salmon_x_shape", {"g_fc_h_hz", "g_fc_v_hz", "g_T", "g_stop_deg",
                            "g_x_amp", "g_x_fc"}),
    ):
        cfg = load_config(EXAMPLES / "typologies" / f"{name}.yaml")
        space = DesignSpace.from_config(cfg)
        assert isinstance(space, GeneratedSpace)
        assert set(space.keys()) == expected_keys
        assert space.seed.params["grid"]["rows"]["type"] == "salmon_elliptical"
        families.validate(space.seed)
        assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
