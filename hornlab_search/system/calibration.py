"""Per-channel calibration records for the two-way system (contract v1, §3).

A ``SystemResponse`` stores each excitation field per its declared
:class:`~hornlab_search.system.contracts.SourceBasis.per_input`
(``"V_rms"`` or ``"normal_velocity_mps"``). A coherent sum needs one shared reference, so this
module applies an explicit, approved :class:`CalibrationRecord` that brings every channel to
Pa per ``V_rms``. Nothing is inferred: without a record the fields keep their declared basis and
:func:`hornlab_search.system.combine.combine` refuses a mixed-reference sum exactly as before.

The record is deliberately *more* restrictive than the old free-text route:

* no interpolation in v1 — the record's frequency grid must match the response grid to 1e-9
  relative, else ``CAL_FREQ_GRID_MISMATCH``;
* a channel is required for **every** response excitation and vice versa
  (``CAL_CHANNEL_MISSING``);
* the channel's ``from_per_input`` must equal the basis's ``per_input`` (``CAL_UNIT_MISMATCH``);
* the record's ``scope`` must cover the requested ``case_key`` (``CAL_SCOPE_MISMATCH``);
* non-finite factors or fields are refused (``CAL_NONFINITE``).

Fidelity is capped by the calibration method: a transfer derived from an unloaded driver model
can never make the summed response better than ``SCREEN_COMPLEX_APPROX`` (finding N2). The ladder
order is read from :class:`~hornlab_search.system.contracts.Fidelity` — never redefined here.

Pure module: no file IO, no globals mutated, deterministic ids via
:func:`~hornlab_search.system.contracts.domain_sha16`.
"""
from __future__ import annotations

import datetime as _dt
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, Mapping, get_args

import numpy as np

from hornlab_search.system import contracts

__all__ = [
    "CAL_SCHEMA", "CALIBRATION_TOKENS", "CalMethod", "METHOD_FIDELITY_CAP",
    "CalibrationError", "ChannelCalibration", "CalibrationRecord",
    "apply_calibration", "new_record",
]

#: Schema id written into ``to_dict()`` payloads.
CAL_SCHEMA = "hornlab.system.calibration.v1"
#: Domain for :func:`contracts.domain_sha16` (contract §3).
_ID_DOMAIN = "system.calibration"

CalMethod = Literal[
    "measured_on_horn",
    "loaded_electroacoustic_model",
    "unloaded_driver_model",
    "assumed_ideal",
]

#: The summed response's fidelity can never exceed this cap for a given method.
METHOD_FIDELITY_CAP: Mapping[str, str] = {
    "measured_on_horn": "MEASURED_VALIDATED",
    "loaded_electroacoustic_model": "COUPLED_VENTED_FEM_BEM_LEM",
    "unloaded_driver_model": "SCREEN_COMPLEX_APPROX",
    "assumed_ideal": "SCREEN_COMPLEX_APPROX",
}

#: Declared refusal tokens (contract §3). ``CalibrationError.token`` is always one of these.
CALIBRATION_TOKENS: tuple[str, ...] = (
    "CAL_SCOPE_MISMATCH",
    "CAL_FREQ_GRID_MISMATCH",
    "CAL_CHANNEL_MISSING",
    "CAL_UNIT_MISMATCH",
    "CAL_NONFINITE",
)

#: The frozen fidelity ladder, read from ``contracts.Fidelity`` (not redefined here).
_FIDELITY_LADDER: tuple[str, ...] = tuple(get_args(contracts.Fidelity))

_RECORD_KEYS = frozenset({
    "approved_by", "channels", "created_utc", "notes", "record_id", "schema", "scope",
})
_CHANNEL_KEYS = frozenset({
    "evidence_path", "excitation", "factor_im", "factor_re", "frequencies_hz",
    "from_per_input", "method", "to_per_input",
})
_ID_RE = re.compile(r"[0-9a-f]{16}")


class CalibrationError(ValueError):
    """A calibration record or application refused with a declared token."""

    def __init__(self, token: str, detail: str) -> None:
        if token not in CALIBRATION_TOKENS:
            raise AssertionError(f"undeclared calibration token {token!r}")
        self.token = token
        self.detail = detail
        super().__init__(f"{token}: {detail}")


def _error(token: str, detail: str) -> CalibrationError:
    return CalibrationError(token, detail)


# --------------------------------------------------------------------------- helpers

def _finite_tuple(name: str, value: Any) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise contracts.SchemaError(f"{name} must be a list of numbers, got {value!r}")
    out: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise contracts.SchemaError(f"{name} must contain numbers, got {item!r}")
        out.append(float(item))
    return tuple(out)


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise contracts.SchemaError(f"{what} must be a mapping, got {type(value).__name__}")
    return value


