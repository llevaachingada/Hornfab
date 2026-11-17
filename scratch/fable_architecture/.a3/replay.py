"""A3 replay: E1 Part A/B/C repeated with parity-exact FULL J as the truth.

Truth = stored objective v7 J, verified equal to the parity-harness regeneration on every row
(.a3/all.pkl parity max|dJ| = 0). All ten lanes run v7; no J is compared across versions.

Selectors (all refit every 8 reveals, training only on revealed rows unless `tr` = transfer):
  score       knobs                -> J
  score_desc  27-d mesh descriptor -> J        (input control for the head comparison)
  resp_curve  27-d descriptor      -> bw_h/bw_v/di curves -> E1 coverage+DI proxy
  resp_term   27-d descriptor      -> the 9 normalized v7 terms -> J = sum_k w_k t_k
  actual      historical order
  random      shuffled order
  resp_curve_tr / resp_term_tr: + all rows from the other engine groups (Part B).

Also computes Part C (held-out engine ranking) and the secondary "top-decile" outcome.
Writes .a3/results.json.
"""
import collections
import json
import math
import pathlib
import pickle
import sys
import time
from types import SimpleNamespace

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import _cov_term_v5
from hornlab_search.metrics.di import target_di_gaussian_db

D = pickle.load(open(ROOT / '.a3/all.pkl', 'rb'))
recs, X, Y, T, J = D['recs'], D['X'], D['Y'], D['T'], D['J']
W = D['wvec']
TERMS = D['terms']
LANES = D['lanes']
ENGINE = np.array([r['engine'] for r in recs])
LANE = np.array([r['lane'] for r in recs])

# Curve heads are brief-agnostic: E1 trained them on every descriptor row, including the smooth
# brief. Term heads are brief-specific (normalized v7 CD terms) and train on CD rows only.
data_all, _ = pickle.load(open(ROOT / '.e1/descriptors.pkl', 'rb'))
X_all = np.asarray([x for _, x, _ in data_all], float)
Y_all = np.asarray([y for _, _, y in data_all], float)
E_all = np.array(['OSSE' if not r['gen'] else ('GRID' if r['gen'] == 'grid' else 'GEN-FF')
                  for r, _, _ in data_all])
print('all descriptor rows', len(X_all), 'CD rows', len(recs), flush=True)

BATCH = 8
STARTS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
LANE_FILTER = sys.argv[2] if len(sys.argv) > 2 else None
bench = {g: np.array([i for i, r in enumerate(recs) if r['lane'] == g]) for g in LANES}
knob_keys = D['knob_keys']
KG = {}
# rebuild knobs per lane from rows.pkl params/knobs (all.pkl kept only ragged lists)
rows_all = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
byid = {(r['run'], r['h']): r for r in rows_all}
for g in LANES:
    ks = knob_keys[g]
    rows_g = []
    for i in bench[g]:
        r = byid[(recs[i]['run'], recs[i]['h'])]
        src = r['knobs'] if r['knobs'] else r['params']
        rows_g.append([float(src[k]) for k in ks])
    KG[g] = np.asarray(rows_g, float)

briefs = {}
for g in LANES:
    r0 = recs[bench[g][0]]
    briefs[g] = H.brief(pathlib.Path('runs') / r0['run'] / 'config.yaml')
    b = briefs[g]
    assert b.objective_version == 7
    assert abs(D['wvec'] - np.array([H.resolve_v7_weights(b.weights)[k] for k in TERMS])).max() == 0


F18 = np.asarray(rows_all[0]['f'], float)


def proxy_curve(Z, b):
    t = b.target
    p = b.objective_params
    w = H.resolve_v7_weights(b.weights)
    f = F18
    band = (f >= t.band_lo_hz) & (f <= t.band_hi_hz)
    ref = t.di_target_db if t.di_target_db is not None else target_di_gaussian_db(
        t.coverage_h_deg, t.coverage_v_deg)
    outs = []
    for z in np.atleast_2d(Z):
        m = SimpleNamespace(bw_h_deg=z[:18], bw_v_deg=z[18:36])
        cov = _cov_term_v5(m, None, t, f, band, p)
        di = float(np.mean((z[36:][band] - ref) ** 2)) / 10.0
        outs.append(w['cov'] * cov / p.tolerances['cov'] + w['di'] * di / p.tolerances['di'])
    return np.asarray(outs)


def model(fit_n=32):
    return ExtraTreesRegressor(n_estimators=fit_n, min_samples_leaf=2, random_state=0, n_jobs=2)


def reveals(order, values, thr):
    n = len(order)
    return max(8, next((j + 1 for j, i in enumerate(order) if values[i] <= thr), n + 1))


