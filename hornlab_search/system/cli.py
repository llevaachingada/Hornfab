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


# --------------------------------------------------------------------------- reference workflow

def _reference_error(exc: BaseException) -> int:
    print(json.dumps({
        "error": str(exc),
        "token": getattr(exc, "token", None),
    }, indent=2))
    return 2


def _parse_overrides(text: str | None) -> dict | None:
    if text is None:
        return None
    raw = Path(text[1:]).read_text(encoding="utf-8") if text.startswith("@") else text
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("--overrides must be a JSON object of vented-source values")
    return payload


def _cmd_reference_prepare(args: argparse.Namespace) -> int:
    from hornlab_search.system import reference as REF

    try:
        prepared = REF.prepare(
            root=args.root,
            overrides=_parse_overrides(args.overrides),
            horn_mesh=args.horn_mesh,
            source_group=args.source_group,
            store_root=args.out,
            case_dir=args.case_dir,
            experiment_id=args.experiment_id,
            mesh_role=args.mesh_role,
            scale_factor=args.scale_factor,
            translation_mm=tuple(args.translation_mm),
            timeout_s=args.timeout_s,
            run_now=not args.dry_run,
        )
    except (REF.ReferenceError, ValueError, OSError, RuntimeError) as exc:
        return _reference_error(exc)
    print(json.dumps(prepared.as_dict(), indent=2))
    if args.dry_run:
        return 0
    return 0 if prepared.valid else 1


def _cmd_reference_validate(args: argparse.Namespace) -> int:
    from hornlab_search.system import reference as REF

    try:
        validation = REF.validate(args.case_dir, args.request, timeout_s=args.timeout_s)
    except (REF.ReferenceError, ValueError, OSError, RuntimeError) as exc:
        return _reference_error(exc)
    print(json.dumps(validation.as_dict(), indent=2))
    return 0 if (validation.valid and not validation.blockers) else 1


def _cmd_reference_solve(args: argparse.Namespace) -> int:
    from hornlab_search.system import reference as REF

    try:
        result = REF.solve(
            args.case_dir,
            args.request,
            backend=args.backend,
            authorized_by=args.authorized_by,
            out=args.run_out,
            timeout_s=args.timeout_s,
        )
    except REF.ReferenceError as exc:
        return _reference_error(exc)
    except (ValueError, OSError, RuntimeError) as exc:
        return _reference_error(exc)
    print(json.dumps(result.as_dict(), indent=2))
    return 0


def _cmd_reference_report(args: argparse.Namespace) -> int:
    from hornlab_search.system import reference as REF

    try:
        report = REF.report(args.case_dir, run_dir=args.run_dir)
    except (REF.ReferenceError, ValueError, OSError, RuntimeError) as exc:
        return _reference_error(exc)
    if args.markdown_out:
        Path(args.markdown_out).write_text(report.markdown, encoding="utf-8")
    if args.json:
        payload = dict(report.as_dict())
        payload.pop("markdown", None)
        print(json.dumps(payload, indent=2))
    else:
        print(report.markdown)
    return 0


