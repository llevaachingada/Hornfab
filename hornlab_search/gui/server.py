"""Local web GUI server: ``hornlab-search gui`` (or ``python -m hornlab_search.gui``).

Python stdlib only. Binds 127.0.0.1. Serves ``static/`` and a JSON API over the run folders
(``data.py``) and an allow-listed CLI launcher (``jobs.py``). It never solves in-process.

Safety: the Host header must name this server (blocks DNS rebinding), and every POST must be
``application/json`` (a cross-site form cannot send that without a CORS preflight, which we never grant).
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import data as D
from . import data_verify as DV
from .jobs import JobError, JobManager

STATIC = Path(__file__).with_name("static")
MAX_BODY = 64 * 1024
DEFAULT_PORT = 8765

_LOG = logging.getLogger(__name__)


def _q_int(q: dict, key: str, default: int) -> int:
    raw = (q.get(key) or [None])[0]
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _q_str(q: dict, key: str, default: str) -> str:
    raw = (q.get(key) or [None])[0]
    return default if raw in (None, "") else str(raw)


def _q_list(q: dict, key: str) -> list[str]:
    out: list[str] = []
    for item in q.get(key) or []:
        for part in str(item).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _q_bool(q: dict, key: str, default: bool | None = None):
    raw = (q.get(key) or [None])[0]
    if raw in (None, ""):
        return default
    value = str(raw).strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{key} must be a boolean")


class App:
    def __init__(self, root: Path, runs: Path | None = None, analysis_dir: Path | None = None,
                 study_service=None, study_jobs=None, study_runs=None, study_launcher=None,
                 study_roots=(), system_store: Path | None = None):
        self._inflight: dict = {}                       # single-flight GETs (see get())
        self._inflight_lock = threading.Lock()
        self.root = root.resolve()
        # Horn + woofer system store (read-only #/hw views); the system package's isolated
        # store lives beside the repo's runs/, never inside it.
        self.system_store = (Path(system_store) if system_store is not None
                             else self.root / "system_runs").resolve()
        self.runs = (runs or self.root / "runs").resolve()
        self.analysis_dir = (Path(analysis_dir) if analysis_dir is not None
                             else self.runs / "analysis").resolve()
        self.jobs = JobManager(self.root, self.runs, system_root=self.system_store)
        self._study_service = study_service
        self._study_jobs = study_jobs
        self._study_runs = study_runs
        self._study_launcher = study_launcher
        self._extra_study_roots = tuple(Path(p) for p in study_roots)
        self._study_index_obj = None
        self._study_processes = {}
        self._study_bridge_lock = threading.Lock()
        self._study_jobs_by_root = {}
        self._study_runs_by_root = {}
        self._study_runs_lock = threading.Lock()
        self._study_solve_jobs_by_root = {}
        self._study_solve_jobs_lock = threading.Lock()

    def _studies(self):
        if self._study_service is None:
            from hornlab_search.studies.service import StudyService
            self._study_service = StudyService(self.runs / "studies")
        return self._study_service

    def _study_index(self):
        if self._study_index_obj is None:
            from .study_index import StudyIndex
            # Tests and embedders may inject a service whose root is not runs/studies.
            primary = (self._studies().store.root if self._study_service is not None
                       else self.runs / "studies")
            self._study_index_obj = StudyIndex(
                self.root, primary_root=primary,
                extra_roots=self._extra_study_roots)
        return self._study_index_obj

    def _annotate_night_studies(self, payload):
        """Name the study a running queue step prepares or runs, so Status can link to it.

        A night step carries its study root in ``--root``; the study index already knows that
        root's label. Only open steps are resolved, and only when one exists, so an idle poll
        pays nothing. Any failure leaves the payload untouched: status must never fail here.
        """
        import re

        if not isinstance(payload, dict):
            return payload
        queues = payload.get("queues")
        if not isinstance(queues, list):
            return payload
        steps = [q["open_step"] for q in queues
                 if isinstance(q, dict) and isinstance(q.get("open_step"), dict)]
        if not steps:
            return payload
        for step in steps:
            match = re.search(r"--root[=\s]+\"?([^\s\"]+)", str(step.get("command") or ""))
            if not match:
                continue
            label = match.group(1).replace("\\", "/").strip("/")
            # One registry, not the whole index: a night step names its own study root, and
            # opening every registered root on a 10 s poll made the Status page crawl.
            try:
                _root_id, service = self._study_index().service_for_path(self.root / label)
                study = service.list_studies(limit=1)[0]
            except Exception:  # noqa: BLE001 - unknown/broken root: leave the step unlinked
                continue
            step["study_id"] = study.get("id")
            step["study_label"] = study.get("name") or study.get("question") or study.get("id")
        return payload

    def _study_run_bridge(self, service=None):
        service = service or self._studies()
        root = service.store.root.resolve()
        if root == self._studies().store.root.resolve() and self._study_runs is not None:
            return self._study_runs
        with self._study_runs_lock:
            bridge = self._study_runs_by_root.get(root)
            if bridge is None:
                from .study_jobs import StudyRunBridge
                def launch(package, _service=service):
                    from hornlab_search.studies.production import launch_study
                    return launch_study(package, root=self.root, study_root=_service.store.root)
                bridge = StudyRunBridge(service, launcher=self._study_launcher or launch)
                self._study_runs_by_root[root] = bridge
            return bridge

    def _is_primary(self, service) -> bool:
        try:
            return service.store.root.resolve() == self._studies().store.root.resolve()
        except Exception:  # noqa: BLE001
            return False

    def _study_cpu_bridge(self, service=None, *, reconcile=False):
        # The GUI polls panels concurrently; initialize/reconcile exactly once before
        # any request may submit a fresh job into the same registry.
        service = service or self._studies()
        root = service.store.root.resolve()
        if self._is_primary(service) and self._study_jobs is not None:
            return self._study_jobs
        with self._study_bridge_lock:
            return self._create_study_cpu_bridge(service, reconcile=reconcile)

    def _create_study_cpu_bridge(self, service, *, reconcile=False):
        root = service.store.root.resolve()
        existing = self._study_jobs_by_root.get(root)
        if existing is not None:
            if reconcile and not getattr(existing, "_gui_reconciled", False):
                for study in service.list_studies(limit=1000):
                    existing.reconcile_after_restart(study["id"], limit=50)
                setattr(existing, "_gui_reconciled", True)
            return existing
        from .study_jobs import StudyCpuJobs
        def prerequisite(sid, kind, rev, package):
            return service.get_study(sid)["revision"] == rev
        def valid(sid, jid, identity):
            meta = service.get_artifact_metadata(sid, identity.get("kind", ""))
            job = service.get_cpu_job(sid, jid)
            return (meta.get("status") == "available" and meta.get("sha256") == identity.get("sha256")
                    and job["revision"] == meta.get("revision"))
        def dispatch(kind, sid, jid):
            import subprocess
            from hornlab_search.studies.production import study_interpreter
            folder = service.store.root / "workers" / jid
            folder.mkdir(parents=True, exist_ok=True)
            log_path = folder / "worker.log"
            argv = [str(study_interpreter(self.root)), "-m", "hornlab_search.studies.cli", kind,
                    "--root", str(service.store.root), "--study", sid, "--key", jid,
                    "--expected-revision", str(service.get_cpu_job(sid, jid)["revision"])]
            with log_path.open("ab") as output:
                process = subprocess.Popen(argv, cwd=self.root, stdout=output, stderr=subprocess.STDOUT,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self._study_processes[jid] = process
            def finish():
                code = process.wait()
                self._study_processes.pop(jid, None)
                if service.get_cpu_job(sid, jid)["status"] != "running":
                    return
                artifact_kind = {"analyze": "analysis", "diagnose": "diagnostics"}.get(kind, "proposal")
                meta = service.get_artifact_metadata(sid, artifact_kind)
                if code == 0 and (meta.get("status") != "available"
                                  or meta.get("revision") != service.get_cpu_job(sid, jid)["revision"]):
                    code = 6
                self._study_jobs_by_root[root].finish(
                    sid, jid, exit_code=code,
                    artifact_identity={"kind": artifact_kind, "sha256": meta.get("sha256")})
            threading.Thread(target=finish, daemon=True).start()
            return {"pid": process.pid, "log": str(log_path)}
        bridge = StudyCpuJobs(service, dispatcher=dispatch,
                              prerequisite=prerequisite, artifact_validator=valid)
        self._study_jobs_by_root[root] = bridge
        # A prior server's PID cannot establish ownership in this process. Preserve
        # ambiguous jobs durably and require reconciliation; never launch them again.
        # A read-only view of a night-arm registry must not mutate its jobs, so discovery
        # reconciles only when this process is about to own/submit work (or is the primary).
        if reconcile or self._is_primary(service):
            for study in service.list_studies(limit=1000):
                bridge.reconcile_after_restart(study["id"], limit=50)
            setattr(bridge, "_gui_reconciled", True)
        return bridge

    def _study_solve_jobs(self, service=None):
        """One durable ``solve_design`` job bridge per study registry root."""
        service = service or self._studies()
        root = service.store.root.resolve()
        with self._study_solve_jobs_lock:
            bridge = self._study_solve_jobs_by_root.get(root)
            if bridge is None:
                from .study_jobs import StudySolveDesignJobs
                bridge = StudySolveDesignJobs(service, runs_root=self.runs, root=self.root)
                self._study_solve_jobs_by_root[root] = bridge
            return bridge

    # GET routes return (status, json-able) ; raise FileNotFoundError / ValueError for 404 / 400
    def get(self, path: str, q: dict) -> object:
        """Single-flight wrapper: identical concurrent GETs share ONE computation.

        Measured 2026-11-18: a cold start with the browser reloading (or several tabs) ran the
        same multi-second run/campaign/leader scans once PER request, all fighting over the GIL
        -- ~53 s per call instead of ~9 s, and the page sat on "Loading…". Followers now wait for
        the leader's result (or its exception) instead of recomputing."""
        key = (path, tuple(sorted((k, tuple(v)) for k, v in (q or {}).items())))
        with self._inflight_lock:
            slot = self._inflight.get(key)
            leader = slot is None
            if leader:
                slot = self._inflight[key] = {"ev": threading.Event(), "res": None, "err": None}
        if not leader:
            slot["ev"].wait(300)
            if slot["err"] is not None:
                raise slot["err"]
            if slot["ev"].is_set():
                return slot["res"]
        try:
            slot["res"] = self._get_uncoalesced(path, q)
            return slot["res"]
        except BaseException as exc:  # noqa: BLE001 - re-raised to the leader, shared with followers
            slot["err"] = exc
            raise
        finally:
            slot["ev"].set()
            with self._inflight_lock:
                if self._inflight.get(key) is slot:
                    del self._inflight[key]

    def _get_uncoalesced(self, path: str, q: dict) -> object:
        parts = [unquote(p) for p in path.strip("/").split("/")[1:]]      # drop "api"
        head = parts[0] if parts else ""
        if head == "status":
            return self._annotate_night_studies(D.status(self.root, self.runs))
        if head == "lanes":
            return D.lane_status(self.runs)
        if head == "overview" and len(parts) == 1:
            from . import data_overview as OV
            days = _q_int(q, "days", 14)
            if not 1 <= days <= 365:
                raise ValueError("days must be between 1 and 365")
            return OV.overview(self.root, self.runs, days=days,
                               show_legacy=bool(_q_bool(q, "legacy", False)))
        if head == "overview" and len(parts) == 2 and parts[1] == "snapshots":
            from . import data_overview_snapshot as OSN
            return {"snapshots": OSN.snapshots(self.root, self.runs)}
        if head == "overview" and len(parts) == 2 and parts[1] == "findings":
            # Phase 2 findings: computed from the SAME phase-1 overview payload; the engine reads
            # run ndjson only for the budget curve and an existing walls.json (read-only). Phase 3.3
            # software health joins the same list so one tab ranks every recommendation.
            from . import data_overview as OV, data_overview_findings as F, data_overview_state as ST
            from . import data_overview_health as H
            days = _q_int(q, "days", 14)
            if not 1 <= days <= 365:
                raise ValueError("days must be between 1 and 365")
            ov = OV.overview(self.root, self.runs, days=days,
                             show_legacy=bool(_q_bool(q, "legacy", False)))
            fs = F.findings(ov, self.runs) + H.health_findings(ov, self.root, self.runs)
            fs.sort(key=F.sort_key)
            fs = ST.merge_state(fs, ST.load_state(self.runs))
            return {"findings": fs, "counts": {s: sum(1 for f in fs if f["severity"] == s)
                                               for s in F.SEVERITIES},
                    "generated_utc": ov["generated_utc"]}
        if head == "overview" and len(parts) == 2 and parts[1] == "health":
            from . import data_overview as OV, data_overview_health as H
            days = _q_int(q, "days", 14)
            if not 1 <= days <= 365:
                raise ValueError("days must be between 1 and 365")
            ov = OV.overview(self.root, self.runs, days=days,
                             show_legacy=bool(_q_bool(q, "legacy", False)))
            return {"findings": H.health_findings(ov, self.root, self.runs),
                    "generated_utc": ov["generated_utc"]}
        if head == "overview" and len(parts) == 2 and parts[1] == "registry":
            from . import data_overview_registry as RG
            return RG.load_project_registry(self.root)
        if head == "overview" and len(parts) == 2 and parts[1] == "params":
            from . import data_overview_params as PR
            days = _q_int(q, "days", 14)
            if not 1 <= days <= 365:
                raise ValueError("days must be between 1 and 365")
            return PR.params(self.root, self.runs, days=days,
                             show_legacy=bool(_q_bool(q, "legacy", False)))
        if head == "studies":
            from .data_studies import build_study_view, study_summaries
            index = self._study_index()
            if len(parts) == 1:
                return {"studies": study_summaries(index.list_studies(limit=50)),
                        "roots": [{"id": item["id"], "label": item["label"]}
                                  for item in index.roots()]}
            root_id = (q.get("root") or [None])[0]
            item, service, study = index.resolve(parts[1], root_id)
            study = {**study, "root": item["id"], "root_label": item["label"]}
            if len(parts) >= 3 and parts[2] == "observations":
                # Read-only observation -> persisted physical-artifact bridge. GET only: these
                # handlers never touch the CPU/solve/verify job bridges (see study_designs.py).
                from . import study_designs as SD
                if len(parts) == 3:
                    return SD.observations(
                        index, parts[1], root_id=root_id, runs_root=self.runs,
                        page=_q_int(q, "page", 1),
                        page_size=_q_int(q, "page_size", 25),
                        sort=_q_str(q, "sort", "best_j"),
                        q=_q_str(q, "q", "") or None,
                        state=_q_list(q, "state") or None,
                        verified=_q_bool(q, "verified"),
                        new_incumbent=_q_bool(q, "new_incumbent"),
                        pareto=_q_bool(q, "pareto"),
                        nondominated=_q_bool(q, "nondominated"),
                        include_predicted=bool(_q_bool(q, "include_predicted", False)))
                if len(parts) == 4:
                    return SD.observation_detail(index, parts[1], parts[3],
                                                 root_id=root_id, runs_root=self.runs)
                if len(parts) == 5 and parts[4] in ("geometry", "acoustics", "balloon"):
                    tier = _q_str(q, "tier", "screen")
                    handler = {"geometry": SD.geometry, "acoustics": SD.acoustics,
                               "balloon": SD.balloon}[parts[4]]
                    return handler(index, parts[1], parts[3], root_id=root_id,
                                   runs_root=self.runs, tier=tier)
                raise FileNotFoundError(path)
            if len(parts) == 2:
                return study
            if len(parts) == 3 and parts[2] == "jobs":
                self._study_cpu_bridge(service, reconcile=self._is_primary(service))
                return {"jobs": service.list_cpu_jobs(parts[1], limit=50)}
            if len(parts) == 4 and parts[2] == "artifacts":
                return service.artifact_view(parts[1], parts[3])
            if len(parts) == 3 and parts[2] == "export":
                # B8: the same read-only export record the CLI `study export` writes.
                return service.export_study(parts[1])
            if len(parts) == 3:
                self._study_cpu_bridge(service, reconcile=self._is_primary(service))
                artifact = None
                if parts[2] == "overview":
                    artifact = {"status": "partial", "revision": study["revision"],
                                "data": {"spec": study["spec"], "readiness": service.readiness(parts[1])},
                                "provenance": {"spec_hash": study["spec_hash"]}}
                elif parts[2] in {"data", "explain", "propose", "execute", "decide"}:
                    kind = {"data": "snapshot", "explain": "analysis", "propose": "proposal",
                            "execute": "results", "decide": "decision"}[parts[2]]
                    meta = service.get_artifact_metadata(parts[1], kind)
                    fallback_reason = None
                    if parts[2] == "execute" and meta.get("status") == "missing":
                        # No run results yet: show the prepared run package (S10 QA finding).
                        package_meta = service.get_artifact_metadata(parts[1], "package")
                        if package_meta.get("status") == "available":
                            meta = package_meta
                            fallback_reason = ("No run results are recorded; showing the prepared run "
                                               "package (not launched).")
                    if parts[2] == "decide" and meta.get("status") == "missing":
                        from .data_studies import decision_panel_artifact
                        recorded = decision_panel_artifact(study, service.export_study(parts[1]))
                        if recorded is not None:
                            from .data_studies import workflow_panel
                            return workflow_panel(service, study, parts[2], recorded, root=self.root,
                                                  runs_root=self.runs, launcher_available=True)
                    if meta.get("status") == "available":
                        raw = service.store.read_artifact(meta["sha256"])
                        if len(raw) > 128_000:
                            artifact = {"status": "partial", "revision": study["revision"],
                                        "data": {}, "provenance": {"sha256": meta["sha256"]},
                                        "reasons": ["Artifact exceeds the bounded panel size."]}
                        else:
                            try:
                                content = json.loads(raw)
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                content = None
                            # Real artifacts hold >50 ids/configs; show a bounded, explicitly
                            # truncated preview instead of failing the whole panel (S10 QA).
                            from .data_studies import bounded_preview
                            preview, truncated = bounded_preview(content if isinstance(content, dict) else {})
                            reasons = ["Artifact semantics and dependencies are not yet validated."]
                            if fallback_reason:
                                reasons.insert(0, fallback_reason)
                            if truncated:
                                reasons.append(f"Display preview: {truncated} long list(s)/mapping(s) were "
                                               "shortened to the bounded panel size; the stored artifact is unchanged.")
                            artifact = {"status": "unknown", "revision": study["revision"],
                                        "data": preview if isinstance(preview, dict) else {},
                                        "provenance": {"sha256": meta["sha256"]},
                                        "reasons": reasons}
                    elif meta.get("status") in {"stale", "unavailable"}:
                        artifact = {"status": "stale" if meta["status"] == "stale" else "failed",
                                    "revision": study["revision"], "data": {},
                                    "provenance": {"sha256": meta.get("sha256")},
                                    "reasons": [meta.get("reason", "Artifact is not available.")]}
                from .data_studies import workflow_panel
                return workflow_panel(service, study, parts[2], artifact, root=self.root,
                                      runs_root=self.runs, launcher_available=True)
        if head == "comparisons":
            from .data_bo import load_comparison_specs
            if len(parts) == 1:
                return {"comparisons": [{"name": item["name"], "label": item["label"]}
                                        for item in load_comparison_specs(self.root)]}
            if len(parts) == 2 and D.ANALYSIS_SET_ID.match(parts[1]):
                from .data_bo import method_board_view
                match = next((item for item in load_comparison_specs(self.root)
                              if item["name"] == parts[1]), None)
                if match is None:
                    raise FileNotFoundError(parts[1])
                def service_for(path):
                    return self._study_index().service_for_path(path)
                return method_board_view(match["spec"], root=self.root, runs_root=self.runs,
                                         service_for=service_for)
        if head == "runs":
            return D.list_runs(self.runs)
        if head == "analysis" and len(parts) == 1:
            return D.analysis_sets(self.analysis_dir)
        if head == "analysis" and len(parts) == 2:
            return D.analysis_report(self.analysis_dir, parts[1])
        if head == "elites":
            return D.elites_catalog(self.runs, self.root)
        if head == "run" and len(parts) == 2:
            return D.run_detail(self.runs, parts[1], root=self.root)
        if head == "campaigns":
            return D.list_campaigns(self.runs)
        if head == "campaign" and len(parts) == 2:
            return D.campaign_detail(self.runs, parts[1])
        if head == "mesh" and len(parts) == 3:
            tier = (q.get("tier") or ["screen"])[0]
            return D.mesh_surface(self.runs, parts[1], parts[2], tier=tier)
        if head == "preview-shape" and len(parts) == 2:
            return D.preview_shape(self.root, parts[1], q)
        if head == "balloon" and len(parts) == 2:
            return D.balloon_designs(self.runs, parts[1])
        if head == "balloon" and len(parts) == 3:
            tier = (q.get("tier") or ["screen"])[0]
            return D.balloon(self.runs, parts[1], parts[2], tier=tier)
        if head == "briefs":
            return D.list_briefs(self.root)
        if head == "evolution" and len(parts) == 2:
            return D.evolution(self.runs, parts[1])
        if head == "evolution" and len(parts) == 3 and parts[2] == "frames3d":
            return D.evolution_frames3d(self.runs, parts[1])
        if head == "umap" and len(parts) == 2:
            method = (q.get("method") or ["auto"])[0]
            return D.run_umap_cloud(self.runs, parts[1], method=method, root=self.root)
        if head == "archive" and len(parts) == 2:
            return D.run_archive(self.runs, parts[1])
        if head == "typologies":
            return D.typologies(self.root, self.runs)
        if head == "leaders":
            return D.leaders(self.runs)
        if head == "configs":
            return D.list_configs(self.root)
        if head == "budget-hint":
            return self._budget_hint(q)
        if head == "catalog":
            return D.catalog(self.root)
        if head == "families":
            argv = ["families"]
            b = (q.get("brief") or [""])[0]
            if b:
                match = [x for x in D.list_briefs(self.root) if x["name"] == b]
                if not match:
                    raise ValueError(f"unknown brief {b!r}")
                argv += ["--brief", match[0]["path"]]
            rc, text = self.jobs.run_cli(argv)
            return {"returncode": rc, "text": text}
        if head == "jobs":
            return self.jobs.list()
        if head == "job" and len(parts) == 2:
            try:
                return self.jobs.view(parts[1], 200)
            except KeyError:
                raise FileNotFoundError(parts[1]) from None
        if head == "compare":
            return self._compare((q.get("a") or [""])[0], (q.get("b") or [""])[0])
        if head == "verify" and len(parts) == 2:
            return DV.verify_report(self.runs, parts[1], root=self.root)
        if head == "design" and len(parts) == 3:
            tier = (q.get("tier") or ["screen"])[0]
            return DV.design_payload(self.runs, parts[1], parts[2], tier)
        if head == "hw":
            return self._hw(parts[1:], q)
        raise FileNotFoundError(path)

    def _hw(self, parts: list[str], q: dict) -> object:
        """Horn + woofer system views (G0): read-only, no solver, no Boundary Lab import."""
        from . import data_hw as HW
        sub = parts[0] if parts else ""
        if sub == "cases" and len(parts) == 1:
            return HW.hw_cases(self.root, self.system_store)
        if sub == "readiness" and len(parts) == 1:
            return HW.hw_readiness(self.root, self.system_store)
        if sub == "case" and len(parts) == 3:
            return HW.hw_case(self.root, self.system_store, f"{parts[1]}/{parts[2]}")
        if sub == "basis" and len(parts) == 3:
            domain = (q.get("domain") or [""])[0]
            return HW.hw_basis(self.root, self.system_store, f"{parts[1]}/{parts[2]}", domain)
        if sub == "screens" and len(parts) == 1:
            from . import data_hw_screen as SW
            return SW.hw_screens(self.root, self.system_store)
        if sub == "screen" and len(parts) == 2:
            from . import data_hw_screen as SW
            return SW.hw_screen(self.root, self.system_store, parts[1])
        if sub == "mesh" and len(parts) == 3:
            part = (q.get("part") or ["box"])[0]
            return HW.hw_mesh(self.root, self.system_store, f"{parts[1]}/{parts[2]}", part)
        if sub == "compare" and len(parts) == 1:
            from . import data_hw_compare as CMP
            return CMP.hw_compare(self.root, self.system_store,
                                  (q.get("a") or [""])[0], (q.get("b") or [""])[0])
        if sub == "compare-matrix" and len(parts) == 1:
            from . import data_hw_compare as CMP
            # Accept both ?keys=a,b and repeated ?keys=a&keys=b.
            keys = [k for v in (q.get("keys") or []) for k in str(v).split(",") if k]
            return CMP.hw_compare_matrix(self.root, self.system_store, keys)
        if sub == "assets" and len(parts) == 1:
            from . import data_hw_new as NEW
            raw = (q.get("limit") or ["40"])[0]
            try:
                limit = max(10, min(200, int(raw)))
            except (TypeError, ValueError):
                raise ValueError(f"limit must be an int, got {raw!r}") from None
            return NEW.hw_assets(self.root, self.system_store, limit=limit)
        if sub == "drivers" and len(parts) == 1:
            from . import data_hw_new as NEW
            return NEW.hw_drivers(self.root, self.system_store)
        if sub == "spec-defaults" and len(parts) == 1:
            from . import data_hw_new as NEW
            return NEW.hw_spec_defaults(self.root)
        if sub == "specs" and len(parts) == 1:
            from . import data_hw_new as NEW
            return NEW.hw_specs(self.root)
        if sub == "overview" and len(parts) == 1:
            return HW.hw_overview(self.root, self.system_store)
        if sub == "stage-options" and len(parts) == 1:
            from . import data_hw_stage as HWS
            return HWS.stage_options(self.root, self.system_store)
        if sub == "solve-presets" and len(parts) == 1:
            from . import data_hw_stage as HWS
            return HWS.solve_presets(self.root, self.system_store)
        if sub == "authorization" and len(parts) == 1:
            from . import data_hw_stage as HWS
            return HWS.authorization_state(self.root)
        raise FileNotFoundError("/".join(["hw", *parts]))

    def _budget_hint(self, q: dict) -> dict:
        """Hansen-grounded budget suggestion for Launch / Compose (``search/budget_heuristic``).

        Query: ``n_knobs`` (required unless ``config`` is a known configs path), optional
        ``restarts_mode`` / ``restarts_max``. ``config`` looks up ``n_knobs`` from ``list_configs``.
        """
        from hornlab_search.search.budget_heuristic import suggest_budget

        n_raw = (q.get("n_knobs") or [""])[0]
        cfg_path = (q.get("config") or [""])[0].strip()
        mode = (q.get("restarts_mode") or [""])[0]
        rmax_raw = (q.get("restarts_max") or ["2"])[0]
        n: int | None = None
        if n_raw not in ("", None):
            try:
                n = int(n_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"n_knobs must be an int, got {n_raw!r}") from exc
        if n is None and cfg_path:
            match = [c for c in D.list_configs(self.root) if c.get("path") == cfg_path]
            if not match:
                raise ValueError(f"unknown config {cfg_path!r}")
            n = int(match[0].get("n_knobs") or 1)
        if n is None:
            raise ValueError("budget-hint needs n_knobs= or config=")
        try:
            rmax = int(rmax_raw) if rmax_raw not in ("", None) else 2
        except (TypeError, ValueError) as exc:
            raise ValueError(f"restarts_max must be an int, got {rmax_raw!r}") from exc
        out = suggest_budget(n, restarts_mode=mode or None, restarts_max=rmax)
        if cfg_path:
            out["config"] = cfg_path
        return out

    def _compare(self, a: str, b: str) -> dict:
        from hornlab_search.cli import _first_ok_metrics, compare_metrics
        out = {}
        dirs = {}
        ms = []
        for key, rid in (("a", a), ("b", b)):
            d = D._resolve_run(self.runs, rid)
            dirs[key] = d
            row, m = _first_ok_metrics(d)
            if m is None:
                return {"error": f"no solved row with metrics in {rid}"}
            ms.append(m)
            out[key] = D.design_curves(d, row["design_hash"])
        # C-2: the solve group each side belongs to + the keys that differ (never a silent mix).
        out["group_a"], out["group_b"], out["mixed_keys"] = D.solve_group_fingerprints(dirs["a"], dirs["b"])
        # J is only comparable inside one objective definition: state both versions and whether the
        # pair crosses them (the compare view renders the banner when this flag is true).
        out["objective_version_a"] = D.run_objective_version(dirs["a"])
        out["objective_version_b"] = D.run_objective_version(dirs["b"])
        out["versions_mixed"] = out["objective_version_a"] != out["objective_version_b"]
        try:
            out["rows"] = D.clean(compare_metrics(*ms))
        except ValueError as exc:
            return {"error": str(exc), **out}
        # P0 scoring truth: each side's own scored-target view (never overlaid; the compare
        # view shows both when the scored briefs differ). Additive; absent stays absent.
        out.update(D.compare_scoring_views(self.runs, a, b))
        return out

    def post(self, path: str, body: dict) -> object:
        parts = [unquote(p) for p in path.strip("/").split("/")][1:]
        head = parts[0] if parts else ""
        if head == "overview" and len(parts) == 3 and parts[1] == "findings":
            # GUI-written finding state (owner decision O4: the one GUI-written state file).
            # set_status validates status/id and writes atomically; ValueError maps to 400.
            from . import data_overview_state as ST
            payload = body or {}
            state = ST.set_status(self.runs, parts[2], payload.get("status"),
                                  note=payload.get("note"), by="gui")
            return {"ok": True, "id": parts[2], "state": state}
        if head == "hw":
            # Horn + woofer endpoints: pure recompute plus the one GUI-written spec file
            # (examples/systems/user/). panel-fit/validate are pure; spec/save writes that file;
            # no solver and no Boundary Lab import happens here.
            from . import data_hw_screen as SW
            from . import data_hw_new as NEW
            if len(parts) == 2 and parts[1] == "panel-fit":
                return SW.panel_fit(body or {})
            if len(parts) == 3 and parts[1] == "spec" and parts[2] == "validate":
                payload = body or {}
                spec = payload.get("spec") if isinstance(payload, dict) and "spec" in payload else payload
                return NEW.validate_spec(spec or {})
            if len(parts) == 3 and parts[1] == "spec" and parts[2] == "save":
                payload = body or {}
                return NEW.save_spec(self.root, str(payload.get("name") or ""),
                                     payload.get("spec") or {}, replace=bool(payload.get("replace")))
            raise FileNotFoundError(path)
        if head == "studies":
            from hornlab_search.studies.schema import StudyError
            root_id = body.pop("root", None) if isinstance(body, dict) else None
            if len(parts) == 1:
                service = self._studies()
                created = service.create_study(body.get("spec"), body.get("idempotency_key"),
                                                body.get("parent_id"))
                self._study_index().roots(force=True)
                return created
            _item, service, _study = self._study_index().resolve(parts[1], root_id)
            if len(parts) == 3 and parts[2] == "revise":
                return service.revise(parts[1], body.get("spec"), body.get("expected_revision"), body.get("idempotency_key"))
            if len(parts) == 3 and parts[2] in ("decide", "decision"):
                return service.decide(parts[1], body.get("expected_revision"), body.get("outcome"),
                                      body.get("rationale"), body.get("idempotency_key"))
            if len(parts) == 3 and parts[2] == "package":
                return self._study_run_bridge(service).prepare_package(parts[1], body)
            if len(parts) == 3 and parts[2] == "launch":
                return self._study_run_bridge(service).launch(parts[1], body)
            if len(parts) == 3 and parts[2] == "cancel":
                if body.get("job_id"):
                    # Validate ownership in the registry before touching our child process.
                    result = self._study_cpu_bridge(service, reconcile=True).cancel(parts[1], {
                        "job_id": body["job_id"], "idempotency_key": body.get("idempotency_key")})
                    process = self._study_processes.get(body["job_id"])
                    if process is not None and process.poll() is None:
                        process.terminate()
                    return result
                return self._study_run_bridge(service).cancel(parts[1], body)
            if len(parts) == 3 and parts[2] == "jobs":
                if isinstance(body, dict) and body.get("kind") == "solve_design":
                    # GPU verify job: its own durable ledger, same GPU lane as the search.
                    return self._study_solve_jobs(service).submit(parts[1], body)
                return self._study_cpu_bridge(service, reconcile=True).submit(parts[1], body)
            if len(parts) == 3 and parts[2] == "queue":
                from .study_queue import queue_study
                return queue_study(service, parts[1], root=self.root, runs_root=self.runs, payload=body)
            if len(parts) == 3 and parts[2] == "child":
                from .study_child import create_child
                return create_child(service, parts[1], question=str(body.get("question") or ""),
                                    policy=body.get("policy"),
                                    idempotency_key=str(body.get("idempotency_key") or ""))
            raise StudyError("unsupported study operation")
        if head == "save-bounds":
            # Deliberately OUTSIDE the generic handler try: a malformed body raises ValueError
            # and reaches do_POST's 400 mapping, while an unknown config (FileNotFoundError)
            # reaches its 404 mapping. Rejections are a normal 200 {ok:false}.
            return D.save_bounds(self.root, body)
        try:
            if head == "brief":
                p = D.save_user_brief(self.root, str(body.get("name", "")), body.get("brief") or {})
                return {"ok": True, "path": p.relative_to(self.root).as_posix()}
            if head == "preview":                       # the exact command a launch would run (same validation)
                kind = str(body.get("kind", ""))
                args = body.get("args") or {}
                if kind.startswith("hw-") or kind == "overview-snapshot":
                    # These jobs run through a repo entry script, not the stock CLI; the preview
                    # must print the command that will really run (never a lie).
                    prev = self.jobs.preview(kind, args)
                    return {"command": prev["command"], "gpu": prev["gpu"], "entry": prev.get("entry"),
                            "gpu_busy": None}
                argv, gpu = self.jobs.build_argv(kind, args)
                from .jobs import _quote
                return {"command": "hornlab-search " + " ".join(_quote(x) for x in argv), "gpu": gpu,
                        "gpu_busy": self.jobs.gpu_busy() if gpu else None}
            if head == "jobs":
                job = self.jobs.launch(str(body.get("kind", "")), body.get("args") or {})
                return {"id": job.id, "status": job.status,
                        "position": self.jobs.queue_position(job)}
            if head == "job" and len(parts) == 3 and parts[2] == "cancel":
                return self.jobs.cancel(parts[1], only_queued=bool((body or {}).get("only_queued"))).view(40)
            if head == "gpu-clean":
                busy = self.jobs.gpu_busy()
                if busy:
                    return {"error": busy + " - gpu-clean refused (it would kill a running solve)"}
                rc, text = self.jobs.run_cli(["gpu-clean"])
                return {"ok": rc == 0, "text": text}
            if head == "stop-current":
                # Owner 2026-10-25: kill the externally-started run that holds OUR GPU lock (the
                # lock file records its pid + command); gui-started jobs route through cancel.
                return self.jobs.stop_external()
        except (JobError, ValueError) as exc:
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001 - e.g. a ConfigError from load_brief
            return {"error": f"{type(exc).__name__}: {exc}"}
        raise FileNotFoundError(path)


