"""``source.cap`` reaches the NATIVE (non-grid) mesher route, and ``auto`` stays inert.

Measured 2026-11-20: ``runs/source_sensitivity2/ss_morph_{auto,cap150,cap60}`` (design
``cf716e738ef8``, family OSSE, a config with NO ``generator:`` block) produced three
**byte-identical** meshes (sha256 prefix ``c59ec195``) while recording three different
``mesh_hash`` values (``7abdb667298f`` / ``bcf9a8cec98b`` / ``c42751b96235``). The native formula
route in ``mesh/build.py`` never passed the brief's cap into the mesher, so ``MeshSpec.hash()``
recorded a change the geometry did not have.

The mesher's config path already carries the cap
(``hornlab_mesher/config_builder.py``)::

    807   source = _section(config, "source", "Source")
    1028  "sourceRadius": _scalar_or_expr(source, config, names=("source_radius_mm", ...))
    2247  source_radius_mm=_num_or_default(params.get("sourceRadius"), -1)

so the fix is wiring, not a refusal. ``build.build_mesh`` now adds
``mcfg["source"]["source_radius_mm"]`` only when the brief sets a numeric ``source.cap``:

    build.build_mesh                         (native formula branch)
      -> families.to_mesher_config           (dict; no cap)
      -> [fix] mcfg["source"]["source_radius_mm"] = brief source.cap
      -> hornlab_mesher.build_from_config
         -> config_builder.build_geometry_params -> resolve_geometry
         -> PointGridHornGeometry(source_radius_mm=..., source_auto_angle_deg=<a0>)
         -> build_mesh (cap surfaces use the explicit radius, angle stays as provenance)

``auto``/absent adds nothing, so the mesher keeps its ``-1.0`` default and the a0 auto-angle
branch: every stored native mesh, ``MeshSpec.hash()`` and ``.msh`` stays byte-identical.

The tests pin:
  * the stored screen run (``runs/20261119T081214Z-screen-8470bd``) reproduces its own recorded
    mesh hash AND its stored ``.msh`` byte for byte under ``auto``;
  * the exact source-sensitivity bug artifacts: ``auto`` rebuilds the stored ``c59ec195`` mesh,
    ``cap: 60`` now produces a different ``.msh`` while its recorded mesh hash is unchanged;
  * the mesher config / resolved geometry wiring: auto has no ``source`` override,
    cap 60 puts ``source_radius_mm=60`` on the ``PointGridHornGeometry`` and keeps the auto angle.
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import REPO, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.mesh import build
from hornlab_search.types import Design

pytestmark = requires_mesher

# ------------------------------------------------------------------ stored native evidence
RUN = REPO / "runs" / "20261119T081214Z-screen-8470bd"
DESIGN_HASH = "cf716e738ef8"
SS2 = REPO / "runs" / "source_sensitivity2"
BRIEFS = REPO / "examples" / "briefs" / "source_sensitivity_2026-11-20"
AUTO_BRIEF = BRIEFS / "room_landscape_80x50_700_hf1440_v7_12k_auto.yaml"
CAP60_BRIEF = BRIEFS / "room_landscape_80x50_700_hf1440_v7_12k_cap60.yaml"
CAP150_BRIEF = BRIEFS / "room_landscape_80x50_700_hf1440_v7_12k_cap150.yaml"


class _Stop(Exception):
    """Sentinel: stop once the mesher config has been captured (no gmsh build)."""


def _design() -> Design:
    raw = json.loads((RUN / "designs" / DESIGN_HASH / "design.json").read_text(encoding="utf-8"))
    design = Design(raw["family"], raw["params"])
    # The point of this file: a design on the NATIVE formula route, not grid/cad.
    assert "grid" not in design.params and "cad" not in design.params
    assert design.family == "OSSE"
    return design


def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ndjson_row(run_dir: Path) -> dict:
    """The stored row for this design, read from the run's own search.ndjson."""
    for line in (run_dir / "search.ndjson").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("design_hash") == DESIGN_HASH:
            return row
    raise AssertionError(f"no row for design {DESIGN_HASH} in {run_dir / 'search.ndjson'}")


def _cfg(brief: Path | None = None):
    """The stored native run's config, optionally with another brief (verify 12 kHz)."""
    if brief is None:
        return load_config(RUN / "config.yaml")
    return load_config(RUN / "config.yaml", brief=brief)


def _with_cap(cfg, cap):
    """Same brief, explicit source.cap (the screen variant used by the config-capture test)."""
    return dataclasses.replace(cfg, brief={**cfg.brief, "source": {"cap": cap}})


