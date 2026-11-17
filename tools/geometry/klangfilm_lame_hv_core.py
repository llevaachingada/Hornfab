"""Phase B Klangfilm-Lame H/V core: monotone integrated-slope flare, derived axial turn, swept beak.

Schema ``klangfilm-lame-hv-core-v1``, ``rows.type: klangfilm_lame_hv_core``. The legacy kernels are
imported read-only; ``cd_core_blend = 0`` returns the v1 grid bit-for-bit (the same nesting contract as
Phase A).

Why a new core
--------------
Phase A offsets the parent radii on the forward branch. The 2026-11-17 Stage A A/B measured that this
has almost no acoustic authority (largest intended-axis mean -6 dB beamwidth change 2.74 deg, a
narrowing; both scoring policies got worse). The pattern is set by the mouth and the rollback, not by
the entrance tangent, and no additive offset can change the flare law itself.

This module builds the wall from an explicit **slope law in z**:

    theta_i(z) = theta_i0 + (theta_i1 - theta_i0) * Q(z / L_core)         i in {H, V}
    r_i(z)     = r0 + integral_0^z tan(theta_i(u)) du
    P(z, phi)  = (rho cos phi, rho sin phi, z + dz_beak(z, phi))

with ``Q`` the shared C2 quintic gate and ``rho`` the Lame radius for semi-axes ``a(z)=r_H``,
``b(z)=r_V`` and exponent ``p(z)``. Consequences:

* both axes share one z, so every station is a real planar Lame section;
* the flare is monotone by construction (``tan theta > 0``), and the axial turn is *derived* from the
  slope law rather than hand-placed;
* H and V are fully independent at every station, which is what the parent cannot do;
* ``p(z)`` starts at 2 and follows its own late gate, so **mouth sculpting is independent of the
  acoustic flare** (changing p moves only the diagonal/corner radius, never the H/V meridians);
* the optional **beak** adds axial offsets only after ``beak_start_fraction``:
  ``dz = eta(u) * [-D_H cos^2(phi) + D_V sin^2(phi) + D_D sin^2(2 phi)]`` with ``eta`` a C2 gate, so
  H lip setback, V lip projection and diagonal scoop are independent and cannot touch the throat or
  the core. All three zero is an exact no-op.

Scope / honesty
---------------
* This is the **monotone core plus a swept beak**, not a full returning lip. A true arc-length roll
  needs a section-normal (spine) parameterisation so one station still has one plane; that is a
  separate module. Nothing here hides a turn inside the core: the core stays monotone and the axial
  extent is the core length plus the beak offsets.
* An independent-slope core does not satisfy Ahlswede's spherical curved-cap area law. The exact
  Gamma flat-area formula is reported per station and ``meta.wavefront_model =
  'independent_hv_core'``; the legacy curved-cap lock stays with v1.
* The driver source cap is not modelled here. A biaxial source ring or a common-tangent landing is a
  separate control and is not implemented.
"""
from __future__ import annotations

import math

import numpy as np

from tools.geometry import klangfilm_lame as parent
from tools.geometry import lame_cap

SCHEMA = "klangfilm-lame-hv-core-v1"
KIND = "klangfilm_lame_hv_core"

CORE_KEYS = frozenset({
    "cd_core_blend",
    "theta_h0_deg", "theta_v0_deg", "theta_h1_deg", "theta_v1_deg",
    "core_length_mm",
    "lame_p_mouth", "lame_start_frac", "lame_end_frac",
    "beak_h_setback_mm", "beak_v_projection_mm", "beak_diagonal_mm", "beak_start_frac",
})
SHAPE_KEYS = parent.SHAPE_KEYS | CORE_KEYS
GRID_KEYS = frozenset({"n_phi", "n_s", "wall_thickness_mm"})
_N = 1201
_CLEARANCE_MM = 2.0

_CORE_BOUNDS = {
    "cd_core_blend": (0.0, 1.0),
    "theta_h0_deg": (0.0, 25.0), "theta_v0_deg": (0.0, 25.0),
    "theta_h1_deg": (5.0, 60.0), "theta_v1_deg": (5.0, 60.0),
    "core_length_mm": (30.0, 480.0),
    "lame_p_mouth": (2.0, 8.0), "lame_start_frac": (0.0, 1.0), "lame_end_frac": (0.0, 1.0),
    "beak_h_setback_mm": (0.0, 60.0), "beak_v_projection_mm": (0.0, 45.0),
    "beak_diagonal_mm": (-20.0, 20.0), "beak_start_frac": (0.50, 0.99),
}

