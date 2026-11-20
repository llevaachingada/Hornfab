"""Adapter for the rolled rectangular body + CD wall-angle law (`rolled-family-cd-v1`).

The adapter is deliberately thin: it delegates the entire parent surface and its saved-recipe
contract to :mod:`rolled_family` (the frozen v1 kernel), then adds one versioned, digest-bound
operation on the inner grid (see :mod:`_rolled_rect_cd_v1`). The additive rule is absolute:

* ``g_cd_h_deg == g_cd_v_deg == 0`` -> the parent result object is returned unchanged, so the
  neutral control is the **bit-for-bit** v1 geometry;
* nonzero amplitudes -> the CD kernel displaces only the pre-roll arc; the throat, mouth outline,
  depth and returned lip are unchanged by construction.

The kind is new (``rolled_family_rect_cd_v1``) and the schema/digest are new, so no existing
rolled-family recipe's identity changes.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

import numpy as np

from . import _rolled_rect_v1 as _v1
from . import _rolled_rect_cd_v1 as cd_kernel
from . import rolled_family
from .registry import GeneratorError

KIND = "rolled_family_rect_cd_v1"
KINDS = (KIND,)
PARENT_KIND = rolled_family.KINDS[0]
MODES = (*rolled_family.MODES, "cd")
SCHEMA = "rolled-family-cd-v1"
CD_KNOB_KEYS = frozenset("g_" + key for key in cd_kernel.CD_KEYS)
SPEC_KEYS = rolled_family.SPEC_KEYS
GRID_KEYS = rolled_family.GRID_KEYS


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") in KINDS)


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(cd_kernel.__file__), Path(rolled_family.__file__),
                 Path(_v1.__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def shape_keys(kind=None):
    if kind is not None and kind not in KINDS:
        raise GeneratorError(f"unknown rolled-CD type: {kind!r}")
    return frozenset(rolled_family.shape_keys(PARENT_KIND)) | cd_kernel.CD_KEYS


def _split(knobs):
    """Split a knob mapping into (parent knobs, CD knobs). Requires the full CD key set."""
    if not isinstance(knobs, dict):
        raise GeneratorError("rolled-CD knobs must be a mapping")
    cd = {key[len("g_"):]: knobs[key] for key in CD_KNOB_KEYS if key in knobs}
    parent = {key: value for key, value in knobs.items() if key not in CD_KNOB_KEYS}
    if set(cd) != cd_kernel.CD_KEYS:
        raise GeneratorError(f"rolled-CD knobs: expected {sorted(CD_KNOB_KEYS)}, "
                             f"missing {sorted(cd_kernel.CD_KEYS - set(cd))}")
    try:
        cd_kernel.validate_cd(cd)
    except ValueError as exc:
        raise GeneratorError(f"rolled-CD law: {exc}") from exc
    return parent, cd


def _parent_spec(spec):
    rows = spec["rows"]
    mode = rows.get("mode")
    if mode not in MODES:
        raise GeneratorError(f"explicit relief mode required, one of {MODES}")
    parent_mode = "smooth" if mode == "cd" else mode
    out = {key: spec[key] for key in ("name", "n_phi", "n_s", "wall_thickness_mm", "span")
           if key in spec}
    out["rows"] = {"type": PARENT_KIND, "mode": parent_mode}
    return out


def _parent_block(block, parent_knobs):
    rows = copy.deepcopy(block["rows"])
    rows["type"] = PARENT_KIND
    rows["schema"] = rolled_family.SCHEMA
    rows["implementation_sha256"] = rolled_family.implementation_digest()
    if rows.get("mode") == "cd":
        rows["mode"] = "smooth"
    out = {"rows": rows, "knobs": parent_knobs}
    for key in ("n_phi", "n_s", "wall_thickness_mm", "span"):
        if key in block:
            out[key] = block[key]
    return out


def _check_recipe(block):
    if not is_family_spec(block):
        raise GeneratorError("not a rolled-CD block")
    if set(block) - set(SPEC_KEYS):
        raise GeneratorError(f"unknown rolled-CD block key(s) {sorted(set(block) - set(SPEC_KEYS))}")
    rows = block["rows"]
    if set(rows) - {"type", "mode", "schema", "implementation_sha256", "driver"}:
        raise GeneratorError("unknown rolled-CD rows metadata")
    if block.get("span", "quarter") != "quarter":
        raise GeneratorError("rolled-CD family requires quarter symmetry")
    if rows.get("schema") != SCHEMA or rows.get("implementation_sha256") != implementation_digest():
        raise GeneratorError("rolled-CD schema or implementation differs from saved recipe")
    if "knobs" not in block:
        raise GeneratorError("rolled-CD knobs are required")


def design_params(spec, knobs, brief):
    if not is_family_spec(spec):
        raise GeneratorError("not a rolled-CD specification")
    if set(spec) - set(SPEC_KEYS):
        raise GeneratorError("unknown rolled-CD specification key(s)")
    parent_knobs, cd = _split(knobs)
    parent = rolled_family.design_params(_parent_spec(spec), parent_knobs, brief)
    block = copy.deepcopy(parent["grid"])
    block["rows"].update(type=KIND, schema=SCHEMA,
                         implementation_sha256=implementation_digest())
    block["knobs"] = {**block["knobs"],
                      **{"g_" + key: value for key, value in cd.items()}}
    resolve_grid(block, brief)                     # full geometry + envelope validation
    return {"grid": block}


def _envelope(inner, outer, wall, brief):
    both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    extents = [2 * np.max(abs(both[:, 0])), 2 * np.max(abs(both[:, 1])), np.ptp(both[:, 2])]
    for actual, key in zip(extents, ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm")):
        limit = (brief.get("envelope") or {}).get(key)
        if limit is not None and actual > float(limit):
            raise GeneratorError(f"invalid_envelope: {key} {actual:.3f} exceeds {limit}")
    return extents


def resolve_grid(block, brief):
    """Materialize the parent v1 surface, then apply the CD law (neutral = parent unchanged)."""
    _check_recipe(block)
    parent_knobs, cd = _split(block["knobs"])
    parent_block = _parent_block(block, parent_knobs)
    parent = rolled_family.resolve_grid(parent_block, brief)
    if cd_kernel.is_neutral(cd):
        return parent
    try:
        inner = cd_kernel.apply_to_inner(parent["inner_points"], cd)
    except ValueError as exc:
        raise GeneratorError(f"rolled-CD law: {exc}") from exc
    wall = float(block.get("wall_thickness_mm", 3.0))
    from . import grid
    outer = grid.grid_outer_points(inner, wall)
    for name, sheet in (("inner", inner), ("outer", outer)):
        if not np.isfinite(sheet).all():
            raise GeneratorError(f"nonfinite {name} surface")
        normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
        if np.min(np.linalg.norm(normal, axis=-1)) <= 1e-9:
            raise GeneratorError(f"degenerate {name} surface")
    grid.check_self_approach(inner, outer, wall)
    extents = _envelope(inner, outer, wall, brief)
    meta = dict(parent["meta"])
    meta.update(construction_label=SCHEMA, cd={key: float(value) for key, value in cd.items()},
                parent_construction=parent["meta"].get("construction_label"),
                implementation_sha256=implementation_digest(),
                mouth_w_mm=float(extents[0]), mouth_h_mm=float(extents[1]),
                x_span_mm=float(extents[2]))
    meta["shape"] = dict(meta.get("shape") or {}, **{key: float(value) for key, value in cd.items()})
    meta.setdefault("notes", [])
    meta["notes"] = [*meta["notes"],
                     "LABELED HYPOTHESIS: flare-timing wall-angle schedule; no published geometry"]
    return {"inner_points": inner, "outer_points": outer, "meta": meta}


def validate_grid_params(block):
    _check_recipe(block)
    parent_knobs, _cd = _split(block["knobs"])
    rolled_family.validate_grid_params(_parent_block(block, parent_knobs))


def validate_search_config(spec, seed, bounds, brief):
    """Mirror the parent contract and add the CD window/amplitude rules."""
    if not is_family_spec(spec):
        raise GeneratorError("not a rolled-CD specification")
    parent_seed, cd_seed = _split(seed)
    parent_bounds = {key: value for key, value in bounds.items()
                     if key not in CD_KNOB_KEYS}
    cd_bounds = {key: value for key, value in bounds.items() if key in CD_KNOB_KEYS}
    if set(cd_bounds) != CD_KNOB_KEYS:
        raise GeneratorError(f"rolled-CD needs explicit bounds for {sorted(CD_KNOB_KEYS)}")
    rolled_family.validate_search_config(_parent_spec(spec), parent_seed, parent_bounds, brief)
    intervals = {}
    for key, b in cd_bounds.items():
        value = cd_seed[key[len("g_"):]]
        if not b.lo <= value <= b.hi:
            raise GeneratorError(f"{key}: seed outside its declared bounds")
        if not b.search and not (b.lo == b.hi == value):
            raise GeneratorError(f"{key}: fixed bound must equal its seed")
        if b.log:
            raise GeneratorError("rolled-CD knobs use explicit linear physical bounds")
        intervals[key] = (float(b.lo), float(b.hi))
        try:
            for endpoint in (b.lo, b.hi):
                cd_kernel.validate_cd({**cd_seed, key[len("g_"):]: float(endpoint)})
        except ValueError as exc:
            raise GeneratorError(f"rolled-CD law at a bound: {exc}") from exc
    for key, limit in (("g_cd_h_deg", cd_kernel.MAX_CD_H_DEG),
                       ("g_cd_v_deg", cd_kernel.MAX_CD_V_DEG)):
        lo, hi = intervals[key]
        if abs(lo) > limit or abs(hi) > limit:
            raise GeneratorError(f"{key}: bound exceeds +/-{limit:g} deg")
    start = intervals["g_cd_start_s"]
    peak = intervals["g_cd_peak_s"]
    end = intervals["g_cd_end_s"]
    if not start[1] < peak[0] or not peak[1] < end[0]:
        raise GeneratorError("independent CD window bounds overlap")
    position_search = any(cd_bounds[k].search
                          for k in ("g_cd_start_s", "g_cd_peak_s", "g_cd_end_s"))
    strength_away_zero = any(lo > 0 or hi < 0 for key, (lo, hi) in intervals.items()
                             if key in ("g_cd_h_deg", "g_cd_v_deg"))
    if position_search and not strength_away_zero:
        raise GeneratorError("CD window position is dormant when both amplitudes can be zero; pin it")
