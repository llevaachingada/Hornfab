"""Deterministic coupled fake evaluator + a contract-faithful test journal.

No mesher, BEM solver, GPU, subprocess or acoustic store is touched.  The
evaluator is a pure analytic fixture (same parameter vector -> same J/coverage/
ripple) used to exercise the real study service, runner, lane and CLI seams.

``CanonicalJournal`` is an alias for the real durable ``DraftAttemptJournal``.
The earlier body-vs-``package_id`` identity defect (service.py:390) was fixed in
commit 9b798f5 while this verification ran; ``tests/test_b8_regressions.py`` keeps
that behaviour as a regression guard.
"""
from __future__ import annotations

import json

from hornlab_search.studies.package import prepare_run_package
from hornlab_search.studies.runner import select_verification
from hornlab_search.studies.schema import canonical
from hornlab_search.studies.service import DraftAttemptJournal, StudyService

SPEC = {
    'protocol': 'bo-study-v1.1',
    'name': 'coupled fixture study',
    'question': 'Does the workflow preserve units, signs and prediction status?',
    'task': {'name': 'fixture-osse-task'},
    'cohort': 'fixture-cohort-v1',
    'policy': {'mode': 'adaptive_serial', 'protocol': 'bo-study-v1.1'},
    'pins': {'code_pins': {'fixture': '1'}},
}

REFERENCE = {'limits': [12.5, 1.25], 'spec_hash': 'a' * 64, 'frozen_at_snapshot': True}

SNAPSHOT = {
    'snapshot_id': 'snapshot-fixture-1',
    'brief': 'fixture-brief',
    'units': {'j': 'dimensionless', 'coverage_deg': 'degree', 'ripple_db': 'dB'},
    'objective': {'name': 'J', 'direction': 'minimize', 'score_version': 'v4-fixture'},
    'measured': True,
}

MODEL = {
    'model_id': 'model-fixture-1',
    'protocol': 'bo-study-v1.1',
    'training_ids': [f'screen-{i}' for i in range(8)],
    'device': 'cpu',
}

ANALYSIS = {
    'analysis_id': 'analysis-fixture-1',
    'method': 'fixture-coupled-analytic',
    'reference': REFERENCE,
    'units': SNAPSHOT['units'],
    'objective': SNAPSHOT['objective'],
}

# Fixed 8 screen points.  J is minimized and the four lowest J are the finalists.
SCREEN_X = [(0.05, 0.10), (0.15, 0.20), (0.25, 0.30), (0.35, 0.40),
            (0.45, 0.50), (0.55, 0.60), (0.65, 0.70), (0.75, 0.80)]
AUDIT_SEED = 20261112


def true_j(x):
    a, b = x
    return round(1.0 + 2.0 * (a - 0.05) ** 2 + 3.0 * (b - 0.10) ** 2, 9)


def true_coverage(x):
    a, b = x
    return round(4.0 + 10.0 * a + 2.0 * b, 9)


def true_ripple(x):
    a, b = x
    return round(0.30 + 0.8 * a + 0.5 * b, 9)


PROPOSAL = {
    'proposal_id': 'proposal-fixture-1',
    'model_id': MODEL['model_id'],
    'method': 'fixture_coupled_v1',
    'objective': SNAPSHOT['objective'],
    'units': SNAPSHOT['units'],
    'reference': REFERENCE,
    'predictions': [
        {'candidate_id': 'pred-0', 'solve_id': 'pred-0', 'x': [0.02, 0.08],
         'j': true_j([0.02, 0.08]), 'coverage_deg': true_coverage([0.02, 0.08]),
         'ripple_db': true_ripple([0.02, 0.08]), 'status': 'predicted', 'measured': False},
        {'candidate_id': 'pred-1', 'solve_id': 'pred-1', 'x': [0.08, 0.12],
         'j': true_j([0.08, 0.12]), 'coverage_deg': true_coverage([0.08, 0.12]),
         'ripple_db': true_ripple([0.08, 0.12]), 'status': 'predicted', 'measured': False},
    ],
    'acquisition': {'value': -0.25, 'units': 'log acquisition ranking diagnostic'},
}


