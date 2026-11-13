"""Study registry primitives. Concrete execution/package schema is not yet frozen."""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROTOCOL = 'bo-study-v1.1'
STAGE_STATES = frozenset({'not_started', 'queued', 'running', 'complete', 'failed',
                          'interrupted', 'unknown', 'stale'})
DECISIONS = frozenset({'accept', 'reject', 'inconclusive'})


class StudyError(Exception):
    """A typed service failure, translatable by an API adapter."""
    status_code = 400


class NotFound(StudyError):
    status_code = 404


class Conflict(StudyError):
    status_code = 409


class Unavailable(StudyError):
    status_code = 422


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise StudyError(f'value is not finite canonical JSON: {exc}') from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def validate_spec(spec: dict) -> dict:
    """Validate an opaque draft, not a full executable StudySpec.

    The protocol does not freeze its detailed field schema; this cannot approve a
    package or establish cohort, numerical, or execution eligibility.
    """
    if not isinstance(spec, dict) or spec.get('protocol') != PROTOCOL:
        raise StudyError('draft spec must be an object with protocol bo-study-v1.1')
    return json.loads(canonical(spec))
