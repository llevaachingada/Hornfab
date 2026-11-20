"""Writes the FAV-001 8-hour variation night configs (2026-11-20 evening). Run from repo root."""
import yaml, copy, json, os
R=""
FAV="runs/20261120T084006Z-screen-fc4e18"
fav=json.load(open(FAV+"/best.json"))["params"]["grid"]["knobs"]
c500_best=None
for l in open("runs/20261120T205235Z-screen-f96805/search.ndjson"):
    r=json.loads(l)
    if r.get("ok") and r.get("design_hash")=="746d33134776": c500_best=r["params"]["grid"]["knobs"]
assert c500_best
base=yaml.safe_load(open("examples/typologies/cd_v11_completion_2026-11-20/cd11c__crowe_x_osse_cd.yaml"))
HOME="../../briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"
C500="../../briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml"
X900="../../briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml"
def dump(path, header, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as fh:
        fh.write("".join(f"# {l}\n" for l in header)); yaml.safe_dump(obj, fh, sort_keys=False, width=100)
# home XO900 brief: v11 home brief, only F_X 900 (+ H anchor, CD band)
b=yaml.safe_load(open("examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"))
b["name"]="room_landscape_80x50_900_hf1440_v11cd"
b["description"]=("(objective v11) HOME XO900 CD identity: the v11 home CD brief (600x480x480) with F_X 900 Hz "
  "(H corridor from 900, V from 1000, CD band 900-8000). Own identity: never ranked against the 700 Hz brief.")
b["target"]["f0_hz"]=900.0; b["target"]["f0_v_hz"]=900.0
b["target"]["coverage_profile"]["h"][0]["hz"]=900
b["objective"]["cd"]["band_hz"]=[900.0,8000.0]
dump("examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml",[
 "HOME XO900 v11 CD brief (2026-11-20 evening, research proposal 2 in docs/research/favorites_2026-11-20/).",
 "Copied from cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml; changed ONLY name, description,",
 "target.f0_hz/f0_v_hz 700 -> 900, coverage_profile.h[0].hz 700 -> 900, objective.cd.band_hz [700,8000] -> [900,8000].",
 "Envelope unchanged 600x480x480. NEW J IDENTITY: never rank against any other brief."],b)
BASEB={"g_k":(1.0,1.0),"g_a_h_deg":(32.0,42.0),"g_a_v_deg":(20.0,30.0),"g_L_mm":(220.0,340.0),"g_s":(0.2,0.55),
       "g_n":(1.8,3.2),"g_r_lip_mm":(8.0,30.0),"g_wrap_deg":(50.0,160.0),"g_sf_ab":(0.7,0.9),"g_sf_amt":(0.12,0.38),
       "g_q":(0.996,0.996),"g_sf_m":(4,4),"g_sf_n1":(1.8,1.8),"g_sf_n2":(7.0,7.0),"g_sf_start":(0.25,0.25)}
def make(name, seed, brief, over, budget, desc, sigma=0.1, rng=1234):
    c=copy.deepcopy(base); c["name"]=name; c["brief_file"]=brief
    c["seed_params"]={k:float(seed[k]) for k in sorted(seed)}
    bd={}
    B=dict(BASEB); B.update(over)
    for k in sorted(seed):
        lo,hi=B[k]
        if lo==hi: bd[k]={"lo":float(seed[k]),"hi":float(seed[k]),"search":False}
        else:
            assert lo<=seed[k]<=hi,(name,k,seed[k],lo,hi); bd[k]={"lo":float(lo),"hi":float(hi)}
    c["bounds"]=bd; c["search"]["budget"]=budget; c["search"]["sigma0"]=sigma; c["search"]["seed"]=rng
    c["description"]=desc; return c
D="examples/typologies/fav8_2026-11-20/"
H=["FAV-001 8-hour variation night (2026-11-20 evening, owner: 'queue up like 8 hours of solves related to variations",
   "on this FAV horn'). Plan + rationale: docs/research/favorites_2026-11-20/FAV8_NIGHT_PLAN.md"]
F=dict(fav)
lanes=[
 # (name, seed, brief, bound overrides, note)
 ("fav8__k1_cd_polish", F, HOME, {}, "k frozen at 1: polish FAV-001's directivity in a wider box (depth, flare, lip, angles)"),
 ("fav8__k_low", F, HOME, {"g_k":(1.0,1.6)}, "k in [1,1.6]: the low-k sweet spot between FAV-001 and the k~2 search best"),
 ("fav8__wide_h", dict(F,g_a_h_deg=38.0,g_a_v_deg=24.0), HOME, {"g_a_h_deg":(35.0,44.0),"g_a_v_deg":(20.0,27.0),"g_k":(1.0,1.6)}, "push toward a true 80x50: a_h up, a_v down (FAV-001 is ~69x58)"),
 ("fav8__sf_shape", F, HOME, {"g_sf_n1":(1.2,3.0),"g_sf_n2":(3.0,10.0),"g_sf_start":(0.1,0.5)}, "unlock superformula mouth-morph shape (n1, n2, onset); k 1"),
 ("fav8__lip_study", F, HOME, {"g_wrap_deg":(30.0,200.0),"g_r_lip_mm":(8.0,45.0),"g_q":(0.95,0.999)}, "mouth termination: lip wrap/radius and OSSE q; k 1"),
 ("fav8__deep", dict(F,g_L_mm=300.0,g_s=0.35), HOME, {"g_L_mm":(260.0,420.0),"g_k":(1.0,1.6),"g_s":(0.15,0.5),"g_n":(1.5,4.0)}, "use the unused depth (brief allows 480): L 260-420"),
 ("fav8__k_low_s2", F, HOME, {"g_k":(1.0,1.6)}, "seed-variance twin of fav8__k_low (CMA seed 2026)"),
 ("fav8__x900_k1", F, X900, {}, "FAV-001 at its natural crossover: home envelope, F_X 900, k 1"),
 ("fav8__x900_klow_sf", F, X900, {"g_k":(1.0,1.6),"g_sf_n1":(1.2,3.0),"g_sf_n2":(3.0,10.0),"g_sf_start":(0.1,0.5)}, "home XO900 with low k + superformula shape"),
 ("fav8__c500_polish", dict(c500_best), C500, {"g_k":(1.0,2.2),"g_L_mm":(190.0,330.0),"g_a_h_deg":(32.0,39.0),"g_a_v_deg":(20.0,32.0),"g_s":(0.2,0.45)}, "compact 500/900: continue from verify-best 746d33134776"),
 ("fav8__c500_wide_h", dict(c500_best,g_a_h_deg=36.0), C500, {"g_k":(1.0,2.2),"g_L_mm":(190.0,330.0),"g_a_h_deg":(34.0,41.0),"g_a_v_deg":(20.0,32.0),"g_s":(0.2,0.45)}, "compact: hold H wider at HF (it narrows to ~58 deg)"),
 ("fav8__c500_sf", dict(c500_best), C500, {"g_k":(1.0,2.2),"g_L_mm":(190.0,330.0),"g_a_h_deg":(32.0,39.0),"g_a_v_deg":(20.0,32.0),"g_s":(0.2,0.45),"g_sf_n1":(1.2,3.0),"g_sf_n2":(3.0,10.0),"g_sf_start":(0.1,0.5)}, "compact + superformula shape"),
]
for name,seed,brief,over,note in lanes:
    rng=2026 if name.endswith("_s2") else 1234
    dump(D+name+".yaml", H+[note], make(name, seed, brief, over, 80, f"FAV-001 variation: {note}; 80 valid", rng=rng))
print("\n".join(l[0] for l in lanes))
