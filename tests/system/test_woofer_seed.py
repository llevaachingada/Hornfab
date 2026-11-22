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


def _recorded_case_box(**overrides) -> C.BoxPoint:
    """The parent's R4-class top cell (12PR300, 115 L, 371.2 x 371.2 x 1080.7 mm, 170 cm^2).

    Values are the exact source the parent staged into BL (``port_length_m = 0.15488``); the
    contract carries the derived effective length, so the neck is inverted with the fixed
    bassbox ``N_END`` and ``2 * lip`` is added.  The refusal is recorded verbatim in
    ``system_runs/system/bl_r4_tower_box/20261119T001041Z-ref_case-40216-b32bb5a2/manifest.json``.
    """
    r_eq = math.sqrt(170.0 * 1e-4 / math.pi)
    neck_m = 0.15488  # BL source port_length_m in the recorded case
    values = {
        "kind": "vented",
        "external_width_mm": 371.2,
        "external_height_mm": 371.2,
        "external_depth_mm": 1080.690776151898,
        "net_volume_l": 115.0,
        "wall_mm": 18.0,
        "port_type": "round_flared",
        "port_throat_area_cm2": 170.0,
        "port_nfr": 0.0,
        "requested_tuning_hz": 49.72,
        "derived_effective_port_length_m": neck_m + 2.0 * 0.85 * r_eq,
        "derived_tuning_hz": 49.72,
        "fits": {},
    }
    values.update(overrides)
    return C.BoxPoint(**values)


def _bl_validate_reference(box: C.BoxPoint, **overrides) -> str | None:
    """Independent literal transcription of BL ``parameters.py::validate`` lines 100-109.

    Used only to compare verdicts with :func:`W.bl_panel_fit_feasible`; the in-module function
    additionally refuses a panel whose separation budget is impossible at any ``y``.
    """
    o = {
        "driver_moving_diameter_m": 0.200,
        "driver_y_m": 0.100,
        "port_y_m": -0.130,
        "port_wall_m": 0.003,
        "port_roundover_m": 0.008,
        "cone_depth_m": 0.040,
        "clearance_m": 0.003,
    }
    o.update(overrides)
    w = box.external_width_mm * 1e-3
    h = box.external_height_mm * 1e-3
    d = box.external_depth_mm * 1e-3
    t = box.wall_mm * 1e-3
    driver = o["driver_moving_diameter_m"] / 2.0
    throat = math.sqrt(box.port_throat_area_cm2 * 1e-4 / math.pi)
    mouth = throat + o["port_roundover_m"]
    port_outer = mouth + o["port_wall_m"]
    length = W.bass_reference.port_neck_length_mm(box) * 1e-3 + 2.0 * o["port_roundover_m"]
    c = o["clearance_m"]
    if (driver + c >= w / 2 - t
            or abs(o["driver_y_m"]) + driver + c >= h / 2 - t):
        return W.BL_PANEL_FIT_DRIVER_WALL
    if (port_outer + c >= w / 2 - t
            or abs(o["port_y_m"]) + port_outer + c >= h / 2 - t):
        return W.BL_PANEL_FIT_PORT_WALL
    if abs(o["driver_y_m"] - o["port_y_m"]) <= driver + port_outer + c:
        return W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION
    if length <= t + o["port_roundover_m"] + c or length + 2.0 * mouth >= d - t:
        return W.BL_PANEL_FIT_PORT_REAR_WALL
    if o["cone_depth_m"] + c >= d - t:
        return W.BL_PANEL_FIT_CONE_REAR_WALL
    return None


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


# --------------------------------------------------------------------------- BL panel fit


def test_recorded_bl_refusal_case_is_rejected_by_panel_fit() -> None:
    # The parent's top cell (12PR300, 115 L, 371.2 x 371.2 x 1080.7 mm, 170 cm^2) was refused
    # verbatim by BL: "Driver must fit inside the enclosure walls with 3 mm clearance."
    # (manifest .../20261119T001041Z-ref_case-40216-b32bb5a2).  BL checks the individual walls
    # before the pair rule; this screen label identifies the binding root cause: the 371.2 mm
    # front cannot separate a 200 mm demo driver from a 170 cm^2 port at any legal y.
    ok, reason = W.bl_panel_fit_feasible(_recorded_case_box())
    assert ok is False
    assert reason == W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION
    # BL's own per-component check at the demo y offsets fails too, which is what it reported.
    assert _bl_validate_reference(_recorded_case_box()) == W.BL_PANEL_FIT_DRIVER_WALL


