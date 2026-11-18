"""Drive the EXISTING WP3 replay tool over the stored home-brief designs (read-only, CPU).

No scoring code is re-implemented here: this only builds the design list and calls
``tools.analysis.brief_truth_replay.scenarios`` (the WP3 tool), which dispatches every J to the
canonical v9 scorer and hashes every read before/after. Stored responses are never written.

Run:  .venv\\Scripts\\python.exe scratch/fable_architecture/.b1/b1_v9_score.py \
          --brief <corridor.yaml> --out <dir> [--limit N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def load_tool():
    path = REPO / "tools" / "analysis" / "brief_truth_replay.py"
    spec = importlib.util.spec_from_file_location("brief_truth_replay", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rows", type=Path, default=HERE / "home_brief_rows.json")
    ap.add_argument("--limit", type=int, default=0, help="score only the first N (benchmark)")
    ap.add_argument("--offset", type=int, default=0)
    a = ap.parse_args()

    rows = json.loads(a.rows.read_text(encoding="utf-8"))["rows"]
    seen, designs = set(), []
    for r in rows:
        key = (r["run"], r["design_hash"])
        if key in seen:
            continue
        seen.add(key)
        run = r["run"]
        # Prefer a frozen snapshot (stable manifests + junctioned immutable design tree) so the
        # live night queue cannot change a hashed source mid-run.
        snap = HERE / "snap" / run
        run_path = f"scratch/fable_architecture/.b1/snap/{run}" if snap.is_dir() else f"runs/{run}"
        base = REPO / run_path if not Path(run_path).is_absolute() else Path(run_path)
        rp = base / "designs" / r["design_hash"] / "response.npz"
        if not rp.is_file():
            continue
        designs.append({"label": f"{run}:{r['design_hash']}",
                        "run": run_path, "design_hash": r["design_hash"],
                        "own_cell": None})
    designs.sort(key=lambda d: d["label"])
    designs = designs[a.offset:]
    if a.limit:
        designs = designs[: a.limit]
    print(f"[b1_v9_score] {len(designs)} stored designs -> {a.brief.name}", flush=True)

    btr = load_tool()
    prov = btr.provenance()
    t0 = time.perf_counter()
    btr.scenarios([a.brief], designs, a.out, prov)
    print(f"[b1_v9_score] {time.perf_counter() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
