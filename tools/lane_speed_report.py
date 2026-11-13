"""Solo vs concurrent solve-speed report across lanes (GPU / CPU).

Reads every runs/*/search.ndjson (and run.ndjson-style single runs if present), takes rows that really solved
(not cached, solve seconds > 0, n_dof known), and tags each as SOLO or CONCURRENT: concurrent when its solve
interval overlaps the active window [first start, last end] of any run on the OTHER lane. Reports, per lane and
backend, median solve seconds and median seconds per 1000 dofs, solo vs concurrent, plus the slowdown ratio.

Read-only; stdlib only. Usage:
  .venv\\Scripts\\python.exe tools\\lane_speed_report.py [--runs runs] [--since 2026-11-01] [--csv out.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics as st
from datetime import datetime, timedelta, timezone
from pathlib import Path

CPU_BACKENDS = {"beat_cpu", "bempp_cpu"}


def _parse_utc(s: str) -> datetime:
    return datetime.strptime(s.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def _lane(row: dict) -> str:
    if row.get("lane"):
        return row["lane"]
    return "cpu" if row.get("backend") in CPU_BACKENDS else "gpu"


def load_rows(runs: Path, since: datetime | None) -> list[dict]:
    out = []
    for f in sorted(runs.glob("*/search.ndjson")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            sec = r.get("seconds") or {}
            solve, total = sec.get("solve") or 0.0, sec.get("total") or 0.0
            if r.get("cached") or solve <= 0 or not r.get("n_dof") or not r.get("created_utc"):
                continue
            end = _parse_utc(r["created_utc"])
            if since and end < since:
                continue
            out.append({
                "run": f.parent.name, "lane": _lane(r), "backend": r.get("backend") or "beat_cuda(assumed)",
                "n_dof": int(r["n_dof"]), "solve_s": float(solve),
                "start": end - timedelta(seconds=float(total)), "end": end,
            })
    return out


def tag_concurrency(rows: list[dict]) -> None:
    windows: dict[tuple[str, str], list[datetime]] = {}
    for r in rows:
        w = windows.setdefault((r["run"], r["lane"]), [r["start"], r["end"]])
        w[0], w[1] = min(w[0], r["start"]), max(w[1], r["end"])
    for r in rows:
        r["concurrent"] = any(
            lane != r["lane"] and a < r["end"] and r["start"] < b for (_, lane), (a, b) in windows.items()
        )


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["lane"], r["backend"], r["concurrent"]), []).append(r)
    out = []
    for (lane, backend, conc), g in sorted(groups.items()):
        out.append({
            "lane": lane, "backend": backend, "mode": "concurrent" if conc else "solo", "n": len(g),
            "runs": len({x["run"] for x in g}),
            "median_dof": int(st.median(x["n_dof"] for x in g)),
            "median_solve_s": round(st.median(x["solve_s"] for x in g), 1),
            "median_s_per_kdof": round(st.median(1000 * x["solve_s"] / x["n_dof"] for x in g), 2),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--since", help="YYYY-MM-DD (UTC), only rows after this date")
    ap.add_argument("--csv", help="also write the per-row table here")
    a = ap.parse_args()
    since = datetime.strptime(a.since, "%Y-%m-%d").replace(tzinfo=timezone.utc) if a.since else None
    rows = load_rows(Path(a.runs), since)
    if not rows:
        print("no solved rows found")
        return
    tag_concurrency(rows)
    summ = summarize(rows)
    hdr = ["lane", "backend", "mode", "n", "runs", "median_dof", "median_solve_s", "median_s_per_kdof"]
    print(" | ".join(hdr))
    for s in summ:
        print(" | ".join(str(s[h]) for h in hdr))
    print()
    for lane in sorted({s["lane"] for s in summ}):
        for backend in sorted({s["backend"] for s in summ if s["lane"] == lane}):
            m = {s["mode"]: s for s in summ if s["lane"] == lane and s["backend"] == backend}
            if "solo" in m and "concurrent" in m:
                ratio = m["concurrent"]["median_s_per_kdof"] / m["solo"]["median_s_per_kdof"]
                print(f"{lane}/{backend}: concurrent is {ratio:.2f}x solo per-kdof solve time "
                      f"({(ratio - 1) * 100:+.0f}%); solo n={m['solo']['n']}, concurrent n={m['concurrent']['n']}")
            else:
                print(f"{lane}/{backend}: only {', '.join(m)} data so far, no ratio")
    print("\nNote: per-kdof normalizes size only roughly (BEM cost is not linear in dofs); compare like configs.")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["run", "lane", "backend", "concurrent", "n_dof", "solve_s", "start", "end"])
            w.writeheader()
            for r in rows:
                w.writerow({k: r[k] for k in w.fieldnames})
        print(f"rows -> {a.csv}")


if __name__ == "__main__":
    main()
