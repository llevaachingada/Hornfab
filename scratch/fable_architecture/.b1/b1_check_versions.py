import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sel = json.loads((Path(__file__).resolve().parent / "b1_selection.json").read_text(encoding="utf-8"))
for rec in sel:
    run = rec["run"]
    h = rec["design_hash"]
    vers, oks = set(), []
    for line in (REPO / "runs" / run / "search.ndjson").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("design_hash") == h:
            vers.add(r.get("objective_version"))
            oks.append((r.get("ok"), r.get("objective")))
    rj = json.loads((REPO / "runs" / run / "run.json").read_text(encoding="utf-8"))
    print(f"{h} {run} row_versions={sorted(v for v in vers if v is not None)} "
          f"run_version={rj.get('objective_version')} rows={oks}")