CORE_DEFAULTS = {
    "cd_core_blend": 0.0,
    "theta_h0_deg": 8.0, "theta_v0_deg": 5.0, "theta_h1_deg": 30.0, "theta_v1_deg": 20.0,
    "core_length_mm": 190.0, "lame_p_mouth": 4.0, "lame_start_frac": 0.25,
    "lame_end_frac": 0.90, "beak_h_setback_mm": 0.0, "beak_v_projection_mm": 0.0,
    "beak_diagonal_mm": 0.0, "beak_start_frac": 0.85,
}


def legacy_view(shape):
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
    if not float(shape["lame_start_frac"]) < float(shape["lame_end_frac"]):
        raise ValueError("lame_start_frac must be below lame_end_frac")
    for key in ("theta_h0_deg", "theta_v0_deg", "theta_h1_deg", "theta_v1_deg"):
        if float(shape[key]) >= 89.0:
            raise ValueError(f"{key} must stay below 89 deg (the core is monotone in z)")


def _cumtrapz(y, x):
    out = np.zeros_like(y)
    out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return out


def _meridian(r0_mm, theta0_deg, theta1_deg, core_mm):
    """r(z) = r0 + integral tan(theta) dz on a shared z grid."""
    z = np.linspace(0.0, float(core_mm), _N)
    t0, t1 = math.radians(float(theta0_deg)), math.radians(float(theta1_deg))
    th = t0 + (t1 - t0) * lame_cap.quintic(z / float(core_mm))
    return z, float(r0_mm) + _cumtrapz(np.tan(th), z), th


def core_table(shape, y0_mm):
    """Dense table on a shared z: z, a, b, theta_h, theta_v, p."""
    if float(shape["cd_core_blend"]) == 0.0:
        raise ValueError("core_table is only defined for the enabled core")
    core = float(shape["core_length_mm"])
    z, r_h, th_h = _meridian(y0_mm, shape["theta_h0_deg"], shape["theta_h1_deg"], core)
    z_v, r_v, th_v = _meridian(y0_mm, shape["theta_v0_deg"], shape["theta_v1_deg"], core)
    if not np.array_equal(z, z_v):
        raise ValueError("H/V meridians must share one z grid")
    return {"z": z, "a": r_h, "b": r_v, "theta_h": th_h, "theta_v": th_v,
            "p": _lame_p(z, core, shape), "core_mm": core}


def _lame_p(z, core_mm, shape):
    u = np.clip(np.asarray(z) / float(core_mm), 0.0, 1.0)
    a, b = float(shape["lame_start_frac"]), float(shape["lame_end_frac"])
    g = lame_cap.quintic((u - a) / max(b - a, 1e-9))
    g = np.where((u >= a) & (u <= b), g, np.where(u > b, 1.0, 0.0))
    return 2.0 + (float(shape["lame_p_mouth"]) - 2.0) * g


def _beak_offsets(z, core_mm, shape, phis):
    """(n_phi, n_stations) axial offsets; exactly zero before beak_start_fraction."""
    dh = float(shape["beak_h_setback_mm"])
    dv = float(shape["beak_v_projection_mm"])
    dd = float(shape["beak_diagonal_mm"])
    if dh == 0.0 and dv == 0.0 and dd == 0.0:
        return np.zeros((len(phis), len(z)))
    u = np.clip(np.asarray(z) / float(core_mm), 0.0, 1.0)
    u0 = float(shape["beak_start_frac"])
    gate = lame_cap.quintic((u - u0) / max(1.0 - u0, 1e-9))
    gate = np.where(u >= u0, gate, 0.0)
    fn = -dh * np.cos(phis) ** 2 + dv * np.sin(phis) ** 2 + dd * np.sin(2.0 * phis) ** 2
    return np.outer(fn, gate)


