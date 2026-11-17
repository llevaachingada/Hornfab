"""Check the per-lane sibling-holdout prior rank against .x3/strict.py's own scheme-2 P."""
import numpy as np, sys
sys.path.insert(0, 'scratch/fable_architecture/.x3c')
from a7_common import load_base, sibling, cov
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr
X, Y, G, E, ids, rows, f = load_base(); nf = len(f); band = np.where(f >= 600)[0]
S = np.array([sibling(g) for g in G])
P = np.zeros_like(Y); B = np.zeros_like(Y)
for g in sorted(set(S)):
    te = S == g; tr = ~te
    P[te] = ExtraTreesRegressor(n_estimators=100, min_samples_leaf=2, random_state=0,
                                n_jobs=4).fit(X[tr], Y[tr]).predict(X[te])
    B[te] = Y[tr].mean(axis=0)
rp = []
for g in sorted(set(G)):
    if (G == g).sum() >= 30:
        r = spearmanr(cov(Y[G == g], band, nf), cov(P[G == g], band, nf)).statistic
        rp.append((g, int((G == g).sum()), round(float(r), 3)))
print('strict-style sibling rank, lanes>=30:', len(rp), 'median', round(float(np.nanmedian([x[2] for x in rp])), 3))
print('lanes>=40 median', round(float(np.nanmedian([x[2] for x in rp if x[1] >= 40])), 3))
for x in rp:
    if x[1] >= 40:
        print(x)
