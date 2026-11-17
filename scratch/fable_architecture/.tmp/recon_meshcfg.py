import pathlib, yaml, json, collections

root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\runs')
seen = collections.Counter()
diff_cfgs = []
for rd in sorted(root.iterdir()):
    cfgp = rd/'config.yaml'
    if not rd.is_dir() or not cfgp.is_file():
        continue
    try:
        cfg = yaml.safe_load(open(cfgp, encoding='utf8'))
    except Exception:
        continue
    mesh = cfg.get('mesh') or {}
    keys = tuple(sorted(mesh))
    seen[keys] += 1
    cs, cv, cf = mesh.get('dof_cap_screen'), mesh.get('dof_cap_verify'), mesh.get('dof_cap_final')
    if cs is not None and cv is not None and cs != cv:
        diff_cfgs.append((rd.name, cfg.get('name'), 'dof', cs, cv, cf, keys, mesh))
    # mesh resolution keys
    for k in ('res_mm', 'res_mm_screen', 'res_mm_verify', 'epw', 'epw_screen', 'epw_verify'):
        if k in mesh:
            pass
print('mesh key sets:', seen)
print('configs with dof_cap_screen != dof_cap_verify:', len(diff_cfgs))
for d in diff_cfgs[:30]:
    print(d[0], d[1], d[2], d[3], d[4], d[5], d[6])
# also list every distinct mesh mapping with res/epw variants
m2 = collections.Counter()
for rd in sorted(root.iterdir()):
    cfgp = rd/'config.yaml'
    if not rd.is_dir() or not cfgp.is_file():
        continue
    try:
        cfg = yaml.safe_load(open(cfgp, encoding='utf8'))
    except Exception:
        continue
    mesh = cfg.get('mesh') or {}
    m2[json.dumps({k: mesh.get(k) for k in ('epw','dof_cap_screen','dof_cap_verify','dof_cap_final','res_mm','res_mm_screen','res_mm_verify') if k in mesh}, sort_keys=True)] += 1
print('\ndistinct mesh mode mappings:')
for k, v in m2.most_common():
    print(v, k)
