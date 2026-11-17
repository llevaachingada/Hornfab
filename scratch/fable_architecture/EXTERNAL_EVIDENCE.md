# External primary evidence for optimizer and switch choices

- Repo: `C:\Users\hunte\Hrns\hornlab-search`; HEAD at final write
  `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` (`2026-11-16T20:38:46-05:00`); files were read at
  `13b47632`, byte-identical at the cited SHAs.
- This is a compact source table, not a literature review. Every source was fetched; metadata and
  abstracts were read where the publisher exposed them. A paywalled full text is marked as such.
- The question is not "is method X good?" but "what exact claim does the source support, and under
  which conditions does that claim transfer to expensive, stateful, geometry-constrained BEM?"
- No solve, benchmark, pytest or experiment was run. Historical Hornfab numbers are records, not
  fresh measurements.

Status legend: **verified metadata/abstract**; **verified claim** (abstract or open full text
supports the stated claim); **documented only** (paper says it but no independent replication here);
**plausible inference** (follows from the source but is not a quoted result); **fails/limits** is
my transfer judgement for Hornfab.

## 1. Source table

| # | Topic | Source (author/title/year) | Stable identifier | Exact claim supported | Transfers to Hornfab when | Fails / limits for Hornfab | Status |
|---|---|---|---|---|---|---|---|
| E1 | Conditional / mixed continuous-categorical BO | Wang, Hutter, Zoghi, Matheson, de Freitas, "Bayesian Optimization in a Billion Dimensions via Random Embeddings", JAIR 55:361-387, 2016 | DOI `10.1613/jair.4806`; arXiv:1301.1942 | BO had been restricted to moderate dimension; REMBO applies to domains with **both categorical and continuous variables**; it can solve billions of dimensions **provided the intrinsic dimensionality is low**; it is state-of-the-art on a 47-discrete-parameter MIP | The 6-14 Hornfab knobs may have a low effective dimension after no-op/active projection; mixed categorical knobs would need an explicit embedding, not the current discrete-refusal path | If the effective dimension is not low, or geometry feasibility makes the response discontinuous, the guarantee does not apply. It does not supply a feasibility model. A 60-100-solve budget is far below the paper's demonstration scale | verified claim (abstract); documented only for the billion-dimension result |
| E2 | Conditional parameter spaces (discrete/categorical) | Hutter, Hoos, Leyton-Brown, "Sequential Model-Based Optimization for General Algorithm Configuration" (SMAC), LION 5, LNCS 6683:507-523, 2011 | DOI `10.1007/978-3-642-25566-3_40` | SMAC's random-forest-based sequential model handles **categorical and conditional** algorithm-configuration parameters and is evaluated on algorithm-configuration benchmarks | A Hornfab task with a categorical choice (e.g. a topology switch) would need a surrogate that accepts conditional parameters; a GP over a one-hot/conditional space is a different model | The paper's empirical setting is algorithm configuration with many cheap runs, not 60-100 expensive BEM solves. A random forest is not the locked scalar GP. Full text was paywalled here; claim is limited to the documented method/benchmark scope | metadata verified; claim documented only |
| E3 | Constrained black-box optimization / separate feasibility model | Gardner, Kusner, Xu, Weinberger, Cunningham, "Bayesian Optimization with Inequality Constraints", ICML 2014, PMLR 32(2):937-945 | `https://proceedings.mlr.press/v32/gardner14.html` | A prior on **both** the objective and each constraint lets constrained BO find optimal feasible points even when small feasible regions cause standard methods to fail; feasibility is assumed as expensive as the objective | Valid when a signed constraint value is observed at infeasible points (e.g. envelope/throat/loading margins computable cheaply) | A pre-solve geometry refusal is often binary and gives no smooth margin; the model then has no signal. The code has a constrained Pareto prototype (`bo/pareto.py:90-125`) but it is not wired. Extra GPs need data, and the scalar production path has no constraint output | verified claim (abstract); transfer judgement |
| E4 | Quality diversity / multiple locally optimal solutions | Tjanaka et al., "pyribs: A Bare-Bones Python Library for Quality Diversity Optimization", GECCO 2023; docs `docs.pyribs.org` | DOI `10.1145/3583131.3590374`; `https://docs.pyribs.org/en/stable/index.html` | QD seeks a **collection of diverse, high-performing solutions covering a measure space**, not one optimum; MAP-Elites archives keep the best representative per cell; pyribs composes archive, emitters, scheduler | Useful when the deliverable is a menu of coverage/ripple/size trade-offs and the owner wants to choose, not when a single scalar J is the question | The docs' toy example is 1000 iterations x 36 solutions x 3 emitters = 108,000 evaluations. A 60-100-solve Hornfab run fills a tiny fraction of a 2-D archive. Descriptor choice (mean H/V beamwidth) is a modelling decision, not a free measure. Archive cells are not a scalar ranking | verified claim (docs); cost inference from the example |
| E4b | CMA-ME specifically | Fontaine, Togelius, Nikolaidis, Hoover, "Covariance Matrix Adaptation for the Rapid Illumination of Behavior Space", GECCO 2020, pp.94-102 | DOI `10.1145/3377930.3390232` | CMA-ME ranks CMA candidates by archive improvement to illuminate a behavior space; it is not a single-objective convergence method | Transfers only with a meaningful descriptor and enough evaluations to populate an archive | Same budget/descriptor limits as E4; the Hornfab implementation excludes failed rows from the archive but still tells them to the emitter, so invalid rows influence ranks (`search/cma_me.py:29-34`) | metadata verified from pyribs citation; claim from method |
| E5 | Parameterization / active subspaces / sensitivity | Constantine, Dow, Wang, "Active Subspace Methods in Theory and Practice: Applications to Kriging Surfaces", SIAM J. Sci. Comput. 36(4):A1500-A1524, 2014 | DOI `10.1137/130916138`; arXiv:1304.2070 | Many engineering responses vary mainly along a few directions; gradients identify the strongest directions; a response surface can be built on the low-dimensional **active subspace**; demonstrated on a 100-variable elliptic PDE | Useful if Hornfab can supply gradients or accurate finite differences and the response is smooth; could reduce an expensive 14-D GP to a few directions | No gradients are available from the BEM pipeline; finite differences cost roughly `d+1` extra solves per point, which is prohibitive at 60-100 solves. Geometry refusals create discontinuities. CMA's covariance summary (`search/cma.py:246-314`) is a local search-distribution diagnostic, **not** a global active subspace or Sobol decomposition | verified claim (abstract); transfer judgement |
| E6 | Robust engineering design | Beyer & Sendhoff, "Robust optimization - A comprehensive survey", Comput. Methods Appl. Mech. Eng. 196(33-34):3190-3218, 2007 | DOI `10.1016/j.cma.2007.03.003` | Robust optimization formulations explicitly account for parameter/uncertainty variation and trade nominal performance against robustness; the formulation and uncertainty model are choices, not a universal objective | Relevant if manufacturing/measurement tolerances are characterized and the owner wants a design robust to them | Hornfab has no quantified manufacturing/measurement uncertainty model in the scoring path; a robust objective would require repeated sampling or a surrogate of variation, multiplying BEM cost. The survey does not say robust design is free or universally superior | metadata verified; full text paywalled, claim limited to survey scope |
| E7 | Multiobjective engineering design | Deb, Pratap, Agarwal, Meyarivan, "A fast and elitist multiobjective genetic algorithm: NSGA-II", IEEE Trans. Evol. Comput. 6(2):182-197, 2002 | DOI `10.1109/4235.996017` | Fast nondominated sorting (`O(MN^2)`), elitism, crowding distance, and constrained multiobjective handling produce better spread/convergence than earlier MOEAs on the paper's test problems | Useful when the deliverable is a Pareto front and a population can be evaluated in parallel/batch | The Hornfab NSGA-II module itself estimates ~100 individuals x 100 generations = 10,000 evaluations (`search/nsga.py:1-8`). At 60-100 BEM solves it is not executable. It uses a penalty, not a separate feasibility GP. No CLI dispatch (`search/cma.py:496-506`) | verified claim (abstract); local cost documented |
| E8 | CMA restarts | Auger & Hansen, "A Restart CMA Evolution Strategy With Increasing Population Size", CEC 2005, pp.1769-1776 | DOI `10.1109/CEC.2005.1554902` | IPOP-CMA-ES increases population size on each restart so search becomes more global; on 25 CEC 2005 functions it was similar on unimodal, **significantly better in 29/60 multimodal cases, worse in 4/60** | A restart is a sensible response to premature convergence or a bad basin if the budget can pay for a larger population | The result is not universal: 4/60 cases got worse. Each restart spends the same expensive BEM budget; with 60-100 solves a restart can consume the whole arm. Warm-starting at a converged point can defeat the restart's diversity. Hornfab already implements IPOP/BIPOP (`search/cma.py:422-480`) | verified claim (abstract) |
| E9 | Trust-region BO (TuRBO) | Eriksson, Pearce, Gardner, Turner, Poloczek, "Scalable Global Optimization via Local Bayesian Optimization", NeurIPS 32:5497-5508, 2019 | arXiv:1910.01739 | Global GP-BO over-explores and is often not competitive on difficult high-dimensional problems; TuRBO fits local models and allocates samples across trust regions with an implicit bandit, outperforming SOTA on RL/robotics/natural-science problems; high-dimensional problems with several thousand observations remain challenging | Local refinement is plausible once a good basin is known and a GP is already fitted; the Hornfab variant is implemented | The paper's regime is many observations and continuous bounded domains. Hornfab has 60-100 expensive solves and geometry feasibility. The repo variant deliberately omits an every-fourth exploration cadence and any restart (`bo/turbo.py:20-26,308-311`); a collapsed region is terminal. No global guarantee | verified claim (abstract); variant divergence verified in code |
| E10 | Cost-aware / portfolio scheduling | Li, Jamieson, DeSalvo, Rostamizadeh, Talwalkar, "Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization", JMLR 18:1-52, 2018 | arXiv:1603.06560 | Hyperband speeds up random search via **adaptive resource allocation and early stopping**, with order-of-magnitude speedup on deep-learning/kernel problems | Useful if a cheap fidelity/resource exists (coarse mesh, fewer frequencies, shorter solve) and a config can be rejected early | A BEM solve is close to atomic: there is no meaningful partial-fidelity early-stop in the current pipeline, and stopping a solve wastes the partial cost. Cache hits/refusals further distort resource accounting. The paper assumes many cheap trials | verified claim (abstract); transfer fails on atomic solves |
| E11 | Anytime / censored evaluation | Hansen, Auger, Ros, Mersmann, Tusar, Brockhoff, "COCO: A Platform for Comparing Continuous Optimizers in a Black-Box Setting", Optim. Methods Softw. 36(4):1-31, 2021 (online 2020) | DOI `10.1080/10556788.2020.1808977`; arXiv:1603.08785 | COCO defines runtime by **number of function calls**, uses target values and problem instances, and supports single/multiobjective comparison; the methodology is explicitly about reproducible black-box benchmarking | The right frame for any Hornfab comparison: report best-so-far vs successful-query cost, censored/incomplete runs, and targets | COCO assumes many runs/instances and target values. Hornfab has 2-3 seeds, 1-2 tasks and unequal solve costs; final-best-only comparisons and stopping the loser early are biased. The current reports are descriptive, not COCO-grade | verified claim (abstract); transfer judgement |
| E12 | Multi-task / transfer BO | Swersky, Snoek, Adams, "Multi-Task Bayesian Optimization", NIPS 26:2004-2012, 2013 | Harvard DASH `http://nrs.harvard.edu/urn-3:HUL.InstRepos:12561002`; PDF `http://hips.seas.harvard.edu/files/swersky-multi-nips-2013.pdf` | A multi-task GP transfers knowledge from previous optimizations and **significantly speeds up** a new task versus a single-task approach when tasks are related; also supports cost-sensitive acquisition | Relevant to "may a GP share observations across shape families?" only if the tasks are genuinely related and a multi-task kernel is implemented | The current code has one `SingleTaskGP` and no task index (`bo/model.py:1-14`); the cohort gate refuses cross-task pooling (`bo/cohort.py:20-22,126-134`). The paper's speedup is conditional on related tasks; unrelated tasks can transfer negatively `[interp]`. Tiny data makes a shared kernel hard to identify | verified claim (abstract); negative-transfer part is plausible inference |
| E13 | Scaling limitation of vanilla BO | Wang et al. 2016 (same as E1), plus the TuRBO abstract (E9) | see E1/E9 | Vanilla BO is restricted to moderate dimension; on difficult high-dimensional problems it is "often not competitive with other paradigms"; REMBO works only if intrinsic dimension is low | A low-effective-dimension projection is the defensible route; otherwise more BO dimensions is not free | The cost of extra dimensions is not just GP fit time: each added knob increases `n_min=max(16,2(d+1))`, the candidate-pool volume, and the chance of geometric infeasibility. At d=14, `n_min=30`; the 100-row spend floor is only ~3.3 x `n_min` | verified claim (abstracts) |

