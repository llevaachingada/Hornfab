"""Verify the first CMA tranche and continue promising sculpted lanes to 60."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from hornlab_search.report.preferred_pattern import preferred_pattern_diagnostics
from hornlab_search.search import rundir
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.solve.cache import load_response
from tools.geometry.sculpted_roll_probe import source
from tools.night_queue.verify_night_jobs import latest_rows

EXE = ROOT / ".venv/Scripts/hornlab-search.exe"
NIGHT = ROOT / "runs/nights/sculpted_xo900_cma_pilot_2026-11-21"
CACHE = ROOT / "scratch/sculpted_xo900_cma_cache"


def source_matches(first, second):
    a, a_faces = source(first)
    b, b_faces = source(second)
    distance, mapping = cKDTree(a).query(b)
    return (len(a) == len(b) == len(set(mapping))
            and set(map(tuple, np.sort(a_faces, axis=1))) == set(map(tuple, np.sort(mapping[b_faces], axis=1)))
            and float(distance.max()) * 1000 <= 0.001)


def verify_candidates(run, seed, best, label):
    verify = run / label
    command = [str(EXE), "verify", "--run", str(run), "--designs", f"{seed},{best}",
               "--cache-dir", str(CACHE), "--verify-dir", str(verify)]
    env = dict(os.environ, HORNLAB_GPU_LOCK="refuse")
    returned = subprocess.run(command, cwd=ROOT, env=env).returncode
    if returned:
        return {"admitted": False, "verify_exit": returned}
    base, candidate = [verify / "designs" / design for design in (seed, best)]
    a, b = [rundir.read_json(directory / "status.json") for directory in (base, candidate)]
    if not all(s and s.get("ok") and s.get("terms", {}).get("cd_status_code") == 0 for s in (a, b)):
        return {"admitted": False, "reason": "incomplete full-balloon verify pair"}
    pains = [preferred_pattern_diagnostics(load_response(directory / "response.npz"))
             for directory in (base, candidate)]
    patterns = [p["planes"] for p in pains]
    width_delta = {}
    for plane in ("h", "v"):
        baseline, treatment = (pattern[plane]["rms_error_deg"] for pattern in patterns)
        if baseline is None or treatment is None:
            return {"admitted": False, "reason": f"missing {plane.upper()} preferred-pattern error"}
        width_delta[plane] = treatment - baseline
    delta = b["objective"] - a["objective"]
    load_delta = b["terms"]["load"] - a["terms"]["load"]
    source_ok = source_matches(base / "mesh.msh", candidate / "mesh.msh")
    return {"admitted": source_ok and delta <= -0.08 and max(width_delta.values()) <= 3 and load_delta <= 0.10,
            "J_seed": a["objective"], "J_candidate": b["objective"], "delta_j": delta,
            "H_V_rms_error_delta_deg": width_delta, "loading_delta_j": load_delta,
            "source_matched": source_ok, "verify_dir": str(verify)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane", choices=("r3", "k1", "crowe"))
    lane = parser.parse_args().lane
    summary = latest_rows(NIGHT / "summary.jsonl").get(lane + "_30", {})
    run_path = summary.get("run_dir")
    if not run_path or not (Path(run_path) / "search.ndjson").exists():
        print("Continuation held: first tranche has no run path", flush=True)
        return 0
    run = Path(run_path)
    rows = read_ndjson(run / "search.ndjson")
    good = [r for r in rows if r.get("ok") and r.get("objective_version") == 11
            and r.get("terms", {}).get("cd_status_code") == 0]
    if not good or not rows[0].get("ok"):
        print("Continuation held: first tranche has no qualified seed and result", flush=True)
        return 0
    seed, best = good[0], min(good, key=lambda r: r["objective"])
    gap = best["objective"] - seed["objective"]
    late_delta = best["objective"] - min(r["objective"] for r in good[:20])
    report = {"run": str(run), "accepted_screen": len(good), "screen_delta_j": gap,
              "screen_delta_after_20": late_delta,
              "seed": seed["design_hash"], "screen_best": best["design_hash"]}
    evidence = NIGHT / f"{lane}_decision.json"
    if gap <= -0.08:
        report["first_verify"] = verify_candidates(run, report["seed"], report["screen_best"], "verify_first30")
    rundir.write_json_atomic(evidence, report)
    print(report, flush=True)
    if len(good) < 30 or late_delta > -0.02 or not report.get("first_verify", {}).get("admitted"):
        return 0

    command = [str(EXE), "search", "--resume", str(run), "--budget", "60", "--mode", "screen",
               "--cache-dir", str(CACHE)]
    report["continuation_exit"] = subprocess.run(command, cwd=ROOT,
                                                   env=dict(os.environ, HORNLAB_GPU_LOCK="refuse")).returncode
    if report["continuation_exit"] == 0:
        final = rundir.read_json(run / "best.json")
        if final["design_hash"] != report["screen_best"]:
            report["second_verify"] = verify_candidates(run, report["seed"], final["design_hash"], "verify_final60")
    rundir.write_json_atomic(evidence, report)
    return report["continuation_exit"]


if __name__ == "__main__":
    sys.exit(main())

