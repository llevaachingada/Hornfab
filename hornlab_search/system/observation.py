"""Observation standards and honest curve labels for the system layer.

Contract: ``docs/system_v1/01_CONTRACTS.md`` section 5.  This is a **schema only** module:
no distance, angle grid, window or approval value is committed here.  A read model calls
:func:`label_for` so a curve is never presented as a far-field result without a declared
:class:`ObservationStandard`.

The fallback label is the exact contract string, used whenever the standard is missing or
does not claim a far field.  A declared far-field standard renders the distance and frame
so the claim is visible on the curve itself.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hornlab_search.system.contracts import domain_sha16

__all__ = [
    "NEAR_FIELD_LABEL",
    "OBSERVATION_ID_DOMAIN",
    "OBSERVATION_SCHEMA",
    "OBSERVATION_TOKENS",
    "ObservationError",
    "ObservationStandard",
    "label_for",
]

OBSERVATION_SCHEMA = "hornlab.system.observation.v1"
OBSERVATION_ID_DOMAIN = "system.observation"
OBSERVATION_TOKENS: tuple[str, ...] = ("OBSERVATION_INVALID",)

#: Exact contract label for an undeclared / non-far-field observation.
NEAR_FIELD_LABEL = "near-field cuts (undeclared standard)"


class ObservationError(ValueError):
    """An observation standard does not satisfy the schema."""

    def __init__(self, token: str, detail: str) -> None:
        if token not in OBSERVATION_TOKENS:
            raise AssertionError(f"undeclared observation token {token!r}")
        self.token = token
        self.detail = detail
        super().__init__(f"{token}: {detail}")


# --------------------------------------------------------------------------- validation

def _finite(name: str, value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ObservationError("OBSERVATION_INVALID", f"{name} must be a number") from None
    if not math.isfinite(number):
        raise ObservationError("OBSERVATION_INVALID", f"{name} must be finite")
    return number


def _angles(name: str, value: Any) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ObservationError(
            "OBSERVATION_INVALID", f"{name} must be a sequence of angles")
    return tuple(_finite(f"{name}[{index}]", item) for index, item in enumerate(value))


def _window(value: Any) -> tuple[tuple[float, float], ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ObservationError(
            "OBSERVATION_INVALID", "listening_window must be null or a sequence of pairs")
    pairs: list[tuple[float, float]] = []
    for index, item in enumerate(value):
        if isinstance(item, (str, bytes)) or not isinstance(item, Sequence) or len(item) != 2:
            raise ObservationError(
                "OBSERVATION_INVALID",
                f"listening_window[{index}] must be a (low, high) pair",
            )
        low = _finite(f"listening_window[{index}][0]", item[0])
        high = _finite(f"listening_window[{index}][1]", item[1])
        if low > high:
            raise ObservationError(
                "OBSERVATION_INVALID",
                f"listening_window[{index}] low {low:g} exceeds high {high:g}",
            )
        pairs.append((low, high))
    return tuple(pairs)


# --------------------------------------------------------------------------- record

@dataclass(frozen=True, slots=True)
class ObservationStandard:
    """The declared distance, angular grid, listening window and approval of one observation."""

    standard_id: str
    distance_m: float
    angular_frame: str
    h_angles_deg: tuple[float, ...]
    v_angles_deg: tuple[float, ...]
    listening_window: tuple[tuple[float, float], ...] | None
    far_field_claimed: bool
    approved_by: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.standard_id, str) or not self.standard_id.strip():
            raise ObservationError("OBSERVATION_INVALID", "standard_id must be a non-empty string")
        if not isinstance(self.distance_m, (int, float)) or isinstance(self.distance_m, bool):
            raise ObservationError("OBSERVATION_INVALID", "distance_m must be a number")
        if not math.isfinite(float(self.distance_m)) or float(self.distance_m) <= 0.0:
            raise ObservationError("OBSERVATION_INVALID", "distance_m must be finite and > 0")
        if not isinstance(self.angular_frame, str) or not self.angular_frame.strip():
            raise ObservationError(
                "OBSERVATION_INVALID", "angular_frame must be a non-empty string")
        _angles("h_angles_deg", self.h_angles_deg)
        _angles("v_angles_deg", self.v_angles_deg)
        normalised = _window(self.listening_window)
        if normalised != self.listening_window:
            object.__setattr__(self, "listening_window", normalised)
        if not isinstance(self.far_field_claimed, bool):
            raise ObservationError("OBSERVATION_INVALID", "far_field_claimed must be a bool")
        if self.approved_by is not None and (
                not isinstance(self.approved_by, str) or not self.approved_by.strip()):
            raise ObservationError(
                "OBSERVATION_INVALID", "approved_by must be a non-empty string or null")

    # ------------------------------------------------------------------ identity

    def payload(self) -> Mapping[str, Any]:
        """Canonical payload hashed for ``standard_id``."""
        return {
            "distance_m": float(self.distance_m),
            "angular_frame": self.angular_frame,
            "h_angles_deg": [float(value) for value in self.h_angles_deg],
            "v_angles_deg": [float(value) for value in self.v_angles_deg],
            "listening_window": (
                None if self.listening_window is None
                else [[float(low), float(high)] for low, high in self.listening_window]
            ),
            "far_field_claimed": bool(self.far_field_claimed),
            "approved_by": self.approved_by,
        }

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe record with sorted keys."""
        body = {"standard_id": self.standard_id, **self.payload()}
        return dict(sorted(body.items()))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ObservationStandard":
        """Validate a mapping and derive ``standard_id`` from its payload."""
        if not isinstance(data, Mapping):
            raise ObservationError("OBSERVATION_INVALID", "a standard must be a mapping")
        distance = _finite("distance_m", data.get("distance_m"))
        frame = data.get("angular_frame")
        if not isinstance(frame, str) or not frame.strip():
            raise ObservationError(
                "OBSERVATION_INVALID", "angular_frame must be a non-empty string")
        far_field = data.get("far_field_claimed")
        if not isinstance(far_field, bool):
            raise ObservationError(
                "OBSERVATION_INVALID", "far_field_claimed must be a bool")
        approved = data.get("approved_by")
        if approved == "None":  # the repo's canonical_json renders a null as "None"
            approved = None
        if approved is not None and (
                not isinstance(approved, str) or not approved.strip()):
            raise ObservationError(
                "OBSERVATION_INVALID", "approved_by must be a non-empty string or null")
        payload = {
            "distance_m": distance,
            "angular_frame": frame,
            "h_angles_deg": [float(value) for value in _angles("h_angles_deg",
                                                               data.get("h_angles_deg", ()))],
            "v_angles_deg": [float(value) for value in _angles("v_angles_deg",
                                                               data.get("v_angles_deg", ()))],
            "listening_window": (
                None if data.get("listening_window") is None
                else [[float(low), float(high)]
                      for low, high in _window(data.get("listening_window")) or ()]
            ),
            "far_field_claimed": far_field,
            "approved_by": approved,
        }
        return cls(
            standard_id=domain_sha16(OBSERVATION_ID_DOMAIN, payload),
            distance_m=distance,
            angular_frame=frame,
            h_angles_deg=tuple(payload["h_angles_deg"]),
            v_angles_deg=tuple(payload["v_angles_deg"]),
            listening_window=_window(payload["listening_window"]),
            far_field_claimed=far_field,
            approved_by=approved,
        )


# --------------------------------------------------------------------------- labels

def label_for(basis: Any, standard: ObservationStandard | None) -> str:
    """Label one curve with its declared observation standard.

    The contract fallback is exact: ``"near-field cuts (undeclared standard)"`` when the
    standard is ``None`` or does not claim a far field.  ``basis`` is accepted so callers
    pass the same object they are labelling; this schema does not infer a claim from it.
    """
    if standard is None or not standard.far_field_claimed:
        return NEAR_FIELD_LABEL
    return f"far-field {float(standard.distance_m):g} m ({standard.angular_frame})"
