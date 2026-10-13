"""Frequency -> mesher resolution, and the dof budget (01_CONTRACTS section 6).

Offline module: imports only numpy/math and ``hornlab_search.constants``. Nothing here
hardcodes a dof cap or ``dof_per_triangle``; both come from the Config (``MeshSettings``) so
they can change in YAML when TOOLCHAIN.md's measured VRAM ceiling is final.

``SYMMETRY_PLANE`` and ``QUADRANT_FACTOR`` are the ONLY place the quadrants -> solver-flag
mapping exists (silent killer #2 in 00_ORCHESTRATOR.md). ``solve/`` imports them from here.
"""
from __future__ import annotations

import math

from ..constants import C_AIR

QUADRANT_FACTOR: dict[str, int] = {"1234": 1, "12": 2, "14": 2, "1": 4}
SYMMETRY_PLANE: dict[str, str | None] = {"1234": None, "12": "xz", "14": "yz", "1": "yz+xz"}

# Mirror of hornlab_mesher.mesh_sizing.TRIANGLES_PER_AREA_OVER_H2 (N ~= 2.3 * A / h^2). Kept as a
# local constant so this module stays importable with nothing installed; a mesher-gated test
# asserts the two are equal.
TRIANGLES_PER_AREA_OVER_H2 = 2.3

# EFFECTIVE triangles per (area / mouth_res^2) of the solved mesh when the throat is meshed at
# res/2 (as res_mm_for does) and the mesher's wall-clearance guard is active. Measured at CP-2 on
# the shipped seeds at 10 kHz, epw 6, quarter domain: OSSE 2.8, ICW 3.4, FREEFORM 3.1 (it falls
# toward the uniform 2.3 only as the mesh gets much finer than the wall). The default used by
# triangles_for / f_max_for_dofs is the middle of that range, so a budget does not over-promise
# frequency by more than ~10-15 % for any shipped family.
EFFECTIVE_TRI_PER_AREA_H2 = 3.0


def _check_quadrants(quadrants: str) -> int:
    try:
        return QUADRANT_FACTOR[quadrants]
    except KeyError:
        raise ValueError(f"quadrants must be one of {list(QUADRANT_FACTOR)}, got {quadrants!r}") from None


def res_mm_for(epw: float, f_max_hz: float) -> dict:
    """res = 1000 * C_AIR / (epw * f_max). Returns {'throat': res/2, 'mouth': res, 'rear': res}.
    Finer at the throat, where the field is strongest."""
    if epw <= 0 or f_max_hz <= 0:
        raise ValueError(f"epw and f_max_hz must be positive, got epw={epw!r} f_max_hz={f_max_hz!r}")
    res = 1000.0 * C_AIR / (epw * f_max_hz)
    return {"throat": res / 2.0, "mouth": res, "rear": res}


def max_triangles_for(dof_cap: int, quadrants: str, dof_per_triangle: float,
                      slack: float = 1.15) -> int:
    """FULL-DOMAIN-EQUIVALENT ceiling:
         tri_solved = dof_cap / dof_per_triangle
         tri_full   = tri_solved * QUADRANT_FACTOR[quadrants]
         return ceil(tri_full * slack)
    The product is rounded to 6 decimals before ceil so float noise (73600.00000000001) cannot
    add a triangle."""
    qf = _check_quadrants(quadrants)
    if dof_per_triangle <= 0:
        raise ValueError(f"dof_per_triangle must be positive, got {dof_per_triangle!r}")
    tri_full = (dof_cap / dof_per_triangle) * qf
    return int(math.ceil(round(tri_full * slack, 6)))


def estimate_dofs(n_triangles: int, quadrants: str, dof_per_triangle: float) -> int:
    """n_triangles is what the .msh contains (already reduced by the quadrant factor), so
    ``quadrants`` only validates; the measured ``dof_per_triangle`` already folds in the
    symmetry-plane boundary overhead (TOOLCHAIN M1: 0.500 full domain, ~0.51 quarter)."""
    _check_quadrants(quadrants)
    return int(math.ceil(round(n_triangles * dof_per_triangle, 6)))


def dof_cap_for(mesh_spec, settings, mode: str | None = None) -> int:
    """The dof cap that applies to ``mesh_spec``.

    ``settings`` is ``Config.mesh`` (MeshSettings). With ``mode`` given it is simply
    ``settings.dof_cap(mode)``. Without it, find the mode whose ``max_triangles`` this spec
    carries (either of the two forward formulas in use: ``max_triangles_for`` here, and
    ``config.mesh_spec``'s ``ceil(2 * cap * qf * slack)``); if no mode matches, invert
    ``max_triangles_for`` so hand-built specs still get a consistent cap.
    """
    if mode is not None:
        return int(settings.dof_cap(mode))
    qf = _check_quadrants(mesh_spec.quadrants)
    slack = float(getattr(settings, "max_triangle_slack", 1.15))
    dpt = float(settings.dof_per_triangle)
    for m in ("screen", "verify", "final"):
        cap = int(settings.dof_cap(m))
        if mesh_spec.max_triangles in (max_triangles_for(cap, mesh_spec.quadrants, dpt, slack),
                                       int(math.ceil(round(2 * cap * qf * slack, 6)))):
            return cap
    return int(round(mesh_spec.max_triangles / (qf * slack) * dpt))


def triangles_for(area_m2: float, epw: float, f_max_hz: float, quadrants: str,
                  tri_per_area_h2: float = EFFECTIVE_TRI_PER_AREA_H2) -> float:
    """Triangles the SOLVED (reduced) mesh holds for a surface of full-domain area ``area_m2``
    meshed at ``res_mm_for(epw, f_max_hz)['mouth']`` everywhere. Forward half of the chain
    that ``f_max_for_dofs`` inverts."""
    qf = _check_quadrants(quadrants)
    h_mm = res_mm_for(epw, f_max_hz)["mouth"]
    return tri_per_area_h2 * (area_m2 * 1e6 / qf) / (h_mm * h_mm)


def f_max_for_dofs(dof_cap, area_m2, epw, quadrants, dof_per_triangle,
                   tri_per_area_h2: float = EFFECTIVE_TRI_PER_AREA_H2) -> float:
    """Inverse of the sizing chain. Used by --dry-run and by the report to say what frequency a
    budget actually buys.

    ``area_m2`` is the FULL-DOMAIN surface area (a quarter-mesh area times 4). Chain:
        tri_solved = dof_cap / dof_per_triangle
        h_mm       = sqrt(tri_per_area_h2 * (area_m2*1e6/qf) / tri_solved)
        f_max      = 1000 * C_AIR / (epw * h_mm)
    """
    qf = _check_quadrants(quadrants)
    if dof_cap <= 0 or area_m2 <= 0 or epw <= 0 or dof_per_triangle <= 0:
        raise ValueError("dof_cap, area_m2, epw and dof_per_triangle must all be positive")
    tri_solved = dof_cap / dof_per_triangle
    h_mm = math.sqrt(tri_per_area_h2 * (area_m2 * 1e6 / qf) / tri_solved)
    return 1000.0 * C_AIR / (epw * h_mm)
