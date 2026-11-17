"""P1 predictor replay (hooks A, B, C + skip test), all valid stored rows.

Read-only CPU analysis.  Predictor: the .fable/an3.py ExtraTrees response model (27 shape
descriptors -> 18-freq H/V beamwidth + DI).  Objective proxy: the repo's own v7 cov and di terms
on the parity-exact stored metrics (verified against stored terms); full-J prediction is NOT
available and is never substituted.  Splits: the existing strict sibling groups (.x3/strict.py)
and engine groups.  Order within a lane: created_utc (chronological), tie-break (run, n).
"""
import pickle, pathlib, collections, re, json, sys, warnings
import numpy as np
warnings.filterwarnings('ignore')
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.types import MetricSet
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective.scalar_v7 import _cov_term_v5
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.neighbors import NearestNeighbors
from scipy.stats import spearmanr

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
OUT = REPO / 'scratch/fable_architecture/.p1'
rng_global = np.random.default_rng(0)

# ---------------------------------------------------------------- data
rows_all = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb'))
            if r['ok'] and r['f'] and len(r['f']) == 18]
D = np.load(OUT / 'desc_all.npz')
keep = D['keep']
idx = np.where(keep)[0]
rows = [rows_all[i] for i in idx]
X = D['X'][idx]
G = np.array([r['config'] for r in rows])
B = np.array([str(r['brief']) for r in rows])
Y = np.array([np.concatenate([r['bwh'], r['bwv'], r['di']]) for r in rows], float)
J = np.array([float(r['J']) for r in rows])
N = np.array([int(r['n'] or 0) for r in rows])
CREATED = np.array([str(r['created'] or '') for r in rows])
RUN = np.array([r['run'] for r in rows])
nf = 18


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
E = np.array(['OSSE' if r['gen'] == '' else ('GRID' if r['gen'] == 'grid' else 'GEN-FF') for r in rows])

brief = H.landscape_brief()
T, W, P = brief.target, brief.weights, brief.objective_params
F = np.array(rows[0]['f'], float)
BAND = (F >= T.band_lo_hz) & (F <= T.band_hi_hz)
REF_DI = target_di_gaussian_db(T.coverage_h_deg, T.coverage_v_deg)
W_DI = float(W['di'])
TOL = P.tolerances


def covdi(bwh, bwv, di):
    """Tolerance-normalised v7 cov + v7 di, and their weighted sum (coverage-plus-DI)."""
    m = MetricSet(freqs_hz=F, bw_h_deg=np.asarray(bwh, float), bw_v_deg=np.asarray(bwv, float),
                  di_db=np.asarray(di, float), di_source='balloon',
                  ripple_h_db=np.full(F.size, np.nan), ripple_v_db=np.full(F.size, np.nan),
                  on_axis_db=np.full(F.size, np.nan), z_throat_real=None)
    cov = _cov_term_v5(m, None, T, F, BAND, P) / TOL['cov']
    di_s = float(np.mean((np.asarray(di, float)[BAND] - REF_DI) ** 2) / 10.0 / TOL['di'])
    return float(cov), di_s, float(cov + W_DI * di_s)


# actual terms, all rows; verify against stored
ACT_C, ACT_D, ACT_S = np.zeros(len(rows)), np.zeros(len(rows)), np.zeros(len(rows))
for i, r in enumerate(rows):
    ACT_C[i], ACT_D[i], ACT_S[i] = covdi(r['bwh'], r['bwv'], r['di'])
stored_dir = np.array([float(r['terms']['di']) for r in rows])
stored_cov = np.array([float(r['terms']['cov']) for r in rows])

# test lanes: an7's inclusion rule on the full data (cd brief, >= 40 rows)
cnt = collections.Counter(G)
LANES = sorted([g for g in cnt if cnt[g] >= 40 and set(B[G == g]) == {'cd'}])
test_mask = np.isin(G, LANES)
max_cov_err = float(np.nanmax(np.abs(ACT_C[test_mask] - stored_cov[test_mask])))
max_di_err = float(np.nanmax(np.abs(ACT_D[test_mask] - stored_dir[test_mask])))
print(f'actual term check vs stored (19 test lanes): max |cov| err {max_cov_err:.4f}, '
      f'max |di| err {max_di_err:.4f}', flush=True)
