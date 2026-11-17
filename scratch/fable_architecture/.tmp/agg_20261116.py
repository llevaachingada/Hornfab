"""Read-only aggregate of 2026-11-16 runs: denominators + refusal sub-classification."""
import json, glob, os
from collections import Counter

ROOT = r"C:\Users\hunte\Hrns\hornlab-search\runs"
runs = []
for d in sorted(glob.glob(os.path.join(ROOT, "*"))):
    n = os.path.basename(d)
    if not (len(n) > 8 and n[:8] == "20261116" and "T" in n):
        continue
    nd = os.path.join(d, "search.ndjson")
    if not os.path.exists(nd):
        continue
    rows = []
    for line in open(nd, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    if rows:
        runs.append((n, rows))

att = uniq = ok = solved = cached = 0
kinds = Counter()
env_as_geom = 0
geom_other = 0
env_pre = 0
too_large = 0
solve_fail = 0
metrics = 0
exc = 0
for n, rows in runs:
    att += len(rows)
    uniq += len({r.get("design_hash") for r in rows})
    okr = [r for r in rows if r.get("ok")]
    ok += len(okr)
    cached += sum(1 for r in okr if r.get("cached"))
    solved += sum(1 for r in okr if not r.get("cached"))
    for r in rows:
        k = r.get("kind") or ""
        kinds[k or "<none>"] += 1
        e = str(r.get("error") or "")
        if k == "invalid_geometry" and "outside the brief envelope" in e:
            env_as_geom += 1
        elif k == "invalid_geometry":
            geom_other += 1
        elif k == "invalid_envelope":
            env_pre += 1
        elif k == "mesh_too_large":
            too_large += 1
        elif k == "solve_failed":
            solve_fail += 1
        elif k == "metrics_failed":
            metrics += 1
        elif k == "exception":
            exc += 1

print("runs_with_rows", len(runs))
print("attempts", att, "unique_designs", uniq)
print("ok_rows", ok, "cached_ok", cached, "solved_this_run(ok&!cached)", solved)
print("kinds", dict(kinds))
print("post_mesh_envelope_coded_as_invalid_geometry", env_as_geom)
print("other_invalid_geometry", geom_other)
print("pre_mesh_invalid_envelope", env_pre)
print("mesh_too_large", too_large, "solve_failed", solve_fail, "metrics_failed", metrics, "exception", exc)
print("valid_geometry_rate", round((att - env_as_geom - geom_other - env_pre) / att, 4) if att else None)
print("complete_bem_rate_of_attempts", round(solved / att, 4) if att else None)
