import sys; sys.path.insert(0, sys.argv[1])
from webster import *
from scipy.optimize import brentq
for kk in [1.0,1.5,2.0,2.5,3.0,3.5,4.0]:
    def wmouth(L):
        kn=dict(best); kn.update({"g_k":kk,"g_L_mm":L}); _,_,m=area_profile(kn); return m["mouth_w_mm"]-587.35
    try: L=brentq(wmouth,200,330,xtol=0.5)
    except Exception as e: print(kk,"no L",e); continue
    kn=dict(best); kn.update({"g_k":kk,"g_L_mm":L}); z,A,meta=area_profile(kn); zt=throat_z(z,A,f).real
    print(f"k{kk:3.1f} L{L:5.1f} W{meta['mouth_w_mm']:5.0f} H{meta['mouth_h_mm']:5.0f} | LFP20 {cross(f,zt,0.2):5.0f} LFP50 {cross(f,zt,0.5):5.0f} | Re z@682/782/896/1028: "+" ".join(f"{v:4.2f}" for v in zt[5:9]))
