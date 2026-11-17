"""A3 test: low-rank reconstruction fidelity of the stored response (cuts + balloon + z).

Read-only. Loads one lane, builds PCA bases from that lane's rows, reconstructs a Response and
scores through the parity harness, compares full J and terms. No fitting, no selection.
"""
import dataclasses
import pathlib
import pickle
import sys
import time
import collections

import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H
from hornlab_search.solve.cache import load_response

rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
data, _ = pickle.load(open(ROOT / '.e1/descriptors.pkl', 'rb'))
lane = sys.argv[1] if len(sys.argv) > 1 else 'hl__biradial_es_style_v7'
sel = [(r, y) for r, x, y in data if r['config'] == lane]
print('lane', lane, 'n', len(sel))
cfg = H.brief(pathlib.Path('runs') / sel[0][0]['run'] / 'config.yaml')

CUTS = []
BAL = []
Z = []
js = []
terms = []
t0 = time.time()
for r, _ in sel:
    resp = H.resp_from_run(pathlib.Path('runs') / r['run'], r['h'])
    met = H.metrics_parity(resp, cfg.target)
    J, t = H.score_v7(met, resp, cfg.target, cfg.weights, cfg.objective_params)
    off = float(np.mean(resp.spl_h_db[:, resp.axis_index]))
    CUTS.append(np.concatenate([resp.spl_h_db.ravel(), resp.spl_v_db.ravel()]) - off)
    BAL.append(resp.spl_balloon_db.ravel() - off)
    Z.append(np.asarray(resp.z_throat, float))
    js.append(J)
    terms.append(t)
print('loaded+scored', len(js), 'elapsed %.1fs' % (time.time() - t0))
CUTS = np.asarray(CUTS); BAL = np.asarray(BAL); Z = np.asarray(Z); js = np.asarray(js)
print('shapes', CUTS.shape, BAL.shape, Z.shape, 'J range', js.min(), js.max())

tmpl = H.resp_from_run(pathlib.Path('runs') / sel[0][0]['run'], sel[0][0]['h'])


def pca(X, k):
    mu = X.mean(0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    k = min(k, Vt.shape[0])
    return mu, Vt[:k], S[:k]


def recon(X, mu, V, k):
    return mu + (X - mu) @ V[:k].T @ V[:k]


for K in (8, 16, 24, 32, 48):
    mu_c, Vc, Sc = pca(CUTS, K)
    mu_b, Vb, Sb = pca(BAL, K)
    dJ = []
    tdiff = collections.defaultdict(list)
    for i in range(len(js)):
        c = recon(CUTS[i:i + 1], mu_c, Vc, K)[0]
        b = recon(BAL[i:i + 1], mu_b, Vb, K)[0]
        off = float(np.mean(tmpl.spl_h_db[:, tmpl.axis_index]))  # offset irrelevant; keep template
        resp = dataclasses.replace(
            tmpl, spl_h_db=(c[:18 * 73].reshape(18, 73) + off),
            spl_v_db=(c[18 * 73:].reshape(18, 73) + off),
            spl_balloon_db=(b.reshape(18, 512) + off), z_throat=Z[i] + 0j)
        met = H.metrics_parity(resp, cfg.target)
        J, t = H.score_v7(met, resp, cfg.target, cfg.weights, cfg.objective_params)
        dJ.append(J - js[i])
        for k in ('cov', 'rip', 'di', 'dislope', 'flat', 'load', 'distd', 'diag', 'flat_cv'):
            tdiff[k].append(t[k] - terms[i][k])
    dJ = np.asarray(dJ)
    print('K=%2d  dJ median %+.4f  p95|dJ| %.4f  max|dJ| %.4f  term max: %s' % (
        K, np.median(dJ), np.percentile(np.abs(dJ), 95), np.max(np.abs(dJ)),
        ', '.join('%s %.3f' % (k, np.max(np.abs(v))) for k, v in tdiff.items())))
print('lane J sd', np.std(js), 'range', js.max() - js.min())
