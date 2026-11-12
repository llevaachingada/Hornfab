"""Offline objective v8 re-score + per-class tolerance calibration over the stored dataset.

NO GPU, NO solver, NO writes outside ``--out`` (default ``scratch/objective_v8_2026-11-12``;
``dataset/`` is READ-ONLY). This is day-plan group G's deliverable: it

* walks ``<dataset>/shard-*.jsonl`` + ``shard-NNNN/rec-NNNN.npz`` exactly like
  ``tools/rescore/rescore_v6_v7.py`` (rows read via ``gate_audit.parse_stored_row``, version-agnostic);
* re-scores every stored valid row under v4 / v6 / v7 (the class-matched real briefs) and under
  v8 (``hornlab_search/objective/scalar_v8.py``, v8 default weights, per-class measured
  tolerances, hard-refusal gates; the throat gate is NOT applied: the dataset stores no mesh);
* CALIBRATES the v8 tolerances from the same rows: per brief class, tolerance =
  median raw-unit value of the term over the top decile (``max(3, ceil(n/10))`` rows) of the
  stored valid rows ranked under the class-matched v4 brief — the A.9 ``term_balance``
  top-decile method applied to the v8 linear units;
* reports, per class and per baseline version (v4/v6/v7): the top-20 shortlist overlap and the
  Kendall tau between v8's and the baseline's ranking (over shared unique (design, target) keys
  with both scores below the 1e3 penalty floor), plus the tau on the union of the two top-20
  lists, gate refusals and penalty counts;
* writes ``v8_rescore.json`` + ``v8_rescore.md`` under ``--out``.

Usage (from the repo root; pass the dataset explicitly when running from a worktree)::

    .venv\\Scripts\\python.exe tools/analysis/v8_rescore.py \\
        --dataset C:\\path\\to\\hornlab-search\\dataset --out scratch/objective_v8_2026-11-12

Never rank J across versions: every table here compares rankings WITHIN one pair of versions
over the same stored rows, never absolute J values across versions.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import kendalltau

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# The canonical stored-row reader and the v6/v7 re-score helpers are imported, never copied:
# one implementation of dataset parsing, target classification and gate maths.
sys.path.insert(0, str(REPO_ROOT / "tools" / "rescore"))

import gate_audit as ga  # noqa: E402
import rescore_v6_v7 as r67  # noqa: E402

from hornlab_search.objective import scalar_v8 as s8  # noqa: E402
from hornlab_search.objective.scalar_v4 import V4Params  # noqa: E402
from hornlab_search.objective.scalar_v8 import V8_WEIGHTED_KEYS, resolve_v8_weights  # noqa: E402
from hornlab_search.objective.scalar_v8 import V8_MEASURED_TOLERANCES  # noqa: E402
from hornlab_search.objective.terms import PENALTY_FAILED  # noqa: E402
from hornlab_search.targets.spec import Target  # noqa: E402

#: Class-matched v4 briefs (the 2026-10-26 campaign set; each carries its class facts:
#: cov_narrow_ratio, cov_below_f0, freq_weights, and the loading weight for B).
V4_BRIEFS = {
    "A": REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v4" / "b1t_hifi_90x60_850_tall_v4.yaml",
    "B": REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v4" / "b3bt_pa_90x60_600_load_tall_v4.yaml",
    "C": REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v4" / "b3a_pa_90x90_400_square_v4.yaml",
}
TOP_N = 20
CLASSES = ("A", "B", "C")
OUT_DIR_DEFAULT = REPO_ROOT / "scratch" / "objective_v8_2026-11-12"


def _as_float(value) -> float:
    """``float(value)`` when it is a finite number, ``nan`` otherwise (stored-J reader)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and math.isfinite(float(value)):
        return float(value)
    return float("nan")


@dataclass(frozen=True)
class BriefConfig:
    """name + version + weights + validated params block of one brief YAML."""

    name: str
    version: int
    weights: dict
    params: object


def load_v4_brief(path: Path) -> BriefConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: brief must be a mapping")
    objective = raw.get("objective") or {}
    version = int(objective.get("version", 0))
    if version != 4:
        raise ValueError(f"{path}: expected objective.version 4, got {version!r}")
    return BriefConfig(name=str(raw.get("name") or path.stem), version=4,
                       weights=dict(raw.get("weights") or {}),
                       params=V4Params.from_block(objective))


