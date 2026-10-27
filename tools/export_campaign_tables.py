"""Export compact, analysis-ready tables from a campaign's runs (no meshes, no raw acoustic responses).

Reads the run directories named in night ``summary.jsonl`` files and writes, under ``--out``:

* ``cells_summary.csv``  one row per cell: family, seed J, best J, refusal rate, evals;
* ``evals.csv``          one row per evaluation: J, the eight normalised terms, per-eval scalar metrics,
                         flattened design parameters (``p_<name>``), plus the per-frequency beamwidth/DI
                         series as JSON columns -- enough to re-score or fit surrogates without CUDA;
* ``best_designs.json``  the best design's parameters and terms per cell;
* ``README.md``          column definitions and caveats.

Usage::

    .venv\\Scripts\\python.exe tools\\export_campaign_tables.py --night runs/nights/v4_overnight_2026-10-27 --out docs/data/campaign_v4_2026-10-27
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

TERMS = ["cov", "rip", "di", "dislope", "flat", "load", "distd", "diag", "penalty", "total"]


def _rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--night", type=Path, required=True, help="night folder containing summary.jsonl")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    cells = []
    for line in (args.night / "summary.jsonl").read_text(encoding="utf-8").splitlines():
        j = json.loads(line)
        if j.get("run_dir"):
            cells.append((j["id"].split("__", 1)[1], Path(j["run_dir"])))

    all_rows, summary, best_out, pkeys = [], [], {}, set()
    for cell, rd in cells:
        nd = _rows(rd / "search.ndjson")
        ok = [r for r in nd if r.get("ok")]
        best = min(ok, key=lambda r: r["objective"]) if ok else None
        seed = nd[0]
        summary.append({
            "cell": cell, "family": (best or seed).get("family"), "evals": len(nd), "refused": len(nd) - len(ok),
            "refused_pct": round(100 * (len(nd) - len(ok)) / max(len(nd), 1), 1),
            "seed_J": round(seed["objective"], 4) if seed.get("ok") else None,
            "best_J": round(best["objective"], 4) if best else None,
            "best_eval_no": nd.index(best) + 1 if best else None, "run_dir": rd.name,
        })
        if best:
            best_out[cell] = {"design_hash": best["design_hash"], "objective": best["objective"],
                              "params": best["params"], "terms": best["terms"]}
        for i, r in enumerate(nd):
            m = r.get("metrics") or {}
            row = {"cell": cell, "eval": i + 1, "ok": bool(r.get("ok")), "cached": r.get("cached"),
                   "family": r.get("family"), "design_hash": r.get("design_hash"),
                   "J": r.get("objective"), "objective_version": r.get("objective_version"),
                   "error": (r.get("error") or "")[:120], "n_dof": r.get("n_dof"), "seconds": r.get("seconds")}
            for t in TERMS:
                row[f"term_{t}"] = (r.get("terms") or {}).get(t)
            for k in ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db", "on_axis_db"):
                if k in m:
                    row[k] = json.dumps([round(x, 3) if isinstance(x, float) else x for x in m[k]])
            for k, v in (r.get("params") or {}).items():
                row[f"p_{k}"] = v
                pkeys.add(f"p_{k}")
            all_rows.append(row)

    base = ["cell", "eval", "ok", "cached", "family", "design_hash", "J", "objective_version", "error", "n_dof",
            "seconds"] + [f"term_{t}" for t in TERMS] + ["freqs_hz", "bw_h_deg", "bw_v_deg", "di_db",
                                                         "ripple_h_db", "ripple_v_db", "on_axis_db"]
    cols = base + sorted(pkeys)
    with open(args.out / "evals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(all_rows)
    with open(args.out / "cells_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    (args.out / "best_designs.json").write_text(json.dumps(best_out, indent=1), encoding="utf-8")
    (args.out / "README.md").write_text(README, encoding="utf-8")
    print(f"{len(summary)} cells, {len(all_rows)} evaluations -> {args.out}")
    return 0


README = """# Campaign tables (objective v4)

Exported by `tools/export_campaign_tables.py` from the screen-tier runs. No meshes, no raw responses.

* `cells_summary.csv` - one row per typology cell. `refused` = candidates the search refused (invalid geometry/envelope);
  `best_eval_no` is the 1-based row in `evals.csv` for that cell.
* `evals.csv` - one row per evaluation. `J` is the v4 objective; `term_*` are the **tolerance-normalised** terms
  (raw = term x tolerance, tolerances in `docs/evidence/OBJECTIVE_V4_TOLERANCES.md`; `J = sum(weight x term) + penalty`,
  weights in each cell's brief under `examples/briefs/campaign_2026-10-26_v4/`). `p_*` are the design parameters
  (blank when not used by that family). `freqs_hz`, `bw_h_deg`, `bw_v_deg`, `di_db`, `ripple_*`, `on_axis_db` are JSON
  arrays on the 12-point screen grid (500-10k Hz). Refused rows have blank J/terms.
* `best_designs.json` - best parameters and terms per cell.

Caveats: J is comparable only WITHIN a cell (each brief weights the terms differently). The screen grid has 12 frequency
points, so dispersion between them is interpolated. Cached rows (`cached=True`) re-use an earlier solve of the same geometry.
Each cell's search is CMA-ES with one fixed seed; a "resume" extends the same run, so later rows are later CMA generations.
The solve cache itself (needed to re-score under a different objective without CUDA) is NOT included here.
"""

if __name__ == "__main__":
    raise SystemExit(main())
