"""Objective v2 metric tests (senior pass 2026-10-24, WP1).

The v1 functions are tested unchanged in tests/test_metrics_smoothness.py. These tests pin the
new detrended ripple/flatness and the Gaussian-beam DI reference.
"""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.metrics import di as di_mod
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.metrics.smoothness import (band_flatness_detrended_db, ripple_db,
                                               ripple_detrended_db)
from test_metrics_helpers import probe_angles

ANG = probe_angles()          # 73 samples, 2.5 deg, exact 0 at index 36


def _gauss_db(angles_deg, cov_total_deg):
    half = cov_total_deg / 2.0
    return -6.0206 * (np.asarray(angles_deg, dtype=float) / half) ** 2


def _cosn_db(angles_deg, cov_total_deg):
    half = cov_total_deg / 2.0
    n = np.log(0.5) / np.log(np.cos(np.radians(half)))
    return 20.0 * np.log10(np.cos(np.radians(np.asarray(angles_deg, dtype=float))) ** n)


def _ripple(tilt_db, amplitude=1.0):
    s = np.array(tilt_db, dtype=float)
    s += amplitude * np.where(np.arange(s.size) % 2 == 0, 1.0, -1.0)
    return s


# ---- ripple about a smooth beam


@pytest.mark.parametrize("cov", [60.0, 90.0, 120.0])
def test_ideal_gaussian_taper_has_no_detrended_ripple(cov):
    assert ripple_detrended_db(ANG, _gauss_db(ANG, cov), cov) < 0.05


@pytest.mark.parametrize("cov", [60.0, 90.0, 120.0])
def test_ideal_cosn_taper_has_no_detrended_ripple(cov):
    assert ripple_detrended_db(ANG, _cosn_db(ANG, cov), cov) < 0.05


@pytest.mark.parametrize("cov", [60.0, 90.0])
def test_alternating_one_db_ripple_survives_detrending(cov):
    rippled = _ripple(_gauss_db(ANG, cov), amplitude=1.0)
    assert 0.5 < ripple_detrended_db(ANG, rippled, cov) < 1.5


def test_v1_ripple_still_scores_the_taper_itself():
    # Documents the bug the v2 metric fixes: an ideal 90-degree Gaussian taper already reads
    # ~1.9 dB per plane under v1, because the taper is variance to a plain std.
    assert ripple_db(ANG, _gauss_db(ANG, 90.0), 90.0) == pytest.approx(1.92, abs=0.05)
    assert ripple_detrended_db(ANG, _gauss_db(ANG, 90.0), 90.0) < 0.05


def test_ripple_detrended_uses_the_same_coverage_and_floor_rules():
    flat = np.full(ANG.shape, 94.0)
    assert ripple_detrended_db(ANG, flat, 75.0) == 0.0
    # Fewer than seven samples inside coverage -> nan (mirrors the v1 MIN rule, at 7).
    assert np.isnan(ripple_detrended_db(ANG, flat, 9.9))
    # A sample beyond the -40 dB floor cannot drive the residual.
    deep = flat.copy()
    deep[ANG == 10.0] = 94.0 - 60.0
    assert ripple_detrended_db(ANG, deep, 75.0) == 0.0


def test_ripple_detrended_requires_an_exact_on_axis_sample():
    even = np.linspace(-90.0, 90.0, 72)
    with pytest.raises(ValueError):
        ripple_detrended_db(even, np.zeros(72), 75.0)


# ---- flatness without the drive tilt


def _tilted(freqs):
    return -3.0 * np.log2(np.asarray(freqs, dtype=float) / freqs[0])


def test_pure_tilt_is_removed_exactly():
    freqs = np.geomspace(500.0, 10000.0, 24)
    assert band_flatness_detrended_db(freqs, _tilted(freqs)) < 1e-9


def test_tilt_plus_half_db_alternating_reads_half_a_db():
    freqs = np.geomspace(500.0, 10000.0, 24)
    x = _tilted(freqs) + 0.5 * np.where(np.arange(freqs.size) % 2 == 0, 1.0, -1.0)
    assert band_flatness_detrended_db(freqs, x) == pytest.approx(0.5, abs=0.05)


def test_flatness_ignores_nonfinite_and_needs_four_points():
    assert np.isnan(band_flatness_detrended_db(np.array([500.0, 1000.0, 2000.0]),
                                               np.array([0.0, 0.0, 0.0])))
    freqs = np.array([500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0])
    x = _tilted(freqs)
    x_bad = x.copy()
    x_bad[2] = np.nan
    x_bad[5] = np.inf
    assert band_flatness_detrended_db(freqs, x_bad) < 1e-9


# ---- Gaussian-beam DI reference (Report 1 F5)


@pytest.mark.parametrize("h,v,expected", [(90.0, 90.0, 10.33),
                                         (90.0, 60.0, 11.91),
                                         (75.0, 45.0, 13.76)])
def test_target_di_gaussian_matches_the_reference(h, v, expected):
    assert target_di_gaussian_db(h, v) == pytest.approx(expected, abs=0.05)


def test_target_di_gaussian_is_cached_and_validated():
    a = target_di_gaussian_db(90, 60)
    b = target_di_gaussian_db(90.0, 60.0)
    assert a == b
    assert di_mod._target_di_gaussian_db_cached.cache_info().hits >= 1
    with pytest.raises(ValueError):
        target_di_gaussian_db(0.0, 60.0)
    with pytest.raises(ValueError):
        target_di_gaussian_db(90.0, float("nan"))
