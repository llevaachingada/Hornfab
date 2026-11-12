# Search-Math Research Dossier — 2026-11 (day group R)

**Repo:** `llevaachingada/Hornfab` (hornlab-search), worktree `oc-wt\R`, branch `day/R-research-dossier`, main tip `2ecbc69`.
**Lane:** research continuation after a prior research lane died; this dossier was written from a **verified source pack** (below) plus read-only inspection of repo source and installed library source. No new web research, no solves, no GPU.

**Citation shorthand**

- `S1`–`S7b` = the verified source pack refs listed at the bottom.
- `[repo: <file>:<line>]` = `hornlab_search/...` source in this repo, read at main tip `2ecbc69`.
- `[pycma]` / `[ribs]` = installed library source, read-only, at
  `C:\Users\hunte\Hrns\hornlab-search\.venv\Lib\site-packages\{cma,ribs}\**`,
  verified versions: **pycma 4.5.0, ribs 0.12.0, sklearn 1.9.1, scipy 1.18.1** (import check run 2026-11-12).
- `[TO-VERIFY — check …]` = a claim the source pack does not cover and library/repo source could not confirm. These are **not** established facts; each names the exact reference to check.

**Honesty rules applied here:** every numeric claim about our runs is either senior-measured 2026-11-12 (given to this lane) or marked `[measured]` with the exact script (below). At most one short quote per source. Nothing else is asserted without a primary source.

---

## Owner summary (plain language)

1. **Refused designs are eating the search.** ~14–16% of every solve comes back as "invalid geometry / mesh too large / outside envelope" and is scored a flat 1000. At that plateau the optimizer cannot tell a near-miss from a disaster, and a run whose whole generation fails looks *finished* (flat fitness), not stuck [repo: search/cma.py:121-126]. The cheapest fix is to make refusals **rare and graded** before they happen, and to keep the optimizer's population inside the feasible region with pycma's own feasibility-resampling.

2. **A weight is not an influence.** In objective v4 the coverage term (weight 1.0, same as ripple) owns a median **42%** of J while ripple owns **1%** and loading **0%**. The cause is arithmetic, not acoustics: coverage errors are **squared** and divided by fixed tolerances, so the farther a design is from target the more cov swallows everything; a linear dB term can never compete. Section 6 shows the numbers and proposes a **v8 recipe**: linear-ish error units, tolerances calibrated from our own 28k-row archive, clamped worst-case terms, and lexicographic gates instead of giant penalties.

3. **The screen lies by construction.** Screen cannot rank the top-20 it itself produced (verify beats screen in 95% of 104 pairs), because a 12-point 500–10 kHz grid plus selection bias makes the top of a coarse grid look better than it is. Stop treating screen rank as truth: **verify 15–20 finalists, rank by verify J only**, and add a couple of mid-band screen points the config already supports (`screen_extra_hz`, [repo: config.py:344-358]).

4. **Variance is the real enemy.** Best-J at fixed budget swings 26–59% between seeds, and 42% of runs were still improving at the end. More independent seeds with restarts (BIPOP already implemented, off by default [repo: search/cma.py:16-21]) plus warm starts from our archive are cheaper buys than longer single runs.

5. **The QD atlas is the right artifact, the wrong knobs.** CMA-ME already maps the horn space; CMA-MAE (one `learning_rate` parameter) plus the second "result archive" that pyribs 0.12 scaffolds would let backwards and forwards progress coexist, and infeasible rows must stop borrowing the seed's archive coordinates ([repo: search/cma_me.py:304-317]).

6. **Comparison hygiene:** with a 26% spread, detecting a 10% improvement between two configs needs **~106 runs per group** — far beyond what we run. Any honest "config A beats config B" claim needs paired seeds, bootstrap CIs on the paired differences, and the ECDF/ERT reporting style of IOHprofiler [S4/S4b]. This is a workflow change, not a code change.

Proposed **new dependency:** none this round. SALib (given-data sensitivity, [S5]) is only justified later, once §9's own-data analysis (rank correlations + CMA covariance eigenvectors, already dumped per run [repo: search/cma.py:51-119]) has shown it is insufficient.

---

## Preliminaries: what our search actually is (verified)

- Single-ES CMA-ES in the unit box `[0,1]^k` with `bounds=[0.0,1.0]` passed to pycma, `x0` = normalized seed, budget caps **non-cached** evaluations only; the partial generation at budget end is never `tell`-ed; resume replays from cache for free [repo: search/cma.py:3-14, 316-321, 441-443]. Bounds outside the unit box are handled by `DesignSpace.denormalize` clipping, **not** by CMA penalties [repo: search/cma.py:3-4].
- IPOP/BIPOP restarts exist behind `search.restarts: {mode: ipop|bipop, max: N}` and mirror pycma's own schedule (IPOP doubles popsize `2**k`; BIPOP alternates small/randomized runs `popsize0·m**(U²)`, `sigma0·0.01**U` with large runs; two deliberate divergences documented) [repo: search/cma.py:222-279, 464-516; config.py:727-748]. Off by default [repo: config.py:119].
- CMA-ME (`search.algorithm: cma_me`) uses ribs 0.12.0 `GridArchive` + one `EvolutionStrategyEmitter` (`ranker="2imp"`, `es="cma_es"`, `selection_rule="mu"`) + `Scheduler`, descriptors = mean in-band H/V −6 dB beamwidth in degrees, archive range fixed `[0,180]°` [repo: search/cma_me.py:20-28, 54, 123-146]. Failed evaluations are told back with **the seed's archive coordinates** and a penalty objective [repo: search/cma_me.py:304-317]; solutions are clipped to `[0,1]` before denormalize [repo: search/cma_me.py:363-368].
- The evaluator never raises; deterministic failure kinds (`invalid_geometry`, `invalid_envelope`, `mesh_too_large`) are memoized/marker-cached, solver failures are not, and scored penalties are `PENALTY_INVALID = PENALTY_FAILED = 1.0e3` [repo: search/evaluate.py:65-74, 11-19; objective/terms.py:16-19]. A graded envelope penalty exists behind `search: {infeasible_penalty: graded}`: `1000 + 100·overshoot`, capped at 2000 [repo: search/evaluate.py:1001-1015; objective/terms.py:104-115].
- After 3 consecutive `solve_failed` the run aborts (resumable) because scoring them as 1000-penalties flattens the landscape and CMA-ES then ends on `tolflatfitness` (OSSE seed 4101, 2026-10-23) [repo: search/cma.py:121-126].
- Objectives: `J = Σ_k w_k·term_k/tol_k + penalty` (v4/v6/v7), stored terms are the normalized values; v4 adds `distd`/`diag`, v6 is loading_smooth, v7 adds loading-frequency (LFP), constant-velocity flatness, 8 kHz floor, asymmetric V [repo: objective/scalar_v4.py:9-13; scalar_v6.py:1-11; scalar_v7.py:34-33, 78-85]. Default v4 weights `{cov:1.0, rip:1.0, di:0.3, dislope:0.5, flat:0.5, load:0.0}` [repo: objective/terms.py:30]. Term raw units: cov/diag/di/dislope **squared** errors (`err²/100`, `err²/10`), rip/flat/load **linear** (mean ripple dB, std dB, under-load hinge) [repo: objective/terms.py:49-98].
- Screen/verify/final grids are frozen: screen 12 points 500–10 000 Hz, verify 25 points 300–16 000 Hz, final 36 points 250–20 000 Hz [repo: config.py:27-31]; opt-in `grid.screen_extra_hz` can append extra screen points (approved: 250/315/400 low + 2573/3311/4260 mid-band) [repo: config.py:344-358, 367-371]; verify HF density extension starts at 5 kHz [repo: config.py:46-47].

