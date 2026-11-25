"""Focused tests for the metric-composite acquisition and q=1 proposal (Pass 1).

These tests use a real CPU ``float64`` BoTorch fit on synthetic data; they are not individually
skipped.  The whole module skips only when the optional bayes engine is absent.  Run from the
worktree root with the isolated bayes interpreter:

    $env:PYTHONPATH="C:\\Users\\hunte\\Hrns\\hornfab-metric-bo-wt"
    & C:\\Users\\hunte\\Hrns\\oc-wt\\bo-study\\bayes-venv\\Scripts\\python.exe -m pytest \
        tests/test_bo_metric_propose.py -q
"""
from __future__ import annotations

import sys

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("botorch")
pytest.importorskip("linear_operator")

from hornlab_search.bo.data import POOL_STATUS_NOTE, CandidatePool, PoolCandidate
from hornlab_search.bo.metric_contracts import (
    V10_COMPONENT_NAMES,
    MetricAcquisitionResult,
    MetricModelFitResult,
    MetricTrainingArtifact,
    sha256_json,
)
from hornlab_search.bo.metric_model import fit_metric_model
from hornlab_search.bo.metric_objective import (
    MetricAcquisitionScores,
    build_metric_acquisition,
    evaluate_metric_candidates,
    stable_argmax,
)
from hornlab_search.bo.metric_propose import (
    MetricProposalHistory,
    MetricProposalPolicy,
    propose_metric_candidate,
)

D = 3
N = 40
COMPONENT_NAMES = V10_COMPONENT_NAMES


def synthetic_components(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2]
    load = 0.10 + 0.30 * x0 + 0.02 * x1
    coverage = 0.10 + 0.20 * x0 + 0.03 * x2
    ripple = 0.05 + 0.15 * x0 * x1 + 0.02 * x2
    other = np.full(X.shape[0], 0.25)
    return np.column_stack([load, coverage, ripple, other])


def make_artifact(*, n: int = N, d: int = D, seed: int = 5) -> MetricTrainingArtifact:
    rng = np.random.default_rng(seed)
    X = rng.random((n, d))
    Y = synthetic_components(X)
    J = np.sum(Y, axis=1, keepdims=True)
    metadata = {"objective_version": 10, "bounds_hash": "synthetic-bounds-v1"}
    checksum = sha256_json({"X": X.tolist(), "J": J.tolist(), "Y": Y.tolist(),
                            "metadata": metadata})
    return MetricTrainingArtifact(
        status="ok", objective_version=10,
        feature_names=("x0", "x1", "x2")[:d], component_names=tuple(COMPONENT_NAMES),
        X=X, J=J, Y_components=Y,
        observation_ids=tuple(f"obs-{i:03d}" for i in range(n)),
        selected_ids=tuple(f"obs-{i:03d}" for i in range(n)),
        metadata=metadata, checksum=checksum)


@pytest.fixture(scope="module")
def artifact():
    return make_artifact()


@pytest.fixture(scope="module")
def fitted(artifact):
    return fit_metric_model(artifact, seed=0)


def _make_pool(vectors, *, ids=None, geometries=None, status="ok", seeds=(0,),
               solve_hash="solve-0"):
    candidates = []
    for i, vector in enumerate(vectors):
        arr = np.asarray(vector, dtype=np.float64).reshape(-1)
        cid = f"pool-{i:02d}" if ids is None else str(ids[i])
        geom = f"geom-pool-{i:02d}" if geometries is None else str(geometries[i])
        candidates.append(PoolCandidate(
            candidate_id=cid, pool_index=i, seed=int(seeds[0]),
            active_vector=arr.copy(), full_vector=arr.copy(),
            design_hash=f"design-{cid}", geometry_hash=geom,
            intended_solve_hash=solve_hash, params={}, descriptors={}, checks={}))
    return CandidatePool(
        status=status, requested=len(candidates),
        seed=(None if not seeds else int(seeds[0])),
        seeds_tried=tuple(int(s) for s in seeds), candidates=tuple(candidates),
        counts={"unique": len(candidates)}, seed_reports=(),
        intended_solve_hash=solve_hash, note=POOL_STATUS_NOTE)


# ------------------------------------------------------------------ acquisition


