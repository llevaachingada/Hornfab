# OPEN QUESTIONS — sorted by whether the answer could change the architecture

A question is listed only if a different answer changes a decision. "Cheap" means existing
artifacts or CPU-only; "expensive" means new BEM solves. Every test below is **proposed, not
run**. Snapshot: `main` @ `601be8c`, 2026-11-16T20:43-05:00.

## Tier 1 — answers that could change the architecture

### Q1. Does the conservative generic-GRID extent estimate actually cause false refusals?
- **Why it matters:** the estimate is code-confirmed conservative (E-018), and a positive estimate
  is a hard pre-mesh refusal. If it refuses shapes the mesher would fit, the cheapest high-value
  fix is the estimator, not a new geometry architecture.
- **What changes:** if yes → fix the estimator and re-measure refusal rates before touching the
  600 mm envelope; if no → the envelope is binding for real and size becomes an owner decision
  (Q2).
- **Cheap test (CPU, no BEM):** for N asymmetric grid knob vectors near the box, compare
  `grid.envelope_extents` to the actual `build_mesh` bbox and `evaluate.envelope_violation`;
  count `pre_mesh_refused AND post_mesh_admitted`. Exact procedure in
  `SIZE_FEASIBILITY_EVIDENCE.md` §7.
- **Current evidence:** code conservatism verified; realised effect unknown.

### Q2. Is the owner's acoustic intent a point (80×50) or a region (60–90 H / 40–60 V)?
- **Why it matters:** v7 scores a frequency-flat point target while the brief's own comment calls
  80/50 the centre of a range (E-037). This is upstream of every optimizer choice: an optimizer
  cannot fix a goal-shape mismatch.
- **What changes:** a region/corridor objective (v9-like) vs the current point objective; whether
  off-centre-but-acceptable designs should stop being penalised quadratically.
- **Cheap test:** none can settle intent; requires owner preference statements or pairwise
  choices among in-band designs. The technical part (what a corridor scores) is testable offline
  on stored responses.
- **Current evidence:** the owner/lane is already implementing `objective/scalar_v9.py` with
  frequency-dependent corridors (E-046), but it is uncommitted and currently unimportable.
  This makes Q2 urgent: the architecture should be compared against v9, not against a
  hypothetical.

### Q3. Is screen J a valid proxy for verify/acoustic ranking, especially near the top?
- **Why it matters:** every "stall", "no gain" and "switch" rule acts on screen J. If screen and
  verify rankings diverge in the top quartile, the supervisor is switching on noise.
- **What changes:** whether any screen-J-based adaptive policy is admissible at all; whether the
  next spend is verification rather than more search.
- **Cheap test (zero GPU):** on the 42 existing screen/verify pairs in
  `docs/status/2026-11-15-bo-vs-cma/data.json`, compute Spearman/Kendall overall and top-quartile,
  per arm. Predeclare failure at top-quartile ρ < 0.5 or a sign flip in the best-3.
- **Current evidence:** historical median screen-vs-verify drift +3.4 % (BO) and +9.4 % (CMA),
  worst 13.8 %/18.4 %; rank correlation not computed here.

### Q4. Is the score stable under the documented rerank, or does the incumbent change?
- **Why it matters:** the single v7→DSP rerank moved the #1 design to #12 (E-042). If that is
  typical, optimizing v7 is optimizing a ranking artefact.
- **What changes:** whether v7 (or v9) is trustworthy enough to be the search objective; whether
  the next spend is a scoring audit rather than geometry or optimizer work.
- **Cheap test (zero GPU):** rescore all stored responses of one landscape cohort under v7, v9
  (when importable) and `hifi_rescore`, and compare top-quartile ordering, not absolute J.
- **Current evidence:** one run, 32 designs; not a universal result either way.

### Q5. Does a shared geometry representation buy more than fixing validity and data reuse?
- **Why it matters:** the four/five candidate architectures differ in cost by a lot. A grammar or
  a shared freeform surface is a large build; fixing the envelope classifier, the conservative
  extent estimate, `search.links` for generators and the cohort gates is small.
- **What changes:** route selection (minimal unification vs grammar vs shared body vs QD-first).
- **Cheap test:** none conclusive; a bounded prototype on one difficult class (rollback +
  asymmetric + source mount) would show whether the shared representation preserves the meshed
  surface and the published-family provenance. This is a design experiment, not a benchmark.
- **Current evidence:** E-004–E-012 show the modularity ceiling; E-018/E-016 show cheap fixes
  with measurable effects. No evidence that a shared representation would repay its cost.

### Q6. Should product size be hard, soft, report-only, or multi-objective during discovery?
- **Why it matters:** the current brief enforces 600×480×480 before and after meshing; oversize
  designs get no acoustic data (E-015, E-019). An exploratory size study could produce new
  parents, or could spend GPU proving large horns behave differently.
- **What changes:** whether to run a versioned oversize campaign, and at what compute ceiling;
  whether size becomes a Pareto/report-only descriptor.
- **Cheap test:** classify existing refusals by overshoot band (already partly done: 38/120 ≤5 %
  in one QD run) and estimate DOF/cost for a proposed larger box with `sizing.f_max_for_dofs`.
  No GPU.
- **Current evidence:** conservative estimate unmeasured (Q1); no acoustic data for any oversize
  design; owner has kept the 600 mm envelope. **A separate oversize study is not justified by
  evidence yet.**
- **Note:** if ever run, re-optimize at the HF1440 throat rather than geometric-similarity
  scaling, and keep product feasibility as a separate final filter.

