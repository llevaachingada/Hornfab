"""Region-level mesh-resolution audit (read-only).

Answers "did the produced mesh actually put resolution where the policy asked?" from a saved
``.msh`` plus its producer metadata. Nothing here rebuilds or solves anything.

Region identity
---------------
Gmsh physical tags deliberately combine every rigid surface into ``SD1G0`` (tag 1), so the tag
alone cannot say "throat" from "outer shell".  When the design directory carries
``mesh_meta.json`` with the producer ``mesher_config``, this tool rebuilds the *point-grid geometry*
with ``hornlab_mesher.config_builder.resolve_geometry`` (no meshing, CPU only) and assigns each
tag-1 triangle to the nearest producer surface grid:

* nearest ``inner_points`` -> throat_transition / inner_bore / mouth_lip by the producer grid's
  own axial station index;
* nearest ``outer_points`` -> outer_shell;
* a non-inner triangle behind the throat plane -> rear_cap.

The assignment is geometric, not guessed from tag numbers, and every row reports the mapping
residual (centroid distance to the assigned producer grid).  Rows with a large residual are
reported as ``unknown`` rather than silently assigned.  CAD/STEP meshes have no point-grid
producer record; they fall back to physical-tag regions and are labelled ``tag_1_wall``.

Requested vs realized
---------------------
``requested_mm`` is the documented search-side policy evaluated at the triangle centroid:
the mesher's throat->mouth axial interpolation for inner surfaces, the (factored) rear size for
the outer shell/rear cap, throat size for the source, and aperture size for tag 12.  It is the
policy the mesher was *asked* for, not a re-run of Gmsh's size fields; clearance caps and boundary
effects can therefore show up honestly as realized/requested != 1.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/mesh_region_audit.py <design dir | mesh.msh> \\
        [--fmax HZ] [--epw 6] [--out text|json|csv]

``--out csv`` prints one header row per mesh (region rows), so a batch can be concatenated.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.constants import C_AIR  # noqa: E402
from hornlab_search.mesh.build import read_msh_summary  # noqa: E402

TOOL = "mesh_region_audit"
SCHEMA_VERSION = 1

SOURCE_TAG = 2
ENCLOSURE_TAG = 3
MID_CHAMBER_TAG = 8
PORT_INTERIOR_TAG = 9
MID_PORT_TAGS = (10, 11)
MOUTH_APERTURE_TAG = 12
WALL_TAG = 1

THROAT_STATION_FRACTION = 0.10
MOUTH_STATION_FRACTION = 0.90

REGION_ORDER = (
    "source",
    "throat_transition",
    "inner_bore",
    "mouth_lip",
    "mouth_aperture",
    "outer_shell",
    "rear_cap",
    "enclosure",
    "mid_chamber",
    "port_interior",
    "mid_port_exit",
    "tag_1_wall",
    "unknown",
)


def _triangle_tags(path: Path) -> np.ndarray:
    """Physical tag of every 3-node triangle, in file order (same order as read_msh_summary)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index("$Elements")
    n_el = int(lines[start + 1])
    tags: list[int] = []
    for ln in lines[start + 2: start + 2 + n_el]:
        f = ln.split()
        if int(f[1]) != 2:
            continue
        nt = int(f[2])
        tags.append(int(f[3]) if nt >= 1 else 0)
    return np.asarray(tags, dtype=np.int64)


def _resolve_mesh(target: Path) -> Path:
    mesh = target / "mesh.msh" if target.is_dir() else target
    if not mesh.is_file():
        raise FileNotFoundError(f"no mesh file at {mesh}")
    return mesh


def _read_meta(mesh: Path) -> dict | None:
    meta = mesh.parent / "mesh_meta.json"
    if not meta.is_file():
        return None
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _run_settings(mesh: Path) -> dict:
    """Best-effort ``mesh.epw`` / ``dof_per_triangle`` / ``rear_res_factor`` from the run config."""
    out: dict = {}
    design_dir = mesh.parent
    for parent in (design_dir, *design_dir.parents):
        cfg_path = parent / "config.yaml"
        if not cfg_path.is_file():
            continue
        try:
            import yaml

            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            mesh_cfg = cfg.get("mesh") or {}
            for key in ("epw", "dof_per_triangle", "rear_res_factor", "curvature_npts",
                        "quadrants"):
                if key in mesh_cfg:
                    out[key] = mesh_cfg[key]
        except Exception:
            pass
        break
    return out


