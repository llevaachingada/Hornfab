"""Deterministic composite q=1 proposal over an existing legal candidate pool (Pass 1).

The proposal engine consumes the frozen B2 pool shape (:class:`~.data.CandidatePool` /
:class:`~.data.PoolCandidate`) or any caller-supplied pool already restricted to a TuRBO local
box.  It never resamples and never implements TuRBO itself.

Selection order:

1. reject invalid/non-finite/out-of-``[0,1]`` active vectors;
2. reject known or explicitly excluded identities;
3. reject dispatched-unresolved pending identities;
4. reject near-duplicates (infinity norm ``<= tol``) of training, pending, excluded or
   previously accepted pool vectors;
5. evaluate the composite ``qLogNEI`` acquisition in q=1 chunks and choose the stable argmax,
   with ties broken by ``candidate_id``.

Model or acquisition failure returns a tagged ``unavailable`` result with no candidate prediction
and no fallback policy.  Predicted values are explicitly model predictions, never solved acoustic
results.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from .acquisition import stable_argmax
from .data import NEAR_DUPLICATE_TOL, is_near_duplicate
from .metric_contracts import (
    METRIC_COMPOSITE_POLICY,
    MetricProposalResult,
)
from .metric_identity import (
    REASON_BOUNDS_MISSING,
    check_bounds_identity,
)
from .metric_model import (
    REASON_CAPABILITY_MISSING,
    REASON_INSUFFICIENT_DATA,
    REASON_MODEL_UNAVAILABLE,
    REASON_OK,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    library_versions,
    predict_metric_components,
)
from .metric_objective import (
    ACQUISITION_UNITS,
    POOL_CHUNK_SIZE,
    SAMPLER_SAMPLE_SHAPE,
    build_metric_acquisition,
    evaluate_metric_candidates,
)

PROPOSE_POLICY = METRIC_COMPOSITE_POLICY
REASON_POOL_EXHAUSTED = "pool_exhausted"
REASON_INVALID_HISTORY = "invalid_history"
PREDICTION_NOTE = "predicted values are model predictions, not solved acoustic results"

SELECTION_ACQUISITION = "acquisition"


@dataclass(frozen=True)
class MetricProposalPolicy:
    """Proposal provenance knobs; the acquisition policy itself is locked."""

    acq_seed: int = 0
    proposal_seed: int = 0
    sample_shape: int = SAMPLER_SAMPLE_SHAPE
    chunk_size: int = POOL_CHUNK_SIZE
    near_duplicate_tol: float = NEAR_DUPLICATE_TOL
    bounds_hash: str = ""


@dataclass(frozen=True)
class MetricProposalHistory:
    """Durable proposal state.  ``pending_identities`` are only dispatched-unresolved jobs."""

    proposal_index: int = 0
    excluded_geometry_hashes: tuple[str, ...] = ()
    excluded_design_hashes: tuple[str, ...] = ()
    excluded_solve_identities: tuple[tuple[str, str], ...] = ()
    pending_identities: tuple[tuple[str, str], ...] = ()
    pending_vectors: tuple = field(default=(), repr=False, compare=False)
    excluded_vectors: tuple = field(default=(), repr=False, compare=False)

    @property
    def next_index(self) -> int:
        return int(self.proposal_index) + 1


def _policy_value(policy, name: str, default):
    if isinstance(policy, Mapping):
        return policy.get(name, default)
    return getattr(policy, name, default)


def _coerce_policy(policy) -> MetricProposalPolicy:
    if isinstance(policy, MetricProposalPolicy):
        return policy
    if policy is None:
        return MetricProposalPolicy()
    acq_seed = _policy_value(policy, "acq_seed", 0)
    proposal_seed = _policy_value(policy, "proposal_seed", 0)
    sample_shape = _policy_value(
        policy, "sample_shape", _policy_value(policy, "sampler_sample_shape",
                                              SAMPLER_SAMPLE_SHAPE))
    chunk_size = _policy_value(
        policy, "chunk_size", _policy_value(policy, "acq_chunk_size", POOL_CHUNK_SIZE))
    tol = _policy_value(policy, "near_duplicate_tol", NEAR_DUPLICATE_TOL)
    bounds_hash = _policy_value(policy, "bounds_hash", "") or ""
    try:
        return MetricProposalPolicy(
            acq_seed=int(acq_seed), proposal_seed=int(proposal_seed),
            sample_shape=int(sample_shape), chunk_size=int(chunk_size),
            near_duplicate_tol=float(tol), bounds_hash=str(bounds_hash))
    except (TypeError, ValueError):
        return MetricProposalPolicy()


def _history_value(history, name: str, default):
    if isinstance(history, Mapping):
        return history.get(name, default)
    return getattr(history, name, default)


def _coerce_history(history) -> MetricProposalHistory:
    if isinstance(history, MetricProposalHistory):
        return history
    if history is None:
        return MetricProposalHistory()
    try:
        return MetricProposalHistory(
            proposal_index=int(_history_value(history, "proposal_index", 0)),
            excluded_geometry_hashes=tuple(
                str(v) for v in (_history_value(history, "excluded_geometry_hashes", ()) or ())),
            excluded_design_hashes=tuple(
                str(v) for v in (_history_value(history, "excluded_design_hashes", ()) or ())),
            excluded_solve_identities=tuple(
                (str(a), str(b)) for a, b in (
                    _history_value(history, "excluded_solve_identities", ()) or ())),
            pending_identities=tuple(
                (str(a), str(b)) for a, b in (
                    _history_value(history, "pending_identities", ()) or ())),
            pending_vectors=tuple(_history_value(history, "pending_vectors", ()) or ()),
            excluded_vectors=tuple(_history_value(history, "excluded_vectors", ()) or ()),
        )
    except (TypeError, ValueError):
        return MetricProposalHistory()


def _vector_of(candidate):
    vector = getattr(candidate, "active_vector", None)
    if vector is None:
        return None
    arr = np.asarray(vector, dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(arr)):
        return None
    return arr


def _candidate_dict(candidate) -> dict:
    if hasattr(candidate, "as_dict"):
        try:
            return candidate.as_dict(include_vectors=True)
        except TypeError:
            return candidate.as_dict()
    return {
        "candidate_id": getattr(candidate, "candidate_id", None),
        "active_vector": getattr(candidate, "active_vector", None),
        "geometry_hash": getattr(candidate, "geometry_hash", None),
        "design_hash": getattr(candidate, "design_hash", None),
        "intended_solve_hash": getattr(candidate, "intended_solve_hash", None),
    }


def _unavailable(reason: str, detail: str | None, *, counts=None, policy=None,
                 history=None, versions=None, started=None, model_result=None,
                 candidate_pool=None, bounds_hash: str | None = None) -> MetricProposalResult:
    policy_obj = policy if isinstance(policy, MetricProposalPolicy) else MetricProposalPolicy()
    hist = history if isinstance(history, MetricProposalHistory) else MetricProposalHistory()
    resolved_bounds = (str(bounds_hash) if bounds_hash is not None
                       else _resolve_bounds_hash(policy_obj, candidate_pool, model_result))
    return MetricProposalResult(
        status=STATUS_UNAVAILABLE, reason=reason, detail=detail,
        candidate=None, candidate_id=None, geometry_hash=None, design_hash=None,
        intended_solve_hash=None, proposal_index=int(hist.proposal_index),
        next_proposal_index=int(hist.proposal_index),
        acquisition_score=None, predicted_j=None, component_means=(), component_sds=(),
        total_sd=None, model_hash=str(getattr(model_result, "model_hash", "") or ""),
        data_hash=str(getattr(model_result, "artifact_checksum", "") or ""),
        policy=METRIC_COMPOSITE_POLICY,
        bounds_hash=resolved_bounds,
        acq_seed=int(policy_obj.acq_seed), proposal_seed=int(policy_obj.proposal_seed),
        fit_s=getattr(model_result, "timing_s", None), acquisition_s=None,
        counts=dict(counts or {}),
        library_versions=(versions if versions is not None else library_versions()),
        timing_s=(None if started is None else time.perf_counter() - started))


def _resolve_bounds_hash(policy: MetricProposalPolicy, candidate_pool, model_result) -> str:
    if policy.bounds_hash:
        return str(policy.bounds_hash)
    for obj in (candidate_pool, model_result):
        value = getattr(obj, "bounds_hash", None)
        if value:
            return str(value)
    return ""


def _bounds_sources(policy: MetricProposalPolicy, candidate_pool, model_result) -> dict[str, str]:
    """Every policy/pool/model object that actually exposes a ``bounds_hash`` source."""
    sources: dict[str, str] = {}
    for name, obj in (("policy", policy), ("pool", candidate_pool), ("model", model_result)):
        if obj is None:
            continue
        if isinstance(obj, Mapping):
            if "bounds_hash" in obj:
                value = obj.get("bounds_hash")
                sources[name] = "" if value is None else str(value)
        elif hasattr(obj, "bounds_hash"):
            value = getattr(obj, "bounds_hash", None)
            sources[name] = "" if value is None else str(value)
    return sources


def _filter_legal(candidate_pool, history: MetricProposalHistory, model_result,
                  policy: MetricProposalPolicy):
    """Return ``(legal, reference_vectors, pending_matrix, counts)`` or raise ``ValueError``."""
    counts = {
        "input": len(getattr(candidate_pool, "candidates", ()) or ()),
        "excluded_bad_vector": 0,
        "excluded_out_of_bounds": 0,
        "excluded_known": 0,
        "excluded_pending": 0,
        "excluded_near_duplicate": 0,
        "excluded_near_pool_duplicate": 0,
        "legal": 0,
        "pending_only_dispatched_unresolved": True,
    }
    d = int(getattr(model_result, "d", 0) or 0)
    excluded_geometry = {str(h) for h in history.excluded_geometry_hashes}
    excluded_design = {str(h) for h in history.excluded_design_hashes}
    excluded_identities = {(str(a), str(b)) for a, b in history.excluded_solve_identities}
    pending_identities = {(str(a), str(b)) for a, b in history.pending_identities}

    reference: list[np.ndarray] = []
    train_X = getattr(model_result, "train_X", None)
    if train_X is not None:
        train_arr = np.asarray(train_X, dtype=np.float64)
        if train_arr.ndim == 2:
            reference.extend(np.asarray(row, dtype=np.float64) for row in train_arr)
    pending_vectors: list[np.ndarray] = []
    for vec in history.pending_vectors:
        arr = np.asarray(vec, dtype=np.float64).reshape(-1)
        if not np.all(np.isfinite(arr)) or (d and arr.size != d):
            raise ValueError("each pending vector must be finite and match the model dimension")
        pending_vectors.append(arr)
        reference.append(arr)
    for vec in history.excluded_vectors:
        arr = np.asarray(vec, dtype=np.float64).reshape(-1)
        if not np.all(np.isfinite(arr)) or (d and arr.size != d):
            raise ValueError("each excluded vector must be finite and match the model dimension")
        reference.append(arr)
    if len(history.pending_identities) != len(pending_vectors):
        raise ValueError("each dispatched unresolved identity requires a pending vector")
    if not d:
        d = int(reference[0].size) if reference else 0

    legal: list[tuple[Any, np.ndarray]] = []
    accepted_vectors: list[np.ndarray] = []
    for candidate in getattr(candidate_pool, "candidates", ()) or ():
        geometry = str(getattr(candidate, "geometry_hash", "") or "")
        design = str(getattr(candidate, "design_hash", "") or "")
        solve_hash = str(getattr(candidate, "intended_solve_hash", "") or "")
        identity = (geometry, solve_hash)
        if geometry in excluded_geometry or design in excluded_design \
                or identity in excluded_identities:
            counts["excluded_known"] += 1
            continue
        if identity in pending_identities:
            counts["excluded_pending"] += 1
            continue
        vector = _vector_of(candidate)
        if vector is None or (d and vector.size != d):
            counts["excluded_bad_vector"] += 1
            continue
        if np.any(vector < 0.0) or np.any(vector > 1.0):
            counts["excluded_out_of_bounds"] += 1
            continue
        if reference and is_near_duplicate(vector, reference, tol=policy.near_duplicate_tol):
            counts["excluded_near_duplicate"] += 1
            continue
        if accepted_vectors and is_near_duplicate(vector, accepted_vectors,
                                                  tol=policy.near_duplicate_tol):
            counts["excluded_near_pool_duplicate"] += 1
            continue
        accepted_vectors.append(vector)
        legal.append((candidate, vector))
    counts["legal"] = len(legal)
    pending_matrix = (np.vstack(pending_vectors) if pending_vectors else None)
    return legal, reference, pending_matrix, counts


def propose_metric_candidate(model_result, candidate_pool, *, policy=None, history=None,
                             require_identity: bool = False,
                             expected_bounds_hash: str | None = None
                             ) -> MetricProposalResult:
    """Choose one candidate with the composite qLogNEI acquisition.

    ``candidate_pool`` may be the standard B2 pool or a caller-restricted pool (for example a
    TuRBO local box); the engine never resamples.  Predictions in the result are model posterior
    summaries, not measured/solved acoustic results.

    ``require_identity=True`` additionally requires the proposal's box identity: every available
    policy/pool/model ``bounds_hash`` source must be non-empty and equal to
    ``expected_bounds_hash`` (recomputed by the caller from a live projection).  An ok result then
    can never carry ``bounds_hash=""``.  The default (``False``) preserves Pass 1 behaviour exactly.
    """
    started = time.perf_counter()
    policy_obj = _coerce_policy(policy)
    hist = _coerce_history(history)
    versions = library_versions()

    identity_bounds: str | None = None
    if require_identity:
        expected = "" if expected_bounds_hash is None else str(expected_bounds_hash).strip()
        sources = _bounds_sources(policy_obj, candidate_pool, model_result)
        identity = check_bounds_identity(expected_hash=expected, sources=sources,
                                         required=tuple(sources))
        if not identity.ok:
            return _unavailable(
                identity.reason or REASON_BOUNDS_MISSING,
                identity.detail or "a recomputed bounds identity is required for this proposal",
                policy=policy_obj, history=hist, versions=versions, started=started,
                model_result=model_result, candidate_pool=candidate_pool,
                bounds_hash=expected)
        identity_bounds = identity.expected

    if candidate_pool is None or getattr(candidate_pool, "status", None) != STATUS_OK \
            or not getattr(candidate_pool, "candidates", ()):
        return _unavailable(
            REASON_POOL_EXHAUSTED, "candidate pool has no novel legal candidate",
            policy=policy_obj, history=hist, versions=versions, started=started,
            model_result=model_result, candidate_pool=candidate_pool)

    try:
        legal, reference, pending_matrix, counts = _filter_legal(
            candidate_pool, hist, model_result, policy_obj)
    except (TypeError, ValueError) as exc:
        return _unavailable(
            REASON_INVALID_HISTORY, f"invalid proposal history: {exc}", policy=policy_obj,
            history=hist, versions=versions, started=started, model_result=model_result,
            candidate_pool=candidate_pool)
    if not legal:
        return _unavailable(
            REASON_POOL_EXHAUSTED,
            "every pooled candidate is already evaluated, pending, out of bounds, or a "
            "near-duplicate", counts=counts, policy=policy_obj, history=hist,
            versions=versions, started=started, model_result=model_result,
            candidate_pool=candidate_pool)

    model_ok = (model_result is not None
                and getattr(model_result, "status", None) == STATUS_OK
                and getattr(model_result, "model", None) is not None)
    if not model_ok:
        reason = (getattr(model_result, "reason", REASON_INSUFFICIENT_DATA)
                  if model_result is not None else REASON_INSUFFICIENT_DATA)
        detail = (getattr(model_result, "detail", None) or "no fitted metric model")
        return _unavailable(
            reason, f"{detail}; no candidate or prediction is fabricated", counts=counts,
            policy=policy_obj, history=hist, versions=versions, started=started,
            model_result=model_result, candidate_pool=candidate_pool)

    candidate_X = np.vstack([vector for _, vector in legal])
    acq = build_metric_acquisition(
        model_result, acq_seed=int(policy_obj.acq_seed),
        sample_shape=int(policy_obj.sample_shape),
        X_baseline=getattr(model_result, "train_X", None), X_pending=pending_matrix)
    if acq.status != STATUS_OK:
        reason = acq.reason or REASON_MODEL_UNAVAILABLE
        return _unavailable(
            reason, f"{acq.detail or 'composite acquisition construction failed'}; "
                    "no fallback and no fabricated prediction", counts=counts,
            policy=policy_obj, history=hist, versions=versions, started=started,
            model_result=model_result, candidate_pool=candidate_pool)

    scores = evaluate_metric_candidates(acq, candidate_X,
                                        chunk_size=int(policy_obj.chunk_size))
    if not scores.ok or scores.values is None:
        return _unavailable(
            scores.reason or REASON_MODEL_UNAVAILABLE,
            f"{scores.detail or 'composite acquisition evaluation failed'}; "
            "no fallback and no fabricated prediction", counts=counts, policy=policy_obj,
            history=hist, versions=versions, started=started, model_result=model_result,
            candidate_pool=candidate_pool)

    ids = [str(getattr(c, "candidate_id", "")) for c, _ in legal]
    chosen = stable_argmax(scores.values, ids)
    if chosen is None:
        return _unavailable(
            REASON_MODEL_UNAVAILABLE,
            "no finite composite acquisition value among legal candidates", counts=counts,
            policy=policy_obj, history=hist, versions=versions, started=started,
            model_result=model_result, candidate_pool=candidate_pool)

    candidate, vector = legal[chosen]
    prediction = predict_metric_components(model_result, vector.reshape(1, -1))
    if prediction.status != STATUS_OK or prediction.j_mean is None \
            or prediction.component_mean is None or prediction.component_sd is None \
            or prediction.j_sd is None:
        return _unavailable(
            prediction.reason or REASON_MODEL_UNAVAILABLE,
            f"{prediction.detail or 'posterior prediction failed'}; no prediction is fabricated",
            counts=counts, policy=policy_obj, history=hist, versions=versions,
            started=started, model_result=model_result, candidate_pool=candidate_pool)

    return MetricProposalResult(
        status=STATUS_OK, reason=REASON_OK, detail=PREDICTION_NOTE,
        selection_reason=SELECTION_ACQUISITION,
        candidate=_candidate_dict(candidate),
        candidate_id=getattr(candidate, "candidate_id", None),
        geometry_hash=getattr(candidate, "geometry_hash", None),
        design_hash=getattr(candidate, "design_hash", None),
        intended_solve_hash=getattr(candidate, "intended_solve_hash", None),
        proposal_index=int(hist.proposal_index),
        next_proposal_index=int(hist.next_index),
        acquisition_score=float(scores.values[chosen]),
        predicted_j=float(prediction.j_mean[0]),
        component_means=tuple(float(v) for v in np.asarray(prediction.component_mean).reshape(-1)),
        component_sds=tuple(float(v) for v in np.asarray(prediction.component_sd).reshape(-1)),
        total_sd=float(prediction.j_sd[0]),
        model_hash=str(getattr(model_result, "model_hash", "") or ""),
        data_hash=str(getattr(model_result, "artifact_checksum", "") or ""),
        policy=METRIC_COMPOSITE_POLICY,
        bounds_hash=(identity_bounds if identity_bounds is not None
                     else _resolve_bounds_hash(policy_obj, candidate_pool, model_result)),
        acq_seed=int(policy_obj.acq_seed), proposal_seed=int(policy_obj.proposal_seed),
        fit_s=getattr(model_result, "timing_s", None),
        acquisition_s=getattr(acq, "timing_s", None),
        counts={**counts, "acquisition_units": ACQUISITION_UNITS},
        library_versions=(getattr(model_result, "library_versions", None) or versions),
        timing_s=time.perf_counter() - started)


__all__ = [
    "PROPOSE_POLICY",
    "REASON_POOL_EXHAUSTED",
    "REASON_INVALID_HISTORY",
    "PREDICTION_NOTE",
    "SELECTION_ACQUISITION",
    "MetricProposalPolicy",
    "MetricProposalHistory",
    "propose_metric_candidate",
]
