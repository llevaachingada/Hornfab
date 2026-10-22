"""Pre-solve surface checks on a written .msh: cheap, CPU-only, run before any GPU time.

Idea after Boundary Lab 0.5.0 (``mesh_topology.py``, ``mesh_quality.py``, ``symmetry.py``);
independent implementation. Three checks, each with its own failure class:

1. **Symmetry fundamental domain** (silent killer 2, geometry side): a reduced mesh must lie in
   the half/quarter its quadrants imply (``sizing.SYMMETRY_PLANE``: ``yz`` -> x >= 0, ``xz`` ->
   y >= 0), within ``max(1e-9 m, 1e-6 * extent)``. A violation is a mesher/convention bug, so it
   raises ``SymmetryMismatchError`` (stops the run; never scored as a bad candidate).
2. **Edge topology**: every edge must be shared by exactly two triangles, except open edges lying
   on an active symmetry plane (the reduced domain's legitimate boundary). Open edges elsewhere
   or non-manifold edges (> 2 triangles) make an exterior BEM surface invalid ->
   ``GeometryInvalidError`` (a refused candidate, classified ``invalid_geometry``).
3. **Near-coincident vertices**: distinct used vertices closer than ``8 * eps(float32) * scale``
   are unwelded seams -> ``GeometryInvalidError``.

Measured 2026-10-22 (cloud, real mesher b922e807a5, seed + random samples of osse_baseline,
icw_termination, throat_adapter, freeform_sculpt, freeform_hv, search_smoke): every mesh passes;
all open edges lie on the symmetry planes, zero non-manifold edges, zero near-coincident vertices
(closest pair ~1.5 mm vs a ~0.3 um tolerance). So the checks only catch genuinely broken meshes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..types import GeometryInvalidError

#: plane name (sizing.SYMMETRY_PLANE vocabulary) -> coordinate axis that is zero on it
_PLANE_AXIS = {"yz": 0, "xz": 1}


@dataclass(frozen=True)
class TopologyReport:
    n_edges: int
    open_edges: int                 # all edges used by exactly one triangle
    open_edges_on_planes: int       # of those, lying on an active symmetry plane
    nonmanifold_edges: int
    near_coincident: int
    min_vertex_spacing_m: float
    tolerance_m: float

    @property
    def bad_open_edges(self) -> int:
        return self.open_edges - self.open_edges_on_planes


def symmetry_planes(symmetry_plane: str | None) -> tuple[str, ...]:
    """'yz+xz' -> ('yz', 'xz'); None -> (). Raises on an unknown plane name."""
    if not symmetry_plane:
        return ()
    planes = tuple(p for p in symmetry_plane.split("+") if p)
    for p in planes:
        if p not in _PLANE_AXIS:
            raise ValueError(f"unknown symmetry plane {p!r} in {symmetry_plane!r}")
    return planes


def plane_tolerance_m(points: np.ndarray) -> float:
    pts = np.asarray(points, dtype=float)
    extent = float(np.max(np.ptp(pts, axis=0))) if len(pts) else 0.0
    return max(1e-9, 1e-6 * extent)


def check_fundamental_domain(points: np.ndarray, symmetry_plane: str | None) -> None:
    """Raise SymmetryMismatchError if a reduced mesh leaves its half/quarter domain."""
    from .build import SymmetryMismatchError          # local: build imports this module
    pts = np.asarray(points, dtype=float)
    tol = plane_tolerance_m(pts)
    for plane in symmetry_planes(symmetry_plane):
        ax = _PLANE_AXIS[plane]
        lo = float(pts[:, ax].min())
        if lo < -tol:
            raise SymmetryMismatchError(
                f"symmetry plane {plane!r} needs {'xy'[ax]} >= 0 but the mesh reaches "
                f"{'xy'[ax]} = {lo:.6g} m (tolerance {tol:.3g} m): the reduced mesh is not in its "
                "fundamental domain")


def analyze(points: np.ndarray, triangles: np.ndarray,
            symmetry_plane: str | None) -> TopologyReport:
    """Edge incidence + near-coincident vertices over the vertices the triangles use."""
    from scipy.spatial import cKDTree

    pts = np.asarray(points, dtype=float)
    tri = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
    edges = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    uniq, count = np.unique(edges, axis=0, return_counts=True)
    open_e = uniq[count == 1]
    tol = plane_tolerance_m(pts[np.unique(tri)])
    on_planes = np.zeros(len(open_e), dtype=bool)
    for plane in symmetry_planes(symmetry_plane):
        ax = _PLANE_AXIS[plane]
        on_planes |= np.all(np.abs(pts[open_e][:, :, ax]) <= tol, axis=1)

    used = pts[np.unique(tri)]
    scale = max(float(np.max(np.ptp(used, axis=0))), float(np.max(np.abs(used))))
    merge_tol = 8.0 * float(np.finfo(np.float32).eps) * scale
    if len(used) >= 2:
        dist, _ = cKDTree(used).query(used, k=2)
        near = int(np.count_nonzero(dist[:, 1] <= merge_tol))
        min_spacing = float(dist[:, 1].min())
    else:
        near, min_spacing = 0, float("nan")
    return TopologyReport(n_edges=int(len(uniq)), open_edges=int(len(open_e)),
                          open_edges_on_planes=int(on_planes.sum()),
                          nonmanifold_edges=int(np.count_nonzero(count > 2)),
                          near_coincident=near, min_vertex_spacing_m=min_spacing,
                          tolerance_m=merge_tol)


def check_surface(points: np.ndarray, triangles: np.ndarray,
                  symmetry_plane: str | None) -> TopologyReport:
    """All three checks; raises (see module docstring), else returns the report."""
    tri = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
    check_fundamental_domain(np.asarray(points, dtype=float)[np.unique(tri)], symmetry_plane)
    rep = analyze(points, tri, symmetry_plane)
    problems = []
    if rep.bad_open_edges:
        problems.append(f"{rep.bad_open_edges} open edge(s) off the symmetry planes")
    if rep.nonmanifold_edges:
        problems.append(f"{rep.nonmanifold_edges} non-manifold edge(s)")
    if rep.near_coincident:
        problems.append(f"{rep.near_coincident} near-coincident vertices (closest "
                        f"{rep.min_vertex_spacing_m:.3g} m, tolerance {rep.tolerance_m:.3g} m)")
    if problems:
        raise GeometryInvalidError("exterior BEM surface is not closed/manifold: "
                                   + "; ".join(problems))
    return rep
