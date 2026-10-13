"""Contract tests 1-8 plus convention checks for beamwidth_deg."""
from __future__ import annotations

import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.special import j1

from hornlab_search.metrics.polar import (
    DB_FLOOR, beamwidth_deg, coverage_mask, normalized_db, _threshold_db)
from test_metrics_helpers import cardioid, cut_db, dipole, omni, probe_angles

HALF_PRESSURE_DB = 20.0 * np.log10(0.5)


def piston(ka):
    def fn(theta):
        x = ka * np.sin(theta)
        out = np.ones_like(x)
        nz = np.abs(x) > 1e-12
        out[nz] = 2.0 * j1(x[nz]) / x[nz]
        return out
    return fn


def piston_expected_width(ka):
    """Total angle where 2*J1(x)/x = 0.5, x = ka*sin(theta)."""
    x0 = brentq(lambda x: 2.0 * j1(x) / x - 0.5, 1.0, 3.0, xtol=1e-14)
    return 2.0 * np.degrees(np.arcsin(x0 / ka))


# 1
def test_cardioid_reads_180_not_90():
    bw, n = beamwidth_deg(probe_angles(), cut_db(cardioid, probe_angles()))
    assert bw == pytest.approx(180.0, abs=0.05)
    assert n in (0, 2)


# 2
def test_dipole_reads_120():
    bw, n = beamwidth_deg(probe_angles(), cut_db(dipole, probe_angles()))
    assert bw == pytest.approx(120.0, abs=0.05)
    assert n == 2


# 2b: the same dipole on a grid that does NOT contain 60 deg, so interpolation
# (not a lucky sample) must find the crossing.
def test_dipole_reads_120_off_grid():
    ang = np.arange(-25, 26) * 3.5          # 3.5 deg steps: contains 0, not 60 (59.5, 63)
    assert not np.any(np.isclose(ang, 60.0))
    bw, n = beamwidth_deg(ang, cut_db(dipole, ang))
    # Linear-in-dB interpolation between 59.5 and 63 deg (measured error 0.06 deg).
    assert bw == pytest.approx(120.0, abs=0.1)
    assert n == 2


# 3
@pytest.mark.parametrize("ka", [3.0, 6.0, 12.0, 24.0])
def test_piston_matches_brentq(ka):
    ang = np.arange(-360, 361) * 0.25
    bw, n = beamwidth_deg(ang, cut_db(piston(ka), ang))
    assert n == 2
    assert bw == pytest.approx(piston_expected_width(ka), abs=0.05)


# 4
def test_omni_has_no_crossing():
    ang = probe_angles()
    assert beamwidth_deg(ang, cut_db(omni, ang)) == (180.0, 0)


# 5
def test_cardioid_on_coarse_10_degree_grid():
    ang = np.arange(-9, 10) * 10.0
    bw, _ = beamwidth_deg(ang, cut_db(cardioid, ang))
    assert abs(bw - 180.0) < 1.0


# 5b: proof that interpolation runs. cos^3 crosses 0.5 at acos(0.5**(1/3)) = 37.47 deg,
# between the 30 and 40 deg samples of a 10 deg grid. Snapping would read 60 or 80.
def test_interpolation_on_coarse_grid():
    ang = np.arange(-9, 10) * 10.0
    exact = 2.0 * np.degrees(np.arccos(0.5 ** (1.0 / 3.0)))
    bw, n = beamwidth_deg(ang, cut_db(lambda t: np.cos(t) ** 3, ang))
    assert n == 2
    assert abs(bw - exact) < 1.0
    assert abs(bw - 80.0) > 2.0 and abs(bw - 60.0) > 2.0


# 6
def test_sidelobe_above_minus_6_uses_outermost_crossings():
    def fn(theta):
        t = np.degrees(np.abs(theta))
        return np.exp(-np.log(2.0) * (t / 20.0) ** 2) + 0.8 * np.exp(-((t - 60.0) / 8.0) ** 2)

    ang = np.arange(-360, 361) * 0.25
    bw, n = beamwidth_deg(ang, cut_db(fn, ang))
    outer = brentq(lambda t: fn(np.radians(np.array([t])))[0] / fn(np.zeros(1))[0] - 0.5,
                   62.0, 70.0, xtol=1e-12)
    assert n == 6
    assert bw == pytest.approx(2.0 * outer, abs=0.05)
    assert bw > 120.0     # the main-lobe-only answer would be about 40