def _check_keys(d: Mapping[str, Any], allowed: frozenset[str], required: frozenset[str],
                what: str) -> None:
    unknown = set(d) - allowed
    if unknown:
        raise contracts.SchemaError(f"unknown {what} keys: {sorted(unknown)}")
    missing = required - set(d)
    if missing:
        raise contracts.SchemaError(f"missing required {what} keys: {sorted(missing)}")


def _grid_matches(record_grid: Sequence[float], response_grid: Any) -> bool:
    """No interpolation in v1: equal length and 1e-9 relative agreement per point."""
    try:
        response = tuple(float(x) for x in np.asarray(response_grid, dtype=np.float64).reshape(-1))
    except (TypeError, ValueError):
        return False
    if len(record_grid) != len(response):
        return False
    return all(math.isclose(float(a), b, rel_tol=1e-9, abs_tol=0.0)
               for a, b in zip(record_grid, response))


def _min_fidelity(left: str, right: str) -> str:
    """The lower (more conservative) of two ladder labels."""
    if left not in _FIDELITY_LADDER or right not in _FIDELITY_LADDER:
        raise contracts.SchemaError(
            f"fidelity labels must be on the contracts ladder, got {left!r}, {right!r}")
    return left if _FIDELITY_LADDER.index(left) <= _FIDELITY_LADDER.index(right) else right


# --------------------------------------------------------------------------- channel

@dataclass(frozen=True, slots=True)
class ChannelCalibration:
    """One excitation's complex Pa-per-``V_rms`` multiplier on an explicit frequency grid."""

    excitation: str
    from_per_input: Literal["V_rms", "normal_velocity_mps"]
    to_per_input: Literal["V_rms"]
    frequencies_hz: tuple[float, ...]
    factor_re: tuple[float, ...]
    factor_im: tuple[float, ...]
    method: CalMethod
    evidence_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.excitation, str) or not self.excitation.strip():
            raise contracts.SchemaError(
                f"channel excitation must be a non-empty string, got {self.excitation!r}")
        if self.from_per_input not in ("V_rms", "normal_velocity_mps"):
            raise _error("CAL_UNIT_MISMATCH",
                         f"channel {self.excitation!r}: unknown from_per_input "
                         f"{self.from_per_input!r}")
        if self.to_per_input != "V_rms":
            raise _error("CAL_UNIT_MISMATCH",
                         f"channel {self.excitation!r}: v1 calibration targets 'V_rms', got "
                         f"{self.to_per_input!r}")
        if self.method not in METHOD_FIDELITY_CAP:
            raise contracts.SchemaError(
                f"channel {self.excitation!r}: unknown method {self.method!r}")
        if not isinstance(self.evidence_path, str) or not self.evidence_path.strip():
            raise contracts.SchemaError(
                f"channel {self.excitation!r}: evidence_path must be non-empty")
        n = len(self.frequencies_hz)
        if n == 0:
            raise _error("CAL_FREQ_GRID_MISMATCH",
                         f"channel {self.excitation!r}: empty frequency grid")
        if len(self.factor_re) != n or len(self.factor_im) != n:
            raise _error("CAL_FREQ_GRID_MISMATCH",
                         f"channel {self.excitation!r}: factor length "
                         f"({len(self.factor_re)}, {len(self.factor_im)}) != grid length {n}")
        if not all(math.isfinite(f) for f in self.frequencies_hz):
            raise _error("CAL_NONFINITE", f"channel {self.excitation!r}: non-finite frequency")
        for i in range(1, n):
            if not self.frequencies_hz[i] > self.frequencies_hz[i - 1]:
                raise _error("CAL_FREQ_GRID_MISMATCH",
                             f"channel {self.excitation!r}: frequencies must be strictly "
                             f"increasing at index {i}")
        if not all(math.isfinite(x) for x in (*self.factor_re, *self.factor_im)):
            raise _error("CAL_NONFINITE", f"channel {self.excitation!r}: non-finite factor")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_path": self.evidence_path,
            "excitation": self.excitation,
            "factor_im": list(self.factor_im),
            "factor_re": list(self.factor_re),
            "frequencies_hz": list(self.frequencies_hz),
            "from_per_input": self.from_per_input,
            "method": self.method,
            "to_per_input": self.to_per_input,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ChannelCalibration":
        data = _require_mapping(d, "ChannelCalibration")
        _check_keys(data, _CHANNEL_KEYS, _CHANNEL_KEYS, "channel")
        return cls(
            excitation=str(data["excitation"]),
            from_per_input=data["from_per_input"],
            to_per_input=data["to_per_input"],
            frequencies_hz=_finite_tuple("frequencies_hz", data["frequencies_hz"]),
            factor_re=_finite_tuple("factor_re", data["factor_re"]),
            factor_im=_finite_tuple("factor_im", data["factor_im"]),
            method=data["method"],
            evidence_path=str(data["evidence_path"]),
        )


