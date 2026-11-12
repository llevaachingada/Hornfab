"""Tests for tools/export_campaign_tables.py. Offline: grouping/labeling only, no solves."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import export_campaign_tables as ect  # noqa: E402


def _run_dir(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    run = tmp_path / "runs" / name
    run.mkdir(parents=True)
    (run / "search.ndjson").write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    return run


def _night(tmp_path: Path, cells: list[tuple[str, Path]]) -> Path:
    night = tmp_path / "nights" / "n1"
    night.mkdir(parents=True)
    lines = [json.dumps({"id": f"n__{name}", "run_dir": str(rd)}) for name, rd in cells]
    (night / "summary.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return night


def test_tables_are_labelled_and_grouped_by_objective_version_and_backend(tmp_path):
    # cell a: objective v7 rows; cell b: v1 rows with a much lower J (would win any naive global rank)
    rows_a = [
        {"n": 0, "design_hash": "a0", "family": "OSSE", "ok": True, "objective": 2.0,
         "objective_version": 7, "params": {"r0_mm": 17.0}, "terms": {"total": 2.0}},
        {"n": 1, "design_hash": "a1", "family": "OSSE", "ok": True, "objective": 1.0,
         "objective_version": 7, "params": {"r0_mm": 18.0}, "terms": {"total": 1.0}},
        {"n": 2, "design_hash": "a2", "family": "OSSE", "ok": False, "objective": 0.5,
         "objective_version": 7, "params": {"r0_mm": 19.0}, "error": "mesh_too_large"},
    ]
    rows_b = [
        {"n": 0, "design_hash": "b0", "family": "FREEFORM", "ok": True, "objective": 0.1,
         "objective_version": 1, "params": {"grid": {"knobs": {"a_deg": 30.0}}},
         "terms": {"total": 0.1}},
    ]
    run_a = _run_dir(tmp_path, "20261031T201057Z-screen-d3158e", rows_a)
    run_b = _run_dir(tmp_path, "20261031T202159Z-screen-ba7648", rows_b)
    night = _night(tmp_path, [("osse_v7", run_a), ("free_v1", run_b)])
    out = tmp_path / "tables"

    assert ect.main(["--night", str(night), "--out", str(out)]) == 0

    with (out / "cells_summary.csv").open(encoding="utf-8", newline="") as f:
        summary = list(csv.DictReader(f))
    # groups are ordered by objective version ascending, never by J across the group boundary:
    # v1's much lower J never displaces the v7 group or mixes with it.
    assert [row["cell"] for row in summary] == ["free_v1", "osse_v7"]
    assert summary[1]["group"] == "v7/unknown" and summary[0]["group"] == "v1/unknown"
    assert summary[1]["objective_version"] == "7" and summary[1]["backend"] == "unknown"
    assert summary[1]["best_J"] == "1.0"
    assert summary[1]["refused"] == "1"          # the failed v7 row never ranks

    with (out / "evals.csv").open(encoding="utf-8", newline="") as f:
        evals = list(csv.DictReader(f))
    assert [row["cell"] for row in evals] == ["free_v1", "osse_v7", "osse_v7", "osse_v7"]
    assert "group" in evals[0] and "backend" in evals[0]
    assert evals[0]["group"] == "v1/unknown" and evals[-1]["group"] == "v7/unknown"
    assert evals[0]["objective_version"] == "1" and evals[-1]["objective_version"] == "7"

    best = json.loads((out / "best_designs.json").read_text(encoding="utf-8"))
    assert set(best) == {"v7/unknown", "v1/unknown"}
    assert best["v7/unknown"]["osse_v7"]["design_hash"] == "a1"
    assert best["v1/unknown"]["free_v1"]["design_hash"] == "b0"

    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "Never rank across groups" in readme


def test_backend_comes_from_the_solve_block_when_present(tmp_path):
    assert ect.backend_of({"solve": {"backend": "beat_cuda"}}) == "beat_cuda"
    assert ect.backend_of({"backend": "bempp_cpu"}) == "bempp_cpu"
    assert ect.backend_of({}) == "unknown"


def test_group_of_defaults_objective_version_to_1():
    assert ect.group_of({"solve": {"backend": "beat_cuda"}}) == "v1/beat_cuda"
    assert ect.group_of({"objective_version": 7, "backend": "beat_cuda"}) == "v7/beat_cuda"
