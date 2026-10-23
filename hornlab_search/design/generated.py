"""GeneratedSpace: the search box over TYPOLOGY GENERATOR knobs (docs/TYPOLOGY_PLAN.md s5).

Same interface as ``DesignSpace`` (``family``, ``seed``, ``bounds``, ``keys``, ``normalize``,
``denormalize``), so CMA-ES and the pipeline are unchanged. The search vector holds generator
knobs (alphabetical, like DesignSpace); ``denormalize`` materialises them into an ordinary FREEFORM
``Design`` via ``generators.registry.materialize``. The design hash is the geometry, so equal shapes
from different knobs deduplicate.

``denormalize`` never raises for bad knobs: a knob vector that gives no legal horn (envelope,
tractrix mouth smaller than the throat, ...) becomes a Design carrying ``_generator_error``, which
``search/evaluate.py`` scores as ``invalid_geometry`` (CMA-ES must not crash on a corner).
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging

import numpy as np

from ..types import Design, GeometryInvalidError
from .generators import registry
from .space import Bound, _ROUND_DECIMALS

log = logging.getLogger("hornlab_search.design.generated")

GENERATOR_ERROR_KEY = "_generator_error"


def brief_hash(brief: dict) -> str:
    body = {k: v for k, v in brief.items() if k != "path"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


class GeneratedSpace:
    family = "FREEFORM"

    def __init__(self, gen: dict, brief: dict, seed_knobs: dict, bounds: dict[str, Bound]):
        self.gen = dict(gen)
        self.brief = dict(brief)
        self.bounds = dict(bounds)
        knobs = {k: float(v) for k, v in (seed_knobs or {}).items()}
        for k in sorted(self.bounds):
            b = self.bounds[k]
            if b.search and k not in knobs:
                knobs[k] = b.midpoint()
                log.warning("generator seed lacks knob %s; filled with the bound midpoint", k)
        self.seed_knobs = knobs
        try:
            params = registry.materialize(self.gen, knobs, self.brief)
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
        return knobs

    def design_from_knobs(self, knobs: dict) -> Design:
        try:
            params = registry.materialize(self.gen, knobs, self.brief)
        except Exception as exc:  # noqa: BLE001 - scored as invalid_geometry in evaluate
            params = {GENERATOR_ERROR_KEY: f"{type(exc).__name__}: {exc}",
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
        knobs = self._knobs_by_hash.get(d.hash())
        if knobs is None:
            raise ValueError("GeneratedSpace.normalize: design was not produced by this space "
                             "(generator knobs cannot be recovered from geometry)")
        return np.array([self.bounds[k].to_unit(float(knobs[k]))[0] for k in self.keys()], dtype=float)

    def knobs_for(self, d: Design) -> dict | None:
        k = self._knobs_by_hash.get(d.hash())
        return None if k is None else copy.deepcopy(k)

    def provenance(self, d: Design) -> dict | None:
        knobs = self.knobs_for(d)
        if knobs is None:
            return None
        return {"name": self.gen.get("name", "typology"), "spec": copy.deepcopy(self.gen),
                "knobs": knobs, "brief": self.brief.get("name"), "brief_hash": brief_hash(self.brief),
                "derived": registry.info(self.gen, knobs, self.brief)}
