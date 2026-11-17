# Local optimizer audit and switch implications (read-only)

- Repo: `C:\Users\hunte\Hrns\hornlab-search`; HEAD at final write
  `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` (`2026-11-16T20:38:46-05:00`). Files were read at
  `13b47632` and are byte-identical at `5cc83af`/`601be8c`; HEAD moved during the pass. A live
  julia/python solve was reported and was not touched.
- `git diff --name-status 13b47632..HEAD` touches only CROWE/Klangfilm design/docs/tools paths, not
  `bo/*`, `search/*`, `studies/*` or `tools/*queue*`. The tree is dirty (27-30 paths during the
  pass); `bo/diagnostics.py` is modified but not cited. This is the optimizer part for the parent
  `OPTIMIZATION_AND_BRIEF_AUDIT.md`, in the same evidence style.
- Status legend: **verified** = read at the SHA or computed read-only; **historical record** = past
  report/run number; **documented only** = plan/README without executable code; **plausible
  inference** = follows from code but not exercised; **unverified**; **contradicted**.

## 1. Bottom line

1. Five policies are **implemented** (`scalar`, `pareto`, `cma_seed`, `exploration`, `turbo`:
   `bo/policy.py:43-51`), but only `scalar`, `turbo`, `pareto` are **executable by the production
   study worker** (`studies/production.py:49-50,120-123`). `cma_seed`/`exploration` are
   dispatcher/test paths; the adaptive runner never selects them.
2. There is **no in-run policy switch**. A package's policy is frozen; changing it invalidates the
   package (observed `adaptive_policy.manual_change_invalidates` includes `"policy"` in
   `runs/bo_multityp_2026-11-16/bo_cov_s71001/package.json`; `studies/runner.py:87-114,166-233`).
   The evaluator only **refits the same policy** (`studies/evaluator.py:636-680`).
3. Scalar BO is a **single-output GP over one frozen task/cohort**, not multi-task/multi-fidelity
   (`bo/model.py:1-14,313-386`). It does not learn from refusals: they are excluded from training
   (`bo/data.py:5-6,107-112,241-275`; `bo/cohort.py:94-107`); "BoTorch learns from every refusal"
   is false here.
4. The historical BO-vs-CMA comparison is **unequal in information and refusal handling**: BO had
   185 prior rows and a size-pre-checked 4096 pool; CMA had one starting design and lost 14-29 of
   60 attempts to "too large" refusals (`docs/status/2026-11-15-bo-vs-cma/README.md:15-22,30-37`).
   It supports these workflows, not a universal optimizer ranking.
5. Raw valid rows are not BO readiness. The builder needs `n_min=max(16,2(d+1))` unique eligible
   designs and study prep applies a **100-row spend floor** (`bo/data.py:71-75`;
   `tools/bo_compare/prepare_study.py:76-77,163-169`; `run_matched_home.py:35-39`). The Le Cleac'h
   cohort has 80 `exact_complete` rows in `offline_scores.json` but **one usable row** after strict
   gates (`docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md:39-44`).
6. Two strict gates disagree on version: `bo/cohort.py` refuses `objective_version != 4` (`:96-97`),
   while the production native builder accepts the brief's version, including v7
   (`bo/data.py:498-500,657-665`; `studies/production.py:143-146`). "cohort.py refuses v7" is
   **verified**; v7 studies are not impossible because they do not call `validate_cohort`.
7. A prepared package can be **unexecutable after code changes**: the cov pilot pins 155 files and
   18 differ now, including `bo/policy.py` and `studies/evaluator.py` (`package.json`, `code_pins`;
   `studies/production.py:90-96`). Its deadline `2026-11-16T07:13:55Z` is also past
   (`production.py:116-119`). This is a read-only hash comparison, not a launch.

## 2. Implemented versus documented

