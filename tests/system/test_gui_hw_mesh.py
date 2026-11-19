"""3-D geometry data layer (P3): box and horn meshes in mm, store-contained, no solver.

Builds a throwaway system store in ``tmp_path`` the same way ``test_gui_hw`` does (manifests
written by the real ``provenance.write_manifest``, cubes from ``test_clearance.write_cube``)
and drives ``gui/data_hw.hw_mesh``. Nothing here touches the network, a solver or Boundary Lab.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw as HW  # noqa: E402
from hornlab_search.gui.data import clean  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402

from test_clearance import write_cube  # noqa: E402

SOURCE = {"width_m": 0.32, "height_m": 0.5, "depth_m": 0.36, "wall_m": 0.018,
          "driver_diameter_m": 0.2, "driver_y_m": 0.1, "port_area_m2": 0.0028,
          "port_length_m": 0.22, "port_y_m": -0.13, "port_nfr": 0.12,
          "mesh_size_m": 0.04, "detail_size_m": 0.012}

KEY = "bl_horn/20261118T000000Z-ok-2-bbbb"


def _case(store: Path, exp: str, name: str, payload: dict | None) -> Path:
    d = store / "system" / exp / name
    d.mkdir(parents=True)
    if payload is not None:
        provenance.write_manifest(d, payload)
    return d


def _staged_horn(store: Path, exp: str, name: str, offset_mm: float, horn_mesh: Path) -> Path:
    d = store / "system" / exp / name
    ext = write_cube(d / "bl_output" / "vented_x" / "exterior.msh", (-0.16, -0.25, -0.36), (0.16, 0.25, 0.0))
    assert ext.is_file()
    provenance.write_manifest(d, {
        "kind": "bl_stage_horn_project", "project_sha256": "ab" * 32,
        "validate": {"returncode": 0, "valid": True},
        "spec": {"source": SOURCE, "horn": {"mesh_path": str(horn_mesh), "translation_mm": [0, 0, offset_mm],
                                            "scale_factor": 1.0, "source_group": "throat",
                                            "mesh_role": "full_domain"}},
        "result": {"ok": True}})
    return d


def _write_grid_mesh(path: Path, n: int) -> Path:
    """A wavy n x n surface: 2*(n-1)^2 triangles (n=200 -> 79202, over the 60k cap)."""
    import meshio

    x = np.linspace(0.0, 1.0, n)
    yy, xx = np.meshgrid(x, x, indexing="ij")
    zz = 0.15 * np.sin(np.pi * xx) * np.sin(np.pi * yy)
    pts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])
    idx = np.arange(n * n).reshape(n, n)
    a = idx[:-1, :-1].ravel()
    b = idx[1:, :-1].ravel()
    c = idx[1:, 1:].ravel()
    d = idx[:-1, 1:].ravel()
    tris = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])]).astype(np.int64)
    path.parent.mkdir(parents=True, exist_ok=True)
    meshio.write(path, meshio.Mesh(points=pts, cells=[("triangle", tris)]),
                 file_format="gmsh22", binary=False)
    return path


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "repo"
    store = root / "system_runs"
    horn = write_cube(store / "system" / "ref_case" / "horn_full" / "h1" / "mesh.msh",
                      (-0.16, -0.25, 0.0), (0.16, 0.25, 0.2))
    _staged_horn(store, "bl_horn", "20261118T000000Z-ok-2-bbbb", 17.0, horn)
    HW._CACHE.clear()
    return root, store


def test_box_and_horn_are_mm_in_the_bl_frame(env) -> None:
    root, store = env
    box = HW.hw_mesh(root, store, KEY, "box")
    assert box["key"] == KEY and box["part"] == "box" and box["units"] == "mm"
    assert "x width, y height, z forward" in box["frame"]
    assert box["decimated"] is False
    assert box["triangle_count"] == 12 and len(box["tris"]) == 36
    assert len(box["verts"]) == 24
    assert box["bbox"][0] == pytest.approx([-160.0, -250.0, -360.0])
    assert box["bbox"][1] == pytest.approx([160.0, 250.0, 0.0])
    assert box["source_files"] == [f"system/bl_horn/{KEY.split('/')[1]}/bl_output/vented_x/exterior.msh"]

    horn = HW.hw_mesh(root, store, KEY, "horn")
    assert horn["part"] == "horn" and horn["units"] == "mm"
    assert horn["decimated"] is False
    assert horn["triangle_count"] == 12 and len(horn["tris"]) == 36
    # local cube z in 0..200 mm, recorded translation +17 mm on z
    assert horn["bbox"][0] == pytest.approx([-160.0, -250.0, 17.0])
    assert horn["bbox"][1] == pytest.approx([160.0, 250.0, 217.0])
    assert horn["source_files"] == ["system/ref_case/horn_full/h1/mesh.msh"]


def test_horn_mesh_outside_the_store_is_refused_without_reading(env, tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    root, store = env
    name = "20261118T000009Z-out-6-gggg"
    key = f"bl_horn/{name}"
    outside = write_cube(tmp_path / "elsewhere" / "mesh.msh", (-0.1, -0.1, 0.0), (0.1, 0.1, 0.2))
    _staged_horn(store, "bl_horn", name, 17.0, outside)
    outside.unlink()                     # a read attempt would now be a different error

    import meshio

    def boom(*a, **k):
        raise AssertionError("a mesh outside the store must never be read")
    monkeypatch.setattr(meshio, "read", boom)
    with pytest.raises(FileNotFoundError) as excinfo:
        HW.hw_mesh(root, store, key, "horn")
    message = str(excinfo.value)
    assert "outside the store" in message and "refusing to read it" in message
    assert not outside.exists()


@pytest.mark.parametrize("part", ["walls", "", None])
def test_part_is_validated(env, part) -> None:
    root, store = env
    with pytest.raises(ValueError) as excinfo:
        HW.hw_mesh(root, store, KEY, part)
    message = str(excinfo.value)
    assert "box" in message and "horn" in message


def test_solve_only_case_uses_the_parent_exterior(env) -> None:
    root, store = env
    parent = store / "system" / "bl_horn" / "20261118T000000Z-ok-2-bbbb"
    wide = _case(store, "bl_smoke_wide", "20261118T231115Z-wide-1-aaaa", {
        "kind": "bl_wide_study_v1", "project": str(parent / "case.blab.json"),
        "run": {"status": "complete"}})
    key = "bl_smoke_wide/20261118T231115Z-wide-1-aaaa"
    assert not (wide / "bl_output").exists()          # the solve-only case has no exterior itself
    box = HW.hw_mesh(root, store, key, "box")
    assert box["bbox"][0] == pytest.approx([-160.0, -250.0, -360.0])
    assert box["bbox"][1] == pytest.approx([160.0, 250.0, 0.0])
    assert box["source_files"] == [
        "system/bl_horn/20261118T000000Z-ok-2-bbbb/bl_output/vented_x/exterior.msh"]


def test_case_with_no_meshes_raises(env) -> None:
    root, store = env
    _case(store, "bl_empty", "20261118T000003Z-empty-1-cccc", {"kind": "bl_stage_horn_project"})
    key = "bl_empty/20261118T000003Z-empty-1-cccc"
    with pytest.raises(FileNotFoundError):
        HW.hw_mesh(root, store, key, "box")
    with pytest.raises(FileNotFoundError):
        HW.hw_mesh(root, store, key, "horn")


def test_decimation_caps_triangles_and_is_deterministic(env) -> None:
    root, store = env
    big = _write_grid_mesh(store / "system" / "ref_case" / "horn_full" / "big" / "mesh.msh", 200)
    name = "20261118T000010Z-big-7-dddd"
    key = f"bl_horn/{name}"
    _staged_horn(store, "bl_horn", name, 0.0, big)
    HW._CACHE.clear()
    first = HW.hw_mesh(root, store, key, "horn")
    assert first["decimated"] is True
    assert 0 < first["triangle_count"] <= HW._TRI_CAP
    assert len(first["tris"]) == 3 * first["triangle_count"]
    assert max(first["tris"]) < len(first["verts"]) // 3

    HW._CACHE.clear()                     # a real recompute, not the cache
    second = HW.hw_mesh(root, store, key, "horn")
    assert second["decimated"] is True
    assert second["triangle_count"] == first["triangle_count"]
    assert second["verts"] == first["verts"]
    assert second["tris"] == first["tris"]

    small = HW.hw_mesh(root, store, KEY, "horn")
    assert small["decimated"] is False and small["triangle_count"] == 12


def test_mesh_without_triangles_is_refused_by_name(env) -> None:
    import meshio

    root, store = env
    path = store / "system" / "ref_case" / "horn_full" / "quads" / "mesh.msh"
    path.parent.mkdir(parents=True)
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    meshio.write(path, meshio.Mesh(points=pts, cells=[("quad", np.array([[0, 1, 2, 3]]))]),
                 file_format="gmsh22", binary=False)
    name = "20261118T000011Z-quad-8-eeee"
    _staged_horn(store, "bl_horn", name, 0.0, path)
    with pytest.raises(ValueError) as excinfo:
        HW.hw_mesh(root, store, f"bl_horn/{name}", "horn")
    message = str(excinfo.value)
    assert "mesh.msh" in message and "quad" in message and "triangle" in message


def test_no_solver_or_boundary_lab_is_touched(env, monkeypatch: pytest.MonkeyPatch) -> None:
    from hornlab_search.system.boundarylab import run as bl_run
    from hornlab_search.system.boundarylab import stage as bl_stage

    def boom(*a, **k):
        raise AssertionError("GUI read path must not call Boundary Lab")
    for module, names in ((bl_run, ("validate_project", "solve_project")),
                          (bl_stage, ("stage_reference_project", "stage_horn_project"))):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, boom)
    root, store = env
    HW.hw_mesh(root, store, KEY, "box")
    HW.hw_mesh(root, store, KEY, "horn")
    assert "blab" not in sys.modules


def test_mesh_payload_is_json_serialisable(env) -> None:
    root, store = env
    for part in ("box", "horn"):
        out = HW.hw_mesh(root, store, KEY, part)
        json.dumps(clean(out), allow_nan=False)
        assert out["verts"] and all(isinstance(v, float) for v in out["verts"])
        assert out["tris"] and all(isinstance(i, int) for i in out["tris"])
        assert isinstance(out["triangle_count"], int) and isinstance(out["decimated"], bool)
        assert out["units"] == "mm"
