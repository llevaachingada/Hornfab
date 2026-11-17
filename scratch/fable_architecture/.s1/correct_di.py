import json,pathlib,sys,pickle,numpy as np
from types import SimpleNamespace
from hornlab_search.objective.scalar_v9 import _di_roughness
from hornlab_search.metrics.di import di_slope_db_per_decade,di_from_balloon

cohort=sys.argv[1]; old=pathlib.Path('scratch/fable_architecture/.s1/records.jsonl' if cohort=='cd' else 'scratch/fable_architecture/.s1/records_smooth.jsonl')
dst=pathlib.Path('scratch/fable_architecture/.s1/records_'+cohort+'_corrected.jsonl')
lookup={(r['run'],r['h']):r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok']}
with dst.open('w') as out:
 for ln in old.open(encoding='utf-8-sig'):
  r=json.loads(ln); src=lookup[(r['run'],r['hash'])]; p=pathlib.Path('runs')/r['run']/'designs'/r['hash']/'response.npz'; z=np.load(p,allow_pickle=False)
  f=np.array(z['freqs_hz']); axis=np.argmin(abs(z['h_angles_deg'])); regen=np.array([di_from_balloon(b,a) for b,a in zip(z['spl_balloon_db'],z['spl_h_db'][:,axis])]); stored=np.array(src['di']); assert np.allclose(f,src['f'])
  m=(f>=700)&(f<=8000); rs=di_slope_db_per_decade(f[m],regen[m]); ss=di_slope_db_per_decade(f[m],stored[m]); rr=_di_roughness(SimpleNamespace(di_db=regen),f,m); sr=_di_roughness(SimpleNamespace(di_db=stored),f,m)
  delta_s=(ss**2-rs**2)/9.; delta_r=(sr-rr)/.5; delta_dead=(max(0.,sr-.5)-max(0.,rr-.5))/.5
  for c in r['cases'].values():
   for k in ('v9','strict','linear'): c[k]+=delta_s+delta_r
   c['dead']+=delta_s+delta_dead
  out.write(json.dumps(r)+'\n')
