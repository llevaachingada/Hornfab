# Optimizer audit — implementation status

Source review: [README.md](README.md) (senior audit, 2026-11-21). Current-tree check:
[CURRENT_STATE_CHECK.md](CURRENT_STATE_CHECK.md).

This pass implements the audit's P0 and P1 ladder offline. Every change is additive or opt-in;
no production default, score version, frozen contract or GPU queue was changed. P2 remains gated
by the audit's own rule: "Only after that authorize matched physical experiments."

## Roadmap status

| Order | Item | Status | Where |
|---|---|---|---|
| P0a | CMA-MAE dual archives + export semantics + replay protocol | **Implemented** | `search/cma_me.py`, `tests/test_search_cma_mae_archive_semantics.py` |
| P0b | Full-identity numerical floor registry + safer continuation advisory + typed switch outcomes | **Implemented** | `tools/analysis/floor_registry.py`, `continuation_advice.py`, `optimizer_switch.py` |
| P0c | Opt-in v10/v11 production-study compatibility with explicit metric dispatch | **Implemented** | `bo/metrics.py`, `studies/builders.py`, `studies/production.py` |
| P1a | Composed optimizer-evidence report (advisory only) | **Implemented** | `tools/analysis/optimizer_evidence.py` |
| P1b | Opt-in covariance-transfer warm start | **Implemented** | `search/warmstart.py`, `search/cma.py`, `config.py` |
| P1c | Controlled matched-benchmark orchestration + compare report | **Implemented** | `tools/analysis/benchmark_orchestrator.py`, `specs/matched_optimizer_pilot_2026-11-21.yaml` |
| P2 | QD descriptor study / second emitter | **Deferred** (needs matched BEM evidence + owner GPU authorization) | audit §6-7 |
| P2 | Cost-aware BO pilot | **Deferred** (same gate) | audit §6-7 |

## P0a — CMA-MAE archive semantics

- The scheduler's **search** archive is soft only when `search.qd.maes` is set; the **result**
  archive is always hard (`learning_rate=1.0`, `threshold_min=-inf`).
- `archive.json` and the GUI `archive_heatmap.json` are exported from the hard result archive.
  The soft search archive is written as `archive_learning.json`, labelled
  `learning_archive_diagnostic` and never read by the atlas.
- Protocol is now `cma-me-archive-v3`. A v2 run is refused on resume before any evaluation with
  an explicit "old result-archive semantics cannot be resumed" message; no silent reinterpretation.
- Regression: the direct ribs pair (same 2x2 cell, archive objectives 10 then 9) stores 9 in the
  soft archive and keeps 10 in the hard result archive; a deterministic run proves the export is
  the hard elite and that the learning file is separate.
- Two historical v2 cma_me run dirs exist (`runs/20261114T235641Z-screen-dfd27f`,
  `runs/20261115T005614Z-screen-6d55fa`). They are read-only evidence now; resuming them is
  refused by design. No run dir was modified.

## P0b — floor identity and switch outcomes

- `tools/analysis/floor_registry.py` keys floors by objective version, resolved brief content
  sha256 (or exact path+name when the file cannot be resolved, with match-quality), score identity
  hash, backend, fidelity, comparison grid, test method/sample size and a three-part uncertainty
  record.
- Entries: v7 home this-pass 0.310479 J; v10 home corridor/preferred_edge 0.467739 J; v10 home
  slope5 0.486317 J; compact400 v10xo 0.1293 J (frequency 0.129111 + mesh 0.007676), with its
  whole-fleet score-consistency caveat. The generic v10 floor is never assigned to compact400.
- Unknown/mismatched identity returns "no applicable published floor" and names the missing or
  mismatched fields. A gain inside the declared band around the floor (`floor/1.25 .. floor*1.25`)
  returns "verify on common grid" instead of a decisive continue/stop.
- Real-run check: `runs/20261115T162516Z-screen-e31b23` (home v7 brief, copied config under
  `runs/`) resolves the v7 brief through the `examples/briefs` re-root and returns
  "do not propose" at floor 0.3105; `runs/20261119T181029Z-screen-c3b6c6` (shipped v10 brief)
  returns "propose continuation" at floor 0.4677.
- `optimizer_switch` now reports mutually exclusive typed counts (valid, cached, geometry /
  envelope / resource refusal, solver failure, pipeline failure, unknown) and names the dominant
  recorded outcome; a clean run reports no dominant failure kind. Historical aggregate keys remain.
- Known limitation: the published floor artifacts do not record the measurement backend,
  quadrants/epw or exact frequency-grid hash, so those identity fields are reported as
  `unverified_fields` rather than blocking a core-exact brief/score match. A future floor
  re-measure should persist them.
