"""Analytic, deterministic tests for :mod:`hornlab_search.metrics.cd`.

Every fixture is synthetic: no BEM, no stored run, no GPU. The expectations are the paper
fixtures from ``docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md`` section 3 (omni, narrowing
Gaussian, flat/shifted cuts, log-linear DI ramp, off-axis residual).
"""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.metrics.cd import (
    cd_metrics,
    di_std_log_db,
    listening_window_metrics,
    log_frequency_weights,
    nacc_matrix,
    nacc_mean,
    power_from_spl_db,
)
from hornlab_search.metrics.spectral import fixed_angle_residual_db
from hornlab_search.types import MetricSet, Response

FREQS = np.geomspace(700.0, 8000.0, 15)
H_ANGLES = np.arange(-90.0, 90.1, 5.0)
V_ANGLES = H_ANGLES
BAND = (700.0, 8000.0)

#: Solver-style structured theta-major balloon. 16 theta rows avoid an equator sample, so the
#: discrete forward-hemisphere area is exactly half of the full-sphere area.
N_THETA, N_PHI = 16, 8
THETA = np.linspace(0.0, 180.0, N_THETA)
PHI = np.arange(N_PHI, dtype=float) * (360.0 / N_PHI)


def _balloon_dirs():
    theta = np.repeat(THETA, N_PHI)
    phi = np.tile(PHI, N_THETA)
    t = np.radians(theta)
    p = np.radians(phi)
    d = np.column_stack([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)])
    return d / np.linalg.norm(d, axis=1, keepdims=True)


DIRS = _balloon_dirs()
DIR_THETA = np.degrees(np.arccos(np.clip(DIRS[:, 2], -1.0, 1.0)))


def _balloon(sigma_deg):
    """Gaussian balloon: ``sigma_deg`` may be a scalar or per-frequency array."""
    sig = np.broadcast_to(np.asarray(sigma_deg, dtype=float), (FREQS.size,))
    return np.vstack([-6.0206 * (DIR_THETA / sig[i]) ** 2 for i in range(FREQS.size)])


def _cuts(sigma_deg, v_shift_deg=None):
    """H/V cuts of the same Gaussian; ``v_shift_deg`` shifts the V beam per frequency."""
    sig = np.broadcast_to(np.asarray(sigma_deg, dtype=float), (FREQS.size,))
    h = np.vstack([-6.0206 * (H_ANGLES / sig[i]) ** 2 for i in range(FREQS.size)])
    if v_shift_deg is None:
        v = h.copy()
    else:
        shift = np.broadcast_to(np.asarray(v_shift_deg, dtype=float), (FREQS.size,))
        v = np.vstack([-6.0206 * ((V_ANGLES - shift[i]) / sig[i]) ** 2
                       for i in range(FREQS.size)])
    return h, v


def _metric_set(di_db):
    n = FREQS.size
    zeros = np.zeros(n)
    return MetricSet(
        freqs_hz=FREQS.copy(), bw_h_deg=zeros + 80.0, bw_v_deg=zeros + 50.0,
        di_db=np.asarray(di_db, dtype=float), di_source="balloon",
        ripple_h_db=zeros.copy(), ripple_v_db=zeros.copy(), on_axis_db=zeros.copy(),
        z_throat_real=None, scalars={})


def _response(spl_h, spl_v, balloon=None):
    return Response(
        freqs_hz=FREQS.copy(), h_angles_deg=H_ANGLES.copy(), v_angles_deg=V_ANGLES.copy(),
        spl_h_db=np.asarray(spl_h, dtype=float), spl_v_db=np.asarray(spl_v, dtype=float),
        balloon_dirs=None if balloon is None else DIRS.copy(),
        spl_balloon_db=None if balloon is None else np.asarray(balloon, dtype=float),
        z_throat=None, meta={} if balloon is None else {"balloon_grid": [N_THETA, N_PHI]})


# --------------------------------------------------------------------------- primitives


def test_power_from_spl_db_floors_non_finite():
    p = power_from_spl_db(np.array([0.0, 10.0, np.nan, -np.inf, np.inf]))
    assert p[0] == pytest.approx(1.0)
    assert p[1] == pytest.approx(10.0)
    assert np.all(p[2:] == pytest.approx(1e-12))
    assert np.all(np.isfinite(p))


