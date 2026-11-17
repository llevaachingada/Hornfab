# Switch admission matrix: what is executable from a given run state

- Repo: `C:\Users\hunte\Hrns\hornlab-search`; HEAD at final write
  `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` (`2026-11-16T20:38:46-05:00`); files were read at
  `13b47632`, byte-identical at the cited SHAs.
- Read-only: states were extracted from `runs/` and `docs/queue/` without re-running a solve,
  rebuilding a cohort, or querying a live process. Numbers are historical records or file counts,
  not fresh measurements.
- "Executable" means **using strictly eligible data and the current code path**, not "someone could
  write a script to do it". A raw `search.ndjson` row is not automatically a BO training row.
- No future-knowledge leakage: a decision at state `t` may use only rows/artifacts produced before
  `t`; it may not use later verify rows, later refits, post-hoc rescoring, or the outcome of a
  comparison arm it is trying to predict. A frozen cohort is frozen once
  (`bo/pareto.py:220-228`; `docs/queue/MATCHED_HOME_PROTOCOL_2026-11-16.md:5-9`).

Status legend: **verified** (file/code read here), **historical record** (report/run number),
**documented only** (plan without executable code), **plausible inference**, **unverified**.

## 1. States used

| ID | State (read-only evidence) | What is actually present |
|---|---|---|
| S1 | `runs/study-f269f257b24e00f2` | Scalar BO study run: 60 screen rows, 60 ok, 0 refused; 6 verify rows, 6 ok. Task p80x60 ext-throat v7. Historical BO arm (`docs/status/2026-11-15-bo-vs-cma/data.json:2-129`) |
| S2 | `runs/study-4e1a6a9cd4bb5201` | TuRBO study run: 61 screen rows (60 ok, 1 failure); 6 verify rows, 6 ok. One seed; historical record says it followed an interrupted run (`docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md:13-17`) |
| S3 | `runs/20261115T052416Z-screen-cdbc27` | CMA arm: 60 attempts, 31 valid, 29 refusals, budget 60 exhausted; task `p80x60__ext_throat_cmacmp_v7`, v7 |
| S4 | `runs/bo_multityp_2026-11-16/bo_cov_s71001` | Prep-only scalar study: 231 training rows, d=9, n_min=20, native build ok; package budget 25 screen + 6 verify = 31 calls, 150 attempts. No screen/verify run exists yet. `package.json` pins 155 files; 18 differ from the current tree; deadline `2026-11-16T07:13:55Z` |
| S5 | `runs/bo_multityp_2026-11-16/lecleach_iwata_ar/cohort` | Raw `offline_scores.json` has 80 `exact_complete` rows, v7; plan records **n=1 usable row** after strict gates (`docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md:39-44`) |
| S6 | `runs/20261116T193501Z-screen-f008ad` | Generic CMA search run: 107 rows, 107 ok, 11 cached; FREEFORM `hl__biradial_es_style_smooth_v7`; budget 96; no strict cohort artifact |
| S7 | `runs/20261115T005614Z-screen-6d55fa` | CMA-ME QD run: 201 rows, 142 ok, 59 failures; 200 non-cached; archive 10/324 cells (3.1% coverage), descriptors mean H/V beamwidth, v4; budget 200 |

## 2. Admission matrix

Legend: **Y** = executable from this state now; **N** = not executable; **C** = conditional on a
named missing artifact or new budget. "Cost" is the dominant cost of the next decision, not a
guarantee.

