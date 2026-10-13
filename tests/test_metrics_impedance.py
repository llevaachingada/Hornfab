"""Contract tests 24-25 for the throat impedance."""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.constants import C_AIR, RHO_AIR
from hornlab_search.metrics.impedance import normalized_throat_impedance


# 24
def test_plane_wave_is_exactly_one():
    u = np.array([1.0, 0.3 + 0.2j, -2.0j])
    p = RHO_AIR * C_AIR * u
    z = normalized_throat_impedance(p, u, 1e-3)
    assert np.allclose(z, 1.0 + 0.0j, rtol=0, atol=1e-15)


# 25
def test_volume_velocity_path_gives_the_same_answer():
    u = np.array([1.0, 0.3 + 0.2j, -2.0j])
    area = 5.07e-4
    p = RHO_AIR * C_AIR * u
    z_u = normalized_throat_impedance(p, u, area)
    z_q = normalized_throat_impedance(p, u * area, area, is_volume_velocity=True)
    assert np.allclose(z_q, z_u, rtol=1e-14, atol=0)
    assert np.allclose(z_q, 1.0 + 0.0j, rtol=0, atol=1e-14)


def test_volume_velocity_needs_positive_area():
    with pytest.raises(ValueError):
        normalized_throat_impedance(1.0, 1.0, None, is_volume_velocity=True)
    with pytest.raises(ValueError):
        normalized_throat_impedance(1.0, 1.0, 0.0, is_volume_velocity=True)
