"""Probe support-distance distributions (sibling holdout) with a sane sd floor."""
import pickle, pathlib, collections, re, warnings
import numpy as np
from sklearn.neighbors import NearestNeighbors
warnings.filterwarnings('ignore')
REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows_all = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb'))
            if r['ok'] and r['f'] and len(r['f']) == 18]
D = np.load(REPO / 'scratch/fable_architecture/.p1/desc_all.npz')
idx = np.where(D['keep'])[0]
rows = [rows_all[i] for i in idx]
X = D['X'][idx]
G = np.array([r['config'] for r in rows])
B = np.array([str(r['brief']) for r in rows])

def sibling(g):
    g = re.sub(r'_v\d+$', '', g).replace('_smooth', '')
    if g.startswith('sp__'):
        return 'sp__control_moderate_strong'
    if g.startswith('rr__pucker') or g == 'rr__reference':
        return 'rr__reference_pucker'
    if g.startswith('klangfilm_hv__a'):
        return 'klangfilm_hv__axis_variants'
    return g
S = np.array([sibling(g) for g in G])
cnt = collections.Counter(G)
LANES = sorted([g for g in cnt if cnt[g] >= 40 and set(B[G == g]) == {'cd'}])
for g in LANES:
    tr = S != sibling(g)
    mu, sd = X[tr].mean(0), X[tr].std(0)
    sd = np.where(sd < 0.05, 1.0, sd)
    Ztr = (X[tr] - mu) / sd
    nn = NearestNeighbors(n_neighbors=2).fit(Ztr)
    dtr = nn.kneighbors(Ztr)[0][:, 1]
    Zte = (X[G == g] - mu) / sd
    dte = NearestNeighbors(n_neighbors=1).fit(Ztr).kneighbors(Zte)[0][:, 0]
    p = np.percentile(dte, [50, 90, 100])
    print('%-40s n=%3d dtr p50/p95/max %.2f/%.2f/%.2f | dte p50/p90/max %.2f/%.2f/%.2f | >max %.0f%% | >p99x1.5 %.0f%%' % (
        g[:40], len(dte), np.median(dtr), np.percentile(dtr, 95), dtr.max(), p[0], p[1], p[2],
        100 * np.mean(dte > dtr.max()), 100 * np.mean(dte > 1.5 * np.percentile(dtr, 99))))
