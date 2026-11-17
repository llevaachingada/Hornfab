"""A3: error of the E1 curve head (27-d -> bw_h/bw_v/di -> coverage+DI) against the full-J terms.

10-fold CV per lane. Reports the weighted cov and DI contribution errors and the share of J that
the curve head does not model at all. Writes .a3/head_error.json.
"""
import json
import pathlib
import pickle
import sys
from types import SimpleNamespace

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import KFold

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import _cov_term_v5
from hornlab_search.metrics.di import target_di_gaussian_db

D = pickle.load(open(ROOT / '.a3/all.pkl', 'rb'))
recs, X, Y, T, J = D['recs'], D['X'], D['Y'], D['T'], D['J']
W, TERMS, LANES = D['wvec'], D['terms'], D['lanes']
F18 = np.asarray(pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))[0]['f'], float)
ICO, IDI = TERMS.index('cov'), TERMS.index('di')
UNM = [i for i in range(len(TERMS)) if i not in (ICO, IDI)]


def parts(Z, b):
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
        out.append([w['cov'] * cov / p.tolerances['cov'], w['di'] * di / p.tolerances['di']])
    return np.asarray(out)


out = {}
for g in LANES:
    ix = np.array([i for i, r in enumerate(recs) if r['lane'] == g])
    b = H.brief(pathlib.Path('runs') / recs[ix[0]]['run'] / 'config.yaml')
    Xg, Yg, Tg, Jg = X[ix], Y[ix], T[ix], J[ix]
    P = np.zeros_like(Yg)
    for tr, te in KFold(10, shuffle=True, random_state=0).split(Xg):
        P[te] = ExtraTreesRegressor(n_estimators=32, min_samples_leaf=2, random_state=0,
                                    n_jobs=2).fit(Xg[tr], Yg[tr]).predict(Xg[te])
    pt, pp = parts(Yg, b), parts(P, b)
    wc_t, wd_t = Tg[:, ICO] * W[ICO], Tg[:, IDI] * W[IDI]
    wc_p, wd_p = pp[:, 0], pp[:, 1]
    unmod = (Tg[:, UNM] * W[UNM]).sum(1)
    out[g] = dict(
        n=int(ix.size),
        cov_weighted_rmse=float(np.sqrt(((wc_p - wc_t) ** 2).mean())),
        di_weighted_rmse=float(np.sqrt(((wd_p - wd_t) ** 2).mean())),
        proxy_rmse=float(np.sqrt(((pp.sum(1) - pt.sum(1)) ** 2).mean())),
        proxy_rho=float(spearmanr(pp.sum(1), pt.sum(1))[0]),
        unmodelled_J_mean=float(unmod.mean()), J_mean=float(Jg.mean()),
        unmodelled_share=float(unmod.mean() / Jg.mean()),
        curve_cov_share=float(wc_t.mean() / Jg.mean()),
        curve_di_share=float(wd_t.mean() / Jg.mean()),
    )
    print(g, {k: round(v, 3) for k, v in out[g].items()}, flush=True)
json.dump(out, open(ROOT / '.a3/head_error.json', 'w'), indent=1)
print('medians', {k: round(float(np.median([out[g][k] for g in out])), 3)
                  for k in out[list(out)[0]]})
