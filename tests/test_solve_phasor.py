"""solve/phasor.py checked against the time domain, not against its own algebra."""
import numpy as np
import pytest

from hornlab_search.solve import phasor

F = 1000.0
W = 2 * np.pi * F
T = np.linspace(0.0, 2.0 / F, 4001)


def _signal(P, convention):
    sign = 1.0 if convention == phasor.BOUNDARY_LAB else -1.0
    return np.real(P * np.exp(sign * 1j * W * T))


def test_time_convention_switch_preserves_the_real_signal():
    P = 0.7 * np.exp(1j * 0.9)
    q = phasor.convert_time_convention(P, phasor.BOUNDARY_LAB, phasor.OURS)
    assert np.allclose(_signal(P, phasor.BOUNDARY_LAB), _signal(q, phasor.OURS), atol=1e-12)
    assert phasor.convert_time_convention(P, phasor.OURS, phasor.OURS) == P
    with pytest.raises(ValueError):
        phasor.convert_time_convention(P, "exp(i t)")


@pytest.mark.parametrize("conv", [phasor.OURS, phasor.BOUNDARY_LAB])
def test_velocity_to_acceleration_matches_a_time_derivative(conv):
    # a linear system: pressure p(t) per unit velocity. Drive with velocity v(t) whose derivative
    # is a UNIT acceleration amplitude; the converted phasor must reproduce that pressure signal.
    p_vel = 0.3 - 0.4j                                   # response to v = 1 (unit velocity phasor)
    p_acc = phasor.velocity_to_acceleration_drive(np.array([p_vel]), [F], conv)[0]
    sign = 1.0 if conv == phasor.BOUNDARY_LAB else -1.0
    v_phasor = 1.0 / (sign * 1j * W)                     # velocity giving a unit acceleration
    v = _signal(v_phasor, conv)
    a = np.gradient(v, T)
    assert np.isclose(np.max(np.abs(a)), 1.0, rtol=1e-3)  # it really is a unit acceleration
    assert np.allclose(_signal(p_acc, conv), _signal(p_vel * v_phasor, conv), atol=1e-12)


def test_boundary_lab_to_ours_magnitude_and_shapes():
    p = np.ones((3, 5)) * (2 + 1j)
    f = np.array([500.0, 1000.0, 2000.0])
    out = phasor.boundary_lab_to_ours(p, f)
    assert out.shape == (3, 5)
    assert np.allclose(np.abs(out[:, 0]), abs(2 + 1j) / (2 * np.pi * f))
    with pytest.raises(ValueError):
        phasor.velocity_to_acceleration_drive(p, [0.0, 1.0, 2.0])
