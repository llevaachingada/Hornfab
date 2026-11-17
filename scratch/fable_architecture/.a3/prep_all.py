"""A3 prep (all CD rows): parity-exact full-J verification + compact arrays for every eligible row.

Writes .a3/all.pkl:
  recs = list of dict(lane, run, h, engine, brief, objective_version, J, terms9)
  X (n,27) old mesh descriptors, Y (n,54) bw_h/bw_v/di, T (n,9) normalized v7 terms, K (n,K) knobs
  meta: knob key list, weights, frequency grid, parity stats.
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
print('CD rows', len(data), 'lanes>=100', len(LANES), flush=True)

# one knob key list per lane (bounds differ by config)
knob_keys = {}
for r, _, _ in data:
    if r['brief'] != 'cd' or r['config'] not in LANES or r['config'] in knob_keys:
        continue
    knob_keys[r['config']] = [k for k, v in r['bounds'].items()
                              if v.get('hi', 0) > v.get('lo', 0) and v.get('search', True)]
KEY_ORDER = sorted(set(k for ks in knob_keys.values() for k in ks))

brief_cache = {}
recs = []
X, Y, T, J, K = [], [], [], [], []
parity = []
t0 = time.time()
for n, (r, x, y) in enumerate(data):
    if r['brief'] != 'cd':
        continue
    bp = pathlib.Path('runs') / r['run'] / 'config.yaml'
    b = brief_cache.get(str(bp))
    if b is None:
        b = brief_cache[str(bp)] = H.brief(bp)
    resp = H.resp_from_run(pathlib.Path('runs') / r['run'], r['h'])
    met = H.metrics_parity(resp, b.target)
    Jr, tr = H.score_v7(met, resp, b.target, b.weights, b.objective_params)
    dJ = abs(Jr - float(r['J']))
    dterm = max(abs(tr[k] - r['terms'][k]) for k in TERMS)
    parity.append((r['config'], r['h'], r['run'], float(dJ), float(dterm), int(b.objective_version)))
    tv = np.array([r['terms'][k] for k in TERMS], float)
    src = r['knobs'] if r['knobs'] else r['params']
    laneset = knob_keys.get(r['config'])
    kk = np.full(len(KEY_ORDER), np.nan)
    if laneset:
        # per-lane knob vector in that lane's own key order is stored separately in 'lane_knobs'
        kv = np.array([float(src[k]) for k in laneset], float)
    else:
        kv = np.zeros(0)
    engine = ('OSSE' if not r['gen'] else ('GRID' if r['gen'] == 'grid' else 'GEN-FF'))
    recs.append(dict(lane=r['config'], run=r['run'], h=r['h'], engine=engine,
                     objective_version=int(b.objective_version), J=float(r['J']),
                     laneset=laneset, terms=[float(v) for v in tv]))
    X.append(np.asarray(x, float)); Y.append(np.asarray(y, float))
    T.append(tv); J.append(float(r['J'])); K.append(kv)
    if (n + 1) % 200 == 0:
        print(n + 1, 'elapsed %.0fs' % (time.time() - t0), flush=True)

X = np.asarray(X); Y = np.asarray(Y); T = np.asarray(T); J = np.asarray(J)
dJ = np.array([p[3] for p in parity]); dt = np.array([p[4] for p in parity])
print('n', len(recs), 'X', X.shape, 'Y', Y.shape, 'T', T.shape)
print('PARITY max|dJ|', dJ.max(), 'max|dterm|', dt.max(),
      'versions', sorted(set(p[5] for p in parity)))
weights = resolve_v7_weights(brief_cache[str(pathlib.Path('runs') / recs[0]['run'] / 'config.yaml')].weights)
wvec = np.array([weights[k] for k in TERMS])
print('weights', dict(zip(TERMS, wvec)))
print('J = T@w max resid', np.abs(J - T @ wvec).max())
pickle.dump(dict(recs=recs, X=X, Y=Y, T=T, J=J, Klist=K, key_order=KEY_ORDER,
                 knob_keys=knob_keys, terms=TERMS, wvec=wvec, parity=parity,
                 failed=len(fails), lanes=LANES), open(ROOT / '.a3/all.pkl', 'wb'))
print('wrote all.pkl')
