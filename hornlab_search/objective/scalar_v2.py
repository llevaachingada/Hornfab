"""The scalar objective J, version 2 (senior pass 2026-10-24, WP1 + objective side of WP4).

LOWER IS BETTER.  ``objective_v2`` NEVER raises and never returns nan or inf.

The six terms keep the v1 names, weights and divisors, so every downstream consumer
(``Evaluation.terms``, the dataset, the report, the surrogate) is version-agnostic:

    J = w_cov*cov + w_rip*rip + w_di*di + w_dislope*dislope + w_flat*flat + w_load*load + penalty

What changes versus v1 (Report 1 F1, F2, F5):

* ``rip`` measures ripple ABOUT A SMOOTH BEAM: per frequency it is the sum of the horizontal and
  vertical ``ripple_detrended_db`` (an even quartic fit removes the taper itself). The v1
  ``ripple_db`` scored the taper as variance, so an ideal beam floored at ~3.8 for the two planes.
* ``flat`` is ``band_flatness_detrended_db``: the on-axis roughness left after removing the
  EQ-able linear tilt in log2 f, not the raw std that mostly measured the unit-acceleration drive.
* ``di`` is scored against ``target_di_gaussian_db(coverage)``, the numerical DI of an ideal
  separable Gaussian beam at the target widths, instead of the cuts formula that read ~2.5 dB low.
  An explicitly set ``target.di_target_db`` keeps its v1 meaning. When ``weights['di'] == 0`` the
  term is skipped (0.0).
* ``cov``, ``dislope`` and ``load`` are unchanged from v1.

Per-frequency inputs come from the solver ``Response`` (``spl_h_db``/``spl_v_db`` at the stored
cut angles, on-axis column ``resp.axis_index``), mirroring ``search/evaluate.py``. If the response
is absent, or it is a collapsed-balloon view / missing angles or indices, the function degrades
gracefully instead of failing: ``rip`` falls back to the stored v1 ``metrics.ripple_h_db`` +
``metrics.ripple_v_db`` and ``flat`` is computed from ``metrics.on_axis_db``.

WP4 (objective side): when ``target.freq_weights`` is set, the per-frequency ripple mean is a
weighted mean. Each frequency gets the PRODUCT of every matching ``band_hz`` interval's weight
(``[[lo_hz, hi_hz, w], ...]``, default 1.0). With no ``freq_weights`` the mean is the plain mean.
The helper is module-level and testable: :func:`freq_weight_vector`. The other terms keep their
v1 aggregation, because the WP1 term list fixes ``cov``, ``di``, ``dislope`` and ``load`` to v1;
only ``rip`` is a per-frequency average in v2.
"""
from __future__ import annotations

import logging
import math

import numpy as np

from ..metrics.di import target_di_gaussian_db
from ..metrics.smoothness import band_flatness_detrended_db, ripple_detrended_db
from ..targets.spec import Target, validate_freq_weights
from . import terms as T
from .scalar import penalty_result, resolve_weights
from .terms import (ALL_KEYS, NAN_TERM_FILL, PENALTY_FAILED, WEIGHTED_KEYS)

log = logging.getLogger("hornlab_search.objective.scalar_v2")

__all__ = ["objective_v2", "freq_weight_vector"]


# ------------------------------------------------------------------ WP4: frequency weights

def freq_weight_vector(freqs_hz, target: Target) -> np.ndarray:
    """Per-frequency weight vector for objective v2.

    ``1.0`` everywhere when ``target.freq_weights`` is absent. Otherwise every frequency gets the
    product of all matching ``freq_weights['band_hz']`` intervals (``[lo_hz, hi_hz, w]``, both
    ends inclusive), so overlapping Hamming-style windows compose multiplicatively.

    Raises ``ValueError`` for a malformed mapping (``Target.from_dict`` validates YAML, but a
    hand-built ``Target`` can still carry one; ``objective_v2`` turns the error into a penalty).
    """
    f = np.asarray(freqs_hz, dtype=float)
    w = np.ones(f.shape, dtype=float)
    raw = getattr(target, "freq_weights", None)
    if raw is None:
        return w
    fw = validate_freq_weights(raw)
    for lo, hi, weight in fw["band_hz"]:
        w = np.where((f >= lo) & (f <= hi), w * float(weight), w)
    return w


# ------------------------------------------------------------------ NaN-safe means

