"""CPU-only, experimental deformation of a captured quarter GRID shell.

The host is supplied as its original sampled inner and outer sheets in mm.
This is a geometric hypothesis, not Crowe's geometry or an acoustic model.
It changes neither the source nor samples before the compact body onset.
Controls are signed millimetres: positive radial moves outward, positive axial
moves downstream. H/V amplitudes interpolate as cos²(phi)/sin²(phi).
Diagonal amplitudes add a sin²(2 phi) term. The terminal controls have their
own arc window and leave the common entrance untouched.

Both sheets receive the *same* displacement at corresponding stations. This
preserves their sampled separation vectors, but does not establish normal wall
thickness, continuous clearance, surface regularity, or mesh validity. Those
must be screened independently before use; no clipping or repair is performed.
"""

from collections.abc import Mapping
import math

import numpy as np


_KEYS = frozenset({
    f"{region}_{plane}_{axis}_mm"
    for region in ("body", "terminal")
    for plane in ("h", "v", "diagonal")
    for axis in ("axial", "radial")
})


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """C2 transition with compact support; no geometry coordinates clipped."""
    u = np.minimum(1.0, np.maximum(0.0, t))
    return u**3 * (10.0 + u * (-15.0 + 6.0 * u))


def shape_host(inner, outer, controls: Mapping[str, float], *, wall_thickness_mm):
    """Return deformed ``(inner, outer)`` arrays with native sampling unchanged.

    Each row is parameterized by cumulative arc on the captured inner sheet,
    including its rollback. The radial body window rises over arc fractions
    .15-.40 and falls over .60-.85. Axial reach changes through a monotone
    whole-body map between 48 and 215 mm of original axial position. This
    preserves the order of axial stations along any one physical meridian,
    including its original reversal. The independent terminal gate opens
    at .80 of the original meridian arc.
    Exact zero controls return the original input objects, without conversion.
    """
    if not isinstance(controls, Mapping):
        raise ValueError("controls must be a mapping")
    unknown = set(controls) - _KEYS
    if unknown:
        raise ValueError(f"unknown sculpt controls: {sorted(unknown)}")
    values = {key: float(controls.get(key, 0.0)) for key in _KEYS}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("sculpt controls must be finite")
    t = float(wall_thickness_mm)
    if not math.isfinite(t) or t <= 0:
        raise ValueError("wall_thickness_mm must be finite and positive")
    if not any(values.values()):
        return inner, outer

    a = np.asarray(inner, dtype=float)
    b = np.asarray(outer, dtype=float)
    if a.shape != b.shape or a.ndim != 3 or a.shape[-1] != 3 or min(a.shape[:2]) < 2:
        raise ValueError("inner and outer must have matching (n_phi, n_s, 3) shapes")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("host sheets must be finite")
    rho = np.hypot(a[..., 0], a[..., 1])
    if np.any(rho <= 0):
        raise ValueError("host inner radii must be positive")
    step = np.linalg.norm(np.diff(a, axis=1), axis=2)
    if np.any(step <= 0):
        raise ValueError("host meridians must have distinct consecutive samples")
    arc = np.concatenate((np.zeros((a.shape[0], 1)), np.cumsum(step, axis=1)), axis=1)
    u = arc / arc[:, -1:]
    radial_body = _smoothstep((u - .15) / .25) * (1.0 - _smoothstep((u - .60) / .25))
    lead, span = 48.0, 167.0
    axial_body = _smoothstep((a[..., 2] - lead) / span)
    terminal = _smoothstep((u - .80) / .20)
    c = a[..., 0] / rho
    s = a[..., 1] / rho
    h, v = c*c, s*s
    diagonal = 4 * h * v

    def blend(region, axis):
        return (h * values[f"{region}_h_{axis}_mm"] + v * values[f"{region}_v_{axis}_mm"]
                + diagonal * values[f"{region}_diagonal_{axis}_mm"])

    axial_amplitude = blend("body", "axial")
    if np.any(1 + axial_amplitude * (1.875 / span) <= 0):
        raise ValueError("body setback would reverse the axial map")
    dr = radial_body * blend("body", "radial") + terminal * blend("terminal", "radial")
    dz = axial_body * axial_amplitude + terminal * blend("terminal", "axial")
    if np.any(rho + dr <= 0) or np.any(np.hypot(b[..., 0], b[..., 1]) + dr <= 0):
        raise ValueError("sculpt produces a non-positive radius")
    delta = np.stack((dr*c, dr*s, dz), axis=-1)
    return a + delta, b + delta
