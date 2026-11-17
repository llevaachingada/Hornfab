# EVIDENCE LEDGER — atomic, status-labelled findings

Snapshot: `C:\Users\hunte\Hrns\hornlab-search`, `main` @
`601be8ceeb48f1750bb4f3f6c1fdc682967c8b94`, observed 2026-11-16T20:43:51-05:00.
All `path:line` citations below are committed content at that SHA unless marked **worktree**.
Status vocabulary: **directly verified** (source/config read), **historical run record**
(dated report/number, not re-run), **reproduction** (recomputed from extant run artifacts),
**plausible inference**, **unverified**, **contradicted**.

---

## A. State of the repository

### E-001: The research target is not the handoff's pinned `main`
- **Status:** directly verified
- **Claim:** local `main` is 11 commits ahead of `origin/main = 2c0e2928…`; the handoff's
  "remote main" snapshot does not describe the checkout.
- **Evidence:** `git rev-parse HEAD` = `601be8c…`; `git rev-parse origin/main` =
  `2c0e2928…`; `git log --oneline 2c0e2928..HEAD` = 11 commits, 2026-11-16 19:20–20:34.
- **Counterevidence / limits:** `origin/main` is the last-fetched ref; a real remote may have
  moved if the concurrent lane pushed. No network fetch was performed (read-only rule).
- **Implication (interpretation):** every "current" claim in the handoff must be re-checked
  against `601be8c`, not `2c0e2928`.

### E-002: Two development lanes overlap in time and file scope
- **Status:** directly verified
- **Claim:** another lane committed 11 times and left 35 working-tree entries during the pass
  (19 modified, 16 untracked); a `julia` solve host and a night queue were live.
- **Evidence:** `git log`, `git status --porcelain`, `Get-Process julia` (PID 37208, 20:07),
  `runs/` activity. None of it was touched.
- **Counterevidence / limits:** process inspection cannot prove which run the Julia host serves.
- **Follow-up:** re-snapshot before any later decision; this dossier is timestamped evidence.

### E-003: The scratch dossier is genuinely outside version control
- **Status:** directly verified
- **Claim:** `scratch/fable_architecture/` is ignored by `.gitignore:9 (/scratch/)`.
- **Evidence:** `git check-ignore -v scratch/fable_architecture/INDEX.md` → match.
- **Implication:** the dossier can be written without dirtying the tracked tree.

---

## B. Geometry, families, parameters

### E-004: The number of distinct geometry engines is small
- **Status:** directly verified
- **Claim:** the real engines are OSSE, R-OSSE, ICW, native FREEFORM, the point-grid (GRID/rows)
  builder and CAD STEP; classical/hybrid names are meridian laws, presets, carriers or
  compositions that materialize into one FREEFORM body.
- **Evidence:** `design/families.py:211-265,519-561`; `design/generators/registry.py:168-228,
  242-345`; `design/generators/grid.py:1-48,488-642`; `mesh/build.py:351-360`;
  `mesh/step_build.py:87-140`.
- **Counterevidence / limits:** rolled-family and KlangFilm bodies are explicit kernels, not
  merely meridian laws; mechanical multi-entry is a CAD topology.
- **Implication (interpretation):** a "universal typology" would not add engines; it would add
  a taxonomy over existing ones.

### E-005: Several catalogue "families" are the same construction under another name/option
- **Status:** directly verified
- **Claim:** `spherical_wave` is literally `lecleach(T=1.0)`; `salmon_axisym` is
  `salmon_elliptical` with `fc = fc_h`; generator `osse` resamples the native OSSE formula;
  `lecleach_mod` with zero harmonics equals `lecleach`.
- **Evidence:** `generators/profiles.py:613-618`; `generators/grid.py:2380-2382`,
  `1146-1157`; `generators/registry.py:127-139`.
- **Counterevidence / limits:** the rows carrier changes meshing/rollback capability even when
  the law is the same; equivalence is not "same acoustic surface".

### E-006: Several catalogue entries differ only by brief/objective/bounds
- **Status:** directly verified
- **Claim:** `native__ath_core_v4` and `native__ath_core_2in_v5` have the same seed and bounds;
  only the brief/objective version and name differ.
- **Evidence:** `examples/typologies/data_2026-10-29_v5/native__ath_core_2in_v5.yaml:1-3`
  (file states it).
- **Implication (interpretation):** catalogue cells are not a taxonomy of physics; grouping them
  as families inflates apparent diversity.

### E-007: Categorical controls are forced through continuous boxes or cannot be searched
- **Status:** directly verified
- **Claim:** `morph_target` is an int KeySpec searched as a rounded continuous box; ICW
  `termination` is a string and cannot carry bounds, so it is never searched.
- **Evidence:** `design/families.py:73,238-239`; `design/space.py:148-152`.
- **Counterevidence / limits:** integer rounding makes the value discrete, but CMA's internal
  representation and step-size still treat it as continuous.
