"""Cross-family transfer test: family-agnostic geometry descriptors read from stored meshes -> beamwidth.
Leave-whole-lanes-out (GroupKFold by config). Read-only."""
import pickle, numpy as np, collections, pathlib, warnings, sys
warnings.filterwarnings('ignore')
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import GroupKFold
rows=[r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok'] and r['f'] and len(r['f'])==18]
rng=np.random.default_rng(0); bycfg=collections.defaultdict(list)
for r in rows: bycfg[r['config']].append(r)
sel=[]
for c,rs in bycfg.items():
    idx=rng.permutation(len(rs))[:70]; sel+=[rs[i] for i in idx]
NS=12
def desc(path):
    txt=open(path).read()
    a=txt.index('$Nodes')+7; b=txt.index('$EndNodes'); lines=txt[a:b].split('\n',1)
    nd=np.array(lines[1].split(),float).reshape(-1,4)[:,1:]*1000.0
    e0=txt.index('$Elements')+10; e1=txt.index('$EndElements'); el=txt[e0:e1].split('\n')[1:]
    wall=set()
    for ln in el:
        p=ln.split()
        if len(p)>=8 and p[1]=='2' and p[3]=='1': wall.update((int(p[-3])-1,int(p[-2])-1,int(p[-1])-1))
    w=nd[sorted(wall)]
    zmax=w[:,2].max(); tol=max(1.0,0.004*zmax)
    out=[]
    for ax,other in ((0,1),(1,0)):
        pl=w[np.abs(w[:,other])<tol]
        prof=[]
        for i in range(NS):
            lo,hi=zmax*i/NS,zmax*(i+1)/NS; m=(pl[:,2]>=lo)&(pl[:,2]<hi)&(pl[:,ax]>1.0)
            prof.append(pl[m,ax].min() if m.any() else np.nan)
        prof=np.array(prof); ok=np.isfinite(prof)
        if ok.sum()<3: return None
        prof=np.interp(np.arange(NS),np.arange(NS)[ok],prof[ok]); out.append(prof)
    return np.concatenate([[zmax, w[:,0].max(), w[:,1].max()], out[0], out[1]])
X=[];Y=[];G=[];keep=[]
for r in sel:
    p=pathlib.Path('runs')/r['run']/'designs'/r['h']/'mesh.msh'
    if not p.is_file(): continue
    try: d=desc(p)
    except Exception as e: continue
    if d is None: continue
    y=np.concatenate([r['bwh'],r['bwv'],r['di']]).astype(float)
    if not np.isfinite(y).all(): continue
    X.append(d);Y.append(y);G.append(r['config']);keep.append(r)
X=np.array(X);Y=np.array(Y);G=np.array(G); f=np.array(keep[0]['f']); nf=len(f)
print('designs with mesh descriptors:',len(X),'lanes:',len(set(G)))
band=np.where(f>=600)[0]
def evalset(Xf,label):
    P=np.zeros_like(Y); 
    for tr,te in GroupKFold(n_splits=len(set(G))).split(Xf,Y,G):
        m=ExtraTreesRegressor(200,min_samples_leaf=2,random_state=0,n_jobs=6).fit(Xf[tr],Y[tr]); P[te]=m.predict(Xf[te])
    res={}
    for nm,off in (('bw_h',0),('bw_v',nf),('DI',2*nf)):
        yt=Y[:,off+band]; yp=P[:,off+band]
        base=np.zeros_like(yt)
        for g in set(G):
            te=G==g; base[te]=Y[~te][:,off+band].mean(0)
        res[nm]=(np.mean(np.abs(yt-yp)), np.mean(np.abs(yt-base)), 1-np.sum((yt-yp)**2)/np.sum((yt-base)**2))
    print(f'{label:34s} '+'  '.join(f'{k}: MAE {v[0]:5.1f} (naive {v[1]:5.1f}) skill R2 {v[2]:+.2f}' for k,v in res.items()))
    return P
print('leave-one-LANE-out prediction of the 600-8000 Hz curves for a lane never seen in training:')
evalset(X[:,:3],'A. bounding size only (D,W/2,H/2)')
P=evalset(X,'B. size + H/V wall profiles (27-d)')
# per-engine-group holdout: train on other engines entirely
grp=np.array(['OSSE' if r['gen']=='' else ('GRID' if r['gen']=='grid' else 'GEN-FF') for r in keep])
print('leave-one-ENGINE-out (train on the other two engine groups only), descriptor set B:')
for g in ('OSSE','GRID','GEN-FF'):
    te=grp==g; m=ExtraTreesRegressor(200,min_samples_leaf=2,random_state=0,n_jobs=6).fit(X[~te],Y[~te]); p=m.predict(X[te])
    s=[]
    for nm,off in (('bw_h',0),('bw_v',nf)):
        yt=Y[te][:,off+band]; base=Y[~te][:,off+band].mean(0); s.append(f'{nm} MAE {np.mean(np.abs(yt-p[:,off+band])):5.1f} (naive {np.mean(np.abs(yt-base)):5.1f}) R2 {1-np.sum((yt-p[:,off+band])**2)/np.sum((yt-base)**2):+.2f}')
    print(f'   held-out {g:7s} n={te.sum():4d}  '+'  '.join(s))
# ranking usefulness: within each held-out lane, does predicted coverage error rank designs?
from scipy.stats import spearmanr
def coverr(M): 
    fb=band; return np.mean((M[:,fb]-80)**2,1)+0.5*np.mean((M[:,nf+fb]-50)**2,1)
ce_t=coverr(Y); ce_p=coverr(P); rr=[]
for g in set(G):
    m=G==g
    if m.sum()>=30: rr.append(spearmanr(ce_t[m],ce_p[m])[0])
print('within-held-out-lane rank correlation of predicted vs true coverage error: median %.2f, quartiles %.2f / %.2f over %d lanes'%(np.median(rr),np.percentile(rr,25),np.percentile(rr,75),len(rr)))
print('across all held-out designs: spearman %.2f'%spearmanr(ce_t,ce_p)[0])
