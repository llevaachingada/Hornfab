# Horn optimization hardening: geometry, acoustics, value and rollout

**Decision record, 2026-11-12.** This pass follows the owner's request for a parent research pass and two independent Terra reviews. It hardens [the reviewed plan](COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md), [the Bayesian/GUI specification](BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md) and [the execution prompts](DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md). The updated protocol is **`bo-study-v1.1`**. These are still planning documents; no optimizer, solver, dataset or GUI implementation was changed.

**Verdict:** the direction is useful, but the prior plan put workflow infrastructure ahead of evidence and did not sufficiently distinguish nominal controls from physical effects. **BoTorch remains included in the full implementation scope**, through engine, GUI, proposals, serial execution, verification and feedback. Put reusable data/rescoring and the **knob → geometry → acoustic response → score** explanation first; build the pure BoTorch adapter in parallel once those interfaces are frozen, then integrate the full loop in dependency order. Gates protect correctness and adoption; they do not remove BoTorch or make implementation depend on a prematurely favorable benchmark.

## 1. What the two reviews changed

| Finding | Evidence | Accepted change |
|---|---|---|
| A searched knob is inactive in the first task | `native__ath_core_v4.yaml:76` pins morph target 1; `:89` searches exponent. Installed `hornlab_mesher/profile_morph.py:550`–`:605` reads exponent only for target 3 | Activity/conditionality audit before feature selection; preserve production config, use an explicit reversible advisory encoding |
| Nominal parameter hashes are not physical uniqueness | `Design.hash` hashes family/params; ignored fields can change hash without changing shape | Keep source design hashes; add sampled final-geometry equivalence diagnostics, never relabel a parameter hash as proof of different surfaces |
| Resolved brief matters more than inline YAML/comments | `config.py:1259`–`:1270`; first brief is 300–8000 Hz, f0 1280 Hz and narrow-side weight 2 | Display/test actual resolved values and provenance; no model trained against stale inline targets |
| The proposed Pareto coverage helper lost an acoustic preference | `V8Params.for_class` sets tolerances, leaving default narrow ratio 1; selected v4 brief requires 2 | Explicitly map supported coverage conventions from the resolved objective; hash/test the metric; no silent symmetric replacement |
| First task is a directivity study with a source-model caveat | Brief `:19`–`:22` discloses the 2-inch uniform-piston limitation around f11≈3957 Hz; loading weight is 0 | Split source-assumption bands; never claim this task optimizes driver loading, efficiency, distortion or max SPL |
| Beamwidth alone can hide lobes/saturation | `metrics/polar.py:69` onward uses outermost crossings and a 180° no-crossing convention; `metrics/compute.py:135` retains multilobe counts | Report crossings, saturation, full polars/balloon DI and missingness alongside coverage/ripple |
| Tree finite differences are not physical derivatives | ExtraTrees is a discontinuous predictor; correlated/adaptive samples and high-dimensional nearest-neighbor distance do not prove local support | Treat finite-step nonadditivity as a provisional diagnostic; prespecified step sensitivity, joint support and group stability; controlled 2×2 acoustic checks come later |
| A large 14-dimensional global pool is not proven useful | 4096 Sobol points, capped 256-point fit and fixed GP regularization were engineering choices | Run subset/pool/noise diagnostics and compare to simple/CMA proposals before closed-loop claims |
| New orchestration was too early | Existing analysis/report and run/verify GUI surfaces already exist | First milestone is an immutable read-only report and a small existing-GUI extension; SQLite/new jobs/new runner are not prerequisites |
| Default cache enforcement could disrupt reuse | S2 previously planned to miss unknown legacy producer entries throughout production callers | Audit first; any enforcement is separately approved, opt-in, tested and reversible |

Reviewers inspected actual source independently and returned recommendations; the parent made the final choices. Source baseline for this pass: DOCS **`4910c64`**, with these documentation edits uncommitted; local `origin/main` **`091c6ed`** (merge of the prior research-plan branch). No code differences were reported by `git diff HEAD..origin/main` over the inspected design/objective/search/surrogate/GUI paths. Remote state can advance again.

## 2. The horn-specific parameter model

The analysis must maintain four separate layers:

1. **Control:** the exact native/generator knob, units, physical family, resolved bounds, transforms and applicability conditions.
2. **Final geometry:** what surface actually changes after morph, guiding curves, axial stretch, clipping, construction and mounting.
3. **Acoustics:** measured per-frequency/per-angle pressure, impedance/loading and derived metrics under a declared source/boundary/mesh model.
4. **Preference:** how the frozen objective's masks, tolerances, weights and gates turn those measurements into J.

A change in layer 4 does not change the horn. A changed parameter hash does not establish a change in layer 2. A change in layer 2 does not establish a better layer-3 response. The report must make these distinctions visible.

