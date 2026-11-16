#!/usr/bin/env python3
"""HornFab HF1440 dual-family geometry gallery, intended for use IN Hornfab repo.
J seeds: existing `grid.rows.type: iwata_ar` and native generator.
K seeds: explicit research PREVIEWS, not production BEM-ready geometries.
Requires numpy, scipy, matplotlib, pyyaml and HornFab checkout for J.
"""
from __future__ import annotations
import argparse, copy, csv, hashlib, math, sys
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from scipy.special import gammaln
from numpy.polynomial.legendre import leggauss
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yaml

# Six different Le Cleac'h/Iwata shapes using ONLY existing HornFab search keys.
# J0 is deliberately the measured good in-repo *seed* from the smooth brief config;
# none of these has been verified acoustically in this script.
J_SEEDS = [
    ('J0', 'current repo smooth-brief anchor', 459.5, .597, 110.8, 1.167, 1.016),
    ('J1', 'balanced longer oval',          470.0, .56,  100.0, 1.50, 1.15),
    ('J2', 'broad horizontal quasi-Iwata',  470.0, .62,  118.0, 1.85, 1.25),
    ('J3', 'long shallow-termination',      500.0, .55,   87.0, 1.68, 1.30),
    ('J4', 'flared / deeper lip-rollback',  485.0, .62,  150.0, 1.55, 1.10),
    ('J5', 'loading-biased broad oval',     425.0, .55,  112.0, 1.42, 1.07),
]
# Six genuinely different Klangfilm-Lame visual prototypes.
# sweep is in physical millimetres, NOT the local-agent dimensionless rim_sweep.
# p means generalized superellipsoid cap exponent at maximum width, NOT a measured
# dispersion control.  Each entry is preview-only and cannot be sent to BEM.
K_SEEDS = [
    ('K0', 'gentle 2018-like ellipse control', 560., 1.55, 2.0, 1.13, 0.),
    ('K1', 'large soft organic mouth',        510., 1.70, 2.8, 1.30, 8.),
    ('K2', 'rounded rectangle / balanced',   530., 1.85, 4.0, 1.45, 15.),
    ('K3', 'high-Lame 2019-inspired curl',   560., 1.75, 6.0, 1.75, 12.),
    ('K4', 'strong winglike rim sweep',      560., 1.90, 4.2, 1.46, 45.),
    ('K5', 'full-roll oval / soft edge',     580., 1.60, 2.4, 1.82, 4.),
]
ENV = (600., 480., 480.)  # W,H,D, mm hard envelope
THROAT_R_MM = 18.0       # repository brief nominal 36 mm; manufacturer 35.8 mm
C_M_S = 343.0


def smootherstep(x):
    t = np.clip(x, 0., 1.)
    return t*t*t*(t*(t*6.-15.)+10.)


def quad_area(a,b,c,h,p, order=18):
    """Independent generalized superellipsoid-cap area (preview construction).
    P(theta,psi) = (rho(psi)*sin(theta)*cos(psi),
                     rho(psi)*sin(theta)*sin(psi), c*cos(theta)).
    For p=2 it is an ellipsoid; not proof of acoustic isophase fronts.
    """
    nodes, weights = leggauss(order)
    tm = math.acos(np.clip(1.-h/c, -1., 1.))
    theta = (nodes+1.)*tm/2.
    psi = (nodes+1.)*math.pi/4.
    co,si = np.cos(psi), np.sin(psi)
    q = (co/a)**p + (si/b)**p
    rho = q**(-1./p)
    drho = rho*((co**(p-1.)*si/a**p)-(si**(p-1.)*co/b**p))/q
    st,ct = np.sin(theta)[:,None],np.cos(theta)[:,None]
    jac = st*np.sqrt(c*c*st*st*(rho[None,:]**2+drho[None,:]**2)
                     +rho[None,:]**4*ct*ct)
    return float(4.*np.sum(jac*(weights[:,None]*tm/2.)*(weights[None,:]*math.pi/4.)))


def cap_axes(r0,h,aspect,p):
    """Fix a/b=aspect and numerically conserve 2*pi*r0*h curved cap area.
    A *new ratio-locked research model*, not the 2018 author's b-fixed macro.
    """
    target = 2.*math.pi*r0*h
    def f(b): return quad_area(aspect*b,b,r0,h,p)-target
    lo,hi = 1e-5*r0,2*r0
    while f(hi)<0.: hi*=2.
    b=brentq(f,lo,hi,xtol=1e-9,rtol=1e-9)
    return aspect*b,b


