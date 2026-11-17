"""A3 whole-surface descriptor arm: does A3-WS-v1 predict full J / the v7 terms better than the
old 27-number mesh descriptor and than the knobs, on the A1/N1b record set?

Denominators: 6 lanes x 10 designs built; klangfilm uses a different brief (smooth) so its J is not
comparable across the CD lanes and it is excluded from the J comparison. The test set is therefore
5 CD lanes x 10 designs = 50, of which 4 lanes (40 designs) are E1 Part A lanes; rf__section_axial_home
has only 51 CD rows and was below E1's 100-row lane floor.

Models: the E1 recipe (ExtraTrees 32, leaf 2) and ridge (alpha 1, standardised), plus standardised
1-nearest-neighbour. Within-lane leave-one-out and leave-one-lane-out. Writes .a3/ws_test.json.
"""
import json
import pathlib
import pickle

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = pathlib.Path('scratch/fable_architecture')
D = pickle.load(open(ROOT / '.a3/all.pkl', 'rb'))
W = pickle.load(open(ROOT / '.a3/ws_desc.pkl', 'rb'))
rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
recs, X, T, J = D['recs'], D['X'], D['T'], D['J']
byid = {(r['run'], r['h']): i for i, r in enumerate(recs)}
rowmap = {(r['run'], r['h']): r for r in rows}

items = []
for w in W['recs']:
    key = (w['run'], w['h'])
    if key not in byid:
        print('not in CD table (different brief / excluded):', w['lane'], w['h'])
        continue
    i = byid[key]
    items.append(dict(lane=w['lane'], run=w['run'], h=w['h'], idx=i,
                      ws=w['vec'], old=X[i], T=T[i], J=J[i]))
LANES = sorted({it['lane'] for it in items})
print('comparable designs', len(items), 'lanes', {g: sum(1 for it in items if it['lane'] == g) for g in LANES})
WS = np.asarray([it['ws'] for it in items])
OLD = np.asarray([it['old'] for it in items])
Tg = np.asarray([it['T'] for it in items])
Jg = np.asarray([it['J'] for it in items])
GB = np.asarray([it['lane'] for it in items])


def mk(kind):
    if kind == 'et':
        return ExtraTreesRegressor(n_estimators=32, min_samples_leaf=2, random_state=0, n_jobs=2)
    if kind == 'ridge':
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    raise ValueError(kind)


def pred_mode(kind, Xtr, ytr, Xte):
    if kind == 'nn':
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        a, b = (Xtr - mu) / sd, (Xte - mu) / sd
        d = ((b[:, None, :] - a[None, :, :]) ** 2).sum(-1)
        return ytr[np.argmin(d, 1)]
    m = mk(kind).fit(Xtr, ytr)
    return m.predict(Xte)


def evaluate(feats, mode, within=True, target='J'):
    out = {}
    for g in LANES:
        te = np.flatnonzero(GB == g)
        pe = []
        for i in te:
            if within:
                tr = np.array([j for j in te if j != i])
            else:
                tr = np.flatnonzero(GB != g)
            Xtr, Xte = feats[tr], feats[i:i + 1]
            if target == 'J':
                p = pred_mode(mode, Xtr, Jg[tr], Xte)
                pe.append(float(p[0]))
            else:
                p = pred_mode(mode, Xtr, Tg[tr], Xte)
                pe.append(float(p[0] @ D['wvec']))
        pe = np.asarray(pe)
        jt = Jg[te]
        out[g] = dict(n=int(te.size),
                      rho=float(spearmanr(pe, jt)[0]) if te.size > 2 else float('nan'),
                      med_abs=float(np.median(np.abs(pe - jt))),
                      rmse=float(np.sqrt(np.mean((pe - jt) ** 2))))
    return out


res = {}
for fname, feats in (('ws404', WS), ('old27', OLD)):
    for mode in ('et', 'ridge', 'nn'):
        for target in ('J', 'terms'):
            for within in (True, False):
                key = f'{fname}|{mode}|{target}|{"within" if within else "cross"}'
                r = evaluate(feats, mode, within, target)
                med = {k: np.median([v[k] for v in r.values()]) for k in ('rho', 'med_abs', 'rmse')}
                res[key] = dict(per_lane=r, median=med)
                print(key, 'median rho %.2f med|dJ| %.3f' % (med['rho'], med['med_abs']), flush=True)

# descriptor-space spread within / between lanes (standardised)
def spread(F):
    mu, sd = F.mean(0), F.std(0) + 1e-9
    Z = (F - mu) / sd
    within = []
    for g in LANES:
        ix = np.flatnonzero(GB == g)
        dd = np.linalg.norm(Z[ix][:, None] - Z[ix][None], axis=-1)
        within.append(dd[np.triu_indices(ix.size, 1)].mean())
    between = []
    for a in range(len(LANES)):
        for b in range(a + 1, len(LANES)):
            ia, ib = np.flatnonzero(GB == LANES[a]), np.flatnonzero(GB == LANES[b])
            between.append(np.linalg.norm(Z[ia][:, None] - Z[ib][None], axis=-1).mean())
    return float(np.mean(within)), float(np.mean(between))


res['spread'] = dict(ws=spread(WS), old=spread(OLD))
print('spread within/between ws', res['spread']['ws'], 'old', res['spread']['old'])
json.dump(res, open(ROOT / '.a3/ws_test.json', 'w'), indent=1)
print('wrote ws_test.json')
