"""Phasor conventions, in one place (idea after Boundary Lab 0.5.0 ``phasor.py``; independent).

Ours: every complex quantity from ``solve/`` uses ``exp(-i omega t)`` (the vendored BEAT engine in
hornlab-beat-bem) and the driver is a unit normal ACCELERATION on tag 2 (``dataset/record.py``,
Collin Q #10). Boundary Lab / BEAT 0.6.0 request ``exp(+i omega t)`` and drive ``normal_velocity``
ports with 1 m/s.

Magnitudes (SPL, beamwidth, DI, ripple) are convention-free. Phase, group delay and the imaginary
part of impedance are NOT: convert before comparing anything complex across tools.
"""
from __future__ import annotations

import numpy as np

OURS = "exp(-i omega t)"
BOUNDARY_LAB = "exp(+i omega t)"
_CONVENTIONS = (OURS, BOUNDARY_LAB)


def convert_time_convention(values, source: str, target: str = OURS) -> np.ndarray:
    """Re(P e^{+i w t}) == Re(conj(P) e^{-i w t}): switching conventions is a complex conjugate."""
    for c in (source, target):
        if c not in _CONVENTIONS:
            raise ValueError(f"unknown phasor convention {c!r}; expected one of {_CONVENTIONS}")
    v = np.asarray(values, dtype=complex)
    return v if source == target else np.conj(v)


def velocity_to_acceleration_drive(p_per_unit_velocity, freqs_hz, convention: str = OURS) -> np.ndarray:
    """Pressure per unit normal ACCELERATION from pressure per unit normal VELOCITY.

    In ``exp(-i w t)``: a = dv/dt = -i w v, so a unit acceleration needs v = 1/(-i w) and the
    response scales by that factor (``record.py``: p_accel = p_vel / (-i w)). In ``exp(+i w t)``
    the factor is 1/(+i w). ``freqs_hz`` broadcasts against the LEADING axis of the pressures.
    """
    if convention not in _CONVENTIONS:
        raise ValueError(f"unknown phasor convention {convention!r}")
    p = np.asarray(p_per_unit_velocity, dtype=complex)
    w = 2.0 * np.pi * np.asarray(freqs_hz, dtype=float)
    if np.any(w <= 0):
        raise ValueError("frequencies must be > 0")
    w = w.reshape((-1,) + (1,) * (p.ndim - 1))
    sign = -1.0 if convention == OURS else 1.0
    return p / (sign * 1j * w)


def boundary_lab_to_ours(p_blab_per_velocity, freqs_hz) -> np.ndarray:
    """A Boundary Lab / BEAT 0.6.0 pressure (exp(+i w t), 1 m/s velocity basis) expressed in our
    convention (exp(-i w t), unit acceleration basis), ready to compare with ``Response.p_*``."""
    ours_vel = convert_time_convention(p_blab_per_velocity, BOUNDARY_LAB, OURS)
    return velocity_to_acceleration_drive(ours_vel, freqs_hz, OURS)
