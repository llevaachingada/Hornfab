"""Frozen unified proposal-policy dispatcher (B7, protocol bo-study-v1.1).

The M3 runner and GUI consume exactly one selector surface:

``PROPOSAL_POLICIES = ("scalar", "pareto", "cma_seed", "exploration")``

* ``scalar``      -- scalar Bayesian proposal (locked scalar-pool v1 engine);
* ``pareto``      -- coverage/ripple trade-off frontier (locked Pareto engine);
* ``cma_seed``    -- an explicit, caller-supplied CMA archive seed pack; **no score math**;
* ``exploration`` -- fixed non-BO maximin exploration from the same legal pool.

Nothing here invents a candidate, a prediction or a score.  Failed fits and missing
capabilities are tagged and propagated exactly; a ``proposal`` may be attached to a tagged
non-``ok`` scalar result only when the underlying engine already labelled it as an explicit
non-BO exploration fallback, and then ``predicted``/``acquisition`` stay ``None``.

Optional BoTorch/GPyTorch/Torch imports are lazy.  Importing :mod:`hornlab_search.bo` (and this
module) never imports torch or botorch; capability checks use ``importlib`` metadata only.
"""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import model as _model
from . import pareto as _pareto
from . import propose as _propose
from .data import N_MIN_FLOOR, n_min_for
from .model import (
    REASON_CAPABILITY_MISSING,
    REASON_OK,
    STATUS_OK,
    STATUS_UNAVAILABLE,
)
from .propose import ProposalHistory, ProposalPolicy

POLICY_SCALAR = "scalar"
POLICY_PARETO = "pareto"
POLICY_CMA_SEED = "cma_seed"
POLICY_EXPLORATION = "exploration"

#: Frozen order for GUI/runner menus.
PROPOSAL_POLICIES = (POLICY_SCALAR, POLICY_PARETO, POLICY_CMA_SEED, POLICY_EXPLORATION)

#: User-facing meanings.  Acquisition values and seed picks are technical rankings, not
#: acoustic quality and not a claim about a horn.
PROPOSAL_POLICY_LABELS = {
    POLICY_SCALAR: "scalar Bayesian",
    POLICY_PARETO: "coverage/ripple trade-offs",
    POLICY_CMA_SEED: "CMA archive seed pack",
    POLICY_EXPLORATION: "fixed exploration",
}

STATUS_CAPABILITY_MISSING = "capability_missing"
STATUS_POOL_EXHAUSTED = "pool_exhausted"

#: Engine-dependent policies.  ``cma_seed``/``exploration`` are explicitly non-BO.
ENGINE_POLICIES = frozenset({POLICY_SCALAR, POLICY_PARETO})

REASON_UNSUPPORTED_POLICY = "unsupported_policy"
REASON_TRAINING_SET_REQUIRED = "training_set_required"
REASON_INSUFFICIENT_TRAINING_DATA = "insufficient_training_data"
REASON_VALIDATED_COHORT_REQUIRED = "validated_cohort_required"
REASON_METRIC_BINDINGS_REQUIRED = "metric_observation_bindings_required"
REASON_METRIC_BINDING_MISMATCH = "metric_observation_binding_mismatch"
REASON_METRIC_POLICY_MISSING = "metric_policy_identity_missing"
REASON_METRIC_INCOMPLETE = "metric_observation_incomplete_or_incompatible"
REASON_LEGAL_POOL_REQUIRED = "legal_pool_required"
REASON_POOL_EXHAUSTED = "pool_exhausted"
REASON_SEEDS_REQUIRED = "explicit_seed_candidates_required"
REASON_DUPLICATE_SEED = "duplicate_seed_identity"
REASON_INVALID_SEED = "invalid_seed_candidate"
REASON_NO_ELIGIBLE_SEED = "no_eligible_seed"
REASON_VALIDATION_FAILED = "proposal_validation_failed"


# --------------------------------------------------------------------------- outcome


