"""CLI canary surface: prepare -> inspect (dry-run) -> parent-gated execute.

The fixtures reuse the synthetic real-metric study from
``test_studies_package_metric_real``.  No mesh, BEM/GPU, pipeline, dataset or queue call is
made; a counting fake backend is instrumented to prove the dry run is zero-call.
"""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from hornlab_search.studies import package as package_mod
from hornlab_search.studies import production
from hornlab_search.studies.cli import (EXIT_INVALID, EXIT_OK, EXIT_UNAVAILABLE,
                                        REAL_METRIC_RELEASE_ENV, main)
from test_studies_metric import _stages
from test_studies_metric_offline_package import _offline
from test_studies_package_metric_real import _approval_record, _real_stages


def invoke(argv, capsys):
    code = main(argv)
    payload = json.loads(capsys.readouterr().out)
    return code, payload


class _CountingBackend:
    """A fake backend whose every entry point counts; dry-run must leave it at zero."""

    def __init__(self):
        self.calls = 0
        self.executions = 0

    def evaluate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('backend evaluated during a zero-call path')

    def next_candidate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('backend proposed during a zero-call path')

    def release(self, *args, **kwargs):
        self.calls += 1

    def execute_study(self, *args, **kwargs):
        self.executions += 1
        raise AssertionError('execute_study called during a zero-call path')


def _instrument_no_backend(monkeypatch):
    """Install counting/failing substitutes AFTER fixture preparation (which may run git)."""
    fake = _CountingBackend()
    monkeypatch.setattr(production, 'build_worker', lambda *a, **k: fake)
    monkeypatch.setattr(production, 'execute_study', fake.execute_study)
    from hornlab_search.solve import base as solve_base
    monkeypatch.setattr(solve_base, 'get_backend', lambda *a, **k: fake)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('subprocess.run spawned'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Popen spawned'))
    monkeypatch.setattr(os, 'system', lambda *a, **k: pytest.fail('os.system spawned'))
    return fake


def _cli_root(tmp_path, monkeypatch):
    """The fixture's registry plus a held approvals record resolved from the temp root."""
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages, status='HELD_PENDING_PARENT_RELEASE',
                              owner_authorization={'authorized': False})
    monkeypatch.setattr(package_mod, 'repo_root', lambda: tmp_path)
    return stages, record


def _prepare_cli(stages, record, tmp_path, capsys, *extra):
    return invoke(['metric-package', '--root', str(tmp_path / 'registry'),
                   '--study', stages['sid'], '--out', 'package.json',
                   '--approvals-record', record,
                   '--budget-profile', 'metric-canary-8x2',
                   '--lane', 'gpu', '--deadline', '2099-01-01T00:00:00Z', *extra], capsys)


def test_cli_prepare_then_dry_run_is_zero_backend(tmp_path, capsys, monkeypatch):
    stages, record = _cli_root(tmp_path, monkeypatch)
    code, prepared = _prepare_cli(stages, record, tmp_path, capsys)
    assert code == EXIT_OK and prepared['ok'] is True
    package = prepared['package']
    assert package['metric']['provenance_mode'] == 'real_metric_v1'
    assert package['budget'] == {'screen_calls': 8, 'verify_calls': 2,
                                 'total_calls': 10, 'attempts': 60}
    assert prepared['approvals']['status'] == 'HELD_PENDING_PARENT_RELEASE'

    no_backend = _instrument_no_backend(monkeypatch)
    before = {p.relative_to(tmp_path).as_posix()
              for p in tmp_path.rglob('*') if p.is_file()}
    code, dry = invoke(['run', '--root', str(tmp_path / 'registry'),
                        '--package', 'package.json', '--dry-run'], capsys)
    assert code == EXIT_OK and dry['status'] == 'dry_run'
    assert dry['metric'] == 'real_metric'
    assert dry['plan']['backend_calls'] == 0
    assert dry['plan']['execute_authorized'] is False
    assert dry['plan']['screen_calls'] == 8 and dry['plan']['verify_calls'] == 2
    assert dry['plan']['refit_every'] == 4
    assert dry['plan']['approvals']['status'] == 'HELD_PENDING_PARENT_RELEASE'
    assert no_backend.calls == 0 and no_backend.executions == 0

    after = {p.relative_to(tmp_path).as_posix()
             for p in tmp_path.rglob('*') if p.is_file()}
    assert after == before
    assert not (tmp_path / 'runs').exists()
    assert not (tmp_path / 'cache').exists()


