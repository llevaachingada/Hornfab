"""Versioned CD wall-angle kernel for the rolled rectangular body (LABELED HYPOTHESIS).

Construction: windowed flare-timing wall-angle schedule applied to the *pre-roll* part of
each azimuth row.  The parent surface is never re-derived here; the caller passes the
already-resolved v1 family inner sheet and this module moves it along each row's normal by
an offset whose derivative is the prescribed wall-angle change.  Neutral amplitudes
(``cd_h_deg == cd_v_deg == 0``) are a pure no-op.

Geometry, for one row with pre-roll arc length ``L`` and arc fraction ``u = s / L``::

    B(u)   = S((u-a)/(b-a)) * S((c-u)/(c-b))           S = v1 quintic smoothstep
    B'(u)  = S'((u-a)/(b-a))/(b-a) * S((c-u)/(c-b))
             - S((u-a)/(b-a)) * S'(c-u)/(c-b))/(c-b)    S'(x) = 30 x^2 (1-x)^2
    A      = radians(cd_h_deg * cos^2 psi_f + cd_v_deg * sin^2 psi_f)
    delta  = A * B'(u) / max|B'|                        [rad] exact first-order angle change
    n      = A * L / max|B'| * B(u)                     [mm] normal offset

``B`` and ``B'`` vanish outside ``(a, c)``, so the throat, the roll-on (mouth) station and
every station at/after ``c`` are unchanged.  ``int delta ds = 0``: the law redistributes
where the flare happens; it does not change the mouth radius or the depth.

No published name is claimed.  Docs: docs/research/typologies/ROLLED_CD_WALL_ANGLE_RESEARCH_2026-11-20.md
"""
from __future__ import annotations

import math

import numpy as np

from . import _rolled_rect_v1 as v1

SCHEMA = "rolled-rect-cd-v1"
CD_KEYS = frozenset({"cd_h_deg", "cd_v_deg", "cd_start_s", "cd_peak_s", "cd_end_s"})
MAX_CD_H_DEG = 20.0
MAX_CD_V_DEG = 20.0
WINDOW_LIMITS = (0.10, 0.55, 0.94)   # start >= lo, peak in (lo, hi), end <= hi


def smoothstep_prime(x):
    """Derivative of the clamped quintic smoothstep; exactly zero outside [0, 1]."""
    v = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    inside = (x > 0.0) & (x < 1.0)
    return np.where(inside, 30.0 * v * v * (1.0 - v) * (1.0 - v), 0.0)


def window(u, start, peak, end):
    """C2 bump and its derivative with respect to ``u``; zero outside (start, end)."""
    u = np.asarray(u, dtype=float)
    p = (u - start) / (peak - start)
    q = (end - u) / (end - peak)
    b = v1.smoothstep(p) * v1.smoothstep(q)
    bp = (smoothstep_prime(p) * v1.smoothstep(q) / (peak - start)
          - v1.smoothstep(p) * smoothstep_prime(q) / (end - peak))
    return b, bp


