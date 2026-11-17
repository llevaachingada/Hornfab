"""P1 probe: lane counts with full descriptors, target finiteness, one model-fit timing."""
import pickle, pathlib, collections, re, time, warnings
import numpy as np
warnings.filterwarnings('ignore')
from sklearn.ensemble import ExtraTreesRegressor

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb'))
        if r['ok'] and r['f'] and len(r['f']) == 18]
D = np.load(REPO / 'scratch/fable_architecture/.p1/desc_all.npz')
X, keep = D['X'], D['keep']
idx = np.where(keep)[0]
rows = [rows[i] for i in idx]
G = np.array([r['config'] for r in rows])
B = np.array([r['brief'] for r in rows])
nf = 18
Y = np.array([np.concatenate([r['bwh'], r['bwv'], r['di']]) for r in rows], float)
fin = np.isfinite(Y).all(1)
print('rows', len(rows), 'finite Y', fin.sum(), 'nonfinite', (~fin).sum())
c = collections.Counter(G[fin])
print('configs', len(c))
for g, n in sorted(c.items()):
    print(f'{g:42s} n={n:4d} brief={sorted(set(B[G == g]))}')
# duplicates of (run, hash)
keyc = collections.Counter((r['run'], r['h']) for r in rows)
print('duplicate (run,hash):', sum(v - 1 for v in keyc.values() if v > 1))
# one fit timing on finite rows
M = fin
t0 = time.time()
m = ExtraTreesRegressor(200, min_samples_leaf=2, random_state=0, n_jobs=6).fit(X[M], Y[M])
print('one fit on', M.sum(), 'rows:', round(time.time() - t0, 1), 's')
