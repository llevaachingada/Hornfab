"""Dump the true CAD edges of a ``plughorn`` design as polylines (mm) for drawing-style renders.

Run with the project venv (build123d); ``render_lines.py`` (viz env) draws them over the BEM mesh.

    .venv\\Scripts\\python.exe tools/render/cad_edges.py examples/typologies/cone_plughorn_2026-10-28/X.yaml out.npz
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    cfg_path, out = argv[0], argv[1]
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh import step_build
    cfg = load_config(cfg_path)
    cad = DesignSpace.from_config(cfg).seed.params["cad"]
    tool = step_build.load_cad_tool(tool=cad["tool"])
    part = tool.build_body(tool.params_from_recipe(cad))
    lines = []
    for e in part.edges():
        n = 2 if e.geom_type.name == "LINE" else 40
        lines.append(np.array([tuple(e.position_at(t)) for t in np.linspace(0, 1, n)]))
    np.savez(out, *lines)
    print(f"{len(lines)} edges -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
