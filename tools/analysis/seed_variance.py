"""A.2 seed_variance.py - seed noise and honest paired comparisons for search runs.

Usage:
    PY tools\\analysis\\seed_variance.py --group name=<dir>,<dir>,... [--group ...]
        [--pair name=<dirA>|<dirB> ...] [--target-j J] [--budget N]
        [--cost-budget S] [--practical-delta D] --out <dir>

Two views, kept separate:

* ``descriptive_historical`` — per-seed best J, median/spread, bootstrap CI of
  the median, normalised best-design distances and (optionally) a fixed-target
  ECDF/ERT.  This is a description of the observed runs, not an inference.
* ``prospective`` — only when a pairing is **predeclared** with ``--pair``.
  Reports paired differences ``d = A - B`` with bootstrap CIs, sign counts,
  fixed-eval-budget and fixed-cost estimates with censoring, target/ERT, and a
  sample-size plan from the pilot paired differences.  Five pairs is a pilot;
  matching CMA seeds alone is not proof of shared candidates.

The legacy 2026-10-23 median-vs-spread rule is retained only as a descriptive
label (``legacy_median_rule``); it is not the decision.  Schema:
``tools/analysis/schema.md`` § seed_variance.json.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import numpy as np

from _common import (add_out_arg, best_so_far_curve, bootstrap_ci, cost_ledger,
                     compare_compatibility, cost_model_eligibility, ecdf_time_to_target,
                     evals_to_within, expected_runtime, fail, load_run, paired_summary,
                     params_flat, power_planning, read_json, replicate_summary,
                     sum_cost_ledgers, time_to_target, valid_rows, value_at_budget,
                     write_report)

TOOL = "seed_variance"
TARGET_RELS = (0.01, 0.05)


def _run_json(run: dict) -> dict:
    return read_json(Path(run["run_dir"]) / "run.json") or {}


def _ledger(run: dict) -> dict:
    rj = _run_json(run)
    return cost_ledger(run["rows"], stats=rj.get("stats"),
                       started_utc=rj.get("started_utc"),
                       finished_utc=rj.get("finished_utc"))


def _sum_ledgers(ledgers: list[dict]) -> dict:
    """Aggregate the count/seconds fields of several ledgers (sums, not rates)."""
    return sum_cost_ledgers(ledgers)


def _provenance(runs: list[dict]) -> set[tuple]:
    """{(objective_version, brief, family)} of every run."""
    out = set()
    for r in runs:
        m = r["meta"]
        out.add((m["objective_version"], str(m["brief"]), str(m["family"])))
    return out


def _legacy_ecdf(runs: list[dict], group_target: float | None, rel: float):
    """Historical COCO-style ECDF relative to the group's own best (descriptive only)."""
    if group_target is None or not math.isfinite(group_target):
        return None
    thresh = group_target * (1.0 + rel)
    curves = [best_so_far_curve(r) for r in runs]
    if not curves:
        return None
    n_max = max(len(c) for c in curves)
    xs: list[int] = []
    reached: list[float] = []
    for n in range(1, n_max + 1):
        n_hit = sum(1 for c in curves if n <= len(c) and c[n - 1]["best"] <= thresh)
        xs.append(n)
        reached.append(n_hit / len(curves))
    pts, prev = [], 0.0
    for x, r in zip(xs, reached):
        if r != prev:
            pts.append([float(x), float(r)])
            prev = r
    if xs and (not pts or pts[-1] != [float(xs[-1]), float(reached[-1])]):
        pts.append([float(xs[-1]), float(reached[-1])])
    return pts


def _seed_distances(runs: list[dict]) -> dict:
    """Normalised L2 distance between the seeds' best designs (shared bounded knobs)."""
    best_dirs = []
    for run in runs:
        valid = valid_rows(run["rows"])
        if not valid:
            continue
        row = min(valid, key=lambda r: float(r.get("objective", float("inf"))))
        params = params_flat(row)
        bounds = run["bounds"]
        normed = {k: (params[k] - bounds[k][0]) / (bounds[k][1] - bounds[k][0])
                  for k in params if k in bounds}
        if normed:
            best_dirs.append((str(run["run_dir"]), normed))
    out: dict[str, float | None] = {}
    for i in range(len(best_dirs)):
        for j in range(i + 1, len(best_dirs)):
            (di, pi), (dj, pj) = best_dirs[i], best_dirs[j]
            keys = sorted(set(pi) & set(pj))
            if not keys:
                out[f"{di}|{dj}"] = None
                continue
            out[f"{di}|{dj}"] = math.sqrt(sum((pi[k] - pj[k]) ** 2 for k in keys)) / math.sqrt(len(keys))
    return out


