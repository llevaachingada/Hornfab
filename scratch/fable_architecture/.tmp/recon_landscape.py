import pathlib, json, yaml, collections, re
root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\runs')
rows_info = []
runs = []
for rd in sorted(root.iterdir()):
    if not rd.is_dir():
        continue
    cfgp = rd/'config.yaml'
    ndp = rd/'search.ndjson'
    if not cfgp.is_file():
        continue
    try:
        cfg = yaml.safe_load(open(cfgp, encoding='utf8'))
    except Exception:
        continue
    t = cfg.get('target') or {}
    env = (cfg.get('brief') or {}).get('envelope') or {}
    name = str(cfg.get('name'))
    if not (t.get('coverage_h_deg') == 80 and t.get('coverage_v_deg') == 50 and env.get('max_mouth_h_mm') == 480):
        continue
    nrows = 0
    ok = 0
    nrows_ok_obj = 0
    design_dirs = 0
    if (rd/'designs').is_dir():
        design_dirs = len([p for p in (rd/'designs').iterdir() if p.is_dir()])
    if ndp.is_file():
        for line in open(ndp, encoding='utf8'):
            try:
                r = json.loads(line)
            except Exception:
                continue
            nrows += 1
            if r.get('ok'):
                ok += 1
                if isinstance(r.get('objective'), (int, float)):
                    nrows_ok_obj += 1
    runs.append(dict(dir=rd.name, name=name, date=rd.name[:8], nrows=nrows, ok=ok, ok_obj=nrows_ok_obj,
                     design_dirs=design_dirs, seed=(cfg.get('search') or {}).get('seed'),
                     sigma0=(cfg.get('search') or {}).get('sigma0'),
                     algorithm=(cfg.get('search') or {}).get('algorithm'),
                     seed_params_hash=hash(json.dumps(cfg.get('seed_params'), sort_keys=True)),
                     brief_name=name))
print('landscape runs:', len(runs))
print('total rows', sum(r['nrows'] for r in runs), 'ok', sum(r['ok'] for r in runs), 'ok_obj', sum(r['ok_obj'] for r in runs))
bydate = collections.Counter(r['date'] for r in runs)
print('by date', dict(sorted(bydate.items())))
byname = collections.Counter(r['name'] for r in runs)
print('distinct config names', len(byname))
for name, c in sorted(byname.items()):
    sub = [r for r in runs if r['name'] == name]
    print(f'{name[:52]:52s} runs={c:3d} rows={sum(r["nrows"] for r in sub):4d} ok_obj={sum(r["ok_obj"] for r in sub):4d} seeds={sorted(set(str(r["seed"]) for r in sub))}')
print()
for r in runs:
    if r['date'] >= '20261115':
        print(r['dir'], '| name', r['name'][:40], '| rows', r['nrows'], 'ok_obj', r['ok_obj'], 'dirs', r['design_dirs'], '| seed', r['seed'], 'sig', r['sigma0'], r['algorithm'])
