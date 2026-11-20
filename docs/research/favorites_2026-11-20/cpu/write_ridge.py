"""Ridge (ATH radial diagonal) + beak lanes, 2026-11-20 ~18:45, queued behind everything else."""
import json
exec(open("docs/research/favorites_2026-11-20/cpu/write_favSC.py").read().split("D=")[0])
BASEB.update({"g_k_v_log":(0.0,0.0),"g_v_exp_mm":(0.0,0.0),"g_a_d_deg":(0.0,0.0),"g_beak_h_mm":(0.0,0.0),
              "g_beak_v_mm":(0.0,0.0),"g_beak_d_mm":(0.0,0.0),"g_beak_start":(0.7,0.7)})
D="examples/typologies/favRB_2026-11-20/"
H=["Ridge + beak lanes (2026-11-20 ~18:45, owner: ATH-style ridges for diagonal dispersion + beak on H and V).",
   "g_a_d_deg: radial diagonal angle a(phi) += a_d sin^2(2phi); g_beak_*: axial lip offset after g_beak_start (C2).",
   "Base: P1 split-plane FAV-001 (k_v 3, s_v 0.5512). Record: docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md s8."]
P=dict(fav, g_k_v=3.0, g_s_v=0.5512)
singles=[("favRBs__ridge8",dict(P,g_a_d_deg=8.0),"single: P1 FAV + diagonal ridge 8 deg"),
         ("favRBs__beak_hv",dict(P,g_beak_h_mm=-15.0,g_beak_v_mm=15.0,g_beak_start=0.7),"single: P1 FAV + beak (H setback 15, V projection 15)"),
         ("favRBs__ridge_beak",dict(P,g_a_d_deg=8.0,g_beak_h_mm=-15.0,g_beak_v_mm=15.0,g_beak_start=0.7),"single: P1 FAV + ridge 8 + beak H-15/V+15")]
for n,s,note in singles: dump(D+n+".yaml",H+[note],make(n,s,HOME,{},1,note))
box={"g_k_v":(1.0,4.0),"g_s_v":(0.3,0.75),"g_a_d_deg":(0.0,14.0),"g_beak_h_mm":(-35.0,25.0),"g_beak_v_mm":(-25.0,35.0),
     "g_beak_d_mm":(-20.0,20.0),"g_beak_start":(0.5,0.9),"g_a_h_deg":(32.0,38.0),"g_a_v_deg":(20.0,30.0),"g_L_mm":(220.0,300.0),"g_s":(0.25,0.47)}
seed=dict(P,g_a_d_deg=6.0,g_beak_h_mm=-10.0,g_beak_v_mm=10.0,g_beak_d_mm=0.0,g_beak_start=0.7)
c=make("favRB__ridge_beak_fav",seed,HOME,box,80,"CMA P1 + ridge + beak from FAV-001"); c["search"]["max_attempts"]=450
dump(D+"favRB__ridge_beak_fav.yaml",H+["CMA P1 + ridge + beak from FAV-001"],c)
W90="../../briefs/room_2026-11-20/room_w90x50_700_hf1440_v11cd.yaml"
r=yaml.safe_load(open("examples/typologies/room_2026-11-20/room__w90x50_home.yaml"))["seed_params"]
rseed=dict(r,g_a_d_deg=6.0,g_beak_h_mm=-10.0,g_beak_v_mm=10.0,g_beak_d_mm=0.0,g_beak_start=0.7,g_k_v_log=0.0,g_v_exp_mm=0.0)
rbox=dict(box,g_a_h_deg=(41.0,48.0),g_a_v_deg=(20.0,33.0),g_L_mm=(175.0,260.0),g_s_v=(0.3,0.9))
c=make("favRB__ridge_beak_w90x50",rseed,W90,rbox,80,"CMA P1 + ridge + beak on the room w90x50 brief"); c["search"]["max_attempts"]=450
dump(D+"favRB__ridge_beak_w90x50.yaml",H+["CMA P1 + ridge + beak, room w90x50 brief (own identity)"],c)
print("ok")
