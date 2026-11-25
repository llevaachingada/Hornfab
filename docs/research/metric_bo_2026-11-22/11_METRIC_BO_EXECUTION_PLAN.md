# Metric-aware BO implementation and launch plan

2026-11-23 · Successor to [the Phase B handoff](../../../../hornfab-metric-bo-wt/docs/research/metric_bo_2026-11-22/10_SENIOR_HANDOFF_PHASE_B.md) at `8c815e2e`.

**Updated owner gate for this campaign:** Require **150 qualified unique CMA screens per horn** before BO handoff. Earlier 100-row guidance below describes the existing admission floor. It does not qualify a release under the new campaign. Keep confirmation and verify rows out of the training count when reserved. [Expanded queue and reconciliation](../../queue/v11_bo_day_2026-11-23/CMA_150PLUS.md)

**Locked confirmation verdict, 2026-11-23:** Home v11 Fold cleared the data gate with 174 unique exact-complete screens. The preregistered confirmation used the original frozen 119-row artifact and all 30 exact-complete, nonduplicate Home Fold A transfer observations. On the identical v11 slate, qLogNEI selected measured J 4.869303 for scalar and 5.209300 for composite, with zero top-decile recall for both. The best measured J in the slate was 3.471456. The configured gate was not met. Keep the slate untouched for reporting, with no post-hoc retuning. Real metric worker dispatch remains disabled. Local script and log: `runs/v11_bo_day_planning/fold_a_locked_analysis.py` and `fold_a_locked_analysis.log`.

**Release decision: HOLD for live metric dispatch.** Home v11 Fold has enough eligible CMA data to fit. The locked confirmation remains below the acquisition gate. On that same opened slate, the composite posterior mean ranked the measured winner second versus third for scalar, with latent 95% interval coverage of 63% versus 87%. At 128 draws, composite qLogNEI beat the scalar pick on three of eight sampler seeds. These paired reruns reuse the same candidates and do not count as new evidence. The local diagnostic is in `runs/v11_bo_day_planning/fold_a_diagnose.log`. The production worker still needs to record all six measured v11 terms with replay parity, recover accepted observations on restart and refit from those rows. The offline intake, production wiring and CPU diagnostics can advance while CMA continues. c400b composite ranked worse than scalar on both CPU holdouts.

**Acquisition sensitivity check.** With four fixed sampler seeds and 2,048 draws, every composite run selected the same measured J of 5.583. Scalar consistently selected 4.869. Raising the draw count made the composite pick stable on this slate and left it worse than scalar. Both posterior means selected a horn measured at 4.810. Include posterior-mean ranking as a control in the next comparison. Freeze the 174-row training cohort, identically ordered candidate slates and any model or acquisition changes before reading another run. Record predictive coverage, top-decile recall, measured J of the picks and wall time on an untouched same-identity trajectory. Keep the opened 30 rows for diagnosis only. The draw-count sweep is in `runs/v11_bo_day_planning/fold_a_mc_sensitivity.log`.

**Full-cohort CPU rehearsal.** A strict, byte-round-tripped artifact from the 174 eligible Fold screens fit through `fit_and_propose(metric_composite_v1)`. The first rehearsal found that the older feature checkout's nominal envelope left only 26 legal candidates out of 128 Sobol geometry draws. The feature checkout now includes the open-envelope config, pre-mesh and post-mesh behavior from canonical `07a8d2d0`. The BO pool also uses the configured sanity limit when nominal enforcement is disabled. On the same draws and training checksum, 85 candidates passed cheap checks and BO selected `1797afbe4d5f` in 7.17 seconds. The selected design is approximately 694 × 532 × 489 mm by sampled acoustic surface extents, with no new mesh, BEM result or verification. This size is allowed by the Home Fold open brief. See `runs/v11_bo_day_planning/fold_shadow_open_174.log` and `fold_150_status/shadow_metric_training_open_v1.json`.

**Worker measurement rehearsal.** The feature checkout records the dataset position returned by a successful append. The metric worker branch reads that exact row back, checks the solve triple, catalog task, active bounds and projected design, then compares all six loss components with canonical replay. It saves the catalog physical solve ID alongside replay's separate response identity. The read-only rehearsal passed on all 174 archived Home v11 Fold screens across three runs, comparing against the saved training artifact and catalog. See `runs/v11_bo_day_planning/v11_fold_worker_identity_174.log`. Existing production policy admission still blocks metric dispatch. The refit path still needs to restore journaled observations, append each eligible screen once and prove the next proposal can be resumed deterministically. [BoTorch closed-loop example](https://botorch.org/docs/v0.17.2/tutorials/closed_loop_botorch_only)

