import ast, pathlib,copy,json,pickle,numpy as np,collections
from hornlab_search.config import load_config
from hornlab_search.types import Design
from hornlab_search.bo.data import materialize_geometry
s=pathlib.Path('scratch/fable_architecture/.x1/probe.py').read_text();fn=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name=='sample');exec(compile(ast.Module(body=[fn],type_ignores=[]),'x1sample','exec'))
R=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'));rng=np.random.default_rng(123);out={}
for name in ['hl__osse_rrect_fold_warm_v7','hl__ext_throat_hvlaw_v7']:
 rs=[r for r in R if r['ok'] and r['config']==name]; best=min(rs,key=lambda r:r['J']); remaining=[r for r in rs if r['h']!=best['h']]; chosen=[best]+[remaining[i] for i in rng.choice(len(remaining),min(10,len(remaining)),replace=False)];b=best['bounds'];keys=[k for k,v in b.items() if isinstance(v,dict) and v.get('search',True) and isinstance(v.get('lo'),(int,float)) and isinstance(v.get('hi'),(int,float)) and v['hi']>v['lo'] and isinstance(best['params'].get(k),(int,float))];results=[]
 for r in chosen:
  try:
   p=pathlib.Path('runs')/r['run'];cfg=load_config(p/'config.yaml');recipe=json.load(open(p/'designs'/r['h']/'design.json'));params=recipe['params'];base=sample(materialize_geometry(Design(recipe['family'],params),cfg,resolution_mm=10)['inner_points'],31,65);cols=[];moves=[]
   for k in keys:
    step=.01*(b[k]['hi']-b[k]['lo']);v=params[k];delta=step if v+step<=b[k]['hi'] else -step
    a=copy.deepcopy(params);a[k]=v+delta; q=sample(materialize_geometry(Design(recipe['family'],a),cfg,resolution_mm=10)['inner_points'],31,65);diff=q-base;cols.append((diff/delta).ravel());moves.append(float(np.sqrt(np.mean(np.sum(diff*diff,axis=2)))))
   mat=np.column_stack(cols);norm=np.linalg.norm(mat,axis=0);normal=np.divide(mat,norm,out=np.zeros_like(mat),where=norm>1e-12);sv=np.linalg.svd(normal,compute_uv=False);pairs=[(keys[i],keys[j],float(normal[:,i]@normal[:,j])) for i in range(len(keys)) for j in range(i+1,len(keys)) if abs(normal[:,i]@normal[:,j])>.95];results.append(dict(hash=r['h'],movement=moves,singular=sv.tolist(),rank=int(np.sum(sv>sv[0]*1e-6)),pairs=pairs))
  except Exception as e:results.append(dict(hash=r['h'],error=str(e)))
 out[name]=dict(keys=keys,results=results);print(name,len(results),'fail',sum('error' in z for z in results),flush=True)
open('scratch/fable_architecture/.x4/geometry.json','w').write(json.dumps(out,indent=2))
