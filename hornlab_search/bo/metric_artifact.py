"""Serialization + integrity checks for ``metric-training-v1`` artifacts (Pass 2).

A training artifact is only a valid *training* label when its bytes, arrays, component schema,
bounds identity and score identity all agree with the frozen task.  This module owns that contract:

* :func:`artifact_bytes` -- deterministic (fixed member order + fixed ZIP timestamps) ``.npz``
  with the arrays and a canonical-JSON ``manifest.json``.  Byte-identical for identical input;
  pickle is never used.
* :func:`artifact_from_bytes` -- the only loader.  It refuses truncated/garbage/foreign payloads,
  validates every array (float64, shape, sha256, finiteness), recomputes the manifest checksum,
  and never unpickles anything.
* :func:`validate_metric_training_artifact` -- recomputes the bounds/score identity from the
  recorded payloads and checks them against a live encoding / expected score / expected task.  A
  mismatch is a typed refusal, never repaired.

The module is dependency-light (numpy + the identity/contract helpers) so the study builder, the
package gate and offline tooling can validate without importing Torch or the scorer.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .metric_contracts import (
    METRIC_TRAINING_VERSION,
    canonical_json,
    component_names,
    component_schema,
    component_schema_hash,
    sha256_json,
    validate_components,
)
from .metric_identity import (
    REASON_BOUNDS_MISMATCH,
    REASON_BOUNDS_MISSING,
    REASON_BOUNDS_PAYLOAD_INVALID,
    REASON_OK,
    REASON_SCORE_MISMATCH,
    REASON_SCORE_MISSING,
    check_bounds_identity,
    check_identity_fields,
    check_score_identity,
    recompute_bounds_hash,
    recompute_score_hash,
    bounds_identity,
)

ARTIFACT_FORMAT = "metric-training-npz-v1"
ARTIFACT_KIND = "metric_training"

_ARRAY_ORDER = ("X", "J", "Y_components", "Y_phys", "G")
_REQUIRED_ARRAYS = ("X", "J", "Y_components")
_MANIFEST_MEMBER = "manifest.json"

STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

REASON_OK = "ok"
REASON_ZIP_INVALID = "artifact_zip_invalid"
REASON_ZIP_TRUNCATED = "artifact_zip_truncated"
REASON_FOREIGN_FORMAT = "artifact_format_foreign"
REASON_MANIFEST_MISSING = "artifact_manifest_missing"
REASON_MANIFEST_INVALID = "artifact_manifest_invalid"
REASON_MEMBER_MISSING = "artifact_member_missing"
REASON_MEMBER_UNEXPECTED = "artifact_member_unexpected"
REASON_PICKLE_REFUSED = "artifact_pickle_refused"
REASON_ARRAY_DTYPE = "artifact_array_dtype"
REASON_ARRAY_SHAPE = "artifact_array_shape"
REASON_ARRAY_SHA = "artifact_array_sha256"
REASON_ARRAY_NONFINITE = "artifact_array_nonfinite"
REASON_CHECKSUM_MISMATCH = "artifact_checksum_mismatch"
REASON_EXPECTED_CHECKSUM_MISMATCH = "artifact_expected_checksum_mismatch"
REASON_IDS_NOT_UNIQUE = "artifact_observation_ids_not_unique"
REASON_STATUS_INVALID = "artifact_status_invalid"
REASON_VERSION = "artifact_version_mismatch"
REASON_OBJECTIVE_VERSION = "artifact_objective_version_unsupported"
REASON_COMPONENT_SCHEMA = "artifact_component_schema_mismatch"
REASON_COMPONENT_SCHEMA_HASH = "artifact_component_schema_hash_mismatch"
REASON_COMPONENT_SCHEMA_HASH_MISSING = "artifact_component_schema_hash_missing"
REASON_J_ROW_MISMATCH = "artifact_j_row_mismatch"
REASON_X_OUT_OF_BOX = "artifact_x_out_of_box"
REASON_X_SHAPE = "artifact_x_shape"
REASON_BOUNDS_PAYLOAD_MISSING = "bounds_identity_payload_missing"
REASON_BOUNDS_ENCODING_INVALID = "artifact_encoding_bounds_invalid"
REASON_IDENTITY_FIELD = "artifact_identity_mismatch"
REASON_IDENTITY_FIELD_MISSING = "artifact_identity_missing"

#: Loader helpers refuse these outright: a metric artifact is data, never a pickled model.
_PICKLE_SUFFIXES = (".pkl", ".pickle", ".pt", ".pth", ".joblib", ".ckpt")
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


# --------------------------------------------------------------------------- result type


@dataclass(frozen=True)
class ArtifactCheck:
    """Tagged result of artifact serialization/validation."""

    status: str
    reason: str = REASON_OK
    detail: str | None = None
    reasons: tuple[str, ...] = ()
    checks: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "reasons": list(self.reasons),
            "checks": dict(self.checks),
        }


def _unavailable(reasons, *, detail: str | None = None, checks: dict | None = None) -> ArtifactCheck:
    ordered: list[str] = []
    for reason in reasons:
        if reason and reason not in ordered:
            ordered.append(str(reason))
    if not ordered:
        ordered.append(REASON_MANIFEST_INVALID)
    return ArtifactCheck(status=STATUS_UNAVAILABLE, reason=ordered[0],
                         detail=detail or "; ".join(ordered),
                         reasons=tuple(ordered), checks=dict(checks or {}))


# --------------------------------------------------------------------------- helpers


def _json_safe(value):
    """Coerce metadata to plain JSON values so canonical hashing cannot raise on numpy types."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, (bytes, bytearray)):
        return hashlib.sha256(bytes(value)).hexdigest()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in value]
    return str(value)


