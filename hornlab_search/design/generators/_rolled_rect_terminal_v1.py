"""H-only terminal roll-onset / C-return law for the rolled rectangular body (v1).

New versioned kernel: the frozen parent and the existing CD wall-angle kernel are untouched.
The law rewrites only the H meridian's terminal section (forward station to lip) as an explicit
C-shaped return, and blends that deformation across azimuth with a band-limited smoothstep that is exactly zero at
and beyond 40 deg from H, so the V cut (and the whole V-side strip) is bit-identical and the
throat/pre-roll are untouched.

Control points on the parent H row (``half`` = parent H half-width, ``z_f`` = parent forward z)::

    P0 = (x_f, z_f)                                   forward / roll-on, parent tangent
    P1 = (half, z_f - max_drop)                       maximum width (still 500 mm)
    P2 = (roll_frac*half, z_f - roll_drop)            visible roll onset
    P3 = (lip_frac*half, z_f - lip_drop)              returned lip (C)

A piecewise cubic Hermite through P0..P3 uses the parent tangent at P0, a vertical tangent at P1
(tangent-continuous max), the P3-P1 direction at P2, and a selectable lip angle at P3.  Neutral
(``tm_roll_frac == 0``) is an exact no-op.

Label: LABELED HYPOTHESIS - no published name.  This is a local mouth-termination shape law, not a
parent or CD-kernel edit.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = "rolled-rect-terminal-v1"
TM_KEYS = frozenset({
    "tm_roll_frac", "tm_lip_frac", "tm_max_drop_mm", "tm_roll_drop_mm",
    "tm_lip_drop_mm", "tm_lip_angle_deg",
})
MAX_FRAC = 0.98
MAX_DROP_MM = 120.0
MIN_LIP_ANGLE = 100.0
MAX_LIP_ANGLE = 220.0
#: Azimuthal concentration of the H-side law (1 at H, exactly 0 at V).
#: Rows at or above this azimuth are left untouched (keeps the V symmetry plane exact).
AZI_ZERO_DEG = 40.0


def is_neutral(tm):
    return float(tm["tm_roll_frac"]) == 0.0


def validate_tm(tm):
    if not isinstance(tm, dict) or set(tm) != TM_KEYS:
        raise ValueError(f"terminal keys: expected {sorted(TM_KEYS)}")
    for key, value in tm.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    roll, lip = float(tm["tm_roll_frac"]), float(tm["tm_lip_frac"])
    if not 0.0 <= roll <= MAX_FRAC:
        raise ValueError(f"tm_roll_frac must be in [0,{MAX_FRAC:g}] (0 = neutral)")
    if roll == 0.0:
        return
    if not 0.5 <= lip < roll:
        raise ValueError("need 0.5 <= tm_lip_frac < tm_roll_frac")
    mx, rd, ld = (float(tm[k]) for k in ("tm_max_drop_mm", "tm_roll_drop_mm", "tm_lip_drop_mm"))
    if not 0.0 <= mx < rd < ld <= MAX_DROP_MM:
        raise ValueError("need 0 <= max_drop < roll_drop < lip_drop <= 120 mm")
    angle = float(tm["tm_lip_angle_deg"])
    if not MIN_LIP_ANGLE <= angle <= MAX_LIP_ANGLE:
        raise ValueError(f"tm_lip_angle_deg must be in [{MIN_LIP_ANGLE:g},{MAX_LIP_ANGLE:g}]")


def _hermite(p0, p1, t0, t1, n):
    length = float(np.linalg.norm(p1 - p0))
    m0, m1 = t0 * length, t1 * length
    t = np.linspace(0.0, 1.0, n)
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    return (np.outer(h00, p0) + np.outer(h10, m0)
            + np.outer(h01, p1) + np.outer(h11, m1))


def _terminal_curve(x, z, forward, tm):
    half = float(np.max(x))
    zf = float(z[forward])
    roll = float(tm["tm_roll_frac"])
    lip = float(tm["tm_lip_frac"])
    p0 = np.array([float(x[forward]), zf])
    p1 = np.array([half, zf - float(tm["tm_max_drop_mm"])])
    p2 = np.array([roll * half, zf - float(tm["tm_roll_drop_mm"])])
    p3 = np.array([lip * half, zf - float(tm["tm_lip_drop_mm"])])
    t0 = np.array([x[forward + 1] - x[forward], z[forward + 1] - z[forward]], dtype=float)
    t0 /= np.linalg.norm(t0)
    # Keep the parent tangent at the roll-on so the junction is C1; the monotone z clamp
    # removes the sub-millimetre Hermite hump downstream.
    t1 = np.array([0.0, -1.0])
    t2 = p3 - p1
    t2 /= np.linalg.norm(t2)
    angle = math.radians(float(tm["tm_lip_angle_deg"]))
    t3 = np.array([math.cos(angle), math.sin(angle)])
    chords = [float(np.linalg.norm(p1 - p0)), float(np.linalg.norm(p2 - p1)),
              float(np.linalg.norm(p3 - p2))]
    count = len(x) - forward
    if count < 6:
        raise ValueError("terminal has too few stations for the C law")
    total = sum(chords)
    n1 = max(2, int(round(count * chords[0] / total)))
    n3 = max(2, int(round(count * chords[2] / total)))
    n2 = count - n1 - n3 - 1
    if n2 < 2:
        n2 = 2
        n1 -= 1
    curve = np.vstack([
        _hermite(p0, p1, t0, t1, n1 + 1),
        _hermite(p1, p2, t1, t2, n2 + 1)[1:],
        _hermite(p2, p3, t2, t3, n3 + 1)[1:],
    ])
    if curve.shape[0] != count:
        raise ValueError("terminal sampling did not match the station count")
    curve[:, 0] = np.minimum(curve[:, 0], half)
    # Enforce a non-increasing axial station so the C cannot fold back through the surface.
    curve[:, 1] = np.minimum.accumulate(curve[:, 1])
    curve[0] = p0
    curve[-1] = p3
    # Keep the returned lip non-increasing in z (a sub-0.01 mm upward hook from the Hermite
    # endpoint tangent is not worth a surface fold).
    curve[-1, 1] = min(curve[-1, 1], curve[-2, 1])
    return curve, {"max_x_mm": half, "max_z_mm": zf - float(tm["tm_max_drop_mm"]),
                   "roll_x_mm": roll * half, "roll_z_mm": zf - float(tm["tm_roll_drop_mm"]),
                   "lip_x_mm": lip * half, "lip_z_mm": zf - float(tm["tm_lip_drop_mm"])}


def apply_to_inner(inner, tm):
    """Return the H-terminal-deformed inner grid; neutral returns the same array."""
    if is_neutral(tm):
        return inner
    validate_tm(tm)
    pts = np.asarray(inner, dtype=float)
    out = pts.copy()
    hrow = pts[0]
    x, z = hrow[:, 0], hrow[:, 2]
    forward = int(np.argmax(z))
    curve, report = _terminal_curve(x, z, forward, tm)
    half = report["max_x_mm"]
    zf = float(z[forward])
    hz = z[forward:]
    phis = np.linspace(0.0, 0.5 * math.pi, pts.shape[0])
    c0 = math.cos(math.radians(AZI_ZERO_DEG))
    for row in range(pts.shape[0]):
        cos_phi = math.cos(float(phis[row]))
        if cos_phi <= c0:
            weight = 0.0
        else:
            tau = (cos_phi - c0) / (1.0 - c0)
            weight = tau * tau * tau * (10.0 - 15.0 * tau + 6.0 * tau * tau)
        if weight == 0.0:
            continue
        rho = np.hypot(pts[row, :, 0], pts[row, :, 1])
        row_max = float(np.max(rho))
        target = row_max * curve[:, 0] / half
        rho_new = rho.copy()
        z_new = pts[row, :, 2].copy()
        rho_new[forward:] = rho[forward:] + weight * (target - rho[forward:])
        z_new[forward:] = z[forward:] + weight * (curve[:, 1] - hz)
        cos_f, sin_f = math.cos(float(phis[row])), math.sin(float(phis[row]))
        out[row, forward:, 0] = rho_new[forward:] * cos_f
        out[row, forward:, 1] = rho_new[forward:] * sin_f
        out[row, forward:, 2] = z_new[forward:]
    out[0, :, 1] = 0.0
    if not np.isfinite(out).all():
        raise ValueError("nonfinite terminal surface")
    if np.any(np.hypot(out[..., 0], out[..., 1]) <= 0):
        raise ValueError("terminal law reaches the horn centreline")
    if np.max(np.abs(out[..., 0])) > half + 1e-6:
        raise ValueError("terminal law exceeds the H half-width")
    return out


def diagnostics(inner, tm):
    if is_neutral(tm):
        return {"neutral": True}
    validate_tm(tm)
    pts = np.asarray(inner, dtype=float)
    x, z = pts[0, :, 0], pts[0, :, 2]
    forward = int(np.argmax(z))
    _curve, report = _terminal_curve(x, z, forward, tm)
    return {"neutral": False, **report}
