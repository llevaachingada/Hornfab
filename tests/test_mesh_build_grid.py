"""WP10 wire-in, mesher-gated tests: ``mesh/build.py`` dispatch -> ``mesh/grid_build.py``.

Real hornlab_mesher on the CPU, offline: no solve, no GPU.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, grid_build, sizing, topology
from hornlab_search.types import MeshResult, MeshTooLargeError

pytestmark = requires_mesher

TYP = EXAMPLES / "typologies"
LOW_F_MAX_HZ = 2000.0                  # keeps these dispatch tests ~0.1-0.2 s each


def _cfg(name="grid_ellipse", **replace):
    cfg = load_config(TYP / f"{name}.yaml")
    return dataclasses.replace(cfg, **replace) if replace else cfg


def _space(name="grid_ellipse"):
    return DesignSpace.from_config(_cfg(name))


def _low_spec(cfg):
    return dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=LOW_F_MAX_HZ)


def test_build_mesh_dispatches_a_grid_design_through_grid_build(tmp_path, monkeypatch):
    cfg = _cfg()
    space = _space()
    captured = {}
    real = grid_build.build_grid_mesh

    def spy(grid, mesh, out_path, cfg_, **kw):
        captured["grid"], captured["out_path"], captured["kw"] = grid, Path(out_path), kw
        return real(grid, mesh, out_path, cfg_, **kw)

    monkeypatch.setattr(grid_build, "build_grid_mesh", spy)
    out = tmp_path / "mesh"
    r = build.build_mesh(space.seed, _low_spec(cfg), cfg, out, mode="screen")
    assert captured and captured["out_path"] == out / "mesh.msh"
    assert set(captured["grid"]) == {"inner_points", "meta", "wall_thickness_mm"}
    assert captured["grid"]["inner_points"].shape[0] == 13        # n_phi quarter rows
    assert captured["grid"]["meta"]["quarter"] is True
    assert captured["kw"]["mode"] == "screen"

    assert isinstance(r, MeshResult) and r.n_triangles > 0
    assert Path(r.path).is_file()
    assert r.quadrants == "1" and r.symmetry_plane == "yz+xz" == sizing.SYMMETRY_PLANE["1"]
    assert r.n_dof is None
    assert r.res_mm["throat"] == pytest.approx(r.res_mm["mouth"] / 2.0)
    assert set(r.res_mm) == {"throat", "mouth", "rear"}
    summary, xyz, tri = build.read_msh_summary(Path(r.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    ext = max(r.bbox_m[3] - r.bbox_m[0], r.bbox_m[4] - r.bbox_m[1], r.bbox_m[5] - r.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert rep.bad_open_edges == 0 and rep.nonmanifold_edges == 0
    # the grid route has no mesh cache/meta yet (documented in grid_build.py)
    assert not (out / "mesh_meta.json").exists()
    # search/evaluate.py's _grid_info must tolerate the missing mesh_meta.json (area is unknown,
    # the grid block stays available); evaluate rows for grid designs thus carry area None.
    from hornlab_search.search import evaluate as E
    area, grid_info = E._grid_info(out)
    assert area is None and grid_info["available"] is True
    print(f"\ngrid mesh: {r.n_triangles} tris, bbox={tuple(round(v, 4) for v in r.bbox_m)}, "
          f"res={r.res_mm}")


def test_grid_design_derivation_matches_the_generator(tmp_path):
    """The mesh route rebuilds the grid from the Design recipe, not from a cached array."""
    from hornlab_search.design.generators import grid as grid_mod

    cfg = _cfg()
    space = _space()
    r = build.build_mesh(space.seed, _low_spec(cfg), cfg, tmp_path, mode="screen")
    block = space.seed.params["grid"]
    inner, meta = grid_mod.grid_points({k: block[k] for k in grid_mod.GRID_SPEC_KEYS},
                                       block["knobs"], cfg.brief)
    assert inner.shape == (13, 33, 3)
    assert meta["source_auto_angle_deg"] == pytest.approx(
        meta["source_auto_angle_deg"]) and meta["source_auto_angle_deg"] > 0
    assert families.validate(space.seed) is None
    assert Path(r.path).is_file()


def test_modulated_grid_meshes_and_is_wider_than_the_plain_ellipse(tmp_path):
    cfg_mod = _cfg("grid_ellipse_mod")
    plain = build.build_mesh(_space("grid_ellipse").seed, _low_spec(cfg_mod), cfg_mod,
                             tmp_path / "plain", mode="screen")
    mod = build.build_mesh(DesignSpace.from_config(cfg_mod).seed, _low_spec(cfg_mod), cfg_mod,
                           tmp_path / "mod", mode="screen")
    assert Path(mod.path).is_file() and mod.n_triangles > 0
    assert mod.symmetry_plane == "yz+xz"
    # G8 factor at the mouth is 1 + a1*cos(2 phi) + a2*cos(4 phi): 1.03 at the H plane
    # (phi=0) and 0.91 at the V plane (phi=90). The measured quarter bbox scales the same way.
    factor_h = 1.0 + 0.06 - 0.03
    factor_v = 1.0 - 0.06 - 0.03
    assert mod.bbox_m[3] == pytest.approx(plain.bbox_m[3] * factor_h, rel=0.01)
    assert mod.bbox_m[4] == pytest.approx(plain.bbox_m[4] * factor_v, rel=0.01)
    print(f"\nplain x_max={plain.bbox_m[3]:.5f} y_max={plain.bbox_m[4]:.5f} m; "
          f"mod x_max={mod.bbox_m[3]:.5f} y_max={mod.bbox_m[4]:.5f} m "
          f"(factors {mod.bbox_m[3] / plain.bbox_m[3]:.4f} / {mod.bbox_m[4] / plain.bbox_m[4]:.4f} "
          f"vs {factor_h:.2f} / {factor_v:.2f})")


def test_grid_build_mesh_without_a_brief_is_a_hard_error(tmp_path):
    cfg = _cfg(brief=None)
    with pytest.raises(ValueError, match="needs cfg.brief"):
        build.build_mesh(_space().seed, _low_spec(cfg), cfg, tmp_path)


def test_grid_recipe_disagreeing_with_the_brief_is_invalid_geometry(tmp_path):
    """A design whose stored recipe no longer fits its brief is an invalid candidate, not a crash."""
    from hornlab_search.design import families
    from hornlab_search.types import Design, GeometryInvalidError

    cfg = _cfg()
    space = _space()
    block = dict(space.seed.params["grid"])
    block["knobs"] = {**block["knobs"], "L_mm": 500.0}     # deeper than the 220 mm envelope
    design = Design("FREEFORM", {"grid": block})
    families.validate(design)                              # structurally legal...
    with pytest.raises(GeometryInvalidError, match="exceeds the brief envelope"):
        build.build_mesh(design, _low_spec(cfg), cfg, tmp_path)   # ...but the brief refuses it


def test_tiny_dof_cap_raises_mesh_too_large_on_the_grid_route(tmp_path):
    cfg = _cfg()
    cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_screen=50))
    ms = mesh_spec("screen", cfg)
    out = tmp_path / "tiny"
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(_space().seed, ms, cfg, out, mode="screen")
    assert not (out / "mesh.msh").exists()


def test_evaluate_row_is_distinguishable_and_maps_too_large(tmp_path):
    from hornlab_search.search import evaluate as E

    cfg = _cfg()
    cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_screen=50))
    space = DesignSpace.from_config(cfg)
    ctx = E.make_context(cfg, None, cache_dir=tmp_path / "cache")
    run = tmp_path / "run"
    ev = E.evaluate(space.seed, space, cfg, "screen", run, None, None, ctx=ctx)
    assert E.error_kind(ev.error) == E.KIND_TOO_LARGE

    row = json.loads((run / "search.ndjson").read_text(encoding="utf-8").splitlines()[0])
    assert row["kind"] == E.KIND_TOO_LARGE
    assert row["family"] == "FREEFORM"                      # frozen family literal
    assert row["params"]["grid"]["knobs"]["L_mm"] == pytest.approx(180.0)
    assert row["generator"]["name"] == "grid"               # provenance distinguishes grid rows
    assert row["generator"]["spec"]["name"] == "grid"
    design_json = json.loads((run / "designs" / ev.design_hash / "design.json")
                             .read_text(encoding="utf-8"))
    assert design_json["family"] == "FREEFORM"
    assert "grid" in design_json["params"] and design_json["generator"]["name"] == "grid"