def _producer_geometry(meta: dict | None):
    """Rebuild the point-grid geometry from the producer mesher config (CPU, no meshing)."""
    if not meta:
        return None, "no mesh_meta.json"
    mcfg = meta.get("mesher_config")
    if not isinstance(mcfg, dict):
        return None, "mesh_meta.json has no mesher_config (CAD/STEP or grid route)"
    try:
        from hornlab_mesher.config_builder import resolve_geometry

        resolved = resolve_geometry(mcfg)
    except Exception as exc:  # producer record exists but this build cannot replay it
        return None, f"resolve_geometry failed: {type(exc).__name__}: {exc}"
    geometry = resolved.geometry
    inner = np.asarray(getattr(geometry, "inner_points", None), dtype=float)
    if inner.ndim != 3 or inner.shape[-1] != 3:
        return None, "producer geometry has no usable inner_points"
    outer = getattr(geometry, "outer_points", None)
    outer = None if outer is None else np.asarray(outer, dtype=float)
    if outer is not None and (outer.ndim != 3 or outer.shape[-1] != 3):
        outer = None
    return {
        "inner": inner,
        "outer": outer,
        "wall_thickness_mm": float(getattr(geometry, "wall_thickness_mm", 6.0) or 6.0),
        "has_enclosure": getattr(geometry, "enclosure", None) is not None,
        "source_axis": "z",
    }, None


def _requested_inner_mm(z_mm: float, z0: float, z1: float, throat: float, mouth: float) -> float:
    span = max(abs(z1 - z0), 1e-9)
    u = min(max((z_mm - z0) / span, 0.0), 1.0)
    return throat + (mouth - throat) * u


def _classify_geometric(centroids_mm: np.ndarray, tags: np.ndarray, geom: dict):
    """Return (region array, residual_mm array, station array, producer_surface array)."""
    from scipy.spatial import cKDTree

    n = centroids_mm.shape[0]
    region = np.full(n, "unknown", dtype=object)
    residual = np.full(n, np.nan)
    station = np.full(n, np.nan)
    surface = np.full(n, "none", dtype=object)

    # Tag-led regions win; they are physical groups, not guesses.
    region[tags == SOURCE_TAG] = "source"
    region[tags == MOUTH_APERTURE_TAG] = "mouth_aperture"
    region[tags == ENCLOSURE_TAG] = "enclosure"
    region[tags == MID_CHAMBER_TAG] = "mid_chamber"
    region[tags == PORT_INTERIOR_TAG] = "port_interior"
    region[np.isin(tags, MID_PORT_TAGS)] = "mid_port_exit"
    rest = tags == WALL_TAG

    inner = geom["inner"].reshape(-1, 3)
    n_phi, n_s, _ = geom["inner"].shape
    inner_tree = cKDTree(inner)
    d_inner, i_inner = inner_tree.query(centroids_mm[rest])
    i_station = i_inner % n_s
    frac = i_station / max(n_s - 1, 1)
    z0 = float(geom["inner"][:, 0, 2].mean())
    z1 = float(geom["inner"][:, -1, 2].mean())

    d_outer = np.full(rest.sum(), np.inf)
    if geom["outer"] is not None:
        outer_tree = cKDTree(geom["outer"].reshape(-1, 3))
        d_outer, _ = outer_tree.query(centroids_mm[rest])

    z_rest = centroids_mm[rest, 2]
    # The rear cap is a flat face behind the throat plane.  Decide it before the inner/outer
    # comparison: at z ~ throat_minus_wall the nearest inner point is the throat ring only a few
    # millimetres away, so a nearest-surface rule alone would fold cap triangles into
    # "throat_transition".  No acoustic inner wall exists behind the throat plane.
    rear_cap = z_rest <= z0 - 0.1 * max(geom["wall_thickness_mm"], 1.0)
    is_inner = (d_inner <= d_outer) & ~rear_cap
    is_outer = (~is_inner) & ~rear_cap

    reg_rest = np.full(rest.sum(), "unknown", dtype=object)
    reg_rest[is_inner & (frac <= THROAT_STATION_FRACTION)] = "throat_transition"
    reg_rest[is_inner & (frac > THROAT_STATION_FRACTION)
             & (frac < MOUTH_STATION_FRACTION)] = "inner_bore"
    reg_rest[is_inner & (frac >= MOUTH_STATION_FRACTION)] = "mouth_lip"
    reg_rest[is_outer] = "outer_shell"
    reg_rest[rear_cap] = "rear_cap"

    # Residual = distance to the surface the row was assigned to.  Large residuals are flagged.
    res_rest = np.where(is_inner, d_inner, d_outer)
    res_rest[rear_cap] = d_outer[rear_cap]
    # Ambiguous thin-wall points: inner and outer are closer together than 0.1 mm.  At the
    # mouth plane this is the planar aperture fill (the mesher only tags it 12 on some routes);
    # behind the throat plane it is the rear cap.  Everything else stays unknown rather than
    # being assigned to a region the producer did not distinguish.
    ambiguous = np.abs(d_inner - d_outer) < 0.1
    span = max(abs(z1 - z0), 1e-9)
    at_mouth = (z_rest >= z1 - max(1.0, 0.002 * span)) | (frac >= 0.98)
    at_rear = z_rest <= z0 - max(1.0, 0.002 * span)
    reg_rest[ambiguous & at_mouth] = "mouth_aperture"
    reg_rest[ambiguous & ~at_mouth & at_rear] = "rear_cap"
    res_rest[ambiguous] = np.nan
    reg_rest[ambiguous & ~at_mouth & ~at_rear] = "unknown"

    region[rest] = reg_rest
    residual[rest] = res_rest
    frac_rest = np.where(is_inner, frac, np.nan)
    station[rest] = frac_rest
    surface[rest] = np.where(is_inner, "inner", np.where(rear_cap, "rear", "outer"))
    return region, residual, station, surface


