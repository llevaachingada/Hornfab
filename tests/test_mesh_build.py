"""Mesher-gated tests for mesh/build.py (04 tests 14-22 plus the reader and the guards).

Every test here drives the real hornlab_mesher on the CPU. None touches the GPU.
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import time

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, sizing
from hornlab_search.types import (Design, GeometryInvalidError, MeshResult, MeshSpec,
                                  MeshTooLargeError)

pytestmark = requires_mesher

ROSSE_SEED = dict(R_mm=150.0, r0_mm=12.7, a_deg=60.0, a0_deg=15.5, k=1.0, q=1.0, exponent=2.0,
                  aspect_ratio=1.0)


def big(cfg):
    """Same Config with dof caps lifted, for tests that study meshing rather than the cap."""
    return dataclasses.replace(cfg, mesh=dataclasses.replace(
        cfg.mesh, dof_cap_screen=10**6, dof_cap_verify=10**6, dof_cap_final=10**6))


def spec(f_max, quadrants="1", max_triangles=10**6, epw=6.0):
    return MeshSpec(epw=epw, f_max_hz=f_max, quadrants=quadrants, max_triangles=max_triangles)


@pytest.fixture(scope="module")
def osse_cfg():
    return load_config(EXAMPLES / "osse_baseline.yaml")


@pytest.fixture(scope="module")
def osse_seed(osse_cfg):
    return DesignSpace.from_config(osse_cfg).seed


def example_seeds():
    out = {}
    for name in ("osse_baseline.yaml", "icw_termination.yaml", "freeform_hv.yaml"):
        c = load_config(EXAMPLES / name)
        out[c.family] = (c, DesignSpace.from_config(c).seed)
    c = load_config(EXAMPLES / "osse_baseline.yaml")
    out["R-OSSE"] = (c, Design("R-OSSE", copy.deepcopy(ROSSE_SEED)))
    return out


SEEDS = example_seeds()


# ------------------------------------------------------------------ test 14, 16


@pytest.mark.parametrize("family", list(SEEDS))
def test_each_family_builds_with_tags(family, tmp_path):
    cfg, design = SEEDS[family]
    ms = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=3000.0)
    r = build.build_mesh(design, ms, cfg, tmp_path, mode="screen")
    assert isinstance(r, MeshResult)
    assert r.n_triangles > 100
    assert r.quadrants == ms.quadrants
    assert r.symmetry_plane == sizing.SYMMETRY_PLANE[ms.quadrants]
    assert r.n_dof is None                     # only a solve reports dofs (contract)
    assert set(r.res_mm) == {"throat", "mouth", "rear"}
    assert r.res_mm["throat"] == pytest.approx(r.res_mm["mouth"] / 2)
    s = build.read_msh_summary(r.path)
    # 16: expected physical tags, SD1D1001 (the source, tag 2) non-empty
    assert s["tags"].get(2, 0) > 0
    assert s["tags"].get(1, 0) > 0
    assert s["tag_names"][2] == "SD1D1001" and s["tag_names"][1] == "SD1G0"
    assert sum(s["tags"].values()) == s["n_triangles"] == r.n_triangles


def test_seed_reader_summary_and_metres(osse_cfg, osse_seed, tmp_path):
    r = build.build_mesh(osse_seed, spec(3000.0, max_triangles=73600), big(osse_cfg), tmp_path)
    s = build.read_msh_summary(r.path)
    assert s["format"].startswith("2.2")
    assert s["n_triangles"] == r.n_triangles
    assert s["n_nodes_used"] <= s["n_nodes"]
    x0, y0, z0, x1, y1, z1 = s["bbox_m"]
    assert tuple(s["bbox_m"]) == tuple(r.bbox_m)
    assert 0.2 < z1 < 0.35                      # L = 260 mm  ->  z extent near 0.26, not 260
    assert x0 == 0.0 and y0 == 0.0              # quarter domain sits in +x +y
    assert 0.1 < s["area_m2"] < 1.0
    assert (tmp_path / "mesh_meta.json").is_file()
    meta = json.loads((tmp_path / "mesh_meta.json").read_text(encoding="utf-8"))
    assert meta["rear_res_factor"] == 1.0               # WP7: default recorded, key/output unchanged


# ------------------------------------------------------------------ test 15


def test_bbox_in_metres_and_guard_fires_on_wrong_scale(osse_cfg, osse_seed, tmp_path, monkeypatch):
    ok = build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path / "ok")
    ext = max(ok.bbox_m[3] - ok.bbox_m[0], ok.bbox_m[4] - ok.bbox_m[1], ok.bbox_m[5] - ok.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M

    real = families.to_mesher_config

    def wrong_scale(*a, **k):
        cfg = real(*a, **k)
        cfg["mesh"]["scale_to_metres"] = False       # deliberately the 1000x-horn mistake
        return cfg

    monkeypatch.setattr(families, "to_mesher_config", wrong_scale)
    with pytest.raises(build.MeshUnitsError, match="mesh_scale") as ei:
        build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path / "bad")
    assert "UNITS" in str(ei.value)
    assert not (tmp_path / "bad" / "mesh.msh").exists()     # an unusable mesh is not left behind
    assert not (tmp_path / "bad" / "mesh_meta.json").exists()
    assert not isinstance(ei.value, GeometryInvalidError)    # a hard failure, not a bad candidate


def test_bbox_guard_bounds():
    build._check_bbox((0.0, 0.0, 0.0, 0.1, 0.1, 0.26))
    for bad in [(0, 0, 0, 0.001, 0.001, 0.001), (0, 0, 0, 100.0, 100.0, 260.0),
                (0, 0, 0, 0.0, 0.0, 6.0)]:
        with pytest.raises(build.MeshUnitsError):
            build._check_bbox(bad)


# ------------------------------------------------------------------ test 17


def test_triangle_count_scales_as_fmax_squared(osse_cfg, osse_seed, tmp_path):
    n = {}
    for f in (3000.0, 6000.0, 12000.0):
        n[f] = build.build_mesh(osse_seed, spec(f), big(osse_cfg), tmp_path / f"f{int(f)}").n_triangles
    r6, r12 = n[6000.0] / n[3000.0], n[12000.0] / n[3000.0]
    print(f"\ntriangles {n}  ratios 1 : {r6:.3f} : {r12:.3f}  (ideal 1 : 4 : 16)")
    assert r6 == pytest.approx(4.0, rel=0.25)
    assert r12 == pytest.approx(16.0, rel=0.25)


# ------------------------------------------------------------------ test 18


def test_too_large_is_refused_before_any_mesh_is_written(osse_cfg, osse_seed, tmp_path):
    # warm-up so the timing below measures the guard, not module imports
    build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path / "warm")
    ms = dataclasses.replace(mesh_spec("screen", osse_cfg), f_max_hz=40000.0)
    out = tmp_path / "huge"
    t0 = time.perf_counter()
    with pytest.raises(MeshTooLargeError, match="no mesh was generated"):
        build.build_mesh(osse_seed, ms, osse_cfg, out, mode="screen")
    dt = time.perf_counter() - t0
    print(f"\nMeshTooLargeError raised in {dt * 1000:.1f} ms")
    assert not (out / "mesh.msh").exists()
    assert dt < 0.100, f"guard took {dt * 1000:.1f} ms"


def test_over_cap_but_inside_mesher_slack_is_caught_after_meshing(osse_cfg, osse_seed, tmp_path):
    """Between the dof cap and the cap * slack the mesher accepts; our dof guard must not."""
    # f_max chosen so the quarter-domain seed lands ~1.25x over the screen cap (inside the 1.5x
    # pre-mesh reject margin). Was 8500 Hz for the plan's cap of 8000; the cap is now read from the
    # config (5000 measured on the 8 GB RTX 4060, TOOLCHAIN.md), so f_max scales as sqrt(cap).
    cap = osse_cfg.mesh.dof_cap_screen
    f_max = 8500.0 * (cap / 8000.0) ** 0.5
    ms = dataclasses.replace(mesh_spec("screen", osse_cfg), f_max_hz=f_max)
    out = tmp_path / "slack"
    with pytest.raises(MeshTooLargeError, match=f"exceeds the dof cap {cap}"):
        build.build_mesh(osse_seed, ms, osse_cfg, out, mode="screen")
    assert not (out / "mesh.msh").exists()            # deleted, never reachable by a solver
    assert not (out / "mesh_meta.json").exists()


def test_mesher_budget_refusal_maps_to_mesh_too_large(osse_cfg, osse_seed, tmp_path):
    ms = spec(9000.0, max_triangles=4000)             # mesher's own ceiling: 1000 solved triangles
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(osse_seed, ms, big(osse_cfg), tmp_path)
    assert not (tmp_path / "mesh.msh").exists()


def test_premesh_estimate_tracks_real_counts(osse_cfg, osse_seed, tmp_path):
    f = 6000.0
    r = build.build_mesh(osse_seed, spec(f), big(osse_cfg), tmp_path)
    ms = spec(f)
    mcfg = families.to_mesher_config(osse_seed, ms, sizing.res_mm_for(6.0, f), tmp_path / "x.msh")
    est = build.estimate_triangles_premesh(mcfg)
    assert est is not None
    assert 0.75 < est / r.n_triangles < 1.25


# ------------------------------------------------------------------ test 19


def test_quarter_is_a_quarter(osse_cfg, osse_seed, tmp_path):
    q = build.build_mesh(osse_seed, spec(6000.0, "1"), big(osse_cfg), tmp_path / "q")
    f = build.build_mesh(osse_seed, spec(6000.0, "1234"), big(osse_cfg), tmp_path / "f")
    assert q.n_triangles / f.n_triangles == pytest.approx(0.25, rel=0.20)
    assert q.symmetry_plane == "yz+xz" and f.symmetry_plane is None


@pytest.mark.parametrize("quadrants,plane", [("12", "xz"), ("14", "yz")])
def test_half_domain_symmetry_pairing(quadrants, plane, osse_cfg, osse_seed, tmp_path):
    """Silent killer #2: what we ask for, what the mesher built, and the solver flag agree."""
    r = build.build_mesh(osse_seed, spec(3000.0, quadrants), big(osse_cfg), tmp_path)
    assert r.symmetry_plane == plane == sizing.SYMMETRY_PLANE[quadrants]
    full = build.build_mesh(osse_seed, spec(3000.0, "1234"), big(osse_cfg), tmp_path / "full")
    assert r.n_triangles / full.n_triangles == pytest.approx(0.5, rel=0.20)


