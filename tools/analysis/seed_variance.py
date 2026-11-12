"""A.2 seed_variance.py — same config/brief, different CMA seeds: how much of the A/B
difference is seed noise?

Usage:  PY tools\\analysis\\seed_variance.py --group name=<dir>,<dir>,... [--group ...] --out <dir>

Per seed: best J; per group: median, spread (max-min), bootstrap 95% CI of the median,
a COCO-style ECDF of evals-to-target, and pairwise distances between the seeds' best
designs in normalised knob space. Verdicts use the 2026-10-23 rule "A beats B only when
medians differ by more than both spreads"; >= 5 seeds prints a verdict, 3-4 seeds only
"indicative". Groups mixing objective version, brief or family are a hard error (exit 2).
Schema: ``tools/analysis/schema.md`` § seed_variance.json.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from _common import (add_out_arg, beats_rule, best_so_far_curve, bootstrap_ci, evals_to_within,
                     fail, load_run, params_flat, valid_rows, write_report)

TOOL = "seed_variance"
TARGET_RELS = (0.01, 0.05)


def _provenance(runs: list[dict]) -> set[tuple]:
    """{(objective_version, brief, family)} of every run."""
    out = set()
    for r in runs:
        m = r["meta"]
        out.add((m["objective_version"], str(m["brief"]), str(m["family"])))
    return out


def analyse_group(name: str, run_dirs: list[Path]) -> dict:
    runs = [load_run(Path(d)) for d in run_dirs]
    prov = _provenance(runs)
    if len(prov) != 1:
        raise ValueError(f"group {name!r} mixes provenance {sorted(prov)} "
                         f"(objective version, brief and family must be identical within a group)")
    seeds = []
    for run in runs:
        curve = best_so_far_curve(run)
        best = curve[-1]["best"] if curve else None
        seeds.append({"run_dir": str(run["run_dir"]), "cma_seed": run["meta"]["cma_seed"],
                      "best_j": best, "n_new_valid": len(curve),
                      "evals_to_1pct": evals_to_within(curve, best, 0.01) if best is not None else None,
                      "evals_to_5pct": evals_to_within(curve, best, 0.05) if best is not None else None})
    bests = [s["best_j"] for s in seeds if s["best_j"] is not None]
    median = float(np.median(bests)) if bests else None
    spread = float(max(bests) - min(bests)) if bests else None
    group_target = min(bests) if bests else None
    ecdf: dict[str, list | None] = {}
    for rel in TARGET_RELS:
        pts = _ecdf(runs, group_target, rel)
        # schema requires both keys; null when the group target can't be computed
        ecdf[f"ecdf_{int(rel * 100)}pct"] = pts
    return {
        "runs": [str(Path(d)) for d in run_dirs], "n_seeds": len(seeds), "seeds": seeds,
        "median_best": median, "spread_best": spread,
        "ci95_median_best": bootstrap_ci(bests),
        "seed_distances_norm": _seed_distances(runs),
        **ecdf,
    }


def _ecdf(runs: list[dict], group_target: float | None, rel: float) -> list[list[float]] | None:
    """COCO-style ECDF: fraction of seeds whose best-so-far reached group_target*(1+rel) by eval n."""
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


def analyse_groups(groups: dict[str, list[Path]]) -> dict:
    schema_rule = ("A beats B only when medians differ by more than both spreads; "
                   ">= 5 seeds prints a verdict (3-4 = indicative)")
    analysed: dict[str, dict] = {}
    provenance: dict[str, set[tuple]] = {}
    for name, dirs in groups.items():
        analysed[name] = analyse_group(name, dirs)
        provenance[name] = _provenance([load_run(Path(d)) for d in dirs])
    verdicts = []
    names = list(analysed)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = analysed[names[i]], analysed[names[j]]
            if a["median_best"] is None or b["median_best"] is None \
                    or a["spread_best"] is None or b["spread_best"] is None:
                continue
            # J is only comparable when the compared groups share objective version,
            # brief AND family (schema.md: a verdict over groups that differ in any of
            # the three is a hard error, not a warning).
            mixed = provenance[names[i]] ^ provenance[names[j]]
            if mixed:
                raise fail(f"seed_variance: verdict {names[i]} vs {names[j]} compares "
                           f"groups of different provenance {sorted(map(str, mixed))} "
                           "(objective version, brief and family must be identical)")
            n_runs = min(a["n_seeds"], b["n_seeds"])
            verdicts.append({
                "a": names[i], "b": names[j],
                "median_a": a["median_best"], "median_b": b["median_best"],
                "spread_a": a["spread_best"], "spread_b": b["spread_best"],
                "n_seeds": n_runs,
                "rule_holds": abs(a["median_best"] - b["median_best"]) > max(
                    a["spread_best"], b["spread_best"]),
                "verdict": beats_rule(a["median_best"], a["spread_best"],
                                      b["median_best"], b["spread_best"], n_runs),
            })
    return {"groups": analysed, "verdicts": verdicts, "seed_rule": schema_rule}


def parse_group(spec: str) -> tuple[str, list[Path]]:
    """Parse ``name=dir,dir,...``."""
    if "=" not in spec:
        raise fail("seed_variance: --group expects name=<dir>,<dir>,...")
    name, _, rest = spec.partition("=")
    dirs = [Path(p) for p in rest.split(",") if p.strip()]
    if not name.strip() or not dirs:
        raise fail("seed_variance: --group expects name=<dir>,<dir>,...")
    return name.strip(), dirs


def _md(payload: dict) -> str:
    lines = ["# Seed variance", "", f"Rule: {payload['seed_rule']}.", ""]
    for name, g in payload["groups"].items():
        lines += [f"## {name}", "",
                  f"- {g['n_seeds']} seeds; median best J **{g['median_best']}**;"
                  f" spread (max-min) **{g['spread_best']}**",
                  f"- bootstrap 95% CI of median: {g['ci95_median_best']}", "",
                  "| run | seed | best J | new valid evals | evals→1% | evals→5% |",
                  "|---|---:|---:|---:|---:|---:|"]
        for s in g["seeds"]:
            lines.append(f"| `{Path(s['run_dir']).name}` | {s['cma_seed']} | "
                         f"{s['best_j']} | {s['n_new_valid']} | {s['evals_to_1pct']} | {s['evals_to_5pct']} |")
        lines.append("")
    if payload["verdicts"]:
        lines += ["## Verdicts (2026-10-23 rule)", "",
                  "| A | B | median A | median B | spread A | spread B | verdict |",
                  "|---|---|---:|---:|---:|---:|---|"]
        for v in payload["verdicts"]:
            lines.append(f"| {v['a']} | {v['b']} | {v['median_a']} | {v['median_b']} | "
                         f"{v['spread_a']} | {v['spread_b']} | **{v['verdict']}** |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--group", action="append", required=True,
                    help="<name>=<dir>,<dir>,... runs of the same config/brief, different CMA seeds")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    groups = dict(parse_group(s) for s in args.group)
    try:
        payload = analyse_groups(groups)
    except ValueError as exc:
        # schema: a group (or verdict) mixing objective version/brief/family is a hard
        # error, exit code 2 — never a warning
        raise fail(f"seed_variance: {exc}") from exc
    write_report(Path(args.out), TOOL, payload, _md(payload))
    print(f"seed_variance OK: {len(groups)} group(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
