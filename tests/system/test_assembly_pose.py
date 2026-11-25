"""Pose resolution and exact horn-to-cabinet clearance.

These tests pin the two defects that blocked a legal mouth-overhang assembly:

* a vertical mount offset must survive as world Y (never silently dropped to a Z-only
  translation), and
* an AABB/projected overlap must not be treated as a collision when the solids are apart.

They also pin the failures that must stay failures: a real penetration, a nested solid,
and an edge-to-edge gap below the declared minimum.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hornlab_search.system import assembly_pose as AP
from hornlab_search.system.boundarylab import collision as K

CABINET = {"external_width_mm": 320.0, "external_height_mm": 500.0, "external_depth_mm": 360.0}

#: The real full-domain horn the solved evidence cases used, when the store is present.
_REAL_HORN = Path(__file__).resolve().parents[2] / "system_runs" / "system" / "ref_case" / (
    "horn_full/lecleach_rollback_1in_v6_9e02db06ecc3/mesh.msh")


def _write_cube(path: Path, lo, hi) -> Path:
    import meshio
    import numpy as np

    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    signs = np.array([[i, j, k] for i in (0, 1) for j in (0, 1) for k in (0, 1)], dtype=float)
    points = lo + signs * (hi - lo)
    triangles = np.array([
        [0, 2, 1], [0, 3, 2], [4, 5, 7], [4, 7, 6], [0, 1, 4], [1, 5, 4],
        [1, 3, 7], [1, 7, 5], [3, 2, 6], [3, 6, 7], [2, 0, 4], [2, 4, 6]], dtype=np.int32)
    meshio.write(path, meshio.Mesh(points=points, cells=[("triangle", triangles)]))
    return path


def _write_frustum(path: Path, *, rear_half: float, mouth_half: float, depth: float) -> Path:
    """A closed square frustum in METRES: small throat ring at z=0, mouth ring at z=depth."""
    import meshio
    import numpy as np

    r, m, d = float(rear_half), float(mouth_half), float(depth)
    points = np.array([
        [-r, -r, 0.0], [r, -r, 0.0], [r, r, 0.0], [-r, r, 0.0],
        [-m, -m, d], [m, -m, d], [m, m, d], [-m, m, d]], dtype=float)
    triangles = np.array([
        [0, 2, 1], [0, 3, 2],          # rear cap (outward -z)
        [4, 5, 6], [4, 6, 7],          # mouth cap (outward +z)
        [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]], dtype=np.int32)
    meshio.write(path, meshio.Mesh(points=points, cells=[("triangle", triangles)]))
    return path


@pytest.fixture()
def box() -> K.Box:
    return K.box_from_cabinet_mm(width_mm=320.0, height_mm=500.0, depth_mm=360.0)


@pytest.fixture()
def cube(tmp_path: Path) -> Path:
    """A 200 mm cube; a prismatic body has no overhang, used for the conservative rule."""
    return _write_cube(tmp_path / "cube_mm.msh", (-0.1, 0.0, 0.0), (0.1, 0.2, 0.2))


@pytest.fixture()
def frustum(tmp_path: Path) -> Path:
    """20 mm throat ring, 150 mm mouth ring, 200 mm deep - the shape that overhangs."""
    return _write_frustum(tmp_path / "frustum.msh", rear_half=0.020, mouth_half=0.150,
                          depth=0.200)


# --------------------------------------------------------------------------- primitives

def test_box_model_matches_generated_exterior_bbox(box: K.Box, tmp_path: Path) -> None:
    exterior = _write_cube(tmp_path / "exterior.msh", box.lo, box.hi)
    ok, why = K._verify_box_matches_surface(box, K.read_surface(exterior))
    assert ok, why


def test_box_model_refuses_a_mismatched_exterior(box: K.Box, tmp_path: Path) -> None:
    exterior = _write_cube(tmp_path / "exterior.msh", (-0.16, -0.25, -0.36), (0.16, 0.25, 0.01))
    ok, _why = K._verify_box_matches_surface(box, K.read_surface(exterior))
    assert not ok


def test_edge_to_edge_distance_is_exact(box: K.Box) -> None:
    # The closest pair is edge-to-edge, 20 mm above the top face: neither a vertex of the
    # triangle nor of the box is that close.
    tri = K.surface_from_arrays([[0.0, 0.27, -0.10], [0.02, 0.27, -0.06], [-0.02, 0.27, -0.06]],
                                [[0, 1, 2]])
    result = K.triangle_surface_box_distance(tri, box, cutoff_m=0.05)
    assert result["min_distance_m"] == pytest.approx(0.02, abs=1e-12)
    assert result["exact"] is True


def test_triangle_through_the_box_face_is_detected(box: K.Box) -> None:
    tri = K.surface_from_arrays([[0.0, 0.24, 0.0], [0.05, 0.26, -0.1], [-0.05, 0.26, -0.05]],
                                [[0, 1, 2]])
    result = K.triangle_surface_box_distance(tri, box, cutoff_m=0.05)
    assert result["intersecting"] is True
    assert result["min_distance_m"] == 0.0


# --------------------------------------------------------------------------- pose policy

def test_above_layout_keeps_the_whole_envelope_clear(frustum: Path) -> None:
    pose = AP.resolve_pose(frustum, cabinet=CABINET, layout=AP.LAYOUT_ABOVE, dz_mm=0.0,
                           clearance_mm=3.0)
    # the 150 mm mouth half-height governs: 250 + 150 + 3
    assert pose.dy_mm == pytest.approx(403.0, abs=1e-9)
    assert pose.support == "seated_on_cabinet_top"
    assert pose.silhouette["front_view_y_overlap_mm"] == 0.0


def test_prismatic_body_has_no_overhang_under_either_rule(cube: Path) -> None:
    above = AP.resolve_pose(cube, cabinet=CABINET, layout=AP.LAYOUT_ABOVE, dz_mm=0.0,
                            clearance_mm=3.0)
    seated = AP.resolve_pose(cube, cabinet=CABINET, layout=AP.LAYOUT_SEATED_OVERHANG,
                             dz_mm=0.0, clearance_mm=3.0)
    assert seated.dy_mm == pytest.approx(above.dy_mm)
    assert seated.silhouette["front_view_y_overlap_mm"] == 0.0


def test_seated_overhang_drops_below_the_top_line_and_still_passes(frustum: Path) -> None:
    pose = AP.resolve_pose(frustum, cabinet=CABINET, layout=AP.LAYOUT_SEATED_OVERHANG,
                           dz_mm=0.0, clearance_mm=3.0)
    # The 20 mm throat ring governs, not the 150 mm mouth: 250 + 3 + 20.
    assert pose.dy_mm == pytest.approx(273.0, abs=1e-9)
    assert pose.legal
    assert pose.clearance["min_distance_m"] == pytest.approx(0.003, abs=1e-9)
    # ... and the mouth now overlaps the cabinet in the front view: 250 - (273 - 150).
    assert pose.silhouette["front_view_y_overlap_mm"] == pytest.approx(127.0, abs=1e-9)
    assert pose.silhouette["front_view_x_overlap_mm"] == pytest.approx(300.0, abs=1e-9)


def test_manual_drop_into_the_box_is_refused(frustum: Path) -> None:
    with pytest.raises(AP.PlacementIllegal, match="not legal"):
        AP.resolve_pose(frustum, cabinet=CABINET, layout=AP.LAYOUT_SEATED_OVERHANG,
                        dz_mm=0.0, dy_mm=200.0, clearance_mm=3.0)


def test_cantilever_requires_an_explicit_dy(frustum: Path) -> None:
    with pytest.raises(AP.PlacementIllegal, match="cantilever"):
        AP.resolve_pose(frustum, cabinet=CABINET, layout=AP.LAYOUT_SEATED_OVERHANG,
                        dz_mm=50.0, clearance_mm=3.0)
    pose = AP.resolve_pose(frustum, cabinet=CABINET, layout=AP.LAYOUT_SEATED_OVERHANG,
                           dz_mm=50.0, dy_mm=273.0, clearance_mm=3.0)
    assert pose.support == "unmodeled_cantilever"
    assert pose.legal


def test_pose_roundtrip_preserves_translation_and_identity(frustum: Path) -> None:
    pose = AP.resolve_pose(frustum, cabinet=CABINET, dz_mm=0.0, clearance_mm=3.0)
    again = AP.AssemblyPose.from_dict(json.loads(json.dumps(pose.to_dict())))
    assert again.translation_mm == pose.translation_mm
    assert again.geometry_id == pose.geometry_id
    assert again.transform_m[1][3] == pytest.approx(pose.dy_mm / 1e3)


def test_pose_refuses_a_metres_for_millimetres_offset(frustum: Path) -> None:
    with pytest.raises(AP.PlacementIllegal, match="metres"):
        AP.resolve_pose(frustum, cabinet=CABINET, dz_mm=0.0, dy_mm=50_000.0, clearance_mm=3.0)


def test_negative_clearance_is_refused(frustum: Path) -> None:
    with pytest.raises(ValueError):
        AP.resolve_pose(frustum, cabinet=CABINET, dz_mm=0.0, clearance_mm=0.0)


# --------------------------------------------------------------------------- real geometry

@pytest.mark.skipif(not _REAL_HORN.is_file(), reason="real full-domain horn not on disk")
def test_real_horn_owner_arrangement() -> None:
    """The photo arrangement, from the real mesh: seated, mouth overhanging, apart."""
    pose = AP.resolve_pose(_REAL_HORN, cabinet=CABINET,
                          layout=AP.LAYOUT_SEATED_OVERHANG, dz_mm=0.0, clearance_mm=3.0,
                          horn_design_hash="f04827bc5973")
    assert pose.support == "seated_on_cabinet_top"
    # the real throat governs (~15.67 mm half-height), not the 116.67 mm mouth radius
    assert pose.dy_mm == pytest.approx(268.674, abs=0.01)
    assert pose.silhouette["front_view_y_overlap_mm"] == pytest.approx(98.0, abs=0.2)
    assert pose.clearance["status"] == "PASS"
    assert pose.clearance["min_distance_m"] == pytest.approx(0.003, abs=1e-6)


@pytest.mark.skipif(not _REAL_HORN.is_file(), reason="real full-domain horn not on disk")
def test_real_horn_legacy_forward_only_pose_is_a_proven_collision() -> None:
    """dz=0 with dy=0 (what the old seam staged) puts the mouth ring inside the cabinet."""
    with pytest.raises(AP.PlacementIllegal, match="inside the cabinet"):
        AP.resolve_pose(_REAL_HORN, cabinet=CABINET, layout=AP.LAYOUT_SEATED_OVERHANG,
                        dz_mm=0.0, dy_mm=0.0, clearance_mm=3.0)