def test_qlognei_uses_modellistgp_and_seeded_sampler(fitted):
    import torch
    from botorch.models import ModelListGP

    acq = build_metric_acquisition(fitted, acq_seed=7)
    assert acq.status == "ok" and acq.reason == "ok"
    assert isinstance(acq.acq.model, ModelListGP)
    assert len(acq.acq.model.models) == 4
    assert acq.acq.sampler.sample_shape == torch.Size([128])
    assert acq.acq_seed == 7 and acq.sample_shape == 128
    assert acq.prune_baseline is False
    assert acq.policy == "metric_composite_v1"
    assert acq.X_baseline.shape == fitted.train_X.shape
    assert np.allclose(acq.X_baseline, fitted.train_X)


def test_composite_objective_sign_lower_j_is_higher_utility(fitted):
    import torch
    from botorch.acquisition.objective import GenericMCObjective

    objective = GenericMCObjective(lambda samples, X: -samples.sum(dim=-1))
    # Two candidates (q=1) with component sums 0.4 and 1.4; lower J must have higher utility.
    samples = torch.tensor([[[[0.1, 0.1, 0.1, 0.1]]],
                            [[[0.35, 0.35, 0.35, 0.35]]]], dtype=torch.float64)
    samples = samples.reshape(2, 1, 1, 4)
    utility = objective(samples, None)
    assert float(utility[0]) == pytest.approx(-0.4)
    assert float(utility[1]) == pytest.approx(-1.4)
    assert float(utility[0]) > float(utility[1])


def test_acquisition_prefers_the_candidate_with_lower_predicted_j(fitted):
    from hornlab_search.bo.metric_model import predict_metric_components

    low = np.array([[0.02, 0.50, 0.50]])
    high = np.array([[0.98, 0.50, 0.50]])
    pred_low = predict_metric_components(fitted, low)
    pred_high = predict_metric_components(fitted, high)
    assert pred_low.status == pred_high.status == "ok"
    assert float(pred_low.j_mean[0]) < float(pred_high.j_mean[0])

    acq = build_metric_acquisition(fitted, acq_seed=1)
    scores = evaluate_metric_candidates(acq, np.vstack([low, high]))
    assert scores.status == "ok"
    assert scores.values.shape == (2,)
    assert np.all(np.isfinite(scores.values))
    # Composite utility is -sum(components): the lower predicted J gets the higher acquisition.
    assert float(scores.values[0]) > float(scores.values[1])


def test_chunked_q1_evaluation_and_stable_tie(fitted):
    candidates = np.array([
        [0.10, 0.10, 0.10],
        [0.20, 0.20, 0.20],
        [0.30, 0.30, 0.30],
        [0.40, 0.40, 0.40],
        [0.50, 0.50, 0.50],
    ])
    acq = build_metric_acquisition(fitted, acq_seed=3)
    whole = evaluate_metric_candidates(acq, candidates, chunk_size=64)
    small = evaluate_metric_candidates(acq, candidates, chunk_size=2)
    assert whole.status == small.status == "ok"
    assert whole.chunks == 1 and small.chunks == 3
    assert np.allclose(whole.values, small.values, rtol=1e-5, atol=1e-5)
    assert stable_argmax(np.array([1.0, 1.0, 0.5]), ["b", "a", "c"]) == 1
    assert stable_argmax(np.array([np.nan, np.nan]), ["a", "b"]) is None


def test_acquisition_is_reproducible_with_same_seed(fitted):
    candidates = np.random.default_rng(9).random((6, D))
    a = evaluate_metric_candidates(build_metric_acquisition(fitted, acq_seed=11), candidates)
    b = evaluate_metric_candidates(build_metric_acquisition(fitted, acq_seed=11), candidates)
    assert a.status == b.status == "ok"
    assert np.allclose(a.values, b.values, rtol=1e-6, atol=1e-6)


def test_missing_model_and_absent_engine_are_tagged(fitted, monkeypatch):
    missing = build_metric_acquisition(None)
    assert missing.status == "unavailable"
    assert missing.reason == "model_unavailable"
    scores = evaluate_metric_candidates(missing, np.zeros((2, D)))
    assert scores.status == "unavailable" and scores.values is None

    for key in [k for k in sys.modules if k == "botorch" or k.startswith("botorch.")]:
        monkeypatch.delitem(sys.modules, key, raising=False)
    monkeypatch.setitem(sys.modules, "botorch", None)
    absent = build_metric_acquisition(fitted)
    assert absent.status == "unavailable"
    assert absent.reason == "capability_missing"
    assert absent.acq is None


