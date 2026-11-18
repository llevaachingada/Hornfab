"""Canonical surface record, contract v2 (stage 3 WP 3.1/3.2, senior plan 2026-11-17).

One sampled description of the inner acoustic wall of any non-CAD, single-sheet horn, built from
the generator WITHOUT meshing, so families can be compared, gated, rebuilt and edited in one
language. Contract: ``scratch/fable_architecture/CANONICAL_SURFACE_CONTRACT.md`` §2-§9 as amended
by §12 (v2). Validated in scratch by N1/N1b/X4 (6/6 lanes, 55/55 designs) - this module packages
that sampler; it does not change it.

* Stations: ``n_s`` (>= 65) points per meridian at equal NORMALISED ARC LENGTH (rollback-safe).
* Azimuths: ``n_phi`` (>= 61 per quarter, step <= 1.5 deg) equally spaced over the modelled
  sector, interpolated in unwrapped azimuth at each station.
* Units: millimetres; z is the horn axis (throat -> mouth); phi = 0 is the horizontal wall.
* The record is a CACHE of the generator's geometry: never an identity, never the mesh.

Nothing here touches the solver, a stored row or an identity. Excluded topologies raise
:class:`RecordRefusal` with a reason code instead of returning an approximate surface.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

SAMPLER_VERSION = "record-v2.0"
DESCRIPTOR_VERSION = "desc-v1.0"
N_S_MIN, N_PHI_MIN = 65, 61

# Typed refusal reasons (contract §9).
R_PORTS = "has_ports"                    # multi-entry / mid-wall openings (MEH)
R_CAD = "cad_body"                       # CAD STEP bodies (multicell, plughorn)
R_ZERO_MERIDIAN = "zero_length_meridian"
R_NONMONOTONE_PHI = "nonmonotone_azimuth"
R_BAD_INPUT = "bad_input"
R_UNSUPPORTED_ROUTE = "unsupported_route"


class RecordRefusal(ValueError):
    """The geometry cannot be faithfully described by a single-sheet record."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class SurfaceRecord:
    inner: np.ndarray                    # (n_phi, n_s, 3) mm
    arc_length_mm: np.ndarray            # (n_phi, n_s) cumulative wall length per meridian
    route: str                           # how the native points were produced
    wall_thickness_mm: float | None = None
    meta: dict = field(default_factory=dict)
    sampler_version: str = SAMPLER_VERSION

    @property
    def n_phi(self) -> int:
        return int(self.inner.shape[0])

    @property
    def n_s(self) -> int:
        return int(self.inner.shape[1])

    def digest(self) -> str:
        """sha256 of the record geometry (float64, little-endian, C order) plus its shape and
        sampler version. The proposed provenance gate (senior review §4.2) compares records
        within a tolerance; equal digests are the fast path."""
        h = hashlib.sha256()
        h.update(f"{self.sampler_version}|{self.inner.shape}".encode())
        h.update(np.ascontiguousarray(self.inner, dtype="<f8").tobytes())
        return h.hexdigest()

    def max_deviation_mm(self, other: "SurfaceRecord") -> float:
        if self.inner.shape != other.inner.shape:
            raise ValueError(f"record shapes differ: {self.inner.shape} vs {other.inner.shape}")
        return float(np.max(np.linalg.norm(self.inner - other.inner, axis=-1)))


# --------------------------------------------------------------------------- sampling

def _resample_meridian(mer: np.ndarray, t: np.ndarray) -> tuple[np.ndarray, float]:
    seg = np.linalg.norm(np.diff(mer, axis=0), axis=1)
    arc = np.r_[0.0, np.cumsum(seg)]
    total = float(arc[-1])
    if not math.isfinite(total) or total <= 0.0:
        raise RecordRefusal(R_ZERO_MERIDIAN, "a meridian has zero or non-finite length")
    u = arc / total
    keep = np.r_[True, np.diff(u) > 1e-12]
    out = np.stack([np.interp(t, u[keep], mer[keep, k]) for k in range(3)], axis=-1)
    return out, total


