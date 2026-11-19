"""Stage 4 CPU pre-work tests: horn mesh QA, scale guard, draft validate loop, import kinds."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system.boundarylab import assemble  # noqa: E402
from hornlab_search.system.boundarylab import import_results as IR  # noqa: E402
from hornlab_search.system.boundarylab.probe import probe_boundarylab  # noqa: E402

REAL_MESH = Path(r"C:/Users/hunte/Hrns/hornlab-search/runs/20261118T200653Z-screen-31495a"
                 "/designs/949cc3684ab6/mesh.msh")


def _write_surface_mesh(path: Path, *, closed: bool, points_m: np.ndarray, tris: np.ndarray,
                        groups: dict[str, int] | None = None) -> None:
    import meshio

    cells = [("triangle", tris)]
    cell_data: dict[str, list] = {}
    if groups:
        tags = np.zeros(len(tris), dtype=np.int64)
        cell_data["gmsh:physical"] = [tags]
        field = {name: np.array([tag, 2]) for name, tag in groups.items()}
    else:
        field = {}
    meshio.write(path, meshio.Mesh(points_m, cells, cell_data=cell_data, field_data=field))


def _closed_box_m(scale_m: float = 0.3) -> tuple[np.ndarray, np.ndarray]:
    """A closed, consistently-outward triangle box: 8 corners, 12 triangles."""
    s = scale_m
    p = np.array([[0, 0, 0], [s, 0, 0], [s, s, 0], [0, s, 0],
                  [0, 0, s], [s, 0, s], [s, s, s], [0, s, s]], dtype=float)
    quads = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b, c, d in quads:
        tris.append((a, b, c))
        tris.append((a, c, d))
    out = np.array(tris, dtype=np.int64)
    # enforce outward winding per face via sign of normal dot (face_center - box_center)
    center = p.mean(axis=0)
    for i, (a, b, c) in enumerate(out):
        n = np.cross(p[b] - p[a], p[c] - p[a])
        if np.dot(n, p[[a, b, c]].mean(axis=0) - center) < 0:
            out[i] = (a, c, b)
    return p, out


def test_horn_mesh_qa_classifies_the_real_quarter_patch() -> None:
    """The saved HornLab mesh is a quarter-model patch: free edges live on x=0/y=0 planes."""
    if not REAL_MESH.is_file():
        pytest.skip("canonical run mesh not present")
    qa = assemble.horn_mesh_qa(REAL_MESH)
    assert qa.closed is False and qa.symmetric_patch is True
    assert qa.full_open_holes == 0
    assert qa.free_edges == qa.free_edges_on_symmetry_planes > 0
    assert qa.orientation_consistent is True
    assert qa.duplicate_points == 0
    # metres: a 12-inch-class horn bbox within ~0.05..0.6 m, x/y start at the symmetry planes
    lo, hi = np.array(qa.bbox_min_m), np.array(qa.bbox_max_m)
    assert np.all(lo > -0.05) and np.all(hi < 1.0)
    assert abs(lo[0]) < 1e-9 and abs(lo[1]) < 1e-9


def test_qa_detects_open_and_punctured_meshes(tmp_path: Path) -> None:
    pts, tris = _closed_box_m()
    _write_surface_mesh(tmp_path / "closed.msh", closed=True, points_m=pts, tris=tris)
    qa = assemble.horn_mesh_qa(tmp_path / "closed.msh")
    assert qa.closed is True and qa.orientation_consistent is True
    assert qa.free_edges == 0 and qa.full_open_holes == 0
    # drop a TOP-face triangle (z=s): its 3 free edges lie on the z=s plane, NOT on any
    # symmetry plane (x=0/y=0) -> classified as true holes, not a symmetric patch
    top_idx = int(np.nonzero(np.all(np.abs(pts[tris, 2] - pts[:, 2].max()) < 1e-12, axis=1))[0][0])
    _write_surface_mesh(tmp_path / "open.msh", closed=True, points_m=pts,
                        tris=np.delete(tris, top_idx, axis=0))
    qa_open = assemble.horn_mesh_qa(tmp_path / "open.msh")
    assert qa_open.closed is False and qa_open.full_open_holes > 0
    with pytest.raises(C.DataQualityError, match="true [\\s]*holes|NOT on symmetry"):
        assemble.plan_assembly(tmp_path / "open.msh", _fake_box(), out_dir=tmp_path,
                               validate_draft=False)


def test_plan_assembly_records_symmetric_patch_as_blocker(tmp_path: Path) -> None:
    """A HornLab quarter patch is honest blocked-by evidence, never silently closed."""
    inv = _realish_quarter_patch(tmp_path)
    plan = assemble.plan_assembly(inv, _fake_box(), validate_draft=False)
    assert plan.horn_mesh.symmetric_patch is True
    assert plan.blockers and plan.blockers[0].startswith("BLOCKED_BY_FULL_DOMAIN_HORN_MESH")
    assert "162" in plan.blockers[0] or f"{plan.horn_mesh.free_edges}" in plan.blockers[0]


def _realish_quarter_patch(tmp_path: Path) -> Path:
    """An open half-cube: the x=0 face removed, so every free edge lies ON the x=0 plane."""
    import meshio

    pts, tris = _closed_box_m()
    drop = np.all(np.abs(pts[tris, 0]) < 1e-12, axis=1)   # ALL three vertices on x=0
    keep = tris[~drop]
    path = tmp_path / "quarter.msh"
    meshio.write(path, meshio.Mesh(pts, [("triangle", keep)]))
    return path


def test_scale_guard_refuses_mm_factor_for_hornfab_meshes(tmp_path: Path) -> None:
    pts, tris = _closed_box_m()
    _write_surface_mesh(tmp_path / "h.msh", closed=True, points_m=pts, tris=tris)
    with pytest.raises(C.DataQualityError, match="already in METRES"):
        assemble._imported_row(tmp_path / "h.msh", "horn", 0.001, (0.0, 0.0, 0.0))


def _fake_box() -> C.BoxPoint:
    return C.BoxPoint(kind="vented", external_width_mm=371.2, external_height_mm=371.2,
                      external_depth_mm=378.8, net_volume_l=35.0, wall_mm=18.0,
                      port_type="round_flared", port_throat_area_cm2=60.0, port_nfr=0.0,
                      requested_tuning_hz=35.0, derived_effective_port_length_m=0.18,
                      derived_tuning_hz=35.0)


def test_plan_assembly_records_bl_validate_gaps_not_guesses(tmp_path: Path) -> None:
    pts, tris = _closed_box_m()
    _write_surface_mesh(tmp_path / "horn.msh", closed=True, points_m=pts, tris=tris,
                        groups={"SD1G0": 1, "SD1D1001": 2})
    # draft-only path (no BL): documented keys, determinism, identity
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    draft = assemble.write_draft_project(case_dir, assemble._imported_row(
        tmp_path / "horn.msh", "horn", 1.0, (0.0, 0.0, 0.0)), _fake_box())
    assert draft.is_file()
    payload = json.loads(draft.read_text(encoding="utf-8"))
    assert set(payload) == {"schema_version", "active_generator_document_id",
                            "generator_documents", "imported_meshes", "stitch_exterior_meshes",
                            "physical_system", "component_channel_by_id", "observation_planes"}
    assert payload["imported_meshes"][0]["scale_factor"] == 1.0
    plan1 = assemble.plan_assembly(tmp_path / "horn.msh", _fake_box(), validate_draft=False)
    plan2 = assemble.plan_assembly(tmp_path / "horn.msh", _fake_box(), validate_draft=False)
    assert plan1.assembly_id == plan2.assembly_id
    assert plan1.blockers == ()


def test_validate_draft_enumerates_bl_expections_on_real_install(tmp_path: Path) -> None:
    """REAL BL validate of the DRAFT: its exact errors are the recorded Stage-4 host-work list."""
    probe = probe_boundarylab(extra_roots=["C:/Users/hunte/Github/boundary-lab"],
                              use_default_roots=False)
    if probe.verified_root is None:
        pytest.skip("verified Boundary Lab not present")
    pts, tris = _closed_box_m()
    _write_surface_mesh(tmp_path / "horn.msh", closed=True, points_m=pts, tris=tris)
    out = tmp_path / "store"
    plan = assemble.plan_assembly(tmp_path / "horn.msh", _fake_box(), out_dir=out,
                                  bl_root=probe.verified_root)
    assert plan.draft_project_path is not None and plan.validate_result is not None
    vr = plan.validate_result
    if vr.returncode == 0 and (vr.parsed or {}).get("valid"):
        assert not plan.blockers, "unexpected draft validity; update the record"
    else:
        assert plan.blockers and plan.blockers[0] == assemble.BLOCKED_BY_HOST_ASSEMBLY_ASSIGNMENTS
        assert any("physical" in e.lower() or "artifact" in e.lower() or "region" in e.lower()
                   for e in plan.blockers), plan.blockers


def test_import_results_kind_detection_and_refusals(tmp_path: Path) -> None:
    art = IR.detect_result_artifact(__import__("pathlib").Path(
        r"C:/Users/hunte/Github/boundary-lab/examples/Simple_Sealed/simple_sealed.blab.json"))
    assert art.kind == "blab_project" and art.manifest is not None
    assert any("not solved results" in n for n in art.notes)
    with pytest.raises(FileNotFoundError):
        IR.detect_result_artifact(tmp_path / "missing.blabsp")
    # a minimal but honest .blabsp zip (manifest only) reads at manifest level
    zpath = tmp_path / "mini.blabsp"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"schema_version": 1, "level": 1}))
    out = IR.read_blabsp_manifest(zpath)
    assert out["level"] == 1 and "_present_sections" in out
    other = tmp_path / "blob.bin"
    other.write_bytes(b"not a zip")
    art = IR.detect_result_artifact(other)
    assert art.kind == "unknown"
