# Hornfab Senior Engineering Audit: Using the Existing Optimizers to Their Full Potential

**Review date:** 2026-11-21  
**Published repository:** https://github.com/llevaachingada/Hornfab  
**Public main checked:** `243136d026c9dcb59015c5d1fd322909c6079e01` (2026-11-20)  
**Scope:** existing optimization engines, their mathematical search capabilities, experimental evidence and low-risk improvements.  
**Review method:** read-only inspection of published GitHub source, historical reports and relevant primary optimization/library sources. No code edited, no BEM solve run and no active job interrupted. Local uncommitted changes and unpushed datasets were not accessible.  
**Confidence labels:** **Confirmed** (observed source or documented experimental record), **Strongly indicated** (consistent technical inference), **Hypothesis** (requires controlled validation). Reported run figures are historical observations, not independently rerun results.

## Executive verdict

**Make the existing optimization system decision-capable before expanding its algorithm catalog.** Hornfab already supports CMA-ES, IPOP/BIPOP, CMA-ME, opt-in CMA-MAE, scalar Bayesian optimization, local TuRBO-style BO and a two-metric Pareto path. Several adjacent capabilities are present but not yet integrated or validated: covariance transfer, general objective-version support in the production BO worker, cost-sensitive proposal allocation, diverse quality-diversity archives and a common strategy-selection evidence report.

**Five top priorities**

1. **P0: Correct CMA-MAE search/result archive semantics.** The current search archive and `result_archive` are constructed with the *same* soft thresholds, and the export reads the *search archive*. In pyRibs, the soft archive may replace an elite with a worse objective while the separate result archive is intended to preserve best-in-cell results. Code risk confirmed; magnitude of lost elites unmeasured.
2. **P0: Repair continuation-advice identity and stop-rule semantics.** The current rule keys numerical improvement floors only by `(objective_version, slope5-string)`. This mixes unrelated v10 task identities and can reject an improvement on the wrong threshold. It calls deterministic discretization differences “noise.” Use complete score/fidelity/frequency/mesh identity.
3. **P0: Reconcile production BoTorch with v10/v11.** The published study production worker still allows only objective v4/v7, even though v10 metric helpers exist and objective v11 is registered elsewhere. Distinguish reusable GP machinery from an actually executable, versioned production study.
4. **P1: Reuse learned search distributions safely.** Warm-start currently imports the best mean and a top-k spread-based sigma, not full covariance or eigenvectors. A full `C` diagnostic is saved for non-restart CMA with <=16 dimensions. A narrowly controlled covariance-transfer experiment could reduce relearning in similar short searches.
5. **P1: Compose an advisory search supervisor from tools already present.** Integrate, do not reimplement: space-card, parameter activity, seed-pack, walls, optimizer-switch, continuation advice, QD comparison, budget heuristics and strict BO study admission. It should recommend next experiments with provenance, not change queues or algorithm defaults.

## 1. Current capability matrix