def sample_record(points, *, n_phi: int = N_PHI_MIN, n_s: int = N_S_MIN, route: str = "points",
                  wall_thickness_mm: float | None = None, meta: dict | None = None) -> SurfaceRecord:
    """Resample native inner-wall points ``(n_meridians, n_points, 3)`` (mm) to the contract
    grid. Raises :class:`RecordRefusal` rather than emitting a wrong surface."""
    a = np.asarray(points, dtype=float)
    if a.ndim != 3 or a.shape[2] != 3 or a.shape[0] < 2 or a.shape[1] < 2:
        raise RecordRefusal(R_BAD_INPUT, f"expected (n_meridians>=2, n_points>=2, 3), got {a.shape}")
    if not np.all(np.isfinite(a)):
        raise RecordRefusal(R_BAD_INPUT, "non-finite coordinates")
    if n_s < N_S_MIN or n_phi < 2:
        raise ValueError(f"n_s must be >= {N_S_MIN} and n_phi >= 2")
    t = np.linspace(0.0, 1.0, n_s)
    mer, lengths = [], []
    for m in a:
        r, L = _resample_meridian(m, t)
        mer.append(r)
        lengths.append(L)
    b = np.asarray(mer)                                   # (n_mer, n_s, 3)
    out = np.empty((n_phi, n_s, 3))
    arc = np.empty((n_phi, n_s))
    Ls = np.asarray(lengths)
    for j in range(n_s):
        ph = np.unwrap(np.arctan2(b[:, j, 1], b[:, j, 0]))
        if j == 0 and np.allclose(b[:, j, :2], 0.0):
            ph = np.unwrap(np.arctan2(b[:, 1, 1], b[:, 1, 0]))   # degenerate point throat
        if np.any(np.diff(ph) < -1e-8):
            raise RecordRefusal(R_NONMONOTONE_PHI, f"station {j}: azimuth not monotone")
        phi = np.linspace(ph[0], ph[-1], n_phi)
        for k in range(3):
            out[:, j, k] = np.interp(phi, ph, b[:, j, k])
        if j == 0:
            Lphi = np.interp(phi, ph, Ls)
    arc[:] = Lphi[:, None] * t[None, :]
    return SurfaceRecord(inner=out, arc_length_mm=arc, route=route,
                         wall_thickness_mm=None if wall_thickness_mm is None else float(wall_thickness_mm),
                         meta=dict(meta or {}))


# --------------------------------------------------------------------------- routes

def native_points(design, cfg, *, res_mm: float = 10.0):
    """Inner (and outer, if any) native points for a design, from the same code paths the
    mesher uses, without meshing. Returns ``(inner, outer|None, route, wall_mm)``."""
    import pathlib

    from ..config import mesh_spec
    from ..design import families

    params = design.params if isinstance(design.params, dict) else {}
    if params.get("cad") or params.get("step_path") or design.family in ("CAD", "STEP"):
        raise RecordRefusal(R_CAD, "CAD bodies take their own route (contract §9)")
    if params.get("meh") or params.get("mid_ports"):
        raise RecordRefusal(R_PORTS, "multi-entry / ported walls are not a single sheet")
    if "grid" in params:
        # Same resolution as mesh/build.py::_build_grid_mesh, so the record is what gets meshed.
        from ..design.generators import grid
        from ..design.generators import (klangfilm_lame_family, klangfilm_lame_hv_core_family,
                                         klangfilm_lame_hv_family, lecleach_swept_hv,
                                         record_body, rolled_family)
        b = params["grid"]
        brief = getattr(cfg, "brief", None) or {}
        t = float(b.get("wall_thickness_mm", 3.0))
        for family in (rolled_family, klangfilm_lame_family, klangfilm_lame_hv_family,
                       klangfilm_lame_hv_core_family, lecleach_swept_hv, record_body):
            if family.is_family_spec(b):
                g = family.resolve_grid(b, brief)
                outer = g.get("outer_points")
                return (np.asarray(g["inner_points"], float),
                        None if outer is None else np.asarray(outer, float),
                        family.__name__.rsplit(".", 1)[-1], float(g.get("wall_thickness_mm", t)))
        knobs = b.get("knobs") or {}
        if "rows" in b:
            spec = {k: v for k, v in b.items() if k != "knobs"}
            inner, _ = grid.rows_grid_points(spec, knobs, brief)
            route = "grid_rows"
        else:
            spec = {k: b[k] for k in grid.GRID_SPEC_KEYS if k in b}
            inner, _ = grid.grid_points(spec, knobs, brief)
            route = "grid"
        inner = np.asarray(inner, float)
        return inner, grid.grid_outer_points(inner, t), route, t
    from hornlab_mesher.config_builder import resolve_geometry
    msp = mesh_spec("screen", cfg)
    mcfg = families.to_mesher_config(design, msp, {"throat": res_mm, "mouth": res_mm, "rear": res_mm},
                                     pathlib.Path("<record>"), mounting=getattr(cfg, "mounting", None))
    mcfg["mesh"].update({"throat_res_mm": res_mm, "mouth_res_mm": res_mm, "rear_res_mm": res_mm,
                         "allow_large_mesh": True})
    rg = resolve_geometry(mcfg, allow_large_mesh=True)
    outer = getattr(rg.geometry, "outer_points", None)
    wall = params.get("wall_thickness_mm")
    return (np.asarray(rg.geometry.inner_points, float),
            None if outer is None else np.asarray(outer, float), "native",
            None if wall is None else float(wall))


