"""T2 identifiability check for the CROWE-inspired V2A four-DOF family (CPU geometry only).

Loads a config with searched bounds, perturbs each of the four variables by +-10% of its
normalized box at three parent designs, and reports the descriptor Jacobian SVD, practical rank,
weak variables and pairwise collinearity. This is the addendum's T2 law-level check; it is not a
mesh-level or acoustic Jacobian.

Run:
  .venv\\Scripts\\python.exe tools/geometry/crowe_hv_area_aspect_jacobian.py `
      --config examples/typologies/crowe_hv_area_aspect_2026-11-16/configs/c1_four_dof_bounds.yaml
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
from hornlab_search.design.space import Bound


def _bounds(cfg) -> dict:
    return {str(k): Bound(lo=float(b["lo"]), hi=float(b["hi"]),
                          search=bool(b.get("search", True)))
            for k, b in cfg.bounds_raw.items()}


def _parents(cfg) -> list[tuple[str, dict]]:
    seed = {k: float(v) for k, v in cfg.seed_params.items()}
    low = {k: float(b["lo"]) + 0.25 * (float(b["hi"]) - float(b["lo"]))
           for k, b in cfg.bounds_raw.items()}
    high = {k: float(b["lo"]) + 0.75 * (float(b["hi"]) - float(b["lo"]))
            for k, b in cfg.bounds_raw.items()}
    return [("seed", seed), ("low_quarter", low), ("high_three_quarter", high)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="config under examples/ with searched bounds")
    parser.add_argument("--delta", type=float, default=0.1, help="normalized box half-step")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    if not family.is_family_spec(cfg.generator):
        parser.error(f"{args.config} is not a {family.KIND} config")
    bounds = _bounds(cfg)
    reports = []
    for name, knobs in _parents(cfg):
        report = family.identifiability_report(cfg.generator, knobs, bounds, cfg.brief,
                                               delta=args.delta)
        reports.append({"parent": name, "knobs": knobs, **report})
    payload = {"config": args.config, "kind": family.KIND,
               "implementation_sha256": family.implementation_digest(),
               "parents": reports}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"# {Path(args.config).name} T2 identifiability (delta {args.delta:g})")
    for report in reports:
        print(f"\n## {report['parent']}")
        print(f"keys: {report['keys']}")
        print(f"singular values: {[round(v, 6) for v in report['singular_values']]}")
        print(f"effective rank {report['effective_rank']}, practical rank "
              f"{report['practical_rank']}, weak {report['weak_keys']}, "
              f"max |cosine| {report['max_pairwise_abs_cosine']:.6f}")
        print("column norms: " + ", ".join(
            f"{k}={v:.4f}" for k, v in report["column_norms"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
