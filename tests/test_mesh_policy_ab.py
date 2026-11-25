"""Offline tests for tools/analysis/mesh_policy_ab.py arm parsing/row shaping.

The mesh build itself needs gmsh and is exercised by the evidence run; CI only pins the pure
arm naming and CSV row contract so a typo cannot silently change an arm identity.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "analysis" / "mesh_policy_ab.py"

_spec = importlib.util.spec_from_file_location("mesh_policy_ab", TOOL)
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)


def test_parse_arms_and_names():
    assert policy._parse_arms("1.0:1, 1.5:1 ,2:1.5") == [(1.0, 1.0), (1.5, 1.0), (2.0, 1.5)]
    assert policy._arm_name(1.5, 1.0) == "rear1.5_epw1"
    assert policy._arm_name(2.0, 2.0) == "rear2_epw2"
    with pytest.raises(ValueError):
        policy._parse_arms("1.5")
    with pytest.raises(ValueError):
        policy._parse_arms("0:1")


def test_ab_row_keeps_policy_and_region_medians():
    report = {
        "n_vertices": 100,
        "dof_estimate": 51,
        "res_mm": {"throat": 2.0, "mouth": 4.0, "rear": 6.0},
        "unknown_triangle_fraction": 0.0,
        "regions": [
            {"region": "inner_bore", "edge_mm_p50": 3.0, "n_triangles": 60},
            {"region": "outer_shell", "edge_mm_p50": 6.0, "n_triangles": 40},
        ],
    }
    arm = {
        "arm": "rear1.5_epw1", "rear_res_factor": 1.5, "epw_multiplier": 1.0,
        "epw": 6.0, "f_max_hz": 8000.0, "n_triangles": 100, "n_vertices": 100,
        "dof_estimate": 51, "mesh_seconds": 2.0, "res_mm": report["res_mm"],
        "regions": report["regions"], "report": report,
    }
    row = policy._ab_row("run", "abc123", arm)
    assert row["res_rear_mm"] == 6.0
    assert row["inner_p50_mm"] == 3.0 and row["outer_p50_mm"] == 6.0
    assert row["inner_triangles"] == 60 and row["outer_triangles"] == 40
    assert set(policy.AB_COLUMNS) <= set(row)
