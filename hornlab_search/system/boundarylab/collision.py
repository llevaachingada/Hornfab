"""Exact horn-to-cabinet clearance for stage-assembled Boundary Lab projects.

Why this module exists
----------------------
Boundary Lab compiles independent bodies (the imported horn surface and the generated
vented-enclosure shell) without any inter-body geometry test: ``blab project validate``
accepts intersecting separate bodies, and BL's ``mesh_quality`` checks are per-resource.
The previous HornFab guard (:mod:`.clearance`) used an AABB gap plus a vertex-to-vertex
KD-tree distance.  That guard is *sound but incomplete*: any AABB overlap that is not an
actual solid intersection came back ``BODY_CLEARANCE_UNPROVEN`` and refused a physically
legal mouth-overhang assembly.

What is modelled
----------------
Boundary Lab's vented provider generates a **rectangular** enclosure: the manifold
``exterior.msh`` is the box ``[-W/2, W/2] x [-H/2, H/2] x [-D, 0]`` with the driver and
port openings recessed into the baffle plane ``z=0`` (verified for the staged cases; the
exterior mesh bbox equals the parameter box exactly, and ``enclosure/parameters.py``
rejects any driver/port/cone that does not fit inside the walls).  The horn is an
imported closed triangle surface that BL translates by ``translation_m`` (metres, after
``scale_to_m``).  So the mechanically meaningful question is exact:

    minimum distance between the horn's triangle surface and that axis-aligned box,
    plus whether any part of the horn is inside the box.

That is solved in closed form per triangle:

* a triangle and a convex polytope are closest either at a vertex/edge of the triangle
  against the box (endpoint-to-box, edge-to-box-edge) or face-to-face parallel, where the
  triangle's own edges carry the same distance;
* so ``min over the 3 triangle edges of distance(segment, box)`` is exact, and a segment's
  distance to the box is ``min(2 endpoint-to-box, 12 segment-to-box-edge)``;
* any triangle edge that clips the box slab-wise means the triangle penetrates it, i.e.
  distance 0 -- this also covers the "edge passes through a face interior" case that a
  pure vertex-face/edge-edge decomposition misses.

Limits, stated up front:

* the box model is exact for BL's vented provider.  When the caller passes the compiled
  ``exterior.msh`` this module verifies its bbox against the parameter box and refuses
  (``UNPROVEN``) on disagreement instead of silently testing the wrong solid;
* the horn surface must be closed and non-degenerate (HornFab refuses to stage a
  non-closed horn before this check runs);
* support brackets/baffles are not part of either solid and are reported separately by
  the pose record, never silently assumed.

Nothing here writes to disk, starts a solver, or imports Boundary Lab.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

__all__ = [
    "CLEARANCE_PASS",
    "CLEARANCE_VIOLATION",
    "CLEARANCE_UNPROVEN",
    "Box",
    "CollisionReport",
    "Surface",
    "box_from_cabinet_mm",
    "read_surface",
    "surface_from_arrays",
    "transform_surface",
    "points_inside_box",
    "segment_box_distance",
    "triangle_surface_box_distance",
    "test_horn_box_clearance",
]

CLEARANCE_PASS = "PASS"
CLEARANCE_VIOLATION = "VIOLATION"
CLEARANCE_UNPROVEN = "UNPROVEN"

#: Default agreement tolerance between a parameter box and a compiled exterior mesh.
_BBOX_TOL_M = 1e-6
#: Numerical slack on the gap comparison (1 um); the meshes themselves are mm-scale.
_DIST_EPS_M = 1e-9


@dataclass(frozen=True)
class Box:
    """An axis-aligned solid box in metres."""

    lo: tuple[float, float, float]
    hi: tuple[float, float, float]

    def __post_init__(self) -> None:
        lo = tuple(float(v) for v in self.lo)
        hi = tuple(float(v) for v in self.hi)
        if len(lo) != 3 or len(hi) != 3:
            raise ValueError("box lo/hi must have 3 components")
        if not all(math.isfinite(v) for v in lo + hi):
            raise ValueError("box lo/hi must be finite")
        if not all(a < b for a, b in zip(lo, hi)):
            raise ValueError(f"box lo must be < hi on every axis, got {lo} / {hi}")
        object.__setattr__(self, "lo", lo)
        object.__setattr__(self, "hi", hi)

    @property
    def size(self) -> tuple[float, float, float]:
        return tuple(h - l for l, h in zip(self.lo, self.hi))  # type: ignore[return-value]

    def to_dict(self) -> dict[str, Any]:
        return {"lo_m": list(self.lo), "hi_m": list(self.hi), "size_m": list(self.size)}


def box_from_cabinet_mm(*, width_mm: float, height_mm: float, depth_mm: float) -> Box:
    """BL's cabinet frame: centred on x/y, baffle plane at z=0, body into z<0."""
    w, h, d = (float(v) for v in (width_mm, height_mm, depth_mm))
    if not all(math.isfinite(v) and v > 0.0 for v in (w, h, d)):
        raise ValueError(f"cabinet dimensions must be positive and finite, got {(w, h, d)!r}")
    return Box(lo=(-w / 2e3, -h / 2e3, -d / 1e3), hi=(w / 2e3, h / 2e3, 0.0))


