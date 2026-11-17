"""A7 inspection: whole-surface record coverage, engines, lane chronology."""
import numpy as np, glob, collections, pickle, json

ROOT = 'scratch/fable_architecture'
E = np.load(f'{ROOT}/.x3/extended.npz', allow_pickle=True)
ids = [str(h) for h in E['ids']]
idx = {h: i for i, h in enumerate(ids)}
G, Ee = E['G'], E['E']
rows = pickle.load(open(f'{ROOT}/.fable/rows.pkl', 'rb'))
row_by = {(r['run'], r['h']): r for r in rows}

recs = [np.load(f, allow_pickle=True) for f in sorted(glob.glob(f'{ROOT}/.n1b/build/*.npz'))]
print('n1b records', len(recs))
print('lanes', dict(collections.Counter(str(r['lane']) for r in recs)))
print('in 1715 targets:', sum(str(r['design_hash']) in idx for r in recs), 'of', len(recs))
print('missing:', [str(r['design_hash']) for r in recs if str(r['design_hash']) not in idx])

# engine per n1b record
eng = collections.Counter()
for r in recs:
    h = str(r['design_hash'])
    if h in idx:
        eng[(str(r['lane']), str(Ee[idx[h]]))] += 1
for k in sorted(eng):
    print('ENG', k, eng[k])

cnt = collections.Counter(G)
print('lanes', len(cnt), 'lanes>=30', sum(v >= 30 for v in cnt.values()),
      'lanes>=48', sum(v >= 48 for v in cnt.values()))
for g in sorted(cnt, key=lambda x: -cnt[x]):
    sub = collections.Counter(Ee[G == g])
    print('LANE', g, cnt[g], dict(sub))

# chronology availability: every extended id must map to exactly one (run,h)
hit = 0
for h in ids:
    n = sum(1 for r in rows if r['h'] == h and r['ok'])
    hit += (n >= 1)
print('ids with a valid row', hit, 'of', len(ids))
# created range per lane
for g in sorted(cnt):
    ts = [r['created'] for r in rows if r['config'] == g and r['ok'] and r['h'] in idx]
    print('TIME', g, len(ts), min(ts) if ts else None, max(ts) if ts else None)
