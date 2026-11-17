import pickle,numpy as np,collections,json,pathlib,re
from sklearn.ensemble import ExtraTreesRegressor
D=np.load('scratch/fable_architecture/.fable/desc.npz'); data,_=pickle.load(open('scratch/fable_architecture/.e1/descriptors.pkl','rb'));mp=collections.defaultdict(list)
for r,x,y in data:mp[(r['config'],x.tobytes(),y.tobytes())].append(r)
X=[];Y=[];G=[];E=[]; ids=[];bad=collections.Counter()
for g,x,y in zip(D['G'],D['X'],D['Y']):
 matches=mp[(g,x.tobytes(),y.tobytes())];assert len(set(r['h'] for r in matches))==1;r=matches[0]
 try:
  m=json.loads((pathlib.Path('runs')/r['run']/'designs'/r['h']/'metrics.json').read_text()); z=np.array([m[k] for k in ('z_throat_real','ripple_h_db','ripple_v_db','on_axis_db')],float).ravel()
  if len(z)!=72 or not np.isfinite(z).all():raise ValueError('missing/nonfinite target')
  assert np.allclose(m['freqs_hz'],r['f']);X.append(x);Y.append(np.r_[y,z]);G.append(g);E.append('OSSE' if r['gen']=='' else 'GRID' if r['gen']=='grid' else 'GEN-FF');ids.append(r['h'])
 except Exception as ex:bad[str(ex)]+=1
X=np.array(X);Y=np.array(Y);G=np.array(G);E=np.array(E);np.savez('scratch/fable_architecture/.x3/extended.npz',X=X,Y=Y,G=G,E=E,ids=ids);print('count',len(X),'excluded',dict(bad),'duplicates',len(ids)-len(set(ids)),flush=True)
def sibling(g):
 g=re.sub(r'_v\d+$','',g).replace('_smooth','')
 if g.startswith('sp__'):return 'sp__control_moderate_strong'
 if g.startswith('rr__pucker') or g=='rr__reference':return 'rr__reference_pucker'
 if g.startswith('klangfilm_hv__a'):return 'klangfilm_hv__axis_variants'
 return g
S=np.array([sibling(g) for g in G]);f=np.array(next(r['f'] for r,x,y in data if r['ok']));band=np.where(f>=600)[0]
# Design identity may appear in two groups. Remove identical hashes from every training fold.
for feat in ['size','profile']:
 xx=X[:,:3] if feat=='size' else X
 for scheme,groups in [('lane',G),('sibling',S),('engine',E)]:
  P=np.zeros_like(Y);B=np.zeros_like(Y)
  for group in sorted(set(groups)):
   te=groups==group;tr=(~te)&(~np.isin(ids,np.array(ids)[te])); pred=ExtraTreesRegressor(n_estimators=60,min_samples_leaf=2,random_state=0,n_jobs=4).fit(xx[tr],Y[tr]).predict(xx[te]);P[te]=pred;B[te]=Y[tr].mean(axis=0)
   if scheme=='engine':print('ENGINE',feat,group,*[round(1-np.sum((Y[te][:,i*18+band]-P[te][:,i*18+band])**2)/np.sum((Y[te][:,i*18+band]-B[te][:,i*18+band])**2),3) for i in range(7)],flush=True)
  print('POOLED',feat,scheme,*[round(1-np.sum((Y[:,i*18+band]-P[:,i*18+band])**2)/np.sum((Y[:,i*18+band]-B[:,i*18+band])**2),3) for i in range(7)],flush=True)
