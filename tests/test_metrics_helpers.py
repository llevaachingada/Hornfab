"""Shared synthetic-pattern helpers for the metrics tests (no tests in this module).

Patterns are given as pressure-magnitude functions of the angle from +Z, theta in
radians (axisymmetric), or of (theta, phi) for the lobed case.
"""
from __future__ import annotations

import numpy as np

from conftest import fibonacci_sphere
from hornlab_search.types import Response

ON_AXIS_DB = 94.0


def probe_angles(count: int = 73) -> np.ndarray:
    """The contract's probe grid: count odd samples, -90..+90 inclusive, exact 0."""
    half = (count - 1) // 2
    return np.arange(-half, half + 1) * (180.0 / (count - 1))


def to_db(p) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(np.abs(np.asarray(p, dtype=float)))


def cut_db(fn, angles_deg) -> np.ndarray:
    """Axisymmetric pattern fn(theta_rad) on a cut, absolute dB with ON_AXIS_DB on axis."""
    p = fn(np.radians(np.asarray(angles_deg, dtype=float)))
    return ON_AXIS_DB + to_db(p / fn(np.zeros(1))[0])


def balloon_db(fn, dirs) -> np.ndarray:
    """Axisymmetric pattern on unit vectors, +Z on axis."""
    theta = np.arccos(np.clip(dirs[:, 2], -1.0, 1.0))
    return ON_AXIS_DB + to_db(fn(theta) / fn(np.zeros(1))[0])


def omni(theta):
    return np.ones_like(theta)


def dipole(theta):
    return np.cos(theta)


def cardioid(theta):
    return (1.0 + np.cos(theta)) / 2.0


def make_response(fn, freqs=(1000.0, 2000.0, 4000.0), n_balloon: int = 512,
                  angle_count: int = 73) -> Response:
    """Frequency-independent Response for an axisymmetric pattern."""
    freqs = np.asarray(freqs, dtype=float)
    ang = probe_angles(angle_count)
    dirs = fibonacci_sphere(n_balloon)
    cut = cut_db(fn, ang)
    bal = balloon_db(fn, dirs)
    nf = freqs.size
    return Response(
        freqs_hz=freqs, h_angles_deg=ang.copy(), v_angles_deg=ang.copy(),
        spl_h_db=np.tile(cut, (nf, 1)), spl_v_db=np.tile(cut, (nf, 1)),
        balloon_dirs=dirs, spl_balloon_db=np.tile(bal, (nf, 1)),
        z_throat=np.ones(nf, dtype=complex), backend="fake",
    )
