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


def workflow_panel(service, study, phase, artifact=None, *, root, launcher_available=False):
    """Add registry-backed next steps without equating predictions with measurements."""
    import importlib.util
    from hornlab_search.studies.package import verify_package
    sid, revision = study["id"], study["revision"]
    kinds = ("snapshot", "training_manifest", "analysis", "model", "pool", "proposal", "package", "results", "verification")
    metadata = {kind: service.get_artifact_metadata(sid, kind) for kind in kinds}
    def read(kind):
        if metadata[kind].get("status") != "available":
            return {}
        view = service.artifact_view(sid, kind)
        return view.get("data") if isinstance(view.get("data"), dict) else {}
    manifest, proposal, package = read("training_manifest"), read("proposal"), read("package")
    import subprocess
    import sys
    from pathlib import Path
    from hornlab_search.studies.production import study_interpreter
    interpreter = study_interpreter(root)
    engine = all(importlib.util.find_spec(name) is not None for name in ("torch", "botorch", "gpytorch", "hornlab_mesher"))
    if interpreter.resolve() != Path(sys.executable).resolve():
        try:
            probe = subprocess.run([str(interpreter), "-c", "import importlib.util; print(all(importlib.util.find_spec(n) is not None for n in ('torch','botorch','gpytorch','hornlab_mesher')))"],
                                   capture_output=True, text=True, timeout=10)
            engine = probe.returncode == 0 and probe.stdout.strip() == "True"
        except (OSError, subprocess.TimeoutExpired):
            engine = False
    sufficient = manifest.get("status") == "ok" and int(manifest.get("n", 0)) >= int(manifest.get("n_min", 16))
    jobs = service.list_cpu_jobs(sid, limit=10)
    active = next((job for job in jobs if job["status"] in ("queued", "running", "unknown")), None)
    scalar_ready = engine and sufficient
    policy = study.get("spec", {}).get("policy") or {}
    current_policy = policy.get("proposal_policy") or policy.get("mode") or "scalar"
    reason = ("BoTorch engine is unavailable in the GUI interpreter." if not engine else
              "Build a compatible training cohort with enough eligible unique observations." if not sufficient else
              "Scalar score model is available; proposal still requires geometry validation.")
    policies = [dict(card, status="ready" if card["mode"] == "scalar" and scalar_ready else "unavailable",
                     reason=reason if card["mode"] == "scalar" else "This first production workflow supports scalar policy only.")
                for card in POLICY_FALLBACKS]
    data = dict((artifact or {}).get("data") or {})
    data.update({"current_policy": current_policy, "policies": policies,
                 "readiness": {"engine_available": engine, "eligible_rows": manifest.get("n"),
                               "minimum_rows": manifest.get("n_min"), "reason": reason},
                 "artifacts": [{"kind": k, "sha256": m["sha256"]} for k, m in metadata.items() if m.get("status") == "available"],
                 "actions": []})
    action = lambda kind, label, enabled, **extra: {"kind": kind, "label": label, "enabled": enabled, **extra}
    if phase in ("overview", "data", "explain"):
        data["actions"].append(action("analyze", "Build snapshot and analyze compatible data", active is None,
                                      payload={"package_hash": None}))
    if phase == "propose":
        data["actions"].append(action("propose", "Generate scalar proposal", scalar_ready and current_policy == "scalar" and active is None,
                                      payload={"package_hash": None}))
        if proposal.get("candidate"):
            data["candidates"] = [{"id": proposal["candidate"].get("candidate_id"),
                                   "j": proposal.get("predicted"), "params": proposal["candidate"].get("params"),
                                   "selection_reason": proposal.get("selection_reason"), "measured": False}]
    if phase in ("propose", "execute"):
        data["actions"].append(action("package", "Prepare immutable solve package", not package and proposal.get("status") == "ok" and current_policy == "scalar" and active is None))
    if phase == "decide":
        verification = read("verification")
        selection = verification.get("selection") or {}
        selected = set(selection.get("finalists") or ()) | set(selection.get("audits") or ())
        verified = set(verification.get("verified_geometry_ids") or ())
        has_verification = (bool(selected) and selected <= verified
                            and not selection.get("shortfall") and not selection.get("audit_shortfall"))
        data["actions"].append(action("decision", "Record study decision", True,
            allowed_outcomes=["inconclusive", "accept", "reject"] if has_verification else ["inconclusive"],
            reason=("Review the measured verification evidence before accepting or rejecting the study."
                    if has_verification else "Verification evidence is missing or partial. Record an inconclusive decision with a rationale, or complete verification first.")))
    if package:
        try:
            package = verify_package({"package_id": metadata["package"]["sha256"], **package})
            data.update({"package": package, "package_hash": package["package_id"], "package_revision": revision})
            from hornlab_search.studies.production import execution_capability
            capability = execution_capability(service, package, root=root)
            data["execution_capability"] = capability
            if phase == "execute":
                from hornlab_search.studies.service import DraftAttemptJournal
                data["call_counts"] = DraftAttemptJournal(service).state(package["package_id"])
                with service.store.connect() as conn:
                    package_row = conn.execute("SELECT status,active,cancelled FROM packages WHERE id=? AND study_id=?",
                                               (package["package_id"], sid)).fetchone()
                    attempts = conn.execute("SELECT kind,status,result_json FROM attempts WHERE package_id=?",
                                            (package["package_id"],)).fetchall()
                launched = package_row is not None
                if package_row:
                    data["run_status"] = dict(package_row)
                    results = [(row["kind"], json.loads(row["result_json"])) for row in attempts if row["result_json"]]
                    data["progress"] = {
                        "proposed": len(attempts), "started": data["call_counts"]["total_calls"],
                        "solved": sum(bool(r.get("physical_measurement")) for _, r in results),
                        "cached": sum(r.get("outcome") == "cached" for _, r in results),
                        "refused": sum(r.get("outcome") == "cheap_refusal" for _, r in results),
                        "infrastructure_failed": sum(r.get("outcome") in ("infrastructure_failure", "solver_failure") for _, r in results),
                        "verified": sum(k in ("verify", "audit") and bool(r.get("physical_measurement")) for k, r in results),
                        "unknown": sum(row["status"] == "unknown" for row in attempts),
                    }
                data["actions"].append(action("launch", "Launch serial solve study",
                    launcher_available and capability.get("status") == "ok" and not launched, package_hash=package["package_id"], package_revision=revision))
                data["actions"].append(action("cancel", "Stop after current candidate", launched and bool(package_row["active"]),
                    package_id=package["package_id"], package_status="running"))
        except (ValueError, ImportError) as exc:
            data["execution_capability"] = {"status": "unavailable", "reason": str(exc)}
    if active:
        data["job"] = {"id": active["id"], "status": active["status"], "fields": active.get("fields")}
        data["actions"].append(action("cancel", "Cancel analysis job", True, job_id=active["id"], job_status=active["status"]))
    data, _ = bounded_preview(data)
    # Preserve missing/unknown evidence status independently of safe preparation actions.
    state = (artifact or {}).get("status", "missing")
    reasons = list((artifact or {}).get("reasons") or [])
    if phase == "execute" and data.get("run_status"):
        state = "partial"
        reasons = [r for r in reasons if "not launched" not in r and not r.startswith("No run results are recorded")]
        run_status = data["run_status"]
        status_label = "cancellation requested" if run_status.get("cancelled") else run_status.get("status", "unknown")
        reasons.insert(0, f"Study execution status: {status_label}. Progress comes from the durable attempt journal; verification evidence is published after completion.")
    if phase == "propose" and proposal.get("schema") == "study-proposal-v1" and proposal.get("status") == "ok":
        # Readiness is narrow: the known advisory schema and its entire registered
        # dependency graph must refer to this revision and content-addressed bytes.
        checked = set()
        def graph_valid(kind, expected_hash=None, ancestors=frozenset()):
            if kind in ancestors:
                return False
            meta = service.get_artifact_metadata(sid, kind)
            if (meta.get("status") != "available" or meta.get("revision") != revision
                    or (expected_hash is not None and meta.get("sha256") != expected_hash)):
                return False
            if kind in checked:
                return True
            deps = meta.get("dependencies") or {}
            if kind == "proposal" and not {"snapshot", "training", "analysis", "model", "pool", "training_manifest"} <= set(deps):
                return False
            if not all(graph_valid(dep, sha, ancestors | {kind}) for dep, sha in deps.items()):
                return False
            checked.add(kind)
            return True
        if (manifest.get("schema") == "study-training-manifest-v1" and manifest.get("status") == "ok"
                and proposal.get("revision") == revision and proposal.get("study_id") == sid
                and proposal.get("candidate") and graph_valid("proposal")):
            state = "ready"
            reasons = [r for r in reasons if r != "Artifact semantics and dependencies are not yet validated."]
            reasons.insert(0, "Advisory proposal and current-revision artifact dependencies validated. Predicted scores remain unmeasured.")
    if current_policy != "scalar":
        reasons.insert(0, f"Current policy is {current_policy}; this production workflow supports scalar only. Select scalar to continue.")
    return build_study_view(study, phase, {"status": state, "validated": state == "ready", "revision": revision,
        "data": data, "provenance": {**((artifact or {}).get("provenance") or {}), "spec_hash": study["spec_hash"]},
        "reasons": reasons}).to_dict()


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


