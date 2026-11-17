## v3 required architectural decision: adaptive search-policy supervision

In addition to the geometry/scoring/size architecture, **make an explicit go / defer / reject decision** on the owner's potential intelligent watchdog and scheduling supervisor. The possible reward is better *verified discoveries and reusable acoustic information per actual GPU-hour*; the hazards are wrong early stopping, biased BO-vs-CMA comparisons, hidden changes of objectives/bounds/cohorts, GPU contention, misleading hard-limit pinning, and excess orchestration complexity. Compare at least a minimal hardened-watchdog baseline, a read-only/shadow adviser, a controlled between-job controller, and a more formal cost-aware algorithm portfolio/experiment-design alternative. **Do not merely choose a fashionable method.** Your design may conclude it should not be built yet.

If a supervisor is justified, specify: observations (run events, refusal taxonomy, hard-versus-soft geometry limits, elapsed and physical solve time, BO cohort readiness, raw acoustic/QD progress, uncertainty); competing action candidates; policy/reward and calibration; failure-state and missing-data handling; who can approve or enact which changes; how it interacts with *existing* runner and TuRBO/CMA internals; new immutable config/study ID on any bound/brief/optimizer change; what data are reusable; safe paused-run handoff; serialization and atomic queue write; dry-run/replay and rollback. No autonomous change of source/score/hard constraints or GPU budget. Define a minimal **offline historical replay plus prospective shadow test**, falsification criterion, and fair matched-control comparison before recommending auto-actuation.

The first pass may find that shape/source/scoring invalidity is a more important blocker than policy automation, in which case say so and rank the supervisor lower. Read `09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md` and `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md`. Add supervisory tickets only if justified by your choice; do not let them distract from the fundamental discovery architecture.

# PASTE INTO FABLE: FINAL ARCHITECTURE AND IMPLEMENTATION DECISION

You have completed Hornfab's broad architectural discovery pass (`scratch/fable_architecture/FABLE_DISCOVERY.md`). If you requested targeted evidence, read `TARGETED_FINDINGS.md` and verify decisive original sources. If there was no additional evidence pass, proceed using the sources already reviewed. The current checkout, not a previous web snapshot, is authoritative.

**Decide.** Do not keep postponing decisions under the pretext of more research. Choose an architecture that best improves horn discovery, search validity, acoustic realism and efficient use of measured data. Preserve uncertainty honestly and prefer a reversible experiment when the evidence cannot yet justify a large refactor.

## Requested deliverables

### 1. Decision memo

- A clear **recommended direction**, the leading alternatives and why they lost, including a serious *minimal change* baseline.
- Which problem should be addressed first, and which seemingly attractive ideas are lower leverage right now.
- Which existing parts of Hornfab should remain intact, which need adapters or surgical correction, which are candidates for redesign, and which experimental features are genuinely unnecessary.
- A list of assumptions that would cause you to reverse this choice, plus the evidence/test that would reveal them.

### 2. Scientific and mathematical specification

Specify only the mathematics needed for the chosen approach, without preserving accidental old limits:

- How shape parameters or compositional choices map to a canonical, reproducible acoustic surface; where physical feasibility, smoothness/joins, symmetry and source conditions are checked; and how non-star-shaped/rolled/multiple-entry shapes are treated rather than forced into the wrong representation.
- What is independent, derived, categorical, conditional, coupled, or inactive, and how those relationships are encoded without opaque clipping, false degrees of freedom or unbounded dimension inflation.
- Feasibility taxonomy and whether search can model/use *distance from* constraint violation, *probability of feasible geometry*, or simple rejection. Invalid designs must not become synthetic successful acoustic data.
- Whether a staged **acoustic-discovery vs product-feasibility** separation is advisable. If so, define where size is hard, soft, diagnostic-only, a user-preference filter or a Pareto/QD descriptor; how envelope checks remain correct for asymmetric/oblique surfaces; which current code paths and BO adapters need changes; how true acoustic scores for legitimate oversized designs differ from geometry-refusal observations. If **not** advisable, explain why. Do not modify the current home brief in place or assume exploratory size values from the supplied proposal are approved.
- What **flexible briefs** should mean mathematically: target bands, frequency-dependent tolerances, weighted preferences, physical hard constraints, robust/worst-case criteria, multiobjective/QD archives, and/or human choice. Distinguish H/V coverage, pattern smoothness, lobes, high-frequency narrowing, DI behavior, loading, source realism and DSP. Propose meaningful metrics, validation and avoidance of gaming, not an unjustified score revision.
- How CMA-ES, CMA-ME/quality diversity, scalar/TuRBO/Pareto BO, mixed-variable optimizers, multi-fidelity/active learning or alternative methods would interact. Do not assume all are needed. Show data requirements and budget accounting.
- Exactly when a **physical solve** can be reused, when a **derived metric** can be recomputed, when **a new score** can be produced, and when an incompatible or missing physical response requires a fresh solve. Respect `physical_solve_id`, `analysis_id`, `score_id` and `study_id` or specify a compatible improved contract.
- Explicit interface choices: module APIs, configuration shape, versioning/migration, sampled-surface identity and historical compatibility. Distinguish a conceptual interface from an existing implementation.

### 3. Minimum discriminating prototype

Treat a **resource-bounded, optional over-envelope test** as one possible discriminating experiment, not a required extra GPU study. First determine whether existing response data and cheap, full-surface geometry measurements can settle the relevant question. If new solves could actually change the architecture decision, propose authorization gates and cost limits rather than launching them.

Design **one or two small tests that could prove the architecture worth adopting or kill it early**. Favor saved acoustic responses and CPU-only surface generation before consuming the RTX 4060's GPU. Examples, only if appropriate: near-equivalence of two named typologies mapped into one representation; reduction of invalid geometry without narrowing attainable surfaces; an offline ranking/coverage-region comparison; hierarchical family search against separate-family baselines. Include controls, cold starts, repeatability, saved-data eligibility, clear failure criteria, and actual runtime/resource accounting. No GPU job is authorized by this document.

### 4. Implementation and verification map

Provide **small, sequentially testable tickets** with (a) purpose, (b) files/interfaces, (c) input/output contract, (d) objective acceptance test, (e) regression risks, (f) dependency and (g) whether cheap agents can implement or Fable should personally derive/review it. Leave scientific design alternatives open where your evidence is insufficient. Limit simultaneous file edits and preserve owner/integrator rules.

Produce these files in the research notes location (not tracked code unless the owner authorizes integration):

```
FABLE_DECISION.md
FABLE_MATH_AND_INTERFACES.md
FABLE_MINIMUM_EXPERIMENT.md
FABLE_IMPLEMENTATION_TICKETS.md
FABLE_RISK_AND_FALSIFICATION.md
```

## Review standard

You must **adversarially challenge your chosen solution**. State a plausible cheaper design that might outperform it. Provide one-page executive rationale for the non-technical owner, then enough precision for implementation. Do not bury hard numerical claims in vague architectural prose. Do not hallucinate tests, papers, measurements or implementation status. You may do original derivation yourself where it is the highest-value use of your capability; do not mechanically delegate your core reasoning.

Do not automatically launch production code changes. Follow the repo's active-work protections, published-horn source verification, pinned-fork policy and independent physics validation. If a novel approach changes foundational contracts or physical assumptions, identify the required owner decisions explicitly.