@dataclass(frozen=True)
class ProposalOutcome:
    """Tagged result of :func:`fit_and_propose`.

    ``status`` is one of ``ok`` / ``unavailable`` / ``capability_missing`` /
    ``pool_exhausted``.  On every non-``ok`` status ``predicted`` and (except for a published,
    explicitly labelled exploration fallback) ``acquisition`` are ``None``.  No zero J or fake
    probability is ever substituted.
    """

    status: str
    reason: str
    policy: str
    selection_reason: str | None = None
    proposal: dict | None = None
    predicted: dict | None = None
    acquisition: dict | None = None
    fallback: bool = False
    verification_mode: str = "scalar"
    library_versions: dict = field(default_factory=dict)
    detail: str | None = None
    counts: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "policy": self.policy,
            "selection_reason": self.selection_reason,
            "proposal": self.proposal,
            "predicted": self.predicted,
            "acquisition": self.acquisition,
            "fallback": bool(self.fallback),
            "verification_mode": self.verification_mode,
            "library_versions": dict(self.library_versions),
            "detail": self.detail,
            "counts": dict(self.counts),
        }


def verification_mode(policy: str) -> str:
    """Return the frozen verification mode for a policy name.

    Scalar and both non-BO arms use the scalar verification selection; only ``pareto`` changes
    the fixed finalist selection rule.
    """
    if policy == POLICY_PARETO:
        return "pareto"
    if policy in (POLICY_SCALAR, POLICY_CMA_SEED, POLICY_EXPLORATION):
        return "scalar"
    raise ValueError(f"unknown proposal policy {policy!r}")


# --------------------------------------------------------------------------- capability


def _engine_versions() -> dict:
    """Package versions without importing torch/botorch (importlib metadata only)."""
    out: dict[str, Any] = {"engine": "botorch"}
    for key in ("torch", "botorch", "gpytorch", "linear_operator"):
        try:
            out[key] = importlib.metadata.version(key)
        except Exception:  # noqa: BLE001 - absent distribution is an honest marker
            out[key] = None
    out["available"] = all(out.get(k) is not None for k in ("torch", "botorch", "gpytorch"))
    return out


def _engine_available() -> bool:
    """True when the optional engine is importable; never imports it here."""
    return all(importlib.util.find_spec(name) is not None
               for name in ("torch", "botorch", "gpytorch"))


def _data(status: str, reason: str, detail: str | None = None, **extra) -> dict:
    out = {"status": status, "reason": reason, "detail": detail}
    out.update(extra)
    return out


def _scalar_data_status(training_set) -> dict:
    if training_set is None:
        return _data(STATUS_UNAVAILABLE, REASON_TRAINING_SET_REQUIRED,
                     "a TrainingSet produced by bo.data is required")
    status = getattr(training_set, "status", None)
    if status != STATUS_OK:
        return _data(STATUS_UNAVAILABLE, REASON_INSUFFICIENT_TRAINING_DATA,
                     f"training set status is {status!r}")
    d = getattr(training_set, "d", None)
    X = getattr(training_set, "X", None)
    n = getattr(training_set, "n", None)
    n_actual = len(X) if X is not None else n
    if n_actual is None:
        return _data(STATUS_UNAVAILABLE, REASON_INSUFFICIENT_TRAINING_DATA,
                     "training set has no usable row count")
    try:
        n_actual = int(n_actual)
    except (TypeError, ValueError):
        return _data(STATUS_UNAVAILABLE, REASON_INSUFFICIENT_TRAINING_DATA,
                     "training set has no usable row count")
    if d is None:
        return _data(STATUS_UNAVAILABLE, REASON_INSUFFICIENT_TRAINING_DATA,
                     "training set has no usable dimension")
    try:
        d_int = int(d)
    except (TypeError, ValueError):
        return _data(STATUS_UNAVAILABLE, REASON_INSUFFICIENT_TRAINING_DATA,
                     "training set has no usable dimension")
    n_min = getattr(training_set, "n_min", None)
    if n_min is None:
        n_min = n_min_for(d_int)
    else:
        try:
            n_min = int(n_min)
        except (TypeError, ValueError):
            n_min = max(N_MIN_FLOOR, 2 * (d_int + 1))
    if n_actual < n_min:
        return _data(STATUS_UNAVAILABLE, REASON_INSUFFICIENT_TRAINING_DATA,
                     f"n={n_actual} is below n_min={n_min}",
                     n=n_actual, n_min=n_min)
    return _data(STATUS_OK, REASON_OK, None, n=n_actual, n_min=n_min)


