"""Serial study worker using the ordinary HornLab evaluation/persistence pipeline.

Importing this module does not import BoTorch, acquire a lane or construct a solver.
The GUI launches this worker in its own process; cancellation is cooperative.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import math
from pathlib import Path
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone

from .schema import Unavailable, canonical
from .package import verify_package
from .service import DraftAttemptJournal


def study_interpreter(root):
    """Prefer the current interpreter, otherwise the sanctioned isolated bayes env."""
    if all(importlib.util.find_spec(name) is not None for name in ('torch', 'botorch', 'gpytorch', 'hornlab_mesher')):
        return Path(sys.executable)
    candidate = Path(root).resolve().parent / 'oc-wt' / 'bo-study' / 'bayes-venv' / 'Scripts' / 'python.exe'
    return candidate if candidate.is_file() else Path(sys.executable)


def _json(service, study_id, kind):
    meta = service.get_artifact_metadata(study_id, kind)
    if meta.get('status') != 'available':
        raise Unavailable(f'{kind} artifact unavailable')
    return json.loads(service.store.read_artifact(meta['sha256']))


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


#: Policies the production worker can execute.  Pareto additionally needs frozen bindings.
#: ``metric_composite_v1`` is deliberately NOT appended here: it is a package-gated route with
#: its own explicit ``real_metric_v1`` contract (see :func:`execution_capability`).
PRODUCTION_POLICIES = ('scalar', 'turbo', 'pareto')

METRIC_POLICY = 'metric_composite_v1'
REAL_METRIC_PROVENANCE = 'real_metric_v1'


def objective_admission(cfg, task):
    """Return ``None`` when the resolved objective is admitted, else a refusal reason.

    v4/v7 keep their historical blanket admission.  v10/v11 are OPT-IN: the resolved config and
    brief must be the exact pair of a registered study task in ``studies.builders._TASK_REGISTRY``
    AND the version-specific metric policy must freeze for that brief.  Every other version is
    refused.  This is a pure unit-level check: it reads YAML and freezes a policy identity, never a
    solver.
    """
    version = int(getattr(cfg, 'objective_version', -1))
    if version in (4, 7):
        return None
    from . import builders
    if version not in builders.registered_objective_versions():
        return ('production worker supports objective v4/v7 and registered v10/v11 tasks only; '
                f'got v{version}')
    task = task if isinstance(task, dict) else {}
    match = builders.registered_task_match(version, task.get('config'), task.get('brief'))
    if match is None:
        return (f'objective v{version} is admitted only through a registered study task '
                '(exact config/brief pair or a derived config with unchanged task identity); '
                'this task is not registered')
    entry = match['entry']
    try:
        import numpy as np
        from hornlab_search.bo.metrics import freeze_metric_policy_for_version
        from hornlab_search.objective import replay
        brief = replay.brief_from_config(entry['config'])
        if int(brief.objective_version) != version:
            return 'registered task config and brief disagree on objective version'
        target = brief.target
        grid = np.asarray([float(target.band_lo_hz), float(target.band_hi_hz)])
        freeze_metric_policy_for_version(brief, grid)
    except (ValueError, TypeError, OSError) as exc:
        return f'registered task metric policy cannot be frozen: {exc}'
    return None


def pareto_bindings(service, sid, proposal=None):
    '''Return the frozen Pareto bindings or raise ``Unavailable`` naming what is missing.

    Requires the proposal to bind a ``pareto_metrics`` artifact (dependency hash) that carries
    the frozen metric policy (payload + matching hash), the frozen hypervolume reference and
    complete per-row metric observations for the training cohort.
    '''
    proposal = proposal if proposal is not None else _json(service, sid, 'proposal')
    binding = proposal.get('pareto') if isinstance(proposal, dict) else None
    if not isinstance(binding, dict) or not binding.get('pareto_metrics'):
        raise Unavailable('pareto proposal does not bind a frozen pareto_metrics artifact '
                          '(metric policy, reference and cohort metric observations)')
    meta = service.get_artifact_metadata(sid, 'pareto_metrics')
    if meta.get('status') != 'available' or meta.get('sha256') != binding['pareto_metrics']:
        raise Unavailable('pareto_metrics artifact is missing or differs from the proposal binding')
    payload = json.loads(service.store.read_artifact(meta['sha256']))
    policy = payload.get('metric_policy') or {}
    text = policy.get('payload_json')
    if (not isinstance(text, str)
            or hashlib.sha256(text.encode()).hexdigest() != policy.get('physical_metric_spec_hash')):
        raise Unavailable('frozen metric policy is missing or its hash does not match')
    reference = payload.get('reference') or {}
    point = reference.get('ref_point') or ()
    if (reference != binding.get('reference') or len(point) != 2
            or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point)):
        raise Unavailable('frozen hypervolume reference is missing or differs from the proposal')
    if binding.get('metric_spec_hash') != policy.get('physical_metric_spec_hash'):
        raise Unavailable('proposal metric spec hash differs from the frozen metric policy')
    if not payload.get('observations'):
        raise Unavailable('no complete cohort metric observation is bound')
    return payload


def execution_capability(service, package, *, root):
    """Validate the immutable inputs without creating a backend or writing files.

    ``scalar``/``turbo``/``pareto`` use the historical admissions unchanged.  A
    ``metric_composite_v1`` package is admitted only through the explicit ``real_metric_v1``
    contract in :mod:`hornlab_search.studies.metric_refit` (approvals, pins, caps, GPU lane);
    there is no fallback to scalar or synthetic execution.
    """
    metric = package.get('metric') if isinstance(package, dict) else None
    real_metric = (isinstance(metric, dict)
                   and metric.get('provenance_mode') == REAL_METRIC_PROVENANCE)
    real_metric_status = None
    try:
        if real_metric:
            from .metric_refit import verify_real_metric_package
            real_metric_status = verify_real_metric_package(service, package, root=root)
            if real_metric_status.get('status') != 'ok':
                raise Unavailable(real_metric_status.get('detail')
                                  or 'real metric package contract refused')
        else:
            verify_package(package)
        from .package import EXECUTION_CODE_FILES
        for name in EXECUTION_CODE_FILES:
            pinned = package.get('code_pins', {}).get(name)
            path = Path(__file__).resolve().parents[2] / name
            if (not pinned or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != pinned):
                raise Unavailable(f'execution code changed or is unpinned: {name}')
        study = service.get_study(package['study_id'])
        if study['revision'] != package['spec_revision'] or study['spec_hash'] != package['spec_hash']:
            raise Unavailable('package revision/spec is stale')
        for kind, sha in package['artifacts'].items():
            if service.get_artifact_metadata(study['id'], kind).get('sha256') != sha:
                raise Unavailable(f'{kind} differs from the frozen package')
        pending = list(package['artifacts'])
        visited = set()
        while pending:
            kind = pending.pop()
            if kind in visited:
                continue
            visited.add(kind)
            metadata = service.get_artifact_metadata(study['id'], kind)
            service.store.read_artifact(metadata['sha256'])
            for dependency, sha in metadata.get('dependencies', {}).items():
                if service.get_artifact_metadata(study['id'], dependency).get('sha256') != sha:
                    raise Unavailable(f'{kind} dependency {dependency} changed')
                pending.append(dependency)
        if not package.get('deadline'):
            raise Unavailable('execution requires a timezone-aware deadline')
        if datetime.fromisoformat(package['deadline'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
            raise Unavailable('execution deadline has expired')
        policy = (package.get('proposal_policy') or {}).get('policy')
        if policy not in PRODUCTION_POLICIES and not real_metric:
            raise Unavailable('production worker supports scalar, turbo and pareto policies only '
                              '(and the explicit real_metric_v1 metric package); '
                              f'got {policy!r}')
        if policy != METRIC_POLICY and real_metric:
            raise Unavailable('real_metric_v1 provenance requires the metric_composite_v1 policy')
        interpreter = study_interpreter(root)
        if interpreter.resolve() != Path(sys.executable).resolve():
            probe = subprocess.run([str(interpreter), '-c',
                "import importlib.util,json; print(json.dumps([n for n in ('torch','botorch','gpytorch','hornlab_mesher') if importlib.util.find_spec(n) is None]))"],
                capture_output=True, text=True, timeout=20)
            missing = json.loads(probe.stdout) if probe.returncode == 0 else ['study interpreter']
        else:
            missing = [name for name in ('torch', 'botorch', 'gpytorch', 'hornlab_mesher')
                       if importlib.util.find_spec(name) is None]
        if missing:
            raise Unavailable('missing engine dependencies: ' + ', '.join(missing))
        snapshot = _json(service, study['id'], 'snapshot')
        task = snapshot['task']
        for field in ('config', 'brief'):
            path = Path(task[field])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != task[field + '_sha256']:
                raise Unavailable(f'{field} changed since snapshot; rebuild the study')
        from hornlab_search.config import load_config
        cfg = load_config(task['config'])
        if cfg.objective_version != task['objective_version']:
            raise Unavailable('resolved objective differs from frozen task')
        if real_metric:
            # The metric route replaces only the registered-task scalar admission with its own
            # explicit provenance/identity contract; canonical admission is untouched above.
            if (real_metric_status or {}).get('status') != 'ok':
                raise Unavailable((real_metric_status or {}).get('detail')
                                  or 'real metric package contract refused')
        else:
            refusal = objective_admission(cfg, task)
            if refusal is not None:
                raise Unavailable(refusal)
        if cfg.raw.get('band_split') or cfg.raw.get('meh'):
            raise Unavailable('multi-call band-split/MEH configurations require a separate budget contract')
        expected_backend = 'beat_cuda' if package['lane'] == 'gpu' else 'beat_cpu'
        if cfg.solve.backend != expected_backend:
            raise Unavailable(f'lane requires {expected_backend}; configuration uses {cfg.solve.backend}')
        if real_metric and (package['lane'] != 'gpu' or cfg.solve.backend != 'beat_cuda'):
            raise Unavailable('real metric canary requires a gpu/beat_cuda execution lane')
        pool = _json(service, study['id'], 'pool')
        if not pool.get('candidates'):
            raise Unavailable('full immutable candidate pool is missing; regenerate the proposal')
        from .package import verify_candidate_policy
        verify_candidate_policy(package, cfg, pool=pool)
        from hornlab_search.search.evaluate import collect_lib_shas
        current_pins = collect_lib_shas()
        if interpreter.resolve() != Path(sys.executable).resolve():
            probe = subprocess.run([str(interpreter), '-c',
                'import json; from hornlab_search.search.evaluate import collect_lib_shas; print(json.dumps(collect_lib_shas()))'],
                cwd=root, capture_output=True, text=True, timeout=20)
            if probe.returncode:
                raise Unavailable('cannot inspect execution interpreter dependency pins')
            current_pins = json.loads(probe.stdout)
        if not real_metric:
            manifest = _json(service, study['id'], 'training_manifest')
            if manifest.get('status') != 'ok':
                raise Unavailable('training set is not ready')
            for key in ('config_sha256', 'brief_sha256', 'objective_version'):
                if (manifest.get('task') or {}).get(key) != task[key]:
                    raise Unavailable('training task differs from frozen snapshot')
            measured_pins = (manifest.get('meta') or {}).get('measured_dependency_pins')
            if not isinstance(measured_pins, dict):
                raise Unavailable('training cohort lacks measured dependency pins; regenerate intake')
            for key in ('hornlab_mesher', 'hornlab_beat_bem', 'hornlab_plots'):
                value = measured_pins.get(key)
                if not isinstance(value, str) or value == 'unknown' or not value:
                    raise Unavailable(f'training cohort lacks measured pin: {key}')
                if value != current_pins.get(key):
                    raise Unavailable(f'training cohort dependency differs from execution: {key}')
        for key, value in package.get('dependency_pins', {}).items():
            if current_pins.get(key) != value:
                raise Unavailable(f'dependency pin changed: {key}')
        if policy == METRIC_POLICY:
            proposal = _json(service, study['id'], 'proposal')
            if proposal.get('proposal_policy') != policy:
                raise Unavailable('proposal artifact policy differs from the package policy')
        elif policy != 'scalar':
            proposal = _json(service, study['id'], 'proposal')
            if proposal.get('proposal_policy') != policy:
                raise Unavailable('proposal artifact policy differs from the package policy')
            if policy == 'turbo':
                from hornlab_search.bo.turbo import TurboState
                record = proposal.get('trust_region')
                if not isinstance(record, dict) or record.get('state_after') is None:
                    raise Unavailable('turbo proposal lacks its persisted trust-region state')
                TurboState.from_dict(record['state_after'])
            if policy == 'pareto':
                pareto_bindings(service, study['id'], proposal)
        return {'status': 'ok', 'reason': None, 'detail': None}
    except (Unavailable, KeyError, ValueError, OSError) as exc:
        return {'status': 'capability_missing', 'reason': 'production_inputs_unavailable', 'detail': str(exc)}


class ProductionJournal(DraftAttemptJournal):
    """Opt in to the frozen, durable journal after package preflight succeeds."""
    durable_contract = 'b5-journal-v2'

    def claim(self, package):
        if not super().claim(package):
            return False
        try:
            _write(self.store.root / 'workers' / package['package_id'] / 'process.json',
                   {'pid': os.getpid()})
        except Exception:
            self.release(package['package_id'], 'unknown')
            raise
        return True

    def load_progress(self, package_id):
        progress = super().load_progress(package_id)
        # Include completed verification and refusal attempts for truthful resume.
        with self.store.connect() as conn:
            rows = conn.execute('SELECT candidate_json,result_json FROM attempts '
                                'WHERE package_id=? AND result_json IS NOT NULL ORDER BY rowid',
                                (package_id,)).fetchall()
        progress['observations'] = [{'candidate': json.loads(row['candidate_json']),
                                     'result': json.loads(row['result_json'])} for row in rows]
        return progress


def _training(service, sid):
    import numpy as np
    from hornlab_search.bo.data import TrainingSet
    manifest = _json(service, sid, 'training_manifest')
    meta = service.get_artifact_metadata(sid, 'training')
    with np.load(service.store.artifacts / meta['sha256'], allow_pickle=False) as values:
        arrays = {key: np.asarray(values[key]) if key in values.files else None
                  for key in ('X', 'J', 'Y', 'Y_phys', 'G')}
    fields = {key: manifest[key] for key in ('status', 'd', 'n', 'n_min', 'n_max',
                                            'n_eligible', 'n_unique', 'projection_version')}
    for key in ('ids', 'selected_ids', 'excluded_ids', 'elite_ids', 'maximin_ids', 'active_keys'):
        fields[key] = tuple(manifest[key])
    return TrainingSet(**fields, **arrays, preparation=None, meta=manifest.get('meta', {}))


def _pool(service, sid):
    import numpy as np
    from hornlab_search.bo.data import CandidatePool, PoolCandidate
    raw = _json(service, sid, 'pool')
    candidates = []
    for row in raw['candidates']:
        row = dict(row)
        for key in ('active_vector', 'full_vector'):
            row[key] = np.asarray(row[key], dtype=float)
        candidates.append(PoolCandidate(**row))
    summary = raw.get('summary') or {}
    return CandidatePool(status='ok', requested=len(candidates), seed=summary.get('seed'),
                         seeds_tried=tuple(summary.get('seeds_tried') or ()),
                         candidates=tuple(candidates), counts=summary.get('counts') or {},
                         seed_reports=(), intended_solve_hash=summary.get('intended_solve_hash'),
                         note=raw.get('status_note', 'cheap-check-passed; mesh/acoustic eligibility unknown'))


def build_worker(service, package, *, root, backend_factory=None):
    """Construct adapters; backend/store creation remains inside owned lane evaluation."""
    from hornlab_search.config import load_config, mesh_spec, solve_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE
    from hornlab_search.studies.evaluator import (MetricPipelineStudyEvaluator,
                                                 bind_metric_record_identity,
                                                 load_metric_dataset_record,
                                                 record_metric_measurement)
    from .lanes import StudyLane
    from hornlab_search.search import evaluate as pipeline
    from hornlab_search.solve.base import get_backend

    root = Path(root).resolve()
    snapshot = _json(service, package['study_id'], 'snapshot')
    cfg = load_config(snapshot['task']['config'])
    from .package import verify_candidate_policy
    verify_candidate_policy(package, cfg, pool=_json(service, package['study_id'], 'pool'))
    policy = (package.get('proposal_policy') or {}).get('policy') or 'scalar'
    metric_brief = None
    if policy == POLICY_METRIC_COMPOSITE:
        from hornlab_search.objective.replay import brief_from_config
        from .metric_study import METRIC_TRAINING_MANIFEST_KIND, TASK_IDENTITY_FIELDS

        metric_brief = brief_from_config(snapshot['task']['config'])
        metric_manifest = _json(service, package['study_id'], METRIC_TRAINING_MANIFEST_KIND)
        metric_score = metric_manifest['score']['payload']
        metric_task = {key: metric_manifest['task'].get(key) for key in TASK_IDENTITY_FIELDS}
        metric_task.update(brief_hash=metric_score.get('brief_hash'), score_hash=metric_score.get('score_hash'))
        metric_bounds = metric_manifest['bounds']['hash']
    space = DesignSpace.from_config(cfg)
    from .builders import _task_encoding
    encoding = _task_encoding(space)

    class LifecycleLane(StudyLane):
        @contextmanager
        def owned(self, lane, package):
            with super().owned(lane, package) as runtime:
                try:
                    yield runtime
                finally:
                    if hasattr(evaluator, '_backend') and callable(getattr(evaluator._backend, 'release', None)):
                        evaluator._backend.release()

    lane = LifecycleLane(runs_root=root / 'runs',
                     cpu_cache=root / 'cache_cpu' / 'studies' / package['package_id'],
                     gpu_cache=root / 'cache' / 'studies' / package['package_id'],
                     cpu_dataset=root / 'dataset_cpu', gpu_dataset=root / 'dataset')
    run_root = root / 'runs' / ('study-' + package['package_id'][:16])

    class WorkerEvaluator(MetricPipelineStudyEvaluator):
        def _propose_through_policy(self):
            if self.history.proposal_index == 0:
                proposal = _json(service, package['study_id'], 'proposal')
                if self.policy == 'turbo':
                    self.adopt_trust_region(proposal.get('trust_region'))
                return proposal.get('candidate') or proposal.get('proposal')
            return super()._propose_through_policy()

        def _pareto_metric(self, design_hash):
            '''Measure this screen's physical errors with the SAME frozen metric policy.'''
            from hornlab_search.bo.metrics import FrozenSupport, measure_metrics_for_policy
            from hornlab_search.objective import replay
            from hornlab_search.solve.cache import load_response
            frozen = FrozenSupport(pareto_payload['metric_policy']['payload_json'],
                                   pareto_payload['metric_policy']['physical_metric_spec_hash'])
            ddir = run_root / 'screen' / 'designs' / str(design_hash)
            try:
                response = load_response(ddir / 'response.npz')
                metrics = replay._metrics_from_json(
                    json.loads((ddir / 'metrics.json').read_text(encoding='utf-8')))
                if metrics is None:
                    raise ValueError('metrics.json missing')
                obs = measure_metrics_for_policy(frozen, metrics, response)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                return {'status': 'capability_missing', 'reason': f'stored screen arrays: {exc}',
                        'physical_metric_spec_hash': frozen.physical_metric_spec_hash,
                        'coverage_deg': None, 'ripple_db': None}
            return {'status': obs.status, 'reason': obs.reason,
                    'physical_metric_spec_hash': obs.physical_metric_spec_hash,
                    'coverage_deg': obs.coverage_deg, 'ripple_db': obs.ripple_db}

        def next_candidate(self, state):
            candidate = super().next_candidate(state)
            return self._normalise(candidate, kind=candidate['kind']) if candidate else None

        def _normalise(self, raw, *, kind):
            candidate = super()._normalise(raw, kind=kind)
            if candidate is None:
                return None
            design = self._design(candidate)
            mode = 'screen' if kind == 'screen' else 'verify'
            # Same transformations as the production pipeline, before computing identity.
            design = pipeline.apply_links(design, space, cfg)
            design = pipeline._derive_throat_coupling(design, cfg)
            candidate.update(params=dict(design.params), design_hash=design.hash())
            candidate['solve_id'] = hashlib.sha256(canonical({
                'design': design.hash(), 'mesh': mesh_spec(mode, cfg).hash(),
                'solve': solve_spec(mode, cfg).hash(), 'mounting': cfg.mounting,
                'config': snapshot['task']['config_sha256'],
                'brief': snapshot['task']['brief_sha256']}).encode()).hexdigest()
            return candidate

        def lookup(self, candidate):
            path = run_root / 'results' / (candidate['solve_id'] + '.json')
            if not path.is_file():
                return None
            result = json.loads(path.read_text(encoding='utf-8'))
            if result.get('solve_id') != candidate['solve_id']:
                raise Unavailable('persisted result identity mismatch')
            if result.get('outcome') not in ('success', 'cached', 'cheap_refusal'):
                return None  # Transient failures are retried under a new durable reservation.
            return {**result, 'call_status': 'not_called',
                    'outcome': 'cached' if result.get('physical_measurement') else result['outcome']}

        def evaluate(self, candidate, attempt_id):
            runtime = lane.runtime
            if runtime is None:
                raise RuntimeError('study lane is not owned')
            from hornlab_search.dataset.store import DatasetStore
            from hornlab_search.search.outcomes import classify
            mode = 'screen' if candidate['kind'] == 'screen' else 'verify'
            directory = run_root / mode
            directory.mkdir(parents=True, exist_ok=True)
            from hornlab_search.search import rundir
            if not (directory / 'run.json').is_file():
                rundir.write_config_snapshot(directory, cfg)
                _write(directory / 'run.json', {'id': directory.name, 'name': cfg.name,
                    'mode': mode, 'backend': cfg.solve.backend, 'objective_version': cfg.objective_version,
                    'study_id': package['study_id'], 'package_id': package['package_id'],
                    'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
                    'lib_shas': pipeline.collect_lib_shas()})
            if not hasattr(self, '_backend'):
                self._backend = (backend_factory or get_backend)(cfg.solve.backend,
                    timeout_s=cfg.solve.timeout_s, cuda_fused=cfg.solve.cuda_fused,
                    retry_worker_exit=False)
            calls = [0]
            backend = self._backend

            class CountedBackend:
                def __getattr__(self, key):
                    return getattr(backend, key)

                def solve(self, *args, **kwargs):
                    if calls[0]:
                        raise RuntimeError('study attempt would exceed one backend call')
                    calls[0] += 1
                    return backend.solve(*args, **kwargs)

                def solve_traced(self, *args, **kwargs):
                    if calls[0]:
                        raise RuntimeError('study attempt would exceed one backend call')
                    calls[0] += 1
                    return backend.solve_traced(*args, **kwargs)

            # Main dataset roots are single-writer; the lane lock owns publication.
            store = DatasetStore(runtime['dataset_dir'])
            # A study's mode directory is always named 'screen'/'verify'; the dataset row needs
            # a study-scoped run id so later cohort admission can identify the package attempt.
            study_run_id = f"study-{package['package_id'][:16]}-{mode}"
            context = pipeline.make_context(cfg, store, cache_dir=runtime['cache_dir'],
                                            ndjson=directory / 'search.ndjson',
                                            run_id=study_run_id)
            evaluation = pipeline.evaluate(self._design(candidate), space, cfg, mode,
                                           directory, store, CountedBackend(), ctx=context)
            result = self.result_from_evaluation(candidate, evaluation)
            result['call_status'] = 'called' if calls[0] else 'not_called'
            complete = bool(classify(evaluation).complete)
            if complete:
                # Re-read the artifacts the normal pipeline actually committed. A
                # finite live score can still contain substituted/missing metrics.
                from hornlab_search.objective.replay import replay_run_dir
                try:
                    replay = replay_run_dir(directory, evaluation.design_hash,
                                             config_path=snapshot['task']['config'])
                    result['canonical_replay'] = replay.to_dict()
                    complete = bool(replay.complete and replay.j is not None
                                    and math.isfinite(float(replay.j))
                                    and abs(float(replay.j) - float(evaluation.objective)) <= 1e-9)
                    if complete:
                        result.update(physical_id=replay.physical_id, score_id=replay.score_id,
                                      metric_id=replay.metric_id, observed_j=float(replay.j))
                except (OSError, ValueError, TypeError) as exc:
                    complete = False
                    result['canonical_replay'] = {'status': 'unavailable', 'reason': str(exc)}
                if not complete:
                    result.update(outcome='metric_failure', observed_j=None,
                                  error='canonical replay is incomplete or differs from the live score')
            result['physical_measurement'] = complete
            result['eligible'] = complete and candidate['kind'] == 'screen'
            # Successful cached responses are measured evidence under the current score.
            if result['eligible']:
                result['outcome'] = 'success' if calls[0] else 'cached'
                if metric_brief is not None and calls[0]:
                    try:
                        meta, reference = load_metric_dataset_record(
                            store, evaluation.dataset_position, result, run_id=study_run_id,
                            version=metric_brief.objective_version)
                        reference['identity'] = bind_metric_record_identity(
                            meta, result, expected=metric_task, encoding=encoding, bounds_hash=metric_bounds)
                    except (OSError, ValueError, TypeError, IndexError, KeyError) as exc:
                        result.update(eligible=False, metric_refusal=str(exc))
                    else:
                        result = record_metric_measurement(
                            {**result, 'observed_j': evaluation.objective}, meta.get('terms'), replay,
                            brief=metric_brief, dataset_record=reference)
                elif metric_brief is not None:
                    result.update(eligible=False, metric_refusal='not_new_eligible_screen')
            if self.policy == 'pareto' and result['eligible']:
                result['pareto_metric'] = self._pareto_metric(evaluation.design_hash)
            result['attempt_id'] = attempt_id
            _write(run_root / 'results' / (candidate['solve_id'] + '.json'), result)
            return result

    seed = int((_json(service, package['study_id'], 'model')).get('seed', 0))
    pareto_payload = pareto_training = None
    metric_artifact = metric_ledger = metric_manifest_obj = None
    initial_proposal = None
    if policy == POLICY_METRIC_COMPOSITE:
        from .metric_refit import MetricRefitLedger, REAL_METRIC_REFIT_EVERY
        from .metric_study import _load_training_artifact

        metric_artifact, metric_manifest_obj, training_meta, _manifest_meta = (
            _load_training_artifact(service, package['study_id']))
        model_manifest = _json(service, package['study_id'], 'model')
        seed = int(model_manifest.get('seed', 0))
        metric_ledger = MetricRefitLedger(
            service, package['study_id'], package['package_id'],
            base_artifact=metric_artifact, base_manifest=metric_manifest_obj,
            base_artifact_sha256=training_meta['sha256'], seed=seed,
            refit_every=REAL_METRIC_REFIT_EVERY)
        proposal = _json(service, package['study_id'], 'proposal')
        initial_proposal = proposal.get('candidate') or proposal.get('proposal')
        training = None
    else:
        training = _training(service, package['study_id'])
        if policy == 'pareto':
            from .builders import pareto_training_from_artifacts
            pareto_payload = pareto_bindings(service, package['study_id'])
            pareto_training = pareto_training_from_artifacts(training, pareto_payload)
    evaluator = WorkerEvaluator(service, package, config=cfg, space=space, encoding=encoding,
        training_set=training, pool=_pool(service, package['study_id']),
        seed=seed, audit_seed=seed, evaluate_fn=lambda *args: None, policy=policy,
        pareto_training=pareto_training,
        metric_artifact=metric_artifact, metric_manifest=metric_manifest_obj,
        metric_ledger=metric_ledger, metric_brief=metric_brief,
        initial_proposal=initial_proposal)
    return evaluator, lane, ProductionJournal(service)


def execute_study(service, package, *, root):
    status = execution_capability(service, package, root=root)
    if status['status'] != 'ok':
        return status
    from .runner import run_package
    evaluator, lane, journal = build_worker(service, package, root=root)
    policy = (package.get('proposal_policy') or {}).get('policy')
    if policy == METRIC_POLICY:
        # The evaluator is injected by this caller; the gate refuses a metric package without a
        # real evaluator, and never falls back to scalar/synthetic execution.
        from .metric_study import metric_execution_gate
        gate = metric_execution_gate(
            package, allow_real_solver=True, real_evaluator=evaluator,
            service=service, root=root)
        if gate.get('status') != 'ok':
            return {'status': 'capability_missing', 'reason': gate.get('reason'),
                    'detail': gate.get('detail')}
    previous = os.environ.get('HORNLAB_GPU_LOCK')
    os.environ['HORNLAB_GPU_LOCK'] = 'refuse'
    try:
        result = run_package(package, evaluator, lane, journal)
        if result.get('status') == 'launch_conflict_or_stale':
            return result
        state = journal.state(package['package_id']) if result.get('status') != 'launch_conflict_or_stale' else {}
        result['progress'] = state
        for mode in ('screen', 'verify'):
            run_json = Path(root) / 'runs' / ('study-' + package['package_id'][:16]) / mode / 'run.json'
            if run_json.is_file():
                record = json.loads(run_json.read_text(encoding='utf-8'))
                record.update(status=result['status'], finished_utc=datetime.now(timezone.utc).isoformat())
                _write(run_json, record)
        if state:
            results = {'status': result['status'], 'package_id': package['package_id'],
                       'progress': state, 'observations': journal.load_progress(package['package_id'])['observations']}
            for kind, payload, deps in (
                    ('results', results, {'package': package['package_id']}),
                    ('verification', {'status': result['status'], 'selection': evaluator.selection,
                                      'verified_geometry_ids': sorted(evaluator._verified_geometry_ids)}, None)):
                if service.get_artifact_metadata(package['study_id'], kind).get('status') == 'missing' and result['status'] == 'pool_exhausted':
                    if deps is None:
                        deps = {'results': service.get_artifact_metadata(package['study_id'], 'results')['sha256']}
                    service.attach_artifact(package['study_id'], package['spec_revision'], kind,
                        canonical(payload).encode(), deps, kind + ':' + package['package_id'])
        result.update(package_id=package['package_id'], run_dir=str(Path(root) / 'runs' / ('study-' + package['package_id'][:16])))
        _write(service.store.root / 'workers' / package['package_id'] / 'result.json', result)
        return result
    finally:
        if previous is None:
            os.environ.pop('HORNLAB_GPU_LOCK', None)
        else:
            os.environ['HORNLAB_GPU_LOCK'] = previous


def launch_study(package, *, root, study_root):
    """Launch the immutable package in a dedicated interpreter process."""
    from .service import StudyService
    service = StudyService(study_root)
    status = execution_capability(service, package, root=root)
    if status['status'] != 'ok':
        from hornlab_search.gui.study_jobs import StudyJobError
        raise StudyJobError('capability_missing', status['detail'], 503)
    worker = Path(study_root).resolve() / 'workers' / package['package_id']
    path = worker / 'package.json'
    _write(path, package)
    argv = [str(study_interpreter(root)), '-m', 'hornlab_search.studies.cli', 'run', '--root', str(Path(study_root).resolve()),
            '--package', str(path), '--execute', '--project-root', str(Path(root).resolve())]
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with (worker / 'worker.log').open('ab') as output:
        process = subprocess.Popen(argv, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=flags)
    return {'pid': process.pid, 'package_id': package['package_id'], 'log': str(worker / 'worker.log')}


def cancel_study(package, *, study_root):
    from .service import StudyService
    journal = ProductionJournal(StudyService(study_root))
    return journal.cancel(package['package_id'], 'cancel:' + package['package_id'])


def reconcile_production(service, study_id, *, root):
    """Resolve only exact persisted attempt evidence; never infer an absent solve."""
    from .reconcile import reconcile_study
    journal = ProductionJournal(service)

    class Probe:
        def inspect(self, attempt):
            path = Path(root) / 'runs' / ('study-' + attempt['package_id'][:16]) / 'results' / (attempt['solve_id'] + '.json')
            if path.is_file():
                result = json.loads(path.read_text(encoding='utf-8'))
                if result.get('attempt_id') == attempt['attempt_id'] and result.get('solve_id') == attempt['solve_id']:
                    return {'state': 'result', 'attempt_id': attempt['attempt_id'],
                            'solve_id': attempt['solve_id'], 'result': result}
            return {'state': 'unknown'}

    result = reconcile_study(study_id, Probe(), journal)
    released = []
    with service.store.connect() as conn:
        packages = conn.execute('SELECT id FROM packages WHERE study_id=? AND active=1', (study_id,)).fetchall()
    for package in packages:
        pid = package['id']
        identity = service.store.root / 'workers' / pid / 'process.json'
        if identity.is_file():
            process = json.loads(identity.read_text(encoding='utf-8'))
            if _process_alive(process.get('pid')) is False:
                journal.release(pid, 'unknown' if journal.state(pid)['unresolved'] else 'interrupted')
                released.append(pid)
    result['released_dead_workers'] = released
    return result


def _process_alive(pid):
    """False only for demonstrably dead PIDs; denied/ambiguous stays unknown."""
    if type(pid) is not int or pid <= 0:
        return None
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            status = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(status)):
                return None
            return status.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
