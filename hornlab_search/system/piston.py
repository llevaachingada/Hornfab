"""Analytic circular-piston directivity — a **screening benchmark only**.

The model is the classical far-field pressure of an ideal rigid circular piston of radius ``a``
mounted in an infinite baffle and moving uniformly (Rayleigh/Sommerfeld half-space solution):

    D(theta) = 2 * J1(x) / x,        x = k * a * sin(theta),        k = 2*pi*f / c

with ``J1`` the Bessel function of the first kind of order one. ``D(0) = 1`` by the limit
``J1(x)/x -> 1/2``, the pattern is symmetric in ``+/- theta``, and ``D`` first reaches -6 dB at
the angle where ``20 log10|D| = -6`` (``nan`` when the pattern never falls that far by 90 deg,
e.g. very low ``ka``).

**SCREENING BENCHMARK ONLY — ideal rigid uniformly moving piston in an infinite baffle; no cone
breakup, no finite baffle, not a paper-cone model; never claim a real driver's DI from this.**
It ignores the surround, dust cap, cone bending, the cabinet edge and the horn, so its numbers are
an upper-bound geometry benchmark, not a prediction for any physical driver.

Time convention is irrelevant to a real magnitude pattern and is not claimed here.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.special import j1

try:  # the repo constant is the canonical air speed (343 m/s at 20 C)
    from hornlab_search.constants import C_AIR as _DEFAULT_C
except ImportError:  # pragma: no cover - the package always ships constants.py
    _DEFAULT_C = 343.0

__all__ = [
    "piston_directivity",
    "first_minus6db_angle",
    "ka",
    "SPEED_OF_SOUND_MPS",
]

SPEED_OF_SOUND_MPS: float = float(_DEFAULT_C)

_TINY = 1e-300


def _check_radius(a_m: float) -> float:
    a = float(a_m)
    if not (math.isfinite(a) and a > 0.0):
        raise ValueError(f"piston radius a_m must be finite and > 0, got {a_m!r}")
    return a


def _check_c(c: float | None) -> float:
    speed = SPEED_OF_SOUND_MPS if c is None else float(c)
    if not (math.isfinite(speed) and speed > 0.0):
        raise ValueError(f"speed of sound c must be finite and > 0, got {c!r}")
    return speed


def ka(f: Any, a_m: float, c: float | None = None) -> Any:
    """Dimensionless ``k a = 2*pi*f*a/c`` (array/scalar in ``f``)."""
    a = _check_radius(a_m)
    speed = _check_c(c)
    freq = np.asarray(f, dtype=float)
    if np.any(~np.isfinite(freq)) or np.any(freq < 0.0):
        raise ValueError("frequency must be finite and >= 0")
    out = 2.0 * math.pi * freq * a / speed
    return float(out) if out.ndim == 0 else out


def piston_directivity(
    f: Any,
    a_m: float,
    theta_deg: Any,
    c: float | None = None,
) -> Any:
    """Complex-free pressure directivity ``2 J1(x)/x`` at angle ``theta_deg`` off axis.

    ``f`` and ``theta_deg`` must broadcast together (a scalar ``f`` with a vector of angles is
    the usual call). Returns a real ndarray/scalar; the sign follows the Bessel zero crossings,
    so use ``abs`` for a magnitude/dB claim.
    """
    a = _check_radius(a_m)
    speed = _check_c(c)
    freq = np.asarray(f, dtype=float)
    if np.any(~np.isfinite(freq)) or np.any(freq < 0.0):
        raise ValueError("frequency must be finite and >= 0")
    theta = np.asarray(theta_deg, dtype=float)
    if np.any(~np.isfinite(theta)):
        raise ValueError("theta_deg must be finite")

    x = (2.0 * math.pi * freq / speed) * a * np.sin(np.radians(theta))
    x_arr = np.asarray(x, dtype=float)
    out = np.ones_like(x_arr, dtype=float)
    nonzero = x_arr != 0.0
    out[nonzero] = 2.0 * j1(x_arr[nonzero]) / x_arr[nonzero]
    return float(out) if out.ndim == 0 else out


def first_minus6db_angle(f: Any, a_m: float, c: float | None = None) -> float:
    """First angle [deg, 0..90] on the main lobe where ``20 log10|D|`` reaches -6 dB.

    Returns ``nan`` when the ideal piston never reaches -6 dB within 90 deg (small ``ka``).
    The search uses a dense linear grid plus a linear interpolation of the dB curve; it is a
    deterministic benchmark, not a physical measurement.
    """
    speed = _check_c(c)
    a = _check_radius(a_m)
    freq = np.asarray(f, dtype=float)
    if np.any(~np.isfinite(freq)) or np.any(freq < 0.0):
        raise ValueError("frequency must be finite and >= 0")

    grid = np.linspace(0.0, 90.0, 9001)
    d = np.abs(np.asarray(piston_directivity(freq, a, grid, c=speed), dtype=float))
    db = 20.0 * np.log10(np.maximum(d, _TINY))
    below = db <= -6.0
    if not bool(np.any(below)) or bool(below[0]):
        # either the pattern never falls 6 dB by 90 deg, or (degenerate) it is < -6 at 0 deg
        return math.nan
    idx = int(np.argmax(below))
    a0, a1 = grid[idx - 1], grid[idx]
    y0, y1 = db[idx - 1], db[idx]
    if y1 == y0:  # pragma: no cover - a step exactly on the threshold
        return float(a1)
    return float(a0 + (a1 - a0) * (-6.0 - y0) / (y1 - y0))