def _pareto_data_status(cohort, metric_observations) -> dict:
    if cohort is None or not getattr(cohort, "ok", False) \
            or not getattr(cohort, "observations", None):
        return _data(STATUS_UNAVAILABLE, REASON_VALIDATED_COHORT_REQUIRED,
                     "only a successful, non-empty validated CohortResult is accepted")
    if not isinstance(metric_observations, dict):
        return _data(STATUS_UNAVAILABLE, REASON_METRIC_BINDINGS_REQUIRED,
                     "metric_observations must map every cohort observation ID to a "
                     "complete MetricObservation")
    claims = {}
    for row in getattr(cohort, "policy_identity", ()) or ():
        try:
            key, namespace, value = row
        except (TypeError, ValueError):
            return _data(STATUS_UNAVAILABLE, REASON_METRIC_POLICY_MISSING,
                         "malformed cohort policy identity")
        claims[str(key)] = (namespace, value)
    try:
        metric_ns, metric_json = claims["metric_policy"]
        mask_ns, mask_json = claims["frequency_masks"]
        metric_hash = json.loads(metric_json)
        if (metric_ns != "bo.physical_metric_spec_hash" or mask_ns != metric_ns
                or json.loads(mask_json) != metric_hash
                or not isinstance(metric_hash, str) or len(metric_hash) != 64
                or any(c not in "0123456789abcdef" for c in metric_hash)):
            raise ValueError("metric and support identities must name the same physical metric hash")
    except (KeyError, TypeError, ValueError):
        return _data(STATUS_UNAVAILABLE, REASON_METRIC_POLICY_MISSING,
                     "the cohort must bind metric_policy and frequency_masks to one canonical "
                     "physical_metric_spec_hash")

    observations = tuple(getattr(cohort, "observations", ()) or ())
    ids = [getattr(o, "observation_id", None) for o in observations]
    if any(oid is None for oid in ids) or len(set(ids)) != len(ids) \
            or set(metric_observations) != set(ids):
        return _data(STATUS_UNAVAILABLE, REASON_METRIC_BINDING_MISMATCH,
                     "every cohort observation ID needs exactly one ID-bound metric observation")
    values = []
    for oid in ids:
        item = metric_observations[oid]
        if (getattr(item, "status", None) != "complete"
                or getattr(item, "physical_metric_spec_hash", None) != metric_hash):
            return _data(STATUS_UNAVAILABLE, REASON_METRIC_INCOMPLETE,
                         "metric observation is partial, missing, or uses a different metric hash")
        try:
            pair = [float(getattr(item, "coverage_deg")), float(getattr(item, "ripple_db"))]
        except (AttributeError, TypeError, ValueError):
            return _data(STATUS_UNAVAILABLE, REASON_METRIC_INCOMPLETE,
                         "coverage/ripple physical errors are missing or non-numeric")
        if not np.isfinite(pair).all() or min(pair) < 0:
            return _data(STATUS_UNAVAILABLE, REASON_METRIC_INCOMPLETE,
                         "coverage/ripple physical errors must be finite and nonnegative")
        values.append(pair)
    try:
        reference = _pareto.frozen_reference(values)
    except (TypeError, ValueError):
        return _data(STATUS_UNAVAILABLE, REASON_METRIC_INCOMPLETE,
                     "a finite two-objective frozen reference cannot be formed")
    return _data(STATUS_OK, REASON_OK, None, frozen_reference=reference,
                 n=len(values), metric_spec_hash=metric_hash)