def _tag_only_regions(tags: np.ndarray) -> np.ndarray:
    region = np.full(tags.shape[0], "unknown", dtype=object)
    region[tags == SOURCE_TAG] = "source"
    region[tags == MOUTH_APERTURE_TAG] = "mouth_aperture"
    region[tags == ENCLOSURE_TAG] = "enclosure"
    region[tags == MID_CHAMBER_TAG] = "mid_chamber"
    region[tags == PORT_INTERIOR_TAG] = "port_interior"
    region[np.isin(tags, MID_PORT_TAGS)] = "mid_port_exit"
    region[tags == WALL_TAG] = "tag_1_wall"
    return region


def _dihedral_deg(tri: np.ndarray, xyz_m: np.ndarray, region: np.ndarray | None = None) -> np.ndarray:
    """Per-triangle maximum angle to a neighbour across a shared edge, degrees.

    Smooth surfaces stay near 0 deg; a value near the geometric corner angle means the mesh is
    faceting that corner (either intended ridge or under-resolution). Boundary edges are ignored.
    """
    p0, p1, p2 = xyz_m[tri[:, 0]], xyz_m[tri[:, 1]], xyz_m[tri[:, 2]]
    normals = np.cross(p1 - p0, p2 - p0)
    norm = np.linalg.norm(normals, axis=1)
    normals = np.divide(normals, norm[:, None], out=np.zeros_like(normals),
                        where=norm[:, None] > 0)
    edge_of: dict[tuple[int, int], list[int]] = {}
    for i, (a, b, c) in enumerate(tri.tolist()):
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            edge_of.setdefault(key, []).append(i)
    out = np.zeros(tri.shape[0])
    for pair in edge_of.values():
        if len(pair) != 2:
            continue
        i, j = pair
        if region is not None and region[i] != region[j]:
            continue
        c = float(np.clip(np.dot(normals[i], normals[j]), -1.0, 1.0))
        ang = math.degrees(math.acos(c))
        out[i] = max(out[i], ang)
        out[j] = max(out[j], ang)
    return out


