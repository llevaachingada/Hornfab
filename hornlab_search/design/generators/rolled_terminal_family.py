"""Adapter for the H-only terminal roll-onset / C-return law (`rolled-family-term-v1`).

New kind ``rolled_family_rect_term_v1``. It delegates the parent surface and the existing CD
wall-angle law to :mod:`rolled_cd_family` (both untouched), then applies the versioned
:mod:`_rolled_rect_terminal_v1` deformation to the H meridian's terminal section.

The additive rule is absolute: ``g_tm_roll_frac == 0`` returns the delegated result object
unchanged, so the width-500 control geometry is bit-for-bit.  H-only: the azimuthal blend is a C2
smoothstep that is exactly zero at and beyond 40 deg from H, so the V cut, throat and depth are
unchanged (the x=0 symmetry plane stays exact).
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np

from . import _rolled_rect_cd_v1 as cd_kernel
from . import _rolled_rect_terminal_v1 as tm_kernel
from . import _rolled_rect_v1 as _v1
from . import rolled_cd_family
from . import rolled_family
from .registry import GeneratorError

KIND = "rolled_family_rect_term_v1"
KINDS = (KIND,)
PARENT_KIND = rolled_cd_family.KIND
MODES = rolled_cd_family.MODES
SCHEMA = "rolled-family-term-v1"
TM_KNOB_KEYS = frozenset("g_" + key for key in tm_kernel.TM_KEYS)
SPEC_KEYS = rolled_cd_family.SPEC_KEYS


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") in KINDS)


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(tm_kernel.__file__), Path(rolled_cd_family.__file__),
                 Path(cd_kernel.__file__), Path(rolled_family.__file__), Path(_v1.__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def shape_keys(kind=None):
    if kind is not None and kind not in KINDS:
        raise GeneratorError(f"unknown rolled-terminal type: {kind!r}")
    return frozenset(rolled_cd_family.shape_keys()) | tm_kernel.TM_KEYS


def _split(knobs):
    if not isinstance(knobs, dict):
        raise GeneratorError("rolled-terminal knobs must be a mapping")
    tm = {key[2:]: knobs[key] for key in TM_KNOB_KEYS if key in knobs}
    cd = {key: value for key, value in knobs.items() if key not in TM_KNOB_KEYS}
    if set(tm) != tm_kernel.TM_KEYS:
        raise GeneratorError(f"rolled-terminal knobs: expected {sorted(TM_KNOB_KEYS)}")
    try:
        tm_kernel.validate_tm(tm)
    except ValueError as exc:
        raise GeneratorError(f"rolled-terminal law: {exc}") from exc
    return cd, tm


def _cd_spec(spec):
    rows = spec["rows"]
    mode = rows.get("mode")
    if mode not in MODES:
        raise GeneratorError(f"explicit mode required, one of {MODES}")
    out = {key: spec[key] for key in ("name", "n_phi", "n_s", "wall_thickness_mm", "span")
           if key in spec}
    out["rows"] = {"type": rolled_cd_family.KIND, "mode": mode}
    return out


def _cd_block(block, cd_knobs):
    rows = copy.deepcopy(block["rows"])
    rows.update(type=rolled_cd_family.KIND, schema=rolled_cd_family.SCHEMA,
                implementation_sha256=rolled_cd_family.implementation_digest())
    out = {"rows": rows, "knobs": cd_knobs}
    for key in ("n_phi", "n_s", "wall_thickness_mm", "span"):
        if key in block:
            out[key] = block[key]
    return out


def _check_recipe(block):
    if not is_family_spec(block):
        raise GeneratorError("not a rolled-terminal block")
    if set(block) - set(SPEC_KEYS):
        raise GeneratorError(f"unknown rolled-terminal block key(s) {sorted(set(block) - set(SPEC_KEYS))}")
    rows = block["rows"]
    if set(rows) - {"type", "mode", "schema", "implementation_sha256", "driver"}:
        raise GeneratorError("unknown rolled-terminal rows metadata")
    if block.get("span", "quarter") != "quarter":
        raise GeneratorError("rolled-terminal family requires quarter symmetry")
    if rows.get("schema") != SCHEMA or rows.get("implementation_sha256") != implementation_digest():
        raise GeneratorError("rolled-terminal schema or implementation differs from saved recipe")
    if "knobs" not in block:
        raise GeneratorError("rolled-terminal knobs are required")


def design_params(spec, knobs, brief):
    if not is_family_spec(spec):
        raise GeneratorError("not a rolled-terminal specification")
    if set(spec) - set(SPEC_KEYS):
        raise GeneratorError("unknown rolled-terminal specification key(s)")
    cd_knobs, tm = _split(knobs)
    result = rolled_cd_family.design_params(_cd_spec(spec), cd_knobs, brief)
    block = copy.deepcopy(result["grid"])
    block["rows"].update(type=KIND, schema=SCHEMA, implementation_sha256=implementation_digest())
    block["knobs"] = {**block["knobs"], **{"g_" + key: value for key, value in tm.items()}}
    resolve_grid(block, brief)
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
    _check_recipe(block)
    cd_knobs, tm = _split(block["knobs"])
    base = rolled_cd_family.resolve_grid(_cd_block(block, cd_knobs), brief)
    if tm_kernel.is_neutral(tm):
        return base
    try:
        inner = tm_kernel.apply_to_inner(base["inner_points"], tm)
    except ValueError as exc:
        raise GeneratorError(f"rolled-terminal law: {exc}") from exc
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
    meta = dict(base["meta"])
    meta.update(construction_label=SCHEMA,
                terminal={key: float(value) for key, value in tm.items()},
                terminal_diagnostics=tm_kernel.diagnostics(base["inner_points"], tm),
                parent_construction=base["meta"].get("construction_label"),
                implementation_sha256=implementation_digest(),
                mouth_w_mm=float(extents[0]), mouth_h_mm=float(extents[1]),
                x_span_mm=float(extents[2]))
    meta["shape"] = dict(meta.get("shape") or {}, **{key: float(value) for key, value in tm.items()})
    meta.setdefault("notes", [])
    meta["notes"] = [*meta["notes"],
                     "LABELED HYPOTHESIS: H-only terminal roll-onset/C-return; no published geometry"]
    return {"inner_points": inner, "outer_points": outer, "meta": meta}


def validate_grid_params(block):
    _check_recipe(block)
    cd_knobs, _tm = _split(block["knobs"])
    rolled_cd_family.validate_grid_params(_cd_block(block, cd_knobs))


def validate_search_config(spec, seed, bounds, brief):
    if not is_family_spec(spec):
        raise GeneratorError("not a rolled-terminal specification")
    cd_seed, tm_seed = _split(seed)
    if not isinstance(bounds, dict):
        raise GeneratorError("rolled-terminal bounds must be a mapping")
    cd_bounds = {key: value for key, value in bounds.items() if key not in TM_KNOB_KEYS}
    tm_bounds = {key: value for key, value in bounds.items() if key in TM_KNOB_KEYS}
    rolled_cd_family.validate_search_config(_cd_spec(spec), cd_seed, cd_bounds, brief)
    if set(tm_bounds) != TM_KNOB_KEYS:
        raise GeneratorError(f"rolled-terminal needs explicit bounds for {sorted(TM_KNOB_KEYS)}")
    for key, bound in tm_bounds.items():
        value = tm_seed[key[2:]]
        if not bound.lo <= value <= bound.hi:
            raise GeneratorError(f"{key}: seed outside its declared bounds")
        if not bound.search and not (bound.lo == bound.hi == value):
            raise GeneratorError(f"{key}: fixed bound must equal its seed")
        if bound.log:
            raise GeneratorError("rolled-terminal knobs use explicit linear physical bounds")
        for endpoint in (bound.lo, bound.hi):
            try:
                tm_kernel.validate_tm({**tm_seed, key[2:]: float(endpoint)})
            except ValueError as exc:
                raise GeneratorError(f"rolled-terminal law at a bound: {exc}") from exc
