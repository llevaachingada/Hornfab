"""Probe: dataset alignment, timing of one wavelength-conditioned fit."""
import numpy as np, pickle, time, collections
from sklearn.ensemble import ExtraTreesRegressor

ROOT = 'scratch/fable_architecture'
D = np.load(f'{ROOT}/.x3/extended.npz', allow_pickle=True)
X, Y, G, E, ids = D['X'], D['Y'], D['G'], D['E'], [str(h) for h in D['ids']]
rows = pickle.load(open(f'{ROOT}/.fable/rows.pkl', 'rb'))
f = np.array([250.0, 315.0, 400.0, 500.0, 643.33, 827.75, 1065.04, 1370.35, 1763.18,
              2268.63, 2573.0, 2918.96, 3311.0, 3755.72, 4260.0, 4830.0, 5480.0, 6000.0])
# is this the same grid as the stored rows?
fs = collections.Counter(tuple(np.round(r['f'], 2)) for r in rows if r['ok'] and r['f'] and len(r['f']) == 18)
print('distinct 18-f grids', len(fs), 'top', fs.most_common(3))
print('band', int((f >= 600).sum()), 'of', len(f))

# row lookup for created timestamp and engine
by_ch = {}
for r in rows:
    if r['ok']:
        by_ch.setdefault((r['config'], r['h']), []).append(r)
miss = [(g, h) for g, h in zip(G, ids) if (g, h) not in by_ch]
print('designs without a valid row', len(miss))
mult = sum(len(v) > 1 for v in by_ch.values())
print('(config,h) with multiple valid rows', mult)

c = 343.0
band = np.where(f >= 600)[0]
xx = X[:, None, :] * (2 * np.pi * f[None, :, None] / c)     # (n,18,27)
print('feature', xx.shape)
t0 = time.time()
ExtraTreesRegressor(n_estimators=40, min_samples_leaf=3, random_state=0, n_jobs=4).fit(
    xx.reshape(-1, 27), Y[:, :54].reshape(-1, 18, 3)[:, :, 0].reshape(-1))
print('one fit seconds', round(time.time() - t0, 1))
