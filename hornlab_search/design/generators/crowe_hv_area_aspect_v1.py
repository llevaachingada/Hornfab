"""CROWE-inspired H/V area+aspect waveguide family, forward flare only (schema v1, V2A contract).

V2A addendum:
``docs/research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md``. It supersedes the
V2 senior research and the earlier chat's 15-40 mm circular-hold rule on throat transition and
parameter count.

Exactly four search dimensions (``PARAM_KEYS``):

* ``height_v_active_mm`` -- true vertical aperture budget.
* ``L_forward_mm`` -- forward acoustic section length.
* ``area_mid_bias`` -- one interior log-area bias (normalized -0.15..+0.15) whose C2 window and
  first two derivatives vanish at both ends.
* ``aspect_timing_u50`` -- the physical forward-depth fraction where half of the H/V aspect
  development has happened; one timing coordinate replacing aspect-mid/late onset/rate knobs.

Fixed generator-block values (not search dimensions):

* ``width_h_active_mm`` -- held at a production reference (~560-580 mm) for the vertical study.
* ``p_mouth`` -- fixed provisional ~3-3.5; compare p=2.2 vs 3.5 as a paired A/B config.
* ``throat_round_hold_mm`` -- fixed 0 by default (ATH CORE starts the smooth morph at the throat);
  a 20 mm expanding-circular hold config exists for the T2 A/B. It is never a search knob.

Construction on ``u = z/L_forward`` in ``[0, 1]``:

```
A(0) = pi r0^2,   A(1) = C(p_mouth) (W/2) (H/2)
log A(u) = log A(0) + log(A(1)/A(0)) * [m0 u + (1 - m0) u^2] + area_mid_bias * B_A(u)
m0 = (L * 2 tan(exit_angle) / r0) / log(A(1)/A(0)),   0 <= m0 <= 2
S_R(u) = smootherstep(w(u)),  w = u / (u + q (1-u)),  q = u50 / (1-u50)
log R(u) = log(W/H) * S_R(u)
p(u) = 2 + (p_mouth - 2) * S_R(u)
a = sqrt(A R / C(p)),   b = sqrt(A / (R C(p))),
C(p) = 4 Gamma(1 + 1/p)^2 / Gamma(1 + 2/p)
```

``S_R`` is monotone and C2: zero first and second derivatives at u=0 and u=1 for every
``u50``, exact half point ``S_R(u50)=0.5``, and no extra optimization dimension. The area law's
initial slope equals the driver-exit tangent, so ``a'(0) = b'(0) = tan(exit_angle)`` while
``R'(0) = p'(0) = 0``. For a fixed positive throat hold, the gate is shifted to
``S_R((u-h)/(1-h))``; the section is exactly circular over the hold and remains C2 at its boundary.

Not implemented here (Phase 2, no knob registered): returned lip/roll, rim setback, X crease,
independent area-late / aspect-mid / aspect-late knobs, throat-angle search, objective/search
default changes.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import scipy

from ._lame_cap_v1 import flat_lame_area
from .registry import GeneratorError

KIND = "crowe_hv_area_aspect_v1"
SCHEMA = "crowe-hv-area-aspect-v1"

#: The four V2A search dimensions.
PARAM_KEYS = frozenset({
    "height_v_active_mm",
    "L_forward_mm",
    "area_mid_bias",
    "aspect_timing_u50",
})

#: Fixed generator-block keys. ``seed_policy`` is a config directive, not geometry.
GEN_KEYS = frozenset({
    "name",
    "n_anchors",
    "wall_thickness_mm",
    "width_h_active_mm",
    "p_mouth",
    "throat_round_hold_mm",
    "seed_policy",
})
SHAPE_KEYS = PARAM_KEYS | (GEN_KEYS - {"name", "seed_policy"})

#: Module-level physical limits. Search priors (narrower) live in the YAML configs.
_BOUNDS = {
    "area_mid_bias": (-0.15, 0.15),
    "aspect_timing_u50": (0.15, 0.75),
    "p_mouth": (2.0, 5.0),
    "throat_round_hold_mm": (0.0, 200.0),
    "wall_thickness_mm": (0.5, 12.0),
}

_N_ANCHORS_MIN = 9
_N_ANCHORS_MAX = 32          # also the mesher's crossSections maximum
_DENSE = 2049
DEFAULT_CUTS_MM = (0.0, 5.0, 10.0, 20.0, 40.0, 60.0, 100.0)


def is_family_spec(spec) -> bool:
    return isinstance(spec, dict) and spec.get("name") == KIND


def implementation_digest() -> str:
    """SHA-256 of this module plus the numerical library versions that shape its floats."""
    data = Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256()
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)
    digest.update(f"numpy={np.__version__};scipy={scipy.__version__}".encode())
    return digest.hexdigest()


def _driver(brief) -> dict:
    driver = (brief or {}).get("driver")
    if not isinstance(driver, dict):
        raise GeneratorError("crowe_hv_area_aspect_v1 requires an explicit driver")
    try:
        out = {k: float(driver[k]) for k in ("exit_radius_mm", "exit_angle_deg")}
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError("driver radius and exit angle are required") from exc
    if not all(math.isfinite(v) for v in out.values()):
        raise GeneratorError("driver radius and exit angle must be finite")
    if out["exit_radius_mm"] <= 0 or not 0.0 <= out["exit_angle_deg"] < 45.0:
        raise GeneratorError("invalid driver radius or exit angle")
    return out


def _shape(gen, knobs) -> dict:
    if not is_family_spec(gen):
        raise GeneratorError(f"expected generator name {KIND!r}")
    unknown = sorted(set(gen) - GEN_KEYS)
    if unknown:
        raise GeneratorError(f"unknown generator key(s) {unknown}")
    if not isinstance(knobs, dict):
        raise GeneratorError("knobs must be a mapping")
    if set(knobs) != PARAM_KEYS:
        raise GeneratorError(
            f"knob mismatch: missing={sorted(PARAM_KEYS - set(knobs))}, "
            f"unknown={sorted(set(knobs) - PARAM_KEYS)}")
    shape = {**{k: gen[k] for k in GEN_KEYS - {"name", "seed_policy"} if k in gen}, **knobs}
    shape.setdefault("n_anchors", 29)
    shape.setdefault("wall_thickness_mm", 3.0)
    shape.setdefault("width_h_active_mm", 580.0)
    shape.setdefault("p_mouth", 3.25)
    shape.setdefault("throat_round_hold_mm", 0.0)
    _validate_shape(shape)
    return shape


def _validate_shape(shape) -> None:
    if not isinstance(shape, dict) or set(shape) != SHAPE_KEYS:
        raise GeneratorError(
            f"shape keys: missing={sorted(SHAPE_KEYS - set(shape or {}))}, "
            f"unknown={sorted(set(shape or {}) - SHAPE_KEYS)}")
    for key, value in shape.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise GeneratorError(f"{key} must be a finite number")
    if shape["L_forward_mm"] <= 0.0:
        raise GeneratorError("L_forward_mm must be positive")
    if shape["width_h_active_mm"] <= 0.0 or shape["height_v_active_mm"] <= 0.0:
        raise GeneratorError("width_h_active_mm and height_v_active_mm must be positive")
    for key, (lo, hi) in _BOUNDS.items():
        if not lo <= float(shape[key]) <= hi:
            raise GeneratorError(f"{key} must be in [{lo}, {hi}], got {shape[key]}")
    if not 0.0 < float(shape["aspect_timing_u50"]) < 1.0:
        raise GeneratorError("aspect_timing_u50 must be in (0, 1)")
    hold = float(shape["throat_round_hold_mm"])
    if hold >= 0.5 * float(shape["L_forward_mm"]):
        raise GeneratorError("throat_round_hold_mm must be shorter than half of L_forward_mm")
    if hold > 0.0 and float(shape["aspect_timing_u50"]) <= hold / float(shape["L_forward_mm"]):
        raise GeneratorError("aspect_timing_u50 must lie beyond the fixed throat hold")
    n = shape["n_anchors"]
    if int(n) != n or not _N_ANCHORS_MIN <= int(n) <= _N_ANCHORS_MAX:
        raise GeneratorError(
            f"n_anchors must be an integer in [{_N_ANCHORS_MIN}, {_N_ANCHORS_MAX}], got {n!r}")


def _smootherstep(x):
    t = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    return t * t * t * (10.0 + t * (-15.0 + 6.0 * t))


def _timing(u, u50: float):
    """Warped-quintic C2 timing law: S(0)=0, S(u50)=0.5, S(1)=1, S'=S''=0 at both ends.

    ``q = u50/(1-u50)``, ``w = u/(u + q(1-u))``, ``S = smootherstep(w)``. The warp keeps the
    single u50 timing coordinate while the outer quintic supplies the endpoint derivatives.
    """
    u = np.asarray(u, dtype=float)
    q = float(u50) / (1.0 - float(u50))
    w = u / (u + q * (1.0 - u))
    return _smootherstep(w)


def timing_derivatives(u, u50: float):
    """Analytic ``(S, dS/du, d2S/du2)`` for the warped quintic; tests and diagnostics."""
    u = np.asarray(u, dtype=float)
    q = float(u50) / (1.0 - float(u50))
    den = q + u * (1.0 - q)
    w = u / den
    wp = q / den ** 2
    wpp = -2.0 * q * (1.0 - q) / den ** 3
    s = _smootherstep(w)
    ds = 30.0 * w * w * (1.0 - w) ** 2 * wp
    d2s = (60.0 * w * (1.0 - w) * (1.0 - 2.0 * w) * wp ** 2
           + 30.0 * w * w * (1.0 - w) ** 2 * wpp)
    return s, ds, d2s


def _aspect_gate(u, u50: float, hold_u: float):
    """Timing law, optionally after a fixed expanding-circular hold (C2 at the boundary)."""
    u = np.asarray(u, dtype=float)
    if hold_u > 0.0:
        raw = (float(u50) - hold_u) / (1.0 - hold_u)
        s = np.clip((u - hold_u) / (1.0 - hold_u), 0.0, 1.0)
        return _timing(s, raw)
    return _timing(u, float(u50))


def _area_mid_window(u):
    """C3 compact mid-area basis: value and first two derivatives are zero at both ends."""
    u = np.asarray(u, dtype=float)
    return (4.0 * u * (1.0 - u)) ** 4


def evaluate(shape, brief, u) -> dict:
    """Evaluate the continuous V2A law at ``u`` in [0, 1]; mm, mm^2, dimensionless."""
    _validate_shape(shape)
    driver = _driver(brief)
    r0 = driver["exit_radius_mm"]
    a0 = driver["exit_angle_deg"]
    width = float(shape["width_h_active_mm"])
    height = float(shape["height_v_active_mm"])
    if width / 2.0 <= r0 or height / 2.0 <= r0:
        raise GeneratorError("mouth must exceed the driver exit")
    u = np.asarray(u, dtype=float)
    if np.any(~np.isfinite(u)) or np.any((u < 0.0) | (u > 1.0)):
        raise GeneratorError("u must be finite and lie in [0, 1]")
    length = float(shape["L_forward_mm"])
    p_mouth = float(shape["p_mouth"])
    area0 = math.pi * r0 * r0
    area1 = flat_lame_area(width / 2.0, height / 2.0, p_mouth)
    if not area1 > area0:
        raise GeneratorError("mouth area must exceed the throat area")
    delta = math.log(area1 / area0)
    slope0 = length * 2.0 * math.tan(math.radians(a0)) / r0
    m0 = slope0 / delta
    if not -1e-12 <= m0 <= 2.0 + 1e-12:
        raise GeneratorError(
            "no monotone area law with the driver exit tangent: normalized throat slope "
            f"m0={m0:.6f} must be in [0, 2]; use a gentler exit angle, shorter depth, or a "
            "different family")
    base = m0 * u + (1.0 - m0) * u * u
    log_area = (math.log(area0) + delta * base
                + float(shape["area_mid_bias"]) * _area_mid_window(u))
    hold_u = float(shape["throat_round_hold_mm"]) / length
    u50 = float(shape["aspect_timing_u50"])
    gate = _aspect_gate(u, u50, hold_u)
    log_aspect = math.log(width / height) * gate
    p = 2.0 + (p_mouth - 2.0) * gate
    area = np.exp(log_area)
    aspect = np.exp(log_aspect)
    c = np.array([flat_lame_area(1.0, 1.0, float(v)) for v in p])
    a = np.sqrt(area * aspect / c)
    b = np.sqrt(area / (aspect * c))
    return {
        "z_mm": u * length,
        "a_mm": a,
        "b_mm": b,
        "p": p,
        "area_mm2": area,
        "aspect": aspect,
        "log_area": log_area,
        "log_aspect": log_aspect,
        "aspect_gate": gate,
        "area_throat_mm2": area0,
        "area_mouth_mm2": area1,
        "area_ratio": area1 / area0,
        "m0": m0,
        "delta_log_area": delta,
        "u50": u50,
        "hold_u": hold_u,
        "warp_q": (float(u50) / (1.0 - float(u50)) if hold_u == 0.0
                   else ((u50 - hold_u) / (1.0 - hold_u))
                   / (1.0 - (u50 - hold_u) / (1.0 - hold_u))),
    }


def _check_forward(law) -> None:
    for name, radii in (("H", law["a_mm"]), ("V", law["b_mm"])):
        if not np.isfinite(radii).all() or float(radii.min()) <= 0.0:
            raise GeneratorError(f"{name} forward radius must be finite and positive")
        if np.any(np.diff(radii) <= 0.0):
            raise GeneratorError(
                f"{name} forward radius is not strictly increasing; the area bias or timing "
                "is incompatible with this parent")


def _check_shape_geometry(shape, brief) -> dict:
    law = evaluate(shape, brief, np.linspace(0.0, 1.0, _DENSE))
    _check_forward(law)
    return law


def _anchor_u(n: int):
    s = np.linspace(0.0, 1.0, int(n))
    return 0.5 * (1.0 - np.cos(math.pi * s))


def _rows(z, radii, angles):
    return [[round(float(zi), 6), round(float(ri), 6), round(float(ai), 6)]
            for zi, ri, ai in zip(z, radii, angles)]


def materialize(gen, knobs, brief) -> dict:
    """Generator block + four knobs -> ordinary FREEFORM params (H/V meridians + stations)."""
    shape = _shape(gen, knobs)
    driver = _driver(brief)
    r0 = driver["exit_radius_mm"]
    width = float(shape["width_h_active_mm"])
    height = float(shape["height_v_active_mm"])
    length = float(shape["L_forward_mm"])
    envelope = (brief or {}).get("envelope") or {}
    for key, actual in (("max_mouth_w_mm", width), ("max_mouth_h_mm", height),
                        ("max_depth_mm", length)):
        limit = envelope.get(key)
        if limit is not None and actual > float(limit) + 1e-9:
            raise GeneratorError(f"invalid_envelope: {key} {actual:.3f} exceeds {float(limit):.3f}")
    if width / 2.0 <= r0 or height / 2.0 <= r0:
        raise GeneratorError("mouth must exceed the driver exit")
    dense = _check_shape_geometry(shape, brief)
    u = _anchor_u(int(shape["n_anchors"]))
    anchors = evaluate(shape, brief, u)
    slope_h = np.gradient(dense["a_mm"], dense["z_mm"], edge_order=2)
    slope_v = np.gradient(dense["b_mm"], dense["z_mm"], edge_order=2)
    angle_h = np.degrees(np.arctan(np.interp(anchors["z_mm"], dense["z_mm"], slope_h)))
    angle_v = np.degrees(np.arctan(np.interp(anchors["z_mm"], dense["z_mm"], slope_v)))

    def profile(radii, angles):
        return {"points": _rows(anchors["z_mm"], radii, angles),
                "throatAngleDeg": round(float(angles[0]), 6),
                "mouthAngleDeg": round(float(angles[-1]), 6)}

    hold_u = float(shape["throat_round_hold_mm"]) / length
    stations = [{"t": 0.0, "shape": "circle"}]
    if hold_u > 1e-9:
        # Fixed expanding-circular hold end. Nudge it off an anchor station: the mesher refuses
        # semantic axial features closer than 1e-7 in normalized t.
        t_hold = hold_u + (2e-6 if float(np.min(np.abs(u - hold_u))) < 1e-6 else 0.0)
        stations.append({"t": round(float(t_hold), 6), "shape": "superellipse", "exponent": 2.0})
    for i in range(len(u) - 1):
        t_mid = 0.5 * (u[i] + u[i + 1])
        if t_mid <= hold_u + 1e-9:
            continue
        stations.append({"t": round(float(t_mid), 6), "shape": "superellipse",
                         "exponent": round(float(np.interp(t_mid, u, anchors["p"])), 6)})
    stations.append({"t": 1.0, "shape": "superellipse",
                     "exponent": round(float(anchors["p"][-1]), 6)})
    return {
        "profileH": profile(anchors["a_mm"], angle_h),
        "profileV": profile(anchors["b_mm"], angle_v),
        "crossSections": stations,
        "wall_thickness_mm": round(float(shape["wall_thickness_mm"]), 6),
    }


def _slope_curvature(law):
    z = law["z_mm"]

    def slope(r):
        return np.gradient(r, z, edge_order=2)

    def curvature(r):
        rp = slope(r)
        rpp = np.gradient(rp, z, edge_order=2)
        return np.abs(rpp) / (1.0 + rp * rp) ** 1.5

    return slope(law["a_mm"]), slope(law["b_mm"]), curvature(law["a_mm"]), curvature(law["b_mm"])


def section_cuts(gen, knobs, brief, stations_mm=DEFAULT_CUTS_MM) -> list[dict]:
    """Physical-section table: area, aspect, roundness, wall tangent and meridian curvature.

    The default stations are the V2A review set 0/5/10/20/40/60/100 mm. ``inside_round_hold``
    refers only to the fixed ``throat_round_hold_mm`` (0 by default); there is no universal
    15-40 mm rule. Curvature is ``|r''|/(1+r'^2)^(3/2)`` in 1/mm.
    """
    shape = _shape(gen, knobs)
    length = float(shape["L_forward_mm"])
    stations = np.asarray(stations_mm, dtype=float).reshape(-1)
    if np.any(~np.isfinite(stations)) or np.any((stations < 0.0) | (stations > length)):
        raise GeneratorError(f"section stations must lie in [0, {length:.3f}] mm")
    u = stations / length
    law = evaluate(shape, brief, u)
    dense = evaluate(shape, brief, np.linspace(0.0, 1.0, _DENSE))
    z = dense["z_mm"]
    slope_h, slope_v, kappa_h, kappa_v = _slope_curvature(dense)
    hold_mm = float(shape["throat_round_hold_mm"])
    rows = []
    for i, z_mm in enumerate(stations):
        rows.append({
            "z_mm": round(float(z_mm), 4),
            "a_mm": round(float(law["a_mm"][i]), 4),
            "b_mm": round(float(law["b_mm"][i]), 4),
            "area_mm2": round(float(law["area_mm2"][i]), 3),
            "area_ratio_to_throat": round(float(law["area_mm2"][i] / law["area_throat_mm2"]), 6),
            "aspect": round(float(law["aspect"][i]), 6),
            "p": round(float(law["p"][i]), 6),
            "aspect_gate": round(float(law["aspect_gate"][i]), 6),
            "wall_h_deg": round(float(np.degrees(np.arctan(np.interp(z_mm, z, slope_h)))), 4),
            "wall_v_deg": round(float(np.degrees(np.arctan(np.interp(z_mm, z, slope_v)))), 4),
            "curvature_h_1_per_mm": round(float(np.interp(z_mm, z, kappa_h)), 8),
            "curvature_v_1_per_mm": round(float(np.interp(z_mm, z, kappa_v)), 8),
            "inside_round_hold": bool(z_mm <= hold_mm + 1e-9),
        })
    return rows


def _throat_smoothness(shape, brief) -> dict:
    length = float(shape["L_forward_mm"])
    u50 = float(shape["aspect_timing_u50"])
    hold_u = float(shape["throat_round_hold_mm"]) / length
    law = evaluate(shape, brief, np.array([0.0, 5.0 / length, 10.0 / length,
                                           20.0 / length, u50]))
    first20 = law["z_mm"] <= 20.0 + 1e-12
    return {
        "aspect_at_5mm": round(float(law["aspect"][1]), 9),
        "aspect_at_10mm": round(float(law["aspect"][2]), 9),
        "aspect_at_20mm": round(float(law["aspect"][3]), 9),
        "p_at_5mm": round(float(law["p"][1]), 9),
        "p_at_10mm": round(float(law["p"][2]), 9),
        "p_at_20mm": round(float(law["p"][3]), 9),
        "max_abs_aspect_minus_1_over_first_20mm": round(
            float(np.max(np.abs(law["aspect"][first20] - 1.0))), 12),
        "max_abs_p_minus_2_over_first_20mm": round(
            float(np.max(np.abs(law["p"][first20] - 2.0))), 12),
        "aspect_timing_u50": u50,
        "gate_at_u50": round(float(law["aspect_gate"][-1]), 12),
        "fixed_throat_round_hold_mm": float(shape["throat_round_hold_mm"]),
        "hold_fraction": round(float(hold_u), 9),
        "warp_q": round(float(
            (u50 if hold_u == 0.0 else (u50 - hold_u) / (1.0 - hold_u))
            / (1.0 - (u50 if hold_u == 0.0 else (u50 - hold_u) / (1.0 - hold_u)))), 9),
    }


def info(gen, knobs, brief) -> dict:
    """JSON-safe report of the V2A law, fixed values, fixed values and deferred Phase 2 items."""
    shape = _shape(gen, knobs)
    driver = _driver(brief)
    u = np.linspace(0.0, 1.0, _DENSE)
    law = evaluate(shape, brief, u)
    slope_h, slope_v, _, _ = _slope_curvature(law)
    u50 = float(shape["aspect_timing_u50"])
    i50 = int(np.argmin(np.abs(u - u50)))
    i0 = 0
    i1 = len(u) - 1
    margin = float(min(np.diff(law["a_mm"]).min(), np.diff(law["b_mm"]).min()))
    return {
        "kind": KIND,
        "schema": SCHEMA,
        "implementation_sha256": implementation_digest(),
        "construction_label": (
            SCHEMA + ": forward area/aspect superellipse; V2A four-variable contract; our "
            "construction, not Crowe CAD; no returned lip or X crease"),
        "source_tangent_is_assumption": True,
        "source_angle_deg_is_assumption": True,
        "driver": driver,
        "search_keys": sorted(PARAM_KEYS),
        "fixed": {
            "width_h_active_mm": float(shape["width_h_active_mm"]),
            "p_mouth": float(shape["p_mouth"]),
            "throat_round_hold_mm": float(shape["throat_round_hold_mm"]),
            "n_anchors": int(shape["n_anchors"]),
            "wall_thickness_mm": float(shape["wall_thickness_mm"]),
        },
        "aspect_timing": {
            "u50": u50,
            "u50_z_mm": round(float(u50 * float(shape["L_forward_mm"])), 4),
            "gate_at_u50": round(float(law["aspect_gate"][i50]), 12),
            "warp_q": law["warp_q"],
            "fixed_round_hold_mm": float(shape["throat_round_hold_mm"]),
        },
        "forward": {
            "L_mm": float(shape["L_forward_mm"]),
            "width_h_mm": float(shape["width_h_active_mm"]),
            "height_v_mm": float(shape["height_v_active_mm"]),
            "mouth_w_mm": float(shape["width_h_active_mm"]),
            "mouth_h_mm": float(shape["height_v_active_mm"]),
            "area_throat_mm2": float(law["area_throat_mm2"]),
            "area_mouth_mm2": float(law["area_mouth_mm2"]),
            "area_ratio": float(law["area_ratio"]),
            "aspect_mouth": float(shape["width_h_active_mm"] / shape["height_v_active_mm"]),
            "p_mouth": float(shape["p_mouth"]),
            "m0": float(law["m0"]),
            "delta_log_area": float(law["delta_log_area"]),
            "area_mid_bias": float(shape["area_mid_bias"]),
        },
        "throat": {
            "r0_mm": driver["exit_radius_mm"],
            "exit_angle_deg": driver["exit_angle_deg"],
            "tangent_h_deg": round(float(np.degrees(np.arctan(slope_h[i0]))), 6),
            "tangent_v_deg": round(float(np.degrees(np.arctan(slope_v[i0]))), 6),
            "area_mm2": float(law["area_mm2"][i0]),
            "aspect": float(law["aspect"][i0]),
            "p": float(law["p"][i0]),
        },
        "mouth": {
            "tangent_h_deg": round(float(np.degrees(np.arctan(slope_h[i1]))), 6),
            "tangent_v_deg": round(float(np.degrees(np.arctan(slope_v[i1]))), 6),
            "area_mm2": float(law["area_mm2"][i1]),
            "aspect": float(law["aspect"][i1]),
            "p": float(law["p"][i1]),
        },
        "throat_smoothness": _throat_smoothness(shape, brief),
        "section_cuts_mm": section_cuts(
            gen, knobs, brief,
            tuple(s for s in DEFAULT_CUTS_MM if s <= float(shape["L_forward_mm"]))),
        "min_forward_radius_margin_mm": margin,
        "deferred_phase2": ["returned_lip_roll", "rim_setback", "x_crease",
                            "independent_area_late", "independent_aspect_mid_late",
                            "throat_blend_length_study"],
        "not_claimed": ["acoustic readiness", "Crowe CAD equivalence", "roll geometry",
                        "X-crease geometry", "full-system performance", "BO readiness"],
    }


def validate_search_config(gen, seed, bounds, brief) -> None:
    """Validate the seed and every bound endpoint; enforce the V2A four-variable contract."""
    shape = _shape(gen, seed)
    _check_shape_geometry(shape, brief)
    if set(bounds) != PARAM_KEYS:
        raise GeneratorError(
            f"V2A exposes exactly four search dimensions {sorted(PARAM_KEYS)}; "
            f"missing={sorted(PARAM_KEYS - set(bounds))}, "
            f"unknown={sorted(set(bounds) - PARAM_KEYS)}")
    for key in PARAM_KEYS:
        bound, value = bounds[key], float(seed[key])
        if not all(math.isfinite(float(v)) for v in (bound.lo, bound.hi, value)):
            raise GeneratorError(f"{key}: bounds and seed must be finite")
        if not float(bound.lo) <= value <= float(bound.hi):
            raise GeneratorError(f"{key}: seed {value} is outside [{bound.lo}, {bound.hi}]")
        if getattr(bound, "log", False):
            raise GeneratorError(f"{key}: linear physical bounds are required")
        if not getattr(bound, "search", True) and float(bound.lo) != float(bound.hi):
            raise GeneratorError(f"{key}: a fixed bound must have lo == hi")
        for endpoint in (bound.lo, bound.hi):
            _check_shape_geometry(_shape(gen, {**seed, key: float(endpoint)}), brief)


def _descriptors(gen, knobs, brief) -> np.ndarray:
    """Dimensionless/physical surface descriptors used by the T2 identifiability check."""
    shape = _shape(gen, knobs)
    length = float(shape["L_forward_mm"])
    u = np.array([0.5, 0.8])
    law = evaluate(shape, brief, u)
    dense = evaluate(shape, brief, np.linspace(0.0, 1.0, 501))
    slope_h, slope_v, kappa_h, _ = _slope_curvature(dense)
    z = dense["z_mm"]
    z5, z8 = 0.5 * length, 0.8 * length
    return np.array([
        law["area_mm2"][0],
        law["aspect"][0],
        law["p"][0],
        np.degrees(np.arctan(np.interp(z5, z, slope_h))),
        law["area_mm2"][1],
        law["aspect"][1],
        law["p"][1],
        np.degrees(np.arctan(np.interp(z8, z, slope_v))),
        float(np.interp(z5, z, kappa_h)) * length,
        float(shape["height_v_active_mm"]),
        float(law["area_mouth_mm2"]),
        float(shape["width_h_active_mm"] / shape["height_v_active_mm"]),
        float(shape["aspect_timing_u50"]) * length,
    ], dtype=float)


def identifiability_report(gen, knobs, bounds, brief, delta: float = 0.1) -> dict:
    """T2 law-level Jacobian: normalized +-delta box perturbations -> SVD rank and collinearity."""
    validate_search_config(gen, knobs, bounds, brief)
    base = _descriptors(gen, knobs, brief)
    labels = ["area_mid_mm2", "aspect_mid", "p_mid", "wall_h_mid", "area_late_mm2",
              "aspect_late", "p_late", "wall_v_late", "curvature_mid_xL", "mouth_h_mm",
              "mouth_area_mm2", "mouth_aspect", "timing_station_mm"]
    scale = np.maximum(np.abs(base), 1e-9)
    columns = {}
    for key in sorted(PARAM_KEYS):
        bound = bounds[key]
        step = float(delta) * (float(bound.hi) - float(bound.lo))
        if step <= 0.0:
            step = 1e-6
        plus = min(float(bound.hi), float(knobs[key]) + step)
        minus = max(float(bound.lo), float(knobs[key]) - step)
        if plus == minus:
            columns[key] = np.zeros_like(base)
            continue
        dp = (_descriptors(gen, {**knobs, key: plus}, brief)
              - _descriptors(gen, {**knobs, key: minus}, brief))
        # Normalized +-delta box Jacobian: relative descriptor change per unit normalized
        # coordinate. This keeps variables with different physical units comparable.
        columns[key] = dp / scale / (2.0 * float(delta))
    keys = sorted(columns)
    matrix = np.column_stack([columns[k] for k in keys])
    _, s, _ = np.linalg.svd(matrix, full_matrices=False)
    rank = int(np.sum(s > 1e-6 * max(float(s[0]), 1e-12)))
    practical = int(np.sum(s > 0.01 * max(float(s[0]), 1e-12)))
    norm = np.linalg.norm(matrix, axis=0)
    cosine = np.abs(matrix.T @ matrix) / np.maximum(np.outer(norm, norm), 1e-12)
    np.fill_diagonal(cosine, 0.0)
    weak = [k for k, n in zip(keys, norm) if n < 0.01 * max(float(norm.max()), 1e-12)]
    return {
        "keys": keys,
        "descriptors": labels,
        "singular_values": [float(v) for v in s],
        "effective_rank": rank,
        "practical_rank": practical,
        "weak_keys": weak,
        "max_pairwise_abs_cosine": float(np.max(cosine)),
        "column_norms": {k: float(v) for k, v in zip(keys, norm)},
    }
