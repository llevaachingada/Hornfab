"""Objective v2 (senior pass 2026-10-24, WP1/WP4). Offline, numpy only.

The v1 golden tests live unchanged in tests/test_objective_scalar.py; these cover the detrended
terms, the Gaussian-beam DI target, graceful degradation, the never-raise contract and the
per-frequency weights.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective import (ALL_KEYS, DEFAULT_WEIGHTS, PENALTY_FAILED, TERM_KEYS,
                                      WEIGHTED_KEYS, objective)
from hornlab_search.objective.scalar_v2 import freq_weight_vector, objective_v2
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet, Response
from test_metrics_helpers import probe_angles

FREQS = np.geomspace(500.0, 10000.0, 12)
TARGET = Target(coverage_h_deg=75.0, coverage_v_deg=45.0, band_lo_hz=700.0, band_hi_hz=5500.0,
                di_target_db=None, di_slope_target=0.0, z_min=0.5)
W = dict(DEFAULT_WEIGHTS)
ANG = probe_angles()


def _gauss_db(angles_deg, cov_total_deg):
    return -6.0206 * (np.asarray(angles_deg, dtype=float) / (cov_total_deg / 2.0)) ** 2


def _metrics(freqs=FREQS, target=TARGET) -> MetricSet:
    n = freqs.size
    di = target_di_gaussian_db(target.coverage_h_deg, target.coverage_v_deg)
    return MetricSet(freqs_hz=np.array(freqs, float),
                     bw_h_deg=np.full(n, target.coverage_h_deg),
                     bw_v_deg=np.full(n, target.coverage_v_deg),
                     di_db=np.full(n, di), di_source="balloon",
                     ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n),
                     on_axis_db=np.zeros(n), z_throat_real=np.full(n, 1.0), scalars={})


def _response(freqs=FREQS, angles=ANG, h_db=None, v_db=None) -> Response:
    a = np.asarray(angles, float)
    h = np.tile(_gauss_db(a, TARGET.coverage_h_deg), (len(freqs), 1)) if h_db is None else \
        np.tile(np.asarray(h_db, float), (len(freqs), 1))
    v = np.tile(_gauss_db(a, TARGET.coverage_v_deg), (len(freqs), 1)) if v_db is None else \
        np.tile(np.asarray(v_db, float), (len(freqs), 1))
    return Response(freqs_hz=np.array(freqs, float), h_angles_deg=a.copy(), v_angles_deg=a.copy(),
                    spl_h_db=h, spl_v_db=v, balloon_dirs=None, spl_balloon_db=None,
                    z_throat=np.ones(len(freqs), dtype=complex), backend="fake", n_dof=1, meta={})


def _messy() -> MetricSet:
    m = _metrics()
    n = m.freqs_hz.size
    rng = np.random.default_rng(7)
    return dataclasses.replace(
        m, bw_h_deg=m.bw_h_deg + rng.normal(0, 10, n), bw_v_deg=m.bw_v_deg + rng.normal(0, 8, n),
        di_db=m.di_db + np.linspace(-2, 2, n), ripple_h_db=np.abs(rng.normal(1.5, 0.3, n)),
        ripple_v_db=np.abs(rng.normal(1.0, 0.3, n)), on_axis_db=rng.normal(0, 1.2, n),
        z_throat_real=np.full(n, 0.3))


# ---- shape and the never-raise contract


def test_key_set_matches_v1_exactly_and_total_is_weighted_sum():
    j, t = objective_v2(_messy(), None, True, TARGET, W)
    assert set(t) == set(ALL_KEYS) and set(TERM_KEYS) <= set(t)
    assert j == pytest.approx(t["total"], rel=1e-12)
    assert j == pytest.approx(sum(W[k] * t[k] for k in WEIGHTED_KEYS), rel=1e-12)
    assert all(np.isfinite(v) for v in t.values())


def test_perfect_design_scores_zero_under_v2():
    j, t = objective_v2(_metrics(), None, True, TARGET, W)
    assert abs(j) < 1e-12 and abs(t["total"]) < 1e-12
    assert t["n_nan"] == 0 and t["n_in_band"] > 0 and t["di_estimated"] == 0.0


def test_none_or_failed_is_the_failure_penalty():
    for metrics, ok in ((None, True), (None, False), (_metrics(), False)):
        j, t = objective_v2(metrics, None, ok, TARGET, W)
        assert j == PENALTY_FAILED and set(t) == set(ALL_KEYS)
        assert t["penalty"] == PENALTY_FAILED and all(t[k] == 0.0 for k in WEIGHTED_KEYS)


def test_objective_v2_never_raises_on_garbage():
    bad = dataclasses.replace(_metrics(), bw_h_deg=np.zeros(3))
    for metrics, resp, target, weights in (
            (bad, None, TARGET, W),
            (_metrics(), object(), TARGET, W),
            (_metrics(), None, TARGET, {"cov": "oops", "bogus": 1.0}),
            (_metrics(), None, dataclasses.replace(TARGET, freq_weights={"bogus": 1}), W),
    ):
        j, t = objective_v2(metrics, resp, True, target, weights)
        assert np.isfinite(j) and set(t) == set(ALL_KEYS)
        assert all(np.isfinite(v) for v in t.values())


def test_never_inf_even_for_inf_and_nan_inputs():
    for m in (_messy(), _metrics()):
        m.bw_h_deg[3] = np.inf
        m.ripple_h_db[4] = -np.inf
        m.on_axis_db[2] = np.nan
        j, t = objective_v2(m, None, True, TARGET, W)
        assert np.isfinite(j) and all(np.isfinite(v) for v in t.values())


def test_nan_ripple_at_one_frequency_is_finite_and_counted():
    m = _metrics()
    inband = np.flatnonzero((m.freqs_hz >= TARGET.band_lo_hz) & (m.freqs_hz <= TARGET.band_hi_hz))
    m.ripple_h_db[inband[2]] = np.nan
    j, t = objective_v2(m, None, True, TARGET, W)
    assert np.isfinite(j) and t["n_nan"] == 1


def test_no_frequency_inside_the_band_is_a_failure():
    t = dataclasses.replace(TARGET, band_lo_hz=20000.0, band_hi_hz=30000.0)
    j, terms = objective_v2(_metrics(), None, True, t, W)
    assert j == PENALTY_FAILED and terms["n_in_band"] == 0


# ---- term behaviour


def test_ideal_beam_response_reads_near_zero_detrended_ripple():
    m = _metrics()
    m.ripple_h_db[:] = 1.9          # the v1 floor for an ideal taper
    m.ripple_v_db[:] = 1.9
    j_none, t_none = objective_v2(m, None, True, TARGET, W)
    _, t_resp = objective_v2(m, _response(), True, TARGET, W)
    assert t_none["rip"] == pytest.approx(3.8, abs=1e-9)     # graceful fallback = v1 values
    assert t_resp["rip"] < 0.05                              # detrended response path
    assert j_none > objective_v2(m, _response(), True, TARGET, W)[0]


def test_detrended_flatness_removes_a_pure_tilt():
    m = _metrics()
    m.on_axis_db = -3.0 * np.log2(m.freqs_hz / m.freqs_hz[0])
    _, t = objective_v2(m, None, True, TARGET, W)
    assert t["flat"] < 1e-9


def test_di_uses_the_gaussian_reference():
    m = _metrics()
    ref = target_di_gaussian_db(TARGET.coverage_h_deg, TARGET.coverage_v_deg)
    m.di_db = np.full(m.freqs_hz.size, ref + 2.0)
    _, t = objective_v2(m, None, True, TARGET, W)
    assert t["di"] == pytest.approx(4.0 / 10.0)


def test_explicit_di_target_keeps_its_v1_meaning():
    m = _metrics()
    tgt = dataclasses.replace(TARGET, di_target_db=m.di_db[0] + 2.0)
    _, t = objective_v2(m, None, True, tgt, W)
    assert t["di"] == pytest.approx(4.0 / 10.0)


def test_di_weight_zero_skips_the_term():
    m = dataclasses.replace(_metrics(), di_db=np.full(FREQS.size, 100.0))
    _, t_off = objective_v2(m, None, True, TARGET, {**W, "di": 0.0})
    _, t_on = objective_v2(m, None, True, TARGET, W)
    assert t_off["di"] == 0.0
    assert t_on["di"] > 0.0
    assert t_off["total"] == pytest.approx(t_on["total"] - W["di"] * t_on["di"])


def test_cov_dislope_and_load_match_the_v1_values():
    m = _messy()
    _, t1 = objective(m, True, TARGET, W)
    _, t2 = objective_v2(m, None, True, TARGET, W)
    for k in ("cov", "dislope", "load"):
        assert t2[k] == pytest.approx(t1[k], rel=1e-12, abs=1e-12)


def test_response_without_an_exact_zero_axis_degrades_gracefully():
    even = np.linspace(-90.0, 90.0, 72)
    resp = _response(angles=even)
    m = _metrics()
    m.ripple_h_db[:] = 1.0
    m.ripple_v_db[:] = 1.0
    j, t = objective_v2(m, resp, True, TARGET, W)
    assert np.isfinite(j) and t["rip"] == pytest.approx(2.0)


# ---- WP4: per-frequency weights


def _weighted_fixture():
    freqs = np.array([600.0, 700.0, 1000.0, 2000.0, 3000.0, 5500.0, 6000.0])
    m = _metrics(freqs)
    values = np.array([99.0, 2.0, 4.0, 8.0, 16.0, 32.0, 99.0])
    m.ripple_h_db = values / 2.0
    m.ripple_v_db = values / 2.0
    return freqs, m


def test_no_freq_weights_gives_the_plain_mean():
    freqs, m = _weighted_fixture()
    _, t = objective_v2(m, None, True, TARGET, W)
    # In-band values 2, 4, 8, 16, 32 -> 12.4.
    assert t["rip"] == pytest.approx(np.mean([2.0, 4.0, 8.0, 16.0, 32.0]))


def test_weighted_mean_matches_a_hand_computed_value():
    freqs, m = _weighted_fixture()
    tgt = dataclasses.replace(
        TARGET, freq_weights={"band_hz": [[700.0, 2000.0, 2.0], [2000.0, 5500.0, 0.5]]})
    w = freq_weight_vector(freqs, tgt)
    # 700 and 1000 -> 2; 2000 is in BOTH intervals -> 2*0.5 = 1; 3000 and 5500 -> 0.5.
    assert w.tolist() == [1.0, 2.0, 2.0, 1.0, 0.5, 0.5, 1.0]
    _, t = objective_v2(m, None, True, tgt, W)
    expected = (2.0 * 2.0 + 2.0 * 4.0 + 1.0 * 8.0 + 0.5 * 16.0 + 0.5 * 32.0) / (2 + 2 + 1 + 0.5 + 0.5)
    assert t["rip"] == pytest.approx(expected)


def test_weight_vector_defaults_to_one_and_is_shape_stable():
    assert np.all(freq_weight_vector(FREQS, TARGET) == 1.0)
    assert freq_weight_vector(FREQS, TARGET).shape == FREQS.shape
