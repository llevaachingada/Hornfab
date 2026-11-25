"""Adapter: CD wall-angle backbone under a retained returned lip (`cd-backbone-v1`), two kinds.

LABELED HYPOTHESIS, no published name. Dossier:
docs/research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md

* ``rolled_family_rect_bb_v1`` -- parent = :mod:`rolled_cd_family` (rolled rectangle + CD law);
* ``klangfilm_lame_hv_bb_v1``  -- parent = :mod:`klangfilm_lame_hv_family` (Klangfilm-Lame Phase A).

The parent surface and its saved-recipe contract are delegated unchanged; the backbone kernel
(:mod:`_cd_backbone_v1`) then rebuilds only each row's pre-roll arc. Additive rule:
``g_bb_h == g_bb_v == 0`` returns the parent result object unchanged (bit-for-bit). For any setting
the throat station, every forward (roll-on) station, the returned lip and the rim are kept exactly.
The kinds, schemas and digests are new, so no existing recipe identity changes.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np

from . import _cd_backbone_v1 as kernel
from . import klangfilm_lame_hv_family, lame_shell, rolled_cd_family
from .registry import GeneratorError

ROLLED_KIND = "rolled_family_rect_bb_v1"
LAME_KIND = "klangfilm_lame_hv_bb_v1"
KINDS = (ROLLED_KIND, LAME_KIND)
SCHEMAS = {ROLLED_KIND: "rolled-family-bb-v1", LAME_KIND: "klangfilm-lame-hv-bb-v1"}
PARENTS = {ROLLED_KIND: rolled_cd_family, LAME_KIND: klangfilm_lame_hv_family}
PARENT_KIND = {ROLLED_KIND: rolled_cd_family.KIND, LAME_KIND: klangfilm_lame_hv_family.KIND}
PARENT_SCHEMA = {ROLLED_KIND: rolled_cd_family.SCHEMA, LAME_KIND: klangfilm_lame_hv_family.SCHEMA}
BB_KNOB_KEYS = frozenset("g_" + key for key in kernel.BB_KEYS)
_ROW_META = {ROLLED_KIND: {"type", "mode", "schema", "implementation_sha256", "driver"},
             LAME_KIND: {"type", "schema", "implementation_sha256", "driver"}}


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") in KINDS)


def _kind(spec):
    if not is_family_spec(spec):
        raise GeneratorError("not a CD-backbone specification")
    return spec["rows"]["type"]


def implementation_digest(kind):
    if kind not in KINDS:
        raise GeneratorError(f"unknown CD-backbone type: {kind!r}")
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(kernel.__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    digest.update(f"{kind};parent={PARENTS[kind].implementation_digest()}".encode())
    return digest.hexdigest()


def _split(knobs):
    if not isinstance(knobs, dict):
        raise GeneratorError("CD-backbone knobs must be a mapping")
    bb = {key[len("g_"):]: knobs[key] for key in BB_KNOB_KEYS if key in knobs}
    parent = {key: value for key, value in knobs.items() if key not in BB_KNOB_KEYS}
    if set(bb) != kernel.BB_KEYS:
        raise GeneratorError(f"CD-backbone knobs: expected {sorted(BB_KNOB_KEYS)}, "
                             f"missing {sorted(kernel.BB_KEYS - set(bb))}")
    try:
        kernel.validate_bb(bb)
    except ValueError as exc:
        raise GeneratorError(f"CD-backbone law: {exc}") from exc
    return parent, bb


def _parent_spec(spec):
    kind = _kind(spec)
    out = copy.deepcopy({key: value for key, value in spec.items() if key != "knobs"})
    rows = {"type": PARENT_KIND[kind]}
    if kind == ROLLED_KIND:
        rows["mode"] = spec["rows"].get("mode")
    out["rows"] = rows
    return out


def _parent_block(block, parent_knobs):
    kind = _kind(block)
    out = copy.deepcopy({key: value for key, value in block.items() if key != "knobs"})
    rows = copy.deepcopy(block["rows"])
    rows.update(type=PARENT_KIND[kind], schema=PARENT_SCHEMA[kind],
                implementation_sha256=PARENTS[kind].implementation_digest())
    out["rows"] = rows
    out["knobs"] = parent_knobs
    return out


def _check_recipe(block):
    kind = _kind(block)
    rows = block["rows"]
    if set(rows) - _ROW_META[kind]:
        raise GeneratorError("unknown CD-backbone rows metadata")
    if block.get("span", "quarter") != "quarter":
        raise GeneratorError("CD-backbone family requires quarter symmetry")
    if rows.get("schema") != SCHEMAS[kind] or rows.get("implementation_sha256") != implementation_digest(kind):
        raise GeneratorError("CD-backbone schema or implementation differs from saved recipe")
    if "knobs" not in block:
        raise GeneratorError("CD-backbone knobs are required")
    return kind


def design_params(spec, knobs, brief):
    kind = _kind(spec)
    parent_knobs, bb = _split(knobs)
    block = copy.deepcopy(PARENTS[kind].design_params(_parent_spec(spec), parent_knobs, brief)["grid"])
    block["rows"].update(type=kind, schema=SCHEMAS[kind], implementation_sha256=implementation_digest(kind))
    block["knobs"] = {**block["knobs"], **{"g_" + key: value for key, value in bb.items()}}
    resolve_grid(block, brief)                         # full geometry + envelope validation
    return {"grid": block}


def _extents(inner, outer):
    both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    return [float(2 * np.max(abs(both[:, 0]))), float(2 * np.max(abs(both[:, 1]))), float(np.ptp(both[:, 2]))]


def resolve_grid(block, brief):
    """Materialise the parent surface, then apply the backbone (neutral = parent object unchanged)."""
    kind = _check_recipe(block)
    parent_knobs, bb = _split(block["knobs"])
    parent = PARENTS[kind].resolve_grid(_parent_block(block, parent_knobs), brief)
    if kernel.is_neutral(bb):
        return parent
    try:
        inner, info = kernel.apply_to_inner(parent["inner_points"], bb)
    except ValueError as exc:
        raise GeneratorError(f"CD-backbone law: {exc}") from exc
    wall = float(block.get("wall_thickness_mm", 3.0))
    from . import grid
    shell_metrics = None
    try:
        if kind == ROLLED_KIND:
            outer = grid.grid_outer_points(inner, wall)
        else:
            outer, shell_metrics = lame_shell.offset_quarter_surface(inner, wall)
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f"CD-backbone shell: {exc}") from exc
    for name, sheet in (("inner", inner), ("outer", outer)):
        if not np.isfinite(sheet).all():
            raise GeneratorError(f"nonfinite {name} surface")
        normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
        if np.min(np.linalg.norm(normal, axis=-1)) <= 1e-9:
            raise GeneratorError(f"degenerate {name} surface")
    grid.check_self_approach(inner, outer, wall)
    extents = _extents(inner, outer)
    policy = block.get("size_policy", "enforce")
    violations = []
    for actual, key in zip(extents, ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm")):
        limit = ((brief or {}).get("envelope") or {}).get(key)
        if limit is not None and actual > float(limit):
            if policy == "enforce":
                raise GeneratorError(f"invalid_envelope: {key} {actual:.3f} exceeds {limit}")
            violations.append({"key": key, "actual_mm": actual, "limit_mm": float(limit)})
    meta = dict(parent["meta"])
    meta.update(construction_label=SCHEMAS[kind], parent_construction=parent["meta"].get("construction_label"),
                schema=SCHEMAS[kind], implementation_sha256=implementation_digest(kind),
                backbone={key: float(value) for key, value in bb.items()},
                backbone_rows={"theta_c_h_deg": next((r["theta_c_deg"] for r in info if r["row"] == 0), None),
                               "theta_c_v_deg": next((r["theta_c_deg"] for r in info
                                                      if r["row"] == inner.shape[0] - 1), None),
                               "max_lam": max((r["lam"] for r in info), default=0.0),
                               "rows_changed": len(info)},
                mouth_w_mm=extents[0], mouth_h_mm=extents[1], x_span_mm=extents[2])
    if kind == LAME_KIND:
        meta.update(shell_metrics=shell_metrics, envelope_violations=violations, envelope_ok=not violations)
    meta["shape"] = dict(meta.get("shape") or {}, **{key: float(value) for key, value in bb.items()})
    meta["notes"] = [*meta.get("notes", []),
                     "LABELED HYPOTHESIS: CD wall-angle backbone under the retained return; no published geometry"]
    return {"inner_points": inner, "outer_points": outer, "meta": meta}


def validate_grid_params(block):
    _check_recipe(block)
    parent_knobs, _bb = _split(block["knobs"])
    PARENTS[_kind(block)].validate_grid_params(_parent_block(block, parent_knobs))


def validate_search_config(spec, seed, bounds, brief):
    """Mirror the parent contract and add the backbone bound and dormancy rules."""
    kind = _kind(spec)
    parent_seed, bb_seed = _split(seed)
    bb_bounds = {key: value for key, value in bounds.items() if key in BB_KNOB_KEYS}
    parent_bounds = {key: value for key, value in bounds.items() if key not in BB_KNOB_KEYS}
    if set(bb_bounds) != BB_KNOB_KEYS:
        raise GeneratorError(f"CD-backbone needs explicit bounds for {sorted(BB_KNOB_KEYS)}")
    PARENTS[kind].validate_search_config(_parent_spec(spec), parent_seed, parent_bounds, brief)
    for key, b in bb_bounds.items():
        value = bb_seed[key[len("g_"):]]
        if not b.lo <= value <= b.hi:
            raise GeneratorError(f"{key}: seed outside its declared bounds")
        if not b.search and not (b.lo == b.hi == value):
            raise GeneratorError(f"{key}: fixed bound must equal its seed")
        if b.log:
            raise GeneratorError("CD-backbone knobs use explicit linear bounds")
        try:
            for endpoint in (b.lo, b.hi):
                kernel.validate_bb({**bb_seed, key[len("g_"):]: float(endpoint)})
        except ValueError as exc:
            raise GeneratorError(f"CD-backbone law at a bound: {exc}") from exc
    shape_search = any(bb_bounds[k].search for k in ("g_bb_throat_frac", "g_bb_rollin_frac"))
    strength_away_zero = any(bb_bounds[k].lo > 0.0 for k in ("g_bb_h", "g_bb_v"))
    if shape_search and not strength_away_zero:
        raise GeneratorError("backbone shape knobs are dormant when both strengths can be zero; pin them")
