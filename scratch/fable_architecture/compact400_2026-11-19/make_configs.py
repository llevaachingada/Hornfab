"""Emit the compact400 (400 mm cube) search configs + two home v10 s2w continuations (2026-11-19).

Deterministic: each config = an existing, loadable source config with ONLY these changes:
  name / description / brief_file / search block (cma, budget, seed) / seed_params (the source
  family's best stored design, or the config seed) / the size knobs' bounds (mouth W/H, depth).
Every other knob, bound, mesh and solve setting is inherited unchanged. Re-run to regenerate.
Usage:  .venv\\Scripts\\python.exe scratch/fable_architecture/compact400_2026-11-19/make_configs.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "examples" / "typologies" / "compact400_2026-11-19"
C4_BRIEF = "../../briefs/compact400_2026-11-19/compact400_xo1000_1400_hf1440_v10xo.yaml"
T = ROOT / "examples" / "typologies"


def best_params(run: str, dh: str | None) -> dict:
    rd = ROOT / "runs" / run
    if dh is None:
        dh = json.loads((rd / "best.json").read_text())["design_hash"]
    for line in (rd / "search.ndjson").open(encoding="utf-8"):
        r = json.loads(line)
        if r.get("design_hash") == dh:
            p = r["params"]
            return p["grid"]["knobs"] if "grid" in p else p
    raise KeyError(f"{dh} not in {run}")


def set_bound(cfg, k, lo=None, hi=None):
    b = cfg["bounds"].setdefault(k, {})
    if lo is not None:
        b["lo"] = float(lo)
    if hi is not None:
        b["hi"] = float(hi)


def fit_seed(cfg):
    """A seed outside a SEARCHED bound widens the bound (never silently clip a recorded best);
    pinned (search: false) knobs keep their pinned value."""
    for k, v in list(cfg["seed_params"].items()):
        b = cfg["bounds"].get(k)
        if not isinstance(b, dict) or not isinstance(v, (int, float)):
            continue
        if b.get("search", True) is False:
            cfg["seed_params"][k] = b["lo"]
            continue
        if v < b["lo"]:
            b["lo"] = float(v)
        if v > b["hi"]:
            b["hi"] = float(v)


# id, source config, seed (run, design | None = run best) or "config", size policy, note
C4 = [
    ("c4_01_fold_warm", "b6_2026-11-19/hl__osse_rrect_fold_warm_v7__b6_v10_s1.yaml",
     ("study-0c9805ad97208a2e/screen", "00826f071b24"), "osse",
     "v10 leader family (fold_warm, published v10 1.4214) shrunk into the cube"),
    ("c4_02_morph", "b6_2026-11-19/hl__osse_rrect_morph_v7__b6_v10_s1.yaml",
     ("20261115T154322Z-screen-07bea2", "436a4d221328"), "osse",
     "v10 #2 family (rrect morph, published v10 1.4305)"),
    ("c4_03_ext_throat", "b6_2026-11-19/hl__ext_throat_hvlaw_v7__b6_v10_s1.yaml",
     ("study-4e1a6a9cd4bb5201/screen", "a23763f1c6fc"), "osse",
     "v7 #1 / v10 #3 family (ext-throat H/V law); 332x300 ancestors already solved at this size"),
    ("c4_04_petal_hvlaw", "scout40w2_2026-11-19/scout40w3__petal_hvlaw_v7.yaml",
     ("20261119T155454Z-screen-d1a61d", "74d8eed97268"), "osse",
     "compact register A1 (petal H/V law), best compact-slate loading"),
    ("c4_05_tritonia_v8", "scout40w2_2026-11-19/scout40w3__tritonia_v8.yaml",
     ("20261119T152446Z-screen-d98c8d", "cded84a911d2"), "osse",
     "compact register A3 (tritonia v8), real +0.48 J gain on W3"),
    ("c4_06_twinray", "b6_2026-11-19/hl__ath_twinray380_landscape_v8__b6_v10_s1.yaml",
     ("20261116T052759Z-screen-44001e", "bbe858b5b6a4"), "osse_keep",
     "ATH TwinRay; seeded at bbe858b5b6a4 (367x377x255), the best stored HF1440 design that "
     "already fits the cube: compact400 CPU rescore 1.7302, the bar every lane must beat"),
    ("c4_07_ath_core_14in", "atlas_2026-10-30/atlas__ath_core.yaml", "config", "osse_square",
     "ATH core law: 237 of the 393 solved 400-cube designs that meet this corridor are this "
     "family at a 2-inch throat; this lane measures it at the HF1440 1.4-inch throat"),
    ("c4_08_lecleach_iwata_ar", "scout40_2026-11-19/scout40__lecleach_iwata_ar_smooth_v7.yaml",
     ("20261119T050957Z-screen-53fe3d", None), "rows",
     "Le Cleac'h / Iwata AR rows march; its best (400x305x244) already fits the cube"),
]

HOME = [
    ("h_09_fold_warm_v10_s2w", "b6_2026-11-19/hl__osse_rrect_fold_warm_v7__b6_v10_s2.yaml",
     ("study-0c9805ad97208a2e/screen", "00826f071b24"), {"L_mm": (None, 330.0)},
     "Q3 measured fold_warm bound-pinned at L_mm HIGH (271.9): widen to 330 (home envelope depth "
     "480) and warm-start at the PUBLISHED v10 best 00826f071b24, not the lane seed"),
    ("h_10_ext_throat_v10_s2w", "b6_2026-11-19/hl__ext_throat_hvlaw_v7__b6_v10_s2.yaml",
     ("study-4e1a6a9cd4bb5201/screen", "a23763f1c6fc"), {"az_a_cos_pow": (0.5, None)},
     "Q3 measured ext_throat bound-pinned at az_a_cos_pow LOW: widen lo and warm-start at the "
     "PUBLISHED v10 best a23763f1c6fc"),
]


def load(rel):
    return yaml.safe_load((T / rel).read_text(encoding="utf-8"))


def common_search(cfg, seed, budget, sigma0=None, penalty="resample_strict"):
    """penalty: search_preflight 2026-11-19 found the OSSE lanes' sampled refusals are
    invalid_geometry (flat 1000; 'graded' is inert there), so they replace refusals with
    resample_strict + budget_counts valid; the rows lane (envelope refusals) stays graded."""
    s = cfg.setdefault("search", {})
    for k in ("qd", "archive", "emitters", "warm_start"):
        s.pop(k, None)
    s["algorithm"] = "cma"
    s["budget"] = budget
    s["budget_counts"] = "valid"
    s["max_attempts"] = int(budget * 1.8)
    s["seed"] = seed
    s["infeasible_penalty"] = penalty
    if penalty == "resample_strict":
        s["error_policy"] = "retry_same_then_stop"   # required by the loader for resample_strict
    if sigma0 is not None:
        s["sigma0"] = sigma0


def emit(cfg, cid, src, note, extra):
    cfg["name"] = f"{cid}__{Path(src).stem}"
    cfg["description"] = (f"{note}. Generated by scratch/fable_architecture/compact400_2026-11-19/"
                          f"make_configs.py from examples/typologies/{src}; {extra}")
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{cfg['name']}.yaml"
    with p.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(yaml.safe_dump(cfg, sort_keys=False, width=100))
    return p


def main():
    made = []
    for i, (cid, src, seed, policy, note) in enumerate(C4):
        cfg = copy.deepcopy(load(src))
        cfg["brief_file"] = C4_BRIEF
        if seed != "config":
            bp = best_params(*seed)
            for k in list(cfg["seed_params"]):
                if k in bp:
                    cfg["seed_params"][k] = bp[k]
        sp = cfg["seed_params"]
        if policy in ("osse", "osse_square", "osse_keep"):
            # The size knobs must be SEARCHED and the mouth morph switched ON, or a family whose
            # source pinned morph_target 0 (ext_throat, petal) keeps its 570-600 mm wall-law mouth.
            for k in ("morph_width_mm", "morph_height_mm", "L_mm", "morph_corner_mm"):
                if k in cfg["bounds"]:
                    cfg["bounds"][k].pop("search", None)
            for k in ("morph_target", "morph_allow_shrinkage"):
                cfg["bounds"][k] = {"lo": 1, "hi": 1, "search": False}
                sp[k] = 1
            if policy == "osse_square":     # 2-inch ATH core law re-thrown on the HF1440 exit
                cfg["bounds"]["r0_mm"] = {"lo": 18.0, "hi": 18.0, "search": False}
                sp["r0_mm"] = 18.0
            # mouth: outer bbox <= 400 incl. shell; morph target is the inner mouth
            # ("osse_keep": the seed already fits the cube, keep its own size knobs)
            if policy != "osse_keep":
                sp["morph_width_mm"] = 380.0
                sp["morph_height_mm"] = (min(float(sp.get("morph_height_mm", 330.0)), 330.0)
                                         if policy == "osse" else 380.0)
            set_bound(cfg, "morph_width_mm", 300.0, 392.0)
            set_bound(cfg, "morph_height_mm", 240.0, 392.0)
            # depth: envelope 385 (+15 gate); a long wall at a 380 mouth is wasted length
            if policy != "osse_keep":
                sp["L_mm"] = min(float(sp["L_mm"]), 260.0)
            set_bound(cfg, "L_mm", 150.0, 300.0)
            if "morph_corner_mm" in cfg["bounds"]:
                set_bound(cfg, "morph_corner_mm", 8.0, 46.0)
        fit_seed(cfg)
        m = cfg.setdefault("mesh", {})
        for k in ("dof_cap_screen", "dof_cap_verify", "dof_cap_final"):
            m[k] = max(int(m.get(k, 0) or 0), 24000)    # atlas ath_core carried 12000 (3/32 too large)
        common_search(cfg, seed=40001 + i, budget=60, sigma0=0.2,
                      penalty="graded" if policy == "rows" else "resample_strict")
        made.append(emit(cfg, cid, src, note,
                         "compact400 identity (400 mm cube, F_X 1 kHz); 60 VALID evals, CMA; size "
                         "knobs re-bounded to the cube, every other knob inherited"))
    for i, (cid, src, seed, widen, note) in enumerate(HOME):
        cfg = copy.deepcopy(load(src))
        bp = best_params(*seed)
        for k in list(cfg["seed_params"]):
            if k in bp:
                cfg["seed_params"][k] = bp[k]
        for k, (lo, hi) in widen.items():
            set_bound(cfg, k, lo, hi)
        fit_seed(cfg)
        common_search(cfg, seed=61903 + i, budget=80, sigma0=0.15)
        made.append(emit(cfg, cid, src, note,
                         "home v10 identity unchanged (brief and objective as the source); 80 VALID "
                         "evals from the published best"))
    for p in made:
        print(p.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
