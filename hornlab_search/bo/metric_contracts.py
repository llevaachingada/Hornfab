"""Frozen shared contracts for the metric-composite Bayesian engine (Pass 1).

This module is intentionally dependency-light: numpy only, no Torch, no scorer import.  It freezes
the component schemas, selection/artifact dataclasses, tagged result types, and the checksum helper
used by :mod:`hornlab_search.bo.metric_training`, :mod:`~.metric_model`,
:mod:`~.metric_objective`, and :mod:`~.metric_propose`.

The scientific contract is recorded in
``docs/research/metric_bo_2026-11-22/ADR_metric_composite_v1.md``.  Do not change component names,
order, or source-term mappings without a new schema ID and a new artifact version.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

METRIC_TRAINING_VERSION = "metric-training-v1"
METRIC_COMPOSITE_POLICY = "metric_composite_v1"

V10_COMPONENT_SCHEMA_ID = "v10-metric-components-v1"
V11_COMPONENT_SCHEMA_ID = "v11-metric-components-v1"

V10_COMPONENT_NAMES = ("load_j", "coverage_j", "ripple_j", "other_j")
V11_COMPONENT_NAMES = (
    "load_j",
    "other_base_j",
    "cd_lw_j",
    "cd_di_std_j",
    "cd_nacc_j",
    "offaxis_smooth_j",
)

#: Every active v9/v10 weighted term that can enter ``other_j`` / ``other_base_j``.
V10_OTHER_TERMS = ("flat", "dislope", "di_roughness", "flat_cv", "hf_floor", "constancy")
V11_OTHER_BASE_TERMS = ("cov_profile", "rip") + V10_OTHER_TERMS
V11_CD_TERM_KEYS = ("cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")

_V10_SOURCE_TERMS = {
    "load_j": ("load",),
    "coverage_j": ("cov_profile",),
    "ripple_j": ("rip",),
    "other_j": V10_OTHER_TERMS,
}
_V11_SOURCE_TERMS = {
    "load_j": ("load",),
    "other_base_j": V11_OTHER_BASE_TERMS,
    "cd_lw_j": ("cd_lw",),
    "cd_di_std_j": ("cd_di_std",),
    "cd_nacc_j": ("cd_nacc",),
    "offaxis_smooth_j": ("offaxis_smooth",),
}

COMPONENT_SCHEMAS: dict[int, dict] = {
    10: {
        "schema_id": V10_COMPONENT_SCHEMA_ID,
        "objective_version": 10,
        "components": list(V10_COMPONENT_NAMES),
        "source_terms": {k: list(v) for k, v in _V10_SOURCE_TERMS.items()},
        "report_only_terms": [],
    },
    11: {
        "schema_id": V11_COMPONENT_SCHEMA_ID,
        "objective_version": 11,
        "components": list(V11_COMPONENT_NAMES),
        "source_terms": {k: list(v) for k, v in _V11_SOURCE_TERMS.items()},
        "report_only_terms": ["cd_omega_2pi", "cd_status_code"],
    },
}

#: Canonical sentinel used by ``objective.terms.NAN_TERM_FILL``.  A term equal to its normalised
#: value means the whole term was unmeasurable; the extractor refuses it instead of training on it.
NAN_TERM_FILL = 30.0

#: Declared floating-point parity tolerance (absolute + relative).  This is a serialization
#: tolerance, not an acoustic tolerance: the extractor uses the scorer's own term row and weights.
PARITY_ABS_TOL = 1e-12
PARITY_REL_TOL = 1e-12


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text for hashes/manifests (no NaN, sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False, default=float)


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def component_schema(objective_version: int) -> dict:
    """Return a copy of the frozen schema for ``objective_version`` (10 or 11)."""
    try:
        schema = COMPONENT_SCHEMAS[int(objective_version)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"unsupported objective version for metric components: {objective_version!r}")
    return {
        "schema_id": schema["schema_id"],
        "objective_version": int(schema["objective_version"]),
        "components": list(schema["components"]),
        "source_terms": {k: list(v) for k, v in schema["source_terms"].items()},
        "report_only_terms": list(schema["report_only_terms"]),
    }


def component_schema_hash(objective_version: int) -> str:
    """SHA-256 of the frozen component schema (order, mapping, version, report-only keys)."""
    return sha256_json(component_schema(objective_version))


V10_SCHEMA_HASH = component_schema_hash(10)
V11_SCHEMA_HASH = component_schema_hash(11)


def component_names(objective_version: int) -> tuple[str, ...]:
    return tuple(component_schema(objective_version)["components"])


def parity_tolerance(j: float) -> float:
    """Declared reconstruction tolerance for a canonical scalar ``j``."""
    return float(PARITY_ABS_TOL + PARITY_REL_TOL * max(1.0, abs(float(j))))


def validate_components(objective_version: int, components, j: float,
                        names=None) -> tuple[bool, float, tuple[str, ...]]:
    """Validate a component vector against the frozen schema and scalar ``J``.

    Returns ``(ok, reconstructed, reasons)``.  The vector is summed in schema order with
    ``math.fsum``; a mismatch is reported, never repaired by a residual.
    """
    reasons: list[str] = []
    version = int(objective_version)
    expected = component_names(version)
    got_names = tuple(names) if names is not None else expected
    if got_names != expected:
        return False, float("nan"), (f"component names/order differ: {got_names!r} != {expected!r}",)
    arr = np.asarray(components, dtype=np.float64).reshape(-1)
    if arr.size != len(expected):
        return False, float("nan"), (f"expected {len(expected)} components, got {arr.size}",)
    if not np.all(np.isfinite(arr)):
        return False, float("nan"), ("component vector contains NaN/Inf",)
    reconstructed = float(math.fsum(float(v) for v in arr))
    try:
        jj = float(j)
    except (TypeError, ValueError):
        return False, reconstructed, ("canonical J is not a number",)
    if not math.isfinite(jj):
        return False, reconstructed, ("canonical J is not finite",)
    delta = abs(reconstructed - jj)
    if delta > parity_tolerance(jj):
        reasons.append(
            f"component sum {reconstructed!r} differs from canonical J {jj!r} by {delta!r} "
            f"(tolerance {parity_tolerance(jj)!r})")
        return False, reconstructed, tuple(reasons)
    return True, reconstructed, ()


@dataclass(frozen=True)
class ContributionExtraction:
    """Tagged result of one v10/v11 contribution extraction."""

    status: str
    reason: str = ""
    observation_id: str = ""
    objective_version: int = 0
    component_names: tuple[str, ...] = ()
    components: np.ndarray | None = None
    j: float | None = None
    j_reconstructed: float | None = None
    parity_abs: float | None = None
    parity_tol: float | None = None
    schema_hash: str = ""
    cd_status: str | None = None
    quality_flags: tuple[str, ...] = ()
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "observation_id": self.observation_id,
            "objective_version": int(self.objective_version),
            "component_names": list(self.component_names),
            "components": (None if self.components is None
                           else np.asarray(self.components, dtype=float).reshape(-1).tolist()),
            "j": self.j,
            "j_reconstructed": self.j_reconstructed,
            "parity_abs": self.parity_abs,
            "parity_tol": self.parity_tol,
            "schema_hash": self.schema_hash,
            "cd_status": self.cd_status,
            "quality_flags": list(self.quality_flags),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class MetricTrainingCandidate:
    """One compatible, already-encoded observation before selection/artifact assembly."""

    observation_id: str
    x: np.ndarray
    J: float
    objective_version: int
    physical_id: str = ""
    solve_id: str = ""
    design_hash: str = ""
    geometry_hash: str = ""
    brief_hash: str = ""
    score_hash: str = ""
    task_identity: str = ""
    backend: str = ""
    fidelity: str = ""
    grid_hash: str = ""
    dependency_hash: str = ""
    mesh_hash: str = ""
    active_keys: tuple[str, ...] = ()
    bounds_hash: str = ""
    status: str = "ok"
    components: np.ndarray | None = None
    component_names: tuple[str, ...] = ()
    cd_status: str | None = None
    quality_flags: tuple[str, ...] = ()
    source: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SelectionPolicy:
    """Frozen cohort-selection policy (training cap, never a raw-discovery cap)."""

    n_max: int = 256
    elite_n: int = 64
    n_min_floor: int = 16
    seed: int = 0
    near_duplicate_tol: float = 1e-6
    require_single_backend: bool = True
    require_single_fidelity: bool = True
    require_single_mesh: bool = True
    require_single_dependency: bool = True
    allow_cd_cuts_fallback: bool = False
    allow_cuts_estimate_di: bool = False

    def to_dict(self) -> dict:
        return {
            "n_max": int(self.n_max),
            "elite_n": int(self.elite_n),
            "n_min_floor": int(self.n_min_floor),
            "seed": int(self.seed),
            "near_duplicate_tol": float(self.near_duplicate_tol),
            "require_single_backend": bool(self.require_single_backend),
            "require_single_fidelity": bool(self.require_single_fidelity),
            "require_single_mesh": bool(self.require_single_mesh),
            "require_single_dependency": bool(self.require_single_dependency),
            "allow_cd_cuts_fallback": bool(self.allow_cd_cuts_fallback),
            "allow_cuts_estimate_di": bool(self.allow_cuts_estimate_di),
        }

    @property
    def policy_hash(self) -> str:
        return sha256_json(self.to_dict())


@dataclass(frozen=True)
class SelectionResult:
    """Tagged result of the full-corpus compatible-observation selection."""

    status: str
    reasons: tuple[str, ...] = ()
    d: int = 0
    n_available: int = 0
    n_compatible: int = 0
    n_unique: int = 0
    n_selected: int = 0
    n_min: int = 0
    n_max: int = 0
    selected: tuple[MetricTrainingCandidate, ...] = ()
    excluded: tuple[dict, ...] = ()
    objective_version: int | None = None
    component_names: tuple[str, ...] = ()
    policy: dict = field(default_factory=dict)
    policy_hash: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return tuple(c.observation_id for c in self.selected)

    @property
    def excluded_ids(self) -> tuple[str, ...]:
        return tuple(str(e.get("observation_id")) for e in self.excluded)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "d": int(self.d),
            "n_available": int(self.n_available),
            "n_compatible": int(self.n_compatible),
            "n_unique": int(self.n_unique),
            "n_selected": int(self.n_selected),
            "n_min": int(self.n_min),
            "n_max": int(self.n_max),
            "selected_ids": list(self.selected_ids),
            "excluded": [dict(e) for e in self.excluded],
            "objective_version": self.objective_version,
            "component_names": list(self.component_names),
            "policy": dict(self.policy),
            "policy_hash": self.policy_hash,
        }


@dataclass(frozen=True)
class MetricTrainingArtifact:
    """Immutable ``metric-training-v1`` training payload plus its manifest."""

    status: str
    objective_version: int
    feature_names: tuple[str, ...]
    component_names: tuple[str, ...]
    X: np.ndarray | None = None
    J: np.ndarray | None = None
    Y_components: np.ndarray | None = None
    Y_phys: np.ndarray | None = None
    G: np.ndarray | None = None
    observation_ids: tuple[str, ...] = ()
    selected_ids: tuple[str, ...] = ()
    excluded: tuple[dict, ...] = ()
    metadata: dict = field(default_factory=dict)
    checksum: str = ""
    reasons: tuple[str, ...] = ()
    version: str = METRIC_TRAINING_VERSION

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def d(self) -> int:
        return 0 if self.X is None else int(np.asarray(self.X).shape[1])

    @property
    def n(self) -> int:
        return 0 if self.X is None else int(np.asarray(self.X).shape[0])

    @property
    def m(self) -> int:
        return len(self.component_names)

    def to_dict(self, *, include_arrays: bool = True) -> dict:
        out = {
            "status": self.status,
            "version": self.version,
            "objective_version": int(self.objective_version),
            "feature_names": list(self.feature_names),
            "component_names": list(self.component_names),
            "observation_ids": list(self.observation_ids),
            "selected_ids": list(self.selected_ids),
            "excluded": [dict(e) for e in self.excluded],
            "metadata": dict(self.metadata),
            "checksum": self.checksum,
            "reasons": list(self.reasons),
        }
        if include_arrays:
            out["X"] = None if self.X is None else np.asarray(self.X, dtype=float).tolist()
            out["J"] = None if self.J is None else np.asarray(self.J, dtype=float).tolist()
            out["Y_components"] = (None if self.Y_components is None
                                   else np.asarray(self.Y_components, dtype=float).tolist())
            out["Y_phys"] = (None if self.Y_phys is None
                             else np.asarray(self.Y_phys, dtype=float).tolist())
            out["G"] = None if self.G is None else np.asarray(self.G, dtype=float).tolist()
        return out


@dataclass(frozen=True)
class MetricModelFitResult:
    """Tagged result of a multi-output metric model fit."""

    status: str
    reason: str
    detail: str | None = None
    model: Any = field(default=None, repr=False, compare=False)
    output_names: tuple[str, ...] = ()
    d: int | None = None
    n: int | None = None
    train_X: np.ndarray | None = field(default=None, repr=False, compare=False)
    train_ids: tuple[str, ...] = ()
    per_output: tuple[dict, ...] = ()
    model_hash: str = ""
    artifact_checksum: str = ""
    library_versions: dict = field(default_factory=dict)
    seed: int = 0
    timing_s: float | None = None
    warnings: tuple[str, ...] = ()
    policy: str = METRIC_COMPOSITE_POLICY

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class MetricPrediction:
    """Posterior component/J summary in original contribution and J units."""

    status: str
    reason: str
    detail: str | None = None
    component_mean: np.ndarray | None = None
    component_sd: np.ndarray | None = None
    j_mean: np.ndarray | None = None
    j_sd: np.ndarray | None = None
    flags: tuple[str, ...] = ()
    interval_label: str = (
        "model credible interval from the independent-output posterior; not a physical tolerance")
    observation_noise: bool = False


@dataclass(frozen=True)
class MetricAcquisitionResult:
    """A built composite qLogNEI acquisition and its frozen provenance."""

    status: str
    reason: str
    detail: str | None = None
    acq: Any = field(default=None, repr=False, compare=False)
    X_baseline: np.ndarray | None = field(default=None, repr=False, compare=False)
    X_pending: np.ndarray | None = field(default=None, repr=False, compare=False)
    acq_seed: int = 0
    sample_shape: int = 128
    prune_baseline: bool = False
    policy: str = METRIC_COMPOSITE_POLICY
    library_versions: dict = field(default_factory=dict)
    timing_s: float | None = None


@dataclass(frozen=True)
class MetricProposalResult:
    """Tagged q=1 proposal result; predictions are never solved acoustic results."""

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
    acquisition_score: float | None = None
    predicted_j: float | None = None
    component_means: tuple[float, ...] = ()
    component_sds: tuple[float, ...] = ()
    total_sd: float | None = None
    model_hash: str = ""
    data_hash: str = ""
    policy: str = METRIC_COMPOSITE_POLICY
    bounds_hash: str = ""
    acq_seed: int = 0
    proposal_seed: int = 0
    fit_s: float | None = None
    acquisition_s: float | None = None
    counts: dict = field(default_factory=dict)
    library_versions: dict = field(default_factory=dict)
    timing_s: float | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def read_only_array(value, *, dtype=np.float64) -> np.ndarray:
    """Return a contiguous read-only copy; used by artifact builders."""
    arr = np.array(value, dtype=dtype, copy=True)
    arr.setflags(write=False)
    return arr


__all__ = [
    "METRIC_TRAINING_VERSION",
    "METRIC_COMPOSITE_POLICY",
    "V10_COMPONENT_SCHEMA_ID",
    "V11_COMPONENT_SCHEMA_ID",
    "V10_COMPONENT_NAMES",
    "V11_COMPONENT_NAMES",
    "V10_SCHEMA_HASH",
    "V11_SCHEMA_HASH",
    "V10_OTHER_TERMS",
    "V11_OTHER_BASE_TERMS",
    "V11_CD_TERM_KEYS",
    "COMPONENT_SCHEMAS",
    "NAN_TERM_FILL",
    "PARITY_ABS_TOL",
    "PARITY_REL_TOL",
    "canonical_json",
    "sha256_json",
    "component_schema",
    "component_schema_hash",
    "component_names",
    "parity_tolerance",
    "validate_components",
    "ContributionExtraction",
    "MetricTrainingCandidate",
    "SelectionPolicy",
    "SelectionResult",
    "MetricTrainingArtifact",
    "MetricModelFitResult",
    "MetricPrediction",
    "MetricAcquisitionResult",
    "MetricProposalResult",
    "read_only_array",
]
