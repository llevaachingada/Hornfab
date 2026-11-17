import json, pickle
import numpy as np
from sklearn.decomposition import PCA
from scipy.spatial.distance import cdist

d=np.load('scratch/fable_architecture/.fable/desc.npz'); X,Y,G=d['X'],d['Y'],d['G']
rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'))
eng={r['config']: ('OSSE' if not r['gen'] else 'GRID' if r['gen']=='grid' else 'GEN-FF') for r in rows if r['ok']}
E=np.array([eng[g] for g in G]); rng=np.random.default_rng(2701)
p=PCA(n_components=8).fit(X[:,3:]); xp=p.transform(X[:,3:]); x=np.column_stack([X[:,0],xp]); x=(x-x.mean(0))/x.std(0)
q=PCA(n_components=6).fit(Y); y=q.transform(Y); y=(y-y.mean(0))/y.std(0)
dist=cdist(x,x); np.fill_diagonal(dist,np.inf)
centres=rng.choice(len(x),300,replace=False)
def fit(i,ids):
    dx=x[ids]-x[i]; dy=y[ids]-y[i]
    return np.linalg.lstsq(dx,dy,rcond=None)[0].T
def eval_group(other=False,multilane=False, residual=False):
    result=[]
    for i in centres:
        ids=np.argsort(dist[i]); ids=ids[np.isfinite(dist[i,ids])]
        if other: ids=ids[E[ids]!=E[i]]
        if multilane and len(set(G[ids[:50]]))<2: continue
        tr,te=ids[:40],ids[40:50]
        if len(te)<10: continue
        J=fit(i,tr); dy=y[te]-y[i]; pred=(x[te]-x[i])@J.T
        if residual:
            # Local size-only linear projection fitted on training deltas, evaluated out of sample.
            st=x[tr,:1]-x[i,:1]; sy=y[tr]-y[i]; b=np.linalg.lstsq(st,sy,rcond=None)[0]
            sz=x[te,:1]-x[i,:1]; dy=dy-sz@b; pred=pred-sz@b
        denom=np.sum((dy-dy.mean(0))**2)
        sv=np.linalg.svd(J,compute_uv=False)
        result.append([1-np.sum((dy-pred)**2)/denom if denom else np.nan, sv[0]/sv[-1],*sv,len(set(G[ids[:50]]))])
    return np.array(result)
def quant(a): return np.quantile(a,[.1,.25,.5,.75,.9]).tolist()
def summ(a): return {'n':len(a),'r2':quant(a[:,0]),'condition':quant(a[:,1]),'sv_median':np.median(a[:,2:8],axis=0).tolist(),'fraction_sv_below_1pct':np.mean(a[:,2:8] < .01*a[:,2:3],axis=0).tolist(),'multilane_fraction':float(np.mean(a[:,-1]>=2))}
pair_centres=rng.choice(len(x),500,replace=False); corrections={}
for factor in [0,2,4]:
    out=[]; actual_ratios=[]
    for i in pair_centres:
        ids=np.argsort(dist[i]); radius=dist[i,ids[39]]
        eligible=ids[50:]
        if factor==0: target=ids[0]; tr=ids[1:41]
        else: target=eligible[np.argmin(abs(dist[i,eligible]-factor*radius))]; tr=ids[:40]
        J=fit(i,tr); true=x[target]-x[i]; pred=np.linalg.pinv(J)@(y[target]-y[i]); den=np.linalg.norm(true)
        if den>1e-12: out.append([np.linalg.norm(pred-true)/den,np.linalg.norm(pred-true)**2,den**2]); actual_ratios.append(dist[i,target]/radius)
    a=np.array(out); corrections[str(factor)]={'n':len(a),'relative_error':quant(a[:,0]),'skill_no_change':float(1-a[:,1].sum()/a[:,2].sum()),'actual_radius_ratio':quant(actual_ratios)}
result={'shape_variance':float(p.explained_variance_ratio_.sum()),'response_variance':float(q.explained_variance_ratio_.sum()),'all':summ(eval_group()),'multi_lane':summ(eval_group(multilane=True)),'other_engine':summ(eval_group(other=True)),'size_residual':summ(eval_group(residual=True)),'corrections':corrections,'response_pc_loadings':q.components_.tolist()}
open('scratch/fable_architecture/.e2/brief_results.json','w').write(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='response_pc_loadings'},indent=2))
