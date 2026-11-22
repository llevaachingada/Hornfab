"""Stage-real-PysicalSystem adapter tests (no solver; BL optional).

Offline tests cover spec construction, argv-free dry runs, local refusal rules and the
blocker/resolution helpers. The REAL staging path (BL's own generator + ``blab project
validate``) runs only when ``HORNLAB_BL_REAL_TESTS=1`` and a verified local Boundary Lab is
present, mirroring the env-gate convention in ``test_boundarylab_geometry.py``.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import provenance  # noqa: E402
from hornlab_search.system.boundarylab import stage as S  # noqa: E402
from hornlab_search.system.boundarylab.probe import BLCapabilityError, BLRoot, probe_boundarylab  # noqa: E402

REAL_BL_ROOT = "C:/Users/hunte/Github/boundary-lab"

_DEFAULTS = {
    "width_m": 0.32, "height_m": 0.5, "depth_m": 0.36, "wall_m": 0.018,
    "driver_diameter_m": 0.2, "cone_depth_m": 0.04, "surround_width_m": 0.012,
    "cap_diameter_m": 0.05, "driver_y_m": 0.1, "port_length_m": 0.22,
    "port_area_m2": 0.002827433388, "port_nfr": 0.12, "port_roundover_m": 0.008,
    "port_wall_m": 0.003, "port_y_m": -0.13, "mesh_size_m": 0.04, "detail_size_m": 0.012,
}


def fake_bl_root(tmp_path: Path, *, verified: bool = True) -> BLRoot:
    """A verified-shaped BLRoot carrying the provider manifest fields this adapter reads."""
    root = tmp_path / "boundary-lab"
    provider_dir = root / "geometry_providers" / "vented_enclosure"
    provider_dir.mkdir(parents=True)
    manifest = {
        "manifest_version": 1,
        "id": "blab.vented_enclosure",
        "provider_api": 1,
        "source_schema_version": 1,
        "backend": "enclosure.backend:create_backend",
        "default_source": _DEFAULTS,
        "mesh_scale_factor": 1.0,
    }
    (provider_dir / "provider.json").write_text(json.dumps(manifest), encoding="utf-8")
    return BLRoot(
        path=str(root),
        kind="checkout",
        version="0.5.0",
        git_head=None,
        python_executable=str(root / ".venv" / "Scripts" / "python.exe"),
        cli_entry=str(root / ".venv" / "Scripts" / "blab.exe"),
        provider_dir=str(provider_dir),
        hashes=(),
        missing=() if verified else ("fake root intentionally unverified",),
        detail={"provider_manifest": manifest},
    )


def write_closed_box_double(path: Path) -> Path:
    """Write a 12-triangle closed test double (two groups) — interface wiring only.

    This is NOT a mesher and never ships geometry: it exists so the horn-import wiring
    (rigid wall + one moving source group) can be exercised without Lane A's full-domain
    horn mesh. Units are metres.
    """
    import meshio
    import numpy as np

    h = 0.1
    points = np.array([
        [-h, -h, -h], [h, -h, -h], [h, h, -h], [-h, h, -h],
        [-h, -h, h], [h, -h, h], [h, h, h], [-h, h, h],
    ], dtype=float)
    wall = [(0, 2, 1), (0, 3, 2), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5),
            (0, 1, 5), (0, 5, 4), (3, 6, 2), (3, 7, 6)]
    throat = [(4, 5, 6), (4, 6, 7)]
    triangles = np.array(wall + throat, dtype=np.int64)
    tags = np.array([1] * len(wall) + [2] * len(throat), dtype=np.int32)
    mesh = meshio.Mesh(
        points=points,
        cells=[("triangle", triangles)],
        cell_data={"gmsh:physical": [tags]},
        field_data={"horn_wall": [1, 2], "horn_throat": [2, 2]},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    meshio.write(path, mesh, file_format="gmsh22", binary=False)
    return path


# --------------------------------------------------------------------------- offline specs

def test_build_stage_spec_uses_provider_defaults_and_off_symmetry(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    spec = S.build_stage_spec(root, {"width_m": 0.30}, case_dir=tmp_path / "case")
    assert spec["provider_id"] == "blab.vented_enclosure"
    assert spec["provider_root"].endswith("geometry_providers")
    assert spec["source"]["width_m"] == 0.30
    assert spec["source"]["port_nfr"] == _DEFAULTS["port_nfr"]      # untouched default
    assert spec["configuration"] == {"symmetry_config": {"mode": "off"}}
    assert spec["expectations"]["mmd_kg"] == 0.035
    assert "horn" not in spec


def test_build_stage_spec_records_the_numeric_overrides(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    overrides = {"width_m": 0.30, "height_m": 0.44}
    spec = S.build_stage_spec(root, overrides, case_dir=tmp_path / "case")
    # ``source`` stays the merged view; ``overrides`` is the explicit caller request (B22).
    assert spec["overrides"] == overrides
    assert spec["source"]["width_m"] == 0.30 and spec["source"]["height_m"] == 0.44
    assert spec["source"]["port_nfr"] == _DEFAULTS["port_nfr"]


def test_staged_manifest_detail_records_the_overrides(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """The staged manifest detail must carry the same overrides as the spec (B22).

    The BL-side runner is mocked out: this exercises ``_stage``'s manifest assembly only.
    """
    root = fake_bl_root(tmp_path)
    seen: dict[str, Any] = {}

    def fake_execute(argv, timeout_s, cancel_path):  # noqa: ANN001 - mirrors _execute
        seen["argv"] = list(argv)
        return 1, ["[adapter] mocked runner refusal"]

    monkeypatch.setattr(S, "_execute", fake_execute)
    result = S.stage_reference_project(root, {"height_m": 0.44}, store_root=tmp_path)
    assert result.ok is False and result.manifest_path is not None
    assert seen["argv"] and "runner_stage.py" in seen["argv"][-2]
    payload = provenance.load_manifest(result.manifest_path)["payload"]
    assert payload["spec"]["overrides"] == {"height_m": 0.44}
    assert payload["detail"]["overrides"] == {"height_m": 0.44}
    assert payload["detail"]["overrides"] == payload["spec"]["overrides"]
    assert payload["spec"]["source"]["height_m"] == 0.44


def test_stage_reference_dry_run_returns_spec_without_executing(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    result = S.stage_reference_project(root, {"height_m": 0.44}, store_root=tmp_path, run_now=False)
    assert result.ok is False and result.returncode == -1
    spec = result.detail["spec_dry_run"]
    assert isinstance(spec, dict)
    assert spec["source"]["height_m"] == 0.44
    assert spec["case_name"] == "ref_case"
    assert not list(tmp_path.rglob("adapter_spec.json"))


def test_stage_horn_dry_run_records_explicit_groups_and_drops_air_volume(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    horn = write_closed_box_double(tmp_path / "horn" / "mesh.msh")
    result = S.stage_horn_project(
        root, horn, source_group="horn_throat", translation_mm=(0.0, 0.0, 200.0),
        mesh_role="test_double", store_root=tmp_path, run_now=False,
    )
    spec = result.detail["spec_dry_run"]
    assert isinstance(spec, dict)
    assert spec["horn"]["source_group"] == "horn_throat"
    assert spec["horn"]["mesh_role"] == "test_double"
    assert spec["horn"]["mesh_path"] == str(horn.resolve())
    assert spec["horn"]["scale_factor"] == 1.0
    assert "air_volume_m3_min" not in spec["expectations"]
    assert spec["expectations"]["mmd_kg"] == 0.035


def test_unknown_override_key_is_rejected_locally(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    with pytest.raises(ValueError, match="unknown vented-source key"):
        S.build_stage_spec(root, {"bogus_m": 1.0}, case_dir=tmp_path / "case")


def test_unverified_root_is_rejected(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path, verified=False)
    with pytest.raises(BLCapabilityError):
        S.build_stage_spec(root, {}, case_dir=tmp_path / "case")


def test_missing_horn_mesh_is_rejected_before_spec(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    with pytest.raises(FileNotFoundError):
        S.stage_horn_project(root, tmp_path / "absent.msh", source_group="throat",
                             store_root=tmp_path, run_now=False)


def test_runner_is_shipped_next_to_the_adapter() -> None:
    path = S.runner_path()
    assert path.is_file() and path.name == "runner_stage.py"
    text = path.read_text(encoding="utf-8")
    assert "stage_generation" in text and "write_project_file" in text
    assert "PhysicalSystemCompiler" in text


def test_resolve_full_domain_horn_mesh_reports_absence_and_newest(tmp_path: Path) -> None:
    assert S.resolve_full_domain_horn_mesh(tmp_path) is None
    older = tmp_path / "system" / "ref_case" / "horn_full" / "20260101T000000Z-a" / "mesh.msh"
    newer = tmp_path / "system" / "ref_case" / "horn_full" / "20260102T000000Z-b" / "mesh.msh"
    for path in (older, newer):
        path.parent.mkdir(parents=True)
        path.write_text("mesh\n", encoding="utf-8")
    assert S.resolve_full_domain_horn_mesh(tmp_path) == newer
    assert S.BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT == "BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT"


# --------------------------------------------------------------------------- real BL (opt-in)

def _real_root() -> BLRoot | None:
    if os.environ.get("HORNLAB_BL_REAL_TESTS", "").strip() != "1":
        pytest.skip("real Boundary Lab staging gated off (set HORNLAB_BL_REAL_TESTS=1)")
    probe = probe_boundarylab(extra_roots=[REAL_BL_ROOT], use_default_roots=False)
    if probe.verified_root is None:
        pytest.skip("verified Boundary Lab not present")
    return probe.verified_root


def test_real_bl_stage_reference_project_validates(tmp_path: Path) -> None:
    """The upstream fixture flow, staged through BL and validated by BL's own CLI."""
    root = _real_root()
    assert root is not None
    result = S.stage_reference_project(root, store_root=tmp_path, timeout_s=900.0)
    assert result.ok is True, "\n".join(result.captured_log_tail[-20:])
    assert result.valid is True
    assert result.project_path is not None and result.project_path.is_file()
    assert result.manifest_path is not None and result.manifest_path.is_file()
    payload = provenance.load_manifest(result.manifest_path)["payload"]
    assert payload["kind"] == "bl_stage_reference_project"
    assert payload["validate"]["valid"] is True
    assert payload["result"]["verification"]["failures"] == []
    checks: dict[str, Any] = payload["result"]["verification"]["checks"]
    assert checks["interface_count"]["actual"] == 1
    assert checks["region_count"]["actual"] == 2
    assert checks["reopened_interface_count"]["actual"] == 1
    assert checks["solve_kind"]["actual"] == "coupled_bem_fem"
    assert checks["excitation_port_count"]["actual"] == 1
    assert payload["bl_dependency_hashes"]["src/blab/physical_compiler.py"]


