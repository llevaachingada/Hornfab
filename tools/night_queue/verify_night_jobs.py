"""Verify the top-N designs of search jobs that ran EARLIER IN THE SAME NIGHT.

A night file cannot name a run directory that does not exist yet (search run dirs are
timestamped at launch), so ``hornlab-search verify --run <dir>`` cannot be written into the
night file directly. This helper reads ``runs/nights/<night>/summary.jsonl`` (one row per
finished job, written by ``tools/run_campaign_night.py``), finds each named job's run_dir and
runs ``hornlab-search verify --run <dir> --top N`` on it, strictly one after another.

    .venv\\Scripts\\python.exe tools\\night_queue\\verify_night_jobs.py --night <night> \\
        --top 5 --jobs job_a,job_b [--top-for job_c=2] [--dry-run]

Verify is the heavy tier, so by default each verify runs with the owner-approved batch-12 recipe
(CONTINUITY 2026-11-14 "BATCH-12 FOR HEAVY RUNS": ``HORNLAB_FREQ_BATCH_SIZE=12`` for verify/final
only; screens stay unbatched) and under ``tools/bench/run_with_memwatch.py`` (spawn mode), which
writes ``runs/nights/<night>/memwatch/<job>.json`` with the dedicated + shared (WDDM spill) peaks
the recipe asks to record for the first heavy batched runs. ``--freq-batch-size 0`` leaves the
environment untouched; ``--no-memwatch`` runs verify bare.

Jobs that are missing from the summary, did not exit 0, or have no run_dir are reported and
skipped (the rest still verify). Exit code: 0 when every requested job verified, 3 when some
were skipped or failed, 2 on bad arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / ".venv" / "Scripts" / "hornlab-search.exe"
MEMWATCH = REPO_ROOT / "tools" / "bench" / "run_with_memwatch.py"


def latest_rows(summary: Path) -> dict[str, dict]:
    """job id -> its LAST summary row (a retried job appends a second row)."""
    rows: dict[str, dict] = {}
    if not summary.is_file():
        return rows
    for line in summary.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("id"):
            rows[str(row["id"])] = row
    return rows


def plan(rows: dict[str, dict], jobs: list[str], top: int, top_for: dict[str, int]) -> tuple[list, list]:
    todo, skipped = [], []
    for job in jobs:
        row = rows.get(job)
        if row is None:
            skipped.append((job, "not in summary.jsonl (not run yet, or a different night)"))
            continue
        if row.get("exit_code") != 0:
            skipped.append((job, f"exit_code {row.get('exit_code')!r}"))
            continue
        run_dir = row.get("run_dir")
        if not run_dir or not (Path(run_dir) / "search.ndjson").is_file():
            skipped.append((job, f"no usable run_dir ({run_dir!r})"))
            continue
        todo.append((job, run_dir, int(top_for.get(job, top))))
    return todo, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--night", required=True, help="night name (runs/nights/<night>/summary.jsonl)")
    ap.add_argument("--jobs", required=True, help="comma-separated job ids of that night")
    ap.add_argument("--top", type=int, default=5, help="designs per job (default 5)")
    ap.add_argument("--top-for", action="append", default=[], metavar="JOB=N",
                    help="per-job override of --top (repeatable)")
    ap.add_argument("--nights-dir", default=str(REPO_ROOT / "runs" / "nights"))
    ap.add_argument("--freq-batch-size", type=int, default=12,
                    help="HORNLAB_FREQ_BATCH_SIZE for the verify children (default 12, the heavy-run "
                         "recipe); 0 = leave the environment as it is")
    ap.add_argument("--no-memwatch", action="store_true",
                    help="do not wrap verify in tools/bench/run_with_memwatch.py")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    a = ap.parse_args(argv)
    if a.freq_batch_size < 0:
        print("--freq-batch-size must be >= 0", file=sys.stderr)
        return 2
    top_for: dict[str, int] = {}
    for item in a.top_for:
        job, _, n = item.partition("=")
        if not job or not n.isdigit():
            print(f"bad --top-for {item!r} (want JOB=N)", file=sys.stderr)
            return 2
        top_for[job] = int(n)
    jobs = [j.strip() for j in a.jobs.split(",") if j.strip()]
    rows = latest_rows(Path(a.nights_dir) / a.night / "summary.jsonl")
    todo, skipped = plan(rows, jobs, a.top, top_for)
    for job, why in skipped:
        print(f"[verify_night_jobs] SKIP {job}: {why}", flush=True)
    env = dict(os.environ)
    if a.freq_batch_size:
        env["HORNLAB_FREQ_BATCH_SIZE"] = str(a.freq_batch_size)
    print(f"[verify_night_jobs] HORNLAB_FREQ_BATCH_SIZE={env.get('HORNLAB_FREQ_BATCH_SIZE', '<unset>')}"
          f" memwatch={'off' if a.no_memwatch else 'on'}", flush=True)
    mw_dir = Path(a.nights_dir) / a.night / "memwatch"
    failed = []
    for job, run_dir, n in todo:
        argv_v = [str(CLI), "verify", "--run", run_dir, "--top", str(n)]
        if not a.no_memwatch:
            argv_v = [sys.executable, str(MEMWATCH), "--out", str(mw_dir / f"{job}.json"), "--", *argv_v]
        print(f"[verify_night_jobs] {job}: {' '.join(argv_v)}", flush=True)
        if a.dry_run:
            continue
        mw_dir.mkdir(parents=True, exist_ok=True)
        rc = subprocess.call(argv_v, cwd=str(REPO_ROOT), env=env)
        print(f"[verify_night_jobs] {job}: exit {rc}", flush=True)
        if rc != 0:
            failed.append(job)
    if skipped or failed:
        print(f"[verify_night_jobs] skipped {len(skipped)}, failed {len(failed)} {failed}", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
