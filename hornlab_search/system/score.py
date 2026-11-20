"""Report-only scoring, dominance flags and phase-honesty refusal marking (Lane D).

There is **no scalar objective** in this module. :func:`render_report` never ranks rows by a
single number; it only emits deterministic Markdown/JSON, Pareto flags computed on explicitly
supplied numeric axes and feasibility columns, and status tokens. A future objective needs its
own versioned contract; it is not smuggled in through a report sort.

Row schema (all optional except an identifier)
-----------------------------------------------
Each row is a mapping. Recognised keys:

``row_id`` / ``id``
    Stable identifier (falls back to ``row-<input index>``).
``sort_key``
    Explicit, finite sort key (scalar or sequence). Rows are sorted by ``sort_key`` then
    ``row_id``. No axis/objective column is ever used implicitly.
``numeric_axes`` (alias ``dominance_axes``)
    Mapping ``name -> number``; the only numeric columns dominance may use.
``axis_directions`` (alias ``dominance_directions``)
    Mapping ``name -> "+" | "-"`` (maximise / minimise); default ``"+"``. Conflicting
    directions for one axis across rows are a :class:`contracts.SchemaError`.
``feasibility`` (alias ``bool_axes``)
    Mapping ``name -> bool``; boolean feasibility columns used by dominance.
``fidelity`` / ``data_quality``
    Passed through unchanged (per row) for comparability labelling.
``data_support``
    ``{"freq_hz": [lo, hi] | values, "angle_deg": [lo, hi] | values}`` describing the data's
    actual support.
``claims``
    List of claim mappings with optional ``axis``, ``freq_hz`` and ``angle_deg``. A claim
    outside ``data_support`` (or whose support was not declared) is marked ``REFUSED`` — never
    extrapolated — and the matching axis cell becomes ``REFUSED``.

NaN / infinity never dominates: a non-finite or missing value on a compared axis blocks a
domination relationship in both directions (conservative, no invented ordering).
"""
from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from hornlab_search.system import contracts

__all__ = [
    "render_report",
    "flag_off_axis_cancellation",
    "dominates",
]

_NUMERIC_ALIASES = ("numeric_axes", "dominance_axes")
_FEASIBILITY_ALIASES = ("feasibility", "bool_axes")
_DIRECTION_ALIASES = ("axis_directions", "dominance_directions")
_INELIGIBLE_PREFIXES = ("FAIL", "REFUSED", "BLOCKED", "PHASE_UNAVAILABLE")


# --------------------------------------------------------------------------- helpers

def _jsonable(value: Any) -> Any:
    """Recursively convert numpy/scalars to JSON-safe values; non-finite floats become None."""
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int)):
        return value
    return str(value)


