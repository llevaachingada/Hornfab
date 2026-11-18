"""Tests for ``hornlab_search.system.piston`` (analytic piston screening benchmark).

These pin the closed-form properties only: axis value, symmetry, monotonicity while the main lobe
lasts, the first -6 dB angle against an independent dense grid, and the ``ka -> 0`` limit.
Nothing here claims a real driver's DI.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.special import j1

REPO = Path(__file__).resolve().parents[2]

from hornlab_search.constants import C_AIR  # noqa: E402
from hornlab_search.system import piston  # noqa: E402


def _hand_d(x: float) -> float:
    """Independent closed form used by the test (not the module's helper)."""
    if x == 0.0:
        return 1.0
    return 2.0 * j1(x) / x


def test_axis_is_unity() -> None:
    for f in (20.0, 500.0, 8000.0):
        d = piston.piston_directivity(f, 0.05, 0.0)
        assert d == pytest.approx(1.0, rel=0.0, abs=1e-12)


def test_angular_symmetry() -> None:
    theta = np.linspace(-90.0, 90.0, 361)
    d = piston.piston_directivity(2500.0, 0.08, theta)
    np.testing.assert_allclose(d, d[::-1], rtol=0.0, atol=1e-15)


def test_monotone_nonincreasing_inside_the_main_lobe() -> None:
    """For ka = 2 the pattern has not reached the first Bessel zero, so D falls monotonically."""
    a = 0.05
    f = C_AIR / (math.pi * a)          # ka = 2*pi*f*a/c = 2
    assert piston.ka(f, a) == pytest.approx(2.0, rel=1e-12)
    theta = np.linspace(0.0, 90.0, 901)
    d = piston.piston_directivity(f, a, theta)
    assert np.all(d > 0.0)
    assert np.all(np.diff(d) <= 1e-15), "piston main-lobe magnitude must be monotone nonincreasing"


def test_first_minus6db_angle_matches_an_independent_dense_search() -> None:
    a = 0.1
    f = 6000.0
    k = 2.0 * math.pi * f / C_AIR

    def db_plus_6(theta_deg: float) -> float:
        x = k * a * math.sin(math.radians(theta_deg))
        if x == 0.0:
            return 6.0
        return 20.0 * math.log10(abs(_hand_d(x))) + 6.0

    scan = np.linspace(0.1, 90.0, 4000)
    values = np.array([db_plus_6(t) for t in scan])
    crossings = np.where((values[:-1] > 0.0) & (values[1:] <= 0.0))[0]
    assert crossings.size, "the hand-chosen ka has no -6 dB crossing"
    i = int(crossings[0])
    root = brentq(db_plus_6, scan[i], scan[i + 1], xtol=1e-12)

    got = piston.first_minus6db_angle(f, a)
    assert got == pytest.approx(root, abs=0.2), f"got {got:.4f} deg, dense grid {root:.4f} deg"


def test_ka_to_zero_is_omnidirectional() -> None:
    theta = np.linspace(-90.0, 90.0, 361)
    d = piston.piston_directivity(1.0, 1e-3, theta)
    assert float(piston.ka(1.0, 1e-3)) < 1e-4
    np.testing.assert_allclose(d, 1.0, rtol=0.0, atol=1e-6)
    assert math.isnan(piston.first_minus6db_angle(1.0, 1e-3))
