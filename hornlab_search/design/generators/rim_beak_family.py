"""Adapter: rim beak (``rim-beak-v1``) over a CD-backbone parent, kind ``beak_v1``.

LABELED HYPOTHESIS. Owner request 2026-11-25: bring back the pulled-back / pushed-forward "beak" mouths for horns that
hang freestanding (every solve here is a freestanding model, not a baffle). Parents: ``rows_bb_v1`` (Le Cleac'h /
Iwata CD hybrids) and ``rolled_family_rect_bb_v1``. The parent's saved recipe (including its own schema and digest) is
carried verbatim under ``rows.parent_rows``, so the parent identity is part of this design's hash.

Neutral rule: ``rb_h == rb_v == rb_d == 0`` returns the parent's resolved result object unchanged (bit-for-bit; for a
``rows_bb_v1`` parent that means no ``outer_points`` and the same verify mesh). Otherwise the kernel moves the late
body and the whole lip/return/rim axially (see :mod:`_rim_beak_v1`), and the shell is re-offset with
``grid.grid_outer_points`` (the shell both supported parents use). Quarter span only. Own module and digest: adding it
changes no existing kind's identity.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np

from . import _rim_beak_v1 as kernel
from . import cd_backbone_family, cd_backbone_rows_family
from .registry import GeneratorError

KIND = "beak_v1"
SCHEMA = "rim-beak-family-v1"
RB_KNOB_KEYS = frozenset("g_" + key for key in kernel.RB_KEYS)
PARENT_MODULES = (cd_backbone_rows_family, cd_backbone_family)
PARENT_TYPES = (cd_backbone_rows_family.KIND, cd_backbone_family.ROLLED_KIND)
_ROW_META = {"type", "parent_rows", "schema", "implementation_sha256"}
LABEL = ("LABELED HYPOTHESIS: rim beak (H/V/diagonal lip offset along the axis) over {parent}; "
         "freestanding mouth, not a published construction")


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") == KIND)


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(kernel.__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    digest.update(f"{KIND};parents={','.join(PARENT_TYPES)}".encode())
    return digest.hexdigest()


def _split(knobs):
    if not isinstance(knobs, dict):
        raise GeneratorError("rim-beak knobs must be a mapping")
    rb = {key[len("g_"):]: knobs[key] for key in RB_KNOB_KEYS if key in knobs}
    parent = {key: value for key, value in knobs.items() if key not in RB_KNOB_KEYS}
    if set(rb) != kernel.RB_KEYS:
        raise GeneratorError(f"rim-beak knobs: expected {sorted(RB_KNOB_KEYS)}, "
                             f"missing {sorted(kernel.RB_KEYS - set(rb))}")
    try:
        kernel.validate_rb(rb)
    except ValueError as exc:
        raise GeneratorError(f"rim-beak law: {exc}") from exc
    return parent, rb


def _module(parent_rows):
    for module in PARENT_MODULES:
        if module.is_family_spec({"rows": parent_rows}):
            return module
    raise GeneratorError(f"beak_v1: unsupported parent {parent_rows.get('type')!r}")


def _parent_spec(spec):
    """The parent's spec (no knobs): this block with ``rows`` replaced by ``rows.parent_rows``."""
    if not is_family_spec(spec):
        raise GeneratorError("not a beak_v1 specification")
    if spec.get("span", "quarter") != "quarter":
        raise GeneratorError("beak_v1 requires quarter symmetry (row 0 = H, last = V)")
    parent = spec["rows"].get("parent_rows")
    if not isinstance(parent, dict) or parent.get("type") not in PARENT_TYPES:
        raise GeneratorError(f"beak_v1 needs rows.parent_rows with type in {list(PARENT_TYPES)}")
    out = copy.deepcopy({key: value for key, value in spec.items() if key != "knobs"})
    out["rows"] = copy.deepcopy(parent)
    return out


def _check_recipe(block):
    _parent_spec(block)
    rows = block["rows"]
    if set(rows) - _ROW_META:
        raise GeneratorError("unknown beak_v1 rows metadata")
    if rows.get("schema") != SCHEMA or rows.get("implementation_sha256") != implementation_digest():
        raise GeneratorError("beak_v1 schema or implementation differs from saved recipe")
    if "knobs" not in block:
        raise GeneratorError("beak_v1 knobs are required")


