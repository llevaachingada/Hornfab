"""Adapter: throat sculpt (``throat-sculpt-v1``) over an ``osse_rollback`` rows parent, kind ``throat_sculpt_v1``.

LABELED HYPOTHESIS. Research lane 2026-11-25
(``docs/research/typologies/sculpted_throat_2026-11-25/``): a circular, driver-matched entrance that turns into
a directionally constricted (possibly below-source-radius, nonconvex) section and recovers into the UNCHANGED
parent body. The kernel (:mod:`_throat_sculpt_v1`) holds the laws; this module only resolves the parent, hands
the kernel a dense station set, rebuilds the grid and the 3 mm shell, and records what was achieved.

Parent: the plain ``grid`` rows kind ``osse_rollback`` (FAV / P1 split-plane Crowe-X OS-SE rollback lineage).
Its recipe is carried verbatim under ``rows.parent_rows``, so the parent identity is part of the design hash.

Neutral rule: every ts amplitude zero returns the parent's own ``rows_grid_points`` result (bit-for-bit, same
stations). Any active operator re-resolves the parent on ``DENSE_N_S`` arc stations, deforms the forward core
only, and re-stations every row with ``rows.core_step_mm`` spacing through the core. A ``ts_c2`` of 1e-9 is
therefore a pure STATION CONTROL (same surface, sculpt-style stations) for matched acoustic A/B.

Quarter span only (the radial harmonics are even cosines; the slot law is mirror-symmetric). Own module and
digest: adding it changes no existing kind's identity.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

import numpy as np

from . import _throat_sculpt_v1 as kernel
from . import cd_backbone_family, cd_backbone_rows_family
from .registry import GeneratorError

KIND = "throat_sculpt_v1"
SCHEMA = "throat-sculpt-family-v1"
PARENT_TYPES = ("osse_rollback",)
TS_KNOB_KEYS = tuple("g_" + k for k in kernel.TS_KEYS)
DENSE_N_S = 600
_ROW_META = {"type", "parent_rows", "schema", "implementation_sha256", "core_step_mm"}
LABEL = ("LABELED HYPOTHESIS: throat sculpt (angular slot delay + signed even-harmonic radial sculpt, optional "
         "area preservation) on the forward core of {parent}; downstream body unchanged; not a published construction")


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get("rows"), dict)
            and spec["rows"].get("type") == KIND)


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(kernel.__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    digest.update(f"{KIND};parents={','.join(PARENT_TYPES)};parent=grid.rows_per_azimuth".encode())
    return digest.hexdigest()


def _split(knobs):
    if not isinstance(knobs, dict):
        raise GeneratorError("throat-sculpt knobs must be a mapping")
    ts = {k: float(knobs.get("g_" + k, kernel.DEFAULTS[k])) for k in kernel.TS_KEYS}
    parent = {k: v for k, v in knobs.items() if k not in TS_KNOB_KEYS}
    try:
        kernel.validate(ts)
    except ValueError as exc:
        raise GeneratorError(f"throat-sculpt law: {exc}") from exc
    return parent, ts


def _core_step(spec):
    v = spec["rows"].get("core_step_mm", kernel.CORE_STEP_DEFAULT_MM)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.5 <= float(v) <= 10.0:
        raise GeneratorError("throat_sculpt_v1: rows.core_step_mm must be in [0.5, 10] mm")
    return float(v)


def _parent_spec(spec):
    if not is_family_spec(spec):
        raise GeneratorError("not a throat_sculpt_v1 specification")
    if spec.get("span", "quarter") != "quarter":
        raise GeneratorError("throat_sculpt_v1 requires quarter symmetry (row 0 = H, last = V)")
    parent = spec["rows"].get("parent_rows")
    if not isinstance(parent, dict) or parent.get("type") not in PARENT_TYPES:
        raise GeneratorError(f"throat_sculpt_v1 needs rows.parent_rows with type in {list(PARENT_TYPES)}")
    _core_step(spec)
    out = copy.deepcopy({k: v for k, v in spec.items() if k != "knobs"})
    out["rows"] = copy.deepcopy(parent)
    return out


def _check_recipe(block):
    _parent_spec(block)
    rows = block["rows"]
    if set(rows) - _ROW_META:
        raise GeneratorError("unknown throat_sculpt_v1 rows metadata")
    if rows.get("schema") != SCHEMA or rows.get("implementation_sha256") != implementation_digest():
        raise GeneratorError("throat_sculpt_v1 schema or implementation differs from saved recipe")
    if "knobs" not in block:
        raise GeneratorError("throat_sculpt_v1 knobs are required")


def design_params(spec, knobs, brief):
    from . import grid
    parent_knobs, ts = _split(knobs)
    pspec = _parent_spec(spec)
    block = copy.deepcopy(grid.design_params(pspec, parent_knobs, brief)["grid"])
    rows = {"type": KIND, "parent_rows": block["rows"], "schema": SCHEMA,
            "implementation_sha256": implementation_digest()}
    if "core_step_mm" in spec["rows"]:
        rows["core_step_mm"] = float(spec["rows"]["core_step_mm"])
    block["rows"] = rows
    block["knobs"] = {**block["knobs"], **{"g_" + k: float(v) for k, v in ts.items()}}
    resolve_grid(block, brief)                      # full geometry validation
    return {"grid": block}


def _parent_block(block, parent_knobs):
    out = _parent_spec(block)
    out["knobs"] = parent_knobs
    return out


def resolve_grid(block, brief):
    from . import grid
    _check_recipe(block)
    parent_knobs, ts = _split(block["knobs"])
    pblock = _parent_block(block, parent_knobs)
    pspec = {k: v for k, v in pblock.items() if k != "knobs"}
    if kernel.is_neutral(ts):
        inner, meta = grid.rows_per_azimuth(pspec, parent_knobs, brief)
        return {"inner_points": inner, "meta": meta}
    n_s = int(pspec.get("n_s", 32))
    # Parent meta at the recipe's own stations (cheap, fully validated), parent geometry from the SAME
    # analytic marches rows_per_azimuth resamples (osse_rollback: 400 samples per row plus the lip).
    _pinner, dmeta = grid.rows_per_azimuth(pspec, parent_knobs, brief)
    marches = grid._rows_marches(pspec, parent_knobs, brief)
    psis = np.asarray([m["phi"] for m in marches], dtype=float)
    if abs(psis[0]) > 1e-12 or abs(psis[-1] - 0.5 * math.pi) > 1e-9:
        raise GeneratorError("throat_sculpt_v1: parent rows must span psi 0 (H) .. 90 deg (V)")
    psis[0], psis[-1] = 0.0, 0.5 * math.pi
    rows = []
    for m in marches:
        x = np.asarray(m["x"], dtype=float)
        y = np.asarray(m["y"], dtype=float)
        if len(x) < DENSE_N_S // 2:              # a coarse march is refined by arc interpolation
            arc = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))))
            t = np.linspace(0.0, arc[-1], DENSE_N_S + 1)
            x, y = np.interp(t, arc, x), np.interp(t, arc, y)
        rows.append((x, y))
    r0 = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    try:
        new_rows, info = kernel.apply(rows, psis, ts, r0, a0, n_s, _core_step(block))
    except ValueError as exc:
        raise GeneratorError(f"throat-sculpt law: {exc}") from exc
    base_meta = {k: v for k, v in dmeta.items()
                 if k not in ("rows", "n_s", "min_self_approach_mm", "min_cross_row_distance_mm")}
    inner, meta = grid._build_rows_grid(new_rows, psis, n_s, base_meta, resample=False)
    wall = float(block.get("wall_thickness_mm", 3.0))
    try:
        outer = grid.grid_outer_points(inner, wall)
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f"throat-sculpt shell: {exc}") from exc
    for name, sheet in (("inner", inner), ("outer", outer)):
        if not np.isfinite(sheet).all():
            raise GeneratorError(f"nonfinite {name} surface")
        normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
        if np.min(np.linalg.norm(normal[:, 1:], axis=-1)) <= 1e-9:
            raise GeneratorError(f"degenerate {name} surface")
    grid.check_self_approach(inner, outer, wall)
    extents = cd_backbone_family._extents(inner, outer)
    violations = cd_backbone_rows_family._envelope(extents, brief, "report")
    parent_type = pspec["rows"]["type"]
    meta.update(construction_label=f"{SCHEMA}({parent_type})", parent_construction=parent_type,
                schema=SCHEMA, implementation_sha256=implementation_digest(),
                throat_sculpt={k: float(v) for k, v in ts.items()},
                throat_sculpt_achieved=info,
                throat_radius_mm=float(np.hypot(inner[0, 0, 0], inner[0, 0, 1])),
                mouth_w_mm=extents[0], mouth_h_mm=extents[1], x_span_mm=extents[2],
                L_mm=float(np.max(inner[..., 2])), x_min_mm=float(np.min(inner[..., 2])),
                x_max_mm=float(np.max(inner[..., 2])),
                envelope_violations=violations, envelope_ok=not violations)
    meta["notes"] = [*meta.get("notes", []), LABEL.format(parent=parent_type)]
    return {"inner_points": inner, "outer_points": outer, "meta": meta}


def validate_grid_params(block):
    from . import grid
    _check_recipe(block)
    parent_knobs, _ts = _split(block["knobs"])
    grid.validate_grid_params(_parent_block(block, parent_knobs))


def validate_search_config(spec, seed, bounds, brief):
    from . import grid
    pspec = _parent_spec(spec)
    parent_seed, ts_seed = _split(seed)
    grid.design_params(pspec, {k: v for k, v in parent_seed.items()}, brief)
    ts_bounds = {k: b for k, b in bounds.items() if k in TS_KNOB_KEYS}
    for key, b in ts_bounds.items():
        name = key[len("g_"):]
        value = ts_seed[name]
        if not b.lo <= value <= b.hi:
            raise GeneratorError(f"{key}: seed outside its declared bounds")
        if not b.search and not (b.lo == b.hi == value):
            raise GeneratorError(f"{key}: fixed bound must equal its seed")
        if b.log:
            raise GeneratorError("throat-sculpt knobs use explicit linear bounds")
        if b.search and name == "ts_area":
            raise GeneratorError("ts_area is a 0/1 policy switch; pin it per lane")
        try:
            for endpoint in (b.lo, b.hi):
                kernel.validate({**ts_seed, name: float(endpoint)})
        except ValueError as exc:
            raise GeneratorError(f"throat-sculpt law at a bound: {exc}") from exc

    def searched(names):
        return any(("g_" + n) in ts_bounds and ts_bounds["g_" + n].search for n in names)

    def pinned_zero(names):
        return not searched(names) and all(ts_seed[n] == 0.0 for n in names)
    if searched(("ts_on_mm", "ts_rise_mm", "ts_fall_mm")) and pinned_zero(kernel.RADIAL_AMP):
        raise GeneratorError("ts_on/rise/fall are dormant when every radial amplitude is pinned at zero; pin them")
    if searched(("ts_slot_pow", "ts_slot_span_mm")) and pinned_zero(kernel.SLOT_AMP):
        raise GeneratorError("ts_slot_pow/span are dormant when every slot depth is pinned at zero; pin them")
