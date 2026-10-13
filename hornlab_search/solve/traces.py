"""Boundary-trace capture and exact exterior-field recovery (05_TASK_SOLVE item 4b).

Facts (TOOLCHAIN C2b, confirmed in ``hornlab_beat_bem`` 0.2.0 source):

* ``SolveConfig(surface_traces=True)`` makes the solver return the boundary Cauchy datum per
  frequency, in the same unit-normal-acceleration convention as the far field:
  ``surface_pressure_complex (F, n_vertices)`` is the P1 pressure BY NODE and
  ``surface_neumann_complex (F, n_faces)`` the DP0 normal derivative BY ELEMENT.
* The Julia loader (``load_gmsh22_with_tags``) keeps the ``.msh`` node order and the ``.msh``
  triangle order, with no merging. So a trace vector is indexed by the file's own nodes
  (pressure) and triangles (Neumann). Under a symmetry-reduced solve both cover the reduced
  (fundamental-domain) mesh only, which is exactly the mesh in the file.
* ``hornlab_bempp_bem.evaluate_exterior_from_traces`` wants coefficient vectors in BEMPP's DOF
  order, which is not guaranteed to equal file order. ``dof_permutations`` recovers the map by
  matching coordinates (P1 dof interpolation points <-> file nodes; DP0 interpolation points <->
  triangle centroids) and REFUSES unless the match is one-to-one to 1e-9 m. Nothing is guessed.

``field_from_traces`` is the exact boundary-integral step. It is NEVER learned (11_PHASE2).

Trace dict returned by ``package_traces`` / ``capture_traces`` (all arrays, npz-friendly):
  points (nv,3)          node coordinates, file order, metres   [pressure ordering]
  face_centroids (nf,3)  triangle centroids, file order, metres [neumann ordering]
  face_normals (nf,3)    unit normals from (v2-v1)x(v3-v1)
  pressure (F,nv) c128   P1 pressure by node
  neumann  (F,nf) c128   DP0 dp/dn by element
  freqs_hz (F,)
  ordering               str, describes the two orderings
  mesh_path, symmetry_plane (str / None)
"""
from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import numpy as np

from ..constants import C_AIR
from ..types import MeshResult, SolveSpec

log = logging.getLogger("hornlab_search.solve.traces")

MATCH_TOL_M = 1e-9
ORDERING = "pressure=node (.msh node order), neumann=element (.msh triangle order); " \
           "both cover the solved (symmetry-reduced) mesh only"


class TraceOrderingError(RuntimeError):
    """The trace vectors cannot be mapped to BEMPP dof order one-to-one."""


# ------------------------------------------------------------------ reading the .msh (read only)


