"""A3 extra tables: informative-start reveals (floor excluded), and Part C decile composition."""
import json
import pathlib
import pickle
import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture/.a3')
R = json.load(open(ROOT / 'results.json'))
RP = json.load(open(ROOT / 'results_proxy.json'))
D = pickle.load(open(ROOT / 'all.pkl', 'rb'))
recs, J = D['recs'], D['J']
ENGINE = np.array([r['engine'] for r in recs])

KS = ('score', 'score_desc', 'resp_curve', 'resp_term', 'actual', 'random')
print('=== Part A: reveals above the 8-reveal floor, starts where the initial set is not a hit ===')
print('lane,n_inf,' + ','.join(KS))
agg = {k: [] for k in KS}
for g, v in R['lanes'].items():
    vals = {}
    n_inf = None
    for k in KS:
        a = np.array(v['reveals'][k], float)
        a = a[a > 8] - 8
        n_inf = a.size
        vals[k] = float(np.median(a)) if a.size else float('nan')
        agg[k].append(vals[k])
    print(g, n_inf, ','.join('%.1f' % vals[k] for k in KS))
print('MEDIAN', {k: round(float(np.nanmedian(agg[k])), 1) for k in KS})

print('\n=== Paired proxy-truth vs full-J truth (same selector, lane medians) ===')
print('lane,score_proxy,score_J,curve_proxy,curve_J,delta_curve,delta_score')
dc, ds = [], []
for g in R['lanes']:
    a = RP['lanes'][g]['median']; b = R['lanes'][g]['median']
    dc.append(b['resp_curve'] - a['resp_curve']); ds.append(b['score'] - a['score'])
    print(g, a['score'], b['score'], a['resp_curve'], b['resp_curve'],
          b['resp_curve'] - a['resp_curve'], b['score'] - a['score'])
print('median', 'score %+.1f curve %+.1f' % (np.median(ds), np.median(dc)))

print('\n=== Part C held-out decile composition (full J truth) ===')
for e in ('GEN-FF', 'GRID', 'OSSE'):
    te = np.flatnonzero(ENGINE == e)
    j = J[te]
    dec = np.quantile(j, 0.1)
    sel = te[j <= dec]
    lanes = [recs[i]['lane'] for i in sel]
    from collections import Counter
    c = Counter(lanes)
    print(e, 'pool', te.size, 'decile', sel.size, 'J range %.2f..%.2f' % (j.min(), j.max()),
          'top lane share %.2f' % (c.most_common(1)[0][1] / sel.size),
          'lanes in decile', dict(c.most_common(4)),
          'J decile range %.2f..%.2f' % (j[j <= dec].min(), j[j <= dec].max()))
