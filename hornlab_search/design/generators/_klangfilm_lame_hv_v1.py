"""Klangfilm-Lame H/V throat core (Phase A): independent H and V wall tangents on one round driver rim.

``rows.type: klangfilm_lame_hv_cd``, schema ``klangfilm-lame-hv-v1``. The legacy kernel
``klangfilm_lame.py`` (schema ``klangfilm-lame-v1``) is imported **read-only** as the parent; it is never
modified here. With ``cd_core_blend = 0`` (or every new deviation zero) this module returns the parent's
grid bit-for-bit.

Why this module exists
----------------------
The parent gates aspect ``q(s)`` and exponent ``p(s)`` with one quintic ``Q`` whose derivative at the
throat is zero (``Q'(0) = 0``). A zero initial derivative of ``ln q`` forces ``da/dz = db/dz`` at z = 0:
the mouth may be elongated, but the first H and V wall slopes are identical. A round driver rim does not
require an axisymmetric *downstream* wall tangent, so Phase A adds an explicit, two-axis entrance
deformation:

    B1(t) = t (1 - t)^3                    B1(0)=B1(1)=0, B1'(0)=1, B1'(1)=B1''(1)=0
    B2(t) = 64 t^3 (1 - t)^3               B2 peaks at 1.0 at t = 1/2, value/slopes 0 at both ends
    delta_i(z) = blend * [dm_i * L * B1(z/L) + gain_i * B2(z/L)],   t = z / L,  0 <= z <= L

with ``dm_i = tan(theta_i,0_target) - tan(theta_i,0_base)``. Consequences, all testable:

* ``delta_i(0) = 0`` and ``a(0) = b(0) = r0``: the modeled circle at the driver plane is unchanged.
* ``d(delta_i)/dz |_0 = blend * dm_i``: the first wall slope is exactly the requested target tangent,
  and H/V respond independently. Hence ``d ln q / dz |_0 = (tan th_H - tan th_V) / r0`` as required.
* ``delta_i`` and its first two derivatives vanish at ``z = L``: the untouched legacy horn is recovered
  C2 at the join (a curvature jump at the *throat* is inherent to a finite tangent change on a round rim;
  position and tangent stay continuous there).
* ``L`` is a fraction of the **monotonic forward span** only (the parent's axial turn is at ``h = R/4``),
  never a fraction of the rolled-back ``h`` coordinate. Rollback stations are left untouched, so the
  intrinsic Klangfilm return keeps its legacy shape for this controlled A/B.

Area semantics: the legacy curved-cap area lock (``superellipsoid_cap_v1`` over an unswept spherical
wavefront) is solved first, then the forward radii are deformed. The deformed shell therefore no longer
satisfies ``S(h) = 2 pi R h``; ``meta.area_mode`` says so (``deformed_after_cap_lock``) and the residual is
reported as a diagnostic, not silently re-labelled. This is Phase A of the 2026-11-16 handoff: a
controlled entrance/early-core experiment, **not** a claim of 80x50 constant directivity.

Throat provenance: the parent's raw wall half-angle is derived (9.3669 deg at fc 494.439 Hz, r0 18 mm).
``brief.driver.exit_angle_deg`` (2 deg) remains a simulation assumption; nothing here converts it into a
wall tangent or claims it is an HF1440 datasheet value.

Frozen copy: reproduced from ``tools/geometry/klangfilm_lame_hv.py`` (SHA256
cbb23cc02d9b5d135e1ec46b4d0f3fdac68f8120c313b1a8ffe8e360672bea02). It must stay in sync with that
reviewed source; regenerate rather than hand-edit.
"""
from __future__ import annotations

import math

import numpy as np

from . import _klangfilm_lame_v1 as parent
from . import _lame_cap_v1 as lame_cap

SCHEMA = "klangfilm-lame-hv-v1"
KIND = "klangfilm_lame_hv_cd"
PARENT_SCHEMA = parent.SCHEMA

#: New Phase A controls only. Termination (beak/lip) and the Phase B monotonic CD core are separate,
#: gated modules; no knob is registered here that has no implemented effect.
CORE_KEYS = frozenset({"cd_core_blend", "theta_h0_deg", "theta_v0_deg",
                       "h_mid_gain_mm", "v_mid_gain_mm", "core_join_fraction"})