def test_reshaped_height_560mm_makes_the_recorded_case_buildable() -> None:
    box = _recorded_case_box(external_height_mm=560.0)
    assert W.bl_panel_fit_feasible(box) == (True, None)


def test_shallow_depth_fires_only_the_port_rear_wall_rule() -> None:
    box = _recorded_case_box(external_height_mm=560.0, external_depth_mm=300.0)
    ok, reason = W.bl_panel_fit_feasible(box)
    assert ok is False
    assert reason == W.BL_PANEL_FIT_PORT_REAR_WALL
    # The walls and separation pass; only BL's rear-mouth rule fires.
    assert _bl_validate_reference(box) == W.BL_PANEL_FIT_PORT_REAR_WALL


@pytest.mark.parametrize("driver_y_m", [0.0, 0.02, -0.02, 0.24])
def test_driver_center_variant_matches_bl_formula(driver_y_m: float) -> None:
    box = _recorded_case_box(external_height_mm=560.0)
    expected = _bl_validate_reference(box, driver_y_m=driver_y_m)
    ok, reason = W.bl_panel_fit_feasible(box, driver_y_m=driver_y_m)
    assert (ok, reason) == (expected is None, expected)


def test_bl_panel_fit_is_deterministic() -> None:
    for box in (_recorded_case_box(), _recorded_case_box(external_height_mm=560.0)):
        first = W.bl_panel_fit_feasible(box)
        for _ in range(4):
            assert W.bl_panel_fit_feasible(box) == first


def test_separation_helper_agrees_with_the_boolean_gate() -> None:
    """The GUI numbers and the gate verdict come from one arithmetic (never disagree)."""
    heights = (300.0, 371.2, 420.0, 560.0, 700.0)
    areas = (20.0, 45.0, 100.0, 170.0)
    for height in heights:
        base = W.bl_panel_fit_separation(
            _recorded_case_box(external_height_mm=height, port_throat_area_cm2=20.0))
        for area in areas:
            box = _recorded_case_box(external_height_mm=height, port_throat_area_cm2=area)
            sep = W.bl_panel_fit_separation(box)
            assert W.bl_panel_fit_separation(box) == sep                     # deterministic
            # Same placement as the gate's defaults -> the same verdict, always.
            demo_y = W.bl_panel_fit_separation(
                box, driver_y_m=W.BL_DEMO_DRIVER_Y_M, port_y_m=W.BL_DEMO_PORT_Y_M)
            assert 0.0 <= demo_y["driver_y_m"] and demo_y["port_y_m"] <= 0.0
            assert (demo_y["feasible"], demo_y["reason"]) == W.bl_panel_fit_feasible(box)
            # The screen wrapper (max legal y) reports the same offsets and verdict.
            screen = W._bl_panel_fit_for_screen(box)
            assert (screen["driver_y_m"], screen["port_y_m"]) == \
                (sep["driver_y_m"], sep["port_y_m"])
            assert (screen["accepted"], screen["reason"]) == (sep["feasible"], sep["reason"])
            assert sep["required_m"] > 0.0 and sep["available_m"] > 0.0
            if area > 20.0:
                # A larger port needs strictly more separation and leaves strictly less room.
                assert sep["required_m"] > base["required_m"]
                assert sep["available_m"] < base["available_m"]


