"""Generate Morph / guiding-curve SEARCH variants of every typology that can take them.

Owner ask (2026-10-26): "make these part of the optimization search for all the typologies
that we can do this on". The shipped configs are left untouched (their config_sha, cached
results and resumes stay valid); each capable base gets sibling configs under
``examples/typologies/shape_variants/``:

* ``<base>__morph``  - Ath Morph searched (width, height, corner, rate, fixed part); the target
  shape is PINNED (a categorical gene is not searched: measured 2026-10-26, CMA-ES flips a rounded
  target 15.8 % of steps): a RECTANGLE on OSSE / R-OSSE / ICW, a SUPERELLIPSE (exponent searched,
  2.5..6) on FREEFORM bases, whose mesher refuses a rectangle target on an elliptical base as
  non-convex (measured on TwinRay and biradial). Shrinking is allowed, so a narrower target bites.
* ``<base>__gcurve`` - OSSE only: the OS-SE superformula guiding curve searched (width,
  height/width, position along the length, n1, n2, n3; lobes m1 = m2 = 4, a = b = 1, rotation 0
  pinned) PLUS the rectangle Morph above. This is the CORE / TwinRay crease class. The mesher
  requires a circular cross-section with a guiding curve, so ``exponent`` / ``aspect_ratio`` are
  pinned at 2 / 1 (the curve's own height/width shapes the outline instead).

Search boxes are centred on the base seed's MEASURED mouth (the sandbox preview), not invented:
width/height +-30 %, curve width +-30 %, curve height/width +-40 % around the mouth's H/W.
Every variant is then checked: the seed must preview AND mesh (the real dry-run), and an LHS of
``--lhs`` points inside the new box must preview; the measured invalid fraction is recorded in
the variant's header and in ``shape_variants/VARIANTS.md``. A variant whose seed does not mesh is
NOT written (reported instead).

Usage:
    .venv\\Scripts\\python.exe tools\\make_shape_variants.py            # write + check all
    .venv\\Scripts\\python.exe tools\\make_shape_variants.py --only osse_baseline --lhs 24
    .venv\\Scripts\\python.exe tools\\make_shape_variants.py --dry-run  # report, write nothing
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hornlab_search.gui import data as D  # noqa: E402

OUT_DIR = ROOT / "examples" / "typologies" / "shape_variants"
# legacy / duplicate / symmetry-check configs are not typologies to search
SKIP = {"search_smoke", "throat_adapter", "freeform_sculpt_symcheck_full",
        "freeform_sculpt_symcheck_quarter", "osse_baseline_fusedcuda", "osse_axi_fusedcuda",
        "freeform_sculpt_fusedcuda", "perturbed_osse_hv_fusedcuda"}
# variants run on the campaign's fused-CUDA settings: a Morph / guiding-curve wall has more area
FUSED_MESH = {"dof_cap_screen": 12000, "dof_cap_verify": 12000, "dof_cap_final": 12000}


def _r(x: float, nd: int = 3) -> float:
    return float(round(float(x), nd))


def _box(seed: float, rel: float, lo_floor: float | None = None, hi_cap: float | None = None) -> dict:
    lo, hi = seed * (1.0 - rel), seed * (1.0 + rel)
    if lo_floor is not None:
        lo = max(lo, lo_floor)
    if hi_cap is not None:
        hi = min(hi, hi_cap)
    return {"lo": _r(lo, 1), "hi": _r(hi, 1)}


def _seed_dims(cfg_entry: dict) -> dict | None:
    out = D.preview_shape(ROOT, cfg_entry["name"], {"detail": ["2d"]})
    return out.get("dims") if out.get("available") else None


def _morph_rows(dims: dict, family: str) -> tuple[dict, dict]:
    w, h = float(dims["w"]), float(dims["h"])
    superellipse = family == "FREEFORM"
    seed = {"morph_target": 3 if superellipse else 1, "morph_allow_shrinkage": 1,
            "morph_exponent": 4.0, "morph_width_mm": _r(w, 1), "morph_height_mm": _r(h, 1),
            "morph_corner_mm": 20.0, "morph_rate": 3.0, "morph_fixed": 0.0}
    pinned = ["morph_target", "morph_allow_shrinkage"] + (["morph_corner_mm"] if superellipse
                                                           else ["morph_exponent"])
    bounds = {k: {"lo": seed[k], "hi": seed[k], "search": False} for k in pinned}
    bounds.update({
        "morph_width_mm": _box(w, 0.30, lo_floor=40.0),
        "morph_height_mm": _box(h, 0.30, lo_floor=40.0),
        "morph_rate": {"lo": 1.0, "hi": 6.0},
        "morph_fixed": {"lo": 0.0, "hi": 0.3},
    })
    if superellipse:
        bounds["morph_exponent"] = {"lo": 2.5, "hi": 6.0}
    else:
        bounds["morph_corner_mm"] = {"lo": 3.0, "hi": 60.0}
    return seed, bounds


def _gcurve_rows(dims: dict) -> tuple[dict, dict]:
    w, h = float(dims["w"]), float(dims["h"])
    ar = h / w if w > 0 else 1.0
    seed = {"gcurve_type": 2, "gcurve_width_mm": _r(w, 1), "gcurve_aspect_ratio": _r(ar),
            "gcurve_dist": 0.6, "gcurve_rot_deg": 0.0, "gcurve_sf_a": 1.0, "gcurve_sf_b": 1.0,
            "gcurve_sf_m1": 4.0, "gcurve_sf_m2": 4.0, "gcurve_sf_n1": 1.0, "gcurve_sf_n2": 1.0,
            "gcurve_sf_n3": 1.0}
    pinned = ("gcurve_type", "gcurve_rot_deg", "gcurve_sf_a", "gcurve_sf_b", "gcurve_sf_m1",
              "gcurve_sf_m2")
    bounds = {k: {"lo": seed[k], "hi": seed[k], "search": False} for k in pinned}
    bounds.update({
        "gcurve_width_mm": _box(w, 0.30, lo_floor=40.0),
        "gcurve_aspect_ratio": {"lo": _r(ar * 0.6), "hi": _r(ar * 1.4)},
        "gcurve_dist": {"lo": 0.35, "hi": 0.9},
        "gcurve_sf_n1": {"lo": 0.3, "hi": 4.0},
        "gcurve_sf_n2": {"lo": 0.5, "hi": 8.0},
        "gcurve_sf_n3": {"lo": 0.5, "hi": 8.0},
    })
    return seed, bounds


def _variant_raw(base_raw: dict, base_path: Path, kind: str, dims: dict) -> dict:
    raw = copy.deepcopy(base_raw)
    seeds = raw.setdefault("seed_params", {})
    bounds = raw.setdefault("bounds", {})
    if kind == "gcurve":
        for k, v in (("exponent", 2.0), ("aspect_ratio", 1.0)):     # the mesher's gcurve rule
            seeds[k] = v
            bounds[k] = {"lo": v, "hi": v, "search": False}
        s, b = _gcurve_rows(dims)
        seeds.update(s)
        bounds.update(b)
    s, b = _morph_rows(dims, str(raw.get("family", "")))
    seeds.update(s)
    bounds.update(b)
    raw.setdefault("mesh", {}).update(FUSED_MESH)
    solve = raw.setdefault("solve", {})
    if str(solve.get("backend", "beat_cuda")) == "beat_cuda":
        solve["cuda_fused"] = True
    raw["name"] = f"{base_raw.get('name') or base_path.stem}__{kind}"
    if raw.get("brief_file"):                                      # re-root the relative path
        raw["brief_file"] = Path(
            __import__("os").path.relpath((base_path.parent / raw["brief_file"]).resolve(), OUT_DIR)
        ).as_posix()
    n = sum(1 for v in bounds.values() if isinstance(v, dict) and v.get("search", True))
    search = raw.setdefault("search", {})
    search["budget"] = max(int(search.get("budget") or 0), 12 * n)
    return raw


def _lhs_invalid(name: str, bounds: dict, keys: list[str], n: int, seed: int = 7) -> tuple[int, int, list]:
    rng = np.random.default_rng(seed)
    bad, reasons = 0, []
    for i in range(n):
        knobs = {}
        for k in keys:
            lo, hi = float(bounds[k]["lo"]), float(bounds[k]["hi"])
            knobs[k] = lo + (hi - lo) * (i + rng.random()) / n
        out = D.preview_shape(ROOT, name, {"detail": ["2d"], "knobs": [json.dumps(knobs)]})
        if not out.get("available") or out.get("rejected"):
            bad += 1
            reasons.append(((out.get("rejected") or out.get("notes") or ["?"])[0])[:120])
    return bad, n, reasons


def _dry_run(path: Path) -> tuple[bool, str]:
    exe = ROOT / ".venv" / "Scripts" / "hornlab-search.exe"
    r = subprocess.run([str(exe), "run", "--config", str(path), "--mode", "screen", "--dry-run"],
                       capture_output=True, text=True, cwd=ROOT, timeout=900)
    text = (r.stdout + r.stderr).strip().splitlines()
    tail = next((ln for ln in reversed(text) if "dof" in ln or "FAIL" in ln or "error" in ln.lower()),
                text[-1] if text else "")
    return r.returncode == 0, tail.strip()[:200]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", help="base config name (repeatable)")
    ap.add_argument("--lhs", type=int, default=16, help="LHS preview points per variant box")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = ["# Shape variants (generated by tools/make_shape_variants.py)", "",
              "| variant | base | new searched knobs | seed mesh | LHS invalid | note |",
              "|---|---|---|---|---|---|"]
    for c in D.list_configs(ROOT):
        if "shape_variants" in c["path"] or "campaign_" in c["path"] or c["name"] in SKIP:
            continue
        if args.only and c["name"] not in args.only:
            continue
        kinds = (["morph"] if c.get("morph_capable") else []) + (["gcurve"] if c.get("gcurve_capable") else [])
        if not kinds:
            continue
        base_path = ROOT / c["path"]
        base_raw = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
        if any(k.startswith("morph_") for k in (base_raw.get("bounds") or {})):
            kinds = [k for k in kinds if k != "morph"]           # already searches Morph (ath_core)
        dims = _seed_dims(c)
        if not dims:
            report.append(f"| - | {c['name']} | - | base seed does not preview | - | skipped |")
            continue
        for kind in kinds:
            raw = _variant_raw(base_raw, base_path, kind, dims)
            path = OUT_DIR / f"{raw['name']}.yaml"
            new_keys = [k for k, b in raw["bounds"].items()
                        if (k.startswith("morph_") or k.startswith("gcurve_")) and b.get("search", True)]
            header = (f"# GENERATED by tools/make_shape_variants.py from {c['path']} ({kind} variant).\n"
                      f"# Base seed mouth (measured): {dims['w']} x {dims['h']} mm, depth {dims['d']} mm.\n"
                      "# Regenerate rather than hand-edit; the base config is untouched.\n")
            text = header + yaml.safe_dump(raw, sort_keys=False)
            if args.dry_run:
                report.append(f"| {raw['name']} | {c['name']} | {', '.join(new_keys)} | (dry-run) | - | - |")
                continue
            path.write_text(text, encoding="utf-8")
            D._PREVIEW_CONFIG_CACHE.clear()
            ok, tail = _dry_run(path)
            if not ok:
                path.unlink()
                D._PREVIEW_CONFIG_CACHE.clear()
                report.append(f"| ~~{raw['name']}~~ | {c['name']} | {', '.join(new_keys)} | FAILS | - | not written: {tail} |")
                print(f"DROP {raw['name']}: {tail}")
                continue
            bad, n, reasons = _lhs_invalid(raw["name"], raw["bounds"], new_keys, args.lhs)
            common = max(set(reasons), key=reasons.count) if reasons else ""
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"# check: seed meshes ({tail}); LHS {bad}/{n} new-knob points refused"
                         + (f" (commonest: {common})" if common else "") + "\n")
            report.append(f"| {raw['name']} | {c['name']} | {', '.join(new_keys)} | ok | {bad}/{n} | {common} |")
            print(f"OK   {raw['name']}: {tail}; LHS {bad}/{n} refused")
    if not args.dry_run:
        (OUT_DIR / "VARIANTS.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