def seed_study(root, spec=None):
    """Create a study with snapshot/cohort/analysis/model/proposal artifacts at rev 1."""
    service = StudyService(root)
    study = service.create_study(spec or SPEC, 'create-seed')
    sid = study['id']
    snapshot = service.attach_artifact(sid, 1, 'snapshot', canonical(SNAPSHOT).encode(), {}, 'snap')
    cohort = service.attach_artifact(sid, 1, 'cohort', canonical({'cohort': 'fixture'}).encode(),
                                     {'snapshot': snapshot['sha256']}, 'cohort')
    analysis = service.attach_artifact(sid, 1, 'analysis', canonical(ANALYSIS).encode(),
                                       {'snapshot': snapshot['sha256'], 'cohort': cohort['sha256']},
                                       'analysis')
    model = service.attach_artifact(sid, 1, 'model', canonical(MODEL).encode(),
                                    {'snapshot': snapshot['sha256']}, 'model')
    proposal = service.attach_artifact(sid, 1, 'proposal', canonical(PROPOSAL).encode(),
                                       {'model': model['sha256']}, 'proposal')
    hashes = {'snapshot': snapshot['sha256'], 'cohort': cohort['sha256'],
              'analysis': analysis['sha256'], 'model': model['sha256'],
              'proposal': proposal['sha256']}
    return service, sid, hashes


def seeded_package(root, *, lane='cpu', deadline='2099-01-01T00:00:00Z', key='package'):
    service, sid, hashes = seed_study(root)
    package = prepare_run_package(service, sid, lane=lane, deadline=deadline,
                                  idempotency_key=key)
    return service, sid, hashes, package


class CanonicalJournal(DraftAttemptJournal):
    """The real durable journal, marked as the v2 runner contract."""

    durable_contract = 'b5-journal-v2'


def _screen_result(candidate):
    x = candidate['x']
    return {
        'solve_id': candidate['solve_id'],
        'kind': candidate['kind'],
        'call_status': 'called',
        'outcome': 'success',
        'eligible': candidate['kind'] == 'screen',
        'physical_id': f"physical-{candidate['geometry_id']}",
        'score_id': 'score-fixture-v4',
        'observed_j': true_j(x),
        'coverage_deg': true_coverage(x),
        'ripple_db': true_ripple(x),
        'units': {'coverage_deg': 'degree', 'ripple_db': 'dB', 'j': 'dimensionless'},
    }


