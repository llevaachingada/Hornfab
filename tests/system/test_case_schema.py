"""Offline tests for :mod:`hornlab_search.system.case_schema` (contract section 2)."""
from __future__ import annotations

import dataclasses
import json

import pytest

from hornlab_search.system.case_schema import (
    CASE_SCHEMA,
    CaseHeader,
    ClearanceBlock,
    Declaration,
    GeometryBlock,
    SolveBlock,
    StageBlock,
    SystemCase,
)


def _case() -> SystemCase:
    return SystemCase(
        header=CaseHeader(
            case_key="exp/20261118T225108Z-case",
            experiment="exp",
            case="20261118T225108Z-case",
            kind="bl_stage_reference_project",
            created_utc="2026-11-18T23:23:06+00:00",
            status="solved",
            status_reason="RUN_COMPLETE",
            manifest_integrity="verified",
            source_path="system/exp/20261118T225108Z-case",
        ),
        declaration=Declaration(
            declared=True,
            fidelity="COUPLED_VENTED_FEM_BEM_LEM",
            motor="demo",
            motor_source="readiness",
            transducer_shape="demo",
            gate="G4",
            ref="#1",
            evidence="EVIDENCE.md section 1",
            horn_source="ideal_velocity",
            pair_with="exp/other",
        ),
        stage=StageBlock(
            ok=True,
            error=None,
            project_rel="system/exp/20261118T225108Z-case/case.blab.json",
            clearance=ClearanceBlock(status="pass", min_gap_mm=3.0, source="stage_report.json"),
        ),
        solve=SolveBlock(
            run_status="complete",
            n_frequencies=3,
            freq_min_hz=250.0,
            freq_max_hz=1100.0,
            backend_id="beat_cpu",
            solve_kind="coupled_bem_fem",
            completion_done=3,
            completion_total=3,
            authorized_by=None,
            run_manifest_integrity="verified",
        ),
        geometry=GeometryBlock(
            box_mm=(371.2, 500.0, 360.0),
            net_volume_l=115.0,
            net_volume_source="declared",
            port_area_cm2=45.0,
            tuning_hz=30.0,
            horn_mesh="lecleach_rollback_1in_v6_9e02db06ecc3",
            horn_mesh_sha256="9b4057c2",
            horn_offset_mm_xyz=(0.0, 0.0, 10.0),
            driver_name="FaitalPRO 12PR300",
        ),
        refusals=(),
        diagnostics=("a diagnostic",),
        sources=("system/exp/case/manifest.json", "system/exp/case/request.json"),
    )


def test_schema_version_is_frozen_contract_value():
    assert CASE_SCHEMA == "hornlab.system.case.v1"


def test_to_dict_is_json_safe_sorted_and_tuples_are_lists():
    data = _case().to_dict()
    assert list(data) == sorted(data)
    assert list(data["header"]) == sorted(data["header"])
    assert list(data["geometry"]) == sorted(data["geometry"])
    assert data["geometry"]["box_mm"] == [371.2, 500.0, 360.0]
    assert data["geometry"]["horn_offset_mm_xyz"] == [0.0, 0.0, 10.0]
    assert data["refusals"] == []
    assert isinstance(data["sources"], list)
    # nothing left that json cannot encode
    assert json.loads(json.dumps(data, sort_keys=True, allow_nan=False)) == data


def test_to_dict_is_byte_deterministic():
    first = json.dumps(_case().to_dict(), sort_keys=True, separators=(",", ":"))
    second = json.dumps(_case().to_dict(), sort_keys=True, separators=(",", ":"))
    assert first == second


def test_nested_blocks_serialise_with_sorted_keys():
    stage = _case().stage.to_dict()
    assert list(stage) == sorted(stage)
    assert list(stage["clearance"]) == sorted(stage["clearance"])
    assert stage["clearance"]["min_gap_mm"] == 3.0


def test_dataclasses_are_frozen():
    case = _case()
    with pytest.raises(dataclasses.FrozenInstanceError):
        case.header = None  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        case.geometry.box_mm = (1.0, 2.0, 3.0)  # type: ignore[misc]