| Next action | S1 scalar complete | S2 TuRBO complete | S3 CMA refused 29/60 | S4 prep-only cov | S5 Le Cleac'h low-n | S6 generic CMA run | S7 QD run |
|---|---|---|---|---|---|---|---|
| CMA continue / restart | C: needs the CMA config/run identity; the BO study dir is not a CMA run | C: same; one seed only | C: resume needs a new budget; refusals remain unless resample/filter | N: no CMA run in this package | C: data-building run only; not a BO arm | Y: same run, extend budget | Y: same run/archive; output is QD, not scalar |
| Scalar BO | Y: 185 prior + 60 screen rows; n_min=16; 6 verify excluded from training | C: 60 rows are data-eligible, but it is a different policy/state; package does not switch | C: 31 valid rows clear n_min=16, but the 100-row spend floor refuses a new study | Y as **proposal**; N as **execution**: package pins/deadline stale | N: 1 < n_min=16 and < 100 floor | C: raw 107 rows are not a strict cohort; build cohort first | C: 142 valid rows, but no strict v4 cohort artifact; build gate first |
| TuRBO | Y: scalar data + pool + GP; needs a legal pool/trust state | C: continue only if `TurboState` is recovered from the proposal artifact; otherwise re-init | C: 31 rows fit n_min, but no pool/trust state | Y as proposal; N as execution (package stale) | N: below n_min/floor | C: needs cohort + pool | C: needs cohort + pool |
| Pareto | C: needs complete coverage/ripple metric observations and one metric hash; not in the scalar run | C: same | N: no metric observation artifact | Y as proposal if `pareto_metrics` builds; production gate needs the artifact | N: below floor | C: needs metrics | C: needs metrics; v4 hash |
| QD / CMA-ME | N: no archive/descriptors; different algorithm | N | N | N | N | N | Y: continue the archive; no production study policy |
| Geometry-only exploration | C: needs the legal pool; not the same as BO | C: needs pool | C: needs pool; 29 refusals show geometry is the binding constraint | Y: pool artifact exists; cheap checks only | C: raw designs exist but no pool | C: build pool | C: build pool |
| Verify | Y: 6 verify rows exist; new verification needs a new budget and the frozen selection rule | Y: 6 verify rows exist | Y: 31 valid rows; select finalists; 2-6 solves | N: no screen rows yet | C: raw rows, but no verified finalist | Y: 107 rows; select finalists | C: 142 ok rows; select finalists |
| Stop / pivot | Y: arm complete; report | Y: arm complete | Y: budget exhausted; report refusals | Y: do not launch; rebuild package | Y: pivot to data building | C: continue search or build cohort | Y: archive deliverable; stop scalar-J framing |

## 3. Per-state notes

### S1 - scalar BO completed (60/60)

- Strictly eligible training data: the initial 185-row cohort plus 60 measured screen rows. The
  evaluator adds only screen results with `outcome in (success, cached)`, `eligible is True`, a
  finite `observed_j`, and a unique `physical_id`; verify/audit rows return `False` and are **not**
  added (`studies/evaluator.py:528-551`). This is why verify cannot leak into the next refit.
- Gates: `n_min=max(16,2(d+1))`; for the historical v7 task d=6, `n_min=16`; the training set is
  well above it. The model must still fit and produce finite hyperparameters
  (`bo/model.py:313-386`); a flat/failed fit is a tagged refusal.
- Missing for a new proposal: the legal candidate pool. The scalar `capability_status` checks only
  the training set (`bo/policy.py:459-461`), but `propose_one` refuses if the pool is absent/not
  `ok` (`bo/propose.py:302-329`). A study package normally binds the pool artifact; a bare run dir
  does not.
- Bias: the 60 rows are from the same BO arm; reusing them as a new prior is fine for a new arm
  only if the new arm is declared as dependent, not as an independent seed. The 185-row prior is
  shared with the historical CMA arms, so a "new" comparison using them is not independent.
- Cost: one GP refit + pool scoring is CPU (~seconds to minutes); the next screen solve is one BEM
  call. No GPU work in the proposal itself.

### S2 - TuRBO completed (60/61)

- Strictly eligible: 60 successful screens; the one failure is excluded from training
  (`bo/data.py:107-112`). n=60 is above n_min for d=6.
- The trust region is durable state, not a statistic that can be recomputed from rows alone. If the
  proposal artifact carries `trust_region.state_after`, `TurboState.from_dict` can restore it
  (`bo/turbo.py:98-115`; `studies/production.py:186-191`). If not, a new run can only re-initialize
  at the best measured design (`bo/turbo.py:130-143`), which is a different experiment.
