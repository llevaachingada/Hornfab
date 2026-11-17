import collections, json, pathlib, pickle, sys
import numpy as np
from hornlab_search.objective import replay as R
sys.path.insert(0, str(pathlib.Path('scratch/fable_architecture/.tmp').resolve()))
import fable_replay_harness as H

root=pathlib.Path('scratch/fable_architecture')
rows=pickle.load(open(root/'.fable/rows.pkl','rb'))
groups=collections.defaultdict(list)
for r in rows:
    if r['ok'] and r['brief']=='cd' and np.isfinite(r['J']): groups[r['config']].append(r)
results=[]
for name, group in sorted(groups.items()):
    for i in np.linspace(0,len(group)-1,min(3,len(group)),dtype=int):
        r=group[i]; p=pathlib.Path('runs')/r['run']
        for regenerate in (() if '--corrected-only' in sys.argv else (False,True)):
            try:
                res=R.replay_run_dir(p,r['h'],config_path=p/'config.yaml',regenerate_metrics=regenerate)
                results.append(dict(config=name,run=r['run'],hash=r['h'],mode='regenerated' if regenerate else 'stored_metrics',stored=r['J'],replayed=res.j,status=res.status,error=None))
            except Exception as e:
                results.append(dict(config=name,run=r['run'],hash=r['h'],mode='regenerated' if regenerate else 'stored_metrics',stored=r['J'],replayed=None,status=None,error=repr(e)))
        try:
            b=H.brief(p/'config.yaml'); resp=H.load_response(p/'designs'/r['h']/'response.npz')
            replayed=H.score_v7(H.metrics_parity(resp,b.target),resp,b.target,b.weights,b.objective_params)[0]
            results.append(dict(config=name,run=r['run'],hash=r['h'],mode='corrected',stored=r['J'],replayed=float(replayed),status='scored',error=None))
        except Exception as e:
            results.append(dict(config=name,run=r['run'],hash=r['h'],mode='corrected',stored=r['J'],replayed=None,status=None,error=repr(e)))
out=root/'.e1/parity.json'; out.write_text(json.dumps(results,indent=2))
for mode in (('corrected',) if '--corrected-only' in sys.argv else ('stored_metrics','regenerated','corrected')):
    z=[x for x in results if x['mode']==mode]; valid=[x for x in z if x['replayed'] is not None and np.isfinite(x['replayed'])]; e=np.array([x['replayed']-x['stored'] for x in valid]); print(mode,'n',len(valid),'errors',len(z)-len(valid),'statuses',collections.Counter(x['status'] for x in z),'median_abs',np.median(abs(e)),'max_abs',np.max(abs(e)),'over_0.17',sum(abs(e)>.17))
