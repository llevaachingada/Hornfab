import pickle, numpy as np, collections, warnings
warnings.filterwarnings('ignore')
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import cross_val_predict, KFold
from sklearn.inspection import permutation_importance
from scipy.stats import spearmanr
allrows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'))
bycfg=collections.defaultdict(list)
for r in allrows: bycfg[(r['config'],r['brief'])].append(r)
print('== A. per-lane parameter structure (lanes with >=100 valid rows)')
print('lane | d searched | CV rank-corr of tree model on J | knobs carrying 90% of importance | top knobs | elite(top10%) knobs pinned within 3% of a bound | PCA dims for 90% of elite knob variance')
for (c,b),rs in sorted(bycfg.items(),key=lambda kv:-sum(x['ok'] for x in kv[1])):
    ok=[r for r in rs if r['ok']]
    if len(ok)<100: continue
    src=lambda r:(r['knobs'] if r['knobs'] else r['params']) or {}
    bounds=ok[0]['bounds'] or {}
    keys=[k for k,v in bounds.items() if isinstance(v,dict) and v.get('search',True) and isinstance(v.get('lo'),(int,float)) and v.get('hi')!=v.get('lo') and isinstance(src(ok[0]).get(k),(int,float))]
    if len(keys)<2: print(c,'no searched keys parsed',len(keys)); continue
    lo=np.array([bounds[k]['lo'] for k in keys],float); hi=np.array([bounds[k]['hi'] for k in keys],float)
    X=np.array([[src(r).get(k,np.nan) for k in keys] for r in ok],float); y=np.log(np.array([r['J'] for r in ok]))
    g=np.isfinite(X).all(1); X=X[g]; y=y[g]; Xn=(X-lo)/(hi-lo)
    et=ExtraTreesRegressor(300,min_samples_leaf=3,random_state=0,n_jobs=4)
    pred=cross_val_predict(et,Xn,y,cv=KFold(5,shuffle=True,random_state=0)); rho=spearmanr(pred,y)[0]
    et.fit(Xn,y); imp=permutation_importance(et,Xn,y,n_repeats=5,random_state=0,n_jobs=4).importances_mean; imp=np.clip(imp,0,None)
    o=np.argsort(-imp); cum=np.cumsum(imp[o])/imp.sum(); k90=int(np.searchsorted(cum,0.9)+1)
    el=Xn[np.argsort(y)[:max(10,len(y)//10)]]
    pinned=[keys[i] for i in range(len(keys)) if (np.mean(el[:,i]<0.03)>0.5 or np.mean(el[:,i]>0.97)>0.5)]
    s=np.linalg.svd(el-el.mean(0),compute_uv=False); e=s**2/np.sum(s**2); pd=int(np.searchsorted(np.cumsum(e),0.9)+1)
    print(f'{c[:32]:32s} {b:6s} n={len(y):3d} | d={len(keys):2d} | rho={rho:.2f} | {k90} | {", ".join(keys[i] for i in o[:3])} | pinned: {pinned} | {pd}')

print('\n== B. allocation replay on the 27 CD-brief lanes (each lane = its rows in time order; pulling a lane reveals its next row)')
lanes={}
for (c,b),rs in bycfg.items():
    if b!='cd': continue
    rs=sorted(rs,key=lambda r:(r['created'] or '',r['n'] or 0))
    lanes[c]=np.array([r['J'] if r['ok'] else np.inf for r in rs])
names=list(lanes); T=sum(len(v) for v in lanes.values()); best=min(v.min() for v in lanes.values())
print('lanes',len(names),'total attempts',T,'global best',round(best,3),'in',[n for n in names if lanes[n].min()==best][0])
def run(policy,seed=0,batch=8):
    rng=np.random.default_rng(seed); pos={n:0 for n in names}; cur={n:np.inf for n in names}; hist=[]; used=0; alive=set(names)
    def pull(n,k):
        nonlocal used
        k=min(k,len(lanes[n])-pos[n]); 
        if k<=0: alive.discard(n); return
        cur[n]=min(cur[n],lanes[n][pos[n]:pos[n]+k].min()); pos[n]+=k; used+=k; hist.append((used,min(cur.values())))
        if pos[n]>=len(lanes[n]): alive.discard(n)
    if policy=='round_robin':
        while alive:
            for n in list(names):
                if n in alive: pull(n,batch)
    elif policy=='halving':   # successive halving: 16 rows each, keep best half, double
        k=16; act=list(names)
        while act and alive:
            for n in act:
                if n in alive: pull(n,k)
            act=sorted([n for n in act if n in alive],key=lambda n:cur[n])[:max(1,len(act)//2)]; k*=2
            if len(act)==1:
                while act[0] in alive: pull(act[0],batch)
                break
    elif policy=='ucb':       # bandit on rank of current best with an exploration bonus
        for n in names: pull(n,batch)
        t=len(names)
        while alive:
            t+=1
            sc={n:(-np.log(cur[n]) if np.isfinite(cur[n]) else -5)+0.35*np.sqrt(np.log(t)/(pos[n]/batch)) for n in alive}
            pull(max(sc,key=sc.get),batch)
    elif policy=='actual':
        ev=sorted(((r['created'] or '',r['n'] or 0,r['config'],r['J'] if r['ok'] else np.inf) for r in allrows if r['brief']=='cd'))
        b=np.inf
        for i,e in enumerate(ev): b=min(b,e[3]); hist.append((i+1,b))
    return hist
def reach(hist,thr): 
    for u,b in hist:
        if b<=thr: return u
    return None
for pol in ('actual','round_robin','halving','ucb'):
    h=run(pol); print(f'{pol:12s} attempts to reach J<=5.0: {reach(h,5.0)}  <=4.0: {reach(h,4.0)}  <=3.65: {reach(h,3.65)}  <=3.2: {reach(h,3.2)}   (total used {h[-1][0]})')
top=[n for n in names if lanes[n].min()<=4.0]; print('lanes that ever reach J<=4.0:',top,' their first-16-row best:',[round(float(lanes[n][:16].min()),2) for n in top])
first16=sorted(((float(v[:16].min()),n) for n,v in lanes.items())); print('rank of lanes by first-16-row best:',[(n[:22],round(j,1)) for j,n in first16[:8]])
print('spearman(first-16 best, final best) across lanes: %.2f'%spearmanr([lanes[n][:16].min() if np.isfinite(lanes[n][:16].min()) else 99 for n in names],[lanes[n].min() for n in names])[0])
