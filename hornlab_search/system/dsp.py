"""Complex DSP assembly for the system layer (Stage 1, Lane D).

The filters are **not** implemented here. Every response comes from
:mod:`hornlab_search.meh.dsp`, which pins the house conventions:

* analog prototype in ``s = j f / fc`` with ``exp(+j omega t)``,
* Linkwitz-Riley of even order 2/4/8 (a squared Butterworth section),
* ``delay(f, ms) = exp(-j 2 pi f tau)`` with ``tau = ms * 1e-3`` (positive ``ms`` = physical delay),
* ``polarity`` +1 / -1 and an analog peaking biquad.

Scope of this stage
-------------------
Only **analog prototypes** are assembled: there is no biquad/sample-rate realisation, no
pre-warping, no AD/DA or propagation model. A caller that needs a real digital implementation
does that in a later stage; this module must keep matching :mod:`hornlab_search.meh.dsp` exactly.

Convention decisions encoded here
---------------------------------
* ``DspPoint.crossover_type`` selects the Linkwitz-Riley order (``LR2`` -> 2, ``LR4`` -> 4,
  ``LR8`` -> 8). The horn channel gets the **high-pass**, the woofer channel the **low-pass**.
* ``DspPoint.relative_delay_ms`` is applied to the **horn** channel with
  ``meh.dsp.delay``; positive values delay the horn relative to the woofer.
* ``DspPoint.polarity_woofer`` is applied to the **woofer** channel only.
* ``DspPoint.peq_bands_woofer`` entries are ``(fc_hz, gain_db, q)`` and are applied to the
  **woofer** channel only, in the tuple order given.
* Channel gains are linear scalars ``10**(gain_db / 20)`` using the contract field names
  ``gain_db_horn`` and ``gain_db_woofer``.
"""
from __future__ import annotations

import numpy as np

from hornlab_search.meh import dsp as meh_dsp
from hornlab_search.system import contracts

__all__ = [
    "LR_ORDERS",
    "filter_bank",
    "validate_dsp_point",
]

#: Supported Linkwitz-Riley alignments and the even order passed to ``meh.dsp.lr``.
LR_ORDERS: dict[str, int] = {"LR2": 2, "LR4": 4, "LR8": 8}


def _order(crossover_type: str) -> int:
    ctype = str(crossover_type)
    order = LR_ORDERS.get(ctype)
    if order is None:
        raise contracts.SchemaError(
            f"unsupported crossover_type {crossover_type!r}; "
            f"expected one of {sorted(LR_ORDERS)}")
    return order


def _frequency_axis(freqs_hz) -> np.ndarray:
    f = np.asarray(freqs_hz, dtype=np.float64)
    if f.ndim != 1:
        raise contracts.SchemaError(f"freqs_hz must be a 1-D array, got shape {f.shape}")
    if not np.all(np.isfinite(f)) or np.any(f < 0.0):
        raise contracts.SchemaError("freqs_hz must be finite and non-negative")
    return f


