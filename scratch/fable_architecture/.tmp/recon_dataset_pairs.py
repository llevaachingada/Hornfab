import json, collections, pathlib

root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\dataset')
groups = collections.defaultdict(list)
for shard in sorted(root.glob('shard-*.jsonl')):
    si = int(shard.stem.split('-')[1])
    for row, line in enumerate(open(shard, encoding='utf8')):
        try:
            d = json.loads(line)
        except Exception:
            continue
        groups[d.get('design_hash')].append((si, row, d))
print('total dataset records', sum(len(v) for v in groups.values()), 'design hashes', len(groups))
pair_groups = {k: v for k, v in groups.items() if len({d.get('mesh_hash') for _, _, d in v}) > 1}
print('design hashes with >1 mesh_hash', len(pair_groups))
npairs = sum(len(v) for v in pair_groups.values())
print('rows in those groups', npairs)
# distribution of group sizes
print('group size dist', collections.Counter(len(v) for v in pair_groups.values()))
# inspect a few groups
for k, v in list(pair_groups.items())[:5]:
    print('\ndesign', k, 'n', len(v))
    for si, row, d in v:
        print(' shard', si, 'row', row, 'mesh', d.get('mesh_hash'), 'solve', d.get('solve_hash'), 'ok', d.get('ok'),
              'freqs', d.get('solve', {}).get('freqs_hz')[0], '-', d.get('solve', {}).get('freqs_hz')[-1],
              'n_dof', d.get('mesh', {}).get('n_dof'), 'res', d.get('mesh', {}).get('res_mm'),
              'target', (d.get('target') or {}).get('coverage_h_deg'), (d.get('target') or {}).get('coverage_v_deg'),
              (d.get('target') or {}).get('band_lo_hz'), (d.get('target') or {}).get('band_hi_hz'),
              'J', d.get('objective'), 'created', d.get('created_utc'))
# check targets within groups: same or different
same_target = 0
diff_target = 0
target_sigs = {}
for k, v in pair_groups.items():
    sigs = {json.dumps(d.get('target'), sort_keys=True) for _, _, d in v}
    if len(sigs) == 1:
        same_target += 1
    else:
        diff_target += 1
    target_sigs[k] = len(sigs)
print('\ngroups with identical target', same_target, 'different target', diff_target)