- Alias decision: `v10_home_shipped_preferred_edge` is an explicit entry with its own resolved
  brief identity because the shipped production brief is field-identical to the offline rescore
  brief in driver/envelope/symmetry/source/target/weights/objective (only name/description and the
  grid block differ), and its measurement command and source artifact are recorded. It is not a
  name-based borrow; the generic v10 floor still does not reach compact400.

## P0c — production BO v10/v11

- v4/v7 admission and metric contracts are unchanged.
- v10 uses the existing `freeze_metric_policy_v10` / `measure_metrics_v10`; v11 has a separate
  `METRIC_SCHEMA_V11 = bo-physical-metric-v11/1` policy that carries the `objective.cd` block and
  `scalar_v11` / `metrics.cd` code shas, reusing the v10 raw coverage/ripple math. Cohort labels
  now include 11 and mixed 4/7/9/10/11 cohorts are refused.
- Production admission is registry-driven. Three tasks are registered:
  `compact400__fold_warm_v10xo` (v10 compact400 fold-warm leader), `home_v10__morph`
  (v10, d=14, with a completed full-C source run) and `home900__landscape_v11cd` (v11). A
  **derived** config with an unchanged non-search task
  identity (same brief content, objective, bounds, target, weights, mesh, solve, family, seed) is
  admitted with basis `derived_task_identity`; a changed task field or a different brief is
  refused. This is what lets the matched-benchmark orchestrator write arm configs under its own
  output directory without opening v10/v11 to arbitrary configs.
- `build_pareto_metrics`, `measure_record_metrics` and the production Pareto worker dispatch on
  the resolved version with no silent fallback; v10/v11 training manifests record a
  `metric_identity` (schema + hash + code shas, plus the CD block for v11) and refuse mixed stored
  versions. v4/v7 manifests are byte-identical (no new key).

## P1a — composed optimizer evidence

`tools/analysis/optimizer_evidence.py` produces one `optimizer-evidence-v1` JSON/Markdown report:

- default evidence: `optimizer_switch` (typed outcomes, stall, walls), `continuation_advice`
  (identity-resolved floor, uncertainty, advice), cost ledger and cross-run compatibility;
- opt-in evidence: `space_card`, `parameter_activity` (CPU geometry only), `seed_pack` (with
  `--catalog`), `qd_compare` (with both manifests), budget heuristic (with `--config`);
- every key number carries `{source_tool, source_field}` provenance;
- at most two `alternatives`, each with action/why/evidence/confidence/constraints;
- unknown identity suppresses only floor-dependent continuation/common-grid advice; typed
  failure/wall/stall alternatives survive and `insufficient_evidence` names the missing floor;
- flags `advisory_only: true`, `dispatches_work: false`, `changes_defaults: false`; cross-run
  raw-J ranking is explicitly `performed: false`.
- Real-run check: the v10 run above returns one `extend_same_identity_lane` alternative with the
  0.4677 floor and a 0.9172 J window gain.

## P1b — covariance-transfer warm start

- New opt-in `search.warm_start.covariance` (bool or mapping: `blend`, `eig_floor`, `eig_cap`,
  `max_dim`, `scale_sigma`). Absent/false leaves the mean-only record byte-identical.
- Transform: `Sigma_old = sigma_old^2 C_old`;
  `T = D_new^-1 D_old Sigma_old D_old D_new^-1` with `D = diag(span)` in search coordinates
  (`log10` width for log bounds); shape normalized to trace `d`, then symmetrized, eigenvalue
  floor/cap, conservative identity blend, SPD verification.
- `scale_sigma: true` (default) uses the declared `search.sigma0` for overall width and transfers
  shape; `scale_sigma: false` uses `sqrt(trace(T)/trace(C_target))` to preserve the transferred
  total variance even after clipping/blending. 20k-draw sampling test: relative Frobenius error
  0.00862 at d=3 (5 % tolerance).
- Injection is plain single-ES only, before the first `ask`, via cma 4.5.0 `es.sm.C` +
  `es.sm._decompose_C()` with an SPD re-check. The source is the run that supplied the warm mean;
  missing sidecars, restart-only summaries, dimension > 16, knob/order mismatch and non-SPD `C`
  are refused. Config validation refuses covariance + `search.restarts` and covariance + `cma_me`
  instead of silently ignoring the opt-in.
- run.json records source run/path, `C_sha256`, source sigma, old/new spans, formula, blend,
  eigen bounds, max_dim, scale convention, target sigma, traces, condition number, eigenvalues
  and `spd_verified`.

## P1c — matched-benchmark orchestration

`tools/analysis/benchmark_orchestrator.py` has two offline subcommands:

