"""Mesher-gated tests: the Le Cleac'h GRID rows recipe -> ``_build_grid_mesh`` -> ``grid_build``.

Real hornlab_mesher on the CPU, offline: no solve, no GPU.  The verified Fourcade
construction is marched to a rollback stop (190 deg, inside the dossier's 180-200 probe
window) and built through the FULL wire-in route: design.params recipe -> mesh/build.py
``_build_grid_mesh`` -> grid/grid_build (explicit outer shell).  Checked for topology,
the [0.02, 5.0] m unit band, the source tag, the self-approach meta and rollback.
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
from hornlab_search.types import Design, MeshResult, MeshTooLargeError

pytestmark = requires_mesher

TYP = EXAMPLES / "typologies"
LOW_F_MAX_HZ = 2000.0                 # keeps these mesher-gated tests fast
ROLLBACK_STOP = 190.0                 # dossier 9b.4 probe window 180-200 deg


def _cfg():
    return load_config(TYP / "lecleach_rollback.yaml")


def _space():
    return DesignSpace.from_config(_cfg())


def _low_spec(cfg):
    return dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=LOW_F_MAX_HZ)


def _rollback_design():
    """The example seed with stop_deg moved into the rollback probe window."""
    space = _space()
    block = dict(space.seed.params["grid"])
    block["knobs"] = {**block["knobs"], "g_stop_deg": ROLLBACK_STOP}
    design = Design("FREEFORM", {"grid": block})
    families.validate(design)
    return design, block


def test_rollback_lecleach_rows_build_through_the_full_wire_in(tmp_path):
    cfg = _cfg()
    design, block = _rollback_design()
    out = tmp_path / "mesh"
    r = build.build_mesh(design, _low_spec(cfg), cfg, out, mode="screen")

    assert isinstance(r, MeshResult) and r.n_triangles > 0
    assert Path(r.path).is_file()
    assert r.quadrants == "1" and r.symmetry_plane == sizing.SYMMETRY_PLANE["1"]
    assert r.n_dof is None
    summary, xyz, tri = build.read_msh_summary(Path(r.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    ext = max(r.bbox_m[3] - r.bbox_m[0], r.bbox_m[4] - r.bbox_m[1],
              r.bbox_m[5] - r.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M
    assert 0.02 <= ext <= 5.0                       # the task's explicit unit band
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert rep.bad_open_edges == 0 and rep.nonmanifold_edges == 0
    assert not (out / "mesh_meta.json").exists()    # the grid route writes no meta file
    print(f"\nlecleach rollback rows mesh: {r.n_triangles} tris, "
          f"bbox={tuple(round(v, 4) for v in r.bbox_m)}, res={r.res_mm}")


def test_rollback_lecleach_rows_meta_carries_the_verified_construction():
    cfg = _cfg()
    _design, block = _rollback_design()
    spec = {k: v for k, v in block.items() if k != "knobs"}
    inner, meta = grid_mod.rows_grid_points(spec, block["knobs"], cfg.brief)
    assert inner.shape == (block["n_phi"], block["n_s"] + 1, 3)
    assert meta["rows_type"] == "lecleach"
    assert meta["construction_label"].startswith("Fourcade 2015")
    assert "hypothesis_label" not in meta
    assert meta["min_self_approach_mm"] >= 2.0 * block["wall_thickness_mm"] \
        + grid_mod.SELF_APPROACH_MARGIN_MM
    assert meta["min_self_approach_limit_mm"] == pytest.approx(8.0)
    assert "REPORT ONLY" in meta["min_cross_row_distance_scope"]
    assert len(meta["rows"]) == block["n_phi"]
    row = meta["rows"][0]
    for key in ("phi_deg", "length_mm", "mouth_x_mm", "mouth_y_mm",
                "x_min_mm", "x_max_mm", "y_max_mm"):
        assert key in row
    # real rollback: x_max is reached before the lip (mouth_x < x_max)
    assert all(m["x_max_mm"] > m["mouth_x_mm"] + 1e-6 for m in meta["rows"])
    # the lip sits behind the widest station: x is non-monotone along the row
    assert np.any(np.diff(inner[0, :, 2]) < 0.0)


def test_lecleach_rows_tiny_dof_cap_raises_mesh_too_large(tmp_path):
    cfg = _cfg()
    cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_screen=50))
    design, _block = _rollback_design()
    out = tmp_path / "tiny"
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(design, _low_spec(cfg), cfg, out, mode="screen")
    assert not (out / "mesh.msh").exists()


def test_lecleach_seed_recipe_re_derives_the_same_grid_and_meshes(tmp_path):
    """The mesh route rebuilds from the stored recipe (no arrays), not from a cached grid."""
    cfg = _cfg()
    space = _space()
    block = space.seed.params["grid"]
    inner, meta = grid_mod.rows_grid_points(
        {k: v for k, v in block.items() if k != "knobs"}, block["knobs"], cfg.brief)
    assert meta["rows_type"] == "lecleach"
    r = build.build_mesh(space.seed, _low_spec(cfg), cfg, tmp_path / "seed", mode="screen")
    assert Path(r.path).is_file()


# ---------------------------------------------------------------------------
# TASK C: the HALF model through the FULL wire route (recipe -> build_mesh ->
# grid_build).  quadrants "14", symmetry plane yz (x >= 0), 2x the quarter dofs.
# ---------------------------------------------------------------------------

SADDLE = TYP / "salmon_saddle.yaml"


def _saddle_cfg():
    return load_config(SADDLE)


def _saddle_low_spec(cfg):
    return dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=LOW_F_MAX_HZ)


def test_half_model_saddle_builds_through_the_full_wire_in(tmp_path):
    cfg = _saddle_cfg()
    space = DesignSpace.from_config(cfg)
    out = tmp_path / "half"
    r = build.build_mesh(space.seed, _saddle_low_spec(cfg), cfg, out, mode="screen")

    assert isinstance(r, MeshResult) and r.n_triangles > 0
    assert Path(r.path).is_file()
    assert r.quadrants == "14"
    assert r.symmetry_plane == sizing.SYMMETRY_PLANE["14"] == "yz"
    summary, xyz, tri = build.read_msh_summary(Path(r.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    ext = max(r.bbox_m[3] - r.bbox_m[0], r.bbox_m[4] - r.bbox_m[1],
              r.bbox_m[5] - r.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M
    assert 0.02 <= ext <= 5.0                       # the task's explicit unit band
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["14"])
    assert rep.bad_open_edges == 0 and rep.nonmanifold_edges == 0
    # the reduced half lies in x >= 0 and actually crosses y = 0 (top and bottom present)
    assert float(np.min(xyz[:, 0])) >= -1e-9
    assert float(np.min(xyz[:, 1])) < 0.0 < float(np.max(xyz[:, 1]))
    assert not (out / "mesh_meta.json").exists()    # the grid route writes no meta file
    print(f"\nsalmon saddle HALF mesh: {r.n_triangles} tris, "
          f"bbox={tuple(round(v, 4) for v in r.bbox_m)}, res={r.res_mm}")


def test_half_model_tiny_dof_cap_raises_mesh_too_large(tmp_path):
    cfg = _saddle_cfg()
    cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_screen=50))
    space = DesignSpace.from_config(cfg)
    out = tmp_path / "tiny_half"
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(space.seed, _saddle_low_spec(cfg), cfg, out, mode="screen")
    assert not (out / "mesh.msh").exists()


def test_half_model_dofs_use_the_quadrant_factor():
    cfg = _saddle_cfg()
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
    # a HALF recipe under a quarter config
    cfg = _saddle_cfg()
    space = DesignSpace.from_config(cfg)
    bad = dataclasses.replace(_saddle_low_spec(cfg), quadrants="1")
    with pytest.raises(ValueError, match="grid/symmetry mismatch"):
        build.build_mesh(space.seed, bad, cfg, tmp_path / "half_as_quarter", mode="screen")
    # a QUARTER recipe under a half config
    qcfg = _cfg()
    qspace = _space()
    qbad = dataclasses.replace(_low_spec(qcfg), quadrants="14")
    with pytest.raises(ValueError, match="grid/symmetry mismatch"):
        build.build_mesh(qspace.seed, qbad, qcfg, tmp_path / "quarter_as_half", mode="screen")
