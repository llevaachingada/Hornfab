"""Response -> MetricSet. Frozen definitions: 01_CONTRACTS.md section 10."""
from __future__ import annotations

import logging
import math

import numpy as np

from ..constants import BESSEL_J1P_11, C_AIR, KEELE_K
from ..targets.spec import Target
from ..types import MetricSet, Response
from .di import di_from_balloon, di_from_cuts, di_slope_db_per_decade
from .polar import DB_FLOOR, beamwidth_deg
from .smoothness import band_flatness_db, ripple_db

log = logging.getLogger("hornlab_search.metrics.compute")

#: The exact key set of MetricSet.scalars. The report and the dataset index by key.
SCALAR_KEYS = (
    "n_freqs", "di_source", "n_multilobe_h", "n_multilobe_v", "n_nan_ripple",
    "bw_h_mean_deg", "bw_v_mean_deg", "di_mean_db", "di_slope_db_per_dec",
    "ripple_mean_db", "flatness_db", "f_break_h_hz", "f_break_v_hz", "f11_hz",
)

_warned_cuts_estimate = False


def reset_warning_state() -> None:
    """Re-arm the once-per-run cuts_estimate warning. The run entry point calls this."""
    global _warned_cuts_estimate
    _warned_cuts_estimate = False


def _nanmean(x) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    return float(np.mean(x)) if x.size else float("nan")


def _check_rows(name: str, arr, nf: int) -> np.ndarray:
    a = np.asarray(arr, dtype=float)
    if a.ndim != 2 or a.shape[0] != nf:
        raise ValueError(f"compute_metrics: {name} has shape {a.shape}, expected ({nf}, n) "
                         "to match resp.freqs_hz")
    return a


def compute_metrics(resp: Response, target: Target, *, mouth_h_m: float | None = None,
                    mouth_v_m: float | None = None,
                    throat_radius_m: float | None = None) -> MetricSet:
    """Metrics over resp.freqs_hz, which holds only what was actually solved.

    di_source is 'balloon' when both resp.spl_balloon_db and resp.balloon_dirs are
    present (equal weights, so the balloon must be equal-area), else 'cuts_estimate'
    with one WARNING per run (see reset_warning_state).

    Aggregates (the *_mean_*, slope and flatness scalars) use the frequencies inside
    [target.band_lo_hz, target.band_hi_hz], or all frequencies if none fall inside.
    The per-frequency arrays always cover every solved frequency.

    A dead frequency (all -inf) gives bw 180.0, DI 0.0, on-axis -120 dB (re the band
    mean) and ripple nan, so only the ripple arrays can hold nan, and
    scalars['n_nan_ripple'] counts them.

    Design checks (never constraints), nan when the input is not supplied:
      f_break = KEELE_K / (mouth_dimension_m * coverage_deg)
      f11     = BESSEL_J1P_11 * C_AIR / (2 pi throat_radius_m)
    """
    global _warned_cuts_estimate
    freqs = np.asarray(resp.freqs_hz, dtype=float)
    nf = freqs.size
    spl_h = _check_rows("spl_h_db", resp.spl_h_db, nf)
    spl_v = _check_rows("spl_v_db", resp.spl_v_db, nf)
    ax = resp.axis_index
    h_ang = np.asarray(resp.h_angles_deg, dtype=float)
    v_ang = np.asarray(resp.v_angles_deg, dtype=float)

    use_balloon = resp.spl_balloon_db is not None and resp.balloon_dirs is not None
    bal = _check_rows("spl_balloon_db", resp.spl_balloon_db, nf) if use_balloon else None
    di_source = "balloon" if use_balloon else "cuts_estimate"
    if not use_balloon and not _warned_cuts_estimate:
        _warned_cuts_estimate = True
        log.warning("no balloon in the response: DI is a cuts_estimate (separable-rectangle "
                    "assumption). No checkpoint may be passed on it.")

    bw_h = np.empty(nf)
    bw_v = np.empty(nf)
    n_h = np.zeros(nf, dtype=int)
    n_v = np.zeros(nf, dtype=int)
    di = np.empty(nf)
    rip_h = np.empty(nf)
    rip_v = np.empty(nf)
    for i in range(nf):
        bw_h[i], n_h[i] = beamwidth_deg(h_ang, spl_h[i])
        bw_v[i], n_v[i] = beamwidth_deg(v_ang, spl_v[i])
        if use_balloon:
            di[i] = di_from_balloon(bal[i], spl_h[i, ax])
        else:
            di[i] = di_from_cuts(bw_h[i], bw_v[i])
        rip_h[i] = ripple_db(h_ang, spl_h[i], target.coverage_h_deg)
        rip_v[i] = ripple_db(v_ang, spl_v[i], target.coverage_v_deg)

    band = (freqs >= target.band_lo_hz) & (freqs <= target.band_hi_hz)
    if not band.any():
        band = np.ones(nf, dtype=bool)

    axis_db = spl_h[:, ax].copy()
    finite = np.isfinite(axis_db)
    in_band_finite = finite & band
    if in_band_finite.any():
        ref = float(np.mean(axis_db[in_band_finite]))
    elif finite.any():
        ref = float(np.mean(axis_db[finite]))
    else:
        ref = 0.0
    on_axis = np.where(finite, np.maximum(axis_db - ref, DB_FLOOR), DB_FLOOR)

    z_real = None if resp.z_throat is None else np.real(np.asarray(resp.z_throat)).astype(float)

    slope = di_slope_db_per_decade(freqs[band], di[band])
    if math.isnan(slope) and band.sum() < nf:
        slope = di_slope_db_per_decade(freqs, di)

    def _fb(mouth, cov):
        if mouth is None or not float(mouth) > 0.0:
            return float("nan")
        return float(KEELE_K / (float(mouth) * cov))

    if throat_radius_m is not None and float(throat_radius_m) > 0.0:
        f11 = float(BESSEL_J1P_11 * C_AIR / (2.0 * math.pi * float(throat_radius_m)))
    else:
        f11 = float("nan")

    scalars = {
        "n_freqs": int(nf),
        "di_source": di_source,
        "n_multilobe_h": int(np.sum(n_h > 2)),
        "n_multilobe_v": int(np.sum(n_v > 2)),
        "n_nan_ripple": int(np.isnan(rip_h).sum() + np.isnan(rip_v).sum()),
        "bw_h_mean_deg": _nanmean(bw_h[band]),
        "bw_v_mean_deg": _nanmean(bw_v[band]),
        "di_mean_db": _nanmean(di[band]),
        "di_slope_db_per_dec": float(slope),
        "ripple_mean_db": _nanmean(np.concatenate([rip_h[band], rip_v[band]])),
        "flatness_db": band_flatness_db(on_axis[band]),
        "f_break_h_hz": _fb(mouth_h_m, target.coverage_h_deg),
        "f_break_v_hz": _fb(mouth_v_m, target.coverage_v_deg),
        "f11_hz": f11,
    }
    assert set(scalars) == set(SCALAR_KEYS)

    return MetricSet(
        freqs_hz=freqs.copy(),
        bw_h_deg=bw_h, bw_v_deg=bw_v,
        di_db=di, di_source=di_source,
        ripple_h_db=rip_h, ripple_v_db=rip_v,
        on_axis_db=on_axis,
        z_throat_real=z_real,
        scalars=scalars,
    )
