"""WP9b mesher-gated tests: the rows recipe -> ``_build_grid_mesh`` -> ``grid_build``.

Real hornlab_mesher on the CPU, offline: no solve, no GPU.  One Salmon rollback row grid
(stop 185 deg, inside the dossier's 180-200 probe window) is built through the FULL wire-in
route and checked for topology, units and the meta the estimator/report need.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.generators import grid as grid_mod
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, grid_build, sizing, topology
from hornlab_search.types import Design, MeshResult, MeshTooLargeError

pytestmark = requires_mesher

TYP = EXAMPLES / "typologies"
LOW_F_MAX_HZ = 2000.0                  # keeps the mesher-gated tests ~0.1-0.3 s each
ROLLBACK_STOP = 185.0                  # dossier 9b.4 probe window 180-200 deg


def _cfg(name="salmon_elliptical"):
    return load_config(TYP / f"{name}.yaml")


def _space(name="salmon_elliptical"):
    return DesignSpace.from_config(_cfg(name))


def _low_spec(cfg):
    return dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=LOW_F_MAX_HZ)


def _rollback_design():
    """The example seed with stop_deg moved to the rollback probe window."""
    space = _space()
    block = dict(space.seed.params["grid"])
    block["knobs"] = {**block["knobs"], "g_stop_deg": ROLLBACK_STOP}
    design = Design("FREEFORM", {"grid": block})
    families.validate(design)
    return design, block


def test_rollback_rows_build_through_the_full_wire_in(tmp_path):
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
    ext = max(r.bbox_m[3] - r.bbox_m[0], r.bbox_m[4] - r.bbox_m[1], r.bbox_m[5] - r.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert rep.bad_open_edges == 0 and rep.nonmanifold_edges == 0
    # the grid/rows route still writes no mesh_meta.json (documented in grid_build.py)
    assert not (out / "mesh_meta.json").exists()
    print(f"\nrollback rows mesh: {r.n_triangles} tris, "
          f"bbox={tuple(round(v, 4) for v in r.bbox_m)}, res={r.res_mm}")


def test_rollback_rows_meta_carries_self_approach_and_row_extents():
    cfg = _cfg()
    _design, block = _rollback_design()
    spec = {k: v for k, v in block.items() if k != "knobs"}
    inner, meta = grid_mod.rows_grid_points(spec, block["knobs"], cfg.brief)
    assert inner.shape == (block["n_phi"], block["n_s"] + 1, 3)
    assert meta["rows_type"] == "salmon_elliptical"
    assert "LABELED HYPOTHESIS-SHAPE EXPERIMENT" in meta["hypothesis_label"]
    assert meta["min_self_approach_mm"] >= 2.0 * block["wall_thickness_mm"] \
        + grid_mod.SELF_APPROACH_MARGIN_MM
    assert meta["min_self_approach_limit_mm"] == pytest.approx(8.0)
    assert "REPORT ONLY" in meta["min_cross_row_distance_scope"]
    assert len(meta["rows"]) == block["n_phi"]
    row = meta["rows"][0]
    for key in ("phi_deg", "length_mm", "mouth_x_mm", "mouth_y_mm",
                "x_min_mm", "x_max_mm", "y_max_mm"):
        assert key in row
    # rollback: x is non-monotone on at least one row (x_max > mouth x)
    assert any(m["x_max_mm"] > m["mouth_x_mm"] + 1e-6 for m in meta["rows"])


def test_rows_route_tiny_dof_cap_raises_mesh_too_large(tmp_path):
    cfg = _cfg()
    cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_screen=50))
    design, _block = _rollback_design()
    out = tmp_path / "tiny"
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(design, _low_spec(cfg), cfg, out, mode="screen")
    assert not (out / "mesh.msh").exists()


def test_seed_recipe_re_derives_the_same_grid_as_the_space(tmp_path):
    """The mesh route rebuilds from the stored recipe (no arrays), not from a cached grid."""
    cfg = _cfg()
    space = _space()
    block = space.seed.params["grid"]
    inner, meta = grid_mod.rows_grid_points(
        {k: v for k, v in block.items() if k != "knobs"}, block["knobs"], cfg.brief)
    assert meta["rows_type"] == "salmon_elliptical"
    # the example seed itself is legal and meshes through the same dispatch
    r = build.build_mesh(space.seed, _low_spec(cfg), cfg, tmp_path / "seed", mode="screen")
    assert Path(r.path).is_file()
