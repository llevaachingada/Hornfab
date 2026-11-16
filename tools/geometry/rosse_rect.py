"""Rectangular rolled-mouth horn built from ATH's R-OSSE meridian, one meridian per azimuth.

Why (study 2026-11-15, docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md): the rolled-rectangle
experiment (``rolled_rect.py``) uses a log-spiral analogue whose wall angle IS its turning parameter, so the
wall leaves the throat parallel to the axis and keeps turning (no constant-angle section, beam narrows with
frequency), H and V share one normalised contour (no H/V coverage control), and the size of the roll is tied
to ``decay`` (the roll takes ~30% of the mouth radius and ~35% of the depth). Its knobs shape the drawing,
not the acoustics.

This module keeps that family's useful part - a landscape rounded-rectangle mouth with a real rollback - and
puts it on a published constant-directivity construction whose parameters map to acoustic intent:

* each azimuth ``p`` is Marcel Batik's R-OSSE curve (ATH), evaluated by Magnus's installed
  ``hornlab_mesher.profile_formulas.profile_points`` (never re-implemented here) with numeric parameters
  computed for that azimuth - the way ATH builds non-round R-OSSE waveguides (R and a as functions of p);
* ``a(p) = a_v + (a_h - a_v) cos^2 p + a_diag sin^2 2p``: coverage half-angles (HF beamwidth) set
  separately for H and V; ``a_diag`` > 0 widens the diagonals, which draws the Crowe-style creases from the
  throat toward the mouth corners;
* ``R(p)``: the mouth outline is a superellipse through ``width/2`` and ``height/2`` with corner exponent
  ``rect_exponent`` (2 = ellipse, 4-8 = rounded rectangle) - mouth size sets the pattern-control frequency;
* throat ``r0``/``a0`` come from the brief's driver (round, no adapter); ``k`` sets the OS throat
  expansion; ``r``, ``m``, ``b``, ``q``, ``tmax`` are R-OSSE's own mouth / rollback controls.

Depth is not a knob: it follows from coverage and mouth size, as in ATH. LABEL: our construction on ATH's
published R-OSSE; not ATH's own rectangular designs and not Crowe's geometry.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = "rosse-rect-v1"
SHAPE_KEYS = frozenset({
    "width_mm", "height_mm", "rect_exponent", "a_h_deg", "a_v_deg", "a_diag_deg",
    "k", "r", "m", "b", "q", "tmax", "wall_thickness_mm", "n_phi", "n_s",
})


def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f"shape keys: missing={sorted(SHAPE_KEYS-set(shape))}, "
                         f"unknown={sorted(set(shape)-SHAPE_KEYS)}")
    for key, value in shape.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    if not shape["width_mm"] > shape["height_mm"] > 0:
        raise ValueError("this landscape family requires width > height > 0")
    if not 2.0 <= shape["rect_exponent"] <= 12.0:
        raise ValueError("rect_exponent must be in [2,12]")
    for key in ("a_h_deg", "a_v_deg"):
        if not 5.0 <= shape[key] <= 75.0:
            raise ValueError(f"{key} must be in [5,75]")
    if not 0.0 <= shape["a_diag_deg"] <= 20.0:
        raise ValueError("a_diag_deg must be in [0,20]")
    if not 0.5 <= shape["k"] <= 10.0:
        raise ValueError("k must be in [0.5,10]")
    if not 0.05 <= shape["r"] <= 2.0 or not 0.5 <= shape["m"] <= 0.99:
        raise ValueError("need r in [0.05,2] and m in [0.5,0.99]")
    if not 0.0 <= shape["b"] <= 1.0 or not 1.0 <= shape["q"] <= 10.0:
        raise ValueError("need b in [0,1] and q in [1,10]")
    if not 0.5 <= shape["tmax"] <= 1.0:
        raise ValueError("tmax must be in [0.5,1]")
    if shape["wall_thickness_mm"] <= 0:
        raise ValueError("wall_thickness_mm must be positive")
    for key, minimum in (("n_phi", 13), ("n_s", 24)):
        if int(shape[key]) != shape[key] or shape[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")


def mouth_radius(shape, phi):
    """Superellipse mouth radius R(p) through width/2 (p=0) and height/2 (p=90 deg)."""
    e = float(shape["rect_exponent"])
    c, s = np.abs(np.cos(phi)), np.abs(np.sin(phi))
    return ((c / (shape["width_mm"] / 2.0)) ** e + (s / (shape["height_mm"] / 2.0)) ** e) ** (-1.0 / e)


def coverage_deg(shape, phi):
    """Per-azimuth R-OSSE coverage half-angle a(p), degrees."""
    return (shape["a_v_deg"] + (shape["a_h_deg"] - shape["a_v_deg"]) * np.cos(phi) ** 2
            + shape["a_diag_deg"] * np.sin(2.0 * phi) ** 2)


def rosse_params(shape, driver, phi):
    """The numeric R-OSSE parameter set Magnus's profile_points gets for azimuth ``phi``."""
    return {"type": "R-OSSE", "R": float(mouth_radius(shape, phi)), "r0": float(driver["exit_radius_mm"]),
            "a": float(coverage_deg(shape, phi)), "a0": float(driver["exit_angle_deg"]),
            "k": float(shape["k"]), "q": float(shape["q"]), "m": float(shape["m"]), "r": float(shape["r"]),
            "b": float(shape["b"]), "tmax": float(shape["tmax"])}


def meridian(shape, driver, phi, n):
    """(n, 2) array of (axial z, radius) along one azimuth, from the installed mesher's R-OSSE."""
    from hornlab_mesher.profile_formulas import profile_points
    pts = np.asarray(profile_points(rosse_params(shape, driver, phi), int(n), phi=0.0), dtype=float)
    if pts.shape != (int(n), 2) or not np.isfinite(pts).all():
        raise ValueError(f"R-OSSE meridian failed at phi={math.degrees(phi):.1f} deg")
    return pts


def make_grid(shape, brief):
    """Quarter model: rings at equal R-OSSE parameter t across azimuths (shared stations)."""
    validate_shape(shape)
    driver = brief["driver"]
    r0, a0 = float(driver["exit_radius_mm"]), float(driver["exit_angle_deg"])
    if not 0 < r0 < shape["height_mm"] / 2 or not 0 < a0 < 45:
        raise ValueError("need a round throat smaller than the mouth and exit angle in (0,45)")
    phis = np.linspace(0.0, math.pi / 2.0, int(shape["n_phi"]))
    n = int(shape["n_s"]) + 1
    rows = []
    for p in phis:
        try:
            mer = meridian(shape, driver, float(p), n)
        except ValueError as exc:
            raise ValueError(f"R-OSSE: {exc}") from exc
        z, rho = mer[:, 0], mer[:, 1]
        if np.any(rho <= 0):
            raise ValueError("R-OSSE radius reached zero")
        rows.append(np.stack((rho * math.cos(p), rho * math.sin(p), z), axis=-1))
    pts = np.stack(rows)
    pts[0, :, 1] = 0.0
    pts[-1, :, 0] = 0.0
    meta = {"quarter": True, "row_span": "quarter", "symmetry_plane": "yz+xz",
            "source_auto_angle_deg": a0,
            "construction_label": SCHEMA + ": ATH R-OSSE (Batik) per azimuth via hornlab_mesher; ours, "
                                  "not ATH's rectangular designs or Crowe ES",
            "shape": dict(shape)}
    return pts, meta
