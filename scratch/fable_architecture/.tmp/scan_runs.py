"""Read-only bounded scan of runs/*/search.ndjson to quantify refusal categories.
Writes only under scratch/fable_architecture/.tmp/. No imports of mesh/solve/search."""
import json, os, sys, glob
from collections import Counter

ROOT = r"C:\Users\hunte\Hrns\hornlab-search\runs"
rows_out = []
for d in sorted(glob.glob(os.path.join(ROOT, "*"))):
    if not os.path.isdir(d):
        continue
    name = os.path.basename(d)
    if not (len(name) > 8 and name[:8].isdigit() and "T" in name):
        continue
    rj = os.path.join(d, "run.json")
    nd = os.path.join(d, "search.ndjson")
    rec = {"run": name, "mode": None, "status": None, "config": None,
           "rows": 0, "kinds": Counter(), "err_prefix": Counter(), "ok": 0,
           "objective_version": None, "family": None}
    try:
        with open(rj, "r", encoding="utf-8") as f:
            j = json.load(f)
        rec["mode"] = j.get("mode"); rec["status"] = j.get("status")
        rec["config"] = j.get("config_name"); rec["objective_version"] = j.get("objective_version")
        rec["family"] = j.get("family")
    except Exception as e:
        rec["status"] = f"RUNJSON_ERR:{e}"
    try:
        with open(nd, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                rec["rows"] += 1
                k = r.get("kind") or ""
                rec["kinds"][k or "<none>"] += 1
                if r.get("ok"):
                    rec["ok"] += 1
                err = str(r.get("error") or "")
                if err:
                    # first 60 chars normalize
                    rec["err_prefix"][err[:70]] += 1
    except FileNotFoundError:
        pass
    except Exception as e:
        rec["status"] = f"{rec['status']}|ND_ERR:{e}"
    rows_out.append(rec)

def top(c, n=8):
    return c.most_common(n)

out = []
for r in rows_out:
    out.append({
        "run": r["run"], "mode": r["mode"], "status": r["status"], "config": r["config"],
        "objver": r["objective_version"], "family": r["family"],
        "rows": r["rows"], "ok": r["ok"],
        "kinds": dict(r["kinds"]),
        "top_err": top(r["err_prefix"], 6),
    })
with open(os.path.join(os.path.dirname(__file__), "run_scan.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)

# Aggregate by config name
agg = {}
for r in rows_out:
    key = str(r["config"])
    a = agg.setdefault(key, {"runs": 0, "rows": 0, "ok": 0, "kinds": Counter(),
                             "objver": set(), "mode": Counter()})
    a["runs"] += 1; a["rows"] += r["rows"]; a["ok"] += r["ok"]
    a["kinds"].update(r["kinds"]); a["mode"][r["mode"]] += 1
    if r["objective_version"] is not None:
        a["objver"].add(r["objective_version"])
aggo = {}
for k, a in agg.items():
    aggo[k] = {"runs": a["runs"], "rows": a["rows"], "ok": a["ok"],
               "objver": sorted(x for x in a["objver"] if isinstance(x, int)),
               "mode": dict(a["mode"]), "kinds": dict(a["kinds"])}
with open(os.path.join(os.path.dirname(__file__), "run_agg_by_config.json"), "w", encoding="utf-8") as f:
    json.dump(aggo, f, indent=1, sort_keys=True)

print("runs scanned:", len(rows_out))
print("with rows:", sum(1 for r in rows_out if r["rows"]))
for k, a in sorted(aggo.items(), key=lambda kv: -kv[1]["rows"]):
    print(f"{str(k)[:42]:42s} runs={a['runs']:3d} rows={a['rows']:5d} ok={a['ok']:5d} modes={a['mode']} kinds={a['kinds']}")
