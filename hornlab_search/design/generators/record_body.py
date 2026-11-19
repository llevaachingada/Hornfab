"""Explicit canonical-record body: solve a contract-v2 record as-is (senior plan WP 4.2/4.3).

A grid recipe whose ``rows.type`` is ``canonical_record_v2`` carries the record's inner points
inline plus its digest. Resolving it re-checks the digest of the points (provenance gated on the
GEOMETRY, senior review §4.2) and builds the freestanding outer shell with the same
``grid.grid_outer_points`` the generic route uses. Nothing is re-derived from knobs, so the solved
surface is exactly the (possibly edited) record: the unedited record is the WP 4.2 control, the
U3 variants (``geometry.edits``) are the WP 4.3 arms.
"""
from __future__ import annotations

import hashlib

import numpy as np

from .registry import GeneratorError

KIND = "canonical_record_v2"
SAMPLER_VERSION = "record-v2.0"


def is_family_spec(spec) -> bool:
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") == KIND)


def points_digest(inner: np.ndarray, sampler_version: str = SAMPLER_VERSION) -> str:
    """Identical to ``geometry.record.SurfaceRecord.digest`` for the same array."""
    h = hashlib.sha256()
    h.update(f"{sampler_version}|{inner.shape}".encode())
    h.update(np.ascontiguousarray(inner, dtype="<f8").tobytes())
    return h.hexdigest()


#: Outer-shell constructions: "grid" = ``grid.grid_outer_points`` (default; the WP 4.2-validated
#: route), "normal" = ``lame_shell.offset_quarter_surface`` (sampled 3D surface normal + self-approach
#: check), the shell the Klangfilm-Lame families build, so a Klangfilm host replays its own shell.
OUTER_OFFSETS = ("grid", "normal")


def spec_from_record(rec, *, wall_thickness_mm: float, source_auto_angle_deg: float,
                     name: str = "grid", outer_offset: str = "grid") -> dict:
    """The grid recipe for a :class:`geometry.record.SurfaceRecord` (inline points)."""
    inner = np.asarray(rec.inner, dtype=float)
    if outer_offset not in OUTER_OFFSETS:
        raise GeneratorError(f"{KIND}: outer_offset must be one of {OUTER_OFFSETS}")
    extra = {} if outer_offset == "grid" else {"outer_offset": outer_offset}
    return {"name": name, "n_phi": int(inner.shape[0]), "n_s": int(inner.shape[1]),
            "wall_thickness_mm": float(wall_thickness_mm),
            "rows": {"type": KIND, "implementation_sha256": points_digest(inner, rec.sampler_version),
                     "sampler_version": rec.sampler_version,
                     "source_auto_angle_deg": float(source_auto_angle_deg),
                     "edit": (rec.meta or {}).get("edit"),
                     **extra,
                     "points": inner.tolist()}}


# WP 4.4 (senior verdict 2026-11-19): record-edit freedoms as searched knobs on an explicit record body.
#   vertical timing (pair): ``g_vt_mm`` = total V-wall mouth height (mm); ``g_vt_hold`` = how much the early
#     V-wall growth is held back (0 = none). (host mouth height, 0) reproduces the host exactly.
#   V-lip beak (2026-11-19): ``g_beak_v_mm`` = axial projection of the top/bottom lips (0 = none);
#     optional ``g_beak_start`` = wall fraction where it starts (default 0.7; inert at 0 mm).
# Every knob has a host value inside its bounds, so the control is always reachable.
VT_KNOBS = ("g_vt_hold", "g_vt_mm")
BEAK_KNOBS = ("g_beak_v_mm", "g_beak_start")
ALL_KNOBS = VT_KNOBS + BEAK_KNOBS
BEAK_START_DEFAULT = 0.7
#: a rolled lip may approach its own body, never closer than this (or the host's own clearance)
MIN_LIP_CLEARANCE_MM = 2.0


def _host_record(inner, rows):
    from hornlab_search.geometry.record import SurfaceRecord
    seg = np.linalg.norm(np.diff(inner, axis=1), axis=-1)
    arc = np.concatenate([np.zeros((inner.shape[0], 1)), np.cumsum(seg, axis=1)], axis=1)
    return SurfaceRecord(inner=inner, arc_length_mm=arc, route="record_body",
                         sampler_version=str(rows.get("sampler_version") or SAMPLER_VERSION))


