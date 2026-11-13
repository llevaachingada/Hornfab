"""C2 crash/injection matrix and C3 revision/idempotency/concurrency invariants."""
from __future__ import annotations

import pytest

from b8_fake_study import (CanonicalJournal, CoupledEvaluator, NoEvidenceProbe,
                           ReplayEvaluator, ResultProbe, SCREEN_X, SPEC, _screen_result,
                           cached_result, seeded_package)
from hornlab_search.gui.server import App
from hornlab_search.gui.study_jobs import StudyCpuJobs
from hornlab_search.studies.lanes import StudyLane
from hornlab_search.studies.package import prepare_run_package
from hornlab_search.studies.reconcile import reconcile_study
from hornlab_search.studies.runner import run_package
from hornlab_search.studies.schema import Conflict
from hornlab_search.studies.service import StudyService


def _lane(tmp_path):
    return StudyLane(
        runs_root=tmp_path / 'runs',
        cpu_cache=tmp_path / 'cache' / 'cpu',
        gpu_cache=tmp_path / 'cache' / 'gpu',
        cpu_dataset=tmp_path / 'dataset' / 'cpu',
        gpu_dataset=tmp_path / 'dataset' / 'gpu',
    )


def _candidate(solve_id='screen-0', index=0):
    return {'kind': 'screen', 'solve_id': solve_id, 'geometry_id': solve_id,
            'x': SCREEN_X[index]}


# ---------------------------------------------------------------- C2 crash matrix