- Missing: the current package's proposal artifact/trust state and a legal pool. A bare
  `screen/` dir has rows but not the package policy/trust record.
- Bias: one seed, and the historical record says the arm followed an interrupted run. Continuing it
  is not a replicate; reporting it as one would be wrong.

### S3 - CMA with 29/60 refusals

- Strictly eligible: 31 valid rows; 29 refusals are **not** training rows. 31 >= n_min=16, but the
  100-row spend floor (`tools/bo_compare/prepare_study.py:76-77,163-169`) refuses a new BO study.
  This is the clearest "math-executable but policy-inadmissible" case.
- CMA continue is executable: the run is a normal search run with a budget stop; a new invocation
  can extend the budget if the config/identity is unchanged (`search/cma.py:482-530`). The 29
  refusals will recur unless the opt-in resample/filter path is used (`:54-77,746-938`), and the
  historical arm did not use it.
- Geometry is the binding constraint, not the optimizer: "too large" refusals are 29/60
  (historical record, `docs/status/2026-11-15-bo-vs-cma/data.json`). A policy switch to BO does not
  fix an oversized search box; a geometry/cost-aware experiment does.
- Verify: yes, select finalists from 31 valid rows. A verify result is a new BEM call; do not
  substitute a predicted design (`docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md:71-92`).

### S4 - prep-only 231-row cov study

- This is the strongest BO state: native training is `ok`, n=231, d=9, n_min=20, policy status
  `ok`, and the package has a scalar proposal, pool, model, training manifest and a 25+6 budget.
- It is **not executable now** for two independent reasons:
  1. 18 of 155 `code_pins` differ from the current tree, including `bo/policy.py` and
     `studies/evaluator.py`; `execution_capability` hashes the current files and refuses
     (`studies/production.py:90-96`).
  2. The package deadline `2026-11-16T07:13:55Z` is in the past relative to the observed write
     time; `production.py:116-119` refuses an expired deadline.
- Rebuilding the package is a CPU-only prep step (no solve) and is the correct action; editing the
  package to bypass pins is not.
- Bias: if rebuilt, the study is still one seed/one arm; do not compare its 25 screens to a CMA arm
  with a different valid-row budget without the matched protocol.

### S5 - Le Cleac'h 80 raw / 1 strict

- Raw `exact_complete` rows are not a cohort. The strict builder must recover design params,
  reproduce the design hash, encode the vector, and pass the objective/metric policy; only one row
  survives per the plan (`docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md:39-44`).
- `n_min` for d=4 is 16; one row is far below. `prepare_study` also enforces >=100 selected rows
  (`tools/bo_compare/prepare_study.py:76-77,163-169`). Scalar/TuRBO/Pareto are **N**.