def test_nonfinite_acquisition_never_returns_a_score():
    import torch

    class FakeAcq:
        def __call__(self, tensor):
            return torch.full((tensor.shape[0],), float("nan"), dtype=torch.float64)

    fake = MetricAcquisitionResult(status="ok", reason="ok", acq=FakeAcq(), acq_seed=0)
    scores = evaluate_metric_candidates(fake, np.random.default_rng(1).random((4, D)))
    assert scores.status == "unavailable"
    assert scores.reason == "nonfinite_acquisition"
    assert scores.values is not None and np.all(np.isnan(scores.values))
    assert stable_argmax(scores.values, ["a", "b", "c", "d"]) is None


# ------------------------------------------------------------------ proposal


def test_proposal_filters_bounds_dedup_pending_and_duplicates(artifact, fitted):
    training_vector = np.array(fitted.train_X[0], copy=True)
    pending_vector = np.array([0.70, 0.70, 0.70])
    vectors = [
        training_vector,                    # near-duplicate of training
        [1.10, 0.20, 0.30],                 # out of bounds high
        [-0.10, 0.20, 0.30],                # out of bounds low
        [np.nan, 0.20, 0.30],               # non-finite
        [0.90, 0.90, 0.90],                 # known geometry
        pending_vector,                     # pending identity
        [0.80, 0.80, 0.80],                 # accepted
        [0.80 + 5e-7, 0.80, 0.80],          # near-duplicate of accepted
        [0.15, 0.25, 0.35],                 # legal
        [0.45, 0.55, 0.65],                 # legal
        [0.85, 0.15, 0.75],                 # legal
    ]
    geometries = ["geom-train", "geom-hi", "geom-lo", "geom-nan", "geom-known",
                  "geom-pending", "geom-a", "geom-b", "geom-c", "geom-d", "geom-e"]
    pool = _make_pool(vectors, geometries=geometries)
    history = MetricProposalHistory(
        proposal_index=2,
        excluded_geometry_hashes=("geom-known",),
        pending_identities=(("geom-pending", "solve-0"),),
        pending_vectors=(pending_vector,))
    result = propose_metric_candidate(fitted, pool, history=history)
    assert result.status == "ok" and result.reason == "ok"
    counts = result.counts
    assert counts["input"] == len(vectors)
    assert counts["excluded_bad_vector"] == 1
    assert counts["excluded_out_of_bounds"] == 2
    assert counts["excluded_known"] == 1
    assert counts["excluded_pending"] == 1
    assert counts["excluded_near_duplicate"] == 1
    assert counts["excluded_near_pool_duplicate"] == 1
    assert counts["legal"] == 4
    assert result.candidate_id in {"pool-06", "pool-08", "pool-09", "pool-10"}
    assert result.proposal_index == 2 and result.next_proposal_index == 3
    chosen = np.asarray(result.candidate["active_vector"], dtype=float)
    assert np.all(chosen >= 0.0) and np.all(chosen <= 1.0)


def test_proposal_records_predictions_hashes_seeds_and_timings(artifact, fitted):
    pool = _make_pool([[0.15, 0.25, 0.35], [0.85, 0.65, 0.45]])
    policy = MetricProposalPolicy(acq_seed=5, proposal_seed=9, bounds_hash="bounds-v1")
    result = propose_metric_candidate(fitted, pool, policy=policy,
                                      history=MetricProposalHistory(proposal_index=0))
    assert result.status == "ok"
    assert result.selection_reason == "acquisition"
    assert result.policy == "metric_composite_v1"
    assert result.model_hash == fitted.model_hash
    assert result.data_hash == artifact.checksum
    assert result.bounds_hash == "bounds-v1"
    assert result.acq_seed == 5 and result.proposal_seed == 9
    assert result.candidate_id in {"pool-00", "pool-01"}
    assert result.acquisition_score is not None and np.isfinite(result.acquisition_score)
    assert result.predicted_j is not None and np.isfinite(result.predicted_j)
    assert len(result.component_means) == 4 and len(result.component_sds) == 4
    assert all(np.isfinite(v) for v in result.component_means)
    assert all(np.isfinite(v) and v >= 0.0 for v in result.component_sds)
    assert result.predicted_j == pytest.approx(sum(result.component_means), rel=0.0, abs=0.0)
    assert result.total_sd == pytest.approx(
        float(np.sqrt(np.sum(np.square(result.component_sds)))), rel=0.0, abs=1e-12)
    assert result.fit_s is not None and result.fit_s >= 0.0
    assert result.acquisition_s is not None and result.acquisition_s >= 0.0
    assert result.timing_s is not None and result.timing_s >= 0.0
    assert "not solved acoustic results" in (result.detail or "")
    assert "ranking diagnostic" in result.counts["acquisition_units"]