def _pick(row: Mapping[str, Any], aliases: Sequence[str]) -> Mapping[str, Any]:
    for key in aliases:
        value = row.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _numeric_axes(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return _pick(row, _NUMERIC_ALIASES)


def _feasibility_axes(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return _pick(row, _FEASIBILITY_ALIASES)


def _directions(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return _pick(row, _DIRECTION_ALIASES)


def _sortable(value: Any) -> tuple[int, float, str]:
    if value is None:
        return (0, 0.0, "")
    if isinstance(value, bool):
        return (1, float(value), "")
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        return (2, number if math.isfinite(number) else math.inf, "")
    return (3, 0.0, str(value))


def _sort_key(row: Mapping[str, Any]) -> tuple[tuple[int, float, str], ...]:
    raw = row.get("sort_key", ())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
        values: tuple[Any, ...] = (raw,)
    else:
        values = tuple(raw)
    row_id = str(row.get("row_id", row.get("id", "")))
    return tuple(_sortable(v) for v in values) + (_sortable(row_id),)


def _raw_axis_value(value: Any) -> Any:
    """Unwrap a ``{value, direction}`` axis cell; plain numbers pass through unchanged."""
    if isinstance(value, Mapping):
        return value.get("value")
    return value


def _embedded_direction(value: Any) -> str | None:
    if isinstance(value, Mapping):
        direction = value.get("direction")
        if direction is not None:
            return str(direction)
    return None


def _axis_direction(key: str, a_value: Any, b_value: Any,
                    directions: Mapping[str, str]) -> str | None:
    """Resolve the direction: explicit map first, else the axis cell's own ``direction``."""
    if key in directions:
        return str(directions[key])
    a_dir = _embedded_direction(a_value)
    b_dir = _embedded_direction(b_value)
    if a_dir is not None and b_dir is not None and a_dir != b_dir:
        return None
    return a_dir if a_dir is not None else (b_dir if b_dir is not None else "+")


def _finite_number(value: Any) -> float | None:
    try:
        number = float(_raw_axis_value(value))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return None


def dominates(a: Mapping[str, Any], b: Mapping[str, Any],
              directions: Mapping[str, str]) -> bool:
    """Whether row ``a`` strictly dominates row ``b`` on the declared axes only.

    Requires every numeric axis declared by either row and every feasibility column to be
    present and finite/boolean in both rows; otherwise the pair is treated as unorderable
    (missing/NaN never dominates). At least one strict improvement is required.
    """
    num_keys = set(_numeric_axes(a)) | set(_numeric_axes(b))
    feas_keys = set(_feasibility_axes(a)) | set(_feasibility_axes(b))
    if not num_keys and not feas_keys:
        return False

    for key in sorted(num_keys):
        av = _finite_number(_numeric_axes(a).get(key))
        bv = _finite_number(_numeric_axes(b).get(key))
        if av is None or bv is None:
            return False
        direction = _axis_direction(
            key, _numeric_axes(a).get(key), _numeric_axes(b).get(key), directions)
        if direction is None:
            return False
        if direction == "+" and av < bv:
            return False
        if direction == "-" and av > bv:
            return False

    feasible_a = _feasibility_axes(a)
    feasible_b = _feasibility_axes(b)
    for key in sorted(feas_keys):
        av = _bool_or_none(feasible_a.get(key))
        bv = _bool_or_none(feasible_b.get(key))
        if av is None or bv is None:
            return False
        if bv and not av:
            return False

    strict = False
    for key in sorted(num_keys):
        av = float(_raw_axis_value(_numeric_axes(a)[key]))
        bv = float(_raw_axis_value(_numeric_axes(b)[key]))
        direction = _axis_direction(key, _numeric_axes(a)[key], _numeric_axes(b)[key], directions)
        if direction == "+" and av > bv:
            strict = True
        if direction == "-" and av < bv:
            strict = True
    for key in sorted(feas_keys):
        if bool(feasible_a[key]) and not bool(feasible_b[key]):
            strict = True
    return strict


def _supported(value: Any, support: Any) -> bool:
    """Whether ``value`` lies inside a declared support; no support => not supported."""
    if support is None:
        return False
    if isinstance(support, Mapping):
        if "values" in support:
            return value in tuple(support["values"])
        lo = support.get("lo", support.get("min"))
        hi = support.get("hi", support.get("max"))
        if lo is None or hi is None:
            return False
        return _supported(value, (lo, hi))
    if isinstance(support, (list, tuple)):
        if len(support) == 2:
            lo, hi = support
            try:
                x, lo_f, hi_f = float(value), float(lo), float(hi)
            except (TypeError, ValueError):
                return False
            if not (math.isfinite(x) and math.isfinite(lo_f) and math.isfinite(hi_f)):
                return False
            return lo_f <= x <= hi_f
        return value in tuple(support)
    return False


def _apply_claims(row: Mapping[str, Any], out: dict[str, Any],
                  axes: Sequence[str]) -> list[dict[str, Any]]:
    """Mark any claim outside declared data support as REFUSED (no extrapolation)."""
    claims = row.get("claims") or []
    if not claims:
        return []
    support = row.get("data_support") or {}
    supported = support if isinstance(support, Mapping) else {}
    processed: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for claim in claims:
        claim_map = dict(claim) if isinstance(claim, Mapping) else {"claim": claim}
        freq = claim_map.get("freq_hz", claim_map.get("frequency_hz"))
        angle = claim_map.get("angle_deg")
        ok = True
        reasons: list[str] = []
        if freq is not None:
            limit = supported.get("freq_hz", supported.get("frequency_hz"))
            if not _supported(freq, limit):
                ok = False
                reasons.append(f"frequency {freq!r} outside declared support {limit!r}")
        if angle is not None:
            limit = supported.get("angle_deg")
            if not _supported(angle, limit):
                ok = False
                reasons.append(f"angle {angle!r} outside declared support {limit!r}")

        claim_out = dict(claim_map)
        if ok:
            claim_out.setdefault("status", "PASS")
        else:
            claim_out["status"] = "REFUSED"
            claim_out["refusal_reason"] = "; ".join(reasons)
            axis = claim_map.get("axis")
            if isinstance(axis, str) and axis in axes:
                out[axis] = "REFUSED"
            refused.append(claim_out)
        processed.append(claim_out)
    out["claims"] = processed
    return refused


def _axis_status(row: Mapping[str, Any], axes: Sequence[str]) -> list[str]:
    statuses: list[str] = []
    for axis in axes:
        value = row.get(axis)
        if value is None:
            continue
        text = str(value)
        statuses.append(text)
    return statuses


def _has_ineligible_status(row: Mapping[str, Any], axes: Sequence[str]) -> bool:
    return any(s.upper().startswith(_INELIGIBLE_PREFIXES)
               for s in _axis_status(row, axes))


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, Mapping):
        text = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))
    elif isinstance(value, (list, tuple)):
        text = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- report

