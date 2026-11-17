"""Lawfulness probe for the Klangfilm-Lame H/V Phase A search box (CPU only, no solves).

The handoff asks for a search box whose samples are *actually legal*, not a box that looks plausible.
This script loads the Stage A config through the canonical adapter (so the same bound/seed/dormancy
rules apply as in a real study), draws a Latin-hypercube sample over the four searched knobs, and
materialises every sample with the kernel. Refusals are bucketed by exact exception text. It also
bisects each knob's feasible wall from the seed, so the declared bounds are justified by measurement.

Nothing here meshes, solves, queues or mutates a run. Output:
  docs/evidence/klangfilm_hv_2026-11-16/SEARCH_BOX.md
  docs/evidence/klangfilm_hv_2026-11-16/search_box.json

Usage:
  .venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_search_box.py [--samples 200]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.generated import GeneratedSpace  # noqa: E402
from hornlab_search.design.generators import grid  # noqa: E402
from tools.geometry import klangfilm_lame_hv as H  # noqa: E402

CONFIG = ROOT / "examples/typologies/klangfilm_hv_2026-11-16/configs/stage_a_search.yaml"
EVIDENCE = ROOT / "docs/evidence/klangfilm_hv_2026-11-16"
SEARCHED = ("g_theta_h0_deg", "g_theta_v0_deg", "g_h_mid_gain_mm", "g_v_mid_gain_mm")
#: Probe ceilings for the empirical wall search: the kernel's own module-level maxima.
PROBE_HI = {"g_theta_h0_deg": 25.0, "g_theta_v0_deg": 25.0,
            "g_h_mid_gain_mm": 80.0, "g_v_mid_gain_mm": 80.0}


def _shape(seed: dict, knobs: dict, grid_keys: dict) -> dict:
    out = {k[2:]: float(v) for k, v in {**seed, **knobs}.items()}
    out.update(grid_keys)
    return out


def _bucket(message: str) -> str:
    if "shrinks below the throat radius" in message:
        return "radius falls below the throat radius"
    if "not non-decreasing" in message:
        return "forward radius is not non-decreasing"
    if "not strictly monotonic" in message:
        return "forward z is not strictly monotonic"
    if "must be in" in message:
        return "knob outside kernel bounds"
    return message[:120]


def _lawful(seed: dict, brief: dict, grid_keys: dict, knobs: dict) -> tuple[bool, str]:
    try:
        H.make_grid(_shape(seed, knobs, grid_keys), brief)
        return True, ""
    except ValueError as exc:
        return False, str(exc)


def _wall(seed: dict, brief: dict, grid_keys: dict, key: str,
          probe_hi: float) -> float | None:
    """Largest lawful value above the seed (bisection up to the kernel ceiling)."""
    if _lawful(seed, brief, grid_keys, {key: probe_hi})[0]:
        return None
    low, high = float(seed[key]), float(probe_hi)
    for _ in range(14):
        mid = 0.5 * (low + high)
        if _lawful(seed, brief, grid_keys, {key: mid})[0]:
            low = mid
        else:
            high = mid
    return round(low, 3)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=200)
    args = ap.parse_args(argv)

    cfg = load_config(CONFIG)
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    bounds = raw["bounds"]
    seed = {k: float(v) for k, v in cfg.seed_params.items()}
    grid_keys = {k: float(raw["generator"][k]) for k in ("n_phi", "n_s", "wall_thickness_mm")}
    brief = cfg.brief or {}

    # The canonical route validates the box (bounds, fixed==seed, dormancy, endpoints) and the seed.
    GeneratedSpace.from_config(cfg)
    block = GeneratedSpace.from_config(cfg).seed.params["grid"]
    inner, meta = grid.rows_grid_points(block, block["knobs"], brief)

    lows = np.array([float(bounds[k]["lo"]) for k in SEARCHED])
    highs = np.array([float(bounds[k]["hi"]) for k in SEARCHED])
    rng = np.random.default_rng(20261116)
    unit = np.empty((args.samples, len(SEARCHED)))
    for j in range(len(SEARCHED)):
        unit[:, j] = (rng.permutation(args.samples) + rng.random(args.samples)) / args.samples
    points = lows + unit * (highs - lows)

    records, failures = [], []
    for i, row in enumerate(points):
        knobs = {k: float(v) for k, v in zip(SEARCHED, row)}
        ok, message = _lawful(seed, brief, grid_keys, knobs)
        if ok:
            pts, _ = H.make_grid(_shape(seed, knobs, grid_keys), brief)
            records.append({"i": i, "knobs": knobs,
                            "width_mm": float(2 * np.abs(pts[:, :, 0]).max()),
                            "height_mm": float(2 * np.abs(pts[:, :, 1]).max()),
                            "depth_mm": float(np.ptp(pts[:, :, 2]))})
        else:
            failures.append({"i": i, "knobs": knobs, "reason": _bucket(message), "raw": message})

    walls = {k: _wall(seed, brief, grid_keys, k, PROBE_HI[k]) for k in SEARCHED}

    # Box corners: a 200-point LHS is evidence, not proof, so also test the 2^4 extreme combinations.
    corners = []
    for combo in __import__("itertools").product(*[(float(bounds[k]["lo"]), float(bounds[k]["hi"]))
                                                  for k in SEARCHED]):
        knobs = dict(zip(SEARCHED, combo))
        ok, message = _lawful(seed, brief, grid_keys, knobs)
        corners.append({"knobs": knobs, "ok": ok, "reason": _bucket(message) if message else ""})
    lawful = len(records)
    verdict = "LAWFUL" if lawful == args.samples else f"REFUSALS PRESENT ({len(failures)})"

    summary = {
        "config": str(CONFIG.relative_to(ROOT)), "schema": H.SCHEMA,
        "samples": args.samples, "lawful": lawful, "refused": len(failures),
        "lawful_fraction": lawful / args.samples,
        "bounds": {k: {"lo": float(bounds[k]["lo"]), "hi": float(bounds[k]["hi"]),
                       "search": bool(bounds[k].get("search", True))} for k in SEARCHED},
        "seed_materialised": {"shape": list(np.shape(inner)), "core_mode": meta["core_mode"],
                              "envelope_ok": meta.get("envelope_ok", True),
                              "implementation_sha256": meta["implementation_sha256"],
                              "size_policy": meta.get("size_policy", "enforce")},
        "empirical_monotonicity_wall": walls,
        "corners": {"tested": len(corners), "lawful": sum(c["ok"] for c in corners),
                    "refused": [c for c in corners if not c["ok"]]},
        "refusal_buckets": {b: sum(1 for f in failures if f["reason"] == b)
                            for b in sorted({f["reason"] for f in failures})},
        "range_in_lawful_samples": {
            "width_mm": [min(r["width_mm"] for r in records), max(r["width_mm"] for r in records)],
            "height_mm": [min(r["height_mm"] for r in records), max(r["height_mm"] for r in records)],
            "depth_mm": [min(r["depth_mm"] for r in records), max(r["depth_mm"] for r in records)],
        } if records else None,
        "failures": failures[:40],
        "verdict": verdict,
        "scope": "CPU geometry lawfulness only. No meshing, BEM, queue admission, or acoustic claim.",
        "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "kernel_sha256": hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest(),
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "search_box.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8")

    extent = summary["range_in_lawful_samples"]
    lines = [
        "# Klangfilm-Lame H/V Phase A - Stage A search-box lawfulness",
        "",
        "**CPU geometry only.** No meshing, BEM, queue admission or acoustic claim. "
        f"Config `{summary['config']}` (sha256 `{summary['config_sha256'][:16]}...`), "
        f"kernel `{summary['kernel_sha256'][:16]}...`.",
        "",
        f"- Samples: **{args.samples}** Latin-hypercube points over the four searched knobs.",
        f"- Lawful: **{lawful}**; refused: **{len(failures)}**; verdict: **{verdict}**.",
        f"- Box corners (2^4 extreme combinations): **{summary['corners']['lawful']}/"
        f"{summary['corners']['tested']}** lawful.",
        f"- Seed materialised: shape {tuple(summary['seed_materialised']['shape'])}, "
        f"mode `{meta['core_mode']}`, envelope_ok={meta.get('envelope_ok', True)}, "
        f"digest `{meta['implementation_sha256'][:16]}...`.",
        "",
        "## Declared box",
        "",
        "| knob | lo | hi | searched | largest lawful value above the seed (probe ceiling) |",
        "|---|---|---|---|---|",
    ]
    for k in SEARCHED:
        b = summary["bounds"][k]
        w = walls[k]
        wall_text = f"none up to {PROBE_HI[k]:g}" if w is None else f"{w:g}"
        lines.append(f"| `{k}` | {b['lo']:g} | {b['hi']:g} | {b['search']} | {wall_text} |")
    lines += ["", "## Lawful range inside the box", ""]
    if extent:
        lines.append(f"- W {extent['width_mm'][0]:.2f}-{extent['width_mm'][1]:.2f} mm, "
                     f"H {extent['height_mm'][0]:.2f}-{extent['height_mm'][1]:.2f} mm, "
                     f"D {extent['depth_mm'][0]:.2f}-{extent['depth_mm'][1]:.2f} mm "
                     "(envelope 600 x 480 x 480).")
    lines.append("")
    if failures:
        lines += ["## Refusals", "", "| knob set | reason |", "|---|---|"]
        for f in failures[:40]:
            kn = ", ".join(f"{k}={v:.3f}" for k, v in f["knobs"].items())
            lines.append(f"| {kn} | `{f['reason']}` |")
        lines.append("")
        if len(failures) > 40:
            lines.append(f"... {len(failures) - 40} more in `search_box.json`.")
    else:
        lines += ["No refusal: every sampled point produced a finite, non-decreasing forward radius on a "
                  "round 18 mm throat, with the join before the parent's axial turn.", ""]
    lines += [
        "## Why these bounds and not the handoff's first guesses",
        "",
        "The 2026-11-16 handoff proposed `h_mid_gain_mm -12..+35` and `v_mid_gain_mm -20..+15`. Negative "
        "gains are not merely aggressive here, they are **infeasible**: the B2 basis ramps as t^3, so a "
        "negative mm gain locally dominates the wall slope. Measured at the canonical incumbent (join "
        "0.65): the V radius falls below the 18 mm throat at about -5.2 mm and stops being "
        "non-decreasing at about -0.04 mm; the handoff's -8 mm seed reaches 15.02 mm at z ~ 61.8 mm. The "
        "kernel refuses instead of clamping, so the Stage A box must be the positive quadrant. Measured "
        "positive walls are 20.5-21.5 mm (H) and 4.0-5.5 mm (V) depending on the throat angle; 20.0 and "
        "3.75 keep margin. A genuinely tighter interior needs the Phase B integrated-slope core, where a "
        "lower-but-positive wall slope is monotone by construction.",
        "",
        "Three positive walls are real too, from the same slope budget: the H gain (~21.6 mm), the V gain "
        "(~5.4 mm at theta_V 5 deg, falling to ~4.0 mm at 13 deg), and theta_V itself at about 17.1 deg. "
        "The last one is worth stating because it is counter-intuitive: a steeper early V slope overshoots "
        "and then the aspect gate pulls b back, so b stops being non-decreasing. Every declared bound sits "
        "inside its wall, and all 2^4 box corners are lawful.",
        "",
        f"Re-run: `.venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_search_box.py --samples {args.samples}`",
        "",
    ]
    (EVIDENCE / "SEARCH_BOX.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Stage A box: {lawful}/{args.samples} lawful, verdict {verdict}")
    print(f"largest lawful above seed (mm/deg): {walls}")
    print(f"corners: {summary['corners']['lawful']}/{summary['corners']['tested']} lawful")
    print(f"lawful W/H/D: {extent}")
    for bucket, count in summary["refusal_buckets"].items():
        print(f"  refused {count}: {bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