def test_separation_helper_reports_the_recorded_real_driver_numbers() -> None:
    # Sd-derived 12PR300 moving diameter on the recorded 371.2 mm, 18 mm wall, 45 cm^2 cell.
    sep = W.bl_panel_fit_separation(_recorded_case_box(port_throat_area_cm2=45.0),
                                    driver_moving_diameter_m=0.2605)
    assert sep["required_m"] == pytest.approx(0.1821, abs=5e-5)
    assert sep["available_m"] == pytest.approx(0.1501, abs=5e-5)
    assert sep["feasible"] is False
    assert sep["reason"] == W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION
    # With a supplied y pair the helper checks exactly that pair, not the max-legal one.
    fixed = W.bl_panel_fit_separation(_recorded_case_box(external_height_mm=560.0),
                                      driver_y_m=0.0, port_y_m=-0.13)
    assert (fixed["driver_y_m"], fixed["port_y_m"]) == (0.0, -0.13)
    assert (fixed["feasible"], fixed["reason"]) == W.bl_panel_fit_feasible(
        _recorded_case_box(external_height_mm=560.0), driver_y_m=0.0, port_y_m=-0.13)


def test_screen_rejects_bl_panel_fit_into_the_visible_ledger(tmp_path: Path) -> None:
    asset = _synthetic_asset(tmp_path)
    catalog = W.load_driver_catalog(["faitalpro_12pr300"])
    cabinet = C.VentedBoxRanges(
        net_volume_l_range=(115.0, 115.0), tuning_hz_range=(49.0, 50.0),
        port_throat_area_cm2_range=(170.0, 170.0), wall_mm=18.0)
    assembly = C.AssemblyRanges(horn_layout="separate_above")
    target = C.SystemTargets(
        listening_angle_h_deg=(-30.0, 30.0), listening_angle_v_deg=(-15.0, 15.0),
        low_freq_f3_hz_max=None)
    result = W.run_seed_screen(
        asset, catalog, cabinet=cabinet, assembly=assembly, target=target,
        envelope=_envelope(), limit_boxes=2, dz_offsets_mm=(0.0,),
        xo_range_hz=(600.0, 900.0), shortlist_size=3)
    fit_rows = [r for r in result.rejected_ledger if r["stage"] == "bl_panel_fit"]
    assert fit_rows, result.rejected_ledger
    assert all(row["reasons"] == [W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION]
               for row in fit_rows)
    assert result.counts["bl_panel_fit_rejected"] == len(fit_rows)
    assert result.kept_rows == ()
    assert result.study_id


# --------------------------------------------------------------------------- end-to-end replay


def test_identical_inputs_produce_byte_identical_outputs(tmp_path: Path) -> None:
    asset = _synthetic_asset(tmp_path)
    catalog = W.load_driver_catalog(
        ["faitalpro_10pr300", "faitalpro_12pr320"])
    cabinet = C.VentedBoxRanges(
        net_volume_l_range=(60.0, 115.0), tuning_hz_range=(40.0, 55.0),
        # 45 cm^2 is the largest port that survives the BL panel-fit gate on the 372 mm
        # 12-inch front; 100-170 cm^2 is now correctly refused before scoring.
        port_throat_area_cm2_range=(45.0, 45.0), wall_mm=18.0)
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


def _pareto_row(row_id: str, **overrides: float) -> dict:
    axes = {
        "match_error_h_db2": 1.0,
        "match_error_v_db2": 1.0,
        "lf_f3_hz": 40.0,
        "port_velocity_ratio": 0.5,
        "excursion_margin_db": 3.0,
        "cabinet_footprint_m2": 0.2,
        "mounting_distance_mm": 30.0,
    }
    axes.update(overrides)
    return {"row_id": row_id, "numeric_axes": axes, "feasibility": {}}


def test_nondominated_front_is_strict_and_keeps_ties() -> None:
    # ``good`` is better on one axis and equal elsewhere -> strict domination.
    good = _pareto_row("good", match_error_h_db2=0.5)
    worse = _pareto_row("worse", match_error_h_db2=1.5)
    # ``tradeoff`` is better on H but worse on V -> incomparable, both stay.
    tradeoff = _pareto_row("tradeoff", match_error_h_db2=0.4, match_error_v_db2=2.0)
    # ``tie`` equals ``good`` -> no strict improvement either way, both stay.
    tie = _pareto_row("tie", match_error_h_db2=0.5)

    front = W._nondominated([good, worse, tradeoff, tie])
    ids = {row["row_id"] for row in front}
    assert ids == {"good", "tradeoff", "tie"}
    assert "worse" not in ids
