"""A.3 sensitivity.py — per-knob influence on J for one search run.

Usage:  PY tools\\analysis\\sensitivity.py --run <dir> [--runs-dir <base>] --out <dir>

Per knob: Spearman rho vs J on valid rows (optimizer samples — biased, see the
2026-11-12 study), the top-decile-vs-all distribution shift, and — when sklearn is
installed and there are enough rows — a global surrogate (RandomForest on ALL valid
rows of the family) with permutation importance, which is not biased by the optimizer's
sampling density. Productionised from ``study_2026-11-12/sensitivity_analysis.py``
(same rank-correlation and top-decile logic, cited here). Sobol needs SALib, which is
NOT installed, so there is no Sobol here.
Schema: ``tools/analysis/schema.md`` § sensitivity.json.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from _common import (add_out_arg, bounds_of, fail, load_run, knobs_shared, params_flat,
                     run_meta, spearman, top_decile, valid_rows, write_report)

TOOL = "sensitivity"
MIN_ROWS = 10          # below this a per-knob rho is meaningless (same floor as the study)
SURROGATE_MIN_ROWS = 60


def _pool_family_rows(run: dict, family: str | None, runs_dir: Path | None,
                      objective_version: int | None) -> list[dict]:
    """Valid rows of the SAME family + objective version, pooled from ``--runs-dir`` (optional).

    The global surrogate wants the full design set of a family, not only one optimizer's
    path (2026-11-12 amendment to A.3)."""
    if runs_dir is None:
        return valid_rows(run["rows"])
    rows = []
    for d in sorted(Path(runs_dir).iterdir()):
        if not (d / "search.ndjson").exists():
            continue
        other = load_run(d)
        m = other["meta"]
        if family and m["family"] != family:
            continue
        if objective_version and m["objective_version"] != objective_version:
            continue
        rows.extend(valid_rows(other["rows"]))
    return rows


def analyse_run(run_dir: Path, family_runs_dir: Path | None = None) -> dict:
    run = load_run(Path(run_dir))
    meta = run["meta"]
    valid = valid_rows(run["rows"])
    out: dict = {"run_dir": str(run["run_dir"]), "family": meta["family"],
                 "objective_version": meta["objective_version"],
                 "n_valid": len(valid), "top_decile_n": None,
                 "spearman": [], "top_decile_shift": [], "surrogate": None}
    if len(valid) < MIN_ROWS:
        return out
    keys = knobs_shared(valid)
    jvals = np.array([float(r["objective"]) for r in valid])
    pmat = [params_flat(r) for r in valid]
    top = top_decile(run["rows"])
    out["top_decile_n"] = len(top) if top else None
    top_params = [params_flat(r) for r in top] if top else []

    for key in keys:
        kvals = np.array([p.get(key, float("nan")) for p in pmat])
        rho = spearman(kvals, jvals)
        if rho is None:
            continue
        out["spearman"].append({"key": key, "rho": rho, "rho_abs": abs(rho), "n": len(valid)})
    out["spearman"].sort(key=lambda s: -s["rho_abs"])

    bounds = run["bounds"]
    for key in keys:
        allv = np.array([p.get(key, float("nan")) for p in pmat])
        topv = np.array([p.get(key, float("nan")) for p in top_params])
        if not np.isfinite(allv).any() or not np.isfinite(topv).any():
            continue
        mean_all, mean_top = float(np.nanmean(allv)), float(np.nanmean(topv))
        shift = None
        if key in bounds:
            lo, hi = bounds[key]
            shift = (mean_top - mean_all) / (hi - lo)
        out["top_decile_shift"].append({"key": key, "mean_all": mean_all, "mean_top": mean_top,
                                        "shift_norm": shift})
    out["top_decile_shift"].sort(key=lambda s: -abs(s["shift_norm"] or 0.0))

    out["surrogate"] = _surrogate(keys, pmat, jvals, meta["family"],
                                  family_pool=_pool_family_rows(run, meta["family"],
                                                                family_runs_dir,
                                                                meta["objective_version"]))
    return out


def _surrogate(keys: list[str], pmat: list[dict], jvals: np.ndarray, family: str | None,
               *, family_pool: list[dict] | None = None) -> dict | None:
    """sklearn RandomForest permutation importance; None when sklearn is missing or rows too few."""
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.inspection import permutation_importance
        from sklearn.model_selection import train_test_split
    except Exception:  # noqa: BLE001 - optional dependency by design
        return {"available": False, "note": "sklearn not installed; Spearman only"}

    # Use the pooled rows when we have them (all valid rows of the family); else this run's rows.
    if family_pool:
        Xkeys = knobs_shared(family_pool)
        X = np.array([[params_flat(r).get(k, np.nan) for k in Xkeys] for r in family_pool], dtype=float)
        y = np.array([float(r["objective"]) for r in family_pool], dtype=float)
    else:
        Xkeys = keys
        X = np.array([np.array([p.get(k, np.nan) for k in keys]) for p in pmat], dtype=float)
        y = np.asarray(jvals, dtype=float)
    good = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[good], y[good]
    if X.shape[0] < SURROGATE_MIN_ROWS or X.shape[1] == 0:
        return {"available": False, "note": f"too few rows ({int(X.shape[0])} < {SURROGATE_MIN_ROWS})"}
    # sklearn 1.9's train_test_split returns a sequence of 4 arrays (train/test, X/y).
    splits = train_test_split(X, y, test_size=0.2, random_state=0)
    if len(splits) != 4:
        return {"available": False, "note": "unexpected train_test_split arity"}
    Xtr, Xte, ytr, yte = (np.asarray(part, dtype=float) for part in splits)
    model = RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=1)
    model.fit(Xtr, ytr)
    r2 = float(model.score(Xte, yte))
    # permutation_importance returns a Bunch (a dict subclass) carrying means/stds per knob.
    imp = permutation_importance(model, Xte, yte, n_repeats=10, random_state=0, n_jobs=1)
    imp_mean = np.asarray(imp["importances_mean"], dtype=float)
    imp_std = np.asarray(imp["importances_std"], dtype=float)
    if imp_mean.shape != (len(Xkeys),) or imp_std.shape != (len(Xkeys),):
        return {"available": False, "note": "permutation importance shape mismatch"}
    importance = sorted(({"key": k, "permutation_importance": float(m), "std": float(s)}
                         for k, m, s in zip(Xkeys, imp_mean, imp_std)),
                        key=lambda d: -d["permutation_importance"])
    return {"available": True, "model": "RandomForestRegressor", "n_train": int(Xtr.shape[0]),
            "n_test": int(Xte.shape[0]), "r2": r2, "importance": importance}


def _md(payload: dict) -> str:
    r = payload
    lines = ["# Sensitivity", "",
             f"Run `{Path(r['run_dir']).name}` (family `{r['family']}`, objective"
             f" v{r['objective_version']}, {r['n_valid']} valid rows).",
             "Spearman on optimizer samples is biased; the surrogate importance below is the",
             "unbiased companion (productionised from `study_2026-11-12/sensitivity_analysis.py`).", ""]
    if r["spearman"]:
        lines += ["| knob | rho | n |", "|---|---:|---:|"]
        for s in r["spearman"]:
            lines.append(f"| `{s['key']}` | {s['rho']:+.3f} | {s['n']} |")
        lines.append("")
    if r["top_decile_shift"]:
        lines += ["### Top-decile vs all (distribution shift)", "",
                  "| knob | mean all | mean top | shift (norm to bound width) |", "|---|---:|---:|---:|"]
        for s in r["top_decile_shift"]:
            shift = s["shift_norm"]
            shift_s = "—" if shift is None else f"{shift:.3f}"
            lines.append(f"| `{s['key']}` | {s['mean_all']:.4g} | {s['mean_top']:.4g} | {shift_s} |")
        lines.append("")
    sur = r["surrogate"]
    if sur and sur.get("available"):
        lines += [f"### Global surrogate ({sur['model']}, R² OOS {sur['r2']:.2f})", "",
                  "| knob | permutation importance (ΔJ) |", "|---|---:|"]
        for s in sur["importance"]:
            lines.append(f"| `{s['key']}` | {s['permutation_importance']:.4g} ± {s['std']:.2g} |")
        lines.append("")
    elif sur:
        lines += [f"_Surrogate unavailable: {sur.get('note', '')}_", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--run", required=True, help="run dir")
    ap.add_argument("--runs-dir", default=None,
                    help="optional base dir whose runs of the same family+objective version "
                         "pool the global surrogate's training rows")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    try:
        payload = analyse_run(Path(args.run),
                              Path(args.runs_dir) if args.runs_dir else None)
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"sensitivity: {exc}") from exc

    def fn(plt):
        if not payload["spearman"]:
            return None
        ss = payload["spearman"][:15]
        fig, ax = plt.subplots(figsize=(6, 0.35 * len(ss) + 1.5))
        y = list(range(len(ss)))[::-1]
        ax.barh(y, [s["rho"] for s in ss])
        ax.set_yticks(y, [s["key"] for s in ss])
        ax.axvline(0, color="k", lw=0.8)
        ax.set_xlabel("Spearman rho (higher value → lower J when negative)")
        fig.tight_layout()
        return fig

    write_report(Path(args.out), TOOL, payload, _md(payload), {"sensitivity.png": fn})
    print(f"sensitivity OK: {payload['n_valid']} valid rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
