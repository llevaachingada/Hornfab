"""CROWE V2A analytic-law vs actual BEM-wall geometry truth (CPU only, read/build only).

WP1 of ``docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md``.  This tool answers one
question: **how far is the meshed interior acoustic wall from the analytic V2A law the search
optimises?**

It deliberately does **not** import or invoke any BEM/solve module.  It may (a) evaluate the
generator's own analytic law, (b) build a CPU mesh through the existing
``hornlab_search.mesh.build`` -> pinned ``hornlab_mesher`` path, and (c) read an existing ``.msh``.
No solve, no GPU, no queue, no mutation of any stored run artifact.

Reused rather than re-implemented
=================================
* ``hornlab_search.design.generators.crowe_hv_area_aspect_v1.evaluate`` - the intended law.
* ``hornlab_search.design.families.to_mesher_config`` + ``hornlab_mesher.config_builder``
  ``resolve_geometry`` - the mesher's own native point grid (the "native floor" reference).
* ``hornlab_search.mesh.build.build_mesh`` - CPU mesh build and the project's guards.
* ``hornlab_search.compare.mshio.read_msh`` - ASCII MSH 2.x reader and physical tags.
* Attribution: the role-aware inner-wall isolation and the *native-floor*-relative FABLE v2 rule
  (``CANONICAL_SURFACE_CONTRACT.md`` section 12) follow
  ``scratch/fable_architecture/.n1b/inner.py`` / ``.x4c/inner.py`` (65 x 61 canonical record).
  Here the *analytic* law samples replace the resampled native record, because WP1 asks about the
  law-vs-wall mismatch, not sampler convergence.

Why ``tools/analysis/mesh_fidelity.py`` is not extended in place
===============================================================
``mesh_fidelity.py`` reports per-tag triangle edge-length percentiles against a wavelength
criterion.  It has no analytic reference surface, no triangle-surface projection, no role
classification and no signed deviation.  Extending it would turn a frequency-resolution report into
a different instrument; WP1 therefore lives in this separate read-only tool.

Measurement vocabulary (see the evidence doc for the exact definitions)
======================================================================
* ``analytic_to_mesh`` - exact point-to-triangle 3D distance from analytic section samples to the
  classified inner-wall triangles.  Positive signed bias means the mesh wall is **outside** the
  analytic wall (radial sign convention).
* ``native_floor`` - 99th-percentile distance from classified inner-wall mesh nodes to the
  mesher's own native point grid, i.e. the pinned mesher's own fit error.  Report-only; never used
  to hide a real law-vs-wall deviation.
* FABLE v2 relative rule: ``p99_analytic <= max(1 mm, 1.25 * native_floor_p99)``.  Reported
  alongside the absolute p99; passing it is not permission to ignore a millimetre-scale bias.

Usage
=====
    .venv\\Scripts\\python.exe tools/analysis/crowe_mesh_truth.py ^
        --config examples/typologies/crowe_hv_area_aspect_2026-11-16/configs/c1_four_dof_bounds.yaml ^
        --out docs/evidence/crowe_v2a_geometry_truth/surface_truth.json

    # law only (no mesher, no gmsh)
    .venv\\Scripts\\python.exe tools/analysis/crowe_mesh_truth.py --config <cfg> --out <json> --no-mesh

    # reuse a mesh already built for the config's own seed
    .venv\\Scripts\\python.exe tools/analysis/crowe_mesh_truth.py --config <cfg> --out <json> ^
        --existing-mesh <dir-with-mesh.msh>
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.compare import mshio  # noqa: E402
from hornlab_search.config import load_config, mesh_spec  # noqa: E402
from hornlab_search.design import families  # noqa: E402
from hornlab_search.design.generators import crowe_hv_area_aspect_v1 as family  # noqa: E402
from hornlab_search.design.space import Bound  # noqa: E402
from hornlab_search.types import Design  # noqa: E402

TOOL = "crowe_mesh_truth"
SCHEMA_VERSION = 1

#: Physical V2A section stations (mm).  Matches the generator's own V2A review set + 80 mm.
STATIONS_MM = (0.0, 5.0, 10.0, 20.0, 40.0, 80.0, 100.0)
#: Normalized forward stations u = z/L.
NORMALIZED_U = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
#: Azimuths measured from +x toward +y (contract CANONICAL_SURFACE_CONTRACT section 3).
AZIMUTHS_DEG = (0.0, 22.5, 45.0, 67.5, 90.0)

#: mesher physical tags (hornlab_mesher.tags.PhysicalGroup).
SOURCE_TAG = 2          # PRIMARY_SOURCE / SD1D1001
WALL_TAG = 1            # RIGID_WALL / SD1G0 (inner + outer shell + rear closure)
ENCLOSURE_TAG = 3       # ENCLOSURE_WALL

#: Classify a tag-1 triangle as inner wall when |r - r_law| is below this.  The outer shell at the
#: throat sits ~3 mm out (wall thickness 3 mm), so 2 mm separates the two populations without
#: needing a threshold fitted after the fact.
INNER_RADIAL_TOL_MM = 2.0
#: Native point-grid resolution used for the native floor (same 10 mm as FABLE N1/N1b/X4).
NATIVE_RES_MM = 10.0
#: FABLE v2 rule constants.
RULE_ABS_FLOOR_MM = 1.0
RULE_RELATIVE_FACTOR = 1.25

#: The canonical WP1 sample set (12 geometrically admitted cases under the c1 four-DOF box).
#: c0 seed at W580/H474/L300; two interior heights; single-variable low/high for all four knobs;
#: two coupled feasible corners.  The c1 config's own bounds are used to check admission; invalid
#: corners are reported as typed refusals, never patched.
DEFAULT_CASES = (
    {"name": "c0_seed", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 300.0,
                                  "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}},
    {"name": "interior_h400", "knobs": {"height_v_active_mm": 400.0, "L_forward_mm": 300.0,
                                        "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}},
    {"name": "interior_h430", "knobs": {"height_v_active_mm": 430.0, "L_forward_mm": 300.0,
                                        "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}},
    {"name": "height_low300", "knobs": {"height_v_active_mm": 300.0, "L_forward_mm": 300.0,
                                        "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}},
    {"name": "length_low220", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 220.0,
                                        "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}},
    {"name": "length_high340", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 340.0,
                                         "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}},
    {"name": "area_bias_low", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 300.0,
                                        "area_mid_bias": -0.15, "aspect_timing_u50": 0.5}},
    {"name": "area_bias_high", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 300.0,
                                         "area_mid_bias": 0.15, "aspect_timing_u50": 0.5}},
    {"name": "u50_low", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 300.0,
                                  "area_mid_bias": 0.0, "aspect_timing_u50": 0.35}},
    {"name": "u50_high", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 300.0,
                                   "area_mid_bias": 0.0, "aspect_timing_u50": 0.65}},
    {"name": "corner_small_boxy", "knobs": {"height_v_active_mm": 300.0, "L_forward_mm": 220.0,
                                            "area_mid_bias": -0.15, "aspect_timing_u50": 0.65}},
    {"name": "corner_large_round", "knobs": {"height_v_active_mm": 474.0, "L_forward_mm": 340.0,
                                             "area_mid_bias": 0.15, "aspect_timing_u50": 0.35}},
)

_FORBIDDEN_MODULES = ("hornlab_search.solve", "hornlab_beat_bem", "hornlab_bempp_bem")


# ------------------------------------------------------------------ guards / provenance


def no_solve_guard() -> None:
    """Refuse to run if a solve/BEM module has been imported into this process.

    The tool never imports one; this is a belt-and-braces safeguard so an accidental future import
    fails loudly instead of turning a geometry report into an acoustic run.
    """
    loaded = sorted(
        name for name in sys.modules
        if any(name == bad or name.startswith(bad + ".") for bad in _FORBIDDEN_MODULES)
    )
    if loaded:
        raise RuntimeError(
            f"{TOOL}: refusing to run with solve/BEM modules imported ({loaded}); "
            "this tool is CPU geometry truth only")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def git_snapshot() -> dict:
    def _run(*args: str) -> str:
        try:
            out = subprocess.run(("git", *args), cwd=ROOT, capture_output=True, text=True,
                                 timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            return ""
        return out.stdout.strip() if out.returncode == 0 else ""

    return {
        "repo_head": _run("rev-parse", "HEAD") or None,
        "working_tree_porcelain": _run("status", "--porcelain").splitlines(),
    }


def mesher_pin() -> dict:
    pin = None
    try:
        text = (ROOT / "TOOLCHAIN.md").read_text(encoding="utf-8")
        m = re.search(r"hornlab-waveguide-mesher:\s*`([0-9a-f]{40})`", text)
        pin = m.group(1) if m else None
    except OSError:
        pass
    try:
        import importlib.metadata as md
        version = md.version("hornlab-waveguide-mesher")
    except Exception:
        version = None
    return {"pinned_sha40": pin, "installed_version": version}


def config_sha(raw: dict) -> str:
    """Same canonicalisation as ``hornlab_search.search.rundir.config_sha`` (12 hex chars).

    Reimplemented locally so this tool never imports the search package.
    """
    def _jsonable(value):
        if isinstance(value, dict):
            return {str(k): _jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_jsonable(v) for v in value]
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    blob = json.dumps(_jsonable(raw), sort_keys=True, separators=(",", ":"))
    return sha256_bytes(blob.encode())[:12]


def canonical_sha256(value) -> str:
    """Full SHA-256 of a canonical JSON encoding (brief/target/weights provenance)."""
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(blob.encode())


def _bounds(cfg) -> dict:
    return {str(k): Bound(lo=float(b["lo"]), hi=float(b["hi"]),
                          search=bool(b.get("search", True)))
            for k, b in cfg.bounds_raw.items()}


def fable_v2_threshold(floor_p99_mm: float) -> float:
    """FABLE contract v2 rule-2 threshold: ``max(1 mm, 1.25 * native_floor_p99)``."""
    return max(RULE_ABS_FLOOR_MM, RULE_RELATIVE_FACTOR * float(floor_p99_mm))


# ------------------------------------------------------------------ pure analytic geometry


def law_radius_mm(a, b, p, phi_rad):
    """Superellipse radial half-span at a ray azimuth.  ``|x/a|^p + |y/b|^p = 1``."""
    ct = np.abs(np.cos(phi_rad))
    st = np.abs(np.sin(phi_rad))
    return (np.power(ct / a, p) + np.power(st / b, p)) ** (-1.0 / p)


def analytic_section(shape: dict, brief: dict, z_mm: float) -> dict:
    """Exact law values at one physical station (mm, mm^2, dimensionless)."""
    length = float(shape["L_forward_mm"])
    if not (0.0 <= float(z_mm) <= length + 1e-9):
        raise ValueError(f"station {z_mm!r} mm is outside [0, {length:g}] mm")
    law = family.evaluate(shape, brief, np.array([float(z_mm) / length]))
    return {
        "z_mm": float(z_mm),
        "u": float(z_mm) / length,
        "a_mm": float(law["a_mm"][0]),
        "b_mm": float(law["b_mm"][0]),
        "p": float(law["p"][0]),
        "area_mm2": float(law["area_mm2"][0]),
        "aspect": float(law["aspect"][0]),
    }


def analytic_samples(shape: dict, brief: dict,
                     stations_mm=STATIONS_MM, normalized_u=NORMALIZED_U,
                     azimuths_deg=AZIMUTHS_DEG) -> tuple[np.ndarray, list[dict]]:
    """Analytic wall points at both physical and normalized stations, all requested azimuths.

    Returns ``(points[n,3] mm, records[n])``.  ``z`` is the physical depth; normalized stations are
    multiplied by the case's own ``L_forward_mm`` so every case samples the same *fractional*
    development as well as the same absolute depths.
    """
    length = float(shape["L_forward_mm"])
    az = np.radians(np.asarray(azimuths_deg, dtype=float))
    points: list[list[float]] = []
    records: list[dict] = []
    for basis, stations in (("physical_mm", stations_mm),
                            ("normalized_u", [float(u) * length for u in normalized_u])):
        for z_mm in stations:
            z_mm = float(z_mm)
            if z_mm < 0.0 or z_mm > length + 1e-9:
                # A physical station beyond this case's shorter L is a typed skip, never a 0.
                records.append({"basis": basis, "z_mm": z_mm, "status": "station_beyond_L"})
                continue
            sec = analytic_section(shape, brief, z_mm)
            for phi in az:
                r = float(law_radius_mm(sec["a_mm"], sec["b_mm"], sec["p"], phi))
                points.append([r * math.cos(float(phi)), r * math.sin(float(phi)), z_mm])
                records.append({
                    "basis": basis, "z_mm": z_mm, "u": sec["u"],
                    "azimuth_deg": float(np.degrees(phi)),
                    "a_mm": sec["a_mm"], "b_mm": sec["b_mm"], "p": sec["p"],
                    "area_mm2": sec["area_mm2"], "aspect": sec["aspect"],
                    "status": "sampled",
                })
    return np.asarray(points, dtype=float), records


def _law_radius_at_centroids(shape: dict, brief: dict, z_mm, x, y):
    """Law radial half-span for arrays of mesh centroids; NaN outside the forward law domain."""
    length = float(shape["L_forward_mm"])
    z = np.asarray(z_mm, dtype=float)
    u = np.clip(z / length, 0.0, 1.0)
    law = family.evaluate(shape, brief, u)
    phi = np.arctan2(np.asarray(y, dtype=float), np.asarray(x, dtype=float))
    return law_radius_mm(law["a_mm"], law["b_mm"], law["p"], phi)


# ------------------------------------------------------------------ exact mesh distances


def _closest_point_on_triangles(points: np.ndarray, tri_pts: np.ndarray):
    """Vectorised closest point on a triangle (Ericson, *Real-Time Collision Detection* 5.1.5).

    ``points`` (N,3), ``tri_pts`` (N,K,3,3) -> ``(dist (N,K), closest (N,K,3))``.
    """
    p = np.broadcast_to(points[:, None, :], tri_pts.shape[:-2] + (3,))
    a, b, c = tri_pts[..., 0, :], tri_pts[..., 1, :], tri_pts[..., 2, :]
    ab = b - a
    ac = c - a
    ap = p - a

    def dot(u, v):
        return np.einsum("...i,...i->...", u, v)

    d1 = dot(ab, ap)
    d2 = dot(ac, ap)
    bp = p - b
    d3 = dot(ab, bp)
    d4 = dot(ac, bp)
    cp = p - c
    d5 = dot(ab, cp)
    d6 = dot(ac, cp)

    result = np.empty_like(p)
    done = np.zeros(p.shape[:-1], dtype=bool)

    def assign(mask, value):
        nonlocal done
        mask = mask & ~done
        if np.any(mask):
            result[mask] = value[mask] if hasattr(value, "shape") else value
            done |= mask

    assign((d1 <= 0.0) & (d2 <= 0.0), a)
    assign((d3 >= 0.0) & (d4 <= d3), b)

    vc = d1 * d4 - d3 * d2
    assign((vc <= 0.0) & (d1 >= 0.0) & (d3 <= 0.0),
           a + (d1 / np.where(d1 - d3 == 0.0, 1.0, d1 - d3))[..., None] * ab)

    assign((d6 >= 0.0) & (d5 <= d6), c)

    vb = d5 * d2 - d1 * d6
    assign((vb <= 0.0) & (d2 >= 0.0) & (d6 <= 0.0),
           a + (d2 / np.where(d2 - d6 == 0.0, 1.0, d2 - d6))[..., None] * ac)

    va = d3 * d6 - d5 * d4
    denom_edge = (d4 - d3) + (d5 - d6)
    assign((va <= 0.0) & ((d4 - d3) >= 0.0) & ((d5 - d6) >= 0.0),
           b + (np.where(denom_edge == 0.0, 0.0, (d4 - d3) / np.where(denom_edge == 0.0, 1.0,
                                                                       denom_edge)))[..., None] * (c - b))

    remaining = ~done
    if np.any(remaining):
        total = va + vb + vc
        total = np.where(total == 0.0, 1.0, total)
        v = vb / total
        w = vc / total
        result[remaining] = (a + v[..., None] * ab + w[..., None] * ac)[remaining]

    closest = result
    return np.linalg.norm(closest - p, axis=-1), closest


def point_to_surface(points: np.ndarray, triangles_xyz: np.ndarray, *, k: int = 16) -> dict:
    """Exact point-to-triangle-surface distance, with a KD-tree only as a candidate selector."""
    points = np.asarray(points, dtype=float)
    tri = np.asarray(triangles_xyz, dtype=float)
    if points.size == 0 or tri.size == 0:
        return {"distance_mm": np.array([]), "closest_mm": np.zeros((0, 3)),
                "triangle_index": np.array([], dtype=int)}
    centroids = tri.mean(axis=1)
    k = int(min(max(1, k), len(tri)))
    _, cand_idx = cKDTree(centroids).query(points, k=k)
    cand_idx = np.atleast_2d(cand_idx)
    if cand_idx.shape == (1, k) and len(points) == 1:
        cand_idx = cand_idx  # already (1,k)
    cand = tri[cand_idx]                       # (N,k,3,3)
    dist, closest = _closest_point_on_triangles(points, cand)
    best = np.argmin(dist, axis=1)
    rows = np.arange(len(points))
    return {
        "distance_mm": dist[rows, best],
        "closest_mm": closest[rows, best],
        "triangle_index": cand_idx[rows, best],
    }


def triangulate_grid(grid: np.ndarray) -> np.ndarray:
    """Structured ``(n_phi, n_s, 3)`` point grid -> two triangles per cell (no wrap)."""
    grid = np.asarray(grid, dtype=float)
    n_phi, n_s, _ = grid.shape
    pts = grid.reshape(-1, 3)
    idx = np.arange(n_phi * n_s).reshape(n_phi, n_s)
    t1 = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:]], axis=-1).reshape(-1, 3)
    t2 = np.stack([idx[:-1, :-1], idx[1:, 1:], idx[:-1, 1:]], axis=-1).reshape(-1, 3)
    return pts[np.vstack([t1, t2])]


# ------------------------------------------------------------------ mesh roles / topology


def _tag_by_name(mesh, candidates: tuple[str, ...], fallback: int | None) -> int | None:
    for tag, name in mesh.names.items():
        if str(name).strip().upper() in candidates:
            return int(tag)
    return fallback


def _symmetry_axes(quadrants: str) -> tuple[int, ...]:
    """Coordinate axes that are symmetry planes for a reduced quadrants string.

    Mirrors ``hornlab_search.mesh.sizing.SYMMETRY_PLANE`` without importing the mesh sizing
    module (this tool has no need for mesh sizing beyond the config's own values):
    ``yz`` mirrors x (axis 0), ``xz`` mirrors y (axis 1).
    """
    return {"14": (0,), "12": (1,), "1": (0, 1), "1234": ()}.get(str(quadrants), ())


def mesh_topology(xyz: np.ndarray, tri: np.ndarray,
                  symmetry_axes: tuple[int, ...] = ()) -> dict:
    """Open edges, non-manifold edges, winding-inconsistent edges and role-aware openness.

    A reduced (quarter) mesh is intentionally open on its symmetry planes.  ``open_edges`` is the
    raw count; ``open_edges_off_symmetry_planes`` is the only one that would indicate a real hole.
    """
    e = np.vstack([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    key = np.sort(e, axis=1)
    uniq, inv, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    signs = np.where(e[:, 0] < e[:, 1], 1.0, -1.0)
    signed = np.bincount(inv, weights=signs, minlength=len(uniq))
    winding_bad = int(np.sum((counts == 2) & (np.abs(signed) > 0.5)))
    used = np.unique(tri)
    pts = xyz[used]

    open_keys = uniq[counts == 1]
    on_plane = np.zeros(len(open_keys), dtype=bool)
    for axis in symmetry_axes:
        tol = 1e-6 * max(float(np.ptp(pts[:, axis])), 1.0)
        on_plane |= ((np.abs(xyz[open_keys[:, 0], axis]) <= tol)
                     & (np.abs(xyz[open_keys[:, 1], axis]) <= tol))
    return {
        "n_edges": int(len(uniq)),
        "open_edges": int(np.sum(counts == 1)),
        "open_edges_on_symmetry_planes": int(np.sum(on_plane)),
        "open_edges_off_symmetry_planes": int(np.sum(~on_plane)),
        "nonmanifold_edges": int(np.sum(counts > 2)),
        "winding_inconsistent_edges": winding_bad,
        "symmetry_axes": list(symmetry_axes),
        "bbox_mm": [float(v) for v in (*pts.min(axis=0), *pts.max(axis=0))],
        "n_nodes_used": int(used.size),
    }


def classify_roles(mesh, shape: dict, brief: dict) -> dict:
    """Split physical tags into source / inner acoustic wall / remaining wall (shell) roles.

    * source: the tag named ``SD1D1001`` (or numeric tag 2);
    * wall: the tag named ``SD1G0`` / ``RIGID_WALL`` (or numeric tag 1);
    * inner wall: wall triangles whose centroid radial half-span is within
      ``INNER_RADIAL_TOL_MM`` of the analytic law at the same (z, azimuth).  This isolates the
      acoustic inner sheet from the offset outer shell / rear closure, which share the wall tag in
      a freestanding offset-solid mesh;
    * shell: the remaining wall triangles (outer shell, rear closure, rim).
    """
    xyz = mesh.xyz * 1000.0                    # metres -> millimetres
    tags = np.asarray(mesh.phys, dtype=np.int64)
    source_tag = _tag_by_name(mesh, ("SD1D1001", "PRIMARY_SOURCE"), SOURCE_TAG)
    wall_tag = _tag_by_name(mesh, ("SD1G0", "RIGID_WALL"), WALL_TAG)
    src_mask = tags == source_tag
    wall_mask = tags == wall_tag

    wall_idx = np.nonzero(wall_mask)[0]
    tri = mesh.tri
    cent = xyz[tri[wall_idx]].mean(axis=1) if len(wall_idx) else np.zeros((0, 3))
    length = float(shape["L_forward_mm"])
    z = cent[:, 2] if len(cent) else np.zeros(0)
    forward = (z >= -1e-6) & (z <= length + 1e-6)
    delta = np.full(len(wall_idx), np.nan)
    if np.any(forward):
        r_law = _law_radius_at_centroids(shape, brief, z[forward], cent[forward, 0], cent[forward, 1])
        r = np.hypot(cent[forward, 0], cent[forward, 1])
        delta[forward] = r - r_law
    inner_local = forward & np.isfinite(delta) & (np.abs(delta) <= INNER_RADIAL_TOL_MM)
    inner_idx = wall_idx[inner_local]
    shell_idx = wall_idx[~inner_local]

    def _stats(values):
        values = np.asarray(values, dtype=float)
        values = values[np.isfinite(values)]
        if values.size == 0:
            return None
        return {str(q): float(np.percentile(values, q)) for q in (1, 5, 50, 95, 99)}

    return {
        "xyz_mm": xyz,
        "source_tri": np.nonzero(src_mask)[0],
        "wall_tri": wall_idx,
        "inner_tri": inner_idx,
        "shell_tri": shell_idx,
        "source_tag": int(source_tag) if source_tag is not None else None,
        "wall_tag": int(wall_tag) if wall_tag is not None else None,
        "tag_names": {int(k): str(v) for k, v in mesh.names.items()},
        "tag_counts": {int(t): int((tags == t).sum()) for t in np.unique(tags)},
        "inner_radial_delta_mm_stats": _stats(delta[inner_local]),
        "shell_radial_delta_mm_stats": _stats(delta[~inner_local & forward]),
        "inner_tol_mm": INNER_RADIAL_TOL_MM,
    }


def mesh_section(triangles_xyz: np.ndarray, z_mm: float, *, quarter: bool = True) -> dict:
    """Intersect inner-wall triangles with the plane ``z = z_mm`` and measure the section.

    Returns H/V half-spans (maximum |x| / |y|), full-section area and aspect.  A section with too
    few spans or an implausible angular coverage is ``measurable=False`` - never ``0.0``.
    """
    tri = np.asarray(triangles_xyz, dtype=float)
    if tri.size == 0:
        return {"measurable": False, "reason": "no inner-wall triangles", "z_mm": float(z_mm)}
    z = float(z_mm)
    pts: list[np.ndarray] = []
    for k in range(3):
        a = tri[:, k, :]
        b = tri[:, (k + 1) % 3, :]
        za, zb = a[:, 2], b[:, 2]
        cross = ((za - z) * (zb - z) <= 0.0) & (np.abs(za - zb) > 1e-12)
        if not np.any(cross):
            continue
        t = (z - za[cross]) / (zb[cross] - za[cross])
        pts.append(a[cross] + t[:, None] * (b[cross] - a[cross]))
    if not pts:
        return {"measurable": False, "reason": "plane misses the inner wall", "z_mm": z}
    p = np.vstack(pts)
    # Deduplicate points at the same location (vertices lie on two edges).
    key = np.round(p, 6)
    p = p[np.unique(key, axis=0, return_index=True)[1]]
    r = np.hypot(p[:, 0], p[:, 1])
    theta = np.arctan2(p[:, 1], p[:, 0])
    eps = 1e-6
    if quarter:
        keep = (theta >= -eps) & (theta <= 0.5 * math.pi + eps)
        p, r, theta = p[keep], r[keep], np.clip(theta[keep], 0.0, 0.5 * math.pi)
    if len(r) < 3:
        return {"measurable": False, "reason": f"only {len(r)} section points", "z_mm": z}
    order = np.argsort(theta)
    theta, r = theta[order], r[order]
    h_half = float(np.max(p[:, 0]))
    v_half = float(np.max(p[:, 1]))
    # Build a monotone r(theta) table with the axis endpoints, then integrate the full area by
    # fourfold symmetry: A_full = 2 * integral_0^{pi/2} r(theta)^2 dtheta.
    th = np.concatenate(([0.0], theta, [0.5 * math.pi]))
    rr = np.concatenate(([h_half], r, [v_half]))
    if len(th) < 3 or np.any(np.diff(th) < -1e-12):
        return {"measurable": False, "reason": "non-monotone section angle", "z_mm": z}
    _trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    area = 2.0 * float(_trapezoid(rr * rr, th))
    return {
        "measurable": True,
        "z_mm": z,
        "h_half_span_mm": h_half,
        "v_half_span_mm": v_half,
        "width_mm": 2.0 * h_half if quarter else float(np.ptp(p[:, 0])),
        "height_mm": 2.0 * v_half if quarter else float(np.ptp(p[:, 1])),
        "area_mm2": area,
        "aspect": float(h_half / v_half) if v_half > 0 else None,
        "n_points": int(len(r)),
    }


# ------------------------------------------------------------------ native point grid


def native_geometry(design: Design, cfg) -> dict:
    """The pinned mesher's own native inner/outer point grid at ``NATIVE_RES_MM`` (mm)."""
    from hornlab_mesher.config_builder import resolve_geometry

    msp = mesh_spec("screen", cfg)
    mcfg = families.to_mesher_config(
        design, msp, {"throat": NATIVE_RES_MM, "mouth": NATIVE_RES_MM, "rear": NATIVE_RES_MM},
        Path("<crowe-mesh-truth-native>"), mounting=getattr(cfg, "mounting", None))
    mcfg["mesh"].update({"throat_res_mm": NATIVE_RES_MM, "mouth_res_mm": NATIVE_RES_MM,
                         "rear_res_mm": NATIVE_RES_MM, "allow_large_mesh": True})
    rg = resolve_geometry(mcfg, allow_large_mesh=True)
    geom = rg.geometry
    outer = getattr(geom, "outer_points", None)
    return {
        "inner_points_mm": np.asarray(geom.inner_points, dtype=float),
        "outer_points_mm": None if outer is None else np.asarray(outer, dtype=float),
        "surface_fit": str(getattr(geom, "surface_fit", "unknown")),
        "topology_mode": str(getattr(geom, "topology_mode", "unknown")),
        "mode": str(rg.mode),
        "n_phi": int(np.asarray(geom.inner_points).shape[0]),
        "n_s": int(np.asarray(geom.inner_points).shape[1]),
    }


# ------------------------------------------------------------------ rank


def _surface_vector(shape, brief, stations_mm, normalized_u, azimuths_deg) -> np.ndarray:
    pts, _ = analytic_samples(shape, brief, stations_mm, normalized_u, azimuths_deg)
    return pts.reshape(-1)


def surface_displacement_rank(shape, brief, knobs, bounds, *, delta: float = 0.1,
                              stations_mm=STATIONS_MM, normalized_u=NORMALIZED_U,
                              azimuths_deg=AZIMUTHS_DEG) -> dict:
    """Normalized law-surface displacement Jacobian for the four knobs at common samples.

    This is the analytic-surface analogue of a mesh-vertex Jacobian (the WP1 estimate).  One-sided
    inward differences are used whenever the seed sits on a bound, so no invalid central difference
    is ever taken at the seed.  Units: mm displacement per unit normalized box coordinate.
    """
    base = _surface_vector(shape, brief, stations_mm, normalized_u, azimuths_deg)
    keys = sorted(family.PARAM_KEYS)
    columns: dict[str, np.ndarray] = {}
    steps: dict[str, dict] = {}
    for key in keys:
        lo, hi = float(bounds[key].lo), float(bounds[key].hi)
        value = float(knobs[key])
        step = float(delta) * (hi - lo)
        if step <= 0.0:
            columns[key] = np.zeros_like(base)
            steps[key] = {"scheme": "fixed", "step": 0.0}
            continue
        plus = min(hi, value + step)
        minus = max(lo, value - step)
        d_plus = plus - value
        d_minus = value - minus
        if d_plus > 0.0 and d_minus > 0.0 and abs(d_plus - d_minus) < 1e-12:
            p_plus = analytic_samples({**shape, key: plus}, brief, stations_mm, normalized_u,
                                      azimuths_deg)[0].reshape(-1)
            p_minus = analytic_samples({**shape, key: minus}, brief, stations_mm, normalized_u,
                                       azimuths_deg)[0].reshape(-1)
            columns[key] = (p_plus - p_minus) / (2.0 * delta)
            steps[key] = {"scheme": "central", "plus": plus, "minus": minus,
                          "normalized_step": float(delta)}
        else:
            # The seed sits on a bound: use an inward one-sided difference, never a clipped
            # central difference that silently halves the denominator.
            inward = minus if value >= hi else plus
            shape_in = {**shape, key: inward}
            p_in = analytic_samples(shape_in, brief, stations_mm, normalized_u,
                                    azimuths_deg)[0].reshape(-1)
            sign = -1.0 if value >= hi else 1.0
            columns[key] = sign * (p_in - base) / float(delta)
            steps[key] = {"scheme": "one_sided_inward", "inward": inward,
                          "normalized_step": float(delta)}
    matrix = np.column_stack([columns[k] for k in keys])
    scale = float(np.sqrt(np.mean(base.reshape(-1, 3) ** 2))) if base.size else 0.0
    relative = matrix / max(scale, 1e-12)
    _, s, _ = np.linalg.svd(relative, full_matrices=False)
    s0 = max(float(s[0]) if len(s) else 0.0, 1e-12)
    norms = np.linalg.norm(relative, axis=0)
    cosine = np.abs(relative.T @ relative) / np.maximum(np.outer(norms, norms), 1e-12)
    np.fill_diagonal(cosine, 0.0)
    return {
        "keys": keys,
        "scheme": steps,
        "n_samples": int(base.size // 3),
        "sample_scale_mm": scale,
        "singular_values_relative": [float(v) for v in s],
        "effective_rank": int(np.sum(s > 1e-6 * s0)),
        "practical_rank": int(np.sum(s > 0.01 * s0)),
        "column_norms_relative": {k: float(v) for k, v in zip(keys, norms)},
        "column_norms_mm": {k: float(np.linalg.norm(columns[k])) for k in keys},
        "max_pairwise_abs_cosine": float(np.max(cosine)) if cosine.size else None,
        "pairwise_abs_cosine": {f"{a}|{b}": float(cosine[i, j])
                                for i, a in enumerate(keys) for j, b in enumerate(keys) if i < j},
        "absolute_vs_acoustic": (
            "analytic surface displacement, not a remeshed vertex Jacobian and not acoustic "
            "independence"),
    }


def law_rank(shape, knobs, bounds, brief, *, delta: float = 0.1) -> dict:
    """Reuse the generator's own T2 descriptor Jacobian (law level)."""
    return _law_rank(shape, knobs, bounds, brief, delta)


def _law_rank(shape, knobs, bounds, brief, delta: float = 0.1) -> dict:
    # ``identifiability_report`` takes the raw generator block, not the merged shape.
    gen = {k: v for k, v in shape.items() if k in family.GEN_KEYS - {"name", "seed_policy"}}
    gen["name"] = family.KIND
    return family.identifiability_report(gen, knobs, bounds, brief, delta=delta)


# ------------------------------------------------------------------ per-case analysis


def _stats(values) -> dict:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0}
    return {
        "n": int(v.size),
        "mean_mm": float(np.mean(v)),
        "median_mm": float(np.median(v)),
        "rms_mm": float(np.sqrt(np.mean(v * v))),
        "p95_mm": float(np.percentile(v, 95)),
        "p99_mm": float(np.percentile(v, 99)),
        "max_mm": float(np.max(v)),
    }


def _deviation_stats(points: np.ndarray, records: list[dict], tri: np.ndarray,
                     *, k: int = 24) -> dict:
    """Unsigned + signed deviations of analytic samples from the classified inner wall."""
    if len(points) == 0 or len(tri) == 0:
        return {"measurable": False, "reason": "no analytic samples or inner-wall triangles"}
    proj = point_to_surface(points, tri, k=k)
    dist = proj["distance_mm"]
    delta = proj["closest_mm"] - points
    radial = np.column_stack([points[:, 0], points[:, 1], np.zeros(len(points))])
    radial /= np.maximum(np.linalg.norm(radial, axis=1), 1e-12)[:, None]
    signed = np.einsum("ij,ij->i", delta, radial)
    sign = np.where(signed >= 0.0, 1.0, -1.0)
    signed_mag = sign * dist
    out = {"measurable": True, **_stats(dist)}
    out["signed_bias_mm"] = float(np.mean(signed_mag))
    out["signed_p50_mm"] = float(np.median(signed_mag))
    out["signed_min_mm"] = float(np.min(signed_mag))
    out["signed_max_mm"] = float(np.max(signed_mag))
    out["signed_positive_fraction"] = float(np.mean(signed >= 0.0))
    # Per-station detail (requested stations only; normalized/final duplicates are kept because
    # they answer a different question).
    per_station = []
    keys = [(r["basis"], r["z_mm"]) for r in records]
    for basis, z_mm in sorted(set(keys), key=lambda kv: (kv[0], kv[1])):
        idx = [i for i, (b, z) in enumerate(keys) if b == basis and z == z_mm]
        s = _stats(dist[idx])
        s.update({"basis": basis, "z_mm": float(z_mm)})
        s["signed_bias_mm"] = float(np.mean(signed_mag[idx]))
        per_station.append(s)
    out["per_station"] = per_station
    return out


def _dense_diagnostic(shape: dict, brief: dict, inner_triangles: np.ndarray,
                      *, n_u: int = 97, n_az: int = 73) -> dict:
    """A denser law-vs-wall scan (2.5 deg azimuth, 1/96 forward steps) for context.

    The prescribed WP1 sample set is deliberately sparse (7 + 6 stations, 5 azimuths).  This
    diagnostic asks whether that sparse set misses a corner/feature: it is reported separately and
    never replaces the prescribed numbers.
    """
    if len(inner_triangles) == 0:
        return {"measurable": False, "reason": "no inner-wall triangles"}
    length = float(shape["L_forward_mm"])
    us = np.linspace(0.0, 1.0, int(n_u))
    az = np.linspace(0.0, 90.0, int(n_az))
    pts, recs = analytic_samples(shape, brief, tuple(us * length), (), tuple(az))
    d = point_to_surface(pts, inner_triangles, k=16)["distance_mm"]
    i = int(np.argmax(d))
    out = {**_stats(d), "n_u": int(n_u), "n_azimuth": int(n_az),
           "azimuth_step_deg": 90.0 / (int(n_az) - 1),
           "max_at": {k: recs[i][k] for k in ("z_mm", "u", "azimuth_deg")}}
    # Per-azimuth p99 exposes corner-localised error that a single aggregate hides.
    out["per_azimuth"] = [
        {"azimuth_deg": float(a),
         "p99_mm": float(np.percentile(d[[j for j, r in enumerate(recs)
                                          if r["azimuth_deg"] == a]], 99)),
         "max_mm": float(np.max(d[[j for j, r in enumerate(recs)
                                  if r["azimuth_deg"] == a]]))}
        for a in (0.0, 22.5, 45.0, 67.5, 90.0)
    ]
    return out


def _source_face(mesh, xyz_mm: np.ndarray, source_tri: np.ndarray) -> dict:
    if len(source_tri) == 0:
        return {"present": False}
    pts = xyz_mm[np.unique(mesh.tri[source_tri])]
    return {
        "present": True,
        "n_triangles": int(len(source_tri)),
        "x_min_mm": float(pts[:, 0].min()), "x_max_mm": float(pts[:, 0].max()),
        "y_min_mm": float(pts[:, 1].min()), "y_max_mm": float(pts[:, 1].max()),
        "z_min_mm": float(pts[:, 2].min()), "z_max_mm": float(pts[:, 2].max()),
        "quarter_width_mm": float(pts[:, 0].max() - pts[:, 0].min()),
        "quarter_height_mm": float(pts[:, 1].max() - pts[:, 1].min()),
        "full_width_mm": float(2.0 * np.max(np.abs(pts[:, 0]))),
        "full_height_mm": float(2.0 * np.max(np.abs(pts[:, 1]))),
        "interpretation": (
            "36 mm modeled source: full extents are 2*max|x| and 2*max|y| because the mesh is a "
            "quarter domain; [derived], not a measured source diameter"),
    }


def _shell_clearance(inner_triangles: np.ndarray, shell_triangles: np.ndarray,
                     length_mm: float) -> dict:
    """Minimum/median distance from clearly-outer shell centroids to the inner wall.

    Rim faces touch the inner wall by construction; to avoid reporting a meaningless zero,
    centroids closer than 0.25 mm to an inner-wall edge (the welded rim) are excluded.  A second
    reading excludes the first/last 5 mm of depth, which removes rim and rear-closure faces and
    reports the actual outer-shell stand-off.
    """
    if len(inner_triangles) == 0 or len(shell_triangles) == 0:
        return {"measurable": False, "reason": "missing inner or shell triangles"}
    shell_cent = shell_triangles.mean(axis=1)
    d = point_to_surface(shell_cent, inner_triangles, k=8)["distance_mm"]
    keep = d > 0.25
    if not np.any(keep):
        return {"measurable": False, "reason": "all shell centroids touch the inner wall"}
    d_keep = d[keep]
    z = shell_cent[keep, 2]
    core = (z > 5.0) & (z < float(length_mm) - 5.0)
    out = {"measurable": True, "min_mm": float(np.min(d_keep)),
           "p05_mm": float(np.percentile(d_keep, 5)),
           "median_mm": float(np.median(d_keep)),
           "max_mm": float(np.max(d_keep)),
           "n_shell_triangles_scored": int(np.sum(keep)),
           "definition": ("distance from outer/shell triangle centroids to the inner-wall "
                           "surface; rim centroids <0.25 mm excluded")}
    if np.any(core):
        out["core_min_mm"] = float(np.min(d_keep[core]))
        out["core_median_mm"] = float(np.median(d_keep[core]))
        out["core_definition"] = "same, excluding shell centroids within 5 mm of z=0 or z=L"
    return out


def _mesh_hash(path: Path) -> str:
    return sha256_file(path)


def analyse_case(cfg, case: dict, args, provenance: dict) -> dict:
    """Measure one case; never raises for an invalid case (typed refusal instead)."""
    name = str(case.get("name") or "case")
    knobs = case.get("knobs")
    record = {"name": name, "status": "pending", "config": str(case.get("config") or ""),
              "seed_params": None, "refusal": None}
    try:
        if case.get("config"):
            case_cfg = load_config(Path(case["config"]))
        else:
            case_cfg = cfg
        if knobs is None:
            knobs = {k: float(v) for k, v in case_cfg.seed_params.items()}
        knobs = {k: float(v) for k, v in knobs.items()}
        if set(knobs) != set(family.PARAM_KEYS):
            raise ValueError(f"case {name!r}: knobs must be exactly {sorted(family.PARAM_KEYS)}; "
                             f"got {sorted(knobs)}")
        bounds = _bounds(case_cfg)
        brief = case_cfg.brief
        if not isinstance(brief, dict) or not isinstance(brief.get("driver"), dict):
            raise ValueError(f"case {name!r}: config has no usable brief.driver")
        shape = family._shape(case_cfg.generator, knobs)
        family.validate_search_config(case_cfg.generator, knobs, bounds, brief)
        effective_raw = json.loads(json.dumps(case_cfg.raw, default=str))
        effective_raw["seed_params"] = dict(knobs)
        effective_raw["name"] = f"{case_cfg.name}__{name}"
        record.update({
            "status": "ok",
            "seed_params": knobs,
            "config_sha256": config_sha(effective_raw),
            "base_config_sha256": config_sha(case_cfg.raw),
            "bounds": {k: {"lo": float(v.lo), "hi": float(v.hi)} for k, v in bounds.items()},
            "analytic": {
                "sections": [analytic_section(shape, brief, z)
                             for z in STATIONS_MM
                             if 0.0 <= z <= float(shape["L_forward_mm"]) + 1e-9],
                "terminal_z_mm": float(shape["L_forward_mm"]),
                "throat_area_mm2": float(math.pi * brief["driver"]["exit_radius_mm"] ** 2),
            },
        })
        points, sample_records = analytic_samples(shape, brief)
        record["analytic"]["sample_count"] = int(len(points))
        design = Design("FREEFORM", family.materialize(case_cfg.generator, knobs, brief))
        record["provenance"] = {
            "design_hash": design.hash(),
            "brief_sha256": canonical_sha256(brief),
            "target_sha256": canonical_sha256(case_cfg.target_raw),
            "weights_sha256": canonical_sha256(case_cfg.weights),
            "objective_version": int(getattr(case_cfg, "objective_version", 1)),
            "mesh_epw": float(case_cfg.mesh.epw),
            "mounting_mode": "freestanding" if getattr(case_cfg, "mounting", None) is None
            else "enclosure",
            "source_radius_mm": float(brief["driver"]["exit_radius_mm"]),
            "source_exit_angle_deg": float(brief["driver"]["exit_angle_deg"]),
            "physical_solve_id": "not_applicable: geometry-only run, no acoustic solve",
            "labels": "[measured] mesh/tag/section fields; [derived] full W/H from a quarter "
                      "bbox; [proposed] none",
        }
        rank = {
            "law_level": _law_rank(shape, knobs, bounds, brief),
            "surface_displacement": surface_displacement_rank(shape, brief, knobs, bounds),
        }
        record["rank"] = rank

        if args.no_mesh:
            record["status"] = "law_only"
            record["mesh"] = None
            record["deviation"] = None
            return record

        # ---- build or reuse the mesh
        if args.existing_mesh:
            if len(args._resolved_cases) != 1:
                raise ValueError("--existing-mesh applies only to a single-case sample set")
            mesh_dir = Path(args.existing_mesh)
            if not (mesh_dir / "mesh.msh").is_file():
                raise FileNotFoundError(f"{mesh_dir} does not contain mesh.msh")
            build_info = {"reused": True, "seconds": 0.0}
            mesh_path = mesh_dir / "mesh.msh"
        else:
            from hornlab_search.mesh import build
            mesh_dir = Path(args._mesh_root) / name
            t0 = time.perf_counter()
            result = build.build_mesh(design, mesh_spec("screen", case_cfg), case_cfg, mesh_dir)
            build_info = {"reused": False, "seconds": time.perf_counter() - t0,
                          "n_triangles": int(result.n_triangles),
                          "n_dof": result.n_dof}
            mesh_path = Path(result.path)
        mesh = mshio.read_msh(mesh_path)
        roles = classify_roles(mesh, shape, brief)
        xyz_mm = roles["xyz_mm"]
        tri = mesh.tri
        inner_triangles = xyz_mm[tri[roles["inner_tri"]]]
        shell_triangles = xyz_mm[tri[roles["shell_tri"]]]
        topo = mesh_topology(xyz_mm, tri, _symmetry_axes(case_cfg.mesh.quadrants))
        native = native_geometry(Design("FREEFORM", family.materialize(
            case_cfg.generator, knobs, brief)), case_cfg)
        native_tri = triangulate_grid(native["inner_points_mm"])
        inner_nodes = np.unique(tri[roles["inner_tri"]])
        floor = point_to_surface(xyz_mm[inner_nodes], native_tri, k=12)["distance_mm"]
        floor_stats = {
            "p50_mm": float(np.percentile(floor, 50)),
            "p95_mm": float(np.percentile(floor, 95)),
            "p99_mm": float(np.percentile(floor, 99)),
            "max_mm": float(np.max(floor)),
            "n_nodes": int(len(inner_nodes)),
            "definition": ("distance from classified inner-wall mesh nodes to the pinned "
                           "mesher's native point grid at 10 mm sample resolution"),
        }

        dev = _deviation_stats(points, sample_records, inner_triangles, k=24)
        dense = _dense_diagnostic(shape, brief, inner_triangles)
        threshold = fable_v2_threshold(floor_stats["p99_mm"])
        rule_pass = bool(dev.get("p99_mm", math.inf) <= threshold) if dev.get("measurable") else None

        # ---- mesh sections at every requested station
        section_rows = []
        for basis, stations in (("physical_mm", STATIONS_MM),
                                ("normalized_u", [u * float(shape["L_forward_mm"])
                                                  for u in NORMALIZED_U])):
            for z in stations:
                z = float(z)
                if z < 0.0 or z > float(shape["L_forward_mm"]) + 1e-9:
                    section_rows.append({"basis": basis, "z_mm": z,
                                         "status": "station_beyond_L"})
                    continue
                m = mesh_section(inner_triangles, z)
                a = analytic_section(shape, brief, z)
                row = {"basis": basis, "z_mm": z,
                       "analytic": {k: a[k] for k in ("a_mm", "b_mm", "p", "area_mm2",
                                                      "aspect")},
                       "mesh": m}
                if m.get("measurable"):
                    row["delta_mm"] = {
                        "h_half_span": m["h_half_span_mm"] - a["a_mm"],
                        "v_half_span": m["v_half_span_mm"] - a["b_mm"],
                        "area": m["area_mm2"] - a["area_mm2"],
                        "aspect": (m["aspect"] - a["aspect"]) if m.get("aspect") is not None
                        else None,
                    }
                section_rows.append(row)

        meta = {}
        if (mesh_dir / "mesh_meta.json").is_file():
            try:
                meta = json.loads((mesh_dir / "mesh_meta.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {}
        mesher_cfg = meta.get("mesher_config", {}).get("mesh", {}) if meta else {}

        bbox = topo["bbox_mm"]
        terminal_z = float(np.max(inner_triangles[:, :, 2]))
        source = _source_face(mesh, xyz_mm, roles["source_tri"])
        shell = _shell_clearance(inner_triangles, shell_triangles,
                                 float(shape["L_forward_mm"]))
        record["mesh"] = {
            "path": str(mesh_path),
            "sha256": _mesh_hash(mesh_path),
            "build": build_info,
            "n_triangles": int(len(tri)),
            "n_nodes": int(len(xyz_mm)),
            "format": "gmsh ASCII 2.2",
            "tags": roles["tag_counts"],
            "tag_names": roles["tag_names"],
            "source_tag": roles["source_tag"],
            "wall_tag": roles["wall_tag"],
            "inner_triangles": int(len(roles["inner_tri"])),
            "shell_triangles": int(len(roles["shell_tri"])),
            "inner_tol_mm": roles["inner_tol_mm"],
            "inner_radial_delta_mm_stats": roles["inner_radial_delta_mm_stats"],
            "shell_radial_delta_mm_stats": roles["shell_radial_delta_mm_stats"],
            "topology": topo,
            "symmetry": {
                "quadrants": str(case_cfg.mesh.quadrants),
                "symmetry_plane": meta.get("result", {}).get("symmetry_plane") if meta else None,
                "quarter_min_x_mm": float(xyz_mm[:, 0].min()),
                "quarter_min_y_mm": float(xyz_mm[:, 1].min()),
                "bbox_quarter_mm": bbox,
                "full_width_mm": float(2.0 * bbox[3]) if case_cfg.mesh.quadrants in ("1", "12", "14")
                else float(bbox[3] - bbox[0]),
                "full_height_mm": float(2.0 * bbox[4]) if case_cfg.mesh.quadrants in ("1", "12", "14")
                else float(bbox[4] - bbox[1]),
                "depth_mm": float(bbox[5] - bbox[2]),
            },
            "source_face": source,
            "shell_clearance": shell,
            "terminal_z_mm": terminal_z,
            "terminal_z_delta_mm": terminal_z - float(shape["L_forward_mm"]),
            "mouth_section": mesh_section(inner_triangles, terminal_z),
            "throat_section": mesh_section(inner_triangles, 0.0),
            "mesher": {
                **provenance["mesher"],
                "surface_fit_configured": str(mesher_cfg.get("surface_fit", "auto")),
                "surface_fit_resolved_native": native["surface_fit"],
                "native_grid_shape": [native["n_phi"], native["n_s"]],
                "native_grid_res_mm": NATIVE_RES_MM,
                "mesh_meta_key": meta.get("key") if meta else None,
            },
        }
        record["sections"] = section_rows
        record["deviation"] = dev
        record["dense_diagnostic"] = dense
        record["native_floor"] = floor_stats
        record["fable_v2_rule"] = {
            "absolute_p99_mm": dev.get("p99_mm"),
            "threshold_mm": threshold,
            "threshold_rule": "max(1.0 mm, 1.25 * native_floor_p99)",
            "native_floor_p99_mm": floor_stats["p99_mm"],
            "pass": rule_pass,
            "note": ("passing this relative rule is not permission to ignore a millimetre-scale "
                     "wall deviation; both numbers are reported"),
        }
        return record
    except Exception as exc:                    # typed refusal, never silent omission
        record["status"] = "refused"
        record["refusal"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback_tail": __import__("traceback").format_exc().splitlines()[-8:],
            "handling": "recorded as a typed refusal; bounds were not patched",
        }
        return record


# ------------------------------------------------------------------ sample-set resolution


def _read_json_or_yaml(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    import yaml
    return yaml.safe_load(text)


def resolve_cases(cfg, samples_arg: str | None) -> list[dict]:
    """Resolve the case list from ``--samples`` (dir / manifest) or the built-in canonical set."""
    if not samples_arg:
        return [dict(c) for c in DEFAULT_CASES]
    path = Path(samples_arg)
    if path.is_dir():
        cases = []
        for p in sorted(path.glob("*.yaml")) + sorted(path.glob("*.yml")):
            cases.append({"name": p.stem, "config": str(p)})
        if not cases:
            raise ValueError(f"{path}: no .yaml case configs found")
        return cases
    data = _read_json_or_yaml(path)
    if isinstance(data, dict) and "cases" in data:
        cases = data["cases"]
    elif isinstance(data, list):
        cases = data
    else:
        raise ValueError(f"{path}: expected a list of cases or an object with a 'cases' list")
    out = []
    for i, item in enumerate(cases):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: case #{i} must be a mapping")
        case = dict(item)
        case.setdefault("name", f"case_{i}")
        out.append(case)
    return out


# ------------------------------------------------------------------ output


def _csv_rows(cases: list[dict]) -> list[dict]:
    rows = []
    for c in cases:
        dev = c.get("deviation") or {}
        dense = c.get("dense_diagnostic") or {}
        floor = c.get("native_floor") or {}
        rule = c.get("fable_v2_rule") or {}
        rank = (c.get("rank") or {}).get("surface_displacement") or {}
        rows.append({
            "case": c.get("name"),
            "status": c.get("status"),
            "design_hash": (c.get("provenance") or {}).get("design_hash", ""),
            "config_sha256": c.get("config_sha256", ""),
            "refusal_type": (c.get("refusal") or {}).get("type", ""),
            "n_samples": dev.get("n", ""),
            "median_mm": dev.get("median_mm", ""),
            "p95_mm": dev.get("p95_mm", ""),
            "p99_mm": dev.get("p99_mm", ""),
            "max_mm": dev.get("max_mm", ""),
            "signed_bias_mm": dev.get("signed_bias_mm", ""),
            "dense_p99_mm": dense.get("p99_mm", ""),
            "dense_max_mm": dense.get("max_mm", ""),
            "native_floor_p99_mm": floor.get("p99_mm", ""),
            "fable_threshold_mm": rule.get("threshold_mm", ""),
            "fable_pass": rule.get("pass", ""),
            "surface_rank": rank.get("practical_rank", ""),
            "mesh_triangles": (c.get("mesh") or {}).get("n_triangles", ""),
            "mesh_sha256": (c.get("mesh") or {}).get("sha256", ""),
        })
    return rows


def write_outputs(payload: dict, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str),
                        encoding="utf-8")
    csv_path = out_path.with_suffix(".csv")
    rows = _csv_rows(payload["cases"])
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


# ------------------------------------------------------------------ main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--config", required=True,
                    help="base CROWE V2A config (c1 bounds recommended) - or a single case config")
    ap.add_argument("--out", required=True,
                    help="JSON output path; a sibling .csv per-case summary is written too")
    ap.add_argument("--samples", default=None,
                    help="case manifest (.json/.yaml) or a directory of case .yaml configs; "
                         "default: the built-in 12-case canonical WP1 set")
    ap.add_argument("--existing-mesh", default=None,
                    help="directory containing an already-built mesh.msh (single-case mode only)")
    ap.add_argument("--no-mesh", action="store_true",
                    help="law-only mode: no mesh build, no gmsh; analytic sections + rank only")
    ap.add_argument("--no-solve", action="store_true",
                    help="accepted for compatibility; this tool can never solve (safeguard is "
                         "always on)")
    ap.add_argument("--mesh-root", default=None,
                    help="directory for built meshes (default: a temp dir beside --out)")
    args = ap.parse_args(argv)

    no_solve_guard()
    cfg = load_config(Path(args.config))
    if not family.is_family_spec(cfg.generator):
        ap.error(f"{args.config} is not a {family.KIND} config")

    cases = resolve_cases(cfg, args.samples)
    args._resolved_cases = cases
    if args.mesh_root:
        args._mesh_root = Path(args.mesh_root)
    else:
        args._mesh_root = Path(args.out).resolve().parent / "_crowe_truth_meshes"
    if args.existing_mesh and len(cases) != 1:
        ap.error("--existing-mesh needs a single-case sample set")

    provenance = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": str(args.config),
        "base_config_sha256": config_sha(cfg.raw),
        "generator_implementation_sha256": family.implementation_digest(),
        "mesher": mesher_pin(),
        "git": git_snapshot(),
        "stations_mm": list(STATIONS_MM),
        "normalized_u": list(NORMALIZED_U),
        "azimuths_deg": list(AZIMUTHS_DEG),
        "inner_radial_tol_mm": INNER_RADIAL_TOL_MM,
        "native_res_mm": NATIVE_RES_MM,
        "units": "mm, mm^2, degrees; signed bias positive = mesh wall outside the analytic wall",
        "sampling_method": (
            "analytic law samples projected to the classified inner-wall triangle surface "
            "(exact point-to-triangle, KD-tree candidate selection, k=24)"),
        "physical_tag_method": (
            "tag 2 / SD1D1001 = source; tag 1 / SD1G0 = wall; inner-wall subset = wall triangles "
            "whose centroid radial half-span is within 2 mm of the law at the same z and azimuth"),
        "no_solve": True,
    }
    results = []
    for case in cases:
        print(f"[{TOOL}] case {case.get('name')} ...", flush=True)
        rec = analyse_case(cfg, case, args, provenance)
        results.append(rec)
        if rec["status"] in ("ok", "law_only"):
            dev = rec.get("deviation") or {}
            extra = ""
            if dev.get("measurable"):
                extra = (f"median {dev['median_mm']:.3f} mm, p99 {dev['p99_mm']:.3f} mm, "
                         f"max {dev['max_mm']:.3f} mm")
            print(f"[{TOOL}]   {rec['status']} {extra}", flush=True)
        else:
            print(f"[{TOOL}]   {rec['status']}: {(rec.get('refusal') or {}).get('type')} "
                  f"{(rec.get('refusal') or {}).get('message', '')[:160]}", flush=True)

    payload = {"meta": provenance, "cases": results}
    write_outputs(payload, Path(args.out))
    print(f"[{TOOL}] wrote {args.out} (+ {Path(args.out).with_suffix('.csv').name})",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
