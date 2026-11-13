"""S0 catalog.py — fixed-fixture tests for the read-only experiment catalog.

The fixture is a synthetic dataset root shaped exactly like ``DatasetStore`` writes it:
metadata lines in ``shard-NNNN.jsonl``, one ``shard-NNNN/rec-RRRR.npz`` per successful
record, and a separate ``index.jsonl``.  It deliberately includes a torn active-shard tail,
an index orphan, a record missing from the index, a corrupt NPZ, missing required arrays,
missing loading input, a missing provenance block, duplicate cache rows and a failed record.
No live data is touched; every test asserts the source bytes are unchanged.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from test_tools_analysis_common import load_tool, run_cli, run_json_payload

cat = load_tool("catalog")

LIB = {k: "a" * 40 for k in
       ("hornlab_mesher", "hornlab_best", "hornlab_bempp_bem", "hornlab_plots",
        "hornlab_search")}
LIB["hornlab_beat_bem"] = LIB.pop("hornlab_best")
LIB_SHA = "a" * 10 + "+" + "a" * 10
ATH_BRIEF = "native_ath_core_2in_v4"
ATH_HASH = "fa45251216b5"

FREQS = [300.0, 1000.0, 8000.0]
ANGLES = [-45.0, 0.0, 45.0]
BAL_DIRS = [[0.0, 0.0, 1.0], [0.2, 0.0, 0.98]]


def arrays(*, balloon: bool = True, loading: bool = True) -> dict:
    out = {
        "freqs_hz": np.array(FREQS, dtype=float),
        "h_angles_deg": np.array(ANGLES, dtype=float),
        "v_angles_deg": np.array(ANGLES, dtype=float),
        "spl_h_db": np.full((3, 3), 80.0),
        "spl_v_db": np.full((3, 3), 79.0),
        "on_axis_db": np.full(3, 80.0),
    }
    if balloon:
        out["balloon_dirs"] = np.array(BAL_DIRS, dtype=float)
        out["spl_balloon_db"] = np.full((3, 2), 70.0)
    if loading:
        out["z_throat"] = np.full(3, 1.2, dtype=complex)
    return out


def terms(*, di_estimated=0.0, penalty=0.0) -> dict:
    return {"cov": 0.4, "rip": 0.2, "di": 0.3, "dislope": 0.1, "flat": 0.2,
            "load": 0.0, "distd": 0.1, "diag": 0.2, "penalty": penalty,
            "total": 1.5 + penalty, "n_nan": 0, "n_in_band": 3,
            "di_estimated": di_estimated}


def meta(i: int, *, ok: bool = True, version: int = 4, brief: str = ATH_BRIEF,
         brief_hash: str = ATH_HASH, run_id: str | None = "run-a",
         config_name: str | None = "cfgA", provenance: bool = True,
         design_hash: str | None = None, mesh_hash: str = "mesh0",
         solve_hash: str | None = None, mode: str = "screen",
         backend: str = "beat_cuda", di_estimated=0.0,
         generator: dict | None = None) -> dict:
    dh = design_hash or f"d{i:04d}"
    sh = solve_hash or f"s{i:04d}"
    target = {
        "coverage_h_deg": 50.0, "coverage_v_deg": 50.0,
        "band_lo_hz": 300.0, "band_hi_hz": 8000.0, "f0_hz": 1280.0,
        "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
        "freq_weights": {"band_hz": [[2500.0, 5500.0, 2.0]]},
    }
    out = {
        "schema_version": 1,
        "design_hash": dh, "mesh_hash": mesh_hash, "solve_hash": sh,
        "family": "OSSE",
        "params": {"L_mm": 260.0, "a_deg": 24.2},
        "target": target,
        "mesh": {"n_triangles": 100, "n_dof": 200, "quadrants": "1",
                 "res_mm": {"throat": 4.0, "mouth": 8.0, "rear": None},
                 "bbox_m": [0.0, 0.0, 0.0, 0.4, 0.4, 0.3], "area_m2": 0.2,
                 "seconds": 1.0,
                 "grid": {"angular_segments": 64, "length_segments": 32,
                          "available": True}},
        "solve": {"backend": backend, "mode": mode, "freqs_hz": FREQS,
                  "observation": {"distance_m": 2.0, "angle_count": 3,
                                  "balloon": True, "balloon_points": 2},
                  "gmres_tol": 1e-5, "seconds": 2.0, "peak_vram_mb": 10.0,
                  "n_dof": 200},
        "excitation": {"port_tag": 2, "port_name": "SD1D1001",
                       "kind": "uniform_normal_velocity", "amplitude": 1.0,
                       "units": "m/s", "frequency_dependent": False, "notes": ""},
        "traces": {"captured": False, "path": None, "kind": None,
                   "sample_fraction": 0.05},
        "metrics_scalars": {"di_source": "balloon", "n_freqs": 3},
        "objective": 5.0 if ok else 1000.0,
        "terms": terms(di_estimated=di_estimated) if ok else terms(penalty=1000.0),
        "objective_version": version,
        "ok": ok,
        "error": "" if ok else "invalid_geometry: synthetic refusal",
        "created_utc": f"2026-11-12T10:00:{i:02d}Z",
        "lib_shas": dict(LIB),
    }
    if provenance:
        prov = {"config": config_name, "brief": brief, "brief_hash": brief_hash}
        if generator is not None:
            prov["generator"] = generator
        out["provenance"] = prov
    if run_id:
        out["run_id"] = run_id
    if config_name:
        out["config_name"] = config_name
    return out


def _index_entry(meta_dict: dict, shard: int, row: int) -> dict:
    solve = meta_dict["solve"]
    return {"design_hash": meta_dict["design_hash"], "shard": shard, "row": row,
            "objective": meta_dict["objective"], "ok": meta_dict["ok"],
            "family": meta_dict["family"], "backend": solve["backend"],
            "mode": solve["mode"], "lib_sha": LIB_SHA,
            "created_utc": meta_dict["created_utc"], "solve_seconds": 2.0,
            "traces": False}


def write_fixture(root: Path) -> dict:
    """Write the synthetic dataset root and return a few expected counts."""
    root.mkdir(parents=True, exist_ok=True)
    shard0 = [
        meta(0, run_id="run-a"),
        meta(1, run_id="run-b", config_name="cfgB", design_hash="d0000",
             solve_hash="s0000"),          # duplicate physical solve of record 0
        meta(2, run_id="run-c"),
        meta(3, run_id="run-a"),          # missing balloon
        meta(4, run_id="run-a"),          # missing z_throat
        meta(5, run_id="run-a", di_estimated=1.0),  # gate incomplete
        meta(6, run_id=None, config_name=None),     # torn npz + experiment unknown
        meta(7, version=1, provenance=False, run_id=None, config_name=None),
        meta(8, ok=False, run_id="run-a"),          # failed
        meta(9, brief="other_brief", brief_hash="bbbbbbbbbbbb", run_id="run-x"),
    ]
    shard1 = [
        meta(10, run_id="run-d", config_name="cfgA"),
    ]
    root.mkdir(exist_ok=True)
    for shard, metas in ((0, shard0), (1, shard1)):
        d = root / f"shard-{shard:04d}"
        d.mkdir(exist_ok=True)
        with (root / f"shard-{shard:04d}.jsonl").open("w", encoding="utf-8") as f:
            for i, m in enumerate(metas):
                f.write(json.dumps(m, separators=(",", ":")) + "\n")
                if m["ok"]:
                    if shard == 0 and i == 3:
                        np.savez(d / f"rec-{i:04d}.npz", **arrays(balloon=False))
                    elif shard == 0 and i == 4:
                        np.savez(d / f"rec-{i:04d}.npz", **arrays(loading=False))
                    elif shard == 0 and i == 6:
                        (d / f"rec-{i:04d}.npz").write_bytes(b"this is not a zip")
                    else:
                        np.savez(d / f"rec-{i:04d}.npz", **arrays())
        if shard == 1:
            # Torn, uncommitted tail in the active shard: no newline, never a record.
            with (root / "shard-0001.jsonl").open("a", encoding="utf-8") as f:
                f.write('{"schema_version":1,"design_hash":"torn"')

    # Index: omit record 2 (record_without_index), add an orphan (index_without_record),
    # and leave a torn tail in index.jsonl.
    with (root / "index.jsonl").open("w", encoding="utf-8") as f:
        for shard, metas in ((0, shard0), (1, shard1)):
            for i, m in enumerate(metas):
                if shard == 0 and i == 2:
                    continue
                f.write(json.dumps(_index_entry(m, shard, i),
                                   separators=(",", ":")) + "\n")
        f.write(json.dumps({"design_hash": "orphan", "shard": 1, "row": 5,
                            "objective": 1.0, "ok": True, "family": "OSSE",
                            "backend": "beat_cuda", "mode": "screen",
                            "lib_sha": LIB_SHA, "created_utc": None,
                            "solve_seconds": None, "traces": False},
                           separators=(",", ":")) + "\n")
        f.write('{"design_hash":"torn-index"')

    return {"records": len(shard0) + len(shard1), "index_rows": len(shard0) + len(shard1) - 1 + 1}


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


# ------------------------------------------------------------------ tests


def test_scan_counts_records_and_index_separately_with_coherence(tmp_path):
    root = tmp_path / "dataset"
    expected = write_fixture(root)
    scan = cat.scan_root(root)
    c = scan["counts"]
    assert c["records"] == expected["records"] == 11
    assert c["index_rows"] == expected["index_rows"] == 11
    assert c["records_ok"] == 10 and c["records_failed"] == 1
    assert c["record_without_index"] == 1
    assert c["index_orphans"] == 1
    assert c["shard_torn_tail_bytes"] > 0
    assert c["index_torn_tail_bytes"] > 0
    assert scan["coherence"]["record_without_index"] == 1
    assert scan["coherence"]["index_without_record"] == 1
    assert any(e["reason"] == "torn_tail_skipped" for e in scan["exclusions"])


def test_duplicate_cache_rows_do_not_inflate_unique_solves_or_geometries(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    scan = cat.scan_root(root)
    # Globally: 10 successful rows, but d0 appears twice under different runs -> 9 solves.
    assert scan["counts"]["records_ok"] == 10
    assert scan["counts"]["unique_physical_solves"] == 9
    assert scan["counts"]["unique_geometries"] == 9
    # The ATH cohort alone: 8 successful rows, d0 duplicated -> 7 independent solves.
    ath = cat.records_for(scan, brief=ATH_BRIEF, ok=True)
    assert len(ath) == 8
    assert len({r["physical_solve_id"] for r in ath}) == 7
    assert len({r["geometry_id"] for r in ath}) == 7


def test_missing_provenance_flagged_not_inferred(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    scan = cat.scan_root(root)
    rec = next(r for r in scan["records"] if r["design_hash"] == "d0007")
    assert "provenance_missing" in rec["unknowns"]
    assert "run_id_missing" in rec["unknowns"]
    assert "config_missing" in rec["unknowns"]
    assert rec["experiment_id"] is None
    assert rec["score_identity"]


def test_missing_arrays_and_gates_are_partial_not_complete(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    scan = cat.scan_root(root)
    by_dh = {r["design_hash"]: r for r in scan["records"]}
    assert by_dh["d0000"]["completeness"]["classification"] == "complete"
    assert by_dh["d0003"]["completeness"]["classification"] == "partial_unsupported"
    assert by_dh["d0003"]["completeness"]["missing_score_arrays"] == [
        "balloon_dirs", "spl_balloon_db"]
    assert by_dh["d0004"]["completeness"]["classification"] == "partial_loading_inputs"
    assert by_dh["d0004"]["completeness"]["missing_loading_arrays"] == ["z_throat"]
    assert by_dh["d0005"]["completeness"]["classification"] == "gate_incomplete"
    assert "di_estimated_cuts" in by_dh["d0005"]["completeness"]["gate_failures"]
    assert by_dh["d0006"]["completeness"]["classification"] == "torn_artifact"
    assert by_dh["d0000"]["completeness"]["complete_replayable"] is True
    assert by_dh["d0003"]["completeness"]["complete_replayable"] is False


def test_npz_shape_mismatch_is_not_complete(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    m = meta(0)
    (root / "shard-0000").mkdir()
    (root / "shard-0000.jsonl").write_text(
        json.dumps(m, separators=(",", ":")) + "\n", encoding="utf-8")
    bad = arrays()
    bad["spl_h_db"] = np.zeros((2, 3))  # solve grid has 3 frequencies
    np.savez(root / "shard-0000" / "rec-0000.npz", **bad)
    (root / "index.jsonl").write_text(
        json.dumps(_index_entry(m, 0, 0), separators=(",", ":")) + "\n", encoding="utf-8")
    comp = cat.scan_root(root)["records"][0]["completeness"]
    assert comp["classification"] == "shape_incoherent"
    assert comp["complete_replayable"] is False
    assert any("spl_h_db" in issue for issue in comp["shape_issues"])


def test_selective_array_summary_does_not_dump_all_arrays(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    scan = cat.scan_root(root, selected_arrays=["on_axis_db"])
    rec = next(r for r in scan["records"] if r["design_hash"] == "d0000")
    selected = rec["arrays"]["selected"]
    assert set(selected) == {"on_axis_db"}
    assert selected["on_axis_db"]["shape"] == [3]
    assert selected["on_axis_db"]["dtype"] == "float64"
    assert set(rec["arrays"]["keys"]) >= {"spl_h_db", "spl_balloon_db"}
    assert "spl_h_db" not in selected


def test_generator_knobs_recovered_from_provenance_only(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    gen = {"name": "grid", "spec": {"name": "grid"}, "knobs": {"a_deg": 20.0},
           "brief": ATH_BRIEF, "brief_hash": ATH_HASH}
    m = meta(0, generator=gen)
    (root / "shard-0000").mkdir()
    (root / "shard-0000.jsonl").write_text(
        json.dumps(m, separators=(",", ":")) + "\n", encoding="utf-8")
    np.savez(root / "shard-0000" / "rec-0000.npz", **arrays())
    (root / "index.jsonl").write_text(
        json.dumps(_index_entry(m, 0, 0), separators=(",", ":")) + "\n", encoding="utf-8")
    scan = cat.scan_root(root)
    gen_out = scan["records"][0]["provenance"]["generator"]
    assert gen_out["knob_source"] == "provenance.generator.knobs"
    assert gen_out["knobs"] == {"a_deg": 20.0}
    assert gen_out["knobs_unknown"] is False


def test_torn_and_live_tail_handled_without_writes(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    before = snapshot(root)
    scan = cat.scan_root(root)
    after = snapshot(root)
    assert before == after, "catalog must never repair or rewrite a source root"
    assert scan["active_shard"] == 1
    assert scan["counts"]["records"] == 11
    assert scan["shards"][-1]["torn_tail_bytes"] > 0
    assert not (root / "out").exists()


def test_fixed_fixture_export_is_deterministic(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    fixed = "2026-11-12T00:00:00Z"
    cat.write_catalog(cat.scan_root(root), out1, generated_utc=fixed)
    cat.write_catalog(cat.scan_root(root), out2, generated_utc=fixed)
    assert (out1 / "catalog.json").read_bytes() == (out2 / "catalog.json").read_bytes()
    assert (out1 / "catalog.csv").read_bytes() == (out2 / "catalog.csv").read_bytes()
    doc = run_json_payload(out1, "catalog")
    assert doc["generated_utc"] == fixed
    assert doc["counts"]["records"] == 11


def test_refuses_to_write_inside_a_source_root(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    with pytest.raises(ValueError, match="refusing to write inside"):
        cat.write_catalog(cat.scan_root(root), root / "out")


def test_cli_writes_json_md_csv(tmp_path):
    root = tmp_path / "dataset"
    write_fixture(root)
    out = tmp_path / "out"
    proc = run_cli("catalog", ["--root", str(root), "--array", "on_axis_db"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "catalog OK" in proc.stdout
    doc = run_json_payload(out, "catalog")
    assert doc["tool"] == "catalog" and doc["counts"]["records"] == 11
    assert (out / "catalog.md").exists() and (out / "catalog.csv").exists()
    assert "Experiment catalog" in (out / "catalog.md").read_text(encoding="utf-8")
