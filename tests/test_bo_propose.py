"""Focused tests for the scalar-pool v1 proposal policy (hornlab_search/bo/propose.py).

Engine-using proposal tests are skipped when BoTorch is absent; cadence/pending/exhaustion gates
and the model-unavailable fallback are pure numpy and always run.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import sys

import numpy as np
import pytest

import hornlab_search.bo.propose as propose_mod
from hornlab_search.bo import (
    AcquisitionResult,
    CandidatePool,
    ModelFitResult,
    PoolCandidate,
    PredictionResult,
    ProposalHistory,
    ProposalPolicy,
    build_training_set,
    fit_model,
    make_pure_observations,
    propose_one,
)
from hornlab_search.bo.data import POOL_STATUS_NOTE

# These unit tests exercise selection independently of the publication validation gate.
propose_one = propose_mod._propose_one

HAS_BOTORCH = importlib.util.find_spec("botorch") is not None
requires_botorch = pytest.mark.skipif(
    not HAS_BOTORCH, reason="optional BoTorch engine (isolated bayes venv) absent")


def _make_pool(vectors, *, prefix="pool", status="ok", seeds=(0,)):
    candidates = []
    for i, vector in enumerate(vectors):
        arr = np.asarray(vector, dtype=np.float64).reshape(-1)
        candidates.append(PoolCandidate(
            candidate_id=f"{prefix}-{i:02d}", pool_index=i, seed=int(seeds[0]),
            active_vector=arr.copy(), full_vector=arr.copy(),
            design_hash=f"design-{prefix}-{i:02d}", geometry_hash=f"geom-{prefix}-{i:02d}",
            intended_solve_hash="solve-0", params={}, descriptors={}, checks={}))
    return CandidatePool(
        status=status, requested=len(candidates), seed=(None if not seeds else int(seeds[0])),
        seeds_tried=tuple(int(s) for s in seeds), candidates=tuple(candidates),
        counts={"unique": len(candidates)}, seed_reports=(), intended_solve_hash="solve-0",
        note=POOL_STATUS_NOTE)


@pytest.fixture(scope="module")
def training():
    return build_training_set(make_pure_observations(2, 16, seed=1), d=2)


@pytest.fixture(scope="module")
def fitted(training):
    return fit_model(training, seed=0)


@pytest.fixture(scope="module")
def pool():
    return _make_pool(np.random.default_rng(11).random((8, 2)))


# ------------------------------------------------------------------ pure gates


def test_pool_exhausted_preserves_seeds_and_index():
    exhausted = _make_pool([], status="pool_exhausted", seeds=(10, 11, 12))
    result = propose_one(None, exhausted, history=ProposalHistory(proposal_index=5))
    assert result.status == "unavailable"
    assert result.reason == "pool_exhausted"
    assert result.candidate is None and result.predicted is None
    assert result.next_proposal_index == 5  # no dispatch -> cadence does not advance
    assert result.seeds_tried == (10, 11, 12)
    assert len(result.seeds_tried) <= 3  # at most two extra recorded seeds


def test_all_candidates_excluded_returns_pool_exhausted(training, fitted):
    pool = _make_pool([[0.9, 0.9], [0.9, 0.1]])
    history = ProposalHistory(proposal_index=0,
                              excluded_geometry_hashes=("geom-pool-00", "geom-pool-01"))
    result = propose_one(fitted, pool, history=history)
    assert result.status == "unavailable"
    assert result.reason == "pool_exhausted"
    assert result.candidate is None and result.predicted is None
    assert result.counts["excluded_known"] == 2
    assert result.next_proposal_index == 0


def test_model_unavailable_returns_labelled_fallback_without_predictions(training):
    flat = dataclasses.replace(training, J=np.full_like(training.J, 1.0),
                               Y=np.full_like(training.Y, -1.0))
    flat_fit = fit_model(flat)
    assert flat_fit.reason == "flat_training_response"
    pool = _make_pool([[0.9, 0.9], [0.9, 0.1]])
    result = propose_one(flat_fit, pool, history=ProposalHistory(proposal_index=0))
    assert result.status == "unavailable"
    assert result.reason == "flat_training_response"
    assert result.selection_reason == "exploration_fallback"
    assert result.fallback is True
    assert result.candidate is not None  # a legal non-BO suggestion exists
    assert result.predicted is None  # never zero predictions


def test_ok_status_with_missing_model_object_is_model_unavailable(training, fitted):
    broken = ModelFitResult(status="ok", reason="ok", d=fitted.d, n=fitted.n,
                            model=None, train_X=fitted.train_X)
    pool = _make_pool([[0.9, 0.9], [0.9, 0.1]])
    result = propose_one(broken, pool, history=ProposalHistory(proposal_index=0))
    assert result.status == "unavailable"
    assert result.reason == "model_unavailable"
    assert result.predicted is None and result.fallback is True


def test_pending_contains_only_dispatched_unresolved_identities(fitted):
    pool = _make_pool([[0.9, 0.9], [0.9, 0.1]])
    identity = ("geom-pool-00", "solve-0")
    pending = ProposalHistory(proposal_index=0, pending_identities=(identity,),
                              pending_vectors=(np.array([0.9, 0.9]),))
    result = propose_one(fitted, pool, history=pending)
    assert result.candidate_id == "pool-01"
    assert result.counts["excluded_pending"] == 1

    resolved = ProposalHistory(proposal_index=0)
    result2 = propose_one(fitted, pool, history=resolved)
    assert result2.counts["excluded_pending"] == 0
    assert result2.counts["legal"] == 2
    # A resolved (no longer pending) identity is not retroactively excluded by this field.
    assert result2.candidate_id in {"pool-00", "pool-01"}


def test_near_duplicate_tolerance_is_one_e_minus_six(training, fitted):
    train_vec = np.array(training.X[0], copy=True)
    vectors = [
        train_vec,                       # near-duplicate of a training point
        np.array([0.9, 0.9]),            # accepted
        np.array([0.9, 0.9 + 5e-7]),     # pairwise near-duplicate of the previous
        np.array([0.1, 0.9]),
        np.array([0.9, 0.1]),
    ]
    pool = _make_pool(vectors)
    result = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    assert result.counts["excluded_near_duplicate"] == 1
    assert result.counts["excluded_near_pool_duplicate"] == 1
    assert result.counts["legal"] == 3
    assert result.candidate_id not in {"pool-00", "pool-02"}


def test_proposal_cadence_is_locked_and_survives_resume(fitted, pool):
    seen = []
    history = ProposalHistory(proposal_index=0)
    for _ in range(3):
        result = propose_one(fitted, pool, history=history)
        seen.append(result.selection_reason)
        history = ProposalHistory(proposal_index=result.next_proposal_index)
    # 0, 1, 2 -> acquisition; the 4th new index (3) -> exploration.
    assert seen == ["acquisition", "acquisition", "acquisition"]
    fourth = propose_one(fitted, pool, history=history)
    assert fourth.proposal_index == 3
    assert fourth.selection_reason == "exploration"
    assert fourth.next_proposal_index == 4
    # Simulated resume: construct history from the persisted next index; cadence is not reset.
    resumed = ProposalHistory(proposal_index=fourth.next_proposal_index)
    fifth = propose_one(fitted, pool, history=resumed)
    assert fifth.proposal_index == 4
    assert fifth.selection_reason == "acquisition"
    seventh = propose_one(fitted, pool, history=ProposalHistory(proposal_index=7))
    assert seventh.selection_reason == "exploration"


def test_exploration_uses_the_farthest_pool_point(fitted):
    pool = _make_pool([[0.9, 0.9], [0.2, 0.2], [0.5, 0.5]])
    # Index 3 is the exploration arm.
    result = propose_one(fitted, pool, history=ProposalHistory(proposal_index=3))
    assert result.selection_reason == "exploration"
    assert result.exploration["method"] == "maximin"
    assert result.exploration["distance_l2"] > 0.0
    # The chosen point is one of the legal candidates, with a finite prediction.
    assert result.candidate_id in {"pool-00", "pool-01", "pool-02"}
    assert result.predicted is not None
    assert np.isfinite(result.predicted["j_mean"])


def test_exploration_every_four_policy_predicate():
    policy = ProposalPolicy()
    assert [i for i in range(8) if policy.is_exploration(i)] == [3, 7]
    assert policy.exploration_every == 4


def test_optional_engine_absent_propagates_capability_error(fitted, pool, monkeypatch):
    for key in [k for k in sys.modules if k == "botorch" or k.startswith("botorch.")]:
        monkeypatch.delitem(sys.modules, key, raising=False)
    monkeypatch.setitem(sys.modules, "botorch", None)
    result = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    assert result.status == "unavailable"
    assert result.reason == "capability_missing"
    assert result.predicted is None


# ------------------------------------------------------------------ engine proposals


def test_acquisition_failure_returns_model_unavailable_without_predictions(
        fitted, pool, monkeypatch):
    torch = pytest.importorskip("torch")

    class FakeAcq:
        def __call__(self, tensor):
            return torch.full((tensor.shape[0],), float("nan"), dtype=torch.float64)

    fake = AcquisitionResult(status="ok", reason="ok", acq=FakeAcq(), acq_seed=0)
    monkeypatch.setattr(propose_mod, "build_acquisition", lambda *a, **k: fake)
    result = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    assert result.status == "unavailable"
    assert result.reason == "model_unavailable"
    assert result.fallback is True
    assert result.predicted is None
    assert "nonfinite_acquisition" in (result.detail or "")


def test_posterior_failure_returns_model_unavailable_without_predictions(
        fitted, pool, monkeypatch):
    forced = PredictionResult(status="unavailable", reason="model_unavailable",
                              detail="forced posterior failure")
    monkeypatch.setattr(propose_mod, "predict_j", lambda *a, **k: forced)
    result = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    assert result.status == "unavailable"
    assert result.reason == "model_unavailable"
    assert result.predicted is None


@requires_botorch
def test_acquisition_proposal_has_predictions_and_units(fitted, pool):
    result = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    assert result.status == "ok" and result.reason == "ok"
    assert result.selection_reason == "acquisition"
    assert result.candidate_id in {f"pool-{i:02d}" for i in range(8)}
    assert result.counts["legal"] == 8
    predicted = result.predicted
    assert predicted is not None
    assert predicted["j_lower"] <= predicted["j_mean"] <= predicted["j_upper"]
    assert "model credible interval" in predicted["interval_label"]
    assert result.acquisition is not None
    assert "ranking diagnostic" in result.acquisition["units"]
    assert np.isfinite(result.acquisition["value"])
    assert result.acquisition["acq_seed"] == 0
    assert result.next_proposal_index == 1


@requires_botorch
def test_acquisition_proposal_is_reproducible(fitted, pool):
    a = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    b = propose_one(fitted, pool, history=ProposalHistory(proposal_index=0))
    assert a.candidate_id == b.candidate_id
    assert a.acquisition["value"] == pytest.approx(b.acquisition["value"], rel=1e-6, abs=1e-6)
    assert a.predicted["j_mean"] == pytest.approx(b.predicted["j_mean"], rel=1e-9, abs=1e-12)


def test_publication_refuses_missing_validation_context(pool):
    result = propose_mod.propose_one(None, pool)
    assert result.reason == "capability_missing"
    assert result.candidate is None and result.next_proposal_index == 0


def test_maximin_ties_choose_geometry_id():
    pool = _make_pool([[0.1, 0.1], [0.9, 0.9]])
    a, b = pool.candidates
    a = dataclasses.replace(a, geometry_hash="z")
    b = dataclasses.replace(b, geometry_hash="a")
    pick = propose_mod._maximin_pick([(a, a.active_vector), (b, b.active_vector)], [])
    assert pick[0].geometry_hash == "a"


def test_pending_identity_requires_matching_vector(pool):
    result = propose_mod._propose_one(None, pool, history=ProposalHistory(
        pending_identities=(("g", "s"),)))
    assert result.candidate is None and result.next_proposal_index == 0
    assert "pending vector" in result.detail
