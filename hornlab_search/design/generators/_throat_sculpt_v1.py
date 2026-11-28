"""Versioned throat-sculpt kernel (``throat-sculpt-v1``; LABELED HYPOTHESIS, no published name).

Research basis: ``docs/research/typologies/sculpted_throat_2026-11-25/`` (handoff s6.1 / s6.3 and the
CAD-verified ST260-BLD reference, whose signed angular throat angle drives the wall 62 % of the way into
the source disk on one axis). The kernel deforms the FORWARD CORE of an already-resolved parent meridian
set (row = fixed azimuth psi, psi = 0 the horizontal plane, psi = 90 deg the vertical plane; each row a
single-valued wall r(z) from the source plane z = 0 up to its forward station) and leaves the body, the
mouth and any lip downstream of the core bit-for-bit untouched.

Two independent operators, applied in this order:

(A) **Angular slot depth** (flare-onset delay, NOT a contraction).  With the source cone
    ``t(z) = r0 + z tan(a0)`` and the parent's excess flare ``e(z) = r_p(z) - t(z)``::

        D(psi) = slot_h |cos psi|^(2p) + slot_v |sin psi|^(2p) + slot_d |sin 2psi|^(2p)
        r(z)   = t(z) + e(m(z)),   m = 0 (z <= D),  m = z (z >= z_rec),
        m(z)   = z_rec B((z - D) / (z_rec - D)) between,  z_rec = max_psi D + slot_span

    ``B`` is the unique quintic with B(0)=B'(0)=B''(0)=0, B(1)=1, B'(1)=(z_rec-D)/z_rec, B''(1)=0
    (monotone for every D < z_rec), so the onset and the recovery are both C2 and the wall from z_rec on
    IS the parent.  The driver tangent is exact (the wall is the source cone up to D).

(C) **Signed radial sculpt** (driver-matched; may cross below r0 = a TRUE pinch)::

        r += r0 w(z) F(psi),   F = c2 cos 2psi + c4 cos 4psi + c6 cos 6psi
        w = Q((z - z0)/rise) on [z0, zp],  1 - Q((z - zp)/fall) on [zp, z1],  0 elsewhere

    ``Q`` is the C2 quintic smoothstep, so w and its first two derivatives vanish at z0 (the source plane
    keeps its circle and tangent when z0 = 0) and at z1.  Negative ``c2`` narrows H and widens V.  The
    even cosines keep both mirror planes (quarter model).

``area = 1`` rescales each section radially, at every z in the core, so the sculpted section area equals
the pre-sculpt (post-slot) area: the sculpt then redistributes the passage instead of choking it.  The
achieved pinch is REPORTED from the emitted rows (never inferred from c2); a non-positive radius, a core
that is not single-valued, or a sculpt that reaches past the forward station is refused.

Station policy: the sculpted rows are re-stationed with ``core_step_mm`` spacing (by arc) through the core
and uniform arc spacing after it, the SAME station count split for every row, so the throat feature is
carried by the point grid instead of being chorded by the parent's uniform stations.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = "throat-sculpt-v1"
TS_KEYS = ("ts_c2", "ts_c4", "ts_c6", "ts_on_mm", "ts_rise_mm", "ts_fall_mm", "ts_area",
           "ts_slot_h_mm", "ts_slot_v_mm", "ts_slot_d_mm", "ts_slot_pow", "ts_slot_span_mm")
DEFAULTS = {"ts_c2": 0.0, "ts_c4": 0.0, "ts_c6": 0.0, "ts_on_mm": 0.0, "ts_rise_mm": 12.0,
            "ts_fall_mm": 30.0, "ts_area": 0.0, "ts_slot_h_mm": 0.0, "ts_slot_v_mm": 0.0,
            "ts_slot_d_mm": 0.0, "ts_slot_pow": 2.0, "ts_slot_span_mm": 40.0}
LIMITS = {"ts_c2": (-0.8, 0.8), "ts_c4": (-0.4, 0.4), "ts_c6": (-0.2, 0.2), "ts_on_mm": (0.0, 60.0),
          "ts_rise_mm": (2.0, 80.0), "ts_fall_mm": (4.0, 160.0), "ts_area": (0.0, 1.0),
          "ts_slot_h_mm": (0.0, 80.0), "ts_slot_v_mm": (0.0, 80.0), "ts_slot_d_mm": (0.0, 60.0),
          "ts_slot_pow": (0.5, 8.0), "ts_slot_span_mm": (5.0, 200.0)}
RADIAL_AMP = ("ts_c2", "ts_c4", "ts_c6")
SLOT_AMP = ("ts_slot_h_mm", "ts_slot_v_mm", "ts_slot_d_mm")
CORE_STEP_DEFAULT_MM = 3.0
CORE_MARGIN_MM = 6.0          # stations stay fine this far past the last deformed z
MIN_BODY_STATIONS = 8


def validate(ts: dict) -> None:
    for key in TS_KEYS:
        if key not in ts:
            raise ValueError(f"missing throat-sculpt key {key}")
        v = ts[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            raise ValueError(f"{key} must be a finite number")
        lo, hi = LIMITS[key]
        if not lo <= float(v) <= hi:
            raise ValueError(f"{key} must be in [{lo:g}, {hi:g}], got {v!r}")
    if float(ts["ts_area"]) not in (0.0, 1.0):
        raise ValueError("ts_area must be 0 (free) or 1 (preserve the pre-sculpt section area)")


def radial_active(ts: dict) -> bool:
    return any(float(ts[k]) != 0.0 for k in RADIAL_AMP)


def slot_active(ts: dict) -> bool:
    return any(float(ts[k]) != 0.0 for k in SLOT_AMP)


def is_neutral(ts: dict) -> bool:
    return not (radial_active(ts) or slot_active(ts))


def _Q(u):
    u = np.clip(u, 0.0, 1.0)
    return u ** 3 * (10.0 - 15.0 * u + 6.0 * u * u)


def bump(z, ts: dict):
    """Compact-support C2 axial window w(z) (0 outside [z0, z1], 1 at the peak)."""
    z = np.asarray(z, dtype=float)
    z0 = float(ts["ts_on_mm"])
    zp = z0 + float(ts["ts_rise_mm"])
    z1 = zp + float(ts["ts_fall_mm"])
    up = _Q((z - z0) / (zp - z0))
    down = 1.0 - _Q((z - zp) / (z1 - zp))
    return np.where(z <= zp, up, down) * ((z > z0) & (z < z1))


def harmonic(psi, ts: dict):
    psi = np.asarray(psi, dtype=float)
    return (float(ts["ts_c2"]) * np.cos(2 * psi) + float(ts["ts_c4"]) * np.cos(4 * psi)
            + float(ts["ts_c6"]) * np.cos(6 * psi))


def slot_depth(psi, ts: dict):
    p = 2.0 * float(ts["ts_slot_pow"])
    psi = np.asarray(psi, dtype=float)
    return (float(ts["ts_slot_h_mm"]) * np.abs(np.cos(psi)) ** p
            + float(ts["ts_slot_v_mm"]) * np.abs(np.sin(psi)) ** p
            + float(ts["ts_slot_d_mm"]) * np.abs(np.sin(2 * psi)) ** p)


def slot_map(z, D: float, z_rec: float):
    """C2 monotone delayed coordinate m(z): 0 up to D, z from z_rec, quintic between."""
    z = np.asarray(z, dtype=float)
    if D <= 0.0:
        return z.copy()
    sig = (z_rec - D) / z_rec
    a, b, c = 10.0 - 4.0 * sig, -15.0 + 7.0 * sig, 6.0 - 3.0 * sig
    u = np.clip((z - D) / (z_rec - D), 0.0, 1.0)
    mid = z_rec * u ** 3 * (a + u * (b + c * u))
    return np.where(z <= D, 0.0, np.where(z >= z_rec, z, mid))


def core_end_mm(ts: dict, psis) -> float:
    """Largest z any operator touches."""
    end = 0.0
    if radial_active(ts):
        end = float(ts["ts_on_mm"]) + float(ts["ts_rise_mm"]) + float(ts["ts_fall_mm"])
    if slot_active(ts):
        end = max(end, float(np.max(slot_depth(psis, ts))) + float(ts["ts_slot_span_mm"]))
    return end


def _forward_core(x, y):
    """Index of the forward station (max z); the core is x[:k+1], which must be strictly increasing."""
    k = int(np.argmax(x))
    if not np.all(np.diff(x[: k + 1]) > 0.0):
        raise ValueError("parent row is not a single-valued r(z) up to its forward station")
    return k


def _area_quarter(r_by_row: np.ndarray, psis: np.ndarray) -> np.ndarray:
    """Full section area from quarter rows: 4 * 0.5 * int_0^{pi/2} r^2 dpsi (trapezoid)."""
    return 2.0 * np.trapezoid(r_by_row ** 2, psis, axis=0)


def apply(rows, psis, ts: dict, r0: float, a0_deg: float, n_s: int,
          core_step_mm: float = CORE_STEP_DEFAULT_MM):
    """Deform the forward core of every row; return (new_rows, info).

    ``rows`` is a list of (x, y) arrays (x = axial z mm from the source plane, y = radius mm),
    densely sampled; ``psis`` their azimuths (quarter, 0 = H).  ``new_rows`` are re-stationed to
    exactly ``n_s + 1`` stations each.
    """
    validate(ts)
    psis = np.asarray(psis, dtype=float)
    if psis[0] != 0.0 or abs(psis[-1] - 0.5 * math.pi) > 1e-9:
        raise ValueError("throat sculpt needs quarter rows from psi = 0 (H) to 90 deg (V)")
    z_end = core_end_mm(ts, psis)
    t_a0 = math.tan(math.radians(a0_deg))
    xs, ys, ks = [], [], []
    for x, y in rows:
        x = np.asarray(x, dtype=float).copy()
        y = np.asarray(y, dtype=float).copy()
        k = _forward_core(x, y)
        if x[k] <= z_end + CORE_MARGIN_MM:
            raise ValueError(f"the sculpt reaches z = {z_end:.1f} mm but a row's forward station is "
                             f"at {x[k]:.1f} mm; shorten the sculpt")
        if abs(x[0]) > 1e-6 or abs(y[0] - r0) > 1e-6 * max(1.0, r0):
            raise ValueError("parent row does not start on the source circle (z = 0, r = r0)")
        xs.append(x); ys.append(y); ks.append(k)
    # (A) slot delay
    D = slot_depth(psis, ts)
    z_rec = float(np.max(D)) + float(ts["ts_slot_span_mm"]) if slot_active(ts) else 0.0
    if slot_active(ts):
        for i in range(len(xs)):
            if D[i] <= 0.0:
                continue
            x, y, k = xs[i], ys[i], ks[i]
            core = x <= z_rec
            t = r0 + x * t_a0
            e_core = y[: k + 1] - (r0 + x[: k + 1] * t_a0)
            m = slot_map(x[core], float(D[i]), z_rec)
            y[core] = t[core] + np.interp(m, x[: k + 1], e_core)
    pre = [y.copy() for y in ys]
    # (C) radial sculpt
    if radial_active(ts):
        F = harmonic(psis, ts)
        for i in range(len(xs)):
            ys[i] = ys[i] + r0 * bump(xs[i], ts) * F[i] * (xs[i] <= z_end + 1e-9)
        if float(ts["ts_area"]) == 1.0:
            zc = np.linspace(0.0, z_end, 801)
            r_pre = np.stack([np.interp(zc, xs[i][: ks[i] + 1], pre[i][: ks[i] + 1]) for i in range(len(xs))])
            r_new = np.stack([np.interp(zc, xs[i][: ks[i] + 1], ys[i][: ks[i] + 1]) for i in range(len(xs))])
            if np.any(r_new <= 0.0):
                raise ValueError("the radial sculpt drives the wall through the axis")
            scale = np.sqrt(_area_quarter(r_pre, psis) / _area_quarter(r_new, psis))
            for i in range(len(xs)):
                s = np.where(xs[i] <= z_end, np.interp(xs[i], zc, scale), 1.0)
                ys[i] = ys[i] * s
    for y in ys:
        if not np.all(np.isfinite(y)) or np.any(y <= 0.0):
            raise ValueError("the throat sculpt produced a non-positive or nonfinite radius")
    # re-station: shared core/body split
    l_core = []
    for x, y, k in zip(xs, ys, ks):
        arc = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))))
        zc_end = min(z_end + CORE_MARGIN_MM, float(x[k]))
        l_core.append(float(np.interp(zc_end, x[: k + 1], arc[: k + 1])))
    n_core = int(math.ceil(max(l_core) / float(core_step_mm)))
    if n_s - n_core < MIN_BODY_STATIONS:
        raise ValueError(f"n_s = {n_s} leaves {n_s - n_core} body stations after {n_core} core stations "
                         f"at {core_step_mm:g} mm; raise n_s (>= {n_core + MIN_BODY_STATIONS})")
    out = []
    for x, y, lc in zip(xs, ys, l_core):
        arc = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))))
        tgt = np.concatenate((np.linspace(0.0, lc, n_core + 1),
                              np.linspace(lc, arc[-1], n_s - n_core + 1)[1:]))
        xr, yr = np.interp(tgt, arc, x), np.interp(tgt, arc, y)
        xr[0], yr[0], xr[-1], yr[-1] = x[0], y[0], x[-1], y[-1]
        out.append((xr, yr))
    info = describe(out, pre, xs, psis, r0, z_end)
    info.update({"slot_depth_mm": {f"{math.degrees(p):.2f}": float(d) for p, d in zip(psis, D)},
                 "slot_recover_mm": z_rec, "core_end_mm": z_end, "core_stations": n_core,
                 "core_step_mm": float(core_step_mm)})
    return out, info


def describe(rows, pre, dense_x, psis, r0: float, z_end: float) -> dict:
    """Achieved-geometry descriptors from the emitted rows (z-sampled)."""
    zc = np.linspace(0.0, max(z_end, 1.0), 401)
    R = []
    for x, y in rows:
        k = int(np.argmax(x))
        R.append(np.interp(zc, x[: k + 1], y[: k + 1]))
    R = np.stack(R)                               # (rows, z)
    i, j = np.unravel_index(int(np.argmin(R)), R.shape)
    area = _area_quarter(R, psis)
    hv = R[0] / R[-1]
    return {"r_min_mm": float(R[i, j]), "pinch_ratio": float(R[i, j] / r0),
            "intrusion_mm": float(max(0.0, r0 - R[i, j])), "r_min_z_mm": float(zc[j]),
            "r_min_psi_deg": float(math.degrees(psis[i])),
            "true_pinch": bool(R[i, j] < r0 - 1e-9),
            "h_waist_min_mm": float(np.min(R[0])), "v_waist_min_mm": float(np.min(R[-1])),
            "area_ratio_min": float(np.min(area) / (math.pi * r0 ** 2)),
            "area_monotone": bool(np.all(np.diff(area) >= -1e-6 * area[0])),
            "hv_ratio_min": float(np.min(hv)), "hv_ratio_max": float(np.max(hv)),
            "negative_slope_rows": int(sum(np.any(np.diff(r) < -1e-9) for r in R))}
