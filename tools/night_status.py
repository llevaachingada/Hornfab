"""One-shot two-lane status of unattended nights: per-lane queue log tails, the running job per
lane, its run dir row count and newest-row age, the holder of ``runs/.gpu.lock`` /
``runs/.cpu.lane.lock`` (alive or stale), and ALERTs when a lane goes quiet while its job runs.
Read-only; safe while the nights run.

Usage (repo root)::

    .venv\\Scripts\\python.exe tools/night_status.py                      # nights touched in the last 24 h
    .venv\\Scripts\\python.exe tools/night_status.py --since-hours 6 --top 8
    .venv\\Scripts\\python.exe tools/night_status.py --queue-log runs/nights/queue_2026-10-28.log

Two lanes (2026-11-12): each lane's lock file is ``runs/.gpu.lock`` / ``runs/.cpu.lane.lock``
(same mechanism, separate files, one per lane). The runner writes per-night queue logs to
``runs/overnight/queue_<night>.log`` and the detached controllers write their start/stop notes to
``runs/nights/queue_*.log``; both are shown here. A lane is STALLED (ALERT) when its running job's
run dir has a ``search.ndjson`` whose newest row is older than 30 minutes.

J is comparable only WITHIN a brief (each brief has its own target and weights): the "best" table
groups by brief.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: Alert when a lane's running job has not written a row for this long (D.1).
NEWEST_ROW_ALERT_S = 30 * 60.0

#: A queue log older than this holds no running job (the runner wrote its last queue line when
#: the night died or ended); without the filter, weeks-old abandoned logs show phantom jobs.
QUEUE_LOG_FRESH_S = 24 * 3600.0

#: lane -> its lock file under ``runs/`` (same mapping as search/gpulock.LANE_LOCK_FILES).
LOCK_FILES = {"gpu": ".gpu.lock", "cpu": ".cpu.lane.lock"}


def _load_runner_helpers():
    """Parse helpers from tools/run_campaign_night.py by path (both files stay import-light)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_night_runner_helpers_for_status", REPO / "tools" / "run_campaign_night.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_runner = _load_runner_helpers()
_parse_run_dir = _runner.parse_run_dir
_count_evals = _runner.count_evals
_lock_holder_pid = _runner._lock_holder_pid
_pid_alive = _runner._pid_alive

_QUEUE_START_RE = re.compile(r"^=== (\S+) START (\S+) : (.*)$")
_QUEUE_END_RE = re.compile(r"^=== (\S+) END (\S+) exit (-?\d+)")
_QUEUE_BACKEND_RE = re.compile(r"--backend[ =](\S+)")


# ------------------------------------------------------------------ pure helpers


def _rows(nd: Path) -> list[dict]:
    out = []
    try:
        text = nd.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _brief_of(run_dir: Path) -> str:
    try:
        rj = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        return ((rj.get("config") or {}).get("brief") or {}).get("name") or "?"
    except (OSError, ValueError):
        return "?"


def lane_of_argv(argv: str) -> str:
    """The lane a job's argv implies: ``--backend beat_cpu`` -> cpu lane, otherwise gpu."""
    match = _QUEUE_BACKEND_RE.search(argv or "")
    return "cpu" if (match and match.group(1).startswith("beat_cpu")) else "gpu"


def parse_queue_log(text: str) -> list[dict]:
    """Open (running) jobs from a runner queue log's START/END lines, in first-start order.

    Returns ``[{"id", "argv", "started", "ended", "exit"}]``; a job is open while the last event
    mentioning it is a START (an END line closes it; RETRY lines keep it open).
    """
    open_jobs: dict[str, dict] = {}
    order: list[str] = []
    for line in (text or "").splitlines():
        line = line.lstrip("\ufeff")
        start = _QUEUE_START_RE.match(line)
        end = _QUEUE_END_RE.match(line)
        if start:
            stamp, job_id, argv = start.group(1), start.group(2), start.group(3)
            if job_id not in open_jobs:
                order.append(job_id)
            open_jobs[job_id] = {"id": job_id, "argv": argv.strip(),
                                 "started": stamp, "ended": None, "exit": None}
        elif end:
            job_id = end.group(2)
            open_jobs.setdefault(job_id, {"id": job_id, "argv": "", "started": end.group(1),
                                          "ended": None, "exit": None})
            open_jobs[job_id].update(ended=end.group(1), exit=int(end.group(3)))
    return [open_jobs[job_id] for job_id in order if open_jobs[job_id]["ended"] is None]


