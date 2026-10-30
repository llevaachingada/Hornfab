"""Render horn meshes to PNG views (pyvista, off-screen). Runs in the viz env, NOT the project venv.

Targets (each ``label=PATH`` or just ``PATH``; PATH may be):
  * a mesh file (``.../mesh.msh``),
  * a design dir (``runs/<run>/designs/<hash>``),
  * a run dir (``runs/<run>``) -> its best design (best.json).
Quarter/half meshes are mirrored to the full horn.

Views: ``a`` front 3/4, ``b`` behind 3/4 (the underside / outer shell), ``c`` straight-on front, ``s`` side,
``u`` from below. Colors: ``gray`` (report style) or ``apricot`` (organic shapes).

Setup once (CPU wheels, ~200 MB):  py -3 -m venv "%LOCALAPPDATA%/hornlab/vizenv" && "%LOCALAPPDATA%/hornlab/vizenv/Scripts/pip" install pyvista meshio
Usage (repo root)::

    "%LOCALAPPDATA%/hornlab/vizenv/Scripts/python.exe" tools/render/render_views.py --out scratch/r --views a,b,s runs/<run> clover=scratch/m/clover/mesh.msh

Writes ``<out>/<label>_<view>.png`` and ``<out>/targets.json`` (label -> mesh, run dir, design hash) for compose.py.
It uses the GPU's OpenGL for a few seconds; harmless next to a running solve (a few hundred MB of VRAM at most).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import meshio
import numpy as np
import pyvista as pv

VIEWS = {"a": (0.55, 0.38, 1.0), "b": (1.0, 0.55, -0.45), "c": (0.0, 0.02, 1.0), "s": (1.0, 0.05, 0.05),
         "u": (0.25, -1.0, 0.35)}
COLORS = {"gray": ((0.62, 0.64, 0.67), (0.25, 0.26, 0.28)), "apricot": ((0.86, 0.62, 0.26), (0.35, 0.25, 0.12))}


def resolve(target: str) -> dict:
    label, _, path = target.rpartition("=") if "=" in target else ("", "", target)
    p = Path(path)
    run_dir = design_hash = None
    if p.suffix == ".msh":
        mesh = p
        if p.parent.parent.name == "designs":
            run_dir, design_hash = p.parent.parent.parent, p.parent.name
    elif (p / "mesh.msh").exists():
        mesh = p / "mesh.msh"
        if p.parent.name == "designs":
            run_dir, design_hash = p.parent.parent, p.name
    elif (p / "best.json").exists():
        design_hash = json.loads((p / "best.json").read_text(encoding="utf-8"))["design_hash"]
        run_dir, mesh = p, p / "designs" / design_hash / "mesh.msh"
    else:
        raise SystemExit(f"cannot find a mesh for {target!r} (mesh.msh, design dir or run dir with best.json)")
    return {"label": label or (design_hash or p.stem), "mesh": str(mesh),
            "run_dir": str(run_dir) if run_dir else None, "design_hash": design_hash}


def load_full(mesh_path: str) -> pv.PolyData:
    m = meshio.read(mesh_path)
    tri = np.vstack([c.data for c in m.cells if c.type == "triangle"])
    pts = m.points
    for ax in (0, 1):                       # mirror the symmetry planes of quarter / half models
        if pts[:, ax].min() > -1e-6:
            q = pts.copy()
            q[:, ax] *= -1
            tri = np.vstack([tri, tri[:, ::-1] + len(pts)])
            pts = np.vstack([pts, q])
    faces = np.hstack([np.full((len(tri), 1), 3), tri]).ravel()
    return pv.PolyData(pts * 1000.0, faces).clean(tolerance=1e-4).compute_normals(split_vertices=True, feature_angle=50)


def render(mesh: pv.PolyData, view: str, color: str, out: Path, size: int) -> None:
    body, edge = COLORS[color]
    c = np.array(mesh.center)
    extent = np.ptp(np.array(mesh.points), axis=0).max()
    p = pv.Plotter(off_screen=True, window_size=(size, size), lighting="none")
    p.set_background("white")
    p.add_mesh(mesh, color=body, smooth_shading=True, ambient=0.33, diffuse=0.74, specular=0.2, specular_power=18,
               silhouette=dict(color=edge, line_width=1.3))
    d = np.array(VIEWS[view], float)
    d /= np.linalg.norm(d)
    p.camera_position = [tuple(c + d * extent * 2.6), tuple(c), (0, 1, 0)]
    p.camera.view_angle = 30
    for pos, inten in (((-1.0, 1.2, 1.0), 1.0), ((1.2, -0.2, 0.8), 0.5), ((0.3, 1.0, -1.2), 0.4)):
        p.add_light(pv.Light(position=pos, focal_point=(0, 0, 0), light_type="camera light", intensity=inten))
    p.enable_ssao(radius=extent * 0.03, bias=0.5, kernel_size=64, blur=True)
    p.enable_anti_aliasing("ssaa")
    p.reset_camera()
    p.camera.zoom(1.1)
    p.screenshot(out)
    p.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", default="a,b,s")
    ap.add_argument("--color", default="gray", choices=sorted(COLORS))
    ap.add_argument("--size", type=int, default=1000)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    targets = [resolve(t) for t in args.targets]
    for t in targets:
        mesh = load_full(t["mesh"])
        for v in args.views.split(","):
            render(mesh, v, args.color, out / f"{t['label']}_{v}.png", args.size)
        print("ok", t["label"])
    prev = json.loads((out / "targets.json").read_text(encoding="utf-8")) if (out / "targets.json").exists() else {}
    prev.update({t["label"]: t for t in targets})
    (out / "targets.json").write_text(json.dumps(prev, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
