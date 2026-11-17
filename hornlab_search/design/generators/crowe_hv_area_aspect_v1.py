"""CROWE-inspired H/V area+aspect waveguide family, forward flare only (schema v1).

This is the forward, no-return geometry described in
``docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md`` section 7. It is a
versioned typology generator: ``generator.name: crowe_hv_area_aspect_v1`` materialises ordinary
FREEFORM H/V meridians plus superellipse cross-section stations, so the existing mesher builds
every surface and the frozen Family contract is untouched.

Primary coordinates on the forward section, ``u = z / L`` in ``[0, 1]``:

* ``log A(u)`` -- cross-sectional area law. It is the unique quadratic through
  ``A(0) = pi r0^2`` and ``A(1) = C(p_mouth) (W/2) (H/2)`` whose initial slope equals the driver
  exit tangent ``da/dz(0) = db/dz(0) = tan(exit_angle)``. The normalized initial slope ``m0``
  must lie in ``[0, 2]``; a steeper driver/depth combination has no monotone member of this
  family and is refused rather than silently distorted.
* ``log R(u)`` -- aspect law ``R = a / b``. It is exactly 1 for the first ``round_throat_mm``
  (the owner's 15-40 mm near-throat rule), then develops through a C2 smootherstep with
  localized mid/late perturbations. Both wall tangents therefore start equal and the near-throat
  section is exactly circular, not merely close to it.
* ``p(u)`` -- superellipse exponent, exactly 2 for the first ``round_throat_mm`` (area expands
  before the section becomes boxy) and ``p_mouth`` at the mouth through the same C2 gate. No
  ridge/crease exists in v1; the X crease is Phase 2 and its onset is a separate 20-40% knob.

At every station the superellipse ``(|x|/a)^p + (|y|/b)^p = 1`` has enclosed area
``A = C(p) a b`` and aspect ``R = a / b``; the generator inverts those exactly:

    a = sqrt(A R / C(p)),    b = sqrt(A / (R C(p))),
    C(p) = 4 Gamma(1 + 1/p)^2 / Gamma(1 + 2/p).

The mid/late knobs are normalized log-area and log-aspect perturbations with C2 compact windows
that are exactly zero at both ends, so the requested mouth W/H and the source tangent are
preserved by construction. The realised surface is sampled and refused if either forward radius
is non-positive or non-monotone.

Not implemented here (Phase 2 in the research document; no knob is registered without an
implemented effect): returned lip/roll, rim setback, the X crease, ``p_progress_start/rate``,
the throat-length source-uncertainty study, and any objective/search default change.
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

#: Active Phase 1 coordinates (the research document's 7-9 rank-pruned dimensions).
PARAM_KEYS = frozenset({
    "L_forward_mm",
    "width_h_active_mm",
    "height_v_active_mm",
    "area_mid_rate",
    "area_late_rate",
    "aspect_mid",
    "aspect_late",
    "p_mouth",
    "round_throat_mm",
})

#: Fixed generator-block keys (not search dimensions). ``seed_policy`` is a config directive.
GEN_KEYS = frozenset({"name", "n_anchors", "wall_thickness_mm", "seed_policy"})
SHAPE_KEYS = PARAM_KEYS | (GEN_KEYS - {"name", "seed_policy"})

#: Normalized log perturbation amplitudes. The public knobs are rates in [-1, 1]; the physical
#: amplitude lives here so a knob's meaning cannot drift with a config edit.
AREA_MID_AMPLITUDE = 0.25
AREA_LATE_AMPLITUDE = 0.20
ASPECT_MID_AMPLITUDE = 0.20
ASPECT_LATE_AMPLITUDE = 0.18

#: Module-level physical limits. Search priors (narrower) live in the YAML configs.
_BOUNDS = {
    "p_mouth": (2.0, 5.0),
    "area_mid_rate": (-1.0, 1.0),
    "area_late_rate": (-1.0, 1.0),
    "aspect_mid": (-1.0, 1.0),
    "aspect_late": (-1.0, 1.0),
    "round_throat_mm": (10.0, 90.0),
    "wall_thickness_mm": (0.5, 12.0),
}

_N_ANCHORS_MIN = 9
_N_ANCHORS_MAX = 32          # also the mesher's crossSections maximum
_DENSE = 2049


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
    if float(shape["round_throat_mm"]) >= float(shape["L_forward_mm"]):
        raise GeneratorError("round_throat_mm must be shorter than L_forward_mm")
    n = shape["n_anchors"]
    if int(n) != n or not _N_ANCHORS_MIN <= int(n) <= _N_ANCHORS_MAX:
        raise GeneratorError(
            f"n_anchors must be an integer in [{_N_ANCHORS_MIN}, {_N_ANCHORS_MAX}], got {n!r}")


def _smootherstep(x):
    t = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    return t * t * t * (10.0 + t * (-15.0 + 6.0 * t))


def _windows(u):
    """C2 compact mid/late windows, exactly zero at both ends (peak normalized to 1)."""
    u = np.asarray(u, dtype=float)
    mid = (4.0 * u * (1.0 - u)) ** 4
    late = np.where((u > 0.0) & (u < 1.0),
                    (u / 0.8) ** 12 * ((1.0 - u) / 0.2) ** 3, 0.0)
    return mid, late


def evaluate(shape, brief, u) -> dict:
    """Evaluate the continuous law at ``u`` in [0, 1]; mm, mm^2, dimensionless.

    ``a_mm`` and ``b_mm`` are the H and V inner semi-axes. ``area_mm2`` is exactly
    ``C(p) a b`` by construction, and ``aspect`` is exactly ``R``.
    """
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
    mid, late = _windows(u)
    log_area = (math.log(area0) + delta * base
                + float(shape["area_mid_rate"]) * AREA_MID_AMPLITUDE * mid
                + float(shape["area_late_rate"]) * AREA_LATE_AMPLITUDE * late)
    # Owner rules 1-3: the section is exactly circular for round_throat_mm (a/b = 1, p = 2),
    # while the area law keeps expanding. Aspect and section-shape development share one C2 gate,
    # so tangent and curvature are continuous at the gate and at the mouth.
    u_round = float(shape["round_throat_mm"]) / length
    gate = _smootherstep((u - u_round) / (1.0 - u_round))
    log_aspect = (math.log(width / height)
                  + float(shape["aspect_mid"]) * ASPECT_MID_AMPLITUDE * mid
                  + float(shape["aspect_late"]) * ASPECT_LATE_AMPLITUDE * late) * gate
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
        "area_throat_mm2": area0,
        "area_mouth_mm2": area1,
        "area_ratio": area1 / area0,
        "m0": m0,
        "delta_log_area": delta,
    }


def _check_forward(law) -> None:
    for name, radii in (("H", law["a_mm"]), ("V", law["b_mm"])):
        if not np.isfinite(radii).all() or float(radii.min()) <= 0.0:
            raise GeneratorError(f"{name} forward radius must be finite and positive")
        if np.any(np.diff(radii) <= 0.0):
            raise GeneratorError(
                f"{name} forward radius is not strictly increasing; the area/aspect "
                "perturbations are too strong for this parent")


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
    """Generator block + knobs -> ordinary FREEFORM params (H/V meridians + stations)."""
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

    stations = [{"t": 0.0, "shape": "circle"}]
    u_round = float(shape["round_throat_mm"]) / length
    if u_round > 1e-9:
        # Explicit end of the exact round-throat zone. Nudge it off an anchor station: the
        # mesher refuses semantic axial features closer than 1e-7 in normalized t.
        t_round = u_round + (2e-6 if float(np.min(np.abs(u - u_round))) < 1e-6 else 0.0)
        stations.append({"t": round(float(t_round), 6), "shape": "superellipse",
                         "exponent": 2.0})
    # Interior stations sit halfway between meridian anchors, so no station coincides with an
    # anchor; their exponents sample the same C2 p(u) gate.
    for i in range(len(u) - 1):
        t_mid = 0.5 * (u[i] + u[i + 1])
        if t_mid <= u_round + 1e-9:
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


def _station(u, law, i, slope_h, slope_v):
    return {
        "u": round(float(u), 6),
        "z_mm": round(float(law["z_mm"][i]), 4),
        "a_mm": round(float(law["a_mm"][i]), 4),
        "b_mm": round(float(law["b_mm"][i]), 4),
        "area_mm2": round(float(law["area_mm2"][i]), 3),
        "aspect": round(float(law["aspect"][i]), 6),
        "p": round(float(law["p"][i]), 6),
        "wall_h_deg": round(float(np.degrees(np.arctan(slope_h[i]))), 4),
        "wall_v_deg": round(float(np.degrees(np.arctan(slope_v[i]))), 4),
    }


DEFAULT_CUTS_MM = (0.0, 5.0, 10.0, 20.0, 40.0, 80.0)


def section_cuts(gen, knobs, brief, stations_mm=DEFAULT_CUTS_MM) -> list[dict]:
    """Section cuts at physical z stations: area, aspect, roundness, tangent, curvature.

    The owner's review stations (0/5/10/20/40/80 mm) are the default. Curvature is the planar
    meridian curvature ``|r''| / (1 + r'^2)^(3/2)`` in 1/mm, evaluated on the dense law and
    interpolated. This is a geometry measurement, not a mesh or acoustic result.
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

    def slope(r):
        return np.gradient(r, z, edge_order=2)

    def curvature(r):
        rp = slope(r)
        rpp = np.gradient(rp, z, edge_order=2)
        return np.abs(rpp) / (1.0 + rp * rp) ** 1.5

    slope_h = slope(dense["a_mm"])
    slope_v = slope(dense["b_mm"])
    kappa_h = curvature(dense["a_mm"])
    kappa_v = curvature(dense["b_mm"])
    round_mm = float(shape["round_throat_mm"])
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
            "wall_h_deg": round(float(np.degrees(np.arctan(np.interp(z_mm, z, slope_h)))), 4),
            "wall_v_deg": round(float(np.degrees(np.arctan(np.interp(z_mm, z, slope_v)))), 4),
            "curvature_h_1_per_mm": round(float(np.interp(z_mm, z, kappa_h)), 8),
            "curvature_v_1_per_mm": round(float(np.interp(z_mm, z, kappa_v)), 8),
            "inside_round_throat": bool(z_mm <= round_mm + 1e-9),
        })
    return rows


