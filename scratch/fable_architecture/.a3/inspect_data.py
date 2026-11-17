"""A3 inspection only: shapes/keys/lane coverage. Read-only except this .a3 folder."""
import pickle, pathlib, collections, sys
import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
print('rows', len(rows))
print('row keys', sorted(rows[0].keys()))
r = rows[0]
for k in rows[0]:
    v = r[k]
    s = f'{k}: {type(v).__name__}'
    try:
        s += f' len={len(v)}'
    except Exception:
        s += f' = {v!r}'[:120]
    print(s)
print()
print('configs', len(set(x['config'] for x in rows)))
print('briefs', collections.Counter(x['brief'] for x in rows).most_common())
print('objective versions', collections.Counter(x.get('objective_version') or x.get('objective') for x in rows))
print('n with terms', sum(1 for x in rows if 'terms' in x))
if 'terms' in r:
    print('terms keys', sorted(r['terms']))
print('sample row J', r.get('J'), 'terms', r.get('terms'))
print()
print('n1b build npz:')
f = sorted((ROOT / '.n1b/build').glob('*.npz'))[0]
z = np.load(f)
for k in z.files:
    a = z[k]
    print(' ', k, getattr(a, 'shape', None), getattr(a, 'dtype', None))
print(' lane', z['lane'], 'hash', z['design_hash'], 'mode', z['mode'], 'prov', str(z['provenance'])[:80])
print(' lanes in build', collections.Counter(str(np.load(p)['lane']) for p in sorted((ROOT / '.n1b/build').glob('*.npz'))))
print()
print('x1 npz:')
f = sorted((ROOT / '.x1').glob('*.npz'))[0]
z = np.load(f)
for k in z.files:
    a = z[k]
    print(' ', k, getattr(a, 'shape', None), getattr(a, 'dtype', None))
print(' lanes in x1', collections.Counter(str(np.load(p)['lane']) for p in sorted((ROOT / '.x1').glob('*.npz'))))
print()
data, fails = pickle.load(open(ROOT / '.e1/descriptors.pkl', 'rb'))
print('e1 extracted', len(data), 'failed', len(fails))
print('e1 row keys', sorted(data[0][0].keys()))
print('desc dim', np.asarray(data[0][1]).shape, 'resp dim', np.asarray(data[0][2]).shape)
print('e1 lanes', collections.Counter(x[0]['config'] for x in data).most_common())
print('e1 lanes by brief', collections.Counter((x[0]['config'], x[0]['brief']) for x in data).most_common(20))
