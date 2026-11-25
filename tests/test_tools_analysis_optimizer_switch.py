"""Offline evidence and safety checks for the advisory switch report."""
from __future__ import annotations

import json

import pytest

from test_tools_analysis_common import load_tool, make_row, run_cli, write_run

switch = load_tool("optimizer_switch")


def test_stall_and_wall_are_advisory_and_do_not_qualify_bo(tmp_path):
    rows = [make_row(i, 1.0, params={"a_deg": 60.0}) for i in range(50)]
    run = write_run(rows, tmp_path, "plateau")
    report = switch.analyse_run(run)
    assert report["progress"]["stalled"] is True
    assert any(w["key"] == "a_deg" and w["wall_hi"] for w in report["walls"])
    text = " ".join(report["recommendations"])
    assert "physical limits" in text and "Do not automatically widen" in text
    assert "strict cohort/admission" in text and "raw valid row count is not that gate" in text


def test_failure_priority_and_small_run_uncertainty(tmp_path):
    rows = [make_row(i, 1.0) for i in range(5)]
    rows += [{"n": i, "ok": False, "kind": "invalid_geometry"} for i in range(5, 30)]
    run = write_run(rows, tmp_path, "failures")
    report = switch.analyse_run(run)
    assert report["failure_signal"]["above_threshold"] is True
    assert report["failure_signal"]["dominant_kind"] == "geometry_refusal"
    assert "geometry refusal" in report["recommendations"][0]
    assert report["progress"]["stalled"] is None
    assert report["cost_ledger"]["index_rows"] == 30


def test_typed_outcome_counts_on_a_mixed_run(tmp_path):
    rows = []
    for i in range(8):
        rows.append(make_row(i, 1.0))
    for i in range(8, 10):
        rows.append(make_row(i, 1.0, cached=True))
    for i in range(10, 16):
        rows.append(make_row(i, 1000.0, ok=False, kind="invalid_geometry"))
    for i in range(16, 20):
        rows.append(make_row(i, 1000.0, ok=False, kind="invalid_envelope"))
    for i in range(20, 23):
        rows.append(make_row(i, 1000.0, ok=False, kind="mesh_too_large"))
    for i in range(23, 26):
        rows.append(make_row(i, 1000.0, ok=False, kind="solve_failed"))
    for i in range(26, 28):
        rows.append(make_row(i, 1000.0, ok=False, kind="exception"))
    for i in range(28, 30):
        rows.append(make_row(i, 1000.0, ok=False, kind="mystery"))
    run = write_run(rows, tmp_path, "mixed")
    report = switch.analyse_run(run)
    counts = report["outcome_counts"]
    assert counts["index_rows"] == 30
    assert counts["valid"] == 8
    assert counts["cached"] == 2
    assert counts["geometry_refusal"] == 6
    assert counts["envelope_refusal"] == 4
    assert counts["resource_refusal"] == 3
    assert counts["solver_failure"] == 3
    assert counts["pipeline_failure"] == 2
    assert counts["unknown"] == 2
    assert counts["counts_sum_to_index_rows"] is True
    assert counts["non_valid_non_cached"] == 20
    assert report["failure_signal"]["dominant_kind"] == "geometry_refusal"
    assert "geometry refusal" in report["recommendations"][0]



def test_cli_output_and_reject_output_in_input_run(tmp_path):
    run = write_run([make_row(i, 3.0 - i * 0.01) for i in range(8)], tmp_path, "run")
    proc = run_cli("optimizer_switch", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads((tmp_path / "out" / "optimizer_switch.json").read_text(encoding="utf-8"))
    assert payload["runs"][0]["progress"]["stalled"] is None
    assert "not compared" in payload["limitations"]
    assert (tmp_path / "out" / "optimizer_switch.md").exists()
    with pytest.raises(SystemExit):
        switch.main(["--run", str(run), "--out", str(run / "output")])


def test_missing_objective_does_not_claim_wall_analysis_succeeded(tmp_path):
    rows = [make_row(i, 1.0) for i in range(10)]
    rows[3]["objective"] = None
    run = write_run(rows, tmp_path, "missing")
    report = switch.analyse_run(run)
    assert report["progress"]["valid_rows"] == 9
    assert "unavailable" in report["wall_note"]


def test_all_valid_run_has_no_dominant_failure_kind(tmp_path):
    """A clean run must not be described as dominated by an 'unknown outcome'."""
    rows = [make_row(i, 5.0 - 0.01 * i) for i in range(30)]
    run = write_run(rows, tmp_path, "clean")
    report = switch.analyse_run(run)
    signal = report["failure_signal"]
    assert signal["dominant_kind"] is None
    assert "none" in signal["dominant_label"]
    assert signal["counts"]["unknown"] == 0
