"""CPU research construction on HornLab's parametric R-OSSE evaluator.

A varies the native meridian parameters with physical azimuth. B is an optional
finish on the resulting meridian, in cumulative arc coordinates. Neither path
is used for neutral archival replay.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..design.generators.lame_shell import offset_quarter_surface

SCHEMA = "sculpted-rosse-meridians-v1"


@dataclass(frozen=True)
class Planes:
    """Control values at H, 45 degrees and V, in that order."""

    h: float
    d: float
    v: float

    def at(self, phi):
        c = np.cos(phi) ** 2
        s = np.sin(phi) ** 2
        return self.h * c + self.v * s + (self.d - (self.h + self.v) / 2) * 4 * c * s


@dataclass(frozen=True)
class Body:
    width_mm: float
    height_mm: float
    exponent: float
    angle_deg: Planes
    apex_shift: Planes
    apex_radius: Planes
    bend: Planes
    tmax: float
    k: float
    q: float


@dataclass(frozen=True)
class Finish:
    axial_mm: Planes = Planes(0, 0, 0)
    radial_mm: Planes = Planes(0, 0, 0)
    start_arc: Planes = Planes(0.76, 0.76, 0.76)
    roundover_mm: Planes = Planes(0, 0, 0)


def smootherstep(t):
    """Bound the gate domain while leaving the physical coordinates untouched."""
    u = np.clip(t, 0.0, 1.0)
    return u**3 * (10 + u * (6 * u - 15))


def finish_meridian(z, rho, phi, finish: Finish):
    """Apply rim offsets and an endpoint-neutral meridian-normal curvature correction."""
    axial = float(finish.axial_mm.at(phi))
    radial = float(finish.radial_mm.at(phi))
    start = float(finish.start_arc.at(phi))
    rounding = float(finish.roundover_mm.at(phi))
    if not np.isfinite([axial, radial, start, rounding]).all() or not 0.5 <= start <= 0.93:
        raise ValueError("terminal start must be in [0.5, 0.93] and amplitudes finite")
    if axial == 0 and radial == 0 and rounding == 0:
        return z, rho
    length = np.r_[0.0, np.cumsum(np.hypot(np.diff(z), np.diff(rho)))]
    gate = smootherstep((length / length[-1] - start) / (1 - start))
    if rounding == 0:
        return z + axial * gate, rho + radial * gate
    dz, dr = np.gradient(z, length), np.gradient(rho, length)
    scale = np.hypot(dz, dr)
    if np.any(scale <= 0):
        raise ValueError("terminal curvature correction needs nondegenerate tangents")
    normal_offset = 4 * rounding * gate * (1 - gate) / scale
    return z + axial * gate - normal_offset * dr, rho + radial * gate + normal_offset * dz


def surface(body: Body, finish: Finish, *, radius_mm: float, source_angle_deg: float,
            wall_mm: float, collar_mm: tuple[float, float], n_phi: int, n_s: int):
    """Sample a quarter surface in the native R-OSSE parameter with an exact round entrance.

    A short common physical-z collar regularizes the actual throat slope.
    The published parametric curve is retained after that join unless B is active.
    """
    from hornlab_mesher.profile_formulas import calculate_rosse, profile_points
    from scipy.optimize import brentq

    if n_phi < 9 or n_s < 24 or not 0 < collar_mm[0] < collar_mm[1]:
        raise ValueError("require at least 9 azimuths, 24 meridian points and an increasing collar")
    if not (body.width_mm > body.height_mm > 2 * radius_mm and 2 <= body.exponent <= 10):
        raise ValueError("invalid landscape aperture or section exponent")
    if not (0.5 <= body.k <= 10 and 1 <= body.q <= 10 and 0.8 <= body.tmax <= 1):
        raise ValueError("R-OSSE k, q or tmax outside the studied family domain")
    if not (radius_mm > 0 and 0 < source_angle_deg < 45):
        raise ValueError("invalid driver interface")
    phi = np.linspace(0, np.pi / 2, n_phi)
    cos, sin = np.cos(phi), np.sin(phi)
    dims = ((2 * cos / body.width_mm) ** body.exponent
            + (2 * sin / body.height_mm) ** body.exponent) ** (-1 / body.exponent)
    angles, shifts, apex, bends = [control.at(phi) for control in (
        body.angle_deg, body.apex_shift, body.apex_radius, body.bend)]
    for values, lo, hi, name in (
        (angles, 5, 75, "opening angle"), (shifts, 0.5, 0.99, "apex shift"),
        (apex, 0.05, 2, "apex radius"), (bends, -0.1, 1, "bend"),
    ):
        if not np.isfinite(values).all() or np.any((values < lo) | (hi < values)):
            raise ValueError(f"interpolated {name} leaves [{lo}, {hi}]")
    inner = np.empty((n_phi, n_s, 3))
    for i, p in enumerate(phi):
        cfg = {"type": "R-OSSE", "R": dims[i], "r0": radius_mm, "a": angles[i],
               "a0": source_angle_deg, "k": body.k, "q": body.q, "m": shifts[i],
               "r": apex[i], "b": bends[i], "tmax": body.tmax}
        # Rev7 R belongs to t=1. Fit the native R for a requested physical
        # radius at the earlier truncation, keeping aperture and sweep decoupled.
        if body.tmax < 1:
            target = dims[i]

            def radius_error(native_radius):
                return calculate_rosse(body.tmax, 0, {**cfg, "R": native_radius})[1] - target

            cfg["R"] = brentq(radius_error, (target + radius_mm) / 2, 2 * target, xtol=1e-10)
        z, rho = profile_points(cfg, n_s).T
        # Apply the collar only on the entrance branch, even if a future curve returns far.
        peak = int(np.argmax(z))
        if peak == 0 or peak == n_s - 1 or np.any(np.diff(z[:peak + 1]) <= 0):
            raise ValueError(f"expected one forward branch and a returning lip at {np.degrees(p):g} degrees")
        if z[peak] <= collar_mm[1] or np.min(z[peak:]) <= collar_mm[1]:
            raise ValueError("returned lip overlaps the entrance collar")
        blend = smootherstep((z - collar_mm[0]) / (collar_mm[1] - collar_mm[0]))
        cone = radius_mm + np.tan(np.radians(source_angle_deg)) * z
        rho = np.where(z <= collar_mm[1], cone + blend * (rho - cone), rho)
        z, rho = finish_meridian(z, rho, p, finish)
        if np.any(rho <= 0) or not np.isfinite([z, rho]).all():
            raise ValueError(f"nonpositive or nonfinite radius at {np.degrees(p):g} degrees")
        inner[i] = np.column_stack((rho * cos[i], rho * sin[i], z))
    inner[0, :, 1] = 0.0
    inner[-1, :, 0] = 0.0
    outer, _ = offset_quarter_surface(inner, wall_mm)
    return inner, outer
