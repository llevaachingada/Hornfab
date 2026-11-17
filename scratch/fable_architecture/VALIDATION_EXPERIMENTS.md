# VALIDATION_EXPERIMENTS — five standalone research briefs (X1–X5)

Each brief is self-contained. Read `LOW_COST_AGENT_HANDOFF.md` first for the rules, the shared data
and the order. Numbering here supersedes the X1–X11 list in `FABLE_OPTIONS_REVIEW.md`.

**Rules that apply to every brief**
- Repository: `C:\Users\hunte\Hrns\hornlab-search`. Interpreter: `.venv\Scripts\python.exe`.
- Read-only. No GPU or BEM solve, no `hornlab-search` command that solves, no pytest, no git
  mutation, no process control, no edits to tracked files, queues or configs.
- CPU geometry evaluation is allowed. Building a mesh (gmsh) is allowed **only** where a brief says
  so, into a temp folder under `scratch/fable_architecture/.x<N>/`, never into `runs/`.
- Write outputs only under `scratch/fable_architecture/`. Record HEAD SHA and timestamp.
- Report what failed and what is unknown. Do not substitute a different experiment.
- Anything under "Optional BEM stage" is a *proposal to the owner*. Do not run it.

**Shared data (already built)**
- `scratch/fable_architecture/.fable/rows.pkl`: every attempt on the home landscape brief
  (target 80 × 50, envelope 600 × 480 × 480, runs `runs/2026111[5-7]*-screen-*`), 3,802 rows, 3,414
  valid. Fields per row: `run, config, brief (cd|smooth), engine, gen, ok, J, terms, params, knobs,
  bbox, ndof, h (design hash), f, bwh, bwv, di, bounds, created`. Rebuild with `.fable/load.py`.
- Per-design artifacts: `runs/<run>/designs/<h>/{design.json, mesh.msh, response.npz,
  metrics.json, status.json}`. Meshes are gmsh 2.2 ASCII in metres; physical group 1 is the wall,
  group 2 the source.
- `scratch/fable_architecture/.fable/desc.npz`: 27 geometry numbers for 1,715 designs (depth,
  half-width, half-height, 12 H and 12 V inner half-widths), responses, and lane labels.
- "Lane" means one config name. "Engine group": `OSSE` (native), `GRID` (generator name `grid`),
  `GEN-FF` (generator name `typology`).
- "Sibling lanes": lanes that share a construction and differ by version suffix or brief, for
  example `hl__ext_throat_hvlaw_v7` / `_v8`, `hl__osse_rrect_morph_v7` / `_v8`,
  `hl__ath_tritonia_landscape_v7` / `_v8` / `_v9`, `sp__control|moderate|strong_v7`,
  `rr__reference|pucker_*`, and each `*_smooth_*` with its non-smooth twin. Build the full sibling
  map first by stripping `_v\d+`, `_smooth` and seed suffixes and by checking that seed parameters
  match; list it in every report.

---

## X1 — Canonical surface round trip and information preservation

**Question.** Can each existing non-CAD engine emit the surface defined in
`CANONICAL_SURFACE_CONTRACT.md` without losing geometry or source information that matters?

**Decision it changes.** Whether the canonical layer is viable as the common language (ADR open
decision O1), and whether a parametric backbone could inherit existing designs (O2).

**Sources.**
- Contract: `CANONICAL_SURFACE_CONTRACT.md` §3–§9.
- Point-grid input and caller: `.venv/Lib/site-packages/hornlab_mesher/geometry.py:214`;
  `hornlab_search/mesh/grid_build.py` (how `inner`, `outer`, source angle and symmetry are passed).
- Grid and rows surfaces: `hornlab_search/design/generators/grid.py` (`grid_points`,
  `rows_per_azimuth`, `envelope_extents`); family adapters `rolled_family.py`,
  `klangfilm_lame_family.py`, `klangfilm_lame_hv_family.py`, `lecleach_swept_hv.py` (`resolve_grid`).
- Native surfaces without meshing: `hornlab_search/bo/data.py:871-953`;
  `tools/analysis/geometry_effects.py`.
- Design reconstruction from a stored row: `design.json` plus the run's `config.yaml`.

**Method.**
- *Part A, sampling.* Choose 10 designs from each of 6 lanes covering every engine route present in
  `rows.pkl`: one native OSSE with azimuthal law (`hl__ext_throat_hvlaw_v7`), one native OSSE with
  morph (`hl__ath_tritonia_landscape_v9`), one generic grid or rows-with-rollback lane
  (`hl__crowe_x_osse_cd_v7`), one rolled family (`rf__section_axial_home_v7`), one Klangfilm
  (`hl__klangfilm_lame_curved_v1`), one generated freeform (`hl__biradial_es_style_v7`). For each,
  write a throwaway scratch sampler that returns `inner[n_phi, n_s, 3]` in mm on arc-length
  stations, plus every metadata field in contract §5.
