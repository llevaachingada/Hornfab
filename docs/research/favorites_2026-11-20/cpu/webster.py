"""CPU proxy: plane-wave Webster TMM throat resistance from the generator's own wall grid. Relative trends only."""
import yaml, json, math, sys, numpy as np
from scipy.special import j1, struve
from hornlab_search.design.generators import grid
cfg=yaml.safe_load(open("examples/typologies/cd_v11_completion_2026-11-20/cd11c__crowe_x_osse_cd.yaml"))
best=json.load(open("runs/20261120T084006Z-screen-fc4e18/best.json"))["params"]["grid"]["knobs"]
spec={k:v for k,v in cfg["generator"].items() if k!="seed_policy"}
spec["n_s"]=120
drv={"driver":{"exit_radius_mm":18.0,"exit_angle_deg":2.0}}
C=343.0; RHO=1.2
def area_profile(kn):
    pts,meta=grid.rows_grid_points(spec,kn,drv)
    nphi=pts.shape[0]; phis=np.linspace(0,np.pi/2,nphi)
    rows=[]
    for i in range(nphi):
        p=pts[i]; r=np.hypot(p[:,0],p[:,1]); z=p[:,2]
        # keep the monotone part (before lip rollback)
        stop=np.argmax(z); rows.append((z[:stop+1],r[:stop+1]))
    zmax=min(r[0][-1] for r in rows)
    zg=np.linspace(0,zmax,int(zmax/1.0)+1)
    R=np.array([np.interp(zg,z,r) for z,r in rows])     # nphi x nz
    x=R*np.cos(phis)[:,None]; y=R*np.sin(phis)[:,None]
    # quarter polygon area incl origin: shoelace over (0,0)->rows->(0,0)
    A=np.zeros(len(zg))
    for j in range(len(zg)):
        xs=np.concatenate([[0],x[:,j],[0]]); ys=np.concatenate([[0],y[:,j],[0]])
        A[j]=0.5*abs(np.dot(xs,np.roll(ys,-1))-np.dot(ys,np.roll(xs,-1)))*4
    return zg*1e-3, A*1e-6, meta
def zrad_piston(k,a,S):
    ka2=2*k*a
    return RHO*C/S*((1-j1(ka2)/(k*a))+1j*struve(1,ka2)/(k*a))
def throat_z(z,A,f):
    out=[]
    for fr in f:
        k=2*np.pi*fr/C
        Z=zrad_piston(k,math.sqrt(A[-1]/math.pi),A[-1])
        for i in range(len(z)-1,0,-1):
            L=z[i]-z[i-1]; S=0.5*(A[i]+A[i-1]); Zc=RHO*C/S
            c,s=math.cos(k*L),math.sin(k*L)
            Z=(Z*c+1j*Zc*s)/(1j*Z*s/Zc+c)
        out.append(Z*A[0]/(RHO*C))
    return np.array(out)
f=np.array([300,394,452,519,595,682,782,896,1028,1178,1351,1549,1776,2037,2335])
def cross(f,z,t):
    for i in range(1,len(f)):
        if z[i-1]<t<=z[i]: return f[i-1]*(f[i]/f[i-1])**((t-z[i-1])/(z[i]-z[i-1]))
    return float('nan')
if __name__=="__main__":
    variants=[("best k1",{}),("k1.5",{"g_k":1.5}),("k2",{"g_k":2.0}),("k3",{"g_k":3.0}),("k4",{"g_k":4.0}),
              ("k1 L340",{"g_L_mm":340.0}),("k2.5 L320",{"g_k":2.5,"g_L_mm":320.0})]
    for name,d in variants:
        kn=dict(best); kn.update(d)
        try:
            z,A,meta=area_profile(kn)
        except Exception as e:
            print(name,"REFUSED",e); continue
        zt=throat_z(z,A,f).real
        print(f"{name:10s} W{meta['mouth_w_mm']:5.0f} H{meta['mouth_h_mm']:5.0f} D{meta['x_span_mm']:4.0f} | LFP20 {cross(f,zt,0.2):5.0f} LFP50 {cross(f,zt,0.5):5.0f} | "+" ".join(f"{v:4.2f}" for v in zt))
