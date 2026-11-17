"""A3 term-error decomposition.

For each lane:
  * 10-fold CV of the response-functional head (27-d descriptors -> 9 normalized v7 terms),
    reporting per-term RMSE/bias (normalized units and weighted J units) and its share of
    sum_k |w_k * error_k|;
  * J error of the composed head (RMSE, median |dJ|, Spearman with truth, LOO error at the
    lane's best design);
  * the truth-level gap J - (coverage+DI proxy): which terms it is made of;
  * the curve head's own error: predicted cov/di vs true cov/di, and the unmodelled terms.

Writes .a3/terms.json.
"""
import collections
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
UNMODELLED = [k for k in TERMS if k not in ('cov', 'di')]


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
        out.append([w['cov'] * cov / p.tolerances['cov'], w['di'] * di / p.tolerances['di'],
                    w['cov'] * cov / p.tolerances['cov'] + w['di'] * di / p.tolerances['di']])
    return np.asarray(out)


out = {}
for g in LANES:
    ix = np.array([i for i, r in enumerate(recs) if r['lane'] == g])
    b = H.brief(pathlib.Path('runs') / recs[ix[0]]['run'] / 'config.yaml')
    Xg, Tg, Yg, Jg = X[ix], T[ix], Y[ix], J[ix]
    # ---- 10-fold CV of the term head
    P = np.zeros_like(Tg)
    kf = KFold(n_splits=10, shuffle=True, random_state=0)
    for tr, te in kf.split(Xg):
        P[te] = model().fit(Xg[tr], Tg[tr]).predict(Xg[te])
    Jp = P @ W
    err = P - Tg                      # normalized term error (pred - true)
    werr = err * W
    rmse_t = np.sqrt((err ** 2).mean(0))
    bias_t = err.mean(0)
    rmse_w = np.sqrt((werr ** 2).mean(0))
    share = np.abs(werr).mean(0) / np.abs(werr).mean(0).sum()
    r2 = 1 - (err ** 2).sum(0) / ((Tg - Tg.mean(0)) ** 2).sum(0)
    # leave-one-out prediction of the lane's best design
    best = int(np.argmin(Jg))
    loo = model().fit(np.delete(Xg, best, axis=0), np.delete(Tg, best, axis=0)).predict(Xg[best:best + 1])[0]
    loo_dJ = float(loo @ W - Jg[best])
    # ---- truth-level proxy gap
    pc = proxy_curve(Yg, b)
    gap = Jg - pc[:, 2]
    # exact check that the gap is the non-modelled weighted terms
    gap_terms = Tg[:, [TERMS.index(k) for k in UNMODELLED]] @ W[[TERMS.index(k) for k in UNMODELLED]]
    gap_resid = np.abs(gap - gap_terms).max()
    out[g] = dict(
        n=int(ix.size),
        term_rmse={k: float(v) for k, v in zip(TERMS, rmse_t)},
        term_bias={k: float(v) for k, v in zip(TERMS, bias_t)},
        term_rmse_J={k: float(v) for k, v in zip(TERMS, rmse_w)},
        term_share_J={k: float(v) for k, v in zip(TERMS, share)},
        term_r2={k: float(v) for k, v in zip(TERMS, r2)},
        J_rmse=float(np.sqrt(((Jp - Jg) ** 2).mean())),
        J_med_abs=float(np.median(np.abs(Jp - Jg))),
        J_spearman=float(spearmanr(Jp, Jg)[0]),
        J_sd=float(Jg.std()),
        best_J=float(Jg[best]), best_loo_dJ=loo_dJ,
        best_loo_dJ_terms={k: float(v) for k, v in zip(TERMS, (loo - Tg[best]) * W)},
        proxy_r=float(spearmanr(pc[:, 2], Jg)[0]),
        proxy_gap_mean=float(gap.mean()), proxy_gap_sd=float(gap.std()),
        proxy_gap_resid_max=float(gap_resid),
        J_composition={k: float((Tg[:, i] * W[i]).mean()) for i, k in enumerate(TERMS)},
        J_composition_share={k: float((Tg[:, i] * W[i]).mean() / Jg.mean()) for i, k in enumerate(TERMS)},
    )
    print(g, 'n', ix.size, 'J_rmse %.3f med %.3f rho %.2f' % (
        out[g]['J_rmse'], out[g]['J_med_abs'], out[g]['J_spearman']),
        'proxy r %.2f gap %.2f+-%.2f' % (out[g]['proxy_r'], gap.mean(), gap.std()),
        'best LOO dJ %+.2f' % loo_dJ, 'gap resid', gap_resid, flush=True)
    print('   shares', {k: round(out[g]['term_share_J'][k], 2) for k in TERMS}, flush=True)

json.dump(out, open(ROOT / '.a3/terms.json', 'w'), indent=1)
print('wrote terms.json')
