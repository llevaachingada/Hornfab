"""Endpoint-ready, bounded study view models; no artifact or NPZ reads.

Inputs are already-resolved service summaries and artifact metadata. This adapter
never computes acoustic scores and never claims that file existence implies readiness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import re
from typing import Any, Mapping

PHASES = ("overview", "data", "explain", "propose", "execute", "decide")
STATES = ("ready", "missing", "stale", "partial", "unknown", "dependency_missing", "failed", "interrupted")
MAX_ITEMS = 50
MAX_BYTES = 128_000

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_POLICY_STATUSES = frozenset(STATES) | {"unavailable", "capability_missing", "pool_exhausted", "no_data", "fit_failed", "busy"}
_ARTIFACT_STATUSES = frozenset(STATES) | {"available", "unavailable"}
_PROGRESS_KEYS = ("proposed", "started", "solved", "cached", "refused", "infeasible",
                  "infrastructure_failed", "verified", "unknown")
_EXECUTE_ACTION_KINDS = frozenset({
    "save_draft", "select_evidence", "analyze", "propose", "package", "launch",
    "cancel", "decision", "revise", "save_seeds", "create_child",
})

# Frozen fallback selector labels. The ``mode`` is the backend proposal-policy value; the
# ``id``/``label`` are the frozen public labels used before a panel supplies explicit cards.
POLICY_FALLBACKS = (
    {"id": "scalar", "mode": "scalar", "label": "scalar",
     "requires": ["training_set"], "verification_mode": "scalar"},
    {"id": "coverage-ripple", "mode": "pareto", "label": "coverage-ripple",
     "requires": ["cohort", "metric_observations"], "verification_mode": "pareto"},
    {"id": "cma-seed", "mode": "cma_seed", "label": "cma-seed",
     "requires": ["seeds"], "verification_mode": "scalar"},
    {"id": "exploration", "mode": "exploration", "label": "exploration",
     "requires": ["pool"], "verification_mode": "scalar"},
)


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


# --------------------------------------------------------------------------- policy cards


def _policy_card(item: Mapping[str, Any]) -> dict:
    pid = item.get("id")
    if not isinstance(pid, str) or not pid or len(pid) > 128:
        raise ValueError("invalid policy id")
    mode = item.get("mode", pid)
    if not isinstance(mode, str) or not mode or len(mode) > 128:
        raise ValueError("invalid proposal policy mode")
    label = item.get("label", pid)
    if not isinstance(label, str) or not label:
        raise ValueError("invalid policy label")
    status = item.get("status", "unknown")
    if not isinstance(status, str) or status not in _POLICY_STATUSES:
        status = "unknown"
    reason = item.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("invalid policy reason")
    if status != "ready" and not reason:
        reason = "Policy is unavailable; no reason was recorded."
    requires = item.get("requires", [])
    if not isinstance(requires, (list, tuple)) or len(requires) > MAX_ITEMS:
        raise ValueError("invalid policy requirements")
    if any(not isinstance(x, str) or len(x) > 128 for x in requires):
        raise ValueError("invalid policy requirement")
    verification_mode = item.get("verification_mode")
    if verification_mode is not None and not isinstance(verification_mode, str):
        raise ValueError("invalid policy verification mode")
    return {
        "id": pid,
        "mode": mode,
        "label": label,
        "status": status,
        "reason": reason,
        "requires": list(requires),
        "verification_mode": verification_mode,
        # Readiness is only ever the panel's explicit ``ready`` status.
        "available": status == "ready",
    }


def policy_cards(policies) -> list[dict]:
    """Bounded policy selector cards with explicit status/reason.

    ``policies`` is the panel's ``policies`` list (``{id,label,status,reason,requires,
    verification_mode}``). When absent, the frozen scalar/coverage-ripple/cma-seed/
    exploration labels are returned with status ``unknown`` — never inferred from files.
    """
    if policies is None:
        policies = ()
    if not isinstance(policies, (list, tuple)) or len(policies) > MAX_ITEMS:
        raise ValueError("policies must be a bounded list")
    if not policies:
        return [dict(card, status="unknown", available=False,
                     reason="Policy capabilities are not present in this panel.")
                for card in POLICY_FALLBACKS]
    cards = []
    for item in policies:
        if not isinstance(item, Mapping):
            raise ValueError("invalid policy card")
        cards.append(_policy_card(item))
    return cards


# --------------------------------------------------------------------------- execute view


def _bounded_mapping(value, name: str):
    if value is None:
        return None
    bounded = _json_value(value)
    if not isinstance(bounded, dict):
        raise ValueError(f"{name} must be a mapping")
    return bounded


def _optional_revision(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("invalid package revision")
    return value


def _sanitize_actions(actions) -> list[dict]:
    if actions is None:
        return []
    if not isinstance(actions, (list, tuple)) or len(actions) > MAX_ITEMS:
        raise ValueError("actions must be a bounded list")
    out = []
    for item in actions:
        if not isinstance(item, Mapping):
            raise ValueError("invalid action")
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in _EXECUTE_ACTION_KINDS:
            continue
        entry = {"kind": kind, "enabled": item.get("enabled") is True}
        if item.get("label") is not None:
            if not isinstance(item["label"], str):
                raise ValueError("invalid action label")
            entry["label"] = item["label"]
        for key in ("package_hash", "job_id", "job_status", "package_id", "package_status",
                    "seed_pack_id"):
            if key in item and item[key] is not None:
                if not isinstance(item[key], str):
                    raise ValueError(f"invalid action {key}")
                entry[key] = item[key]
        if "package_revision" in item and item["package_revision"] is not None:
            entry["package_revision"] = _optional_revision(item["package_revision"])
        out.append(entry)
    return out


def execute_view(data, *, status: str | None = None, reason: str | None = None) -> dict:
    """Bounded execute-page view model from an already-resolved panel.

    Passes through explicit package/budget/lane/deadline/stop-recovery/verification/progress
    values, validates them as bounded JSON, and never computes a score or a readiness claim.
    """
    if data is None:
        payload = {}
        state = "unknown"
        why = "Execution state is unknown; no validated panel data was provided."
    else:
        if not isinstance(data, Mapping):
            raise ValueError("execution view requires a mapping")
        payload = _json_value(dict(data))
        if not isinstance(payload, dict):
            raise ValueError("execution view requires a mapping")
        state = status if isinstance(status, str) and status else payload.get("status", "unknown")
        why = reason if reason is not None else payload.get("reason")
    if not isinstance(state, str) or state not in STATES:
        state = "unknown"
    if why is not None and not isinstance(why, str):
        raise ValueError("invalid execution reason")
    if state != "ready" and not why:
        why = "Execution state is not validated; no reason was recorded."

    package = _bounded_mapping(payload.get("package"), "package")
    package_hash = payload.get("package_hash")
    if package_hash is None and package is not None:
        package_hash = package.get("hash", package.get("package_hash", package.get("sha256")))
    if package_hash is not None:
        if not isinstance(package_hash, str) or not package_hash or len(package_hash) > 128:
            raise ValueError("invalid package hash")
    package_revision = payload.get("package_revision")
    if package_revision is None and package is not None:
        package_revision = package.get("revision")
    package_revision = _optional_revision(package_revision)

    lane = payload.get("lane")
    if lane is not None:
        if not isinstance(lane, str) or len(lane) > 64:
            raise ValueError("invalid lane")
    deadline = payload.get("deadline")
    if deadline is not None:
        deadline = _json_value(deadline)
        if not isinstance(deadline, (str, int, float, bool, dict)):
            raise ValueError("invalid deadline")

    stop_recovery = _bounded_mapping(
        payload.get("stop_recovery", payload.get("stop_rules")), "stop_recovery")

    verification = None
    raw_verification = payload.get("verification", payload.get("verification_policy"))
    if raw_verification is not None:
        if isinstance(raw_verification, str):
            verification = {"description": raw_verification[:1000]}
        elif isinstance(raw_verification, Mapping):
            bounded = _json_value(dict(raw_verification))
            if not isinstance(bounded, dict):
                raise ValueError("invalid verification policy")
            verification = {}
            for key in ("finalists", "audits"):
                if key in bounded:
                    value = bounded[key]
                    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                        raise ValueError("verification counts must be nonnegative integers")
                    verification[key] = value
            for key in ("mode", "description", "policy"):
                if key in bounded:
                    if not isinstance(bounded[key], str):
                        raise ValueError("invalid verification policy field")
                    verification[key] = bounded[key]
            if not verification:
                verification = bounded
        else:
            raise ValueError("invalid verification policy")

    progress = None
    raw_progress = payload.get("progress")
    if raw_progress is not None:
        if not isinstance(raw_progress, Mapping):
            raise ValueError("progress must be a mapping")
        unknown = set(raw_progress) - set(_PROGRESS_KEYS)
        if unknown:
            raise ValueError(f"unknown progress counts: {sorted(unknown)!r}")
        progress = {}
        for key in _PROGRESS_KEYS:
            if key in raw_progress:
                value = raw_progress[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError("progress counts must be nonnegative integers")
                progress[key] = value

    job = None
    raw_job = payload.get("job")
    if raw_job is not None:
        if not isinstance(raw_job, Mapping):
            raise ValueError("invalid job")
        bounded = _json_value(dict(raw_job))
        if not isinstance(bounded, dict):
            raise ValueError("invalid job")
        job = {key: bounded[key] for key in ("id", "kind", "status") if key in bounded}
        if not job:
            raise ValueError("invalid job")
    else:
        job_id = payload.get("job_id")
        job_status = payload.get("job_status")
        if job_id is not None or job_status is not None:
            job = {}
            if job_id is not None:
                if not isinstance(job_id, str) or not _ID_RE.match(job_id):
                    raise ValueError("invalid job id")
                job["id"] = job_id
            if job_status is not None:
                if not isinstance(job_status, str) or len(job_status) > 64:
                    raise ValueError("invalid job status")
                job["status"] = job_status

    result = {
        "status": state,
        "reason": why,
        "package": package,
        "package_hash": package_hash,
        "package_revision": package_revision,
        "budget": _bounded_mapping(payload.get("budget"), "budget"),
        "lane": lane,
        "deadline": deadline,
        "stop_recovery": stop_recovery,
        "verification": verification,
        "progress": progress,
        "job": job,
        "actions": _sanitize_actions(payload.get("actions")),
        "score_math": False,
    }
    if len(json.dumps(result, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError("execution view exceeds payload limit")
    return result


# --------------------------------------------------------------------------- artifact panel


def artifact_panel(artifact) -> dict:
    """Bounded typed artifact metadata; binary/NPZ arrays are never loaded or returned."""
    if artifact is None:
        return {
            "status": "missing",
            "reason": "No artifact reference was supplied.",
            "kind": None,
            "sha256": None,
            "revision": None,
            "data": {},
            "provenance": {},
            "reasons": [],
            "metadata_only": True,
            "arrays_included": False,
        }
    if not isinstance(artifact, Mapping):
        raise ValueError("artifact must be a mapping")
    status = artifact.get("status", "unknown")
    if not isinstance(status, str) or status not in _ARTIFACT_STATUSES:
        status = "unknown"
    reason = artifact.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("invalid artifact reason")
    if status == "available":
        # Registry availability is not semantic validation. Only an explicit
        # ``validated: true`` may render as ready; otherwise stay unknown and say why.
        status = "ready" if artifact.get("validated") is True else "unknown"
        if status == "unknown" and not reason:
            reason = ("Artifact content is registered, but its schema/dependencies were not "
                      "validated in this view.")
    if status == "ready" and artifact.get("validated") is False:
        status = "unknown"
        reason = reason or "Artifact is not validated."
    if status not in ("ready", "available") and not reason:
        reason = "Artifact is unavailable; no reason was recorded."

    kind = artifact.get("kind")
    if kind is not None:
        if not isinstance(kind, str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$", kind):
            raise ValueError("invalid artifact kind")
    sha256 = artifact.get("sha256")
    if sha256 is not None:
        if not isinstance(sha256, str) or not _SHA256_RE.match(sha256):
            raise ValueError("invalid artifact sha256")
    revision = _optional_revision(artifact.get("revision"))

    data = _json_value(artifact.get("data") or {})
    if not isinstance(data, dict):
        raise ValueError("artifact data must be a mapping")
    provenance = _json_value(artifact.get("provenance") or {})
    if not isinstance(provenance, dict):
        raise ValueError("artifact provenance must be a mapping")
    reasons = _json_value(artifact.get("reasons") or [])
    if not isinstance(reasons, list):
        raise ValueError("artifact reasons must be a list")

    result = {
        "status": status,
        "reason": reason,
        "kind": kind,
        "sha256": sha256,
        "revision": revision,
        "data": data,
        "provenance": provenance,
        "reasons": [str(x) for x in reasons],
        "metadata_only": True,
        "arrays_included": False,
    }
    if len(json.dumps(result, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError("artifact view exceeds payload limit")
    return result