def _plain_mean(x) -> tuple[float, int]:
    """(nanmean, number of non-finite entries). All non-finite -> (NAN_TERM_FILL, n)."""
    x = np.asarray(x, dtype=float)
    bad = ~np.isfinite(x)
    n = int(bad.sum())
    good = x[~bad]
    if good.size == 0:
        return NAN_TERM_FILL, n
    return float(np.mean(good)), n


def _weighted_mean(x, w) -> tuple[float, int]:
    """Weighted nanmean. All non-finite -> (NAN_TERM_FILL, n)."""
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    bad = ~np.isfinite(x)
    n = int(bad.sum())
    good = ~bad
    if not good.any():
        return NAN_TERM_FILL, n
    ww = w[good]
    if ww.shape != x[good].shape or not np.all(np.isfinite(ww)) or float(np.sum(ww)) <= 0.0:
        # Defence in depth: an unusable weight vector behaves like the plain mean.
        return float(np.mean(x[good])), n
    return float(np.sum(ww * x[good]) / np.sum(ww)), n


# ------------------------------------------------------------------ Response access

def _cut_arrays(resp, n_freqs: int):
    """(h_angles, v_angles, spl_h, spl_v) from a Response, or None if unusable."""
    if resp is None:
        return None
    try:
        ha = np.asarray(resp.h_angles_deg, dtype=float)
        va = np.asarray(resp.v_angles_deg, dtype=float)
        sh = np.asarray(resp.spl_h_db, dtype=float)
        sv = np.asarray(resp.spl_v_db, dtype=float)
    except Exception:  # noqa: BLE001 - a collapsed/absent view degrades, never fails
        return None
    if ha.ndim != 1 or va.ndim != 1 or sh.ndim != 2 or sv.ndim != 2:
        return None
    if sh.shape != (n_freqs, ha.size) or sv.shape != (n_freqs, va.size):
        return None
    if ha.size == 0 or va.size == 0:
        return None
    return ha, va, sh, sv


def _on_axis_index(resp, h_angles) -> int | None:
    """Index of the exact 0-degree sample, or None when the response is not usable."""
    try:
        i = int(resp.axis_index)
    except Exception:  # noqa: BLE001 - Response.axis_index asserts on a missing 0
        return None
    if not (0 <= i < h_angles.size) or abs(float(h_angles[i])) > 1e-9:
        return None
    return i


def _v2_ripple_values(metrics, resp, target: Target, band: np.ndarray):
    """Per-frequency ``ripple_h + ripple_v`` under v2, and whether the Response path was used."""
    f = np.asarray(metrics.freqs_hz, dtype=float)
    n = f.size
    arrays = _cut_arrays(resp, n)
    if arrays is not None:
        ha, va, sh, sv = arrays
        out = np.full(n, np.nan)
        try:
            for j in np.flatnonzero(band):
                out[j] = (ripple_detrended_db(ha, sh[j], target.coverage_h_deg)
                          + ripple_detrended_db(va, sv[j], target.coverage_v_deg))
            return out, True
        except Exception:  # noqa: BLE001 - malformed angles fall back to the v1 values
            log.debug("objective_v2: detrended ripple failed; using stored v1 ripple", exc_info=True)
    # Graceful degradation: the stored v1 ripple pair (band slicing happens at the call site).
    try:
        rh = np.asarray(metrics.ripple_h_db, dtype=float)
        rv = np.asarray(metrics.ripple_v_db, dtype=float)
        if rh.shape == rv.shape and rh.shape == f.shape:
            return rh + rv, False
    except Exception:  # noqa: BLE001
        pass
    return np.full(n, np.nan), False


def _v2_flat_value(metrics, resp, target: Target, band: np.ndarray) -> float:
    """Detrended on-axis flatness over the in-band frequencies."""
    f = np.asarray(metrics.freqs_hz, dtype=float)
    arrays = _cut_arrays(resp, f.size)
    if arrays is not None:
        ha, _va, sh, _sv = arrays
        ax = _on_axis_index(resp, ha)
        if ax is not None:
            try:
                on_axis = sh[:, ax]
                flat = band_flatness_detrended_db(f[band], on_axis[band])
                if np.isfinite(flat):
                    return float(flat)
            except Exception:  # noqa: BLE001
                log.debug("objective_v2: response flatness failed; using metrics.on_axis_db",
                          exc_info=True)
    try:
        on_axis = np.asarray(metrics.on_axis_db, dtype=float)
        flat = band_flatness_detrended_db(f[band], on_axis[band])
    except Exception:  # noqa: BLE001
        flat = float("nan")
    return float(flat) if np.isfinite(flat) else NAN_TERM_FILL


