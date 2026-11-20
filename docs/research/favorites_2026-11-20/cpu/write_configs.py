import yaml, copy, json, os
R="C:/Users/hunte/Hrns/hornlab-search/"
FAV_RUN="20261120T084006Z-screen-fc4e18"; FAV_HASH="4140768780f0"
best=json.load(open(R+f"runs/{FAV_RUN}/best.json"))["params"]["grid"]["knobs"]
base=yaml.safe_load(open(R+"examples/typologies/cd_v11_completion_2026-11-20/cd11c__crowe_x_osse_cd.yaml"))
HOME_BRIEF="../../briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"
C500_BRIEF="../../briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml"
def dump(path, header, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as fh:
        fh.write("".join(f"# {l}\n" for l in header)); yaml.safe_dump(obj, fh, sort_keys=False, width=100)
# ---- compact brief
b=yaml.safe_load(open(R+"examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"))
b["name"]="compact500_xo900_80x50_hf1440_v11cd"
b["description"]=("(objective v11) COMPACT500 XO900 CD identity: the v11 CD brief with the envelope cut to "
  "500x500x500 mm and F_X 900 Hz (H corridor 60-90 pref 80 from 900 Hz, V 40-60 pref 50 from 1000 Hz, "
  "CD block band 900-8000 Hz); HF1440, band 350-8000. Own identity: never ranked against the 700 Hz "
  "600x480x480 v11 brief or any v7/v9/v10 brief.")
b["envelope"]={"max_depth_mm":500.0,"max_mouth_h_mm":500.0,"max_mouth_w_mm":500.0}
b["target"]["f0_hz"]=900.0; b["target"]["f0_v_hz"]=900.0
b["target"]["coverage_profile"]["h"][0]["hz"]=900
b["objective"]["cd"]["band_hz"]=[900.0,8000.0]
dump(R+"examples/briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml",[
 "COMPACT500 XO900 v11 CD brief (2026-11-20, owner request: 'maybe 500mm cubed max bounding box and designed",
 "around a 900 Hertz crossover'). Copied from cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml;",
 "changed keys ONLY: name, description, envelope 600x480x480 -> 500x500x500, target.f0_hz/f0_v_hz 700 -> 900,",
 "coverage_profile.h[0].hz 700 -> 900, objective.cd.band_hz [700,8000] -> [900,8000]. Key mapping follows",
 "docs/research/compact_horn_system_2026-11-19/compact_xo900_identity.md sec 1.1 (F_X = target.f0_hz).",
 "Loading rule at F_X 900: LFP20 <= 900/1.6 = 562.5 Hz and Re z >= 0.5 from 900 Hz (scalar_v7 _load_v7).",
 "NEW J IDENTITY: never rank against any other brief. Research: docs/research/favorites_2026-11-20/CROWE_X_FAVORITE_RESEARCH.md"],b)
# ---- configs
OPEN={"g_k":(1.0,5.0),"g_a_h_deg":(32.0,42.0),"g_a_v_deg":(20.0,30.0),"g_L_mm":(220.0,340.0),"g_s":(0.2,0.55),
      "g_n":(1.8,3.2),"g_r_lip_mm":(8.0,30.0),"g_wrap_deg":(50.0,160.0),"g_sf_ab":(0.7,0.9),"g_sf_amt":(0.12,0.38)}
FIXED=["g_q","g_sf_m","g_sf_n1","g_sf_n2","g_sf_start"]
def make(name, seed, brief, bounds_open, budget, desc, searched=True):
    c=copy.deepcopy(base); c["name"]=name; c["brief_file"]=brief
    c["seed_params"]={k:float(seed[k]) for k in sorted(seed)}
    bd={}
    for k in sorted(seed):
        if searched and k in bounds_open: bd[k]={"lo":bounds_open[k][0],"hi":bounds_open[k][1]}
        else: bd[k]={"lo":float(seed[k]),"hi":float(seed[k]),"search":False}
    c["bounds"]=bd; c["search"]["budget"]=budget; c["description"]=desc
    return c
D="examples/typologies/fav_crowe_2026-11-20/"
HDR=[f"Favorite follow-up (2026-11-20): Crowe-X on OS-SE CD, favorite {FAV_HASH} from runs/{FAV_RUN}.",
     "Research + rationale: docs/research/favorites_2026-11-20/CROWE_X_FAVORITE_RESEARCH.md; registry docs/favorites/FAVORITES.yaml."]
# k-attribution sweep: favorite knobs, k raised, L re-solved (CPU) so the mouth width stays 587 mm
for kk,L in [(2.0,274.2),(3.0,286.7),(4.0,298.2)]:
    s=dict(best); s["g_k"]=kk; s["g_L_mm"]=L; tag=f"k{int(kk)}"
    dump(R+D+f"favk__{tag}_hold_mouth.yaml", HDR+[f"k-attribution single screen solve: g_k {kk}, g_L_mm {L} (mouth W held at 587 mm), every other knob = favorite.",
         "Run with: hornlab-search run --config <this> --mode screen. Same v11 home brief: J comparable with the favorite's screen J 4.9965."],
         make(f"favk__{tag}_hold_mouth", s, HOME_BRIEF, {}, 1, f"k-attribution: favorite {FAV_HASH} with g_k {kk}, g_L_mm {L} (mouth held)", searched=False))
# home CMA search with k unlocked
s=dict(best); s["g_k"]=3.0; s["g_L_mm"]=286.7
dump(R+D+"fav__crowe_k_home.yaml", HDR+["CMA search, SAME v11 home brief as the favorite (J comparable with cd11c lanes at screen).",
     "New: g_k unlocked [1,5] (frozen at 1.0 in every earlier crowe lane), wider g_a_h/g_a_v/g_L/g_s/g_wrap.",
     "Seed: favorite knobs with g_k 3.0, g_L_mm 286.7 (CPU proxy: same 587 mm mouth, Re z 0.5-0.9 at 700-1000 Hz)."],
     make("fav__crowe_k_home", s, HOME_BRIEF, OPEN, 60, f"favorite {FAV_HASH} follow-up: k unlocked, home v11 brief, 60 valid"))
# compact 500 / XO 900 search
s=dict(best); s.update({"g_k":3.0,"g_L_mm":264.5,"g_s":0.30})
C=dict(OPEN); C["g_L_mm"]=(190.0,330.0); C["g_a_v_deg"]=(20.0,32.0); C["g_a_h_deg"]=(32.0,39.0); C["g_s"]=(0.2,0.45)
dump(R+D+"fav__crowe_c500_xo900.yaml", HDR+["CMA search on the NEW compact500_xo900 v11 brief (500x500x500, F_X 900 Hz): own J identity.",
     "Seed: favorite knobs with g_k 3.0, g_L_mm 264.5, g_s 0.30 (CPU fit: mouth 484 x 361 mm, depth 265 mm)."],
     make("fav__crowe_c500_xo900", s, C500_BRIEF, C, 60, f"favorite {FAV_HASH} compact variant: 500 mm cube, XO 900, k unlocked, 60 valid"))
print("ok")
