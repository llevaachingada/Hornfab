"""Contract tests 18-23 for ripple and the helpers it uses."""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.metrics.polar import coverage_mask, normalized_db
from hornlab_search.metrics.smoothness import band_flatness_db, coverage_error_deg, ripple_db
from test_metrics_helpers import probe_angles

ANG = probe_angles()           # 73 samples, 2.5 deg, exact 0 at index 36


def _flat():
    return np.full(ANG.shape, 94.0)


# 18
def test_flat_is_zero():
    assert ripple_db(ANG, _flat(), 75.0) == 0.0


# 19
def test_alternating_plus_minus_one_is_one():
    s = _flat()
    inside = np.nonzero(coverage_mask(ANG, 75.0) & (ANG != 0.0))[0]
    s[inside] += np.where(np.arange(inside.size) % 2 == 0, 1.0, -1.0)
    assert inside.size == 30                 # 15 at +1, 15 at -1, on-axis exactly 0
    assert ripple_db(ANG, s, 75.0) == pytest.approx(1.0, abs=1e-9)


# 20
def test_deep_null_inside_coverage_is_floored_out():
    s = _flat()
    s[ANG == 10.0] = 94.0 - 60.0
    assert ripple_db(ANG, s, 75.0) == 0.0


# 21
def test_fewer_than_five_survivors_is_nan():
    assert np.isnan(ripple_db(ANG, _flat(), 8.0))        # +-4 deg: 0, +-2.5 -> 3 samples
    s = _flat()
    s[ANG != 0.0] = 94.0 - 60.0                          # everything but on-axis floored out
    assert np.isnan(ripple_db(ANG, s, 75.0))


def test_exactly_five_survivors_is_a_number():
    assert ripple_db(ANG, _flat(), 12.5) == 0.0          # +-6.25: 0, +-2.5, +-5 -> 5 samples
    assert np.isnan(ripple_db(ANG, _flat(), 9.9))        # +-4.95: 0, +-2.5 -> 3 samples


def test_samples_outside_coverage_are_ignored():
    s = _flat()
    s[np.abs(ANG) > 37.5] -= 20.0
    assert ripple_db(ANG, s, 75.0) == 0.0


# 22
def test_coverage_mask_75_is_31_samples():
    m = coverage_mask(ANG, 75.0)
    assert m.sum() == 31
    assert ANG[m].min() == -37.5 and ANG[m].max() == 37.5


# 23
def test_normalized_db_exact_zero_is_floor_not_inf():
    with np.errstate(divide="ignore"):
        s = 20.0 * np.log10(np.array([0.0, 0.5, 1.0, 0.5, 0.0]))
    n = normalized_db(s)
    assert n[0] == -120.0 and n[4] == -120.0
    assert np.all(np.isfinite(n))
    assert normalized_db(np.array([np.nan, 0.0, 0.0]), ref_db=0.0)[0] == -120.0


# ---- additions

def test_band_flatness_removes_mean_and_ignores_nonfinite():
    assert band_flatness_db(np.array([90.0, 94.0, 98.0])) == pytest.approx(np.sqrt(32.0 / 3.0))
    assert band_flatness_db(np.full(5, 77.0)) == 0.0
    assert band_flatness_db(np.array([90.0, np.nan, 98.0, -np.inf])) == pytest.approx(4.0)
    assert np.isnan(band_flatness_db(np.array([np.nan])))


def test_coverage_error_is_signed_bw_minus_target():
    e = coverage_error_deg(np.array([80.0, 70.0]), 75.0)
    assert e.tolist() == [5.0, -5.0]
