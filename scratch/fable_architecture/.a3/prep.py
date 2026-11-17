"""A3 prep: eligibility, parity-exact full-J verification, compact per-lane arrays.

Read-only w.r.t. everything outside scratch/fable_architecture/.a3/.
Writes .a3/prep.pkl with:
  lanes[lane] = dict(rows=[dict(run,h,config,brief,J,terms(9),knobvec)], X=27-d old mesh desc, Y=54 resp,
                       K=knobs, terms=T(9), engine, ids)
  plus parity stats.
"""
import collections
import pathlib
import pickle
import sys
import time

import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import resolve_v7_weights

TERMS = ('cov', 'rip', 'di', 'dislope', 'flat', 'load', 'distd', 'diag', 'flat_cv')

data, fails = pickle.load(open(ROOT / '.e1/descriptors.pkl', 'rb'))
rows_all = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
lane_counts = collections.Counter(r['config'] for r, _, _ in data if r['brief'] == 'cd')
LANES = sorted(g for g, n in lane_counts.items() if n >= 100)
print('lanes', LANES, 'n', [lane_counts[g] for g in LANES])

# brief per (run) cache; verify every row in a lane uses the same objective version/weights/target
brief_cache = {}
parity = []
lanes = {}
t0 = time.time()
for g in LANES:
    items = [(r, x, y) for r, x, y in data if r['config'] == g and r['brief'] == 'cd']
    # knobs matrix: E1's rule (bounds keys with hi>lo and search true, from the first row)
    keys = None
    recs = []
    X, Y, Kk, T, J = [], [], [], [], []
    versions = set()
    for r, x, y in items:
        bp = pathlib.Path('runs') / r['run'] / 'config.yaml'
        b = brief_cache.get(str(bp))
        if b is None:
            b = brief_cache[str(bp)] = H.brief(bp)
        versions.add(int(b.objective_version))
        if keys is None:
            keys = [k for k, v in r['bounds'].items()
                    if v.get('hi', 0) > v.get('lo', 0) and v.get('search', True)]
        src = r['knobs'] if r['knobs'] else r['params']
        kv = np.array([float(src[k]) for k in keys], float)
        tv = np.array([r['terms'][k] for k in TERMS], float)
        if not (np.isfinite(tv).all() and np.isfinite(float(r['J']))):
            print('NONFINITE TERM', g, r['h'], r['terms']); raise SystemExit(1)
        # parity-exact full J regeneration
        resp = H.resp_from_run(pathlib.Path('runs') / r['run'], r['h'])
        met = H.metrics_parity(resp, b.target)
        Jr, tr = H.score_v7(met, resp, b.target, b.weights, b.objective_params)
        dJ = abs(Jr - float(r['J']))
        dterm = max(abs(tr[k] - r['terms'][k]) for k in TERMS)
        parity.append((g, r['h'], r['run'], dJ, dterm, int(b.objective_version)))
        recs.append(dict(run=r['run'], h=r['h'], J=float(r['J'])))
        X.append(np.asarray(x, float)); Y.append(np.asarray(y, float))
        Kk.append(kv); T.append(tv); J.append(float(r['J']))
    engine = ('OSSE' if not items[0][0]['gen'] else
              ('GRID' if items[0][0]['gen'] == 'grid' else 'GEN-FF'))
    lanes[g] = dict(rows=recs, X=np.asarray(X), Y=np.asarray(Y), K=np.asarray(Kk),
                    T=np.asarray(T), J=np.asarray(J), engine=engine,
                    knobs=keys, objective_versions=sorted(versions),
                    weights=resolve_v7_weights(brief_cache[str(pathlib.Path('runs') / items[0][0]['run'] / 'config.yaml')].weights))
    print('lane', g, 'n', len(recs), 'knobs', len(keys), 'engine', engine,
          'obj', sorted(versions), 'elapsed %.0fs' % (time.time() - t0), flush=True)

dJ = np.array([p[3] for p in parity]); dt = np.array([p[4] for p in parity])
print('PARITY n', len(parity), 'max|dJ|', dJ.max(), 'max|dterm|', dt.max(),
      'versions', sorted(set(p[5] for p in parity)))
print('J by lane', {g: (float(l['J'].min()), float(l['J'].max()), float(np.median(l['J']))) for g, l in lanes.items()})
pickle.dump(dict(lanes=lanes, parity=parity, terms=TERMS, failed=len(fails)),
            open(ROOT / '.a3/prep.pkl', 'wb'))
print('wrote prep.pkl')
