"""Pass 1 data layer for metric-composite Bayesian optimization.

This module owns two responsibilities, both offline and numpy-only (no Torch, no BEM):

* **Contribution extraction** -- turn the canonical v10/v11 scorer term row into the frozen
  component vector (``load_j``/``coverage_j``/``ripple_j``/``other_j`` or the v11 CD block).
  Contributions are always ``weight * normalised_term`` in canonical ``J`` units; no component is
  ever computed as "J minus the others" and a parity failure is a tagged refusal.
* **Full-corpus cohort selection + artifact assembly** -- rank/select over *every* compatible
  completed observation (never a raw positional ``[:limit]`` slice), deduplicate physical/cached
  observations, and emit an immutable ``metric-training-v1`` payload with a manifest checksum.

The scientific contract is ``docs/research/metric_bo_2026-11-22/ADR_metric_composite_v1.md``.
Component names, order and source-term mappings are frozen in
:mod:`hornlab_search.bo.metric_contracts`; this module does not redefine them.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Iterable, Mapping

import numpy as np

from .metric_contracts import (
    METRIC_TRAINING_VERSION,
    NAN_TERM_FILL,
    ContributionExtraction,
    MetricTrainingArtifact,
    MetricTrainingCandidate,
    SelectionPolicy,
    SelectionResult,
    component_names,
    component_schema,
    component_schema_hash,
    parity_tolerance,
    read_only_array,
    sha256_json,
    validate_components,
)
from .metric_identity import (
    bounds_identity as _strict_bounds_identity,
    bounds_payload,
    recompute_bounds_hash,
    recompute_score_hash,
    score_identity as _score_identity,
    score_payload,
)

_ELIGIBLE_STATUS = frozenset({"ok", "complete", "success", "valid"})
_IDENTITY_FIELDS = (
    "objective_version",
    "brief_hash",
    "score_hash",
    "task_identity",
    "backend",
    "fidelity",
    "grid_hash",
    "dependency_hash",
    "mesh_hash",
    "active_keys",
    "bounds_hash",
)
#: Identity fields an observation MUST carry to be pooled. Empty values are not an identity:
#: they are a capability gap and are refused (never pooled as an empty-string identity group).
_REQUIRED_IDENTITY_FIELDS = (
    "brief_hash",
    "score_hash",
    "task_identity",
    "backend",
    "fidelity",
    "grid_hash",
    "dependency_hash",
    "mesh_hash",
    "bounds_hash",
)
_V10_PRIMARY = frozenset({"load", "cov_profile", "rip"})


# ---------------------------------------------------------------------------- helpers


def bounds_identity(encoding) -> str:
    """Stable identity of an :class:`ActiveProjection`'s bounds/active-key box.

    Delegates to :func:`hornlab_search.bo.metric_identity.bounds_identity` with ``strict=True`` so
    the hash covers the per-key physical lo/hi, transform kind, active-key order, projection
    version and fixed values.  Two boxes with the same dimension are not the same box.
    """
    return _strict_bounds_identity(encoding, strict=True)


def _base_tolerance(params_v9, key: str) -> float:
    if key == "hf_floor":
        return float(params_v9.hf_floor["tolerance"])
    if key == "constancy":
        return float(params_v9.constancy["tolerance"])
    return float(params_v9.tolerances[key])


def _is_unmeasurable_term(value: float, tolerance: float | None) -> bool:
    """True when the *normalised* term is the scorer's whole-term ``NAN_TERM_FILL`` sentinel.

    Base terms are normalised by their tolerance (``raw / tol``), so the stored value equals
    ``NAN_TERM_FILL / tol``; CD terms store ``NAN_TERM_FILL`` directly.  Both forms are checked.
    """
    if not math.isfinite(value):
        return False
    if value == NAN_TERM_FILL:
        return True
    if tolerance and tolerance > 0.0:
        expected = NAN_TERM_FILL / tolerance
        return value == expected or math.isclose(value * tolerance, NAN_TERM_FILL,
                                                 rel_tol=1e-12, abs_tol=1e-12)
    return False


def _refuse(version: int, reason: str, *, observation_id: str = "",
            detail: str | None = None, components=None, j=None, reconstructed=None,
            parity_abs=None, parity_tol=None, schema_hash: str = "",
            cd_status: str | None = None, quality_flags: tuple[str, ...] = ()) -> ContributionExtraction:
    return ContributionExtraction(
        status="refused",
        reason=reason,
        observation_id=observation_id,
        objective_version=int(version),
        component_names=tuple(component_names(version)) if version in (10, 11) else (),
        components=(None if components is None else read_only_array(components)),
        j=j,
        j_reconstructed=reconstructed,
        parity_abs=parity_abs,
        parity_tol=parity_tol,
        schema_hash=schema_hash,
        cd_status=cd_status,
        quality_flags=tuple(quality_flags),
        detail=detail,
    )


def _common_validation(terms, version: int, observation_id: str):
    """Validate the parts shared by v10/v11 extraction.

    Returns ``(reason, detail, penalty, total, n_nan, di_estimated)``; ``reason`` is empty on
    success.
    """
    if not isinstance(terms, Mapping):
        return ("terms_not_mapping", f"term row is {type(terms).__name__}, not a mapping",
                None, None, 0, False)
    if "penalty" not in terms:
        return "missing_term:penalty", "term row has no penalty", None, None, 0, False
    try:
        penalty = float(terms["penalty"])
    except (TypeError, ValueError):
        return "nonfinite_term:penalty", f"penalty={terms['penalty']!r}", None, None, 0, False
    if not math.isfinite(penalty):
        return "nonfinite_term:penalty", f"penalty={penalty!r}", None, None, 0, False
    if penalty > 0.0:
        return (f"penalty_row", f"penalty={penalty!r} (failed/refused score, never training data)",
                penalty, None, 0, False)
    if "total" not in terms:
        return "missing_term:total", "term row has no total", penalty, None, 0, False
    try:
        total = float(terms["total"])
    except (TypeError, ValueError):
        return "nonfinite_term:total", f"total={terms['total']!r}", penalty, None, 0, False
    if not math.isfinite(total):
        return "nonfinite_term:total", f"total={total!r}", penalty, None, 0, False
    try:
        n_nan = int(terms.get("n_nan") or 0)
    except (TypeError, ValueError):
        n_nan = 0
    di_estimated = bool(terms.get("di_estimated"))
    return "", None, penalty, total, n_nan, di_estimated


def _quality_flags(*, n_nan: int, cuts_estimate_di: bool, cd_cuts_fallback: bool) -> tuple[str, ...]:
    flags: list[str] = []
    if cuts_estimate_di:
        flags.append("cuts_estimate_di")
    if cd_cuts_fallback:
        flags.append("cd_cuts_fallback")
    if n_nan > 0:
        flags.append("n_nan")
    return tuple(flags)


# ---------------------------------------------------------------------------- v10


def extract_v10_contributions(terms, weights=None, params=None, *,
                              observation_id: str = "",
                              policy: SelectionPolicy | None = None) -> ContributionExtraction:
    """Extract the frozen v10 component vector from a canonical ``objective_v10`` term row.

    ``load_j``/``coverage_j``/``ripple_j`` are the three named weighted contributions; every
    remaining *active* weighted key (including optional ``hf_floor``/``constancy``) is summed
    into ``other_j``.  The vector is validated against ``terms["total"]`` with the declared
    serialization tolerance.
    """
    from ..objective.scalar_v10 import resolve_v10_weights

    policy = policy or SelectionPolicy()
    version = 10
    schema_hash = component_schema_hash(version)
    reason, detail, _penalty, total, n_nan, di_estimated = _common_validation(
        terms, version, observation_id)
    if reason:
        return _refuse(version, reason, observation_id=observation_id, detail=detail,
                       schema_hash=schema_hash)
    if params is None:
        return _refuse(version, "params_required", observation_id=observation_id,
                       detail="a validated V10Params instance is required",
                       schema_hash=schema_hash)

    p9 = params.v9
    active = tuple(params.weighted_keys())
    w = resolve_v10_weights(weights, params)

    for key in active:
        if key not in terms:
            return _refuse(version, f"missing_term:{key}", observation_id=observation_id,
                           schema_hash=schema_hash)
        try:
            value = float(terms[key])
        except (TypeError, ValueError):
            return _refuse(version, f"nonfinite_term:{key}", observation_id=observation_id,
                           detail=f"{key}={terms[key]!r}", schema_hash=schema_hash)
        if not math.isfinite(value):
            return _refuse(version, f"nonfinite_term:{key}", observation_id=observation_id,
                           detail=f"{key}={value!r}", schema_hash=schema_hash)
        tol = _base_tolerance(p9, key)
        if _is_unmeasurable_term(value, tol):
            return _refuse(version, f"unmeasurable_term:{key}", observation_id=observation_id,
                           detail=f"{key} is the NAN_TERM_FILL sentinel", schema_hash=schema_hash)

    if di_estimated and not policy.allow_cuts_estimate_di:
        return _refuse(version, "cuts_estimate_di", observation_id=observation_id,
                       detail="DI from cuts-estimate is refused by default",
                       schema_hash=schema_hash)

    load_j = float(w["load"]) * float(terms["load"])
    coverage_j = float(w["cov_profile"]) * float(terms["cov_profile"])
    ripple_j = float(w["rip"]) * float(terms["rip"])
    other_j = float(math.fsum(
        float(w[key]) * float(terms[key]) for key in active if key not in _V10_PRIMARY))

    components = np.asarray([load_j, coverage_j, ripple_j, other_j], dtype=np.float64)
    ok, reconstructed, why = validate_components(version, components, total)
    parity_abs = abs(float(reconstructed) - float(total)) if math.isfinite(reconstructed) else None
    flags = _quality_flags(n_nan=n_nan, cuts_estimate_di=di_estimated, cd_cuts_fallback=False)
    if not ok:
        return _refuse(version, "parity_mismatch", observation_id=observation_id,
                       detail="; ".join(why), components=components, j=total,
                       reconstructed=reconstructed, parity_abs=parity_abs,
                       parity_tol=parity_tolerance(total), schema_hash=schema_hash,
                       quality_flags=flags)
    return ContributionExtraction(
        status="ok",
        observation_id=observation_id,
        objective_version=version,
        component_names=tuple(component_names(version)),
        components=read_only_array(components),
        j=float(total),
        j_reconstructed=float(reconstructed),
        parity_abs=parity_abs,
        parity_tol=parity_tolerance(total),
        schema_hash=schema_hash,
        quality_flags=flags,
        detail=(f"n_nan={n_nan}" if n_nan else None),
    )


# ---------------------------------------------------------------------------- v11


def extract_v11_contributions(terms, weights=None, params=None, *,
                              observation_id: str = "",
                              policy: SelectionPolicy | None = None) -> ContributionExtraction:
    """Extract the frozen v11 component vector from a canonical ``objective_v11`` term row.

    The four CD weights come only from ``objective.cd`` (through ``resolve_v11_weights``);
    ``cd_omega_2pi``/``cd_status_code`` are report-only.  The base terms are re-normalised exactly
    as :func:`~hornlab_search.objective.scalar_v11._objective_v11` does before weighting, so the
    reconstruction follows the scorer's arithmetic rather than a residual.
    """
    from ..objective.scalar_v11 import (CD_STATUS_BALLOON, CD_STATUS_CODES,
                                        CD_STATUS_CUTS_FALLBACK, resolve_v11_weights)

    policy = policy or SelectionPolicy()
    version = 11
    schema_hash = component_schema_hash(version)
    reason, detail, _penalty, total, n_nan, di_estimated = _common_validation(
        terms, version, observation_id)
    if reason:
        return _refuse(version, reason, observation_id=observation_id, detail=detail,
                       schema_hash=schema_hash)
    if params is None:
        return _refuse(version, "params_required", observation_id=observation_id,
                       detail="a validated V11Params instance is required",
                       schema_hash=schema_hash)

    p9 = params.v10.v9
    active_base = tuple(params.v10.v9.weighted_keys())
    cd_keys = ("cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")
    for key in tuple(active_base) + cd_keys + ("cd_status_code",):
        if key not in terms:
            return _refuse(version, f"missing_term:{key}", observation_id=observation_id,
                           schema_hash=schema_hash)

    for key in active_base:
        try:
            value = float(terms[key])
        except (TypeError, ValueError):
            return _refuse(version, f"nonfinite_term:{key}", observation_id=observation_id,
                           detail=f"{key}={terms[key]!r}", schema_hash=schema_hash)
        if not math.isfinite(value):
            return _refuse(version, f"nonfinite_term:{key}", observation_id=observation_id,
                           detail=f"{key}={value!r}", schema_hash=schema_hash)
        if _is_unmeasurable_term(value, _base_tolerance(p9, key)):
            return _refuse(version, f"unmeasurable_term:{key}", observation_id=observation_id,
                           detail=f"{key} is the NAN_TERM_FILL sentinel", schema_hash=schema_hash)

    try:
        status_code = float(terms["cd_status_code"])
    except (TypeError, ValueError):
        return _refuse(version, "nonfinite_term:cd_status_code", observation_id=observation_id,
                       detail=f"cd_status_code={terms['cd_status_code']!r}", schema_hash=schema_hash)
    status_name = next((name for name, code in CD_STATUS_CODES.items() if code == status_code), None)
    if status_name is None:
        return _refuse(version, "unknown_cd_status", observation_id=observation_id,
                       detail=f"cd_status_code={status_code!r}", schema_hash=schema_hash)
    if status_name == "unmeasurable" or status_code == CD_STATUS_CODES["unmeasurable"]:
        return _refuse(version, "cd_unmeasurable", observation_id=observation_id,
                       detail="the CD block could not be measured", schema_hash=schema_hash,
                       cd_status="unmeasurable")
    cd_cuts_fallback = status_name == "cuts_fallback" or status_code == CD_STATUS_CUTS_FALLBACK
    if cd_cuts_fallback and not policy.allow_cd_cuts_fallback:
        return _refuse(version, "cd_cuts_fallback", observation_id=observation_id,
                       detail="cuts-fallback CD requires an explicit policy", schema_hash=schema_hash,
                       cd_status="cuts_fallback")
    if di_estimated and not policy.allow_cuts_estimate_di:
        return _refuse(version, "cuts_estimate_di", observation_id=observation_id,
                       detail="DI from cuts-estimate is refused by default",
                       schema_hash=schema_hash, cd_status=status_name)

    for key in cd_keys:
        try:
            value = float(terms[key])
        except (TypeError, ValueError):
            return _refuse(version, f"nonfinite_term:{key}", observation_id=observation_id,
                           detail=f"{key}={terms[key]!r}", schema_hash=schema_hash)
        if not math.isfinite(value):
            return _refuse(version, f"nonfinite_term:{key}", observation_id=observation_id,
                           detail=f"{key}={value!r}", schema_hash=schema_hash)
        if _is_unmeasurable_term(value, None):
            return _refuse(version, f"unmeasurable_term:{key}", observation_id=observation_id,
                           detail=f"{key} is the NAN_TERM_FILL sentinel", schema_hash=schema_hash,
                           cd_status=status_name)

    w = resolve_v11_weights(weights, params)

    def _renormalise(value: float, tolerance: float) -> float:
        # The exact arithmetic of scalar_v11._objective_v11: reconstruct the raw term from the
        # v10 row, then normalise it again through the same v9 tolerance.
        raw = float(value) * float(tolerance)
        return raw / float(tolerance)

    load_j = float(w["load"]) * _renormalise(terms["load"], _base_tolerance(p9, "load"))
    other_base_j = float(math.fsum(
        float(w[key]) * _renormalise(terms[key], _base_tolerance(p9, key))
        for key in active_base if key != "load"))
    cd_lw_j = float(w["cd_lw"]) * float(terms["cd_lw"])
    cd_di_std_j = float(w["cd_di_std"]) * float(terms["cd_di_std"])
    cd_nacc_j = float(w["cd_nacc"]) * float(terms["cd_nacc"])
    offaxis_j = float(w["offaxis_smooth"]) * float(terms["offaxis_smooth"])

    components = np.asarray([load_j, other_base_j, cd_lw_j, cd_di_std_j, cd_nacc_j, offaxis_j],
                            dtype=np.float64)
    ok, reconstructed, why = validate_components(version, components, total)
    parity_abs = abs(float(reconstructed) - float(total)) if math.isfinite(reconstructed) else None
    flags = _quality_flags(n_nan=n_nan, cuts_estimate_di=di_estimated,
                           cd_cuts_fallback=cd_cuts_fallback)
    if not ok:
        return _refuse(version, "parity_mismatch", observation_id=observation_id,
                       detail="; ".join(why), components=components, j=total,
                       reconstructed=reconstructed, parity_abs=parity_abs,
                       parity_tol=parity_tolerance(total), schema_hash=schema_hash,
                       cd_status=status_name, quality_flags=flags)
    return ContributionExtraction(
        status="ok",
        observation_id=observation_id,
        objective_version=version,
        component_names=tuple(component_names(version)),
        components=read_only_array(components),
        j=float(total),
        j_reconstructed=float(reconstructed),
        parity_abs=parity_abs,
        parity_tol=parity_tolerance(total),
        schema_hash=schema_hash,
        cd_status=status_name,
        quality_flags=flags,
        detail=(f"n_nan={n_nan}" if n_nan else None),
    )


def extract_contributions(terms, *, objective_version: int, weights=None, params,
                          observation_id: str = "",
                          policy: SelectionPolicy | None = None) -> ContributionExtraction:
    """Dispatch to the v10/v11 extractor for ``objective_version`` (10 or 11 only)."""
    version = int(objective_version)
    if version == 10:
        return extract_v10_contributions(terms, weights=weights, params=params,
                                         observation_id=observation_id, policy=policy)
    if version == 11:
        return extract_v11_contributions(terms, weights=weights, params=params,
                                         observation_id=observation_id, policy=policy)
    return _refuse(version, f"unsupported_objective_version:{objective_version}",
                   observation_id=observation_id)


# v10/v11 aliases for callers that prefer the short names.
v10_contributions = extract_v10_contributions
v11_contributions = extract_v11_contributions


# ---------------------------------------------------------------------------- selection


def _as_str(value) -> str:
    return "" if value is None else str(value)


def _coerce_candidate(record) -> MetricTrainingCandidate:
    if isinstance(record, MetricTrainingCandidate):
        return record
    if not isinstance(record, Mapping):
        raise TypeError(f"selection records must be MetricTrainingCandidate or mapping, "
                        f"got {type(record)!r}")
    oid = record.get("observation_id", record.get("id"))
    if oid is None:
        raise ValueError("selection record is missing an observation_id")
    x = record.get("x", record.get("unit_vector", record.get("active_vector")))
    if x is None:
        raise ValueError(f"selection record {oid!r} is missing x")
    J = record.get("J", record.get("j", record.get("objective")))
    if J is None:
        raise ValueError(f"selection record {oid!r} is missing J")
    components = record.get("components", record.get("Y_components"))
    return MetricTrainingCandidate(
        observation_id=str(oid),
        x=np.asarray(x, dtype=np.float64).reshape(-1),
        J=float(J),
        objective_version=int(record.get("objective_version", 0) or 0),
        physical_id=_as_str(record.get("physical_id")),
        solve_id=_as_str(record.get("solve_id", record.get("solve_hash"))),
        design_hash=_as_str(record.get("design_hash")),
        geometry_hash=_as_str(record.get("geometry_hash")),
        brief_hash=_as_str(record.get("brief_hash")),
        score_hash=_as_str(record.get("score_hash", record.get("score_identity"))),
        task_identity=_as_str(record.get("task_identity")),
        backend=_as_str(record.get("backend")),
        fidelity=_as_str(record.get("fidelity")),
        grid_hash=_as_str(record.get("grid_hash")),
        dependency_hash=_as_str(record.get("dependency_hash")),
        mesh_hash=_as_str(record.get("mesh_hash")),
        active_keys=tuple(str(k) for k in (record.get("active_keys") or ())),
        bounds_hash=_as_str(record.get("bounds_hash")),
        status=_as_str(record.get("status") or "ok"),
        components=None if components is None else np.asarray(components, dtype=np.float64),
        component_names=tuple(str(k) for k in (record.get("component_names") or ())),
        cd_status=record.get("cd_status"),
        quality_flags=tuple(record.get("quality_flags") or ()),
        source=dict(record.get("source") or {}),
    )


def _structural_check(candidate: MetricTrainingCandidate, *, d: int, expected_active: tuple[str, ...],
                      expected_bounds: str) -> tuple[MetricTrainingCandidate | None, list[str]]:
    """Return a normalised candidate or the typed exclusion reasons."""
    reasons: list[str] = []
    if candidate.status not in _ELIGIBLE_STATUS:
        return None, [f"failed_solve:{candidate.status or 'unknown'}"]
    version = int(candidate.objective_version)
    if version not in (10, 11):
        return None, [f"unsupported_objective_version:{candidate.objective_version!r}"]
    missing_identity = [field_name for field_name in _REQUIRED_IDENTITY_FIELDS
                        if not _as_str(getattr(candidate, field_name)).strip()]
    if missing_identity:
        return None, [f"capability_missing:missing_identity:{name}" for name in missing_identity]
    try:
        J = float(candidate.J)
    except (TypeError, ValueError):
        return None, ["j_nonfinite"]
    if not math.isfinite(J):
        return None, ["j_nonfinite"]

    x = np.asarray(candidate.x, dtype=np.float64).reshape(-1)
    if x.size != int(d):
        reasons.append(f"x_shape:{x.size}!={int(d)}")
    if not np.all(np.isfinite(x)):
        reasons.append("x_nonfinite")
    elif np.any((x < 0.0) | (x > 1.0)):
        reasons.append("x_out_of_box")
    if reasons:
        return None, reasons

    active_keys = tuple(candidate.active_keys) or expected_active
    if tuple(candidate.active_keys) and tuple(candidate.active_keys) != expected_active:
        reasons.append("active_keys_mismatch")
    bounds_hash = candidate.bounds_hash or expected_bounds
    if candidate.bounds_hash and candidate.bounds_hash != expected_bounds:
        reasons.append("bounds_identity_mismatch")
    if reasons:
        return None, reasons

    expected = component_names(version)
    names = tuple(candidate.component_names) or expected
    components = None
    if names != expected:
        reasons.append("component_schema_mismatch")
    elif candidate.components is not None:
        arr = np.asarray(candidate.components, dtype=np.float64).reshape(-1)
        if arr.size != len(expected):
            reasons.append(f"component_shape:{arr.size}!={len(expected)}")
        elif not np.all(np.isfinite(arr)):
            reasons.append("component_nonfinite")
        else:
            ok, _reconstructed, why = validate_components(version, arr, J)
            if not ok:
                reasons.append("component_parity")
            else:
                components = arr
    elif candidate.component_names:
        reasons.append("missing_component")
    if reasons:
        return None, reasons

    normalised = MetricTrainingCandidate(
        observation_id=candidate.observation_id,
        x=np.array(x, dtype=np.float64, copy=True),
        J=J,
        objective_version=version,
        physical_id=candidate.physical_id,
        solve_id=candidate.solve_id,
        design_hash=candidate.design_hash,
        geometry_hash=candidate.geometry_hash,
        brief_hash=candidate.brief_hash,
        score_hash=candidate.score_hash,
        task_identity=candidate.task_identity,
        backend=candidate.backend,
        fidelity=candidate.fidelity,
        grid_hash=candidate.grid_hash,
        dependency_hash=candidate.dependency_hash,
        mesh_hash=candidate.mesh_hash,
        active_keys=active_keys,
        bounds_hash=bounds_hash,
        status="ok",
        components=components,
        component_names=(expected if components is not None else tuple(candidate.component_names)),
        cd_status=candidate.cd_status,
        quality_flags=candidate.quality_flags,
        source=dict(candidate.source),
    )
    return normalised, []


def _identity_key(candidate: MetricTrainingCandidate) -> tuple[str, ...]:
    out: list[str] = []
    for field_name in _IDENTITY_FIELDS:
        value = getattr(candidate, field_name)
        if isinstance(value, (tuple, list)):
            out.append("|".join(str(v) for v in value))
        else:
            out.append("" if value is None else str(value))
    return tuple(out)


def _identity_mismatch_fields(reference: tuple[str, ...],
                              candidate: MetricTrainingCandidate) -> list[str]:
    got = _identity_key(candidate)
    return [name for name, a, b in zip(_IDENTITY_FIELDS, reference, got) if a != b]


def _physical_key(candidate: MetricTrainingCandidate):
    if candidate.physical_id:
        return ("physical", candidate.physical_id)
    if candidate.geometry_hash or candidate.mesh_hash or candidate.solve_id:
        return ("geometry", candidate.geometry_hash, candidate.mesh_hash, candidate.solve_id)
    if candidate.design_hash:
        return ("design", candidate.design_hash)
    return None


def _same_observation(a: MetricTrainingCandidate, b: MetricTrainingCandidate,
                      tol: float) -> bool:
    if abs(float(a.J) - float(b.J)) > parity_tolerance(float(a.J)):
        return False
    if np.max(np.abs(np.asarray(a.x) - np.asarray(b.x))) > float(tol):
        return False
    if (a.components is None) != (b.components is None):
        return False
    if a.components is not None:
        if np.max(np.abs(np.asarray(a.components) - np.asarray(b.components))) > 1e-12:
            return False
    return True


def _deduplicate(candidates: list[MetricTrainingCandidate], *, tol: float):
    """Return ``(unique, exclusions)``; conflicting physical aliases are refused, not picked."""
    buckets: dict[tuple, list[MetricTrainingCandidate]] = {}
    unique: list[MetricTrainingCandidate] = []
    for candidate in candidates:
        key = _physical_key(candidate)
        if key is None:
            unique.append(candidate)
        else:
            buckets.setdefault(key, []).append(candidate)
    exclusions: list[dict] = []
    for key, group in buckets.items():
        if len(group) == 1:
            unique.append(group[0])
            continue
        keep = group[0]
        conflict = any(not _same_observation(keep, other, tol) for other in group[1:])
        if conflict:
            for candidate in group:
                exclusions.append({
                    "observation_id": candidate.observation_id,
                    "reasons": ["duplicate_conflict"],
                    "detail": f"physical identity {key!r} maps to different J/x/components",
                })
        else:
            survivor = min(group, key=lambda c: (float(c.J), c.observation_id))
            for candidate in group:
                if candidate is survivor:
                    continue
                exclusions.append({
                    "observation_id": candidate.observation_id,
                    "reasons": ["duplicate_cached"],
                    "detail": f"same physical identity {key!r}; kept "
                              f"{survivor.observation_id!r}",
                })
            unique.append(survivor)
    return unique, exclusions


def _maximin_select(candidates: list[MetricTrainingCandidate],
                    selected: list[MetricTrainingCandidate], k: int) -> list[MetricTrainingCandidate]:
    """Deterministic farthest-point selection; ties by observation ID then input index."""
    if k <= 0 or not candidates:
        return []
    cand_x = np.vstack([c.x for c in candidates])
    if selected:
        sel_x = np.vstack([c.x for c in selected])
        min_dist = np.min(np.linalg.norm(cand_x[:, None, :] - sel_x[None, :, :], axis=2), axis=1)
    else:
        min_dist = np.full(cand_x.shape[0], np.inf, dtype=float)
    chosen: list[MetricTrainingCandidate] = []
    for _ in range(min(k, len(candidates))):
        best = float(np.max(min_dist))
        tied = np.flatnonzero(min_dist >= best - 1e-12)
        pick = min((int(i) for i in tied),
                   key=lambda i: (candidates[i].observation_id, i))
        chosen.append(candidates[pick])
        min_dist[pick] = -np.inf
        dist = np.linalg.norm(cand_x - cand_x[pick], axis=1)
        min_dist = np.minimum(min_dist, dist)
    return chosen


def select_metric_training_observations(records: Iterable,
                                        *, encoding,
                                        policy: SelectionPolicy | None = None) -> SelectionResult:
    """Select a metric-training cohort over the WHOLE compatible corpus.

    ``n_max`` is a training-selection cap, never a raw-discovery cap: every supplied record is
    compatible-checked and deduplicated before the 64-lowest-J + deterministic-maximin ranking.
    Below ``n_min = max(16, 2*(d+1))`` the result is ``needs_initial_data`` but still publishes
    the compatible unique observations (capped at ``n_max``) so a caller can replay/intake them.
    """
    policy = policy or SelectionPolicy()
    d = int(getattr(encoding, "d"))
    expected_active = tuple(str(k) for k in getattr(encoding, "active_keys", ()) or ())
    expected_bounds = bounds_identity(encoding)
    n_max = int(policy.n_max)
    n_min = max(int(policy.n_min_floor), 2 * (d + 1))
    if n_max < 1:
        return SelectionResult(status="refused", reasons=(f"n_max must be >= 1, got {n_max}",),
                               d=d, n_min=n_min, n_max=n_max, policy=policy.to_dict(),
                               policy_hash=policy.policy_hash)

    raw = list(records)
    excluded: list[dict] = []
    valid: list[MetricTrainingCandidate] = []
    for record in raw:
        try:
            candidate = _coerce_candidate(record)
        except (TypeError, ValueError) as exc:
            excluded.append({"observation_id": str(getattr(record, "observation_id", "") or ""),
                             "reasons": ["malformed_record"], "detail": str(exc)})
            continue
        normalised, reasons = _structural_check(candidate, d=d, expected_active=expected_active,
                                                expected_bounds=expected_bounds)
        if normalised is None:
            excluded.append({
                "observation_id": candidate.observation_id,
                "reasons": reasons,
                "detail": "structurally incompatible observation",
            })
            continue
        valid.append(normalised)

    n_available = len(raw)
    if not valid:
        return SelectionResult(
            status="refused",
            reasons=("no compatible observations",),
            d=d, n_available=n_available, n_compatible=0, n_unique=0, n_selected=0,
            n_min=n_min, n_max=n_max, excluded=tuple(excluded),
            objective_version=None, component_names=(), policy=policy.to_dict(),
            policy_hash=policy.policy_hash,
        )

    # Deterministic reference identity: the modal identity tuple (ties by canonical order).
    groups: dict[tuple[str, ...], list[MetricTrainingCandidate]] = {}
    for candidate in valid:
        groups.setdefault(_identity_key(candidate), []).append(candidate)
    reference = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0][0]
    compatible = groups[reference]
    for key, members in groups.items():
        if key == reference:
            continue
        for candidate in members:
            mismatched = _identity_mismatch_fields(reference, candidate)
            excluded.append({
                "observation_id": candidate.observation_id,
                "reasons": [f"identity_mismatch:{name}" for name in mismatched] or
                           ["identity_mismatch"],
                "detail": "observation does not share the cohort identity",
            })

    unique, dedup_excluded = _deduplicate(compatible, tol=float(policy.near_duplicate_tol))
    excluded.extend(dedup_excluded)
    version = int(compatible[0].objective_version)
    schema_names = tuple(component_names(version))

    ordered = sorted(unique, key=lambda c: (float(c.J), c.observation_id))
    if len(ordered) < n_min:
        selected = ordered[:n_max]
        status = "needs_initial_data"
        reasons = (f"n_unique {len(ordered)} < n_min {n_min}",)
    else:
        status = "ok"
        reasons = ()
        if len(ordered) <= n_max:
            selected = ordered
        else:
            elite_n = max(0, min(int(policy.elite_n), n_max))
            elites = ordered[:elite_n]
            remaining = ordered[elite_n:]
            maximin = _maximin_select(remaining, elites, n_max - elite_n)
            selected = elites + maximin

    selected_ids_set = {c.observation_id for c in selected}
    for candidate in ordered:
        if candidate.observation_id in selected_ids_set:
            continue
        excluded.append({
            "observation_id": candidate.observation_id,
            "reasons": ["not_selected:n_max_cap"],
            "detail": f"compatible observation outside the {n_max}-observation training cap",
        })

    return SelectionResult(
        status=status,
        reasons=reasons,
        d=d,
        n_available=n_available,
        n_compatible=len(compatible),
        n_unique=len(unique),
        n_selected=len(selected),
        n_min=n_min,
        n_max=n_max,
        selected=tuple(selected),
        excluded=tuple(excluded),
        objective_version=version,
        component_names=schema_names,
        policy=policy.to_dict(),
        policy_hash=policy.policy_hash,
    )


# ---------------------------------------------------------------------------- artifact


def _array_digest(array: np.ndarray) -> dict:
    arr = np.ascontiguousarray(array)
    return {
        "sha256": hashlib.sha256(arr.tobytes()).hexdigest(),
        "dtype": str(arr.dtype),
        "shape": [int(v) for v in arr.shape],
    }


def _resolve_identity_stamp(identity_metadata: Mapping[str, Any] | None, version: int,
                            *, require_identity: bool) -> tuple[dict, list[str]]:
    """Validate/stamp frozen bounds+score identity into artifact metadata.

    Returns ``(metadata, reasons)``.  ``require_identity=True`` demands a recomputable bounds
    payload and the full score identity; ``require_identity=False`` validates whatever payload the
    caller supplied (Pass 1 synthetic callers stay working) and never invents identity.
    """
    meta = dict(identity_metadata or {})
    reasons: list[str] = []

    raw_version = meta.get("objective_version")
    declared_version = None
    if raw_version is not None:
        try:
            declared_version = int(raw_version)
        except (TypeError, ValueError):
            declared_version = None
    if require_identity and declared_version is None:
        reasons.append("identity:objective_version_missing")
    elif declared_version is not None and declared_version != int(version):
        reasons.append(
            f"identity:objective_version_mismatch:{declared_version}!={int(version)}")

    # Bounds identity: an explicit payload, or a live encoding supplied by the caller.
    payload = meta.get("bounds_identity_payload")
    encoding = meta.get("encoding")
    recomputed_bounds = ""
    stamped_payload = None
    if payload is not None:
        try:
            recomputed_bounds = recompute_bounds_hash(payload)
            stamped_payload = dict(payload)
        except ValueError as exc:
            reasons.append(f"identity:bounds_payload_invalid:{exc}")
    elif encoding is not None:
        try:
            recomputed_bounds = _strict_bounds_identity(encoding, strict=True)
            stamped_payload = bounds_payload(encoding, strict=True)
        except ValueError as exc:
            reasons.append(f"identity:bounds_payload_invalid:{exc}")
    if recomputed_bounds:
        declared_bounds = str(meta.get("bounds_hash") or "").strip()
        if declared_bounds and declared_bounds != recomputed_bounds:
            reasons.append("identity:bounds_hash_mismatch")
        if stamped_payload is not None:
            meta["bounds_identity_payload"] = stamped_payload
        meta["bounds_hash"] = recomputed_bounds
        meta.pop("encoding", None)
    elif require_identity:
        reasons.append("identity:bounds_payload_missing")

    # Score identity: only attempted when required or when the caller already supplied one.
    brief_hash = str(meta.get("brief_hash") or "").strip()
    score_hash = str(meta.get("score_hash") or "").strip()
    declared_score = str(meta.get("score_identity") or "").strip()
    supplied_payload = meta.get("score_identity_payload")
    wants_score = require_identity or bool(declared_score) or supplied_payload is not None
    if wants_score:
        missing = [name for name, value in (("brief_hash", brief_hash),
                                            ("score_hash", score_hash)) if not value]
        if missing:
            if require_identity:
                reasons.extend(f"identity:{name}_missing" for name in missing)
        else:
            try:
                expected_payload = score_payload(
                    objective_version=int(version), brief_hash=brief_hash,
                    score_hash=score_hash)
                expected_score = _score_identity(
                    objective_version=int(version), brief_hash=brief_hash,
                    score_hash=score_hash)
            except ValueError as exc:
                reasons.append(f"identity:score_payload_invalid:{exc}")
            else:
                if supplied_payload is not None:
                    try:
                        recomputed_score = recompute_score_hash(supplied_payload)
                    except ValueError as exc:
                        reasons.append(f"identity:score_payload_invalid:{exc}")
                    else:
                        if recomputed_score != expected_score:
                            reasons.append("identity:score_identity_mismatch")
                if declared_score and declared_score != expected_score:
                    reasons.append("identity:score_identity_mismatch")
                if require_identity:
                    meta["score_identity_payload"] = expected_payload
                    meta["score_identity"] = expected_score
    return meta, reasons


def build_metric_training_artifact(selection, *, identity_metadata: Mapping[str, Any],
                                   y_phys=None, G=None,
                                   feature_names: tuple[str, ...] | None = None,
                                   require_identity: bool = False
                                   ) -> MetricTrainingArtifact:
    """Assemble an immutable ``metric-training-v1`` payload from a successful selection.

    Arrays are copied to read-only ``float64``; ``J == sum(Y_components)`` is validated per row
    with :func:`~hornlab_search.bo.metric_contracts.validate_components`, and the manifest
    checksum covers canonical metadata plus every array digest.
    """
    version = int(getattr(selection, "objective_version", 0) or 0)
    names = tuple(getattr(selection, "component_names", ()) or ())
    if names and version in (10, 11):
        names = tuple(component_names(version))

    stamped_metadata, identity_reasons = _resolve_identity_stamp(
        identity_metadata, version, require_identity=bool(require_identity))

    def _refused(reasons: tuple[str, ...]):
        return MetricTrainingArtifact(
            status="refused", objective_version=version, feature_names=tuple(feature_names or ()),
            component_names=names, metadata=dict(stamped_metadata), reasons=reasons)

    if identity_reasons:
        return _refused(tuple(identity_reasons))

    if not isinstance(selection, SelectionResult):
        return _refused(("selection must be a SelectionResult",))
    if selection.status != "ok" or not selection.ok:
        return _refused((f"selection status is {selection.status!r}, not 'ok'",))
    if version not in (10, 11):
        return _refused((f"unsupported objective version {version!r}",))
    expected_names = tuple(component_names(version))
    if names != expected_names:
        return _refused((f"component names/order {names!r} != {expected_names!r}",))
    selected = list(selection.selected)
    if not selected:
        return _refused(("selection has no selected observations",))
    if len({c.observation_id for c in selected}) != len(selected):
        return _refused(("selected observation IDs are not unique",))

    components_rows: list[np.ndarray] = []
    j_values: list[float] = []
    for candidate in selected:
        if candidate.components is None:
            return _refused((f"observation {candidate.observation_id!r} has no components",))
        if tuple(candidate.component_names) and tuple(candidate.component_names) != expected_names:
            return _refused((f"observation {candidate.observation_id!r} component schema differs",))
        arr = np.asarray(candidate.components, dtype=np.float64).reshape(-1)
        if arr.size != len(expected_names):
            return _refused((f"observation {candidate.observation_id!r} has {arr.size} "
                             f"components, expected {len(expected_names)}",))
        j = float(candidate.J)
        ok, _reconstructed, why = validate_components(version, arr, j)
        if not ok:
            return _refused((f"observation {candidate.observation_id!r}: {'; '.join(why)}",))
        components_rows.append(arr)
        j_values.append(j)

    X = np.vstack([np.asarray(c.x, dtype=np.float64).reshape(-1) for c in selected])
    J = np.asarray(j_values, dtype=np.float64).reshape(-1, 1)
    Y_components = np.vstack(components_rows)
    d = int(X.shape[1])
    if feature_names is None:
        feature_names = tuple(selected[0].active_keys)
    feature_names = tuple(str(k) for k in feature_names)
    if feature_names and len(feature_names) != d:
        return _refused((f"feature_names length {len(feature_names)} != d {d}",))
    if not np.all(np.isfinite(X)):
        return _refused(("X contains non-finite values",))

    def _optional(array, label, columns):
        if array is None:
            return None
        arr = np.asarray(array, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(-1, columns)
        if arr.shape[0] != len(selected) or not np.all(np.isfinite(arr)):
            raise ValueError(f"{label} must be finite with {len(selected)} rows")
        return read_only_array(arr)

    try:
        Y_phys = _optional(y_phys, "Y_phys", 1)
        G_arr = _optional(G, "G", 1)
    except ValueError as exc:
        return _refused((str(exc),))

    X_ro = read_only_array(X)
    J_ro = read_only_array(J)
    Y_ro = read_only_array(Y_components)
    schema = component_schema(version)
    schema_hash = component_schema_hash(version)
    metadata: dict[str, Any] = dict(stamped_metadata)
    metadata.update({
        "version": METRIC_TRAINING_VERSION,
        "objective_version": version,
        "component_schema": schema["schema_id"],
        "component_schema_hash": schema_hash,
        "component_names": list(expected_names),
        "feature_names": list(feature_names),
        "policy": dict(selection.policy),
        "policy_hash": selection.policy_hash,
        "n": len(selected),
        "d": d,
        "n_unique": int(selection.n_unique),
        "n_compatible": int(selection.n_compatible),
        "observation_ids": [c.observation_id for c in selected],
        "selected_ids": list(selection.selected_ids),
        "excluded": [dict(e) for e in selection.excluded],
    })
    arrays_manifest = {"X": _array_digest(X_ro), "J": _array_digest(J_ro),
                       "Y_components": _array_digest(Y_ro)}
    if Y_phys is not None:
        arrays_manifest["Y_phys"] = _array_digest(Y_phys)
    if G_arr is not None:
        arrays_manifest["G"] = _array_digest(G_arr)
    manifest = {
        "version": METRIC_TRAINING_VERSION,
        "objective_version": version,
        "component_schema_hash": schema_hash,
        "metadata": metadata,
        "observation_ids": list(metadata["observation_ids"]),
        "selected_ids": list(metadata["selected_ids"]),
        "excluded": metadata["excluded"],
        "arrays": arrays_manifest,
    }
    try:
        checksum = sha256_json(manifest)
    except (TypeError, ValueError) as exc:
        return _refused((f"manifest is not canonically serializable: {exc}",))
    metadata["manifest_checksum"] = checksum
    metadata["manifest_checksum_algorithm"] = "sha256(canonical-json(metadata+array digests))"

    return MetricTrainingArtifact(
        status="ok",
        objective_version=version,
        feature_names=feature_names,
        component_names=expected_names,
        X=X_ro,
        J=J_ro,
        Y_components=Y_ro,
        Y_phys=Y_phys,
        G=G_arr,
        observation_ids=tuple(metadata["observation_ids"]),
        selected_ids=tuple(metadata["selected_ids"]),
        excluded=tuple(dict(e) for e in selection.excluded),
        metadata=metadata,
        checksum=checksum,
    )


__all__ = [
    "bounds_identity",
    "extract_v10_contributions",
    "extract_v11_contributions",
    "extract_contributions",
    "v10_contributions",
    "v11_contributions",
    "select_metric_training_observations",
    "build_metric_training_artifact",
]
