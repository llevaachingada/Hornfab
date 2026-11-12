"""``hornlab-search ab-bl export | solve | import | compare | demo`` (wired in ``hornlab_search/cli.py``).

The five steps of docs/ab/BOUNDARY_LAB_AB.md, one command each. Every command prints the folder it wrote and what to run next.
Exit codes: 0 ok / PASS, 10 WARN verdict, 11 FAIL verdict (report still written), 1 error, 2 usage, 3 GPU busy.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXIT_WARN, EXIT_FAIL = 10, 11


def add_arguments(p) -> None:
    sub = p.add_subparsers(dest="ab_cmd")
    ws = "workspace folder (default: the newest folder under runs/ab_bl)"

    e = sub.add_parser("export", help="write the BL handoff folder for one design")
    e.add_argument("--source", required=True, help="config YAML (seed design), run directory, or designs/<hash> directory")
    e.add_argument("--config", help="config YAML when --source is a design/run folder without config.yaml")
    e.add_argument("--design-hash", help="which design of a run directory (default: --rank)")
    e.add_argument("--rank", type=int, default=0, help="rank in the run (0 = best objective)")
    e.add_argument("--workspace", help="output workspace (default runs/ab_bl/<label>)")
    e.add_argument("--lo-hz", type=float, default=100.0)
    e.add_argument("--hi-hz", type=float, default=None,
                   help="top of the frequency grid, whole Hz (default: 20000, or what the mesh resolves, whichever is lower)")
    e.add_argument("--ppo", type=float, default=12.0, help="frequency points per octave (default 12 = 1/12 octave)")
    e.add_argument("--angle-count", type=int, default=73, help="odd; 73 = 2.5 degree steps over -90..+90")
    e.add_argument("--balloon-points", type=int, default=2048)
    e.add_argument("--distance-m", type=float, help="observation radius (default: the config's solve.distance_m)")
    e.add_argument("--rebuild-mesh", action="store_true",
                   help="re-mesh with the production mesher at --mesh-f-max (default: use the design's existing mesh.msh)")
    e.add_argument("--mesh-f-max", type=float, help="highest frequency the rebuilt mesh must resolve (default --hi-hz)")
    e.add_argument("--max-dof", type=int, help="dof ceiling for the rebuilt mesh (default: config dof_cap_final)")
    e.add_argument("--keep-symmetry", action="store_true",
                   help="export the reduced mesh with a Boundary Lab symmetry flag instead of a full mesh (default: full mesh, symmetry off)")

    s = sub.add_parser("solve", help="high-resolution full-band Hornfab reference solve of the exported design (GPU)")
    s.add_argument("--workspace", help=ws)
    s.add_argument("--symmetric", action="store_true",
                   help="solve the native reduced mesh with solver symmetry (faster, and a second check) instead of the full handoff mesh")
    s.add_argument("--max-dof", type=int, help="refuse above this many dofs (default: the config's dof_cap_final)")
    s.add_argument("--dry-run", action="store_true", help="read the mesh and print the dof / time estimate; launch no solver")
    s.add_argument("--out", help="reference folder (default <workspace>/hornfab_reference)")

    i = sub.add_parser("import", help="read Boundary Lab exports (or generic CSV) into the normalized form")
    i.add_argument("--bl", help="Boundary Lab results folder (default <workspace>/results_from_friend)")
    i.add_argument("--workspace", help=ws)
    i.add_argument("--out", help="where to write the normalized data (default <workspace>/bl_normalized)")
    i.add_argument("--polar-csv", help="generic CSV: freq_hz,plane,angle_deg,spl_db[,phase_deg]")
    i.add_argument("--on-axis-csv", help="generic CSV: freq_hz,spl_db[,phase_deg]")
    i.add_argument("--impedance-csv", help="generic CSV: freq_hz,z_real,z_imag")
    i.add_argument("--level", choices=("absolute", "normalized"), default="absolute", help="level meaning for --polar-csv")
    i.add_argument("--distance-m", type=float)

    c = sub.add_parser("compare", help="compare the Hornfab reference with the Boundary Lab results and write the report")
    c.add_argument("--workspace", help=ws)
    c.add_argument("--hornfab", help="Hornfab reference folder (default <workspace>/hornfab_reference)")
    c.add_argument("--bl", help="Boundary Lab results (default <workspace>/results_from_friend)")
    c.add_argument("--handoff", help="handoff folder (default <workspace>/bl_handoff)")
    c.add_argument("--out", help="report folder (default <workspace>/compare)")
    c.add_argument("--tolerances", help="JSON file with any of the tolerance names (see docs/ab/BOUNDARY_LAB_AB.md)")
    c.add_argument("--bands", help="comma separated band edges in Hz, default 1000,5000,10000")
    c.add_argument("--chart-backend", choices=("auto", "matplotlib", "builtin"), default="auto")
    c.add_argument("--no-verdict-exit", action="store_true", help="exit 0 even for WARN / FAIL")

    d = sub.add_parser("demo", help="synthetic data for both sides, whole pipeline, no GPU, no Boundary Lab")
    d.add_argument("--fake", action="store_true", help="required: confirms the data is synthetic")
    d.add_argument("--out", help="output folder (default runs/ab_bl/demo_fake)")
    d.add_argument("--inject", default="offset6", help="comma list of faults for the second case "
                   "(none, offset6, slope, conj, polarity, delay, mirror, swap, radius, all). Default offset6")
    d.add_argument("--chart-backend", choices=("auto", "matplotlib", "builtin"), default="auto")


def _runs_root(args) -> Path:
    return Path(getattr(args, "runs_dir", None) or REPO / "runs") / "ab_bl"


def _workspace(args, *, must_exist=True) -> Path:
    if getattr(args, "workspace", None):
        return Path(args.workspace)
    root = _runs_root(args)
    cands = sorted((d for d in root.glob("*") if d.is_dir()), key=lambda d: d.stat().st_mtime) if root.exists() else []
    if not cands and must_exist:
        raise SystemExit(f"no workspace under {root}: run `hornlab-search ab-bl export ...` first or pass --workspace")
    ws = cands[-1] if cands else root
    print(f"(using workspace {ws})")
    return ws


def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_export(args) -> int:
    from .export_for_bl import export_for_bl
    from . import hornfab_side as hs
    cfg, design, label, found_mesh, _k = hs.resolve_source(args.source, config=args.config, design_hash=args.design_hash,
                                                           rank=args.rank)
    ws = Path(args.workspace) if args.workspace else _runs_root(args) / label
    man = export_for_bl(args.source, ws / "bl_handoff", config=args.config, design_hash=args.design_hash, rank=args.rank,
                        lo_hz=args.lo_hz, hi_hz=args.hi_hz, points_per_octave=args.ppo, angle_count=args.angle_count,
                        balloon_points=args.balloon_points, distance_m=args.distance_m, rebuild_mesh=args.rebuild_mesh,
                        mesh_f_max_hz=args.mesh_f_max, max_dof=args.max_dof, keep_symmetry=args.keep_symmetry,
                        cfg=cfg, design=design, label=label, mesh_path=None if args.rebuild_mesh else found_mesh)
    q = man["mesh"]["quality"]
    print(f"export OK: {man['design']['label']}  {man['mesh']['n_triangles']} triangles (full), ~{man['mesh']['approx_p1_dofs']} dofs, "
          f"{man['frequencies']['count']} frequencies {man['frequencies']['lo_hz']:g}-{man['frequencies']['hi_hz']:g} Hz")
    if "f_valid_p95_hz" in q:
        print(f"  mesh edge p95 {q['edge_p95_m'] * 1000:.1f} mm -> about {q['f_valid_p95_hz'] / 1000:.1f} kHz at {q['epw_assumed']:g} elements per wavelength")
        if q["f_valid_p95_hz"] < man["frequencies"]["hi_hz"]:
            print(f"  WARNING: the mesh does not resolve the top of the grid ({man['frequencies']['hi_hz']:g} Hz); re-export with "
                  f"--rebuild-mesh (needs the mesher) or lower --hi-hz")
    print(f"  handoff folder: {ws / 'bl_handoff'}\n  send it to your friend (zip the folder); FOR_YOUR_FRIEND.md inside tells them what to do")
    print(f"  next: hornlab-search ab-bl solve --workspace \"{ws}\"")
    return 0


def cmd_solve(args, argv) -> int:
    from ..config import load_config
    from ..search.gpulock import GpuBusyError, gpu_lock
    from ..types import BackendUnavailableError, Design
    from . import hornfab_side as hs
    ws = _workspace(args)
    ho = ws / "bl_handoff"
    man = _load_json(ho / "handoff.json")
    d = man["design"]
    if not d.get("config_path"):
        print("solve FAILED: handoff.json has no config_path (export was given a bare design); pass the config again via export")
        return 1
    cfg = load_config(d["config_path"], backend=getattr(args, "backend", None))
    design = Design(d["family"], dict(d["params"]))
    if design.hash() != d["design_hash"]:
        print("solve FAILED: the design hash recomputed from handoff.json differs from the recorded one (library change?)")
        return 1
    freqs = man["frequencies"]["freqs_hz"]
    obs = man["observation"]
    native = man["mesh"]["native"]
    if args.symmetric or man["mesh"]["symmetry_in_blab"] != "off":
        mesh_rel, quadrants = native["file"], native["quadrants"]     # reduced mesh + solver symmetry
    else:
        mesh_rel, quadrants = man["mesh"]["file"], "1234"           # the exact full mesh the friend gets
    out = Path(args.out) if args.out else ws / "hornfab_reference"
    max_dof = args.max_dof or int(cfg.mesh.dof_cap_final)
    kwargs = dict(cfg=cfg, design=design, out_dir=out, freqs_hz=freqs, angle_count=int(obs["angle_count"]),
                  balloon_points=int(obs["balloon_points_hornfab"]), distance_m=float(obs["distance_m"]),
                  mesh_path=ho / mesh_rel, quadrants=quadrants, max_dof=max_dof,
                  label=f"Hornfab {man['design']['label']}",
                  extra_meta={"handoff_mesh_sha256": man["mesh"]["sha256"],
                              "solved_mesh": "native reduced (solver symmetry)" if args.symmetric else "full handoff mesh"})
    if args.dry_run:
        _, rep = hs.solve_reference(dry_run=True, **kwargs)
        print(f"solve dry-run: {rep['n_freqs']} frequencies {rep['f_lo_hz']:g}-{rep['f_hi_hz']:g} Hz, mesh ~{rep['est_dof']} dofs "
              f"({quadrants}), estimated {rep['est_solve_minutes']:.0f} minutes (rough cost curve, not a promise)")
        return 0
    from ..cli import _backend, _command_string
    from ..solve import worker
    worker.install_handlers()
    try:
        with gpu_lock(_command_string(argv), runs_root=Path(getattr(args, "runs_dir", None) or REPO / "runs")):
            try:
                backend = _backend(cfg)
            except BackendUnavailableError as exc:
                print(f"solve FAILED: {exc}")
                return 1
            vram0 = worker.vram_used_mib()
            print(f"GPU hygiene: stale hosts cleared by warm(); VRAM baseline before the solve: "
                  f"{'unknown' if vram0 is None else f'{vram0:.0f} MiB'} (desktop alone is ~300-500 MiB)")
            try:
                worker.warm(backend)
                _, rep = hs.solve_reference(backend=backend, **kwargs)
            finally:
                worker.shutdown(verify=True)          # CLAUDE.md GPU rule 6: end a measurement with no host left
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(f"solve OK: {rep['n_freqs']} frequencies, ~{rep['est_dof']} dofs, {rep['solve_seconds'] / 60:.1f} min; output {out}")
    print(f"  next: send bl_handoff to your friend, then `hornlab-search ab-bl compare --workspace \"{ws}\"`")
    return 0


def cmd_import(args) -> int:
    from . import bl_import as bi
    if args.polar_csv or args.on_axis_csv or args.impedance_csv:
        data = bi.import_generic_csv(polar_csv=args.polar_csv, on_axis_csv=args.on_axis_csv, impedance_csv=args.impedance_csv,
                                     level=args.level, distance_m=args.distance_m, label="CSV")
        out = Path(args.out or "ab_csv_normalized")
    else:
        ws = _workspace(args)
        src = Path(args.bl) if args.bl else ws / "results_from_friend"
        if not src.exists() and (ws / "bl_handoff" / "results_from_friend").exists():
            src = ws / "bl_handoff" / "results_from_friend"
        hp = ws / "bl_handoff" / "handoff.json"
        data = bi.import_bl(src, handoff=_load_json(hp) if hp.exists() else None)
        out = Path(args.out) if args.out else ws / "bl_normalized"
    data.save(out)
    print(f"import OK: {data.source} route={data.meta.get('route')} {data.freqs_hz.size} frequencies "
          f"{data.freqs_hz[0]:g}-{data.freqs_hz[-1]:g} Hz, {data.angles_deg.size} angles, balloon={'yes' if data.balloon_dirs is not None else 'no'}, "
          f"impedance={'yes' if data.z_norm is not None else 'no'}, absolute on-axis={'yes' if data.axis_db_absolute() is not None else 'no'}")
    for n in data.meta.get("notes", []):
        print(f"  note: {n}")
    print(f"  normalized data: {out}")
    return 0


def cmd_compare(args) -> int:
    from . import bl_import as bi
    from . import hornfab_side as hs
    from .analysis import BANDS_DEFAULT, Tolerances, compare
    from .report import build_report
    ws = _workspace(args)
    ho = Path(args.handoff) if args.handoff else ws / "bl_handoff"
    handoff = _load_json(ho / "handoff.json") if (ho / "handoff.json").exists() else None
    a_path = Path(args.hornfab) if args.hornfab else ws / "hornfab_reference"
    b_path = Path(args.bl) if args.bl else ws / "results_from_friend"
    if not b_path.exists() and (ho / "results_from_friend").exists():
        b_path = ho / "results_from_friend"
    a = hs.load_hornfab(a_path, label="Hornfab")
    b = bi.import_bl(b_path, handoff=handoff, label="Boundary Lab")
    prov = {"hornfab_folder": str(a_path), "bl_folder": str(b_path)}
    if handoff:
        prov["handoff_design"] = handoff["design"]["design_hash"]
        ref = (a.meta.get("reference_meta") or {})
        if ref.get("handoff_mesh_sha256") and ref["handoff_mesh_sha256"] != handoff["mesh"]["sha256"]:
            print("WARNING: the Hornfab reference was solved on a different mesh than the current handoff (sha256 differs)")
        bm = (b.meta.get("bl_manifest") or {}).get("meshes") or []
        shas = [m.get("sha256") for m in bm if isinstance(m, dict)]
        if shas and handoff["mesh"]["sha256"] not in shas:
            print("WARNING: the Boundary Lab run recorded a different mesh hash than the handoff mesh (the friend used another mesh?)")
    tol = Tolerances.from_dict(_load_json(Path(args.tolerances)) if args.tolerances else None)
    bands = BANDS_DEFAULT
    if args.bands:
        edges = [float(x) for x in args.bands.split(",")]
        names = [f"<{edges[0]:g}"] + [f"{lo:g}-{hi:g}" for lo, hi in zip(edges[:-1], edges[1:])] + [f">{edges[-1]:g}"]
        lows = [0.0] + edges
        highs = edges + [float("inf")]
        bands = tuple(zip(names, lows, highs))
    cmp = compare(a, b, tolerances=tol, bands=bands)
    out = Path(args.out) if args.out else ws / "compare"
    res = build_report(cmp, out, provenance=prov, backend=args.chart_backend)
    print((out / "verdict.txt").read_text(encoding="utf-8"))
    print(f"report: {out / 'report.html'}\nsummary: {out / 'summary.json'}")
    if args.no_verdict_exit:
        return 0
    return {"pass": 0, "warn": EXIT_WARN, "fail": EXIT_FAIL}.get(res["overall"], 0)


def cmd_demo(args) -> int:
    from ..config import load_config
    from ..design.space import DesignSpace
    from . import bl_import as bi
    from . import fake, hornfab_side as hs
    from .analysis import Tolerances, compare
    from .export_for_bl import export_for_bl
    from .report import build_report
    if not args.fake:
        print("demo needs --fake (it only makes synthetic data; real runs use export / solve / compare)")
        return 2
    out = Path(args.out) if args.out else _runs_root(args) / "demo_fake"
    cases = ["none"]
    inj = [x.strip() for x in args.inject.split(",") if x.strip()]
    if "all" in inj:
        inj = [x for x in fake.INJECTIONS if x != "none"]
    cases += [x for x in inj if x != "none"]
    fake.write_hornfab_side(out / "hornfab_reference")
    rows = []
    for case in cases:
        cdir = out / case
        route = "gui" if case != "none" else "both"        # clean case: both BL routes, the headless run wins on import
        fake.write_bl_gui_side(cdir / "results_from_friend", inject=case)
        if route == "both":
            fake.write_bl_headless_side(cdir / "results_from_friend" / "headless_run", inject=case)
        a = hs.load_hornfab(out / "hornfab_reference", label="Hornfab (synthetic)")
        b = bi.import_bl(cdir / "results_from_friend", label=f"Boundary Lab (synthetic, inject={case})")
        res = build_report(compare(a, b, tolerances=Tolerances()), cdir / "compare", backend=args.chart_backend,
                           provenance={"synthetic": True, "inject": case})
        rows.append((case, res["overall"], [f["code"] for f in res["findings"] if f["likelihood"] != "info"]))
    # handoff export demo on the tiny synthetic quarter mesh
    ex = REPO / "examples" / "osse_baseline.yaml"
    if ex.exists():
        cfg = load_config(ex)
        design = DesignSpace.from_config(cfg).seed
        mesh = out / "synthetic_quarter.msh"
        fake.write_fake_quarter_msh(mesh)
        export_for_bl(None, out / "bl_handoff", cfg=cfg, design=design, mesh_path=mesh, quadrants="1", label="demo-synthetic-mesh")
    print("demo --fake: synthetic data for both sides (no solver, no Boundary Lab)")
    print(f"{'case':<10} {'verdict':<8} findings")
    for case, v, f in rows:
        print(f"{case:<10} {v.upper():<8} {', '.join(f) or '-'}")
    print(f"reports: {out}/<case>/compare/report.html ; handoff example: {out / 'bl_handoff'}")
    ok = rows[0][1] == "pass" and all(r[1] in ("warn", "fail") for r in rows[1:])
    if not ok:
        print("demo CHECK FAILED: the clean case should PASS and every injected fault should WARN or FAIL")
        return 1
    return 0


def run(args, argv) -> int:
    cmd = getattr(args, "ab_cmd", None)
    if cmd == "export":
        return cmd_export(args)
    if cmd == "solve":
        return cmd_solve(args, argv)
    if cmd == "import":
        return cmd_import(args)
    if cmd == "compare":
        return cmd_compare(args)
    if cmd == "demo":
        return cmd_demo(args)
    print("usage: hornlab-search ab-bl {export,solve,import,compare,demo} ... (docs/ab/BOUNDARY_LAB_AB.md)", file=sys.stderr)
    return 2