### 2.1 Required control ledger

Reuse the existing parameter SSOT in `design/params/`, `families.KeySpec`, generator registry and mesher schema. Add analysis activity records; do not create another authority for horn defaults/units. Each record includes: native/generator context; `searched/fixed/derived/conditional/inactive/unresolved`; actual resolved value/range; application predicate; affected geometry features; source code reference; unit transform; and evidence status. Static disabled branches can establish inactivity. A flat local numerical response alone cannot prove global inactivity.

Examples for the first task, not universal acoustic laws:

| Controls | Geometry relationship to inspect | Interpretation limit |
|---|---|---|
| `L_mm`, `a_deg`, `a0_deg`, `k` | Depth and generalized OS throat/flare profile; nominal angle is a wall half-angle | Target coverage is a total included acoustic angle, not simply the same number or guaranteed twice the knob |
| `n`, `s`, `q` | Shape/amount/truncation of the added termination | A termination change also changes effective aperture and curvature; effects are coupled |
| `s1`, `s2` | Existing axial-stretch law, with their documented units | Installed law is inactive when either component is zero; station parameter is not necessarily physical z |
| Morph width/height/corner/rate/fixed fraction | Final target contour and where/how it blends into the base | Can affect diagonals and both planes, not independent H/V sliders |
| `morph_exponent` | Superellipse target exponent | Inactive for this task's fixed rounded-rectangle target 1; active for target 3 |

Keep all original knobs/configs unchanged for reproducibility. An advisory BO feature projection may remove **statically proven, geometry-tested no-op controls**, fixing them to the recorded reference value when decoding. This projection is versioned and reversible; compare it explicitly with the full-dimension CMA baseline. It cannot merge different categorical branches or silently remove a locally quiet but conditionally active knob.

One useful mathematical example is the documented smooth morph branch: `r_final = r_base + t^gamma*(r_target-r_base_at_end)`, with t running from the fixed-part boundary to the mouth. Here target means the **resolved** target after implicit sizing/no-shrink rules, before any later global transforms. At t=1 that target fixes the morph-branch mouth; gamma changes the interior transition. Holding base/end/target/fixed boundary constant, for 0<t<1 the geometry derivative is `t^gamma*log(t)*(r_target-r_base_at_end)`; its sign depends on expansion versus contraction. Thus width/height and rate already interact **in the construction**, before acoustics. “Larger rate is better” is not a global rule. This explains the sourced construction, not a replacement implementation/acoustic gradient; the adapter must preserve actual stretch/scaling/transform order.

### 2.2 Geometry bridge and equality tests

Sample the **canonical final transformed surface** using existing geometry/profile APIs; never reimplement the OSSE equation or a mesher. Preserve physical z and normalized z/depth, H/V and diagonal meridians, azimuthal cross-section contours, derived area/aspect, absolute throat/mouth/depth, and termination descriptors. Account for axial stretch and noncircular contours. Two shapes sharing H/V cuts can still differ in their corners/diagonals.

Every sampled descriptor records station/azimuth grid, units, boundary/seam convention, symmetry and sampling-convergence check. Freeze the adapter and grid at the parent contract gate after inspecting the actual API. Unsupported CAD/non-star-shaped surfaces remain unsupported until an existing geometry API supplies an appropriate representation. Do not force a radial representation onto arbitrary geometry.

Use several legal anchor designs to perturb each knob at the declared normalized steps. Report geometry change with its numeric tolerance and activity region. A sampled-geometry fingerprint is an analysis approximation, not a replacement for production hashes or proof that unsampled surfaces are identical. Do not change cache keys from it.

Optional geometry-Jacobian singular values describe **local numerical shape sensitivity** only. They are not acoustic gradients, global dimensionality proofs or an inverse generator. Clamps, topology changes and failed perturbations must be explicit.

One pure installed-component check was run here, without meshing or BEM: at 64 azimuths, changing morph exponent 2→8 caused **zero** target-contour change for target 1; the same change affected 60/64 samples for target 3. The illustrative contour used width 400 mm, height 300 mm and corner 20 mm, not edited project defaults. This confirms that code branch's conditional behavior, not whole-surface convergence or an acoustic effect.

### 2.3 Size, frequency, source and objective confounding

Report two distinct study questions: **best horn within a stated envelope** and **shape benefit at matched physical size**. If a longer/wider horn scores better while its aperture grows, say that; do not claim the flare law alone improved. For matched-size follow-up, use legal constructions that hold relevant dimensions fixed and record what still changes. Do not statistically condition away a deterministic construction relationship and call the result a causal law.

Include absolute dimensions and dimensionless frequency/size (`k=2πf/c`, `kW`, `kH`, or a declared equivalent radius). Wavelength-scaled geometry comparisons require consistent scaling of every dimensional input and source/observation condition; normalized plots do not make fixed-frequency SPL or a real driver scale invariant.

