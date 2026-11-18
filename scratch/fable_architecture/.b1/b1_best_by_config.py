import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = json.loads((HERE / "home_brief_rows.json").read_text(encoding="utf-8"))["rows"]
best = {}
for r in rows:
    c = r["config_name"]
    if c not in best or r["objective"] < best[c]["objective"]:
        best[c] = r
for c, r in sorted(best.items(), key=lambda kv: kv[1]["objective"]):
    print(f"{r['objective']:.4f}  {c:42s} {r['run']}  {r['design_hash']}")
