"""Mesher-gated: the HALF-model GRID rows route (fix-6) + the variant seeds.

Real hornlab_mesher on the CPU, offline: no solve, no GPU.  The photographed saddle
(salmon rows, span half, quadrants "14") is built through the FULL wire route:
Design params recipe -> mesh/build.py::_build_grid_mesh -> grid/grid_build ->
PointGridHornGeometry(symmetry_planes=("x",)) -> topology on the yz plane.
The quarter variant seeds (iwata_ar, toroidal_rollback) are also built once to prove
their recipes are meshable; the quarter route stays byte-identical (protected suites).
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.generators import grid as grid_mod
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, sizing, topology
from hornlab_search.types import MeshResult, MeshTooLargeError

pytestmark = requires_mesher

TYP = EXAMPLES / "typologies"
LOW_F_MAX_HZ = 2000.0


def _cfg(name="salmon_saddle"):
    return load_config(TYP / f"{name}.yaml")


def _low_spec(cfg, *, quadrants=None):
    spec = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=LOW_F_MAX_HZ)
    return dataclasses.replace(spec, quadrants=quadrants) if quadrants else spec


def test_saddle_half_builds_through_the_full_wire_route(tmp_path):
    cfg = _cfg()
    space = DesignSpace.from_config(cfg)
    out = tmp_path / "half"
    r = build.build_mesh(space.seed, _low_spec(cfg), cfg, out, mode="screen")

    assert isinstance(r, MeshResult) and r.n_triangles > 0
    assert Path(r.path).is_file()
    assert r.quadrants == "14"
    assert r.symmetry_plane == sizing.SYMMETRY_PLANE["14"] == "yz"
    assert r.n_dof is None
    summary, xyz, tri = build.read_msh_summary(Path(r.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    ext = max(r.bbox_m[3] - r.bbox_m[0], r.bbox_m[4] - r.bbox_m[1],
              r.bbox_m[5] - r.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M
    assert 0.02 <= ext <= 5.0
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["14"])
    assert rep.bad_open_edges == 0 and rep.nonmanifold_edges == 0
    # the reduced half is x >= 0 and crosses y = 0 (both top and bottom present)
    assert float(np.min(xyz[:, 0])) >= -1e-9
    assert float(np.min(xyz[:, 1])) < 0.0 < float(np.max(xyz[:, 1]))
    assert not (out / "mesh_meta.json").exists()
    print(f"\nsaddle HALF mesh: {r.n_triangles} tris, "
          f"bbox={tuple(round(v, 4) for v in r.bbox_m)}, res={r.res_mm}")


def test_half_model_meta_carries_span_and_labels():
    cfg = _cfg()
    space = DesignSpace.from_config(cfg)
    block = space.seed.params["grid"]
    assert block["span"] == "half" and block["n_phi"] == 25
    inner, meta = grid_mod.rows_grid_points(
        {k: v for k, v in block.items() if k != "knobs"}, block["knobs"], cfg.brief)
    assert inner.shape == (block["n_phi"], block["n_s"] + 1, 3)
    assert meta["span"] == "half" and meta["half_model"] is True
    assert meta["quadrants"] == "14" and meta["symmetry_plane"] == "yz"
    assert "RECONSTRUCTION" in meta["reconstruction_label"]
    assert meta["stop_cos2k"] == [0.25] and meta["stop_sin2k1"] == [0.2]
    assert abs(meta["wfc_over_hfc"] - 1.0) <= 0.02
    assert np.allclose(inner[0, :, 0], 0.0, atol=1e-9)
    assert np.allclose(inner[-1, :, 0], 0.0, atol=1e-9)


def test_saddle_tiny_dof_cap_raises_mesh_too_large(tmp_path):
    cfg = _cfg()
    cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_screen=50))
    space = DesignSpace.from_config(cfg)
    out = tmp_path / "tiny"
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(space.seed, _low_spec(cfg), cfg, out, mode="screen")
    assert not (out / "mesh.msh").exists()


def test_half_dofs_use_the_quadrant_factor():
    cfg = _cfg()
    spec = mesh_spec("screen", cfg)
    assert spec.quadrants == "14"
    assert sizing.QUADRANT_FACTOR["14"] == 2
    assert spec.max_triangles == sizing.max_triangles_for(
        cfg.mesh.dof_cap_screen, "14", cfg.mesh.dof_per_triangle,
        cfg.mesh.max_triangle_slack)
    quarter = sizing.max_triangles_for(
        cfg.mesh.dof_cap_screen, "1", cfg.mesh.dof_per_triangle,
        cfg.mesh.max_triangle_slack)
    assert spec.max_triangles == pytest.approx(quarter / 2.0, abs=1)


def test_grid_symmetry_mismatch_is_refused_before_meshing(tmp_path):
    cfg = _cfg()
    space = DesignSpace.from_config(cfg)
    half_as_quarter = _low_spec(cfg, quadrants="1")
    with pytest.raises(ValueError, match="grid/symmetry mismatch"):
        build.build_mesh(space.seed, half_as_quarter, cfg, tmp_path / "bad1", mode="screen")
    qcfg = _cfg("lecleach_toroidal")
    qspace = DesignSpace.from_config(qcfg)
    quarter_as_half = _low_spec(qcfg, quadrants="14")
    with pytest.raises(ValueError, match="grid/symmetry mismatch"):
        build.build_mesh(qspace.seed, quarter_as_half, qcfg, tmp_path / "bad2", mode="screen")


def test_sin_free_half_span_equals_the_quarter_geometry_mirrored():
    # Same landed knobs, two spans: with NO odd-sine term the explicit half model is
    # exactly the quarter surface plus its y -> -y mirror (no new geometry, only dofs).
    cfg = _cfg()
    knobs = {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8, "g_stop_deg": 170.0,
             "g_stop_cos2k": [0.25]}
    base = {"name": "grid", "rows": {"type": "salmon_elliptical"}, "n_phi": 25,
            "n_s": 32, "wall_thickness_mm": 3.0}
    half, hm = grid_mod.rows_grid_points({**base, "span": "half"}, knobs, cfg.brief)
    quarter, qm = grid_mod.rows_grid_points({**base, "span": "quarter"}, knobs, cfg.brief)
    assert hm["half_model"] is True and qm["half_model"] is False
    assert hm["quadrants"] == "14" and qm["quadrants"] == "1"
    # the -phi side is the +phi side mirrored through y = 0 (x and the march unchanged)
    for j in range(1, 13):
        plus = half[12 + j]
        mirrored = np.column_stack([plus[:, 0], -plus[:, 1], plus[:, 2]])
        assert np.abs(half[12 - j] - mirrored).max() <= 1e-9
    # and the +phi side IS the quarter geometry at the same azimuths (bit-for-bit)
    for j in range(13):
        assert np.abs(half[12 + j] - quarter[2 * j]).max() <= 1e-9


@pytest.mark.parametrize("name", ["lecleach_iwata_ar", "lecleach_toroidal"])
def test_quarter_variant_seeds_mesh(name, tmp_path):
    cfg = _cfg(name)
    space = DesignSpace.from_config(cfg)
    r = build.build_mesh(space.seed, _low_spec(cfg), cfg, tmp_path / name, mode="screen")
    assert r.quadrants == "1" and r.symmetry_plane == sizing.SYMMETRY_PLANE["1"]
    assert Path(r.path).is_file()
    summary, xyz, tri = build.read_msh_summary(Path(r.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