def _pool_data_status(pool) -> dict:
    if pool is None:
        return _data(STATUS_UNAVAILABLE, REASON_LEGAL_POOL_REQUIRED,
                     "a legal CandidatePool is required")
    if getattr(pool, "status", None) != STATUS_OK:
        return _data(STATUS_POOL_EXHAUSTED, REASON_POOL_EXHAUSTED,
                     "candidate pool is not in the ok state")
    candidates = list(getattr(pool, "candidates", ()) or ())
    if not candidates:
        return _data(STATUS_POOL_EXHAUSTED, REASON_POOL_EXHAUSTED,
                     "candidate pool contains no novel legal candidate")
    for candidate in candidates:
        vector = getattr(candidate, "active_vector", None)
        if vector is None:
            continue
        try:
            arr = np.asarray(vector, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            continue
        if arr.size and np.isfinite(arr).all() and np.all(arr >= 0.0) and np.all(arr <= 1.0):
            return _data(STATUS_OK, REASON_OK, None, n=len(candidates))
    return _data(STATUS_POOL_EXHAUSTED, REASON_POOL_EXHAUSTED,
                 "no candidate carries a finite unit-box active vector")


def _seed_field(item, *names):
    if isinstance(item, dict):
        for name in names:
            if name in item and item[name] is not None:
                return item[name]
        return None
    for name in names:
        value = getattr(item, name, None)
        if value is not None:
            return value
    return None


def _seed_eligibility(item):
    raw = _seed_field(item, "cheap_checks_passed", "eligibility", "verification")
    if isinstance(raw, (bool, np.bool_)):
        return "passed" if bool(raw) else "rejected"
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in {"unknown", "unverified"}:
            return "unknown"
        if text in {"cheap_checks_passed", "passed", "ok", "eligible", "true"}:
            return "passed"
        if text in {"rejected", "failed", "fail", "ineligible", "false"}:
            return "rejected"
    return None


def _seed_table(seeds) -> tuple[list[dict] | None, dict | None]:
    """Validate explicit seed candidates; return ``(entries, error)``."""
    if seeds is None or isinstance(seeds, (str, bytes, dict)):
        return None, _data(STATUS_UNAVAILABLE, REASON_SEEDS_REQUIRED,
                           "an explicit non-empty seed-candidate sequence from S5 is required")
    try:
        items = list(seeds)
    except TypeError:
        return None, _data(STATUS_UNAVAILABLE, REASON_SEEDS_REQUIRED,
                           "seed candidates must be a sequence")
    if not items:
        return None, _data(STATUS_UNAVAILABLE, REASON_SEEDS_REQUIRED,
                           "seed candidate sequence is empty")
    entries = []
    seen = set()
    for index, item in enumerate(items):
        source = _seed_field(item, "source", "seed_source", "origin", "archive_source")
        seed = _seed_field(item, "seed", "seed_id", "archive_seed", "index")
        source = None if source is None else str(source).strip()
        seed = None if seed is None else str(seed).strip()
        if not source or not seed:
            return None, _data(STATUS_UNAVAILABLE, REASON_INVALID_SEED,
                               f"seed candidate {index} is missing a nonempty source/seed identity")
        eligibility = _seed_eligibility(item)
        if eligibility is None:
            return None, _data(
                STATUS_UNAVAILABLE, REASON_INVALID_SEED,
                f"seed candidate {index} must carry cheap_checks_passed=True/False or an "
                f"explicit eligibility of 'cheap_checks_passed'/'unknown'")
        key = (source, seed)
        if key in seen:
            return None, _data(STATUS_UNAVAILABLE, REASON_DUPLICATE_SEED,
                               f"duplicate seed identity {key!r}")
        seen.add(key)
        entries.append({"source": source, "seed": seed, "eligibility": eligibility,
                        "key": key, "item": item})
    if not any(entry["eligibility"] != "rejected" for entry in entries):
        return None, _data(STATUS_UNAVAILABLE, REASON_NO_ELIGIBLE_SEED,
                           "every provided seed candidate is explicitly rejected")
    return entries, None


def _seed_counts(entries) -> dict:
    return {
        "input": len(entries),
        "passed": sum(1 for e in entries if e["eligibility"] == "passed"),
        "unknown": sum(1 for e in entries if e["eligibility"] == "unknown"),
        "rejected": sum(1 for e in entries if e["eligibility"] == "rejected"),
        "selectable": sum(1 for e in entries if e["eligibility"] != "rejected"),
    }


def _seed_proposal(entry) -> dict:
    item = entry["item"]
    out: dict
    if isinstance(item, dict):
        out = dict(item)
    elif hasattr(item, "as_dict"):
        try:
            out = item.as_dict(include_vectors=True)
        except TypeError:
            out = item.as_dict()
    else:
        out = {}
        for name in ("candidate_id", "geometry_hash", "design_hash", "intended_solve_hash",
                     "params", "descriptors", "checks"):
            value = getattr(item, name, None)
            if value is not None:
                out[name] = value
    out["source"] = entry["source"]
    out["seed"] = entry["seed"]
    out["seed_identity"] = f"{entry['source']}|{entry['seed']}"
    out["eligibility"] = entry["eligibility"]
    return out


def _select_seed(entries) -> dict:
    """Deterministic: passed before unknown, then lexicographic source/seed identity."""
    return sorted(entries, key=lambda e: (
        0 if e["eligibility"] == "passed" else 1, e["source"], e["seed"]))[0]


def capability_status(policy: str, *, training_set=None, cohort=None,
                      metric_observations=None, pool=None, seeds=None) -> dict:
    """Explicit preflight for a proposal policy.

    Returns ``status``/``reason``/``detail``/``required_inputs`` plus the data gate
    (``data_status``/``data_reason``) and optional-engine marker (``engine_status``).  The
    overall ``status`` is ``ok`` only when the policy can actually propose now.
    """
    if policy not in PROPOSAL_POLICIES:
        return {
            "policy": policy, "status": STATUS_UNAVAILABLE,
            "reason": REASON_UNSUPPORTED_POLICY,
            "detail": f"known policies are {PROPOSAL_POLICIES!r}",
            "data_status": STATUS_UNAVAILABLE, "data_reason": REASON_UNSUPPORTED_POLICY,
            "engine_status": "not_required", "engine_reason": None,
            "verification_mode": None, "required_inputs": [],
            "library_versions": _engine_versions(),
        }
    mode = verification_mode(policy)
    if policy == POLICY_SCALAR:
        data = _scalar_data_status(training_set)
        required = ["training_set"]
    elif policy == POLICY_PARETO:
        data = _pareto_data_status(cohort, metric_observations)
        required = ["cohort", "metric_observations"]
    elif policy == POLICY_CMA_SEED:
        entries, error = _seed_table(seeds)
        data = error if error is not None else _data(
            STATUS_OK, REASON_OK, None, counts=_seed_counts(entries))
        required = ["seeds"]
    else:  # exploration
        data = _pool_data_status(pool)
        required = ["pool"]

    needs_engine = policy in ENGINE_POLICIES
    engine_ok = _engine_available() if needs_engine else None
    if not needs_engine:
        engine_status, engine_reason = "not_required", None
    elif engine_ok:
        engine_status, engine_reason = STATUS_OK, None
    else:
        engine_status, engine_reason = STATUS_CAPABILITY_MISSING, REASON_CAPABILITY_MISSING

    if data["status"] != STATUS_OK:
        overall, reason, detail = data["status"], data["reason"], data.get("detail")
    elif needs_engine and not engine_ok:
        overall = STATUS_CAPABILITY_MISSING
        reason = REASON_CAPABILITY_MISSING
        detail = ("optional BoTorch/GPyTorch/Torch engine is unavailable; lazy import keeps "
                  "this a tagged refusal, not a fabricated proposal")
    else:
        overall, reason, detail = STATUS_OK, REASON_OK, data.get("detail")

    out = {
        "policy": policy,
        "status": overall,
        "reason": reason,
        "detail": detail,
        "data_status": data["status"],
        "data_reason": data["reason"],
        "engine_status": engine_status,
        "engine_reason": engine_reason,
        "verification_mode": mode,
        "required_inputs": list(required),
        "library_versions": _engine_versions(),
    }
    for key in ("frozen_reference", "n", "n_min", "metric_spec_hash", "counts"):
        if key in data:
            out[key] = data[key]
    return out


# --------------------------------------------------------------------------- dispatch


def _normalise_status(status: str | None, reason: str | None) -> str:
    if reason == REASON_POOL_EXHAUSTED:
        return STATUS_POOL_EXHAUSTED
    if reason == REASON_CAPABILITY_MISSING or (
            isinstance(reason, str) and reason.startswith("capability_missing")):
        return STATUS_CAPABILITY_MISSING
    if status in (STATUS_OK, STATUS_UNAVAILABLE, STATUS_CAPABILITY_MISSING,
                  STATUS_POOL_EXHAUSTED):
        return status
    return STATUS_UNAVAILABLE


def _failure(policy: str, reason: str, detail: str | None = None, *,
             status: str = STATUS_UNAVAILABLE, counts: dict | None = None,
             library_versions: dict | None = None) -> ProposalOutcome:
    return ProposalOutcome(
        status=_normalise_status(status, reason), reason=reason, policy=policy,
        selection_reason=None, proposal=None, predicted=None, acquisition=None,
        fallback=False, verification_mode=verification_mode(policy),
        library_versions=dict(library_versions or _engine_versions()),
        detail=detail, counts=dict(counts or {}))


def _outcome_from_proposal_result(policy: str, result) -> ProposalOutcome:
    reason = getattr(result, "reason", None) or "unknown_failure"
    status = getattr(result, "status", STATUS_UNAVAILABLE)
    predicted = getattr(result, "predicted", None)
    acquisition = getattr(result, "acquisition", None)
    return ProposalOutcome(
        status=_normalise_status(status, reason),
        reason=reason,
        policy=policy,
        selection_reason=getattr(result, "selection_reason", None),
        proposal=getattr(result, "candidate", None),
        predicted=predicted,
        acquisition=acquisition,
        fallback=bool(getattr(result, "fallback", False)),
        verification_mode=verification_mode(policy),
        library_versions=dict(getattr(result, "library_versions", {}) or {}),
        detail=getattr(result, "detail", None),
        counts=dict(getattr(result, "counts", {}) or {}))


def _outcome_from_pareto_proposal(result: dict) -> ProposalOutcome:
    status = result.get("status", STATUS_UNAVAILABLE)
    reason = result.get("reason") or ("ok" if status == STATUS_OK else "unknown_failure")
    ok = status == STATUS_OK
    predicted = result.get("physical_predictions") if ok else None
    if ok and result.get("acquisition_value") is not None:
        acquisition = {
            "value": result.get("acquisition_value"),
            "units": "log expected hypervolume improvement (technical ranking only)",
            "selection_reason": result.get("selection_reason"),
            "reference": result.get("reference"),
        }
    else:
        acquisition = None
    return ProposalOutcome(
        status=_normalise_status(status, reason),
        reason=reason,
        policy=POLICY_PARETO,
        selection_reason=result.get("selection_reason"),
        proposal=result.get("candidate") if ok else None,
        predicted=predicted,
        acquisition=acquisition,
        fallback=False,
        verification_mode="pareto",
        library_versions=_engine_versions(),
        detail=result.get("note") or result.get("detail"),
        counts=dict(result.get("counts") or {}))


def fit_and_propose(policy: str, *, training_set=None, cohort=None,
                    metric_observations=None, pool=None, history=None, seed: int = 0,
                    encoding=None, config=None, cma_seed_candidates=None,
                    resolution_mm: float = 30.0) -> ProposalOutcome:
    """Fit (when required) and select one proposal for ``policy``.

    Scalar calls the locked ``fit_model`` + ``propose_one``; Pareto calls ``fit_pareto`` +
    ``propose_pareto``; ``cma_seed`` selects deterministically from the caller's explicit seed
    list with no score math; ``exploration`` uses the existing legal-pool maximin selection and
    is labelled non-BO.  Tagged failures are propagated without fabricated values.
    """
    if policy not in PROPOSAL_POLICIES:
        return ProposalOutcome(
            status=STATUS_UNAVAILABLE, reason=REASON_UNSUPPORTED_POLICY, policy=str(policy),
            selection_reason=None, proposal=None, predicted=None, acquisition=None,
            fallback=False, verification_mode="scalar",
            library_versions=_engine_versions(),
            detail=f"known policies are {PROPOSAL_POLICIES!r}", counts={})

    if policy == POLICY_SCALAR:
        if training_set is None:
            return _failure(POLICY_SCALAR, REASON_TRAINING_SET_REQUIRED,
                            "a TrainingSet produced by bo.data is required")
        fitted = _model.fit_model(training_set, seed=int(seed))
        if getattr(fitted, "status", None) != STATUS_OK:
            reason = getattr(fitted, "reason", None) or "model_unavailable"
            return _failure(POLICY_SCALAR, reason, getattr(fitted, "detail", None),
                            status=getattr(fitted, "status", STATUS_UNAVAILABLE),
                            library_versions=getattr(fitted, "library_versions", None))
        result = _propose.propose_one(
            fitted, pool, history=history, encoding=encoding, config=config,
            resolution_mm=resolution_mm)
        return _outcome_from_proposal_result(POLICY_SCALAR, result)

    if policy == POLICY_PARETO:
        if cohort is None:
            return _failure(POLICY_PARETO, REASON_VALIDATED_COHORT_REQUIRED,
                            "only a successful validated CohortResult is accepted")
        if metric_observations is None:
            return _failure(POLICY_PARETO, REASON_METRIC_BINDINGS_REQUIRED,
                            "ID-bound complete MetricObservations are required")
        fitted = _pareto.fit_pareto(cohort, metric_observations, seed=int(seed))
        if getattr(fitted, "status", None) != STATUS_OK:
            reason = getattr(fitted, "reason", None) or "model_unavailable"
            return _failure(POLICY_PARETO, reason, None,
                            status=getattr(fitted, "status", STATUS_UNAVAILABLE))
        hist = history if history is not None else ProposalHistory()
        result = _pareto.propose_pareto(
            fitted, pool, hist, encoding=encoding, config=config, seed=int(seed),
            resolution_mm=resolution_mm)
        return _outcome_from_pareto_proposal(result)

    if policy == POLICY_CMA_SEED:
        entries, error = _seed_table(cma_seed_candidates)
        if error is not None:
            return _failure(POLICY_CMA_SEED, error["reason"], error.get("detail"),
                            status=error["status"])
        counts = _seed_counts(entries)
        chosen = _select_seed(entries)
        return ProposalOutcome(
            status=STATUS_OK, reason=REASON_OK, policy=POLICY_CMA_SEED,
            selection_reason="cma_archive_seed",
            proposal=_seed_proposal(chosen),
            predicted=None, acquisition=None, fallback=False,
            verification_mode=verification_mode(POLICY_CMA_SEED),
            library_versions=_engine_versions(),
            detail=("explicit CMA archive seed selection from caller-provided candidates "
                    "(non-BO; no score math and no predictions)"),
            counts=counts)

    # exploration
    pool_state = _pool_data_status(pool)
    if pool_state["status"] != STATUS_OK:
        return _failure(POLICY_EXPLORATION, pool_state["reason"], pool_state.get("detail"),
                        status=pool_state["status"])
    hist = history if history is not None else ProposalHistory()
    try:
        legal, counts = _propose._filter_legal(pool, hist, None, ProposalPolicy())
    except (AttributeError, TypeError, ValueError) as exc:
        return _failure(POLICY_EXPLORATION, REASON_POOL_EXHAUSTED,
                        f"legal-pool filtering failed: {type(exc).__name__}: {exc}",
                        status=STATUS_POOL_EXHAUSTED)
    if not legal:
        return _failure(POLICY_EXPLORATION, REASON_POOL_EXHAUSTED,
                        "every pooled candidate is already evaluated, pending, or a "
                        "near-duplicate", status=STATUS_POOL_EXHAUSTED, counts=counts)
    reference = []
    for vector in tuple(hist.pending_vectors) + tuple(hist.excluded_vectors):
        arr = np.asarray(vector, dtype=float).reshape(-1)
        if np.isfinite(arr).all():
            reference.append(arr)
    pick = _propose._maximin_pick(legal, reference)
    if pick is None:
        return _failure(POLICY_EXPLORATION, REASON_POOL_EXHAUSTED,
                        "maximin selection returned no candidate",
                        status=STATUS_POOL_EXHAUSTED, counts=counts)
    candidate, _vector, distance = pick
    try:
        _propose.validate_selected_candidate(
            candidate, pool, encoding=encoding, config=config, resolution_mm=resolution_mm)
    except Exception as exc:  # noqa: BLE001 - a refused geometry is never published
        return _failure(POLICY_EXPLORATION, REASON_VALIDATION_FAILED,
                        f"proposal validation failed: {type(exc).__name__}: {exc}",
                        counts=counts)
    counts = dict(counts)
    counts.update({"method": "maximin", "distance_l2": float(distance),
                   "reference_points": len(reference)})
    return ProposalOutcome(
        status=STATUS_OK, reason=REASON_OK, policy=POLICY_EXPLORATION,
        selection_reason="maximin_exploration",
        proposal=_propose._candidate_dict(candidate),
        predicted=None, acquisition=None, fallback=False,
        verification_mode=verification_mode(POLICY_EXPLORATION),
        library_versions=_engine_versions(),
        detail=("non-BO fixed maximin exploration from the same legal pool; no predictions "
                "or acquisition scores are produced"),
        counts=counts)


__all__ = [
    "POLICY_SCALAR",
    "POLICY_PARETO",
    "POLICY_CMA_SEED",
    "POLICY_EXPLORATION",
    "PROPOSAL_POLICIES",
    "PROPOSAL_POLICY_LABELS",
    "ENGINE_POLICIES",
    "STATUS_CAPABILITY_MISSING",
    "STATUS_POOL_EXHAUSTED",
    "ProposalOutcome",
    "verification_mode",
    "capability_status",
    "fit_and_propose",
]
