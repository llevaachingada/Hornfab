"""Interruption/recovery tests for the synthetic metric-composite study (Pass 2, lane A).

These tests drive the real :func:`run_package` loop with the real
:class:`~hornlab_search.studies.production.ProductionJournal` over a temp ``StudyService``.  The
evaluator is the synthetic-only adapter; the acoustic function is a pure Python stand-in.
"""
from __future__ import annotations

import numpy as np

from hornlab_search.studies import metric_study
from hornlab_search.studies.metric_study import (
    FrozenLaneAdapter,
    MetricSyntheticEvaluator,
    metric_execution_gate,
)
from hornlab_search.studies.production import ProductionJournal
from hornlab_search.studies.runner import run_package

from test_studies_metric import _runtime, _stages, synthetic_result


def _evaluator(stages, *, evaluator=synthetic_result, limit=None):
    artifact, fitted, pool, bounds = _runtime(stages)
    return MetricSyntheticEvaluator(
        artifact, fitted, pool, synthetic_evaluator=evaluator, seed=0,
        bounds_hash=bounds, proposal_limit=limit)


def _run(stages, evaluator):
    return run_package(stages["package"], evaluator, FrozenLaneAdapter(),
                       ProductionJournal(stages["service"]))


# --------------------------------------------------------------------------- unknown attempt


def test_unknown_attempt_blocks_resume_and_evaluates_nothing(tmp_path):
    stages = _stages(tmp_path)
    package = stages["package"]
    journal = ProductionJournal(stages["service"])
    assert journal.claim(package)
    candidate = _evaluator(stages).next_candidate({"screen_calls": 0})
    assert journal.begin(package, candidate, True) is not None
    journal.release(package["package_id"], "interrupted")  # unresolved on purpose

    calls = []

    def evaluate(candidate, attempt_id):
        calls.append(candidate["solve_id"])
        return synthetic_result(candidate, attempt_id)

    result = _run(stages, _evaluator(stages, evaluator=evaluate, limit=None))
    assert result["status"] == "launch_conflict_or_stale"
    assert calls == []
    assert journal.state(package["package_id"])["unresolved"] is True


# --------------------------------------------------------------------------- pending proposal


def test_pending_proposal_is_evaluated_and_never_silently_reselected(tmp_path):
    stages = _stages(tmp_path)
    package = stages["package"]
    service = stages["service"]
    journal = ProductionJournal(service)
    assert journal.claim(package)
    first = _evaluator(stages)
    staged = first.next_candidate({"screen_calls": 0})
    assert staged is not None
    journal.stage_proposal(package, staged, 0, first.proposal_rng_state(), "stage:pending:1")
    journal.release(package["package_id"], "interrupted")

    calls = []
    next_calls = []

    def evaluate(candidate, attempt_id):
        calls.append(candidate["solve_id"])
        return synthetic_result(candidate, attempt_id)

    resumed = _evaluator(stages, evaluator=evaluate, limit=1)
    original_next = resumed.next_candidate

    def guarded_next(state):
        next_calls.append(state)
        return None  # deliberately refuses to re-select anything

    resumed.next_candidate = guarded_next
    result = _run(stages, resumed)
    assert result["status"] == "pool_exhausted"
    assert calls == [staged["solve_id"]]
    # next_candidate was only consulted after the staged proposal resolved.
    assert len(next_calls) == 1
    assert journal.state(package["package_id"])["screen_calls"] == 1
    del original_next


# --------------------------------------------------------------------------- no double evaluation


def test_rerun_after_limit_stop_evaluates_nothing_twice(tmp_path):
    stages = _stages(tmp_path)
    package = stages["package"]
    first_calls = []

    def first_eval(candidate, attempt_id):
        first_calls.append(candidate["solve_id"])
        return synthetic_result(candidate, attempt_id)

    result = _run(stages, _evaluator(stages, evaluator=first_eval, limit=3))
    assert result["status"] == "pool_exhausted"
    assert len(first_calls) == 3

    second_calls = []

    def second_eval(candidate, attempt_id):
        second_calls.append(candidate["solve_id"])
        return synthetic_result(candidate, attempt_id)

    result = _run(stages, _evaluator(stages, evaluator=second_eval, limit=3))
    assert result["status"] == "pool_exhausted"
    assert second_calls == []
    state = ProductionJournal(stages["service"]).state(package["package_id"])
    assert state["screen_calls"] == 3
    assert state["attempts"] == 3


# --------------------------------------------------------------------------- resume determinism


def test_resumed_study_makes_the_same_next_proposal_as_an_uninterrupted_run(tmp_path):
    stages = _stages(tmp_path)
    package = stages["package"]
    uninterrupted = _evaluator(stages, limit=2)
    result = _run(stages, uninterrupted)
    assert result["status"] == "pool_exhausted"

    # The uninterrupted evaluator already holds the final two observations and refit model.
    uninterrupted.proposal_limit = None
    next_uninterrupted = uninterrupted.next_candidate({"screen_calls": 2})
    assert next_uninterrupted is not None

    resumed = _evaluator(stages, limit=2)
    journal = ProductionJournal(stages["service"])
    assert resumed.restore_progress(journal.load_progress(package["package_id"]))
    resumed.proposal_limit = None
    next_resumed = resumed.next_candidate({"screen_calls": 2})
    assert next_resumed is not None
    assert next_resumed["solve_id"] == next_uninterrupted["solve_id"]

    # Same frozen state -> same model hash, not just the same first candidate.
    assert resumed.model_result.model_hash == uninterrupted.model_result.model_hash


# --------------------------------------------------------------------------- gate + existing policies


def test_gate_and_existing_policies_are_unchanged(tmp_path):
    stages = _stages(tmp_path)
    package = stages["package"]
    assert metric_execution_gate(
        package, synthetic_evaluator=synthetic_result)["real_solver_allowed"] is False
    assert metric_execution_gate(
        package, allow_real_solver=True,
        synthetic_evaluator=synthetic_result)["reason"] == \
        "metric_composite_real_execution_not_authorized"

    from hornlab_search.bo.policy import PROPOSAL_POLICIES, verification_mode
    from hornlab_search.studies.production import PRODUCTION_POLICIES
    assert PRODUCTION_POLICIES == ("scalar", "turbo", "pareto")
    assert PROPOSAL_POLICIES[:5] == ("scalar", "pareto", "cma_seed", "exploration", "turbo")
    assert verification_mode("turbo") == verification_mode("scalar") == "scalar"
    assert verification_mode("pareto") == "pareto"
    # The synthetic evaluator never executes a real backend call.
    assert np.isfinite(1.0)
