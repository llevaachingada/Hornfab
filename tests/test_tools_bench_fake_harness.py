"""Offline tests for tools/bench/fake_harness.py (S9 preparation).

The harness is a deterministic fixture generator plus the S3 cost-ledger replay.
These tests pin: same seed -> byte-identical timing JSON; a dry run writes no
fixture and starts no solve; the ledger and stage sums reconcile; and failed or
refused attempts are accounted for (including zero-second inferred BEM calls).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.bench.fake_harness import (
    FIXED_EPOCH,
    STAGE_TIMING_FILE,
    replay,
    synthesize,
)
from tools.bench.timing_ledger import summarize

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "bench" / "fake_harness.py"


def test_same_seed_same_timing_json(tmp_path):
    a = replay(seed=11, candidates=36, cache_hit_rate=0.25, prefetch_depth=2, meh=True)
    b = replay(seed=11, candidates=36, cache_hit_rate=0.25, prefetch_depth=2, meh=True)
    assert a == b
    assert a["ledger"] == b["ledger"]
    assert a["stage_timing"] == b["stage_timing"]

    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    replay(seed=11, candidates=36, cache_hit_rate=0.25, prefetch_depth=2, meh=True, out=p1)
    replay(seed=11, candidates=36, cache_hit_rate=0.25, prefetch_depth=2, meh=True, out=p2)
    assert p1.read_bytes() == p2.read_bytes()

    other = replay(seed=12, candidates=36, cache_hit_rate=0.25, prefetch_depth=2, meh=True)
    assert other["stage_timing"]["stage_seconds"] != a["stage_timing"]["stage_seconds"]


def test_dry_run_zero_solves_and_zero_fixtures(tmp_path):
    fixtures = tmp_path / "fixtures"
    out = tmp_path / "timing.json"
    result = replay(seed=2, candidates=12, dry_run=True,
                    fixtures_dir=fixtures, out=out)

    assert result["dry_run"] is True
    assert result["guards"] == {
        "solve_processes_started": 0,
        "acoustic_records_written": 0,
        "solver_or_mesher_imported": False,
        "fixture_files_written": 0,
    }
    assert not fixtures.exists()
    assert out.exists()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["guards"]["solve_processes_started"] == 0
    assert written["guards"]["acoustic_records_written"] == 0
    assert not list(tmp_path.rglob("*.npz"))
    assert not list(tmp_path.rglob("*.msh"))


def test_ledger_and_stage_reconciliation_sums(tmp_path):
    fixtures = tmp_path / "fixtures"
    result = replay(seed=7, candidates=30, cache_hit_rate=0.20, prefetch_depth=2,
                    fixtures_dir=fixtures)
    ledger = result["ledger"]

    assert result["guards"]["fixture_files_written"] == 3
    assert (fixtures / STAGE_TIMING_FILE).exists()
    assert (fixtures / "search_fixture.ndjson").exists()

    # S3 ledger identities.
    assert ledger["index_rows"] == ledger["cache_hits"] + ledger["attempts_new"]
    assert (ledger["valid_evaluations_total"]
            == ledger["valid_evaluations_new"] + ledger["valid_evaluations_cached"])
    elapsed = ledger["elapsed_seconds"]
    assert elapsed["recorded_total"] == pytest.approx(
        elapsed["attempts_all_incl_failed_refused"] + elapsed["cached_replay"])
    assert elapsed["wall_span"] is None
    assert ledger["cost_label"] == "accumulated_candidate_cost_no_wall_span"
    assert ledger["actual_bem_calls_inferred"] >= ledger["actual_bem_calls_observed"]
    assert ledger["actual_bem_calls_observed"] > 0
    assert all(ledger["stats_reconciliation"].values())

    # Stage reconciliation: candidate totals equal top-level stages, elapsed adds
    # only the run overhead and prefetch wait, and every check passes.
    stages = result["stage_timing"]
    assert all(stages["checks"].values())
    assert stages["candidate_total_sum_s"] == pytest.approx(
        stages["top_level_stage_sum_s"])
    assert stages["elapsed_s"] == pytest.approx(
        stages["candidate_total_sum_s"] + stages["run_overhead_s"]
        + stages["prefetch_wait_s"])
    assert stages["candidate_total_rows"] == ledger["attempts_new"]
    assert stages["prefetch_seconds"] > 0
    assert stages["prefetch_overlap_s"] == pytest.approx(
        min(stages["prefetch_seconds"], stages["candidate_total_sum_s"]))
    assert stages["prefetch_adds_to_elapsed_s"] == 0
    assert stages["naive_all_stage_sum_s"] > stages["elapsed_s"]
    assert stages["unaccounted_s"] == pytest.approx(0.0)

    # The generated manifest is consumable by the existing offline timing ledger.
    manifest = json.loads((fixtures / "timing_manifest.json").read_text(encoding="utf-8"))
    summary = summarize(manifest, fixtures)
    assert summary["attempt_count"] == ledger["index_rows"]
    assert summary["stage_seconds"]["candidate_total"] == pytest.approx(
        stages["candidate_total_sum_s"])
    assert summary["verified_useful_per_hour"] is None


def test_failure_path_accounting():
    result = replay(
        seed=5, candidates=40, cache_hit_rate=0.0, refusal_rate=0.3,
        solver_failure_rate=0.4, pipeline_failure_rate=0.2,
    )
    ledger = result["ledger"]
    assert ledger["cache_hits"] == 0
    assert ledger["cheap_refusals"] > 0
    assert ledger["solver_failures"] > 0
    assert ledger["pipeline_failures"] > 0
    assert ledger["valid_evaluations_new"] > 0
    assert sum(ledger["failure_kinds"].values()) == (
        ledger["cheap_refusals"] + ledger["solver_failures"]
        + ledger["pipeline_failures"] + ledger["unknown_failures"])
    assert {"solve_failed", "exception"}.issubset(set(ledger["failure_kinds"]))
    assert ledger["elapsed_seconds"]["failed_refused_attempts"] > 0

    # A recorded solve failure with no positive solve seconds is still an inferred
    # BEM attempt; the harness deliberately alternates those with observed calls.
    inferred_without_observed = (
        ledger["actual_bem_calls_inferred"] - ledger["actual_bem_calls_observed"])
    assert inferred_without_observed > 0
    assert inferred_without_observed <= ledger["solver_failures"]

    # Verification is operator-supplied, never inferred from a synthetic row.
    assert all(attempt["verified_useful"] is None for attempt in result["attempts"])


def test_stage_rows_mirror_profiling_schema():
    fixture = synthesize(seed=1, candidates=9, meh=True)
    required = {"stage", "seconds", "design_hash", "key", "thread", "unix_time"}
    assert fixture["stage_rows"]
    assert all(required <= set(row) for row in fixture["stage_rows"])
    solver_rows = [r for r in fixture["stage_rows"] if r["stage"] == "solver_path"]
    assert solver_rows
    assert all(isinstance(r.get("timings"), dict) for r in solver_rows)
    assert any(r["stage"] == "meh_inner_optimize" for r in fixture["stage_rows"])
    assert any(r["thread"] == "MainThread" for r in fixture["stage_rows"])
    assert min(r["unix_time"] for r in fixture["stage_rows"]) >= FIXED_EPOCH


def test_cli_dry_run_writes_timing_json_only(tmp_path):
    fixtures = tmp_path / "fixtures"
    out = tmp_path / "timing.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--seed", "3",
         "--candidates", "10", "--fixtures-dir", str(fixtures), "--out", str(out)],
        capture_output=True, text=True, check=True,
        cwd=str(REPO),
    )
    stdout = json.loads(completed.stdout)
    assert stdout["dry_run"] is True
    assert stdout["guards"]["solve_processes_started"] == 0
    assert stdout["guards"]["acoustic_records_written"] == 0
    assert not fixtures.exists()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["synthetic"] is True
    assert written["stage_timing"]["checks"]["naive_stage_sum_overcounts_elapsed"] is True
