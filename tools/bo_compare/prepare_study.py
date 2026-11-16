"""Prepare ONE BoTorch study package for the matched BO-vs-CMA comparison (no solves; CPU only).

Plan: docs/queue/BO_VS_CMA_PLAN_2026-11-15.md. Mirrors scratch/2026-11-14_bayes/prepare_pilot.py (the
verified pilot path) with three differences: the training cohort is an explicit prepared directory
(built with ``tools/analysis/study_cohort.py --run-id <prior run>`` so no earlier study's rows leak in),
the policy seed is a CLI argument (each arm gets its own seeded Sobol pool), and the package selects an
explicit named budget profile (default ``comparison-60`` = 60 screens + 6 verify calls; baseline stays
18 + 6, and ``comparison-25``/``comparison-30`` cover the small multi-typology campaigns).

The study task is either a registered ``--task`` name or an explicit ``--config``/``--brief`` pair; the
latter stages any typology without registering a new named task (the spec carries the exact
``{"config": ..., "brief": ...}`` shape ``builders._read_task`` consumes). Giving both ``--task`` and
``--config`` is refused. Omitting both keeps the historical default task
(``p80x60__osse_ext_throat_home700_v7_seed5678``) so the 15 Nov night files stay replayable.

Run with the Bayesian interpreter (Torch/BoTorch/GPyTorch), from the canonical checkout:

    ..\\oc-wt\\bo-study\\bayes-venv\\Scripts\\python.exe tools\\bo_compare\\prepare_study.py \\
        --root runs\\bo_vs_cma\\bo_s31001 --cohort runs\\bo_vs_cma\\cohort --seed 31001 \\
        --deadline-hours 6 --label bo_s31001 \\
        --task p80x60__osse_ext_throat_home700_v7_seed5678

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

#: Default named budget profile; every other profile in ``BUDGET_PROFILES`` may be selected explicitly.
DEFAULT_BUDGET_PROFILE = "comparison-60"

#: Legacy default task when neither ``--task`` nor ``--config`` is given. The 15 Nov night files
#: (``docs/queue/bo_vs_cma_2026-11-15.yaml``, ``bo_ext_2026-11-16.yaml``) omit ``--task`` and rely on
#: exactly this task, so it must stay the default for them to remain replayable.
DEFAULT_TASK = "p80x60__osse_ext_throat_home700_v7_seed5678"


def _repo_path(value) -> Path:
    """Resolve a CLI path relative to the repository root when it is not absolute."""
    path = Path(str(value))
    return (path if path.is_absolute() else REPO / path).resolve()


def _inside_repo(path: Path) -> bool:
    return path == REPO or REPO in path.parents


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", required=True, help="study root (created; must not hold a package.json)")
    ap.add_argument("--cohort", required=True, help="dir with offline_scores.json + catalog.csv")
    ap.add_argument("--dataset", default=str(REPO / "dataset"))
    ap.add_argument("--seed", type=int, required=True, help="policy / Sobol pool seed of this arm")
    ap.add_argument("--deadline-hours", type=float, default=6.0)
    ap.add_argument("--label", required=True)
    ap.add_argument("--lane", default="gpu", choices=("gpu", "cpu"))
    ap.add_argument("--task", default=None,
                    help="registered study task name (give --task OR --config)")
    ap.add_argument("--config", default=None,
                    help="typology config path (relative to the repo root is fine); "
                         "replaces --task and stages any typology")
    ap.add_argument("--brief", default=None,
                    help="design brief path for --config (default: the config's brief_file)")
    ap.add_argument("--budget-profile", default=DEFAULT_BUDGET_PROFILE,
                    help="named package budget profile (default: %(default)s)")
    ap.add_argument("--policy", default="scalar", choices=("scalar", "turbo", "pareto"),
                    help="proposal policy (turbo = turbo_pool_v1 trust region; pareto = coverage/ripple)")
    ap.add_argument("--min-rows", type=int, default=100,
                    help="refuse unless the cohort gives at least this many usable training rows (default 100)")
    a = ap.parse_args(argv)

    from hornlab_search.studies.package import BUDGET_PROFILES

    if a.budget_profile not in BUDGET_PROFILES:
        print(f"refusing: unknown --budget-profile {a.budget_profile!r} "
              f"(known: {sorted(BUDGET_PROFILES)})", file=sys.stderr)
        return 2
    if a.task and a.config:
        print("refusing: give either --task or --config, not both", file=sys.stderr)
        return 2
    if a.brief and not a.config:
        print("refusing: --brief requires --config", file=sys.stderr)
        return 2
    if not a.task and not a.config:
        # Backward compatibility: the 15 Nov nights omit --task and expect this exact task.
        a.task = DEFAULT_TASK

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
    # Resolve the study task identity: either a registry name or an explicit config/brief pair.
    if a.config:
        config_path = _repo_path(a.config)
        if not _inside_repo(config_path):
            print(f"refusing: --config {config_path} is outside the repository root {REPO}",
                  file=sys.stderr)
            return 2
        if not config_path.is_file():
            print(f"refusing: --config not found: {config_path}", file=sys.stderr)
            return 2
        if a.brief:
            brief_path = _repo_path(a.brief)
        else:
            from hornlab_search.config import load_config
            try:
                loaded = load_config(config_path)
            except Exception as exc:  # noqa: BLE001 - a bad config is an explicit refusal, not a crash
                print(f"refusing: --config {config_path} could not be loaded: {exc}",
                      file=sys.stderr)
                return 2
            raw_brief = loaded.raw.get("brief_file") if isinstance(loaded.raw, dict) else None
            if not raw_brief:
                print(f"refusing: --config {config_path} names no brief_file; pass --brief",
                      file=sys.stderr)
                return 2
            ref = Path(str(raw_brief))
            if ref.is_absolute():
                brief_path = ref.resolve()
            else:
                beside_config = (config_path.parent / ref)
                brief_path = (beside_config if beside_config.exists() else REPO / ref).resolve()
        if not _inside_repo(brief_path):
            print(f"refusing: --brief {brief_path} is outside the repository root {REPO}",
                  file=sys.stderr)
            return 2
        if not brief_path.is_file():
            print(f"refusing: brief not found: {brief_path}", file=sys.stderr)
            return 2
        task_spec = {"config": str(config_path), "brief": str(brief_path)}
        task_label = str(config_path)
        training_config = str(config_path)
    else:
        task_spec = {"name": a.task}
        task_label = a.task
        training_config = builders._read_task({"name": a.task}, root=REPO)["config"]
    # Owner rule (2026-11-15): BoTorch only on a typology that already has enough solved designs.
    # The model's own floor (2*(d+1)) is far too lax for spending GPU hours; refuse before any study exists.
    from hornlab_search.bo.data import build_native_training_set
    tr = build_native_training_set(training_config, scores_json=source["scores_json"],
                                   catalog_csv=source["catalog_csv"],
                                   dataset_root=source["dataset_root"], require_single_fidelity=True)
    n_ok = int(getattr(tr, "n", 0) or 0)
    if getattr(tr, "status", None) != "ok" or n_ok < a.min_rows:
        print(f"refusing: task {task_label} has {n_ok} usable training rows "
              f"(< --min-rows {a.min_rows}); build a CMA cohort first", file=sys.stderr)
        return 3
    print(f"training rows: {n_ok} (min {a.min_rows})", file=sys.stderr)
    root.mkdir(parents=True, exist_ok=True)
    spec = {"protocol": "bo-study-v1.1",
            "question": f"BO-vs-CMA matched comparison arm {a.label} "
                        f"(seed {a.seed}, {a.budget_profile})",
            "task": task_spec, "source": source,
            "policy": {"proposal_policy": a.policy, "seed": a.seed}}
    service = StudyService(root)
    sid = service.create_study(spec, f"bo-vs-cma-{a.label}")["id"]
    steps = {}
    for fn in (builders.freeze_snapshot, builders.build_training, builders.build_analysis,
               builders.build_proposal):
        res = fn(service, sid, root=root)
        steps[fn.__name__] = res.get("status") if isinstance(res, dict) else "ok"
    deadline = (datetime.now(timezone.utc) + timedelta(hours=a.deadline_hours)).isoformat()
    package = prepare_run_package(service, sid, lane=a.lane, deadline=deadline,
                                  budget_profile=a.budget_profile)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    print(json.dumps({"study_id": sid, "policy": a.policy, "package_id": package["package_id"], "budget": package["budget"],
                      "budget_profile": package.get("budget_profile"), "deadline": deadline,
                      "steps": steps, "preflight": execution_capability(service, package, root=REPO)},
                     default=str), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