| Capability | Status | Evidence |
|---|---|---|
| Scalar BO (qLogNEI, one GP) | implemented | `bo/model.py:1-14,204-413`; `bo/acquisition.py`; `bo/propose.py`; dispatcher `bo/policy.py:617-631` |
| TuRBO (`turbo_pool_v1`) | implemented, HornLab variant | `bo/turbo.py:1-26,130-175,272-421`; production gate `studies/production.py:186-191` |
| Pareto (coverage/ripple, qLogNEHVI) | implemented, independent GPs | `bo/pareto.py:128-156,278-308,311-355`; production gate `production.py:192-193` |
| Constrained Pareto (loading margins) | code exists, **not wired** | `bo/pareto.py:90-125`; plan says "margins exist ... but are not wired in" `docs/queue/BO_EXT_PLAN_2026-11-16.md:70-74` |
| CMA-ES with IPOP/BIPOP restarts | implemented | `search/cma.py:16-22,422-480`; config block `search.restarts` |
| CMA-ME / MAP-Elites | implemented | `search/cma_me.py:1-45,220-284,319-405`; ribs 0.12.0 |
| NSGA-II | library implemented, **not a CLI algorithm** | `search/nsga.py:1-8,94-165`; dispatch rejects it: `search/cma.py:496-506` |
| Warm start (mean/sigma from prior runs) | implemented for CMA/CMA-ME | `search/warmstart.py:1-16,57-127`; used `search/cma.py:517-530`, `search/cma_me.py:357-370` |
| Validity/refusal handling in BO | implemented as exclusion | `bo/data.py:68,107-112,241-275`; `bo/cohort.py:94-107,145-151` |
| Discrete/categorical BO | **refused** | `bo/encoding.py:116-129,242-254,313-328` |
| Mixed fidelity in native BO cohort | allowed by default, published; strict cohort refuses | `bo/data.py:380-387,744-747`; `cohort.py:119-125,143-144` |
| Partial pooling across policy conflicts | **not implemented** (whole cohort refused) | `cohort.py:53-54,143-144`; `bo/data.py:744-747,772-775` |
| Multi-task / cross-family GP | **not implemented** | one `SingleTaskGP`, `bo/model.py:1-14`; config-name gate `bo/data.py:541-545` |
| Cost-aware acquisition | code exists, **not wired** | `bo/extensions.py:40-71`; needs >=30 uncached timings; plan `BO_EXT_PLAN:72-74` |
| Active subspaces / global sensitivity | **not implemented**; CMA covariance summary only | `search/cma.py:246-314` (local search covariance) |
| Automatic policy switching | **not implemented** | `studies/runner.py:87-114,166-233`; `studies/evaluator.py:636-680` |

## 3. Scalar BO: what the GP actually sees

**Training rows.** Only observations with `eligible=True` and `status in {ok, complete, success,
valid}` are used; solver/infra/gate failures are excluded by typed status, never by a large `J`
(`bo/data.py:48-68,107-112`). `Y=-J` is the target (`:309-311`); no fabricated `J=1000` row and no
failure relabelled as acoustic (`:338-357`).

**Selection and model.** Below `n_min=max(16,2(d+1))` unique geometries the result is
`needs_initial_data` with a scrambled-Sobol manifest and no trained model
(`bo/data.py:71-75,278-297`; `bo/model.py:226-235,254-261`). Above `n_max=256`, keep the 64 lowest-J
rows plus deterministic maximin rows (`bo/data.py:29-30,299-307`); duplicates are collapsed by
`(geometry_hash, solve_hash)` (`:241-275`). The model is SingleTaskGP + ConstantMean +
ScaleKernel(Matern-5/2, ARD) + Standardize, fixed tiny noise, one exact-MLL attempt, <=100
iterations, float64 CPU, two Torch threads, never CUDA (`bo/model.py:1-14,38-52,313-386`). Flat
response is `flat_training_response` (`:290-295`); negative predicted J is flagged, not clamped
(`:500-564`).

**No constraints in scalar BO.** qLogNEI runs over a finite pool; feasibility is handled by pool
construction and post-selection validation, not a constraint GP (`bo/model.py` has no constraint
output; `bo/propose.py:472-501` validates). The GP has no notion of "near the envelope".

## 4. When a GP may share observations

The code answers this with identity gates, not with a task-similarity model.