The first task's 2-inch source and 300–8000 Hz brief are retained. Show results below/above the brief's modal/source-assumption marker separately, with higher-band predictions labeled geometry comparisons under that excitation. Do not silently shorten the scoring band to improve agreement or claim the marker is a universal hard validity boundary for every real driver.

Loading (`Re z`, LFP, hold) is not the same as electroacoustic efficiency, sound power, sensitivity at specified electrical drive, maximum SPL or distortion. On-axis flatness is not power-response flatness. Those require their own complete inputs/model and validation. Raw J and a two-axis coverage/ripple frontier are not an overall loudspeaker-quality certificate.

## 3. Useful interaction analysis, with limits

Start with actual paired design examples and physical-geometry effects, then held-out acoustic associations and exact score decomposition. Show which variables changed together in the archive, what the constructed shape did, which frequency regions changed and which objective terms moved.

The tree diagnostic uses **prespecified normalized steps 0.025, 0.05 and 0.10**; these are finite perturbations, not derivatives. For each pair and anchor, report legal endpoints, geometry changes, 4-point distance/support, the relevant 2D projected coverage, and contributing independent groups. Near-neighbor radius is a diagnostic, not a support certificate. Boundary-truncated anchors are counted/excluded explicitly. Never cross a categorical/conditional branch and interpret it as one smooth interaction.

Do not rank from one step alone. Compare median absolute nonadditivity, sign distribution and pair-order stability across the steps and fold/group fits. Suppress a recommendation when support is weak, the model fails held-out baseline comparison, rankings are step-dependent, or a synthetic additive/correlated test produces misleading interactions. Counts such as 100 rows, five groups and 20 anchors are screening policies, not power or validity proofs. Twenty anchors from one trajectory are not twenty independent studies.

The result is a **hypothesis card**, not an automatic hard link or pin. A useful next experiment compares a legal four-design 2×2 parameter rectangle under the same physical source/spec, with enough numerical resolution to separate response differences from mesh/grid error. Repeat at another supported anchor when seeking a broader rule. Known no-op/conditionally inactive controls and coupled-geometry constraints are explicit negative tests.

