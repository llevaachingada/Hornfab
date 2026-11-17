import pathlib, json, collections, yaml
root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\runs')

# 1) study screen vs verify mesh hashes
print('== study screen/verify mesh hashes ==')
for S in sorted(root.glob('study-*')):
    sd, vd = S/'screen', S/'verify'
    if not (sd/'designs').is_dir() or not (vd/'designs').is_dir():
        continue
    common = sorted({p.name for p in (sd/'designs').iterdir() if p.is_dir()} &
                    {p.name for p in (vd/'designs').iterdir() if p.is_dir()})
    same = diff = 0
    example = None
    for h in common:
        try:
            a = json.load(open(sd/'designs'/h/'status.json')).get('mesh_hash')
            b = json.load(open(vd/'designs'/h/'status.json')).get('mesh_hash')
        except Exception:
            continue
        if a == b:
            same += 1
        else:
            diff += 1
            if example is None:
                example = (h, a, b)
    print(S.name, 'same', same, 'diff', diff, 'example', example)

# 2) runs search.ndjson: same design_hash with >1 mesh_hash, and response availability
print('\n== run ndjson mesh variants ==')
tot_groups = 0
tot_with_resp = 0
for rd in sorted(root.iterdir()):
    ndp = rd/'search.ndjson'
    if not rd.is_dir() or not ndp.is_file():
        continue
    groups = collections.defaultdict(set)
    meta = {}
    try:
        for line in open(ndp, encoding='utf8'):
            r = json.loads(line)
            if not r.get('ok'):
                continue
            groups[r.get('design_hash')].add(r.get('mesh_hash'))
            meta[(r.get('design_hash'), r.get('mesh_hash'))] = r
    except Exception:
        continue
    multi = {h: m for h, m in groups.items() if len(m) > 1}
    if multi:
        tot_groups += len(multi)
        resp = 0
        for h, meshes in multi.items():
            d = rd/'designs'/h
            if d.is_dir() and (d/'response.npz').is_file():
                # only one response per design dir; can't hold both meshes
                resp += 1
        tot_with_resp += resp
        print(rd.name, 'multi', len(multi), 'design dir', resp)
print('run ndjson multi-mesh groups', tot_groups, 'with a design dir', tot_with_resp)
