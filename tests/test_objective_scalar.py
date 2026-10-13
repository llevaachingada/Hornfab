"""Tests 1-7 of 08_TASK_PIPELINE: the scalar objective. Offline, numpy only."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hornlab_search.metrics.di import target_di_db
from hornlab_search.objective import (ALL_KEYS, DEFAULT_WEIGHTS, PENALTY_FAILED, TERM_KEYS,
                                      WEIGHTED_KEYS, objective, penalty_result, weighted_terms)
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

FREQS = np.geomspace(500.0, 10000.0, 12)
TARGET = Target(coverage_h_deg=75.0, coverage_v_deg=45.0, band_lo_hz=700.0, band_hi_hz=5500.0,
                di_target_db=None, di_slope_target=0.0, z_min=0.5)
W = dict(DEFAULT_WEIGHTS)


def perfect(freqs=FREQS, target=TARGET) -> MetricSet:
    n = freqs.size
    di = target_di_db(target.coverage_h_deg, target.coverage_v_deg)
    return MetricSet(freqs_hz=freqs.copy(),
                     bw_h_deg=np.full(n, target.coverage_h_deg),
                     bw_v_deg=np.full(n, target.coverage_v_deg),
                     di_db=np.full(n, di), di_source="balloon",
                     ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n),
                     on_axis_db=np.zeros(n), z_throat_real=np.full(n, 1.0), scalars={})


def messy() -> MetricSet:
    m = perfect()
    n = m.freqs_hz.size
    rng = np.random.default_rng(3)
    return dataclasses.replace(
        m, bw_h_deg=m.bw_h_deg + rng.normal(0, 10, n), bw_v_deg=m.bw_v_deg + rng.normal(0, 8, n),
        di_db=m.di_db + np.linspace(-2, 2, n), ripple_h_db=np.abs(rng.normal(1.5, 0.3, n)),
        ripple_v_db=np.abs(rng.normal(1.0, 0.3, n)), on_axis_db=rng.normal(0, 1.2, n),
        z_throat_real=np.full(n, 0.3))


# 1
def test_all_term_keys_present_and_weighted_terms_sum_to_total():
    j, t = objective(messy(), True, TARGET, W)
    assert set(TERM_KEYS) <= set(t) and set(t) == set(ALL_KEYS)
    assert t["penalty"] == 0.0
    assert j == pytest.approx(t["total"], rel=1e-12)
    assert j == pytest.approx(sum(W[k] * t[k] for k in WEIGHTED_KEYS), rel=1e-12)
    wt = weighted_terms(t, W)
    assert wt["total"] == pytest.approx(j, rel=1e-12)
    assert all(np.isfinite(v) for v in t.values())


# 2
def test_perfect_design_scores_zero():
    j, t = objective(perfect(), True, TARGET, W)
    assert abs(j) < 1e-12 and abs(t["total"]) < 1e-12
    assert t["n_nan"] == 0 and t["n_in_band"] > 0 and t["di_estimated"] == 0.0


# 3
def test_none_metrics_and_not_ok_give_exactly_the_failure_penalty():
    for args in ((None, True), (None, False), (perfect(), False)):
        j, t = objective(args[0], args[1], TARGET, W)
        assert j == PENALTY_FAILED and np.isfinite(j)
        assert set(t) == set(ALL_KEYS)
        assert t["penalty"] == PENALTY_FAILED and t["total"] == PENALTY_FAILED
        assert all(t[k] == 0.0 for k in WEIGHTED_KEYS)


def test_objective_never_raises_on_garbage():
    m = perfect()
    bad = dataclasses.replace(m, bw_h_deg=np.zeros(3))          # shape mismatch
    j, t = objective(bad, True, TARGET, W)
    assert j == PENALTY_FAILED and set(t) == set(ALL_KEYS)
    j, _ = objective(m, True, TARGET, {"cov": "oops", "bogus": 1.0})
    assert np.isfinite(j)


def test_never_inf_even_for_inf_inputs():
    m = messy()
    m.bw_h_deg[3] = np.inf
    m.ripple_h_db[4] = -np.inf
    j, t = objective(m, True, TARGET, W)
    assert np.isfinite(j) and all(np.isfinite(v) for v in t.values())


# 4
def test_nan_ripple_at_one_frequency_is_finite_and_counted():
    m = messy()
    inband = np.flatnonzero((m.freqs_hz >= TARGET.band_lo_hz) & (m.freqs_hz <= TARGET.band_hi_hz))
    m.ripple_h_db[inband[2]] = np.nan
    j, t = objective(m, True, TARGET, W)
    assert np.isfinite(j) and t["n_nan"] == 1
    j0, t0 = objective(messy(), True, TARGET, W)
    assert t0["n_nan"] == 0


def test_all_nan_ripple_does_not_reward_the_design():
    m = perfect()
    m.ripple_h_db[:] = np.nan
    j, t = objective(m, True, TARGET, W)
    assert np.isfinite(j) and t["rip"] > 0.0
    assert j > objective(perfect(), True, TARGET, W)[0]
    assert j < PENALTY_FAILED


# 5
def test_out_of_band_frequencies_do_not_affect_j():
    base = messy()
    j0, t0 = objective(base, True, TARGET, W)
    f = np.append(base.freqs_hz, 15000.0)
    junk = lambda a, v: np.append(a, v)                                   # noqa: E731
    worse = dataclasses.replace(
        base, freqs_hz=f, bw_h_deg=junk(base.bw_h_deg, 3.0), bw_v_deg=junk(base.bw_v_deg, 179.0),
        di_db=junk(base.di_db, -50.0), ripple_h_db=junk(base.ripple_h_db, 99.0),
        ripple_v_db=junk(base.ripple_v_db, np.nan), on_axis_db=junk(base.on_axis_db, -80.0),
        z_throat_real=junk(base.z_throat_real, -5.0))
    j1, t1 = objective(worse, True, TARGET, W)
    assert j1 == pytest.approx(j0, rel=0, abs=1e-12)
    assert t1["n_in_band"] == t0["n_in_band"] and t1["n_nan"] == t0["n_nan"]


def test_no_frequency_inside_the_band_is_a_failure_not_a_free_pass():
    t = dataclasses.replace(TARGET, band_lo_hz=20000.0, band_hi_hz=30000.0)
    j, terms = objective(perfect(), True, t, W)
    assert j == PENALTY_FAILED and terms["n_in_band"] == 0


# 6
def test_more_ripple_scores_strictly_worse():
    m1, m2 = perfect(), perfect()
    m1.ripple_h_db[:] = 0.5
    m1.ripple_v_db[:] = 0.5                  # 1 dB total
    m2.ripple_h_db[:] = 1.0
    m2.ripple_v_db[:] = 1.0                  # 2 dB total
    assert objective(m1, True, TARGET, W)[0] < objective(m2, True, TARGET, W)[0]


# 7
def test_cuts_estimate_di_is_flagged():
    m = perfect()
    j, t = objective(dataclasses.replace(m, di_source="cuts_estimate"), True, TARGET, W)
    assert t["di_estimated"] == 1.0
    assert j == pytest.approx(objective(m, True, TARGET, W)[0])      # still computed
    assert objective(m, True, TARGET, W)[1]["di_estimated"] == 0.0


def test_load_term_skipped_without_impedance_and_weight_zero_by_default():
    m = dataclasses.replace(messy(), z_throat_real=None)
    j, t = objective(m, True, TARGET, W)
    assert t["load"] == 0.0
    jz, tz = objective(messy(), True, TARGET, W)      # z = 0.3 < z_min = 0.5
    assert tz["load"] == pytest.approx(0.2) and W["load"] == 0.0
    j2, _ = objective(messy(), True, TARGET, {**W, "load": 1.0})
    assert j2 == pytest.approx(jz + 0.2)


def test_di_target_override_and_slope_target():
    m = perfect()
    t2 = dataclasses.replace(TARGET, di_target_db=m.di_db[0] + 2.0)
    j, t = objective(m, True, t2, W)
    assert t["di"] == pytest.approx(4.0 / 10.0)
    steep = dataclasses.replace(m, di_db=m.di_db + 4.0 * np.log10(m.freqs_hz))     # +4 dB/decade
    _, ts = objective(steep, True, TARGET, W)
    assert ts["dislope"] == pytest.approx(16.0, rel=1e-6)


def test_penalty_result_shape():
    j, t = penalty_result(123.0)
    assert j == 123.0 and t["total"] == 123.0 and set(t) == set(ALL_KEYS)
