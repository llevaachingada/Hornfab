"""A.6 ab_compare.py — equal-budget A/B of two search configurations.

Usage:
    PY tools\\analysis\\ab_compare.py --a <dir>[,<dir>...] --b <dir>[,<dir>...]
        [--label-a <name>] [--label-b <name>] --out <dir>

Best-so-far J at matched counts of new valid evaluations (median of each side's runs),
final medians and spreads, and the 2026-10-23 verdict rule ("A beats B only when medians
differ by more than both spreads"; >= 5 runs per side prints a verdict, 3-4 "indicative",
fewer "no-verdict"). J values are only comparable when both sides share the objective
version and family: a mismatch is a hard error (exit 2). Used for narrow-vs-control and
staged-vs-joint. Schema: ``tools/analysis/schema.md`` § ab_compare.json.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from _common import (add_out_arg, best_so_far_curve, beats_rule, fail, load_run, write_report)

TOOL = "ab_compare"


def load_side(dirs: list[Path]) -> list[dict]:
    return [load_run(Path(d)) for d in dirs]


def analyse(a_dirs: list[Path], b_dirs: list[Path],
            label_a: str | None = None, label_b: str | None = None) -> dict:
    side_a, side_b = load_side(a_dirs), load_side(b_dirs)
    for side, label in ((side_a, "a"), (side_b, "b")):
        versions = {r["meta"]["objective_version"] for r in side}
        fams = {r["meta"]["family"] for r in side}
        if len(versions) > 1 or len(fams) > 1:
            raise fail(f"ab_compare: side {label} mixes objective versions {sorted(map(str, versions))} "
                       f"or families {sorted(map(str, fams))}")
    if {r["meta"]["objective_version"] for r in side_a} != {r["meta"]["objective_version"] for r in side_b} \
            or {r["meta"]["family"] for r in side_a} != {r["meta"]["family"] for r in side_b}:
        raise fail("ab_compare: the compared sides differ in objective version or family; "
                   "J is never ranked across versions")
    curves_a = [best_so_far_curve(r) for r in side_a]
    curves_b = [best_so_far_curve(r) for r in side_b]
    n_match = min([len(c) for c in curves_a + curves_b] or [0])
    equal_budget = []
    for n in range(1, n_match + 1):
        a = float(np.median([c[n - 1]["best"] for c in curves_a if len(c) >= n]))
        b = float(np.median([c[n - 1]["best"] for c in curves_b if len(c) >= n]))
        equal_budget.append({"n": n, "best_a": a, "best_b": b})
    # downsample the report to ~20 points so the JSON stays readable
    if len(equal_budget) > 20:
        step = max(1, -(-len(equal_budget) // 20))  # ceil(len / 20)
        sampled = equal_budget[::step]
        if sampled[-1] is not equal_budget[-1]:
            sampled.append(equal_budget[-1])
        equal_budget = sampled
    finals_a = [c[-1]["best"] for c in curves_a if c]
    finals_b = [c[-1]["best"] for c in curves_b if c]
    med_a = float(np.median(finals_a)) if finals_a else None
    med_b = float(np.median(finals_b)) if finals_b else None
    spr_a = float(max(finals_a) - min(finals_a)) if len(finals_a) >= 2 else 0.0
    spr_b = float(max(finals_b) - min(finals_b)) if len(finals_b) >= 2 else 0.0
    verdict = None
    if med_a is not None and med_b is not None:
        n_runs = min(len(side_a), len(side_b))
        if med_a != med_b and n_runs < 3:
            verdict = {"rule_holds": abs(med_a - med_b) > max(spr_a, spr_b),
                       "n_runs_per_side": n_runs,
                       "verdict": "no-verdict",
                       "note": f"{n_runs} run(s) per side: below the 3-run 'indicative' floor"}
        else:
            verdict = {"rule_holds": abs(med_a - med_b) > max(spr_a, spr_b),
                       "n_runs_per_side": n_runs,
                       "verdict": beats_rule(med_a, spr_a, med_b, spr_b, n_runs)}
    return {"label_a": label_a or "a", "label_b": label_b or "b",
            "sides": {"a": {"runs": [str(Path(d)) for d in a_dirs],
                            "n_runs": len(side_a), "n_new_valid_max": max([len(c) for c in curves_a] or [0])},
                      "b": {"runs": [str(Path(d)) for d in b_dirs],
                            "n_runs": len(side_b), "n_new_valid_max": max([len(c) for c in curves_b] or [0])}},
            "equal_budget": equal_budget,
            "final": {"median_a": med_a, "median_b": med_b, "spread_a": spr_a, "spread_b": spr_b},
            "verdict": verdict,
            "seed_rule": "A beats B only when medians differ by more than both spreads"}


def _md(payload: dict) -> str:
    lines = ["# A/B comparison (equal budget of new valid evaluations)", "",
             f"**{payload['label_a']}**: {payload['sides']['a']['n_runs']} run(s); "
             f"**{payload['label_b']}**: {payload['sides']['b']['n_runs']} run(s).", "",
             "| new valid evals | "
             f"{payload['label_a']} (median J) | {payload['label_b']} (median J) |",
             "|---:|---:|---:|"]
    for p in payload["equal_budget"]:
        lines.append(f"| {p['n']} | {p['best_a']:.4g} | {p['best_b']:.4g} |")
    f = payload["final"]
    v = payload["verdict"]
    lines += ["", f"Final: median {f['median_a']} vs {f['median_b']}; spreads "
              f"{f['spread_a']} vs {f['spread_b']}."]
    if v:
        lines.append(f"Verdict: **{v['verdict']}** (rule holds: {v['rule_holds']}; "
                     f"{v['n_runs_per_side']} run(s) per side).")
    lines.append(f"_Rule: {payload['seed_rule']}._")
    return "\n".join(lines)


def charts(payload: dict) -> dict:
    """PNG charts for this report (used by main() and by report_day)."""
    def fn(plt):
        eq = payload["equal_budget"]
        if not eq:
            return None
        fig, ax = plt.subplots(figsize=(6.5, 4))
        ax.plot([p["n"] for p in eq], [p["best_a"] for p in eq], label=payload["label_a"])
        ax.plot([p["n"] for p in eq], [p["best_b"] for p in eq], label=payload["label_b"])
        ax.set_xlabel("new valid evaluations (equal budget)")
        ax.set_ylabel("best-so-far J (median of the side's runs)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig
    return {"ab_compare.png": fn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--a", required=True, help="run dir(s) for side A, comma separated")
    ap.add_argument("--b", required=True, help="run dir(s) for side B, comma separated")
    ap.add_argument("--label-a", default=None)
    ap.add_argument("--label-b", default=None)
    add_out_arg(ap)
    args = ap.parse_args(argv)
    a_dirs = [Path(p) for p in args.a.split(",") if p.strip()]
    b_dirs = [Path(p) for p in args.b.split(",") if p.strip()]
    if not a_dirs or not b_dirs:
        raise fail("ab_compare: --a and --b need at least one run dir each")
    payload = analyse(a_dirs, b_dirs, args.label_a, args.label_b)

    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"ab_compare OK: {payload['sides']['a']['n_runs']} vs "
          f"{payload['sides']['b']['n_runs']} run(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