SHAPE_KEYS = parent.SHAPE_KEYS | CORE_KEYS
GRID_KEYS = frozenset({"n_phi", "n_s", "wall_thickness_mm"})

#: Module-level physical limits. Search priors (narrower) live in the YAML configs, not here.
_CORE_BOUNDS = {"cd_core_blend": (0.0, 1.0), "theta_h0_deg": (0.0, 25.0), "theta_v0_deg": (0.0, 25.0),
                "h_mid_gain_mm": (-80.0, 80.0), "v_mid_gain_mm": (-80.0, 80.0),
                "core_join_fraction": (0.05, 0.95)}

#: Inert seed used by the family adapter / docs. ``theta_*`` seeds are replaced by the measured parent
#: tangent before any non-zero blend is requested (see ``defaults_for``).
CORE_DEFAULTS = {"cd_core_blend": 0.0, "theta_h0_deg": 0.0, "theta_v0_deg": 0.0,
                 "h_mid_gain_mm": 0.0, "v_mid_gain_mm": 0.0, "core_join_fraction": 0.65}

_MONO_TOL = 1e-9


def legacy_view(shape):
    """Parent shape dict (drops the Phase A keys) so the legacy validator stays authoritative."""
    return {k: shape[k] for k in parent.SHAPE_KEYS}


