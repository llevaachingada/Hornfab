import json,pathlib,pickle
import numpy as np
from hornlab_search.config import load_config
from hornlab_search.types import Design
from hornlab_search.bo.data import materialize_geometry
from hornlab_search.design.generated import materialize
from hornlab_search.design.generators.grid import grid_points
root=pathlib.Path('scratch/fable_architecture'); data,_=pickle.load(open(root/'.e1/descriptors.pkl','rb')); names=['hl__ext_throat_hvlaw_v7','hl__rosse_rect_cd_v7','hl__biradial_es_style_v7']; out={}
def resample(grid):
    # Correspondence in normalized meridian arc and azimuth index, not a canonical
    # whole-surface identity; reparameterization itself affects this estimate.
    t=np.linspace(0,1,80); first=[]
    for row in grid:
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(row,axis=0),axis=1))]; arc/=arc[-1]
        first.append(np.stack([np.interp(t,arc,row[:,j]) for j in range(3)],axis=1))
    first=np.array(first); u=np.linspace(0,1,len(first)); v=np.linspace(0,1,33)
    return np.stack([np.stack([np.interp(v,u,first[:,j,k]) for k in range(3)],axis=1) for j in range(80)],axis=1)
for name in names:
    r=min([v[0] for v in data if v[0]['config']==name],key=lambda q:q['J']); cfg=load_config(pathlib.Path('runs')/r['run']/'config.yaml')
    def surface(knobs):
        if r['gen']=='grid': return resample(grid_points(cfg.generator,knobs,cfg.brief)[0])
        params=materialize(cfg.generator,knobs,cfg.brief) if r['gen']=='typology' else knobs
        return resample(materialize_geometry(Design(r['engine'],params),cfg)['inner_points'])
    source=r['knobs'] if r['gen'] else r['params']
    try: base=surface(source)
    except Exception as e:
        out[name]={'error':repr(e)}; print(name,'unsupported:',repr(e),flush=True); continue
    reference=resample(materialize_geometry(Design(r['engine'],r['params']),cfg)['inner_points']) if r['gen']!='grid' else None
    roundtrip=float(np.max(np.linalg.norm(base-reference,axis=2))) if reference is not None else None
    print(name,'shape',base.shape,'bbox',np.ptp(base,axis=(0,1)),'roundtrip_max_mm',roundtrip,flush=True)
    aa=np.gradient(base,axis=0); bb=np.gradient(base,axis=1); normal=np.cross(aa,bb); mag=np.linalg.norm(normal,axis=2); normal=normal/np.maximum(mag[...,None],1e-12)
    radial=np.dstack([base[:,:,0],base[:,:,1],np.zeros(base.shape[:2])]); dot=np.sum(normal*radial,axis=2); normal*=np.where(dot<0,-1,1)[...,None]
    dist=np.linalg.norm(np.diff(base,axis=1),axis=2); arc=np.concatenate([np.zeros((len(base),1)),np.cumsum(dist,axis=1)],axis=1); s=arc/np.maximum(arc[:,-1:],1e-9); phi=np.arctan2(base[:,:,1],base[:,:,0]); outer=np.where(s>.5,np.sin(np.pi*(s-.5))**2,0); inner=np.where(s<.5,np.sin(2*np.pi*s)**2,0); mouth=np.where(s>.85,np.sin(np.pi*(s-.85)/.30)**2,0)
    weights={'vertical_outer':-np.sin(phi)**2*outer,'vertical_inner':-np.sin(phi)**2*inner,'horizontal_outer':np.cos(phi)**2*outer,'mouth_flare':mouth,'diagonal_pull':np.sin(2*phi)**2*outer}
    fields={k:(normal*v[...,None]).reshape(-1) for k,v in weights.items()}; columns=[]; keys=[]; errors={}
    for k,b in r['bounds'].items():
        if not isinstance(b,dict) or not b.get('search',True) or k not in source: continue
        lo=b.get('lo'); hi=b.get('hi'); value=source[k]
        if not all(isinstance(x,(int,float)) for x in (lo,hi,value)) or hi<=lo: continue
        step=.01*(hi-lo); a=max(lo,value-step); z=min(hi,value+step)
        if z<=a: continue
        try:
            pp=dict(source); pm=dict(source); pp[k]=z; pm[k]=a
            up=surface(pp); down=surface(pm)
            if up.shape!=base.shape or down.shape!=base.shape: raise ValueError('grid dimensions changed')
            col=((up-down)/(z-a)).reshape(-1)
            if np.linalg.norm(col)>1e-10: columns.append(col/np.linalg.norm(col)); keys.append(k)
            else: errors[k]='zero motion'
        except Exception as e: errors[k]=repr(e)
    if not columns:
        out[name]={'error':'No searchable knobs are directly represented in stored design parameters; needs generator adapter','shape':base.shape,'knob_errors':errors}; print(name,out[name],flush=True); continue
    J=np.array(columns).T; u,singular,vt=np.linalg.svd(J,full_matrices=False); rank=int(np.sum(singular>singular[0]*1e-8)); U=u[:,:rank]
    unexplained={k:float(np.linalg.norm(v-U@(U.T@v))/np.linalg.norm(v)) for k,v in fields.items()}
    out[name]={'shape':base.shape,'roundtrip_max_mm':roundtrip,'searched_knobs_used':keys,'knob_errors':errors,'rank':rank,'relative_unexplained_norm':unexplained,'singular_values':singular.tolist(),'normal_degenerate_points':int(sum(mag.ravel()<1e-12))}; print('result',out[name],flush=True)
(root/'.x2/jacobian.json').write_text(json.dumps(out,indent=2))
