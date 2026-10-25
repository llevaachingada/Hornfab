"""GRID adapter: point grid (mm) -> .msh in METRES -> the same ``MeshResult`` as ``mesh/build.py``.

This is **not** a mesher: gmsh authoring stays inside ``hornlab_mesher``. It wraps the
point-grid builder with the closure mode the measured probe found BEM-usable
(``NOTES_FOR_SENIOR.md`` 2026-10-24, point-grid curl acceptance)::

    PointGridHornGeometry(inner_points=mm grid (n_phi, n_s + 1, 3),
                          closed=False, outer_points=explicit outer shell,
                          wall_thickness_mm=t, source_shape=1,
                          source_auto_angle_deg=<throat angle from the grid meta>,
                          symmetry_planes=("x", "y"))            # quarter model
    MeshDensity(throat_res_mm=..., mouth_res_mm=..., rear_res_mm=...,
                aperture_res_scale=1.0, max_triangles=..., allow_large_mesh=False)

A freestanding point-grid build **requires explicit ``outer_points``** -- without them the
mesher resolves BARE (inner wall + throat cap only), which is not a closed BEM surface. This
module therefore always builds the shell via ``grid.grid_outer_points`` when the caller does not
supply one.

MODE-DEPENDENT since WP12: when the run's brief carries ``mounting`` (a rear enclosure), the
route builds **no** outer shell at all and passes ``enclosure=HornEnclosure(...)`` instead --
``PointGridHornGeometry`` refuses enclosure + outer_points together (geometry.py:316-320), and
the enclosure builder supplies the closed domain. ``closed=False`` and the symmetry planes stay
exactly as for the freestanding route (reduced-domain cut planes are the enclosure builder's
job); only ``outer_points``/``wall_thickness_mm`` change.

Every guard after the build is the SAME code ``mesh/build.py`` runs (imported, not copied), so
the two routes cannot drift:

* bbox in ``[0.02, 5.0] m``                        -> ``MeshUnitsError``
* mesher triangle count vs the .msh                -> ``MeshConsistencyError``
* source tag 2 (SD1D1001) non-empty                -> ``GeometryInvalidError``
* dofs (``sizing.estimate_dofs`` / vertices) > cap -> ``MeshTooLargeError``
* ``topology.check_surface`` for the plane from
  ``sizing.SYMMETRY_PLANE[mesh.quadrants]``       -> ``GeometryInvalidError`` /
  ``SymmetryMismatchError``

Quadrants and the symmetry plane come from ONE source, ``sizing.SYMMETRY_PLANE``, exactly as in
``mesh/build.py`` (silent killer #2).  Two models ship: the QUARTER grid (``"1"``, G8/G9 even in
``phi``) and the HALF grid (``"14"``, plane yz, x >= 0) that the lecleach_mod b-terms / axial bend
force.  The grid meta's ``half_model`` is the single source of the model; a mismatch with
``mesh.quadrants`` is refused before the mesher runs rather than silently mirroring wrong.

No mesh cache: ``build.mesh_cache_key`` hashes a ``Design``, which a GRID run does not have. See
the wire-in note at the bottom of this module.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..design import families
from ..design.generators import grid as grid_gen
from ..types import GeometryInvalidError, MeshResult, MeshTooLargeError
from . import sizing, topology
from .build import (SOURCE_TAG, MeshConsistencyError, _check_bbox, _check_dofs,
                    read_msh_summary, res_mm_for_spec)

#: Same default shell the FREEFORM generator path uses (``families`` / ``registry``: 3 mm).
DEFAULT_WALL_THICKNESS_MM = 3.0

#: Quadrants -> the mesher's symmetry-plane axes (mirror of ``sizing.SYMMETRY_PLANE``
#: vocabulary).  "1" is the quarter (G8/G9 even in phi); "14" is the half model the
#: lecleach_mod b-terms force (left-right mirror only, plane yz, x >= 0); "1234" is the
#: FULL ring (no mirror planes; the mesher's native closed/full mode, 2026-10-25:
#: the odd-cosine lecleach_asym asymmetry requires it -- MOUTH_RIPPLE/SALMON dossiers).
#: The mesher's ``PointGridHornGeometry`` uses the same axis names
#: ("x" = x=0/yz, "y" = y=0/xz); an empty tuple + ``closed=True`` is its default mode.
_GRID_SYMMETRY_AXES = {"1": ("x", "y"), "14": ("x",), "1234": ()}


def _resolve_grid(grid: dict, *, enclosure: dict | None = None
                  ) -> tuple[np.ndarray, np.ndarray | None, float, dict, bool]:
    """``grid`` dict -> ``(inner, outer, wall_thickness_mm, meta, closed)``.

    Accepts either the pair returned by ``grid.grid_points`` packed as
    ``{"inner_points": ..., "meta": ...}`` or the same dict plus ``outer_points`` /
    ``wall_thickness_mm``. ``closed=True`` only for a full-circle grid (``meta["quarter"]``
    false AND not a half model); this pass's ``build_grid_mesh`` refuses that config.

    ``enclosure`` (the normalized WP12 mounting block) selects the enclosure topology: no outer
    shell is built (``outer`` is None) and an explicit ``outer_points`` in ``grid`` is refused,
    mirroring the mesher's own structural guard (geometry.py:316-320).
    """
    if not isinstance(grid, dict):
        raise TypeError(f"grid must be a dict, got {type(grid).__name__}")
    if "inner_points" not in grid:
        raise ValueError("grid dict needs 'inner_points' (n_phi, n_s + 1, 3) millimetres")
    inner = np.asarray(grid["inner_points"], dtype=float)
    if inner.ndim != 3 or inner.shape[2] != 3:
        raise ValueError(f"inner_points must be (n_phi, n_s + 1, 3), got {inner.shape}")
    meta = dict(grid.get("meta") or {})
    half = bool(meta.get("half_model", False))
    closed = (not bool(meta.get("quarter", True))) and not half
    t = float(grid.get("wall_thickness_mm", DEFAULT_WALL_THICKNESS_MM))
    outer = grid.get("outer_points")
    if enclosure is not None:
        if outer is not None:
            raise ValueError(
                "enclosure cannot be combined with outer_points; choose either the enclosure "
                "topology or the freestanding wall shell")
        return inner, None, t, meta, closed
    if outer is None:
        outer = grid_gen.grid_outer_points(inner, t, half=half, full=closed)
    else:
        outer = np.asarray(outer, dtype=float)
        if outer.shape != inner.shape:
            raise ValueError(
                f"outer_points {outer.shape} must match inner_points {inner.shape}")
        grid_gen.check_self_approach(inner, outer, t)
    return inner, outer, t, meta, closed


def build_grid_mesh(grid, mesh, out_path, cfg, *, mode: str | None = None,
                    mounting: dict | None = None) -> MeshResult:
    """GRID geometry + ``MeshSpec`` -> ``out_path`` (.msh, metres) and a ``MeshResult``.

    ``grid`` is the dict described in :func:`_resolve_grid`; ``mesh`` is the ``MeshSpec``
    ``config.mesh_spec`` returns; ``cfg`` is the run ``Config`` (dof caps and
    ``dof_per_triangle`` come from ``cfg.mesh``, exactly as in ``mesh/build.py``);
    ``mode`` ("screen"|"verify"|"final") selects the cap, else it is inferred from
    ``mesh.max_triangles`` like ``build.py`` does.

    ``mounting`` (WP12) is the normalized ``brief.mounting`` block from the run ``Config``.
    When set, no outer shell is built and the mesher's ``HornEnclosure`` is passed instead
    (one translator: ``design.families.enclosure_section``/``enclosure_object``).

    The mesher budget is ``int(mesh.max_triangles)`` -- the same value ``families
    .to_mesher_config`` puts in ``mesh.max_triangles`` for the FREEFORM route (the mesher reads
    it as a FULL-DOMAIN-EQUIVALENT ceiling and divides by the quarter factor itself).
    """
    import hornlab_mesher  # noqa: F401  (pin guard: keeps the import error a clear one)
    from hornlab_mesher.config_parser import ConfigError
    from hornlab_mesher.geometry import MeshDensity, PointGridHornGeometry
    from hornlab_mesher.mesher import MesherError, TriangleBudgetExceeded, build_mesh_with_info

    t0 = time.perf_counter()
    out_path = Path(out_path)
    inner, outer, t, meta, closed = _resolve_grid(grid, enclosure=mounting)
    enclosure = None if mounting is None else families.enclosure_object(mounting)
    half = bool(meta.get("half_model", False))
    full = bool(closed)          # a full ring = the mesher's native closed mode (2026-10-25)
    if full and enclosure is not None:
        raise ValueError(
            "the WP12 enclosure route takes the quarter/half rows in this pass; a full "
            "ring + enclosure needs its own validation pass")
    expected = "14" if half else ("1234" if full else "1")
    if mesh.quadrants != expected:
        raise ValueError(
            f"grid/symmetry mismatch: this grid is a {meta.get('row_span', 'quarter')} "
            f"model (meta row_span={meta.get('row_span')!r}, symmetry plane "
            f"{meta.get('symmetry_plane')!r}), but mesh.quadrants={mesh.quadrants!r}. "
            f"A {meta.get('row_span', 'quarter')} grid needs quadrants={expected!r} "
            f"(b-terms / the axial bend force the HALF model; all-cosine recipes stay "
            f"quarter; the seam-free FULL ring - the odd-cosine lecleach_asym asymmetry "
            f"- is '1234').")
    angle = meta.get("source_auto_angle_deg")
    if angle is None:
        raise ValueError("grid meta lacks 'source_auto_angle_deg' (the rounded source cap angle)")
    angle = float(angle)
    if not np.isfinite(angle) or abs(angle) < 1e-12:
        raise ValueError(
            f"source_auto_angle_deg must be nonzero (got {angle!r}); 0 removes the source cap")

    res = res_mm_for_spec(mesh, cfg)
    # KEYWORDS ONLY: positional arg 4 of MeshDensity is aperture_res_scale, not max_triangles.
    density = MeshDensity(
        throat_res_mm=float(res["throat"]),
        mouth_res_mm=float(res["mouth"]),
        rear_res_mm=float(res["rear"]),
        aperture_res_scale=1.0,
        max_triangles=int(mesh.max_triangles),
        allow_large_mesh=False,
    )
    geometry = PointGridHornGeometry(
        inner_points=inner,
        closed=full,                           # the full ring is the mesher's native closed mode
        outer_points=outer,                    # None in enclosure mode (structural guard)
        wall_thickness_mm=float(t) if enclosure is None else 0.0,
        source_shape=1,
        source_auto_angle_deg=angle,
        symmetry_planes=_GRID_SYMMETRY_AXES[mesh.quadrants],
        enclosure=enclosure,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _path, info = build_mesh_with_info(geometry, density, output_path=out_path,
                                           scale_to_metres=True)
    except TriangleBudgetExceeded as exc:
        raise MeshTooLargeError(str(exc)) from exc
    except (ConfigError, ValueError, MesherError) as exc:
        raise families.wrap_mesher_error(exc) from exc

    summary, xyz, tri = read_msh_summary(out_path, return_arrays=True)
    want = sizing.SYMMETRY_PLANE[mesh.quadrants]
    try:
        _check_bbox(summary["bbox_m"])
        if int(info.n_triangles) != summary["n_triangles"]:
            raise MeshConsistencyError(
                f"mesher reports {info.n_triangles} triangles, the .msh holds "
                f"{summary['n_triangles']}")
        if summary["tags"].get(SOURCE_TAG, 0) <= 0:
            raise GeometryInvalidError(
                f"mesh has no elements on physical tag {SOURCE_TAG} (SD1D1001, the source); "
                f"tags present: {summary['tags']}")
        _check_dofs(summary["n_triangles"], summary["n_nodes_used"], mesh, cfg, mode)
        topology.check_surface(xyz, tri, want)
    except (MeshConsistencyError, GeometryInvalidError, MeshTooLargeError):
        out_path.unlink(missing_ok=True)     # never leave an unusable mesh to be picked up later
        raise

    return MeshResult(
        path=str(out_path), n_triangles=summary["n_triangles"], n_dof=None,
        quadrants=mesh.quadrants, symmetry_plane=want,
        res_mm=dict(res), bbox_m=tuple(summary["bbox_m"]),
        seconds=time.perf_counter() - t0)


# ------------------------------------------------------------------ wire-in note (no cache)
# ``mesh/build.py`` keys its cache on ``design.hash()`` + ``mesh.hash()``. A GRID design has no
# ``Design`` object, so the wire-in lane must key on the GEOMETRY itself, e.g.
# ``sha256(np.ascontiguousarray(inner, dtype=np.float64).tobytes() + struct.pack("<d", t)
# + json.dumps(meta, sort_keys=True))`` + ``mesh.hash()``; do not reuse ``mesh_cache_key`` as is,
# or two different grids that happen to share a Design hash (none) would collide. The cache is
# deliberately absent here until the pseudo-family owns that key.

# ------------------------------------------------------------------ SKETCH only (2026-10-25)
# GRID mesh-cache design, written down but NOT implemented (ISSUES M4 local-only item:
# "GRID-route mesh-cache absence"). Comment-only: nothing above depends on this block.
#
# * KEY = the design RECIPE JSON, i.e. the persisted ``design.params["grid"]`` (generator kind +
#   every knob, ``n_phi``/``n_s``/``wall_thickness_mm``, span) -- NOT a ``Design`` hash, which a
#   GRID run does not have -- PLUS a hash of the MESH-BUILD inputs: the resolved ``MeshDensity``
#   (throat/mouth/rear res from ``res_mm_for_spec``, aperture_res_scale, max_triangles,
#   allow_large_mesh) and the symmetry/model inputs (``mesh.quadrants``, ``_GRID_SYMMETRY_AXES``,
#   ``source_auto_angle_deg``, ``source_shape``, ``DEFAULT_WALL_THICKNESS_MM``). The point-grid
#   arrays are a pure function of the recipe, so hashing the recipe avoids re-marching to hash.
# * INVALIDATION = hash change, nothing else: same recipe + same build inputs -> reuse the .msh;
#   any knob, sampling, density or symmetry edit -> a new key -> remesh. No TTL, no mtime.
# * STORAGE candidate = ``runs/.mesh_cache/<key>.msh`` (GUI/cache-owned, like the existing
#   ``runs/.gui_cache``) or a explicit ``--cache-dir`` argument threaded through the caller, so a
#   measurement can point it at scratch. Store the ``MeshResult`` fields beside the .msh (n_triangles,
#   dofs, res_mm, bbox, symmetry_plane) so a hit still reports the same result shape.
# * WARNING -- the M2/M4 lesson: the EXISTING solve/mesh caches are NOT keyed by library SHA. In
#   M2 the A/B had to re-solve on FRESH cache dirs because stale entries would otherwise have
#   silently served responses from the old ``hornlab_beat_bem``/``hornlab_mesher`` build as if they
#   were the A/B arm. A GRID mesh cache inherits that hazard: the .msh depends on the mesher's
#   code as much as on the recipe. Any implementation MUST therefore either (a) fold the library
#   SHAs (``hornlab_mesher``, and the gmsh version) into the key, or (b) leave the cache per-SHA
#   (``runs/.mesh_cache/<lib_shas>/<key>.msh``) so a reinstall cannot mix builds -- fresh cache
#   dirs per GPU job remain the measurement default either way.

