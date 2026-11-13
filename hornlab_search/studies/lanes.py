"""Explicit lane ownership for a future authorized study runner.

No host cleanup or solve calls. Cache and dataset roots are explicit values for
an evaluator adapter, not invented environment variables. The journal/production
package authorization remains independently required before runner dispatch.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
from threading import Lock

from hornlab_search.search.gpulock import cpu_lane_lock, gpu_lock

_ENV_GUARD = Lock()
_WORKER_ENV = 'HORNLAB_BEAT_WORKER_DIR'
_OWNER_ENVS = ('HORNLAB_CPU_LANE_LOCK_OWNER', 'HORNLAB_GPU_LOCK_OWNER')
_THREAD_ENVS = ('JULIA_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')


class StudyLane:
    lane_contract = 'b5-owned-lane-v1'

    def __init__(self, *, runs_root, cpu_cache, gpu_cache, cpu_dataset, gpu_dataset):
        roots = [Path(p) for p in (runs_root, cpu_cache, gpu_cache, cpu_dataset, gpu_dataset)]
        if any(not p.is_absolute() for p in roots):
            raise ValueError('absolute lane roots required')
        self.runs_root, cpu_cache, gpu_cache, cpu_dataset, gpu_dataset = map(Path.resolve, roots)
        if cpu_cache == gpu_cache or cpu_dataset == gpu_dataset:
            raise ValueError('CPU and GPU cache/dataset roots must differ')
        self._roots = {'cpu': {'cache_dir': cpu_cache, 'dataset_dir': cpu_dataset},
                       'gpu': {'cache_dir': gpu_cache, 'dataset_dir': gpu_dataset}}
        self.runtime = None

    @contextmanager
    def owned(self, lane, package):
        if lane not in self._roots or package.get('lane') != lane:
            raise ValueError('explicit matching lane required')
        # Environment is process-global; do not allow another thread or a nested
        # caller to overwrite worker/lock ownership while a study is running.
        if not _ENV_GUARD.acquire(blocking=False):
            raise RuntimeError('another study lane is active in this process')
        previous = {}
        try:
            if any(os.environ.get(k) for k in _OWNER_ENVS):
                raise RuntimeError('nested or inherited lane ownership is not allowed')
            lock = cpu_lane_lock if lane == 'cpu' else gpu_lock
            with lock(f"study {package['study_id']}", self.runs_root):
                overrides = {_WORKER_ENV: str(self.runs_root / 'lanes' / lane / 'workers')}
                if lane == 'cpu':
                    overrides.update({key: '12' for key in _THREAD_ENVS})
                previous = {key: os.environ.get(key) for key in overrides}
                os.environ.update(overrides)
                self.runtime = {'lane': lane, 'worker_dir': Path(overrides[_WORKER_ENV]),
                                **self._roots[lane]}
                try:
                    yield self.runtime
                finally:
                    self.runtime = None
                    for key, old in previous.items():
                        if old is None: os.environ.pop(key, None)
                        else: os.environ[key] = old
        finally:
            _ENV_GUARD.release()


class FakeEvaluatorBridge:
    """Adapter for injected test callbacks; cannot invoke production evaluator itself."""
    def __init__(self, lane, *, propose, lookup, preflight, evaluate, observe,
                 restore=None, rng_state=None):
        self.lane = lane
        self._propose, self._lookup, self._preflight = propose, lookup, preflight
        self._evaluate, self._observe = evaluate, observe
        self._restore, self._rng_state = restore, rng_state

    def _runtime(self):
        if self.lane.runtime is None:
            raise RuntimeError('lane not owned')
        return self.lane.runtime

    def next_candidate(self, state): return self._propose(state, self._runtime())
    def lookup(self, candidate): return self._lookup(candidate, self._runtime())
    def preflight(self, candidate): return self._preflight(candidate, self._runtime())
    def evaluate(self, candidate, attempt_id): return self._evaluate(candidate, attempt_id, self._runtime())
    def observe(self, result): return self._observe(result, self._runtime())

    def restore_progress(self, progress):
        if self._restore is None:
            raise RuntimeError('durable observation restoration not configured')
        return self._restore(progress, self._runtime())

    def proposal_rng_state(self):
        if self._rng_state is None:
            raise RuntimeError('durable proposal RNG state not configured')
        return self._rng_state(self._runtime())
