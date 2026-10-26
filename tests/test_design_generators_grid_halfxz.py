"""Phase 0 item 2D (2026-10-26): the rows ``span: half_xz`` model.

``lecleach_asym_odd``'s ``cos(phi)`` asymmetry breaks the left-right (x) mirror, but it is
EVEN under the up/down mirror ``phi -> -phi``.  The upper half (phi 0..180, mirror plane
xz, y >= 0, quadrants "12") is therefore an honest half model: the half's points mirrored
over y equal the full ring's, and the mesh has ~half the triangles (2x dof saving).

The full ring below is built from the SAME shape knobs at the mirror-equivalent angular
resolution (``n_phi_full = 2 * n_phi_half - 2 = 48``), so every half row and its mirror has
an exact full-ring counterpart.  CPU mesh only; the GPU equivalence A/B (<=0.05 dB / <=1
deg) is Phase B item 5.

Offline.  The mirror/point/validation tests do not need the mesher; the triangle-count
test is mesher-gated.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, grid_build, sizing, topology

TYP = EXAMPLES / "typologies"
HALF_N_PHI = 25
#: mirror-equivalent full-ring resolution: 25 upper-half rows + 23 mirrored interiors,
#: with phi = 0 and phi = 180 shared (25 + 23 = 48).
FULL_N_PHI = 2 * HALF_N_PHI - 2


def _rows_case():
    """The shipped lecleach_asym_odd seed's shape knobs + brief (derived state included)."""
    cfg = load_config(TYP / "lecleach_asym_odd.yaml")
    block = DesignSpace.from_config(cfg).seed.params["grid"]
    base = {k: v for k, v in block.items() if k != "knobs"}
    return cfg, base, block["knobs"]


def _points(span: str, n_phi: int):
    cfg, base, knobs = _rows_case()
    return G.rows_grid_points({**base, "span": span, "n_phi": n_phi}, knobs, cfg.brief)


# ------------------------------------------------------------------ geometry: mirror-exact

def test_half_xz_points_mirror_the_full_ring():
    cfg, base, knobs = _rows_case()
    half, hm = G.rows_grid_points({**base, "span": "half_xz", "n_phi": HALF_N_PHI},
                                  knobs, cfg.brief)
    full, fm = G.rows_grid_points({**base, "span": "full", "n_phi": FULL_N_PHI},
                                  knobs, cfg.brief)

    assert hm["row_span"] == hm["span"] == "half_xz"
    assert hm["quadrants"] == "12" and hm["symmetry_plane"] == "xz"
    assert hm["quarter"] is False and hm["half_model"] is False
    assert hm["phi_span_deg"] == 180.0 and hm["n_phi_quarter"] == 13
    assert fm["row_span"] == "full" and fm["quadrants"] == "1234"
    assert fm["symmetry_plane"] is None

    # Both half_xz endpoint rows live on the xz mirror plane (y = 0); the phi = 90 row
    # is the vertical row (x = 0).
    assert np.allclose(half[0, :, 1], 0.0, atol=1e-12)
    assert np.allclose(half[-1, :, 1], 0.0, atol=1e-12)
    i_v = int(np.argmin(np.abs(np.linspace(0.0, math.pi, HALF_N_PHI) - 0.5 * math.pi)))
    assert np.allclose(half[i_v, :, 0], 0.0, atol=1e-12)

    # The upper half IS the full ring's phi 0..180 rows (to 1e-9 mm).
    assert np.abs(full[:HALF_N_PHI] - half).max() <= 1e-9
    # The lower half is each interior upper row mirrored over y (phi -> -phi).
    worst = 0.0
    for k, i in enumerate(range(HALF_N_PHI - 2, 0, -1)):
        mirrored = half[i].copy()
        mirrored[:, 1] *= -1.0
        worst = max(worst, float(np.abs(full[HALF_N_PHI + k] - mirrored).max()))
    assert worst <= 1e-9, worst
    print(f"\nhalf_xz vs full mirror: direct "
          f"{float(np.abs(full[:HALF_N_PHI] - half).max()):.3e} mm, mirrored {worst:.3e} mm")


def test_half_xz_outer_shell_endpoints_lie_on_the_xz_plane():
    cfg, base, knobs = _rows_case()
    inner, _meta = G.rows_grid_points({**base, "span": "half_xz", "n_phi": HALF_N_PHI},
                                      knobs, cfg.brief)
    outer = G.grid_outer_points(inner, 3.0, half_xz=True)
    assert np.allclose(outer[0, :, 1], 0.0, atol=1e-12)
    assert np.allclose(outer[-1, :, 1], 0.0, atol=1e-12)
    assert np.allclose(inner[0, :, 1], 0.0, atol=1e-12)


