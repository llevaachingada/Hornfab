import json, pickle, pathlib, collections
import numpy as np
from scipy.interpolate import interp1d
from scipy.spatial import cKDTree
from hornlab_search.config import load_config
from hornlab_search.types import Design
from hornlab_search.bo.data import materialize_geometry
from hornlab_search.design.generators import grid, rolled_family, klangfilm_lame_family

names=['hl__ext_throat_hvlaw_v7','hl__ath_tritonia_landscape_v9','hl__crowe_x_osse_cd_v7','rf__section_axial_home_v7','hl__klangfilm_lame_curved_v1','hl__biradial_es_style_v7']
rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'))
def sample(points,nphi,ns):
    # Parameterize each original meridian by its own normalized arc length.
    a=np.asarray(points); t=np.linspace(0,1,ns); b=[]
    for mer in a:
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(mer,axis=0),axis=1))]
        if arc[-1] <= 0: raise ValueError('zero-length meridian')
        arc=arc/arc[-1]; keep=np.r_[True,np.diff(arc)>1e-12]
        b.append(np.stack([np.interp(t,arc[keep],mer[keep,k]) for k in range(3)],axis=-1))
    b=np.array(b)
    # Polar angles need not be uniformly spaced, notably on morphed sections.
    result=np.empty((nphi,ns,3))
    for j in range(ns):
        ph=np.unwrap(np.arctan2(b[:,j,1],b[:,j,0]))
        if np.any(np.diff(ph)<-1e-8): raise ValueError('nonmonotone azimuth; no safe interpolation')
        phi=np.linspace(ph[0],ph[-1],nphi)
        for k in range(3): result[:,j,k]=np.interp(phi,ph,b[:,j,k])
    return result
all_surfaces=[]; all_names=[]
for name in names:
    chosen=[]; seen=set()
    for r in rows:
        if r['config']==name and r['ok'] and r['h'] not in seen:
            p=pathlib.Path('runs')/r['run']/'designs'/r['h']/'design.json'
            if p.exists(): chosen.append((r,p)); seen.add(r['h'])
        if len(chosen)==10: break
    print('\n',name,'selected',len(chosen),flush=True)
    for r,p in chosen:
        try:
            recipe=json.load(open(p)); config=load_config(pathlib.Path('runs')/r['run']/'config.yaml')
            design=Design(recipe['family'],recipe['params']); block=recipe['params'].get('grid')
            if block and klangfilm_lame_family.is_family_spec(block):
                a=klangfilm_lame_family.resolve_grid(block,config.brief); points=a['inner_points']; mode='klangfilm'
            elif block and rolled_family.is_family_spec(block):
                a=rolled_family.resolve_grid(block,config.brief); points=a['inner_points']; mode='rolled'
            elif block:
                points,meta=grid.grid_points(block,block.get('knobs',{}),config.brief); mode='grid'
            else:
                a=materialize_geometry(design,config,resolution_mm=10); points=a['inner_points']; mode=a['formula']
            coarse=sample(points,31,65); fine=sample(points,61,129)
            repeat=sample(points,31,65)
            delta=np.max(np.linalg.norm(coarse-fine[::2,::2],axis=2))
            arcs=np.cumsum(np.linalg.norm(np.diff(coarse,axis=1),axis=2),axis=1)
            np.savez_compressed('scratch/fable_architecture/.x1/'+r['h']+'.npz',inner=coarse,arc_length_mm=np.column_stack([np.zeros(31),arcs]),design_hash=r['h'],lane=name,mode=mode,run=r['run'])
            all_surfaces.append(coarse); all_names.append(name)
            refine='fixed-recipe'
            if not block:
                finer=materialize_geometry(design,config,resolution_mm=5)['inner_points']
                repeat_raw=materialize_geometry(design,config,resolution_mm=10)['inner_points']
                refine=round(float(np.max(np.linalg.norm(coarse-sample(finer,31,65),axis=2))),4)
                deterministic=np.array_equal(points,repeat_raw)
            else: deterministic='not retested resolver'
            mesh=pathlib.Path('runs')/r['run']/'designs'/r['h']/'mesh.msh'
            md='unavailable'
            if mesh.exists():
                txt=mesh.read_text(); a0=txt.index('$Nodes')+7; a1=txt.index('$EndNodes'); ln=txt[a0:a1].split('\n',1)
                nd=np.array(ln[1].split(),float).reshape(-1,4)[:,1:]*1000
                b0=txt.index('$Elements')+10; b1=txt.index('$EndElements'); wall=set()
                for line in txt[b0:b1].split('\n')[1:]:
                    z=line.split()
                    if len(z)>=8 and z[1]=='2' and z[3]=='1': wall.update((int(z[-3])-1,int(z[-2])-1,int(z[-1])-1))
                if wall:
                    ds=cKDTree(fine.reshape(-1,3)).query(nd[sorted(wall)],workers=1)[0]; md=[round(float(t),3) for t in np.quantile(ds,[.5,.99])]
            print(r['h'],mode,np.asarray(points).shape,'resampling_delta_mm',round(delta,6),'resolver_refine_max_mm',refine,'resolver_deterministic',deterministic,'tag1_node_to_grid_upper_mm_median_p99',md,flush=True)
        except Exception as e: print(r['h'],'FAILED',type(e).__name__,str(e)[:220],flush=True)
if all_surfaces:
    z=np.array(all_surfaces); names=np.array(all_names); flat=z.reshape(len(z),-1); mu=flat.mean(0)
    U,S,V=np.linalg.svd(flat-mu,full_matrices=False)
    for k in (8,12,16):
        rec=(U[:,:k]*S[:k])@V[:k]+mu
        err=np.sqrt(np.mean(np.sum((rec-flat).reshape(z.shape)**2,axis=-1),axis=(1,2)))
        for n in sorted(set(names)):
            e=err[names==n]; print('PCA',k,n,'median_mm',round(float(np.median(e)),4),'worst_mm',round(float(e.max()),4),flush=True)
