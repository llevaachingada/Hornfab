"""Assemble the B1 selection table (read-only): v7 top five + v9 corridor top five, union/dedup.

Inputs are all stored artifacts produced earlier in this directory:
  home_brief_rows.json            - best ok row per design hash, home brief (b1_compute.py)
  v9_home_pool_v1000/replay_matrix.csv - WP3 tool replay of those designs under the v9 corridor
  snap/<run>/config.yaml          - frozen config for the finalist mesh estimate

Run:  .venv\\Scripts\\python.exe scratch/fable_architecture/.b1/b1_table.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import csv  # noqa: E402

from hornlab_search.config import load_config, mesh_spec, mode_freqs  # noqa: E402

V9_CSV = HERE / "v9_home_pool_v1000" / "replay_matrix.csv"


def main() -> int:
    rows = json.loads((HERE / "home_brief_rows.json").read_text(encoding="utf-8"))["rows"]
    v7 = sorted(rows, key=lambda r: r["objective"])
    # dedup by design hash, keep best (rows are already best-per-(run,hash); a hash can appear in
    # more than one run)
    seen, v7u = set(), []
    for r in v7:
        if r["design_hash"] in seen:
            continue
        seen.add(r["design_hash"])
        v7u.append(r)

    v9rows = list(csv.DictReader(V9_CSV.open(encoding="utf-8")))
    v9rows.sort(key=lambda r: float(r["J"]))
    seen9, v9u = set(), []
    for r in v9rows:
        h = r["design_hash"]
        if h in seen9:
            continue
        seen9.add(h)
        v9u.append(r)

    print("=== stored v7 top 10 under the home brief ===")
    for i, r in enumerate(v7u[:10], 1):
        print(f"{i:>2} {r['design_hash']} {r['objective']:.4f} {r['run']} {r['config_name']}")
    print("\n=== v9 corridor (h90_70 v1000) top 10 ===")
    for i, r in enumerate(v9u[:10], 1):
        print(f"{i:>2} {r['design_hash']} {float(r['J']):.4f} {r['run_dir'].split(chr(92))[-1]} "
              f"{r['design']}  v7={r['stored_J']} n_band={r['n_solved_in_band']}")

    top7 = v7u[:5]
    top9 = v9u[:5]
    union = []
    for r in top9:
        h = r["design_hash"]
        hit = next((x for x in v7u if x["design_hash"] == h), None)
        union.append({"hash": h, "source": "v9", "v9": r, "v7": hit})
    have = {u["hash"] for u in union}
    for r in top7:
        if r["design_hash"] in have:
            # mark the v9 entry as an overlap instead of adding a duplicate
            for u in union:
                if u["hash"] == r["design_hash"]:
                    u["source"] = "both"
            continue
        union.append({"hash": r["design_hash"], "source": "v7",
                      "v9": next((x for x in v9u if x["design_hash"] == r["design_hash"]), None),
                      "v7": r})
        have.add(r["design_hash"])
    # top up from v7 until ten
    for r in v7u:
        if len(union) >= 10:
            break
        if r["design_hash"] in have:
            continue
        have.add(r["design_hash"])
        union.append({"hash": r["design_hash"], "source": "topup",
                      "v9": next((x for x in v9u if x["design_hash"] == r["design_hash"]), None),
                      "v7": r})
    union = union[:10]

    print("\n=== union (v9 top5 + v7 top5, dedup, top-up) ===")
    out = []
    for i, u in enumerate(union, 1):
        v7r, v9r = u["v7"], u["v9"]
        run = (v7r or {}).get("run") or v9r["run_dir"].replace("\\", "/").split("/")[-1]
        cfg_path = HERE / "snap" / run / "config.yaml"
        cfg = load_config(cfg_path)
        ms = mesh_spec("finalist", cfg)
        rec = {
            "n": i, "design_hash": u["hash"], "run": run, "source": u["source"],
            "config": cfg.name,
            "v7_J": float(v7r["objective"]) if v7r else None,
            "v7_run": (v7r or {}).get("run"),
            "v7_tri": (v7r or {}).get("n_triangles"),
            "v7_dof": (v7r or {}).get("n_dof"),
            "v9_J": float(v9r["J"]) if v9r else None,
            "v9_stored_J": v9r["stored_J"] if v9r else None,
            "v9_run": v9r["run_dir"].replace("\\", "/").split("/")[-1] if v9r else None,
            "v9_n_band": v9r["n_solved_in_band"] if v9r else None,
            "v9_n_total": v9r["n_solved_total"] if v9r else None,
            "freqs_screen": len(mode_freqs("screen", cfg)),
            "freqs_verify": len(mode_freqs("verify", cfg)),
            "freqs_finalist": len(mode_freqs("finalist", cfg)),
            "dof_cap_screen": int(cfg.mesh.dof_cap("screen")),
            "dof_cap_finalist": int(cfg.mesh.dof_cap("finalist")),
            "max_triangles_finalist": int(ms.max_triangles),
            "f_max_finalist": float(ms.f_max_hz),
            "epw": float(ms.epw),
            "quadrants": str(ms.quadrants),
            "balloon_finalist": int(cfg.solve.balloon_points("finalist")),
            "backend": cfg.solve.backend,
        }
        out.append(rec)
        print(json.dumps(rec))
    (HERE / "b1_selection.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {HERE / 'b1_selection.json'} ({len(out)} designs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
