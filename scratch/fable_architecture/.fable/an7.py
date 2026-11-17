"""Would a predictor trained on OTHER constructions have chosen better designs to solve first
than the lane's actual first solves? Read-only replay; siblings excluded from training."""
import numpy as np, warnings, io, contextlib, re, collections
warnings.filterwarnings('ignore')
src=open('scratch/fable_architecture/.fable/an3.py').read().split("print('leave-one-LANE-out")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
from sklearn.ensemble import ExtraTreesRegressor
J=np.array([r['J'] for r in keep]); N=np.array([r['n'] or 0 for r in keep]); B=np.array([r['brief'] for r in keep])
fam=lambda c: re.sub(r'(_smooth)?(_warm)?(_v\d+)?$','',re.sub(r'_smooth','',c))
F=np.array([fam(c) for c in G]); nf=len(f); band=np.where(f>=700)[0]
cov=lambda M: np.mean(np.where(M[:,band]<80,2,1)*(M[:,band]-80)**2,1)/100+0.5*np.mean(np.where(M[:,nf+band]<50,2,1)*(M[:,nf+band]-50)**2,1)/100
print('designs',len(keep),'lanes',len(set(G)),'construction groups',len(set(F)))
res=[]
for g in sorted(set(G)):
    te=(G==g)
    if te.sum()<40 or B[te][0]!='cd': continue
    tr=F!=fam(g)                       # exclude the lane AND its siblings
    m=ExtraTreesRegressor(200,min_samples_leaf=2,random_state=0,n_jobs=6).fit(X[tr],Y[tr]); pc=cov(m.predict(X[te]))
    j=J[te]; n=N[te]; order=np.argsort(pc)
    first8=j[np.argsort(n)[:8]].min()          # best J among the 8 earliest-solved sampled designs of the lane
    pick8=j[order[:8]].min()                   # best J among the predictor's top 8
    rnd=np.mean([j[np.random.default_rng(s).permutation(len(j))[:8]].min() for s in range(200)])
    pct=lambda v: 100*np.mean(j<v)             # percentile within lane (0 = best)
    res.append((g,te.sum(),j.min(),first8,pick8,rnd,pct(first8),pct(pick8)))
    print(f'{g[:36]:36s} n={te.sum():3d} lane best {j.min():6.2f} | earliest-8 best {first8:6.2f} | predictor top-8 best {pick8:6.2f} | random-8 best {rnd:6.2f}')
R=np.array([r[2:] for r in res],float)
print('lanes',len(R))
print('median gap to lane best: earliest-8 %.2f, predictor-8 %.2f, random-8 %.2f'%tuple(np.median(R[:,k]-R[:,0]) for k in (1,2,3)))
print('predictor-8 better than earliest-8 in %d of %d lanes; better than random-8 in %d'%((R[:,2]<R[:,1]).sum(),len(R),(R[:,2]<R[:,3]).sum()))
print('median within-lane percentile of the pick (0=best): earliest-8 %.0f, predictor-8 %.0f'%(np.median(R[:,4]),np.median(R[:,5])))
