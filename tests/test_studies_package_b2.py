"""B1/B2 package tests: temporary roots, synthetic artifacts, no solve machinery."""
from __future__ import annotations

import json

import pytest

from hornlab_search.studies.package import (EXECUTION_BUDGET, PACKAGE_KIND, STATUS_NOTE,
                                            package_hash, prepare_run_package, verify_package)
from hornlab_search.studies.schema import Conflict, StudyError, Unavailable, canonical, digest
from hornlab_search.studies.service import DraftAttemptJournal, StudyService

SPEC = {'protocol': 'bo-study-v1.1', 'task': {'name': 'fixture'}, 'cohort': 'fixture'}


def seed_study(root, *, spec=None):
    service = StudyService(root)
    study = service.create_study(spec or SPEC, 'create')
    sid = study['id']
    snapshot = service.attach_artifact(sid, 1, 'snapshot', b'{"snapshot":1}', {}, 'snapshot')
    model = service.attach_artifact(sid, 1, 'model', b'{"model":1}',
                                    {'snapshot': snapshot['sha256']}, 'model')
    proposal = service.attach_artifact(sid, 1, 'proposal', b'{"proposal":1}',
                                       {'model': model['sha256']}, 'proposal')
    return service, sid, {'snapshot': snapshot['sha256'], 'model': model['sha256'],
                          'proposal': proposal['sha256']}


def make_package(service, sid, **kwargs):
    options = {'lane': 'cpu', 'deadline': '2099-01-01T00:00:00Z', 'idempotency_key': 'pkg'}
    options.update(kwargs)
    return prepare_run_package(service, sid, **options)


def test_package_identity_budget_and_published_bytes(tmp_path):
    service, sid, artifacts = seed_study(tmp_path)
    package = make_package(service, sid)

    assert package['execution_mode'] == 'adaptive_serial'
    assert package['protocol'] == 'bo-study-v1.1'
    assert package['deadline_required'] is True
    assert package['budget'] == {'screen_calls': 18, 'verify_calls': 6,
                                 'total_calls': 24, 'attempts': 120}
    assert package['budget'] == EXECUTION_BUDGET
    assert package['lane'] == 'cpu'
    assert package['status_note'] == STATUS_NOTE
    assert package['artifacts'] == artifacts
    assert package['verification_policy']['finalists_max'] == 4
    assert package['verification_policy']['audit_samples'] == 2
    assert package['adaptive_policy']['permits_hash_linked_child_models'] is True
    assert package['adaptive_policy']['display_only_selection_invalidates'] is False

    body = {key: value for key, value in package.items() if key != 'package_id'}
    assert package['package_id'] == digest(body) == package_hash(package)
    assert verify_package(package) is package

    metadata = service.get_artifact_metadata(sid, PACKAGE_KIND)
    assert metadata['status'] == 'available'
    assert metadata['sha256'] == package['package_id']
    assert service.store.read_artifact(package['package_id']) == canonical(body).encode()
    assert service.store.read_artifact(package['package_id']) == canonical(
        {key: value for key, value in package.items() if key != 'package_id'}).encode()


def test_package_idempotency_and_conflicting_reuse(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    first = make_package(service, sid)
    repeated = make_package(service, sid)
    assert repeated == first
    assert service.store.recovery_diagnostics()['missing'] == []

    with pytest.raises(Conflict):
        prepare_run_package(service, sid, lane='gpu', deadline='2099-01-01T00:00:00Z',
                            idempotency_key='pkg')
    with pytest.raises(Conflict):
        # A second package for the same revision/kind must not be silently written.
        prepare_run_package(service, sid, lane='cpu', deadline='2099-01-01T00:00:00Z',
                            idempotency_key='another')


def test_manual_revision_change_invalidates_but_display_selection_does_not(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid)
    journal = DraftAttemptJournal(service)
    assert journal.claim(package)

    # Display-only selection appends an event; it must not bump spec_revision.
    service.append_event(sid, 'display_selection', {'candidate': 'c0'}, 'display')
    assert service.get_study(sid)['revision'] == 1
    assert make_package(service, sid) == package
    assert journal.is_current(package)
    journal.release(package['package_id'], 'display_only')

    service.revise(sid, {**SPEC, 'cohort': 'changed'}, 1, 'edit')
    assert service.get_study(sid)['revision'] == 2
    assert service.get_artifact_metadata(sid, PACKAGE_KIND, 1)['status'] == 'stale'
    with pytest.raises(Conflict):
        make_package(service, sid, expected_revision=1, idempotency_key='stale')
    assert DraftAttemptJournal(service).claim(package) is False


def test_missing_and_mismatched_artifacts_are_refused(tmp_path):
    service = StudyService(tmp_path)
    sid = service.create_study(SPEC, 'create')['id']
    with pytest.raises(Unavailable):
        prepare_run_package(service, sid, deadline='2099-01-01T00:00:00Z')

    snapshot = service.attach_artifact(sid, 1, 'snapshot', b'{"snapshot":1}', {}, 's')
    service.attach_artifact(sid, 1, 'model', b'{"model":1}',
                            {'snapshot': snapshot['sha256']}, 'm')
    with pytest.raises(Unavailable):
        prepare_run_package(service, sid, deadline='2099-01-01T00:00:00Z')

    service, sid, artifacts = seed_study(tmp_path / 'other')
    (service.store.artifacts / artifacts['proposal']).write_bytes(b'tampered')
    with pytest.raises(Unavailable):
        prepare_run_package(service, sid, deadline='2099-01-01T00:00:00Z')


def test_exact_budget_caps_count_new_calls_and_attempts(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid)
    journal = DraftAttemptJournal(service)
    assert journal.claim(package)

    for index in range(18):
        attempt = journal.begin(package, {'kind': 'screen', 'solve_id': f's{index}'}, True)
        assert attempt
        journal.finish(attempt, {'solve_id': f's{index}', 'call_status': 'called',
                                 'outcome': 'success'})
    assert journal.begin(package, {'kind': 'screen', 'solve_id': 'screen-over'},
                         True) is None

    for index in range(6):
        attempt = journal.begin(package, {'kind': 'verify', 'solve_id': f'v{index}'}, True)
        assert attempt
        journal.finish(attempt, {'solve_id': f'v{index}', 'call_status': 'called',
                                 'outcome': 'success'})
    assert journal.begin(package, {'kind': 'audit', 'solve_id': 'verify-over'},
                         True) is None
    assert journal.state(package['package_id'])['total_calls'] == 24

    # Cheap deterministic refusals consume attempts, not BEM calls.
    for index in range(96):
        attempt = journal.begin(package, {'kind': 'screen', 'solve_id': f'r{index}'}, False)
        assert attempt
        journal.finish(attempt, {'solve_id': f'r{index}', 'call_status': 'not_called',
                                 'outcome': 'cheap_refusal'})
    state = journal.state(package['package_id'])
    assert state['attempts'] == 120
    assert state['total_calls'] == 24
    assert journal.begin(package, {'kind': 'screen', 'solve_id': 'attempt-over'},
                         False) is None


def test_package_rejects_non_finite_or_wrong_budget_json(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid)
    forged = json.loads(json.dumps(package))
    forged['budget'] = {**forged['budget'], 'total_calls': 25}
    forged['package_id'] = digest({key: value for key, value in forged.items()
                                   if key != 'package_id'})
    with pytest.raises(StudyError):
        verify_package(forged)
    tampered = dict(package)
    tampered['lane'] = 'gpu'
    with pytest.raises(Unavailable):
        verify_package(tampered)