| Component | Current published status | Most useful next decision | Evidence |
|---|---|---|---|
| CMA-ES | **Implemented/active** | Preflight sigma, bounds, refusal causes, adaptation budget; compare multi-start | `hornlab_search/search/cma.py` |
| IPOP/BIPOP | **Implemented opt-in** with shared budget and deterministic resume | Benchmark only for budgets sufficient to complete restarts; independent starting means matter | `search/cma.py`, `_RestartSchedule` |
| CMA warm-start | **Implemented but limited** to best mean + top-k spread sigma | Test transfer of full covariance across identical compatible coordinates | `search/warmstart.py` |
| CMA covariance capture | **Implemented diagnostic**, full C for non-restart and d<=16 | Add guarded import/transform under separate search-policy identity | `search/cma.py::covariance_summary` |
| Local LQ-assisted CMA | **Implemented opt-in**, efficiency benefit not established | Equal-real-BEM-call A/B vs plain CMA | `search/cma.py`, `search.surrogate: lq` |
| CMA-ME | **Implemented**, one emitter, mean H/V beamwidth grid | Compare descriptor choice, genuine acoustic diversity and archive efficiency | `search/cma_me.py` |
| CMA-MAE | **Implemented opt-in with archive bug risk** | Split soft learning archive from strict best-result archive | `search/cma_me.py::make_archive` |
| Constrained QD emitter | **Designed, not implemented** | Defer until correctness and plain QD benchmarks | `docs/research/bo_study/QD_CONSTRAINED_EMITTER_DESIGN.md` |
| BoTorch scalar GP/qLogNEI | **Implemented and empirically promising in a limited task** | Standardize data eligibility, objective compatibility, real cost accounting | `bo/model.py`, `acquisition.py`, `studies/production.py` |
| TuRBO-style local BO | **Implemented Hornlab variant**, one region, no silent restart | Replicate same-information comparison and test multi-basin only if needed | `bo/turbo.py` |
| Pareto BO | **Implemented for two physical errors** (coverage, ripple), policy-sensitive | Broaden only after metric support and archive integrity validated | `bo/pareto.py`, `bo/metrics.py` |
| NSGA-II | **Implemented numerical helper, not CLI search dispatcher** | Retain as offline comparator, not a new production workflow yet | `search/nsga.py` |
| Cost-aware BO | **Functions exist, not production-integrated** | Evaluate measured actual BEM time, not cache hits or imagined costs | `bo/extensions.py` |
| Optimizer recommendation | **Separate read-only tools** | Compose a single evidence summary; keep advisory | `tools/analysis/optimizer_switch.py`, `continuation_advice.py`, `space_card.py` |

The current main includes supported scoring versions 1,2,3,4,5,6,7,9,10,11. A scoring version supported by `objective/versions.py` is **not** synonymous with a version accepted by every BO study worker or Pareto metric path.

## 2. Detailed code findings

### A. CMA-MAE best-in-cell preservation: P0

`hornlab_search/search/cma_me.py` creates `maes`-configured archives through one `make_archive()` helper and then calls:

```python
archive = make_archive()
result_archive = make_archive()
scheduler = Scheduler(archive, [emitter], result_archive=result_archive)
```

For CMA-MAE, both therefore get `learning_rate < 1` and finite `threshold_min`. Later `archive_payload()` does `data = archive.data()`, so published archive and heatmap are taken from the *search* archive rather than best-result archive. The official pyRibs tutorial explicitly distinguishes these: the soft search archive can contain a lower-performing replacement; the result archive is the best-elite archive.

**Remedy:** construct the soft search archive unchanged; construct `result_archive` as a conventional failure-excluding hard elite archive with `learning_rate=1.0` and `threshold_min=-inf`; export best-in-cell tables and heatmaps from `result_archive` while optionally preserving a separate, clearly labeled learning-archive diagnostic. Regression test: in the same cell insert a score 10 and then 9 where 9 beats the *soft threshold* but not 10. Require result cell = 10, even if the learning archive stores 9. Because existing deterministic replay and serialized archive meaning can change, version the QD protocol and refuse silent reinterpretation of old runs. Review seed insertion, scheduler `tell`, restart/replay and both error/eligibility masks.

**Do not confuse archive admission with feasible-only emitter learning.** The existing archive masks exclude ineligible records from storage, but the emitter still receives failure-last ranking information. The proposed constrained emitter contract has not been implemented.

**Source:** https://docs.pyribs.org/en/stable/tutorials/cma_mae.html ; https://docs.pyribs.org/en/stable/api/ribs.schedulers.Scheduler.html

### B. Stop and switch decisions use insufficient identity: P0

`tools/analysis/continuation_advice.py` currently has `FLOORS={(7,''):0.3105,(10,''):0.4677,(10,'slope5'):0.4863}` and derives a score identity chiefly from objective number and the substring `slope5` in the brief path. Yet the contemporaneous compact400 v10xo study measured a **0.1293 J** within-study floor; that is not the home-v10 floor. A gain of 0.18 J on that compact identity could be wrongly dismissed by the generic 0.4677 rule. Nothing in this observation proves that a particular run has been incorrectly stopped, because this script is advisory.

Make a **floor registry keyed to exact resolved score identity, physical solver identity, comparison grid, and test method**, including sample size and the source of numerical error estimates. Unknown identity = “no applicable published floor,” never borrow another brief's threshold. Separate deterministic fidelity bias, measured uncertainty and stochastic variability. Use a common-grid verification decision for borderline cases.

