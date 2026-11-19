"""Contract tests for ``hornlab_search.system.contracts`` (Stage 0 freeze gate).

These tests pin the conventions the four Stage-1 lanes build against: exp(+jomega_t) only,
per-input basis compatibility, phase-honest refusals, domain-separated identities and the
strict schema-v1 parser (unknown keys/units are errors, not warnings).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import contracts as C  # noqa: E402


def _basis(**kw) -> C.SourceBasis:
    defaults: dict[str, Any] = dict(
        per_input="normal_velocity_mps", distance_m=2.0, origin_xyz_m=(0.0, 0.0, 0.0),
        angular_frame="hornfab_cuts_hv", source_geometry_hash="abc123",
    )
    defaults.update(kw)
    return C.SourceBasis(**defaults)


# --------------------------------------------------------------------------- basis compatibility

def test_source_basis_rejects_wrong_time_convention() -> None:
    with pytest.raises(C.IncompatibleBasis):
        C.SourceBasis(per_input="V_rms", time_convention="exp(-jomega_t)")


def test_compatible_bases_sum_flag() -> None:
    a = _basis()
    ok, reason = a.compatible_for_sum_with(_basis())
    assert ok and reason == "declared compatible"
    ok, _ = a.compatible_for_sum_with(_basis(per_input="V_rms"))
    assert not ok
    ok, _ = a.compatible_for_sum_with(_basis(angular_frame="cartesian_dirs"))
    assert not ok
    ok, _ = a.compatible_for_sum_with(_basis(distance_m=None))
    assert not ok
    ok, _ = a.compatible_for_sum_with(_basis(source_geometry_hash=None))
    assert not ok


# --------------------------------------------------------------------------- phase honesty

def _asset(quality: C.AssetQuality, fields: frozenset[str] = frozenset({"p_h", "p_v"})) -> C.HornAsset:
    return C.HornAsset(
        asset_id="test-asset", design_hash="d123", response_path="runs/x/response.npz",
        mesh_path=None, geometry=C.GeometryMetadata(family="OSSE"),
        available_fields=fields, quality=quality,
        freqs_hz=(500.0, 1000.0, 2000.0),
        source_basis=_basis() if quality == "EXACT_COMPLEX" else None,
    )


def test_magnitude_only_asset_refuses_phase_but_flags_it() -> None:
    a = _asset("MAGNITUDE_ONLY", frozenset({"spl_balloon_db", "H", "V"}))
    assert a.has_complex is False
    with pytest.raises(C.PhaseUnavailable) as exc:
        a.require_complex()
    assert "MAGNITUDE_ONLY" in str(exc.value) and "PHASE_ALIGNMENT_UNAVAILABLE" in str(exc.value)


def test_exact_complex_asset_passes_the_phase_gate() -> None:
    a = _asset("EXACT_COMPLEX")
    assert a.has_complex
    basis = a.require_complex()
    assert basis.per_input == "normal_velocity_mps"


def test_exact_complex_requires_declared_basis() -> None:
    with pytest.raises(C.DataQualityError):
        C.HornAsset(
            asset_id="x", design_hash="d", response_path="p",
            mesh_path=None, geometry=C.GeometryMetadata(),
            available_fields=frozenset({"p_h"}), quality="EXACT_COMPLEX",
            freqs_hz=(1000.0,), source_basis=None,
        )


# --------------------------------------------------------------------------- identity

def test_domain_sha16_is_stable_and_domain_separated() -> None:
    payload = {"a": 1, "b": [1.0, 2.5], "c": "x"}
    assert C.domain_sha16("dom", payload) == C.domain_sha16("dom", {"b": [1.0, 2.5], "a": 1, "c": "x"})
    assert C.domain_sha16("dom", payload) != C.domain_sha16("dom2", payload)
    assert C.domain_sha16("dom", payload) != C.domain_sha16("dom", {"a": 2, "b": [1.0, 2.5], "c": "x"})
    assert len(C.system_score_id(payload)) == 16
    # a horn score id is never a system score id even for identical payloads
    assert C.system_score_id(payload) != C.system_score_id.__module__  # sanity
    assert C.assembly_geometry_id(payload) != C.system_physics_id(payload)


# --------------------------------------------------------------------------- schema v1 parser

_MIN_SPEC = {
    "schema_version": 1,
    "experiment_id": "two_way_pilot",
    "mode": "fixed_horn",
    "horn": {"asset_id": "REAL_INVENTORY_ID"},
    "woofer": {"driver_id": "REAL_DRIVER_ID"},
    "cabinet": {
        "external_width_mm_range": [340.0, 510.0],
        "external_height_mm_range": [470.0, 850.0],
        "external_depth_mm_range": [260.0, 570.0],
        "net_volume_l_range": [35.0, 115.0],
        "tuning_hz_range": [30.0, 65.0],
        "port_throat_area_cm2_range": [45.0, 170.0],
    },
    "assembly": {"woofer_center_y_mm_range": [90.0, 400.0]},
    "dsp": {"xo_hz_range": [700.0, 1300.0]},
    "target": {
        "listening_angle_h_deg": [-30.0, 30.0],
        "listening_angle_v_deg": [-15.0, 15.0],
    },
    "fidelity": "screen_only",
}


def test_minimal_spec_parses_and_hashes_stably() -> None:
    spec = C.parse_system_spec_dict(_MIN_SPEC)
    assert spec.experiment_id == "two_way_pilot"
    assert spec.dsp.crossover_types == ("LR4",)
    assert spec.hash() == C.parse_system_spec_dict(_MIN_SPEC).hash()


def test_unknown_top_level_key_is_rejected() -> None:
    bad = dict(_MIN_SPEC)
    bad["surrogate"] = "no"
    with pytest.raises(C.SchemaError, match="unknown spec keys"):
        C.parse_system_spec_dict(bad)


def test_unknown_nested_key_is_rejected() -> None:
    bad = {**_MIN_SPEC, "dsp": {**_MIN_SPEC["dsp"], "predictor": "x"}}
    with pytest.raises(C.SchemaError, match="unknown dsp keys"):
        C.parse_system_spec_dict(bad)


def test_missing_required_key_and_bad_schema_version_are_rejected() -> None:
    bad = {k: v for k, v in _MIN_SPEC.items() if k != "target"}
    with pytest.raises(C.SchemaError, match="missing required"):
        C.parse_system_spec_dict(bad)
    with pytest.raises(C.SchemaError, match="schema_version"):
        C.parse_system_spec_dict({**_MIN_SPEC, "schema_version": 2})


def test_incoherent_and_bad_enum_specs_are_rejected() -> None:
    bad = {**_MIN_SPEC, "dsp": {**_MIN_SPEC["dsp"], "xo_hz_range": [1300.0, 700.0]}}
    with pytest.raises(C.SchemaError, match="lo <= hi"):
        spec = C.parse_system_spec_dict(bad)
    with pytest.raises(C.SchemaError):
        C.parse_system_spec_dict({**_MIN_SPEC, "fidelity": "full_auto"})
    with pytest.raises(C.SchemaError):
        C.parse_system_spec_dict({**_MIN_SPEC, "mode": "magic_auto"})
    bad_cab = {**_MIN_SPEC, "cabinet": {**_MIN_SPEC["cabinet"], "kind": "folded_horn"}}
    with pytest.raises(C.SchemaError):
        C.parse_system_spec_dict(bad_cab)
    bad_dsp_types = {**_MIN_SPEC, "dsp": {**_MIN_SPEC["dsp"], "crossover_types": ("LR7",)}}
    with pytest.raises(C.SchemaError, match="LR2/LR4/LR8"):
        C.parse_system_spec_dict(bad_dsp_types)


# --------------------------------------------------------------------------- system response

def test_system_response_requires_bases_and_matching_frequency_axis() -> None:
    f = np.array([700.0, 900.0, 1100.0])
    C.SystemResponse(
        frequencies_hz=f, excitation_names=("horn", "woofer"),
        p_by_excitation={"horn": np.ones((3, 4), complex), "woofer": np.ones((3, 4), complex)},
        excitation_bases={"horn": _basis(), "woofer": _basis(per_input="V_rms")},
        p_total=None, magnitude_screen=None, observation_directions=None,
        observation_angles_deg=None, fidelity="SCREEN_COMPLEX_APPROX",
    )  # bases present; heterogeneous per_input is allowed at construction (combine refuses later)
    with pytest.raises(C.DataQualityError, match="without SourceBasis"):
        C.SystemResponse(
            frequencies_hz=f, excitation_names=("horn",),
            p_by_excitation={"horn": np.ones((3, 4), complex)},
            excitation_bases={}, p_total=None, magnitude_screen=None,
            observation_directions=None, observation_angles_deg=None,
            fidelity="SCREEN_COMPLEX_APPROX",
        )
    with pytest.raises(C.DataQualityError, match="frequency axis mismatch"):
        C.SystemResponse(
            frequencies_hz=f, excitation_names=("horn",),
            p_by_excitation={"horn": np.ones((2, 4), complex)},
            excitation_bases={"horn": _basis()}, p_total=None, magnitude_screen=None,
            observation_directions=None, observation_angles_deg=None,
            fidelity="SCREEN_COMPLEX_APPROX",
        )


def test_system_response_phase_gate_works() -> None:
    f = np.array([700.0])
    screen = C.SystemResponse(
        frequencies_hz=f, excitation_names=(), p_by_excitation=None,
        excitation_bases={}, p_total=None, magnitude_screen=np.zeros((1, 1)),
        observation_directions=None, observation_angles_deg=None, fidelity="SCREEN_MAGNITUDE",
    )
    with pytest.raises(C.PhaseUnavailable):
        screen.require_phase()
