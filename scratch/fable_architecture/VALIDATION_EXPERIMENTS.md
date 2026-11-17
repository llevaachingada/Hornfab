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