`tools/analysis/optimizer_switch.py` also counts all non-valid records as a single failure/refusal fraction, mixing cached outcomes, deterministic geometry refusals and infrastructure errors; it currently warns about the distinction but doesn't quantify each kind. Integrate typed outcome counts and cost ledger before recommendations.

### C. BO objective compatibility is a production limitation: P0

`hornlab_search/studies/production.py` explicitly refuses objectives outside `(4, 7)` during production validation, while v10 has a separately versioned metric helper in `hornlab_search/bo/metrics.py` and v11 has a registered objective scorer in `objective/scalar_v11.py`. `studies/builders.py` declares the accepted task registry. Investigate the producer/worker/admission/verify/export chain end to end rather than removing the guard alone. Any new metric adapters must have score replay parity, full versioned hashes and no inadvertent mixed-version training. Keep existing v4/v7 study contracts unchanged.

The BO training code excludes unresolved/refused BEM results, deduplicates by physical geometry and solve identity, and by default fits a scalar GP to `Y=-J`; it cannot automatically infer feasibility quality from discarded refusals. A separately named native training helper can declare mixed fidelity, which is not the same as correcting screen/verify bias. Enforce strict physical comparability for controlled pilots.

### D. Covariance knowledge transfer: P1 research

`search/cma.py::covariance_summary` records sampling-direction eigens, per-knob sigma and full matrix `C` only if `include_C=True` and `n_dim<=16`. Non-restart CMA requests full `C` at the end; restart summaries request only compressed statistics. `search/warmstart.py::mean_and_sigma` selects an earlier best design and optionally estimates a scalar sigma from its top-k spread. It does not import full covariance.

**Safe mathematical route:** with old/new bound-span diagonal matrices `D_old`, `D_new`, transform the *actual sampling covariance* `Sigma_old = sigma_old^2 C_old` to the new unit coordinates as:

`Sigma_new = D_new^{-1} D_old Sigma_old D_old D_new^{-1}`.

Recenter using the physical incumbent coordinates; rescale to a declared new `sigma0`, so `C_new = Sigma_new / sigma0^2`. Add regularization (eigenvalue floor/cap and conservative blending toward identity), and verify symmetric positive definiteness, expected candidate variation, geometry acceptance and exact parameter mapping. This is only meaningful for compatible search knobs and geometry laws; source objective/brief/fidelity similarity is a **condition**, not an assumption. An academic warm-start study shows naïve mean/covariance copying can fail when tasks are dissimilar.

Run an offline sampling test first, then compare mean-only vs covariance-informed warm starts on a task where CMA's covariance has had enough generations to learn something. Short runs may never yield informative covariance.

**Source:** https://cdn.aaai.org/ojs/17109/17109-13-20603-1-2-20210518.pdf ; https://cma-es.github.io/apidocs-pycma/cma.evolution_strategy.html

### E. Effective search dimension: P1 analysis

There are three different things often confused: **(i)** active config knobs, **(ii)** independent geometric degrees of freedom and **(iii)** acoustically important directions under a particular target and frequency band. Existing `tools/analysis/parameter_activity.py`, `geometry_effects.py`, `space_card.py` and linked-parameter handling can distinguish the first two. Calculate an approximate surface/area/meridian Jacobian with respect to normalized knobs, examine singular values and near-collinear columns, and confirm potential redundancy over multiple anchor designs, not just the incumbent. Then compare with response/score sensitivity on matched saved observations. CMA covariance eigendirections are search-distribution information, not a replacement for acoustic sensitivity or full active-subspace evidence.

Don't permanently remove knobs based on one brief's low sensitivity. Test reversible reduced-coordinate runs, retain a no-reduction control, and preserve all original physical coordinates in records.

**Sources:** https://epubs.siam.org/doi/10.1137/1.9781611973860.ch4 ; https://link.springer.com/article/10.1007/s11831-025-10349-x

### F. Geometric searchability and refusal handling: P1

