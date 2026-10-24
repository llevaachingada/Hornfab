import json, glob, os, sys
root = sys.argv[1]
rows = []
for p in glob.glob(os.path.join(root, "runs", "*", "best.json")):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    t = d.get("terms") or (d.get("evaluation") or {}).get("terms")
    if not t:
        continue
    rows.append((os.path.basename(os.path.dirname(p)), d.get("objective", t.get("total")), t))
rows.sort(key=lambda r: r[0])
W = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5}
for name, J, t in rows[-25:]:
    w = {k: round(W.get(k, 0) * float(t.get(k, 0)), 2) for k in W}
    w["load"] = round(float(t.get("load", 0)), 3)
    print(name[:60], "J=", round(float(J), 2) if J is not None else None, w)
