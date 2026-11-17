"""Shared-backbone expressiveness: how many shape modes describe every lane's H/V wall profiles,
and how many are needed to predict the response? Read-only."""
import numpy as np, warnings, sys, io, contextlib
warnings.filterwarnings('ignore')
src=open('scratch/fable_architecture/.fable/an3.py').read().split("print('leave-one-LANE-out")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
np.savez('scratch/fable_architecture/.fable/desc.npz',X=X,Y=Y,G=G)
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import GroupKFold
from scipy.interpolate import make_lsq_spline
prof=X[:,3:]            # 12 H + 12 V inner half-widths (mm) at equal depth fractions
D=X[:,0:1]
print('designs',len(X),'lanes',len(set(G)),' profile matrix',prof.shape)
mu=prof.mean(0); U,S,Vt=np.linalg.svd(prof-mu,full_matrices=False)
print('== shape-mode count vs reconstruction error of H/V wall profiles across ALL lanes (mm RMS / worst-design mm RMS)')
for k in (2,3,4,6,8,10,12):
    rec=(U[:,:k]*S[:k])@Vt[:k]+mu; e=np.sqrt(np.mean((rec-prof)**2,1)); print(f'   {k:2d} modes (+depth): RMS {np.sqrt(np.mean(e**2)):5.2f} mm   95th pct {np.percentile(e,95):5.2f}   worst {e.max():5.2f}')
print('== leave-one-lane-out: are modes learned WITHOUT a lane able to describe that lane? (8 modes)')
errs={}
for g in sorted(set(G)):
    te=G==g; m2=prof[~te].mean(0); u,s,vt=np.linalg.svd(prof[~te]-m2,full_matrices=False); B=vt[:8]
    rec=((prof[te]-m2)@B.T)@B+m2; errs[g]=np.sqrt(np.mean((rec-prof[te])**2))
v=np.array(list(errs.values())); print('   median lane RMS %.2f mm; worst lanes:'%np.median(v),sorted(((round(e,1),g[:30]) for g,e in errs.items()),reverse=True)[:5])
print('== per-plane cubic B-spline with n control values (clamped, equal knots), fit error over all designs')
z=np.linspace(0,1,12)
for n in (4,5,6,8):
    t=np.concatenate([[0]*4,np.linspace(0,1,n-2)[1:-1],[1]*4]); e=[]
    for row in prof:
        for p in (row[:12],row[12:]):
            sp=make_lsq_spline(z,p,t,k=3); e.append(np.sqrt(np.mean((sp(z)-p)**2)))
    e=np.array(e); print(f'   {n} control values per plane ({2*n} total): RMS {np.sqrt(np.mean(e**2)):5.2f} mm  95th pct {np.percentile(e,95):5.2f}  worst {e.max():5.2f}')
print('== response prediction from the first k shape modes + depth (leave-one-lane-out skill R2 on bw_h / bw_v, 600-8000 Hz)')
f=np.array(keep[0]['f']); nf=len(f); band=np.where(f>=600)[0]
Zs=(prof-mu)@Vt.T
for k in (2,3,5,8,12,24):
    Xf=np.hstack([D,Zs[:,:k]]); P=np.zeros_like(Y)
    for tr,te in GroupKFold(n_splits=len(set(G))).split(Xf,Y,G):
        P[te]=ExtraTreesRegressor(150,min_samples_leaf=2,random_state=0,n_jobs=6).fit(Xf[tr],Y[tr]).predict(Xf[te])
    out=[]
    for off in (0,nf):
        yt=Y[:,off+band]; base=np.zeros_like(yt)
        for g in set(G): te=G==g; base[te]=Y[~te][:,off+band].mean(0)
        out.append(1-np.sum((yt-P[:,off+band])**2)/np.sum((yt-base)**2))
    print(f'   k={k:2d}: bw_h {out[0]:+.2f}  bw_v {out[1]:+.2f}')
