import collections,json,pathlib,pickle,yaml
from math import isfinite
root=pathlib.Path('scratch/fable_architecture')
rows=pickle.load(open(root/'.fable/rows.pkl','rb')); runs=collections.defaultdict(list)
for r in rows: runs[r['run']].append(r)
allrows=sorted(rows,key=lambda r:(r['created'],r['run'],r['n'] or 0)); result=[]
for run,rr in sorted(runs.items()):
    rr.sort(key=lambda r:(r['created'],r['n'] or 0)); first=rr[0]; cfg=yaml.safe_load(open(pathlib.Path('runs')/run/'config.yaml')); earlier=[r for r in allrows if r['created']<first['created'] and r['brief']==first['brief'] and r['ok']]; matches=[]
    for c in sorted({r['config'] for r in earlier}):
        es=[r for r in earlier if r['config']==c]; best=min(es,key=lambda r:r['J']); h=first['h'] and first['h']==best['h']; p=first.get('knobs') or first.get('params') or {}; q=best.get('knobs') or best.get('params') or {}; shared=[k for k,v in p.items() if isinstance(v,(int,float)) and isinstance(q.get(k),(int,float))]; param=bool(len(shared)>=3 and len(shared)==sum(isinstance(v,(int,float)) for v in p.values()) and all(abs(float(p[k])-float(q[k]))<=1e-5*max(1,abs(float(q[k]))) for k in shared))
        if h or param: matches.append({'config':c,'run':best['run'],'best':best['J'],'hash_match':bool(h),'params_match':bool(param),'same_config':c==first['config']})
    best_prior={c:min(r['J'] for r in earlier if r['config']==c) for c in {r['config'] for r in earlier}}
    firstj=first['J'] if first['ok'] else None
    for m in matches: m['within_noise']=firstj is not None and firstj<=m['best']+.17
    result.append({'run':run,'config':first['config'],'brief':first['brief'],'start':first['created'],'attempts':len(rr),'first_J':firstj,'first_hash':first['h'],'warm_start':(cfg.get('search') or {}).get('warm_start'), 'matches':matches,'seed_keys':sorted((cfg.get('seed_params') or {}).keys())})
(root/'.x5/lineage.json').write_text(json.dumps(result,indent=2)); print('runs',len(result),'cross config matches',sum(any(not z['same_config'] for z in x['matches']) for x in result))
for x in result:
    if any(not z['same_config'] for z in x['matches']): print(x['run'],x['config'],x['first_J'],x['matches'])
