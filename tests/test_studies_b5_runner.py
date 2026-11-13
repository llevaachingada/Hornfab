from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from hornlab_search.studies.runner import ContractError, run_package
from hornlab_search.studies.reconcile import reconcile_study


def package():
    return {'study_id': 's', 'package_id': 'p', 'spec_revision': 1,
            'execution_mode': 'adaptive_serial', 'lane': 'cpu',
            'deadline': '2099-01-01T00:00:00Z',
            'budget': {'screen_calls': 18, 'verify_calls': 6, 'total_calls': 24, 'attempts': 120}}


class Journal:
    durable_contract = 'b5-journal-v1'
    def __init__(self):
        self.active = False; self.items = {}; self.counters = {'attempts': 0, 'unresolved': []}
        self.current = True; self.stopped = False; self.released = None
    def claim(self, p):
        if self.active or not self.current: return False
        self.active = True; return True
    def state(self, p): return dict(self.counters)
    def is_current(self, p): return self.current
    def cancelled(self, p): return self.stopped
    def begin(self, p, c, reserve):
        i = str(len(self.items)); self.items[i] = {'attempt_id': i, **c, 'reserved': reserve}
        self.counters['attempts'] += 1; self.counters['unresolved'].append(i); return i
    def finish(self, i, result):
        self.items[i]['result'] = result; self.counters['unresolved'].remove(i)
    def release(self, p, status): self.active = False; self.released = status
    def unresolved(self, s): return [self.items[i] for i in self.counters['unresolved']]
    def resolve(self, i, result): self.finish(i, result)


class Lane:
    lane_contract = 'b5-owned-lane-v1'
    def __init__(self): self.held = False; self.entered = 0
    @contextmanager
    def owned(self, lane, p):
        assert lane == 'cpu'; self.held = True; self.entered += 1
        try: yield
        finally: self.held = False


class Evaluator:
    def __init__(self, lane, crash=False): self.lane = lane; self.n = 0; self.crash = crash; self.calls = 0
    def next_candidate(self, state):
        if self.n == 3: return None
        self.n += 1; return {'kind': 'screen', 'solve_id': str(self.n)}
    def lookup(self, c):
        assert self.lane.held
        return {'cached': True} if c['solve_id'] == '1' else None
    def preflight(self, c): return {'refused': True} if c['solve_id'] == '2' else None
    def evaluate(self, c, i):
        assert self.lane.held; self.calls += 1
        if self.crash: raise RuntimeError('unknown boundary')
        return {'call_status': 'called'}
    def observe(self, r): return True


def test_dry_run_never_touches_adapters():
    p = package(); p.pop('deadline')
    assert run_package(p, None, None, None, dry_run=True) == {'status': 'dry_run', 'deadline_required': True}
    with pytest.raises(ContractError): run_package(p, None, None, None)


def test_serial_cache_refusal_and_solve():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    result = run_package(package(), e, lane, j)
    assert result['status'] == 'pool_exhausted' and e.calls == 1 and lane.entered == 1
    assert [v['reserved'] for v in j.items.values()] == [False, False, True]
    assert not j.counters['unresolved']


def test_unknown_reservation_blocks_resume_and_exact_reconcile():
    j = Journal(); lane = Lane(); e = Evaluator(lane, crash=True)
    assert run_package(package(), e, lane, j)['status'] == 'unknown'
    assert j.items['2']['reserved'] and j.counters['unresolved'] == ['2']
    assert run_package(package(), e, lane, j)['status'] == 'unknown'
    class Probe:
        def __init__(self, solve): self.solve = solve
        def inspect(self, attempt):
            return {'state': 'result', 'attempt_id': attempt['attempt_id'],
                    'solve_id': self.solve, 'result': {'call_status': 'called'}}
    assert reconcile_study('s', Probe('wrong'), j)['status'] == 'unknown'
    assert reconcile_study('s', Probe('3'), j)['status'] == 'reconciled'
    assert not j.counters['unresolved']


def test_duplicate_claim_and_revision_stop():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    j.active = True
    assert run_package(package(), e, lane, j)['status'] == 'launch_conflict_or_stale'
    assert lane.entered == 0 and e.calls == 0
    j.active = False; j.current = False
    assert run_package(package(), e, lane, j)['status'] == 'launch_conflict_or_stale'


def test_missing_durable_contract_fails_closed():
    assert run_package(package(), None, Lane(), object())['status'] == 'capability_missing'


