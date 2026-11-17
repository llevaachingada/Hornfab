"""A3 tables from results.json / terms.json / ws_test.json. Read-only."""
import json
import pathlib
import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture/.a3')
R = json.load(open(ROOT / 'results.json'))
TM = json.load(open(ROOT / 'terms.json'))
WS = json.load(open(ROOT / 'ws_test.json'))
KS = ('score', 'score_desc', 'resp_curve', 'resp_term', 'actual', 'random',
      'resp_curve_tr', 'resp_term_tr')

print('=== Part A: hit sets and medians (truth = full J, threshold best+0.1) ===')
print('lane,n,best,hit0.1,hitdec,proxyrho,proxbestrank,proxbesttopdec,' + ','.join(KS))
rows = []
for g, v in R['lanes'].items():
    rows.append([g, v['n'], v['best'], v['hit_n_0p1'], v['hit_n_decile'], v['proxy_spearman'],
                 v['proxy_best_rank'], int(v['proxy_best_J_top_decile'])] + [v['median'][k] for k in KS])
    print(','.join(str(x) if not isinstance(x, float) else '%.3f' % x for x in rows[-1]))
med = {k: float(np.median([R['lanes'][g]['median'][k] for g in R['lanes']])) for k in KS}
print('MEDIAN LANE', {k: round(v, 2) for k, v in med.items()})
print('n lanes', len(R['lanes']))

print('\n=== Part A: floor occupancy (starts whose initial 8 already contains a hit) ===')
for k in KS:
    n8 = sum(1 for g in R['lanes'] for x in R['lanes'][g]['reveals'][k] if x == 8)
    print(k, n8, '/', 10 * len(R['lanes']))

print('\n=== Part A decile outcome (top-decile hit, secondary) ===')
medd = {k: float(np.median([R['lanes'][g]['median_decile'][k] for g in R['lanes']])) for k in KS}
print('MEDIAN LANE decile', {k: round(v, 2) for k, v in medd.items()})

print('\n=== Part A pass-line arithmetic (Part A: resp at most half of score and actual) ===')
for g, v in R['lanes'].items():
    print(g, 'resp_curve %.1f score %.1f actual %.1f half(score)=%.1f half(actual)=%.1f' % (
        v['median']['resp_curve'], v['median']['score'], v['median']['actual'],
        v['median']['score'] / 2, v['median']['actual'] / 2))

print('\n=== Part B: transfer effect (same lane, medians) ===')
for g, v in R['lanes'].items():
    print(g, 'curve %.1f -> tr %.1f ; term %.1f -> tr %.1f' % (
        v['median']['resp_curve'], v['median']['resp_curve_tr'],
        v['median']['resp_term'], v['median']['resp_term_tr']))
d = [R['lanes'][g]['median']['resp_curve_tr'] - R['lanes'][g]['median']['resp_curve'] for g in R['lanes']]
d2 = [R['lanes'][g]['median']['resp_term_tr'] - R['lanes'][g]['median']['resp_term'] for g in R['lanes']]
print('median delta curve %.1f (%% %.0f), term %.1f (%% %.0f)' % (
    np.median(d), 100 * np.median(d) / np.median([R['lanes'][g]['median']['resp_curve'] for g in R['lanes']]),
    np.median(d2), 100 * np.median(d2) / np.median([R['lanes'][g]['median']['resp_term'] for g in R['lanes']])))

print('\n=== Part C ===')
for e, v in R['partC'].items():
    print(e, 'n', v['n'], 'top_n', v['top_n'], 'train curve/term', v['n_train_curve'], v['n_train_term'])
    for k in ('score_desc', 'resp_term', 'resp_curve_proxy', 'resp_curve_proxy_on_proxy_truth'):
        print('   ', k, 'top10 %.3f top25 %.3f' % (v[k]['top10'], v[k]['top25']))

print('\n=== Term error (10-fold CV of the 27-d -> 9-term head) ===')
print('lane,n,J_rmse,J_medabs,Jrho,proxy_r,gap_mean,shares(cov,dislope,diag,load,flat_cv)')
for g, v in TM.items():
    print(g, v['n'], '%.3f %.3f %.2f %.2f %.2f' % (v['J_rmse'], v['J_med_abs'], v['J_spearman'],
                                                   v['proxy_r'], v['proxy_gap_mean']),
          {k: round(v['term_share_J'][k], 2) for k in ('cov', 'dislope', 'diag', 'load', 'flat_cv')})
sh = {k: float(np.mean([TM[g]['term_share_J'][k] for g in TM])) for k in TM[list(TM)[0]]['term_share_J']}
print('mean shares', {k: round(v, 3) for k, v in sh.items()})
rm = {k: float(np.median([TM[g]['term_rmse'][k] for g in TM])) for k in sh}
print('median normalized RMSE', {k: round(v, 3) for k, v in rm.items()})
print('J composition share (mean over lanes)', {k: round(float(np.mean([TM[g]['J_composition_share'][k] for g in TM])), 3) for k in sh})
print('best-design LOO dJ', {g: round(TM[g]['best_loo_dJ'], 2) for g in TM})
print('proxy gap resid max', max(TM[g]['proxy_gap_resid_max'] for g in TM))

print('\n=== Whole-surface descriptors (A3-WS-v1) ===')
for k in ('ws404|et|J|within', 'ws404|et|J|cross', 'ws404|et|terms|within', 'ws404|et|terms|cross',
          'old27|et|J|within', 'old27|et|J|cross', 'old27|et|terms|within', 'old27|et|terms|cross',
          'ws404|ridge|J|within', 'old27|ridge|J|within'):
    print(k, WS[k]['median'])
print('spread', WS['spread'])
print('\nWS per-lane within terms et:')
for g, v in WS['ws404|et|terms|within']['per_lane'].items():
    print('  ', g, v)
print('OLD per-lane within terms et:')
for g, v in WS['old27|et|terms|within']['per_lane'].items():
    print('  ', g, v)