Hard clipping occurs in `hornlab_search/design/space.py::denormalize`; geometry and brief envelope refusal paths exist in `search/evaluate.py` and BO pool filtering. A size envelope is a product brief, while self-intersections and invalid driver coupling are intrinsic geometry/physics constraints. In separate, fully identified **discovery studies**, consider allowing report-only oversize shapes within hardware/resource caps, recording actual acoustic responses and dimensions for a size-versus-acoustics Pareto analysis. Do not silently change existing production brief semantics. Remember widening bounds changes normalization coordinates: historical normalized GP vectors cannot simply be reused under new bounds.

If refusal storms are frequent, first exploit cheap geometry preflight and existing strict resampling. Explicit inequality constraints via `cma.fmin_con2` and constrained BO are valid research options, but they need a proper continuous physical margin and matched-cost validation before replacing current handling.

## 3. Historical acoustic and optimizer evidence

| Record | What it says | What it does **not** establish |
|---|---|---|
| Nov 15 BO vs CMA, one warm 80x60 task | Three BO verify J: 3.107/3.251/3.189, median 3.189; CMA: 3.827/3.827/3.392, median 3.827. CMA refused 14–29 of 60 attempts, BO 0–3. | Universal BO superiority. BO had 185 fitted historical rows and a prechecked pool; CMA received only one starting mean and different invalid-handling. |
| Nov 16 landscape scalar vs TuRBO | Reported verified 3.149 scalar vs 2.766 TuRBO. | Reliable algorithm ranking: one seed, TuRBO followed an interrupted run. |
| Nov 17 Klangfilm sigma/bounds | Full bounds/sigma 0.25: 24 refusals of 45, no improvement from 6.401; seed-centered bounds/sigma 0.10: 9 refusals of 102, best 2.819. | Isolated sigma causation: both sigma and bounds changed, and attempts differ. |
| Nov 19 compact400 v10xo verification | Verify J 1.1864 / 1.2763 / 1.3734; adjacent gaps below floor 0.1293, effectively a tie. | That the lowest numerical J is a robust winner across full polar or installed-system metrics. |
| Nov 19 home v10 fold | Common-grid verify J 1.4867 vs published 1.6704, 0.184 improvement. | A cross-brief winner, or a universal case for the fold family. |
| Le Cléac'h staged vs joint | Actual staged J 2.629, joint 2.439. | Equal-budget superiority: the record contains 63 stage evaluations versus 104 joint evaluations, despite a description calling it equal budget. |

Source reports:
- https://github.com/llevaachingada/Hornfab/blob/main/docs/status/2026-11-15-bo-vs-cma/README.md
- https://github.com/llevaachingada/Hornfab/blob/main/docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md
- https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md
- https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/P12_VERIFY_2026-11-19.md
- https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/STAGED_SEARCH_AB_2026-10-31.md

## 4. What method should be used, and when?

| Situation | Preferred existing capability | Caveat |
|---|---|---|
| New family, little coherent historical data, 5–20 continuous knobs | CMA-ES, legal geometry preflight, several diverse seeds | Short budgets may not learn covariance; check sigma/constraints first |
| Search stalls and evidence supports multiple viable basins | Independent CMA starts; IPOP/BIPOP only when meaningful restarts fit the remaining budget | Restarts centered at the same incumbent are not independent basin discovery |
| Well-populated single-brief archive and expensive BEM calls | Scalar BoTorch, a controlled alternative to CMA | GP pool/model overhead may dominate at cheap screen fidelity; require strict data identity |
| Refine one promising local region | Existing TuRBO-style BO or local CMA | Current TuRBO has one region; terminal collapse is not automatic multi-start |
| Discover meaningfully different coverage families | CMA-ME; CMA-MAE only after archive correction | Current mean H/V width descriptors miss lobe, loading, size and spectral differences |
| Expose competing physical criteria | Pareto postanalysis/BO on frozen coherent metrics | Current production Pareto is coverage/ripple only; NSGA-II is numerical helper, not CLI |
| Repeatedly identical shapes from many knobs | Geometric parameter-activity diagnostics and reversible coordinate reduction | Check family construction and acoustic sensitivity before blaming optimizer |
| Different solve cost by geometry | Actual cost ledger then controlled cost-aware proposal selection | Existing helper does not prove benefit; keep GPU memory caps and true-call accounting |

