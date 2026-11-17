import numpy as np,pickle,re,collections,json
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr
D=np.load('scratch/fable_architecture/.fable/desc.npz',allow_pickle=True); X,Y,G=D['X'],D['Y'],D['G']; rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'))
eng={}
for r in rows:
 if r['config'] in G:
  e='OSSE' if r['gen']=='' else ('GRID' if r['gen']=='grid' else 'GEN-FF')
  eng.setdefault(r['config'],set()).add(e)
assert all(len(x)==1 for x in eng.values()); E=np.array([next(iter(eng[g])) for g in G]); f=np.array(next(r['f'] for r in rows if r['ok'] and r['f'] and len(r['f'])==18)); band=np.where(f>=600)[0]
def sibling(g):
 g=re.sub(r'_v\d+$','',g).replace('_smooth','')
 if g.startswith('sp__'): return 'sp__control_moderate_strong'
 if g.startswith('rr__pucker') or g=='rr__reference': return 'rr__reference_pucker'
 if g.startswith('klangfilm_hv__a'): return 'klangfilm_hv__axis_variants'
 return g
S=np.array([sibling(g) for g in G]); print('SIBLINGS',json.dumps({s:sorted(set(G[S==s])) for s in sorted(set(S))},indent=2)); print('engine',collections.Counter(E))
def model(): return ExtraTreesRegressor(n_estimators=100,min_samples_leaf=2,random_state=0,n_jobs=4)
def cov(y):
 a=y[:,band]; b=y[:,18+band];return np.mean(np.where(a<80,2,1)*(a-80)**2,axis=1)/100+.5*np.mean(np.where(b<50,2,1)*(b-50)**2,axis=1)/100
for feature in ('size','profile'):
 x=X[:,:3] if feature=='size' else X
 for scheme,groups in [('lane',G),('sibling',S),('engine',E)]:
  P=np.zeros_like(Y); B=np.zeros_like(Y)
  for group in sorted(set(groups)):
   te=groups==group; tr=~te; P[te]=model().fit(x[tr],Y[tr]).predict(x[te]); B[te]=Y[tr].mean(axis=0)
   if scheme=='engine':
    print('RESULT',feature,scheme,group,'n',te.sum(),*[round(1-np.sum((Y[te][:,k*18+band]-P[te][:,k*18+band])**2)/np.sum((Y[te][:,k*18+band]-B[te][:,k*18+band])**2),4) for k in range(3)],flush=True)
  print('RESULT',feature,scheme,'pooled',*[round(1-np.sum((Y[:,k*18+band]-P[:,k*18+band])**2)/np.sum((Y[:,k*18+band]-B[:,k*18+band])**2),4) for k in range(3)],flush=True)
  rank=[spearmanr(cov(Y[G==g]),cov(P[G==g])).statistic for g in set(G) if sum(G==g)>=30]
  print('RANK',feature,scheme,len(rank),np.nanmedian(rank),flush=True)
# Residualize both train and test targets using size regression fit on training only; compare shape residual to zero.
from sklearn.linear_model import LinearRegression
for group in sorted(set(E)):
 te=E==group; tr=~te; size=LinearRegression().fit(X[tr,:3],Y[tr]); residual=Y-size.predict(X[:,:3]); pred=model().fit(X[tr,3:],residual[tr]).predict(X[te,3:]); print('RESIDUAL',group,*[round(1-np.sum((residual[te][:,k*18+band]-pred[:,k*18+band])**2)/np.sum(residual[te][:,k*18+band]**2),4) for k in range(3)],flush=True)
