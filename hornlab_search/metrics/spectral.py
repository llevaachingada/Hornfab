"""Fixed-angle spectral ripple audit for stored responses. REPORT-ONLY.

These are pure functions over already-stored response arrays. They are deliberately NOT part of
any objective: nothing here may change a stored ``J``. The audit fits a low-order polynomial in
``log2(f)`` to an off-axis minus on-axis normalised response at one fixed angle and reports the
residual spread. See ``tools/analysis/spectral_ripple_audit.py`` for the CLI and
``docs/research/ripple_hf_2026-11-19/HANDOFF_2026-11-19.md`` for the motivating handoff.

Conventions (READ BEFORE USING THE NUMBERS)
-------------------------------------------
* Normalisation: ``n(f) = spl_db[f, j] - spl_db[f, i0]`` where ``i0`` is the sample nearest the
  reference angle (default 0 deg). This is the off-axis response relative to on-axis.
* Detrend: least-squares polynomial of order ``detrend_order`` in ``x = log2(f)``. A quadratic
  (order 2) removes a smooth drive tilt plus a constant slope; orders 1 and 3 are provided so a
  caller can show rank stability under fit order.
* Residual spread: the POPULATION root-mean-square, ``sqrt(mean(residual ** 2))``. Because the
  least-squares residual from an intercept-bearing design is mean-zero, this equals the population
  standard deviation (``ddof=0``). The repo's sample-std convention in
  ``metrics/smoothness.py`` (``ddof = n_params``) is deliberately NOT reused here: this module is a
  report-only diagnostic, and changing it must never move a stored objective value.
* Reference model: ``reference="trend"`` (default) detrends with a polynomial in ``log2(f)``. This
  is an EXPLORATORY removal of the drive tilt and has no standards backing behind the exact order.
  ``reference="band_mean"`` subtracts the mean of the normalised dB over the band; this is the
  deviation-from-band-mean smoothness definition used by IEC 60268-5 section 20.6 and Klippel
  Application Note 40. Neither reference is a hearing-weighted score; both are report-only.
* Refusal: a missing/unreachable angle sample, a band with fewer than ``detrend_order + 3``
  samples (``dof < 2``), or any non-finite member of the band returns ``rms_db = nan`` together
  with a short ``reason`` string rather than raising. Shape problems (wrong array ranks/dims) are
  programming errors and do raise ``ValueError``.
"""
from __future__ import annotations

import numpy as np

#: Default reporting band from the 2026-11-19 handoff (10 stored samples in the archive).
DEFAULT_BAND_HZ = (1065.0, 4832.5)

#: A nearest angle sample farther than this is treated as missing.
ANGLE_MATCH_TOL_DEG = 0.5


def _nearest_sample(angles_deg, target_deg):
    """Return ``(index, deviation)`` for the angle sample nearest ``target_deg``.

    ``deviation`` is ``|angle - target|`` in degrees. An empty angle array returns ``(None, inf)``.
    """
    a = np.asarray(angles_deg, dtype=float)
    if a.size == 0:
        return None, float("inf")
    i = int(np.argmin(np.abs(a - target_deg)))
    return i, abs(float(a[i]) - float(target_deg))


