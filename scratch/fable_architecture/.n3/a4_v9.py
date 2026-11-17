"""N3: A4's grid-independence measurement repeated under objective v9 (corridor coverage plus
the strict constancy cost). Read-only, CPU, no solve. Same 58 study screen/verify pairs, same
dense grids and interpolation as `.a4/a4.py`; metrics always from the parity-exact harness.

Primary quantity  J_v9       : objective v9 on corridor target T_co (H 60-90 deg from 700 Hz,
                               V 40-60 deg from 1000 Hz), block/weights exactly as `.a9/a9.py`
                               lines 17-22. Corridor and weights are R3 PLACEHOLDERS.
Secondary         J_v9+cons  : J_v9 + strict constancy cost from `.s1/replay.py`:
                               constancy(bw_h, 60, 80, onset 700) + 0.5*constancy(bw_v, 40, 60, onset 1000).

Stored J is never re-scored with plain compute_metrics.
"""
import sys, json, pathlib, warnings
import numpy as np
warnings.filterwarnings('ignore')
sys.path.insert(0, 'scratch/fable_architecture/.tmp')
import fable_replay_harness as H
from scipy.stats import spearmanr

# --- v9 target / block / weights, verbatim from .a9/a9.py lines 17-22 -----------------------
BASE = {'coverage_h_deg': 80., 'coverage_v_deg': 50., 'band_lo_hz': 350., 'band_hi_hz': 8000.,
        'f0_hz': 700., 'f0_v_hz': 1000., 'di_slope_target': 0., 'z_min': .5,
        'loaded_hi_hz': 5600., 'freq_weights': {'band_hz': [[2500., 5500., 2.]]}}
BLOCK = {'version': 9, 'flat_band': 'scored', 'cov_v_weight': .5, 'cov_narrow_ratio': 2.,
         'cov_below_f0': 'mask',
         'tolerances': {'cov_profile': 3., 'rip': 1., 'flat': 1.5, 'load': .3,
                        'dislope': 9., 'di_roughness': .5, 'flat_cv': 1.5}}
WEIGHTS = {'cov_profile': 1., 'rip': 1., 'flat': .5, 'load': 1., 'dislope': 1.,
           'di_roughness': 1., 'flat_cv': 1.}
P9 = H.V9Params.from_block(BLOCK)
W9 = H.resolve_v9_weights(WEIGHTS, P9)
T_CO = H.Target.from_dict({**BASE, 'coverage_profile': {
    'mode': 'corridor',
    'h': [[700, 75, 60, 90], [8000, 75, 60, 90]],
    'v': [[1000, 50, 40, 60], [8000, 50, 40, 60]]}})
KEYS9 = ['cov_profile', 'rip', 'flat', 'load', 'dislope', 'di_roughness', 'flat_cv']


def constancy(f, b, lo, hi, onset):
    """Strict per-plane constancy cost, verbatim from .s1/replay.py (linear=False).

    Returns (cost, fitted_level). The caller supplies the corridor bounds.
    """
    m = (f >= onset) & (f <= 8000) & np.isfinite(b)
    a = b[m]
    if a.size < 2:
        return float('nan'), float('nan')
    x = np.log10(f[m])
    level = np.clip(a.mean(), lo, hi)
    return float(np.mean((a - level) ** 2) / 25), float(level)


def score9(resp):
    """v9 J, weighted per-term contributions, and the strict constancy cost on this grid.

    ``cons``   : H level clipped to the T_co corridor bound 60-90 deg (the N3 secondary).
    ``cons_s1``: H bound 60-80 deg, i.e. .s1/replay.py's literal call (labelled sensitivity).
    """
    m = H.metrics_parity(resp, T_CO)
    j, t = H.score_v9(m, resp, T_CO, WEIGHTS, P9)
    f = np.asarray(m.freqs_hz)
    ch, lh = constancy(f, np.asarray(m.bw_h_deg), 60, 90, 700)
    cv, lv = constancy(f, np.asarray(m.bw_v_deg), 40, 60, 1000)
    ch_s1, _ = constancy(f, np.asarray(m.bw_h_deg), 60, 80, 700)
    cons = ch + 0.5 * cv
    return {'j': float(j), 'jc': float(j + cons), 'cons': float(cons),
            'jc_s1': float(j + ch_s1 + 0.5 * cv), 'cons_s1': float(ch_s1 + 0.5 * cv),
            'ch': float(ch), 'cv': float(cv), 'lh': lh, 'lv': lv,
            'pen': float(t.get('penalty', 0.0)),
            'terms': {k: float(W9.get(k, 0.0)) * float(t.get(k, 0.0)) for k in KEYS9}}