def make_klangfilm_preview(seed, n_phi=49, n_s=90):
    _, _, fc, aspect_m, p_m, endfrac, sweep_mm = seed
    R=C_M_S*1000./(math.pi*fc)
    y0=THROAT_R_MM
    h0=R-math.sqrt(R*R-y0*y0)
    h_end=endfrac*R
    hs=np.unique(np.r_[np.geomspace(h0,h_end,65), np.linspace(h0,h_end,65)])
    xa=[];yb=[]; zs=[];ps=[]; ars=[]
    for h in hs:
        t=smootherstep((h-h0)/(R-h0))
        ar=1.+(aspect_m-1.)*t
        p=2.+(p_m-2.)*t
        a,b=cap_axes(R,h,ar,p)
        theta=math.acos(np.clip(1.-h/R,-1.,1.))
        xa.append(a*math.sin(theta)); yb.append(b*math.sin(theta))
        # In mm: x = ln(h/h0)*c/(4*pi*fc) - (h-h0)
        zs.append(math.log(h/h0)*C_M_S*1000./(4.*math.pi*fc) - (h-h0))
        ps.append(p);ars.append(ar)
    a=np.asarray(xa); b=np.asarray(yb); z=np.asarray(zs)
    # Genuine arc-length sampling, not axial z: rollback makes z nonmonotone.
    arc=np.r_[0.,np.cumsum(np.sqrt(np.diff(z)**2 + .5*(np.diff(a)**2+np.diff(b)**2)))]
    tau=np.linspace(0.,arc[-1],n_s+1)
    a=np.interp(tau,arc,a);b=np.interp(tau,arc,b)
    z=np.interp(tau,arc,z);p=np.interp(tau,arc,ps)
    phi=np.linspace(0., math.pi/2., n_phi)
    cos=np.cos(phi)[:,None];sin=np.sin(phi)[:,None]
    rho=((cos/a[None,:])**p[None,:]+(sin/b[None,:])**p[None,:])**(-1./p[None,:])
    # True round physical coupling plane; gradual zero-tangent sweep window downstream.
    xyz=np.stack((rho*cos, rho*sin, np.broadcast_to(z, rho.shape).copy()),axis=-1)
    xyz[:,0,0]=THROAT_R_MM*cos[:,0];xyz[:,0,1]=THROAT_R_MM*sin[:,0]
    w=smootherstep((tau/tau[-1]-.55)/.45)
    xyz[...,2] -= sweep_mm*cos**2*w[None,:]
    xyz[0,:,1]=0.;xyz[-1,:,0]=0.
    return xyz


def mirror_quarter(q):
    """Mirror exact H/V quarter symmetry for 3D preview export only."""
    q0=q.copy()
    q1=q[::-1].copy(); q1[...,0]*=-1.
    q2=q.copy(); q2[...,0]*=-1.;q2[...,1]*=-1.
    q3=q[::-1].copy();q3[...,1]*=-1.
    return np.concatenate((q0, q1[1:],q2[1:],q3[1:]),axis=0)


def bbox(q):
    x,y,z=q[...,0],q[...,1],q[...,2]
    return (2*float(np.max(abs(x))),2*float(np.max(abs(y))),float(np.ptp(z)))


def write_open_obj(q, dest):
    """Preview surface ONLY. No rear enclosure, outer shell, source cap, or BEM tags."""
    full=mirror_quarter(q)
    np_, ns,_=full.shape
    with open(dest,'w',encoding='utf8') as f:
        f.write('# visual-only open interior surface; NOT watertight or BEM ready\n')
        for x,y,z in full.reshape(-1,3): f.write(f'v {x:.6f} {y:.6f} {z:.6f}\n')
        for i in range(np_):
            ni=(i+1)%np_
            for j in range(ns-1):
                a=i*ns+j+1;b=ni*ns+j+1
                f.write(f'f {a} {b} {b+1}\n');f.write(f'f {a} {b+1} {a+1}\n')