- *Part B, checks.* Run the five acceptance tests of contract §8. For test 2 use the stored
  `mesh.msh` wall nodes: compute each node's distance to the sampled surface (nearest point on the
  bilinear patch grid is sufficient).
- *Part C, backbone fit (CPU only).* Fit the area–aspect–section form of
  `FABLE_OPTIONS_REVIEW.md` §3.1 G-B to each sampled surface by least squares and report the
  whole-surface deviation. Also redo the shape-mode fit (`.fable/an4.py`) on whole surfaces instead
  of two planes.

**Success metrics.**
- A, B: all five acceptance tests pass for at least five of six lanes; every exact metadata field
  recovered for all.
- C: informational. Report median and worst deviation per lane for the backbone and for 8, 12 and
  16 whole-surface modes.

**Counterexamples to look for.** Extended-throat designs where the driven plane is not z = 0;
rollback designs where z is not monotone; mouth ripple or fold lanes where 3° sampling misses
detail; designs whose outer shell, not inner wall, sets the envelope; the two-station section limit
of the generated-freeform route.

**Failure criteria.** Two or more engines cannot meet test 2 at any reasonable sampling; or a
source or shell field cannot be recovered without meshing. Either overturns the "common language"
claim for those engines. State which.

**Output.** `X1_ROUND_TRIP.md`: per-lane table of the five tests, the list of fields that could not
be recovered, the measured mesher fit error, Part C numbers, and a revised tolerance proposal for
contract §8. Scripts in `.x1/`.

**Optional BEM stage (owner approval required, do not run).** Re-mesh 6 designs from their
canonical surface through the point-grid route and solve them on the original frequency grid to
confirm the response matches the stored one within the scoring noise. About 6 screen solves.

---

## X2 — Geometry deformation and acoustic authority

**Question.** Which composable modifications of an existing surface give genuinely new control of
H/V directivity, and which only reproduce what existing knobs already do?

**Decision it changes.** Deformation modules versus a parametric backbone as the route to new
shapes (ADR open decision O2).

**Depends on.** X1 Part A samplers (or, if X1 is not done, the two-plane profiles in `desc.npz`,
with the limitation stated).

**Sources.**
- `FABLE_OPTIONS_REVIEW.md` §3.1 G-D (definition of a module as a normal displacement field).
- Surrogate recipe: `.fable/an3.py` (extra-trees model from geometry numbers to beamwidth curves).
- The one existing authority experiment and its decision rule:
  `docs/evidence/klangfilm_hv_2026-11-16/STAGE_A_VS_B_DECISION.md` (throat-only arms moved the
  intended axis ≤ 2.74°; a 3° rule was pre-declared).
- Existing H/V control inside OSSE: the `az_*` keys in `hornlab_search/design/families.py:99-184`;
  lane `hl__ext_throat_hvlaw_v7`.

**Method.**
- *Part A, module library (CPU).* Define six displacement fields on (s, φ), each with one weight in
  mm: vertical squeeze (cos² weighting toward φ = 90°) over the outer half of the wall; the same
  over the inner half; horizontal widening over the outer half; mouth flare (last 15 % of arc
  length, all azimuths); diagonal pull (peaks at 45°); lip roll (increase termination radius).
- *Part B, redundancy.* For three base lanes (best design of `hl__ext_throat_hvlaw_v7`,
  `hl__rosse_rect_cd_v7`, `hl__biradial_es_style_v7`) compute the surface Jacobian with respect to
  the lane's own searched knobs (finite differences, 1 % of each bound range). Project each module's
  displacement field onto the span of those Jacobian columns. Report the unexplained fraction: near
  0 means the module is redundant with existing knobs; near 1 means it is new freedom.
- *Part C, predicted authority.* Using the surrogate, predict the change in mean H and V beamwidth
  in three bands (0.7–1.1, 1.1–2.5, 2.5–5.5 kHz) for weights of ±5, ±10, ±20 mm. Report degrees per
  10 mm and whether H and V move independently (ratio of off-axis to on-axis change).
- *Part D, validity (CPU, mesh-only allowed).* For each module at ±10 mm on each base, check
  envelope, throat ring unchanged, minimum wall gap, and that the point-grid mesh builds inside the
  DOF cap. Mesh only; no solve.
- *Part E, cross-engine combinations (CPU, mesh-only).* Build as point grids three shapes no engine
  produces today: OSSE with azimuthal wall law plus a rolled lip; a rolled body with a mid-wall
  section change; a biradial with the vertical squeeze. Report whether they mesh.

**Success metrics.** A module "has authority" if predicted intended-axis change is ≥ 3° at ≤ 10 mm
weight in at least one band, with the other axis moving less than half as much, and its unexplained
fraction in Part B is ≥ 0.5 on at least two bases.

**Counterexamples to look for.** Modules that only rescale size (the surrogate will credit them
with large changes that are really the size effect; control by renormalizing the bounding box);
modules whose predicted effect lies outside the training data (report the distance to the nearest
training design and distrust predictions beyond the 95th percentile of within-data distances).

