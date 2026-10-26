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


def test_grid_self_approach_classifies_invalid_geometry_and_is_memoized(tmp_path, monkeypatch):
    """S1b (2026-10-25 R9 audit + campaign finding): the rows route's in-build_grid_mesh
    re-checks (the self-approach guard in _resolve_grid) used to escape build_grid_mesh as a
    bare GeneratorError and land in evaluate's generic-except as kind 'exception' - flat 1000,
    never memoized, re-run on every replay (a 2026-10-25 salmon campaign burned 29/40 evals
    that way). The evaluate boundary now maps GeneratorError onto invalid_geometry, so the
    failure is deterministic, failure-marker memoized and replayed as cached. build_grid_mesh
    itself still raises bare GeneratorError (test_mesh_grid_build.py pins that contract);
    mesh/build.build_mesh_from_design_grid's recipe-step wrap stays as it is. Fixture: the
    salmon_saddle seed under a 17.4 mm-exit brief (its tuned 12.7 mm brief leaves the outer
    shell 0.002 mm above the refusal limit; the bigger driver pushes it just under)."""
    from hornlab_search.design.generators import grid as grid_gen
    from hornlab_search.search import evaluate as E

    # 2026-10-26: the guard now measures folds only (arc separation >= pi/2 * limit), so this
    # seed's old 0.002 mm "refusal" -- a chord-vs-arc false positive on ordinary lip curvature --
    # is gone (it measures ~12.6 mm against the 8 mm limit). The contract under test is the
    # BOUNDARY: a real guard refusal must come back as invalid_geometry and be memoized. The
    # gap measurement is therefore forced below the limit; the refusal still travels the real
    # check_self_approach -> build_grid_mesh -> evaluate path.
    monkeypatch.setattr(grid_gen, "min_self_approach_mm", lambda *a, **k: 1.0)

    bigger = dict(_cfg("salmon_saddle").brief)
    bigger.pop("path", None)                               # loader-added runtime key, not schema
    # S1a driver-pass premise fix (2026-10-25): the organic family brief now carries f0_hz
    # 1900 + objective v3, and a copied f0 brief DERIVES the seed (fc re-aimed) - so this
    # fixture must stay derivation-inert to keep testing its ORIGINAL premise: the saddle's
    # own TUNED seed (fc 800/1200, ratio 0.9962) under a 17.4 mm-exit brief. Stripping the
    # f0/objective keys restores exactly that brief; assert on the tuned knobs below.
    bigger.pop("objective", None)
    (bigger.get("target") or {}).pop("f0_hz", None)
    bigger["name"] = "bigger_driver"
    bigger["driver"] = {**bigger["driver"], "exit_radius_mm": 17.4}
    bigger["envelope"] = {**bigger["envelope"],
                          "max_mouth_w_mm": 520.0, "max_mouth_h_mm": 420.0}
    brief_yaml = tmp_path / "bigger_driver.yaml"
    brief_yaml.write_text(json.dumps(bigger), encoding="utf-8")     # JSON is valid YAML 1.2
    cfg = load_config(TYP / "salmon_saddle.yaml", brief=brief_yaml)
    space = DesignSpace.from_config(cfg)
    assert cfg.raw.get("feasibility") is None              # derivation-inert premise holds
    assert dict(cfg.seed_params.get("grid", {}).get("knobs")
                or cfg.seed_params).get("g_fc_h_hz", 800.0) == pytest.approx(800.0)
    ctx = E.make_context(cfg, None, cache_dir=tmp_path / "cache")
    ev1 = E.evaluate(space.seed, space, cfg, "screen", tmp_path / "run1", None, None, ctx=ctx)
    assert E.error_kind(ev1.error) == E.KIND_INVALID, ev1.error
    assert "self-approach" in ev1.error, ev1.error                  # it IS the guard that failed
    markers = list((tmp_path / "cache" / "solve" / "failures").glob("*.json"))
    assert len(markers) >= 1
    ctx2 = E.make_context(cfg, None, cache_dir=tmp_path / "cache")
    ev2 = E.evaluate(space.seed, space, cfg, "screen", tmp_path / "run2", None, None, ctx=ctx2)
    assert ev2.cached and E.error_kind(ev2.error) == E.KIND_INVALID
    row = json.loads((tmp_path / "run2" / "search.ndjson").read_text(encoding="utf-8").splitlines()[0])
    assert row["kind"] == E.KIND_INVALID and row["kind"] != "exception"


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
