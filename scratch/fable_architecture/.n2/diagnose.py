import collections, pathlib, pickle
import yaml

rows = pickle.load(open('scratch/fable_architecture/.fable/rows.pkl', 'rb'))
runs = collections.defaultdict(list)
for r in rows:
    runs[r['run']].append(r)
for rr in runs.values():
    rr.sort(key=lambda r: (r['created'], r['n'] or 0))
first = {k: v[0] for k, v in runs.items()}
allrows = sorted(rows, key=lambda r: (r['created'], r['run'], r['n'] or 0))


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


for run in sorted(runs):
    f = first[run]
    cfg = yaml.safe_load(open(pathlib.Path('runs') / run / 'config.yaml'))
    seed = cfg.get('seed_params') or {}
    earlier = [r for r in allrows if r['created'] < f['created'] and r['ok']]
    best = {}
    for r in earlier:
        if r['config'] not in best or r['J'] < best[r['config']]['J']:
            best[r['config']] = r
    cand = []
    for c, b in best.items():
        shared = [k for k, v in seed.items() if num(v) and k in b['params'] and num(b['params'][k])]
        if len(shared) < 3:
            continue
        md = max(abs(float(seed[k]) - float(b['params'][k])) / max(1.0, abs(float(b['params'][k]))) for k in shared)
        ndiff = sum(1 for k in shared if abs(float(seed[k]) - float(b['params'][k])) > 1e-6 * max(1.0, abs(float(b['params'][k]))))
        cand.append((md, ndiff, len(shared), c, b['run'], b['J']))
    cand.sort()
    top = cand[0] if cand else None
    eq = all(abs(float(seed[k]) - float(f['params'][k])) <= 1e-9 for k in seed if k in f['params'] and num(seed[k]))
    print(f"{run} {f['config']:45s} seedrow_eq={eq} nearest={top}")
