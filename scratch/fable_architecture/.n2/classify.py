import collections, json, pathlib, pickle
import yaml

root = pathlib.Path('scratch/fable_architecture')
rows = pickle.load(open(root / '.fable/rows.pkl', 'rb'))
runs = collections.defaultdict(list)
for r in rows:
    runs[r['run']].append(r)
for rr in runs.values():
    rr.sort(key=lambda r: (r['created'], r['n'] or 0))

first = {}
for run, rr in runs.items():
    first[run] = rr[0]

allrows = sorted(rows, key=lambda r: (r['created'], r['run'], r['n'] or 0))

def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def match(seed, target):
    """All numeric seed keys present in target must match within 1e-6 (rel-or-abs)."""
    shared = [k for k, v in seed.items() if num(v) and k in target and num(target[k])]
    if not shared:
        return False, 0
    for k in shared:
        a, b = float(seed[k]), float(target[k])
        if abs(a - b) > 1e-6 * max(1.0, abs(b)):
            return False, len(shared)
    return True, len(shared)

result = []
for run in sorted(runs):
    f = first[run]
    cfg = yaml.safe_load(open(pathlib.Path('runs') / run / 'config.yaml'))
    seedp = cfg.get('seed_params') or {}
    s = cfg.get('search') or {}
    earlier = [r for r in allrows if r['created'] < f['created'] and r['ok']]
    # best earlier row per config
    best_by_config = {}
    for r in earlier:
        c = r['config']
        if c not in best_by_config or r['J'] < best_by_config[c]['J']:
            best_by_config[c] = r
    matches = []
    for c, b in best_by_config.items():
        target = b.get('knobs') or b.get('params') or {}
        ok, shared = match(seedp, target)
        if ok:
            matches.append({'run': b['run'], 'config': c, 'best_J': b['J'],
                            'shared_keys': shared, 'same_config': c == f['config']})
    matches.sort(key=lambda m: (not m['same_config'], m['best_J']))
    result.append({
        'run': run, 'config': f['config'], 'brief': f['brief'],
        'start': f['created'], 'algorithm': s.get('algorithm'),
        'seed': s.get('seed'), 'warm_start': s.get('warm_start'),
        'seed_param_count': len(seedp),
        'matches': matches,
    })

(root / '.n2/classify.json').write_text(json.dumps(result, indent=1, default=str))
print('runs', len(result))
print('with explicit warm_start:', sum(1 for x in result if x['warm_start']))
print('with an earlier-best seed match:', sum(1 for x in result if x['matches']))
print('no match:', sum(1 for x in result if not x['matches']))
for x in result:
    tag = 'WARM' if x['warm_start'] else ('MATCH' if x['matches'] else 'NONE')
    ms = '; '.join(f"{m['run']}/{m['config']} J={m['best_J']:.4f} same={m['same_config']} k={m['shared_keys']}" for m in x['matches'][:4])
    print(f"{tag:5} {x['run']} {x['config']} :: {ms}")