### Q7. Are geometry refusals a learnable margin or a binary pre-solve event?
- **Why it matters:** constrained BO and feasibility-aware acquisition need a signed value at
  infeasible points; a binary refusal gives a classifier at best and no gradient.
- **What changes:** feasibility-GP/constrained BO (likely rejected) vs cheap envelope filter and
  box repair (likely preferred).
- **Cheap test (zero GPU):** compute cheap envelope/throat diagnostics for historical accepted and
  refused designs, fit a simple classifier, report AUC/calibration.
- **Current evidence:** refusals carry text reasons but no margin; the pool already performs a
  binary pre-check (`bo/data.py:1219-1236`).

### Q8. Is a 100–231-row GP good enough to rank held-out designs at d = 6–14?
- **Why it matters:** the 100-row floor is a spend heuristic. If held-out ranking is poor, more BO
  arms are the wrong next spend.
- **What changes:** whether to invest in BO cohorts or in data-building CMA/QD runs.
- **Cheap test (zero GPU):** time-blocked or leave-one-arm-out validation with the locked model on
  the 185-row prior, the 231-row cov cohort and the 60-row arms.
- **Current evidence:** replay refit rank correlation 0.68–0.83 per arm, median absolute error
  0.2–0.4 J near the best, but very wide intervals; not a held-out ranking test.

### Q9. Is quality-diversity worth 60–200 solves at the current descriptors?
- **Why it matters:** QD can produce a valuable repertoire while scalar J is flat (E-056), but
  10/324 cells after 200 solves is a sparse deliverable and the descriptors are achieved
  beamwidth, not goal distance.
- **What changes:** whether a QD-first architecture is worth building; whether the watchdog must
  become archive-aware.
- **Cheap test:** re-analyse existing QD archives: cell occupancy per solve, descriptor spread,
  whether any archived elite survives a verify check (the latter needs solves). Also test
  alternative descriptors offline from stored responses.
- **Current evidence:** 3.1 % archive coverage; no evidence that archived elites are acoustically
  good or owner-preferred.

### Q10. Does mixed screen/verify fidelity preserve ranking enough to pool?
- **Why it matters:** the native BO builder allows mixed fidelity by default; study prep refuses
  it. If ranks move, a mixed cohort needs a fidelity term or must be split.
- **What changes:** the training-set policy for BO; the value of cheap screen rows as prior data.
- **Cheap test (zero GPU):** reuse Q3's screen/verify pairs; compare top-k ordering by design and
  admit mixed cohorts only if stability exceeds the measured drift.
- **Current evidence:** drift numbers exist; rank stability not computed.

## Tier 2 — cheap tests a low-cost agent can run next (in priority order)

| # | Test | Data | Cost | Decision affected |
|---|---|---|---|---|
| T1 | Screen-vs-verify rank correlation (Q3/Q10) | `data.json`, `study-*/screen`, `study-*/verify` | zero GPU | any screen-J policy |
| T2 | Held-out GP ranking (Q8) | cohort manifests, training sets | zero GPU | BO investment |
| T3 | Refusal-margin classifier (Q7) | stored params + ndjson reasons | zero GPU | feasibility model vs filter |
| T4 | Grid extent vs mesh false-refusal count (Q1) | generate knobs + mesh, no BEM | CPU meshing | fix estimator vs widen box |
| T5 | v7 / v9 / DSP top-quartile rank stability (Q4) | stored `response.npz` | zero GPU (v9 needs the missing module) | objective choice |
| T6 | Pool cheap-check vs actual success AUC | pool artifacts + outcomes | zero GPU | whether BO's low refusal rate is selection bias |
| T7 | Archive occupancy/descriptor analysis (Q9) | `archive.json` + ndjson | zero GPU | QD-first viability |

## Tier 3 — questions that need original scientific/mathematical thought (not delegation)

1. **What is the right object of search?** A scalar J, a feasible region with a menu, a repertoire,
   or a set of re-solvable physical responses? This determines whether the "architecture" is an
   optimizer, an objective, or a data model. Current evidence does not decide it.
2. **What geometric coordinates make invalid or unbuildable shapes rare without excluding good
   horns?** The evidence shows categoricals forced into continuous boxes and coupled knobs
   (E-007/E-008). Whether a physically constrained parameterization can be both expressive and
   low-invalidity is a modelling question, not a code-search question.
3. **How should frequency-dependent coverage be specified so that "acceptable" is not just a wider
   tolerance?** v9's corridor design is one answer; whether corridors should be smooth, monotone,
   asymmetric, or room/DSP-dependent is an acoustic-design judgement.
4. **What would falsify the value of a search supervisor?** The honest answer is an equal-cost,
   predeclared matched experiment with censored reporting; whether that experiment is affordable
   or informative at 2–3 seeds is a statistical-design question.
5. **Does the 600 mm envelope represent a product constraint or a hypothesis about what the owner
   will build?** If the latter, size exploration is a product-research question; if the former, it
   is a hard filter. Only the owner can settle it, but the scientific consequence differs.

## Already settled / not worth further cheap work

- "BoTorch learns from every refusal" — false in this code; refusals are excluded from training
  (E-048).
- "The watchdog can see whether a run is scientifically productive" — false; it sees a conflated
  bad-outcome flag and ignores BO studies (E-025/E-027).
- "The repo has no live-reload or watchdog" — false; both are committed (E-028).
- "The v3 handoff's line numbers/HEAD describe the checkout" — false; cite observed SHAs
  (E-001/E-013).
- "Graded infeasibility penalty applies to native families" — false; it is unreachable there
  (E-017).
- "Widening parameter bounds re-uses old normalized vectors safely" — false; historical clipping
  is refused and encodings change (E-050). Re-encode from physical parameters.
