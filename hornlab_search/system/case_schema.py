"""Typed system case schema (contract ``01_CONTRACTS.md`` section 2).

The schema is a pure data model: frozen dataclasses, JSON-safe ``to_dict()`` with sorted keys
and tuples converted to lists.  It has no filesystem, solver or GUI imports; :mod:`read_case`
builds it from a case directory.

Field order in each dataclass is the contract's order; ``to_dict()`` sorts keys, so the JSON
representation is deterministic and independent of construction order.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "CASE_SCHEMA",
    "CaseStatus",
    "CaseSchemaError",
    "CaseHeader",
    "ClearanceBlock",
    "StageBlock",
    "SolveBlock",
    "GeometryBlock",
    "Declaration",
    "SystemCase",
]

CASE_SCHEMA = "hornlab.system.case.v1"

CaseStatus = Literal["solved", "staged", "refused", "invalid"]

UNDECLARED = "UNDECLARED"


class CaseSchemaError(ValueError):
    """A schema error carrying a stable UPPER_SNAKE ``token`` and a human ``detail``."""

    def __init__(self, token: str, detail: str = "") -> None:
        super().__init__(f"{token}: {detail}" if detail else token)
        self.token = token
        self.detail = detail


def _jsonable(value: Any) -> Any:
    """JSON-safe recursively: dataclasses -> dicts, tuples -> lists, sorted keys, no NaN."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in sorted(dataclasses.fields(value), key=lambda item: item.name)
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


@dataclass(frozen=True, slots=True)
class CaseHeader:
    case_key: str
    experiment: str
    case: str
    kind: str | None
    created_utc: str | None
    status: CaseStatus
    status_reason: str
    manifest_integrity: Literal["verified", "mismatch", "unknown"]
    source_path: str

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class ClearanceBlock:
    status: Literal["pass", "violation", "unproven", "not_recorded"]
    min_gap_mm: float | None
    source: str

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class StageBlock:
    ok: bool | None
    error: str | None
    project_rel: str | None
    clearance: ClearanceBlock | None

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class SolveBlock:
    run_status: str | None
    n_frequencies: int | None
    freq_min_hz: float | None
    freq_max_hz: float | None
    backend_id: str | None
    solve_kind: str | None
    completion_done: int | None
    completion_total: int | None
    authorized_by: str | None
    run_manifest_integrity: str

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class GeometryBlock:
    box_mm: tuple[float | None, float | None, float | None]
    net_volume_l: float | None
    net_volume_source: str | None
    port_area_cm2: float | None
    tuning_hz: float | None
    horn_mesh: str | None
    horn_mesh_sha256: str | None
    horn_offset_mm_xyz: tuple[float, float, float] | None
    driver_name: str | None

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class Declaration:
    declared: bool
    fidelity: str
    motor: str
    motor_source: str | None
    transducer_shape: str
    gate: str | None
    ref: str | None
    evidence: str | None
    horn_source: str | None
    pair_with: str | None

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class SystemCase:
    header: CaseHeader
    declaration: Declaration
    stage: StageBlock | None
    solve: SolveBlock | None
    geometry: GeometryBlock | None
    refusals: tuple[str, ...]
    diagnostics: tuple[str, ...]
    sources: tuple[str, ...]

    def to_dict(self) -> dict:
        return _jsonable(self)