def dense(resp, n):
    return H.interp_response(resp, np.geomspace(350.0, 8000.0, n), method='pchip')


rec = []
for S in sorted(pathlib.Path('runs').glob('study-*')):
    if not (S / 'screen/designs').is_dir() or not (S / 'verify/designs').is_dir():
        continue
    bs = H.brief(S / 'screen/config.yaml')      # v7 brief: used ONLY for the A4-style set rule
    for h in sorted({p.name for p in (S / 'screen/designs').iterdir()}
                    & {p.name for p in (S / 'verify/designs').iterdir()}):
        try:
            a = json.load(open(S / 'screen/designs' / h / 'status.json'))
            b = json.load(open(S / 'verify/designs' / h / 'status.json'))
            if not (a.get('ok') and b.get('ok')):
                continue
            rs = H.resp_from_run(S / 'screen', h)
            rv = H.resp_from_run(S / 'verify', h)
            # v7 screen J on the stored grid: reproduces A4's `top` membership rule exactly.
            m7 = H.metrics_parity(rs, bs.target)
            j7 = float(H.score_v7(m7, rs, bs.target, bs.weights, bs.objective_params)[0])
            d = {'h': h, 'study': S.name, 'v7_snative': j7,
                 'v_native': score9(rv), 's_native': score9(rs)}
            for n in (58, 116, 232):
                d[f'v_{n}'] = score9(dense(rv, n))
                d[f's_{n}'] = score9(dense(rs, n))
            rec.append(d)
        except Exception as e:
            print('skip', S.name, h[:8], repr(e)[:140])
print('pairs', len(rec))
print('penalty rows (v9):', sum(1 for r in rec for k in
      ('v_native', 's_native', 'v_58', 'v_116', 'v_232', 's_58', 's_116', 's_232')
      if r[k]['pen'] > 0.0))
print('constancy nan cells:', sum(1 for r in rec for k in
      ('v_native', 's_native', 'v_58', 'v_116', 'v_232', 's_58', 's_116', 's_232')
      if not np.isfinite(r[k]['cons'])))

# --- sanity: weighted contributions must sum to J_v9 (non-penalty rows) ---------------------
worst = max(abs(sum(r[k]['terms'].values()) - r[k]['j'])
            for r in rec for k in ('v_58', 'v_116', 'v_232') if r[k]['pen'] == 0.0)
print('max |sum(weighted terms) - J_v9|:', worst)

J = lambda k, fld='j': np.array([r[k][fld] for r in rec])
term = lambda k, t: np.array([r[k]['terms'][t] for r in rec])

N = len(rec)
allm = np.ones(N, bool)
# best 28: the 28 pairs with the LOWEST v9 dense-116 J (rule stated in the report)
b28 = np.zeros(N, bool)
b28[np.argsort(J('v_116'), kind='stable')[:min(28, N)]] = True
v7m = np.array([r['v7_snative'] for r in rec]) < 3.6


def line(name, a, b, m, fld='j', width=56):
    x, y = J(a, fld)[m], J(b, fld)[m]
    ok = np.isfinite(x) & np.isfinite(y)
    d = (y - x)[ok]
    rho = spearmanr(x[ok], y[ok])[0] if ok.sum() > 2 else float('nan')
    print(f'{name:{width}s} n={int(ok.sum()):2d} mean {d.mean():+.3f} sd {d.std(ddof=1):.3f} '
          f'spearman {rho:.3f}')


