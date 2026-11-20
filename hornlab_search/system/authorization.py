"""Typed solve-authorization records for the HornFab system layer.

Contract: ``docs/system_v1/01_CONTRACTS.md`` section 4.  A record says *who* authorised
*which action* over *which scope*, and *why*, with an optional expiry.  The system layer
never grants a solve from a bare boolean: :func:`check` raises one of the four refusal
tokens below, and :class:`AuthorizationRecord` keeps the legacy free-string form wrapped
(:attr:`AuthorizationRecord.legacy_free_string`) so an existing ``authorized_by`` value
still works without pretending it was typed.

Determinism: ``record_id`` is always ``domain_sha16("system.authorization", payload)``;
the legacy wrapper uses a fixed epoch ``created_utc`` so the same free string always
produces the same record.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from hornlab_search.system.contracts import domain_sha16

__all__ = [
    "AUTH_ACTIONS",
    "AUTH_ID_DOMAIN",
    "AUTH_SCHEMA",
    "AUTH_SCOPE_KINDS",
    "AUTH_TOKENS",
    "AuthorizationError",
    "AuthorizationRecord",
    "LEGACY_CREATED_UTC",
    "check",
    "from_legacy_string",
    "load_authorization",
]

AUTH_SCHEMA = "hornlab.system.authorization.v1"
AUTH_ID_DOMAIN = "system.authorization"
AUTH_SCOPE_KINDS: tuple[str, ...] = ("case", "experiment", "funnel_run")
AUTH_ACTIONS: tuple[str, ...] = ("bl_solve",)
AUTH_TOKENS: tuple[str, ...] = (
    "AUTH_MISSING",
    "AUTH_EXPIRED",
    "AUTH_SCOPE_MISMATCH",
    "AUTH_ACTION_NOT_GRANTED",
)

#: Fixed timestamp for a wrapped legacy free string (the real creation time is unknown).
LEGACY_CREATED_UTC = "1970-01-01T00:00:00+00:00"

_UTC = _dt.timezone.utc


class AuthorizationError(RuntimeError):
    """An authorization record is missing, expired, out of scope, or lacks an action."""

    def __init__(self, token: str, detail: str) -> None:
        if token not in AUTH_TOKENS:
            raise AssertionError(f"undeclared authorization token {token!r}")
        self.token = token
        self.detail = detail
        super().__init__(f"{token}: {detail}")


# --------------------------------------------------------------------------- validation

def _text(name: str, value: Any, token: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorizationError(token, f"{name} must be a non-empty string")
    return value


def _utc(name: str, value: Any, token: str) -> str:
    text = _text(name, value, token)
    try:
        parsed = _dt.datetime.fromisoformat(text)
    except ValueError:
        raise AuthorizationError(token, f"{name} is not an ISO-8601 timestamp: {text!r}") from None
    if parsed.tzinfo is None or parsed.utcoffset() != _dt.timedelta(0):
        raise AuthorizationError(token, f"{name} must be a UTC ISO-8601 timestamp: {text!r}")
    return text


def _parse_utc(name: str, value: str) -> _dt.datetime:
    try:
        parsed = _dt.datetime.fromisoformat(value)
    except ValueError:
        raise AuthorizationError(
            "AUTH_EXPIRED", f"{name} is not an ISO-8601 timestamp: {value!r}") from None
    if parsed.tzinfo is None or parsed.utcoffset() != _dt.timedelta(0):
        raise AuthorizationError(
            "AUTH_EXPIRED", f"{name} must be a UTC ISO-8601 timestamp: {value!r}")
    return parsed


def _text_tuple(name: str, value: Any, token: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AuthorizationError(token, f"{name} must be a sequence of non-empty strings")
    items = tuple(str(item) for item in value)
    if not items:
        raise AuthorizationError(token, f"{name} must not be empty")
    if any(not item.strip() for item in items):
        raise AuthorizationError(token, f"{name} contains an empty entry")
    return items


def _actions(value: Any) -> tuple[str, ...]:
    actions = _text_tuple("actions", value, "AUTH_ACTION_NOT_GRANTED")
    unknown = [action for action in actions if action not in AUTH_ACTIONS]
    if unknown:
        raise AuthorizationError(
            "AUTH_ACTION_NOT_GRANTED",
            f"actions {unknown!r} are not in {list(AUTH_ACTIONS)}",
        )
    return actions


# --------------------------------------------------------------------------- record

@dataclass(frozen=True, slots=True)
class AuthorizationRecord:
    """A typed who/why/scope/action record written beside a BL solve."""

    record_id: str
    who: str
    why: str
    scope_kind: Literal["case", "experiment", "funnel_run"]
    scope: tuple[str, ...]
    actions: tuple[Literal["bl_solve"], ...]
    created_utc: str
    expires_utc: str | None
    legacy_free_string: bool = False

    def __post_init__(self) -> None:
        _text("record_id", self.record_id, "AUTH_MISSING")
        _text("who", self.who, "AUTH_MISSING")
        _text("why", self.why, "AUTH_MISSING")
        if self.scope_kind not in AUTH_SCOPE_KINDS:
            raise AuthorizationError(
                "AUTH_SCOPE_MISMATCH",
                f"scope_kind must be one of {list(AUTH_SCOPE_KINDS)}, got {self.scope_kind!r}",
            )
        _text_tuple("scope", self.scope, "AUTH_SCOPE_MISMATCH")
        _actions(self.actions)
        _utc("created_utc", self.created_utc, "AUTH_MISSING")
        if self.expires_utc is not None:
            _utc("expires_utc", self.expires_utc, "AUTH_EXPIRED")

    # ------------------------------------------------------------------ identity

    def payload(self) -> Mapping[str, Any]:
        """The canonical payload hashed for ``record_id`` (no id, no schema key)."""
        return {
            "who": self.who,
            "why": self.why,
            "scope_kind": self.scope_kind,
            "scope": list(self.scope),
            "actions": list(self.actions),
            "created_utc": self.created_utc,
            "expires_utc": self.expires_utc,
            "legacy_free_string": bool(self.legacy_free_string),
        }

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe record with sorted keys (lists for tuples)."""
        body = {
            "record_id": self.record_id,
            "who": self.who,
            "why": self.why,
            "scope_kind": self.scope_kind,
            "scope": list(self.scope),
            "actions": list(self.actions),
            "created_utc": self.created_utc,
            "expires_utc": self.expires_utc,
            "legacy_free_string": bool(self.legacy_free_string),
        }
        return dict(sorted(body.items()))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuthorizationRecord":
        """Validate a mapping and derive its id (a supplied id is never trusted)."""
        if not isinstance(data, Mapping):
            raise AuthorizationError("AUTH_MISSING", "an authorization record must be a mapping")
        who = _text("who", data.get("who"), "AUTH_MISSING")
        why = _text("why", data.get("why"), "AUTH_MISSING")
        scope_kind = data.get("scope_kind")
        if scope_kind not in AUTH_SCOPE_KINDS:
            raise AuthorizationError(
                "AUTH_SCOPE_MISMATCH",
                f"scope_kind must be one of {list(AUTH_SCOPE_KINDS)}, got {scope_kind!r}",
            )
        scope = _text_tuple("scope", data.get("scope"), "AUTH_SCOPE_MISMATCH")
        actions = _actions(data.get("actions"))
        created_utc = _utc("created_utc", data.get("created_utc"), "AUTH_MISSING")
        expires = data.get("expires_utc")
        if expires == "None":  # the repo's canonical_json renders a null as "None"
            expires = None
        expires_utc = None if expires is None else _utc("expires_utc", expires, "AUTH_EXPIRED")
        legacy = data.get("legacy_free_string", False)
        if not isinstance(legacy, bool):
            raise AuthorizationError("AUTH_MISSING", "legacy_free_string must be a bool")

        payload = {
            "who": who,
            "why": why,
            "scope_kind": scope_kind,
            "scope": list(scope),
            "actions": list(actions),
            "created_utc": created_utc,
            "expires_utc": expires_utc,
            "legacy_free_string": legacy,
        }
        return cls(
            record_id=domain_sha16(AUTH_ID_DOMAIN, payload),
            who=who,
            why=why,
            scope_kind=scope_kind,
            scope=scope,
            actions=actions,
            created_utc=created_utc,
            expires_utc=expires_utc,
            legacy_free_string=legacy,
        )


