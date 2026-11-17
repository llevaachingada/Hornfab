import pickle,json,pathlib,numpy as np
from hornlab_search.config import load_config
from hornlab_search.design.generators import rolled_family
rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')); seen=set()
for r in rows:
 if r['config']!='rf__section_axial_home_v7' or not r['ok'] or r['h'] in seen: continue
 p=pathlib.Path('runs')/r['run']; jpath=p/'designs'/r['h']/'design.json'
 if not jpath.exists(): continue
 seen.add(r['h']); j=json.load(open(jpath)); cfg=load_config(p/'config.yaml')
 try:
  g=rolled_family.resolve_grid(j['params']['grid'],cfg.brief); pts=np.concatenate([g['inner_points'].reshape(-1,3),g['outer_points'].reshape(-1,3)])
  ext=np.array([2*np.max(np.abs(pts[:,0])),2*np.max(np.abs(pts[:,1])),np.ptp(pts[:,2])]); b=np.array(r['bbox'])*1000; stored=np.array([2*(b[3]-b[0]),2*(b[4]-b[1]),b[5]-b[2]])
  print(r['h'],'surface',ext.round(3).tolist(),'stored',stored.round(3).tolist(),'delta', (ext-stored).round(3).tolist())
 except Exception as e: print(r['h'],type(e).__name__,str(e))
 if len(seen)==10: break