def _triangle_metrics(xyz_m: np.ndarray, tri: np.ndarray):
    p0, p1, p2 = xyz_m[tri[:, 0]], xyz_m[tri[:, 1]], xyz_m[tri[:, 2]]
    edges = np.stack([
        np.linalg.norm(p1 - p0, axis=1),
        np.linalg.norm(p2 - p1, axis=1),
        np.linalg.norm(p0 - p2, axis=1),
    ], axis=1)
    cross = np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    area = 0.5 * cross
    perimeter = edges.sum(axis=1)
    inradius = np.divide(2.0 * area, perimeter, out=np.zeros_like(area), where=perimeter > 0)
    longest = edges.max(axis=1)
    aspect = np.divide(longest, 2.0 * inradius, out=np.full_like(longest, np.inf),
                       where=inradius > 1e-15)
    # Smallest angle from the two shortest edges, triangle cosine rule.
    s = np.sort(edges, axis=1)
    a, b, c = s[:, 2], s[:, 1], s[:, 0]  # c shortest, a longest
    cos_c = np.clip((a * a + b * b - c * c) / np.maximum(2.0 * a * b, 1e-30), -1.0, 1.0)
    min_angle = np.degrees(np.arccos(cos_c))
    return edges, area, aspect, min_angle


def _weighted_percentiles(values: np.ndarray, weights: np.ndarray, qs: list[float]) -> list[float]:
    if values.size == 0:
        return [float("nan")] * len(qs)
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    total = w.sum()
    if total <= 0:
        return [float(np.percentile(v, q)) for q in qs]
    cw = np.cumsum(w) / total
    return [float(np.interp(q / 100.0, cw, v)) for q in qs]


def _stats(rows: dict[str, np.ndarray], n_tri: int, n_vert: int, area: float) -> dict:
    if n_tri == 0:
        return {
            "n_triangles": 0, "n_vertices": 0, "area_mm2": 0.0,
            "edge_mm_p05": None, "edge_mm_p25": None, "edge_mm_p50": None,
            "edge_mm_p75": None, "edge_mm_p95": None, "edge_mm_p99": None,
            "edge_mm_max": None, "edge_mm_area_weighted_mean": None,
            "aspect_p50": None, "aspect_p95": None, "min_angle_p05_deg": None,
            "dihedral_p95_deg": None, "dihedral_max_deg": None,
            "frac_dihedral_gt30": None,
        }
    e = rows["edges_mm"]
    d = rows["dihedral_deg"]
    return {
        "n_triangles": int(n_tri),
        "n_vertices": int(n_vert),
        "area_mm2": float(area),
        "edge_mm_p05": float(np.percentile(e, 5)),
        "edge_mm_p25": float(np.percentile(e, 25)),
        "edge_mm_p50": float(np.percentile(e, 50)),
        "edge_mm_p75": float(np.percentile(e, 75)),
        "edge_mm_p95": float(np.percentile(e, 95)),
        "edge_mm_p99": float(np.percentile(e, 99)),
        "edge_mm_max": float(e.max()),
        "edge_mm_area_weighted_mean": float(np.average(e, weights=rows["areas_mm2"])),
        "aspect_p50": float(np.percentile(rows["aspect"], 50)),
        "aspect_p95": float(np.percentile(rows["aspect"], 95)),
        "min_angle_p05_deg": float(np.percentile(rows["min_angle_deg"], 5)),
        "dihedral_p95_deg": float(np.percentile(d, 95)),
        "dihedral_max_deg": float(d.max()),
        "frac_dihedral_gt30": float(np.mean(d > 30.0)),
    }