def _array_digest(array) -> dict:
    arr = np.ascontiguousarray(np.asarray(array, dtype=np.float64))
    return {
        "dtype": str(arr.dtype),
        "shape": [int(v) for v in arr.shape],
        "sha256": hashlib.sha256(arr.tobytes()).hexdigest(),
    }


def _manifest_core(artifact, arrays: Mapping[str, np.ndarray]) -> dict:
    _bookkeeping = {"artifact_checksum", "source_manifest_checksum"}
    meta = {str(k): v for k, v in dict(getattr(artifact, "metadata", None) or {}).items()
            if str(k) not in _bookkeeping}
    try:
        version = int(getattr(artifact, "objective_version", 0) or 0)
    except (TypeError, ValueError):
        version = 0
    schema_id = meta.get("component_schema")
    schema_hash = meta.get("component_schema_hash")
    if version in (10, 11):
        schema_id = schema_id or component_schema(version)["schema_id"]
        schema_hash = schema_hash or component_schema_hash(version)
    return {
        "format": ARTIFACT_FORMAT,
        "kind": ARTIFACT_KIND,
        "version": str(getattr(artifact, "version", METRIC_TRAINING_VERSION)
                       or METRIC_TRAINING_VERSION),
        "objective_version": version,
        "feature_names": [str(k) for k in (getattr(artifact, "feature_names", ()) or ())],
        "component_names": [str(k) for k in (getattr(artifact, "component_names", ()) or ())],
        "component_schema": schema_id,
        "component_schema_hash": schema_hash,
        "observation_ids": [str(v) for v in (getattr(artifact, "observation_ids", ()) or ())],
        "selected_ids": [str(v) for v in (getattr(artifact, "selected_ids", ()) or ())],
        "excluded": [_json_safe(e) for e in (getattr(artifact, "excluded", ()) or ())],
        "bounds_identity_payload": _json_safe(meta.get("bounds_identity_payload")),
        "bounds_hash": str(meta.get("bounds_hash") or ""),
        "score_identity_payload": _json_safe(meta.get("score_identity_payload")),
        "score_identity": str(meta.get("score_identity") or ""),
        "task_identity": str(meta.get("task_identity") or ""),
        "backend": str(meta.get("backend") or ""),
        "fidelity": str(meta.get("fidelity") or ""),
        "grid_hash": str(meta.get("grid_hash") or ""),
        "dependency_hash": str(meta.get("dependency_hash") or ""),
        "mesh_hash": str(meta.get("mesh_hash") or ""),
        "arrays": {name: _array_digest(arr) for name, arr in arrays.items()},
        "source_checksum": str(getattr(artifact, "checksum", "") or ""),
        "metadata": _json_safe(meta),
    }


def _artifact_arrays(artifact) -> dict:
    arrays: dict[str, np.ndarray] = {}
    for name in _ARRAY_ORDER:
        value = getattr(artifact, name, None)
        if value is None:
            continue
        arrays[name] = np.ascontiguousarray(np.asarray(value, dtype=np.float64))
    return arrays


