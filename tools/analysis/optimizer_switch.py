"""Advisory optimizer decision report for recorded search runs; never executes a search.

Usage: PY tools/analysis/optimizer_switch.py --run RUN [--run RUN ...] --out DIR
Each run is assessed separately. This is not an optimizer comparison or a BO admission gate.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from _common import cost_ledger, fail, load_run, run_fingerprint, write_report
from walls import analyse_run as analyse_walls

TOOL = "optimizer_switch"
THRESHOLDS = {"failure_min_attempts": 25, "failure_window": 30,
              "failure_fraction": 0.30, "stall_valid": 40,
              "min_relative_improvement": 0.005, "bo_min_usable_rows": 100}


def _valid(row):
    value = row.get("objective")
    return (row.get("ok") is True and isinstance(value, (int, float))
            and not isinstance(value, bool) and math.isfinite(value) and value < 900)


def analyse_run(path: Path) -> dict:
    run = load_run(path)
    rows = run["rows"]
    valid = [r for r in rows if _valid(r)]
    window = rows[-THRESHOLDS["failure_window"]:]
    failure_fraction = (sum(not _valid(r) for r in window) / len(window)) if window else None
    unhealthy = (len(rows) >= THRESHOLDS["failure_min_attempts"] and
                 failure_fraction is not None and failure_fraction > THRESHOLDS["failure_fraction"])
    n = THRESHOLDS["stall_valid"]
    progress = {"valid_rows": len(valid), "best_j": None, "best_row_n": None,
                "first_j": None, "relative_gain_last_window": None, "stalled": None}
    if valid:
        best = min(valid, key=lambda r: r["objective"])
        progress.update(best_j=best["objective"], best_row_n=best.get("n"),
                        first_j=valid[0]["objective"])
    if len(valid) > n:
        before = min(r["objective"] for r in valid[:-n])
        now = min(r["objective"] for r in valid)
        gain = (before - now) / max(abs(before), 1e-12)
        progress.update(relative_gain_last_window=gain,
                        stalled=gain < THRESHOLDS["min_relative_improvement"])

    try:
        wall = analyse_walls(path)
    except (TypeError, ValueError, KeyError) as exc:
        # Historical rows can lack an objective or parameters. Do not infer no wall.
        wall = {"walls": [], "note": f"Wall analysis unavailable: {exc}"}
    pins = [w for w in wall["walls"] if w["wall_lo"] or w["wall_hi"]]
    recommendations = []
    if unhealthy:
        recommendations.append("Investigate geometry, envelope, resource and solver failure kinds first; the aggregate failure rate does not identify the cause.")
    if pins:
        recommendations.append("Review the pinned dimensions and physical limits; a wall is a diagnostic, not proof that widening is safe or useful. Do not automatically widen.")
    if progress["stalled"]:
        recommendations.append("Investigate headroom and sampling scale; consider a new seed or global exploration. For a collapsed TuRBO region, inspect its recorded state and consider a separately controlled restart, not an assumed automatic one.")
    if not recommendations:
        recommendations.append("No decisive switch signal: gather more compatible evidence and check search headroom and sampling scale.")
    recommendations.append("For BO, use study_cohort and prepare_study.py's strict cohort/admission checks; 100 usable training rows is a minimum, and this report's raw valid row count is not that gate.")
    return {"run_dir": str(path), "meta": run["meta"], "fingerprint": run_fingerprint(run),
            "cost_ledger": cost_ledger(rows),
            "failure_signal": {"window_rows": len(window), "fraction": failure_fraction,
                               "above_threshold": unhealthy,
                               "definition": "not ok or missing, nonfinite or >=900 objective; includes failures, refusals and cached rows"},
            "progress": progress, "walls": wall["walls"], "wall_note": wall.get("note"),
            "recommendations": recommendations}


def _md(payload):
    lines = ["# Optimizer decision report", "", payload["limitations"], "",
             f"Heuristics: `{THRESHOLDS}`; walls use the existing top-decile wall analysis.", ""]
    for run in payload["runs"]:
        p = run["progress"]
        f = run["failure_signal"]
        lines += [f"## {run['run_dir']}", "",
                  f"Valid rows: {p['valid_rows']}; best J: {p['best_j']} (row n={p['best_row_n']}); "
                  f"stall: {p['stalled']}; failure/refusal fraction: {f['fraction']} "
                  f"over {f['window_rows']} rows.",
                  f"Wall signals: {', '.join(w['key'] for w in run['walls'] if w['wall_lo'] or w['wall_hi']) or 'none reported'}. "
                  f"{run['wall_note'] or ''}", ""]
        lines.extend(f"- {item}" for item in run["recommendations"])
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="append", required=True, help="search run directory; repeat for multiple runs")
    parser.add_argument("--out", required=True, help="report directory outside the input runs")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    paths = [Path(p).resolve() for p in args.run]
    if any(out == path or path in out.parents for path in paths):
        raise fail("optimizer_switch: output must be outside input run directories")
    try:
        runs = [analyse_run(path) for path in paths]
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"optimizer_switch: {exc}") from exc
    payload = {"thresholds": THRESHOLDS, "runs": runs,
               "limitations": "Advisory heuristics only; no optimizer is switched and no config is changed. Runs are not compared. Raw rows are not independent seeds or verified BO training observations. Missing timing, cached rows and unrecorded preparation costs limit the ledger; inspect identities and matched budgets before comparing methods."}
    write_report(out, TOOL, payload, _md(payload))
    print(f"optimizer_switch OK: {len(runs)} run(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
