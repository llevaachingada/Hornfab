"""``source.cap`` reaches the GRID mesher: ``auto`` is inert, an explicit radius is live.

Measured 2026-11-20: three briefs identical except ``source.cap`` (auto / 150 / 60) produced the
same mesh hash, solve hash and response on the grid route, because ``grid_build.build_grid_mesh``
never passed ``source_radius_mm`` to ``PointGridHornGeometry``. Evidence:
``runs/source_sensitivity/*`` (six dirs, mesh hash ``7abdb667298f``).

The tests below pin both halves of the fix:
  * the stored design's 12 kHz auto run is byte-identical (same MeshSpec hash), and the geometry
    still takes the mesher's auto-angle branch (``source_radius_mm`` stays its -1.0 default);
  * an explicit cap changes the geometry/mesh identity (``source_radius_mm`` is the brief value
    and the produced ``.msh`` bytes differ), while ``source_auto_angle_deg`` stays set.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, REPO, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.constants import C_AIR
from hornlab_search.design.generators import grid as G
from hornlab_search.mesh import build, grid_build
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec

pytestmark = requires_mesher

# ------------------------------------------------------------------ stored auto evidence
RUN = REPO / "runs" / "20261119T090559Z-screen-9b8767"
DESIGN_HASH = "9b5428e6dec8"
SOURCE_BRIEF = (REPO / "examples" / "briefs" / "source_sensitivity_2026-11-20"
                / "room_landscape_80x50_700_hf1440_v7_12k_auto.yaml")
SS_RUN = REPO / "runs" / "source_sensitivity" / "ss_crowex_auto"

# ------------------------------------------------------------------ tiny live-knob fixture
R0_MM = 5.0
A0_DEG = 8.0
L_MM = 60.0
RM_MM = 25.0
N_PHI = 13
N_S = 32
EPW = 6.0
MOUTH_RES_MM = 12.0
F_MAX_HZ = 1000.0 * C_AIR / (EPW * MOUTH_RES_MM)

TINY_SPEC = {"name": "grid", "profile_h": {"type": "conical"}, "profile_v": "same",
             "n_phi": N_PHI, "n_s": N_S, "max_wall_deg": 80.0, "wall_thickness_mm": 3.0}
TINY_KNOBS = {"L_mm": L_MM, "h_rm_mm": RM_MM}
TINY_BRIEF = {
    "driver": {"exit_radius_mm": R0_MM, "exit_angle_deg": A0_DEG},
    "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
}


class _Stop(Exception):
    """Sentinel: abort before gmsh once the mesher geometry object has been captured."""


def _stored_design() -> Design:
    raw = json.loads((RUN / "designs" / DESIGN_HASH / "design.json").read_text(encoding="utf-8"))
    return Design(raw["family"], raw["params"])


def _stored_cfg(*, cap=None):
    """The 12 kHz source-sensitivity brief on the stored run's config (mode verify)."""
    cfg = load_config(RUN / "config.yaml", brief=SOURCE_BRIEF)
    if cap is not None:
        cfg = dataclasses.replace(cfg, brief={**cfg.brief, "source": {"cap": cap}})
    return cfg


def _stored_recorded_mesh_hash() -> str:
    first = (SS_RUN / "search.ndjson").read_text(encoding="utf-8").splitlines()[0]
    row = json.loads(first)
    assert row["design_hash"] == DESIGN_HASH
    return str(row["mesh_hash"])


def _capture_geometry(design, mspec, cfg, out_dir, monkeypatch) -> dict:
    import hornlab_mesher.mesher as mesher

    captured: dict = {}

    def spy(geometry, density, **kwargs):
        captured["geometry"] = geometry
        captured["density"] = density
        raise _Stop()

    monkeypatch.setattr(mesher, "build_mesh_with_info", spy)
    with pytest.raises(_Stop):
        build.build_mesh(design, mspec, cfg, out_dir, mode="verify")
    return captured


def _tiny_cfg(brief: dict):
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    lifted = dataclasses.replace(cfg.mesh, dof_cap_screen=10**6, dof_cap_verify=10**6,
                                 dof_cap_final=10**6)
    return dataclasses.replace(cfg, brief=brief, mesh=lifted)


