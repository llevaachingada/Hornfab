"""2026-11-18 owner-directed reuse pass (Fable WP 1.4/1.5). NO recomputation of completed columns.

Reads the preserved row-level rescore.jsonl + rescore_summary.json of a completed column and
re-emits a rescore_summary.json into a NEW UNIQUE output directory with the corrected
mixed_identity semantics (score identity per column, not per-design score_id counts). The score
identity is computed exactly as the fixed tools/analysis/rescore_identity.py computes it: the
replay takes objective version/weights/block from the PASSED brief (replay.py:668-674), so the
identity inputs are the column's brief file plus SCORE_CODE_VERSION. J, ranks, parity values are
copied through untouched - nothing is re-scored.

Usage:
  python reuse_summary_emitter.py --rows <orig_dir> --summary <orig_dir> --brief <brief.yaml> --out <new_dir>
"""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from hornlab_search.objective.replay import SCORE_CODE_VERSION, _hash as _replay_hash  # noqa: E402
from hornlab_search.objective.replay import load_brief_context  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    orig_dir = Path(a.summary)
    old = json.loads((orig_dir / "rescore_summary.json").read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in Path(a.rows).read_text(encoding="utf-8").splitlines() if l.strip()]

    b = load_brief_context(a.brief)
    identity = _replay_hash({
        "kind": "score",
        "score_code": SCORE_CODE_VERSION,
        "objective_version": int(b.objective_version),
        "weights": b.weights,
        "objective_block": b.objective_block,
        "brief_hash": b.brief_hash(),
        "brief_name": b.name,
    })

    best: dict = {}
    for r in rows:
        j = r.get("j")
        if j is None or not math.isfinite(float(j)):
            continue
        if r["lane"] not in best or j < best[r["lane"]]["j"]:
            best[r["lane"]] = {"j": float(j), "run": r["run"], "design_hash": r["design_hash"]}
    summary = {
        "brief": str(a.brief), "objective_version": int(b.objective_version),
        "run_brief_filter": old.get("run_brief_filter"),
        "runs_skipped_other_brief": old.get("runs_skipped_other_brief"),
        "score_ids": old.get("score_ids", []),
        "n": old.get("n"), "scored": old.get("scored"),
        "score_identity_ids": [identity],
        "mixed_identity": False,
        "status_counts": dict(Counter(r.get("status", "error") for r in rows)),
        "lane_best": dict(sorted(best.items(), key=lambda kv: kv[1]["j"])),
        "reused_from": {"rows": str(Path(a.rows)), "summary": str(orig_dir),
                        "note": "row-level J values copied byte-for-byte from the completed pass; "
                                "only summary flags re-emitted (2026-11-18 owner-directed reuse)"},
    }
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: output dir {out} exists and is not empty")
    out.mkdir(parents=True)
    (out / "rescore_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"reused: {orig_dir} -> {out}: n={summary['n']} scored={summary['scored']} "
          f"identity={identity[:16]} mixed_identity=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
