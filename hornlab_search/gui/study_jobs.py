"""Registry-backed study job bridges, independent of the GUI JobManager.

The injected registry owns atomic revision/idempotency reservation and CAS state
transitions. No registry or subprocess is created here. Integrators must enforce
HTTP origin/hostname/JSON restrictions before calling this Python seam.

``StudySolveDesignJobs`` (bottom of this module) is the one GPU job: it re-solves a single study
design through the ordinary CLI ``verify`` body and keeps its own durable ledger next to the study
registry, because the frozen studies registry only reserves analyze/propose/diagnose CPU jobs.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import re
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
KINDS = frozenset({"analyze", "propose", "diagnose"})
#: ``solve_design`` is deliberately NOT in :data:`KINDS`: the frozen studies registry only
#: reserves analyze/propose/diagnose CPU jobs.  This GPU job keeps its own durable ledger next
#: to the study registry instead (see :class:`StudySolveDesignJobs`).
SOLVE_DESIGN_KIND = "solve_design"
_DESIGN_HASH = re.compile(r"^[0-9a-f]{6,64}$")
#: ``hornlab_search.gui.data.RUN_ID`` -- a run folder this GUI can resolve and link.
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6}$")
SOLVE_LEDGER_NAME = "study_solve_designs.json"


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

# --------------------------------------------------------------------------- study design verify
#
# A Bayesian study has no ``runs/<ts>-screen-*`` folder of its own, so its page cannot show the
# ordinary run views (curves + 3D).  ``solve_design`` closes that gap without touching the study
# code pins or ``hornlab_search/studies/**``: it re-solves ONE measured design through the ordinary
# CLI ``verify`` body into a real standalone verify run, holds the same GPU lane the search uses,
# and records ``(study_id, design_hash) -> run_id`` in a small ledger beside the study registry.


def solve_ledger_path(store_root) -> Path:
    return Path(store_root) / SOLVE_LEDGER_NAME


def _empty_ledger() -> dict:
    return {"version": 1, "solves": {}, "jobs": {}, "keys": {}}


def _solve_key(study_id: str, design_hash: str) -> str:
    return f"{study_id}/{design_hash}"


def read_solve_ledger(store_root) -> dict:
    """Best-effort read of the solve ledger; a missing/corrupt file is an empty ledger."""
    try:
        raw = json.loads(solve_ledger_path(store_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty_ledger()
    if not isinstance(raw, dict):
        return _empty_ledger()
    out = _empty_ledger()
    for name in ("solves", "jobs", "keys"):
        value = raw.get(name)
        if isinstance(value, dict):
            out[name] = {str(k): v for k, v in value.items()
                         if isinstance(v, dict) or name == "keys"}
    return out


_LEDGER_LOCKS: dict[str, threading.Lock] = {}
_LEDGER_LOCKS_GUARD = threading.Lock()


def _ledger_lock(path: Path) -> threading.Lock:
    key = str(Path(path).resolve())
    with _LEDGER_LOCKS_GUARD:
        lock = _LEDGER_LOCKS.get(key)
        if lock is None:
            lock = _LEDGER_LOCKS[key] = threading.Lock()
        return lock


def _write_solve_ledger(store_root, ledger: dict) -> None:
    path = solve_ledger_path(store_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(ledger, sort_keys=True, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _update_solve_ledger(store_root, mutate) -> dict:
    """Atomic read-modify-write of the ledger; one writer per store root in this process."""
    with _ledger_lock(solve_ledger_path(store_root)):
        ledger = read_solve_ledger(store_root)
        mutate(ledger)
        _write_solve_ledger(store_root, ledger)
        return ledger


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_alive(pid: int) -> bool:
    from hornlab_search.search.gpulock import _pid_alive as alive
    return alive(int(pid))


def _gpu_busy(runs_root) -> str | None:
    from hornlab_search.search.gpulock import _lock_path, _read_lock
    lock = _read_lock(_lock_path(Path(runs_root)))
    if lock and lock.get("pid"):
        try:
            pid = int(lock["pid"])
        except (TypeError, ValueError):
            return None
        if pid > 0 and _pid_alive(pid):
            return (f'GPU busy: {lock.get("user", "?")} running "{lock.get("command", "?")}" '
                    f'(pid {pid}) since {lock.get("start_time", "?")}')
    return None


def _active_solve_job(ledger: dict, study_id: str) -> dict | None:
    for job in (ledger.get("jobs") or {}).values():
        if (isinstance(job, dict) and job.get("study_id") == study_id
                and job.get("status") in ("queued", "running")):
            return job
    return None


def new_verify_run_dir(runs_root, design_hash: str, *, now=None) -> Path:
    """Create ``<runs>/<utc-ts>-studyverify-<hash6>`` (a real GUI run id).

    The GUI's ``RUN_ID`` is ``<stamp>-<lowercase mode>-<6 hex>``; a study/design pair cannot fit
    two extra dash-separated segments while still being listed/resolvable by ``/api/runs`` and
    ``#/run/<id>``.  The study id, design hash and policy are therefore recorded in ``run.json``
    provenance, and the id itself names the mode and the design-hash prefix.
    """
    if not isinstance(design_hash, str) or not _DESIGN_HASH.fullmatch(design_hash):
        raise StudyJobError("invalid_input", "invalid design hash", 400)
    stamp = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}-studyverify-{design_hash[:6]}"
    if not _RUN_ID.fullmatch(name):
        raise StudyJobError("invalid_input", "derived verify run id is invalid", 400)
    folder = Path(runs_root) / name
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def prepare_verify_run(run_dir, cfg, *, study_id: str, design_hash: str, family: str,
                       params: dict, objective: float, policy: str | None = None,
                       study: dict | None = None) -> dict:
    """Write the real run dir the ordinary ``verify`` body reads.

    ``config.yaml`` is the study's own config snapshot (the same writer the CLI runs use);
    ``run.json`` marks this as a standalone verify run (``mode: verify`` and NO ``verify_of``),
    so the GUI reads ``designs/<hash>`` and the 3D route renders it; ``search.ndjson`` seeds the
    one ok row the verify body selects by hash.
    """
    from hornlab_search.search import rundir
    from hornlab_search.search.evaluate import collect_lib_shas

    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    rundir.write_config_snapshot(run_dir, cfg)
    seed = {
        "ok": True,
        "design_hash": str(design_hash),
        "family": str(family),
        "params": dict(params),
        "objective": float(objective),
        "mode": "screen",
        "created_utc": rundir.utc_now(),
    }
    (run_dir / "search.ndjson").write_text(
        json.dumps(seed, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    provenance = {
        "source": "gui.study_solve_design",
        "study_id": str(study_id),
        "design_hash": str(design_hash),
        "policy": policy,
        "study_name": (study or {}).get("name") or (study or {}).get("question"),
    }
    meta = {
        "run_id": run_dir.name,
        "config_name": getattr(cfg, "name", None),
        "family": str(family),
        "mode": "verify",
        "config": cfg.raw,
        "config_sha": rundir.config_sha(cfg.raw),
        "backend": cfg.solve.backend,
        "lib_shas": collect_lib_shas(),
        "toolchain": rundir.toolchain_snapshot(),
        "command": f"study solve_design {study_id} {design_hash}",
        "study_provenance": provenance,
        "status": "running",
        "started_utc": rundir.utc_now(),
    }
    rundir.write_json_atomic(run_dir / "run.json", meta)
    return {"run_dir": run_dir, "run_id": run_dir.name, "run_json": meta}


def _verify_env() -> dict:
    """The child owns the GPU lock itself (one CUDA solve at a time); a held lane is fatal."""
    env = {**os.environ, "HORNLAB_GPU_LOCK": "refuse", "PYTHONUNBUFFERED": "1"}
    # Never let the child inherit a lock-owner claim from the GUI process: the verify body must
    # acquire the lane for itself rather than silently proceeding unlocked.
    env.pop("HORNLAB_GPU_LOCK_OWNER", None)
    return env


class StudySolveDesignJobs:
    """One-design GPU verify job for the study page (``solve_design`` action).

    Reservation, idempotency and the (study, design) -> run mapping are file-backed in the study
    store directory because the frozen studies registry only reserves analyze/propose/diagnose
    CPU jobs.  Every failure is recorded on the job (status + reason); a run dir is only advertised
    as finished after the verify body left the design directory behind.
    """

    def __init__(self, service, *, runs_root, root=None, gpu_busy=None, runner=None,
                 synchronous: bool = False):
        self.service = service
        self.runs_root = Path(runs_root)
        self.root = Path(root) if root is not None else self.runs_root.parent
        self.store_root = Path(service.store.root)
        self._gpu_busy = gpu_busy or (lambda: _gpu_busy(self.runs_root))
        self._runner = runner or self._subprocess_runner
        self.synchronous = bool(synchronous)
        self._reconcile()

    # ---- durable ledger helpers
    def _ledger(self) -> dict:
        return read_solve_ledger(self.store_root)

    def _update(self, mutate) -> dict:
        return _update_solve_ledger(self.store_root, mutate)

    def _patch_job(self, job_id: str, **fields) -> None:
        def mutate(ledger):
            job = (ledger.get("jobs") or {}).get(job_id)
            if isinstance(job, dict):
                job.update(fields)
        self._update(mutate)

    def _reconcile(self) -> None:
        """A job whose owning GUI process is gone is interrupted, never left 'running'."""
        now, changed = _utc_now(), [False]

        def mutate(ledger):
            for job in (ledger.get("jobs") or {}).values():
                if not isinstance(job, dict) or job.get("status") not in ("queued", "running"):
                    continue
                pid = job.get("pid")
                if isinstance(pid, int) and pid != os.getpid() and not _pid_alive(pid):
                    job.update(status="interrupted", finished_utc=now,
                               reason="the GUI process ended before this solve finished")
                    changed[0] = True
        if any(isinstance(j, dict) and j.get("status") in ("queued", "running")
               for j in (self._ledger().get("jobs") or {}).values()):
            self._update(mutate)

    def view(self, job: dict) -> dict:
        out = {key: job.get(key) for key in
               ("study_id", "design_hash", "status", "reason", "run_id",
                "started_utc", "finished_utc") if job.get(key) is not None}
        job_id = job.get("job_id")
        if job_id is not None:
            out["id"] = job_id
            out["job_id"] = job_id
        return out

    # ---- request path
    def submit(self, study_id, payload) -> dict:
        _id(study_id, "study id")
        if not isinstance(payload, dict):
            raise StudyJobError("invalid_input", "invalid request", 400)
        _require_key(payload)
        if set(payload) != {"kind", "expected_revision", "idempotency_key", "design_hash"}:
            raise StudyJobError("invalid_input", "invalid request fields", 400)
        if payload.get("kind") != SOLVE_DESIGN_KIND:
            raise StudyJobError("invalid_input", "invalid kind", 400)
        design_hash = payload.get("design_hash")
        if not isinstance(design_hash, str) or not _DESIGN_HASH.fullmatch(design_hash):
            raise StudyJobError("invalid_input", "invalid design hash", 400)
        key = _id(payload["idempotency_key"], "idempotency key")
        try:
            study = self.service.get_study(study_id)
        except Exception as exc:  # noqa: BLE001 - missing study is a typed refusal
            raise StudyJobError("not_found", str(exc), 404) from exc
        revision = payload.get("expected_revision")
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise StudyJobError("invalid_input", "invalid revision", 400)
        if revision != study.get("revision"):
            raise StudyJobError("conflict", "stale study revision", 409)
        ledger = self._ledger()
        replay = (ledger.get("keys") or {}).get(f"{study_id}:{key}")
        if replay is not None:
            existing = (ledger.get("jobs") or {}).get(str(replay))
            if isinstance(existing, dict):
                return self.view(existing)
            raise StudyJobError("conflict", "idempotency key has no job", 409)
        active = _active_solve_job(ledger, study_id)
        if active is not None:
            raise StudyJobError(
                "conflict", f"a study solve is already active for design "
                            f"{active.get('design_hash')}", 409)
        design = self._design_observation(study_id, design_hash)
        config_path, brief = self._config_paths(study_id, study)
        cfg = self._load_config(config_path, brief)
        busy = self._gpu_busy()
        if busy:
            self._record_failed(study_id, design_hash, key, str(busy))
            raise StudyJobError("unavailable", str(busy), 422)
        family = design.get("family") or getattr(cfg, "family", None) or "OSSE"
        design = {**design, "family": family}
        job_id = uuid.uuid4().hex
        now = _utc_now()
        record = {"job_id": job_id, "study_id": study_id, "design_hash": design_hash,
                  "status": "queued", "reason": None, "run_id": None,
                  "idempotency_key": key, "pid": os.getpid(),
                  "started_utc": now, "finished_utc": None}

        def reserve(ledger_):
            ledger_["jobs"][job_id] = record
            ledger_["keys"][f"{study_id}:{key}"] = job_id
        self._update(reserve)
        policy = (study.get("spec") or {}).get("policy") or {}
        policy_name = ((policy.get("proposal_policy") or policy.get("mode"))
                       if isinstance(policy, dict) else None)
        if self.synchronous:
            self._execute(study_id, job_id, design_hash, design, cfg, policy_name, study)
        else:
            threading.Thread(target=self._execute, daemon=True,
                             args=(study_id, job_id, design_hash, design, cfg,
                                   policy_name, study)).start()
        return self.view((self._ledger().get("jobs") or {}).get(job_id) or record)

    def _record_failed(self, study_id, design_hash, key, reason) -> str:
        job_id = uuid.uuid4().hex
        now = _utc_now()
        record = {"job_id": job_id, "study_id": study_id, "design_hash": design_hash,
                  "status": "failed", "reason": reason, "run_id": None,
                  "idempotency_key": key, "pid": os.getpid(),
                  "started_utc": now, "finished_utc": now}

        def mutate(ledger):
            ledger["jobs"][job_id] = record
            ledger["keys"][f"{study_id}:{key}"] = job_id
        self._update(mutate)
        return job_id

    # ---- worker
    def _execute(self, study_id, job_id, design_hash, design, cfg, policy, study) -> None:
        from hornlab_search.search import rundir
        from hornlab_search.search.evaluate import read_ndjson

        self._patch_job(job_id, status="running", started_utc=_utc_now())
        run_dir = None
        try:
            run_dir = new_verify_run_dir(self.runs_root, design_hash)
            prepare_verify_run(run_dir, cfg, study_id=study_id, design_hash=design_hash,
                               family=design["family"], params=design["params"],
                               objective=design["objective"], policy=policy, study=study)
            self._patch_job(job_id, run_id=run_dir.name, run_dir=str(run_dir))
            rc = self._runner(run_dir, design_hash, _verify_env())
            metrics = run_dir / "designs" / design_hash / "metrics.json"
            if rc != 0:
                raise StudyJobError("failed", f"verify exited {rc}", 422)
            if not metrics.is_file():
                raise StudyJobError(
                    "failed", "verify finished without its design directory", 422)
            rows = [row for row in read_ndjson(run_dir / "search.ndjson")
                    if row.get("ok") is True and row.get("design_hash") == design_hash
                    and isinstance(row.get("objective"), (int, float))]
            best = min(rows, key=lambda row: float(row["objective"])) if rows else None
            rundir.update_run_json(
                run_dir, status="finished", finished_utc=rundir.utc_now(),
                stop_reason="solve_design: 1 design, 0 failed",
                best=None if best is None else {
                    "design_hash": best.get("design_hash"),
                    "objective": float(best["objective"]), "eval_no": 0})
            now = _utc_now()

            def record(ledger):
                ledger["solves"][_solve_key(study_id, design_hash)] = {
                    "run_id": run_dir.name, "study_id": study_id,
                    "design_hash": design_hash, "recorded_utc": now}
            self._update(record)
            self._patch_job(job_id, status="complete", reason=None, finished_utc=now)
        except Exception as exc:  # noqa: BLE001 - the job carries the reason, never a crash
            if run_dir is not None:
                try:
                    rundir.update_run_json(
                        run_dir, status="failed", finished_utc=rundir.utc_now(),
                        stop_reason=f"solve_design failed: {exc}")
                except Exception:  # noqa: BLE001 - diagnostics only
                    pass
            self._patch_job(job_id, status="failed",
                            reason=f"{type(exc).__name__}: {exc}", finished_utc=_utc_now())

    # ---- resolution
    def _read_artifact(self, study_id, kind):
        meta = self.service.get_artifact_metadata(study_id, kind)
        if meta.get("status") != "available":
            raise StudyJobError("capability_missing", f"{kind} artifact is not available", 503)
        try:
            raw = self.service.store.read_artifact(meta["sha256"])
        except Exception as exc:  # noqa: BLE001
            raise StudyJobError("unavailable", f"{kind} artifact is unreadable: {exc}", 422) from exc
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise StudyJobError("unavailable", f"{kind} artifact is not JSON", 422) from exc

    def _design_observation(self, study_id, design_hash) -> dict:
        results = self._read_artifact(study_id, "results")
        observations = results.get("observations") if isinstance(results, dict) else None
        if not isinstance(observations, list) or not observations:
            raise StudyJobError("unavailable", "the study has no results observations yet", 422)
        matches = []
        for row in observations:
            if not isinstance(row, dict):
                continue
            candidate = row.get("candidate") if isinstance(row.get("candidate"), dict) else {}
            result = row.get("result") if isinstance(row.get("result"), dict) else {}
            identity = candidate.get("design_hash") or result.get("design_hash")
            if identity == design_hash:
                matches.append((candidate, result))
        if not matches:
            raise StudyJobError(
                "unavailable", f"design {design_hash} is not an observation of this study", 422)
        chosen = None
        for candidate, result in matches:
            if result.get("physical_measurement") is not True:
                continue
            value = result.get("observed_j")
            if isinstance(value, bool) or not isinstance(value, (int, float)) \
                    or not math.isfinite(float(value)):
                continue
            if result.get("kind") == "screen":
                chosen = (candidate, result)
                break
            if chosen is None:
                chosen = (candidate, result)
        if chosen is None:
            raise StudyJobError(
                "unavailable", f"design {design_hash} has no complete physical measurement", 422)
        candidate, result = chosen
        params = result.get("params") if isinstance(result.get("params"), dict) else candidate.get("params")
        if not isinstance(params, dict) or not params:
            raise StudyJobError("unavailable", "the design has no recorded parameters", 422)
        return {"family": candidate.get("family") or result.get("family"),
                "params": dict(params),
                "objective": float(result["observed_j"]),
                "candidate": candidate, "result": result}

    def _config_paths(self, study_id, study) -> tuple[Path, Path | None]:
        """Study config from the frozen snapshot, then the package/spec ``task`` block."""
        task = {}
        try:
            snapshot = self._read_artifact(study_id, "snapshot")
            if isinstance(snapshot, dict) and isinstance(snapshot.get("task"), dict):
                task = dict(snapshot["task"])
        except StudyJobError:
            task = {}
        if not task.get("config"):
            try:
                package = self._read_artifact(study_id, "package")
                spec = package.get("spec") if isinstance(package, dict) else None
                if isinstance(spec, dict) and isinstance(spec.get("task"), dict):
                    task = {**spec["task"], **task}
            except StudyJobError:
                pass
        if not task.get("config"):
            spec = study.get("spec") if isinstance(study.get("spec"), dict) else {}
            if isinstance(spec.get("task"), dict):
                task = {**spec["task"], **task}
        raw = task.get("config")
        if not isinstance(raw, str) or not raw:
            raise StudyJobError("capability_missing", "the study has no recorded task config", 503)
        config = Path(raw)
        if not config.is_absolute():
            config = self.root / config
        config = config.resolve()
        if not config.is_file():
            raise StudyJobError("capability_missing", f"study config not found: {config}", 503)
        brief = None
        raw_brief = task.get("brief")
        if isinstance(raw_brief, str) and raw_brief:
            candidate = Path(raw_brief)
            if not candidate.is_absolute():
                candidate = self.root / candidate
            candidate = candidate.resolve()
            if candidate.is_file():
                brief = candidate
        return config, brief

    def _load_config(self, config_path, brief):
        from hornlab_search.config import load_config
        try:
            return load_config(config_path, brief=brief)
        except Exception as exc:  # noqa: BLE001 - a broken config is a typed refusal
            raise StudyJobError(
                "unavailable", f"study config could not be loaded: {exc}", 422) from exc

    def _subprocess_runner(self, run_dir, design_hash, env) -> int:
        """Run the ordinary CLI verify body in the study interpreter (never a second solver)."""
        import subprocess
        from hornlab_search.studies.production import study_interpreter
        argv = [str(study_interpreter(self.root)), "-m", "hornlab_search.cli", "verify",
                "--run", str(run_dir), "--verify-dir", str(run_dir),
                "--designs", design_hash,
                "--runs-dir", str(self.runs_root),
                "--dataset-dir", str(self.root / "dataset"),
                "--cache-dir", str(self.root / "cache")]
        with (run_dir / "worker.log").open("ab") as output:
            process = subprocess.Popen(
                argv, cwd=str(self.root), stdout=output, stderr=subprocess.STDOUT, env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return process.wait()