@dataclass(frozen=True)
class Surface:
    """A triangle surface in metres: ``points (N,3)`` and ``triangles (T,3)``."""

    points: np.ndarray
    triangles: np.ndarray
    label: str = ""

    def __post_init__(self) -> None:
        pts = np.asarray(self.points, dtype=np.float64)
        tris = np.asarray(self.triangles, dtype=np.int64)
        if pts.ndim != 2 or pts.shape[1] != 3:
            raise ValueError(f"surface points must be (N,3), got {pts.shape}")
        if tris.ndim != 2 or tris.shape[1] != 3 or tris.shape[0] == 0:
            raise ValueError(f"surface triangles must be (T,3) with T>0, got {tris.shape}")
        if tris.min() < 0 or tris.max() >= pts.shape[0]:
            raise ValueError("surface triangles index points out of range")
        object.__setattr__(self, "points", pts)
        object.__setattr__(self, "triangles", tris)

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.points.min(axis=0), self.points.max(axis=0)

    def to_dict(self) -> dict[str, Any]:
        lo, hi = self.bounds
        return {
            "label": self.label,
            "points": int(self.points.shape[0]),
            "triangles": int(self.triangles.shape[0]),
            "bbox_min_m": [float(v) for v in lo],
            "bbox_max_m": [float(v) for v in hi],
        }


@dataclass(frozen=True)
class CollisionReport:
    """Verdict for one horn surface against one cabinet solid."""

    status: str
    method: str
    min_gap_m: float
    min_distance_m: float | None
    distance_exact: bool
    aabb_gap_m: float
    intersecting: bool
    nested: str | None
    witness_horn_m: tuple[float, float, float] | None
    witness_box_m: tuple[float, float, float] | None
    detail: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == CLEARANCE_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "horn_box_clearance_v1",
            "status": self.status,
            "method": self.method,
            "min_gap_m": float(self.min_gap_m),
            "min_distance_m": None if self.min_distance_m is None else float(self.min_distance_m),
            "distance_exact": bool(self.distance_exact),
            "aabb_gap_m": float(self.aabb_gap_m),
            "intersecting": bool(self.intersecting),
            "nested": self.nested,
            "witness_horn_m": None if self.witness_horn_m is None else list(self.witness_horn_m),
            "witness_box_m": None if self.witness_box_m is None else list(self.witness_box_m),
            "detail": dict(self.detail),
            "bounds": (
                "exact triangle-vs-box distance for BL's rectangular vented enclosure; "
                "distance_exact=False means min_distance_m is a lower bound at the search "
                "cutoff (still enough to prove PASS when it is >= min_gap_m)"),
        }


# --------------------------------------------------------------------------- surfaces

def read_surface(path: str | Path, *, label: str | None = None) -> Surface:
    """Read the first triangle block of a ``.msh`` file (metres, as written by meshers)."""
    import meshio

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"surface mesh not found: {p}")
    mesh = meshio.read(p)
    tris = None
    for block in mesh.cells:
        if block.type == "triangle":
            tris = np.asarray(block.data, dtype=np.int64)
            break
    if tris is None or tris.size == 0:
        raise ValueError(f"mesh {p} has no triangle cells")
    return Surface(points=np.asarray(mesh.points, dtype=np.float64), triangles=tris,
                   label=str(label or p.stem))


def surface_from_arrays(points: Sequence[Sequence[float]], triangles: Sequence[Sequence[int]],
                        *, label: str = "") -> Surface:
    return Surface(points=np.asarray(points, dtype=np.float64),
                   triangles=np.asarray(triangles, dtype=np.int64), label=label)


