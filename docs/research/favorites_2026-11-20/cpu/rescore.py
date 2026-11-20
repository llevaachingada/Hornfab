import yaml, copy, sys, os
from hornlab_search.objective.replay import replay_run_dir
S=sys.argv[1]
base=yaml.safe_load(open("examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml"))
runs={"crowe_x_osse":"runs/20261120T185832Z-verify-e5de4a","ext_throat":"runs/20261120T185416Z-verify-9d392f",
      "osse_fold":"runs/20261120T185520Z-verify-fec2a6","osse_morph":"runs/20261120T185618Z-verify-f4c824",
      "ath_core_petal":"runs/20261120T185717Z-verify-7fb1b5"}
def variant(name, fx=None, load_w=None):
    b=copy.deepcopy(base)
    if fx:
        b["target"]["f0_hz"]=fx; b["target"]["f0_v_hz"]=fx
        b["target"]["coverage_profile"]["h"][0]["hz"]=fx
        b["target"]["coverage_profile"]["v"][0]["hz"]=max(fx,1000.0)
        b["objective"]["cd"]["band_hz"][0]=fx
    if load_w is not None: b["weights"]["load"]=load_w
    p=os.path.join(S,f"brief_{name}.yaml"); yaml.safe_dump(b,open(p,"w")); return p
vs=[("as_brief",None,None),("fx800",800.0,None),("fx900",900.0,None),("fx1000",1000.0,None),("load0",None,0.0)]
print("variant   " + " ".join(f"{k:>15s}" for k in runs))
for name,fx,lw in vs:
    p=variant(name,fx,lw); row=[]
    for k,rd in runs.items():
        r=replay_run_dir(rd, brief=p)
        J=getattr(r,"j",None) or getattr(r,"total",None)
        if J is None: J=r.terms.get("total") if hasattr(r,"terms") else None
        L=r.terms.get("load") if hasattr(r,"terms") else None
        row.append(f"{J:7.3f} (L{L:5.2f})")
    print(f"{name:9s} "+" ".join(f"{x:>15s}" for x in row))
