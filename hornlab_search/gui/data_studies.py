"""Endpoint-ready, bounded study view models; no artifact or NPZ reads.

Inputs are already-resolved service summaries and artifact metadata. This adapter
never computes acoustic scores and never claims that file existence implies readiness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from typing import Any, Mapping

PHASES = ("overview", "data", "explain", "propose", "execute", "decide")
STATES = ("ready", "missing", "stale", "partial", "unknown", "dependency_missing", "failed", "interrupted")
MAX_ITEMS = 50
MAX_BYTES = 128_000


@dataclass(frozen=True)
class StudyPanel:
    phase: str
    status: str
    revision: int
    data: dict
    provenance: dict
    reasons: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def _json_value(value):
    """Return bounded JSON values; reject arrays/objects that could hide huge payloads."""
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > 4096:
            raise ValueError("string exceeds view limit")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite view value")
        return value
    if isinstance(value, (tuple, list)):
        if len(value) > MAX_ITEMS:
            raise ValueError("list exceeds view limit")
        return [_json_value(x) for x in value]
    if isinstance(value, Mapping):
        if len(value) > MAX_ITEMS or any(not isinstance(k, str) for k in value):
            raise ValueError("invalid view mapping")
        return {k: _json_value(v) for k, v in value.items()}
    raise ValueError("non-JSON view value")


def build_study_view(study: Mapping[str, Any], phase: str, artifact: Mapping | None = None) -> StudyPanel:
    """Build a panel from service data and typed artifact metadata, never from paths.

    A ready panel requires an explicit validated status and matching spec revision.
    Missing artifacts, revision drift and dependency states remain visible to callers.
    Provenance and units/direction are passed through, never synthesized.
    """
    if phase not in PHASES or not isinstance(study, Mapping):
        raise ValueError("invalid phase or study")
    revision = study.get("revision", study.get("spec_revision"))
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise ValueError("study revision missing")
    if artifact is None:
        return StudyPanel(phase, "missing", revision, {}, {}, ("artifact unavailable",))
    if not isinstance(artifact, Mapping):
        raise ValueError("artifact must be a mapping")
    state = artifact.get("status", "unknown")
    if state not in STATES:
        state = "unknown"
    if artifact.get("revision") != revision:
        state = "stale" if artifact.get("revision") is not None else "unknown"
    if state == "ready" and artifact.get("validated") is not True:
        state = "unknown"
    data = _json_value(artifact.get("data") or {})
    provenance = _json_value(artifact.get("provenance") or {})
    reasons = _json_value(artifact.get("reasons") or [])
    if not isinstance(data, dict) or not isinstance(provenance, dict) or not isinstance(reasons, list):
        raise ValueError("invalid panel data, provenance or reasons")
    if len(json.dumps([data, provenance, reasons], allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError("view exceeds payload limit")
    return StudyPanel(phase, state, revision, data, provenance, tuple(str(x) for x in reasons))


def study_summaries(studies, *, limit=50):
    """Return an explicit small allow-list of summary fields, never artifact contents."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_ITEMS:
        raise ValueError("invalid list limit")
    allowed = ("study_id", "id", "name", "question", "revision", "spec_revision", "status", "readiness")
    result = []
    for study in studies:
        if len(result) >= limit:
            break
        if not isinstance(study, Mapping):
            raise ValueError("invalid study summary")
        result.append(_json_value({k: study[k] for k in allowed if k in study}))
    return result
