"""Mesh-only check of horn configs: does each seed build, fit the solver cap, fit the brief envelope and
couple round to the driver? CPU only (gmsh). NO solver, NO Julia, NO GPU - safe while a night runs.

Why this exists: ``hornlab-search run --dry-run`` calls ``worker.install_handlers()`` before its dry-run
branch, so it is not safe while a GPU night owns the solver host. This tool calls the mesher directly.

Usage (repo root)::

    .venv\\Scripts\\python.exe tools/shape_check.py examples/typologies/<folder>/*.yaml
    .venv\\Scripts\\python.exe tools/shape_check.py cfg.yaml --brief examples/briefs/<brief>.yaml
    .venv\\Scripts\\python.exe tools/shape_check.py cfg.yaml --save-mesh scratch/meshes   # keep mesh.msh for rendering
    .venv\\Scripts\\python.exe tools/shape_check.py cfg.yaml --geometry-only             # no gmsh: generator extents only

Columns: generator refusal, dofs vs the screen cap, mouth W x H and depth (bounding box, mm) vs the brief envelope,
and the driver coupling plane (mesh tag 2) vs the brief's exit diameter. Exit code 1 if any config fails.
"""
from __future__ import annotations

import argparse
import glob
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.config import load_config, mesh_spec  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.mesh import build  # noqa: E402
from hornlab_search.mesh.throat_check import fits_exit, throat_shape  # noqa: E402

#: Wall allowance added to the mouth/depth extents before the envelope comparison (mm). The bounding box
#: already includes the outer shell, so this is a small margin for the estimator's rounding only.
ENVELOPE_SLACK_MM = 0.5


def check(path: str, brief: str | None, mode: str, save_dir: Path | None, geometry_only: bool) -> dict:
    out = {"config": Path(path).stem, "ok": False, "note": ""}
    cfg = load_config(path, brief=brief)
    space = DesignSpace.from_config(cfg)
    design = space.seed
    err = design.params.get("_generator_error")
    if err:
        out["note"] = f"REFUSED by the generator: {err[:160]}"
        return out
    env = (cfg.brief or {}).get("envelope") or {}
    exit_r = ((cfg.brief or {}).get("driver") or {}).get("exit_radius_mm")
    exit_d = 2.0 * float(exit_r) if exit_r else None
    if geometry_only:
        from hornlab_search.design.generators import grid
        g = design.params.get("grid")
        if not isinstance(g, dict):
            out["note"] = "geometry-only needs a grid/rows generator config"
            return out
        spec = {k: v for k, v in g.items() if k != "knobs"}
        _pts, meta = grid.rows_grid_points(spec, g["knobs"], cfg.brief) if "rows" in g else (None, {})
        out.update(mouth_w=meta.get("mouth_w_mm"), mouth_h=meta.get("mouth_h_mm"), depth=meta.get("x_span_mm"))
        out["ok"] = True
        return out
    ms = mesh_spec(mode, cfg)
    work = Path(tempfile.mkdtemp(prefix="shape-check-"))
    try:
        mesh = build.build_mesh(design, ms, cfg, work, mode=mode)
        summ = build.read_msh_summary(Path(mesh.path))
        bb = mesh.bbox_m
        cad = design.params.get("cad") if isinstance(design.params, dict) else None
        if isinstance(cad, dict) and cad.get("tool") == "plughorn":
            # A cone mid horn: the driver face IS the cone, there is no compression-driver exit to match.
            fit, why = True, f"cone r {float(cad['cone_r_mm']):.0f} mm (no exit to match)"
        else:
            shape = throat_shape(mesh.path)
            fit, why = fits_exit(shape, exit_d)
        out.update(dofs=int(summ["n_nodes_used"]), cap=int(cfg.mesh.dof_cap(mode)), quadrants=mesh.quadrants,
                   mouth_w=2000.0 * bb[3], mouth_h=2000.0 * bb[4], depth=1000.0 * (bb[5] - bb[2]),
                   throat=why if fit is not None else "unknown", throat_ok=bool(fit))
        if save_dir is not None:
            dest = save_dir / Path(path).stem
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mesh.path, dest / "mesh.msh")
            out["saved"] = str(dest / "mesh.msh")
    except Exception as exc:  # noqa: BLE001 - one bad config must not stop the table
        out["note"] = f"MESH FAILED: {type(exc).__name__}: {str(exc)[:200]}"
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)
    over = []
    for key, lim in (("mouth_w", "max_mouth_w_mm"), ("mouth_h", "max_mouth_h_mm"), ("depth", "max_depth_mm")):
        if env.get(lim) is not None and out[key] > float(env[lim]) + ENVELOPE_SLACK_MM:
            over.append(f"{key} {out[key]:.0f} > {float(env[lim]):.0f}")
    out["envelope"] = "fits" if not over else "OVER: " + ", ".join(over)
    out["ok"] = out["dofs"] <= out["cap"] and not over and out["throat_ok"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("configs", nargs="+", help="config YAMLs (globs ok)")
    ap.add_argument("--brief", help="override the config's brief_file")
    ap.add_argument("--mode", default="screen", choices=("screen", "verify", "final"))
    ap.add_argument("--save-mesh", help="copy each mesh.msh to <dir>/<config>/mesh.msh (for tools/render)")
    ap.add_argument("--geometry-only", action="store_true", help="rows generators: extents without meshing")
    args = ap.parse_args(argv)
    paths = sorted({p for c in args.configs for p in (glob.glob(c) or [c])})
    save = Path(args.save_mesh) if args.save_mesh else None
    bad = 0
    print("| config | ok | dofs / cap | mouth W x H mm | depth mm | envelope | driver coupling | note |")
    print("|---|---|---|---|---|---|---|---|")
    for p in paths:
        try:
            r = check(p, args.brief, args.mode, save, args.geometry_only)
        except Exception as exc:  # noqa: BLE001
            r = {"config": Path(p).stem, "ok": False, "note": f"CONFIG ERROR: {type(exc).__name__}: {str(exc)[:200]}"}
        bad += 0 if r["ok"] else 1
        f = (lambda k, nd=0: "-" if r.get(k) is None else f"{r[k]:.{nd}f}")
        dofs = "-" if "dofs" not in r else f"{r['dofs']} / {r['cap']}"
        print(f"| {r['config']} | {'yes' if r['ok'] else 'NO'} | {dofs} | {f('mouth_w')} x {f('mouth_h')} | {f('depth')} | "
              f"{r.get('envelope', '-')} | {r.get('throat', '-')} | {r.get('note', '')} |")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
