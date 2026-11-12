"""A.6 ab_compare.py - equal-budget, fixed-cost and paired A/B of two treatments.

Usage:
    PY tools\\analysis\\ab_compare.py --a <dir>[,<dir>...] --b <dir>[,<dir>...]
        [--label-a <name>] [--label-b <name>]
        [--pair name=<dirA>|<dirB> ...] [--target-j J] [--budget N]
        [--cost-budget S] [--practical-delta D] --out <dir>

Descriptive views (equal new-valid-eval budget medians, final medians/spreads and
fixed accumulated-attempt-cost medians) are always reported.  Prospective paired
inference is reported only for predeclared ``--pair`` entries: paired differences
``d = A - B`` with bootstrap CIs, sign counts, censoring and a pilot sample-size
plan.  The old median-versus-spread rule is retained only as
``legacy_median_rule`` (a descriptive label, not the decision).  J is only
comparable when both sides share objective version, brief and family; that
mismatch remains a hard error (exit 2).  Schema:
``tools/analysis/schema.md`` § ab_compare.json.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

from _common import (add_out_arg, best_so_far_curve, beats_rule, compare_compatibility,
                     cost_ledger, cost_model_eligibility, ecdf_time_to_target,
                     expected_runtime, fail, load_run, paired_summary, power_planning,
                     read_json, replicate_summary, sum_cost_ledgers, time_to_target,
                     value_at_budget, write_report)

TOOL = "ab_compare"


def load_side(dirs: list[Path]) -> list[dict]:
    return [load_run(Path(d)) for d in dirs]


def _curve(run: dict) -> list[dict]:
    return best_so_far_curve(run, include_failed_seconds=True)


def _cost_curve(run: dict) -> list[dict]:
    return [{"n": p["n"], "best": p["best"], "cost_s": p["wall_s"]} for p in _curve(run)]


def _ledger(run: dict) -> dict:
    rj = read_json(Path(run["run_dir"]) / "run.json") or {}
    return cost_ledger(run["rows"], stats=rj.get("stats"),
                       started_utc=rj.get("started_utc"),
                       finished_utc=rj.get("finished_utc"))


def _outcome_counts(runs: list[dict], curves: list[list[dict]]) -> dict:
    statuses = [(read_json(Path(r["run_dir"]) / "run.json") or {}).get("status")
                for r in runs]
    return {
        "n_runs": len(runs),
        "finished": sum(1 for s in statuses if s == "finished"),
        "interrupted_or_unknown": sum(1 for s in statuses if s not in ("finished",)),
        "with_valid_eval": sum(1 for c in curves if c),
        "all_failure": sum(1 for c in curves if not c),
    }


def _verdict_label(decision: str | None, direction: str | None) -> str:
    if decision == "a_better":
        return "a-beats-b"
    if decision == "b_better":
        return "b-beats-a"
    if decision == "pilot_only":
        return "indicative" if direction else "no-verdict"
    return "no-verdict"


def _pair_record(name: str, run_a: dict, run_b: dict, *, target_j: float | None,
                 budget: int | None, cost_budget: float | None) -> dict:
    curve_a, curve_b = _curve(run_a), _curve(run_b)
    cost_a, cost_b = _cost_curve(run_a), _cost_curve(run_b)
    best_a = curve_a[-1]["best"] if curve_a else None
    best_b = curve_b[-1]["best"] if curve_b else None
    last_evals = [c[-1]["n"] for c in (curve_a, curve_b) if c]
    last_costs = [c[-1]["wall_s"] for c in (curve_a, curve_b) if c]
    eval_budget = budget if budget is not None else (min(last_evals) if last_evals else 0)
    cost_cap = cost_budget if cost_budget is not None else (min(last_costs) if last_costs else 0.0)
    va = value_at_budget(curve_a, eval_budget, "n")
    vb = value_at_budget(curve_b, eval_budget, "n")
    ca = value_at_budget(cost_a, cost_cap, "cost_s")
    cb = value_at_budget(cost_b, cost_cap, "cost_s")
    seed_a = (run_a.get("meta") or {}).get("cma_seed")
    seed_b = (run_b.get("meta") or {}).get("cma_seed")
    rec: dict[str, Any] = {
        "pair": name,
        "a": str(Path(run_a["run_dir"])),
        "b": str(Path(run_b["run_dir"])),
        "seed_a": seed_a,
        "seed_b": seed_b,
        "shared_cma_seed": seed_a == seed_b,
        "shared_seed_warning": ("same RNG seed is not proof of shared candidates; "
                                "pairing is valid only because it was predeclared"),
        "compatibility": compare_compatibility([run_a, run_b]),
        "final": {
            "a_best_j": best_a, "b_best_j": best_b,
            "difference": (best_a - best_b) if (best_a is not None and best_b is not None) else None,
        },
        "fixed_eval_budget": {
            "budget": eval_budget,
            "budget_basis": "declared" if budget is not None else "min_observed",
            "a": va, "b": vb,
            "difference": ((va["value"] - vb["value"])
                           if (va["value"] is not None and vb["value"] is not None) else None),
            "complete_pair": (va["observed"] and vb["observed"]
                              and not va["censored"] and not vb["censored"]),
        },
        "fixed_cost_budget": {
            "budget_s": cost_cap,
            "budget_basis": "declared" if cost_budget is not None else "min_observed",
            "a": ca, "b": cb,
            "difference": ((ca["value"] - cb["value"])
                           if (ca["value"] is not None and cb["value"] is not None) else None),
            "complete_pair": (ca["observed"] and cb["observed"]
                              and not ca["censored"] and not cb["censored"]),
        },
    }
    if target_j is not None:
        ta = time_to_target(curve_a, target_j, "n", budget)
        tb = time_to_target(curve_b, target_j, "n", budget)
        tca = time_to_target(cost_a, target_j, "cost_s", cost_budget)
        tcb = time_to_target(cost_b, target_j, "cost_s", cost_budget)
        rec["time_to_target"] = {
            "target_j": float(target_j),
            "evals": {"a": ta, "b": tb},
            "cost_s": {"a": tca, "b": tcb},
            "difference_evals": ((ta["value"] - tb["value"])
                                 if (ta.get("reached") and tb.get("reached")) else None),
            "difference_cost_s": ((tca["value"] - tcb["value"])
                                  if (tca.get("reached") and tcb.get("reached")) else None),
        }
    return rec


def analyse(a_dirs: list[Path], b_dirs: list[Path],
            label_a: str | None = None, label_b: str | None = None, *,
            pairs: list[tuple[str, Path, Path]] | None = None,
            target_j: float | None = None, budget: int | None = None,
            cost_budget: float | None = None,
            practical_delta: float | None = None,
            alpha: float = 0.05, power: float = 0.8) -> dict:
    side_a, side_b = load_side(a_dirs), load_side(b_dirs)
    for side, label in ((side_a, "a"), (side_b, "b")):
        versions = {r["meta"]["objective_version"] for r in side}
        fams = {r["meta"]["family"] for r in side}
        briefs = {str(r["meta"]["brief"]) for r in side}
        if len(versions) > 1 or len(fams) > 1 or len(briefs) > 1:
            raise fail(f"ab_compare: side {label} mixes objective versions "
                       f"{sorted(map(str, versions))}, briefs {sorted(briefs)} or "
                       f"families {sorted(map(str, fams))}")
    if {r["meta"]["objective_version"] for r in side_a} != {r["meta"]["objective_version"] for r in side_b} \
            or {r["meta"]["family"] for r in side_a} != {r["meta"]["family"] for r in side_b} \
            or {str(r["meta"]["brief"]) for r in side_a} != {str(r["meta"]["brief"]) for r in side_b}:
        raise fail("ab_compare: the compared sides differ in objective version, brief or family; "
                   "J is never ranked across versions")
    curves_a = [_curve(r) for r in side_a]
    curves_b = [_curve(r) for r in side_b]
    n_match = min([len(c) for c in curves_a + curves_b] or [0])
    equal_budget = []
    for n in range(1, n_match + 1):
        obs_a = [c[n - 1]["best"] for c in curves_a if len(c) >= n]
        obs_b = [c[n - 1]["best"] for c in curves_b if len(c) >= n]
        a = float(np.median(obs_a)) if obs_a else None
        b = float(np.median(obs_b)) if obs_b else None
        equal_budget.append({"n": n, "best_a": a, "best_b": b,
                             "n_observed_a": len(obs_a), "n_observed_b": len(obs_b),
                             "n_censored_a": len(curves_a) - len(obs_a),
                             "n_censored_b": len(curves_b) - len(obs_b)})
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
    legacy = None
    if med_a is not None and med_b is not None:
        n_runs = min(len(side_a), len(side_b))
        legacy = {"rule_holds": abs(med_a - med_b) > max(spr_a, spr_b),
                  "n_runs_per_side": n_runs,
                  "verdict": (beats_rule(med_a, spr_a, med_b, spr_b, n_runs)
                              if n_runs >= 3 else "no-verdict"),
                  "note": "historical median-vs-spread label; not the pairing decision"}
    # fixed accumulated-attempt cost medians (descriptive)
    cost_curves_a = [_cost_curve(r) for r in side_a]
    cost_curves_b = [_cost_curve(r) for r in side_b]
    last_costs = [c[-1]["cost_s"] for c in cost_curves_a + cost_curves_b if c]
    cost_cap = cost_budget if cost_budget is not None else (min(last_costs) if last_costs else 0.0)
    va = [value_at_budget(c, cost_cap, "cost_s") for c in cost_curves_a]
    vb = [value_at_budget(c, cost_cap, "cost_s") for c in cost_curves_b]
    fixed_cost = {
        "budget_s": cost_cap,
        "budget_basis": "declared" if cost_budget is not None else "min_observed",
        "median_a": float(np.median([v["value"] for v in va if v["value"] is not None]))
        if any(v["value"] is not None for v in va) else None,
        "median_b": float(np.median([v["value"] for v in vb if v["value"] is not None]))
        if any(v["value"] is not None for v in vb) else None,
        "n_observed_a": sum(1 for v in va if v["observed"]),
        "n_observed_b": sum(1 for v in vb if v["observed"]),
        "n_censored_a": sum(1 for v in va if v["censored"]),
        "n_censored_b": sum(1 for v in vb if v["censored"]),
    }
    fixed_target = None
    if target_j is not None:
        fixed_target = {
            "target_j": float(target_j),
            "a": {
                "ecdf_evals": ecdf_time_to_target(curves_a, target_j, "n", budget),
                "ecdf_cost_s": ecdf_time_to_target(cost_curves_a, target_j, "cost_s", cost_budget),
                "ert_evals": expected_runtime(curves_a, target_j, "n", budget),
                "ert_cost_s": expected_runtime(cost_curves_a, target_j, "cost_s", cost_budget),
            },
            "b": {
                "ecdf_evals": ecdf_time_to_target(curves_b, target_j, "n", budget),
                "ecdf_cost_s": ecdf_time_to_target(cost_curves_b, target_j, "cost_s", cost_budget),
                "ert_evals": expected_runtime(curves_b, target_j, "n", budget),
                "ert_cost_s": expected_runtime(cost_curves_b, target_j, "cost_s", cost_budget),
            },
        }
    # predeclared pairs only — never inferred from equal seed numbers
    index_a = {Path(r["run_dir"]).resolve(): r for r in side_a}
    index_b = {Path(r["run_dir"]).resolve(): r for r in side_b}
    pair_records: list[dict] = []
    for name, da, db in (pairs or []):
        ra = index_a.get(Path(da).resolve())
        rb = index_b.get(Path(db).resolve())
        if ra is None or rb is None:
            raise fail(f"ab_compare: pair {name!r} must reference one --a run and one --b run")
        pair_records.append(_pair_record(name, ra, rb, target_j=target_j, budget=budget,
                                         cost_budget=cost_budget))
    final_diffs = [p["final"]["difference"] for p in pair_records
                   if p["final"]["difference"] is not None]
    budget_diffs = [p["fixed_eval_budget"]["difference"] for p in pair_records
                    if p["fixed_eval_budget"]["complete_pair"]
                    and p["fixed_eval_budget"]["difference"] is not None]
    cost_diffs = [p["fixed_cost_budget"]["difference"] for p in pair_records
                  if p["fixed_cost_budget"]["complete_pair"]
                  and p["fixed_cost_budget"]["difference"] is not None]
    preferred = budget_diffs if budget_diffs else final_diffs
    overall_compat = compare_compatibility(side_a + side_b)
    pair_compat = all(p["compatibility"]["compatible_for_inference"] for p in pair_records)
    compatibility_blocked = (not overall_compat["compatible_for_inference"]
                             or (bool(pair_records) and not pair_compat))
    summary = paired_summary(preferred, practical_delta) if pair_records else None
    power_plan = power_planning(preferred, practical_delta, alpha, power) if pair_records else None
    if compatibility_blocked:
        verdict = {
            "verdict": "no-verdict",
            "rule_holds": False,
            "n_runs_per_side": len(pair_records) or min(len(side_a), len(side_b)),
            "decision": "incompatible",
            "ci95_bootstrap_mean": (summary or {}).get("ci95_bootstrap_mean"),
            "practical_delta": practical_delta,
            "pilot": True,
            "evidence_class": "blocked",
            "note": "Grid/fidelity/backend/target/software compatibility blocks pooled "
                    "prospective inference: " + ", ".join(overall_compat["blocking"]),
        }
    elif summary is not None:
        decision = summary.get("decision")
        verdict = {
            "verdict": _verdict_label(decision, summary.get("direction")),
            "rule_holds": decision in ("a_better", "b_better"),
            "n_runs_per_side": len(pair_records),
            "decision": decision,
            "ci95_bootstrap_mean": summary.get("ci95_bootstrap_mean"),
            "practical_delta": practical_delta,
            "pilot": summary.get("pilot"),
            "evidence_class": summary.get("evidence_class"),
            "note": summary.get("note"),
        }
    else:
        verdict = {
            "verdict": "no-verdict",
            "rule_holds": False,
            "n_runs_per_side": min(len(side_a), len(side_b)),
            "decision": "descriptive_only",
            "ci95_bootstrap_mean": None,
            "practical_delta": practical_delta,
            "pilot": True,
            "note": "No predeclared --pair; no prospective paired inference. "
                    "legacy_median_rule is descriptive only.",
        }
    combined_cost = sum_cost_ledgers([_ledger(r) for r in side_a + side_b])
    compat = compare_compatibility(side_a + side_b)
    return {
        "label_a": label_a or "a",
        "label_b": label_b or "b",
        "sides": {
            "a": {"runs": [str(Path(d)) for d in a_dirs], "n_runs": len(side_a),
                  "n_new_valid_max": max([len(c) for c in curves_a] or [0]),
                  "cost": sum_cost_ledgers([_ledger(r) for r in side_a]),
                  "replicates": replicate_summary(side_a),
                  "outcomes": _outcome_counts(side_a, curves_a)},
            "b": {"runs": [str(Path(d)) for d in b_dirs], "n_runs": len(side_b),
                  "n_new_valid_max": max([len(c) for c in curves_b] or [0]),
                  "cost": sum_cost_ledgers([_ledger(r) for r in side_b]),
                  "replicates": replicate_summary(side_b),
                  "outcomes": _outcome_counts(side_b, curves_b)},
        },
        "compatibility": compat,
        "cost_totals": combined_cost,
        "cost_model": cost_model_eligibility(combined_cost, compat),
        "equal_budget": equal_budget,
        "fixed_cost": fixed_cost,
        "fixed_target": fixed_target,
        "final": {"median_a": med_a, "median_b": med_b, "spread_a": spr_a, "spread_b": spr_b},
        "verdict": verdict,
        "legacy_median_rule": legacy,
        "paired": {
            "pairing_declared": bool(pair_records),
            "compatibility_blocked": compatibility_blocked,
            "pairs": pair_records,
            "summaries": {
                "final_best": paired_summary(final_diffs, practical_delta) if final_diffs else None,
                "fixed_eval_budget": paired_summary(budget_diffs, practical_delta) if budget_diffs else None,
                "fixed_cost_budget": paired_summary(cost_diffs, practical_delta) if cost_diffs else None,
                "preferred_basis": ("fixed_eval_budget" if budget_diffs else
                                    ("final_best" if final_diffs else None)),
                "summary": summary,
            },
            "power": power_plan,
            "note": ("No pairing was predeclared; descriptive views only."
                     if not pair_records else
                     "Paired inference over predeclared pairs; five pairs is a pilot."),
        },
        "seed_rule": "Legacy descriptive label only: A beats B when medians differ by "
                     "more than both spreads; not the decision.",
    }


def _md(payload: dict) -> str:
    lines = ["# A/B comparison", "",
             f"**{payload['label_a']}**: {payload['sides']['a']['n_runs']} run(s); "
             f"**{payload['label_b']}**: {payload['sides']['b']['n_runs']} run(s).", "",
             "Descriptive equal-budget view (median of each side's runs; censoring shown):",
             "",
             "| new valid evals | "
             f"{payload['label_a']} (median J) | {payload['label_b']} (median J) | "
             "observed A/B | censored A/B |",
             "|---:|---:|---:|---:|---:|"]
    for p in payload["equal_budget"]:
        lines.append(f"| {p['n']} | {p['best_a']:.4g} | {p['best_b']:.4g} | "
                     f"{p['n_observed_a']}/{p['n_observed_b']} | "
                     f"{p['n_censored_a']}/{p['n_censored_b']} |")
    f = payload["final"]
    fc = payload["fixed_cost"]
    lines += ["", f"Final: median {f['median_a']} vs {f['median_b']}; spreads "
                  f"{f['spread_a']} vs {f['spread_b']}.",
              f"Fixed accumulated-attempt cost at {fc['budget_s']} s: median "
              f"{fc['median_a']} vs {fc['median_b']} "
              f"(observed {fc['n_observed_a']}/{fc['n_observed_b']}, "
              f"censored {fc['n_censored_a']}/{fc['n_censored_b']})."]
    ft = payload.get("fixed_target")
    if ft:
        ea = ft["a"]["ecdf_evals"]
        eb = ft["b"]["ecdf_evals"]
        lines.append(f"Fixed target J <= {ft['target_j']}: A reached "
                     f"{ea['n_reached']}/{ea['n_runs']} (ERT {ft['a']['ert_evals']['ert']} evals), "
                     f"B reached {eb['n_reached']}/{eb['n_runs']} "
                     f"(ERT {ft['b']['ert_evals']['ert']} evals); ERT is a lower bound.")
    lines.append("")
    v = payload["verdict"]
    lines += [f"Decision: **{v['verdict']}** ({v.get('decision')}; "
              f"{v['n_runs_per_side']} pair(s)/side)."]
    if payload["legacy_median_rule"]:
        lm = payload["legacy_median_rule"]
        lines += [f"_Legacy descriptive label: {lm['verdict']} "
                  f"(rule holds: {lm['rule_holds']}). Not the decision._", ""]
    p = payload["paired"]
    if not p["pairing_declared"]:
        lines += ["No pairing was predeclared; prospective paired inference is unavailable.", ""]
        return "\n".join(lines)
    for rec in p["pairs"]:
        lines += [f"### {rec['pair']}", "",
                  f"- d_final = A - B = {rec['final']['difference']}",
                  f"- fixed-eval-budget d = {rec['fixed_eval_budget']['difference']} "
                  f"(complete pair: {rec['fixed_eval_budget']['complete_pair']})",
                  f"- fixed-cost d = {rec['fixed_cost_budget']['difference']} "
                  f"(complete pair: {rec['fixed_cost_budget']['complete_pair']})",
                  f"- shared CMA seed: {rec['shared_cma_seed']} — {rec['shared_seed_warning']}", ""]
    s = p["summaries"]["summary"]
    if s:
        lines += ["| n pairs | mean d | median d | 95% CI mean | signs (A/B/tie) | decision |",
                  "|---:|---:|---:|---|---|---|",
                  f"| {s['n_pairs']} | {s.get('mean')} | {s.get('median')} | "
                  f"{s.get('ci95_bootstrap_mean')} | "
                  f"{s['signs']['a_better']}/{s['signs']['b_better']}/{s['signs']['ties']} | "
                  f"**{s['decision']}** |", "", f"_{s['note']}_", ""]
    pw = p.get("power")
    if pw:
        lines += [f"Power/sample-size plan: {pw.get('status')} — "
                  f"{pw.get('n_pairs_required')} pairs for practical delta "
                  f"{pw.get('practical_delta')} ({pw.get('method')}).", ""]
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


def parse_pair(spec: str) -> tuple[str, Path, Path]:
    if "=" not in spec or "|" not in spec:
        raise fail("ab_compare: --pair expects name=<dirA>|<dirB>")
    name, _, rest = spec.partition("=")
    a, _, b = rest.partition("|")
    if not name.strip() or not a.strip() or not b.strip():
        raise fail("ab_compare: --pair expects name=<dirA>|<dirB>")
    return name.strip(), Path(a.strip()), Path(b.strip())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--a", required=True, help="run dir(s) for side A, comma separated")
    ap.add_argument("--b", required=True, help="run dir(s) for side B, comma separated")
    ap.add_argument("--label-a", default=None)
    ap.add_argument("--label-b", default=None)
    ap.add_argument("--pair", action="append", default=None,
                    help="<name>=<dirA>|<dirB> predeclared A/B replicate pairing")
    ap.add_argument("--target-j", type=float, default=None,
                    help="fixed physical target J for time-to-target reporting")
    ap.add_argument("--budget", type=int, default=None, help="fixed new-valid-eval budget")
    ap.add_argument("--cost-budget", type=float, default=None,
                    help="fixed accumulated-attempt cost budget in seconds")
    ap.add_argument("--practical-delta", type=float, default=None,
                    help="practical improvement threshold in J for decisions/power")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    add_out_arg(ap)
    args = ap.parse_args(argv)
    a_dirs = [Path(p) for p in args.a.split(",") if p.strip()]
    b_dirs = [Path(p) for p in args.b.split(",") if p.strip()]
    if not a_dirs or not b_dirs:
        raise fail("ab_compare: --a and --b need at least one run dir each")
    pairs = [parse_pair(s) for s in (args.pair or [])]
    payload = analyse(a_dirs, b_dirs, args.label_a, args.label_b, pairs=pairs,
                      target_j=args.target_j, budget=args.budget,
                      cost_budget=args.cost_budget,
                      practical_delta=args.practical_delta,
                      alpha=args.alpha, power=args.power)
    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"ab_compare OK: {payload['sides']['a']['n_runs']} vs "
          f"{payload['sides']['b']['n_runs']} run(s), {len(pairs)} pair(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
