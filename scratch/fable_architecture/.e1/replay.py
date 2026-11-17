import collections, json, pathlib, pickle, sys
from types import SimpleNamespace
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from hornlab_search.objective.scalar_v7 import _cov_term_v5, resolve_v7_weights
from hornlab_search.metrics.di import target_di_gaussian_db

root=pathlib.Path('scratch/fable_architecture')
sys.path.insert(0,str((root/'.tmp').resolve()))
import fable_replay_harness as H
data, failures=pickle.load(open(root/'.e1/descriptors.pkl','rb'))
rows=[r for r,x,y in data]; X=np.array([x for r,x,y in data]); Y=np.array([y for r,x,y in data]); G=np.array([r['config'] for r in rows]); E=np.array(['OSSE' if not r['gen'] else ('GRID' if r['gen']=='grid' else 'GEN-FF') for r in rows]); C=np.array([r['brief']=='cd' for r in rows]); f=np.array(rows[0]['f'])
cfg={}
for r in rows:
    if r['config'] not in cfg: cfg[r['config']]=H.brief(pathlib.Path('runs')/r['run']/'config.yaml')
def score(y,name):
    b=cfg[name]; t=b.target; p=b.objective_params; w=resolve_v7_weights(b.weights)
    band=(f>=t.band_lo_hz)&(f<=t.band_hi_hz); ref=t.di_target_db if t.di_target_db is not None else target_di_gaussian_db(t.coverage_h_deg,t.coverage_v_deg)
    out=[]
    for z in y:
        m=SimpleNamespace(bw_h_deg=z[:18],bw_v_deg=z[18:36])
        cov=_cov_term_v5(m,None,t,f,band,p); di=np.mean((z[36:][band]-ref)**2)/10 if w['di'] else 0
        out.append(w['cov']*cov/p.tolerances['cov']+w['di']*di/p.tolerances['di'])
    return np.array(out)
truth=np.zeros(len(rows)); errs=[]
for g in sorted(set(G)):
    ix=np.flatnonzero(G==g); truth[ix]=score(Y[ix],g)
    for i in ix:
        w=resolve_v7_weights(cfg[g].weights); terms=rows[i]['terms']; error=abs(truth[i]-(w['cov']*terms['cov']+w['di']*terms['di'])); errs.append(error)
        if error>1e-7 and len([v for v in errs if v>1e-7])<3: print('mismatch',g,truth[i],terms['cov'],terms['di'],cfg[g].objective_params,flush=True)
print('proxy parity max',max(errs),flush=True)
if max(errs)>1e-7: raise RuntimeError('proxy score parity failed')
def model(): return ExtraTreesRegressor(n_estimators=32,min_samples_leaf=2,random_state=0,n_jobs=2)
def knobmatrix(ix):
    rs=[rows[i] for i in ix]; bounds=rs[0]['bounds']; keys=[k for k,v in bounds.items() if v.get('hi',0)>v.get('lo',0) and v.get('search',True)]
    arr=[]
    for r in rs:
        d=r['knobs'] or r['params']; arr.append([float(d[k]) for k in keys])
    return np.array(arr)
def reveals(order,values,threshold):
    return max(8,next((j+1 for j,i in enumerate(order) if values[i]<=threshold),len(order)+1))
def runlane(ix,seed,kind,transfer=False):
    rng=np.random.default_rng(seed); n=len(ix); start=list(rng.choice(n,8,replace=False)); remaining=[i for i in range(n) if i not in start]; order=start[:]; threshold=min(truth[ix])+.1
    if any(truth[ix[i]]<=threshold for i in order): return reveals(order,truth[ix],threshold)
    if kind=='actual': return reveals(order+remaining,truth[ix],threshold)
    if kind=='random': rng.shuffle(remaining); return reveals(order+remaining,truth[ix],threshold)
    knobs=knobmatrix(ix) if kind=='score' else None
    ext=np.flatnonzero(E!=E[ix[0]]) if transfer else np.array([],int)
    while remaining:
        if kind=='score':
            m=model().fit(knobs[order],truth[ix[order]]); pred=m.predict(knobs[remaining])
        else:
            tr=np.r_[ext,ix[order]]; m=model().fit(X[tr],Y[tr]); pred=score(m.predict(X[ix[remaining]]),G[ix[0]])
        chosen=[remaining[k] for k in np.argsort(pred,kind='stable')[:8]]
        order.extend(chosen); remaining=[k for k in remaining if k not in chosen]
        if any(truth[ix[i]]<=threshold for i in chosen): break
    return reveals(order,truth[ix],threshold)
results={'parity_max':max(errs),'failed_extraction':len(failures),'lanes':{},'cross_engine':{}}
for g in sorted(set(G[C])):
    ix=np.flatnonzero((G==g)&C)
    if len(ix)<100: continue
    try:
        v={}
        for kind in ('score','response','actual','random','transfer'):
            v[kind]=[runlane(ix,s,'response' if kind=='transfer' else kind,kind=='transfer') for s in range(10)]
        v['n']=len(ix); best=ix[np.argmin(truth[ix])]; v['proxy_best_full_j_decile']=bool(rows[best]['J']<=np.quantile([rows[i]['J'] for i in ix],.1))
        results['lanes'][g]=v; print(g,{k:np.median(v[k]) for k in ('score','response','actual','random','transfer')},flush=True)
    except Exception as e:
        results['lanes'][g]={'n':len(ix),'error':repr(e)}; print('ERROR',g,repr(e),flush=True)
    (root/'.e1/results.json').write_text(json.dumps(results,indent=2))
for engine in sorted(set(E)):
    tr=np.flatnonzero(E!=engine); te=np.flatnonzero((E==engine)&C); pred=model().fit(X[tr],Y[tr]).predict(X[te]); est=np.array([score(pred[j:j+1],G[i])[0] for j,i in enumerate(te)])
    top=set(np.argsort(truth[te])[:int(np.ceil(len(te)*.1))]); ranking=np.argsort(est); results['cross_engine'][engine]={'n':len(te),'top10_recall':len(top.intersection(ranking[:int(np.ceil(len(te)*.1))]))/len(top),'top25_recall':len(top.intersection(ranking[:int(np.ceil(len(te)*.25))]))/len(top)}
    (root/'.e1/results.json').write_text(json.dumps(results,indent=2)); print(engine,results['cross_engine'][engine],flush=True)