def build_report(target, *, fmax: float | None = None, epw: float | None = None,
                 dof_per_triangle: float | None = None) -> dict:
    mesh = _resolve_mesh(Path(target))
    meta = _read_meta(mesh)
    run = _run_settings(mesh)
    if epw is None:
        epw = float(run.get("epw", 6.0))
    summary, xyz, tri = read_msh_summary(mesh, return_arrays=True)
    tags = _triangle_tags(mesh)
    if tags.shape[0] != tri.shape[0]:
        raise ValueError(f"{mesh}: triangle/tag count mismatch ({tags.shape[0]} vs {tri.shape[0]})")

    xyz_mm = np.asarray(xyz, dtype=float) * 1000.0
    centroids_mm = xyz_mm[tri].mean(axis=1)
    edges_m, area_m2, aspect, min_angle = _triangle_metrics(
        np.asarray(xyz, dtype=float), tri)
    area_mm2 = area_m2 * 1e6

    # Local topology report (read-only).  The mesher already enforces this at build time; the
    # audit repeats it on the stored file so a copied/edited mesh cannot hide a tear.
    topology_report = None
    try:
        from hornlab_search.mesh import sizing as mesh_sizing
        from hornlab_search.mesh import topology as mesh_topology

        quadrants = None
        if isinstance(meta, dict) and isinstance(meta.get("result"), dict):
            quadrants = meta["result"].get("quadrants")
        quadrants = quadrants or run.get("quadrants")
        plane = mesh_sizing.SYMMETRY_PLANE.get(str(quadrants)) if quadrants else None
        if plane is not None or str(quadrants) == "1234":
            rep = mesh_topology.check_surface(np.asarray(xyz, dtype=float), tri, plane)
            topology_report = {
                "quadrants": str(quadrants),
                "symmetry_plane": plane,
                "bad_open_edges": int(getattr(rep, "bad_open_edges", 0)),
                "nonmanifold_edges": int(getattr(rep, "nonmanifold_edges", 0)),
                "near_coincident": int(getattr(rep, "near_coincident", 0)),
            }
    except Exception as exc:                          # advisory only: never fail the audit
        topology_report = {"error": f"{type(exc).__name__}: {exc}"}

    geometry, geom_reason = _producer_geometry(meta)
    if geometry is not None:
        region, residual_mm, station, producer_surface = _classify_geometric(
            centroids_mm, tags, geometry)
        region_source = "producer_geometry"
    else:
        region = _tag_only_regions(tags)
        residual_mm = np.full(tags.shape[0], np.nan)
        station = np.full(tags.shape[0], np.nan)
        producer_surface = np.where(tags == WALL_TAG, "unknown", "none")
        region_source = "physical_tags"
    # Faceting angle within a region only: edges where two regions meet are geometric corners
    # (source disc to wall, shell to rim) and would swamp the smooth-surface distribution.
    dihedral = _dihedral_deg(tri, np.asarray(xyz, dtype=float), region)

    res_mm = {}
    if dof_per_triangle is None:
        dof_per_triangle = run.get("dof_per_triangle")
    rear_factor = run.get("rear_res_factor")
    if isinstance(meta, dict) and isinstance(meta.get("result"), dict):
        res_mm = dict(meta["result"].get("res_mm") or {})
        if meta.get("rear_res_factor") is not None:
            rear_factor = meta["rear_res_factor"]
    if not res_mm:
        mcfg = (meta or {}).get("mesher_config") if isinstance(meta, dict) else None
        m = (mcfg or {}).get("mesh") if isinstance(mcfg, dict) else None
        if isinstance(m, dict):
            res_mm = {
                "throat": m.get("throat_res_mm"),
                "mouth": m.get("mouth_res_mm"),
                "rear": m.get("rear_res_mm"),
            }
    throat_req = float(res_mm.get("throat") or float("nan"))
    mouth_req = float(res_mm.get("mouth") or float("nan"))
    rear_req = float(res_mm.get("rear") or float("nan"))
    if fmax is None and math.isfinite(mouth_req) and mouth_req > 0:
        fmax = 1000.0 * C_AIR / (epw * mouth_req)

    # Requested size at each triangle, per region policy.
    requested = np.full(tags.shape[0], np.nan)
    if geometry is not None:
        z = centroids_mm[:, 2]
        z0 = float(geometry["inner"][:, 0, 2].mean())
        z1 = float(geometry["inner"][:, -1, 2].mean())
        requested[(region == "throat_transition") | (region == "inner_bore")
                  | (region == "mouth_lip")] = [
            _requested_inner_mm(zi, z0, z1, throat_req, mouth_req)
            for zi in z[(region == "throat_transition") | (region == "inner_bore")
                        | (region == "mouth_lip")]
        ]
        requested[region == "outer_shell"] = rear_req
        requested[region == "rear_cap"] = rear_req
        requested[region == "source"] = throat_req
        requested[region == "mouth_aperture"] = mouth_req
    else:
        requested[region == "source"] = throat_req
        requested[region == "mouth_aperture"] = mouth_req

    h_max_mm = float(edges_m.max() * 1000.0)

    rows = []
    for rname in REGION_ORDER:
        mask = region == rname
        n = int(mask.sum())
        if not n:
            continue
        sub = {
            "edges_mm": edges_m[mask].ravel() * 1000.0,
            "areas_mm2": np.repeat(area_mm2[mask], 3),
            "aspect": aspect[mask],
            "min_angle_deg": min_angle[mask],
            "dihedral_deg": dihedral[mask],
        }
        e_per_tri = edges_m[mask] * 1000.0
        e_min = e_per_tri.min(axis=1)
        e_max = e_per_tri.max(axis=1)
        used = np.unique(tri[mask])
        row = {
            "region": rname,
            **_stats(sub, n, int(used.size), float(area_mm2[mask].sum())),
            "requested_mm_p50": float(np.nanmedian(requested[mask]))
            if np.isfinite(requested[mask]).any() else None,
            "requested_mm_area_weighted_mean": float(np.average(
                requested[mask][np.isfinite(requested[mask])],
                weights=area_mm2[mask][np.isfinite(requested[mask])]))
            if np.isfinite(requested[mask]).any() else None,
            "realized_over_requested_p50": float(np.nanmedian(
                e_min[np.isfinite(requested[mask])] / requested[mask][np.isfinite(requested[mask])]))
            if np.isfinite(requested[mask]).any() else None,
            "mapping_residual_mm_p50": float(np.nanpercentile(residual_mm[mask], 50))
            if np.isfinite(residual_mm[mask]).any() else None,
            "mapping_residual_mm_p95": float(np.nanpercentile(residual_mm[mask], 95))
            if np.isfinite(residual_mm[mask]).any() else None,
            "station_frac_mean": float(np.nanmean(station[mask]))
            if np.isfinite(station[mask]).any() else None,
            "producer_surface": "/".join(sorted({str(v) for v in producer_surface[mask]
                                                 if str(v) != "none"})) or "none",
        }
        if fmax is not None:
            row["h_max_over_lambda"] = (h_max_mm / 1000.0) / (C_AIR / fmax)
            row["region_h_p95_over_lambda"] = (row["edge_mm_p95"] / 1000.0) / (C_AIR / fmax)
        else:
            row["h_max_over_lambda"] = None
            row["region_h_p95_over_lambda"] = None
        rows.append(row)

    n_unknown = int((region == "unknown").sum())
    return {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "mesh": str(mesh),
        "run_config": run,
        "rear_res_factor": rear_factor,
        "n_triangles": int(summary["n_triangles"]),
        "n_vertices": int(summary["n_nodes_used"]),
        "dof_estimate": int(math.ceil(summary["n_triangles"] * float(dof_per_triangle)))
        if dof_per_triangle else None,
        "bbox_m": list(summary["bbox_m"]),
        "area_m2": float(summary["area_m2"]),
        "tags": summary["tags"],
        "res_mm": {k: (None if v is None else float(v)) for k, v in res_mm.items()},
        "epw": float(epw),
        "fmax_hz": float(fmax) if fmax is not None else None,
        "region_source": region_source,
        "region_source_note": geom_reason,
        "unknown_triangle_fraction": float(n_unknown / max(tri.shape[0], 1)),
        "topology": topology_report,
        "regions": rows,
    }


