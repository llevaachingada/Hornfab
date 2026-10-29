"""Polar-cut metrics: beamwidth, coverage mask, normalized dB.

Frozen definitions: 01_CONTRACTS.md section 10. Pure numpy, no solver.
"""
from __future__ import annotations

import numpy as np

# Floor for normalized dB. One -inf makes every std/mean downstream nan, and a nan
# objective poisons the CMA-ES covariance update for the rest of the run.
DB_FLOOR = -120.0

# Tolerance for "is this the 0-degree sample" and for coverage-edge inclusion.
_ANGLE_TOL = 1e-9


def _threshold_db(drop_db: float) -> float:
    """The normalized level (negative dB) at which a beamwidth edge is declared.

    The two conventional drop labels are exact amplitude ratios, not rounded dB:
      -6 dB  is HALF PRESSURE: 20*log10(0.5) = -6.0206 dB.
      -3 dB  is HALF POWER:    10*log10(0.5) = -3.0103 dB.
    This is what makes the contract's closed-form cases exact. A cardioid
    p = (1+cos t)/2 is 0.5 at exactly t = 90 deg, and a dipole p = cos t is 0.5 at
    exactly t = 60 deg (01_CONTRACTS section 10: "the cardioid reads 180.0"). A strict
    -6.0000 dB threshold would instead read about 179.73 and 119.83 deg, because
    -6.0206 dB is 0.0206 dB below -6.0 (see NOTES_FOR_SENIOR.md). Any other
    drop_db is taken literally.
    """
    if abs(drop_db - 6.0) < 1e-12:
        return 20.0 * np.log10(0.5)
    if abs(drop_db - 3.0) < 1e-12:
        return 10.0 * np.log10(0.5)
    return -float(drop_db)


