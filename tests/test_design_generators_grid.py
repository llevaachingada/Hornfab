"""Pure (no mesher) tests for the GRID radius field, design/generators/grid.py.

Everything here is analytic: the checks are the closed forms from Report 2 section 4 /
``docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md`` section 2.4.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry

R0_MM = 5.0
A0_DEG = 8.0
L_MM = 60.0
RM_H_MM = 25.0
RM_V_MM = 15.0
N_PHI = 13
N_S = 32

BRIEF = {
    "driver": {"exit_radius_mm": R0_MM, "exit_angle_deg": A0_DEG},
    "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
}


def spec(**extra) -> dict:
    """Conical H/V meridians at different mouth radii -> a true ellipse cross-section."""
    out = {"name": "grid", "profile_h": {"type": "conical"},
           "profile_v": {"type": "conical"}, "n_phi": N_PHI, "n_s": N_S,
           "max_wall_deg": 80.0, "wall_thickness_mm": 3.0}
    out.update(extra)
    return out


def knobs(**extra) -> dict:
    out = {"L_mm": L_MM, "h_rm_mm": RM_H_MM, "v_rm_mm": RM_V_MM}
    out.update(extra)
    return out


def meridians():
    mh = registry.build_meridian(spec()["profile_h"], knobs(), "h", r0=R0_MM, a0=A0_DEG,
                                 L=L_MM, max_wall=80.0, phi=0.0)
    mv = registry.build_meridian(spec()["profile_v"], knobs(), "v", r0=R0_MM, a0=A0_DEG,
                                 L=L_MM, max_wall=80.0, phi=math.pi / 2.0)
    z = np.linspace(0.0, 1.0, N_S + 1) * L_MM
    return z, np.interp(z, mh.z_mm, mh.r_mm), np.interp(z, mv.z_mm, mv.r_mm)


def phi_grid():
    return np.linspace(0.0, 0.5 * math.pi, N_PHI)


def radius(grid):
    return np.hypot(grid[..., 0], grid[..., 1])


# ------------------------------------------------------------------ the radius field


def test_ellipse_closed_form_at_pnorm_2_with_zero_modulation():
    """pnorm=2, every a_k=0, term_side=0: r = r_H r_V / sqrt((r_V cos)^2 + (r_H sin)^2)."""
    inner, meta = G.grid_points(spec(), knobs(), BRIEF)
    z, r_h, r_v = meridians()
    phi = phi_grid()
    expected = (r_h[None, :] * r_v[None, :]) / np.sqrt(
        (r_v[None, :] * np.cos(phi)[:, None]) ** 2
        + (r_h[None, :] * np.sin(phi)[:, None]) ** 2)
    assert inner.shape == (N_PHI, N_S + 1, 3)
    assert np.allclose(radius(inner), expected, rtol=0.0, atol=1e-9)
    # endpoint meridians are exactly the two half-plane radii
    assert np.allclose(radius(inner)[0, :], r_h, rtol=0.0, atol=1e-9)
    assert np.allclose(radius(inner)[-1, :], r_v, rtol=0.0, atol=1e-9)
    assert meta["pnorm"] == 2.0
    assert meta["mouth_radius_h_mm"] == pytest.approx(RM_H_MM, abs=1e-9)
    assert meta["mouth_radius_v_mm"] == pytest.approx(RM_V_MM, abs=1e-9)
    assert meta["L_mm"] == pytest.approx(L_MM)
    assert meta["a_k"] == {1: {"throat": 0.0, "mouth": 0.0}, 2: {"throat": 0.0, "mouth": 0.0}}


def test_superellipse_closed_form_at_pnorm_4():
    inner, meta = G.grid_points(spec(), knobs(g_pnorm=4.0), BRIEF)
    z, r_h, r_v = meridians()
    phi = phi_grid()
    p = 4.0
    expected = (r_h[None, :] * r_v[None, :]) / (
        (np.abs(r_v[None, :] * np.cos(phi)[:, None]) ** p
         + np.abs(r_h[None, :] * np.sin(phi)[:, None]) ** p) ** (1.0 / p))
    assert np.allclose(radius(inner), expected, rtol=0.0, atol=1e-9)
    assert meta["pnorm"] == 4.0
    # p=4 is fatter than p=2 off the axes (superellipse, not ellipse)
    inner2, _ = G.grid_points(spec(), knobs(), BRIEF)
    mid = N_PHI // 2
    assert radius(inner)[mid, -1] > radius(inner2)[mid, -1]


def test_zero_modulation_adds_nothing():
    base, _ = G.grid_points(spec(), knobs(), BRIEF)
    zero, meta = G.grid_points(spec(), knobs(g_a1_throat=0.0, g_a1_mouth=0.0,
                                             g_a2_throat=0.0, g_a2_mouth=0.0), BRIEF)
    assert np.array_equal(base, zero)
    assert meta["fourier_k"] == 2


def test_fourier_mouth_knob_scales_the_mouth_and_throat_knob_is_at_the_throat():
    a1_mouth = 0.1
    inner, meta = G.grid_points(spec(), knobs(g_a1_mouth=a1_mouth), BRIEF)
    base, _ = G.grid_points(spec(), knobs(), BRIEF)
    phi = phi_grid()
    factor = 1.0 + a1_mouth * np.cos(2.0 * phi)
    assert np.allclose(radius(inner)[:, -1] / radius(base)[:, -1], factor, rtol=0.0, atol=1e-12)
    # a_k(0) = a_k_throat = 0 for this knob -> the throat circle is untouched
    assert np.allclose(radius(inner)[:, 0], radius(base)[:, 0], rtol=0.0, atol=1e-12)
    assert meta["a_k"][1] == {"throat": 0.0, "mouth": a1_mouth}

    a1_throat = 0.2
    inner_t, meta_t = G.grid_points(spec(), knobs(g_a1_throat=a1_throat,
                                                  g_a1_mouth=a1_mouth), BRIEF)
    throat_factor = 1.0 + a1_throat * np.cos(2.0 * phi)
    assert np.allclose(radius(inner_t)[:, 0] / radius(base)[:, 0], throat_factor,
                       rtol=0.0, atol=1e-12)
    assert meta_t["a_k"][1]["throat"] == a1_throat


def test_term_side_rolls_the_sides_back_with_smoothstep_weight():
    term = 10.0
    base, _ = G.grid_points(spec(), knobs(), BRIEF)
    rolled, meta = G.grid_points(spec(), knobs(g_term_side_mm=term), BRIEF)
    phi = phi_grid()
    s = np.linspace(0.0, 1.0, N_S + 1)
    w = 3.0 * s ** 2 - 2.0 * s ** 3
    assert w[0] == 0.0 and w[N_S // 2] == pytest.approx(0.5) and w[-1] == 1.0
    # smoothstep at the stations used by the grid (n_s=32 -> s=0.5 lands on station 16)
    dz = rolled[..., 2] - base[..., 2]
    expected = -term * np.cos(phi)[:, None] ** 2 * w[None, :]
    assert np.allclose(dz, expected, rtol=0.0, atol=1e-12)
    # sign convention: rollback = NEGATIVE z at the sides (phi=0), zero at top/bottom (phi=90)
    assert rolled[0, -1, 2] == pytest.approx(L_MM - term, abs=1e-12)
    assert rolled[-1, -1, 2] == pytest.approx(L_MM, abs=1e-12)
    assert rolled[0, 0, 2] == 0.0 and rolled[-1, 0, 2] == 0.0
    assert meta["term_side_mm"] == -term


def test_quarter_endpoint_rows_sit_exactly_on_the_mirror_planes():
    inner, meta = G.grid_points(spec(), knobs(g_a1_mouth=0.15, g_a2_throat=0.05), BRIEF)
    assert np.all(inner[0, :, 1] == 0.0)          # phi=0 row: y == 0 (xz plane)
    assert np.all(inner[-1, :, 0] == 0.0)         # phi=90 row: x == 0 (yz plane)
    assert np.all(inner[..., 0] >= 0.0) and np.all(inner[..., 1] >= 0.0)
    assert meta["quarter"] is True and meta["n_phi"] == N_PHI


def test_meta_is_json_serialisable_and_has_no_arrays():
    _, meta = G.grid_points(spec(), knobs(g_term_side_mm=4.0, g_a1_mouth=0.1), BRIEF)
    json.dumps(meta)                                # no numpy arrays inside
    assert meta["source_auto_angle_deg"] == pytest.approx(
        math.degrees(math.atan((RM_H_MM - R0_MM) / L_MM)), abs=1e-9)
    assert isinstance(meta["sign_conventions"], dict)
    assert meta["min_self_approach_mm"] > 0.0


# ------------------------------------------------------------------ outer shell


def test_outer_points_offset_a_flat_row_by_the_wall_thickness():
    """A flat (constant-radius) row has its normal along +rho: rho -> rho + t exactly."""
    t = 3.0
    z = np.linspace(0.0, 60.0, N_S + 1)
    rho = np.full_like(z, 10.0)
    phi = phi_grid()
    flat = np.stack([np.stack([rho * np.cos(p), rho * np.sin(p), z], axis=-1) for p in phi])
    outer = G.grid_outer_points(flat, t)
    assert outer.shape == flat.shape
    assert np.allclose(np.hypot(outer[..., 0], outer[..., 1]), 10.0 + t,
                       rtol=0.0, atol=1e-6)
    assert np.allclose(outer[..., 2], z[None, :], rtol=0.0, atol=1e-9)
    assert np.all(outer[0, :, 1] == 0.0) and np.all(outer[-1, :, 0] == 0.0)


def test_outer_points_use_the_outward_in_plane_normal_on_a_cone():
    inner, _ = G.grid_points(spec(), knobs(), BRIEF)
    t = 3.0
    outer = G.grid_outer_points(inner, t)
    alpha = math.atan((RM_H_MM - R0_MM) / L_MM)
    # outward (+rho) and rearward (-z) by t along the wall normal
    assert np.hypot(outer[0, -1, 0], outer[0, -1, 1]) == pytest.approx(
        RM_H_MM + t * math.cos(alpha), abs=1e-9)
    assert outer[0, -1, 2] == pytest.approx(L_MM - t * math.sin(alpha), abs=1e-9)
    assert G.min_self_approach_mm(inner, outer, limit_mm=2 * t + 2) >= 2 * t + 2


def test_self_approach_guard_refuses_a_folded_row():
    """A row that curls back within 2t + 2 mm of itself raises GeneratorError (dossier 2.4 P4)."""
    t = 3.0
    theta = np.linspace(0.0, 1.5 * math.pi, N_S + 1)     # 270 deg arc, radius 3 mm
    rho = 10.0 + 3.0 * np.cos(theta)
    z = 3.0 * np.sin(theta)
    phi = phi_grid()
    curled = np.stack([np.stack([rho * np.cos(p), rho * np.sin(p), z], axis=-1) for p in phi])
    gap = G.min_self_approach_mm(curled, limit_mm=2 * t + 2)
    assert gap < 2 * t + 2                                # the fixture really self-approaches
    with pytest.raises(registry.GeneratorError, match="self-approach"):
        G.grid_outer_points(curled, t)


# ------------------------------------------------------------------ refusals / unit sanity


def test_quarter_requires_at_least_13_phi_rows():
    with pytest.raises(registry.GeneratorError, match="n_phi"):
        G.grid_points(spec(n_phi=12), knobs(), BRIEF)


def test_unknown_typology_propagates_generator_error():
    with pytest.raises(registry.GeneratorError, match="unknown typology"):
        G.grid_points(spec(profile_h={"type": "bogus"}), knobs(), BRIEF)
