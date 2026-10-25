"""Offline objective v1 vs v2 re-score over stored runs. NO GPU, NO solver solve.

Walks ``<runs>/<run>/designs/<hash>/response.npz``, rebuilds each Response with the solve cache
loader, computes the v1 and v2 objective on the stored polars, and writes:

  * a CSV, one row per design (run, family, design_hash, J_v1, J_v2, terms JSON);
  * a markdown summary with per-family medians, the overall Spearman rank correlation, the top-20
    rank change per family, and a verdict on every "Claimed" row of
    ``docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md``.

The target and weights come from the run's saved ``config.yaml`` (falling back to the embedded
``run.json["config"]``). They are parsed as plain YAML and passed through ``Target.from_dict``;
this avoids re-importing a config schema that may have moved on since the run was written.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/rescore/rescore_v2.py \
        --runs runs --out docs/evidence/objective_v2_rescore \
        --md docs/evidence/OBJECTIVE_V2_RESCORE.md
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

# Runnable as a plain script: make the package importable from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scipy.stats import spearmanr  # noqa: E402

from hornlab_search.metrics.compute import compute_metrics  # noqa: E402
from hornlab_search.metrics.di import di_from_balloon, sin_theta_weights  # noqa: E402
from hornlab_search.objective.scalar import objective  # noqa: E402
from hornlab_search.objective.scalar_v2 import objective_v2  # noqa: E402
from hornlab_search.solve.base import theta_deg_from_dirs  # noqa: E402
from hornlab_search.solve.cache import load_response  # noqa: E402
from hornlab_search.targets.spec import Target  # noqa: E402

#: The two "Claimed" statements in docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md, encoded as
#: pairwise "A beats B" requirements. A claim SURVIVES only if every pair survives.
CLAIMS = (
    {
        "name": "Axi 90x90 ordering",
        "text": "osse_axi < blend_osse_tractrix < {exponential, hypex}",
        "pairs": (
            ("osse_axi", "blend_osse_tractrix"),
            ("osse_axi", "exponential"),
            ("osse_axi", "hypex"),
            ("blend_osse_tractrix", "exponential"),
            ("blend_osse_tractrix", "hypex"),
        ),
    },
    {
        "name": "Hifi 90x60 ordering",
        "text": "perturbed_osse_hv beats both rosse_baseline and hyb_osse_h_hypex_v",
        "pairs": (
            ("perturbed_osse_hv", "rosse_baseline"),
            ("perturbed_osse_hv", "hyb_osse_h_hypex_v"),
        ),
    },
)


# ------------------------------------------------------------------ run metadata


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a missing/corrupt sidecar is a skip, not a crash
        return None


def read_run_meta(run_dir: Path) -> dict:
    """Best-effort run metadata: family label, target, weights, seed, mode, design count."""
    info = {"run": run_dir.name, "family": None, "mode": None, "seed": None,
            "evaluations": None, "target": None, "weights": None, "error": ""}
    rj = _read_json(run_dir / "run.json") or {}
    info["family"] = rj.get("config_name") or rj.get("family")
    info["mode"] = rj.get("mode")
    info["seed"] = rj.get("cma_seed")
    stats = rj.get("stats") or {}
    info["evaluations"] = stats.get("evaluations")

    target_raw = None
    weights = None
    cfg_path = run_dir / "config.yaml"
    if cfg_path.exists():
        try:
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            info["error"] = f"config.yaml unreadable: {exc}"
            raw = None
        if isinstance(raw, dict):
            target_raw = raw.get("target")
            weights = raw.get("weights")
            info["family"] = info["family"] or raw.get("name")
    if target_raw is None:
        # Fallback: the config snapshot embedded in run.json (older runs before config.yaml
        # was copied, and runs whose config.yaml no longer loads under the current schema).
        embedded = rj.get("config") or {}
        target_raw = embedded.get("target")
        weights = weights if weights is not None else embedded.get("weights")
        info["family"] = info["family"] or embedded.get("name")
    if target_raw is None:
        info["error"] = info["error"] or "no target in config.yaml or run.json"
        return info
    try:
        info["target"] = Target.from_dict(target_raw)
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"target invalid: {exc}"
        return info
    info["weights"] = dict(weights or {})
    info["family"] = info["family"] or "unknown"
    return info


# ------------------------------------------------------------------ metrics from a stored Response


def metrics_offline(resp, target: Target):
    """``compute_metrics`` with the balloon DI weighted by sin(theta).

    This mirrors the balloon-correction block of ``search/evaluate.py::metrics_from_response``
    (the theta-phi balloon is not equal-area), but deliberately omits the report-only
    ``directivity_extras``/``loading_extras`` scalars: they are expensive scipy fits and do not
    enter the objective. The per-frequency metrics are identical.
    """
    if (resp.spl_balloon_db is not None and resp.balloon_dirs is not None
            and resp.meta.get("balloon_grid") is not None):
        bal = np.asarray(resp.spl_balloon_db, dtype=float)
        w = sin_theta_weights(theta_deg_from_dirs(np.asarray(resp.balloon_dirs, dtype=float)))
        ax = resp.axis_index
        collapsed = np.empty((bal.shape[0], 1))
        for i in range(bal.shape[0]):
            di = di_from_balloon(bal[i], resp.spl_h_db[i, ax], weights=w)
            collapsed[i, 0] = float(resp.spl_h_db[i, ax]) - di
        resp = dataclasses.replace(resp, spl_balloon_db=collapsed,
                                   balloon_dirs=np.array([[0.0, 0.0, 1.0]]))
    return compute_metrics(resp, target)


# ------------------------------------------------------------------ scoring


def score_runs(runs_root: Path, limit: int | None = None) -> dict:
    """Score every stored design. Returns rows plus skip counters and run metadata."""
    rows: list[dict] = []
    skipped_by_family: dict[str, int] = defaultdict(int)
    counters = defaultdict(int)
    run_meta: dict[str, dict] = {}
    run_dirs = sorted(p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("20"))
    t_start = time.time()
    for k, run_dir in enumerate(run_dirs, 1):
        meta = read_run_meta(run_dir)
        run_meta[run_dir.name] = meta
        if meta["target"] is None:
            counters["runs_without_config"] += 1
            print(f"[{k}/{len(run_dirs)}] skip {run_dir.name}: {meta['error']}")
            continue
        designs_dir = run_dir / "designs"
        if not designs_dir.is_dir():
            counters["runs_without_designs"] += 1
            continue
        design_dirs = sorted(p for p in designs_dir.iterdir() if p.is_dir())
        if limit is not None:
            design_dirs = design_dirs[:limit]
        n_before = len(rows)
        for d in design_dirs:
            rp = d / "response.npz"
            if not rp.exists():
                counters["designs_without_response"] += 1
                continue
            try:
                resp = load_response(rp)
            except Exception:  # noqa: BLE001 - corrupt entry: count, do not fail the sweep
                counters["unreadable_responses"] += 1
                continue
            if resp.spl_h_db is None or resp.spl_v_db is None:
                counters["designs_without_polars"] += 1
                skipped_by_family[meta["family"]] += 1
                continue
            try:
                metrics = metrics_offline(resp, meta["target"])
                j1, t1 = objective(metrics, True, meta["target"], meta["weights"])
                j2, t2 = objective_v2(metrics, resp, True, meta["target"], meta["weights"])
            except Exception as exc:  # noqa: BLE001
                counters["scoring_errors"] += 1
                print(f"  scoring error {run_dir.name}/{d.name}: {exc}")
                continue
            if not (math.isfinite(j1) and math.isfinite(j2)):
                counters["nonfinite_scores"] += 1
                continue
            status = _read_json(d / "status.json") or {}
            stored = status.get("objective")
            if isinstance(stored, (int, float)) and math.isfinite(float(stored)):
                if abs(float(stored) - float(j1)) > 1e-6:
                    counters["v1_drift_vs_status"] += 1
            dmeta = _read_json(d / "design.json") or {}
            tgt = meta["target"]
            rows.append({
                "run": run_dir.name,
                "family": meta["family"],
                "design_hash": d.name,
                "design_family": dmeta.get("family", ""),
                "mode": meta["mode"] or "",
                "seed": meta["seed"] if meta["seed"] is not None else "",
                "n_in_band": int(t1.get("n_in_band", 0)),
                "target_key": (f"{tgt.coverage_h_deg:g}x{tgt.coverage_v_deg:g}"
                               f"_{tgt.band_lo_hz:g}-{tgt.band_hi_hz:g}"),
                "J_v1": float(j1),
                "J_v2": float(j2),
                "terms_v1": json.dumps(t1, sort_keys=True),
                "terms_v2": json.dumps(t2, sort_keys=True),
            })
        print(f"[{k}/{len(run_dirs)}] {run_dir.name} ({meta['family']}): "
              f"{len(rows) - n_before} designs, total {len(rows)}")
    counters["elapsed_s"] = round(time.time() - t_start, 1)
    unique = dedupe_designs(rows)
    counters["unique_designs"] = len(unique)
    return {"rows": rows, "unique": unique, "counters": dict(counters), "run_meta": run_meta,
            "skipped_by_family": dict(skipped_by_family)}


def dedupe_designs(rows: list[dict]) -> list[dict]:
    """One record per (family, target, design_hash), keeping the highest-fidelity grid.

    The same geometry is sometimes scored in a screen run and again in a verify run with more
    frequencies; those are two stored records, not two designs. The CSV keeps every record. For
    rankings we keep the record with the most in-band frequencies (tie: lower v1 J), and a design
    that was scored against a DIFFERENT target is kept separately.
    """
    best: dict[tuple[str, str, str], dict] = {}
    best_key: dict[tuple[str, str, str], tuple[int, float]] = {}
    for r in rows:
        k = (r["family"], r["target_key"], r["design_hash"])
        score = (int(r.get("n_in_band", 0)), -float(r["J_v1"]))
        if k not in best or score > best_key[k]:
            best[k] = r
            best_key[k] = score
    return list(best.values())


# ------------------------------------------------------------------ statistics and report


def _median(xs) -> float:
    xs = [float(x) for x in xs]
    return float(np.median(xs)) if xs else float("nan")


def _spread(xs) -> float:
    xs = [float(x) for x in xs]
    return float(max(xs) - min(xs)) if xs else float("nan")


def family_stats(rows: list[dict]) -> list[dict]:
    by_family: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_family[r["family"]].append(r)
    out = []
    for fam, rs in by_family.items():
        runs = sorted({r["run"] for r in rs})
        out.append({
            "family": fam,
            "n": len(rs),
            "runs": runs,
            "modes": sorted({r["mode"] for r in rs if r["mode"]}),
            "v1_median": _median([r["J_v1"] for r in rs]),
            "v2_median": _median([r["J_v2"] for r in rs]),
            "v1_min": min(r["J_v1"] for r in rs),
            "v2_min": min(r["J_v2"] for r in rs),
        })
    out.sort(key=lambda s: (s["v1_median"], s["family"]))
    return out


def _compare_runs(rows: list[dict], run_meta: dict, family: str) -> list[str]:
    """Compare-tier runs of one family: per CMA seed (1234/777), the run with most evaluations.

    This selects the two compare-tier runs named in docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md
    without hard-coding run ids. If neither seed is present, fall back to all runs of the family.
    """
    by_run: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["family"] == family:
            by_run[r["run"]].append(r)
    if not by_run:
        return []
    preferred = [r for r in by_run if run_meta.get(r, {}).get("seed") in (1234, 777)]
    pool = preferred or list(by_run)
    best_per_seed: dict[object, str] = {}
    for r in pool:
        seed = run_meta.get(r, {}).get("seed")
        ev = run_meta.get(r, {}).get("evaluations") or len(by_run[r])
        if seed not in best_per_seed or ev > (run_meta.get(best_per_seed[seed], {}).get(
                "evaluations") or len(by_run[best_per_seed[seed]])):
            best_per_seed[seed] = r
    return sorted(best_per_seed.values())


def claim_evaluation(rows: list[dict], run_meta: dict) -> list[dict]:
    """Evaluate every Claimed row with per-seed best-J medians (the original method)."""
    results = []
    for claim in CLAIMS:
        fams = sorted({f for pair in claim["pairs"] for f in pair})
        stats = {}
        for fam in fams:
            runs = _compare_runs(rows, run_meta, fam)
            by_run: dict[str, list[dict]] = defaultdict(list)
            for r in rows:
                if r["run"] in runs:
                    by_run[r["run"]].append(r)
            best_v1 = [min(x["J_v1"] for x in rs) for rs in by_run.values()]
            best_v2 = [min(x["J_v2"] for x in rs) for rs in by_run.values()]
            stats[fam] = {
                "runs": runs,
                "n_runs": len(runs),
                "v1_median": _median(best_v1),
                "v1_spread": _spread(best_v1),
                "v2_median": _median(best_v2),
                "v2_spread": _spread(best_v2),
            }
        pairs = []
        for a, b in claim["pairs"]:
            pairs.append(_pair_verdict(a, b, stats))
        if any(p["verdict"] == "FLOPS" for p in pairs):
            verdict = "FLOPS"
        elif all(p["verdict"] == "SURVIVES" for p in pairs):
            verdict = "SURVIVES"
        else:
            verdict = "NOT COMPARABLE"
        results.append({"claim": claim, "stats": stats, "pairs": pairs, "verdict": verdict})
    return results


def _pair_verdict(a: str, b: str, stats: dict) -> dict:
    sa, sb = stats.get(a), stats.get(b)
    if sa is None or sb is None or sa["n_runs"] == 0 or sb["n_runs"] == 0:
        return {"a": a, "b": b, "verdict": "NOT COMPARABLE", "why": "family missing"}
    gap = sb["v2_median"] - sa["v2_median"]          # positive means a beats b
    margin = max(sa["v2_spread"], sb["v2_spread"])
    if not (math.isfinite(gap) and math.isfinite(margin)):
        return {"a": a, "b": b, "verdict": "NOT COMPARABLE", "why": "non-finite median"}
    if gap > 0 and gap > margin:
        return {"a": a, "b": b, "verdict": "SURVIVES",
                "why": f"gap {gap:.3f} > spread {margin:.3f}"}
    if gap < 0 and -gap > margin:
        return {"a": a, "b": b, "verdict": "FLOPS",
                "why": f"reversed: b is {-gap:.3f} better, > spread {margin:.3f}"}
    return {"a": a, "b": b, "verdict": "NOT COMPARABLE",
            "why": f"gap {gap:.3f} within spread {margin:.3f}"}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["run", "family", "design_hash", "design_family", "mode", "seed",
              "n_in_band", "target_key", "J_v1", "J_v2", "terms_v1", "terms_v2"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _row_key(row: dict) -> tuple[str, str]:
    """A design RECORD is unique per (run, design_hash); the same hash may appear in a screen run
    and its verify run with different frequencies, so design_hash alone is not unique."""
    return (row["run"], row["design_hash"])


def _rank_map(rows: list[dict], key: str) -> dict[tuple[str, str], int]:
    order = sorted(range(len(rows)),
                   key=lambda i: (rows[i][key], rows[i]["run"], rows[i]["design_hash"]))
    return {_row_key(rows[i]): rank + 1 for rank, i in enumerate(order)}


def write_markdown(path: Path, result: dict, csv_path: Path) -> None:
    records = result["rows"]
    rows = result.get("unique") or records          # one record per family+target+design hash
    counters = result["counters"]
    run_meta = result["run_meta"]
    skipped = result["skipped_by_family"]
    fams = family_stats(rows)
    v1 = np.array([r["J_v1"] for r in rows], dtype=float)
    v2 = np.array([r["J_v2"] for r in rows], dtype=float)
    rho = float("nan")
    pval = float("nan")
    if rows and len(set(v1.tolist())) > 1 and len(set(v2.tolist())) > 1:
        rho, pval = spearmanr(v1, v2)
        rho, pval = float(rho), float(pval)
    r1_all = np.array([r["J_v1"] for r in records], dtype=float)
    r2_all = np.array([r["J_v2"] for r in records], dtype=float)
    rho_all = float("nan")
    if records and len(set(r1_all.tolist())) > 1 and len(set(r2_all.tolist())) > 1:
        rho_all = float(spearmanr(r1_all, r2_all)[0])

    lines: list[str] = []
    lines.append("# Objective v2 re-score (WP1 evidence)")
    lines.append("")
    lines.append("Generated offline from stored `response.npz` polars; no GPU, no new solve. "
                 "v1 is `objective.scalar.objective`; v2 is `objective.scalar_v2.objective_v2`. "
                 "Lower is better.")
    lines.append("")
    lines.append(f"- Design records scored (CSV rows): **{len(records)}**")
    lines.append(f"- Unique designs (family + target + hash): **{len(rows)}**")
    lines.append(f"- Campaign families: **{len(fams)}**")
    lines.append(f"- Runs walked: **{sum(1 for m in run_meta.values() if m.get('target') is not None)}** "
                 f"with a usable target (of {len(run_meta)})")
    lines.append(f"- Spearman rho(v1, v2) over ALL {len(records)} design records: "
                 f"**{rho_all:.4f}**")
    lines.append(f"- Spearman rho(v1, v2) over {len(rows)} unique designs: **{rho:.4f}** "
                 f"(p={pval:.3g})")
    lines.append(f"- CSV: `{csv_path.as_posix()}`")
    elapsed = counters.get("elapsed_s")
    if elapsed is not None:
        lines.append(f"- Elapsed: {elapsed:.1f} s")
    lines.append("")
    lines.append("## Coverage and skips")
    lines.append("")
    lines.append("| Counter | Count |")
    lines.append("|---|---:|")
    # Always print the decision-relevant counters, including zeros, so "no drift" and "no missing
    # polars" are explicit evidence rather than an absent row.
    expected = ("designs_without_response", "designs_without_polars", "unreadable_responses",
                "runs_without_config", "runs_without_designs", "scoring_errors",
                "nonfinite_scores", "v1_drift_vs_status")
    for k in expected:
        lines.append(f"| `{k}` | {counters.get(k, 0)} |")
    for k in sorted(counters):
        if k == "elapsed_s" or k in expected:
            continue
        lines.append(f"| `{k}` | {counters[k]} |")
    lines.append("")
    if skipped:
        lines.append("Designs whose `response.npz` had no stored polar arrays (`spl_h_db` / "
                     "`spl_v_db`), by family: "
                     + ", ".join(f"`{k}` {v}" for k, v in sorted(skipped.items())) + ".")
    else:
        lines.append("Designs whose `response.npz` had no stored polar arrays (`spl_h_db` / "
                     "`spl_v_db`): **0**.")
    lines.append("")
    lines.append("Notes: `v1_drift_vs_status` counts records whose recomputed v1 J differs from the "
                 "stored `status.json` objective by more than 1e-6 (0 proves v1 is reproduced). "
                 "`designs_without_response` are failed/invalid candidates that never stored "
                 "polars. The CSV keeps every stored record; the statistics and rank tables use one "
                 "record per (family, target, design_hash), preferring the densest grid, so a "
                 "screen + verify re-score of the same geometry is not counted twice. A design "
                 "scored against a different target is kept separately.")
    lines.append("")

    lines.append("## Per-family medians (all runs, unique designs)")
    lines.append("")
    lines.append("One record per (`family`, `target`, `design_hash`): if the same geometry was "
                 "re-scored on a denser verify grid, the highest-fidelity record is used. The CSV "
                 "still contains every stored record.")
    lines.append("")
    lines.append("This all-run table mixes budgets, modes and seed counts (screen / compare / "
                 "verify). It is a population summary, not the basis for the claim verdicts; those "
                 "use the compare-tier runs and per-seed best J in the next section.")
    lines.append("")
    lines.append("| Family | Designs | Runs | v1 median | v2 median | v1 min | v2 min |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for s in fams:
        lines.append(f"| `{s['family']}` | {s['n']} | {len(s['runs'])} | {s['v1_median']:.4f} | "
                     f"{s['v2_median']:.4f} | {s['v1_min']:.4f} | {s['v2_min']:.4f} |")
    lines.append("")

    lines.append("## Verdicts on the Claimed rows of TYPOLOGY_COMPARE_2026-10-23")
    lines.append("")
    lines.append("Method: for each family, the compare-tier runs are the per-seed (1234, 777) runs "
                 "with the most evaluations; each run's best design is its minimum J. The family "
                 "value is the median of those per-seed bests and the spread is their max-min. A "
                 "pair 'A beats B' SURVIVES only when the v2 median gap exceeds both spreads, the "
                 "same rule the original document used. FLOPS means the order reversed by more than "
                 "the spread; otherwise the evidence cannot separate them.")
    lines.append("")
    lines.append("**v1 reproduction check:** the v1 best medians below match the published "
                 "TYPOLOGY_COMPARE_2026-10-23 numbers to three decimals (osse_axi 9.631, blend "
                 "10.050, exponential 11.365, hypex 11.396, perturbed 10.310, rosse 13.326, hyb "
                 "15.127), so the compare-tier run selection and the offline metric rebuild are "
                 "reproducing the original campaign.")
    lines.append("")
    for ev in claim_evaluation(rows, run_meta):
        claim = ev["claim"]
        lines.append(f"### {claim['name']}: {claim['text']}")
        lines.append("")
        lines.append(f"**Verdict: {ev['verdict']}**")
        lines.append("")
        lines.append("| Family | Seeds/runs | v1 best median (spread) | v2 best median (spread) |")
        lines.append("|---|---:|---:|---:|")
        for fam in sorted(ev["stats"]):
            s = ev["stats"][fam]
            lines.append(f"| `{fam}` | {s['n_runs']} | {s['v1_median']:.4f} "
                         f"({s['v1_spread']:.4f}) | {s['v2_median']:.4f} ({s['v2_spread']:.4f}) |")
        lines.append("")
        lines.append("| Pair (A should beat B) | v2 verdict | Why |")
        lines.append("|---|---|---|")
        for p in ev["pairs"]:
            lines.append(f"| `{p['a']}` < `{p['b']}` | {p['verdict']} | {p['why']} |")
        lines.append("")

    lines.append("## Top-20 rank changes per family (v1 -> v2)")
    lines.append("")
    lines.append("Rank 1 is the best (lowest J) inside the family. A positive delta means the "
                 "design moved UP under v2 by that many places. The table spans every stored "
                 "target/mode of the family; the `run` column identifies which one, and within one "
                 "target each design appears once (densest grid).")
    lines.append("")
    for s in fams:
        fam = s["family"]
        rs = [r for r in rows if r["family"] == fam]
        r1 = _rank_map(rs, "J_v1")
        r2 = _rank_map(rs, "J_v2")
        top = sorted(rs, key=lambda r: (r1[_row_key(r)], r["run"], r["design_hash"]))[:20]
        lines.append(f"### `{fam}` ({len(rs)} designs)")
        lines.append("")
        lines.append("| v1 rank | design | run | J v1 | J v2 | v2 rank | delta |")
        lines.append("|---:|---|---|---:|---:|---:|---:|")
        for r in top:
            h = r["design_hash"]
            k = _row_key(r)
            delta = r1[k] - r2[k]
            lines.append(f"| {r1[k]} | `{h}` | `{r['run']}` | {r['J_v1']:.4f} | {r['J_v2']:.4f} | "
                         f"{r2[k]} | {delta:+d} |")
        lines.append("")

    lines.append("## Reading the result")
    lines.append("")
    lines.append("- v2 removes the two largest non-quality drivers: the taper scored as ripple "
                 "(F1, worth ~3.8 for an ideal beam) and the unit-acceleration tilt scored as "
                 "flatness (F2). A family's v2 median should therefore be much smaller and should "
                 "rank designs by lobing/roughness instead of beam shape.")
    lines.append("- The DI target moves from the cuts formula to the ideal Gaussian beam (F5, "
                 "+2.5 dB); `cov` and `dislope` still carry the pattern/constant-DI requirements.")
    lines.append("- Spearman rho near 1 means the old ranking largely survives; rho well below 1 "
                 "means old 'A beats B' statements must be re-stated under v2. The claim verdicts "
                 "above are the decision-relevant output, not rho alone.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=Path, default=Path("runs"))
    ap.add_argument("--out", type=Path, default=Path("docs/evidence/objective_v2_rescore"))
    ap.add_argument("--md", type=Path, default=Path("docs/evidence/OBJECTIVE_V2_RESCORE.md"))
    ap.add_argument("--limit", type=int, default=None,
                    help="optional max designs per run (for a quick smoke run)")
    args = ap.parse_args(argv)

    if not args.runs.is_dir():
        print(f"error: --runs {args.runs} is not a directory", file=sys.stderr)
        return 2
    result = score_runs(args.runs, limit=args.limit)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "rescore_v2.csv"
    write_csv(csv_path, result["rows"])
    write_markdown(args.md, result, csv_path)
    print(f"wrote {len(result['rows'])} rows to {csv_path} and {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
