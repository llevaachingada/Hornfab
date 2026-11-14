# -*- coding: utf-8 -*-
"""Spot-check of dossier measured findings 1 (refusal kinds) against runs/*/search.ndjson.

READ-ONLY on the main checkout: reads its runs/ tree; writes nothing there.
Run: .venv\\Scripts\\python.exe spotcheck_findings.py
"""
import json
from collections import Counter
from pathlib import Path

RUNS = Path(r"C:\Users\hunte\Hrns\hornlab-search\runs")

kinds = Counter()
n_rows = 0
n_runs = 0
for ndj in RUNS.glob("*/search.ndjson"):
    n_runs += 1
    for line in ndj.read_bytes().decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        n_rows += 1
        if not r.get("ok"):
            kinds[r.get("kind") or "?"] += 1

print(f"runs with search.ndjson: {n_runs}; rows total: {n_rows}")
total_fail = sum(kinds.values())
print(f"failed rows: {total_fail} ({100.0 * total_fail / max(n_rows, 1):.1f}% of rows)")
for k, v in kinds.most_common(12):
    print(f"  {k:20s} {v:6d}  ({100.0 * v / max(n_rows, 1):.1f}% of all rows)")