def make_preview_row(axs, q, title, dims, valid):
    full=mirror_quarter(q)
    plot=np.concatenate((full,full[:1]),axis=0)
    X,Y,Z=plot[::3,::3,0],plot[::3,::3,1],plot[::3,::3,2]
    maxs=max(ENV)*.56
    poses=[(20,-65),(90,-90),(5,0)]
    for i,(el,az) in enumerate(poses):
        ax=axs[i]
        ax.plot_surface(X,Y,Z,color='#c9b780',edgecolor='none',antialiased=True,shade=True)
        ax.view_init(elev=el,azim=az)
        ax.set_xlim(-maxs,maxs); ax.set_ylim(-maxs,maxs);ax.set_zlim(-maxs,maxs)
        ax.set_box_aspect((1,1,1),zoom=.92)
        ax.set_axis_off()
    # Azimuth endpoints are the H and V meridians. Draw both sides of each section.
    for index,wall in [(3,q[0]),(4,q[-1])]:
        radius=wall[:,0] if index==3 else wall[:,1]
        depth=wall[:,2]
        ax=axs[index];color='#2d6ea0' if index==3 else '#b65b40'
        ax.plot(depth,radius,color=color,lw=1.7)
        ax.plot(depth,-radius,color=color,lw=1.7)
        ax.plot([depth[0],depth[0]],[-THROAT_R_MM,THROAT_R_MM],lw=2.3,color='black')
        ax.set_xlim(-120,430);ax.set_ylim(-275,275);ax.grid(alpha=.2)
        ax.tick_params(labelsize=6)
        ax.set_aspect('equal',adjustable='box')
    axs[0].set_title(f'{title}\n{dims[0]:.0f}x{dims[1]:.0f}x{dims[2]:.0f} mm | {"PASS" if valid else "ENVELOPE"}',
                     fontsize=8,loc='left',color='black' if valid else 'firebrick')


def save_sheet(items, path, heading):
    if not items: return
    fig=plt.figure(figsize=(17, 3.2*len(items)), dpi=110,layout='constrained')
    gs=fig.add_gridspec(len(items),5)
    for row, (ident,label,q,dims,valid) in enumerate(items):
        axs=[fig.add_subplot(gs[row,k],projection='3d' if k<3 else None) for k in range(5)]
        make_preview_row(axs,q,f'{ident} {label}',dims,valid)
        if row==0:
            for j,name in enumerate(('3/4','front','side','H section','V section')):
                axs[j].text2D(.5,1.12,name,transform=axs[j].transAxes,ha='center',fontsize=9) if j<3 else axs[j].set_title(name,fontsize=9)
    fig.suptitle(heading+' | blue/red sections | black = 36 mm nominal throat | GEOMETRY ONLY',fontsize=12)
    fig.savefig(path,dpi=140);plt.close(fig)


def repo_j_seed(base,seed):
    ident,label,fc,t,stop,ar,p=seed
    cfg=copy.deepcopy(base)
    cfg['name']='hf1440_gallery_'+ident.lower()
    cfg['description']=f'RENDER/PREFLIGHT seed {ident}: {label}; no acoustic performance established'
    vals=dict(g_fc_hz=fc,g_T=t,g_stop_deg=stop,g_ar_m=ar,g_ar_p=p)
    cfg['seed_params'].update(vals)
    # Pin for a SINGLE reproducible geometry. Not a search configuration.
    for key,value in vals.items(): cfg['bounds'][key]=dict(lo=value,hi=value,search=False)
    return cfg


