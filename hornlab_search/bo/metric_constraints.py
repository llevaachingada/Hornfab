"""RESEARCH-ONLY constrained Bayesian optimization over physical metric posteriors.

This module builds a ``qLogNoisyExpectedImprovement`` acquisition whose feasibility comes from
**constraint posteriors** (the same independent-output GP used by the research composite), not from
rescaling score weights and not from treating a large score penalty as a hard constraint.

Contract
--------
* A :class:`PhysicalConstraint` is a signed margin ``g_i(x) = metric_i(x) - threshold <= 0``.
* Constraint metric keys must be outputs of the fitted model.  A missing metric makes the
  acquisition unavailable; it is never replaced by a fake feasible point.
* Infeasibility is a hard mask in the evaluation helper: a candidate with no feasible posterior
  sample gets ``-inf`` (and is refused by selection).  The BoTorch utility uses a large finite
  negative penalty internally so ``qLogNEI``'s log-space reduction cannot become NaN; the public
  evaluation restores the hard ``-inf`` mask.
* Nothing here is wired into ``bo.policy`` or any production search.  Every result is tagged
  ``research_only=True`` and ``policy="physical_constrained_research_v1"``.
* v11 CD scoring is not universal; the caller opts in explicitly by naming CD metric outputs.

Torch/BoTorch are imported lazily.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from .metric_contracts import sha256_json

RESEARCH_POLICY = "physical_constrained_research_v1"
RESEARCH_ONLY = True
OBJECTIVE_VERSION = 11
MARGIN_CONVENTION = "g_i(x) = metric_i(x) - threshold_i <= 0"
POLICY_LABEL = (
    "research-only constrained acquisition; not a production policy and not wired into bo.policy")
ACQUISITION_POLICY = "qLogNoisyExpectedImprovement_hard_constraints"
SAMPLER_SAMPLE_SHAPE = 128
INFEASIBLE_PENALTY = -1e6

STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

REASON_OK = "ok"
REASON_INVALID_MODEL = "invalid_model"
REASON_NO_CONSTRAINTS = "no_constraints"
REASON_DUPLICATE_CONSTRAINT = "duplicate_constraint"
REASON_CONSTRAINT_OUTPUT_MISSING = "constraint_output_missing"
REASON_UNSUPPORTED_MISSING_POLICY = "unsupported_missing_value_policy"
REASON_NO_OBJECTIVE_OUTPUTS = "no_objective_outputs"
REASON_INVALID_CANDIDATES = "invalid_candidates"
REASON_CAPABILITY_MISSING = "capability_missing"
REASON_ACQUISITION_FAILED = "acquisition_failed"
REASON_NONFINITE_ACQUISITION = "nonfinite_acquisition"
REASON_NO_FEASIBLE_CANDIDATE = "no_feasible_candidate"
REASON_NONFINITE_POSTERIOR = "nonfinite_posterior"


@dataclass(frozen=True)
class PhysicalConstraint:
    """One signed physical constraint (``g_i(x) <= 0``)."""

    metric_key: str
    units: str
    threshold: float
    source: str
    fidelity: str
    missing_value_policy: str = "refuse"
    objective_version: int = OBJECTIVE_VERSION

    def to_dict(self) -> dict:
        return {
            "objective_version": int(self.objective_version),
            "metric_key": self.metric_key,
            "units": self.units,
            "threshold": float(self.threshold),
            "source": self.source,
            "fidelity": self.fidelity,
            "missing_value_policy": self.missing_value_policy,
            "margin_convention": MARGIN_CONVENTION,
        }

    @property
    def identity_hash(self) -> str:
        return sha256_json(self.to_dict())


@dataclass(frozen=True)
class ConstrainedAcquisitionResult:
    """A built constrained acquisition plus its frozen provenance."""

    status: str
    reason: str
    detail: str | None = None
    acq: Any = field(default=None, repr=False, compare=False)
    model_result: Any = field(default=None, repr=False, compare=False)
    constraints: tuple[dict, ...] = ()
    output_names: tuple[str, ...] = ()
    objective_output_names: tuple[str, ...] = ()
    constraint_output_names: tuple[str, ...] = ()
    objective_indices: tuple[int, ...] = ()
    constraint_indices: tuple[int, ...] = ()
    thresholds: tuple[float, ...] = ()
    X_baseline: np.ndarray | None = field(default=None, repr=False, compare=False)
    X_pending: np.ndarray | None = field(default=None, repr=False, compare=False)
    acq_seed: int = 0
    sample_shape: int = SAMPLER_SAMPLE_SHAPE
    infeasible_penalty: float = INFEASIBLE_PENALTY
    policy: str = RESEARCH_POLICY
    acquisition_policy: str = ACQUISITION_POLICY
    library_versions: dict = field(default_factory=dict)
    timing_s: float | None = None
    research_only: bool = RESEARCH_ONLY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "constraints": [dict(v) for v in self.constraints],
            "output_names": list(self.output_names),
            "objective_output_names": list(self.objective_output_names),
            "constraint_output_names": list(self.constraint_output_names),
            "objective_indices": list(self.objective_indices),
            "constraint_indices": list(self.constraint_indices),
            "thresholds": list(self.thresholds),
            "acq_seed": int(self.acq_seed),
            "sample_shape": int(self.sample_shape),
            "infeasible_penalty": float(self.infeasible_penalty),
            "policy": self.policy,
            "acquisition_policy": self.acquisition_policy,
            "library_versions": dict(self.library_versions),
            "timing_s": self.timing_s,
            "research_only": bool(self.research_only),
        }


@dataclass(frozen=True)
class ConstrainedCandidateEvaluation:
    """Per-candidate constrained acquisition values and sampled feasibility."""

    status: str
    reason: str
    detail: str | None = None
    values: np.ndarray | None = None
    acquisition_values: np.ndarray | None = None
    feasibility_probability: np.ndarray | None = None
    feasible_mask: np.ndarray | None = None
    objective_mean: np.ndarray | None = None
    constraint_mean: np.ndarray | None = None
    constraint_max: np.ndarray | None = None
    n: int = 0
    n_samples: int = 0
    infeasible_count: int = 0
    seed: int = 0
    flags: tuple[str, ...] = ()
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        def _list(v):
            return None if v is None else np.asarray(v, dtype=float).reshape(-1).tolist()

        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "values": _list(self.values),
            "acquisition_values": _list(self.acquisition_values),
            "feasibility_probability": _list(self.feasibility_probability),
            "feasible_mask": (None if self.feasible_mask is None
                              else np.asarray(self.feasible_mask, dtype=bool).reshape(-1).tolist()),
            "objective_mean": _list(self.objective_mean),
            "constraint_mean": (None if self.constraint_mean is None
                                else np.asarray(self.constraint_mean, dtype=float).tolist()),
            "constraint_max": (None if self.constraint_max is None
                               else np.asarray(self.constraint_max, dtype=float).tolist()),
            "n": int(self.n),
            "n_samples": int(self.n_samples),
            "infeasible_count": int(self.infeasible_count),
            "seed": int(self.seed),
            "flags": list(self.flags),
            "research_only": bool(self.research_only),
            "policy": self.policy,
        }


@dataclass(frozen=True)
class ConstrainedSelection:
    """One advisory candidate chosen among sampled-feasible candidates."""

    status: str
    reason: str
    detail: str | None = None
    candidate_index: int | None = None
    value: float | None = None
    feasibility_probability: float | None = None
    values: np.ndarray | None = None
    eligibility_threshold: float = 0.5
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


def _constraint_list(constraints) -> tuple[PhysicalConstraint, ...]:
    if constraints is None:
        return ()
    if isinstance(constraints, PhysicalConstraint):
        return (constraints,)
    return tuple(constraints)


def _import_acq_engine():
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


def constraint_margins(metric_samples, constraints: Sequence[PhysicalConstraint],
                       output_names: Sequence[str]) -> np.ndarray:
    """Pure NumPy signed margins ``g = metric - threshold`` for a sample array.

    ``metric_samples`` has shape ``[..., m]`` with the last axis ordered by ``output_names``.
    Returns shape ``[..., k]`` (``k`` constraints).  A missing output name raises ``KeyError``;
    callers that must not fabricate feasibility use :func:`feasibility_from_samples`.
    """
    arr = np.asarray(metric_samples, dtype=np.float64)
    names = tuple(str(v) for v in output_names)
    margins = []
    for constraint in constraints:
        try:
            index = names.index(constraint.metric_key)
        except ValueError as exc:
            raise KeyError(f"constraint output {constraint.metric_key!r} is not in the model") from exc
        margins.append(arr[..., index] - float(constraint.threshold))
    if not margins:
        return np.zeros(arr.shape[:-1] + (0,), dtype=np.float64)
    return np.stack(margins, axis=-1)


def feasibility_from_samples(metric_samples, constraints: Sequence[PhysicalConstraint],
                             output_names: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    """Pure NumPy ``(feasible_mask, margins)`` with ``g_i <= 0`` for every constraint."""
    margins = constraint_margins(metric_samples, constraints, output_names)
    feasible = np.all(margins <= 0.0, axis=-1)
    return feasible, margins


def _unavailable(reason: str, detail: str | None = None, *,
                 constraints: Sequence[PhysicalConstraint] = (),
                 output_names: Sequence[str] = (), acq_seed: int = 0,
                 sample_shape: int = SAMPLER_SAMPLE_SHAPE,
                 timing_s: float | None = None,
                 versions: Mapping[str, Any] | None = None) -> ConstrainedAcquisitionResult:
    return ConstrainedAcquisitionResult(
        status=STATUS_UNAVAILABLE, reason=reason, detail=detail,
        constraints=tuple(c.to_dict() for c in constraints),
        output_names=tuple(output_names), acq_seed=int(acq_seed),
        sample_shape=int(sample_shape), timing_s=timing_s,
        library_versions=dict(versions or {}))


def build_constrained_acquisition(model_result, constraints, *, acq_seed: int = 0,
                                  sample_shape: int = SAMPLER_SAMPLE_SHAPE,
                                  X_baseline=None, X_pending=None,
                                  objective_output_names: Sequence[str] | None = None,
                                  infeasible_penalty: float = INFEASIBLE_PENALTY
                                  ) -> ConstrainedAcquisitionResult:
    """Build a ``qLogNEI`` acquisition with hard feasibility from constraint posteriors.

    ``model_result`` must be an ``ok`` independent-output fit with ``output_names`` covering every
    constraint metric.  Objective outputs are all remaining model outputs unless
    ``objective_output_names`` narrows them.  Missing constraint metrics, an empty objective set,
    a non-``refuse`` missing-value policy and any construction failure return a tagged
    ``unavailable`` result; no acquisition and no fake feasible candidate are produced.
    """
    started = time.perf_counter()
    if model_result is None or getattr(model_result, "status", None) != STATUS_OK \
            or getattr(model_result, "model", None) is None:
        return _unavailable(REASON_INVALID_MODEL, "model_result must be an ok fitted model",
                            acq_seed=acq_seed, sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)
    names = tuple(str(v) for v in (getattr(model_result, "output_names", ()) or ()))
    if not names:
        return _unavailable(REASON_INVALID_MODEL, "model_result has no output_names",
                            acq_seed=acq_seed, sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)
    cons = _constraint_list(constraints)
    if not cons:
        return _unavailable(REASON_NO_CONSTRAINTS, "at least one PhysicalConstraint is required",
                            output_names=names, acq_seed=acq_seed,
                            sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)
    keys = [c.metric_key for c in cons]
    if len(set(keys)) != len(keys):
        return _unavailable(REASON_DUPLICATE_CONSTRAINT,
                            f"duplicate constraint metric keys {keys!r}",
                            constraints=cons, output_names=names, acq_seed=acq_seed,
                            sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)
    for constraint in cons:
        if constraint.metric_key not in names:
            return _unavailable(f"{REASON_CONSTRAINT_OUTPUT_MISSING}:{constraint.metric_key}",
                                f"model outputs are {names!r}; a missing constraint metric is "
                                "never assumed feasible", constraints=cons,
                                output_names=names, acq_seed=acq_seed,
                                sample_shape=sample_shape,
                                timing_s=time.perf_counter() - started)
        if constraint.missing_value_policy != "refuse":
            return _unavailable(
                f"{REASON_UNSUPPORTED_MISSING_POLICY}:{constraint.metric_key}",
                f"only missing_value_policy='refuse' is supported, got "
                f"{constraint.missing_value_policy!r}", constraints=cons,
                output_names=names, acq_seed=acq_seed, sample_shape=sample_shape,
                timing_s=time.perf_counter() - started)
        value = getattr(constraint, "threshold", None)
        if not isinstance(value, (int, float)) or isinstance(value, bool) \
                or not math.isfinite(float(value)):
            return _unavailable(f"{REASON_INVALID_MODEL}:{constraint.metric_key}",
                                f"constraint threshold must be finite, got {value!r}",
                                constraints=cons, output_names=names, acq_seed=acq_seed,
                                sample_shape=sample_shape,
                                timing_s=time.perf_counter() - started)

    constraint_keys = tuple(c.metric_key for c in cons)
    if objective_output_names is None:
        objective_names = tuple(n for n in names if n not in constraint_keys)
    else:
        objective_names = tuple(str(v) for v in objective_output_names)
        unknown = [n for n in objective_names if n not in names]
        overlap = [n for n in objective_names if n in constraint_keys]
        if unknown or overlap or not objective_names:
            return _unavailable(
                REASON_NO_OBJECTIVE_OUTPUTS,
                f"objective outputs {objective_names!r} must be non-empty, known model outputs "
                f"and disjoint from constraints {constraint_keys!r} (unknown={unknown!r}, "
                f"overlap={overlap!r})", constraints=cons, output_names=names,
                acq_seed=acq_seed, sample_shape=sample_shape,
                timing_s=time.perf_counter() - started)
    if not objective_names:
        return _unavailable(REASON_NO_OBJECTIVE_OUTPUTS,
                            "every model output is a constraint; no objective output remains",
                            constraints=cons, output_names=names, acq_seed=acq_seed,
                            sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)

    engine, import_error = _import_acq_engine()
    if engine is None:
        return _unavailable(REASON_CAPABILITY_MISSING,
                            f"optional BoTorch acquisition engine is unavailable: {import_error}",
                            constraints=cons, output_names=names, acq_seed=acq_seed,
                            sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)

    baseline = X_baseline if X_baseline is not None else getattr(model_result, "train_X", None)
    if baseline is None:
        return _unavailable(REASON_INVALID_CANDIDATES, "no observed X_baseline is available",
                            constraints=cons, output_names=names, acq_seed=acq_seed,
                            sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)
    try:
        baseline_arr = np.asarray(baseline, dtype=np.float64)
        if baseline_arr.ndim != 2 or baseline_arr.shape[0] < 1 or not np.all(np.isfinite(baseline_arr)):
            raise ValueError(f"X_baseline must be finite 2-D, got {baseline_arr.shape}")
        pending_arr = None
        if X_pending is not None:
            pending_arr = np.asarray(X_pending, dtype=np.float64)
            if pending_arr.size and (pending_arr.ndim != 2
                                     or pending_arr.shape[1] != baseline_arr.shape[1]
                                     or not np.all(np.isfinite(pending_arr))):
                raise ValueError("X_pending must be finite and match the baseline dimension")
            if not pending_arr.size:
                pending_arr = None
    except (TypeError, ValueError) as exc:
        return _unavailable(REASON_INVALID_CANDIDATES, str(exc), constraints=cons,
                            output_names=names, acq_seed=acq_seed, sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)

    obj_idx = tuple(names.index(n) for n in objective_names)
    con_idx = tuple(names.index(n) for n in constraint_keys)
    thresholds = tuple(float(c.threshold) for c in cons)
    torch = engine["torch"]
    try:
        try:
            from .model import NUM_THREADS, library_versions
            torch.set_num_threads(NUM_THREADS)
            versions = library_versions()
        except Exception:  # noqa: BLE001
            versions = {}

        def utility(samples, X=None):
            # samples: [..., m].  Feasibility is a hard mask from the constraint outputs.
            constraint_samples = samples[..., list(con_idx)]
            thresholds_t = torch.as_tensor(thresholds, dtype=samples.dtype,
                                           device=samples.device)
            feasible = torch.all(constraint_samples - thresholds_t <= 0.0, dim=-1)
            objective_score = -samples[..., list(obj_idx)].sum(dim=-1)
            penalty = torch.full_like(objective_score, float(infeasible_penalty))
            return torch.where(feasible, objective_score, penalty)

        sampler = engine["SobolQMCNormalSampler"](
            torch.Size([int(sample_shape)]), seed=int(acq_seed))
        objective = engine["GenericMCObjective"](utility)
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
        return _unavailable(REASON_ACQUISITION_FAILED,
                            f"constrained qLogNEI construction failed: "
                            f"{type(exc).__name__}: {exc}", constraints=cons,
                            output_names=names, acq_seed=acq_seed,
                            sample_shape=sample_shape,
                            timing_s=time.perf_counter() - started)

    return ConstrainedAcquisitionResult(
        status=STATUS_OK, reason=REASON_OK, acq=acq, model_result=model_result,
        constraints=tuple(c.to_dict() for c in cons), output_names=names,
        objective_output_names=objective_names,
        constraint_output_names=constraint_keys, objective_indices=obj_idx,
        constraint_indices=con_idx, thresholds=thresholds,
        X_baseline=np.array(baseline_arr, dtype=np.float64, copy=True),
        X_pending=None if pending_arr is None else pending_arr.copy(),
        acq_seed=int(acq_seed), sample_shape=int(sample_shape),
        infeasible_penalty=float(infeasible_penalty), library_versions=versions,
        timing_s=time.perf_counter() - started)


def evaluate_constrained_candidates(acquisition_result, X, *, n_samples: int = SAMPLER_SAMPLE_SHAPE,
                                    seed: int = 0) -> ConstrainedCandidateEvaluation:
    """Evaluate acquisition values and sampled feasibility for a candidate pool.

    The public ``values`` are ``-inf`` wherever no posterior sample satisfies every constraint.
    ``feasibility_probability`` is the empirical fraction of feasible posterior samples (a model
    diagnostic, not a calibrated probability).  Non-finite posteriors or acquisition values make
    the whole evaluation unavailable.
    """
    started = time.perf_counter()
    if acquisition_result is None or getattr(acquisition_result, "status", None) != STATUS_OK \
            or getattr(acquisition_result, "acq", None) is None:
        return ConstrainedCandidateEvaluation(
            status=STATUS_UNAVAILABLE, reason=REASON_INVALID_MODEL,
            detail="no ok constrained acquisition", n_samples=int(n_samples), seed=int(seed))
    try:
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.ndim != 2 or not np.all(np.isfinite(arr)):
            raise ValueError(f"candidate X must be finite 2-D, got shape {arr.shape}")
    except (TypeError, ValueError) as exc:
        return ConstrainedCandidateEvaluation(
            status=STATUS_UNAVAILABLE, reason=REASON_INVALID_CANDIDATES, detail=str(exc),
            n_samples=int(n_samples), seed=int(seed))

    engine, import_error = _import_acq_engine()
    if engine is None:
        return ConstrainedCandidateEvaluation(
            status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING, detail=import_error,
            n=int(arr.shape[0]), n_samples=int(n_samples), seed=int(seed))
    torch = engine["torch"]
    try:
        from .model import NUM_THREADS
        torch.set_num_threads(NUM_THREADS)
    except Exception:  # noqa: BLE001
        pass

    names = tuple(getattr(acquisition_result, "output_names", ()) or ())
    con_idx = list(getattr(acquisition_result, "constraint_indices", ()) or ())
    obj_idx = list(getattr(acquisition_result, "objective_indices", ()) or ())
    thresholds = np.asarray(getattr(acquisition_result, "thresholds", ()), dtype=np.float64)
    try:
        torch.manual_seed(int(seed))
        with torch.no_grad():
            tensor = torch.as_tensor(arr, dtype=torch.float64).unsqueeze(-2)  # (b,1,d)
            acq_values = acquisition_result.acq(tensor).detach().cpu().numpy().reshape(-1)
            posterior = acquisition_result.model_result.model.posterior(
                torch.as_tensor(arr, dtype=torch.float64), observation_noise=False)
            samples = posterior.rsample(torch.Size([int(n_samples)])).detach().cpu().numpy()
    except Exception as exc:  # noqa: BLE001 - a failed posterior/acquisition yields nothing
        return ConstrainedCandidateEvaluation(
            status=STATUS_UNAVAILABLE, reason=REASON_ACQUISITION_FAILED,
            detail=f"constrained evaluation failed: {type(exc).__name__}: {exc}",
            n=int(arr.shape[0]), n_samples=int(n_samples), seed=int(seed))

    if samples.shape[-1] != len(names):
        return ConstrainedCandidateEvaluation(
            status=STATUS_UNAVAILABLE, reason=REASON_NONFINITE_POSTERIOR,
            detail=f"posterior sample shape {samples.shape} does not match {len(names)} outputs",
            n=int(arr.shape[0]), n_samples=int(n_samples), seed=int(seed))
    if not np.all(np.isfinite(samples)) or not np.all(np.isfinite(acq_values)):
        return ConstrainedCandidateEvaluation(
            status=STATUS_UNAVAILABLE, reason=REASON_NONFINITE_POSTERIOR,
            detail="posterior samples or acquisition values contain NaN/Inf",
            n=int(arr.shape[0]), n_samples=int(n_samples), seed=int(seed))

    constraint_samples = samples[..., con_idx] - thresholds  # [S, q, k]
    feasible = np.all(constraint_samples <= 0.0, axis=-1)    # [S, q]
    feasibility_probability = feasible.mean(axis=0)          # [q]
    objective_mean = samples[..., obj_idx].sum(axis=-1).mean(axis=0)  # [q]
    constraint_mean = constraint_samples.mean(axis=0)        # [q, k]
    constraint_max = constraint_samples.max(axis=0)          # [q, k]
    values = np.where(feasibility_probability > 0.0, acq_values, -np.inf)

    flags: list[str] = []
    if np.any(feasibility_probability <= 0.0):
        flags.append("infeasible_candidates_present")
    if not np.all(np.isfinite(values)):
        flags.append("infeasible_values_are_neg_inf")
    return ConstrainedCandidateEvaluation(
        status=STATUS_OK, reason=REASON_OK, values=values,
        acquisition_values=acq_values, feasibility_probability=feasibility_probability,
        feasible_mask=feasibility_probability > 0.0, objective_mean=objective_mean,
        constraint_mean=constraint_mean, constraint_max=constraint_max,
        n=int(arr.shape[0]), n_samples=int(n_samples),
        infeasible_count=int(np.sum(feasibility_probability <= 0.0)), seed=int(seed),
        flags=tuple(flags))


def select_constrained_candidate(evaluation, *,
                                 min_feasibility_probability: float = 0.5
                                 ) -> ConstrainedSelection:
    """Pick the highest acquisition value among sufficiently feasible candidates.

    Infeasible candidates are refused (``-inf`` values); when none meets the sampled feasibility
    threshold the selection is unavailable.  This is advisory research output, not a switch.
    """
    if evaluation is None or getattr(evaluation, "status", None) != STATUS_OK \
            or getattr(evaluation, "values", None) is None:
        return ConstrainedSelection(status=STATUS_UNAVAILABLE, reason=REASON_INVALID_MODEL,
                                    detail="no ok candidate evaluation")
    values = np.asarray(evaluation.values, dtype=np.float64).reshape(-1)
    probs = np.asarray(evaluation.feasibility_probability, dtype=np.float64).reshape(-1)
    threshold = float(min_feasibility_probability)
    eligible = np.isfinite(values) & (probs >= threshold)
    if not bool(eligible.any()):
        return ConstrainedSelection(
            status=STATUS_UNAVAILABLE, reason=REASON_NO_FEASIBLE_CANDIDATE,
            detail=f"no candidate has feasibility probability >= {threshold:g}",
            values=values, eligibility_threshold=threshold)
    candidates = np.flatnonzero(eligible)
    best = candidates[int(np.argmax(values[candidates]))]
    return ConstrainedSelection(
        status=STATUS_OK, reason=REASON_OK, candidate_index=int(best),
        value=float(values[best]), feasibility_probability=float(probs[best]),
        values=values, eligibility_threshold=threshold)


__all__ = [
    "RESEARCH_POLICY",
    "RESEARCH_ONLY",
    "OBJECTIVE_VERSION",
    "MARGIN_CONVENTION",
    "ACQUISITION_POLICY",
    "SAMPLER_SAMPLE_SHAPE",
    "INFEASIBLE_PENALTY",
    "STATUS_OK",
    "STATUS_UNAVAILABLE",
    "REASON_OK",
    "REASON_INVALID_MODEL",
    "REASON_NO_CONSTRAINTS",
    "REASON_DUPLICATE_CONSTRAINT",
    "REASON_CONSTRAINT_OUTPUT_MISSING",
    "REASON_UNSUPPORTED_MISSING_POLICY",
    "REASON_NO_OBJECTIVE_OUTPUTS",
    "REASON_INVALID_CANDIDATES",
    "REASON_CAPABILITY_MISSING",
    "REASON_ACQUISITION_FAILED",
    "REASON_NONFINITE_ACQUISITION",
    "REASON_NO_FEASIBLE_CANDIDATE",
    "REASON_NONFINITE_POSTERIOR",
    "PhysicalConstraint",
    "ConstrainedAcquisitionResult",
    "ConstrainedCandidateEvaluation",
    "ConstrainedSelection",
    "constraint_margins",
    "feasibility_from_samples",
    "build_constrained_acquisition",
    "evaluate_constrained_candidates",
    "select_constrained_candidate",
]