def night_queue_logs(runs_root: Path) -> list[tuple[str, Path]]:
    """``[(night, queue_log)]`` for every queue log under ``runs/overnight`` and ``runs/nights``,
    deduped per night: the runner's log (``overnight/queue_<night>.log``) wins because it holds
    the START/END lines; the controller's ``nights/queue*.log`` fills nights without a runner
    log (it carries no job entries, only start/stop notes)."""
    out: dict[str, Path] = {}
    for folder, pattern in (("nights", "*queue*.log"), ("overnight", "queue_*.log")):
        for path in sorted((runs_root / folder).glob(pattern)):
            if folder == "overnight" and "queue_" in path.name:
                night = path.name[len("queue_"):-len(".log")]
            else:
                night = path.stem.lstrip("_")
                if night.startswith("queue"):
                    night = night[len("queue"):].lstrip("_-")
            if not night:
                continue
            out[night] = path                              # overnight scanned second: it wins
    return sorted(out.items(), key=lambda kv: kv[1].stat().st_mtime)


def lock_status(lane: str, runs_root: Path, *, alive_fn=None) -> dict:
    """The state of one lane's lock file: ``{"held", "pid", "record", "alive"}`` (d.1)."""
    alive_fn = alive_fn or _pid_alive
    path = Path(runs_root) / LOCK_FILES.get(lane, f".{lane}.unknown.lock")
    record: dict | None = None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        record = data if isinstance(data, dict) else None
    except (OSError, ValueError):
        record = None
    pid = _lock_holder_pid(path)
    alive: bool | None = None
    if record is not None and isinstance(record.get("pid"), int) and record["pid"] > 0:
        pid = record["pid"]
    if pid is not None:
        alive = bool(alive_fn(int(pid)))
    return {"lane": lane, "path": str(path), "held": path.exists(), "record": record,
            "pid": pid, "alive": alive}


def scan_running_jobs(runs_root: Path, repo_root: Path, *, now: float | None = None,
                      queue_log_fresh_s: float | None = QUEUE_LOG_FRESH_S) -> list[dict]:
    """Every lane's currently running job, with its run dir row count and newest-row age.

    Rows come from the run dir's ``search.ndjson``; the newest-row age is the file's mtime
    relative to ``now`` (``None`` when there is no run dir or no ndjson yet). Queue logs older
    than ``queue_log_fresh_s`` hold no running job (abandoned night) and are skipped.
    """
    now = time.time() if now is None else float(now)
    jobs: list[dict] = []
    for night, queue_log in night_queue_logs(runs_root):
        if queue_log_fresh_s is not None and now - queue_log.stat().st_mtime > queue_log_fresh_s:
            continue
        try:
            text = queue_log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for entry in parse_queue_log(text):
            job_log = Path(runs_root) / "nights" / night / f"{entry['id']}.log"
            run_dir = _parse_run_dir(job_log.read_text(encoding="utf-8", errors="replace")
                                     if job_log.exists() else "", repo_root=repo_root)
            ndjson = (run_dir / "search.ndjson") if run_dir is not None else None
            newest_age: float | None = None
            if ndjson is not None and ndjson.exists():
                newest_age = max(0.0, now - ndjson.stat().st_mtime)
            jobs.append({
                "lane": lane_of_argv(entry["argv"]),
                "night": night,
                "id": entry["id"],
                "argv": entry["argv"],
                "started": entry["started"],
                "run_dir": None if run_dir is None else str(run_dir),
                "rows": _count_evals(ndjson) if ndjson is not None else 0,
                "newest_age_s": newest_age,
            })
    return jobs


def build_lane_report(runs_root: Path, repo_root: Path, *, now: float | None = None,
                      alive_fn=None) -> list[str]:
    """The rendered two-lane section (D.1), including ALERT lines."""
    now = time.time() if now is None else float(now)
    lines = ["## Lanes"]
    jobs = scan_running_jobs(runs_root, repo_root, now=now)
    for lane in ("gpu", "cpu"):
        lock = lock_status(lane, runs_root, alive_fn=alive_fn)
        lane_jobs = [job for job in jobs if job["lane"] == lane]
        if lock["held"]:
            record = lock["record"] or {}
            state = "live holder" if lock["alive"] else "STALE holder (pid gone; take over)"
            user = record.get("user", "?")
            command = str(record.get("command", "?"))[:90]
            since = record.get("start_time", "?")
            lines.append(f"- lane {lane}: lock {lock['path']} HELD by pid {lock['pid']} "
                         f"({state}): {user} running \"{command}\" since {since}")
        else:
            lines.append(f"- lane {lane}: lock {lock['path']} free")
        if not lane_jobs:
            lines.append("  - running job: none")
        for job in lane_jobs:
            age = job["newest_age_s"]
            age_text = "n/a" if age is None else f"{age / 60:.0f} min old"
            run_text = job["run_dir"] or "(run dir not parsed yet)"
            lines.append(f"  - running job {job['id']} (night {job['night']}, since "
                         f"{job['started']}): {run_text} - {job['rows']} rows, newest {age_text}")
            if age is not None and age > NEWEST_ROW_ALERT_S:
                lines.append(f"  - ALERT lane {lane}: newest row is {age / 60:.0f} min old "
                             f"(> {NEWEST_ROW_ALERT_S / 60:.0f}) while job {job['id']} runs; "
                             f"check the lane's hosts and {run_text}/search.ndjson")
    return lines


