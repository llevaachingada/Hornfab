"""Stage-5 seed-screen tests: geometry legality, unit guards, catalogue honesty, replay identity.

Synthetic-only: no solver, no GPU, no mesher, no real run tree.  The real driver YAMLs are read
(read-only) for the catalogue/replay tests.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.meh.drivers import load_cone
from hornlab_search.system import compatibility as K
from hornlab_search.system import contracts as C
from hornlab_search.system import piston
from hornlab_search.system import woofer_seed as W

REPO = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- fixtures


def _envelope() -> W.HornEnvelope:
    # The real Stage-4 full-domain bbox (metres) is used as the synthetic envelope scale.
    return W.envelope_from_bbox_m(
        (-0.1166727878710462, -0.1166727878710462, -0.003,
         0.1166727878710462, 0.1166727878710462, 0.1398738872624888),
        source="test_full_domain", design_hash="f04827bc5973")


def _box_point(**overrides) -> C.BoxPoint:
    values = {
        "kind": "vented",
        "external_width_mm": 500.0,
        "external_height_mm": 700.0,
        "external_depth_mm": 800.0,
        "net_volume_l": 60.0,
        "wall_mm": 18.0,
        "port_type": "round_flared",
        "port_throat_area_cm2": 100.0,
        "port_nfr": 0.0,
        "requested_tuning_hz": 40.0,
        "derived_effective_port_length_m": 0.15,
        "derived_tuning_hz": 40.0,
        "fits": {"port_velocity_fits": True},
    }
    values.update(overrides)
    return C.BoxPoint(**values)


def _asset(response_path: Path, freqs: tuple[float, ...]) -> C.HornAsset:
    return C.HornAsset(
        asset_id="synthetic0000000000",
        design_hash="0123456789ab",
        response_path=str(response_path),
        mesh_path=None,
        geometry=C.GeometryMetadata(family="TEST", brief_id="synthetic"),
        available_fields=frozenset({
            "freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db", "p_h", "p_v"}),
        quality="MAGNITUDE_ONLY",
        freqs_hz=freqs,
        source_basis=None,
    )


def _synthetic_asset(tmp_path: Path) -> C.HornAsset:
    freqs = np.array([500.0, 600.0, 700.0, 800.0, 900.0, 1000.0])
    angles = np.array([-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0])
    rel = piston.relative_level_db(freqs[:, None], 0.11, angles[None, :])
    spl = 100.0 + rel
    pressure = (10.0 ** (spl / 20.0)).astype(np.complex128)
    path = tmp_path / "response.npz"
    np.savez(
        path, freqs_hz=freqs, h_angles_deg=angles, v_angles_deg=angles,
        spl_h_db=spl, spl_v_db=spl, p_h=pressure, p_v=pressure)
    return _asset(path, tuple(float(f) for f in freqs))


def _driver(stem: str = "faitalpro_10pr300") -> W.DriverEntry:
    catalog = W.load_driver_catalog([stem])
    assert catalog.entries, catalog.rejected
    return catalog.entries[0]


# --------------------------------------------------------------------------- placement / units


def test_mount_transform_sign_convention_x_and_z() -> None:
    matrix = W.mount_transform(dx_mm=10.0, dy_mm=20.0, dz_mm=30.0)
    assert matrix[0] == (1.0, 0.0, 0.0, pytest.approx(0.010))
    assert matrix[1] == (0.0, 1.0, 0.0, pytest.approx(0.020))
    assert matrix[2] == (0.0, 0.0, 1.0, pytest.approx(0.030))
    assert matrix[3] == (0.0, 0.0, 0.0, 1.0)
    # +z must move toward the listener per the feature's cabinet-front convention.
    toward = W.mount_transform(dz_mm=40.0)
    away = W.mount_transform(dz_mm=-40.0)
    assert toward[2][3] > 0.0 > away[2][3]
    assert toward[2][3] == pytest.approx(0.040)


def test_300mm_spacing_is_refused_by_derived_legality() -> None:
    envelope = _envelope()
    box = _box_point()
    dy_min = W.derive_min_center_spacing_mm(envelope, box)
    assert dy_min > 300.0, dy_min
    check = W.placement_legality(envelope, box, dy_mm=300.0, dz_mm=0.0)
    assert check.accepted is False
    assert check.status == "FAIL"
    assert any("illegal spacing" in reason for reason in check.reasons)

    legal = W.placement_legality(envelope, box, dy_mm=dy_min, dz_mm=0.0)
    assert legal.accepted is True, legal.reasons
    assert legal.horn_bbox_mm[1] >= box.external_height_mm / 2.0


def test_1000x_unit_scale_errors_are_caught() -> None:
    # Millimetres passed where metres are expected.
    with pytest.raises(ValueError, match="unit-scale"):
        W.validate_bbox_m((116.67, 116.67, -3.0, 116.67, 116.67, 139.87))
    with pytest.raises(ValueError, match="unit-scale"):
        W.mount_transform(dz_mm=400_000.0)


# --------------------------------------------------------------------------- boxes / drivers


def test_unbuildable_port_is_rejected() -> None:
    driver = _driver().driver
    point = _box_point(derived_effective_port_length_m=0.95)
    row = W.evaluate_box(driver, point, f3_target_hz=None)
    assert row["feasible"] is False
    assert any("port" in reason.lower() for reason in row["reasons"]), row["reasons"]


def test_missing_driver_field_is_recorded_not_guessed() -> None:
    cone = load_cone("faitalpro_10pr300", directory=W.DEFAULT_TS_DIR)
    geometry = C.DriverGeometry(cutout_mm=232.0, frame_od_mm=261.0, depth_mm=115.3)
    driver = C.WooferDriver(
        driver_id="faitalpro_10pr300",
        cone=cone,
        geometry_mm=geometry,
        provenance={"source_urls": (cone.source,)},
        data_quality={"supports_lf_ts_screening": True})
    row = W.evaluate_box(driver, _box_point(), f3_target_hz=None)
    detail = row["driver_geometry"]
    assert "mounting_depth_behind_baffle_mm" in detail["missing_fields"]
    assert detail["mounting_depth_behind_baffle_mm"] is None
    assert detail["installed_claims_allowed"] is False
    assert detail["note"].startswith("missing geometry fields are recorded")


# --------------------------------------------------------------------------- end-to-end replay


def test_identical_inputs_produce_byte_identical_outputs(tmp_path: Path) -> None:
    asset = _synthetic_asset(tmp_path)
    catalog = W.load_driver_catalog(
        ["faitalpro_10pr300", "faitalpro_12pr320"])
    cabinet = C.VentedBoxRanges(
        net_volume_l_range=(60.0, 115.0), tuning_hz_range=(40.0, 55.0),
        port_throat_area_cm2_range=(100.0, 170.0), wall_mm=18.0)
    assembly = C.AssemblyRanges(horn_layout="separate_above")
    target = C.SystemTargets(
        listening_angle_h_deg=(-30.0, 30.0), listening_angle_v_deg=(-15.0, 15.0),
        low_freq_f3_hz_max=None)
    kwargs = dict(
        cabinet=cabinet, assembly=assembly, target=target, envelope=_envelope(),
        limit_boxes=2, dz_offsets_mm=(0.0, 10.0), xo_range_hz=(600.0, 900.0),
        shortlist_size=3)

    first = W.run_seed_screen(asset, catalog, **kwargs)
    second = W.run_seed_screen(asset, catalog, **kwargs)

    assert first.study_id == second.study_id
    assert first.to_json() == second.to_json()
    assert first.to_markdown() == second.to_markdown()
    assert first.kept_rows, "the synthetic screen should keep at least one candidate"
    assert len(first.shortlist) <= 3
    payload = first.to_payload()
    assert payload["schema"] == W.SEED_SCHEMA
    assert payload["input_sha256"]["asset_response_npz"]
    assert "creation" not in json_text(first).lower()


def json_text(result: W.SeedResult) -> str:
    import json

    return json.dumps(result.to_payload(), sort_keys=True)