**Failure criteria.** No module meets the authority test on two bases, or all that do are
redundant. Then modules are not the route and the backbone alternative moves up.

**Output.** `X2_AUTHORITY.md`: module × base table (unexplained fraction, degrees per 10 mm by band
and axis, validity), the extrapolation-distance check, Part E results. Scripts in `.x2/`.

**Optional BEM stage (owner approval required, do not run).** For the two best modules: weights
0, +10, −10 mm on two bases, 12 screen solves total, judged by the same pre-declared 3° rule on the
grid-invariant score once it exists. This is the only step that can confirm authority; the
surrogate can only nominate.

---

## X3 — Cross-family response-level transfer

**Question.** Can a geometry-aware model predict useful acoustic behaviour for designs from an
engine it has not seen, and would that reduce new BEM evaluations?

**Decision it changes.** Whether to build the response-level surrogate, use it for lane selection,
and later let it choose solves across lanes (ADR open decisions O3, O6).

**Sources.**
- Baseline to reproduce first: `.fable/an3.py` and `.fable/an5.py`. Published baseline numbers:
  leave-one-lane-out error 4.5° (H) and 4.0° (V) against naive 11.0° and 14.1°; leave-one-engine-out
  skill R² 0.39 / 0.69 (OSSE held out), 0.18 / 0.51 (GRID), 0.53 / 0.71 (GEN-FF); lane ranking 0.90.
- Responses: `response.npz` per design, loaded with `hornlab_search.solve.cache.load_response`
  (fields `freqs_hz, h_angles_deg, v_angles_deg, spl_h_db, spl_v_db, spl_balloon_db, z_throat`).
- Metric definitions: `hornlab_search/metrics/compute.py`.

**Method.**
- *Part A, strict splits.* Three validation schemes, reported side by side: (1) leave one lane out;
  (2) leave one *sibling group* out (all versions and brief twins of a construction together);
  (3) leave one *engine group* out. Scheme 3 is the headline. Scheme 1 is reported only to show the
  size of the leakage.
- *Part B, better inputs.* Compare: size only; two-plane profiles (the baseline); whole-surface
  descriptors from contract §7 if X1 is done; the same with lengths multiplied by 2π f / c so one
  model serves all frequencies.
- *Part C, more targets.* Add throat resistance curve, in-coverage ripple and on-axis response to
  beamwidth and DI.
- *Part D, size control.* Repeat scheme 3 after removing the size effect (regress every target on
  depth, width and height first, then test whether shape descriptors predict the residual). This
  checks whether "engines occupy different response regions" is more than a size difference.
- *Part E, similarity augmentation, with leakage control.* A design solved at scale 1 gives exact
  responses at scale s for frequencies divided by s. Add copies at s = 0.8, 0.9, 1.1, 1.25 to the
  *training* set only. All copies of a design must stay in the same fold as the design; never
  evaluate on a scaled copy of a training design. Report gain against the unaugmented model under
  scheme 3. Note the scaled throat no longer matches the driver; exclude the top octave of each
  scaled copy.
- *Part F, value in solves.* Learning curves inside a held-out engine: ranking quality of a model
  with n = 0, 8, 16, 32, 64 local designs, with and without the transferred model's prediction as
  an input. Report how many local solves the prior is worth.

**Success metrics (scheme 3, held-out engine).**
- Skill R² ≥ 0.6 on both H and V beamwidth for at least two of three engines.
- Within-lane rank correlation of predicted against true coverage error ≥ 0.6 median.
- Prior worth ≥ 15 local solves in Part F.
- Part D residual skill R² > 0.2 (shape matters beyond size).

**Counterexamples to look for.** Results that hold under scheme 1 but vanish under schemes 2 and 3
(sibling leakage); augmentation gains that vanish when copies are kept in-fold (correlated
augmentation); a model that predicts lane means well but cannot rank inside a lane; good beamwidth
but no skill on impedance or ripple.

**Failure criteria.** Scheme 3 skill below 0.3 on both planes for two engines after Part B, or
Part F shows the prior worth fewer than 5 solves. Then transfer is not a basis for lane selection
or unified acquisition; the canonical layer remains useful for validity and sensitivity only.

**Output.** `X3_TRANSFER.md`: the three-scheme table per input set and target, Part D, Part E with
and without leakage control, Part F curves, and a one-line verdict against each metric. Scripts in
`.x3/`.

**Optional BEM stage (owner approval required, do not run).** Prospective test: for a construction
with no stored rows, have the model rank 200 CPU-generated candidates, solve its top 10 and 10
random ones. 20 screen solves.

---

## X4 — Parameter-space intelligence

**Question.** Which knobs are inactive, coupled, redundant or pinned by a real constraint, and how
should that shape future searches without removing useful freedom too early?

**Decision it changes.** Which knobs future search configs fix, link or free, and whether bounds
should be expressed as constraints on the surface (ADR open decision O4).

