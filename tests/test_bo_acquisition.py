"""Focused tests for locked qLogNEI acquisition (hornlab_search/bo/acquisition.py).

Engine-using tests are skipped when BoTorch is absent; the nonfinite/capability gates are not.
"""
from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pytest

from hornlab_search.bo import (
    AcquisitionResult,
    build_acquisition,
    build_training_set,
    evaluate_candidates,
    fit_model,
    make_pure_observations,
    stable_argmax,
)
from hornlab_search.bo.acquisition import ACQUISITION_UNITS

HAS_BOTORCH = importlib.util.find_spec("botorch") is not None
requires_botorch = pytest.mark.skipif(
    not HAS_BOTORCH, reason="optional BoTorch engine (isolated bayes venv) absent")


@pytest.fixture(scope="module")
def fitted():
    ts = build_training_set(make_pure_observations(2, 16, seed=1), d=2)
    return fit_model(ts, seed=0)


@pytest.fixture(scope="module")
def candidates():
    return np.random.default_rng(3).random((20, 2))


@requires_botorch
def test_build_acquisition_is_locked(fitted, candidates):
    acq = build_acquisition(fitted, acq_seed=7)
    assert acq.status == "ok" and acq.reason == "ok"
    assert acq.acq_seed == 7
    assert acq.sample_shape == 128
    assert acq.prune_baseline is False
    assert acq.policy == "qLogNoisyExpectedImprovement"
    assert acq.X_baseline.shape == fitted.train_X.shape
    assert np.allclose(acq.X_baseline, fitted.train_X)
    assert "ranking diagnostic" in ACQUISITION_UNITS
    scores = evaluate_candidates(acq, candidates)
    assert scores.status == "ok" and scores.reason == "ok"
    assert scores.values.shape == (20,)
    assert np.all(np.isfinite(scores.values))
    assert int(scores.nonfinite_count) == 0
    assert scores.chunks == 1  # q=1 pool of 20 in one chunk of 64
    assert scores.acq_seed == 7


@requires_botorch
def test_same_seed_acquisition_is_reproducible(fitted, candidates):
    a = evaluate_candidates(build_acquisition(fitted, acq_seed=11), candidates)
    b = evaluate_candidates(build_acquisition(fitted, acq_seed=11), candidates)
    assert a.status == b.status == "ok"
    assert np.allclose(a.values, b.values, rtol=1e-6, atol=1e-6)


@requires_botorch
def test_chunked_evaluation_is_consistent(fitted, candidates):
    acq = build_acquisition(fitted, acq_seed=5)
    whole = evaluate_candidates(acq, candidates, chunk_size=64)
    small = evaluate_candidates(acq, candidates, chunk_size=3)
    assert whole.status == small.status == "ok"
    assert whole.chunks == 1 and small.chunks == 7
    assert np.allclose(whole.values, small.values, rtol=1e-5, atol=1e-5)


def test_stable_argmax_ties_by_candidate_id_and_ignores_nonfinite():
    values = np.array([1.0, 1.0, 0.5, np.inf, np.nan])
    ids = ["b", "a", "c", "z", "d"]
    assert stable_argmax(values, ids) == 1  # tie between "a" and "b" -> "a"
    assert stable_argmax(np.array([np.nan, np.nan]), ["a", "b"]) is None
    assert stable_argmax(np.array([]), []) is None


def test_missing_model_is_a_tagged_unavailability(candidates):
    acq = build_acquisition(None, acq_seed=0)
    assert acq.status == "unavailable"
    assert acq.reason == "model_unavailable"
    scores = evaluate_candidates(acq, candidates)
    assert scores.status == "unavailable"
    assert scores.values is None  # never zero predictions


@requires_botorch
def test_nonfinite_acquisition_never_returns_scores(monkeypatch):
    torch = pytest.importorskip("torch")

    class FakeAcq:
        def __call__(self, tensor):
            return torch.full((tensor.shape[0],), float("nan"), dtype=torch.float64)

    fake = AcquisitionResult(status="ok", reason="ok", acq=FakeAcq(), acq_seed=0)
    scores = evaluate_candidates(fake, np.random.default_rng(1).random((4, 2)))
    assert scores.status == "unavailable"
    assert scores.reason == "nonfinite_acquisition"
    assert scores.values is not None and np.all(np.isnan(scores.values))
    assert scores.finite_mask is not None and not bool(scores.finite_mask.any())
    assert stable_argmax(scores.values, ["a", "b", "c", "d"]) is None


def test_optional_engine_absent_is_a_clean_capability_error(fitted, monkeypatch):
    # A cached ``botorch.*`` submodule would bypass a bare ``sys.modules["botorch"] = None``.
    for key in [k for k in sys.modules if k == "botorch" or k.startswith("botorch.")]:
        monkeypatch.delitem(sys.modules, key, raising=False)
    monkeypatch.setitem(sys.modules, "botorch", None)
    acq = build_acquisition(fitted, acq_seed=0)
    assert acq.status == "unavailable"
    assert acq.reason == "capability_missing"
    assert acq.acq is None


@requires_botorch
def test_pending_points_reach_botorch(fitted):
    pending = np.array([[0.123, 0.456]])
    result = build_acquisition(fitted, X_pending=pending)
    assert result.ok
    assert np.array_equal(result.acq._full_X_baseline[-1:].detach().cpu().numpy(), pending)
    assert np.array_equal(result.X_pending, pending)
    assert not build_acquisition(fitted, X_pending=[[float("nan"), 0.5]]).ok

