"""RESEARCH-ONLY physical-metric composite model (v11 CD block).

This module is a research instrument, not a production proposal policy.  It fits one independent
Gaussian process per **physical** CD output produced by :mod:`hornlab_search.metrics.cd`
(``cd_lw_db``, ``cd_di_std_db``, ``cd_nacc``, ``offaxis_smooth_db``) and evaluates nonlinear
transforms on posterior **samples** rather than on the posterior mean.  It is deliberately not
reachable from :data:`hornlab_search.bo.policy.PROPOSAL_POLICIES`; every result carries
``research_only=True`` and ``policy="physical_composite_research_v1"``.

What is real here
-----------------
* The four metrics are exactly the fields :func:`hornlab_search.metrics.cd.cd_metrics` returns.
  No metric is invented and no missing value is filled.
* Contribution arithmetic is imported from the canonical v11 resolver and the validated
  ``V11Params`` object (:func:`hornlab_search.objective.scalar_v11.resolve_v11_weights`,
  ``_norm_cd``, ``_norm_nacc``).  Weights/tolerances are never hard-coded here.
* A full ``J`` is reconstructed only from a complete supplied contribution set.  The CD terms
  alone are a partial contribution and are reported as such.

Explicit non-goals
------------------
* H/V coverage, loading and other v9/v10 terms are **future candidates**, not implemented here:
  they are not produced by ``metrics/cd.py`` and mapping them onto a CD physical model would mix
  two different measurement contracts.
* No calibrated uncertainty claim: GP intervals are a model diagnostic.  No acoustic improvement
  claim: these are predictions, not solved responses.
* v11 CD scoring is not a universal requirement.  Nothing in this module imposes CD scoring on a
  non-CD brief; the caller must explicitly opt in by passing a v11 ``V11Params``.

Torch/BoTorch/GPyTorch are imported lazily so importing this module is cheap and does not require
the optional bayes engine.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .metric_contracts import sha256_json

RESEARCH_POLICY = "physical_composite_research_v1"
RESEARCH_ONLY = True
OBJECTIVE_VERSION = 11
POLICY_LABEL = (
    "research-only physical-metric composite model; not a production proposal policy and not "
    "registrable in bo.policy.PROPOSAL_POLICIES")

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_UNAVAILABLE = "unavailable"

REASON_OK = "ok"
REASON_UNSUPPORTED_VERSION = "unsupported_objective_version"
REASON_PARAMS_REQUIRED = "params_required"
REASON_CD_STATUS = "cd_status_unavailable"
REASON_CUTS_FALLBACK = "cd_cuts_fallback"
REASON_MISSING_METRIC = "missing_metric"
REASON_NONFINITE_METRIC = "nonfinite_metric"
REASON_NACC_RANGE = "cd_nacc_out_of_range"
REASON_MISSING_CONTRIBUTION = "missing_contribution"
REASON_NONFINITE_CONTRIBUTION = "nonfinite_contribution"
REASON_INVALID_TRAINING_DATA = "invalid_training_data"
REASON_CAPABILITY_MISSING = "capability_missing"
REASON_OUTPUT_FIT_FAILED = "output_fit_failed"
REASON_MODEL_UNAVAILABLE = "model_unavailable"
REASON_INSUFFICIENT_DATA = "insufficient_data"

#: ``metrics.cd`` source/band contract.  ``source`` names which measurement path can carry the
#: metric: a balloon, H/V cuts, or either (with the cuts path explicitly flagged).
_SPEC_ROWS = (
    ("cd_lw_db", "cd_lw", "dB", "either", (700.0, 8000.0), "refuse"),
    ("cd_di_std_db", "cd_di_std", "dB", "either", (700.0, 8000.0), "refuse"),
    ("cd_nacc", "cd_nacc", "ratio", "cuts", (700.0, 8000.0), "refuse"),
    ("offaxis_smooth_db", "offaxis_smooth", "dB", "cuts", (2500.0, 8000.0), "refuse"),
)


@dataclass(frozen=True)
class PhysicalMetricSpec:
    """Frozen physical metric definition (physical units, source, band, missing policy)."""

    metric_key: str
    term_key: str
    units: str
    source: str
    frequency_support: tuple[float, float]
    missing_policy: str
    objective_version: int = OBJECTIVE_VERSION

    def to_dict(self) -> dict:
        return {
            "objective_version": int(self.objective_version),
            "metric_key": self.metric_key,
            "term_key": self.term_key,
            "units": self.units,
            "source": self.source,
            "frequency_support": [float(self.frequency_support[0]),
                                  float(self.frequency_support[1])],
            "missing_policy": self.missing_policy,
        }

    @property
    def identity_hash(self) -> str:
        """SHA-256 over the canonical JSON of this metric definition."""
        return sha256_json(self.to_dict())


PHYSICAL_METRIC_SPECS: tuple[PhysicalMetricSpec, ...] = tuple(
    PhysicalMetricSpec(metric_key=mk, term_key=tk, units=u, source=s, frequency_support=band,
                       missing_policy=mp)
    for mk, tk, u, s, band, mp in _SPEC_ROWS)
PHYSICAL_METRIC_BY_KEY = {spec.metric_key: spec for spec in PHYSICAL_METRIC_SPECS}
PHYSICAL_TERM_KEYS = tuple(spec.term_key for spec in PHYSICAL_METRIC_SPECS)
PHYSICAL_SCHEMA_HASH = sha256_json({
    "objective_version": OBJECTIVE_VERSION,
    "metrics": [spec.to_dict() for spec in PHYSICAL_METRIC_SPECS],
})

#: Documented future candidates.  They are intentionally NOT implemented: ``metrics/cd.py`` does
#: not produce them, so they would require a different measurement contract.
FUTURE_METRIC_CANDIDATES = ("h_coverage_deg", "v_coverage_deg", "loading_re_z")


@dataclass(frozen=True)
class PhysicalContributionResult:
    """Tagged contribution extraction from one ``cd_metrics`` payload."""

    status: str
    reason: str
    detail: str | None = None
    objective_version: int = OBJECTIVE_VERSION
    contributions: tuple[float, ...] = ()
    contributions_by_term: dict = field(default_factory=dict)
    metric_values: dict = field(default_factory=dict)
    weights: dict = field(default_factory=dict)
    tolerances: dict = field(default_factory=dict)
    cd_status: str | None = None
    cuts_fallback: bool = False
    quality_flags: tuple[str, ...] = ()
    schema_hash: str = PHYSICAL_SCHEMA_HASH
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "objective_version": int(self.objective_version),
            "contributions": [float(v) for v in self.contributions],
            "contributions_by_term": {k: float(v) for k, v in self.contributions_by_term.items()},
            "metric_values": {k: float(v) for k, v in self.metric_values.items()},
            "weights": {k: float(v) for k, v in self.weights.items()},
            "tolerances": {k: float(v) for k, v in self.tolerances.items()},
            "cd_status": self.cd_status,
            "cuts_fallback": bool(self.cuts_fallback),
            "quality_flags": list(self.quality_flags),
            "schema_hash": self.schema_hash,
            "research_only": bool(self.research_only),
            "policy": self.policy,
        }


@dataclass(frozen=True)
class PhysicalJReconstruction:
    """Result of reconstructing a full physical J from supplied term contributions."""

    status: str
    partial: bool
    reason: str = ""
    j: float | None = None
    j_partial_sum: float | None = None
    required_terms: tuple[str, ...] = ()
    supplied_terms: tuple[str, ...] = ()
    missing_terms: tuple[str, ...] = ()
    objective_version: int = OBJECTIVE_VERSION
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK and not self.partial

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "partial": bool(self.partial),
            "reason": self.reason,
            "j": self.j,
            "j_partial_sum": self.j_partial_sum,
            "required_terms": list(self.required_terms),
            "supplied_terms": list(self.supplied_terms),
            "missing_terms": list(self.missing_terms),
            "objective_version": int(self.objective_version),
            "research_only": bool(self.research_only),
            "policy": self.policy,
        }


def _unavailable(reason: str, detail: str | None = None, *,
                 objective_version: int = OBJECTIVE_VERSION,
                 cd_status: str | None = None, cuts_fallback: bool = False,
                 quality_flags: tuple[str, ...] = (),
                 contributions: tuple[float, ...] = (),
                 contributions_by_term: Mapping[str, float] | None = None,
                 metric_values: Mapping[str, float] | None = None,
                 weights: Mapping[str, float] | None = None,
                 tolerances: Mapping[str, float] | None = None) -> PhysicalContributionResult:
    return PhysicalContributionResult(
        status=STATUS_UNAVAILABLE, reason=reason, detail=detail,
        objective_version=int(objective_version),
        contributions=tuple(float(v) for v in contributions),
        contributions_by_term={str(k): float(v) for k, v in (contributions_by_term or {}).items()},
        metric_values={str(k): float(v) for k, v in (metric_values or {}).items()},
        weights={str(k): float(v) for k, v in (weights or {}).items()},
        tolerances={str(k): float(v) for k, v in (tolerances or {}).items()},
        cd_status=cd_status, cuts_fallback=bool(cuts_fallback),
        quality_flags=tuple(quality_flags))


def _finite_float(value, key: str) -> tuple[float | None, str | None]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None, f"{REASON_NONFINITE_METRIC}:{key}"
    if not math.isfinite(v):
        return None, f"{REASON_NONFINITE_METRIC}:{key}"
    return v, None


def extract_physical_contributions(cd_raw, *, params, objective_version: int = OBJECTIVE_VERSION,
                                   weights: Mapping[str, float] | None = None,
                                   allow_cd_cuts_fallback: bool = False
                                   ) -> PhysicalContributionResult:
    """Extract the four physical v11 contributions from a ``cd_metrics`` payload.

    ``cd_raw`` is the exact dict returned by :func:`hornlab_search.metrics.cd.cd_metrics`.
    ``params`` must be a validated :class:`~hornlab_search.objective.scalar_v11.V11Params`.
    Contributions are in canonical J contribution units computed with the canonical resolver:
    ``w_lw * cd_lw_db / tol_lw``, ``w_di * cd_di_std_db / tol_di``,
    ``w_nacc * (1 - cd_nacc) / tol_nacc`` and ``w_off * offaxis_smooth_db / tol_off``.

    Missing keys, non-finite values, ``cd_status == "unmeasurable"`` and a cuts fallback (unless
    explicitly allowed and flagged) are refusals.  A value is never filled or imputed.
    """
    if int(objective_version) != OBJECTIVE_VERSION:
        return _unavailable(REASON_UNSUPPORTED_VERSION,
                            f"physical composite is defined for objective v11 only, got "
                            f"{objective_version!r}", objective_version=objective_version)
    if params is None:
        return _unavailable(REASON_PARAMS_REQUIRED,
                            "a validated V11Params instance is required; physical contributions "
                            "are never computed from hard-coded weights")
    try:
        from ..objective.scalar_v11 import (_norm_cd, _norm_nacc, CD_STATUS_CODES,
                                            resolve_v11_weights)
    except Exception as exc:  # noqa: BLE001 - canonical scorer import failure is a refusal
        return _unavailable(REASON_CAPABILITY_MISSING,
                            f"canonical v11 scorer is unavailable: {type(exc).__name__}: {exc}")

    if not hasattr(params, "cd"):
        return _unavailable(REASON_PARAMS_REQUIRED,
                            f"params must be V11Params (has objective.cd), got {type(params).__name__}")
    if not isinstance(cd_raw, Mapping):
        return _unavailable(REASON_MISSING_METRIC, f"cd_raw must be a mapping, got {type(cd_raw).__name__}")

    status = cd_raw.get("cd_status")
    if status not in CD_STATUS_CODES:
        return _unavailable(REASON_CD_STATUS,
                            f"unknown or missing cd_status {status!r}")
    if status == "unmeasurable":
        return _unavailable(REASON_CD_STATUS, "the CD block is unmeasurable", cd_status=status)
    cuts_fallback = status == "cuts_fallback"
    if cuts_fallback and not allow_cd_cuts_fallback:
        return _unavailable(REASON_CUTS_FALLBACK,
                            "cuts-fallback CD is refused by default; pass "
                            "allow_cd_cuts_fallback=True to keep the row (flagged)",
                            cd_status=status, cuts_fallback=True)

    w = resolve_v11_weights(dict(weights) if weights is not None else None, params)
    cd = params.cd
    tolerances = {
        "cd_lw": float(cd.lw["tolerance_db"]),
        "cd_di_std": float(cd.di_std["tolerance_db"]),
        "cd_nacc": float(cd.nacc["tolerance"]),
        "offaxis_smooth": float(cd.offaxis["tolerance_db"]),
    }

    metric_values: dict[str, float] = {}
    for spec in PHYSICAL_METRIC_SPECS:
        if spec.metric_key not in cd_raw:
            return _unavailable(REASON_MISSING_METRIC, f"cd_raw has no {spec.metric_key!r}",
                                cd_status=status, cuts_fallback=cuts_fallback)
        value, error = _finite_float(cd_raw[spec.metric_key], spec.metric_key)
        if error is not None or value is None:
            return _unavailable(error or REASON_NONFINITE_METRIC,
                                f"{spec.metric_key}={cd_raw.get(spec.metric_key)!r}",
                                cd_status=status, cuts_fallback=cuts_fallback)
        if spec.metric_key == "cd_nacc" and not (-1e-9 <= value <= 1.0 + 1e-9):
            return _unavailable(REASON_NACC_RANGE,
                                f"cd_nacc={value!r} is outside the physical [0, 1] ratio",
                                cd_status=status, cuts_fallback=cuts_fallback)
        metric_values[spec.metric_key] = float(value)

    # The exact canonical arithmetic: normalise with the scorer's own helpers, then weight.
    normalised = {
        "cd_lw": _norm_cd(metric_values["cd_lw_db"], tolerances["cd_lw"]),
        "cd_di_std": _norm_cd(metric_values["cd_di_std_db"], tolerances["cd_di_std"]),
        "cd_nacc": _norm_nacc(metric_values["cd_nacc"], tolerances["cd_nacc"]),
        "offaxis_smooth": _norm_cd(metric_values["offaxis_smooth_db"], tolerances["offaxis_smooth"]),
    }
    contributions_by_term = {
        term: float(w[term]) * float(normalised[term]) for term in PHYSICAL_TERM_KEYS
    }
    contributions = tuple(contributions_by_term[term] for term in PHYSICAL_TERM_KEYS)
    flags: list[str] = []
    if cuts_fallback:
        flags.append("cd_cuts_fallback")
    if not all(math.isfinite(v) for v in contributions):
        return _unavailable(REASON_NONFINITE_CONTRIBUTION,
                            "a canonical contribution is non-finite",
                            cd_status=status, cuts_fallback=cuts_fallback,
                            quality_flags=tuple(flags), metric_values=metric_values,
                            weights=w, tolerances=tolerances)
    return PhysicalContributionResult(
        status=STATUS_OK, reason=REASON_OK, cd_status=status,
        contributions=contributions, contributions_by_term=contributions_by_term,
        metric_values=metric_values, weights={k: float(v) for k, v in w.items()},
        tolerances=tolerances, cuts_fallback=cuts_fallback, quality_flags=tuple(flags))


def reconstruct_physical_j(*, contributions: Mapping[str, float] | None = None,
                           cd_contributions: Mapping[str, float] | None = None,
                           base_contributions: Mapping[str, float] | None = None,
                           params=None) -> PhysicalJReconstruction:
    """Reconstruct a full physical ``J`` from term contributions, or report what is missing.

    Contribution keys are canonical term keys in J contribution units (the values the canonical
    v11 scorer multiplies its weights by).  ``cd_contributions`` carries the four CD term keys;
    ``base_contributions`` carries the active v9/v10 term keys (``params.weighted_keys()``).
    ``contributions`` is the merged mapping and is convenient when the caller already has both.

    A full J is returned (``status="ok"``, ``partial=False``) only when a validated ``params`` is
    supplied and every required base **and** CD term is present and finite.  Otherwise the result
    is ``status="partial"`` with ``j=None`` and the missing term names; ``j_partial_sum`` records
    the sum of the supplied terms as a diagnostic.  CD terms alone can never claim a full J.
    """
    merged: dict[str, float] = {}
    for source in (contributions, base_contributions, cd_contributions):
        if source is None:
            continue
        if not isinstance(source, Mapping):
            return PhysicalJReconstruction(status=STATUS_UNAVAILABLE, partial=True,
                                           reason="contributions_must_be_mapping")
        for key, value in source.items():
            try:
                v = float(value)
            except (TypeError, ValueError):
                return PhysicalJReconstruction(status=STATUS_UNAVAILABLE, partial=True,
                                               reason=f"{REASON_NONFINITE_CONTRIBUTION}:{key}")
            if not math.isfinite(v):
                return PhysicalJReconstruction(status=STATUS_UNAVAILABLE, partial=True,
                                               reason=f"{REASON_NONFINITE_CONTRIBUTION}:{key}")
            merged[str(key)] = float(v)

    if params is not None and hasattr(params, "weighted_keys"):
        required_base = tuple(str(k) for k in params.weighted_keys())
    else:
        required_base = ()
    required = tuple(dict.fromkeys(required_base + PHYSICAL_TERM_KEYS))
    missing = tuple(k for k in required if k not in merged)
    supplied = tuple(k for k in required if k in merged)
    partial_sum = float(math.fsum(merged.values()))
    if params is None:
        return PhysicalJReconstruction(
            status=STATUS_PARTIAL, partial=True, reason=REASON_PARAMS_REQUIRED,
            j=None, j_partial_sum=partial_sum, required_terms=required,
            supplied_terms=supplied, missing_terms=missing)
    if missing:
        return PhysicalJReconstruction(
            status=STATUS_PARTIAL, partial=True, reason=REASON_MISSING_CONTRIBUTION,
            j=None, j_partial_sum=partial_sum, required_terms=required,
            supplied_terms=supplied, missing_terms=missing)
    return PhysicalJReconstruction(
        status=STATUS_OK, partial=False, reason=REASON_OK, j=partial_sum,
        j_partial_sum=partial_sum, required_terms=required, supplied_terms=supplied,
        missing_terms=())


# ---------------------------------------------------------------------------- research model


@dataclass(frozen=True)
class PhysicalModelFitResult:
    """Tagged research-only fit result (one independent GP per physical output)."""

    status: str
    reason: str
    detail: str | None = None
    model: Any = field(default=None, repr=False, compare=False)
    output_names: tuple[str, ...] = ()
    metric_specs: tuple[dict, ...] = ()
    d: int | None = None
    n: int | None = None
    train_X: np.ndarray | None = field(default=None, repr=False, compare=False)
    per_output: tuple[dict, ...] = ()
    seed: int = 0
    timing_s: float | None = None
    library_versions: dict = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    schema_hash: str = PHYSICAL_SCHEMA_HASH
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "output_names": list(self.output_names),
            "metric_specs": [dict(v) for v in self.metric_specs],
            "d": self.d,
            "n": self.n,
            "per_output": [dict(v) for v in self.per_output],
            "seed": int(self.seed),
            "timing_s": self.timing_s,
            "library_versions": dict(self.library_versions),
            "warnings": list(self.warnings),
            "schema_hash": self.schema_hash,
            "research_only": bool(self.research_only),
            "policy": self.policy,
        }


def _physical_unavailable(reason: str, detail: str | None = None, *, d=None, n=None,
                          output_names: Sequence[str] = (), per_output: Sequence[dict] = (),
                          seed: int = 0, timing_s: float | None = None,
                          warnings_seen: Sequence[str] = ()) -> PhysicalModelFitResult:
    return PhysicalModelFitResult(
        status=STATUS_UNAVAILABLE, reason=reason, detail=detail, model=None,
        output_names=tuple(output_names), metric_specs=(), d=d, n=n, train_X=None,
        per_output=tuple(per_output), seed=int(seed), timing_s=timing_s,
        library_versions={}, warnings=tuple(warnings_seen))


def _resolve_specs(output_names: Sequence[str] | None,
                   specs: Sequence[PhysicalMetricSpec] | None) -> tuple[PhysicalMetricSpec, ...]:
    if specs is None:
        if output_names is None:
            return PHYSICAL_METRIC_SPECS
        return tuple(PHYSICAL_METRIC_BY_KEY[str(name)] for name in output_names)
    try:
        return tuple(specs)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"specs must be an iterable of PhysicalMetricSpec, got {specs!r}") from exc


def fit_physical_model(X, Y_phys, *, output_names: Sequence[str] | None = None,
                       specs: Sequence[PhysicalMetricSpec] | None = None, seed: int = 0,
                       max_iters: int = 100) -> PhysicalModelFitResult:
    """Fit one GP per physical output in physical units (RESEARCH ONLY).

    The model uses the same independent-output patterns as
    :func:`hornlab_search.bo.metric_model.fit_metric_model` (Matérn-5/2 ARD, per-output
    standardisation, fixed noise floor, constant outputs parked flat) but is tagged
    ``research_only=True`` and must never be added to ``PROPOSAL_POLICIES``.
    """
    started = time.perf_counter()
    try:
        chosen = _resolve_specs(output_names, specs)
    except KeyError as exc:
        return _physical_unavailable(REASON_INVALID_TRAINING_DATA,
                                     f"unknown physical output {exc.args[0]!r}", seed=seed,
                                     timing_s=time.perf_counter() - started)
    names = tuple(spec.metric_key for spec in chosen)
    if not names:
        return _physical_unavailable(REASON_INSUFFICIENT_DATA, "no physical outputs requested",
                                     seed=seed, timing_s=time.perf_counter() - started)

    try:
        X_arr = np.array(X, dtype=np.float64, copy=True)
        Y_arr = np.array(Y_phys, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as exc:
        return _physical_unavailable(REASON_INVALID_TRAINING_DATA,
                                     f"X/Y are not numeric: {exc}", seed=seed,
                                     output_names=names,
                                     timing_s=time.perf_counter() - started)
    if X_arr.ndim != 2 or Y_arr.ndim != 2 or X_arr.shape[0] != Y_arr.shape[0]:
        return _physical_unavailable(REASON_INVALID_TRAINING_DATA,
                                     f"X/Y must be 2-D with matching rows, got "
                                     f"X{X_arr.shape}, Y{Y_arr.shape}", seed=seed,
                                     output_names=names,
                                     timing_s=time.perf_counter() - started)
    n, d = int(X_arr.shape[0]), int(X_arr.shape[1])
    if Y_arr.shape[1] != len(names):
        return _physical_unavailable(REASON_OUTPUT_FIT_FAILED,
                                     f"Y has {Y_arr.shape[1]} columns, expected {len(names)}",
                                     d=d, n=n, output_names=names, seed=seed,
                                     timing_s=time.perf_counter() - started)
    if n < 2:
        return _physical_unavailable(REASON_INSUFFICIENT_DATA,
                                     f"at least two observations are required, got n={n}",
                                     d=d, n=n, output_names=names, seed=seed,
                                     timing_s=time.perf_counter() - started)
    if not np.all(np.isfinite(X_arr)) or not np.all(np.isfinite(Y_arr)):
        return _physical_unavailable(REASON_INVALID_TRAINING_DATA,
                                     "X/Y contain NaN/Inf", d=d, n=n, output_names=names,
                                     seed=seed, timing_s=time.perf_counter() - started)
    if np.any((X_arr < 0.0) | (X_arr > 1.0)):
        return _physical_unavailable(REASON_INVALID_TRAINING_DATA,
                                     "X contains values outside [0,1]", d=d, n=n,
                                     output_names=names, seed=seed,
                                     timing_s=time.perf_counter() - started)

    try:
        from . import metric_model
        engine, import_error = metric_model._import_engine()
    except Exception as exc:  # noqa: BLE001
        return _physical_unavailable(REASON_CAPABILITY_MISSING,
                                     f"optional BoTorch engine is unavailable: {exc}",
                                     d=d, n=n, output_names=names, seed=seed,
                                     timing_s=time.perf_counter() - started)
    if engine is None:
        return _physical_unavailable(REASON_CAPABILITY_MISSING,
                                     f"optional BoTorch engine is unavailable: {import_error}",
                                     d=d, n=n, output_names=names, seed=seed,
                                     timing_s=time.perf_counter() - started)

    torch = engine["torch"]
    try:
        from .model import NUM_THREADS, library_versions
        torch.set_num_threads(NUM_THREADS)
        versions = library_versions()
    except Exception:  # noqa: BLE001
        versions = {}
    X_t = torch.as_tensor(X_arr, dtype=torch.float64)
    models = []
    records: list[dict] = []
    all_warnings: list[str] = []
    for i, name in enumerate(names):
        y_t = torch.as_tensor(Y_arr[:, i:i + 1], dtype=torch.float64)
        try:
            record, output_model, warnings_seen = metric_model._fit_one_output(
                engine, X_t, y_t, index=i, output_name=name, d=d, n=n, seed=int(seed),
                max_iters=int(max_iters))
        except Exception as exc:  # noqa: BLE001 - never let an output failure escape
            return _physical_unavailable(f"{REASON_OUTPUT_FIT_FAILED}:{name}",
                                         f"physical output {name!r} failed: "
                                         f"{type(exc).__name__}: {exc}", d=d, n=n,
                                         output_names=names, per_output=tuple(records),
                                         seed=seed, timing_s=time.perf_counter() - started,
                                         warnings_seen=tuple(all_warnings))
        records.append(record)
        models.append(output_model)
        all_warnings.extend(warnings_seen)

    try:
        model = engine["ModelListGP"](*models)
        model.eval()
        with torch.no_grad():
            posterior = model.posterior(X_t, observation_noise=False)
            mean = posterior.mean.detach().cpu().numpy()
            variance = posterior.variance.detach().cpu().numpy()
        if mean.shape != (n, len(names)) or variance.shape != (n, len(names)):
            raise RuntimeError(f"posterior shapes {mean.shape}/{variance.shape} != "
                               f"{(n, len(names))}")
        if not (np.all(np.isfinite(mean)) and np.all(np.isfinite(variance))):
            raise RuntimeError("posterior contains NaN/Inf")
    except Exception as exc:  # noqa: BLE001
        return _physical_unavailable(REASON_MODEL_UNAVAILABLE,
                                     f"combined physical posterior failed: "
                                     f"{type(exc).__name__}: {exc}", d=d, n=n,
                                     output_names=names, per_output=tuple(records), seed=seed,
                                     timing_s=time.perf_counter() - started,
                                     warnings_seen=tuple(all_warnings))

    return PhysicalModelFitResult(
        status=STATUS_OK, reason=REASON_OK, model=model, output_names=names,
        metric_specs=tuple(spec.to_dict() for spec in chosen), d=d, n=n,
        train_X=np.array(X_arr, dtype=np.float64, copy=True), per_output=tuple(records),
        seed=int(seed), timing_s=time.perf_counter() - started, library_versions=versions,
        warnings=tuple(all_warnings), schema_hash=sha256_json({
            "objective_version": OBJECTIVE_VERSION,
            "metrics": [spec.to_dict() for spec in chosen],
        }))


@dataclass(frozen=True)
class PhysicalTransformResult:
    """Posterior-sample evaluation of a nonlinear transform (never applied to the mean)."""

    status: str
    reason: str
    detail: str | None = None
    sampled_mean: np.ndarray | None = None
    sampled_sd: np.ndarray | None = None
    transform_of_mean: np.ndarray | None = None
    nonlinear_gap: np.ndarray | None = None
    n_samples: int = 0
    seed: int = 0
    flags: tuple[str, ...] = ()
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


def evaluate_physical_transform(model_result, X, transform: Callable,
                                *, n_samples: int = 128, seed: int = 0
                                ) -> PhysicalTransformResult:
    """Evaluate ``transform`` on posterior **samples** of the physical outputs.

    ``transform`` receives a tensor of shape ``[S, q, m]`` (sample, query, output) and must return
    a tensor of shape ``[S, q]`` or ``[S, q, k]``.  The returned ``sampled_mean`` is the mean of
    the per-sample transform; ``transform_of_mean`` is the transform of the posterior mean and is
    reported only as a diagnostic gap.  Composite decisions must use the sampled value.
    """
    if model_result is None or getattr(model_result, "status", None) != STATUS_OK \
            or getattr(model_result, "model", None) is None:
        return PhysicalTransformResult(status=STATUS_UNAVAILABLE,
                                       reason=REASON_MODEL_UNAVAILABLE,
                                       detail="no fitted physical model")
    try:
        from . import metric_model
        engine, import_error = metric_model._import_engine()
    except Exception as exc:  # noqa: BLE001
        return PhysicalTransformResult(status=STATUS_UNAVAILABLE,
                                       reason=REASON_CAPABILITY_MISSING,
                                       detail=f"optional BoTorch engine is unavailable: {exc}")
    if engine is None:
        return PhysicalTransformResult(status=STATUS_UNAVAILABLE,
                                       reason=REASON_CAPABILITY_MISSING,
                                       detail=f"optional BoTorch engine is unavailable: {import_error}")
    torch = engine["torch"]
    try:
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        expected_d = int(getattr(model_result, "d", 0) or 0)
        if arr.ndim != 2 or (expected_d and arr.shape[1] != expected_d):
            raise ValueError(f"unexpected candidate shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("candidate X contains NaN/Inf")
        try:
            from .model import NUM_THREADS
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        torch.manual_seed(int(seed))
        with torch.no_grad():
            posterior = model_result.model.posterior(
                torch.as_tensor(arr, dtype=torch.float64), observation_noise=False)
            samples = posterior.rsample(torch.Size([int(n_samples)]))
            values = transform(samples)
            plug_in = transform(posterior.mean)
        values_np = values.detach().cpu().numpy()
        plug_np = plug_in.detach().cpu().numpy()
    except Exception as exc:  # noqa: BLE001
        return PhysicalTransformResult(status=STATUS_UNAVAILABLE,
                                       reason=REASON_MODEL_UNAVAILABLE,
                                       detail=f"sample transform failed: {type(exc).__name__}: {exc}")

    sampled_mean = values_np.mean(axis=0)
    sampled_sd = values_np.std(axis=0)
    flags: list[str] = []
    if not (np.all(np.isfinite(sampled_mean)) and np.all(np.isfinite(sampled_sd))
            and np.all(np.isfinite(plug_np))):
        flags.append("nonfinite_transform")
    return PhysicalTransformResult(
        status=STATUS_OK, reason=REASON_OK, sampled_mean=sampled_mean,
        sampled_sd=sampled_sd, transform_of_mean=plug_np,
        nonlinear_gap=sampled_mean - plug_np, n_samples=int(n_samples), seed=int(seed),
        flags=tuple(flags))


__all__ = [
    "RESEARCH_POLICY",
    "RESEARCH_ONLY",
    "OBJECTIVE_VERSION",
    "POLICY_LABEL",
    "STATUS_OK",
    "STATUS_PARTIAL",
    "STATUS_UNAVAILABLE",
    "REASON_OK",
    "REASON_UNSUPPORTED_VERSION",
    "REASON_PARAMS_REQUIRED",
    "REASON_CD_STATUS",
    "REASON_CUTS_FALLBACK",
    "REASON_MISSING_METRIC",
    "REASON_NONFINITE_METRIC",
    "REASON_NACC_RANGE",
    "REASON_MISSING_CONTRIBUTION",
    "REASON_NONFINITE_CONTRIBUTION",
    "REASON_INVALID_TRAINING_DATA",
    "REASON_CAPABILITY_MISSING",
    "REASON_OUTPUT_FIT_FAILED",
    "REASON_MODEL_UNAVAILABLE",
    "REASON_INSUFFICIENT_DATA",
    "PhysicalMetricSpec",
    "PHYSICAL_METRIC_SPECS",
    "PHYSICAL_METRIC_BY_KEY",
    "PHYSICAL_TERM_KEYS",
    "PHYSICAL_SCHEMA_HASH",
    "FUTURE_METRIC_CANDIDATES",
    "PhysicalContributionResult",
    "PhysicalJReconstruction",
    "PhysicalModelFitResult",
    "PhysicalTransformResult",
    "extract_physical_contributions",
    "reconstruct_physical_j",
    "fit_physical_model",
    "evaluate_physical_transform",
]
