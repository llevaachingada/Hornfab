"""C6: CLI end-to-end leg plus duplicate-launch/stale-revision exit codes."""
from __future__ import annotations

import json

import pytest

from b8_fake_study import MODEL, PROPOSAL, SNAPSHOT, SPEC, canonical
from hornlab_search.studies import cli
from hornlab_search.studies.schema import Conflict
from hornlab_search.studies.service import StudyService


def _call(capsys, argv):
    code = cli.main(argv)
    lines = [line for line in capsys.readouterr().out.strip().splitlines() if line]
    payload = json.loads(lines[-1]) if lines else None
    return code, payload


def _write(path, value):
    path.write_text(canonical(value), encoding='utf-8')
    return path


def test_cli_end_to_end_create_package_dry_run_decide_export(tmp_path, capsys):
    root = tmp_path / 'study-root'
    root.mkdir()
    _write(root / 'spec.json', SPEC)

    code, payload = _call(capsys, ['validate', '--root', str(root), '--spec', 'spec.json'])
    assert code == cli.EXIT_OK and payload['ok'] is True

    code, created = _call(capsys, ['create', '--root', str(root), '--spec', 'spec.json',
                                   '--key', 'cli-create'])
    assert code == cli.EXIT_OK
    sid = created['study']['id']

    # Duplicate create with the same key/payload is the same study, not a second one.
    code, duplicate = _call(capsys, ['create', '--root', str(root), '--spec', 'spec.json',
                                     '--key', 'cli-create'])
    assert code == cli.EXIT_OK and duplicate['study']['id'] == sid
    assert len(StudyService(root).list_studies()) == 1

    # Same key with a different payload is a conflict (409 -> EXIT_CONFLICT).
    _write(root / 'spec2.json', {**SPEC, 'name': 'different study'})
    code, payload = _call(capsys, ['create', '--root', str(root), '--spec', 'spec2.json',
                                   '--key', 'cli-create'])
    assert code == cli.EXIT_CONFLICT and payload['ok'] is False

    service = StudyService(root)
    snapshot = service.attach_artifact(sid, 1, 'snapshot', canonical(SNAPSHOT).encode(), {}, 'snap')
    model = service.attach_artifact(sid, 1, 'model', canonical(MODEL).encode(),
                                    {'snapshot': snapshot['sha256']}, 'model')
    service.attach_artifact(sid, 1, 'proposal', canonical(PROPOSAL).encode(),
                            {'model': model['sha256']}, 'proposal')

    # Stale revision is a 409 at the service seam and a distinct CLI exit code.
    code, payload = _call(capsys, ['package', '--root', str(root), '--study', sid,
                                   '--out', 'stale.json', '--revision', '2',
                                   '--deadline', '2099-01-01T00:00:00Z', '--key', 'stale-package'])
    assert code == cli.EXIT_CONFLICT and payload['ok'] is False

    args = ['package', '--root', str(root), '--study', sid, '--out', 'package.json',
            '--revision', '1', '--lane', 'cpu',
            '--deadline', '2099-01-01T00:00:00Z', '--key', 'cli-package']
    code, packaged = _call(capsys, args)
    assert code == cli.EXIT_OK, packaged
    package_id = packaged['package_id']
    assert package_id == packaged['package']['package_id']
    assert packaged['package']['execution_mode'] == 'adaptive_serial'
    assert packaged['package']['budget'] == {'screen_calls': 18, 'verify_calls': 6,
                                             'total_calls': 24, 'attempts': 120}

    # Duplicate package preparation is idempotent and returns the same identity.
    duplicate_args = list(args)
    duplicate_args[duplicate_args.index('package.json')] = 'package-dup.json'
    code, duplicated = _call(capsys, duplicate_args)
    assert code == cli.EXIT_OK and duplicated['package_id'] == package_id

    # A duplicate dry-run launch is deterministic, spawns nothing and writes nothing.
    run_args = ['run', '--root', str(root), '--package', 'package.json', '--dry-run']
    code, first = _call(capsys, run_args)
    assert code == cli.EXIT_OK and first['status'] == 'dry_run'
    assert first['package_id'] == package_id
    code, second = _call(capsys, run_args)
    assert code == cli.EXIT_OK and second['package_id'] == package_id

    # Real scheduling is refused in this build; the exit code is explicit.
    code, payload = _call(capsys, ['run', '--root', str(root), '--package', 'package.json'])
    assert code == cli.EXIT_USAGE and payload['ok'] is False

    # A tampered package is unavailable (422 -> EXIT_UNAVAILABLE).
    tampered = json.loads((root / 'package.json').read_text(encoding='utf-8'))
    tampered['lane'] = 'gpu'
    _write(root / 'tampered.json', tampered)
    code, payload = _call(capsys, ['run', '--root', str(root), '--package', 'tampered.json',
                                   '--dry-run'])
    assert code == cli.EXIT_UNAVAILABLE and payload['ok'] is False

    # Missing inputs and path escapes use stable, separate codes.
    code, payload = _call(capsys, ['run', '--root', str(root), '--package', 'missing.json',
                                   '--dry-run'])
    assert code == cli.EXIT_INVALID and payload['ok'] is False
    code, payload = _call(capsys, ['run', '--root', str(root), '--package', '../escape.json',
                                   '--dry-run'])
    assert code == cli.EXIT_USAGE and payload['ok'] is False

    # Decide and export are validated actions, and a child study retains lineage.
    service.revise(sid, {**SPEC, 'cohort': 'changed'}, 1, 'cli-revise')
    _write(root / 'decision.json', {'outcome': 'inconclusive',
                                    'rationale': 'fixture only; no acoustic claim',
                                    'revision': 2})
    code, decided = _call(capsys, ['decide', '--root', str(root), '--study', sid,
                                   '--payload', 'decision.json', '--key', 'cli-decide'])
    assert code == cli.EXIT_OK and decided['decision']['outcome'] == 'inconclusive'

    code, child = _call(capsys, ['create', '--root', str(root), '--spec', 'spec.json',
                                 '--parent', sid, '--key', 'cli-child'])
    assert code == cli.EXIT_OK and child['study']['parent_id'] == sid
    child_id = child['study']['id']

    code, exported = _call(capsys, ['export', '--root', str(root), '--study', sid,
                                    '--out', 'export.json'])
    assert code == cli.EXIT_OK and exported['children'] == [child_id]
    record = json.loads((root / 'export.json').read_text(encoding='utf-8'))
    assert record['study']['revision'] == 2
    assert [d['outcome'] for d in record['decisions']] == ['inconclusive']

    # A stale decision revision is a conflict, never a silent overwrite.
    with pytest.raises(Conflict):
        service.decide(sid, 1, 'accept', 'stale decision', 'stale-decision')