def design_params(spec, knobs, brief):
    parent_knobs, rb = _split(knobs)
    pspec = _parent_spec(spec)
    block = copy.deepcopy(_module(pspec["rows"]).design_params(pspec, parent_knobs, brief)["grid"])
    block["rows"] = {"type": KIND, "parent_rows": block["rows"], "schema": SCHEMA,
                     "implementation_sha256": implementation_digest()}
    block["knobs"] = {**block["knobs"], **{"g_" + key: value for key, value in rb.items()}}
    resolve_grid(block, brief)                      # full geometry + envelope validation
    return {"grid": block}


def _parent_block(block, parent_knobs):
    out = _parent_spec(block)
    out["knobs"] = parent_knobs
    return out


def resolve_grid(block, brief):
    from . import grid
    _check_recipe(block)
    parent_knobs, rb = _split(block["knobs"])
    pblock = _parent_block(block, parent_knobs)
    parent = _module(pblock["rows"]).resolve_grid(pblock, brief)
    if kernel.is_neutral(rb):
        return parent
    try:
        inner, info = kernel.apply_to_inner(np.asarray(parent["inner_points"], dtype=float), rb)
    except ValueError as exc:
        raise GeneratorError(f"rim-beak law: {exc}") from exc
    wall = float(block.get("wall_thickness_mm", 3.0))
    try:
        outer = grid.grid_outer_points(inner, wall)
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f"rim-beak shell: {exc}") from exc
    for name, sheet in (("inner", inner), ("outer", outer)):
        if not np.isfinite(sheet).all():
            raise GeneratorError(f"nonfinite {name} surface")
        normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
        if np.min(np.linalg.norm(normal, axis=-1)) <= 1e-9:
            raise GeneratorError(f"degenerate {name} surface")
    grid.check_self_approach(inner, outer, wall)
    extents = cd_backbone_family._extents(inner, outer)
    violations = cd_backbone_rows_family._envelope(extents, brief, block.get("size_policy", "enforce"))
    parent_type = pblock["rows"]["type"]
    meta = dict(parent["meta"])
    meta.update(construction_label=f"{SCHEMA}({parent_type})", parent_construction=parent_type,
                schema=SCHEMA, implementation_sha256=implementation_digest(),
                rim_beak={key: float(value) for key, value in rb.items()},
                rim_beak_rows={"dz_h_mm": info[0]["dz_mm"], "dz_v_mm": info[-1]["dz_mm"],
                               "dz_min_mm": min(r["dz_mm"] for r in info),
                               "dz_max_mm": max(r["dz_mm"] for r in info)},
                mouth_w_mm=extents[0], mouth_h_mm=extents[1], x_span_mm=extents[2],
                envelope_violations=violations, envelope_ok=not violations)
    meta["notes"] = [*meta.get("notes", []), LABEL.format(parent=parent_type)]
    return {"inner_points": inner, "outer_points": outer, "meta": meta}


def validate_grid_params(block):
    _check_recipe(block)
    parent_knobs, _rb = _split(block["knobs"])
    pblock = _parent_block(block, parent_knobs)
    _module(pblock["rows"]).validate_grid_params(pblock)


def validate_search_config(spec, seed, bounds, brief):
    pspec = _parent_spec(spec)
    parent_seed, rb_seed = _split(seed)
    rb_bounds = {key: value for key, value in bounds.items() if key in RB_KNOB_KEYS}
    parent_bounds = {key: value for key, value in bounds.items() if key not in RB_KNOB_KEYS}
    if set(rb_bounds) != RB_KNOB_KEYS:
        raise GeneratorError(f"beak_v1 needs explicit bounds for {sorted(RB_KNOB_KEYS)}")
    _module(pspec["rows"]).validate_search_config(pspec, parent_seed, parent_bounds, brief)
    for key, b in rb_bounds.items():
        value = rb_seed[key[len("g_"):]]
        if not b.lo <= value <= b.hi:
            raise GeneratorError(f"{key}: seed outside its declared bounds")
        if not b.search and not (b.lo == b.hi == value):
            raise GeneratorError(f"{key}: fixed bound must equal its seed")
        if b.log:
            raise GeneratorError("rim-beak knobs use explicit linear bounds")
        try:
            for endpoint in (b.lo, b.hi):
                kernel.validate_rb({**rb_seed, key[len("g_"):]: float(endpoint)})
        except ValueError as exc:
            raise GeneratorError(f"rim-beak law at a bound: {exc}") from exc
    if rb_bounds["g_rb_start_frac"].search and not any(rb_bounds["g_" + k].search for k in kernel.AMP_KEYS) \
            and all(rb_seed[k] == 0.0 for k in kernel.AMP_KEYS):
        raise GeneratorError("rb_start_frac is dormant when every beak amplitude is pinned at zero; pin it")
