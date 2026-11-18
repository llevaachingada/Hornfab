"""Pure fabrication-feasibility rules for the system package (no mesher, no solver)."""
from __future__ import annotations

from hornlab_search.system.geometry.rules import (
    DEFAULT_BRACE_CLEARANCE_MM,
    DEFAULT_MIN_WALL_MM,
    DEFAULT_PORT_CLEARANCE_MM,
    check_driver_and_brace_clearance,
    check_port_fits,
    check_wall_thickness,
    check_woofer_horn_clearance,
    fabrication_report,
)

__all__ = [
    "DEFAULT_BRACE_CLEARANCE_MM",
    "DEFAULT_MIN_WALL_MM",
    "DEFAULT_PORT_CLEARANCE_MM",
    "check_driver_and_brace_clearance",
    "check_port_fits",
    "check_wall_thickness",
    "check_woofer_horn_clearance",
    "fabrication_report",
]
