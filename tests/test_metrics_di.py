"""Contract tests 9-17 for the directivity-index functions."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import fibonacci_sphere
from hornlab_search.metrics.di import (
    di_from_balloon, di_from_cuts, di_slope_db_per_decade, sin_theta_weights, target_di_db)
from hornlab_search.metrics.polar import beamwidth_deg
from test_metrics_helpers import ON_AXIS_DB, balloon_db, cardioid, cut_db, dipole, omni

DI_3 = 10.0 * np.log10(3.0)          # 4.7712 dB: directivity factor 3


def _di(fn, n=512):
    return di_from_balloon(balloon_db(fn, fibonacci_sphere(n)), ON_AXIS_DB)


# 9
def test_omni_is_zero_db():
    assert _di(omni) == pytest.approx(0.0, abs=0.01)


# 10
def test_dipole_512():
    assert _di(dipole) == pytest.approx(4.771, abs=0.05)


# 11
def test_cardioid_512():
    assert _di(cardioid) == pytest.approx(4.771, abs=0.05)


# 12
def test_cardioid_quadrature_convergence(capsys):
    counts = (128, 512, 1024, 4096)
    errs = [abs(_di(cardioid, n) - DI_3) for n in counts]
    with capsys.disabled():
        print("\ncardioid DI quadrature error (dB): "
              + ", ".join(f"{n}: {e:.3e}" for n, e in zip(counts, errs)))
    assert all(b < a for a, b in zip(errs, errs[1:]))
    assert errs[2] < 0.02


# 13, 14
def test_target_di_75_by_45():
    assert target_di_db(75.0, 45.0) == pytest.approx(11.3, abs=0.1)


def test_target_di_full_sphere_is_zero():
    assert target_di_db(360.0, 180.0) == pytest.approx(0.0, abs=0.1)


# 15
def test_cuts_estimate_agrees_with_balloon_for_omni():
    ang = np.arange(-36, 37) * 2.5
    bw, _ = beamwidth_deg(ang, cut_db(omni, ang))
    assert di_from_cuts(bw, bw) == pytest.approx(_di(omni), abs=0.3)


# 16
def test_cuts_estimate_is_an_estimate_for_a_lobed_pattern():
    """Gaussian beam whose width grows 3x on the diagonals: both cuts read 40 deg,
    the estimate assumes a 40 x 40 rectangle, the true sphere average says otherwise."""
    def pat(theta, phi):
        sig = np.radians(20.0) * (1.0 + 2.0 * np.sin(2.0 * phi) ** 2)
        return np.exp(-np.log(2.0) * (theta / sig) ** 2)

    dirs = fibonacci_sphere(4096)
    theta = np.arccos(dirs[:, 2])
    phi = np.arctan2(dirs[:, 1], dirs[:, 0])
    di_true = di_from_balloon(20.0 * np.log10(pat(theta, phi)), 0.0)

    ang = np.arange(-360, 361) * 0.25
    th = np.radians(np.abs(ang))
    bw_h, _ = beamwidth_deg(ang, 20.0 * np.log10(pat(th, np.zeros_like(th))))
    bw_v, _ = beamwidth_deg(ang, 20.0 * np.log10(pat(th, np.full_like(th, np.pi / 2))))
    assert bw_h == pytest.approx(40.0, abs=0.05) and bw_v == pytest.approx(40.0, abs=0.05)
    assert abs(di_from_cuts(bw_h, bw_v) - di_true) > 1.0


# 17
def test_di_slope_exact():
    f = np.geomspace(500.0, 16000.0, 12)
    assert di_slope_db_per_decade(f, 7.0 + 3.0 * np.log10(f)) == pytest.approx(3.0, abs=1e-9)
    assert di_slope_db_per_decade(f, np.full(f.shape, 9.0)) == pytest.approx(0.0, abs=1e-9)


# ---- additions

def test_power_average_not_db_average():
    # One point at 0 dB and one at -inf dB: power mean 0.5 -> DI 3.01 dB.
    # An (incorrect) dB mean would be -inf.
    assert di_from_balloon(np.array([0.0, -np.inf]), 0.0) == pytest.approx(10 * np.log10(2), abs=1e-12)


def test_theta_phi_grid_needs_sin_theta_weights():
    """The solver's real balloon is a theta-major theta-phi grid, not equal-area."""
    n_theta, n_phi = 91, 72
    theta = np.linspace(0.0, 180.0, n_theta)
    th = np.repeat(theta, n_phi)                       # theta-major, phi fastest
    p = (1.0 + np.cos(np.radians(th))) / 2.0
    spl = ON_AXIS_DB + 20.0 * np.log10(np.maximum(p, 1e-12))
    w = sin_theta_weights(th)
    assert di_from_balloon(spl, ON_AXIS_DB, weights=w) == pytest.approx(DI_3, abs=0.01)
    assert abs(di_from_balloon(spl, ON_AXIS_DB) - DI_3) > 0.5      # equal weights are wrong here
    with pytest.raises(ValueError):
        di_from_balloon(spl, ON_AXIS_DB, weights=w[:-1])


def test_dead_balloon_is_finite():
    assert di_from_balloon(np.full(512, -np.inf), -np.inf) == 0.0
    assert di_from_balloon(np.full(512, -np.inf), 94.0) == 0.0


def test_cuts_estimate_saturation_convention():
    assert di_from_cuts(180.0, 180.0) == 0.0
    assert di_from_cuts(180.0, 90.0) == pytest.approx(di_from_cuts(360.0, 90.0))
    assert di_from_cuts(90.0, 90.0) > di_from_cuts(120.0, 120.0) > 0.0
