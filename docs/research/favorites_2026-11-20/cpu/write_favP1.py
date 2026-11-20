"""Writes the P1 split-plane (g_k_v, g_s_v) lanes, 2026-11-20 evening. Run from repo root."""
import json, math, yaml
from scipy.optimize import brentq
from hornlab_search.design.generators import grid
exec(open("docs/research/favorites_2026-11-20/cpu/write_favL.py").read().split('BASEB["g_throat_hv_ratio"]')[0])
BASEB.update({"g_k_v":(1.0,1.0),"g_s_v":(0.0,0.0)})
pol=next(json.loads(l)["params"]["grid"]["knobs"] for l in open("runs/20261120T221434Z-screen-037ca6/search.ndjson")
         if '"392276e62470"' in l and json.loads(l).get("ok"))
SPEC={k:v for k,v in base["generator"].items() if k!="seed_policy"}
def fit_sv(kn, r0, h_target):
    def h(sv): k2=dict(kn, g_s_v=sv); return grid.rows_grid_points(SPEC,k2,{"driver":{"exit_radius_mm":r0,"exit_angle_deg":2.0}})[1]["mouth_h_mm"]-h_target
    return round(brentq(h, 0.05, 0.9, xtol=1e-4),4)
F2="../../briefs/hf2in_2026-11-20/room_landscape_80x50_700_hf2in_v11cd.yaml"
D="examples/typologies/favP1_2026-11-20/"
H=["P1 split-plane OS-SE lanes (2026-11-20 evening, owner: 'Yes, build P1'). Knobs g_k_v / g_s_v: k(phi) = k cos^2 + k_v sin^2,",
   "s(phi) = s cos^2 + s_v sin^2; H row keeps k = 1 and s. Dossier: docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md."]
fav1=dict(fav, g_k_v=3.0); fav1["g_s_v"]=fit_sv(fav1,18.0,450.3)
pol1=dict(pol, g_k_v=2.5); pol1["g_s_v"]=fit_sv(pol1,18.0,447.0)
pol2=dict(pol, g_k_v=1.4); pol2["g_s_v"]=fit_sv(pol2,25.4,461.0)
dump(D+"favP1s__fav_kv3_sv.yaml",H+[f"single: FAV-001 + k_v 3, s_v {fav1['g_s_v']} (V mouth restored to 450 mm). Compare favL1__kv3 (J 4.657)."],
     make("favP1s__fav_kv3_sv",fav1,HOME,{},1,"single: FAV-001 + split-plane k_v 3 with V mouth restored"))
box={"g_k_v":(1.0,4.0),"g_s_v":(0.15,0.7),"g_a_h_deg":(32.0,38.0),"g_a_v_deg":(20.0,30.0),"g_L_mm":(220.0,320.0),"g_s":(0.2,0.47)}
for n,s,b,o,note in [("favP1__split_fav",fav1,HOME,box,"CMA split-plane from FAV-001 (k_H 1 fixed; k_v, s_v searched)"),
                     ("favP1__split_polish",pol1,HOME,box,"CMA split-plane from 392276e62470 (k1-polish winner)"),
                     ("favP1__split_2in",pol2,F2,dict(box,g_k_v=(1.0,2.2)),"CMA split-plane on the 2-inch exit from 392276e62470, mild k_v")]:
    c=make(n,s,b,o,80,note); c["search"]["max_attempts"]=450; dump(D+n+".yaml",H+[note],c)
print("s_v fits:", fav1["g_s_v"], pol1["g_s_v"], pol2["g_s_v"])
