import pickle, collections, pathlib, yaml, re, json
rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'))
configs={}
for r in rows:
    if r['ok']: configs.setdefault(r['config'],set()).add(r['run'])
def group(n):
    if n.startswith('sp__'): return 'sp__control_moderate_strong'
    if n.startswith(('rr__reference','rr__pucker')): return 'rr__reference_pucker'
    if n.startswith('klangfilm_hv__a'): return 'klangfilm_hv__axis_variants'
    return re.sub(r'_v\d+$','',n.replace('_smooth',''))
groups=collections.defaultdict(list)
for n in configs: groups[group(n)].append(n)
for g, ns in sorted(groups.items()):
    print(g,':', ', '.join(sorted(ns)))
    if len(ns)>1:
        seeds={}
        for n in ns:
            seeds[n]=[]
            for run in sorted(configs[n]):
                c=yaml.safe_load(open(pathlib.Path('runs')/run/'config.yaml'))
                seed=c.get('seed_params'); seeds[n].append(json.dumps(seed,sort_keys=True))
        pairs=[]
        for i,n in enumerate(ns):
            for m in ns[i+1:]:
                overlap=set(seeds[n]) & set(seeds[m]); nonnull=overlap-{'null','{}'}
                pairs.append(n+' / '+m+': '+('exact nonempty match' if nonnull else 'no exact nonempty match'))
        print('  seeds:', '; '.join(pairs))
