"""Diagonal (45 / 135 degree azimuth) -6 dB beamwidth from the stored balloon.

Objective v4's ``diag`` term reads this. The H and V cuts miss what a crease, pucker or X-shape
does on the diagonals; the balloon already carries those directions, so no new solves are needed.
Pure numpy/scipy, no solver. Method mirrors ``beam_shape`` (forward +Z, tangent-plane coordinates
``u = x/z``, ``v = y/z``) and the prototype in ``scratch/v4_review/analyze.py``.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import LinearNDInterpolator

from .polar import _threshold_db

#: A ray that never falls below the -6 dB level inside this polar angle reads as a half-width of
#: this angle (the pattern is at least that wide); the full width is then ``2 * MAX_POLAR_DEG``.
MAX_POLAR_DEG = 89.0
_N_STEPS = 400


def _halfwidth_deg(interp, phi: float, level_db: float, rmax: float, r: np.ndarray) -> float:
    u = r * np.cos(phi)
    v = r * np.sin(phi)
    val = interp(u, v)
    below = np.nonzero(np.isfinite(val) & (val <= level_db))[0]
    if below.size == 0:
        return MAX_POLAR_DEG
    j = int(below[0])
    if j == 0:
        return 0.0
    v0, v1 = val[j - 1], val[j]
    t = (level_db - v0) / (v1 - v0) if v1 != v0 else 1.0
    rr = r[j - 1] + t * (r[j] - r[j - 1])
    return float(np.degrees(np.arctan(rr)))


def diagonal_beamwidths_deg(dirs, spl_row_db, on_axis_db: float,
                            drop_db: float = 6.0) -> tuple[float, float]:
    """(bw45, bw135): the full included -``drop_db`` angle in the 45 and 135 degree azimuth planes.

    ``dirs`` is the (nb, 3) unit-vector balloon grid, ``spl_row_db`` the (nb,) levels of ONE
    frequency, ``on_axis_db`` the on-axis level (the reference, as everywhere else in this repo).
    Returns ``(nan, nan)`` when the balloon is unusable (too few forward points, a non-finite
    reference, or an interpolation failure); the caller decides what an unmeasurable diagonal costs.
    """
    d = np.asarray(dirs, dtype=float)
    s = np.asarray(spl_row_db, dtype=float)
    if d.ndim != 2 or d.shape[1] != 3 or s.shape != (d.shape[0],) or not np.isfinite(on_axis_db):
        return float("nan"), float("nan")
    z = d[:, 2]
    fwd = z >= np.cos(np.radians(MAX_POLAR_DEG))
    if int(fwd.sum()) < 8:
        return float("nan"), float("nan")
    pts = np.column_stack([d[fwd, 0] / z[fwd], d[fwd, 1] / z[fwd]])
    vals = s[fwd] - float(on_axis_db)
    vals = np.where(np.isfinite(vals), vals, -120.0)
    _, keep = np.unique(np.round(pts, 9), axis=0, return_index=True)
    pts, vals = pts[keep], vals[keep]
    try:
        interp = LinearNDInterpolator(pts, vals)
    except Exception:  # noqa: BLE001 - degenerate point set: unmeasurable, never a crash
        return float("nan"), float("nan")
    level = _threshold_db(drop_db)
    rmax = float(np.tan(np.radians(MAX_POLAR_DEG)))
    r = np.linspace(0.0, rmax, _N_STEPS)
    out = []
    for phi in (np.radians(45.0), np.radians(135.0)):
        out.append(_halfwidth_deg(interp, phi, level, rmax, r)
                   + _halfwidth_deg(interp, phi + np.pi, level, rmax, r))
    return float(out[0]), float(out[1])
