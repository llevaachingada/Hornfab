# 09 — Pass 2 implementation status

- **Date:** 2026-11-22
- **Branch:** `feat/metric-aware-bo` (feature worktree `C:/Users/hunte/Hrns/hornfab-metric-bo-wt`)
- **Starting SHA:** `a8bddd4f5b835812a29bf51bd6b6b5c1ee2b864d` (Pass 1)
- **Base SHA:** `a30f2de9a5898d51b1c2e48b0513297db6e7584e`
- **Canonical checkout:** `C:/Users/hunte/Hrns/hornlab-search` on `hornfab-all-2026-11-18`, HEAD
  unchanged at `a30f2de9`, 63 pre-existing dirty files untouched.

## Final status

```
PASS 1 FOUNDATION: IMPLEMENTED
PASS 2 STUDY INTEGRATION: IMPLEMENTED AND SYNTHETICALLY TESTED
METRIC COMPOSITE POLICY: OPT-IN
PHYSICAL METRIC MODEL: RESEARCH-ONLY
REAL-DATA MODEL VALIDATION: NOT EXECUTED
HISTORICAL RESCORING: NOT EXECUTED
NEW BEM SOLVES: NONE
EXISTING JOBS: UNDISTURBED
FEATURE BRANCH: PUSHED
CANONICAL CHECKOUT: UNCHANGED
```

## Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Pass 1 branch/code reconciled | met | start SHA `a8bddd4f`; Pass 1 tests unchanged |
| One existing feature worktree used | met | `hornfab-metric-bo-wt` only; no new worktree |
| Canonical checkout undisturbed | met | 63 dirty files, HEAD/branch unchanged at start and end |
| Strict bounds identity enforced | met | `bo/metric_identity.py`, artifact payload re-hash, policy gate, proposal `require_identity=True` |
| Unsafe cohort replay fallback addressed | met | typed `metric_selection_unavailable`; `allow_unranked_replay` opt-in only |
| Stored-score identity checked before selection | met | `score_identity_unavailable` exclusions; brief + catalog score hash required |
| Training artifacts validated after storage reload | met | deterministic NPZ round trip + `validate_metric_training_artifact` |
| Metric-composite study policy opt-in | met | appended 6th; no default change |
| Existing policy defaults unchanged | met | `PRODUCTION_POLICIES` unchanged; scalar/TuRBO/Pareto tests pass |
| Synthetic study construction succeeds | met | 6 artifact kinds + package in `metric_study.py`; parent run |
| Synthetic adaptive proposal/update succeeds | met | 3 proposals, refit per observation; parent run |
| Synthetic interruption/recovery succeeds | met | no double evaluation; same next proposal after restore |
| Composite acquisition uses correct sign | met | `-sum(samples)` and uncertainty-can-outrank tests |
| Synthetic CPU GP fits actually run | met | `fit_s=2.17`, model hash, per-output records |
| Candidate and pending identities durable | met | journal stage/restore; pending never silently re-selected |
| Existing scalar/TuRBO/Pareto regressions | met | 583 passed / 3 documented skips |
| Existing CMA behavior untouched | met | no CMA file changed |
| Physical-metric research implemented/scoped | met | research-only `physical_composite.py`, canonical formulas |
| Optional constraints research-only | met | `metric_constraints.py`, not in policy registry |
| Scientific limitations documented | met | docs 04/05/06 and this file |
| No real-data GP training | met | synthetic fixtures only |
| No historical rescoring | met | no dataset/run path executed |
| No bulk archive traversal | met | catalog/cohort not run against real data |
| No new BEM solve | met | no solver/mesh/GPU import reached; sentinel tests |
| No optimizer campaign | met | no queue or campaign touched |
| No canonical checkout merge | met | branch only |
| Tests and raw evidence recorded | met | `06_SYNTHETIC_VALIDATION.md` |
| Documentation/code index updated | met | INDEX, CODE_MAP, this directory |
| CONTINUITY and ISSUES updated | met | same pushed commit |
| Feature branch pushed + remote SHA verified | met | see final report / CONTINUITY |
| Phase B/C validation gates documented | met | docs 07 and 08 |

## Exact modified/added files

Modified:

```
hornlab_search/bo/__init__.py
hornlab_search/bo/metric_model.py
hornlab_search/bo/metric_propose.py
hornlab_search/bo/metric_training.py
hornlab_search/bo/policy.py
hornlab_search/studies/package.py
tests/test_bo_policy.py
tools/analysis/optimizer_switch.py
tools/analysis/study_cohort.py
docs/INDEX.md
docs/CODE_MAP.md
docs/CONTINUITY.md
docs/ISSUES.md
docs/research/metric_bo_2026-11-22/ADR_metric_composite_v1.md
```

Added:

