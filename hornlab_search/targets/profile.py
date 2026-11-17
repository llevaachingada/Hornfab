"""Frequency-dependent coverage profiles for objective v9 (amended RFC 2026-11-17).

An anchor is a 4-tuple ``(hz, preferred_deg, min_deg, max_deg)``:

* ``corridor`` mode: ``min_deg`` and ``max_deg`` are both present (the scored corridor);
* ``target`` mode: only ``preferred_deg`` is present (``min``/``max`` are ``None``).

Values are interpolated linearly against ``log10(hz)``.  Outside the anchor span the
nearest anchor is held (no extrapolation): below the onset the first anchor defines the
scorer's "one-sided" floor, and above the last anchor the final target is held.

Pure stdlib; this module is imported by ``objective/scalar_v9.py`` (scoring) and
``targets/scoring_view.py`` (display truth).  Nothing here solves, meshes or guesses: an
invalid profile raises ``ValueError`` naming the anchor, and the config layer turns that
into a ``ConfigError`` at load time.
"""
from __future__ import annotations

import math

#: Accepted profile modes (amended RFC sections B/D).
MODES = ("corridor", "target")
#: Accepted interpolation names.  ``log_frequency`` is the only one the scorer implements.
INTERPOLATIONS = ("log_frequency",)

_ANCHOR_KEYS = frozenset({"hz", "preferred_deg", "min_deg", "max_deg"})