class CoupledEvaluator:
    """Evaluator contract fixture for the real serial runner."""

    def __init__(self, *, audit_seed=AUDIT_SEED, lane_probe=None):
        self.audit_seed = audit_seed
        self.lane_probe = lane_probe
        self.measured = []
        self.verified = []
        self.issued = set()
        self.evaluate_calls = 0
        self.lookup_calls = 0
        self.observed = []
        self.selection = None
        self.cached = {}
        self.persisted = {}
        self.raise_after_dispatch = False
        self.raise_after_persistence = False
        self.raise_in_observe = False
        self.on_evaluate = None
        self._x_by_geometry = {f'screen-{i}': x for i, x in enumerate(SCREEN_X)}
        self._plan = None

    # -- evaluator protocol -------------------------------------------------
    def next_candidate(self, state):
        plan = self._verification_plan()
        if self.selection is None and len(self.measured) >= len(SCREEN_X):
            rows = self._rows()
            self.selection = select_verification(rows, mode='scalar', audit_seed=self.audit_seed)
            plan = self._plan
        if plan is not None:
            for kind, geometry_id in plan:
                solve_id = f'{kind}-{geometry_id}'
                if solve_id not in self.issued:
                    self.issued.add(solve_id)
                    return {'kind': kind, 'solve_id': solve_id, 'geometry_id': geometry_id,
                            'x': self._x_by_geometry[geometry_id]}
            return None
        if len(self.measured) < len(SCREEN_X):
            index = len(self.measured)
            solve_id = f'screen-{index}'
            if solve_id in self.issued:
                return None
            self.issued.add(solve_id)
            return {'kind': 'screen', 'solve_id': solve_id, 'geometry_id': solve_id,
                    'x': SCREEN_X[index]}
        return None

    def _verification_plan(self):
        if self._plan is None and len(self.measured) >= len(SCREEN_X):
            rows = self._rows()
            self.selection = select_verification(rows, mode='scalar', audit_seed=self.audit_seed)
            self._plan = ([('verify', gid) for gid in self.selection['finalists']]
                          + [('audit', gid) for gid in self.selection['audits']])
        return self._plan

    def _rows(self):
        return [{'geometry_id': r['physical_id'].replace('physical-', ''),
                 'eligible': True, 'measured_screen': True, 'already_verified': False,
                 'j': r['observed_j']} for r in self.measured]

    def lookup(self, candidate):
        self.lookup_calls += 1
        if self.lane_probe is not None:
            self.lane_probe(candidate)
        return self.cached.get(candidate['solve_id'])

    def preflight(self, candidate):
        return None

    def evaluate(self, candidate, attempt_id):
        self.evaluate_calls += 1
        result = _screen_result(candidate)
        if self.on_evaluate is not None:
            self.on_evaluate(candidate, result)
        if self.raise_after_persistence:
            self.persisted[candidate['solve_id']] = result
            raise RuntimeError('simulated crash after evaluator persistence')
        if self.raise_after_dispatch:
            raise RuntimeError('simulated crash after dispatch start')
        return result

    def observe(self, result):
        self.observed.append(result)
        if result.get('kind') == 'screen' and result.get('eligible') is True:
            self.measured.append(result)
        else:
            self.verified.append(result)
        if self.raise_in_observe:
            raise RuntimeError('simulated crash before observe completed')
        return True

    def restore_progress(self, progress):
        self.measured = []
        for item in progress.get('observations', []):
            result = item.get('result') or {}
            if result.get('kind') == 'screen' and result.get('eligible') is True:
                self.measured.append(result)
        return True

    def proposal_rng_state(self):
        return {'fixture': 'coupled-v1', 'issued': sorted(self.issued),
                'audit_seed': self.audit_seed}


class ReplayEvaluator:
    """Return one exact candidate and its already-persisted result (no new call)."""

    def __init__(self, candidate, cached_result, lane_probe=None):
        self.candidate = candidate
        self.cached_result = cached_result
        self.lane_probe = lane_probe
        self.evaluate_calls = 0
        self.lookup_calls = 0
        self.issued = False
        self.observed = []
        self.lane_owned_at_lookup = False

    def next_candidate(self, state):
        if self.issued:
            return None
        self.issued = True
        return dict(self.candidate)

    def lookup(self, candidate):
        self.lookup_calls += 1
        if self.lane_probe is not None:
            self.lane_probe(candidate)
        self.lane_owned_at_lookup = True
        return dict(self.cached_result)

    def preflight(self, candidate):
        return None

    def evaluate(self, candidate, attempt_id):
        self.evaluate_calls += 1
        raise AssertionError('cached identity must never be re-evaluated')

    def observe(self, result):
        self.observed.append(result)
        return True

    def restore_progress(self, progress):
        return True

    def proposal_rng_state(self):
        return {'fixture': 'replay-v1'}


class ResultProbe:
    """Reconciliation probe returning injected exact-attempt evidence."""

    def __init__(self, evidence=None):
        self.evidence = evidence or {}

    def inspect(self, attempt):
        return self.evidence.get(attempt['attempt_id'], {'state': 'unknown'})


class NoEvidenceProbe:
    def inspect(self, attempt):
        return {'state': 'unknown'}


def cached_result(result):
    """Translate a persisted result into a no-new-call cache hit."""
    return {**result, 'call_status': 'not_called', 'outcome': 'cached'}
