"""Compare two search run directories (e.g. pipeline_prefetch off vs on) for the WP2 gate.

Checks that the two ``search.ndjson`` files hold the SAME candidates in the SAME order with the
SAME objectives (timing fields ignored), then prints wall-clock and candidates/hour from each
``run.json``. Exit code 0 = identical results, 1 = they differ.

    .venv\\Scripts\\python.exe tools\\bench\\compare_search_runs.py runs\\serial_run runs\\prefetch_run
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KEYS = ("n", "design_hash", "mesh_hash", "solve_hash", "key", "objective", "terms", "ok", "kind", "cached")


def read_rows(run_dir) -> list[dict]:
    rows = []
    p = Path(run_dir) / "search.ndjson"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def compare_rows(a: list[dict], b: list[dict], rel_tol: float = 0.0) -> list[str]:
    """Human-readable differences (empty list = identical on the compared keys)."""
    out = []
    if len(a) != len(b):
        out.append(f"row count differs: {len(a)} vs {len(b)}")
    for i, (ra, rb) in enumerate(zip(a, b)):
        for k in KEYS:
            va, vb = ra.get(k), rb.get(k)
            if isinstance(va, float) and isinstance(vb, float):
                same = abs(va - vb) <= rel_tol * max(abs(va), abs(vb), 1e-300)
            else:
                same = va == vb
            if not same:
                out.append(f"row {i} key {k}: {va!r} vs {vb!r}")
    return out


def run_stats(run_dir) -> dict:
    p = Path(run_dir) / "run.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    s = d.get("last_invocation") or d.get("stats") or {}
    return {"candidates_per_hour": s.get("candidates_per_hour"),
            "mean_seconds_per_candidate": s.get("mean_seconds_per_candidate"),
            "pipeline_prefetch": d.get("pipeline_prefetch"), "status": d.get("status")}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print(__doc__)
        return 2
    a, b = argv
    diffs = compare_rows(read_rows(a), read_rows(b))
    sa, sb = run_stats(a), run_stats(b)
    print(f"A {a}: {sa}\nB {b}: {sb}")
    if sa.get("candidates_per_hour") and sb.get("candidates_per_hour"):
        print(f"candidates/hour ratio B/A = {sb['candidates_per_hour'] / sa['candidates_per_hour']:.3f}")
    if diffs:
        print(f"RESULTS DIFFER ({len(diffs)}):")
        for d in diffs[:20]:
            print("  " + d)
        return 1
    print("IDENTICAL: same candidates, same order, same objectives.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