| Dimension | May share? | Gate |
|---|---|---|
| Shape family / task | **No**, unless it is the same registered task | `data.py:541-545` requires the catalog and score row to name `expected_config`; `cohort.py:126-132` requires `task == s0.config_name` |
| Source model | **No explicit sharing**; only indirect identity | `cohort.py:126-132` requires `excitation == s0.excitation`; `brief_hash`, `task_identity`, `config/brief` hashes are policy fields (`data.py:385-387`; `production.py:136-140`). There is no separate `source_model` field |
| Mesh / fidelity | **Mixed only in the native builder, and published** | `NATIVE_FIDELITY_FIELDS = (fidelity, grid_hash, solve_hash)` and default `require_single_fidelity=False` (`data.py:380-387,744-747`). The strict cohort path requires one `fidelity`, `frequency_grid`, `mesh_policy` across rows (`cohort.py:119-125,143-144`); study prep passes `require_single_fidelity=True` (`builders.py:574-577`; `tools/bo_compare/prepare_study.py:163`) |
| Score definition | **No** | `objective_version`, `target`, `weights`, `metric_source`, `resolved_brief` must be equal across rows (`cohort.py:96-97,108-144`; `data.py:657-675,693-705`). J across versions is never ranked (`AGENTS.md`; `objective/versions.py:11-19`) |
| Encoding / active keys | **No** | `encoding` is a policy field (`cohort.py:20-22`); `build_proposal` refuses if `training_set.d` or `active_keys` differ from the selected task (`builders.py:1109-1111`) |
| Partial pooling | **No** for policy conflicts | `validate_cohort` returns no observations on any refusal (`cohort.py:53-54,143-144`); `build_native_training_set` marks the whole set `incompatible_cohort` / `capability_missing` (`data.py:744-747,772-775`). The only permitted "mixture" is declared mixed fidelity, and even that is only published, not corrected |
| Multi-task GP | **No** | `bo/model.py` constructs one `SingleTaskGP`; no task index/kernel sharing |

`cohort.py`'s cross-row fields are `task`, `resolved_brief`, `target`, `score_policy`,
`metric_policy`, `frequency_masks`, `backend`, `fidelity`, `mesh_policy`, `frequency_grid`,
`dependencies`, `excitation`, `encoding` (`:20-22`). `resolved_brief` must use the R0 namespace
(`:133-134`); same-`physical_id` with a different metric/score/design/vector/J is `incompatible`
(`:156-159`); source root/shard/row must join exactly (`:85-93`). This is a strong no-leakage gate,
and it is why cross-typology pooling is a different model, not a config change.

**Fidelity caveat.** The native builder's default mixed-fidelity mode does not make screen-J and
verify-J interchangeable. The M0 freeze declares a mixed 192-screen + 5-verify cohort
(`data.py:380-387,464-472`); `require_single_fidelity=True` is the opt-in refusal. Historical median
screen-to-verify drift was +3.4% (BO) and +9.4% (CMA), worst 13.8%/18.4%
(`docs/status/2026-11-15-bo-vs-cma/README.md:47-54`). Mixed-fidelity training assumes a ranking
stability the report only partly supports; `bo/data.py` adds no fidelity covariate/noise term.

## 5. Active dimension, discrete values and clipping

- `MIN_ACTIVE_DIM = 1`, `MAX_ACTIVE_DIM = 20`; outside that range construction refuses
  (`bo/encoding.py:21-22,119-122`). Home v7 tasks are d=6/9/14; no current task hits 20.
- A discrete/categorical/bool active dimension is refused statically from the family `KeySpec`
  table and from a runtime discrete value (`encoding.py:55-63,116-129,313-328`). CAD/grid designs
  carrying a recipe rather than invertible continuous parameters are refused (`:242-244`). There is
  no one-hot, ordinal, or conditional-parameter encoding in this module.
