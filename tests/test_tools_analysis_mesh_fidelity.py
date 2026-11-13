"""Offline tests for tools/analysis/mesh_fidelity.py (A4).

A hand-written gmsh ASCII v2.2 fixture with two physical tags and known edge lengths. No gmsh,
BEM or GPU import beyond the read-only ``.msh`` reader.
"""
from __future__ import annotations

import importlib.util
import math
import sys

import numpy as np

from conftest import REPO

_TOOL = REPO / "tools" / "analysis" / "mesh_fidelity.py"


def _load_tool(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mf = _load_tool("mesh_fidelity_tool", _TOOL)

# Tag 1 "SD1D1001" (source): triangle (1,2,3), edges 0.01, sqrt(2)*0.01, 0.01 m.
# Tag 2 "WALL": triangle (1,5,6), edges 0.1, sqrt(2)*0.1, 0.1 m.
_MSH = """$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
2
2 1 "SD1D1001"
2 2 "WALL"
$EndPhysicalNames
$Nodes
6
1 0 0 0
2 0.01 0 0
3 0 0.01 0
4 0.01 0.01 0
5 0.1 0 0
6 0 0.1 0
$EndNodes
$Elements
2
1 2 2 1 1 1 2 3
2 2 2 2 2 1 5 6
$EndElements
"""


def _write_mesh(directory, text=_MSH):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "mesh.msh"
    path.write_text(text, encoding="utf-8")
    return path


def test_per_tag_percentiles_and_source_only_status(tmp_path):
    msh = _write_mesh(tmp_path / "design")
    report = mf.build_report(msh, fmax=1000.0, epw=6.0)

    by_name = {r["name"]: r for r in report["tags"]}
    assert set(by_name) == {"SD1D1001", "WALL"}
    src = by_name["SD1D1001"]
    wall = by_name["WALL"]

    src_edges_mm = np.array([10.0, 10.0 * math.sqrt(2.0), 10.0])
    assert src["n_triangles"] == 1 and wall["n_triangles"] == 1
    assert math.isclose(src["edge_mm_max"], 10.0 * math.sqrt(2.0), rel_tol=1e-9)
    assert math.isclose(src["edge_mm_p50"], float(np.percentile(src_edges_mm, 50)), rel_tol=1e-9)
    assert math.isclose(src["edge_mm_p95"], float(np.percentile(src_edges_mm, 95)), rel_tol=1e-9)
    assert math.isclose(wall["edge_mm_max"], 100.0 * math.sqrt(2.0), rel_tol=1e-9)

    limit_mm = 343.0 / (6.0 * 1000.0) * 1000.0
    assert math.isclose(report["h_max_limit_mm"], limit_mm, rel_tol=1e-9)
    assert src["valid"] is True and wall["valid"] is False
    k = 2.0 * math.pi * 1000.0 / 343.0
    assert math.isclose(src["k_h_max"], k * 0.01 * math.sqrt(2.0), rel_tol=1e-9)

    assert report["mesh_fidelity_status"] == "source_valid_only"
    assert report["mesh_meta"] is None
    # Read-only: nothing new appears beside the mesh.
    assert sorted(p.name for p in msh.parent.iterdir()) == ["mesh.msh"]


def test_no_fmax_is_not_assessed_and_unnamed_tags_fall_back(tmp_path):
    unnamed = _MSH.replace('$PhysicalNames\n2\n2 1 "SD1D1001"\n2 2 "WALL"\n$EndPhysicalNames\n', "")
    msh = _write_mesh(tmp_path / "design", unnamed)
    (msh.parent / "mesh_meta.json").write_text('{"res_mm": 4.0, "rear_res_factor": 2.0}',
                                               encoding="utf-8")
    report = mf.build_report(msh)

    assert report["mesh_fidelity_status"] == "not_assessed"
    assert report["fmax_hz"] is None and report["h_max_limit_mm"] is None
    assert all(r["valid"] is None and r["k_h_max"] is None for r in report["tags"])
    assert {r["name"] for r in report["tags"]} == {"tag_1", "tag_2"}
    assert report["mesh_meta"] == {"res_mm": 4.0, "rear_res_factor": 2.0}
