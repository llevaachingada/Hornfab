"""SUPERSEDED DIAGNOSTIC — do not quote its lane count.

Early attempt to reproduce an7 by pairing desc.npz rows to rows.pkl on identical metric arrays.
That mapping is ambiguous for duplicate designs across runs, so this script reported 20 lanes and
slightly different medians.  The authoritative reproduction is `.fable/an7.py` itself (19 lanes;
0.55 / 0.43 / 0.30; 12 of 19; 9 of 19), recorded in P1_PREDICTOR_REPLAY.md.  Kept only as a record
of the term-formula check, which later moved to inspect_terms5.py.

P1 stage 0: reproduce the known an7 result from the stored descriptor sample, and verify the
coverage-plus-DI formula against the stored v7 terms. Read-only."""
import pickle, pathlib, collections, re, warnings
import numpy as np
warnings.filterwarnings('ignore')

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
D = np.load(REPO / 'scratch/fable_architecture/.fable/desc.npz', allow_pickle=True)
X, Y, G = D['X'], D['Y'], D['G']
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb'))
        if r['ok'] and r['f'] and len(r['f']) == 18]
print('rows', len(rows), 'desc', X.shape)

# Map each desc row to a rows.pkl row by exact (bwh,bwv,di) match.
def key(r):
    return (tuple(np.round(r['bwh'], 6)), tuple(np.round(r['bwv'], 6)), tuple(np.round(r['di'], 6)))
by_key = collections.defaultdict(list)
for r in rows:
    if r['bwh'] is not None and r['bwv'] is not None and r['di'] is not None:
        by_key[key(r)].append(r)
keep = []
miss = 0
for i in range(X.shape[0]):
    k = (tuple(np.round(Y[i, :18], 6)), tuple(np.round(Y[i, 18:36], 6)), tuple(np.round(Y[i, 36:], 6)))
    if k in by_key:
        keep.append(by_key[k][0])
    else:
        keep.append(None)
        miss += 1
print('desc rows matched to rows.pkl:', sum(k is not None for k in keep), 'missing', miss)

f = np.array(keep[0]['f'])
nf = len(f)
band = np.where(f >= 700)[0]
cov = lambda M: np.mean(np.where(M[:, band] < 80, 2, 1) * (M[:, band] - 80) ** 2, 1) / 100 + \
    0.5 * np.mean(np.where(M[:, nf + band] < 50, 2, 1) * (M[:, nf + band] - 50) ** 2, 1) / 100
fam = lambda c: re.sub(r'(_smooth)?(_warm)?(_v\d+)?$', '', re.sub(r'_smooth', '', c))
J = np.array([r['J'] for r in keep])
N = np.array([r['n'] or 0 for r in keep])
B = np.array([r['brief'] for r in keep])
from sklearn.ensemble import ExtraTreesRegressor
res = []
for g in sorted(set(G)):
    te = G == g
    if te.sum() < 40 or B[te][0] != 'cd':
        continue
    tr = np.array([fam(c) != fam(g) for c in G])
    m = ExtraTreesRegressor(200, min_samples_leaf=2, random_state=0, n_jobs=6).fit(X[tr], Y[tr])
    pc = cov(m.predict(X[te]))
    j, n = J[te], N[te]
    order = np.argsort(pc)
    first8 = j[np.argsort(n)[:8]].min()
    pick8 = j[order[:8]].min()
    rnd = np.mean([j[np.random.default_rng(s).permutation(len(j))[:8]].min() for s in range(200)])
    pct = lambda v: 100 * np.mean(j < v)
    res.append((g, te.sum(), j.min(), first8, pick8, rnd, pct(first8), pct(pick8)))
    print(f'{g[:36]:36s} n={te.sum():3d} lane best {j.min():6.2f} | earliest-8 {first8:6.2f} | pred-8 {pick8:6.2f} | random-8 {rnd:6.2f}')
R = np.array([r[2:] for r in res], float)
print('lanes', len(R), '(an7 reported 19)')
print('median gap to lane best: earliest-8 %.2f, predictor-8 %.2f, random-8 %.2f' %
      tuple(np.median(R[:, k] - R[:, 0]) for k in (1, 2, 3)))
print('predictor-8 better than earliest-8 in %d of %d; better than random-8 in %d' %
      ((R[:, 2] < R[:, 1]).sum(), len(R), (R[:, 2] < R[:, 3]).sum()))

# ---- formula check ----
from hornlab_search.metrics.di import target_di_gaussian_db
wv = np.ones_like(f, dtype=float)
wv[(f >= 2500) & (f <= 5500)] = 2.0
ref = target_di_gaussian_db(80.0, 50.0)
bad = 0
tot = 0
for r in rows[:400]:
    if not (r['terms'] and r['bwh'] is not None and r['bwv'] is not None and r['di'] is not None):
        continue
    e_h = np.asarray(r['bwh']) - 80.0
    e_v = np.asarray(r['bwv']) - 50.0
    c = np.sum(np.where(e_h < 0, 2, 1)[band] * e_h[band] ** 2 * wv[band]) / np.sum(wv[band]) / 100 \
        + np.sum(np.where(e_v < 0, 2, 1)[band] * e_v[band] ** 2 * wv[band]) / np.sum(wv[band]) / 100
    d = np.mean((np.asarray(r['di'])[band] - ref) ** 2) / 10.0
    tot += 1
    if abs(c - r['terms']['cov']) > 0.02 or abs(d - r['terms']['di']) > 0.02:
        bad += 1
        if bad <= 5:
            print('MISMATCH', r['config'], 'cov', round(c, 3), r['terms']['cov'], 'di', round(d, 3), r['terms']['di'])
print('formula check: bad', bad, 'of', tot, '| ref DI', ref)
