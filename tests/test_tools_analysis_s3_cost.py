"""S3 focused tests: cost ledger, failed-work accounting, compatibility, censoring,
paired differences/intervals, fixed-budget/cost views and power planning.

All fixtures are synthetic run dirs under ``tmp_path``; nothing reads live data.
"""
from __future__ import annotations

import pytest

from test_tools_analysis_common import (BASE_CONFIG, load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

cm = load_tool("_common")
sv = load_tool("seed_variance")
ab = load_tool("ab_compare")


# ------------------------------------------------------------------ helpers

def _row(i: int, *, ok: bool = True, kind: str = "ok", cached: bool = False,
         total: float | None = 2.0, solve: float | None = None,
         objective: float | None = None,
         version: int = 4, family: str = "OSSE", mode: str = "screen") -> dict:
    obj = objective if objective is not None else (10.0 if ok else 1000.0)
    row = make_row(i, obj, ok=ok, kind=kind, cached=cached,
                   version=version, family=family, mode=mode)
    sec: dict = {}
    if total is not None:
        sec["total"] = total
    if solve is not None:
        sec["solve"] = solve
    row["seconds"] = sec
    return row


def _ledger_rows() -> list[dict]:
    return [
        _row(0, total=10.0, solve=8.0),                       # valid, BEM call
        _row(1, cached=True, total=0.5, solve=0.0),           # cache hit
        _row(2, ok=False, kind="invalid_geometry", total=0.4, solve=0.0),
        _row(3, ok=False, kind="mesh_too_large", total=0.6, solve=0.0),
        _row(4, ok=False, kind="solve_failed", total=5.0, solve=4.0),
        _row(5, ok=False, kind="exception", total=1.0, solve=0.0),
        _row(6, ok=False, kind="mystery_kind", total=0.2, solve=0.0),
    ]


# ------------------------------------------------------------------ cost ledger

def test_cost_ledger_separates_rows_attempts_cache_valid_bem_and_failures():
    stats = {"evaluations": 7, "non_cached": 6, "cache_hits": 1, "failures": 5,
             "total_gpu_seconds": 12.0, "total_mesh_seconds": 3.0}
    led = cm.cost_ledger(_ledger_rows(), stats=stats,
                         started_utc="2026-11-12T10:00:00Z",
                         finished_utc="2026-11-12T10:00:20Z")
    assert led["index_rows"] == 7
    assert led["cache_hits"] == 1 and led["attempts_new"] == 6
    assert led["valid_evaluations_new"] == 1 and led["valid_evaluations_cached"] == 1
    assert led["valid_evaluations_total"] == 2
    assert led["cheap_refusals"] == 2
    assert led["geometry_refusals"] == 1 and led["resource_refusals"] == 1
    assert led["solver_failures"] == 1 and led["pipeline_failures"] == 1
    assert led["unknown_failures"] == 1
    assert led["actual_bem_calls_observed"] == 2
    assert led["actual_bem_calls_inferred"] == 2
    assert led["actual_bem_seconds"] == pytest.approx(12.0)
    assert led["timing_observations"] == 2 and len(led["z_log_seconds"]) == 2
    el = led["elapsed_seconds"]
    assert el["attempts_all_incl_failed_refused"] == pytest.approx(17.2)
    assert el["valid_new"] == pytest.approx(10.0)
    assert el["failed_refused_attempts"] == pytest.approx(7.2)
    assert el["cached_replay"] == pytest.approx(0.5)
    assert el["recorded_total"] == pytest.approx(17.7)
    assert el["wall_span"] == pytest.approx(20.0)
    assert el["unaccounted_overhead"] == pytest.approx(2.3)
    assert led["cost_label"] == "wall_start_end"
    assert led["cost_model_gate"]["eligible"] is False
    assert led["cost_model_gate"]["status"] == "unavailable_insufficient_timing"
    assert all(led["stats_reconciliation"].values())


def test_cost_ledger_without_wall_timestamps_labels_accumulated_cost():
    led = cm.cost_ledger(_ledger_rows())
    assert led["cost_label"] == "accumulated_candidate_cost_no_wall_span"
    assert led["elapsed_seconds"]["wall_span"] is None
    assert led["elapsed_seconds"]["unaccounted_overhead"] is None


def test_cost_model_gate_needs_thirty_timing_observations():
    rows29 = [_row(i, total=2.0, solve=1.0) for i in range(29)]
    rows30 = [_row(i, total=2.0, solve=1.0) for i in range(30)]
    assert cm.cost_ledger(rows29)["cost_model_gate"]["eligible"] is False
    gate30 = cm.cost_ledger(rows30)["cost_model_gate"]
    assert gate30["eligible"] is True
    assert gate30["status"] == "eligible_not_fitted_in_m0"


def test_cost_model_gate_requires_count_and_compatibility():
    rows30 = [_row(i, total=2.0, solve=1.0) for i in range(30)]
    led = cm.cost_ledger(rows30)
    ok = cm.cost_model_eligibility(led, {"compatible_for_inference": True, "blocking": []})
    assert ok["eligible"] is True and ok["count_gate_passed"] is True
    assert ok["status"] == "eligible_not_fitted_in_m0"
    bad = cm.cost_model_eligibility(
        led, {"compatible_for_inference": False, "blocking": ["software_drift"]})
    assert bad["eligible"] is False and bad["status"] == "unavailable_incompatible_identity"
    short = cm.cost_model_eligibility(
        cm.cost_ledger(rows30[:29]),
        {"compatible_for_inference": True, "blocking": []})
    assert short["eligible"] is False and short["status"] == "unavailable_insufficient_timing"


def test_outcome_category_keeps_failure_types_distinct():
    assert cm.outcome_category(_row(0)) == "valid"
    assert cm.outcome_category(_row(1, ok=False, kind="invalid_envelope")) == "cheap_refusal"
    assert cm.outcome_category(_row(1, ok=False, kind="solve_failed")) == "solver_failure"
    assert cm.outcome_category(_row(1, ok=False, kind="exception")) == "pipeline_failure"
    assert cm.outcome_category(_row(1, ok=False, kind="weird")) == "unknown_failure"


# ------------------------------------------------------------------ curve/cost basis

def test_best_so_far_curve_failed_seconds_are_opt_in_and_honest(tmp_path):
    rows = [_row(0, total=2.0), _row(1, ok=False, kind="invalid_geometry", total=3.0),
            _row(2, total=2.0), _row(3, cached=True, total=1.0), _row(4, total=2.0)]
    run = {"rows": rows}
    legacy = cm.best_so_far_curve(run)
    honest = cm.best_so_far_curve(run, include_failed_seconds=True)
    assert [p["wall_s"] for p in legacy] == [2.0, 4.0, 6.0]
    assert [p["wall_s"] for p in honest] == [2.0, 7.0, 9.0]
    assert [p["wall_s_valid_only"] for p in honest] == [2.0, 4.0, 6.0]
    assert [p["attempt_n"] for p in honest] == [1, 3, 4]
    assert [p["best"] for p in honest] == [10.0, 10.0, 10.0]


# ------------------------------------------------------------------ compatibility/replicates

def test_compatibility_detects_software_drift_and_fidelity(tmp_path):
    ra = write_run([_row(0)], tmp_path, "a", seed=1,
                   extra_run_json={"lib_shas": {"hornlab_search": "aaa"}})
    rb = write_run([_row(0)], tmp_path, "b", seed=2,
                   extra_run_json={"lib_shas": {"hornlab_search": "bbb"}})
    comp = cm.compare_compatibility([cm.load_run(ra), cm.load_run(rb)])
    assert comp["compatible_for_inference"] is False
    assert "software_drift" in comp["blocking"]
    rc = write_run([_row(0, mode="verify")], tmp_path, "c", seed=3,
                   extra_run_json={"lib_shas": {"hornlab_search": "aaa"}})
    comp2 = cm.compare_compatibility([cm.load_run(ra), cm.load_run(rc)])
    assert "mode_mismatch" in comp2["blocking"]


def test_compatibility_task_config_block_is_optional(tmp_path):
    cfg_a = {**BASE_CONFIG}
    cfg_b = {**BASE_CONFIG, "bounds": {**BASE_CONFIG["bounds"],
                                       "a_deg": {"lo": 11.0, "hi": 60.0}}}
    ra = write_run([_row(0)], tmp_path, "a", seed=1, config=cfg_a)
    rb = write_run([_row(0)], tmp_path, "b", seed=2, config=cfg_b)
    loose = cm.compare_compatibility([cm.load_run(ra), cm.load_run(rb)])
    strict = cm.compare_compatibility([cm.load_run(ra), cm.load_run(rb)],
                                      block_task_config=True)
    assert "task_config_hash_mismatch" not in loose["blocking"]
    assert "task_config_hash_mismatch" in strict["blocking"]


def test_replicate_summary_flags_duplicate_seeds_and_keeps_resumes_in_one_rep(tmp_path):
    r1 = write_run([_row(0)], tmp_path, "r1", seed=5101,
                   extra_run_json={"resumes": ["2026-10-23T13:00:00Z"]})
    r2 = write_run([_row(0)], tmp_path, "r2", seed=5101,
                   extra_run_json={"restarts": [{"index": 0}]})
    rep = cm.replicate_summary([cm.load_run(r1), cm.load_run(r2)])
    assert rep["n_run_dirs"] == 2 and rep["n_independent_replicates"] == 1
    assert rep["duplicate_seed_run_dirs"] == {"5101": ["r1", "r2"]}
    assert rep["resumed_runs"] == ["r1"] and rep["restarted_runs"] == ["r2"]
    info = cm.replicate_info(cm.load_run(r1))
    assert info["n_resume_segments"] == 2 and info["is_resumed"] is True


# ------------------------------------------------------------------ censoring/target/ERT

def _curve(*points):
    return [{"n": i + 1, "best": b, "cost_s": c} for i, (b, c) in enumerate(points)]


def test_time_to_target_and_ert_are_censoring_aware():
    curves = [_curve((10.0, 1.0), (5.0, 2.0)),
              _curve((10.0, 1.0), (8.0, 2.0), (4.0, 3.0)),
              _curve((9.0, 1.0), (6.0, 2.0))]
    ecdf = cm.ecdf_time_to_target(curves, 5.0, "n")
    assert ecdf["n_runs"] == 3 and ecdf["n_reached"] == 2 and ecdf["n_censored"] == 1
    # the censored run is in the denominator but is never counted as reached
    assert ecdf["points"] == [[2, pytest.approx(1 / 3)], [3, pytest.approx(2 / 3)]]
    assert ecdf["ecdf_is_lower_bound"] is True
    ert = cm.expected_runtime(curves, 5.0, "n")
    assert ert["ert"] == pytest.approx((2 + 3 + 2) / 2)
    assert ert["n_success"] == 2 and ert["n_censored"] == 1
    assert ert["ert_is_lower_bound"] is True


def test_all_failure_and_zero_target_are_handled():
    assert cm.time_to_target([], 5.0, "n")["reached"] is False
    ert = cm.expected_runtime([[]], 5.0, "n")
    assert ert["status"] == "no_success" and ert["ert"] is None
    assert cm.time_to_target(_curve((0.0, 1.0)), 0.0, "n")["reached"] is True


def test_value_at_budget_reports_censoring_and_unequal_lengths():
    curve = _curve((10.0, 1.0), (8.0, 2.0))
    assert cm.value_at_budget(curve, 5, "n")["censored"] is True
    assert cm.value_at_budget(curve, 2, "n")["value"] == 8.0
    assert cm.value_at_budget(curve, 2, "n")["censored"] is False
    assert cm.value_at_budget([], 3, "n")["observed"] is False


# ------------------------------------------------------------------ paired stats/power

def test_paired_summary_known_effect_with_interval():
    diffs = [-2.0, -2.0, -2.0, -2.0, -2.0]      # A is 2 J better in every pair
    s = cm.paired_summary(diffs, practical_delta=1.0)
    assert s["n_pairs"] == 5 and s["mean"] == -2.0
    assert s["ci95_bootstrap_mean"] == [-2.0, -2.0]
    assert s["signs"] == {"a_better": 5, "b_better": 0, "ties": 0}
    assert s["decision"] == "a_better" and s["pilot"] is True
    # a practical target larger than the effect makes the same data inconclusive
    assert cm.paired_summary(diffs, practical_delta=3.0)["decision"] == "inconclusive"


def test_four_pairs_is_pilot_only_not_a_win():
    s = cm.paired_summary([-3.0, -2.0, -2.5, -2.2], practical_delta=0.5)
    assert s["n_pairs"] == 4 and s["decision"] == "pilot_only"
    assert s["direction"] == "a_better"


def test_power_planning_uses_pilot_sd_and_practical_delta():
    p = cm.power_planning([-1.5, -2.5, -2.0, -1.8, -2.2], practical_delta=0.5)
    assert p["status"] == "ok"
    assert p["n_pairs_required"] >= 2
    assert p["method"].startswith("normal approximation")
    assert cm.power_planning([-2.0, -2.0], practical_delta=1.0)["status"] == "unavailable"


# ------------------------------------------------------------------ tool integration

def test_seed_variance_reports_cost_and_duplicate_replicates(tmp_path):
    d1 = write_run([_row(0, total=2.0, solve=1.0)], tmp_path, "s1", seed=5101)
    d2 = write_run([_row(0, total=2.0, solve=1.0)], tmp_path, "s2", seed=5101)
    g = sv.analyse_group("g", [d1, d2], target_j=20.0, budget=1)
    assert g["cost_totals"]["index_rows"] == 2
    assert g["cost_totals"]["actual_bem_calls_observed"] == 2
    assert g["cost_model"]["count_gate_passed"] is False
    assert g["cost_model"]["status"] == "unavailable_insufficient_timing"
    assert g["replicates"]["n_independent_replicates"] == 1
    assert g["fixed_target"]["ecdf_evals"]["n_reached"] == 2


def test_ab_compare_fixed_cost_and_paired_views(tmp_path):
    def side(prefix, curves):
        return [write_run([_row(0, objective=obj, total=sec, solve=sec, mode="screen")],
                          tmp_path, f"{prefix}{i}", seed=100 + i)
                for i, (obj, sec) in enumerate(curves)]
    a = side("a", [(10.0, 2.0), (9.0, 2.0)])
    b = side("b", [(10.0, 2.0), (9.0, 2.0)])
    pairs = [(f"p{i}", da, db) for i, (da, db) in enumerate(zip(a, b))]
    p = ab.analyse(a, b, pairs=pairs, budget=1, cost_budget=2.0,
                   target_j=10.0, practical_delta=0.1)
    assert p["sides"]["a"]["cost"]["actual_bem_calls_observed"] == 2
    assert p["sides"]["a"]["outcomes"] == {"n_runs": 2, "finished": 2,
                                           "interrupted_or_unknown": 0,
                                           "with_valid_eval": 2, "all_failure": 0}
    assert p["fixed_cost"]["budget_s"] == 2.0
    assert p["fixed_target"]["target_j"] == 10.0
    assert p["fixed_target"]["a"]["ecdf_evals"]["n_reached"] == 2
    assert p["fixed_target"]["a"]["ert_evals"]["ert"] == 1.0
    assert p["paired"]["pairing_declared"] is True
    assert p["paired"]["summaries"]["summary"]["n_pairs"] == 2
    assert p["verdict"]["decision"] == "pilot_only"


def test_software_drift_blocks_paired_verdict_but_keeps_descriptive(tmp_path):
    libs_a = {"hornlab_search": "sha-a"}
    libs_b = {"hornlab_search": "sha-b"}
    a = [write_run([_row(0, objective=8.0)], tmp_path, f"a{i}", seed=10 + i,
                   extra_run_json={"lib_shas": libs_a}) for i in range(2)]
    b = [write_run([_row(0, objective=10.0)], tmp_path, f"b{i}", seed=20 + i,
                   extra_run_json={"lib_shas": libs_b}) for i in range(2)]
    pairs = [(f"p{i}", da, db) for i, (da, db) in enumerate(zip(a, b))]
    p = ab.analyse(a, b, pairs=pairs, practical_delta=0.5)
    assert p["compatibility"]["compatible_for_inference"] is False
    assert "software_drift" in p["compatibility"]["blocking"]
    assert p["paired"]["compatibility_blocked"] is True
    assert p["verdict"]["decision"] == "incompatible"
    assert p["verdict"]["verdict"] == "no-verdict"
    # descriptive medians still exist; only the prospective decision is blocked
    assert p["final"]["median_a"] == 8.0 and p["final"]["median_b"] == 10.0
    payload = sv.analyse_groups({"a": a, "b": b}, pairs=pairs, practical_delta=0.5)
    assert payload["prospective"]["summaries"]["summary"]["decision"] == "incompatible"
    assert payload["verdicts"][0]["verdict"] == "no-verdict"


def test_shared_cma_seed_is_reported_but_not_assumed_shared_candidates(tmp_path):
    a = write_run([_row(0, objective=8.0)], tmp_path, "a", seed=777)
    b = write_run([_row(0, objective=10.0)], tmp_path, "b", seed=777)
    p = ab.analyse([a], [b], pairs=[("p", a, b)], practical_delta=0.5)
    rec = p["paired"]["pairs"][0]
    assert rec["shared_cma_seed"] is True
    assert "not proof" in rec["shared_seed_warning"]


def test_seed_variance_cli_accepts_pairs_target_and_power(tmp_path):
    a = [write_run([_row(j, total=2.0) for j in range(4)], tmp_path, f"a{i}", seed=10 + i)
         for i in range(2)]
    b = [write_run([_row(j, total=2.0) for j in range(4)], tmp_path, f"b{i}", seed=20 + i)
         for i in range(2)]
    argv = ["--group", "a=" + ",".join(str(d) for d in a),
            "--group", "b=" + ",".join(str(d) for d in b),
            "--target-j", "20", "--budget", "2",
            "--practical-delta", "0.5"]
    for i, (da, db) in enumerate(zip(a, b)):
        argv += ["--pair", f"p{i}={da}|{db}"]
    proc = run_cli("seed_variance", argv, tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(tmp_path / "out", "seed_variance")
    assert doc["prospective"]["pairing_declared"] is True
    assert doc["prospective"]["power"]["status"] in ("ok", "unavailable")
    assert "fixed_target" in doc["descriptive_historical"]["groups"]["a"]
