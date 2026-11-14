"""Record a job's peak DEDICATED + SHARED ("Windows WDDM spill") VRAM.

AGENTS.md GPU/Julia hygiene rule 8: ``nvidia-smi`` cannot see a spill, so a CUDA timing is only
valid with the host tree's ``\\GPU Process Memory(*)\\Shared Usage`` recorded and near zero. The
night runner records dedicated VRAM only. This wrapper adds the shared counter (design context:
``docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md`` section C4).

Two observer-only modes (this script never kills a process):

SPAWN (ceiling points) -- start a child and watch its process tree::

    python tools\\bench\\run_with_memwatch.py --out arm.json -- <child command + args...>

ATTACH (watch a night arm you cannot spawn) -- watch one lane's BEAT host trees::

    python tools\\bench\\run_with_memwatch.py --attach --lane gpu --runs-dir runs \\
        --deadline-seconds 600 --out night_arm.json

Both write the same JSON record::

    {"child_cmd": [...], "exit_code": 0, "wall_s": 12.3,
     "dedicated_peak_mib": 7341, "shared_peak_mib": 12,
     "spill_mib": 0, "spilled": false, "pids_sampled": [1234, 5678],
     "off_windows": false, "samples_at": ["2026-11-13T...", ...]}

Off Windows the counters are unavailable: the peaks, ``spill_mib`` are null and ``off_windows``
is true; the script still writes the record and returns the child's exit code unchanged.

The caller runs ``hornlab-search gpu-clean`` first (never this tool). The measurement itself reuses
``tools/bench/_bench_common`` (``process_gpu_mib``, ``SPILL_MIB``) and the guarded host baseline in
``tools/bench/_hosts``; neither module is modified.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
for _p in (str(_HERE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _bench_common  # noqa: E402  (same-dir helper, read-only reuse)
import _hosts  # noqa: E402  (guarded BEAT-host baseline; never calls kill_hosts)
from hornlab_search.solve import worker  # noqa: E402

#: Sample cadence for both modes (seconds); the plan asks for 1-2 s in attach mode.
DEFAULT_PERIOD_S = 1.0


# ------------------------------------------------------------------ pure helpers


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def descendants_of(root_pid: int, pairs) -> set[int]:
    """Every live pid in the parent/child tree rooted at ``root_pid``, including the root.

    ``pairs`` is an iterable of ``(pid, ppid)`` from the process table. A root that is no longer
    in the table (a child that just exited) yields the empty set.
    """
    alive: set[int] = set()
    kids: dict[int, list[int]] = {}
    for pid, ppid in pairs:
        alive.add(int(pid))
        kids.setdefault(int(ppid), []).append(int(pid))
    if int(root_pid) not in alive:
        return set()
    out: set[int] = {int(root_pid)}
    stack = [int(root_pid)]
    while stack:
        for child in kids.get(stack.pop(), ()):
            if child not in out:
                out.add(child)
                stack.append(child)
    return out


def aggregate_samples(samples, spill_threshold: int = _bench_common.SPILL_MIB) -> dict:
    """Peak/spill aggregation over counter samples -- pure, no Windows counter access.

    ``samples`` is a list of dicts with ``dedicated_mib`` / ``shared_mib`` (ints or None) and an
    optional ISO ``at`` timestamp. Peak is the max per counter. ``spill_mib`` is
    ``shared_peak - spill_threshold`` when that is positive, else 0 (None when no counter sample
    exists). ``spilled`` is ``shared_peak > spill_threshold``.
    """
    samples = list(samples)
    dedicated = [s["dedicated_mib"] for s in samples if s.get("dedicated_mib") is not None]
    shared = [s["shared_mib"] for s in samples if s.get("shared_mib") is not None]
    ats = [s["at"] for s in samples if s.get("at")]
    if not dedicated and not shared:
        return {"dedicated_peak_mib": None, "shared_peak_mib": None,
                "spill_mib": None, "spilled": False, "samples_at": ats}
    dedicated_peak = max(dedicated) if dedicated else 0
    shared_peak = max(shared) if shared else 0
    spill = shared_peak - spill_threshold if shared_peak > spill_threshold else 0
    return {"dedicated_peak_mib": dedicated_peak, "shared_peak_mib": shared_peak,
            "spill_mib": spill, "spilled": shared_peak > spill_threshold, "samples_at": ats}


class _Collector:
    """Thread-safe sample/pid accumulator (the sampler runs in a daemon thread in spawn mode)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._samples: list[dict] = []
        self._pids: set[int] = set()

    def note_pids(self, pids) -> None:
        with self._lock:
            self._pids.update(int(p) for p in pids)

    def add(self, at: str, dedicated_mib: int, shared_mib: int, pids) -> None:
        with self._lock:
            self._samples.append({"at": at, "dedicated_mib": dedicated_mib,
                                  "shared_mib": shared_mib})
            self._pids.update(int(p) for p in pids)

    def snapshot(self) -> tuple[list[dict], set[int]]:
        with self._lock:
            return list(self._samples), set(self._pids)