- **Follow-up:** a mixed/categorical encoding is not implemented anywhere in `bo/encoding.py`
  (see E-031).

### E-008: Some "independent" knobs are coupled or inactive by predicate
- **Status:** directly verified
- **Claim:** an active guiding curve replaces `a_deg`; `s1`/`s2` are no-ops unless both are
  nonzero; `n`/`q` are ignored at `s=0`; `rot_deg` couples radius and depth; `morph_exponent`
  is a proven no-op at `morph_target=1`.
- **Evidence:** `generators/profiles` via `profile_formulas.py:389-393`; `families.py:56-59,
  435-443`; `families.py:216`; `tools/analysis/parameter_activity.py:586-606`.
- **Counterevidence / limits:** the no-op proof is for one ATH target/brief; it is not general.

### E-009: Generator modularity does not reach the meshed surface as advertised
- **Status:** directly verified
- **Claim:** the generator emits exactly two cross-section stations (`t=0` circle, `t=1` mouth
  shape); arbitrary station stacks exist only in native FREEFORM. The "FREEFORM refuses
  morph + non-elliptical station" rule is a search-layer policy, not a mesher refusal.
- **Evidence:** `design/generators/registry.py:315-332`; mesher `freeform.py:1874-1903`
  (cited in A's report); `families.py:519-561`.
- **Implication (interpretation):** "composable in YAML" ≠ "composable after meshing".

### E-010: `search.links` cannot be used with generator families
- **Status:** directly verified
- **Claim:** `reduce_space` raises `ValueError("search.links is not supported with a generator
  block")`, so the H5 remedy "couple length/lip/wrap with links" is blocked for exactly the
  grid/rolled/KlangFilm families where it was proposed.
- **Evidence:** `hornlab_search/search/links.py:36-37`; `docs/queue/HOME_18H_PLAN_2026-11-16.md:
  135-136` (proposal).
- **Counterevidence / limits:** native OSSE/R-OSSE/ICW/FREEFORM do support links.
- **Follow-up:** a generator-aware link schema is proposed in B's §7, not implemented.

### E-011: Existing analyzers already cover most of the "activity" vocabulary — with refusals
- **Status:** directly verified
- **Claim:** `parameter_activity.py` is native-only and can prove one no-op; `geometry_effects.py`
  refuses CAD/point-grid and non-star-shaped surfaces; `geometry_descriptors.py` refuses MEH,
  mid-ports, CAD and grid; `tools/analysis/links.py` is statistical co-movement, not physics.
- **Evidence:** `tools/analysis/parameter_activity.py:512-519,586-606,636-641`;
  `tools/analysis/geometry_effects.py:14-15,104-124`; `tools/analysis/geometry_descriptors.py:
  112-127`; `tools/analysis/links.py:1-11,52-53`.
- **Implication (interpretation):** new tooling should extend these, not duplicate them.

### E-012: A latent ordering hazard exists in the mounting route
- **Status:** plausible inference (code read, no shipped config exercises it)
- **Claim:** `to_mesher_config` forces `mode="enclosure"` and then copies top-level design keys,
  so a design carrying a `mode` key could overwrite the enclosure flip while the enclosure
  section remains.
- **Evidence:** `design/families.py:696-710`; no `examples/` config sets top-level `mode`.
- **Counterevidence / limits:** latent only; no observed failure.

### E-013: The handoff's grid.py line numbers are stale
- **Status:** contradicted
- **Claim:** `design/generators/grid.py` is 3020 lines at snapshot, not the 2813 stated in the
  v3 dispatch (the earlier figure came from a blank-line-skipping line count).
- **Evidence:** `(Get-Content grid.py).Count` = 3020; `def envelope_extents` at L2989.
- **Implication:** cite function names + observed lines, not the handoff's line numbers.

---

## C. Failures, boundaries, size

### E-014: The live 2026-11-16 boundary is geometry/envelope, not GPU
- **Status:** reproduction (extant NDJSON parsed)
- **Claim:** in 53 runs on 2026-11-16: 2,538 attempts, 2,288 `ok`, 2,249 complete non-cached
  BEM solves (88.6 %), 81 pre-mesh `invalid_envelope`, 169 `invalid_geometry`, **0**
  `mesh_too_large`, **0** `solve_failed`/`metrics_failed`/`exception`.
- **Evidence:** `runs/20261116*/search.ndjson`; parser
  `scratch/fable_architecture/.tmp/agg_20261116.py`, outputs `run_scan.json`,
  `run_agg_by_config.json`.
- **Counterevidence / limits:** "complete BEM" is `ok AND !cached`; it does not mean verified or
  acoustically good. The window is one brief.
- **Implication (interpretation):** a GPU-limit narrative is not supported by this window.

### E-015: Post-mesh envelope refusals are coded as `invalid_geometry`
- **Status:** directly verified
- **Claim:** the post-mesh envelope check returns `KIND_INVALID` (`invalid_geometry`), while only
  the pre-mesh generator estimate is `invalid_envelope`.
- **Evidence:** `search/evaluate.py:278-295` (message), `:1580` (kind assignment);
  `search/outcomes.py:114-119` (classifier follows the kind token).
- **Counterevidence / limits:** `evaluate.py:1219` and `:1440` also assign `KIND_INVALID` at other
  stages; the taxonomy is route-dependent.
- **Implication (interpretation):** any "geometry failure rate" that reads the `kind` token
  over-counts geometry and under-counts envelope.

### E-016: Family `GeneratorError` text `invalid_envelope` is mapped to geometry
- **Status:** directly verified
- **Claim:** the mapper tests `gerr.startswith("invalid_envelope")`, but a family error string is
  prefixed (`"GeneratorError: invalid_envelope: …"`), so it fails the test and becomes
  `invalid_geometry`.
- **Evidence:** `search/evaluate.py:1546`; run `20261116T222251Z-screen-91ddfb`
  (`k_lame_E3_s11041`) shows the prefixed message.
- **Counterevidence / limits:** native pre-mesh errors are produced without the prefix and are
  classified correctly.
- **Follow-up:** prefix-agnostic parsing + a regression fixture.

### E-017: The graded infeasibility penalty is unreachable for native families
- **Status:** directly verified
- **Claim:** the graded branch requires `kind == invalid_envelope` **and** a stored
  `_generator_overshoot`; native envelope refusals are `invalid_geometry` and carry no overshoot,
  so they always receive the flat `1e3`.
- **Evidence:** `search/evaluate.py:1046-1052`; `objective/terms.py:18-19,101-115`;
  `design/generated.py:31-35`; `docs/queue/HOME_18H_PLAN_2026-11-16.md:132-134` (prior claim,
  now confirmed).
- **Counterevidence / limits:** generated FREEFORM designs can reach the graded branch.
- **Implication (interpretation):** "graded penalty" is a generated-FREEFORM feature, not a
  general constraint signal.

### E-018: The generic GRID pre-mesh estimate is conservative on both axes
- **Status:** directly verified (code); realised false refusals **unverified**
- **Claim:** the generic radial-grid `envelope_extents` takes `max(radius)` over φ and reports
  `W = H = 2(max radius + wall)`, so an asymmetric section's smaller axis is over-reported; the
  estimate becomes a hard pre-mesh refusal when positive.
- **Evidence:** `design/generators/grid.py:2989-3020` (verified at L3015-3020); dispatch to
  family/rows routes at `:2997-3006`; `design/generators/registry.py:404-428`;
  `design/generated.py:210-221`.
- **Counterevidence / limits:** rows route uses per-azimuth cos/sin widths
  (`grid.py:2817-2842`); generated FREEFORM uses per-plane maxima (`registry.py:478-479`);
  family routes use per-plane meta (`grid.py:3000-3002`). Only the generic grid branch is
  conservative. No measurement in this pass shows a realised false refusal.
- **Follow-up:** the exact CPU surface-vs-mesh check is specified in
  `SIZE_FEASIBILITY_EVIDENCE.md` §7; it was **not run**.

### E-019: A QD run lost 120/401 attempts to envelope refusals under a 300 mm brief
- **Status:** reproduction + historical run record
- **Claim:** `20261112T110126Z-screen-c414b1` (`atlas__osse_ext_throat`, cma_me) had 401
  attempts, 281 `ok`, 120 refusals all `height > 300 mm`, all coded `invalid_geometry`; overshoots:
  15 ≤302 mm, 19 ≤305, 31 ≤310, 38 ≤315 (≤5 %), median 329 mm, max 490 mm.
- **Evidence:** run `search.ndjson`; B's parser and `.tmp` overshoot measurement.
- **Counterevidence / limits:** "≤5 % over" is a geometric plausibility band, not acoustic merit;
  a horn that fits a 315 mm box is not thereby good.

### E-020: BO candidate-pool envelope is a different test from production
- **Status:** directly verified
- **Claim:** the pool rejects `w/h/depth > limit + 0.5 mm` using the **inner** surface for native
  designs, while production uses `+0.5` for W/H (outer bbox, shell included) and `+15.0` for
  depth.
- **Evidence:** `bo/data.py:1219-1236` (pool), `:1200-1216` (descriptors);
  `search/evaluate.py:289-295` (production); `registry.py:384,418,468`.
- **Counterevidence / limits:** no measured effect on pool yield; rolled-family outer surface is
  included in the pool path (`bo/data.py:1262-1266`).
- **Implication (interpretation):** "size rejected" counts are split across `schema_rejected`
  (pre-mesh estimate) and `envelope_rejected` (post-materialize); they are not one denominator.

### E-021: BO cannot encode most grid/rolled/CAD designs
- **Status:** directly verified
- **Claim:** `materialize_geometry` supports native families and the versioned rolled-family
  recipe only; any other `grid`/`cad` design raises `UnsupportedGeometryError`.
- **Evidence:** `bo/data.py:871-953`, especially `:908-910`.
- **Counterevidence / limits:** rolled-family is supported; KlangFilm/`osse_rollback` grid rows are
  not.
- **Implication (interpretation):** a "wider bounds" proposal does not make new rows BO-eligible
  unless their geometry adapter exists.

### E-022: Solve cost rises super-linearly well before the dense operator limit
- **Status:** historical run record
- **Claim:** measured quarter-domain warm solves: 2,369 dofs ≈0.4 s/frequency (~700 candidates/h),
  5,140 ≈2.8 s (~110/h), 7,001 ≈7.5 s, 8,941 ≈45 s; footprint 20–40× the dense operator at ~5k
  dofs; cap later raised 12k→24k at 5.8 GiB with zero spill.
- **Evidence:** `TOOLCHAIN.md:105,126-127,132` (2026-10-12 measurement);
  `docs/status/2026-11-14/README.md:16` (later record).
- **Counterevidence / limits:** the two records disagree on caps; neither was re-measured here.
- **Implication (interpretation):** a larger envelope is not "free"; mouth area raises triangles
  at fixed resolution, and `sizing.f_max_for_dofs` is the cheap pricing function.

### E-023: Strict resampling is opt-in and is the only "learn nothing" path
- **Status:** directly verified
- **Claim:** `resample_strict` / `retry_same_then_stop` redraw deterministic refusals up to
  `RESAMPLE_CAP = 10` and never tell them; default CMA tells a flat `1e3` and can spend budget on
  invalid attempts (`budget_counts: new`) or not (`valid`).
- **Evidence:** `search/cma.py:54-77,179-198,218-229,538-544`.
- **Counterevidence / limits:** the historical CMA-vs-BO arms did not use the strict path.

### E-024: Five boundaries are routinely conflated
- **Status:** directly verified (classification), with per-row status in B's audit
- **Claim:** search box, mesher validity (`MeshConsistencyError`/units), physical/manufacturing
  limits (throat fit, self-approach ≥2t+2), owner envelope (600×480×480), and GPU/DOF caps are
  distinct, with different remedies and different failure kinds.
- **Evidence:** `search/evaluate.py:343-359,926-928`; `mesh/build.py:38-41,250-257,383-399`;
  `generators/grid.py:662-703`; brief L21-23.
- **Implication (interpretation):** a single "invalid" rate cannot support a policy decision.

---

## D. Watchdog, queue, adaptive supervision

### E-025: The watchdog's bad-outcome predicate merges five outcome classes
- **Status:** directly verified
- **Claim:** `bad(r) = (not ok) or non-finite(objective) or objective >= 900`; this conflates
  geometry, envelope, resource, transient and metric failures, and also catches a legitimately
  measured hard-gate penalty that `outcomes.classify` would admit.
- **Evidence:** `tools/run_campaign_night.py:90-91,166-168`; contrast
  `search/outcomes.py:6-19,66-78,80-136`.
- **Counterevidence / limits:** for plain CMA on a fixed brief the rule fires on real refusals
  (5/6 replays matched); the defect is conflation, not arithmetic.

### E-026: `pin_*` thresholds are hard-coded, not public YAML
- **Status:** directly verified
- **Claim:** `pin_min_valid=30`, `pin_frac=0.03`, `pin_count=3` are read via `cfg.get` defaults,
  but `_resolve_watchdog` rejects unknown keys except `pin_ignore`.
- **Evidence:** `tools/run_campaign_night.py:99-131,186,196,199`; corroborated by
  `docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md:16`.
- **Counterevidence / limits:** no test exercises supplying these keys (which would fail).

### E-027: The watchdog never watches BoTorch study, verify or cohort jobs
- **Status:** directly verified
- **Claim:** only a `search` argv (not `verify-night`) with a `watchdog` mapping is watched; a
  `hornlab_search.studies.cli run` job has no `search` component.
- **Evidence:** `tools/run_campaign_night.py:97-98,138-140,636-644`;
  `tests/test_night_runner_watchdog.py:112-126`.
- **Implication (interpretation):** a "supervisor" whose object is optimizer choice has no
  observation of the jobs that run optimizers.

### E-028: Live queue reload is committed, and one doc contradicts it
- **Status:** directly verified / contradicted (doc)
- **Claim:** the runner re-reads the night YAML before every job and supports reorder/insert/
  remove, PAUSE, STOP and admission; `queue.ps1:21-22` still claims a started night is read once.
- **Evidence:** `tools/run_campaign_night.py:1232-1275,1356-1422`;
  `tests/test_night_runner_live.py:54-159`; contradicted doc `tools/night_queue/queue.ps1:21-22`.
- **Counterevidence / limits:** the code is right at HEAD; a local-only claim in
  `HOME_18H_PLAN:198` ("nothing committed") is stale.

### E-029: Idempotency is per-process; a restart can double-run
- **Status:** plausible inference from code (no restart test)
- **Claim:** `done` starts empty every `run_night`, and `queue_state.json` is written but never
  read back; a new process cannot know what a previous process finished.
- **Evidence:** `tools/run_campaign_night.py:1278-1286,1352,1356-1365,1419-1422`.
- **Follow-up:** a restart test and durable completed-ID protection.

### E-030: Watchdog-stopped runs lose their `best_J` in the summary
- **Status:** reproduction
- **Claim:** all 38 watchdog rows in `runs/nights/*/summary.jsonl` have `best_J: null` because the
  kill precedes the search's final summary print.
- **Evidence:** `runs/nights/*/summary.jsonl`; `tools/run_campaign_night.py:1178-1215`.
- **Implication (interpretation):** "best at stop" must be recomputed from `search.ndjson`.

### E-031: 5 of 6 watchdog stops reproduce exactly; the sixth is a QD counterfactual
- **Status:** reproduction
- **Claim:** replaying `watchdog_verdict` on ndjson prefixes reproduces the logged reason for
  refusal-rate, bound-pin, no-gain and stall stops; the QD run `c414b1` was not actually watched
  (watchdog postdates it).
- **Evidence:** `WATCHDOG_REPLAY.md` §2–§5; helper `.tmp/watchdog_replay.py`.
- **Counterevidence / limits:** poll timing can shift the trigger by 1–2 rows; one resume case
  changes the first pinned key with one extra row.

### E-032: The refusal rule would have killed a productive QD run
- **Status:** reproduction of the rule + counterfactual (the run was not watched)
- **Claim:** at row 25 the 2026-11-16 rule triggers (`refusal 36 % / 25`); the run actually
  continued to 401 rows, best J 6.636, archive 5/324 (best at eval 60).
- **Evidence:** `20261112T110126Z-screen-c414b1`; `archive.json`; `WATCHDOG_REPLAY.md` §3b.
- **Counterevidence / limits:** archive state at row 25 is unknown; the archive keeps only the
  best per cell, so an earlier cell may have been overwritten.

### E-033: `no gain` stops discarded later improvements
- **Status:** historical run record
- **Claim:** `ab4fb9` stopped at row 30 with best 3.762, resumed later to 3.673 (2.4 %); `e4c778`
  stopped at 4.891 and later reached 4.661 (4.7 %).
- **Evidence:** `runs/nights/home_day*_2026-11-16.yaml`; run ndjson; `WATCHDOG_REPLAY.md` §5.
- **Counterevidence / limits:** these are screen J, not verified acoustics; no verify solve of
  the same designs exists in those dirs.

### E-034: Resume judges only new rows
- **Status:** directly verified (code + test)
- **Claim:** with `--resume DIR`, `wd_base = len(existing rows)` and the verdict sees only the
  new slice.
- **Evidence:** `tools/run_campaign_night.py:1028-1035,1076`;
  `tests/test_night_runner_watchdog.py:175-192`.
- **Counterevidence / limits:** pin/stall checks therefore ignore pre-resume rows; a resumed
  arm is not judged against its true archive best.

### E-035: The control plane already has a read-only seam
- **Status:** directly verified (functions exist) / proposed (use)
- **Claim:** `watchdog_verdict` is a pure function and the kill is a separate loop; a shadow
  advisor can compute a verdict without acting.
- **Evidence:** `tools/run_campaign_night.py:164-211` vs `:1076-1086`;
  `SEARCH_CONTROL_MAP.md` §7.
- **Counterevidence / limits:** the advisor would share the same biased input and has no
  counterfactual.

---

## E. Objective, brief, acoustic truth, reuse

### E-036: v7 is a normalized weighted sum of nine scalar terms
- **Status:** directly verified
- **Claim:** `J = Σ w_k · raw_k / tol_k` over cov, rip, di, dislope, flat, load, distd, diag,
  flat_cv; the only local operators are the single-frequency 8 kHz one-sided floor and the load
  window minimum.
- **Evidence:** `objective/scalar_v7.py:384-407,410-513,549-552`; `scalar_v2.py:301-408`;
  `objective/terms.py:18-35`.
- **Counterevidence / limits:** `rip` is frequency-resolved within coverage and then averaged;
  "scalar" describes the aggregation, not the inputs.

### E-037: The "80×50" target is an exact point inside a stated owner range
- **Status:** directly verified
- **Claim:** the brief asks for 80 H × 50 V as the centre of "60-90 H, 40-60 V"; the scorer
  compares every scored frequency to 80/50, with V weighted 0.5.
- **Evidence:** brief L8, L28-29, L41-50, L68;
  `examples/briefs/.../room_landscape_80x50_700_hf1440_v7.yaml`;
  `scalar_v7.py:410-513`; `targets/spec.py:9-37`.
- **Counterevidence / limits:** the brief's comment is dated context, not a newly approved
  acceptance interval.
- **Implication (interpretation):** this is a goal-shape question, not a tolerance tweak.

### E-038: Flat DI is soft; off-axis leakage and rear energy are unscored
- **Status:** directly verified
- **Claim:** a +5 dB/dec DI slope costs ≈2.78 with tolerance 9.0; no term charges leakage outside
  ±coverage/2, true rear, or arbitrary-plane polar smoothness; SPDI/listening-window are
  report-only.
- **Evidence:** `scalar_v2.py:359-360`; `objective/terms.py:73-79`;
  `search/evaluate.py:508-543`; `metrics/smoothness.py:59-90`.
- **Counterevidence / limits:** the 45°/135° `diag` term partially covers diagonal behaviour; it
  does not penalise diagonal-vs-H/V inconsistency.

### E-039: Lobe handling is outermost-crossing based
- **Status:** directly verified (code) / plausible inference (consequence)
- **Claim:** beamwidth uses the outermost −6 dB crossings, so a strong wide lobe can keep or
  inflate reported width; ripple only sees in-coverage samples above −40 dB.
- **Evidence:** `metrics/polar.py:69-121`; `metrics/smoothness.py:59-90`.
- **Follow-up:** a polar-smoothness/leakage metric would be a new objective term, not a weight
  change.

### E-040: Reuse is response-anchored and bounded by stored support
- **Status:** directly verified
- **Claim:** `physical_solve_id` = design+mesh+solve hash; `analysis_id` = response checksum +
  metric method/options; `score_id` = analysis ids + objective version + scorer hash + resolved
  brief + weights/tolerances. Objective/DSP terms recompute at zero GPU only within stored
  frequencies/angles; geometry, source, symmetry or new frequency support require a solve.
- **Evidence:** `dataset/identity_v2.py:1-13,40-63`;
  `dataset/record.py:245-274`; `objective/scalar_v7.py:52-53`.
- **Counterevidence / limits:** `hifi_rescore` approximates rear from ±90° cuts and needs the
  requested angles on the solved grid (`hifi_rescore.py:16-18,64,73-77`).

### E-041: Two "cohort" gates disagree on v4/v7
- **Status:** directly verified
- **Claim:** `bo/cohort.py` hard-refuses `objective_version != 4`; `bo/data.py` reads the brief's
  version and the production builder accepts v7; `bo/metrics.py` has both a v4-only policy seam
  and a v4/v7 freeze path.
- **Evidence:** `bo/cohort.py:96-97`; `bo/data.py:498-500,657-665`;
  `studies/production.py:143-146`; `bo/metrics.py:65,254-268,527-590`.
- **Counterevidence / limits:** both can be true because they are different gates; neither was
  changed here.
- **Implication (interpretation):** "the BO stack supports v7" and "the strict cohort refuses v7"
  are both defensible sentences; a report must name the gate.

### E-042: The rerank evidence is a narrow sensitivity demonstration
- **Status:** historical run record
- **Claim:** on run `5d1082` (32 designs), the v7 #1 design (J 3.924) fell to rank 12 under a
  DSP-aware rerank (8.291); tolerances were cohort top-decile medians, not perceptual thresholds.
- **Evidence:** `docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md:7-31`;
  `docs/queue/HOME_SCORE_AUDIT_2026-11-16.md:36-40`; `hifi_rescore.py:137-160`.
- **Counterevidence / limits:** one run, one brief group; the rerank retains v7 coverage and
  dislope and cannot fix a mismatched brief.

### E-043: QD's descriptor space is achieved coverage, not goal distance
- **Status:** directly verified
- **Claim:** the archive is 2-D over mean in-band H/V beamwidth on a fixed 0–180° interval.
- **Evidence:** `config.py:39-42 (QD_DESCRIPTORS)`; `search/cma_me.py:71-74,99-147`;
  `docs/status/.../archive.json` (10/324 after 200 solves in `6d55fa`).
- **Counterevidence / limits:** a different descriptor block is configurable per run; the default
  is not a claim about what the owner wants.

### E-044: `flat` and `flat_cv` use different dispersion conventions
- **Status:** directly verified (code) / plausible inconsistency
- **Claim:** `flat` uses sample std (ddof=2, `smoothness.py:116`); `flat_cv` uses population std
  (ddof=0, `scalar_v7.py:374`).
- **Counterevidence / limits:** the difference is tiny at large n and nowhere documented as
  intentional; no test asserts equality.

### E-045: The f11/loaded-bound numbers are consistent
- **Status:** directly verified (closed-form check)
- **Claim:** driver radius 18 mm gives f11 ≈ 5584 Hz, matching `loaded_hi_hz: 5600`.
- **Evidence:** `constants.py` BESSEL/C; brief L14, L37; computed in C's report.
- **Counterevidence / limits:** this checks arithmetic only; it does not validate the source model.

### E-046: An objective v9 "coverage corridor" objective is in flight but not importable
- **Status:** directly verified (worktree)
- **Claim:** `hornlab_search/objective/scalar_v9.py` (561 lines, untracked, dated 2026-11-17)
  implements frequency-dependent H/V coverage profiles, detrended DI roughness and an optional
  HF floor; it imports `hornlab_search.targets.profile`, which **does not exist at this snapshot**;
  `objective/versions.py` is modified to list 9 as supported.
- **Evidence:** `objective/scalar_v9.py:1-59` (worktree); `Test-Path targets/profile.py` = False;
  `git status` shows `M hornlab_search/objective/versions.py` and `?? scalar_v9.py`; RFC at
  `docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md`.
- **Counterevidence / limits:** it is uncommitted and the concurrent lane may finish it; do not
  describe v9 as available.
- **Implication (interpretation):** the "goal regions" alternative is already being implemented
  by the owner/lane; a later architecture decision should compare against v9, not assume it is
  hypothetical.

---

## F. Optimizers, admission, external evidence

### E-047: Five policies exist; three are production-executable; there is no in-run switch
- **Status:** directly verified
- **Claim:** policies are scalar, pareto, cma_seed, exploration, turbo; production policies are
  scalar/turbo/pareto; a policy change invalidates the prepared package.
- **Evidence:** `bo/policy.py:43-51`; `studies/production.py:49-50,120-123`;
  `studies/runner.py:87-114,166-233`; package `adaptive_policy.manual_change_invalidates`.
- **Counterevidence / limits:** a new package can select any production policy at prep time.

### E-048: Scalar BO is a single-output GP over one frozen task and learns nothing from refusals
- **Status:** directly verified
- **Claim:** `SingleTaskGP` + Matern-5/2 ARD, one output; training rows require eligibility and a
  complete status; solver/infra/gate failures are excluded; `Y = -J`.
- **Evidence:** `bo/model.py:1-14,313-386`; `bo/data.py:48-68,107-112,309-311,338-357`.
- **Counterevidence / limits:** "nothing from refusals" is about the GP, not about the candidate
  pool, which rejects some geometry before solving.

### E-049: Data sufficiency gates are explicit and stricter than "some valid rows"
- **Status:** directly verified
- **Claim:** `n_min = max(16, 2(d+1))` unique eligible geometries; `n_max = 256`; a 4096-point
  Sobol candidate pool; study prep imposes a ≥100-selected-row floor.
- **Evidence:** `bo/data.py:29-32,71-75,278-307,1068-1073`;
  `tools/bo_compare/prepare_study.py:76-77,163-169`.
- **Counterevidence / limits:** the 100-row floor is a spend heuristic, not a demonstrated
  sufficiency threshold.

### E-050: The encoding refuses discrete/categorical dimensions and historical clipping
- **Status:** directly verified
- **Claim:** active dims 1–20; discrete/categorical/bool active dimensions are refused; historical
  observations outside the box are never clipped (`HistoricalClippingError`); only a new in-box
  proposal may be clipped.
- **Evidence:** `bo/encoding.py:21-22,55-63,116-129,242-260,276-289`.
- **Implication (interpretation):** a mixed categorical/hierarchical geometry plan needs a new
  encoding, not a config change.

### E-051: TuRBO is a declared variant without restart or exploration cadence
- **Status:** directly verified
- **Claim:** `turbo_pool_v1` reuses the scalar GP and qLogNEI, builds a local box from ARD
  lengthscales, doubles/halves `L` on success/failure, and terminates at `L < 0.5**7`; no
  automatic restart and no every-fourth maximin cadence.
- **Evidence:** `bo/turbo.py:1-26,40-46,130-175,308-311,334-421`.
- **Counterevidence / limits:** it is durable/idempotent by solve ID, so a continued arm is not a
  fresh replicate.

### E-052: The constrained Pareto path exists but is not wired
- **Status:** directly verified
- **Claim:** coverage/ripple Pareto GPs and qLogNEHVI are implemented; a constrained variant
  requires measured signed margins for every row and is not connected to the production path.
- **Evidence:** `bo/pareto.py:90-125,128-156,278-308`; `docs/queue/BO_EXT_PLAN_2026-11-16.md:
  70-74`.
- **Implication (interpretation):** constrained BO is a candidate ingredient, not a current
  capability.

### E-053: The historical BO-vs-CMA gap is confounded
- **Status:** historical run record
- **Claim:** BO arms had 185 prior rows, a 4096-design size-pre-checked pool, 60/60/60 valid
  screens and 6 verify rows; CMA arms had one starting design, 31/44/46 valid screens, 14–29
  "too large" refusals and 6 verify rows; BO improved on the start in 2/3 arms, CMA in 0/3.
- **Evidence:** `docs/status/2026-11-15-bo-vs-cma/README.md:15-22,30-37` and `data.json`.
- **Counterevidence / limits:** the report itself says the test is warm-started from an optimized
  CMA basin; no equal-information cold-start test exists.

### E-054: A prepared BO package can be unexecutable after code changes
- **Status:** directly verified (hash comparison)
- **Claim:** `bo_cov_s71001` pins 155 files; 18 differ at snapshot (including `bo/policy.py`,
  `studies/evaluator.py`); its deadline `2026-11-16T07:13:55Z` is past.
- **Evidence:** `runs/bo_multityp_2026-11-16/bo_cov_s71001/package.json`;
  `studies/production.py:86-119`.
- **Counterevidence / limits:** some mismatches are concurrent-lane edits; core mismatches are
  committed changes.

### E-055: Budget semantics in the comparison doc are partly contradicted by the adapter
- **Status:** directly verified / contradicted (doc)
- **Claim:** the matched adapter sets `budget_counts: new` and `max_attempts: None`, so cache hits
  are free and non-cached refusals consume the 80; the doc says "including refusals/cache
  outcomes".
- **Evidence:** `tools/night_queue/run_matched_home.py:112,123`;
  `docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md:36-39`.
- **Implication (interpretation):** report actual counters, not the headline budget label.

### E-056: QD value is an archive, not a lower scalar J
- **Status:** historical run record + directly verified (code)
- **Claim:** the QD run `6d55fa` filled 10/324 cells after 200 non-cached solves (3.1 %), while its
  scalar best may be flat; archive admission excludes non-complete rows but the emitter still
  ranks them.
- **Evidence:** `runs/20261115T005614Z-screen-6d55fa/archive.json`;
  `search/cma_me.py:29-34,220-284`.
- **Counterevidence / limits:** 3.1 % coverage is a budget/descriptor outcome, not proof QD
  "failed"; it is also not proof it is worth 200 solves.

### E-057: External methods transfer only under conditions Hornfab does not currently meet
- **Status:** verified claims/metadata; transfer judgement is inference
- **Claim:** constrained BO needs a signed constraint value; active subspaces need gradients;
  Hyperband needs cheap partial fidelity; multi-task BO needs related tasks and a multi-task
  kernel; QD needs a meaningful descriptor and far more evaluations (pyribs' own example uses
  ~108k); TuRBO's published result is a different budget regime and the repo variant omits
  restart/exploration.
- **Evidence:** `EXTERNAL_EVIDENCE.md` E1–E13 with DOIs/URLs.
- **Counterevidence / limits:** absence of transfer evidence is not proof of failure; it is proof
  that a claim would need a Hornfab experiment.

### E-058: The five supervisor options each have concrete evidence against them
- **Status:** directly verified (capabilities) + inference (evaluation)
- **Claim:** (O1) watchdog ignores BO studies and scalar-stall conflates value; (O2) shadow
  advisor has no counterfactual; (O3) policy controller has no state migration and invalidates
  packages; (O4) portfolio faces non-stationary, unequally-budgeted arms and few seeds; (O5)
  cost-aware design is unwired and needs ≥30 timings; (O6) deferral is the safest default while
  score truth is contested.
- **Evidence:** `SUPERVISOR_OPTIONS.md` §1–§3 with the cited lines.
- **Counterevidence / limits:** the simpler baseline (keep watchdog + read-only advisor + no auto
  switch) is a recommendation about evidence sufficiency, not a proof that switching never helps.

### E-059: No adaptive-policy claim has been experimentally validated here
- **Status:** unverified (and explicitly so)
- **Claim:** no shadow-mode recommendation set, no matched equal-cost arm comparison, and no
  prospectively censored run exists in this dossier; all switching conclusions are from
  historical records or code.
- **Evidence:** absence of artifacts; `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md` stages 1–3 are
  not reached.
- **Follow-up:** `OPEN_QUESTIONS.md` Q1–Q6.

---

## G. Acceptance checklist (from `02_EVIDENCE_FORMAT.md`)

| Item | Result |
|---|---|
| Exact commit / branch / working-tree condition / timestamps recorded | Yes — `SOURCE_INDEX.md` §1, every audit header |
| Direct source references support every headline | Yes — `path:line` at `601be8c`; unverified items labelled |
| Old plans not reported as new work; implementation checked in code | Yes — e.g. E-016, E-028, E-037, E-057 |
| Existing analyzers/tests inventoried before suggesting new code | Yes — E-011, `SEARCH_CONTROL_MAP.md` §8 |
| Contradictions preserved, not guessed | Yes — E-013, E-015/E-016, E-041, E-044, E-046, E-055 |
| Negative evidence / failure cases per task | Yes — each audit has a counterevidence section |
| Index short enough to scan first | Yes — `INDEX.md` |
| No tracked files changed; no queue change; no GPU solve | Yes — see `SOURCE_INDEX.md` §6 |
| Open questions name the decision they would change | Yes — `OPEN_QUESTIONS.md` |