def run_lane(g, starts=STARTS):
    ix = bench[g]
    n = len(ix)
    Jg, Tg, Xg, Kg, Yg = J[ix], T[ix], X[ix], KG[g], Y[ix]
    b = briefs[g]
    proxy_true = proxy_curve(Yg, b)
    best = float(Jg.min())
    thr = best + 0.1
    dec = np.quantile(Jg, 0.1)
    ext = np.flatnonzero(ENGINE != recs[ix[0]]['engine'])
    Xe, Te = X[ext], T[ext]
    ext_all = np.flatnonzero(E_all != recs[ix[0]]['engine'])
    Xa, Ya = X_all[ext_all], Y_all[ext_all]
    out = {k: [] for k in ('score', 'score_desc', 'resp_curve', 'resp_term', 'actual', 'random',
                           'resp_curve_tr', 'resp_term_tr')}
    outd = {k: [] for k in out}
    for seed in range(starts):
        rng = np.random.default_rng(seed)
        start = list(rng.choice(n, BATCH, replace=False))
        remaining = [i for i in range(n) if i not in start]
        rng2 = np.random.default_rng(seed)
        rand_order = start[:] + list(rng2.permutation(remaining))
        act_order = start[:] + remaining
        for kind in out:
            order = start[:]
            rem = remaining[:]
            if kind == 'actual':
                order = act_order
            elif kind == 'random':
                order = rand_order
            else:
                while rem:
                    tr = np.array(order)
                    if kind == 'score':
                        m = model().fit(Kg[tr], Jg[tr]); pred = m.predict(Kg[rem])
                    elif kind == 'score_desc':
                        m = model().fit(Xg[tr], Jg[tr]); pred = m.predict(Xg[rem])
                    elif kind == 'resp_curve':
                        m = model().fit(Xg[tr], Yg[tr]); pred = proxy_curve(m.predict(Xg[rem]), b)
                    elif kind == 'resp_term':
                        m = model().fit(Xg[tr], Tg[tr]); pred = m.predict(Xg[rem]) @ W
                    elif kind == 'resp_curve_tr':
                        m = model().fit(np.r_[Xa, Xg[tr]], np.r_[Ya, Yg[tr]])
                        pred = proxy_curve(m.predict(Xg[rem]), b)
                    elif kind == 'resp_term_tr':
                        m = model().fit(np.r_[Xe, Xg[tr]], np.r_[Te, Tg[tr]])
                        pred = m.predict(Xg[rem]) @ W
                    else:
                        raise ValueError(kind)
                    chosen = [rem[k] for k in np.argsort(pred, kind='stable')[:BATCH]]
                    order.extend(chosen)
                    rem = [k for k in rem if k not in chosen]
                    if any(Jg[i] <= thr for i in chosen):
                        break
            out[kind].append(reveals(order, Jg, thr))
            outd[kind].append(reveals(order, Jg, dec))
        if seed == 0:
            print('  lane', g, 'start0', {k: out[k][-1] for k in out}, flush=True)
    res = dict(n=n, best=best, thr=thr, decile=float(dec),
               hit_n_0p1=int((Jg <= thr).sum()), hit_n_decile=int((Jg <= dec).sum()),
               proxy_spearman=float(_spearman(proxy_true, Jg)),
               proxy_best_J_top_decile=bool(Jg[int(np.argmin(proxy_true))] <= dec),
               proxy_best_rank=int((Jg < Jg[int(np.argmin(proxy_true))]).sum()) + 1,
               reveals=out, reveals_decile=outd,
               median={k: float(np.median(out[k])) for k in out},
               median_decile={k: float(np.median(outd[k])) for k in outd})
    return res


def _spearman(a, b):
    from scipy.stats import spearmanr
    return spearmanr(a, b).statistic


results = dict(lanes={}, partC={}, meta=dict(starts=STARTS, batch=BATCH, terms=TERMS,
                                             wvec=[float(v) for v in W]))
t0 = time.time()
for g in LANES:
    print('lane', g, flush=True)
    results['lanes'][g] = run_lane(g)
    print('  median', results['lanes'][g]['median'], 'decile',
          results['lanes'][g]['median_decile'], 'elapsed %.0fs' % (time.time() - t0), flush=True)
    json.dump(results, open(ROOT / '.a3/results.json', 'w'), indent=1)

# ---------------- Part C: hold out one engine group entirely -------------------------------
cd = np.ones(len(recs), bool)
for engine in sorted(set(ENGINE)):
    tr = np.flatnonzero(ENGINE != engine)
    te = np.flatnonzero(ENGINE == engine)
    tr_all = np.flatnonzero(E_all != engine)
    mj = model().fit(X[tr], J[tr]); pj = mj.predict(X[te])
    mt = model().fit(X[tr], T[tr]); jt = mt.predict(X[te]) @ W
    mc = model().fit(X_all[tr_all], Y_all[tr_all])
    jc = proxy_curve(mc.predict(X[te]), briefs[LANES[0]])
    dec = np.quantile(J[te], 0.1)
    top = set(np.flatnonzero(J[te] <= dec))
    out = dict(n=int(te.size), top_n=len(top),
               n_train_curve=int(tr_all.size), n_train_term=int(tr.size))
    for name, est in (('score_desc', pj), ('resp_term', jt), ('resp_curve_proxy', jc)):
        rank = np.argsort(est, kind='stable')
        out[name] = dict(top10=float(len(top.intersection(rank[:int(np.ceil(te.size * .1))])) / max(1, len(top))),
                         top25=float(len(top.intersection(rank[:int(np.ceil(te.size * .25))])) / max(1, len(top))))
    # proxy truth vs full J truth for the curve head
    pt = proxy_curve(Y[te], briefs[LANES[0]])
    pdec = np.quantile(pt, 0.1)
    ptop = set(np.flatnonzero(pt <= pdec))
    rank = np.argsort(jc, kind='stable')
    out['resp_curve_proxy_on_proxy_truth'] = dict(
        top10=float(len(ptop.intersection(rank[:int(np.ceil(te.size * .1))])) / max(1, len(ptop))),
        top25=float(len(ptop.intersection(rank[:int(np.ceil(te.size * .25))])) / max(1, len(ptop))))
    results['partC'][engine] = out
    print('partC', engine, out, flush=True)
    json.dump(results, open(ROOT / '.a3/results.json', 'w'), indent=1)

print('DONE elapsed %.0fs' % (time.time() - t0))
