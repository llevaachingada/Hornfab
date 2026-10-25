"""Classical horn profile generators (TYPOLOGY_PLAN.md s4).

Public API re-exported from profiles.py:
    Meridian             - frozen dataclass: z_mm, r_mm, theta_deg (arrays), info (dict)
    GeneratorUnavailable - raised when a generator is not yet implementable
    conical              - constant-angle flare
    exponential          - exponential area expansion
    hypex                - Salmon hypex (T=0 catenoidal .. T=1 exponential)
    tractrix             - Voigt tractrix, length derived from fc and max_wall_deg
    lecleach             - Le Cléac'h Fourcade 2015 exact construction (R9-J verified)
    spherical_wave       - lecleach(..., T=1.0)
    blend                - weighted blend of two meridians on normalised t=z/L
    select_anchors       - choose [z, r, angleDeg] anchors by equal arc-length in (z,theta) space
    perturb_increments   - monotone radial perturbation via log-increment scaling
    hermite_reference    - cubic Hermite reconstruction from anchors (for fidelity tests)
"""
from .profiles import (
    Meridian,
    GeneratorUnavailable,
    conical,
    exponential,
    hypex,
    tractrix,
    lecleach,
    spherical_wave,
    blend,
    select_anchors,
    perturb_increments,
    hermite_reference,
)

__all__ = [
    "Meridian",
    "GeneratorUnavailable",
    "conical",
    "exponential",
    "hypex",
    "tractrix",
    "lecleach",
    "spherical_wave",
    "blend",
    "select_anchors",
    "perturb_increments",
    "hermite_reference",
]
