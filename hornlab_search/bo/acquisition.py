"""Locked qLogNEI acquisition for scalar-pool v1 (B3, protocol bo-study-v1.1).

The acquisition is ``qLogNoisyExpectedImprovement`` with the observed eligible training ``X`` as
``X_baseline``, a ``SobolQMCNormalSampler(sample_shape=[128], seed=acq_seed)`` and
``prune_baseline=False`` (spec 3.3/3.4).  Candidates are scored q=1 in chunks of 64.

The acquisition value is a **ranking diagnostic**, never predicted ``J`` or a probability of
success.  BoTorch is imported lazily inside the functions; when it is absent callers get a tagged
``capability_missing`` result.  A nonfinite or failed evaluation returns a tagged
``model_unavailable`` / ``nonfinite_acquisition`` result with no fabricated scores.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .model import (
    NUM_THREADS,
    REASON_CAPABILITY_MISSING,
    REASON_MODEL_UNAVAILABLE,
    REASON_OK,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    library_versions,
)

ACQUISITION_POLICY = "qLogNoisyExpectedImprovement"
SAMPLER_SAMPLE_SHAPE = 128
PRUNE_BASELINE = False
POOL_CHUNK_SIZE = 64
REASON_NONFINITE_ACQUISITION = "nonfinite_acquisition"
ACQUISITION_UNITS = (
    "log qLogNEI acquisition score (ranking diagnostic only; not predicted J, not a "
    "probability of success)")


def _import_acq_engine():
    """Lazily import the optional acquisition stack.  Returns ``(engine, error)``."""
    try:
        import torch
        from botorch.acquisition.logei import qLogNoisyExpectedImprovement
        from botorch.sampling.normal import SobolQMCNormalSampler
    except Exception as exc:  # noqa: BLE001 - absence is a capability error
        return None, f"{type(exc).__name__}: {exc}"
    return {"torch": torch, "qLogNEI": qLogNoisyExpectedImprovement,
            "SobolQMCNormalSampler": SobolQMCNormalSampler}, None


@dataclass(frozen=True)
class AcquisitionResult:
    """A built qLogNEI acquisition object plus its frozen provenance."""

    status: str
    reason: str
    detail: str | None = None
    acq: Any = field(default=None, repr=False, compare=False)
    X_baseline: np.ndarray | None = field(default=None, repr=False, compare=False)
    X_pending: np.ndarray | None = field(default=None, repr=False, compare=False)
    acq_seed: int = 0
    sample_shape: int = SAMPLER_SAMPLE_SHAPE
    prune_baseline: bool = PRUNE_BASELINE
    policy: str = ACQUISITION_POLICY
    library_versions: dict = field(default_factory=dict)
    timing_s: float | None = None

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "X_baseline": (None if self.X_baseline is None
                           else np.asarray(self.X_baseline, dtype=float).tolist()),
            "X_pending": None if self.X_pending is None else self.X_pending.tolist(),
            "acq_seed": int(self.acq_seed),
            "sample_shape": int(self.sample_shape),
            "prune_baseline": bool(self.prune_baseline),
            "policy": self.policy,
            "library_versions": dict(self.library_versions),
            "timing_s": self.timing_s,
        }


@dataclass(frozen=True)
class AcquisitionScores:
    """Scores for a candidate pool: q=1 in chunks, stable ties by candidate id downstream."""

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


def build_acquisition(model_result, *, acq_seed: int = 0,
                      sample_shape: int = SAMPLER_SAMPLE_SHAPE,
                      X_baseline=None, X_pending=None) -> AcquisitionResult:
    """Build ``qLogNEI`` with the observed eligible ``X_baseline``.

    ``X_baseline`` defaults to the fitted model's training ``X``.  The sampler seed is the
    recorded ``acq_seed``; ``prune_baseline`` stays ``False``.
    """
    started = time.perf_counter()
    versions = library_versions()
    if model_result is None or getattr(model_result, "status", None) != STATUS_OK \
            or getattr(model_result, "model", None) is None:
        reason = getattr(model_result, "reason", REASON_MODEL_UNAVAILABLE) \
            if model_result is not None else REASON_MODEL_UNAVAILABLE
        if reason == REASON_CAPABILITY_MISSING:
            return AcquisitionResult(status=STATUS_UNAVAILABLE, reason=reason,
                                     detail=getattr(model_result, "detail", None),
                                     acq_seed=acq_seed, sample_shape=sample_shape,
                                     library_versions=versions,
                                     timing_s=time.perf_counter() - started)
        return AcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=(f"no fitted model (model reason={reason!r})"),
            acq_seed=acq_seed, sample_shape=sample_shape, library_versions=versions,
            timing_s=time.perf_counter() - started)

    engine, import_error = _import_acq_engine()
    if engine is None:
        return AcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING,
            detail=f"optional BoTorch acquisition engine is unavailable: {import_error}",
            acq_seed=acq_seed, sample_shape=sample_shape, library_versions=versions,
            timing_s=time.perf_counter() - started)

    baseline = X_baseline if X_baseline is not None else model_result.train_X
    if baseline is None:
        return AcquisitionResult(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                 detail="no observed X_baseline is available",
                                 acq_seed=acq_seed, sample_shape=sample_shape,
                                 library_versions=versions,
                                 timing_s=time.perf_counter() - started)
    baseline_arr = np.asarray(baseline, dtype=np.float64)
    if baseline_arr.ndim != 2 or baseline_arr.shape[0] < 1:
        return AcquisitionResult(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                 detail=f"X_baseline has an invalid shape {baseline_arr.shape}",
                                 acq_seed=acq_seed, sample_shape=sample_shape,
                                 library_versions=versions,
                                 timing_s=time.perf_counter() - started)

    pending_arr = None
    if X_pending is not None:
        try:
            pending_arr = np.asarray(X_pending, dtype=np.float64)
            if (pending_arr.ndim != 2 or pending_arr.shape[1] != baseline_arr.shape[1]
                    or not np.all(np.isfinite(pending_arr))):
                raise ValueError("X_pending must be finite and have the baseline dimension")
            if not len(pending_arr):
                pending_arr = None
        except (ValueError, TypeError) as exc:
            return AcquisitionResult(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                     detail=str(exc), library_versions=versions)
    torch = engine["torch"]
    try:
        try:
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        sampler = engine["SobolQMCNormalSampler"](torch.Size([int(sample_shape)]),
                                                  seed=int(acq_seed))
        acq = engine["qLogNEI"](
            model=model_result.model,
            X_baseline=torch.as_tensor(baseline_arr, dtype=torch.float64),
            sampler=sampler,
            prune_baseline=False,
            X_pending=(None if pending_arr is None else
                       torch.as_tensor(pending_arr, dtype=torch.float64)),
        )
    except Exception as exc:  # noqa: BLE001 - never escape an engine failure
        return AcquisitionResult(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"qLogNEI construction failed: {type(exc).__name__}: {exc}",
            acq_seed=acq_seed, sample_shape=sample_shape, library_versions=versions,
            timing_s=time.perf_counter() - started)
    return AcquisitionResult(
        status=STATUS_OK, reason=REASON_OK, acq=acq,
        X_baseline=np.array(baseline_arr, dtype=np.float64, copy=True),
        X_pending=None if pending_arr is None else pending_arr.copy(),
        acq_seed=int(acq_seed), sample_shape=int(sample_shape),
        prune_baseline=False, library_versions=versions,
        timing_s=time.perf_counter() - started)


def evaluate_candidates(acquisition_result: AcquisitionResult, X, *,
                        chunk_size: int = POOL_CHUNK_SIZE) -> AcquisitionScores:
    """Evaluate q=1 acquisition for each candidate in chunks of ``chunk_size`` (default 64)."""
    started = time.perf_counter()
    if acquisition_result is None or acquisition_result.status != STATUS_OK \
            or acquisition_result.acq is None:
        reason = (getattr(acquisition_result, "reason", REASON_MODEL_UNAVAILABLE)
                  if acquisition_result is not None else REASON_MODEL_UNAVAILABLE)
        return AcquisitionScores(status=STATUS_UNAVAILABLE, reason=reason,
                                 detail=getattr(acquisition_result, "detail", None),
                                 chunk_size=chunk_size,
                                 acq_seed=getattr(acquisition_result, "acq_seed", 0),
                                 timing_s=time.perf_counter() - started)
    try:
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim != 2:
            raise ValueError(f"candidate X must be 2-D, got shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("candidate X contains NaN/Inf")
    except (TypeError, ValueError) as exc:
        return AcquisitionScores(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                 detail=str(exc), chunk_size=chunk_size,
                                 acq_seed=acquisition_result.acq_seed,
                                 timing_s=time.perf_counter() - started)

    engine, import_error = _import_acq_engine()
    if engine is None:
        return AcquisitionScores(status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING,
                                 detail=import_error, chunk_size=chunk_size,
                                 acq_seed=acquisition_result.acq_seed,
                                 timing_s=time.perf_counter() - started)
    torch = engine["torch"]
    try:
        try:
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        step = max(1, int(chunk_size))
        pieces: list[np.ndarray] = []
        chunks = 0
        with torch.no_grad():
            for start in range(0, arr.shape[0], step):
                chunk = arr[start:start + step]
                tensor = torch.as_tensor(chunk, dtype=torch.float64).unsqueeze(-2)  # (b, 1, d)
                values = acquisition_result.acq(tensor)
                pieces.append(values.detach().cpu().numpy().reshape(-1))
                chunks += 1
        scores = (np.concatenate(pieces, axis=0) if pieces
                  else np.empty((0,), dtype=np.float64))
    except Exception as exc:  # noqa: BLE001 - a failed acquisition never yields scores
        return AcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"acquisition evaluation failed: {type(exc).__name__}: {exc}",
            n=int(arr.shape[0]), chunk_size=chunk_size,
            acq_seed=acquisition_result.acq_seed,
            timing_s=time.perf_counter() - started)

    if scores.size != arr.shape[0]:
        return AcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=f"acquisition returned {scores.size} values for {arr.shape[0]} candidates",
            n=int(arr.shape[0]), chunk_size=chunk_size, chunks=chunks,
            acq_seed=acquisition_result.acq_seed,
            timing_s=time.perf_counter() - started)
    finite = np.isfinite(scores)
    nonfinite = int((~finite).sum())
    if not bool(finite.any()):
        return AcquisitionScores(
            status=STATUS_UNAVAILABLE, reason=REASON_NONFINITE_ACQUISITION,
            detail="every candidate acquisition value is nonfinite",
            values=scores, finite_mask=finite, n=int(scores.size), chunk_size=chunk_size,
            chunks=chunks, nonfinite_count=nonfinite,
            acq_seed=acquisition_result.acq_seed,
            timing_s=time.perf_counter() - started)
    return AcquisitionScores(
        status=STATUS_OK, reason=REASON_OK, values=scores, finite_mask=finite,
        n=int(scores.size), chunk_size=chunk_size, chunks=chunks, nonfinite_count=nonfinite,
        acq_seed=acquisition_result.acq_seed,
        timing_s=time.perf_counter() - started)


def stable_argmax(values, candidate_ids) -> int | None:
    """Largest **finite** value; ties broken by the lexicographically smallest candidate id.

    Returns the index into ``values``/``candidate_ids`` or ``None`` when nothing is finite.
    """
    vals = np.asarray(values, dtype=np.float64).reshape(-1)
    ids = tuple(str(c) for c in candidate_ids)
    if vals.size == 0 or vals.size != len(ids):
        return None
    finite = np.flatnonzero(np.isfinite(vals))
    if finite.size == 0:
        return None
    best = float(np.max(vals[finite]))
    tied = [int(i) for i in finite if float(vals[i]) == best]
    return min(tied, key=lambda i: (ids[i], i))


__all__ = [
    "ACQUISITION_POLICY",
    "SAMPLER_SAMPLE_SHAPE",
    "PRUNE_BASELINE",
    "POOL_CHUNK_SIZE",
    "ACQUISITION_UNITS",
    "REASON_NONFINITE_ACQUISITION",
    "AcquisitionResult",
    "AcquisitionScores",
    "build_acquisition",
    "evaluate_candidates",
    "stable_argmax",
]