- Historical observations outside the resolved box are **never clipped**; `HistoricalClippingError`
  is raised (`encoding.py:255-260`; `data.py:236-240`). A new proposal that leaves `[0,1]` also
  refuses unless the caller explicitly passes `clip=True` for an in-box proposal
  (`encoding.py:276-289`). Candidate-pool construction clips only its own local Sobol points to
  `[0,1]` (`bo/turbo.py:211`), not historical rows.
- The active projection drops only explicit `no_ops`; it does not learn a subspace
  (`encoding.py:93-130`). The official ATH projection drops `morph_exponent` at
  `morph_target == 1` for the ATH task (`builders.py:810-815`; `data.py:485-489`).

**Open inconsistency (plausible inference, not exercised).** `build_native_training_set` builds
`no_ops = {"morph_exponent": 4.0}` whenever the key exists (`data.py:485-489`), while the study
proposal encoding only drops it when `seed.params["morph_target"] == 1` (`builders.py:810-815`).
For a task with both a `morph_exponent` key and `morph_target == 0`, the training projection and
the proposal projection can have different `d`/`active_keys`, and `build_proposal` will refuse
(`builders.py:1109-1111`). The current home v7 tasks have no `morph_exponent` (`data.py:485-489`
comment), so this is latent. It is worth a targeted unit test before adding such a task.

## 6. v4-only versus v7 rows: two gates, one name

There are two different "cohort" gates:

1. `bo/cohort.py::validate_cohort` is the strict joined S0/R0 gate. It hard-codes
   `r.get("objective_version") != 4` (`:96-97`) and is called by `bo/pipeline.py`; the
   Pareto-from-cohort path accepts only a successful `CohortResult` (`bo/pareto.py:159-172`).
   It **does refuse v7 rows** (verified).
2. `bo/data.py::build_native_training_set` is the production study path. It reads the brief's
   objective version (`:498-500`) and compares each score/catalog row to that expected version
   (`:657-665`). It accepts v7 and is what `studies/builders.py:558-585` calls. Production supports
   objective v4 and v7 (`studies/production.py:143-146`).

The metric layer has the same split: `bo/metrics.py::resolve_metric_policy` raises
`unsupported_objective_version` for anything but 4 (`:65,254-268`), while
`freeze_metric_policy` accepts 4 or 7 and gives v7 a distinct metric hash (`:527-590`). The Pareto
production path uses `freeze_metric_policy` (`studies/builders.py:963-982`), so v7 Pareto studies
can work even though the generic v4 policy seam cannot.

Consequence: a claim like "the BO stack supports v7" and a claim like "the strict cohort gate
refuses v7" can both be true. The audit must name which gate it means. This is not a request to
loosen either gate.

## 7. TuRBO, Pareto, CMA and warm start: the implementation details that matter

### 7.1 TuRBO

`turbo_pool_v1` reuses the scalar GP and qLogNEI, scores only candidates inside a local box, and
builds the box from fitted ARD lengthscales (`bo/turbo.py:1-26,334-421`). State is durable and
idempotent by solve ID; success counter doubles `L` after 3 successes, failure counter halves it
after `max(4, d)` non-improvements, and `L < 0.5**7` is terminal
(`:40-46,152-175`; `bo/extensions.py:96-121`). Infrastructure/metric/unknown outcomes leave state
unchanged (`turbo.py:152-166`); a geometry refusal counts as a non-improvement (`:358-363`).
There is **no automatic restart** and **no every-fourth maximin exploration cadence**
(`turbo.py:20-26,308-311`). This is a declared HornLab variant, not the published TuRBO byte for
byte. It needs a fitted GP with finite lengthscales and a non-collapsed state; otherwise it is a
tagged refusal, not a proposal.

### 7.2 Pareto

`pareto_pool_v1` fits independent coverage/ripple GPs and uses qLogNEHVI over a frozen reference
(`bo/pareto.py:14-16,128-156,278-308`); the reference is frozen once (`:19-27,220-258`) and later
rows beyond it add no hypervolume (`:220-228`). The frontier is a menu of physical trade-offs, not
the acoustic optimum (`:350-355`). The constrained variant (`:90-125`) is **not wired**; it needs
measured signed margins for every row. The production gate checks only that a `pareto_metrics`
artifact/hash/reference is bound (`studies/production.py:53-83,192-193`).