# 7
def test_reference_is_on_axis_not_maximum():
    def level_db(t):
        # on-axis dip: 0 dB at 0 deg, about +2.3 dB near 7.5 deg, then a smooth roll-off
        return -(t / 20.0) ** 2 * 6.0 + 3.5 * (1.0 - np.exp(-(t / 5.0) ** 2))

    ang = np.arange(-360, 361) * 0.25
    s = 94.0 + level_db(ang)
    assert s.max() - s[ang == 0.0][0] > 2.0
    bw, n = beamwidth_deg(ang, s)
    on_axis_ref = brentq(lambda t: level_db(t) - HALF_PRESSURE_DB, 10.0, 60.0, xtol=1e-12)
    max_ref = brentq(lambda t: level_db(t) - (level_db(7.5) + HALF_PRESSURE_DB), 10.0, 60.0,
                     xtol=1e-12)
    assert n == 2
    assert abs(2.0 * (max_ref - on_axis_ref)) > 3.0   # the two conventions really differ
    assert bw == pytest.approx(2.0 * on_axis_ref, abs=0.05)


# 8
def test_no_exact_zero_raises():
    ang = (np.arange(-36, 36) + 0.5) * 2.5        # symmetric, but no sample at 0
    with pytest.raises(ValueError):
        beamwidth_deg(ang, np.zeros_like(ang))


# ---- conventions that resolve contract section 10 (see NOTES_FOR_SENIOR.md)

def test_minus_6_db_is_half_pressure():
    assert _threshold_db(6.0) == pytest.approx(HALF_PRESSURE_DB, abs=1e-12)
    assert _threshold_db(3.0) == pytest.approx(10.0 * np.log10(0.5), abs=1e-12)
    assert _threshold_db(10.0) == -10.0


def test_clearly_narrow_pattern_reads_its_true_minus_6_db_width():
    # A pattern whose half-pressure point is clearly inside +-80 deg (here exactly +-30).
    n_exp = np.log(0.5) / np.log(np.cos(np.radians(30.0)))
    ang = probe_angles()
    bw, n = beamwidth_deg(ang, cut_db(lambda t: np.cos(t) ** n_exp, ang))
    assert n == 2
    assert bw == pytest.approx(60.0, abs=0.05)


def test_true_cardioid_is_the_only_180_reading():
    # A pattern 0.1 dB narrower than the cardioid must read narrower than 180.
    ang = probe_angles()
    bw, n = beamwidth_deg(ang, cut_db(lambda t: cardioid(t) * np.cos(t / 2.0) ** 0.1, ang))
    assert n == 2
    assert 170.0 < bw < 179.9


def test_one_sided_pattern_runs_to_the_grid_edge():
    ang = probe_angles()
    s = np.where(ang < 0.0, 94.0 - 20.0, 94.0)        # left side far down, right side flat
    s[ang == 0.0] = 94.0
    bw, n = beamwidth_deg(ang, s)
    assert n == 1
    assert 90.0 < bw < 95.0                            # crossing near 0 to the +90 edge


def test_dead_and_nonfinite_patterns_are_finite():
    ang = probe_angles()
    assert beamwidth_deg(ang, np.full(ang.shape, -np.inf)) == (180.0, 0)
    s = cut_db(dipole, ang)
    s[5] = np.nan
    bw, _ = beamwidth_deg(ang, s)
    assert np.isfinite(bw)


# ---- coverage_mask / normalized_db helpers used by the beamwidth family

def test_coverage_mask_inclusive_edge():
    m = coverage_mask(probe_angles(), 75.0)
    assert m.sum() == 31
    assert coverage_mask(np.array([-37.5, 37.5, 37.6]), 75.0).tolist() == [True, True, False]


def test_normalized_db_floor_and_default_reference():
    s = np.array([-np.inf, 0.0, 90.0, 94.0, 90.0, np.nan, -np.inf])
    n = normalized_db(s)                               # reference: centre sample (94)
    assert np.all(np.isfinite(n))
    assert n[3] == 0.0 and n[2] == -4.0
    assert n[0] == DB_FLOOR and n[5] == DB_FLOOR
    with pytest.raises(ValueError):
        normalized_db(np.zeros(4))
