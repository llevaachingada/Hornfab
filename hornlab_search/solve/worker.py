"""Warm-worker lifecycle for the BEAT persistent Julia host, and the GPU hygiene around it.

Why this module is load-bearing (01_CONTRACTS section 9, AGENTS.md "GPU / Julia hygiene"):

* A cold start is 12-41 s; a warm host answers in ~0.01 s. At ~4 s per screening candidate a
  cold start per candidate would quadruple the cost of every search.
* ``hornlab_beat_bem.shutdown_workers()`` does NOT reliably end the persistent host (measured
  2026-10-12), and stale hosts hold ~1 GB VRAM each and cause false OOMs and
  ``Warm BEAT Engine solver exited with code 1`` crashes. So this module owns a process-level
  view: it can list the hosts, clear stale ones before a warm-up, and verify a release.

Process shape on Windows (measured): ``python -m hornlab_beat_bem.worker_host`` (the venv
launcher) -> the system ``python.exe`` doing the same -> ``julialauncher.exe`` -> ``julia.exe``
(whose own command line is bare, so it can only be found through its ancestors). A host is
therefore identified by the ``hornlab_beat_bem.worker_host`` marker in a command line, and
killed as a TREE (``taskkill /F /T``), never by image name: ``taskkill /IM julia.exe`` would
also take a Boundary Lab or another agent's solver.

Only this module calls ``shutdown_workers`` (contract rule). Every process-listing and
process-killing step goes through an injectable function so the logic is unit-tested with a
fake process table, with no Julia present.
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

log = logging.getLogger("hornlab_search.solve.worker")

HOST_MARKER = "hornlab_beat_bem.worker_host"
LAUNCHER_MARKER = "hornlab_beat_bem"          # julialauncher.exe cmdline carries the package dir

#: The BEAT worker registry directory the host was spawned with. Its ``<lane>/workers`` suffix is
#: how a host is attributed to one of the two nightly lanes (2026-11-12 two-lane night).
WORKER_DIR_ENV = "HORNLAB_BEAT_WORKER_DIR"

#: Registry dir shape ``.../<lane>/workers``; the parent name is the lane.
_WORKERS_DIRNAME = "workers"

#: ``--dir <registry>`` / ``--dir=<registry>`` on a ``worker_host`` command line.
_HOST_DIR_RE = re.compile(r'--dir(?:=|\s+)(?:"([^"]+)"|(\S+))')

#: A single idle warm host plus the desktop uses ~1.5-2.5 GB. Above this with a host present,
#: the host (or a crashed predecessor) is holding more than a healthy warm worker should.
VRAM_HIGH_MIB = 4000

_WARM: set[str] = set()
_SOLVE_TIMES: dict[str, list[float]] = {}
_HOSTS_AT_SOLVE: dict[str, list[tuple[int, ...]]] = {}
_COLD_START_S: dict[str, float] = {}
_HANDLERS_INSTALLED = False
_PREV_SIGINT = None

#: Default for a ``lane=`` keyword: derive it from ``HORNLAB_BEAT_WORKER_DIR`` (and fall back to
#: the old no-lane behaviour when the process is outside a lane). Distinct from an explicit None.
_AUTO_LANE = object()


def _repo_runs_root() -> Path:
    return Path(__file__).resolve().parents[2] / "runs"


class WorkerReleaseError(RuntimeError):
    """A Julia host survived release/kill: it is still holding VRAM."""


# ------------------------------------------------------------------ process table


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    ppid: int
    name: str
    cmdline: str


# ------------------------------------------------------------------ lane identity


def worker_dir_from_env() -> str | None:
    """The registry dir this process was launched with (``HORNLAB_BEAT_WORKER_DIR``), or None.

    Read directly from the environment: ``hornlab_beat_bem.worker_registry.worker_dir()`` creates
    the directory as a side effect, so it must never be called from classification code.
    """
    raw = os.environ.get(WORKER_DIR_ENV, "").strip()
    return raw or None


def derive_lane(registry_dir: str | os.PathLike | None) -> str | None:
    """Lane name from a registry dir of the shape ``.../<lane>/workers``; None when unknown.

    A host whose registry dir does not end in ``workers`` (or is absent) is UNKNOWN and must be
    left alone: killing it could take another lane's warm host. This is decision 3 of the
    2026-11-12 two-lane night, expressed as one pure function so every cleanup path shares it.
    """
    if not registry_dir:
        return None
    try:
        path = Path(str(registry_dir))
    except (TypeError, ValueError):
        return None
    if path.name.lower() != _WORKERS_DIRNAME:
        return None
    lane = path.parent.name.strip().lower()
    return lane or None


def lane_from_env() -> str | None:
    """This process's lane from ``HORNLAB_BEAT_WORKER_DIR``, or None when not in a lane."""
    return derive_lane(worker_dir_from_env())