def test_sizing_symmetry_table_matches_the_mesher(osse_cfg, osse_seed, tmp_path):
    import hornlab_mesher as hm
    for quadrants in sizing.SYMMETRY_PLANE:
        ms = spec(2500.0, quadrants)
        mcfg = families.to_mesher_config(osse_seed, ms, sizing.res_mm_for(6.0, 2500.0),
                                         tmp_path / f"{quadrants}.msh")
        built = hm.build_from_config(mcfg, tmp_path / f"{quadrants}.msh")
        assert built.native_symmetry_plane == sizing.SYMMETRY_PLANE[quadrants], quadrants


def test_symmetry_mismatch_is_a_hard_error(osse_cfg, osse_seed, tmp_path, monkeypatch):
    saved = dict(sizing.SYMMETRY_PLANE)
    monkeypatch.setitem(sizing.SYMMETRY_PLANE, "1", "xz")     # simulate drift in the one table
    with pytest.raises(build.SymmetryMismatchError, match="yz\\+xz"):
        build.build_mesh(osse_seed, spec(3000.0, "1"), big(osse_cfg), tmp_path)
    assert not (tmp_path / "mesh.msh").exists()
    assert saved["1"] == "yz+xz"


# ------------------------------------------------------------------ test 20


def test_build_is_deterministic(osse_cfg, osse_seed, tmp_path):
    a = build.build_mesh(osse_seed, spec(6000.0), big(osse_cfg), tmp_path / "a")
    b = build.build_mesh(osse_seed, spec(6000.0), big(osse_cfg), tmp_path / "b")
    sa, sb = build.read_msh_summary(a.path), build.read_msh_summary(b.path)
    ha = hashlib.sha256(open(a.path, "rb").read()).hexdigest()[:12]
    hb = hashlib.sha256(open(b.path, "rb").read()).hexdigest()[:12]
    print(f"\ntriangles {a.n_triangles} vs {b.n_triangles}; file sha {ha} vs {hb}; "
          f"area {sa['area_m2']!r} vs {sb['area_m2']!r}")
    assert a.n_triangles == b.n_triangles
    assert a.bbox_m == b.bbox_m
    assert sa["n_nodes"] == sb["n_nodes"]


