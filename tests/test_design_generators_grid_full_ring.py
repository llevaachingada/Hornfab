"""C2 (2026-10-25, owner-approved): signed x_amp v2 + the lecleach_asym odd-cosine
asymmetry (full ring) + the even-lobe mouth ripple ("pleats") + the full-span rows route.

Offline; the real mesher runs on the CPU only for the full-ring capability test
(no solve, no GPU). The full-ring mode is the mesher's native ``PointGridHornGeometry``
default (closed=True, symmetry planes unused); our adapter now passes it through.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace
from hornlab_search.types import Design

TYP = EXAMPLES / "typologies"
R0 = 12.7
A0 = 5.0
BRIEF = {"driver": {"exit_radius_mm": R0, "exit_angle_deg": A0},
         "envelope": {"max_mouth_w_mm": 500.0, "max_mouth_h_mm": 400.0,
                      "max_depth_mm": 300.0}}


def _spec(kind: str, **over):
    return {"rows": {"type": kind}, "n_phi": over.pop("n_phi", 15), "n_s": 32,
            **over}


# --------------------------------------------------------------- signed x (X v2)

def test_signed_x_amp_flips_the_mouth_reading():
    """+amp opens the DIAGONALS (the literal X); -amp opens the CARDINAL planes."""
    pos, _ = G.x_shape_modulation(170.0, 0.25, 0.0, 0.0)          # phi = 0 (H plane)
    diag, _ = G.x_shape_modulation(170.0, 0.25, 0.0, np.pi / 4)   # the diagonal
    neg_h, _ = G.x_shape_modulation(170.0, -0.25, 0.0, 0.0)
    neg_diag, _ = G.x_shape_modulation(170.0, -0.25, 0.0, np.pi / 4)
    assert float(diag) > float(pos)      # +: the diagonal stop is deeper (opens)
    assert float(neg_h) > float(neg_diag)   # -: the H-plane reads deeper than the diagonal


def test_signed_x_amp_rejects_over_range():
    with pytest.raises(registry.GeneratorError, match="signed"):
        G.x_shape_modulation(170.0, 0.5, 0.0, 0.0)
    with pytest.raises(registry.GeneratorError, match="signed"):
        G._rows_shape_knobs({"g_x_amp": -0.5})


def test_x_amp_zero_is_still_exactly_the_plain_rows():
    """P2 preserved through the signed change: x_amp = 0 ignores x_fc (P2's contract)."""
    a = G.x_shape_modulation(170.0, 0.0, 0.3, np.array([0.0, np.pi / 4]))[1]
    assert np.allclose(a, 1.0)


# ------------------------------------------------- lecleach_asym (odd cosine)

def test_asym_forces_the_full_ring():
    with pytest.raises(registry.GeneratorError, match="FULL ring"):
        G.rows_grid_points(
            _spec("lecleach_asym", span="quarter"), {"g_eps_m": 0.25}, BRIEF)
    with pytest.raises(registry.GeneratorError, match="FULL ring"):
        G.rows_grid_points(
            _spec("lecleach_asym", span="half", n_phi=25),
            {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0, "g_eps_m": 0.2}, BRIEF)


def test_asym_eps_zero_builds_the_quarter_exactly():
    grid, meta = G.rows_grid_points(
        _spec("lecleach_asym"), {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0}, BRIEF)
    assert meta["row_span"] == "quarter" and meta["quadrants"] == "1"


def test_asym_rows_share_the_throat_and_differ_at_the_mouth():
    grid, meta = G.rows_grid_points(
        _spec("lecleach_asym", span="full", n_phi=25),
        {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0, "g_eps_m": 0.25}, BRIEF)
    assert meta["row_span"] == "full" and meta["quadrants"] == "1234" \
        and meta["symmetry_plane"] is None
    # every row shares the driver's exit radius at the throat (w(0) = 0)
    throat = np.hypot(grid[:, 0, 0], grid[:, 0, 1])
    assert np.allclose(throat, R0, atol=1e-9)
    # the +x side's mouth is wider than the -x side with eps > 0
    mouth_x = grid[:, -1, 0]
    assert float(np.max(mouth_x)) > float(-np.min(mouth_x)) + 0.01 * float(np.max(mouth_x))


def test_asym_validator_ranges():
    with pytest.raises(registry.GeneratorError, match="eps_m"):
        G._rows_lecleach_asym_knobs({"g_eps_m": 0.4})
    with pytest.raises(registry.GeneratorError, match="eps_start"):
        G._rows_lecleach_asym_knobs({"g_eps_start": 1.0})
    out = G._rows_lecleach_asym_knobs({"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0,
                                       "g_eps_m": -0.3})
    assert out["eps_m"] == -0.3 and out["r_lip_mm"] == 0.0


# -------------------------------------------------- the mouth ripple (pleats)

def test_ripple_validator_evict_s_and_ranges():
    with pytest.raises(registry.GeneratorError, match="EVEN integer"):
        G._rows_shape_knobs({"g_fc_h_hz": 800.0, "g_fc_v_hz": 1100.0,
                             "g_ripple_lobes": 11.0})
    with pytest.raises(registry.GeneratorError, match="ripple_amp_mm"):
        G._rows_shape_knobs({"g_fc_h_hz": 800.0, "g_fc_v_hz": 1100.0,
                             "g_ripple_lobes": 12.0, "g_ripple_amp_mm": 60.0})   # cap raised 6 -> 50 mm 2026-10-27 (Solana-depth flutes); 60 is still refused
    with pytest.raises(registry.GeneratorError, match="ripple_amp_mm > 0 needs"):
        G._rows_shape_knobs({"g_fc_h_hz": 800.0, "g_fc_v_hz": 1100.0,
                             "g_ripple_amp_mm": 3.0})
    out = G._rows_shape_knobs({"g_fc_h_hz": 800.0, "g_fc_v_hz": 1100.0,
                               "g_ripple_lobes": 24.0, "g_ripple_amp_mm": 0.5,
                               "g_ripple_start": 0.95})
    assert out["ripple_lobes"] == 24 and out["ripple_amp_mm"] == 0.5


def test_ripple_resolution_guard_refuses_an_unrepresentable_lobe_count():
    with pytest.raises(registry.GeneratorError, match="samples per lobe"):
        G._rows_ripple_resolution_guard(24, 0.5 * np.pi, 15)     # 15-row quarter span


def test_ripple_delivers_its_mm_height_at_the_widest_station():
    """The ridge height at the row's widest station is amp_mm (the signed-mm contract).

    Compare the ROW RADII (the meta mouth_y_mm / the assembled x column), not the
    assembled y column: row phi = 0 is the H-plane row, whose y column is zero by
    construction (y * sin(0))."""
    base_spec = {"rows": {"type": "salmon_elliptical"}, "n_phi": 15, "n_s": 32}
    knobs = {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1100.0}
    base = G.rows_grid_points(base_spec, knobs, BRIEF)
    rip = G.rows_grid_points(base_spec, {**knobs, "g_ripple_lobes": 8.0,
                                         "g_ripple_amp_mm": 3.0,
                                         "g_ripple_start": 0.7}, BRIEF)
    # the H row's ridge peak: +amp_mm exactly (cos 0 = +1, the window is 1 at the mouth)
    assert float(rip[0][0, -1, 0] - base[0][0, -1, 0]) == pytest.approx(3.0, rel=0.12)
    # the row META's widest-station radius carries the same delta
    assert float(rip[1]["rows"][0]["mouth_y_mm"]
                 - base[1]["rows"][0]["mouth_y_mm"]) == pytest.approx(3.0, rel=0.12)
    # and the meta carries the ripple contract + label
    assert rip[1]["ripple_lobes"] == 8 and "ripple_law" in rip[1]


# ------------------------------------------------------------- the FULL ring

@requires_mesher
def test_full_ring_lecleach_asym_meshes_through_the_real_adapter():
    """The capability probe: a closed full-ring point grid (quadrants '1234') meshes on
    the CPU exactly like the mesher's native closed mode; no solve, no GPU."""
    from hornlab_search.mesh import build

    cfg = load_config(TYP / "lecleach_asym_odd.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    families.validate(space.seed)
    json.dumps(space.seed.params)
    spec = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=2000.0)
    design = Design("FREEFORM", {"grid": space.seed.params["grid"]})
    result = build.build_mesh(design, spec, cfg, Path("runs") / "c2_probe", mode="screen")
    assert result.quadrants == "1234" and result.symmetry_plane is None
    assert result.n_triangles > 0 and Path(result.path).is_file()
    print(f"\nfull-ring mesh: {result.n_triangles} tris; bbox = "
          f"{tuple(round(v, 4) for v in result.bbox_m)}")


@requires_mesher
def test_full_ring_rejects_a_quadrant_mismatch():
    from hornlab_search.mesh import grid_build

    cfg = load_config(TYP / "lecleach_asym_odd.yaml")
    space = DesignSpace.from_config(cfg)
    grid = space.seed.params["grid"]
    inner, meta = G.rows_grid_points(
        grid, grid.get("knobs", {}),
        {"driver": cfg.brief["driver"], "envelope": cfg.brief["envelope"]})
    ms = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=2000.0)
    with pytest.raises(ValueError, match="needs quadrants='1234'"):
        grid_build.build_grid_mesh(
            {"inner_points": inner, "meta": meta, "wall_thickness_mm": 3.0},
            dataclasses.replace(ms, quadrants="1"),
            Path("runs") / "c2_probe_mismatch", cfg, mode="screen")

import dataclasses  # noqa: E402