def record_for_design(design, cfg, *, n_phi: int = N_PHI_MIN, n_s: int = N_S_MIN) -> SurfaceRecord:
    """The contract-v2 record of one design (no mesh)."""
    inner, _outer, route, wall = native_points(design, cfg)
    meta = {"design_hash": design.hash(), "family": design.family,
            "brief": (getattr(cfg, "brief", None) or {}).get("name")}
    return sample_record(inner, n_phi=n_phi, n_s=n_s, route=route, wall_thickness_mm=wall, meta=meta)


# --------------------------------------------------------------------------- descriptors

def _plane(rec: SurfaceRecord, phi_frac: float) -> np.ndarray:
    i = int(round(phi_frac * (rec.n_phi - 1)))
    return rec.inner[i]


def descriptors(rec: SurfaceRecord, *, n_curve: int = 32) -> dict:
    """Contract §7 minimum set, from the record alone (mm and degrees; one modelled quarter is
    assumed, with phi 0 = H wall and the last azimuth = V wall)."""
    s_idx = np.linspace(0, rec.n_s - 1, n_curve)
    out: dict = {"descriptor_version": DESCRIPTOR_VERSION}
    for name, frac in (("h", 0.0), ("diag", 0.5), ("v", 1.0)):
        mer = _plane(rec, frac)
        r = np.hypot(mer[:, 0], mer[:, 1])
        z = mer[:, 2]
        dz, dr = np.gradient(z), np.gradient(r)
        ang = np.degrees(np.arctan2(dr, dz))               # wall half-angle from the axis
        out[f"{name}_halfwidth_mm"] = np.interp(s_idx, np.arange(rec.n_s), r)
        out[f"{name}_z_mm"] = np.interp(s_idx, np.arange(rec.n_s), z)
        out[f"{name}_wall_angle_deg"] = np.interp(s_idx, np.arange(rec.n_s), ang)
    # sections: quarter outline (x(phi), y(phi)) at each station -> area by the shoelace rule
    x, y = rec.inner[:, :, 0], rec.inner[:, :, 1]
    area_q = 0.5 * np.abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1], axis=0))   # (n_s,)
    width, height = x[0], y[-1]                                             # half extents
    area = 4.0 * area_q
    with np.errstate(divide="ignore", invalid="ignore"):
        aspect = np.where(height > 0, width / height, np.nan)
        shape_index = np.where((width > 0) & (height > 0), area / (4.0 * width * height), np.nan)
    out["area_mm2"] = np.interp(s_idx, np.arange(rec.n_s), area)
    out["aspect"] = np.interp(s_idx, np.arange(rec.n_s), aspect)
    out["shape_index"] = np.interp(s_idx, np.arange(rec.n_s), shape_index)
    out["mouth_width_mm"] = float(2.0 * np.max(np.abs(rec.inner[:, :, 0])))
    out["mouth_height_mm"] = float(2.0 * np.max(np.abs(rec.inner[:, :, 1])))
    out["depth_mm"] = float(np.max(rec.inner[:, :, 2]) - np.min(rec.inner[:, :, 2]))
    out["rollback"] = bool(np.any(np.diff(rec.inner[:, :, 2], axis=1) < -1e-9))
    return out


def envelope_margins(rec: SurfaceRecord, envelope_mm: dict, *, include_wall: bool = True) -> dict:
    """Signed margins (mm, positive = inside) of the record against a brief envelope
    ``{width_mm, height_mm, depth_mm}``. ``include_wall`` adds the record's wall thickness on
    each side (a build-box view); the stored ``bbox_m`` convention is the owner's open decision
    (senior review §4.2), so both views are available."""
    d = descriptors(rec)
    t = (rec.wall_thickness_mm or 0.0) if include_wall else 0.0
    out = {}
    for key, size in (("width_mm", d["mouth_width_mm"] + 2 * t),
                      ("height_mm", d["mouth_height_mm"] + 2 * t),
                      ("depth_mm", d["depth_mm"])):
        lim = envelope_mm.get(key)
        out[key] = None if lim is None else float(lim) - float(size)
    return out


__all__ = ["SAMPLER_VERSION", "DESCRIPTOR_VERSION", "SurfaceRecord", "RecordRefusal",
           "sample_record", "native_points", "record_for_design", "descriptors",
           "envelope_margins", "R_PORTS", "R_CAD", "R_ZERO_MERIDIAN", "R_NONMONOTONE_PHI",
           "R_BAD_INPUT", "R_UNSUPPORTED_ROUTE"]
