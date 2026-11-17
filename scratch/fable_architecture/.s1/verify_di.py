import json,pickle,pathlib,numpy as np,yaml,sys
from hornlab_search.objective.replay import _response_from_arrays
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.targets.spec import Target
from hornlab_search.objective.scalar_v9 import V9Params,objective_v9
cohort=sys.argv[1]; p=pathlib.Path('scratch/fable_architecture/.s1/records_'+cohort+'_corrected.jsonl'); records=[json.loads(x) for x in p.open()]; lookup={(r['run'],r['h']):r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok']}
b=yaml.safe_load(open('scratch/fable_architecture/.s1/brief.yaml')); target=Target.from_dict(b['target']); params=V9Params.from_block(b['objective'])
for i in np.linspace(0,len(records)-1,min(10,len(records)),dtype=int):
 r=records[i]; src=lookup[(r['run'],r['hash'])]; z=np.load(pathlib.Path('runs')/r['run']/'designs'/r['hash']/'response.npz',allow_pickle=False); keys=['freqs_hz','h_angles_deg','v_angles_deg','spl_h_db','spl_v_db','balloon_dirs','spl_balloon_db','z_throat']; resp,_=_response_from_arrays({},{k:z[k] for k in keys if k in z}); m=compute_metrics(resp,target);m.di_db=np.array(src['di']); score,terms=objective_v9(m,resp,True,target,b['weights'],params); delta=score-r['cases']['0,1000']['v9'];print(r['hash'],'delta',delta);assert abs(delta)<1e-8
