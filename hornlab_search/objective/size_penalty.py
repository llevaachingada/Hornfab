"""Opt-in soft size cost on J (owner, 2026-11-25 18:23 / 18:56).

The owner's size-control intent: the optimizer may explore designs larger than the product box, but a
design that is too large scores worse, instead of being refused before it is solved. The open envelope
policy (``envelope.enforce: false`` + ``max_utilization``) only moved the HARD refusal outward; inside it an
oversize design paid nothing. This adds the soft cost, declared by the brief::

    envelope:
      enforce: false
      max_utilization: 1.30          # hard refusal (compute guard), well past where the cost bites
      soft_penalty: {weight: 1.0, tolerance: 0.05}

``cost = weight * (max(0, u - 1) / tolerance) ** 2`` with ``u = size_feasibility.max_utilization`` (the
largest of W/H/D of the SOLVED mesh over the product box, ``design/size.py``). No cost inside the box; with
tolerance 0.05 a design 5 % over costs 1.0 J, 10 % over 4.0 J. A solved row whose size could not be
measured pays ``weight * NAN_TERM_FILL`` (unknown is not free).

It is added AFTER the acoustic objective (``search/evaluate.py``, ``objective/replay.py``): the frozen v1-v11
scorers are untouched. ``terms`` gains ``size_penalty`` (the J contribution), ``size_utilization`` and
``J_acoustic``. Absent ``soft_penalty`` = byte-identical rows. The brief hash covers the block, so a brief
that declares it is a NEW J/BO identity.
"""
from __future__ import annotations

import math

from .terms import NAN_TERM_FILL

__all__ = ["SOFT_PENALTY_KEYS", "validate_soft_penalty", "soft_penalty_block", "size_penalty_terms"]

SOFT_PENALTY_KEYS = ("weight", "tolerance")


def validate_soft_penalty(block, where: str, *, enforce: bool) -> dict:
    """Return the normalized block or raise ``ValueError`` with ``where`` in the message."""
    if not isinstance(block, dict):
        raise ValueError(f"{where}: envelope.soft_penalty must be a mapping {{weight, tolerance}}")
    unknown = sorted(set(block) - set(SOFT_PENALTY_KEYS))
    missing = [k for k in SOFT_PENALTY_KEYS if k not in block]
    if unknown or missing:
        raise ValueError(f"{where}: envelope.soft_penalty needs exactly {list(SOFT_PENALTY_KEYS)}; "
                         f"unknown {unknown}, missing {missing}")
    out = {}
    for key in SOFT_PENALTY_KEYS:
        val = block[key]
        if (not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val)
                or val <= 0):
            raise ValueError(f"{where}: envelope.soft_penalty.{key} must be a positive finite number")
        out[key] = float(val)
    if enforce:
        raise ValueError(f"{where}: envelope.soft_penalty requires enforce: false (a production "
                         "envelope refuses oversize designs, so there is nothing to penalize)")
    return out


def soft_penalty_block(brief: dict | None) -> dict | None:
    """The brief's declared soft size penalty, or ``None`` (the default: no size term)."""
    env = (brief or {}).get("envelope") or {}
    block = env.get("soft_penalty") if isinstance(env, dict) else None
    if block is None:
        return None
    return validate_soft_penalty(block, "brief", enforce=bool(env.get("enforce", True)))


def size_penalty_terms(size_record: dict | None, block: dict) -> dict:
    """``{size_penalty, size_utilization}`` for one solved design (``size_utilization`` -1 = unmeasured)."""
    u = (size_record or {}).get("max_utilization")
    if isinstance(u, (int, float)) and not isinstance(u, bool) and math.isfinite(float(u)):
        over = max(0.0, float(u) - 1.0) / block["tolerance"]
        return {"size_penalty": float(block["weight"] * over * over), "size_utilization": float(u)}
    return {"size_penalty": float(block["weight"] * NAN_TERM_FILL), "size_utilization": -1.0}
