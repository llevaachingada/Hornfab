"""R16 body-clearance gate: proven-gap PASS, proven VIOLATION, refused UNPROVEN.

Offline: synthetic closed cubes written with meshio (metres). The staging integration test
mocks BL's subprocess and validate call, so it exercises the real ``_stage`` bookkeeping
(manifest record + ``ok`` flip) without Boundary Lab. One replay test re-checks the two real
staged assembly cases when their gitignored run dirs are on disk.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import provenance  # noqa: E402
from hornlab_search.system.boundarylab import clearance as CL  # noqa: E402
from hornlab_search.system.boundarylab import run as bl_run  # noqa: E402
from hornlab_search.system.boundarylab import stage as S  # noqa: E402

from test_bl_stage import fake_bl_root  # noqa: E402


def write_cube(path: Path, lo, hi) -> Path:
    import meshio

    (x0, y0, z0), (x1, y1, z1) = lo, hi
    pts = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                    [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], dtype=float)
    tris = np.array([(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 4, 7), (0, 7, 3),
                     (1, 2, 6), (1, 6, 5), (0, 1, 5), (0, 5, 4), (3, 6, 2), (3, 7, 6)],
                    dtype=np.int64)
    path.parent.mkdir(parents=True, exist_ok=True)
    meshio.write(path, meshio.Mesh(points=pts, cells=[("triangle", tris)]),
                 file_format="gmsh22", binary=False)
    return path


@pytest.fixture()
def box(tmp_path: Path) -> Path:
    # Enclosure like BL's default vented box: front face at z = 0, body behind it.
    return write_cube(tmp_path / "exterior.msh", (-0.16, -0.25, -0.36), (0.16, 0.25, 0.0))


@pytest.fixture()
def horn(tmp_path: Path) -> Path:
    # A 0.2 m cube "horn" whose rear face sits at its local z = 0.
    return write_cube(tmp_path / "horn.msh", (-0.1, -0.1, 0.0), (0.1, 0.1, 0.2))


def test_aabb_gap_is_euclidean_and_zero_on_overlap() -> None:
    assert CL.aabb_gap_m((0, 0, 0), (1, 1, 1), (2, 0, 0), (3, 1, 1)) == pytest.approx(1.0)
    assert CL.aabb_gap_m((0, 0, 0), (1, 1, 1), (4, 5, 1), (5, 6, 2)) == pytest.approx(5.0)
    assert CL.aabb_gap_m((0, 0, 0), (1, 1, 1), (0.5, 0.5, 0.5), (2, 2, 2)) == 0.0


def test_translated_horn_with_proven_gap_passes(horn: Path, box: Path) -> None:
    rep = CL.body_clearance(horn, [box], translation_mm=(0, 0, 17))
    assert rep.status == CL.CLEARANCE_PASS and rep.ok
    assert rep.aabb_gap_m == pytest.approx(0.017)
    assert rep.vertex_min_distance_m is None          # not needed once the lower bound proves it
    assert rep.to_dict()["kind"] == "body_clearance_v1"


@pytest.fixture()
def flush_horn(tmp_path: Path) -> Path:
    # Same footprint as the box front face, so corner vertices line up (tight upper bound).
    return write_cube(tmp_path / "flush.msh", (-0.16, -0.25, 0.0), (0.16, 0.25, 0.2))


def test_horn_pushed_into_the_box_is_a_proven_violation(flush_horn: Path, box: Path) -> None:
    rep = CL.body_clearance(flush_horn, [box], translation_mm=(0, 0, -0.5))
    assert rep.status == CL.BODY_CLEARANCE_VIOLATION and not rep.ok
    assert rep.aabb_gap_m == 0.0
    assert rep.vertex_min_distance_m == pytest.approx(0.0005)


def test_gap_below_minimum_is_a_violation_even_without_contact(flush_horn: Path, box: Path) -> None:
    rep = CL.body_clearance(flush_horn, [box], translation_mm=(0, 0, 0.5))
    assert rep.status == CL.BODY_CLEARANCE_VIOLATION
    assert rep.aabb_gap_m == pytest.approx(0.0005)


def test_coarse_overlap_is_refused_as_unproven_not_passed(horn: Path, box: Path) -> None:
    # 8-vertex cubes: the vertex bound is loose (corners ~60 mm apart) although the bodies
    # overlap by 3 mm, so neither proof holds. The gate must still refuse.
    rep = CL.body_clearance(horn, [box], translation_mm=(0, 0, -3))
    assert rep.status == CL.BODY_CLEARANCE_UNPROVEN and not rep.ok
    assert rep.aabb_gap_m == 0.0


def test_nested_bodies_without_close_vertices_are_unproven(tmp_path: Path, box: Path) -> None:
    inner = write_cube(tmp_path / "inner.msh", (-0.05, -0.05, -0.25), (0.05, 0.05, -0.15))
    rep = CL.body_clearance(inner, [box])
    assert rep.status == CL.BODY_CLEARANCE_UNPROVEN
    assert rep.vertex_min_distance_m is not None and rep.vertex_min_distance_m > 1e-3


def test_scale_factor_is_applied_before_translation(tmp_path: Path, box: Path) -> None:
    mm_horn = write_cube(tmp_path / "horn_mm.msh", (-100, -100, 0), (100, 100, 200))
    rep = CL.body_clearance(mm_horn, [box], scale_factor=0.001, translation_mm=(0, 0, 5))
    assert rep.status == CL.CLEARANCE_PASS
    assert rep.aabb_gap_m == pytest.approx(0.005)


def test_bad_inputs_are_refused(horn: Path, box: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        CL.body_clearance(horn, [])
    with pytest.raises(ValueError):
        CL.body_clearance(horn, [box], min_gap_m=0.0)
    with pytest.raises(ValueError):
        CL.body_clearance(horn, [box], translation_mm=(0, 0))
    with pytest.raises(FileNotFoundError):
        CL.body_clearance(tmp_path / "missing.msh", [box])


# --------------------------------------------------------------------------- _stage wiring

def _mock_bl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, box: Path) -> None:
    project = tmp_path / "case" / "case.blab.json"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text("{}", encoding="utf-8")
    final = {"ok": True, "project_path": str(project), "output_dir": str(tmp_path),
             "meshes": [{"id": "exterior", "purpose": "bem_surface", "path": str(box)},
                        {"id": "interior", "purpose": "fem_volume", "path": str(box)}],
             "mesh_info": {}}
    monkeypatch.setattr(S, "_execute", lambda argv, timeout, cancel: (0, [json.dumps(final)]))
    monkeypatch.setattr(S.bl_run, "validate_project", lambda root, path: bl_run.ValidationResult(
        returncode=0, parsed={"valid": True}, stdout_tail=(), stderr_tail=(), argv=()))


@pytest.mark.parametrize("offset_z, ok, status", [
    (17.0, True, "PASS"),
    # The exact triangle-vs-box stage gate is stronger than the legacy AABB/vertex guard:
    # this synthetic 8-vertex cube overlaps the box by 3 mm, which is a proven crossing, not
    # merely an unproven ambiguity.
    (-3.0, False, "VIOLATION"),
])
def test_stage_horn_project_records_clearance_and_gates_ok(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, horn: Path, box: Path,
        offset_z: float, ok: bool, status: str) -> None:
    _mock_bl(monkeypatch, tmp_path, box)
    result = S.stage_horn_project(
        fake_bl_root(tmp_path), horn, source_group="g", translation_mm=(0, 0, offset_z),
        case_dir=tmp_path / "case",
    )
    assert result.ok is ok
    assert result.detail["clearance_status"] == status
    payload = provenance.load_manifest(result.manifest_path)["payload"]
    assert payload["clearance"]["status"] == status
    if not ok:
        assert any(status in line for line in result.captured_log_tail)
        assert "project_sha256" not in payload


def test_stage_reference_project_has_no_clearance_record(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, box: Path) -> None:
    _mock_bl(monkeypatch, tmp_path, box)
    result = S.stage_reference_project(fake_bl_root(tmp_path), case_dir=tmp_path / "case")
    assert result.ok is True
    assert "clearance_status" not in result.detail


# --------------------------------------------------------------------------- real-case replay

_RUNS = Path(__file__).resolve().parents[2] / "system_runs" / "system"
_REAL_CASES = {
    # staged, never solved: horn rear 3 mm inside the enclosure front plane
    "bl_ref_case/20261118T231100Z-assembly-62864-f62bf799": "BODY_CLEARANCE_VIOLATION",
    # the 20 mm assembly the smoke/G4 solves used (17 mm standoff)
    "bl_horn_assembly/20261118T224519Z-assembly-11000-4a85a0f8": "PASS",
}


@pytest.mark.parametrize("case, expected", sorted(_REAL_CASES.items()))
def test_real_staged_cases_replay(case: str, expected: str) -> None:
    case_dir = _RUNS / case
    spec_path = case_dir / "adapter_spec.json"
    exteriors = sorted(case_dir.glob("bl_output/*/exterior.msh"))
    if not spec_path.is_file() or not exteriors:
        pytest.skip(f"gitignored run dir not on disk: {case}")
    horn = json.loads(spec_path.read_text(encoding="utf-8"))["horn"]
    if not Path(horn["mesh_path"]).is_file():
        pytest.skip(f"horn mesh not on disk: {horn['mesh_path']}")
    rep = CL.body_clearance(horn["mesh_path"], exteriors, translation_mm=horn["translation_mm"],
                            scale_factor=horn.get("scale_factor", 1.0))
    assert rep.status == expected


# --------------------------------------------------------------------------- exact stage gate

_REAL_CASES_EXACT = {
    # dy = 0 puts the mouth ring in the middle of the cabinet: 27 horn vertices are inside
    # the solid, so the exact gate proves a collision the legacy AABB guard called ambiguous.
    "bl_ref_case/20261118T231100Z-assembly-62864-f62bf799": "VIOLATION",
    # the 20 mm forward assembly the smoke/G4 solves used: 17 mm standoff.
    "bl_horn_assembly/20261118T224519Z-assembly-11000-4a85a0f8": "PASS",
}


@pytest.mark.parametrize("case, expected", sorted(_REAL_CASES_EXACT.items()))
def test_real_staged_cases_exact_horn_box_gate(case: str, expected: str) -> None:
    from hornlab_search.system.boundarylab import collision as K

    case_dir = _RUNS / case
    spec_path = case_dir / "adapter_spec.json"
    exteriors = sorted(case_dir.glob("bl_output/*/exterior.msh"))
    if not spec_path.is_file() or not exteriors:
        pytest.skip(f"gitignored run dir not on disk: {case}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    horn, source = spec["horn"], spec["source"]
    if not Path(horn["mesh_path"]).is_file():
        pytest.skip(f"horn mesh not on disk: {horn['mesh_path']}")
    placed = K.transform_surface(K.read_surface(horn["mesh_path"]),
                                 translation_mm=horn["translation_mm"],
                                 scale_factor=horn.get("scale_factor", 1.0))
    box = K.box_from_cabinet_mm(width_mm=source["width_m"] * 1e3,
                                height_mm=source["height_m"] * 1e3,
                                depth_mm=source["depth_m"] * 1e3)
    rep = K.test_horn_box_clearance(placed, box, min_gap_m=0.001,
                                    compiled_exterior=K.read_surface(exteriors[0]))
    assert rep.status == expected
    assert rep.detail["compiled_exterior_matches_box"] is True
