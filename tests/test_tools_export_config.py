"""Tests for tools/export_config.py. Offline: config export only, no mesher, no solve."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.mesh.build import mounting_of, res_mm_for_spec
from hornlab_search.types import Design
from test_dataset_factory import LIB_SHAS

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import export_config  # noqa: E402


def _run_dir(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "20261031T201057Z-screen-d3158e"
    run.mkdir(parents=True)
    shutil.copyfile(REPO / "examples" / "search_smoke.yaml", run / "config.yaml")
    (run / "run.json").write_text(json.dumps({
        "run_id": run.name, "mode": "screen", "config_name": "search_smoke",
        "lib_shas": LIB_SHAS,
    }), encoding="utf-8")
    seed = {"r0_mm": 17.78, "a_deg": 37.5, "a0_deg": 15.5, "L_mm": 260.0, "n": 4.0,
            "s": 0.7, "q": 0.995, "k": 1.0, "exponent": 4.0, "aspect_ratio": 1.25}
    rows = [
        {"n": 0, "design_hash": "aaaaaaaaaaaa", "family": "OSSE", "ok": True,
         "objective": 2.0, "objective_version": 7, "params": seed,
         "terms": {"total": 2.0}},
        {"n": 1, "design_hash": "bbbbbbbbbbbb", "family": "OSSE", "ok": True,
         "objective": 1.0, "objective_version": 7, "params": dict(seed, L_mm=200.0),
         "terms": {"total": 1.0}},
        {"n": 2, "design_hash": "cccccccccccc", "family": "FREEFORM", "ok": True,
         "objective": 3.0, "objective_version": 7,
         "params": {"grid": {"knobs": {"a_deg": 30.0}}}, "terms": {"total": 0.5}},
        {"n": 3, "design_hash": "dddddddddddd", "family": "OSSE", "ok": False,
         "objective": 1000.0, "params": seed, "error": "mesh_too_large"},
    ]
    (run / "search.ndjson").write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    return run


def test_export_writes_exact_mesher_config_and_meta(tmp_path):
    run = _run_dir(tmp_path)
    out = tmp_path / "out"
    doc = export_config.export_run(run, top=2, out=out)

    assert doc["written"] == ["bbbbbbbbbbbb", "aaaaaaaaaaaa"]
    assert doc["skipped"] == []                      # the grid row did not make the top 2
    mesher = json.loads((out / "bbbbbbbbbbbb.mesher.json").read_text(encoding="utf-8"))
    meta = json.loads((out / "bbbbbbbbbbbb.meta.json").read_text(encoding="utf-8"))

    cfg = load_config(run / "config.yaml")
    mesh = mesh_spec("screen", cfg)
    res = res_mm_for_spec(mesh, cfg)
    design = Design(family="OSSE", params=json.loads((out / "bbbbbbbbbbbb.meta.json")
                                                     .read_text(encoding="utf-8"))["params"])
    expected = families.to_mesher_config(
        design, mesh, res, run / "designs" / "bbbbbbbbbbbb" / "mesh.msh",
        mounting=mounting_of(cfg))
    assert mesher == expected
    assert mesher["formula"] == "OSSE" and mesher["mesh"]["scale_to_metres"] is True

    assert meta["family"] == "OSSE" and meta["J"] == 1.0
    assert meta["objective_version"] == 7
    assert meta["terms"] == {"total": 1.0}
    assert meta["lib_sha"].startswith(LIB_SHAS["hornlab_mesher"][:10])
    assert meta["run_id"] == run.name and meta["config_name"] == "search_smoke"


def test_export_lists_generator_designs_as_skipped_with_reason(tmp_path):
    run = _run_dir(tmp_path)
    out = tmp_path / "out"
    doc = export_config.export_run(run, top=3, out=out)
    assert doc["written"] == ["bbbbbbbbbbbb", "aaaaaaaaaaaa"]
    assert [s["design_hash"] for s in doc["skipped"]] == ["cccccccccccc"]
    reason = doc["skipped"][0]["reason"]
    assert "grid" in reason and "to_mesher_config" in reason
    assert json.loads((out / "skipped.json").read_text(encoding="utf-8")) == doc["skipped"]
    assert not (out / "cccccccccccc.mesher.json").exists()


def test_select_top_dedupes_designs_and_ignores_failures():
    rows = [
        {"design_hash": "a", "ok": True, "objective": 5.0, "n": 0},
        {"design_hash": "a", "ok": True, "objective": 3.0, "n": 2},
        {"design_hash": "b", "ok": True, "objective": 4.0, "n": 1},
        {"design_hash": "c", "ok": False, "objective": 0.1, "n": 3},
        {"design_hash": "d", "ok": True, "objective": float("nan"), "n": 4},
    ]
    top = export_config.select_top(rows, 5)
    assert [r["design_hash"] for r in top] == ["a", "b"]
    assert top[0]["objective"] == 3.0