The feature-checkout suite covering the envelope, catalog identities, scoring profiles, measurement, search, journal runner, metric intake and offline packaging returned **175 passed, 4 skipped**. A follow-up covering offline provenance and synthetic recovery returned **21 passed**. The rehearsal read existing BEM responses and left the running CMA queue alone.

**Interpreter parity.** The Bayesian interpreter alone reports the archived `hornlab_bempp_bem` pin as `unknown`. Although the Fold solve uses `beat_cuda`, the catalog dependency hash includes the BEM++ distribution. The canonical solver environment has all four archived external pins and lacks BoTorch and GPyTorch. A CPU import check used the Bayesian interpreter with feature source, Bayesian packages and canonical solver packages on `PYTHONPATH` in that order. It imported the correct source and Bayesian libraries and matched all four archived external pins. Rehearse and freeze an equivalent worker environment with the real package. Keep the catalog dependency identity strict.

**Offline package rehearsal.** `freeze_snapshot` resolved the canonical `r3_v11_fold.yaml` and open Home 80×50 brief. The regular study builders ingested and packaged the 174 replayed CMA observations, including the fitted model, 85-candidate pool and metric proposal. Package `9c8862dd0afef2fa31d93866b36c07147b253da94e45726d799bb0eab1d392ba` verified and refused a request for solver authority. The local reproducer and output are `runs/v11_bo_day_planning/fold_metric_service_174.py` and `fold_metric_service_174_final.log`.

**Local coding pickup, 2026-11-23.** The CPU validator fix and regression tests are in the existing `hornfab-metric-bo-wt` feature checkout. Focused tests passed 12/12. The strict probe ran with imports pinned to that checkout and saved artifacts under the canonical `runs/metric-bo-senior-8c815e2e/` directory. A second local agent wrote the fixed-slate v11 Fold acquisition probe, which also passed a rerun using the strict validator directly. On the 30-row fresh-seed and 18-row chronological slates, scalar qLogNEI selected measured J 4.865 and 4.292. Composite selected the actual lowest J on each slate, 3.831 and 3.859. This is retrospective evidence with one acquisition seed. The script and outputs are `acquisition_probe_v11_strict.py` and `acquisition_probe_v11_strict.log`. Next, turn the stored-term and canonical-replay join into the study-service intake in B1, turn the B3 probe into a maintained CPU harness, and pre-register the transferred Home Fold A trajectory as an untouched confirmation set. New solves provide prospective confirmation and additional task cohorts.

**Generated-space follow-up.** A read-only probe using canonical open-envelope code rebuilt and projected the first 12 successful records from each of the five Room 90×50, c500 and FAV runs. All 60 matched exactly. The earlier larger probes used the feature base before the open-envelope correction. Repeat the full scoped replay on the corrected feature checkout before deciding whether there is a remaining recipe-compatibility defect. Durable recipe-based generated intake is still needed.

## What was checked

Execution used the clean existing `feat/metric-aware-bo` checkout at `8c815e2e`, the canonical checkout's explicit round-3 configs, and its consolidated `dataset/`. The canonical checkout was on `hornfab-all-2026-11-18` at `626a7c65` with concurrent edits. Python 3.12.10, torch 2.14.1+cpu and BoTorch 0.18.1 imported from the handoff's Bayesian interpreter, with the repository imports verified against the feature checkout. The following census considers only the twelve named run IDs from handoff §2. It retained successful dataset rows with a response file, exact stored component parity and an exact design round-trip through the current projection.

| Task | Actual objective | Manifest OK | Dataset OK, original + seedspread | Stored terms + encoding | Canonical replay |
|---|---:|---:|---:|---:|---:|
| c400b | 10 | 145 | 113 + 30 | 143 | 143 exact-complete |
| c400a | 10 | 151 | 120 + 29 | 149 | Pending |
| c500 | 11 | 213 | 151 + 60 | 0 with current intake | Pending generated-space fix |
| home_fold_a | 10 | 177 | 146 + 29 | 175 | 175 exact-complete |
| v11_fold | 11 | 121 | 89 + 30 | 119 | 119 exact-complete |
| fav | 11 | 186 | 124 + 60 | 0 with current intake | Pending generated-space fix |

