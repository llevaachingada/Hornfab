"""A3 smoke: parity of regenerated full J vs stored J, plus timing. Read-only."""
import pathlib, pickle, sys, time, collections
import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import resolve_v7_weights

rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
data, _ = pickle.load(open(ROOT / '.e1/descriptors.pkl', 'rb'))
lanes = [g for g, n in collections.Counter(r['config'] for r, _, _ in data if r['brief'] == 'cd').items() if n >= 100]
cfg_cache = {}
n = 0
t0 = time.time()
diffs = []
term_diffs = collections.defaultdict(list)
for r, _, _ in data:
    if r['config'] not in lanes or r['brief'] != 'cd':
        continue
    bp = pathlib.Path('runs') / r['run'] / 'config.yaml'
    b = cfg_cache.get(str(bp))
    if b is None:
        b = cfg_cache[str(bp)] = H.brief(bp)
    resp = H.resp_from_run(pathlib.Path('runs') / r['run'], r['h'])
    met = H.metrics_parity(resp, b.target)
    w = resolve_v7_weights(b.weights)
    J, t = H.score_v7(met, resp, b.target, b.weights, b.objective_params)
    d = abs(J - r['J'])
    diffs.append(d)
    for k in ('cov', 'rip', 'di', 'dislope', 'flat', 'load', 'distd', 'diag', 'flat_cv'):
        term_diffs[k].append(abs(t[k] - r['terms'][k]))
    n += 1
    if n % 50 == 0:
        print(n, 'max|dJ|', max(diffs), 'mean', np.mean(diffs), 'elapsed %.1fs' % (time.time() - t0), flush=True)
    if n >= 200:
        break
print('n', n, 'elapsed', time.time() - t0)
print('dJ quantiles', np.percentile(diffs, [50, 90, 99, 100]))
for k, v in term_diffs.items():
    print('term', k, 'median', np.median(v), 'max', max(v))
print('configs', {k: len(v) for k, v in cfg_cache.items()})
