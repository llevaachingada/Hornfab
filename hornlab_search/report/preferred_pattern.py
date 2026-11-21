"""Report-only pattern and impedance diagnostics over stored BEM samples.

These descriptive statistics do not alter an objective or establish system performance.
"""
from __future__ import annotations

import numpy as np

from ..metrics.acoustic_v2 import _sustained_onset, loading_onset
from ..metrics.pattern_quality import balloon_lobe_map, cut_pattern_quality


def _frequencies(response):
    f = np.asarray(response.freqs_hz, float)
    if f.ndim != 1 or not f.size or not np.isfinite(f).all() or np.any(np.diff(f) <= 0):
        raise ValueError("frequencies must be finite, nonempty and strictly increasing")
    return f


def _band(f, band):
    lo, hi = map(float, band)
    if not np.isfinite([lo, hi]).all() or lo <= 0 or hi < lo:
        raise ValueError("band must be finite, positive, and ordered")
    mask = (f >= lo) & (f <= hi)
    if not mask.any():
        raise ValueError("band contains no solved frequencies")
    return mask


def preferred_pattern_diagnostics(response, *, band_hz=(1500., 8000.), h_target_deg=80.,
                                  v_target_deg=50., h_corridor_deg=(60., 90.),
                                  v_corridor_deg=(40., 60.), dwell=3):
    """Return H/V per-frequency cut evidence, band errors and sustained corridor onset.

    Errors use only uncensored boresight-connected first-crossing widths; missing
    samples are counted and prevent an onset through the observed band end. Means
    and RMS are equally weighted over solved frequencies, not bandwidth integrals.
    Onset examines all stored samples through band_hz's upper edge, with no
    extrapolation. Balloon map is coarse and may be unavailable.
    """
    f = _frequencies(response)
    use = _band(f, band_hz)
    if not isinstance(dwell, int) or dwell < 1:
        raise ValueError("dwell must be a positive integer")
    result = {"band_hz": list(map(float, band_hz)), "frequencies_hz": f.tolist(),
              "definition": "boresight-connected -6 dB crossing; equal solved-frequency weighting",
              "limitations": "Sampled cuts and balloon cannot resolve features between angular or frequency samples; no interpolation across frequency or objective change.",
              "planes": {}}
    for name, angles, cuts, target, corridor in (
        ("h", response.h_angles_deg, response.spl_h_db, h_target_deg, h_corridor_deg),
        ("v", response.v_angles_deg, response.spl_v_db, v_target_deg, v_corridor_deg)):
        target = float(target)
        lo, hi = map(float, corridor)
        if not np.isfinite([target, lo, hi]).all() or target <= 0 or lo < 0 or hi < lo:
            raise ValueError("target and corridor must be finite and ordered")
        cuts = np.asarray(cuts, float)
        if cuts.ndim != 2 or cuts.shape[0] != f.size:
            raise ValueError(f"{name} cuts must have one row per frequency")
        rows = [cut_pattern_quality(angles, row, coverage_deg=target) for row in cuts]
        widths = [row["connected"]["width_deg"] for row in rows]
        w = np.array([np.nan if x is None else x for x in widths])
        valid = use & np.isfinite(w)
        errors = w[valid] - target
        through_end = f <= float(band_hz[1])
        onset = _sustained_onset(f[through_end], (np.isfinite(w) & (w >= lo) & (w <= hi))[through_end], dwell)
        onset.update(corridor_deg=[lo, hi], dwell=dwell,
                     note="sustained over every stored sample through band upper edge; widths only, inspect lobe flags separately")
        result["planes"][name] = {
            "target_deg": target, "width_deg": widths,
            "mean_signed_error_deg": float(np.mean(errors)) if errors.size else None,
            "rms_error_deg": float(np.sqrt(np.mean(errors**2))) if errors.size else None,
            "valid_samples_in_band": int(valid.sum()), "total_samples_in_band": int(use.sum()),
            "corridor_onset": onset, "cut_quality": rows,
        }
    if response.spl_balloon_db is None or response.balloon_dirs is None:
        result["balloon"] = {"status": "missing"}
    else:
        try:
            result["balloon"] = balloon_lobe_map(response.spl_balloon_db, response.balloon_dirs,
                                                  (response.meta or {}).get("balloon_grid"))
        except ValueError as exc:
            result["balloon"] = {"status": "unavailable", "reason": str(exc)}
    return result


def _extrema(freq, values):
    """Sampled global and strict local extrema; no inferred resonance between points."""
    valid = np.isfinite(values)
    if not valid.any():
        return {"status": "missing"}
    idx = np.flatnonzero(valid)
    imin, imax = idx[np.argmin(values[valid])], idx[np.argmax(values[valid])]
    def point(i):
        return {"frequency_hz": float(freq[i]), "value": float(values[i])}
    peaks, troughs = [], []
    for i in range(1, len(values) - 1):
        if valid[i-1:i+2].all():
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(point(i))
            if values[i] < values[i-1] and values[i] < values[i+1]:
                troughs.append(point(i))
    return {"status": "valid", "min": point(imin), "max": point(imax),
            "peak_to_trough": float(values[imax] - values[imin]),
            "local_peaks": peaks, "local_troughs": troughs}


def impedance_diagnostics(response, *, band_hz=(900., 8000.), onset_threshold=0.7, dwell=2):
    """Report sampled normalized resistance/reactance and sustained loading onset."""
    f = _frequencies(response)
    mask = _band(f, band_hz)
    threshold = float(onset_threshold)
    if not np.isfinite(threshold) or not isinstance(dwell, int) or dwell < 1:
        raise ValueError("onset threshold must be finite and dwell a positive integer")
    result = {"band_hz": list(map(float, band_hz)), "normalization": "z_throat / rho c as stored",
              "limitations": "Equal sample mean; peaks and onset are sampled, not continuous. Linear impedance alone does not establish audible ringing, driver distortion, or system power transfer."}
    if response.z_throat is None:
        result.update(status="missing", loading_onset={"status": "missing"})
        return result
    z = np.asarray(response.z_throat, complex)
    if z.shape != f.shape:
        raise ValueError("impedance must have one value per frequency")
    band_z, band_f = z[mask], f[mask]
    real = np.real(band_z)
    finite = np.isfinite(real)
    result.update(status="valid" if np.isfinite(z).all() else "partial",
                  frequencies_hz=band_f.tolist(),
                  resistance=[float(x) if np.isfinite(x) else None for x in real],
                  reactance=[float(x) if np.isfinite(x) else None for x in np.imag(band_z)],
                  mean_resistance=float(np.mean(real[finite])) if finite.any() else None,
                  resistance_extrema=_extrema(band_f, real),
                  reactance_extrema=_extrema(band_f, np.imag(band_z)),
                  loading_onset=loading_onset(f[f <= band_hz[1]], z[f <= band_hz[1]], threshold, dwell))
    return result
