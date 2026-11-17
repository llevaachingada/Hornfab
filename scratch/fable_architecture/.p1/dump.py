"""Dump the report numbers from results.json + fairpool.json in a compact form."""
import json, pathlib
R = json.load(open('scratch/fable_architecture/.p1/results.json'))
F = json.load(open('scratch/fable_architecture/.p1/fairpool.json'))
print('META', R['meta'])
print('\nHOOK A sibling', {k: R['hookA']['sibling_holdout'][k] for k in ('n', 'rho', 'rho_vs_bestJ', 'top5_overlap_actual', 'top5_overlap_bestJ')})
print('HOOK A engine', {k: R['hookA']['engine_holdout'][k] for k in ('n', 'rho', 'rho_vs_bestJ', 'top5_overlap_actual', 'top5_overlap_bestJ')})
print('HOOK A equal40', {k: R['hookA']['equal40'][k] for k in ('rho', 'top5_overlap')})
print('\nHOOK A per lane (pred decile | actual decile | best J | outside)')
for g, v in R['hookA']['sibling_median_stat'].items():
    s = R['support'][g]
    print('%-40s %8.3f %8.3f  bestJ %6.2f  n=%3d outside=%3d' % (
        g[:40], v['pred'], v['actual'], R['hookA']['sibling_holdout']['bestJ'][list(R['hookA']['sibling_median_stat']).index(g)],
        s['n'], s['outside']))
print('\nHOOK A ranks')
pv = R['hookA']['sibling_holdout']['pred']; av = R['hookA']['sibling_holdout']['actual']
import numpy as np
pr = np.argsort(np.argsort(pv)) + 1
ar = np.argsort(np.argsort(av)) + 1
for g, p, a in zip(R['hookA']['sibling_median_stat'], pr, ar):
    print('%-40s pred_rank %2d actual_rank %2d' % (g[:40], p, a))
print('\nHOOK B rows')
for h in R['hookB']['rows']:
    print('%-40s n=%3d firstJ %6.2f predJ %6.2f randJ %6.2f | firstS %6.3f predS %6.3f randS %6.3f | outside=%s' % (
        h['lane'][:40], h['n'], h['firstJ'], h['predJ'], h['randomJ'], h['firstS'], h['predS'], h['randomS'], h['pred_outside']))
print('\nHOOK B summary', R['hookB']['summary'])
print('\nHOOK C')
for k in ('8', '16', '32'):
    c = R['hookC'][k]
    print(k, {kk: c[kk] for kk in c if kk != 'rows'})
print('\nSKIP', R['skip']['rate'], R['skip']['pooled_skipped_top10'], R['skip']['pooled_skipped'],
      R['skip_actual_covdi'])
worst = sorted(R['skip']['lanes'], key=lambda x: -x['rate'])[:6]
print('worst skip lanes', worst)
print('\nFAIRPOOL')
print('run algos', F['cma_run_algorithms'])
for k, v in F['lanes'].items():
    print('%-42s obs=%3d exp_rec=%3d upper=%3d arms=%d' % (k, v['observations'], v['recorded_exploration'], v['upper_bound_model_free'], len(v['arms'])))
print('lanes <30 recorded model-free:', sum(1 for v in F['lanes'].values() if v['recorded_exploration'] < 30), 'of', len(F['lanes']))
print('lanes <30 even at upper bound:', len(F['lanes_with_fewer_than_30_unbiased']), 'of', len(F['lanes']))
print('support thresholds')
for k, v in R['support'].items():
    print('%-40s thr=%.2f p99=%.2f outside=%3d med=%.2f' % (k[:40], v['threshold'], v['p99_train_nn'], v['outside'], v['median_dist']))
