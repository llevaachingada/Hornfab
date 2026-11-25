"""Offline tests for tools/analysis/mesh_region_audit.py (no mesher, no GPU).

The tool is read-only: a synthetic gmsh 2.2 ASCII mesh exercises the tag-led path, and the pure
helpers are checked directly.  The producer-geometry path needs a real mesher config and is
covered by the evidence run, not by CI.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "analysis" / "mesh_region_audit.py"

_spec = importlib.util.spec_from_file_location("mesh_region_audit", TOOL)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def _write_mesh(path: Path) -> None:
    path.write_text(
        "$MeshFormat\n"
        "2.2 0 8\n"
        "$EndMeshFormat\n"
        '$PhysicalNames\n2\n2 1 "SD1G0"\n2 2 "SD1D1001"\n$EndPhysicalNames\n'
        "$Nodes\n4\n"
        "1 0 0 0\n2 0.001 0 0\n3 0 0.001 0\n4 0.001 0.001 0\n"
        "$EndNodes\n"
        "$Elements\n2\n"
        "1 2 2 1 1 1 2 3\n"
        "2 2 2 2 1 2 3 4\n"
        "$EndElements\n",
        encoding="utf-8",
    )


def test_tag_only_report_from_a_stored_mesh(tmp_path):
    mesh = tmp_path / "mesh.msh"
    _write_mesh(mesh)
    report = audit.build_report(mesh, fmax=1000.0, epw=6.0)
    assert report["region_source"] == "physical_tags"
    assert report["n_triangles"] == 2
    assert report["n_vertices"] == 4
    regions = {r["region"]: r for r in report["regions"]}
    assert regions["source"]["n_triangles"] == 1
    assert regions["tag_1_wall"]["n_triangles"] == 1
    assert regions["source"]["edge_mm_max"] == pytest.approx(math.hypot(1.0, 1.0), rel=1e-9)
    # 1 mm edge at 1 kHz: lambda = 343 mm, so h/lambda is small and finite.
    assert 0.0 < regions["source"]["h_max_over_lambda"] < 0.01


def test_dihedral_is_zero_for_coplanar_and_90_for_a_fold():
    xyz = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                    [1.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    coplanar = np.array([[0, 1, 2], [1, 3, 2]])
    assert audit._dihedral_deg(coplanar, xyz).max() == pytest.approx(0.0)
    folded = np.array([[0, 1, 2], [0, 1, 4]])
    ang = audit._dihedral_deg(folded, xyz)
    assert ang.max() == pytest.approx(90.0, abs=1e-9)


def test_requested_inner_size_interpolates_and_clamps():
    assert audit._requested_inner_mm(0.0, 0.0, 100.0, 2.0, 8.0) == pytest.approx(2.0)
    assert audit._requested_inner_mm(50.0, 0.0, 100.0, 2.0, 8.0) == pytest.approx(5.0)
    assert audit._requested_inner_mm(200.0, 0.0, 100.0, 2.0, 8.0) == pytest.approx(8.0)


def test_triangle_quality_and_area_weighting():
    xyz = np.array([[0.0, 0.0, 0.0], [0.01, 0.0, 0.0], [0.0, 0.01, 0.0]])
    tri = np.array([[0, 1, 2]])
    edges, area, aspect, min_angle = audit._triangle_metrics(xyz, tri)
    assert area[0] == pytest.approx(5e-5)
    assert edges.max() == pytest.approx(math.hypot(0.01, 0.01))
    assert aspect[0] == pytest.approx(1.0 + math.sqrt(2.0), rel=1e-6)
    assert min_angle[0] == pytest.approx(45.0)
    vals = np.array([1.0, 10.0])
    weights = np.array([9.0, 1.0])
    p50 = audit._weighted_percentiles(vals, weights, [50.0])[0]
    assert p50 < 5.0


def test_tag_only_regions_do_not_invent_geometry():
    tags = np.array([1, 2, 3, 8, 9, 10, 11, 12, 99])
    regions = audit._tag_only_regions(tags)
    assert regions.tolist() == [
        "tag_1_wall", "source", "enclosure", "mid_chamber", "port_interior",
        "mid_port_exit", "mid_port_exit", "mouth_aperture", "unknown",
    ]
