"""9-degree driver exit-angle lanes (owner 2026-11-20 ~18:28: 'use the 9 degree throat angle ... aligns with some drivers')."""
import json, math, yaml
from scipy.optimize import brentq
exec(open("docs/research/favorites_2026-11-20/cpu/write_favSC.py").read().split("D=")[0])
src="examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"
b=yaml.safe_load(open(src)); b["name"]="room_landscape_80x50_700_hf1440a9_v11cd"
b["driver"]["exit_angle_deg"]=9.0
b["description"]=b["description"]+" DRIVER EXIT ANGLE 9 deg (1.4-inch exit) study."
dump("examples/briefs/a9_2026-11-20/room_landscape_80x50_700_hf1440a9_v11cd.yaml",[
 "9-DEGREE EXIT-ANGLE study brief (2026-11-20, owner: some 1.4-inch drivers exit at ~9 deg).",
 f"Copied from {src}; changed ONLY name, description, driver.exit_angle_deg 2.0 -> 9.0 (OS a0; source cap auto follows).",
 "NEW J IDENTITY: never rank against the 2-deg briefs; compare physical numbers."],b)
A9="../../briefs/a9_2026-11-20/room_landscape_80x50_700_hf1440a9_v11cd.yaml"
def fit_sv9(kn,h):
    from hornlab_search.design.generators import grid
    f=lambda sv: grid.rows_grid_points(SPEC,dict(kn,g_s_v=sv),{"driver":{"exit_radius_mm":18.0,"exit_angle_deg":9.0}})[1]["mouth_h_mm"]-h
    return round(brentq(f,0.05,0.9,xtol=1e-4),4)
D="examples/typologies/favA9_2026-11-20/"
H=["9-deg exit-angle lanes (2026-11-20 ~18:28). Brief: examples/briefs/a9_2026-11-20/ (driver a0 9 deg). Own J identity.",
   "Geometry knobs as the favSC / favP1 lanes; dossier docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md s7."]
sc=dict(fav,g_k_v=3.0,g_k_v_log=1.0,g_v_exp_mm=50.0); sc["g_s_v"]=fit_sv9(sc,450.3)
p1=dict(fav,g_k_v=3.0); p1["g_s_v"]=fit_sv9(p1,450.3)
BASEB.update({"g_k_v_log":(1.0,1.0),"g_v_exp_mm":(0.0,0.0)})
singles=[("favA9s__fav_plain",dict(fav),"single: FAV-001 knobs exactly at a0 9 deg"),
         ("favA9s__fav_p1",p1,f"single: FAV-001 + k_v 3, s_v {p1['g_s_v']} at a0 9"),
         ("favA9s__fav_core",sc,f"single: FAV-001 SplitCore (log k_v 3, V exp 50 mm, s_v {sc['g_s_v']}) at a0 9")]
for n,s,note in singles: dump(D+n+".yaml",H+[note],make(n,s,A9,{},1,note))
box={"g_k_v":(1.0,4.0),"g_s_v":(0.15,0.7),"g_v_exp_mm":(10.0,90.0),"g_a_h_deg":(32.0,38.0),"g_a_v_deg":(20.0,30.0),"g_L_mm":(220.0,320.0),"g_s":(0.2,0.47)}
c=make("favA9__core_fav",sc,A9,box,80,"CMA SplitCore from FAV-001 at a0 9 deg"); c["search"]["max_attempts"]=450
dump(D+"favA9__core_fav.yaml",H+["CMA SplitCore from FAV-001 at a0 9 deg"],c)
print(p1["g_s_v"], sc["g_s_v"])