def read_msh_geometry(path) -> tuple[np.ndarray, np.ndarray]:
    """(nodes (nv,3) in file order, faces (nf,3) 0-based node rows in file order).

    Parses exactly what the Julia loader parses: every ``$Nodes`` row with >= 4 fields, every
    element of gmsh type 2 (3-node triangle) whose three nodes exist. Read only; this is not a
    mesh writer.
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    i0 = lines.index("$Nodes")
    n_nodes = int(lines[i0 + 1])
    ids, xyz = [], []
    for row in lines[i0 + 2: i0 + 2 + n_nodes]:
        f = row.split()
        if len(f) >= 4:
            ids.append(int(f[0]))
            xyz.append([float(f[1]), float(f[2]), float(f[3])])
    nodes = np.asarray(xyz, dtype=float)
    row_of = {gid: i for i, gid in enumerate(ids)}
    j0 = lines.index("$Elements")
    n_el = int(lines[j0 + 1])
    faces = []
    for row in lines[j0 + 2: j0 + 2 + n_el]:
        f = row.split()
        if len(f) < 8 or int(f[1]) != 2:
            continue
        try:
            faces.append([row_of[int(f[-3])], row_of[int(f[-2])], row_of[int(f[-1])]])
        except KeyError:
            continue
    return nodes, np.asarray(faces, dtype=np.int64).reshape(-1, 3)


def package_traces(mesh: MeshResult, spec: SolveSpec, raw_traces: dict) -> dict:
    """Attach geometry and ordering metadata to ``{'pressure','neumann'}`` from a traced solve."""
    nodes, faces = read_msh_geometry(mesh.path)
    p = np.asarray(raw_traces["pressure"])
    q = np.asarray(raw_traces["neumann"])
    nf = len(spec.freqs_hz)
    if p.shape != (nf, nodes.shape[0]):
        raise TraceOrderingError(
            f"surface_pressure {p.shape} != (n_freqs={nf}, n_nodes_in_file={nodes.shape[0]}): "
            f"the solver's vertex set is not the file's node set")
    if q.shape != (nf, faces.shape[0]):
        raise TraceOrderingError(
            f"surface_neumann {q.shape} != (n_freqs={nf}, n_triangles_in_file={faces.shape[0]})")
    v1, v2, v3 = nodes[faces[:, 0]], nodes[faces[:, 1]], nodes[faces[:, 2]]
    cross = np.cross(v2 - v1, v3 - v1)
    normals = cross / np.linalg.norm(cross, axis=1, keepdims=True)
    return {
        "points": nodes, "face_centroids": (v1 + v2 + v3) / 3.0, "face_normals": normals,
        "pressure": p.astype(np.complex128), "neumann": q.astype(np.complex128),
        "freqs_hz": np.asarray(spec.freqs_hz, dtype=float), "ordering": ORDERING,
        "mesh_path": str(mesh.path), "symmetry_plane": mesh.symmetry_plane,
    }


def capture_traces(mesh: MeshResult, spec: SolveSpec, backend_cfg=None, *, backend=None) -> dict | None:
    """Solve once with ``surface_traces=True`` and return the packaged trace dict, or None if the
    backend cannot produce traces (beat not importable, or the result carries none).

    ``backend_cfg`` is an optional ``hornlab_beat_bem.SolveConfig``; its ``surface_traces`` is
    forced on. ``backend`` is an existing ``BeatBackend`` to reuse (keeps the warm worker).
    Off by default in the pipeline: capture for 1 design in 20, never for every candidate.
    Raises on solver failure (a failed capture is not "unavailable").
    """
    try:
        from .beat import BeatBackend
    except ImportError:
        return None
    be = backend or BeatBackend(getattr(backend_cfg, "beat_backend", "cuda"))
    cfg = dataclasses.replace(backend_cfg, surface_traces=True) if backend_cfg is not None else None
    raw = be.solve_raw(mesh, spec, surface_traces=True, cfg=cfg)
    if getattr(raw, "surface_pressure_complex", None) is None:
        log.warning("solver returned no surface traces")
        return None
    return package_traces(mesh, spec, {"pressure": raw.surface_pressure_complex,
                                       "neumann": raw.surface_neumann_complex})


# ------------------------------------------------------------------ dof order recovery


def _match_points(file_pts: np.ndarray, dof_pts: np.ndarray, what: str, tol: float) -> np.ndarray:
    """perm with ``dof_pts[i] == file_pts[perm[i]]``; raises unless one-to-one within ``tol``."""
    from scipy.spatial import cKDTree
    if file_pts.shape != dof_pts.shape:
        raise TraceOrderingError(
            f"{what}: file has {file_pts.shape[0]} entries but BEMPP has {dof_pts.shape[0]} dofs")
    dist, idx = cKDTree(file_pts).query(dof_pts)
    if float(dist.max()) > tol:
        raise TraceOrderingError(f"{what}: dof/file point mismatch, worst {float(dist.max()):.3e} m > {tol:g}")
    if np.unique(idx).size != idx.size:
        raise TraceOrderingError(
            f"{what}: the match is not one-to-one ({idx.size - np.unique(idx).size} file entries "
            f"claimed twice): duplicate seam nodes or a different mesh")
    return idx


def _spaces(loaded, symmetry_plane):
    """(p1_space, dp0_space) exactly as ``evaluate_exterior_from_traces`` builds them."""
    import bempp_cl.api as bempp_api
    if symmetry_plane is None:
        return (bempp_api.function_space(loaded.grid, "P", 1),
                bempp_api.function_space(loaded.grid, "DP", 0))
    from hornlab_bempp_bem.symmetry import build_symmetry_context
    ctx = build_symmetry_context(loaded.grid, np.asarray(loaded.physical_tags, dtype=np.int32),
                                 symmetry_plane)
    return ctx.reduced_p1, ctx.reduced_dp0


def _dof_points(space, vertices: np.ndarray, elements: np.ndarray, per_element_centroid: bool) -> np.ndarray:
    """(n_dof, 3) coordinates of each global dof of a bempp P1 / DP0 space, from its
    ``local2global`` table (element e, local shape function i -> global dof) and the grid's own
    ``vertices (3, nv)`` / ``elements (3, ne)``. P1: the vertex a dof sits on; DP0: the element
    centroid. Every dof must be hit and always at the same point, or this raises."""
    l2g = np.asarray(space.local2global)
    n = int(space.global_dof_count)
    pts = np.full((n, 3), np.nan)
    ne = elements.shape[1]
    for i in range(l2g.shape[1]):
        dofs = l2g[:, i]
        if per_element_centroid:
            xyz = vertices[:, elements].mean(axis=1).T                    # (ne, 3)
        else:
            xyz = vertices[:, elements[i]].T                              # (ne, 3)
        have = ~np.isnan(pts[dofs, 0])
        if np.any(have) and np.abs(pts[dofs[have]] - xyz[have]).max() > 1e-12:
            raise TraceOrderingError("a bempp dof maps to two different points")
        pts[dofs] = xyz
    if np.isnan(pts).any():
        raise TraceOrderingError(f"{int(np.isnan(pts[:, 0]).sum())} of {n} bempp dofs touch no element")
    return pts


def dof_permutations(loaded, traces: dict, tol: float = MATCH_TOL_M) -> tuple[np.ndarray, np.ndarray]:
    """(perm_p1, perm_dp0): ``pressure_bempp = pressure_file[..., perm_p1]`` and likewise for
    the Neumann trace. Coordinate matching, one-to-one or it raises ``TraceOrderingError``.

    Measured on the seed horn (quarter, 'yz+xz'): bempp's grid vertices and elements ARE the
    file's nodes and triangles in file order, and the symmetry context's reduced P1 space has one
    dof per vertex in vertex order, so both permutations are the identity. (The plain
    ``function_space(grid, 'P', 1)`` of an OPEN reduced mesh drops the free-boundary vertices
    and has fewer dofs than nodes; that space is not the one used with a symmetry plane.)"""
    p1, dp0 = _spaces(loaded, traces.get("symmetry_plane"))
    v = np.asarray(loaded.grid.vertices, dtype=float)
    e = np.asarray(loaded.grid.elements, dtype=np.int64)
    pp = _dof_points(p1, v, e, per_element_centroid=False)
    qq = _dof_points(dp0, v, e, per_element_centroid=True)
    return (_match_points(np.asarray(traces["points"], float), pp, "P1 pressure", tol),
            _match_points(np.asarray(traces["face_centroids"], float), qq, "DP0 neumann", tol))


def field_from_traces(traces: dict, points_m: np.ndarray, freqs_hz: np.ndarray) -> np.ndarray:
    """Exact exterior boundary-integral evaluation. Wraps
    ``hornlab_bempp_bem.evaluate_exterior_from_traces``.

    THIS STEP IS EXACT AND IS NEVER LEARNED. It is how a learned Dirichlet-to-Neumann map
    becomes a polar in phase 2, and how such a map is checked for physically valid boundary data.

    ``points_m`` (N,3) in metres, ``freqs_hz`` a subset of ``traces['freqs_hz']`` (matched to
    1e-6 relative). Returns (len(freqs_hz), N) complex pressure in the solver's convention
    (unit normal acceleration, exp(-i omega t)), i.e. directly comparable to ``Response.p_h``.
    """
    import hornlab_bempp_bem as bempp
    from hornlab_bempp_bem import evaluate_exterior_from_traces

    pts = np.asarray(points_m, dtype=float)
    want = np.atleast_1d(np.asarray(freqs_hz, dtype=float))
    have = np.asarray(traces["freqs_hz"], dtype=float)
    rows = []
    for f in want:
        j = int(np.argmin(np.abs(have - f)))
        if abs(have[j] - f) > 1e-6 * f:
            raise ValueError(f"frequency {f} Hz is not in the captured traces {have.tolist()}")
        rows.append(j)
    loaded = bempp.load_mesh(traces["mesh_path"], scale=1.0, native_symmetry_plane=traces.get("symmetry_plane"))
    perm_p, perm_q = dof_permutations(loaded, traces)
    out = np.empty((want.size, pts.shape[0]), dtype=np.complex128)
    for i, j in enumerate(rows):
        out[i] = evaluate_exterior_from_traces(
            loaded, float(have[j]), 2.0 * np.pi * float(have[j]) / C_AIR,
            np.asarray(traces["pressure"])[j][perm_p], np.asarray(traces["neumann"])[j][perm_q],
            pts, symmetry_plane=traces.get("symmetry_plane"))
    return out


def cut_points(angles_deg: np.ndarray, distance_m: float, plane: str) -> np.ndarray:
    """Observation points the solver uses: H = (R sin a, 0, R cos a), V = (0, R sin a, R cos a)."""
    a = np.radians(np.asarray(angles_deg, dtype=float))
    s, c = distance_m * np.sin(a), distance_m * np.cos(a)
    z = np.zeros_like(a)
    if plane == "horizontal":
        return np.column_stack([s, z, c])
    if plane == "vertical":
        return np.column_stack([z, s, c])
    raise ValueError(f"plane must be 'horizontal' or 'vertical', got {plane!r}")