# ------------------------------------------------------------------ test 21


def test_export_step(osse_cfg, osse_seed, tmp_path):
    ms = spec(3000.0)
    path, info = build.export_step(osse_seed, ms, osse_cfg, tmp_path / "horn.step")
    assert path.is_file() and path.stat().st_size > 1000
    assert info.volume_mm3 > 0
    assert info.body
    assert not (tmp_path / "horn.msh").exists()


# ------------------------------------------------------------------ test 22


def test_cache_hit_does_not_invoke_the_mesher(osse_cfg, osse_seed, tmp_path, monkeypatch):
    import hornlab_mesher as hm
    first = build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path)

    def boom(*a, **k):
        raise AssertionError("the mesher was invoked on a cache hit")

    monkeypatch.setattr(hm, "build_from_config", boom)
    second = build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path)
    assert second.n_triangles == first.n_triangles
    assert second.bbox_m == first.bbox_m
    assert second.path == first.path
    # a different spec is a different key: it must reach the mesher
    with pytest.raises(AssertionError, match="mesher was invoked"):
        build.build_mesh(osse_seed, spec(3500.0), big(osse_cfg), tmp_path)


def test_shared_cache_hardlinks_mesh_but_copies_meta(osse_cfg, osse_seed, tmp_path, monkeypatch):
    import hornlab_mesher as hm
    cache = tmp_path / "cache"
    first = build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path / "run1", cache_dir=cache)
    monkeypatch.setattr(hm, "build_from_config",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("mesher invoked")))
    second = build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path / "run2", cache_dir=cache)
    p1 = tmp_path / "run1" / "mesh.msh"
    p2 = tmp_path / "run2" / "mesh.msh"
    assert p2.is_file() and not p2.is_symlink()
    assert second.path == str(p2) and second.n_triangles == first.n_triangles
    assert os.path.samefile(p2, p1)
    assert os.stat(p2).st_nlink >= 2
    assert p2.read_bytes() == p1.read_bytes()
    m1 = tmp_path / "run1" / "mesh_meta.json"
    m2 = tmp_path / "run2" / "mesh_meta.json"
    assert not os.path.samefile(m2, m1)
    assert m2.read_bytes() == m1.read_bytes()


