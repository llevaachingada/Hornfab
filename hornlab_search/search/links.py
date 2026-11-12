"""B.2 (day 2026-11-12): linked knobs — ``search.links``.

``links: {<knob>: {from: <parent>, scale: a, offset: b, min: .., max: ..}}`` removes the linked
knob from the CMA-ES dimension and computes it from its parent BEFORE meshing
(``v = scale * parent + offset``, clipped to ``[min, max]``, which defaults to the knob's own
bound ``[lo, hi]``). One level only (a parent may itself not be linked, which also excludes
cycles); unknown knobs are a ConfigError at load. The linked knob's value in the seed params is
ignored with a warning (the computed value wins everywhere, including the seed evaluation).

Absent ``search.links`` = today's behaviour byte for byte: ``reduce_space`` returns the given
space unchanged and ``apply_links`` returns the given design unchanged.
"""
from __future__ import annotations

import copy
import dataclasses
import logging

from ..design import families
from ..design.space import DesignSpace, Bound
from ..types import Design

log = logging.getLogger("hornlab_search.search.links")

_ROUND_DECIMALS = 10       # same value rounding as DesignSpace.denormalize


def reduce_space(space, cfg) -> tuple[object, dict | None]:
    """(space, resolved_links). With ``search.links`` configured, a NEW DesignSpace whose
    linked knobs have ``search: False`` (removed from the CMA dimension, bounds kept for
    clipping); the seed's stale values for them are ignored with a warning. Without the key,
    ``(space, None)`` — the same object, default behaviour untouched."""
    links = getattr(getattr(cfg, "search", None), "links", None)
    if not links:
        return space, None
    if getattr(cfg, "generator", None):
        raise ValueError("search.links is not supported with a generator block")
    bounds = dict(space.bounds)
    for knob in sorted(links):
        b = bounds[knob]
        bounds[knob] = Bound(lo=b.lo, hi=b.hi, search=False, log=b.log)
    params = copy.deepcopy(space.seed.params)
    stale = []
    for knob in sorted(links):
        try:
            families.param_get(space.family, params, knob)
            stale.append(knob)
        except KeyError:
            pass
    if stale:
        log.warning("search.links: the seed's own value(s) for linked knob(s) %s are ignored "
                    "(computed from the parent)", stale)
    reduced = DesignSpace(family=space.family, seed=Design(space.family, params),
                          bounds=bounds)
    return reduced, _resolved(space, links)


def _resolved(space, links) -> dict:
    """The run.json block: the links with the DEFAULTS (missing min/max) filled from the
    knob's own bound, so the record is complete without re-deriving it."""
    out = {}
    for knob, spec in links.items():
        b = space.bounds[knob]
        out[knob] = {"from": spec["from"], "scale": float(spec.get("scale", 1.0)),
                     "offset": float(spec.get("offset", 0.0)),
                     "min": float(spec.get("min", b.lo)), "max": float(spec.get("max", b.hi))}
    return out


def apply_links(design: Design, space, cfg) -> Design:
    """Compute every linked knob from its parent (``scale * parent + offset``, clipped to
    ``[min, max]``) BEFORE meshing. Returns a NEW Design (the candidate is never mutated); with
    no links the SAME design object is returned (zero cost, default path byte-identical)."""
    links = getattr(getattr(cfg, "search", None), "links", None)
    if not links:
        return design
    params = dict(design.params)            # shallow copy: the candidate object stays untouched
    for knob in sorted(links):
        spec = links[knob]
        parent = families.param_get(design.family, params, spec["from"])
        v = float(parent) * float(spec.get("scale", 1.0)) + float(spec.get("offset", 0.0))
        lo, hi = float(spec.get("min", space.bounds[knob].lo)), \
            float(spec.get("max", space.bounds[knob].hi))
        v = min(max(v, lo), hi)
        families.param_set(design.family, params, knob,
                           round(v, _ROUND_DECIMALS))
    return Design(design.family, params)