def transform_surface(surface: Surface, *, translation_mm: Sequence[float] = (0.0, 0.0, 0.0),
                      scale_factor: float = 1.0, label: str | None = None) -> Surface:
    """Apply BL's own order: ``points * scale_to_m + translation_m`` (translation in metres)."""
    t = np.asarray([float(v) for v in translation_mm], dtype=np.float64)
    if t.shape != (3,):
        raise ValueError(f"translation_mm must have 3 components, got {translation_mm!r}")
    if not (math.isfinite(scale_factor) and scale_factor > 0.0):
        raise ValueError(f"scale_factor must be positive and finite, got {scale_factor!r}")
    pts = surface.points * float(scale_factor) + t / 1000.0
    return Surface(points=pts, triangles=surface.triangles,
                   label=surface.label if label is None else label)


# --------------------------------------------------------------------------- primitives

def _box_edges(lo: np.ndarray, hi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The 12 edges of an axis-aligned box as arrays of endpoints."""
    signs = np.array([[i, j, k] for i in (0, 1) for j in (0, 1) for k in (0, 1)], dtype=float)
    corners = lo[None, :] + signs * (hi - lo)[None, :]
    pairs = ((0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6), (3, 7),
             (4, 5), (4, 6), (5, 7), (6, 7))
    p = np.array([corners[a] for a, _ in pairs])
    q = np.array([corners[b] for _, b in pairs])
    return p, q


def _point_box_distance(p: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    sep = np.maximum.reduce([lo - p, p - hi, np.zeros_like(p)])
    return np.linalg.norm(sep, axis=-1)


def _closest_segment_segment(p1: np.ndarray, q1: np.ndarray, p2: np.ndarray,
                             q2: np.ndarray, *, eps: float = 1e-15) -> tuple[np.ndarray, np.ndarray]:
    """Closest points between segments (Ericson, vectorised)."""
    d1, d2 = q1 - p1, q2 - p2
    r = p1 - p2
    a = np.einsum("ij,ij->i", d1, d1)
    e = np.einsum("ij,ij->i", d2, d2)
    f = np.einsum("ij,ij->i", d2, r)
    c = np.einsum("ij,ij->i", d1, r)
    b = np.einsum("ij,ij->i", d1, d2)

    degen_a = a <= eps
    degen_e = e <= eps
    normal = ~degen_a & ~degen_e
    denom = a * e - b * b

    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(np.abs(denom) > eps,
                     np.clip((b * f - c * e) / np.where(denom == 0.0, 1.0, denom), 0.0, 1.0), 0.0)
        t = np.where(normal & (e > eps),
                     (b * s + f) / np.where(e == 0.0, 1.0, e), 0.0)
    low = normal & (t < 0.0)
    high = normal & (t > 1.0)
    t = np.where(low, 0.0, np.where(high, 1.0, t))
    with np.errstate(divide="ignore", invalid="ignore"):
        s_low = np.clip(-c / np.where(a == 0.0, 1.0, a), 0.0, 1.0)
        s_high = np.clip((b - c) / np.where(a == 0.0, 1.0, a), 0.0, 1.0)
    s = np.where(low, s_low, np.where(high, s_high, s))
    # degenerate branches
    s = np.where(degen_a, 0.0, s)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(degen_a & ~degen_e,
                     np.clip(f / np.where(e == 0.0, 1.0, e), 0.0, 1.0), t)
    t = np.where(degen_a & degen_e, 0.0, t)
    return p1 + d1 * s[:, None], p2 + d2 * s[:, None]


def _segment_box_intersects(p: np.ndarray, q: np.ndarray,
                            lo: np.ndarray, hi: np.ndarray, *, eps: float = 1e-15) -> np.ndarray:
    """Slab clip: does the closed segment ``p-q`` touch the box? Vectorised over rows."""
    d = q - p
    t0 = np.zeros(p.shape[0])
    t1 = np.ones(p.shape[0])
    ok = np.ones(p.shape[0], dtype=bool)
    for axis in range(3):
        pa, da = p[:, axis], d[:, axis]
        parallel = np.abs(da) <= eps
        outside = parallel & ((pa < lo[axis]) | (pa > hi[axis]))
        ok &= ~outside
        with np.errstate(divide="ignore", invalid="ignore"):
            ta = (lo[axis] - pa) / np.where(parallel, 1.0, da)
            tb = (hi[axis] - pa) / np.where(parallel, 1.0, da)
        tmin = np.where(parallel, -np.inf, np.minimum(ta, tb))
        tmax = np.where(parallel, np.inf, np.maximum(ta, tb))
        # keep the raw interval: clamping to [0,1] before the comparison turns a
        # segment lying wholly outside a slab into a false t0 == t1 hit
        t0 = np.maximum(t0, tmin)
        t1 = np.minimum(t1, tmax)
        ok &= ~(t1 < t0)
    return ok


def segment_box_distance(p: np.ndarray, q: np.ndarray, box: Box, *,
                         box_edges: tuple[np.ndarray, np.ndarray] | None = None
                         ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact distance between ``rows of p-q`` and ``box``.

    Returns ``(distance, witness_on_segment, witness_on_box, intersects)``.
    """
    lo = np.asarray(box.lo)
    hi = np.asarray(box.hi)
    ep, eq = box_edges if box_edges is not None else _box_edges(lo, hi)
    n = p.shape[0]
    best = np.full(n, np.inf)
    ws = np.zeros((n, 3))
    wb = np.zeros((n, 3))

    def offer(d: np.ndarray, ps: np.ndarray, pb: np.ndarray) -> None:
        nonlocal best, ws, wb
        m = d < best
        if np.any(m):
            best = np.where(m, d, best)
            ws[m] = ps[m]
            wb[m] = pb[m]

    for end in (p, q):
        clamped = np.clip(end, lo, hi)
        offer(_point_box_distance(end, lo, hi), end, clamped)
    for index in range(ep.shape[0]):
        c_seg, c_edge = _closest_segment_segment(
            p, q, np.repeat(ep[index][None, :], n, axis=0), np.repeat(eq[index][None, :], n, axis=0))
        offer(np.linalg.norm(c_seg - c_edge, axis=1), c_seg, c_edge)
    intersects = _segment_box_intersects(p, q, lo, hi)
    best = np.where(intersects, 0.0, best)
    ws = np.where(intersects[:, None], p, ws)
    wb = np.where(intersects[:, None], p, wb)
    return best, ws, wb, intersects


# --------------------------------------------------------------------------- surface vs box

def points_inside_box(points: np.ndarray, box: Box, *, tol: float = 1e-12) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64)
    lo = np.asarray(box.lo) + tol
    hi = np.asarray(box.hi) - tol
    return np.all((pts >= lo) & (pts <= hi), axis=1)