**Decision rule:** maximize *best verified same-identity acoustic gain* and the number of *distinct, physically valid verified basins* per actual backend time, including preparation and optimizer overhead. Never compare raw J across different resolved briefs or versions.

## 5. Minimal controlled validation program

**Phase 0: offline correctness, no GPU.** Repair and test QD archive semantics; audit floor identity; run advisory outputs on recent records; create a scored/physical cohort and provenance manifest; establish existing CMA, BO and QD workflow capabilities. Include synthetic path assertions for archive semantics, but do not treat synthetic optimization functions as proof of acoustic benefit.

**Phase 1: cheap strategy sensitivity.** Preflight a factorial trial with sigma and bounds varied independently (2x2), using at least one refusal-heavy family and one geometry-healthy family. Evaluate predicted geometry acceptance offline, then request a small explicit BEM budget only for unresolved hypotheses. Quantify valid evaluation fraction and distinct geometry basins.

**Phase 2: matched real BEM A/B.** Pick two different but comparable physical tasks (for example a current v7 incumbent task and a current v10 task **only once** BO fully supports it). Freeze within-task objective identity, geometry/driver, source model, exact bounds, mesh, frequency/angle grids, version hashes, solve backend, historical training/cohort access, common incumbent and eligibility. Run paired random seeds for **cold CMA, mean-only warm CMA, covariance-informed CMA if supported, scalar BO and TuRBO**; use 5 seeds/arm as an initial pilot if practical. Separately report new backend calls, attempts/refusals, cache hits, optimizer overhead, wall-clock, convergence curves, finalist verify cost and confidence/uncertainty. Reject cross-arm information leakage. Do not label 80 CMA *candidate attempts* equivalent to 80 BO *successful BEM calls*.

**Phase 3: QD experiment.** After archival correctness, compare ordinary CMA-ME with CMA-MAE and one acoustically better descriptor proposal. Freeze descriptor units and grid edges; track occupied cells, verified best-in-cell quality, physically distinct shapes, full polar/lobe/DI consistency and cost. A sparse 100-evaluation map is not evidence that a dense archive is exhausted.

Predefine any superiority threshold as an **effect that survives common-grid verification and exceeds the appropriate numerical uncertainty floor**, not simply a p-value or a provisional screen-J difference. Follow the COCO anytime benchmarking principle: compare best-so-far against actual budget and time, with incomplete/stopped arms represented fairly.

**Source:** https://numbbo.github.io/coco-doc/perf-assessment/

## 6. Prioritized implementation roadmap

| Order | Reviewable change | Principal paths | Acceptance and risk |
|---|---|---|---|
| P0a | Correct MAE dual archives and export semantic, version replay | `search/cma_me.py`, `tests/test_search_cma_mae.py`, `tests/test_search_cma_me.py` | Hard result archive cannot regress within a cell; old protocol not silently reinterpreted; risk to resumed runs demands isolation |
| P0b | Full-identity numerical floor registry / safer continuation advisory | `tools/analysis/continuation_advice.py`, `optimizer_switch.py`, corresponding tests | Unknown floor refuses decisive recommendation; compact400 not assigned generic v10 floor |
| P0c | BO objective compatibility audit and *opt-in* v10/v11 integration | `bo/metrics.py`, `studies/production.py`, `studies/builders.py`, `bo/policy.py`, `tests/test_bo_metrics_v10.py`, additional v11 tests | Scalar model/cohort/verify replay parity on frozen current briefs before production worker is opened |
| P1a | Curated optimizer-evidence report (advisory only) | `tools/analysis/space_card.py`, `parameter_activity.py`, `seed_pack.py`, `walls.py`, `optimizer_switch.py`, `continuation_advice.py`, `qd_compare.py`, `search/budget_heuristic.py` | JSON with typed evidence, identities, uncertainty, at most 2 suggested alternatives; never dispatches work |
| P1b | Covariance transfer, separately identified opt-in | `search/cma.py`, `search/warmstart.py`, config schema, tests covariance/warmstart | SPD coordinate transform, damping and historical comparability; no default change without measured pilot |
| P1c | Controlled benchmark orchestration and compare report | `tools/analysis/ab_compare.py`, `tools/analysis/study_cohort.py`, `studies/`, new bounded test configs | Paired seeds, matched historical information and actual BEM+wall time; no cross-task raw-J ranking |
| P2 | QD descriptor study and possible second emitter | `search/cma_me.py`, `tools/analysis/qd_compare.py`, `metrics/acoustic_v2.py`, QD tests | Verified broader basins per cost, stable archive-grid specification |
| P2 | Cost-aware BO pilot | `bo/extensions.py`, `bo/policy.py`, `studies/evaluator.py`, timing manifests | No systematic worse time-to-verified-target or extra overhead; existing helper alone not enough |