assert max_cov_err < 0.02 and max_di_err < 0.02
# smooth lanes in the training pool use a different weight/objective block; their stored terms
# are not used by any hook, only their response curves enter training.
print('test lanes', len(LANES), flush=True)
for g in LANES:
    print(f'  {g:42s} n={cnt[g]}', flush=True)

# chronological order within a lane
def order_key(i):
    return (CREATED[i], RUN[i], N[i])

lane_idx = {g: np.array(sorted(np.where(G == g)[0], key=order_key)) for g in LANES}

# ---------------------------------------------------------------- models
def fit_predict(train_mask, test_idx):
    m = ExtraTreesRegressor(200, min_samples_leaf=2, random_state=0, n_jobs=6).fit(X[train_mask], Y[train_mask])
    return m.predict(X[test_idx])


PRED_S = np.full(len(rows), np.nan)          # predicted covdi (sibling holdout)
PRED_C = np.full(len(rows), np.nan)
PRED_D = np.full(len(rows), np.nan)
OUTSIDE = np.zeros(len(rows), bool)
SUPPORT = {}

print('fitting sibling-holdout models', flush=True)
for g in LANES:
    te = np.where(G == g)[0]
    tr = S != sibling(g)
    Pp = fit_predict(tr, te)
    c, d, s = zip(*[covdi(Pp[k, :nf], Pp[k, nf:2 * nf], Pp[k, 2 * nf:]) for k in range(len(te))])
    PRED_C[te], PRED_D[te], PRED_S[te] = np.array(c), np.array(d), np.array(s)
    # distance support from the sibling-holdout training set
    mu, sd = X[tr].mean(0), X[tr].std(0)
    sd = np.where(sd < 0.05, 1.0, sd)
    Ztr = (X[tr] - mu) / sd
    nn = NearestNeighbors(n_neighbors=2).fit(Ztr)
    dtr = nn.kneighbors(Ztr)[0][:, 1]
    thr = float(1.5 * np.percentile(dtr, 99))
    Zte = (X[te] - mu) / sd
    dte = NearestNeighbors(n_neighbors=1).fit(Ztr).kneighbors(Zte)[0][:, 0]
    OUTSIDE[te] = dte > thr
    SUPPORT[g] = {'threshold': thr, 'p99_train_nn': float(np.percentile(dtr, 99)),
                  'max_train_nn': float(dtr.max()),
                  'outside': int(OUTSIDE[te].sum()), 'n': int(len(te)),
                  'median_dist': float(np.median(dte)), 'max_dist': float(dte.max()),
                  'beyond_train_max': int((dte > dtr.max()).sum())}

# engine-holdout predictions
PRED_ES = np.full(len(rows), np.nan)
ENGINE_SET = {}
for e in sorted(set(E[G != ''])):
    te = np.where(E == e)[0]
    tr = E != e
    if tr.sum() < 20:
        continue
    Pp = fit_predict(tr, te)
    PRED_ES[te] = np.array([covdi(Pp[k, :nf], Pp[k, nf:2 * nf], Pp[k, 2 * nf:])[2] for k in range(len(te))])
    ENGINE_SET[e] = int(te.size)

# ---------------------------------------------------------------- helpers
def decile_stat(v, frac=0.10):
    k = max(1, int(np.ceil(frac * len(v))))
    return float(np.mean(np.sort(v)[:k]))


def lane_result(g, pred, n_first=None, n_pred=None, seed=0):
    ii = lane_idx[g]
    j = J[ii]
    ps = pred[ii]
    order = np.argsort(ps, kind='stable')
    out = {'lane': g, 'n': int(len(ii)), 'bestJ': float(j.min()),
           'pred_decile': decile_stat(ps), 'act_decile': decile_stat(ACT_S[ii]),
           'bestJ_pred': float(j[order[0]]), 'firstJ': float(j[0]),
           'outside_pred': int(OUTSIDE[ii].sum()),
           'pred_pick_outside': bool(OUTSIDE[ii][order[0]])}
    return out