def test_copy_entry_replaces_an_existing_link_without_writing_through(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "mesh.msh").write_bytes(b"new mesh bytes")
    (src / "mesh_meta.json").write_text('{"key": "k"}', encoding="utf-8")
    third = tmp_path / "third.msh"
    third.write_bytes(b"third-party bytes")
    dst = tmp_path / "dst"
    dst.mkdir()
    os.link(third, dst / "mesh.msh")
    build._copy_entry(src, dst)
    assert third.read_bytes() == b"third-party bytes"
    assert (dst / "mesh.msh").read_bytes() == b"new mesh bytes"
    assert os.path.samefile(dst / "mesh.msh", src / "mesh.msh")
    assert (dst / "mesh_meta.json").read_bytes() == (src / "mesh_meta.json").read_bytes()


def test_rebuild_into_the_same_design_dir_never_writes_through_the_cache(osse_cfg, osse_seed,
                                                                        tmp_path):
    cache = tmp_path / "cache"
    out = tmp_path / "run"
    first = build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), out, cache_dir=cache)
    key1 = build.mesh_cache_key(osse_seed, spec(3000.0), big(osse_cfg))
    cache_msh = cache / key1 / "mesh.msh"
    before = cache_msh.read_bytes()
    assert os.path.samefile(out / "mesh.msh", cache_msh)
    second = build.build_mesh(osse_seed, spec(3500.0), big(osse_cfg), out, cache_dir=cache)
    assert second.n_triangles != first.n_triangles
    assert cache_msh.read_bytes() == before
    assert not os.path.samefile(out / "mesh.msh", cache_msh)
    assert (out / "mesh.msh").read_bytes() != before


def test_cache_hit_still_honours_the_dof_cap(osse_cfg, osse_seed, tmp_path):
    ms = dataclasses.replace(mesh_spec("screen", osse_cfg), f_max_hz=6000.0)
    build.build_mesh(osse_seed, ms, osse_cfg, tmp_path, mode="screen")
    tight = dataclasses.replace(osse_cfg, mesh=dataclasses.replace(osse_cfg.mesh, dof_cap_screen=100))
    with pytest.raises(MeshTooLargeError):
        build.build_mesh(osse_seed, ms, tight, tmp_path, mode="screen")


# ------------------------------------------------------------------ error mapping


def test_invalid_design_never_reaches_the_mesher(osse_cfg, tmp_path, monkeypatch):
    import hornlab_mesher as hm
    monkeypatch.setattr(hm, "build_from_config",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("mesher invoked")))
    with pytest.raises(GeometryInvalidError, match="bogus_key"):
        build.build_mesh(Design("OSSE", {"r0_mm": 17.78, "bogus_key": 1.0}), spec(3000.0),
                         big(osse_cfg), tmp_path)


