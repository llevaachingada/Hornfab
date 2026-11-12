"""Offline tests for tools/night_report.py (D.4, 2026-11-12).

Hermetic: a synthetic night (fake summary.jsonl + run dirs + job logs) lives in tmp_path.
No real runs/, no GPU, no solver.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from conftest import REPO

TOOL = REPO / "tools" / "night_report.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("night_report_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


report = _load_tool()


# ------------------------------------------------------------------ fixtures


def _synthetic_night(runs_root: Path, name: str = "gpu_day_2026-11-12") -> tuple[Path, Path]:
    """summary.jsonl rows (incl. a retry pair and a failed job) + run dirs + job logs."""
    night_dir = runs_root / "nights" / name
    night_dir.mkdir(parents=True)

    gpu_run = runs_root / "20261112T110126Z-screen-c414b1"
    gpu_run.mkdir()
    (gpu_run / "search.ndjson").write_text(
        '\n'.join(json.dumps({"ok": True, "objective": 20.0 + i}) for i in range(30))
        + "\n" + json.dumps({"ok": False, "kind": "invalid_geometry"}) + "\n",
        encoding="utf-8")
    cpu_run = runs_root / "cpu_20261112T094509Z-verify-cafe12"
    cpu_run.mkdir()
    (cpu_run / "search.ndjson").write_text(
        json.dumps({"ok": True}) + "\n" + json.dumps({"ok": False, "kind": "envelope"}) + "\n",
        encoding="utf-8")

    rows = [
        # A gpu search job that was blocked once (GPU busy) and succeeded on attempt 2.
        {"id": "g1_core_law_resume", "kind": "search", "start": "2026-11-12T09:35:01Z",
         "end": "2026-11-12T09:36:01Z", "seconds": 60.0, "exit_code": 3, "run_dir":
         str(gpu_run), "evals_ndjson": 0, "best_J": None, "vram_baseline_mb": 512.0,
         "vram_after_mb": 900.0,
         "note": "exit code 3",
         "lane": "gpu", "backend": "beat_cuda", "status": "blocked", "attempts": 1},
        {"id": "g1_core_law_resume", "kind": "search", "start": "2026-11-12T09:38:01Z",
         "end": "2026-11-12T09:40:01Z", "seconds": 7200.0, "exit_code": 0,
         "run_dir": str(gpu_run), "evals_ndjson": 31, "best_J": 12.5,
         "vram_baseline_mb": 512.0, "vram_after_mb": 2048.0,
         "note": "ok; peak 3333 MiB",
         "lane": "gpu", "backend": "beat_cuda", "status": "ok", "attempts": 2},
        # A CPU verify command job, recorded successfully.
        {"id": "c1_xcheck_cpu", "kind": "command", "start": "2026-11-12T09:35:56Z",
         "end": "2026-11-12T09:45:09Z", "seconds": 553.0, "exit_code": 0,
         "run_dir": str(cpu_run), "evals_ndjson": 2, "best_J": 2.98,
         "vram_baseline_mb": None, "vram_after_mb": None, "note": "ok",
         "lane": "cpu", "backend": "beat_cpu", "status": "ok", "attempts": 1},
        # A gpu job that failed for real; its log has tracebacks.
        {"id": "g9_atlas", "kind": "search", "start": "2026-11-12T09:41:00Z",
         "end": "2026-11-12T09:41:20Z", "seconds": 20.0, "exit_code": 1, "run_dir": None,
         "evals_ndjson": 0, "best_J": None, "vram_baseline_mb": None,
         "vram_after_mb": None, "note": "exit code 1",
         "lane": "gpu", "backend": "beat_cuda", "status": "failed", "attempts": 1},
    ]
    (night_dir / "summary.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    (night_dir / "g9_atlas.log").write_text(
        "=== pre-hygiene g9_atlas\nTraceback (most recent call last):\n"
        "config load failed: brief not found\n", encoding="utf-8")
    (night_dir / "g1_core_law_resume.log").write_text(
        "=== pre-hygiene g1\n"  # no error line: the retry succeeded
        "  seed J=13.0  best J=12.5 (improved on the seed); stop: budget\n", encoding="utf-8")
    return night_dir, runs_root


def _render(tmp_path: Path, names=("gpu_day_2026-11-12",)):
    runs_root = tmp_path / "runs"
    for name in names:
        _synthetic_night(runs_root, name)
    return report.build_report(list(names), runs_root=runs_root, repo_root=tmp_path)


# ------------------------------------------------------------------ helpers


def test_latest_rows_keeps_the_last_row_per_job():
    rows = [{"id": "a", "n": 1}, {"id": "a", "n": 2}, {"id": "b", "n": 3}]
    latest = report.latest_rows(rows)
    summary = {r["id"]: r["n"] for r in latest}
    assert summary == {"a": 2, "b": 3}


def test_status_of_recorded_and_inferred():
    assert report.status_of({"status": "blocked"}) == ("blocked", "measured")
    assert report.status_of({"exit_code": 0}) == ("ok", "inferred")          # old runner row
    assert report.status_of({"exit_code": 124}) == ("timeout", "inferred")
    assert report.status_of({"exit_code": 1}) == ("failed", "inferred")
    assert report.status_of({"exit_code": 3, "note": "GPU busy (pid 5)"}) == ("blocked", "inferred")


def test_lane_of_recorded_and_inferred():
    assert report.lane_of({"lane": "cpu"}) == "cpu"
    assert report.lane_of({"backend": "beat_cpu"}, "") == "cpu"
    assert report.lane_of({}, "cpu_day_2026-11-12") == "cpu"
    assert report.lane_of({}, "gpu_2026-11-12") == "gpu"


def test_parse_peak_mb():
    assert report.parse_peak_mb("ok; peak 3333 MiB") == 3333.0
    assert report.parse_peak_mb("no peak here") is None


# ------------------------------------------------------------------ report content


def test_report_labels_measured_and_counts_the_two_lanes(tmp_path):
    text = _render(tmp_path)

    assert "[measured]" in text and "[inferred]" in text
    assert "## Night `gpu_day_2026-11-12`" in text
    # retry pair collapses to the LAST row: attempt 2 with 31 evals and best J 12.5
    line = [line for line in text.splitlines() if "`g1_core_law_resume`" in line][0]
    assert "| ok |" in line and "| 2 |" in line and "| 31 |" in line and "12.5" in line
    # per-lane sections
    assert "### lane gpu" in text and "### lane cpu" in text
    # gpu lane: 2 jobs (g1 attempt-2 + failed g9), exits ok 1 failed 1
    gpu_block = text.split("### lane gpu")[1].split("### lane cpu")[0]
    assert "jobs: 2" in gpu_block and "blocked 0" not in gpu_block
    assert "exits: failed 1, ok 1" in gpu_block
    # evals come from run dirs, not budgets; valid/refused counted from search.ndjson
    assert "evals (from run dirs, not budgets): 31" in gpu_block
    assert "valid 30 / refused 1 rows" in gpu_block
    assert "evals/hour" in gpu_block
    # VRAM peak parsed from the note
    assert "VRAM peak max 3333 MiB" in gpu_block
    # cpu lane: valid 1 / refused 1
    cpu_block = text.split("### lane cpu")[1]
    assert "valid 1 / refused 1 rows" in cpu_block
    assert "| 2.98 |" in text            # the table row carries the cpu job's best J


def test_failed_jobs_list_their_first_error_line(tmp_path):
    text = _render(tmp_path)
    failed = [line for line in text.splitlines() if "`g9_atlas` [failed]" in line][0]
    assert "GPU busy" not in failed
    assert "Traceback (most recent call last)" in failed


def test_retry_blocked_job_is_not_listed_as_failed(tmp_path):
    text = _render(tmp_path)
    # The failed-jobs block exists but only lists g9 (g1's last row is ok)
    block = text.split("Blocked/failed jobs")[1]
    assert "`g1_core_law_resume`" not in block


def test_night_report_cli_writes_the_out_file(tmp_path, capsys):
    runs_root = tmp_path / "runs"
    name = "gpu_day_2026-11-12"
    _synthetic_night(runs_root, name)
    out = tmp_path / "docs" / "evidence" / "NIGHT_2026-11-12.md"

    rc = report.main(["--night", name, "--out", str(out), "--runs-root", str(runs_root)])

    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Night report: " + name)
    assert "### lane cpu" in text
    capsys.readouterr() in (None,)  # printed to stdout as well (exercised, output not asserted)


def test_missing_night_dir_is_reported_not_fatal(tmp_path, capsys):
    text = report.build_report(["ghost_night"], runs_root=tmp_path / "runs",
                               repo_root=tmp_path)
    assert "ghost_night" in text and "not found" in text
