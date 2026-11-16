"""Section-constrained ES-600 family study, not Crowe's original ES equation.

Independent raster-measured H/V meridians, intersecting swept walls, bounded
transverse crown, and reconstructed rear body. Uses the existing HornLab mesher.
"""
from functools import lru_cache
import math
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
import yaml
from ._rolled_rect_v1 import smoothstep

SCHEMA = 'crowe-section-study-v2'
REFERENCE = Path(__file__).resolve().parent/'data/crowe_section_reference_v1.yaml'
SHAPE_KEYS = frozenset({'width_mm','height_mm','depth_mm','h_depth_scale','crown_mm','junction_power','throat_blend_mm','wall_thickness_mm','n_phi','n_s'})

@lru_cache(maxsize=1)
def reference():
    return yaml.safe_load(REFERENCE.read_text(encoding='utf-8'))

def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f'section shape keys: missing={sorted(SHAPE_KEYS-set(shape))}, unknown={sorted(set(shape)-SHAPE_KEYS)}')
    for k,v in shape.items():
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
            raise ValueError(f'{k} must be finite')
    if not shape['width_mm'] > shape['height_mm'] > 0 or shape['depth_mm'] <= 0:
        raise ValueError('need positive landscape dimensions')
    if not .9 <= shape['h_depth_scale'] <= 1.1:
        raise ValueError('h_depth_scale must be in [0.9,1.1]')
    if not 0 <= shape['crown_mm'] < .2*shape['height_mm']:
        raise ValueError('crown must be nonnegative and below 20 percent of height')
    if not 16 <= shape['junction_power'] <= 48:
        raise ValueError('junction_power must be in [16,48]')
    if not 0 < shape['throat_blend_mm'] < .2*shape['depth_mm'] or shape['wall_thickness_mm'] <= 0:
        raise ValueError('need a short positive throat blend and positive wall thickness')
    for k,m in [('n_phi',25),('n_s',48)]:
        if int(shape[k]) != shape[k] or shape[k] < m:
            raise ValueError(f'{k} must be an integer >= {m}')

def _profile(key,radial_scale,depth_scale,r0):
    ref=reference(); pts=np.array(ref[key],float)
    pts[:,0]=r0+(pts[:,0]-ref['reference_throat_radius_mm'])*radial_scale
    pts[:,1]*=depth_scale
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    return PchipInterpolator(arc/arc[-1],pts,axis=0)(np.linspace(0,1,8193))

def section_profiles(shape,driver):
    """Return dense (H,V) arrays [radius,z], before the driver throat blend."""
    validate_shape(shape); ref=reference()
    r0=float(driver['exit_radius_mm']); a0=float(driver['exit_angle_deg'])
    if not 0 < r0 < shape['height_mm']/2 or not 0 < a0 < 45:
        raise ValueError('need a round throat and exit angle in (0,45)')
    rr=ref['reference_throat_radius_mm']; zs=shape['depth_mm']/ref['reference_depth_mm']
    h=_profile('horizontal_mm',(shape['width_mm']/2-r0)/(ref['reference_width_mm']/2-rr),zs*shape['h_depth_scale'],r0)
    v=_profile('vertical_mm',(shape['height_mm']/2-r0)/(ref['reference_height_mm']/2-rr),zs,r0)
    return h,v

def _sweep(shape,driver):
    h,v=section_profiles(shape,driver); xh,zh=h.T; dv=float(v[:,1].max())
    if np.any(zh>=dv): raise ValueError('H section must remain behind V forward extremum')
    pivot=float(np.max((xh*xh+zh*zh-dv*dv)/(2*(dv-zh))))
    if pivot<=0: raise ValueError('nonpositive sweep pivot')
    rh=np.hypot(xh,zh+pivot); peak=int(np.argmax(rh))
    if np.any(np.diff(rh[:peak+1])<=0) or np.any(np.diff(rh[peak:])>=0):
        raise ValueError('H sweep radius is not single-peaked')
    # Source top continues flat to the rear; extend only far enough to meet
    # the measured H roll end, rather than inventing a tail for that section.
    tail_z=float(rh[-1]-pivot)
    if not 0<tail_z<v[-1,1]: raise ValueError('incompatible profile return extents')
    tail=np.column_stack((np.full(513,v[-1,0]),np.linspace(v[-1,1],tail_z,513)))
    v=np.concatenate((v,tail[1:]))
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(v,axis=0),axis=1))]; station=arc/arc[-1]
    target=v[:,1]+pivot; peak_v=int(np.argmax(target))
    if target[peak_v]>rh[peak]+1e-8 or target[-1]<rh[-1]-1e-8:
        raise ValueError('section radii do not share a return domain')
    up=PchipInterpolator(rh[:peak+1],h[:peak+1],axis=0,extrapolate=False)
    down=PchipInterpolator(rh[peak:][::-1],h[peak:][::-1],axis=0,extrapolate=False)
    real_start=rh[0]-pivot
    if real_start>=shape['throat_blend_mm']:
        raise ValueError('throat blend ends before the sweep inverse exists')
    # The held initial joint is never exposed: its participation is exactly zero
    # until a real intersection exists. No extrapolated/imaginary surface is used.
    # Each inverse has its own real domain. The constructed tail can round a
    # few ulps below rh[-1] after subtracting/adding the pivot; clamp to that
    # branch endpoint after the explicit physical-domain guard above. Using
    # the ascending lower bound for both branches produced rare NaN endpoints.
    forward=np.clip(target[:peak_v+1],rh[0],rh[peak])
    returning=np.clip(target[peak_v+1:],rh[-1],rh[peak])
    joint=np.concatenate((up(forward),down(returning)))
    crown=shape['crown_mm']*smoothstep((v[:,0]-driver['exit_radius_mm'])/(shape['height_mm']/2-driver['exit_radius_mm']))
    return station,v,joint,pivot,crown,real_start