def test_verification_selection_is_actual_distinct_and_seeded():
    from hornlab_search.studies.runner import select_verification
    rows = [{'geometry_id': str(i), 'eligible': True, 'measured_screen': True, 'already_verified': False, 'j': i}
            for i in range(7)]
    rows.append({'geometry_id': 'ignored', 'eligible': True, 'measured_screen': True, 'already_verified': True, 'j': -1})
    a = select_verification(rows, mode='scalar', audit_seed=8)
    assert a['finalists'] == ['0', '1', '2', '3'] and len(a['audits']) == 2
    assert a == select_verification(rows, mode='scalar', audit_seed=8)
    assert set(a['audits']).isdisjoint(a['finalists'])


def test_pareto_selection_requires_fixed_box_and_uses_nondominated():
    from hornlab_search.studies.runner import select_verification
    rows = [{'geometry_id': name, 'eligible': True, 'measured_screen': True, 'already_verified': False,
             'feasible': True, 'objectives': obj} for name, obj in
            [('a', [0., 1.]), ('b', [0.5, 0.5]), ('c', [1., 0.]), ('d', [0.9, 0.9])]]
    with pytest.raises(ContractError): select_verification(rows, mode='pareto', audit_seed=1)
    out = select_verification(rows, mode='pareto', audit_seed=1, objective_box=[[0, 1], [0, 1]])
    assert out['finalists'] == ['a', 'c', 'b'] and out['audits'] == ['d']


def test_ambiguous_dispatched_result_retains_reservation():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    e.evaluate = lambda candidate, attempt: {'status': 'unknown'}
    assert run_package(package(), e, lane, j)['status'] == 'unknown'
    assert j.counters['unresolved'] == ['2'] and j.items['2']['reserved']


def test_transactional_budget_refusal_never_dispatches():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    begin = j.begin
    def cap(p, c, reserve):
        return None if reserve else begin(p, c, reserve)
    j.begin = cap
    assert run_package(package(), e, lane, j)['status'] == 'budget_exhausted_or_stale'
    assert e.calls == 0 and len(j.items) == 2 and not j.counters['unresolved']


def test_crash_after_external_persistence_is_not_retried():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    saved = {}
    def persisted_then_crash(c, attempt):
        saved.update({'state': 'result', 'attempt_id': attempt, 'solve_id': c['solve_id'],
                      'result': {'call_status': 'called', 'outcome': 'success'}})
        raise RuntimeError('crash before journal completion')
    e.evaluate = persisted_then_crash
    assert run_package(package(), e, lane, j)['status'] == 'unknown'
    assert run_package(package(), e, lane, j)['status'] == 'unknown'
    class Probe:
        def inspect(self, attempt): return saved
    assert reconcile_study('s', Probe(), j)['status'] == 'reconciled'
    assert j.items['2']['result']['outcome'] == 'success'


def test_reconcile_ambiguous_call_status_keeps_reservation():
    j = Journal(); lane = Lane(); e = Evaluator(lane, crash=True)
    assert run_package(package(), e, lane, j)['status'] == 'unknown'
    class Probe:
        def inspect(self, a):
            return {'state': 'result', 'attempt_id': a['attempt_id'],
                    'solve_id': a['solve_id'], 'result': {'call_status': 'unknown'}}
    assert reconcile_study('s', Probe(), j)['status'] == 'unknown'
    assert j.counters['unresolved'] == ['2']


def test_pareto_audits_can_include_infeasible_actual_screen():
    from hornlab_search.studies.runner import select_verification
    rows = [{'geometry_id': 'a', 'eligible': True, 'measured_screen': True, 'already_verified': False,
             'feasible': True, 'objectives': [0, 0]},
            {'geometry_id': 'b', 'eligible': True, 'measured_screen': True, 'already_verified': False,
             'feasible': False, 'objectives': [1, 1]}]
    out = select_verification(rows, mode='pareto', audit_seed=3, objective_box=[[0, 2], [0, 2]])
    assert out['finalists'] == ['a'] and out['audits'] == ['b']


def test_two_launches_use_atomic_claim():
    from threading import Event, Lock, Thread
    j = Journal(); lock = Lock(); entered = Event(); release = Event()
    def claim(p):
        with lock:
            if j.active: return False
            j.active = True; return True
    j.claim = claim
    lane = Lane(); e = Evaluator(lane)
    original = e.next_candidate
    def block(state):
        entered.set(); assert release.wait(5); return original(state)
    e.next_candidate = block
    outcomes = []
    t = Thread(target=lambda: outcomes.append(run_package(package(), e, lane, j)))
    t.start(); assert entered.wait(5)
    assert run_package(package(), e, lane, j)['status'] == 'launch_conflict_or_stale'
    release.set(); t.join(5)
    assert not t.is_alive() and outcomes[0]['status'] == 'pool_exhausted'
    assert e.calls == 1


