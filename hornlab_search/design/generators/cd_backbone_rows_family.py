"""Adapter: CD wall-angle backbone over a generic WP9b rows parent (kind ``rows_bb_v1``).

LABELED CD HYBRID, no published name. The parents (``lecleach``, ``lecleach_ar``, ``iwata_ar``,
``salmon_elliptical``, ...) were designed for loading or a natural narrowing pattern, not constant
directivity. A ``rows_bb_v1`` design is a NEW identity (e.g. "Le Cleac'h AR + CD backbone"), scored on a CD
brief against its own neutral control; it is never presented or ranked as the original typology.

Construction: the parent rows recipe is carried verbatim under ``rows.parent_rows`` and built by
:func:`grid.rows_grid_points`; the shared kernel :mod:`_cd_backbone_v1` then rebuilds only each row's
pre-roll arc (throat, roll-on station, return and rim kept exactly). Dossiers:
docs/research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md (construction) and its
"CD variants of non-CD returned-lip families" section.

Neutral rule: ``g_bb_h == g_bb_v == 0`` returns the parent's own ``(inner_points, meta)`` and no
``outer_points``, so ``mesh/grid_build`` offsets the shell exactly as for the bare rows recipe and the verify
mesh is byte-identical. This kind lives in its own module so the digests of the existing
``cd_backbone_family`` kinds (and their saved recipes) do not change. Quarter span only.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np

from . import _cd_backbone_v1 as kernel
from . import cd_backbone_family as base
from .registry import GeneratorError

KIND = "rows_bb_v1"
SCHEMA = "rows-bb-v1"
#: Generic rows parents the backbone may wrap (returned-lip WP9b marches, quarter span).
PARENT_TYPES = ("lecleach", "lecleach_ar", "iwata_ar", "salmon_elliptical", "lecleach_mod",
                "toroidal_rollback")
HYBRID_LABEL = ("LABELED CD HYBRID: CD wall-angle backbone under the parent's retained return; the parent "
                "typology ({parent}) is not constant-directivity by design and this design is not that typology")
_ROW_META = {"type", "parent_rows", "schema", "implementation_sha256"}
_GEOM_KEYS = ("n_phi", "n_s", "wall_thickness_mm")


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") == KIND)


def _sources():
    from .. import throat_hv
    from . import grid, profiles
    return (Path(__file__), Path(kernel.__file__), Path(base.__file__), Path(grid.__file__),
            Path(profiles.__file__), Path(throat_hv.__file__))


def implementation_digest():
    digest = hashlib.sha256()
    for path in _sources():
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    digest.update(f"{KIND};parent=grid.rows_grid_points".encode())
    return digest.hexdigest()


def _parent_spec(spec):
    """The generic rows spec of the parent (no knobs)."""
    if not is_family_spec(spec):
        raise GeneratorError("not a rows_bb_v1 specification")
    if spec.get("span", "quarter") != "quarter":
        raise GeneratorError("rows_bb_v1 requires quarter symmetry (the backbone reads row 0 = H, last = V)")
    parent = spec["rows"].get("parent_rows")
    if not isinstance(parent, dict) or parent.get("type") not in PARENT_TYPES:
        raise GeneratorError(f"rows_bb_v1 needs rows.parent_rows with type in {list(PARENT_TYPES)}")
    out = {key: copy.deepcopy(spec[key]) for key in _GEOM_KEYS if key in spec}
    out["rows"] = copy.deepcopy(parent)
    return out


def _check_recipe(block):
    _parent_spec(block)
    rows = block["rows"]
    if set(rows) - _ROW_META:
        raise GeneratorError("unknown rows_bb_v1 rows metadata")
    if rows.get("schema") != SCHEMA or rows.get("implementation_sha256") != implementation_digest():
        raise GeneratorError("rows_bb_v1 schema or implementation differs from saved recipe")
    if "knobs" not in block:
        raise GeneratorError("rows_bb_v1 knobs are required")


def design_params(spec, knobs, brief):
    from . import grid
    parent_knobs, bb = base._split(knobs)
    block = copy.deepcopy(grid.design_params(_parent_spec(spec), parent_knobs, brief)["grid"])
    if block.get("span", "quarter") != "quarter":
        raise GeneratorError("rows_bb_v1 requires quarter symmetry")
    block["rows"] = {"type": KIND, "parent_rows": block["rows"], "schema": SCHEMA,
                     "implementation_sha256": implementation_digest()}
    block["knobs"] = {**block["knobs"], **{"g_" + key: value for key, value in bb.items()}}
    resolve_grid(block, brief)                       # full geometry + envelope validation
    return {"grid": block}


def _envelope(extents, brief, policy):
    violations = []
    for actual, key in zip(extents, ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm")):
        limit = ((brief or {}).get("envelope") or {}).get(key)
        if limit is not None and actual > float(limit):
            if policy == "enforce":
                raise GeneratorError(f"invalid_envelope: {key} {actual:.3f} exceeds {limit}")
            violations.append({"key": key, "actual_mm": actual, "limit_mm": float(limit)})
    return violations


def resolve_grid(block, brief):
    from . import grid
    _check_recipe(block)
    parent_knobs, bb = base._split(block["knobs"])
    spec = _parent_spec(block)
    parent_type = spec["rows"]["type"]
    try:
        inner0, meta0 = grid.rows_grid_points(spec, parent_knobs, brief)
    except GeneratorError:
        raise
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f"rows_bb_v1 parent: {exc}") from exc
    wall = float(block.get("wall_thickness_mm", 3.0))
    neutral = kernel.is_neutral(bb)
    info = []
    if neutral:
        inner = inner0
    else:
        try:
            inner, info = kernel.apply_to_inner(np.asarray(inner0, dtype=float), bb)
        except ValueError as exc:
            raise GeneratorError(f"CD-backbone law: {exc}") from exc
    try:
        outer = grid.grid_outer_points(np.asarray(inner, dtype=float), wall)
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f"CD-backbone shell: {exc}") from exc
    if not neutral:
        for name, sheet in (("inner", inner), ("outer", outer)):
            if not np.isfinite(sheet).all():
                raise GeneratorError(f"nonfinite {name} surface")
            normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
            if np.min(np.linalg.norm(normal, axis=-1)) <= 1e-9:
                raise GeneratorError(f"degenerate {name} surface")
        grid.check_self_approach(inner, outer, wall)
    extents = base._extents(np.asarray(inner, dtype=float), outer)
    violations = _envelope(extents, brief, block.get("size_policy", "enforce"))
    meta = dict(meta0)
    meta.update(mouth_w_mm=extents[0], mouth_h_mm=extents[1], x_span_mm=extents[2],
                envelope_violations=violations, envelope_ok=not violations, rows_bb_parent_type=parent_type)
    if neutral:
        return {"inner_points": inner, "meta": meta}     # no outer_points: grid_build offsets as for the parent
    meta.update(construction_label=f"{SCHEMA}({parent_type})", parent_construction=parent_type,
                schema=SCHEMA, implementation_sha256=implementation_digest(),
                backbone={key: float(value) for key, value in bb.items()},
                backbone_rows={"theta_c_h_deg": next((r["theta_c_deg"] for r in info if r["row"] == 0), None),
                               "theta_c_v_deg": next((r["theta_c_deg"] for r in info
                                                      if r["row"] == inner.shape[0] - 1), None),
                               "max_lam": max((r["lam"] for r in info), default=0.0),
                               "rows_changed": len(info)})
    meta["notes"] = [*meta.get("notes", []), HYBRID_LABEL.format(parent=parent_type)]
    return {"inner_points": inner, "meta": meta}


def validate_grid_params(block):
    from . import grid
    _check_recipe(block)
    parent_knobs, _bb = base._split(block["knobs"])
    grid.validate_grid_params({**_parent_spec(block), "knobs": parent_knobs})


def validate_search_config(spec, seed, bounds, brief):
    """Backbone bound and dormancy rules (generic rows carry no search-config contract of their own)."""
    _parent_spec(spec)
    _parent_seed, bb_seed = base._split(seed)
    bb_bounds = {key: value for key, value in bounds.items() if key in base.BB_KNOB_KEYS}
    if set(bb_bounds) != base.BB_KNOB_KEYS:
        raise GeneratorError(f"rows_bb_v1 needs explicit bounds for {sorted(base.BB_KNOB_KEYS)}")
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
