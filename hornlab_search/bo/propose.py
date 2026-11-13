"""Deterministic scalar-pool v1 proposal policy (B3, protocol bo-study-v1.1).

Implements spec section 3.4 over the frozen B2 :class:`~.data.CandidatePool`:

* q=1 qLogNEI acquisition in chunks of 64, stable argmax (ties by geometry ID);
* every fourth **new proposal index** uses maximin exploration from the same legal pool;
  the cadence is driven by :class:`ProposalHistory.proposal_index`, so a resumed run cannot reset
  it;
* the legal pool removes already-evaluated identities, **only dispatched-unresolved** pending
  identities, and unit-coordinate near-duplicates (infinity norm ``<= 1e-6``);
* if no novel legal candidate remains, return ``pool_exhausted`` (the B2 pool builder already
  enforces at most two extra recorded Sobol seeds -- this adapter never resamples).

Failure is tagged, never fabricated: a model/acquisition/posterior failure returns a
``model_unavailable`` result with no zero predictions.  A deterministic maximin pick may be
attached as an explicitly labelled non-BO exploration fallback, but its prediction fields stay
``None``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .acquisition import (
    ACQUISITION_UNITS,
    POOL_CHUNK_SIZE,
    SAMPLER_SAMPLE_SHAPE,
    build_acquisition,
    evaluate_candidates,
    stable_argmax,
)
from .data import NEAR_DUPLICATE_TOL, is_near_duplicate
from .model import (
    REASON_CAPABILITY_MISSING,
    REASON_INSUFFICIENT_DATA,
    REASON_MODEL_UNAVAILABLE,
    REASON_NEEDS_INITIAL_DATA,
    REASON_OK,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    library_versions,
    predict_j,
)

PROPOSE_POLICY = "scalar_pool_v1"
EXPLORATION_EVERY = 4
REASON_POOL_EXHAUSTED = "pool_exhausted"

SELECTION_ACQUISITION = "acquisition"
SELECTION_EXPLORATION = "exploration"
SELECTION_EXPLORATION_FALLBACK = "exploration_fallback"


@dataclass(frozen=True)
class ProposalPolicy:
    """Frozen proposal cadence/batching.  ``exploration_every=4`` is the locked cadence."""

    exploration_every: int = EXPLORATION_EVERY
    acq_chunk_size: int = POOL_CHUNK_SIZE
    acq_seed: int = 0
    sampler_sample_shape: int = SAMPLER_SAMPLE_SHAPE
    near_duplicate_tol: float = NEAR_DUPLICATE_TOL

    @property
    def policy(self) -> str:
        return PROPOSE_POLICY

    def is_exploration(self, proposal_index: int) -> bool:
        """True for every fourth 0-based new proposal index (3, 7, 11, ...)."""
        every = max(1, int(self.exploration_every))
        return (int(proposal_index) + 1) % every == 0


@dataclass(frozen=True)
class ProposalHistory:
    """Durable proposal state.  ``pending_identities`` are **only dispatched-unresolved** jobs."""

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


@dataclass(frozen=True)
class ProposalResult:
    """Tagged proposal result; callers must not substitute zero predictions."""

    status: str
    reason: str
    detail: str | None = None
    selection_reason: str | None = None
    candidate: dict | None = None
    candidate_id: str | None = None
    geometry_hash: str | None = None
    design_hash: str | None = None
    intended_solve_hash: str | None = None
    proposal_index: int | None = None
    next_proposal_index: int | None = None
    predicted: dict | None = None
    acquisition: dict | None = None
    exploration: dict | None = None
    fallback: bool = False
    counts: dict = field(default_factory=dict)
    model_reason: str | None = None
    pool_status: str | None = None
    seeds_tried: tuple[int, ...] = ()
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
            "selection_reason": self.selection_reason,
            "candidate": self.candidate,
            "candidate_id": self.candidate_id,
            "geometry_hash": self.geometry_hash,
            "design_hash": self.design_hash,
            "intended_solve_hash": self.intended_solve_hash,
            "proposal_index": self.proposal_index,
            "next_proposal_index": self.next_proposal_index,
            "predicted": self.predicted,
            "acquisition": self.acquisition,
            "exploration": self.exploration,
            "fallback": bool(self.fallback),
            "counts": dict(self.counts),
            "model_reason": self.model_reason,
            "pool_status": self.pool_status,
            "seeds_tried": list(self.seeds_tried),
            "library_versions": dict(self.library_versions),
            "timing_s": self.timing_s,
        }


def _candidate_arrays(candidate):
    vector = getattr(candidate, "active_vector", None)
    if vector is None:
        return None
    arr = np.asarray(vector, dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(arr)):
        return None
    return arr


def _filter_legal(candidate_pool, history: ProposalHistory, model_result, policy: ProposalPolicy):
    """Return ``(legal_candidates, counts)`` after identity/pending/near-duplicate filters."""
    counts = {
        "input": len(getattr(candidate_pool, "candidates", ()) or ()),
        "excluded_known": 0,
        "excluded_pending": 0,
        "excluded_near_duplicate": 0,
        "excluded_near_pool_duplicate": 0,
        "excluded_bad_vector": 0,
        "legal": 0,
        "pending_only_dispatched_unresolved": True,
    }
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
    for vec in tuple(history.pending_vectors) + tuple(history.excluded_vectors):
        arr = np.asarray(vec, dtype=np.float64).reshape(-1)
        if np.all(np.isfinite(arr)):
            reference.append(arr)

    legal = []
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
        vector = _candidate_arrays(candidate)
        if vector is None:
            counts["excluded_bad_vector"] += 1
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
    return legal, counts


def _maximin_pick(legal, reference_vectors):
    """Farthest-point pick (L2) from the reference set; ties by geometry ID."""
    if not legal:
        return None
    if reference_vectors:
        ref = np.vstack([np.asarray(v, dtype=np.float64).reshape(1, -1)
                         for v in reference_vectors])
    else:
        ref = None
    best_idx = None
    best_dist = -np.inf
    for idx, (candidate, vector) in enumerate(legal):
        if ref is None:
            dist = float("inf")
        else:
            dist = float(np.min(np.linalg.norm(ref - vector.reshape(1, -1), axis=1)))
        cid = str(getattr(candidate, "geometry_hash", ""))
        if dist > best_dist + 1e-15:
            best_idx, best_dist = idx, dist
        elif dist == best_dist or abs(dist - best_dist) <= 1e-15:
            prior = str(getattr(legal[best_idx][0], "geometry_hash", ""))
            if cid < prior:
                best_idx, best_dist = idx, dist
    candidate, vector = legal[best_idx]
    return candidate, vector, float(best_dist)


def _candidate_dict(candidate) -> dict:
    if hasattr(candidate, "as_dict"):
        try:
            return candidate.as_dict(include_vectors=True)
        except TypeError:
            return candidate.as_dict()
    return {"candidate_id": getattr(candidate, "candidate_id", None)}


def _prediction_dict(prediction, index: int) -> dict | None:
    if prediction is None or prediction.status != STATUS_OK:
        return None
    return {
        "j_mean": float(prediction.j_mean[index]),
        "j_lower": float(prediction.j_lower[index]),
        "j_upper": float(prediction.j_upper[index]),
        "y_mean": float(prediction.y_mean[index]),
        "y_sd": float(prediction.y_sd[index]),
        "flags": list(prediction.flags),
        "nonphysical": bool(prediction.nonphysical),
        "interval_label": prediction.interval_label,
        "observation_noise": bool(prediction.observation_noise),
    }


def _build_result(*, status, reason, detail=None, selection_reason=None, candidate=None,
                  proposal_index=0, next_proposal_index=0, predicted=None, acquisition=None,
                  exploration=None, fallback=False, counts=None, model_reason=None,
                  pool_status=None, seeds_tried=(), started=None, versions=None):
    cand = candidate
    return ProposalResult(
        status=status, reason=reason, detail=detail, selection_reason=selection_reason,
        candidate=_candidate_dict(cand) if cand is not None else None,
        candidate_id=(None if cand is None else getattr(cand, "candidate_id", None)),
        geometry_hash=(None if cand is None else getattr(cand, "geometry_hash", None)),
        design_hash=(None if cand is None else getattr(cand, "design_hash", None)),
        intended_solve_hash=(None if cand is None else getattr(cand, "intended_solve_hash", None)),
        proposal_index=int(proposal_index), next_proposal_index=int(next_proposal_index),
        predicted=predicted, acquisition=acquisition, exploration=exploration,
        fallback=bool(fallback), counts=dict(counts or {}), model_reason=model_reason,
        pool_status=pool_status, seeds_tried=tuple(seeds_tried or ()),
        library_versions=(versions if versions is not None else library_versions()),
        timing_s=(None if started is None else time.perf_counter() - started),
    )


def _propose_one(model_result, candidate_pool, proposal_policy=None, history=None) -> ProposalResult:
    """Choose one candidate from the finite legal pool under the cadence-aware policy."""
    started = time.perf_counter()
    policy = proposal_policy if isinstance(proposal_policy, ProposalPolicy) else ProposalPolicy()
    hist = history if isinstance(history, ProposalHistory) else ProposalHistory()
    index = int(hist.proposal_index)
    next_index = index + 1
    versions = library_versions()
    pool_status = getattr(candidate_pool, "status", None)
    seeds_tried = tuple(getattr(candidate_pool, "seeds_tried", ()) or ())

    if candidate_pool is None or pool_status != "ok" \
            or not getattr(candidate_pool, "candidates", ()):
        return _build_result(
            status=STATUS_UNAVAILABLE, reason=REASON_POOL_EXHAUSTED,
            detail="candidate pool has no novel legal candidate",
            proposal_index=index, next_proposal_index=index, pool_status=pool_status,
            seeds_tried=seeds_tried, started=started, versions=versions)

    if len(hist.pending_vectors) != len(hist.pending_identities):
        return _build_result(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                             detail="each dispatched unresolved identity requires a pending vector",
                             proposal_index=index, next_proposal_index=index, started=started,
                             versions=versions)
    if hist.pending_vectors:
        try:
            pending = np.asarray(hist.pending_vectors, dtype=np.float64)
            expected_d = len(_candidate_arrays(candidate_pool.candidates[0]))
            if (pending.shape != (len(hist.pending_identities), expected_d)
                    or not np.all(np.isfinite(pending))):
                raise ValueError("pending vectors must be finite and match candidate dimension")
        except (TypeError, ValueError) as exc:
            return _build_result(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                 detail=str(exc), proposal_index=index, next_proposal_index=index,
                                 started=started, versions=versions)
    legal, counts = _filter_legal(candidate_pool, hist, model_result, policy)
    if not legal:
        return _build_result(
            status=STATUS_UNAVAILABLE, reason=REASON_POOL_EXHAUSTED,
            detail="every pooled candidate is already evaluated, pending, or a near-duplicate",
            proposal_index=index, next_proposal_index=index, counts=counts,
            pool_status=pool_status, seeds_tried=seeds_tried, started=started,
            versions=versions)

    reference: list[np.ndarray] = []
    if getattr(model_result, "train_X", None) is not None:
        train_arr = np.asarray(model_result.train_X, dtype=np.float64)
        if train_arr.ndim == 2:
            reference.extend(np.asarray(row, dtype=np.float64) for row in train_arr)
    for vec in tuple(hist.pending_vectors) + tuple(hist.excluded_vectors):
        arr = np.asarray(vec, dtype=np.float64).reshape(-1)
        if np.all(np.isfinite(arr)):
            reference.append(arr)

    model_ok = (model_result is not None
                and getattr(model_result, "status", None) == STATUS_OK
                and getattr(model_result, "model", None) is not None)
    if model_ok:
        model_reason = None
    elif model_result is None:
        model_reason = REASON_INSUFFICIENT_DATA
    elif getattr(model_result, "status", None) != STATUS_OK:
        model_reason = getattr(model_result, "reason", REASON_MODEL_UNAVAILABLE)
    else:
        # status says ok but the fitted model object is missing: unusable, never fabricate.
        model_reason = REASON_MODEL_UNAVAILABLE

    # ---- maximin exploration arm (also the labelled non-BO fallback) ----------------------
    if policy.is_exploration(index) or not model_ok:
        pick = _maximin_pick(legal, reference)
        assert pick is not None  # legal is non-empty here
        candidate, vector, distance = pick
        if not model_ok:
            return _build_result(
                status=STATUS_UNAVAILABLE, reason=model_reason or REASON_INSUFFICIENT_DATA,
                detail="model/acquisition unavailable; returning a labelled non-BO maximin "
                       "exploration fallback (no predictions are fabricated)",
                selection_reason=SELECTION_EXPLORATION_FALLBACK, candidate=candidate,
                proposal_index=index, next_proposal_index=next_index, predicted=None,
                exploration={"method": "maximin", "distance_l2": distance,
                             "reference_points": len(reference)},
                fallback=True, counts=counts, model_reason=model_reason,
                pool_status=pool_status, seeds_tried=seeds_tried, started=started,
                versions=versions)

        assert model_result is not None
        prediction = predict_j(model_result, vector.reshape(1, -1))
        return _build_result(
            status=STATUS_OK, reason=REASON_OK,
            selection_reason=SELECTION_EXPLORATION, candidate=candidate,
            proposal_index=index, next_proposal_index=next_index,
            predicted=_prediction_dict(prediction, 0),
            exploration={"method": "maximin", "distance_l2": distance,
                         "reference_points": len(reference)},
            counts=counts, model_reason=None, pool_status=pool_status,
            seeds_tried=seeds_tried, started=started, versions=versions)

    # ---- acquisition arm ------------------------------------------------------------------
    candidate_X = np.vstack([vector for _, vector in legal])
    acq = build_acquisition(model_result, acq_seed=int(policy.acq_seed),
                            sample_shape=int(policy.sampler_sample_shape),
                            X_pending=(np.asarray(hist.pending_vectors, dtype=np.float64)
                                       if hist.pending_vectors else None))
    if not acq.ok:
        pick = _maximin_pick(legal, reference)
        assert pick is not None
        candidate, _vector, distance = pick
        return _build_result(
            status=STATUS_UNAVAILABLE, reason=acq.reason or "model_unavailable",
            detail=(acq.detail or "acquisition construction failed") +
                   "; returned a labelled non-BO maximin fallback with no predictions",
            selection_reason=SELECTION_EXPLORATION_FALLBACK, candidate=candidate,
            proposal_index=index, next_proposal_index=next_index, predicted=None,
            exploration={"method": "maximin", "distance_l2": distance,
                         "reference_points": len(reference), "fallback_for": "acquisition"},
            fallback=True, counts=counts, model_reason=acq.reason,
            pool_status=pool_status, seeds_tried=seeds_tried, started=started,
            versions=versions)

    scores = evaluate_candidates(acq, candidate_X, chunk_size=int(policy.acq_chunk_size))
    if not scores.ok or scores.values is None:
        pick = _maximin_pick(legal, reference)
        assert pick is not None
        candidate, _vector, distance = pick
        failure_reason = (REASON_CAPABILITY_MISSING if scores.reason == REASON_CAPABILITY_MISSING
                          else REASON_MODEL_UNAVAILABLE)
        return _build_result(
            status=STATUS_UNAVAILABLE, reason=failure_reason,
            detail=(f"{scores.reason}: {scores.detail or 'acquisition evaluation failed'}") +
                   "; returned a labelled non-BO maximin fallback with no predictions",
            selection_reason=SELECTION_EXPLORATION_FALLBACK, candidate=candidate,
            proposal_index=index, next_proposal_index=next_index, predicted=None,
            exploration={"method": "maximin", "distance_l2": distance,
                         "reference_points": len(reference), "fallback_for": "acquisition"},
            fallback=True, counts=counts, model_reason=scores.reason,
            pool_status=pool_status, seeds_tried=seeds_tried, started=started,
            versions=versions)

    ids = [str(getattr(c, "geometry_hash", "")) for c, _ in legal]
    chosen = stable_argmax(scores.values, ids)
    if chosen is None:
        return _build_result(
            status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
            detail=(f"no finite acquisition value among legal candidates "
                    f"(acquisition reason={scores.reason!r})"),
            proposal_index=index, next_proposal_index=index, counts=counts,
            model_reason=scores.reason, pool_status=pool_status, seeds_tried=seeds_tried,
            started=started, versions=versions)
    candidate, vector = legal[chosen]
    assert model_result is not None
    prediction = predict_j(model_result, vector.reshape(1, -1))
    predicted = _prediction_dict(prediction, 0)
    if predicted is None:
        # A posterior failure after a successful acquisition is still model_unavailable.
        return _build_result(
            status=STATUS_UNAVAILABLE, reason=prediction.reason,
            detail=(prediction.detail or "posterior prediction failed") +
                   "; no predictions are fabricated",
            selection_reason=SELECTION_ACQUISITION, candidate=candidate,
            proposal_index=index, next_proposal_index=next_index, predicted=None,
            acquisition={"value": float(scores.values[chosen]),
                         "units": ACQUISITION_UNITS, "acq_seed": int(policy.acq_seed),
                         "chunk_size": int(policy.acq_chunk_size),
                         "chunks": int(scores.chunks),
                         "n_candidates": int(scores.n)},
            counts=counts, model_reason=prediction.reason, pool_status=pool_status,
            seeds_tried=seeds_tried, started=started, versions=versions)
    return _build_result(
        status=STATUS_OK, reason=REASON_OK, selection_reason=SELECTION_ACQUISITION,
        candidate=candidate, proposal_index=index, next_proposal_index=next_index,
        predicted=predicted,
        acquisition={"value": float(scores.values[chosen]), "units": ACQUISITION_UNITS,
                     "acq_seed": int(policy.acq_seed),
                     "chunk_size": int(policy.acq_chunk_size),
                     "chunks": int(scores.chunks), "n_candidates": int(scores.n),
                     "nonfinite_count": int(scores.nonfinite_count)},
        counts=counts, model_reason=None, pool_status=pool_status,
        seeds_tried=seeds_tried, started=started, versions=versions)



def validate_selected_candidate(candidate, candidate_pool, *, encoding, config, resolution_mm=30.0):
    """Recreate the selected design and verify pool identities before publication.

    This resolves one surface only, never creates a mesh or calls a solver. The caller
    must pass the same resolved config, encoding, and sampling resolution as the pool.
    """
    from .data import (materialize_geometry, intended_solve_identity, _geometry_hash,
                       _surface_descriptors, _brief_envelope, _envelope_ok,
                       _expected_throat_radius, _throat_ok, _jsonable_params)
    from hornlab_search.design import families
    if encoding is None or config is None:
        raise ValueError("resolved encoding and config required to validate proposal")
    active = np.asarray(candidate.active_vector, dtype=float)
    if active.ndim != 1 or not np.all(np.isfinite(active)) or np.any(active < 0) or np.any(active > 1):
        raise ValueError("invalid selected active vector")
    full = encoding.to_full(active)
    if not np.array_equal(full, np.asarray(candidate.full_vector, dtype=float)):
        raise ValueError("selected full vector disagrees with projection")
    design = encoding.space.denormalize(full)
    families.validate(design)
    if design.hash() != candidate.design_hash or _jsonable_params(design.params) != candidate.params:
        raise ValueError("selected design or parameters disagree with pool")
    solve_hash = intended_solve_identity(config)
    if solve_hash != candidate.intended_solve_hash or solve_hash != candidate_pool.intended_solve_hash:
        raise ValueError("intended solve identity disagrees with pool")
    mat = materialize_geometry(design, config, resolution_mm=resolution_mm)
    if _geometry_hash(mat["inner_points"], mat["formula"]) != candidate.geometry_hash:
        raise ValueError("materialized geometry identity disagrees with pool")
    desc = _surface_descriptors(mat["inner_points"])
    if not _envelope_ok(desc, _brief_envelope(config)) or not _throat_ok(
            desc["throat_radius_mm"], _expected_throat_radius(design.params)):
        raise ValueError("selected geometry fails cheap checks")


def propose_one(model_result, candidate_pool, proposal_policy=None, history=None, *,
                encoding=None, config=None, resolution_mm=30.0) -> ProposalResult:
    """Select and revalidate one candidate before exposing it in a proposal."""
    result = _propose_one(model_result, candidate_pool, proposal_policy, history)
    if result.candidate_id is None:
        return result
    try:
        candidate = next(c for c in candidate_pool.candidates if c.candidate_id == result.candidate_id)
        validate_selected_candidate(candidate, candidate_pool, encoding=encoding, config=config,
                                    resolution_mm=resolution_mm)
    except Exception as exc:  # refusal preserves history and does not publish stale geometry
        return _build_result(status=STATUS_UNAVAILABLE, reason="capability_missing",
                             detail=f"proposal validation failed: {type(exc).__name__}: {exc}",
                             proposal_index=result.proposal_index,
                             next_proposal_index=result.proposal_index, counts=result.counts,
                             pool_status=result.pool_status, seeds_tried=result.seeds_tried,
                             versions=result.library_versions)
    return result


def propose_by_policy(*args, **kwargs):
    """Delegate to the frozen multi-policy dispatcher (B7).

    Imported lazily so the scalar module keeps its existing import graph and an absent optional
    engine never breaks importing :mod:`hornlab_search.bo`.
    """
    from .policy import fit_and_propose
    return fit_and_propose(*args, **kwargs)


__all__ = [
    "PROPOSE_POLICY",
    "EXPLORATION_EVERY",
    "REASON_POOL_EXHAUSTED",
    "SELECTION_ACQUISITION",
    "SELECTION_EXPLORATION",
    "SELECTION_EXPLORATION_FALLBACK",
    "ProposalPolicy",
    "ProposalHistory",
    "ProposalResult",
    "propose_one",
    "propose_by_policy",
]