def analyse_group(name: str, run_dirs: list[Path], *, target_j: float | None = None,
                  budget: int | None = None,
                  cost_budget: float | None = None) -> dict:
    runs = [load_run(Path(d)) for d in run_dirs]
    prov = _provenance(runs)
    if len(prov) != 1:
        raise ValueError(f"group {name!r} mixes provenance {sorted(prov)} "
                         f"(objective version, brief and family must be identical within a group)")
    compat = compare_compatibility(runs, block_task_config=True)
    task_block = [b for b in compat["blocking"]
                  if b.startswith(("objective", "brief", "family", "task_config"))]
    if task_block:
        raise ValueError(f"group {name!r} is not one task/scoring identity: {task_block}")
    seeds = []
    target_curves: list[list[dict]] = []
    for run in runs:
        curve = best_so_far_curve(run, include_failed_seconds=True)
        target_curves.append(curve)
        best = curve[-1]["best"] if curve else None
        cost_curve = [{"n": p["n"], "best": p["best"], "cost_s": p["wall_s"]} for p in curve]
        entry = {
            "run_dir": str(run["run_dir"]),
            "cma_seed": run["meta"]["cma_seed"],
            "best_j": best,
            "n_new_valid": len(curve),
            "evals_to_1pct": evals_to_within(curve, best, 0.01) if best is not None else None,
            "evals_to_5pct": evals_to_within(curve, best, 0.05) if best is not None else None,
            "cost": _ledger(run),
            "replicate": replicate_summary([run]),
        }
        if target_j is not None:
            entry["time_to_target_evals"] = time_to_target(curve, target_j, "n", budget)
            entry["time_to_target_cost_s"] = time_to_target(cost_curve, target_j, "cost_s", cost_budget)
        seeds.append(entry)
    bests = [s["best_j"] for s in seeds if s["best_j"] is not None]
    median = float(np.median(bests)) if bests else None
    spread = float(max(bests) - min(bests)) if bests else None
    group_target = min(bests) if bests else None
    ecdf: dict[str, list | None] = {}
    for rel in TARGET_RELS:
        ecdf[f"ecdf_{int(rel * 100)}pct"] = _legacy_ecdf(runs, group_target, rel)
    statuses = [(read_json(Path(r["run_dir"]) / "run.json") or {}).get("status") for r in runs]
    cost_totals = _sum_ledgers([s["cost"] for s in seeds])
    out: dict[str, Any] = {
        "runs": [str(Path(d)) for d in run_dirs],
        "n_seeds": len(seeds),
        "seeds": seeds,
        "median_best": median,
        "spread_best": spread,
        "ci95_median_best": bootstrap_ci(bests),
        "seed_distances_norm": _seed_distances(runs),
        "ecdf_basis": "relative_to_group_best_descriptive",
        "compatibility": compat,
        "replicates": replicate_summary(runs),
        "outcome_counts": {
            "n_runs": len(runs),
            "finished": sum(1 for s in statuses if s == "finished"),
            "interrupted_or_unknown": sum(1 for s in statuses if s not in ("finished",)),
            "with_valid_eval": sum(1 for s in seeds if s["best_j"] is not None),
            "all_failure": sum(1 for s in seeds if s["best_j"] is None),
        },
        "cost_totals": cost_totals,
        "cost_model": cost_model_eligibility(cost_totals, compat),
        **ecdf,
    }
    if target_j is not None:
        out["fixed_target"] = {
            "target_j": float(target_j),
            "budget_evals": budget,
            "budget_cost_s": cost_budget,
            "ecdf_evals": ecdf_time_to_target(target_curves, target_j, "n", budget),
            "ecdf_cost_s": ecdf_time_to_target(
                [[{"n": p["n"], "best": p["best"], "cost_s": p["wall_s"]} for p in c]
                 for c in target_curves], target_j, "cost_s", cost_budget),
            "ert_evals": expected_runtime(target_curves, target_j, "n", budget),
            "ert_cost_s": expected_runtime(
                [[{"n": p["n"], "best": p["best"], "cost_s": p["wall_s"]} for p in c]
                 for c in target_curves], target_j, "cost_s", cost_budget),
        }
    return out


