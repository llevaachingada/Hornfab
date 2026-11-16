"""Audit a master-family search box through the real CPU mesher, without BEM."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generators import rolled_family
from hornlab_search.mesh.build import build_mesh, read_msh_summary
from hornlab_search.mesh.throat_check import fits_exit, throat_shape
from hornlab_search.search.evaluate import envelope_violation


def audit(path, samples=64, seed=0):
    cfg = load_config(path)
    space = DesignSpace.from_config(cfg)
    keys = space.keys()
    if not rolled_family.is_family_spec(cfg.generator):
        raise ValueError('only canonical rolled-family configs are supported')
    if len(keys) > 10:
        raise ValueError('more than ten axes requires an explicit corner sampling plan')
    origin = space.normalize(space.seed)
    trials = [('seed', origin)]
    trials += [('corner', np.array(x)) for x in itertools.product([0., 1.], repeat=len(keys))]
    trials += [('uniform', x) for x in np.random.default_rng(seed).random((samples, len(keys)))]
    results = []
    with tempfile.TemporaryDirectory(prefix='rolled-family-audit-') as tmp:
        for i, (kind, unit) in enumerate(trials):
            record = {'kind': kind, 'unit': unit.tolist()}
            try:
                design = space.denormalize(unit)
                if design.params.get('_generator_error'):
                    raise ValueError(design.params['_generator_error'])
                mesh = build_mesh(design, mesh_spec('screen', cfg), cfg, Path(tmp)/str(i), mode='screen')
                why = envelope_violation(mesh, cfg.brief)
                fit, source_note = fits_exit(throat_shape(mesh.path), 2*cfg.brief['driver']['exit_radius_mm'])
                if why or not fit:
                    raise ValueError(why or source_note)
                record.update(ok=True, dofs=read_msh_summary(Path(mesh.path))['n_nodes_used'],
                              bbox_m=mesh.bbox_m, design_hash=design.hash())
            except Exception as exc:
                record.update(ok=False, error=f'{type(exc).__name__}: {exc}')
            results.append(record)
    # A local point-cloud Jacobian exposes dormant or exactly redundant knobs.
    derivatives = []
    for i in range(len(keys)):
        lo, hi = origin.copy(), origin.copy()
        lo[i] -= 1e-3
        hi[i] += 1e-3
        if lo[i] < 0 or hi[i] > 1:
            raise ValueError('seed must be interior for the local activity audit')
        pair = []
        for x in (lo, hi):
            geometry = rolled_family.resolve_grid(space.denormalize(x).params['grid'], cfg.brief)
            pair.append(np.concatenate((geometry['inner_points'].ravel(), geometry['outer_points'].ravel())))
        derivatives.append((pair[1]-pair[0])/.002)
    singular = np.linalg.svd(np.array(derivatives), compute_uv=False)
    rank = int(np.sum(singular > singular[0]*1e-8))
    summary = {}
    for kind in ('seed', 'corner', 'uniform'):
        rows = [r for r in results if r['kind'] == kind]
        summary[kind] = {'valid': sum(r['ok'] for r in rows), 'tested': len(rows)}
    return {'schema': 'rolled-family-box-audit-v1', 'config': str(path),
            'config_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'implementation_sha256': rolled_family.implementation_digest(), 'keys': keys,
            'initial_unit': origin.tolist(), 'bounds': cfg.bounds_raw,
            'initial_step_physical': {k: cfg.search.sigma0*(space.bounds[k].hi-space.bounds[k].lo) for k in keys},
            'jacobian_rank': rank, 'jacobian_singular_values': singular.tolist(),
            'summary': summary, 'results': results,
            'ok': all(r['ok'] for r in results) and rank == len(keys)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    parser.add_argument('--samples', type=int, default=64)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    report = audit(args.config, args.samples)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('config', 'summary', 'jacobian_rank', 'ok')}))
    raise SystemExit(0 if report['ok'] else 1)