def test_log_frequency_weights_trapezoid_and_refusal():
    f = np.array([100.0, 200.0, 400.0, 800.0])           # uniform in log10
    w = log_frequency_weights(f)
    assert w.sum() == pytest.approx(1.0)
    assert w == pytest.approx([0.1666666667, 0.3333333333, 0.3333333333, 0.1666666667])
    masked = log_frequency_weights(f, np.array([False, True, True, True]))
    assert masked[0] == 0.0 and masked.sum() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        log_frequency_weights(np.array([100.0]), None)
    with pytest.raises(ValueError):
        log_frequency_weights(np.array([100.0, 100.0]))
    with pytest.raises(ValueError):
        log_frequency_weights(np.array([0.0, 100.0]))


# --------------------------------------------------------------------------- M4


def test_di_std_matches_hand_weighted_ramp():
    f = np.geomspace(700.0, 8000.0, 12)
    di = 2.0 * np.log10(f / 700.0) + 3.0
    lf = np.log10(f)
    w = np.empty(f.size)
    w[0] = 0.5 * (lf[1] - lf[0])
    w[-1] = 0.5 * (lf[-1] - lf[-2])
    w[1:-1] = 0.5 * (lf[2:] - lf[:-2])
    w /= w.sum()
    mean = np.sum(w * di)
    expected = np.sqrt(np.sum(w * (di - mean) ** 2))
    assert di_std_log_db(f, di, band_hz=BAND) == pytest.approx(expected, rel=1e-12)


def test_di_std_is_zero_for_constant_and_nan_when_short():
    assert di_std_log_db(FREQS, np.full(FREQS.size, 7.5), band_hz=BAND) == pytest.approx(0.0)
    short = np.array([1000.0, 2000.0])
    assert np.isnan(di_std_log_db(short, np.array([1.0, 2.0]), band_hz=BAND))


# --------------------------------------------------------------------------- M5


def test_nacc_matrix_is_one_for_frequency_invariant_pattern():
    g = -6.0206 * (H_ANGLES / 30.0) ** 2
    s = np.tile(g, (FREQS.size, 1))
    m = nacc_matrix(s, H_ANGLES)
    assert m.shape == (FREQS.size, FREQS.size)
    assert np.all(np.diag(m) == pytest.approx(1.0))
    assert m == pytest.approx(np.ones_like(m))


def test_nacc_identical_cuts_is_one_and_shifted_v_is_less():
    g = -6.0206 * (H_ANGLES / 30.0) ** 2
    h = np.tile(g, (FREQS.size, 1))
    same = nacc_mean(FREQS, h, h.copy(), H_ANGLES, V_ANGLES, band_hz=BAND)
    assert same["nacc"] == pytest.approx(1.0)
    assert same["n_pairs"] > 0

    shift = 5.0 * np.log2(FREQS / FREQS[0])          # beam walks with frequency
    v = np.vstack([-6.0206 * ((H_ANGLES - shift[i]) / 30.0) ** 2
                   for i in range(FREQS.size)])
    moved = nacc_mean(FREQS, h, v, H_ANGLES, V_ANGLES, band_hz=BAND)
    assert 0.0 < moved["nacc"] < 1.0


# --------------------------------------------------------------------------- M2 / M3


def test_omni_balloon_lw_zero_and_omega_is_one():
    # Omega_CD = 2*pi for the omni forward region, so Omega_CD/(2*pi) = 1.
    omni = np.zeros((FREQS.size, DIRS.shape[0]))
    lwm = listening_window_metrics(omni, DIRS, [N_THETA, N_PHI], FREQS, band_hz=BAND)
    assert lwm["status"] == "balloon"
    assert lwm["n_dirs"] == DIRS.shape[0]
    assert lwm["lw_distortion_db"] == pytest.approx(0.0, abs=1e-12)
    assert lwm["omega_cd_2pi"] == pytest.approx(1.0, abs=1e-12)
    assert np.allclose(lwm["per_freq_omega_2pi"], 1.0, atol=1e-12)
    assert np.allclose(lwm["per_freq_lw_db"], 0.0, atol=1e-12)


