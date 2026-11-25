"""Composite metric acquisition for the metric-composite engine (Pass 1).

The acquisition is a ``qLogNoisyExpectedImprovement`` over a :class:`ModelListGP`.  The scalar
objective is reconstructed from posterior **samples** of the component vector:

    utility(samples) = -sum(samples over the component dimension)   # lower J is better

so the existing scalar ``J`` identity remains the decision quantity without duplicating any
scoring formula.  The sampler is a seeded ``SobolQMCNormalSampler`` with ``sample_shape=[128]``;
``prune_baseline=False`` and ``cache_root=False`` are the locked Pass-1 settings, and candidates
are scored q=1 in chunks of 64.

BoTorch is imported lazily.  A missing engine or any construction/evaluation failure returns a
tagged ``unavailable`` result; no scores are fabricated.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from .acquisition import stable_argmax
from .metric_contracts import METRIC_COMPOSITE_POLICY, MetricAcquisitionResult
from .metric_model import (
    REASON_CAPABILITY_MISSING,
    REASON_INSUFFICIENT_DATA,
    REASON_MODEL_UNAVAILABLE,
    REASON_OK,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    library_versions,
)

ACQUISITION_POLICY = "qLogNoisyExpectedImprovement"
SAMPLER_SAMPLE_SHAPE = 128
PRUNE_BASELINE = False
CACHE_ROOT = False
POOL_CHUNK_SIZE = 64
REASON_NONFINITE_ACQUISITION = "nonfinite_acquisition"
ACQUISITION_UNITS = (
    "composite qLogNEI acquisition score (ranking diagnostic only; not predicted J, not a "
    "probability of success)")


def _import_acq_engine():
    """Lazily import the optional acquisition stack.  Returns ``(engine, error)``."""
    try:
        import torch
        from botorch.acquisition.logei import qLogNoisyExpectedImprovement
        from botorch.acquisition.objective import GenericMCObjective
        from botorch.sampling.normal import SobolQMCNormalSampler
    except Exception as exc:  # noqa: BLE001 - absence is a capability error
        return None, f"{type(exc).__name__}: {exc}"
    return {"torch": torch, "qLogNEI": qLogNoisyExpectedImprovement,
            "GenericMCObjective": GenericMCObjective,
            "SobolQMCNormalSampler": SobolQMCNormalSampler}, None


def composite_utility(samples, X=None):
    """Scalar utility of component posterior samples: ``-sum`` over the output dimension."""
    return -samples.sum(dim=-1)


@dataclass(frozen=True)
class MetricAcquisitionScores:
    """q=1 composite acquisition scores for a candidate pool."""

    status: str
    reason: str
    detail: str | None = None
    values: np.ndarray | None = None
    finite_mask: np.ndarray | None = None
    n: int = 0
    chunk_size: int = POOL_CHUNK_SIZE
    chunks: int = 0
    nonfinite_count: int = 0
    acq_seed: int = 0
    units: str = ACQUISITION_UNITS
    timing_s: float | None = None

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "values": (None if self.values is None
                       else np.asarray(self.values, dtype=float).reshape(-1).tolist()),
            "finite_mask": (None if self.finite_mask is None
                            else np.asarray(self.finite_mask, dtype=bool).reshape(-1).tolist()),
            "n": int(self.n),
            "chunk_size": int(self.chunk_size),
            "chunks": int(self.chunks),
            "nonfinite_count": int(self.nonfinite_count),
            "acq_seed": int(self.acq_seed),
            "units": self.units,
            "timing_s": self.timing_s,
        }


def build_metric_acquisition(model_result, *, acq_seed: int = 0,
                             sample_shape: int = SAMPLER_SAMPLE_SHAPE,
                             X_baseline=None, X_pending=None) -> MetricAcquisitionResult:
    """Build the composite ``qLogNEI`` acquisition over the fitted ``ModelListGP``."""
    started = time.perf_counter()
    versions = library_versions()
    if model_result is None or getattr(model_result, "status", None) != STATUS_OK \
            or getattr(model_result, "model", None) is None:
        reason = (getattr(model_result, "reason", REASON_MODEL_UNAVAILABLE)
                  if model_result is not None else REASON_MODEL_UNAVAILABLE)
        if reason == REASON_CAPABILITY_MISSING:
            return MetricAcquisitionResult(
                status=STATUS_UNAVAILABLE, reason=reason,
                detail=getattr(model_result, "detail", None), acq_seed=int(acq_seed),
                sample_shape=int(sample_shape), library_versions=versions,
                timing_s=time.perf_counter() - started)
        return MetricAcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"no fitted metric model (model reason={reason!r})",
            acq_seed=int(acq_seed), sample_shape=int(sample_shape),
            library_versions=versions, timing_s=time.perf_counter() - started)

    engine, import_error = _import_acq_engine()
    if engine is None:
        return MetricAcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING,
            detail=f"optional BoTorch acquisition engine is unavailable: {import_error}",
            acq_seed=int(acq_seed), sample_shape=int(sample_shape),
            library_versions=versions, timing_s=time.perf_counter() - started)

    baseline = X_baseline if X_baseline is not None else getattr(model_result, "train_X", None)
    if baseline is None:
        return MetricAcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail="no observed X_baseline is available", acq_seed=int(acq_seed),
            sample_shape=int(sample_shape), library_versions=versions,
            timing_s=time.perf_counter() - started)
    baseline_arr = np.asarray(baseline, dtype=np.float64)
    if baseline_arr.ndim != 2 or baseline_arr.shape[0] < 1:
        return MetricAcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"X_baseline has an invalid shape {baseline_arr.shape}",
            acq_seed=int(acq_seed), sample_shape=int(sample_shape),
            library_versions=versions, timing_s=time.perf_counter() - started)

    pending_arr = None
    if X_pending is not None:
        try:
            pending_arr = np.asarray(X_pending, dtype=np.float64)
            if (pending_arr.ndim != 2 or pending_arr.shape[1] != baseline_arr.shape[1]
                    or not np.all(np.isfinite(pending_arr))):
                raise ValueError("X_pending must be finite and match the baseline dimension")
            if not len(pending_arr):
                pending_arr = None
        except (ValueError, TypeError) as exc:
            return MetricAcquisitionResult(
                status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                detail=str(exc), acq_seed=int(acq_seed), sample_shape=int(sample_shape),
                library_versions=versions, timing_s=time.perf_counter() - started)

    torch = engine["torch"]
    try:
        try:
            from .model import NUM_THREADS
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        sampler = engine["SobolQMCNormalSampler"](
            torch.Size([int(sample_shape)]), seed=int(acq_seed))
        objective = engine["GenericMCObjective"](
            lambda samples, X: -samples.sum(dim=-1))
        acq = engine["qLogNEI"](
            model=model_result.model,
            X_baseline=torch.as_tensor(baseline_arr, dtype=torch.float64),
            sampler=sampler,
            objective=objective,
            prune_baseline=False,
            cache_root=False,
            X_pending=(None if pending_arr is None
                       else torch.as_tensor(pending_arr, dtype=torch.float64)),
        )
    except Exception as exc:  # noqa: BLE001 - never escape an engine failure
        return MetricAcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"composite qLogNEI construction failed: {type(exc).__name__}: {exc}",
            acq_seed=int(acq_seed), sample_shape=int(sample_shape),
            library_versions=versions, timing_s=time.perf_counter() - started)

    return MetricAcquisitionResult(
        status=STATUS_OK, reason=REASON_OK, acq=acq,
        X_baseline=np.array(baseline_arr, dtype=np.float64, copy=True),
        X_pending=None if pending_arr is None else pending_arr.copy(),
        acq_seed=int(acq_seed), sample_shape=int(sample_shape), prune_baseline=False,
        policy=METRIC_COMPOSITE_POLICY, library_versions=versions,
        timing_s=time.perf_counter() - started)


def evaluate_metric_candidates(acquisition_result, X, *, chunk_size: int = POOL_CHUNK_SIZE
                               ) -> MetricAcquisitionScores:
    """Evaluate the q=1 composite acquisition for each candidate in chunks of ``chunk_size``."""
    started = time.perf_counter()
    if acquisition_result is None or getattr(acquisition_result, "status", None) != STATUS_OK \
            or getattr(acquisition_result, "acq", None) is None:
        reason = (getattr(acquisition_result, "reason", REASON_MODEL_UNAVAILABLE)
                  if acquisition_result is not None else REASON_MODEL_UNAVAILABLE)
        return MetricAcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=reason,
            detail=getattr(acquisition_result, "detail", None), chunk_size=int(chunk_size),
            acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
            timing_s=time.perf_counter() - started)
    try:
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim != 2:
            raise ValueError(f"candidate X must be 2-D, got shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("candidate X contains NaN/Inf")
    except (TypeError, ValueError) as exc:
        return MetricAcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_INSUFFICIENT_DATA, detail=str(exc),
            chunk_size=int(chunk_size),
            acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
            timing_s=time.perf_counter() - started)

    engine, import_error = _import_acq_engine()
    if engine is None:
        return MetricAcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING,
            detail=import_error, chunk_size=int(chunk_size),
            acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
            timing_s=time.perf_counter() - started)
    torch = engine["torch"]
    try:
        try:
            from .model import NUM_THREADS
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        step = max(1, int(chunk_size))
        pieces: list[np.ndarray] = []
        chunks = 0
        with torch.no_grad():
            for start in range(0, arr.shape[0], step):
                chunk = arr[start:start + step]
                tensor = torch.as_tensor(chunk, dtype=torch.float64).unsqueeze(-2)  # (b,1,d)
                values = acquisition_result.acq(tensor)
                pieces.append(values.detach().cpu().numpy().reshape(-1))
                chunks += 1
        scores = (np.concatenate(pieces, axis=0) if pieces
                  else np.empty((0,), dtype=np.float64))
    except Exception as exc:  # noqa: BLE001 - a failed acquisition never yields scores
        return MetricAcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"composite acquisition evaluation failed: {type(exc).__name__}: {exc}",
            n=int(arr.shape[0]), chunk_size=int(chunk_size),
            acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
            timing_s=time.perf_counter() - started)

    if scores.size != arr.shape[0]:
        return MetricAcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"acquisition returned {scores.size} values for {arr.shape[0]} candidates",
            n=int(arr.shape[0]), chunk_size=int(chunk_size), chunks=chunks,
            acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
            timing_s=time.perf_counter() - started)
    finite = np.isfinite(scores)
    nonfinite = int((~finite).sum())
    if not bool(finite.any()):
        return MetricAcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_NONFINITE_ACQUISITION,
            detail="every candidate acquisition value is nonfinite", values=scores,
            finite_mask=finite, n=int(scores.size), chunk_size=int(chunk_size),
            chunks=chunks, nonfinite_count=nonfinite,
            acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
            timing_s=time.perf_counter() - started)
    return MetricAcquisitionScores(
        status=STATUS_OK, reason=REASON_OK, values=scores, finite_mask=finite,
        n=int(scores.size), chunk_size=int(chunk_size), chunks=chunks,
        nonfinite_count=nonfinite,
        acq_seed=int(getattr(acquisition_result, "acq_seed", 0) or 0),
        timing_s=time.perf_counter() - started)


__all__ = [
    "ACQUISITION_POLICY",
    "SAMPLER_SAMPLE_SHAPE",
    "PRUNE_BASELINE",
    "CACHE_ROOT",
    "POOL_CHUNK_SIZE",
    "REASON_NONFINITE_ACQUISITION",
    "ACQUISITION_UNITS",
    "MetricAcquisitionScores",
    "composite_utility",
    "build_metric_acquisition",
    "evaluate_metric_candidates",
    "stable_argmax",
]
