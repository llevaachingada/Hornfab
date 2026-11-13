"""C1: one complete deterministic coupled fake-evaluator study.

Real service + GUI adapter/API + real serial runner and lane.  The only fixture is
the analytic evaluator and the test-only journal identity wrapper.
"""
from __future__ import annotations

import json

import pytest

from b8_fake_study import (ANALYSIS, AUDIT_SEED, CanonicalJournal, CoupledEvaluator,
                           MODEL, PROPOSAL, REFERENCE, SCREEN_X, SNAPSHOT, SPEC,
                           canonical, seeded_package, true_coverage, true_j, true_ripple)
from hornlab_search.gui.server import App
from hornlab_search.studies.lanes import StudyLane
from hornlab_search.studies.runner import run_package, select_verification
from hornlab_search.studies.schema import Conflict, NotFound
from hornlab_search.studies.service import StudyService


def _lane(tmp_path):
    return StudyLane(
        runs_root=tmp_path / 'runs',
        cpu_cache=tmp_path / 'cache' / 'cpu',
        gpu_cache=tmp_path / 'cache' / 'gpu',
        cpu_dataset=tmp_path / 'dataset' / 'cpu',
        gpu_dataset=tmp_path / 'dataset' / 'gpu',
    )


def test_complete_coupled_study_workflow(tmp_path):
    service, sid, hashes, package = seeded_package(tmp_path / 'registry')
    app = App(tmp_path, runs=tmp_path / 'runs', study_service=service)

    # create (real API POST) -------------------------------------------------
    created = app.post('/api/studies', {'spec': SPEC, 'idempotency_key': 'create-api'})
    assert created['revision'] == 1
    # The fixture study is created through the same service seam; GET it back.
    assert app.get(f'/api/studies/{sid}', {})['id'] == sid

    # analyze/evidence views -------------------------------------------------
    overview = app.get(f'/api/studies/{sid}/overview', {})
    assert overview['status'] == 'partial' and overview['revision'] == 1
    data = app.get(f'/api/studies/{sid}/data', {})
    assert data['data'] == SNAPSHOT
    explain = app.get(f'/api/studies/{sid}/explain', {})
    assert explain['data']['reference'] == REFERENCE
    assert app.get(f'/api/studies/{sid}/execute', {})['status'] == 'missing'

    # propose view keeps predicted rows and original units/signs -------------
    proposal_view = app.get(f'/api/studies/{sid}/propose', {})
    proposal = proposal_view['data']
    assert proposal['proposal_id'] == PROPOSAL['proposal_id']
    assert proposal['objective']['direction'] == 'minimize'
    assert proposal['reference'] == REFERENCE
    assert proposal['units'] == SNAPSHOT['units']
    for row in proposal['predictions']:
        assert row['measured'] is False and row['status'] == 'predicted'
        assert row['j'] == pytest.approx(true_j(row['x']))
        assert row['coverage_deg'] == pytest.approx(true_coverage(row['x']))
        assert row['ripple_db'] == pytest.approx(true_ripple(row['x']))
        # The display keeps J in its own signed original units, never -J.
        assert row['j'] > 0

    proposal_hash_before = service.get_artifact_metadata(sid, 'proposal')['sha256']

    # prepare package through the current service seam (no package API here) -
    assert package['execution_mode'] == 'adaptive_serial'
    assert package['artifacts']['snapshot'] == hashes['snapshot']
    assert package['artifacts']['model'] == hashes['model']
    assert package['artifacts']['proposal'] == hashes['proposal']

    # dry-run makes no calls / writes nothing ---------------------------------
    dry = run_package(package, None, None, None, dry_run=True)
    assert dry['status'] == 'dry_run'

    # simulated serial screen + verify/audit ---------------------------------
    journal = CanonicalJournal(service)
    evaluator = CoupledEvaluator()
    result = run_package(package, evaluator, _lane(tmp_path), journal)
    assert result['status'] == 'pool_exhausted', result

    state = journal.state(package['package_id'])
    assert state['attempts'] == 14
    assert state['screen_calls'] == 8
    assert state['verify_calls'] == 6
    assert state['total_calls'] == 14
    assert state['verify_candidates'] == 6
    assert state['unresolved'] is False
    assert evaluator.evaluate_calls == 14

    selection = evaluator.selection
    assert selection is not None
    assert len(selection['finalists']) == 4
    assert len(selection['audits']) == 2
    assert not set(selection['finalists']) & set(selection['audits'])
    assert selection['shortfall'] == 0 and selection['audit_shortfall'] == 0
    assert selection['audit_seed'] == AUDIT_SEED

    screens = sorted(evaluator.measured, key=lambda r: (r['observed_j'], r['physical_id']))
    expected_finalists = [r['physical_id'].replace('physical-', '') for r in screens[:4]]
    assert sorted(selection['finalists']) == sorted(expected_finalists)
    # Deterministic seeded audit choice over the remaining eligible screens.
    again = select_verification(
        [{'geometry_id': r['physical_id'].replace('physical-', ''), 'eligible': True,
          'measured_screen': True, 'already_verified': False, 'j': r['observed_j']}
         for r in evaluator.measured], mode='scalar', audit_seed=AUDIT_SEED)
    assert again['audits'] == selection['audits']
    assert again['finalists'] == selection['finalists']

    observations = journal.observations(package['package_id'])
    assert len(observations) == 8
    assert {o['candidate']['kind'] for o in observations} == {'screen'}
    measured_ids = {o['result']['physical_id'] for o in observations}
    assert measured_ids == {f'physical-screen-{i}' for i in range(8)}
    # Verification results are real measurements but not training observations.
    assert len(evaluator.verified) == 6
    for predicted in PROPOSAL['predictions']:
        assert predicted['candidate_id'] not in measured_ids
        assert predicted['solve_id'] not in {o['candidate']['solve_id'] for o in observations}

    # persist stage artifacts and project them through the API ---------------
    measured_rows = [{'physical_id': o['result']['physical_id'],
                      'solve_id': o['candidate']['solve_id'],
                      'j': o['result']['observed_j'],
                      'coverage_deg': o['result']['coverage_deg'],
                      'ripple_db': o['result']['ripple_db'],
                      'units': o['result']['units']} for o in observations]
    results_content = {'measured': measured_rows, 'screen_calls': state['screen_calls'],
                       'verify_calls': state['verify_calls'],
                       'finalists': selection['finalists'], 'audits': selection['audits'],
                       'predictions_are_not_measured': True}
    results = service.attach_artifact(sid, 1, 'results',
                                      canonical(results_content).encode(),
                                      {'package': package['package_id']}, 'results')
    verification_content = {'finalists': selection['finalists'], 'audits': selection['audits'],
                            'audit_seed': selection['audit_seed'],
                            'verified': [r['solve_id'] for r in evaluator.verified]}
    service.attach_artifact(sid, 1, 'verification', canonical(verification_content).encode(),
                            {'results': results['sha256']}, 'verification')

    execute_view = app.get(f'/api/studies/{sid}/execute', {})
    assert execute_view['data'] == results_content
    assert all(row['solve_id'].startswith('screen-') for row in execute_view['data']['measured'])
    assert not any(row['solve_id'].startswith('pred-') for row in execute_view['data']['measured'])

    # decide, export, child --------------------------------------------------
    decision = app.post(f'/api/studies/{sid}/decide',
                        {'expected_revision': 1, 'outcome': 'accept',
                         'rationale': 'coupled fixture validates workflow, not acoustics',
                         'idempotency_key': 'decide'})
    assert decision['outcome'] == 'accept' and decision['revision'] == 1
    service.attach_artifact(sid, 1, 'decision',
                            canonical({'outcome': 'accept',
                                       'rationale': 'coupled fixture validates workflow, not acoustics'}).encode(),
                            {'verification': service.get_artifact_metadata(sid, 'verification')['sha256']},
                            'decision-artifact')
    decide_view = app.get(f'/api/studies/{sid}/decide', {})
    assert decide_view['data']['outcome'] == 'accept'

    exported = service.export_study(sid)
    assert exported['protocol'] == 'bo-study-v1.1'
    assert exported['study']['revision'] == 1
    assert [d['outcome'] for d in exported['decisions']] == ['accept']
    kinds = {a['kind'] for a in exported['artifacts']}
    assert {'snapshot', 'cohort', 'analysis', 'model', 'proposal', 'package',
            'results', 'verification', 'decision'} <= kinds
    assert any(e['kind'] == 'package_claimed' for e in exported['events'])
    assert any(e['kind'] == 'attempt_resolved' for e in exported['events'])
    assert exported['children'] == []
    assert exported['recovery_diagnostics']['missing'] == []

    # Frozen reference and proposal identity never change as results arrive.
    assert service.get_artifact_metadata(sid, 'proposal')['sha256'] == proposal_hash_before
    stored_proposal = json.loads(service.store.read_artifact(proposal_hash_before))
    assert stored_proposal['reference'] == REFERENCE

    child = service.create_study({**SPEC, 'name': 'child study'}, 'create-child', parent_id=sid)
    assert child['parent_id'] == sid
    assert service.get_study(child['id'])['parent_id'] == sid
    assert service.export_study(sid)['children'] == [child['id']]

    # A stale manual edit after the package is no longer silent: launch conflicts.
    service.revise(sid, {**SPEC, 'cohort': 'changed'}, 1, 'edit-after-decision')
    assert service.get_study(sid)['revision'] == 2
    with pytest.raises(Conflict):
        service.revise(sid, SPEC, 1, 'stale-edit')


def test_package_api_is_not_invented_and_package_seam_is_current(tmp_path):
    """Record the seam that actually exists instead of inventing an endpoint."""
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    app = App(tmp_path, runs=tmp_path / 'runs', study_service=service)
    try:
        app.post(f'/api/studies/{sid}/package', {'idempotency_key': 'pkg'})
    except Exception as exc:  # StudyError("unsupported study operation")
        assert getattr(exc, 'status_code', 400) == 400
    else:
        raise AssertionError('unexpected package endpoint appeared; update this test')
    assert package['package_id'] == service.get_artifact_metadata(sid, 'package')['sha256']
    with pytest.raises(NotFound):
        service.get_study('does-not-exist')
