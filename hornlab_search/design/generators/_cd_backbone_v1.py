"""Versioned CD wall-angle backbone kernel for returned-lip parents (LABELED HYPOTHESIS).

No published name is claimed. Dossier:
docs/research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md

The parent surface is never re-derived here. The caller passes an already-resolved inner point grid
(rows = fixed azimuth, stations = throat -> forward/max-z station -> returned lip). For each row the
pre-roll part (throat to that row's forward station) is replaced by a blend of the parent row and a
CD backbone curve built from the wall-angle schedule (arc fraction ``u``)::

    theta_bb(u) = t0 + (theta_c - t0) S(u/lt) + (tf - theta_c) S((u - (1 - lr))/lr)
    X_new(u)    = (1 - lam) X_parent(u) + lam X_bb(u)          (positions at equal arc fraction)
    lam(psi)    = bb_h cos^2 psi + bb_v sin^2 psi

``S`` is the C2 quintic and ``t0``/``tf`` are the row's own wall angles at the throat and at the
forward station, so both curves share end points and end tangents. ``theta_c`` and the backbone arc
length are solved so ``X_bb`` lands exactly on the row's forward station. Because both curves advance
monotonically in z and radius, so does every convex blend. The throat station, the forward station,
every station after it (the return) and the rim are kept exactly; rows with ``lam <= 1e-12`` and
``bb_h == bb_v == 0`` are pure no-ops.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import fsolve

SCHEMA = "cd-backbone-v1"
BB_KEYS = frozenset({"bb_h", "bb_v", "bb_throat_frac", "bb_rollin_frac"})
LIMITS = {"bb_h": (0.0, 1.0), "bb_v": (0.0, 1.0),
          "bb_throat_frac": (0.05, 0.30), "bb_rollin_frac": (0.15, 0.45)}
MAX_BODY_SUM = 0.80          # throat transition + roll-in must leave a body
_N = 4001                    # integration samples per row
_TOL_MM = 1e-6
_LAM_EPS = 1e-12             # rows whose blend weight is below this are left bit-identical


def _S(x):
    x = np.clip(x, 0.0, 1.0)
    return x ** 3 * (10.0 - 15.0 * x + 6.0 * x * x)


def validate_bb(shape):
    for key in BB_KEYS:
        if key not in shape:
            raise ValueError(f"missing backbone key {key}")
        value = shape[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        lo, hi = LIMITS[key]
        if not lo <= float(value) <= hi:
            raise ValueError(f"{key} must be in [{lo:g}, {hi:g}]")
    if float(shape["bb_throat_frac"]) + float(shape["bb_rollin_frac"]) > MAX_BODY_SUM:
        raise ValueError(f"bb_throat_frac + bb_rollin_frac must be <= {MAX_BODY_SUM:g}")


def is_neutral(shape):
    return float(shape["bb_h"]) == 0.0 and float(shape["bb_v"]) == 0.0


def _row_profile(row):
    rho = np.hypot(row[:, 0], row[:, 1])
    z = row[:, 2]
    f = int(np.argmax(z))
    if f < 3:
        raise ValueError("row has no measurable pre-roll")
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1]))
    length = float(ds.sum())
    if length <= 0.0:
        raise ValueError("degenerate pre-roll arc")
    u = np.r_[0.0, np.cumsum(ds)] / length
    theta = np.degrees(np.arctan2(np.gradient(rho[:f + 1]), np.gradient(z[:f + 1])))
    return rho, z, f, u, theta, length


def backbone_schedule(u, t0, thc, tf, lt, lr):
    """Wall angle (deg) of the backbone at arc fraction ``u``."""
    u = np.asarray(u, dtype=float)
    return t0 + (thc - t0) * _S(u / lt) + (tf - thc) * _S((u - (1.0 - lr)) / lr)


def _integrate(t0, thc, tf, length, lt, lr):
    uu = np.linspace(0.0, 1.0, _N)
    th = np.radians(backbone_schedule(uu, t0, thc, tf, lt, lr))
    du = np.diff(uu) * length
    z = np.r_[0.0, np.cumsum(0.5 * (np.cos(th[1:]) + np.cos(th[:-1])) * du)]
    r = np.r_[0.0, np.cumsum(0.5 * (np.sin(th[1:]) + np.sin(th[:-1])) * du)]
    return uu, z, r


def solve_backbone(t0, tf, zf, rf, length0, lt, lr):
    """``(theta_c, arc length)`` so the backbone from (0, 0) lands on (zf, rf)."""
    def fun(x):
        _, z, r = _integrate(t0, x[0], tf, x[1], lt, lr)
        return [z[-1] - zf, r[-1] - rf]
    sol, _info, ok, _msg = fsolve(fun, [math.degrees(math.atan2(rf, zf)), length0], full_output=True)
    if ok != 1 or float(np.max(np.abs(fun(sol)))) > _TOL_MM:
        raise ValueError("backbone end-point solve failed")
    return float(sol[0]), float(sol[1])


def apply_to_inner(inner, shape):
    """Return ``(new_inner, info)``; the same array and an empty list when neutral."""
    if is_neutral(shape):
        return inner, []
    validate_bb(shape)
    lam_h, lam_v = float(shape["bb_h"]), float(shape["bb_v"])
    lt, lr = float(shape["bb_throat_frac"]), float(shape["bb_rollin_frac"])
    inner = np.asarray(inner, dtype=float)
    out = inner.copy()
    h_ref = inner[0, :, 0]
    v_ref = inner[-1, :, 1]
    info = []
    for j in range(inner.shape[0]):
        row = inner[j]
        rho, z, f, u, th, length0 = _row_profile(row)
        psi = math.atan2(row[f, 1] / v_ref[f], row[f, 0] / h_ref[f])
        lam = lam_h * math.cos(psi) ** 2 + lam_v * math.sin(psi) ** 2
        if lam <= _LAM_EPS:
            continue
        zf, rf = float(z[f] - z[0]), float(rho[f] - rho[0])
        t0, tf = float(th[0]), float(th[-1])
        thc, length = solve_backbone(t0, tf, zf, rf, length0, lt, lr)
        uu, zb, rb = _integrate(t0, thc, tf, length, lt, lr)
        zb_u = z[0] + np.interp(u, uu, zb)
        rb_u = rho[0] + np.interp(u, uu, rb)
        zb_u[0], rb_u[0], zb_u[-1], rb_u[-1] = z[0], rho[0], z[f], rho[f]
        if not np.all(np.diff(zb_u) > 0.0) or np.any(np.diff(rb_u) < -1e-9):
            raise ValueError(f"row {j}: backbone is not monotone before the roll")
        z_new = (1.0 - lam) * z[:f + 1] + lam * zb_u
        r_new = (1.0 - lam) * rho[:f + 1] + lam * rb_u
        if not np.all(np.diff(z_new) > 0.0):
            raise ValueError(f"row {j}: blend reverses the pre-roll axial order")
        if np.any(np.diff(r_new) < -1e-6):
            raise ValueError(f"row {j}: blend creates a constriction before the roll")
        if np.any(r_new <= 0.0):
            raise ValueError(f"row {j}: blend crosses the axis")
        scale = r_new / rho[:f + 1]
        out[j, :f + 1, 0] = row[:f + 1, 0] * scale
        out[j, :f + 1, 1] = row[:f + 1, 1] * scale
        out[j, :f + 1, 2] = z_new
        if int(np.argmax(out[j, :, 2])) != f:
            raise ValueError(f"row {j}: backbone moves the forward station")
        info.append({"row": j, "psi_deg": round(math.degrees(psi), 3), "lam": round(lam, 6),
                     "theta_c_deg": round(thc, 4), "arc_mm": round(length, 3)})
    if not np.isfinite(out).all():
        raise ValueError("nonfinite backbone surface")
    return out, info