def filter_bank(point: contracts.DspPoint,
                freqs_hz,
                ranges: contracts.DspRanges | None = None) -> dict[str, np.ndarray]:
    """Return the complex drive filters for one :class:`contracts.DspPoint`.

    ``{"horn": H_horn, "woofer": H_woofer}`` with each value a ``(nf,)`` ``complex128`` array
    at ``freqs_hz``. Both channels are assembled exclusively from :mod:`hornlab_search.meh.dsp`;
    this function adds no phase, delay or propagation of its own.

    :class:`contracts.DspPoint` carries no ranges, so pass the spec's
    :class:`contracts.DspRanges` as ``ranges`` to range-check the point at entry (B26). With
    ``ranges=None`` the historical per-field checks only apply, preserving existing callers.
    """
    if ranges is not None:
        validate_dsp_point(point, ranges)
    f = _frequency_axis(freqs_hz)
    order = _order(point.crossover_type)
    fc = float(point.xo_hz)
    if not np.isfinite(fc) or fc <= 0.0:
        raise contracts.SchemaError(f"xo_hz must be finite and > 0, got {point.xo_hz!r}")

    # Linkwitz-Riley split: horn takes the high-pass, woofer the low-pass.
    horn = meh_dsp.lr(f, fc, order, "hp")
    woofer = meh_dsp.lr(f, fc, order, "lp")

    # Woofer-only shaping: peaking bands, then polarity.
    for band in point.peq_bands_woofer:
        try:
            band_fc, band_gain_db, band_q = band
        except (TypeError, ValueError):
            raise contracts.SchemaError(
                f"peq_bands_woofer entries must be (fc_hz, gain_db, q), got {band!r}") from None
        woofer = woofer * meh_dsp.peaking(f, float(band_fc), float(band_gain_db), float(band_q))
    woofer = woofer * meh_dsp.polarity(point.polarity_woofer)

    # Channel gains: linear scalar per channel.
    horn = horn * 10.0 ** (float(point.gain_db_horn) / 20.0)
    woofer = woofer * 10.0 ** (float(point.gain_db_woofer) / 20.0)

    # Honest relative delay: applied to the horn path only (positive = horn delayed).
    horn = horn * meh_dsp.delay(f, float(point.relative_delay_ms))

    return {
        "horn": np.asarray(horn, dtype=np.complex128),
        "woofer": np.asarray(woofer, dtype=np.complex128),
    }


def validate_dsp_point(point: contracts.DspPoint,
                       ranges: contracts.DspRanges) -> None:
    """Validate ``point`` against ``ranges``; raise :class:`contracts.SchemaError` on violation.

    This is the construction-site gate: check a candidate before calling :func:`filter_bank`.
    It checks the crossover type, crossover/gain/delay ranges, PEQ band count and boost ceiling
    (cuts are unlimited), PEQ q/fc sanity and woofer polarity.
    """
    ranges.validate()
    _order(point.crossover_type)
    if point.crossover_type not in ranges.crossover_types:
        raise contracts.SchemaError(
            f"crossover_type {point.crossover_type!r} not in allowed "
            f"{tuple(ranges.crossover_types)!r}")

    def _in_range(name: str, value: float, bounds: tuple[float, float]) -> None:
        v = float(value)
        lo, hi = (float(bounds[0]), float(bounds[1]))
        if not (np.isfinite(v) and lo <= v <= hi):
            raise contracts.SchemaError(f"{name} {v!r} outside [{lo!r}, {hi!r}]")

    _in_range("xo_hz", point.xo_hz, ranges.xo_hz_range)
    _in_range("gain_db_woofer", point.gain_db_woofer, ranges.gain_db_range)
    _in_range("gain_db_horn", point.gain_db_horn, ranges.gain_db_range)
    _in_range("relative_delay_ms", point.relative_delay_ms, ranges.relative_delay_ms_range)

    if len(point.peq_bands_woofer) > ranges.peq_max_bands:
        raise contracts.SchemaError(
            f"{len(point.peq_bands_woofer)} PEQ bands exceed peq_max_bands="
            f"{ranges.peq_max_bands}")
    for band in point.peq_bands_woofer:
        try:
            band_fc, band_gain_db, band_q = band
        except (TypeError, ValueError):
            raise contracts.SchemaError(
                f"peq_bands_woofer entries must be (fc_hz, gain_db, q), got {band!r}") from None
        if not (np.isfinite(float(band_fc)) and float(band_fc) > 0.0):
            raise contracts.SchemaError(f"PEQ fc must be finite and > 0, got {band_fc!r}")
        if not (np.isfinite(float(band_q)) and float(band_q) > 0.0):
            raise contracts.SchemaError(f"PEQ q must be finite and > 0, got {band_q!r}")
        if not np.isfinite(float(band_gain_db)):
            raise contracts.SchemaError(f"PEQ gain_db must be finite, got {band_gain_db!r}")
        if float(band_gain_db) > float(ranges.peq_max_boost_db):
            raise contracts.SchemaError(
                f"PEQ boost {float(band_gain_db)!r} dB exceeds peq_max_boost_db="
                f"{ranges.peq_max_boost_db!r} dB")

    try:
        meh_dsp.polarity(point.polarity_woofer)
    except ValueError as exc:
        raise contracts.SchemaError(str(exc)) from None
