"""Offline integrated B5 flow: temporary registry, fake acoustic outcomes only."""
from __future__ import annotations

import json
from pathlib import Path

from hornlab_search.studies.lanes import FakeEvaluatorBridge, StudyLane
from hornlab_search.studies.reconcile import reconcile_study
from hornlab_search.studies.runner import run_package, select_verification
from hornlab_search.studies.service import DraftAttemptJournal, StudyService


class _TestOnlyJournal(DraftAttemptJournal):
    # The draft journal deliberately has no production authorization marker.
    durable_contract = 'b5-journal-v1'


def test_integrated_fake_study_restart_reconcile_and_decide(tmp_path, monkeypatch):
    monkeypatch.delenv('HORNLAB_CPU_LANE_LOCK_OWNER', raising=False)
    monkeypatch.delenv('HORNLAB_GPU_LOCK_OWNER', raising=False)
    service = StudyService(tmp_path / 'registry')
    sid = service.create_study({'protocol': 'bo-study-v1.1', 'task': {'name': 'synthetic'}}, 'create')['id']
    p = {'study_id': sid, 'package_id': 'fake-package', 'spec_revision': 1,
         'execution_mode': 'adaptive_serial', 'lane': 'cpu', 'deadline': '2099-01-01T00:00:00Z',
         'budget': {'screen_calls': 18, 'verify_calls': 6, 'total_calls': 24, 'attempts': 120}}
    service.attach_artifact(sid, 1, 'package', json.dumps(p).encode(), {}, 'package')
    lane = StudyLane(runs_root=tmp_path / 'runs', cpu_cache=tmp_path / 'cc',
                     gpu_cache=tmp_path / 'gc', cpu_dataset=tmp_path / 'cd',
                     gpu_dataset=tmp_path / 'gd')
    queue = [{'kind': 'screen', 'solve_id': f's{i}', 'geometry_id': str(i)} for i in range(6)]
    observed = []; persisted = {}; calls = []
    def propose(state, runtime): return queue.pop(0) if queue else None
    def lookup(candidate, runtime): return None
    def preflight(candidate, runtime): return None
    def evaluate(candidate, attempt_id, runtime):
        assert Path(runtime['worker_dir']).parts[-2:] == ('cpu', 'workers')
        assert (tmp_path / 'runs/.cpu.lane.lock').exists()
        calls.append(candidate['solve_id'])
        result = {'solve_id': candidate['solve_id'], 'call_status': 'called', 'outcome': 'success',
                  'geometry_id': candidate['geometry_id'], 'j': float(candidate['geometry_id'])}
        if candidate['solve_id'] == 'v0':
            persisted.update({'state': 'result', 'attempt_id': attempt_id,
                              'solve_id': candidate['solve_id'], 'result': result})
            raise RuntimeError('simulated crash after external result persisted')
        return result
    def observe(result, runtime): observed.append(result); return True
    bridge = FakeEvaluatorBridge(lane, propose=propose, lookup=lookup, preflight=preflight,
                                 evaluate=evaluate, observe=observe)
    j = _TestOnlyJournal(service)
    assert run_package(p, bridge, lane, j)['status'] == 'pool_exhausted'
    assert len(observed) == 6 and j.state('fake-package')['screen_calls'] == 6
    screened = [{'geometry_id': r['geometry_id'], 'j': r['j'], 'eligible': True, 'measured_screen': True,
                 'already_verified': False} for r in observed]
    chosen = select_verification(screened, mode='scalar', audit_seed=42)
    assert chosen['finalists'] == ['0', '1', '2', '3']
    assert set(chosen['audits']) == {'4', '5'}
    queue.extend([{'kind': 'verify' if g in chosen['finalists'] else 'audit',
                   'solve_id': f'v{g}', 'geometry_id': g}
                  for g in chosen['finalists'] + chosen['audits']])
    assert run_package(p, bridge, lane, j)['status'] == 'unknown'
    restarted = _TestOnlyJournal(StudyService(tmp_path / 'registry'))
    assert restarted.state('fake-package')['reservations']['verify_calls'] == 1
    assert run_package(p, bridge, lane, restarted)['status'] == 'launch_conflict_or_stale'
    class Probe:
        def inspect(self, attempt): return persisted
    assert reconcile_study(sid, Probe(), restarted)['status'] == 'reconciled'
    # This fake test explicitly attaches the recovered observation before continuing;
    # real refit/replay wiring remains an integration prerequisite.
    observed.append(persisted['result'])
    assert run_package(p, bridge, lane, restarted)['status'] == 'pool_exhausted'
    state = restarted.state('fake-package')
    assert state['screen_calls'] == 6 and state['verify_calls'] == 6 and state['total_calls'] == 12
    assert calls.count('v0') == 1 and len(observed) == 12
    reopened = StudyService(tmp_path / 'registry')
    decision = reopened.decide(sid, 1, 'inconclusive', 'Synthetic offline fixture only.', 'decision')
    assert decision['outcome'] == 'inconclusive' and reopened.get_study(sid)['revision'] == 1
    assert not (tmp_path / 'runs/.cpu.lane.lock').exists()
