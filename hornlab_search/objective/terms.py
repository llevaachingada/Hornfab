"""The six raw objective terms (01_CONTRACTS section 11). Pure numpy, no solver.

Every function takes only arrays already restricted to the target band, returns a plain float,
and never raises. ``nan`` handling lives in one place (``_mean``/``_std``): a NaN is dropped and
counted by the caller; a term whose every in-band value is NaN returns ``NAN_TERM_FILL`` (a
documented, finite, deliberately unflattering number), because returning 0.0 would reward the
very patterns the metrics could not measure.
"""
from __future__ import annotations

import numpy as np

from ..metrics.di import di_slope_db_per_decade, target_di_db
from ..targets.spec import Target

#: Penalties, all LARGE AND FINITE (contract section 11). Never inf: one inf poisons the CMA-ES
#: covariance update for the rest of the run.
PENALTY_INVALID = 1.0e3
PENALTY_FAILED = 1.0e3

#: The six weighted terms plus the two bookkeeping keys, in contract order.
TERM_KEYS = ("cov", "rip", "di", "dislope", "flat", "load", "penalty", "total")
#: The six raw terms that carry a weight.
WEIGHTED_KEYS = ("cov", "rip", "di", "dislope", "flat", "load")
#: Keys that accompany TERM_KEYS in every ``Evaluation.terms`` (same key set, always).
EXTRA_KEYS = ("n_nan", "n_in_band", "di_estimated")
ALL_KEYS = TERM_KEYS + EXTRA_KEYS

#: Contract defaults (section 11).
DEFAULT_WEIGHTS = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0}

#: Value of a term when EVERY in-band sample of it is NaN (nothing measurable). Not in the
#: contract: chosen to be bigger than any good design's term (typical 0-10) and far below the
#: 1e3 failure penalty so such a design ranks above a failure but below a working one.
NAN_TERM_FILL = 30.0


def _mean(x: np.ndarray) -> tuple[float, int]:
    """(nanmean, number of NaN entries). All-NaN -> (NAN_TERM_FILL, n)."""
    x = np.asarray(x, dtype=float)
    bad = ~np.isfinite(x)
    n = int(bad.sum())
    good = x[~bad]
    if good.size == 0:
        return NAN_TERM_FILL, n
    return float(np.mean(good)), n


def cov_term(bw_h, bw_v, target: Target) -> tuple[float, int]:
    """mean_f( (bw_h - target_h)^2 + (bw_v - target_v)^2 ) / 100"""
    e = (np.asarray(bw_h, float) - target.coverage_h_deg) ** 2 \
        + (np.asarray(bw_v, float) - target.coverage_v_deg) ** 2
    m, n = _mean(e)
    return m / 100.0, n


def rip_term(ripple_h, ripple_v) -> tuple[float, int]:
    """mean_f( ripple_h + ripple_v ); a frequency where either is NaN is dropped and counted."""
    return _mean(np.asarray(ripple_h, float) + np.asarray(ripple_v, float))


def di_target(target: Target) -> float:
    return float(target.di_target_db) if target.di_target_db is not None \
        else float(target_di_db(target.coverage_h_deg, target.coverage_v_deg))


def di_term(di_db, target: Target) -> tuple[float, int]:
    """mean_f( (di - di_target)^2 ) / 10"""
    m, n = _mean((np.asarray(di_db, float) - di_target(target)) ** 2)
    return m / 10.0, n


def dislope_term(freqs_hz, di_db, target: Target) -> tuple[float, int]:
    """(di_slope - di_slope_target)^2, slope = polyfit(log10 f, di, 1)[0] over the band.
    Fewer than two usable points: slope is NaN -> contributes 0.0 and is counted."""
    s = di_slope_db_per_decade(freqs_hz, di_db)
    if not np.isfinite(s):
        return 0.0, 1
    return float((s - target.di_slope_target) ** 2), 0


def flat_term(on_axis_db) -> tuple[float, int]:
    """std_f( on_axis_db ), population std over the in-band finite samples."""
    x = np.asarray(on_axis_db, float)
    good = x[np.isfinite(x)]
    n = int(x.size - good.size)
    if good.size == 0:
        return NAN_TERM_FILL, n
    return float(np.std(good)), n


def load_term(z_real, target: Target) -> tuple[float, int]:
    """mean_f( max(0, z_min - Re z_throat) ). Skipped (0.0) when the backend reports no z."""
    if z_real is None:
        return 0.0, 0
    z = np.asarray(z_real, float)
    m, n = _mean(np.maximum(0.0, target.z_min - z))
    return m, n
