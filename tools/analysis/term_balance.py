"""A.9 term_balance.py — which objective term actually carries J, per brief?

Usage:  PY tools\\analysis\\term_balance.py --run <dir> [--run <dir> ...] --out <dir>

Per brief: the share of J per term (weight * stored term / total, per valid row, then
median/mean across rows) and the RAW-unit distributions of the top-decile designs — the
data the v8 tolerance recalibration needs (2026-11-12 senior amendment). The stored
``terms`` in ``search.ndjson`` are the normalised units of the run's objective version
(v1-v3 rows store already-weighted contributions; v4+ rows store term/tolerance), so the
raw value is recovered with the run's config weights/tolerances (term names per
``hornlab_search/objective/terms.py`` / ``scalar_v4.py`` / ``scalar_v6.py``, read-only).
Schema: ``tools/analysis/schema.md`` § term_balance.json.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from _common import (add_out_arg, fail, load_run, run_meta, top_decile, valid_rows,
                     write_report)

TOOL = "term_balance"


def _weighted_keys(version: int | None) -> tuple:
    """Weighted term keys per objective version, from the repo's objective modules (read-only)."""
    from hornlab_search.objective.terms import WEIGHTED_KEYS
    from hornlab_search.objective.scalar_v4 import V4_WEIGHTED_KEYS
    from hornlab_search.objective.scalar_v6 import V6_WEIGHTED_KEYS
    from hornlab_search.objective.scalar_v7 import V7_WEIGHTED_KEYS
    v = int(version) if version else 0
    if v == 6:
        return tuple(V6_WEIGHTED_KEYS)
    if v == 7:
        return tuple(V7_WEIGHTED_KEYS)
    if v >= 4:
        return tuple(V4_WEIGHTED_KEYS)
    return tuple(WEIGHTED_KEYS)


def _weights_and_tolerances(cfg: dict, version: int | None) -> tuple[dict, dict]:
    weights = dict((cfg or {}).get("weights") or {})
    tolerances: dict = {}
    obj = (cfg or {}).get("objective")
    if isinstance(obj, dict):
        tolerances = dict(obj.get("tolerances") or {})
    return weights, tolerances


def _shares_and_raw(rows: list[dict], version: int | None, weights: dict,
                    tolerances: dict, top_rows: list[dict] | None) -> tuple[dict, dict]:
    """(per-term share stats, per-term raw-unit stats of the top-decile rows)."""
    wk = _weighted_keys(version)
    pre_weighted = version is not None and version < 4  # v3 rows store w*t directly
    share_vals: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        terms = r.get("terms") or {}
        total = terms.get("total")
        if not isinstance(total, (int, float)) or not total:
            continue
        for k in wk:
            t = terms.get(k)
            if isinstance(t, (int, float)):
                contrib = float(t) if pre_weighted else float(weights.get(k, 0.0)) * float(t)
                share_vals[k].append(contrib / float(total))
    shares = {}
    for k, vals in share_vals.items():
        shares[k] = {"median": float(np.median(vals)), "mean": float(np.mean(vals))}
    raw_stats: dict[str, dict] = {}
    if top_rows:
        raw_vals: dict[str, list[float]] = defaultdict(list)
        for r in top_rows:
            terms = r.get("terms") or {}
            for k in wk:
                t = terms.get(k)
                if not isinstance(t, (int, float)):
                    continue
                if pre_weighted:
                    w = float(weights.get(k, 0.0))
                    raw = float(t) / w if w != 0.0 else 0.0
                elif tolerances.get(k) is not None:
                    raw = float(t) * float(tolerances[k])
                else:
                    raw = float(t)
                raw_vals[k].append(raw)
        for k, vals in raw_vals.items():
            raw_stats[k] = {"median": float(np.median(vals)),
                            "p10": float(np.percentile(vals, 10)),
                            "p90": float(np.percentile(vals, 90))}
    return shares, raw_stats


