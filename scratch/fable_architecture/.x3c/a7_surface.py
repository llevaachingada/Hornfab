"""A7 part B1: whole-surface inputs from the contract-v2 records.

Source: scratch/fable_architecture/.n1b/build/*.npz (65 stations x 61 azimuths, generated
surface in metres, res 10 mm). Only lanes that PASS N1b are used; the lecleach lane is
excluded (X1B_CONTRACT_V2.md: not reproducible at HEAD). No lecleach substitution.

Descriptor version (fixed before scoring):
  surface-32v1, from the *inner* sampled sheet, 32 uniform arc stations (contract 7 wants
  >= 32 stations), 7 channels per station:
    half-width W(s)=max x, half-height H(s)=max y, mean depth z(s),
    quarter-section area A(s) (shoelace, x-y plane), aspect R=W/H,
    shape index A/(W*H) (pi/4 ellipse, 1 rectangle), wall angle atan2(dr/dz) in degrees
  plus three sizes: full mouth width 2*W(1), full mouth height 2*H(1), total depth.
  That is 32*7+3 = 227 features. surface-8v1 repeats it at 8 stations (59 features) as a
  lower-variance check, because n is small.

Targets are the stored responses of the *meshed* design (rows.pkl bwh/bwv/di + metrics.json),
as in .x3/extended.py. The description is the generator surface; for Crowe and rolled the
mesher departs from the generator by <=1.64 mm / <=0.70 mm at corners (X1B rule 3), which is
a stated limitation, not corrected here.

Because the contract records cover only 60 N1b-passing designs, this test also runs each
input set on the SAME 60 designs (matched comparison), so the only thing that changes is
the input representation. Splits are .x3/strict.py's lane / sibling / engine groups.
"""
import numpy as np, glob, json, pathlib, pickle, collections, sys
sys.path.insert(0, 'scratch/fable_architecture/.x3c')
from a7_common import load_base, sibling, skills, cov
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr

ROOT = 'scratch/fable_architecture'
KL_LEC = 'hl__lecleach_hv_landscape_smooth_v7'
Xb, Yb, Gb, Eb, idsb, rows, f = load_base()
nf = len(f); band = np.where(f >= 600)[0]

# ---------- assemble the 60-design whole-surface sample ----------
e1, _ = pickle.load(open(f'{ROOT}/.e1/descriptors.pkl', 'rb'))
prof = {(r['run'], r['h']): x for r, x, y in e1}

recs, dropped = [], collections.Counter()
for p in sorted(glob.glob(f'{ROOT}/.n1b/build/*.npz')):
    z = np.load(p, allow_pickle=True)
    lane = str(z['lane'])
    if lane == KL_LEC:
        dropped['lecleach not N1b-passing'] += 1
        continue
    h, run = str(z['design_hash']), str(z['run'])
    r = next((q for q in rows if q['run'] == run and q['h'] == h and q['ok']
              and q['f'] and len(q['f']) == 18), None)
    if r is None:
        dropped['no 18-point row'] += 1
        continue
    if (run, h) not in prof:
        dropped['no 27-number descriptor'] += 1
        continue
    try:
        m = json.loads((pathlib.Path('runs') / run / 'designs' / h / 'metrics.json').read_text())
        zz = np.array([m[k] for k in ('z_throat_real', 'ripple_h_db', 'ripple_v_db', 'on_axis_db')], float).ravel()
        y = np.r_[np.array(r['bwh'] + r['bwv'] + r['di'], float), zz]
        if len(y) != 126 or not np.isfinite(y).all():
            raise ValueError('bad target')
    except Exception as ex:
        dropped[str(ex)[:40]] += 1
        continue
    recs.append(dict(lane=lane, h=h, run=run, inner=z['inner'], y=y, x=prof[(run, h)],
                     engine=('OSSE' if r['gen'] == '' else 'GRID' if r['gen'] == 'grid' else 'GEN-FF'),
                     bbox=r['bbox']))
print('whole-surface sample', len(recs), 'dropped', dict(dropped))

bycfg = collections.Counter(rr['lane'] for rr in recs)
print('per lane', dict(bycfg))
print('per engine', dict(collections.Counter(rr['engine'] for rr in recs)))
print('also in the 1,715 base:', sum(rr['h'] in set(idsb) for rr in recs), 'of', len(recs))


