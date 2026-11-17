"""A7 part B2: explicit wavelength-scaled inputs.

Representation versions (fixed here, before any result was inspected):

  WL-1 (per-frequency wavelength scaling).  For design i, frequency f_k:
      z_(i,k) = x_i * (2*pi*f_k / c)
  with x_i the 27 mesh-derived lengths in mm (.fable/an3.py desc; all 27 columns are
  lengths) and c = 343.0 m/s (20 degC, hornlab_search/constants.py C_AIR).
  No separate frequency channel.  One model serves all 18 frequencies: training rows are
  every training design x every stored frequency; held-out rows are the held-out designs
  x the scoring band f >= 600 Hz.  The multiplier carries a fixed 1000 (mm vs m), i.e.
  the features are a constant multiple of the dimensionless ka; trees are invariant to
  that constant, so it changes nothing and is left explicit.

  WL-0 (control).  Same per-frequency row structure, raw x_i, no frequency channel: the
  model must predict all 18 frequencies from one feature vector.

  WL-2 (reference-frequency control).  Scaling x_i by 2*pi*f_ref/c at f_ref = 1000 Hz is a
  constant monotone rescale trees ignore, so WL-2 is informationally identical to the Part E
  frequency-conditioned baseline [x, ln f]; the code uses unscaled x to avoid float-threshold
  noise.  It is run only as an implementation-parity control against .x3/augment.txt.

Model: ExtraTreesRegressor(40 trees, min_samples_leaf=3, random_state=0, n_jobs=4) --
the Part E model, so WL-1 compares with a representation that already has a record.
Splits: exactly .x3/strict.py (lane / sibling / engine).  Baseline: per-fold,
per-frequency training mean.  Skill: 1 - SSE/SSE_baseline, pooled over band points.
Within-lane rank is reported for every scheme, including the engine folds.
"""
import numpy as np, sys
sys.path.insert(0, 'scratch/fable_architecture/.x3c')
from a7_common import load_base, sibling, cov, skills
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr

X, Y, G, E, ids, rows, f = load_base()
nf = len(f)
band = np.where(f >= 600)[0]
S = np.array([sibling(g) for g in G])
C = 343.0
K = 2 * np.pi * f / C
KREF = 2 * np.pi * 1000.0 / C
print('WL-1: k(f) min/max %.5f %.5f 1/mm ; band %d of %d; designs %d; lanes %d; engines %s'
      % (K.min(), K.max(), len(band), nf, len(X), len(set(G)), dict(zip(*np.unique(E, return_counts=True)))))


def model():
    return ExtraTreesRegressor(n_estimators=40, min_samples_leaf=3, random_state=0, n_jobs=4)


def pack(idx, freqs, version):
    x = X[idx]
    if version == 'WL-1':
        a = x[:, None, :] * K[None, freqs, None]
    elif version == 'WL-0':
        # control: one feature vector per design repeated at every frequency, no frequency
        # information at all (the same model must serve all 18 targets)
        a = np.broadcast_to(x[:, None, :], (len(idx), len(freqs), x.shape[1]))
    else:
        q = len(freqs) if np.ndim(freqs) else 1
        # unscaled x: 2*pi*f_ref/c is a constant monotone rescale trees are invariant to,
        # so this is the same representation and avoids float-threshold noise in the parity run
        a = np.concatenate([np.broadcast_to(x[:, None, :], (len(idx), q, x.shape[1])),
                            np.broadcast_to(np.log(f)[np.atleast_1d(freqs)][None, :, None], (len(idx), q, 1))],
                           axis=2)
    y = np.stack([Y[idx][:, i * nf:(i + 1) * nf][:, freqs] for i in range(3)], axis=2)
    return a.reshape(len(idx) * len(freqs), -1), y.reshape(-1, 3)


def run(version, scheme, groups, label=True):
    P = np.zeros((len(X), 54))
    B = np.zeros((len(X), 54))
    allf = np.arange(nf)
    for g in sorted(set(groups)):
        te = groups == g
        tr = ~te
        it = np.where(te)[0]
        a, b = pack(np.where(tr)[0], allf, version)
        a2, b2 = pack(it, band, version)
        m = model().fit(a, b)
        p = m.predict(a2).reshape(len(it), len(band), 3)
        bm = b.reshape(-1, nf, 3).mean(axis=0)   # per-frequency training mean
        for i in range(3):
            P[np.ix_(it, i * nf + band)] = p[:, :, i]
            B[np.ix_(it, i * nf + band)] = bm[band, i]
        if scheme == 'engine':
            sk = skills(Y[te], P[te], B[te], band)
            print('WL-RESULT', version, scheme, g, 'n', int(te.sum()), *[round(s, 4) for s in sk], flush=True)
    sk = skills(Y, P, B, band)
    print('WL-POOLED', version, scheme, 'n', len(X), *[round(s, 4) for s in sk], flush=True)
    if True:   # the pass line is a rank, so report it for every scheme including engine
        rank = []
        for g in sorted(set(G)):
            if (G == g).sum() >= 30:
                r = spearmanr(cov(Y[G == g], band, nf), cov(P[G == g], band, nf)).statistic
                rank.append(r)
        print('WL-RANK', version, scheme, 'lanes', len(rank), 'median', round(float(np.nanmedian(rank)), 4),
              flush=True)
    return P


# Full three-scheme table for the two per-frequency representations (skip with --wl2 for
# the parity control only)
if '--wl2' not in sys.argv:
    for version in ('WL-0', 'WL-1'):
        for scheme, groups in [('lane', G), ('sibling', S), ('engine', E)]:
            run(version, scheme, groups)

# WL-2 parity control: engine splits only (compare .x3/augment.txt baseline numbers).
# Uses augment.py's extra duplicate-hash removal so the numbers are a like-for-like parity
# check; WL-1 above uses strict.py's tr=~te unchanged.
ids_arr = np.array(ids)
for e in sorted(set(E)):
    te = E == e
    tr = (~te) & (~np.isin(ids_arr, ids_arr[te]))
    it = np.where(te)[0]
    a, b = pack(np.where(tr)[0], np.arange(nf), 'WL-2')
    a2, _ = pack(it, band, 'WL-2')
    m = model().fit(a, b)
    p = m.predict(a2).reshape(len(it), len(band), 3)
    bm = b.reshape(-1, nf, 3).mean(axis=0)
    P = np.zeros((len(it), 54))
    B = np.zeros((len(it), 54))
    for i in range(3):
        P[np.ix_(np.arange(len(it)), i * nf + band)] = p[:, :, i]
        B[np.ix_(np.arange(len(it)), i * nf + band)] = bm[band, i]
    print('WL2-CONTROL', e, 'n', len(it), *[round(s, 4) for s in skills(Y[te], P, B, band)], flush=True)
print('done')
