"""Run an overnight hornlab-search campaign night, one GPU job at a time.

The input is a runtime YAML file (``runs/nights/<night>.yaml`` is the convention; the file
itself is not committed)::

    night: smoke_2026-10-27
    jobs:
      - {id: phaseB_ladder, kind: command,
         argv: [".venv\\\\Scripts\\\\python.exe", "tools\\\\measure_fused_ceiling.py", "..."]}
      - {id: t0__b1t__rosse_morph, kind: search,
         config: examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml,
         budget: 1, mode: screen}

Every job runs STRICTLY SEQUENTIALLY within its lane:

1. pre-hygiene: run ``hornlab-search gpu-clean --lane <lane>`` as a subprocess (lane-aware: it
   kills only that lane's BEAT hosts and leaves the other lane's hosts, and any host whose lane
   cannot be determined, alone), then take/observe the lane's lock and record the ``nvidia-smi``
   VRAM baseline on the GPU lane only;
2. run the job as a subprocess with a per-job timeout (search 3 h, command 2 h) and tee
   stdout/stderr to ``runs/nights/<night>/<id>.log``;
3. post-hygiene: ``gpu-clean`` again, then record peak/after VRAM, the run directory parsed from
   the log, the evaluation count read from that run's ``search.ndjson`` (never from ``--budget``),
   and the best J parsed from the search tool's final summary line (``None`` when absent);
4. append one JSON line per job to ``runs/nights/<night>/summary.jsonl``;
5. a failed or timed-out job is recorded and the runner moves on. It never retries.

Two lanes (2026-11-12): a night file may set top-level ``lane: gpu|cpu`` (default ``gpu``). A
``cpu`` night skips the GPU lock and nvidia-smi VRAM accounting, holds ``runs/.cpu.lane.lock`` for
its duration, and exports its own ``HORNLAB_BEAT_WORKER_DIR`` so host cleanup can tell the lanes
apart. Per-job search keys ``backend:``, ``cache_dir:``, ``dataset_dir:`` and ``env:`` (mapping)
become ``--backend``, ``--cache-dir``, ``--dataset-dir`` and the child environment.

Also writes a short ``SUMMARY.md`` table. The module is deliberately import-light: stdlib plus
PyYAML, with the parsing/accounting helpers pure so the whole protocol can be exercised offline.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

SEARCH_TIMEOUT_S = 3 * 60 * 60
COMMAND_TIMEOUT_S = 2 * 60 * 60
LOCK_WAIT_S = 300.0
VRAM_POLL_S = 2.0

#: Lanes this runner understands. ``gpu`` is the historical single-lane behaviour.
LANES = ("gpu", "cpu")
#: Julia/BLAS threads the CPU lane leaves for its host (16 physical cores: leave 4 for gmsh, the
#: GPU lane's feeder and the OS). Overridable per job through ``env:``.
CPU_LANE_THREADS = 12

_MODES = ("screen", "verify", "final")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

#: ``search: ... output <dir>`` / ``search FAILED: ... (output: <dir>)`` /
#: ``search ABORTED: ... (partial results in <dir>)`` /
#: ``search OK: N rows in <dir>/search.ndjson`` (the CLI's final summary line, 2026-11-12:
#:   also appears in COMMAND-kind jobs that wrap hornlab-search search).
_RUN_DIR_RES = (
    re.compile(r"(?:^|[\s(])output:\s*(.+?)\s*\)?\s*$"),
    re.compile(r"(?:^|\s)output\s+(.+?)\s*$"),
    re.compile(r"partial results in\s+(.+?)\s*\)?\s*$"),
)
#: ``search OK: N rows in <run_dir>/search.ndjson``  (run-level line from cli.py _cmd_search)
_SEARCH_OK_RE = re.compile(r"\bsearch OK:\s*\d+\s+rows\s+in\s+(.+?)/search\.ndjson\b")
_BEST_J_RE = re.compile(
    r"\bbest\s+J\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)")


# ------------------------------------------------------------------ plan model


@dataclass(frozen=True)
class Job:
    """One resolved night job. ``argv`` is what will actually be launched."""

    id: str
    kind: str
    argv: tuple[str, ...]
    timeout_s: float
    config: str | None = None
    budget: int | None = None
    mode: str | None = None
    brief: str | None = None
    backend: str | None = None
    cache_dir: str | None = None
    dataset_dir: str | None = None
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NightPlan:
    night: str
    jobs: tuple[Job, ...]
    path: Path
    lane: str = "gpu"


@dataclass
class JobResult:
    id: str
    kind: str
    start: str
    end: str
    seconds: float
    exit_code: int
    run_dir: str | None
    evals_ndjson: int
    best_J: float | None
    vram_baseline_mb: float | None
    vram_after_mb: float | None
    note: str

    def to_dict(self) -> dict:
        """The exact one-line ``summary.jsonl`` schema (key order is intentional)."""
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "seconds": self.seconds,
            "exit_code": self.exit_code,
            "run_dir": self.run_dir,
            "evals_ndjson": self.evals_ndjson,
            "best_J": self.best_J,
            "vram_baseline_mb": self.vram_baseline_mb,
            "vram_after_mb": self.vram_after_mb,
            "note": self.note,
        }


# ------------------------------------------------------------------ pure helpers


def _repo_path(repo_root: Path | str | None) -> Path:
    return Path(repo_root) if repo_root is not None else REPO_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(value: object, what: str) -> str:
    text = str(value or "").strip()
    if not _SAFE_NAME.match(text):
        raise ValueError(f"{what} must match {_SAFE_NAME.pattern!r}, got {text!r}")
    return text


def _positive_timeout(value: object, default: float, job_id: str) -> float:
    if value is None:
        return float(default)
    try:
        out = float(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"job {job_id!r}: timeout_s must be a number") from exc
    if out <= 0:
        raise ValueError(f"job {job_id!r}: timeout_s must be positive")
    return out


def _lane_dir(lane: str, runs_root: Path | str) -> Path:
    """The lane's BEAT worker registry dir: ``<runs>/lanes/<lane>/workers``."""
    return Path(runs_root) / "lanes" / lane / "workers"