PRIMARY_A = {g: lane_result(g, PRED_S) for g in LANES}

# ---------------------------------------------------------------- hook A
def rank_report(pred_arr, label):
    if np.isnan(pred_arr[test_mask]).any():
        return {'label': label, 'status': 'unavailable',
                'n_nan': int(np.isnan(pred_arr[test_mask]).sum())}
    pv, av = [], []
    for g in LANES:
        ii = lane_idx[g]
        pv.append(decile_stat(pred_arr[ii]))
        av.append(decile_stat(ACT_S[ii]))
    pv, av = np.array(pv), np.array(av)
    rho = float(spearmanr(pv, av).statistic)
    jbest = np.array([J[lane_idx[g]].min() for g in LANES])
    rho_j = float(spearmanr(pv, jbest).statistic)
    top5p = set(np.argsort(pv)[:5])
    top5a = set(np.argsort(av)[:5])
    top5j = set(np.argsort(jbest)[:5])
    return {'label': label, 'n': int(len(LANES)), 'rho': rho, 'rho_vs_bestJ': rho_j,
            'top5_overlap_actual': len(top5p & top5a), 'top5_overlap_bestJ': len(top5p & top5j),
            'pred': pv.tolist(), 'actual': av.tolist(), 'bestJ': jbest.tolist()}


hookA = {
    'sibling_holdout': rank_report(PRED_S, 'sibling holdout'),
    'engine_holdout': rank_report(PRED_ES, 'engine holdout'),
    'sibling_median_stat': {g: {'pred': decile_stat(PRED_S[lane_idx[g]], 0.10),
                                'actual': decile_stat(ACT_S[lane_idx[g]], 0.10)} for g in LANES},
}
# equal-pool sensitivity: 40 rows per lane, fixed seed
rng = np.random.default_rng(12345)
sub = {}
for g in LANES:
    ii = lane_idx[g]
    pick = rng.permutation(len(ii))[:40]
    sub[g] = ii[pick]
pv = np.array([decile_stat(PRED_S[sub[g]]) for g in LANES])
av = np.array([decile_stat(ACT_S[sub[g]]) for g in LANES])
hookA['equal40'] = {'rho': float(spearmanr(pv, av).statistic),
                    'top5_overlap': len(set(np.argsort(pv)[:5]) & set(np.argsort(av)[:5])),
                    'pred': pv.tolist(), 'actual': av.tolist()}

# ---------------------------------------------------------------- hook B
def random_median_j(ii, k, rng):
    j = J[ii]
    return float(np.median([j[rng.permutation(len(j))[:k]].min() for _ in range(200)]))


hookB = []
for li, g in enumerate(LANES):
    ii = lane_idx[g]
    o = np.argsort(PRED_S[ii], kind='stable')
    rng = np.random.default_rng(1000 + li)
    rnd = float(np.median([J[ii][rng.permutation(len(ii))[:1]].min() for _ in range(200)]))
    hookB.append({'lane': g, 'n': int(len(ii)), 'firstJ': float(J[ii][0]),
                  'predJ': float(J[ii][o[0]]), 'randomJ': rnd,
                  'firstS': float(ACT_S[ii][0]), 'predS': float(ACT_S[ii][o[0]]),
                  'randomS': float(np.median(ACT_S[ii])),
                  'pred_outside': bool(OUTSIDE[ii][o[0]]),
                  'pred_rank_actual': float(np.mean(J[ii] < J[ii][o[0]]))})

