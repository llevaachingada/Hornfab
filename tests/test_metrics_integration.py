"""Contract tests 31-35 for compute_metrics on synthetic Responses."""
from __future__ import annotations

import dataclasses
import logging
import math

import numpy as np
import pytest

from conftest import FAKE_FREQS
from hornlab_search.constants import BESSEL_J1P_11, C_AIR, KEELE_K
from hornlab_search.metrics.compute import SCALAR_KEYS, compute_metrics, reset_warning_state
from hornlab_search.targets.spec import Target
from test_metrics_helpers import cardioid, dipole, make_response

DI_3 = 10.0 * np.log10(3.0)
DOCUMENTED_KEYS = {
    "n_freqs", "di_source", "n_multilobe_h", "n_multilobe_v", "n_nan_ripple",
    "bw_h_mean_deg", "bw_v_mean_deg", "di_mean_db", "di_slope_db_per_dec",
    "ripple_mean_db", "flatness_db", "f_break_h_hz", "f_break_v_hz", "f11_hz",
}
TARGET = Target(75.0, 45.0, 700.0, 13000.0, None)


def _take(resp, n):
    return dataclasses.replace(
        resp, freqs_hz=resp.freqs_hz[:n], spl_h_db=resp.spl_h_db[:n], spl_v_db=resp.spl_v_db[:n],
        spl_balloon_db=resp.spl_balloon_db[:n], z_throat=resp.z_throat[:n])


# 31
def test_fake_response_cardioid(fake_response):
    m = compute_metrics(fake_response, TARGET)
    assert m.freqs_hz.shape == (12,) and tuple(m.freqs_hz) == tuple(FAKE_FREQS)
    assert np.allclose(m.bw_h_deg, 180.0, atol=0.05) and np.allclose(m.bw_v_deg, 180.0, atol=0.05)
    assert np.allclose(m.di_db, 4.771, atol=0.05)
    assert m.di_source == "balloon"
    assert m.scalars["di_source"] == "balloon"
    assert m.scalars["n_freqs"] == 12
    assert m.scalars["n_multilobe_h"] == 0 and m.scalars["n_nan_ripple"] == 0
    assert m.scalars["di_slope_db_per_dec"] == pytest.approx(0.0, abs=1e-9)
    assert m.scalars["flatness_db"] == pytest.approx(0.0, abs=1e-9)
    assert np.allclose(m.on_axis_db, 0.0, atol=1e-9)
    assert m.z_throat_real is not None and m.z_throat_real.shape == (12,)
    for arr in (m.bw_h_deg, m.bw_v_deg, m.di_db, m.ripple_h_db, m.ripple_v_db, m.on_axis_db):
        assert arr.shape == (12,) and np.all(np.isfinite(arr))


# 32
def test_short_sweep_never_reaches_for_a_twelfth(fake_response):
    short = _take(fake_response, 9)
    m = compute_metrics(short, TARGET)
    assert m.scalars["n_freqs"] == 9
    for arr in (m.freqs_hz, m.bw_h_deg, m.bw_v_deg, m.di_db, m.ripple_h_db, m.ripple_v_db,
                m.on_axis_db, m.z_throat_real):
        assert arr.shape == (9,)


def test_arrays_not_matching_freqs_raise(fake_response):
    bad = dataclasses.replace(fake_response, spl_h_db=fake_response.spl_h_db[:9])
    with pytest.raises(ValueError):
        compute_metrics(bad, TARGET)


# 33
@pytest.mark.parametrize("drop", ["dirs_only", "dirs_and_spl"])
def test_no_balloon_falls_back_to_cuts_estimate_with_warning(fake_response, caplog, drop):
    reset_warning_state()
    resp = dataclasses.replace(
        fake_response, balloon_dirs=None,
        spl_balloon_db=None if drop == "dirs_and_spl" else fake_response.spl_balloon_db)
    with caplog.at_level(logging.WARNING, logger="hornlab_search.metrics.compute"):
        m = compute_metrics(resp, TARGET)
        compute_metrics(resp, TARGET)                    # second call: no second warning
    assert m.di_source == "cuts_estimate" and m.scalars["di_source"] == "cuts_estimate"
    assert np.all(np.isfinite(m.di_db))
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warns) == 1 and "cuts_estimate" in warns[0].getMessage()


