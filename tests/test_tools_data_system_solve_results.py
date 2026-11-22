"""Offline tests for the portable system result exporter (no real store, no solver)."""
from __future__ import annotations

import importlib.util
from types import SimpleNamespace

import numpy as np

from conftest import REPO

TOOL = REPO / "tools" / "data" / "system_solve_results.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("system_solve_results_tool", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _observation(domain_id: str, kind: str, points, angles=None, distance=2.0):
    return SimpleNamespace(
        domain_id=domain_id, kind=kind, points_m=np.asarray(points, dtype=float),
        angles_deg=None if angles is None else np.asarray(angles, dtype=float),
        distance_m=distance,
    )


def _field(excitation: str, observation, values):
    return SimpleNamespace(
        excitation_id=excitation, observation=observation,
        p_pa=np.asarray(values, dtype=np.complex128),
        basis=SimpleNamespace(per_input="V_rms"),
    )


def test_fmt_and_db_are_bounded_and_empty_on_undefined() -> None:
    tool = _load_tool()
    assert tool._fmt(1.23456789123) == "1.23456789"
    assert tool._fmt(None) == ""
    assert tool._fmt(float("nan")) == ""
    assert tool._db(0.5, 1.0) == "-6.0206"
    assert tool._db(1.0, 0.0) == ""


def test_axis_index_uses_polar_zero_and_on_axis_probe() -> None:
    tool = _load_tool()
    polar = _observation(
        "observation:horizontal-polar", "polar_observation",
        [[0, 0, 2], [1, 0, 1.732], [-1, 0, 1.732]], angles=[0.0, 30.0, -30.0])
    assert tool._axis_index(polar) == 0

    probe = _observation(
        "observation:probe:on_axis_2m", "point_probe", [[0, 0, 2]])
    assert tool._axis_index(probe) == 0

    off_axis = _observation(
        "observation:probe:up30_2m", "point_probe", [[0, 1, 1.732]])
    assert tool._axis_index(off_axis) is None


def test_axis_map_prefers_the_explicit_probe_over_the_polar_zero() -> None:
    tool = _load_tool()
    polar = _observation(
        "observation:horizontal-polar", "polar_observation",
        [[0, 0, 2], [1, 0, 1.732]], angles=[0.0, 30.0])
    probe = _observation(
        "observation:probe:on_axis_2m", "point_probe", [[0, 0, 2]])
    result = SimpleNamespace(fields=(
        _field("vented/voltage", polar, [[1.0, 0.1], [2.0, 0.2]]),
        _field("vented/voltage", probe, [[3.0], [4.0]]),
    ))
    axes = tool._axis_map(result)
    assert axes[("vented/voltage", 0)] == 3.0
    assert axes[("vented/voltage", 1)] == 4.0


def test_flatten_keeps_nested_keys_and_json_encodes_lists() -> None:
    tool = _load_tool()
    flat = tool._flatten({"box": {"net_volume_l": 115.0}, "tags": ["a", "b"]})
    assert flat["box.net_volume_l"] == 115.0
    assert flat["tags"] == '["a", "b"]'
