"""R3: corridor re-rank. Read-only. Writes CORRIDOR_RERANK.md + candidate YAMLs."""
from __future__ import annotations

import dataclasses
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import yaml
from scipy.stats import spearmanr

sys.path.insert(0, r"C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp")
import fable_replay_harness as H
from hornlab_search.objective.scalar_v9 import V9Params, objective_v9
from hornlab_search.targets.spec import Target

REPO = H.REPO
BASE = REPO / "scratch" / "fable_architecture"
OUT = BASE / "CORRIDOR_RERANK.md"
CANDS = BASE / ".tmp" / "v9_candidates"
RESULTS = BASE / ".tmp" / "r3_results.json"


def head_sha():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def make_candidate(onset: int):
    b = H.landscape_brief()
    target = {f.name: getattr(b.target, f.name) for f in dataclasses.fields(b.target)
              if not f.name.startswith("coverage_profile_")}
    target["coverage_profile"] = {
        "mode": "corridor",
        "interpolation": "log_frequency",
        "h": [{"hz": 700, "preferred_deg": 80, "min_deg": 60, "max_deg": 90},
              {"hz": 8000, "preferred_deg": 80, "min_deg": 60, "max_deg": 90}],
        "v": [{"hz": onset, "preferred_deg": 50, "min_deg": 40, "max_deg": 60},
              {"hz": 8000, "preferred_deg": 50, "min_deg": 40, "max_deg": 60}],
    }
    objective = {
        "version": 9,
        "tolerances": {"cov_profile": 3.0, "rip": 1.0, "flat": 1.5, "load": 0.3,
                       "dislope": 9.0, "di_roughness": 1.0, "flat_cv": 1.5},
        "cov_narrow_ratio": 2.0, "cov_below_f0": "one_sided", "cov_v_weight": 0.5,
        "flat_band": "scored", "loaded_re_z": 0.5, "lfp_re_z": 0.2,
        "lfp_crossover_ratio": 1.6,
    }
    weights = {"cov_profile": 1.0, "rip": 1.0, "flat": 0.5, "load": 1.0,
               "dislope": 1.0, "di_roughness": 1.0, "flat_cv": 1.0}
    return {"_placeholder": "candidate v9 coverage_profile awaiting the owner's choice; "
                             "scratch only, not a shipped brief",
            "name": f"placeholder_v9_v_onset_{onset}",
            "target": target, "objective": objective, "weights": weights}


def rank_rows(rows, key):
    return sorted([r for r in rows if r.get(key) is not None and np.isfinite(r[key])],
                  key=lambda r: r[key])


def metrics_from_json(payload):
    """Stored metrics.json -> MetricSet (the stored DI is already sin-theta exact)."""
    from hornlab_search.types import MetricSet
    f = np.asarray(payload["freqs_hz"], float)
    n = f.size

    def arr(name):
        raw = payload.get(name)
        if raw is None:
            return np.full(n, np.nan)
        return np.array([np.nan if v is None else v for v in raw], float)

    z = arr("z_throat_real") if payload.get("z_throat_real") is not None else None
    return MetricSet(freqs_hz=f, bw_h_deg=arr("bw_h_deg"), bw_v_deg=arr("bw_v_deg"),
                     di_db=arr("di_db"), di_source=str(payload.get("di_source")
                                                         or (payload.get("scalars") or {}).get("di_source")
                                                         or "balloon"),
                     ripple_h_db=arr("ripple_h_db"), ripple_v_db=arr("ripple_v_db"),
                     on_axis_db=arr("on_axis_db"), z_throat_real=z,
                     scalars=dict(payload.get("scalars") or {}))


def run_design_dir(run_dir, design_hash):
    d = pathlib.Path(run_dir) / "designs" / design_hash
    if not d.is_dir():
        d = pathlib.Path(run_dir) / "verify" / "designs" / design_hash
    return d