def lane_env(lane: str, runs_root: Path | str) -> dict[str, str]:
    """Environment overrides for one lane's search subprocess (pure; unit-tested offline).

    Every lane gets its OWN ``HORNLAB_BEAT_WORKER_DIR`` (decision 3: lane identity is the worker
    registry directory). The CPU lane additionally caps Julia/BLAS threads so it leaves cores for
    gmsh, the GPU lane's feeder and the OS. Returns overrides only; callers merge on top of the
    current environment and under the job's own ``env:``.
    """
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r} (known: {LANES})")
    env = {"HORNLAB_BEAT_WORKER_DIR": str(_lane_dir(lane, runs_root))}
    if lane == "cpu":
        for key in ("JULIA_NUM_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
                    "MKL_NUM_THREADS"):
            env[key] = str(int(CPU_LANE_THREADS))
    return env


def build_job_env(job: Job, night_lane: str, runs_root: Path | str,
                  base: dict[str, str] | None = None) -> dict[str, str]:
    """The exact child environment: process env, then lane overrides, then the job's own env."""
    env = dict(os.environ if base is None else base)
    env.update(lane_env(night_lane, runs_root))
    env.update({str(k): str(v) for k, v in (job.env or {}).items()})
    return env


def _search_argv(job_id: str, spec: dict, cli_exe: Path) -> tuple[str, ...]:
    config = spec.get("config")
    if not config:
        raise ValueError(f"job {job_id!r}: kind search requires 'config'")
    budget = spec.get("budget")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError(f"job {job_id!r}: kind search requires a non-negative integer 'budget'")
    mode = str(spec.get("mode") or "screen")
    if mode not in _MODES:
        raise ValueError(f"job {job_id!r}: mode must be one of {_MODES}, got {mode!r}")
    resume = spec.get("resume")
    if resume:
        # Continue an earlier run: the CLI reads the run's own config.yaml (no sha mismatch), replays
        # the finished candidates from search.ndjson/the solve cache, and spends ``budget`` on NEW solves.
        argv = [str(cli_exe), "search", "--resume", str(resume), "--budget", str(budget),
                "--mode", mode]
    else:
        argv = [str(cli_exe), "search", "--config", str(config), "--budget", str(budget),
                "--mode", mode]
    brief = spec.get("brief")
    if brief:
        argv.extend(["--brief", str(brief)])
    # Two-lane night (2026-11-12): per-job backend / cache / dataset roots. The CPU lane keeps its
    # OWN cache and dataset roots beside the shared runs/ tree (decision 1).
    backend = spec.get("backend")
    if backend:
        argv.extend(["--backend", str(backend)])
    cache_dir = spec.get("cache_dir")
    if cache_dir:
        argv.extend(["--cache-dir", str(cache_dir)])
    dataset_dir = spec.get("dataset_dir")
    if dataset_dir:
        argv.extend(["--dataset-dir", str(dataset_dir)])
    return tuple(argv)


