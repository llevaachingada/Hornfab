import sys, json
from pathlib import Path
import numpy as np
import pyvista as pv
sys.path.insert(0, "tools/render")
import render_views as rv

rv.VIEWS["t"] = (0.35, 0.9, 0.5)  # top-skewed, from +y (up axis of the render camera)
OUT = Path("scratch/last_day/r"); OUT.mkdir(parents=True, exist_ok=True)

def segments(cut):
    segs = []
    if cut is None or cut.n_points == 0:
        return np.zeros((0, 2, 2))
    lines = cut.lines
    i = 0
    while i < len(lines):
        n = lines[i]; ids = lines[i + 1:i + 1 + n]; i += n + 1
        pts = cut.points[ids]
        for a, b in zip(pts[:-1], pts[1:]):
            segs.append([a, b])
    return np.array(segs)

rows = [l.split() for l in Path(sys.argv[1] if len(sys.argv) > 1 else "scratch/last_day/targets.txt").read_text().splitlines() if l.strip()]
for run_dir, h in rows:
    mesh_path = Path(run_dir) / "designs" / h / "mesh.msh"
    try:
        mesh = rv.load_full(str(mesh_path))
        rv.render(mesh, "a", "gray", OUT / f"{h}_iso.png", 1400)
        rv.render(mesh, "t", "gray", OUT / f"{h}_top.png", 1400)
        # mesh is in mm; axis z = horn axis, y = vertical, x = horizontal
        vcut = mesh.slice(normal=(1, 0, 0), origin=(0, 0, 0))  # plane x=0: vertical meridian
        hcut = mesh.slice(normal=(0, 1, 0), origin=(0, 0, 0))  # plane y=0: horizontal meridian
        vs = segments(vcut)[:, :, [2, 1]]   # (z, y)
        hs = segments(hcut)[:, :, [2, 0]]   # (z, x)
        np.savez(OUT / f"{h}_sec.npz", vseg=vs, hseg=hs)
        print("ok", h, len(vs), len(hs), flush=True)
    except Exception as e:
        print("FAIL", h, repr(e), flush=True)
