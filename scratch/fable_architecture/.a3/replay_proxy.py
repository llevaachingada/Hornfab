"""A3 paired control: the SAME Part A replay with E1's coverage+DI proxy as the truth.

Purpose: isolate the proxy-objective explanation. `resp_curve` is the identical selector in
replay.py (27-d descriptor -> bw_h/bw_v/di -> proxy); here the truth and hit threshold are also the
proxy. `score`/`score_desc` are retargeted at the proxy, because a score model must predict the
objective it is judged on. Compare with results.json (full-J truth) lane by lane.

Writes .a3/results_proxy.json.
"""
import json
import pathlib
import pickle
import sys
from types import SimpleNamespace

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import _cov_term_v5
from hornlab_search.metrics.di import target_di_gaussian_db

D = pickle.load(open(ROOT / '.a3/all.pkl', 'rb'))
recs, X, Y = D['recs'], D['X'], D['Y']
LANES = D['lanes']
STARTS, BATCH = 10, 8
rows_all = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
byid = {(r['run'], r['h']): r for r in rows_all}
knob_keys = D['knob_keys']
F18 = np.asarray(rows_all[0]['f'], float)


def model():
    return ExtraTreesRegressor(n_estimators=32, min_samples_leaf=2, random_state=0, n_jobs=2)


def proxy_curve(Z, b):
    t, p = b.target, b.objective_params
    w = H.resolve_v7_weights(b.weights)
    band = (F18 >= t.band_lo_hz) & (F18 <= t.band_hi_hz)
    ref = t.di_target_db if t.di_target_db is not None else target_di_gaussian_db(
        t.coverage_h_deg, t.coverage_v_deg)
    out = []
    for z in np.atleast_2d(Z):
        m = SimpleNamespace(bw_h_deg=z[:18], bw_v_deg=z[18:36])
        cov = _cov_term_v5(m, None, t, F18, band, p)
        di = float(np.mean((z[36:][band] - ref) ** 2)) / 10.0
        out.append(w['cov'] * cov / p.tolerances['cov'] + w['di'] * di / p.tolerances['di'])
    return np.asarray(out)


def reveals(order, values, thr):
    return max(8, next((j + 1 for j, i in enumerate(order) if values[i] <= thr), len(order) + 1))


out = {}
for g in LANES:
    ix = np.array([i for i, r in enumerate(recs) if r['lane'] == g])
    b = H.brief(pathlib.Path('runs') / recs[ix[0]]['run'] / 'config.yaml')
    Xg, Yg = X[ix], Y[ix]
    K = []
    ks = knob_keys[g]
    for i in ix:
        r = byid[(recs[i]['run'], recs[i]['h'])]
        src = r['knobs'] if r['knobs'] else r['params']
        K.append([float(src[k]) for k in ks])
    K = np.asarray(K, float)
    truth = proxy_curve(Yg, b)
    thr = float(truth.min()) + 0.1
    dec = float(np.quantile(truth, 0.1))
    vals = {k: [] for k in ('score', 'score_desc', 'resp_curve', 'actual', 'random')}
    decs = {k: [] for k in vals}
    n = len(ix)
    for seed in range(STARTS):
        rng = np.random.default_rng(seed)
        start = list(rng.choice(n, BATCH, replace=False))
        remaining = [i for i in range(n) if i not in start]
        act = start[:] + remaining
        rnd = start[:] + list(np.random.default_rng(seed).permutation(remaining))
        for kind in vals:
            order = start[:]
            rem = remaining[:]
            if kind == 'actual':
                order = act
            elif kind == 'random':
                order = rnd
            else:
                while rem:
                    tr = np.array(order)
                    if kind == 'score':
                        pred = model().fit(K[tr], truth[tr]).predict(K[rem])
                    elif kind == 'score_desc':
                        pred = model().fit(Xg[tr], truth[tr]).predict(Xg[rem])
                    else:
                        pred = proxy_curve(model().fit(Xg[tr], Yg[tr]).predict(Xg[rem]), b)
                    chosen = [rem[k] for k in np.argsort(pred, kind='stable')[:BATCH]]
                    order.extend(chosen)
                    rem = [k for k in rem if k not in chosen]
                    if any(truth[i] <= thr for i in chosen):
                        break
            vals[kind].append(reveals(order, truth, thr))
            decs[kind].append(reveals(order, truth, dec))
    out[g] = dict(n=n, hit_n=int((truth <= thr).sum()), hit_n_dec=int((truth <= dec).sum()),
                  median={k: float(np.median(vals[k])) for k in vals},
                  median_dec={k: float(np.median(decs[k])) for k in vals})
    print(g, out[g]['median'], flush=True)

json.dump(dict(lanes=out, meta=dict(starts=STARTS, batch=BATCH, truth='coverage+DI proxy')),
          open(ROOT / '.a3/results_proxy.json', 'w'), indent=1)
print('medians', {k: float(np.median([out[g]['median'][k] for g in out])) for k in out[list(out)[0]]['median']})
print('wrote results_proxy.json')