def make_grid(shape, brief):
    """Quarter grid. ``cd_core_blend = 0`` delegates to the v1 parent (bit-identical)."""
    validate_shape(shape)
    if float(shape["cd_core_blend"]) == 0.0:
        pts, meta = parent.make_grid(legacy_view(shape), brief)
        meta = dict(meta)
        meta.update(schema=SCHEMA, core_mode="legacy",
                    construction_label=SCHEMA + ": blend 0 -> v1 parent (bit-identical)",
                    wavefront_model="legacy_curved_cap")
        return pts, meta
    y0 = float(brief["driver"]["exit_radius_mm"])
    tab = core_table(shape, y0)
    n = int(shape["n_s"]) + 1
    z = np.linspace(0.0, tab["core_mm"], n)
    a = np.interp(z, tab["z"], tab["a"])
    b = np.interp(z, tab["z"], tab["b"])
    p = np.interp(z, tab["z"], tab["p"])
    phis = np.linspace(0.0, math.pi / 2.0, int(shape["n_phi"]))
    dz = _beak_offsets(z, tab["core_mm"], shape, phis)
    pts = np.zeros((len(phis), n, 3))
    for j in range(n):
        rho, _ = lame_cap.radial_lame(phis, max(a[j], 1e-9), max(b[j], 1e-9), max(p[j], 2.0))
        pts[:, j, 0] = rho * np.cos(phis)
        pts[:, j, 1] = rho * np.sin(phis)
        pts[:, j, 2] = z[j] + dz[:, j]
    pts[0, :, 1] = 0.0
    pts[-1, :, 0] = 0.0
    clearance = _check_geometry(pts, tab)
    meta = {"quarter": True, "row_span": "quarter", "symmetry_plane": "yz+xz",
            "source_auto_angle_deg": float(brief["driver"]["exit_angle_deg"]),
            "angle_provenance": "assumed_legacy",
            "construction_label": SCHEMA + ": z-parameterised H/V slope core, independent Lamé "
                                  "exponent, swept beak (no returning lip; not a curved-cap area lock)",
            "schema": SCHEMA, "core_mode": "hv_core", "wavefront_model": "independent_hv_core",
            "area_mode": "flat_lame_area_reported", "min_lip_clearance_mm": clearance,
            "theta_h0_deg": float(shape["theta_h0_deg"]), "theta_v0_deg": float(shape["theta_v0_deg"]),
            "theta_h1_deg": float(shape["theta_h1_deg"]), "theta_v1_deg": float(shape["theta_v1_deg"]),
            "core_length_mm": float(shape["core_length_mm"]),
            "lame_p_mouth": float(shape["lame_p_mouth"]),
            "beak": {k: float(shape[k]) for k in ("beak_h_setback_mm", "beak_v_projection_mm",
                                                  "beak_diagonal_mm", "beak_start_frac")},
            "shape": dict(shape)}
    return pts, meta


def _lip_clearance(pts):
    """Minimum distance between the last station and the stations before the last three."""
    lip = pts[:, -1, :]
    body = pts[:, :-3, :].reshape(-1, 3)
    if body.size == 0:
        return float("inf")
    return float(np.linalg.norm(lip[:, None, :] - body[None, :, :], axis=-1).min())


def _meridian_turns(z_values):
    d = np.diff(np.asarray(z_values, float))
    return int(np.count_nonzero(np.sign(d[1:]) != np.sign(d[:-1])))


def _check_geometry(pts, tab):
    if not np.isfinite(pts).all():
        raise ValueError("non-finite grid")
    if np.any(np.diff(tab["a"]) < -1e-9) or np.any(np.diff(tab["b"]) < -1e-9):
        raise ValueError("core radius is not non-decreasing")
    if float(tab["a"].min()) < float(tab["a"][0]) - 1e-9:
        raise ValueError("H radius shrinks below the throat")
    if float(tab["b"].min()) < float(tab["b"][0]) - 1e-9:
        raise ValueError("V radius shrinks below the throat")
    for idx, name in ((0, "H"), (-1, "V")):
        # one reversal is the intended setback; a second is the lip re-approaching. More than two is a fold.
        if _meridian_turns(pts[idx, :, 2]) > 2:
            raise ValueError(f"{name} meridian reverses axially more than twice (beak too aggressive)")
    core_step = float(tab["core_mm"]) / max(len(tab["z"]) - 1, 1)
    if float(np.min(np.diff(pts[0, :, 2]))) < -core_step:
        raise ValueError("beak setback folds the lip back faster than the core advances "
                         "(reduce beak_h_setback_mm or move beak_start_fraction later)")
    clearance = _lip_clearance(pts)
    if clearance < _CLEARANCE_MM:
        raise ValueError(f"lip returns into the horn: min clearance {clearance:.2f} mm "
                         f"< {_CLEARANCE_MM} mm")
    return clearance