TINY_MESH_SPEC = MeshSpec(epw=EPW, f_max_hz=F_MAX_HZ, quadrants="1", max_triangles=10**6)


def _tiny_grid():
    return G.grid_points(TINY_SPEC, TINY_KNOBS, TINY_BRIEF)


def _mesh_build_hash(geometry) -> str:
    """Stable identity of the geometry inputs a grid mesh build receives (spec-level)."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(geometry.inner_points, dtype=np.float64).tobytes())
    if geometry.outer_points is not None:
        h.update(np.ascontiguousarray(geometry.outer_points, dtype=np.float64).tobytes())
    h.update(struct.pack("<d", float(geometry.wall_thickness_mm)))
    h.update(json.dumps({
        "source_shape": int(geometry.source_shape),
        "source_auto_angle_deg": geometry.source_auto_angle_deg,
        "source_radius_mm": float(geometry.source_radius_mm),
        "closed": bool(geometry.closed),
        "symmetry_planes": list(geometry.symmetry_planes),
    }, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def _capture_tiny_geometry(cap, out_dir, monkeypatch) -> dict:
    import hornlab_mesher.mesher as mesher

    inner, meta = _tiny_grid()
    cfg = _tiny_cfg({**TINY_BRIEF, "source": {"cap": cap}})
    captured: dict = {}

    def spy(geometry, density, **kwargs):
        captured["geometry"] = geometry
        raise _Stop()

    monkeypatch.setattr(mesher, "build_mesh_with_info", spy)
    with pytest.raises(_Stop):
        grid_build.build_grid_mesh({"inner_points": inner, "meta": meta,
                                    "wall_thickness_mm": 3.0},
                                   TINY_MESH_SPEC, out_dir / "mesh.msh", cfg)
    return captured


# ------------------------------------------------------------------ auto is inert


def test_auto_cap_keeps_the_stored_mesh_hash_and_the_auto_angle_branch(monkeypatch, tmp_path):
    design = _stored_design()
    assert design.hash() == DESIGN_HASH

    cfg = _stored_cfg()
    recorded = _stored_recorded_mesh_hash()
    # runs/source_sensitivity/ss_crowex_auto/search.ndjson: same design, 12 kHz brief.
    assert recorded == "7abdb667298f"
    mspec = mesh_spec("verify", cfg)
    assert mspec.hash() == recorded

    # The named stored run itself (8 kHz embedded brief) still reproduces its own mesh hash.
    orig_cfg = load_config(RUN / "config.yaml")
    orig_row = json.loads((RUN / "search.ndjson").read_text(
        encoding="utf-8").splitlines()[0])
    assert orig_row["design_hash"] == DESIGN_HASH
    assert mesh_spec("screen", orig_cfg).hash() == orig_row["mesh_hash"]

    # Explicit cap:auto is the stored brief (default) as far as every identity is concerned.
    cfg_explicit = _stored_cfg(cap="auto")
    assert mesh_spec("verify", cfg_explicit).hash() == recorded
    assert grid_build.source_cap_radius_mm(cfg) is None
    assert grid_build.source_cap_radius_mm(cfg_explicit) is None
    # The grid-build provenance record says exactly which cap was used (auto -> the angle).
    assert grid_build.source_cap_provenance(cfg, 2.0) == {
        "cap": "auto", "radius_mm": None, "radius_source": "auto_angle",
        "auto_angle_deg": 2.0,
    }

    # No source_radius_mm keyword -> the mesher's own -1.0 default and the auto-angle branch.
    cap_a = _capture_geometry(design, mspec, cfg, tmp_path / "a", monkeypatch)
    cap_b = _capture_geometry(design, mspec, cfg_explicit, tmp_path / "b", monkeypatch)
    for captured in (cap_a, cap_b):
        geom = captured["geometry"]
        assert geom.source_radius_mm == -1.0
        assert geom.source_auto_angle_deg == pytest.approx(2.0)
    geom = cap_a["geometry"]
    assert np.array_equal(geom.inner_points, cap_b["geometry"].inner_points)

    # The existing design provenance agrees with that auto resolution (do not duplicate it):
    # recipe_meta stores throat_radius / sin(exit_angle), exactly the mesher's auto branch.
    recipe = json.loads((RUN / "designs" / DESIGN_HASH / "design.json").read_text(
        encoding="utf-8"))["generator"]["recipe_meta"]["source_cap"]
    assert recipe["source"] == "point_grid_resolved"
    ring = np.asarray(geom.inner_points, dtype=float)[:, 0, :]
    center = ring.mean(axis=0)
    center[:2] = 0.0
    radii = np.linalg.norm((ring - center)[:, :2], axis=1)
    throat_radius = float(radii[radii > 1e-9].mean())
    auto_radius = throat_radius / abs(math.sin(math.radians(geom.source_auto_angle_deg)))
    assert recipe["radius_mm"] == pytest.approx(auto_radius, rel=1e-12)


def test_auto_cap_rebuilds_the_stored_mesh_byte_for_byte(tmp_path):
    """The strongest form of "auto is inert": the rebuilt .msh is the stored one exactly."""
    design = _stored_design()
    cfg = _stored_cfg()
    result = build.build_mesh(design, mesh_spec("verify", cfg), cfg, tmp_path / "auto",
                              mode="verify")
    rebuilt = hashlib.sha256(Path(result.path).read_bytes()).hexdigest()
    stored = SS_RUN / "designs" / DESIGN_HASH / "mesh.msh"
    recorded = hashlib.sha256(stored.read_bytes()).hexdigest()
    print(f"\nauto .msh sha256 rebuilt={rebuilt[:12]} stored={recorded[:12]} "
          f"tris={result.n_triangles}")
    assert rebuilt == recorded


# ------------------------------------------------------------------ the knob is live


def test_explicit_cap_changes_the_mesh_identity_and_keeps_the_auto_angle(monkeypatch, tmp_path):
    auto = _capture_tiny_geometry("auto", tmp_path / "auto", monkeypatch)["geometry"]
    cap60 = _capture_tiny_geometry(60, tmp_path / "cap60", monkeypatch)["geometry"]

    # The mesher prefers an explicit radius over the angle; the angle stays set in both cases.
    assert auto.source_radius_mm == -1.0
    assert cap60.source_radius_mm == pytest.approx(60.0)
    assert auto.source_auto_angle_deg is not None and auto.source_auto_angle_deg > 0.0
    assert cap60.source_auto_angle_deg == pytest.approx(auto.source_auto_angle_deg)

    # The grid-build provenance record distinguishes the explicit brief radius from auto.
    prov = grid_build.source_cap_provenance(
        _tiny_cfg({**TINY_BRIEF, "source": {"cap": 60}}), auto.source_auto_angle_deg)
    assert prov["cap"] == 60.0 and prov["radius_mm"] == 60.0
    assert prov["radius_source"] == "brief"
    assert prov["auto_angle_deg"] == pytest.approx(auto.source_auto_angle_deg)

    h_auto = _mesh_build_hash(auto)
    h_cap60 = _mesh_build_hash(cap60)
    print(f"\nsource.cap auto -> geometry hash {h_auto[:12]} "
          f"(source_radius_mm={auto.source_radius_mm:g}); "
          f"cap 60 -> {h_cap60[:12]} (source_radius_mm={cap60.source_radius_mm:g})")
    assert h_auto != h_cap60


def test_explicit_cap_changes_the_built_msh_bytes(tmp_path):
    inner, meta = _tiny_grid()
    paths = {}
    for label, cap in (("auto", "auto"), ("cap60", 60)):
        cfg = _tiny_cfg({**TINY_BRIEF, "source": {"cap": cap}})
        out = tmp_path / label / "mesh.msh"
        grid_build.build_grid_mesh({"inner_points": inner, "meta": meta,
                                    "wall_thickness_mm": 3.0},
                                   TINY_MESH_SPEC, out, cfg)
        assert out.is_file()
        paths[label] = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"\n.msh sha256 auto={paths['auto'][:12]} cap60={paths['cap60'][:12]}")
    assert paths["auto"] != paths["cap60"]


def test_sub_throat_cap_surfaces_the_meshers_own_outcome_not_a_new_error(tmp_path):
    """cap 1 mm < the 5 mm throat: the mesher clamps (max(radius, throat*1.001)), never raises
    a new exception type; if it does refuse, that refusal is the wrapped GeometryInvalidError."""
    inner, meta = _tiny_grid()
    cfg = _tiny_cfg({**TINY_BRIEF, "source": {"cap": 1.0}})
    out = tmp_path / "subthroat" / "mesh.msh"
    try:
        r = grid_build.build_grid_mesh({"inner_points": inner, "meta": meta,
                                        "wall_thickness_mm": 3.0},
                                       TINY_MESH_SPEC, out, cfg)
    except GeometryInvalidError:
        return
    assert Path(r.path).is_file()


def test_mesher_guard_errors_from_geometry_construction_are_wrapped(monkeypatch, tmp_path):
    """A mesher ValueError raised while constructing the cap geometry is a GeometryInvalidError."""
    import hornlab_mesher.geometry as mesher_geometry

    inner, meta = _tiny_grid()
    cfg = _tiny_cfg({**TINY_BRIEF, "source": {"cap": 60}})

    def boom(**kwargs):
        raise ValueError("rounded-cap source radius must be at least the throat radius")

    monkeypatch.setattr(mesher_geometry, "PointGridHornGeometry", boom)
    with pytest.raises(GeometryInvalidError,
                       match="source radius must be at least the throat radius"):
        grid_build.build_grid_mesh({"inner_points": inner, "meta": meta,
                                    "wall_thickness_mm": 3.0},
                                   TINY_MESH_SPEC, tmp_path / "mesh.msh", cfg)

# ------------------------------------------------------------------ the cache identity
# 2026-11-20 (second half of the same bug): threading the radius into the geometry is not enough.
# The mesh and solve caches key on ``MeshSpec.hash()`` / ``SolveSpec.hash()``, so unless the cap
# enters the mesh identity a cap change still resolves to the auto mesh and its cached response.
# These two tests pin the identity: absent/auto is byte-identical to every stored hash, an explicit
# radius is a different mesh.

def test_mesh_spec_hash_is_unchanged_for_auto_and_stored_runs():
    cfg = load_config(RUN / "config.yaml")
    stored = json.loads((RUN / "search.ndjson").read_text(encoding="utf-8").splitlines()[0])
    assert mesh_spec("screen", cfg).hash() == stored["mesh_hash"]
    assert mesh_spec("screen", cfg).source_cap_mm == 0.0
    auto = load_config(RUN / "config.yaml", brief=SOURCE_BRIEF)
    assert mesh_spec("verify", auto).source_cap_mm == 0.0
    assert mesh_spec("verify", auto).hash() == mesh_spec("verify", auto).hash()  # stable


def test_mesh_spec_hash_changes_with_an_explicit_cap():
    briefs = SOURCE_BRIEF.parent
    auto = load_config(RUN / "config.yaml", brief=briefs / "room_landscape_80x50_700_hf1440_v7_12k_auto.yaml")
    cap150 = load_config(RUN / "config.yaml", brief=briefs / "room_landscape_80x50_700_hf1440_v7_12k_cap150.yaml")
    cap60 = load_config(RUN / "config.yaml", brief=briefs / "room_landscape_80x50_700_hf1440_v7_12k_cap60.yaml")
    h_auto = mesh_spec("verify", auto).hash()
    h150 = mesh_spec("verify", cap150).hash()
    h60 = mesh_spec("verify", cap60).hash()
    assert mesh_spec("verify", cap150).source_cap_mm == 150.0
    assert mesh_spec("verify", cap60).source_cap_mm == 60.0
    assert len({h_auto, h150, h60}) == 3
    # the stored 12 kHz auto run keeps its hash
    assert h_auto.startswith("7abdb667298f")
