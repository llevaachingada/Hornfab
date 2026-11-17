# OPTION 09: Evidence-driven search supervisor and adaptive GPU queue

**Status:** Substantial hypothesis for Fable's *independent architectural comparison*, NOT an implementation order, not authorization to change a live queue, and not a conclusion that automatic switching is beneficial. Reviewed against GitHub `main` at commit `2c0e2928e932a47975fc284401eafa74ebfc5002` (2026-11-16). The local checkout, its dirty state, jobs and dependency pins have **not** been verified remotely.

## What we actually want

Optimize for *validated, useful acoustic designs and reusable information per scarce GPU-hour*, not merely lowest current `J`, number of successful solver calls, or fastest apparent improvement. The owner wants a workflow that recognizes when a CMA-ES arm has stagnated, a family/parameter box is unproductive, a high-rate refusal regime is burning attempts, or a BoTorch variant offers better value, then reallocates compute intelligently. Also retain unusual and diverse good horns and support worthwhile parameter/size exploration.

This spans **three different control layers** that should not be collapsed into one opaque watchdog:

1. **Safety/execution watchdog:** process health, Julia/CUDA resources, corrupt/incomplete records, timeouts, deterministic refusals, locks, paused/resumed runs; can stop a harmful run under defined policy.
2. **Optimizer-internal controller:** CMA covariance/step-size/restart criteria; TuRBO trust-region shrink/expand/collapse; BO acquisitions. Let proven optimizer mechanics do their own work unless there is a clear reason to intervene.
3. **Study or campaign supervisor:** choose whether to *keep* a run, stop/reseed, build a valid BO cohort, invoke scalar/TuRBO/Pareto BO, widen a new versioned **search** domain, change family, request a score/metric audit, run a cheap geometry study, select a higher-fidelity verification, or finish the campaign. This is a scientific decision with opportunity cost, validation and provenance.

**Do not prematurely prescribe one policy.** Fable should compare: (A) the existing watchdog + better reports; (B) a shadow-mode recommendation supervisor; (C) a cautious policy-driven between-job scheduler; (D) portfolio/racing/multi-armed-bandit allocation among frozen study arms; (E) an experiment-design layer that uses canonical geometry, constraint learning and cost estimates, rather than optimizer switching as the primary lever; (F) no adaptive automation until physical scoring and source assumptions are trustworthy. A combination can win.

## Verified code map and existing capability

