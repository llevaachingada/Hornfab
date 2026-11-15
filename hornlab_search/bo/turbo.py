"""Declared HornLab trust-region proposal policy ``turbo_pool_v1`` (spec 3.6).

The policy reuses the locked scalar engine unchanged -- the same :func:`~.model.fit_model`
GP (SingleTaskGP, Matern-5/2 ARD, Standardize, fixed tiny noise) on the same training set and
refits, and the same q=1 qLogNEI (128 Sobol MC samples, chunks of 64, stable argmax by
geometry ID) -- but scores only candidates **inside a local box**:

* box weights ``w_j = ell_j / geometric_mean(ell)`` from the fitted GP lengthscales and
  ``box = clip(center +/- L*w/2, 0, 1)`` (:func:`~.extensions.trust_box`);
* candidates are (1) members of the frozen global Sobol pool that lie inside the box plus
  (2) a fresh local scrambled-Sobol set of :data:`LOCAL_SOBOL_N` points inside the box whose
  seed is derived deterministically from the study seed and proposal index.  Local points go
  through the same cheap checks the pool builder uses (schema/materialize/envelope/throat;
  no mesh, no BEM) and the same legal-pool filter as scalar (``propose._filter_legal``);
* the state (center, L, counters, lengthscales, iteration, best J) is updated after every
  completed screen observation with :func:`~.extensions.update_trust_region`: a success is an
  improvement of more than ``1e-3*max(|J_best|,1e-8)``; three successes double L (max 1.6);
  ``max(4, d)`` consecutive non-improvements (eligible non-improvements **and** cheap geometry
  refusals) halve it.  Infrastructure/unknown failures do not touch the state.
* Shrinking below ``0.5**7`` is terminal (:data:`REASON_TRUST_REGION_COLLAPSED`).  There is
  no silent restart, no physical-bound widening and no extra replicate.

There is deliberately **no every-4th maximin exploration cadence**: the trust region itself
manages exploration (it grows on success and shrinks on stagnation).  This is the declared
HornLab trust-region variant, not a byte-identical implementation of every TuRBO paper detail.

Nothing here imports torch/botorch at import time.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace

import numpy as np

from .extensions import TrustRegion, trust_box, update_trust_region

TURBO_POLICY = "turbo_pool_v1"
L_INIT = 0.8
L_MIN = 0.5 ** 7
L_MAX = 1.6
LOCAL_SOBOL_N = 512
MAX_ATTEMPTS_PER_INDEX = 3
SUCCESS_TOL = 1e-3
BOX_TOL = 1e-12

STATUS_ACTIVE = "active"
STATUS_COLLAPSED = "collapsed"

REASON_TRUST_REGION_COLLAPSED = "trust_region_collapsed"
REASON_TRUST_REGION_NO_LEGAL = "trust_region_no_legal_candidate"
REASON_TRUST_REGION_INVALID = "trust_region_state_invalid"

OUTCOME_MEASURED = "measured"
OUTCOME_REFUSAL = "geometry_refusal"

SELECTION_TRUST_REGION = "trust_region_acquisition"


@dataclass(frozen=True)
class TurboState:
    """Durable, JSON-serialisable trust-region state."""

    center: tuple[float, ...]
    best_j: float
    length: float = L_INIT
    success_counter: int = 0
    failure_counter: int = 0
    iteration: int = 0
    lengthscales: tuple[float, ...] | None = None
    status: str = STATUS_ACTIVE
    terminal_reason: str | None = None
    #: solve IDs whose outcome already updated this state (resume replays the rest exactly once).
    applied: tuple[str, ...] = ()

    @property
    def active(self) -> bool:
        return self.status == STATUS_ACTIVE

    def to_dict(self) -> dict:
        return {
            "policy": TURBO_POLICY,
            "center": [float(v) for v in self.center],
            "best_j": float(self.best_j),
            "length": float(self.length),
            "length_bounds": {"init": L_INIT, "min": L_MIN, "max": L_MAX},
            "success_counter": int(self.success_counter),
            "failure_counter": int(self.failure_counter),
            "iteration": int(self.iteration),
            "lengthscales": (None if self.lengthscales is None
                             else [float(v) for v in self.lengthscales]),
            "status": self.status,
            "terminal_reason": self.terminal_reason,
            "applied": list(self.applied),
        }

    @classmethod
    def from_dict(cls, payload) -> "TurboState":
        if not isinstance(payload, dict) or payload.get("policy") != TURBO_POLICY:
            raise ValueError("persisted trust-region state is missing or names another policy")
        center = tuple(float(v) for v in payload["center"])
        best = float(payload["best_j"])
        length = float(payload["length"])
        ls = payload.get("lengthscales")
        state = cls(center=center, best_j=best, length=length,
                    success_counter=int(payload["success_counter"]),
                    failure_counter=int(payload["failure_counter"]),
                    iteration=int(payload["iteration"]),
                    lengthscales=None if ls is None else tuple(float(v) for v in ls),
                    status=str(payload["status"]),
                    terminal_reason=payload.get("terminal_reason"),
                    applied=tuple(str(v) for v in payload.get("applied") or ()))
        _validate(state)
        return state


def _validate(state: TurboState) -> None:
    c = np.asarray(state.center, dtype=float)
    if (c.ndim != 1 or c.size == 0 or not np.all(np.isfinite(c)) or np.any(c < 0) or np.any(c > 1)
            or not math.isfinite(state.best_j) or not math.isfinite(state.length)
            or state.length <= 0 or state.length > L_MAX + 1e-12
            or state.success_counter < 0 or state.failure_counter < 0 or state.iteration < 0
            or state.status not in (STATUS_ACTIVE, STATUS_COLLAPSED)):
        raise ValueError("invalid trust-region state")
    if state.lengthscales is not None and len(state.lengthscales) != c.size:
        raise ValueError("trust-region lengthscales do not match the centre dimension")


def initial_state(training_set) -> TurboState:
    """Centre at the best measured eligible training design (ties by observation ID)."""
    X = np.asarray(getattr(training_set, "X"), dtype=float)
    J = np.asarray(getattr(training_set, "J"), dtype=float).reshape(-1)
    ids = [str(i) for i in (getattr(training_set, "ids", ()) or range(len(J)))]
    if X.ndim != 2 or len(X) == 0 or len(J) != len(X) or len(ids) != len(X):
        raise ValueError("a non-empty training set is required to centre the trust region")
    finite = [i for i in range(len(J)) if math.isfinite(J[i]) and np.all(np.isfinite(X[i]))]
    if not finite:
        raise ValueError("no finite measured training design")
    best = min(finite, key=lambda i: (float(J[i]), ids[i]))
    state = TurboState(center=tuple(float(v) for v in X[best]), best_j=float(J[best]))
    _validate(state)
    return state


def _as_region(state: TurboState) -> TrustRegion:
    return TrustRegion(center=tuple(state.center), best_j=float(state.best_j),
                       length=float(state.length), successes=int(state.success_counter),
                       failures=int(state.failure_counter), iteration=int(state.iteration))


def update_state(state: TurboState, *, outcome: str, candidate=None, J=None,
                 solve_id: str | None = None) -> TurboState:
    """Apply one completed screen outcome.

    ``outcome`` is ``measured`` (eligible, finite J) or ``geometry_refusal``.  Any other
    outcome (infrastructure, metric, unknown) returns the state **unchanged**.  A solve ID
    already applied is ignored, so resume replay is idempotent.
    """
    if outcome not in (OUTCOME_MEASURED, OUTCOME_REFUSAL):
        return state
    if solve_id is not None and str(solve_id) in state.applied:
        return state
    if not state.active:
        return state
    region = update_trust_region(_as_region(state), outcome=outcome, candidate=candidate, J=J)
    collapsed = region.status != "active" or region.length < L_MIN
    applied = state.applied + ((str(solve_id),) if solve_id is not None else ())
    return replace(state, center=tuple(float(v) for v in region.center),
                   best_j=float(region.best_j), length=float(region.length),
                   success_counter=int(region.successes), failure_counter=int(region.failures),
                   iteration=int(region.iteration),
                   status=STATUS_COLLAPSED if collapsed else STATUS_ACTIVE,
                   terminal_reason=REASON_TRUST_REGION_COLLAPSED if collapsed else None,
                   applied=applied)


def box_bounds(state: TurboState, lengthscales):
    lo, hi = trust_box(_as_region(state), lengthscales)
    return np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)


def local_seed(study_seed: int, proposal_index: int, attempt: int) -> int:
    text = f"{TURBO_POLICY}:{int(study_seed)}:{int(proposal_index)}:{int(attempt)}"
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def local_candidates(encoding, config, lo, hi, *, seed: int, n: int = LOCAL_SOBOL_N,
                     resolution_mm: float = 30.0, tag: str = "turbo"):
    """Scrambled Sobol points inside ``[lo, hi]`` passed through the pool builder's cheap checks.

    The exact same primitives and order as :func:`~.data.build_candidate_pool` are used
    (decode -> canonical design -> schema validate -> materialize -> envelope -> throat ->
    geometry identity).  No mesh is built and no solver is called.
    """
    from hornlab_search.design import families

    from .data import (POOL_STATUS_NOTE, NEAR_DUPLICATE_TOL, PoolCandidate,
                       _empty_counts, geometry_checks, materialized_geometry_hash,
                       _jsonable_params, _sobol_unit,
                       canonical_design, intended_solve_identity, is_near_duplicate,
                       materialize_geometry)

    space = encoding.space
    d = int(encoding.d)
    lo = np.asarray(lo, dtype=float).reshape(-1)
    hi = np.asarray(hi, dtype=float).reshape(-1)
    if lo.shape != (d,) or hi.shape != (d,) or np.any(hi < lo):
        raise ValueError("trust-region box does not match the active dimension")
    unit, method = _sobol_unit(d, int(n), int(seed))
    points = np.clip(lo + (hi - lo) * unit, 0.0, 1.0)
    solve_hash = intended_solve_identity(config)
    counts = _empty_counts()
    counts["generated"] = int(points.shape[0])
    accepted, vectors, seen = [], [], set()
    for i in range(points.shape[0]):
        active = np.asarray(points[i], dtype=float)
        try:
            full = encoding.to_full(active)
            design = canonical_design(space.denormalize(full), config, space=space)
        except Exception:  # noqa: BLE001 - a bad decoded point is a rejected candidate
            counts["schema_rejected"] += 1
            continue
        params = getattr(design, "params", None)
        if isinstance(params, dict) and params.get("_generator_error"):
            counts["schema_rejected"] += 1
            continue
        try:
            families.validate(design)
        except Exception:  # noqa: BLE001
            counts["schema_rejected"] += 1
            continue
        try:
            mat = materialize_geometry(design, config, resolution_mm=resolution_mm)
        except Exception:  # noqa: BLE001
            counts["geometry_rejected"] += 1
            continue
        desc, envelope_ok, throat_ok = geometry_checks(mat, config, params)
        if not envelope_ok:
            counts["envelope_rejected"] += 1
            continue
        if not throat_ok:
            counts["throat_rejected"] += 1
            continue
        ghash = materialized_geometry_hash(mat)
        if (ghash, solve_hash) in seen:
            counts["geometry_duplicate"] += 1
            continue
        if is_near_duplicate(active, vectors, NEAR_DUPLICATE_TOL):
            counts["near_duplicate"] += 1
            continue
        seen.add((ghash, solve_hash))
        vectors.append(active.copy())
        accepted.append(PoolCandidate(
            candidate_id=f"{tag}-{int(seed)}-{i:05d}-{ghash[:8]}", pool_index=i, seed=int(seed),
            active_vector=active.copy(), full_vector=np.asarray(full, dtype=float).copy(),
            design_hash=design.hash(), geometry_hash=ghash, intended_solve_hash=solve_hash,
            params=_jsonable_params(params), descriptors=desc,
            checks={"schema": "passed", "envelope": "passed", "throat": "passed",
                    "materialized": True, "mesh_built": False, "bem_called": False},
            status=POOL_STATUS_NOTE))
        counts["unique"] += 1
        counts["novel"] += 1
    return tuple(accepted), {"method": method, "seed": int(seed), "counts": counts}


def _in_box(vector, lo, hi) -> bool:
    v = np.asarray(vector, dtype=float).reshape(-1)
    return bool(v.shape == lo.shape and np.all(v >= lo - BOX_TOL) and np.all(v <= hi + BOX_TOL))


def propose_turbo(fitted, pool, history, state: TurboState, *, encoding, config, seed: int = 0,
                  resolution_mm: float = 30.0, local_n: int = LOCAL_SOBOL_N,
                  local_fn=None):
    """Select one trust-region candidate.  Returns ``(ProposalResult, record)``.

    ``record`` is the durable trust-region record (state before/after, box, attempts); the
    caller persists ``record['state_after']``.  ``local_fn`` is a test seam replacing
    :func:`local_candidates` (same signature).
    """
    import time

    from .acquisition import (ACQUISITION_UNITS, POOL_CHUNK_SIZE, SAMPLER_SAMPLE_SHAPE,
                              build_acquisition, evaluate_candidates, stable_argmax)
    from .data import CandidatePool, intended_solve_identity
    from .model import REASON_MODEL_UNAVAILABLE, REASON_OK, STATUS_OK, STATUS_UNAVAILABLE, predict_j
    from .propose import (ProposalHistory, ProposalPolicy, _build_result, _filter_legal,
                          _prediction_dict, validate_selected_candidate)

    started = time.perf_counter()
    hist = history if isinstance(history, ProposalHistory) else ProposalHistory()
    index = int(hist.proposal_index)
    before = state.to_dict()
    record = {"policy": TURBO_POLICY, "proposal_index": index, "state_before": before,
              "attempts": [], "exploration_cadence": "none: the trust region manages exploration",
              "local_sobol_n": int(local_n)}

    def finish(result, current):
        record["state_after"] = current.to_dict()
        return result, record

    def terminal(reason, detail, current, counts=None):
        from .policy import STATUS_POOL_EXHAUSTED
        return finish(_build_result(status=STATUS_POOL_EXHAUSTED, reason=reason, detail=detail,
                                    proposal_index=index, next_proposal_index=index,
                                    counts=counts, started=started), current)

    if not state.active:
        return terminal(state.terminal_reason or REASON_TRUST_REGION_COLLAPSED,
                        "trust region already collapsed below the minimum length; no restart",
                        state)
    if fitted is None or getattr(fitted, "status", None) != STATUS_OK:
        return finish(_build_result(status=STATUS_UNAVAILABLE,
                                    reason=getattr(fitted, "reason", None) or REASON_MODEL_UNAVAILABLE,
                                    detail="trust-region policy requires the fitted scalar GP",
                                    proposal_index=index, next_proposal_index=index,
                                    started=started), state)
    ls = (getattr(fitted, "hyperparameters", {}) or {}).get("lengthscales")
    try:
        ls = np.asarray(ls, dtype=float).reshape(-1)
        if ls.shape != (len(state.center),) or not np.all(np.isfinite(ls)) or np.any(ls <= 0):
            raise ValueError("fitted lengthscales unavailable or mismatched")
    except (TypeError, ValueError) as exc:
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                    detail=f"trust-region box needs ARD lengthscales: {exc}",
                                    proposal_index=index, next_proposal_index=index,
                                    started=started), state)
    if len(hist.pending_vectors) != len(hist.pending_identities):
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                    detail="each dispatched unresolved identity requires a pending vector",
                                    proposal_index=index, next_proposal_index=index,
                                    started=started), state)
    state = replace(state, lengthscales=tuple(float(v) for v in ls))
    solve_hash = getattr(pool, "intended_solve_hash", None) or intended_solve_identity(config)
    generator = local_fn or local_candidates
    pool_members = tuple(getattr(pool, "candidates", ()) or ()) \
        if getattr(pool, "status", None) == "ok" else ()
    legal, counts, combined, lo, hi = [], {}, None, None, None
    for attempt in range(MAX_ATTEMPTS_PER_INDEX):
        lo, hi = box_bounds(state, ls)
        inside = tuple(c for c in pool_members if _in_box(c.active_vector, lo, hi))
        lseed = local_seed(seed, index, attempt)
        local, local_report = generator(encoding, config, lo, hi, seed=lseed, n=int(local_n),
                                        resolution_mm=resolution_mm)
        combined = CandidatePool(
            status="ok", requested=len(inside) + int(local_n), seed=lseed,
            seeds_tried=(lseed,), candidates=inside + tuple(local), counts={},
            seed_reports=(), intended_solve_hash=solve_hash,
            note="trust-region candidates: frozen pool members inside the box + local Sobol")
        legal, counts = _filter_legal(combined, hist, fitted, ProposalPolicy())
        record["attempts"].append({
            "attempt": attempt, "length": float(state.length),
            "box": {"lo": lo.tolist(), "hi": hi.tolist()}, "pool_inside": len(inside),
            "local_seed": int(lseed), "local": dict(local_report.get("counts") or {}),
            "legal": len(legal)})
        if legal:
            break
        # No legal candidate in the box counts as a non-improvement (shrink path).
        state = update_state(state, outcome=OUTCOME_REFUSAL)
        if not state.active:
            return terminal(REASON_TRUST_REGION_COLLAPSED,
                            "no legal candidate in the box and the trust region collapsed",
                            state, counts)
    if not legal:
        state = replace(state, status=STATUS_COLLAPSED, terminal_reason=REASON_TRUST_REGION_NO_LEGAL)
        return terminal(REASON_TRUST_REGION_NO_LEGAL,
                        f"no legal trust-region candidate after {MAX_ATTEMPTS_PER_INDEX} attempts",
                        state, counts)
    record["box"] = {"lo": lo.tolist(), "hi": hi.tolist(),
                     "weights": (ls / np.exp(np.log(ls).mean())).tolist()}

    candidate_X = np.vstack([vector for _, vector in legal])
    acq = build_acquisition(fitted, acq_seed=0, sample_shape=SAMPLER_SAMPLE_SHAPE,
                            X_pending=(np.asarray(hist.pending_vectors, dtype=np.float64)
                                       if hist.pending_vectors else None))
    if not acq.ok:
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason=acq.reason or REASON_MODEL_UNAVAILABLE,
                                    detail=acq.detail or "acquisition construction failed",
                                    proposal_index=index, next_proposal_index=index,
                                    counts=counts, started=started), state)
    scores = evaluate_candidates(acq, candidate_X, chunk_size=POOL_CHUNK_SIZE)
    if not scores.ok or scores.values is None:
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                    detail=f"{scores.reason}: {scores.detail or 'acquisition failed'}",
                                    proposal_index=index, next_proposal_index=index,
                                    counts=counts, started=started), state)
    ids = [str(getattr(c, "geometry_hash", "")) for c, _ in legal]
    chosen = stable_argmax(scores.values, ids)
    if chosen is None:
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                    detail="no finite acquisition value inside the trust region",
                                    proposal_index=index, next_proposal_index=index,
                                    counts=counts, started=started), state)
    candidate, vector = legal[chosen]
    try:
        validate_selected_candidate(candidate, combined, encoding=encoding, config=config,
                                    resolution_mm=resolution_mm)
    except Exception as exc:  # noqa: BLE001 - a refused geometry is never published
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason="capability_missing",
                                    detail=f"proposal validation failed: {type(exc).__name__}: {exc}",
                                    proposal_index=index, next_proposal_index=index,
                                    counts=counts, started=started), state)
    prediction = predict_j(fitted, vector.reshape(1, -1))
    predicted = _prediction_dict(prediction, 0)
    if predicted is None:
        return finish(_build_result(status=STATUS_UNAVAILABLE, reason=prediction.reason,
                                    detail="posterior prediction failed; no predictions are fabricated",
                                    proposal_index=index, next_proposal_index=index,
                                    counts=counts, started=started), state)
    counts = dict(counts)
    counts["trust_region_source"] = ("pool" if str(candidate.candidate_id).startswith("pool-")
                                     else "local")
    return finish(_build_result(
        status=STATUS_OK, reason=REASON_OK, selection_reason=SELECTION_TRUST_REGION,
        candidate=candidate, proposal_index=index, next_proposal_index=index + 1,
        predicted=predicted,
        acquisition={"value": float(scores.values[chosen]), "units": ACQUISITION_UNITS,
                     "acq_seed": 0, "chunk_size": int(POOL_CHUNK_SIZE),
                     "chunks": int(scores.chunks), "n_candidates": int(scores.n),
                     "nonfinite_count": int(scores.nonfinite_count)},
        counts=counts, started=started), state)


__all__ = [
    "TURBO_POLICY", "L_INIT", "L_MIN", "L_MAX", "LOCAL_SOBOL_N", "MAX_ATTEMPTS_PER_INDEX",
    "REASON_TRUST_REGION_COLLAPSED", "REASON_TRUST_REGION_NO_LEGAL", "TurboState",
    "initial_state", "update_state", "box_bounds", "local_seed", "local_candidates",
    "propose_turbo",
]