def brief_configs() -> dict[int, dict[str, BriefConfig]]:
    """``{version: {class: BriefConfig}}`` for v4 and the r67-loaded v6/v7 briefs."""
    v4 = {cls: load_v4_brief(path) for cls, path in V4_BRIEFS.items()}
    older = r67.brief_configs()
    return {4: v4, 6: older[6], 7: older[7]}


def v8_params_for_class(cls: str, v4: BriefConfig):
    """V8Params for a class: measured tolerances + the class brief's cov flags."""
    p = s8.V8Params.for_class(cls)
    return replace(p, cov_narrow_ratio=v4.params.cov_narrow_ratio,
                   cov_below_f0=v4.params.cov_below_f0)


# ------------------------------------------------------------------ dataset pass


def collect_rows(dataset_root: Path, briefs: dict, limit: int | None = None) -> dict:
    """One read-only pass: store class, J_v4/v6/v7 and the v8 raw linear terms per row."""
    counters: dict[str, int] = {}
    def bump(key: str, n: int = 1) -> None:
        counters[key] = counters.get(key, 0) + n

    w8 = resolve_v8_weights(None)
    rows: list[dict] = []
    for shard, row_i, meta, arrays in r67.iter_dataset_rows(dataset_root):
        bump("rows_seen")
        if limit is not None and len(rows) >= limit:
            break
        try:
            target = Target.from_dict(meta.get("target") or {})
        except Exception:  # noqa: BLE001 - an old/invalid target is a skip with a reason
            bump("target_invalid")
            continue
        parsed = ga.parse_stored_row(r67._row_to_gate_row(meta, arrays), "dataset")
        if parsed is None:
            bump("parse_failed")
            continue
        try:
            metrics, resp = r67.build_scoring_inputs(meta, arrays, parsed)
            cls = r67.classify_target(target)
        except Exception:  # noqa: BLE001 - one bad row must not stop the sweep
            bump("scoring_error")
            continue
        try:
            j4, _ = score_versions_one(metrics, resp, target, briefs[4][cls], 4)
        except Exception:  # noqa: BLE001
            bump("scoring_error")
            continue
        j6, _ = score_versions_one(metrics, resp, target, briefs[6][cls], 6)
        j7, _ = score_versions_one(metrics, resp, target, briefs[7][cls], 7)

        v8p = v8_params_for_class(cls, briefs[4][cls])
        f = np.asarray(parsed["freqs"], dtype=float)
        band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
        score = band & (f >= target.f0_effective_hz())
        info = s8.v8_raw_terms(metrics, resp, target, band, score, v8p, w8, throat=None)
        rows.append({
            "shard": shard, "row": row_i,
            "design_hash": str(meta.get("design_hash") or ""),
            "target_key": r67.target_key(target),
            "family": str(meta.get("family") or ""),
            "stored_version": meta.get("objective_version"),
            "stored_J": _as_float(meta.get("objective")),
            "class": cls,
            "J_v4": float(j4), "J_v6": float(j6), "J_v7": float(j7),
            "v8_gate_failed": bool(info["gate_failed"]),
            "v8_gate_reason": info["gate_reason"],
            "v8_diag": {k: float(v) for k, v in info["diag"].items()},
            **{f"v8raw_{k}": float(info["raw"][k]) for k in V8_WEIGHTED_KEYS},
        })
        bump("scored")
        if len(rows) % 2000 == 0:
            print(f"  scored {len(rows)} rows ...", flush=True)
    return {"rows": rows, "counters": counters, "briefs": briefs}


def score_versions_one(metrics, resp, target, brief: BriefConfig, version: int):
    """(J, terms) for one version with one class brief (the dispatchers used by collect_rows)."""
    from hornlab_search.objective.scalar_v6 import objective_v6
    from hornlab_search.objective.scalar_v7 import objective_v7
    from hornlab_search.objective.scalar_v4 import objective_v4
    if version == 4:
        return objective_v4(metrics, resp, True, target, brief.weights, brief.params)
    if version == 6:
        return objective_v6(metrics, resp, True, target, brief.weights, brief.params)
    if version == 7:
        return objective_v7(metrics, resp, True, target, brief.weights, brief.params)
    raise ValueError(f"unsupported version {version}")


def j_v8(row: dict, tolerances: dict, weights: dict | None = None) -> float:
    """v8 J of a collected row under per-class tolerances (refusals score the 1e3 refusal)."""
    if row["v8_gate_failed"]:
        return float(PENALTY_FAILED)
    w = resolve_v8_weights(weights)
    raw = {k: row[f"v8raw_{k}"] for k in V8_WEIGHTED_KEYS}
    if not all(math.isfinite(raw[k] / tolerances[k]) for k in V8_WEIGHTED_KEYS):
        return float(PENALTY_FAILED)
    return float(sum(w[k] * raw[k] / tolerances[k] for k in V8_WEIGHTED_KEYS))


