"""DesignSpace: the bounded search box and the [0,1]^k <-> Design map (01_CONTRACTS section 5).

The search vector order is the ALPHABETICAL order of the searchable keys, never the YAML key
order, so reordering a YAML file cannot silently permute the CMA-ES vector of a resumed run.
"""
from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass

import numpy as np

from ..types import Design, GeometryInvalidError
from . import families

log = logging.getLogger("hornlab_search.design.space")

# Denormalized values are rounded to this many decimals. The Design hash canonicalizes top-level
# floats to 9 decimals but leaves floats nested inside lists of dicts (FREEFORM crossSections)
# untouched, so 1e-16 round-trip noise would otherwise change a hash.
_ROUND_DECIMALS = 10


@dataclass(frozen=True)
class Bound:
    lo: float
    hi: float
    search: bool = True
    log: bool = False          # search in log space, for scale-like params

    def __post_init__(self):
        lo, hi = float(self.lo), float(self.hi)
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise ValueError(f"Bound needs finite lo/hi, got lo={self.lo!r} hi={self.hi!r}")
        if hi < lo:
            raise ValueError(f"Bound hi < lo: lo={lo!r} hi={hi!r}")
        if self.log and lo <= 0:
            raise ValueError(f"log=True bounds require lo > 0, got lo={lo!r}")
        if self.search and hi == lo:
            raise ValueError(
                f"a searchable Bound needs lo < hi (got both {lo!r}); set search: false to pin it")

    # -- the 1-D map, in one place
    def _fwd(self, v: float) -> float:
        return math.log10(v) if self.log else v

    def _inv(self, u: float) -> float:
        return 10.0 ** u if self.log else u

    def to_unit(self, v: float) -> tuple[float, bool]:
        """(value in [0,1], was_clipped)."""
        lo, hi = self._fwd(float(self.lo)), self._fwd(float(self.hi))
        if self.log and v <= 0:
            return 0.0, True
        u = (self._fwd(float(v)) - lo) / (hi - lo)
        c = min(1.0, max(0.0, u))
        return c, (c != u)

    def from_unit(self, x: float) -> float:
        lo, hi = self._fwd(float(self.lo)), self._fwd(float(self.hi))
        x = min(1.0, max(0.0, float(x)))
        return self._inv(lo + x * (hi - lo))

    def midpoint(self) -> float:
        return self.from_unit(0.5)


def _to_python(v):
    return float(v) if isinstance(v, (np.floating,)) else (int(v) if isinstance(v, np.integer) else v)


@dataclass
class DesignSpace:
    family: str
    seed: Design
    bounds: dict[str, Bound]

    def __post_init__(self):
        if self.seed.family != self.family:
            raise GeometryInvalidError(
                f"seed family {self.seed.family!r} != space family {self.family!r}")
        table = families.FAMILY_KEYS[self.family]
        # Every bound key must be a legal key of the family (or a path into one).
        for key in self.bounds:
            if families.root_key(key) not in table and not (
                    self.family == "FREEFORM" and key in families.FREEFORM_ALIASES):
                raise GeometryInvalidError(
                    f"{self.family}: bounds key '{key}' is not a legal {self.family} key")
        # A searchable key absent from the seed is filled with the bound midpoint (log-mid for
        # log bounds) and logged. This changes the seed geometry, so it is a WARNING, and the
        # filled seed is what normalize/denormalize use thereafter.
        params = copy.deepcopy(self.seed.params)
        filled = []
        for key in sorted(self.bounds):
            b = self.bounds[key]
            if not b.search:
                continue
            try:
                families.param_get(self.family, params, key)
            except KeyError:
                if "." in key and families.root_key(key) in params:
                    raise GeometryInvalidError(
                        f"{self.family}: bounds key '{key}' points into the seed but the path "
                        "does not exist") from None
                if key in families.FREEFORM_ALIASES and self.family == "FREEFORM":
                    raise GeometryInvalidError(
                        f"{self.family}: bounds key '{key}' needs a superellipse station in "
                        "crossSections") from None
                params[key] = b.midpoint()
                filled.append(key)
        if filled:
            log.warning("seed lacks searchable key(s) %s; filled with the bound midpoint "
                        "(this changes the seed geometry)", filled)
        self.seed = Design(self.family, params)

    # ------------------------------------------------------------------ vector
    def keys(self) -> list[str]:
        """Searchable keys, SORTED ALPHABETICALLY. This order IS the CMA-ES vector order and
        must never depend on YAML key order."""
        return sorted(k for k, b in self.bounds.items() if b.search)

    def normalize(self, d: Design) -> np.ndarray:
        """Design -> [0,1]^k. Out-of-bounds values are CLIPPED (never raised) and logged."""
        keys = self.keys()
        x = np.empty(len(keys), dtype=float)
        for i, k in enumerate(keys):
            v = families.param_get(self.family, d.params, k)
            u, clipped = self.bounds[k].to_unit(float(v))
            if clipped:
                b = self.bounds[k]
                log.warning("normalize: %s=%r outside [%r, %r]; clipped", k, v, b.lo, b.hi)
            x[i] = u
        return x

    def denormalize(self, x: np.ndarray) -> Design:
        """[0,1]^k -> Design. x is clipped first. Non-searched keys keep the SEED's values."""
        keys = self.keys()
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size != len(keys):
            raise ValueError(f"expected a vector of length {len(keys)}, got {x.size}")
        x = np.clip(x, 0.0, 1.0)
        params = copy.deepcopy(self.seed.params)
        table = families.FAMILY_KEYS[self.family]
        for k, xi in zip(keys, x):
            val = self.bounds[k].from_unit(float(xi))
            spec = table.get(families.root_key(k))
            if spec is not None and spec.kind is int and k == families.root_key(k):
                val = int(round(val))
            else:
                val = round(val, _ROUND_DECIMALS)
            families.param_set(self.family, params, k, _to_python(val))
        return Design(self.family, params)

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_config(cls, cfg) -> "DesignSpace":
        """Build from a hornlab_search.config.Config (seed_params + bounds_raw). A config with a
        ``generator:`` block gets a GeneratedSpace (same interface, knobs -> FREEFORM design)."""
        if getattr(cfg, "generator", None):
            from .generated import GeneratedSpace
            return GeneratedSpace.from_config(cfg)
        bounds: dict[str, Bound] = {}
        for k, b in cfg.bounds_raw.items():
            bounds[str(k)] = Bound(lo=float(b["lo"]), hi=float(b["hi"]),
                                   search=bool(b.get("search", True)),
                                   log=bool(b.get("log", False)))
        seed = Design(str(cfg.family), copy.deepcopy(dict(cfg.seed_params)))
        return cls(family=str(cfg.family), seed=seed, bounds=bounds)