**Explicitly defer:** automatic strategy switching, wholesale geometry-family rewrite, large exact GP over all heterogeneous historic rows, hard removal of weak-sensitivity parameters, multi-fidelity BO trained on uncorrected screen/verify differences, global neural surrogate training, unvalidated “universal” objective changes, and heavy CMA-MAE emitter internals. The `search/nsga.py` helper need not become production CLI merely because it exists.

## 7. Acceptance and agent handoff instructions

The senior local agent should begin with `git status --porcelain`, current HEAD/branches/worktrees, `tools/night_status.py`, pinned library versions, diff against current published `main` and the first 60–80 lines of active queue/status ledgers. A stale public `ACTIVE_STATE.md` claim that the GPU is free is not sufficient authorization. Check current code before treating any item above as still outstanding. Segregate live/uncommitted GPU lanes and never modify pending-run hashes or score versions. Work in small separate commits/PRs; first change should be **CMA-MAE archive preservation tests and patch**, unless local main already fixed it. Report old/new archive comparisons and evidence of no inappropriate resume migration.

Second, fix the floor-identity advisory before its output influences a queue. Third, audit and separately register BoTorch current-scoring compatibility with full regression replay. Fourth, deliver a single read-only optimizer recommendation report using existing tools. Only after that authorize matched physical experiments. Use the current repository tests plus targeted real run evidence to accept implementation, not green unit tests alone.

**Success criterion:** Hornfab can explain which optimizer to choose, why it is promising on this *specific* physical task, what the verified alternatives are, and how much real solve time and uncertainty the decision entails. It does not silently equate a low score with a better loudspeaker.

## Primary research and official software references

- Official pyRibs CMA-MAE, two archive semantics: https://docs.pyribs.org/en/stable/tutorials/cma_mae.html
- Official pyRibs Scheduler result archive: https://docs.pyribs.org/en/latest/api/ribs.schedulers.Scheduler.html
- pycma CMA-ES, restarts, BIPOP: https://cma-es.github.io/apidocs-pycma/cma.evolution_strategy.html
- Warm Starting CMA-ES for Hyperparameter Optimization (AAAI 2021): https://cdn.aaai.org/ojs/17109/17109-13-20603-1-2-20210518.pdf
- Eriksson et al., TuRBO (NeurIPS 2019): https://proceedings.neurips.cc/paper/2019/hash/6c990b7aca7bc7058f5e98ea909e924b-Abstract.html
- BoTorch constrained Bayesian optimization: https://botorch.org/docs/tutorials/scalable_constrained_bo
- BoTorch cost-aware optimization: https://botorch.org/docs/tutorials/cost_aware_bayesian_optimization
- SIAM Active Subspaces: https://epubs.siam.org/doi/10.1137/1.9781611973860.ch4
- Engineering shape dimensionality survey (2025): https://link.springer.com/article/10.1007/s11831-025-10349-x
- COCO anytime performance assessment: https://numbbo.github.io/coco-doc/perf-assessment/
- pycma constraint handling: https://cma-es.github.io/apidocs-pycma/cma.constraints_handler.AugmentedLagrangian.html
- QD literature catalog (Fontaine CMA-ME/MAE): https://quality-diversity.github.io/papers.html

**Bottom line:** correct the two clearest decision/record problems, bring existing BO up to the current scoring contracts, then demonstrate covariance reuse and matched optimizer superiority. Do not let better code infrastructure substitute for better verified horns.
