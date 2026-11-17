# Supervisor options: what could decide, and the evidence against each

- Repo: `C:\Users\hunte\Hrns\hornlab-search`; HEAD at final write
  `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` (`2026-11-16T20:38:46-05:00`); files were read at
  `13b47632`, byte-identical at the cited SHAs.
- Read-only. No policy code, threshold, queue YAML, process or solve was changed. Options are
  compared as architecture choices; none is recommended as an implemented policy.
- The current supervisor is **not** a policy controller: it is a night-runner watchdog plus a
  read-only advisory report.
  - Watchdog: stops a running `search` job on refusal rate, no-gain, bound-pinning, or stall
    (`tools/run_campaign_night.py:86-108,164-211`), kills the job tree (`:1076-1081`) and records
    `status: watchdog` / exit 75 (`:84,1116`). It explicitly **does not watch BoTorch study jobs**
    (`:97-98`).
  - Advisor: `tools/analysis/optimizer_switch.py` reads runs and emits heuristic JSON/Markdown;
    it never switches, never compares runs, and labels raw rows as not BO training observations
    (`:1-4,15-18,21-24,56-64,104-105`).
  - The study runner has no switch: a policy change invalidates the package
    (`runs/bo_multityp_2026-11-16/bo_cov_s71001/package.json`,
    `adaptive_policy.manual_change_invalidates` includes `"policy"`); the runner only asks the
    same evaluator for the next candidate (`studies/runner.py:87-114,166-233`); the evaluator only
    refits the same policy (`studies/evaluator.py:636-680`).
- Status legend: **verified**, **historical record**, **documented only**, **plausible inference**,
  **unverified**, **contradicted**.

## 1. Comparison

| Option | What it would do | Evidence for | Evidence against | Cost / failure mode |
|---|---|---|---|---|
| **O1** Keep watchdog + better reports | Keep stopping bad *search* jobs; improve the advisory report | Already implemented; cheap; no new policy risk; watchdog catches refusal/stall/bound-pin (`run_campaign_night.py:164-211`) | Excludes BO studies (`:97-98`); cannot see scientific value (QD archive, surrogate data); stall thresholds are heuristic; kills a job and loses the in-flight generation; `optimizer_switch` explicitly does not compare runs (`:104-105`) | Low CPU cost; risk of stopping a productive non-scalar run; no improvement in decision quality |
| **O2** Shadow-mode read-only advisor | Compute a recommendation from the same rows, log it, never act | Safe; builds an audit trail; can be evaluated against later outcomes | Same biased input as the run; no counterfactual; no enforcement; can be ignored; recommendations are threshold rules, not causal estimates (`optimizer_switch.py:56-64`); needs trustworthy scoring first | Low cost; risk of false confidence and report sprawl |
| **O3** Bounded between-job policy controller | At a job boundary, choose the next policy from a fixed set under hard caps | A between-job boundary is the only safe place to change policy; packages already have deadlines/budgets/pins (`production.py:86-196`) | No state migration: TuRBO needs a `TurboState`, Pareto needs complete metric observations, CMA needs a warm-start run (`bo/turbo.py:130-143`; `bo/policy.py:225-301`; `search/warmstart.py:79-91`). A policy change invalidates the package. Code pins/deadline are checked at execution (`production.py:90-119`). Budget semantics differ (screen calls vs new candidates vs valid rows) (`run_matched_home.py:112-123`; `cma.py:184-243`). The controller would choose from the same biased rows it is trying to improve | Medium engineering; high risk of invalid comparisons and stale packages; no clean counterfactual |
| **O4** Portfolio / racing / bandit across frozen arms | Allocate solves among CMA/scalar/TuRBO/Pareto arms; stop losers early | Treats the choice as an allocation problem; can use observed cost/refusal data; matches the goal of spending the next solve well | Arms are expensive and stateful; only 2-3 seeds; each arm has a different valid-row/refusal budget; racing assumes many cheap, stationary arms; early stopping biases the comparison; shared GPU/cache breaks independence; winner's curse with small n. The historical comparison already has 60 vs 31-46 valid rows (`docs/status/2026-11-15-bo-vs-cma/data.json`) | High GPU cost; statistically weak; can silently corrupt a matched comparison |
| **O5** Geometry/cost-aware experiment design instead of method switching | Choose the next design by expected information/cost/feasibility, not by optimizer label | Addresses the binding constraint seen in S3 (29/60 too-large refusals); a cost model and geometry checks exist in prototype (`bo/extensions.py:40-71`; `bo/data.py:1068-1180`) | Cost model needs >=30 uncached timings and is not wired (`extensions.py:40-71`; `docs/queue/BO_EXT_PLAN_2026-11-16.md:72-74`); geometry refusals are often binary; it does not fix the score/source truth; it can still optimize the wrong objective | Medium CPU + solve cost; needs a trusted cost/feasibility model; risk of over-engineering the acquisition |
| **O6** Defer automation until scoring/source truth is trustworthy | No automatic switching; fix v7/score/cohort truth first | The owner's v7 review pause is active (`docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md:9-11,200-204`); a switch on an unstable J is meaningless; code already has two v4/v7 gates that disagree (`bo/cohort.py:96-97` vs `bo/data.py:657-665`) | Deferral has opportunity cost; a stalled run may waste GPU; "do nothing" is still a policy; it does not answer whether a switch would help | Low engineering; may delay useful data campaigns; does not resolve the counterfactual |