def test_narrowing_gaussian_raises_lw_and_di_std_and_lowers_nacc():
    sigma = 40.0 * (FREQS / FREQS[0]) ** -0.5      # 40 deg at 700 Hz, ~11.8 deg at 8 kHz
    balloon = _balloon(sigma)
    lwm = listening_window_metrics(balloon, DIRS, [N_THETA, N_PHI], FREQS, band_hz=BAND)
    assert lwm["lw_distortion_db"] > 0.1
    assert lwm["status"] == "balloon"

    h, v = _cuts(sigma)
    nm = nacc_mean(FREQS, h, v, H_ANGLES, V_ANGLES, band_hz=BAND)
    assert nm["nacc"] < 1.0

    # DI grows as the pattern narrows, so its log-weighted spread is positive.
    from hornlab_search.metrics.di import di_from_balloon, sin_theta_weights
    w = sin_theta_weights(DIR_THETA)
    axis = int(np.argmax(DIRS[:, 2]))
    di = np.array([di_from_balloon(balloon[i], balloon[i, axis], weights=w)
                   for i in range(FREQS.size)])
    assert np.ptp(di) > 1.0
    assert di_std_log_db(FREQS, di, band_hz=BAND) > 0.5


# --------------------------------------------------------------------------- off-axis


def test_offaxis_flat_is_zero_and_a_bump_is_positive():
    flat = _response(np.zeros((FREQS.size, H_ANGLES.size)),
                     np.zeros((FREQS.size, V_ANGLES.size)))
    flat_out = cd_metrics(_metric_set(np.zeros(FREQS.size)), flat)
    assert flat_out["offaxis_smooth_db"] == pytest.approx(0.0, abs=1e-12)
    assert flat_out["cd_status"] == "cuts_fallback"

    h = np.zeros((FREQS.size, H_ANGLES.size))
    j30 = int(np.argmin(np.abs(H_ANGLES - 30.0)))
    h[:, j30] = 2.0 * (np.log10(FREQS) - np.log10(2500.0))
    bumped = _response(h, np.zeros((FREQS.size, V_ANGLES.size)))
    bump_out = cd_metrics(_metric_set(np.zeros(FREQS.size)), bumped)
    assert bump_out["offaxis_smooth_db"] > 0.05
    assert bump_out["offaxis_smooth_db"] == pytest.approx(
        fixed_angle_residual_db(FREQS, h, H_ANGLES, 30.0, reference="band_mean",
                                band_hz=(2500.0, 8000.0)))


# --------------------------------------------------------------------------- aggregate


def test_omni_response_all_cd_keys():
    omni = np.zeros((FREQS.size, DIRS.shape[0]))
    h = np.zeros((FREQS.size, H_ANGLES.size))
    resp = _response(h, h.copy(), balloon=omni)
    out = cd_metrics(_metric_set(np.zeros(FREQS.size)), resp)
    assert out["cd_status"] == "balloon"
    assert out["cd_lw_db"] == pytest.approx(0.0, abs=1e-12)
    assert out["cd_omega_2pi"] == pytest.approx(1.0, abs=1e-12)
    assert out["cd_di_std_db"] == pytest.approx(0.0, abs=1e-12)
    assert out["cd_nacc"] == pytest.approx(1.0)
    assert out["offaxis_smooth_db"] == pytest.approx(0.0, abs=1e-12)
    assert set(out) == {"cd_lw_db", "cd_omega_2pi", "cd_di_std_db", "cd_nacc",
                        "offaxis_smooth_db", "cd_status"}


def test_no_balloon_falls_back_to_cuts():
    h = -6.0206 * (H_ANGLES[None, :] / 30.0) ** 2 + np.zeros((FREQS.size, 1))
    v = -6.0206 * (V_ANGLES[None, :] / 30.0) ** 2 + np.zeros((FREQS.size, 1))
    resp = _response(h, v)
    out = cd_metrics(_metric_set(np.zeros(FREQS.size)), resp)
    assert out["cd_status"] == "cuts_fallback"
    assert np.isnan(out["cd_omega_2pi"])
    assert np.isfinite(out["cd_lw_db"])
    assert np.isfinite(out["cd_di_std_db"])
    assert np.isfinite(out["cd_nacc"])
    assert np.isfinite(out["offaxis_smooth_db"])


def test_cd_metrics_tolerates_missing_arrays():
    out = cd_metrics(None, None)
    assert out["cd_status"] == "unmeasurable"
    assert all(np.isnan(out[k]) for k in
               ("cd_lw_db", "cd_omega_2pi", "cd_di_std_db", "cd_nacc", "offaxis_smooth_db"))
