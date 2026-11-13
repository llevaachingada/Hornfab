"""Focused PipelineStudyEvaluator tests: injected fakes, no BEM/GPU/engine."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from hornlab_search.bo.propose import ProposalHistory
from hornlab_search.studies.evaluator import PipelineStudyEvaluator
from hornlab_search.studies.runner import encode_proposal_history, run_package
from hornlab_search.types import Design, Evaluation


def package(**overrides):
    value = {'study_id': 's', 'package_id': 'p', 'spec_revision': 1,
             'execution_mode': 'adaptive_serial', 'lane': 'cpu',
             'deadline': '2099-01-01T00:00:00Z',
             'budget': {'screen_calls': 18, 'verify_calls': 6,
                        'total_calls': 24, 'attempts': 120}}
    value.update(overrides)
    return value


class Lane:
    lane_contract = 'b5-owned-lane-v1'

    @contextmanager
    def owned(self, lane, p):
        yield None


class Journal:
    durable_contract = 'b5-journal-v1'

    def __init__(self):
        self.items = {}
        self.active = False
        self.current = True
        self.stopped = False
        self.released = None

    def claim(self, p):
        if self.active or not self.current:
            return False
        self.active = True
        return True

    def _calls(self, items=()):
        items = list(self.items.values()) if not items else list(items)
        called = [i for i in items if i.get('result', {}).get('call_status') == 'called']
        return {
            'screen_calls': sum(1 for i in called if i['kind'] == 'screen'),
            'verify_calls': sum(1 for i in called if i['kind'] != 'screen'),
            'total_calls': len(called),
        }

    def state(self, p):
        unknown = [i for i in self.items.values() if i['status'] == 'unknown']
        reservations = {'screen_calls': 0, 'verify_calls': 0, 'total_calls': 0}
        for item in unknown:
            if not item['reserved']:
                continue
            field = 'screen_calls' if item['kind'] == 'screen' else 'verify_calls'
            reservations[field] += 1
            reservations['total_calls'] += 1
        trailing = 0
        for item in sorted(self.items.values(), key=lambda i: i['id']):
            outcome = (item.get('result') or {}).get('outcome')
            if item['status'] == 'resolved' and outcome in ('solver_failure',
                                                             'infrastructure_failure'):
                trailing += 1
            elif item['status'] == 'resolved':
                trailing = 0
        return {'attempts': len(self.items), **self._calls(),
                'reservations': reservations,
                'verify_candidates': len({i['solve_id'] for i in self.items.values()
                                          if i['kind'] in ('verify', 'audit')}),
                'consecutive_failures': trailing,
                'unresolved': bool(unknown)}

    def is_current(self, p):
        return self.current

    def cancelled(self, p):
        return self.stopped

    def begin(self, p, candidate, reserve):
        attempt = str(len(self.items))
        self.items[attempt] = {'id': attempt, 'attempt_id': attempt, **candidate,
                               'reserved': bool(reserve), 'status': 'unknown'}
        return attempt

    def finish(self, attempt, result):
        item = self.items[attempt]
        if 'result' in item:
            return
        item['result'] = result
        item['status'] = 'resolved'

    def release(self, p, status):
        self.active = False
        self.released = status

    def unresolved(self, s):
        return [i for i in self.items.values() if i['status'] == 'unknown']

    def resolve(self, attempt, result):
        self.finish(attempt, result)


def screen_candidate(index):
    return {'candidate_id': f'c{index}', 'geometry_hash': f'g{index}',
            'design_hash': f'd{index}', 'intended_solve_hash': f's{index}',
            'params': {'i': index}, 'x': [index / 20.0, index / 21.0],
            'active_vector': [index / 20.0, index / 21.0], 'checks': {}}


def evaluation(design, **overrides):
    index = design.params.get('i', 0)
    values = {'design_hash': f'd{index}', 'design': design, 'mesh_hash': f'm{index}',
              'solve_hash': f's{index}', 'objective': 1.0 + index, 'terms': {'cov': 1.0, 'rip': 0.2},
              'metrics': None, 'mesh': None, 'outcome': None, 'cached': False, 'error': ''}
    values.update(overrides)
    return Evaluation(**values)


def fake_proposer(count=8):
    def propose(state):
        proposed = getattr(propose, 'count', 0)
        if proposed >= count:
            return None
        propose.count = proposed + 1
        return screen_candidate(proposed)
    propose.count = 0
    return propose


def evaluator(*, propose=None, evaluate=None, lookup=None, preflight=None, fit=None,
              package_value=None):
    return PipelineStudyEvaluator(
        None, package_value or package(),
        evaluate_fn=evaluate or (lambda design, attempt, runtime: evaluation(design)),
        lookup_fn=lookup, preflight_fn=preflight,
        propose_fn=propose or fake_proposer(),
        fit_fn=fit or (lambda training, seed: SimpleNamespace(status='ok', reason='ok')))


def test_full_serial_loop_screens_then_four_finalists_and_two_audits():
    evaluator_adapter = evaluator()
    journal = Journal()
    result = run_package(package(), evaluator_adapter, Lane(), journal)
    assert result['status'] == 'pool_exhausted'
    screens = [i for i in journal.items.values() if i['kind'] == 'screen']
    verify = [i for i in journal.items.values() if i['kind'] == 'verify']
    audit = [i for i in journal.items.values() if i['kind'] == 'audit']
    assert len(screens) == 8
    assert len(verify) == 4 and len(audit) == 2
    assert evaluator_adapter.selection['shortfall'] == 0
    assert evaluator_adapter.selection['audit_shortfall'] == 0
    # Verification candidates reuse actual measured screen geometries, never predictions.
    measured = {r['geometry_id'] for r in evaluator_adapter._measured}
    assert {i['geometry_id'] for i in verify} <= measured
    assert {i['geometry_id'] for i in audit} <= measured
    assert not {i['geometry_id'] for i in verify} & {i['geometry_id'] for i in audit}


def test_cache_hit_is_not_called_and_never_evaluated():
    calls = []
    cached = {'solve_id': 's0', 'kind': 'screen', 'geometry_id': 'g0',
              'call_status': 'not_called', 'outcome': 'cached', 'eligible': True,
              'observed_j': 1.0, 'physical_id': 'physical-g0', 'score_id': 'score-g0',
              'design_hash': 'd0', 'x': [0.0, 0.0], 'params': {'i': 0}}
    attempts = []
    def evaluate(design, attempt, runtime):
        calls.append(design.params.get('i'))
        attempts.append(attempt)
        return evaluation(design)
    adapter = evaluator(propose=fake_proposer(2),
                        evaluate=evaluate,
                        lookup=lambda candidate: cached if candidate['solve_id'] == 's0' else None)
    journal = Journal()
    run_package(package(), adapter, Lane(), journal)
    first = journal.items['0']
    assert first['reserved'] is False
    assert first['result']['call_status'] == 'not_called'
    assert first['result']['outcome'] == 'cached'
    assert '0' not in attempts


def test_cheap_refusal_consumes_attempt_not_a_call():
    def preflight(candidate):
        if candidate['solve_id'] == 's1':
            return {'solve_id': 's1', 'kind': 'screen', 'call_status': 'not_called',
                    'outcome': 'cheap_refusal', 'eligible': False,
                    'error': 'invalid_envelope: fixture'}
        return None
    adapter = evaluator(propose=fake_proposer(2), preflight=preflight)
    journal = Journal()
    run_package(package(), adapter, Lane(), journal)
    refused = journal.items['1']
    assert refused['reserved'] is False
    assert refused['result']['outcome'] == 'cheap_refusal'
    assert journal.state(package()['package_id'])['screen_calls'] == 1


def test_three_infrastructure_failures_stop_the_runner():
    def evaluate(design, attempt, runtime):
        return evaluation(design, error='solve_failed: simulated transient')
    adapter = evaluator(propose=fake_proposer(5), evaluate=evaluate)
    journal = Journal()
    result = run_package(package(), adapter, Lane(), journal)
    assert result['status'] == 'infrastructure_failures'
    assert journal.state(package()['package_id'])['consecutive_failures'] == 3


def test_numerical_model_failure_pauses_bo():
    def fit(training, seed):
        return SimpleNamespace(status='unavailable', reason='model_unavailable')
    adapter = evaluator(propose=fake_proposer(20), fit=fit)
    journal = Journal()
    result = run_package(package(), adapter, Lane(), journal)
    assert result['status'] == 'model_unavailable'
    assert journal.released == 'model_unavailable'


def test_dispatch_exception_is_unknown_and_keeps_the_reservation():
    def evaluate(design, attempt, runtime):
        raise RuntimeError('ambiguous dispatch boundary')
    adapter = evaluator(propose=fake_proposer(1), evaluate=evaluate)
    journal = Journal()
    result = run_package(package(), adapter, Lane(), journal)
    assert result['status'] == 'unknown'
    assert journal.items['0']['reserved'] is True
    assert journal.items['0']['status'] == 'unknown'


def test_duplicate_geometry_and_already_verified_are_excluded():
    adapter = evaluator()
    adapter._measured = [
        {'geometry_id': 'dup', 'eligible': True, 'measured_screen': True, 'observed_j': 1.0,
         'score_id': 'x', 'outcome': 'success'},
        {'geometry_id': 'dup', 'eligible': True, 'measured_screen': True, 'observed_j': 2.0,
         'score_id': 'y', 'outcome': 'success'},
        {'geometry_id': 'a', 'eligible': True, 'measured_screen': True, 'observed_j': 3.0,
         'score_id': 'z', 'outcome': 'success'},
        {'geometry_id': 'b', 'eligible': True, 'measured_screen': True, 'observed_j': 4.0,
         'score_id': 'w', 'outcome': 'success'},
        {'geometry_id': 'already', 'eligible': True, 'measured_screen': True,
         'observed_j': 5.0, 'score_id': 'v', 'outcome': 'success'},
    ]
    adapter._verified_geometry_ids = {'already'}
    adapter._build_verification_plan()
    planned = {gid for _kind, gid in adapter._plan}
    assert 'dup' not in planned and 'already' not in planned
    assert planned == {'a', 'b'} or planned == {'a', 'b'}


def test_restore_progress_preserves_cadence_and_verified_identities():
    adapter = evaluator()
    state = encode_proposal_history(
        ProposalHistory(proposal_index=3),
        {'screens_exhausted': True, 'screen_index': 3,
         'verified_geometry_ids': ['g2']})
    assert adapter.restore_progress({'proposal_index': 3, 'rng_state': state,
                                     'observations': []}) is True
    assert adapter.history.proposal_index == 3
    assert adapter.screen_index == 3
    assert adapter._screens_exhausted is True
    assert adapter._verified_geometry_ids == {'g2'}
    restored = adapter.proposal_rng_state()
    assert restored['proposal_history']['proposal_index'] == 3
    assert restored['rng_state']['screens_exhausted'] is True


def test_capability_missing_without_an_evaluator_is_never_a_fake_candidate():
    adapter = PipelineStudyEvaluator(None, package(), propose_fn=fake_proposer())
    status = adapter.capability_status()
    assert status['status'] == 'capability_missing'
    assert 'evaluate_fn' in status['missing']
    assert run_package(package(), adapter, Lane(), Journal())['status'] == 'capability_missing'
