import numpy as np,pickle
from sklearn.ensemble import ExtraTreesRegressor
D=np.load('scratch/fable_architecture/.x3/extended.npz');X,Y,E,ids=D['X'],D['Y'],D['E'],D['ids']; data,_=pickle.load(open('scratch/fable_architecture/.e1/descriptors.pkl','rb')); f=np.array(data[0][0]['f']);nf=len(f); band=np.where(f>=600)[0]
def pack(x,y,scale,indices):
 fs=f[indices]/scale; a=np.repeat(x[:,None,:]*scale,len(indices),axis=1); fq=np.broadcast_to(np.log(fs)[None,:,None],(len(x),len(indices),1)); Yc=np.stack([y[:,i*nf:(i+1)*nf][:,indices] for i in range(3)],axis=2)
 return np.concatenate((a,fq),axis=2).reshape(-1,28),Yc.reshape(-1,3)
for e in sorted(set(E)):
 te=E==e;tr=(~te)&(~np.isin(ids,ids[te])); xt,yt=pack(X[tr],Y[tr],1,np.arange(nf)); xe,ye=pack(X[te],Y[te],1,band);blocks=[(xt,yt)]
 for s in (.8,.9,1.1,1.25):blocks.append(pack(X[tr],Y[tr],s,np.where(f<=max(f)/2)[0]))
 for tag in ('base','augment'):
  a,b=(xt,yt) if tag=='base' else (np.concatenate([z[0] for z in blocks]),np.concatenate([z[1] for z in blocks]));m=ExtraTreesRegressor(n_estimators=40,min_samples_leaf=3,random_state=0,n_jobs=4,max_features=1.0).fit(a,b);p=m.predict(xe); base=Y[tr,:54].reshape(-1,3,nf)[:,:,band].mean(axis=0).T; base=np.tile(base,(int(te.sum()),1));score=[1-np.sum((ye[:,i]-p[:,i])**2)/np.sum((ye[:,i]-base[:,i])**2) for i in range(3)];print(e,tag,'train samples',len(a),'skills',np.round(score,4),flush=True)