def _job_env(spec: dict, job_id: str) -> dict[str, str]:
    """A job's optional ``env:`` mapping, validated to string keys/values."""
    raw = spec.get("env")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"job {job_id!r}: env must be a mapping of names to values")
    out: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"job {job_id!r}: env keys must be non-empty strings")
        if isinstance(value, (dict, list)) or value is None:
            raise ValueError(f"job {job_id!r}: env[{key!r}] must be a scalar")
        out[key] = str(value)
    return out


def load_night(path: Path | str, *, repo_root: Path | str | None = None,
               cli_exe: Path | str | None = None) -> NightPlan:
    """Parse a night YAML into ordered, fully resolved jobs.

    ``kind: search`` is expanded to
    ``hornlab-search search --config <cfg> --budget <n> --mode <mode> [--brief <brief>]``;
    ``kind: command`` uses its ``argv`` verbatim. The config's own ``brief_file`` is left to the
    search tool; ``--brief`` is added only when the job itself sets one.
    """
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read night file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping with 'night' and 'jobs'")

    root = _repo_path(repo_root)
    night = _safe_name(raw.get("night"), "night")
    lane = str(raw.get("lane") or "gpu").strip().lower()
    if lane not in LANES:
        raise ValueError(f"{path}: top-level lane must be one of {LANES}, got {lane!r}")
    cli = Path(cli_exe) if cli_exe is not None else root / ".venv" / "Scripts" / (
        "hornlab-search.exe")
    specs = raw.get("jobs")
    if not isinstance(specs, list) or not specs:
        raise ValueError(f"{path}: 'jobs' must be a non-empty list")

    jobs: list[Job] = []
    seen: set[str] = set()
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError(f"{path}: jobs[{index}] must be a mapping")
        job_id = _safe_name(spec.get("id"), f"jobs[{index}].id")
        if job_id in seen:
            raise ValueError(f"{path}: duplicate job id {job_id!r}")
        seen.add(job_id)
        kind = str(spec.get("kind") or "").strip()
        job_env = _job_env(spec, job_id)
        if kind == "search":
            argv = _search_argv(job_id, spec, cli)
            timeout = _positive_timeout(spec.get("timeout_s"), SEARCH_TIMEOUT_S, job_id)
            jobs.append(Job(
                id=job_id, kind=kind, argv=argv, timeout_s=timeout,
                config=str(spec.get("config")),
                budget=int(str(spec.get("budget"))),  # validated in _search_argv
                mode=str(spec.get("mode") or "screen"),
                brief=None if not spec.get("brief") else str(spec.get("brief")),
                backend=None if not spec.get("backend") else str(spec.get("backend")),
                cache_dir=None if not spec.get("cache_dir") else str(spec.get("cache_dir")),
                dataset_dir=None if not spec.get("dataset_dir") else str(spec.get("dataset_dir")),
                env=job_env,
            ))
        elif kind == "command":
            argv_raw = spec.get("argv")
            if (not isinstance(argv_raw, list) or not argv_raw
                    or not all(isinstance(a, (str, int, float)) for a in argv_raw)):
                raise ValueError(
                    f"job {job_id!r}: kind command requires a non-empty 'argv' list of strings")
            timeout = _positive_timeout(spec.get("timeout_s"), COMMAND_TIMEOUT_S, job_id)
            jobs.append(Job(
                id=job_id, kind=kind, argv=tuple(str(a) for a in argv_raw),
                timeout_s=timeout, env=job_env))
        else:
            raise ValueError(f"job {job_id!r}: kind must be 'search' or 'command', got {kind!r}")
    return NightPlan(night=night, jobs=tuple(jobs), path=path, lane=lane)


