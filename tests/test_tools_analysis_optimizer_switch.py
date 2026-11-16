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
    rows += [{"n": i, "ok": False, "failure_kind": "invalid_geometry"} for i in range(5, 30)]
    run = write_run(rows, tmp_path, "failures")
    report = switch.analyse_run(run)
    assert report["failure_signal"]["above_threshold"] is True
    assert report["recommendations"][0].startswith("Investigate geometry")
    assert report["progress"]["stalled"] is None
    assert report["cost_ledger"]["index_rows"] == 30


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