def triangle_surface_box_distance(surface: Surface, box: Box, *,
                                  cutoff_m: float = 0.05) -> dict[str, Any]:
    """Exact minimum distance between a triangle surface and a solid box.

    Triangles whose AABB is farther than ``cutoff_m`` from the box are skipped; when
    nothing closer exists the distance is reported as a lower bound at ``cutoff_m``
    (``exact=False``), which still proves any required gap up to that value.
    """
    if not (math.isfinite(cutoff_m) and cutoff_m > 0.0):
        raise ValueError(f"cutoff_m must be positive and finite, got {cutoff_m!r}")
    lo = np.asarray(box.lo)
    hi = np.asarray(box.hi)
    pts = surface.points
    tris = surface.triangles
    tri_lo = pts[tris].min(axis=1) - cutoff_m
    tri_hi = pts[tris].max(axis=1) + cutoff_m
    keep = np.all((tri_hi >= lo) & (tri_lo <= hi), axis=1)
    idx = np.nonzero(keep)[0]

    hull_lo, hull_hi = surface.bounds
    aabb_gap = float(np.linalg.norm(np.maximum.reduce(
        [lo - hull_hi, hull_lo - hi, np.zeros(3)])))

    if idx.size == 0:
        return {"min_distance_m": cutoff_m, "exact": False, "intersecting": False,
                "aabb_gap_m": aabb_gap, "witness_horn_m": None, "witness_box_m": None,
                "triangles_tested": 0}

    edges = ((0, 1), (1, 2), (2, 0))
    box_edges = _box_edges(lo, hi)
    best = math.inf
    witness: tuple[np.ndarray, np.ndarray] | None = None
    intersecting = False
    for (i, j) in edges:
        p = pts[tris[idx, i]]
        q = pts[tris[idx, j]]
        d, ws, wb, hit = segment_box_distance(p, q, box, box_edges=box_edges)
        if np.any(hit):
            intersecting = True
            k = int(np.nonzero(hit)[0][0])
            best = 0.0
            witness = (ws[k], wb[k])
            break
        k = int(np.argmin(d))
        if float(d[k]) < best:
            best = float(d[k])
            witness = (ws[k], wb[k])
    exact = best < cutoff_m
    return {
        "min_distance_m": float(best),
        "exact": bool(exact),
        "intersecting": bool(intersecting or best <= 1e-12),
        "aabb_gap_m": aabb_gap,
        "witness_horn_m": None if witness is None else tuple(float(v) for v in witness[0]),
        "witness_box_m": None if witness is None else tuple(float(v) for v in witness[1]),
        "triangles_tested": int(idx.size),
    }