**Sources.**
- Existing ledger and vocabulary: `tools/analysis/parameter_activity.py` (native only; proves one
  no-op), `tools/analysis/links.py` (statistical co-movement), `hornlab_search/search/links.py`
  (linear links; refused for generator blocks at lines 36-37).
- Known conditionals to recover as a sanity check, from `GEOMETRY_AND_PARAMETER_MAP.md` §2: `n` and
  `q` inactive at `s = 0`; `s1`, `s2` inactive unless both non-zero; `morph_*` inactive at
  `morph_target = 0`; `morph_exponent` inactive unless target is 3; an active guiding curve replaces
  `a_deg`; `rot_deg` couples radius and depth.
- Baseline acoustic importance: `.fable/an2.py` part A (12 lanes; 2–7 of 5–18 knobs carry 90 % of
  importance; lanes with a pinned top-decile knob: `g_fc_hz`, `g_L_mm`, `s`, `g_depth_mm`,
  `az_a_cos_pow`, `morph_width_mm`, `n`).
- Bound and envelope checks: `hornlab_search/search/evaluate.py` (`envelope_violation`, about line
  281); `hornlab_search/design/generators/grid.py` (`envelope_extents`).

**Method.**
- *Part A, geometric evidence (CPU).* For five lanes with ≥ 100 valid rows spanning the engines, at
  the best design and at 10 random valid designs: finite-difference Jacobian of the sampled surface
  with respect to each searched knob (step 1 % of the bound range). Report per knob the RMS surface
  movement in mm; the singular values and numerical rank; pairs of knobs whose columns have cosine
  > 0.95.
- *Part B, acoustic evidence (zero GPU).* Per lane: permutation importance from an extra-trees
  model on J and separately on H and V coverage error; stability across five bootstrap resamples.
- *Part C, classification.* Label each knob with one of: `inactive here` (moves the surface < 0.2
  mm everywhere sampled), `geometrically active, acoustically weak` (moves the surface, importance
  indistinguishable from zero across bootstraps), `coupled with <knob>`, `pinned at box edge`
  (top-decile mass within 3 % of a bound, and the constraint margins of contract §7 are not near
  zero), `pinned at a real constraint` (same, but a constraint margin is near zero), `active`.
- *Part D, temporal check.* Fit Parts B and C on the first half of each lane's rows in time order;
  report agreement with the second half.

**Success metrics.** Part A recovers every known conditional listed above that applies to the
sampled lanes; Parts A and B agree on at least 80 % of knobs labelled inactive or weak; Part D
agreement ≥ 75 %.

**Counterexamples to look for.** A knob that is inactive at the sampled designs but active
elsewhere in the box (conditional activity: sample at box corners before labelling); a knob that
barely moves the surface but strongly moves the response (throat-region knobs are the likely case,
so weight surface movement near the throat separately); importance that reflects where the
optimizer happened to sample rather than the physics.

**Failure criteria.** Geometric and acoustic evidence disagree on more than a third of knobs, or
labels are unstable between halves. Then importance cannot yet drive search design.

**How results may be used (state this in the report).** Recommend `fix` only for `inactive here`
confirmed at box corners; recommend a link only for `coupled` pairs confirmed geometrically;
recommend a widening *proposal* (never an automatic change) for `pinned at box edge`;
`geometrically active, acoustically weak` knobs stay free but are flagged as first candidates to
freeze when dimension must drop.

**Output.** `X4_PARAMETER_SPACE.md`: one table per lane with the labels and evidence, the list of
recovered and missed known conditionals, proposed fixes, links and widening proposals. Scripts in
`.x4/`. No config is edited.

**Optional BEM stage.** None.

---

## X5 — Adaptive allocation: what historical replay really establishes

**Question.** What do replays of past campaigns establish about lane racing, portfolio and
supervisor policies, once hindsight and seeded-lane leakage are removed?

**Decision it changes.** Whether to build lane racing or any supervisor beyond a noise-aware rule
table, and what it may automate (ADR open decision O5).

**Sources.**
- First replay to reproduce and then correct: `.fable/an2.py` part B. Its published numbers: 27
  constant-directivity lanes, 2,853 attempts; campaign best J 3.10 reached at attempt 55 in actual
  order; successive halving reached it after 290 attempts and consumed 1,363 in total; best of first
  16 rows against final lane rank 0.90. **Known flaw:** lane `hl__ext_throat_hvlaw_v8` was seeded
  with the v7 optimum, so the replay found the best design "early" for free.
- Watchdog rules and replay: `tools/run_campaign_night.py` (verdict function about lines 164-211);
  `WATCHDOG_REPLAY.md`.
- Warm starts and seeds: each run's `config.yaml` (`seed_params`, `search.warm_start`), and
  `hornlab_search/search/warmstart.py`.
- Noise floor: `FABLE_DISCOVERY.md` §5.1 (0.17 J standard deviation among the best designs); use
  the grid-invariant value if the other agent has produced one in `FREQUENCY_BUDGET.md`.