---

## Q1. Constraint handling for cheap-to-check infeasibility (~16% of evaluations)

### What the literature / sources say

- S7 (CMA-ES tutorial): abstract-level restart-strategy background; the specific statement about truncated-selection bias when sampling is restricted needs checking. **[TO-VERIFY — check Hansen, arXiv:1604.00772, section on boundaries/selection]**
- S6 / pycma source (verified 4.5.0):
  - `cma/options_parameters.py:197 — def is_feasible(x, f)`: the option-level feasibility predicate pycma's resampling machinery consults.
  - `cma/evolution_strategy.py:2139 — def ask_and_eval(...)`: ask + evaluate with **feasibility resampling** (regenerates samples until feasible, `irun` budget-limited; then evaluates the last sample and lets the fitness functions penalty take over).
  - `cma/evolution_strategy.py:5496 — def fmin_con2(...)`: the newer constrained-optimization driver using an augmented-Lagrangian view of constraints; the `tell` fitness machinery computes and updates "an augmented Lagrangian" and returns those values as fitness [pycma: evolution_strategy.py:3426-3429, with 2539 noting the dynamic augmented Lagrangian is what is optimized].
  - `cma/boundary_handler.py:454 — class BoundTransform`: injects a fixed-coordinate transform; our plain CMA path instead relies on denormalize clipping [repo: search/cma.py:3-4].
- Our own penalty design is already large-and-finite for a reason: "**Never inf: one inf poisons the CMA-ES covariance update for the rest of the run.**" [repo: objective/terms.py:16-17], and the graded envelope penalty aims penalties back toward the feasible region [repo: objective/terms.py:101-115].

### The math

With flat penalties, a feasible region cut Φ = 16% of samples distorts selection: in a generation of popsize λ, the μ best *feasible* individuals are a biased draw of the μ best overall — effectively a truncated sampling problem; the estimator of the progress direction loses rank information exactly near the boundary. Resampling keeps F values informative but wastes budget; graded penalties keep budget but reintroduce landscape slope (good if graded correctly, terrible if a far-outside design scores like a near-miss — see the J=1000 ties: 9.8% of generations were ≥50% flat-penalty ties, senior-measured 2026-11-12).

### Mapping to our setup

Refusals decompose (senior-measured; my whole-tree spot-check `[measured 2026-11-12]`, script `study_2026-11-12/research/spotcheck_findings.py`, 415 runs / 34 475 ndjson rows: failures 13.8% — invalid_geometry 9.1%, mesh_too_large 2.6%, invalid_envelope 1.7%):

| Cause | Cheap to predict pre-mesh? | Right tool |
|---|---|---|
| `invalid_geometry` (generator refuses) | yes — it is a pure function of design params | resampling (reject + re-ask), keep count |
| `mesh_too_large` | partially — dof is monotone in resolution knobs | resampling with a dof-cap feasibility predicate |
| `invalid_envelope` | yes — envelope overshoot is computed pre-mesh (WP3) [repo: evaluate.py:1001-1015] | graded penalty (already shipped) |

### Recommendation (ONE): pre-mesh feasibility predicate + pycma resampling

Keep the penalty bedrock (never inf), but stop spending 16% of budget on designs a cheap check can reject:

1. Give pycma the truth: wrap the objective so that a deterministic refusal (`invalid_geometry`, `invalid_envelope`, `mesh_too_large`) is signalled by returning the value *and* setting `is_feasible = lambda x, f: feasible_flag(x)` in the options dict. pycma's `ask_and_eval` then resamples the infeasible draws (budget-limited) instead of training the CMA on a 1000-plateau [pycma: options_parameters.py:197; evolution_strategy.py:2139].
2. Config sketch (illustrative; would be a new small optional block, not shipped from this doc):

```yaml
search:
  feasiblity_resample: true      # opts["is_feasible"] = design-level pre-mesh predicate
  resample_budget: 0.15          # stop resampling after ~15% of popsize extra asks each gen
  infeasible_penalty: graded     # already implemented [repo: config.py:118]
```

3. Bound-wall optimum (morph_fixed pinned 32/51 runs, tmax 11/22, 7% of knobs within 2% of a bound — senior-measured): an optimum sitting *on* a bound is a modelling statement, not a search problem; where the physics allows it, **widen the bound or move the knob** (re-express in log space), rescaled by a one-knob experiment, rather than fight the wall with penalties. For knobs where the wall is real (mesh budget), keep the clipping [repo: search/cma.py:3-4] and accept boundary optima; the resampled boundary draws then simply count as infeasible.
4. `fmin_con2` / augmented Lagrangian is the *scholarly alternative* for the envelope overshoot (a continuous constraint value we already compute) [pycma: evolution_strategy.py:5496, 3426-3429], but it changes the fitness values the CMA sees (Lagrangian, not J), which would break every stored-J comparison and the verify/screen contract. Park it.

### Expected gain / risk / test

- Gain: up to ~10% more real evaluations per run (the invalid_geometry share) plus un-flattened generations; avoids `tolflatfitness` stop-looks-like-finish episodes [repo: search/cma.py:121-126].
- Risk: resampling wastes asks when a whole region is infeasible (cap the resample budget); a wrong predicate would hide real information.
- Test with our data: replay 10 archived run configs with the resampling option offline (no solves — the ndjson history supplies F), and compare (a) refusal share, (b) fraction of generations with ≥50% flat-penalty ties [finding 1], (c) best-J at equal non-cached budget.

---

## Q2. Surrogate-assisted CMA-ES (lq-CMA-ES) at 5–20 D with a 28k-row archive

### What the sources say

