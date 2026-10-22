"""CEA-2034 (spinorama) subset computable from horizontal/vertical cuts.

Method after Boundary Lab's forward-beam-shape / CEA-2034 docs (idea only; independent implementation).

Honest subset: the cuts stop at +-90 deg, so the Early Reflections curve and a
full-sphere Sound Power are NOT computed from cuts. Only the Listening Window and
the Sound Power DI (given a balloon-derived DI) are provided. Cuts: angles ascending
in [-90, +90] including 0, absolute dB, shape (nf, na).
"""
from __future__ import annotations

import numpy as np


def _cut_at(angles, spl, targets):
    """Linear interpolation of each row of spl at the target angles; NaN outside range."""
    a = np.asarray(angles, dtype=float).ravel()
    s = np.asarray(spl, dtype=float)
    if s.ndim != 2 or s.shape[1] != a.size:
        raise ValueError(f"spinorama: spl has shape {s.shape}, expected (nf, {a.size}) to match angles")
    if a.size < 2 or np.any(np.diff(a) <= 0):
        raise ValueError("spinorama: angles must be strictly ascending with at least 2 samples")
    out = np.full((s.shape[0], len(targets)), np.nan)
    for j, t in enumerate(targets):
        if t < a[0] - 1e-9 or t > a[-1] + 1e-9:
            continue
        k = int(np.argmin(np.abs(a - t)))
        if abs(a[k] - t) < 1e-9:
            out[:, j] = s[:, k]
            continue
        i1 = int(np.searchsorted(a, t))
        i0 = i1 - 1
        w = (t - a[i0]) / (a[i1] - a[i0])
        out[:, j] = (1.0 - w) * s[:, i0] + w * s[:, i1]
    return out


def listening_window_db(h_angles_deg, spl_h_db, v_angles_deg, spl_v_db) -> np.ndarray:
    """CEA-2034 listening window, (nf,) dB.

    Energy (10^(L/10)) mean of 9 curves: on-axis, vertical +-10 deg, horizontal
    +-10, +-20, +-30 deg, converted back to dB. Missing angles are linearly
    interpolated (in dB) between neighbouring samples; on-axis is the horizontal
    cut at 0 deg. NaN in any of the nine curves gives NaN.
    """
    h = _cut_at(h_angles_deg, spl_h_db, [0.0, -10.0, 10.0, -20.0, 20.0, -30.0, 30.0])
    v = _cut_at(v_angles_deg, spl_v_db, [-10.0, 10.0])
    if h.shape[0] != v.shape[0]:
        raise ValueError(f"listening_window_db: h has {h.shape[0]} rows, v has {v.shape[0]}")
    curves = np.concatenate([h, v], axis=1)
    with np.errstate(over="ignore", invalid="ignore"):
        return 10.0 * np.log10(np.mean(10.0 ** (curves / 10.0), axis=1))


def spdi_db(lw_db, on_axis_db, di_db) -> np.ndarray:
    """Sound-power DI, (nf,) dB.

    CEA-2034: SPDI = LW - SP. Our balloon DI = OnAxis - SP, so SP = OnAxis - DI and
    SPDI = LW - (OnAxis - DI) = DI - (OnAxis - LW).
    """
    lw = np.asarray(lw_db, dtype=float)
    ax = np.asarray(on_axis_db, dtype=float)
    di = np.asarray(di_db, dtype=float)
    if not (lw.shape == ax.shape == di.shape):
        raise ValueError(f"spdi_db: shapes differ {lw.shape}, {ax.shape}, {di.shape}")
    return di - (ax - lw)