```
hornlab_search/bo/metric_identity.py
hornlab_search/bo/metric_artifact.py
hornlab_search/bo/physical_composite.py
hornlab_search/bo/metric_constraints.py
hornlab_search/bo/metric_diagnostics.py
hornlab_search/studies/metric_study.py
tests/test_bo_metric_identity.py
tests/test_bo_metric_artifact.py
tests/test_study_cohort_fallback_safety.py
tests/test_bo_policy_metric.py
tests/test_bo_metric_acquisition_sign.py
tests/test_studies_metric.py
tests/test_studies_metric_recovery.py
tests/test_bo_physical_composite.py
tests/test_bo_metric_constraints.py
tests/test_bo_metric_diagnostics.py
tests/test_optimizer_switch_metric_advisory.py
docs/research/metric_bo_2026-11-22/02_STUDY_INTEGRATION.md
docs/research/metric_bo_2026-11-22/03_IDENTITY_AND_INTEGRITY.md
docs/research/metric_bo_2026-11-22/04_PHYSICAL_COMPOSITE_RESEARCH.md
docs/research/metric_bo_2026-11-22/05_DIAGNOSTICS_AND_ADVISORY.md
docs/research/metric_bo_2026-11-22/06_SYNTHETIC_VALIDATION.md
docs/research/metric_bo_2026-11-22/07_DEFERRED_REAL_DATA_PLAN.md
docs/research/metric_bo_2026-11-22/08_DEFERRED_GPU_PILOT.md
docs/research/metric_bo_2026-11-22/09_IMPLEMENTATION_STATUS.md
```

Not changed: `objective/scalar_v10.py`, `objective/scalar_v11.py`, `metrics/**`,
`search/**`, `solve/**`, `mesh/**`, `docs/plan/01_CONTRACTS.md`, canonical `ACTIVE_STATE.md`.

## Identity solution (summary)

1. `metric_identity.bounds_identity(strict=True)` hashes a canonical payload containing the
   projection version, ordered active keys, per-key physical `lo`/`hi`, log flag, transform kind,
   active flag and fixed values. Same dimension with a different physical box, changed transform,
   changed active order or changed fixed values all produce a different hash.
2. The artifact records both the payload and its hash; reload re-hashes the payload and refuses a
   tamper. The policy gate requires a caller-recomputed hash and compares artifact, live encoding,
   caller and (when present) proposal/package copies.
3. Score identity binds objective version + brief hash + catalog score identity + score module. It
   is recomputed and compared, never accepted from the artifact alone.
4. Task/backend/fidelity/grid/dependency identities are compared field by field.
5. Missing identity is a typed refusal (`bounds_identity_missing`, `score_identity_missing`,
   `metric_task_identity_mismatch`, …), never an empty-string success.

## Cohort replay solution (summary)

`tools/analysis/study_cohort.py` no longer replays an entire v10/v11 compatible group when no
candidate is encodable. The default is a typed refusal with record counts, per-record encoding
reasons and zero rows replayed. `allow_unranked_replay=True` is explicit and recorded as
`replay_authorized` with `n_replayed`, so it cannot masquerade as ranked selection. Stored J is only
used for ranking when the catalog score identity and provenance brief hash are established; missing
or ambiguous identity excludes the record. Legacy (non-v10/v11) behaviour is unchanged.

## Policy/study integration (summary)

- `PROPOSAL_POLICIES` appends `metric_composite_v1`; labels and `ENGINE_POLICIES` updated;
  verification mode is scalar finalist selection. `PRODUCTION_POLICIES` is unchanged.
- `capability_status`/`fit_and_propose` gained a strict metric branch with reason-coded refusals
  and no fallback.
- `studies/metric_study.py` extends the existing service/builders: `metric_training` +
  `metric_training_manifest` + `model` (manifest, not pickle) + existing `pool` + `proposal` +
  additive synthetic `package` block. `metric_bindings` re-reads and revalidates the stored artifact.
- `metric_execution_gate` refuses real execution even when `allow_real_solver=True`; only an
  explicitly injected synthetic evaluator is accepted. The synthetic evaluator implements the
  existing runner protocol and uses the real `ProductionJournal`.
- `run_synthetic_metric_study` proves the 11-step flow and resume behaviour on synthetic data.

## Known limitations / open items

1. **No real-data validation.** Doc 07 is prepared and labelled
   `NOT EXECUTED - REQUIRES OWNER AUTHORIZATION`.
2. **No matched BEM pilot.** Doc 08 is prepared and not launched.
3. **Independent outputs.** Inter-component correlation is not modeled; `j_sd` is
   `sqrt(sum(var))` under an independence assumption. Optional correlated arm E is not implemented.
4. **Constant components add no directional signal** (documented parking).
5. **Empirical coverage is not calibration.** The diagnostics module reports coverage on synthetic
   data only and labels it not calibrated.
6. **Real execution gate is deliberate.** `metric_composite_v1` is absent from
   `PRODUCTION_POLICIES`; enabling it requires the deferred validation plus a separate owner
   decision.
7. **GUI exposure is unchanged.** The GUI real-run policy list still contains only
   scalar/turbo/pareto; the new policy is not launchable from the GUI.
8. **Synthetic refit artifact is in-memory augmented.** Durable training is the frozen initial
   artifact; new observations are journaled separately and replayed on restore. A future real
   worker should persist an updated immutable artifact per accepted observation batch rather than
   relying on in-memory augmentation.
9. **Platform reproducibility.** Same interpreter/seed/versions is expected to reproduce
   `model_hash`; bitwise identity across different Torch/BLAS builds is not claimed.

## Recommended next authorization

1. Owner-authorized bounded real-data validation exactly as doc 07 (census first, then a scoped
   cohort, then CPU fits and holdouts). No GPU.
2. If that passes, authorize the matched pilot in doc 08 with a declared budget and verification
   policy.
3. Only after both: a separate decision to add `metric_composite_v1` to `PRODUCTION_POLICIES` and
   expose it in the GUI. Do not enable it by default.