def analyse_run(run_dir: Path) -> dict:
    run = load_run(Path(run_dir))
    meta = run["meta"]
    version = meta["objective_version"]
    valid = valid_rows(run["rows"])
    if version is None:
        version = max((int(r["objective_version"]) for r in valid
                       if isinstance(r.get("objective_version"), int)),
                      default=None)
    version_rows = [r for r in valid if r.get("objective_version") in (None, version)] \
        if version else valid
    weights, tolerances = _weights_and_tolerances(run["config"], version)
    # schema.md: the top decile is max(3, ceil(n_valid / 10)) rows of the >= 10 valid
    # rows; a run with < 10 valid rows has NO top decile at all (degrade, never fake).
    top = top_decile(version_rows)
    shares, raw_stats = _shares_and_raw(version_rows, version, weights, tolerances, top)
    shares = dict(sorted(shares.items(), key=lambda kv: -kv[1]["median"]))
    return {"run_dir": str(run["run_dir"]), "brief": meta["brief"],
            "objective_version": version, "family": meta["family"],
            "n_valid": len(version_rows), "n_top": len(top) if top else 0,
            "shares": shares, "top_decile_raw": raw_stats,
            "weights": {k: float(weights.get(k, 0.0)) for k in _weighted_keys(version)},
            "tolerances": {k: (float(tolerances[k]) if tolerances.get(k) is not None else None)
                           for k in _weighted_keys(version)}}


def _md(payload: dict) -> str:
    if "runs" in payload:  # multi-run wrapper: render one section per run
        return "\n\n".join(_md(r) for r in payload["runs"])
    v = payload["objective_version"]
    lines = ["# Term balance", "",
             f"Brief `{payload['brief']}` (objective v{v if v is not None else '?'}, "
             f"{payload['n_valid']} valid rows, {payload['n_top']} top-decile).", "",
             "Share of J per term (median / mean over valid rows):", "",
             "| term | share median | share mean | weight | tolerance |", "|---|---:|---:|---:|---:|"]
    for k, s in payload["shares"].items():
        tol = payload["tolerances"].get(k)
        lines.append(f"| `{k}` | {s['median']:.3f} | {s['mean']:.3f} | "
                     f"{payload['weights'].get(k, 0.0)} | "
                     + (f"{tol}" if tol is not None else "—"))
        lines[-1] += " |"
    lines += ["", "Raw-unit values of the top-decile designs (recalibration inputs):", "",
              "| term | median | p10 | p90 |", "|---|---:|---:|---:|"]
    for k, s in (payload["top_decile_raw"] or {}).items():
        lines.append(f"| `{k}` | {s['median']:.4g} | {s['p10']:.4g} | {s['p90']:.4g} |")
    lines.append("")
    return "\n".join(lines)


def charts(payload: dict) -> dict:
    """Chart factory for main() and report_day.py: median share of J per term."""
    def fn(plt):
        shares = payload.get("shares") or {}
        if not shares:
            return None
        fig, ax = plt.subplots(figsize=(7, 4))
        keys = list(shares)
        ax.bar(keys, [shares[k]["median"] for k in keys])
        ax.set_ylabel("median share of J")
        v = payload.get("objective_version")
        ax.set_title(f"term balance — {payload['brief']} (v{v if v is not None else '?'})")
        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()
        return fig
    return {"term_balance.png": fn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--run", action="append", required=True, help="run dir (repeatable)")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    payloads = []
    for d in args.run:
        try:
            payloads.append(analyse_run(Path(d)))
        except (FileNotFoundError, ValueError) as exc:
            raise fail(f"term_balance: {exc}") from exc
    if len(payloads) == 1:
        payload = payloads[0]          # single run = the flat schema.md shape
    else:
        payload = {"brief": payloads[0]["brief"],
                   "objective_version": payloads[0]["objective_version"],
                   "runs": payloads}

    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"term_balance OK: {len(payloads)} run(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
