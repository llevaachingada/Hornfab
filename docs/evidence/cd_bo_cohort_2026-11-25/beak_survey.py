import glob, json, re, collections
from pathlib import Path
PAT = re.compile(r'g_(beak_\w+|rim_sweep\w*|axial_[hv]_mm|bend_\w+|sweep\w*|lip_fwd\w*|setback\w*)$')
rows = []
for f in glob.glob('runs/*/search.ndjson'):
    run = Path(f).parent
    try:
        cfg = json.loads((run / 'run.json').read_text(encoding='utf-8'))['config']
    except Exception:
        continue
    b = cfg.get('bounds') or {}
    keys = [k for k in b if PAT.match(k)]
    if not keys:
        continue
    searched = [k for k in keys if b[k].get('search', True) and b[k]['lo'] != b[k]['hi']]
    best = None; n = 0
    for line in open(f, encoding='utf-8'):
        if not line.strip(): continue
        r = json.loads(line)
        if not r.get('ok') or r.get('objective') is None: continue
        n += 1
        if best is None or r['objective'] < best['objective']: best = r
    if not best: continue
    kn = ((best.get('params') or {}).get('grid') or {}).get('knobs') or {}
    rows.append({'run': run.name, 'name': cfg.get('name'), 'brief': (cfg.get('brief') or {}).get('name'),
                 'ver': (cfg.get('objective') or {}).get('version'), 'n': n, 'J': round(best['objective'], 3),
                 'kind': (cfg.get('generator') or {}).get('rows', {}).get('type') if isinstance((cfg.get('generator') or {}).get('rows'), dict) else (cfg.get('generator') or {}).get('kind'),
                 'searched': {k: (b[k]['lo'], b[k]['hi'], round(float(kn.get(k, float('nan'))), 2)) for k in searched},
                 'fixed': {k: b[k]['lo'] for k in keys if k not in searched}})
rows.sort(key=lambda r: r['run'])
for r in rows:
    print(f"{r['run'][:15]} {str(r['name'])[:34]:34s} v{r['ver']} n={r['n']:3d} J={r['J']:7.3f} {str(r['kind'])[:24]:24s} S={r['searched']} F={r['fixed']}")
