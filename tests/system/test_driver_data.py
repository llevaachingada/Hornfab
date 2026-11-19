"""Tests for the system driver schema (SYS-11) and the fabrication geometry rules.

Covers: the reused frozen cone-YAML schema, strict system-geometry schema v1, the
``geometry_completeness`` classifier (T/S screening vs installed fidelity) and the pure
PASS/FAIL/skip fabrication rules. No mesher, solver or GPU is involved.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]

from hornlab_search.system import drivers as D  # noqa: E402
from hornlab_search.system.contracts import (  # noqa: E402
    BoxPoint,
    DataQualityError,
    DriverGeometry,
    SchemaError,
)
from hornlab_search.system.geometry import rules  # noqa: E402


# --------------------------------------------------------------------------- geometry fixture

def _geometry_dict() -> dict:
    values = {
        "cutout_mm": 283.0,
        "frame_od_mm": 315.2,
        "depth_mm": 140.6,
        "cone_depth_mm": 45.0,
        "surround_width_mm": 22.0,
        "dust_cap_diameter_mm": 70.0,
        "mounting_depth_behind_baffle_mm": 140.6,
    }
    return {
        "driver_id": "faitalpro_12pr300_8",
        "sourced_from": ["https://faitalpro.com/en/products/LF_Loudspeakers/product_details/"
                         "index.php?id=101050110"],
        "measured_by": "manufacturer",
        **values,
    }


def _valid_point() -> BoxPoint:
    """A generous box that the fabrication rules accept (big internal depth)."""
    return BoxPoint(
        kind="vented",
        external_width_mm=500.0,
        external_height_mm=700.0,
        external_depth_mm=800.0,
        net_volume_l=60.0,
        wall_mm=18.0,
        port_type="round_flared",
        port_throat_area_cm2=100.0,
        port_nfr=0.0,
        requested_tuning_hz=35.0,
        derived_effective_port_length_m=0.150,
        derived_tuning_hz=35.0,
        fits={},
    )


def _valid_geometry() -> DriverGeometry:
    return D.parse_driver_geometry_dict(_geometry_dict()).geometry


# --------------------------------------------------------------------------- cone reuse

def test_load_woofer_reuses_the_frozen_cone_schema() -> None:
    w = D.load_woofer("faitalpro_15xl1400")
    assert w.driver_id == "faitalpro_15xl1400"
    assert w.cone.kind == "cone"
    assert w.cone.source.startswith("http")
    assert w.geometry_mm is None
    assert w.data_quality["geometry_present"] is False
    assert w.data_quality["supports_lf_ts_screening"] is True
    assert w.data_quality["supports_installed_exterior_bem"] is False


# --------------------------------------------------------------------------- geometry parse

def test_geometry_document_roundtrips_all_fields(tmp_path: Path) -> None:
    path = tmp_path / "faitalpro_12pr300_8.yaml"
    path.write_text(yaml.safe_dump(_geometry_dict()), encoding="utf-8")
    doc = D.load_driver_geometry(path)
    assert doc.driver_id == "faitalpro_12pr300_8"
    assert doc.measured_by == "manufacturer"
    assert doc.sourced_from[0].startswith("https://")
    for name in D.GEOMETRY_FIELDS:
        assert getattr(doc.geometry, name) == pytest.approx(_geometry_dict()[name])
    assert doc.present_fields == D.GEOMETRY_FIELDS


def test_unknown_geometry_key_is_a_hard_error() -> None:
    bad = _geometry_dict()
    bad["baffle_hole_mm"] = 283.0
    with pytest.raises(SchemaError):
        D.parse_driver_geometry_dict(bad)


def test_declared_null_geometry_value_is_a_hard_error() -> None:
    bad = _geometry_dict()
    bad["dust_cap_diameter_mm"] = None
    with pytest.raises(SchemaError):
        D.parse_driver_geometry_dict(bad)


def test_nonpositive_and_nonfinite_geometry_values_are_rejected() -> None:
    for value in (0.0, -1.0, float("nan"), float("inf")):
        bad = _geometry_dict()
        bad["depth_mm"] = value
        with pytest.raises(SchemaError):
            D.parse_driver_geometry_dict(bad)


def test_metadata_values_are_validated() -> None:
    bad = _geometry_dict()
    bad["measured_by"] = "datasheet"
    with pytest.raises(SchemaError):
        D.parse_driver_geometry_dict(bad)

    bad = _geometry_dict()
    bad["sourced_from"] = ["not-a-url"]
    with pytest.raises(SchemaError):
        D.parse_driver_geometry_dict(bad)

    bad = _geometry_dict()
    del bad["driver_id"]
    with pytest.raises(SchemaError):
        D.parse_driver_geometry_dict(bad)


# --------------------------------------------------------------------------- SYS-11 classifier

def test_ts_only_driver_permits_lf_screening_but_not_installed_fidelity() -> None:
    completeness = D.geometry_completeness([])
    assert completeness["SCREEN_MAGNITUDE"] is True
    assert completeness["SCREEN_COMPLEX_APPROX"] is True
    assert completeness["INSTALLED_EXTERIOR_BEM"] is False
    assert completeness["COUPLED_VENTED_FEM_BEM_LEM"] is False
    assert completeness["MEASURED_VALIDATED"] is False
    assert D.missing_installed_fields({}) == D.INSTALLED_GEOMETRY_FIELDS


def test_full_geometry_unlocks_installed_tiers_but_never_measured_validation() -> None:
    full = D.geometry_completeness(D.GEOMETRY_FIELDS)
    assert full["INSTALLED_EXTERIOR_BEM"] is True
    assert full["COUPLED_VENTED_FEM_BEM_LEM"] is True
    assert full["MEASURED_VALIDATED"] is False
    assert D.missing_installed_fields(D.GEOMETRY_FIELDS) == ()


def test_partial_geometry_flags_the_missing_field() -> None:
    partial = D.GEOMETRY_FIELDS[:-1]
    missing = D.missing_installed_fields(partial)
    assert missing == (D.GEOMETRY_FIELDS[-1],)
    assert D.geometry_completeness(partial)["INSTALLED_EXTERIOR_BEM"] is False


def test_null_geometry_via_load_woofer_reports_false_flags() -> None:
    w = D.load_woofer("faitalpro_15xl1400")
    assert w.geometry_mm is None
    assert w.data_quality["has_full_geometry"] is False
    assert w.data_quality["supports_coupled_fidelity"] is False
    assert w.data_quality["supports_lf_ts_screening"] is True


def test_load_woofer_with_full_geometry_reports_true_flags(tmp_path: Path) -> None:
    path = tmp_path / "geometry.yaml"
    path.write_text(yaml.safe_dump(_geometry_dict()), encoding="utf-8")
    w = D.load_woofer("faitalpro_15xl1400", geometry=path)
    assert w.geometry_mm is not None
    assert w.data_quality["has_full_geometry"] is True
    assert w.data_quality["supports_installed_exterior_bem"] is True
    assert w.provenance["measured_by"] == "manufacturer"


def test_require_fidelity_gate_refuses_installed_claims_without_geometry(tmp_path: Path) -> None:
    ts_only = D.load_woofer("faitalpro_15xl1400")
    D.require_fidelity(ts_only, "SCREEN_MAGNITUDE")  # LF screening is always allowed
    with pytest.raises(DataQualityError):
        D.require_fidelity(ts_only, "INSTALLED_EXTERIOR_BEM")
    with pytest.raises(DataQualityError):
        D.require_fidelity(ts_only, "COUPLED_VENTED_FEM_BEM_LEM")
    with pytest.raises(DataQualityError):
        D.require_fidelity(ts_only, "MEASURED_VALIDATED")

    path = tmp_path / "geometry.yaml"
    path.write_text(yaml.safe_dump(_geometry_dict()), encoding="utf-8")
    full = D.load_woofer("faitalpro_15xl1400", geometry=path)
    D.require_fidelity(full, "INSTALLED_EXTERIOR_BEM")
    D.require_fidelity(full, "COUPLED_VENTED_FEM_BEM_LEM")
    with pytest.raises(SchemaError):
        D.require_fidelity(full, "NOT_A_FIDELITY")


# --------------------------------------------------------------------------- fabrication rules

def test_valid_box_passes_all_evaluable_rules() -> None:
    point = _valid_point()
    geometry = _valid_geometry()
    assert rules.check_port_fits(point, geometry).startswith("PASS")
    assert rules.check_driver_and_brace_clearance(point, geometry).startswith("PASS")
    assert rules.check_wall_thickness(point, geometry).startswith("PASS")
    assert rules.check_woofer_horn_clearance(point, geometry).startswith("skip:")


def test_port_neck_too_long_fails() -> None:
    point = dataclasses.replace(_valid_point(), derived_effective_port_length_m=0.900)
    result = rules.check_port_fits(point, _valid_geometry())
    assert result.startswith("FAIL"), result


def test_shallow_box_fails_driver_and_brace_clearance() -> None:
    point = dataclasses.replace(_valid_point(), external_depth_mm=200.0)
    result = rules.check_driver_and_brace_clearance(point, _valid_geometry())
    assert result.startswith("FAIL"), result


def test_thin_wall_fails_and_threshold_is_configurable() -> None:
    thin = dataclasses.replace(_valid_point(), wall_mm=8.0)
    assert rules.check_wall_thickness(thin, None).startswith("FAIL")
    assert rules.check_wall_thickness(thin, None, min_wall_mm=8.0).startswith("PASS")
    assert rules.check_wall_thickness(_valid_point(), None).startswith("PASS")


def test_unknown_horn_flange_is_an_explicit_skip() -> None:
    assert rules.check_woofer_horn_clearance(_valid_point(), _valid_geometry()) == (
        "skip: unknown horn flange")


def test_known_horn_flange_is_a_footprint_screen() -> None:
    point = _valid_point()
    geometry = _valid_geometry()
    assert rules.check_woofer_horn_clearance(
        point, geometry, horn_flange_extent_mm=50.0).startswith("PASS")
    assert rules.check_woofer_horn_clearance(
        point, geometry, horn_flange_extent_mm=400.0).startswith("FAIL")


def test_unknown_driver_geometry_skips_rather_than_passes() -> None:
    assert rules.check_driver_and_brace_clearance(_valid_point(), None).startswith("skip:")


def test_fabrication_report_has_all_rules() -> None:
    report = rules.fabrication_report(_valid_point(), _valid_geometry())
    assert set(report) == {
        "port_fits", "driver_and_brace_clearance", "wall_thickness", "woofer_horn_clearance"}
    assert all(isinstance(v, str) for v in report.values())
