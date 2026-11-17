import pickle,json,pathlib,numpy as np
from hornlab_search.config import load_config
from hornlab_search.design.generators import _klangfilm_lame_v1 as kernel
rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')); seen=set()
for r in rows:
 if r['config']!='hl__klangfilm_lame_curved_v1' or not r['ok'] or r['h'] in seen: continue
 p=pathlib.Path('runs')/r['run']; path=p/'designs'/r['h']/'design.json'
 if not path.exists():continue
 seen.add(r['h']); j=json.load(open(path)); block=j['params']['grid']; cfg=load_config(p/'config.yaml')
 try:
  shape={k:block['knobs']['g_'+k] for k in kernel.SHAPE_KEYS-{'n_phi','n_s','wall_thickness_mm'}}
  shape.update({k:block[k] for k in ('n_phi','n_s','wall_thickness_mm')})
  points,meta=kernel.make_grid(shape,cfg.brief); again,_=kernel.make_grid(shape,cfg.brief)
  print(r['h'],'shape',points.shape,'same_bytes',np.array_equal(points,again),'stored_schema',block['rows']['schema'],'saved_implementation',block['rows']['implementation_sha256'])
 except Exception as e: print(r['h'],'FAILED',type(e).__name__,str(e))
 if len(seen)==10:break