def test_real_bl_stage_horn_project(tmp_path: Path) -> None:
    """Two-body wiring: rigid wall + one moving normal-velocity source.

    Uses Lane A's full-domain closed horn mesh when it is present and falls back to the
    closed test double otherwise; either way the recorded ``mesh_role`` says which one ran.
    ``SD1D1001`` is the reference horn's 25.4 mm throat disc (radius 12.7 mm, z = 0 plane),
    i.e. the horn's own excitation face; ``SD1G0`` is the radiating wall.
    """
    root = _real_root()
    assert root is not None
    repo_store = Path(__file__).resolve().parents[2] / "system_runs"
    full_domain = S.resolve_full_domain_horn_mesh(repo_store)
    if full_domain is not None:
        horn, source_group, mesh_role = full_domain, "SD1D1001", "full_domain"
        expected_groups = ["SD1D1001", "SD1G0"]
    else:
        horn = write_closed_box_double(tmp_path / "horn" / "mesh.msh")
        source_group, mesh_role = "horn_throat", "test_double"
        expected_groups = ["horn_throat", "horn_wall"]
    # The 0.2 m test-double cube is centred on its origin, so it needs 120 mm to clear the
    # enclosure front face (z = 0) by the R16 1 mm minimum; the full-domain horn clears at 20 mm.
    offset_z = 20.0 if mesh_role == "full_domain" else 120.0
    result = S.stage_horn_project(
        root, horn, source_group=source_group, translation_mm=(0.0, 0.0, offset_z),
        mesh_role=mesh_role, store_root=tmp_path, timeout_s=900.0,
    )
    assert result.ok is True, "\n".join(result.captured_log_tail[-20:])
    assert result.valid is True
    assert result.manifest_path is not None
    payload = provenance.load_manifest(result.manifest_path)["payload"]
    horn_decision = payload["result"]["horn"]
    assert horn_decision["mesh_role"] == mesh_role
    assert sorted(horn_decision["surface_groups"]) == sorted(expected_groups)
    assert horn_decision["moving_group"] == source_group
    assert horn_decision["rigid_groups"] == [g for g in expected_groups if g != source_group]
    assert horn_decision["excitation_port"]["kind"] == "normal_velocity"
    assert payload["clearance"]["status"] == "PASS"
    assert payload["clearance"]["aabb_gap_m"] >= 1.0e-3
    checks = payload["result"]["verification"]["checks"]
    assert checks["excitation_port_count"]["actual"] == 2
    assert checks["reopened_solve_kind"]["actual"] == "coupled_bem_fem"


def test_real_bl_stage_horn_unknown_group_is_refused(tmp_path: Path) -> None:
    """A guessed surface group must fail loudly instead of being silently assigned."""
    root = _real_root()
    assert root is not None
    horn = write_closed_box_double(tmp_path / "horn" / "mesh.msh")
    result = S.stage_horn_project(
        root, horn, source_group="not_a_group", mesh_role="test_double",
        store_root=tmp_path, timeout_s=900.0,
    )
    assert result.ok is False and result.valid is False
    assert result.project_path is None
    assert any("not a 2D physical group" in line for line in result.captured_log_tail)
