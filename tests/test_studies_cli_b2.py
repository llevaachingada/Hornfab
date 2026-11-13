"""B2 CLI tests: contained temp roots, strict argv, typed exit codes, zero-spawn dry run."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from hornlab_search.studies.cli import (EXIT_CONFLICT, EXIT_INVALID, EXIT_NOT_FOUND, EXIT_OK,
                                        EXIT_UNAVAILABLE, EXIT_USAGE, main)
from hornlab_search.studies.service import StudyService

SPEC = {'protocol': 'bo-study-v1.1', 'task': {'name': 'fixture'}, 'cohort': 'fixture'}


def invoke(argv, capsys):
    code = main(argv)
    payload = json.loads(capsys.readouterr().out)
    return code, payload


def seed_registry(root):
    service = StudyService(root)
    sid = service.create_study(SPEC, 'create')['id']
    snapshot = service.attach_artifact(sid, 1, 'snapshot', b'{"snapshot":1}', {}, 'snapshot')
    model = service.attach_artifact(sid, 1, 'model', b'{"model":1}',
                                    {'snapshot': snapshot['sha256']}, 'model')
    service.attach_artifact(sid, 1, 'proposal', b'{"proposal":1}',
                            {'model': model['sha256']}, 'proposal')
    return service, sid


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_cli_validate_create_child_decision_export(tmp_path, capsys):
    root = tmp_path / 'registry'
    write_json(root / 'study.json', SPEC)

    code, out = invoke(['validate', '--root', str(root), '--spec', 'study.json'], capsys)
    assert code == EXIT_OK and out['ok'] and out['status'] == 'valid' and len(out['spec_hash']) == 64

    code, created = invoke(['create', '--root', str(root), '--spec', 'study.json'], capsys)
    assert code == EXIT_OK and created['study']['revision'] == 1
    study_id = created['study']['id']
    repeated = invoke(['create', '--root', str(root), '--spec', 'study.json'], capsys)
    assert repeated[0] == EXIT_OK and repeated[1]['study']['id'] == study_id

    child = invoke(['create', '--root', str(root), '--spec', 'study.json',
                    '--parent', study_id], capsys)
    assert child[0] == EXIT_OK and child[1]['study']['parent_id'] == study_id

    write_json(root / 'decision.json', {'outcome': 'inconclusive', 'rationale': 'pilot only'})
    code, decided = invoke(['decide', '--root', str(root), '--study', study_id,
                            '--payload', 'decision.json'], capsys)
    assert code == EXIT_OK and decided['decision']['outcome'] == 'inconclusive'

    code, exported = invoke(['export', '--root', str(root), '--study', study_id,
                             '--out', 'exports/study.json'], capsys)
    assert code == EXIT_OK and exported['parent_id'] is None
    assert child[1]['study']['id'] in exported['children']
    record = json.loads((root / 'exports/study.json').read_text(encoding='utf-8'))
    assert record['study']['id'] == study_id
    assert record['decisions'][0]['outcome'] == 'inconclusive'
    assert isinstance(record['artifacts'], list)


def test_cli_typed_exit_codes_for_missing_and_unavailable(tmp_path, capsys):
    root = tmp_path / 'registry'
    write_json(root / 'study.json', SPEC)
    code, created = invoke(['create', '--root', str(root), '--spec', 'study.json'], capsys)
    study_id = created['study']['id']

    assert invoke(['snapshot', '--root', str(root), '--study', study_id], capsys)[0] == EXIT_UNAVAILABLE
    assert invoke(['analyze', '--root', str(root), '--study', study_id], capsys)[0] == EXIT_UNAVAILABLE
    assert invoke(['propose', '--root', str(root), '--study', study_id], capsys)[0] == EXIT_UNAVAILABLE
    assert invoke(['package', '--root', str(root), '--study', study_id,
                   '--out', 'pkg.json'], capsys)[0] == EXIT_UNAVAILABLE
    assert invoke(['snapshot', '--root', str(root), '--study', 'missing'], capsys)[0] == EXIT_NOT_FOUND
    assert invoke(['reconcile', '--root', str(root), '--study', 'missing'], capsys)[0] == EXIT_NOT_FOUND

    # A decision without a rationale is a typed invalid input (HTTP 400 analogue).
    write_json(root / 'bad-decision.json', {'outcome': 'accept'})
    code, out = invoke(['decide', '--root', str(root), '--study', study_id,
                        '--payload', 'bad-decision.json'], capsys)
    assert code == EXIT_INVALID and out['ok'] is False


def test_cli_strict_argv_and_path_traversal(tmp_path, capsys):
    root = tmp_path / 'registry'
    outside = tmp_path / 'outside.json'
    write_json(outside, SPEC)
    write_json(root / 'study.json', SPEC)

    assert invoke([], capsys)[0] == EXIT_USAGE
    assert invoke(['bogus'], capsys)[0] == EXIT_USAGE
    assert invoke(['validate', '--root', str(root)], capsys)[0] == EXIT_USAGE
    assert invoke(['validate', '--root', str(root), '--spec', 'study.json',
                   '--bogus', 'x'], capsys)[0] == EXIT_USAGE
    assert invoke(['validate', '--root', str(root), '--spec=study.json'], capsys)[0] == EXIT_USAGE
    assert invoke(['validate', '--root', str(root), '--spec', '../outside.json'], capsys)[0] == EXIT_USAGE
    assert invoke(['validate', '--root', str(root), '--spec', str(outside)], capsys)[0] == EXIT_USAGE
    assert invoke(['package', '--root', str(root), '--study', 'x',
                   '--out', '../package.json'], capsys)[0] == EXIT_USAGE
    # missing --dry-run is refused instead of pretending to schedule a real run
    write_json(root / 'package.json', {'package_id': 'x'})
    assert invoke(['run', '--root', str(root), '--package', 'package.json'], capsys)[0] == EXIT_USAGE


def test_cli_package_dry_run_is_zero_spawn_and_zero_write(tmp_path, capsys, monkeypatch):
    root = tmp_path / 'registry'
    service, study_id = seed_registry(root)

    code, packaged = invoke(['package', '--root', str(root), '--study', study_id,
                             '--out', 'out/package.json', '--lane', 'cpu',
                             '--deadline', '2099-01-01T00:00:00Z'], capsys)
    assert code == EXIT_OK
    package = packaged['package']
    assert package['budget'] == {'screen_calls': 18, 'verify_calls': 6,
                                 'total_calls': 24, 'attempts': 120}
    assert package['lane'] == 'cpu' and package['deadline_required'] is True
    assert package['execution_mode'] == 'adaptive_serial'
    assert package['package_id'] == json.loads(
        (root / 'out/package.json').read_text(encoding='utf-8'))['package_id']

    before = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('subprocess.run spawned'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Popen spawned'))
    monkeypatch.setattr(os, 'system', lambda *a, **k: pytest.fail('os.system spawned'))

    code, dry = invoke(['run', '--root', str(root), '--package', 'out/package.json',
                        '--dry-run'], capsys)
    assert code == EXIT_OK and dry['status'] == 'dry_run'
    assert dry['budget'] == package['budget']
    assert dry['lane'] == 'cpu' and dry['deadline_required'] is True
    assert dry['deadline_provided'] is True
    assert dry['package_id'] == package['package_id']

    after = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert after == before
    assert not (root / 'runs').exists()
    assert not (root / 'cache').exists()
    assert not (root / 'dataset').exists()


def test_cli_reconcile_reports_unknown_without_evidence(tmp_path, capsys):
    root = tmp_path / 'registry'
    service, study_id = seed_registry(root)
    code, packaged = invoke(['package', '--root', str(root), '--study', study_id,
                             '--out', 'package.json', '--deadline',
                             '2099-01-01T00:00:00Z'], capsys)
    assert code == EXIT_OK
    from hornlab_search.studies.service import DraftAttemptJournal
    journal = DraftAttemptJournal(service)
    assert journal.claim(packaged['package'])
    assert journal.begin(packaged['package'], {'kind': 'screen', 'solve_id': 's0'}, True)

    code, out = invoke(['reconcile', '--root', str(root), '--study', study_id], capsys)
    assert code == EXIT_OK and out['status'] == 'unknown'
    assert out['unknown'] and out['pending'][0]['solve_id'] == 's0'