- Night plans and what the owner asked for: `runs/nights/*.yaml`, `docs/queue/HOME_18H_PLAN_2026-11-16.md`.

**Method.**
- *Part A, lineage map.* For every run in `rows.pkl`, determine where its starting point came from:
  hand-written seed, the best design of an earlier run (which one), or a warm start. Mark every lane
  whose first row is already within one noise unit of its parent's best as "seeded".
- *Part B, corrected replay.* Re-run the replay with (1) seeded lanes merged into their parent as
  one arm, in time order; (2) only time-respecting information (a policy may pull a lane only after
  the timestamp at which that lane's config existed); (3) all "reach the target" thresholds
  expressed as "within one noise unit of the eventual best".
- *Part C, policies.* Actual order; round robin; successive halving with and without an exploration
  floor (every arm gets at least 32 rows); a max-seeking bandit (rank arms by best-so-far with a
  bonus that shrinks with pulls); and the existing watchdog rules applied per run.
- *Part D, censoring ledger.* For every arm a policy stops early, record what that arm later
  achieved in the real data. Report lanes dropped that ended in the true top three, and
  owner-requested lanes dropped (see the night plans).
- *Part E, predictability.* Rank correlation between best-of-first-n rows and final lane best for
  n = 8, 16, 32, with seeded lanes merged; and the same using a geometry-only prediction if X3 has
  produced one.
- *Part F, sensitivity.* Repeat Part B with row order shuffled within each run (20 shuffles) to show
  how much of any saving is ordering luck.

**Success metrics.** A policy is worth building only if, after the Part B corrections, it reaches
within one noise unit of the best with at least 30 % fewer attempts than round robin in the median
shuffle, drops no eventual top-three arm, and drops no owner-requested lane.

**Counterexamples to look for.** Savings that disappear when seeded lanes are merged; a lane that
started badly and finished best (`hl__ext_throat_hvlaw_v7`: 6.6 after 16 rows, 3.10 final) being
dropped; smooth-brief and constant-directivity lanes compared on J (they are different objectives:
never race them against each other); arms stopped by the watchdog counted as failures rather than
censored.

**Failure criteria.** Corrected savings below 15 %, or any top-three arm dropped under every policy
with a floor. Then the evidence supports only a rule table and human ordering, and adaptive
allocation waits for a prospective test.

**Output.** `X5_ALLOCATION.md`: lineage map, corrected replay table per policy, censoring ledger,
predictability by n, shuffle spread, and a list of exactly which supervisor actions the evidence
supports automating. Scripts in `.x5/`.

**Optional BEM stage (owner approval required, do not run).** A prospective matched test: two
nights with identical approved job lists, one in fixed order and one under the best policy, equal
attempt budgets, results censored honestly.

---

# Part 2 — briefs E1–E3 (from `ARCHITECTURE_SYNTHESIS.md` §5) and S1

These three decide between the two candidate architectures. The rules and shared data at the top
of this file apply. S1 (range-plus-constancy scoring) is briefed in `SCORING_RANGE_PROPOSAL.md` §7.

## E1 — Does modelling the response beat modelling the score?

**Question.** If the next design to solve had been chosen by a model that predicts response curves
and then applies the scoring, would good designs have been found in fewer solves than by a model of
J, or by the order the optimizer actually used?

**Decision it changes.** Whether response-model-centred discovery is the spine of the architecture
(`ARCHITECTURE_SYNTHESIS.md` §3). This is the single most important experiment.

**Sources.**
- `scratch/fable_architecture/.fable/rows.pkl` and `.fable/desc.npz` (see shared data).
- Scoring of a predicted response: v7 coverage is `mean((bw − target)²)/100` with the narrow side
  doubled (`hornlab_search/objective/scalar_v7.py:410-513`); the full scorer needs a complete
  response. Because the model predicts beamwidth and DI curves only, use the **coverage-plus-DI
  part of J** as the objective for all selectors, computed identically from true curves when a
  design is "revealed". State this limitation in the report.
- Model recipe: `.fable/an3.py` (extra-trees from geometry numbers to curves).

**Method.** This is a replay: nothing is solved. The "pool" is the set of designs already solved,
and "solving" a design means revealing its stored result.
- *Part A, within a lane.* For each lane with ≥ 100 valid rows: start from 8 randomly revealed
  designs. Repeatedly pick one unrevealed design and reveal it, using each selector:
  (a) **score model:** predict the objective directly from the lane's knobs; pick the lowest
  prediction;
  (b) **response model:** predict the beamwidth and DI curves from geometry numbers, compute the
  objective from the predicted curves, pick the lowest;
  (c) **actual order:** the order the optimizer really used;
  (d) **random order**, as a floor.
  Refit after every 8 reveals. Record how many reveals each selector needs to find a design within
  0.1 of the lane's best objective. Repeat with 10 random starts.
- *Part B, with help from other engines.* Same, but selector (b) may also train on all designs from
  *other engine groups* from the start. This tests whether cross-engine data speeds up a new lane.
- *Part C, cross-engine discovery.* Hold out one engine group entirely. Train (b) on the other two.
  Rank the held-out group's designs by predicted objective. Report what fraction of the held-out
  group's true best 10 % appear in the model's top 10 % and top 25 %.

**Success metrics.**
- Part A: selector (b) needs at most half the reveals of (a) and of (c), in the median lane.
- Part B: adding other-engine data reduces reveals further, by at least 20 %.
- Part C: at least 40 % of the true best decile is in the model's top 25 % for two of three engines
  (random would give 25 %).

**Counterexamples to look for.** Selector (c) looks slow only because the optimizer was also
exploring; (b) wins only in lanes with a sibling lane in training (apply the sibling map and
exclude siblings); (b) wins on coverage but the true J winner differs because of loading or ripple
(report how often the coverage-plus-DI best is also in the top decile of full J).

**Failure criteria.** Selector (b) is not clearly faster than (a) in Part A, and Part C is at
chance. Then the response-model spine is unsupported and the alternative (E2) or the present
per-lane approach stands.

**Output.** `E1_RESPONSE_VS_SCORE.md`: table of median reveals per selector per lane, Parts B and C,
the sibling-excluded versions, and a verdict against each metric. Scripts in `.e1/`.

**Optional BEM stage (owner approval required, do not run).** A prospective night: 40 solves chosen
by selector (b) from a freshly generated pool against 40 chosen by the usual optimizer, same lane
and brief.

## E2 — Is the response locally invertible?

**Question.** Near a given horn, does a small change of shape produce a proportional, predictable
change of response, well enough that a target response could be reached by a few corrective steps?

**Decision it changes.** Whether "construct, then correct" (`ARCHITECTURE_SYNTHESIS.md` §4) is
viable as the spine or as a proposer.

**Sources.** `.fable/desc.npz` (shape numbers `X`, responses `Y`, lanes `G`); `.fable/an4.py`
(shape modes); `.fable/an1.py` (response principal components).

**Method (stage one, stored data only).**
- Reduce shape to depth plus 8 shape modes and response to 6 principal components (fit both on all
  designs; report the variance each keeps).
- *Part A, local linearity.* For 300 randomly chosen designs, take the 40 nearest designs in shape
  space, fit a linear map from shape change to response change, and report: fit quality on 10
  held-out neighbours; the map's condition number; its singular values.
- *Part B, controllability.* From those singular values, identify response directions that no
  shape change moves (near-zero singular values). Describe them in plain terms, for example
  "low-frequency vertical beamwidth at fixed mouth height".
- *Part C, retrospective correction.* For 500 pairs of designs (i, j) that are neighbours in shape
  space: use the local map at i to predict the shape change needed to turn i's response into j's;
  compare with the true shape difference (relative error). Repeat for pairs two and four
  neighbourhood-radii apart to see how far a step can be trusted.
- *Part D, across engines.* Repeat Part A with neighbours restricted to a different engine group
  from the centre design.

**Success metrics.** Part A held-out fit R² ≥ 0.7 in the median neighbourhood; Part C relative
error ≤ 30 % for adjacent pairs and ≤ 50 % at two radii; at least four response directions
controllable.

**Counterexamples to look for.** Neighbourhoods that are all siblings from one optimizer run (the
map then describes that run, not the physics: require at least two lanes per neighbourhood where
possible and report both ways); good fit only because size dominates (repeat with size regressed
out); response directions that matter for the score but are uncontrollable.

**Failure criteria.** Median R² below 0.4, or step predictions no better than assuming no change.
Then correction by proportional steps is not viable and the alternative architecture is closed.

**Output.** `E2_INVERTIBILITY.md`: the four parts with distributions, the list of uncontrollable
directions, and a verdict. Scripts in `.e2/`.

**Stage two (owner approval required, do not run).** Three target responses inside the reachable
set, five corrective steps each, about 15 solves; success is reaching each target's coverage within
3° in five steps.

## E3 — Can a candidate be judged from a few frequencies?

**Question.** Could hopeless candidates be abandoned after a few frequencies, and how much compute
would that have saved without discarding good designs?

**Decision it changes.** Whether the choice of frequencies becomes part of experiment selection
under either architecture, and whether a staged solve interface is worth requesting.

**Sources.**
- Solver wrapper: `hornlab_search/solve/` (find where the frequency list is passed to the backend
  and whether frequencies are solved in a loop; `solve/worker.py` and the backend adapter).
- Measured per-frequency cost: `TOOLCHAIN.md`, lines about 105–132.
- Rows and stored 18-frequency responses: `rows.pkl`; per-row `seconds` and `n_dof` in
  `search.ndjson`.

**Method.**
- *Part A, code read.* Establish, with file and line references: is cost proportional to the number
  of frequencies; can a solve be issued for a subset and later extended on the same mesh without
  repeating work; what fixed overhead exists per call. If the answer is "not without solver
  changes", say so; Part B is then an estimate of what such a change would be worth.
- *Part B, replay.* For each lane, process designs in the order they were solved. For each design,
  reveal frequencies in a fixed informative order (start with one near the crossover, one mid-band,
  one high, one low; then the rest). After each reveal compute the best J the design could still
  achieve: score the revealed frequencies as they are and assume a perfect result at the unrevealed
  ones. Abandon when that bound is worse than the lane's best-so-far by more than a margin.
  Use margins of 0.5, 1.0 and 2.0 J.
- *Part C.* Report the fraction of frequency-solves saved; the number of designs wrongly abandoned
  that were in the lane's final top 10 %; and the saving when the order of frequencies is chosen
  per lane to maximize early separation.

**Success metrics.** At least 40 % of frequency-solves saved at a margin that wrongly abandons no
final top-decile design.

**Counterexamples to look for.** Terms that are not sums over frequency (standard deviations,
slopes, the loading crossing) cannot be bounded by "assume perfect elsewhere" in a simple way:
handle each explicitly and state the bound used. Early in a run the best-so-far is poor, so little
is abandoned (report savings by position in the run). Abandoned designs leave incomplete responses
(count how many training rows would have been lost).

**Failure criteria.** Less than 20 % saved at any safe margin, or Part A shows a large fixed cost
per call that removes the benefit.

**Output.** `E3_FREQUENCY_STAGING.md`: Part A findings with references, the savings table, the
false-abandonment count, and a verdict. Scripts in `.e3/`.

**Optional BEM stage.** None proposed; a staged solve would be a solver-interface change, which is
an owner decision.

---

# Part 3 — briefs U1–U3 (layered backbone, from `UNIVERSAL_HORN_FAMILY.md` §6)

These decide whether a layered generator with pluggable specialist laws is worth building. Read
`UNIVERSAL_HORN_FAMILY.md` §1.2 and §2 first (20 minutes). The rules and shared data at the top of
this file apply. **Vocabulary:** a horn is a sheet of points `P(s, φ)`; `s` runs 0–1 from throat to
lip along the wall, the same stations at every azimuth `φ`. *Layers* along the horn: throat,
expansion, H/V split, section, termination. A *specialist law* is an existing family's own
mathematics used to fill one layer.

## U1 — Can a layered form reproduce existing horns exactly?

**Question.** If each existing law-based family is rewritten as "its own expansion law + its split
+ its section + its termination, on shared wall-length stations", is the resulting surface the same
as the one Hornfab built and solved?

**Decision it changes.** Whether a layered backbone can inherit historical designs and data, or is
only one more family.

**Depends on.** The X1 scratch samplers under `.x1/` (five of six routes materialize; Klangfilm
does not, see X1 report).

**Sources.**
- Mesher families and their formulas: `docs/research/typologies/MESHER_TYPOLOGIES.md` §1 (OSSE),
  §2 (R-OSSE), §3 (ICW curvature spline), §4 (FREEFORM), §6 (morph, azimuth-dependent parameters).
- Existing near-backbones to study as models: `hornlab_search/design/generators/grid.py` (header
  docstring: radius field), `crowe_hv_area_aspect_v1.py` (header: area/aspect/section),
  `tools/geometry/klangfilm_lame_hv_core.py` (header: slope laws, section exponent, beak).
- Shared-station lesson: `docs/research/typologies/LECLEACH_HV_ELLIPSOID_2026-11-16.md` §2–§3.
- Best stored designs: `.fable/rows.pkl`; meshes at `runs/<run>/designs/<h>/mesh.msh`.

**Method (CPU only, no mesh build needed).**
1. Choose the best valid design from each of four lanes: `hl__ext_throat_hvlaw_v7` (OSSE with
   azimuth law), `hl__biradial_es_style_v7` (two profiles, generated freeform),
   `hl__rosse_rect_cd_v7` or `hl__crowe_x_osse_cd_v7` (rows / rollback), and one Le Cléac'h H/V
   lane (`hl__lecleach_hv_landscape_smooth_v7`).
2. For each, sample the family's own surface on 65 wall-length stations × 31 azimuths using the X1
   sampler. This is the *target*.
3. Write the same horn in layered form, in a scratch script: (a) principal ribs at 0°, 45°, 90°
   taken from the family's own law; (b) wall angle `ψ(s)` along each rib computed from those ribs;
   (c) the section between ribs described by one shape exponent per station plus one diagonal
   term; (d) the lip as the continuation of `ψ` past the hand-over station. Rebuild the surface
   from (b)–(d) only.
4. Report whole-surface deviation between rebuilt and target (median, 95th percentile, worst, and
   where the worst occurs: throat, body, corners, lip).
5. Repeat step 3 replacing the family's own rib law with a generic one: `ψ(s)` as a monotone
   spline with 4, 6 and 8 control values per rib. Report the same deviations. The gap between
   steps 4 and 5 is what the specialist mathematics is worth.

**Success metrics.** Step 4 worst deviation ≤ 0.5 mm for at least three of four lanes.

**Counterexamples to look for.** Rounded-rectangle corners and morphs that one exponent plus one
diagonal term cannot follow; lips where ribs have different lengths so that shared stations distort
the roll; throat extensions where the driven plane is not at `s = 0`.

**Failure criteria.** Two or more lanes above 2 mm in step 4 with the family's own ribs. Then the
"sheet with three ribs and a section law" is too poor a carrier, and the section layer needs more
than one exponent and one diagonal term (report how many azimuth terms are needed to reach 0.5 mm).

**Output.** `U1_LAYERED_REPRODUCTION.md`; scripts in `.u1/`.

**Optional BEM stage (owner approval required, do not run).** Solve the four rebuilt surfaces
through the point-grid route and compare responses with the stored ones. Four screen solves.

## U2 — Are the families islands or one continent?

**Question.** Between two good horns from different families, are the in-between shapes valid and
sensible, or is there a wall of bad shapes?

**Decision it changes.** Whether one shared search space can replace lanes, or whether a lane-like
outer choice must remain even inside a common generator.

**Depends on.** U1 step 3 (layered descriptions of the endpoint horns).

**Method.**
1. *Paths (CPU).* Take three pairs of U1 horns from different lanes. For each pair, interpolate the
   layered description in ten equal steps: wall angle along each rib, section exponent, diagonal
   term, lip curvature and wrap, rib length. Rebuild each intermediate surface.
2. *Validity (CPU).* For every intermediate: inside 600 × 480 × 480; throat ring unchanged; no
   backward fold before the lip; minimum wall-to-wall gap above twice the wall thickness plus 2 mm;
   width and height non-decreasing before the lip. Report which checks fail and where on the path.
3. *Predicted behaviour (zero GPU, indicative only).* Predict beamwidth curves with the model in
   `.fable/an3.py`, and mark each intermediate as inside or outside the training data by distance
   (beyond the 95th percentile of within-data nearest-neighbour distance = outside).
4. *Smoothness measure.* Along each path report the largest step-to-step change in predicted mean
   H and V beamwidth and whether the sequence is monotone.

**Success metrics.** At least two of three paths are geometrically valid at every step.

**Counterexamples to look for.** Paths valid only because the endpoints are near-twins; predicted
smoothness that merely reflects the model averaging (which is why the BEM stage matters).

**Failure criteria.** Two of three paths have invalid stretches longer than two steps. Then
families are separated by invalid geometry in this description, and either the description must
change or lanes must stay.

**Output.** `U2_PATHS.md` with one table per path and rendered section overlays; scripts in `.u2/`.

**Optional BEM stage (owner approval required, do not run).** Solve the eleven shapes on each of
two valid paths, 22 screen solves. This is the only real test of "one continent".

## U3 — Do the new structural freedoms move the beam?

**Question.** Do the freedoms that no current family exposes change the response enough to matter?

**Decision it changes.** Whether the backbone's extra reach is acoustically real. Precedent: the
Klangfilm Stage A test, where a geometrically real freedom moved the beam ≤ 2.74°
(`docs/evidence/klangfilm_hv_2026-11-16/STAGE_A_VS_B_DECISION.md`).

**Depends on.** U1 (layered description of the best stored design).

**Method.**
1. *Variants (CPU).* Starting from the layered description of the best design of
   `hl__ext_throat_hvlaw_v7`, build single-change variants, each paired with the unchanged control:
   (a) vertical flare timing: keep the vertical wall angle low for the first 60 % of the wall, then
   open so the mouth height reaches 460–480 mm at unchanged depth (two strengths);
   (b) termination split: larger lip radius on the sides with the top and bottom unchanged, and
   the reverse (two variants);
   (c) section steering: exponent rising from 2 to 3 early versus late (two variants);
   (d) diagonal term pulling the 45° wall in by 10 mm at the mouth (one variant).
2. *Checks (CPU).* All validity checks of U2; report mouth width, height, depth, minimum lip radius.
3. *Indicative prediction (zero GPU).* As U2 step 3, with the inside/outside flag.

**Success metrics for the CPU stage.** All variants valid; each changes the surface by at least
5 mm RMS somewhere other than the last 5 % of the wall.

**Failure criteria for the CPU stage.** Variant (a) cannot reach 460 mm height without violating a
validity check. Then the "unused height" opportunity is geometric fiction in this envelope.

**Output.** `U3_STRUCTURAL_FREEDOMS.md`; scripts in `.u3/`.

**BEM stage (owner approval required, do not run).** Solve the control and the seven variants plus
repeats of the control on a denser frequency grid: about 12–16 screen solves. Pre-declared rule: a
freedom "has authority" if it moves the intended plane's mean beamwidth by ≥ 3° in at least one of
the bands 0.7–1.1, 1.1–2.5, 2.5–5.5 kHz while the other plane moves by less than half as much.
Score with the grid-invariant method from `FREQUENCY_BUDGET.md` (at least 22 frequencies).
