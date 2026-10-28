"""Report-only horn loudness readout: how loud a horn plays for the SAME throat motion (P12, 2026-10-27).

The solver drives the throat with unit normal acceleration and stores the complex pressure it
produces (``Response.p_h``) plus the normalised throat impedance ``z_throat``. That is enough to say,
with no driver data and no new solve, how much output one horn gives relative to another on the same
driver - the horn's own share of sensitivity. Two curves and three scalars:

* ``loading_db`` = 10 log10(Re z): radiated power versus a fully loaded throat (Re z = 1) for the same
  throat velocity. Around cutoff Re z can exceed 1, so this can be slightly positive.
* ``onaxis_db_per_mps``: on-axis SPL at ``ref_distance_m`` (default 1 m) for 1 m/s rms uniform throat
  velocity, i.e. 20 log10(|p_axis| * omega * (r / r_ref) / p_ref). Unit acceleration -> unit velocity is
  |a| = omega |v| (time convention drops out of magnitudes). Extrapolating the stored 2 m arc to 1 m by
  1/r is the usual sensitivity convention, not a near-field claim. Comparable between horns with the
  same throat area (same driver); it includes the directivity, as an on-axis measurement does.
* ``output_gap_at_f0_db``: worst case over solved f >= 0.95 f0 of max(0, 10 log10(Z_LOADED / Re z)),
  the quantity proposed for scoring in docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md
  s2.1 (here report-only). ``f_loaded_hz``: lowest solved frequency from which Re z stays >= 0.5
  (within ~3 dB of a loaded throat), roughly the lowest sensible crossover for the horn.
* ``throat_area_m2`` / ``throat_diameter_equiv_mm``: area of the source surface the solver actually drove
  (mesh tag area x symmetry copies) and the diameter of a circle of that area. This is the area the
  impedance is normalised by; it is NOT a shape check (OSSE/R-OSSE ``aspect_ratio`` also stretches the
  throat into an ellipse - measured 24 x 36 mm on a 36 mm brief; tools/loudness_report.py reads the throat
  width x height from the mesh).

Upper-bound caveat: a real compression driver moves a little more when the load drops, so the true
output gap is somewhat smaller than ``loading_db`` says; ``hornlab_search.driver`` gives the per-driver
number. Stored data check (2026-10-27): throat power 0.5 rho c Re(z) A |v|^2 equals the power integrated
over the stored 2 m balloon within 0.0-0.4 dB, 500 Hz - 8 kHz, on four horns.

Pure numpy. ``horn_loudness`` never raises: anything it cannot compute is NaN.
"""
from __future__ import annotations

import logging
import math

import numpy as np

from ..constants import REF_P
from ..mesh.sizing import QUADRANT_FACTOR

log = logging.getLogger("hornlab_search.metrics.loudness")

#: Solver physical tag of the driven throat surface (hornlab_search.solve.beat.SOURCE_TAG).
SOURCE_TAG = "2"
#: Re z that counts as loaded for the output gap (-1.5 dB free), the research report's z_min.
Z_LOADED = 0.7
#: Re z that counts as "within ~3 dB of loaded" for ``f_loaded_hz``.
Z_HALF = 0.5
#: Frequencies down to this fraction of f0 count as "at f0" (the screen grid rarely hits f0 exactly).
F0_SLACK = 0.95

SCALAR_KEYS = ("output_gap_at_f0_db", "f_loaded_hz", "throat_area_m2", "throat_diameter_equiv_mm")


def throat_area_m2(resp) -> float:
    """Full-model area of the driven throat surface: the mesh tag area times the symmetry copies.
    NaN when the response carries no mesh metadata."""
    try:
        meta = resp.meta or {}
        area = float(meta["physical_tag_areas_m2"][SOURCE_TAG])
        q = meta.get("quadrants")
        factor = QUADRANT_FACTOR[str(q)] if q is not None else 1
        out = area * factor
        return out if out > 0.0 and math.isfinite(out) else float("nan")
    except Exception:  # noqa: BLE001 - report-only
        return float("nan")


def onaxis_pressure_per_accel(resp) -> np.ndarray:
    """|p| on axis per unit throat acceleration, at the stored distance. From the complex ``p_h`` when
    present, else from ``spl_h_db`` (dB re 20 uPa, the same magnitude)."""
    ax = resp.axis_index
    if resp.p_h is not None:
        return np.abs(np.asarray(resp.p_h)[:, ax])
    return REF_P * 10.0 ** (np.asarray(resp.spl_h_db, dtype=float)[:, ax] / 20.0)


def output_gap_db(freqs_hz, z_real, f0_hz) -> float:
    """Worst case over solved f >= F0_SLACK * f0 of max(0, 10 log10(Z_LOADED / Re z)). NaN if no data."""
    f = np.asarray(freqs_hz, dtype=float)
    z = np.asarray(z_real, dtype=float)
    if f0_hz is None or not np.isfinite(f0_hz):
        return float("nan")
    sel = (f >= F0_SLACK * float(f0_hz)) & np.isfinite(z)
    if not sel.any():
        return float("nan")
    gap = 10.0 * np.log10(Z_LOADED / np.maximum(z[sel], 1e-6))
    return float(max(0.0, np.max(gap)))


def loaded_from_hz(freqs_hz, z_real, threshold: float = Z_HALF) -> float:
    """Lowest solved frequency from which Re z stays >= ``threshold`` (NaN if it never does)."""
    f = np.asarray(freqs_hz, dtype=float)
    z = np.asarray(z_real, dtype=float)
    ok = np.isfinite(z) & (z >= threshold)
    for i in range(f.size):
        if ok[i:].all():
            return float(f[i])
    return float("nan")


def horn_loudness(resp, *, f0_hz: float | None = None, ref_distance_m: float = 1.0) -> dict:
    """Horn-only loudness readout of one stored Response (see the module docstring).

    Returns ``freqs_hz``, ``re_z``, ``loading_db``, ``onaxis_db_per_mps`` (arrays, NaN where unknown)
    and the ``SCALAR_KEYS`` scalars."""
    nan = float("nan")
    f = np.asarray(getattr(resp, "freqs_hz", []), dtype=float)
    out = {"freqs_hz": f, "re_z": np.full(f.shape, np.nan), "loading_db": np.full(f.shape, np.nan),
           "onaxis_db_per_mps": np.full(f.shape, np.nan), **{k: nan for k in SCALAR_KEYS}}
    try:
        area = throat_area_m2(resp)
        out["throat_area_m2"] = area
        if np.isfinite(area):
            out["throat_diameter_equiv_mm"] = 2000.0 * math.sqrt(area / math.pi)
        if resp.z_throat is not None:
            zr = np.real(np.asarray(resp.z_throat))
            out["re_z"] = zr
            with np.errstate(divide="ignore", invalid="ignore"):
                out["loading_db"] = np.where(zr > 0.0, 10.0 * np.log10(np.maximum(zr, 1e-12)), np.nan)
            out["output_gap_at_f0_db"] = output_gap_db(f, zr, f0_hz)
            out["f_loaded_hz"] = loaded_from_hz(f, zr)
        r = float((resp.meta or {}).get("distance_m", nan))
        p_a = onaxis_pressure_per_accel(resp)
        omega = 2.0 * np.pi * f
        with np.errstate(divide="ignore", invalid="ignore"):
            out["onaxis_db_per_mps"] = 20.0 * np.log10(p_a * omega * (r / float(ref_distance_m)) / REF_P)
    except Exception:  # noqa: BLE001 - report-only, never raises
        log.debug("horn_loudness failed", exc_info=True)
    return out