def host_registry_dir(cmdline: str) -> str | None:
    """The ``--dir`` argument on a BEAT host command line, or None when it carries none."""
    match = _HOST_DIR_RE.search(cmdline or "")
    if not match:
        return None
    return match.group(1) or match.group(2)


def host_lane(cmdline: str) -> str | None:
    """Lane a host belongs to, from the ``--dir`` on its command line; None = unknown."""
    return derive_lane(host_registry_dir(cmdline))


def live_locked_lanes(runs_root: Path | str | None = None) -> set[str]:
    """Lane names whose lock is held by a LIVE process other than us (lazy import: search ->
    solve has no import dependency at module load)."""
    from ..search.gpulock import live_locked_lanes as _live
    return _live(Path(runs_root) if runs_root is not None else None)


def _runs_root_for(registry_dir: str | None) -> Path | None:
    """``runs/`` from an env registry dir ``runs/lanes/<lane>/workers``; None when unknown."""
    if not registry_dir:
        return None
    try:
        parts = Path(str(registry_dir)).parts
    except (TypeError, ValueError):
        return None
    if len(parts) >= 2 and parts[-1].lower() == _WORKERS_DIRNAME:
        return Path(*parts[:-3]) if len(parts) >= 3 else None
    return None


def list_processes() -> list[ProcInfo]:
    """Every process on the machine: pid, parent pid, image name, full command line.

    Windows: one PowerShell ``Get-CimInstance Win32_Process`` call (cmd lines are not
    available from ``tasklist``). POSIX: ``ps``. Returns [] and logs a warning on failure, so
    callers degrade to "no hosts seen" rather than crash.
    """
    try:
        if os.name == "nt":
            cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                   "Get-CimInstance Win32_Process | "
                   "Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
                   "ConvertTo-Json -Compress"]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True).stdout
            rows = json.loads(out) if out.strip() else []
            if isinstance(rows, dict):
                rows = [rows]
            return [ProcInfo(int(r["ProcessId"]), int(r["ParentProcessId"] or 0),
                             str(r["Name"] or ""), str(r["CommandLine"] or "")) for r in rows]
        out = subprocess.run(["ps", "-eo", "pid=,ppid=,comm=,args="], capture_output=True,
                             text=True, timeout=30, check=True).stdout
        procs = []
        for line in out.splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 3:
                procs.append(ProcInfo(int(parts[0]), int(parts[1]), parts[2],
                                      parts[3] if len(parts) > 3 else ""))
        return procs
    except Exception as exc:
        log.warning("could not list processes (%s); assuming no BEAT hosts", exc)
        return []


def kill_tree(pid: int) -> bool:
    """Kill ``pid`` and all its descendants. True if the kill command reported success.

    Windows ``taskkill /F /T /PID``; POSIX: SIGKILL to the process group, then the pid.
    """
    try:
        if os.name == "nt":
            r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(int(pid))],
                               capture_output=True, text=True, timeout=30)
            return r.returncode == 0
        try:
            os.killpg(os.getpgid(int(pid)), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            os.kill(int(pid), signal.SIGKILL)
        return True
    except Exception as exc:
        log.warning("kill_tree(%s) failed: %s", pid, exc)
        return False


def vram_used_mib() -> float | None:
    """Total GPU memory in use, MiB, from ``nvidia-smi`` (a separate process, per AGENTS.md
    hygiene rule 5). None if nvidia-smi is missing or fails."""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=15, check=True)
        vals = [float(x) for x in r.stdout.split() if x.strip()]
        return max(vals) if vals else None
    except Exception:
        return None