# --------------------------------------------------------------------------- bounded preview


def bounded_preview(value, *, max_items: int = MAX_ITEMS, max_bytes: int = MAX_BYTES - 8_000):
    """Return ``(preview, truncations)``: a display-only copy of a real artifact that fits
    the panel limits, with every shortening made explicit.

    Real study artifacts (snapshots, training manifests, proposals) routinely hold more
    than 50 ids/configs; :func:`build_study_view` deliberately refuses such data. This helper
    produces the bounded view the panel may show: lists keep their first items plus a
    ``"... N more items not shown"`` marker, mappings keep their first keys plus a
    ``"_truncated_keys"`` count, long strings are cut with a marker, and nesting deeper than
    eight levels is summarised. It never invents or reorders values. When the result still
    exceeds the byte budget the item cap is reduced (50 -> 20 -> 10 -> 5 -> 2).
    """
    caps = [c for c in (max_items, 20, 10, 5, 2) if c <= max_items] or [2]
    for cap in caps:
        count = [0]
        preview = _preview(value, cap, 0, count)
        try:
            size = len(json.dumps(preview, allow_nan=False).encode())
        except ValueError:
            continue
        if size <= max_bytes:
            return preview, count[0]
    return {"_truncated": "artifact too large for the bounded panel; open the artifact file"}, 1