def _knob_values(knobs) -> dict | None:
    if not knobs:
        return None
    unknown = sorted(set(knobs) - set(ALL_KNOBS))
    if unknown:
        raise GeneratorError(f"{KIND}: unknown knobs {unknown}; allowed {list(ALL_KNOBS)}")
    vals = {k: float(knobs[k]) for k in knobs}
    if not all(np.isfinite(v) for v in vals.values()):
        raise GeneratorError(f"{KIND}: record-edit knobs must be finite")
    if any(k in vals for k in VT_KNOBS):
        missing = [k for k in VT_KNOBS if k not in vals]
        if missing:
            raise GeneratorError(f"{KIND}: vertical timing needs both {list(VT_KNOBS)}, missing {missing}")
        if not 0.0 <= vals["g_vt_hold"] <= 0.9:
            raise GeneratorError(f"{KIND}: g_vt_hold {vals['g_vt_hold']} outside [0, 0.9]")
        if vals["g_vt_mm"] <= 0.0:
            raise GeneratorError(f"{KIND}: g_vt_mm must be positive")
    if "g_beak_start" in vals and "g_beak_v_mm" not in vals:
        raise GeneratorError(f"{KIND}: g_beak_start needs g_beak_v_mm")
    if not -30.0 <= vals.get("g_beak_v_mm", 0.0) <= 60.0:
        raise GeneratorError(f"{KIND}: g_beak_v_mm {vals['g_beak_v_mm']} outside [-30, 60]")
    if not 0.3 <= vals.get("g_beak_start", BEAK_START_DEFAULT) <= 0.95:
        raise GeneratorError(f"{KIND}: g_beak_start {vals['g_beak_start']} outside [0.3, 0.95]")
    return vals


def apply_knobs(inner: np.ndarray, rows: dict, knobs) -> tuple[np.ndarray, str | None]:
    """Apply the record edits (vertical timing, then the V-lip beak) to verified host points.

    Validity is RELATIVE to the host: a U2 structure check (fold before the lip, shrinking W/H before
    the lip, non-positive radius) refuses the edit only if the host passed it, so rolled-lip hosts
    (which fold back by design) can be edited; the lip may not come closer to the body than
    ``MIN_LIP_CLEARANCE_MM`` (or the host's own clearance, if smaller)."""
    vals = _knob_values(knobs)
    if vals is None:
        return inner, rows.get("edit")
    from hornlab_search.geometry import edits
    host = _host_record(inner, rows)
    v = host
    names = []
    if "g_vt_mm" in vals:
        v = edits.vertical_timing(v, mouth_height_mm=vals["g_vt_mm"], strength=vals["g_vt_hold"])
        names.append(v.meta.get("edit"))
    if vals.get("g_beak_v_mm", 0.0) != 0.0:
        v = edits.vertical_beak(v, projection_mm=vals["g_beak_v_mm"],
                                start=vals.get("g_beak_start", BEAK_START_DEFAULT))
        names.append(v.meta.get("edit"))
    ref, chk = edits.validity(host), edits.validity(v)
    bad = sorted(k for k, x in chk.items() if x is False and ref.get(k) is True)
    if bad:
        raise GeneratorError(f"{KIND}: record edit {vals} fails structure checks the host passes {bad}")
    need = min(MIN_LIP_CLEARANCE_MM, edits.lip_clearance_mm(host))
    got = edits.lip_clearance_mm(v)
    if got < need - 1e-9:
        raise GeneratorError(f"{KIND}: record edit {vals} brings the lip within {got:.2f} mm of the wall "
                             f"(minimum {need:.2f} mm)")
    return v.inner, " + ".join(n for n in names if n) or None


def host_value(inner: np.ndarray, knob: str) -> float | None:
    """The knob value that reproduces the host exactly (None: inert at the host, any value is fine)."""
    return {"g_vt_mm": host_mouth_height_mm(inner), "g_vt_hold": 0.0, "g_beak_v_mm": 0.0}.get(knob)


def design_params(spec, knobs, brief) -> dict:
    if not knobs:
        return {"grid": dict(spec)}
    block = {**spec, "knobs": _knob_values(knobs)}
    resolve_grid(block, brief)
    return {"grid": block}


