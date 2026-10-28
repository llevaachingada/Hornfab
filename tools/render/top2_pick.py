import json, re
from pathlib import Path
R = Path("runs"); N = R / "nights"
TYPO = [("CD-throat hybrid (osse_rollback)", r"^(hy|po)__"), ("Quatrefoil Salmon", r"^qf__"),
        ("Chanterelle (Salmon)", r"chanterelle"), ("R-OSSE morph", r"rosse_morph"),
        ("ATH core / ridge", r"ath_core|core_law"), ("ATH twin-ray", r"twinray"),
        ("Biradial (Keele)", r"biradial"), ("OSSE-H / hypex-V", r"hypex"),
        ("OSSE", r"osse_baseline|osse_morph|osse_b1w"), ("Le Cleac'h", r"lecleach"),
        ("Salmon rows / ripple", r"salmon")]
def rows(p):
    for l in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try: yield json.loads(l)
        except ValueError: pass
def brief(rd):
    try: return json.loads((rd/"run.json").read_text())["config"]["brief"]["name"]
    except Exception: return "?"
cands = {}
for s in N.glob("*/summary.jsonl"):
    for j in rows(s):
        if not j.get("run_dir"): continue
        rd = Path(j["run_dir"]); nd = rd/"search.ndjson"
        if not nd.exists(): continue
        typ = next((t for t, rx in TYPO if re.search(rx, j["id"])), None)
        if not typ: continue
        best = min((r for r in rows(nd) if r.get("ok") and float(r["objective"]) < 900), key=lambda r: float(r["objective"]), default=None)
        if best and (rd/"designs"/best["design_hash"]/"mesh.msh").exists():
            cands.setdefault(typ, []).append(dict(J=float(best["objective"]), job=j["id"], h=best["design_hash"], rd=str(rd), brief=brief(rd)))
out = []
for typ, _ in TYPO:
    seen = set()
    for c in sorted(cands.get(typ, []), key=lambda c: c["J"]):
        if c["h"] in seen: continue
        seen.add(c["h"]); out.append(dict(typ=typ, **c))
        if len(seen) == 2: break
for o in out: print(f'{o["typ"]:34s} {o["J"]:7.3f} {o["job"]:34s} {o["brief"]}')
Path("scratch/top2/picks.json").write_text(json.dumps(out, indent=1))