def test_proposal_is_deterministic_with_same_seeds(fitted):
    pool = _make_pool([[0.10, 0.20, 0.30], [0.40, 0.50, 0.60], [0.70, 0.80, 0.90]])
    policy = MetricProposalPolicy(acq_seed=13, proposal_seed=2)
    history = MetricProposalHistory(proposal_index=4)
    a = propose_metric_candidate(fitted, pool, policy=policy, history=history)
    b = propose_metric_candidate(fitted, pool, policy=policy, history=history)
    assert a.status == b.status == "ok"
    assert a.candidate_id == b.candidate_id
    assert a.acquisition_score == pytest.approx(b.acquisition_score, rel=1e-6, abs=1e-9)
    assert a.predicted_j == pytest.approx(b.predicted_j, rel=1e-9, abs=1e-12)
    assert a.component_means == pytest.approx(b.component_means, rel=1e-9, abs=1e-12)


def test_proposal_accepts_an_already_restricted_pool(fitted):
    full = _make_pool([[0.10, 0.20, 0.30], [0.40, 0.50, 0.60],
                       [0.70, 0.80, 0.90], [0.90, 0.10, 0.50]])
    restricted = _make_pool([full.candidates[1].active_vector,
                             full.candidates[3].active_vector],
                            ids=["pool-01", "pool-03"],
                            geometries=["geom-pool-01", "geom-pool-03"])
    result = propose_metric_candidate(fitted, restricted,
                                      history=MetricProposalHistory(proposal_index=0))
    assert result.status == "ok"
    assert result.counts["input"] == 2
    assert result.candidate_id in {"pool-01", "pool-03"}


def test_pool_exhausted_and_model_unavailable_fabricate_nothing(fitted):
    exhausted = _make_pool([[0.2, 0.2, 0.2]], status="pool_exhausted")
    empty = propose_metric_candidate(fitted, exhausted)
    assert empty.status == "unavailable"
    assert empty.reason == "pool_exhausted"
    assert empty.candidate is None and empty.predicted_j is None

    pool = _make_pool([[0.2, 0.2, 0.2], [0.8, 0.8, 0.8]])
    missing = propose_metric_candidate(None, pool)
    assert missing.status == "unavailable"
    assert missing.reason == "insufficient_data"
    assert missing.candidate is None and missing.predicted_j is None

    failed_fit = MetricModelFitResult(status="unavailable", reason="output_fit_failed:ripple_j")
    failed = propose_metric_candidate(failed_fit, pool)
    assert failed.status == "unavailable"
    assert "ripple_j" in failed.reason
    assert failed.candidate is None and failed.component_means == ()


def test_acquisition_failure_returns_unavailable_without_candidate(fitted, monkeypatch):
    import torch
    import hornlab_search.bo.metric_propose as propose_mod

    class FakeAcq:
        def __call__(self, tensor):
            return torch.full((tensor.shape[0],), float("nan"), dtype=torch.float64)

    fake = MetricAcquisitionResult(status="ok", reason="ok", acq=FakeAcq(), acq_seed=0)
    monkeypatch.setattr(propose_mod, "build_metric_acquisition", lambda *a, **k: fake)
    pool = _make_pool([[0.2, 0.2, 0.2], [0.8, 0.8, 0.8]])
    result = propose_metric_candidate(fitted, pool)
    assert result.status == "unavailable"
    assert result.reason == "nonfinite_acquisition"
    assert result.candidate is None
    assert result.predicted_j is None and result.component_means == ()


def test_invalid_pending_history_is_tagged(fitted):
    pool = _make_pool([[0.2, 0.2, 0.2], [0.8, 0.8, 0.8]])
    history = MetricProposalHistory(pending_identities=(("geom-x", "solve-0"),))
    result = propose_metric_candidate(fitted, pool, history=history)
    assert result.status == "unavailable"
    assert result.reason == "invalid_history"
    assert result.candidate is None


def test_proposal_engine_does_not_import_bem_solver_or_dataset_modules(fitted):
    pool = _make_pool([[0.2, 0.2, 0.2], [0.8, 0.8, 0.8]])
    before = set(sys.modules)
    result = propose_metric_candidate(fitted, pool)
    assert result.status == "ok"
    new_modules = set(sys.modules) - before
    forbidden = ("hornlab_search.solve", "hornlab_search.dataset",
                 "hornlab_beat_bem", "hornlab_mesher")
    leaked = [name for name in new_modules
              if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)]
    assert leaked == []
