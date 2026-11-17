import collections,importlib.util,json,pathlib,pickle,sys
root=pathlib.Path('scratch/fable_architecture'); rows=pickle.load(open(root/'.fable/rows.pkl','rb')); runs=collections.defaultdict(list)
for r in rows:
    if r['brief']=='cd': runs[r['run']].append(r)
spec=importlib.util.spec_from_file_location('rcn',pathlib.Path('tools/run_campaign_night.py')); mod=importlib.util.module_from_spec(spec); sys.modules['rcn']=mod; spec.loader.exec_module(mod)
out=[]
for run,stored in sorted(runs.items()):
    path=pathlib.Path('runs')/run; raw=[]
    for line in (path/'search.ndjson').read_text(encoding='utf8').splitlines():
        try: raw.append(json.loads(line))
        except ValueError: pass
    raw=raw[:len(stored)]; bounds=mod._run_bounds(path); verdict=None; index=None
    for i in range(1,len(raw)+1):
        verdict=mod.watchdog_verdict(raw[:i],dict(mod.WATCHDOG_DEFAULTS),bounds)
        if verdict: index=i; break
    def best(seq): return min((float(r['objective']) for r in seq if r.get('ok') and isinstance(r.get('objective'),(int,float)) and r['objective']<900),default=None)
    out.append({'run':run,'config':stored[0]['config'],'attempts':len(raw),'trigger':index,'reason':verdict,'best_at_trigger':best(raw[:index]) if index else None,'final_best':best(raw),'lost_rows':len(raw)-index if index else 0})
(root/'.x5/watchdog.json').write_text(json.dumps(out,indent=2)); print('runs',len(out),'triggers',sum(bool(x['trigger']) for x in out),'continuations',sum(x['lost_rows']>0 for x in out))
for x in out:
    if x['lost_rows'] and x['final_best'] is not None and x['best_at_trigger'] is not None and x['final_best']<x['best_at_trigger']-.17: print(x)
