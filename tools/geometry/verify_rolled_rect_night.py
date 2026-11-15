"""Verify rolled-rectangle night results with their required opt-in geometry adapter."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.night_queue.verify_night_jobs import latest_rows, plan

WRAPPER = ROOT / "tools" / "geometry" / "rolled_rect_cli.py"
MEMWATCH = ROOT / "tools" / "bench" / "run_with_memwatch.py"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--night", required=True, action="append")
    parser.add_argument("--jobs", required=True, help="comma-separated job IDs")
    parser.add_argument("--top", type=int, default=1)
    parser.add_argument("--nights-dir", default=str(ROOT / "runs" / "nights"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    jobs = [job.strip() for job in args.jobs.split(",") if job.strip()]
    if args.top < 1 or not jobs or len(jobs) != len(set(jobs)):
        parser.error("--top must be positive and --jobs must contain distinct job IDs")
    rows = {}
    for night in args.night:
        rows.update(latest_rows(Path(args.nights_dir) / night / "summary.jsonl"))
    todo, skipped = plan(rows, jobs, args.top, {})
    for job, reason in skipped:
        print(f"[verify_rolled_rect] SKIP {job}: {reason}", flush=True)
    env = dict(os.environ)
    env["HORNLAB_FREQ_BATCH_SIZE"] = "12"
    mw_dir = Path(args.nights_dir) / args.night[-1] / "memwatch"
    failed = []
    for job, run_dir, top in todo:
        command = [sys.executable, str(MEMWATCH), "--out", str(mw_dir / f"{job}.json"), "--",
                   sys.executable, str(WRAPPER), "verify", "--run", str(run_dir), "--top", str(top)]
        print(f"[verify_rolled_rect] {job}: {' '.join(command)}", flush=True)
        if args.dry_run:
            continue
        mw_dir.mkdir(parents=True, exist_ok=True)
        rc = subprocess.call(command, cwd=str(ROOT), env=env)
        if rc != 0:
            failed.append(job)
            print(f"[verify_rolled_rect] {job}: exit {rc}", flush=True)
    return 3 if skipped or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