def validate_search_config(spec, seed, bounds, brief) -> None:
    """Every knob needs a seed and an explicit bound; each bound must contain the host value of its
    knob so the search can return to the unedited horn."""
    if not seed:
        return
    vals = _knob_values(seed)
    if not isinstance(bounds, dict) or set(bounds) != set(vals):
        raise GeneratorError(f"{KIND}: bounds must name exactly the seeded knobs {sorted(vals)}")
    inner = np.asarray(((spec or {}).get("rows") or {}).get("points"), dtype=float)
    for k in sorted(vals):
        lo, hi = float(bounds[k].lo), float(bounds[k].hi)
        if not lo <= vals[k] <= hi:
            raise GeneratorError(f"{KIND}: seed {k}={vals[k]:g} outside [{lo:g}, {hi:g}]")
        h = host_value(inner, k)
        if h is not None and not lo - 1e-6 <= h <= hi + 1e-6:
            raise GeneratorError(f"{KIND}: bounds of {k} [{lo:g}, {hi:g}] exclude the host value "
                                 f"{h:.1f} (control must be reachable)")


def host_mouth_height_mm(inner: np.ndarray) -> float:
    """The (g_vt_mm, g_vt_hold=0) value that reproduces the host exactly."""
    return float(2.0 * np.linalg.norm(np.asarray(inner, float)[-1, -1, :2]))


def resolve_grid(block, brief) -> dict:
    from . import grid
    rows = block.get("rows") or {}
    try:
        inner = np.asarray(rows["points"], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError(f"{KIND}: rows.points missing or malformed") from exc
    if inner.ndim != 3 or inner.shape[2] != 3 or not np.all(np.isfinite(inner)):
        raise GeneratorError(f"{KIND}: points must be finite (n_phi, n_s, 3), got {inner.shape}")
    want = rows.get("implementation_sha256")
    got = points_digest(inner, str(rows.get("sampler_version") or SAMPLER_VERSION))
    if want != got:
        raise GeneratorError(f"{KIND}: point digest {got[:12]} != recorded {str(want)[:12]}")
    host_digest = got
    inner, edit = apply_knobs(inner, rows, block.get("knobs"))
    if block.get("knobs"):
        got = points_digest(inner, str(rows.get("sampler_version") or SAMPLER_VERSION))
    else:
        edit = rows.get("edit")
    if (brief or {}).get("mounting"):
        raise GeneratorError(f"{KIND}: explicit record bodies are freestanding only in this pass")
    t = float(block.get("wall_thickness_mm", 3.0))
    mode = str(rows.get("outer_offset") or "grid")
    if mode not in OUTER_OFFSETS:
        raise GeneratorError(f"{KIND}: outer_offset must be one of {OUTER_OFFSETS}")
    if mode == "normal":
        from . import lame_shell
        outer, _ = lame_shell.offset_quarter_surface(inner, t)
        grid.check_self_approach(inner, outer, t)
    else:
        outer = grid.grid_outer_points(inner, t)
    angle = float(rows.get("source_auto_angle_deg", 0.0))
    if not abs(angle) > 1e-9:
        raise GeneratorError(f"{KIND}: source_auto_angle_deg must be nonzero")
    meta = {"quarter": True, "row_span": "quarter", "source_auto_angle_deg": angle,
            "mouth_w_mm": float(2.0 * np.max(np.abs(outer[:, :, 0]))),
            "mouth_h_mm": float(2.0 * np.max(np.abs(outer[:, :, 1]))),
            "x_span_mm": float(np.max(outer[:, :, 2]) - min(0.0, float(np.min(outer[:, :, 2])))),
            "record_digest": got, "host_digest": host_digest, "edit": edit,
            "knobs": dict(block.get("knobs") or {})}
    return {"inner_points": inner, "outer_points": outer, "meta": meta, "wall_thickness_mm": t}


def validate_grid_params(block) -> None:
    """Structural check used by FREEFORM validation (digest re-checked, no brief needed)."""
    rows = (block or {}).get("rows") or {}
    try:
        inner = np.asarray(rows["points"], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError(f"{KIND}: rows.points missing or malformed") from exc
    if inner.ndim != 3 or inner.shape[2] != 3:
        raise GeneratorError(f"{KIND}: points must be (n_phi, n_s, 3)")
    if points_digest(inner, str(rows.get("sampler_version") or SAMPLER_VERSION)) != rows.get("implementation_sha256"):
        raise GeneratorError(f"{KIND}: point digest does not match the recorded digest")
    apply_knobs(inner, rows, block.get("knobs"))
