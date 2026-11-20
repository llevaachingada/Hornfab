import sys; sys.path.insert(0, sys.argv[1])
from webster import *
from scipy.optimize import brentq
fx=900.0
rows=[]
for kk in [1.0,2.0,2.5,3.0,3.5]:
  for ah,av in [(34.9,26.8),(36.0,24.0)]:
    for s in [0.30,0.40]:
        def wm(L):
            kn=dict(best); kn.update({"g_k":kk,"g_L_mm":L,"g_a_h_deg":ah,"g_a_v_deg":av,"g_s":s}); _,_,m=area_profile(kn); return m["mouth_w_mm"]-484.0
        try: L=brentq(wm,120,420,xtol=0.5)
        except Exception as e: print(kk,ah,s,"noL",e); continue
        kn=dict(best); kn.update({"g_k":kk,"g_L_mm":L,"g_a_h_deg":ah,"g_a_v_deg":av,"g_s":s}); z,A,m=area_profile(kn); zt=throat_z(z,A,f).real
        l20=cross(f,zt,0.2); rzmin=min(zt[f>=fx]); pen=max(0,math.log2(l20*1.6/fx))+max(0,0.5-rzmin)
        print(f"k{kk:3.1f} ah{ah} av{av} s{s} L{L:5.1f} W{m['mouth_w_mm']:4.0f} H{m['mouth_h_mm']:4.0f} D{m['x_span_mm']:4.0f} | LFP20 {l20:4.0f} LFP50 {cross(f,zt,0.5):5.0f} minRe>=900 {rzmin:4.2f} | proxy load raw {pen:4.2f}")
