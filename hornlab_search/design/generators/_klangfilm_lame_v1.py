"""Klangfilm-Lame horn: 2018 Klangfilm spherical-wave parent + Lame section + rollback-aware GRID geometry.

``rows.type: klangfilm_lame``. Derived family (schema ``klangfilm-lame-v1``); the frozen 2018 port in
``klangfilm_ellipse.py`` is untouched. NOT an exact reproduction of Ahlswede's unpublished 2019 calculator.

Construction
* Parent (published, Kolbrek 2007 / Ahlswede 2018): ``R0 = c/(pi fc)``, cap height ``h``, target curved area
  ``S(h) = 2 pi R0 h``, wall ``y = sqrt(2 R0 h - h^2)``, ``z = ln(h/h0)/m - h + h0``.
* Section at each parent station: Lame outline ``|x/a|^p + |y/b|^p = 1`` with ``a = q b`` and one scalar ``b``
  solved so the superellipsoid cap (``lame_cap``) has area ``S(h)`` (``area_mode = curved_cap_ratio_locked``);
  section semi-axes are ``a sin(th)``, ``b sin(th)``, ``th = acos(1 - h/R0)``.
* ``q(s)`` and ``p(s)`` follow ONE C2 quintic gate from (1, 2) at the round driver plane to (aspect, lame_p) at
  ``morph_frac`` of the pre-shoulder parent arc length, then hold (``lame_tail_mode = hold_after_shoulder``).
  No fractional-power ramp (its slope diverges at the throat).
* Optional ``rim_sweep_ratio`` = D_edge / A: H-side setback ``-D_edge cos^2(phi) W(s)`` with a C2 gate W.
* Optional ``source_blend_ratio`` (= L_b / 2 y0, default 0 = OFF) with ``entry_half_angle_deg``: C2 local
  wall-tangent splice (per axis) that is a CAD entrance experiment, NOT an HF1440 adapter. Not searched.

Throat provenance: ``brief.driver.exit_angle_deg`` (2 deg) is a simulation assumption, not an HF1440 datasheet
value; the raw wall half-angle here is derived (10.617 deg at fc 560 Hz, r 18 mm). Nothing forces 2 deg.
"""
from __future__ import annotations

import math

import numpy as np

from . import _lame_cap_v1 as lame_cap

SCHEMA = "klangfilm-lame-v1"
SHAPE_KEYS = frozenset({"fc_hz", "aspect", "lame_p", "end_frac", "rim_sweep_ratio", "morph_frac",
                        "source_blend_ratio", "entry_half_angle_deg", "wall_thickness_mm", "n_phi", "n_s"})
C_AIR = 343.0
_ORDER = 24
_NDENSE = 160
_BOUNDS = {"fc_hz": (150.0, 3000.0), "aspect": (1.0, 4.0), "lame_p": (2.0, 8.0), "end_frac": (0.3, 1.9),
           "rim_sweep_ratio": (-0.6, 0.6), "morph_frac": (0.05, 0.9), "source_blend_ratio": (0.0, 2.0),
           "entry_half_angle_deg": (0.0, 20.0)}


