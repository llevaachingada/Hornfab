"""Room-targeted coverage lanes (owner 2026-11-20 ~18:34: 20x16x9 ft room, wide sweet spot; compact 400 cube at 1 kHz)."""
import json, math, copy, yaml
from scipy.optimize import brentq
from hornlab_search.design.generators import grid
exec(open("docs/research/favorites_2026-11-20/cpu/write_favSC.py").read().split("D=")[0])
BASEB.update({"g_k_v_log":(0.0,0.0),"g_v_exp_mm":(0.0,0.0)})
SRC="examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"
def brief(name, h, v, fx, env, note):
    b=yaml.safe_load(open(SRC)); b["name"]=name
    hmin,hmax=(75,105) if h==90 else (60,90); vmin,vmax=(40,60) if v==50 else (48,72)
    cp=b["target"]["coverage_profile"]
    cp["h"]=[{"hz":int(fx),"min_deg":hmin,"max_deg":hmax,"preferred_deg":h},{"hz":8000,"min_deg":hmin,"max_deg":hmax,"preferred_deg":h}]
    cp["v"]=[{"hz":max(1000,int(fx)),"min_deg":vmin,"max_deg":vmax,"preferred_deg":v},{"hz":8000,"min_deg":vmin,"max_deg":vmax,"preferred_deg":v}]
    b["target"]["coverage_h_deg"]=float(h); b["target"]["coverage_v_deg"]=float(v)
    b["target"]["f0_hz"]=float(fx); b["target"]["f0_v_hz"]=float(fx); b["objective"]["cd"]["band_hz"]=[float(fx),8000.0]
    b["envelope"]={"max_depth_mm":env[2],"max_mouth_h_mm":env[1],"max_mouth_w_mm":env[0]}
    b["description"]=f"(objective v11) ROOM identity {name}: H {h} ({hmin}-{hmax}) from {fx:g} Hz, V {v} ({vmin}-{vmax}) from {max(1000,fx):g} Hz, F_X {fx:g}, envelope {env[0]:g}x{env[1]:g}x{env[2]:g}. {note} Own identity."
    path=f"examples/briefs/room_2026-11-20/{name}.yaml"
    dump(path,["Room-targeted v11 CD brief (2026-11-20, owner: 20 x 16 x 9 ft room, wide sweet spot).",
      f"Copied from {SRC}; changed ONLY name, description, coverage_profile H/V corridors + coverage_h/v_deg, f0_hz/f0_v_hz,",
      "objective.cd.band_hz start, envelope. Rationale: docs/research/favorites_2026-11-20/ROOM_TARGETS.md. Own J identity."],b)
    return "../../briefs/room_2026-11-20/"+name+".yaml"
def seed(base_kn, a_h, a_v, r0, w, h):
    kn=dict(base_kn, g_a_h_deg=a_h, g_a_v_deg=a_v)
    def wm(L): return grid.rows_grid_points(SPEC,dict(kn,g_L_mm=L),{"driver":{"exit_radius_mm":r0,"exit_angle_deg":2.0}})[1]["mouth_w_mm"]-w
    kn["g_L_mm"]=round(brentq(wm,120,340,xtol=0.5),1)
    def hm(sv): return grid.rows_grid_points(SPEC,dict(kn,g_s_v=sv),{"driver":{"exit_radius_mm":r0,"exit_angle_deg":2.0}})[1]["mouth_h_mm"]-h
    try: kn["g_s_v"]=round(brentq(hm,0.05,0.9,xtol=1e-4),4)
    except ValueError: pass
    return kn
P=dict(fav, g_k_v=2.0, g_s_v=fav["g_s"])
lanes=[]
B1=brief("room_w90x50_700_hf1440_v11cd",90,50,700,(600,480,480),"Wide-sweet-spot target (Geddes-style toe-in crossfire).")
B2=brief("room_w90x60_700_hf1440_v11cd",90,60,700,(600,480,480),"Wide sweet spot, forgiving vertical.")
C1=brief("compact400_xo1000_w90x50_hf1440_v11cd",90,50,1000,(400,400,400),"400 mm cube, 1 kHz crossover.")
C2=brief("compact400_xo1000_w90x60_hf1440_v11cd",90,60,1000,(400,400,400),"400 mm cube, 1 kHz crossover, forgiving vertical.")
C3=brief("compact400_xo1000_80x50_hf1440_v11cd",80,50,1000,(400,400,400),"400 mm cube, 1 kHz crossover, FAV-001 coverage.")
D="examples/typologies/room_2026-11-20/"
H=["Room-targeted P1 split-plane lanes (2026-11-20 ~18:40). Rationale docs/research/favorites_2026-11-20/ROOM_TARGETS.md."]
home_box={"g_k_v":(1.0,4.0),"g_s_v":(0.3,0.9),"g_a_h_deg":(41.0,48.0),"g_a_v_deg":(20.0,33.0),"g_L_mm":(175.0,260.0),"g_s":(0.25,0.47)}
cmp_box={"g_k_v":(1.0,4.0),"g_s_v":(0.25,0.95),"g_a_h_deg":(36.0,48.0),"g_a_v_deg":(20.0,33.0),"g_L_mm":(125.0,210.0),"g_s":(0.12,0.32)}
specs=[("room__w90x50_home",B1,seed(P,45.0,24.0,18.0,585,440),home_box),
       ("room__w90x60_home",B2,seed(P,45.0,30.0,18.0,585,470),home_box),
       ("room__c400_w90x50",C1,seed(dict(P,g_s=0.25),45.0,24.0,18.0,388,330),cmp_box),
       ("room__c400_w90x60",C2,seed(dict(P,g_s=0.25),45.0,30.0,18.0,388,370),cmp_box),
       ("room__c400_80x50",C3,seed(dict(P,g_s=0.25),38.0,24.0,18.0,388,330),cmp_box)]
for n,b,s,box in specs:
    box2={k:(min(v[0],s[k]),max(v[1],s[k])) for k,v in box.items()}
    c=make(n,s,b,box2,80,"room-targeted P1 split-plane lane"); c["search"]["max_attempts"]=450
    dump(D+n+".yaml",H,c); print(n, {k:s[k] for k in ("g_a_h_deg","g_a_v_deg","g_L_mm","g_s","g_s_v")})