- Every seedspread run is in the store. For the three replayed cohorts, stored J and replayed J were identical and reconstructed stored component sums differed by at most `3.56e-15`. Every successful v11 dataset record in scope carried the balloon CD status and passed the stored-term extractor. c500 and FAV refused at encoding because their generated geometry needs the recorded knob recipe. General `GeneratedSpace.normalize` cannot recover it from geometry alone. A follow-up CPU probe re-materialized the stored knobs with the feature code and current round-3 config. Only **26/211 c500 and 26/184 FAV** matched the original design hash and projected exactly. The remainder need a provenance or generator-compatibility investigation before a recipe adapter can recover them.
- Catalog dependency hash `f4dcdca807bdfad0` and screen grid hash `c41ff9a7581ba429` were stable across the twelve runs. The three replayed cohorts each had one group and mesh-spec hash `8e789cd0deef`. The recorded search code SHA varied across `a30f2de9`, `07a8d2d0`, and `626a7c65`. The dependency hash is separate from that SHA. Round-3 open-envelope behavior landed in `07a8d2d0`; the original feature base lacks it. Historical response replay establishes label parity. Live admission also needs the correct open-envelope behavior and execution pins.
- The current c400 A/B YAMLs differ only by config name and CMA seed. Brief, task, catalog score, grid, dependency and active-box hashes agree in the census. Treat them as separate experiments within a candidate shared task. Before pooling, check every run snapshot, fixed values, effective evaluator behavior and per-record identity. Explicitly allowlist the four runs and deduplicate cross-run repeats. The existing cohort CLI filters by config name, so the two configs are separate in the completed work.
- c400b's replay confirmed a **screen** best of `0.9678663563955058` within its identity. Use it as the screening incumbent. Establish the verify incumbent at verify fidelity before claiming a gain. Keep c400 and Home v10/XO claims scoped to their own briefs, with LF loading, H/V and physical size reported separately. A low J does not establish driver-mounted performance or production size. Use the [OS-SE family card](../../knowledge/typologies/osse_ath.md) and [experimental morphs card](../../knowledge/typologies/experimental_morphs.md).

### P0 artifact blocker and local evidence

`design/generated.py::brief_hash` emits a SHA-256 prefix of 12 lowercase hex characters over the resolved brief without its path. `bo/metric_identity.py::score_payload` calls the generic token validator, which requires at least 16 characters for both brief and catalog score. All three real artifact builds failed:

```text
r3_c400_b 143 strict_artifact_refused ("identity:score_payload_invalid:brief_hash is not a catalog identity token: '16825ffd3faf'",)
r3_home_fold_a 175 strict_artifact_refused ("identity:score_payload_invalid:brief_hash is not a catalog identity token: '7940664a60cf'",)
r3_v11_fold 119 strict_artifact_refused ("identity:score_payload_invalid:brief_hash is not a catalog identity token: 'c6bc496e7b4f'",)
```

Canonical local evidence is in `runs/metric-bo-senior-8c815e2e/`. Each `cohort-*/` contains `offline_scores.json` and `catalog.csv`. `audit_probe.py` reproduces the strict refusal from those files. `audit_probe_exploratory.py` tests an in-process tokenizer correction permitting the writer's exact format, with equality and catalog score checks still enabled. Three artifacts round-tripped in memory. This experiment produced no release artifact, source change or GPU solve.

The focused feature-checkout acquisition-sign, metric-identity and cohort-selection tests returned `16 passed, 2 warnings in 6.16s`. The warnings were GPyTorch training-input warnings from the acquisition-sign fixture. The production brief-token failure surfaced only on the real artifact input.

### Preliminary model comparison

The probe loaded the canonical v10 four-component vectors, used identical observations and vectors for each pair, and called the existing scalar and metric model APIs on CPU float64 with seed 0. The original trajectory provided the training set for the whole seedspread holdout. The chronological check used the tail of the original trajectory. There were no shared design hashes across either split. Prediction ranking was by posterior mean J. Top-decile recall uses three designs in each test split.

