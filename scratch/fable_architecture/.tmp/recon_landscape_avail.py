import pathlib, json, yaml, collections
root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\runs')
total = have_dir = have_resp = have_metrics = 0
missing = []
for rd in sorted(root.iterdir()):
    cfgp = rd/'config.yaml'; ndp = rd/'search.ndjson'
    if not rd.is_dir() or not cfgp.is_file() or not ndp.is_file():
        continue
    try:
        cfg = yaml.safe_load(open(cfgp, encoding='utf8'))
    except Exception:
        continue
    t = cfg.get('target') or {}; env = (cfg.get('brief') or {}).get('envelope') or {}
    if not (t.get('coverage_h_deg') == 80 and t.get('coverage_v_deg') == 50 and env.get('max_mouth_h_mm') == 480):
        continue
    for line in open(ndp, encoding='utf8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if not (r.get('ok') and isinstance(r.get('objective'), (int, float))):
            continue
        total += 1
        h = r.get('design_hash')
        d = rd/'designs'/h
        if d.is_dir():
            have_dir += 1
            if (d/'response.npz').is_file():
                have_resp += 1
            if (d/'metrics.json').is_file():
                have_metrics += 1
        else:
            missing.append((rd.name, h, r.get('mode'), r.get('cached')))
print('ok rows', total, 'have design dir', have_dir, 'have response', have_resp, 'have metrics', have_metrics)
print('missing examples', missing[:10], 'n missing', len(missing))
# also check whether response dir status key matches row key
mismatch = 0
for rd in sorted(root.iterdir()):
    cfgp = rd/'config.yaml'; ndp = rd/'search.ndjson'
    if not rd.is_dir() or not cfgp.is_file() or not ndp.is_file():
        continue
    try:
        cfg = yaml.safe_load(open(cfgp, encoding='utf8'))
    except Exception:
        continue
    t = cfg.get('target') or {}; env = (cfg.get('brief') or {}).get('envelope') or {}
    if not (t.get('coverage_h_deg') == 80 and t.get('coverage_v_deg') == 50 and env.get('max_mouth_h_mm') == 480):
        continue
    for line in open(ndp, encoding='utf8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if not (r.get('ok') and isinstance(r.get('objective'), (int, float))):
            continue
        h = r.get('design_hash'); d = rd/'designs'/h
        if d.is_dir() and (d/'status.json').is_file():
            s = json.load(open(d/'status.json'))
            if s.get('key') and r.get('key') and s['key'] != r['key']:
                mismatch += 1
print('status key mismatches', mismatch)