def normalized_db(spl_db, ref_db=None) -> np.ndarray:
    """spl_db minus the on-axis value, floored at DB_FLOOR (-120 dB).

    ref_db: scalar, or an array whose shape is spl_db.shape[:-1] (one reference per
    row). If None, the reference is the centre sample along the last axis, which is
    the 0-degree sample of the contract's odd, symmetric -90..+90 grid; an even
    length then raises ValueError.

    Never returns -inf or nan: a non-finite input or a non-finite reference (a dead,
    all -inf pattern) maps to DB_FLOOR.
    """
    s = np.asarray(spl_db, dtype=float)
    if ref_db is None:
        n = s.shape[-1]
        if n % 2 == 0:
            raise ValueError("normalized_db: need an odd sample count to infer the on-axis sample")
        ref = s[..., n // 2]
    else:
        ref = np.asarray(ref_db, dtype=float)
    if ref.ndim and ref.ndim == s.ndim - 1:
        ref = ref[..., None]
    with np.errstate(invalid="ignore", over="ignore"):
        d = s - ref
    return np.where(np.isfinite(d), np.maximum(d, DB_FLOOR), DB_FLOOR)


def coverage_mask(angles_deg, target_total_deg) -> np.ndarray:
    """True inside +/- target/2, inclusive at the edge."""
    a = np.asarray(angles_deg, dtype=float)
    return np.abs(a) <= 0.5 * float(target_total_deg) + _ANGLE_TOL


def beamwidth_deg(angles_deg, spl_db, drop_db: float = 6.0) -> tuple[float, int]:
    """Total included angle between the OUTERMOST two -drop_db crossings.

    Returns (width_deg, n_crossings).

    Frozen rules (01_CONTRACTS.md section 10):
      - Reference is the ON-AXIS sample, not the maximum.
      - Crossings are interpolated LINEARLY IN dB versus angle between the two
        bracketing samples. Never snapped to the nearest sample.
      - No crossing anywhere in range -> (180.0, 0).
      - More than two crossings -> outermost pair; n_crossings is the true count.
      - No exact 0-degree sample -> ValueError.

    Cases the contract does not spell out:
      - Exactly one crossing: the other edge is the end of the angle grid on that
        side (the pattern is still inside the threshold there), so a one-sided
        pattern reads the angle from the crossing to the grid edge.
      - A non-finite on-axis level (a dead pattern) carries no information and reads
        (180.0, 0), the same as "no crossing".
      - Non-finite off-axis samples are treated as the -120 dB floor.
    The threshold level is defined in _threshold_db.
    """
    a = np.asarray(angles_deg, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    if a.ndim != 1 or s.shape != a.shape:
        raise ValueError(f"beamwidth_deg: angles {a.shape} and spl {s.shape} must be equal 1-D shapes")
    if a.size < 2:
        raise ValueError("beamwidth_deg: need at least two samples")
    if np.any(np.diff(a) <= 0):
        raise ValueError("beamwidth_deg: angles must be strictly ascending")
    i0 = int(np.argmin(np.abs(a)))
    if abs(a[i0]) > _ANGLE_TOL:
        raise ValueError("beamwidth_deg: no exact 0-degree sample in the angle array")
    if not np.isfinite(s[i0]):
        return 180.0, 0

    thr = _threshold_db(drop_db)
    n = normalized_db(s, s[i0])
    inside = n >= thr
    flips = np.nonzero(inside[:-1] != inside[1:])[0]
    if flips.size == 0:
        return 180.0, 0

    # One side of every flip is >= thr and the other < thr, so n[j+1] != n[j].
    t = (thr - n[flips]) / (n[flips + 1] - n[flips])
    crossings = a[flips] + t * (a[flips + 1] - a[flips])
    lo, hi = float(crossings.min()), float(crossings.max())
    if crossings.size == 1:
        if lo < 0.0:
            hi = float(a[-1])
        else:
            lo = float(a[0])
    return hi - lo, int(crossings.size)


def beamwidth_edges_deg(angles_deg, spl_db, drop_db: float = 6.0) -> tuple[float, float]:
    """The signed (lower_deg, upper_deg) -drop_db crossings of a cut (2026-10-29, objective v5 C5).

    ``beamwidth_deg`` returns one total width; some briefs specify the two halves separately
    (an asymmetric vertical coverage). This returns the SAME outermost crossing on each side of
    the on-axis sample, so ``upper - lower`` is ``beamwidth_deg``'s width for a two-sided pattern.

    Frozen rules, matching ``beamwidth_deg`` (01_CONTRACTS.md section 10):
      - Reference is the ON-AXIS sample, not the maximum; no exact 0-degree sample -> ValueError.
      - Threshold is the same exact half-pressure level (-6.0206 dB) for ``drop_db=6``.
      - Crossings are interpolated LINEARLY IN dB versus angle between the bracketing samples.
      - No crossing on a side -> the angle grid's edge on that side, so a one-sided pattern still
        reports a usable, finite edge.
      - An all-non-finite pattern carries no information: both edges are the grid edges.

    ``lower`` is the outermost negative-side crossing (the grid start when there is none) and
    ``upper`` the outermost positive-side crossing (the grid end when there is none).
    """
    a = np.asarray(angles_deg, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    if a.ndim != 1 or s.shape != a.shape:
        raise ValueError(
            f"beamwidth_edges_deg: angles {a.shape} and spl {s.shape} must be equal 1-D shapes")
    if a.size < 2:
        raise ValueError("beamwidth_edges_deg: need at least two samples")
    if np.any(np.diff(a) <= 0):
        raise ValueError("beamwidth_edges_deg: angles must be strictly ascending")
    i0 = int(np.argmin(np.abs(a)))
    if abs(a[i0]) > _ANGLE_TOL:
        raise ValueError("beamwidth_edges_deg: no exact 0-degree sample in the angle array")
    lo_edge, hi_edge = float(a[0]), float(a[-1])
    if not np.isfinite(s[i0]):
        return lo_edge, hi_edge

    thr = _threshold_db(drop_db)
    n = normalized_db(s, s[i0])
    inside = n >= thr
    flips = np.nonzero(inside[:-1] != inside[1:])[0]
    if flips.size == 0:
        return lo_edge, hi_edge

    # One side of every flip is >= thr and the other < thr, so n[j+1] != n[j].
    t = (thr - n[flips]) / (n[flips + 1] - n[flips])
    crossings = a[flips] + t * (a[flips + 1] - a[flips])
    lower = crossings[crossings <= 0.0]
    upper = crossings[crossings >= 0.0]
    lo = float(lower.min()) if lower.size else lo_edge
    hi = float(upper.max()) if upper.size else hi_edge
    return lo, hi