def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f"shape keys: missing={sorted(SHAPE_KEYS - set(shape))}, "
                         f"unknown={sorted(set(shape) - SHAPE_KEYS)}")
    parent.validate_shape(legacy_view(shape))
    for key, (lo, hi) in _CORE_BOUNDS.items():
        v = shape[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{key} must be a finite number")
        if not lo <= v <= hi:
            raise ValueError(f"{key} must be in [{lo}, {hi}]")


# ---------------------------------------------------------------- pure math kernel
def cd_hv_delta(z_mm, z_join_mm, theta_base_deg, theta_target_deg,
                mid_gain_mm=0.0, core_blend=1.0):
    """C2-at-the-join radial offset for ONE axis, only for ``0 <= z <= z_join``.

    Returns an array shaped like ``z_mm`` that is exactly 0 outside the join interval. Callers must pass
    the **forward branch only** (or keep rollback stations unmodified themselves): the parent's rollback
    revisits small z values, and a z-mask alone would deform it.
    """
    z = np.asarray(z_mm, dtype=float)
    if not math.isfinite(float(z_join_mm)) or z_join_mm <= 0.0:
        raise ValueError("z_join_mm must be finite and positive")
    if not 0.0 <= core_blend <= 1.0:
        raise ValueError("core_blend must be in [0, 1]")
    if not (math.isfinite(theta_base_deg) and math.isfinite(theta_target_deg)):
        raise ValueError("theta angles must be finite")
    t_raw = z / float(z_join_mm)
    t = np.clip(t_raw, 0.0, 1.0)
    dm = (math.tan(math.radians(float(theta_target_deg)))
          - math.tan(math.radians(float(theta_base_deg))))
    b1 = t * (1.0 - t) ** 3
    b2 = 64.0 * t ** 3 * (1.0 - t) ** 3
    delta = core_blend * (dm * float(z_join_mm) * b1 + float(mid_gain_mm) * b2)
    inside = (z >= 0.0) & (z <= float(z_join_mm))
    return np.where(inside, delta, 0.0)


def _chord_deg(z, r, i0=0, i1=1):
    dz = float(z[i1] - z[i0])
    if abs(dz) <= 0.0:
        raise ValueError("degenerate station spacing at the throat")
    return math.degrees(math.atan2(float(r[i1] - r[i0]), dz))


def forward_slice(tab):
    """Index ``slice(0, turn+1)`` of the monotonic forward branch (parent turn at ``h = R/4``)."""
    z = np.asarray(tab["z"], dtype=float)
    turn = int(np.argmax(z))
    if turn < 3:
        raise ValueError("parent table has no usable forward branch")
    if not np.all(np.diff(z[: turn + 1]) > _MONO_TOL * max(1.0, float(np.abs(z).max()))):
        raise ValueError("parent forward branch is not strictly monotonic in z")
    return turn


def _deform(tab, shape, y0_mm):
    """Apply the Phase A H/V deformation in place on the forward branch; return bookkeeping."""
    blend = float(shape["cd_core_blend"])
    z, a, b = np.asarray(tab["z"]), np.asarray(tab["a"]), np.asarray(tab["b"])
    turn = forward_slice(tab)
    z_turn = float(z[turn])
    z_join = float(shape["core_join_fraction"]) * z_turn
    if not 0.0 < z_join < z_turn:
        raise ValueError(f"core join {z_join:.3f} mm must lie strictly inside (0, {z_turn:.3f}) mm")
    base_h = _chord_deg(z, a, 0, 1)
    base_v = _chord_deg(z, b, 0, 1)
    dh = cd_hv_delta(z[: turn + 1], z_join, base_h, shape["theta_h0_deg"],
                     shape["h_mid_gain_mm"], blend)
    dv = cd_hv_delta(z[: turn + 1], z_join, base_v, shape["theta_v0_deg"],
                     shape["v_mid_gain_mm"], blend)
    a_new, b_new = a.copy(), b.copy()
    a_new[: turn + 1] += dh
    b_new[: turn + 1] += dv
    _check_forward(z[: turn + 1], a_new[: turn + 1], b_new[: turn + 1], y0_mm)
    info = {"core_blend": blend, "core_join_mm": z_join, "z_forward_mm": z_turn,
            "theta_base_h_deg": base_h, "theta_base_v_deg": base_v,
            "delta_h_max_mm": float(np.max(np.abs(dh))), "delta_v_max_mm": float(np.max(np.abs(dv))),
            "turn_index": turn, "rollback_stations": int(len(z) - turn - 1)}
    tab.update(z=z, a=a_new, b=b_new, q=a_new / np.maximum(b_new, 1e-12), hv=info)
    return info


def _check_forward(z, a, b, y0_mm):
    """Refuse silent clipping: positive, non-shrinking, monotone forward radii and a round throat."""
    for name, r in (("H", a), ("V", b)):
        if not np.isfinite(r).all():
            raise ValueError(f"{name} forward radius is not finite")
        if float(r.min()) <= 0.0:
            raise ValueError(f"{name} forward radius is non-positive")
        if abs(float(r[0]) - y0_mm) > 1e-9:
            raise ValueError(f"{name} throat radius {r[0]:.9f} mm != driver radius {y0_mm:.9f} mm")
        if float(r.min()) < y0_mm * (1.0 - 1e-9):
            raise ValueError(f"{name} forward radius shrinks below the throat radius")
        if np.any(np.diff(r) < -_MONO_TOL * max(1.0, float(np.abs(r).max()))):
            raise ValueError(f"{name} forward radius is not non-decreasing")


def profile(shape, y0_mm):
    """Dense station table. ``cd_core_blend == 0`` returns the parent's table unchanged."""
    validate_shape(shape)
    tab = parent.profile(legacy_view(shape), y0_mm)
    if float(shape["cd_core_blend"]) == 0.0:
        tab["hv"] = {"core_blend": 0.0, "core_join_mm": None, "z_forward_mm": None,
                     "theta_base_h_deg": _chord_deg(tab["z"], tab["a"], 0, 1),
                     "theta_base_v_deg": _chord_deg(tab["z"], tab["b"], 0, 1),
                     "delta_h_max_mm": 0.0, "delta_v_max_mm": 0.0, "legacy": True}
        return tab
    _deform(tab, shape, y0_mm)
    tab["hv"]["legacy"] = False
    return tab


# ---------------------------------------------------------------- geometry
def make_grid(shape, brief):
    """Quarter model (n_phi, n_s + 1, 3), identical to the parent at zero blend."""
    validate_shape(shape)
    y0 = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    tab = profile(shape, y0)
    rm = 0.5 * (tab["a"] + tab["b"])
    arc = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(tab["z"]), np.diff(rm)))))
    n = int(shape["n_s"]) + 1
    t = np.linspace(0.0, arc[-1], n)
    z = np.interp(t, arc, tab["z"])
    a = np.interp(t, arc, tab["a"])
    b = np.interp(t, arc, tab["b"])
    p = np.interp(t, arc, tab["p"])
    phis = np.linspace(0.0, math.pi / 2.0, int(shape["n_phi"]))
    s_ap_t = float(np.interp(tab["s_ap"], arc, arc))
    W = lame_cap.quintic(t / max(s_ap_t, 1e-9))
    D_edge = float(shape["rim_sweep_ratio"]) * float(a.max())
    pts = np.zeros((len(phis), n, 3))
    for j in range(n):
        rho, _ = lame_cap.radial_lame(phis, max(a[j], 1e-9), max(b[j], 1e-9), max(p[j], 2.0))
        pts[:, j, 0] = rho * np.cos(phis)
        pts[:, j, 1] = rho * np.sin(phis)
        pts[:, j, 2] = z[j] - D_edge * np.cos(phis) ** 2 * W[j]
    pts[0, :, 1] = 0.0
    pts[-1, :, 0] = 0.0
    hv = dict(tab["hv"])
    meta = {"quarter": True, "row_span": "quarter", "symmetry_plane": "yz+xz",
            "source_auto_angle_deg": a0, "angle_provenance": "assumed_legacy",
            "construction_label": SCHEMA + ": parent klangfilm-lame-v1 forward core + independent H/V "
                                  "entrance slopes (Phase A; no beak, no Phase B CD core)",
            "area_mode": "curved_cap_ratio_locked" if hv["core_blend"] == 0.0 else "deformed_after_cap_lock",
            "lame_tail_mode": "hold_after_shoulder", "r0_mm": tab["R"],
            "cap_area_resid_max": float(tab["cap_area_resid"].max()),
            "core_mode": "legacy" if hv["core_blend"] == 0.0 else "hv_throat_phase_a",
            "core_join_fraction": float(shape["core_join_fraction"]),
            "core_info": hv, "shape": dict(shape)}
    return pts, meta