def test_cli_repeat_prepare_is_idempotent(tmp_path, capsys, monkeypatch):
    stages, record = _cli_root(tmp_path, monkeypatch)
    code, first = _prepare_cli(stages, record, tmp_path, capsys)
    assert code == EXIT_OK
    code, second = _prepare_cli(stages, record, tmp_path, capsys)
    assert code == EXIT_OK
    assert second['package_id'] == first['package_id']
    assert second['package'] == first['package']


@pytest.mark.parametrize('mutation', ['missing', 'artifact', 'adaptive', 'lane', 'deadline'])
def test_cli_prepare_refusals_are_typed(tmp_path, capsys, monkeypatch, mutation):
    stages, record = _cli_root(tmp_path, monkeypatch)
    profile, lane, deadline = 'metric-canary-8x2', 'gpu', '2099-01-01T00:00:00Z'
    expected = EXIT_INVALID
    if mutation == 'missing':
        record = 'approvals/missing.json'
        expected = EXIT_UNAVAILABLE
    elif mutation == 'artifact':
        record = _approval_record(tmp_path, stages, artifact_sha256='f' * 64)
        expected = EXIT_UNAVAILABLE
    elif mutation == 'adaptive':
        record = _approval_record(tmp_path, stages, profile='metric-adaptive-30x2')
        profile = 'metric-adaptive-30x2'
    elif mutation == 'lane':
        lane = 'cpu'
    elif mutation == 'deadline':
        deadline = '2000-01-01T00:00:00+00:00'
    code, out = invoke(['metric-package', '--root', str(tmp_path / 'registry'),
                        '--study', stages['sid'], '--out', 'package.json',
                        '--approvals-record', record,
                        '--budget-profile', profile,
                        '--lane', lane, '--deadline', deadline], capsys)
    assert code == expected and out['ok'] is False


def test_cli_offline_and_synthetic_packages_cannot_execute(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(package_mod, 'repo_root', lambda: tmp_path)
    offline = _offline(_stages(tmp_path / 'offs')['package'])
    (tmp_path / 'offline.json').write_text(json.dumps(offline), encoding='utf-8')
    synthetic = _stages(tmp_path / 'syn')['package']
    (tmp_path / 'synthetic.json').write_text(json.dumps(synthetic), encoding='utf-8')

    no_backend = _instrument_no_backend(monkeypatch)
    code, out = invoke(['run', '--root', str(tmp_path), '--package', 'offline.json',
                        '--execute'], capsys)
    assert code == EXIT_UNAVAILABLE
    assert 'real solver' in out['error']['message']

    code, out = invoke(['run', '--root', str(tmp_path), '--package', 'synthetic.json',
                        '--execute'], capsys)
    assert code == EXIT_UNAVAILABLE
    assert 'real solver' in out['error']['message']
    assert no_backend.calls == 0 and no_backend.executions == 0


def test_cli_held_record_blocks_execute_then_release_delegates(tmp_path, capsys, monkeypatch):
    stages, record = _cli_root(tmp_path, monkeypatch)
    code, _ = _prepare_cli(stages, record, tmp_path, capsys)
    assert code == EXIT_OK

    # Held record: refused before any executor construction.
    called = []
    monkeypatch.setattr(production, 'execute_study',
                        lambda service, package, root: called.append(package['package_id']) or {'status': 'ok'})
    monkeypatch.setenv(REAL_METRIC_RELEASE_ENV, '1')
    code, out = invoke(['run', '--root', str(tmp_path / 'registry'),
                        '--package', 'package.json', '--execute'], capsys)
    assert code == EXIT_UNAVAILABLE and 'HELD_PENDING_PARENT_RELEASE' in out['error']['message']
    assert called == []

    # Approve the record but leave the parent gate unset: still refused, still no executor.
    payload = json.loads((tmp_path / record).read_text(encoding='utf-8'))
    payload['status'] = 'APPROVED_FOR_CANARY'
    payload['owner_authorization']['authorized'] = True
    (tmp_path / record).write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.delenv(REAL_METRIC_RELEASE_ENV, raising=False)
    code, out = invoke(['run', '--root', str(tmp_path / 'registry'),
                        '--package', 'package.json', '--execute'], capsys)
    assert code == EXIT_UNAVAILABLE and REAL_METRIC_RELEASE_ENV in out['error']['message']
    assert called == []

    # Approved + owner-authorized + parent gate: the package is handed to the executor.
    monkeypatch.setenv(REAL_METRIC_RELEASE_ENV, '1')
    code, out = invoke(['run', '--root', str(tmp_path / 'registry'),
                        '--package', 'package.json', '--execute'], capsys)
    assert code == EXIT_OK
    assert called == [_status_package_id(tmp_path)]
    assert out['ok'] is True


def _status_package_id(root):
    package = json.loads((root / 'registry' / 'package.json').read_text(encoding='utf-8'))
    return package['package_id']
