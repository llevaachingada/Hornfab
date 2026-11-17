"""Section cuts for the CROWE-inspired V2A forward area/aspect family (CPU geometry only).

Loads a ``crowe_hv_area_aspect_v1`` config, evaluates the generator's own law at the physical
stations, and prints area, aspect, superellipse exponent (roundness), aspect-gate value, wall
tangent and meridian curvature. This answers the review request directly: it measures the law the
search materialises, not a low-resolution preview, wireframe or source-cap render.

The V2A default stations are 0/5/10/20/40/60/100 mm. ``--stations`` accepts a comma list and
``--json`` emits the machine-readable form. No mesh, BEM or GPU work happens here.

Run:
  .venv\\Scripts\\python.exe tools/geometry/crowe_hv_area_aspect_sections.py `
      --config examples/typologies/crowe_hv_area_aspect_2026-11-16/configs/c0_four_dof_seed.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from hornlab_search.config import load_config
from hornlab_search.design.generators import crowe_hv_area_aspect_v1 as family


def _stations(text: str) -> tuple[float, ...]:
    return tuple(float(part) for part in text.split(",") if part.strip())


def _markdown(rows: list[dict], meta: dict) -> str:
    head = ("| z (mm) | a (mm) | b (mm) | area (mm^2) | area/throat | aspect a/b | p | "
            "gate | wall H (deg) | wall V (deg) | curvature H (1/mm) | curvature V (1/mm) | "
            "hold |")
    sep = "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"
    lines = [head, sep]
    for row in rows:
        lines.append(
            f"| {row['z_mm']:g} | {row['a_mm']:.4f} | {row['b_mm']:.4f} | {row['area_mm2']:.3f} | "
            f"{row['area_ratio_to_throat']:.6f} | {row['aspect']:.6f} | {row['p']:.6f} | "
            f"{row['aspect_gate']:.6f} | {row['wall_h_deg']:.4f} | {row['wall_v_deg']:.4f} | "
            f"{row['curvature_h_1_per_mm']:.8f} | {row['curvature_v_1_per_mm']:.8f} | "
            f"{'yes' if row['inside_round_hold'] else 'no'} |")
    lines.append("")
    lines.append(
        f"aspect timing u50: {meta['aspect_timing_u50']:.4f}; gate(u50) = "
        f"{meta['gate_at_u50']:.6f}; fixed hold = {meta['fixed_throat_round_hold_mm']:.3f} mm; "
        f"first-20-mm max |aspect-1| = {meta['max_abs_aspect_minus_1_over_first_20mm']:.3e}; "
        f"first-20-mm max |p-2| = {meta['max_abs_p_minus_2_over_first_20mm']:.3e}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="config under examples/")
    parser.add_argument("--stations", default="0,5,10,20,40,60,100",
                        help="comma-separated physical z stations in mm")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    gen = cfg.generator
    if not family.is_family_spec(gen):
        parser.error(f"{args.config} is not a {family.KIND} config")
    rows = family.section_cuts(gen, cfg.seed_params, cfg.brief, _stations(args.stations))
    meta = family._throat_smoothness(family._shape(gen, cfg.seed_params), cfg.brief)
    payload = {"config": args.config, "kind": family.KIND,
               "implementation_sha256": family.implementation_digest(),
               "throat_smoothness": meta, "sections": rows}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"# {Path(args.config).name} ({family.SCHEMA})")
        print()
        print(_markdown(rows, meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
