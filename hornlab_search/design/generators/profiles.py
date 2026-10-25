"""Classical horn meridian generators (TYPOLOGY_PLAN.md s4, V1-V2).

Units throughout: mm for lengths, degrees for angles, Hz for frequencies.
z is measured from the throat; z[0] == 0 always. All arrays are float64.

Le Cléac'h is LIVE: ``lecleach`` routes to the verified Fourcade 2015 exact construction
(R9-J gate passed 2026-10-25; see docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md).
``GeneratorUnavailable`` remains for any future unverified generator.

C_AIR is imported from hornlab_search.constants (343.0 m/s); never hardcoded.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicHermiteSpline, PchipInterpolator
from scipy.optimize import brentq

from hornlab_search.constants import C_AIR

_TWO_PI = 2.0 * np.pi


# ---------------------------------------------------------------------------
# Meridian dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, eq=False)
class Meridian:
    """Frozen profile record.  Arrays are read-only by convention (not enforced).

    Attributes
    ----------
    name : str
        Human-readable typology label.
    z_mm : ndarray, shape (n,)
        Axial positions in mm, strictly increasing, z[0] == 0.
    r_mm : ndarray, shape (n,)
        Radii in mm, all > 0.
    theta_deg : ndarray, shape (n,)
        Wall angle in degrees: degrees(atan(dr/dz)), analytic where available.
        Absolute values strictly < 90 for all points.
    info : dict
        Generator-specific scalars: m_per_m, fc_hz, T, a_mm, truncated_at_deg, …
    """
    name: str
    z_mm: np.ndarray
    r_mm: np.ndarray
    theta_deg: np.ndarray
    info: dict

    @property
    def length_mm(self) -> float:
        """Axial length from throat to mouth (mm)."""
        return float(self.z_mm[-1])

    @property
    def mouth_radius_mm(self) -> float:
        """Mouth radius (mm)."""
        return float(self.r_mm[-1])


# ---------------------------------------------------------------------------
# Sentinel for unavailable generators
# ---------------------------------------------------------------------------

class GeneratorUnavailable(RuntimeError):
    """Raised when a generator cannot be implemented from a verified source."""


# ---------------------------------------------------------------------------
# Profile generators
# ---------------------------------------------------------------------------

def conical(r0_mm, rm_mm, L_mm, n: int = 400) -> Meridian:
    """Conical horn: r = r0 + z·tan(alpha), alpha = atan((rm-r0)/L).

    Wall angle is constant = alpha everywhere.
    """
    r0_mm, rm_mm, L_mm = float(r0_mm), float(rm_mm), float(L_mm)
    alpha = np.arctan((rm_mm - r0_mm) / L_mm)
    z = np.linspace(0.0, L_mm, n)
    r = r0_mm + z * np.tan(alpha)
    theta = np.degrees(alpha) * np.ones(n)
    return Meridian(
        name="conical",
        z_mm=z,
        r_mm=r,
        theta_deg=theta,
        info={"alpha_deg": float(np.degrees(alpha))},
    )


def exponential(r0_mm, rm_mm, L_mm, n: int = 400) -> Meridian:
    """Exponential horn: r = r0·exp(m·z), m = ln(rm/r0)/L.

    info keys:
        m_per_m  flare constant in 1/m
        fc_hz    plane-wave cutoff = m_per_m · C_AIR / (2π)
    """
    r0_mm, rm_mm, L_mm = float(r0_mm), float(rm_mm), float(L_mm)
    m_mm = np.log(rm_mm / r0_mm) / L_mm        # 1/mm
    m_per_m = m_mm * 1_000.0                   # 1/m
    fc_hz = m_per_m * C_AIR / _TWO_PI
    z = np.linspace(0.0, L_mm, n)
    r = r0_mm * np.exp(m_mm * z)
    # dr/dz = m_mm · r   (analytic)
    theta = np.degrees(np.arctan(m_mm * r))
    return Meridian(
        name="exponential",
        z_mm=z,
        r_mm=r,
        theta_deg=theta,
        info={"m_per_m": float(m_per_m), "fc_hz": float(fc_hz)},
    )


def hypex(r0_mm, rm_mm, L_mm, T, n: int = 400) -> Meridian:
    """Salmon hypex: r = r0·(cosh(mz) + T·sinh(mz)).

    m is solved numerically (brentq) so r(L) = rm.
    T=0 → catenoidal, T=1 → exponential.  T must be in [0, 1].

    info keys:
        m_per_m  flare constant 1/m
        fc_hz    m_per_m · C_AIR / (2π)   (same convention as exponential)
        T        the T-factor used
    """
    r0_mm, rm_mm, L_mm, T = float(r0_mm), float(rm_mm), float(L_mm), float(T)
    if not (0.0 <= T <= 1.0):
        raise ValueError(f"hypex T must be in [0, 1], got {T}")

    def _resid(m_mm):
        return r0_mm * (np.cosh(m_mm * L_mm) + T * np.sinh(m_mm * L_mm)) - rm_mm

    m_lo = 1e-10
    m_hi = 100.0 / L_mm
    while _resid(m_hi) < 0:
        m_hi *= 10.0
    m_mm = brentq(_resid, m_lo, m_hi, xtol=1e-14, rtol=1e-12)

    m_per_m = m_mm * 1_000.0
    fc_hz = m_per_m * C_AIR / _TWO_PI

    z = np.linspace(0.0, L_mm, n)
    r = r0_mm * (np.cosh(m_mm * z) + T * np.sinh(m_mm * z))
    # dr/dz = r0 · m · (sinh(mz) + T·cosh(mz))   (analytic)
    drdz = r0_mm * m_mm * (np.sinh(m_mm * z) + T * np.cosh(m_mm * z))
    theta = np.degrees(np.arctan(drdz))
    return Meridian(
        name="hypex",
        z_mm=z,
        r_mm=r,
        theta_deg=theta,
        info={"m_per_m": float(m_per_m), "fc_hz": float(fc_hz), "T": float(T)},
    )


def tractrix(r0_mm, fc_hz, max_wall_deg: float = 80.0, n: int = 400) -> Meridian:
    """Voigt tractrix. Mouth radius a = C_AIR/(2π·fc) (converted to mm).

    Parametric form (r is the free variable, x is measured from the mouth plane,
    z is measured from the throat toward the mouth):

        x(r) = a·ln[(a + √(a²−r²)) / r] − √(a²−r²)

    Throat at r=r0 (requires r0 < a, else ValueError).
    z(r) = x(r0) − x(r), strictly increasing as r → a.

    Wall angle (analytic):  sin(θ) = r/a
    Derivation: dx/dr = −√(a²−r²)/r = −u/r,  dz/dr = u/r,
                dr/dz = r/u = r/√(a²−r²) = tan(arcsin(r/a))  ✓
    Tangent-segment property: the tangent at (z, r) meets the axis at z−u,
    giving segment length √(u² + r²) = √(a²) = a (constant).

    Profile is truncated at max_wall_deg (must be < 90); info contains
    a_mm, fc_hz, truncated_at_deg.

    The r-uniform parameterisation produces z values that are strictly increasing
    (dz/dr > 0 everywhere on the profile) but not uniformly spaced.
    """
    r0_mm, fc_hz = float(r0_mm), float(fc_hz)
    max_wall_deg = float(max_wall_deg)
    if max_wall_deg >= 90.0:
        raise ValueError(f"max_wall_deg must be < 90, got {max_wall_deg}")

    a_m = C_AIR / (_TWO_PI * fc_hz)
    a_mm = a_m * 1_000.0

    if r0_mm >= a_mm:
        raise ValueError(
            f"r0_mm={r0_mm:.4g} must be < a_mm={a_mm:.4g} "
            f"(a = C_AIR / (2π·fc) with fc={fc_hz:.1f} Hz)"
        )

    # r_max: where the wall angle equals max_wall_deg
    r_max_mm = a_mm * np.sin(np.radians(max_wall_deg))

    def _x_tract(r_arr):
        u = np.sqrt(a_mm**2 - r_arr**2)
        return a_mm * np.log((a_mm + u) / r_arr) - u

    x_throat = float(_x_tract(r0_mm))

    # r-uniform grid from r0 to r_max
    r = np.linspace(r0_mm, r_max_mm, n)
    x = _x_tract(r)
    z = x_throat - x              # z=0 at throat, increases to mouth

    # Analytic wall angle: sin(θ) = r/a
    theta = np.degrees(np.arcsin(np.clip(r / a_mm, -1.0, 1.0)))

    return Meridian(
        name="tractrix",
        z_mm=z,
        r_mm=r,
        theta_deg=theta,
        info={
            "a_mm": float(a_mm),
            "fc_hz": float(fc_hz),
            "truncated_at_deg": float(theta[-1]),
        },
    )


# ---------------------------------------------------------------------------
# Le Cléac'h (JMLC): Fourcade 2015 exact construction (eqs 10-27, 42-43)
# ---------------------------------------------------------------------------

_LECLEACH_MAX_STEPS = 200_000
#: FREEFORM meridians must stay below 90 deg; rollback above this uses the GRID rows route.
_LECLEACH_FREEFORM_MAX_STOP_DEG = 88.0


def _lecleach_error(message: str):
    """``registry.GeneratorError`` without a module-level import cycle."""
    from .registry import GeneratorError
    return GeneratorError(message)


def lecleach_exact(r0_mm, fc_hz, T, phi0_deg, stop_deg, dl_mm: float = 1.0,
                   c=C_AIR):
    """Fourcade 2015 Le Cléac'h construction (eqs 10-27, 42-43) -> MM samples.

    Source of record: ``docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md``
    (fetched Fourcade PDF; its section 2.3 reference case is the R9-J gate).  The march
    is the senior-pass port ``evidence/jmlc_reference.py`` evaluated in METRES and
    returned here in MILLIMETRES::

        R0 = r0 / sin(phi0)                         (eq 11)
        S0 = 2 pi R0^2 (1 - cos phi0)               (eq 13)
        m  = 4 pi fc / c                            (eq 43)
        S(l) = S0 [cosh(m l / 2) + T sinh(m l / 2)]^2   (eq 42)

    per step ``l_i = i dl``: spherical core ``2 pi (R0+l_i)^2 (1-cos phi0)`` (eq 15)
    plus the earlier rings ``2 pi h_k (h_k sin phi_{k-1} + y_{k-1}) dalpha_{k-1}``,
    ``h_k = l_i - l_{k-1}`` (eq 20); ``S_ii = S(l_i) - acc`` (eq 22);
    ``r_i = dl sin phi_{i-1} + y_{i-1}`` (eq 23); ``dalpha = S_ii/(2 pi r_i dl)``
    (eq 24); ``phi_i = phi_{i-1} + dalpha`` (25); ``x_i = x_{i-1} + dl cos phi_i``
    (26); ``y_i = y_{i-1} + dl sin phi_i`` (27).  Stop at the first sample with
    ``phi_i >= stop_deg`` (p.11, inclusive).  ``O(n^2)``, vectorised ring sum.

    ANGLE CONVENTION: ``phi0_deg`` is the wall HALF-angle.  The repo's
    ``driver.exit_angle_deg`` is already a half-angle (WP2 precedent: do not halve it
    again).  The published reference case quotes an INCLUDED 8.0 deg exit, so its
    ``phi0_deg`` is 4.0 and reproducing it also needs its own ``c=344.0``.

    Rollback is LEGAL output: ``x`` decreases once the wall passes 90 deg and ``y``
    falls after 180 deg.  The FREEFORM wrapper refuses stop > 88 deg; the GRID rows
    route calls this directly.  Refusals raise ``GeneratorError``.

    Returns
    -------
    (x_mm, y_mm, phi_deg, meta)
        ``x`` = wall axial abscissa from the throat, ``y`` = wall radius (mm),
        ``phi`` = wall angle (deg, half-angle convention), all including the throat
        point.  ``meta`` carries ``L0_mm`` (arc length at stop), ``S_L0_m2`` /
        ``S_L0_mm2`` (wavefront area at L0), ``max_x_mm``, ``max_y_mm``,
        ``width_mm`` (2 max y), ``phi1_deg`` / ``phi1_included_deg`` (2 phi1, the
        included tangent-cone angle at the throat, the published "angle de la gorge"),
        and the construction inputs.
    """
    r0_mm = float(r0_mm)
    fc_hz = float(fc_hz)
    T = float(T)
    phi0_deg = float(phi0_deg)
    stop_deg = float(stop_deg)
    dl_mm = float(dl_mm)
    c = float(c)
    for name, value in (("r0_mm", r0_mm), ("fc_hz", fc_hz), ("T", T),
                        ("phi0_deg", phi0_deg), ("stop_deg", stop_deg),
                        ("dl_mm", dl_mm), ("c", c)):
        if not np.isfinite(value):
            raise _lecleach_error(f"lecleach_exact: {name} must be finite, got {value!r}")
    if r0_mm <= 0.0:
        raise _lecleach_error(f"lecleach_exact: r0_mm must be > 0, got {r0_mm}")
    if fc_hz <= 0.0:
        raise _lecleach_error(f"lecleach_exact: fc_hz must be > 0, got {fc_hz}")
    if T < 0.0:
        raise _lecleach_error(f"lecleach_exact: T must be >= 0, got {T}")
    if dl_mm <= 0.0:
        raise _lecleach_error(f"lecleach_exact: dl_mm must be > 0, got {dl_mm}")
    if c <= 0.0:
        raise _lecleach_error(f"lecleach_exact: c must be > 0, got {c}")
    if not (0.0 < phi0_deg < stop_deg <= 360.0):
        raise _lecleach_error(
            "lecleach_exact: need 0 < phi0_deg < stop_deg <= 360, got "
            f"phi0={phi0_deg}, stop={stop_deg}")

    r0 = r0_mm / 1000.0                       # metres (the port's native unit)
    dl = dl_mm / 1000.0
    phi0 = np.radians(phi0_deg)
    R0 = r0 / np.sin(phi0)
    S0 = _TWO_PI * R0**2 * (1.0 - np.cos(phi0))
    m = 4.0 * np.pi * fc_hz / c

    def _S(length):
        return S0 * (np.cosh(m * length / 2.0) + T * np.sinh(m * length / 2.0)) ** 2

    xs = [0.0]
    ys = [r0]
    phis = [float(phi0)]
    dal: list[float] = []
    steps = 0
    while float(np.degrees(phis[-1])) < stop_deg:
        steps += 1
        li = steps * dl
        acc = _TWO_PI * (R0 + li) ** 2 * (1.0 - np.cos(phi0))
        if steps > 1:
            k = np.arange(1, steps)
            h = li - (k - 1) * dl
            ph = np.asarray(phis, dtype=float)[k - 1]
            yk = np.asarray(ys, dtype=float)[k - 1]
            da = np.asarray(dal, dtype=float)[k - 1]
            acc += float(np.sum(_TWO_PI * h * (h * np.sin(ph) + yk) * da))
        s_ii = float(_S(li)) - float(acc)
        if not np.isfinite(s_ii) or s_ii <= 0.0:
            raise _lecleach_error(
                "lecleach_exact: S_ii <= 0 (non-positive bracket) at step "
                f"{steps} (l={li * 1000.0:.3f} mm, S_ii={s_ii:.6g}); refuse instead of clamping")
        r_i = dl * np.sin(phis[-1]) + ys[-1]
        if not np.isfinite(r_i) or r_i <= 0.0:
            raise _lecleach_error(
                f"lecleach_exact: non-positive wall radius r_i={r_i!r} at step {steps}")
        dalpha = s_ii / (_TWO_PI * r_i * dl)
        phi = phis[-1] + dalpha
        x = xs[-1] + dl * np.cos(phi)
        y = ys[-1] + dl * np.sin(phi)
        if not (np.isfinite(phi) and np.isfinite(x) and np.isfinite(y)):
            raise _lecleach_error(f"lecleach_exact: non-finite point at step {steps}")
        if y <= 0.0:
            raise _lecleach_error(
                f"lecleach_exact: wall radius crossed zero (y={y:.6g}) at step {steps}")
        dal.append(float(dalpha))
        phis.append(float(phi))
        xs.append(float(x))
        ys.append(float(y))
        if steps > _LECLEACH_MAX_STEPS:
            raise _lecleach_error(
                "lecleach_exact: march did not reach stop_deg; refusing an unbounded sweep")

    x_mm = np.asarray(xs, dtype=float) * 1000.0
    y_mm = np.asarray(ys, dtype=float) * 1000.0
    phi_deg = np.degrees(np.asarray(phis, dtype=float))
    L0_mm = float(steps) * dl_mm
    S_L0_m2 = float(_S(steps * dl))
    phi1_deg = float(phi_deg[1]) if phi_deg.size > 1 else float(phi0_deg)
    meta = {
        "units": "samples/L0/max_x/max_y/width in mm; S_L0 in m^2 and mm^2",
        "L0_mm": L0_mm,
        "S_L0_m2": S_L0_m2,
        "S_L0_mm2": S_L0_m2 * 1.0e6,
        "max_x_mm": float(np.max(x_mm)),
        "max_y_mm": float(np.max(y_mm)),
        "width_mm": 2.0 * float(np.max(y_mm)),
        "phi1_deg": phi1_deg,
        "phi1_included_deg": 2.0 * phi1_deg,
        "phi0_deg": phi0_deg,
        "phi0_included_deg": 2.0 * phi0_deg,
        "stop_deg": float(phi_deg[-1]),
        "stop_target_deg": stop_deg,
        "n_steps": int(steps),
        "dl_mm": dl_mm,
        "r0_mm": r0_mm,
        "fc_hz": fc_hz,
        "T": T,
        "c": c,
        "source": "Fourcade 2015 eqs 10-27, 42-43 (JMLC_LECLEACH_RESEARCH_2026-10-25.md)",
    }
    return x_mm, y_mm, phi_deg, meta


def lecleach(r0_mm, fc_hz, T, max_wall_deg: float = 80.0, n: int = 400,
             *, phi0_deg: float | None = None, dl_mm: float = 1.0,
             c=C_AIR) -> Meridian:
    """Le Cléac'h FREEFORM meridian from the verified Fourcade construction.

    Routes to :func:`lecleach_exact`; the knobs are ``fc_hz``, ``T`` and
    ``max_wall_deg`` (the stop angle), exactly like the other meridian generators.
    ``phi0_deg`` is the throat wall HALF-angle and is required (the registry passes the
    brief's ``driver.exit_angle_deg`` unchanged; JMLC driver tables quote INCLUDED
    angles, so halve only where an operator pastes one).  ``n`` is kept for source
    compatibility and is unused: the march resolution is ``dl_mm`` (Fourcade's 1 mm).

    Only stop <= 88 deg is representable as a FREEFORM meridian (z must stay
    monotone and |theta| < 90).  Rollback (stop > 88 deg) is legal ONLY through the
    GRID rows route (``generator: {name: grid, rows: {type: lecleach}}``); this
    wrapper refuses it instead of silently meshing a BARE shell.
    """
    if phi0_deg is None:
        raise _lecleach_error(
            "lecleach: phi0_deg (wall HALF-angle at the throat) is required; the registry "
            "passes the brief's driver exit angle. JMLC driver tables quote an INCLUDED "
            "angle: halve it at the operator boundary (8 deg included -> phi0_deg=4).")
    phi0 = float(phi0_deg)
    stop = float(max_wall_deg)
    if not (0.0 < phi0 < stop):
        raise _lecleach_error(
            f"lecleach: need 0 < phi0_deg < max_wall_deg, got phi0={phi0}, stop={stop}")
    if stop > _LECLEACH_FREEFORM_MAX_STOP_DEG:
        raise _lecleach_error(
            f"lecleach: stop_deg={stop:g} > {_LECLEACH_FREEFORM_MAX_STOP_DEG:g} cannot be a "
            "FREEFORM meridian (rollback needs the GRID rows route: "
            "generator: {name: grid, rows: {type: lecleach}})")
    x_mm, y_mm, phi_deg, meta = lecleach_exact(
        r0_mm, fc_hz, T, phi0, stop, dl_mm=dl_mm, c=c)
    if not np.all(np.diff(x_mm) > 0.0):
        raise _lecleach_error(
            "lecleach: the march is not x-monotone at this stop; use the GRID rows route")
    if np.any(np.abs(phi_deg) >= 90.0):
        raise _lecleach_error(
            "lecleach: the march reached |theta| >= 90 deg; use the GRID rows route")
    return Meridian(
        name="lecleach",
        z_mm=x_mm,
        r_mm=y_mm,
        theta_deg=phi_deg,
        info=meta,
    )


def spherical_wave(r0_mm, fc_hz, max_wall_deg: float = 80.0, *,
                   phi0_deg: float | None = None, dl_mm: float = 1.0,
                   c=C_AIR) -> Meridian:
    """Spherical-wave horn = Le Cléac'h with T=1 (now a working generator)."""
    return lecleach(r0_mm, fc_hz, T=1.0, max_wall_deg=max_wall_deg,
                    phi0_deg=phi0_deg, dl_mm=dl_mm, c=c)


# ---------------------------------------------------------------------------
# WP9 G2: meridian splice
# ---------------------------------------------------------------------------

#: A wall-angle gap at the radius-matched joint at or below this takes the direct splice;
#: a larger gap uses the C1 Hermite bridge (Report 4 WP9 step 1: "if no match within 2 deg").
_SPLICE_MATCH_TOL_DEG = 2.0
#: Hermite bridge length as a fraction of the SECOND parent's length (Report 4 WP9 step 1).
_SPLICE_BRIDGE_FRAC = 0.10
_SPLICE_BRIDGE_SAMPLES = 41


def splice(first: Meridian, second: Meridian, zs_frac: float) -> Meridian:
    """C1 splice: ``first`` up to ``z_s``, then ``second`` (Report 4 WP9 step 1, G2).

    Both parents are built from the same throat radius (the caller does that; this
    function refuses a mismatch).  ``z_s = zs_frac * first.length_mm``.

    The second parent is translated in z so that the point where its radius equals
    ``first``'s radius at ``z_s`` sits at ``z_s``; radius continuity at the joint is
    therefore exact.  The wall-angle gap there is measured; when it is <= 2 deg the
    two parents are spliced directly.  Otherwise a cubic Hermite bridge over 10 % of
    the second parent's length joins the parents with matching value and tangent at
    both ends (Report 4 WP9 step 1's fallback).  [inferred] Plan ambiguity: the plan
    does not say which of the two angle-matching points (radius match vs. wall-angle
    search) defines the joint; the radius match is used because a radius step is not
    representable in a single meridian, and the angle gap selects direct vs. bridge.

    Parameters
    ----------
    first, second : Meridian
        Parents, both starting at the same r0 > 0 with strictly increasing r.
    zs_frac : float
        Splice position as a fraction of ``first.length_mm``; must be in [0.2, 0.8]
        (the plan's knob range; not widened here).
    """
    zs_frac = float(zs_frac)
    if not (0.2 <= zs_frac <= 0.8):
        raise ValueError(f"splice: zs_frac must be in [0.2, 0.8], got {zs_frac}")
    r0a, r0b = float(first.r_mm[0]), float(second.r_mm[0])
    if abs(r0a - r0b) > 1e-6:
        raise ValueError(
            f"splice: both parents must be built from the same r0; got {r0a:.6g} vs {r0b:.6g}")
    if not (np.all(np.diff(first.z_mm) > 0) and np.all(np.diff(second.z_mm) > 0)):
        raise ValueError("splice: parent z must be strictly increasing")
    if not (np.all(np.diff(first.r_mm) > 0) and np.all(np.diff(second.r_mm) > 0)):
        raise ValueError("splice: parent r must be strictly increasing")

    L1 = first.length_mm
    z_s = zs_frac * L1
    r_s = float(np.interp(z_s, first.z_mm, first.r_mm))
    th_s = float(np.interp(z_s, first.z_mm, first.theta_deg))

    r2_min, r2_max = float(second.r_mm[0]), float(second.r_mm[-1])
    if not (r2_min - 1e-9 <= r_s <= r2_max + 1e-9):
        raise ValueError(
            f"splice: the second parent's radius range [{r2_min:.3g}, {r2_max:.3g}] mm "
            f"does not contain the joint radius {r_s:.3g} mm")
    z2_s = float(np.interp(r_s, second.r_mm, second.z_mm))
    dz = z_s - z2_s
    z2 = second.z_mm + dz
    th2_s = float(np.interp(z2_s, second.z_mm, second.theta_deg))
    delta_deg = th2_s - th_s

    keep1 = first.z_mm < z_s - 1e-12
    z_out = [float(v) for v in first.z_mm[keep1]] + [z_s]
    r_out = [float(v) for v in first.r_mm[keep1]] + [r_s]
    th_out = [float(v) for v in first.theta_deg[keep1]] + [th_s]

    z_bridge = None
    if abs(delta_deg) <= _SPLICE_MATCH_TOL_DEG:
        joint = "matched"
        keep2 = z2 > z_s + 1e-12
        z_out += [float(v) for v in z2[keep2]]
        r_out += [float(v) for v in second.r_mm[keep2]]
        th_out += [float(v) for v in second.theta_deg[keep2]]
    else:
        joint = "hermite_bridge"
        L2 = second.length_mm
        z_bridge = min(z_s + _SPLICE_BRIDGE_FRAC * L2, float(z2[-1]))
        if z_bridge <= z_s + 1e-9:
            raise ValueError("splice: no room for the Hermite bridge on the second parent")
        r_b = float(np.interp(z_bridge, z2, second.r_mm))
        th_b = float(np.interp(z_bridge, z2, second.theta_deg))
        cs = CubicHermiteSpline(
            np.array([z_s, z_bridge]),
            np.array([r_s, r_b]),
            np.array([np.tan(np.radians(th_s)), np.tan(np.radians(th_b))]),
        )
        zb = np.linspace(z_s, z_bridge, _SPLICE_BRIDGE_SAMPLES)
        rb = cs(zb)
        thb = np.degrees(np.arctan(cs(zb, 1)))
        z_out += [float(v) for v in zb[1:]]
        r_out += [float(v) for v in rb[1:]]
        th_out += [float(v) for v in thb[1:]]
        keep2 = z2 > z_bridge + 1e-12
        z_out += [float(v) for v in z2[keep2]]
        r_out += [float(v) for v in second.r_mm[keep2]]
        th_out += [float(v) for v in second.theta_deg[keep2]]

    z = np.asarray(z_out, dtype=float)
    r = np.asarray(r_out, dtype=float)
    th = np.asarray(th_out, dtype=float)
    if not (np.all(np.isfinite(z)) and np.all(np.isfinite(r)) and np.all(np.isfinite(th))):
        raise ValueError("splice: produced non-finite points")
    if not np.all(np.diff(z) > 0):
        raise ValueError("splice: produced non-increasing z at the joint")
    if not np.all(r > 0) or np.any(np.abs(th) >= 90.0):
        raise ValueError("splice: produced an invalid meridian (r<=0 or |theta|>=90)")

    return Meridian(
        name=f"splice({first.name},{second.name},zs={zs_frac:.3g})",
        z_mm=z,
        r_mm=r,
        theta_deg=th,
        info={
            "zs_frac": zs_frac,
            "z_s_mm": float(z_s),
            "dz_mm": float(dz),
            "joint": joint,
            "delta_theta_deg": float(delta_deg),
            "z_bridge_mm": None if z_bridge is None else float(z_bridge),
            "first_type": str(first.name),
            "second_type": str(second.name),
            "L1_mm": float(L1),
            "L2_mm": float(second.length_mm),
        },
    )


# ---------------------------------------------------------------------------
# WP9 G3: throat blend (throat_blend_mm)
# ---------------------------------------------------------------------------

def _os_radius(r0_mm: float, a0_rad: float, alpha_rad: float, z):
    """OSSE/OS radius with s=0: sqrt(r0^2 + 2 r0 z tan(a0) + z^2 tan(alpha)^2).

    ``alpha`` is the far-field (coverage) angle; ``a0`` the throat angle.
    """
    z = np.asarray(z, dtype=float)
    return np.sqrt(r0_mm**2 + 2.0 * r0_mm * z * np.tan(a0_rad) + (z * np.tan(alpha_rad)) ** 2)


def _os_far_angle(r0_mm: float, a0_deg: float, L_b_mm: float, theta_cls_deg: float) -> float:
    """Far-field angle whose OS meridian has wall angle ``theta_cls_deg`` at ``L_b_mm``.

    Solves the implicit Report 4 WP9 step 2 relation (r_OS itself depends on alpha)::

        tan^2(alpha) = (tan(theta_cls(L_b)) * r_OS(L_b) - r0 * tan(a0)) / L_b
    """
    a0 = float(np.radians(a0_deg))
    target = float(np.tan(np.radians(theta_cls_deg)))

    def resid(alpha):
        r_l = float(_os_radius(r0_mm, a0, alpha, L_b_mm))
        return float(np.tan(alpha) ** 2 - (target * r_l - r0_mm * np.tan(a0)) / L_b_mm)

    lo, hi = 1e-12, float(np.radians(89.999))
    f_lo, f_hi = resid(lo), resid(hi)
    if f_lo > 0.0 or f_hi < 0.0:
        raise ValueError(
            f"throat blend: cannot match the classical wall angle {theta_cls_deg:.3f} deg "
            f"at L_b={L_b_mm:.3f} mm with the OS throat (a0={a0_deg:.3f} deg)")
    return brentq(resid, lo, hi, xtol=1e-15, rtol=1e-14)


def throat_blend(classical: Meridian, r0_mm: float, a0_deg: float, L_b_mm: float) -> Meridian:
    """Blend an OS throat into a classical meridian over ``[0, L_b_mm]`` (G3).

    ``r(z) = (1-w) r_OS(z) + w r_cls(z)`` with ``w = 3t^2 - 2t^3`` and ``t = z / L_b``.
    ``r_OS`` is the OS meridian (OSSE with s=0) starting at the driver exit angle
    ``a0_deg`` whose far-field angle is solved so its wall angle at ``L_b`` equals the
    classical meridian's.  ``w`` is C1 with ``w'(0) = w'(L_b) = 0``, so:

    * ``r(0) = r_OS(0) = r0`` and the throat angle is the driver exit angle;
    * at ``L_b`` the blend lands exactly on the classical radius and angle, and the
      classical profile is copied unchanged beyond ``L_b``.

    ``L_b_mm`` must be in ``(0, classical.length_mm]``.  The caller skips this function
    entirely for a zero/absent knob (the default-0 path stays bit-for-bit).
    """
    r0 = float(r0_mm)
    L_b = float(L_b_mm)
    if not (L_b > 0.0):
        raise ValueError(f"throat blend: L_b must be > 0, got {L_b}")
    if L_b > classical.length_mm + 1e-9:
        raise ValueError(
            f"throat blend: L_b={L_b:.3f} mm exceeds the {classical.name} meridian "
            f"length {classical.length_mm:.3f} mm")

    z = classical.z_mm
    r_cls = classical.r_mm
    th_cls = classical.theta_deg
    r_l = float(np.interp(L_b, z, r_cls))
    th_l = float(np.interp(L_b, z, th_cls))
    alpha = _os_far_angle(r0, a0_deg, L_b, th_l)

    a0 = float(np.radians(a0_deg))
    t = np.clip(z / L_b, 0.0, 1.0)
    w = 3.0 * t**2 - 2.0 * t**3
    dw_dz = np.where(z <= L_b, (6.0 * t - 6.0 * t**2) / L_b, 0.0)
    inside = z <= L_b

    r_os = _os_radius(r0, a0, alpha, z)
    d_os = (r0 * np.tan(a0) + z * np.tan(alpha) ** 2) / r_os
    d_cls = np.tan(np.radians(th_cls))
    r = np.where(inside, (1.0 - w) * r_os + w * r_cls, r_cls)
    dr_dz = np.where(inside, (1.0 - w) * d_os + w * d_cls + dw_dz * (r_cls - r_os), d_cls)
    # Beyond L_b copy the classical angle array verbatim (not atan(tan(theta))): the
    # classical meridian is unchanged, byte for byte, past the blend.
    th = np.where(inside, np.degrees(np.arctan(dr_dz)), th_cls)

    return Meridian(
        name=f"throat_blend({classical.name},{L_b:.3g}mm)",
        z_mm=np.asarray(z, dtype=float),
        r_mm=np.asarray(r, dtype=float),
        theta_deg=np.asarray(th, dtype=float),
        info={
            "throat_blend_mm": float(L_b),
            "r0_mm": r0,
            "a0_deg": float(a0_deg),
            "os_far_angle_deg": float(np.degrees(alpha)),
            "r_at_L_b_mm": r_l,
            "theta_at_L_b_deg": th_l,
            "L_mm": float(classical.length_mm),
        },
    )


# ---------------------------------------------------------------------------
# WP9 G4: spherical_salmon (neutral name; Report 2 section 3 march)
# ---------------------------------------------------------------------------

_SALMON_MAX_STEPS = 200_000


def salmon_march_core(r0_mm, fc_hz, T, theta0_deg, stop_deg, dx_mm: float = 0.25, *,
                      require_increasing_x: bool = False):
    """March state ``(xs, ys, thetas, areas, meta)``; arrays include the throat point.

    Report 2 section 3 keeps the Salmon area law on spherical wavefront caps normal
    to the wall and the trapezoidal wall continuity (eqs. 1 and 3).  The apex form
    (eq. 2) is not used as the independent variable: for the shipped 1-inch, 5 deg
    throat at fc >= 600 Hz the apex advance is over-consumed by the cap-curvature term
    and no theta in [theta_i, max_wall] satisfies eq. 2 (fc 800 Hz: the largest cap
    area reachable at dx = 0.25 mm is 509.4 mm^2 against the required 510.7 mm^2).
    [inferred] The march therefore advances the wall by dx_mm at the mean wall angle
    (eq. 3's trapezoid) and solves theta from the area law (eq. 1) with brentq; this is
    the same Salmon law and keeps every checked property (area law, z increasing,
    theta non-decreasing, plane-wave limit).  Refusals raise ValueError instead of
    clamping.

    WP9b: this is the reusable core behind ``spherical_salmon`` and the GRID rows
    machinery.  ``stop_deg`` may exceed 90 deg (rollback): ``xs`` is the wall axial
    abscissa measured from the throat (non-monotone past 90 deg), ``ys`` the radius,
    ``areas`` the wavefront cap area at every sample.  ``require_increasing_x`` keeps
    the G4 FREEFORM guard (``spherical_salmon`` passes True); the rows route passes
    False because a curled row legitimately moves back in x.  ``stop_deg == 180`` is
    refused: the cap-area law has an asymptote there.
    """
    r0 = float(r0_mm)
    fc = float(fc_hz)
    T = float(T)
    th0 = float(theta0_deg)
    maxw = float(stop_deg)
    dx = float(dx_mm)
    for name, val in (("r0_mm", r0), ("fc_hz", fc), ("T", T), ("theta0_deg", th0),
                      ("stop_deg", maxw), ("dx_mm", dx)):
        if not np.isfinite(val):
            raise ValueError(f"spherical_salmon: {name} must be finite, got {val!r}")
    if r0 <= 0.0:
        raise ValueError(f"spherical_salmon: r0_mm must be > 0, got {r0}")
    if fc <= 0.0:
        raise ValueError(f"spherical_salmon: fc_hz must be > 0, got {fc}")
    if T < 0.0:
        raise ValueError(f"spherical_salmon: T must be >= 0, got {T}")
    if dx <= 0.0:
        raise ValueError(f"spherical_salmon: dx_mm must be > 0, got {dx}")
    if not (0.0 < th0 < maxw < 360.0):
        raise ValueError(
            f"spherical_salmon: need 0 < theta0_deg < stop_deg < 360, got "
            f"theta0={th0}, stop={maxw}")
    if abs(maxw - 180.0) < 1e-9:
        raise ValueError(
            "spherical_salmon: stop_deg=180 is the cap-area asymptote (the wavefront "
            "cap grows without bound); choose a stop below or above 180 deg")

    th0r = float(np.radians(th0))
    maxwr = float(np.radians(maxw))
    x0 = C_AIR * 1000.0 / (_TWO_PI * fc)              # mm
    R0 = r0 / np.sin(th0r)
    A0 = _TWO_PI * R0**2 * (1.0 - np.cos(th0r))       # mm^2

    def _area(apex_mm):
        return A0 * (np.cosh(apex_mm / x0) + T * np.sinh(apex_mm / x0)) ** 2

    def _cap(r, th):
        return _TWO_PI * (r / np.sin(th)) ** 2 * (1.0 - np.cos(th))

    z = [0.0]
    r = [r0]
    th = [th0r]
    s = [0.0]
    areas = [float(_cap(r0, th0r))]
    steps = 0
    while th[-1] < maxwr - 1e-12:
        s_next = s[-1] + dx
        a_next = _area(s_next)

        def r_at(theta, ds=dx):
            return r[-1] + ds * np.sin(0.5 * (theta + th[-1]))

        def f(theta):
            return _cap(r_at(theta), theta) - a_next

        f0 = f(th[-1])
        if f0 > 1e-12:
            raise ValueError(
                "spherical_salmon: the area law grows slower than the fixed-angle wall "
                f"(step {steps}); a non-decreasing theta march is impossible for these knobs")
        if f(maxwr) >= 0.0:
            # f0 == 0 (within tolerance): the area law is already satisfied at theta_i.
            theta = th[-1] if f0 >= 0.0 else brentq(f, th[-1], maxwr, xtol=1e-14, rtol=1e-13)
            rr = r_at(theta)
            zz = z[-1] + dx * np.cos(0.5 * (theta + th[-1]))
            ss = s_next
        else:
            theta = maxwr
            th_mid = 0.5 * (maxwr + th[-1])

            def g(arc):
                rr = r[-1] + (arc - s[-1]) * np.sin(th_mid)
                return _cap(rr, maxwr) - _area(arc)

            g0, g1 = g(s[-1]), g(s_next)
            if not (g0 > 0.0 > g1):
                raise ValueError(
                    "spherical_salmon: brentq bracket exhausted at the max_wall stop "
                    f"(g0={g0:.6g}, g1={g1:.6g}, step {steps})")
            ss = brentq(g, s[-1], s_next, xtol=1e-13)
            rr = r[-1] + (ss - s[-1]) * np.sin(th_mid)
            zz = z[-1] + (ss - s[-1]) * np.cos(th_mid)

        if not (np.isfinite(zz) and np.isfinite(rr) and np.isfinite(theta)):
            raise ValueError("spherical_salmon: march produced a non-finite point")
        if require_increasing_x and zz <= z[-1]:
            raise ValueError(
                "spherical_salmon: self-approach / non-increasing z "
                f"({zz:.6g} <= {z[-1]:.6g}); refuse instead of clamping")
        if not (0.0 < theta <= maxwr + 1e-12):
            raise ValueError(f"spherical_salmon: march left the wall-angle bracket ({theta!r})")

        z.append(float(zz))
        r.append(float(rr))
        th.append(float(theta))
        s.append(float(ss))
        areas.append(float(_cap(rr, theta)))
        steps += 1
        if steps > _SALMON_MAX_STEPS:
            raise ValueError("spherical_salmon: march did not stop; refusing an unbounded sweep")

    xs = np.asarray(z, dtype=float)
    ys = np.asarray(r, dtype=float)
    thetas = np.asarray(th, dtype=float)
    meta = {
        "fc_hz": float(fc),
        "T": float(T),
        "theta0_deg": float(th0),
        "stop_deg": float(np.degrees(thetas[-1])),
        "stop_target_deg": float(maxw),
        "dx_mm": float(dx),
        "x0_mm": float(x0),
        "A0_mm2": float(A0),
        "s_end_mm": float(s[-1]),
        "s_mm": [float(v) for v in s],
        "n_steps": int(len(xs) - 1),
        "x_min_mm": float(np.min(xs)),
        "x_max_mm": float(np.max(xs)),
        "y_max_mm": float(np.max(ys)),
        "requiring_increasing_x": bool(require_increasing_x),
    }
    return xs, ys, thetas, np.asarray(areas, dtype=float), meta


def _salmon_march(r0_mm, fc_hz, T, theta0_deg, max_wall_deg, dx_mm):
    """G4 FREEFORM march: the core with its historical ``max_wall < 90`` refusal.

    Returns the historical ``(z, r, theta, s, A0, x0)`` tuple.  The march core is
    :func:`salmon_march_core`; this wrapper is what keeps ``spherical_salmon``
    byte-identical to the pre-WP9b generator (same operations, same order).
    """
    maxw = float(max_wall_deg)
    if not (0.0 < float(theta0_deg) < maxw < 90.0):
        raise ValueError(
            f"spherical_salmon: need 0 < theta0_deg < max_wall_deg < 90, got "
            f"theta0={float(theta0_deg)}, max_wall={maxw}")
    xs, ys, thetas, _areas, meta = salmon_march_core(
        r0_mm, fc_hz, T, theta0_deg, maxw, dx_mm, require_increasing_x=True)
    return (xs, ys, thetas, np.asarray(meta["s_mm"], dtype=float),
            meta["A0_mm2"], meta["x0_mm"])


def spherical_salmon(r0_mm, fc_hz, T, theta0_deg, max_wall_deg, dx_mm: float = 0.25) -> Meridian:
    """Spherical-wavefront Salmon horn (Report 2 section 3; neutral G4 name).

    Area law ``A(s) = A0 (cosh(s/x0) + T sinh(s/x0))^2`` with ``x0 = c/(2 pi fc)``
    applied to spherical caps normal to the wall:
    ``A = 2 pi (r/sin theta)^2 (1 - cos theta)`` (-> ``pi r^2`` as theta -> 0).
    March step ``dx_mm = 0.25``; stop at ``max_wall_deg``.  The dense march is returned
    as a :class:`Meridian`; the registry resamples it with ``select_anchors``.

    Units: mm, degrees, Hz.  See ``_salmon_march`` for the [inferred] resolution of
    Report 2 eq. 2 and for the refusal rules (bracket exhausted, self-approach).
    ``lecleach`` / ``spherical_wave`` are the verified Fourcade construction (R9-J);
    this neutral name is a different discretization and does not claim it.
    """
    z, r, th, s, A0, x0 = _salmon_march(r0_mm, fc_hz, T, theta0_deg, max_wall_deg, dx_mm)
    return Meridian(
        name="spherical_salmon",
        z_mm=z,
        r_mm=r,
        theta_deg=np.degrees(th),
        info={
            "fc_hz": float(fc_hz),
            "T": float(T),
            "theta0_deg": float(theta0_deg),
            "max_wall_deg": float(max_wall_deg),
            "dx_mm": float(dx_mm),
            "x0_mm": float(x0),
            "A0_mm2": float(A0),
            "s_end_mm": float(s[-1]),
            "stop_deg": float(np.degrees(th[-1])),
            "n_steps": int(len(z) - 1),
        },
    )


# ---------------------------------------------------------------------------
# Hybrid / utility functions
# ---------------------------------------------------------------------------

def blend(a: Meridian, b: Meridian, w: float, n: int = 400) -> Meridian:
    """Blend two meridians on normalised t = z/L.

    r(t) = (1−w)·r_a(t) + w·r_b(t)
    L    = (1−w)·L_a + w·L_b

    Throat radii must match within 1e-6 mm (else ValueError).
    Each parent is represented as a CubicHermiteSpline in t-space, with
    slopes dr/dt = L_parent · tan(theta_parent) at each sample point.
    The blended angle is derived from the analytic blend derivative:
        dr/dz_blend = [(1−w)·dr_a/dt + w·dr_b/dt] / L_blend
    """
    w = float(w)
    r0a, r0b = float(a.r_mm[0]), float(b.r_mm[0])
    if abs(r0a - r0b) > 1e-6:
        raise ValueError(
            f"blend: throat radii must agree within 1e-6 mm; "
            f"got {r0a:.6g} vs {r0b:.6g}"
        )

    L_a, L_b = a.length_mm, b.length_mm
    L_blend = (1.0 - w) * L_a + w * L_b

    # Normalise each parent to t ∈ [0, 1]
    t_a = a.z_mm / L_a
    t_b = b.z_mm / L_b

    # Slopes in t-space: dr/dt = L · tan(θ)
    dra_dt = L_a * np.tan(np.radians(a.theta_deg))
    drb_dt = L_b * np.tan(np.radians(b.theta_deg))

    cs_a = CubicHermiteSpline(t_a, a.r_mm, dra_dt)
    cs_b = CubicHermiteSpline(t_b, b.r_mm, drb_dt)

    t = np.linspace(0.0, 1.0, n)
    r_blend = (1.0 - w) * cs_a(t) + w * cs_b(t)
    dr_blend_dt = (1.0 - w) * cs_a(t, 1) + w * cs_b(t, 1)
    dr_blend_dz = dr_blend_dt / L_blend
    theta_blend = np.degrees(np.arctan(dr_blend_dz))

    return Meridian(
        name=f"blend({a.name},{b.name},w={w:.3g})",
        z_mm=t * L_blend,
        r_mm=r_blend,
        theta_deg=theta_blend,
        info={"w": float(w), "L_a": float(L_a), "L_b": float(L_b), "L": float(L_blend)},
    )


def select_anchors(m: Meridian, n_anchors: int = 16) -> list[list[float]]:
    """Select ``n_anchors`` from ``m`` as [[z_mm, r_mm, angleDeg], ...].

    Both endpoints are always included.  Interior anchors are placed at equal
    arc-length stations in the normalised (z/L, θ/max(|θ|, 1)) plane, so
    that high-curvature regions receive more anchors.

    ``n_anchors`` must be in [2, 64].  Output is sorted by z (strictly increasing).
    """
    if not (2 <= n_anchors <= 64):
        raise ValueError(f"n_anchors must be in [2, 64], got {n_anchors}")

    z, r, theta = m.z_mm, m.r_mm, m.theta_deg
    L = m.length_mm
    theta_scale = max(float(np.max(np.abs(theta))), 1.0)

    # Normalised coordinates
    zn = z / L
    tn = theta / theta_scale

    # Cumulative arc length in (zn, tn) space
    dzn = np.diff(zn)
    dtn = np.diff(tn)
    ds = np.sqrt(dzn**2 + dtn**2)
    arc = np.concatenate([[0.0], np.cumsum(ds)])
    total_arc = float(arc[-1])

    if n_anchors == 2:
        return [
            [float(z[0]),  float(r[0]),  float(theta[0])],
            [float(z[-1]), float(r[-1]), float(theta[-1])],
        ]

    # n_anchors equally-spaced arc targets (including endpoints)
    target_arcs = np.linspace(0.0, total_arc, n_anchors)
    indices = [0]
    for ta in target_arcs[1:-1]:
        idx = int(np.searchsorted(arc, ta, side="left"))
        idx = max(1, min(idx, len(z) - 2))
        indices.append(idx)
    indices.append(len(z) - 1)

    # Deduplicate while preserving order
    seen: set[int] = set()
    unique: list[int] = []
    for i in sorted(indices):
        if i not in seen:
            seen.add(i)
            unique.append(i)

    return [[float(z[i]), float(r[i]), float(theta[i])] for i in unique]


def perturb_increments(
    anchors: list[list[float]],
    u,
    u_max: float,
) -> list[list[float]]:
    """Monotone-increment perturbation of anchor radii.

    base increments d_i = r_{i+1} − r_i  (must all be > 0).
    new r_{i+1} = new_r_i + d_i · exp(clip(u_i, −u_max, u_max))

    z values are unchanged.  Angles are re-derived using a monotone
    PchipInterpolator through the new (z, r) points.  The throat angle
    is kept from the base anchors (index 0).

    Parameters
    ----------
    anchors : list of [z, r, angleDeg]
    u : array-like of length len(anchors)−1
    u_max : positive float; clips each u_i
    """
    u = np.asarray(u, dtype=float)
    n = len(anchors)
    if len(u) != n - 1:
        raise ValueError(f"len(u)={len(u)} must equal len(anchors)−1={n - 1}")

    z_arr   = np.array([a[0] for a in anchors], dtype=float)
    r_arr   = np.array([a[1] for a in anchors], dtype=float)
    theta_base = float(anchors[0][2])

    d = np.diff(r_arr)
    if np.any(d <= 0.0):
        raise ValueError("base increments r_{i+1}−r_i must all be > 0")

    new_d = d * np.exp(np.clip(u, -u_max, u_max))
    new_r = np.empty(n)
    new_r[0] = r_arr[0]
    for i in range(n - 1):
        new_r[i + 1] = new_r[i] + new_d[i]

    # Re-derive angles via monotone PCHIP
    pchip = PchipInterpolator(z_arr, new_r)
    drdzm = pchip.derivative()(z_arr)
    new_theta = np.degrees(np.arctan(drdzm))
    new_theta[0] = theta_base   # keep throat angle from base

    return [
        [float(z_arr[i]), float(new_r[i]), float(new_theta[i])]
        for i in range(n)
    ]


def hermite_reference(anchors: list[list[float]], z_mm) -> np.ndarray:
    """Cubic Hermite interpolation through anchors, slopes = tan(angleDeg).

    Used by tests to bound the fidelity of the anchor representation:
    the Hermite reconstruction must reproduce the analytic meridian within
    0.2 mm max radial error (TYPOLOGY_PLAN.md s9 V2).
    """
    z_arr = np.array([a[0] for a in anchors], dtype=float)
    r_arr = np.array([a[1] for a in anchors], dtype=float)
    slopes = np.tan(np.radians(np.array([a[2] for a in anchors], dtype=float)))
    cs = CubicHermiteSpline(z_arr, r_arr, slopes)
    return cs(np.asarray(z_mm, dtype=float))


def perturb_increments_shape(
    anchors: list[list[float]],
    u,
    u_max: float,
) -> list[list[float]]:
    """Shape-only monotone-increment perturbation of anchor radii.

    Same construction as :func:`perturb_increments` -- base increments
    ``d_i = r_{i+1} - r_i`` are scaled by ``exp(clip(u_i, -u_max, u_max))`` and the
    radii rebuilt from the throat -- but the perturbed increment vector is then
    rescaled so its sum is unchanged::

        new_d *= d.sum() / new_d.sum()

    The mouth radius is the anchor-radius sum, so it is unchanged to floating-point
    precision: these knobs redistribute the *shape* (where the expansion happens)
    without changing the size.  Mouth size comes from the parent typology's own
    knobs (e.g. ``h_rm_mm``), not from this perturbation.

    ``z`` values are unchanged and the angles are re-derived exactly as in
    :func:`perturb_increments` (monotone PCHIP; throat angle kept from anchor 0).
    ``u_max`` clamping is identical, so every increment stays positive and in the
    same direction class as the legacy path.

    Raises
    ------
    ValueError
        If ``len(u) != len(anchors) - 1``, if the base increments are not all
        positive (same as the legacy path), or if the rescaled increment sum is not
        a finite positive number (impossible-knob guard; the registry turns this
        into an invalid-geometry candidate like any other bad knob).
    """
    u = np.asarray(u, dtype=float)
    n = len(anchors)
    if len(u) != n - 1:
        raise ValueError(f"len(u)={len(u)} must equal len(anchors)−1={n - 1}")

    z_arr   = np.array([a[0] for a in anchors], dtype=float)
    r_arr   = np.array([a[1] for a in anchors], dtype=float)
    theta_base = float(anchors[0][2])

    d = np.diff(r_arr)
    if np.any(d <= 0.0):
        raise ValueError("base increments r_{i+1}−r_i must all be > 0")

    new_d = d * np.exp(np.clip(u, -u_max, u_max))
    total = float(np.sum(new_d))
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("perturbed increment sum is not finite and positive; "
                         "cannot rescale to the parent mouth radius")
    new_d = new_d * (float(np.sum(d)) / total)

    new_r = np.empty(n)
    new_r[0] = r_arr[0]
    for i in range(n - 1):
        new_r[i + 1] = new_r[i] + new_d[i]

    # Re-derive angles via monotone PCHIP (identical to perturb_increments)
    pchip = PchipInterpolator(z_arr, new_r)
    drdzm = pchip.derivative()(z_arr)
    new_theta = np.degrees(np.arctan(drdzm))
    new_theta[0] = theta_base   # keep throat angle from base

    return [
        [float(z_arr[i]), float(new_r[i]), float(new_theta[i])]
        for i in range(n)
    ]