Primary methodological grounding: [scikit-learn on correlated permutation importance](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html), [Apley–Zhu effect-plot limitations](https://arxiv.org/abs/1612.08468), and [SciPy space-filling design documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html). None makes adaptive archive associations causal.

## 4. Reusable data is the foundation, across scoring configurations

The owner's explicit priority is reusable data that survives different scoring configurations. Make this a required M0/M1 deliverable within the existing plan, not another architecture:

* **Physical solve identity:** immutable geometry/source/boundary/mesh/frequency/observation/backend/producer inputs and raw response/artifact hashes. Preserve original runs/dataset/cache and their uncertainty/completeness.
* **Derived metric identity:** the physical response plus target/coverage/band/frequency weighting/normalization conventions, metric code and required inputs. Some metrics depend on the target; stored metrics are not universally scoring-independent.
* **Score identity:** derived inputs plus exact version/weights/tolerances/gates/brief/code. One compatible physical solve can support several immutable metric/score tables. A score change does not overwrite the original.

First replay original scoring from preserved raw data. Then change weights/tolerances and, where data supports it, coverage/band/target; regenerate target-dependent ripple/masks/normalization instead of only reweighting stored terms. Assert **zero backend calls and no historical artifact mutation**. Output exact-complete, partial/unsupported, or additional-data/solve-required with per-row reasons. A missing gate/input is never a pass; incomplete scores cannot rank beside complete ones as equivalents. Existing v1–v7 scorer dispatch and offline tools are reused; v8 remains an explicit research scorer until separately registered.

Record replay parity and physical completeness separately: reproducing a historical scorer that dropped missing bins is not proof of complete modern input support. Require each metric's declared common intended masks/weights across compared designs, or an identical predeclared restricted mask with distinct identity/partial status. Reject silent per-design finite filtering, invalid-weight fallback and mixed ripple-definition fallback.

| Requested change | Reuse policy |
|---|---|
| Weights/tolerances or supported scoring version | Reuse raw physics if required inputs exist; create a new score identity |
| Target coverage/band/frequency weights | Rebuild affected metrics from supported stored angles/frequencies and exact conventions; no imaginary samples |
| Denser frequency grid or converged/finer mesh | Existing data cannot prove the new solve; mark additional solves required |
| New observation angles/distances at an already solved frequency | Stored boundary traces and geometry may support field re-evaluation on some records; audit capability, do not promise universal support or universally require a new BEM solve |
| Source/driver/mounting/material changes | Compare actual physical inputs; a mere label change is not new physics, but changed excitation/boundaries usually need a new solve unless an exact recorded linear multi-source basis supports re-synthesis |
| New loading/throat/diagonal/MEH terms | Require actual impedance, driven-plane/geometry, balloon/channel/network inputs respectively; refuse incomplete reconstruction |

The supplied external assessments were treated as leads. Local source confirms `surrogate/predict.py:7,84,93,110` and `surrogate/train.py:9,71` use the original scalar scorer and a predicted MetricSet without throat impedance; the inspected CLI's guards check bundle/config geometry/grid and gate report, not a complete newer objective input contract. This is a **source-level scoring-compatibility gap**, not measured performance loss. Before comparing this existing surrogate to BoTorch, add explicit supported-version/input capabilities and either share a correctly version-aware pure scorer adapter or refuse unsupported newer objectives. Do not fabricate predicted impedance or assume six output curves support all v6/v7 gates. Newer generator knob provenance does exist; census coverage rather than rewriting on the premise it is all lost.

Preservation audit includes `dataset`, `dataset_cpu`, both solve-cache roots, run/config/provenance, required meshes and sampled traces, with hashes, recoverability and a bounded temporary restore/replay test. Static `tools/hf_sync.py` inspection shows its `push` default groups are text/dataset and its solve-group collector reads `cache/solve`; CPU-root and additional geometry coverage need explicit inventory. **No remote-backup staleness was verified here.** Uploads/remote operations/default backup changes are separate execution actions; a timestamp is not a successful restore test.

## 5. Inclusive implementation order: foundations, BoTorch, integration

### M0 — read-only task/parameter/evidence audit

Owners: S0/R0 + B2, parent freezes schema/semantics. Deliver preservation/zero-solve rescoring capabilities above and inventory a real candidate cohort: complete target/source/fidelity/software identity, actual unique controls, approximate geometry equivalence, successful solves, independent experiments, missing arrays and failures by type. ATH is a candidate, not assumed to have enough compatible data. If it fails, parent selects an evidenced existing task without weakening compatibility. BoTorch code/fixture work may proceed in parallel after its input/scoring contract is frozen; inadequate archival data is not a reason to delete that workstream.

Add parameter activity and geometry bridge tools as proposed `tools/analysis/parameter_activity.py` and `geometry_effects.py`, using existing parameter/geometry authorities. No default config, cache, dataset writer, job manager or GUI launch changes. Tests: target-1 exponent invariance/target-3 activity; stretch conditionality; H/V symmetry exchange where appropriate; diagonal contour changes; units/scale; pure surface versus hash equivalence; missing or unsupported geometry.

### M1 — first useful owner-facing result

Owners: S3/S4/S6 plus a small existing analysis-view extension. Deliver an immutable JSON/MD/HTML report with **3–5 actual selectable designs** from a compatible cohort, tracing knobs → geometry → measured per-band acoustics → exact frozen J contributions. Show no-op/conditional controls, source-model bands, crossings/DI/loading context, score-versus-physics distinctions, exclusions and grouped validation. Return `insufficient_evidence` honestly where needed.

Serve it through the existing analysis/report route and existing run/design/verify links. Add a dedicated renderer only for the agreed artifact schema. No new persistent DB, job framework or adaptive runner is required. Existing exports and analysis continue to work. The full Design Study GUI remains the target experience but is introduced incrementally from this report.

The first GUI interaction is concrete: select a control, see its context/units/activity predicate, highlight the affected regions of an existing geometry preview, then select real example designs and compare measured curves and score terms. A two-control view shows supported combinations and which geometry changes coincide. Reuse the existing sandbox/inspector where available; no slider creates a measured response or starts a solve. Distinguish deterministic construction relationships from observed acoustic associations in labels and diagrams.

### M2 — advisory BoTorch comparison

Owner: B3 with B2, parent reviews diagnostics. Prepare candidate artifacts only, under the activity-aware mapping and unchanged physical/scoring task. Check pool novelty, cheaply rejected fraction, unsupported physics, train/holdout quality, fit/acquisition overhead, pool-seed sensitivity and subset/regularization sensitivity. Compare with legal space-filling and existing CMA/seed proposals, not only another sophisticated model.

Initial recipe constants remain fixed for implementation; assess prespecified diagnostics rather than letting workers optimize their own recipe. Retrospective prediction/ranking is off-policy evidence. Candidates say **cheap checks passed; mesh/acoustic eligibility unknown** until evaluated. Optional different physical policies are new study revisions, not silent default substitutions.

Gate to prospective pilot: reproducible candidates, credible data/geometry mapping, informative diagnostics and no runtime regressions. Prepare an equal-cost pilot with the existing serial tools and explicit approval/scheduling; no new adaptive runner is needed just to test one small proposal batch.

### M3 — full planned integration after foundation/interface checks

After M0–M2 interfaces and correctness gates, implement the planned persistent workflow/job bridge, adaptive serial loop and richer GUI workspace in separate slices. This remains full-plan scope; it is sequenced after the foundation, not discarded or contingent on proving a BO win before integration code exists. Pareto, constraints, cost-aware acquisition and trust-region variants retain their planned interfaces/tests and separate integration gates. Preserve schema/physics/lane/crash rules. Real solves, production activation and claims of improvement still require scheduled pilot evidence. True multi-fidelity GP/KG and new solver architectures need their own locked method design before activation.

The orchestrator records each phase's evidence and continues through the authorized offline implementation when dependency gates pass; it must not declare the whole task complete at M1/M2 or silently drop BoTorch. If real data is insufficient, continue fixture/API implementation while exposing that limitation. Actual solve/adoption gates remain separate. Offline work must not disturb running solves.

## 6. Compatibility and ranking guardrails

* **No production cache enforcement in M0–M2.** S2 first reports producer/source risks. A later opt-in producer guard needs a legacy-hit inventory, measured reuse impact, call-site tests and rollback. Do not invalidate the historical archive by default.
* **No search or objective default changes.** CMA/QD correctness fixes are isolated reviewed patches; QD-specific defects do not block read-only native analysis or ordinary seed reports. A new optional module must not import BoTorch on normal GUI/CMA startup.
* **Coverage convention is explicit.** Build raw helper params from the resolved brief's supported `cov_narrow_ratio`, `cov_below_f0` and `diag_reference`, with declared helper tolerances used only to satisfy its raw API. For the candidate ATH task, ratio is **2**, not the `for_class("A")` default 1. Exact band/frequency weighting and detrended-ripple branch are frozen in the metric hash. Unsupported conventions refuse instead of silently falling back.
* **Preserve an acoustic context card around a Pareto view.** Show DI source/variation, multilobes/crossings, on-axis response, loading where measurable, physical size/source assumptions and verification status. A nondominated coverage/ripple point can still be undesirable. Missing context is not a gate pass. Do not invent new hard cutoffs; review acceptability under the existing brief and measured curves.
* **GP subset stability is measured.** Initial elite/diversity selection is an approximation. For an adaptive extension, retain all new eligible study observations until capacity; then reserve the latest `min(64,n_new)` plus the best 64 eligible scalar observations (or specified Pareto elites), deduplicate, and maximin-fill remaining capacity. Publish exact additions/evictions and compare diagnostics to the all-data fit when tractable. A changed subset is not an independent experiment.
* **Research limitations stay visible.** No BEM solve, full mesh convergence, real driver validation or closed-loop BO speed benchmark ran in this hardening pass. Pure installed contour behavior was checked; source/metric claims were inspected, not a measured new horn result.

## 7. Primary horn-design basis

[Batík's OS-SE construction paper](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) supports distinguishing the base profile, added termination and later morph rather than treating nominal controls as independent acoustic axes. Its construction is a geometry model, not a guarantee of a realized beamwidth.

[Wadbro et al.'s horn–lens optimization preprint](https://people.cs.umu.se/martinb/downloads/Papers/WaUdBe10_preprint.pdf) treats radiation/transmission and directional behavior as separate objectives with trade-offs in a specified model; its simplified geometry does not transfer a quantitative gain to our 3D stack. [COMSOL's primary horn-optimization example](https://doc.comsol.com/6.3/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html) explicitly demonstrates that an improved on-axis objective can create undesirable off-axis minima. This supports keeping frequency/angle context around scores rather than maximizing one attractive summary.

Existing local grounding remains `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md`, the mesher/pinned source, parameter SSOT and the resolved brief. New typology laws still follow the existing typology-research protocol and reference-case tests. No new named construction or changed acoustic priority was implemented here.

**Highest-value first deliverable:** an existing-GUI report that lets the owner inspect a real shape change, the measured response it changed, the score term responsible, and a testable next idea. BoTorch then helps choose the next useful experiment, while the existing software remains operational.

## 8. Refusals and errors: protect learning without narrowing the horn box

**Integrated review of the owner's refusal handoff.** Source: `C:/Users/hunte/Hrns/oc-wt/REF/docs/research/REFUSALS_AND_OPTIMIZER_HANDOFF_2026-11-12.md`, branch `docs/refusals-handoff-2026-11-12` at `0133772`; inspected search code in DOCS `4910c64` matches the relevant paths in local `origin/main=5f7c116`. PR state was not refreshed through GitHub. Existing refusal/valid-budget behavior was already partly in the plan; this section fixes overclaims and makes implementation/test ownership explicit. BoTorch and reusable rescoring remain fully included.

### 8.1 What the supplied research gets right, and what needs correction

* Plain CMA supports `search.infeasible_penalty: resample` and `budget_counts: valid`; `max_attempts` is a separate ceiling. `budget_counts: valid` alone does not remove penalties from `tell`.
* **Current resample does not guarantee “never told.”** In both serial/prefetch branches, `cma.py:573`–`:599` performs up to ten replacements, then appends the final objective and can call `tell`. `test_all_refusing_box_resamples_the_cap_and_still_tells_the_penalty` deliberately covers this. The test named `test_refusals_are_logged_but_every_told_candidate_is_valid` only checks that the selected best belongs to an ok row; it does not spy on `tell`. Strengthen the tests rather than trusting the name or module comments.
* “Free” means **not charged to the valid-evaluation counter**, not free CPU, mesh, worker, energy or wall time. `max_attempts: 600` is an explicit cap; the implicit cap is 4×budget only when the field is absent in valid mode. The actual algorithm token is `cma`, not `plain`.
* Existing `budget_count` increments valid when `ev.error` is empty; solve/metric failures do not consume this valid count, contrary to a nearby comment, but do consume new-attempt caps. A measured gate refusal may have no error and therefore is not automatically excluded by this counter. Keep successful solve, usable measurement, objective eligibility and budget policy separate.
* CMA-ME rejects `resample` at config load. Its scheduler binds emitted vectors/order/count to its tell data. Simply filtering rows, replacing public arrays after `ask`, using fake descriptors, or calling `ask` again is not a valid supported equivalent. Any true feasible-only QD change needs emitter/scheduler semantics and archive mapping designed together.
* The observed archive has no penalty cells, but that is **one run's result**, not universal archive protection. Previous S1 findings still apply: an empty fallback cell can admit failures under ordinary ME, and an unsafe MAE threshold can admit them too. MAE threshold updates do not isolate the emitter from invalid ranks or infrastructure failures.

Verification run in this review, no real BEM: all **17 existing resample/budget tests passed**. A second, in-memory spy around the existing all-refusing test observed:

```json
{"pytest_exit": 0, "tell_calls": [{"n_told": 4, "penalty_1000_count": 4}], "scope": "synthetic_backend_existing_test_no_real_solve"}
```

Command for the existing tests: project Python `-B -m pytest tests/test_search_resample.py tests/test_search_budget_counts.py -q -p no:cacheprovider`, from DOCS. The spy changed only that subprocess's in-memory method and used the test's temporary synthetic artifacts. No installed/source code or live data was patched.

### 8.2 Outcome classification: different events need different treatment

| Outcome | Optimizer treatment under the new opt-in strict policy | Data/analysis treatment |
|---|---|---|
| Deterministically invalid geometry | Bounded replace from current CMA distribution; no fake acoustic score sent to strict CMA | Preserve provenance/condition and negative geometry label only where established |
| Actual brief-envelope violation | Same bounded refusal handling; no automatic box narrowing | Brief-dependent constraint label; optional graded violation is a distinct declared policy, not an acoustic measurement |
| `mesh_too_large` / dof budget | Resource rejection under current mesh/backend/cap; bounded replace or stop | Resource/cap-censored label, not proof the horn is physically bad; retain for later larger-cap/backend studies |
| Transient `solve_failed` / worker crash | Retry the **same exact candidate/spec** within a fixed cap; no new ask, fake J or tell; stop resumably if unresolved | Infrastructure event and actual compute cost, not negative geometry/acoustic feasibility |
| `metrics_failed`, generic exception or unclassified error | Stop resumably with diagnostics by default; no blind resampling or fabricated score | Unknown/pipeline failure, excluded from feasibility training until its cause is established |
| Measured acoustic gate failure | Apply the explicit brief's existing constraint/score policy; it is real physical information, not an infrastructure error | Preserve available raw response and signed gate margins. A changed scoring brief may reuse it. No missing-gate pass |
| Successful complete score | Normal tell/model update under selected policy | Eligible measured response/score variant with full identity |
| Cache/memo result | Reuse only under established identity; retain truthful counters | Not an independent new solve; deterministic cached refusals still consume sampling effort and strict draw cap |

Existing `to_training_arrays` excludes `solve_failed` by prefix when failures are included; this alone does not prove generic exceptions/metric failures are safe invalid labels. Add typed analysis/training views, not a rewrite of historical rows. A classifier for geometry feasibility, a predictor of resource fit and a model of acoustic gate margins are different tools.

### 8.3 F0: small strict plain-CMA/infrastructure slice

Keep existing flat/graded/resample defaults and old resume behavior unchanged. Add **proposed, not yet implemented** `search.infeasible_penalty: resample_strict` for plain `cma`, and shared optional **`search.error_policy: retry_same_then_stop`** (absent/default `legacy`). Strict mode requires that error policy plus `budget_counts: valid`; reject contradictory configurations. QD can opt into the error policy without pretending to support deterministic resampling. These are planned schema additions, not usable flags today. Parent-frozen contract:

1. Maintain the current bounds and normalized transforms. For each generation slot, try the asked vector, then at most **ten** replacement draws from the same current CMA distribution for deterministic refusals. Never return a deterministic-refusal penalty to strict `tell`.
2. If the slot still refuses, any total draw/attempt/deadline cap is exhausted, or an unknown error occurs, stop with an explicit resumable reason and **do not tell the incomplete/contaminated generation**. Retain the valid partial observations/pending state so resume can reconstruct it. Do not “complete” a batch with penalties, duplicates, invented values or silently widened/narrowed bounds.

   A fully completed eligible batch can be told once and checkpointed before a cap stop, provided no unresolved/in-flight error remains. The forbidden case is a refusal/error-filled or partial batch that merely has enough placeholder entries. Test the cap landing on the final valid slot separately from the final refused slot.
3. A transient solve failure gets at most **two total backend attempts for that same candidate/spec**, counting the first call. Retry only when the classified condition is eligible and own-lane recovery is safe. Do not ask a new vector, alter physical settings, permanently cache the transient failure or update CMA between attempts. On failure exhaustion stop resumably before `tell`; legacy global unhealthy-host protection remains an additional safety limit.
4. Bound sampling, including cached refusals: in strict mode enforce a total candidate-draw cap equal to the resolved `max_attempts` (or the current valid-mode 4×budget default), in addition to existing counters and per-slot replacement cap. Count the seed once; retries are backend attempts, not new draws. Reject an unbounded strict policy if no draw cap/deadline can be resolved. Do not silently change legacy max-attempt semantics outside this new opt-in mode.
5. Record proposed/drawn/replaced/refused/cached/scored/told counts, actual BEM calls/retries, elapsed cost, eligibility and stop reason. Existing `valid` counting is not a speed claim or proof that every budgeted row satisfies acoustic gates. All positive and negative raw evidence remains preserved.
6. Mark resume protocol and completed/partial-generation boundaries explicitly. Reproduce candidate/tell sequences for strict serial/prefetch and interrupted/resumed runs; refuse unsupported strict+LQ/restart combinations until tests establish chronology. This changes behavior only when opted in; a new enum must pass config validation before any command is documented as usable.

Strict tell eligibility is explicit: an error-free, complete canonical score is allowed, **including a deliberately configured acoustic-gate penalty when the gate is fully measured**. That is the real declared constrained objective. Missing gate inputs, fabricated infrastructure penalties and deterministic geometry/resource refusal scores are not eligible. Decide by typed status, score capability and terms, never `J>=1000`. BO regression may exclude the same measured gate penalty from its acoustic GP while retaining its constraint margins; that does not contradict the optimizer's declared score policy.

An invalid deterministic seed remains the recorded failed baseline and cannot become “best valid horn”; do not secretly substitute a different baseline. If configuration/materialization permits a search distribution, bounded generation sampling may continue without telling the baseline failure. If space construction itself fails, report the config error. A seed's transient failure uses the same exact-candidate retry/stop rules.

Checkpoint generation state/RNG, generation+slot/order, original/replacement vectors, observation IDs, pending/unknown attempts, all counters and pinned code/spec identity atomically before any irreversible dispatch boundary (or use a tested generation-boundary snapshot plus durable event journal that reconstructs the same state). Capture every RNG stream used; a serialized ES alone may not capture external/global RNG state. Use supported trusted local state serialization/replay; never pickle live backend/worker objects. Reserve actual backend-attempt capacity **after a cache miss but before the call**. Unknown dispatches conservatively retain that reservation and cannot trigger an automatic third call. Resume reconciles first, preserves cumulative strict caps unless an explicit budget extension is recorded, and refuses incompatible protocol/spec/code. Prefetch work already started is counted and cancelled/drained/reconciled on stop; no additional solve dispatch or tell may occur afterward.

Use actual `tell` spies with candidate hashes/statuses: ordinary intermittent refusal, all-refusing box, refusal cap on the final batch slot, attempt/deadline mid-batch, cached refusal loop, transient failure then success, persistent infrastructure error, metric exception, valid J equal/above 1000, measured gate refusal, seed failure, prefetch and resume. Assert the state/covariance is untouched when no complete eligible batch was told. Compare a healthy run with one injected transient failure: the successful told vectors/scores should match under the same seed/protocol, though time/call counts differ. Do not claim rejection sampling preserves an unconditioned CMA trajectory.

This is a small additive correctness option, not a new optimizer framework. Implement F0 beside the shared classification/rescoring foundation, with exact ownership separate from B3's BO files. Default flips and live-queue edits are outside this review.

### 8.4 F1: QD archive safety and infrastructure isolation, then explicit constrained-QD design

Extend S1's warm-start/archive invariants with actual failure exclusion for both ME and MAE, covering scheduler **search and result archives**. Unknown descriptors cannot masquerade as measured seed/corner descriptors. Preserve emitted order/count/vector→evaluation→hash mapping and genuine successful scores. Invalid archive-admission feedback may change when corrected; do not promise identical emitter ranks/trajectory or assume an archive-only filter gives isolation. Parent must approve the archive/add-info/emitter contract together; if supported APIs cannot express it, return unsupported for the senior adapter design rather than mutate scheduler internals or silently drop rows.

First isolate transient/unknown infrastructure errors before `scheduler.tell` through the proposed shared error policy: same-candidate bounded retry/stop, full batch/scheduler/emitter/RNG checkpoint or verified replay, and reconciliation of unknown attempts/prefetch. Never resume with a fresh `ask` over unresolved state. For deterministic geometry/resource refusals, **v1 QD retains an explicitly disclosed legacy penalty/emitter policy** until a separately opt-in constrained-emitter adapter is designed. It must never advertise feasible-only trajectory isolation. Archive corrections and any changed admission/rank feedback are explicit correctness changes, not proof that the ES update formula has become constraint-aware.

A subsequent senior-designed adapter must prove final accepted solutions are registered consistently with the scheduler and underlying ES, bounded replacement/cap behavior, valid parent weighting and restart behavior, replay, result-archive safety and all-invalid handling against installed ribs 0.12.0. Use supported APIs or a separately reviewed pinned fork; no private-state mutation or hand-written ES. A thin filter/wrapper alone is not assumed sufficient. No fake NaN/Infinity objective or descriptor hack. Benchmark any changed algorithm against the existing wide-box QD baseline at matched total cost before adopting it.

### 8.5 No hidden narrowing, and no loss of reusable failure evidence

Resampling leaves configured bounds intact but samples the distribution **conditioned on acceptance**, advances RNG draws and can concentrate near feasibility boundaries. It is not trajectory-neutral. Report acceptance by region, repeated failures, boundary mass and resource exclusion. Keep a wide-box control and compare verified quality per total wall/BEM cost. Use exact cheap prechecks for known invalid constructions; uncertain geometric/resource heuristics return “needs mesh/check”, not new undocumented hard horn limits. Do not use `narrow` to hide refusals. A legitimate broad-envelope improvement and a matched-size shape study remain different tasks.

A bounded census during this pass observed main dataset **28,575 records: 23,941 ok, 4,634 failed**; CPU **237: 221 ok, 16 failed**. Counts can advance: the handoff's 28,573 is a prior snapshot, not a contradiction. The existing shards did not change during this read, but this was not an atomic writer snapshot. Main failures split into 3,079 invalid geometry, 553 envelope, 882 mesh-budget, 57 solve failures and 63 generic exceptions; none should be collapsed into one acoustic-loss class.

The archived `fbab4f` check reproduced **1001 rows: 567 ok, 327 invalid geometry, 106 mesh too large, 1 solve failed**. Its archive had **17 cells and zero recorded J>=1000 cells**. This supports the handoff's observation for that archive only.

D.3's `plan_merge` filters CPU backend and duplicates, **not ok status**. Preserve both successful responses and failure metadata by default in the provenance-aware raw archive; provide separate explicit complete-acoustic, physical-constraint, resource-censored and infrastructure views. Do not pre-filter/delete failed source rows merely to obtain a clean training table. Failed metadata is not acoustic arrays; infrastructure failures are not constraint labels. Parity checks use matched successful measurements and do not validate failure labels. Any apply remains a separate reviewed action; none was run here.

GUI: show sampling rejection, geometric/brief constraint, resource cap, measured acoustic gate and infrastructure issue separately, with actual time/attempt/BEM/retry costs. “Excluded from learning” does not mean “not saved” or “free”. Display the engine's actual policy: legacy penalty, capped resampling with fallback, strict resampling, or QD legacy-emitter handling. BoTorch uses the same classification to avoid training J=1000 as an acoustic observation; failure data does not disappear from the reusable archive.

Primary API grounding: [pycma feasibility/rejection options](https://cma-es.github.io/apidocs-pycma/cma.options_parameters.html), [Hansen's CMA tutorial](https://www.cmap.polytechnique.fr/~nikolaus.hansen/cmatutorial), and [pyribs scheduler source](https://docs.pyribs.org/en/stable/_modules/ribs/schedulers/_scheduler.html) / [emitter API](https://docs.pyribs.org/en/stable/api/ribs.emitters.EvolutionStrategyEmitter.html). These support the interface/conditioning concerns; the strict recovery/cap choices above are explicit HornLab engineering policy to test, not published performance guarantees.
