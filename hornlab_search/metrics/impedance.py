"""Throat impedance. 01_CONTRACTS.md section 10 (`z_throat_real`)."""
from __future__ import annotations

import numpy as np

from ..constants import C_AIR, RHO_AIR


def normalized_throat_impedance(p, u, area_m2=None, *, is_volume_velocity: bool = False) -> np.ndarray:
    """Specific acoustic impedance at the throat over rho*c: p / (rho*c*u).

    A plane wave in a duct has p = rho*c*u, so z = 1 + 0j exactly.

    If the solver reports volume velocity Q (m^3/s) instead of particle velocity u,
    pass it as `u` with is_volume_velocity=True and the throat area; then u = Q / area_m2.
    """
    p = np.asarray(p, dtype=complex)
    u = np.asarray(u, dtype=complex)
    if is_volume_velocity:
        if area_m2 is None or not float(area_m2) > 0.0:
            raise ValueError("normalized_throat_impedance: volume velocity needs a positive area_m2")
        u = u / float(area_m2)
    return p / (RHO_AIR * C_AIR * u)
