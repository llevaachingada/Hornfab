"""Read-only preflight for staged BoTorch arms (no solves, no GPU, no study created).

Proves, for every `--arm SLUG=TASK:COHORT_DIR`:

* the task name is registered in ``hornlab_search.studies.builders._TASK_REGISTRY``;
* its config and brief files exist and resolve to the declared objective version;
* the cohort directory holds ``offline_scores.json`` + ``catalog.csv``;
* the strict BoTorch gate (``build_native_training_set(..., require_single_fidelity=True)``)
  accepts at least ``--min-rows`` usable rows;
* the cohort's **measured dependency pins** (the mesher / BEM / plots build that produced the
  scores) match the interpreter that will execute the study — the check that
  ``studies/production.py:170-181`` performs at launch, and the reason a cohort solved months ago
  with an older BEM pin is not executable today;
* the requested ``--budget-profile`` exists in ``hornlab_search.studies.package.BUDGET_PROFILES``.

Nothing here writes, solves, or imports torch/botorch. Exit code 0 only when every arm is ready.

    .venv\\Scripts\\python.exe tools\\bo_compare\\preflight_arms.py \\
        --budget-profile comparison-25 --min-rows 100 \\
        --arm arm_a=p80x60__ext_throat_hvlaw_cov_v7:runs/bo_multityp_2026-11-16/ext_throat_hvlaw_cov/cohort
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def _parse_arm(text: str) -> tuple[str, str, Path]:
    slug, _, rest = text.partition("=")
    task, sep, cohort = rest.partition(":")
    if not slug.strip() or not task.strip() or sep != ":" or not cohort.strip():
        raise argparse.ArgumentTypeError(
            f"--arm must be SLUG=TASK:COHORT_DIR, got {text!r}")
    return slug.strip(), task.strip(), Path(cohort.strip())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", action="append", required=True, type=_parse_arm,
                    metavar="SLUG=TASK:COHORT_DIR")
    ap.add_argument("--budget-profile", default="comparison-25")
    ap.add_argument("--min-rows", type=int, default=100)
    ap.add_argument("--dataset", default=str(REPO / "dataset"))
    a = ap.parse_args(argv)

    from hornlab_search.bo.data import build_native_training_set
    from hornlab_search.search.evaluate import collect_lib_shas
    from hornlab_search.studies import builders
    from hornlab_search.studies.package import BUDGET_PROFILES
    from hornlab_search.studies.production import study_interpreter

    # Pins of the interpreter that will actually run the study (same selection as production.py).
    execution_python = study_interpreter(REPO)
    if execution_python.resolve() != Path(sys.executable).resolve() and execution_python.is_file():
        import subprocess
        probe = subprocess.run(
            [str(execution_python), "-c",
             "import json; from hornlab_search.search.evaluate import collect_lib_shas; "
             "print(json.dumps(collect_lib_shas()))"],
            cwd=str(REPO), capture_output=True, text=True, timeout=60)
        execution_pins = (json.loads(probe.stdout) if probe.returncode == 0
                          else {"probe_error": (probe.stderr or "unknown")[-300:]})
    else:
        execution_pins = collect_lib_shas()

    profile_ok = a.budget_profile in BUDGET_PROFILES
    rows: list[dict] = []
    for slug, task, cohort in a.arm:
        row: dict = {"arm": slug, "task": task, "cohort": str(cohort)}
        try:
            entry = builders._read_task({"name": task}, root=REPO)
        except Exception as exc:  # noqa: BLE001 - a refusal is the finding
            row.update(ready=False, reason=f"task_not_registered: {type(exc).__name__}: {exc}")
            rows.append(row)
            continue
        cfg_path = Path(entry["config"])
        brief_path = Path(entry["brief"]) if entry.get("brief") is not None else None
        row.update(config=str(cfg_path), brief=str(brief_path) if brief_path else None,
                   objective_version=entry.get("objective_version"),
                   config_exists=cfg_path.is_file(),
                   brief_exists=bool(brief_path and brief_path.is_file()))
        scores, catalog = cohort / "offline_scores.json", cohort / "catalog.csv"
        row.update(cohort_scores=scores.is_file(), cohort_catalog=catalog.is_file())
        if not (row["config_exists"] and row["brief_exists"]
                and row["cohort_scores"] and row["cohort_catalog"]):
            row.update(ready=False, reason="missing_config_brief_or_cohort_file")
            rows.append(row)
            continue
        try:
            tr = build_native_training_set(
                str(cfg_path), scores_json=str(scores), catalog_csv=str(catalog),
                dataset_root=str(Path(a.dataset).resolve()), require_single_fidelity=True)
        except Exception as exc:  # noqa: BLE001 - a refusal is the finding
            row.update(ready=False, reason=f"training_set_error: {type(exc).__name__}: {exc}")
            rows.append(row)
            continue
        n = int(getattr(tr, "n", 0) or 0)
        status = getattr(tr, "status", "?")
        row.update(training_status=status, n=n, d=getattr(tr, "d", None),
                   n_eligible=getattr(tr, "n_eligible", None))
        measured = ((json.loads(scores.read_text(encoding="utf-8")).get("selection") or {})
                    .get("dependency_pins") or {})
        row["measured_dependency_pins"] = measured
        pin_problems = []
        for key in ("hornlab_mesher", "hornlab_beat_bem", "hornlab_plots"):
            was, now = measured.get(key), execution_pins.get(key)
            if not isinstance(was, str) or was in ("", "unknown") or was != now:
                pin_problems.append(f"{key}: cohort={was!r} execution={now!r}")
        row["execution_pins_match"] = not pin_problems
        if status != "ok" or n < a.min_rows:
            row.update(ready=False,
                       reason=f"insufficient_rows: status={status} n={n} < {a.min_rows}")
        elif pin_problems:
            row.update(ready=False,
                       reason="dependency_pin_mismatch: " + "; ".join(pin_problems))
        elif not profile_ok:
            row.update(ready=False,
                       reason=f"unknown_budget_profile {a.budget_profile!r}")
        else:
            row.update(ready=True, reason="ok")
        rows.append(row)

    ready = all(r.get("ready") for r in rows) and profile_ok
    print(json.dumps({"ready": ready, "budget_profile": a.budget_profile,
                      "budget": BUDGET_PROFILES.get(a.budget_profile),
                      "min_rows": a.min_rows, "execution_interpreter": str(execution_python),
                      "execution_pins": execution_pins, "arms": rows},
                     indent=1, default=str))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