def render_report(rows: list[dict],
                  axes: Sequence[str] = contracts.REPORT_AXES) -> dict[str, str]:
    """Render a deterministic, report-only summary of ``rows``.

    Returns ``{"markdown": str, "json": str}``. The same rows produce byte-identical strings.
    Rows are ordered by their explicit ``sort_key`` then ``row_id``; no scalar objective is
    ever used for ordering. ``system_objective_version`` is stamped from the frozen contract.
    """
    axes = tuple(str(a) for a in axes)
    raw_rows = [dict(r) for r in rows]
    ids = [str(r.get("row_id", r.get("id", f"row-{i}"))) for i, r in enumerate(raw_rows)]
    if len(set(ids)) != len(ids):
        raise contracts.SchemaError("report rows must have unique row_id values")

    # Explicit directions must agree across rows; default '+' (maximise).
    directions: dict[str, str] = {}
    for row in raw_rows:
        for key, value in _directions(row).items():
            direction = str(value)
            if direction not in ("+", "-"):
                raise contracts.SchemaError(
                    f"axis direction for {key!r} must be '+' or '-', got {value!r}")
            if directions.setdefault(str(key), direction) != direction:
                raise contracts.SchemaError(
                    f"conflicting directions for axis {key!r}: "
                    f"{directions[str(key)]!r} vs {direction!r}")

    order = sorted(range(len(raw_rows)), key=lambda i: _sort_key(raw_rows[i]))

    dominated_by: dict[int, list[str]] = {i: [] for i in range(len(raw_rows))}
    for i in range(len(raw_rows)):
        for j in range(len(raw_rows)):
            if i == j:
                continue
            if dominates(raw_rows[j], raw_rows[i], directions):
                dominated_by[i].append(ids[j])
    pareto = {i: not dominated_by[i] for i in dominated_by}

    out_rows: list[dict[str, Any]] = []
    refused_rows: list[tuple[str, dict[str, Any]]] = []
    for i in order:
        out = _jsonable(raw_rows[i])
        out["row_id"] = ids[i]
        out["pareto"] = bool(pareto[i])
        out["dominated_by"] = sorted(dominated_by[i])
        refused = _apply_claims(raw_rows[i], out, axes)
        out_rows.append(out)
        for claim in refused:
            refused_rows.append((ids[i], claim))

    frontier = [ids[i] for i in order if pareto[i]]
    eligible = [ids[i] for i in order if pareto[i]
                and not _has_ineligible_status(raw_rows[i], axes)
                and not any(ids[i] == rid for rid, _ in refused_rows)]
    winner: str | None = None
    winner_status = "no eligible non-dominated row"
    if len(eligible) == 1:
        winner = eligible[0]
        winner_status = "sole eligible non-dominated row"
    elif len(eligible) > 1:
        winner_status = "multiple eligible non-dominated rows; no sole winner"
    elif frontier:
        winner_status = ("all non-dominated rows carry FAIL/REFUSED status; "
                         "no sole winner (vertical/oblique null rows are excluded)")

    payload = {
        "system_objective_version": int(contracts.SYSTEM_OBJECTIVE_VERSION),
        "axes": list(axes),
        "directions": dict(sorted(directions.items())),
        "pareto_frontier": frontier,
        "winner": winner,
        "winner_status": winner_status,
        "rows": out_rows,
    }
    json_text = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False) + "\n"

    show_fidelity = any("fidelity" in r for r in raw_rows)
    show_quality = any("data_quality" in r for r in raw_rows)
    header = ["row_id"]
    if show_fidelity:
        header.append("fidelity")
    header.extend(axes)
    header.append("dominance")
    if show_quality:
        header.append("data_quality")

    lines = ["# System report (report-only)", "",
             f"system_objective_version: {contracts.SYSTEM_OBJECTIVE_VERSION}",
             f"axes: {', '.join(axes)}",
             f"pareto_frontier: {', '.join(frontier) if frontier else '(none)'}",
             f"winner: {winner if winner else '(none)'}",
             f"winner_status: {winner_status}", "",
             "| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for i in order:
        out = next(r for r in out_rows if r["row_id"] == ids[i])
        cells = [ids[i]]
        if show_fidelity:
            cells.append(_cell(raw_rows[i].get("fidelity")))
        cells.extend(_cell(raw_rows[i].get(axis)) for axis in axes)
        if out["pareto"]:
            cells.append("pareto")
        elif out["dominated_by"]:
            cells.append("dominated by " + ", ".join(out["dominated_by"]))
        else:
            cells.append("-")
        if show_quality:
            cells.append(_cell(raw_rows[i].get("data_quality")))
        lines.append("| " + " | ".join(cells) + " |")

    if refused_rows:
        lines.extend(["", "## refused claims (outside declared data support)", ""])
        for row_id, claim in refused_rows:
            axis = claim.get("axis", "claim")
            reason = claim.get("refusal_reason", "outside declared support")
            lines.append(f"- {row_id} / {axis}: REFUSED ({reason})")

    markdown = "\n".join(lines) + "\n"
    return {"markdown": markdown, "json": json_text}


# --------------------------------------------------------------------------- SYS-18 detector

def flag_off_axis_cancellation(
    responses: Mapping[str, np.ndarray],
    *,
    on_axis_key: str = "on_axis",
    off_axis_keys: Sequence[str] | None = None,
    freqs_hz: Any = None,
    xo_hz: float | None = None,
    octave_halfwidth: float = 0.5,
    dip_db: float = 6.0,
    smoothness_db: float = 3.0,
    direction_angles_deg: Mapping[str, float] | None = None,
    max_off_axis_deg: float = 20.0,
) -> dict[str, Any]:
    """SYS-18: detect a vertical/oblique cancellation null inside the crossover band.

    ``responses`` maps direction label -> 1-D dB array on the same frequency grid. If the
    on-axis response is smooth (ripple ``<= smoothness_db``) but any off-axis direction dips
    more than ``dip_db`` below the on-axis band level, the returned ``status`` is exactly
    ``"FAIL: vertical/oblique null"`` (assign it to the row's ``crossover_physics`` axis).
    Rows so flagged must never be selected as a sole winner (:func:`render_report` enforces
    this).

    ``off_axis_keys`` restricts the detector (the caller supplies the +-20 degree set); when
    omitted, ``direction_angles_deg`` with ``max_off_axis_deg`` selects directions, otherwise
    every non-on-axis key is used. ``freqs_hz`` + ``xo_hz`` select the crossover octave
    ``xo_hz * 2**(+-octave_halfwidth)``; without ``xo_hz`` the whole array is inspected.

    Returns a JSON-friendly dict with ``status``, ``axis='crossover_physics'``, the worst drop
    and the per-direction drops. No phase is invented; this is a magnitude-only detector.
    """
    arrays: dict[str, np.ndarray] = {}
    for key, values in responses.items():
        arr = np.asarray(values, dtype=np.float64)
        if arr.ndim != 1:
            raise contracts.SchemaError(
                f"response {key!r} must be 1-D dB, got shape {arr.shape}")
        arrays[str(key)] = arr
    if not arrays:
        raise contracts.SchemaError("flag_off_axis_cancellation needs at least one response")
    lengths = {a.shape[0] for a in arrays.values()}
    if len(lengths) != 1:
        raise contracts.SchemaError("all responses must share one frequency axis")
    n = lengths.pop()

    on_key = on_axis_key if on_axis_key in arrays else next(iter(arrays))

    freqs = None if freqs_hz is None else np.asarray(freqs_hz, dtype=np.float64)
    if freqs is not None and (freqs.ndim != 1 or freqs.shape[0] != n):
        raise contracts.SchemaError("freqs_hz must be 1-D and match the response length")
    if xo_hz is not None:
        if freqs is None:
            raise contracts.SchemaError(
                "xo_hz needs freqs_hz to locate the crossover band (no index guessing)")
        lo = float(xo_hz) * 2.0 ** (-float(octave_halfwidth))
        hi = float(xo_hz) * 2.0 ** (float(octave_halfwidth))
        mask = (freqs >= lo) & (freqs <= hi)
        band_hz = [lo, hi]
    else:
        mask = np.ones(n, dtype=bool)
        band_hz = [float(np.nanmin(freqs)) if freqs is not None else 0.0,
                   float(np.nanmax(freqs)) if freqs is not None else float(n - 1)]

    if not np.any(mask):
        return {"status": "SCREEN_ONLY", "axis": "crossover_physics",
                "detail": "no samples inside the requested crossover band",
                "band_hz": band_hz, "worst_drop_db": 0.0, "worst_direction": None,
                "on_axis_ripple_db": None, "dips": {}}

    on_values = arrays[on_key][mask]
    on_finite = on_values[np.isfinite(on_values)]
    if on_finite.size < 2:
        return {"status": "SCREEN_ONLY", "axis": "crossover_physics",
                "detail": "too few finite on-axis samples to judge smoothness",
                "band_hz": band_hz, "worst_drop_db": 0.0, "worst_direction": None,
                "on_axis_ripple_db": None, "dips": {}}

    on_ripple = float(np.max(on_finite) - np.min(on_finite))
    on_level = float(np.mean(on_finite))
    if on_ripple > float(smoothness_db):
        return {"status": "SCREEN_ONLY", "axis": "crossover_physics",
                "detail": (f"on-axis ripple {on_ripple:.3f} dB exceeds smoothness "
                           f"{float(smoothness_db):.3f} dB; null detector not applicable"),
                "band_hz": band_hz, "worst_drop_db": 0.0, "worst_direction": None,
                "on_axis_ripple_db": on_ripple, "dips": {}}

    if off_axis_keys is not None:
        keys = [k for k in (str(k) for k in off_axis_keys) if k in arrays and k != on_key]
    elif direction_angles_deg is not None:
        keys = [k for k, ang in sorted(direction_angles_deg.items(), key=lambda kv: str(kv[0]))
                if k in arrays and k != on_key and abs(float(ang)) <= float(max_off_axis_deg)]
    else:
        keys = [k for k in arrays if k != on_key]

    dips: dict[str, float] = {}
    for key in keys:
        values = arrays[key][mask]
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        dips[key] = float(on_level - np.min(finite))

    worst_key = max(dips, key=lambda k: dips[k]) if dips else None
    worst_drop = float(dips[worst_key]) if worst_key is not None else 0.0
    if worst_key is not None and worst_drop > float(dip_db):
        detail = (f"on-axis smooth (ripple {on_ripple:.3f} dB) but {worst_key} dips "
                  f"{worst_drop:.3f} dB > {float(dip_db):.3f} dB in the crossover band")
        return {"status": "FAIL: vertical/oblique null", "axis": "crossover_physics",
                "detail": detail, "band_hz": band_hz, "worst_drop_db": worst_drop,
                "worst_direction": worst_key, "on_axis_ripple_db": on_ripple, "dips": dips}

    return {"status": "PASS", "axis": "crossover_physics",
            "detail": "no off-axis dip exceeds the threshold in the crossover band",
            "band_hz": band_hz, "worst_drop_db": worst_drop,
            "worst_direction": worst_key, "on_axis_ripple_db": on_ripple, "dips": dips}