## 2. Evidence against each option, in more detail

### O1 - Keep the watchdog and improve reports

**For.** The watchdog is simple, local, and already operational. It stops a search on a high
refusal rate, a seed that never improves, a best design pinned at a bound, or a flat best-so-far
(`run_campaign_night.py:164-211`). It does not change thresholds or restart policies. The advisory
report is explicitly read-only (`optimizer_switch.py:1-4`).

**Against.**
- It **does not watch BoTorch study jobs** (`run_campaign_night.py:97-98`), exactly the jobs a switch
  supervisor would reason about. A BO arm can stall or burn attempts unseen.
- The stall rule is **scalar-J only** (`:204-210`). QD can add archive cells, BO can add surrogate
  rows, and geometry can add feasibility knowledge while J is flat; stopping those is a loss.
- The refusal rule treats "not ok / nonfinite / objective >= 900" as failure (`:166-168`). That is
  right for a broken solver and wrong for a hard-but-real geometry; it cannot separate a bad box from
  a bad optimizer. It also kills the job tree (`:1076-1081`), so the partial generation is not told.
- `optimizer_switch.py` says it does not compare runs and raw rows are not independent seeds
  (`:104-105`). Better formatting does not fix that.

**Verdict.** This is the right **baseline**, not a supervisor. It should stay, but it should not be
described as a policy decision system.

### O2 - Shadow-mode read-only advisor

**For.** A shadow advisor can log "what I would have done" without spending a solve or changing a
package. It is the natural next step after O1 because it is reversible and auditable.

**Against.**
- Its input is the same `search.ndjson`/run summary the run already produced; it has no independent
  measurement of whether a switch would have helped.
- Its recommendations are fixed thresholds, not a pipeline model: refusal fraction >30% over 30 rows,
  stall >40 valid rows, `bo_min_usable_rows=100` (`optimizer_switch.py:15-18,27-71`).
- It cannot establish causality: the unchosen arm's counterfactual is missing. Logging a
  recommendation and later observing one arm does not identify the switch effect.
- It adds a report surface but not a gate; a human can ignore it, and an automated runner cannot use
  it without becoming O3. It also still needs trustworthy scores/sources.

**Verdict.** Useful as an **evaluation harness**, not as a supervisor. It should be paired with a
predeclared decision rule and a held-out period; otherwise it is narrative.

### O3 - Bounded between-job policy controller

**For.** A between-job boundary avoids mid-generation state corruption. The package already has
deadlines, budgets, code pins, dependency pins, and a policy field
(`studies/production.py:86-196`). A controller could be constrained to a small, predeclared set.

**Against.**
- **No state migration.** TuRBO needs a fitted GP with finite ARD lengthscales plus a durable
  `TurboState` (`bo/turbo.py:130-143,272-333`); Pareto needs complete ID-bound coverage/ripple
  observations under one metric hash (`bo/policy.py:225-301`; `bo/pareto.py:159-217`); CMA needs a
  config/run identity and a warm-start source (`search/warmstart.py:79-91`). A string change is not
  a switch; the missing artifacts must be built.
- **Package invalidation and pins.** The observed package declares
  `manual_change_invalidates: [spec, source, cohort, policy]`; the runner validates one package
  (`runner.py:87-114`). Execution hashes 155 code files (`production.py:90-96`), checks the
  deadline (`:116-119`) and dependency pins (`:170-181`); a controller code change invalidates
  existing packages unless it is in the frozen execution set.
- **No common cost unit.** BO counts screen calls; CMA counts new non-cached candidates (or valid
  rows in `valid` mode); QD counts evaluations; the study has separate screen/verify/attempt caps
  (`run_matched_home.py:112-123`; `cma.py:184-243`; `studies/runner.py:87-114`).
- **Bias and no counterfactual.** Switching after seeing early results conditions the later estimate
  on the switch; the matched protocol keeps fixed budgets for that reason
  (`HOME_OPTIMIZER_COMPARISON:59-64`). A one-seed between-job switch is a new experiment, not a
  controlled comparison.

**Verdict.** This is the **highest-risk** option. It is only defensible after O6 (truth) and with a
predeclared, replicated, equal-cost design. It is not a safe next step.

### O4 - Portfolio / racing / bandit among frozen arms

**For.** If the arms are frozen and each pull is a solve, a bandit is the natural formalization of
"spend the next solve where it is most valuable". It also gives an explicit exploration cost.

**Against.**
- **Non-stationary, non-independent arms.** CMA/BO adapt, TuRBO's region grows/shrinks, Pareto refits
  GPs, and cache/refusals change effective cost; the i.i.d. bandit assumption fails.
