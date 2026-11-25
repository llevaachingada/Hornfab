"""GeneratedSpace: the search box over TYPOLOGY GENERATOR knobs (docs/TYPOLOGY_PLAN.md s5).

Same interface as ``DesignSpace`` (``family``, ``seed``, ``bounds``, ``keys``, ``normalize``,
``denormalize``), so CMA-ES and the pipeline are unchanged. The search vector holds generator
knobs (alphabetical, like DesignSpace); ``denormalize`` materialises them into an ordinary FREEFORM
``Design`` via the module dispatch in :func:`materialize` (``generators.registry.materialize`` for
typologies, ``generators.grid.design_params`` for ``name: grid``). The design hash is the geometry
(the recipe for a grid), so equal shapes from different knobs deduplicate.

``denormalize`` never raises for bad knobs: a knob vector that gives no legal horn (envelope,
tractrix mouth smaller than the throat, ...) becomes a Design carrying ``_generator_error``, which
``search/evaluate.py`` scores as ``invalid_geometry`` (CMA-ES must not crash on a corner).
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import math

import numpy as np

from ..types import Design, GeometryInvalidError
from .generators import grid as grid_gen
from .generators import registry
from .space import Bound, _ROUND_DECIMALS

log = logging.getLogger("hornlab_search.design.generated")

GENERATOR_ERROR_KEY = "_generator_error"
#: Relative pre-mesh envelope overshoot carried alongside an ``invalid_envelope`` error.
#: ABSENT on every legal design (and on non-envelope generator errors): search/evaluate.py
#: reads ``params.get(GENERATOR_OVERSHOOT_KEY)`` only to grade the penalty.
GENERATOR_OVERSHOOT_KEY = "_generator_overshoot"
#: Cap on the stored overshoot.  ``graded_infeasible_penalty`` saturates at 2e3 for an
#: overshoot of 10, so larger values carry no extra ranking information.
_MAX_STORED_OVERSHOOT = 10.0


def brief_hash(brief: dict) -> str:
    body = {k: v for k, v in brief.items() if k != "path"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def materialize(gen: dict, knobs: dict, brief: dict) -> dict:
    """Generator block + knobs -> Design params, dispatching on the block's ``name``.

    ``name: grid`` is the WP10 point-grid adapter: its params are the compact surface spec plus the
    knob recipe (``{"grid": {...}}``), NOT FREEFORM anchors, because the grid is evaluated at mesh
    time by ``mesh/grid_build.py``. Every other name keeps the typology path (FREEFORM anchors).
    """
    if str(gen.get("name", "")) == "grid":
        return grid_gen.design_params(gen, knobs, brief)
    if str(gen.get("name", "")) == "plughorn":
        return plughorn_params(gen, knobs, brief)
    if str(gen.get("name", "")) == "meh":
        return meh_params(gen, knobs, brief)
    from .generators import crowe_hv_area_aspect_v1
    if str(gen.get("name", "")) == crowe_hv_area_aspect_v1.KIND:
        from ..config import brief_for_envelope_adapter
        return crowe_hv_area_aspect_v1.materialize(gen, knobs, brief_for_envelope_adapter(brief))
    return registry.materialize(gen, knobs, brief)


class GeneratorRecipeError(ValueError):
    """A persisted generator provenance recipe cannot be proven against the configured task.

    Raised by :func:`design_from_recipe`; it always means "refuse the historical record", never
    "clip it into range" or "recover knobs from geometry". ``GeneratedSpace.normalize`` cannot
    invert geometry, so a durable generated-space intake must carry the recorded recipe.
    """


def design_from_recipe(space, recipe: dict, *, expected_design_hash: str,
                       brief: dict | None = None) -> Design:
    """Rebuild a historical generated-space Design from its persisted provenance recipe.

    ``recipe`` is the ``provenance.generator`` block written by
    :meth:`GeneratedSpace.provenance` and reduced by ``search/evaluate.py`` to
    ``{name, spec, knobs, brief, brief_hash}``. This is the durable intake path for generated
    tasks (grid rows, typologies, CAD recipes): ``Design.params`` alone is a recipe, not an
    invertible continuous vector.

    Validation is deliberately fail-closed and happens BEFORE conversion:

    * the recipe must carry a ``spec`` mapping, a ``knobs`` mapping and a ``brief_hash``;
    * the recorded spec must equal the configured generator spec exactly (a changed recipe is
      refused, including ``rows``/``n_phi``/``wall_thickness_mm`` and any generator ``fixed``
      block);
    * the recorded ``brief_hash`` must equal the resolved task brief's hash;
    * the knob key set must equal the configured generator's knob key set exactly (neither a
      missing nor an extra key is accepted);
    * every knob must be a finite scalar; pinned (``search: false``, ``lo == hi``) knobs must
      equal the configured fixed value exactly, and searched knobs must lie inside their
      resolved bound (no clipping);
    * the knobs must materialise a legal horn and reproduce ``expected_design_hash`` exactly.

    On success the exact knob vector is attached to ``space``'s recipe cache so the subsequent
    :class:`~hornlab_search.bo.encoding.ActiveProjection` round-trip reads the recipe rather than
    trying to invert geometry. Any failure raises :class:`GeneratorRecipeError`.
    """
    if not isinstance(space, GeneratedSpace):
        raise GeneratorRecipeError("recipe intake requires a generated task space")
    if not isinstance(recipe, dict):
        raise GeneratorRecipeError(f"generator recipe is {type(recipe).__name__}, not a mapping")
    spec, knobs = recipe.get("spec"), recipe.get("knobs")
    if not isinstance(spec, dict) or not isinstance(knobs, dict):
        raise GeneratorRecipeError("generator recipe needs both a spec mapping and a knobs mapping")
    recorded_brief = recipe.get("brief_hash")
    if not isinstance(recorded_brief, str) or not recorded_brief:
        raise GeneratorRecipeError("generator recipe has no brief_hash proof")
    resolved_brief = dict(space.brief if brief is None else brief)
    if brief_hash(resolved_brief) != recorded_brief:
        raise GeneratorRecipeError(
            "generator recipe brief_hash differs from the configured task brief "
            f"({recorded_brief!r} != {brief_hash(resolved_brief)!r})")
    if spec != space.gen:
        raise GeneratorRecipeError(
            "generator recipe spec differs from the configured task generator block")
    name = recipe.get("name")
    if name is not None and str(name) != str(space.gen.get("name", "typology")):
        raise GeneratorRecipeError(
            f"generator recipe name {name!r} differs from configured {space.gen.get('name')!r}")

    expected_keys = set(space.seed_knobs)
    got_keys = set(knobs)
    if got_keys != expected_keys:
        missing = sorted(expected_keys - got_keys)
        extra = sorted(got_keys - expected_keys)
        raise GeneratorRecipeError(
            f"generator recipe knob set differs from the configured task (missing={missing}, "
            f"extra={extra})")

    validated: dict[str, float] = {}
    for key in sorted(knobs):
        value = knobs[key]
        if isinstance(value, (list, tuple)):
            raise GeneratorRecipeError(
                f"generator knob {key!r} is list-valued; the continuous intake cannot encode it")
        if isinstance(value, bool):
            raise GeneratorRecipeError(f"generator knob {key!r} is boolean, not a finite number")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise GeneratorRecipeError(
                f"generator knob {key!r} is not a finite number ({value!r})") from None
        if not math.isfinite(number):
            raise GeneratorRecipeError(f"generator knob {key!r} is not finite ({value!r})")
        bound = space.bounds.get(key)
        if bound is None:
            raise GeneratorRecipeError(f"generator knob {key!r} has no resolved bound")
        if bound.hi == bound.lo:
            if number != float(bound.lo):
                raise GeneratorRecipeError(
                    f"pinned generator knob {key!r} changed: recipe {number!r} != configured "
                    f"fixed value {float(bound.lo)!r}")
        else:
            _, clipped = bound.to_unit(number)
            if clipped:
                raise GeneratorRecipeError(
                    f"generator knob {key!r}={number!r} is outside its resolved bound "
                    f"[{bound.lo}, {bound.hi}]; historical observations are never clipped")
        validated[key] = number

    try:
        params = materialize(space.gen, validated, resolved_brief)
    except Exception as exc:  # noqa: BLE001 - a bad recipe is a typed refusal
        raise GeneratorRecipeError(
            f"generator recipe does not materialise a legal horn: {exc}") from exc
    design = Design("FREEFORM", params)
    if design.hash() != str(expected_design_hash):
        raise GeneratorRecipeError(
            f"re-materialised design hash {design.hash()} != recorded {expected_design_hash}")
    # Make the recipe directly available to ActiveProjection; geometry cannot be inverted.
    space._knobs_by_hash[design.hash()] = dict(validated)
    return design


def generator_info(gen: dict, knobs: dict, brief: dict) -> dict:
    """Report-only derived quantities for a generator block, never raising."""
    from .generators import crowe_hv_area_aspect_v1
    if str(gen.get("name", "")) == crowe_hv_area_aspect_v1.KIND:
        try:
            return crowe_hv_area_aspect_v1.info(gen, knobs, brief)
        except Exception:  # noqa: BLE001 - report-only
            return {}
    return registry.info(gen, knobs, brief)


def plughorn_params(gen: dict, knobs: dict, brief: dict) -> dict:
    """``name: plughorn`` -> ``{"cad": recipe}`` for ``tools/cad/plughorn.py`` (2026-10-28).

    Recipe = the tool's documented DEFAULTS, overridden by ``generator.fixed`` and then by the knobs
    (knob names ARE the tool's keys, e.g. ``h_angle2_deg``). Every key is written, so the recipe is
    explicit and the design hash is the geometry. The tool's own validation (ranges, plug clearance)
    runs here, and the outer size is checked against the brief envelope, so an illegal knob vector
    becomes ``invalid_geometry`` / ``invalid_envelope`` before any mesh.
    """
    from dataclasses import asdict

    from ..mesh import step_build                   # lazy: mesh imports the design package
    tool = step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL)
    recipe = dict(asdict(tool.DEFAULTS))
    fixed = dict(gen.get("fixed") or {})
    for src in (fixed, knobs):
        unknown = sorted(set(src) - set(recipe))
        if unknown:
            raise ValueError(f"plughorn: unknown key(s) {unknown}")
        recipe.update({k: float(v) for k, v in src.items()})
    for k in tool.INT_KEYS:
        recipe[k] = int(round(recipe[k]))
    params = tool.params_from_recipe(recipe)          # raises ValueError on a bad shape
    d = params.derived()
    _check_cad_envelope("plughorn", (d["outer_w_mm"], d["outer_h_mm"], d["depth_total_mm"]), brief)
    return {"cad": {"tool": step_build.PLUGHORN_TOOL, **recipe}}


def meh_params(gen: dict, knobs: dict, brief: dict) -> dict:
    """``name: meh`` -> ``{"cad": recipe}`` for ``tools/cad/meh.py`` (MEH, 2026-10-30).

    Recipe = the tool's documented defaults (C9), overridden by ``generator.fixed`` and then by
    the knobs (knob names ARE the tool's keys). Every key is written, so the design hash is the
    geometry. The tool's own ``derived()`` runs the layout check and the deterministic slide
    repair here; a non-empty ``reasons`` list is an illegal horn (``invalid_geometry`` before any
    mesh). The mouth and depth are checked against the brief envelope.
    """
    from ..mesh import step_build                   # lazy: mesh imports the design package
    tool = step_build.load_cad_tool(tool=step_build.MEH_TOOL)
    recipe = dict(tool.defaults())
    fixed = dict(gen.get("fixed") or {})
    for src in (fixed, knobs):
        unknown = sorted(set(src) - set(recipe))
        if unknown:
            raise ValueError(f"meh: unknown key(s) {unknown}")
        recipe.update(src)
    for key in ("cov_h_deg", "cov_v_deg", "z_frac", "across_frac", "port_along_mm", "slide_mm"):
        recipe[key] = float(recipe[key])
    for key in ("env_w_mm", "env_h_mm", "env_d_mm", "box_t_mm", "roll_mm", "wall_t_mm",
                "spacer_mm", "exit_mm", "cd_duct_mm", "cd_body_d_mm", "cd_body_len_mm",
                "cone_cutout_mm", "cone_depth_mm", "clearance_mm"):
        recipe[key] = float(recipe[key])
    recipe["walls"] = str(recipe["walls"])
    d = tool.derived(recipe)                        # the tool's own validation + repair
    reasons = list(d.get("reasons") or [])
    if reasons:
        raise ValueError(f"meh: layout infeasible: {reasons}")
    _check_cad_envelope("meh", (d["mouth_w"], d["mouth_h"], recipe["env_d_mm"]), brief)
    return {"cad": {"tool": step_build.MEH_TOOL, **recipe}}


def _check_cad_envelope(tool: str, dimensions_mm, brief: dict) -> None:
    from ..config import ENVELOPE_AXES, envelope_policy

    policy = envelope_policy(brief)
    tolerance = 0.5 if policy.mode == "production" else 0.0
    for key, actual, limit in zip(ENVELOPE_AXES, dimensions_mm, policy.candidate_limits_mm):
        if float(actual) > min(limit + tolerance, policy.sanity_max_mm):
            raise ValueError(f"invalid_envelope: {tool}: {key} {actual:.1f} mm "
                             f"exceeds the {policy.mode} envelope {limit:g} mm")


class GeneratedSpace:
    family = "FREEFORM"

    def __init__(self, gen: dict, brief: dict, seed_knobs: dict, bounds: dict[str, Bound]):
        self.gen = dict(gen)
        self.brief = dict(brief)
        self.bounds = dict(bounds)
        from .generators import (rolled_family, rolled_cd_family, cd_backbone_family, cd_backbone_rows_family, rim_beak_family, rolled_terminal_family, klangfilm_lame_family, klangfilm_lame_hv_family, klangfilm_lame_hv_core_family,
                                lecleach_swept_hv, sculpted_rosse_family, crowe_hv_area_aspect_v1, record_body)
        for family in (rolled_family, rolled_cd_family, cd_backbone_family, cd_backbone_rows_family, rim_beak_family, rolled_terminal_family, klangfilm_lame_family, klangfilm_lame_hv_family, klangfilm_lame_hv_core_family,
                       lecleach_swept_hv, sculpted_rosse_family, crowe_hv_area_aspect_v1, record_body):
            if family.is_family_spec(self.gen):
                family.validate_search_config(self.gen, seed_knobs, self.bounds, self.brief)
                break
        # Harmonic stop-law knobs are JSON lists of floats (grid rows); every other
        # generator knob is a scalar. Keep both forms (a list must not be float()ed).
        knobs = {}
        for k, v in (seed_knobs or {}).items():
            if isinstance(v, (list, tuple)):
                knobs[k] = [float(x) for x in v]
            else:
                knobs[k] = float(v)
        for k in sorted(self.bounds):
            b = self.bounds[k]
            if b.search and k not in knobs:
                knobs[k] = b.midpoint()
                log.warning("generator seed lacks knob %s; filled with the bound midpoint", k)
        self.seed_knobs = knobs
        try:
            params = materialize(self.gen, knobs, self.brief)
        except Exception as exc:  # the SEED must be legal: stop with a clear message
            raise GeometryInvalidError(f"generator seed is not a legal horn: {exc}") from exc
        self.seed = Design("FREEFORM", params)
        self._knobs_by_hash = {self.seed.hash(): dict(knobs)}

    @classmethod
    def from_config(cls, cfg) -> "GeneratedSpace":
        bounds = {str(k): Bound(lo=float(b["lo"]), hi=float(b["hi"]), search=bool(b.get("search", True)),
                                log=bool(b.get("log", False))) for k, b in cfg.bounds_raw.items()}
        return cls(cfg.generator, cfg.brief, dict(cfg.seed_params), bounds)

    def keys(self) -> list[str]:
        return sorted(k for k, b in self.bounds.items() if b.search)

    def knobs_from_unit(self, x) -> dict:
        x = np.clip(np.asarray(x, dtype=float).reshape(-1), 0.0, 1.0)
        keys = self.keys()
        if x.size != len(keys):
            raise ValueError(f"expected a vector of length {len(keys)}, got {x.size}")
        knobs = dict(self.seed_knobs)
        for k, xi in zip(keys, x):
            knobs[k] = round(self.bounds[k].from_unit(float(xi)), _ROUND_DECIMALS)
        return self.apply_knob_links(knobs)

    #: ``search.links`` resolved for this space (stage 0 WP 0.2, 2026-11-17); None = no links.
    links: dict | None = None

    def apply_knob_links(self, knobs: dict) -> dict:
        """Compute linked generator knobs from their parents in KNOB space (before
        ``materialize``): ``v = scale * parent + offset`` clipped to ``[min, max]``. Without
        links the same dict is returned (default path byte-identical)."""
        if not self.links:
            return knobs
        out = dict(knobs)
        for knob in sorted(self.links):
            spec = self.links[knob]
            v = float(out[spec["from"]]) * float(spec["scale"]) + float(spec["offset"])
            out[knob] = round(min(max(v, float(spec["min"])), float(spec["max"])), _ROUND_DECIMALS)
        return out

    def design_from_knobs(self, knobs: dict) -> Design:
        from ..config import envelope_policy

        policy = envelope_policy(self.brief)
        try:
            params = materialize(self.gen, knobs, self.brief)
        except Exception as exc:  # noqa: BLE001 - scored as invalid_geometry in evaluate
            params = {GENERATOR_ERROR_KEY: f"{type(exc).__name__}: {exc}",
                      "_knobs": {k: knobs[k] for k in sorted(knobs)}}
        if GENERATOR_ERROR_KEY not in params and policy.mode == "production":
            # Pre-mesh envelope estimate. ``materialize`` checks the INNER mouth; this catches
            # the outer shell offset the post-mesh bounding box includes, so an envelope
            # violation is scored (invalid_envelope) without paying for a mesh. The happy path
            # adds nothing: no overshoot key is present when the estimate is 0.
            try:
                overshoot = registry.envelope_overshoot_estimate(params, self.brief)
            except Exception:  # noqa: BLE001 - an estimate must never turn a legal knob invalid
                log.debug("pre-mesh envelope estimate failed", exc_info=True)
                overshoot = None
            if overshoot is not None and overshoot > 0.0:
                value = min(max(float(overshoot), 0.0), _MAX_STORED_OVERSHOOT)
                params = {**params,
                          GENERATOR_ERROR_KEY: (
                              "invalid_envelope: estimated outside the brief envelope "
                              f"(max relative overshoot {value:.4f})"),
                          GENERATOR_OVERSHOOT_KEY: float(value),
                          "_knobs": {k: knobs[k] for k in sorted(knobs)}}
        d = Design("FREEFORM", params)
        # last-wins: provenance then names the knobs of the candidate actually being evaluated
        # (two knob vectors can round to the same anchors); CMA never normalizes loop candidates.
        self._knobs_by_hash[d.hash()] = dict(knobs)
        return d

    def denormalize(self, x) -> Design:
        return self.design_from_knobs(self.knobs_from_unit(x))

    def normalize(self, d: Design) -> np.ndarray:
        """Design -> [0,1]^k for a design this space produced (the seed or a denormalized
        vector). Geometry cannot be inverted to knobs, so any other design raises."""
        knobs = self.knobs_for(d)
        if knobs is None:
            raise ValueError("GeneratedSpace.normalize: design was not produced by this space "
                             "(generator knobs cannot be recovered from geometry)")
        return np.array([self.bounds[k].to_unit(float(knobs[k]))[0] for k in self.keys()], dtype=float)

    def knobs_for(self, d: Design) -> dict | None:
        k = self._knobs_by_hash.get(d.hash())
        if k is None:
            from .generators import rolled_family, rolled_cd_family, cd_backbone_family, cd_backbone_rows_family, rim_beak_family, rolled_terminal_family, klangfilm_lame_family, klangfilm_lame_hv_family, klangfilm_lame_hv_core_family, lecleach_swept_hv, sculpted_rosse_family
            block = d.params.get('grid') if isinstance(d.params, dict) else None
            for family in (rolled_family, rolled_cd_family, cd_backbone_family, cd_backbone_rows_family, rim_beak_family, rolled_terminal_family, klangfilm_lame_family, klangfilm_lame_hv_family, klangfilm_lame_hv_core_family, lecleach_swept_hv, sculpted_rosse_family):
                if family.is_family_spec(block) and family.is_family_spec(self.gen):
                    from ..config import brief_for_envelope_adapter
                    family.resolve_grid(block, brief_for_envelope_adapter(self.brief))
                    candidate = block.get('knobs')
                    if not isinstance(candidate, dict) or set(candidate) != set(self.seed_knobs):
                        raise ValueError('saved family knob set differs from configured task')
                    rebuilt = Design('FREEFORM', materialize(self.gen, candidate, self.brief))
                    if rebuilt.hash() != d.hash():
                        raise ValueError('saved family recipe differs from configured task')
                    k = candidate
                    self._knobs_by_hash[d.hash()] = dict(k)
                    break
        return None if k is None else copy.deepcopy(k)

    def provenance(self, d: Design) -> dict | None:
        knobs = self.knobs_for(d)
        if knobs is None:
            return None
        return {"name": self.gen.get("name", "typology"), "spec": copy.deepcopy(self.gen),
                "knobs": knobs, "brief": self.brief.get("name"), "brief_hash": brief_hash(self.brief),
                "derived": generator_info(self.gen, knobs, self.brief),
                # WP 0.9 (2026-11-17): additive, NON-identity recipe metadata (never hashed).
                "recipe_meta": self._recipe_meta(d, knobs)}

    def _recipe_meta(self, d: Design, knobs: dict) -> dict:
        """Termination kind, mesher wall thickness and resolved source cap; never raises."""
        from .recipe_meta import recipe_metadata
        mounting = self.brief.get("mounting")
        mounting = mounting if isinstance(mounting, dict) and mounting else None
        inner = meta = None
        block = d.params.get("grid") if isinstance(d.params, dict) else None
        if isinstance(block, dict):
            try:
                if "rows" in block:
                    spec = {k: v for k, v in block.items() if k != "knobs"}
                    inner, meta = grid_gen.rows_grid_points(spec, block.get("knobs") or {}, self.brief)
                else:
                    spec = {k: block[k] for k in grid_gen.GRID_SPEC_KEYS if k in block}
                    inner, meta = grid_gen.grid_points(spec, block.get("knobs") or {}, self.brief)
            except Exception:  # noqa: BLE001 - metadata only
                inner = meta = None
        return recipe_metadata(d, mounting=mounting, gen={"spec": self.gen}, grid_inner=inner,
                               grid_meta=meta)
