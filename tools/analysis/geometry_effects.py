"""Canonical final-surface sampler for the parameter/geometry audit (B2, M0).

Everything here goes through the installed ``hornlab_mesher`` point-grid API
(``config_builder.resolve_geometry`` via :func:`hornlab_search.bo.data.materialize_geometry`).
We never reimplement OSSE/R-OSSE/ICW/FREEFORM formulas or gmsh meshing, never call BEM, and never
change cache keys.

The sampler preserves physical and normalized z/depth, H/V/diagonal meridians, azimuthal
cross-section contours, area/aspect, throat/mouth/depth, axial stretch and non-circular contours.
Every descriptor records its station/azimuth grid, units, seam/symmetry convention, raw API
provenance and a sampling-convergence check (coarse vs finer geometry resolve — explicitly not a
mesh/acoustic convergence claim).

Unsupported CAD and point-grid recipes are refused.  A sampled surface whose axial stations are
not monotone at some azimuth (a folded/rollback wall) is refused as non-star-shaped; we do not
force a radial representation onto it.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from hornlab_search.bo.data import UnsupportedGeometryError, materialize_geometry

DEFAULT_RESOLUTION_MM = 12.0
CONVERGENCE_TOL_MM = 0.5
CONVERGENCE_REL_TOL = 0.01
EQUIVALENCE_TOL_MM = 0.05
CANONICAL_ANGLES_DEG = tuple(float(a) for a in range(0, 360, 15))
CANONICAL_T = tuple(float(t) for t in np.linspace(0.0, 1.0, 65))
STATION_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
#: Fixed 64-azimuth mouth contour used by the conditional-activity audit.  This is deliberately
#: coarser in angle than the raw geometry grid but fine enough to reproduce the hardening
#: decision's 64-azimuth morph-exponent check.
EXPONENT_CONTOUR_AZIMUTHS_DEG = tuple(float(a) for a in np.linspace(0.0, 360.0, 64,
                                                                   endpoint=False))
UNITS = "mm"

_SYMMETRY_FACTOR = {"1234": 1, "12": 2, "14": 2, "1": 4}
_SYMMETRY_PLANES = {"1234": (), "12": ("y",), "14": ("x",), "1": ("x", "y")}
_SPAN_DEG = {"1234": (0.0, 360.0), "12": (0.0, 180.0), "14": (-90.0, 90.0), "1": (0.0, 90.0)}


@dataclass(frozen=True)
class GeometrySample:
    design_hash: str
    family: str
    units: str
    azimuths_deg: tuple[float, ...]
    t_stations: tuple[float, ...]
    z_mm: np.ndarray
    z_norm: np.ndarray
    radius_mm: np.ndarray                 # (n_azimuth, n_station)
    meridians_mm: dict[str, np.ndarray]   # H / V / diagonal_45 / diagonal_135
    cross_sections: tuple[dict, ...]
    descriptors: dict
    grid: dict
    convergence: dict
    provenance: dict

    def as_dict(self) -> dict:
        return {
            "design_hash": self.design_hash,
            "family": self.family,
            "units": self.units,
            "azimuths_deg": list(self.azimuths_deg),
            "t_stations": list(self.t_stations),
            "z_mm": [float(v) for v in self.z_mm],
            "z_norm": [float(v) for v in self.z_norm],
            "radius_mm": [[float(v) for v in row] for row in self.radius_mm],
            "meridians_mm": {k: [float(v) for v in arr] for k, arr in self.meridians_mm.items()},
            "cross_sections": [dict(s) for s in self.cross_sections],
            "descriptors": dict(self.descriptors),
            "grid": dict(self.grid),
            "convergence": dict(self.convergence),
            "provenance": dict(self.provenance),
        }


# ---------------------------------------------------------------------------- helpers


def _dedup_angles(angles: np.ndarray, radii: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.mod(np.asarray(angles, dtype=float), math.tau)
    order = np.argsort(a)
    a, r = a[order], np.asarray(radii, dtype=float)[order]
    keep = np.concatenate(([True], np.diff(a) > 1e-9))
    return a[keep], r[keep]


def _quad_grid_area(points: np.ndarray, *, wrap: bool) -> float:
    p = np.asarray(points, dtype=float)
    if wrap:
        p = np.vstack([p, p[:1]])
    a, b, c, d = p[:-1, :-1], p[1:, :-1], p[1:, 1:], p[:-1, 1:]
    return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=-1).sum()
                 + 0.5 * np.linalg.norm(np.cross(c - a, d - a), axis=-1).sum())


def assert_star_shaped(points: np.ndarray, *, z_tol_mm: float = 1e-6) -> None:
    """Refuse a surface that is not a single-valued radial star about the axis.

    The point grid must have strictly positive finite radius everywhere and non-decreasing axial
    station along every azimuth row.  A folded/rollback wall cannot be represented by a radius
    field and is explicitly unsupported rather than silently flattened.
    """
    p = np.asarray(points, dtype=float)
    if p.ndim != 3 or p.shape[2] != 3 or p.shape[0] < 2 or p.shape[1] < 2:
        raise UnsupportedGeometryError(
            f"expected a (n_phi, n_station, 3) point grid, got shape {p.shape}")
    if not np.all(np.isfinite(p)):
        raise UnsupportedGeometryError("point grid contains non-finite coordinates")
    r = np.hypot(p[:, :, 0], p[:, :, 1])
    if np.any(r <= 0.0):
        raise UnsupportedGeometryError("point grid contains a non-positive radius")
    dz = np.diff(p[:, :, 2], axis=1)
    if np.any(dz < -float(z_tol_mm)):
        raise UnsupportedGeometryError(
            "axial stations are not monotone at some azimuth (folded/rollback or non-star-shaped "
            "surface); a radial representation is unsupported")


def _raw_angles(points: np.ndarray) -> np.ndarray:
    a = np.arctan2(points[:, 0, 1], points[:, 0, 0])
    return np.asarray(a, dtype=float)


def _full_circle_field(points: np.ndarray, quadrants: str) -> tuple[np.ndarray, np.ndarray]:
    """Return sorted full-circle azimuths (rad) and radius rows for the sampled surface."""
    r = np.hypot(points[:, :, 0], points[:, :, 1])
    a = _raw_angles(points)
    if quadrants == "1234":
        # Full ring: angles may wrap from +pi to -pi; sort in [0, 2pi).
        angles, radii = _dedup_angles(a, r)
    elif quadrants == "1":
        # Quarter span 0..pi/2; mirror about pi/2 then about pi.
        order = np.argsort(a)
        aq, rq = a[order], r[order]
        mirror_x = math.pi - aq[::-1]
        half_a, half_r = _dedup_angles(np.concatenate([aq, mirror_x]),
                                       np.concatenate([rq, rq[::-1]]))
        angles, radii = _dedup_angles(np.concatenate([half_a, half_a + math.pi]),
                                      np.concatenate([half_r, half_r]))
    elif quadrants == "12":
        # Half span 0..pi; mirror about pi.
        angles, radii = _dedup_angles(np.concatenate([a, a + math.pi]),
                                      np.concatenate([r, r]))
    elif quadrants == "14":
        # Span -pi/2..pi/2 symmetric about the x axis (y=0); mirror about 0.
        angles, radii = _dedup_angles(np.concatenate([a, -a]), np.concatenate([r, r]))
    else:
        raise UnsupportedGeometryError(f"unsupported quadrants token {quadrants!r}")
    if angles.size < 2:
        raise UnsupportedGeometryError("the full-circle surface has fewer than two azimuths")
    # Periodic interpolation anchor at 2*pi.
    a0 = np.mod(angles, math.tau)
    order = np.argsort(a0)
    a0, radii = a0[order], radii[order]
    if a0[0] > 1e-12:
        # Rotate so the first sample is at 0 where possible; interpolation below handles any
        # starting point via the periodic anchor.
        pass
    a_ext = np.concatenate([a0, [math.tau]])
    r_ext = np.concatenate([radii, radii[:1]], axis=0)
    return a_ext, r_ext


def _canonical_field(points: np.ndarray, quadrants: str) -> tuple[np.ndarray, np.ndarray]:
    """Resample onto the fixed canonical (azimuth, normalized-depth) grid."""
    assert_star_shaped(points)
    z = points[:, :, 2]
    z_station = np.median(z, axis=0)
    z_span = float(z_station[-1] - z_station[0])
    if not math.isfinite(z_span) or z_span <= 0.0:
        raise UnsupportedGeometryError("resolved surface has no positive axial depth")
    t = (z_station - z_station[0]) / z_span
    if np.any(np.diff(t) <= 0.0):
        raise UnsupportedGeometryError("normalized axial stations are not strictly increasing")
    full_a, full_r = _full_circle_field(points, quadrants)
    canon_rad = np.radians(np.asarray(CANONICAL_ANGLES_DEG, dtype=float))
    R_raw = np.empty((canon_rad.size, points.shape[1]), dtype=float)
    for j in range(points.shape[1]):
        R_raw[:, j] = np.interp(canon_rad, full_a, full_r[:, j])
    tgt_t = np.asarray(CANONICAL_T, dtype=float)
    R = np.vstack([np.interp(tgt_t, t, R_raw[i]) for i in range(canon_rad.size)])
    z_can = np.interp(tgt_t, t, z_station)
    return R, z_can


def _descriptors(points: np.ndarray, quadrants: str, params: dict) -> dict:
    x, y, z = points[:, :, 0], points[:, :, 1], points[:, :, 2]
    r = np.hypot(x, y)
    throat = float(np.mean(r[:, 0]))
    mouth_r = r[:, -1]
    width = float(2.0 * np.max(np.abs(x[:, -1])))
    height = float(2.0 * np.max(np.abs(y[:, -1])))
    depth = float(np.max(z) - np.min(z))
    min_r = float(np.min(r))
    max_r = float(np.max(r))
    aspect = width / height if height else float("inf")
    radial_ratio = float(np.max(mouth_r) / np.min(mouth_r)) if np.min(mouth_r) > 0 else float("inf")
    factor = _SYMMETRY_FACTOR.get(quadrants, 1)
    area_sampled = _quad_grid_area(points, wrap=(quadrants == "1234"))
    ratios = (np.max(r, axis=0) / np.min(r, axis=0))
    noncircular = [float(f) for f, q in zip(np.linspace(0.0, 1.0, r.shape[1]), ratios)
                   if np.isfinite(q) and q > 1.0 + 1e-3]
    station_z_spread = float(np.max(np.ptp(z, axis=0)))
    try:
        s1 = float(params.get("s1", 0.0) or 0.0)
        s2 = float(params.get("s2", 0.0) or 0.0)
        stretch_active = bool(s1 != 0.0 and s2 != 0.0)
    except (TypeError, ValueError):
        s1 = s2 = 0.0
        stretch_active = False
    return {
        "throat_radius_mm": throat,
        "mouth_width_mm": width,
        "mouth_height_mm": height,
        "depth_mm": depth,
        "area_sampled_mm2": float(area_sampled),
        "area_full_domain_mm2": float(area_sampled * factor),
        "symmetry_factor": int(factor),
        "aspect_ratio": float(aspect),
        "mouth_radial_ratio": radial_ratio,
        "min_radius_mm": min_r,
        "max_radius_mm": max_r,
        "circular_mouth": bool(abs(radial_ratio - 1.0) <= 1e-6 and abs(aspect - 1.0) <= 1e-6),
        "noncircular_station_fractions": noncircular,
        "station_z_spread_mm": station_z_spread,
        "canonical_z_note": ("expected 0 for a symmetric axial station grid; a nonzero spread "
                             "means the median station was used as the shared normalized-depth "
                             "grid and should be read as a sampling convention, not a new law"),
        "s1": s1,
        "s2": s2,
        "stretch_active": stretch_active,
    }


def _build_sample(design, mat: dict) -> GeometrySample:
    points = np.asarray(mat["inner_points"], dtype=float)
    quadrants = str(mat.get("quadrants", "1234"))
    params = getattr(design, "params", {}) or {}
    R, z_can = _canonical_field(points, quadrants)
    z0 = float(z_can[0])
    span = float(z_can[-1] - z0)
    z_norm = (z_can - z0) / span if span > 0 else np.zeros_like(z_can)
    angles = tuple(float(v) for v in CANONICAL_ANGLES_DEG)
    meridian_idx = {
        "H": angles.index(0.0),
        "diagonal_45": angles.index(45.0),
        "V": angles.index(90.0),
        "diagonal_135": angles.index(135.0),
    }
    meridians = {k: np.asarray(R[i], dtype=float) for k, i in meridian_idx.items()}
    cross_sections = []
    for frac in STATION_FRACTIONS:
        j = int(min(len(CANONICAL_T) - 1, round(frac * (len(CANONICAL_T) - 1))))
        radii = np.asarray(R[:, j], dtype=float)
        rad = np.radians(np.asarray(angles, dtype=float))
        cross_sections.append({
            "t": float(CANONICAL_T[j]),
            "angles_deg": list(angles),
            "radius_mm": [float(v) for v in radii],
            "x_mm": [float(v) for v in radii * np.cos(rad)],
            "y_mm": [float(v) for v in radii * np.sin(rad)],
        })
    descriptors = _descriptors(points, quadrants, params)
    grid = {
        "raw_n_phi": int(points.shape[0]),
        "raw_n_stations": int(points.shape[1]),
        "canonical_n_azimuth": len(CANONICAL_ANGLES_DEG),
        "canonical_n_stations": len(CANONICAL_T),
        "canonical_azimuth_step_deg": 15.0,
        "canonical_t_step": float(CANONICAL_T[1] - CANONICAL_T[0]),
        "resolution_mm": float(mat.get("resolution_mm", DEFAULT_RESOLUTION_MM)),
        "quadrants": quadrants,
        "symmetry_planes": list(_SYMMETRY_PLANES.get(quadrants, ())),
        "azimuth_span_deg": list(_SPAN_DEG.get(quadrants, (0.0, 360.0))),
        "seam": "periodic" if quadrants == "1234" else "mirror planes (no seam)",
        "full_circle_sampled": quadrants == "1234",
        "left_right_symmetric": quadrants in ("1", "12", "1234"),
        "up_down_symmetric": quadrants in ("1", "14", "1234"),
        "sampling_mode": mat.get("sampling_metadata", {}).get("geometrySampleAxialMap"),
    }
    provenance = {
        "api": mat.get("api"),
        "formula": mat.get("formula"),
        "mode": mat.get("mode"),
        "surface_fit": mat.get("surface_fit"),
        "design_hash": design.hash(),
        "units": UNITS,
        "sampling_metadata": dict(mat.get("sampling_metadata") or {}),
    }
    return GeometrySample(
        design_hash=design.hash(), family=str(getattr(design, "family", "")), units=UNITS,
        azimuths_deg=angles, t_stations=tuple(float(v) for v in CANONICAL_T),
        z_mm=np.asarray(z_can, dtype=float), z_norm=z_norm,
        radius_mm=np.asarray(R, dtype=float), meridians_mm=meridians,
        cross_sections=tuple(cross_sections), descriptors=descriptors, grid=grid,
        convergence={}, provenance=provenance,
    )


def sample_surface(design, config, *, resolution_mm: float = DEFAULT_RESOLUTION_MM,
                   check_convergence: bool = True) -> GeometrySample:
    """Sample the canonical final transformed surface through the installed mesher API."""
    mat = materialize_geometry(design, config, resolution_mm=float(resolution_mm))
    sample = _build_sample(design, mat)
    if not check_convergence:
        return GeometrySample(**{**sample.__dict__,
                                 "convergence": {
                                     "checked": False,
                                     "note": "sampling convergence not requested",
                                     "units": UNITS,
                                 }})
    fine = materialize_geometry(design, config, resolution_mm=float(resolution_mm) / 2.0)
    fine_sample = _build_sample(design, fine)
    delta = surface_delta(sample, fine_sample)
    converged = (delta["max_abs_radius_delta_mm"] <= CONVERGENCE_TOL_MM
                 and delta["max_relative_radius_delta"] <= CONVERGENCE_REL_TOL)
    convergence = {
        "checked": True,
        "coarse_resolution_mm": float(resolution_mm),
        "fine_resolution_mm": float(resolution_mm) / 2.0,
        "coarse_grid": [int(sample.grid["raw_n_phi"]), int(sample.grid["raw_n_stations"])],
        "fine_grid": [int(fine_sample.grid["raw_n_phi"]), int(fine_sample.grid["raw_n_stations"])],
        "max_abs_radius_delta_mm": float(delta["max_abs_radius_delta_mm"]),
        "max_relative_radius_delta": float(delta["max_relative_radius_delta"]),
        "abs_tolerance_mm": CONVERGENCE_TOL_MM,
        "relative_tolerance": CONVERGENCE_REL_TOL,
        "converged": bool(converged),
        "units": UNITS,
        "note": "geometry-sampling convergence only; not mesh, acoustic or BEM convergence",
    }
    return GeometrySample(**{**sample.__dict__, "convergence": convergence})


def surface_delta(a: GeometrySample, b: GeometrySample, *,
                  tol_mm: float = EQUIVALENCE_TOL_MM) -> dict:
    """Compare two canonical surfaces; geometry equivalence is separate from ``Design.hash``."""
    if a.radius_mm.shape != b.radius_mm.shape:
        raise ValueError(f"canonical shapes differ: {a.radius_mm.shape} vs {b.radius_mm.shape}")
    delta = np.abs(np.asarray(a.radius_mm) - np.asarray(b.radius_mm))
    zdelta = np.abs(np.asarray(a.z_mm) - np.asarray(b.z_mm))
    scale = float(max(np.max(np.abs(b.radius_mm)), 1.0))
    max_abs = float(np.max(delta))
    return {
        "max_abs_radius_delta_mm": max_abs,
        "mean_abs_radius_delta_mm": float(np.mean(delta)),
        "max_relative_radius_delta": float(max_abs / scale),
        "max_abs_z_delta_mm": float(np.max(zdelta)),
        "tolerance_mm": float(tol_mm),
        "changed": bool(max_abs > float(tol_mm)),
        "design_hashes_equal": a.design_hash == b.design_hash,
        "surface_fingerprints_equal": surface_fingerprint(a) == surface_fingerprint(b),
    }


def surfaces_equivalent(a: GeometrySample, b: GeometrySample,
                        tol_mm: float = EQUIVALENCE_TOL_MM) -> bool:
    return not surface_delta(a, b, tol_mm=tol_mm)["changed"]


def surface_fingerprint(sample: GeometrySample) -> str:
    """Stable sampled-surface fingerprint; never relabelled as a production cache key."""
    h = hashlib.sha256()
    for arr in (sample.radius_mm, sample.z_mm):
        rounded = np.round(np.asarray(arr, dtype=float), 6)
        h.update(str(tuple(rounded.shape)).encode())
        h.update(np.ascontiguousarray(rounded, dtype="<f8").tobytes())
    return h.hexdigest()[:20]


def mouth_contour_at_azimuths(design, config, *,
                              azimuths_deg=EXPONENT_CONTOUR_AZIMUTHS_DEG,
                              station_fraction: float = 1.0,
                              resolution_mm: float = DEFAULT_RESOLUTION_MM) -> dict:
    """Sample the canonical mouth cross-section at a caller-specified azimuth grid.

    Used by the conditional-activity audit: the target-1 morph exponent must leave the mouth
    contour unchanged at all 64 sampled azimuths, while target 3 must change most of them.
    The surface still comes from the installed ``hornlab_mesher`` geometry resolve; this helper
    only interpolates the full-circle radius field, it does not reimplement a profile law.
    """
    if not 0.0 <= float(station_fraction) <= 1.0:
        raise ValueError("station_fraction must be in [0, 1]")
    mat = materialize_geometry(design, config, resolution_mm=float(resolution_mm))
    points = np.asarray(mat["inner_points"], dtype=float)
    assert_star_shaped(points)
    full_a, full_r = _full_circle_field(points, str(mat.get("quadrants", "1234")))
    j = int(min(points.shape[1] - 1,
                round(float(station_fraction) * (points.shape[1] - 1))))
    az = np.asarray(azimuths_deg, dtype=float)
    radius = np.interp(np.radians(az), full_a, full_r[:, j])
    return {
        "azimuths_deg": [float(v) for v in az],
        "radius_mm": [float(v) for v in radius],
        "n_azimuths": int(az.size),
        "station_fraction": float(station_fraction),
        "resolution_mm": float(resolution_mm),
        "units": UNITS,
        "api": mat.get("api"),
    }


def meridian_activity(sample_a: GeometrySample, sample_b: GeometrySample,
                      meridian: str) -> dict:
    """Change of one named meridian (H / V / diagonal_45 / diagonal_135) between two samples."""
    if meridian not in sample_a.meridians_mm:
        raise ValueError(f"unknown meridian {meridian!r}")
    delta = np.abs(np.asarray(sample_a.meridians_mm[meridian])
                   - np.asarray(sample_b.meridians_mm[meridian]))
    return {
        "meridian": meridian,
        "max_abs_delta_mm": float(np.max(delta)),
        "mean_abs_delta_mm": float(np.mean(delta)),
        "changed": bool(np.max(delta) > EQUIVALENCE_TOL_MM),
    }


def with_params(design, **overrides):
    """Copy a Design with top-level parameter overrides (for legal perturbation tests)."""
    import copy

    from hornlab_search.types import Design

    params = copy.deepcopy(getattr(design, "params", {}) or {})
    params.update(overrides)
    return Design(str(getattr(design, "family", "FREEFORM")), params)


__all__ = [
    "DEFAULT_RESOLUTION_MM",
    "CONVERGENCE_TOL_MM",
    "CONVERGENCE_REL_TOL",
    "EQUIVALENCE_TOL_MM",
    "CANONICAL_ANGLES_DEG",
    "CANONICAL_T",
    "STATION_FRACTIONS",
    "EXPONENT_CONTOUR_AZIMUTHS_DEG",
    "UNITS",
    "UnsupportedGeometryError",
    "GeometrySample",
    "assert_star_shaped",
    "sample_surface",
    "surface_delta",
    "surfaces_equivalent",
    "surface_fingerprint",
    "mouth_contour_at_azimuths",
    "meridian_activity",
    "with_params",
    "materialize_geometry",
]
