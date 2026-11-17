import numpy as np,pickle,collections
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr
D=np.load('scratch/fable_architecture/.fable/desc.npz',allow_pickle=True); X,Y,G=D['X'],D['Y'],D['G']; rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')); f=np.array(next(r['f'] for r in rows if r['ok'] and r['f'] and len(r['f'])==18)); b=np.where(f>=700)[0]
def cov(y):
 a=y[:,b];v=y[:,18+b];return np.mean(np.where(a<80,2,1)*(a-80)**2,axis=1)/100+.5*np.mean(np.where(v<50,2,1)*(v-50)**2,axis=1)/100
eng={r['config']:('OSSE' if r['gen']=='' else 'GRID' if r['gen']=='grid' else 'GEN-FF') for r in rows if r['config'] in G}; E=np.array([eng[g] for g in G]); y=cov(Y)
def model(): return ExtraTreesRegressor(n_estimators=100,min_samples_leaf=2,random_state=0,n_jobs=4)
rng=np.random.default_rng(42)
for e in sorted(set(E)):
 loc=np.where(E==e)[0]; other=np.where(E!=e)[0]; prior=cov(model().fit(X[other],Y[other]).predict(X[loc])); out=collections.defaultdict(list)
 for rep in range(10):
  order=rng.permutation(len(loc)); test=order[64:]; out[(0,'prior')].append(spearmanr(y[loc[test]],prior[test]).statistic)
  for n in (8,16,32,64):
   train=order[:n]; yy=y[loc[train]]
   for method,xx in [('local',X[loc]),('plus',np.column_stack((X[loc],prior)))]:
    p=model().fit(xx[train],yy).predict(xx[test]);out[(n,method)].append(spearmanr(y[loc[test]],p).statistic)
 print(e,[(k,round(float(np.nanmedian(v)),3)) for k,v in sorted(out.items())],flush=True)