### 7.3 CMA-ES, restarts and refusals

CMA-ES uses pycma on `[0,1]^k`, clips inside `DesignSpace.denormalize`, and counts **non-cached**
evaluations against the budget (`search/cma.py:1-10,184-243`). Cache hits are free; refusals are
not free in the default `budget_counts: new` mode, because they are non-cached attempts (`:201-229`).
The opt-in `budget_counts: valid` counts only valid rows and uses an attempts cap
(`:184-198,218-229`). IPOP/BIPOP restarts mirror pycma's schedule and share the global budget
(`:16-22,422-480`); `resample_strict`/`retry_same_then_stop` resample a refusal or retry the same
candidate under explicit caps (`:54-77,746-938`). These are opt-in; the historical CMA-vs-BO runs
did not use them (`docs/status/2026-11-15-bo-vs-cma/README.md:30-37`). Solver health is separate:
3 consecutive `solve_failed` rows stop the run resumably rather than becoming `J=1000`
(`cma.py:316-326,597-606,791-799`); do not turn infrastructure failures into objective evidence.

### 7.4 CMA-ME / QD

CMA-ME runs a 2-D grid archive over mean in-band H/V beamwidth with one `EvolutionStrategyEmitter`
(`search/cma_me.py:1-45,71-99,127-147,319-405`). Archive admission excludes non-complete rows by an
explicit mask while the emitter still sees the full batch and ranks failures last
(`:220-316,903-922`); this is not feasible-only learning and not trajectory-neutral
(`:29-34,627-638`). QD's value is an archive, not a lower scalar J; a stalled J can still add cells.
The pyribs tutorial uses 1000 iterations x 36 x 3 = 108,000 evaluations (external docs), two to
three orders above a 60-100-solve budget. A sparse archive is a different deliverable.

### 7.5 NSGA-II and warm start

NSGA-II exists as a plain numpy module and a `search_pareto` adapter, but `search.algorithm` only
dispatches `cma`/`cma_me` (`search/cma.py:496-506`); it has no CLI/queue route. Its own docstring
estimates ~100 x 100 = 10,000 evaluations and says it needs a batched surrogate (`search/nsga.py:1-8`);
at 60-100 BEM solves it is not an executable arm.

Warm start replaces the CMA mean with the best valid prior design and optionally sets `sigma0` from
the top-k spread (`search/warmstart.py:57-127`). It refuses a different objective version/brief,
family, or searched knob names unless `allow_cross_brief` is set (`:79-91`). It does **not** filter
the prior by BO's strict cohort fields and does **not** use a GP. That is why "same prior data" is
not established by pointing both at a run directory: BO consumes the strict selected set, CMA only
the best `ok` row and a top-k spread.

## 8. Historical BO-vs-CMA: quantified unequal information

All numbers below are **historical records** from `docs/status/2026-11-15-bo-vs-cma/README.md` and
`data.json`; none was re-run in this pass.

| Item | BO arms | CMA arms |
|---|---:|---:|
| Prior knowledge | 185 solved designs, best J 3.2328 (`README:20`) | same best design as start; `sigma0=0.15` (`README:20-22`) |
| Seeds / new screen budget | 3; 60 | 3; 60 |
| Valid / refused screens | 60/0, 60/0, 60/3 (`data.json` arms) | 31/29, 44/16, 46/14 (`data.json` arms) |
| Candidate feasibility | 4096-design pool pre-checked for size (`README:22`) | direct sampling; no pre-check by default |
| Verify / best verify J | 6; 3.107 / 3.251 / 3.189 | 6; 3.827 / 3.827 / 3.392 |
| Improved on start? / median verify | 2 of 3; 3.189 | 0 of 3 (`README:14-15`); 3.827 |

The effective information ratio is not 60:60. BO got 60 usable acoustic rows every arm; CMA got
31-46. BO also received 185 prior rows; CMA received one starting vector. CMA's 14-29 "too large"
refusals (`README:16`) were avoided by BO's pool pre-check. The comparison mixes prior information,
refusal handling, and local-vs-global search; the report says so (`README:86-92`). `[interp]` The
0.638 median gap is not a causal "BO vs CMA" estimate under equal information.