| Code / evidence | Verified state and consequence |
|---|---|
| [`tools/run_campaign_night.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/tools/run_campaign_night.py), ~84–213 | Existing search watchdog: 30 s polling, after enough attempts high recent refusal fraction; no gain since seed; less than 0.5% best-`J` improvement across a 40-valid-evaluation window; bound-pinned top candidates. These are heuristics, not validated optimal stopping laws. `pin_ignore` suppresses deliberately hard limits. |
| Same runner, ~1002–1123 | Stops a monitored search subprocess, preserves partial result rows, status `watchdog` / exit 75. A resumed job is judged on newly added rows. The search watchdog does not inspect BoTorch studies the same way. |
| Same runner, ~1232–1422 | **Already live-reloads queue YAML between jobs**; supports reorder/add/remove pending IDs, PAUSE/STOP, last-good YAML on invalid edits, and admission filtering. A supervisor should reuse this seam, not introduce another concurrent queue executor. |
| [`tools/analysis/optimizer_switch.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/tools/analysis/optimizer_switch.py) | Existing *advisory*, per-run analysis of refusal fraction, stalled progress and bound walls; has no automatic optimizer/bounds/queue action and is not an equal-information optimizer comparison or BO readiness gate. |
| [`tools/analysis/walls.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/tools/analysis/walls.py) | Already flags wall-adjacent elite designs and produces a candidate widening/narrowing report. Its proposal is **not evidence that changing a bound is safe or useful**. |
| [`hornlab_search/bo/policy.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/hornlab_search/bo/policy.py) | Existing scalar, TuRBO, Pareto, CMA seed and exploration proposal choices; policy execution and capability have strict eligibility requirements. |
| [`hornlab_search/bo/turbo.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/hornlab_search/bo/turbo.py) | Local trust-region shrinks/expands **within normalized `[0,1]` domain**, ends on collapse, does not automatically change physical parameter bounds or restart. |
| [`hornlab_search/search/cma_me.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/hornlab_search/search/cma_me.py) | Quality-diversity can legitimately add valuable archive cells even without improving one incumbent. Stall metrics that look only at best scalar `J` can stop useful discovery. |
| [`hornlab_search/bo/data.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/hornlab_search/bo/data.py), `bo/cohort.py`, `bo/encoding.py` | BO needs strictly compatible measured rows, projection and pool capability. Invalid penalty rows, cached duplicates or incompatible source/mesh/score IDs are **not** sufficient training data. |
| [`hornlab_search/dataset/identity_v2.py`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/hornlab_search/dataset/identity_v2.py) | Existing separate identities for physical solve, analysis, score and study. Reuse *raw physical results* when eligible, not cached old normalized vectors/old `J` labels after changed bounds/objectives. |
| [`docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md`](https://github.com/llevaachingada/Hornfab/blob/2c0e2928e932a47975fc284401eafa74ebfc5002/docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md) | Three-arm historical BO vs CMA has unequal information and refusal counts. One landscape TuRBO > scalar comparison is promising but unreplicated. `MATCHED_HOME_PROTOCOL_2026-11-16.md` describes a more rigorous controlled comparison. |
| `tests/test_night_runner_watchdog.py`, `tests/test_night_runner_live.py` | Existing offline tests for stop, resume, pin ignore, live YAML changes and admission. Extend tests; do not alter thresholds just to make a new policy appear effective. |

**Important code-review hypothesis:** `watchdog_verdict` uses `not ok` / objective `>=900` as a common bad-outcome flag. This is understandable for early stopping but obscures geometry refusal, envelope feasibility, resource OOM, transient infrastructure and metric faults. Investigate the true failure taxonomy and denominator before deriving actions. The `pin_*` defaults in the function may not be exposed in the public YAML schema; verify behavior locally instead of inventing supported keys. A fresh resume's window changes interpretation of no-gain; check tests and real resume logs rather than assuming resumed `n` behaves like initial seed.

## Why an ordinary automatic switch is not always smart

- **No progress** can mean local convergence, insufficient iterations, bad solver fidelity, score/metric gaming, narrow bounds, a true physical limit or an inappropriate source model. Changing optimizer often leaves the root cause untouched.
- **Bound pinning** can be beneficial, a natural physical optimum, a hard geometric/safety boundary or a numerical artifact. Widening every pinned bound can cause instability, meaningless conditional controls and more invalid geometry.
- **CMA vs BO** cannot be ranked just by historical final `J` because BO consumed a CMA-created cohort. Both physical solve cost and warm-data acquisition cost count. Changing to BO requires appropriate eligible rows and geometry adapter.
- **Early stopping biases comparisons.** If poor-looking CMA arms are cut at 30 rows but BO goes to 80, the result is not an equal-budget performance test. Separate controlled fixed-policy experiments from adaptive production search. Do not use an adaptive run to prove the policy that selected it without controlling bias.
- **Different search goals.** A scalar stall may still produce novel and useful shape descriptors, coverage trade-offs or data for future surrogate training. QD and exploration need different progress signals.
- **Score instability.** A new objective version may reorder an apparent incumbent from #1 to #12. A live supervisor should watch raw loading, beamwidth, polar smoothness, failure rates and verify drift, not merely `J`.

## Actions as *hypotheses*, not hard-coded rules

| Observation | Candidate action(s) to investigate | Required checks before acting |
|---|---|---|
| High deterministic geometry refusals | Review geometry law, constraints, no-op controls, candidate pre-screen; reroute to feasible family | Check refusal reasons and whether a stricter cheap preflight actually preserves good designs |
| High transient backend failures or shared-VRAM spill | Pause for infrastructure diagnosis, not optimizer switching | Identify clean-host state, own lane/lock, resource log; do not kill unrelated workers |
| CMA improvements plateau | Continue, change CMA seed/step size, separately cold-restart, try scalar BO or TuRBO, or move family | Compare improvement *per GPU-hour*, archive novelty, cumulative historical gain and matched-cohort readiness |
| Top designs reach a search-box wall | Compare local expansion, new parameterization, feasibility-aware sampling or accept physical limit | Independent bound limits, source/geometry validity; make a new versioned config and re-encode historical parameters |
| TuRBO region collapses | End that local arm; consider separate restart/global BO or other family | Prevent untracked restart/hidden extra budget; trust-region collapse is not proof of global optimum |
| Good scalar result but poor verified field | Verification/calibration/score audit, not more exploitation | Source, mesh/frequency, measurement/score identity; physical response availability |
| New family with few eligible BO rows | Bounded CMA/Sobol exploration or CPU geometry study | Count eligible independent physical rows and their pins; avoid fabricated `J=1000` samples |
| Valid but over-product-envelope candidate | Tag as exploratory for a separate budget or retain existing hard product brief | Owner approval, true W/H/D and solver cost; do not edit historical production brief |
| Strong quality-diversity gain without scalar best gain | Continue QD if this matches the study purpose | Record new viable archive cells, feature novelty and validated acoustic usefulness |

## Fable decision space: policy architecture, not a magic threshold

1. **Minimal:** keep present runner and improve failure segmentation, visual dashboards, and explicit prompts for a human operator. Could outperform a complicated controller if scoring is unstable.
2. **Shadow-mode supervisor (sensible first prototype, not mandatory):** read immutable snapshots and running state, emit `recommendation.json` with observations, alternatives, confidence limits, affected cohort, proposed next job and counterevidence. **Never edit queue or launch work.** Compare the recommendations against actual historical and prospective outcomes.
3. **Bounded policy controller:** apply a previously approved finite decision table only **between jobs**, by atomic, admission-checked edits to pending jobs. Frozen jobs, active studies and source/score/bounds changes require a new versioned experiment and user/integrator approval.
4. **Algorithm portfolio / racing scheduler:** allocate initial small budgets to diverse families/optimizers then use measured improvement-per-cost and uncertainties to redistribute resource, with an explicit exploration floor so seemingly weak families are not permanently excluded. Compare successive-halving, Hyperband/ASHA, multi-armed bandits, Bayesian experimental design or simpler priority scores; they differ in assumptions, e.g. partial CMA histories are not trivially predictive of eventual returns.
5. **Geometry/physics-driven research scheduler:** optimize information gain and design-space coverage, choose extra fidelity/temperature, validate source and metrics, or introduce new shape parameterizations; optimizer switching may not be the biggest opportunity.

Fable should be willing to reject the supervisor concept if the upstream quality of objective/geometry/source data makes automation premature.

## Potential implementation boundary (for Fable to accept/change/reject)

```text
immutable run and study snapshots + exact provenance + active runner state
                    |
        offline diagnostic and cost accounting
                    |
        candidate actions with prerequisites / uncertainties
                    |
       approval and admission / policy versioning
                    |
        between-job queue interface (existing reload seam)
                    |
        append-only decision/reason/audit record
```

For any contemplated controller, require: full **reason** and counter-evidence, idempotent action IDs, no duplicate live runner, one GPU solve at a time, CPU/GPU lane isolation, atomic legal YAML, finished job never silently repeated, revalidation of queue admission, hard budgets and wall-clock caps, no invalid physical observations, deterministic replay, dry-run, and explicit visible owner gate for policy/brief/domain changes. Historic work and running studies must be untouched.

## What cheap investigators should do before Fable

Read `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md`. In short: reconstruct real watchdog stops/restarts and counterfactual *limitations* from logs; audit event types, cost denominators, and BO readiness; compare the effect of thresholds on different study purposes; map safe queue control interfaces; identify how parameter widening changes encoding and solved-data eligibility. Use existing analysis scripts and matched protocols; no GPU, no queue mutation. Provide both recommendations and evidence against the supervisor. If a result is absent, mark **unknown**.

## Experiment and testing standard

**Stage 0:** evidence and code audit, no new solves. **Stage 1:** deterministic historical replay of advisories using only data actually available by each past decision timestamp; do not leak future rows into decision. Distinguish fidelity/noise, cache hit, cost and IDs. Because the unchosen alternative was not run, replay cannot prove its hypothetical improvement. **Stage 2:** shadow-mode next-job recommendations on a live or saved queue, but *read-only*; no disruption. **Stage 3 (owner-approved only):** equal-prior matched arm comparison with frozen control policy and a separate adaptive policy, randomized method/sequence where practical, multiple initial seeds and cohorts, exact budgets/elapsed time, verified winners, diversity/coverage value and regression checks. Treat incomplete and killed jobs as censored, not failures of acoustic merit. Only after this evidence should Fable consider autonomy.

Acceptance questions include: Does it reduce actual GPU/wall hours to reach a verified target? Does it increase *new compatible measured responses* and viable diversity without sacrificing the final score? What fraction of recommendations were wrong or premature? How many data-building jobs did the watchdog kill that later had to be resumed? How much operator attention, model-fitting overhead and queue downtime does it add? Does it preserve reproducibility? Can every decision be explained and reversed without loss?

## External primary sources for Fable to review critically

- [BoTorch TuRBO-1 tutorial](https://botorch.org/docs/v0.17.0/tutorials/turbo_1): local trust regions and restart/collapse mechanics, distinct from hard domain expansion.
- [BoTorch feasibility-driven trust-region community notebook](https://botorch.org/docs/next/notebooks_community/furbo): illustrative feasibility-driven extension, **not** evidence it is appropriate for Hornfab.
- [COCO / anytime black-box benchmarking](https://coco-platform.org/getting-started/index.html) and [Anytime Performance Assessment (2022)](https://doi.org/10.1109/TEVC.2022.3210897): evaluation-cost/target and censored-run methodology.
- [Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization](https://arxiv.org/abs/1603.06560): resource allocation and early stopping, *but* configurations/fidelity assumptions must be checked against Hornfab's stateful optimizer runs.
- [pycma documentation](https://cma-es.github.io/): restart/constraints and native CMA behavior before building an outer restart manager.

**Bottom line:** treat a search supervisor as a *testable policy competing for scarce compute*, not as a blanket auto-switcher. The likely lowest-risk first version is evidence-quality instrumentation + shadow recommendations + explicit approval, leveraging existing runner code. Fable decides whether that is actually the best scientific investment.