hb = np.array([[h['firstJ'], h['predJ'], h['randomJ']] for h in hookB])
hbS = np.array([[h['firstS'], h['predS'], h['randomS']] for h in hookB])
hookB_sum = {'n': len(hookB),
             'pred_beats_first': int((hb[:, 1] < hb[:, 0]).sum()),
             'pred_beats_random': int((hb[:, 1] < hb[:, 2]).sum()),
             'random_beats_first': int((hb[:, 2] < hb[:, 0]).sum()),
             'median_gap_first': float(np.median(hb[:, 1] - hb[:, 0])),
             'median_gap_random': float(np.median(hb[:, 1] - hb[:, 2])),
             'covdi_pred_beats_first': int((hbS[:, 1] < hbS[:, 0]).sum()),
             'covdi_pred_beats_random': int((hbS[:, 1] < hbS[:, 2]).sum()),
             'covdi_random_beats_first': int((hbS[:, 2] < hbS[:, 0]).sum()),
             'outside_pick_lanes': [h['lane'] for h in hookB if h['pred_outside']]}

# ---------------------------------------------------------------- hook C
hookC = {}
def reveals(ii, target_j):
    cum = np.minimum.accumulate(J[ii])
    hit = np.where(cum <= target_j)[0]
    return int(hit[0] + 1) if hit.size else int(len(ii) + 1)


for k in (8, 16, 32):
    rec = []
    for li, g in enumerate(LANES):
        ii = lane_idx[g]
        kk = min(k, len(ii))
        order = np.argsort(PRED_S[ii], kind='stable')
        rng = np.random.default_rng(2000 + 100 * k + li)
        rand_best = float(np.median([J[ii][rng.permutation(len(ii))[:kk]].min() for _ in range(200)]))
        row = {'lane': g, 'n': int(len(ii)),
               'firstJ': float(J[ii][:kk].min()),
               'predJ': float(J[ii][order[:kk]].min()),
               'randomJ': rand_best,
               'pred_set_rank_actual': float(np.mean(J[ii] < J[ii][order[:kk]].min())),
               'firstS': float(ACT_S[ii][:kk].min()),
               'predS': float(ACT_S[ii][order[:kk]].min()),
               'randomS': float(np.median([ACT_S[ii][rng.permutation(len(ii))[:kk]].min()
                                           for _ in range(200)]))}
        for nm, v in (('first', row['firstJ']), ('pred', row['predJ']), ('random', row['randomJ'])):
            row['reveals_' + nm] = reveals(ii, v)
        rec.append(row)
    arr = np.array([[r['firstJ'], r['predJ'], r['randomJ'],
                     r['reveals_first'], r['reveals_pred'], r['reveals_random']] for r in rec])
    arrS = np.array([[r['firstS'], r['predS'], r['randomS']] for r in rec])
    hookC[k] = {'rows': rec,
                'pred_beats_first': int((arr[:, 1] < arr[:, 0]).sum()),
                'pred_beats_random': int((arr[:, 1] < arr[:, 2]).sum()),
                'random_beats_first': int((arr[:, 2] < arr[:, 0]).sum()),
                'covdi_pred_beats_first': int((arrS[:, 1] < arrS[:, 0]).sum()),
                'covdi_pred_beats_random': int((arrS[:, 1] < arrS[:, 2]).sum()),
                'covdi_random_beats_first': int((arrS[:, 2] < arrS[:, 0]).sum()),
                'median_reveals_first': float(np.median(arr[:, 3])),
                'median_reveals_pred': float(np.median(arr[:, 4])),
                'median_reveals_random': float(np.median(arr[:, 5])),
                'censored_pred': int((arr[:, 4] > np.array([r['n'] for r in rec])).sum())}

# ---------------------------------------------------------------- skip test
skip = {'pooled_skipped': 0, 'pooled_skipped_top10': 0, 'lanes': []}
for g in LANES:
    ii = lane_idx[g]
    j, ps = J[ii], PRED_S[ii]
    med = np.median(ps)
    skipped = ps > med                      # predictor's bottom half = worst predicted
    k = max(1, int(np.ceil(0.10 * len(j))))
    top = j <= np.sort(j)[k - 1]
    hit = int((skipped & top).sum())
    skip['pooled_skipped'] += int(skipped.sum())
    skip['pooled_skipped_top10'] += hit
    skip['lanes'].append({'lane': g, 'skipped': int(skipped.sum()), 'top10': int(top.sum()),
                          'skipped_in_top10': hit,
                          'rate': float(hit / max(1, skipped.sum()))})
