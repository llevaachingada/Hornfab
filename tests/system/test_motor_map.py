"""Offline tests for the committed-T/S -> Boundary Lab motor mapping and staging spec.

The REAL staging path (BL's own generator, configuration patch, compiler and
``blab project validate``) stays behind the existing ``HORNLAB_BL_REAL_TESTS=1`` env gate,
copied from ``tests/system/test_bl_stage.py``. Nothing here imports ``blab``.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import provenance  # noqa: E402
from hornlab_search.system.boundarylab import motor_map as M  # noqa: E402
from hornlab_search.system.boundarylab.probe import BLRoot, probe_boundarylab  # noqa: E402
from hornlab_search.system.contracts import BoxPoint  # noqa: E402

REAL_BL_ROOT = "C:/Users/hunte/Github/boundary-lab"

#: Provider manifest defaults (copied fixture; no BL import).
_DEFAULTS = {
    "width_m": 0.32, "height_m": 0.5, "depth_m": 0.36, "wall_m": 0.018,
    "driver_diameter_m": 0.2, "cone_depth_m": 0.04, "surround_width_m": 0.012,
    "cap_diameter_m": 0.05, "driver_y_m": 0.1, "port_length_m": 0.22,
    "port_area_m2": 0.002827433388, "port_nfr": 0.12, "port_roundover_m": 0.008,
    "port_wall_m": 0.003, "port_y_m": -0.13, "mesh_size_m": 0.04, "detail_size_m": 0.012,
}


def fake_bl_root(tmp_path: Path) -> BLRoot:
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
        path=str(root), kind="checkout", version="0.5.0", git_head=None,
        python_executable=str(root / ".venv" / "Scripts" / "python.exe"),
        cli_entry=str(root / ".venv" / "Scripts" / "blab.exe"),
        provider_dir=str(provider_dir), hashes=(), missing=(),
        detail={"provider_manifest": manifest},
    )


def _copy_yaml_without(path: Path, tmp_path: Path, key: str) -> Path:
    """Drop one top-level YAML line (test-only; the committed file is never edited)."""
    kept = [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith(f"{key}:")]
    target = tmp_path / path.name
    target.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return target


def _local_validate_component_parameters_patch(patch: Any) -> None:
    """Locally re-typed subset of BL ``validate_patch`` (no blab import).

    Mirrors ``configuration.py``: top-level keys must be PATCH_SECTIONS members (only
    ``component_parameters`` here); values must be objects; nulls are not removals; the
    whole patch must be finite JSON.
    """
    allowed_sections = {
        "regions", "surface_assignments", "interfaces", "component_assignments",
        "excitation_ports", "component_parameters", "channel_config", "component_channels",
        "symmetry_config", "stitching_config",
    }
    if not isinstance(patch, dict):
        raise ValueError("configuration_patch must be an object")
    unknown = set(patch) - allowed_sections
    if unknown:
        raise ValueError(f"unknown patch sections: {sorted(unknown)}")
    json.dumps(patch, allow_nan=False)
    section = patch.get("component_parameters")
    if section is None:
        return
    if not isinstance(section, dict):
        raise ValueError("component_parameters must be an object")
    for component_id, parameters in section.items():
        if not isinstance(component_id, str) or not component_id.strip():
            raise ValueError("component_parameters keys must be nonempty strings")
        if not isinstance(parameters, dict):
            raise ValueError("component parameters must be an object")
        for key, value in parameters.items():
            if value is None:
                raise ValueError(f"Null is not a removal operation ({key})")


# --------------------------------------------------------------------------- motor mapping

def test_mapping_units_and_real_dry_mass() -> None:
    mapping = M.map_motor()
    assert mapping.ok is True and mapping.refusals == {}
    p = mapping.parameters
    assert p["re_ohm"] == 5.4
    assert p["le_h"] == pytest.approx(0.00042)          # 0.42 mH
    assert p["bl_n_per_a"] == pytest.approx(14.1)       # 14.1 T*m
    assert p["mmd_kg"] == pytest.approx(0.0295)         # 29.5 g DRY, not 0.035
    assert p["mmd_kg"] != 0.035
    assert p["cms_m_per_n"] == pytest.approx(0.00023)   # 0.23 mm/N
    assert p["rms_n_s_per_m"] == pytest.approx(1.4)     # 1.4 kg/s
    assert p["motion_profile"] == "rigid_translation"   # BL defaults only
    assert p["motion_axis"] == [0, 0, 1]
    assert mapping.dry_mass_kg == pytest.approx(0.0295)
    assert set(p) == set(M.BL_MOTOR_PARAMETER_KEYS)


def test_field_map_records_every_factor() -> None:
    mapping = M.map_motor()
    factors = {key: value.get("factor") for key, value in mapping.field_map.items()}
    assert factors["re_ohm"] == 1.0
    assert factors["le_h"] == 1e-3
    assert factors["bl_n_per_a"] == 1.0
    assert factors["mmd_kg"] == 1e-3
    assert factors["cms_m_per_n"] == 1e-3
    assert factors["rms_n_s_per_m"] == 1.0
    assert factors["motion_profile"] is None and factors["motion_axis"] is None
    assert mapping.field_map["mmd_kg"]["yaml_field"] == "mmd_g"
    assert "DRY" in mapping.field_map["mmd_kg"]["unit"]


def test_model_fs_and_vas_cross_checks() -> None:
    checks = M.map_motor().cross_checks
    assert checks["fs_published_hz"] == pytest.approx(50.0)
    assert checks["fs_model"] == pytest.approx(50.2069406253, rel=1e-9)
    assert checks["fs_error_percent"] < 1.0
    assert checks["fs_within_8_percent"] is True
    assert checks["mms_model_kg"] == pytest.approx(0.0436902883, rel=1e-9)
    assert checks["mms_error_percent"] < 2.0
    assert checks["vas_model_l"] == pytest.approx(92.5543810986, rel=1e-9)
    assert checks["vas_error_percent"] < 1.0
    assert checks["le_bl"]["checked"] is False


def test_missing_motor_field_is_refused_with_token(tmp_path: Path) -> None:
    broken = _copy_yaml_without(M.TS_PATH, tmp_path, "bl_tm")
    mapping = M.map_motor(broken)
    assert mapping.ok is False
    assert mapping.refusals == {"bl_n_per_a": M.MOTOR_FIELD_UNAVAILABLE}
    assert "bl_n_per_a" not in mapping.parameters
    with pytest.raises(ValueError, match="motor fields are unavailable"):
        mapping.patch("bl_motor12pr")


# --------------------------------------------------------------------------- geometry

def test_geometry_override_set_tokens_and_sd_diameter() -> None:
    geo = M.geometry_overrides()
    assert geo.complete is False
    assert geo.refusals == {
        "cone_depth_m": M.GEOMETRY_FIELD_UNAVAILABLE,
        "surround_width_m": M.GEOMETRY_FIELD_UNAVAILABLE,
        "cap_diameter_m": M.GEOMETRY_FIELD_UNAVAILABLE,
        "driver_y_m": M.GEOMETRY_FIELD_UNAVAILABLE,
    }
    assert geo.values["driver_diameter_m"] == pytest.approx(0.260506559868, rel=1e-12)
    assert "2*sqrt(Sd" in geo.derived["driver_diameter_m"]
    assert set(geo.values) <= set(M.GEOMETRY_REQUIRED_FIELDS)


def test_geometry_converts_present_manufacturer_fields(tmp_path: Path) -> None:
    data = {
        "driver_id": "fixture", "measured_by": "manufacturer",
        "sourced_from": ["https://example.invalid"],
        "cutout_mm": 283, "frame_od_mm": 315.2, "depth_mm": 140.6,
        "cone_depth_mm": 38.5, "surround_width_mm": 11.0,
        "dust_cap_diameter_mm": 60.0,
    }
    path = tmp_path / "geometry.yaml"
    path.write_text(json.dumps(data), encoding="utf-8")
    geo = M.geometry_overrides(geometry_path=path)
    assert geo.values["cone_depth_m"] == pytest.approx(0.0385)
    assert geo.values["surround_width_m"] == pytest.approx(0.011)
    assert geo.values["cap_diameter_m"] == pytest.approx(0.060)
    assert geo.refusals == {"driver_y_m": M.GEOMETRY_FIELD_UNAVAILABLE}


def test_panel_placement_default_shape_fits_but_real_diameter_does_not() -> None:
    point = M.load_seed_reference_box().point
    demo = M.panel_placement(point, _DEFAULTS["driver_diameter_m"])
    assert demo["driver_fits_wall"] and demo["port_fits_wall"] and demo["separation_ok"]

    real_diameter = M.geometry_overrides().values["driver_diameter_m"]
    real = M.panel_placement(point, real_diameter)
    assert real["driver_fits_wall"] is True
    assert real["separation_ok"] is False
    assert real["available_separation_m"] < real["required_separation_m"]


# --------------------------------------------------------------------------- patch structure

def test_patch_has_only_component_parameters_and_bl_schema() -> None:
    patch = M.map_motor().patch("bl_motor12pr")
    _local_validate_component_parameters_patch(patch)
    assert set(patch) == {"component_parameters"}
    assert set(patch["component_parameters"]) == {"bl_motor12pr/driver"}
    parameters = patch["component_parameters"]["bl_motor12pr/driver"]
    assert set(parameters) == set(M.BL_MOTOR_PARAMETER_KEYS)
    assert parameters["mmd_kg"] == pytest.approx(0.0295)


def test_local_patch_schema_rejects_unknown_section_and_null() -> None:
    with pytest.raises(ValueError, match="unknown patch sections"):
        _local_validate_component_parameters_patch({"bogus": {}})
    with pytest.raises(ValueError, match="Null is not a removal"):
        _local_validate_component_parameters_patch(
            {"component_parameters": {"bl_motor12pr/driver": {"mmd_kg": None}}})


# --------------------------------------------------------------------------- seed box / source

def test_seed_box_is_the_committed_row_and_source_is_derived() -> None:
    seed = M.load_seed_reference_box()
    assert isinstance(seed.point, BoxPoint)
    assert seed.candidate_id == M.SEED_CANDIDATE_ID
    assert seed.driver_id == "faitalpro_12pr300"
    assert seed.point.external_width_mm == pytest.approx(371.2)
    assert seed.point.external_height_mm == pytest.approx(371.2)
    assert seed.point.external_depth_mm == pytest.approx(1078.791264974584)
    assert seed.point.net_volume_l == pytest.approx(115.0)
    assert seed.point.wall_mm == pytest.approx(18.0)
    assert seed.point.port_throat_area_cm2 == pytest.approx(45.0)
    assert seed.point.derived_tuning_hz == pytest.approx(30.0)
    assert seed.point.derived_effective_port_length_m == pytest.approx(0.129568868851, rel=1e-9)

    placement = M.panel_placement(seed.point, _DEFAULTS["driver_diameter_m"])
    source, record = M.vented_source(
        seed.point, defaults=_DEFAULTS,
        driver_diameter_m=_DEFAULTS["driver_diameter_m"],
        driver_y_m=placement["driver_y_m"], port_y_m=placement["port_y_m"])
    assert set(source) == set(_DEFAULTS)
    assert source["width_m"] == pytest.approx(0.3712)
    assert source["height_m"] == pytest.approx(0.3712)
    assert source["depth_m"] == pytest.approx(1.078791264974584)
    assert source["port_area_m2"] == pytest.approx(0.0045)
    assert source["port_nfr"] == 0.0
    assert source["port_length_m"] == pytest.approx(0.081228989539979, rel=1e-9)
    assert record["port_neck_m"] > 0.0


def test_build_spec_dry_run_records_tokens_and_real_patch(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    spec = M.build_motor_stage_spec(root, case_dir=tmp_path / "case")
    assert spec["component_id"] == "bl_motor12pr/driver"
    assert spec["component_parameters"]["mmd_kg"] == pytest.approx(0.0295)
    assert spec["component_parameters"]["re_ohm"] == pytest.approx(5.4)
    assert spec["source"]["driver_diameter_m"] == pytest.approx(0.2)  # staged shape is demo
    assert spec["geometry_overrides_used"]["staged_transducer_shape"] \
        == M.MOTOR_GEOMETRY_INCOMPLETE
    assert spec["geometry_overrides_used"]["cone_depth_m"] == M.GEOMETRY_FIELD_UNAVAILABLE
    assert spec["geometry_attempt"]["source"]["driver_diameter_m"] \
        == pytest.approx(0.260506559868, rel=1e-12)
    assert spec["mapping"]["dry_mass_kg"] == pytest.approx(0.0295)


def test_stage_motor_project_dry_run_does_not_execute(tmp_path: Path) -> None:
    root = fake_bl_root(tmp_path)
    result = M.stage_motor_project(root, store_root=tmp_path, run_now=False)
    assert result.ok is False and result.returncode == -1
    assert result.detail["spec_dry_run"]["component_id"] == "bl_motor12pr/driver"
    assert not list(tmp_path.rglob("adapter_spec.json"))


# --------------------------------------------------------------------------- real BL (opt-in)

def _real_root() -> BLRoot | None:
    if os.environ.get("HORNLAB_BL_REAL_TESTS", "").strip() != "1":
        pytest.skip("real Boundary Lab staging gated off (set HORNLAB_BL_REAL_TESTS=1)")
    probe = probe_boundarylab(extra_roots=[REAL_BL_ROOT], use_default_roots=False)
    if probe.verified_root is None:
        pytest.skip("verified Boundary Lab not present")
    return probe.verified_root


def test_real_bl_motor_stage_serializes_real_ts(tmp_path: Path) -> None:
    root = _real_root()
    assert root is not None
    result = M.stage_motor_project(root, store_root=tmp_path, timeout_s=900.0)
    assert result.ok is True, "\n".join(result.captured_log_tail[-20:])
    assert result.valid is True
    assert result.project_path is not None and result.project_path.is_file()
    assert result.manifest_path is not None and result.manifest_path.is_file()

    payload = provenance.load_manifest(result.manifest_path)["payload"]
    assert payload["kind"] == "bl_motor_stage_project"
    assert payload["motor_mapping"]["parameters"]["mmd_kg"] == pytest.approx(0.0295)
    assert payload["motor_mapping"]["parameters"]["re_ohm"] == pytest.approx(5.4)
    assert len(payload["configuration_patch_sha256"]) == 64
    assert payload["configuration_patch"]["component_parameters"]["bl_motor12pr/driver"][
        "mmd_kg"] == pytest.approx(0.0295)
    assert payload["yaml_sha256"]["driver_ts"] == payload["motor_mapping"]["ts_sha256"]
    parameters = payload["result"]["component_parameters_serialized"]
    assert parameters["mmd_kg"] == pytest.approx(0.0295)
    assert parameters["mmd_kg"] != 0.035
    assert parameters["re_ohm"] == pytest.approx(5.4)
    assert parameters["bl_n_per_a"] == pytest.approx(14.1)
    assert parameters["cms_m_per_n"] == pytest.approx(0.00023)
    assert parameters["rms_n_s_per_m"] == pytest.approx(1.4)
    assert parameters["le_h"] == pytest.approx(0.00042)
    assert parameters["motion_profile"] == "rigid_translation"
    assert payload["result"]["component_parameters_reopened"]["mmd_kg"] == pytest.approx(0.0295)
    assert payload["result"]["interior_tetrahedra"] and payload["result"]["air_volume_m3"]
    assert payload["validate"]["valid"] is True
    geometry_check = payload["result"]["geometry_check"]
    assert geometry_check["ok"] is False
    assert "Driver and port must not overlap" in geometry_check["error"]