def test_journal_failure_after_evaluation_leaves_unknown_intent():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    finish = j.finish
    def fail_finish(attempt, result):
        if attempt == '2': raise OSError('simulated journal crash')
        finish(attempt, result)
    j.finish = fail_finish
    with pytest.raises(OSError): run_package(package(), e, lane, j)
    assert j.counters['unresolved'] == ['2'] and j.items['2']['reserved']
    assert j.released == 'interrupted'
    assert run_package(package(), e, lane, j)['status'] == 'unknown'


def test_revision_invalidated_during_preflight_stops_dispatch():
    j = Journal(); lane = Lane(); e = Evaluator(lane)
    original = e.preflight
    def invalidate(candidate):
        result = original(candidate)
        if candidate['solve_id'] == '3': j.current = False
        return result
    e.preflight = invalidate
    assert run_package(package(), e, lane, j)['status'] == 'stale'
    assert e.calls == 0 and len(j.items) == 2


def test_durable_draft_journal_fake_runner_and_recovery(tmp_path):
    import json
    from hornlab_search.studies.service import DraftAttemptJournal, StudyService
    service = StudyService(tmp_path)
    sid = service.create_study({'protocol': 'bo-study-v1.1', 'task': {'name': 'fake'}}, 'create')['id']
    p = {**package(), 'study_id': sid}
    service.attach_artifact(sid, 1, 'package', json.dumps(p).encode(), {}, 'package')
    class TestJournal(DraftAttemptJournal):
        durable_contract = 'b5-journal-v1'  # test-only: not production authorization
    j = TestJournal(service); lane = Lane(); evaluator = Evaluator(lane, crash=True)
    assert run_package(p, evaluator, lane, j)['status'] == 'unknown'
    reopened = TestJournal(StudyService(tmp_path))
    state = reopened.state('p')
    assert state['attempts'] == 3 and state['reservations']['total_calls'] == 1
    assert state['unresolved']
    assert run_package(p, evaluator, lane, reopened)['status'] == 'launch_conflict_or_stale'
    class Probe:
        def inspect(self, a):
            return {'state': 'result', 'attempt_id': a['attempt_id'], 'solve_id': a['solve_id'],
                    'result': {'solve_id': a['solve_id'], 'call_status': 'called', 'outcome': 'success'}}
    assert reconcile_study(sid, Probe(), reopened)['status'] == 'reconciled'
    state = TestJournal(StudyService(tmp_path)).state('p')
    assert state['total_calls'] == 1 and not state['unresolved']


def test_durable_journal_budget_before_backend(tmp_path):
    import json
    from hornlab_search.studies.service import DraftAttemptJournal, StudyService
    svc = StudyService(tmp_path)
    sid = svc.create_study({'protocol': 'bo-study-v1.1', 'task': {'name': 'fake'}}, 'create')['id']
    p = {**package(), 'study_id': sid, 'budget': {**package()['budget'], 'screen_calls': 0}}
    svc.attach_artifact(sid, 1, 'package', json.dumps(p).encode(), {}, 'package')
    class TestJournal(DraftAttemptJournal):
        durable_contract = 'b5-journal-v1'
    j = TestJournal(svc); lane = Lane(); evaluator = Evaluator(lane)
    assert run_package(p, evaluator, lane, j)['status'] == 'budget_exhausted_or_stale'
    assert evaluator.calls == 0 and j.state('p')['attempts'] == 2


def test_durable_journal_two_runners_one_claim(tmp_path):
    import json
    from threading import Event, Thread
    from hornlab_search.studies.service import DraftAttemptJournal, StudyService
    svc = StudyService(tmp_path)
    sid = svc.create_study({'protocol': 'bo-study-v1.1', 'task': {'name': 'fake'}}, 'create')['id']
    p = {**package(), 'study_id': sid}
    svc.attach_artifact(sid, 1, 'package', json.dumps(p).encode(), {}, 'package')
    class TestJournal(DraftAttemptJournal):
        durable_contract = 'b5-journal-v1'
    j = TestJournal(svc); lane = Lane(); evaluator = Evaluator(lane)
    entered, release = Event(), Event()
    original = evaluator.next_candidate
    def block(state):
        entered.set(); assert release.wait(5); return original(state)
    evaluator.next_candidate = block
    results = []
    thread = Thread(target=lambda: results.append(run_package(p, evaluator, lane, j)))
    thread.start(); assert entered.wait(5)
    assert run_package(p, evaluator, lane, TestJournal(StudyService(tmp_path)))['status'] == 'launch_conflict_or_stale'
    release.set(); thread.join(5)
    assert not thread.is_alive() and results[0]['status'] == 'pool_exhausted'
    assert evaluator.calls == 1