def generate(root,out,include_j=True,include_k=True):
    root=Path(root).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    jobs=[];items_j=[];items_k=[]
    if include_k:
        # Manifest, not executable HornFab config: the new solver-backed family is unverified.
        kmanifest = {'schema':'hornfab.klangfilm_lame.preview.v1',
                     'kind':'RESEARCH_GEOMETRY_NOT_BEM_READY',
                     'throat_diameter_mm':2*THROAT_R_MM,
                     'envelope_mm':dict(W=ENV[0],H=ENV[1],D=ENV[2]),
                     'area_model':'ratio-locked generalized superellipsoid cap (our proposal, not 2018 macro)',
                     'candidates':[dict(id=k[0],style=k[1],fc_hz=k[2],aspect=k[3],
                                        lame_p=k[4],end_frac=k[5],rim_sweep_mm=k[6]) for k in K_SEEDS]}
        (out/'K_PREVIEW_SEEDS_NOT_FOR_BEM.yaml').write_text(
            yaml.safe_dump(kmanifest,sort_keys=False),encoding='utf8')
    if include_j:
        sys.path.insert(0,str(root))
        from hornlab_search.design.generators import grid
        path=root/'examples/typologies/home_landscape_2026-11-15/hl__lecleach_iwata_ar_landscape_smooth_v7.yaml'
        base=yaml.safe_load(path.read_text(encoding='utf-8'))
        brief=(path.parent/base['brief_file']).resolve()
        br=yaml.safe_load(brief.read_text(encoding='utf-8'))
        assert br['driver']['exit_radius_mm']==THROAT_R_MM
        assert [br['target']['coverage_h_deg'],br['target']['coverage_v_deg']]==[80.,50.]
        for seed in J_SEEDS:
            ident,label=seed[:2];cfg=repo_j_seed(base,seed)
            dest=out/(ident+'_PRE-FLIGHT_PINNED.yaml')
            # YAML copied outside of repo needs ABSOLUTE brief_file path, otherwise config fails.
            cfg['brief_file']=str(brief)
            dest.write_text(yaml.safe_dump(cfg,sort_keys=False,allow_unicode=True),encoding='utf8')
            try:
                q,meta=grid.rows_grid_points(cfg['generator'],cfg['seed_params'],br)
                dims=bbox(q);valid=all(v<=lim for v,lim in zip(dims,ENV))
                write_open_obj(q,out/(ident+'_OPEN_SURFACE.obj'))
                items_j.append((ident,label,q,dims,valid))
                jobs.append([ident,'REAL_REPO_IWATA_AR',label,*map(lambda v:round(v,2),dims),valid,'geometry generated; mesh not certified'])
            except Exception as ex:
                jobs.append([ident,'REAL_REPO_IWATA_AR',label,'','','',False,'GENERATOR REJECTED: '+str(ex)[:180]])
    if include_k:
        for seed in K_SEEDS:
            ident,label=seed[:2]
            try:
                q=make_klangfilm_preview(seed)
                dims=bbox(q);valid=all(v<=lim for v,lim in zip(dims,ENV))
                write_open_obj(q,out/(ident+'_PREVIEW_ONLY_OPEN_SURFACE.obj'))
                items_k.append((ident,label,q,dims,valid))
                jobs.append([ident,'RESEARCH_ONLY_KLANGFILM_LAME',label,*map(lambda v:round(v,2),dims),valid,'preview only; NOT safe to BEM'])
            except Exception as ex:
                jobs.append([ident,'RESEARCH_ONLY_KLANGFILM_LAME',label,'','','',False,'PREVIEW ERROR: '+str(ex)[:180]])
    if items_j: save_sheet(items_j,out/'01_IWATA_EXISTING_CODE.png','HF1440 Le Cleac\'h / Iwata existing-code starts')
    if items_k: save_sheet(items_k,out/'02_KLANGFILM_LAME_EXPERIMENTAL.png','HF1440 Klangfilm Lame research previews')
    with open(out/'INDEX.csv','w',newline='',encoding='utf8') as f:
        writer=csv.writer(f);writer.writerow(['id','kind','style','W_mm','H_mm','D_mm','envelope_pass','status']);writer.writerows(jobs)
    for j in jobs: print(' | '.join(map(str,j)))
    print('Output:',out)


def selftest_math():
    # Test sphere cap and bisection-based curved-area conservation.
    r=.19;h=.11
    assert abs(quad_area(r,r,r,h,2.)/(2.*math.pi*r*h)-1.)<1e-9
    for p in (2.,3.5,5.5):
        a,b=cap_axes(180.,70.,1.8,p)
        assert abs(quad_area(a,b,180.,70.,p)/(2.*math.pi*180.*70.)-1.)<1e-8
    # Test `phi` grid and round coupling geometry.
    k=make_klangfilm_preview(K_SEEDS[2],n_phi=13,n_s=45)
    assert np.max(np.abs(np.hypot(k[:,0,0],k[:,0,1])-THROAT_R_MM))<1e-6
    assert np.all(np.isfinite(k))
    print('SELFTEST PASS: curved spherical cap, Lamé area preservation, round throat, finite points')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Create dual-family HF1440 seed images and repo-backed J YAMLs')
    parser.add_argument('--repo',default='.',help='path to HornFab checkout (J family)')
    parser.add_argument('--out',default='docs/queue/hf1440_diverse_seed_sheet')
    parser.add_argument('--k-only',action='store_true',help='run K previews without HornFab checkout')
    parser.add_argument('--j-only',action='store_true',help='existing-code J family only')
    parser.add_argument('--selftest',action='store_true')
    args=parser.parse_args()
    if args.selftest: selftest_math()
    else: generate(args.repo,args.out,include_j=not args.k_only,include_k=not args.j_only)