def _roundness_summary(shape, brief) -> dict:
    length = float(shape["L_forward_mm"])
    round_mm = float(shape["round_throat_mm"])
    u = np.linspace(0.0, round_mm / length, 999)
    law = evaluate(shape, brief, u)
    return {
        "round_throat_mm": round_mm,
        "max_abs_aspect_minus_1": round(float(np.max(np.abs(law["aspect"] - 1.0))), 12),
        "max_abs_p_minus_2": round(float(np.max(np.abs(law["p"] - 2.0))), 12),
        "max_abs_a_minus_b_mm": round(float(np.max(np.abs(law["a_mm"] - law["b_mm"]))), 9),
        "area_ratio_at_round_throat": round(float(np.interp(round_mm, law["z_mm"],
                                                            law["area_mm2"]) / law["area_throat_mm2"]), 6),
    }


def info(gen, knobs, brief) -> dict:
    """JSON-safe report of the law, the realised anchors and the deferred Phase 2 items."""
    shape = _shape(gen, knobs)
    driver = _driver(brief)
    u = np.linspace(0.0, 1.0, _DENSE)
    law = evaluate(shape, brief, u)
    slope_h = np.gradient(law["a_mm"], law["z_mm"], edge_order=2)
    slope_v = np.gradient(law["b_mm"], law["z_mm"], edge_order=2)
    picks = [0.0, 0.25, 0.5, 0.75, 1.0]
    index = [int(np.argmin(np.abs(u - p))) for p in picks]
    margin = float(min(np.diff(law["a_mm"]).min(), np.diff(law["b_mm"]).min()))
    return {
        "kind": KIND,
        "schema": SCHEMA,
        "implementation_sha256": implementation_digest(),
        "construction_label": (
            SCHEMA + ": forward area/aspect superellipse; our construction, not Crowe CAD; "
            "no returned lip or X crease"),
        "source_tangent_is_assumption": True,
        "source_angle_deg_is_assumption": True,
        "driver": driver,
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
        },
        "throat": {
            "r0_mm": driver["exit_radius_mm"],
            "exit_angle_deg": driver["exit_angle_deg"],
            "tangent_h_deg": round(float(np.degrees(np.arctan(slope_h[0]))), 6),
            "tangent_v_deg": round(float(np.degrees(np.arctan(slope_v[0]))), 6),
            "area_mm2": float(law["area_mm2"][0]),
            "aspect": float(law["aspect"][0]),
            "p": float(law["p"][0]),
        },
        "mouth": {
            "tangent_h_deg": round(float(np.degrees(np.arctan(slope_h[-1]))), 6),
            "tangent_v_deg": round(float(np.degrees(np.arctan(slope_v[-1]))), 6),
            "area_mm2": float(law["area_mm2"][-1]),
            "aspect": float(law["aspect"][-1]),
            "p": float(law["p"][-1]),
        },
        "stations": [_station(u[i], law, i, slope_h, slope_v) for i in index],
        "perturbations": {
            "area_mid_rate": float(shape["area_mid_rate"]),
            "area_late_rate": float(shape["area_late_rate"]),
            "aspect_mid": float(shape["aspect_mid"]),
            "aspect_late": float(shape["aspect_late"]),
            "area_mid_amplitude": AREA_MID_AMPLITUDE,
            "area_late_amplitude": AREA_LATE_AMPLITUDE,
            "aspect_mid_amplitude": ASPECT_MID_AMPLITUDE,
            "aspect_late_amplitude": ASPECT_LATE_AMPLITUDE,
        },
        "n_anchors": int(shape["n_anchors"]),
        "round_throat_mm": float(shape["round_throat_mm"]),
        "roundness": _roundness_summary(shape, brief),
        "section_cuts_mm": section_cuts(
            gen, knobs, brief,
            tuple(s for s in DEFAULT_CUTS_MM if s <= float(shape["L_forward_mm"]))),
        "wall_thickness_mm": float(shape["wall_thickness_mm"]),
        "min_forward_radius_margin_mm": margin,
        "deferred_phase2": ["returned_lip_roll", "rim_setback", "x_crease",
                            "p_progress_start_rate", "throat_blend_length_study"],
        "not_claimed": ["acoustic readiness", "Crowe CAD equivalence", "roll geometry",
                        "X-crease geometry", "full-system performance"],
    }


def validate_search_config(gen, seed, bounds, brief) -> None:
    """Validate the seed and every bound endpoint before a search is allowed to start."""
    shape = _shape(gen, seed)
    _check_shape_geometry(shape, brief)
    if set(bounds) != PARAM_KEYS:
        raise GeneratorError(
            f"every {KIND} knob needs an explicit matching bound; "
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
