"""Writes the SplitCore lanes (owner fixture, 2026-11-20 ~18:25): log k + V-only exponential throat blend."""
import json, math
exec(open("docs/research/favorites_2026-11-20/cpu/write_favP1.py").read().split("F2=")[0])
BASEB.update({"g_k_v_log":(1.0,1.0),"g_v_exp_mm":(0.0,0.0)})
D="examples/typologies/favSC_2026-11-20/"
H=["SplitCore variant lanes (2026-11-20 ~18:25, owner: 'try its ideas to create this geometry typology variant').",
   "Source: owner-supplied HornFab_SplitCore_Analytic_Reference_Fixture.py (Batik OS-SE eq. 3 generalized OS term):",
   "geometric k(phi) (g_k_v_log 1) + V-weighted exponential throat r0 exp(z tan a0/r0) blended C2 into the base V wall",
   "by z = g_v_exp_mm. LABELED HYPOTHESIS-SHAPE EXPERIMENT. Fixture a0 9 deg NOT adopted: the brief's driver a0 2 deg is kept."]
fav1=dict(fav,g_k_v=3.0,g_k_v_log=1.0,g_v_exp_mm=50.0); fav1["g_s_v"]=fit_sv(fav1,18.0,450.3)
pol1=dict(pol,g_k_v=2.5,g_k_v_log=1.0,g_v_exp_mm=40.0); pol1["g_s_v"]=fit_sv(pol1,18.0,447.0)
dump(D+"favSCs__fav_core.yaml",H+[f"single: FAV-001 + log k_v 3 + V exp throat 50 mm, s_v {fav1['g_s_v']} (V mouth 450). Compare favP1s__fav_kv3_sv."],
     make("favSCs__fav_core",fav1,HOME,{},1,"single: FAV-001 SplitCore (log k_v 3, V exp 50 mm)"))
box={"g_k_v":(1.0,4.0),"g_s_v":(0.15,0.7),"g_v_exp_mm":(10.0,90.0),"g_a_h_deg":(32.0,38.0),"g_a_v_deg":(20.0,30.0),"g_L_mm":(220.0,320.0),"g_s":(0.2,0.47)}
for n,s,note in [("favSC__core_fav",fav1,"CMA SplitCore from FAV-001: k_H 1, log k_v, V exp throat length searched"),
                 ("favSC__core_polish",pol1,"CMA SplitCore from 392276e62470 (k1-polish winner)")]:
    c=make(n,s,HOME,box,80,note); c["search"]["max_attempts"]=450; dump(D+n+".yaml",H+[note],c)
print("s_v", fav1["g_s_v"], pol1["g_s_v"])
