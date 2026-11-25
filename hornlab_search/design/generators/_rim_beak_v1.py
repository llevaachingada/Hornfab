"""Versioned rim-beak kernel (``rim-beak-v1``, LABELED HYPOTHESIS, no published name).

Moves each row's late body, roll-on station, return and rim along the horn axis by an azimuth-dependent amount, so
the mouth stops being a single plane: H lips ahead of or behind V lips, plus a 45-degree scoop. The caller passes an
already-resolved inner point grid (rows = fixed azimuth, row 0 = H plane, last row = V plane; stations = throat ->
forward/max-z station -> returned lip). For every row::

    A(psi)  = rb_h cos^2 psi + rb_v sin^2 psi + rb_d sin^2(2 psi)          (mm, + = toward the listener)
    G(u)    = S((u - rb_start) / (1 - rb_start)) on the pre-roll arc (u = arc fraction to the forward station),
              G = 1 for the forward station and every station after it
    z_new   = z + G(u) A(psi)

``S`` is the C2 quintic, so the throat, the source and the early wall (u <= rb_start) are untouched, the body bends
smoothly into the beak and the lip/return/rim move rigidly (their shape and curl are kept). ``psi`` is the same
normalised section angle the CD backbone uses. All amplitudes zero returns the input array unchanged. Refused: a
pre-roll that stops advancing axially, a forward station that moves, nonfinite output.
"""

from __future__ import annotations

import math

import numpy as np

SCHEMA = "rim-beak-v1"
RB_KEYS = frozenset({"rb_h_mm", "rb_v_mm", "rb_d_mm", "rb_start_frac"})
LIMITS = {"rb_h_mm": (-60.0, 60.0), "rb_v_mm": (-60.0, 60.0), "rb_d_mm": (-30.0, 30.0),
          "rb_start_frac": (0.30, 0.90)}
AMP_KEYS = ("rb_h_mm", "rb_v_mm", "rb_d_mm")


def _S(x):
    x = np.clip(x, 0.0, 1.0)
    return x ** 3 * (10.0 - 15.0 * x + 6.0 * x * x)


def validate_rb(shape):
    for key in RB_KEYS:
        if key not in shape:
            raise ValueError(f"missing rim-beak key {key}")
        value = shape[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        lo, hi = LIMITS[key]
        if not lo <= float(value) <= hi:
            raise ValueError(f"{key} must be in [{lo:g}, {hi:g}]")


def is_neutral(shape):
    return all(float(shape[key]) == 0.0 for key in AMP_KEYS)


def amplitude(psi, shape):
    return (float(shape["rb_h_mm"]) * np.cos(psi) ** 2 + float(shape["rb_v_mm"]) * np.sin(psi) ** 2
            + float(shape["rb_d_mm"]) * np.sin(2.0 * psi) ** 2)


def apply_to_inner(inner, shape):
    """Return ``(new_inner, info)``; the same array and an empty list when neutral."""
    if is_neutral(shape):
        return inner, []
    validate_rb(shape)
    start = float(shape["rb_start_frac"])
    inner = np.asarray(inner, dtype=float)
    out = inner.copy()
    h_ref, v_ref = inner[0, :, 0], inner[-1, :, 1]
    info = []
    for j in range(inner.shape[0]):
        row = inner[j]
        rho = np.hypot(row[:, 0], row[:, 1])
        z = row[:, 2]
        f = int(np.argmax(z))
        if f < 3:
            raise ValueError(f"row {j}: no measurable pre-roll")
        ds = np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1]))
        u = np.r_[0.0, np.cumsum(ds)] / float(ds.sum())
        psi = math.atan2(row[f, 1] / v_ref[f], row[f, 0] / h_ref[f])
        amp = float(amplitude(psi, shape))
        gate = np.ones_like(z)
        gate[:f + 1] = _S((u - start) / (1.0 - start))
        z_new = z + gate * amp
        if not np.all(np.diff(z_new[:f + 1]) > 0.0):
            raise ValueError(f"row {j}: rim beak reverses the pre-roll axial order")
        if int(np.argmax(z_new)) != f:
            raise ValueError(f"row {j}: rim beak moves the forward station")
        out[j, :, 2] = z_new
        info.append({"row": j, "psi_deg": round(math.degrees(psi), 3), "dz_mm": round(amp, 4)})
    if not np.isfinite(out).all():
        raise ValueError("nonfinite rim-beak surface")
    return out, info