def _content_checksum(artifact, arrays: Mapping[str, np.ndarray] | None = None) -> str:
    if arrays is None:
        arrays = _artifact_arrays(artifact)
    return sha256_json(_manifest_core(artifact, arrays))


def _write_member(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    archive.writestr(info, payload)


def _npy_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.lib.format.write_array(stream, np.asarray(array), allow_pickle=False)
    return stream.getvalue()


def _guard_name(name: str) -> None:
    lowered = str(name).lower()
    if lowered.endswith(_PICKLE_SUFFIXES):
        raise ValueError(f"{REASON_PICKLE_REFUSED}: {name!r}")


def _read_npy(payload: bytes, label: str) -> np.ndarray:
    try:
        return np.lib.format.read_array(io.BytesIO(payload), allow_pickle=False)
    except Exception as exc:  # noqa: BLE001 - a malformed member is a typed refusal
        raise ValueError(f"{REASON_MANIFEST_INVALID}: {label!r} is not a valid .npy array: "
                         f"{type(exc).__name__}: {exc}") from exc


# --------------------------------------------------------------------------- serialize


def artifact_bytes(artifact) -> bytes:
    """Deterministic ``.npz`` bytes for ``artifact``.

    Member order is fixed, ZIP timestamps are pinned and the manifest is canonical JSON, so two
    calls with the same input produce byte-identical output.  No pickle is used.
    """
    if artifact is None:
        raise ValueError(f"{REASON_STATUS_INVALID}: artifact is None")
    if getattr(artifact, "status", None) != STATUS_OK:
        raise ValueError(
            f"{REASON_STATUS_INVALID}: artifact status is {getattr(artifact, 'status', None)!r}")
    arrays = _artifact_arrays(artifact)
    for name in _REQUIRED_ARRAYS:
        if name not in arrays:
            raise ValueError(f"{REASON_MEMBER_MISSING}:{name}")
    core = _manifest_core(artifact, arrays)
    manifest = dict(core)
    manifest["artifact_checksum"] = sha256_json(core)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name in _ARRAY_ORDER:
            if name in arrays:
                _write_member(archive, f"{name}.npy", _npy_bytes(arrays[name]))
        _write_member(archive, _MANIFEST_MEMBER,
                      canonical_json(manifest).encode("utf-8"))
    return buffer.getvalue()


def artifact_from_bytes(blob, *, expected_checksum: str | None = None
                        ) -> tuple[Any | None, ArtifactCheck]:
    """Load and validate an artifact from bytes.  Returns ``(artifact|None, ArtifactCheck)``."""
    checks: dict = {}
    reasons: list[str] = []
    if not isinstance(blob, (bytes, bytearray)):
        return None, _unavailable([REASON_ZIP_INVALID], detail="blob is not bytes")

    try:
        archive = zipfile.ZipFile(io.BytesIO(bytes(blob)))
    except zipfile.BadZipFile as exc:
        reason = (REASON_ZIP_TRUNCATED if "end of" in str(exc).lower() else REASON_ZIP_INVALID)
        return None, _unavailable([reason], detail=f"{type(exc).__name__}: {exc}")
    except (EOFError, OSError) as exc:
        return None, _unavailable([REASON_ZIP_TRUNCATED],
                                  detail=f"{type(exc).__name__}: {exc}")

    with archive:
        names = list(archive.namelist())
        checks["members"] = list(names)
        for name in names:
            try:
                _guard_name(name)
            except ValueError as exc:
                return None, _unavailable([str(exc).split(":", 1)[0]], detail=str(exc))
        if _MANIFEST_MEMBER not in names:
            return None, _unavailable([REASON_MANIFEST_MISSING],
                                      detail="archive has no manifest.json")
        try:
            manifest = json.loads(archive.read(_MANIFEST_MEMBER).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            return None, _unavailable([REASON_MANIFEST_INVALID],
                                      detail=f"manifest.json is unreadable: "
                                             f"{type(exc).__name__}: {exc}")
        if not isinstance(manifest, Mapping):
            return None, _unavailable([REASON_MANIFEST_INVALID],
                                      detail="manifest.json is not a JSON object")
        if manifest.get("format") != ARTIFACT_FORMAT or manifest.get("kind") != ARTIFACT_KIND:
            return None, _unavailable(
                [REASON_FOREIGN_FORMAT],
                detail=f"format={manifest.get('format')!r} kind={manifest.get('kind')!r} "
                       f"!= {ARTIFACT_FORMAT!r}/{ARTIFACT_KIND!r}")

        manifest_arrays = manifest.get("arrays")
        if not isinstance(manifest_arrays, Mapping):
            return None, _unavailable([REASON_MANIFEST_INVALID],
                                      detail="manifest has no array digest table")
        expected_members = {f"{name}.npy" for name in manifest_arrays}
        expected_members.add(_MANIFEST_MEMBER)
        unexpected = sorted(set(names) - expected_members)
        if unexpected:
            return None, _unavailable([REASON_MEMBER_UNEXPECTED],
                                      detail=f"unexpected members: {unexpected}")
        missing = sorted(expected_members - set(names))
        if missing:
            return None, _unavailable([REASON_MEMBER_MISSING],
                                      detail=f"missing members: {missing}")

        arrays: dict[str, np.ndarray] = {}
        for name, digest in manifest_arrays.items():
            if name not in _ARRAY_ORDER:
                return None, _unavailable([REASON_MEMBER_UNEXPECTED],
                                          detail=f"unexpected array {name!r}")
            try:
                raw = archive.read(f"{name}.npy")
                arr = _read_npy(raw, name)
            except (KeyError, ValueError) as exc:
                return None, _unavailable([REASON_MANIFEST_INVALID], detail=str(exc))
            if arr.dtype != np.float64:
                reasons.append(f"{REASON_ARRAY_DTYPE}:{name}")
            try:
                shape = [int(v) for v in arr.shape]
            except (TypeError, ValueError):
                shape = []
            want_shape = list((digest or {}).get("shape") or [])
            if shape != want_shape:
                reasons.append(f"{REASON_ARRAY_SHAPE}:{name}")
            want_sha = str((digest or {}).get("sha256") or "")
            got_sha = hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()
            if want_sha != got_sha:
                reasons.append(f"{REASON_ARRAY_SHA}:{name}")
            if arr.size and not np.all(np.isfinite(arr)):
                reasons.append(f"{REASON_ARRAY_NONFINITE}:{name}")
            read_only = np.array(arr, dtype=np.float64, copy=True)
            read_only.setflags(write=False)
            arrays[name] = read_only
            checks[name] = {"dtype": str(arr.dtype), "shape": shape, "sha256": got_sha}

    for name in _REQUIRED_ARRAYS:
        if name not in arrays:
            reasons.append(f"{REASON_MEMBER_MISSING}:{name}")
    if reasons:
        return None, _unavailable(reasons, checks=checks)

    core = {str(k): v for k, v in manifest.items() if str(k) != "artifact_checksum"}
    stored_checksum = str(manifest.get("artifact_checksum") or "")
    try:
        recomputed_checksum = sha256_json(core)
    except (TypeError, ValueError) as exc:
        return None, _unavailable([REASON_MANIFEST_INVALID],
                                  detail=f"manifest is not canonically serializable: {exc}")
    if not stored_checksum or stored_checksum != recomputed_checksum:
        return None, _unavailable([REASON_CHECKSUM_MISMATCH],
                                  detail=f"stored {stored_checksum!r} != recomputed "
                                         f"{recomputed_checksum!r}", checks=checks)
    source_checksum = str(manifest.get("source_checksum") or "")
    if expected_checksum not in (None, ""):
        if str(expected_checksum) not in {stored_checksum, source_checksum}:
            return None, _unavailable(
                [REASON_EXPECTED_CHECKSUM_MISMATCH],
                detail=f"expected {expected_checksum!r}, artifact is {stored_checksum!r}",
                checks=checks)

    try:
        observation_ids = tuple(str(v) for v in (manifest.get("observation_ids") or ()))
        selected_ids = tuple(str(v) for v in (manifest.get("selected_ids") or ()))
    except (TypeError, ValueError):
        return None, _unavailable([REASON_MANIFEST_INVALID],
                                  detail="observation/selected IDs are not a string sequence")
    if len(set(observation_ids)) != len(observation_ids):
        return None, _unavailable([REASON_IDS_NOT_UNIQUE],
                                  detail="observation IDs are not unique", checks=checks)
    if len(set(selected_ids)) != len(selected_ids):
        return None, _unavailable([REASON_IDS_NOT_UNIQUE],
                                  detail="selected IDs are not unique", checks=checks)

    metadata = _json_safe(manifest.get("metadata") or {})
    if not isinstance(metadata, dict):
        metadata = {}
    metadata = dict(metadata)
    for key in ("bounds_identity_payload", "bounds_hash", "score_identity_payload",
                "score_identity", "task_identity", "backend", "fidelity", "grid_hash",
                "dependency_hash", "mesh_hash", "component_schema", "component_schema_hash"):
        value = manifest.get(key)
        if value not in (None, "") and key not in metadata:
            metadata[key] = value
    metadata["artifact_checksum"] = stored_checksum
    if source_checksum:
        metadata["source_manifest_checksum"] = source_checksum

    from .metric_contracts import MetricTrainingArtifact

    returned_checksum = source_checksum or stored_checksum
    try:
        artifact = MetricTrainingArtifact(
            status=STATUS_OK,
            objective_version=int(manifest.get("objective_version", 0) or 0),
            feature_names=tuple(str(v) for v in (manifest.get("feature_names") or ())),
            component_names=tuple(str(v) for v in (manifest.get("component_names") or ())),
            X=arrays.get("X"),
            J=arrays.get("J"),
            Y_components=arrays.get("Y_components"),
            Y_phys=arrays.get("Y_phys"),
            G=arrays.get("G"),
            observation_ids=observation_ids,
            selected_ids=selected_ids,
            excluded=tuple(dict(e) for e in (manifest.get("excluded") or ())),
            metadata=metadata,
            checksum=returned_checksum,
            version=str(manifest.get("version") or METRIC_TRAINING_VERSION),
        )
    except (TypeError, ValueError) as exc:
        return None, _unavailable([REASON_MANIFEST_INVALID],
                                  detail=f"artifact reconstruction failed: {exc}",
                                  checks=checks)
    checks["artifact_checksum"] = stored_checksum
    return artifact, ArtifactCheck(status=STATUS_OK, reason=REASON_OK, checks=checks)


def load_artifact_file(path, *, expected_checksum: str | None = None
                       ) -> tuple[Any | None, ArtifactCheck]:
    """Read an artifact file, refusing pickled-model extensions before touching the bytes."""
    name = Path(str(path)).name
    try:
        _guard_name(name)
    except ValueError as exc:
        return None, _unavailable([REASON_PICKLE_REFUSED], detail=str(exc))
    try:
        blob = Path(str(path)).read_bytes()
    except OSError as exc:
        return None, _unavailable([REASON_ZIP_INVALID],
                                  detail=f"artifact file is unreadable: {exc}")
    return artifact_from_bytes(blob, expected_checksum=expected_checksum)


# --------------------------------------------------------------------------- validate


def validate_metric_training_artifact(artifact, *, encoding=None,
                                      expected_bounds_hash: str | None = None,
                                      expected_score: Mapping[str, Any] | None = None,
                                      expected_task: Mapping[str, Any] | None = None
                                      ) -> ArtifactCheck:
    """Validate artifact integrity and, when supplied, every frozen identity it depends on.

    Identity arguments are opt-in so Pass 1 synthetic artifacts keep working.  Whenever a payload
    is present it is re-hashed; whenever an expected identity is supplied a missing/mismatched
    identity is a typed refusal.
    """
    checks: dict = {}
    reasons: list[str] = []

    if artifact is None:
        return _unavailable([REASON_STATUS_INVALID], detail="artifact is None")
    status = getattr(artifact, "status", None)
    checks["status"] = status
    if status != STATUS_OK or not bool(getattr(artifact, "ok", False)):
        reasons.append(REASON_STATUS_INVALID)

    try:
        version = int(getattr(artifact, "objective_version", 0) or 0)
    except (TypeError, ValueError):
        version = 0
    checks["objective_version"] = version
    if version not in (10, 11):
        reasons.append(REASON_OBJECTIVE_VERSION)
    if str(getattr(artifact, "version", "") or "") != METRIC_TRAINING_VERSION:
        reasons.append(REASON_VERSION)

    arrays: dict[str, np.ndarray] = {}
    for name in _ARRAY_ORDER:
        value = getattr(artifact, name, None)
        if value is None:
            if name in _REQUIRED_ARRAYS:
                reasons.append(f"{REASON_MEMBER_MISSING}:{name}")
            continue
        try:
            arr = np.asarray(value)
        except Exception:  # noqa: BLE001
            reasons.append(f"{REASON_ARRAY_DTYPE}:{name}")
            continue
        checks[name] = {"dtype": str(arr.dtype), "shape": [int(v) for v in arr.shape]}
        if arr.dtype != np.float64:
            reasons.append(f"{REASON_ARRAY_DTYPE}:{name}")
        if not np.all(np.isfinite(arr)):
            reasons.append(f"{REASON_ARRAY_NONFINITE}:{name}")
        arrays[name] = np.ascontiguousarray(arr, dtype=np.float64)

    X = arrays.get("X")
    J = arrays.get("J")
    Y = arrays.get("Y_components")
    expected_names: tuple[str, ...] = ()
    if version in (10, 11):
        expected_names = tuple(component_names(version))
    names = tuple(str(k) for k in (getattr(artifact, "component_names", ()) or ()))
    checks["component_names"] = list(names)
    if version in (10, 11) and names != expected_names:
        reasons.append(REASON_COMPONENT_SCHEMA)

    meta = dict(getattr(artifact, "metadata", None) or {})
    if version in (10, 11):
        schema_id = meta.get("component_schema")
        if schema_id and str(schema_id) != component_schema(version)["schema_id"]:
            reasons.append(REASON_COMPONENT_SCHEMA)
        stored_schema_hash = meta.get("component_schema_hash")
        live_schema_hash = component_schema_hash(version)
        if stored_schema_hash:
            if str(stored_schema_hash) != live_schema_hash:
                reasons.append(REASON_COMPONENT_SCHEMA_HASH)
        elif any(v is not None for v in (encoding, expected_bounds_hash, expected_score,
                                         expected_task)):
            reasons.append(REASON_COMPONENT_SCHEMA_HASH_MISSING)

    # J reconstruction and X bounds.
    if X is not None and J is not None and Y is not None and version in (10, 11):
        J_flat = np.asarray(J, dtype=np.float64).reshape(-1)
        if X.ndim != 2 or Y.ndim != 2 or X.shape[0] != Y.shape[0] or Y.shape[0] != J_flat.size:
            reasons.append(REASON_X_SHAPE)
        elif Y.shape[1] != len(expected_names):
            reasons.append(REASON_COMPONENT_SCHEMA)
        else:
            if np.any((X < 0.0) | (X > 1.0)):
                reasons.append(REASON_X_OUT_OF_BOX)
            for row in range(J_flat.size):
                ok, _reconstructed, _why = validate_components(version, Y[row], J_flat[row])
                if not ok:
                    reasons.append(f"{REASON_J_ROW_MISMATCH}:{row}")
                    break

    # Serialized-artifact checksum (only present on artifacts that came back through bytes).
    recorded_checksum = str(meta.get("artifact_checksum") or "")
    if recorded_checksum:
        try:
            actual = _content_checksum(artifact, arrays)
        except Exception:  # noqa: BLE001
            actual = None
        checks["artifact_checksum"] = recorded_checksum
        if actual != recorded_checksum:
            reasons.append(REASON_CHECKSUM_MISMATCH)

    # ---- bounds identity
    payload = meta.get("bounds_identity_payload")
    stored_bounds = str(meta.get("bounds_hash") or "").strip()
    target_bounds = ""
    if expected_bounds_hash is not None:
        target_bounds = str(expected_bounds_hash).strip()
        if not target_bounds:
            reasons.append(REASON_BOUNDS_MISSING)
    if encoding is not None:
        try:
            live = bounds_identity(encoding, strict=True)
        except ValueError as exc:
            reasons.append(REASON_BOUNDS_ENCODING_INVALID)
            checks["encoding_bounds_error"] = str(exc)
        else:
            checks["encoding_bounds_hash"] = live
            if target_bounds and live != target_bounds:
                reasons.append(REASON_BOUNDS_MISMATCH)
            target_bounds = target_bounds or live
    if target_bounds:
        if not stored_bounds:
            reasons.append(REASON_BOUNDS_MISSING)
        elif stored_bounds != target_bounds:
            reasons.append(REASON_BOUNDS_MISMATCH)
    if payload is not None:
        try:
            recomputed_bounds = recompute_bounds_hash(payload)
        except ValueError as exc:
            reasons.append(REASON_BOUNDS_PAYLOAD_INVALID)
            checks["bounds_payload_error"] = str(exc)
        else:
            checks["bounds_payload_hash"] = recomputed_bounds
            if stored_bounds and recomputed_bounds != stored_bounds:
                reasons.append(REASON_BOUNDS_MISMATCH)
            if target_bounds and recomputed_bounds != target_bounds:
                reasons.append(REASON_BOUNDS_MISMATCH)
    elif target_bounds:
        reasons.append(REASON_BOUNDS_PAYLOAD_MISSING)

    # ---- score identity
    if expected_score is not None:
        spec = dict(expected_score)
        score_check = check_score_identity(
            metadata=meta,
            objective_version=int(spec.get("objective_version") or 0),
            brief_hash=str(spec.get("brief_hash") or ""),
            score_hash=str(spec.get("score_hash") or ""),
            score_module=(None if spec.get("score_module") is None
                          else str(spec.get("score_module"))))
        checks["score_identity"] = score_check.to_dict()
        if not score_check.ok:
            reasons.append(score_check.reason or REASON_SCORE_MISMATCH)
    else:
        score_payload = meta.get("score_identity_payload")
        if score_payload is not None:
            try:
                recomputed_score = recompute_score_hash(score_payload)
            except ValueError as exc:
                reasons.append(REASON_SCORE_MISMATCH)
                checks["score_payload_error"] = str(exc)
            else:
                checks["score_payload_hash"] = recomputed_score
                recorded_score = str(meta.get("score_identity") or "")
                if recorded_score and recorded_score != recomputed_score:
                    reasons.append(REASON_SCORE_MISMATCH)

    # ---- task/backend/fidelity/grid/dependency/mesh identity
    if expected_task is not None:
        allowed = ("task_identity", "backend", "fidelity", "grid_hash", "dependency_hash",
                   "mesh_hash")
        expected_fields = {str(k): v for k, v in dict(expected_task).items() if str(k) in allowed}
        if expected_fields:
            observed = {str(k): meta.get(k) for k in expected_fields}
            task_check = check_identity_fields(
                expected=expected_fields, observed=observed,
                fields=tuple(expected_fields),
                reason=REASON_IDENTITY_FIELD,
                missing_reason=REASON_IDENTITY_FIELD_MISSING)
            checks["task_identity"] = task_check.to_dict()
            if not task_check.ok:
                reasons.append(task_check.reason or REASON_IDENTITY_FIELD)

    if reasons:
        return _unavailable(reasons, checks=checks)
    return ArtifactCheck(status=STATUS_OK, reason=REASON_OK, checks=checks)


__all__ = [
    "ARTIFACT_FORMAT",
    "ARTIFACT_KIND",
    "STATUS_OK",
    "STATUS_UNAVAILABLE",
    "REASON_OK",
    "REASON_ZIP_INVALID",
    "REASON_ZIP_TRUNCATED",
    "REASON_FOREIGN_FORMAT",
    "REASON_MANIFEST_MISSING",
    "REASON_MANIFEST_INVALID",
    "REASON_MEMBER_MISSING",
    "REASON_MEMBER_UNEXPECTED",
    "REASON_PICKLE_REFUSED",
    "REASON_ARRAY_DTYPE",
    "REASON_ARRAY_SHAPE",
    "REASON_ARRAY_SHA",
    "REASON_ARRAY_NONFINITE",
    "REASON_CHECKSUM_MISMATCH",
    "REASON_EXPECTED_CHECKSUM_MISMATCH",
    "REASON_IDS_NOT_UNIQUE",
    "REASON_STATUS_INVALID",
    "REASON_VERSION",
    "REASON_OBJECTIVE_VERSION",
    "REASON_COMPONENT_SCHEMA",
    "REASON_COMPONENT_SCHEMA_HASH",
    "REASON_COMPONENT_SCHEMA_HASH_MISSING",
    "REASON_J_ROW_MISMATCH",
    "REASON_X_OUT_OF_BOX",
    "REASON_X_SHAPE",
    "REASON_BOUNDS_MISSING",
    "REASON_BOUNDS_MISMATCH",
    "REASON_BOUNDS_PAYLOAD_INVALID",
    "REASON_BOUNDS_PAYLOAD_MISSING",
    "REASON_BOUNDS_ENCODING_INVALID",
    "REASON_SCORE_MISSING",
    "REASON_SCORE_MISMATCH",
    "REASON_IDENTITY_FIELD",
    "REASON_IDENTITY_FIELD_MISSING",
    "ArtifactCheck",
    "artifact_bytes",
    "artifact_from_bytes",
    "load_artifact_file",
    "validate_metric_training_artifact",
]
