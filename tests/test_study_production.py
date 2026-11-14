"""Production adapters with real durable registry and instrumented pipeline boundary."""
from datetime import datetime, timezone, timedelta
import json
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.studies import builders
from hornlab_search.studies.package import prepare_run_package
from hornlab_search.studies.production import build_worker, execution_capability, _pool, _training
from hornlab_search.studies.runner import run_package
from hornlab_search.studies.service import StudyService
from hornlab_search.bo.data import CandidatePool, PoolCandidate
from hornlab_search.bo.policy import ProposalOutcome
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.types import Evaluation, SolveOutcome
from test_study_builders import _tiny_fixture, NATIVE_CONFIG


def _prepared(tmp_path, monkeypatch):
    service = StudyService(tmp_path / 'registry')
    spec = {'protocol': 'bo-study-v1.1', **_tiny_fixture(service.store.root)}
    from hornlab_search.search.evaluate import collect_lib_shas
    scores_path = __import__('pathlib').Path(spec['source']['scores_json'])
    scores = json.loads(scores_path.read_text(encoding='utf-8'))
    scores['selection'] = {'dependency_pins': collect_lib_shas()}
    scores_path.write_text(json.dumps(scores), encoding='utf-8')
    sid = service.create_study(spec, 'create')['id']
    builders.freeze_snapshot(service, sid, root=service.store.root)
    builders.build_training(service, sid, root=service.store.root)
    builders.build_analysis(service, sid, root=service.store.root)
    space = DesignSpace.from_config(load_config(NATIVE_CONFIG))
    candidates = []
    for i in range(8):
        full = np.full(len(space.keys()), .1 + .1 * i)
        design = space.denormalize(full)
        active = np.delete(full, space.keys().index('morph_exponent'))
        candidates.append(PoolCandidate(str(i), i, 17, active, full, design.hash(),
                                        design.hash(), 'spec', design.params, {}, {}))
    pool = CandidatePool('ok', 8, 17, (17,), tuple(candidates), {}, (), 'spec', 'fixture')
    from hornlab_search.bo import policy
    monkeypatch.setattr(policy, 'capability_status', lambda *a, **k: {'status': 'ok'})
    monkeypatch.setattr(policy, 'fit_and_propose', lambda *a, **k: ProposalOutcome(
        status='ok', reason='ok', policy='scalar', selection_reason='acquisition',
        proposal=candidates[0].as_dict(include_vectors=True), predicted=None,
        acquisition=None, fallback=False, verification_mode='scalar', library_versions={}))
    builders.build_proposal(service, sid, root=service.store.root, pool=pool)
    package = prepare_run_package(service, sid, lane='gpu',
        deadline=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    return service, package, candidates


def test_hash_bound_pool_and_training_round_trip(tmp_path, monkeypatch):
    service, package, candidates = _prepared(tmp_path, monkeypatch)
    restored = _pool(service, package['study_id'])
    assert [row.design_hash for row in restored.candidates] == [row.design_hash for row in candidates]
    training = _training(service, package['study_id'])
    assert training.n == 32 and training.status == 'ok'
    assert np.array_equal(training.Y.reshape(-1), -training.J.reshape(-1))


@pytest.mark.parametrize('traced', [False, True])
def test_production_worker_initial_proposal_call_count_and_lane_roots(tmp_path, monkeypatch, traced):
    service, package, candidates = _prepared(tmp_path, monkeypatch)
    from hornlab_search.search import evaluate as pipeline
    calls = []

    class Backend:
        def solve(self, *args):
            calls.append('solve')

        def solve_traced(self, *args):
            calls.append('traced')

    def evaluate(design, space, cfg, mode, directory, store, backend, *, ctx):
        assert directory.is_absolute()
        assert ctx.cache_dir == tmp_path / 'cache' / 'studies' / package['package_id']
        backend.solve_traced() if traced else backend.solve()
        return Evaluation(design.hash(), design, 'mesh', mode, 1.0, {'total': 1.0},
                          None, None, SolveOutcome(True, None, .1, None))

    monkeypatch.setattr(pipeline, 'evaluate', evaluate)
    from hornlab_search.objective.replay import ReplayResult
    monkeypatch.setattr('hornlab_search.objective.replay.replay_run_dir', lambda *args, **kwargs:
        ReplayResult('exact_complete', (), 'canonical-physical', 'canonical-metric', 'canonical-score',
                     4, 'stored', j=1.0, stored_j=1.0, parity_delta=0.0))
    evaluator, lane, journal = build_worker(service, package, root=tmp_path,
                                           backend_factory=lambda *a, **k: Backend())
    candidate = evaluator.next_candidate({'screen_calls': 0})
    assert candidate['candidate_id'] == candidates[0].candidate_id
    assert len(candidate['solve_id']) == 64
    assert journal.claim(package)
    with lane.owned('gpu', package):
        attempt = journal.begin(package, candidate, True)
        result = evaluator.evaluate(candidate, attempt)
        assert result['call_status'] == 'called'
        assert result['eligible'] and result['observed_j'] == 1.0
        assert result['physical_id'] == 'canonical-physical'
        assert result['score_id'] == 'canonical-score'
        journal.finish(attempt, result)
        cached = evaluator.lookup(candidate)
        assert cached['call_status'] == 'not_called'
    journal.release(package['package_id'], 'interrupted')
    assert len(calls) == 1
    assert journal.state(package['package_id'])['screen_calls'] == 1
    assert len(journal.load_progress(package['package_id'])['observations']) == 1


def test_full_production_journal_screen_verify_and_restore(tmp_path, monkeypatch):
    service, package, candidates = _prepared(tmp_path, monkeypatch)
    evaluator, lane, journal = build_worker(service, package, root=tmp_path)
    evaluator.fit_fn = lambda *args: SimpleNamespace(status='ok', reason=None)
    evaluator.propose_fn = lambda state: (
        candidates[evaluator.history.proposal_index].as_dict(include_vectors=True)
        if evaluator.history.proposal_index < len(candidates) else None)

    def evaluate(candidate, attempt_id):
        return {'solve_id': candidate['solve_id'], 'kind': candidate['kind'],
                'call_status': 'called', 'outcome': 'success', 'observed_j': float(candidate['params']['L_mm']),
                'eligible': candidate['kind'] == 'screen', 'geometry_id': candidate['geometry_id'],
                'physical_id': candidate['solve_id'], 'score_id': 'score:' + candidate['solve_id'],
                'x': candidate['x'], 'params': candidate['params'], 'physical_measurement': True}

    evaluator.evaluate = evaluate
    monkeypatch.setenv('HORNLAB_GPU_LOCK', 'refuse')
    result = run_package(package, evaluator, lane, journal)
    assert result['status'] == 'pool_exhausted'
    state = journal.state(package['package_id'])
    assert (state['screen_calls'], state['verify_calls'], state['total_calls']) == (8, 6, 14)
    assert len(evaluator._verified_geometry_ids) == 6
    restored, _, _ = build_worker(service, package, root=tmp_path)
    restored.fit_fn = evaluator.fit_fn
    assert restored.restore_progress(journal.load_progress(package['package_id']))
    assert restored.history.proposal_index == 8
    assert restored._verified_geometry_ids == evaluator._verified_geometry_ids
    assert restored.training_set.n == evaluator.training_set.n


@pytest.mark.parametrize('replay_mode', ['missing', 'incomplete', 'score_disagrees'])
def test_pipeline_score_without_complete_persisted_replay_never_trains(tmp_path, monkeypatch, replay_mode):
    service, package, _ = _prepared(tmp_path, monkeypatch)
    from hornlab_search.search import evaluate as pipeline
    from hornlab_search.objective.replay import ReplayResult

    class Backend:
        def solve(self):
            return None

    def evaluate(design, space, cfg, mode, directory, store, backend, *, ctx):
        backend.solve()
        return Evaluation(design.hash(), design, 'mesh', mode, 1.0, {'total': 1.0},
                          None, None, SolveOutcome(True, None, .1, None))

    def replay(*args, **kwargs):
        if replay_mode == 'missing':
            raise FileNotFoundError('pipeline artifacts absent')
        return ReplayResult('exact_complete' if replay_mode == 'score_disagrees' else 'supported_incomplete',
                            (), 'physical', 'metric', 'score', 4, 'stored', j=1.1)

    monkeypatch.setattr(pipeline, 'evaluate', evaluate)
    monkeypatch.setattr('hornlab_search.objective.replay.replay_run_dir', replay)
    evaluator, lane, _ = build_worker(service, package, root=tmp_path,
                                     backend_factory=lambda *a, **k: Backend())
    candidate = evaluator.next_candidate({'screen_calls': 0})
    original_n = evaluator.training_set.n
    with lane.owned('gpu', package):
        result = evaluator.evaluate(candidate, 'attempt-fixture')
    assert result['outcome'] == 'metric_failure'
    assert result['call_status'] == 'called'
    assert result['eligible'] is False and result['physical_measurement'] is False
    assert result['observed_j'] is None
    evaluator.observe(result)
    assert evaluator.training_set.n == original_n
    assert evaluator.lookup(candidate) is None


def test_changed_snapshot_config_refuses_before_solver(tmp_path, monkeypatch):
    service, package, candidates = _prepared(tmp_path, monkeypatch)
    monkeypatch.setattr('hornlab_search.studies.production.study_interpreter', lambda root: __import__('pathlib').Path(__import__('sys').executable))
    monkeypatch.setattr('hornlab_search.studies.production.importlib.util.find_spec', lambda name: object())
    snapshot = json.loads(service.store.read_artifact(package['artifacts']['snapshot']))
    snapshot['task']['config_sha256'] = '0' * 64
    original = service.store.read_artifact
    monkeypatch.setattr(service.store, 'read_artifact', lambda sha: json.dumps(snapshot).encode()
                        if sha == package['artifacts']['snapshot'] else original(sha))
    status = execution_capability(service, package, root=tmp_path)
    assert status['status'] == 'capability_missing'
    assert 'config changed' in status['detail']


def test_cli_execute_requires_explicit_flag(tmp_path):
    from hornlab_search.studies.cli import main
    assert main(['run', '--root', str(tmp_path), '--package', 'missing.json']) == 2


def test_reconcile_preserves_live_worker_and_releases_only_proven_dead(tmp_path, monkeypatch):
    from hornlab_search.studies.production import reconcile_production, _write
    service, package, candidates = _prepared(tmp_path, monkeypatch)
    evaluator, lane, journal = build_worker(service, package, root=tmp_path)
    assert journal.claim(package)
    candidate = evaluator.next_candidate({'screen_calls': 0})
    attempt = journal.begin(package, candidate, True)
    _write(service.store.root / 'workers' / package['package_id'] / 'process.json', {'pid': 123})
    monkeypatch.setattr('hornlab_search.studies.production._process_alive', lambda pid: True)
    assert reconcile_production(service, package['study_id'], root=tmp_path)['released_dead_workers'] == []
    monkeypatch.setattr('hornlab_search.studies.production._process_alive', lambda pid: False)
    result = reconcile_production(service, package['study_id'], root=tmp_path)
    assert result['status'] == 'unknown'
    assert result['released_dead_workers'] == [package['package_id']]
    assert not journal.claim(package)  # No evidence means no permission to repeat a solve.
    evidence = {'attempt_id': attempt, 'solve_id': candidate['solve_id'], 'kind': 'screen',
                'call_status': 'called', 'outcome': 'success', 'observed_j': 2.0,
                'physical_id': 'physical', 'score_id': 'score', 'eligible': True}
    _write(tmp_path / 'runs' / ('study-' + package['package_id'][:16]) / 'results' /
           (candidate['solve_id'] + '.json'), evidence)
    result = reconcile_production(service, package['study_id'], root=tmp_path)
    assert result['resolved'] == [attempt]
    assert journal.claim(package)
    assert journal.state(package['package_id'])['screen_calls'] == 1
    journal.release(package['package_id'], 'interrupted')


def test_cpu_builder_rejects_stale_captured_revision(tmp_path, monkeypatch):
    from hornlab_search.studies.cli import _build_chain
    from hornlab_search.studies.schema import Conflict
    service = StudyService(tmp_path)
    study = service.create_study({'protocol': 'bo-study-v1.1'}, 'create')
    with pytest.raises(Conflict, match='stale study revision'):
        _build_chain(service, study['id'], tmp_path, {'--expected-revision': '2'}, through='analysis')


def test_replay_configuration_and_policy_code_are_bound_before_dispatch(tmp_path, monkeypatch):
    service, package, _ = _prepared(tmp_path, monkeypatch)
    required = {'hornlab_search/objective/replay.py', 'hornlab_search/config.py',
                'hornlab_search/bo/acquisition.py', 'hornlab_search/bo/policy.py',
                'hornlab_search/bo/encoding.py', 'hornlab_search/search/links.py',
                'hornlab_search/metrics/compute.py'}
    assert required <= set(package['code_pins'])
    from hornlab_search.studies.package import package_hash
    package['code_pins']['hornlab_search/objective/replay.py'] = '0' * 64
    package['package_id'] = package_hash(package)
    status = execution_capability(service, package, root=tmp_path)
    assert status['status'] == 'capability_missing'
    assert 'objective/replay.py' in status['detail']


@pytest.mark.parametrize('pins_status', ['current', 'missing', 'changed'])
def test_execution_requires_current_measured_cohort_dependencies(tmp_path, monkeypatch, pins_status):
    service, package, _ = _prepared(tmp_path, monkeypatch)
    import sys
    from pathlib import Path
    from hornlab_search.studies import production
    original = production._json

    def read(service, sid, kind):
        value = original(service, sid, kind)
        if kind == 'training_manifest' and pins_status != 'current':
            if pins_status == 'missing':
                value['meta'].pop('measured_dependency_pins', None)
            else:
                value['meta']['measured_dependency_pins']['hornlab_beat_bem'] = 'old-solver-pin'
        return value

    monkeypatch.setattr(production, '_json', read)
    monkeypatch.setattr(production, 'study_interpreter', lambda root: Path(sys.executable))
    monkeypatch.setattr(production.importlib.util, 'find_spec', lambda name: object())
    status = execution_capability(service, package, root=tmp_path)
    assert status['status'] == ('ok' if pins_status == 'current' else 'capability_missing'), status
