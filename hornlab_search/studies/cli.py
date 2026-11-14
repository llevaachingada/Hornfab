"""Validated study-workflow CLI (``bo-study-v1.1`` execution package lane).

Usage from the project interpreter::

    .venv\\Scripts\\python.exe -m hornlab_search.studies.cli validate --root ROOT --spec study.json
    ...
    .venv\\Scripts\\python.exe -m hornlab_search.studies.cli run --root ROOT --package package.json --dry-run

Artifact paths are resolved inside an explicit study root. ``run --dry-run``
acquires no lane and creates no solver. ``run --execute`` uses the production
worker and requires a current immutable package, dependencies and deadline.
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
    'snapshot': ({'--study'}, {'--root', '--key', '--config', '--brief', '--scores',
                               '--catalog', '--dataset-root'}),
    'analyze': ({'--study'}, {'--root', '--key', '--config', '--brief', '--scores',
                              '--catalog', '--dataset-root', '--expected-revision'}),
    'propose': ({'--study'}, {'--root', '--key', '--config', '--brief', '--scores',
                              '--catalog', '--dataset-root', '--policy', '--seed', '--expected-revision'}),
    'package': ({'--study', '--out'},
                {'--root', '--lane', '--deadline', '--key', '--revision'}),
    'run': ({'--package'}, {'--root', '--dry-run', '--execute', '--project-root'}),
    'reconcile': ({'--study'}, {'--root', '--project-root'}),
    'decide': ({'--study', '--payload'}, {'--root', '--key'}),
    'export': ({'--study', '--out'}, {'--root'}),
}

_BOOLEAN_FLAGS = {'--dry-run', '--execute'}


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


def _flag_path(root, values, flag):
    raw = values.get(flag)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise UsageError(f'{flag} requires a path')
    path = Path(raw)
    if path.is_absolute():
        return str(path)
    return str(_contained(root, raw, flag))


def _spec_with_flags(service, study_id, root, values):
    """Merge explicit CLI inputs into a copy of the current draft spec.

    This never revises or persists the study; it only supplies validated inputs
    to the builder for this invocation.
    """
    import copy
    spec = copy.deepcopy(service.get_study(study_id)['spec'])
    if not isinstance(spec, dict):
        raise StudyError('study spec is not an object')
    task = spec.get('task') if isinstance(spec.get('task'), dict) else {}
    source = spec.get('source') if isinstance(spec.get('source'), dict) else {}
    config = _flag_path(root, values, '--config')
    brief = _flag_path(root, values, '--brief')
    scores = _flag_path(root, values, '--scores')
    catalog = _flag_path(root, values, '--catalog')
    dataset = _flag_path(root, values, '--dataset-root')
    if config:
        task['config'] = config
    if brief:
        task['brief'] = brief
    if scores:
        source['scores_json'] = scores
    if catalog:
        source['catalog_csv'] = catalog
    if dataset:
        source['dataset_root'] = dataset
    if task:
        spec['task'] = task
    if source:
        spec['source'] = source
    if values.get('--policy') is not None:
        policy = spec.get('policy') if isinstance(spec.get('policy'), dict) else {}
        policy['proposal_policy'] = values['--policy']
        spec['policy'] = policy
    return spec


def _build_chain(service, study_id, root, values, *, through):
    """Build snapshot -> training -> analysis (and proposal when requested)."""
    from . import builders
    from .schema import Conflict
    base_service = service
    captured_revision = service.get_study(study_id)['revision']
    if values.get('--expected-revision') is not None:
        expected = values['--expected-revision']
        if not expected.isdigit() or int(expected) < 1:
            raise UsageError('--expected-revision must be a positive integer')
        if service.get_study(study_id)['revision'] != int(expected):
            raise Conflict('stale study revision before worker build')

    class RevisionBoundService:
        def __getattr__(self, name):
            return getattr(base_service, name)

        def get_study(self, requested_id):
            study = base_service.get_study(requested_id)
            if requested_id == study_id and study['revision'] != captured_revision:
                raise Conflict('study revision changed during worker build')
            return study

    service = RevisionBoundService()

    spec = _spec_with_flags(service, study_id, root, values)
    key = values.get('--key')

    def key_for(name):
        return f'{key}:{name}' if key else None

    snapshot = service.get_artifact_metadata(study_id, 'snapshot')
    if snapshot.get('status') != 'available':
        snapshot_result = builders.freeze_snapshot(
            service, study_id, root=root, spec=spec, idempotency_key=key_for('snapshot'))
    else:
        snapshot_result = {'snapshot': snapshot, 'artifact': snapshot, 'idempotent': True}
    if through == 'snapshot':
        return {'status': 'ok', 'snapshot': snapshot_result.get('artifact', snapshot),
                'artifact': snapshot_result.get('artifact', snapshot),
                'idempotent': snapshot_result.get('idempotent', False)}

    training_result = builders.build_training(
        service, study_id, root=root, spec=spec, idempotency_key=key_for('training'))
    if through == 'training':
        return {'status': 'ok', 'snapshot': snapshot_result.get('artifact'),
                'training': training_result['training'],
                'training_ids': training_result['training_ids'],
                'training_manifest': training_result['training_manifest'],
                'idempotent': training_result.get('idempotent', False)}

    analysis_result = builders.build_analysis(
        service, study_id, root=root, spec=spec, idempotency_key=key_for('analysis'))
    if through == 'analysis':
        return {'status': 'ok', 'snapshot': snapshot_result.get('artifact'),
                'training': training_result['training'],
                'training_ids': training_result['training_ids'],
                'training_manifest': training_result['training_manifest'],
                'analysis': analysis_result['artifact'],
                'idempotent': analysis_result.get('idempotent', False)}

    seed = values.get('--seed')
    if seed is not None:
        if not seed.isdigit():
            raise UsageError('--seed must be a non-negative integer')
        seed = int(seed)
    proposal_result = builders.build_proposal(
        service, study_id, root=root, spec=spec, policy=values.get('--policy'),
        seed=seed, idempotency_key=key_for('proposal'))
    return {
        'status': proposal_result.get('status', 'ok'),
        'snapshot': snapshot_result.get('artifact'),
        'training': training_result['training'],
        'training_ids': training_result['training_ids'],
        'training_manifest': training_result['training_manifest'],
        'analysis': analysis_result['artifact'],
        'model': proposal_result.get('model'),
        'pool': proposal_result.get('pool'),
        'proposal': proposal_result.get('proposal', proposal_result.get('artifact')),
        'artifact': proposal_result.get('artifact'),
        'proposal_policy': proposal_result.get('proposal_policy'),
        'verification_mode': proposal_result.get('verification_mode'),
        'reason': proposal_result.get('reason'),
        'idempotent': proposal_result.get('idempotent', False),
    }


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
        if bool(values.get('--dry-run')) == bool(values.get('--execute')):
            raise UsageError('run requires exactly one of --dry-run or --execute')
        package = verify_package(_read_json(
            _contained(root, values['--package'], '--package'), '--package'))
        if not values.get('--dry-run'):
            from .production import execute_study
            project_root = Path(values.get('--project-root', Path(__file__).resolve().parents[2])).resolve()
            result = execute_study(StudyService(root), package, root=project_root)
            if result.get('status') == 'capability_missing':
                raise Unavailable(result.get('detail') or result.get('reason'))
            return result
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
        return _build_chain(service, values['--study'], root, values, through='snapshot')
    if command == 'analyze':
        return _build_chain(service, values['--study'], root, values, through='analysis')
    if command == 'propose':
        return _build_chain(service, values['--study'], root, values, through='proposal')

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
        from .production import reconcile_production
        project_root = Path(values.get('--project-root', Path(__file__).resolve().parents[2])).resolve()
        result = reconcile_production(service, values['--study'], root=project_root)
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