# ------------------------------------------------------------------ output


def _fmt(v, nd=3):
    if v is None:
        return "-"
    if isinstance(v, float):
        if not math.isfinite(v):
            return "-"
        return f"{v:.{nd}f}"
    return str(v)


def _text(report: dict) -> str:
    out = [
        f"mesh: {report['mesh']}",
        f"triangles: {report['n_triangles']}  vertices: {report['n_vertices']}  "
        f"dof_estimate: {_fmt(report['dof_estimate'], 0)}  area: {report['area_m2']:.5f} m2",
        f"policy: res_mm {json.dumps(report['res_mm'], sort_keys=True)}  "
        f"rear_res_factor: {_fmt(report['rear_res_factor'], 2)}  epw: {report['epw']:g}  "
        f"fmax: {_fmt(report['fmax_hz'], 0)} Hz",
        f"region source: {report['region_source']}  "
        f"({report['region_source_note'] or 'ok'}); "
        f"unknown {100.0 * report['unknown_triangle_fraction']:.2f}%",
        f"{'region':<18} {'tris':>6} {'verts':>6} {'p50mm':>7} {'p95mm':>7} {'maxmm':>7} "
        f"{'hreq':>6} {'r/req':>6} {'asp95':>6} {'dih95':>6} {'res95':>6}",
    ]
    for r in report["regions"]:
        out.append(
            f"{r['region']:<18} {r['n_triangles']:>6} {r['n_vertices']:>6} "
            f"{_fmt(r['edge_mm_p50']):>7} {_fmt(r['edge_mm_p95']):>7} "
            f"{_fmt(r['edge_mm_max']):>7} {_fmt(r['requested_mm_p50'], 1):>6} "
            f"{_fmt(r['realized_over_requested_p50'], 2):>6} "
            f"{_fmt(r['aspect_p95'], 2):>6} {_fmt(r['dihedral_p95_deg'], 1):>6} "
            f"{_fmt(r['mapping_residual_mm_p95'], 2):>6}"
        )
    if report["region_source"] != "producer_geometry":
        out.append(f"note: {report['region_source_note']}; regions are physical-tag level only")
    return "\n".join(out)


