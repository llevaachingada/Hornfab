"""Advisory optimizer decision report for recorded search runs; never executes a search.

Usage: PY tools/analysis/optimizer_switch.py --run RUN [--run RUN ...] --out DIR
Each run is assessed separately. This is not an optimizer comparison or a BO admission gate.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from _common import cost_ledger, fail, load_run, read_json, run_fingerprint, write_report
from walls import analyse_run as analyse_walls

TOOL = "optimizer_switch"
THRESHOLDS = {"failure_min_attempts": 25, "failure_window": 30,
              "failure_fraction": 0.30, "stall_valid": 40,
              "min_relative_improvement": 0.005, "bo_min_usable_rows": 100}

#: Advisory switch vocabulary.  Every recommendation is a suggestion; this tool never executes a
#: search, changes a queue or switches an optimizer.
SWITCH_RECOMMENDATIONS = ("CONTINUE_CMA", "TRY_SCALAR_BO", "TRY_TURBO", "TRY_METRIC_COMPOSITE",
                          "REVIEW_BOUNDS", "INSUFFICIENT_DATA", "MODEL_UNAVAILABLE")
SWITCH_THRESHOLDS = {"min_valid_solves": 12, "cohort_coverage_min": 0.5,
                     "incumbent_concentration_high": 0.6, "bounds_saturation_high": 0.5,
                     "model_spearman_min": 0.5}
VALIDATION_STATUSES = ("research_only", "validation_required", "validated")


def _valid(row):
    value = row.get("objective")
    return (row.get("ok") is True and isinstance(value, (int, float))
            and not isinstance(value, bool) and math.isfinite(value) and value < 900)


def _bounded_switch_inputs(report: dict, *, bounds: dict | None = None,
                           model_diagnostics: dict | None = None,
                           historical_validation=None) -> dict:
    progress = report.get("progress") or {}
    rows = report.get("_rows")
    valid = [r for r in (rows or []) if _valid(r)]
    if rows is None:
        n_valid = int(progress.get("valid_rows") or 0)
        design_ids = set()
        objectives = []
    else:
        n_valid = len(valid)
        design_ids = {str(r.get("design_hash") or r.get("key") or r.get("n")) for r in valid}
        objectives = [float(r["objective"]) for r in valid]
    concentration = None
    if objectives:
        best = min(objectives)
        near = sum(abs(v - best) <= 0.01 * max(abs(best), 1e-12) for v in objectives)
        concentration = float(near / len(objectives))
    pins = [w for w in report.get("walls") or [] if w.get("wall_lo") or w.get("wall_hi")]
    pinned = {str(w.get("key")) for w in pins}
    active = set((bounds or {}).keys())
    saturation = (float(len(pinned & active) / len(active)) if active else None)
    coverage = None
    if rows is not None:
        coverage = (len(valid) / len(rows) if rows else None)
    return {
        "compatible_completed_solves": int(n_valid),
        "compatible_designs": int(len(design_ids) if rows is not None else n_valid),
        "active_dimension": int(len(active)),
        "cohort_coverage": coverage,
        "cma_stagnation": progress.get("stalled"),
        "incumbent_concentration": concentration,
        "bounds_saturation": saturation,
        "model_diagnostic_quality": model_diagnostics,
        "historical_validation_status": (
            historical_validation if isinstance(historical_validation, str)
            else "not_provided"),
        "expected_overhead": {
            "units": "relative GPU/CPU model fits per proposal round (rough, advisory)",
            "scalar_bo": 1.0,
            "turbo": 1.0,
            "metric_composite_v11": 6,
        },
        "thresholds": dict(SWITCH_THRESHOLDS),
    }


def _model_diagnostics_usable(model_diagnostics) -> bool:
    if not isinstance(model_diagnostics, dict):
        return False
    if str(model_diagnostics.get("status", "ok")).lower() != "ok":
        return False
    spearman = model_diagnostics.get("spearman")
    if spearman is not None:
        try:
            if not math.isfinite(float(spearman)) or float(spearman) < SWITCH_THRESHOLDS[
                    "model_spearman_min"]:
                return False
        except (TypeError, ValueError):
            return False
    return True


def build_switch(report: dict, *, bounds: dict | None = None,
                 model_diagnostics: dict | None = None,
                 historical_validation=None) -> dict:
    """Build the structured advisory switch block (no execution, no queue change).

    ``report`` is the dict :func:`analyse_run` builds.  ``model_diagnostics`` (optional) is the
    recorded quality of a candidate model; ``historical_validation`` (optional) is a validation
    status string.  The metric-composite recommendation is always labelled research-only /
    validation-required by default and never "proven superior".
    """
    inputs = _bounded_switch_inputs(report, bounds=bounds, model_diagnostics=model_diagnostics,
                                    historical_validation=historical_validation)
    reasons: list[str] = []
    recommendation = "CONTINUE_CMA"
    validity = (historical_validation if historical_validation in VALIDATION_STATUSES
                else "validation_required")
    model_usable = _model_diagnostics_usable(model_diagnostics)
    model_attempted = isinstance(model_diagnostics, dict)
    failure_signal = report.get("failure_signal") or {}
    progress = report.get("progress") or {}
    n_valid = inputs["compatible_completed_solves"]
    d = inputs["active_dimension"]
    coverage = inputs["cohort_coverage"]
    concentration = inputs["incumbent_concentration"]
    saturation = inputs["bounds_saturation"]

    if n_valid < SWITCH_THRESHOLDS["min_valid_solves"]:
        recommendation = "INSUFFICIENT_DATA"
        reasons.append(
            f"{n_valid} compatible completed solve(s) is below the advisory minimum "
            f"{SWITCH_THRESHOLDS['min_valid_solves']}; gather more compatible evidence first.")
    elif model_attempted and not model_usable:
        recommendation = "MODEL_UNAVAILABLE"
        reasons.append(
            "A model diagnostic was supplied but is unavailable or below the advisory quality "
            "floor; no model-based switch is recommended.")
    elif failure_signal.get("above_threshold"):
        recommendation = "CONTINUE_CMA"
        reasons.append(
            "The recent failure/refusal fraction is above threshold; investigate failure kinds "
            "before switching optimizer.")
    elif saturation is not None and saturation > SWITCH_THRESHOLDS["bounds_saturation_high"]:
        recommendation = "REVIEW_BOUNDS"
        reasons.append(
            f"Bounds saturation is {saturation:.2f} of the active dimension; review pinned "
            "dimensions and physical limits before any switch. Do not widen automatically.")
    elif progress.get("stalled"):
        reasons.append(
            "The valid-objective improvement over the last stall window is below the advisory "
            "floor.")
        if model_usable:
            recommendation = "TRY_METRIC_COMPOSITE"
            reasons.append(
                "A usable per-metric model diagnostic was supplied; a metric-composite proposal "
                "is worth a controlled trial only.")
        elif n_valid >= THRESHOLDS["bo_min_usable_rows"] and d <= 4:
            recommendation = "TRY_SCALAR_BO"
            reasons.append(
                f"Enough compatible solves ({n_valid}) and a small active dimension ({d}); a "
                "scalar BO trial is a reasonable next experiment.")
        elif n_valid >= SWITCH_THRESHOLDS["min_valid_solves"] and d > 4:
            recommendation = "TRY_TURBO"
            reasons.append(
                f"Active dimension {d} is large for a global scalar GP; a trust-region (TuRBO) "
                "trial is a reasonable next experiment.")
        else:
            recommendation = "CONTINUE_CMA"
            reasons.append(
                "No model diagnostic was supplied and the cohort is below the BO row minimum; "
                "continue CMA and gather compatible observations.")
    else:
        recommendation = "CONTINUE_CMA"
        reasons.append("No decisive switch signal in this report; continue the current CMA run.")
        if coverage is not None and coverage < SWITCH_THRESHOLDS["cohort_coverage_min"]:
            reasons.append(
                f"Only {coverage:.2f} of recorded rows are compatible completed solves; this "
                "weakens any downstream cohort/model claim.")
        if concentration is not None and concentration > SWITCH_THRESHOLDS[
                "incumbent_concentration_high"]:
            reasons.append(
                f"Incumbent concentration is high ({concentration:.2f} of valid rows within 1% "
                "of the best); watch for a collapsed search region.")

    if recommendation == "TRY_METRIC_COMPOSITE":
        if model_diagnostics is None:
            validity = "validation_required"
        elif validity == "validated":
            validity = "validation_required"
        reasons.append(
            "Metric-composite is research-only here: "
            f"{validity}. It has never been shown superior in this report; do not present it as "
            "proven and do not switch production policy without validation.")
    else:
        reasons.append(
            "Metric-composite remains research-only and is not recommended by this report.")

    return {
        "recommendation": recommendation,
        "reasons": reasons,
        "advisory_only": True,
        "executes_search": False,
        "changes_queue": False,
        "inputs": inputs,
        "metric_composite": {
            "status": validity,
            "research_only": True,
            "validation": validity,
            "never_proven_superior": True,
            "model_diagnostics_supplied": bool(model_attempted),
            "model_diagnostics_usable": bool(model_usable),
            "historical_validation_status": inputs["historical_validation_status"],
        },
        "vocabulary": list(SWITCH_RECOMMENDATIONS),
    }


def analyse_run(path: Path, *, model_diagnostics: dict | None = None,
                historical_validation=None) -> dict:
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
    report = {"run_dir": str(path), "meta": run["meta"], "fingerprint": run_fingerprint(run),
              "cost_ledger": cost_ledger(rows),
              "failure_signal": {"window_rows": len(window), "fraction": failure_fraction,
                                 "above_threshold": unhealthy,
                                 "definition": "not ok or missing, nonfinite or >=900 objective; includes failures, refusals and cached rows"},
              "progress": progress, "walls": wall["walls"], "wall_note": wall.get("note"),
              "recommendations": recommendations,
              "_rows": rows}
    report["switch"] = build_switch(report, bounds=run.get("bounds"),
                                    model_diagnostics=model_diagnostics,
                                    historical_validation=historical_validation)
    report.pop("_rows", None)
    return report


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
        switch = run.get("switch") or {}
        if switch:
            lines += ["", f"Switch (advisory only): **{switch.get('recommendation')}**"]
            lines.extend(f"  - {item}" for item in switch.get("reasons") or [])
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--run", action="append", required=True, help="search run directory; repeat for multiple runs")
    parser.add_argument("--out", required=True, help="report directory outside the input runs")
    parser.add_argument("--model-diagnostics", default=None,
                        help="optional JSON file with model diagnostic quality (read-only)")
    parser.add_argument("--historical-validation", default=None,
                        help="optional validation status string for the advisory switch")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    paths = [Path(p).resolve() for p in args.run]
    if any(out == path or path in out.parents for path in paths):
        raise fail("optimizer_switch: output must be outside input run directories")
    model_diagnostics = None
    if args.model_diagnostics:
        model_diagnostics = read_json(Path(args.model_diagnostics))
        if not isinstance(model_diagnostics, dict):
            raise fail("optimizer_switch: --model-diagnostics must be a JSON object")
    try:
        runs = [analyse_run(path, model_diagnostics=model_diagnostics,
                            historical_validation=args.historical_validation)
                for path in paths]
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"optimizer_switch: {exc}") from exc
    payload = {"thresholds": THRESHOLDS, "runs": runs,
               "limitations": "Advisory heuristics only; no optimizer is switched and no config is changed. Runs are not compared. Raw rows are not independent seeds or verified BO training observations. Missing timing, cached rows and unrecorded preparation costs limit the ledger; inspect identities and matched budgets before comparing methods."}
    write_report(out, TOOL, payload, _md(payload))
    print(f"optimizer_switch OK: {len(runs)} run(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
