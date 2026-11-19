"""Score-term audit of the shipped v10 home brief (Fable senior, 2026-11-19). READ-ONLY, CPU-only.

Replays STORED responses through the canonical replay (hornlab_search.objective.replay); no BEM solve,
no mesher call, nothing under runs/ is written. Outputs go to --out (must be new or empty).

What it measures (see REPORT.md next to this file):
  A. term decomposition of the top-N-per-lane v10 designs under the shipped brief and three
     counterfactual briefs (dislope weight 0; ripple_region max_edge; both);
  B. a physical corridor-miss metric on the whole fleet (degrees outside H 60-90 from 700 Hz /
     V 40-60 from 1 kHz), from stored metrics.json;
  C. outermost vs main-lobe (first-crossing) beamwidth on the top-300 v10 designs;
  D. per-term attribution of the screen->verify J difference over the published v10 floor pairs.

Usage (from the canonical checkout):
  .venv\\Scripts\\python.exe scratch\\fable_architecture\\score_term_audit_2026-11-19\\score_term_audit.py ^
      --out runs\\analysis\\score_term_audit_2026-11-19 --topn 10
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from hornlab_search.metrics.acoustic_v2 import main_lobe  # noqa: E402
from hornlab_search.metrics.polar import beamwidth_deg  # noqa: E402
from hornlab_search.objective.replay import load_brief_context, replay_run_dir  # noqa: E402

SHIPPED = ROOT / "examples/briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml"
RESCORE = ROOT / "runs/analysis/v10_rescore_2026-11-18"
VARIANTS = ("shipped", "nodislope", "maxedge", "nodislope_maxedge")
TERMS = ("cov_profile", "rip", "dislope", "flat", "flat_cv", "load", "di_roughness")
DIR_TERMS = ("cov_profile", "rip", "dislope", "di_roughness")
LF_TERMS = ("load", "flat_cv", "flat")
H_CORR, H_ON = (60.0, 90.0), 700.0          # brief corridor values (read from the brief below)
V_CORR, V_ON = (40.0, 60.0), 1000.0


def write_variants(out: Path) -> dict:
    base = yaml.safe_load(SHIPPED.read_text(encoding="utf-8"))

    def mk(name, fn):
        d = yaml.safe_load(SHIPPED.read_text(encoding="utf-8"))
        fn(d)
        d["name"] = f"{base['name']}__audit_{name}"
        p = out / "briefs" / f"{name}.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
        return load_brief_context(p)

    return {
        "shipped": mk("shipped", lambda d: None),
        "nodislope": mk("nodislope", lambda d: d["weights"].__setitem__("dislope", 0.0)),
        "maxedge": mk("maxedge", lambda d: d["objective"].__setitem__("ripple_region", "max_edge")),
        "nodislope_maxedge": mk("nodislope_maxedge", lambda d: (
            d["weights"].__setitem__("dislope", 0.0),
            d["objective"].__setitem__("ripple_region", "max_edge"))),
    }


def index_design_dirs(hashes: set[str]) -> dict[str, list[Path]]:
    """design_hash -> run dirs holding designs/<hash>. The rescore rows store only the LEAF run
    name (e.g. "screen") for nested runs, so rows are resolved by hash (finding F8)."""
    loc: dict[str, list[Path]] = collections.defaultdict(list)
    for root, dirs, _files in os.walk(ROOT / "runs"):
        p = Path(root)
        if "analysis" in p.parts or "lanes" in p.parts:
            dirs[:] = []
            continue
        if p.name == "designs":
            for d in dirs:
                if d in hashes and (p / d / "metrics.json").exists():
                    loc[d].append(p.parent)
            dirs[:] = []
    return loc


def run_dir_for(row, loc) -> Path:
    """The row's own run when its "run" names a top-level dir holding the design; otherwise the
    unique (or first) dir whose leaf name equals the row's "run" (nested study-* runs, F8)."""
    h, name = row["design_hash"], row["run"]
    if row.get("run_path"):                      # rescore rows written after the F8 fix
        return ROOT / "runs" / row["run_path"]
    direct = ROOT / "runs" / name
    if (direct / "designs" / h).is_dir():
        return direct
    same_leaf = [p for p in loc[h] if p.name == name]
    return (same_leaf or loc[h])[0]


def fleet_rows():
    rows = [json.loads(line) for line in open(RESCORE / "v10/rescore.jsonl", encoding="utf-8")]
    v7 = {r["design_hash"]: r.get("j") for r in map(json.loads, open(RESCORE / "v7/rescore.jsonl", encoding="utf-8"))}
    return [r for r in rows if r["j"] is not None], v7


def part_a(rows, loc, briefs, topn):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["lane"]].append(r)
    out = []
    for lane, rs in by.items():
        for r in sorted(rs, key=lambda r: r["j"])[:topn]:
            run = run_dir_for(r, loc)
            rec = {"lane": lane, "design_hash": r["design_hash"], "run_dir": str(run.relative_to(ROOT)),
                   "ambiguous_dirs": len(loc[r["design_hash"]]), "j_fleet": r["j"]}
            for v, b in briefs.items():
                rr = replay_run_dir(run, r["design_hash"], brief=b, config_path=run / "config.yaml")
                rec[v] = {"j": rr.j, "terms": rr.terms, "w": rr.weights}
            out.append(rec)
    return out


