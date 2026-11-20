"""Writes the throat-loading lanes (2026-11-20 evening): V-only k via throat_hv_ratio and a 2-inch exit. Repo root."""
import yaml, copy, json, os, math
import importlib.util
spec=importlib.util.spec_from_file_location("w8","docs/research/favorites_2026-11-20/cpu/write_fav8.py")
src=open("docs/research/favorites_2026-11-20/cpu/write_fav8.py").read().split("D=\"examples/typologies/fav8_2026-11-20/\"")[0]
exec(src)   # dump, make, BASEB, fav, c500_best, HOME, C500 (also re-writes the identical home XO900 brief)
F2="../../briefs/hf2in_2026-11-20/room_landscape_80x50_700_hf2in_v11cd.yaml"
C2="../../briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd.yaml"
F11_2IN=round(1.8412*343.0/(2*math.pi*0.0254),1)   # 3957 Hz, 2-inch exit first cross-mode
for src_b,dst,name in [("examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml",F2,"room_landscape_80x50_700_hf2in_v11cd"),
                       ("examples/briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml",C2,"compact500_xo900_80x50_hf2in_v11cd")]:
    b=yaml.safe_load(open(src_b)); b["name"]=name
    b["driver"]["exit_radius_mm"]=25.4
    b["target"]["loaded_hi_hz"]=F11_2IN
    b["description"]=b["description"].replace("HF1440","2-INCH EXIT (r0 25.4 mm)")+" DRIVER-SIZE STUDY: 2-inch exit."
    dump("examples/briefs/hf2in_2026-11-20/"+os.path.basename(dst),[
      f"2-INCH COMPRESSION-DRIVER study brief (2026-11-20 evening, owner: 'also consider a two inch compression driver size').",
      f"Copied from {src_b}; changed ONLY name, description, driver.exit_radius_mm 18.0 -> 25.4 (50.8 mm exit),",
      f"target.loaded_hi_hz -> {F11_2IN} (first cross-mode 1.8412 c / (2 pi a) of a 25.4 mm exit; scalar_v7 loaded window rule).",
      "driver.exit_angle_deg stays 2.0 (ASSUMED; no specific 2-inch driver chosen). Ideal uniform-velocity cap source:",
      "real 2-inch driver response/phase plug not modeled. NEW J IDENTITY: never rank against the 1.4-inch briefs."],b)
BASEB["g_throat_hv_ratio"]=(1.0,1.0)
D="examples/typologies/favL_2026-11-20/"
H=["Throat-loading lanes for FAV-001 (2026-11-20 evening, owner: improve throat loading without losing the directivity).",
   "Rationale: docs/research/favorites_2026-11-20/THROAT_LOADING_LEVERS.md. Levers: V-only k via the existing",
   "g_throat_hv_ratio (k(phi) = k*rho**(-cos2phi/2); k=sqrt(K), rho=K -> k_H 1, k_V K) and a 2-inch exit (new brief)."]
FV=dict(fav, g_throat_hv_ratio=1.0)
kv=lambda K: {"g_k":math.sqrt(K),"g_throat_hv_ratio":K}
BOX={"g_a_h_deg":(32.0,38.0),"g_a_v_deg":(20.0,32.0),"g_L_mm":(220.0,320.0),"g_s":(0.2,0.47)}
singles=[("favL1__kv3_single",dict(FV,**kv(3.0),g_L_mm=260.4),HOME,"single: FAV-001 knobs, V-only k (k_H 1, k_V 3)"),
         ("favL1__2in_single",dict(FV),F2,"single: FAV-001 knobs exactly, 2-inch exit"),
         ("favL1__2in_kv2_single",dict(FV,**kv(2.0),g_L_mm=259.1),F2,"single: 2-inch exit + V-only k 2")]
for n,s,b,note in singles:
    dump(D+n+".yaml",H+[note+". Run: hornlab-search run --config <this> --mode screen."],make(n,s,b,{},1,note))
lanes=[("favL__kv_home",dict(FV,**kv(2.0)),HOME,dict(BOX,g_k=(1.0,2.0),g_throat_hv_ratio=(1.0,4.0)),"CMA home 1.4in 700 Hz: V-only/asymmetric k (k in [1,2], rho in [1,4])"),
       ("favL__2in_home",dict(FV),F2,dict(BOX,g_k=(1.0,1.6),g_throat_hv_ratio=(1.0,4.0)),"CMA home 2-inch 700 Hz: k [1,1.6], rho [1,4], seeded at FAV-001"),
       ("favL__2in_c500",dict(c500_best,g_throat_hv_ratio=1.0,g_k=1.2,g_L_mm=255.0),C2,{"g_k":(1.0,2.2),"g_throat_hv_ratio":(1.0,4.0),"g_L_mm":(190.0,290.0),"g_a_h_deg":(32.0,37.0),"g_a_v_deg":(20.0,31.0),"g_s":(0.2,0.38)},"CMA compact500 XO900 2-inch: seeded at 746d33134776 with k 1.2")]
for n,s,b,o,note in lanes:
    c=make(n,s,b,o,80,note); c["search"]["max_attempts"]=450
    dump(D+n+".yaml",H+[note],c)
print("ok", F11_2IN)
