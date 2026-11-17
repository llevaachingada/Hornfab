import ast,pathlib,json,pickle,numpy as np
from hornlab_search.config import load_config
from hornlab_search.types import Design
from hornlab_search.bo.data import materialize_geometry
from hornlab_search.design.generated import materialize
from hornlab_search.design.generators import grid, rolled_family,klangfilm_lame_family
s=pathlib.Path('scratch/fable_architecture/.x1/probe.py').read_text();fn=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name=='sample');exec(compile(ast.Module(body=[fn],type_ignores=[]),'x1sample','exec'))
def surface(cfg,knobs):
 params=materialize(cfg.generator,knobs,cfg.brief);d=Design('FREEFORM',params);block=params.get('grid')
 if block:
  if klangfilm_lame_family.is_family_spec(block):pts=klangfilm_lame_family.resolve_grid(block,cfg.brief)['inner_points']
  elif rolled_family.is_family_spec(block):pts=rolled_family.resolve_grid(block,cfg.brief)['inner_points']
  else:pts=grid.grid_points(block,block.get('knobs',{}),cfg.brief)[0]
 else:pts=materialize_geometry(d,cfg,resolution_mm=10)['inner_points']
 return d.hash(),sample(pts,31,65)
R=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'));rng=np.random.default_rng(124);out={}
for name in ['hl__crowe_x_osse_cd_v7','hl__biradial_es_style_v7','hl__klangfilm_lame_curved_v1']:
 rs=[r for r in R if r['ok'] and r['config']==name];best=min(rs,key=lambda r:r['J']);other=[r for r in rs if r['h']!=best['h']];chosen=[best]+[other[i] for i in rng.choice(len(other),min(10,len(other)),replace=False)];keys=[k for k,v in best['bounds'].items() if isinstance(v,dict) and v.get('search',True) and isinstance(v.get('lo'),(int,float)) and isinstance(v.get('hi'),(int,float)) and v['hi']>v['lo'] and isinstance(best['knobs'].get(k),(int,float))];results=[]
 for r in chosen:
  try:
   cfg=load_config(pathlib.Path('runs')/r['run']/'config.yaml');knobs=r['knobs'];h,base=surface(cfg,knobs)
   if h!=r['h']:raise ValueError('reconstructed design hash '+h+' != stored '+r['h'])
   cols=[];moves=[]
   for k in keys:
    b=r['bounds'][k];step=.01*(b['hi']-b['lo']);v=knobs[k];delta=step if v+step<=b['hi'] else -step;kn=dict(knobs);kn[k]=v+delta;_,q=surface(cfg,kn);diff=q-base;cols.append((diff/delta).ravel());moves.append(float(np.sqrt(np.mean(np.sum(diff*diff,axis=2)))))
   mat=np.column_stack(cols);norm=np.linalg.norm(mat,axis=0);normal=np.divide(mat,norm,out=np.zeros_like(mat),where=norm>1e-12);sv=np.linalg.svd(normal,compute_uv=False);pairs=[(keys[i],keys[j],float(normal[:,i]@normal[:,j])) for i in range(len(keys)) for j in range(i+1,len(keys)) if abs(normal[:,i]@normal[:,j])>.95];results.append(dict(hash=h,movement=moves,singular=sv.tolist(),rank=int(np.sum(sv>sv[0]*1e-6)),pairs=pairs))
  except Exception as e:results.append(dict(hash=r['h'],error=type(e).__name__+': '+str(e)))
 out[name]=dict(keys=keys,results=results);print(name,len(results),'fail',sum('error' in z for z in results),flush=True)
open('scratch/fable_architecture/.x4/generated_geometry.json','w').write(json.dumps(out,indent=2))