# ------------------------------------------------------------------ calibration


def calibrate(rows: list[dict], cls: str, rank_key: str = "J_v4") -> dict | None:
    """tolerance = median raw value of the term over the class's top-decile rows.

    Rows are ranked by ``rank_key`` (default J_v4: one version-consistent ruler per class;
    the A.9 run-level method ranks by the run's own version) with penalties last, top decile =
    ``max(3, ceil(n/10))`` rows. A term whose raw value is ``NAN_TERM_FILL`` (unmeasurable) is
    excluded from that term's median, never stored as a tolerance. A class with no rankable
    rows returns ``None`` (degrade, never fake); a class whose top decile has NO measurable
    raw value for a term raises.
    """
    subset = [r for r in rows if r["class"] == cls and math.isfinite(r[rank_key])
              and r[rank_key] < r67.PENALTY_FLOOR]
    if not subset:
        return None
    n_top = max(3, math.ceil(len(subset) / 10))
    top = sorted(subset, key=lambda r: (r[rank_key], r["design_hash"], r["target_key"]))[:n_top]
    tolerances: dict[str, float] = {}
    stats: dict[str, dict] = {}
    for k in V8_WEIGHTED_KEYS:
        vals = [r[f"v8raw_{k}"] for r in top
                if math.isfinite(r[f"v8raw_{k}"]) and r[f"v8raw_{k}"] != s8.NAN_TERM_FILL]
        if not vals:
            raise ValueError(f"class {cls}: no measurable raw value for the v8 term {k!r} "
                             f"in its top decile; tolerances cannot be calibrated")
        med = float(np.median(vals))
        if not (med > 0.0) or not math.isfinite(med):
            raise ValueError(f"class {cls}: v8 term {k!r} calibrates to {med!r} (needs a "
                             f"finite tolerance > 0); the top decile carries no measurable "
                             f"spread for it")
        tolerances[k] = med
        stats[k] = {"n_raw": len(vals),
                    "median": med,
                    "p10": float(np.percentile(vals, 10)),
                    "p90": float(np.percentile(vals, 90))}
    return {"class": cls, "n_valid": len(subset), "n_top": len(top),
            "rank_key": rank_key, "tolerances": tolerances, "raw_stats": stats}


def calibrate_all(rows: list[dict], rank_key: str = "J_v4") -> dict[str, dict]:
    out = {cls: calibrate(rows, cls, rank_key) for cls in CLASSES}
    return {cls: cal for cls, cal in out.items() if cal is not None}


# ------------------------------------------------------------------ pair analysis


def unique_best_by(rows: list[dict], jkey: str) -> list[dict]:
    """Best (lowest-J) row per (design_hash, target_key); penalties sort last."""
    best: dict[tuple[str, str], dict] = {}
    for r in rows:
        k = (r["design_hash"], r["target_key"])
        cur = best.get(k)
        if cur is None or r67._better(r[jkey]) < r67._better(cur[jkey]):
            best[k] = r
    return sorted(best.values(), key=lambda r: (r67._better(r[jkey]), r["design_hash"],
                                                r["target_key"]))


