# Split ownership — two parent sessions (2026-11-12 ~23:40)

Agreed by the owner after a second agent session began executing the same handoff in the
canonical checkout `C:\Users\hunte\Hrns\hornlab-search` (branch `main`).

## Session A — bo-study parent (this session)
Commits (only, with a fresh mtime check <30 s old → wait, else commit later):
- `hornlab_search/objective/replay.py`, `tools/analysis/offline_scores.py`
- `tools/analysis/{catalog,cohorts,parameter_activity,geometry_effects,parameter_study,source_fidelity}.py`
- `hornlab_search/bo/{__init__,encoding,metrics,data}.py` (data.py: append-only, B2 lane)
- `tools/experiments/**` (S11), `tools/bench/fake_harness.py` (S9), `docs/throughput/S9_PERFORMANCE_PREPARATION_2026-11-12.md`
- their focused tests: `tests/test_obj_replay.py`, `tests/test_tools_analysis_{offline_scores,catalog,cohorts,parameter_activity,geometry_effects,parameter_study,source_fidelity}.py`,
  `tests/test_bo_{encoding,data,metrics*}.py`, `tests/test_experiment_manifest.py`, `tests/test_bench_s9_timing_ledger.py`
- `scratch/bo_m0/s10/fixtures/**` via `git add -f` ONLY WHEN the gui renderer test file is committed by Session B (the test imports the fixtures).

## Session B — handoff executor (the second agent session)
Commits:
- `hornlab_search/studies/**` (B1/B5: schema/store/service/runner/reconcile)
- `hornlab_search/gui/{server.py,study_jobs.py,data_studies.py,data.py(app.py tuple/analysis serving),static/{app.js,app.css,studies.js}}` 
  — NOTE: gui/data.py carries BOTH your analysis-page overhaul and Session A's two-key
  `ANALYSIS_TOOL_JSONS` addition; include both, do not revert either. Session A's two lines are
  the `parameter_study`, `source_fidelity` entries.
- `hornlab_search/bo/{pareto,extensions}.py` (B7) — Session A does not touch these.
- their tests: `tests/test_studies_registry_b1.py`, `tests/test_studies_b5_runner.py`,
  `tests/test_gui_studies_*.py`, `tests/test_gui_study_adapters.py`, `tests/test_b8_foundation_adversarial.py`,
  `tests/test_bo_{pareto,extensions,sensitivity,cohort_gate,proposal_validation}.py`,
  `tests/test_gui_views_analysis_m1.py` (+ fixtures above, `git add -f`),
  `tests/test_gui_views_analysis.py` (your modified version — it encodes the new section layout),
  `docs/HANDOFF_ANALYSIS_PAGE_2026-11-12.md`, `docs/CODE_MAP.md`, `docs/INDEX.md`, `NOTES_FOR_SENIOR.md` entries.

## Rules
1. Never touch the other session's paths; never reformat or revert them.
2. Commit per validated slice; one slice per commit; push requires the standing repo rules
   (CONTINUITY + ISSUES in the same commit as any push).
3. If a shared path is discovered (e.g., both sessions edited one file), STOP and append to
   `NOTES_FOR_SENIOR.md` instead of resolving unilaterally.
4. The GPU night queue remains live; no solves, no gpu-clean, no queue edits from either session.
5. `bo/data.py` and `bo/metrics.py` belong to Session A's B2 lane — Session B must not edit them.