# --------------------------------------------------------------------------- record

@dataclass(frozen=True, slots=True)
class CalibrationRecord:
    """An approved, scoped set of channel calibrations; ``record_id`` is domain-hashed."""

    record_id: str
    created_utc: str
    approved_by: str
    scope: tuple[str, ...]
    channels: tuple[ChannelCalibration, ...]
    notes: str

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not _ID_RE.fullmatch(self.record_id):
            raise contracts.SchemaError(
                f"record_id must be 16 lowercase hex chars, got {self.record_id!r}")
        if not isinstance(self.created_utc, str) or not self.created_utc:
            raise contracts.SchemaError("created_utc must be a non-empty ISO-8601 string")
        try:
            stamp = _dt.datetime.fromisoformat(self.created_utc)
        except ValueError:
            raise contracts.SchemaError(
                f"created_utc is not ISO-8601: {self.created_utc!r}") from None
        if stamp.utcoffset() != _dt.timedelta(0):
            raise contracts.SchemaError(
                f"created_utc must be UTC with +00:00, got {self.created_utc!r}")
        if not isinstance(self.approved_by, str) or not self.approved_by.strip():
            raise contracts.SchemaError("approved_by must be non-empty")
        if not self.scope or not all(isinstance(s, str) and s.strip() for s in self.scope):
            raise contracts.SchemaError("scope must be a non-empty tuple of case keys or ('*',)")
        if not self.channels:
            raise contracts.SchemaError("a calibration record needs at least one channel")
        seen: set[str] = set()
        for channel in self.channels:
            if not isinstance(channel, ChannelCalibration):
                raise contracts.SchemaError(
                    f"channels must be ChannelCalibration, got {type(channel).__name__}")
            if channel.excitation in seen:
                raise contracts.SchemaError(
                    f"duplicate calibration channel for excitation {channel.excitation!r}")
            seen.add(channel.excitation)

    def identity_payload(self) -> dict[str, Any]:
        """The payload hashed into ``record_id`` (``to_dict()`` without the id)."""
        payload = self.to_dict()
        payload.pop("record_id")
        return payload

    def compute_id(self) -> str:
        """The expected id; never hand-picked (contract §3 / conventions)."""
        return contracts.domain_sha16(_ID_DOMAIN, self.identity_payload())

    def fidelity_cap(self) -> str:
        """Lowest (most conservative) channel cap, in the frozen contracts ladder order."""
        caps = [METHOD_FIDELITY_CAP[channel.method] for channel in self.channels]
        return min(caps, key=_FIDELITY_LADDER.index)

    def covers(self, case_key: str) -> bool:
        return "*" in self.scope or case_key in self.scope

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_by": self.approved_by,
            "channels": [channel.to_dict() for channel in self.channels],
            "created_utc": self.created_utc,
            "notes": self.notes,
            "record_id": self.record_id,
            "schema": CAL_SCHEMA,
            "scope": list(self.scope),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CalibrationRecord":
        data = _require_mapping(d, "CalibrationRecord")
        _check_keys(data, _RECORD_KEYS, _RECORD_KEYS, "calibration")
        if data["schema"] != CAL_SCHEMA:
            raise contracts.SchemaError(
                f"calibration schema must be {CAL_SCHEMA!r}, got {data['schema']!r}")
        channels = data["channels"]
        if isinstance(channels, (str, bytes)) or not isinstance(channels, Sequence):
            raise contracts.SchemaError("channels must be a list of channel mappings")
        scope = data["scope"]
        if isinstance(scope, (str, bytes)) or not isinstance(scope, Sequence):
            raise contracts.SchemaError("scope must be a list of case keys or ['*']")
        record = cls(
            record_id=str(data["record_id"]),
            created_utc=str(data["created_utc"]),
            approved_by=str(data["approved_by"]),
            scope=tuple(str(s) for s in scope),
            channels=tuple(ChannelCalibration.from_dict(c) for c in channels),
            notes=str(data["notes"]),
        )
        if record.record_id != record.compute_id():
            raise contracts.SchemaError(
                f"record_id {record.record_id!r} != computed {record.compute_id()!r}")
        return record


