"""Deliverable validation: YAML parses, ids are unique vs the live night, argv paths exist,
design rows resolve to ok rows, and the B1 mesh job scope is exactly the five fold-warm probes."""
from __future__ import annotations

import csv
import json
import yaml
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NIGHT = REPO / "runs" / "nights" / "cd_rrect_2026-11-17.yaml"
FILES = [HERE / "b1_night_insert.yaml", HERE / "b1_mesh_night_insert.yaml"]
EXCLUDE = {"2f7307c06023", "507e7257c091", "ced63c6a01a1", "688ffe811b6a", "78f599e8a1d2"}

live_ids = [j["id"] for j in yaml.safe_load(NIGHT.read_text(encoding="utf-8"))["jobs"]]
print("live jobs:", len(live_ids))
csv_rows = list(csv.DictReader((HERE / "b1_designs.csv").open(encoding="utf-8")))
csv_pairs = {(r["run"], r["design"]) for r in csv_rows}
print("design rows:", len(csv_rows), "unique:", len(csv_pairs))

for path in FILES:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    ids = [j["id"] for j in doc["jobs"]]
    print(f"\nyaml ok: {path.name}: night={doc['night']} lane={doc['lane']} jobs={len(ids)}")
    print("  ids:", ids)
    print("  collisions with live:", sorted(set(ids) & set(live_ids)))
    for job in doc["jobs"]:
        argv = [str(t) for t in job["argv"]]
        paths = [t for t in argv if t.endswith((".exe", ".py", ".csv", ".yaml", ".yml", ".json"))
                 or t.startswith("scratch/")]
        for p in paths:
            print(f"  argv path {p}: exists={(REPO / p).exists()}")
        if "--design" in argv:
            spec = argv[argv.index("--design") + 1]
            run, _, h = spec.rpartition(":")
            ok = False
            for line in (REPO / run / "search.ndjson").read_text(encoding="utf-8").splitlines():
                row = json.loads(line) if line.strip() else {}
                if row.get("design_hash") == h and row.get("ok"):
                    ok = True
                    break
            print(f"  design {run}:{h} ok_row={ok} fold_warm_scope={h in EXCLUDE}")

print("\nmesh job ids not in the five-design scope:",
      [i for i in yaml.safe_load(FILES[1].read_text(encoding="utf-8"))["jobs"]
       if i["argv"][i["argv"].index("--design") + 1].rpartition(":")[2] not in EXCLUDE])

# The B1 mesh contract: every stored reference row's solve hash must be this config's screen
# solve spec (same grid, backend, observation).
import sys  # noqa: E402
sys.path.insert(0, str(REPO))
from hornlab_search.config import load_config, solve_spec  # noqa: E402

print("\nsame-screen-grid contract (stored solve_hash == config screen solve hash):")
cfgs: dict = {}
for row in csv_rows:
    run, h = row["run"], row["design"]
    if run not in cfgs:
        cfgs[run] = load_config(REPO / run / "config.yaml")
    want = solve_spec("screen", cfgs[run]).hash()
    got = None
    for line in (REPO / run / "search.ndjson").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("design_hash") == h and rec.get("ok"):
            got = rec.get("solve_hash")
            break
    print(f"  {h}: {got} == {want} -> {got == want}")
