"""Frozen bounds/score identity contracts for metric-composite studies (Pass 2).

A ``metric-training-v1`` artifact is only usable as a *study* training label when every frozen
identity it depends on is the same identity the study intends to optimize:

* the physical parameter box (lo/hi per key), active-key order, transform kind, projection
  version and fixed values of the :class:`~.encoding.ActiveProjection`;
* the scoring identity (objective version + brief hash + catalog score identity + score module).

This module is deliberately dependency-light (hashlib/json/math only) so that the study builder,
the proposal engine, the package gate and offline tooling can all validate the same contract
without importing Torch, BoTorch or the scorer.

Design rules
------------
* A caller-declared hash is **never** proof.  Callers pass the hash they *recomputed* from a live
  frozen object (space/projection/config), and every other source must agree with it.
* Missing identity fails closed.  An empty string is ``unavailable``, never "match".
* Two boxes with the same dimension or the same number of parameters are not the same box; the
  identity payload records per-key physical bounds and transforms, not counts.
* The payload is recorded in artifact/manifest metadata so a later reload can recompute the hash
  and detect tampering instead of trusting the stored hash.

Pass 1 shipped ``metric_training.bounds_identity`` hashed only ``active_keys``/``version``/
``transforms``.  The strict payload here additionally records ``fixed_values`` and the identity
schema version.  No real-data artifact existed when this contract was extended (Pass 1 was
synthetic-only), so the change is a versioned contract extension, not a silent migration.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .metric_contracts import canonical_json, sha256_json

BOUNDS_IDENTITY_VERSION = "metric-bounds-identity-v1"
SCORE_IDENTITY_VERSION = "metric-score-identity-v1"

STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

REASON_OK = "ok"
REASON_BOUNDS_MISSING = "bounds_identity_missing"
REASON_BOUNDS_MISMATCH = "bounds_identity_mismatch"
REASON_BOUNDS_PAYLOAD_MISSING = "bounds_identity_payload_missing"
REASON_BOUNDS_PAYLOAD_INVALID = "bounds_identity_payload_invalid"
REASON_TRANSFORM_MISSING = "bounds_transform_missing"
REASON_ACTIVE_KEYS_MISSING = "active_parameter_keys_missing"
REASON_ACTIVE_KEYS_MISMATCH = "active_parameter_order_mismatch"
REASON_PROJECTION_VERSION_MISSING = "projection_version_missing"
REASON_SCORE_MISSING = "score_identity_missing"
REASON_SCORE_MISMATCH = "score_identity_mismatch"
REASON_OBJECTIVE_VERSION_MISMATCH = "objective_version_mismatch"
REASON_BRIEF_MISMATCH = "brief_identity_mismatch"
REASON_SCORE_MODULE_MISMATCH = "score_module_mismatch"
REASON_FIXED_VALUE_INVALID = "fixed_value_invalid"

#: Catalog ``score_identity`` values are sha256 prefixes (``_sha16`` in tools/analysis/catalog.py).
_IDENTITY_TOKEN = re.compile(r"^[0-9a-f]{16,64}$")
_SCORE_MODULES = {10: "scalar_v10", 11: "scalar_v11"}


# --------------------------------------------------------------------------- canonical helpers


def _finite(value, label: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not numeric: {value!r}") from exc
    if not math.isfinite(out):
        raise ValueError(f"{label} is not finite: {value!r}")
    return out


def _token(value, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{label} is missing")
    if not _IDENTITY_TOKEN.match(text):
        raise ValueError(f"{label} is not a catalog identity token: {text!r}")
    return text


# --------------------------------------------------------------------------- bounds identity


def bounds_payload(encoding, *, strict: bool = True) -> dict:
    """Canonical bounds payload for an ``ActiveProjection``-like object.

    ``strict`` requires ``key_transforms()`` (which carries the per-key physical lo/hi and log
    flag) and a non-empty projection version.  A minimal test double may only call with
    ``strict=False`` and is then explicitly labelled by the reduced payload.
    """
    active = tuple(str(k) for k in getattr(encoding, "active_keys", ()) or ())
    version = str(getattr(encoding, "version", "") or "")
    if strict:
        if not active:
            raise ValueError(f"{REASON_ACTIVE_KEYS_MISSING}: encoding has no active keys")
        if not version:
            raise ValueError(f"{REASON_PROJECTION_VERSION_MISSING}: encoding has no version")
        if len(set(active)) != len(active):
            raise ValueError("active key order contains duplicates")
    transforms = None
    getter = getattr(encoding, "key_transforms", None)
    if callable(getter):
        try:
            transforms = dict(getter() or {})
        except Exception as exc:  # noqa: BLE001 - a broken projection is a refusal
            if strict:
                raise ValueError(f"{REASON_TRANSFORM_MISSING}: key_transforms failed: {exc}") from exc
            transforms = None
    if strict and not transforms:
        raise ValueError(f"{REASON_TRANSFORM_MISSING}: encoding did not expose key_transforms()")

    payload: dict[str, Any] = {
        "version": BOUNDS_IDENTITY_VERSION,
        "projection_version": version,
        "active_keys": list(active),
    }
    if transforms:
        clean: dict[str, dict] = {}
        for key in transforms:
            row = dict(transforms[key] or {})
            try:
                lo = _finite(row["lo"], f"transform {key!r} lo")
                hi = _finite(row["hi"], f"transform {key!r} hi")
            except KeyError as exc:
                raise ValueError(f"{REASON_TRANSFORM_MISSING}: transform {key!r} lacks lo/hi") from exc
            if strict and not hi > lo:
                raise ValueError(f"transform {key!r} has an empty physical box: [{lo}, {hi}]")
            log = bool(row.get("log", False))
            if strict and log and lo <= 0.0:
                raise ValueError(f"transform {key!r} is log10 but lo={lo!r} <= 0")
            clean[str(key)] = {
                "lo": lo,
                "hi": hi,
                "log": log,
                "transform": str(row.get("transform") or ("log10" if log else "identity")),
                "active": bool(row.get("active", True)),
            }
        if strict:
            missing = [key for key in active if key not in clean]
            if missing:
                raise ValueError(f"{REASON_TRANSFORM_MISSING}: active keys lack transforms: {missing}")
        payload["transforms"] = clean
    payload["fixed_values"] = {
        str(k): _finite(v, f"fixed value {k!r}")
        for k, v in (getattr(encoding, "fixed_values", None) or {}).items()
    }
    return payload


def bounds_identity(encoding, *, strict: bool = True) -> str:
    """SHA-256 of the canonical bounds payload (the only accepted box identity)."""
    return sha256_json(bounds_payload(encoding, strict=strict))


def recompute_bounds_hash(payload: Mapping[str, Any]) -> str:
    """Recompute the hash of a recorded payload and reject malformed/tampered payloads."""
    if not isinstance(payload, Mapping):
        raise ValueError(f"{REASON_BOUNDS_PAYLOAD_MISSING}: bounds payload must be a mapping")
    data = dict(payload)
    if data.get("version") != BOUNDS_IDENTITY_VERSION:
        raise ValueError(
            f"{REASON_BOUNDS_PAYLOAD_INVALID}: payload version {data.get('version')!r} "
            f"!= {BOUNDS_IDENTITY_VERSION!r}")
    active = data.get("active_keys")
    if not isinstance(active, (list, tuple)) or not active:
        raise ValueError(f"{REASON_BOUNDS_PAYLOAD_INVALID}: payload has no active key order")
    if not str(data.get("projection_version") or ""):
        raise ValueError(f"{REASON_PROJECTION_VERSION_MISSING}: payload has no projection version")
    transforms = data.get("transforms")
    if not isinstance(transforms, Mapping) or not transforms:
        raise ValueError(f"{REASON_TRANSFORM_MISSING}: payload has no per-key transforms")
    for key in active:
        row = transforms.get(key)
        if not isinstance(row, Mapping):
            raise ValueError(f"{REASON_TRANSFORM_MISSING}: active key {key!r} has no transform")
        lo = _finite(row.get("lo"), f"transform {key!r} lo")
        hi = _finite(row.get("hi"), f"transform {key!r} hi")
        if not hi > lo:
            raise ValueError(f"payload transform {key!r} has an empty physical box")
    fixed = data.get("fixed_values", {})
    if not isinstance(fixed, Mapping):
        raise ValueError(f"{REASON_BOUNDS_PAYLOAD_INVALID}: fixed_values must be a mapping")
    for key, value in fixed.items():
        _finite(value, f"fixed value {key!r}")
    return sha256_json(data)


# --------------------------------------------------------------------------- score identity


def score_payload(*, objective_version: int, brief_hash: str, score_hash: str,
                  score_module: str | None = None) -> dict:
    """Canonical score payload.  Objective version alone is never sufficient."""
    try:
        version = int(objective_version)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{REASON_OBJECTIVE_VERSION_MISMATCH}: {objective_version!r}") from exc
    module = str(score_module or _SCORE_MODULES.get(version, ""))
    expected = _SCORE_MODULES.get(version)
    if expected is None:
        raise ValueError(f"{REASON_OBJECTIVE_VERSION_MISMATCH}: no metric score module for v{version}")
    if module != expected:
        raise ValueError(f"{REASON_SCORE_MODULE_MISMATCH}: {module!r} != {expected!r} for v{version}")
    return {
        "version": SCORE_IDENTITY_VERSION,
        "objective_version": version,
        "brief_hash": _token(brief_hash, "brief_hash"),
        "score_hash": _token(score_hash, "score_hash"),
        "score_module": module,
    }


def score_identity(*, objective_version: int, brief_hash: str, score_hash: str,
                   score_module: str | None = None) -> str:
    return sha256_json(score_payload(
        objective_version=objective_version, brief_hash=brief_hash,
        score_hash=score_hash, score_module=score_module))


def recompute_score_hash(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{REASON_SCORE_MISSING}: score payload must be a mapping")
    data = dict(payload)
    if data.get("version") != SCORE_IDENTITY_VERSION:
        raise ValueError(f"{REASON_SCORE_MISMATCH}: payload version {data.get('version')!r}")
    return sha256_json(score_payload(
        objective_version=data.get("objective_version"),
        brief_hash=data.get("brief_hash"),
        score_hash=data.get("score_hash"),
        score_module=data.get("score_module")))


def score_module_for(objective_version: int) -> str:
    try:
        return _SCORE_MODULES[int(objective_version)]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{REASON_OBJECTIVE_VERSION_MISMATCH}: {objective_version!r}") from exc


# --------------------------------------------------------------------------- checks


@dataclass(frozen=True)
class IdentityCheck:
    """Tagged identity comparison across frozen sources."""

    status: str
    reason: str = REASON_OK
    detail: str | None = None
    expected: str = ""
    sources: tuple[tuple[str, str], ...] = ()
    missing: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "expected": self.expected,
            "sources": {k: v for k, v in self.sources},
            "missing": list(self.missing),
            "mismatched": list(self.mismatched),
        }


def _unavailable(reason: str, detail: str, *, expected: str = "",
                 sources=(), missing=(), mismatched=()) -> IdentityCheck:
    return IdentityCheck(status=STATUS_UNAVAILABLE, reason=reason, detail=detail,
                         expected=str(expected or ""),
                         sources=tuple(sources), missing=tuple(missing),
                         mismatched=tuple(mismatched))


def check_bounds_identity(*, expected_hash: str, sources: Mapping[str, Any],
                          expected_payload: Mapping[str, Any] | None = None,
                          required: tuple[str, ...] | None = None) -> IdentityCheck:
    """Require every named source to carry the *recomputed* box hash.

    ``expected_hash`` must be recomputed from a live frozen projection (or, when
    ``expected_payload`` is supplied, from the recorded payload that is independently
    re-hashed here).  A missing source, an empty value or any disagreement refuses.
    """
    listed = tuple((str(k), "" if v is None else str(v)) for k, v in sources.items())
    if not str(expected_hash or "").strip():
        return _unavailable(REASON_BOUNDS_MISSING, "no recomputed bounds hash was supplied",
                            sources=listed)
    expected = str(expected_hash).strip()
    if expected_payload is not None:
        try:
            recomputed = recompute_bounds_hash(expected_payload)
        except ValueError as exc:
            return _unavailable(REASON_BOUNDS_PAYLOAD_INVALID, str(exc), expected=expected,
                                sources=listed)
        if recomputed != expected:
            return _unavailable(
                REASON_BOUNDS_MISMATCH,
                f"recorded bounds payload hashes to {recomputed!r}, not the expected {expected!r}",
                expected=expected, sources=listed, mismatched=("payload",))
    names = tuple(str(n) for n in (required if required is not None else sources.keys()))
    missing = tuple(name for name in names
                    if not dict(listed).get(name, "").strip())
    if missing:
        return _unavailable(
            REASON_BOUNDS_MISSING,
            "bounds identity missing from: " + ", ".join(missing),
            expected=expected, sources=listed, missing=missing)
    mismatched = tuple(name for name in names if dict(listed).get(name) != expected)
    if mismatched:
        observed = ", ".join(f"{name}={dict(listed).get(name)!r}" for name in mismatched)
        return _unavailable(
            REASON_BOUNDS_MISMATCH,
            f"bounds identity differs in {', '.join(mismatched)}: {observed} "
            f"(expected {expected!r})",
            expected=expected, sources=listed, mismatched=mismatched)
    return IdentityCheck(status=STATUS_OK, reason=REASON_OK, detail=None, expected=expected,
                         sources=listed)


def check_score_identity(*, metadata: Mapping[str, Any], objective_version: int,
                         brief_hash: str, score_hash: str,
                         score_module: str | None = None,
                         payload_key: str = "score_identity_payload") -> IdentityCheck:
    """Validate a training artifact's recorded score identity against the frozen task.

    The expected brief/score identities come from the caller's frozen config/catalog identity,
    not from the artifact being checked.  A recorded payload is re-hashed when present.
    """
    try:
        expected = score_identity(objective_version=objective_version, brief_hash=brief_hash,
                                  score_hash=score_hash, score_module=score_module)
    except ValueError as exc:
        return _unavailable(REASON_SCORE_MISSING, str(exc))
    if not isinstance(metadata, Mapping):
        return _unavailable(REASON_SCORE_MISSING, "artifact metadata is missing",
                            expected=expected)
    recorded_hash = str(metadata.get("score_identity") or "").strip()
    recorded_brief = str(metadata.get("brief_hash") or "").strip()
    recorded_score = str(metadata.get("score_hash") or "").strip()
    try:
        recorded_version = int(metadata.get("objective_version"))
    except (TypeError, ValueError):
        recorded_version = None
    missing = tuple(name for name, value in (
        ("score_identity", recorded_hash), ("brief_hash", recorded_brief),
        ("score_hash", recorded_score)) if not value)
    if recorded_version is None:
        missing = missing + ("objective_version",)
    if missing:
        return _unavailable(REASON_SCORE_MISSING,
                            "score identity missing from artifact metadata: "
                            + ", ".join(missing), expected=expected, missing=missing)
    if recorded_version != int(objective_version):
        return _unavailable(
            REASON_OBJECTIVE_VERSION_MISMATCH,
            f"artifact objective version {recorded_version!r} != {int(objective_version)!r}",
            expected=expected, mismatched=("objective_version",))
    if recorded_brief != str(brief_hash).strip():
        return _unavailable(
            REASON_BRIEF_MISMATCH,
            f"artifact brief_hash {recorded_brief!r} != frozen {str(brief_hash)!r}",
            expected=expected, mismatched=("brief_hash",))
    if recorded_score != str(score_hash).strip():
        return _unavailable(
            REASON_SCORE_MISMATCH,
            f"artifact score_hash {recorded_score!r} != frozen {str(score_hash)!r}",
            expected=expected, mismatched=("score_hash",))
    if recorded_hash != expected:
        return _unavailable(
            REASON_SCORE_MISMATCH,
            f"artifact score identity {recorded_hash!r} != recomputed {expected!r}",
            expected=expected, mismatched=("score_identity",))
    payload = metadata.get(payload_key)
    if payload is not None:
        try:
            recomputed = recompute_score_hash(payload)
        except ValueError as exc:
            return _unavailable(REASON_SCORE_MISMATCH, str(exc), expected=expected,
                                mismatched=("score_identity_payload",))
        if recomputed != expected:
            return _unavailable(
                REASON_SCORE_MISMATCH,
                f"recorded score payload hashes to {recomputed!r}, not {expected!r}",
                expected=expected, mismatched=("score_identity_payload",))
    return IdentityCheck(status=STATUS_OK, reason=REASON_OK, expected=expected)


def check_identity_fields(*, expected: Mapping[str, Any], observed: Mapping[str, Any],
                          fields: tuple[str, ...], reason: str = "identity_mismatch",
                          missing_reason: str = "identity_missing") -> IdentityCheck:
    """Compare exact string identities (task, backend, fidelity, dependency ...)."""
    expected_pairs = tuple((str(f), "" if expected.get(f) is None else str(expected.get(f)))
                           for f in fields)
    observed_pairs = tuple((str(f), "" if observed.get(f) is None else str(observed.get(f)))
                           for f in fields)
    missing = tuple(name for name, value in expected_pairs + observed_pairs if not value)
    if missing:
        return _unavailable(missing_reason,
                            "identity missing for: " + ", ".join(sorted(set(missing))),
                            sources=observed_pairs, missing=tuple(sorted(set(missing))))
    mismatched = tuple(name for (name, want), (_, got) in zip(expected_pairs, observed_pairs)
                       if want != got)
    if mismatched:
        detail = "; ".join(
            f"{name}: expected {want!r}, observed {got!r}"
            for (name, want), (_, got) in zip(expected_pairs, observed_pairs) if want != got)
        return _unavailable(reason, detail, sources=observed_pairs, mismatched=mismatched)
    return IdentityCheck(status=STATUS_OK, reason=REASON_OK, sources=observed_pairs)


def payload_to_json(payload: Mapping[str, Any]) -> str:
    """Canonical JSON text for manifest storage (rejects NaN/Inf)."""
    return canonical_json(dict(payload))


__all__ = [
    "BOUNDS_IDENTITY_VERSION",
    "SCORE_IDENTITY_VERSION",
    "STATUS_OK",
    "STATUS_UNAVAILABLE",
    "REASON_OK",
    "REASON_BOUNDS_MISSING",
    "REASON_BOUNDS_MISMATCH",
    "REASON_BOUNDS_PAYLOAD_MISSING",
    "REASON_BOUNDS_PAYLOAD_INVALID",
    "REASON_TRANSFORM_MISSING",
    "REASON_ACTIVE_KEYS_MISSING",
    "REASON_ACTIVE_KEYS_MISMATCH",
    "REASON_PROJECTION_VERSION_MISSING",
    "REASON_SCORE_MISSING",
    "REASON_SCORE_MISMATCH",
    "REASON_OBJECTIVE_VERSION_MISMATCH",
    "REASON_BRIEF_MISMATCH",
    "REASON_SCORE_MODULE_MISMATCH",
    "REASON_FIXED_VALUE_INVALID",
    "bounds_payload",
    "bounds_identity",
    "recompute_bounds_hash",
    "score_payload",
    "score_identity",
    "recompute_score_hash",
    "score_module_for",
    "IdentityCheck",
    "check_bounds_identity",
    "check_score_identity",
    "check_identity_fields",
    "payload_to_json",
]
