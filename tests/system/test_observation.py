"""Offline tests for the observation-standard schema and label helper (contract section 5)."""
from __future__ import annotations

import json

import pytest

from hornlab_search.system.contracts import SourceBasis
from hornlab_search.system.observation import (
    NEAR_FIELD_LABEL,
    OBSERVATION_ID_DOMAIN,
    ObservationError,
    ObservationStandard,
    label_for,
)
from hornlab_search.system.contracts import domain_sha16

PAYLOAD = {
    "distance_m": 2.0,
    "angular_frame": "hornfab_cuts_hv",
    "h_angles_deg": [-30.0, 0.0, 30.0],
    "v_angles_deg": [-10.0, 0.0, 10.0],
    "listening_window": [[-15.0, 15.0], [-5.0, 5.0]],
    "far_field_claimed": False,
    "approved_by": None,
}


def _standard(**overrides) -> ObservationStandard:
    payload = dict(PAYLOAD)
    payload.update(overrides)
    return ObservationStandard.from_dict(payload)


def test_identity_and_round_trip() -> None:
    standard = _standard()
    assert standard.standard_id == domain_sha16(OBSERVATION_ID_DOMAIN, standard.payload())
    assert list(standard.to_dict()) == sorted(standard.to_dict())
    assert json.loads(json.dumps(standard.to_dict())) == standard.to_dict()
    assert ObservationStandard.from_dict(standard.to_dict()) == standard


def test_label_is_the_contract_fallback_without_a_far_field_claim() -> None:
    basis = SourceBasis(per_input="V_rms", distance_m=2.0)
    assert label_for(basis, None) == NEAR_FIELD_LABEL
    assert label_for(basis, _standard(far_field_claimed=False)) == NEAR_FIELD_LABEL
    assert NEAR_FIELD_LABEL == "near-field cuts (undeclared standard)"


def test_declared_far_field_label_carries_distance_and_frame() -> None:
    standard = _standard(far_field_claimed=True, approved_by="owner")
    label = label_for(SourceBasis(per_input="V_rms", distance_m=2.0), standard)
    assert label == "far-field 2 m (hornfab_cuts_hv)"
    assert "far-field" in label


def test_validation_rejects_bad_geometry_and_windows() -> None:
    with pytest.raises(ObservationError) as exc:
        _standard(distance_m=0.0)
    assert exc.value.token == "OBSERVATION_INVALID"
    with pytest.raises(ObservationError) as exc:
        _standard(angular_frame="  ")
    assert exc.value.token == "OBSERVATION_INVALID"
    with pytest.raises(ObservationError) as exc:
        _standard(h_angles_deg=(0.0, float("nan")))
    assert exc.value.token == "OBSERVATION_INVALID"
    with pytest.raises(ObservationError) as exc:
        _standard(listening_window=[[15.0, -15.0]])
    assert exc.value.token == "OBSERVATION_INVALID"
    with pytest.raises(ObservationError) as exc:
        _standard(listening_window=[[1.0, 2.0, 3.0]])
    assert exc.value.token == "OBSERVATION_INVALID"
    with pytest.raises(ObservationError) as exc:
        _standard(far_field_claimed="yes")
    assert exc.value.token == "OBSERVATION_INVALID"
    with pytest.raises(ObservationError) as exc:
        _standard(approved_by="")
    assert exc.value.token == "OBSERVATION_INVALID"


def test_missing_optional_angle_grids_are_empty_not_inferred() -> None:
    standard = ObservationStandard.from_dict({
        "distance_m": 1.0,
        "angular_frame": "cartesian_dirs",
        "far_field_claimed": False,
        "approved_by": None,
    })
    assert standard.h_angles_deg == ()
    assert standard.v_angles_deg == ()
    assert standard.listening_window is None
    assert label_for(SourceBasis(per_input="V_rms"), standard) == NEAR_FIELD_LABEL
