"""SYS-08 / filter-assembly tests for ``hornlab_search.system.dsp``.

The filter implementation is ``hornlab_search.meh.dsp`` only. These tests pin that the system
assembly is a thin, exact wrapper: the same numbers as direct ``meh.dsp`` calls, the documented
channel split (horn HP, woofer LP), linear gains, woofer-only polarity/PEQ and the honest
``exp(-j omega tau)`` delay applied to the horn path only.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.meh import dsp as meh_dsp  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import dsp as sys_dsp  # noqa: E402


def _point(**kw: Any) -> C.DspPoint:
    defaults: dict[str, Any] = dict(
        crossover_type="LR4",
        xo_hz=1000.0,
        gain_db_woofer=-3.0,
        gain_db_horn=-1.5,
        relative_delay_ms=0.37,
        polarity_woofer=-1.0,
        peq_bands_woofer=((850.0, 2.0, 1.2),),
    )
    defaults.update(kw)
    return C.DspPoint(**defaults)


FREQS = np.array([50.0, 200.0, 700.0, 1000.0, 2500.0, 8000.0])


def test_filter_bank_matches_direct_meh_dsp_calls_exactly() -> None:
    point = _point()
    bank = sys_dsp.filter_bank(point, FREQS)
    order = sys_dsp.LR_ORDERS[point.crossover_type]

    expected_horn = meh_dsp.lr(FREQS, point.xo_hz, order, "hp")
    expected_horn = expected_horn * 10.0 ** (point.gain_db_horn / 20.0)
    expected_horn = expected_horn * meh_dsp.delay(FREQS, point.relative_delay_ms)

    expected_woofer = meh_dsp.lr(FREQS, point.xo_hz, order, "lp")
    for fc, gain_db, q in point.peq_bands_woofer:
        expected_woofer = expected_woofer * meh_dsp.peaking(FREQS, fc, gain_db, q)
    expected_woofer = expected_woofer * meh_dsp.polarity(point.polarity_woofer)
    expected_woofer = expected_woofer * 10.0 ** (point.gain_db_woofer / 20.0)

    np.testing.assert_allclose(bank["horn"], expected_horn, rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(bank["woofer"], expected_woofer, rtol=1e-12, atol=0.0)
    assert bank["horn"].dtype == np.complex128
    assert bank["woofer"].dtype == np.complex128


def test_all_supported_lr_orders_are_used() -> None:
    for ctype, order in sys_dsp.LR_ORDERS.items():
        point = _point(crossover_type=ctype)
        bank = sys_dsp.filter_bank(point, FREQS)
        expected = meh_dsp.lr(FREQS, point.xo_hz, order, "hp")
        expected = expected * 10.0 ** (point.gain_db_horn / 20.0)
        expected = expected * meh_dsp.delay(FREQS, point.relative_delay_ms)
        np.testing.assert_allclose(bank["horn"], expected, rtol=1e-12, atol=0.0)


def test_horn_gets_highpass_and_woofer_lowpass() -> None:
    point = _point(gain_db_woofer=0.0, gain_db_horn=0.0, relative_delay_ms=0.0,
                   polarity_woofer=1.0, peq_bands_woofer=())
    f = np.array([100.0, 10000.0])
    bank = sys_dsp.filter_bank(point, f)
    # Below the crossover the woofer passes and the horn is attenuated, and vice versa.
    assert abs(bank["woofer"][0]) > 0.99
    assert abs(bank["horn"][0]) < 1e-3
    assert abs(bank["horn"][1]) > 0.99
    assert abs(bank["woofer"][1]) < 1e-3


def test_gains_are_linear_scalars_and_polarity_is_woofer_only() -> None:
    point = _point(polarity_woofer=-1.0, peq_bands_woofer=())
    bank = sys_dsp.filter_bank(point, FREQS)
    reference = sys_dsp.filter_bank(
        C.DspPoint("LR4", 1000.0, 0.0, 0.0, point.relative_delay_ms, 1.0, ()), FREQS)
    np.testing.assert_allclose(
        np.abs(bank["horn"]), np.abs(reference["horn"]) * 10.0 ** (point.gain_db_horn / 20.0),
        rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(
        np.abs(bank["woofer"]),
        np.abs(reference["woofer"]) * 10.0 ** (point.gain_db_woofer / 20.0),
        rtol=1e-12, atol=0.0)
    # Polarity is a sign on the woofer only; the horn phase is untouched.
    np.testing.assert_allclose(
        bank["woofer"],
        -reference["woofer"] * 10.0 ** (point.gain_db_woofer / 20.0),
        rtol=1e-12, atol=0.0)


def test_delay_convention_is_exp_minus_j_omega_tau_on_the_horn_path() -> None:
    f = np.array([125.0, 1000.0, 4000.0])
    tau_s = 0.25e-3
    expected = np.exp(-2j * np.pi * f * tau_s)
    np.testing.assert_allclose(meh_dsp.delay(f, 0.25), expected, rtol=1e-15, atol=0.0)
    # Unwrapped phase slope is -2 pi tau rad/Hz, i.e. positive ms = physical delay.
    # (Dense grid, phase kept within +-pi so unwrap has no branch ambiguity.)
    dense = np.linspace(1.0, 1800.0, 1800)
    phase = np.unwrap(np.angle(meh_dsp.delay(dense, 0.25)))
    slope = (phase[-1] - phase[0]) / (dense[-1] - dense[0])
    assert slope == pytest.approx(-2.0 * np.pi * tau_s, rel=0.0, abs=1e-12)

    # A zero delay is exactly unity; the system bank therefore adds no phase of its own.
    point = _point(relative_delay_ms=0.0, peq_bands_woofer=())
    bank = sys_dsp.filter_bank(point, f)
    assert np.allclose(meh_dsp.delay(f, 0.0), 1.0 + 0.0j)
    assert np.all(np.isfinite(bank["horn"]))
    assert np.all(np.isfinite(bank["woofer"]))


def test_unknown_crossover_type_raises_schema_error() -> None:
    with pytest.raises(C.SchemaError, match="crossover_type"):
        sys_dsp.filter_bank(_point(crossover_type="LR6"), FREQS)
    with pytest.raises(C.SchemaError, match="crossover_type"):
        sys_dsp.validate_dsp_point(_point(crossover_type="LR6"), C.DspRanges())


@pytest.mark.parametrize("bad", [
    dict(xo_hz=2000.0),
    dict(gain_db_horn=4.0),
    dict(gain_db_woofer=-40.0),
    dict(relative_delay_ms=2.0),
    dict(peq_bands_woofer=((850.0, 2.0, 1.2), (900.0, 1.0, 1.0), (950.0, 1.0, 1.0))),
    dict(peq_bands_woofer=((850.0, 5.0, 1.2),)),
    dict(polarity_woofer=0.5),
])
def test_validate_dsp_point_rejects_out_of_range_points(bad: dict) -> None:
    with pytest.raises(C.SchemaError):
        sys_dsp.validate_dsp_point(_point(**bad), C.DspRanges())


def test_validate_dsp_point_accepts_an_in_range_point() -> None:
    sys_dsp.validate_dsp_point(_point(), C.DspRanges())
