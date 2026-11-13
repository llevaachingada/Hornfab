"""Registry-backed CPU study job bridge, independent of GUI JobManager/GPU lanes.

The injected registry owns atomic revision/idempotency reservation and CAS state
transitions. No registry or subprocess is created here. Integrators must enforce
HTTP origin/hostname/JSON restrictions before calling this Python seam.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Protocol

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
KINDS = frozenset({"analyze", "propose"})


@dataclass(frozen=True)
class StudyJobError(Exception):
    code: str
    message: str
    http_status: int

    def __str__(self):
        return self.message


class JobRegistry(Protocol):
    def reserve_cpu_job(self, study_id, expected_revision, idempotency_key, request_hash, kind, package_hash): ...
    def get_cpu_job(self, study_id, job_id): ...
    def compare_and_set_cpu_job(self, study_id, job_id, expected_states, new_state, fields, idempotency_key): ...
    def list_cpu_jobs(self, study_id, limit): ...


def _id(value, label):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise StudyJobError("invalid_input", f"invalid {label}", 400)
    return value


def contained_path(root, relative):
    """Resolve a registry-owned relative path without POSIX/Windows traversal."""
    from pathlib import Path
    if not isinstance(relative, str) or not relative:
        raise StudyJobError("invalid_input", "invalid relative path", 400)
    for path in (PurePosixPath(relative), PureWindowsPath(relative)):
        if path.is_absolute() or path.drive or ".." in path.parts:
            raise StudyJobError("invalid_input", "path escapes root", 400)
    base = Path(root).resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise StudyJobError("invalid_input", "path escapes root", 400)
    return target


class StudyCpuJobs:
    """Dispatch only server-owned job kinds via injected dispatcher and durable registry.

    dispatcher(kind, study_id, job_id) is trusted application code, not client argv.
    It returns a process-identity mapping; an exception has ambiguous launch outcome,
    so the job becomes unknown and is never automatically relaunched.
    """
    def __init__(self, registry: JobRegistry, dispatcher=None, artifact_validator=None, prerequisite=None):
        self.registry = registry
        self.dispatcher = dispatcher
        self.artifact_validator = artifact_validator
        self.prerequisite = prerequisite

    def submit(self, study_id, payload):
        _id(study_id, "study id")
        if not isinstance(payload, dict) or set(payload) != {"kind", "expected_revision", "idempotency_key", "package_hash"}:
            raise StudyJobError("invalid_input", "invalid request fields", 400)
        kind, rev, key, package = (payload[k] for k in ("kind", "expected_revision", "idempotency_key", "package_hash"))
        _id(key, "idempotency key")
        if kind not in KINDS or isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
            raise StudyJobError("invalid_input", "invalid kind or revision", 400)
        if not isinstance(package, str) or not _HASH.fullmatch(package):
            raise StudyJobError("invalid_input", "invalid package hash", 400)
        if self.dispatcher is None:
            raise StudyJobError("capability_missing", "CPU job dispatcher unavailable", 503)
        if self.prerequisite is None:
            raise StudyJobError("capability_missing", "CPU job prerequisite checker unavailable", 503)
        if self.prerequisite(study_id, kind, rev, package) is not True:
            raise StudyJobError("unavailable", "CPU job prerequisites unavailable", 422)
        request_hash = hashlib.sha256(json.dumps({"kind": kind, "revision": rev, "package_hash": package},
                                                 sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        job, created = self.registry.reserve_cpu_job(study_id, rev, key, request_hash, kind, package)
        if not created:
            return self.registry.get_cpu_job(study_id, _id(job["id"], "job id"))
        job_id = _id(job["id"], "job id")
        self.registry.compare_and_set_cpu_job(study_id, job_id, ("queued",), "running", {}, f"start-{job_id}")
        try:
            identity = self.dispatcher(kind, study_id, job_id)
            if not isinstance(identity, dict) or not identity:
                raise ValueError("dispatcher did not return a process identity")
            return self.registry.compare_and_set_cpu_job(study_id, job_id, ("running",), "running",
                                                         {"process_identity": identity}, f"process-{job_id}")
        except Exception as exc:
            return self.registry.compare_and_set_cpu_job(study_id, job_id, ("running",), "unknown",
                                                         {"error": f"dispatch outcome unknown: {type(exc).__name__}"},
                                                         f"unknown-{job_id}")

    def finish(self, study_id, job_id, *, exit_code, artifact_identity=None):
        """Record a bounded worker outcome; success needs a verified registered artifact."""
        _id(study_id, "study id")
        _id(job_id, "job id")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise StudyJobError("invalid_input", "invalid exit code", 400)
        if exit_code != 0:
            return self.registry.compare_and_set_cpu_job(study_id, job_id, ("running",), "failed",
                {"error": f"CPU worker exited {exit_code}"}, f"failed-{job_id}")
        if self.artifact_validator is None:
            raise StudyJobError("capability_missing", "artifact validation unavailable", 503)
        if not isinstance(artifact_identity, dict) or not artifact_identity:
            raise StudyJobError("unavailable", "registered artifact identity missing", 422)
        if self.artifact_validator(study_id, job_id, artifact_identity) is not True:
            raise StudyJobError("unavailable", "artifact validation failed", 422)
        return self.registry.compare_and_set_cpu_job(study_id, job_id, ("running",), "complete",
            {"artifact_identity": artifact_identity}, f"complete-{job_id}")

    def reconcile_after_restart(self, study_id, *, limit=50):
        _id(study_id, "study id")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
            raise StudyJobError("invalid_input", "invalid list limit", 400)
        jobs = self.registry.list_cpu_jobs(study_id, limit)
        out = []
        for job in jobs:
            if job.get("status") in ("queued", "running"):
                jid = _id(job.get("id"), "job id")
                job = self.registry.compare_and_set_cpu_job(study_id, jid, (job["status"],), "unknown",
                    {"error": "process state not established after restart"}, f"restart-unknown-{jid}")
            out.append(job)
        return out
