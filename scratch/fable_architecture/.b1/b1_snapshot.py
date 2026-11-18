"""Freeze a read-only snapshot of the home-brief run dirs for the WP3 replay tool.

The live night queue appends to / rewrites ``run.json`` and ``search.ndjson`` of the runs it is
currently resuming, and the WP3 tool's zero-write guard (correctly) refuses a run whose hashed
source changed mid-read. This copies the *manifests* (run.json/best.json/config.yaml) and
junction-links the immutable ``designs/`` tree, so the replay reads a stable view while the
original run stays untouched and writable by the queue.

Snapshot lives under scratch/fable_architecture/.b1/snap/<run>/. Nothing under runs/ is written.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOME_BRIEF = "room_landscape_80x50_700_hf1440_v7.yaml"
SNAP = HERE / "snap"


def main() -> int:
    rows = json.loads((HERE / "home_brief_rows.json").read_text(encoding="utf-8"))["rows"]
    runs = sorted({r["run"] for r in rows})
    SNAP.mkdir(parents=True, exist_ok=True)
    made = 0
    for run in runs:
        src = REPO / "runs" / run
        dst = SNAP / run
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("run.json", "best.json", "config.yaml"):
            s = src / name
            if s.is_file():
                shutil.copy2(s, dst / name)
        link = dst / "designs"
        if not link.exists():
            # Junction: no admin needed on Windows; the source tree stays the only copy.
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(src / "designs")],
                           check=True, capture_output=True, text=True)
        made += 1
    print(f"[b1_snapshot] {made} run snapshots under {SNAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