def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f"shape keys: missing={sorted(SHAPE_KEYS - set(shape))}, unknown={sorted(set(shape) - SHAPE_KEYS)}")
    for key, (lo, hi) in _BOUNDS.items():
        v = shape[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{key} must be a finite number")
        if not lo <= v <= hi:
            raise ValueError(f"{key} must be in [{lo}, {hi}]")
    if shape["wall_thickness_mm"] <= 0:
        raise ValueError("wall_thickness_mm must be positive")
    for key, minimum in (("n_phi", 7), ("n_s", 24)):
        if int(shape[key]) != shape[key] or shape[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")


# ---------------------------------------------------------------- analytic throat (parent)
def parent_constants(fc_hz, y0_mm, c_mm_s=C_AIR * 1000.0):
    R = c_mm_s / (math.pi * fc_hz)
    if not 0 < y0_mm < R:
        raise ValueError(f"throat radius {y0_mm} mm must be below R0 {R:.1f} mm (lower fc_hz)")
    h0 = y0_mm * y0_mm / (R + math.sqrt(R * R - y0_mm * y0_mm))
    return R, h0, 4.0 / R


def parent_wall_halfangle_deg(fc_hz, y0_mm, c_mm_s=C_AIR * 1000.0):
    """Analytic wall half-angle of the raw parent at the throat (10.617223 deg for 560 Hz, 18 mm)."""
    R, h0, m = parent_constants(fc_hz, y0_mm, c_mm_s)
    return math.degrees(math.atan(((R - h0) / y0_mm) / (1.0 / (m * h0) - 1.0)))


# ---------------------------------------------------------------- dense station table
def _stations(shape, y0_mm):
    fc, q_ap, p_ap = float(shape["fc_hz"]), float(shape["aspect"]), float(shape["lame_p"])
    R, h0, m = parent_constants(fc, y0_mm)
    h_end = float(shape["end_frac"]) * R
    if h_end <= h0 * 1.01:
        raise ValueError("end_frac too small: termination at/below the throat cap height")
    hs = np.unique(np.concatenate((np.geomspace(h0, h_end, _NDENSE), np.linspace(h0, h_end, _NDENSE))))
    hs = hs[np.concatenate(([True], np.diff(hs) > 1e-6 * h0))]          # drop near-duplicates (z must stay strictly monotone)
    z = np.log(hs / h0) / m - hs + h0
    y = np.sqrt(np.maximum(2 * R * hs - hs * hs, 0.0))
    arc = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(z), np.diff(y)))))
    ap = h_end if h_end < R else R
    s_ap = float(np.interp(ap, hs, arc))
    t = arc / (float(shape["morph_frac"]) * s_ap)
    g = lame_cap.quintic(t)
    q = np.exp(math.log(q_ap) * g)
    p = 2.0 + (p_ap - 2.0) * g
    th = np.arccos(np.clip(1.0 - hs / R, -1, 1))
    a = np.empty_like(hs)
    b = np.empty_like(hs)
    resid = np.zeros_like(hs)
    for i, h in enumerate(hs):
        target = 2 * math.pi * R * h
        if g[i] <= 0.0:                                    # exact round parent, no solve
            a[i] = b[i] = R
        else:
            a[i], b[i] = lame_cap.area_locked_axes(target, q[i], R, h, p[i], _ORDER)
            resid[i] = abs(lame_cap.lame_cap_area(a[i], b[i], R, h, p[i], _ORDER) / target - 1.0)
    st = np.sin(th)
    return {"z": z, "a": a * st, "b": b * st, "p": p, "q": q, "h": hs, "arc": arc, "s_ap": s_ap, "R": R,
            "cap_area_resid": resid}


def _blend(z, r, tan_target, Lb):
    """C2 local tangent splice (per axis): r + k z (1 - Q(z/Lb)), k = tan(target) - r'(0)."""
    if Lb <= 0:
        return r
    dr0 = (r[1] - r[0]) / (z[1] - z[0])
    k = tan_target - dr0
    out = r + k * z * (1.0 - lame_cap.quintic(z / Lb))           # zero for z >= Lb
    turn = int(np.argmax(z))
    out[turn + 1:] = r[turn + 1:]                                # rollback branch (z falls back below Lb) untouched
    return out


def profile(shape, y0_mm):
    """Dense table dict, with the optional (default OFF) source blend applied to both axes."""
    tab = _stations(shape, y0_mm)
    Lb = float(shape["source_blend_ratio"]) * 2.0 * y0_mm
    if Lb > 0:
        zz = tab["z"]
        turn = int(np.argmax(zz))
        if zz[turn] < Lb * 1.05 or not np.all(np.diff(zz[: turn + 1]) > 0):
            raise ValueError("source blend length exceeds the forward-going part of the horn")
        tn = math.tan(math.radians(float(shape["entry_half_angle_deg"])))
        tab["a"] = _blend(tab["z"], tab["a"], tn, Lb)
        tab["b"] = _blend(tab["z"], tab["b"], tn, Lb)
        tab["blend_mm"] = Lb
    tab["a"][0] = tab["b"][0] = y0_mm
    return tab