# ---------------------------------------------------------------- diagnostics
def _semi_axes_at(tab, z_mm):
    turn = forward_slice(tab)
    zf = tab["z"][: turn + 1]
    if not 0.0 <= z_mm <= float(zf[-1]):
        raise ValueError("station outside the monotonic forward branch")
    return (float(np.interp(z_mm, zf, tab["a"][: turn + 1])),
            float(np.interp(z_mm, zf, tab["b"][: turn + 1])),
            float(np.interp(z_mm, zf, tab["p"][: turn + 1])))


def _slope_deg_at(tab, z_mm, axis):
    turn = forward_slice(tab)
    zf = tab["z"][: turn + 1]
    r = (tab["a"] if axis == "h" else tab["b"])[: turn + 1]
    dr = np.gradient(r, zf, edge_order=2)
    return math.degrees(math.atan(float(np.interp(z_mm, zf, dr))))


def _mesh_chord_deg(pts, index, comp):
    """One-sided wall angle of the materialised meridian over its first arc station."""
    return math.degrees(math.atan2(float(pts[index, 1, comp] - pts[index, 0, comp]),
                                   float(pts[index, 1, 2] - pts[index, 0, 2])))


def _model_throat_deg(shape, tab, axis):
    """Analytic one-sided throat tangent: base chord plus the exactly injective B1 derivative."""
    hv = tab["hv"]
    base = hv["theta_base_h_deg"] if axis == "h" else hv["theta_base_v_deg"]
    if hv["core_blend"] == 0.0:
        return base
    target = float(shape["theta_h0_deg"] if axis == "h" else shape["theta_v0_deg"])
    slope = (math.tan(math.radians(base))
             + hv["core_blend"] * (math.tan(math.radians(target)) - math.tan(math.radians(base))))
    return math.degrees(math.atan(slope))


