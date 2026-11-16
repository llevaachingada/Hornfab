"""CPU-only synthetic wiring smoke; no meshing, BEM, or acoustic inference."""
import json
import math
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch

from hornlab_search.bo import model
from hornlab_search.bo.data import (TrainingObservation, build_candidate_pool,
                                    build_training_set, geometry_checks,
                                    materialize_geometry, materialized_geometry_hash)
from hornlab_search.bo.encoding import ActiveProjection
from hornlab_search.bo.policy import fit_and_propose
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.types import Design

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'examples/typologies/rolled_family_2026-11-15/rf__section_radial_v7.yaml'
REPORT = Path(__file__).with_name('bo_synthetic_smoke.json')
torch.set_num_threads(1)
model.NUM_THREADS = 1


def cold_replay():
    obj = json.load(sys.stdin)
    cfg = load_config(CONFIG)
    enc = ActiveProjection.identity(DesignSpace.from_config(cfg))
    design = Design('FREEFORM', obj['params'])
    x = enc.normalize_design(design)
    mat = materialize_geometry(design, cfg, resolution_mm=30.)
    _, env_ok, throat_ok = geometry_checks(mat, cfg, design.params)
    print(json.dumps({'x': x.tolist(), 'design_hash': design.hash(),
                      'geometry_hash': materialized_geometry_hash(mat),
                      'envelope_ok': env_ok, 'throat_ok': throat_ok}))


def main():
    started = time.monotonic()
    report = {'status': 'failed', 'data': 'synthetic only; no acoustic measurement or inference',
              'config': str(CONFIG), 'versions': model.library_versions(),
              'torch_threads': 1, 'gpu_or_bem_calls': 0}
    try:
        cfg = load_config(CONFIG)
        space = DesignSpace.from_config(cfg)
        enc = ActiveProjection.identity(space)
        report['active_keys'] = list(enc.active_keys)
        assert enc.d == 5
        # Production n_min is 16. Sample valid surfaces through the canonical pool.
        training_pool = build_candidate_pool(space, enc, cfg, n=16, seed=481,
                                              max_extra_seeds=0, resolution_mm=30.)
        assert training_pool.status == 'ok' and len(training_pool.candidates) == 16, training_pool.summary()
        observations = []
        for i, c in enumerate(training_pool.candidates):
            x = np.asarray(c.active_vector)
            j = float(np.sum((x - np.array([.2, .35, .5, .65, .8])) ** 2))
            observations.append(TrainingObservation(f'synthetic-{i:02d}', x, J=j,
                                geometry_hash=c.geometry_hash, solve_hash=c.intended_solve_hash))
        train = build_training_set(observations, encoding=enc)
        assert train.status == 'ok' and train.n == 16
        pool = build_candidate_pool(space, enc, cfg, n=8, seed=977, max_extra_seeds=0,
                                    known_geometry_hashes=[c.geometry_hash for c in training_pool.candidates],
                                    resolution_mm=30.)
        assert pool.status == 'ok' and len(pool.candidates) > 0, pool.summary()
        outcome = fit_and_propose('scalar', training_set=train, pool=pool, encoding=enc,
                                  config=cfg, seed=4, resolution_mm=30.)
        payload = outcome.to_dict()
        assert outcome.status == 'ok' and outcome.selection_reason == 'acquisition', payload
        assert not outcome.fallback and outcome.acquisition, payload
        assert all(math.isfinite(float(v)) for v in outcome.proposal['active_vector'])
        candidate = next(c for c in pool.candidates if c.candidate_id == outcome.proposal['candidate_id'])
        design = enc.denormalize(candidate.active_vector)
        result = subprocess.run([sys.executable, __file__, '--cold'], cwd=ROOT,
                                input=json.dumps({'params': design.params}), text=True,
                                capture_output=True, timeout=30, check=True)
        cold = json.loads(result.stdout.strip().splitlines()[-1])
        assert cold['design_hash'] == candidate.design_hash and cold['geometry_hash'] == candidate.geometry_hash
        assert np.allclose(cold['x'], candidate.active_vector) and cold['envelope_ok'] and cold['throat_ok']
        report.update(status='ok', training_n=train.n, pool_count=len(pool.candidates),
                      synthetic_objective='sum((unit_vector - [0.2,0.35,0.5,0.65,0.8])**2)',
                      selection_reason=outcome.selection_reason, acquisition=outcome.acquisition,
                      predicted=outcome.predicted, candidate_id=candidate.candidate_id,
                      active_vector=candidate.active_vector.tolist(), design_hash=candidate.design_hash,
                      geometry_hash=candidate.geometry_hash, cold_replay=cold,
                      pool_counts=pool.counts, training_pool_counts=training_pool.counts)
    except Exception as exc:
        report.update(error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
    report['elapsed_s'] = round(time.monotonic()-started, 3)
    REPORT.write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps(report, default=str))
    return 0 if report['status'] == 'ok' else 1


if __name__ == '__main__':
    if '--cold' in sys.argv:
        cold_replay()
    else:
        raise SystemExit(main())