- The honest next action is a CMA data-building cohort (the plan estimates ~25 screens to reach the
  100-row floor for Le Cleac'h/rounded-rect; `BO_MULTITYPOLOGY_PLAN:208-209`). That is a data
  investment, not a policy switch.
- Bias: using the 80 raw rows as if they were 80 independent BO observations would inflate evidence
  and violate the cohort gate. Do not.

### S6 - generic CMA run, 107 rows

- The run has 107 `ok` rows and 11 cache hits; it is a normal CMA run, not a study cohort. It has
  no S0 catalog/R0 replay join, no per-row policy attestation, no strict design round-trip. Feeding
  `search.ndjson` directly to `build_training_set` would bypass the cohort identity gate and is not
  admissible.
- CMA continue is Y (same config/run). Verify is Y (select finalists from 107 rows). Scalar BO is
  C until a strict cohort is built. This is the ordinary "search first, cohort later" state.
- Bias: the 11 cache hits are not independent new evidence; they must not be counted as solves.

### S7 - QD run, 200 solves, 3.1% archive

- The archive has 10 occupied of 324 cells after 200 non-cached solves; 59 rows failed and are
  excluded from archive admission (`search/cma_me.py:220-284`; `archive.json` read-only). The
  scalar best may be flat while the archive still adds cells; a "stalled J" stop rule would
  destroy that deliverable.
- QD continue is Y (same archive/run), but it is not a production study policy
  (`PRODUCTION_POLICIES` is scalar/turbo/pareto; `studies/production.py:49-50`). A switch to QD
  from a BO/CMA study is not a package edit; it is a new search run.
- Bias: the archive's 3.1% coverage is not "the QD method failed"; it is a 2-D discretization of a
  200-solve budget. Reporting it next to a scalar J requires saying what question is being asked.

## 4. Exact gates (checklist)

A next policy is admissible only if all of these are true:

1. **Task identity**: same registered task/config/brief; `task`, `resolved_brief`, `target`,
   `score_policy`, `metric_policy`, `frequency_masks`, `backend`, `fidelity`, `mesh_policy`,
   `frequency_grid`, `dependencies`, `excitation`, `encoding` agree (`bo/cohort.py:20-22,108-144`).
2. **Row eligibility**: `status=exact_complete`, `ok=true`, finite `J`, `design_hash` matches S0/R0,
   response-detrended ripple evidenced, target/weights present (`cohort.py:94-109`).
3. **Objective version**: the chosen gate's version. `cohort.py` is v4-only (`:96-97`); the native
   builder accepts the brief's version (`bo/data.py:657-665`); production supports v4/v7
   (`studies/production.py:143-146`).
4. **Size**: `n >= max(16, 2(d+1))` unique eligible geometries (`bo/data.py:71-75`); a new study
   additionally needs >=100 selected rows (`tools/bo_compare/prepare_study.py:76-77,163-169`).
5. **Encoded vector**: finite, exactly `d` active dims, inside `[0,1]`; historical clipping refused
   (`bo/encoding.py:255-289`; `bo/cohort.py:145-151`).
6. **Active dims**: 1..20; no discrete/categorical active dimension (`bo/encoding.py:21-22,116-129`).
7. **Candidate pool**: `status=ok`, at least one finite unit-box vector (`bo/policy.py:304-326`);
   every selected candidate re-materialized and validated (`bo/propose.py:472-501`).
8. **Model**: finite training response (`s2>1e-12`), successful fit with finite hyperparameters
   (`bo/model.py:290-295,313-386`); TuRBO additionally needs finite ARD lengthscales and active
   trust state (`bo/turbo.py:312-333`).
9. **Pareto**: complete ID-bound metric observations under one metric spec hash, n>=n_min
   (`bo/policy.py:225-301`; `bo/pareto.py:159-217`).
10. **Execution**: package pins, dependency pins, lane, deadline and policy all match
    (`studies/production.py:86-196`); a prepared package is not executable after a code change.
11. **Budget**: screen/verify/attempt caps and no future rows (`studies/runner.py:87-114,166-233`).
12. **No leakage**: verify/audit rows are not added to training (`studies/evaluator.py:528-551`);
    the Pareto reference is frozen once (`bo/pareto.py:220-228`); a switch decision cannot use the
    outcome of the arm it is choosing.

## 5. What is missing in each state (summary)

| State | Missing before a *new* BO arm | Missing before a *new* CMA arm | Missing before a *new* QD arm |
|---|---|---|---|
| S1 | pool artifact; fresh package | CMA config/run identity | descriptors/archive |
| S2 | pool + trust state | CMA config/run identity | descriptors/archive |
| S3 | >=100 valid rows; pool | new budget | descriptors/archive |
| S4 | fresh code pins + deadline | CMA warm-start run | descriptors/archive |
| S5 | >=16 (and >=100) strict rows | data-building run | enough solves |
| S6 | strict cohort | nothing (continue) | descriptors/archive |
| S7 | strict v4 cohort | nothing (continue) | nothing (continue) |

**Bias note.** None of these states supports a clean "which optimizer is better" answer. S1/S2 are
completed arms with one seed; S3 is a refusal-heavy CMA arm; S4 is an unlaunched prep; S5 is a
data-poor cohort; S6/S7 are search runs without a strict cohort. Any cross-state comparison must
report the valid-row counts, refusal counts, cache hits, prior information and verify shortfall, or
it is comparing unequal information.
