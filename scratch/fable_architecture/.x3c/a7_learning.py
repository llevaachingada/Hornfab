"""A7 part F: sibling lineage in the learning curve, within-lane chronology, solve value.

Fixed before results:
  * Base: the 1,715-design .x3/extended.npz sample, chronological order per lane by the row's
    `created` timestamp (ties: run, design hash).
  * Prior for lane g = ExtraTrees(100, leaf 2, seed 0) trained on every design whose
    sibling(g') != sibling(g)  [strict scheme-2 rule, .x3/strict.py sibling map, unchanged].
    A second prior excludes the whole engine (scheme 3) for the Part F comparison.
    Both are out-of-fold for every design of g by construction.
  * P1 chronology: each lane with N >= 40 is cut into 4 contiguous chronological blocks;
    within-block Spearman(cov(y), cov(prior prediction)) of the coverage proxy
    (f >= 600 Hz, asymmetric 80x50, identical to strict.py).
  * P2 learning curve: test = the LAST 16 designs of the lane; training = the FIRST n
    designs (expanding window, chronological). n in {8,16,32,48}; 48 only if N >= 64.
    'local' = model on X only; 'plus' = model on [X, prior coverage prediction].
    10 seeded repetitions draw the n training designs at random from the pre-test window
    (seed 42) as a stability check; the chronological curve is the primary one.
  * P3 solve value: median local curve across lanes. Prior worth = smallest n whose local
    median reaches the prior-only median (">48" if none). Marginal value of a solve =
    change in local median divided by the solves added. Matched-n prior gain is converted
    with the local 16->32 slope.
  * Lanes with a constant coverage vector in the test set are excluded and counted.
"""
import numpy as np, sys, collections
sys.path.insert(0, 'scratch/fable_architecture/.x3c')
from a7_common import load_base, sibling, cov
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr

X, Y, G, E, ids, rows, f = load_base()
nf = len(f); band = np.where(f >= 600)[0]
S = np.array([sibling(g) for g in G])

# chronological key per (config, h)
created = {}
for r in rows:
    if r['ok'] and r['f'] and len(r['f']) == 18:
        k = (r['config'], r['h'])
        run_key = '%s|%s' % (r['created'], r['run'])
        created[k] = min(created.get(k, '9|'), run_key)
key = np.array(['%s|%s' % (created.get((g, h), '9|'), h) for g, h in zip(G, ids)])
ycov = cov(Y, band, nf)


def model():
    return ExtraTreesRegressor(n_estimators=100, min_samples_leaf=2, random_state=0, n_jobs=4)


