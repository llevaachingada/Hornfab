"""2026-11-18 owner-directed reuse pass (Fable WP 1.5/R2). Selects 120-200 REPRESENTATIVE designs
from the preserved full-fleet v10-offline rescore.jsonl for the two NEW scoring definitions
(v10-shipped identity agreement vs offline; v10_slope5 diagnostic sample). Full-fleet re-scoring of
these two definitions is NOT queued; slope5 ranks nothing until its floor exists (R2) and shipped
rows are sample-verified against the offline column whose J values ship unchanged.

Strata (dedup by (run, design_hash), cap ~160):
  1. lane-best union (v7 + v10 lane_bests)          -- historical winners
  2. per-lane J-rank 1/4/10 for the 10 best lanes    -- acoustically diverse near-top
  3. 70 stratified-random rows, proportional per lane, seed 20261118
  4. 12 worst-J scored rows                          -- tail behaviour
  5. up to 10 additional_data_or_solve_required rows  -- known failure cases

Usage:
  python select_rescore_sample.py --rows <v10_offline rescore.jsonl> [--rows7 <v7 jsonl>] --out <sample.json>
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path


def load(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", required=True)
    ap.add_argument("--rows7", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    v10 = load(a.rows)
    v7 = load(a.rows7) if a.rows7 else v10
    keys = set()

    # 1. lane-best union
    for rows in (v7, v10):
        best: dict = {}
        for r in rows:
            j = r.get("j")
            if j is None:
                continue
            k = (r["run"], r["design_hash"])
            if r["lane"] not in best or j < best[r["lane"]][1]:
                best[r["lane"]] = (k, j)
        for k, _ in best.values():
            keys.add(k)

    winners = len(keys)

    # 2. per-lane diversity on the top-10 lanes by best v10 J
    lane_rows: dict = defaultdict(list)
    for r in v10:
        if r.get("j") is not None:
            lane_rows[r["lane"]].append((r["j"], (r["run"], r["design_hash"])))
    for lane in sorted(lane_rows, key=lambda ln: min(j for j, _ in lane_rows[ln]))[:10]:
        for rank in (0, 3, 9):                      # 0-based -> J-rank 1/4/10
            if rank < len(lane_rows[lane]):
                keys.add(sorted(lane_rows[lane])[rank][1])

    diversity = len(keys) - winners

    # 3. stratified random
    rng = random.Random(20261118)
    pool = {ln: [(j, k) for j, k in v if k not in keys] for ln, v in lane_rows.items()}
    total_avail = sum(len(v) for v in pool.values())
    quotas = {ln: max(1, round(70 * len(v) / total_avail)) for ln, v in pool.items() if v}
    while sum(quotas.values()) > 70:
        big = max(quotas, key=lambda ln: quotas[ln])
        quotas[big] -= 1
    for ln, q in quotas.items():
        sample = rng.sample(pool[ln], min(q, len(pool[ln])))
        for _j, k in sample:
            keys.add(k)
    stratified = len(keys) - winners - diversity

    # 4. worst-scored tail  5. failure cases
    scored = sorted(((r["j"], (r["run"], r["design_hash"])) for r in v10 if r.get("j") is not None),
                    reverse=True)
    for _j, k in scored[:12]:
        keys.add(k)
    tail = len(keys) - winners - diversity - stratified
    fails = [r for r in v10 if r.get("status") != "exact_complete"][:10]
    for r in fails:
        keys.add((r["run"], r["design_hash"]))
    n_fail = len(keys) - winners - diversity - stratified - tail

    reasons = {}
    for rows, name in ((v7, "lane_best_v7"), (v10, "lane_best_v10")):
        best: dict = {}
        for r in rows:
            j = r.get("j")
            if j is None:
                continue
            if r["lane"] not in best or j < best[r["lane"]]["j"]:
                best[r["lane"]] = {"j": j, "run": r["run"], "design_hash": r["design_hash"]}
        for r in best.values():
            reasons.setdefault((r["run"], r["design_hash"]), []).append(name)
    fail_keys = {(r["run"], r["design_hash"]) for r in fails}
    worst_keys = {k for _j, k in scored[:12]}
    out = []
    for k in sorted(keys):
        reason = []
        if k in fail_keys:
            reason.append("failure_case")
        if k in worst_keys:
            reason.append("worst_j_tail")
        reason.extend(reasons.get(k, []))
        out.append({"run": k[0], "design_hash": k[1], "reasons": reason or ["stratified_random"]})

    payload = {"n": len(out), "strata": {"lane_best_union": winners, "per_lane_diversity": diversity,
                                         "stratified_random": stratified, "worst_j_tail": tail,
                                         "failure_cases": n_fail},
               "seed": 20261118, "selection": out}
    Path(a.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"sample: {len(out)} designs -> {a.out} | strata {payload['strata']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