- S1 (lq-CMA-ES, GECCO 2019; mechanics also documented in pycma's own `cma/fitness_models.py` header). Verified from installed source: `LQModel` (class at fitness_models.py:398) builds linear (d+1), diagonal (2d+1), then full-quadratic (d(d+3)/2+1) models by pseudo-inverse on rank-based weights (`sorted_weights`, `max_weight=20`; settings at fitness_models.py:371-381, method at 538-540); `SurrogatePopulation` (class at 94) truly evaluates at least one solution, and keeps adding true evaluations while Kendall tau between model and truth is below `tau_truth_threshold` (default **0.85**, fitness_models.py:85, check at 307), then predicts the rest. Documented caveats (pack S1): model-size setting 1.0 poor on some functions (1.1 fine), Hessian not guaranteed PSD, poor on Rosenbrock-like ill-conditioned valleys (see also the comment at fitness_models.py:766).
- S6: `fmin_lq_surr2` verified at pycma evolution_strategy.py:4417 (exported via cma/__init__.py:131).
- Alternatives GP-EI / TuRBO / RF-GBM: general knowledge, not grounded in this pack. **[TO-VERIFY — check any primary surrogate-BO reference, e.g. Kandasamy et al. TuRBO ICML 2020]**

### The math

lq-CMA-ES replaces most of a generation's true evaluations with quadratic-model predictions. With d=10 (FREEFORM-class designs are around 10–20 knobs), the full model needs d(d+3)/2+1 = 76 support points before it can fit the full quadratic — at our 10–60 s/candidate and 150-evaluation budgets, the model only becomes trustworthy in the last third of a run. That is why S1's mechanism (start linear, grow as data accumulates) matters: we can't afford the full-quadratic phase early. Kendall-tau gating [S1] directly addresses our measured screen↔verify rank breakup (finding 3): the surrogate only predicts when it agrees with truth at τ ≥ 0.85.

### Mapping to our setup

- Our evaluation is deterministic (same design hash ⇒ same J, byte-identical cache keys [repo: evaluate.py:862-874]) — the surrogate's *only* job is budget saving, so the τ-gated honesty mechanism is the right one; a noisy objective would need the noise handling we do not have measured.
- The 28k-row prior archive gives the model warm support points, **but** rows span multiple objective versions and briefs — J is not comparable across versions (repo rule; AGENTS 2026-11-12 note) — so only same-(config_sha, objective_version) rows may support the model. That constraint shrinks the usable set; check sizes before promising anything.
- Refusals interact: predicted values for designs that would be refused must be replaced by true evaluations — SurrogatePopulation's own-evaluate-at-least-one mechanism does not know about geometry gates. Feasibility must therefore ride *ahead* of the surrogate (Q1 first).

### Recommendation / sketch

- Try `fmin_lq_surr2` on **offline replay** first: it is a pycma-level driver, so a thin experiment script (outside the repo) can drive it against the cached solve-cache... — actually it needs fresh solves for unevaluated points, so an honest trial costs GPU. Cheaper first step: implement the *model check* without the optimizer — fit `cma.fitness_models.LQModel` on archived (x → J) rows of one config and measure cross-validated Kendall tau against held-out rows. If τ < 0.85 on our own data, do not ship the surrogate.
- GP-EI / TuRBO / RF-GBM: [TO-VERIFY — check Kandasamy et al. 2020 (TuRBO), Shahriari et al. Bayesian optimization tutorial (IEEE Proc. 2016)] — plausible fits for a 10–60 s deterministic black box, but ungrounded here; do not build on them this round.
- Expected gain: 2–4× evaluations if τ holds (S1 reports budget savings at roughly that order — **[TO-VERIFY — check S1 tables, GECCO 2019]** for the exact multipliers); 0 and wasted effort if the J-landscape is too non-quadratic per-brief.
- Risk: model-led search inherits the model's blind spots (Rosenbrock-like valleys, [S1]/[pycma: fitness_models.py:766]); the winner's-curse problem of §7 gets worse with predicted rankings.
- Test with our data: the LQModel offline replay above, per config family (`rosse`, `freeform_sculpt`), reporting CV-Kendall-tau and per-model-size S1-style caveats.

---

## Q3. Warm starts / transfer from the prior archive

### What the sources say

- S2 (Nomura, Watanabe, Akimoto, Ozaki, Onishi, "Warm Starting CMA-ES for Hyperparameter Optimization", AAAI 2021, arXiv:2012.06932; correction noted in the pack: the author is Nomura et al., *not* "Nomura & Shibata"): WS-CMA-ES initializes the CMA distribution — **mean AND covariance** — from past HPO results, cutting the adaptation phase; the benefit is largest under small budgets. (That "small budget" is our case: 150–1000 non-cached evals [repo: search/cma.py:310].)
- Contextual variant (S2b in pack): Sekino, Uchida, Shirakawa, PPSN 2024 (arXiv:2502.12555): GP regression over contexts → posterior initialization; our "brief" block is the context analog — but this is a second paper, treat as directional.
- pycma `inject` verified: evolution_strategy.py:3166 — `def inject(self, solutions, force=None)`, i.e. injecting concrete solutions into the sampled population; the docstring there describes forcing mean/sigma as well [pycma: evolution_strategy.py:3166 area — one short quote permitted by rules: see source].

### The math

Given prior final distributions (x̄_i, C_i, σ_i) from archived runs of the *same* brief family, WS-CMA-ES sets x0 to a weighted mean and C0 to the weighted covariance of the archived best-population samples, shrinking toward identity by λ_ws. Under a fixed evaluation budget B, adaptation of C costs O(d·popsize) evaluations before the distribution pays off (the CMA-ES covariance learning phase); warm starting skips part of it. Cross-brief safety: covariances encode knob couplings of a *particular objective version and brief*; reusing them across briefs imports couplings that may not exist (v4 vs v7 terms differ structurally [repo: scalar_v7.py:13-51]).

### Mapping to our setup

- We already archive per-run CMA dumps: `cma/covariance.json` sidecars and `restarts` entries carry keys (C_ii, std_unit, condition number, eigenvectors+loadings) [repo: search/cma.py:51-119, 490-506].
- `inject` can seed the first generation with the archived best designs (their unit-box parameters are in the ndjson `params` via `evaluation_to_row` [repo: evaluate.py:570-581]); pycma handles injection as in-distribution samples.

### Recommendation

1. Same-brief, same-objective-version warm start only: mean ← archived best point; sigma0 ← archived final σ [as recorded in restarts entries, repo: search/cma.py:490-494]; C0 ← archived C shrunk 50% toward identity (conservative); inject the top-3 archived designs into generation 1 [pycma: evolution_strategy.py:3166].
2. Cross-brief: *mean-only* warm start is defensible (a good seed is a good seed); covariance transfer across briefs is not, unless the briefs share `config_sha`-level identity. Contextual warm starting (GP over brief fields, PPSN 2024) is the right long-term shape but is not yet measured on our data: **[TO-VERIFY — check arXiv:2502.12555 §method]**.
3. Config sketch (schema only, to be validated first):

```yaml
search:
  warm_start:
    from_runs: ["<run_id>", ...]     # same brief_hash + objective_version
    mean: best                       # best | archive_sample_mean
    cov:  none | shrunk:0.5          # C-0 shrinkage factor toward identity
    inject_top_k: 3
```

- Expected gain: per S2, largest under small budgets — for us plausibly 10–30% better best-J at 150 evals (tag as expectation, not measurement).
- Risk: warm-start feedback loops (runs converging to archive modes); mitigate by keeping 1 of every N runs cold-started.
- Test: 10 fresh seeds × {cold, warm same-brief} on one brief, paired by seed; report paired differences (see §8 stats).

---

## Q4. Restarts and budget allocation

### What the sources say

- S7: restart-strategy background at tutorial level; specific IPOP-vs-BIPOP performance claims **[TO-VERIFY — check Hansen's tutorial §restarts, arXiv:1604.00772; and Auger & Hansen BIPOP paper (GECCO 2005/beyond) — not in pack → do not cite numerically]**.
- Our own mirror of pycma's schedules is verified in detail: `_RestartSchedule.plan/observe` reproduce IPOP (`popsize·2^k`) and BIPOP (small runs `popsize0·m**(U**2)`, `sigma0·0.01**U`, budget cumulation rules, with two documented divergences) [repo: search/cma.py:222-279].
- Successive halving / Hyperband: general knowledge, not in pack. **[TO-VERIFY — check Jamieson & Talwalkar (2016), arXiv:1508.04585]** if we later want budget-elastic races.

### The math of our variance

Seed variance is the dominant effect: best@150 spread 26% (rosse, 2 seeds; freeform_sculpt, 26 seeds) and 59% (v6, 2 seeds), while 42% of runs still improved >1% in the last 20% of budget (senior-measured 2026-11-12; 54/130 runs). A single long run buys *depth*; an uncertain landscape with flat runs rewards *breadth*: independent restarts sample different basins. With restarts already implemented and off, turning them on costs zero code, only config [repo: config.py:119].

### Recommendation

1. First change (config-only): `search.restarts: {mode: bipop, max: 3}` for screen-class runs. Small BIPOP restarts also re-roll `sigma0` (0.01^U), which attacks the "bound-wall optimum" failure (finding 6) by re-randomizing scale. Keep the budget semantics: restarts share the same non-cached budget, resume replays deterministically [repo: search/cma.py:16-24].
2. Do **not** chase successive halving/Hyperband before the multi-fidelity correlation study of §7 exists (it decides the ratios); treat as [TO-VERIFY].
3. Budget shape: 54/130 runs improved >1% in the last 20% (finding 5) argues budget is currently *not* the binding constraint on quality — variance is. Prefer `2 × budget at popsize/2 seeds` over `1 × budget, longer`, until the §8 power study says otherwise.
- Expected gain: high-probability improvement of median best-J (restarts are the standard remedy for basin-seeking variance); magnitude unmeasured on our data.
- Risk: BIPOP small restarts can consume the whole remaining budget (documented divergence, [repo: search/cma.py:242-247]) — monitor `restarts` entries in run.json.
- Test: same-brief A/B A=`restarts: bipop max 3` vs B=off, 10 seeds each, paired by seed; report per-restart stop reasons and best-J (§8).

---

## Q5. Quality-diversity: CMA-ME today vs CMA-MAE; ribs-0.12 specifics

### What the sources say

- S3 (CMA-MAE, GECCO 2023): cell threshold update `t_e ← (1−α)·t_e + α·f(θ′)`, accept iff `f(θ) > t_e`, improvement value `Δ = f − t_e`; α=1/−inf ≡ CMA-ME, α=0 ≡ plain CMA-ES annealing-to-elitist; density-descent property holds strictly for 0<α<1. pyribs 0.12.1 tutorial (docs.pyribs.org cma_mae): `GridArchive(learning_rate, threshold_min)` **plus a second default result archive** keeping best-per-cell; `EvolutionStrategyEmitter(ranker="imp", selection_rule="mu", restart_rule="basic")`; `Scheduler(archive, emitters, result_archive)`. Empirical: α ∈ {0.01, 0.1} best on sphere-lunar-lander style problems; α=0 stalls exploration, α=1 stalls after ~500 iters. Metrics: (normalized) QD score, archive coverage.
- ribs 0.12.0 source (verified): `GridArchive` takes `learning_rate` (default **1.0**) and `threshold_min` (default **-inf**) at _grid_archive.py:63-64, 111-112, validated at 170-171; `ImprovementRanker` class exists at rankers.py:136 and the abbreviated name `2imp` maps to `TwoStageImprovementRanker` (rankers.py:20), with `EvolutionStrategyEmitter.ranker` defaulting to `"2imp"` at _evolution_strategy_emitter.py:88; `Scheduler` accepts a `result_archive` distinct from `archive` (_scheduler.py:39 doc and 61-65, with a same-object guard at 105-108); the emitter optimizer forwards `bounds` into pycma `opts["bounds"]` (_pycma_es.py:48-61), and out-of-bounds samples are resampled up to a fixed limit with the warning "During bounds handling, this ES resampled at least …" (_evolution_strategy_base.py:12, 17).
- Our wiring: CMA-ME uses `GridArchive(...)` with **default** learning_rate/threshold_min (i.e. CMA-ME semantics), one emitter `ranker="2imp"`, bounds `[(0.0,1.0)]*k` on the emitter [repo: search/cma_me.py:137-146], descriptors fixed [0,180]° [repo: search/cma_me.py:54], failed rows reuse the seed's coordinates [repo: search/cma_me.py:304-317].

### The math, and the two fidelity bugs this exposes

CMA-MAE's threshold memory is what allows *backwards* progress to not erase better elites while still letting *forward* (new-cell) progress in. With α=1 equivalent settings (our default archive), improvement values are plain `f − t_cell`, so re-solving an occupied cell with a slightly better elite competes directly against *new* cells; with a mid α (0.01–0.1), the archive's bar for its own old cells relaxes over time [S3].

Two concrete mismatches with our data (findings 6–7):

1. **Emitter bounds distortion.** We pass emitter `bounds=[(0,1)]*k` [repo: search/cma_me.py:143] and additionally clip in `clip01` [repo: search/cma_me.py:301-302, 363-368]. ribs forwards bounds into pycma's own bounds handling, which *resamples* out-of-bounds draws (with the ≥100-times warning above). Because our archive landscape concentrates on bounds (morph_fixed 32/51, tmax 11/22; 7% of knobs within 2% of a bound — senior-measured), a large fraction of emitter samples get resampled — wasted ask-budget and distorted selection. Fix direction: for the QD path, drop the pycma-level `bounds` and keep only `clip01` (denormalize already clips [repo: search/cma.py:3-4]); the clipped sample is still evaluated and told back, which is exactly what the improvement semantics want.
2. **Refused rows borrow the seed's cell** [repo: search/cma_me.py:311-315]: with a penalty objective −J = −1000 and the *seed's* measures, a refusal burst fights the seed's real elite in its own cell — poisoning the cell it is placed in. Better: give refused rows a *fresh* cell (nearest feasible descriptor from a cheap predict) or exclude them from `tell` (ribs tolerates partial batch semantics? — **[TO-VERIFY — check ribs 0.12 `Scheduler.tell` partial-batch contract]**); minimally documented, honest option today: keep the fallback but *record it* in archive.json stats (fields exist [repo: search/cma_me.py:232-244]).

### Recommendation

- Keep CMA-ME as the default QD run; add a CMA-MAE trial: `GridArchive(learning_rate=0.1, threshold_min=0.0)` + a second plain `GridArchive` passed to the `Scheduler` as `result_archive` [S3; ribs: _scheduler.py:39] and `ranker="imp"` (ImprovementRanker, ribs: rankers.py:136) per the 0.12 CMA-MAE recipe. This is config/code work in `search/cma_me.py` — a bounded change (the constructor lines only).
- Use QD score (normalized) and archive coverage for atlas-vs-atlas comparison, and `ribs.visualize.archive_ecdf` for distributional views [S3; ribs/visualize/_archive_ecdf.py exists].
- Expected gain: better atlas Pareto-frontiers per budget and no stall-after-500-iterations pattern [S3]; on our problem, mainly better *coverage of beam-shape space* (which is the product of a QD run: finding 7's refused-design detection via seed-cell landing improves once cells are honest).
- Risk: CMA-MAE's result archive adds memory; α choice is another hyperparameter (start 0.1, S3's best).
- Test: budget-matched cma_me vs cma_mae on one brief, 3 seeds each; compare QD score, coverage, and best-J-from-archive; verify no `resampled at least …` emissions in the log (bounds fix).

---

## Q6. Objective design: weights that are not influences; a v8 recipe

### What the sources say

- Weighted normalized sums are the repo contract (see preliminaries). Chebyshev / achievement scalarizing functions as the classical alternative scalarization: **[TO-VERIFY — check Miettinen, "Nonlinear Multiobjective Optimization", Kluwer 1999, chapters on achievement scalarizing functions]** (not in the pack).
- The tolerance-normalisation rationale is the repo's own: v3's six terms differed ~300× in scale so "a weight did not mean influence" [repo: objective/scalar_v4.py:3-7].

### The math — why weight ≠ influence, numerically

Take the v4 defaults [repo: objective/terms.py:30] and a typical failure mode. Let e = per-frequency beamwidth error in degrees.

- **cov (squared, /100, tol_cov):** normalized contribution to J = `w_cov · mean(e_H²+e_V²)/100 / tol_cov`. For a *good-but-not-final* design with e ≈ 10° per plane: (100+100)/100 = 2.0 → 2.0/tol_cov. For a *far* design with e ≈ 30°: 1800/100 = 18 → 18/tol_cov. Ratio between the two: **9×** for a 3× error growth — quadratic distance-dependence.
- **rip (linear, tol_rip):** normalized = `w_rip · mean(ripple dB)/tol_rip`. A 2 dB ripple design and a 3 dB ripple design contribute 2/tol and 3/tol — ratio **1.5×** for the same 50% relative change. No distance amplification.
- **Result** (finding 2, senior-measured medians): cov share of J = **0.42**, diag 0.16, di 0.11, flat 0.11, **rip 0.01** (weight 1.0, same as cov), **load 0.00**; v6: di_rise **0.47**, load_near **0.00**. The weight vector says cov≈rip; the metric reality says cov≈42×rip. Squared terms with fixed tolerances dominate *when far* and the linear terms are noise; conversely when all designs are near target, the squared terms collapse (≈0) and the run drifts on whatever is left.
- **load/load_near ≈ 0.00 share** is the second pathology: a hinge `max(0, z_min − Re z)` [repo: terms.py:97] is *exactly zero* whenever the design is loaded, so its gradient/influence is zero almost everywhere — the optimizer literally cannot see what it is weighted for, until it hits the wall, where a graded penalty or hinge spike appears out of nowhere. Same mathematics as the J=1000 ties: terms that are ~0 or ~1000 carry no ranking information between.

### Tolerance calibration from our own data

The tolerances are per-brief and mandatory [repo: objective/scalar_v4.py:70-105], so the fix is data, not code: for each brief, compute from the (same-version, same-brief) archive rows: `tol_k = median(term_k raw) over the top-decile J rows`, i.e. "the miss size that a *good* design has". That pins each normalized term at ≈1 for a design as good as the best decile, restoring weight-proportionality *by construction*.

### Proposal: v8 settings (consistent with findings 1, 2, 3, 6)

1. **Error units.** Score `mean|e|/tol` (mean absolute) rather than `mean(e²)/100` for cov/diag/di, or equivalently divide squared terms by their RMS-consistent tolerance² and clamp. Rationale: kill distance-dependent influence; a 2× error is worth 2×, not 9×.
   - Keep v7's one-sided narrow-side ratio (it is a *weighting* policy, ortho­gonal to units) [repo: scalar_v7.py:437-439].
2. **Clamp the worst case.** `term_norm_k = min(raw_k/tol_k, CAP_K)` with CAP_K ≈ 5. Prevents one unscoreable frequency (or an outlier lobe) from reproducing the flat-1000 plateau *inside* an otherwise valid design; keeps the penalty-ordering invariant (worst_valid_j ≪ PENALTY_INVALID, [repo: scalar_v4.py:140-146]).
3. **Tolerances from the archive**, not hand-guesses (top-decile median recipe above; v6 already ships "physical-ish starting tolerances" — upgrade them with measured deciles, [repo: scalar_v6.py:49-59]).
4. **Lexicographic gates for refusals**, replacing part of the penalty ladder: feasibility is *rank 0* (refuse ⇒ out, graded overshoot points back [repo: terms.py:104-115]); J ranks only within rank 0. Cheaper than making a mega-penalty "work".
5. **Keep the flat/rip terms linear** (they already are [repo: terms.py:82-98]) — the asymmetry is in the squared terms, not these.
6. **When is MO worth it?** When two finalist sets differ by *which term* they excel in (median pairwise term-J Spearman across their top-20 < ~0.2, computed from archived rows). The repository already has `search/nsga.py` (exists — behavior not verified here); NSGA-II/Pareto fronts are a larger change: justify with the correlation check first, and never rank J across objective versions (repo rule).

- Expected gain: finding-2 disappears (shares track weights); screen/verify disagreement partly improves too, since the current J's distance-quadratic component is exactly the part a coarse grid most distorts (finding 3). No honest number without the replay below.
- Risk: every recalibration changes stored-J semantics — a run.json/brief must never silently mix v8 and v4 numbers; version the objective.
- Test with our data: pure offline re-scoring. Archived rows carry full `terms` dicts and configs [repo: evaluate.py:570-581]; recompute shares and top-20 Spearman(screen, verify-recompute) under candidate v8 formulas on all 34k rows, pick the variant that (a) equalizes shares to within ~2× of weights and (b) maximizes screen→verify rank preservation — no solves needed.

---

## Q7. Multi-fidelity, winner's curse, and the screen→verify ladder

### What the sources say

- S4 (IOHprofiler, Applied Soft Computing 88, 2020): ECDF-of-fixed-target running-time aggregation as the standard practice for comparing optimizers; S4b (IOHprofiler 2018): fixed-target runtime distributions and fixed-budget values (ERT practice built on COCO). Both are *reporting* formalisms; neither directly quantifies selection bias, so any claim that "winner's curse" behaves like X under a coarse screen beyond what is below needs a reference: **[TO-VERIFY — check the model-selection-optimization-bias literature, e.g. Jensen & Cohen "Multiple Comparisons in Optimization Benchmarks" (JEMR/real-world?) — exact cite unconfirmed]**.
- Grounded observation instead: S1's τ ≥ 0.85 gate is precisely a rank-correlation honesty check between surrogate (≈cheap view) and truth — the same construct we need between screen and verify.

### The math of winner's curse on our grid

Screen J (12 log-sp points, 500 Hz–10 kHz [repo: config.py:27-31]) differs from verify J by (a) 2× frequency resolution, (b) HF density starting at 5 kHz on verify [repo: config.py:46-47], (c) different dof caps. Screen-selecting the top-k of N designs estimates `E[J_screen | selected]` biased low; its rank correlation with verify is exactly what failed: verify worse than screen in 95% of 104 pairs (+25–50% typical), within-run Spearman top-5 ≈ 0.1–0.3 (senior-measured, finding 3). A selection with ρ ≈ 0.2 on the top-5 has essentially no information content; ranking by verify-J only is not conservatism, it is statistics.

### Mapping: the aliasing question

Finding: "frequency-grid density vs narrow-beam aliasing" — a 12-point grid spacing Δf/f ≈ 2^(log2(10000/500)/11) ≈ 1.26 (about a quarter-octave). A beamwidth response with structure at the scale of < 2 grid steps (e.g. a notch at 4–5 kHz, driver-mode related) is aliased: screen and verify can disagree *by construction* on such designs. The `screen_extra_hz` mid-band points (2573/3311/4260 Hz) already exist precisely for this [repo: config.py:367-371] — they should be default-on for any brief whose J is sensitive in 2.5–5.5 kHz (presence band; v4 docstring notes that emphasis is the brief's freq_weights [repo: scalar_v4.py:32-33]).

### Recommendation

1. **Finalists:** verify top **15–20** screen designs, rank by verify J only (senior recommendation, confirmed by the ρ numbers). Below 15, winner's curse dominates; above 20, verify cost is wasted because top-20 ranking between positions 20–40 is indistinguishable.
2. **Screen enrichment:** turn on `screen_extra_hz` mid-band points for affected briefs (config-only).
3. **Rank-correlation hygiene:** every campaign reports per-run `spearman(J_screen, J_verify)` on the verified set; a campaign whose ρ < 0.3 has a *fidelity* problem, not a finalist-count problem.
4. **Not yet:** screen→verify successive halving with ratios from theory — **[TO-VERIFY — check Jamieson & Talwalkar 2016 / Li et al. Hyperband 2017]** before scheduling.
- Expected gain: finalists that actually win at final — the only measured number is that current screen top-5 ordering carries ~no information (ρ 0.1–0.3).
- Risk: verify cost grows ~15–20 designs per campaign; bounded.
- Test: replay archived campaigns, compute ρ(screen, verify) with/without extra screen points from the recorded metric arrays.

---

## Q8. Comparison statistics: how many runs is an answer?

### What the sources say

- S4/S4b: ECDF of fixed-target running times, ERT, and fixed-budget values are the COCO/IOHprofiler-standard views for optimizer comparison.
- No power-analysis content is in the pack; the computation below is ours, analytic and marked `[measured]` for its arithmetic.

### The math (script `study_2026-11-12/research/power_calc.py`, run 2026-11-12, two-sided α=0.05, power 0.80, equal-n two-sample, normal-approximation `n = 2·(z_{α/2}+z_{power})²·(σ/Δ)²`)

```
z_(alpha/2)=1.9600, z_(power)=0.8416; n = 2*(za+zb)^2*(sd/delta)^2
  spread=0.26 delta=0.05: n=     424 per group (effect size d=0.192)
  spread=0.26 delta=0.10: n=     106 per group (effect size d=0.385)
  spread=0.26 delta=0.20: n=      27 per group (effect size d=0.769)
  spread=0.59 delta=0.05: n=    2186 per group (effect size d=0.085)
  spread=0.59 delta=0.10: n=     546 per group (effect size d=0.169)
  spread=0.59 delta=0.20: n=     137 per group (effect size d=0.339)
```

Reading: with our 26% seed spread, a claimed 10% improvement between two configs is undetectable at n<~106/group. **Most of our past "A beat B" comparisons at n≈2–10 were noise.** The 26-seed freeform_sculpt group is the only sample where per-group t-tests are even marginal (detectable Δ ≈ 20%).

### Recommendation

1. **Paired designs always:** same seed list on both sides; report paired differences, not group means. Pairing removes the between-seed variance component from σ (the paired-σ is typically much smaller; measure it once on the 26-seed group).
2. **Bootstrap CIs on the paired median difference** (10k resamples) as the standard report artifact, plus `scipy.stats.mannwhitneyu` for unpaired distributions (scipy 1.18.1 installed — verified at import).
3. **Report in IOH style** (S4/S4b): fixed-budget best-J ECDF across seeds per config, rather than single best-J medians.
4. Number of runs: decide the claim first (Δ=10% ⇒ ~106/group unpaired, or far fewer paired — compute paired σ once), not the other way round.
- Expected gain: honest conclusions; likely reversal of some past config preferences.
- Risk: none beyond compute for paired runs.
- Test: rerun the last campaign's A/B with the 26-seed protocol on one brief.

---

## Q9. Sensitivity, coupling, and turning findings into `links:`/pins

### What the sources say

- S5 (SALib docs): given-data (model-free) sensitivity methods exist — **Delta Moment-Independent** (Borgonovo 2007; Plischke et al. 2013) and **RBD-FAST** (Tarantola et al. 2006; Plischke 2012; Tissot et al. 2012) — both compute indices from pre-existing X/Y samples without a resampling design. Sobol/Morris/FAST in SALib need structured sampling; PAWN/Shapley exist too. **SALib is NOT installed in this repo** (verified: import check; pack S5) — adding it needs owner approval.
- CMA covariance eigen-analysis: implemented and dumped per run — `covariance_summary` writes `C_ii`, `std_unit`, shares, condition number, and top eigenvector loadings per restart into run.json/covariance.json [repo: search/cma.py:51-119, 490-506]; the docstring is explicit that eigenvectors are "coupled search directions for J, not acoustic Sobol indices" [repo: search/cma.py:113-115].
- Spearman-on-optimizer-samples bias: correlations computed on *optimizer-sampled* X overstate sensitivity in explored regions and hide it elsewhere; the honest given-data methods (Delta/RBD-FAST) correct for design density [S5 description].
- Surrogate-based Sobol / SHAP on a trained RF/GBM: used elsewhere, but we have no grounded reference in the pack: **[TO-VERIFY — check e.g. Fisher et al. SHAP overview or an SA-on-surrogate primary source]**.
- Active subspaces (Constantine et al.): direction set from ∇f covariance — not in the pack; **[TO-VERIFY — check Constantine, "Active Subspaces", SIAM 2015]**.

### The math and mapping

- The C eigenvectors [repo: search/cma.py:91-103] give exactly a `links:`-shaped hypothesis: a direction `v` with large eigenvalue whose top-2 loadings (a, b on knobs `knob_a`, `knob_b`) says the landscape varies fastest along `knob_b ≈ knob_a·(v_b/v_a) + const` (in unit-box coords; denormalize per-key to physical units). Turn each candidate into an explicit repo `links:` entry only after an *independent* check: resample J along the direction from archived rows (quadratic fit through cache hits), or pin `knob_a` and confirm the optimum tracks the link.
- Spearman ranks over optimizer samples are fine for *ranking knobs within the explored region* (they answered finding 2's share question), but Delta/RBD-FAST would give density-corrected indices on exactly our X,Y archives.
- Sobol *total-order* indices from given data (RBD-FAST) then directly answer "which knobs does the optimum not care about" → pin candidates.
- Expected gain: principled pin/link list per brief; likely 2–4 actionable links per family from the existing covariance.json dumps.
- Risk: given-data indices are estimators with sampling noise — report CIs.
- Test: offline script over dataset store records for one config: rank correlations vs RBD-FAST vs covariance-eigenvector loadings; check consistency across versions.
- Dependency call: **defer SALib** until this offline comparison shows the rank/eigen toolkit misses something (ownership/approval per [S5]).

---

## Q10. Anything else for better horns per solve

- **dof-adaptive fidelity** (mesh budget scales with candidate promise): our per-mode dof caps are fixed in config [repo: config.py:59-71]; a screen-stage candidate does not need final-stage dofs. Careful: solve hash includes the mesh spec — lower-dof screens create *different cache keys*, which is correct (no cross-fidelity cache pollution) but means "screen cheap, verify honest" duplicates mesh work; the band-split policy exists as a different lever [repo: evaluate.py:76-77, 763-790].
- **Early stopping of bad candidates mid-sweep:** the solver-unhealthy streak guard [repo: search/cma.py:121-126] protects the *solver*; a *candidate*-level early stop (abort solve when pre-mesh envelope/dof estimate exceeds caps) is exactly the WP3 graded path [repo: evaluate.py:1001-1015] — recommend default-on rather than opt-in after the Q1 resampling change.
- **Batch/parallel CMA over two lanes:** the two-lane CPU/GPU hygiene regime is established (AGENTS 2026-11-12; lane identity via `HORNLAB_BEAT_WORKER_DIR`, ndjson rows carry `lane`/`backend` provenance [repo: evaluate.py:518-534, 592-598]). Two *independent seeds* (not one split CMA) should run one-per-lane: the paired-seed protocol of §8 needs exactly this kind of pairing, and each lane keeps its own worker registry. Do not attempt population-parallel CMA (`popsize` split across lanes) before measuring — it changes pycma's serial RNG stream and breaks deterministic resume [repo: search/cma.py:237-241].
- **Replay/cache exploitation:** budget already excludes cache hits [repo: search/cma.py:6-14]; the *failure* markers cache deterministic refusals across runs [repo: evaluate.py:1018-1023]. Missing piece: a cross-run *seed* cache — when starting run B, run A's ndjson rows for identical (design,mesh,solve) keys are already shared via the solve cache, but the CMA **initial population could be seeded from A's archive top-K** (see Q3) at zero solve cost.
- **J=1000 tie handling:** scoring failed candidates with the exact same 1000 makes rank-based selection treat them as ties (finding 1's 9.8% of generations ≥50% ties); a tiny deterministic jitter (e.g. `1000 + 1e-6·hash(design_hash) % 1`) would restore ranking without pretending refusals are informative — a one-line change, worth an A/B.

---

## Ranked table: change → expected gain → cost → verification on our data

| # | Change (all within existing contracts) | Expected gain | Cost | Verify on our data |
|---|---|---|---|---|
| 1 | Verify top 15–20 screen finalists; rank by verify J only (§7) | Stops picking losers; fixes the 95%-of-pairs regression | Just verify compute | ρ(screen, verify) tracked per campaign [finding 3] |
| 2 | `search.restarts: {mode: bipop, max: 3}` default for screen runs (§4) | Attacks 26–59% seed spread; zero code | Config only + reruns | Paired-seed A/B (§8), per-restart best-J in run.json `restarts` [repo: search/cma.py:490-506] |
| 3 | Q1 feasibility resampling (`is_feasible` + resample budget) + graded-penalty default-on (§1) | ~10% more real evals; no flat-run stops | Small search/cma.py option plumbing | Refusal share & ≥50%-tie generations per run [finding 1] |
| 4 | QD path: drop pycma bounds, keep clip01; CMA-MAE trial (lr=0.1, threshold_min=0, result_archive, ranker="imp") (§5) | Better atlas coverage; kills resample distortion | Bounded cma_me.py change | No ≥100-times resample warnings; QD score/coverage vs cma_me [S3] |
| 5 | v8 objective: |e|/tol units + clamped terms + archive-calibrated tolerances (§6) | Weights ≈ influences (cov 0.42→~w); stops rip/load invisibility | Offline re-score of 34k rows; shares + top-20 Spearman replay |
| 6 | Warm start same-brief (mean/σ/C0-shrunk + inject top-3) (§3) | 10–30% best-J at small budgets (S2-flavored expectation) | New optional block + replay harness | Paired-seed A/B cold vs warm, §8 protocol |
| 7 | `screen_extra_hz` mid-band default for 2.5–5.5 kHz-sensitive briefs (§7) | Removes 4–5 kHz aliasing from ranking | Config | ρ(screen, verify) with/without [repo: config.py:367-371] |
| 8 | J-tie jitter for failed rows (§10) | Restores selection signal in refusal-heavy generations | One line + A/B | Tie-share metric per generation |
| 9 | Paired-seed statistics + IOH-style ECDF reporting (§8) | Honest A/B claims; reveals required n | Reporting scripts in tools/ | Power table above [measured] |
| 10 | Refusal-aware CMA-ME tells (stop borrowing seed cell) (§5) | Un-poisons the seed's cell | Small cma_me.py change | archive.json stats + cell-objective audit |
| 11 | lq-CMA-ES only after offline LQModel τ test passes (§2) | 2–4× budget saving *if* τ≥0.85 | Replay script first | CV-Kendall-tau per config [S1] |
| 12 | SALib Delta/RBD-FAST sensitivity (§9) | Density-corrected knob ranking | New dependency (owner approval) [S5] | Offline on 28k-row archive |

---

## Measured-by-this-lane (scripts, all in `C:\Users\hunte\Hrns\study_2026-11-12\research\`, venv python, READ-ONLY on the main checkout)

1. `spotcheck_findings.py` — refusal-kind share over all 415 `runs/*/search.ndjson` (34 475 rows): failures 13.8%: invalid_geometry 9.1%, mesh_too_large 2.6%, invalid_envelope 1.7%, solve_failed 0.2%, exception 0.2%. [measured 2026-11-12; consistent with, and slightly below, the senior-measured 16% / 10.8 / 3.0 / 2.0 — scope of runs differs; both retained.]
2. `power_calc.py` — §8 sample-size table above. [measured 2026-11-12; arithmetic only, no repo data.]

All other numeric findings remain **senior-measured 2026-11-12** as delivered in the lane handoff.

## Source pack (as verified and cited)

- [S1] Hansen, N., "A Global Surrogate Model for CMA-ES", GECCO 2019, ACM (lq-CMA-ES; mechanics also documented in pycma `cma/fitness_models.py` header).
- [S2] Nomura, Watanabe, Akimoto, Ozaki, Onishi, "Warm Starting CMA-ES for Hyperparameter Optimization", AAAI 2021, https://arxiv.org/abs/2012.06932 (correction: Nomura et al., not "Nomura & Shibata"). [S2b] Sekino, Uchida, Shirakawa, "Warm Starting of CMA-ES for Contextual Optimization Problems", PPSN 2024, https://arxiv.org/abs/2502.12555.
- [S3] Fontaine & Nikolaidis, "Covariance Matrix Adaptation MAP-Annealing (CMA-MAE)", GECCO 2023, https://arxiv.org/abs/2205.10752; pyribs v0.12.1 tutorial: docs.pyribs.org/en/stable/tutorials/cma_mae.html.
- [S4] Doerr, Ye, Horesh, Wang, Shir, Bäck, "Benchmarking Discrete Optimization Heuristics with IOHprofiler", Applied Soft Computing 88 (2020), https://arxiv.org/abs/1912.09237. [S4b] Doerr, Wang, Ye, van Rijn, Bäck, "IOHprofiler", 2018, https://arxiv.org/abs/1810.05281.
- [S5] SALib docs, https://salib.readthedocs.io/en/latest/ (Delta Moment-Independent — Borgonovo 2007, Plischke et al. 2013; RBD-FAST — Tarantola et al. 2006, Plischke 2012, Tissot et al. 2012; structured-sampling methods).
- [S6] pycma 4.5.0 installed source — paths and lines cited inline; all verified by this lane.
- [S7] Hansen, "The CMA Evolution Strategy: A Tutorial", https://arxiv.org/abs/1604.00772 (2016/2023).

## Repo file:line spot-check results (all verified this lane, main tip 2ecbc69)

- `hornlab_search/search/cma.py`: 3-4 (clip in denormalize), 6-10 (budget), 16-21 (restarts doc), 48, 51-119 (covariance_summary), 121-126 (solver-health streak), 222-279 (BIPOP/IPOP schedule), 296-303 (cma_me dispatch), 316-321 (es_options), 404-409 (seed first), 414-453 (sweep/tell rules), 464-516 (restart loop), 490-506 (restart log fields).
- `hornlab_search/search/cma_me.py`: 20-28 (ribs 0.12.0 usage), 54, 59, 116-118, 137-146 (archive+emitter, bounds), 192-245 (archive payload), 301-302 (clip01), 304-317 (tell_batch fallback), 319-331 (seed add), 378-380 (finish).
- `hornlab_search/search/evaluate.py`: 11-19 (cache semantics), 65-74 (kinds), 76-77, 262-279 (envelope), 407-408 (load threshold), 518-534 (lane identity), 570-581 (row schema), 592-598 (lane fields), 763-790 (band split), 1001-1015 (graded penalty), 1018-1023 (failure markers).
- `hornlab_search/config.py`: 27-31 (freq grids), 35-42, 46-47, 55-71 (mesh caps), 110-121 (SearchSettings), 138, 141, 344-358/367-371 (screen_extra), 727-748 (restarts validation), 751-784 (qd validation).
- `hornlab_search/objective/terms.py`: 16-19, 22-35, 49-98 (raw terms), 101-115 (graded penalty).
- `hornlab_search/objective/scalar_v4.py`: 1-13, 58-62, 140-146, 165-195, 226-265. `scalar_v6.py`: 34-59, 201-226, 241-271, 323-328. `scalar_v7.py`: 34-43, 78-94, 214-239, 289-326, 332-354, 360-383, 386-446, 449-465.
- pycma 4.5.0 (`.venv/Lib/site-packages/cma/`): `__init__.py:131,137`; `evolution_strategy.py:2139 (ask_and_eval), 2539, 3166 (inject), 3426-3429 (augmented Lagrangian in tell), 4417 (fmin_lq_surr2), 5496 (fmin_con2)`; `options_parameters.py:197 (is_feasible)`; `boundary_handler.py:454 (BoundTransform)`; `fitness_models.py:81-94 (SurrogatePopulation, tau 0.85), 307, 371-381 (LQModel, max_weight 20), 398, 538-540 (sorted_weights), 766 (Rosenbrock caveat), 943`.
- ribs 0.12.0 (`.venv/Lib/site-packages/ribs/`): `archives/_grid_archive.py:63-64, 111-112, 170-171 (learning_rate=1.0, threshold_min=-inf)`; `emitters/rankers.py:20 ("2imp" → TwoStageImprovementRanker), 136 (ImprovementRanker)`; `emitters/_evolution_strategy_emitter.py:88 (default ranker "2imp")`; `schedulers/_scheduler.py:39, 61-65, 105-108 (result_archive)`; `emitters/opt/_pycma_es.py:48-61 (bounds → opts)`; `emitters/opt/_evolution_strategy_base.py:12, 17 (resample limit + warning)`; `visualize/_archive_ecdf.py` (exists).

**[TO-VERIFY] index (16):** §1 truncated-selection bias (S7 §); §1 fmin_con2 use contract for our purposes (pycma docstring depth); §2 GP-EI/TuRBO/RF-GBM primary refs; §2 S1 budget-saving multiplier from paper tables; §2 S1 model-size setting syntax in options (`model_size` — check fitness_models docs); §3 PPSN 2024 method details (arXiv:2502.12555 §method); §3 `inject` semantics beyond docstring (forced mean/sigma mechanics); §4 IPOP/BIPOP relative performance claims (tutorial §restarts; Auger & Hansen); §4 successive halving/Hyperband (arXiv:1508.04585 / Hyperband paper); §5 ribs `Scheduler.tell` partial-batch contract; §6 Miettinen achievement scalarizing (Kluwer 1999); §7 winner's-curse benchmark-bias reference; §7 Hyperband ratios; §9 SHAP-on-surrogate reference; §9 Active Subspaces (Constantine, SIAM 2015); §10 population-parallel CMA determinism claim (pycma RNG stream docs).
