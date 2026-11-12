"""Offline tests for ``tools/data/doctor.py`` (Phase 4 read-only data integrity report).

Hermetic: a synthetic runs/cache/dataset tree under ``tmp_path`` only. No GPU, no solver, no
real run or dataset bytes, no subprocess. The tool is loaded by path, matching the
``tests/test_tools_*.py`` convention.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

from conftest import REPO

TOOL = REPO / "tools" / "data" / "doctor.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("doctor_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


doctor = _load_tool()


# ------------------------------------------------------------------ synthetic tree

D1, M1, S1 = "aaaa00000001", "111111111111", "222222222222"
D2, M2, S2 = "bbbb00000002", "333333333333", "444444444444"
D3, M3, S3 = "cccc00000003", "555555555555", "666666666666"

MESH_KEY = f"{D1}-{M1}"
SOLVE_KEY = f"{D1}-{M1}-{S1}"
UNREF_MESH = "deadbeef0000-cafebabe0000"
UNREF_SOLVE = "deadbeef0001-cafebabe0001-abcd00000001"

REF_TRACE = b"referenced-trace-bytes"
ORPHAN_TRACE = b"orphan-trace-bytes-longer"
MISSING_TRACE = b"missing-trace-bytes"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def _record(design: str, mesh: str, solve: str, *, ok: bool,
            trace: str | None = None) -> dict:
    return {
        "design_hash": design,
        "mesh_hash": mesh,
        "solve_hash": solve,
        "ok": ok,
        "traces": {"path": trace},
    }


def _make_tree(tmp_path: Path, *, missing_trace: bool = True) -> dict:
    dataset = tmp_path / "dataset"
    traces = dataset / "traces"
    runs = tmp_path / "runs"
    cache_mesh = tmp_path / "cache" / "mesh"
    cache_solve = tmp_path / "cache" / "solve"

    # Two shards: shard 0 has a duplicate pair and one failed record; shard 1 has the
    # missing-trace record. 4 records total, 3 ok, 1 failed.
    _write_jsonl(dataset / "shard-0000.jsonl", [
        _record(D1, M1, S1, ok=True, trace="traces/ref.npz"),
        _record(D1, M1, S1, ok=True, trace=None),
        _record(D2, M2, S2, ok=False, trace=None),
    ])
    _write_jsonl(dataset / "shard-0001.jsonl", [
        # The traces field may also be a plain string, not a dict with ``path``.
        {"design_hash": D3, "mesh_hash": M3, "solve_hash": S3, "ok": True,
         "traces": "traces/missing.npz"},
    ])
    # Arrays for the first ok record only; the failed record has none.
    _write(dataset / "shard-0000" / "rec-0000.npz", b"arrays-0")
    _write(dataset / "shard-0001" / "rec-0000.npz", b"arrays-1")

    _write(traces / "ref.npz", REF_TRACE)
    _write(traces / "orphan.npz", ORPHAN_TRACE)
    if not missing_trace:
        _write(traces / "missing.npz", MISSING_TRACE)

    # Cache: the referenced entries are named by the run metadata keys; the planted
    # unreferenced entries match nothing.
    _write(cache_mesh / MESH_KEY / "mesh.msh", b"mesh-bytes")
    _write_json(cache_mesh / MESH_KEY / "mesh_meta.json", {"key": MESH_KEY})
    _write(cache_mesh / UNREF_MESH / "mesh.msh", b"unreferenced-mesh")
    _write(cache_solve / SOLVE_KEY / "response.npz", b"response-bytes")
    _write_json(cache_solve / SOLVE_KEY / "status.json", {"key": SOLVE_KEY})
    _write(cache_solve / UNREF_SOLVE / "response.npz", b"unreferenced-solve")

    # Two run design dirs.  Run A's heavy files are hardlinks to their cache entries
    # (st_nlink == 2); run B's are plain copies (st_nlink == 1).
    run_a = runs / "runA"
    design_a = run_a / "designs" / D1
    _write_json(design_a / "design.json", {"design_hash": D1})
    _write_json(design_a / "mesh_meta.json", {"key": MESH_KEY})
    _write_json(design_a / "status.json", {"ok": True, "key": SOLVE_KEY})
    os.link(cache_mesh / MESH_KEY / "mesh.msh", design_a / "mesh.msh")
    os.link(cache_solve / SOLVE_KEY / "response.npz", design_a / "response.npz")
    _write_jsonl(run_a / "search.ndjson", [{"key": SOLVE_KEY}])

    run_b = runs / "runB"
    design_b = run_b / "designs" / D2
    _write_json(design_b / "design.json", {"design_hash": D2})
    _write_json(design_b / "mesh_meta.json", {"key": f"{D2}-{M2}"})
    _write_json(design_b / "status.json", {"ok": False, "key": f"{D2}-{M2}-{S2}"})
    _write(design_b / "mesh.msh", b"unlinked-mesh")
    _write(design_b / "response.npz", b"unlinked-response")

    # A backup that is a subset of the main dataset.
    _write_jsonl(tmp_path / "dataset_backup_20260101" / "shard-0000.jsonl", [
        _record(D1, M1, S1, ok=True, trace=None),
    ])

    return {
        "runs": runs,
        "cache_mesh": cache_mesh,
        "cache_solve": cache_solve,
        "dataset": dataset,
        "design_a": design_a,
        "design_b": design_b,
        "ref_trace": traces / "ref.npz",
        "orphan_trace": traces / "orphan.npz",
        "missing_trace": traces / "missing.npz",
    }


def _run(t: dict) -> dict:
    return doctor.run(
        runs=t["runs"],
        cache_mesh=t["cache_mesh"],
        cache_solve=t["cache_solve"],
        dataset=t["dataset"],
    )


def _argv(t: dict, *extra: str) -> list[str]:
    return [
        "--runs", str(t["runs"]),
        "--cache-mesh", str(t["cache_mesh"]),
        "--cache-solve", str(t["cache_solve"]),
        "--dataset", str(t["dataset"]),
        *extra,
    ]


# ------------------------------------------------------------------ 1. records/duplicates


def test_record_counts_and_duplicate_groups(tmp_path):
    t = _make_tree(tmp_path)
    doc = _run(t)

    records = doc["records"]
    assert records["total_records"] == 4
    assert records["ok_true"] == 3
    assert records["ok_false"] == 1
    assert records["distinct_pairs"] == 3
    assert records["failed_without_arrays"] == 1
    assert records["errors"] == []

    counts = {Path(s["path"]).name: s["line_count"] for s in records["shards"]}
    assert counts == {"shard-0000.jsonl": 3, "shard-0001.jsonl": 1}

    duplicates = doc["duplicates"]
    assert duplicates["group_count"] == 1
    assert duplicates["extra_rows"] == 1
    assert duplicates["sample"] == [
        {"pair": f"{D1}-{S1}", "count": 2},
    ]


# ------------------------------------------------------------------ 2. traces


def test_orphan_and_missing_trace_samples(tmp_path):
    t = _make_tree(tmp_path)
    doc = _run(t)

    traces = doc["traces"]
    assert traces["files_on_disk"] == 2
    assert traces["referenced_names"] == 2

    assert traces["orphans"]["count"] == 1
    assert traces["orphans"]["bytes"] == len(ORPHAN_TRACE)
    assert [Path(s["path"]).name for s in traces["orphans"]["sample"]] == ["orphan.npz"]

    assert traces["missing"]["count"] == 1
    assert traces["missing"]["sample"] == ["missing.npz"]


# ------------------------------------------------------------------ 3. cache references


def test_only_planted_cache_entries_are_unreferenced(tmp_path):
    t = _make_tree(tmp_path)
    doc = _run(t)

    mesh = doc["cache"]["mesh"]
    assert mesh["entries"] == 2
    assert mesh["referenced"] == 1
    assert mesh["unreferenced"]["count"] == 1
    assert [Path(s["path"]).name for s in mesh["unreferenced"]["sample"]] == [UNREF_MESH]
    reported = {Path(s["path"]).name for s in mesh["unreferenced"]["sample"]}
    assert MESH_KEY not in reported

    solve = doc["cache"]["solve"]
    assert solve["entries"] == 2
    assert solve["referenced"] == 1
    assert solve["unreferenced"]["count"] == 1
    assert [Path(s["path"]).name for s in solve["unreferenced"]["sample"]] == [UNREF_SOLVE]
    reported = {Path(s["path"]).name for s in solve["unreferenced"]["sample"]}
    assert SOLVE_KEY not in reported


# ------------------------------------------------------------------ 4. run heavy files


def test_not_linked_run_files_are_exactly_the_planted_one(tmp_path):
    t = _make_tree(tmp_path)
    doc = _run(t)

    heavy = doc["run_heavy"]
    assert heavy["design_dirs_scanned"] == 2
    for kind, filename in (("mesh", "mesh.msh"), ("response", "response.npz")):
        section = heavy[kind]
        assert section["scanned"] == 2
        assert section["linked"] == 1
        assert section["not_linked"] == 1
        assert [Path(s["path"]).name for s in section["sample"]] == [filename]
        assert Path(section["sample"][0]["path"]).parent == t["design_b"]
        assert section["not_linked_bytes"] == (t["design_b"] / filename).stat().st_size


def test_limit_caps_design_dirs_scanned(tmp_path):
    t = _make_tree(tmp_path)
    doc = doctor.run(
        runs=t["runs"],
        cache_mesh=t["cache_mesh"],
        cache_solve=t["cache_solve"],
        dataset=t["dataset"],
        limit=1,
    )
    assert doc["run_heavy"]["design_dirs_scanned"] == 1
    assert doc["run_heavy"]["mesh"]["scanned"] == 1


# ------------------------------------------------------------------ 5. backups


def test_backup_subset_is_reported(tmp_path):
    t = _make_tree(tmp_path)
    doc = _run(t)

    assert len(doc["backups"]) == 1
    backup = doc["backups"][0]
    assert backup["record_count"] == 1
    assert backup["subset"] is True
    assert backup["missing_count"] == 0


# ------------------------------------------------------------------ 6. exit codes + JSON


def test_json_report_round_trips(tmp_path):
    t = _make_tree(tmp_path)
    out = tmp_path / "reports" / "doctor.json"

    assert doctor.main(_argv(t, "--json", str(out), "--quiet")) == 1

    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert set(loaded) == {
        "generated_utc", "paths", "limit", "records", "duplicates", "traces",
        "cache", "run_heavy", "backups", "findings",
    }
    assert loaded["records"]["total_records"] == 4
    assert loaded["duplicates"]["group_count"] == 1
    assert loaded["cache"]["mesh"]["unreferenced"]["count"] == 1
    assert loaded["run_heavy"]["mesh"]["not_linked"] == 1


def test_exit_code_is_one_only_with_a_missing_trace(tmp_path):
    clean = _make_tree(tmp_path / "clean", missing_trace=False)
    assert doctor.main(_argv(clean, "--quiet")) == 0
    clean_doc = _run(clean)
    assert clean_doc["traces"]["missing"]["count"] == 0
    assert not [f for f in clean_doc["findings"] if f["severity"] == "ERROR"]

    broken = _make_tree(tmp_path / "broken", missing_trace=True)
    assert doctor.main(_argv(broken, "--quiet")) == 1
    broken_doc = _run(broken)
    assert broken_doc["traces"]["missing"]["count"] == 1
    errors = [f for f in broken_doc["findings"] if f["severity"] == "ERROR"]
    assert [f["section"] for f in errors] == ["traces"]