def _preview(value, cap, depth, count):
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        count[0] += 1
        return None
    if isinstance(value, str):
        if len(value) > 4096:
            count[0] += 1
            return value[:4000] + f"... ({len(value) - 4000} more characters not shown)"
        return value
    if depth >= 8:
        count[0] += 1
        return "... (nested detail not shown)"
    if isinstance(value, (list, tuple)):
        items = [_preview(v, cap, depth + 1, count) for v in list(value)[:cap - 1 if len(value) > cap else cap]]
        if len(value) > cap:
            count[0] += 1
            items.append(f"... {len(value) - (cap - 1)} more items not shown")
        return items
    if isinstance(value, Mapping):
        keys = [k for k in value if isinstance(k, str)]
        skipped_non_str = len(value) - len(keys)
        shown = keys if len(keys) <= cap else keys[:cap - 1]
        out = {k: _preview(value[k], cap, depth + 1, count) for k in shown}
        hidden = len(keys) - len(shown) + skipped_non_str
        if hidden:
            count[0] += 1
            out["_truncated_keys"] = hidden
        return out
    count[0] += 1
    return "... (non-JSON value not shown)"


def decision_panel_artifact(study, export_record):
    """Decide-phase panel input built from the registry's recorded decisions.

    ``service.decide`` records decisions in the registry (not as a ``decision`` artifact), so
    before this the Decide phase showed "missing" even after a decision was recorded (S10 QA
    finding). Returns ``None`` when nothing is recorded. Status stays ``partial``: a recorded
    decision is not a validated decision artifact or export bundle.
    """
    if not isinstance(export_record, Mapping):
        return None
    decisions = [d for d in export_record.get("decisions") or () if isinstance(d, Mapping)]
    if not decisions:
        return None
    recent = decisions[-20:]
    artifacts = [{"kind": a.get("kind"), "sha256": a.get("sha256"), "revision": a.get("revision")}
                 for a in (export_record.get("artifacts") or ()) if isinstance(a, Mapping)][:MAX_ITEMS]
    reasons = ["Decisions are read from the study registry; no validated decision artifact or "
               "export bundle backs them."]
    if len(decisions) > len(recent):
        reasons.append(f"Showing the latest {len(recent)} of {len(decisions)} recorded decisions.")
    return {
        "status": "partial",
        "revision": study.get("revision"),
        "data": {
            "recorded_decisions": [{"seq": d.get("seq"), "revision": d.get("revision"),
                                    "outcome": d.get("outcome"),
                                    "rationale": str(d.get("rationale") or "")[:2000]}
                                   for d in recent],
            "current_revision_decided": any(d.get("revision") == study.get("revision")
                                            for d in decisions),
            "children": list(export_record.get("children") or ())[:MAX_ITEMS],
            "artifacts": artifacts,
        },
        "provenance": {"source": "study registry decisions table"},
        "reasons": reasons,
    }