def main():
    t0 = time.time()
    sha = head_sha()
    CANDS.mkdir(parents=True, exist_ok=True)
    cand_meta = {}
    for onset in (700, 1000, 1250):
        p = CANDS / f"candidate_v_onset_{onset}.yaml"
        p.write_text(yaml.safe_dump(make_candidate(onset), sort_keys=False), encoding="utf-8")
        c = yaml.safe_load(p.read_text(encoding="utf-8"))
        cand_meta[onset] = dict(path=p, target=Target.from_dict(c["target"]),
                                params=V9Params.from_block(c["objective"]),
                                weights=c["weights"])

    b7 = H.landscape_brief()
    runs = H.load_landscape_runs()
    rows = []
    cache = {}
    total = 0
    for rd in runs:
        cfg_name = str(rd["cfg"].get("name"))
        for r in rd["rows"]:
            if not (r.get("ok") and isinstance(r.get("objective"), (int, float))):
                continue
            total += 1
            h = r.get("design_hash")
            ck = (rd["dir"].name, h)
            try:
                if ck not in cache:
                    d = run_design_dir(rd["dir"], h)
                    payload = H.json_load(d / "metrics.json")
                    resp = H.load_response(d / "response.npz")
                    cache[ck] = (resp, metrics_from_json(payload))
                resp, m = cache[ck]
                j7, t7 = H.score_v7(m, resp, b7.target, b7.weights, b7.objective_params)
                rec = dict(run=rd["dir"].name, config=cfg_name, design=h, n=r.get("n"),
                           j7=j7, j={}, penalty={})
                for onset, cm in cand_meta.items():
                    j9, t9 = objective_v9(m, resp, True, cm["target"], cm["weights"], cm["params"])
                    rec["j"][onset] = j9
                    rec["penalty"][onset] = bool(t9.get("penalty", 0.0) > 0.0)
                rows.append(rec)
            except Exception as e:
                rows.append(dict(run=rd["dir"].name, config=cfg_name, design=h, n=r.get("n"),
                                 j7=None, j={}, penalty={}, error=repr(e)[:120]))
            if total % 500 == 0:
                print(f"scored {total} ok rows, cached {len(cache)}", flush=True)
    print("ok rows total", total, "records", len(rows), flush=True)

    # dedupe exact duplicate rows within a run? keep every row (the request says every row)
    v7_sorted = rank_rows(rows, "j7")
    v7_top20 = v7_sorted[:20]
    v7_top100 = v7_sorted[:100]
    v7_top100_ids = {(r["run"], r["n"]) for r in v7_top100}

    def row_id(r):
        return f"`{r['run']}` #{r['n']} `{r['design']}` ({r['config']})"

    summary = {}
    for onset in (700, 1000, 1250):
        cand = rank_rows([{**r, "jc": r["j"].get(onset)} for r in rows], "jc")
        top20 = cand[:20]
        ids20 = {(r["run"], r["n"]) for r in top20}
        overlap = len({(r["run"], r["n"]) for r in v7_top20} & ids20)
        cand_by_id = {(r["run"], r["n"]): r for r in cand}
        common = [r for r in v7_top100 if (r["run"], r["n"]) in cand_by_id]
        rho = spearmanr([r["j7"] for r in common], [cand_by_id[(r["run"], r["n"])]["jc"] for r in common])[0]
        # best row per config
        cfg7, cfgc = {}, {}
        for r in v7_sorted:
            cfg7.setdefault(r["config"], r)
        for r in cand:
            cfgc.setdefault(r["config"], r)
        cfg_rank7 = {c: i + 1 for i, c in enumerate(sorted(cfg7, key=lambda c: cfg7[c]["j7"]))}
        cfg_rankc = {c: i + 1 for i, c in enumerate(sorted(cfgc, key=lambda c: cfgc[c]["jc"]))}
        moved = [(c, cfg_rank7[c], cfg_rankc[c]) for c in cfg7
                 if abs(cfg_rank7[c] - cfg_rankc[c]) > 3]
        summary[onset] = dict(overlap=overlap, rho=float(rho),
                              top20=cand[:20], top20_ids=ids20, cfg7=cfg7, cfgc=cfgc,
                              cfg_rank7=cfg_rank7, cfg_rankc=cfg_rankc, moved=moved,
                              n_penalty=sum(1 for r in rows if r.get("penalty", {}).get(onset)),
                              n_valid=len(cand))

    lines = []
    lines.append("# CORRIDOR_RERANK")
    lines.append("")
    lines.append(f"- Repo HEAD at run: `{sha}`")
    lines.append(f"- Timestamp: `{time.strftime('%Y-%m-%dT%H:%M:%S%z')}`")
    lines.append("- Read-only against `runs/`; no solve, mesher, GPU, queue or config write.")
    lines.append(f"- Scope: **{total}** ok rows from **{len(runs)}** landscape runs / "
                 f"**{len(set(r['config'] for r in rows))}** configs (80x50, 600x480x480, 2026-11-15 onward).")
    lines.append(f"- v7 baseline: the standard landscape brief `{b7.name}` applied to every row "
                 "(not each row's own variant), metrics regenerated with the parity-exact sin-theta DI rule.")
    lines.append("- v9 candidates are **placeholders awaiting the owner's choice**; they live under "
                 "`.tmp/v9_candidates/`, not `examples/`. Only the V onset differs (700 / 1,000 / 1,250 Hz); "
                 "H is 60-90 deg from 700 Hz in all three. `cov_below_f0: one_sided` means a wide pattern "
                 "below onset is free while a narrow one is charged.")
    lines.append("- v9 J is **not numerically comparable** to v7 J: the term sets differ "
                 "(v9 drops weighted `di`/`distd`, adds `di_roughness`, and scores a corridor). "
                 "Only ranks and overlaps are compared.")
    lines.append("")
    lines.append("## Top-20 overlap with v7")
    lines.append("")
    lines.append("| candidate | rows valid | top-20 overlap | Spearman within v7 top 100 | v9-penalised rows |")
    lines.append("|---|---|---|---|---|")
    for onset in (700, 1000, 1250):
        s = summary[onset]
        lines.append(f"| V onset {onset} Hz | {s['n_valid']} | {s['overlap']}/20 | {s['rho']:.3f} | {s['n_penalty']} |")
    lines.append("")
    for onset in (700, 1000, 1250):
        s = summary[onset]
        lines.append(f"### Candidate V onset {onset} Hz")
        lines.append("")
        lines.append("Top 20 under the candidate (v7 rank in brackets):")
        lines.append("")
        lines.append("| # | row | J v9 | J v7 | v7 rank |")
        lines.append("|---|---|---|---|---|")
        v7rank = {(r["run"], r["n"]): i + 1 for i, r in enumerate(v7_sorted)}
        for i, r in enumerate(s["top20"], 1):
            lines.append(f"| {i} | {row_id(r)} | {r['jc']:.3f} | {r['j7']:.3f} | "
                         f"{v7rank.get((r['run'], r['n']), '>20')} |")
        lines.append("")
        lines.append("Configs moving more than three places (by best row per config):")
        lines.append("")
        if s["moved"]:
            lines.append("| config | v7 rank | candidate rank | move |")
            lines.append("|---|---|---|---|")
            for c, a, b in sorted(s["moved"], key=lambda x: -abs(x[1] - x[2])):
                lines.append(f"| `{c}` | {a} | {b} | {b-a:+d} |")
        else:
            lines.append("None.")
        lines.append("")
    lines.append("## Best row per config")
    lines.append("")
    lines.append("| config | v7 best J | v700 best J | v1000 best J | v1250 best J |")
    lines.append("|---|---|---|---|---|")
    for c in sorted(summary[700]["cfg7"]):
        r7 = summary[700]["cfg7"].get(c)
        vals = []
        for onset in (700, 1000, 1250):
            rc = summary[onset]["cfgc"].get(c)
            vals.append("n/a" if rc is None else f"{rc['jc']:.3f}")
        lines.append(f"| `{c}` | {r7['j7']:.3f} | " + " | ".join(vals) + " |")
    lines.append("")
    lines.append("## Candidate files")
    lines.append("")
    for onset in (700, 1000, 1250):
        lines.append(f"- `{cand_meta[onset]['path'].relative_to(REPO).as_posix()}`")
    lines.append("")
    lines.append(f"_Script: `scratch/fable_architecture/.tmp/r3_corridor_rerank.py`; runtime "
                 f"{time.time()-t0:.1f}s._")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    RESULTS.write_text(json.dumps([{k: v for k, v in r.items() if k != "j"} | {"j": r.get("j", {})}
                                   for r in rows], indent=0), encoding="utf-8")
    print("wrote", OUT)
    for onset in (700, 1000, 1250):
        s = summary[onset]
        print("onset", onset, "overlap", s["overlap"], "rho %.3f" % s["rho"],
              "moved", len(s["moved"]), "penalty", s["n_penalty"])


if __name__ == "__main__":
    main()
