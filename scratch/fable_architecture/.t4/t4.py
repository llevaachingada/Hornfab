"""T4 / WP 0.5: does the generic-GRID pre-mesh extent estimate refuse horns the mesh would fit?
CPU only (gmsh), no solve. Usage: python t4.py <config.yaml> <n> [brief.yaml]"""
import sys, json, pathlib, tempfile, warnings
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from scipy.stats import qmc
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.generated import materialize, GeneratedSpace
from hornlab_search.design.generators import registry
from hornlab_search.mesh.build import build_mesh
from hornlab_search.search.evaluate import envelope_violation
from hornlab_search.types import Design

cfg_path, n = sys.argv[1], int(sys.argv[2])
kw = {"brief": sys.argv[3]} if len(sys.argv) > 3 else {}
cfg = load_config(cfg_path, **kw)
space = GeneratedSpace.from_config(cfg)
keys = space.keys()
X = qmc.Sobol(len(keys), seed=20261117).random(n)
ms = mesh_spec("screen", cfg)
rows = []
for x in X:
    knobs = space.knobs_from_unit(x)
    rec = {"knobs": knobs}
    try:
        params = materialize(space.gen, knobs, space.brief)
    except Exception as e:
        rec["status"] = "materialize_refused"; rec["err"] = str(e)[:120]; rows.append(rec); continue
    over = registry.envelope_overshoot_estimate(params, space.brief)
    rec["pre_overshoot"] = None if over is None else float(over)
    rec["pre_refused"] = bool(over is not None and over > 0)
    try:
        m = build_mesh(Design("FREEFORM", params), ms, cfg, pathlib.Path(tempfile.mkdtemp()), mode="screen")
        why = envelope_violation(m, cfg.brief)
        rec["post_ok"] = not why; rec["post_why"] = why
        rec["status"] = "meshed"
    except Exception as e:
        rec["status"] = "mesh_refused"; rec["err"] = f"{type(e).__name__}: {str(e)[:120]}"
    rows.append(rec)
pre = [r for r in rows if r.get("pre_refused")]
meshed_pre = [r for r in pre if r.get("status") == "meshed"]
false_ref = [r for r in meshed_pre if r.get("post_ok")]
admitted = [r for r in rows if r.get("status") == "meshed" and not r.get("pre_refused")]
missed = [r for r in admitted if not r.get("post_ok")]
summary = {"config": cfg_path, "brief": cfg.brief.get("name"), "n": n, "keys": keys,
           "materialize_refused": sum(r["status"] == "materialize_refused" for r in rows),
           "pre_refused": len(pre), "pre_refused_meshed": len(meshed_pre),
           "false_refusals(pre_refused_and_post_ok)": len(false_ref),
           "pre_admitted_meshed": len(admitted), "missed(pre_admitted_but_post_violates)": len(missed),
           "mesh_refused": sum(r["status"] == "mesh_refused" for r in rows)}
print(json.dumps(summary, indent=1))
out = pathlib.Path("scratch/fable_architecture/.t4") / (pathlib.Path(cfg_path).stem + ".json")
out.write_text(json.dumps({"summary": summary, "rows": rows}, default=str, indent=1))
