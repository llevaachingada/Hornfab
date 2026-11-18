"""System-layer feature CLI (additive; NOT registered in the global hornlab-search CLI).

    python -m hornlab_search.system.cli --help
    python -m hornlab_search.system.cli pilot --spec examples/systems/two_way_80x50_700_research.yaml \
        --driver-stem faitalpro_12pr300 --asset-id <id> --out <dir>

All commands are CPU-only, read-only against canonical runs/, and write only to the isolated
system store (default ``system_runs/`` or $HORNLAB_SYSTEM_STORE).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

__all__ = ["main"]

_TS_DIR = Path(__file__).resolve().parents[2] / "examples" / "systems" / "driver_ts"


def _cmd_portfolio(args: argparse.Namespace) -> int:
    import yaml

    from hornlab_search.system import portfolio
    from hornlab_search.system.contracts import parse_system_spec_dict

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(json.dumps({"error": f"spec not found: {spec_path}"}))
        return 2
    spec = parse_system_spec_dict(yaml.safe_load(spec_path.read_text(encoding="utf-8")))
    stems = tuple(args.driver_stem) if args.driver_stem else (
        "faitalpro_12pr300", "faitalpro_12pr320")
    result = portfolio.run_portfolio(
        spec,
        driver_stems=stems,
        runs_root=args.runs_root,
        scan_limit=args.scan_limit,
        k=args.k,
        limit_boxes=args.limit_boxes,
        driver_ts_dir=args.driver_ts_dir,
        out_dir=args.out,
    )
    print(json.dumps({
        "study_id": result.meta["study_id"],
        "case_dir": result.meta.get("case_dir"),
        "selected_assets": len(result.asset_summary),
        "rejected_count": result.meta["rejected_count"],
        "n_rows": len(result.rows),
        "screen_disagree_tol_deg": result.meta["screen_disagree_tol_deg"],
        "same_budget_per_cell": result.meta["same_budget_per_cell"],
        "assets": [
            {"asset_id": a["asset_id"], "family": a["family"], "brief_id": a["brief_id"],
             "freq_range_hz": a["freq_range_hz"], "cuts_screen_by_xo_deg": a["cuts_screen_by_xo_deg"]}
            for a in result.asset_summary
        ],
    }, indent=2))
    print(result.report["markdown"])
    return 0


def _cmd_pilot(args: argparse.Namespace) -> int:
    import yaml

    from hornlab_search.system import optimize
    from hornlab_search.system.contracts import parse_system_spec_dict

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(json.dumps({"error": f"spec not found: {spec_path}"}))
        return 2
    spec = parse_system_spec_dict(yaml.safe_load(spec_path.read_text(encoding="utf-8")))
    result = optimize.run_pilot(
        spec,
        driver_stem=args.driver_stem,
        driver_ts_dir=args.driver_ts_dir,
        geometry_path=args.geometry,
        runs_root=args.runs_root,
        asset_id=args.asset_id,
        scan_limit=args.scan_limit,
        limit_boxes=args.limit_boxes,
        out_dir=args.out,
    )
    print(json.dumps({
        "study_id": result.meta["study_id"],
        "spec_hash": result.meta["spec_hash"],
        "case_dir": result.meta.get("case_dir"),
        "asset_id": None if result.asset is None else result.asset.asset_id,
        "converted": None if result.converted is None else result.converted.to_dict(),
        "driver": {"driver_id": result.driver.driver_id, "name": result.driver.cone.name},
        "n_box_candidates": len(result.boxes),
    }, indent=2))
    print(result.report["markdown"])
    return 0


def _cmd_list_drivers(args: argparse.Namespace) -> int:
    directory = Path(args.driver_ts_dir) if args.driver_ts_dir else _TS_DIR
    stems = sorted(
        p.stem for p in directory.glob("*.yaml")
        if p.is_file()) if directory.is_dir() else []
    print(json.dumps({"driver_ts_dir": str(directory), "stems": stems}))
    return 0


def _cmd_list_assets(args: argparse.Namespace) -> int:
    from hornlab_search.system import horn_assets as HA

    result = HA.inventory_runs(args.runs_root, limit=args.limit)
    print(json.dumps({"runs_scanned": result.runs_scanned,
                      "assets_total": len(result.assets),
                      "by_quality": result.quality_counts(),
                      "rows": [HA.asset_row(a) for a in result.assets[: args.limit]]},
                     indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hornlab_search.system.cli",
        description="Additive two-way horn+woofer system layer (screening only; no GPU, no solver)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pilot = sub.add_parser("pilot", help="fixed-horn CPU feasibility pilot (screen_only)")
    p_pilot.add_argument("--spec", required=True, metavar="YAML",
                         help="schema-v1 system spec (examples/systems/...)")
    p_pilot.add_argument("--driver-stem", default=None,
                         help="T/S stem (default: spec.woofer.driver_id)")
    p_pilot.add_argument("--driver-ts-dir", default=None,
                         help="directory of driver T/S YAMLs (default examples/systems/driver_ts, "
                              "falls back to examples/drivers)")
    p_pilot.add_argument("--geometry", default=None,
                         help="schema-v1 driver geometry YAML (optional)")
    p_pilot.add_argument("--asset-id", default=None,
                         help="saved horn asset id (from audit_saved_horns.py / list-assets)")
    p_pilot.add_argument("--runs-root", default=None, help="saved-response root override")
    p_pilot.add_argument("--scan-limit", type=int, default=300,
                         help="max newest run dirs scanned for the asset id")
    p_pilot.add_argument("--limit-boxes", type=int, default=8,
                         help="keep the N smallest feasible box candidates")
    p_pilot.add_argument("--out", default=None, metavar="DIR",
                         help="isolated store root for the case manifest (default system_runs)")
    p_pilot.set_defaults(func=_cmd_pilot)

    p_drivers = sub.add_parser("list-drivers", help="list pilot driver stems")
    p_drivers.add_argument("--driver-ts-dir", default=None)
    p_drivers.set_defaults(func=_cmd_list_drivers)

    p_portfolio = sub.add_parser(
        "portfolio", help="Stage 3: diverse-horn portfolio screen (identical CPU budget, "
                          "report-only; NOT a horn leaderboard)")
    p_portfolio.add_argument("--spec", required=True, metavar="YAML")
    p_portfolio.add_argument("--driver-stem", action="append", default=None, metavar="STEM",
                             help="driver stem (repeatable; default: both verified 12-inch)")
    p_portfolio.add_argument("--k", type=int, default=6, help="portfolio size (4-8 recommended)")
    p_portfolio.add_argument("--limit-boxes", type=int, default=8)
    p_portfolio.add_argument("--scan-limit", type=int, default=60,
                             help="max newest runs scanned for the candidate pool")
    p_portfolio.add_argument("--runs-root", default=None)
    p_portfolio.add_argument("--driver-ts-dir", default=None)
    p_portfolio.add_argument("--out", default=None, metavar="DIR",
                             help="isolated store root (default system_runs)")
    p_portfolio.set_defaults(func=_cmd_portfolio)

    p_assets = sub.add_parser("list-assets", help="bounded read-only asset inventory")
    p_assets.add_argument("--runs-root", default=None)
    p_assets.add_argument("--limit", type=int, default=40)
    p_assets.set_defaults(func=_cmd_list_assets)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:  # pragma: no cover
        sys.exit(0)