def test_durable_three_infrastructure_failures_stop(tmp_path):
    import json
    from hornlab_search.studies.service import DraftAttemptJournal, StudyService
    svc = StudyService(tmp_path)
    sid = svc.create_study({'protocol': 'bo-study-v1.1', 'task': {'name': 'fake'}}, 'create')['id']
    p = {**package(), 'study_id': sid}
    svc.attach_artifact(sid, 1, 'package', json.dumps(p).encode(), {}, 'package')
    class TestJournal(DraftAttemptJournal):
        durable_contract = 'b5-journal-v1'
    class Failing(Evaluator):
        def lookup(self, candidate): return None
        def preflight(self, candidate): return None
        def next_candidate(self, state):
            self.n += 1; return {'kind': 'screen', 'solve_id': str(self.n)}
        def evaluate(self, candidate, attempt):
            self.calls += 1
            return {'solve_id': candidate['solve_id'], 'call_status': 'called',
                    'outcome': 'infrastructure_failure'}
    lane = Lane(); evaluator = Failing(lane); journal = TestJournal(svc)
    assert run_package(p, evaluator, lane, journal)['status'] == 'infrastructure_failures'
    assert evaluator.calls == 3 and journal.state('p')['total_calls'] == 3


def test_durable_verify_and_total_caps_include_retries(tmp_path):
    import json
    from hornlab_search.studies.service import DraftAttemptJournal, StudyService
    svc = StudyService(tmp_path)
    sid = svc.create_study({'protocol': 'bo-study-v1.1', 'task': {'name': 'fake'}}, 'create')['id']
    p = {**package(), 'study_id': sid,
         'budget': {'screen_calls': 2, 'verify_calls': 1, 'total_calls': 2, 'attempts': 10}}
    svc.attach_artifact(sid, 1, 'package', json.dumps(p).encode(), {}, 'package')
    j = DraftAttemptJournal(svc)
    assert j.claim(p)
    first = j.begin(p, {'kind': 'screen', 'solve_id': 'retry'}, True)
    j.finish(first, {'call_status': 'called', 'outcome': 'solver_failure'})
    second = j.begin(p, {'kind': 'audit', 'solve_id': 'verify'}, True)
    j.finish(second, {'call_status': 'called', 'outcome': 'success'})
    assert j.begin(p, {'kind': 'verify', 'solve_id': 'another'}, True) is None
    assert j.begin(p, {'kind': 'screen', 'solve_id': 'retry'}, True) is None
    state = j.state('p')
    assert state['screen_calls'] == 1 and state['verify_calls'] == 1 and state['total_calls'] == 2
    j.release('p', 'budget_exhausted')


def test_concrete_cpu_lane_owns_lock_env_and_restores(tmp_path, monkeypatch):
    import os
    from hornlab_search.studies.lanes import StudyLane
    monkeypatch.delenv('HORNLAB_CPU_LANE_LOCK_OWNER', raising=False)
    monkeypatch.delenv('HORNLAB_GPU_LOCK_OWNER', raising=False)
    monkeypatch.setenv('HORNLAB_BEAT_WORKER_DIR', 'previous')
    lane = StudyLane(runs_root=tmp_path / 'runs', cpu_cache=tmp_path / 'cc',
                     gpu_cache=tmp_path / 'gc', cpu_dataset=tmp_path / 'cd',
                     gpu_dataset=tmp_path / 'gd')
    with lane.owned('cpu', package()) as runtime:
        assert (tmp_path / 'runs/.cpu.lane.lock').exists()
        assert os.environ['HORNLAB_BEAT_WORKER_DIR'] == str(tmp_path / 'runs/lanes/cpu/workers')
        assert runtime['cache_dir'] == tmp_path / 'cc' and runtime['dataset_dir'] == tmp_path / 'cd'
        with pytest.raises(RuntimeError):
            with lane.owned('cpu', package()): pass
    assert not (tmp_path / 'runs/.cpu.lane.lock').exists()
    assert os.environ['HORNLAB_BEAT_WORKER_DIR'] == 'previous' and lane.runtime is None