skip['rate'] = float(skip['pooled_skipped_top10'] / max(1, skip['pooled_skipped']))
# sensitivity: top decile by actual covdi instead of J
skip_s = {'pooled_skipped': 0, 'pooled_hit': 0}
for g in LANES:
    ii = lane_idx[g]
    ps = PRED_S[ii]
    skipped = ps > np.median(ps)
    a = ACT_S[ii]
    k = max(1, int(np.ceil(0.10 * len(a))))
    top = a <= np.sort(a)[k - 1]
    skip_s['pooled_skipped'] += int(skipped.sum())
    skip_s['pooled_hit'] += int((skipped & top).sum())
skip_s['rate'] = float(skip_s['pooled_hit'] / max(1, skip_s['pooled_skipped']))

# ---------------------------------------------------------------- prediction quality per lane
qual = []
for g in LANES:
    ii = lane_idx[g]
    rho = spearmanr(PRED_S[ii], ACT_S[ii]).statistic
    qual.append({'lane': g, 'n': int(len(ii)), 'spearman_covdi': float(rho),
                 'outside': int(OUTSIDE[ii].sum())})

# ---------------------------------------------------------------- save
res = {'meta': {'n_rows': len(rows), 'n_desc': int(keep.sum()), 'lanes': len(LANES),
                'max_cov_err': max_cov_err, 'max_di_err': max_di_err,
                'ref_di': float(REF_DI), 'w_di': W_DI, 'tol_cov': TOL['cov'], 'tol_di': TOL['di']},
       'lanes': {g: int(cnt[g]) for g in LANES},
       'support': SUPPORT,
       'hookA': hookA,
       'hookB': {'rows': hookB, 'summary': hookB_sum},
       'hookC': hookC,
       'skip': skip, 'skip_actual_covdi': skip_s,
       'quality': qual,
       'engine_sizes': ENGINE_SET}
(OUT / 'results.json').write_text(json.dumps(res, indent=1))

print('\n=== HOOK A (lane ranking) ===')
for key in ('sibling_holdout', 'engine_holdout', 'equal40'):
    a = hookA[key]
    print(key, {k: a[k] for k in ('n', 'rho', 'top5_overlap', 'rho_vs_bestJ', 'top5_overlap_bestJ') if k in a})
print('\n=== HOOK B ===', hookB_sum)
print('\n=== HOOK C ===')
for k in (8, 16, 32):
    print(k, {kk: hookC[k][kk] for kk in ('pred_beats_first', 'pred_beats_random', 'random_beats_first',
                                          'covdi_pred_beats_first', 'covdi_pred_beats_random',
                                          'median_reveals_first', 'median_reveals_pred', 'median_reveals_random')})
# gate counts excluding lanes whose predictor pick is outside training support
hbo = [h for h in hookB if not h['pred_outside']]
print('hook B excluding outside-pick lanes:', sum(h['predJ'] < h['firstJ'] for h in hbo), 'of', len(hbo))
for k in (8, 16, 32):
    keep_l = {h['lane'] for h in hbo}
    rr = [r for r in hookC[k]['rows'] if r['lane'] in keep_l]
    print(f'hook C N={k} excluding outside-pick lanes:', sum(r['predJ'] < r['firstJ'] for r in rr), 'of', len(rr))
print('\n=== SKIP ===', skip['rate'], skip['pooled_skipped_top10'], '/', skip['pooled_skipped'],
      '| covdi-decile', skip_s['rate'], skip_s['pooled_hit'], '/', skip_s['pooled_skipped'])
print('\n=== per-lane ===')
for r in qual:
    g = r['lane']
    b = next(x for x in hookB if x['lane'] == g)
    print(f"{g[:40]:40s} n={r['n']:3d} rho={r['spearman_covdi']:+.2f} outside={r['outside']:3d} "
          f"| first {b['firstJ']:6.2f} pred {b['predJ']:6.2f} rand {b['randomJ']:6.2f} out={b['pred_outside']}")
