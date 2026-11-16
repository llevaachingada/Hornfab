"""Pure Lamé section geometry; planar area is not curved wavefront area.

Angles are radians from the positive horizontal axis.  These functions do not
register a generator or prescribe a morph schedule.
"""
import math

import numpy as np
from scipy.special import gammaln


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def superellipse_area_coefficient(p):
    """Return C(p) for planar area C(p)*a*b, with positive exponent p."""
    p = _positive(p, "p")
    return float(4.0 * math.exp(2.0 * gammaln(1.0 + 1.0 / p)
                                - gammaln(1.0 + 2.0 / p)))


def flat_area_axes(area, aspect, p):
    """Return positive semi-axes (a, b) with a/b=aspect and planar area=area."""
    area = _positive(area, "area")
    aspect = _positive(aspect, "aspect")
    coefficient = superellipse_area_coefficient(p)
    # Log arithmetic avoids intermediate overflow for otherwise representable axes.
    log_base = math.log(area) - math.log(coefficient)
    log_aspect = math.log(aspect)
    try:
        a = math.exp((log_base + log_aspect) / 2.0)
        b = math.exp((log_base - log_aspect) / 2.0)
    except OverflowError as exc:
        raise ValueError("area and aspect produce unrepresentable axes") from exc
    if not (math.isfinite(a) and math.isfinite(b) and a > 0 and b > 0):
        raise ValueError("area and aspect produce unrepresentable axes")
    return a, b


def polar_radius(phi, a, b, p):
    """Fixed-ray radius of |x/a|**p + |y/b|**p = 1.

    Accept a scalar or array of finite azimuths; return a float or ndarray.
    """
    a, b, p = _positive(a, "a"), _positive(b, "b"), _positive(p, "p")
    angles = np.asarray(phi, dtype=float)
    if not np.all(np.isfinite(angles)):
        raise ValueError("phi must be finite")
    with np.errstate(divide="ignore", invalid="ignore"):
        x = p * (np.log(np.abs(np.cos(angles))) - math.log(a))
        y = p * (np.log(np.abs(np.sin(angles))) - math.log(b))
        radius = np.exp(-np.logaddexp(x, y) / p)
    return float(radius) if radius.ndim == 0 else radius


def smootherstep(t):
    """Quintic 0-to-1 transition with zero first and second endpoint derivatives."""
    t = np.asarray(t, dtype=float)
    if not np.all(np.isfinite(t)) or np.any((t < 0) | (t > 1)):
        raise ValueError("t must be finite and in [0, 1]")
    result = t**3 * (t * (6 * t - 15) + 10)
    return float(result) if result.ndim == 0 else result