- **Unequal information and early-stop bias.** BO's 60 screens were 60 valid rows; CMA's were 31-46
  valid with 14-29 refusals (`docs/status/2026-11-15-bo-vs-cma/data.json`). Counting "pulls" over-
  rewards the low-refusal arm, and stopping a loser early is the bias COCO censoring exposes
  (`HOME_OPTIMIZER_COMPARISON:83-85`).
- **Few seeds and winner's curse.** Two seeds and one GPU lane cannot support a high-confidence
  bandit; selecting the best observed arm without shrinkage overstates it.

**Verdict.** A portfolio is a **research design**, not a supervisor. It needs many more arms/seeds
or a surrogate/cheap-fidelity layer before it is statistically meaningful.

### O5 - Geometry/cost-aware experiment design instead of method switching

**For.** The S3 state shows the binding constraint is geometry: 29/60 attempts were "too large"
refusals. The code already has cheap geometry checks and a candidate pool
(`bo/data.py:1068-1180`), a prototype cost model (`bo/extensions.py:40-71`), and a strict
single-fidelity cohort builder. A design that chooses a feasible, informative next point is more
valuable than a label change.

**Against.**
- The cost model is **not wired**: it needs >=30 compatible uncached timings and is only a
  heuristic (`extensions.py:40-71`; `BO_EXT_PLAN:72-74`). Without it, "cost-aware" is a guess.
- Feasibility is often binary at the pre-solve check; a cheap envelope/throat margin can be
  computed, but a binary refusal has no gradient. It also does not fix the score/source truth.
- It adds CPU work and a new failure surface (the pool is explicitly "cheap-check-passed;
  mesh/acoustic eligibility unknown", `bo/data.py:33`), and it may be over-engineered relative to
  building the missing cohorts and verifying the score.

**Verdict.** Promising as a **targeted intervention** (especially a feasibility-first candidate
filter), but it is not evidence for switching. It should be evaluated as an experiment, not
assumed.

### O6 - Defer automation until scoring/source truth is trustworthy

**For.** The v7 objective is under owner review (`BO_MULTITYPOLOGY_PLAN:9-11,200-204`). The two
cohort gates disagree on v4/v7 (`bo/cohort.py:96-97` vs `bo/data.py:657-665`). A switch on an
unstable J is not a decision about optimizers; it is a decision about a moving score. The highest
return may be validity/data/objective work, not another policy.

**Against.**
- Deferral is not free: a stalled run holds the GPU, and "no automation" still leaves the watchdog
  and manual queue in place, without starting the data-building cohort.
- It does not answer the counterfactual; without a cheap falsifying test, the answer stays unknown.
- It can become permanent if the "wait for truth" rule has no owner/date, and it may be unnecessary
  if the score audit already shows a stable ranking.

**Verdict.** The **safest default** while the score/source audit is open, provided it is paired with
the low-cost audits in `ADAPTIVE_UNKNOWNS.md` and a date/owner for the decision.

## 3. Simpler baseline (what I would keep)

1. **Keep the watchdog as a safety net, not a scientist.** It may stop on infrastructure failure,
   solver-unhealthy streaks, hard refusal explosion, or an expired deadline. It should **not** stop
   a comparison arm on scalar-J stall, and it should **not** be extended to BO studies until it can
   distinguish "no scientific value" from "no scalar-J improvement".
2. **Keep the advisory report read-only.** Do not wire it to a package policy. Add a
   predeclared decision table and a held-out evaluation period before calling it a supervisor.
3. **No automatic policy switching.** Use separate, predeclared arms with frozen cohorts and fixed
   budgets. If a switch is studied, it is a new experiment with its own package and its own
   counterfactual.
4. **Gate execution on truth, not on optimism.** Package pins, dependency pins, deadline, cohort
   identity, objective version and metric hash are hard gates (`production.py:86-196`). A stale
   package is rebuilt, not patched.
5. **Report cost and censoring.** Report valid rows, refusals, cache hits, attempts, observed vs
   inferred BEM calls, and verify shortfall; treat an unfinished arm as censored, not as a zero
   (`docs/queue/MATCHED_HOME_PROTOCOL_2026-11-16.md:5-20`; `HOME_OPTIMIZER_COMPARISON:36-41`).
6. **Spend the next cheap work on validity/data/objective, not switching.** The highest-return
   candidates from this audit are: resolve the v4/v7 gate split, quantify screen-vs-verify rank
   stability, test whether refusals have a learnable margin, and build the missing 25-screen
   cohorts for the genuinely different typologies. Those are CPU/data work, not policy code.

## 4. What would change the recommendation

- If a zero-GPU score audit shows the v7 ranking is stable under the verify/hi-fi rescore and the
  cohort gates agree, O6's main objection weakens.
- If a predeclared matched experiment with **equal valid-row budgets** and **equal refusal
  handling** shows a gap larger than the seed spread, a bounded between-job controller (O3) becomes
  worth designing.
- If a cost/feasibility model validates on >=30 uncached timings and reduces refusals without
  changing the score, O5 becomes the better intervention than any policy switch.
- If QD archives show owner-relevant diversity at 60-100 solves, the supervisor must stop treating
  a flat scalar J as failure; that is a change to the objective/report, not to the optimizer.

Until one of those is true, the simpler baseline is the defensible architecture.