The TuRBO-vs-scalar landscape comparison is smaller: one seed per policy, 136 records, and TuRBO
followed an interrupted run; best screen/verify 2.4976/2.7662 vs 2.9486/3.1493
(`docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md:13-17`). It is a lead, not a replication.

The matched-home protocol tries to fix prior/refusal symmetry: one frozen cohort per task, six arms,
two seeds, CMA warm-started from the same cohort's best design/top-ten spread, BO capped at 80 screen
calls, and explicit cache/refusal/observed-vs-inferred cost reporting
(`docs/queue/MATCHED_HOME_PROTOCOL_2026-11-16.md:5-20`;
`tools/night_queue/run_matched_home.py:35-39,112-123`). It still does not guarantee equal physical
calls.

**Budget-semantics contradiction.** `HOME_OPTIMIZER_COMPARISON:36-39` says CMA caps "candidate
evaluations at 80, including refusals/cache outcomes". The matched adapter actually sets
`budget_counts: new` and `max_attempts: None` (`run_matched_home.py:112`), so cache hits are free
and non-cached refusals consume the 80. The same file labels the budgets
`cma_new_candidates: 80`, `bo_screen_call_cap: 80`, `verify_cap: 2`
(`run_matched_home.py:123`). The documentation's "including cache outcomes" is **contradicted** by
the code; "including refusals" is correct for the default mode. Report the actual counters, not the
headline.

## 9. What this means for switching (short form)

A switch is not "choose a better optimizer"; it changes the **data contract, model state and budget
accounting**:

- Scalar -> TuRBO needs a fitted GP with finite ARD lengthscales plus a persisted `TurboState`
  (`bo/turbo.py:130-143,272-327`). A fresh run can start it; a mid-run switch cannot use the current
  package runner.
- Scalar -> Pareto needs complete, ID-bound coverage/ripple observations under one frozen metric hash
  (`bo/policy.py:225-284`; `bo/pareto.py:159-217`). Scalar J rows alone are not enough.
- Scalar -> CMA needs the same family/knob names/objective version and a warm-start source
  (`search/warmstart.py:79-91`). A BO cohort row is not automatically a legal CMA row.
- QD needs descriptors and a much larger budget; it is not a drop-in replacement for a stalled J.
- Verify is a separate budget; a screen-only arm has no verified finalist
  (`BO_MULTITYPOLOGY_PLAN:71-92`).

The gate matrix is in `SWITCH_ADMISSION_MATRIX.md`; supervisor options in `SUPERVISOR_OPTIONS.md`.

## 10. Counterevidence, uncertainty and what was not done

- **The historical BO win is real as a workflow result.** With this prior and refusal handling, BO
  produced better verified horns; I do not claim CMA is generally worse. The report's caveat says
  the test is warm-started from an already-optimized CMA basin (`README:86-92`). A cold-start
  equal-information test has not been run.
- **The GP is not obviously mis-calibrated.** Replay refit found rank correlation 0.68-0.83 per arm
  and median absolute error 0.2-0.4 J near the best designs, but 95% intervals were very wide
  (median width ~4.6 J; 157/180 inside) (`README:56-60`). Use the ranking, not the interval, as a
  physical tolerance.
- **No fresh measurement was made.** Section 8 numbers are historical records; no solve, pytest,
  mesher, GPU job or search was run, and no threshold/config/queue YAML was changed.
- **The package pin mismatch is read-only hash evidence at the observed tree.** Some of the 18
  mismatches are other-lane edits; core `bo/policy.py` and `studies/evaluator.py` are not in
  `git status`, so those are committed changes since the package was built. Either way, stale.
- **Unverified:** whether 100 rows is enough for a 14-D GP to rank well; whether mixed fidelity
  preserves rank; whether the cheap pool pass predicts acoustic success (`ADAPTIVE_UNKNOWNS.md`).