def pair_stats(rows: list[dict], mine_key: str, base_key: str) -> dict:
    """Kendall tau + top-20 overlap of one v8-vs-baseline pair within one class."""
    u_mine = unique_best_by(rows, mine_key)
    u_base = unique_best_by(rows, base_key)
    keyed_mine = {(r["design_hash"], r["target_key"]): r[mine_key] for r in u_mine}
    keyed_base = {(r["design_hash"], r["target_key"]): r[base_key] for r in u_base}
    shared = sorted(set(keyed_mine) & set(keyed_base))
    rankable = [k for k in shared
                if keyed_mine[k] < r67.PENALTY_FLOOR and keyed_base[k] < r67.PENALTY_FLOOR]
    tau = float("nan")
    if len(rankable) >= 2:
        a = np.array([keyed_mine[k] for k in rankable], dtype=float)
        b = np.array([keyed_base[k] for k in rankable], dtype=float)
        if len(set(a.tolist())) > 1 and len(set(b.tolist())) > 1:
            tau = float(kendalltau(a, b)[0])
    top_mine = [(r["design_hash"], r["target_key"]) for r in u_mine[:TOP_N]]
    top_base = [(r["design_hash"], r["target_key"]) for r in u_base[:TOP_N]]
    union = sorted(set(top_mine) | set(top_base))
    tau_top = float("nan")
    if len(union) >= 2:
        a = np.array([keyed_mine[k] for k in union if k in keyed_mine], dtype=float)
        b = np.array([keyed_base[k] for k in union if k in keyed_base], dtype=float)
        if a.size == b.size and a.size >= 2 and len(set(a.tolist())) > 1 \
                and len(set(b.tolist())) > 1:
            tau_top = float(kendalltau(a, b)[0])
    return {
        "n_shared": len(shared),
        "n_rankable": len(rankable),
        "kendall_tau": tau,
        "top20_overlap": len(set(top_mine) & set(top_base)),
        "kendall_tau_top20_union": tau_top,
        "top20_mine": [k[0] for k in top_mine],
        "top20_base": [k[0] for k in top_base],
        "penalty_mine": sum(1 for r in u_mine if r[mine_key] >= r67.PENALTY_FLOOR),
        "penalty_base": sum(1 for r in u_base if r[base_key] >= r67.PENALTY_FLOOR),
    }


def analyse(rows: list[dict], tolerances_by_class: dict, weights: dict | None = None) -> dict:
    """Per class: v8 J for every row (with per-class tolerances) and every pair's stats."""
    out: dict = {}
    for cls in CLASSES:
        subset = [r for r in rows if r["class"] == cls]
        if not subset:
            continue
        tol = tolerances_by_class[cls]["tolerances"]
        for r in subset:
            r["J_v8"] = j_v8(r, tol, weights)
        gate_rows = [r for r in subset if r["v8_gate_failed"]]
        reasons: dict[str, int] = {}
        for r in gate_rows:
            key = (r["v8_gate_reason"] or "").split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1
        out[cls] = {
            "rows": len(subset),
            "unique_designs": len({(r["design_hash"], r["target_key"]) for r in subset}),
            "v8_gate_refusals": {"rows": len(gate_rows),
                                 "unique": len({(r["design_hash"], r["target_key"])
                                                for r in gate_rows}),
                                 "by_reason": dict(sorted(reasons.items()))},
            "pairs": {base: pair_stats(subset, "J_v8", f"J_v{base}") for base in (4, 6, 7)},
        }
    return out


# ------------------------------------------------------------------ output


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def write_summary_json(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(summary), indent=2, sort_keys=True), encoding="utf-8")


def _fmt(x, digits: int = 4) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    return f"{v:.{digits}f}" if math.isfinite(v) else "n/a"