# 34
@pytest.mark.parametrize("dead", [-np.inf, 0.0])
def test_dead_frequency_makes_no_inf_and_no_unexplained_nan(fake_response, dead):
    resp = dataclasses.replace(
        fake_response, spl_h_db=fake_response.spl_h_db.copy(), spl_v_db=fake_response.spl_v_db.copy(),
        spl_balloon_db=fake_response.spl_balloon_db.copy())
    resp.spl_h_db[3] = dead
    resp.spl_v_db[3] = dead
    resp.spl_balloon_db[3] = dead
    m = compute_metrics(resp, TARGET)
    for arr in (m.bw_h_deg, m.bw_v_deg, m.di_db, m.on_axis_db):
        assert np.all(np.isfinite(arr))
    n_nan = int(np.isnan(m.ripple_h_db).sum() + np.isnan(m.ripple_v_db).sum())
    assert n_nan == m.scalars["n_nan_ripple"]
    assert not np.any(np.isinf(m.ripple_h_db)) and not np.any(np.isinf(m.ripple_v_db))
    if dead == -np.inf:
        assert n_nan == 2 and m.bw_h_deg[3] == 180.0 and m.di_db[3] == 0.0
        assert m.on_axis_db[3] == -120.0
    else:                                   # flat 0 dB everywhere: an omni pattern
        assert n_nan == 0 and m.ripple_h_db[3] == 0.0 and m.di_db[3] == pytest.approx(0.0, abs=1e-9)
    for k in ("bw_h_mean_deg", "di_mean_db", "ripple_mean_db", "flatness_db", "di_slope_db_per_dec"):
        assert np.isfinite(m.scalars[k])


# 35
def test_scalars_have_exactly_the_documented_keys(fake_response, rng):
    assert set(SCALAR_KEYS) == DOCUMENTED_KEYS and len(SCALAR_KEYS) == len(DOCUMENTED_KEYS)
    dead = dataclasses.replace(fake_response, spl_h_db=np.full_like(fake_response.spl_h_db, -np.inf))
    cases = [
        compute_metrics(fake_response, TARGET),
        compute_metrics(_take(fake_response, 9), TARGET),
        compute_metrics(_take(fake_response, 1), TARGET),
        compute_metrics(dataclasses.replace(fake_response, balloon_dirs=None), TARGET),
        compute_metrics(dataclasses.replace(fake_response, z_throat=None), TARGET),
        compute_metrics(dead, TARGET),
        compute_metrics(fake_response, TARGET, mouth_h_m=0.4, mouth_v_m=0.3, throat_radius_m=0.0254),
        compute_metrics(make_response(dipole), Target(120.0, 120.0, 100.0, 200.0, 4.0)),   # band outside
    ]
    for m in cases:
        assert set(m.scalars) == DOCUMENTED_KEYS


def test_band_fallback_and_single_frequency_are_finite(fake_response):
    m = compute_metrics(_take(fake_response, 1), TARGET)
    assert m.scalars["n_freqs"] == 1 and np.isfinite(m.scalars["bw_h_mean_deg"])


def test_z_throat_none_gives_none(fake_response):
    m = compute_metrics(dataclasses.replace(fake_response, z_throat=None), TARGET)
    assert m.z_throat_real is None


def test_design_checks_use_constants(fake_response):
    m = compute_metrics(fake_response, TARGET, mouth_h_m=0.5, mouth_v_m=0.4, throat_radius_m=0.0254)
    assert m.scalars["f_break_h_hz"] == pytest.approx(KEELE_K / (0.5 * 75.0))
    assert m.scalars["f_break_v_hz"] == pytest.approx(KEELE_K / (0.4 * 45.0))
    assert m.scalars["f11_hz"] == pytest.approx(BESSEL_J1P_11 * C_AIR / (2 * math.pi * 0.0254))
    # constants.py quotes 7914 Hz for "1.0 in" and 3957 Hz for "2.0 in": those are throat
    # DIAMETERS (radius 12.7 mm and 25.4 mm), since f11 uses the radius a.
    assert m.scalars["f11_hz"] == pytest.approx(3957.0, abs=2.0)
    m2 = compute_metrics(fake_response, TARGET, throat_radius_m=0.0127)
    assert m2.scalars["f11_hz"] == pytest.approx(7914.0, abs=2.0)
    no = compute_metrics(fake_response, TARGET)
    assert all(math.isnan(no.scalars[k]) for k in ("f_break_h_hz", "f_break_v_hz", "f11_hz"))


def test_dipole_response_end_to_end():
    m = compute_metrics(make_response(dipole), TARGET)
    assert np.allclose(m.bw_h_deg, 120.0, atol=0.05) and np.allclose(m.di_db, DI_3, atol=0.05)


def test_multilobe_is_counted():
    ang_resp = make_response(lambda t: np.abs(np.cos(3.0 * t)))        # lobes at 0, 60 deg; nulls at 30
    m = compute_metrics(ang_resp, TARGET)
    assert m.scalars["n_multilobe_h"] == 3 and m.scalars["n_multilobe_v"] == 3