- `plan --spec <yaml> --out <dir>` validates a `benchmark-plan-v1` spec, derives one self-contained
  config per arm under `<out>/arms/` (absolute `brief_file`, embedded resolved brief), proves the
  non-search task identity is equal across arms, enforces a declared/deduplicated seed set (>= 5
  unless `--pilot`), and writes `benchmark_plan.json/.md` with `dispatched: false` and launch
  commands as text only.
- `report --plan <json> --results <arm>=<dir>[,...] --out <dir>` enforces the declared seed set
  exactly once per arm, refuses identity/parity mismatches, aggregates typed cost ledgers, and
  delegates predeclared pairs to `ab_compare.analyse` with floor-aware verdicts (no decisive claim
  without `floor_j`; < 5 pairs is pilot-only; no cross-task raw-J ranking).
- Template: `tools/analysis/specs/matched_optimizer_pilot_2026-11-21.yaml` (5 seeds; cold CMA,
  mean-only warm CMA, covariance-informed CMA, scalar BO, TuRBO on the registered home-v10 morph
  task). The covariance arm uses the completed 120-evaluation source run
  `20261119T181029Z-screen-c3b6c6` (full 14x14 C); the BO/TuRBO arms use the task-specific
  `runs/analysis/home_v10_pilot_cohort_2026-11-21` cohort (120 exact-complete rows, prepared
  offline by `python -m tools.analysis.study_cohort`; no backend calls). It is a plan only and
  was not run.
- Integration check: the derived BO arm from the template is admitted by
  `production.objective_admission` via `derived_task_identity`; the derived YAMLs load from a
  temp output directory and resolve the same brief.

## Explicitly not changed

- No optimizer default, no score version, no frozen `01_CONTRACTS.md` content, no GPU job, no
  `runs/` or dataset write.
- NSGA-II remains an offline helper; `cma_me` emitter internals and descriptors are unchanged;
  the constrained QD emitter stays a design document.
- P2 (QD descriptor study / second emitter; cost-aware BO pilot) is deferred until the audit's
  matched-real-BEM authorization and owner GPU approval.

## Validation evidence

Focused set (all touched search/tools/BO/studies/GUI-atlas files, thread-capped):

```text
.venv\Scripts\python.exe -m pytest <30 focused files> -q -p no:cacheprovider -o addopts=""
364 passed, 1 skipped in 78.21s
```

The skip is the pre-existing optional-BoTorch gate (`tests/test_bo_pareto_production.py:158`;
botorch/gpytorch are not installed in `.venv`). A live scalar GP fit/verify replay was therefore
not run; the v10/v11 admission, metric-identity and dispatch layer is unit-tested, and the
audit's matched BEM/replay validation remains part of the gated physical phase.

Real-task dry checks (CPU/read-only, no solve):

- `continuation_advice` on `runs/20261115T162516Z-screen-e31b23` resolves the home-v7 brief
  through the `examples/briefs` re-root (0.0761 J last-100 gain, "do not propose" at the 0.3105
  floor); `runs/20261119T181029Z-screen-c3b6c6` returns "propose continuation" (0.9172 J at the
  0.4677 floor).
- `optimizer_evidence` on the same v10 run returns one `extend_same_identity_lane` alternative
  with the floor/improvement provenance; `dispatches_work: false`.
- The P1c template plan derives all five arms; every CMA and BO/TuRBO launch is marked
  executable against the declared cohort/hashes; the covariance arm resolves the source run's
  full 14x14 C (SPD, trace 14, target sigma 0.2) and the derived BO arm is admitted by
  `objective_admission` with basis `derived_task_identity`.
- The task-specific BO cohort `runs/analysis/home_v10_pilot_cohort_2026-11-21` was prepared
  offline: 120 exact-complete home-v10 rows in one dependency/grid group, `no_backend_calls:
  true`, pins recorded.

Full offline profile:

```text
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" \
    -n 6 --dist loadscope -p no:cacheprovider -q --tb=no
```

Result: the same **7 pre-existing other-lane failures** recorded in CONTINUITY before this pass,
with no failure in a touched file:

- `tests/test_targets.py::test_from_dict_round_trips_example_targets[score_identities.yaml]`
- `tests/test_objective_v8.py::test_v8_is_registered_nowhere_and_never_changes_a_default`
- `tests/test_objective_v8.py::test_v8_key_set_is_v4_minus_load_plus_the_extras`
- `tests/test_tools_search_preflight.py::test_generated_history_fallback_reads_grid_knobs`
- `tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  (reports `gui/study_jobs.py`, not a study module we touched)
- `tests/test_dataset_manifest.py::test_manifest_census_groups_and_provenance` (v11 registration)
- `tests/test_queue_fable_scout40.py::test_scout40_jobs_are_budgeted_and_grouped` (queue-data drift)

No GPU, solver or mesh job was run. `compileall` on the touched package/tools/tests exits 0.