def write_markdown(path: Path, summary: dict, briefs: dict, tolerances: dict) -> None:
    lines: list[str] = []
    lines.append("# Objective v8 offline re-score (proposal — owner sign-off required)")
    lines.append("")
    lines.append("Generated by `tools/analysis/v8_rescore.py` from the committed dataset shards "
                 "(`shard-*.jsonl` + `shard-NNNN/rec-NNNN.npz`). Zero GPU, zero solver; "
                 "`dataset/` is read-only and outputs go to the `--out` folder only.")
    lines.append("")
    lines.append("- v4 briefs: " + ", ".join(f"{c}={briefs[4][c].name}" for c in CLASSES))
    lines.append("- v6 brief: " + briefs[6]["A"].name + " (the only shipped v6 brief; every class)")
    lines.append("- v7 briefs: " + ", ".join(f"{c}={briefs[7][c].name}" for c in CLASSES))
    lines.append("- v8: default v8 weights, per-class calibrated tolerances, hard-refusal gates "
                 "(loading/f11 on loading-scored targets; the round-throat gate is NOT applied "
                 "here — the dataset stores no mesh, in-search enforcement stays with C4).")
    lines.append("")
    c = summary["counters"]
    lines.append(f"- Rows seen **{c.get('rows_seen', 0)}**, scored **{c.get('scored', 0)}** "
                 f"(target_invalid {c.get('target_invalid', 0)}, parse_failed "
                 f"{c.get('parse_failed', 0)}, scoring_error {c.get('scoring_error', 0)})")
    lines.append("")
    lines.append("## Calibrated v8 tolerances (per class)")
    lines.append("")
    lines.append("tolerance = median raw-unit value of the term over the top decile "
                 "(`max(3, ceil(n/10))` rows) of the class's stored valid rows ranked under the "
                 "class-matched v4 brief.")
    lines.append("")
    for cls in CLASSES:
        cal = tolerances.get(cls)
        if not cal:
            continue
        lines.append(f"### Class {cls} — {cal['n_valid']} rankable rows, top decile "
                     f"= {cal['n_top']} rows")
        lines.append("")
        lines.append("| term | tolerance (median) | p10 | p90 | n raw |")
        lines.append("|---|---:|---:|---:|---:|")
        for k in V8_WEIGHTED_KEYS:
            st = cal["raw_stats"][k]
            lines.append(f"| `{k}` | {st['median']:.4g} | {st['p10']:.4g} | {st['p90']:.4g} "
                         f"| {st['n_raw']} |")
        lines.append("")
    lines.append("## v8 vs v4 / v6 / v7 — per brief class")
    lines.append("")
    lines.append("Tau is Kendall's tau between the two rankings over every shared unique "
                 "(design, target) key with BOTH scores below the 1e3 penalty floor "
                 "(v8 refusals are hard refusals, not ranks). `top20 overlap` counts the shared "
                 "entries of the two top-20 shortlists; the union tau pairs the two rankings on "
                 "the union of the two top-20 sets.")
    lines.append("")
    for cls in CLASSES:
        block = summary["classes"].get(cls)
        if not block:
            continue
        lines.append(f"### Class {cls} — {block['rows']} rows, {block['unique_designs']} "
                     "unique (design, target)")
        lines.append("")
        g = block["v8_gate_refusals"]
        lines.append(f"- v8 hard-refusal gate rows: **{g['rows']}** "
                     f"({g['unique']} unique); by reason: {g['by_reason'] or '{}'}")
        lines.append("")
        lines.append("| pair | shared | rankable | Kendall tau | top-20 overlap | tau (top-20 union) "
                     "| penalty rows (v8 / base) |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for base in (4, 6, 7):
            p = block["pairs"][base]
            lines.append(f"| v8 vs v{base} | {p['n_shared']} | {p['n_rankable']} | "
                         f"{_fmt(p['kendall_tau'])} | {p['top20_overlap']} / {TOP_N} | "
                         f"{_fmt(p['kendall_tau_top20_union'])} | "
                         f"{p['penalty_mine']} / {p['penalty_base']} |")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ CLI


def run(dataset_root: Path, out_dir: Path, limit: int | None = None) -> dict:
    briefs = brief_configs()
    collected = collect_rows(dataset_root, briefs, limit=limit)
    rows = collected["rows"]
    tolerances = calibrate_all(rows)
    classes = analyse(rows, tolerances)
    summary = {
        "counters": {k: collected["counters"].get(k, 0) for k in sorted(collected["counters"])},
        "briefs": {str(v): {c: b.name for c, b in briefs[v].items()} for v in (4, 6, 7)},
        "calibration": tolerances,
        "classes": classes,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_summary_json(out_dir / "v8_rescore.json", summary)
    write_markdown(out_dir / "v8_rescore.md", summary, briefs, tolerances)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Offline objective v8 re-score + "
                                             "tolerance calibration (no GPU, no solver)")
    ap.add_argument("--dataset", type=Path, default=REPO_ROOT / "dataset")
    ap.add_argument("--out", type=Path, default=OUT_DIR_DEFAULT,
                    help="output directory (default: scratch/objective_v8_2026-11-12; never "
                         "inside dataset/ or runs/)")
    ap.add_argument("--limit", type=int, default=None,
                    help="optional max scored rows (for a quick smoke run)")
    args = ap.parse_args(argv)
    if not args.dataset.is_dir():
        print(f"error: --dataset {args.dataset} is not a directory", file=sys.stderr)
        return 2
    summary = run(args.dataset, args.out, limit=args.limit)
    print(f"wrote {args.out / 'v8_rescore.json'} and {args.out / 'v8_rescore.md'}")
    print("CALIBRATION " + json.dumps(
        {cls: tolerances["tolerances"] for cls, tolerances in summary["calibration"].items()},
        sort_keys=True))
    per_class: dict = {}
    for cls, block in summary["classes"].items():
        per_class[cls] = {"refusals": block["v8_gate_refusals"]["rows"]}
        for base in (4, 6, 7):
            per_class[cls][f"tau_vs_v{base}"] = block["pairs"][base]["kendall_tau"]
            per_class[cls][f"top20_vs_v{base}"] = block["pairs"][base]["top20_overlap"]
    print("SUMMARY " + json.dumps(_clean(per_class), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
