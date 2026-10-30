"""Drawing-style renders: white faces of a mesh.msh + its true CAD edges (from ``cad_edges.py``).

Viz env (pyvista + meshio)::

    "%LOCALAPPDATA%/hornlab/vizenv/Scripts/python.exe" tools/render/render_lines.py mesh.msh edges.npz out_prefix

Writes ``<out>_front.png`` (orthographic, like a drawing's front view), ``<out>_iso.png`` and
``<out>_section.png`` (the x = 0 half, showing the axe head's side profile).
"""
import sys

import meshio
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True


def main():
    msh, edges_npz, out = sys.argv[1:4]
    m = meshio.read(msh)
    tri = [c.data for c in m.cells if c.type == "triangle"][0]
    pts = m.points * 1000.0
    surf = pv.PolyData(pts, np.c_[np.full(len(tri), 3), tri].ravel())
    lines = [v for _k, v in np.load(edges_npz).items()]
    zmax = pts[:, 2].max()
    span = max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1]))

    def poly(ls):
        out = pv.PolyData()
        for l in ls:
            out = out.merge(pv.lines_from_points(l)) if out.n_points else pv.lines_from_points(l)
        return out

    all_lines = poly(lines)
    half_lines = poly([l for l in lines if (l[:, 0] <= 1e-3).all()])
    for name in ("front", "iso", "section"):
        p = pv.Plotter(window_size=(1200, 900))
        p.set_background("white")
        shade = dict(color="#f4f2ec", smooth_shading=False, ambient=0.6, diffuse=0.45, specular=0.0)
        if name == "section":
            p.add_mesh(surf.clip(normal="x", origin=(0, 0, 0)), **shade)
            p.add_mesh(half_lines, color="black", line_width=2.0)
            p.camera_position = [(2.6 * span, 0, zmax / 2), (0, 0, zmax / 2 - 60), (0, 1, 0)]
            p.enable_parallel_projection()
        else:
            p.add_mesh(surf, **shade)
            p.add_mesh(all_lines, color="black", line_width=2.0)
            if name == "front":
                p.camera_position = [(0, 0, zmax + 3 * span), (0, 0, zmax), (0, 1, 0)]
                p.enable_parallel_projection()
            else:
                p.camera_position = [(-1.1 * span, 0.8 * span, zmax + 1.4 * span), (0, 0, zmax - 160), (0, 1, 0)]
        p.screenshot(f"{out}_{name}.png")
        p.close()
    print("ok", out)


if __name__ == "__main__":
    main()
