"""Contract §3 tests: ``hornlab_search.system.calibration`` + the ``combine`` hook.

The fixtures are synthetic (no real calibration values). The two-excitation response mimics a
horn solved as normal velocity (Pa per m/s) and a woofer as voltage (Pa per V_rms) in one shared
observation frame; the record brings both to Pa per V_rms.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import calibration as cal  # noqa: E402
from hornlab_search.system import combine as comb  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402

FREQS = (500.0, 1000.0, 2000.0)
CASE = "exp_alpha/case_001"
HORN_FIELD = np.array([[1.0 + 0.5j, 0.5 - 0.25j],
                       [0.8 + 0.1j, -0.4 + 0.3j],
                       [0.6 - 0.7j, 0.9 + 0.2j]], dtype=np.complex128)
WOOFER_FIELD = np.array([[0.3 + 0.2j, -0.2 + 0.1j],
                         [0.25 - 0.1j, 0.4 + 0.05j],
                         [0.1 + 0.3j, -0.3 - 0.2j]], dtype=np.complex128)
HORN_FACTOR = (0.5 + 0.1j, 0.45 - 0.05j, 0.4 + 0.02j)
WOOFER_FACTOR = (1.0 + 0.0j, 1.0 + 0.0j, 1.0 + 0.0j)
BANK = {"horn": np.ones(len(FREQS)), "woofer": np.ones(len(FREQS))}
LEVELS = {"horn": 1.0, "woofer": 1.0}
CREATED = "2026-11-20T00:00:00+00:00"


def _basis(per_input: str) -> C.SourceBasis:
    return C.SourceBasis(
        per_input=per_input,
        distance_m=1.0,
        origin_xyz_m=(0.0, 0.0, 0.0),
        angular_frame="cartesian_dirs",
        source_geometry_hash="geom-shared",
    )


def _response(*, fidelity: str = "INSTALLED_EXTERIOR_BEM",
              horn_field: np.ndarray = HORN_FIELD,
              woofer_field: np.ndarray = WOOFER_FIELD,
              per_inputs: tuple[str, str] = ("normal_velocity_mps", "V_rms")
              ) -> C.SystemResponse:
    return C.SystemResponse(
        frequencies_hz=np.array(FREQS, dtype=np.float64),
        excitation_names=("horn", "woofer"),
        p_by_excitation={
            "horn": np.array(horn_field, dtype=np.complex128, copy=True),
            "woofer": np.array(woofer_field, dtype=np.complex128, copy=True),
        },
        excitation_bases={"horn": _basis(per_inputs[0]), "woofer": _basis(per_inputs[1])},
        p_total=None,
        magnitude_screen=None,
        observation_directions=None,
        observation_angles_deg=None,
        fidelity=fidelity,
    )


def _channel(excitation: str, from_per_input: str, *,
             factors=HORN_FACTOR, freqs=FREQS,
             method: str = "loaded_electroacoustic_model") -> cal.ChannelCalibration:
    return cal.ChannelCalibration(
        excitation=excitation,
        from_per_input=from_per_input,
        to_per_input="V_rms",
        frequencies_hz=tuple(freqs),
        factor_re=tuple(complex(f).real for f in factors),
        factor_im=tuple(complex(f).imag for f in factors),
        method=method,
        evidence_path=f"synthetic/{excitation}_transfer.csv",
    )


def _record(*, horn_method: str = "loaded_electroacoustic_model",
            woofer_method: str = "loaded_electroacoustic_model",
            scope=(CASE,), channels=None) -> cal.CalibrationRecord:
    if channels is None:
        channels = (
            _channel("horn", "normal_velocity_mps", factors=HORN_FACTOR, method=horn_method),
            _channel("woofer", "V_rms", factors=WOOFER_FACTOR, method=woofer_method),
        )
    return cal.new_record(
        created_utc=CREATED,
        approved_by="owner",
        scope=scope,
        channels=channels,
        notes="synthetic test record; contains no real calibration values",
    )


# --------------------------------------------------------------------------- record identity

def test_record_round_trip_is_deterministic_and_id_is_domain_hashed() -> None:
    record = _record()
    payload = record.to_dict()
    assert list(payload) == sorted(payload)                     # sorted keys
    assert json.loads(json.dumps(payload)) == payload           # JSON-safe (tuples -> lists)
    assert payload["schema"] == cal.CAL_SCHEMA
    assert payload["record_id"] == record.record_id == _record().record_id
    assert len(record.record_id) == 16

    without_id = {k: v for k, v in payload.items() if k != "record_id"}
    assert record.record_id == C.domain_sha16("system.calibration", without_id)
    assert cal.CalibrationRecord.from_dict(payload) == record
    assert cal.CalibrationRecord.from_dict(json.loads(json.dumps(payload))) == record

    other = _record(horn_method="unloaded_driver_model")
    assert other.record_id != record.record_id


def test_from_dict_rejects_a_hand_picked_id() -> None:
    payload = _record().to_dict()
    payload["record_id"] = "0" * 16
    with pytest.raises(C.SchemaError, match="record_id"):
        cal.CalibrationRecord.from_dict(payload)


# --------------------------------------------------------------------------- fidelity cap

def test_fidelity_cap_uses_the_contracts_ladder_order() -> None:
    assert _record(horn_method="measured_on_horn",
                   woofer_method="measured_on_horn").fidelity_cap() == "MEASURED_VALIDATED"
    assert _record(horn_method="measured_on_horn",
                   woofer_method="loaded_electroacoustic_model"
                   ).fidelity_cap() == "COUPLED_VENTED_FEM_BEM_LEM"
    assert _record(horn_method="loaded_electroacoustic_model",
                   woofer_method="unloaded_driver_model"
                   ).fidelity_cap() == "SCREEN_COMPLEX_APPROX"
    assert _record(horn_method="assumed_ideal",
                   woofer_method="measured_on_horn").fidelity_cap() == "SCREEN_COMPLEX_APPROX"


# --------------------------------------------------------------------------- apply success

def test_apply_calibration_multiplies_fields_and_keeps_the_shared_frame() -> None:
    response = _response()
    out = cal.apply_calibration(response, _record(), case_key=CASE)

    np.testing.assert_allclose(
        out.p_by_excitation["horn"], HORN_FIELD * np.array(HORN_FACTOR)[:, None],
        rtol=0.0, atol=0.0)
    np.testing.assert_allclose(
        out.p_by_excitation["woofer"], WOOFER_FIELD * np.array(WOOFER_FACTOR)[:, None],
        rtol=0.0, atol=0.0)
    assert {b.per_input for b in out.excitation_bases.values()} == {"V_rms"}
    # Everything but the unit declaration is preserved (distance/origin/frame/hash untouched).
    for name in ("horn", "woofer"):
        before, after = response.excitation_bases[name], out.excitation_bases[name]
        assert after.distance_m == before.distance_m
        assert after.origin_xyz_m == before.origin_xyz_m
        assert after.angular_frame == before.angular_frame
        assert after.source_geometry_hash == before.source_geometry_hash
    okay, _ = out.excitation_bases["horn"].compatible_for_sum_with(
        out.excitation_bases["woofer"])
    assert okay
    # The input response is not mutated.
    np.testing.assert_array_equal(response.p_by_excitation["horn"], HORN_FIELD)
    assert response.excitation_bases["horn"].per_input == "normal_velocity_mps"


def test_apply_calibration_caps_fidelity_at_the_method_cap() -> None:
    response = _response(fidelity="INSTALLED_EXTERIOR_BEM")
    loaded = cal.apply_calibration(response, _record(), case_key=CASE)
    assert loaded.fidelity == "INSTALLED_EXTERIOR_BEM"   # cap COUPLED is above INSTALLED

    unloaded = cal.apply_calibration(
        response, _record(horn_method="unloaded_driver_model",
                          woofer_method="unloaded_driver_model"), case_key=CASE)
    assert unloaded.fidelity == "SCREEN_COMPLEX_APPROX"

    measured = cal.apply_calibration(
        response, _record(horn_method="measured_on_horn",
                          woofer_method="measured_on_horn"), case_key=CASE)
    assert measured.fidelity == "INSTALLED_EXTERIOR_BEM"


# --------------------------------------------------------------------------- combine

def test_combine_without_calibration_refuses_mixed_references_identically() -> None:
    response = _response()
    expected = ("cannot coherently sum 'horn' and 'woofer': "
                "per_input 'normal_velocity_mps' vs 'V_rms'")
    with pytest.raises(C.IncompatibleBasis) as old_call:
        comb.combine(response, BANK, LEVELS)
    assert str(old_call.value) == expected

    with pytest.raises(C.IncompatibleBasis) as new_call:
        comb.combine(response, BANK, LEVELS, calibration=None, case_key=CASE)
    assert type(new_call.value) is type(old_call.value)
    assert str(new_call.value) == str(old_call.value) == expected


def test_combine_none_path_is_byte_identical_for_a_summable_response() -> None:
    response = _response(per_inputs=("V_rms", "V_rms"))
    bank = {"horn": np.array([1.0, 0.5, 2.0]), "woofer": np.array([1.0, -1.0, 0.5])}
    before = comb.combine(response, bank, LEVELS)
    after = comb.combine(response, bank, LEVELS, calibration=None, case_key="ignored/case")
    np.testing.assert_array_equal(before.p_total, after.p_total)
    assert before.fidelity == after.fidelity
    for name in ("horn", "woofer"):
        np.testing.assert_array_equal(before.p_by_excitation[name],
                                      after.p_by_excitation[name])
        assert before.excitation_bases[name] == after.excitation_bases[name]


def test_combine_with_record_applies_calibration_then_sums() -> None:
    response = _response()
    out = comb.combine(response, BANK, LEVELS, calibration=_record(), case_key=CASE)
    manual = (HORN_FIELD * np.array(HORN_FACTOR)[:, None]
              + WOOFER_FIELD * np.array(WOOFER_FACTOR)[:, None])
    np.testing.assert_allclose(out.p_total, manual, rtol=0.0, atol=0.0)
    assert out.fidelity == "INSTALLED_EXTERIOR_BEM"
    assert {b.per_input for b in out.excitation_bases.values()} == {"V_rms"}


def test_combine_with_unloaded_record_caps_the_summed_fidelity() -> None:
    response = _response(fidelity="INSTALLED_EXTERIOR_BEM")
    out = comb.combine(
        response, BANK, LEVELS, case_key=CASE,
        calibration=_record(horn_method="unloaded_driver_model",
                            woofer_method="unloaded_driver_model"))
    assert out.fidelity == "SCREEN_COMPLEX_APPROX"


def test_combine_wildcard_scope_is_accepted() -> None:
    out = comb.combine(_response(), BANK, LEVELS,
                       calibration=_record(scope=("*",)), case_key=CASE)
    assert out.p_total is not None


def test_combine_with_calibration_requires_a_case_key() -> None:
    with pytest.raises(cal.CalibrationError) as exc:
        comb.combine(_response(), BANK, LEVELS, calibration=_record())
    assert exc.value.token == "CAL_SCOPE_MISMATCH"


# --------------------------------------------------------------------------- refusal tokens

def test_cal_scope_mismatch() -> None:
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(), _record(scope=("other/case",)), case_key=CASE)
    assert exc.value.token == "CAL_SCOPE_MISMATCH"
    assert "CAL_SCOPE_MISMATCH" in str(exc.value)


def test_cal_channel_missing_for_response_excitation() -> None:
    partial = _record(channels=(_channel("horn", "normal_velocity_mps"),))
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(), partial, case_key=CASE)
    assert exc.value.token == "CAL_CHANNEL_MISSING"


def test_cal_channel_missing_for_extra_record_channel() -> None:
    extra = _record(channels=(
        _channel("horn", "normal_velocity_mps"),
        _channel("woofer", "V_rms", factors=WOOFER_FACTOR),
        _channel("mid", "V_rms", factors=WOOFER_FACTOR),
    ))
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(), extra, case_key=CASE)
    assert exc.value.token == "CAL_CHANNEL_MISSING"


def test_cal_unit_mismatch() -> None:
    wrong_unit = _record(channels=(
        _channel("horn", "V_rms"),                       # basis is normal_velocity_mps
        _channel("woofer", "V_rms", factors=WOOFER_FACTOR),
    ))
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(), wrong_unit, case_key=CASE)
    assert exc.value.token == "CAL_UNIT_MISMATCH"
    assert "normal_velocity_mps" in exc.value.detail


def test_cal_freq_grid_mismatch() -> None:
    off_grid = _record(channels=(
        _channel("horn", "normal_velocity_mps", freqs=(500.0, 1000.0, 2001.0)),
        _channel("woofer", "V_rms", factors=WOOFER_FACTOR),
    ))
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(), off_grid, case_key=CASE)
    assert exc.value.token == "CAL_FREQ_GRID_MISMATCH"


def test_cal_freq_grid_mismatch_on_length() -> None:
    short = _record(channels=(
        _channel("horn", "normal_velocity_mps", factors=HORN_FACTOR[:2],
                 freqs=FREQS[:2]),
        _channel("woofer", "V_rms", factors=WOOFER_FACTOR),
    ))
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(), short, case_key=CASE)
    assert exc.value.token == "CAL_FREQ_GRID_MISMATCH"


def test_cal_nonfinite_response_field() -> None:
    nan_field = np.array(HORN_FIELD, dtype=np.complex128)
    nan_field[1, 0] = np.nan + 0.0j
    with pytest.raises(cal.CalibrationError) as exc:
        cal.apply_calibration(_response(horn_field=nan_field), _record(), case_key=CASE)
    assert exc.value.token == "CAL_NONFINITE"


def test_cal_nonfinite_factor_is_refused_at_construction() -> None:
    with pytest.raises(cal.CalibrationError) as exc:
        cal.ChannelCalibration(
            excitation="horn", from_per_input="normal_velocity_mps", to_per_input="V_rms",
            frequencies_hz=FREQS, factor_re=(0.5, float("nan"), 0.4),
            factor_im=(0.0, 0.0, 0.0), method="loaded_electroacoustic_model",
            evidence_path="synthetic/x.csv")
    assert exc.value.token == "CAL_NONFINITE"


def test_undeclared_token_is_an_assertion_not_a_silent_refusal() -> None:
    with pytest.raises(AssertionError):
        cal.CalibrationError("CAL_MADE_UP", "not a contract token")
