"""A.1 convergence.py — best-so-far J vs valid-evaluation index for search runs.

Usage:  PY tools\\analysis\\convergence.py --run <dir> [--run <dir> ...] --out <dir>

Writes ``convergence.json`` + ``convergence.md`` + one chart per run. Schema:
``tools/analysis/schema.md`` § convergence.json. Cached rows count as replays, not new
evals; the X axis is the count of *new valid* evaluations in row order.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from _common import (add_out_arg, best_so_far_curve, evals_to_within, fail,
                     last20_improvement, load_run, new_rows, refusal_windows,
                     run_meta, valid_rows, write_report)

TOOL = "convergence"


def analyse_run(run_dir: Path) -> dict:
    run = load_run(Path(run_dir))
    rows = run["rows"]
    meta = run["meta"]
    curve = best_so_far_curve(run)
    final_best = curve[-1]["best"] if curve else None
    nv = len(valid_rows(rows))
    n_new = len(new_rows(rows))
    e1 = evals_to_within(curve, final_best, 0.01) if final_best is not None else None
    e5 = evals_to_within(curve, final_best, 0.05) if final_best is not None else None
    flag, imp = last20_improvement(curve)
    refusals: dict[str, int] = {}
    for r in new_rows(rows):
        if r.get("ok") is not True:
            kind = str(r.get("kind") or r.get("error") or "unknown")
            refusals[kind] = refusals.get(kind, 0) + 1
    return {
        "run_dir": str(run["run_dir"]), "brief": meta["brief"], "family": meta["family"],
        "objective_version": meta["objective_version"], "mode": meta["mode"],
        "n_rows": len(rows), "n_valid": nv, "n_cached": len(rows) - n_new, "n_new_valid": len(curve),
        "refusals": refusals,
        "final_best": final_best,
        "curve": [{"n": p["n"], "best": p["best"], "wall_s": p["wall_s"]} for p in curve],
        "evals_to_1pct": e1, "evals_to_5pct": e5,
        "last20_improvement": flag, "last20_improvement_pct": imp,
        "refusal_rate_by_kind": refusal_windows(rows),
    }


def _md(payload: dict) -> str:
    lines = ["# Convergence", "", "Best-so-far J over new **valid** evaluations "
             "(cached replays are not new evals).", ""]
    for r in payload["runs"]:
        lines += [
            f"## `{Path(r['run_dir']).name}`",
            "",
            f"- brief `{r['brief']}` (family `{r['family']}`;"
            f" objective v{r['objective_version']}, mode `{r['mode']}`)",
            f"- rows: {r['n_rows']} ({r['n_valid']} valid, {r['n_cached']} cached replays,"
            f" {r['n_new_valid']} new valid)",
            f"- final best J: **{r['final_best']}**",
            f"- evals to within 1% of final best: {r['evals_to_1pct']};"
            f" within 5%: {r['evals_to_5pct']}",
            f"- still improving in the last 20%: **{r['last20_improvement']}**"
            + (f" ({r['last20_improvement_pct']:.2f}% of final best)" if r["last20_improvement_pct"] is not None else ""),
            "",
            "| window | refusal rate | kinds |",
            "|---|---:|---|",
        ]
        for w in r["refusal_rate_by_kind"]:
            kinds = ", ".join(f"{k}×{v}" for k, v in sorted(w["kinds"].items())) or "—"
            lines.append(f"| {w['w'][0]}–{w['w'][1]} | {w['rate']:.2f} | {kinds} |")
        lines.append("")
    return "\n".join(lines)


def _chart(r: dict):
    def fn(plt):
        curve = r["curve"]
        if not curve:
            return None
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([p["n"] for p in curve], [p["best"] for p in curve], lw=1.5)
        ax.set_xlabel("new valid evaluations")
        ax.set_ylabel("best-so-far J")
        ax.set_title(Path(r["run_dir"]).name)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig
    return fn


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--run", action="append", required=True,
                    help="run dir (repeatable): reads <dir>/search.ndjson read-only")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    runs = []
    for d in args.run:
        try:
            runs.append(analyse_run(Path(d)))
        except (FileNotFoundError, ValueError) as exc:
            raise fail(f"convergence: {exc}") from exc
    payload = runs_payload(runs)
    charts = {f"convergence_{i + 1}.png": _chart(r) for i, r in enumerate(runs) if r["curve"]}
    write_report(Path(args.out), TOOL, payload, _md(payload), charts)  # type: ignore[arg-type]
    print(f"convergence OK: {len(runs)} run(s) -> {args.out}")
    return 0


def runs_payload(runs: list[dict]) -> dict:
    return {"runs": runs}


if __name__ == "__main__":
    raise SystemExit(main())