def test_concrete_gpu_lane_and_fake_bridge_hold_lock_for_full_run(tmp_path, monkeypatch):
    import os
    from hornlab_search.studies.lanes import FakeEvaluatorBridge, StudyLane
    monkeypatch.delenv('HORNLAB_CPU_LANE_LOCK_OWNER', raising=False)
    monkeypatch.delenv('HORNLAB_GPU_LOCK_OWNER', raising=False)
    lane = StudyLane(runs_root=tmp_path / 'runs', cpu_cache=tmp_path / 'cc',
                     gpu_cache=tmp_path / 'gc', cpu_dataset=tmp_path / 'cd',
                     gpu_dataset=tmp_path / 'gd')
    p = {**package(), 'lane': 'gpu'}; counter = []
    def assert_owned(runtime):
        assert (tmp_path / 'runs/.gpu.lock').exists()
        assert os.environ['HORNLAB_BEAT_WORKER_DIR'] == str(tmp_path / 'runs/lanes/gpu/workers')
        assert runtime['cache_dir'] == tmp_path / 'gc'
    def propose(state, runtime):
        assert_owned(runtime)
        if counter: return None
        counter.append('proposed'); return {'kind': 'screen', 'solve_id': 'one'}
    def lookup(c, runtime): assert_owned(runtime); return None
    def preflight(c, runtime): assert_owned(runtime); return None
    def evaluate(c, attempt, runtime):
        assert_owned(runtime); counter.append('called'); return {'call_status': 'called'}
    def observe(result, runtime): assert_owned(runtime); return True
    e = FakeEvaluatorBridge(lane, propose=propose, lookup=lookup, preflight=preflight,
                            evaluate=evaluate, observe=observe)
    assert run_package(p, e, lane, Journal())['status'] == 'pool_exhausted'
    assert counter == ['proposed', 'called'] and not (tmp_path / 'runs/.gpu.lock').exists()


def test_lane_cleanup_after_exception_never_runs_gpu_cleanup(tmp_path, monkeypatch):
    import os
    from hornlab_search.studies.lanes import StudyLane
    from hornlab_search.search import hygiene
    monkeypatch.delenv('HORNLAB_CPU_LANE_LOCK_OWNER', raising=False)
    monkeypatch.delenv('HORNLAB_GPU_LOCK_OWNER', raising=False)
    monkeypatch.setenv('HORNLAB_BEAT_WORKER_DIR', 'before')
    # The lane adapter has no dependency on cleanup; this guards future wiring.
    for name in ('clean_stale_hosts', 'gpu_clean', 'cleanup'):
        if hasattr(hygiene, name):
            monkeypatch.setattr(hygiene, name, lambda *a, **k: pytest.fail('unexpected cleanup'))
    lane = StudyLane(runs_root=tmp_path / 'runs', cpu_cache=tmp_path / 'cc',
                     gpu_cache=tmp_path / 'gc', cpu_dataset=tmp_path / 'cd',
                     gpu_dataset=tmp_path / 'gd')
    with pytest.raises(RuntimeError, match='injected'):
        with lane.owned('cpu', package()):
            raise RuntimeError('injected')
    assert not (tmp_path / 'runs/.cpu.lane.lock').exists()
    assert os.environ['HORNLAB_BEAT_WORKER_DIR'] == 'before'


def test_inherited_owner_refuses_nested_lock(tmp_path, monkeypatch):
    from hornlab_search.studies.lanes import StudyLane
    monkeypatch.setenv('HORNLAB_GPU_LOCK_OWNER', '12345')
    lane = StudyLane(runs_root=tmp_path / 'runs', cpu_cache=tmp_path / 'cc',
                     gpu_cache=tmp_path / 'gc', cpu_dataset=tmp_path / 'cd',
                     gpu_dataset=tmp_path / 'gd')
    with pytest.raises(RuntimeError, match='inherited'):
        with lane.owned('cpu', package()): pass
    assert not (tmp_path / 'runs/.cpu.lane.lock').exists()


def test_verification_excludes_missing_or_predicted_evidence():
    from hornlab_search.studies.runner import select_verification
    rows = [{'geometry_id': 'missing-j', 'eligible': True, 'measured_screen': True,
             'already_verified': False},
            {'geometry_id': 'prediction', 'eligible': True, 'measured_screen': False,
             'already_verified': False, 'j': 1}]
    out = select_verification(rows, mode='scalar', audit_seed=1)
    assert out['finalists'] == [] and out['audits'] == []