def corridor_miss(M):
    f = np.asarray(M["freqs_hz"], float)
    bh, bv = np.asarray(M["bw_h_deg"], float), np.asarray(M["bw_v_deg"], float)
    hm, vm = (f >= H_ON) & (f <= 8000), (f >= V_ON) & (f <= 8000)
    eh = np.maximum(0, np.maximum(H_CORR[0] - bh[hm], bh[hm] - H_CORR[1]))
    ev = np.maximum(0, np.maximum(V_CORR[0] - bv[vm], bv[vm] - V_CORR[1]))
    return float(np.sqrt(np.mean(np.r_[eh, ev] ** 2))), float(eh.max()), float(ev.max())


def part_b(rows, v7, loc):
    out = []
    for r in rows:
        rd = run_dir_for(r, loc)
        M = json.load(open(rd / "designs" / r["design_hash"] / "metrics.json"))
        f, di = np.asarray(M["freqs_hz"], float), np.asarray(M["di_db"], float)
        s = f >= H_ON
        miss, hmax, vmax = corridor_miss(M)
        out.append({"lane": r["lane"], "design_hash": r["design_hash"], "run_dir": str(rd), "v10": r["j"],
                    "v7": v7.get(r["design_hash"]), "miss_rms_deg": miss, "h_max_deg": hmax,
                    "v_max_deg": vmax, "di_slope_db_dec_700_8k": float(np.polyfit(np.log10(f[s]), di[s], 1)[0])})
    return out


def part_c(b_rows, loc, n=300):
    top = sorted(b_rows, key=lambda r: r["v10"])[:n]
    acc = collections.defaultdict(list)
    for r in top:
        z = np.load(Path(r["run_dir"]) / "designs" / r["design_hash"] / "response.npz")
        for plane in ("h", "v"):
            a, S = z[f"{plane}_angles_deg"], z[f"spl_{plane}_db"]
            for i, fi in enumerate(z["freqs_hz"]):
                if fi < H_ON:
                    continue
                bo, _ = beamwidth_deg(a, S[i])
                ml = main_lobe(a, S[i])
                op = ml["outside_peak_db"]
                acc[(plane, round(float(fi)))].append((bo, ml["width_deg"], np.nan if op is None else op))
    return {f"{p}_{f}": {"median_outermost": float(np.nanmedian(np.array(v)[:, 0])),
                         "median_mainlobe": float(np.nanmedian(np.array(v)[:, 1])),
                         "frac_outer_minus_main_gt5": float(np.mean(np.array(v)[:, 0] - np.array(v)[:, 1] > 5)),
                         "frac_outside_peak_gt_m6db": float(np.nanmean(np.array(v)[:, 2] > -6)),
                         "n": len(v)} for (p, f), v in sorted(acc.items())}


def part_d(brief, n_top=28):
    pairs = [json.loads(line) for line in open(RESCORE / "floor_v10/floor_pairs.jsonl", encoding="utf-8")]
    rows = []
    for p in pairs:
        run = ROOT / "runs" / p["run"]
        try:
            a = replay_run_dir(run, p["design_hash"], brief=brief, config_path=run / "config.yaml")
            b = replay_run_dir(run / "verify", p["design_hash"], brief=brief, config_path=run / "config.yaml")
        except Exception:  # noqa: BLE001 - counted, never hidden
            rows.append(None)
            continue
        if a.j is None or b.j is None:
            rows.append(None)
            continue
        w = a.weights
        rows.append({"screen_j": a.j, "verify_j": b.j,
                     "d": {k: w[k] * (b.terms[k] - a.terms[k]) for k in TERMS}})
    ok = [r for r in rows if r is not None]
    out = {"pairs": len(pairs), "replayed": len(ok)}
    top = sorted(ok, key=lambda r: r["screen_j"])[:n_top]
    for lab, X in (("all", ok), (f"top{n_top}_by_screen_j", top)):
        dj = np.array([r["verify_j"] - r["screen_j"] for r in X])
        D = {k: np.array([r["d"][k] for r in X]) for k in TERMS}
        out[lab] = {"sd_dJ": float(dj.std()), "mean_dJ": float(dj.mean()),
                    "share_of_var": {k: float(np.cov(D[k], dj)[0, 1] / dj.var()) for k in TERMS},
                    "sd_dJ_directivity": float(sum(D[k] for k in DIR_TERMS).std()),
                    "sd_dJ_lf": float(sum(D[k] for k in LF_TERMS).std())}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--topn", type=int, default=10)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: {out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)

    briefs = write_variants(out)
    rows, v7 = fleet_rows()
    loc = index_design_dirs({r["design_hash"] for r in rows})
    missing = [r["design_hash"] for r in rows if r["design_hash"] not in loc]

    A = part_a(rows, loc, briefs, a.topn)
    parity = max(abs(r["shipped"]["j"] - r["j_fleet"]) for r in A)
    B = part_b([r for r in rows if r["design_hash"] in loc], v7, loc)
    C = part_c(B, loc)
    D = part_d(briefs["shipped"])

    for name, obj in (("A_terms_topn.json", A), ("B_corridor_miss_fleet.json", B),
                      ("C_beamwidth_definitions_top300.json", C), ("D_floor_attribution.json", D)):
        (out / name).write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")

    shares = collections.defaultdict(list)
    for r in A:
        for k in TERMS:
            shares[k].append(r["shipped"]["w"][k] * r["shipped"]["terms"][k])
    meanj = np.mean([r["shipped"]["j"] for r in A])
    summary = {"fleet_rows_scored": len(rows), "unlocatable": len(missing),
               "ambiguous_hashes": sum(len(v) > 1 for v in loc.values()),
               "A_n": len(A), "A_parity_max_abs_dJ_vs_fleet": parity,
               "A_mean_J": float(meanj),
               "A_term_share": {k: float(np.mean(v) / meanj) for k, v in shares.items()},
               "D": D}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