def write_queue_line(log: Path, text: str) -> None:
    """Append one ``=== <local ISO time> <text>`` line (the overnight queue-log format)."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(f"=== {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')} {text}\n")


def night_dir_for(plan: NightPlan, *, runs_root: Path | str | None = None,
                  repo_root: Path | str | None = None) -> Path:
    root = Path(runs_root) if runs_root is not None else _repo_path(repo_root) / "runs"
    return root / "nights" / plan.night


def parse_run_dir(log_text: str, *, repo_root: Path | str | None = None) -> Path | None:
    """Return the run directory named in a search log, or ``None``.

    Recognises:
    * the normal ``search: ... output <dir>`` line,
    * the failure form ``(output: <dir>)``,
    * the aborted form ``(partial results in <dir>)``,
    * the CLI's final summary line ``search OK: N rows in <dir>/search.ndjson``
      (also present in COMMAND-kind jobs that wrap ``hornlab-search search``).
    """
    # First pass: "search OK: N rows in <run_dir>/search.ndjson" (the most reliable pattern)
    for line in log_text.splitlines():
        m = _SEARCH_OK_RE.search(line)
        if m:
            candidate = m.group(1).strip().strip("\"'")
            if candidate:
                path = Path(candidate)
                if not path.is_absolute():
                    path = _repo_path(repo_root) / path
                return path
    # Second pass: the older output/partial patterns
    for line in log_text.splitlines():
        for pattern in _RUN_DIR_RES:
            match = pattern.search(line)
            if not match:
                continue
            candidate = match.group(1).strip().strip("\"'")
            if not candidate:
                continue
            path = Path(candidate)
            if not path.is_absolute():
                path = _repo_path(repo_root) / path
            return path
    return None


def parse_best_j(log_text: str) -> float | None:
    """Parse the final ``seed J=...  best J=...`` summary; the LAST match wins."""
    matches = _BEST_J_RE.findall(log_text or "")
    if not matches:
        return None
    try:
        return float(matches[-1])
    except ValueError:
        return None


def count_evals(ndjson_path: Path | str) -> int:
    """Count evaluation rows in ``search.ndjson`` (non-empty lines). 0 when absent."""
    try:
        text = Path(ndjson_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", errors="replace") as handle:
        handle.write(text)
        handle.flush()


def _fmt(value: float | None, spec: str = ".6g") -> str:
    return "n/a" if value is None else format(value, spec)


def write_summary_md(path: Path, plan: NightPlan, results: list[JobResult]) -> None:
    """Write the short end-of-night table (one row per recorded job)."""
    lines = [
        f"# Night `{plan.night}`",
        "",
        f"{len(results)} job(s) recorded; machine-readable rows are in `summary.jsonl`.",
        "",
        "| id | kind | exit | seconds | evals | best J | VRAM base/after MiB | run dir | note |",
        "|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    for result in results:
        run_dir = "" if result.run_dir is None else f"`{result.run_dir}`"
        note = (result.note or "").replace("|", "\\|")
        lines.append(
            f"| `{result.id}` | {result.kind} | {result.exit_code} | "
            f"{result.seconds:.1f} | {result.evals_ndjson} | "
            f"{_fmt(result.best_J)} | "
            f"{_fmt(result.vram_baseline_mb, '.0f')}/"
            f"{_fmt(result.vram_after_mb, '.0f')} | {run_dir} | {note} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ subprocess utilities


def _run_capture(argv: list[str], timeout: float, cwd: Path | None = None) -> tuple[int, str]:
    """Run a short helper command; never raises (missing tools become rc 127)."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              cwd=str(cwd) if cwd is not None else None)
        return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError as exc:
        return 127, f"{argv[0]}: {exc}"
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or b""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, f"{' '.join(argv)} timed out after {timeout:g}s\n{out}"
    except OSError as exc:
        return 1, f"{argv[0]}: {exc}"


