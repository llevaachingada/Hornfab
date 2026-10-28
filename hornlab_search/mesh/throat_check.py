"""Is the solved throat the driver's exit? Round, and the exit's diameter (owner rule, 2026-10-27).

Owner decision: a horn is modelled and printed WITHOUT a separate throat adapter. The coupling plane (the
driven source patch, where the compression driver bolts on) must be round at the driver exit diameter;
right after it the horn may morph, carry ridges and go non-round. This module checks only that plane.
Measured on the v4 campaign winners: OSSE / R-OSSE ``aspect_ratio`` stretches the throat too (24 x 36,
26 x 36, 41 x 36, 50 x 36 mm on 36 mm briefs), while the generator families, ATH core and every
aspect-1 cell solve a round throat of the right size. This module reads the driven surface (mesh
physical tag 2) of a stored mesh and reports its width, height and roundness; it does not decide
anything for the search (report-only until wired in as a pre-solve refusal).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

#: Width or height may differ from the exit diameter by this much and still count as matching.
FIT_TOL_MM = 0.5
#: Area / (pi/4 W H) of a round (or elliptical) opening is 1; a superellipse is larger. Allowed slack.
ROUND_AREA_TOL = 0.03

SOURCE_TAG = 2


def throat_shape(mesh_path) -> dict:
    """``width_mm``, ``height_mm``, ``area_mm2`` (full opening, mirrored for quarter/half meshes) and
    ``roundness`` = area / (pi/4 W H) (1.0 for a circle or ellipse). NaNs when the mesh is unreadable."""
    nan = float("nan")
    out = {"width_mm": nan, "height_mm": nan, "area_mm2": nan, "roundness": nan}
    try:
        import meshio
        m = meshio.read(Path(mesh_path))
        tri = m.cells_dict["triangle"]
        tag = m.cell_data_dict["gmsh:physical"]["triangle"]
        src = tri[tag == SOURCE_TAG]
        pts = m.points
        span, copies = [], 1
        for k in (0, 1):
            v = pts[np.unique(src)][:, k]
            mirrored = v.min() > -1e-6           # quarter/half mesh: this axis is a symmetry plane
            span.append(2000.0 * v.max() if mirrored else 1000.0 * (v.max() - v.min()))
            copies *= 2 if mirrored else 1
        a, b, c = pts[src[:, 0]], pts[src[:, 1]], pts[src[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() * 1e6 * copies
        out.update(width_mm=span[0], height_mm=span[1], area_mm2=float(area),
                   roundness=float(area / (math.pi / 4.0 * span[0] * span[1])))
    except Exception:  # noqa: BLE001 - report-only
        pass
    return out


def fits_exit(shape: dict, exit_diameter_mm: float | None) -> tuple[bool | None, str]:
    """(fits, reason). None when it cannot be judged (no exit diameter or unreadable mesh)."""
    w, h, rnd = shape.get("width_mm"), shape.get("height_mm"), shape.get("roundness")
    if not exit_diameter_mm or not all(isinstance(x, float) and math.isfinite(x) for x in (w, h, rnd)):
        return None, "unknown"
    bad = []
    if abs(w - exit_diameter_mm) > FIT_TOL_MM or abs(h - exit_diameter_mm) > FIT_TOL_MM:
        bad.append(f"{w:.1f} x {h:.1f} mm vs {exit_diameter_mm:.1f} mm exit")
    if abs(rnd - 1.0) > ROUND_AREA_TOL:
        bad.append(f"not round (area {rnd:.2f}x an ellipse of that size)")
    return (not bad), ("; ".join(bad) or "round, matches the exit")
