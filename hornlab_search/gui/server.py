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


class App:
    def __init__(self, root: Path, runs: Path | None = None, analysis_dir: Path | None = None,
                 study_service=None, study_jobs=None, study_runs=None, study_launcher=None):
        self.root = root.resolve()
        self.runs = (runs or self.root / "runs").resolve()
        self.analysis_dir = (Path(analysis_dir) if analysis_dir is not None
                             else self.runs / "analysis").resolve()
        self.jobs = JobManager(self.root, self.runs)
        self._study_service = study_service
        self._study_jobs = study_jobs
        self._study_runs = study_runs
        self._study_launcher = study_launcher

    def _studies(self):
        if self._study_service is None:
            from hornlab_search.studies.service import StudyService
            self._study_service = StudyService(self.runs / "studies")
        return self._study_service

    def _study_run_bridge(self):
        if self._study_runs is None:
            from .study_jobs import StudyRunBridge
            self._study_runs = StudyRunBridge(self._studies(), launcher=self._study_launcher)
        return self._study_runs

    # GET routes return (status, json-able) ; raise FileNotFoundError / ValueError for 404 / 400
    def get(self, path: str, q: dict) -> object:
        parts = [unquote(p) for p in path.strip("/").split("/")[1:]]      # drop "api"
        head = parts[0] if parts else ""
        if head == "status":
            return D.status(self.root, self.runs)
        if head == "lanes":
            return D.lane_status(self.runs)
        if head == "studies":
            from .data_studies import build_study_view, study_summaries
            service = self._studies()
            if len(parts) == 1:
                return {"studies": study_summaries(service.list_studies(limit=50))}
            if len(parts) == 2:
                return service.get_study(parts[1])
            if len(parts) == 3 and parts[2] == "jobs":
                return {"jobs": service.list_cpu_jobs(parts[1], limit=50)}
            if len(parts) == 4 and parts[2] == "artifacts":
                return service.artifact_view(parts[1], parts[3])
            if len(parts) == 3 and parts[2] == "export":
                # B8: the same read-only export record the CLI `study export` writes.
                return service.export_study(parts[1])
            if len(parts) == 3:
                study = service.get_study(parts[1])
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
                            return build_study_view(study, parts[2], recorded).to_dict()
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
                return build_study_view(study, parts[2], artifact).to_dict()
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
        raise FileNotFoundError(path)

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
        return out

    def post(self, path: str, body: dict) -> object:
        parts = [unquote(p) for p in path.strip("/").split("/")][1:]
        head = parts[0] if parts else ""
        if head == "studies":
            from hornlab_search.studies.schema import StudyError
            service = self._studies()
            if len(parts) == 1:
                return service.create_study(body.get("spec"), body.get("idempotency_key"), body.get("parent_id"))
            if len(parts) == 3 and parts[2] == "revise":
                return service.revise(parts[1], body.get("spec"), body.get("expected_revision"), body.get("idempotency_key"))
            if len(parts) == 3 and parts[2] in ("decide", "decision"):
                return service.decide(parts[1], body.get("expected_revision"), body.get("outcome"),
                                      body.get("rationale"), body.get("idempotency_key"))
            if len(parts) == 3 and parts[2] == "package":
                return self._study_run_bridge().prepare_package(parts[1], body)
            if len(parts) == 3 and parts[2] == "launch":
                return self._study_run_bridge().launch(parts[1], body)
            if len(parts) == 3 and parts[2] == "cancel":
                return self._study_run_bridge().cancel(parts[1], body)
            if len(parts) == 3 and parts[2] == "jobs":
                from .study_jobs import StudyCpuJobs
                bridge = self._study_jobs or StudyCpuJobs(service)
                return bridge.submit(parts[1], body)
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
                argv, gpu = self.jobs.build_argv(str(body.get("kind", "")), body.get("args") or {})
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
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "max-age=60" if cache else "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

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
        try:
            D.list_runs(app.runs)
        except Exception:  # noqa: BLE001 - a warm-up must never crash the process
            _LOG.debug("run-index warm-up failed", exc_info=True)

    t = threading.Timer(delay_s, _warm)
    t.daemon = True
    t.start()
    return t


def serve(root: Path, port: int = DEFAULT_PORT, open_browser: bool = True, runs: Path | None = None,
          analysis_dir: Path | None = None) -> int:
    app = App(root, runs, analysis_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port))
    url = f"http://127.0.0.1:{port}/"
    print(f"hornlab-search gui: {url}  (Ctrl-C to stop; local only)")
    warm_in_background(app)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
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
    ap.add_argument("--analysis-dir", default=None,
                    help="folder the analysis reports render from (default: runs/analysis)")
    a = ap.parse_args(argv)
    return serve(Path(a.root), a.port, not a.no_browser,
                 analysis_dir=Path(a.analysis_dir) if a.analysis_dir else None)
