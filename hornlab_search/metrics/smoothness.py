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
