import ast, collections, pathlib, pickle
import numpy as np

root=pathlib.Path('scratch/fable_architecture')
source=(root/'.fable/an3.py').read_text()
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='desc')
NS=12
exec(compile(ast.Module(body=[node],type_ignores=[]),str(root/'.fable/an3.py'),'exec'))
rows=pickle.load(open(root/'.fable/rows.pkl','rb'))
out=[]; failed=[]
for r in rows:
    if not (r['ok'] and len(r['f'])==18): continue
    p=pathlib.Path('runs')/r['run']/'designs'/r['h']/'mesh.msh'
    try:
        d=desc(p)
        if d is None or not np.isfinite(d).all(): raise ValueError('incomplete descriptor')
        y=np.array(r['bwh']+r['bwv']+r['di'],float)
        if not np.isfinite(y).all(): raise ValueError('non-finite response')
        out.append((r,d,y))
    except Exception as e: failed.append((r['run'],r['h'],repr(e)))
with open(root/'.e1/descriptors.pkl','wb') as f: pickle.dump((out,failed),f)
print('extracted',len(out),'failed',len(failed), 'eligible CD lanes',sum(n>=100 for n in collections.Counter(r['config'] for r,d,y in out if r['brief']=='cd').values()),flush=True)
