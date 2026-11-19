"""Pure fabrication-feasibility rules for one resolved system box.

Nothing here meshes, solves or draws. Every function takes a resolved
:class:`~hornlab_search.system.contracts.BoxPoint` plus optional
:class:`~hornlab_search.system.contracts.DriverGeometry` and returns a single human-readable
status string. The status prefixes are:

* ``"PASS: ..."`` — the rule is satisfied;
* ``"FAIL: ..."`` — it is violated (a real, actionable build blocker);
* ``"skip: ..."`` — not evaluable because an input is unknown. **A skip is never a pass.**

No tolerance is loosened: a value exactly on a limit passes only when the comparison is ``<=``
(clearance is inclusive). Default policies are explicit keyword arguments, not hidden constants.
"""
from __future__ import annotations

import math

from hornlab_search.system.bass_reference import bassbox, port_neck_length_mm
from hornlab_search.system.contracts import BoxPoint, DriverGeometry

__all__ = [
    "check_port_fits",
    "check_driver_and_brace_clearance",
    "check_wall_thickness",
    "check_woofer_horn_clearance",
    "fabrication_report",
    "DEFAULT_MIN_WALL_MM",
    "DEFAULT_PORT_CLEARANCE_MM",
    "DEFAULT_BRACE_CLEARANCE_MM",
]

#: Default wall-thickness policy (18 mm is the search default; 12 mm is the hard minimum here).
DEFAULT_MIN_WALL_MM = 12.0
#: Gap left behind the port's flare before the rear wall.
DEFAULT_PORT_CLEARANCE_MM = 10.0
#: Allowance for a brace / crossover / wiring pocket behind the driver magnet.
DEFAULT_BRACE_CLEARANCE_MM = 25.0


def _internal_depth_mm(point: BoxPoint) -> float:
    return float(point.external_depth_mm) - 2.0 * float(point.wall_mm)


def _internal_width_mm(point: BoxPoint) -> float:
    return float(point.external_width_mm) - 2.0 * float(point.wall_mm)


def _internal_height_mm(point: BoxPoint) -> float:
    return float(point.external_height_mm) - 2.0 * float(point.wall_mm)


def check_port_fits(
    point: BoxPoint,
    geometry: DriverGeometry | None = None,
    *,
    clearance_mm: float = DEFAULT_PORT_CLEARANCE_MM,
) -> str:
    """Neck length + flared-port bore radius + clearance must fit inside the internal depth.

    The flare allowance is conservatively the port's equivalent bore radius
    ``sqrt(S_port/pi)`` for a flared round port; a slot port is not modelled at this tier.
    ``geometry`` is unused (the port is self-contained) but kept for the uniform rule signature.
    """
    if point.kind == "sealed":
        return "PASS: sealed box has no port to fit"
    if not (math.isfinite(float(clearance_mm)) and float(clearance_mm) >= 0.0):
        raise ValueError(f"clearance_mm must be finite and >= 0, got {clearance_mm!r}")
    try:
        neck_mm = port_neck_length_mm(point)
    except ValueError as exc:
        return f"FAIL: {exc}"
    if not (math.isfinite(neck_mm) and neck_mm > 0.0):
        return f"FAIL: derived port neck length is not positive ({neck_mm!r} mm)"
    s_port_m2 = float(point.port_throat_area_cm2) * 1e-4
    flare_radius_mm = math.sqrt(max(s_port_m2, 0.0) / math.pi) * 1e3
    internal = _internal_depth_mm(point)
    required = neck_mm + flare_radius_mm + float(clearance_mm)
    if required <= internal + 1e-9:
        return (f"PASS: port needs {required:.1f} mm (neck {neck_mm:.1f} + flare "
                f"{flare_radius_mm:.1f} + clearance {float(clearance_mm):.1f}) "
                f"<= internal depth {internal:.1f} mm")
    return (f"FAIL: port needs {required:.1f} mm (neck {neck_mm:.1f} + flare "
            f"{flare_radius_mm:.1f} + clearance {float(clearance_mm):.1f}) "
            f"> internal depth {internal:.1f} mm")