def _vram_mb() -> float | None:
    """``nvidia-smi`` used VRAM in MiB; ``None`` when nvidia-smi is unavailable."""
    rc, out = _run_capture(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], 15)
    if rc != 0:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", out)
    return float(match.group(1)) if match else None


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=60)
        else:
            proc.kill()
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass


class NightRunner:
    """The real subprocess/hygiene layer, isolated so the core can be tested with a fake."""

    def __init__(self, *, repo_root: Path | str | None = None,
                 runs_root: Path | str | None = None,
                 cli_exe: Path | str | None = None,
                 lock_wait_s: float = LOCK_WAIT_S,
                 vram_poll_s: float = VRAM_POLL_S,
                 lane: str = "gpu") -> None:
        if lane not in LANES:
            raise ValueError(f"unknown lane {lane!r} (known: {LANES})")
        self.lane = lane
        self.repo_root = _repo_path(repo_root)
        self.runs_root = (Path(runs_root) if runs_root is not None
                          else self.repo_root / "runs")
        self.cli_exe = (Path(cli_exe) if cli_exe is not None
                        else self.repo_root / ".venv" / "Scripts" / "hornlab-search.exe")
        self.lock_wait_s = float(lock_wait_s)
        self.vram_poll_s = float(vram_poll_s)
        self.last_peak_mb: float | None = None
        self._last_baseline_mb: float | None = None

    # -- hygiene -------------------------------------------------------

    def _gpu_clean(self, log_path: Path) -> int:
        """Lane-aware ``hornlab-search gpu-clean``: only this lane's hosts are touched."""
        rc, out = _run_capture(
            [str(self.cli_exe), "gpu-clean", "--runs-dir", str(self.runs_root),
             "--lane", self.lane], 180)
        _append(log_path, f"gpu-clean --lane {self.lane} rc={rc}\n{out}\n")
        return rc

    def pre_hygiene(self, job: Job, log_path: Path) -> dict:
        _append(log_path, f"=== pre-hygiene {job.id} lane={self.lane} {_utc_now()}\n")
        clean_rc = self._gpu_clean(log_path)
        note = ""
        if clean_rc == 3:
            note = "gpu-clean reported GPU busy"
        elif clean_rc != 0:
            note = f"gpu-clean rc={clean_rc}"

        if self.lane == "cpu":
            # The CPU lane does not take the GPU lock and does not read nvidia-smi: it rides
            # beside the GPU solve (decision 2). The nightly controller holds .cpu.lane.lock for
            # the whole run (see run_night), which is what protects this lane's hosts.
            _append(log_path, "cpu lane: GPU lock and VRAM accounting skipped\n")
            self._last_baseline_mb = None
            return {"baseline_mb": None, "note": note}

        lock = self.runs_root / ".gpu.lock"
        deadline = time.monotonic() + self.lock_wait_s
        while lock.exists() and time.monotonic() < deadline:
            # A job killed on timeout leaves its lock behind (2026-10-28: the next job then
            # waited out lock_wait_s and failed). Take over a lock whose holder is gone.
            holder = _lock_holder_pid(lock)
            if holder is not None and not _pid_alive(holder):
                try:
                    lock.unlink()
                    _append(log_path, f"removed stale GPU lock (holder pid {holder} is gone)\n")
                except OSError:
                    pass
                continue
            time.sleep(0.5)
        if lock.exists():
            raise RuntimeError(
                f"GPU lock still present at {lock} after {self.lock_wait_s:g}s")

        baseline = _vram_mb()
        self._last_baseline_mb = baseline
        _append(log_path,
                f"gpu lock clear; VRAM baseline={_fmt(baseline, '.0f')} MiB\n")

        return {"baseline_mb": baseline, "note": note}

    def post_hygiene(self, job: Job, log_path: Path) -> dict:
        _append(log_path, f"=== post-hygiene {job.id} lane={self.lane} {_utc_now()}\n")
        clean_rc = self._gpu_clean(log_path)
        note = "" if clean_rc == 0 else f"post gpu-clean rc={clean_rc}"
        if self.lane == "cpu":
            _append(log_path, "cpu lane: no VRAM accounting\n")
            return {"after_mb": None, "peak_mb": None, "note": note}
        after = _vram_mb()
        _append(log_path,
                f"VRAM peak={_fmt(self.last_peak_mb, '.0f')} MiB "
                f"after={_fmt(after, '.0f')} MiB\n")
        return {"after_mb": after, "peak_mb": self.last_peak_mb, "note": note}

    # -- job execution -------------------------------------------------

    def run(self, job: Job, log_path: Path) -> tuple[int, bool]:
        """Launch one job, tee its output, enforce the timeout. Returns (exit_code, timed_out)."""
        log_path = Path(log_path)
        self.last_peak_mb = self._last_baseline_mb
        peak = {"value": self._last_baseline_mb}
        stop = threading.Event()

        def poll_vram() -> None:
            while not stop.wait(self.vram_poll_s):
                value = _vram_mb()
                if value is not None and (peak["value"] is None or value > peak["value"]):
                    peak["value"] = value

        poll_thread: threading.Thread | None = None
        if self.lane != "cpu":
            poll_thread = threading.Thread(target=poll_vram, name="night-vram", daemon=True)
            poll_thread.start()

        env = build_job_env(job, self.lane, self.runs_root)
        _append(log_path,
                f"\n=== job {job.id} start {_utc_now()} timeout={job.timeout_s:g}s\n"
                f"=== argv: {' '.join(job.argv)}\n"
                f"=== HORNLAB_BEAT_WORKER_DIR: {env.get('HORNLAB_BEAT_WORKER_DIR')}\n")
        try:
            proc = subprocess.Popen(
                [str(a) for a in job.argv], cwd=str(self.repo_root), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as exc:
            stop.set()
            if poll_thread is not None:
                poll_thread.join(timeout=5)
            self.last_peak_mb = peak["value"]
            _append(log_path, f"LAUNCH FAILED: {exc}\n")
            return 127, False

        lines: queue.Queue[str | None] = queue.Queue()

        def pump() -> None:
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    lines.put(line)
            finally:
                try:
                    if proc.stdout is not None:
                        proc.stdout.close()
                except OSError:
                    pass
                lines.put(None)

        pump_thread = threading.Thread(target=pump, name="night-tee", daemon=True)
        pump_thread.start()
        deadline = time.monotonic() + float(job.timeout_s)
        timed_out = False

        with open(log_path, "a", encoding="utf-8", errors="replace") as log:
            def emit(line: str) -> None:
                log.write(line)
                log.flush()
                try:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                except UnicodeEncodeError:
                    sys.stdout.write(line.encode("ascii", "replace").decode("ascii"))
                    sys.stdout.flush()

            while True:
                try:
                    line = lines.get(timeout=0.2)
                except queue.Empty:
                    line = ""
                if line:
                    emit(line)
                    continue
                if line is None:
                    break
                if proc.poll() is not None:
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    log.write(
                        f"\n=== TIMEOUT after {job.timeout_s:g}s; killing pid {proc.pid}\n")
                    log.flush()
                    _kill_tree(proc)
                    try:
                        proc.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break

            pump_thread.join(timeout=30)
            while True:
                try:
                    trailing = lines.get_nowait()
                except queue.Empty:
                    break
                if trailing:
                    emit(trailing)

        stop.set()
        if poll_thread is not None:
            poll_thread.join(timeout=5)
        self.last_peak_mb = peak["value"]
        if timed_out:
            _append(log_path, f"=== job {job.id} timed out\n")
            return 124, True
        rc = proc.poll()
        code = 0 if rc is None else int(rc)
        _append(log_path, f"=== job {job.id} end {_utc_now()} exit={code}\n")
        return code, False


# ------------------------------------------------------------------ night core


def _run_one(plan: NightPlan, job: Job, *, night_dir: Path, runner, repo_root: Path) -> JobResult:
    log_path = night_dir / f"{job.id}.log"
    started = time.monotonic()
    start = _utc_now()
    baseline: float | None = None
    after: float | None = None
    peak: float | None = None
    exit_code = 1
    timed_out = False
    note_parts: list[str] = []
    ran = False

    try:
        pre = runner.pre_hygiene(job, log_path) or {}
        baseline = pre.get("baseline_mb")
        if pre.get("note"):
            note_parts.append(str(pre["note"]))
        exit_code, timed_out = runner.run(job, log_path)
        ran = True
    except Exception as exc:  # noqa: BLE001 - a failed hygiene block must not stop the night
        note_parts.append(f"pre-hygiene failed: {type(exc).__name__}: {exc}")

    ended = time.monotonic()
    end = _utc_now()

    if ran:
        try:
            post = runner.post_hygiene(job, log_path) or {}
            after = post.get("after_mb")
            peak = post.get("peak_mb")
            if post.get("note"):
                note_parts.append(str(post["note"]))
        except Exception as exc:  # noqa: BLE001 - cleanup failure is recorded, not raised
            note_parts.append(f"post-hygiene failed: {type(exc).__name__}: {exc}")

    log_text = _read_text(log_path)
    run_dir: Path | None = None
    evals = 0
    best_j: float | None = None

    if timed_out:
        exit_code = 124
        note_parts.insert(0, f"TIMEOUT after {job.timeout_s:g}s")
    elif exit_code != 0:
        note_parts.insert(0, f"exit code {exit_code}")
    else:
        note_parts.insert(0, "ok")

    # Parse run-dir, evals, and best-J from the log for both search and command jobs.
    # COMMAND-kind jobs commonly wrap ``hornlab-search search`` and produce the same summary lines;
    # parsing them prevents the summary from showing evals=0/run_dir=null for command jobs.
    if job.kind in ("search", "command"):
        run_dir = parse_run_dir(log_text, repo_root=repo_root)
        if run_dir is None:
            if job.kind == "search":
                note_parts.append("run dir not parsed from log")
        else:
            ndjson = run_dir / "search.ndjson"
            if ndjson.is_file():
                evals = count_evals(ndjson)
            elif job.kind == "search":
                note_parts.append("search.ndjson missing")
        best_j = parse_best_j(log_text)
        if best_j is None and job.kind == "search":
            note_parts.append("best J not in log")
    if peak is not None:
        note_parts.append(f"peak {peak:g} MiB")

    return JobResult(
        id=job.id,
        kind=job.kind,
        start=start,
        end=end,
        seconds=round(ended - started, 3),
        exit_code=int(exit_code),
        run_dir=None if run_dir is None else str(run_dir),
        evals_ndjson=int(evals),
        best_J=best_j,
        vram_baseline_mb=baseline,
        vram_after_mb=after,
        note="; ".join(part for part in note_parts if part),
    )


@contextlib.contextmanager
def night_lane_lock(plan: NightPlan, runs_root: Path | str | None = None):
    """Hold the CPU lane's marker for the whole night (a GPU night takes no lane lock here; its
    search subprocesses take the GPU lock themselves). Lazy import so dry-run/test paths stay
    import-light."""
    if plan.lane != "cpu":
        yield None
        return
    from hornlab_search.search.gpulock import cpu_lane_lock
    root = Path(runs_root) if runs_root is not None else None
    with cpu_lane_lock(f"night {plan.night}", runs_root=root) as holder:
        yield holder


def run_night(plan: NightPlan, *, dry_run: bool = False, only: str | None = None,
              repo_root: Path | str | None = None,
              runs_root: Path | str | None = None,
              runner=None) -> list[JobResult]:
    """Run (or, with ``dry_run``, print) the night's jobs in order.

    ``runner`` is the injection seam for tests: an object with
    ``pre_hygiene(job, log_path)``, ``run(job, log_path) -> (exit_code, timed_out)`` and
    ``post_hygiene(job, log_path)``. Dry-run creates no files and launches nothing.
    """
    root = _repo_path(repo_root)
    jobs = list(plan.jobs)
    if only is not None:
        jobs = [job for job in jobs if job.id == only]
        if not jobs:
            ids = ", ".join(job.id for job in plan.jobs)
            raise ValueError(f"--only {only!r} matched no job (ids: {ids})")

    if dry_run:
        print(f"night: {plan.night} lane={plan.lane} ({len(jobs)} job(s))")
        for index, job in enumerate(jobs, 1):
            print(f"  {index}. {job.id} [{job.kind}] timeout={job.timeout_s:g}s")
            print(f"     argv: {' '.join(job.argv)}")
        return []

    night_dir = night_dir_for(plan, runs_root=runs_root, repo_root=root)
    night_dir.mkdir(parents=True, exist_ok=True)
    if runner is None:
        runner = NightRunner(repo_root=root, runs_root=runs_root, lane=plan.lane)

    summary_path = night_dir / "summary.jsonl"
    # The GUI Status page reads runs/overnight/queue_*.log (gui/data.py _STEP / queue_steps), the
    # same lines tools/overnight/queue_*.ps1 write, so the night shows up there without extra wiring.
    queue_log = night_dir.parent.parent / "overnight" / f"queue_{plan.night}.log"
    results: list[JobResult] = []
    with night_lane_lock(plan, runs_root=runs_root):
        for job in jobs:
            write_queue_line(queue_log, f"START {job.id} : {' '.join(job.argv)}")
            result = _run_one(plan, job, night_dir=night_dir, runner=runner, repo_root=root)
            write_queue_line(queue_log, f"END {job.id} exit {result.exit_code}")
            results.append(result)
            with open(summary_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
                handle.flush()
            print(f"[{result.id}] exit={result.exit_code} evals={result.evals_ndjson} "
                  f"best_J={_fmt(result.best_J)} note={result.note}")
    write_summary_md(night_dir / "SUMMARY.md", plan, results)
    write_queue_line(queue_log, "QUEUE DONE")
    return results


# ------------------------------------------------------------------ CLI


def _lock_holder_pid(lock: Path) -> int | None:
    """PID recorded in a ``runs/.gpu.lock`` file, or None when unreadable."""
    try:
        pid = json.loads(lock.read_text(encoding="utf-8")).get("pid")
        return int(pid) if pid is not None else None
    except (OSError, ValueError, TypeError):
        return None


def _pid_alive(pid: int) -> bool:
    """Same probe as ``hornlab_search.search.gpulock._pid_alive`` (kept local: this module is
    import-light). Windows: OpenProcess + GetExitCodeProcess, never ``os.kill(pid, 0)``."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return ctypes.get_last_error() == 5
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return True
            return code.value == 259
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an overnight hornlab-search campaign night, one GPU job at a time.")
    parser.add_argument("--night", required=True, metavar="YAML",
                        help="night file (conventionally runs/nights/<night>.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the resolved job list; launch nothing, run no hygiene")
    parser.add_argument("--only", metavar="ID", help="run only the job with this id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        plan = load_night(args.night)
    except ValueError as exc:
        print(f"night runner: {exc}", file=sys.stderr)
        return 2
    try:
        results = run_night(plan, dry_run=args.dry_run, only=args.only)
    except ValueError as exc:
        print(f"night runner: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        return 0
    night_dir = night_dir_for(plan)
    failed = sum(1 for result in results if result.exit_code != 0)
    print(f"night {plan.night}: {len(results)} job(s), {failed} failed; "
          f"summary {night_dir / 'summary.jsonl'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