def diagnostics(shape, brief):
    pts, meta = make_grid(shape, brief)
    if meta["core_mode"] == "legacy":
        base = parent.diagnostics(legacy_view(shape), brief)
        base.update(schema=SCHEMA, core_mode="legacy")
        return base
    tab = core_table(shape, float(brief["driver"]["exit_radius_mm"]))
    z = np.asarray(tab["z"])
    def at(frac):
        i = int(np.argmin(np.abs(z - frac * tab["core_mm"])))
        a, b, p = float(tab["a"][i]), float(tab["b"][i]), max(float(tab["p"][i]), 2.0)
        return {"a_mm": a, "b_mm": b, "p": p, "area_mm2": lame_cap.flat_lame_area(a, b, p)}
    return {
        "schema": SCHEMA, "core_mode": "hv_core", "wavefront_model": meta["wavefront_model"],
        "theta_h0_deg": float(shape["theta_h0_deg"]), "theta_v0_deg": float(shape["theta_v0_deg"]),
        "theta_h1_deg": float(shape["theta_h1_deg"]), "theta_v1_deg": float(shape["theta_v1_deg"]),
        "core_length_mm": float(shape["core_length_mm"]),
        "z_forward_mm": float(tab["core_mm"]),
        "throat_section": at(0.0), "mid_core_section": at(0.5), "mouth_section": at(1.0),
        "theta_h_at_mouth_deg": math.degrees(float(tab["theta_h"][-1])),
        "theta_v_at_mouth_deg": math.degrees(float(tab["theta_v"][-1])),
        "lame_p_at_mouth": float(tab["p"][-1]),
        "max_width_mm": float(2 * np.abs(pts[:, :, 0]).max()),
        "max_height_mm": float(2 * np.abs(pts[:, :, 1]).max()),
        "depth_mm": float(np.ptp(pts[:, :, 2])),
        "h_meridian_turns": _meridian_turns(pts[0, :, 2]),
        "v_meridian_turns": _meridian_turns(pts[-1, :, 2]),
        "min_lip_clearance_mm": _lip_clearance(pts),
        "beak_offsets_mm": meta["beak"],
        "finite": bool(np.isfinite(pts).all()),
        "source_angle_is_assumption": True,
    }


# ------------------------------------------------------------------ seeds for the report/preflight
LEGACY_GENES = dict(fc_hz=494.4393461867, aspect=2.0759495982, lame_p=5.0063549541,
                    end_frac=1.7953432921, rim_sweep_ratio=0.004898754, morph_frac=0.3,
                    source_blend_ratio=0.0, entry_half_angle_deg=2.0,
                    wall_thickness_mm=3.0, n_phi=19, n_s=64)
SEEDS = {
    # b1 balanced: L 380, mouth ~ 521 x 262 mm (A0's mouth is 541 x 261), 48 / 24.5 deg end slopes
    "b1": dict(cd_core_blend=1.0, theta_h0_deg=8.0, theta_v0_deg=5.0, theta_h1_deg=48.0,
               theta_v1_deg=24.5, core_length_mm=380.0, lame_p_mouth=4.0,
               lame_start_frac=0.25, lame_end_frac=0.90, beak_h_setback_mm=15.0,
               beak_v_projection_mm=0.0, beak_diagonal_mm=0.0, beak_start_frac=0.85),
    # b2 wide: L 420, mouth ~ 561 x 244 mm, stronger H taper and a wider Lamé mouth
    "b2": dict(cd_core_blend=1.0, theta_h0_deg=12.0, theta_v0_deg=4.0, theta_h1_deg=50.5,
               theta_v1_deg=22.0, core_length_mm=420.0, lame_p_mouth=4.8,
               lame_start_frac=0.30, lame_end_frac=0.92, beak_h_setback_mm=25.0,
               beak_v_projection_mm=0.0, beak_diagonal_mm=0.0, beak_start_frac=0.88),
    # b3 soft: L 340, mouth ~ 498 x 258 mm, gentler end slopes and a rounder lip
    "b3": dict(cd_core_blend=1.0, theta_h0_deg=7.0, theta_v0_deg=6.0, theta_h1_deg=52.1,
               theta_v1_deg=30.4, core_length_mm=340.0, lame_p_mouth=3.0,
               lame_start_frac=0.20, lame_end_frac=0.95, beak_h_setback_mm=10.0,
               beak_v_projection_mm=5.0, beak_diagonal_mm=0.0, beak_start_frac=0.90),
}


def seed_shape(name):
    if name not in SEEDS:
        raise KeyError(name)
    return dict(LEGACY_GENES, **SEEDS[name])