for fld, lab in (('j', 'J_v9 (PRIMARY)'), ('jc', 'J_v9 + constancy (secondary)'),
                 ('jc_s1', 'SENSITIVITY: J_v9 + .s1-literal constancy (H clip 60-80)')):
    print(f'\n== comparisons: {lab}')
    for m, mlab in ((allm, 'all 58'), (b28, 'best 28 by v9 dense-116'),
                    (v7m, 'A4-style v7 screen J<3.6')):
        print('--', mlab, f'n={int(m.sum())}')
        line('verify native(29) -> dense 58  [definition]', 'v_native', 'v_58', m, fld)
        line('dense 58 -> dense 116', 'v_58', 'v_116', m, fld)
        line('dense 116 -> dense 232', 'v_116', 'v_232', m, fld)
        line('DENSE 232: 18-pt source -> 29-pt source', 's_232', 'v_232', m, fld)
        line('DENSE 58 : 18-pt source -> 29-pt source', 's_58', 'v_58', m, fld)

print('\n== constancy: fitted H level vs T_co corridor [60, 90] (clip diagnostics)')
for k in ('v_native', 'v_58', 'v_116', 'v_232'):
    lh = np.array([r[k]['lh'] for r in rec])
    hi = int(np.sum(lh >= 90.0 - 1e-9))
    lo = int(np.sum(lh <= 60.0 + 1e-9))
    print(f'   {k:9s} mean level {lh.mean():6.2f} deg   at/above 90: {hi:2d}   at/below 60: {lo:2d}')

print('\n== constancy cost levels (J-independent), mean / sd')
for k in ('v_native', 'v_58', 'v_116', 'v_232', 's_58', 's_232'):
    c = J(k, 'cons')
    print(f'   {k:9s} all {np.nanmean(c):+.4f} / {np.nanstd(c, ddof=1):.4f}   '
          f'best28 {np.nanmean(c[b28]):+.4f} / {np.nanstd(c[b28], ddof=1):.4f}')
print('-- constancy contribution to the paired differences (mean / sd, all | best 28)')
for a, b, lab in (('v_58', 'v_116', 'dense 58 -> 116'),
                  ('v_116', 'v_232', 'dense 116 -> 232'),
                  ('s_232', 'v_232', 'dense 232: 18 -> 29 solved')):
    d = J(b, 'cons') - J(a, 'cons')
    print(f'   {lab:26s} all {d.mean():+.4f} / {d.std(ddof=1):.4f}   '
          f'best28 {d[b28].mean():+.4f} / {d[b28].std(ddof=1):.4f}')

print('\n== weighted per-term contributions to J_v9 differences, mean / sd (all | best 28)')
for a, b, lab in (('v_native', 'v_58', 'native 29 -> dense 58'),
                  ('v_58', 'v_232', 'dense 58 -> dense 232'),
                  ('s_232', 'v_232', 'dense: 18-pt source -> 29-pt source')):
    print('--', lab)
    for t in KEYS9:
        d = term(b, t) - term(a, t)
        print(f'   {t:13s} all {d.mean():+.4f} / {d.std(ddof=1):.4f}   '
              f'best28 {d[b28].mean():+.4f} / {d[b28].std(ddof=1):.4f}')

print('\n== J_v9 levels (mean / sd) and constancy share')
for k in ('v_native', 'v_58', 'v_116', 'v_232', 's_232'):
    j, c = J(k), J(k, 'cons')
    print(f'   {k:9s} J_v9 {j.mean():+.3f} / {j.std(ddof=1):.3f}   '
          f'J+cons {(j + c).mean():+.3f} / {(j + c).std(ddof=1):.3f}   '
          f'constancy share {np.mean(c / (j + c)):.2%}')

print('\n== cross-check against A4 records (v7 screen J on the stored grid; same harness)')
try:
    A4R = json.load(open('scratch/fable_architecture/.a4/records.json'))
    by_h = {r['h']: r['s_native'][0] for r in A4R}
    d = [abs(r['v7_snative'] - by_h[r['h']]) for r in rec if r['h'] in by_h]
    a4_top = {r['h'] for r in A4R if r['s_native'][0] < 3.6}
    our_top = {r['h'] for r in rec if r['v7_snative'] < 3.6}
    print(f'   n={len(d)}  max |J_v7 diff| {max(d):.2e}  '
          f'A4 set n={len(a4_top)}  our set n={len(our_top)}  '
          f'overlap {len(a4_top & our_top)}')
except FileNotFoundError:
    print('   .a4/records.json absent; skipped')

print('\n== set overlap')
print('best28 & v7set:', int((b28 & v7m).sum()), 'of', int(b28.sum()), '/', int(v7m.sum()))
print('v7set size:', int(v7m.sum()))
