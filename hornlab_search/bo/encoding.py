"""Reversible, audited encoding for advisory Bayesian proposals (protocol bo-study-v1.1).

The search vector order is ALWAYS the existing alphabetical ``DesignSpace.keys()`` order.  A
versioned **active projection** may drop only controls that are statically proven AND
geometry-tested no-ops for the frozen task (``morph_exponent`` at ``morph_target == 1`` for the
ATH task).  Dropped controls are held at their recorded reference value when decoding, so the
full alphabetical vector is always reconstructed before ``space.denormalize``.

This module deliberately does not implement scorer math, acquisition, or the B3 model.  It is a
pure adapter over the existing :class:`~hornlab_search.design.space.DesignSpace` /
:class:`~hornlab_search.design.generated.GeneratedSpace` bound/log transforms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

PROJECTION_VERSION = "active-projection-v1"
MIN_ACTIVE_DIM = 1
MAX_ACTIVE_DIM = 20


class EncodingError(ValueError):
    """Base class for a refused encode/decode request."""


class MissingKeyError(EncodingError):
    """A required full-vector key is absent from the observation."""


class HistoricalClippingError(EncodingError):
    """An historical observation lies outside the resolved search box (never clip silently)."""


class UnsupportedSpaceError(EncodingError):
    """The space contains an unsupported discrete/categorical active dimension."""


class HashMismatchError(EncodingError):
    """Normalize -> denormalize did not reproduce the recorded Design.hash()."""


def _finite_float(value, key: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise MissingKeyError(f"{key}: not a finite number ({value!r})") from None
    if not np.isfinite(out):
        raise MissingKeyError(f"{key}: not a finite number ({value!r})")
    return out


def _is_discrete_value(value) -> bool:
    """True for bool/int/categorical/container values; a plain float is continuous."""
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, np.integer)):
        return True
    if isinstance(value, (str, list, tuple, dict)):
        return True
    return False


def _full_keys(space) -> tuple[str, ...]:
    keys = tuple(str(k) for k in space.keys())
    if keys != tuple(sorted(keys)):
        raise UnsupportedSpaceError(
            "space.keys() is not alphabetical; the protocol requires the existing alphabetical "
            f"order, got {keys}")
    if len(set(keys)) != len(keys):
        raise UnsupportedSpaceError("space.keys() contains duplicates")
    return keys


@dataclass(frozen=True)
class ActiveProjection:
    """Versioned active projection over the full alphabetical search vector.

    ``full_keys`` is exactly ``space.keys()``.  ``active_keys`` is the retained subsequence.
    ``fixed_values`` maps each dropped key to the *physical* reference value held while decoding
    (never to an invented default).
    """

    space: Any = field(repr=False, compare=False)
    full_keys: tuple[str, ...]
    active_keys: tuple[str, ...]
    fixed_values: Mapping[str, float]
    version: str = PROJECTION_VERSION

    # ------------------------------------------------------------------ construction
    @classmethod
    def identity(cls, space) -> "ActiveProjection":
        """The unprojected full-dimension encoding (no control removed)."""
        return cls.from_space(space, no_ops={})

    @classmethod
    def from_space(cls, space, *, no_ops: Mapping[str, float] | None = None,
                   discrete_keys: set[str] | None = None) -> "ActiveProjection":
        """Build and validate a projection.  Only an explicit ``no_ops`` mapping is projected."""
        full = _full_keys(space)
        if not full:
            raise UnsupportedSpaceError("the space has no searchable keys")
        no_ops = {str(k): float(v) for k, v in dict(no_ops or {}).items()}
        unknown = sorted(set(no_ops) - set(full))
        if unknown:
            raise UnsupportedSpaceError(f"no-op key(s) not in space.keys(): {unknown}")
        for key, value in no_ops.items():
            if not np.isfinite(value):
                raise UnsupportedSpaceError(f"{key}: no-op reference value must be finite")
            if key not in space.bounds:
                raise UnsupportedSpaceError(f"{key}: no bound for the no-op reference")
            _, clipped = space.bounds[key].to_unit(value)
            if clipped:
                raise UnsupportedSpaceError(
                    f"{key}: no-op reference value {value!r} lies outside its resolved bound")
        active = tuple(k for k in full if k not in no_ops)
        if not (MIN_ACTIVE_DIM <= len(active) <= MAX_ACTIVE_DIM):
            raise UnsupportedSpaceError(
                f"active dimension d={len(active)} is outside the supported "
                f"[{MIN_ACTIVE_DIM}, {MAX_ACTIVE_DIM}] continuous range")
        discrete = set(discrete_keys or ())
        discrete |= _discrete_keys_from_space(space, active)
        residual = sorted(set(active) & discrete)
        if residual:
            raise UnsupportedSpaceError(
                "unsupported discrete/categorical active dimension(s): "
                f"{residual}; the protocol supports continuous retained parameters only")
        return cls(space=space, full_keys=full, active_keys=active, fixed_values=no_ops)

    # ------------------------------------------------------------------ shape
    @property
    def full_d(self) -> int:
        return len(self.full_keys)

    @property
    def d(self) -> int:
        return len(self.active_keys)

    @property
    def active_index(self) -> tuple[int, ...]:
        return tuple(self.full_keys.index(k) for k in self.active_keys)

    def key_transforms(self) -> dict[str, dict]:
        """Resolved bound metadata; the actual [0,1] map is the existing ``Bound`` logic."""
        out: dict[str, dict] = {}
        for key in self.full_keys:
            b = self.space.bounds[key]
            out[key] = {
                "lo": float(b.lo),
                "hi": float(b.hi),
                "log": bool(b.log),
                "transform": "log10" if b.log else "identity",
                "active": key not in self.fixed_values,
            }
        return out

    def _fixed_unit_values(self) -> np.ndarray:
        out = np.zeros(self.full_d, dtype=float)
        for key, value in self.fixed_values.items():
            u, clipped = self.space.bounds[key].to_unit(float(value))
            if clipped:  # already checked in from_space; defensive
                raise HistoricalClippingError(f"{key}: fixed reference value is outside the box")
            out[self.full_keys.index(key)] = float(u)
        return out

    # ------------------------------------------------------------------ projection
    def to_full(self, active_vector) -> np.ndarray:
        """Active unit vector -> full alphabetical unit vector with fixed values restored."""
        x = np.asarray(active_vector, dtype=float).reshape(-1)
        if x.size != self.d:
            raise EncodingError(f"expected an active vector of length {self.d}, got {x.size}")
        if not np.all(np.isfinite(x)):
            raise EncodingError("active vector contains non-finite values")
        full = self._fixed_unit_values()
        full[list(self.active_index)] = x
        return full

    def to_active(self, full_vector) -> np.ndarray:
        """Full alphabetical unit vector -> active unit vector (validates length/finiteness)."""
        x = np.asarray(full_vector, dtype=float).reshape(-1)
        if x.size != self.full_d:
            raise EncodingError(f"expected a full vector of length {self.full_d}, got {x.size}")
        if not np.all(np.isfinite(x)):
            raise EncodingError("full vector contains non-finite values")
        return x[list(self.active_index)]

    # ------------------------------------------------------------------ assemble / read
    def _full_unit_vector(self, design) -> np.ndarray:
        """Design -> strict full unit vector.  Missing keys and historical clipping refuse."""
        from ..design import families
        from ..design.generated import GeneratedSpace

        if isinstance(self.space, GeneratedSpace):
            knobs = self.space.knobs_for(design)
            if knobs is None:
                raise HashMismatchError(
                    "GeneratedSpace.normalize: design was not produced by this space "
                    "(generator knobs cannot be recovered from geometry)")
            out = np.empty(self.full_d, dtype=float)
            for i, key in enumerate(self.full_keys):
                if key not in knobs:
                    raise MissingKeyError(f"missing generator knob {key!r}")
                value = knobs[key]
                if isinstance(value, (list, tuple)):
                    raise UnsupportedSpaceError(
                        f"{key}: list-valued generator knob is not a continuous scalar")
                u, clipped = self.space.bounds[key].to_unit(_finite_float(value, key))
                if clipped:
                    raise HistoricalClippingError(
                        f"{key}={value!r} is outside its resolved bound "
                        f"[{self.space.bounds[key].lo}, {self.space.bounds[key].hi}]")
                out[i] = float(u)
            return out

        params = getattr(design, "params", None)
        if not isinstance(params, dict):
            raise MissingKeyError("design.params must be a dict")
        if "grid" in params or "cad" in params:
            raise UnsupportedSpaceError(
                "grid/CAD designs carry a recipe, not invertible continuous parameters")
        family = str(getattr(design, "family", self.space.family))
        out = np.empty(self.full_d, dtype=float)
        for i, key in enumerate(self.full_keys):
            try:
                value = families.param_get(family, params, key)
            except KeyError:
                raise MissingKeyError(f"missing required search key {key!r}") from None
            if _is_discrete_value(value):
                raise UnsupportedSpaceError(
                    f"search key {key!r} resolved to a discrete value {value!r}")
            u, clipped = self.space.bounds[key].to_unit(_finite_float(value, key))
            if clipped:
                b = self.space.bounds[key]
                raise HistoricalClippingError(
                    f"{key}={value!r} is outside the resolved bound [{b.lo}, {b.hi}]; "
                    "historical observations must never be clipped")
            out[i] = float(u)
        return out

    def normalize_design(self, design, *, verify_round_trip: bool = True) -> np.ndarray:
        """Design -> active unit vector.  Optionally proves a hash-exact round-trip."""
        full = self._full_unit_vector(design)
        active = self.to_active(full)
        if verify_round_trip:
            rt = self.denormalize(active)
            if rt.hash() != design.hash():
                raise HashMismatchError(
                    f"normalize->denormalize changed Design.hash(): {design.hash()} != "
                    f"{rt.hash()}; the observation is not representable in this space/projection")
        return active

    def denormalize(self, active_vector, *, clip: bool = False):
        """Active unit vector -> Design (full alphabetical vector reconstructed first)."""
        x = np.asarray(active_vector, dtype=float).reshape(-1)
        if x.size != self.d:
            raise EncodingError(f"expected an active vector of length {self.d}, got {x.size}")
        if not np.all(np.isfinite(x)):
            raise EncodingError("active vector contains non-finite values")
        if np.any((x < 0.0) | (x > 1.0)):
            if not clip:
                raise HistoricalClippingError(
                    "active unit vector leaves [0,1]; refusing to clip silently "
                    "(pass clip=True only for a new proposal explicitly kept in box)")
            x = np.clip(x, 0.0, 1.0)
        return self.space.denormalize(self.to_full(x))

    def reference_values(self) -> dict[str, float | None]:
        """Physical reference (seed) values for every active/fixed key, when readable."""
        out: dict[str, float | None] = {}
        seed = getattr(self.space, "seed", None)
        params = getattr(seed, "params", None) if seed is not None else None
        for key in self.full_keys:
            if key in self.fixed_values:
                out[key] = float(self.fixed_values[key])
                continue
            try:
                if isinstance(params, dict):
                    from ..design import families
                    out[key] = float(families.param_get(self.space.family, params, key))
                elif hasattr(self.space, "seed_knobs"):
                    out[key] = float(self.space.seed_knobs[key])
                else:
                    out[key] = None
            except Exception:  # noqa: BLE001 - reference display is best-effort
                out[key] = None
        return out


def _discrete_keys_from_space(space, active_keys: tuple[str, ...]) -> set[str]:
    """Detect statically discrete active dimensions from the existing family KeySpec table."""
    try:
        from ..design import families
        from ..design.space import DesignSpace
    except Exception:  # noqa: BLE001 - a non-native space still gets the explicit set
        return set()
    if not isinstance(space, DesignSpace):
        return set()
    table = families.FAMILY_KEYS.get(str(space.family), {})
    out: set[str] = set()
    for key in active_keys:
        spec = table.get(families.root_key(key))
        if spec is not None and spec.kind not in (float,):
            out.add(key)
    return out


__all__ = [
    "PROJECTION_VERSION",
    "MIN_ACTIVE_DIM",
    "MAX_ACTIVE_DIM",
    "EncodingError",
    "MissingKeyError",
    "HistoricalClippingError",
    "UnsupportedSpaceError",
    "HashMismatchError",
    "ActiveProjection",
]
