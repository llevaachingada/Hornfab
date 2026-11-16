"""Elliptically stretched Klangfilm (spherical-wave) horn - port of Dr. Bernd Ahlswede's calculator.

Source (owner-supplied, 2026-11-16): ``Klangfilm_Elliptical_Horn_Calculator_diy_v10.xlsm`` VBA ``draw_klangfilm``
(Ahlswede, Sep/Oct 2018, diyAudio; formulas from B. Kolbrek, "Introduction to Horn Theory", 2007). Personal /
non-commercial use per the author's note in the macro. Construction, line for line with the macro:

* spherical-wave (Klangfilm) horn: ``r0 = c / (pi fc)``; wavefront cap height ``h = h0 exp(m x)`` with
  ``m = 4 pi fc / c`` and ``h0 = r0 - sqrt(r0^2 - y0^2)`` (y0 = throat radius);
  equal-area radius ``yh = sqrt(2 r0 h - h^2)`` (cap area ``2 pi r0 h``); axial station ``xh = x - h + h0``.
  The profile widens to ``yh = r0`` at ``h = r0`` and then ROLLS BACK and closes as ``h -> 2 r0`` - the
  rollback is the profile itself, not an added lip;
* elliptical stretch: ``strm = 1 + sin(((yh - y0)/(r0 - y0)) pi/2)(stretch - 1)`` - 1 (round) at the throat,
  ``stretch`` at the widest point; the wavefront is a tri-axial ellipsoid cap with ``rb = r0 / strm`` and
  ``ra`` solved (Newton in the macro, bracketed root here) so its cap area equals the spherical cap
  ``2 pi r0 h``; the section semi-axes are ``xa = ra sin(thz)``, ``yb = rb sin(thz)``, ``thz = acos(1 - h/r0)``;
* every section is a PLANAR ellipse at its own ``xh`` (all azimuths share the station).

Knobs: ``fc_hz`` (cut-off -> r0, the curl radius and mouth size), ``stretch`` (H/V aspect at the widest point;
H = major axis), ``end_frac`` = h_end / r0 (how far the profile runs: 1.0 = widest point / mouth perpendicular,
up to 1.9 = deep rollback). The macro's later "bent" variants (diyAudio, construction-vector bending / stereographic
projection) are NOT implemented here - this is the published base construction.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = "klangfilm-ellipse-v1"
SHAPE_KEYS = frozenset({"fc_hz", "stretch", "end_frac", "bend_radius_mm", "throat_ellipse", "wall_thickness_mm", "n_phi", "n_s"})
C_AIR = 343.0          # the macro's cs
_NI = 160              # cap-area quadrature points per axis


def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f"shape keys: missing={sorted(SHAPE_KEYS - set(shape))}, "
                         f"unknown={sorted(set(shape) - SHAPE_KEYS)}")
    for key in ("fc_hz", "stretch", "end_frac", "bend_radius_mm", "throat_ellipse", "wall_thickness_mm"):
        v = shape[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{key} must be a finite number")
    if not 150.0 <= shape["fc_hz"] <= 3000.0:
        raise ValueError("fc_hz must be in [150, 3000]")
    if not 1.0 <= shape["stretch"] <= 4.0:
        raise ValueError("stretch must be in [1, 4]")
    if not 0.3 <= shape["end_frac"] <= 1.9:
        raise ValueError("end_frac (h_end / r0) must be in [0.3, 1.9]")
    if not 150.0 <= shape["bend_radius_mm"] <= 20000.0:
        raise ValueError("bend_radius_mm must be in [150, 20000] (large = flat front)")
    if not 0.1 <= shape["throat_ellipse"] <= 1.0:
        raise ValueError("throat_ellipse must be in [0.1, 1] (1 = calculator ramp; lower = elliptical sooner)")
    if shape["wall_thickness_mm"] <= 0:
        raise ValueError("wall_thickness_mm must be positive")
    for key, minimum in (("n_phi", 7), ("n_s", 24)):
        if int(shape[key]) != shape[key] or shape[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")


def _cap_area(a, b, c, h):
    """Surface of the tri-axial ellipsoid cap of height h on the c axis (macro ``ecap``, midpoint rule)."""
    th_m = math.acos(max(-1.0, min(1.0, 1.0 - h / c)))
    th = (np.arange(_NI) + 0.5) * th_m / _NI
    ph = (np.arange(_NI) + 0.5) * math.pi / _NI
    st, ct = np.sin(th)[:, None], np.cos(th)[:, None]
    sp, cp = np.sin(ph)[None, :], np.cos(ph)[None, :]
    f = np.abs(st) * np.sqrt(c * c * st * st * (b * b * cp * cp + a * a * sp * sp) + a * a * b * b * ct * ct)
    return 2.0 * float(f.sum()) * (th_m / _NI) * (math.pi / _NI)


def _solve_ra(rb, r0, h, target):
    """ra with cap_area(ra, rb, r0, h) == target (monotone in ra; bracketed bisection, as the macro's Newton)."""
    lo, hi = rb, rb
    while _cap_area(hi, rb, r0, h) < target:
        hi *= 1.5
        if hi > 50 * r0:
            raise ValueError("ellipsoid cap area did not bracket")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _cap_area(mid, rb, r0, h) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def profile(shape, y0_mm):
    """(xh, xa, yb) in mm along the horn, densely sampled from the throat to h_end."""
    fc, s, end_frac = float(shape["fc_hz"]), float(shape["stretch"]), float(shape["end_frac"])
    r0 = C_AIR / (math.pi * fc)                       # m
    y0 = y0_mm / 1000.0
    if not y0 < r0:
        raise ValueError(f"throat radius {y0_mm} mm must be below r0 {r0 * 1000:.1f} mm (lower fc_hz)")
    h0 = r0 - math.sqrt(r0 * r0 - y0 * y0)
    m = 4.0 * math.pi * fc / C_AIR
    h_end = end_frac * r0
    # dense samples in h (geometric near the throat, linear later) -> x = ln(h/h0)/m
    hs = np.unique(np.concatenate((np.geomspace(h0, h_end, 300), np.linspace(h0, h_end, 300))))
    out = []
    for h in hs:
        x = math.log(h / h0) / m
        yh = math.sqrt(max(2 * r0 * h - h * h, 0.0))
        xh = x - h + h0
        arg = min(max((yh - y0) / (r0 - y0), 0.0), 1.0)
        # owner 2026-11-16: the throat must turn elliptical (wider H than V) soon after the round driver exit;
        # throat_ellipse < 1 front-loads the calculator's sine ramp (1.0 = the macro exactly).
        arg = arg ** float(shape.get("throat_ellipse", 1.0))
        strm = 1.0 + math.sin(arg * math.pi / 2.0) * (s - 1.0)
        rb = r0 / strm
        if strm == 1.0:
            ra = r0
        else:
            ra = _solve_ra(rb, r0, h, 2.0 * math.pi * r0 * h)
        thz = math.acos(max(-1.0, min(1.0, 1.0 - h / r0)))
        out.append((xh * 1000.0, ra * math.sin(thz) * 1000.0, rb * math.sin(thz) * 1000.0))
    arr = np.asarray(out)
    # the throat row is exactly round at the driver exit radius
    arr[0, 1] = arr[0, 2] = y0_mm
    return arr


def make_grid(shape, brief):
    """Quarter model: planar elliptical sections at shared stations, resampled by arc length."""
    validate_shape(shape)
    r_exit = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    prof = profile(shape, r_exit)
    # resample stations by arc length of the mean-radius meridian (smooth spacing through the rollback)
    rm = 0.5 * (prof[:, 1] + prof[:, 2])
    seg = np.hypot(np.diff(prof[:, 0]), np.diff(rm))
    arc = np.concatenate(([0.0], np.cumsum(seg)))
    n = int(shape["n_s"]) + 1
    t = np.linspace(0.0, arc[-1], n)
    z = np.interp(t, arc, prof[:, 0])
    a = np.interp(t, arc, prof[:, 1])
    b = np.interp(t, arc, prof[:, 2])
    phis = np.linspace(0.0, math.pi / 2.0, int(shape["n_phi"]))
    pts = np.stack([np.stack((a * math.cos(p), b * math.sin(p), z), axis=-1) for p in phis])
    # FRONT CURVE (owner 2026-11-16): bend the horn about a vertical axis on the throat centre line so that,
    # seen from above, the front edge is an arc of radius R - the centre line reaches furthest forward and the
    # sides (H, x = major axis) pull back by the sagitta R - sqrt(R^2 - x^2); seen from the side, the top/bottom
    # lips (V control) then extend further forward than the side lips (H control). Large R = flat front.
    R = float(shape["bend_radius_mm"])
    half_w = float(np.max(np.abs(pts[0, :, 0])))           # widest half-width (H row)
    if half_w >= R:
        raise ValueError(f"bend_radius_mm {R:.0f} must exceed the half-width {half_w:.0f} mm")
    # Per-ROW rigid shift (a point-wise shift by x shears the rolled lip into a fold): row phi is pulled
    # back by the sagitta at its rim's lateral position, ramped in smoothly along the horn (0 at the throat).
    rim_x = np.abs(pts[:, -1, 0]) if np.max(np.abs(pts[:, -1, 0])) > 0 else np.abs(pts[:, :, 0]).max(axis=1)
    rim_x = np.minimum(np.abs(pts[:, :, 0]).max(axis=1), half_w)
    sag = R - np.sqrt(R * R - rim_x * rim_x)                 # (n_phi,)
    u = np.linspace(0.0, 1.0, pts.shape[1])
    w = u * u * (3.0 - 2.0 * u)                              # smoothstep along the arc stations
    pts[..., 2] = pts[..., 2] - sag[:, None] * w[None, :]
    pts[0, :, 1] = 0.0
    pts[-1, :, 0] = 0.0
    meta = {"quarter": True, "row_span": "quarter", "symmetry_plane": "yz+xz",
            "source_auto_angle_deg": a0,
            "construction_label": SCHEMA + ": Klangfilm spherical-wave horn, elliptical stretch "
                                  "(Ahlswede 2018 calculator, Kolbrek 2007)",
            "r0_mm": C_AIR / (math.pi * float(shape["fc_hz"])) * 1000.0,
            "shape": dict(shape)}
    return pts, meta