def _evaluate(shape,driver,stations,phis,sweep):
    ds,v,joint,pivot,crown,real_start=sweep; s=np.asarray(stations,float)
    if s.ndim!=1 or np.any((s<0)|(s>1)): raise ValueError('stations must lie in [0,1]')
    vv=PchipInterpolator(ds,v,axis=0)(s); jj=PchipInterpolator(ds,joint,axis=0)(s)
    d=np.interp(s,ds,crown); xc,zc=jj.T; yv,zv=vv.T
    phi=np.asarray(phis,float).reshape(-1,1); cs,sn=np.cos(phi),np.sin(phi)
    # Positive quadratic root for crowned top y=yV-d*(x/xc)^2.
    denom=sn+np.sqrt(sn*sn+4*d*yv*cs*cs/(xc*xc))
    rt=np.divide(2*yv,denom,out=np.full_like(denom,np.inf),where=denom>0)
    rs=xc/np.maximum(cs,1e-15)
    power=shape['junction_power']
    small=np.minimum(rt,rs)
    rho=small*((small/rs)**power+(small/rt)**power)**(-1/power)
    x=rho*cs
    radicand=(zv+pivot)**2-x*x
    if np.min(radicand)<-1e-6: raise ValueError('non-real swept panel')
    # A narrow rounded join about the exact section-derived intersection.
    # Its radial and axial participation use the same partition of unity.
    wh=(rho/rs)**power
    zz=wh*zc+(1-wh)*(np.sqrt(np.maximum(0,radicand))-pivot)
    w=smoothstep((zv-real_start)/(shape['throat_blend_mm']-real_start))
    rr=float(driver['exit_radius_mm'])+math.tan(math.radians(driver['exit_angle_deg']))*zv
    rho=(1-w)*rr+w*rho; z=(1-w)*zv+w*zz
    pts=np.stack((rho*cs,rho*sn,z),axis=-1)
    pts[np.isclose(phi[:,0],0),:,1]=0; pts[np.isclose(phi[:,0],math.pi/2),:,0]=0
    return pts

def surface_at(shape,driver,stations,phis):
    return _evaluate(shape,driver,stations,phis,_sweep(shape,driver))

def make_grid(shape,brief):
    sweep=_sweep(shape,brief['driver']); ds=np.linspace(0,1,8193)
    centre=_evaluate(shape,brief['driver'],ds,[math.pi/4],sweep)[0]
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centre,axis=0),axis=1))]
    s=np.interp(np.linspace(0,arc[-1],int(shape['n_s'])+1),arc,ds)
    pts=_evaluate(shape,brief['driver'],s,np.linspace(0,math.pi/2,int(shape['n_phi'])),sweep)
    if not np.isfinite(pts).all(): raise ValueError('nonfinite section surface')
    _,v,joint,pivot,crown,_=sweep
    meta={'quarter':True,'row_span':'quarter','symmetry_plane':'yz+xz',
          'source_auto_angle_deg':float(brief['driver']['exit_angle_deg']),
          'construction_label':SCHEMA,'shape':dict(shape),'stations':s.tolist(),
          'sweep_pivot_mm':pivot,'junction':{'x':joint[:,0].tolist(),
          'y':(v[:,0]-crown).tolist(),'z':joint[:,1].tolist()}}
    return pts,meta

def outer_points(inner,shape):
    """Flat rear and rectangular outer body; fillets are inferred, not recovered CAD.

    This explicit solid body is both rendered and solved; no cosmetic mesh is used.
    """
    t=shape['wall_thickness_mm']; phi=np.arctan2(inner[:,0,1],inner[:,0,0])[:,None]
    cs,sn=np.cos(phi),np.sin(phi); r0=np.hypot(inner[:,0,0],inner[:,0,1])[:,None]+t
    from hornlab_search.design.generators.grid import grid_outer_points
    offset=grid_outer_points(inner,t,check=False)
    # Flat rear annulus, a wall-scaled quarter-circle corner and a straight
    # exterior meridian. Arc sampling avoids a zero-tangent hairpin at the rear.
    bend=4*t
    end_r=np.hypot(offset[:,-1,0],offset[:,-1,1])[:,None]
    end_z=offset[:,-1,2:3]
    straight_r=end_r-r0-bend
    straight_z=end_z-bend
    if np.any(straight_r<=0) or np.any(straight_z<=0):
        raise ValueError('rear body too small for its corner radius')
    arc=np.linspace(0,1,inner.shape[1])[None,:]*(straight_r+math.pi*bend/2+straight_z)
    theta=np.clip((arc-straight_r)/bend,0,math.pi/2)
    rho=np.where(arc<straight_r,r0+arc,end_r-bend+bend*np.sin(theta))
    z=bend*(1-np.cos(theta))+np.maximum(arc-straight_r-math.pi*bend/2,0)
    outer=np.stack((rho*cs,rho*sn,z),axis=-1)
    outer[0,:,1]=0; outer[-1,:,0]=0
    return outer