def make_handler(app: App, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "hornlab-gui"

        def log_message(self, fmt, *args):          # quiet; errors still go to stderr below
            pass

        def _send(self, code: int, body: bytes, ctype: str, cache: bool = False) -> None:
            try:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "max-age=60" if cache else "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
            except (ConnectionError, TimeoutError):
                # The browser closed the connection mid-response (tab reload / navigation / a
                # cancelled fetch): nothing left to answer, and not worth a traceback.
                self.close_connection = True

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(D.clean(obj), allow_nan=False).encode(), "application/json")

        def _host_ok(self) -> bool:
            if self.headers.get("Host", "") not in allowed_hosts:
                self._json(403, {"error": "bad Host header"})
                return False
            return True

        def do_GET(self):  # noqa: N802
            if not self._host_ok():
                return
            u = urlparse(self.path)
            try:
                if u.path.startswith("/api/"):
                    return self._json(200, app.get(u.path, parse_qs(u.query)))
                if u.path.startswith("/runs/"):
                    return self._report(u.path)
                if u.path.startswith("/analysis/"):
                    return self._analysis_file(u.path)
                return self._static(u.path)
            except FileNotFoundError as exc:
                return self._json(404, {"error": f"not found: {exc}"})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                from hornlab_search.studies.schema import StudyError
                from .study_jobs import StudyJobError
                if isinstance(exc, (StudyError, StudyJobError)):
                    return self._json(getattr(exc, "status_code", getattr(exc, "http_status", 400)), {"error": str(exc)})
                traceback.print_exc()
                return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

        def do_POST(self):  # noqa: N802
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = -1
            if n < 0 or n > MAX_BODY:
                self.close_connection = True
                return self._json(413, {"error": "request too large"})
            raw = self.rfile.read(n) if n else b""       # always drain: replying early aborts the socket on Windows
            if not self._host_ok():
                return
            origin = self.headers.get("Origin")
            if origin:
                parsed = urlparse(origin)
                if (parsed.scheme != "http" or parsed.netloc not in allowed_hosts
                        or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
                    return self._json(403, {"error": "bad Origin header"})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(415, {"error": "POST must be application/json"})
            try:
                body = json.loads(raw or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("JSON object expected")
                return self._json(200, app.post(urlparse(self.path).path, body))
            except FileNotFoundError as exc:
                return self._json(404, {"error": f"not found: {exc}"})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                from hornlab_search.studies.schema import StudyError
                from .study_jobs import StudyJobError
                if isinstance(exc, (StudyError, StudyJobError)):
                    return self._json(getattr(exc, "status_code", getattr(exc, "http_status", 400)), {"error": str(exc)})
                traceback.print_exc()
                return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

        def _static(self, path: str) -> None:
            rel = "index.html" if path in ("", "/") else path.lstrip("/")
            p = (STATIC / rel).resolve()
            if STATIC.resolve() not in p.parents or not p.is_file():
                raise FileNotFoundError(path)
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            if p.suffix == ".js":
                ctype = "text/javascript"
            self._send(200, p.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))

        def _analysis_file(self, path: str) -> None:
            """Only these kinds of analysis files are served: <set>/<name> and
            <set>/<section>/<name>, where <name> ends in .png/.md/.json/.html. The set and
            section ids use D.ANALYSIS_SET_ID semantics and the file name uses
            D.ANALYSIS_FILE_NAME; the resolved base must stay inside app.analysis_dir (same
            guard pattern as analysis_report). No directory listing, no generic static handler."""
            parts = [unquote(x) for x in path.strip("/").split("/")]
            if len(parts) == 3:
                set_id, section_id, name = parts[1], None, parts[2]
            elif len(parts) == 4:
                set_id, section_id, name = parts[1], parts[2], parts[3]
            else:
                raise FileNotFoundError(path)
            if not D.ANALYSIS_SET_ID.match(set_id):
                raise FileNotFoundError(path)
            if section_id is not None and not D.ANALYSIS_SET_ID.match(section_id):
                raise FileNotFoundError(path)
            if not D.ANALYSIS_FILE_NAME.match(name):
                raise FileNotFoundError(path)
            if Path(name).suffix.lower() not in D.ANALYSIS_FILE_SUFFIXES:
                raise FileNotFoundError(path)
            base = app.analysis_dir / (set_id if set_id != "." else "")
            if section_id is not None:
                base = base / section_id
            try:
                root_res = app.analysis_dir.resolve()
                base_res = base.resolve()
            except OSError:
                raise FileNotFoundError(path) from None
            if base_res != root_res and root_res not in base_res.parents:
                raise FileNotFoundError(path)
            p = base / name
            if not p.is_file():
                raise FileNotFoundError(path)
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            self._send(200, p.read_bytes(), ctype)

        def _report(self, path: str) -> None:
            """Only three kinds of run files are served: runs/<id>/report.html,
            runs/<id>/step/<name>.step, and runs/<id>/cma[/restart_k]/<pycma-log>."""
            parts = [unquote(x) for x in path.strip("/").split("/")]
            if len(parts) == 3 and parts[2] == "report.html" and D.RUN_ID.match(parts[1]):
                p = app.runs / parts[1] / "report.html"
                if p.is_file():
                    return self._send(200, p.read_bytes(), "text/html; charset=utf-8")
            if len(parts) == 4 and parts[2] == "step" and D.RUN_ID.match(parts[1]) and D.STEP_NAME.match(parts[3]):
                p = app.runs / parts[1] / "step" / parts[3]
                if p.is_file():
                    body = p.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/step")
                    self.send_header("Content-Disposition", f'attachment; filename="{parts[3]}"')
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            p = self._cma_log(parts)
            if p is not None:
                body = p.read_bytes()                       # raw bytes, never parsed, never cached
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{p.name}"')
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            raise FileNotFoundError(path)

        def _cma_log(self, parts: list[str]) -> Path | None:
            """C-5: ``runs/<id>/cma/<name>`` and ``runs/<id>/cma/restart_k/<name>`` by strict
            pycma-log name. The name regexes forbid ``/`` and ``..``; the resolved-path check keeps
            every served file inside the run's own ``cma/`` tree (same guard style as ``_report_step``)."""
            if not (len(parts) in (4, 5) and parts[2] == "cma" and D.RUN_ID.match(parts[1])):
                return None
            if len(parts) == 4:
                name, base = parts[3], app.runs / parts[1] / "cma"
            elif D.CMA_RESTART_DIR.match(parts[3]):
                name, base = parts[4], app.runs / parts[1] / "cma" / parts[3]
            else:
                return None
            if not D.CMA_LOG_NAME.match(name):
                return None
            p = (base / name).resolve()
            cma_root = (app.runs / parts[1] / "cma").resolve()
            return p if cma_root in p.parents and p.is_file() else None

    return Handler


def warm_in_background(app: App, delay_s: float = 1.0) -> threading.Timer:
    """Warm the run index off-thread so the owner's first Home load is not a 4 s wait.

    ``D.list_runs`` parses every run's ``search.ndjson`` and memoizes each summary in
    ``_RUN_SUMMARY_CACHE``; doing it once in the background turns that cost into a no-op for
    the first ``/api/runs`` request. ``list_configs`` is deliberately NOT warmed: it
    materializes every geometry and costs tens of seconds of CPU.
    """
    def _warm() -> None:
        # Everything Home asks for on first paint, one after another through the single-flight
        # get() so a browser that arrives mid-warm-up joins this work instead of repeating it.
        for path in ("/api/runs", "/api/campaigns", "/api/leaders"):
            try:
                app.get(path, {})
            except Exception:  # noqa: BLE001 - a warm-up must never crash the process
                _LOG.debug("warm-up of %s failed", path, exc_info=True)
        done.set()

    done = threading.Event()
    t = threading.Timer(delay_s, _warm)
    t.daemon = True
    t.warm_done = done          # serve() waits on this (bounded) before opening the browser
    t.start()
    return t


def serve(root: Path, port: int = DEFAULT_PORT, open_browser: bool = True, runs: Path | None = None,
          analysis_dir: Path | None = None, study_roots=(), system_store: Path | None = None) -> int:
    app = App(root, runs, analysis_dir, study_roots=study_roots, system_store=system_store)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port))
    url = f"http://127.0.0.1:{port}/"
    print(f"hornlab-search gui: {url}  (Ctrl-C to stop; local only)")
    warm = warm_in_background(app)
    if open_browser:
        def _open() -> None:
            # Open the tab once the run index is warm (bounded: never hold the browser back more
            # than 30 s), so the first page load is not a long blank "Loading…".
            print("warming the run index (first start takes a few seconds)...", flush=True)
            warm.warm_done.wait(30)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("gui stopped")
    finally:
        httpd.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hornlab-search gui")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]), help="repository root")
    ap.add_argument("--runs", default=None,
                    help="run folder (default: <root>/runs); point this at the canonical runs when a worktree is used")
    ap.add_argument("--study-root", action="append", default=[], dest="study_roots",
                    help="extra study registry root (repeatable; e.g. a scratch pilot)")
    ap.add_argument("--analysis-dir", default=None,
                    help="folder the analysis reports render from (default: runs/analysis)")
    ap.add_argument("--system-store", default=None,
                    help="horn+woofer system store (default: $HORNLAB_SYSTEM_STORE, else <root>/system_runs)")
    a = ap.parse_args(argv)
    system_store = (Path(a.system_store) if a.system_store
                    else (os.environ.get("HORNLAB_SYSTEM_STORE") or None))
    return serve(Path(a.root), a.port, not a.no_browser,
                 runs=Path(a.runs) if a.runs else None,
                 analysis_dir=Path(a.analysis_dir) if a.analysis_dir else None,
                 study_roots=a.study_roots,
                 system_store=Path(system_store) if system_store else None)
