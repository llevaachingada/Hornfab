"""acoustic_metrics_v2 (proposed, additive): status-aware main-lobe descriptors on a polar cut.

Rev2 plan section 5 (docs/research/QUEUE_PLAN_REV2_2026-11-13.md). Does NOT replace or change
``metrics/polar.py::beamwidth_deg`` (legacy OUTERMOST crossings, 180 deg sentinel), which every
objective version still uses. Nothing here feeds an objective. Pure numpy, no solver.

Main-lobe width = the FIRST threshold crossing walking outward from 0 deg on each side, so a
detached side lobe cannot widen it. Each side is ``valid`` or ``censored`` (no crossing inside the
sampled range); a censored side reports the range edge as a lower bound, never 180 deg as a
measurement.
"""
from __future__ import annotations

import numpy as np

from .polar import _threshold_db, normalized_db

METHOD_VERSION = "acoustic_v2.0"


def _first_crossing(a: np.ndarray, d: np.ndarray, thr: float) -> tuple[float, str]:
    """a, d start at 0 deg and walk outward. Linear-in-dB interpolation, like legacy."""
    for i in range(1, len(a)):
        if d[i] <= thr < d[i - 1] or d[i] <= thr <= d[i - 1] and d[i - 1] > thr:
            t = (d[i - 1] - thr) / (d[i - 1] - d[i])
            return float(a[i - 1] + t * (a[i] - a[i - 1])), "valid"
    return float(a[-1]), "censored"


def main_lobe(angles_deg, spl_db, drop_db: float = 6.0) -> dict:
    """Main-lobe width and off-axis peak on one cut. Reference is the 0 deg sample.

    Returns {width_deg, left_deg, right_deg, left_status, right_status, status,
    max_offaxis_db, max_offaxis_angle_deg, outside_peak_db, method}.
    ``outside_peak_db``: highest level outside the main lobe (dB re axis), so a detached side lobe
    or a lobe above axis shows up even though the main width ignores it. None if nothing outside.
    """
    a = np.asarray(angles_deg, float)
    s = np.asarray(spl_db, float)
    if a.ndim != 1 or a.shape != s.shape:
        raise ValueError("angles_deg and spl_db must be 1-D and the same length")
    order = np.argsort(a)
    a, s = a[order], s[order]
    k = np.flatnonzero(np.abs(a) < 1e-9)
    if k.size != 1:
        raise ValueError("need exactly one 0-degree sample")
    k = int(k[0])
    d = normalized_db(s, s[k])
    thr = _threshold_db(drop_db)
    r_ang, r_st = _first_crossing(a[k:], d[k:], thr)
    l_ang, l_st = _first_crossing(-a[k::-1], d[k::-1], thr)
    out = (a > r_ang) | (a < -l_ang)
    off = np.abs(a) > 1e-9
    j = int(np.argmax(np.where(off, d, -np.inf))) if off.any() else None
    status = "valid" if (l_st == r_st == "valid") else "censored"
    return {
        "width_deg": l_ang + r_ang, "left_deg": l_ang, "right_deg": r_ang,
        "left_status": l_st, "right_status": r_st, "status": status,
        "max_offaxis_db": float(d[j]) if j is not None else None,
        "max_offaxis_angle_deg": float(a[j]) if j is not None else None,
        "outside_peak_db": float(d[out].max()) if out.any() else None,
        "drop_db": float(drop_db), "method": METHOD_VERSION,
    }