# ---------- descriptor ----------
def surface_desc(inner, nst):
    A = np.asarray(inner, float)          # (61 azimuths, 65 stations, xyz) metres
    t = np.linspace(0, 1, A.shape[1])
    ts = np.linspace(0, 1, nst)
    J = np.empty((A.shape[0], nst, 3))
    for k in range(3):
        for i in range(A.shape[0]):
            J[i, :, k] = np.interp(ts, t, A[i, :, k])
    # (61,nst,3)
    rowsF = []
    for s in range(nst):
        x, y, z = J[:, s, 0], J[:, s, 1], J[:, s, 2]
        W, H = x.max(), y.max()
        Aq = 0.5 * abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))
        rowsF.append([W, H, z.mean(), Aq, W / H, Aq / (W * H), 0.0])
    F = np.array(rowsF)
    r = np.hypot(J[:, :, 0], J[:, :, 1]).mean(axis=0)
    dz = np.gradient(J[:, :, 2].mean(axis=0))
    dr = np.gradient(r)
    F[:, 6] = np.degrees(np.arctan2(dr, np.where(np.abs(dz) < 1e-12, 1e-12, dz)))
    depth = A[:, :, 2].max() - A[:, :, 2].min()
    return np.r_[2 * F[-1, 0], 2 * F[-1, 1], depth, F.ravel()]


S32 = np.array([surface_desc(rr['inner'], 32) for rr in recs])
S8 = np.array([surface_desc(rr['inner'], 8) for rr in recs])
XP = np.array([rr['x'] for rr in recs])
Y = np.array([rr['y'] for rr in recs])
G = np.array([rr['lane'] for rr in recs])
S = np.array([sibling(g) for g in G])
E = np.array([rr['engine'] for rr in recs])
print('feature widths size 3, profile %d, surface8 %d, surface32 %d' % (XP.shape[1], S8.shape[1], S32.shape[1]))

# descriptor sanity: full-horn W/H from the whole inner sheet vs 2 * stored quarter bbox.
# The npz record is in mm in the quarter model (max x 272.687 for a 272.687 mm quarter box),
# so full horn = 2x; X1B_CONTRACT_V2 doubles the same way.  The stored box can exceed the
# inner sheet by the outer sheet / mouth rim, so a small negative bias is expected and is
# reported per lane rather than tuned away.
bb = np.array([[rr['bbox'][3] - rr['bbox'][0], rr['bbox'][4] - rr['bbox'][1]] for rr in recs]) * 2 * 1000
glob = np.array([[2 * rr['inner'][:, :, 0].max(), 2 * rr['inner'][:, :, 1].max()] for rr in recs])
d = np.c_[glob[:, 0] - bb[:, 0], glob[:, 1] - bb[:, 1]]
print('full inner W/H - 2*bbox (mm): median %.2f / %.2f  max|.| %.2f / %.2f'
      % (np.median(d[:, 0]), np.median(d[:, 1]), np.abs(d[:, 0]).max(), np.abs(d[:, 1]).max()))
for g in sorted(set(G)):
    mm = G == g
    print('bbox-check', g, 'n', int(mm.sum()), 'median dW/dH',
          round(float(np.median(d[mm, 0])), 2), round(float(np.median(d[mm, 1])), 2))

# ---------- matched three-scheme evaluation ----------
def covf(y):
    return cov(y, band, nf)


def model():
    return ExtraTreesRegressor(n_estimators=100, min_samples_leaf=2, random_state=0, n_jobs=4)


def evaluate(feat, x):
    P = np.zeros_like(Y); B = np.zeros_like(Y)
    for g in sorted(set(feat)):
        te = feat == g
        tr = ~te
        P[te] = model().fit(x[tr], Y[tr]).predict(x[te])
        B[te] = Y[tr].mean(axis=0)
    sk = skills(Y, P, B, band, ntargets=7)
    return P, B, sk


names = ['surface32', 'surface8', 'profile', 'profile+surface32', 'size']
COMBO = np.c_[XP, S32]
print('NOTE: on this 60-design sample lane and sibling folds coincide (6 lanes = 6 sibling groups)')
for nm, x in zip(names, [S32, S8, XP, COMBO, XP[:, :3]]):
    for scheme, groups in [('lane', G), ('sibling', S), ('engine', E)]:
        if scheme == 'engine':
            for g in sorted(set(groups)):
                te = groups == g
                tr = ~te
                P = np.zeros_like(Y); B = np.zeros_like(Y)
                P[te] = model().fit(x[tr], Y[tr]).predict(x[te])
                B[te] = Y[tr].mean(axis=0)
                sk = skills(Y[te], P[te], B[te], band, ntargets=7)
                r = spearmanr(covf(Y[te]), covf(P[te])).statistic
                print('SURF-ENGINE', nm, g, 'n', int(te.sum()), *[round(v, 3) for v in sk],
                      'covrank', round(float(r), 3), flush=True)
        P, B, sk = evaluate(groups, x)
        print('SURF-POOLED', nm, scheme, 'n', len(Y), *[round(v, 3) for v in sk], flush=True)

print('done')
