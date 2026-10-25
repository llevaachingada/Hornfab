"""Pattern smoothness metrics. Frozen definitions: 01_CONTRACTS.md section 10."""
from __future__ import annotations

import numpy as np

from .polar import coverage_mask, normalized_db

MIN_RIPPLE_SAMPLES = 5


def ripple_db(angles_deg, spl_db, target_total_deg, floor_db=-40.0) -> float:
    """Std dev of normalized dB over in-coverage samples, excluding samples more
    than |floor_db| below on-axis. Fewer than 5 survivors -> np.nan.

    The reference is the 0-degree sample of `angles_deg`. The standard deviation
    is the SAMPLE one (ddof=1). The on-axis sample is in the coverage set and is
    exactly 0 after normalization, so the population std of an alternating
    +1/-1 dB pattern would read sqrt((n-1)/n), never 1.0; the sample std reads
    exactly 1.0 (contract test 19). Std rather than peak-to-peak: peak-to-peak is
    set by one sample, which makes the objective spiky and hostile to CMA-ES.
    """
    a = np.asarray(angles_deg, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    if a.shape != s.shape or a.ndim != 1:
        raise ValueError(f"ripple_db: angles {a.shape} and spl {s.shape} must be equal 1-D shapes")
    i0 = int(np.argmin(np.abs(a)))
    if abs(a[i0]) > 1e-9:
        raise ValueError("ripple_db: no exact 0-degree sample in the angle array")
    n = normalized_db(s, s[i0])
    keep = coverage_mask(a, target_total_deg) & (n >= floor_db)
    if int(keep.sum()) < MIN_RIPPLE_SAMPLES:
        return float("nan")
    return float(np.std(n[keep], ddof=1))


def band_flatness_db(spl_axis_db) -> float:
    """Std dev over frequency of the on-axis level, after removing its mean.
    Non-finite entries are ignored; an empty set returns nan."""
    x = np.asarray(spl_axis_db, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    return float(np.std(x - np.mean(x)))


def coverage_error_deg(bw, target_total_deg) -> np.ndarray:
    """Signed, bw - target. Positive means too wide."""
    return np.asarray(bw, dtype=float) - float(target_total_deg)


# ------------------------------------------------------------------ objective v2 additions
# Appended for objective v2 (senior pass 2026-10-24, WP1). The v1 functions above are frozen
# and untouched; these are new names so no existing run can change.

#: Minimum surviving samples for the detrended ripple fit (three coefficients plus one spare).
MIN_RIPPLE_DETRENDED_SAMPLES = 7


def ripple_detrended_db(angles_deg, spl_db, target_total_deg, floor_db=-40.0) -> float:
    """Ripple about a smooth beam: residual std after an even quartic fit.

    Same angle reference, coverage mask and floor as :func:`ripple_db`: the reference is the
    0-degree sample, samples outside +/- ``target_total_deg`` / 2 are ignored, and samples more
    than ``|floor_db|`` below on-axis are dropped. Fewer than 7 survivors returns ``nan``.

    The normalized dB are fitted with ``n ~ a0 + a2*t^2 + a4*t^4`` (``t`` = angle in radians) by
    least squares, and the SAMPLE std of the residual is returned (``ddof=3`` for the three fitted
    coefficients).

    This measures ripple about a smooth beam, so an ideal taper reads ~0. The v1
    :func:`ripple_db` would read ~1.9 dB for the same ideal taper because it scores the taper
    itself as variance (Report 1 F1).
    """
    a = np.asarray(angles_deg, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    if a.shape != s.shape or a.ndim != 1:
        raise ValueError(
            f"ripple_detrended_db: angles {a.shape} and spl {s.shape} must be equal 1-D shapes")
    i0 = int(np.argmin(np.abs(a)))
    if abs(a[i0]) > 1e-9:
        raise ValueError("ripple_detrended_db: no exact 0-degree sample in the angle array")
    n = normalized_db(s, s[i0])
    keep = coverage_mask(a, target_total_deg) & (n >= floor_db)
    if int(keep.sum()) < MIN_RIPPLE_DETRENDED_SAMPLES:
        return float("nan")
    t = np.radians(a[keep])
    design = np.column_stack([np.ones_like(t), t ** 2, t ** 4])
    coef, *_ = np.linalg.lstsq(design, n[keep], rcond=None)
    residual = n[keep] - design @ coef
    return float(np.std(residual, ddof=3))


def band_flatness_detrended_db(freqs_hz, on_axis_db) -> float:
    """On-axis roughness after removing the drive tilt (Report 1 F2).

    A straight line is fitted to ``on_axis_db`` versus ``log2(f)`` using only finite points with
    ``f > 0``; the SAMPLE std of the residual (``ddof=2``) is returned. Fewer than four usable
    points returns ``nan``.

    The unit-normal-acceleration drive makes absolute on-axis level fall roughly 6 dB/octave; that
    tilt is EQ-able, so it must not drive the geometry objective. What remains is ripple, notches
    and other roughness an equaliser cannot cheaply remove.
    """
    f = np.asarray(freqs_hz, dtype=float)
    x = np.asarray(on_axis_db, dtype=float)
    if f.shape != x.shape or f.ndim != 1:
        raise ValueError(
            f"band_flatness_detrended_db: freqs {f.shape} and on-axis {x.shape} must be equal "
            "1-D shapes")
    ok = np.isfinite(f) & np.isfinite(x) & (f > 0.0)
    if int(ok.sum()) < 4:
        return float("nan")
    lf = np.log2(f[ok])
    coef = np.polyfit(lf, x[ok], 1)
    residual = x[ok] - np.polyval(coef, lf)
    out = float(np.std(residual, ddof=2))
    return out if np.isfinite(out) else float("nan")
