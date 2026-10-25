"""Classical horn meridian generators (TYPOLOGY_PLAN.md s4, V1-V2).

Units throughout: mm for lengths, degrees for angles, Hz for frequencies.
z is measured from the throat; z[0] == 0 always. All arrays are float64.

Le Cléac'h / spherical_wave are gated (R9) and raise GeneratorUnavailable.
See ``lecleach`` docstring for the reason and checked references.

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


def lecleach(r0_mm, fc_hz, T, max_wall_deg: float = 80.0, n: int = 400) -> Meridian:
    """Jean-Michel Le Cléac'h spherical-wave horn (TYPOLOGY_PLAN.md R9 gate).

    STATUS: UNAVAILABLE.

    The published construction requires a complex iterative algorithm in which
    successive spherical wavefront caps (normal to the wall) accumulate area
    following A(s) = A0·(cosh(m·s) + T·sinh(m·s))², where s is the arc coordinate
    along the wavefront progression.  The algorithm cannot be reduced to a
    closed-form r(z) expression; it must be implemented from a verified
    description.

    Sources checked and inaccessible during this implementation pass:
      - J.M. Le Cléac'h, ETF 2010 lecture notes (rintelen.ch/download/
        JMMLC_horns_lecture_etf10.pdf) — download exceeded content-length limit.
      - diyaudio.com/community/threads/jean-michel-on-lecleach-horns.140190/
        — returned HTTP 403 Forbidden.
      - sphericalhorns.net/2020/12/21/jmlc-inspired-horn-calculator/
        — accessible, but the author explicitly states "I don't want to claim
        that my algorithm delivers exactly the same results as the original
        JMLC spreadsheets", so it does not qualify as a citable reference.

    Per TYPOLOGY_PLAN.md section 9 (V6): "Gate: implement from the published
    construction, cross-check against an independent reference; ship disabled
    otherwise."
    """
    raise GeneratorUnavailable(
        "Le Cléac'h generator is disabled: primary sources (ETF 2010 PDF, diyaudio forum) "
        "were inaccessible during implementation; the only accessible 'JMLC-inspired' "
        "calculator disclaims matching the original. "
        "See lecleach() docstring and TYPOLOGY_PLAN.md R9 / V6."
    )


def spherical_wave(r0_mm, fc_hz, max_wall_deg: float = 80.0) -> Meridian:
    """Spherical-wave horn = Le Cléac'h with T=1. See lecleach() for status."""
    return lecleach(r0_mm, fc_hz, T=1.0, max_wall_deg=max_wall_deg)


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
