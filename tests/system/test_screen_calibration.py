"""Hermetic tests for the R7a screen ``E_shape`` calibration-record builder.

The fixtures below are minimal hand-authored artifacts: a stored-screen ``response.npz`` plus a
screen study JSON, and a minimal BL headless result directory.  No real run, GPU, or network is
touched.  The synthetic BEM case uses a known analytic pattern (woofer omnidirectional, horn
``[-6,-4,-2,0,-2,-4,-6] dB``), so its ``E_shape`` is exactly 16 dB².
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pytest

from hornlab_search.system import piston
from hornlab_search.system import screen_calibration as SC
from hornlab_search.system.boundarylab import bl_results as R

_FREQS = (100.0, 200.0, 300.0)
_COMMON = (-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0)
_HORN_REL = (-6.0, -4.0, -2.0, 0.0, -2.0, -4.0, -6.0)  # mean square = 16 dB²
_RADIUS_M = 0.13
_OFFSET = np.where(np.isclose(np.arange(-90.0, 90.1, 2.5), 0.0), 0.0, 1.0)


# --------------------------------------------------------------------------- fixture helpers


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _screen_response(
    path: Path,
    *,
    freqs: Sequence[float] = _FREQS,
    angles: np.ndarray | None = None,
    radius_m: float = _RADIUS_M,
) -> Path:
    """Write a magnitude-only stored screen response with a known piston+offset pattern."""
    angles = np.arange(-90.0, 90.1, 2.5) if angles is None else np.asarray(angles, dtype=float)
    freq_arr = np.asarray(freqs, dtype=float)
    piston_rel = np.asarray(piston.relative_level_db(freq_arr, radius_m, angles), dtype=float)
    # The 0 deg offset is zero, so normalisation at 0 deg leaves piston_rel + offset.
    offset = (np.abs(angles) > 1e-9).astype(float)
    spl = piston_rel + offset[None, :] + 100.0
    np.savez_compressed(
        path,
        freqs_hz=freq_arr,
        h_angles_deg=angles,
        v_angles_deg=angles,
        spl_h_db=spl,
        spl_v_db=spl,
    )
    return path


def _screen_study(
    tmp_path: Path,
    *,
    response_name: str = "response.npz",
    radius_m: float = _RADIUS_M,
    freqs: Sequence[float] = _FREQS,
) -> Path:
    response = _screen_response(tmp_path / response_name, freqs=freqs, radius_m=radius_m)
    doc = {
        "study_id": "study-test",
        "asset": {
            "asset_id": "asset-test",
            "design_hash": "deadbeef",
            "quality": "MAGNITUDE_ONLY",
            "brief_id": "test-brief",
            "family": "FREEFORM",
        },
        "screen_response_path": response_name,
        "screen_freqs_hz": list(freqs),
        "driver_id": "testdriver",
        "catalog": [
            {
                "driver_id": "testdriver",
                "name": "Test Driver",
                "sd_cm2": math.pi * (radius_m ** 2) * 1e4,
                "effective_piston_radius_m": radius_m,
            }
        ],
        "metric_spec": {"half_octaves": 1.0 / 3.0, "good_match_db2": 9.0},
        "input_sha256": {
            "asset_response_npz": _sha256(response),
        },
    }
    screen_json = tmp_path / "screen_study.json"
    _write_json(screen_json, doc)
    return screen_json


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bl_case(
    root: Path,
    *,
    freqs: Sequence[float] = _FREQS,
    angles: np.ndarray | None = None,
    horn_rel_db: Sequence[float] = _HORN_REL,
    woofer_rel_db: Sequence[float] | None = None,
) -> Path:
    """Write a minimal BL headless result directory under ``root/run``."""
    angles = (np.arange(-180.0, 180.1, 10.0) if angles is None
              else np.asarray(angles, dtype=float))
    freq_arr = np.asarray(freqs, dtype=float)
    n_angles = angles.size
    if woofer_rel_db is None:
        woofer_rel_db = tuple(0.0 for _ in range(n_angles))
    horn_arr = np.asarray(horn_rel_db, dtype=float)
    woofer_arr = np.asarray(woofer_rel_db, dtype=float)
    if horn_arr.size != n_angles or woofer_arr.size != n_angles:
        raise AssertionError("synthetic patterns must match the direction count")

    run = root / "run"
    run.mkdir(parents=True, exist_ok=True)

    points_h = np.asarray([
        [2.0 * math.sin(math.radians(a)), 0.0, 2.0 * math.cos(math.radians(a))]
        for a in angles
    ])
    points_v = np.asarray([
        [0.0, 2.0 * math.sin(math.radians(a)), 2.0 * math.cos(math.radians(a))]
        for a in angles
    ])
    np.savez_compressed(
        run / "domains.npz",
        d0000_c_0000=points_h,
        d0000_c_0001=np.asarray(angles, dtype=np.float32),
        d0001_c_0000=points_v,
        d0001_c_0001=np.asarray(angles, dtype=np.float32),
    )
    _write_json(run / "domains.json", {
        "domains": [
            {
                "id": "observation:horizontal-polar",
                "kind": "polar_observation",
                "coordinates": {"angle_deg": "d0000_c_0001", "points_m": "d0000_c_0000"},
                "metadata": {"plane": "horizontal"},
                "dimensions": ["observation"],
                "topology": {},
            },
            {
                "id": "observation:vertical-polar",
                "kind": "polar_observation",
                "coordinates": {"angle_deg": "d0001_c_0001", "points_m": "d0001_c_0000"},
                "metadata": {"plane": "vertical"},
                "dimensions": ["observation"],
                "topology": {},
            },
        ]
    })
    _write_json(run / "compiled-system.json", {
        "contract_version": 1,
        "id": "system:test",
        "name": "test",
        "components": [],
        "interfaces": [],
        "meshes": [],
        "metadata": {},
        "regions": [],
        "excitation_ports": [
            {"component_id": "vented/driver", "id": "vented/voltage", "kind": "voltage",
             "name": "vented voltage"},
            {"component_id": "component:horn", "id": "excitation:horn",
             "kind": "normal_velocity", "name": "horn unit normal velocity"},
        ],
    })

    excitations = ("vented/voltage", "excitation:horn")
    (run / "frequencies").mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for index, freq in enumerate(freq_arr):
        horn_mag = np.power(10.0, horn_arr / 20.0).astype(np.complex128)
        woofer_mag = np.power(10.0, woofer_arr / 20.0).astype(np.complex128)
        pressure = np.stack([woofer_mag, horn_mag], axis=0)  # (excitation, observation)
        np.savez_compressed(
            run / "frequencies" / f"{index:06d}.npz",
            q0000=pressure.astype(np.complex128),
            q0001=pressure.astype(np.complex128),
        )
        _write_json(run / "frequencies" / f"{index:06d}.json", {
            "arrays_file": f"{index:06d}.npz",
            "diagnostics": {"phasor_convention": R.BL_PHASOR_CONVENTION},
            "excitation_port_ids": list(excitations),
            "freq_hz": float(freq),
            "quantities": [
                {
                    "axes": ["excitation", "observation"],
                    "dtype": "complex128",
                    "id": "acoustic:pressure:horizontal-polar",
                    "key": "q0000",
                    "quantity": R.BL_PRESSURE_QUANTITY,
                    "shape": [2, n_angles],
                    "target_id": "observation:horizontal-polar",
                    "unit": R.BL_PRESSURE_UNIT,
                },
                {
                    "axes": ["excitation", "observation"],
                    "dtype": "complex128",
                    "id": "acoustic:pressure:vertical-polar",
                    "key": "q0001",
                    "quantity": R.BL_PRESSURE_QUANTITY,
                    "shape": [2, n_angles],
                    "target_id": "observation:vertical-polar",
                    "unit": R.BL_PRESSURE_UNIT,
                },
            ],
        })
        results.append({
            "arrays_file": f"frequencies/{index:06d}.npz",
            "freq_hz": float(freq),
            "metadata_file": f"frequencies/{index:06d}.json",
        })

    _write_json(run / "manifest.json", {
        "backend_id": "beat_cpu",
        "completion_mask": [True] * len(freq_arr),
        "excitation_port_ids": list(excitations),
        "frequencies_hz": [float(f) for f in freq_arr],
        "meshes": [],
        "phasor_convention": R.BL_PHASOR_CONVENTION,
        "results": results,
        "schema": R.BL_HEADLESS_SCHEMA,
        "schema_version": R.BL_HEADLESS_SCHEMA_VERSION,
        "solve_kind": "exterior_bem",
        "status": "complete",
    })
    return root


# --------------------------------------------------------------------------- grid selection


def test_common_grid_is_the_exact_stored_intersection() -> None:
    screen = np.arange(-90.0, 90.1, 2.5)
    bem = np.arange(-180.0, 180.1, 10.0)
    common, record = SC.common_direction_grid(screen, screen, bem, bem, max_deg=30.0)
    assert common == list(_COMMON)
    assert record["n_dirs"] == 7
    assert record["no_interpolation"] is True
    assert record["angles_deg"] == list(_COMMON)


def test_common_grid_excludes_a_direction_missing_from_one_axis() -> None:
    # 5.0 deg exists on the screen grid but not on the 10 deg BEM grid; it must not be invented.
    screen = np.asarray([-30.0, -20.0, -10.0, 0.0, 5.0, 10.0, 20.0, 30.0])
    bem = np.asarray(_COMMON)
    common, _ = SC.common_direction_grid(screen, screen, bem, bem, max_deg=30.0)
    assert common == list(_COMMON)
    assert 5.0 not in common


def test_common_grid_refuses_without_an_exact_on_axis_sample() -> None:
    grid = np.asarray([-20.0, -10.0, 10.0, 20.0, 30.0])
    with pytest.raises(SC.CalibrationRecordError) as caught:
        SC.common_direction_grid(grid, grid, grid, grid, max_deg=30.0)
    assert caught.value.token == "SCREEN_GRID_NO_ON_AXIS"


def test_common_grid_refuses_fewer_than_five_directions() -> None:
    grid = np.asarray([-10.0, 0.0, 10.0])
    with pytest.raises(SC.CalibrationRecordError) as caught:
        SC.common_direction_grid(grid, grid, grid, grid, max_deg=30.0)
    assert caught.value.token == "SCREEN_GRID_TOO_FEW_DIRECTIONS"


# --------------------------------------------------------------------------- frequency mapping


def test_frequency_mapping_records_nearest_stored_bem_samples_and_error() -> None:
    mapping, summary = SC.map_frequencies(
        [773.24, 961.58, 1195.8], [785.5785, 969.6137, 1196.7624], rel_tol=0.02)
    assert [row["bem_hz"] for row in mapping] == [785.5785, 969.6137, 1196.7624]
    assert [row["screen_hz"] for row in mapping] == [773.24, 961.58, 1195.8]
    assert summary["mapping"] == mapping
    assert summary["no_interpolation"] is True
    assert max(summary["relative_errors"]) <= 0.02
    np.testing.assert_allclose(
        summary["relative_errors"],
        [(785.5785 - 773.24) / 773.24, (969.6137 - 961.58) / 961.58,
         (1196.7624 - 1195.8) / 1195.8],
        rtol=0.0, atol=1e-15)


def test_frequency_mapping_refuses_when_the_nearest_sample_is_outside_tolerance() -> None:
    with pytest.raises(SC.CalibrationRecordError) as caught:
        SC.map_frequencies([500.0], [515.6693], rel_tol=0.02)
    assert caught.value.token == "FREQUENCY_MAPPING_REFUSED"
    assert "515.669" in str(caught.value)


def test_frequency_mapping_accepts_a_sample_inside_tolerance() -> None:
    mapping, summary = SC.map_frequencies([100.0], [101.0], rel_tol=0.02)
    assert mapping == [{"screen_hz": 100.0, "bem_hz": 101.0, "relative_error": 0.01}]
    assert summary["mapping"] == mapping


def test_frequency_mapping_refuses_two_screen_frequencies_collapsing_onto_one_bem_sample() -> None:
    with pytest.raises(SC.CalibrationRecordError) as caught:
        SC.map_frequencies([100.0, 101.0], [100.5], rel_tol=0.02)
    assert caught.value.token == "FREQUENCY_MAPPING_DUPLICATE"


# --------------------------------------------------------------------------- synthetic E_shape


def _build_record(tmp_path: Path, *, generated_utc: str = "2026-11-21T00:00:00Z") -> dict[str, Any]:
    screen_json = _screen_study(tmp_path)
    # Keep the synthetic BEM grid on the common directions; the screen still stores a denser
    # 2.5 deg grid, so exact intersection is exercised.
    bem_case = _write_bl_case(tmp_path / "bem_case", angles=np.asarray(_COMMON))
    return SC.build_calibration_record(
        screen_json, bem_case, rel_tol=0.02, max_deg=30.0, generated_utc=generated_utc)


def test_synthetic_bl_result_reproduces_the_known_eshape(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    assert record["schema"] == SC.SCHEMA
    assert record["study_id"] == "study-test"
    assert record["asset_id"] == "asset-test"
    assert record["common_grid"]["angles_deg"] == list(_COMMON)
    assert record["frequency_map"]["mapping"] == [
        {"screen_hz": float(f), "bem_hz": float(f), "relative_error": 0.0} for f in _FREQS
    ]
    for plane in ("H", "V"):
        axis = record["axes"][plane]
        assert axis["bem_e_shape_db2"] == pytest.approx(16.0, rel=1e-12, abs=1e-12)
        assert axis["screen_e_shape_db2"] == pytest.approx(6.0 / 7.0, rel=1e-12, abs=1e-12)
        assert axis["screen_to_bem_factor"] == pytest.approx(
            16.0 / (6.0 / 7.0), rel=1e-12, abs=1e-12)
        assert axis["n_dirs"] == 7
        assert axis["n_freqs"] == 3
    assert record["screen_study"]["driver"]["driver_id"] == "testdriver"
    assert record["screen_study"]["driver"]["effective_piston_radius_m"] == pytest.approx(_RADIUS_M)


def test_confound_and_threshold_labels_are_explicit(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    assert record["confound_tokens"] == [SC.CONFOUND_DEMO_SHAPE_R2]
    assert SC.CONFOUND_DEMO_SHAPE_R2 in record["tokens"]
    assert SC.TOKEN_THRESHOLD_UNCHANGED in record["tokens"]
    assert record["threshold"]["value_db2"] == 9.0
    assert record["threshold"]["token"] == SC.TOKEN_THRESHOLD_UNCHANGED
    assert record["threshold"]["changed"] is False
    assert record["threshold"]["recalibrated"] is False
    assert record["recalibrated"] is False
    assert record["status"] == "QUANTIFIED_NOT_RECALIBRATED"
    assert record["confounds"][SC.CONFOUND_DEMO_SHAPE_R2]["present"] is True


def test_serialisation_is_byte_identical_apart_from_generated_utc(tmp_path: Path) -> None:
    first = _build_record(tmp_path, generated_utc="2026-11-21T00:00:00Z")
    second = _build_record(tmp_path, generated_utc="2026-11-21T00:00:00Z")
    assert SC.record_to_json(first) == SC.record_to_json(second)

    other = _build_record(tmp_path, generated_utc="2026-11-21T00:00:01Z")
    assert other["generated_utc"] == "2026-11-21T00:00:01Z"
    other_copy = dict(other)
    other_copy["generated_utc"] = first["generated_utc"]
    assert SC.record_to_json(other_copy) == SC.record_to_json(first)


def test_write_calibration_record_matches_record_to_json(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    target = SC.write_calibration_record(record, tmp_path / "out" / "record.json")
    assert target.read_text(encoding="utf-8") == SC.record_to_json(record)
