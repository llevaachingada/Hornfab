import collections, json, pathlib, pickle
import yaml

root = pathlib.Path('scratch/fable_architecture')
rows = pickle.load(open(root / '.fable/rows.pkl', 'rb'))
runs = sorted({r['run'] for r in rows})
out = []
for run in runs:
    cfg = yaml.safe_load(open(pathlib.Path('runs') / run / 'config.yaml'))
    s = cfg.get('search') or {}
    out.append({
        'run': run,
        'config': cfg.get('name'),
        'seed_policy': cfg.get('seed_policy'),
        'seed_params_keys': sorted((cfg.get('seed_params') or {}).keys()),
        'search_keys': sorted(s.keys()),
        'warm_start': s.get('warm_start'),
        'seed': s.get('seed'),
        'algorithm': s.get('algorithm'),
        'init': s.get('init'),
        'cfg_top_keys': sorted(cfg.keys()),
    })
(root / '.n2/config_dump.json').write_text(json.dumps(out, indent=1, default=str))
for x in out:
    print(x['run'], x['config'], '| ws=', x['warm_start'], '| seed=', x['seed'], '| policy=', x['seed_policy'])