def diagnostics(shape, brief):
    """Measured throat/tangent/shape checks of the materialised grid. Never asserts a driver angle."""
    pts, meta = make_grid(shape, brief)
    y0 = float(brief["driver"]["exit_radius_mm"])
    tab = profile(shape, y0)
    turn = forward_slice(tab)
    zf = tab["z"][: turn + 1]
    ring = np.hypot(pts[:, 0, 0], pts[:, 0, 1])
    dz = np.diff(tab["z"])
    turns = int(np.count_nonzero(np.sign(dz[1:]) != np.sign(dz[:-1])))
    z_samples = [s for s in (0.5, 1.0, 5.0, 10.0, 15.0, 20.0) if s <= float(zf[-1])]
    stations = {f"{s:g}": {"a_mm": _semi_axes_at(tab, s)[0], "b_mm": _semi_axes_at(tab, s)[1]}
                for s in z_samples}
    q_ref = lambda z: (lambda ab: ab[0] / ab[1])(_semi_axes_at(tab, z))
    p_rel = {r: _semi_axes_at(tab, r * float(zf[-1]))[2] for r in (0.0, 0.2, 0.5, 0.8)}
    out = {
        "schema": SCHEMA, "core_mode": meta["core_mode"], "area_mode": meta["area_mode"],
        "raw_parent_halfangle_deg": parent.parent_wall_halfangle_deg(float(shape["fc_hz"]), y0),
        "theta_base_h_deg": tab["hv"]["theta_base_h_deg"], "theta_base_v_deg": tab["hv"]["theta_base_v_deg"],
        # analytic one-sided tangent (exact by construction), dense-table chord, and final-mesh chord
        "theta_model_h_deg": _model_throat_deg(shape, tab, "h"),
        "theta_model_v_deg": _model_throat_deg(shape, tab, "v"),
        "wall_halfangle_h_deg": _chord_deg(tab["z"], tab["a"], 0, 1),
        "wall_halfangle_v_deg": _chord_deg(tab["z"], tab["b"], 0, 1),
        "mesh_halfangle_h_deg": _mesh_chord_deg(pts, 0, 0),
        "mesh_halfangle_v_deg": _mesh_chord_deg(pts, -1, 1),
        "wall_halfangle_h_target_deg": float(shape["theta_h0_deg"])
        if meta["core_mode"] != "legacy" else None,
        "wall_halfangle_v_target_deg": float(shape["theta_v0_deg"])
        if meta["core_mode"] != "legacy" else None,
        "slope_h_deg_by_z": {f"{s:g}": _slope_deg_at(tab, s, "h") for s in z_samples},
        "slope_v_deg_by_z": {f"{s:g}": _slope_deg_at(tab, s, "v") for s in z_samples},
        "semi_axes_by_z": stations,
        "q_at_0": q_ref(0.0), "q_at_5mm": q_ref(5.0) if 5.0 <= float(zf[-1]) else None,
        "q_at_15mm": q_ref(15.0) if 15.0 <= float(zf[-1]) else None,
        "lame_p_by_forward_fraction": p_rel, "lame_p_at_throat": p_rel[0.0],
        "z_forward_mm": float(zf[-1]), "core_join_mm": tab["hv"]["core_join_mm"],
        "axial_turns_whole_profile": turns,
        "forward_z_strictly_increasing": bool(np.all(dz[:turn] > 0)),
        "throat_radius_mm": float(ring.mean()), "throat_radius_spread_mm": float(np.ptp(ring)),
        "min_radius_ratio_to_throat": float(np.hypot(pts[:, :, 0], pts[:, :, 1]).min(axis=0)[1:].min() / y0),
        "delta_h_max_mm": tab["hv"]["delta_h_max_mm"], "delta_v_max_mm": tab["hv"]["delta_v_max_mm"],
        "cap_area_resid_max": meta["cap_area_resid_max"],
        "max_width_mm": float(2 * np.abs(pts[:, :, 0]).max()),
        "max_height_mm": float(2 * np.abs(pts[:, :, 1]).max()),
        "depth_mm": float(np.ptp(pts[:, :, 2])),
        "finite": bool(np.isfinite(pts).all()),
        "source_angle_is_assumption": True,
        "exit_angle_deg_is_assumption": True,
    }
    return out