def _validate_cut(freqs_hz, spl_db, angles_deg):
    """Validate a cut/axis pair and return float ``(freqs, spl, angles)``."""
    f = np.asarray(freqs_hz, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    a = np.asarray(angles_deg, dtype=float)
    if f.ndim != 1:
        raise ValueError(f"spectral: freqs_hz must be 1-D, got shape {f.shape}")
    if a.ndim != 1:
        raise ValueError(f"spectral: angles_deg must be 1-D, got shape {a.shape}")
    if s.ndim != 2 or s.shape != (f.size, a.size):
        raise ValueError(
            f"spectral: spl_db must have shape {(f.size, a.size)}, got {s.shape}")
    return f, s, a


def _band_mask(freqs_hz, band_hz):
    lo, hi = float(band_hz[0]), float(band_hz[1])
    return (freqs_hz >= lo) & (freqs_hz <= hi)


def fixed_angle_residual_curve(freqs_hz, spl_db, angles_deg, angle_deg,
                               ref_angle_deg=0.0, band_hz=DEFAULT_BAND_HZ,
                               detrend_order=2, reference="trend"):
    """Residual spread of one fixed-angle off-axis response about a reference model.

    Parameters
    ----------
    freqs_hz, angles_deg : 1-D arrays
        Frequency and cut-angle sample grids.
    spl_db : 2-D array, shape ``(len(freqs_hz), len(angles_deg))``
        Stored levels (dB) for one axis; column ``j`` is the fixed-angle cut.
    angle_deg : float
        Target off-axis angle. The nearest stored sample is used; if it is more than
        :data:`ANGLE_MATCH_TOL_DEG` away the call refuses (``rms_db = nan``).
    ref_angle_deg : float
        Reference (on-axis) angle. Same nearest-sample rule.
    band_hz : (lo, hi)
        Inclusive frequency band used for the fit.
    detrend_order : int
        Polynomial order in ``log2(f)``; used only when ``reference="trend"``.
    reference : {"trend", "band_mean"}
        ``"trend"`` (default) removes a polynomial in ``log2(f)``; this is an exploratory detrend.
        ``"band_mean"`` subtracts the mean of the normalised dB over the band, the
        deviation-from-band-mean smoothness definition of IEC 60268-5 section 20.6 / Klippel
        Application Note 40. ``detrend_order`` is ignored for ``band_mean`` and ``n_params = 1``.
        Neither reference is a hearing-weighted score.

    Returns
    -------
    dict
        ``angle_deg``, ``ref_angle_deg``, ``reference``, ``rms_db``, ``max_abs_db``, ``n``,
        ``n_params``, ``dof``, ``freqs_hz``, ``normalized_db``, ``residual_db``, ``reason``. Also
        carries ``angle_target_deg`` and ``ref_angle_target_deg`` so a caller can see any grid
        snapping. On refusal the band arrays are empty and ``rms_db``/``max_abs_db`` are ``nan``.

    Notes
    -----
    ``rms_db`` is the population RMS (``ddof=0``) of the fit residual, as documented in the module
    docstring. For the ``band_mean`` reference the residual is exactly mean-zero, so this equals
    the population std.
    """
    f, s, a = _validate_cut(freqs_hz, spl_db, angles_deg)
    if reference not in ("trend", "band_mean"):
        raise ValueError(
            f"spectral: reference must be 'trend' or 'band_mean', got {reference!r}")
    order = int(detrend_order)
    if order < 0:
        raise ValueError(f"spectral: detrend_order must be >= 0, got {order}")
    n_params = 1 if reference == "band_mean" else order + 1
    out = {
        "angle_deg": float(angle_deg),
        "ref_angle_deg": float(ref_angle_deg),
        "angle_target_deg": float(angle_deg),
        "ref_angle_target_deg": float(ref_angle_deg),
        "reference": reference,
        "rms_db": float("nan"),
        "max_abs_db": float("nan"),
        "n": 0,
        "n_params": n_params,
        "dof": 0,
        "freqs_hz": np.array([], dtype=float),
        "normalized_db": np.array([], dtype=float),
        "residual_db": np.array([], dtype=float),
        "reason": None,
    }

    band = _band_mask(f, band_hz)
    n_band = int(band.sum())
    fb = f[band]
    if n_band == 0:
        out["reason"] = f"no samples in band {float(band_hz[0])}-{float(band_hz[1])} Hz"
        return out
    if not np.all(np.isfinite(fb)) or np.any(fb <= 0.0):
        out["reason"] = "non-positive or non-finite frequency in band (log2 undefined)"
        return out

    j, j_dev = _nearest_sample(a, angle_deg)
    i0, i0_dev = _nearest_sample(a, ref_angle_deg)
    if j is None or j_dev > ANGLE_MATCH_TOL_DEG:
        out["reason"] = (
            f"no angle sample within {ANGLE_MATCH_TOL_DEG:g} deg of {float(angle_deg):g}")
        return out
    if i0 is None or i0_dev > ANGLE_MATCH_TOL_DEG:
        out["reason"] = (
            f"no reference sample within {ANGLE_MATCH_TOL_DEG:g} deg of "
            f"{float(ref_angle_deg):g}")
        return out
    out["angle_deg"] = float(a[j])
    out["ref_angle_deg"] = float(a[i0])

    y = s[band, j] - s[band, i0]
    if not np.all(np.isfinite(y)):
        out["reason"] = "non-finite level in the band at the selected angle(s)"
        return out

    out["n"] = n_band
    out["dof"] = n_band - n_params
    if out["dof"] < 2:
        out["reason"] = (
            f"insufficient degrees of freedom: n={n_band}, params={n_params}, dof={out['dof']}")
        return out

    if reference == "band_mean":
        residual = y - np.mean(y)
    else:
        x = np.log2(fb)
        design = np.vander(x, N=n_params, increasing=True)
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual = y - design @ coef
    rms = float(np.sqrt(np.mean(residual ** 2)))
    out.update({
        "rms_db": rms,
        "max_abs_db": float(np.max(np.abs(residual))),
        "freqs_hz": fb,
        "normalized_db": y,
        "residual_db": residual,
    })
    return out


def fixed_angle_residual_db(freqs_hz, spl_db, angles_deg, angle_deg,
                            ref_angle_deg=0.0, band_hz=DEFAULT_BAND_HZ,
                            detrend_order=2, reference="trend") -> float:
    """Scalar ``rms_db`` from :func:`fixed_angle_residual_curve` (``nan`` on refusal)."""
    return fixed_angle_residual_curve(
        freqs_hz, spl_db, angles_deg, angle_deg, ref_angle_deg=ref_angle_deg,
        band_hz=band_hz, detrend_order=detrend_order, reference=reference)["rms_db"]


def symmetric_pair_report(freqs_hz, spl_db, angles_deg, band_hz=DEFAULT_BAND_HZ,
                          detrend_order=2, ref_angle_deg=0.0):
    """Compare ``+a`` against ``-a`` for every symmetric pair present in the angle grid.

    A positive angle ``a`` is included only when a ``-a`` sample exists within
    :data:`ANGLE_MATCH_TOL_DEG`. Negative members are skipped as loop starts, so every pair appears
    once. ``delta_db = rms(+a) - rms(-a)``; a metric that is an artefact of one side will show a
    non-zero delta. ``nan`` entries propagate into ``delta_db``.
    """
    f, s, a = _validate_cut(freqs_hz, spl_db, angles_deg)
    rows = []
    for angle in sorted({float(x) for x in a if float(x) > ANGLE_MATCH_TOL_DEG}):
        j_neg, dev_neg = _nearest_sample(a, -angle)
        if j_neg is None or dev_neg > ANGLE_MATCH_TOL_DEG:
            continue
        pos = fixed_angle_residual_curve(
            f, s, a, angle, ref_angle_deg=ref_angle_deg, band_hz=band_hz,
            detrend_order=detrend_order)
        neg = fixed_angle_residual_curve(
            f, s, a, -angle, ref_angle_deg=ref_angle_deg, band_hz=band_hz,
            detrend_order=detrend_order)
        delta = pos["rms_db"] - neg["rms_db"]
        rows.append({
            "angle_deg": angle,
            "counterpart_deg": float(a[j_neg]),
            "rms_db": pos["rms_db"],
            "counterpart_rms_db": neg["rms_db"],
            "delta_db": float(delta) if np.isfinite(delta) else float("nan"),
            "reason": pos["reason"] or neg["reason"],
        })
    return rows


def cut_identity_check(freqs_hz, spl_db, angles_deg, metrics, band_hz=DEFAULT_BAND_HZ):
    """Structural consistency checks between a stored cut and its ``metrics.json`` entry.

    The check does NOT re-derive the objective's angular ripple (different definition). Instead it
    verifies the plumbing: frequency count/values, presence of the 0-degree sample, finiteness of
    the cut, and (when supplied) the balloon direction count. The on-axis discrepancy against
    ``metrics["on_axis_db"]`` is reported in two forms because the stored ``on_axis_db`` is
    normalised to its own band mean (``types.py``): the raw offset and the offset after removing
    each side's band mean (the shape comparison). Only the structural checks gate ``ok``.

    ``metrics`` may carry the balloon count under ``n_balloon``, ``balloon_count`` or
    ``n_balloon_dirs``; if absent that check is skipped with a note.
    """
    f, s, a = _validate_cut(freqs_hz, spl_db, angles_deg)
    notes = []
    ok = True

    mf = np.asarray(metrics.get("freqs_hz", []), dtype=float)
    if mf.size == 0:
        ok = False
        notes.append("metrics['freqs_hz'] missing")
        max_rel = float("nan")
    elif mf.size != f.size:
        ok = False
        max_rel = float("nan")
        notes.append(f"frequency count differs: cut {f.size} vs metrics {mf.size}")
    else:
        denom = np.maximum(np.abs(mf), 1e-12 * np.max(np.abs(mf), initial=1.0))
        max_rel = float(np.max(np.abs(f - mf) / denom))
        if not np.isfinite(max_rel) or max_rel > 1e-9:
            ok = False
            notes.append(f"frequency arrays differ (max rel err {max_rel:.3e})")

    j0, dev0 = _nearest_sample(a, 0.0)
    if j0 is None or dev0 > ANGLE_MATCH_TOL_DEG:
        ok = False
        notes.append("no 0-degree sample within tolerance")
        on_axis = None
    else:
        on_axis = s[:, j0]

    if not np.all(np.isfinite(s)):
        ok = False
        notes.append("non-finite entries in spl_db")

    n_balloon = None
    for key in ("n_balloon", "balloon_count", "n_balloon_dirs"):
        if key in metrics and metrics[key] is not None:
            n_balloon = int(metrics[key])
            break
    if n_balloon is None:
        notes.append("balloon count not supplied; balloon check skipped")
    elif n_balloon <= 0:
        ok = False
        notes.append(f"balloon count is not positive: {n_balloon}")

    max_abs_on_axis = float("nan")
    max_abs_shape = float("nan")
    mo = metrics.get("on_axis_db")
    if mo is None:
        notes.append("metrics['on_axis_db'] missing; on-axis comparison skipped")
    elif on_axis is not None:
        mo = np.asarray(mo, dtype=float)
        if mo.shape != on_axis.shape:
            ok = False
            notes.append(f"on_axis_db shape {mo.shape} != cut shape {on_axis.shape}")
        else:
            use = _band_mask(f, band_hz) & np.isfinite(mo) & np.isfinite(on_axis)
            if int(use.sum()) < 1:
                notes.append("no finite in-band samples for on-axis comparison")
            else:
                diff = on_axis[use] - mo[use]
                max_abs_on_axis = float(np.max(np.abs(diff)))
                shape = diff - np.mean(diff)
                max_abs_shape = float(np.max(np.abs(shape)))
                notes.append(
                    f"on_axis_db is band-mean-normalised (stored convention); raw offset "
                    f"{max_abs_on_axis:.3f} dB, shape difference {max_abs_shape:.3f} dB")
                if not np.isfinite(max_abs_shape) or max_abs_shape > 0.5:
                    ok = False
                    notes.append("on-axis shape differs by more than 0.5 dB")

    return {
        "ok": bool(ok),
        "max_abs_on_axis_db": max_abs_on_axis,
        "max_abs_on_axis_shape_db": max_abs_shape,
        "max_freq_rel_err": max_rel,
        "notes": notes,
    }


def sensitivity_scan(freqs_hz, spl_db, angles_deg, angles_deg_targets,
                     band_hz=DEFAULT_BAND_HZ, detrend_orders=(1, 2, 3),
                     ref_angle_deg=0.0):
    """One row per (target angle, reference/order) so a caller can show rank stability.

    Rows cover the exploratory ``trend`` reference at every requested order, plus the
    IEC/Klippel-backed ``band_mean`` reference (``detrend_order = None``). Uses
    :func:`fixed_angle_residual_curve`; a refusal row carries its ``reason`` and ``nan`` rms.
    """
    rows = []
    for target in angles_deg_targets:
        for order in detrend_orders:
            curve = fixed_angle_residual_curve(
                freqs_hz, spl_db, angles_deg, target, ref_angle_deg=ref_angle_deg,
                band_hz=band_hz, detrend_order=order, reference="trend")
            rows.append({
                "angle_target_deg": float(target),
                "angle_deg": curve["angle_deg"],
                "reference": "trend",
                "detrend_order": int(order),
                "rms_db": curve["rms_db"],
                "max_abs_db": curve["max_abs_db"],
                "n": curve["n"],
                "n_params": curve["n_params"],
                "dof": curve["dof"],
                "reason": curve["reason"],
            })
        curve = fixed_angle_residual_curve(
            freqs_hz, spl_db, angles_deg, target, ref_angle_deg=ref_angle_deg,
            band_hz=band_hz, reference="band_mean")
        rows.append({
            "angle_target_deg": float(target),
            "angle_deg": curve["angle_deg"],
            "reference": "band_mean",
            "detrend_order": None,
            "rms_db": curve["rms_db"],
            "max_abs_db": curve["max_abs_db"],
            "n": curve["n"],
            "n_params": curve["n_params"],
            "dof": curve["dof"],
            "reason": curve["reason"],
        })
    return rows
