"""Record-space structural edits and the point-grid hand-off (stage 4 WP 4.1, senior plan
2026-11-17, decision SD-2).

New shape freedoms are TESTED before anyone builds them into a generator: the U3 freedoms
(vertical flare timing, termination split, section steering, diagonal pull) are applied here as
in-plane radial displacement fields on a canonical record (contract §10), checked with the U2
validity rules, and handed to the existing point-grid mesh route (``mesh/grid_build.py``).

* An edit is ``delta(u, phi) -> mm`` with ``u`` the normalised wall position (0 throat, 1 lip)
  and ``phi`` the azimuth fraction of the quarter (0 = H wall, 1 = V wall); points move along
  their own in-plane radial direction, z is unchanged, the throat ring (u = 0) never moves.
* The unedited record through :func:`record_to_grid` is the CONTROL: WP 4.2 must show that
  route reproduces the stored response before any variant is read.

No solve, no stored row, no identity is touched here.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np

from .record import SurfaceRecord, descriptors

LIP_FRACTION = 0.15             # U2 validity: "before the lip" = the first 85 % of the wall


def _grid_uv(rec: SurfaceRecord):
    u = np.linspace(0.0, 1.0, rec.n_s)[None, :]
    phi = np.linspace(0.0, 1.0, rec.n_phi)[:, None]
    return u, phi


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def apply_radial_edit(rec: SurfaceRecord, delta, *, name: str) -> SurfaceRecord:
    """``delta(u, phi)`` (broadcast to ``(n_phi, n_s)``, mm, + = outward) applied along each
    point's in-plane radial direction. The throat station is pinned."""
    u, phi = _grid_uv(rec)
    d = np.broadcast_to(np.asarray(delta(u, phi), dtype=float), (rec.n_phi, rec.n_s)).copy()
    d[:, 0] = 0.0
    xy = rec.inner[:, :, :2]
    r = np.linalg.norm(xy, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = np.where(r[..., None] > 1e-9, xy / r[..., None], 0.0)
    new = rec.inner.copy()
    new[:, :, :2] = xy + unit * d[..., None]
    meta = {**rec.meta, "edit": name, "parent_digest": rec.digest()}
    return dataclasses.replace(rec, inner=new, meta=meta)


# ------------------------------------------------------------------ the U3 freedoms

def vertical_timing(rec: SurfaceRecord, *, mouth_height_mm: float, hold: float = 0.6,
                    strength: float = 0.5) -> SurfaceRecord:
    """U3 (a): hold the vertical wall back for the first ``hold`` of the wall (radial growth
    reduced by ``strength``), then open so the V-wall mouth reaches ``mouth_height_mm`` total,
    at unchanged depth. Weight sin^2 of azimuth (V wall = 1, H wall = 0)."""
    r = np.linalg.norm(rec.inner[:, :, :2], axis=-1)
    r_v_end = float(r[-1, -1])
    growth = r - r[:, :1]

    def delta(u, phi):
        w = np.sin(0.5 * math.pi * phi) ** 2
        s = smoothstep((u - hold) / (1.0 - hold))
        return w * (-strength * growth * (1.0 - s) + (0.5 * mouth_height_mm - r_v_end) * s)
    return apply_radial_edit(rec, delta, name=f"vertical_timing(h={mouth_height_mm},k={strength})")


def vertical_beak(rec: SurfaceRecord, *, projection_mm: float, start: float = 0.7) -> SurfaceRecord:
    """V-lip beak (2026-11-19): axial offset ``dz = +D sin^2(phi) Q((u - start)/(1 - start))`` after
    ``start`` of the wall (Q = C2 quintic gate), so the top/bottom lips project forward while the side
    walls stay put. Same construction as the Klangfilm Phase B ``beak_v_projection_mm``
    (``design/generators/_klangfilm_lame_hv_core_v1.py``), here as a record edit so it applies to any
    host, including rolled lips. D = 0 is an exact no-op. [original-hypothesis] acoustic role."""
    u, phi = _grid_uv(rec)
    w = np.sin(0.5 * math.pi * phi) ** 2
    x = np.clip((u - start) / max(1.0 - start, 1e-9), 0.0, 1.0)
    gate = np.where(u >= start, x ** 3 * (10.0 - 15.0 * x + 6.0 * x ** 2), 0.0)
    dz = float(projection_mm) * w * gate
    new = rec.inner.copy()
    new[:, :, 2] = new[:, :, 2] + dz
    meta = {**rec.meta, "edit": f"vertical_beak(D={projection_mm},start={start})",
            "parent_digest": rec.digest()}
    return dataclasses.replace(rec, inner=new, meta=meta)


def lip_clearance_mm(rec: SurfaceRecord) -> float:
    """Minimum distance from the last (lip) station to the wall stations before the last three:
    a rolled lip that curls into its own body gets a small value (the Phase B kernel's check)."""
    lip = rec.inner[:, -1, :]
    body = rec.inner[:, :-3, :].reshape(-1, 3)
    if body.size == 0:
        return float("inf")
    return float(np.linalg.norm(lip[:, None, :] - body[None, :, :], axis=-1).min())


def termination_split(rec: SurfaceRecord, *, side: str, extra_mm: float = 15.0) -> SurfaceRecord:
    """U3 (b): extra outward flare in the last ``LIP_FRACTION`` of the wall on the sides
    (``side='h'``) or on top and bottom (``side='v'``) only."""
    if side not in ("h", "v"):
        raise ValueError("side must be 'h' or 'v'")

    def delta(u, phi):
        w = np.cos(0.5 * math.pi * phi) ** 2 if side == "h" else np.sin(0.5 * math.pi * phi) ** 2
        s = np.clip((u - (1.0 - LIP_FRACTION)) / LIP_FRACTION, 0.0, 1.0)
        return w * extra_mm * s * s
    return apply_radial_edit(rec, delta, name=f"termination_split({side},{extra_mm})")


def _superellipse_r(a, b, theta, p):
    c, s = np.abs(np.cos(theta)), np.abs(np.sin(theta))
    return 1.0 / ((c / a) ** p + (s / b) ** p) ** (1.0 / p)


def section_steering(rec: SurfaceRecord, *, timing: str, exponent: float = 3.0) -> SurfaceRecord:
    """U3 (c): move each station's section toward a superellipse of ``exponent`` (2 = ellipse)
    with the same H and V half-widths, ramped in ``early`` (u 0.1-0.5) or ``late`` (0.5-0.9)."""
    if timing not in ("early", "late"):
        raise ValueError("timing must be 'early' or 'late'")
    xy = rec.inner[:, :, :2]
    r = np.linalg.norm(xy, axis=-1)
    theta = np.arctan2(xy[..., 1], xy[..., 0])
    a, b = r[0][None, :], r[-1][None, :]
    target = _superellipse_r(a, b, theta, exponent)
    lo, hi = (0.1, 0.5) if timing == "early" else (0.5, 0.9)

    def delta(u, phi):
        return (target - r) * smoothstep((u - lo) / (hi - lo))
    return apply_radial_edit(rec, delta, name=f"section_steering({timing},p={exponent})")


def diagonal_pull(rec: SurfaceRecord, *, pull_mm: float = 10.0, start: float = 0.7) -> SurfaceRecord:
    """U3 (d): pull the 45-degree wall inward by ``pull_mm`` at the mouth (sin^2(2 phi) weight)."""
    def delta(u, phi):
        return -pull_mm * np.sin(math.pi * phi) ** 2 * smoothstep((u - start) / (1.0 - start))
    return apply_radial_edit(rec, delta, name=f"diagonal_pull({pull_mm})")


def u3_variants(rec: SurfaceRecord, *, mouth_height_targets=(460.0, 480.0)) -> dict:
    """The seven U3 single-change variants (VALIDATION_EXPERIMENTS.md U3 step 1)."""
    return {
        "vt_460": vertical_timing(rec, mouth_height_mm=mouth_height_targets[0]),
        "vt_480": vertical_timing(rec, mouth_height_mm=mouth_height_targets[1]),
        "term_sides": termination_split(rec, side="h"),
        "term_topbottom": termination_split(rec, side="v"),
        "steer_early": section_steering(rec, timing="early"),
        "steer_late": section_steering(rec, timing="late"),
        "diag_pull": diagonal_pull(rec),
    }


# ------------------------------------------------------------------ U2 validity checks

def validity(rec: SurfaceRecord, control: SurfaceRecord | None = None, *,
             envelope_mm: dict | None = None, wall_thickness_mm: float | None = None) -> dict:
    """U2 checks plus the U3 reach statistic. ``ok`` is True only if every check passes."""
    out: dict = {}
    d = descriptors(rec)
    pre = slice(0, int(round((1.0 - LIP_FRACTION) * (rec.n_s - 1))) + 1)
    xy = rec.inner[:, :, :2]
    r = np.linalg.norm(xy, axis=-1)
    z = rec.inner[:, :, 2]
    out["no_fold_before_lip"] = bool(np.all(np.diff(z[:, pre], axis=1) > -1e-9))
    half_w = np.abs(rec.inner[0, :, 0])
    half_h = np.abs(rec.inner[-1, :, 1])
    out["w_h_nondecreasing_before_lip"] = bool(np.all(np.diff(half_w[pre]) > -1e-6)
                                               and np.all(np.diff(half_h[pre]) > -1e-6))
    out["radius_positive"] = bool(np.all(r[:, 1:] > 0.0))
    if control is not None:
        out["throat_ring_unchanged"] = bool(np.allclose(rec.inner[:, 0], control.inner[:, 0],
                                                        atol=1e-9))
        disp = np.linalg.norm(rec.inner - control.inner, axis=-1)
        keep = slice(0, int(round(0.95 * (rec.n_s - 1))))
        per_station_rms = np.sqrt(np.mean(disp[:, keep] ** 2, axis=0))
        out["max_rms_change_outside_last5pct_mm"] = float(per_station_rms.max())
        out["reach_ge_5mm"] = bool(per_station_rms.max() >= 5.0)
    t = wall_thickness_mm if wall_thickness_mm is not None else (rec.wall_thickness_mm or 0.0)
    if envelope_mm:
        from .record import envelope_margins
        m = envelope_margins(dataclasses.replace(rec, wall_thickness_mm=t), envelope_mm)
        out["envelope_margins_mm"] = m
        out["inside_envelope"] = all(v is None or v >= 0.0 for v in m.values())
    out["mouth_width_mm"] = d["mouth_width_mm"]
    out["mouth_height_mm"] = d["mouth_height_mm"]
    out["depth_mm"] = d["depth_mm"]
    bools = [v for k, v in out.items() if isinstance(v, bool) and k != "reach_ge_5mm"]
    out["ok"] = bool(all(bools))
    return out


# ------------------------------------------------------------------ point-grid hand-off

def throat_half_angle_deg(rec: SurfaceRecord) -> float:
    """Mean wall half-angle at the throat from the first two stations (the source-cap angle a
    point-grid build needs when the recipe's resolved value is not carried; contract §5 says the
    exact value should be copied from the recipe when available)."""
    p0, p1 = rec.inner[:, 0], rec.inner[:, 1]
    dr = np.linalg.norm(p1[:, :2], axis=-1) - np.linalg.norm(p0[:, :2], axis=-1)
    dz = p1[:, 2] - p0[:, 2]
    return float(np.degrees(np.arctan2(dr, dz)).mean())


def record_to_grid(rec: SurfaceRecord, *, wall_thickness_mm: float | None = None,
                   source_auto_angle_deg: float | None = None) -> dict:
    """The grid dict ``mesh.grid_build.build_grid_mesh`` takes (quarter model, mm)."""
    t = wall_thickness_mm if wall_thickness_mm is not None else rec.wall_thickness_mm
    angle = source_auto_angle_deg if source_auto_angle_deg is not None else throat_half_angle_deg(rec)
    out = {"inner_points": np.ascontiguousarray(rec.inner, dtype=float),
           "meta": {"quarter": True, "row_span": "quarter",
                    "source_auto_angle_deg": float(angle),
                    "record_digest": rec.digest(), "edit": rec.meta.get("edit")}}
    if t is not None and t > 0.0:
        out["wall_thickness_mm"] = float(t)
    return out


__all__ = ["apply_radial_edit", "vertical_timing", "termination_split", "section_steering",
           "diagonal_pull", "u3_variants", "validity", "record_to_grid",
           "throat_half_angle_deg", "smoothstep", "LIP_FRACTION"]