class VramMonitor:
    """Context manager: polls ``probe`` from a daemon thread; ``baseline_mib`` is read first.

    ``peak_mib`` is the maximum total seen; ``peak_delta_mib`` is peak minus baseline, i.e. what
    this solve (plus the pool its host reserves) added. Both are None when the probe returns
    None (no NVIDIA GPU). A poll that reads 0 is a bug in the probe, not a result.
    """

    def __init__(self, interval_s: float = 0.5, probe: Callable[[], float | None] = vram_used_mib):
        self.interval_s = float(interval_s)
        self.probe = probe
        self.baseline_mib: float | None = None
        self.peak_mib: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        v = self.probe()
        if v is not None and (self.peak_mib is None or v > self.peak_mib):
            self.peak_mib = v

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            self._sample()

    def __enter__(self) -> "VramMonitor":
        self.baseline_mib = self.probe()
        self.peak_mib = self.baseline_mib
        self._thread = threading.Thread(target=self._run, name="vram-monitor", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._sample()

    @property
    def peak_delta_mib(self) -> float | None:
        if self.peak_mib is None or self.baseline_mib is None:
            return None
        return max(0.0, self.peak_mib - self.baseline_mib)


# ------------------------------------------------------------------ host discovery


def _descendants(procs: list[ProcInfo], root_pid: int) -> list[ProcInfo]:
    kids: dict[int, list[ProcInfo]] = {}
    for p in procs:
        kids.setdefault(p.ppid, []).append(p)
    out, stack, seen = [], [root_pid], {root_pid}
    while stack:
        for c in kids.get(stack.pop(), []):
            if c.pid not in seen:
                seen.add(c.pid)
                out.append(c)
                stack.append(c.pid)
    return out


def _is_beat_julia_orphan(p: ProcInfo) -> bool:
    """Orphaned Julia-side host left after the Python ``worker_host`` died.

    Windows names the middle process ``julialauncher*``. Linux/macOS often leave a bare
    ``julia`` (or ``julia-1.x``) whose args still point at this package's ``solver.jl
    --worker``. Matching by cmdline package marker keeps Boundary Lab / other agents'
    Julia processes out of scope.
    """
    name = p.name.lower()
    cmd = p.cmdline
    if LAUNCHER_MARKER not in cmd:
        return False
    if name.startswith("julialauncher"):
        return True
    # POSIX: julia binary + our solver worker args (measured Metal/CUDA persistent host).
    if name.startswith("julia") and ("solver.jl" in cmd) and ("--worker" in cmd):
        return True
    return False


def beat_host_roots(procs: list[ProcInfo]) -> list[ProcInfo]:
    """Top-level BEAT worker hosts: processes whose command line carries ``HOST_MARKER`` and
    whose parent is not itself a host, plus orphaned Julia-side hosts running this package's
    solver whose parent is gone. Killing a root with ``kill_tree`` takes the whole host
    (both Python layers, the Julia launcher and ``julia``)."""
    alive = {p.pid for p in procs}
    hosts = [p for p in procs if HOST_MARKER in p.cmdline]
    host_pids = {p.pid for p in hosts}
    roots = [p for p in hosts if p.ppid not in host_pids]
    root_ids = {p.pid for p in roots}
    covered = set(root_ids)
    for r in roots:
        covered.update(d.pid for d in _descendants(procs, r.pid))
    for p in procs:
        if p.pid not in covered and p.ppid not in alive and _is_beat_julia_orphan(p):
            roots.append(p)
            covered.add(p.pid)
            covered.update(d.pid for d in _descendants(procs, p.pid))
    return sorted(roots, key=lambda p: p.pid)


def host_tree_pids(procs: list[ProcInfo]) -> set[int]:
    """Every pid belonging to a BEAT host (roots and all descendants)."""
    ids: set[int] = set()
    for r in beat_host_roots(procs):
        ids.add(r.pid)
        ids.update(d.pid for d in _descendants(procs, r.pid))
    return ids


def list_beat_hosts(lister: Callable[[], list[ProcInfo]] | None = None) -> list[ProcInfo]:
    return beat_host_roots((lister or list_processes)())


def _wait_until_gone(pids: set[int], lister, timeout_s: float, sleep) -> set[int]:
    """Poll the process table until none of ``pids`` is alive or the timeout passes.
    Returns the survivors."""
    deadline = time.monotonic() + timeout_s
    while True:
        alive = {p.pid for p in lister()}
        left = pids & alive
        if not left or time.monotonic() >= deadline:
            return left
        sleep(0.5)


def clear_stale_hosts(*, lister: Callable[[], list[ProcInfo]] | None = None,
                      killer: Callable[[int], bool] = kill_tree,
                      vram_probe: Callable[[], float | None] = vram_used_mib,
                      vram_high_mib: float = VRAM_HIGH_MIB, force: bool = False,
                      lane: str | None | object = _AUTO_LANE,
                      runs_root: Path | str | None = None,
                      timeout_s: float = 20.0, sleep: Callable[[float], None] = time.sleep) -> list[int]:
    """Kill BEAT hosts that look stale, BEFORE a warm-up. Returns the root pids killed.

    A host set is stale when ``force``, or MORE THAN ONE host exists (each holds ~1 GB VRAM and
    they poison each other), or at least one exists while total VRAM use is above
    ``vram_high_mib``. Exactly one host on an idle-looking GPU is kept: adopting it is the
    warm-start saving. Never uses image-name kills; only trees rooted at a ``worker_host``
    command line. Raises ``WorkerReleaseError`` if a host survives the kill.

    Two-lane rule (2026-11-12): ``lane`` defaults to the lane named by ``HORNLAB_BEAT_WORKER_DIR``
    (``.../<lane>/workers``). With a lane, only hosts whose ``--dir`` names that SAME lane are
    candidates; a host whose lane cannot be determined is logged as ``unknown host, left alone``
    and kept, and so is a host of ANOTHER lane whose lock is live. Our own lane's live lock does
    not block us: the lock holder is this lane's authority (the night controller), which is
    exactly the process asking for pre/post hygiene. With no lane at all the historical
    clear-all behaviour is preserved (there is no lane identity to protect).
    """
    lister = lister or list_processes
    procs = lister()
    roots = beat_host_roots(procs)
    if not roots:
        return []
    resolved_lane = lane_from_env() if lane is _AUTO_LANE else (lane or None)
    root_dir = (Path(runs_root) if runs_root is not None
                else _runs_root_for(worker_dir_from_env()) or _repo_runs_root())
    protected = live_locked_lanes(root_dir)
    if resolved_lane is not None:
        # A live lock protects a lane from OTHER lanes; the holder is this lane's own authority.
        protected.discard(str(resolved_lane).lower())
    targets = []
    for r in roots:
        rlane = host_lane(r.cmdline)
        if rlane is not None and rlane in protected:
            log.warning("lane %s lock is live: leaving its BEAT host pid %d alone", rlane, r.pid)
            continue
        if resolved_lane is None:
            targets.append(r)
            continue
        if rlane is None:
            log.info("unknown host, left alone: pid %d (lane %s)", r.pid, resolved_lane)
            continue
        if rlane != str(resolved_lane).lower():
            log.debug("pid %d belongs to lane %s (mine %s): left alone", r.pid, rlane, resolved_lane)
            continue
        targets.append(r)
    if not targets:
        return []
    used = None if force else vram_probe()
    reasons = []
    if force:
        reasons.append("forced")
    if len(targets) > 1:
        reasons.append(f"{len(targets)} hosts")
    if used is not None and used > vram_high_mib:
        reasons.append(f"VRAM {used:.0f} MiB > {vram_high_mib:.0f}")
    if not reasons:
        log.info("one BEAT host (pid %d) and VRAM %s: keeping it for adoption", targets[0].pid,
                 "unknown" if used is None else f"{used:.0f} MiB")
        return []
    all_pids: set[int] = set()
    for r in targets:
        all_pids.add(r.pid)
        all_pids.update(d.pid for d in _descendants(procs, r.pid))
    log.warning("clearing stale BEAT hosts %s (%s)", [r.pid for r in targets], ", ".join(reasons))
    for r in targets:
        killer(r.pid)
    left = _wait_until_gone(all_pids, lister, timeout_s, sleep)
    if left:
        raise WorkerReleaseError(f"BEAT host process(es) survived kill: {sorted(left)}")
    _WARM.clear()
    return [r.pid for r in targets]


# ------------------------------------------------------------------ public lifecycle


def _is_beat(name: str) -> bool:
    return str(name).startswith("beat")


def start_beat_worker(device: str, julia_threads: int | None = None) -> None:
    """Boot the persistent host and JIT-exercise the kernels on a 4-triangle mesh.

    ``julia_threads`` (CPU second lane, 2026-11-12): forwarded to ``warm_up`` so the host is
    keyed on the SAME thread count as ``SolveConfig.julia_threads``; a mismatch would make the
    library spawn a second host (H9). Absent = the library's "auto", byte-identical to before.
    """
    import hornlab_beat_bem as beat
    kw = {} if julia_threads is None else {"julia_threads": int(julia_threads)}
    beat.warm_up(beat_backend=device, mode="tiny", **kw)


def warm(backend) -> None:
    """Idempotent. Calls ``backend.warm()`` once per process per backend, after clearing stale
    BEAT hosts (beat backends only). Logs the cold-start time at INFO."""
    name = backend.name
    if name in _WARM:
        return
    if _is_beat(name):
        clear_stale_hosts()
    t0 = time.perf_counter()
    backend.warm()
    dt = time.perf_counter() - t0
    _COLD_START_S[name] = dt
    _WARM.add(name)
    log.info("worker %s warmed in %.2f s", name, dt)


def mark_cold(name: str | None = None) -> None:
    """Forget that a worker is warm (after a crash/OOM or a release) so ``warm`` runs again."""
    if name is None:
        _WARM.clear()
        _SOLVE_TIMES.clear()
        _HOSTS_AT_SOLVE.clear()
    else:
        _WARM.discard(name)
        _SOLVE_TIMES.pop(name, None)
        _HOSTS_AT_SOLVE.pop(name, None)


def is_warm(name: str) -> bool:
    return name in _WARM


def note_solve_seconds(name: str, seconds: float, *,
                       lister: Callable[[], list[ProcInfo]] | None = None) -> None:
    """Record a solve's wall time; log the first and second at INFO (contract section 9).

    "Is the worker reused?" is answered directly, not inferred from timings (a long CPU solve
    looks the same twice): after the first and the second solve of a beat backend the BEAT host
    root pids are read from the process table, and a WARNING fires if they differ or no host is
    found at the second solve. Two process-table reads per process lifetime, nothing per solve.
    """
    ts = _SOLVE_TIMES.setdefault(name, [])
    ts.append(float(seconds))
    hosts = _HOSTS_AT_SOLVE.setdefault(name, [])
    if _is_beat(name) and len(ts) <= 2:
        hosts.append(tuple(sorted(r.pid for r in list_beat_hosts(lister))))
    if len(ts) == 1:
        log.info("%s first solve: %.2f s%s", name, seconds,
                 f" (host pid {','.join(map(str, hosts[0]))})" if hosts and hosts[0] else "")
    elif len(ts) == 2:
        first, second = ts
        log.info("%s second solve: %.2f s (first was %.2f s, ratio %.1fx)", name, second, first,
                 first / second if second > 0 else float("inf"))
        if _is_beat(name) and len(hosts) == 2 and (not hosts[1] or hosts[0] != hosts[1]):
            log.warning("%s: BEAT host changed between solve 1 and 2 (%s -> %s): the warm worker "
                        "is not being reused", name, hosts[0], hosts[1])


def solve_seconds(name: str) -> list[float]:
    return list(_SOLVE_TIMES.get(name, []))


def detach() -> None:
    """``hornlab_beat_bem.detach_workers()``. Leaves the host warm for the next run. Safe to call
    when beat is not installed or nothing is running."""
    try:
        import hornlab_beat_bem as beat
        beat.detach_workers()
    except Exception as exc:
        log.debug("detach_workers: %s", exc)


def shutdown(*, verify: bool = True, timeout_s: float = 20.0,
             lister: Callable[[], list[ProcInfo]] | None = None,
             killer: Callable[[int], bool] = kill_tree,
             sleep: Callable[[float], None] = time.sleep, stop_fn: Callable[[], None] | None = None,
             lane: str | None | object = _AUTO_LANE) -> list[int]:
    """Stop the BEAT host and VERIFY it is gone. Only call at process exit or at the end of a
    measurement/checkpoint run.

    1. ``hornlab_beat_bem.shutdown_workers()`` (documented to stop the host; measured not to
       be reliable on Windows).
    2. Poll the process table; any host tree still alive is killed with ``kill_tree``.
    3. Poll again. Raises ``WorkerReleaseError`` if anything is still alive.

    Returns the root pids that had to be force-killed (empty when the library stopped them).
    ``verify=False`` skips steps 2-3 (just the library call).

    Two-lane rule: steps 2-3 only consider hosts of ``lane`` (defaulting to the lane named by
    ``HORNLAB_BEAT_WORKER_DIR``). Ending the CPU lane must never force-kill the GPU lane's warm
    host, and a host whose lane cannot be determined is left alone. With no lane the historical
    all-hosts behaviour is preserved.
    """
    lister = lister or list_processes
    before = lister() if verify else []
    resolved_lane = lane_from_env() if lane is _AUTO_LANE else (lane or None)
    roots = beat_host_roots(before)
    if resolved_lane is not None:
        kept = []
        for r in roots:
            rlane = host_lane(r.cmdline)
            if rlane is None:
                log.info("unknown host, left alone: pid %d (lane %s)", r.pid, resolved_lane)
                continue
            if rlane != str(resolved_lane).lower():
                log.debug("pid %d belongs to lane %s (mine %s): left alone",
                          r.pid, rlane, resolved_lane)
                continue
            kept.append(r)
        roots = kept
    mine: set[int] = set()
    trees: dict[int, set[int]] = {}
    for r in roots:
        tree = {r.pid} | {d.pid for d in _descendants(before, r.pid)}
        trees[r.pid] = tree
        mine.update(tree)
    try:
        if stop_fn is not None:
            stop_fn()
        else:
            import hornlab_beat_bem as beat
            beat.shutdown_workers()
    except Exception as exc:
        log.warning("shutdown_workers raised %s: %s", type(exc).__name__, exc)
    _WARM.clear()
    _SOLVE_TIMES.clear()
    _HOSTS_AT_SOLVE.clear()
    if not verify:
        return []
    left = _wait_until_gone(mine, lister, min(timeout_s, 10.0), sleep) if mine else set()
    forced: list[int] = []
    if left:
        for root, tree in trees.items():
            if tree & left:
                log.warning("BEAT host pid %d survived shutdown_workers(); killing its tree", root)
                killer(root)
                forced.append(root)
        left = _wait_until_gone(left, lister, timeout_s, sleep)
    if left:
        raise WorkerReleaseError(f"BEAT host process(es) still alive after release: {sorted(left)}")
    return forced


def recover_after_failure(name: str, *, lister=None, killer: Callable[[int], bool] = kill_tree,
                          drop_clients: Callable[[], None] | None = None,
                          lane: str | None | object = _AUTO_LANE,
                          runs_root: Path | str | None = None) -> None:
    """After a CUDA OOM or a worker crash the host is poisoned (stuck pool, half-dead process).
    Drop warm state, drop the library's cached worker clients, and kill project BEAT hosts so the
    next ``warm`` / solve starts clean.

    ``lane`` is forwarded to :func:`clear_stale_hosts`, so a lane process only ever recycles its
    OWN hosts: the other lane's warm host (and any host whose lane is unknown) is left alone.

    Dropping the clients matters: ``hornlab_beat_bem.worker.get_worker`` caches one
    ``HostedBeatWorker`` per key, and that object keeps its socket after a send fails. Killing the
    host alone left every later solve of the process writing to the dead socket (measured
    2026-10-23, OSSE seed 4101: 21 ``ConnectionResetError`` failures in 63 s after one reset).
    ``detach`` (``detach_workers``) empties that cache; the next solve connects or spawns afresh."""
    mark_cold(name)
    (drop_clients or detach)()
    try:
        clear_stale_hosts(force=True, lister=lister, killer=killer, lane=lane,
                          runs_root=runs_root)
    except Exception as exc:
        log.warning("recover_after_failure: %s", exc)


# ------------------------------------------------------------------ process-exit handlers


def _atexit_detach() -> None:
    detach()


def _sigint(signum, frame) -> None:
    detach()
    prev = _PREV_SIGINT
    if callable(prev) and prev not in (signal.SIG_DFL, signal.SIG_IGN):
        prev(signum, frame)
        return
    raise KeyboardInterrupt


def install_handlers() -> None:
    """atexit -> ``detach()``. SIGINT -> ``detach()`` then re-raise as KeyboardInterrupt (or call
    the previous handler). Idempotent. Called once from cli.py. Ctrl-C therefore never orphans an
    un-adoptable Julia process: the host stays registered and is adopted or idles out."""
    global _HANDLERS_INSTALLED, _PREV_SIGINT
    if _HANDLERS_INSTALLED:
        return
    atexit.register(_atexit_detach)
    if threading.current_thread() is threading.main_thread():
        try:
            _PREV_SIGINT = signal.signal(signal.SIGINT, _sigint)
        except (ValueError, OSError) as exc:     # pragma: no cover
            log.debug("could not install SIGINT handler: %s", exc)
    _HANDLERS_INSTALLED = True


def uninstall_handlers() -> None:
    """Undo ``install_handlers`` (tests)."""
    global _HANDLERS_INSTALLED, _PREV_SIGINT
    try:
        atexit.unregister(_atexit_detach)
    except Exception:  # pragma: no cover
        pass
    if _HANDLERS_INSTALLED and threading.current_thread() is threading.main_thread():
        try:
            signal.signal(signal.SIGINT, _PREV_SIGINT or signal.default_int_handler)
        except (ValueError, OSError):  # pragma: no cover
            pass
    _HANDLERS_INSTALLED = False
    _PREV_SIGINT = None
