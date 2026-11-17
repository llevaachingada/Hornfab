import json,pathlib,pickle
import numpy as np
from scipy.spatial import cKDTree
from sklearn.ensemble import ExtraTreesRegressor

root=pathlib.Path('scratch/fable_architecture'); data,failures=pickle.load(open(root/'.e1/descriptors.pkl','rb'))
rows=[r for r,x,y in data]; X=np.array([x for r,x,y in data]); Y=np.array([y for r,x,y in data]); G=np.array([r['config'] for r in rows]); E=np.array(['OSSE' if not r['gen'] else ('GRID' if r['gen']=='grid' else 'GEN-FF') for r in rows]); f=np.array(rows[0]['f']); bands=[(700,1100),(1100,2500),(2500,5500)]
bases=['hl__ext_throat_hvlaw_v7','hl__rosse_rect_cd_v7','hl__biradial_es_style_v7']; s=(np.arange(12)+.5)/12
# Smooth radial meridian offsets in mm per unit module weight. Outer is C1 at its
# midpoint and mouth; inner is zero at throat and midpoint. Non-meridian geometry
# cannot be recovered from these descriptors, so diagonal and lip are not fabricated.
outer=np.where(s>.5,np.sin(np.pi*(s-.5))**2,0); inner=np.where(s<.5,np.sin(2*np.pi*s)**2,0); mouth=np.where(s>.85,np.sin(np.pi*(s-.85)/.30)**2,0)
fields={'vertical_outer':(np.zeros(12),-outer),'vertical_inner':(np.zeros(12),-inner),'horizontal_outer':(outer,np.zeros(12)),'mouth_flare':(mouth,mouth)}
def deform(base,field,w,fixed_bbox=False):
    h,v=fields[field]; z=base.copy(); dh=w*h; dv=w*v
    z[3:15]+=dh; z[15:27]+=dv
    # Bounding entries use endpoint displacement as an approximation; true maxima
    # need the full surface. This is explicitly not an envelope check.
    z[1]+=dh[-1]; z[2]+=dv[-1]
    if fixed_bbox:
        z[3:15]*=base[1]/z[1]; z[15:27]*=base[2]/z[2]; z[1:3]=base[1:3]
    return z
def means(pred):
    return [[float(np.mean(pred[k*18+np.flatnonzero((f>=lo)&(f<hi))])) for lo,hi in bands] for k in range(2)]
out={'frequencies':f.tolist(),'bands':bands,'basis':{k:[a.tolist(),b.tolist()] for k,(a,b) in fields.items()},'bases':{}}
for name in bases:
    ix=[i for i in np.flatnonzero(G==name) if rows[i]['ok']]; i=min(ix,key=lambda j:rows[j]['J']); x=X[i]; engine=E[i]; tr=E!=engine; scale=np.std(X[tr],axis=0); scale[scale<1e-9]=1; mu=np.mean(X[tr],axis=0); xt=(X[tr]-mu)/scale; unique=np.unique(xt,axis=0); tree=cKDTree(unique); d=tree.query(unique,k=2)[0][:,1]; lim=float(np.quantile(d,.95)); model=ExtraTreesRegressor(n_estimators=100,min_samples_leaf=2,random_state=0,n_jobs=2).fit(X[tr],Y[tr]); p0=model.predict(x[None])[0]
    result={'run':rows[i]['run'],'hash':rows[i]['h'],'J':rows[i]['J'],'engine':engine,'train_n':int(sum(tr)),'distance95':lim,'base_distance':float(tree.query((x-mu)/scale)[0]),'predicted_baseline':means(p0),'modules':{}}
    for field in fields:
        result['modules'][field]={}
        for fixed in (False,True):
            mode='bbox_control' if fixed else 'raw'; entries={}
            for w in (-20,-10,-5,5,10,20):
                z=deform(x,field,w,fixed); pred=model.predict(z[None])[0]; delta=means(pred-p0); distance=float(tree.query((z-mu)/scale)[0]); entries[str(w)]={'delta_deg':delta,'distance':distance,'outside95':distance>lim,'profile_positive':bool(np.all(z[3:]>0))}
            result['modules'][field][mode]=entries
    out['bases'][name]=result; print(name,engine,'base distance',round(result['base_distance'],3),'threshold',round(lim,3),flush=True)
(root/'.x2/results.json').write_text(json.dumps(out,indent=2,allow_nan=False))
