"""Read-only geometry sampling; one fresh process per seed. No mesh or solve."""
import json, sys, subprocess, hashlib, math, traceback
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generators import grid, rolled_family
from hornlab_search.design import families
from hornlab_mesher.config_builder import resolve_geometry
from hornlab_mesher.profile_formulas import profile_points

HOME=ROOT/'examples/typologies/home_landscape_2026-11-15'
RF=ROOT/'examples/typologies/rolled_family_2026-11-15'
FILES=[HOME/('hl__'+x+'_v7.yaml') for x in ('ext_throat_hvlaw','rosse_rect_cd','crowe_x_osse_cd','crowe_panel_home','rolled_es_spiral','biradial_es_style')] + [RF/('rf__'+x+'_v7.yaml') for x in ('rect_radial','section_radial','rect_axial','section_axial')]

def primary():
    cases=[{'type':'OSSE','L':135.,'r0':18.,'a0':4.2,'a':41.5,'s':.9,'n':3.7,'q':.995,'k':1.}, {'type':'OSSE','L':120.,'r0':12.7,'a0':7.5,'a':39.,'s':.7,'n':4.,'q':.99,'k':1.8}, {'type':'R-OSSE','R':130.,'r0':12.7,'a0':7.5,'a':39.,'k':1.8,'r':.3,'b':.3,'m':.8,'q':3.7}]
    results=[]
    for p in cases:
        pts=profile_points(p,1001,0.)
        u=np.linspace(0,1,1001)
        if p['type']=='OSSE':
            z=p['L']*u; a=np.deg2rad(p['a']);a0=np.deg2rad(p['a0']);r0=p['r0'];k=p['k']; L=p['L'];q=p['q']; n=p['n'];s=p['s']
            y=np.sqrt((k*r0)**2+2*k*r0*z*np.tan(a0)+z*z*np.tan(a)**2)+r0*(1-k)+s*L/q*(1-(1-(q*z/L)**n)**(1/n))
            ref=np.column_stack((z,y))
        else:
            R,r0,k,r,m,b,q=[p[x] for x in ('R','r0','k','r','m','b','q')]
            a,a0=np.deg2rad([p['a'],p['a0']]); c1=(k*r0)**2;c2=2*k*r0*np.tan(a0);c3=np.tan(a)**2
            L=(np.sqrt(c2*c2-4*c3*(c1-(R+r0*(k-1))**2))-c2)/(2*c3)
            x=L*(np.sqrt(r*r+m*m)-np.sqrt(r*r+(u-m)**2))+b*L*(np.sqrt(r*r+(1-m)**2)-np.sqrt(r*r+m*m))*u*u
            y=(1-u**q)*(np.sqrt(c1+c2*L*u+c3*L*L*u*u)+r0*(1-k))+u**q*(R+L*(1-np.sqrt(1+c3*(u-1)**2)))
            ref=np.column_stack((x,y))
        e=np.max(np.abs(pts-ref)); d=pts[1]-pts[0]
        v={'params':p,'max_abs_error_mm':float(e),'first':pts[0].tolist(),'last':pts[-1].tolist(),'max_x_mm':float(pts[:,0].max()),'secant_tangent_deg':float(np.degrees(np.arctan2(d[1],d[0])))}
        if p['type']=='R-OSSE': v['analytic_limit_tangent_deg']=float(np.rad2deg(np.arctan(np.tan(a0)*np.sqrt(r*r+m*m)/m)))
        results.append(v)
    return results

def load_points(path, factor):
    name=path.name
    if 'rosse_rect_cd' in name:
        from tools.geometry import rosse_rect_cli; rosse_rect_cli.install()
    elif 'crowe_panel_home' in name:
        from tools.geometry import crowe_panel_cli; crowe_panel_cli.install()
    elif 'rolled_es_spiral' in name:
        from tools.geometry import rolled_rect_cli; rolled_rect_cli.install()
    cfg=load_config(path); space=DesignSpace.from_config(cfg); d=space.seed
    if 'grid' in d.params:
        block=d.params['grid'].copy(); block['n_phi']=max(33,block['n_phi']);block['n_s']=2*(block['n_s']-1)+1 if factor==2 else block['n_s']
        # use multiples of 8 intervals so all requested meridians are samples
        block['n_phi']=8*math.ceil((block['n_phi']-1)/8)+1
        if rolled_family.is_family_spec(block): arr=rolled_family.resolve_grid(block,cfg.brief)['inner_points']
        else: arr,_=grid.rows_grid_points({k:v for k,v in block.items() if k!='knobs'},block['knobs'],cfg.brief)
        route='search grid resolver'
    else:
        ms=mesh_spec('screen',cfg); mc=families.to_mesher_config(d,ms,{'throat':5.,'mouth':10.,'rear':20.},Path('unused.msh'))
        mc['mesh']['angular_segments']=64;mc['mesh']['length_segments']=96 if factor==1 else 192
        resolved=resolve_geometry(mc);arr=np.asarray(resolved.geometry.inner_points);route='search-to-mesher config + resolve_geometry'
    return np.asarray(arr),route,d.params

