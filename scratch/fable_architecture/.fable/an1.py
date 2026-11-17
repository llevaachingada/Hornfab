import pickle, numpy as np, collections, warnings
warnings.filterwarnings('ignore')
rows=[r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok'] and r['f'] and len(r['f'])==18]
print('ok rows with 18-pt grid',len(rows))
f=np.array(rows[0]['f']); band=f>=600
def vec(r):
    return np.concatenate([np.array(r['bwh'],float)[band],np.array(r['bwv'],float)[band],np.array(r['di'],float)[band]*5])  # DI dB x5 ~ deg scale
X=np.array([vec(r) for r in rows]); good=np.isfinite(X).all(1); X=X[good]; rows=[r for r,g in zip(rows,good) if g]
print('finite',len(rows),'response dim',X.shape[1])
mu=X.mean(0); U,S,Vt=np.linalg.svd(X-mu,full_matrices=False); ev=S**2/np.sum(S**2)
print('== 1. response-space PCA (bw_h, bw_v, DI over 600-8000 Hz) cumulative variance:',np.round(np.cumsum(ev)[:10],3))
Z=(X-mu)@Vt[:6].T
grp=lambda r:(r['engine'] if r['gen']=='' else ('GRID' if r['gen']=='grid' else 'GEN-FF'))
for g in ('OSSE','GRID','GEN-FF'):
    m=np.array([grp(r)==g for r in rows]); Xg=X[m]; s=np.linalg.svd(Xg-Xg.mean(0),compute_uv=False); e=s**2/np.sum(s**2)
    print(f'   {g:7s} n={m.sum():4d}  PCs for 90%: {np.searchsorted(np.cumsum(e),0.90)+1}  95%: {np.searchsorted(np.cumsum(e),0.95)+1}   range PC1 [{Z[m,0].min():.0f},{Z[m,0].max():.0f}] PC2 [{Z[m,1].min():.0f},{Z[m,1].max():.0f}] PC3 [{Z[m,2].min():.0f},{Z[m,2].max():.0f}]')
# what the first PCs mean
fb=f[band]; nb=band.sum()
for k in range(4):
    v=Vt[k]; print(f'   PC{k+1} ({ev[k]*100:.0f}%): mean loading bw_h {v[:nb].mean():+.2f} bw_v {v[nb:2*nb].mean():+.2f} DI {v[2*nb:].mean():+.2f} | bw_h low-f {v[:4].mean():+.2f} high-f {v[nb-4:nb].mean():+.2f} | bw_v low-f {v[nb:nb+4].mean():+.2f} high-f {v[2*nb-4:2*nb].mean():+.2f}')
# novelty: fraction of each group's rows whose nearest neighbour in another group (6-PC space) is farther than the median within-group NN distance
from scipy.spatial import cKDTree
print('== 2. does each engine group reach response regions the others do not? (6-PC space, among rows with J<12 = acoustically sane)')
sane=np.array([r['J']<12 for r in rows]); 
for g in ('OSSE','GRID','GEN-FF'):
    m=np.array([grp(r)==g for r in rows])&sane; o=(~np.array([grp(r)==g for r in rows]))&sane
    if m.sum()<5: print('  ',g,'too few sane rows',m.sum()); continue
    d_in=cKDTree(Z[m]).query(Z[m],k=2)[0][:,1]; d_out=cKDTree(Z[o]).query(Z[m],k=1)[0]
    print(f'   {g:7s} sane n={m.sum():4d}  median NN dist within {np.median(d_in):.1f}  to other groups {np.median(d_out):.1f}  share of rows farther from others than 3x within-median: {np.mean(d_out>3*np.median(d_in))*100:.0f}%')
# per-config: achieved mid-band coverage spread = menu
print('== 3. achieved coverage menu among rows with J within 25% of the config best, top configs (H,V mean 1.1-5.5k)')
mid=(f>=1100)&(f<=5500)
bycfg=collections.defaultdict(list)
for r in rows: bycfg[(r['config'],r['brief'])].append(r)
allpts=[]
for (c,b),rs in sorted(bycfg.items(),key=lambda kv:min(x['J'] for x in kv[1]))[:10]:
    jb=min(x['J'] for x in rs); el=[x for x in rs if x['J']<=1.25*jb]
    H=[np.mean(np.array(x['bwh'])[mid]) for x in el]; V=[np.mean(np.array(x['bwv'])[mid]) for x in el]
    allpts+=list(zip(H,V))
    print(f'   {c[:36]:36s} {b:6s} best {jb:5.2f} elites {len(el):3d}  H {min(H):.0f}-{max(H):.0f}  V {min(V):.0f}-{max(V):.0f}')
P=np.array(allpts); print('   union of elites: H %.0f-%.0f, V %.0f-%.0f ; cells occupied on a 5-deg grid: %d'%(P[:,0].min(),P[:,0].max(),P[:,1].min(),P[:,1].max(),len({(int(a//5),int(b//5)) for a,b in P})))
