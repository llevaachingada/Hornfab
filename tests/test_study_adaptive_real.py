"""Adaptive data invariants with actual TrainingSet selection; no acoustic solve."""
from types import SimpleNamespace

import numpy as np

from hornlab_search.bo.data import TrainingObservation, build_training_set
from hornlab_search.studies.evaluator import PipelineStudyEvaluator


def historical():
    rows = [TrainingObservation(f"p{i}", np.array([i / 40, i / 50]), float(i),
                                geometry_hash=f"d{i}", solve_hash=f"s{i}")
            for i in range(20)]
    training = build_training_set(rows, d=2)
    training.meta["identities"] = {
        r.observation_id: {"design_hash": r.geometry_hash, "solve_hash": r.solve_hash}
        for r in rows}
    return training


def result():
    return {"kind": "screen", "outcome": "success", "eligible": True,
            "physical_id": "p-new", "observed_j": 0.2, "x": [0.7, 0.8],
            "design_hash": "d-new", "solve_hash": "s-new", "solve_id": "s-new",
            "geometry_id": "d-new"}


def adapter():
    return PipelineStudyEvaluator(
        None, {}, training_set=historical(), seed=7,
        fit_fn=lambda training, seed: SimpleNamespace(status="ok", reason=None))


def test_first_new_measurement_retains_historical_cohort_and_deduplicates():
    value = adapter()
    assert value.observe(result())
    assert value.training_set.status == "ok"
    assert value.training_set.n == 21
    assert set(historical().ids) <= set(value.training_set.ids)
    assert value.observe(result())
    assert value.training_set.n == 21
    assert len(value._measured) == 1


def test_resume_restores_same_training_arrays_including_historical_rows():
    uninterrupted = adapter()
    uninterrupted.observe(result())
    restarted = adapter()
    assert restarted.restore_progress({"observations": [{"result": result()}]})
    assert restarted.training_set.ids == uninterrupted.training_set.ids
    np.testing.assert_array_equal(restarted.training_set.X, uninterrupted.training_set.X)
    np.testing.assert_array_equal(restarted.training_set.J, uninterrupted.training_set.J)
    # Repeated reconciliation must replace, rather than double-add, the journal rows.
    assert restarted.restore_progress({"observations": [{"result": result()}]})
    assert restarted.training_set.n == 21


def test_verify_results_do_not_enter_screen_training_on_resume():
    verified = {**result(), "kind": "verify", "physical_id": "p-verify"}
    value = adapter()
    assert value.restore_progress({"observations": [{"result": verified}]})
    assert value.training_set.ids == historical().ids
    assert not value.observations


def test_same_physical_geometry_and_solve_does_not_inflate_evidence():
    value = adapter()
    duplicate = {**result(), "physical_id": "other-id", "design_hash": "d0",
                 "solve_hash": "s0", "x": [0.0, 0.0], "observed_j": 0.0}
    assert value.observe(duplicate)
    assert value.training_set.n == 20


def test_verification_staging_does_not_change_screen_exploration_cadence():
    from hornlab_search.bo.propose import ProposalHistory
    from dataclasses import replace
    value = adapter()
    value.history = replace(ProposalHistory(), proposal_index=18)
    value._proposal_sequence = 18
    value._screens_exhausted = True
    value._plan = [("verify", "d-new"), ("audit", "d-other")]
    value._measured = [result()]
    candidate = value.next_candidate({})
    assert candidate["kind"] == "verify"
    checkpoint = value.proposal_rng_state()
    assert checkpoint["proposal_history"]["proposal_index"] == 18
    assert checkpoint["rng_state"]["proposal_sequence"] == 19
    restarted = adapter()
    verified = {**result(), "kind": "verify", "eligible": False}
    assert restarted.restore_progress({
        "proposal_index": 19, "rng_state": checkpoint,
        "observations": [{"result": result()}, {"result": verified}]})
    assert restarted.history.proposal_index == 18
    assert restarted._proposal_sequence == 19
    assert "d-new" in restarted._verified_geometry_ids


def test_failed_verification_is_not_restored_as_verified():
    value = adapter()
    assert value.restore_progress({"observations": [{"result": {
        **result(), "kind": "verify", "outcome": "solver_failure", "observed_j": None}}]})
    assert not value._verified_geometry_ids