# ------------------------------------------------------------------ validation

def test_grid_symmetry_axes_derive_from_the_sizing_source():
    """Silent killer #2: quadrants -> mesher axes must agree with sizing.SYMMETRY_PLANE."""
    expected = {None: (), "yz": ("x",), "xz": ("y",), "yz+xz": ("x", "y")}
    assert set(grid_build._GRID_SYMMETRY_AXES) == set(sizing.SYMMETRY_PLANE)
    for q, plane in sizing.SYMMETRY_PLANE.items():
        assert grid_build._GRID_SYMMETRY_AXES[q] == expected[plane], (q, plane)


def test_half_xz_validation_and_kind_scope():
    cfg, base, knobs = _rows_case()
    # The plain x >= 0 HALF is not a symmetry half for the odd cosine; keep refusing it.
    with pytest.raises(registry.GeneratorError, match="half_xz"):
        G.rows_grid_points({**base, "span": "half", "n_phi": HALF_N_PHI},
                           knobs, cfg.brief)
    # An even n_phi cannot carry the phi = 0/180 endpoints and the phi = 90 row together.
    with pytest.raises(registry.GeneratorError, match="ODD n_phi"):
        G.rows_grid_points({**base, "span": "half_xz", "n_phi": 26}, knobs, cfg.brief)
    # span: half_xz is implemented for lecleach_asym only in this pass.
    salmon = {"name": "grid", "rows": {"type": "salmon_elliptical"},
              "n_phi": HALF_N_PHI, "n_s": 32, "wall_thickness_mm": 3.0,
              "span": "half_xz"}
    with pytest.raises(registry.GeneratorError, match="lecleach_asym"):
        G.rows_grid_points(salmon, knobs, cfg.brief)


# ------------------------------------------------------------------ mesh: half the triangles

@requires_mesher
def test_half_xz_mesh_has_half_the_triangles_and_the_xz_plane(tmp_path):
    cfg, base, knobs = _rows_case()
    inner_h, meta_h = G.rows_grid_points(
        {**base, "span": "half_xz", "n_phi": HALF_N_PHI}, knobs, cfg.brief)
    inner_f, meta_f = G.rows_grid_points(
        {**base, "span": "full", "n_phi": FULL_N_PHI}, knobs, cfg.brief)

    ms = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=2000.0)

    def _spec(quadrants: str):
        return dataclasses.replace(
            ms, quadrants=quadrants,
            max_triangles=sizing.max_triangles_for(
                cfg.mesh.dof_cap_screen, quadrants, cfg.mesh.dof_per_triangle,
                cfg.mesh.max_triangle_slack))

    def _build(inner, meta, quadrants, out):
        return grid_build.build_grid_mesh(
            {"inner_points": inner, "meta": meta, "wall_thickness_mm": 3.0},
            _spec(quadrants), out, cfg, mode="screen")

    r_full = _build(inner_f, meta_f, "1234", tmp_path / "full.msh")
    r_half = _build(inner_h, meta_h, "12", tmp_path / "half.msh")

    assert r_half.quadrants == "12" and r_half.symmetry_plane == sizing.SYMMETRY_PLANE["12"]
    assert r_full.quadrants == "1234" and r_full.symmetry_plane is None
    # ~half the triangles: 25 rows is ~0.52 of the 48-row ring.
    assert r_half.n_triangles * 2 == pytest.approx(r_full.n_triangles, rel=0.15)

    summary, xyz, tri = build.read_msh_summary(Path(r_half.path), return_arrays=True)
    assert float(np.min(xyz[:, 1])) >= -1e-9          # y >= 0 (the reduced xz half)
    assert float(np.max(xyz[:, 1])) > 0.0
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["12"])
    assert rep.nonmanifold_edges == 0
    assert rep.open_edges == rep.open_edges_on_planes

    # The half span must reach the mesh spec as quadrants '12', never '14'/'1'.
    with pytest.raises(ValueError, match="grid/symmetry mismatch"):
        _build(inner_h, meta_h, "14", tmp_path / "bad.msh")
    print(f"\nhalf_xz mesh: {r_half.n_triangles} tris vs full {r_full.n_triangles} "
          f"(ratio {r_full.n_triangles / r_half.n_triangles:.3f})")
