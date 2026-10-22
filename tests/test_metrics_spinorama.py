"""Spinorama subset: listening window and SPDI."""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.metrics.spinorama import listening_window_db, spdi_db

ANG = np.arange(-90.0, 91.0, 5.0)


def _lw_hand(level_fn, nf=1):
    h = [0, -10, 10, -20, 20, -30, 30]
    v = [-10, 10]
    ls = np.array([level_fn(a) for a in h + v])
    return 10 * np.log10(np.mean(10 ** (ls / 10)))


def test_flat_equals_on_axis():
    s = np.tile(np.array([[80.0], [91.5]]), (1, ANG.size))
    lw = listening_window_db(ANG, s, ANG, s)
    np.testing.assert_allclose(lw, [80.0, 91.5], atol=1e-12)


def test_closed_form_linear_rolloff():
    k = 0.2
    h = -k * np.abs(ANG)[None, :]
    lw = listening_window_db(ANG, h, ANG, h)
    assert lw[0] == pytest.approx(_lw_hand(lambda a: -k * abs(a)), abs=1e-12)
    assert lw[0] < 0.0


def test_vertical_cut_used_separately():
    h = np.zeros((1, ANG.size))
    v = -np.abs(ANG)[None, :] * 0.3
    lw = listening_window_db(ANG, h, ANG, v)
    # 7 horizontal at 0 dB, 2 vertical at -3 dB
    expect = 10 * np.log10((7 + 2 * 10 ** (-0.3)) / 9)
    assert lw[0] == pytest.approx(expect, abs=1e-12)


def test_missing_exact_samples_interpolated():
    ang = np.arange(-90.0, 91.0, 15.0)   # no +-10, +-20
    h = -0.2 * np.abs(ang)[None, :]
    lw = listening_window_db(ang, h, ang, h)
    # linear cut: |.| is linear on each side, so interpolation is exact
    assert lw[0] == pytest.approx(_lw_hand(lambda a: -0.2 * abs(a)), abs=1e-12)


def test_nan_propagation_and_range():
    h = np.zeros((2, ANG.size))
    h[1, ANG == 20.0] = np.nan
    lw = listening_window_db(ANG, h, ANG, np.zeros_like(h))
    assert lw[0] == pytest.approx(0.0, abs=1e-12) and np.isnan(lw[1])
    short = np.arange(-20.0, 21.0, 5.0)   # no +-30: NaN, not extrapolated
    z = np.zeros((1, short.size))
    assert np.isnan(listening_window_db(short, z, short, z)[0])


def test_shape_errors():
    with pytest.raises(ValueError):
        listening_window_db(ANG, np.zeros((1, 5)), ANG, np.zeros((1, ANG.size)))
    with pytest.raises(ValueError):
        listening_window_db(ANG, np.zeros((1, ANG.size)), ANG, np.zeros((2, ANG.size)))
    with pytest.raises(ValueError):
        spdi_db(np.zeros(2), np.zeros(3), np.zeros(2))


def test_spdi_identity():
    lw = np.array([88.0, 90.0]); ax = np.array([90.0, 91.0]); di = np.array([8.0, 10.0])
    np.testing.assert_allclose(spdi_db(lw, ax, di), lw - (ax - di))
    # omni: LW == on-axis, DI == 0 -> SPDI == 0
    np.testing.assert_allclose(spdi_db(ax, ax, np.zeros(2)), 0.0)
