"""Offline tests for the typed solve-authorization record (contract section 4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hornlab_search.system.authorization import (
    AUTH_ID_DOMAIN,
    AUTH_SCHEMA,
    AUTH_SCOPE_KINDS,
    AUTH_TOKENS,
    AuthorizationError,
    AuthorizationRecord,
    check,
    from_legacy_string,
    load_authorization,
)
from hornlab_search.system.contracts import domain_sha16

NOW = "2026-11-20T00:00:00+00:00"
CREATED = "2026-11-19T00:00:00+00:00"


def _record(**overrides):
    payload = {
        "who": "owner",
        "why": "approve the reference solve",
        "scope_kind": "case",
        "scope": ["ref/20261120T000000Z-case-1234"],
        "actions": ["bl_solve"],
        "created_utc": CREATED,
        "expires_utc": None,
        "legacy_free_string": False,
    }
    payload.update(overrides)
    return AuthorizationRecord.from_dict(payload)


def test_contract_identity_and_round_trip() -> None:
    record = _record()
    assert AUTH_SCHEMA == "hornlab.system.authorization.v1"
    assert record.record_id == domain_sha16(AUTH_ID_DOMAIN, record.payload())
    assert set(record.to_dict()) == {
        "record_id", "who", "why", "scope_kind", "scope", "actions", "created_utc",
        "expires_utc", "legacy_free_string",
    }
    assert list(record.to_dict()) == sorted(record.to_dict())
    assert json.loads(json.dumps(record.to_dict())) == record.to_dict()
    assert AuthorizationRecord.from_dict(record.to_dict()) == record


def test_from_dict_derives_the_id_even_if_a_wrong_one_is_supplied() -> None:
    record = _record(record_id="hand-picked")
    assert record.record_id != "hand-picked"
    assert record.record_id == domain_sha16(AUTH_ID_DOMAIN, record.payload())


def test_legacy_string_is_wrapped_deterministically() -> None:
    first = from_legacy_string("senior-gate-2026-11-18")
    second = from_legacy_string("senior-gate-2026-11-18")
    assert first == second
    assert first.legacy_free_string is True
    assert first.scope == ("*",)
    assert first.scope_kind == "case"
    assert first.actions == ("bl_solve",)
    assert first.who == "senior-gate-2026-11-18"
    check(first, action="bl_solve", case_key="anything/at-all", now_utc=NOW)


def test_blank_legacy_string_is_missing() -> None:
    for text in ("", "   "):
        with pytest.raises(AuthorizationError) as exc:
            from_legacy_string(text)
        assert exc.value.token == "AUTH_MISSING"


def test_missing_record_and_action_tokens() -> None:
    with pytest.raises(AuthorizationError) as exc:
        check(None, action="bl_solve", case_key="ref/case", now_utc=NOW)
    assert exc.value.token == "AUTH_MISSING"

    record = _record()
    with pytest.raises(AuthorizationError) as exc:
        check(record, action="gpu_solve", case_key="ref/20261120T000000Z-case-1234",
              now_utc=NOW)
    assert exc.value.token == "AUTH_ACTION_NOT_GRANTED"


def test_expiry_is_strict_at_the_boundary() -> None:
    record = _record(expires_utc="2026-11-20T00:00:00+00:00")
    check(record, action="bl_solve", case_key="ref/20261120T000000Z-case-1234",
          now_utc="2026-11-19T23:59:59+00:00")
    with pytest.raises(AuthorizationError) as exc:
        check(record, action="bl_solve", case_key="ref/20261120T000000Z-case-1234",
              now_utc=NOW)
    assert exc.value.token == "AUTH_EXPIRED"

    no_expiry = _record(expires_utc=None)
    check(no_expiry, action="bl_solve", case_key="ref/20261120T000000Z-case-1234",
          now_utc="2099-01-01T00:00:00+00:00")


def test_case_scope_is_exact() -> None:
    record = _record(scope_kind="case", scope=["ref/case-a"])
    check(record, action="bl_solve", case_key="ref/case-a", now_utc=NOW)
    with pytest.raises(AuthorizationError) as exc:
        check(record, action="bl_solve", case_key="ref/case-b", now_utc=NOW)
    assert exc.value.token == "AUTH_SCOPE_MISMATCH"


def test_experiment_scope_matches_the_experiment_component_only() -> None:
    record = _record(scope_kind="experiment", scope=["ref"])
    check(record, action="bl_solve", case_key="ref/case-a", now_utc=NOW)
    with pytest.raises(AuthorizationError) as exc:
        check(record, action="bl_solve", case_key="other/case-a", now_utc=NOW)
    assert exc.value.token == "AUTH_SCOPE_MISMATCH"


def test_funnel_run_scope_names_case_keys() -> None:
    record = _record(scope_kind="funnel_run", scope=["ref/case-a", "ref/case-b"])
    check(record, action="bl_solve", case_key="ref/case-b", now_utc=NOW)
    with pytest.raises(AuthorizationError) as exc:
        check(record, action="bl_solve", case_key="ref/case-c", now_utc=NOW)
    assert exc.value.token == "AUTH_SCOPE_MISMATCH"


def test_wildcard_scope_matches_every_case() -> None:
    record = _record(scope=["*"])
    for case_key in ("ref/a", "other/b", "anything/at-all"):
        check(record, action="bl_solve", case_key=case_key, now_utc=NOW)


def test_from_dict_validates_scope_actions_and_times() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _record(scope_kind="galaxy")
    assert exc.value.token == "AUTH_SCOPE_MISMATCH"
    with pytest.raises(AuthorizationError) as exc:
        _record(scope=[])
    assert exc.value.token == "AUTH_SCOPE_MISMATCH"
    with pytest.raises(AuthorizationError) as exc:
        _record(actions=["gpu_solve"])
    assert exc.value.token == "AUTH_ACTION_NOT_GRANTED"
    with pytest.raises(AuthorizationError) as exc:
        _record(who="")
    assert exc.value.token == "AUTH_MISSING"
    with pytest.raises(AuthorizationError) as exc:
        _record(created_utc="yesterday")
    assert exc.value.token == "AUTH_MISSING"
    with pytest.raises(AuthorizationError) as exc:
        _record(expires_utc="tomorrow")
    assert exc.value.token == "AUTH_EXPIRED"
    with pytest.raises(AuthorizationError) as exc:
        _record(created_utc="2026-11-19T00:00:00")
    assert exc.value.token == "AUTH_MISSING"


def test_all_declared_tokens_are_auth_tokens() -> None:
    assert AUTH_TOKENS == ("AUTH_MISSING", "AUTH_EXPIRED", "AUTH_SCOPE_MISMATCH",
                           "AUTH_ACTION_NOT_GRANTED")
    assert set(AUTH_SCOPE_KINDS) == {"case", "experiment", "funnel_run"}


def test_load_authorization_accepts_plain_wrapped_and_nested_records(tmp_path: Path) -> None:
    record = _record()
    plain = tmp_path / "plain.json"
    plain.write_text(json.dumps(record.to_dict()), encoding="utf-8")
    assert load_authorization(plain) == record

    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"payload": json.dumps(record.to_dict())}), encoding="utf-8")
    assert load_authorization(wrapped) == record

    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps({"record": record.to_dict()}), encoding="utf-8")
    assert load_authorization(nested) == record

    with pytest.raises(AuthorizationError) as exc:
        load_authorization(tmp_path / "absent.json")
    assert exc.value.token == "AUTH_MISSING"

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(AuthorizationError) as exc:
        load_authorization(broken)
    assert exc.value.token == "AUTH_MISSING"
