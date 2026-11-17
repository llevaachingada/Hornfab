import pickle,collections,numpy as np,json
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.inspection import permutation_importance
R=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'));names=['hl__osse_rrect_fold_warm_v7','hl__ext_throat_hvlaw_v7','hl__klangfilm_lame_curved_v1','hl__crowe_x_osse_cd_v7','hl__biradial_es_style_v7']; rng=np.random.default_rng(123);out={}
for name in names:
 rows=sorted([r for r in R if r['ok'] and r['config']==name and len(r['f'])==18],key=lambda r:r['created']);src=lambda r:r['knobs'] or r['params'];b=rows[0]['bounds'];keys=[k for k,v in b.items() if isinstance(v,dict) and v.get('search',True) and isinstance(v.get('lo'),(float,int)) and isinstance(v.get('hi'),(float,int)) and v['hi']>v['lo'] and isinstance(src(rows[0]).get(k),(float,int))];
 X=np.array([[src(r).get(k,np.nan) for k in keys] for r in rows]); f=np.array(rows[0]['f']);band=f>=700
 y=np.array([[r['J'],np.mean((np.array(r['bwh'])[band]-80)**2),np.mean((np.array(r['bwv'])[band]-50)**2)] for r in rows]);ok=np.isfinite(X).all(axis=1)&np.isfinite(y).all(axis=1);X=X[ok];y=y[ok];n=len(X); models={}
 for label,indices in [('all',np.arange(n)),('early',np.arange(n//2)),('late',np.arange(n//2,n))]:
  scores=[]
  for rep in range(5):
   order=rng.permutation(indices); tr=order[:int(.8*len(order))];test=order[int(.8*len(order)):];boots=rng.choice(tr,len(tr),replace=True);per=[]
   for i in range(3):
    mdl=ExtraTreesRegressor(n_estimators=80,min_samples_leaf=3,random_state=rep,n_jobs=4).fit(X[boots],y[boots,i]); per.append(permutation_importance(mdl,X[test],y[test,i],n_repeats=5,random_state=rep,n_jobs=1).importances_mean)
   scores.append(per)
  a=np.array(scores);models[label]=dict(median=np.median(a,axis=0).tolist(),minimum=np.min(a,axis=0).tolist(),maximum=np.max(a,axis=0).tolist())
 out[name]=dict(n=n,keys=keys,models=models)
 print(name,n,len(keys),flush=True)
open('scratch/fable_architecture/.x4/acoustic.json','w').write(json.dumps(out,indent=2))