# ------------------------------------------------------------------ the objective

def objective_v2(metrics, resp, ok: bool, target: Target,
                 weights: dict) -> tuple[float, dict]:
    """Returns (J, terms). LOWER IS BETTER. NEVER raises, never returns inf or nan.

    ``resp`` is the solver Response the metrics came from (used for the detrended ripple and
    flatness); it may be None, in which case the stored v1 ripple arrays and ``metrics.on_axis_db``
    are used. ``terms`` has EXACTLY the v1 key set (``ALL_KEYS``), so downstream code does not need
    to know the objective version.
    """
    try:
        return _objective_v2(metrics, resp, ok, target, weights)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v2() failed; returning the failure penalty")
        return penalty_result(PENALTY_FAILED)


def _objective_v2(metrics, resp, ok, target, weights):
    if metrics is None or not ok:
        return penalty_result(PENALTY_FAILED)
    w = resolve_weights(weights)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    n_band = int(band.sum())
    if n_band == 0:
        log.warning("no solved frequency inside the band [%g, %g] Hz", target.band_lo_hz,
                    target.band_hi_hz)
        return penalty_result(PENALTY_FAILED, n_in_band=0)

    def b(x):
        return np.asarray(x, dtype=float)[band]

    # cov, dislope and load are identical to v1 (contract section 11).
    cov, _ = T.cov_term(b(metrics.bw_h_deg), b(metrics.bw_v_deg), target)
    dsl, _ = T.dislope_term(f[band], b(metrics.di_db), target)
    z = None if metrics.z_throat_real is None else b(metrics.z_throat_real)
    load, _ = T.load_term(z, target)

    # rip: mean_f(ripple_detrended_h + ripple_detrended_v), weighted under WP4 when asked.
    ripple_values, _used_resp = _v2_ripple_values(metrics, resp, target, band)
    if target.freq_weights is not None:
        rip, _ = _weighted_mean(ripple_values[band], freq_weight_vector(f, target)[band])
    else:
        rip, _ = _plain_mean(ripple_values[band])

    # di: v1 formula and aggregation against the Gaussian-beam reference, unless weight 0.
    if float(w["di"]) == 0.0:
        di = 0.0
        di_used = False
    else:
        ref = (float(target.di_target_db) if target.di_target_db is not None
               else target_di_gaussian_db(target.coverage_h_deg, target.coverage_v_deg))
        di_mean, _ = _plain_mean((b(metrics.di_db) - ref) ** 2)
        di = di_mean / 10.0
        di_used = True

    # flat: residual std after removing the log2-frequency tilt, over the whole in-band set.
    flat = _v2_flat_value(metrics, resp, target, band)

    # Frequencies with at least one unmeasurable input (same bookkeeping as v1).
    bad = np.zeros(n_band, dtype=bool)
    for arr in (metrics.bw_h_deg, metrics.bw_v_deg, metrics.on_axis_db):
        bad |= ~np.isfinite(b(arr))
    bad |= ~np.isfinite(ripple_values[band])
    if di_used:
        bad |= ~np.isfinite(b(metrics.di_db))
    if z is not None:
        bad |= ~np.isfinite(z)

    t = {"cov": cov, "rip": rip, "di": di, "dislope": dsl, "flat": flat, "load": load,
         "penalty": 0.0}
    if not all(math.isfinite(t[k]) for k in WEIGHTED_KEYS):
        return penalty_result(PENALTY_FAILED, n_in_band=n_band)
    total = sum(w[k] * t[k] for k in WEIGHTED_KEYS)
    if not math.isfinite(total):          # defence in depth: never hand CMA-ES a nan or inf
        return penalty_result(PENALTY_FAILED, n_in_band=n_band)
    t["total"] = float(total)
    t["n_nan"] = int(bad.sum())
    t["n_in_band"] = n_band
    t["di_estimated"] = 1.0 if metrics.di_source == "cuts_estimate" else 0.0
    assert set(t) == set(ALL_KEYS)
    return float(total), t
