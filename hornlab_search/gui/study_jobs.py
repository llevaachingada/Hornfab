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


@dataclass
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


def _require_key(payload):
    """A missing idempotency key is its own typed error, not generic invalid input."""
    if not isinstance(payload, dict) or payload.get("idempotency_key") in (None, ""):
        raise StudyJobError("missing_idempotency_key", "idempotency_key is required", 400)


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
        if isinstance(payload, dict):
            _require_key(payload)
        if not isinstance(payload, dict) or set(payload) != {"kind", "expected_revision", "idempotency_key", "package_hash"}:
            raise StudyJobError("invalid_input", "invalid request fields", 400)
        kind, rev, key, package = (payload[k] for k in ("kind", "expected_revision", "idempotency_key", "package_hash"))
        _id(key, "idempotency key")
        if kind not in KINDS or isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
            raise StudyJobError("invalid_input", "invalid kind or revision", 400)
        if package is not None and (not isinstance(package, str) or not _HASH.fullmatch(package)):
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
            current = self.registry.get_cpu_job(study_id, job_id)
            if current.get("status") != "running":
                return current
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

    def cancel(self, study_id, payload):
        """Idempotently cancel an owned CPU job; never touches GPU hosts or cleanup."""
        _id(study_id, "study id")
        if not isinstance(payload, dict) or set(payload) != {"job_id", "idempotency_key"}:
            raise StudyJobError("invalid_input", "invalid cancel request fields", 400)
        job_id = _id(payload["job_id"], "job id")
        key = _id(payload["idempotency_key"], "idempotency key")
        job = self.registry.get_cpu_job(study_id, job_id)
        if job.get("status") in ("complete", "failed", "interrupted", "unknown"):
            return job
        return self.registry.compare_and_set_cpu_job(
            study_id, job_id, ("queued", "running"), "interrupted", {}, f"cancel-{job_id}-{key}")