def _verify_box_matches_surface(box: Box, surface: Surface,
                                tol_m: float = _BBOX_TOL_M) -> tuple[bool, str]:
    lo, hi = surface.bounds
    err = max(float(np.max(np.abs(lo - np.asarray(box.lo)))),
              float(np.max(np.abs(hi - np.asarray(box.hi)))))
    if err > tol_m:
        return False, (f"compiled exterior mesh bbox differs from the parameter box by "
                       f"{err:.3e} m (>{tol_m:.1e} m); the box collision model does not "
                       f"describe this mesh")
    return True, ""


def test_horn_box_clearance(horn: Surface, box: Box, *, min_gap_m: float,
                            cutoff_m: float = 0.05,
                            compiled_exterior: Surface | None = None,
                            extra_solids: Iterable[Box] = ()) -> CollisionReport:
    """PASS / VIOLATION / UNPROVEN for the placed horn against the cabinet solid.

    ``extra_solids`` covers mechanical volumes the generated enclosure shell does not
    represent but the real hardware has -- above all the woofer frame/basket and motor,
    which sits on the baffle at the driver's mounted height and can reach past the
    enclosure outline.  They are tested exactly like the cabinet box; the worst verdict
    wins.
    """
    if not (math.isfinite(min_gap_m) and min_gap_m > 0.0):
        raise ValueError(f"min_gap_m must be positive and finite, got {min_gap_m!r}")
    cutoff = max(float(cutoff_m), 4.0 * min_gap_m)
    detail: dict[str, Any] = {"cutoff_m": cutoff}
    if compiled_exterior is not None:
        ok, why = _verify_box_matches_surface(box, compiled_exterior)
        detail["compiled_exterior_matches_box"] = ok
        if not ok:
            detail["reason"] = why
            return CollisionReport(
                status=CLEARANCE_UNPROVEN, method="exact_triangle_box_v1",
                min_gap_m=float(min_gap_m), min_distance_m=None, distance_exact=False,
                aabb_gap_m=math.nan, intersecting=False, nested=None,
                witness_horn_m=None, witness_box_m=None, detail=detail)

    solids = [("cabinet", box)] + [(f"extra_solid_{i}", solid)
                                   for i, solid in enumerate(extra_solids)]
    inside_counts: dict[str, int] = {}
    for name, solid in solids:
        count = int(np.count_nonzero(points_inside_box(horn.points, solid)))
        if count:
            inside_counts[name] = count
    nested = None
    if inside_counts:
        nested = "; ".join(f"{count}_horn_vertices_inside_{name}"
                           for name, count in inside_counts.items())
    result = triangle_surface_box_distance(horn, box, cutoff_m=cutoff)
    dist = float(result["min_distance_m"])
    for _name, solid in solids[1:]:
        other = triangle_surface_box_distance(horn, solid, cutoff_m=cutoff)
        if float(other["min_distance_m"]) < dist:
            result = other
            dist = float(other["min_distance_m"])
    detail.update({
        "triangles_tested": int(result.get("triangles_tested") or 0),
        "horn_bbox_m": [list(map(float, horn.bounds[0])), list(map(float, horn.bounds[1]))],
        "cabinet_box": box.to_dict(),
        "extra_solids": [solid.to_dict() for _name, solid in solids[1:]],
    })
    if nested is not None:
        status = CLEARANCE_VIOLATION
        detail["reason"] = f"horn geometry inside the cabinet solid ({nested})"
    elif bool(result["intersecting"]):
        status = CLEARANCE_VIOLATION
        detail["reason"] = "horn surface touches or penetrates the cabinet solid"
    elif dist + _DIST_EPS_M >= min_gap_m:
        status = CLEARANCE_PASS
    elif not bool(result["exact"]):
        status = CLEARANCE_UNPROVEN
        detail["reason"] = "distance is only a lower bound below the required minimum"
    else:
        status = CLEARANCE_VIOLATION
        detail["reason"] = (f"minimum surface distance {dist:.6g} m < required "
                            f"{min_gap_m:.6g} m")
    return CollisionReport(
        status=status, method="exact_triangle_box_v1", min_gap_m=float(min_gap_m),
        min_distance_m=dist if math.isfinite(dist) else None,
        distance_exact=bool(result["exact"]), aabb_gap_m=float(result["aabb_gap_m"]),
        intersecting=bool(result["intersecting"]), nested=nested,
        witness_horn_m=result.get("witness_horn_m"),
        witness_box_m=result.get("witness_box_m"), detail=detail)