def _num(value, where: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{where} must be a number, got {value!r}") from None
    if not math.isfinite(out):
        raise ValueError(f"{where} must be finite, got {value!r}")
    return out


def _row_tuple(row, plane: str, index: int, f0) -> tuple:
    """Normalise one anchor (mapping or 2..4-sequence) into ``(hz, pref, min, max)``."""
    where = f"coverage_profile.{plane}[{index}]"
    if isinstance(row, dict):
        unknown = sorted(set(row) - _ANCHOR_KEYS)
        if unknown:
            raise ValueError(f"{where}: unknown key(s) {unknown}")
        hz = row.get("hz", f0)
        pref = row.get("preferred_deg")
        lo = row.get("min_deg")
        hi = row.get("max_deg")
    elif isinstance(row, (list, tuple)):
        if not 2 <= len(row) <= 4:
            raise ValueError(f"{where}: expected (hz, preferred[, min, max]), got {row!r}")
        hz, pref = row[0], row[1]
        lo = row[2] if len(row) > 2 else None
        hi = row[3] if len(row) > 3 else None
    else:
        raise ValueError(f"{where}: expected a mapping or a 2-4 sequence, got {type(row).__name__}")

    if hz is None:
        if f0 is None:
            raise ValueError(f"{where}.hz is required when no plane f0 is available")
        hz = f0
    hz = _num(hz, f"{where}.hz")
    if hz <= 0.0:
        raise ValueError(f"{where}.hz must be > 0, got {hz!r}")
    pref = _num(pref, f"{where}.preferred_deg")
    if pref <= 0.0:
        raise ValueError(f"{where}.preferred_deg must be > 0, got {pref!r}")
    lo = None if lo is None else _num(lo, f"{where}.min_deg")
    hi = None if hi is None else _num(hi, f"{where}.max_deg")
    if (lo is None) != (hi is None):
        raise ValueError(f"{where}: min_deg and max_deg must be given together (both or neither)")
    if lo is not None:
        if hi is None:                       # defensive; the pair check above already raised
            raise ValueError(f"{where}: min_deg and max_deg must be given together")
        if not (0.0 < lo <= pref <= hi):
            raise ValueError(
                f"{where}: need 0 < min_deg <= preferred_deg <= max_deg, got "
                f"{lo!r} <= {pref!r} <= {hi!r}")
    return (hz, pref, lo, hi)


def parse_profile(rows, plane: str, f0=None) -> tuple:
    """Validate and sort one plane's anchors; returns a tuple of 4-tuples.

    ``rows`` is the raw YAML list (mappings with ``hz``/``preferred_deg``/optional
    ``min_deg``/``max_deg``) or an already-normalised sequence of tuples.  At least one
    anchor is required and duplicate ``hz`` values are refused (a profile must be a function
    of frequency).
    """
    if plane not in ("h", "v"):
        raise ValueError(f"coverage_profile: plane must be 'h' or 'v', got {plane!r}")
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError(f"coverage_profile.{plane}: at least one anchor is required")
    anchors = tuple(sorted((_row_tuple(row, plane, i, f0) for i, row in enumerate(rows)),
                           key=lambda a: a[0]))
    if len({a[0] for a in anchors}) != len(anchors):
        raise ValueError(f"coverage_profile.{plane}: duplicate hz anchor(s)")
    return anchors


def _check_anchors(anchors) -> tuple:
    """Accept a normalised anchor tuple; refuse anything malformed."""
    if not isinstance(anchors, (list, tuple)) or not anchors:
        raise ValueError("coverage profile anchors must be a non-empty list")
    out = []
    for index, row in enumerate(anchors):
        if not isinstance(row, (list, tuple)) or len(row) != 4:
            raise ValueError(f"coverage profile anchor[{index}] must be (hz, preferred, min, max)")
        hz = _num(row[0], f"coverage profile anchor[{index}].hz")
        pref = _num(row[1], f"coverage profile anchor[{index}].preferred_deg")
        lo = None if row[2] is None else _num(row[2], f"coverage profile anchor[{index}].min_deg")
        hi = None if row[3] is None else _num(row[3], f"coverage profile anchor[{index}].max_deg")
        if (lo is None) != (hi is None):
            raise ValueError(f"coverage profile anchor[{index}]: min/max must be both or neither")
        out.append((hz, pref, lo, hi))
    out.sort(key=lambda a: a[0])
    return tuple(out)


def profile_onset_hz(anchors, f0=None) -> float:
    """The effective scoring onset: ``max(first_anchor_hz, plane_f0)`` (amendment section D)."""
    checked = _check_anchors(anchors)
    onset = checked[0][0]
    if f0 is not None:
        onset = max(onset, _num(f0, "plane f0_hz"))
    return float(onset)


def profile_value(anchors, freq_hz: float) -> tuple:
    """``(preferred, min, max)`` at ``freq_hz``; ``min``/``max`` are ``None`` in target mode.

    Linear against ``log10(hz)`` between anchors, held constant outside the span.  The
    returned values are plain floats (or ``None``), never numpy scalars.
    """
    checked = _check_anchors(anchors)
    f = _num(freq_hz, "frequency")
    if f <= checked[0][0]:
        hz, pref, lo, hi = checked[0]
        return (float(pref), None if lo is None else float(lo), None if hi is None else float(hi))
    if f >= checked[-1][0]:
        hz, pref, lo, hi = checked[-1]
        return (float(pref), None if lo is None else float(lo), None if hi is None else float(hi))
    for left, right in zip(checked, checked[1:]):
        if left[0] <= f <= right[0]:
            if right[0] == left[0]:
                hz, pref, lo, hi = right
                return (float(pref), None if lo is None else float(lo),
                        None if hi is None else float(hi))
            t = ((math.log10(f) - math.log10(left[0]))
                 / (math.log10(right[0]) - math.log10(left[0])))
            pref = left[1] + (right[1] - left[1]) * t
            lo = (None if left[2] is None or right[2] is None
                  else left[2] + (right[2] - left[2]) * t)
            hi = (None if left[3] is None or right[3] is None
                  else left[3] + (right[3] - left[3]) * t)
            return (float(pref), None if lo is None else float(lo),
                    None if hi is None else float(hi))
    # Unreachable for a sorted, non-empty anchor set; kept finite for the never-raise contract.
    hz, pref, lo, hi = checked[-1]
    return (float(pref), None if lo is None else float(lo), None if hi is None else float(hi))


__all__ = ["MODES", "INTERPOLATIONS", "parse_profile", "profile_onset_hz", "profile_value"]
