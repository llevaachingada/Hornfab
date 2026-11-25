"""Advisory-switch tests for ``tools/analysis/optimizer_switch.py``.

Synthetic run-dir fixtures only (``tmp_path``).  The tool must stay advisory: the new ``switch``
block is a structured suggestion and never an execution, queue change or production switch.
"""
from __future__ import annotations

import copy

import pytest

from test_tools_analysis_common import BASE_CONFIG, load_tool, make_row, write_run

switch = load_tool("optimizer_switch")

SWITCH_KEYS = {"recommendation", "reasons", "advisory_only", "executes_search",
               "changes_queue", "inputs", "metric_composite", "vocabulary"}
INPUT_KEYS = {"compatible_completed_solves", "compatible_designs", "active_dimension",
              "cohort_coverage", "cma_stagnation", "incumbent_concentration",
              "bounds_saturation", "model_diagnostic_quality",
              "historical_validation_status", "expected_overhead", "thresholds"}


def test_switch_is_present_and_advisory_only(tmp_path):
    rows = [make_row(i, 3.0 - 0.01 * i) for i in range(20)]
    report = switch.analyse_run(write_run(rows, tmp_path, "run"))
    block = report["switch"]
    assert SWITCH_KEYS.issubset(set(block))
    assert block["advisory_only"] is True
    assert block["executes_search"] is False
    assert block["changes_queue"] is False
    assert block["recommendation"] in switch.SWITCH_RECOMMENDATIONS
    assert INPUT_KEYS.issubset(set(block["inputs"]))
    assert isinstance(block["reasons"], list) and block["reasons"]
    # Existing report keys are unchanged.
    assert {"progress", "failure_signal", "walls", "recommendations",
            "cost_ledger"}.issubset(set(report))


def test_insufficient_data_is_reported_not_guessed(tmp_path):
    rows = [make_row(i, 1.0 - 0.01 * i) for i in range(5)]
    block = switch.analyse_run(write_run(rows, tmp_path, "tiny"))["switch"]
    assert block["recommendation"] == "INSUFFICIENT_DATA"
    assert block["inputs"]["compatible_completed_solves"] == 5
    assert any("minimum" in r for r in block["reasons"])


def test_metric_composite_requires_a_usable_model_and_stays_research_only(tmp_path):
    rows = [make_row(i, 1.0) for i in range(50)]
    run = write_run(rows, tmp_path, "stalled")
    without = switch.analyse_run(run)["switch"]
    assert without["recommendation"] != "TRY_METRIC_COMPOSITE"
    assert without["metric_composite"]["never_proven_superior"] is True

    diagnostics = {"status": "ok", "spearman": 0.8, "mae": 0.1}
    with_model = switch.analyse_run(run, model_diagnostics=diagnostics)["switch"]
    assert with_model["recommendation"] == "TRY_METRIC_COMPOSITE"
    mc = with_model["metric_composite"]
    assert mc["status"] == "validation_required"
    assert mc["research_only"] is True
    assert mc["never_proven_superior"] is True
    assert any("never been shown superior" in r for r in with_model["reasons"])

    # Even a supplied "validated" status is downgraded to validation_required by this advisory.
    validated = switch.analyse_run(run, model_diagnostics=diagnostics,
                                   historical_validation="validated")["switch"]
    assert validated["metric_composite"]["status"] == "validation_required"
    assert validated["metric_composite"]["never_proven_superior"] is True


def test_unusable_model_diagnostic_is_model_unavailable(tmp_path):
    rows = [make_row(i, 1.0 - 0.005 * i) for i in range(30)]
    run = write_run(rows, tmp_path, "bad-model")
    block = switch.analyse_run(run, model_diagnostics={
        "status": "unavailable", "detail": "fit failed"})["switch"]
    assert block["recommendation"] == "MODEL_UNAVAILABLE"
    assert block["metric_composite"]["model_diagnostics_usable"] is False


def test_bounds_saturation_takes_priority_and_never_auto_widens(tmp_path):
    config = copy.deepcopy(BASE_CONFIG)
    config["bounds"] = {"a_deg": {"lo": 10.0, "hi": 60.0}}
    rows = [make_row(i, 1.0 - 0.001 * i, params={"a_deg": 60.0}) for i in range(50)]
    run = write_run(rows, tmp_path, "pinned", config=config)
    block = switch.analyse_run(run)["switch"]
    assert block["recommendation"] == "REVIEW_BOUNDS"
    assert block["inputs"]["bounds_saturation"] == pytest.approx(1.0)
    text = " ".join(block["reasons"])
    assert "Do not widen automatically" in text


def test_failure_signal_keeps_the_current_run(tmp_path):
    rows = [make_row(i, 1.0) for i in range(15)]
    rows += [{"n": i, "ok": False, "failure_kind": "invalid_geometry"} for i in range(15, 45)]
    block = switch.analyse_run(write_run(rows, tmp_path, "failures"))["switch"]
    assert block["recommendation"] == "CONTINUE_CMA"
    assert any("failure" in r.lower() for r in block["reasons"])


def test_cli_reports_switch_and_accepts_optional_diagnostics(tmp_path):
    run = write_run([make_row(i, 1.0) for i in range(50)], tmp_path, "cli")
    diag = tmp_path / "diag.json"
    diag.write_text('{"status": "ok", "spearman": 0.75}', encoding="utf-8")
    proc = switch.main(["--run", str(run), "--out", str(tmp_path / "out"),
                        "--model-diagnostics", str(diag)])
    assert proc == 0
    import json
    payload = json.loads((tmp_path / "out" / "optimizer_switch.json").read_text(encoding="utf-8"))
    assert payload["runs"][0]["switch"]["recommendation"] == "TRY_METRIC_COMPOSITE"
    assert "Switch (advisory only)" in (tmp_path / "out" / "optimizer_switch.md").read_text(
        encoding="utf-8")
