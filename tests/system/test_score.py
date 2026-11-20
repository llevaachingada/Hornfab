"""Report-only scoring tests (SYS-18 + report determinism + refusal marking).

There is no scalar objective here. These tests pin: byte-identical deterministic reports,
explicit-axis-only Pareto dominance, NaN never winning, out-of-band claims marked REFUSED,
and a vertical/oblique null row never being selected as a sole winner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import score  # noqa: E402


def _row(row_id: str, sort_key: Any, cost: float, headroom: float, **kw: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "row_id": row_id,
        "sort_key": (sort_key,),
        "numeric_axes": {"cost": cost, "headroom": headroom},
        "axis_directions": {"cost": "-", "headroom": "+"},
        "fidelity": "SCREEN_COMPLEX_APPROX",
        "data_quality": {"quality": "EXACT_COMPLEX"},
    }
    row.update(kw)
    return row


# --------------------------------------------------------------------------- dominance

def test_dominance_uses_only_declared_axes_and_directions() -> None:
    directions = {"cost": "-", "headroom": "+"}
    a = {"numeric_axes": {"cost": 10.0, "headroom": 8.0}}
    b = {"numeric_axes": {"cost": 12.0, "headroom": 6.0}}
    assert score.dominates(a, b, directions)
    assert not score.dominates(b, a, directions)
    # No declared axes -> no ordering at all (never a scalar objective fallback).
    assert not score.dominates({"cost": 1.0}, {"cost": 2.0}, directions)


def test_nan_never_dominates() -> None:
    directions = {"cost": "-", "headroom": "+"}
    nan_row = {"numeric_axes": {"cost": 1.0, "headroom": float("nan")}}
    good = {"numeric_axes": {"cost": 2.0, "headroom": 1.0}}
    assert not score.dominates(nan_row, good, directions)
    assert not score.dominates(good, nan_row, directions)


def test_boolean_feasibility_participates_in_dominance() -> None:
    directions = {"cost": "-"}
    feasible = {"numeric_axes": {"cost": 10.0}, "feasibility": {"buildable": True}}
    not_feasible = {"numeric_axes": {"cost": 10.0}, "feasibility": {"buildable": False}}
    assert score.dominates(feasible, not_feasible, directions)
    assert not score.dominates(not_feasible, feasible, directions)


def test_nested_numeric_axis_is_a_schema_error_not_a_pareto_row() -> None:
    """The old pilot shipped {value, direction} axes; dominance silently discarded every pair."""
    row = _row("nested", 1, cost=1.0, headroom=2.0)
    row["numeric_axes"]["cost"] = {"value": 1.0, "direction": "-"}
    with pytest.raises(C.SchemaError, match="numeric axis 'cost'"):
        score.render_report([row])
    with pytest.raises(C.SchemaError, match="numeric axis 'cost'"):
        score.validate_axes([row])


def test_non_boolean_feasibility_is_a_schema_error() -> None:
    """A skipped-rule list is detail, not a boolean feasibility column."""
    row = _row("bad-feas", 1, cost=1.0, headroom=2.0)
    row["feasibility"] = {"buildable": True, "rules_skips": ["no geometry"]}
    with pytest.raises(C.SchemaError, match="feasibility column 'rules_skips'"):
        score.render_report([row])


# --------------------------------------------------------------------------- determinism

def test_report_is_byte_identical_and_order_independent() -> None:
    rows = [
        _row("a", 1, cost=10.0, headroom=8.0),
        _row("b", 2, cost=12.0, headroom=6.0),
        _row("c", 3, cost=8.0, headroom=4.0),
    ]
    first = score.render_report(rows)
    second = score.render_report(rows)
    reordered = score.render_report(list(reversed(rows)))
    assert first == second
    assert first == reordered
    assert isinstance(first["markdown"], str) and isinstance(first["json"], str)

    payload = json.loads(first["json"])
    assert payload["system_objective_version"] == C.SYSTEM_OBJECTIVE_VERSION == 1
    assert [r["row_id"] for r in payload["rows"]] == ["a", "b", "c"]
    assert payload["rows"][0]["fidelity"] == "SCREEN_COMPLEX_APPROX"
    assert payload["rows"][0]["data_quality"] == {"quality": "EXACT_COMPLEX"}
    assert payload["pareto_frontier"] == ["a", "c"]
    by_id = {r["row_id"]: r for r in payload["rows"]}
    assert by_id["b"]["pareto"] is False
    assert by_id["b"]["dominated_by"] == ["a"]
    assert by_id["a"]["pareto"] is True and by_id["c"]["pareto"] is True
    # Two non-dominated rows: no sole winner, and never a scalar-objective pick.
    assert payload["winner"] is None


def test_report_markdown_contains_the_axes_and_version() -> None:
    report = score.render_report([_row("only", 1, cost=1.0, headroom=1.0)])
    markdown = report["markdown"]
    assert "report-only" in markdown
    assert "system_objective_version: 1" in markdown
    for axis in C.REPORT_AXES:
        assert axis in markdown


# --------------------------------------------------------------------------- NaN / winner

def test_nan_row_is_never_a_dominance_winner() -> None:
    nan_row = _row("nan", 1, cost=1.0, headroom=float("nan"))
    good = _row("good", 2, cost=2.0, headroom=1.0)
    payload = json.loads(score.render_report([nan_row, good])["json"])
    by_id = {r["row_id"]: r for r in payload["rows"]}
    assert by_id["nan"]["pareto"] is True       # unorderable, not dominated
    assert by_id["nan"]["dominated_by"] == []
    assert payload["winner"] is None
    # Non-finite values serialise as null, never as a ranked number.
    assert by_id["nan"]["numeric_axes"]["headroom"] is None


# --------------------------------------------------------------------------- out-of-band

def test_out_of_band_claim_is_refused_not_extrapolated() -> None:
    row = {
        "row_id": "x",
        "sort_key": (0,),
        "data_support": {"freq_hz": [500.0, 2000.0], "angle_deg": [-30.0, 30.0]},
        "angular_field": "PASS",
        "claims": [{"axis": "angular_field", "freq_hz": 5000.0, "angle_deg": 10.0}],
    }
    report = score.render_report([row])
    payload = json.loads(report["json"])
    out = payload["rows"][0]
    assert out["claims"][0]["status"] == "REFUSED"
    assert out["angular_field"] == "REFUSED"
    assert payload["winner"] is None
    assert "REFUSED" in report["markdown"]


def test_in_band_claim_is_not_refused() -> None:
    row = {
        "row_id": "y",
        "sort_key": (0,),
        "data_support": {"freq_hz": [500.0, 2000.0], "angle_deg": [-30.0, 30.0]},
        "angular_field": "PASS",
        "claims": [{"axis": "angular_field", "freq_hz": 1000.0, "angle_deg": 0.0}],
    }
    payload = json.loads(score.render_report([row])["json"])
    out = payload["rows"][0]
    assert out["claims"][0]["status"] == "PASS"
    assert out["angular_field"] == "PASS"


# --------------------------------------------------------------------------- SYS-18

def _detector_inputs(null_depth_db: float):
    freqs = np.geomspace(200.0, 5000.0, 400)
    on_axis = np.zeros_like(freqs)
    in_band = (freqs >= 1000.0 * 2.0 ** -0.5) & (freqs <= 1000.0 * 2.0 ** 0.5)
    off_axis = np.where(in_band, null_depth_db, 0.0)
    return {"on_axis": on_axis, "h=+20,v=0": off_axis, "h=-20,v=0": off_axis}, freqs


def test_sys18_flags_vertical_oblique_null() -> None:
    responses, freqs = _detector_inputs(-12.0)
    result = score.flag_off_axis_cancellation(responses, freqs_hz=freqs, xo_hz=1000.0)
    assert result["status"] == "FAIL: vertical/oblique null"
    assert result["axis"] == "crossover_physics"
    assert result["worst_drop_db"] > 6.0

    row = {"row_id": "nulled", "sort_key": (0,),
           "crossover_physics": result["status"], "fidelity": "SCREEN_COMPLEX_APPROX"}
    payload = json.loads(score.render_report([row])["json"])
    assert payload["winner"] is None
    assert payload["rows"][0]["pareto"] is True
    assert "vertical/oblique null" in payload["winner_status"]


def test_sys18_passes_when_off_axis_does_not_dip() -> None:
    responses, freqs = _detector_inputs(-2.0)
    result = score.flag_off_axis_cancellation(responses, freqs_hz=freqs, xo_hz=1000.0)
    assert result["status"] == "PASS"


def test_sys18_detector_scopes_to_the_supplied_directions() -> None:
    responses, freqs = _detector_inputs(-12.0)
    responses["h=60,v=0"] = np.where(
        (freqs >= 1000.0 * 2.0 ** -0.5) & (freqs <= 1000.0 * 2.0 ** 0.5), -20.0, 0.0)
    result = score.flag_off_axis_cancellation(
        responses, freqs_hz=freqs, xo_hz=1000.0,
        direction_angles_deg={"h=+20,v=0": 20.0, "h=-20,v=0": -20.0, "h=60,v=0": 60.0},
        max_off_axis_deg=20.0)
    # Only the +-20 degree directions are inspected; the broad-side 60 degree peak is ignored.
    assert result["worst_direction"] in ("h=+20,v=0", "h=-20,v=0")
    assert result["status"] == "FAIL: vertical/oblique null"


def test_sys18_is_screen_only_when_on_axis_is_not_smooth() -> None:
    freqs = np.geomspace(200.0, 5000.0, 100)
    in_band = (freqs >= 1000.0 * 2.0 ** -0.5) & (freqs <= 1000.0 * 2.0 ** 0.5)
    on_axis = np.where(in_band, 8.0 * np.sin(np.linspace(0.0, 12.0 * np.pi, freqs.size)), 0.0)
    off_axis = np.full_like(freqs, -30.0)
    result = score.flag_off_axis_cancellation(
        {"on_axis": on_axis, "h=+20,v=0": off_axis}, freqs_hz=freqs, xo_hz=1000.0)
    assert result["status"] == "SCREEN_ONLY"
    assert result["on_axis_ripple_db"] > 3.0


def test_sys18_requires_a_frequency_axis_for_a_band_claim() -> None:
    responses, _ = _detector_inputs(-12.0)
    with pytest.raises(C.SchemaError, match="freqs_hz"):
        score.flag_off_axis_cancellation(responses, xo_hz=1000.0)
