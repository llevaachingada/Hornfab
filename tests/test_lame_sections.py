import math

import numpy as np
import pytest
from scipy.integrate import quad

from hornlab_search.design.generators.section_lame import (
    flat_area_axes, polar_radius, smootherstep, superellipse_area_coefficient,
)


def test_coefficient_and_flat_axes():
    assert superellipse_area_coefficient(2) == pytest.approx(math.pi)
    assert superellipse_area_coefficient(4) > math.pi
    for p in (2, 4, 6):
        a, b = flat_area_axes(123.0, 1.7, p)
        assert a / b == pytest.approx(1.7)
        assert superellipse_area_coefficient(p) * a * b == pytest.approx(123.0)
        area, _ = quad(lambda phi: 2 * polar_radius(phi, a, b, p)**2,
                       0, math.pi / 2, epsabs=1e-9)
        assert area == pytest.approx(123.0, rel=1e-9)


def test_polar_axes_circle_and_symmetry():
    assert polar_radius(0, 3, 2, 4) == pytest.approx(3)
    assert polar_radius(math.pi / 2, 3, 2, 4) == pytest.approx(2)
    angles = np.linspace(-math.pi, math.pi, 101)
    assert np.allclose(polar_radius(angles, 2, 2, 2), 2)
    assert np.allclose(polar_radius(angles, 3, 2, 4),
                       polar_radius(-angles, 3, 2, 4))


def test_smootherstep_endpoints_and_monotonicity():
    t = np.linspace(0, 1, 1001)
    y = smootherstep(t)
    assert y[0] == 0 and y[-1] == 1
    assert np.all(np.diff(y) >= 0)
    assert smootherstep(0.5) == pytest.approx(0.5)
    assert smootherstep(1e-4) < 1e-10
    assert 1 - smootherstep(1 - 1e-4) < 1e-10


@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan])
def test_invalid_positive_values(value):
    with pytest.raises(ValueError): superellipse_area_coefficient(value)
    with pytest.raises(ValueError): flat_area_axes(value, 1, 2)
    with pytest.raises(ValueError): flat_area_axes(1, value, 2)
    with pytest.raises(ValueError): polar_radius(0, value, 1, 2)


@pytest.mark.parametrize("value", [-0.1, 1.1, math.inf, math.nan])
def test_invalid_progress(value):
    with pytest.raises(ValueError): smootherstep(value)


def test_invalid_angle():
    with pytest.raises(ValueError): polar_radius([0, math.nan], 1, 1, 2)
