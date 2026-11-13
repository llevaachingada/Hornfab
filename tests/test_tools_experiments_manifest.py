"""Focused offline tests for ``tools/experiments/manifest.py`` (S11).

Nothing here solves, launches a job or writes into a live run/cache/dataset tree.
The fixture reuses the real repo config/brief through the normal loaders and a
synthetic run dir for measured-cost/identity tests.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from tools.experiments import manifest as mf

REPO = Path(__file__).resolve().parents[1]
PILOT1 = REPO / "scratch" / "bo_m0" / "s11" / "pilot1_cold_vs_warm_native_ath_core_v4.yaml"
PILOT2 = REPO / "scratch" / "bo_m0" / "s11" / "pilot2_verify_allocation_crease_core_law_v4.yaml"
NATIVE_CONFIG = "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"
NATIVE_BRIEF = "examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml"


# --------------------------------------------------------------------- fixtures


def _rows() -> list[dict]:
    return [
        {"n": 0, "mode": "screen", "ok": True, "cached": False,
         "objective": 10.0, "seconds": {"total": 10.0, "solve": 8.0}},
        {"n": 1, "mode": "screen", "ok": True, "cached": False,
         "objective": 11.0, "seconds": {"total": 12.0, "solve": 9.0}},
        {"n": 2, "mode": "screen", "ok": False, "kind": "invalid_geometry",
         "cached": False, "seconds": {"total": 0.5}},
        {"n": 3, "mode": "screen", "ok": True, "cached": True,
         "objective": 10.0, "seconds": {"total": 0.1, "solve": 0.0}},
        {"n": 4, "mode": "screen", "ok": False, "kind": "solve_failed",
         "cached": False, "seconds": {"total": 4.0}},
        {"n": 5, "mode": "screen", "ok": False, "kind": "exception",
         "cached": False, "seconds": {"total": 1.0}},
        {"n": 6, "mode": "screen", "ok": False, "kind": "mystery_kind",
         "cached": False, "seconds": {"total": 0.2}},
    ]


def _make_run(tmp_path: Path, name: str = "source_run") -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "search.ndjson").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in _rows()),
        encoding="utf-8")
    (d / "run.json").write_text(json.dumps({
        "run_id": name, "config_name": "native__ath_core_v4", "family": "OSSE",
        "cma_seed": 5101, "status": "finished",
        "started_utc": "2026-01-01T00:00:00Z",
        "finished_utc": "2026-01-01T00:00:30Z",
        "config": {},
    }), encoding="utf-8")
    return d


def _fixture_overlay(tmp_path: Path) -> dict:
    """The real pilot-1 overlay with synthetic runtime sources and 2 seed pairs."""
    overlay = yaml.safe_load(PILOT1.read_text(encoding="utf-8"))
    source = _make_run(tmp_path)
    overlay["manifest_id"] = "test-pilot"
    overlay["outputs"]["reserved_root"] = "scratch/bo_m0/s11/out/test-pilot"
    overlay["task"]["cohort"] = None
    overlay["runtime_estimates"]["source_runs"] = [str(source)]
    seeds = [5101, 5102]
    overlay["replicates"]["seeds"] = list(seeds)
    overlay["budget"]["replication_aggregate"].update({
        "n_pairs": 2, "n_arms": 2,
        "screen_new_bem": 72, "verify_new_bem": 24,
        "total_new_bem": 96, "candidate_attempts": 480,
    })
    for arm in overlay["arms"]:
        arm["cma_seeds"] = list(seeds)
        arm.pop("warm_start", None)
        arm.get("config_overlay", {}).get("search", {}).pop("warm_start", None)
    return overlay


@pytest.fixture()
def built(tmp_path: Path) -> dict:
    manifest, findings = mf.build_manifest(_fixture_overlay(tmp_path))
    assert [f for f in findings if f.level == "error"] == []
    return manifest


def _codes(result: mf.ValidationResult) -> set[str]:
    return {e.code for e in result.errors}


def _mutated(built: dict, mutator) -> dict:
    manifest = copy.deepcopy(built)
    mutator(manifest)
    return manifest


# ------------------------------------------------------------------- build


def test_build_resolves_native_task_identity(built: dict) -> None:
    task = built["resolved_task"]
    assert task["config_name"] == "native__ath_core_v4"
    assert task["family"] == "OSSE"
    assert task["objective_version"] == 4
    assert task["resolved_target"]["band_lo_hz"] == 300.0
    assert task["resolved_target"]["band_hi_hz"] == 8000.0
    assert task["resolved_target"]["f0_hz"] == 1280.0
    assert task["objective"]["cov_narrow_ratio"] == 2.0
    assert task["objective"]["tolerances"]["cov"] == 2.0
    assert task["weights"]["load"] == 0.0
    assert task["config_sha256"] == mf.sha256_file(REPO / NATIVE_CONFIG)
    assert task["brief_sha256"] == mf.sha256_file(REPO / NATIVE_BRIEF)


def test_build_hashes_inputs_and_measures_runtime(built: dict) -> None:
    inputs = built["inputs_sha256"]
    for key in ("config_path_sha256", "brief_path_sha256", "config_sha256",
                "brief_sha256", "task_config_hash", "seeds_sha256",
                "budget_sha256", "arm_policies_sha256", "warm_sources_sha256"):
        assert isinstance(inputs[key], str) and len(inputs[key]) == 64
    measured = built["runtime_estimates"]["measured_sources"]
    assert len(measured) == 1
    assert measured[0]["attempts"] == 6  # cached row is not a new attempt
    assert measured[0]["new_bem_calls_inferred"] == 3  # solve_failed is an inferred call
    assert measured[0]["per_bem_seconds"] == pytest.approx(17.0 / 3.0)


def test_build_does_not_create_reserved_outputs(built: dict, tmp_path: Path) -> None:
    root = mf.resolve_path(built["outputs"]["reserved_root"])
    assert built["outputs"]["creates_nothing"] is True
    assert not root.exists()


def test_build_is_read_only_on_config_and_brief(built: dict, tmp_path: Path) -> None:
    before = {p: mf.sha256_file(REPO / p) for p in (NATIVE_CONFIG, NATIVE_BRIEF)}
    # A second build must see byte-identical inputs.
    mf.build_manifest(_fixture_overlay(tmp_path))
    after = {p: mf.sha256_file(REPO / p) for p in (NATIVE_CONFIG, NATIVE_BRIEF)}
    assert before == after


# ----------------------------------------------------------------- validation


def test_valid_manifest_has_no_errors_and_labels_hypotheses(built: dict) -> None:
    result = mf.validate_manifest(built)
    assert result.ok, result.as_dict()
    assert built["mode"] == "prepare_only"
    assert built["execution_authorized"] is False
    assert built["analysis_plan"]["hypotheses"][0]["label"] == "hypothesis"


def test_budget_arithmetic_must_match(built: dict) -> None:
    bad = _mutated(built, lambda m: m["budget"]["per_arm_per_replicate"].update(total_new_bem=23))
    assert "budget_arithmetic" in _codes(mf.validate_manifest(bad))


def test_attempt_cap_is_120(built: dict) -> None:
    bad = _mutated(built, lambda m: m["budget"]["per_arm_per_replicate"].update(candidate_attempts=121))
    assert "budget_attempt_cap" in _codes(mf.validate_manifest(bad))


def test_all_five_stop_rules_are_required(built: dict) -> None:
    bad = _mutated(built, lambda m: m["stop_rules"].pop("pool_exhaustion"))
    assert "stop_rule" in _codes(mf.validate_manifest(bad))


def test_deadline_is_required_and_may_be_a_placeholder(built: dict) -> None:
    assert mf.validate_manifest(built).ok
    bad = _mutated(built, lambda m: m["stop_rules"]["deadline"].update(deadline_required=False))
    assert "deadline_required" in _codes(mf.validate_manifest(bad))
    no_placeholder = _mutated(
        built, lambda m: m["stop_rules"]["deadline"].update(placeholder=False))
    assert "deadline_placeholder" in _codes(mf.validate_manifest(no_placeholder))


def test_three_consecutive_infrastructure_failures(built: dict) -> None:
    bad = _mutated(
        built,
        lambda m: m["stop_rules"]["infrastructure_failures"].update(consecutive_threshold=2))
    assert "stop_infra_threshold" in _codes(mf.validate_manifest(bad))


def test_cpu_lane_must_cite_cpu_lane_lock(built: dict) -> None:
    def break_lane(m):
        m["lane_ownership"]["cpu_if_beat_cpu"]["lock"] = "some other lock"
        m["lane_ownership"]["cpu_if_beat_cpu"]["rule"] = "run on CPU"
    bad = _mutated(built, break_lane)
    assert "lane_cpu_lock" in _codes(mf.validate_manifest(bad))


def test_outputs_must_stay_in_scratch(built: dict) -> None:
    bad = _mutated(built, lambda m: m["outputs"].update(reserved_root="runs/test-pilot"))
    assert "outputs_containment" in _codes(mf.validate_manifest(bad))


def test_unknown_cli_flag_is_rejected(built: dict) -> None:
    def invent(m):
        m["cli_commands"][0]["argv"] = list(m["cli_commands"][0]["argv"]) + ["--warm-seeds", "x"]
    bad = _mutated(built, invent)
    assert "command_unknown_flag" in _codes(mf.validate_manifest(bad))


def test_shell_metacharacters_are_rejected(built: dict) -> None:
    def inject(m):
        m["cli_commands"][0]["argv"][2] = "a;rm -rf x"
    bad = _mutated(built, inject)
    assert "command_shell_meta" in _codes(mf.validate_manifest(bad))


def test_numeric_flag_values_are_validated(built: dict) -> None:
    def break_budget(m):
        argv = list(m["cli_commands"][0]["argv"])
        idx = argv.index("--budget")
        argv[idx + 1] = "abc"
        m["cli_commands"][0]["argv"] = argv
    bad = _mutated(built, break_budget)
    assert "command_type" in _codes(mf.validate_manifest(bad))


def test_results_parser_requires_explicit_unknown(built: dict) -> None:
    def drop_unknown(m):
        m["analysis_plan"]["results_parser"]["outcome_classes"] = [
            "valid", "cheap_refusal", "solver_failure", "pipeline_failure"]
    bad = _mutated(built, drop_unknown)
    assert "results_parser_classes" in _codes(mf.validate_manifest(bad))


def test_results_parser_never_maps_failure_to_j(built: dict) -> None:
    def map_to_j(m):
        m["analysis_plan"]["results_parser"]["failure_to_objective_mapping"] = "j_1000"
    bad = _mutated(built, map_to_j)
    assert "results_parser_failure_mapping" in _codes(mf.validate_manifest(bad))


def test_no_default_objective_registration_changes(built: dict) -> None:
    bad = _mutated(built, lambda m: m["no_default_changes"].update(registration=True))
    assert "no_default_flag" in _codes(mf.validate_manifest(bad))
    speed = _mutated(built, lambda m: m["no_default_changes"].update(speedup_claimed=True))
    assert "no_speedup_claim" in _codes(mf.validate_manifest(speed))


def test_practical_threshold_must_be_labeled_not_a_speedup(built: dict) -> None:
    bad = _mutated(
        built,
        lambda m: m["analysis_plan"]["practical_improvement"].update(label="will_improve"))
    assert "analysis_threshold_label" in _codes(mf.validate_manifest(bad))


def test_expected_outcomes_must_be_hypotheses(built: dict) -> None:
    bad = _mutated(built, lambda m: m["analysis_plan"]["hypotheses"][0].update(label="claim"))
    assert "analysis_hypothesis_label" in _codes(mf.validate_manifest(bad))


def test_seed_schedule_mismatch_is_rejected(built: dict) -> None:
    def break_seeds(m):
        m["replicates"]["seeds"] = [5101]
    bad = _mutated(built, break_seeds)
    codes = _codes(mf.validate_manifest(bad))
    assert "arm_seeds_mismatch" in codes
    assert "input_hash_mismatch" in codes


def test_rollback_and_adoption_are_enumerated(built: dict) -> None:
    bad = _mutated(built, lambda m: m["rollback_and_adoption"].update(
        fail_or_no_gain_rollback=[], owner_adoption_decisions=[]))
    codes = _codes(mf.validate_manifest(bad))
    assert "rollback_items" in codes and "adoption_decisions" in codes


def test_comparability_requires_caveats_and_no_pooling(built: dict) -> None:
    def add_comparability(m):
        m["task"]["comparability"] = {
            "reference_task": "native__ath_core_v4",
            "pool_across_tasks": True,
            "caveats": [],
        }
    bad = _mutated(built, add_comparability)
    codes = _codes(mf.validate_manifest(bad))
    assert "comparability_pool" in codes and "comparability_caveat" in codes


# ------------------------------------------------------------ results parser


def test_outcomes_keep_failure_classes_distinct(tmp_path: Path) -> None:
    summary = mf.parse_run_outcomes(_make_run(tmp_path))
    outcomes = summary["outcomes"]
    assert outcomes["valid"] == 2
    assert outcomes["cached_replay"] == 1
    assert outcomes["cheap_refusal"] == 1
    assert outcomes["solver_failure"] == 1
    assert outcomes["pipeline_failure"] == 1
    assert outcomes["unknown_failure"] == 1
    assert summary["unknown_failure_kinds"] == {"mystery_kind": 1}
    assert summary["failure_to_objective_mapping"] == "none"
    assert summary["unknown_is_explicit"] is True


def test_cost_ledger_counts_attempts_bem_and_seconds(tmp_path: Path) -> None:
    ledger = mf.measure_run_cost(_make_run(tmp_path))
    assert ledger["attempts"] == 6
    assert ledger["valid_evaluations"] == 2
    assert ledger["cache_hits"] == 1
    assert ledger["new_bem_calls_observed"] == 2
    assert ledger["new_bem_calls_inferred"] == 3  # solve_failed counts as an attempt/call
    assert ledger["bem_seconds"] == pytest.approx(17.0)
    assert ledger["elapsed_seconds"]["attempts_all_incl_failed_refused"] == pytest.approx(27.7)
    assert ledger["per_attempt_seconds"] == pytest.approx(27.7 / 6)


# ------------------------------------------------------------------- CLI schema


def test_cli_schema_exposes_only_current_flags() -> None:
    schema = mf.cli_schema()
    assert "search" in schema and "verify" in schema and "run" in schema
    assert "--budget" in schema["search"]["options"]
    assert "--brief" in schema["search"]["options"]
    assert "--designs-file" in schema["verify"]["options"]
    assert "--warm-seeds" not in schema["search"]["options"]


def test_command_templates_validate_against_cli(built: dict) -> None:
    schema = mf.cli_schema()
    for command in built["cli_commands"]:
        findings = mf.validate_argv(command["argv"], schema, command["name"])
        assert findings == [], findings


# ---------------------------------------------------------------- repo artifacts


@pytest.mark.parametrize("overlay_path", [PILOT1, PILOT2])
def test_repo_pilot_overlays_validate(overlay_path: Path) -> None:
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    missing = [p for p in (overlay.get("runtime_estimates") or {}).get("source_runs", [])
               if not (mf.resolve_path(p) / "search.ndjson").is_file()]
    if missing:
        pytest.skip(f"local measured runtime sources unavailable: {missing}")
    manifest, findings = mf.build_manifest(overlay)
    assert [f for f in findings if f.level == "error"] == []
    result = mf.validate_manifest(manifest)
    assert result.ok, result.as_dict()


#: Committed built manifests (docs/evidence copy of the validated scratch originals).
COMMITTED_S11 = REPO / "docs" / "evidence" / "bo_study_2026-11-12" / "s11"


@pytest.mark.parametrize("name", [
    "pilot1_cold_vs_warm_native_ath_core_v4.json",
    "pilot2_verify_allocation_crease_core_law_v4.json",
])
def test_committed_pilot_manifests_validate_clean(name: str) -> None:
    """Both committed manifests validate with zero errors/warnings, no execution."""
    manifest = json.loads((COMMITTED_S11 / name).read_text(encoding="utf-8"))
    result = mf.validate_manifest(manifest)
    assert result.ok, result.as_dict()
    assert result.errors == [], result.as_dict()
    assert result.warnings == [], result.as_dict()
    assert manifest["execution_authorized"] is False
    assert manifest["stop_rules"]["deadline"]["deadline_required"] is True
    per_arm = manifest["budget"]["per_arm_per_replicate"]
    assert per_arm["screen_new_bem"] == 18
    assert per_arm["verify_new_bem"] == 6
    assert per_arm["total_new_bem"] == 24
    assert per_arm["candidate_attempts"] == 120


@pytest.mark.parametrize("name", [
    "pilot1_cold_vs_warm_native_ath_core_v4.json",
    "pilot2_verify_allocation_crease_core_law_v4.json",
])
def test_committed_pilot_commands_validate_against_live_cli(name: str) -> None:
    """Executor-facing argv templates match the real CLI parser (never executed)."""
    manifest = json.loads((COMMITTED_S11 / name).read_text(encoding="utf-8"))
    schema = mf.cli_schema()
    for command in manifest["cli_commands"]:
        findings = mf.validate_argv(command["argv"], schema, command["name"])
        assert findings == [], findings