# ------------------------------------------------------------------ paths / discovery


def _norm_path(path) -> str:
    """Normalise a registry path for comparison, anchoring relative paths at the repo root.

    The night runner launches children with ``cwd=<repo root>`` and sets
    ``HORNLAB_BEAT_WORKER_DIR`` to ``<runs>/lanes/<lane>/workers`` (see
    ``tools/run_campaign_night.py:lane_env``). A host's ``--dir`` therefore may be relative to the
    repo root even if this process was started elsewhere.
    """
    p = Path(str(path))
    if not p.is_absolute():
        p = _ROOT / p
    return os.path.normcase(os.path.normpath(str(p)))


def lane_worker_dir(lane: str, runs_dir) -> Path:
    """The lane's BEAT worker registry dir, mirroring ``run_campaign_night._lane_dir``."""
    root = Path(runs_dir)
    if not root.is_absolute():
        root = _ROOT / root
    return root / "lanes" / lane / "workers"


def _lane_tree_pids(lane: str, runs_dir, procs) -> set[int]:
    """Pids of the BEAT host trees whose ``--dir`` is exactly this lane's worker dir."""
    wanted = _norm_path(lane_worker_dir(lane, runs_dir))
    pairs = [(p.pid, p.ppid) for p in procs]
    pids: set[int] = set()
    for root in worker.beat_host_roots(procs):
        registry = worker.host_registry_dir(root.cmdline)
        if registry is not None and _norm_path(registry) == wanted:
            pids |= descendants_of(root.pid, pairs)
    return pids


def _spawn_tree_pids(child_pid: int, baseline_hosts: set[int], procs) -> set[int]:
    """The child's tree plus any BEAT host tree that appeared after the baseline snapshot.

    Hosts are normally descendants of the child, but a detached/reparented host is not; the
    baseline (``_hosts.snapshot``) is what marks a host as "spawned under this child" in that case.
    """
    pairs = [(p.pid, p.ppid) for p in procs]
    pids = descendants_of(child_pid, pairs)
    for root in worker.beat_host_roots(procs):
        if root.pid not in baseline_hosts:
            pids |= descendants_of(root.pid, pairs)
    return pids


# ------------------------------------------------------------------ sampling


def _sample_once(pids_fn, collector: _Collector) -> None:
    try:
        pids = set(pids_fn())
    except Exception as exc:  # observer must never crash the job
        print(f"memwatch: pid discovery failed: {exc}", file=sys.stderr, flush=True)
        return
    collector.note_pids(pids)
    if not pids:
        return
    try:
        per = _bench_common.process_gpu_mib(pids)
    except Exception as exc:
        print(f"memwatch: GPU counter probe failed: {exc}", file=sys.stderr, flush=True)
        return
    if per is not None:
        collector.add(_iso_now(), per[0], per[1], pids)


def _sample_loop(stop: threading.Event, period: float, pids_fn, collector: _Collector) -> None:
    while not stop.is_set():
        _sample_once(pids_fn, collector)
        if stop.wait(period):
            return


# ------------------------------------------------------------------ JSON


def _build_record(*, child_cmd, exit_code: int, wall_s: float, agg: dict,
                  pids_sampled, off_windows: bool) -> dict:
    return {
        "child_cmd": child_cmd,
        "exit_code": int(exit_code),
        "wall_s": round(float(wall_s), 6),
        "dedicated_peak_mib": agg["dedicated_peak_mib"],
        "shared_peak_mib": agg["shared_peak_mib"],
        "spill_mib": agg["spill_mib"],
        "spilled": bool(agg["spilled"]),
        "pids_sampled": sorted(int(p) for p in pids_sampled),
        "off_windows": bool(off_windows),
        "samples_at": agg["samples_at"],
    }


def _write_json(path, record: dict) -> None:
    out = Path(path)
    if str(out.parent):
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ modes


