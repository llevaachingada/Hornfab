"""Proxy for the two 'loading without HF beaming' levers: V-only k (throat_hv_ratio) and a 2-inch exit."""
import sys, math; sys.path.insert(0, sys.argv[1])
import webster as W
from scipy.optimize import brentq
def run(name, kn, r0=18.0, wtarget=None):
    W.drv["driver"]["exit_radius_mm"]=r0
    if wtarget:
        def wm(L):
            k2=dict(kn); k2["g_L_mm"]=L; return W.area_profile(k2)[2]["mouth_w_mm"]-wtarget
        kn=dict(kn); kn["g_L_mm"]=brentq(wm,150,340,xtol=0.5)
    z,A,m=W.area_profile(kn); zt=W.throat_z(z,A,W.f).real
    fx=700; l20=W.cross(W.f,zt,0.2); rzmin=min(zt[W.f>=fx])
    pen=max(0,math.log2(l20*1.6/fx))+max(0,0.5-rzmin)
    print(f"{name:26s} r0 {r0:4.1f} L {kn['g_L_mm']:5.1f} W{m['mouth_w_mm']:4.0f} H{m['mouth_h_mm']:4.0f} | LFP20 {l20:4.0f} LFP50 {W.cross(W.f,zt,0.5):5.0f} | Re z 682/782/896/1028: "+" ".join(f"{v:4.2f}" for v in zt[5:9])+f" | proxy load term {pen/0.3:4.2f}")
B=dict(W.best)
run("FAV-001 (1.4in, k1)", B)
for K in (2.0,3.0,4.0):
    kn=dict(B); kn["g_k"]=math.sqrt(K); kn["g_throat_hv_ratio"]=K
    run(f"V-only k: kH 1, kV {K:g}", kn, wtarget=587.35)
run("2in exit, FAV knobs", B, r0=25.4)
run("2in exit, mouth held 587", B, r0=25.4, wtarget=587.35)
kn=dict(B); kn["g_k"]=math.sqrt(2.0); kn["g_throat_hv_ratio"]=2.0
run("2in + V-only kV 2", kn, r0=25.4, wtarget=587.35)