| Holdout (train/test) | Arm | Spearman ↑ | Top-decile recall ↑ | Best actual J in predicted top 3 ↓ | MAE ↓ | Empirical latent 95% coverage |
|---|---|---:|---:|---:|---:|---:|
| Seedspread (113/30) | Scalar | 0.240 | 1/3 | 1.311 | 1.310 | 90.0% |
| Seedspread (113/30) | Composite v10 | 0.097 | 0/3 | 1.959 | 1.391 | 73.3% |
| Original tail (90/23) | Scalar | 0.576 | 1/3 | 1.354 | 0.620 | 91.3% |
| Original tail (90/23) | Composite v10 | 0.423 | 1/3 | 1.354 | 0.700 | 91.3% |

The follow-up used the same protocol on Home Fold A and v11 Fold. Each cell shows scalar → composite. Full metrics and warnings are in `audit_probe_all_holdouts.log` beside the replay outputs.

| Task and holdout (train/test) | Spearman ↑ | Top-decile recall ↑ | Best observed J in predicted top decile ↓ | Empirical latent 95% coverage |
|---|---:|---:|---:|---:|
| Home Fold A, seedspread (146/29) | 0.586 → 0.660 | 1/3 → 1/3 | 1.617 → 1.617 | 89.7% → 89.7% |
| Home Fold A, original tail (116/30) | 0.442 → 0.385 | 1/3 → 1/3 | 1.461 → 1.461 | 80.0% → 73.3% |
| v11 Fold, seedspread (89/30) | 0.495 → 0.730 | 0/3 → 1/3 | 4.378 → 3.831 | 86.7% → 53.3% |
| v11 Fold, original tail (71/18) | 0.428 → 0.579 | 0/2 → 1/2 | 3.910 → 3.859 | 77.8% → 66.7% |