# --------------------------------------------------------------------------- entry points

def from_legacy_string(text: str) -> AuthorizationRecord:
    """Wrap an existing free-string approval (``scope`` is ``("*",)``)."""
    value = _text("legacy authorization", text, "AUTH_MISSING")
    return AuthorizationRecord.from_dict({
        "who": value,
        "why": "legacy free-string authorization (wrapped; no typed scope or expiry)",
        "scope_kind": "case",
        "scope": ["*"],
        "actions": ["bl_solve"],
        "created_utc": LEGACY_CREATED_UTC,
        "expires_utc": None,
        "legacy_free_string": True,
    })


def load_authorization(path: Path) -> AuthorizationRecord:
    """Read a record written as a plain mapping or a wrapped ``payload`` record."""
    path = Path(path)
    if not path.is_file():
        raise AuthorizationError("AUTH_MISSING", f"authorization record not found: {path}")
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AuthorizationError("AUTH_MISSING", f"unreadable authorization {path}: {exc}") from None
    if isinstance(body, Mapping) and "record" in body and isinstance(body["record"], Mapping):
        body = body["record"]
    elif isinstance(body, Mapping) and "payload" in body:
        payload = body["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError as exc:
                raise AuthorizationError(
                    "AUTH_MISSING", f"unreadable authorization payload in {path}: {exc}") from None
        body = payload
    return AuthorizationRecord.from_dict(body)


def check(record: AuthorizationRecord | None, *, action: str, case_key: str,
          now_utc: str) -> None:
    """Refuse unless ``record`` grants ``action`` for ``case_key`` at ``now_utc``.

    ``scope`` entries are matched against the case key: exact equality for ``case`` and
    ``funnel_run``, the ``<experiment>`` component for ``experiment``, and ``"*"`` always
    matches.  An expiry at or before ``now_utc`` is refused.
    """
    if record is None:
        raise AuthorizationError("AUTH_MISSING", "no authorization record was supplied")
    if not isinstance(record, AuthorizationRecord):
        raise AuthorizationError("AUTH_MISSING", "authorization must be an AuthorizationRecord")
    if not isinstance(action, str) or not action:
        raise AuthorizationError("AUTH_ACTION_NOT_GRANTED", "an action is required")
    if action not in AUTH_ACTIONS:
        raise AuthorizationError(
            "AUTH_ACTION_NOT_GRANTED", f"action {action!r} is not in {list(AUTH_ACTIONS)}")
    if action not in record.actions:
        raise AuthorizationError(
            "AUTH_ACTION_NOT_GRANTED",
            f"record {record.record_id!r} does not grant {action!r}",
        )
    if record.expires_utc is not None:
        if _parse_utc("now_utc", now_utc) >= _parse_utc("expires_utc", record.expires_utc):
            raise AuthorizationError(
                "AUTH_EXPIRED", f"record {record.record_id!r} expired at {record.expires_utc}")
    case_key = _text("case_key", case_key, "AUTH_SCOPE_MISMATCH")
    if "*" in record.scope:
        return
    if record.scope_kind == "experiment":
        experiment = case_key.split("/", 1)[0]
        matched = experiment in record.scope
    else:
        matched = case_key in record.scope
    if not matched:
        raise AuthorizationError(
            "AUTH_SCOPE_MISMATCH",
            f"record {record.record_id!r} scope {list(record.scope)} does not cover {case_key!r}",
        )