def check_driver_and_brace_clearance(
    point: BoxPoint,
    geometry: DriverGeometry | None,
    *,
    brace_clearance_mm: float = DEFAULT_BRACE_CLEARANCE_MM,
) -> str:
    """Driver rear depth + brace allowance must fit, and the frame must fit the internal baffle.

    Uses ``mounting_depth_behind_baffle_mm`` when known, else the datasheet ``depth_mm``.
    A missing geometry (or missing depth/frame) is a ``skip``, never a pass.
    """
    if geometry is None:
        return "skip: unknown driver geometry"
    driver_depth = (geometry.mounting_depth_behind_baffle_mm
                    if geometry.mounting_depth_behind_baffle_mm is not None
                    else geometry.depth_mm)
    if driver_depth is None:
        return "skip: unknown driver depth behind the baffle"
    if not (math.isfinite(float(brace_clearance_mm)) and float(brace_clearance_mm) >= 0.0):
        raise ValueError(f"brace_clearance_mm must be finite and >= 0, got {brace_clearance_mm!r}")

    required = float(driver_depth) + float(brace_clearance_mm)
    internal = _internal_depth_mm(point)
    if required > internal + 1e-9:
        return (f"FAIL: driver + brace needs {required:.1f} mm "
                f"(driver {float(driver_depth):.1f} + brace {float(brace_clearance_mm):.1f}) "
                f"> internal depth {internal:.1f} mm")

    if geometry.frame_od_mm is not None:
        frame = float(geometry.frame_od_mm)
        if frame > _internal_width_mm(point) + 1e-9:
            return (f"FAIL: frame OD {frame:.1f} mm > internal width "
                    f"{_internal_width_mm(point):.1f} mm")
        if frame > _internal_height_mm(point) + 1e-9:
            return (f"FAIL: frame OD {frame:.1f} mm > internal height "
                    f"{_internal_height_mm(point):.1f} mm")
    else:
        return (f"PASS: driver + brace needs {required:.1f} mm <= internal depth "
                f"{internal:.1f} mm; frame fit not checked (unknown frame_od_mm)")
    return (f"PASS: driver + brace needs {required:.1f} mm <= internal depth {internal:.1f} mm "
            f"and frame OD {float(geometry.frame_od_mm):.1f} mm fits the baffle")


def check_wall_thickness(
    point: BoxPoint,
    geometry: DriverGeometry | None = None,
    *,
    min_wall_mm: float = DEFAULT_MIN_WALL_MM,
) -> str:
    """``wall_mm >= min_wall_mm`` (default policy: at least 12 mm)."""
    if not (math.isfinite(float(min_wall_mm)) and float(min_wall_mm) > 0.0):
        raise ValueError(f"min_wall_mm must be finite and > 0, got {min_wall_mm!r}")
    wall = float(point.wall_mm)
    if wall >= float(min_wall_mm) - 1e-9:
        return f"PASS: wall {wall:.1f} mm >= minimum {float(min_wall_mm):.1f} mm"
    return f"FAIL: wall {wall:.1f} mm < minimum {float(min_wall_mm):.1f} mm"


def check_woofer_horn_clearance(
    point: BoxPoint,
    geometry: DriverGeometry | None,
    *,
    horn_flange_extent_mm: float | None = None,
) -> str:
    """Woofer frame + horn flange footprint check on the baffle.

    The horn flange extent is *not* part of ``DriverGeometry`` and is not in the cabinet contract,
    so without an explicit ``horn_flange_extent_mm`` this rule deliberately returns
    ``"skip: unknown horn flange"`` rather than inventing a flange size. With an explicit extent it
    performs a conservative footprint screen only (no assembly position, no 3-D clearance).
    """
    if horn_flange_extent_mm is None:
        return "skip: unknown horn flange"
    if geometry is None or geometry.frame_od_mm is None:
        return "skip: unknown driver frame"
    if not (math.isfinite(float(horn_flange_extent_mm)) and float(horn_flange_extent_mm) >= 0.0):
        raise ValueError(
            f"horn_flange_extent_mm must be finite and >= 0, got {horn_flange_extent_mm!r}")
    needed = float(geometry.frame_od_mm) / 2.0 + float(horn_flange_extent_mm)
    available = min(_internal_width_mm(point), _internal_height_mm(point)) / 2.0
    if needed <= available + 1e-9:
        return (f"PASS: footprint-only screen: woofer radius + horn flange {needed:.1f} mm "
                f"<= baffle half-extent {available:.1f} mm")
    return (f"FAIL: footprint-only screen: woofer radius + horn flange {needed:.1f} mm "
            f"> baffle half-extent {available:.1f} mm")


def fabrication_report(
    point: BoxPoint,
    geometry: DriverGeometry | None,
    *,
    min_wall_mm: float = DEFAULT_MIN_WALL_MM,
    horn_flange_extent_mm: float | None = None,
) -> dict[str, str]:
    """All four rule results in one dict (keys are the rule names)."""
    return {
        "port_fits": check_port_fits(point, geometry),
        "driver_and_brace_clearance": check_driver_and_brace_clearance(point, geometry),
        "wall_thickness": check_wall_thickness(point, geometry, min_wall_mm=min_wall_mm),
        "woofer_horn_clearance": check_woofer_horn_clearance(
            point, geometry, horn_flange_extent_mm=horn_flange_extent_mm),
    }
