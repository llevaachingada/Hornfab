import sys, json, copy, collections
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H

runs = H.load_landscape_runs()
print('runs', len(runs))

def normalized(cfg):
    d = copy.deepcopy(cfg)
    for k in ('name', 'description', 'brief_file', 'feasibility'):
        d.pop(k, None)
    se = d.get('search') or {}
    for k in ('seed',):
        se.pop(k, None)
    d['search'] = se
    d.pop('seed_params', None)  # start variation is allowed by R4
    return json.dumps(d, sort_keys=True)

groups = collections.defaultdict(list)
for r in runs:
    groups[normalized(r['cfg'])].append(r)

print('normalized groups', len(groups))
for key, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    if len(rs) < 3:
        continue
    names = collections.Counter(r['cfg'].get('name') for r in rs)
    print('\ngroup n', len(rs), 'names', dict(names))
    for r in rs:
        seeds = r['cfg'].get('search', {}).get('seed')
        sp = r['cfg'].get('seed_params') or {}
        valid = [x for x in r['rows'] if x.get('ok') and isinstance(x.get('objective'), (int, float)) and x['objective'] < 900]
        print(' ', r['dir'].name, 'seed', seeds, 'valid', len(valid), 'rows', len(r['rows']), 'best', min((x['objective'] for x in valid), default=None), 'startkey', {k: round(v,4) for k,v in sp.items() if k in ('r0_mm','a_deg','a0_deg','L_mm','s','g_aspect','g_fc_hz','g_lame_p','g_end_frac','g_rim_sweep_ratio','az_a_cos_amp','az_a_cos_pow')})