class StudyRunBridge:
    """Package/launch/cancel bridge for a reviewable immutable run package.

    The launcher is trusted application code (a durable lane/journal adapter),
    never a shell string.  Without an injected launcher, launch is an explicit
    503 capability gap; package preparation and cancellation still work.  A
    duplicate click reuses the same ``(study, package)`` launch result for the
    same idempotency key and conflicts for a different one.

    Launch idempotency is durable (B4/B5): the claim lives in the studies SQLite
    registry (``launches`` table, migration 2), written BEFORE the launcher is
    called, so a GUI/server restart cannot re-dispatch a launched package.  A
    claim whose outcome is ambiguous (launcher raised, or the process died
    between claim and settle) is ``unknown`` and is never relaunched
    automatically.  The durable journal claim remains the final authority in a
    real launcher.
    """

    def __init__(self, registry, *, launcher=None, canceller=None):
        self.registry = registry
        self.launcher = launcher
        self.canceller = canceller

    def prepare_package(self, study_id, payload):
        _id(study_id, "study id")
        if not isinstance(payload, dict) or set(payload) - {
                "expected_revision", "lane", "deadline", "idempotency_key"}:
            raise StudyJobError("invalid_input", "invalid package request fields", 400)
        from hornlab_search.studies.package import prepare_run_package
        revision = payload.get("expected_revision")
        if revision is not None and (isinstance(revision, bool)
                                     or not isinstance(revision, int) or revision < 1):
            raise StudyJobError("invalid_input", "expected_revision must be a positive integer", 400)
        lane = payload.get("lane", "cpu")
        if lane not in ("cpu", "gpu"):
            raise StudyJobError("invalid_input", "lane must be cpu or gpu", 400)
        key = payload.get("idempotency_key")
        if key is not None:
            _id(key, "idempotency key")
        try:
            return prepare_run_package(
                self.registry, study_id, expected_revision=revision, lane=lane,
                deadline=payload.get("deadline"), idempotency_key=key)
        except StudyJobError:
            raise
        except Exception as exc:  # noqa: BLE001 - typed service errors carry HTTP codes
            raise StudyJobError("unavailable", str(exc),
                                getattr(exc, "status_code", 422)) from exc

    def _stored_package(self, study_id, package_id):
        if not isinstance(package_id, str) or not _HASH.fullmatch(package_id):
            raise StudyJobError("invalid_input", "invalid package id", 400)
        metadata = self.registry.get_artifact_metadata(study_id, "package")
        if metadata.get("status") == "missing" or metadata.get("sha256") != package_id:
            raise StudyJobError("conflict", "package is not the current registered package", 409)
        try:
            raw = self.registry.store.read_artifact(package_id)
        except Exception as exc:  # noqa: BLE001
            raise StudyJobError("unavailable", f"package bytes unavailable: {exc}", 422) from exc
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise StudyJobError("unavailable", "package artifact is not JSON", 422) from exc
        if not isinstance(body, dict):
            raise StudyJobError("unavailable", "package artifact must contain an object", 422)
        return {"package_id": package_id, **body} if "package_id" not in body else body

    def launch(self, study_id, payload):
        _id(study_id, "study id")
        if not isinstance(payload, dict) or set(payload) - {
                "package_id", "package_hash", "expected_revision", "idempotency_key"}:
            raise StudyJobError("invalid_input", "invalid launch request fields", 400)
        _require_key(payload)
        package_id = payload.get("package_id") or payload.get("package_hash")
        if (payload.get("package_id") and payload.get("package_hash")
                and payload["package_id"] != payload["package_hash"]):
            raise StudyJobError("conflict", "package id and hash disagree", 409)
        key = _id(payload.get("idempotency_key"), "idempotency key")
        from hornlab_search.studies.package import verify_package
        package = self._stored_package(study_id, package_id)
        try:
            verify_package(package)
        except Exception as exc:  # noqa: BLE001
            raise StudyJobError("unavailable", str(exc),
                                getattr(exc, "status_code", 422)) from exc
        if package.get("study_id") != study_id:
            raise StudyJobError("conflict", "package belongs to a different study", 409)
        expected = payload.get("expected_revision")
        if expected is not None and expected != package.get("spec_revision"):
            raise StudyJobError("conflict", "stale package revision", 409)
        study = self.registry.get_study(study_id)
        if package.get("spec_revision") != study.get("revision"):
            raise StudyJobError("conflict", "stale package revision", 409)
        if self.launcher is None:
            raise StudyJobError("capability_missing", "study launch adapter unavailable", 503)
        pid = package["package_id"]
        for name in ("claim_launch", "settle_launch", "release_launch"):
            if not callable(getattr(self.registry, name, None)):
                raise StudyJobError("capability_missing", "durable launch registry unavailable", 503)
        claim, created = self.registry.claim_launch(study_id, pid, key)
        if not created:
            return self._replay(claim, key)
        try:
            result = self.launcher(package)
        except StudyJobError:
            # A typed refusal is raised before anything is dispatched: free the claim.
            self.registry.release_launch(study_id, pid, key)
            raise
        except Exception as exc:  # noqa: BLE001 - ambiguous launch outcome
            self.registry.settle_launch(study_id, pid, key, "unknown",
                                        error=f"launch outcome unknown: {type(exc).__name__}")
            raise StudyJobError("unknown", f"launch outcome unknown: {type(exc).__name__}", 503) from exc
        if not isinstance(result, dict) or not result:
            self.registry.settle_launch(study_id, pid, key, "unknown",
                                        error="launcher returned no process identity")
            raise StudyJobError("unknown", "launcher returned no process identity", 503)
        return self.registry.settle_launch(study_id, pid, key, "launched", result=result)["result"]

    @staticmethod
    def _replay(claim, key):
        if claim["idempotency_key"] != key:
            raise StudyJobError("launch_conflict", "package already launched", 409)
        if claim["status"] == "launched":
            return claim["result"]
        # 'launching' after a restart, or 'unknown': never re-dispatch blindly.
        raise StudyJobError("unknown", f"launch outcome unknown ({claim['status']}); "
                            "reconcile before relaunching", 503)

    def cancel(self, study_id, payload):
        _id(study_id, "study id")
        if not isinstance(payload, dict) or set(payload) - {"package_id", "job_id", "idempotency_key"}:
            raise StudyJobError("invalid_input", "invalid cancel request fields", 400)
        _require_key(payload)
        if not isinstance(payload.get("idempotency_key"), str):
            raise StudyJobError("invalid_input", "idempotency key required", 400)
        has_package = "package_id" in payload
        has_job = "job_id" in payload
        if has_package == has_job:
            raise StudyJobError("invalid_input", "exactly one of package_id/job_id required", 400)
        if has_job:
            return StudyCpuJobs(self.registry).cancel(study_id, {
                "job_id": payload["job_id"], "idempotency_key": payload["idempotency_key"]})
        if self.registry.get_artifact_metadata(study_id, "package").get("status") == "missing":
            raise StudyJobError("not_found", "package not found for this study", 404)
        self._stored_package(study_id, payload["package_id"])
        if self.canceller is None:
            from hornlab_search.studies.schema import NotFound
            from hornlab_search.studies.service import DraftAttemptJournal
            try:
                result = DraftAttemptJournal(self.registry).cancel(
                    payload["package_id"], payload["idempotency_key"])
            except NotFound as exc:
                raise StudyJobError("not_found", str(exc), 404) from exc
            except Exception as exc:  # noqa: BLE001
                raise StudyJobError("unavailable", str(exc),
                                    getattr(exc, "status_code", 422)) from exc
            return result
        result = self.canceller(payload["package_id"])
        return result if isinstance(result, dict) else {"package_id": payload["package_id"],
                                                       "cancelled": True}
