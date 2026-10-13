"""Directivity index. Frozen definitions: 01_CONTRACTS.md sections 7 and 10."""
from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger("hornlab_search.metrics.di")


def di_from_balloon(spl_balloon_db, spl_axis_db, weights=None) -> float:
    """10*log10( p_axis^2 / mean(p_balloon^2) ), computed in LINEAR POWER.

    Equal weights (weights=None) are correct for an equal-area grid such as the
    contract's Fibonacci balloon. For a theta-phi grid (the real solver's
    `sphere_grid`, theta-major) pass weights=sin_theta_weights(theta_deg), or the
    result is biased towards the poles.

    Averaging dB values instead of powers would be a different and wrong quantity.
    The sphere is covered in full: a hemisphere average gives a dipole the right
    answer and a cardioid the wrong one.

    A dead pattern (non-finite axis level, or no finite balloon power) has no
    defined DI and returns 0.0 with a warning, so downstream means stay finite.
    """
    b = np.asarray(spl_balloon_db, dtype=float).ravel()
    ax = float(spl_axis_db)
    if not np.isfinite(ax):
        log.warning("di_from_balloon: non-finite on-axis level; returning 0.0 dB")
        return 0.0
    with np.errstate(over="ignore", invalid="ignore"):
        ratio = 10.0 ** ((b - ax) / 10.0)          # p_balloon^2 / p_axis^2; -inf -> 0
    if weights is None:
        m = np.mean(ratio)
    else:
        w = np.asarray(weights, dtype=float).ravel()
        if w.shape != ratio.shape:
            raise ValueError(f"di_from_balloon: weights {w.shape} do not match balloon {ratio.shape}")
        m = np.sum(w * ratio) / np.sum(w)
    if not np.isfinite(m) or m <= 0.0:
        log.warning("di_from_balloon: no finite balloon power; returning 0.0 dB")
        return 0.0
    return float(-10.0 * np.log10(m))


def sin_theta_weights(theta_deg) -> np.ndarray:
    """Quadrature weights for a theta-phi grid: sin(theta), theta from +Z in degrees.

    For a grid uniform in phi and uniform in theta (including the poles, where the
    weight is 0, or at midpoints) this is the standard area weighting.
    """
    return np.sin(np.radians(np.asarray(theta_deg, dtype=float)))


def di_from_cuts(bw_h_deg, bw_v_deg) -> float:
    """ESTIMATE. Assumes a separable rectangular pattern.

      Omega = 4*arcsin( sin(bw_h/2) * sin(bw_v/2) )
      DI    = 10*log10( 4*pi / Omega )

    Wrong for lobed or diagonal-misbehaving patterns. The caller MUST set
    MetricSet.di_source = 'cuts_estimate' when using this.

    Two conventions the contract formula does not cover (see NOTES_FOR_SENIOR.md):
      - A beamwidth of 180 or more is the "no -6 dB crossing in range" reading, so it
        means "at least that wide". sin(bw/2) is clamped at 1 (bw_h = 360 and
        bw_h = 180 count the same).
      - If BOTH cuts are saturated (>= 180) the pattern is treated as omnidirectional,
        Omega = 4*pi, DI = 0. The raw formula would give 3.01 dB (a hemisphere) for
        (180, 180) and nonsense for (360, 180), but an omni source and the "target"
        full-sphere case both need to read 0.
    """
    h = float(bw_h_deg)
    v = float(bw_v_deg)
    if h >= 180.0 and v >= 180.0:
        return 0.0
    sh = np.sin(np.radians(min(h, 180.0)) / 2.0)
    sv = np.sin(np.radians(min(v, 180.0)) / 2.0)
    x = min(max(sh * sv, 1e-12), 1.0)
    omega = 4.0 * np.arcsin(x)
    return float(10.0 * np.log10(4.0 * np.pi / omega))


def target_di_db(cov_h_total_deg, cov_v_total_deg) -> float:
    """Same formula, applied to the target angles. 75 x 45 -> 11.3 dB."""
    return di_from_cuts(cov_h_total_deg, cov_v_total_deg)


def di_slope_db_per_decade(freqs_hz, di_db) -> float:
    """polyfit(log10 f, di_db, 1)[0]. Non-finite points are dropped; fewer than two
    usable points returns nan."""
    f = np.asarray(freqs_hz, dtype=float)
    d = np.asarray(di_db, dtype=float)
    ok = np.isfinite(f) & np.isfinite(d) & (f > 0)
    if ok.sum() < 2 or np.ptp(f[ok]) == 0.0:
        return float("nan")
    return float(np.polyfit(np.log10(f[ok]), d[ok], 1)[0])