CSV_COLUMNS = [
    "mesh", "region", "tag_region_source", "n_triangles", "n_vertices", "area_mm2",
    "edge_mm_p05", "edge_mm_p25", "edge_mm_p50", "edge_mm_p75", "edge_mm_p95",
    "edge_mm_p99", "edge_mm_max", "edge_mm_area_weighted_mean", "aspect_p50",
    "aspect_p95", "min_angle_p05_deg", "dihedral_p95_deg", "dihedral_max_deg",
    "frac_dihedral_gt30", "requested_mm_p50",
    "requested_mm_area_weighted_mean", "realized_over_requested_p50",
    "mapping_residual_mm_p50", "mapping_residual_mm_p95", "station_frac_mean",
    "producer_surface", "h_max_over_lambda", "region_h_p95_over_lambda",
    "res_throat_mm", "res_mouth_mm", "res_rear_mm", "rear_res_factor", "fmax_hz", "epw",
]


def _csv_rows(report: dict) -> str:
    rows = [",".join(CSV_COLUMNS)]
    for r in report["regions"]:
        vals = {
            "mesh": report["mesh"],
            "region": r["region"],
            "tag_region_source": report["region_source"],
            "res_throat_mm": report["res_mm"].get("throat"),
            "res_mouth_mm": report["res_mm"].get("mouth"),
            "res_rear_mm": report["res_mm"].get("rear"),
            "rear_res_factor": report["rear_res_factor"],
            "fmax_hz": report["fmax_hz"],
            "epw": report["epw"],
            **r,
        }
        rows.append(",".join("" if vals.get(c) is None else f"{vals.get(c):.6g}"
                             if isinstance(vals.get(c), float) else str(vals.get(c))
                             for c in CSV_COLUMNS))
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", help="design directory containing mesh.msh, or a mesh.msh path")
    ap.add_argument("--fmax", type=float, default=None,
                    help="assessment top frequency; default inferred from mouth resolution and epw")
    ap.add_argument("--epw", type=float, default=None, help="elements per wavelength (default from run config)")
    ap.add_argument("--out", choices=("text", "json", "csv"), default="text")
    args = ap.parse_args(argv)
    report = build_report(args.target, fmax=args.fmax, epw=args.epw)
    if args.out == "json":
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    elif args.out == "csv":
        print(_csv_rows(report))
    else:
        print(_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





