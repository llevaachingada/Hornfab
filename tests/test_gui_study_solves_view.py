"""The study solves view is a bounded, honest projection of the results artifact.

Coverage/ripple are physical ONLY when the observation carries ``pareto_metric``/``pareto``/
``objectives``; ``normalized_terms`` are dimensionless objective contributions and must never be
presented as degrees or dB.  ``verify_run_id`` comes only from the solve ledger, and only while
the run folder still exists.
"""
from __future__ import annotations

import json

import pytest

from hornlab_search.gui.data_studies import study_solves

RUN_ID = "20261116T120000Z-studyverify-abcdef"


def _obs(design_hash=None, *, j: float | None = 1.0, physical=True, outcome="success", kind="screen",
         pareto=None, objectives=None, terms=None, extra_result=None):
    candidate = {"kind": kind, "params": {"L_mm": 120.0}, "descriptors": {"d": 1}}
    if design_hash is not None:
        candidate["design_hash"] = design_hash
    result = {"kind": kind, "observed_j": j, "physical_measurement": physical,
              "outcome": outcome, "params": {"L_mm": 120.0}}
    if pareto is not None:
        result["pareto_metric"] = pareto
    if objectives is not None:
        result["objectives"] = objectives
    if terms is not None:
        result["normalized_terms"] = terms
    if extra_result:
        result.update(extra_result)
    return {"candidate": candidate, "result": result}


def test_rows_sort_by_j_ascending_and_missing_j_last():
    payload = {"observations": [
        _obs("aaaa1111", j=3.0),
        _obs("bbbb2222", j=2.0),
        _obs("nodddddd", j=None),
        None,
        _obs(None, j=0.5),
        _obs("cccc3333", j=1.0),
        "not-an-observation",
    ]}
    out = study_solves(payload)
    assert [row["design_hash"] for row in out["rows"]] == [
        "cccc3333", "bbbb2222", "aaaa1111", "nodddddd"]
    assert out["n_total"] == 7                        # every journal row, including skipped ones
    assert out["truncated"] is False


def test_physical_and_refusal_counts_are_explicit():
    payload = {"observations": [
        _obs("aaaa1111", physical=True),
        _obs("bbbb2222", physical=False, outcome="cheap_refusal", j=None),
        _obs("cccc3333", physical=True),
    ]}
    out = study_solves(payload)
    assert out["n_measured"] == 2
    assert out["n_refused"] == 1
    refused = next(row for row in out["rows"] if row["design_hash"] == "bbbb2222")
    assert refused["physical"] is False
    assert refused["outcome"] == "cheap_refusal"
    assert refused["j"] is None


def test_coverage_and_ripple_use_physical_sources_only():
    payload = {"observations": [
        _obs("aaaa1111", pareto={"status": "complete", "coverage_deg": 1.5, "ripple_db": 0.4}),
        _obs("bbbb2222", objectives=[2.25, 0.75]),
        # dimensionless objective contributions: must NOT become degrees/dB
        _obs("cccc3333", terms={"cov": 0.91, "rip": 0.17}),
        # an incomplete pareto block is not a physical reading either
        _obs("dddd4444", pareto={"status": "capability_missing", "coverage_deg": 9.0,
                                 "ripple_db": 9.0}),
    ]}
    rows = {row["design_hash"]: row for row in study_solves(payload)["rows"]}
    assert rows["aaaa1111"]["coverage_deg"] == pytest.approx(1.5)
    assert rows["aaaa1111"]["ripple_db"] == pytest.approx(0.4)
    assert rows["bbbb2222"]["coverage_deg"] == pytest.approx(2.25)
    assert rows["bbbb2222"]["ripple_db"] == pytest.approx(0.75)
    assert rows["cccc3333"]["coverage_deg"] is None and rows["cccc3333"]["ripple_db"] is None
    assert rows["dddd4444"]["coverage_deg"] is None and rows["dddd4444"]["ripple_db"] is None


def test_limit_is_bounded_and_truncation_is_reported():
    payload = {"observations": [_obs(f"{i:08x}", j=float(i)) for i in range(1, 8)]}
    out = study_solves(payload, limit=3)
    assert len(out["rows"]) == 3
    assert [row["design_hash"] for row in out["rows"]] == [
        "00000001", "00000002", "00000003"]
    assert out["truncated"] is True
    with pytest.raises(ValueError):
        study_solves(payload, limit=51)


def test_missing_or_unreadable_artifact_invents_nothing():
    for value in (None, {}, {"observations": None}, {"observations": "many"}):
        out = study_solves(value)
        assert out["rows"] == []
        assert out["n_total"] == 0
        assert out["n_measured"] == 0
        assert out["n_refused"] == 0
        assert out["truncated"] is False
        assert out["status"] == "partial" and out["reason"]


def test_verify_run_comes_from_the_ledger_and_only_while_it_exists(tmp_path):
    payload = {"observations": [_obs("aaaa1111")]}
    ledger = {"version": 1, "solves": {"s1/aaaa1111": {"run_id": RUN_ID}},
              "jobs": {}, "keys": {}}
    runs = tmp_path / "runs"

    absent = study_solves(payload, study_id="s1", runs_root=runs, ledger=ledger)
    assert absent["rows"][0]["verify_run_id"] is None      # no run folder on disk

    (runs / RUN_ID).mkdir(parents=True)
    present = study_solves(payload, study_id="s1", runs_root=runs, ledger=ledger)
    assert present["rows"][0]["verify_run_id"] == RUN_ID

    # A stale/malformed id is never linked, even when the folder exists.
    bad = {"version": 1, "solves": {"s1/aaaa1111": {"run_id": "../escape"}},
           "jobs": {}, "keys": {}}
    assert study_solves(payload, study_id="s1", runs_root=runs,
                        ledger=bad)["rows"][0]["verify_run_id"] is None
    # A different study's mapping never leaks across studies.
    assert study_solves(payload, study_id="s2", runs_root=runs,
                        ledger=ledger)["rows"][0]["verify_run_id"] is None


def test_active_job_is_surfaced_for_the_ui_guard():
    payload = {"observations": [_obs("aaaa1111")]}
    ledger = {"version": 1, "solves": {},
              "jobs": {"j1": {"job_id": "j1", "study_id": "s1", "design_hash": "aaaa1111",
                              "status": "running"}},
              "keys": {}}
    out = study_solves(payload, study_id="s1", ledger=ledger)
    assert out["job"] == {"id": "j1", "design_hash": "aaaa1111", "status": "running"}


def test_params_and_descriptors_are_bounded_json():
    payload = {"observations": [_obs("aaaa1111", extra_result={"params": {"k": 1}})]}
    row = study_solves(payload)["rows"][0]
    assert row["params"] == {"k": 1}
    assert json.dumps(row)  # JSON-serialisable, no arrays/objects smuggled in