def validate_cd(shape):
    """Validate only the CD keys; the parent shape is validated by the family adapter."""
    for key in CD_KEYS:
        if key not in shape:
            raise ValueError(f"missing CD key {key}")
        value = shape[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    if abs(shape["cd_h_deg"]) > MAX_CD_H_DEG:
        raise ValueError(f"cd_h_deg must be in [-{MAX_CD_H_DEG:g}, {MAX_CD_H_DEG:g}]")
    if abs(shape["cd_v_deg"]) > MAX_CD_V_DEG:
        raise ValueError(f"cd_v_deg must be in [-{MAX_CD_V_DEG:g}, {MAX_CD_V_DEG:g}]")
    start, peak, end = (float(shape[k]) for k in ("cd_start_s", "cd_peak_s", "cd_end_s"))
    lo, hi = WINDOW_LIMITS[0], WINDOW_LIMITS[2]
    if not (lo <= start < peak < end <= hi):
        raise ValueError(f"need {lo} <= cd_start_s < cd_peak_s < cd_end_s <= {hi}")


def is_neutral(shape):
    """True when both amplitudes are exactly zero (the additive no-op)."""
    return float(shape["cd_h_deg"]) == 0.0 and float(shape["cd_v_deg"]) == 0.0


def diagnostics(inner, shape):
    """JSON-safe report: pre-roll arc and peak normal offset per axis (best-effort)."""
    if is_neutral(shape):
        return {"neutral": True}
    validate_cd(shape)
    start, peak, end = (float(shape[k]) for k in ("cd_start_s", "cd_peak_s", "cd_end_s"))
    report = {"neutral": False, "window": [start, peak, end]}
    for label, row in (("h", 0), ("v", -1)):
        f, _rho, _z, length, u = _row_pre_roll(np.asarray(inner, dtype=float)[row])
        b, bp = window(u, start, peak, end)
        max_bp = float(np.max(np.abs(bp)))
        amp = math.radians(float(shape["cd_%s_deg" % label]))
        report[label] = {"pre_roll_mm": length,
                         "peak_offset_mm": (abs(amp) * length / max_bp if max_bp else 0.0)}
    return report


def _row_pre_roll(points):
    """Return ``(f, rho, z, L, u)`` for one row's pre-roll (throat to the forward station)."""
    rho = np.hypot(points[:, 0], points[:, 1])
    z = points[:, 2]
    f = int(np.argmax(z))
    if f < 2:
        raise ValueError("row has no measurable pre-roll")
    dz = np.diff(z[:f + 1])
    dr = np.diff(rho[:f + 1])
    ds = np.hypot(dz, dr)
    length = float(np.sum(ds))
    if length <= 0.0:
        raise ValueError("degenerate pre-roll arc length")
    u = np.r_[0.0, np.cumsum(ds)] / length
    return f, rho, z, length, u


def apply_to_inner(inner, shape):
    """Return a displaced copy of ``inner``; a no-op (same array) when both amplitudes are 0."""
    dh = float(shape["cd_h_deg"])
    dv = float(shape["cd_v_deg"])
    if dh == 0.0 and dv == 0.0:
        return inner
    validate_cd(shape)
    start, peak, end = (float(shape[k]) for k in ("cd_start_s", "cd_peak_s", "cd_end_s"))
    inner = np.asarray(inner, dtype=float)
    out = inner.copy()
    h = inner[0, :, 0]
    v = inner[-1, :, 1]
    for row in range(inner.shape[0]):
        f, rho, z, length, u = _row_pre_roll(inner[row])
        b, bp = window(u, start, peak, end)
        max_bp = float(np.max(np.abs(bp)))
        if max_bp <= 0.0:
            continue
        psi = math.atan2(inner[row, f, 1] / v[f], inner[row, f, 0] / h[f])
        amp = math.radians(dh * math.cos(psi) ** 2 + dv * math.sin(psi) ** 2)
        offset = amp * length / max_bp * b
        # Unit normal in (z, rho); the tangent is (dz/ds, drho/ds).
        s = u * length
        tz = np.gradient(z[:f + 1], s)
        tr = np.gradient(rho[:f + 1], s)
        norm = np.hypot(tz, tr)
        if np.any(norm <= 0.0):
            raise ValueError("degenerate pre-roll tangent")
        nz, nr = -tr / norm, tz / norm
        z_new = z[:f + 1] + offset * nz
        rho_new = rho[:f + 1] + offset * nr
        if np.any(rho_new <= 0.0):
            raise ValueError("CD offset crosses the horn centreline")
        scale = rho_new / rho[:f + 1]
        out[row, :f + 1, 0] = inner[row, :f + 1, 0] * scale
        out[row, :f + 1, 1] = inner[row, :f + 1, 1] * scale
        out[row, :f + 1, 2] = z_new
        if not np.all(np.diff(z_new) > 0.0):
            raise ValueError("CD offset reverses the pre-roll axial station order")
        if int(np.argmax(out[row, :, 2])) != f:
            raise ValueError("CD offset moves the roll-on (forward) station")
        if np.any(np.diff(rho_new) < -1e-6):
            raise ValueError("CD offset creates a constriction before the mouth roll")
        if np.any(np.abs(offset[u >= end]) > 1e-12):
            raise ValueError("CD offset leaks past the window end")
    if not np.isfinite(out).all():
        raise ValueError("nonfinite CD surface")
    return out