def _pair_record(name: str, dir_a: Path, dir_b: Path, *, target_j: float | None,
                 budget: int | None, cost_budget: float | None,
                 practical_delta: float | None) -> dict:
    run_a, run_b = load_run(Path(dir_a)), load_run(Path(dir_b))
    compat = compare_compatibility([run_a, run_b], block_task_config=True)
    task_block = [b for b in compat["blocking"]
                  if b.startswith(("objective", "brief", "family", "task_config"))]
    if task_block:
        raise ValueError(f"pair {name!r} compares different task/scoring identities: {task_block}")
    curve_a = best_so_far_curve(run_a, include_failed_seconds=True)
    curve_b = best_so_far_curve(run_b, include_failed_seconds=True)
    cost_a = [{"n": p["n"], "best": p["best"], "cost_s": p["wall_s"]} for p in curve_a]
    cost_b = [{"n": p["n"], "best": p["best"], "cost_s": p["wall_s"]} for p in curve_b]
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
    seed_a = run_a["meta"]["cma_seed"]
    seed_b = run_b["meta"]["cma_seed"]
    rec: dict[str, Any] = {
        "pair": name,
        "a": str(Path(dir_a)),
        "b": str(Path(dir_b)),
        "seed_a": seed_a,
        "seed_b": seed_b,
        "shared_cma_seed": seed_a == seed_b,
        "shared_seed_warning": ("same RNG seed is not proof of shared candidates; "
                                "pairing is valid only because it was predeclared"),
        "compatibility": compat,
        "final": {
            "a_best_j": best_a,
            "b_best_j": best_b,
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


def _verdict_label(decision: str | None, direction: str | None) -> str:
    if decision == "a_better":
        return "a-beats-b"
    if decision == "b_better":
        return "b-beats-a"
    if decision == "pilot_only":
        return "indicative" if direction else "no-verdict"
    return "no-verdict"


def analyse_groups(groups: dict[str, list[Path]], *,
                   pairs: list[tuple[str, Path, Path]] | None = None,
                   target_j: float | None = None, budget: int | None = None,
                   cost_budget: float | None = None,
                   practical_delta: float | None = None,
                   alpha: float = 0.05, power: float = 0.8) -> dict:
    analysed: dict[str, dict] = {}
    for name, dirs in groups.items():
        analysed[name] = analyse_group(name, dirs, target_j=target_j, budget=budget,
                                       cost_budget=cost_budget)
    pair_records: list[dict] = []
    for name, da, db in (pairs or []):
        pair_records.append(_pair_record(name, da, db, target_j=target_j, budget=budget,
                                         cost_budget=cost_budget,
                                         practical_delta=practical_delta))
    compatible_pairs = [p for p in pair_records
                        if p["compatibility"]["compatible_for_inference"]]
    blocked_pairs = [{"pair": p["pair"], "blocking": p["compatibility"]["blocking"]}
                     for p in pair_records
                     if not p["compatibility"]["compatible_for_inference"]]
    final_diffs = [p["final"]["difference"] for p in compatible_pairs
                   if p["final"]["difference"] is not None]
    budget_diffs = [p["fixed_eval_budget"]["difference"] for p in compatible_pairs
                    if p["fixed_eval_budget"]["complete_pair"]
                    and p["fixed_eval_budget"]["difference"] is not None]
    cost_diffs = [p["fixed_cost_budget"]["difference"] for p in compatible_pairs
                  if p["fixed_cost_budget"]["complete_pair"]
                  and p["fixed_cost_budget"]["difference"] is not None]
    preferred = budget_diffs if budget_diffs else final_diffs
    if pair_records and not compatible_pairs:
        summary = {"n_pairs": 0, "status": "incompatible", "decision": "incompatible",
                   "ci95_bootstrap_mean": None,
                   "note": "No pair is grid/fidelity/software compatible; "
                           "prospective inference is blocked."}
        power_plan = None
    elif pair_records:
        summary = paired_summary(preferred, practical_delta)
        power_plan = power_planning(preferred, practical_delta, alpha, power)
    else:
        summary = None
        power_plan = None
    verdicts = []
    if summary is not None:
        a_finals = [r["final"]["a_best_j"] for r in pair_records
                    if r["final"]["a_best_j"] is not None]
        b_finals = [r["final"]["b_best_j"] for r in pair_records
                    if r["final"]["b_best_j"] is not None]
        decision = summary.get("decision")
        verdicts.append({
            "a": "paired_runs", "b": "declared_pairs",
            "median_a": float(np.median(a_finals)) if a_finals else None,
            "median_b": float(np.median(b_finals)) if b_finals else None,
            "spread_a": (float(max(a_finals) - min(a_finals)) if len(a_finals) >= 2 else 0.0),
            "spread_b": (float(max(b_finals) - min(b_finals)) if len(b_finals) >= 2 else 0.0),
            "n_seeds": summary["n_pairs"],
            "rule_holds": decision in ("a_better", "b_better"),
            "verdict": _verdict_label(decision, summary.get("direction")),
            "decision": decision,
            "ci95_bootstrap_mean": summary.get("ci95_bootstrap_mean"),
            "practical_delta": practical_delta,
            "pilot": summary.get("pilot"),
            "note": summary.get("note"),
        })
    prospective: dict[str, Any] = {
        "pairing_declared": bool(pair_records),
        "pairs": pair_records,
        "compatibility_blocked_pairs": blocked_pairs,
        "summaries": {
            "final_best": paired_summary(final_diffs, practical_delta) if final_diffs else None,
            "fixed_eval_budget": paired_summary(budget_diffs, practical_delta) if budget_diffs else None,
            "fixed_cost_budget": paired_summary(cost_diffs, practical_delta) if cost_diffs else None,
            "preferred_basis": ("fixed_eval_budget" if budget_diffs else
                                ("final_best" if final_diffs else None)),
            "summary": summary,
        },
        "power": power_plan,
        "note": ("Descriptive historical view only: no pairing was predeclared."
                 if not pair_records else
                 "Paired inference over predeclared pairs; five pairs is a pilot."),
    }
    return {
        "seed_rule": ("Legacy descriptive label: A beats B only when medians differ by "
                      "more than both spreads. Not used as the decision; see prospective."),
        "inference_policy": {
            "descriptive_historical": "observed runs; no causal or prospective claim",
            "prospective": "requires --pair; d = A - B; bootstrap CI; censoring reported",
            "pairing": "predeclared pairing only; matching RNG seeds alone is not enough",
            "pilot_warning": "five pairs is a pilot, not a significance guarantee",
        },
        "descriptive_historical": {"groups": analysed},
        "prospective": prospective,
        "groups": analysed,
        "verdicts": verdicts,
    }


def parse_group(spec: str) -> tuple[str, list[Path]]:
    """Parse ``name=dir,dir,...``."""
    if "=" not in spec:
        raise fail("seed_variance: --group expects name=<dir>,<dir>,...")
    name, _, rest = spec.partition("=")
    dirs = [Path(p) for p in rest.split(",") if p.strip()]
    if not name.strip() or not dirs:
        raise fail("seed_variance: --group expects name=<dir>,<dir>,...")
    return name.strip(), dirs


def parse_pair(spec: str) -> tuple[str, Path, Path]:
    """Parse ``name=<dirA>|<dirB>`` (pipe avoids ambiguity with comma-separated dirs)."""
    if "=" not in spec or "|" not in spec:
        raise fail("seed_variance: --pair expects name=<dirA>|<dirB>")
    name, _, rest = spec.partition("=")
    a, _, b = rest.partition("|")
    if not name.strip() or not a.strip() or not b.strip():
        raise fail("seed_variance: --pair expects name=<dirA>|<dirB>")
    return name.strip(), Path(a.strip()), Path(b.strip())


def _md(payload: dict) -> str:
    pol = payload["inference_policy"]
    lines = ["# Seed variance", "",
             f"Rule: {payload['seed_rule']}", "",
             "Descriptive historical view: observed runs, no prospective inference.",
             ""]
    for name, g in payload["descriptive_historical"]["groups"].items():
        lines += [f"## {name}", "",
                  f"- {g['n_seeds']} seeds; median best J **{g['median_best']}**;"
                  f" spread (max-min) **{g['spread_best']}**",
                  f"- bootstrap 95% CI of median: {g['ci95_median_best']}",
                  f"- independent replicates: {g['replicates']['n_independent_replicates']}"
                  f" (duplicate seeds: {g['replicates']['duplicate_seed_run_dirs'] or 'none'})",
                  f"- compatibility blocking: {g['compatibility']['blocking'] or 'none'}", ""]
        ct = g["cost_totals"]
        lines += ["| run | seed | best J | new valid | rows | attempts | cache | BEM calls | failed/refused | cost s | wall s |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for s in g["seeds"]:
            c = s["cost"]
            el = c["elapsed_seconds"]
            lines.append(
                f"| `{Path(s['run_dir']).name}` | {s['cma_seed']} | {s['best_j']} | "
                f"{s['n_new_valid']} | {c['index_rows']} | {c['attempts_new']} | "
                f"{c['cache_hits']} | {c['actual_bem_calls_observed']} | "
                f"{c['cheap_refusals'] + c['solver_failures'] + c['pipeline_failures'] + c['unknown_failures']} | "
                f"{el['attempts_all_incl_failed_refused']:.3f} | {el['wall_span']} |")
        lines.append("")
        ft = g.get("fixed_target")
        if ft:
            lines += [f"Fixed target J <= {ft['target_j']}: "
                      f"ECDF (evals) {ft['ecdf_evals']['n_reached']}/"
                      f"{ft['ecdf_evals']['n_runs']} reached; "
                      f"ERT evals {ft['ert_evals']['ert']} "
                      f"({ft['ert_evals']['n_censored']} censored)", ""]
    lines += ["## Prospective paired comparison", ""]
    if not payload["prospective"]["pairing_declared"]:
        lines.append("No pairing was predeclared; prospective inference is unavailable. "
                     + pol["prospective"] + ".")
        lines.append("")
        return "\n".join(lines)
    for rec in payload["prospective"]["pairs"]:
        lines += [f"### {rec['pair']}", "",
                  f"- d_final = A - B = {rec['final']['difference']}; "
                  f"fixed-eval-budget d = {rec['fixed_eval_budget']['difference']} "
                  f"(complete pair: {rec['fixed_eval_budget']['complete_pair']})",
                  f"- fixed-cost d = {rec['fixed_cost_budget']['difference']} "
                  f"(complete pair: {rec['fixed_cost_budget']['complete_pair']})",
                  f"- shared CMA seed: {rec['shared_cma_seed']} — {rec['shared_seed_warning']}",
                  f"- compatibility blocking: {rec['compatibility']['blocking'] or 'none'}", ""]
    s = payload["prospective"]["summaries"]["summary"]
    if s:
        lines += ["| n pairs | mean d | median d | 95% CI mean | signs (A/B/tie) | decision |",
                  "|---:|---:|---:|---|---|---|"]
        lines.append(f"| {s['n_pairs']} | {s.get('mean')} | {s.get('median')} | "
                     f"{s.get('ci95_bootstrap_mean')} | "
                     f"{s['signs']['a_better']}/{s['signs']['b_better']}/{s['signs']['ties']} | "
                     f"**{s['decision']}** |")
        lines += ["", f"_{s['note']}_", ""]
    pw = payload["prospective"].get("power")
    if pw:
        lines += [f"Power/sample-size plan: {pw.get('status')} — "
                  f"{pw.get('n_pairs_required')} pairs for practical delta "
                  f"{pw.get('practical_delta')} at alpha={pw.get('alpha')}, "
                  f"power={pw.get('power')} ({pw.get('method')}).", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--group", action="append", required=True,
                    help="<name>=<dir>,<dir>,... runs of the same config/brief, different CMA seeds")
    ap.add_argument("--pair", action="append", default=None,
                    help="<name>=<dirA>|<dirB> predeclared replicate pairing for inference")
    ap.add_argument("--target-j", type=float, default=None,
                    help="fixed physical target J (best-so-far <= target) for ECDF/ERT")
    ap.add_argument("--budget", type=int, default=None, help="fixed new-valid-eval budget")
    ap.add_argument("--cost-budget", type=float, default=None,
                    help="fixed accumulated-attempt cost budget in seconds")
    ap.add_argument("--practical-delta", type=float, default=None,
                    help="practical improvement threshold in J for decisions/power")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    add_out_arg(ap)
    args = ap.parse_args(argv)
    groups = dict(parse_group(s) for s in args.group)
    pairs = [parse_pair(s) for s in (args.pair or [])]
    try:
        payload = analyse_groups(groups, pairs=pairs, target_j=args.target_j,
                                 budget=args.budget, cost_budget=args.cost_budget,
                                 practical_delta=args.practical_delta,
                                 alpha=args.alpha, power=args.power)
    except ValueError as exc:
        # schema: a group (or pair) mixing objective version/brief/family/task config
        # is a hard error, exit code 2 — never a warning
        raise fail(f"seed_variance: {exc}") from exc
    write_report(Path(args.out), TOOL, payload, _md(payload))
    print(f"seed_variance OK: {len(groups)} group(s), {len(pairs)} pair(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
