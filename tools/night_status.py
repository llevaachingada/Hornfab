"""One-shot status of unattended GPU nights: queue log tail, finished jobs per night, the job running now, and
the best designs so far. Read-only; safe while a night runs.

Usage (repo root)::

    .venv\\Scripts\\python.exe tools/night_status.py                      # nights touched in the last 24 h
    .venv\\Scripts\\python.exe tools/night_status.py --since-hours 6 --top 8
    .venv\\Scripts\\python.exe tools/night_status.py --queue-log runs/nights/queue_2026-10-28.log

J is comparable only WITHIN a brief (each brief has its own target and weights): the "best" table groups by brief.
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


def _rows(nd: Path) -> list[dict]:
    out = []
    for line in nd.read_text(encoding="utf-8", errors="replace").splitlines():
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


def _live_jobs() -> list[str]:
    try:
        ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hornlab-search(.exe)?\"? search' "
              "-and $_.Name -eq 'hornlab-search.exe' } | ForEach-Object { $_.CommandLine }")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30)
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except Exception:  # noqa: BLE001 - status is best effort
        return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since-hours", type=float, default=24.0)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--queue-log", help="a queue controller log to tail (default: newest runs/nights/*queue*.log)")
    args = ap.parse_args(argv)
    nights_dir = REPO / "runs" / "nights"
    cutoff = time.time() - args.since_hours * 3600

    logs = [Path(args.queue_log)] if args.queue_log else sorted(
        nights_dir.glob("*queue*.log"), key=lambda p: p.stat().st_mtime)[-1:]
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

    print("## Running now")
    live = _live_jobs()
    if not live:
        print("  no hornlab-search search process")
    for cmd in live:
        m = re.search(r"--(?:config|resume)\s+(\S+)", cmd)
        target = m.group(1) if m else cmd[-80:]
        newest = max((p for p in (REPO / "runs").glob("*-screen-*") if p.is_dir()), key=lambda p: p.stat().st_mtime,
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
