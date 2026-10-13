"""The scalar objective J (01_CONTRACTS section 11). LOWER IS BETTER. ``objective`` never raises.

    J = w_cov*cov + w_rip*rip + w_di*di + w_dislope*dislope + w_flat*flat + w_load*load + penalty

``terms`` holds the RAW (unweighted) terms so they can be compared with each other and with the
weights; the weighted contribution of term k is ``weights[k] * terms[k]`` and ``terms['total']``
is their sum plus ``terms['penalty']``. ``weighted_terms`` does that multiplication.

Only frequencies inside ``[target.band_lo_hz, target.band_hi_hz]`` count: the solve grid
deliberately extends past the band so the report can show what happens outside it without
letting it drive the search.
"""
from __future__ import annotations

import logging
import math

import numpy as np

from ..targets.spec import Target
from ..types import MetricSet
from . import terms as T
from .terms import (ALL_KEYS, DEFAULT_WEIGHTS, PENALTY_FAILED, PENALTY_INVALID, TERM_KEYS,
                    WEIGHTED_KEYS)

log = logging.getLogger("hornlab_search.objective.scalar")

__all__ = ["objective", "penalty_result", "weighted_terms", "resolve_weights", "PENALTY_FAILED",
           "PENALTY_INVALID", "TERM_KEYS", "ALL_KEYS", "WEIGHTED_KEYS", "DEFAULT_WEIGHTS"]


def resolve_weights(weights: dict | None) -> dict:
    """Contract defaults overlaid with ``weights``. Unknown keys are ignored with a WARNING
    (a typo in a YAML must not be silent, and the objective must not raise)."""
    out = dict(DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in DEFAULT_WEIGHTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)", k, sorted(DEFAULT_WEIGHTS))
    return out


def _blank_terms() -> dict:
    t = {k: 0.0 for k in ALL_KEYS}
    t["n_nan"] = 0
    t["n_in_band"] = 0
    return t


def penalty_result(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    """(J, terms) of a candidate that produced no metrics: all terms 0.0, penalty = value."""
    t = _blank_terms()
    t["penalty"] = float(value)
    t["total"] = float(value)
    t["n_in_band"] = int(n_in_band)
    return float(value), t


def weighted_terms(terms: dict, weights: dict | None) -> dict:
    """{cov, rip, di, dislope, flat, load, penalty, total} with the weights applied."""
    w = resolve_weights(weights)
    out = {k: w[k] * float(terms.get(k, 0.0)) for k in WEIGHTED_KEYS}
    out["penalty"] = float(terms.get("penalty", 0.0))
    out["total"] = sum(out[k] for k in WEIGHTED_KEYS) + out["penalty"]
    return out


def objective(metrics: MetricSet | None, ok: bool, target: Target,
              weights: dict) -> tuple[float, dict]:
    """Returns (J, terms). LOWER IS BETTER. NEVER raises, never returns inf or nan.

    terms always has exactly ``ALL_KEYS``: the six raw terms (0.0 when skipped), ``penalty``,
    ``total``, ``n_nan`` (in-band frequencies with an unmeasurable input), ``n_in_band`` and
    ``di_estimated`` (1.0 when DI came from the cuts estimate, 0.0 for the balloon).
    """
    try:
        return _objective(metrics, ok, target, weights)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective() failed; returning the failure penalty")
        return penalty_result(PENALTY_FAILED)


def _objective(metrics, ok, target, weights):
    if metrics is None or not ok:
        return penalty_result(PENALTY_FAILED)
    w = resolve_weights(weights)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    n_band = int(band.sum())
    if n_band == 0:
        # No solved frequency inside the band: nothing to score. A configuration error, scored
        # as a failure so the search sees it immediately instead of rewarding an empty set.
        log.warning("no solved frequency inside the band [%g, %g] Hz", target.band_lo_hz,
                    target.band_hi_hz)
        return penalty_result(PENALTY_FAILED, n_in_band=0)

    def b(x):
        return np.asarray(x, dtype=float)[band]

    cov, _ = T.cov_term(b(metrics.bw_h_deg), b(metrics.bw_v_deg), target)
    rip, _ = T.rip_term(b(metrics.ripple_h_db), b(metrics.ripple_v_db))
    di, _ = T.di_term(b(metrics.di_db), target)
    dsl, _ = T.dislope_term(f[band], b(metrics.di_db), target)
    flat, _ = T.flat_term(b(metrics.on_axis_db))
    z = None if metrics.z_throat_real is None else b(metrics.z_throat_real)
    load, _ = T.load_term(z, target)

    # Frequencies with at least one unmeasurable input (bandwidth, ripple, DI, level, z).
    bad = np.zeros(n_band, dtype=bool)
    for arr in (metrics.bw_h_deg, metrics.bw_v_deg, metrics.ripple_h_db, metrics.ripple_v_db,
                metrics.di_db, metrics.on_axis_db):
        bad |= ~np.isfinite(b(arr))
    if z is not None:
        bad |= ~np.isfinite(z)

    t = {"cov": cov, "rip": rip, "di": di, "dislope": dsl, "flat": flat, "load": load,
         "penalty": 0.0}
    total = sum(w[k] * t[k] for k in WEIGHTED_KEYS)
    if not math.isfinite(total):          # defence in depth: never hand CMA-ES a nan or inf
        return penalty_result(PENALTY_FAILED, n_in_band=n_band)
    t["total"] = float(total)
    t["n_nan"] = int(bad.sum())
    t["n_in_band"] = n_band
    t["di_estimated"] = 1.0 if metrics.di_source == "cuts_estimate" else 0.0
    assert set(t) == set(ALL_KEYS)
    return float(total), t