def summarize(arr):
    a=np.asarray(arr); out=[]
    for idx,ang in zip(np.rint(np.linspace(0,len(a)-1,5)).astype(int),(0,22.5,45,67.5,90)):
        xyz=a[idx];r=np.hypot(xyz[:,0],xyz[:,1]);z=xyz[:,2]; dr=r[1]-r[0];dz=z[1]-z[0]
        s=np.r_[0,np.cumsum(np.hypot(np.diff(z),np.diff(r)))]; theta=np.unwrap(np.arctan2(np.gradient(r),np.gradient(z)));curv=np.gradient(theta,s)
        out.append({'phi_requested_deg':ang,'phi_sampled_deg':float(np.rad2deg(np.arctan2(a[idx,0,1],a[idx,0,0]))),'throat_r_mm':float(r[0]),'first_secant_deg':float(np.degrees(np.arctan2(dr,dz))),'dz_negative_intervals':int(np.sum(np.diff(z)<-1e-8)),'z_max_mm':float(max(z)), 'peak_abs_kappa_interior_per_mm':float(np.max(abs(curv[2:-2]))),'kappa_median_interior_per_mm':float(np.median(abs(curv[2:-2])))})
    # A ring here is indexed by common sampling station; only projected area is reliable.
    x,y=a[:,:,0],a[:,:,1]; q=2*np.abs(np.sum(x[:-1]*y[1:]-x[1:]*y[:-1],axis=0))
    return {'shape':list(a.shape),'meridians':out,'projected_xy_area_mm2':{'throat':float(q[0]),'mid_index':float(q[len(q)//2]),'last_index':float(q[-1])},'ring_z_spread_mm':{'throat':float(np.ptp(a[:,0,2])),'mid_index':float(np.ptp(a[:,a.shape[1]//2,2])),'last_index':float(np.ptp(a[:,-1,2]))}}

def one(path):
    try:
        a,route,params=load_points(path,1); b,_,_=load_points(path,2)
        result={'config':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'route':route,'nominal':summarize(a),'double_axial':summarize(b)}
        if path.parent == RF:
            cfg=load_config(path); space=DesignSpace.from_config(cfg); block=space.seed.params['grid'].copy(); block['n_phi']=a.shape[0]; block['knobs']=dict(block['knobs'])
            for key in ('g_inward_h_mm','g_inward_v_mm','g_axial_h_mm','g_axial_v_mm'): block['knobs'][key]=0.0
            base=rolled_family.resolve_grid(block,cfg.brief)['inner_points']; delta=a-base
            result['seed_relief_activity']={'max_abs_x_mm':float(np.max(abs(delta[:,:,0]))),'max_abs_y_mm':float(np.max(abs(delta[:,:,1]))),'max_abs_z_mm':float(np.max(abs(delta[:,:,2]))),'max_h_radial_mm':float(np.max(abs(delta[0,:,0]))),'max_v_radial_mm':float(np.max(abs(delta[-1,:,1]))),'max_h_axial_mm':float(np.max(abs(delta[0,:,2]))),'max_v_axial_mm':float(np.max(abs(delta[-1,:,2])))}
        return result
    except Exception as e:return {'config':str(path.relative_to(ROOT)),'error':repr(e),'traceback':traceback.format_exc()}
if __name__=='__main__':
    if len(sys.argv)>1: print(json.dumps(one(Path(sys.argv[1]))));sys.exit()
    paths=['hornlab_search/design/generators/grid.py','hornlab_search/design/generators/rolled_family.py','tools/geometry/rolled_rect.py','tools/geometry/crowe_panel.py','tools/geometry/rosse_rect.py','.venv/Lib/site-packages/hornlab_mesher/profile_formulas.py']
    out={'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'primary_equations':primary(),'seeds':[]}
    for path in FILES:
        proc=subprocess.run([sys.executable,__file__,str(path)],cwd=ROOT,capture_output=True,text=True,timeout=120)
        try: r=json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception: r={'config':str(path.relative_to(ROOT)),'process_error':proc.stderr[-3000:]}
        out['seeds'].append(r)
        print(path.name, 'error' if 'error' in r or 'process_error' in r else 'ok',flush=True)
    Path(__file__).with_name('geometry_controls.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')