def new_record(*, created_utc: str, approved_by: str,
               scope: Sequence[str], channels: Sequence[ChannelCalibration],
               notes: str = "") -> CalibrationRecord:
    """Build a record and derive its id with :func:`contracts.domain_sha16`.

    A convenience for writers/tests: the id is never passed in, so the "never hand-pick an id"
    rule holds by construction. Validation is the dataclass's own.
    """
    provisional = CalibrationRecord(
        record_id="0" * 16,
        created_utc=created_utc,
        approved_by=approved_by,
        scope=tuple(scope),
        channels=tuple(channels),
        notes=notes,
    )
    return replace(provisional, record_id=provisional.compute_id())


# --------------------------------------------------------------------------- application

def apply_calibration(response: contracts.SystemResponse, record: CalibrationRecord,
                      *, case_key: str) -> contracts.SystemResponse:
    """Bring every excitation field to Pa per ``V_rms`` and cap the fidelity.

    Multiplies each channel's ``(nf, nobs)`` field by its complex factor (one value per
    frequency row), returns a new response, and leaves distance/origin/angular frame/geometry
    hash untouched so :meth:`SourceBasis.compatible_for_sum_with` still guards the sum. The input
    response and its arrays are not mutated.
    """
    if not isinstance(record, CalibrationRecord):
        raise contracts.SchemaError(
            f"record must be a CalibrationRecord, got {type(record).__name__}")
    if not isinstance(case_key, str) or not case_key:
        raise _error("CAL_SCOPE_MISMATCH",
                     "a case_key is required to check a calibration record's scope")
    if not record.covers(case_key):
        raise _error("CAL_SCOPE_MISMATCH",
                     f"record {record.record_id!r} scope {list(record.scope)} does not cover "
                     f"case_key {case_key!r}")

    field_map = response.p_by_excitation
    if field_map is None or not response.excitation_names:
        raise _error("CAL_CHANNEL_MISSING",
                     "response carries no complex excitation fields to calibrate")

    names = tuple(response.excitation_names)
    by_excitation = {channel.excitation: channel for channel in record.channels}
    missing = [name for name in names if name not in by_excitation]
    if missing:
        raise _error("CAL_CHANNEL_MISSING",
                     f"no ChannelCalibration for response excitations {missing}")
    extra = [channel.excitation for channel in record.channels if channel.excitation not in names]
    if extra:
        raise _error("CAL_CHANNEL_MISSING",
                     f"calibration channels {extra} are not response excitations {list(names)}")

    bases = dict(response.excitation_bases)
    calibrated: dict[str, np.ndarray] = {}
    for name in names:
        channel = by_excitation[name]
        basis = bases.get(name)
        if basis is None:
            raise _error("CAL_UNIT_MISMATCH", f"excitation {name!r} has no SourceBasis")
        if channel.from_per_input != basis.per_input:
            raise _error("CAL_UNIT_MISMATCH",
                         f"excitation {name!r}: channel from_per_input "
                         f"{channel.from_per_input!r} != basis per_input {basis.per_input!r}")
        if not _grid_matches(channel.frequencies_hz, response.frequencies_hz):
            raise _error("CAL_FREQ_GRID_MISMATCH",
                         f"excitation {name!r}: record grid {len(channel.frequencies_hz)} points "
                         f"does not match the response grid ({response.frequencies_hz.size} "
                         "points, 1e-9 relative); v1 does not interpolate")

        arr = np.asarray(field_map[name], dtype=np.complex128)
        if arr.shape[0] != len(channel.frequencies_hz):
            raise _error("CAL_FREQ_GRID_MISMATCH",
                         f"excitation {name!r}: field axis {arr.shape[0]} != record grid "
                         f"{len(channel.frequencies_hz)}")
        if not np.all(np.isfinite(arr)):
            raise _error("CAL_NONFINITE", f"excitation {name!r}: field contains non-finite values")
        factor = (np.asarray(channel.factor_re, dtype=np.float64)
                  + 1j * np.asarray(channel.factor_im, dtype=np.float64))
        if not np.all(np.isfinite(factor)):
            raise _error("CAL_NONFINITE", f"excitation {name!r}: factor contains non-finite values")

        calibrated[name] = arr * factor.reshape((-1,) + (1,) * (arr.ndim - 1))
        bases[name] = replace(basis, per_input=channel.to_per_input)

    return replace(
        response,
        p_by_excitation=calibrated,
        excitation_bases=bases,
        fidelity=_min_fidelity(response.fidelity, record.fidelity_cap()),
    )
