"""Offline tests for ``tools/data/keepers.py`` (Phase 4 derived keepers index).

Hermetic: synthetic ``tmp_path`` dataset shards only. No GPU, no solver, no real dataset bytes,
no subprocess. The tool is loaded by path, matching the ``tests/test_tools_*.py`` convention.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

from conftest import REPO

TOOL = REPO / "tools" / "data" / "keepers.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("keepers_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


keepers = _load_tool()


# ------------------------------------------------------------------ synthetic dataset

TARGET_A = {"coverage_h_deg": 75.0, "coverage_v_deg": 45.0, "band_hi_hz": 5500.0}
TARGET_B = {"coverage_h_deg": 75.0, "coverage_v_deg": 45.0, "band_hi_hz": 6000.0}


def _record(design, solve, *, mesh="111111111111", family="OSSE", objective=1.0,
            ok=True, target=None, params=None, n_dof=None,
            created="2026-01-01T00:00:00Z"):
    mesh_block: dict = {}
    if n_dof is not None:
        mesh_block["n_dof"] = n_dof
    return {
        "design_hash": design,
        "solve_hash": solve,
        "mesh_hash": mesh,
        "family": family,
        "objective": objective,
        "ok": ok,
        "created_utc": created,
        "target": dict(TARGET_A if target is None else target),
        "params": dict(params or {}),
        "mesh": mesh_block,
        "metrics_scalars": {},
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def _make_dataset(tmp_path: Path, records: list[dict], name: str = "ds") -> Path:
    dataset = tmp_path / name / "dataset"
    _write_jsonl(dataset / "shard-0000.jsonl", records)
    return dataset


def _run(tmp_path: Path, records: list[dict], name: str = "ds") -> tuple[dict, Path]:
    dataset = _make_dataset(tmp_path, records, name=name)
    out = tmp_path / name / "views" / "keepers.csv"
    doc = keepers.run(dataset=dataset, out=out)
    return doc, out


def _csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


# ------------------------------------------------------------------ 1. dedupe

def test_unique_pairs_and_collapse_count(tmp_path):
    records = [
        _record("d1", "s1", objective=2.0),
        _record("d1", "s1", objective=1.0),  # duplicate: first occurrence wins
        _record("d2", "s2", objective=5.0),
        _record("d3", "s3", ok=False, objective=0.5),
    ]
    doc, out = _run(tmp_path, records)

    assert doc["records_read"] == 4
    assert doc["unique_rows"] == 3
    assert doc["collapsed_extras"] == 1

    header, rows = _csv_rows(out)
    assert len(rows) == 3
    pairs = [(row["design_hash"], row["solve_hash"]) for row in rows]
    assert pairs.count(("d1", "s1")) == 1
    assert set(pairs) == {("d1", "s1"), ("d2", "s2"), ("d3", "s3")}

    first = next(row for row in rows if row["design_hash"] == "d1")
    assert float(first["objective"]) == 2.0


# ------------------------------------------------------------------ 2. best flags

def test_best_flags_lowest_objective_and_failed_rows_never_win(tmp_path):
    records = [
        _record("d1", "s1", family="OSSE", target=TARGET_A, objective=5.0),
        _record("d2", "s2", family="OSSE", target=TARGET_A, objective=3.0),
        _record("d3", "s3", family="OSSE", target=TARGET_A, objective=3.0),  # tie
        # Failed row with the lowest objective must never be flagged.
        _record("d4", "s4", family="OSSE", target=TARGET_A, objective=0.5, ok=False),
        _record("d5", "s5", family="ICW", target=TARGET_B, objective=1.0),
        _record("d6", "s6", family="ICW", target=TARGET_B, objective=7.0),
    ]
    doc, out = _run(tmp_path, records)
    _header, rows = _csv_rows(out)
    by_design = {row["design_hash"]: row for row in rows}

    # Lowest ok objective in (TARGET_A, OSSE) is 3.0: both tied rows win.
    assert by_design["d1"]["is_best_in_target"] == "0"
    assert by_design["d2"]["is_best_in_target"] == "1"
    assert by_design["d3"]["is_best_in_target"] == "1"
    assert by_design["d4"]["is_best_in_target"] == "0"
    # Same group is the whole OSSE family (only target A in OSSE).
    assert by_design["d1"]["is_best_in_family"] == "0"
    assert by_design["d2"]["is_best_in_family"] == "1"
    assert by_design["d3"]["is_best_in_family"] == "1"
    assert by_design["d4"]["is_best_in_family"] == "0"
    # ICW group: only the lowest row wins.
    assert by_design["d5"]["is_best_in_target"] == "1"
    assert by_design["d5"]["is_best_in_family"] == "1"
    assert by_design["d6"]["is_best_in_target"] == "0"
    assert by_design["d6"]["is_best_in_family"] == "0"

    assert doc["best_in_target_rows"] == 3
    assert doc["best_in_family_rows"] == 3


# ------------------------------------------------------------------ 3. target key / label

def test_target_key_stable_and_brief_label_from_name(tmp_path):
    named = dict(TARGET_A, name="wide")
    renamed = dict(TARGET_B, name="narrow")
    records = [
        _record("d1", "s1", target=named),
        _record("d2", "s2", target=named),
        _record("d3", "s3", target=renamed),
        _record("d4", "s4", target=TARGET_A),  # no name
    ]
    _doc, out = _run(tmp_path, records)
    _header, rows = _csv_rows(out)
    by_design = {row["design_hash"]: row for row in rows}

    key1 = by_design["d1"]["target_key"]
    assert key1 == by_design["d2"]["target_key"]
    assert key1 != by_design["d3"]["target_key"]
    assert len(key1) == 12
    assert all(ch in "0123456789abcdef" for ch in key1)

    assert by_design["d1"]["brief_label"] == "wide"
    assert by_design["d2"]["brief_label"] == "wide"
    assert by_design["d3"]["brief_label"] == "narrow"
    assert by_design["d4"]["brief_label"] == ""


# ------------------------------------------------------------------ 4. dof buckets

def test_dof_class_boundaries(tmp_path):
    records = [
        _record("d1", "s1", n_dof=6000),
        _record("d2", "s2", n_dof=10001),
        _record("d3", "s3", n_dof=14000),
        _record("d4", "s4", n_dof=14001),
        _record("d5", "s5", n_dof=None),
    ]
    _doc, out = _run(tmp_path, records)
    _header, rows = _csv_rows(out)
    by_design = {row["design_hash"]: row for row in rows}

    assert by_design["d1"]["dof_class"] == "<=6k"
    assert by_design["d2"]["dof_class"] == "<=14k"
    assert by_design["d3"]["dof_class"] == "<=14k"
    assert by_design["d4"]["dof_class"] == ">14k"
    assert by_design["d5"]["dof_class"] == ""


# ------------------------------------------------------------------ 5. CSV + JSON round-trip

def test_csv_header_and_json_summary_round_trip(tmp_path):
    records = [
        _record("d1", "s1", objective=2.0, n_dof=4000),
        _record("d2", "s2", objective=1.0, n_dof=9000),
    ]
    dataset = _make_dataset(tmp_path, records)
    out = tmp_path / "views" / "keepers.csv"
    summary_path = tmp_path / "views" / "keepers.json"

    assert keepers.main([
        "--dataset", str(dataset),
        "--out", str(out),
        "--json", str(summary_path),
        "--quiet",
    ]) == 0

    header, rows = _csv_rows(out)
    assert header == list(keepers.FIELDS)
    assert len(rows) == 2
    assert set(rows[0]) == set(keepers.FIELDS)

    loaded = json.loads(summary_path.read_text(encoding="utf-8"))
    assert loaded["records_read"] == 2
    assert loaded["unique_rows"] == 2
    assert loaded["collapsed_extras"] == 0
    assert loaded["gate_mode"] == "unavailable"


# ------------------------------------------------------------------ 6. determinism

def test_repeated_runs_produce_identical_csv_bytes(tmp_path):
    records = [
        _record("d1", "s1", objective=4.0, n_dof=4000, params={"grid": {"k": 1}}),
        _record("d1", "s1", objective=1.0),  # duplicate, collapsed
        _record("d2", "s2", objective=2.0, params={"cad": {"k": 2}}),
        _record("d3", "s3", family="ICW", objective=3.0, ok=False),
    ]
    dataset = _make_dataset(tmp_path, records)
    out_a = tmp_path / "a" / "keepers.csv"
    out_b = tmp_path / "b" / "keepers.csv"

    keepers.run(dataset=dataset, out=out_a)
    keepers.run(dataset=dataset, out=out_b)

    assert out_a.read_bytes() == out_b.read_bytes()