def run_spawn(child_cmd: list[str], out, period: float = DEFAULT_PERIOD_S) -> int:
    """Spawn ``child_cmd``, watch its tree, write the record, return the child's exit code."""
    try:
        baseline_hosts = set(_hosts.snapshot())
    except Exception as exc:
        print(f"memwatch: host baseline snapshot failed ({exc}); using empty baseline",
              file=sys.stderr, flush=True)
        baseline_hosts = set()

    start = time.monotonic()
    try:
        proc = subprocess.Popen(list(child_cmd))
    except OSError as exc:
        wall_s = time.monotonic() - start
        print(f"memwatch: could not spawn child: {exc}", file=sys.stderr, flush=True)
        agg = aggregate_samples([])
        _write_json(out, _build_record(child_cmd=list(child_cmd), exit_code=127,
                                       wall_s=wall_s, agg=agg, pids_sampled=[],
                                       off_windows=os.name != "nt"))
        return 127

    collector = _Collector()

    def pids_fn() -> set[int]:
        return _spawn_tree_pids(proc.pid, baseline_hosts, worker.list_processes())

    stop = threading.Event()
    thread = threading.Thread(name="memwatch", target=_sample_loop,
                              args=(stop, max(0.05, float(period)), pids_fn, collector),
                              daemon=True)
    thread.start()
    try:
        exit_code = proc.wait()
        wall_s = time.monotonic() - start
    finally:
        stop.set()
        thread.join(timeout=max(0.05, float(period)) * 3 + 5.0)
        # Final sample catches a persistent host that outlives the child (and the last peak).
        _sample_once(pids_fn, collector)

    samples, pids = collector.snapshot()
    agg = aggregate_samples(samples)
    _write_json(out, _build_record(child_cmd=list(child_cmd), exit_code=exit_code,
                                   wall_s=wall_s, agg=agg, pids_sampled=pids,
                                   off_windows=os.name != "nt"))
    return int(exit_code)


def run_attach(*, lane: str, runs_dir, deadline_s: float, out,
               period: float = DEFAULT_PERIOD_S) -> int:
    """Watch one lane's BEAT host trees for ``deadline_s`` seconds and write the record."""
    start = time.monotonic()
    collector = _Collector()
    saw_hosts = False
    period = max(0.05, float(period))
    deadline_s = max(0.0, float(deadline_s))

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= deadline_s:
            break
        try:
            procs = worker.list_processes()
            pids = _lane_tree_pids(lane, runs_dir, procs)
        except Exception as exc:  # observer only: a probe failure must not fail the window
            print(f"memwatch: lane host discovery failed: {exc}", file=sys.stderr, flush=True)
            pids = set()
        if pids:
            saw_hosts = True
            collector.note_pids(pids)
            try:
                per = _bench_common.process_gpu_mib(pids)
            except Exception as exc:
                print(f"memwatch: GPU counter probe failed: {exc}", file=sys.stderr, flush=True)
                per = None
            if per is not None:
                collector.add(_iso_now(), per[0], per[1], pids)
        remaining = deadline_s - (time.monotonic() - start)
        if remaining <= 0:
            break
        time.sleep(min(period, remaining))

    wall_s = time.monotonic() - start
    samples, pids = collector.snapshot()
    agg = aggregate_samples(samples)
    record = _build_record(child_cmd=None, exit_code=0, wall_s=wall_s, agg=agg,
                           pids_sampled=pids, off_windows=os.name != "nt")
    record["no_hosts_seen"] = not saw_hosts
    record["lane"] = lane
    _write_json(out, record)
    return 0


# ------------------------------------------------------------------ CLI


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Record peak dedicated + shared (WDDM spill) VRAM for a job or a night lane.")
    p.add_argument("--out", required=True, help="path to write the JSON record")
    p.add_argument("--attach", action="store_true",
                   help="watch a lane's BEAT hosts instead of spawning a child")
    p.add_argument("--lane", default="gpu", choices=("gpu", "cpu"),
                   help="attach mode: lane whose worker dir is runs/lanes/<lane>/workers")
    p.add_argument("--runs-dir", default="runs",
                   help="attach mode: runs root (default: <repo>/runs)")
    p.add_argument("--deadline-seconds", type=float, default=None,
                   help="attach mode: how long to watch")
    p.add_argument("--period", type=float, default=DEFAULT_PERIOD_S,
                   help=f"sample cadence in seconds (default {DEFAULT_PERIOD_S:g})")
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" in argv:
        split = argv.index("--")
        head, child = argv[:split], argv[split + 1:]
    else:
        head, child = argv, []
    parser = _parser()
    args = parser.parse_args(head)

    if args.attach:
        if args.deadline_seconds is None or args.deadline_seconds <= 0:
            parser.error("--attach needs --deadline-seconds > 0")
        return run_attach(lane=args.lane, runs_dir=args.runs_dir,
                          deadline_s=args.deadline_seconds, out=args.out,
                          period=args.period)
    if not child:
        parser.error("spawn mode needs '-- <child command + args...>'")
    return run_spawn(child, args.out, period=args.period)


if __name__ == "__main__":
    raise SystemExit(main())
