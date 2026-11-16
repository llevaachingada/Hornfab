"""Geometry-only diagnostic for the owner-supplied K seed pack; no meshing or solving."""
import argparse
import hashlib
import json
import platform
import sys
import traceback
from pathlib import Path

import numpy as np
import scipy
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.geometry import klangfilm_lame as kernel

DEFAULT_SEEDS = ROOT / "docs/research/typologies/dual_lame_2026-11-16/k_visual_seeds_supplied.yaml"
BASE = ROOT / "examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1.yaml"
OUTPUT = ROOT / "docs/research/typologies/dual_lame_2026-11-16/k_visual_seed_diagnostic.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    seeds = yaml.safe_load(args.seeds.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    brief_path = (BASE.parent / base["brief_file"]).resolve()
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    shape = {key[2:]: value for key, value in base["seed_params"].items()}
    shape.update({k: base["generator"][k] for k in ("n_phi", "n_s", "wall_thickness_mm")})
    paths = [args.seeds.resolve(), BASE, brief_path, Path(__file__).resolve(),
             ROOT / "tools/geometry/klangfilm_lame.py", ROOT / "tools/geometry/lame_cap.py"]
    result = {"scope": "Inner sampled quarter-grid geometry only. No shell, mesh, acoustic solve, validity or readiness assertion.",
              "input_sha256": {str(p): digest(p) for p in paths},
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "pyyaml": yaml.__version__},
              "base_shape_defaults": shape, "brief_driver": brief["driver"],
              "pack_exit_diameter_mm": seeds["driver_exit_diameter_mm"],
              "envelope_mm": seeds["hard_envelope_mm"],
              "bbox_method": "Sampled inner quarter-grid, reflected across x=0 and y=0; width=2*max(x), height=2*max(y), depth=max(z)-min(z). Excludes wall thickness and unsampled extrema.",
              "binding": {"rim_sweep": "rim_sweep_ratio; edge setback = ratio * max sampled semi-width, gated by station and cos(phi)^2"},
              "cases": []}
    for sample in seeds["samples"]:
        overrides = dict(sample["params"])
        overrides["rim_sweep_ratio"] = overrides.pop("rim_sweep")
        effective = dict(shape, **overrides)
        case = {"id": sample["id"], "style": sample["style"], "params": effective}
        try:
            pts, meta = kernel.make_grid(effective, brief)
            bbox = {"W": float(2 * pts[..., 0].max()), "H": float(2 * pts[..., 1].max()),
                    "D": float(np.ptp(pts[..., 2]))}
            case.update({"inner_bbox_mm": bbox,
                         "inner_bbox_within_pack_envelope": all(bbox[k] <= seeds["hard_envelope_mm"][k] for k in bbox),
                         "finite": bool(np.isfinite(pts).all()), "grid_shape": list(pts.shape),
                         "grid_sha256": hashlib.sha256(pts.tobytes()).hexdigest(),
                         "cap_area_resid_max": meta["cap_area_resid_max"], "exception": None})
        except Exception as exc:
            case["exception"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        result["cases"].append(case)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(result['cases'])} cases to {args.output}")


if __name__ == "__main__":
    main()
