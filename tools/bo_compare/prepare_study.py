"""Prepare ONE BoTorch study package for the matched BO-vs-CMA comparison (no solves; CPU only).

Plan: docs/queue/BO_VS_CMA_PLAN_2026-11-15.md. Mirrors scratch/2026-11-14_bayes/prepare_pilot.py (the
verified pilot path) with three differences: the training cohort is an explicit prepared directory
(built with ``tools/analysis/study_cohort.py --run-id <prior run>`` so no earlier study's rows leak in),
the policy seed is a CLI argument (each arm gets its own seeded Sobol pool), and the package selects the
explicit ``comparison-60`` budget profile (60 screens + 6 verify calls; baseline stays 18 + 6).

Run with the Bayesian interpreter (Torch/BoTorch/GPyTorch), from the canonical checkout:

    ..\\oc-wt\\bo-study\\bayes-venv\\Scripts\\python.exe tools\\bo_compare\\prepare_study.py \\
        --root runs\\bo_vs_cma\\bo_s31001 --cohort runs\\bo_vs_cma\\cohort --seed 31001 \\
        --deadline-hours 6 --label bo_s31001

Writes ``<root>/package.json`` and prints one JSON line (study id, package id, budget, preflight).
Refuses to overwrite an existing package.json (a re-run needs a fresh --root).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

TASK = "p80x60__osse_ext_throat_home700_v7_seed5678"
PROFILE = "comparison-60"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", required=True, help="study root (created; must not hold a package.json)")
    ap.add_argument("--cohort", required=True, help="dir with offline_scores.json + catalog.csv")
    ap.add_argument("--dataset", default=str(REPO / "dataset"))
    ap.add_argument("--seed", type=int, required=True, help="policy / Sobol pool seed of this arm")
    ap.add_argument("--deadline-hours", type=float, default=6.0)
    ap.add_argument("--label", required=True)
    ap.add_argument("--lane", default="gpu", choices=("gpu", "cpu"))
    ap.add_argument("--policy", default="scalar", choices=("scalar", "turbo", "pareto"),
                    help="proposal policy (turbo = turbo_pool_v1 trust region; pareto = coverage/ripple)")
    a = ap.parse_args(argv)

    from hornlab_search.studies import builders
    from hornlab_search.studies.package import prepare_run_package
    from hornlab_search.studies.production import execution_capability
    from hornlab_search.studies.service import StudyService

    root = Path(a.root).resolve()
    if (root / "package.json").exists():
        print(f"refusing: {root / 'package.json'} exists (use a fresh --root)", file=sys.stderr)
        return 2
    cohort = Path(a.cohort).resolve()
    source = {"scores_json": str(cohort / "offline_scores.json"),
              "catalog_csv": str(cohort / "catalog.csv"),
              "dataset_root": str(Path(a.dataset).resolve())}
    for k in ("scores_json", "catalog_csv"):
        if not Path(source[k]).is_file():
            print(f"missing cohort file {source[k]}", file=sys.stderr)
            return 2
    root.mkdir(parents=True, exist_ok=True)
    spec = {"protocol": "bo-study-v1.1",
            "question": f"BO-vs-CMA matched comparison arm {a.label} (seed {a.seed}, {PROFILE})",
            "task": {"name": TASK}, "source": source,
            "policy": {"proposal_policy": a.policy, "seed": a.seed}}
    service = StudyService(root)
    sid = service.create_study(spec, f"bo-vs-cma-{a.label}")["id"]
    steps = {}
    for fn in (builders.freeze_snapshot, builders.build_training, builders.build_analysis,
               builders.build_proposal):
        res = fn(service, sid, root=root)
        steps[fn.__name__] = res.get("status") if isinstance(res, dict) else "ok"
    deadline = (datetime.now(timezone.utc) + timedelta(hours=a.deadline_hours)).isoformat()
    package = prepare_run_package(service, sid, lane=a.lane, deadline=deadline, budget_profile=PROFILE)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    print(json.dumps({"study_id": sid, "policy": a.policy, "package_id": package["package_id"], "budget": package["budget"],
                      "budget_profile": package.get("budget_profile"), "deadline": deadline,
                      "steps": steps, "preflight": execution_capability(service, package, root=REPO)},
                     default=str), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