def test_crash_after_attempt_intent_never_redispatches(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    assert journal.claim(package)
    candidate = _candidate('intent-crash')
    attempt_id = journal.begin(package, candidate, True)
    assert attempt_id

    state = journal.state(package['package_id'])
    assert state['attempts'] == 1
    assert state['unresolved'] is True
    assert state['reservations'] == {'screen_calls': 1, 'verify_calls': 0, 'total_calls': 1}
    assert state['total_calls'] == 0

    reconciled = reconcile_study(sid, NoEvidenceProbe(), journal)
    assert reconciled == {'status': 'unknown', 'resolved': [], 'unknown': [attempt_id]}
    assert journal.begin(package, _candidate('another'), True) is None

    evaluator = CoupledEvaluator()
    result = run_package(package, evaluator, _lane(tmp_path), journal)
    assert result['status'] == 'launch_conflict_or_stale'
    assert evaluator.evaluate_calls == 0
    assert journal.state(package['package_id'])['reservations']['total_calls'] == 1


def test_crash_after_dispatch_start_stays_unknown_and_never_respends(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    evaluator = CoupledEvaluator()
    evaluator.raise_after_dispatch = True

    result = run_package(package, evaluator, _lane(tmp_path), journal)
    assert result['status'] == 'unknown'
    assert evaluator.evaluate_calls == 1
    state = journal.state(package['package_id'])
    assert state['attempts'] == 1
    assert state['unresolved'] is True
    assert state['reservations']['total_calls'] == 1
    assert state['total_calls'] == 0
    unresolved = journal.unresolved(sid)
    assert len(unresolved) == 1 and unresolved[0]['reserved'] is True

    second = CoupledEvaluator()
    again = run_package(package, second, _lane(tmp_path), journal)
    assert again['status'] == 'launch_conflict_or_stale'
    assert second.evaluate_calls == 0
    # Absence of evidence is not evidence of no call: reservation is retained.
    assert journal.state(package['package_id'])['reservations']['total_calls'] == 1
    assert reconcile_study(sid, NoEvidenceProbe(), journal)['status'] == 'unknown'


def test_crash_after_evaluator_persistence_recovers_known_result(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    evaluator = CoupledEvaluator()
    evaluator.raise_after_persistence = True

    result = run_package(package, evaluator, _lane(tmp_path), journal)
    assert result['status'] == 'unknown'
    attempt = journal.unresolved(sid)[0]
    persisted = evaluator.persisted['screen-0']

    probe = ResultProbe({attempt['attempt_id']: {
        'state': 'result', 'attempt_id': attempt['attempt_id'],
        'solve_id': attempt['solve_id'], 'result': persisted}})
    reconciled = reconcile_study(sid, probe, journal)
    assert reconciled == {'status': 'reconciled',
                          'resolved': [attempt['attempt_id']], 'unknown': []}
    state = journal.state(package['package_id'])
    assert state['total_calls'] == 1 and state['unresolved'] is False
    assert len(journal.observations(package['package_id'])) == 1

    replay = ReplayEvaluator(_candidate('screen-0'), cached_result(persisted))
    resumed = run_package(package, replay, _lane(tmp_path), journal)
    assert resumed['status'] == 'pool_exhausted'
    assert replay.evaluate_calls == 0
    state = journal.state(package['package_id'])
    assert state['total_calls'] == 1
    assert len(journal.observations(package['package_id'])) == 1


def test_crash_after_journal_result_recovers_without_rerun(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    evaluator = CoupledEvaluator()
    evaluator.raise_in_observe = True

    with pytest.raises(RuntimeError, match='observe'):
        run_package(package, evaluator, _lane(tmp_path), journal)

    state = journal.state(package['package_id'])
    assert state['total_calls'] == 1
    assert state['unresolved'] is False
    assert len(journal.observations(package['package_id'])) == 1
    persisted = evaluator.observed[0]

    replay = ReplayEvaluator(_candidate('screen-0'), cached_result(persisted))
    resumed = run_package(package, replay, _lane(tmp_path), journal)
    assert resumed['status'] == 'pool_exhausted'
    assert replay.evaluate_calls == 0
    assert journal.state(package['package_id'])['total_calls'] == 1
    assert len(journal.observations(package['package_id'])) == 1


def test_crash_after_registry_update_is_atomic_and_reconcilable(tmp_path, monkeypatch):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    assert journal.claim(package)
    candidate = _candidate('registry-crash')
    attempt_id = journal.begin(package, candidate, True)
    assert attempt_id
    result = _screen_result(candidate)

    original = service._event
    def failing_event(conn, study_id, kind, payload):
        if kind == 'attempt_resolved':
            raise RuntimeError('simulated registry update failure')
        return original(conn, study_id, kind, payload)

    monkeypatch.setattr(service, '_event', failing_event)
    with pytest.raises(RuntimeError, match='registry update'):
        journal.finish(attempt_id, result)
    monkeypatch.undo()

    # The whole transaction rolled back: the attempt is still uncertain.
    assert [a['attempt_id'] for a in journal.unresolved(sid)] == [attempt_id]
    state = journal.state(package['package_id'])
    assert state['total_calls'] == 0 and state['unresolved'] is True

    reconciled = reconcile_study(sid, ResultProbe({attempt_id: {
        'state': 'result', 'attempt_id': attempt_id, 'solve_id': candidate['solve_id'],
        'result': result}}), journal)
    assert reconciled['resolved'] == [attempt_id]
    state = journal.state(package['package_id'])
    assert state['total_calls'] == 1 and state['unresolved'] is False


def test_cached_already_verified_identity_is_rechecked_under_lane_lock(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    assert journal.claim(package)
    candidate = _candidate('screen-0')
    attempt_id = journal.begin(package, candidate, True)
    result = _screen_result(candidate)
    journal.finish(attempt_id, result)
    assert journal.state(package['package_id'])['total_calls'] == 1
    journal.release(package['package_id'], 'prior_run_released')

    lane = _lane(tmp_path)
    ownership = []
    replay = ReplayEvaluator(
        candidate, cached_result(result),
        lane_probe=lambda item: ownership.append(lane.runtime is not None))
    resumed = run_package(package, replay, lane, journal)
    assert resumed['status'] == 'pool_exhausted'
    assert replay.evaluate_calls == 0
    assert ownership == [True], 'identity recheck must happen while owning the lane'
    state = journal.state(package['package_id'])
    assert state['total_calls'] == 1
    assert state['reservations']['total_calls'] == 0
    assert len(journal.observations(package['package_id'])) == 1


# ------------------------------------------------------- C3 idempotency/concurrency

def _job_payload(package, key='click', kind='propose'):
    return {'kind': kind, 'expected_revision': 1, 'idempotency_key': key,
            'package_hash': package['package_id']}


def test_duplicate_queue_clicks_and_lost_response_return_one_job(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    calls = []
    bridge = StudyCpuJobs(
        service,
        dispatcher=lambda kind, study_id, job_id: calls.append(job_id) or {'pid': 4242},
        prerequisite=lambda *args: True)

    payload = _job_payload(package)
    first = bridge.submit(sid, payload)
    second = bridge.submit(sid, payload)
    assert first['id'] == second['id']
    assert first['status'] == 'running'
    assert len(calls) == 1
    assert len(service.list_cpu_jobs(sid)) == 1

    # A lost response retried through a fresh bridge must return the original job.
    retry_calls = []
    fresh = StudyCpuJobs(service,
                         dispatcher=lambda *a: retry_calls.append(a) or {'pid': 1},
                         prerequisite=lambda *args: True)
    retried = fresh.submit(sid, payload)
    assert retried['id'] == first['id'] and retry_calls == []
    assert len(service.list_cpu_jobs(sid)) == 1

    # Same key, different payload is a conflict, not a second job.
    with pytest.raises(Conflict):
        bridge.submit(sid, _job_payload(package, kind='analyze'))


def test_duplicate_create_post_and_stale_revision_conflict(tmp_path):
    service = StudyService(tmp_path / 'registry')
    app = App(tmp_path, runs=tmp_path / 'runs', study_service=service)
    body = {'spec': SPEC, 'idempotency_key': 'create-once'}
    first = app.post('/api/studies', body)
    second = app.post('/api/studies', body)
    assert first['id'] == second['id']

    with pytest.raises(Conflict):
        app.post('/api/studies', {'spec': {**SPEC, 'name': 'different'},
                                  'idempotency_key': 'create-once'})

    with pytest.raises(Conflict) as exc:
        app.post(f"/api/studies/{first['id']}/revise",
                 {'spec': {**SPEC, 'name': 'edit'}, 'expected_revision': 99,
                  'idempotency_key': 'stale-edit'})
    assert exc.value.status_code == 409


def test_stale_package_revision_blocks_claim_and_reprepare(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    assert journal.claim(package)
    journal.release(package['package_id'], 'test-release')

    service.revise(sid, {**SPEC, 'cohort': 'changed'}, 1, 'manual-edit')
    assert service.get_study(sid)['revision'] == 2
    assert journal.is_current(package) is False
    assert CanonicalJournal(service).claim(package) is False
    with pytest.raises(Conflict):
        prepare_run_package(service, sid, expected_revision=1,
                            deadline='2099-01-01T00:00:00Z', idempotency_key='stale-package')
    assert service.get_artifact_metadata(sid, 'package', revision=1)['status'] == 'stale'


def test_gui_restart_reconciliation_and_ambiguous_ownership(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    calls = []
    bridge = StudyCpuJobs(
        service,
        dispatcher=lambda *args: calls.append(args) or {'pid': 777},
        prerequisite=lambda *args: True)
    payload = _job_payload(package, key='restart')
    job = bridge.submit(sid, payload)
    assert job['status'] == 'running'

    restarted = bridge.reconcile_after_restart(sid)
    assert [item['status'] for item in restarted] == ['unknown']
    assert 'not established after restart' in restarted[0]['fields']['error']
    # A restart never relaunches the ambiguous job.
    again = bridge.submit(sid, payload)
    assert again['id'] == job['id'] and again['status'] == 'unknown'
    assert len(calls) == 1

    def ambiguous(*args):
        calls.append(args)
        raise RuntimeError('spawn outcome ambiguous')
    ambiguous_bridge = StudyCpuJobs(service, dispatcher=ambiguous,
                                    prerequisite=lambda *args: True)
    ambiguous_job = ambiguous_bridge.submit(sid, _job_payload(package, key='ambiguous'))
    assert ambiguous_job['status'] == 'unknown'
    assert 'dispatch outcome unknown' in ambiguous_job['fields']['error']
    assert ambiguous_bridge.reconcile_after_restart(sid)[0]['status'] == 'unknown'
    assert len(calls) == 2


def test_worker_retry_is_explicit_not_automatic(tmp_path):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    calls = []
    bridge = StudyCpuJobs(
        service,
        dispatcher=lambda *args: calls.append(args) or {'pid': 888},
        prerequisite=lambda *args: True)
    payload = _job_payload(package, key='worker-retry')
    job = bridge.submit(sid, payload)
    failed = bridge.finish(sid, job['id'], exit_code=3)
    assert failed['status'] == 'failed'
    assert 'exited 3' in failed['fields']['error']

    # Same idempotency key returns the failed job; it does not silently retry.
    repeated = bridge.submit(sid, payload)
    assert repeated['id'] == job['id'] and repeated['status'] == 'failed'
    assert len(calls) == 1

    # An explicit new request is the only way to spend another worker attempt.
    retry = bridge.submit(sid, _job_payload(package, key='worker-retry-2'))
    assert retry['id'] != job['id'] and retry['status'] == 'running'
    assert len(calls) == 2