def _cmd_funnel(args: argparse.Namespace) -> int:
    from hornlab_search.system import funnel

    ledger = funnel.build_ledger(
        Path(args.root),
        screens_root=args.screens_root,
        system_root=args.system_root,
    )
    if args.out:
        written = funnel.write_ledger(ledger, args.out)
        print(json.dumps({
            "schema": funnel.SCHEMA,
            "tokens": ledger["tokens"],
            "join_counts": ledger["join"]["counts"],
            "false_negative_audit": ledger["false_negative_audit"],
            "written": written,
        }, indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(ledger, indent=2, sort_keys=True))
    else:
        print(funnel.render_markdown(ledger))
    return 0


def _cmd_screen_calibration(args: argparse.Namespace) -> int:
    from hornlab_search.system import screen_calibration

    try:
        record = screen_calibration.build_calibration_record(
            args.screen_json,
            args.bem_run_dir,
            rel_tol=args.rel_tol,
            max_deg=args.max_deg,
            driver_id=args.driver_id,
            generated_utc=args.generated_utc,
        )
    except screen_calibration.CalibrationRecordError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    screen_calibration.write_calibration_record(record, args.out)
    print(json.dumps({
        "schema": record["schema"],
        "status": record.get("status"),
        "tokens": record.get("tokens"),
        "axes": {
            axis: {
                "screen_e_shape_db2": data.get("screen_e_shape_db2"),
                "bem_e_shape_db2": data.get("bem_e_shape_db2"),
                "screen_to_bem_factor": data.get("screen_to_bem_factor"),
            }
            for axis, data in (record.get("axes") or {}).items()
        },
        "threshold": record.get("threshold"),
        "out": str(args.out),
    }, indent=2, sort_keys=True))
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

    p_funnel = sub.add_parser(
        "funnel", help="read-only screen -> BEM case funnel ledger (no solve, no DSP sum)")
    p_funnel.add_argument("--root", default=".", metavar="DIR",
                          help="repository/store root (default: current directory)")
    p_funnel.add_argument("--screens-root", default=None, metavar="DIR",
                          help="tree containing woofer_seed.json files (default <root>/system_runs)")
    p_funnel.add_argument("--system-root", default=None, metavar="DIR",
                          help="tree containing BEM case dirs (default <root>/system_runs/system)")
    p_funnel.add_argument("--out", default=None, metavar="DIR",
                          help="write funnel_ledger.json + funnel_ledger.md under DIR")
    p_funnel.add_argument("--json", action="store_true",
                          help="print the full ledger as JSON (no markdown)")
    p_funnel.set_defaults(func=_cmd_funnel)

    p_cal = sub.add_parser(
        "screen-calibration",
        help="read-only R7a screen-vs-installed-BEM E_shape calibration record")
    p_cal.add_argument("screen_json", help="stored screen study JSON (e.g. woofer_seed.json)")
    p_cal.add_argument("bem_run_dir", help="BL headless result directory or its case directory")
    p_cal.add_argument("--out", required=True, metavar="JSON",
                       help="output calibration record path")
    p_cal.add_argument("--rel-tol", type=float, default=0.02,
                       help="nearest-frequency relative tolerance (default 0.02)")
    p_cal.add_argument("--max-deg", type=float, default=30.0,
                       help="maximum absolute front angle in the common grid (default 30)")
    p_cal.add_argument("--driver-id", default=None,
                       help="override the screen piston driver id (default: infer from the case)")
    p_cal.add_argument("--generated-utc", default=None,
                       help="pin the generated timestamp for byte-identical reruns")
    p_cal.set_defaults(func=_cmd_screen_calibration)

    # ---- reference: no-GUI Boundary Lab reference case (prepare/validate/solve/report)
    p_reference = sub.add_parser(
        "reference",
        help="no-GUI Boundary Lab reference case: prepare, validate, solve (authorized), report")
    ref_sub = p_reference.add_subparsers(dest="reference_command", required=True)

    p_ref_prepare = ref_sub.add_parser(
        "prepare", help="stage the horn+vented project through BL's host path and record it")
    p_ref_prepare.add_argument("--root", default=None, metavar="DIR",
                               help="verified Boundary Lab checkout (default: probe)")
    p_ref_prepare.add_argument("--horn-mesh", default=None, metavar="MSH",
                               help="closed horn mesh (default: newest full-domain mesh, else "
                                    "vented-only with BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT)")
    p_ref_prepare.add_argument("--source-group", default=None,
                               help="2D physical group of the horn mesh to drive (required with "
                                    "--horn-mesh)")
    p_ref_prepare.add_argument("--mesh-role", default="full_domain",
                               choices=["full_domain", "test_double"])
    p_ref_prepare.add_argument("--scale-factor", type=float, default=1.0)
    p_ref_prepare.add_argument("--translation-mm", type=float, nargs=3,
                               default=(0.0, 0.0, 0.0), metavar=("X", "Y", "Z"))
    p_ref_prepare.add_argument("--overrides", default=None,
                               help="JSON object (or @file) of vented-source overrides")
    p_ref_prepare.add_argument("--experiment-id", default="bl_ref_case")
    p_ref_prepare.add_argument("--out", default=None, metavar="DIR",
                               help="isolated store root (default system_runs)")
    p_ref_prepare.add_argument("--case-dir", default=None, metavar="DIR",
                               help="explicit fresh case directory (must be empty)")
    p_ref_prepare.add_argument("--timeout-s", type=float, default=1800.0)
    p_ref_prepare.add_argument("--dry-run", action="store_true",
                               help="build the BL-side spec only; create nothing")
    p_ref_prepare.set_defaults(func=_cmd_reference_prepare)

    p_ref_validate = ref_sub.add_parser(
        "validate", help="BL's own project validate verdict plus reference graph assertions")
    p_ref_validate.add_argument("case_dir")
    p_ref_validate.add_argument("--request", default=None, metavar="JSON",
                                help="BL headless request overlay (schema_version 1)")
    p_ref_validate.add_argument("--timeout-s", type=float, default=300.0)
    p_ref_validate.set_defaults(func=_cmd_reference_validate)

    p_ref_solve = ref_sub.add_parser(
        "solve", help="invoke BL's own project solve (requires --authorized-by)")
    p_ref_solve.add_argument("case_dir")
    p_ref_solve.add_argument("--request", required=True, metavar="JSON")
    p_ref_solve.add_argument("--backend", default="beat_cpu")
    p_ref_solve.add_argument("--authorized-by", default=None,
                             help="senior approval record; without it the solve is refused")
    p_ref_solve.add_argument("--run-out", default=None, metavar="DIR",
                             help="BL run output directory (default <case_dir>/run)")
    p_ref_solve.add_argument("--timeout-s", type=float, default=None)
    p_ref_solve.set_defaults(func=_cmd_reference_solve)

    p_ref_report = ref_sub.add_parser(
        "report", help="markdown report: DSP-preset complex sums, vertical lobing, honesty labels")
    p_ref_report.add_argument("case_dir")
    p_ref_report.add_argument("--run-dir", default=None, metavar="DIR")
    p_ref_report.add_argument("--markdown-out", default=None, metavar="MD",
                              help="also write the markdown report to this file")
    p_ref_report.add_argument("--json", action="store_true",
                              help="print the recomposition tables as JSON (no markdown)")
    p_ref_report.set_defaults(func=_cmd_reference_report)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:  # pragma: no cover
        sys.exit(0)