def test_mesher_config_error_message_preserved_verbatim(osse_cfg, osse_seed, tmp_path, monkeypatch):
    import hornlab_mesher as hm
    from hornlab_mesher.config_parser import ConfigError

    def refuse(*a, **k):
        raise ConfigError("per-azimuth throat stretch is not supported yet; s1 must be a plain "
                          "finite number")

    monkeypatch.setattr(hm, "build_from_config", refuse)
    with pytest.raises(GeometryInvalidError) as ei:
        build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path)
    msg = str(ei.value)
    assert "per-azimuth throat stretch is not supported yet; s1 must be a plain finite number" in msg
    assert "design/custom.py" in msg

    def refuse2(*a, **k):
        raise ValueError("OSSE termination parameter n must be > 0, got -1 at phi=0.0 deg")

    monkeypatch.setattr(hm, "build_from_config", refuse2)
    with pytest.raises(GeometryInvalidError, match="termination parameter n must be > 0"):
        build.build_mesh(osse_seed, spec(3000.0), big(osse_cfg), tmp_path)


def test_real_mesher_rejection_becomes_geometry_invalid(osse_cfg, osse_seed, tmp_path):
    """No monkeypatch: a design that passes our table but that the mesher's own ConfigError
    refuses (a wall far thinner than the mesh can resolve)."""
    d = Design("OSSE", {**osse_seed.params, "wall_thickness_mm": 0.001})
    families.validate(d)                                   # legal for us
    with pytest.raises(GeometryInvalidError, match="wall_thickness_mm"):
        build.build_mesh(d, spec(3000.0), big(osse_cfg), tmp_path)
    assert not (tmp_path / "mesh.msh").exists()


def test_mesher_defaults_are_not_trusted_flat_dict_drops_max_triangles(osse_cfg, osse_seed, tmp_path):
    """Why to_mesher_config is sectioned: a top-level max_triangles is silently ignored by the
    mesher (default 18000 applies), which would cap every quarter mesh at 4500 triangles."""
    import hornlab_mesher as hm
    from hornlab_mesher.mesher import TriangleBudgetExceeded
    ms = spec(9000.0, max_triangles=10**6)
    mcfg = families.to_mesher_config(osse_seed, ms, sizing.res_mm_for(6.0, 9000.0), tmp_path / "s.msh")
    hm.build_from_config(mcfg, tmp_path / "s.msh")          # sectioned form: honoured
    flat = {"formula": "OSSE", "mode": "freestanding", **mcfg["profile"], **mcfg["cross_section"],
            **mcfg["mesh"]}
    with pytest.raises(TriangleBudgetExceeded, match="4,500"):
        hm.build_from_config(flat, tmp_path / "f.msh")


def test_sizing_constant_mirrors_the_mesher():
    from hornlab_mesher.mesh_sizing import TRIANGLES_PER_AREA_OVER_H2
    assert sizing.TRIANGLES_PER_AREA_OVER_H2 == TRIANGLES_PER_AREA_OVER_H2

# ------------------------------------------------------------------ WP7 rear_res_factor

def test_rear_res_factor_is_recorded_and_scales_only_rear(osse_cfg, osse_seed, tmp_path):
    cfg15 = dataclasses.replace(
        osse_cfg, mesh=dataclasses.replace(osse_cfg.mesh, rear_res_factor=1.5))
    ms = spec(1500.0, max_triangles=10**6)
    r = build.build_mesh(osse_seed, ms, cfg15, tmp_path)
    meta = json.loads((tmp_path / "mesh_meta.json").read_text(encoding="utf-8"))
    assert meta["rear_res_factor"] == 1.5
    mesh_cfg = meta["mesher_config"]["mesh"]
    assert mesh_cfg["rear_res_mm"] == pytest.approx(mesh_cfg["mouth_res_mm"] * 1.5)
    assert mesh_cfg["throat_res_mm"] == pytest.approx(mesh_cfg["mouth_res_mm"] / 2.0)
    assert r.res_mm["rear"] == pytest.approx(r.res_mm["mouth"] * 1.5)
    assert r.res_mm["throat"] == pytest.approx(r.res_mm["mouth"] / 2.0)
    assert meta["key"].endswith("-rear1.5")