def _capture_mesher_config(design, mspec, cfg, out_dir, monkeypatch, *, mode: str) -> dict:
    """Run build_mesh up to the mesher call and return the config it would have passed."""
    import hornlab_mesher as hm

    captured: dict = {}

    def spy(config, output_path, **kwargs):
        captured["config"] = copy.deepcopy(config)
        raise _Stop()

    monkeypatch.setattr(hm, "build_from_config", spy)
    with pytest.raises(_Stop):
        build.build_mesh(design, mspec, cfg, out_dir, mode=mode)
    return captured["config"]


def _geometry_identity(geometry) -> str:
    """Stable identity of the geometry the native mesher receives (spec level)."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(geometry.inner_points, dtype=np.float64).tobytes())
    outer = getattr(geometry, "outer_points", None)
    if outer is not None:
        h.update(np.ascontiguousarray(outer, dtype=np.float64).tobytes())
    h.update(json.dumps({
        "source_shape": int(geometry.source_shape),
        "source_radius_mm": float(geometry.source_radius_mm),
        "source_auto_angle_deg": geometry.source_auto_angle_deg,
        "closed": bool(geometry.closed),
        "symmetry_planes": list(geometry.symmetry_planes),
    }, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


# ------------------------------------------------------------------ auto is inert


def test_native_auto_reproduces_the_stored_runs_mesh_hash_and_msh(tmp_path):
    """The strongest form of "auto is inert" on the native route: same hash, same bytes."""
    design = _design()
    cfg = _cfg()
    row = _ndjson_row(RUN)
    assert row["mode"] == "screen"

    mspec = mesh_spec("screen", cfg)
    assert mspec.source_cap_mm == 0.0
    assert mspec.hash() == row["mesh_hash"]
    print(f"\nnative screen auto: recorded mesh_hash={row['mesh_hash']} "
          f"({row['n_triangles']} triangles)")

    result = build.build_mesh(design, mspec, cfg, tmp_path / "auto", mode="screen")
    rebuilt = _sha256(result.path)
    stored = _sha256(RUN / "designs" / DESIGN_HASH / "mesh.msh")
    print(f"native screen auto .msh sha256 rebuilt={rebuilt[:12]} stored={stored[:12]} "
          f"tris={result.n_triangles}")
    assert result.n_triangles == row["n_triangles"]
    assert rebuilt == stored


def test_native_auto_mesher_config_has_no_source_override(monkeypatch, tmp_path):
    """``auto`` must not add a ``source`` section: the mesher's own default stays in force."""
    design = _design()
    cfg = _cfg()
    mspec = mesh_spec("screen", cfg)

    mcfg = _capture_mesher_config(design, mspec, cfg, tmp_path / "auto", monkeypatch,
                                  mode="screen")
    assert "source" not in mcfg
    # No cap, but the mesher still derives the auto angle from a0 itself (config_builder:2197).
    assert mcfg["profile"]["a0_deg"] == pytest.approx(1.5333260429)


# ------------------------------------------------------------------ the knob is wired


def test_explicit_cap_reaches_the_native_geometry_and_keeps_the_auto_angle(monkeypatch, tmp_path):
    from hornlab_mesher.config_builder import resolve_geometry

    design = _design()
    auto_cfg = _cfg()
    cap_cfg = _with_cap(auto_cfg, 60)
    auto_spec = mesh_spec("screen", auto_cfg)
    cap_spec = mesh_spec("screen", cap_cfg)

    # Same out_dir for both captures: ``output.path`` is part of the mesher config dict, and the
    # build aborts before any mesh is written, so only ``source`` may differ below.
    common_out = tmp_path / "mcfg"
    auto_mcfg = _capture_mesher_config(design, auto_spec, auto_cfg, common_out, monkeypatch,
                                       mode="screen")
    cap_mcfg = _capture_mesher_config(design, cap_spec, cap_cfg, common_out, monkeypatch,
                                      mode="screen")

    # The fix touches exactly one place: the mesher's top-level ``source`` section.
    assert "source" not in auto_mcfg
    assert cap_mcfg["source"]["source_radius_mm"] == pytest.approx(60.0)
    without_source = {k: v for k, v in cap_mcfg.items() if k != "source"}
    assert without_source == auto_mcfg

    auto_geom = resolve_geometry(auto_mcfg).geometry
    cap_geom = resolve_geometry(cap_mcfg).geometry
    # The mesher prefers an explicit radius; the a0 auto angle stays set in BOTH cases.
    assert auto_geom.source_radius_mm == -1.0
    assert cap_geom.source_radius_mm == pytest.approx(60.0)
    assert auto_geom.source_auto_angle_deg is not None and auto_geom.source_auto_angle_deg > 0.0
    assert cap_geom.source_auto_angle_deg == pytest.approx(auto_geom.source_auto_angle_deg)
    # The cap shapes the throat cap surface; it does not move the horn wall grid.
    assert np.array_equal(np.asarray(auto_geom.inner_points),
                          np.asarray(cap_geom.inner_points))

    h_auto = _geometry_identity(auto_geom)
    h_cap = _geometry_identity(cap_geom)
    print(f"\nnative source.cap auto -> geometry {h_auto[:12]} "
          f"(source_radius_mm={auto_geom.source_radius_mm:g}); "
          f"cap 60 -> {h_cap[:12]} (source_radius_mm={cap_geom.source_radius_mm:g})")
    assert h_auto != h_cap