## 2. What the evidence does **not** establish

- **It does not establish that TuRBO beats scalar BO on Hornfab.** The published TuRBO claim is
  against other optimizers in a different budget regime; the Hornfab TuRBO arm is one seed and
  followed an interrupted run (`docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md:13-17`).
- **It does not establish that constrained BO would fix geometry refusals.** Gardner's method needs
  a constraint value; a pre-solve "too large" refusal is a binary event. The code's constraint model
  exists but is not wired (`docs/queue/BO_EXT_PLAN_2026-11-16.md:70-74`).
- **It does not establish that QD is worth its budget at 60-100 solves.** The pyribs example uses
  five orders of magnitude more evaluations. QD could still be scientifically useful (archive of
  diverse horns), but that is a different claim from "better scalar J".
- **It does not establish that active subspaces transfer.** The method needs gradients; the BEM
  pipeline has none. Finite differences are unaffordable at this budget.
- **It does not establish that robust design is a drop-in objective.** The survey's formulations
  require an uncertainty model and repeated evaluations; Hornfab does not currently have either.
- **It does not establish that CMA restarts help this pipeline.** IPOP helps in 29/60 multimodal
  cases and hurts in 4/60; with 60-100 expensive solves, a restart is a large fraction of the arm.
- **It does not establish that early stopping is safe.** Hyperband assumes a resource that can be
  early-stopped; a BEM solve is atomic. Early stopping the loser of a comparison biases the
  comparison (COCO's censoring frame is the honest alternative).

## 3. Disagreements, contradictions and negative results

1. **TuRBO paper vs Hornfab variant.** The paper describes a local trust-region method with an
   implicit bandit allocation. The repo explicitly omits an every-fourth maximin cadence and any
   automatic restart (`bo/turbo.py:20-26,308-311`). The repo's `turbo_pool_v1` is a declared
   variant, not a reproduction. A claim about "TuRBO" must name which one.
2. **"BO learns from every refusal" is contradicted by the code.** Refusals and failed evaluations
   are excluded from `TrainingObservation` eligibility (`bo/data.py:107-112,241-275`) and from the
   strict cohort (`bo/cohort.py:94-107`). CMA-ME tells failures to the emitter but excludes them
   from archive admission (`search/cma_me.py:29-34,220-284`); that is not BO training data.
3. **"CMA caps candidate evaluations including cache outcomes" is contradicted.** The matched
   adapter sets `budget_counts: new` and `max_attempts: None`
   (`tools/night_queue/run_matched_home.py:112`); cache hits are free, non-cached refusals consume
   the 80. The same file labels `cma_new_candidates: 80`, `bo_screen_call_cap: 80`,
   `verify_cap: 2` (`:123`). `docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md:36-39` says
   "including refusals/cache outcomes"; only the refusal half matches the code.
4. **Pareto v7 is supported by one path and refused by another.** `freeze_metric_policy` accepts
   v4/v7 (`bo/metrics.py:527-590`) and `build_pareto_metrics` uses it
   (`studies/builders.py:963-982`); `resolve_metric_policy` is v4-only
   (`bo/metrics.py:65,254-268`); `validate_cohort` is v4-only (`bo/cohort.py:96-97`). Do not merge
   these gates by assumption.
5. **The historical BO-vs-CMA result is positive but confounded.** The report's own caveat says
   the test is warm-started from an already-optimized CMA basin, and CMA had little room left
   (`docs/status/2026-11-15-bo-vs-cma/README.md:86-92`). The unequal valid-row counts (60 vs
   31-46) and the pool pre-check (BO) vs direct sampling (CMA) are additional confounders. The
   result supports "BO improved this prior better than CMA did"; it does not support a universal
   ranking.
6. **"Stalled J = no scientific value" is false.** QD archive additions, surrogate training rows,
  and refusal/feasibility data can be valuable even when scalar J is flat. The current watchdog's
  stall rule (`tools/run_campaign_night.py:204-210`) cannot see that difference.
7. **"More dimensions are free" is false.** `MAX_ACTIVE_DIM=20` is a hard encoding limit
  (`bo/encoding.py:21-22`); `n_min` grows as `2(d+1)` (`bo/data.py:71-75`); the candidate pool is
  4096 Sobol points regardless (`bo/data.py:32,1068-1073`), so higher d means a sparser pool and
  more geometric refusals for the same budget.

## 4. Conditions under which the strongest claims fail for Hornfab

| Claim | Fails when | Hornfab-specific reason |
|---|---|---|
| "A GP can learn the landscape from ~100 points" | The response is discontinuous/feasibility-dominated, or the effective dimension is high | Geometry refusals, envelope/throat cliffs, and mixed fidelity create non-smooth targets; no gradients |
| "Constrained BO fixes infeasible regions" | Feasibility is a binary pre-solve refusal with no margin | The current refusal path returns no signed constraint value; `fit_constrained_pareto` requires measured margins for every row and is unwired |
| "QD finds a diverse archive" | The budget is 60-100 solves or the descriptor is uninformative | Pyribs' toy example is 108k evals; a 2-D archive at 60 solves is sparse, and mean beamwidth may not capture what the owner wants |
| "Active subspaces reduce dimension" | No gradients, noisy/discontinuous response, or tiny data | BEM has no gradients; finite differences cost `d+1` solves per point; feasibility jumps break smoothness |
| "Robust design is better" | No uncertainty model or no budget for repeated samples | Manufacturing/measurement tolerances are not quantified in the scoring path |
| "NSGA-II gives a Pareto front" | Population evaluation is unaffordable or a feasibility model is needed | 10,000 evaluations in the module's own estimate; no CLI route; penalty not constraint |
| "CMA restarts escape local optima" | The restart consumes the whole budget or the start is already converged | 60-100 solves; warm start from a converged basin; 4/60 cases got worse in the source |
| "TuRBO polishes a good basin" | No good basin, trust region collapses, or data are too few | One-seed historical arm; no restart; local model needs finite ARD lengthscales |
| "Hyperband allocates resources efficiently" | Evaluations are atomic and cannot be early-stopped | A BEM solve has no cheap partial fidelity; stopping wastes the solve |
| "COCO-style anytime comparison is valid" | Few seeds, unequal budgets, or early stopping of one arm | 2-3 seeds, unequal valid rows, and early stopping biases the comparison |
| "Multi-task BO transfers" | Tasks are unrelated or the kernel is misspecified | Different shape families/briefs/scores are refused by the cohort gate; no multi-task model is implemented |
| "SMAC-style categorical/conditional BO transfers" | Evaluations are expensive and the space is mostly continuous | SMAC's benchmarks are many cheap runs; the locked Hornfab GP is continuous-only and refuses categorical active dimensions |

## 5. Source-status notes

- E1/E9/E10/E11/E12 abstracts were fetched and read. E3/E8/E7 abstracts were fetched from PMLR or
  OpenAlex. E4/E4b are documentation/paper metadata; the pyribs docs page was read directly.
- E5/E6 are paywalled at the publisher; metadata and (for E5) the arXiv abstract were read. E6's
  claim is deliberately limited to the survey's scope, not a numeric result.
- E2 is paywalled; the DOI metadata was verified, and the claim is limited to the method and
  benchmark scope described by the paper. Do not cite it as proof that SMAC beats Hornfab.
- No source here proves that any method beats the current Hornfab pipeline. The only Hornfab
  comparative numbers are the historical records in
  `docs/status/2026-11-15-bo-vs-cma/` and the one-seed landscape comparison; both have the
  confounders named above.
