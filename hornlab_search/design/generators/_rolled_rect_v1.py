"""Frozen v1 analytic kernel, extracted from the archived research generator.

Keep mathematical behaviour immutable; introduce a new version for shape-law changes.
"""
from __future__ import annotations
import math
import numpy as np

SCHEMA = "rolled-rect-experiment-v1"
SHAPE_KEYS = frozenset({
    "width_mm", "height_mm", "depth_mm", "depth_h_ratio", "decay", "rect_exponent",
    "rect_turn_deg", "throat_turn_deg", "terminal_deg", "pucker_h_mm",
    "pucker_v_mm", "pucker_start_deg", "wall_thickness_mm", "n_phi", "n_s",
})


def smoothstep(x):
    """Clamped C2 window; does not introduce a tangent/curvature jump at its ends."""
    v = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    return v ** 3 * (10.0 - 15.0 * v + 6.0 * v ** 2)


def spiral_reference(turn, decay):
    """Analytical integrals of exp(-b*t)*(cos(t),sin(t)), unit reference scale."""
    t = np.asarray(turn, dtype=float)
    b = float(decay)
    e = np.exp(-b * t)
    return ((e * (-b * np.cos(t) + np.sin(t)) + b) / (1.0 + b * b),
            (e * (-b * np.sin(t) - np.cos(t)) + 1.0) / (1.0 + b * b))


def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f"shape keys: missing={sorted(SHAPE_KEYS-set(shape))}, "
                         f"unknown={sorted(set(shape)-SHAPE_KEYS)}")
    for key, value in shape.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    for key in ("width_mm", "height_mm", "depth_mm", "decay", "wall_thickness_mm"):
        if shape[key] <= 0:
            raise ValueError(f"{key} must be positive")
    if shape["width_mm"] <= shape["height_mm"]:
        raise ValueError("this landscape family requires width > height")
    if not 0.5 <= shape["depth_h_ratio"] <= 1.2:
        raise ValueError("depth_h_ratio must be in [0.5,1.2]")
    if not 2 <= shape["rect_exponent"] <= 16:
        raise ValueError("rect_exponent must be in [2,16]")
    if not 0 < shape["throat_turn_deg"] < shape["rect_turn_deg"] < 90:
        raise ValueError("need 0 < throat_turn_deg < rect_turn_deg < 90")
    if not 180 < shape["terminal_deg"] <= 280:
        raise ValueError("terminal_deg must be in (180,280]")
    if not shape["throat_turn_deg"] < shape["pucker_start_deg"] < 180:
        raise ValueError("pucker_start_deg must follow the throat blend and precede 180")
    if max(abs(shape["pucker_h_mm"]), abs(shape["pucker_v_mm"])) > 0.15*shape["depth_mm"]:
        raise ValueError("pucker exceeds 15 percent of depth")
    for key, minimum in (("n_phi", 25), ("n_s", 32)):
        if int(shape[key]) != shape[key] or shape[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")


def surface_at(shape, driver, turn, phis):
    """Evaluate the original surface in mm at reference turn and physical azimuth.

    H/V pucker amplitudes independently advance the side-wall/upper-lower centres.
    Angular relief has its opposite sign at normalized diagonal psi=45 degrees.
    Both mirror planes are maintained; pucker cannot change the x/y outline.
    """
    validate_shape(shape)
    r0 = float(driver["exit_radius_mm"])
    a0 = math.radians(float(driver["exit_angle_deg"]))
    if r0 <= 0 or not 0 < a0 < math.pi/4:
        raise ValueError("need positive round throat radius and exit angle in (0,45) degrees")
    if shape["height_mm"]/2 <= r0:
        raise ValueError("mouth must exceed the driver exit")
    t = np.asarray(turn, dtype=float).reshape(1, -1)
    phi = np.asarray(phis, dtype=float).reshape(-1, 1)
    zref, uref = spiral_reference(t, shape["decay"])
    z90, _ = spiral_reference(math.pi/2, shape["decay"])
    _, u180 = spiral_reference(math.pi, shape["decay"])
    z = shape["depth_mm"] * zref / z90
    f = uref/u180
    common = math.tan(a0)*z*(1-smoothstep(t/math.radians(shape["throat_turn_deg"])))
    h = r0 + f*(shape["width_mm"]/2-r0) + common
    v = r0 + f*(shape["height_mm"]/2-r0) + common
    p = 2+(shape["rect_exponent"]-2)*smoothstep(t/math.radians(shape["rect_turn_deg"]))
    rho = ((np.abs(np.cos(phi))/h)**p + (np.abs(np.sin(phi))/v)**p)**(-1/p)
    x, y = rho*np.cos(phi), rho*np.sin(phi)
    psi = np.arctan2(y/v, x/h)
    # Cos(4 psi) supplies four smooth wall-centre ridges, with separate H/V strength.
    amp = shape["pucker_h_mm"]*np.cos(psi)**2 + shape["pucker_v_mm"]*np.sin(psi)**2
    start = math.radians(shape["pucker_start_deg"])
    window = smoothstep((t-start)/(math.pi-start))
    # Independent H/V axial development: the broad upper/lower panels can reach
    # further forward than the narrow side panels. Keep the throat's first
    # derivative isotropic; the depth split opens through a C2 window.
    depth_blend = smoothstep(t/math.radians(shape["rect_turn_deg"]))
    zz = z*(1+(shape["depth_h_ratio"]-1)*np.cos(psi)**2*depth_blend)
    if shape["pucker_h_mm"] != 0 or shape["pucker_v_mm"] != 0:
        zz += amp*window*np.cos(4*psi)
    points = np.stack((x, y, zz), axis=-1)
    points[np.isclose(phi[:, 0], 0, atol=1e-14), :, 1] = 0.0
    points[np.isclose(phi[:, 0], math.pi/2, atol=1e-14), :, 0] = 0.0
    return points


def make_grid(shape, brief):
    """Quarter model sampled on a shared turn grid with denser throat sampling."""
    validate_shape(shape)
    # Equal arc steps of a reference H/V mean row, not uniform angle: resolves both
    # the throat and the tight return while preserving shared section stations.
    phis = np.linspace(0, math.pi/2, int(shape["n_phi"]))
    dense_t = np.linspace(0, math.radians(shape["terminal_deg"]), 4097)
    centre = surface_at(shape, brief["driver"], dense_t, [math.pi/4])[0]
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(centre, axis=0), axis=1))]
    turns = np.interp(np.linspace(0, arc[-1], int(shape["n_s"])+1), arc, dense_t)
    points = surface_at(shape, brief["driver"], turns, phis)
    if not np.isfinite(points).all():
        raise ValueError("nonfinite geometry")
    # Sampled surface bounds include every station and azimuth, not axis-only radii.
    meta = {"quarter": True, "row_span": "quarter", "symmetry_plane": "yz+xz",
            "source_auto_angle_deg": float(brief["driver"]["exit_angle_deg"]),
            "construction_label": SCHEMA+": original; not Crowe ES or ATH Tritonia",
            "turns_deg": np.rad2deg(turns).tolist(), "shape": dict(shape)}
    return points, meta