def rho(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(set(np.round(a, 9))) < 2 or len(set(np.round(b, 9))) < 2:
        return np.nan
    return spearmanr(a, b).statistic


lanes = [g for g in sorted(set(G)) if (G == g).sum() >= 40]
print('lanes with N>=40:', len(lanes), 'designs', int(sum((G == g).sum() for g in lanes)))

prior_sib = np.full((len(X), 126), np.nan)
prior_eng = np.full((len(X), 126), np.nan)
for g in lanes:
    te = G == g
    tr = S != sibling(g)
    prior_sib[te] = model().fit(X[tr], Y[tr]).predict(X[te])
    tr2 = E != E[te][0]
    prior_eng[te] = model().fit(X[tr2], Y[tr2]).predict(X[te])
pcov = cov(prior_sib, band, nf)
pcov_eng = cov(prior_eng, band, nf)

# ---------- P1: transfer vs chronological position ----------
print('\nP1 chronological blocks (fraction of lane history): Spearman(cov true, cov prior)')
blocks = collections.defaultdict(list)
for g in lanes:
    ix = np.where(G == g)[0]
    ix = ix[np.argsort([key[i] for i in ix])]
    parts = np.array_split(ix, 4)
    for b, p in enumerate(parts):
        r = rho(ycov[p], pcov[p])
        if np.isfinite(r):
            blocks[b].append(r)
for b in range(4):
    v = np.array(blocks[b])
    print('P1 block %d (designs %d-%d of lane): lanes %d median %.3f IQR %.3f/%.3f'
          % (b + 1, b * 25 + 1, (b + 1) * 25, len(v), np.median(v),
             np.percentile(v, 25), np.percentile(v, 75)))

# per-lane prior rank on the whole lane and on the last-16 test window
prior_rank = {}
for g in lanes:
    ix = np.where(G == g)[0]
    ix = ix[np.argsort([key[i] for i in ix])]
    prior_rank[g] = dict(all=rho(ycov[ix], pcov[ix]),
                         test=rho(ycov[ix[-16:]], pcov[ix[-16:]]),
                         test_eng=rho(ycov[ix[-16:]], pcov_eng[ix[-16:]]))
print('\nprior-only within-lane rank (sibling-holdout prior): median all-lane %.3f, '
      'median last-16 %.3f; engine-holdout prior last-16 median %.3f'
      % (np.nanmedian([v['all'] for v in prior_rank.values()]),
         np.nanmedian([v['test'] for v in prior_rank.values()]),
         np.nanmedian([v['test_eng'] for v in prior_rank.values()])))

# ---------- P2: expanding-window learning curves ----------
rng = np.random.default_rng(42)
methods = ['local', 'plus']
chron = collections.defaultdict(list)
reps = collections.defaultdict(list)
per_lane = {}
for g in lanes:
    ix = np.where(G == g)[0]
    ix = ix[np.argsort([key[i] for i in ix])]
    pool, test = ix[:-16], ix[-16:]
    if len(set(np.round(ycov[test], 9))) < 2:
        continue
    row = {}
    for n in (8, 16, 32, 48):
        if n > len(pool):
            continue
        trn = pool[:n]
        for m in methods:
            xx = X[trn] if m == 'local' else np.c_[X[trn], pcov[trn]]
            xe = X[test] if m == 'local' else np.c_[X[test], pcov[test]]
            p = model().fit(xx, ycov[trn]).predict(xe)
            r = rho(ycov[test], p)
            chron[(n, m)].append(r)
            row['%d/%s' % (n, m)] = r
        draws = []
        for _ in range(10):
            trn = rng.choice(pool, n, replace=False)
            for m in methods:
                xx = X[trn] if m == 'local' else np.c_[X[trn], pcov[trn]]
                xe = X[test] if m == 'local' else np.c_[X[test], pcov[test]]
                draws.append((m, rho(ycov[test], model().fit(xx, ycov[trn]).predict(xe))))
        for m in methods:
            v = [r for mm, r in draws if mm == m]
            reps[(n, m)].append(np.nanmedian(v))
    per_lane[g] = row

print('\nP2 expanding window, median Spearman over lanes (chronological prefix -> last 16)')
print('n    local   plus    d(plus-local)   [random-prefix medians: local / plus]')
for n in (8, 16, 32, 48):
    l = np.array([per_lane[g].get('%d/local' % n, np.nan) for g in per_lane])
    p = np.array([per_lane[g].get('%d/plus' % n, np.nan) for g in per_lane])
    lr = np.array(reps.get((n, 'local'), [np.nan]))
    pr = np.array(reps.get((n, 'plus'), [np.nan]))
    if np.all(np.isnan(l)):
        continue
    print('%3d  %.3f   %.3f   %+.3f          %.3f / %.3f   (lanes %d)'
          % (n, np.nanmedian(l), np.nanmedian(p), np.nanmedian(p) - np.nanmedian(l),
             np.nanmedian(lr), np.nanmedian(pr), int(np.isfinite(l).sum())))

# ---------- P3: solve value ----------
print('\nP3 solve value')
sprior = np.nanmedian([v['test'] for v in prior_rank.values()])
print('prior-only median last-16 rank: %.3f' % sprior)
med = {}
for n in (8, 16, 32, 48):
    l = np.array([per_lane[g].get('%d/local' % n, np.nan) for g in per_lane])
    p = np.array([per_lane[g].get('%d/plus' % n, np.nan) for g in per_lane])
    med[n] = (np.nanmedian(l), np.nanmedian(p), int(np.isfinite(l).sum()))
    print('local %2d: %.3f  plus: %.3f  n lanes %d' % (n, med[n][0], med[n][1], med[n][2]))
worth = next((n for n in (8, 16, 32, 48) if n in med and med[n][0] >= sprior), None)
print('prior worth (local curve reaches prior-only rank): %s'
      % ('%d local solves' % worth if worth else '>48 local solves'))
if 16 in med and 32 in med:
    slope = (med[32][0] - med[16][0]) / 16.0
    print('marginal local rank per solve, 16->32: %+.4f' % slope)
    gain = med[16][1] - med[16][0]
    print('plus-minus-local at n=16: %+.3f -> %.1f solve-equivalents (if slope > 0)'
          % (gain, gain / slope if slope > 0 else float('nan')))
# per-lane solve-equivalent count
worth_lane = {}
for g, row in per_lane.items():
    p0 = prior_rank[g]['test']
    hit = [n for n in (8, 16, 32, 48) if ('%d/local' % n) in row and row['%d/local' % n] >= p0]
    worth_lane[g] = (min(hit) if hit else None)
print('per-lane prior worth distribution (None = >48):',
      dict(collections.Counter(w if w else '>48' for w in worth_lane.values())))
print('lanes needing >=16 local solves to match their prior: %d of %d'
      % (sum(1 for v in worth_lane.values() if v is None or v >= 16), len(worth_lane)))

print('\nper-lane (last-16 rank): lane N engine prior local8 local16 local32 plus16 plus32 worth')
for g in sorted(per_lane):
    row = per_lane[g]
    N = int((G == g).sum())
    print('%-40s %3d %-6s %.3f %s %s %s %s %s %s' % (
        g, N, E[G == g][0], prior_rank[g]['test'],
        *['%.3f' % row.get('%d/%s' % (n, m), np.nan) for n, m in
          ((8, 'local'), (16, 'local'), (32, 'local'), (16, 'plus'), (32, 'plus'))],
        (worth_lane[g] if worth_lane[g] else '>48')))
print('done')
