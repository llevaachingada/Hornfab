"""B1 registry tests use isolated temporary paths and no solve machinery."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

from hornlab_search.studies.schema import Conflict, StudyError, Unavailable
from hornlab_search.studies.service import DraftAttemptJournal, StudyService

SPEC = {'protocol': 'bo-study-v1.1', 'task': {'name': 'fixture'}}


def test_revision_retry_and_stale(tmp_path):
    svc = StudyService(tmp_path)
    study = svc.create_study(SPEC, 'create')
    edited = {**SPEC, 'cohort': 'one'}
    result = svc.revise(study['id'], edited, 1, 'edit')
    assert svc.revise(study['id'], edited, 1, 'edit') == result
    with pytest.raises(Conflict):
        svc.revise(study['id'], SPEC, 1, 'different')
    with pytest.raises(Conflict):
        svc.revise(study['id'], SPEC, 1, 'edit')
    assert svc.get_study(study['id'])['revision'] == 2


def test_concurrent_idempotent_job_and_stale_retry(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'create')['id']
    def reserve(_):
        return svc.reserve_cpu_job(sid, 1, 'one', 'request-sha', 'analyze')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(reserve, range(4)))
    assert sum(created for _, created in results) == 1
    assert len({record['id'] for record, _ in results}) == 1
    job = results[0][0]
    svc.revise(sid, {**SPEC, 'task': {'name': 'new'}}, 1, 'revise')
    assert svc.reserve_cpu_job(sid, 1, 'one', 'request-sha', 'analyze')[0] == job
    with pytest.raises(Conflict):
        svc.reserve_cpu_job(sid, 1, 'other', 'request-sha', 'analyze')
    with pytest.raises(Conflict):
        svc.reserve_cpu_job(sid, 1, 'one', 'different', 'analyze')
    assert StudyService(tmp_path).get_cpu_job(sid, job['id']) == job
    with pytest.raises(Conflict):
        svc.compare_and_set_cpu_job(sid, job['id'], ['queued'], 'running', {}, 'stale-start')


def test_package_reference_is_checked_at_reservation_and_start(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    with pytest.raises(Unavailable):
        svc.reserve_cpu_job(sid, 1, 'bad', 'request', 'analyze', 'bad-hash')
    package = svc.attach_artifact(sid, 1, 'package', b'package', {}, 'package')
    job, _ = svc.reserve_cpu_job(sid, 1, 'good', 'request', 'analyze', package['sha256'])
    (svc.store.artifacts / package['sha256']).unlink()
    with pytest.raises(Unavailable):
        svc.compare_and_set_cpu_job(sid, job['id'], ['queued'], 'running', {}, 'start')


def test_job_state_cas_and_unknown_cannot_relaunch(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    job, _ = svc.reserve_cpu_job(sid, 1, 'j', 'hash', 'propose')
    running = svc.compare_and_set_cpu_job(sid, job['id'], ['queued'], 'running', {}, 'start')
    assert svc.compare_and_set_cpu_job(sid, job['id'], ['queued'], 'running', {}, 'start') == running
    svc.compare_and_set_cpu_job(sid, job['id'], ['running'], 'running', {'process_identity': 'pid'}, 'pid')
    svc.compare_and_set_cpu_job(sid, job['id'], ['running'], 'unknown', {}, 'unknown')
    with pytest.raises(StudyError):
        svc.compare_and_set_cpu_job(sid, job['id'], ['unknown'], 'running', {}, 'retry')
    assert svc.list_cpu_jobs(sid)[0]['status'] == 'unknown'


def test_cpu_bridge_uses_durable_registry_without_duplicate_dispatch(tmp_path):
    from hornlab_search.gui.study_jobs import StudyCpuJobs
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    artifact = svc.attach_artifact(sid, 1, 'package', b'package', {}, 'pkg')
    launches = []
    bridge = StudyCpuJobs(svc, dispatcher=lambda *args: launches.append(args) or {'test': 'identity'},
                          prerequisite=lambda *args: True, artifact_validator=lambda *args: True)
    request = {'kind': 'analyze', 'expected_revision': 1, 'idempotency_key': 'launch',
               'package_hash': artifact['sha256']}
    job = bridge.submit(sid, request)
    repeated = bridge.submit(sid, request)
    assert repeated['id'] == job['id'] and len(launches) == 1
    assert bridge.finish(sid, job['id'], exit_code=0, artifact_identity={'fixture': 'ok'})['status'] == 'complete'


def test_artifact_orphan_missing_corrupt_and_revision(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    sha = svc.store.publish(b'orphan')
    assert sha in svc.store.recovery_diagnostics()['unreferenced']
    artifact = svc.attach_artifact(sid, 1, 'snapshot', b'data', {}, 'a')
    assert svc.list_studies()[0]['id'] == sid
    assert svc.get_artifact_metadata(sid, 'snapshot')['dependency_status'] == 'unverified'
    assert svc.get_artifact_metadata(sid, 'missing')['status'] == 'missing'
    assert svc.store.read_artifact(artifact['sha256']) == b'data'
    svc.revise(sid, {**SPEC, 'cohort': 'changed'}, 1, 'rev')
    assert svc.get_artifact_metadata(sid, 'snapshot', 1)['status'] == 'stale'
    assert svc.attach_artifact(sid, 1, 'snapshot', b'data', {}, 'a') == artifact
    with pytest.raises(Conflict):
        svc.attach_artifact(sid, 1, 'model', b'old', {}, 'old')
    (svc.store.artifacts / artifact['sha256']).write_bytes(b'bad')
    with pytest.raises(Unavailable):
        svc.store.read_artifact(artifact['sha256'])
    assert svc.readiness(sid)['dispatch_authorized'] is False


def test_lineage_decision_and_migration_refusal(tmp_path):
    svc = StudyService(tmp_path)
    parent = svc.create_study(SPEC, 'p')['id']
    child = svc.create_study(SPEC, 'c', parent_id=parent)['id']
    assert svc.get_study(child)['parent_id'] == parent
    decision = svc.decide(child, 1, 'inconclusive', 'pilot only', 'd')
    assert decision['outcome'] == 'inconclusive'
    assert svc.get_study(child)['revision'] == 1
    with sqlite3.connect(svc.store.db) as conn:
        conn.execute('PRAGMA user_version=999')
    with pytest.raises(StudyError, match='newer'):
        StudyService(tmp_path)


def test_dependency_readiness_never_confuses_bytes_with_validation(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    snapshot = svc.attach_artifact(sid, 1, 'snapshot', b'snapshot', {}, 's')
    svc.attach_artifact(sid, 1, 'cohort', b'cohort', {'snapshot': snapshot['sha256']}, 'co')
    svc.attach_artifact(sid, 1, 'model', b'model', {'training': 'wrong'}, 'm')
    result = svc.readiness(sid)
    assert result['stages']['snapshot']['status'] == 'unknown'
    assert result['stages']['cohort']['integrity'] == 'verified'
    assert result['stages']['model']['status'] == 'stale'
    assert result['dispatch_authorized'] is False


def test_durable_journal_reservation_reconciliation_and_reopen(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    package = {'study_id': sid, 'package_id': 'p', 'spec_revision': 1,
               'execution_mode': 'adaptive_serial', 'lane': 'cpu', 'deadline': '2099-01-01T00:00:00Z',
               'budget': {'screen_calls': 1, 'verify_calls': 1, 'total_calls': 2, 'attempts': 4}}
    svc.attach_artifact(sid, 1, 'package', json.dumps(package).encode(), {}, 'p')
    journal = DraftAttemptJournal(svc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: journal.claim(package), range(2))) == [False, True]
    aid = journal.begin(package, {'kind': 'screen', 'solve_id': 's1'}, True)
    assert aid and journal.state('p')['reservations']['total_calls'] == 1
    journal.release('p', 'unknown')
    again = DraftAttemptJournal(StudyService(tmp_path))
    assert again.claim(package) is False
    with pytest.raises(StudyError):
        again.resolve(aid, {'call_status': 'called'})
    with pytest.raises(Conflict):
        again.resolve(aid, {'solve_id': 'wrong', 'call_status': 'called'})
    result = {'solve_id': 's1', 'call_status': 'called', 'outcome': 'success'}
    again.resolve(aid, result)
    again.resolve(aid, result)
    assert again.state('p')['total_calls'] == 1
    assert again.state('p')['reservations']['total_calls'] == 0
    assert again.claim(package)
    assert again.begin(package, {'kind': 'screen', 'solve_id': 's2'}, True) is None
    aid2 = again.begin(package, {'kind': 'audit', 'solve_id': 's3'}, True)
    again.finish(aid2, {'call_status': 'not_called', 'outcome': 'cheap_refusal'})
    assert again.state('p')['verify_calls'] == 0
    assert again.state('p')['attempts'] == 2


def test_verification_candidate_cap_counts_cache_hits_and_deduplicates_retries(tmp_path):
    svc = StudyService(tmp_path)
    sid = svc.create_study(SPEC, 'c')['id']
    package = {'study_id': sid, 'package_id': 'p', 'spec_revision': 1,
               'execution_mode': 'adaptive_serial', 'lane': 'cpu', 'deadline': '2099-01-01T00:00:00Z',
               'budget': {'screen_calls': 18, 'verify_calls': 6, 'total_calls': 24, 'attempts': 120}}
    svc.attach_artifact(sid, 1, 'package', json.dumps(package).encode(), {}, 'p')
    journal = DraftAttemptJournal(svc)
    assert journal.claim(package)
    for index in range(6):
        aid = journal.begin(package, {'kind': 'audit' if index % 2 else 'verify', 'solve_id': f's{index}'}, False)
        assert aid
        journal.finish(aid, {'outcome': 'cached', 'call_status': 'not_called'})
    assert journal.state('p')['verify_candidates'] == 6
    assert journal.state('p')['verify_calls'] == 0
    assert journal.begin(package, {'kind': 'verify', 'solve_id': 'new'}, False) is None
    retry = journal.begin(package, {'kind': 'verify', 'solve_id': 's0'}, False)
    assert retry
    journal.finish(retry, {'outcome': 'cached', 'call_status': 'not_called'})
    assert journal.state('p')['verify_candidates'] == 6
