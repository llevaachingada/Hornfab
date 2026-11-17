"""Could a geometry-only surrogate trained on OTHER lanes have ranked a lane before any solve in it?
Also: learning curve with/without transferred prior inside a held-out lane. Read-only."""
import numpy as np, warnings, pickle, collections
warnings.filterwarnings('ignore')
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr
d=np.load('scratch/fable_architecture/.fable/desc.npz',allow_pickle=True); X,Y,G=d['X'],d['Y'],d['G']
rows=[r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok'] and r['f'] and len(r['f'])==18]
f=np.array(rows[0]['f']); nf=len(f); band=np.where(f>=700)[0]
cov=lambda M: np.mean(np.where(M[:,band]<80,2,1)*(M[:,band]-80)**2,1)/100+0.5*np.mean(np.where(M[:,nf+band]<50,2,1)*(M[:,nf+band]-50)**2,1)/100
ct=cov(Y); lanes=sorted(set(G)); pm=[];tm=[];pb=[];tb=[]
for g in lanes:
    te=G==g; m=ExtraTreesRegressor(200,min_samples_leaf=2,random_state=0,n_jobs=6).fit(X[~te],Y[~te]); cp=cov(m.predict(X[te]))
    pm.append(np.median(cp)); tm.append(np.median(ct[te])); pb.append(np.percentile(cp,10)); tb.append(np.percentile(ct[te],10))
print('lanes',len(lanes))
print('predicted vs true lane-median coverage error, lane never seen: spearman %.2f'%spearmanr(pm,tm)[0])
print('predicted vs true lane best-decile coverage error: spearman %.2f'%spearmanr(pb,tb)[0])
o=np.argsort(tb); print('true top-8 lanes by best-decile coverage:',[lanes[i][:24] for i in o[:8]]); o2=np.argsort(pb); print('predicted top-8:',[lanes[i][:24] for i in o2[:8]]); print('overlap top-8:',len(set(o[:8])&set(o2[:8])))
# learning curves inside a held-out lane: n local rows only vs n local rows + prior from other lanes (prior prediction as extra feature)
print('== learning curve inside held-out lanes (>=60 designs): rank corr of predicted vs true coverage error on the rest of the lane')
res=collections.defaultdict(list); rng=np.random.default_rng(0)
for g in lanes:
    te=np.where(G==g)[0]
    if len(te)<60: continue
    prior=ExtraTreesRegressor(200,min_samples_leaf=2,random_state=0,n_jobs=6).fit(X[G!=g],Y[G!=g])
    pp=cov(prior.predict(X[te]))
    for rep in range(5):
        idx=rng.permutation(len(te))
        for n in (0,8,16,32):
            tr=idx[:n]; ho=idx[32:]
            if n==0: res[(n,'prior')].append(spearmanr(pp[ho],ct[te][ho])[0]); continue
            loc=ExtraTreesRegressor(100,min_samples_leaf=1,random_state=0).fit(X[te][tr],ct[te][tr]); res[(n,'local')].append(spearmanr(loc.predict(X[te][ho]),ct[te][ho])[0])
            Xa=np.column_stack([X[te],pp]); both=ExtraTreesRegressor(100,min_samples_leaf=1,random_state=0).fit(Xa[tr],ct[te][tr]); res[(n,'local+prior')].append(spearmanr(both.predict(Xa[ho]),ct[te][ho])[0])
for k in sorted(res): print(f'   n_local={k[0]:2d} {k[1]:12s} median rank corr {np.nanmedian(res[k]):.2f}')
