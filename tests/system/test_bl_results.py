"""Tests for the canonical reader of real Boundary Lab headless solve results.

The static fixture under ``fixtures/bl_results/reference_run`` is authored to the field names
of BL 0.5.0's ``HeadlessResultWriter`` (``src/blab/headless.py:399-541``): manifest.json,
compiled-system.json, domains.json/domains.npz and per-frequency ``frequencies/NNNNNN.{json,npz}``.
Negative cases are produced by mutating a temporary copy; the fixture itself is never edited.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system.boundarylab import bl_results as R  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"
FREQS = (100.0, 200.0)
EXCITATIONS = ("excitation:woofer", "excitation:horn")


# --------------------------------------------------------------------------- helpers

def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "reference_run"
    shutil.copytree(FIXTURE, target)
    return target


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutate_json(path: Path, mutate: Callable[[dict[str, Any]], object]) -> None:
    payload = _json(path)
    mutate(payload)
    _write_json(path, payload)


def _npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as arrays:
        return {key: np.asarray(arrays[key]) for key in arrays.files}


def _write_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    np.savez_compressed(path, **arrays)


def _reference_values(stem: str, key: str) -> np.ndarray:
    return _npz(FIXTURE / "frequencies" / f"{stem}.npz")[key]


# --------------------------------------------------------------------------- positive round trip

def test_reference_run_round_trips_all_domains() -> None:
    assert R.is_bl_headless_result_dir(FIXTURE) is True
    result = R.read_bl_headless_result(FIXTURE)

    assert tuple(result.frequencies_hz.tolist()) == FREQS
    assert result.excitation_ids == EXCITATIONS
    assert set(result.domain_ids()) == {
        "observation:horizontal-polar",
        "observation:vertical-polar",
        "observation:probe:on_axis",
    }
    assert result.data_quality["quality"] == "EXACT_COMPLEX"
    assert result.data_quality["unit"] == "Pa"
    assert result.data_quality["rms_phasors"] is True
    assert result.data_quality["phasor_conventions_observed"] == [R.BL_PHASOR_CONVENTION]
    assert result.data_quality["axes_source"] == "json_axes"
    assert result.data_quality["missing_frequency_indices"] == []
    assert result.provenance.status == "complete"
    assert result.provenance.backend_id == "beat_cpu"
    assert result.provenance.solve_kind == "exterior_bem"
    assert result.provenance.phasor_convention == R.BL_PHASOR_CONVENTION
    assert result.provenance.phasor_conversion == f"{R.BL_PHASOR_CONVENTION} -> {C.TIME_CONVENTION}"
    assert result.provenance.frequency_indices == (0, 1)
    assert result.provenance.frequency_files == (
        "frequencies/000000.json", "frequencies/000000.npz",
        "frequencies/000001.json", "frequencies/000001.npz",
    )

    # Manifest/per-file provenance digests are the real file digests.
    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert result.provenance.manifest_sha256 == sha(FIXTURE / "manifest.json")
    assert result.provenance.compiled_system_sha256 == sha(FIXTURE / "compiled-system.json")
    assert result.provenance.domains_json_sha256 == sha(FIXTURE / "domains.json")
    digest_map = dict(result.provenance.frequency_artifact_sha256)
    assert digest_map["frequencies/000001.npz"] == sha(FIXTURE / "frequencies" / "000001.npz")

    # Values survive exactly: (excitation, observation) split, stacked over frequency.
    stacked = result.per_excitation_bases("observation:horizontal-polar")
    assert list(stacked) == list(EXCITATIONS)
    expected0 = _reference_values("000000", "q0000")
    expected1 = _reference_values("000001", "q0000")
    for index, name in enumerate(EXCITATIONS):
        assert stacked[name].shape == (2, 3)
        assert stacked[name].dtype == np.complex128
        np.testing.assert_array_equal(stacked[name][0], expected0[index])
        np.testing.assert_array_equal(stacked[name][1], expected1[index])
    assert result.data_quality["per_input_by_excitation"] == {
        "excitation:woofer": "normal_velocity_mps",
        "excitation:horn": "normal_velocity_mps",
    }


def test_observation_metadata_is_declared_and_polar_distance_derived() -> None:
    result = R.read_bl_headless_result(FIXTURE)
    horizontal = result.observation_sets["observation:horizontal-polar"]
    assert horizontal.kind == "polar_observation"
    assert horizontal.count == 3
    assert horizontal.distance_m == pytest.approx(2.0)
    assert horizontal.origin_xyz_m == (0.0, 0.0, 0.0)
    assert horizontal.angular_frame == "bl_polar_observation:observation:horizontal-polar"
    assert horizontal.angles_deg is not None
    np.testing.assert_allclose(horizontal.angles_deg, [0.0, 45.0, 180.0])

    probe = result.observation_sets["observation:probe:on_axis"]
    assert probe.kind == "point_probe"
    assert probe.distance_m is None  # mixed radii: never averaged into a fake reference distance
    assert probe.angular_frame == "bl_point_probe:observation:probe:on_axis"
    assert any("samples multiple radii" in note for note in result.provenance.notes)

    basis = result.basis_for("excitation:woofer", "observation:horizontal-polar")
    assert isinstance(basis, C.SourceBasis)
    assert basis.per_input == "normal_velocity_mps"
    assert basis.time_convention == C.TIME_CONVENTION
    assert basis.quantity == "pressure_pa"
    assert basis.distance_m == pytest.approx(2.0)
    assert basis.origin_xyz_m == (0.0, 0.0, 0.0)
    assert basis.source_geometry_hash == result.provenance.source_geometry_hash
    assert basis.source_geometry_hash is not None
    assert "system.bl_source_geometry_v1" not in basis.source_geometry_hash  # domain, not payload

    # Two BL result domains can share a kind but are different observation sets: the declared
    # frame carries the domain id, so the contract refuses a cross-plane coherent sum.
    vertical_basis = result.basis_for("excitation:woofer", "observation:vertical-polar")
    ok, reason = basis.compatible_for_sum_with(vertical_basis)
    assert ok is False and "angular frame" in reason


def test_unit_conversion_records_are_preserved_per_excitation() -> None:
    result = R.read_bl_headless_result(FIXTURE)
    assert {record.excitation_id for record in result.conversion} == set(EXCITATIONS)
    for name in EXCITATIONS:
        record = result.conversion_record(name)
        assert record.from_quantity == R.BL_PRESSURE_QUANTITY
        assert record.from_unit == "Pa"
        assert record.to_quantity == "pressure_pa"
        assert record.to_unit == "Pa"
        assert record.to_per_input == "normal_velocity_mps"
        assert "1 m/s" in record.from_per_input
        assert record.factor == 1.0
        assert record.phasor_from == R.BL_PHASOR_CONVENTION
        assert record.phasor_to == C.TIME_CONVENTION
        assert record.conjugated is False
        assert record.basis_declared_by == "compiled-system.json excitation_ports[].kind"
        assert "excitation_ports[].kind" in record.as_dict()["basis_declared_by"]


def test_to_system_response_assembles_contract_object() -> None:
    result = R.read_bl_headless_result(FIXTURE)
    response = R.to_system_response(result, "observation:horizontal-polar",
                                    fidelity="INSTALLED_EXTERIOR_BEM")
    assert isinstance(response, C.SystemResponse)
    assert response.excitation_names == EXCITATIONS
    assert response.fidelity == "INSTALLED_EXTERIOR_BEM"
    assert response.p_total is None
    assert response.magnitude_screen is None
    assert response.observation_directions is not None
    assert response.observation_directions.shape == (3, 3)
    np.testing.assert_allclose(np.linalg.norm(response.observation_directions, axis=1), 1.0)
    assert response.observation_angles_deg == ("angle_deg",)
    p_by_excitation = response.p_by_excitation
    assert p_by_excitation is not None
    for name in EXCITATIONS:
        assert p_by_excitation[name].shape == (2, 3)
        assert response.excitation_bases[name].per_input == "normal_velocity_mps"
    assert response.physics_provenance["source"] == "boundary_lab_headless_result"
    assert response.physics_provenance["bl_result"]["manifest_sha256"]

    # The contract itself accepts the coherent sum inside one declared frame.
    a = response.excitation_bases[EXCITATIONS[0]]
    b = response.excitation_bases[EXCITATIONS[1]]
    ok, reason = a.compatible_for_sum_with(b)
    assert ok is True, reason


# --------------------------------------------------------------------------- per-input references

def test_voltage_port_is_v_rms_and_mixing_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "compiled-system.json", lambda payload: payload["excitation_ports"][1]
                 .__setitem__("kind", "voltage"))
    result = R.read_bl_headless_result(root)

    assert result.basis_for("excitation:woofer", "observation:vertical-polar").per_input == \
        "normal_velocity_mps"
    horn_basis = result.basis_for("excitation:horn", "observation:vertical-polar")
    assert horn_basis.per_input == "V_rms"
    assert result.conversion_record("excitation:horn").to_per_input == "V_rms"
    assert "2.83 V" in result.conversion_record("excitation:horn").from_per_input
    assert result.data_quality["per_input_by_excitation"]["excitation:horn"] == "V_rms"

    # The manifest orders woofer first; the guard refuses the mixed reference set.
    fields = result.fields_for("observation:vertical-polar")
    assert fields[0].basis.per_input == "normal_velocity_mps"
    with pytest.raises(C.IncompatibleBasis, match="SENSITIVITY_REFERENCE_MISMATCH"):
        result.assert_shared_sensitivity_reference("observation:vertical-polar")

    # Every excitation still gets its own explicit basis; no single mixed-sensitivity field.
    assert {field.basis.per_input for field in fields} == {"normal_velocity_mps", "V_rms"}
    for field in fields:
        assert field.per_input_declaration


def test_unknown_port_kind_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "compiled-system.json", lambda payload: payload["excitation_ports"][0]
                 .__setitem__("kind", "pressure"))
    with pytest.raises(C.DataQualityError, match="EXCITATION_BASIS_UNKNOWN"):
        R.read_bl_headless_result(root)


# --------------------------------------------------------------------------- independence guard

def test_per_excitation_independence_is_structural_and_documented() -> None:
    result = R.read_bl_headless_result(FIXTURE)
    summary = result.assert_per_excitation_independence("observation:horizontal-polar")
    assert summary["excitations"] == list(EXCITATIONS)
    assert summary["frequency_count"] == 2
    assert summary["observation_count"] == 3
    assert set(summary["per_excitation"]) == set(EXCITATIONS)
    assert "no numerical rank claim" in summary["independence_claim"]
    for name in EXCITATIONS:
        assert summary["per_excitation"][name]["max_abs_pa"] > 0.0


def test_exactly_zero_excitation_block_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    for stem in ("000000", "000001"):
        path = root / "frequencies" / f"{stem}.npz"
        arrays = _npz(path)
        arrays["q0000"][1, :] = 0.0
        _write_npz(path, arrays)
    result = R.read_bl_headless_result(root)
    with pytest.raises(C.DataQualityError, match="not driven"):
        result.assert_per_excitation_independence("observation:horizontal-polar")


def test_non_finite_excitation_block_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    path = root / "frequencies" / "000000.npz"
    arrays = _npz(path)
    arrays["q0001"][0, 0] = complex(np.nan, 0.0)
    _write_npz(path, arrays)
    result = R.read_bl_headless_result(root)
    with pytest.raises(C.DataQualityError, match="non-finite"):
        result.assert_per_excitation_independence("observation:vertical-polar")


# --------------------------------------------------------------------------- refusals

def test_magnitude_only_payload_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    for stem in ("000000", "000001"):
        path = root / "frequencies" / f"{stem}.npz"
        arrays = {key: np.abs(value).astype(np.float64) for key, value in _npz(path).items()}
        _write_npz(path, arrays)
        _mutate_json(root / "frequencies" / f"{stem}.json",
                     lambda payload: [quantity.__setitem__("dtype", "float64")
                                      for quantity in payload["quantities"]])
    with pytest.raises(C.DataQualityError, match="MAGNITUDE_ONLY"):
        R.read_bl_headless_result(root)


def test_missing_complex_pressure_raises_phase_token(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    for stem in ("000000", "000001"):
        _mutate_json(root / "frequencies" / f"{stem}.json",
                     lambda payload: [quantity.__setitem__("quantity", "radiation_impedance")
                                      for quantity in payload["quantities"]])
    with pytest.raises(C.DataQualityError, match="PHASE_ALIGNMENT_UNAVAILABLE"):
        R.read_bl_headless_result(root)


def test_wrong_manifest_schema_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "manifest.json", lambda payload: payload.__setitem__("schema", "blabsp"))
    with pytest.raises(C.DataQualityError, match="SCHEMA_MISMATCH"):
        R.read_bl_headless_result(root)


def test_wrong_manifest_version_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "manifest.json", lambda payload: payload.__setitem__("schema_version", 1))
    with pytest.raises(C.DataQualityError, match="SCHEMA_MISMATCH"):
        R.read_bl_headless_result(root)


def test_missing_compiled_system_refuses_excitation_basis(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "compiled-system.json").unlink()
    with pytest.raises(C.DataQualityError, match="EXCITATION_BASIS_UNKNOWN"):
        R.read_bl_headless_result(root)


def test_missing_domains_refuses_observation_metadata(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "domains.json").unlink()
    with pytest.raises(C.DataQualityError, match="OBSERVATION_METADATA_MISSING"):
        R.read_bl_headless_result(root)


def test_unknown_unit_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "frequencies" / "000000.json",
                 lambda payload: payload["quantities"][0].__setitem__("unit", "dB re 20 uPa"))
    with pytest.raises(C.DataQualityError, match="UNITS_UNSUPPORTED"):
        R.read_bl_headless_result(root)


def test_declared_dtype_mismatch_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "frequencies" / "000001.json",
                 lambda payload: payload["quantities"][0].__setitem__("dtype", "complex64"))
    with pytest.raises(C.DataQualityError, match="SCHEMA_MISMATCH"):
        R.read_bl_headless_result(root)


def test_frequency_axis_mismatch_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "frequencies" / "000001.json",
                 lambda payload: payload.__setitem__("freq_hz", 250.0))
    with pytest.raises(C.DataQualityError, match="FREQUENCY_AXIS_MISMATCH"):
        R.read_bl_headless_result(root)


def test_incomplete_run_is_refused_unless_partial_is_requested(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "manifest.json", lambda payload: (
        payload.__setitem__("status", "interrupted"),
        payload.__setitem__("completion_mask", [True, False]),
    ))
    with pytest.raises(C.DataQualityError, match="INCOMPLETE_RUN"):
        R.read_bl_headless_result(root)

    partial = R.read_bl_headless_result(root, allow_partial=True)
    assert partial.frequencies_hz.size == 2
    assert partial.provenance.frequency_indices == (0,)
    assert partial.data_quality["missing_frequency_indices"] == [1]
    assert partial.data_quality["completed_frequencies"] == 1
    # A partial read never fabricates the missing frequency: it is NaN, not a zero field.
    assert np.all(np.isnan(partial.per_excitation_bases("observation:horizontal-polar")
                           ["excitation:woofer"][1]))
    with pytest.raises(C.DataQualityError, match="INCOMPLETE_RUN"):
        partial.assert_per_excitation_independence("observation:horizontal-polar")
    # A committed row stays the real value on the same axis.
    reference = R.read_bl_headless_result(FIXTURE)
    np.testing.assert_array_equal(
        partial.per_excitation_bases("observation:horizontal-polar")["excitation:woofer"][0],
        reference.per_excitation_bases("observation:horizontal-polar")["excitation:woofer"][0],
    )
    # A partial read never fabricates the missing frequency: the uncommitted index stays zero
    # but is excluded from the completed set, and the note says so.
    assert any("partial read" in note for note in partial.provenance.notes)


def test_legacy_phasor_is_conjugated_exactly_once(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "manifest.json",
                 lambda payload: payload.__setitem__("phasor_convention", "exp(-i omega t)"))
    for stem in ("000000", "000001"):
        _mutate_json(root / "frequencies" / f"{stem}.json",
                     lambda payload: payload["diagnostics"].__setitem__(
                         "phasor_convention", "exp(-i omega t)"))
    converted = R.read_bl_headless_result(root)
    reference = R.read_bl_headless_result(FIXTURE)
    for name in EXCITATIONS:
        np.testing.assert_array_equal(
            converted.per_excitation_bases("observation:horizontal-polar")[name],
            np.conjugate(reference.per_excitation_bases("observation:horizontal-polar")[name]),
        )
        record = converted.conversion_record(name)
        assert record.conjugated is True
        assert record.phasor_from == "exp(-i omega t)"
    assert any("conjugated once" in note for note in converted.provenance.notes)


def test_unknown_phasor_convention_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "manifest.json",
                 lambda payload: payload.__setitem__("phasor_convention", "exp(+jomega_t)"))
    with pytest.raises(C.DataQualityError, match="PHASOR_CONVENTION_UNSUPPORTED"):
        R.read_bl_headless_result(root)


def test_manifest_and_frequency_convention_disagreement_is_refused(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _mutate_json(root / "frequencies" / "000000.json",
                 lambda payload: payload["diagnostics"].__setitem__(
                     "phasor_convention", "exp(-i omega t)"))
    with pytest.raises(C.DataQualityError, match="PHASOR_CONVENTION_UNSUPPORTED"):
        R.read_bl_headless_result(root)


# --------------------------------------------------------------------------- axes handling

def test_axes_order_is_honoured_when_json_declares_observation_first(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    reference = R.read_bl_headless_result(FIXTURE)
    for stem in ("000000", "000001"):
        path = root / "frequencies" / f"{stem}.npz"
        arrays = _npz(path)
        for key in ("q0000", "q0001", "q0002"):
            arrays[key] = np.ascontiguousarray(arrays[key].T)
        _write_npz(path, arrays)
        _mutate_json(root / "frequencies" / f"{stem}.json",
                     lambda payload: [quantity.__setitem__(
                         "axes", ["observation", "excitation"])
                         for quantity in payload["quantities"]])
        _mutate_json(root / "frequencies" / f"{stem}.json",
                     lambda payload: [quantity.__setitem__(
                         "shape", list(reversed(quantity["shape"])))
                         for quantity in payload["quantities"]])
    reordered = R.read_bl_headless_result(root)
    for domain in ("observation:horizontal-polar", "observation:vertical-polar",
                   "observation:probe:on_axis"):
        for name in EXCITATIONS:
            np.testing.assert_array_equal(
                reordered.per_excitation_bases(domain)[name],
                reference.per_excitation_bases(domain)[name],
            )
    assert reordered.data_quality["axes_source"] == "json_axes"


def test_empty_axes_falls_back_to_documented_shape_and_records_the_blocker(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    for stem in ("000000", "000001"):
        _mutate_json(root / "frequencies" / f"{stem}.json",
                     lambda payload: [quantity.__setitem__("axes", [])
                                      for quantity in payload["quantities"]])
    result = R.read_bl_headless_result(root)
    assert result.data_quality["axes_source"] == "shape_inferred"
    assert any(note.startswith("BLOCKED_BY_BL_RESULT_FORMAT") for note in result.provenance.notes)
    reference = R.read_bl_headless_result(FIXTURE)
    np.testing.assert_array_equal(
        result.per_excitation_bases("observation:horizontal-polar")["excitation:woofer"],
        reference.per_excitation_bases("observation:horizontal-polar")["excitation:woofer"],
    )


def test_is_bl_headless_result_dir_rejects_non_results(tmp_path: Path) -> None:
    assert R.is_bl_headless_result_dir(tmp_path) is False
    other = tmp_path / "something"
    other.mkdir()
    (other / "manifest.json").write_text('{"schema": "blabsp"}', encoding="utf-8")
    assert R.is_bl_headless_result_dir(other) is False


def test_missing_result_directory_raises_not_found(tmp_path: Path) -> None:
    with pytest.raises(C.DataQualityError, match="BL_RESULT_NOT_FOUND"):
        R.read_bl_headless_result(tmp_path / "does_not_exist")
