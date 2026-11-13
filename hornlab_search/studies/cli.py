"""Validated study-workflow CLI (``bo-study-v1.1`` execution package lane).

Usage from the project interpreter::

    .venv\\Scripts\\python.exe -m hornlab_search.studies.cli validate --root ROOT --spec study.json
    ...
    .venv\\Scripts\\python.exe -m hornlab_search.studies.cli run --root ROOT --package package.json --dry-run

All paths are resolved inside an explicit study root; no shell strings are
executed and no solver/GPU/lane ownership is acquired.  ``run`` is dry-run only
in this build: real scheduling remains a separately authorized action.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from .package import prepare_run_package, verify_package
from .reconcile import reconcile_study
from .runner import run_package
from .schema import StudyError, Unavailable, canonical, digest, validate_spec
from .service import DraftAttemptJournal, StudyService

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INVALID = 3
EXIT_NOT_FOUND = 4
EXIT_CONFLICT = 5
EXIT_UNAVAILABLE = 6

_STATUS_EXIT = {
    400: EXIT_INVALID,
    404: EXIT_NOT_FOUND,
    409: EXIT_CONFLICT,
    422: EXIT_UNAVAILABLE,
}

# command -> (required flags, optional flags)
_COMMANDS = {
    'validate': ({'--spec'}, {'--root'}),
    'create': ({'--spec'}, {'--root', '--key', '--parent'}),
    'snapshot': ({'--study'}, {'--root'}),
    'analyze': ({'--study'}, {'--root'}),
    'propose': ({'--study'}, {'--root'}),
    'package': ({'--study', '--out'},
                {'--root', '--lane', '--deadline', '--key', '--revision'}),
    'run': ({'--package'}, {'--root', '--dry-run'}),
    'reconcile': ({'--study'}, {'--root'}),
    'decide': ({'--study', '--payload'}, {'--root', '--key'}),
    'export': ({'--study', '--out'}, {'--root'}),
}

_BOOLEAN_FLAGS = {'--dry-run'}


class UsageError(Exception):
    """Malformed argv or a path outside the contained study root."""


def _parse(argv):
    if not isinstance(argv, (list, tuple)) or not argv:
        raise UsageError('a study command is required')
    if any(not isinstance(token, str) for token in argv):
        raise UsageError('argv entries must be strings')
    command = argv[0]
    if command not in _COMMANDS:
        raise UsageError(f'unknown study command {command!r}')
    required, optional = _COMMANDS[command]
    allowed = required | optional
    values = {}
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == '--':
            raise UsageError('positional arguments are not allowed')
        if not token.startswith('--'):
            raise UsageError(f'unexpected argument {token!r}')
        if '=' in token:
            raise UsageError('use --flag value; --flag=value is not allowed')
        if token not in allowed:
            raise UsageError(f'flag {token!r} is not allowed for {command}')
        if token in values:
            raise UsageError(f'duplicate flag {token!r}')
        if token in _BOOLEAN_FLAGS:
            values[token] = True
            index += 1
            continue
        if index + 1 >= len(argv):
            raise UsageError(f'{token} requires a value')
        value = argv[index + 1]
        if value.startswith('--'):
            raise UsageError(f'{token} requires a value')
        values[token] = value
        index += 2
    missing = sorted(required - set(values))
    if missing:
        raise UsageError(f'missing required flag(s): {", ".join(missing)}')
    return command, values


def _root(values):
    raw = values.get('--root')
    if raw is None:
        return (Path.cwd() / 'studies').resolve()
    if not isinstance(raw, str) or not raw.strip():
        raise UsageError('--root requires a path')
    return Path(raw).resolve()


def _contained(root, value, flag):
    if not isinstance(value, str) or not value.strip():
        raise UsageError(f'{flag} requires a path')
    path = Path(value)
    candidate = (path if path.is_absolute() else root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise UsageError(f'{flag} path escapes the contained study root') from exc
    return candidate


def _read_json(path, flag):
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise StudyError(f'{flag} could not be read: {exc}') from exc
    try:
        # Accept a UTF-8 BOM: Windows editors/PowerShell commonly write one, and the
        # JSON payload itself stays strictly UTF-8 and object-typed.
        value = json.loads(data.decode('utf-8-sig'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise StudyError(f'{flag} is not valid UTF-8 JSON') from exc
    if not isinstance(value, dict):
        raise StudyError(f'{flag} must contain a JSON object')
    return value


def _write_json(path, value):
    data = canonical(value).encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.tmp-{uuid.uuid4().hex}')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _artifact(service, study_id, kind):
    service.get_study(study_id)  # explicit 404 for an unknown study
    metadata = service.get_artifact_metadata(study_id, kind)
    status = metadata.get('status')
    if status == 'missing':
        raise Unavailable(f'{kind} artifact is not available; its builder is not wired in this build')
    if status != 'available':
        raise Unavailable(f'{kind} artifact is {status}')
    return {'study_id': study_id, 'kind': kind, 'artifact': metadata}


class _NoEvidenceProbe:
    """Conservative probe: absence of evidence is never evidence of no call."""

    def inspect(self, attempt):
        return {'state': 'unknown'}


def _dispatch(command, values):
    root = _root(values)
    if command == 'validate':
        spec = validate_spec(_read_json(_contained(root, values['--spec'], '--spec'), '--spec'))
        return {'status': 'valid', 'spec_hash': digest(spec)}

    if command == 'run':
        if not values.get('--dry-run'):
            raise UsageError('run requires --dry-run; real runs are scheduled separately')
        package = verify_package(_read_json(
            _contained(root, values['--package'], '--package'), '--package'))
        # Handle dry-run before opening the registry: zero registry/acoustic writes.
        # Passing no adapters and dry_run=True is the zero-spawn guard.
        result = run_package(package, None, None, None, dry_run=True)
        result.update({
            'package_id': package['package_id'],
            'study_id': package['study_id'],
            'spec_revision': package['spec_revision'],
            'execution_mode': package['execution_mode'],
            'protocol': package['protocol'],
            'budget': package['budget'],
            'lane': package['lane'],
            'deadline_required': package['deadline_required'],
            'deadline_provided': bool(package.get('deadline')),
            'deadline': package.get('deadline'),
            'status_note': package['status_note'],
        })
        return result

    service = StudyService(root)

    if command == 'create':
        spec = validate_spec(_read_json(_contained(root, values['--spec'], '--spec'), '--spec'))
        parent_id = values.get('--parent')
        key = values.get('--key') or f'create:{digest(spec)}:{parent_id or ""}'
        return {'study': service.create_study(spec, key, parent_id=parent_id)}

    if command == 'snapshot':
        return _artifact(service, values['--study'], 'snapshot')
    if command == 'analyze':
        return _artifact(service, values['--study'], 'analysis')
    if command == 'propose':
        return _artifact(service, values['--study'], 'proposal')

    if command == 'package':
        out = _contained(root, values['--out'], '--out')
        expected = values.get('--revision')
        if expected is not None:
            if not expected.isdigit():
                raise UsageError('--revision must be a positive integer')
            expected = int(expected)
        package = prepare_run_package(
            service, values['--study'], expected_revision=expected,
            lane=values.get('--lane', 'cpu'), deadline=values.get('--deadline'),
            idempotency_key=values.get('--key'))
        _write_json(out, package)
        return {'path': str(out), 'package': package, 'package_id': package['package_id'],
                'budget': package['budget'], 'lane': package['lane'],
                'deadline_required': package['deadline_required'],
                'deadline': package.get('deadline')}

    if command == 'reconcile':
        service.get_study(values['--study'])
        journal = DraftAttemptJournal(service)
        result = reconcile_study(values['--study'], _NoEvidenceProbe(), journal)
        result['pending'] = journal.unresolved(values['--study'])
        return result

    if command == 'decide':
        payload = _read_json(_contained(root, values['--payload'], '--payload'), '--payload')
        extra = set(payload) - {'outcome', 'rationale', 'revision'}
        if extra:
            raise StudyError(f'decision payload has unsupported fields: {sorted(extra)}')
        study = service.get_study(values['--study'])
        revision = payload.get('revision', study['revision'])
        if type(revision) is not int or revision < 1:
            raise StudyError('decision revision must be a positive integer')
        key = values.get('--key') or f'decide:{digest(payload)}'
        return {'decision': service.decide(values['--study'], revision,
                                           payload.get('outcome'), payload.get('rationale'), key)}

    if command == 'export':
        out = _contained(root, values['--out'], '--out')
        record = service.export_study(values['--study'])
        _write_json(out, record)
        return {'path': str(out), 'study_id': values['--study'],
                'revision': record['study']['revision'],
                'parent_id': record['parent_id'], 'children': record['children']}

    raise UsageError(f'unsupported command {command!r}')


def _emit_error(code, kind, message):
    print(canonical({'ok': False, 'error': {'code': code, 'type': kind, 'message': message}}))
    return code


def main(argv):
    """Entry point returning a stable nonzero exit code; never calls sys.exit."""
    try:
        command, values = _parse(argv)
        result = _dispatch(command, values)
        print(canonical({'ok': True, **result}))
        return EXIT_OK
    except UsageError as exc:
        return _emit_error(EXIT_USAGE, 'UsageError', str(exc))
    except StudyError as exc:
        return _emit_error(_STATUS_EXIT.get(exc.status_code, EXIT_INVALID),
                           type(exc).__name__, str(exc))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return _emit_error(EXIT_INVALID, type(exc).__name__, str(exc))


__all__ = [
    'EXIT_OK', 'EXIT_USAGE', 'EXIT_INVALID', 'EXIT_NOT_FOUND', 'EXIT_CONFLICT',
    'EXIT_UNAVAILABLE', 'UsageError', 'main',
]


if __name__ == '__main__':  # pragma: no cover - convenience for manual use
    sys.exit(main(sys.argv[1:]))