def test_cap60_native_mesh_is_no_longer_byte_identical_to_auto(tmp_path):
    """The measured bug artifacts: auto is still the stored c59ec195 mesh, cap 60 now differs."""
    design = _design()
    auto_cfg = _cfg(AUTO_BRIEF)
    cap_cfg = _cfg(CAP60_BRIEF)

    auto_row = _ndjson_row(SS2 / "ss_morph_auto")
    cap_row = _ndjson_row(SS2 / "ss_morph_cap60")
    auto_spec = mesh_spec("verify", auto_cfg)
    cap_spec = mesh_spec("verify", cap_cfg)

    # The recorded identities were always distinct; only the geometry was not.
    assert auto_spec.source_cap_mm == 0.0
    assert auto_spec.hash() == auto_row["mesh_hash"] == "7abdb667298f"
    assert cap_spec.source_cap_mm == pytest.approx(60.0)
    assert cap_spec.hash() == cap_row["mesh_hash"] == "c42751b96235"

    stored_auto = SS2 / "ss_morph_auto" / "designs" / DESIGN_HASH / "mesh.msh"
    stored_cap60 = SS2 / "ss_morph_cap60" / "designs" / DESIGN_HASH / "mesh.msh"
    sha_auto = _sha256(stored_auto)
    sha_cap60_stored = _sha256(stored_cap60)
    # PREMISE (the bug, fixed here): cap 60 was served the auto mesh byte for byte.
    assert sha_auto == sha_cap60_stored
    assert sha_auto.startswith("c59ec195933a")

    auto_result = build.build_mesh(design, auto_spec, auto_cfg, tmp_path / "auto", mode="verify")
    cap_result = build.build_mesh(design, cap_spec, cap_cfg, tmp_path / "cap60", mode="verify")

    rebuilt_auto = _sha256(auto_result.path)
    rebuilt_cap60 = _sha256(cap_result.path)
    print(f"\nnative verify .msh sha256 auto rebuilt={rebuilt_auto[:12]} "
          f"cap60 rebuilt={rebuilt_cap60[:12]} stored(auto)={sha_auto[:12]} "
          f"tris auto={auto_result.n_triangles} cap60={cap_result.n_triangles}")
    # auto stays exactly the stored mesh; the explicit cap is now a real geometry change.
    assert rebuilt_auto == sha_auto
    assert rebuilt_cap60 != sha_auto


# ------------------------------------------------------------------ mesh identity


def test_mesh_spec_hash_is_unchanged_for_native_auto_and_changes_with_the_cap():
    screen_row = _ndjson_row(RUN)                       # 8e789cd0deef, screen / 8 kHz
    auto_12k = _ndjson_row(SS2 / "ss_morph_auto")       # 7abdb667298f, verify / 12 kHz
    cap60_12k = _ndjson_row(SS2 / "ss_morph_cap60")     # c42751b96235
    cap150_12k = _ndjson_row(SS2 / "ss_morph_cap150")   # bcf9a8cec98b

    screen_auto = mesh_spec("screen", _cfg())
    verify_auto = mesh_spec("verify", _cfg(AUTO_BRIEF))
    verify_cap60 = mesh_spec("verify", _cfg(CAP60_BRIEF))
    verify_cap150 = mesh_spec("verify", _cfg(CAP150_BRIEF))

    # auto = 0.0 = the default that is dropped from the hash input: every stored hash is kept.
    assert screen_auto.source_cap_mm == 0.0
    assert verify_auto.source_cap_mm == 0.0
    assert screen_auto.hash() == screen_row["mesh_hash"] == "8e789cd0deef"
    assert verify_auto.hash() == auto_12k["mesh_hash"] == "7abdb667298f"

    # An explicit cap is in the identity, and the stored cap variants keep their recorded values.
    assert verify_cap60.source_cap_mm == pytest.approx(60.0)
    assert verify_cap150.source_cap_mm == pytest.approx(150.0)
    assert verify_cap60.hash() == cap60_12k["mesh_hash"] == "c42751b96235"
    assert verify_cap150.hash() == cap150_12k["mesh_hash"] == "bcf9a8cec98b"
    assert len({verify_auto.hash(), verify_cap60.hash(), verify_cap150.hash()}) == 3
