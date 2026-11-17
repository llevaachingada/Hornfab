"""Dense log-frequency score grid (stage 1 WP 1.2, senior plan 2026-11-17).

A4/N3 measured that scoring on a UNIFORM dense log grid, PCHIP-interpolated in log f from the
solved frequencies, makes J independent of which frequencies were solved: v9 converges by 58
points, v9 plus constancy by 116. This module is that method, packaged (A4 harness
``interp_response(..., method='pchip')``): every real/complex per-frequency array is
interpolated; pressure arrays are dropped so nothing pressure-derived is used; no
extrapolation beyond the solved range.

A dense score is a NEW score identity: never compare it with a stored-grid J.
"""
from __future__ import annotations

import dataclasses

import numpy as np
from scipy.interpolate import PchipInterpolator

DENSE_KIND = "dense_log"
ALLOWED_POINTS = (58, 116, 232)


def _interp(x, a, xn):
    a = np.asarray(a)
    if np.iscomplexobj(a):
        return (PchipInterpolator(x, a.real, axis=0)(xn)
                + 1j * PchipInterpolator(x, a.imag, axis=0)(xn))
    return PchipInterpolator(x, a, axis=0)(xn)


def dense_freqs(solved_hz, points: int, band_lo_hz: float, band_hi_hz: float) -> np.ndarray:
    f = np.asarray(solved_hz, dtype=float)
    lo = max(float(band_lo_hz), float(f.min()))
    hi = min(float(band_hi_hz), float(f.max()))
    if not hi > lo:
        raise ValueError("no overlap between the solved range and the scored band")
    return np.geomspace(lo, hi, int(points))


def dense_response(resp, points: int, band_lo_hz: float, band_hi_hz: float):
    """The Response re-sampled on ``points`` log-spaced frequencies inside the solved range."""
    f = np.asarray(resp.freqs_hz, dtype=float)
    if f.size < 3 or np.any(np.diff(f) <= 0):
        raise ValueError("dense grid needs >= 3 strictly increasing solved frequencies")
    fn = dense_freqs(f, points, band_lo_hz, band_hi_hz)
    x, xn = np.log(f), np.log(fn)
    out = {"freqs_hz": fn, "spl_h_db": _interp(x, resp.spl_h_db, xn),
           "spl_v_db": _interp(x, resp.spl_v_db, xn),
           "spl_balloon_db": None if resp.spl_balloon_db is None else _interp(x, resp.spl_balloon_db, xn),
           "z_throat": None if resp.z_throat is None else _interp(x, resp.z_throat, xn),
           "p_h": None, "p_v": None, "p_balloon": None}
    for name in ("channel_pressure", "channel_sphere_pressure", "impedance_matrix"):
        if getattr(resp, name, None) is not None:
            out[name] = None
    meta = dict(getattr(resp, "meta", {}) or {})
    meta["score_grid"] = {"kind": DENSE_KIND, "points": int(points), "interp": "pchip_logf",
                          "solved_n": int(f.size)}
    out["meta"] = meta
    return dataclasses.replace(resp, **out)


def validate_score_grid(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("objective.score_grid must be a mapping {kind: dense_log, points: N}")
    unknown = set(raw) - {"kind", "points"}
    if unknown:
        raise ValueError(f"objective.score_grid: unknown key(s) {sorted(unknown)}")
    if raw.get("kind") != DENSE_KIND:
        raise ValueError(f"objective.score_grid.kind must be {DENSE_KIND!r}, got {raw.get('kind')!r}")
    n = raw.get("points")
    if isinstance(n, bool) or n not in ALLOWED_POINTS:
        raise ValueError(f"objective.score_grid.points must be one of {list(ALLOWED_POINTS)}, got {n!r}")
    return {"kind": DENSE_KIND, "points": int(n)}
