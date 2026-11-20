"""Pass A lane A4: B22/B23 stage fixes (audit overrides + declared BEM surface roles).

Offline: BL's subprocess and ``project validate`` are mocked exactly as in ``test_clearance``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # tests/ for test_bl_stage

from hornlab_search.system.boundarylab import run as bl_run  # noqa: E402
from hornlab_search.system.boundarylab import stage as S  # noqa: E402

from test_bl_stage import fake_bl_root  # noqa: E402


def _write_cube(path: Path, lo, hi) -> Path:
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


def _mock_bl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, surface: Path,
             purpose: str = "bem_surface") -> None:
    project = tmp_path / "case" / "case.blab.json"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text("{}", encoding="utf-8")
    final = {"ok": True, "project_path": str(project), "output_dir": str(tmp_path),
             "meshes": [{"id": "horn_surface", "purpose": purpose, "path": str(surface)}],
             "mesh_info": {}}
    monkeypatch.setattr(S, "_execute", lambda argv, timeout, cancel: (0, [json.dumps(final)]))
    monkeypatch.setattr(S.bl_run, "validate_project", lambda root, path: bl_run.ValidationResult(
        returncode=0, parsed={"valid": True}, stdout_tail=(), stderr_tail=(), argv=()))


@pytest.fixture()
def box(tmp_path: Path) -> Path:
    return _write_cube(tmp_path / "exterior.msh", (-0.16, -0.25, -0.36), (0.16, 0.25, 0.0))


@pytest.fixture()
def horn(tmp_path: Path) -> Path:
    return _write_cube(tmp_path / "horn.msh", (-0.1, -0.1, 0.0), (0.1, 0.1, 0.2))


def test_stage_detail_overrides_are_read_from_spec_source(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, box: Path) -> None:
    # B22: detail.overrides used to be spec.get("overrides", {}) -> always {}. The resolved
    # source (provider defaults + caller overrides) is the audit value the handbook names.
    _mock_bl(monkeypatch, tmp_path, box)
    result = S.stage_reference_project(
        fake_bl_root(tmp_path), {"height_m": 0.44}, case_dir=tmp_path / "case")
    assert result.ok is True
    assert result.detail["overrides"]["height_m"] == pytest.approx(0.44)
    assert "width_m" in result.detail["overrides"]          # provider default is included


def test_clearance_accepts_a_declared_bem_surface_role(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, horn: Path, box: Path) -> None:
    # B23: membership, not equality. Extend the declared role set and stage a project whose
    # BL mesh purpose is the new label; the clearance gate must still prove the gap.
    assert isinstance(S.BEM_SURFACE_ROLES, frozenset)
    assert "bem_surface" in S.BEM_SURFACE_ROLES
    monkeypatch.setattr(S, "BEM_SURFACE_ROLES",
                        frozenset({"bem_surface", "acoustic_surface"}))
    _mock_bl(monkeypatch, tmp_path, box, purpose="acoustic_surface")
    result = S.stage_horn_project(
        fake_bl_root(tmp_path), horn, source_group="g", translation_mm=(0.0, 0.0, 17.0),
        case_dir=tmp_path / "case")
    assert result.detail["clearance_status"] == "PASS"
    assert result.ok is True