**Prioritize v11 Fold for confirmation.** It improved ranking and top picks on both splits. The 18-row tail falls below the proposed 20-row test floor, and the coverage loss makes acquisition behavior especially important to measure. Home Fold A tied on top picks and had mixed rank results. c400b stays on hold. Keep all six splits as known evidence and pre-register additional locked evidence for confirmation. The follow-up qLogNEI probe above used only the two known v11 Fold slates and one acquisition seed. Independent-output GPs assign no cross-output posterior covariance, and qLogNEI maximizes the sample-level negative sum of the canonical losses. [BoTorch model documentation](https://botorch.org/docs/models) · [BoTorch acquisition documentation](https://botorch.readthedocs.io/en/latest/acquisition.html) · [Astudillo and Frazier](https://proceedings.mlr.press/v97/astudillo19a.html)

## Orchestrator start here

Copy each block as one dispatch prompt. The parent holds the phase gate, sole Git integration, and the run ledger. Each return must contain changed paths, exclusions or refusals, exact commands and output, and the next admissible slice. Any failure stops its dependent slices while independent lanes continue. Keep the canonical live checkout and active writers intact. Run all CPU work with explicit imports, pinned interpreter and BLAS/Torch thread caps. Treat archived handoffs as evidence, and follow the canonical owner amendment and current `AGENTS.md` for execution routing.

| Order | Dispatch | Gate |
|---|---|---|
| 0 | Parent resolves clean integration route and preserves the live tree | Integrated baseline proven CPU-correct for the round-3 open configs |
| 1 parallel | B1 identity and intake, B2 generated knobs, B3 evaluation harness | B1 and B3 join for real task results. B2 is independent and optional for first release |
| 2 | B4 decision | A named task passes data, identity, model and acquisition checks |
| 3 parallel | C1 package and operator path, C2 worker and journal | Shared adapter interface frozen before edits. Combined end-to-end acceptance required |
| 4 | C3 GUI and release rehearsal | Real package remains default-denied. No solve claims on dry-run |
| 5 | D1 gated exploratory screen/verify | Any real launch requires explicit recorded authorization and a free GPU lane |
| 6 | D2 matched pilot | Owner promotion decision supported by prospective verified evidence |

### 0. Reconcile checkout and launch configuration

```text
Model: GPT-6.2 Astra, high. Owner: parent integrator.
Task: reconcile 8c815e2e with the canonical live checkout. Read canonical AGENTS.md,
the exact git status, merge-base and branch-only diffs. The feature base is a30f2de9.
Canonical committed 07a8d2d0 adds open-envelope config, generator feasibility and
post-mesh rejection logic missing from the feature checkout. Canonical also has active
dirty BO/studies files. Preserve them and coordinate ownership before integrating.
Use the named existing feature checkout for audit/repro only until the integration route
is settled under the owner amendment. Do not make a new checkout or stage shared edits.

Freeze the chosen config plus recursive includes/brief, saved run snapshots, installed
dependency pins and execution code. Record source hashes for scorer, writer, replay,
encoding, evaluator, objective inputs and worker. Exercise open-envelope decisions
in pre- and post-mesh paths with CPU fixtures, including a design over nominal size
but within the 1200 mm sanity limit. For any old search SHA, explain compatibility
from function/file evidence and replay, and quarantine unknown behavior. A matching
fork hash alone is insufficient. Recheck GUIs and wrappers against the integrated base.
Return the reviewed baseline, exact launch configuration path, import provenance,
status and handoff for B/C. No BEM or Git push in the audit slice.
```

### B1. Fix the identity seam and publish strict real training intake

```text
Model: GPT-6.1 Terra, medium. Own bo/metric_identity.py, the real offline intake
boundary in tools/analysis/study_cohort.py and focused identity/intake tests. Coordinate
with B3 on input schema. Work against the parent-approved baseline.

Reproduce the exact three failures using canonical runs/metric-bo-senior-8c815e2e/
audit_probe.py. Implement a field-specific brief validator supporting the canonical
12-hex writer token and the existing 16–64 hex contract. Keep score_hash validation
and exact comparisons intact. Never pad, replace or derive a trusted token from an
unrelated hash. Recompute the writer brief token from the independently loaded brief.
Separately pin the full resolved brief and config bytes, including includes, and verify
the canonical scorer inputs. Do not conflate the short writer token, catalog score token,
canonical replay score ID, and study snapshot brief file SHA. Catalog score identity
encodes schema/target, so matching it cannot establish weight/tolerance equivalence
alone. Keep exact expected-task comparisons for backend/fidelity/grid/dependencies/
mesh policy. Preserve per-design IDs and provenance and distinguish a mesh-spec pin
from geometry.

The usable join is the scoped dataset shard row + catalog physical ID + exact_complete
canonical replay row. Extract contributions from the stored terms with the resolved
canonical params and check independently against stored objective and replay J at
PARITY_ABS_TOL/PARITY_REL_TOL. Build actual MetricTrainingCandidate objects with
components and exact vector round-trips. Refuse identity mismatch, no fallback CD/DI,
malformed records, parity errors and unverified source. Record exclusions before the
cap, reject inconsistent duplicates and keep run/timestamp locators. A selected
pre-replay candidate list from study_cohort is only a shortlist. Require at least
100 unique qualified screens for the release artifact plus full strict serialization,
verified reload and immutable publish. A smaller train-only research split may use the
engine minimum max(16, 2*(d+1)). Use no replay widening.

Tests: real writer-format fixtures for v10/v11, existing token compatibility,
invalid length/hex/wrong hash, exact score and bounds drift, artifact mutation,
mismatched terms/weight under a matching catalog schema, cuts fallback and bad joins.
Preserve legacy cohort paths. Show byte-identical strict reload for c400b (143),
home_fold_a (175) and v11_fold (119), or give exact attrition. Leave Phase C held.
```

### B2. Reconstruct historical generated-space inputs

```text
Model: GPT-6.1 Terra, medium. Own generated historical intake and tests, with one
agreed call-site seam owned by B1. Read design/generated.py and bo/encoding.py. Audit
the 211 c500 and 184 FAV successful rows separately. Build a historical path from
provenance.generator knobs + resolved generator spec/brief to Design. Validate exact
knob key set, finite values and bounds before conversion. Re-materialize, compare
the recorded design hash, then encode through ActiveProjection and prove exact
round-trip. Fail closed on a missing or changed recipe, changed geometry, altered
fixed values, out-of-box input or a legacy record with no proof. No clipping or
reverse-engineering shape knobs. Measure materialization cost and consider caching
within the offline run with a fully pinned key. Keep both tasks out of launch until
their own exact replay, strict artifacts and held-out verdict pass. This work does
not block the first normal DesignSpace task.
```

### B3. Build and run a reproducible Phase B comparison

```text
Model: GPT-6.1 Terra, high. Own a CPU analysis CLI and its tests. Read
bo/model.py, bo/metric_model.py, bo/acquisition.py, bo/metric_objective.py and
bo/metric_diagnostics.py. Use B1's verified input contract. Build the harness in
parallel against fixtures, then run c400b, home_fold_a and v11_fold individually.
The synthetic diagnostic times prediction under its acquisition label. Time real
fit, prediction, acquisition build, fixed-pool scoring and proposal separately.

Before reading results for untested cohorts, record input IDs, splits, metrics and
decision criteria. Split by original trajectory vs fresh seed run, and by a temporal
cut (suggest first 80% of original-only training, final 20% test). Validate chronology
from ordered dataset time/locator and remove cross-split exact/near-duplicate design
vectors using the existing policy tolerance. Whole-run test must be untouched by
training selection. Use only training rows for selection, clipping checks, target
standardization, local reference points and any model initialization. Require at
least engine minimum training rows and 20 unique held-out rows with at least two
top-decile selections. For c400 A/B, use an explicit authorized config/run allowlist
and no cross-arm data during a matched trial. Freeze splits with hashes.

Primary: native scalar GP (Y=-J) versus actual metric_composite_v1 (sample utility
=-sum(components)). Use identical train/held-out IDs, input vectors, fidelity,
seed and pool. Compare posterior-mean held-out rank and actual qLogNEI ranking on
the same legal held-out candidate slate; compare the measured J of those selections.
Check maximization sign with asymmetric known losses. Report Spearman,
top-decile recall, best observed J in predicted top k and regret from holdout best,
MAE, RMSE, bias, empirical latent 95% coverage, candidate disagreement, flags and
timings. Fail on nonfinite or missing predictions rather than filtering them away.
Report CD status and output scales/parked constants. CPU temperature/startup order
can skew timings; warm both and repeat timing under equal thread caps.

Secondary ablations only after the primary results: A scalar with matched GP
settings versus grouped components. v10 two-group = load and sum of other three;
v11 two-group = load + other_base and sum of four CD contributions. v11 six-output
is the real v11 policy, and v10 four-output is the real v10 policy. Every grouping
must sum to the same task's J. Optional correlated research uses the same rows
and frozen split; keep it separate from production. Do not change the scorer.
```

### B4. Record a task-level decision before any worker promotion

```text
Model: GPT-6.2 Astra, high. Owner: parent. Verify B1/B3 outputs, code pins,
artifact checksum, SHA-256, cohort row flow and exact component parity. Require a
full 100 qualified screens and both informative holdouts. Suggested conservative
launch screen for untested cohorts: no loss in top-decile recall or best observed
J in predicted top k on either split, with Spearman and qLogNEI held-out choices
checked for material degradation. Freeze the criteria, any numeric margins and a
proposal wall-time cap before reading untested results; show raw scores, including
ties and coverage. Record PASS FOR EXPLORATORY PILOT, HOLD or INSUFFICIENT EVIDENCE.
These small retrospective splits are inadequate for default promotion.

c400b starts HOLD on the known results, even if the strict artifact fix passes.
Do not quietly change split, bounds, kernel or output set to win the same test.
If c400b remains the priority, diagnose seed-domain coverage, constant/outlier
components, residual dependence and high local errors. Keep the v10 objective
and historical rows fixed; evaluate any model change on untouched trajectories.
Prioritize v11 Fold for new confirmation and acquisition tests. If it or Home Fold A
passes, name the candidate and evidence in the approval
record. Do not compare raw J between candidate tasks when choosing the pilot.
```

### C1. Implement the production package and command-line preparation flow

```text
Model: GPT-6.1 Terra, high. Own studies/package.py, shared package contracts and
CLI preparation. Coordinate one frozen interface with C2 before edits. Develop
offline with fixtures after B1. Keep real dispatch held until B4 passes.

Trace metric_study.metric_bindings, prepare_metric_run_package and
metric_execution_gate. package.py currently requires synthetic=true and
real_solver_allowed=false for every metric package. Add an explicit versioned real
metric package contract that is refused unless it has a named approved task and
artifact, strict bindings, declared budget, and a pinned real evaluator. Keep the
existing synthetic package gate intact. Validate the complete file set and every
solver-relevant pin, compare frozen config and dataset identities, and reject
unknown policy/package mixes. Treat missing config/parents/brief or a stale snapshot
as refusal. Use a placement allowed by builders._path or explicit typed source
root handling; do not weaken arbitrary client path containment. Separate prepare,
inspect/plan, and execute. Reuse tools/night_queue/run_bo_arm.py concepts and the
existing service, but prove the actual new CLI prepare + dry-run path. Record exact
commands and package hashes. Dry run and package preparation must make zero backend
calls. Verify byte integrity and fail closed on tampering, changed briefs or
bounds, or no approvals. Keep canonical old studies readable and runnable.
```

### C2. Bind the metric worker, measurements and refit transaction

```text
Model: GPT-6.2 Astra, high. Own studies/production.py, studies/evaluator.py and
the metric refit adapter in studies/metric_study.py after agreeing C1's interface.
Use the existing ProductionJournal and runner. execution_capability currently
blocks v10/v11 and the worker resolves scalar training. Branch on the real metric
package and enforce v10/v11 for it while preserving legacy v4/v7 policies. A policy
tuple append alone cannot release real execution. Keep real evaluator coupled to
the immutable task/config and full proposal bounds checks.

Wire MetricTrainingBinding into fit_and_propose with require_identity=True. Draw
history, excluded/busy hashes and proposal RNG/index from the respected durable
state. Recheck manifest+artifact on resume and before proposals. Reuse existing
typed failures, reservations and reconciler. After each counted screen, durably
reference the original measurement and canonical replay result, with full row
identity, unit vector, stored/replayed J, components, CD and quality flags.
evaluator.py's two normalized terms are insufficient. Exclude failed, verify,
fallback, duplicate and parity-failed rows from training, while every real backend
call remains in its budget ledger. Use stored canonical extraction and replay
cross-check, never posterior J.

Continue from the feature checkout's record_metric_measurement and
load_metric_dataset_record. Keep result.metric_dataset_record.physical_solve_id
as the deduplication key shared with the base cohort. result.physical_id is the
replay response identity and uses a different formula. Preserve the current
bind_metric_record_identity check, which shares the catalog projection and
validates the reported design against the pinned active vector before refit.
During recovery, accept
the exact durable reference for the committed attempt and reject ambiguous
matches. A directory named screen is common to every study and cannot identify
an attempt by itself. Carry the package/attempt identity for recovery.

Refit on a frozen cadence of accepted unique screens. Publish an immutable,
content-addressed artifact over the base cohort plus journal-confirmed accepted
rows before atomically advancing the current refit pointer. Pin source high-water
mark, selected IDs, cap/selection, snapshot, model input SHA and policy/RNG state.
On crash, reconcile reservations and replay results first. Recover by reusing the
same artifact and next candidate, with no duplicate solves or accepted rows.
Replay mismatch or failed fit pauses the arm with its last good state and a typed
reason. Resume must never silently switch to scalar, reinterpret a cap or retry
a spent budget. Exercise interrupted publication, duplicate result, stale artifact,
failed BEM, result-before-finalize, cadence crossing and restart tests through the
production-shaped runner with fake backend dispatch. Record an actual second refit
with a changed accepted-row set and reproducible proposal state.
```

### C3. Operator surface and release rehearsal

```text
Model: GPT-6.1 Terra, medium. Own gui/data_studies.py, gui/study_jobs.py and
focused UI tests after C1/C2 agree on policy_status and action routing. Make the
metric choice opt-in, showing task identity, qualified count, artifact revision,
readiness/refusal, actual observed J and separate predictions. Prove the GUI
build and launch actions reach the same checked API and cannot enable a live solve
from synthetic artifacts or a fall-through scalar configuration. Preserve existing
policy order/defaults. A reviewed command-line canary may precede exposing the GUI
launch control. Rehearse CLI and GUI with the same real-shaped fixture and fake
backend. Test invalid package and all policy routes, then run the project CPU
regression profile. Record targeted test output and attach readiness evidence.
This slice finishes documentation and dry-run rehearsal. Queue stays unchanged.
```

### D1. Exploratory canary, adaptive study and verification

```text
Model: GPT-6.2 Astra, high. Owner: parent/operator only. Require a written
B4 pass on the same frozen identity, C dry-run and crash tests, and recorded owner
authorization for this exact GPU task, screen and verify caps. Apply HornLab
gpu-job, night-queue, search-economy and shape-check as applicable. Verify
tools/night_status.py and live locks; yield until the lane is free. Apply
HORNLAB_GPU_LOCK=refuse, check the worker lane identity, clean only stale hosts per
GPU skill and capture VRAM baseline/spill. Never preempt active work. Use a
dedicated detached queue/controller, explicit interpreter, task package, dataset,
attempt ledger and immutable starting artifact. Dry-run exact argv first. Command
jobs need explicit study-side stopping because queue search watchdog semantics may
not apply.

For the first identity that passes, propose one candidate at a time. Suggested
initial authorization: 8 new screen backend calls with a refit after each 4 accepted
unique screens, then one same-identity adaptive tranche toward 25–30 total screen
calls only if the canary shows valid replay/identity, no duplicate calls, successful
refit-driven proposals and tolerable overhead. Stop on any identity/parity error,
budget accounting inconsistency, persistent fit/proposal failure, lock conflict
or unexplained invalid/duplicate streak. Failed calls consume budget. Track
candidate support and bound pinning. Confirm same backend, screen mesh/grid, and
actual config/dataset pins for every accepted observation.

Budget verify separately. Freeze four screen finalists and two audit slots in
advance, including a same-brief verify incumbent as an audit if there is no
existing verify result at the exact identity. Keep verify rows out of screen
training. Record matched verify J, H/V/directivity, LF loading, coverage,
geometry/SPL sanity, dimensions and screen-to-verify rank changes. Stop and report
when the cap completes. This is an exploratory operational result from one study.
Opening pinned bounds is a separate named task; it changes the search identity
and requires re-admission against audited observations.
```

### D2. Match budgets and decide whether to promote

```text
Model: GPT-6.2 Astra, high. Owner: parent/operator. Follow feature doc 08 after
D1 and explicit campaign approval. Run continued CMA, existing scalar BO (or one
preselected scalar TuRBO), and metric composite over the same authorized task,
starting cohort/incumbent, fixed active box, mesh/frequency tiers, dependency pins,
package/code and verification rules. Ensure the scalar comparator is actually
supported on the selected v10/v11 task through a reviewed reference adapter
without changing legacy defaults. Freeze how CMA receives its checkpoint/seed
and what history every arm may see. Start with multiple paired seeds; two are
exploratory. Prevent cross-arm leakage via pinned cohorts/namespaced study history
and explicit cache policy. Rotate arm order where feasible on the one GPU.

Pre-register the primary endpoint as verified J improvement from the common
verify incumbent at a fixed total compute budget with named acoustic
acceptability criteria. Record the equal-screen-count result as well. Count
actual backend calls, failures and verify screens separately, and show CPU
fit/proposal, GPU solve, verification and total wall-clock time by arm. Report
H/V, LF loading and size without rolling them into a new score. Report paired
per-seed outcomes and uncertainty. If observed gains are within seed/measurement
variance, return INSUFFICIENT_EVIDENCE. Promote defaults only with a recorded owner
decision and verified benefit under this matched protocol.
```

## Reproduce the completed bounded replay

From the existing feature checkout at `8c815e2e`, use the canonical input root. This is a local CPU replay of selected stored responses. The catalog CLI uses `--root` and does not expose the handoff's advertised `--dataset/--run-id` census flags. `study_cohort` enumerates the consolidated shard metadata, filters the allowlisted run IDs and replays selected observations. Its `--limit` selects training rows, so use a separate immutable run allowlist and inventory.

```powershell
$py = 'C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe'
$canon = (Resolve-Path '../hornlab-search').Path
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$rows = @(
    @('r3_c400_b', '16825ffd3faf', 'b2c8982ca1792991', '20261122T221847Z-screen-5857d8', '20261123T153053Z-screen-22c95a'),
    @('r3_home_fold_a', '7940664a60cf', '3f3b428ed532c34f', '20261122T205923Z-screen-391141', '20261123T161240Z-screen-6db400'),
    @('r3_v11_fold', 'c6bc496e7b4f', '77d4fdd49bd2c3b4', '20261123T001107Z-screen-c88c3d', '20261123T162314Z-screen-9a1835')
)
foreach ($row in $rows) {
    $name, $brief, $score, $first, $second = $row
    $config = Join-Path $canon "examples/typologies/round3_2026-11-22/$name.yaml"
    $out = Join-Path $canon "runs/metric-bo-senior-reproduction/cohort-$name"
    & $py -m tools.analysis.study_cohort --config $config --dataset (Join-Path $canon 'dataset') `
        --out $out --limit 256 --run-id $first --run-id $second `
        --expected-score-identity $score --expected-brief-hash $brief
    if ($LASTEXITCODE -ne 0) { throw "Cohort replay failed for $name" }
}
```

At integration, index the plan and update CODE_MAP for new code. Any pushed commit needs the repository's CONTINUITY and ISSUES changes with scoped, verified evidence. Keep raw response arrays, derived training arrays and local study state out of Git.
