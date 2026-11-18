"""2026-11-18 owner-directed reuse pass (Fable WP 1.4/1.5). Scores a SAMPLE of stored designs under
one brief identity using the canonical replay functions (hornlab_search.objective.replay) — the
same functions and row schema as tools/analysis/rescore_identity.py, restricted to the sample.
No BEM solve, no mesher call, no runs/ write; reads stored responses only.

Row schema matches rescore() plus "reasons" from the sample selection. Summary carries the score
identity (same fields as the fixed rescore summary) and a coverage marker so nobody mistakes a
sample column for a full-fleet column.

Usage:
  python sample_rescore.py --brief <brief.yaml> --sample <sample.json> --out <new_dir>
"""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from hornlab_search.objective.replay import (SCORE_CODE_VERSION, _hash as _replay_hash,  # noqa: E402
                                             load_brief_context, replay_run_dir)


def row_identity(r, brief, objective_block) -> str:
    return _replay_hash({
        "kind": "score",
        "score_code": SCORE_CODE_VERSION,
        "objective_version": r.objective_version,
        "weights": r.weights,
        "objective_block": objective_block,
        "brief_hash": (brief.brief_hash() if brief is not None else None),
        "brief_name": (brief.name if brief is not None else None),
    })


def _counts(it):
    c: dict = {}
    for k in it:
        c[k] = c.get(k, 0) + 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brief", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sample = json.loads(Path(a.sample).read_text(encoding="utf-8"))
    runs_root = Path("runs")
    b = load_brief_context(a.brief)
    rows, identity_ids = [], set()

    def lane_of(run: Path) -> str:
        try:
            import yaml
            raw = yaml.safe_load((run / "config.yaml").read_text(encoding="utf-8")) or {}
            return str(raw.get("name") or run.name)
        except Exception:  # noqa: BLE001
            return run.name

    for sel in sample["selection"]:
        run = runs_root / sel["run"]
        lane = lane_of(run)
        try:
            r = replay_run_dir(run, sel["design_hash"], brief=b, config_path=run / "config.yaml")
            rows.append({"run": sel["run"], "lane": lane, "design_hash": sel["design_hash"],
                         "status": r.status, "j": r.j, "score_id": r.score_id,
                         "stored_j": r.stored_j, "parity_delta": r.parity_delta,
                         "reasons": list(r.reasons) + sel.get("reasons", [])})
            if r.j is not None:
                identity_ids.add(row_identity(r, b, b.objective_block))
        except Exception as exc:  # noqa: BLE001 - reported, never hidden
            rows.append({"run": sel["run"], "lane": lane, "design_hash": sel["design_hash"],
                         "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}", "reasons": sel.get("reasons", [])})

    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: output dir {out} exists and is not empty")
    out.mkdir(parents=True)
    with (out / "rescore.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=float) + "\n")
    best: dict = {}
    for r in rows:
        j = r.get("j")
        if j is None or not math.isfinite(float(j)):
            continue
        if r["lane"] not in best or j < best[r["lane"]]["j"]:
            best[r["lane"]] = {"j": float(j), "run": r["run"], "design_hash": r["design_hash"]}
    summary = {"brief": str(a.brief), "objective_version": int(b.objective_version),
               "sampled": True, "sample_n": len(rows), "sample_seed": sample.get("seed"),
               "full_fleet_column": False,
               "score_identity_ids": sorted(identity_ids),
               "mixed_identity": len(identity_ids) > 1,
               "n": len(rows), "scored": sum(r.get("j") is not None for r in rows),
               "status_counts": _counts(r["status"] for r in rows),
               "lane_best": dict(sorted(best.items(), key=lambda kv: kv[1]["j"]))}
    (out / "rescore_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"sample scored: n={summary['n']} scored={summary['scored']} identity={identity_ids and sorted(identity_ids)[0][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