def make_grid(shape, brief):
    """Quarter model (n_phi, n_s + 1, 3): Lame sections on the fixed-ray azimuth, arc-length resampled."""
    validate_shape(shape)
    y0 = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    tab = profile(shape, y0)
    rm = 0.5 * (tab["a"] + tab["b"])
    arc = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(tab["z"]), np.diff(rm)))))
    n = int(shape["n_s"]) + 1
    t = np.linspace(0.0, arc[-1], n)
    z = np.interp(t, arc, tab["z"])
    a = np.interp(t, arc, tab["a"])
    b = np.interp(t, arc, tab["b"])
    p = np.interp(t, arc, tab["p"])
    phis = np.linspace(0.0, math.pi / 2.0, int(shape["n_phi"]))
    # sweep gate: C2 over the pre-shoulder arc, then held through the rollback
    s_ap_t = float(np.interp(tab["s_ap"], arc, arc))
    W = lame_cap.quintic(t / max(s_ap_t, 1e-9))
    D_edge = float(shape["rim_sweep_ratio"]) * float(a.max())
    pts = np.zeros((len(phis), n, 3))
    for j in range(n):
        rho, _ = lame_cap.radial_lame(phis, max(a[j], 1e-9), max(b[j], 1e-9), max(p[j], 2.0))
        pts[:, j, 0] = rho * np.cos(phis)
        pts[:, j, 1] = rho * np.sin(phis)
        pts[:, j, 2] = z[j] - D_edge * np.cos(phis) ** 2 * W[j]
    pts[0, :, 1] = 0.0
    pts[-1, :, 0] = 0.0
    meta = {"quarter": True, "row_span": "quarter", "symmetry_plane": "yz+xz",
            "source_auto_angle_deg": a0, "angle_provenance": "assumed_legacy",
            "construction_label": SCHEMA + ": Klangfilm parent, Lame section, curved-cap area locked "
                                  "(superellipsoid_cap_v1; not Ahlswede 2019 exact)",
            "area_mode": "curved_cap_ratio_locked", "lame_tail_mode": "hold_after_shoulder",
            "r0_mm": tab["R"], "cap_area_resid_max": float(tab["cap_area_resid"].max()),
            "shape": dict(shape)}
    return pts, meta


# ---------------------------------------------------------------- diagnostics (report-only)
def diagnostics(shape, brief):
    """Throat/tangent/shape checks of the materialised point grid. Does NOT assert a driver angle."""
    pts, meta = make_grid(shape, brief)
    y0 = float(brief["driver"]["exit_radius_mm"])
    z0 = pts[0, :, 2]
    xh, yv = pts[0, :, 0], pts[-1, :, 1]
    dz = np.diff(z0)
    tab = profile(shape, y0)                                     # tangent from the dense table (chord error ~0)
    ang_h = math.degrees(math.atan((tab["a"][1] - tab["a"][0]) / (tab["z"][1] - tab["z"][0])))
    ang_v = math.degrees(math.atan((tab["b"][1] - tab["b"][0]) / (tab["z"][1] - tab["z"][0])))
    ring = np.hypot(pts[:, 0, 0], pts[:, 0, 1])
    return {
        "raw_parent_halfangle_deg": parent_wall_halfangle_deg(float(shape["fc_hz"]), y0),
        "wall_halfangle_h_deg": ang_h, "wall_halfangle_v_deg": ang_v,
        "throat_radius_spread_mm": float(ring.max() - ring.min()),
        "throat_radius_mm": float(ring.mean()),
        "min_radius_ratio_to_throat": float(min(np.hypot(pts[:, :, 0], pts[:, :, 1]).min(axis=0)[1:].min() / y0, 9e9)),
        "z_monotone_until_turn_pct": float(100.0 * np.mean(dz[: max(1, len(dz) // 4)] > 0)),
        "cap_area_resid_max": meta["cap_area_resid_max"],
        "max_width_mm": float(2 * np.abs(pts[:, :, 0]).max()), "max_height_mm": float(2 * np.abs(pts[:, :, 1]).max()),
        "depth_mm": float(pts[:, :, 2].max() - pts[:, :, 2].min()),
        "finite": bool(np.isfinite(pts).all()),
        "exit_angle_deg_is_assumption": True,
    }
