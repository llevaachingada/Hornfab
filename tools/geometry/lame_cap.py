"""Lame (superellipse) section and superellipsoid-cap area math for the Klangfilm-Lame family.

Production port of the 2026-11-16 senior reference (``02_LAME_CAP_MATH_REFERENCE.py``). The radial fixed-ray
form is OUR generalisation (``superellipsoid_cap_v1``), NOT Ahlswede's unpublished 2019 calculator. At p = 2 it
reduces to the published tri-axial ellipsoid cap; at a = b = c0, p = 2 it is the sphere (area 2 pi c0 h).
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq
from scipy.special import gammaln

MODEL_ID = "superellipsoid_cap_v1"


@lru_cache(maxsize=16)
def _nodes(order):
    if order < 8:
        raise ValueError("quadrature order must be >= 8")
    return leggauss(order)


def quintic(t):
    """C2 gate Q(t) = 6t^5 - 15t^4 + 10t^3 clipped to [0, 1]; Q'(0)=Q''(0)=Q'(1)=Q''(1)=0."""
    t = np.clip(np.asarray(t, dtype=float), 0.0, 1.0)
    return t * t * t * (10.0 + t * (-15.0 + 6.0 * t))


def dquintic(t):
    t = np.clip(np.asarray(t, dtype=float), 0.0, 1.0)
    return 30.0 * t * t * (1.0 - t) ** 2


def flat_lame_area(a, b, p):
    if min(a, b) <= 0 or p < 2:
        raise ValueError("a, b > 0 and p >= 2 required")
    return float(a * b * math.exp(math.log(4.0) + 2.0 * gammaln(1.0 + 1.0 / p) - gammaln(1.0 + 2.0 / p)))


def radial_lame(phi, a, b, p):
    """rho(phi) and d rho / d phi on [0, pi/2] (no singular angular mapping)."""
    if min(a, b) <= 0 or p < 2:
        raise ValueError("a, b > 0 and p >= 2 required")
    phi = np.asarray(phi, dtype=float)
    co, si = np.cos(phi), np.sin(phi)
    d = (co / a) ** p + (si / b) ** p
    rho = d ** (-1.0 / p)
    dlog = ((co ** (p - 1) * si / a ** p) - (si ** (p - 1) * co / b ** p)) / d
    return rho, rho * dlog


def lame_cap_area(a, b, c, h, p=2.0, order=24):
    """Curved area of P(theta, phi) = (rho sin(theta) cos(phi), rho sin(theta) sin(phi), c cos(theta))."""
    if min(a, b, c) <= 0 or p < 2 or not 0.0 <= h <= 2.0 * c:
        raise ValueError("a, b, c > 0; p >= 2; 0 <= h <= 2c required")
    if h == 0.0:
        return 0.0
    x, w = _nodes(int(order))
    th_max = math.acos(min(1.0, max(-1.0, 1.0 - h / c)))
    theta, wt = (x + 1.0) * th_max / 2.0, w * th_max / 2.0
    phi, wp = (x + 1.0) * math.pi / 4.0, w * math.pi / 4.0
    rho, drho = radial_lame(phi, a, b, p)
    s, co = np.sin(theta)[:, None], np.cos(theta)[:, None]
    jac = s * np.sqrt(c * c * s * s * (rho[None, :] ** 2 + drho[None, :] ** 2) + rho[None, :] ** 4 * co * co)
    return float(4.0 * np.sum(jac * wt[:, None] * wp[None, :]))


def area_locked_axes(target_area, aspect, c, h, p, order=24, rtol=1e-10):
    """(a, b) with a/b = aspect and cap area == target_area (ratio-locked ``curved_cap_ratio_locked`` mode)."""
    if not (target_area > 0 and aspect > 0 and c > 0 and h > 0 and h <= 2 * c and p >= 2):
        raise ValueError("positive target/aspect/c/h; h <= 2c; p >= 2 required")

    def f(b):
        return lame_cap_area(aspect * b, b, c, h, p, order) - target_area

    hi = math.sqrt(target_area / (math.pi * aspect))
    lo = hi * 1e-3
    for _ in range(80):
        if f(hi) >= 0:
            break
        hi *= 2.0
    else:
        raise ValueError("could not bracket the cap-area root (upper)")
    if f(lo) > 0:
        raise ValueError("could not bracket the cap-area root (lower)")
    b = brentq(f, lo, hi, xtol=1e-13, rtol=rtol)
    return aspect * b, b


def legacy_ellipsoid_cap_area(a, b, c, h, order=96):
    """Independent p = 2 reference with the 2018 spherical-angle integrand (tests only)."""
    x, w = _nodes(order)
    tm = math.acos(1.0 - h / c)
    th, wt = (x + 1.0) * tm / 2.0, w * tm / 2.0
    ph, wp = (x + 1.0) * math.pi, w * math.pi
    st, ct = np.sin(th)[:, None], np.cos(th)[:, None]
    cp, sp = np.cos(ph)[None, :], np.sin(ph)[None, :]
    jac = st * np.sqrt(c * c * st * st * (b * b * cp * cp + a * a * sp * sp) + a * a * b * b * ct * ct)
    return float(np.sum(jac * wt[:, None] * wp[None, :]))