# ------------------------------------------------------------------ process probe (kept from 2026-10-28)


def _live_jobs() -> list[str]:
    try:
        ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hornlab-search(.exe)?\"? search' "
              "-and $_.Name -eq 'hornlab-search.exe' } | ForEach-Object { $_.CommandLine }")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30)
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except Exception:  # noqa: BLE001 - status is best effort
        return []


# ------------------------------------------------------------------ CLI


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since-hours", type=float, default=24.0)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--queue-log", help="a queue controller log to tail (default: newest runs/nights/*queue*.log)")
    args = ap.parse_args(argv)
    runs_root = REPO / "runs"
    nights_dir = runs_root / "nights"
    cutoff = time.time() - args.since_hours * 3600
    if not nights_dir.is_dir():
        print(f"no runs/nights under {REPO} (run this from the repo whose nights you want)")
        return 0

    print("\n".join(build_lane_report(runs_root, REPO)))
    print()

    queue_glob = list(runs_root.glob("overnight/queue_*.log")) + list(nights_dir.glob("*queue*.log"))
    logs = [Path(args.queue_log)] if args.queue_log else (
        sorted(queue_glob, key=lambda p: p.stat().st_mtime)[-1:] if queue_glob else [])
    for lg in logs:
        if lg.exists():
            print(f"## Queue log {lg.name} (last 6 lines)")
            for line in lg.read_text(encoding="utf-8", errors="replace").splitlines()[-6:]:
                print("  " + line.lstrip("﻿"))
            print()

    best: dict[str, list] = {}
    print("## Nights")
    for d in sorted((p for p in nights_dir.iterdir() if p.is_dir() and p.stat().st_mtime >= cutoff),
                    key=lambda p: p.stat().st_mtime):
        summ = d / "summary.jsonl"
        done = _rows(summ) if summ.exists() else []
        yml = nights_dir / f"{d.name}.yaml"
        n_jobs = len(re.findall(r"^\s*-\s*\{id:", yml.read_text(encoding="utf-8"), re.M)) if yml.exists() else "?"
        print(f"- **{d.name}**: {len(done)}/{n_jobs} jobs done")
        for j in done:
            note = "" if j.get("exit_code") == 0 else f"  <- exit {j.get('exit_code')}: {str(j.get('note'))[:60]}"
            print(f"    {j['id']}: best J {j.get('best_J')}, {j.get('evals_ndjson')} evals, "
                  f"{round(j.get('seconds', 0) / 60)} min{note}")
            rd = Path(j["run_dir"]) if j.get("run_dir") else None
            if rd and (rd / "search.ndjson").exists():
                for r in _rows(rd / "search.ndjson"):
                    if r.get("ok"):
                        best.setdefault(_brief_of(rd), []).append((float(r["objective"]), j["id"], r["design_hash"], rd.name))
    print()

    print("## Running now (search processes)")
    live = _live_jobs()
    if not live:
        print("  no hornlab-search search process")
    for cmd in live:
        m = re.search(r"--(?:config|resume)\s+(\S+)", cmd)
        target = m.group(1) if m else cmd[-80:]
        newest = max((p for p in (runs_root).glob("*-screen-*") if p.is_dir()), key=lambda p: p.stat().st_mtime,
                     default=None)
        prog = ""
        if newest and (newest / "search.ndjson").exists():
            rs = _rows(newest / "search.ndjson")
            ok = [float(r["objective"]) for r in rs if r.get("ok")]
            prog = f" - {newest.name}: {len(rs)} evals, best J {min(ok):.3f}" if ok else f" - {newest.name}: {len(rs)} evals"
            for r in rs:
                if r.get("ok"):
                    best.setdefault(_brief_of(newest), []).append((float(r["objective"]), "running", r["design_hash"], newest.name))
        print(f"  {target}{prog}")
    print()

    print(f"## Best designs per brief (top {args.top}; J comparable only within a brief)")
    for brief, items in sorted(best.items()):
        seen, rows = set(), []
        for J, job, h, rd in sorted(items):
            if h in seen:
                continue
            seen.add(h)
            rows.append(f"    {J:7.3f}  {job:38s} {h}  runs/{rd}")
            if len(rows) >= args.top:
                break
        print(f"- {brief}")
        print("\n".join(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
