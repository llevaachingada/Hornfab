# ISSUES

## 2026-11-20 evening - FAV split-plane P1 + throat-loading follow-ups

- DONE: P1 split-plane knobs `g_k_v` / `g_s_v` on `osse_rollback` (tests 198/0); lanes queued in `fav8_2026-11-20`.
- OPEN (owner-gated): P2 "Keele-in-V" exponential V throat (build only if P1 leaves a large loading gap); P3
  azimuth-varying lip wrap / R-OSSE rollback (needs R-OSSE equation re-check, KH-003 s0).
- OPEN: transient (ringing / phase) stage from `docs/research/TIME_DOMAIN_RINGING.md` still unbuilt; HF1440 has no
  Thiele/Small data, so `driver/compression.py` cannot predict its response; v11 `load` still one-sided (rewards resonance).

## 2026-11-20 - GUI senior-review pass complete (steps 1-14; gates G/H answered)

- DONE: registry v2 (`cases.d/`) with 20 approved / 5 proposed entries; validated control links
  (lf/wide/dense/farfield/mesh_refine) + LF/wide two-series payload; hermetic F2 tests; F5
  `clearance_m` removal; F6 CPU-lane lock for manual evidence solves; readable shortlist table;
  Overview + five-item menu; New system wizard + Quick launch; P6 stage/validate/solve dialogs
  (solve disabled, decision 6); Compare page with the four README maxima + 2x2 matrix; locked
  Crossover page; final browser sweep 104/104; keyboard story 14/14; hw lifecycle harness.
  Handback: `docs/research/system_woofer_2026-11-18/GUI_HANDBACK_2026-11-20.md`.
- OWNER: gate G yes — woofer worktree locked, `system_runs` copied from the physical path with
  `robocopy /E /XJ` to `E:\hornlab-system-evidence-backup-2026-11-20`, 1,424/1,424 files, identical
  sha256 manifests (`06d1e55a…`). Gate H: "Approve the 11 README-covered" — those entries are
  approved; the 2 WP3 assembled real-motor cases and 3 mesh-refinement controls stay proposed.
- OPEN: decision 6 (GUI solves disabled), decision 3 (crossover sum locked), the 5 proposed
  registry entries until their readouts, `tools/data/system_cases.py` still validates
  `hw_readiness_v1` (census export needs the v2 loader), the CPU evidence README F8 contradiction
  (owned by that lane), the empty `ev_mesh_refine/…52652` dir, the pre-existing B8 host-cleanup
  failure, and the six other-lane full-profile failures (v11 registration, score_identities,
  scout40 queue, search_preflight). No real GUI stage/solve was launched; backend + real-BL staging
  tests cover staging.
- NOTE: this pass did not touch the GPU lock, `gpu-clean`, or any other lane's uncommitted files.

## 2026-11-20 - Rolled H terminal/rollback: width-500 size win, C look not accepted

- DONE (size): width-500 neutral `20261120T165651Z-screen-6a36c3` J 9.0033, H 111.0/90.5/67.2/49.2,
  V 111.8/70.6/56.9/42.9, 500x344x242; width 520 J 9.055; original 576 J 9.305. The 500 is the size/score answer.
- OPEN (geometry): sharp C `20261120T165805Z-screen-01eebe` J 9.6015, rip 0.159; soft lip C
  `20261120T182453Z-screen-63c7f7` J 9.5780, rip 0.158; both match the yellow 220/190 x/z but the
  max-width point is z 174.8 vs the parent 159.0 (forward bulge) and H 8k stays 48.8-49.0. User says
  the shape does not look right. Handoff: `docs/HANDOFF_ROLLED_TERMINAL_2026-11-20.md`.
- OPEN (next): re-anchor the C to the parent max-z, review H/V blend + outer shell (0.95 mm/6.0 fail),
  render, one single solve; no 60-search. Front-load CD `20261120T162808Z-screen-accb39` J 8.326 is the
  score seed; ext-throat `925868ab64d9` verify J 1.9693, H 70.8/V 61.2 at 8k is the HF reference.
- DONE: new kernels/adapters + 27 focused tests; 59 geometry tests pass; no search queued.

## 2026-11-20 - FAV-001 favorite + objective/GUI findings

- DONE: favorites registry `docs/favorites/FAVORITES.yaml` (FAV-001 Crowe-X `4140768780f0`); research
  `docs/research/favorites_2026-11-20/CROWE_X_FAVORITE_RESEARCH.md`.
- QUEUED: night `fav_crowe_2026-11-20` (k-attribution x3, k-home CMA, compact500_xo900 CMA, verify top 3),
  chained behind `cd_v11_verify_and_expand_2026-11-20`. Read results within each brief only.
- OPEN (objective, owner-gated): v7/v10/v11 `load` is one-sided, so throat resonances (Re z up to 3.2 rho c)
  score as perfect loading. Candidate: carry v6 `z_smooth` or a peak/trough term into a future CD identity;
  rescore offline first.
- DONE 2026-11-20 (GUI bug, merged from claude/hungry-sinoussi-4bc609): the run page "Score breakdown" omitted `flat_cv`, `di_roughness` and all v11 CD terms
  (1.54 of FAV-001's J 5.0). It must list every weighted term of the run's objective version.
- DONE 2026-11-20 (GUI feature, merged): a favorite/star toggle on the run page that writes `docs/favorites/FAVORITES.yaml`.
## 2026-11-20 - GUI: full score breakdown + favorites star (closes the FAV-001 GUI items)

- DONE (GUI bug): run page "Score breakdown" now lists every weighted term of the run's objective version
  (`gui/data_breakdown.py`; v11 adds `flat_cv`, `di_roughness`, `cd_lw`, `cd_di_std`, `cd_nacc`,
  `offaxis_smooth`) and sums to the stored J (FAV-001: 4.9965; the old chart showed 3.247 of it).
- DONE (GUI feature): star toggle on the run page backed by `docs/favorites/FAVORITES.yaml` (append-only,
  retire on un-star), star marker + Favorites filter on Runs and Elites (`gui/favorites.py`).
- INTEGRATION: the FAV-001 ISSUES entry with these two OPEN lines is in the main working copy only; mark them
  DONE there when this branch is merged.

## 2026-11-20 - System evidence queue ran (CPU only) + first readout

- DONE: `docs/queue/system_evidence_2026-11-19.yaml` ran in the CPU lane beside the live GPU night;
  9 solves complete (LF 20-200 Hz, 2x2 wide, 10 m, 49-freq), screen replay, census export. Then the
  real-motor assembled case (validate valid true; 25/25 + 12/12 LF) and two refined-mesh 49-freq
  cases. No GPU job started. Census now **54 cases / 19 solved / 29 staged / 3 refused / 3 invalid**.
- FIRST FAILURE (retained): #4 LF attempt used `vented/voltage`; the project port is
  `bl_motor12pr/voltage`. Corrected request completed 12/12 in a manual retry. The failed case is
  evidence, not a bug to erase.
- READOUT: `docs/evidence/system_evidence_2026-11-19/README.md` — motor up to 8.6 dB/40 deg wide,
  box/null structure up to 23.6 dB, 10 m vs 2 m max 1.38 dB/17.3 deg after path correction, 25 vs
  49 shared points 0.03 dB but denser grid exposes -20 dB nulls, assembled LF = vented-only
  default within 0.06 dB. Real-motor assembled vs demo = +4.8..+7.8 dB (mean 6.75, phase 32 deg).
- CRITICAL OPEN: **mesh convergence not established** — default/refine1/refine2 (3,954/5,976/9,148
  interior tris) move nulls by up to ~16 dB, RMS 2.6-3.3 dB. Do not rank small system differences
  or use 25-freq J changes until a convergence protocol is set.
- FIX (runner): CPU-lane `gpu-clean` now uses `--force`, so a busy GPU lane no longer produces a
  false "blocked" retry/classification; test `tests/test_night_runner_live.py` 11 passed.
- OPEN (not in queue): real 12PR300 shape/panel fit (needs maker CAD), calibration/decision 3,
  solve authorization shape/decision 6, float64 control, full-sphere far field.
- NOTE: the queue does not rank systems or change scoring; it produces LF/matrix/observation/
  sampling evidence for the decision report.

## 2026-11-20 - Pilot contracts repaired; system fidelity/normalization decision recorded

- DONE: pilot `--geometry` fidelity fix; scalar Pareto axes + F3 minimise; boolean feasibility;
  `rules_skips` top-level; `score.validate_axes` contract guard. 25 targeted tests; full `tests/system`
  passes (7 real-BL env gates).
- DECIDED: explicit calibration records are the only route to a coherent two-channel sum;
  velocity-referenced geometry experiments are a separate track; arbitrary gain matching and
  magnitude-only phase are rejected. Report: `docs/HORNFAB_SENIOR_DECISION_2026-11-19.md`.
- OPEN (owner decisions 1-6): real 12PR300 geometry/panel policy; calibration/sum; DSP realization;
  far-field standard; solve authorization. Gates D/E remain open.
- OPEN (evidence; CPU solves need authorization): LF 20-200 Hz overlay on #4/#5; 2x2 motor-box (#6 +
  demo-default); real-motor assembled R2; numerical/angular convergence. No solves were run here.
- OPEN (GUI): P4/P5/P6/P8 are backend-only; P7/P9 absent; untracked
  `hw_screen.js`/`hw3d.js`/`data_hw_stage.py` mean a partial commit breaks boot; `#/hw/new` is a dead
  CTA. The current GUI edits belong to another lane.

## 2026-11-20 - P12 verify night done: tie cluster ranked; ext-throat closed

- DONE (GPU): 5 verify-grid replays of the tie-cluster screen bests + 1 ext fallback, ~20 min, chained
  behind the compact400 night (never concurrent). Results in `docs/evidence/P12_VERIFY_2026-11-19.md`.
- MEASURED: compact400 trio stays a 3-way tie on verify (morph 1.1864 > fold 1.2763 > twinray 1.3734,
  gaps inside the 0.1293 floor); home v10 fold s2w beats the published best by 0.184 J on the same
  verify grid (1.4867 vs 1.6704) - a real improvement.
- CLOSED: ext-throat v10 (seed never improved in two independent attempts; no new freedom queued).
- OPEN (owner, GPU): full polars/balloon DI on the compact400 trio - the only step that separates the
  tie. Then the promotion gate (real-driver gaps: 12PR300 geometry, calibration, panel fit) before any
  assembled BL test.

## 2026-11-20 - Ripple program: corpus sweep done, `source.cap` INERT (fix in flight), HF width envelope-bound

- DONE: `tools/analysis/spectral_corpus_sweep.py` + tests (5 passed); 748-run sweep (545 unique designs,
  0 refusals): pooled rho(rip, V+35) 0.662, **21 of 24 identities below 0.8** -> the "redundant" verdict from the 24-design
  sample is **overturned**. Report-only `--compare A B` in the audit tool. `verify` refuses bridge-cell
  runs before any GPU work with the exact `tools/geometry/<cell>_cli.py` command.
- **OPEN (bug, fix in flight):** `source.cap` in a brief never reaches the mesher for grid families —
  `mesh/grid_build.py` hardcodes the auto cap (`source_auto_angle_deg`) and never passes
  `source_radius_mm`. Measured: three briefs differing only in cap gave identical mesh hash
  `7abdb66729…` and identical responses; 4 of 6 source-sensitivity jobs were cache hits. **Every stored
  grid-family solve uses the auto cap (~513 mm curvature at a 1.4-inch throat: a nearly flat piston).**
  Mandate item 5 must not be attempted until this lands; then re-run `docs/queue/source_sensitivity_2026-11-20.yaml`.
- RESOLVED (2026-11-20): `organic_rollback_1in` was **era mixing**, not a trade-off - five Oct-25 runs with
  no declared objective version (rows salmon_elliptical/iwata_ar/lecleach_asym, J 45-86) plus five Nov-13
  v3 runs (all salmon, J ~40). Split by version: -0.500 (v3, n=5) and +0.300 (v?, n=5). The sweep now
  groups by (brief, objective version) and dedupes by design_hash for exactly this reason.
- OPEN (owner): the HOME 600 x 480 mm envelope is the binding constraint on HF width — the Crowe X OSSE
  base sits at 593 mm mouth, so wider-than-74 deg at 8 kHz needs a larger envelope or a different mouth
  law, not a knob.
- OPEN (owner): an acoustic criterion for the fixed-angle residual. The corpus shows it is a second axis;
  nothing yet shows a large residual is audibly bad. A real driver on a real horn at the seat is the only
  measurement that can settle it — no amount of BEM will.
- NOTE: `J` remains incomparable across identities, grids and fidelity tiers (screen 2.80022 vs verify
  3.49921 for the same B3 design). The corpus tool prints `J` for context only and never ranks it across
  identities.

- **FIXED (2026-11-20):** `source.cap` now reaches the mesher for grid families AND the mesh identity (`MeshSpec.source_cap_mm`, hash-neutral when 0). Stored hashes unchanged; cap 150/60 produce distinct meshes. Re-run night `docs/queue/source_sensitivity2_2026-11-20.yaml`. Two caveats stay open: (a) `design/recipe_meta.py` still records the auto radius in `design.json` provenance for explicit-cap runs, and (b) the pre-fix runs under `runs/source_sensitivity/` must not be read as a source-sensitivity result (they are a record of the bug).

- **RESULT (2026-11-20, re-run with the knob live):** grid route - 8 kHz width <=0.2 deg and +25 deg level <=0.05 dB across auto/150/60; 10 kHz 3.1-3.5 deg; **12 kHz H width -10.1 deg, +25 deg level +1.2 dB**. Conditionality starts near 10 kHz, not at 8. Any report above ~10 kHz must state its cap.
- **OPEN (native route):** `source.cap` is still inert for OSSE/FREEFORM configs (they bypass `grid_build`): OSSE morph produced three byte-identical meshes with three different `mesh_hash` values. Either wire the cap in that spec path or refuse a cap on a native brief - do not let the recorded hash keep claiming a change that did not happen.

- **STAGED (2026-11-20):** `docs/queue/hf_width2_2026-11-20.yaml`, one job (`hf_crowex_sf5`, `g_sf_amt` 0.239 -> 0.5, mouth 596 mm) - the only legal mouth-law variant of three that shape-check accepted. Not launched: a concurrent GPU night resumed a search. Readout rule is in the file and in `docs/evidence/ripple_program_2026-11-20/README.md` sec. 3b.

- **FIXED (2026-11-20, native route):** `mesh/build.py` now forwards the brief's numeric `source.cap` into the mesher config's `source.source_radius_mm` for OSSE/R-OSSE/ICW/FREEFORM formulas (`auto` adds nothing -> byte-identical: screen `ababdbae8fea`, 12 kHz `c59ec195933a`). `cap: 60` now builds a different mesh (`5e908a347567`) with the auto angle still set. 13 tests in `tests/test_mesh_source_cap{,_native}.py`, 36 in `test_mesh_build.py` + `test_mesh_grid_build.py`. The three morph solves are being re-run (night `source_sensitivity3_2026-11-20`).
- **OPEN (small, out of that lane's scope):** `mesh/build.py::export_step` also calls `families.to_mesher_config` for the formula path and still ignores an explicit cap, so a STEP export of a cap-variant design would not match its meshed sound-radiating surface. Same one-line injection as the mesh route.

- **FOUND (2026-11-20): a silently-inert knob can POISON the solve cache.** `source_sensitivity2` ran the native route before the fix: it recorded a cap-aware `mesh_hash` (`bcf9a8cec98b`) while the builder ignored the cap, caching an auto-mesh response under a key that became correct only after the fix. `source_sensitivity3` then hit that entry (`cached: true, solve 0.0 s`, auto mesh in the cap-150 dir). Clean re-run staged with a fresh `--cache-dir`: `docs/queue/source_sensitivity4_2026-11-20.yaml` (not run - another lane held the GPU). Rule worth adopting: after fixing an inert knob, purge or bypass the cache for the affected identities.

## 2026-11-20 - Ripple audit grid test RUN (PASS) + OPEN: bridge cells cannot be verified from the plain CLI

- DONE: `ripple_audit_2026-11-20` launched (detached, 08:34 local) and finished 08:48 **exit 0**;
  ten designs re-solved at verify fidelity. Criterion passed: Spearman(V+35 screen, verify) = 0.964,
  max |delta| 0.467 dB, B3 dip reproduced at new sample positions. Evidence:
  `docs/evidence/spectral_ripple_audit_2026-11-19/VERIFY_GRID_TEST.md`.
- **OPEN (dev, needs a fix or a documented rule):** runs whose `generator.rows.type` is an opt-in
  **bridge cell** (`rosse_rect`, `n`, `rolled_rect`, `crowe_panel`) cannot be verified or resumed
  through `hornlab-search verify`; it refuses with `GeometryInvalidError: unknown rows type`. The
  bridge entry points (`tools/geometry/<cell>_cli.py`) work, but nothing in the run dir records which
  entry point a run needs, so a lane has to know it from the config. Options: record the required
  entry point in `run.json` at solve time, or make `verify` detect a bridge rows type and refuse with
  the exact command to use. Affected so far: `runs/20261119T085256Z-screen-c2203f` (and the
  `x_di_*`/`cd11__*` bests that came from the same cells).
- OPEN (owner, item 3): **DONE and read out 2026-11-20.** The *first* dense pair
  (`x_r3_b3_dense_epw6/epw9`, runs `20261120T053929Z`/`T053950Z`) is VOID - it ran 00:39 with the old
  brief (18 frequencies, `cached: true`) and its configs were corrected at 00:46, after the jobs. The
  *second* pair (`x_r3_b3_dense2_epw6/epw9`, `20261120T065945Z` 69.8 s / `T070119Z` 251.9 s) is the
  real thing: 91 frequencies, `cached: false`, epw 6.0 and 9.0. Verdict: the B3 +25 deg feature is a
  **broad, smooth ~600 Hz double-dip** (-6.7 dB shelf to 2.3 kHz, -2.8 dB at 2.75 kHz, -4.9 dB at
  3.2 kHz), identical on both meshes to <=0.1 dB - **not a narrow resonance**, so the handoff's
  resonance hypothesis is answered in the negative for this design. Readout + the 3-grid comparison:
  `docs/evidence/spectral_ripple_audit_2026-11-19/VERIFY_GRID_TEST.md`.
- NOTE: verify `J` != screen `J` (frequency grid enters J). Never pool the tiers or read the delta as
  an improvement.

## 2026-11-20 - Ripple audit test night staged (11 jobs; NOT launched)

- STAGED: `docs/queue/ripple_audit_2026-11-20.yaml` (launch-ready copy in `runs/nights/`, dry-run
  clean). Ten SCOUT40 bests re-solved at verify fidelity (25 freqs vs 18) via
  `hornlab-search verify --designs <hash> --verify-dir runs/ripple_audit/<id>` + one audit job. No
  new configs, no brief edits, no new geometry.
- OPEN (owner): launch authorisation. The night is `lane: gpu` and its per-job `gpu-clean --lane gpu`
  must not run beside another GPU night - chain with `-WaitPid <live runner pid>`, never beside.
  Predeclared criterion: Spearman(screen V+35, verify V+35) >= 0.8 and no design moving > 0.5 dB.
- OPEN (owner, item 3): `docs/queue/fable_expand_2026-11-19.yaml` ids `x_r3_b3_dense_epw6`/`epw9`
  still need their own go-ahead; they are the dense-grid B3 anomaly test, not a metric test.
- NOTE: the concurrently live `fable_expand_2026-11-19` night recorded `watchdog` status on five
  consecutive `x_s2b_*` jobs. Not investigated here; that lane's owner should look before the tail
  (`x_s2c_*`, `x_r3_*`) is trusted.

## 2026-11-20 - Fixed-angle spectral ripple audit (item 1 done) + mandate items 3-6 open

- DONE: handoff moved to `docs/research/ripple_hf_2026-11-19/` (verbatim) with `MANDATE_STATUS.md`
  and `MEASUREMENT_TAXONOMY.md`; report-only `hornlab_search/metrics/spectral.py` +
  `tools/analysis/spectral_ripple_audit.py`; evidence `docs/evidence/spectral_ripple_audit_2026-11-19/`.
  All handoff numbers reproduce to ≤0.002 dB; 14 new tests pass.
- OPEN (owner, decisions H1–H6 in `docs/research/ripple_hf_2026-11-19/MANDATE_STATUS.md`): is
  fixed-angle spectral consistency a brief target (and at what tolerance); standardise the band/angles
  or keep them per-report; GPU authorisation for mandate items 3–5; Crowe X OSSE pursued as an HF
  direction rather than a 700 Hz winner; no retroactive scoring; whether an explicit Re(z) gate is
  wanted beside the weighted `load` term.
- OPEN (dev): mandate items 3–5 not started - dense-frequency + finer-mesh re-solve of the B3
  2.27–3.31 kHz feature, the controlled HF-width experiment (Crowe X OSSE / R-OSSE rect / OSSE morph),
  and installed-source validity above the 5.61 kHz throat cut-on. Item 3 is the only one that can
  settle whether the feature is acoustic or a sampled-grid artefact.
- FINDING (limits item 6): the two references disagree almost completely (ρ = −0.018; band-mean
  penalises legitimately narrowing families) and the metric is largely redundant with `rip`
  (ρ = 0.885) on the 24 SCOUT40 bests. No rank reversal proven, so no new term.
- NOTE: `metrics.json` `on_axis_db` is band-mean-normalised (11.6–15.5 dB below the npz 0° cut); the
  ± angle check cannot validate the metric under `symmetry: hv` (mirror, ≤1.1e-6 dB apart).
- KNOWN (pre-existing, untouched): `tests/test_b8_lanes_bounded_gui::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  fails on `subprocess.Popen` in `gui/study_jobs.py`.
- KNOWN (2026-11-20 full offline run at `3032a0c` + another lane's uncommitted WIP: **5 failed /
  5464 passed / 29 skipped**, 8:39): apart from the `subprocess.Popen` item above, the failures are
  `test_targets::test_from_dict_round_trips_example_targets[score_identities.yaml]`,
  `test_objective_v8::test_v8_key_set_is_v4_minus_load_plus_the_extras`,
  `test_tools_search_preflight::test_generated_history_fallback_reads_grid_knobs`
  (`KeyError: 'source'`) and `test_queue_fable_scout40::test_scout40_jobs_are_budgeted_and_grouped`
  (night YAML now has 24 jobs; the test asserts 18). None is in this change's files - the first three
  are in the areas that lane is editing (`objective/versions.py`, `examples/score_identities.yaml`,
  search preflight) and the fourth is a stale assertion against a grown queue file. Owner/lane to
  confirm, fix or re-baseline; do not weaken the assertions.

## 2026-11-20 - GUI Overview phases 2-4 (DONE) + owner decisions closed

- DONE: findings engine + software health (`GET /api/overview/findings`, `/health`), persisted index
  (`runs/overview/index.json`), line states, project readiness registry (`docs/registry/project_readiness.yaml`,
  HW merged at read time, 45 rows, 0 errors), finding state (dismiss/acknowledge,
  `POST /api/overview/findings/<id>`, `runs/overview/finding_state.json`), parameters tab (bounds +
  2 % bound hits), snapshot spec (`tools/analysis/overview_snapshot_spec.py`) and the CPU-only
  `overview-snapshot` job. Tests **79 + 4 passed**; browser check 24/24 (1280/375, dark/light).
  Evidence: `docs/evidence/overview_phase234_2026-11-20/`.
- RESOLVED (owner, 2026-11-20): O1-O6 accepted as the plan's recommendations. O1 applied: `#/` and
  an empty hash land on `#/overview`; Home remains a route and Status stays in the nav. O4's GUI
  state file is live. O3 (night-end snapshot) is **not** wired into the night runner yet - an
  unattended edit to `tools/night_queue` needs its own approval; the Overview button covers manual
  use.
- OPEN (dev, low): no full-window snapshot has been generated yet (smoke used `--days 1`: 27 lines,
  102/102 sections ok). Judge the first real 14-day snapshot on cost before scheduling it.
- KNOWN: `tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  still fails on `subprocess.Popen` in `gui/study_jobs.py` (pre-existing, untouched here).
- NOTE: `runs/overview/index.json` (306 KB) and `finding_state.json` are the only GUI-written state;
  both are ignored with `runs/`. The index rebuilds itself when corrupt or when the schema changes.
- RESOLVED (visual QA, same day): 16 issues from an independent image review are fixed - params
  keeps best J + bound hits at 375 px (right-aligned nowrap group, header printed once, no duplicate
  timestamp), findings groups follow the payload's severity-tied order with matching-subset tile
  counts, registry drops `WP WP4` / the 50 px SOURCE column / the always-empty DECIDED column and
  states `33 risks + 12 decisions = 45 rows`. Browser pass re-run 24/24 clean.
- OPEN (pre-existing, other lane): the shell's sidebar "Resume search" button is clipped at 1280 by
  the nav column (`app.js` taskbar + `app.css`); present in HEAD, unrelated to the Overview work.

## 2026-11-19 - GUI Overview phase 1 (DONE) + phases 2-4 planned

- DONE: `#/overview` live briefing, score identity registry, typology resolver, GPU lane log fix;
  24 tests passed.
- OPEN (owner): decisions O1-O6 in `docs/overview/OVERVIEW_IMPLEMENTATION_PLAN_2026-11-19.md` §5
  (Overview as landing page, night-end snapshots, GUI-written finding state, v7 floors).
- OPEN (dev): phases 2-4 (findings engine, index cache, registry, snapshots) per the plan.
- KNOWN: `tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  fails on `subprocess.Popen` in `gui/study_jobs.py` (pre-existing, not this change).

## 2026-11-19 - Senior handbook + system solve-data export (DONE)

- DONE: `docs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md`, `tools/data/system_cases.py`,
  `tests/test_tools_data_system_cases.py` (16 passed), `docs/system_data/` (37x53 CSV + JSON +
  screens); companion horn export `docs/top_designs/` (11 tests passed, committed at `9714b39`).
- OPEN (owner, decisions 1-6): real 12PR300 geometry/panel policy; calibration/sum; DSP
  realization; far-field standard; solve authorization. GUI gates D/E remain open.
- OPEN (GUI): P4/P5/P6/P8 are backend-only; P7/P9 absent; the tracked GUI diff imports untracked
  `hw_screen.js`/`hw3d.js` (partial commit breaks boot); `#/hw/new` is a dead CTA.
- OPEN (backend): `pilot --geometry` raises `SchemaError` (`LF_TS_SCREENING` is not a fidelity);
  pilot Pareto dominance is inert (dict axes); preview prefix can lie for bridge geometry jobs.
- NOTE: the 62864 clearance verdict is in readiness/handoff/R16 replay, not in
  `payload.clearance`; the flat export reports `clearance_status=not_recorded`. No GPU was used.

## 2026-11-19 - BO/TuRBO runs invisible in the GUI (fixed)

- DONE: study solves mirrored as ordinary run folders (`tools/night_queue/mirror_bo_studies.py`, hard
  links, auto-run by `run_bo_arm.py`); GUI optimizer filter/badge/header; CMA vs TuRBO matched render set
  `docs/renders/2026-11-19-turbo-vs-cma/` (TuRBO wins 6/6 on screen J; warm-started, not independent).
- OPEN (pre-existing): `test_b8_lanes_bounded_gui::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  fails on `hornlab_search/gui/study_jobs.py` `subprocess.Popen` (commit 6791bfa) - owner of that lane to fix
  or whitelist.
- NOTE: mirror runs are read-only views; "resume"/"continue" buttons on them do not apply (they are not CMA runs).

## 2026-11-19 - P11 s2w attempted; superseded by the compact-slate night (no GPU spent)

- RESOLVED (coordination): the p11_s2w night (box-widened v10 s2 seeded at the published bests, 80
  valid) collided at launch with `compact400_next10_2026-11-19`, which had independently generated the
  same s2w lanes from the same Q3 finding and was already running them (its ext s2w held the GPU lock
  from 18:34:00). This night was stopped cleanly with ZERO jobs run and zero GPU seconds; the lock
  holder was never touched.
- DEDUPE: the compact lane's ext s2w is strictly wider (`az_a_cos_pow` lo 0.5, `L_mm` [180,330]) with
  the same brief/seed/budget -> the p11 ext config is dominated and dropped; their fold s2w covered
  fold. The two `p11_v10_s2w` configs stay in-tree as provenance + fallback (narrower ext widen +
  refusal-tolerant watchdog) if their 10-valid ext result stays inconclusive.
- MEASURED (their night): fold s2w **1.3738** (first v10 design below the published 1.4214; a tie by
  the 0.4677 floor), ext s2w 1.5710 at 10 valid (inconclusive), morph 1.4243, twinray 1.4568 - three
  constructions now inside one floor of the leader.
- OPEN (owner/GPU): the v10 leaderboard is now a 4-way inside-floor cluster (fold 1.3738, morph
  1.4243, twinray 1.4568, ext 1.5710). Ranking them needs verify-grid solves (same source/mesh/grid),
  not more screen evals. Do not queue while `compact400_next10_2026-11-19` is live.

## 2026-11-19 - Top-designs export for cloud agents

- DONE (CPU, no GPU): `tools/data/top_designs.py` + `docs/top_designs/` bundle (52 typology×score
  groups, 437 designs, 161-column CSV, full acoustic NPZ) + README + CODE_MAP/INDEX rows; tests
  `tests/test_tools_data_top_designs.py` 11 passed. Snapshot 2026-11-19T23:40:55Z (HEAD `ddfba68`).
- OPEN (owner/cloud): consume the bundle for cross-typology analysis; if the live compact400 night
  adds winners, regenerate with `tools/data/top_designs.py` and commit the refreshed files.
- NOTE: rank only within objective version; `unversioned` is its own set (pre-provenance rows).
  Use `score_config_sha`/`target_sha` or `--group-by score-config` for strict same-brief cohorts;
  raw complex pressure is not in the NPZ (local `runs/.../response.npz` remains the source).

## 2026-11-20 - Item 3 resolved (dense B3)

- 91-freq dense B3 at epw 6/9: smooth 2.1 dB dip at 2800 Hz, epw6 vs epw9 0.01 dB -> real feature,
  not a grid/mesh artifact. Bundle updated; MANDATE_STATUS item 3 DONE.

## 2026-11-20 - Expansion results + item 3 requeued

- Expansion night 16/16: DI morph 1.1692 / fold 1.2558 / twinray 1.3591 (same 181-angle grid);
  seedB/seedC no winners (data growth); seedC fold 1.2144 reachable cold.
- Ripple item 3 first attempt INVALID (config-level grid ignored; n=18). Dense brief made; dense2
  jobs appended to the live night and running after the other agent's 8 jobs.

## 2026-11-19 - Expansion night staged (16 jobs, 3-4 h), waiting for the other queue

- STAGED: fable_expand_2026-11-19 (configs examples/typologies/expand_2026-11-19/) - full-polar DI on
  the compact trio + v7 leaders, compact seedB/seedC data expansion, ripple item 3 B3 dense grid.
  All shape-check; dry-run clean. Append at the end of the other agent's live queue (do not interrupt).
- NOTE: stale .gpu.lock holder 54748 is dead (auto-takeover by the next runner).

## 2026-11-19 - v10 rescore + compact XO loading done

- DONE: v10 rescore of the W4 v7 bests (petal 1.9591, tri v9 3.0658, tri v8 3.6076 - all behind the
  v10 leaders, petal 0.585 behind fold, outside the 0.4677 floor); compact XO loading healthy
  (load_raw 0.000, driver +/-1.9 dB at 828 Hz).
- OPEN (owner): B6 lane set; compact400 floor re-measure on its own pairs (GPU); rolled cap / KL-HV-B
  lip decisions.

## 2026-11-19 - compact400 queue DONE; continuation bundle published

- DONE: bundle docs/evidence/runs/compact400_cont_2026-11-19/ (9 runs, ~9.9 MB) + README chains.
- RESULTS: compact fold 1.2071, morph 1.2258, twinray 1.4351 (bar 1.7302); v7 petal 4.1202, tri v8
  4.7503, tri v9 4.878 (the continuation regressed), b3 2.800.
- OPEN: v10 rescore of the v7 rows; compact floor re-measure; xo_loading_report on the winners; B6.

## 2026-11-19 - W2/W3 evidence bundle published

- DONE: docs/evidence/runs/scout40w2_2026-11-19/ (15 runs, 18.5 MB, full scores + geometry + best
  meshes/responses) and the README chains.
- LIVE: compact400 queue (w4 tri v9 running; w4 b3, c4x_04, c4x_05 pending).
- OPEN: read those, v10 rescore, compact floor re-measure, archive the appended compact runs, B6.

## 2026-11-19 - Queue verified (19 jobs); fold cont2 appended

- VERIFIED: 19 jobs, 0 config errors, warm starts read, live == docs/queue, lock on the running job.
- WIN so far: compact morph 1.2271 (+0.197), compact fold 1.3147 (+0.153); twinray/petal/tri-v8 ties.
- APPENDED: c4x_05_fold_cont2 (az_a_cos_amp to 0, 80 evals, warm 1.3147) - job 19.
- OPEN: w4 tri v9 / b3, c4x_04/05; then v10 rescore, compact floor re-measure, archive, B6.

## 2026-11-19 - compact morph win 1.2271; cont2 appended

- WIN: c4x_01_morph_cont 1.4243 -> 1.2271 (0.197 J > the 0.1293 compact400 floor); cont2 (a0 widened to
  0.25, 80 evals, warm 1.2271) appended as job 18.
- LIVE: c4x_02 twinray (1.443 at 9 evals), then c4x_03, the w4 v7 lanes, c4x_04.
- NOTE: p11_s2w queue_state is stale ("running" with a dead runner); display-only.

## 2026-11-19 - p11_s2w night superseded (GPU-lock refusal, no relaunch)

- NOTE: p11_s2w exited 1 on `gpu-clean rc=3 GPU busy` while the compact400 night was live - correct
  lock behaviour, no solve interrupted. Its v10 s2w work is already covered by c4n__09 (1.3738, tie)
  and c4n__10 (1.5710, tie); do not relaunch.
- LIVE: compact400 night with the 7 appended 80-eval continuations (c4x_01 running).
- OPEN: read the appended results; v10 rescore of the v7 rows; B6 set; archive.

## 2026-11-19 - 7 x 80-eval continuations appended to the live compact400 queue

- DONE: polled the live queue (compact400 night, job 9/10, GPU locked), checked overlap, appended 7
  continuations (jobs 11-17) to the live + docs/queue night files. Warm starts + shape_check pass.
- OPEN (after the appended jobs): read the compact400 winners (morph 1.4243 / twinray 1.4568 / fold
  1.4677 vs the 1.7302 bar) and the v7 lanes (petal 4.162, tri v8 4.891, tri v9 4.878, b3 2.800);
  v10 rescore for the v7 rows; B6 lane set.
- NOTE: mixed briefs in one night file; the append header states J is not comparable across groups.

## 2026-11-19 - compact400 (400 mm cube) + next-10 night staged

- DONE (CPU): compact400 brief identity + floor 0.1293 J + stored bar 1.7302; 10 configs shape-checked
  and preflighted; night `docs/queue/compact400_next10_2026-11-19.yaml` dry-run OK. Readout:
  `docs/research/compact400_2026-11-19/README.md`.
- OPEN (owner): approve GPU time (~3-5 h) and launch the staged night (command in README section 5).
- OPEN (after the night): re-measure the compact400 floor on its own screen->verify pairs (the
  published 0.1293 comes from 600 mm-class pairs); verify any lane winner that beats 1.7302 by > floor;
  run `xo_loading_report.py --fx 1000` on it (report-only).
- OPEN (carried): ATH core at r0 18 and ext-throat lanes refuse ~half of uniform box samples
  (invalid_geometry); `resample_strict` absorbs it, but watch valid/attempt ratios.

## 2026-11-19 - Q3 night: continuations + never-run typologies

- DONE (GPU): `q3_more_solves_2026-11-19`, 6/6 jobs, ~45 min. Continuations proved the point cheaply:
  fold_warm and ext_throat are **bound-pinned** (L_mm high / az_a_cos_pow low) with unchanged bests;
  crowe v2a improved 6.7324 -> 6.4779 then stalled (tie by floor). First-ever solves: Le Cleach H/V
  pair 7.8865, Crowe ES biradial 9.2355. New rows type `lecleach_ar` storm-limited (44 %) at 15 valid.
  Evidence: `docs/evidence/Q3_MORE_SOLVES_2026-11-19.md`.
- OPEN (local, next GPU): v10 s2 = widen `L_mm` (fold) and `az_a_cos_pow` (ext-throat) AND warm-start at
  the published best designs (00826f071b24 / 436a4d221328 / a23763f1c6fc / 85c59331e4a3). Without both,
  the current boxes cannot beat the published v10 leaders.
- OPEN (local): fix the `lecleach_ar` box (AR_m <= 1.8, stop <= 215 suggested), re-preflight, rerun 40
  valid; the uniform-box preflight under-predicted the 44 % storm.
- OPEN (owner): the October portrait/square sculpture families (quatrefoil, chanterelle, petal_os,
  ripple, cone_plughorn) need their own square/tall brief identity with a measured frequency floor
  before a fair test on this tree; a landscape-corridor run would measure the brief mismatch.
- NOTE (dead configs): `hl__klangfilm_ellipse_smooth_v7`, `hl__rolled_es_spiral_v7`,
  `hl__rosse_rect_cd_v7_r50_negb` reference rows types removed from the generator ("unknown rows
  type"); do not queue without a kernel decision.

## 2026-11-19 - Compact slate: owner decisions executed (CPU only)

- DONE (owner decision): crossover-aware identity authored —
  `examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml`; floor 0.2783 J (257
  pairs) published in `docs/research/compact_horn_system_2026-11-19/compact_xo900_identity.md`.
  CPU replay: fold_warm 1.0624 < A3 1.6028 ≈ A1 1.6578 ≈ A2 1.7074 < C2 2.4680 < K1 3.4445 —
  the petal/tritonia candidates still do not beat fold_warm under the new identity.
- DONE (CPU): A5 re-emit `examples/typologies/compact_2026-11-19/rf__rect_radial_wide_v8_currentgen.yaml`
  (recipe drift was provenance-only; geometry identical to the archived saved mesh within 0.1 mm).
  No solve run; config scoreable for a future authorised screen.
- DONE (CPU): 10-inch panel fit `driver_10inch_fit.md` — 10PR300 legal on the 371.2 mm BL front
  only with the 45 cm² port (+18.0 mm); 12PR300 illegal (−32.0 mm); 170 cm² port fails the 10-inch
  too (−53.4 mm). Register's "frame radius NOT_YET_AVAILABLE" superseded: `frame_od_mm: 261`
  measured (radius 130.5 mm).
- OPEN (owner): first GPU under the new identity — a compact_xo900 search (e.g. warm-start from
  fold_warm 00826f071b24, which now leads on BOTH v10 and the crossover identity) or another lane;
  nothing queued and no GPU spent this pass.
- OPEN (owner): PR #75 disposition (still OPEN/draft at d902a33; superseded locally at 627b880) and
  whether to open a PR from `hornfab-all-2026-11-18` into `main`.
- OPEN (owner, carried): gates D (GUI solve authorization) and E (calibration policy); B6 s2 must
  warm-start at the published bests if ever run.
- OPEN (staging): real 10-inch BL case still needs maker cone/surround/dust-cap dimensions; BL
  stages its demo cone without them.

## 2026-11-19 - Horn sheets: set B added, dated, larger text

- DONE (render): set A 61 horns (sheets 01-21) and set B 4 new horns (sheets 22-23), all dated.
- OPEN: the stray letter near the first V cut on sheet 1 is still unidentified.

## 2026-11-19 - Last-24h horn sheets: score column added

- DONE (render): score column on all 21 sheets; see `docs/renders/2026-11-19-last-day-horns/README.md`.
- OPEN: the sheet-1 stray letter next to the first V cut was not identified; not investigated further.

## 2026-11-19 - Last-24h solved horns rendered (contact sheets)

- DONE (render): 61 unique designs, 21 sheets at 200 dpi, `docs/renders/2026-11-19-last-day-horns/`.
- OPEN (owner): decide whether top-skew view and cut sections belong in `tools/render/render_views.py`
  (currently only in the scratch-side script copy).

## 2026-11-19 - PRIORITY10 night complete; compact-horn register delivered

- DONE (GPU): `fable_priority10_2026-11-19`, 11/11 jobs, 2.18 h. No promotion and no verify: fold_warm
  1.5433 / morph 1.5769 / ext-throat 1.7919 are ties with their published v10 bests inside the 0.4677
  floor; twinray 2.5748 is 0.80 J worse. Record lanes (+0.029, +0.227) and vt_v1 (+0.015) are
  `dislope`/`load`-blind; the rolled hybrid is the only real mover (+6.24 J). Evidence:
  `docs/evidence/PRIORITY10_QUEUE_2026-11-19.md` §11.
- DONE (local): Fable v2 integrated by reviewed diff (`627b880`), excluding its SCOUT40 queue prepend.
  Upstream `main` is still `138d88a`, so PR #75 is unmerged; `gh` cannot resolve the repo here.
- DONE (CPU): compact-horn register, mesh preflight and bounded proposal under
  `docs/research/compact_horn_system_2026-11-19/` (10 rows, measured geometry/config_sha). CPU v10 gate:
  A1 1.9858, A3 2.7734, A2 2.8813, C2 4.8193.
- OPEN (local, next pass): B6 s2, if ever run, must warm-start at the published best designs
  (`00826f071b24`, `436a4d221328`, `a23763f1c6fc`, `85c59331e4a3`), not at the lane seeds — the s1
  configs were mis-seeded and cannot reproduce the published v10 ranks.
- OPEN (owner): compact-horn GPU ask. The proposed A1 petal v10 screen misses its own 0.4677 gate by
  0.10 J; decide between (a) authorising it anyway as a different-mechanism test, (b) starting the
  compact slate from the fold/morph mechanism v10 actually rewards, or (c) no new GPU.
- OPEN (owner): whether to open a PR from `hornfab-all-2026-11-18` into `main` (this push does not).
- NOTE: unrelated uncommitted GUI edits from another lane remain in the tree and were not committed.

## 2026-11-19 - Fable senior: score-term audit + Gate A (XO loading)

- DONE: audit of the shipped v10 home brief; parity |dJ| = 0.0 on 271 designs.
- DONE: dislope = 0, side-lobe and max_edge hypotheses rejected.
- DONE: XO "hump" diagnosed as unit-acceleration referencing (corrected). `load` stays.
- DONE: `tools/analysis/xo_loading_report.py` (report-only).
- FIXED: rescore rows lost nested run paths (`run_path` added).
- OPEN (owner): V corridor onset. 40-60 deg V from 1 kHz sits at the 480 mm envelope limit (~63 deg measured); accept it or move the onset to ~1.2 kHz.
- OPEN (owner, GPU): optional dense re-solve of 3 designs (fold_warm 00826f071b24, ext_throat a23763f1c6fc, rosse fd45d3b5e62f), 1/24 oct, 450-1800 Hz.
- OPEN (finalists): driver choice (HF1440 or another 1.4" driver), and an impedance fit for absolute level/headroom. Minimum crossovers limit the field at 700 Hz.

## 2026-11-19 - Owner gates B/C answered; GUI polish in flight

- DONE (owner): gate B = "Yes to both (Recommended)" - GUI may launch CPU screen jobs and write
  user specs; gate C = "Yes (Recommended)" - GUI-launched CPU stage + validate allowed (no solve).
- OPEN (this pass): P1/P2 UI polish from the second visual review (shortlist row height/radio,
  screens list clipping, panel-fit verdict semantics, trade-off plot size, 375 px reflow).
- OPEN (owner, gate D): decision 6 authorization record shape (Solve stays disabled until answered).
- OPEN (owner, gate E): decision 3 calibration policy (system sum stays locked).

## 2026-11-19 - Horn + woofer GUI P3/P4 backend

- DONE: mesh endpoint (decimation, containment) and A/B compare (mismatch tokens, recorded motor
  G6 numbers reproduced; matrix edges). Endpoints wired + dispatch-tested.
- FIXED in wiring: the matrix route originally read only the first `?keys=` value (0 edges for two
  keys); it now accepts both `?keys=a,b` and repeated `?keys=` (regression asserted).
- OPEN (this pass): P1 UI revision, P2 screens UI, P3 3-D viewer, P4 compare UI.

## 2026-11-19 - Horn + woofer GUI P1/P2 progress

- DONE (P2 backend): screen study reader + panel-fit recompute + endpoints; 33 new tests green;
  acceptance numbers reproduce the recorded 0.1821/0.1501 and 170 cm2 refusals.
- OPEN (this pass): P1 UI revision (ledger row height, default-expanded groups, solved-vs-staging
  reconciliation, readiness KPIs, chart/polar/geometry legibility) and the P2 screens UI module.
- OPEN (senior, carried): decision 6 authorization record shape; decision 3 calibration policy (R1).

## 2026-11-19 23:35 - SCOUT40 night live

- LIVE: fable_scout40_2026-11-19 (18 jobs), controller pid 16596, first rows in 20261119T043506Z-screen-54878f.
- OPEN (local): queue.ps1 cutoff cannot express a cross-midnight stop (HH:mm today, gates later nights only);
  the night runs to its job list (per-job 1 h). Stop = STOP file if needed.

## 2026-11-19 - W2: morph chain closed (tie + persistent storm)

- CLOSED: morph_v8 3.402 -> 3.232 -> 3.757; storm 48% persisted despite resample_strict - no W4.
- GOOD: tritonia v8 W3 at 4.917 (from 5.373 W2 / 5.325 control) - n widen works.
- LIVE: the remaining W3s (tritonia v9, petal, square, rosse).
- OPEN: archive the W2/W3 runs; morning v10 rescore + B6.

## 2026-11-19 - W2: fold chain closed (tie after 3 runs)

- CLOSED: fold_warm 3.754 -> 3.682 -> 3.695 = tie; the W3 pinned on a different knob (az_a_cos_pow),
  so the box is not the limiter - no W4 (economy rule).
- LIVE: morph W3 (3.757 at 7 evals); then tritonia v8/v9, petal, square, rosse W3s.
- OPEN: archive the W2/W3 runs when done; morning v10 rescore + B6.

## 2026-11-19 - W2: square & rosse W3s appended

- DONE: crowe_x square W3 (sigma 0.12 step fix) and rosse W3 (g_b to the kernel's -0.10 floor) appended.
- NOTE: crowe_x osse = no-headroom negative (not requeued); tritonia v9 +0.41 and petal +0.70 are the
  W2 wins so far.
- LIVE: W3 fold_warm at 5 evals (3.762); 7 jobs remain queued.

## 2026-11-19 - W2: petal +0.70 (win) -> w3; crowe_x osse no-headroom

- WIN: petal 4.892 -> 4.196 (+0.70, above floor); W3 with pin_ignore q (OSSE cap 1), warm from 4.196,
  appended.
- NEGATIVE: crowe_x osse no gain (seed = lane best, preflight no_headroom) - NOT requeued; needs a new
  DOF/box/seed to be worth GPU time.
- LIVE: crowe_x square (7.907 vs 7.911 at 11 evals); then rosse and the W3 continuations.

## 2026-11-19 - W2: tritonia v9 +0.41 (above floor) -> w3 appended

- WIN: tritonia v9 5.289 -> 4.878 (+0.41, above the 0.31 floor); W3 (az_fold_v_deg high -10, warm
  from 4.878) appended.
- LIVE: petal at 16 evals, 4.561 vs 4.892 control (improving; resample_strict holding).
- OPEN: archive the W2 runs when done; morning v10 rescore + B6.

## 2026-11-19 - W2: tritonia v8 w3 appended

- DONE: tritonia v8 W3 (n 4..10, warm from 5.373) appended; fold/morph W3 also queued.
- LIVE: fable_scout40w2 job 4/11 (tritonia_v9, 5.030 vs 5.289 at 3 evals).
- OPEN: archive the W2 runs when done; morning v10 rescore + B6.

## 2026-11-19 - W2: morph W3 appended (refusal storm -> resample_strict)

- DONE: morph W3 (resample_strict + error_policy, warm from 3.232) appended; fold W3 also queued.
- LIVE: fable_scout40w2 job 3/10 (tritonia_v8, 5.373 vs 5.325).
- OPEN: archive the W2 runs when done; morning v10 rescore + B6.

## 2026-11-19 - W2 progress: fold w3 appended

- DONE: fold W3 continuation appended (both fold widths 3..40, warm from 3.682).
- LIVE: fable_scout40w2 job 2/9 (morph_v8, 3.733 vs control 3.402 at 9 evals).
- OPEN: archive the W2 runs when done; morning v10 rescore + B6.

## 2026-11-19 - SCOUT40W2 preflight notes

- NOTE: petal 37.5% sampled refusals (box-limited; resample_strict keeps budget valid); crowe_x osse
  no_headroom (seed == prior best; local continuation); crowe_x square report empty, exit 0.
- LIVE: fable_scout40w2 (fold_warm at 24 evals, 3.682 vs 3.754).
- OPEN: archive the W2 runs when the night finishes; then the v10 rescore + B6.

## 2026-11-19 - SCOUT40W2 launched (8 tail watchdog lanes)

- DONE: the eight later exit-75 lanes requeued with measured fixes (2 widens, 3 hard-limit
  pin_ignore, 3 resample_strict) + warm starts; shape_check + warm-start validation pass.
- LIVE: fable_scout40w2_2026-11-19 (8 jobs, controller 41892). Watchdogs get the same rule.
- OPEN: focused preflight for the three resample_strict lanes (running); morning v10 rescore + B6.

## 2026-11-19 - SCOUT40 complete; evidence bundle pushed; 8 tail requeues pending

- DONE: night complete (24/24); full evidence bundle under docs/evidence/runs/scout40_2026-11-19/
  (scores, seeds, geometry, best meshes/responses) + archive_run.py tool.
- OPEN (follow-on night): fold_warm (az_fold_h widen), morph_v8 (morph_rate widen), tritonia v8/v9
  (morph_width envelope pin_ignore), rosse (tmax kernel pin_ignore), petal/crowe_x osse/crowe_x square
  (refusal storms -> resample_strict/lower sigma).
- OPEN: morning v10 rescore + continuation_advice --window 30; B6 lane set (owner approval).
- NOTE: GUI lane working-tree files remain uncommitted (not this lane).

## 2026-11-19 - Requeues all closed; b3_soft 2.800

- DONE: five requeues + the b3 v2 continuation all finished; b3_soft chain 3.540 -> 2.841 -> 2.800
  (0.74 J under the control; B6 candidate). lecleach/iwata/c200mouth/stage_a are ties.
- OPEN: night tail (fold_warm onward) + the morning v10 rescore; any further exit-75 gets the same
  widen-or-pin_ignore requeue.

## 2026-11-19 - c200mouth requeue = tie; stage_a running

- NOTE: s40w__klangfilm_hvcore_c200mouth 10.02 vs 10.156 (tie, below floor); the H-setback widening
  removed the pin but the c200 mouth is not competitive (b3 seed 2.841 dominates).
- NOTE: warm-started runs evaluate the config seed at n=0 (baseline); the CMA mean is the prior best
  and the early samples sit near it. Do not read n=0 as the warm mean.
- OPEN: stage_a requeue + b3_soft v2 in the live night; watch for further watchdog stops.

## 2026-11-19 - Requeue results 1-3; b3_soft v2 queued

- DONE: s40w__klangfilm_b3_soft 2.841 (from 3.540; above floor) -> v2 continuation queued after its
  hard-ceiling theta_h1 pin (pin_ignore, warm start 2.841).
- NOTE: lecleach requeue 8.036 vs 8.037 (tie); iwata 6.671 vs 6.763 (+0.09, below floor).
- OPEN: c200mouth requeue running (10.108 at 24 evals; no gain yet).

## 2026-11-19 - Requeue preflight closed; lecleach requeue = no gain (flag)

- DONE: focused preflight for the narrowed Klangfilm requeues (hits 5.53 and 23.08; both ok).
- NOTE: s40w__lecleach_hv_smooth best 8.186 vs original 8.037 (seed start, no warm start) -> no gain
  at the widened V floor; read with the v10 rescore before any lane call.
- OPEN: watch iwata / b3_soft / c200mouth / stage_a requeues for results or watchdog stops.

## 2026-11-19 - Warm-start fix + requeue corrections

- DONE: `warmstart._param_get` now reads `params.grid.knobs`; test added, focused suite 8/8.
- DONE: night warm-start audit (`scratch/warmstart_audit_2026-11-19.log`); fold_warm/ext_throat warm
  starts removed (study dirs have no config snapshot; seeds are the lane bests).
- DONE: b3_soft beak boxes reverted (pin_ignore is the fix); c200mouth widened only the binding H
  setback (0-30); lecleach requeue runs from its seed (no warm start).
- OPEN: focused preflight of the two narrowed Klangfilm configs running; check before reading results.
- OPEN: continue exit-75 watch on the live night (same widen-or-pin_ignore rule).

## 2026-11-19 - Five bound-pinned requeues queued (s40w__* positions 7-11)

- DONE: widened + requeued the five bound-pinned lanes; shape_check all pass; same v7-smooth briefs so
  J is comparable with the originals (controls); warm-started from each lane's box-limited best.
- OPEN: economy preflight (`--from-runs --samples 64`) running for the four widened configs; check
  before reading the requeue results. stage_a is pin_ignore-only (no new region).
- OPEN: keep watching the live night; any further exit-75 gets the same widen-or-pin_ignore requeue.
- NOTE: c200-mouth core remains a test of the seed, not a basin verdict (its first run was box-limited).

## 2026-11-19 - SCOUT40 watchdog = bound-pinned (box limits), not failures

- EXIT 75 = `WATCHDOG_EXIT` (`tools/run_campaign_night.py:118`); status `watchdog`; partial results kept.
- OPEN (morning, before judging the lanes): widen `g_beak_h_setback_mm` for the c200-mouth core (kernel
  0..60; we used 0..10), `g_fc_v_hz` for lecleach_hv_smooth, `g_fc_hz` for iwata_ar_smooth; add
  `watchdog: {pin_ignore: [g_beak_v_projection_mm]}` for b3_soft (0 is the hard floor). Requeue.
- CORRECTION: the c200-mouth core's 10.156 is box-limited, not a negative-basin verdict.

## 2026-11-19 - SCOUT40 preflight: expected HARD + small refusal warnings

- DONE: preflight `--samples 64` over all configs; the only HARD is `rosse_rect_cd_v7` (bridge rows
  type; runs as the CLI command job, shape-check passed).
- OPEN (after the night): run the economy history checks with `--from-runs` for the warm-started lanes
  (headroom/expected-hits were informational only in this pass).
- NOTE: `morph_v8` and `tritonia_v8` use `infeasible_penalty: graded`, which is inert for their sampled
  (post-mesh/geometry) refusals; `resample_strict` + `budget_counts: valid` is the documented remedy in
  a future config revision (not mid-night).
- NOTE (design): the c200-mouth Phase B core seed scores ~10.2 vs the b3 core's 3.54 on the smooth
  brief (beak-only search, 30 evals); recorded as a negative basin, not a controlled A/B.

## 2026-11-19 - Owner construction fixes wired into SCOUT40; two decisions open

- OPEN (owner): rolled rollback cap — implemented **225** + a 270 control arm (sources warn 160-200 deg
  cavity; 270 is the documented range and has a measured-superior [X] claim). Literal 180-200 is not
  implemented; say the word and the cap arm moves.
- OPEN (owner): Klangfilm returning/curled lip — KL-HV-B has none (BEM: H coverage 65.2 vs >=70;
  widening the mouth did not help). The contract recommends a section-normal-spine returning lip;
  that is a gated construction change (digest + tests + shape_check), not in this pass.
- DONE: Klangfilm record lane (c200w parent) -> Phase B core at the c200 mouth 585 x 255 inner, beak
  searched; rolled section lane -> whole-shape rect pair (225 cap / 270 control, depth ratio opened).
- DONE: ext_throat_v8 dropped by shape_check refusal; warm-start `from_runs` resolved by hand.
- DONE: the night-queue resolver now finds `runs/<study>/{screen,verify}/designs/<hash>` and writes the
  full relative path (before it emitted `runs/verify`, losing the study dir); regression test added,
  3/3 pass. The SCOUT40 configs remain hand-resolved in the committed state.
## 2026-11-19 - horn + woofer system merged; GUI completion P0-P9 in progress

- DONE (local orchestrator): `feat/woofer-system-v0` merged into `hornfab-all-2026-11-18`; pre-merge
  baseline recorded (574 GUI tests, 1 pre-existing failure).
- OPEN (this pass): GUI completion P0-P9 per `docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md`;
  owner gates B-E (screen-launch approval, GUI stage+validate, decision 6 authorization record,
  decision 3 calibration policy) are open questions to the owner.
- DONE (P0): post-merge baseline 862 tests / 1 pre-existing failure / 0 errors / 7 gated skips;
  `#/hw/cases` loads from the canonical checkout. Local env: `system_runs` junction -> worktree store.
- OPEN (senior, carried): decision 6 authorization record shape; decision 3 calibration policy (R1).

## 2026-11-18 - Run artifacts archived to docs/evidence/runs

- DONE (local orchestrator): hl__klangfilm_lame_curved_v1 (f30bd2), _c200 (517217) and
  home_range_pilot_rolled_control_h12 (643de7) committed under `docs/evidence/runs/` with per-design
  design.json + metrics.json, per-run scores.csv (incl. freqs + H/V dispersion columns), and the
  best-design mesh.msh for each run (force-added; `*.msh` gitignored). No OPEN items.

## 2026-11-19 - PR #74 merged into hornfab-all-2026-11-18; SCOUT40 prep next

- DONE (local orchestrator, R21): PR #74 head 37da1ee merged as 4e27afd; offline 72/72 + mesher-gated
  batches pass locally.
- OPEN (local orchestrator): SCOUT40 preflight (resolve_warm_runs OK, shape_check, search_preflight,
  dry-run) -> GPU launch with 14 h cutoff.
- OPEN (after the night): B6 lane set from SCOUT40 winners (owner approves); offline v10 rescore of
  new rows before the B6 call.

## 2026-11-19 - SCOUT40 reordered per owner (smooth first, +2 Lame); ready for local launch

- OPEN (local orchestrator): merge PR #74 -> hornfab-all-2026-11-18 -> main (R21), then the launch steps in the PR/handoff.

## 2026-11-19 - SCOUT40 night ready; B6 deferred behind it

- OPEN (owner box): `resolve_warm_runs.py` (must print OK), shape_check + preflight, dry-run, launch with a 14 h cutoff.
- OPEN (after the night): offline v10 rescore of the new rows; lanes gaining > 0.31 J (v7) in 40 evals -> B6.
- NOTE: v10 rescore `lane_best` lost the run name for fold_warm and ext_throat v7 ("screen"); tool bug, low priority.

## 2026-11-19 - Night fable_vt_b6 ready for owner launch

- OPEN (owner): B6 budget (120 valid per arm, 2 seeds proposed) and the lane set (3 leaders + twinray tail).
- OPEN (owner box): shape_check all 9 configs, search_preflight (`--from-runs` per lane), copy to
  runs/nights/, dry-run, launch detached with a cutoff.

## 2026-11-19 - Typology review done; vt floor 320

- DONE: typology correctness review; H/V pair label fixed; vt bounds 320-465.
- OPEN (owner): close the plain-JMLC R9 gate as passed; spherical_salmon rename gate (neutral name stands).
- OPEN (owner box): Klangfilm workbook reference rows as a test fixture; OS-SE profile table test (mesher).
- OPEN (knowledge track): ICW/FREEFORM one-line cards; KH-001 "author-verified" wording.
- OPEN (local): retire or document unconfigured `lecleach_mod` / `lecleach_ar` rows kinds.

## 2026-11-19 - vt_v1 ready for shape_check; D8 advisory tool shipped

- DONE: WP 4.4 vt search route + `vt_v1.yaml` (bounds 275-465 / hold 0-0.5, seed = control).
- DONE: D8 continuation advisory (`tools/analysis/continuation_advice.py`).
- OPEN (owner box): vt_v1 shape_check + dof cap, then budget-80 CMA probe; success > 0.3105 J.
- OPEN (owner, note): g_vt_mm < ~350 gives a pinched lip (275 -> 324 mm overall); keep or raise the floor.
- OPEN (local lane, not senior-owned): WP 0.7 pin_* exposure; WP 7.1 queue-edit refusal for protected lanes.

## 2026-11-19 - Senior review queue closed (§2.1-§2.4); owner actions open

- DONE: §2.3 judgment calls and §2.4 steer planes reviewed; u3_authority SE + grade shipped.
- OPEN (owner): vt bounds [350, 465] + success > 0.3105 J consent.
- OPEN (owner box): diff shipped vs offline v10 brief YAMLs (expect name-only).
- OPEN (local): §10.2 rows; legacy class relabel + 20-record rebuild sample; B6 readout fold_warm = tie.

## 2026-11-19 - Senior verdicts: rho20 park stands (borderline); v7 floor re-pinned to 0.31 J

- DONE (senior §2.1): rho20 = borderline authority, rho knob inert, G5 park stands; §10.2 rows to
  be written by the plan owner as stated in `scratch/fable_architecture/SENIOR_VERDICTS_2026-11-19.md`.
- DONE (senior §2.2): v7 stored-J floor = 0.31 (combined 0.3105); 0.13 only for dense-scored J.
- OPEN (local/owner): add `se_deg` + `grade` (authority/borderline) to `tools/analysis/u3_authority.py`.
- OPEN (local): update WP 4.4 success test (> 0.3105 J) and the B6 readout (fold_warm = tie).
- OPEN (senior): handback §2.3 judgment-call checks and §2.4 steer plane mapping.

## 2026-11-18 - WP 4.3 done: vt V-freedom authoritative (+32 deg, +2.3 J cost), 4 freedoms inert; WP 4.4 proposal open

- DONE: B2 authority table (verify tier, same identity): vt_460 authority YES via the intended V
  plane (1100-2500, +32.32 deg, H −5.10 secondary); term_topbottom / steer_early / steer_late /
  diag_pull inert (< 3 deg). `docs/evidence/wp43_b2_authority/README.md`.
- OPEN (owner decision): WP 4.4 proposal — open the vt freedom as a searched knob on a NEW config
  version (bounds ~[440, 465], shape_check gate, budget-80 CMA probe; success > 0.1302 J over the
  control). NOT implemented (senior review + owner consent on bounds/slot first).
- OPEN (minor): vt_480 / term_sides excluded pre-solve by the u3_jobs validity table (invalid
  reach) — a dedicated owner probe could still measure them if wanted.

## 2026-11-18 - B1 + WP 2.3 done; 4.2 PASS -> 4.3 running; queue trimmed to Fable-only (owner directive)

- DONE: B1 8/8 probes clean (batch 1 + 2, no spill); WP 2.3 combined-floor record published
  (mesh part sd 0.00768 J; frequency-dominated). `docs/evidence/b1_mesh_2026-11-18/`.
- DONE (WP 4.2): record-route equivalence PASS on the biradial host (max 0.76 deg of the 1 deg
  bound) — B2 is approved under the predeclared rule; `docs/evidence/wp42_u3_biradial/`.
- RUNNING: WP 4.3 five valid variants at verify tier (night fable_wp43_2026-11-18); vt_480 and
  term_sides excluded by the u3_jobs validity table (invalid reach) — recorded; owner may override
  by a later dedicated probe.
- CLOSED (owner directive, BoTorch-vs-CMA experiment): both atlas arms REMOVED from the queue
  (paused, roots/cohort builders untouched on disk); BoTorch resumes only after a 100+ row CMA
  cohort AND explicit owner approval. WP 6.1 stays parked.
- CLOSED (WP 0.7 hardening): unbuffered child env, prepare_study builders guard, run_bo_arm child
  tail, wrapper tests fixed at the real Popen surface (the 2 known order-dependent failures gone).
- OPEN (owner/lane): w-lane continuations (rosse_rect r120/r50, lecleach_iwata_ar, control_v7,
  klangfilm, ath_core14) removed from tonight's queue by the owner — re-queue whenever wanted;
  their run dirs/rows are preserved.
- Carry-over opens unchanged: rho20 senior verdict; v7 floor protocol reconciliation; anchor
  fallback dossier; range15 brief migration; B6 budget; D6 step 2 blocked on the anchor.

## 2026-11-18 - B1 batch 1 complete; batch 2 + 4.2 queued; ext_throat partial resumes with cap 200

- DONE: B1 batch 1 = 5/5 probes exit 0, no Shared-Usage spill (R5 gate met). Batch 2 (3 ext-throat
  probes) + the WP 4.2 biradial-control verify solve are queued behind the live resume2.
  Evidence accumulation: runs/b1_mesh_2026-11-18/ (+ per-probe memwatch JSONs). B1 evidence doc +
  combined floor record (WP 2.3) after batch 2 lands.
- DONE: ext_throat 200-eval screen resumed (resume2) with the corrected cumulative cap; 92 rows
  preserved. BO `_r2` arms stay deferred per R15 (B1 not fully landed + anchor absent).

## 2026-11-18 - B1 probes burned once on a tool fault, re-queued (_rc2); strict-resume semantics recorded

- CLOSED (WP 2.2/D7, commit `8eca641`): fidelity_pairs backend-string fault — the five
  `b1_mesh_*_20261118` probe ids are burned (ledger keeps them); re-queued as
  `b1_mesh_*_20261118_rc2` at the FRONT of the live night (owner-directed queue jump). First _rc2
  probe verified past the crash point (GPU 2538 MiB / 100 %).
- CLOSED (night-queue resume semantics): `--budget` on a strict resume is the ORIGINAL cumulative
  cap, not the missing-eval count — the skill line is corrected; ext_throat resume2 queued with
  `budget: 200` (92/200 rows preserved in runs/20261118T212720Z-screen-c017db).
- OPEN (queue owner): w_klangfilm + w_ath_core14 were killed at ~0 evals (nothing lost) and
  re-queued as `_r2` ids after the atlas arms; w_lecleach_* and the remaining w_* backlog continue
  in order. No cutoff configured.
- Carry-over opens unchanged from earlier entries (rho20 senior item, v7 floor reconciliation,
  anchor fallback dossier, range15 brief orphans, B6 budget).

## 2026-11-18 - rescore reuse published + floors; WP 0.9/D9 merged; v7 floor discrepancy open

- CLOSED (WP 1.4/1.5, owner-directed reuse pass): full-fleet v7/v9/v10 columns reused untouched;
  shipped-vs-offline v10 agreement exact on the sample (max |ΔJ| = 0.0, n=122); slope5 published as
  a 166-design diagnostic sample; mixed_identity fixed and false on all columns. Results:
  `docs/evidence/v10_rescore_2026-11-18/results/` (README = the reading pass).
- OPEN (senior): v7 frequency floor 0.310 J (this pass, top-28 pairs) vs published 0.13 J (D8) —
  protocol reconciliation before tie calls; see NOTES item 3. v10 0.468 / slope5 0.486 stand.
- CLOSED (WP 0.9/D9, R12/R12b): surfaceFit echo + fallback flag in mesh_meta; record_digest block
  in recipe_meta (gates rebuilds via the canonical_record_v2 rule; kernel digests informational);
  build_box_m rows; classify_recipes.py tool; tests offline. Legacy classification EXECUTED over
  the real runs/ tree: 48,471 rebuildable / 3 bridge (klangfilm_hv_core, informational) / 0
  refused / 0 unverified
  (docs/evidence/wp09_d9_provenance_2026-11-18/classify_summary.json). WP 0.9/D9 complete.
- OPEN (STEP 3 gates): B1 probe results (night), then batch 2 / WP 4.2 / BO _r2; B6 waits only on
  the owner's budget decision — its lanes and floors are ready (README above).
- Carry-over opens unchanged: rho20 authority contradicts §10.2's inferred row (senior); range15
  briefs orphaned by R22 discard (owner/range lane); anchor fallback (R4) research dossier;
  WP 2.3 combined floor waits on B1.

## 2026-11-18 - integration closes STEP 1; 2b/2d/2e/2f evidence committed; B1 batch 1 queued

- CLOSED (D10/R21): PR #69 merged (`382c682`), PR #67 merged (`63c23a8`); CLAUDE.md R21 row added;
  R22 resolved (v9 edit discarded, range test deleted, AGENTS/.opencode doc-sync committed, c200w
  yaml kept on a PASSing shape_check). hornfab-all→main PR and #68 close-out: next push.
- CLOSED (R22 consequence, NEW — owner/range lane): 4 queued `home_range15_*` jobs in the live night
  use `briefs/home_range_v9_h12.yaml` whose objective block carries `oa_excess_tol`/`ripple_window`;
  those keys existed only in the discarded uncommitted v9 math and are refused by the merged loader
  — the jobs will exit at start with a ConfigError unless re-homed (v10 `ripple_region:
  preferred_edge`) or the brief is re-pinned. No row rewritten; decision open.
- OPEN (senior, 2b finding): rho20 (A_r20 vs v8) per-band authority TRUE (3.12° H, 2500-5500) in
  `docs/evidence/throat_hv_2026-11-18/authority_A_vs_v8.json` — §10.2's "no [inferred]" row and the
  "rho inert" park are contradicted at the threshold; see NOTES_FOR_SENIOR. Phase 3 vs B_o50: no
  authority (verified).
- CLOSED (R4, D6 anchor): ST260 source check done; config corrected to the device (a0 9.45°, k 2.13,
  m 0.86, q 5.05; STL refit 0.08 mm RMS); NO admissible measured build → R4 fallback recorded,
  ST260 unsolved, 2 anchor solves unspent. A fallback (ATH CORE/Tritonia) research dossier is a NEW
  open item (typology-research protocol) before any fallback GPU.
- OPEN (STEP 3, gated): B1 batch 2 (ext_throat probes) waits on batch 1 probe 1 Shared Usage;
  WP 4.2/4.3 + BO `_r2` queue after that per R6; B6 waits on v10 floors (rescore running).
- OPEN (WP 0.7): night cause lines are queued for the review append (fixer lane running; fix
  candidates listed in NOTES - no code changed yet).

## 2026-11-18 - owner-box integration: digest pin was env-dependent (fixed pre-merge); R22 resolved

- FIXED (R7 / WP 0.9, pre-merge): `tests/test_klangfilm_hv_digest_pin.py` pinned absolute
  `implementation_digest()` values that fold numpy/scipy versions; rewritten to pin frozen file
  content + digest recipe. Stored local recipes verified unlocked (`1304dea3…`/`a032f660…`).
- CLOSED (R22): uncommitted `scalar_v9.py` v9-math edit discarded (patch archived outside repo);
  `tests/test_v9_polar_window.py` deleted (tested only the discarded API); AGENTS.md/.opencode
  doc/config-only sync kept; c200w yaml kept pending shape_check.

## 2026-11-18 - owner questions: all RESOLVED (R1-R25); remaining work is execution

- CLOSED (decided, see OWNER_DECISIONS_RESOLVED_2026-11-18.md): C1-C6, ripple region and rip
  tol/weight, constancy, frequency grid, D6 anchor, B1/B1f, U3 host, throat park, b06a938,
  protected list + refusal storms, provenance rule, envelope convention, Crowe-X g_L_mm, Le Cleach
  wording, BO re-queue policy, space proposals, categorical split, record_gate, PR plan / integrator,
  uncommitted scalar_v9 edits, agent bench, b3_soft trim, throat-block landing.
- OPEN (local agent, execution only): LOCAL_AGENT_PROMPT_2026-11-18.md STEPS 1-4; the CLAUDE.md
  ownership row (STEP 1.5); WP 0.9/D9 implementation (STEP 4f).
- Scheduled measurements (not questions): v10/v10_slope5 floors, B1, ST260 anchor, WP 4.2/4.3.

## 2026-11-18 - night cd_rrect_2026-11-17: failure causes not yet read

- OPEN (local agent): read cause lines for t_klame_turbo100, t_klame_scalar100, t_ath14_turbo100,
  t_hvlaw_turbo100/_scalar100 (row count N), t_trit80_rc2, cont_p80_athcore_corelaw_200,
  cont_biradial_smooth_200, c_rrect_100w_rc2 (review §8 command); append to the review.
- OPEN (WP 0.7 proposal): `ok_no_result` status when a job exits 0 with no rows (t_trit80_rc2).
- OPEN (owner): BO re-queues after the causes; t_hvlaw needs a CMA cohort first.

## 2026-11-18 - integration plan awaits the owner (D10)

- OPEN (owner): approve the PR plan in `HANDOFF_2026-11-18.md` / `HANDBACK_CLOUD_2026-11-18.md` §5.
- OPEN (local agent): work list A-H in `HANDBACK_CLOUD_2026-11-18.md` §6, starting with the full
  local suite on `cloud/fable-next-2026-11-18`.

## 2026-11-18 - throat block on A: park decision (owner)

- OPEN (owner): accept "park on A, inert in this envelope" (G5). An A-family morph-target `_v2`
  is the only legal way to make onset live there; it is a new construction, not recommended.
- OPEN (local agent, CPU): read the throat runs' rows in the v10 rescore column when it runs.

## 2026-11-18 - plan status §10.2 published; A-vs-v8 per-band authority unconfirmed

- OPEN (local agent, CPU): run the `u3_authority.py` command in plan §10.2 to confirm the A-vs-v8
  rows per band (cloud had only whole-band means for v8). Expected: no authority.
- NOTE: "A_r15 beats v8 by 0.0192" is a TIE under the 0.13 floor; do not cite it as a win.

## 2026-11-18 - D6 step 1 anchor (ST260): local source check before any solve

- OPEN (local agent): re-read R-OSSE rev7 + ST260 page, fix config values if they differ, choose
  an admissible measured build (mounting modelable, distance/gating stated, polar step <= 10 deg),
  save it under docs/evidence/anchor_st260_<date>/measured/, run shape_check + the mouth/throat
  property checks.
- OPEN (owner): accept ST260 + the predeclared pass rule; approve 1-2 solves afterwards.

## 2026-11-18 - B1 GPU approval packet ready (WP 2.2 / D7)

- OPEN (owner): approve batch 1 (5 fold-warm x2 probes), optional batch 2 (3 ext_throat_v7 x2
  probes), optional B1f; all after the BO arms. Packet:
  `docs/evidence/b1_readiness_2026-11-18/README.md`.
- OPEN (B1 evidence author): say explicitly that the floor does not cover 3a1038 / 9fcd21 (and
  likely the A_r15 throat design): infeasible at x2 on this card.
- CLOSED: `kind: search` with every bound pinned now refused at search(), CLI and night dry-run.

## 2026-11-18 - v10 rescore not yet run (WP 1.4 / 1.5)

- OPEN (local agent): run the commands in `docs/evidence/v10_rescore_2026-11-18/README.md`
  (three rescores, compare, two floors), check v7 parity and `mixed_identity: false`, commit the
  summaries. CPU only.
- OPEN (owner): v10 rip tolerance/weight are the v9 values in the offline brief; changing them is
  a new identity. Constancy stays undeclared until its floor is measured.
- CLOSED: replay refused v10 (gate fixed, tested).

## 2026-11-18 - throat sweep Phases 1-3 complete; two BO arms skipped, resume needs fresh --root

- DONE: Phases 1-3 on cd_rrect_2026-11-17 (A_r15 beats v8 by 0.0192 on the matched v7 identity;
  Phase 3 best J 5.60780, rho 1.371 / onset 0.320 / ramp 2.160). Evidence:
  docs/evidence/throat_hv_2026-11-18/.
- OPEN (queue owner): resume the two killed BO arms with a FRESH --root
  (runs/night31_2026-11-17/t_ath14_scalar100 had 78 observations; t_corelaw_turbo100) - their
  package.json files now exist, so the stock resume refuses.
- OPEN (integrator): single-design night jobs must be kind: command + \hornlab-search run\;
  kind: search + fully pinned bounds crashes pycma (three part2 handoff job lines affected).
- NOTE (owner): decision on uncommitted scalar_v9.py / AGENTS.md / .opencode edits still open.

## 2026-11-18 - v10 BO metric policy: wiring waits on the owner

- OPEN (owner): PR-D is usable only after PR-A's ripple-region policy is chosen. No study or
  Pareto run consumes the v10 policy yet. Keep qLogNEI / qLogNEHVI; no multi-output GP without a
  held-out ablation.

## 2026-11-18 - v10 ripple region: owner policy needed before any brief uses it

- OPEN (owner): pick the ripple inspection region: preferred_edge / min_edge / seat_zone_deg
  (per-plane totals) / other. Evidence E1-E4 (`evidence_scoring_2026-11-18/`) informs it.
- OPEN: BO metric policy for v10 is a separate patch (PR-D). `tools/analysis/brief_truth_replay.py`
  stays v9-only for now.
- NOTE: v9 target mode inspects +/-preferred (2x the -6 dB edge); v9 numbers stay PROVISIONAL.

## 2026-11-18 - Agent benchmark: first A/B run not done

- OPEN: run the baseline vs treatment arms (with and without the contracts) and save the answers.
  Adoption gate: the treatment beats the baseline, with no regression on cases 15 and 16.

## 2026-11-18 - Klangfilm H/V comment patch changes family digests (owner gate)

- OPEN (owner): land the comments-only fix only if no queued job or saved recipe depends on the
  current klangfilm_lame_hv / hv_core implementation digest. Otherwise defer it.
- OPEN: add a frozen-vs-tools parity test for both H/V kernels (contract check 5).

## 2026-11-18 - Throat H/V follow-ons: local checks

- OPEN (local): shape_check of a rolled seed with rho 0.8 and 1.25, and of iwata_ar onset 0.5,
  before any GPU work. Run the full suite against the pre-patch head.
- CLOSED: the OS-SE "throat pinch" (18 -> 14.2 mm) is the domed source cap (physical tag 2), not
  the acoustic wall (carrier `analysis_2026-11-18/W7_THROAT_PINCH_VERDICT.md`).

## 2026-11-18 - Shared throat H/V block: local verification before any GPU

- OPEN (owner, local): confirm the pinned `hornlab_mesher` evaluates a p-expression for `k`
  (shape_check on config A with rho != 1). Run the osse_rollback geometry tests that are skipped
  without the mesher. Run shape_check plus search_preflight on both configs.
- OPEN (owner, GPU budget): onset sweep on the 80x50 brief (onset at 0/0.25/0.5/0.75), then a
  matched screen of config A vs v8.
- OPEN (design): a rolled-family per-plane throat growth parameter so rho can map there.
  `lecleach_iwata_ar` adoption. R-OSSE parent status for per-azimuth k is unknown.
- NOTE: the rolled-family implementation digest changed (file edited).

## 2026-11-18 - Near-throat H/V control for asymmetric briefs (proposal)

- OPEN (owner): approve the shared throat H/V block (CPU code patch plus tests), and approve the BEM
  onset sweep (90x40, onset at 0/25/50/75 % depth) as a separate GPU budget.
- OPEN (research): no measured H/V-onset data found in the literature. The R-OSSE azimuthal
  status is unknown. The Keele and Mantaray claims rest on summaries (scanned or 403 sources).

## 2026-11-18 - WP-K0/K1 draft contracts delivered; senior review and owner checks open

- DONE (docs only): four draft construction contracts in `docs/knowledge/contracts/`, CLAUDE.md
  routing reconciled with AGENTS.md, Keele scope fix in `hornlab-shape-check`, and the agent
  benchmark spec.
- OPEN (senior reviewer): review the four contracts. Decide whether the "published ellipsoidal
  construction" label on Le Cléac'h H/V should become "reconstruction".
- OPEN (owner/integrator): Crowe-X `g_L_mm` bound (header 320 vs file 285, plus a diverged copy in
  `docs/queue/rolled_readiness_2026-11-15/configs/`). Klangfilm kernel SHA docstrings are stale and
  the b1-b3 SEEDS mouth comments are stale. Run the zero-control tests (Klangfilm, Le Cléac'h H=V,
  rolled zero-amplitude) in the pinned env.

## 2026-11-18 (local orchestrator) - Night truth + data-agreement gate landed; bridge-type _w1 lanes fail the stock analysis path; B1 encoding owner-decided

- DONE (C1, tools): `tools/run_campaign_night.py` + `tools/night_status.py` now record/report per
  job the rows the job itself created (resume-window counting), BO package progress (read-only
  sqlite), a log tail and a stop-reason class; "0 evals" is gone for resumed work (verified:
  `cont_p80_athcore_corelaw_200` 182 rows/159 valid/J 4.8097; `t_trit80_rc2` 80 screen calls).
  Tests: `tests/test_night_status_truth.py` (13) + 46 regression tests pass.
- DONE (C2, tools): `space_card._data_agreement` "unknown"/`unconfirmed (n=...)` unless
  n >= 10; no data-justified link on unknown. Tests: `tests/test_space_card_data_agreement.py`
  (7). Senior do-not "never claim data disagrees for n < 10" is enforced in the tool now.
- DONE (queue, live night `cd_rrect_2026-11-17`): owner-approved edits (rrect BO arm ->
  `c_rrect_100w_rc3` --budget 110; atlas arms to the end; fold-warm held) PLUS a launch-fatal
  repair: all 12 queued `w_*_200w1` jobs had bare `search` argv[0]; `kind: command` runs argv
  verbatim, so they would all have died at launch. Fixed (8 stock -> `.venv/Scripts/
  hornlab-search.exe`, 5 bridge-type -> their `tools/geometry/*_cli.py`). Owner's manual PAUSE
  removed on the owner's word; night resumed into the BO arms. Queue file is untracked; details
  in `runs/nights/cd_rrect_2026-11-17/held_and_edited_2026-11-18.md`.
- DONE (D4 evidence on the fixed state): shape check 9/14; `search_preflight --from-runs`:
  seed-in-box everywhere, history still refused on every loadable lane (raw brief_file string),
  so expected hits remain uncomputed; `hl__klangfilm_lame_curved_v1_c200_w1` is `no_headroom`;
  Crowe marked not-queueable-without-warm_start+reason (append-only) in the decision packet +
  card.
- OPEN (owner C5): brief identity by digest instead of the raw `brief_file` string - the 2026-11-17
  path fix (commits `84339a7`) made the `_w1` configs LOADABLE but cannot restore warm-start/
  preflight history identity at a different directory depth; only the digest fix can.
- OPEN (tools, low): the stock analysis path (`space_card`, `shape_check`, `search_preflight`,
  `DesignSpace.from_config`) refuses the 5 bridge `rows` types (`section_pucker`, `crowe_panel`,
  `klangfilm_lame`, `rosse_rect`, plus legacy `rolled_*` outside bridges); the night jobs run
  them via bridge CLIs. Carding those lanes needs either a bridge-install import shim in the
  analysis path or carding via the bridge CLIs (senior's "5 cardable" ambiguity noted in the
  handoff).
- DONE (B1 prep, 2026-11-18): `tools/night_queue/fidelity_pairs.py` now carries three labelled
  paths — B1f frequency check (renamed; outputs say NOT mesh convergence), B1 mesh-convergence
  refine mode (same stored screen row as reference, same screen grid, only `cfg.mesh.epw`
  scaled; refined solve-hash == stored solve-hash verified for all ten), and a CPU mesh-sizing
  dry run. Realized table in `scratch/fable_architecture/.b1/b1_mesh_feasibility.md`: fold-warm
  x2 (epw 12) = 14 270-15 388 quarter-DOF, probe-grade (inside the 8.9-15.7 k OOM transition,
  Shared-Usage spill decides per design); x3 cap-bound/never built for all; ext-throat x2/x3
  INFEASIBLE on this card (mesher refuses: symmetry-plane slivers; est. ~21.1 k DOF). 24 tests;
  five per-design job spec `.b1/b1_mesh_night_insert.yaml` PROPOSED, not queued.
- OPEN (owner, NEW 2026-11-18 senor-directive addendum §5): v9 corridor-mode ripple mask
  confirmed buggy (`scalar_v9.py:493` passes `hi - lo` as the total inspected angle — a 70-90°
  corridor is scored over only ±10°). **All v9 corridor-mode second scores are PROVISIONAL**: no
  ranking, winner-pick or queue decision from v9 corridor numbers until the owner settles the
  ripple inspection-region policy (preferred edge / guaranteed minimum edge / declared seat
  zone / other). `scalar_v9.py` untouched while the uncommitted other-author edits exist; any
  fix is a NEW versioned objective/score identity (existing v9 J meaning never changes). Target
  mode's `2*preferred` is probably correct per its docstring — verify before changing. v7
  decisions, the throat sweep (v7) and B1/B1f are unaffected. Parallel read-only evidence
  E1-E4 (corridor-mask tests, offline rerank, lobe diagnostics, ablation matrix) assigned to
  the throat agent's isolated clone, delivered to the carrier `evidence_scoring_2026-11-18/`.
  **ANSWERED 2026-11-18: `preferred_edge`; fix = objective v10, draft PR #68 (`feat/objective-v10`
  @ `2ecfdd5`, stacked on `ccr-260b4b76-fi6b8j`, retarget to `main` after PR #67; verification
  4790 passed / 40 skipped / 4 known failures, none new). v9 corridor scores stay PROVISIONAL
  for decisions until v10 lands canonically. Open gates: `0007` (Klangfilm H/V digests), v10
  rip tolerance/weight, the throat-block landing target, the GPU onset sweep, and B1 GPU slots.**
- OPEN (senior/owner): B1 encoding is decided (mesh convergence, not the `verify,finalist`
  frequency pair - that encoding is B1f); CPU dry-run + feasibility table in progress in
  `scratch/fable_architecture/.b1/`; GPU slots queue after the BO arms once the owner approves
  the table. Note: `dof_cap_finalist` does not densify the mesh for these configs (epw/f_max
  unchanged); a real mesh check needs an epw/f_max refinement path.
- OPEN (tools, low): `tests/test_night_bo_arm_wrapper.py` (2) monkeypatch `subprocess.call/run`
  but `tools/night_queue/run_bo_arm.py` has used `Popen` since `1482304` - pre-existing at
  `1d6ebc8`/`3682173`, untouched.
- DONE (docs/proposals): plan amendments D5-D10 in `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md`
  §10.1; corrected C2 explanation + "what J pays for today" table in the decision packet;
  orchestrator handoff `ORCHESTRATOR_HANDOFF_2026-11-17_LATE.md`. Governance: second-writer
  commits `f5db35e`/`3682173`; throat-H/V patch set (clone
  `.claude/worktrees/agent-a527a7d28dc77734a`, tip `5af0048`) integrates after this push +
  post-drain suite; its GPU steps queue at the end after the BO arms and B1.

## 2026-11-17 (acoustic-truth lane) - WP1-WP3 hardened (independent review + reproduction)

- DONE: static compliance review + fresh-input reproduction of commit f5db35e; all headline claims
  reproduce on new inputs; 24 repairs (guard order, typed refusals, grid mesh evidence, committed
  `--parity` mode, mesher-optional existing-mesh, candidate tests on committed YAMLs); tests
  26+22+20 = 68 passed, 0 failed; published measured values unchanged.
- OPEN (owner): unchanged from the WP0-WP3 entry below — production home brief (corridor vs point,
  V onset, DI slope weight, dead band); v9 `preferred`-in-bounds semantics; WP6 pilot scheduling.
- NOTE: v9 scenario J columns were captured against the uncommitted concurrent
  `scalar_v9.py`/`evaluate.py`/`config.py` edits; re-run `brief_truth_replay.py scenarios` if that
  lane commits changed v9 code.

## 2026-11-17 - Pre-approval checks: 14/14 shape-clean, Crowe has no headroom, history unusable

- DONE: shape_check on all 14 changed proposals (14/14 pass: meshes, dof cap, envelope, round
  coupling). Economics: seed-in-box yes everywhere.
- OPEN (owner): `hl__crowe_x_osse_cd_v7` proposal is `no_headroom` (seed == prior best) and has no
  tested sigma0 with bad rate <= 15 %; it needs a declared refinement (warm_start + reason) before a
  night, or the lane is a re-test.
- OPEN (senior): `search_preflight --from-runs` returns `history_unusable` ("objective version/brief
  mismatch (run v7, this config v7)") on every lane with history, so expected in-basin hits cannot be
  computed. Question in `NOTES_FOR_SENIOR.md` (run selection by name; brief comparison/rewritten
  brief_file). Tool behaviour unchanged.

## 2026-11-17 - Stage-5 proposals: data rejects every run-backed geometric link

- DONE: `data_agrees` attached to all 29 cards from `links.py` on the latest run; 20/20 run-backed
  links disagree. The Crowe `g_wrap_deg` and fold-warm `n`/`k` links in the reviewed proposals are
  WITHDRAWN. OPEN (owner C5/§2): review the remaining proposal changes.
- OPEN (owner): `b3_soft`'s `g_theta_h1_deg.hi 60 -> 55.3` trim is sampling-sensitive (fires at a
  64-point box, not at 96: top slice 47 %). Decide on the older evidence or wait.
- OPEN (owner): the `_w1` fold-warm proposal keeps two links with `data_agrees: unknown` (no run);
  needs a run or a 2-run A/B before approval.
- OPEN (owner): `hl__crowe_x_osse_cd_v7` has **no tested sigma0 with predicted bad rate ≤ 15 %**
  (23/96 box points refused); its bounds trim is a candidate but the lane is refusal-dominated.
- OPEN (owner): categorical split for `ath_core.yaml` + 4 `rear_density` `ath_like_rear*` (3 configs
  per source, 15 files) - see `OWNER_DECISIONS_PACKET_2026-11-17.md` §3.

## 2026-11-17 - Verification findings (local orchestrator, Windows checkout)

- OPEN (owner): **12 `examples/typologies/walls_relieved/*/*_w1.yaml` do not load.** `brief_file:
  '../../briefs/...'` resolves to `examples/typologies/briefs/`; the briefs are at `examples/briefs/`,
  so the path is one `../` short. These are 12 jobs queued in `cd_rrect_2026-11-17`; they will fail at
  config load. Pre-existing (`530f4cc`). No config edited - a config change needs owner approval.
- OPEN (orchestrator/owner): **10 generator-route lanes cannot be space-carded** -
  `DesignSpace.from_config` refuses `rows` types `rosse_rect`, `rolled_rect`,
  `rolled_rect_pucker`, `crowe_panel`, `klangfilm_lame` ("unknown rows type") while the mesher
  registry accepts them; those lanes run only through `tools/geometry/*_cli.py`. Pre-existing
  (`main:hornlab_search/design/generators/grid.py:914-916`).
- OPEN: **record shadow could not build a record for 429 / 2055 designs** (`route: null`),
  concentrated in `rosse_rect` r120/r50 and the two `klangfilm_lame` runs. A `record_gate` switch
  cannot be proposed for those lanes until `record_for_design` covers their routes.
- OPEN: **the one-command evidence driver is ~10 h on the full `runs\2026111*` glob** (native route
  ~3-4 s per design). This pass used a bounded 22-run set (the live lanes) instead.
- OPEN (owner): the handoff's "three known pre-existing failures" is incomplete - `main` also fails
  `tests/test_objective_v8.py::test_v8_key_set_is_v4_minus_load_plus_the_extras`,
  `tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  and the two `tests/test_night_bo_arm_wrapper.py` tests. All four files are unchanged on this branch.
- DONE: the two branch-caused test failures are repaired (`test_targets` excludes the WP 7.1 data
  file; `test_search_qd_failure_isolation` asserts the WP 0.2 linked-space reduction).
- DONE: `search.record_gate`, `space_card` `data_agrees`, `--mode finalist` wiring (all opt-in;
  `screen`/`verify`/`final` unchanged).

## 2026-11-17 - Acoustic-truth master plan WP0-WP3 landed

- DONE: master plan `docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md` + index links;
  WP1 mesh truth (12 cases, prescribed p99 ≤ 0.1286 mm vs native floor 0.014–0.024 mm, FABLE v2 12/12,
  mesh-surface rank 4); WP2 report-only pattern quality (18 fixtures, 3 stored winners, legacy/DI parity
  0.0/9e-16); WP3 brief-truth replay (identity Δ=0.0, five NOT-QUEUED v9 corridor candidates, grid sd
  0.208→0.19 interpolated).
- OPEN (owner): approve a production home brief (v9 corridor vs point, V onset 700/1000/1250, DI slope
  weight, dead band) per `docs/evidence/HOME_CROWE_V9_OFFLINE_CANDIDATES_2026-11-17.md`; WP6 pilot
  authorization is separate and requires GPU scheduling approval.
- OPEN (scoring semantics): v9 corridor `preferred_deg` contributes nothing inside `[min,max]` — decide
  whether preferred should score in-bounds.
- OPEN (optional): WP4 provenance/envelope report (master plan §WP4) not done.

## 2026-11-17 - Handoff to the local orchestrator

- OPEN (orchestrator): follow `ORCHESTRATOR_HANDOFF_2026-11-17.md` §2-§4.
- OPEN (owner): review the four `__space_v1` proposals.

## 2026-11-17 - Stage 5 core landed (parameter spaces)

- DONE: sensitivity module, space cards, proposals. OPEN (orchestrator, local): cards for every
  active lane; read each proposal's seed shift and before/after; owner approves config edits;
  `--run` evidence from walls/links on each lane's latest run; constraint-aware CMA repair (the
  margin model is not yet usable by search).
- OPEN: WP 2.1 wiring (CLI `--mode finalist`, GUI modes, evaluate/runner dispatch).
- OPEN: two legacy configs no longer load at HEAD (`hl__klangfilm_lame_curved_v1.yaml`,
  `hl__rolled_es_spiral_v7.yaml`: unknown rows type) - pre-existing, found while carding.

## 2026-11-17 - Plan status table

- DONE: plan §10 status table. OPEN: WP 6.1 (extend offline_scores beyond ATH/v4).

## 2026-11-17 - WP 4.2/4.3 analysis ready

- DONE: rule implementation. OPEN: needs the solves (owner C6).

## 2026-11-17 - WP 4.2/4.3 runnable (needs GPU + owner approval)

- DONE: record body family + U3 job writer. OPEN (owner C6): approve ~2 + 12-16 solves; pick the host
  design (best stored biradial or ext-throat) and run `tools/analysis/u3_jobs.py` on it.

## 2026-11-17 - Evidence driver ready for the owner's machine

- OPEN (owner, Windows): `.venv\\Scripts\\python.exe tools\\analysis\\senior_plan_evidence.py --runs-glob "runs\\2026111*" --u3-lane hl__biradial_es_style_v7 --u3-lane hl__ext_throat_hvlaw_v7 [--brief <v9 brief>]`.

## 2026-11-17 - Stage 5 WP 5.2 warning landed

- OPEN (owner): split `ath_core.yaml` and the 4 `ath_like_rear*` study configs per `morph_target`.

## 2026-11-17 - Stage 7 WP 7.1 done (protected lanes)

- DONE: protected-lane file + advisory-only watchdog for listed lanes.
- OPEN (owner C5): confirm the list (`status: proposed`); decide the 4 no-evidence lanes; decide
  whether hard refusal storms in protected lanes should still stop (today: advisory only).

## 2026-11-17 - Stage 1 WP 1.4/1.5 tool landed

- DONE: rescore + floor tool. OPEN: run on Windows once the owner's C1-C3 brief exists (or on the
  S1 placeholder brief to reproduce N3: expected sd ~0.11 J top-28 for v9 at 18 vs 29 frequencies).

## 2026-11-17 - Stage 3 WP 3.3/3.4 tool landed

- DONE: record shadow gate + history-record tool. OPEN: run it over the ~75 home-landscape runs on
  the Windows checkout and read the disagreement counts before any gate switch.

## 2026-11-17 - Stage 0 WP 0.5 done (GRID extent)

- DONE: per-plane GRID extent estimate; false refusals 3 -> 1 of 64, no admitted design violates.
- OPEN (pre-existing, not ours): `tests/test_gui_preview_shape.py` plughorn-face and
  typology-link tests fail at `1d6ebc8`.

## 2026-11-17 - Stage 4 WP 4.1 CPU stage done on a seed host

- DONE: record-edit module + real point-grid meshes for control and 7 variants (biradial seed).
- OPEN (owner): U3 host pick after the same run on the best stored biradial / ext-throat designs
  (needs `runs/`); WP 4.2 (2 solves) and B2 (12-16 solves) need C6 approval.
- OPEN (pre-existing): `tests/test_mesh_build_grid.py::test_grid_self_approach_classifies_invalid_geometry_and_is_memoized`
  fails at `1d6ebc8` too (EvalContext.solve_cache_root is None).

## 2026-11-17 - Stage 1 WP 1.2 done (dense-grid scoring)

- DONE: opt-in v9 `score_grid`. OPEN: reproduce N3's 58-pair numbers with the packaged path on the
  Windows machine (needs `runs/study-*`); WP 1.3-1.5 wait on owner C1-C3.

## 2026-11-17 - Stage 1 WP 1.1 done (constancy mechanism)

- DONE: opt-in v9 constancy term (off by default). OPEN (owner C2): strict, slope-limited or none
  for the home brief; the slope bound if slope-limited.

## 2026-11-17 - Stage 3 WP 3.1/3.2 landed (record module)

- DONE: `hornlab_search/geometry/record.py` + 11 offline tests.
- OPEN: mesh-agreement test (contract T2) on the six contract lanes needs `runs/` + gmsh (Windows);
  ownership assignment for `geometry/`; WP 3.3 shadow gate and WP 3.4 history records next.

## 2026-11-17 - Stage 0 WP 0.2 done (generator links)

- DONE: `search.links` for generator-block configs (knob-space links). Unblocks coupling for the
  grid/rolled/Klangfilm families (stage 5.1).

## 2026-11-17 - Stage 0: WP 0.1 and WP 0.4 done

- DONE: WP 0.1 refusal taxonomy (post-mesh envelope and prefixed generator envelope errors coded
  `invalid_envelope`); WP 0.4 replay dispatches v9 with production DI. WP 0.3/0.6/0.7 merged.
- OPEN: real-mesh verification of 0.1 on the Windows machine (gmsh needs libGLU, absent here);
  parity check of 0.4 against stored v9 rows (needs `runs/`); WP 0.2, 0.5, 0.8, 0.9 and stage 3.1.

## 2026-11-17 - Stage-0 WP 0.3 / 0.6 / 0.7 implemented (offline)

- DONE: night-runner restart idempotency (0.6); watchdog stop `best_J` + per-kind outcome counts (0.7);
  cohort gate by objective identity instead of hard v4 (0.3). Offline tests added.
- OPEN: expose/document watchdog `pin_min_valid` / `pin_frac` / `pin_count` (rest of 0.7); replay of
  the 38 historical stops is not run (historical records are never rewritten).
## 2026-11-17 - Fable senior review: reserved decisions taken; architecture and staged plan written

- DONE (senior reviewer): lane review confirmed/amended item by item; generator direction decided
  (plural specialist generators, one shared description; no unified backbone); search design decided
  (within-lane BoTorch/CMA-ES, no cross-family model); staged plan written with gates.
  `scratch/fable_architecture/FABLE_SENIOR_REVIEW_2026-11-17.md`,
  `scratch/fable_architecture/ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md`. Docs only.
- CLOSED: the 2026-11-17 lane-review OPEN item "senior reviewer: confirm, amend or overrule; write the
  staged plan; decide the generator direction". U2 closed; B3 and B5 withdrawn.
- OPEN (owner): C1-C4 scoring values for the home brief; C5 protected-list confirmation (4 lanes with
  no request evidence); C6 solve budget (B1 20, record-route equivalence 2, B2 12-16, B6 owner's
  choice); provenance rule; envelope convention; U3 host pick (ext-throat or biradial) after the CPU
  variant stage.
- OPEN (owner): commit `A4_GRID_INDEPENDENT_SCORE.md`, `A5_SOLVER_CALL_TIMING.md`,
  `A9_CORRIDOR_VS_TERM_SET.md`, `X1_ADDENDUM_KLANGFILM_PROVENANCE.md` and their `.a4/`/`.a9/` script
  folders from the Windows checkout; the handoff cites them but no commit contains them.
- OPEN (implementation, ready for task files): stage 0 WP 0.1-0.8 (outcome taxonomy and prefix bug at
  `search/evaluate.py:1562`; generator `search.links`; cohort gate by score identity; parity-exact v9
  replay; GRID extent false-refusal count; night-runner restart idempotency; watchdog best_J and
  outcome classes; doc truths), WP 1.2 dense-grid score identity, WP 2.1 fidelity tiers, WP 3.1-3.2
  record module (needs an owner path assignment for the new module).
- PARKED with reopen conditions: U1-bis, cross-family predictor, supervisor acting on J, QD-first,
  oversize exploration, frequency staging, adjoint freeform (plan §9).
## 2026-11-17 - Stage 0 WP 0.8 / WP 0.9 (metadata) implemented

- DONE: WP 0.8 doc truths (queue.ps1 live-reload comment, `budget_counts` rules, ddof note in
  `docs/reference/OBJECTIVE_STD_CONVENTIONS.md`) and the E-012 `mode` guard with test.
- DONE: WP 0.9 additive recipe metadata (`design/recipe_meta.py`, generator provenance block).
- OPEN: `search/evaluate.py` `_persist` should write `recipe_metadata` for non-generator designs
  (file owned by another agent; NOTES_FOR_SENIOR). OPEN (owner): the `record_digest` /
  `kernel_sha256` rule and envelope convention; legacy-bridge classification (rest of WP 0.9).
## 2026-11-17 - WP 2.1 finalist fidelity tier (config resolution done; CLI/evaluate wiring open)

- DONE: `finalist` mode resolves in config (>= 29 freqs, 2x screen DOF cap, own mesh/solve identity),
  budget profile `fidelity-ladder-10`, offline tests; screen/verify unchanged.
- OPEN: expose `finalist` in CLI `--mode` and gui SEARCH_MODES; evaluate/runner dispatch (files owned
  by other agents); WP 2.2 B1 (20 solves) and WP 2.3 floor not started.

## 2026-11-17 - Lane review of the Fable corpus delivered; decisions reserved to the senior reviewer and owner

- DONE (lane agent, lower-cost): full-corpus review handed to the senior reviewer
  (`LANE_REVIEW_FOR_FABLE_2026-11-17.md`); X1 acceptance verdict consolidated
  (`X1_ACCEPTANCE_TABLE.md`); owner options menu packaged (`OWNER_DECISIONS_2026-11-17.md`,
  options only, no C1-C4 recommendation). Authorship prefaces added to the four senior-authored
  position documents and the handoff §10 table. No code implemented; no pass line changed; not a
  gated decision.
- OPEN (senior reviewer): confirm, amend, or overrule the lane review's decision set; write the
  staged implementation plan (handoff §7); decide the generator direction. Registered for that
  decision: U1 falsified the unified backbone at its own gate (0/5 lanes <= 0.5 mm);
  construct-then-correct closed (E2); response-model spine unsupported at full J; predictor hooks
  A/B/C fail; the canonical record is validated and the scoring proposal is the best-supported
  change.
- OPEN (owner): C1-C4 scoring decisions (options menu only), C5 protected-list confirmation, C6
  section-B budget (B1 20, B2 12-16, B6 owner's choice; B3/B5 withdrawn; B4 optional); the two
  no-solve proposals (provenance digest rule split kernel-vs-validator; envelope convention); the
  stage-0 code-truth list (owner's lane).
- OPEN (proposals, not queued): A12 (contract records for all ~3,414 designs + H-plane transfer
  retest) and the predeclared U1-bis backbone falsification test - both CPU-only, neither run.

## 2026-11-17 - X3 remaining: wavelength scaling lifts V, H still short; prior worth ~8 solves

- DONE (A7): scheme 3 over 1,715 designs. WL-1 lane H/V/DI .785/.880/.809, engine .336/.668/.515;
  V >= .6 in 3/3 engines, H in 0/3, so the both-plane line fails, and the within-lane rank line fails
  on scheme 3 (.489/.500). WL-1 beats its matched frequency-conditioned control on GEN-FF/GRID with
  one OSSE H regression. Whole-surface descriptors (227 features, 60 designs) are underpowered and
  non-attributable. `X3_REMAINING.md`.
- OPEN (owner): H-plane transfer needs a feature carrying section shape/aspect/wall angle; the 27
  lengths do not. A fair whole-surface trial needs more contract records (>60 designs) or a matched
  1%-sampled rematerialisation, not another model.
- OPEN: prior worth is metric-dependent (median lane 8 solves, aggregate crossing >48); the brief's
  <5-solve failure line is not resolvable with the smallest tested n = 8.
- OPEN: the fixed sibling map misses two construction links (fold_warm<-morph, 3x
  klangfilm_hv<-klangfilm_lame), so scheme-2 skill is optimistic for those families.

## 2026-11-17 - X4 completion: lanes pass; ROSSE digest drift is validator-only; lecleach still open

- DONE (A8): five `.x4` lanes 55/55 hash-reproduced and 55/55 pass v2 rule 2 at 65 × 61 (Crowe worst
  p99 1.646 vs 1.712; medians ≤0.051). Labels family 100 %, typology 96.5–100 % (disagreements are
  verify-mode provenance omissions). Envelope binds at ext/ATH; wall gap does not (+4.10 mm min).
  `X4_COMPLETION.md`.
- DONE: `hl__rosse_rect_cd_v7` resolved. `9b040e37…` vs HEAD `601056d0…` is `a10e784`'s validator-only
  `b >= -0.10` change; with the persisted-digest equality bypassed in memory the 11 grids rebuild
  11/11 and match the stored meshes (p99 0.468–0.918 mm; W/H exact; depth = rear closure).
- OPEN: `hl__lecleach_hv_landscape_smooth_v7` remains unrebuildable at HEAD (no digest; `d6c9abd` H/V
  realization change) and 2 of 11 old Klangfilm sample designs remain unverified (`e3a1f4a3…`).
- OPEN: X4 Parts B/D gates are not testable/not run; the full 2^k corner scan is not testable.
- OPEN (owner): require `implementation_sha256` on every grid-row recipe; ROSSE shows a validator-only
  code change is enough to lock a whole stored lane out of its own canonical adapter.

## 2026-11-17 - E1 follow-up: full-J response modelling gives no advantage

- DONE (A3): E1 repeated with parity-exact full J. Median lane reveals - score 18.5, curve head 24.0,
  nine-term head 18.25, actual history 87.25, random 55.25 - so Part A, B and C all fail and E1's
  failure criterion is fully met. The earlier proxy-level success is the proxy: the same selector
  needs 10.0 reveals on cov+DI vs 24.0 on full J. Error sits in `diag`, `dislope`, `cov`, `load`.
  Report `E1_FOLLOWUP_WHOLE_SURFACE.md`.
- OPEN (blocked on data): pool-vs-real-absence cannot be separated without a fresh unlocked pool
  (B4/B6 solves, owner approval). The whole-surface descriptor arm needs more than 10 designs/lane.

## 2026-11-17 - sigma0/bound-width coupling: measured failure mode + institutionalized guidance

- FOUND (measured, `docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md`): sigma0 ≥ 0.25 with >8 free keys
  or global bounds produces refusal storms (25-48 % of evals at the flat 1000 penalty) and flat
  traces. Controlled A/B tonight: same 12-key config, sigma0 0.25/global bounds = 24/45 refusals,
  zero improvement, 45 wasted GPU evals; sigma0 0.10 + seed-centered ±30 % bounds = best J 6.401 →
  2.819 (−56 %), 9 refusals.
- FOUND (related): converged-incumbent seeds with small budgets go flat regardless of sigma0 (the
  four corelaw cohort screens at J 3.233: flat 59-100/60-101). That is restart attribution, not
  step size; `hornlab-search-economy` already covers it.
- DONE (guidance, no hardcoding): sigma0 selection guidance added to the `hornlab-search-economy`
  skill (check 3) and AGENTS.md routing; official CMA-ES sources (pycma docstring, Hansen tutorial
  1604.00772, Practical Hints: x0 ± 2σ0 coverage, local-improvement σ0 ∈ [0.001, 0.1]) cited in the
  evidence doc. `search/cma.py` untouched — sigma0 stays a config knob governed by preflight.
- OPEN (owner): whether stage-based sigma0 starting points listed in the skill should be enforced
  as a preflight `--strict` rule; `docs/plan/12_RESEARCH_BASIS.md` is frozen so the research-basis
  citation lives in the evidence doc instead.
- OPEN (engineering): none — no code changed.

## 2026-11-17 - Consolidation: 18 archive refs, docs + H12 landed, one pre-existing B8 failure

- DONE: local refs preserved before cleanup: 18 archive tags, 5 verified bundles, and snapshots of
  dirty/untracked plus ignored worktree evidence. Worktrees 13 -> 2; local branches 29 -> 4.
- DONE: 17 additive docs from the 2026-11-14 handoff integrated (`caa37d0`; no mass rename sweep).
- DONE: H12 opt-in `oa_excess_tol` + `oa_excess_raw` and its hifi brief integrated (`0a451db`);
  default off and `config_sha` preserved; objective/config/target tests 135 passed.
- OPEN (owner): Fix D Keele `0.9` factor; A527 night-runner directivity guard while preserving
  `pin_ignore`; sab-home `rim_sweep_ratio` floor; A473 v3 configs; outer `.git` quarantine;
  HF staging verification.
- OPEN (engineering): B8 `test_study_modules_have_no_host_cleanup_or_process_kill_paths` fails on
  `subprocess.Popen` in `gui/study_jobs.py` (introduced `b019623`). Pre-existing, not caused by
  consolidation, and not weakened; it needs a design decision.
- NOTE: H12's `oa_excess_raw` is a diagnostic key; `oa_excess_tol` is emitted only when opted in.
- NOTE: `configs/b3_soft.yaml` is another lane's uncommitted edit and was left untouched.

## 2026-11-17 - Fable: P1 predictor replay finishes; no unbiased pool in stored data

- DONE (A10): unbiased-pool gate fired - 0 strict unbiased designs in 8 study lanes, 6 of 8 under 30
  even on the cadence upper bound; fair-pool replay not run. Biased replay: hook A 0.733 vs the 0.8
  line, hook B 11/19 vs 13/19, skip test 8.9 % vs < 2 %; hook C's wins are the pool's, not the
  predictor's. an7 reproduced exactly. `P1_PREDICTOR_REPLAY.md`.
- OPEN (blocked on data): a fair predictor evaluation needs an even, >= 30-per-lane pool of solved
  designs that were not optimizer-selected. None exists; producing one needs owner-approved solves.

## 2026-11-17 - Fable: layered backbone fails U1; generator decision open

- DONE: N1b contract v2 - six lanes pass Test 2 at 65x61 on the native-floor rule; 72 Klangfilm
  designs excluded by digest (`e3a1f4a3` not reproducible at HEAD) and ten verified replacements
  pass; envelope depth is the rear closure exactly; 0/309 stored biradial designs near the size
  limits. N2 lineage - 75/75 runs classified, 0 unknown, 17 of 21 lanes owner-evidenced. N4 U1 -
  0/5 lanes at <= 0.5 mm, 5/5 above 2 mm.
- OPEN (owner): N4 hand-back. Either redesign the layered section and depth laws (two exponents,
  rounded-rectangle section, curvature-placed psi knots) or accept the canonical record as the
  description and drop the compact-backbone claim. U2/U3 stay gated.
- OPEN (owner): contract v2 envelope definition - mesh-built inner sheet or generator outer shell.
  Biradial differs by +1.9...+3.5 mm and the two conventions disagree.
- OPEN (owner): require `implementation_sha256` on every grid-row recipe. Lecleach stores none, and
  its H/V realization changed in `d6c9abd` after both stored runs, so its 48 stored designs cannot
  be rebuilt from their recipes at HEAD.
- DONE (N3): v9 J converges at 58 dense points (sd 0.032/0.019); with constancy it needs 116
  (0.058/0.014 all/best-28). Residual from 18 solved frequencies: 0.113 (J_v9) / 0.205 (with
  constancy) at the top. `N3_GRID_INDEPENDENCE_V9.md`.
- OPEN: U2/U3 not started (gated on N4).
- NOTE: no family cut recommended; Crowe, Le Cleac'h and Klangfilm remain owner-protected.
- NOTE: `configs/b3_soft.yaml` remains another lane's uncommitted Phase B edit.

## 2026-11-17 - Klangfilm convergence check passed; Phase B verdict stands

- DONE: epw-9 re-solves of A0 (16394 dofs) and B3 (6757 dofs); every gate-relevant quantity moves
  <= 0.1 deg / 0.014 Var(DI) / 0.003 J. `AB_REPORT_CONV.md`, `ab_manifest_conv.json`.
- OPEN (unchanged): returning-lip module next; source-cap study separate; no search started.
- NOTE: `configs/b3_soft.yaml` was edited by another lane (budget/max_attempts) and is left uncommitted.

## 2026-11-17 - Klangfilm Phase B: DI constancy gained, H coverage short

- DONE: digest-bound family adapter, four configs (b1-b4), canonical mesh route, four BEM solves, report.
- FINDING: B3 wins the smooth policy (6.570 vs 8.438) and cuts `Var(DI)` 45 %, with clean lobes and better
  loading, but it LOSES the stricter CD policy (14.827 vs 14.208) because that policy weights absolute
  coverage harder - and B3's H -6 dB beamwidth is 65.2 deg, below the 70 deg floor of the pre-declared
  +-10 deg window. B2/B4 show that a bigger mouth does not widen H.
- OPEN: returning-lip (section-normal spine) module, then re-run B3's rule set; the source-cap study stays
  separate.
- LIMITATION: no constant-directivity claim. B3 is a DI-constancy result, not an 80x50 coverage result.

## 2026-11-17 - Agent pings 8/8; OpenCode Go preset active; rbassist child lanes still blocked

- DONE: `tools/agent/ping_agents.py` added; `--live` suite passes 8/8. Static checks cover both
  workspaces (skills, config, orchestrator grants); live checks cover the orchestrator, a delegated
  fixer and prompt isolation. Evidence: `docs/evidence/AGENT_PING_2026-11-17.md`.
- DONE: active preset `opencode-go-max` (`deepseek-flash-max` tiers on OpenCode Go), selected in the
  repo and in the `Hrns` umbrella mirror. Verified `opencode-go/deepseek-v4.1-flash` at variant max
  and live skill loads.
- DONE: the HornLab orchestrator no longer lists rbassist skills (`skills_remove`; live check
  `PING-ISOLATION: (no); rbassist skills: (none)`).
- OPEN (owner): the DeepSeek-direct account balance is exhausted. HornLab no longer depends on it,
  but rbassist presets still put `deepseek/*` first, so its delegated lanes fail until the balance is
  restored or those arrays are reordered.
- OPEN (blocked on the above): P2 model/variant pilot - six representative tasks, correctness first,
  then latency, cost, retries. No variant was changed by this pass.
- OPEN (owner): living-log archival policy (`docs/LOG_ARCHIVAL_PROPOSAL_2026-11-17.md`);
  container-fallback file approval; whether to retire the duplicated global rbassist skills.
- NOTE: the refreshed OpenCode Go key is stored only in `~/.local/share/opencode/auth.json`; no key
  material is in the repository or any committed file.

## 2026-11-17 - ROSSE-RECT b-term negative floor + GUI hover; owner run choice open

- DONE: `g_b` GUI hover now explains the R-OSSE axial bow and sign convention; catalog regenerated
  and verified from the running GUI. All 16 knobs on `hl__rosse_rect_cd_v7` have hover docs.
- DONE: `tools/geometry/rosse_rect.py` accepts `b >= -0.10`; `tests/test_tools_rosse_rect_b.py`
  pins the `-0.05` mesh and the `-0.11` refusal. Real-mesher check at `-0.01..-0.10` fits the
  480 mm brief envelope (depth 422 -> 449 mm).
- OPEN (owner choice): launch the prepared `hl__rosse_rect_cd_v7_r50_negb` (seed `38aeaee3413b`,
  `b = -0.05..0.06`, preflight 55/64 valid) from the live 50-run best, or let the non-negative
  50-run finish first. The live run `20261117T053153Z-screen-15f0e4` continues either way.
- NOTE: no solver/objective/GPU code or running queue was changed by the GUI/doc/validator pass.

## 2026-11-17 - Orchestration P0/P1 landed; P2 model/concurrency pilot open

- DONE (P0a): umbrella workspace can see the HornLab skills. `opencode debug skill` from `Hrns`
  measures 26 skills / 8 of 8 `hornlab-*` (was 18 / 0). Files: `Hrns/AGENTS.md`,
  `Hrns/.opencode/opencode.jsonc`; explanation in `docs/AGENT_BOOTSTRAP_CONTAINER.md`.
- DONE (P0b): `AGENTS.md` has an explicit precedence section and a bounded reading order; Wave 0-3
  and the per-task file-ownership table are marked historical with invariants preserved.
- DONE (P1a): global prompt appends are project-neutral; rbassist rules live in the active rbassist
  workspace. Verified by effective-prompt inspection with `opencode debug agent`.
- DONE (P1b): dispatch discipline rewritten to risk/independence, 3-writer cap, child registry,
  bounded handoffs, terminal-result retrieval allowed, no repeated polling, no default nested
  fan-out.
- OPEN (owner): (1) accept the machine-local container fallback files as non-versioned artifacts;
  (2) decide whether the duplicated global rbassist skills may be retired after one rbassist session
  confirms the project copies suffice; (3) schedule the P2 pilot and confirm the six representative
  tasks; (4) decide the living-log archival policy.
- OPEN (P2, blocked on the above): compare `flash/max` vs `flash/high` orchestrator,
  `flash/high` vs `flash/medium` mechanical fixer, and oracle models on six historical
  numerical/physics pitfalls. No model was changed in this pass.
- NOTE: the eight rbassist skill names flagged in the 2026-11-16 report are **not stale**; all eight
  exist in `rbassist-merge-cloud-local`. The defect was global-only visibility.

## 2026-11-17 - Fable X1: inner-wall agreement fails on two or more lanes; U1 blocked

- OPEN (research, before U1): the contract-minimum surface record (65 stations × 31 azimuths) does
  not meet the pre-declared inner-wall line for rolled (0/10, p99 1.696 mm; 49 azimuths passes
  10/10) or Crowe (0/10, p99 1.870 mm; native-point/mesher-fit floor ~1.07 mm), and one Klangfilm
  design fails at native and dense sampling (p99 1.46 mm).
- OPEN (provenance): the ten selected Klangfilm recipes carry saved digest `e3a1f4a3…`, while the
  current legacy bridge returns `ea5026…`; the addendum's verified digest belongs to a different
  run. The surface rebuild is byte-identical between the two kernel copies; the digest-covered
  companion files changed.
- OPEN (contract method): the literal runbook 4b nearest-surface rule scores mouth-rim nodes as
  inner; a topology (sharp-crease) or signed-position separation is required. The envelope method
  also needs a mouth-rim rule (biradial +1.9…+3.5 mm on width/height).
- DONE: six-lane N1 table (`scratch/fable_architecture/X1_CONTRACT_TESTS.md`); determinism 60/60;
  refinement 30/30 on the three testable lanes; depth deficits traced to the rear closure at
  `z = −t`. One row added to `LOW_COST_AGENT_HANDOFF.md` §10.
- NOTE: N2–N5 were not run because the X1 stop condition was met. No code, config, solve, queue or
  GPU state changed.

## 2026-11-16 - Agent-orchestration review filed; no issue closed (docs-only)

- DONE: [`AGENT_ORCHESTRATION_REVIEW_2026-11-16.md`](AGENT_ORCHESTRATION_REVIEW_2026-11-16.md)
  records the measured cause of slow agent sessions - prompt size from container-directory launches
  and unbudgeted multi-hundred-KB document reads, not agent count - with the evidence queries, the
  P0-P3 plan, and the risk/validation note for each item.
- OPEN (owner/senior decision; 8 items in report section 7): container `Hrns/AGENTS.md`; the
  reading-budget amendment to `AGENTS.md`; moving rbassist prompt blocks to rbassist project scope;
  the dispatch rewrite (3-lane cap, <=2-file direct-work threshold); the preset retier and its one
  cost increase (`oracle` off `glm-5.3-flash`); concurrency 6->4; the eight missing rbassist skill
  names; and the worktree read-only list.
- NOTE: no config, prompt, code, queue or GPU state was changed by this review. The existing
  `deepseek-flash-max` shared preset and the one-project rule are treated as deliberate and are not
  proposed for replacement.

## 2026-11-16 - Fable architecture corpus tracked (40 reports + replays); no issue closed (documentation-only)

- DONE: `scratch/fable_architecture/` committed and pushed to `main` in two commits (`207f97a` plus
  the follow-up). The corpus was previously only an untracked working copy under the ignored
  `/scratch/`; the curated 15-file copy in `docs/research/fable_architecture_2026-11-16/` is
  unchanged and still the entry point.
- READOUT (stored-data, CPU only, no solves): E1 response-targeting gave no advantage over
  score-targeting; E2 minimum-norm inverse fails its stated decision rule; X3 held-out-engine skill
  < 0.6; X5 allocation comparison degenerate; S1 v7 vs v9-plus-constancy share 3 of the top 20 over
  3,414 stored designs. Net: the predictor-first route is weakened; the scoring-range/brief
  question is the live one.
- OPEN (owner decision, not a defect): the corpus's candidate routes, `OPEN_QUESTIONS.md` and
  `FABLE_RESEARCH_REQUESTS.md` remain unactioned — the commits authorise no implementation, config
  or objective change.
- NOTE: the subtree is ~42 MB with ~34 MB of binary evidence (`.e1/descriptors.pkl`,
  `.fable/rows.pkl`, `.s1/records*.jsonl`, `.x3/extended.npz`). Removing it would need a history
  rewrite, so decide deliberately if the "about the data, never the data itself" rule requires it.

## 2026-11-16 (23:30) - BoTorch round 2 LAUNCHED (ath14/corelaw/hvlaw, 25 screens each); readout open

- LAUNCHED: night `bo_multityp_r2_2026-11-16` detached (controller pid 41600, 22:03:34), admission
  packet `docs/queue/bo_multityp_r2_2026-11-16.admission.json` = owner release record for the
  three remaining staged arms; plan/readout rules `docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md`
  §5 (per-arm: cohort-baseline screen J vs arm best; never pooled; SCREEN-ONLY by design — no
  verified finalist).
- OPEN (readout, after the night drains): `tools/night_status.py` + plan §5 metrics per arm +
  hifi_rescore on winners; GUI arms populate under Bayes → Studies.
- DONE (readout 2026-11-17 04:05Z): night drained (7/7 jobs exit 0, 23:03 local). ath14 best
  5.3386 BEAT its cohort baseline 5.3737 (baseline reached at attempt 14); corelaw 3.3308 vs
  3.2325 and hvlaw 3.3533 vs 3.1028 did not beat within 25 screens. See CONTINUITY same date.
  Remaining: hifi_rescore on the ath14 winner + normalised same-basin distance.
- OPEN (from §7 of the plan, unchanged by this release): Crowe/rolled/rounded-rect typologies need
  cohorts (~25 CMA screens each) to reach the 100-row BoTorch floor; the atlas cohort stays
  ineligible (BEM pin mismatch); Crowe bridge study-worker install is separate work.
- NOTE: screen-only arms are directional (owner decision 2026-11-15 stands); use
  `comparison-25`-style budgets for any decision-bearing rerun.

## 2026-11-16 (23:20) - v9 CLOSED: all gates G0-G13 green; production default unchanged

- DONE: full v9 implementation + registration (opt-in only) — schema (`targets/profile.py` + spec fields), `objective/scalar_v9.py`, dispatch (`9: _score_v9`), config requirements + first-anchor feasibility, catalog/cohorts/dataset identity, scoring_view profile display truth, GUI corridor display (G13 chart==scorer exact), schema test file, anchor-below-f0 + corridor>=2 rule fixes, 260-test wave + full filtered suite green.
- RESIDUAL (other lanes / known): b8 static check (pre-existing, `study_jobs.py:829`, BO-GUI lane's module); klangfilm tool tests green standalone / xdist-load-sensitive. Both documented; neither belongs to this wave.
- OPEN (owner): smooth-brief re-baselining for non-CD night-queue cells before the next ranking pass (fairness table: Crowe 6.84 vs Klangfilm 8.92 on the same brief).
- OPEN (owner, v10): loading-oriented profile-aware objective stays gated per the amended RFC (v6 untouched).

## 2026-11-17 - Klangfilm Phase B core built; acoustic gate open

- DONE (CPU geometry): monotone H/V slope core + independent Lamé exponent + swept beak, exact legacy
  nesting, 12 focused tests, geometry preflight with two plots.
- OPEN (owner): register the digest-bound family adapter (with `size_policy`), mesh-validate B1-B3, then
  solve A0 vs B1/B3 with the identical solver/grid/source and both scoring policies.
- LIMITATION: no returning lip (needs a section-normal spine parameterisation) and no BEM for Phase B;
  the driver source cap remains the existing assumption.
- DECISION RULE (fixed): Phase B is worth optimizing only if BW_H/BW_V in 1.2-5.6 kHz land within +-10 deg
  of 80/50 and Var(DI) drops >= 25 % vs A0, with no new -6 dB lobes and load not worse.

## 2026-11-16 (23:15) - v9 G13 GUI corridor + schema lane landed; consolidation gates open

- DONE: G13 chart==scorer corridor display (charts.js/app.js + `tests/test_gui_corridor_v9.py`)
  and schema-lane refusals (below-f0 anchor, >=2 corridor anchors) with
  `tests/test_target_profile.py`; 132 focused v9/GUI tests green, both JS files syntax-checked.
- OPEN (consolidation): full filtered suite; G0-G13 evidence summary into CONTINUITY; owner
  smooth-brief re-baselining decision.
- The v9 dispatch line remains registered; G13 did not fail.

## 2026-11-16 (22:30) - v9 implemented under the amended gates; GUI corridor lane in flight

- DONE: Target schema + `targets/profile.py` (corridor/target validation, anchor-below-f0 refusal); objective v9
  (cov_profile, envelope rip, di_roughness, optional hf_floor, diag/distd unweighted); `bw8k_floor` refusal; dispatch
  + config v9 requirement + K-law feasibility via first-anchor preferred; catalog/cohorts/dataset profile identity
  keys; scoring_view v9 profile emission + level-less DI truth; G11/G12 + fixture gates green; old-J replay exact.
- OPEN (in flight): GUI corridor display lane (charts.js/app.js payload rendering + G13 chart==scorer equality) —
  a G13 failure reverts the v9 dispatch line before the final consolidation commit; schema-lane test file
  (`tests/test_target_profile.py`) lands with that lane's completion.
- OPEN (final gates at consolidation): full filtered suite; G0-G13 evidence summary into CONTINUITY.
- OPEN (owner, from evidence, unchanged): smooth-brief re-baselining decision for non-CD night-queue cells.

## 2026-11-17 - Klangfilm HV Stage A measured: no useful acoustic authority

- DONE: controlled A/B (A0 / A1 H-only / A2 V-only) with identical solver, source and frequency grid;
  evidence in `docs/evidence/klangfilm_hv_2026-11-16/AB_REPORT.md`, `ab_report.json`, `ab_plots/`.
- FINDING: throat-only H/V offsets move the -6 dB pattern by <= 2.74 deg and worsen both scoring
  policies (smooth +0.256/+0.129, CD +0.340/+0.127). The pattern is set by the mouth and rollback,
  not by the entrance tangent.
- OPEN: Phase B monotonic integrated-slope core plus independent beak/rollback, then its own BEM gate.
- NOTE: the arm runs used a pinned HEAD snapshot because the working tree was briefly inconsistent
  (objective v9 dispatch table mid-edit); no other lane's files were modified.
- LIMITATION: the driver source cap is still the existing model assumption; no 80x50 CD claim.

## 2026-11-16 - BoTorch GUI source-audit handoff: core implemented; P3 + browser acceptance open

- DONE (per `docs/research/BO_GUI_SOURCE_AUDIT_HANDOFF_2026-11-16.md`; CONTINUITY same date): P0
  read-only observation→physical-artifact bridge with GET-only API and zero-BEM guard; P1
  Results/Horns/Explore workspace with durable URL selection and cost-framed verify action; P2
  evidence-truth view models (calibration sections, `not recorded`, proposal explanation, target
  integrity, TuRBO/Pareto payloads). Focused suites green (51 tests + node checks + lifecycle +
  compileall); live GPU search untouched.
- LANDED (P1 polish, 2026-11-17): `tests/gui_study_results_lifecycle.mjs` + pytest wrapper import
  the real module graph from disk (relative imports resolve on a file-URL import; `three` stays a
  lazy dynamic import behind view3d/balloon fallbacks), covering mount → default selection →
  Inspect click → detail/geometry/acoustics fetches + pushState selection + inspector repaint, and
  missing-artifact rows stating their reason. Both harnesses green; closed the study_results
  test-bound gap.
- OPEN (zero-solve parity): the legacy authoring Execute tab still renders a "Solve in 3D" button
  that `tests/gui_study_lifecycle.mjs` pins by exact string; Results surface is clean. Decide
  whether to rename/demote there too and update the pinned test in the same commit.
- OPEN (P3, not started): cross-method comparison arm (objective/brief/source parity gates, no
  shared J ranking), incumbent-geometry evolution viewer from stored snapshots only, payload-budget
  audit (keep heavy mesh/curve data off the 128 KB phase panel), and the numerical GPU/CPU verify
  metrics separation.
- OPEN (acceptance, needs an eyes-on/browser pass): acceptance tests 3, 9-10 of the handoff
  (cross-method visual equivalence on symmetry quadrants/rolled mouths; ordinary CMA
  Runs/Elites/Evolution/Verify/Balloon/Sandbox regression in a real browser; desktop/mobile +
  light/dark + screen-reader labels).
- NOTE: a concurrent v9-registration break (`SUPPORTED_OBJECTIVE_VERSIONS` vs
  `_OBJECTIVE_SCORERS` disagreement) briefly made `search.evaluate` import raise and forced a
  temporary removal of one zero-BEM monkeypatch from `tests/test_gui_study_designs_resolver.py`;
  the concurrent session completed the v9 wiring the same evening and the guard was restored
  (19/19 resolver tests green).

## 2026-11-16 - Fable architecture evidence dossier delivered; decision items open

- DONE (read-only): 15-file dossier tracked at `docs/research/fable_architecture_2026-11-16/`;
  tracked digest `docs/research/FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md`. Snapshot
  `601be8c`; citations hold at `0750a30`. No code/solve/queue change.
- OPEN (cheap, zero-GPU; would change architecture): (a) generic-GRID pre-mesh extent vs actual
  meshed bbox false-refusal count; (b) screen-vs-verify rank correlation (top quartile); (c)
  held-out GP ranking at 100-231 rows; (d) refusal-margin classifier (AUC) to decide feasibility
  model vs envelope filter. Exact procedures and predeclared failure thresholds are in the dossier
  `OPEN_QUESTIONS.md`.
- OPEN (owner/Fable): point 80x50 vs region 60-90 H / 40-60 V intent (the in-flight v9 corridor
  objective currently imports a missing `targets/profile.py`); whether the 600x480x480 mm envelope
  is product truth or a hypothesis; whether a shared geometry representation is worth its cost;
  whether an adaptive search supervisor is premature while scoring is contested.
- NOTE: the 12 v3 handoff source documents (`00_START_HERE` ... `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL`,
  including `03_FABLE_DISCOVERY.md`) are co-located in `docs/research/fable_architecture_2026-11-16/`.
- NOTE: the refusal taxonomy is unreliable for policy use - post-mesh envelope and prefixed family
  `invalid_envelope` errors both surface as `invalid_geometry` (`evaluate.py:1546,1580`), and the
  graded infeasibility penalty is unreachable for native families. No fix was applied.

## 2026-11-16 - V2A timing endpoint correction landed; external v9 import blocker

- DONE (CPU geometry): warped-quintic timing law, analytic endpoint derivatives, tests at
  u50 0.35/0.50/0.65 + 20 mm hold, regenerated cuts/T2/mesh evidence. No solve or queue change.
- OPEN (external, not this change): the working tree's uncommitted objective v9 registration
  (`objective/versions.py` includes 9) does not yet update the `search/evaluate.py` dispatch table,
  so importing `search.evaluate` raises RuntimeError. The V2A config-load test is blocked only by
  that concurrent partial change; it is not a V2A regression.
- OPEN: the addendum's T0 screenshot audit, 40-80 mesh DOE, acoustic pilot and Phase 2 geometry
  remain unauthorised/open.

## 2026-11-16 (21:05) - Fairness table delivered; P1 v9 implementation begins under the amended gates

- DONE: Crowe/Klangfilm matched re-score with exact identity replays (docs/evidence/CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md); RFC amended per owner review (mode split, floor refusal + explicit hf_floor, anchor-vs-f0 refusal, v6 untouched with future v10, corridor GUI spec; gates G0-G13).
- OPEN (implementation, gated): v9 implementation — Target schema (`target.coverage_profile`, mode/interpolation validation, anchor-below-f0 refusal), `objective/scalar_v9.py` (cov_profile, per-frequency-envelope ripple, di_roughness, optional hf_floor, diag/distd reported unweighted), versions dispatch + config validator, catalog/cohort target-identity keys, scoring_view profile arrays + GUI corridor display (G13). Registration ONLY after G0-G13 pass with pasted output. v10 stays owner-gated and out of scope.
- OPEN (owner, from evidence): the smooth brief is now proven the fair basis for Crowe-class non-CD horns (6.84 vs Klangfilm 8.92 on the same brief); decide whether night-queue non-CD cells re-baseline onto the smooth brief before the next ranking pass.

## 2026-11-16 - Klangfilm HV Phase A geometry done; acoustic gate open

- DONE (CPU): H/V throat-core family, 71 focused tests, preflight + contact sheet, measured-lawful
  Stage A search box.
- OPEN (owner): authorise the Phase A screen (A0 vs A1/A2, equal solver/source/grid, frozen CD policy).
  No solve was launched; another lane's GPU job was live and untouched.
- OPEN: Phase B monotonic core + beak/shoulder only if Phase A shows insufficient early H/V authority.
- LIMITATION: negative mid gains are infeasible in this offset basis (monotonicity wall ~-0.04 mm), so
  the handoff's -8/-14 mm seeds are refused by design and the Stage A box is positive-only.
- LIMITATION: the v1 saved-recipe digest no longer reproduces (numpy/scipy version bound); regenerate
  before replaying historical `klangfilm-lame-v1` recipes.

## 2026-11-16 - V2A four-DOF geometry landed; acoustic gates and T0 open

- DONE (CPU geometry): four-DOF generator + c0-c3 configs + section/Jacobian tools + 17 focused
  tests; no solve, queue or objective change.
- OPEN (T0): identify the screenshot's saved design ID/config/mesh hash, capture ridges
  on/off/true wireframe and physical sections. The in-repo source check confirms
  `view3d.js` `buildRidgeGeometry` is a display overlay; do not change geometry to hide a line.
- OPEN (owner): authorise the 40-80 candidate mesh DOE and the four-variable acoustic campaign.
  The V2A addendum authorises no new solve.
- OPEN: Phase 2 returned lip/roll, rim setback, X crease, independent area-late/aspect-mid/late
  and a driver-informed source study; no knob is registered until implemented and tested.

## 2026-11-16 - Research library cleanup complete

- DONE: knowledge navigation, family applicability references, supplied research/source
  preservation and agent-skill routing for Claude, OpenCode and Codex.
- LIMITATION: supplied verification labels are inherited, not independently reverified;
  runtime skill activation was not exercised. No new acoustic/code validation implied.
- Existing acoustic and implementation issues below remain unchanged.


## 2026-11-16 - CROWE-inspired area/aspect v1 geometry landed; acoustic gates open

- DONE (CPU geometry): `crowe_hv_area_aspect_v1` + c0/c1 configs + section-cut tool + 18 focused
  tests; no solve, no queue, no objective change.
- OPEN (owner): decide whether to authorize the research document's 40-80 candidate mesh DOE or
  the `c1_frontier_bounds` search box. The V2 document authorises no new solve.
- OPEN: Phase 2 returned lip/roll, rim setback, X crease, `p_progress_start/rate` and the
  throat-length source study; no knob is registered until implemented and tested.
- OPEN: the 300 mm seed reaches 78/76 deg mouth wall angles. The frontier study must trade
  mouth/depth/area before any acoustic claim; the research document's go/no-go gates still bind.

## 2026-11-16 (16:30) - Klangfilm-Lame validation open

- OPEN (local): run shape-check/mesh on `hl__klangfilm_lame_curved_v1` (dof cap, symmetry, shell clearance, source tag 2); render vs reference.
- OPEN (local): small acoustic A/B of throat variants (raw 10.6 vs derived 2/5 deg) under a fixed source model; BEM vs bempp cross-check.
- OPEN: 3-D-normal outer shell, `follow_parent_stretch` tail mode, JMLC-derived parent (not implemented).

## 2026-11-16 (15:00) - Watchdog continuations queued; envelope 700 mm decision

- DONE: watchdog-stopped runs continued (resume or widened + reseeded), queue `home_day2_2026-11-16`.
- DECIDED (owner 14:48): KEEP the 600 mm envelope (no brief change; BO cohorts stay intact). Former question: brief_hash includes the envelope, so editing the landscape briefs in place splits
  every BO cohort (warm start, Tritonia, TwinRay). Options: (a) new `_w700` brief variants only for envelope-limited
  families (Crowe sections, Crowe-X, Klangfilm); (b) edit in place and rebuild cohorts; (c) exclude the envelope from
  brief_hash (scoring-identity code change).


## 2026-11-16 (14:35) - Klangfilm cell unapproved; Le Cleac'h saddle worktree-only; TuRBO results

- OPEN (owner): Klangfilm elliptical cell `hl__klangfilm_ellipse_smooth_v7` - look does not match reference 4.png
  (proportions). Decide: Klangfilm vs Le Cleac'h base for the three owner features (elliptical throat, rollback depth,
  front-arc radius); or implement the diyAudio bent variants (no equations published). Add unit tests before queuing.
  See docs/research/typologies/KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md.
- OPEN: Le Cleac'h saddle (worktree-agent-a4731ed7e21e33eee @ 22829bc) not merged; throat too short vs reference.
- OPEN: scoring agent branch worktree-agent-a527a7d28dc77734a @ 5af0048 - penalty (oa_excess_tol) and auto-widen were
  NOT integrated (concurrent review judged them unsafe/unvalidated); base-vs-hifi re-rank was not delivered.
- RESULT: TuRBO beats CMA on converged home cells (warm 3.762 -> 3.33 screen / 3.80 verify; Tritonia v8 5.69 -> 4.63 /
  5.48). Screen->verify gap 10-18 %: rank finalists on verify.
- OPEN: watchdog bound-pins today - R-OSSE `g_tmax` hi (0.85-1.0, generator max 1.0), TwinRay v8 `s` lo (0.6).


## 2026-11-16 (10:26) - Warm BO admission top-up and runner exit reporting

- Fresh warm cohort had 90 eligible rows: strict gate refused without solves. Added bounded 60-valid CMA data top-up and fresh 80+2 BO retry after Crowe-X; live 28-job dry-run passes.
- Fixed EOF/child-exit reporting race in source; 20 focused runner tests pass. Active process retains old reporting, so its exit 0 for the 90-row refusal is not BO success.
- See docs/queue/HOME_CONTINUATION_2026-11-16.md.

## 2026-11-16 (day) - Reviewed CMA/BO continuation and 80+2 verification budget

- Owner requested useful queue work through tomorrow morning, recent-run bound/convergence
  review, CMA data-building followed by BO and return to CMA, and two rather than six
  verifications per 80 screens. See docs/queue/HOME_CONTINUATION_2026-11-16.md and
  docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md for evidence, sequence and limits.
- Additive comparison-80x2 profile; no historical package/profile rewritten. Future BO
  preparation happens at runtime with strict >=100 usable row admission; failed prep
  prevents execution. Live day queue extension uses the existing detached controller.
- Tritonia v9 preserves fold/hygiene, modestly reopens historical bounds, uses two
  120-valid / 260-attempt CMA seeds, and passes 24/24 sampled CPU mesh checks. sigma .18
  clears the history-aware expected-hit floor (5.68); seed-optimum warning remains.
- Selective agent integration: GUI seed-policy display + tagged offline brief guard.
  Unsafe new penalty, incomplete command guard and unvalidated auto-widen were excluded.
  Rejected OSSE v8 winner falls from base #1 to DSP #12 in offline screen rescore;
  seed becomes DSP #3. This is not a verification result or proof of the new penalty.
- Le Cleac'h saddle remains worktree-only/unapproved; abandoned night-B entries are not
  pending. Original designs, held rolled families, datasets and running jobs preserved.
- Focused offline runner/geometry suite 82 passed; profile/prepare suite 21 passed;
  tagged preflight suite 17 passed; GUI/authoring/profile/prepare targeted suite 59 passed.
  No concurrent GPU solves or solver tests launched. Detailed wrapper checks in plan.

Local-only, 2026-11-16 (23:25) (**study solves table + on-demand 3D for a study design**):
- A study page now lists its own solves (`data.solves`, execute + decide) and each measured design has
  a **Solve in 3D** action. It writes a real standalone verify run
  `runs/<utc-ts>-studyverify-<hash6>` (config snapshot + `run.json.study_provenance` + the study's
  design), runs the existing `verify` body for that one hash, and `#/run/<id>/3d` renders it. One CUDA
  solve per click; the child takes the GPU lock and refuses when the lane is held.
- **Open:** the real GPU click-through and the 3D render were not exercised (the lane was busy with the
  night). Verify on a finished study once the GPU is free.
- **Open:** old study designs still need a fresh solve to be viewable; persisting curves/balloon per
  solved design (worker change, pin change) remains the follow-up if every design must be viewable
  without a re-solve.
- **Open:** `data.solves` coverage/ripple stay blank unless the observation carries a physical
  pareto/objective block; the normalized terms are deliberately never rendered as degrees/dB.

Local-only, 2026-11-16 (23:05) (**a night-file reload killed a running study; the registry still says running**):
- `a_turbo_ath14` (`studies.cli run --execute`, study `4f1e4851...`, package prepared 22:32:30) started
  22:32:30 and the runner's queue log has **no END line** for it: at 22:43:35 the runner reloaded
  `runs/nights/home18_a_2026-11-16.yaml` (edited while running) and started `a_lecleach_sm_s1234`
  instead. The package row is still `status=running, active=1` and `progress` is frozen at
  `proposed 2 / solved 2 / of 60`, so the study's Live tab will keep polling and reporting a dead run
  until it is reconciled. No solve was lost that mattered (2 of 60 calls), but the state is wrong.
- Cause: editing a night YAML while `run_campaign_night.py` is running reloads the plan and moves on
  without writing an END for the in-flight step, and the study package is never marked stopped.
- **Open:** reconcile an orphaned package run (worker gone + no open queue step for the study) to
  `unknown`/`stopped` so the Live tab and `run_status` stop claiming "running". Do not guess from age
  alone: a study can legitimately pause between solves.
- **Open (owner):** edit night files between jobs, not during one, or accept that the current job is
  killed. Two reloads today (`22:25:54`, `22:32:30`) each cut a different step.

Local-only, 2026-11-16 (23:00) (**a running BoTorch study was invisible in the shell**):
- Live night `home18_a_2026-11-16` ran `prep_a_turbo_ath14` then `a_turbo_ath14`
  (`studies.cli run --execute`, started 22:32:30) while Home said "GPU Idle", the lane panel said
  "not running", and the nav pill said "stopped search". Fixed: Status + Home carry a "Running now -
  night <name>" card with the step, kind, elapsed and a link to the study's Live tab; the sidebar
  carries a `NIGHT <step> - <kind>` line; and only the LAST unclosed queue START is labelled
  "running" (an abandoned step now reads "no END line"). `server.py` resolves the step's `--root`
  to a study id from that registry alone (walking all roots made the Status first paint >4 s).
- **Open:** the Live convergence chart is "results artifact is missing" until the run writes its
  results artifact; the KPI strip already advances from the attempt journal. Reading convergence
  from the attempt journal during a run is the next step.
- Runs page (`#/runs`): it now fetches `/api/status` + `/api/studies` beside `/api/runs` and shows the
  running night card plus a "BoTorch studies" table for the studies running right now (links to Live).
  Before this, `/api/runs` alone could never show a study: a study is a registry + package, not a
  `runs/<ts>-screen-*` folder. Completed studies stay on Bayes -> Studies.
- **Open:** the GPU lane lock card shows "stale" between solves (the lock's pid is the per-solve
  worker, not the study runner), and `tools/night_status.py` reports superseded steps as running.
- **Open (owner, unchanged):** this night was launched by the owner's `home18_a/b` plan while the
  bo_multityp arms remain staged; `bo_multityp_2026-11-16` arm 1 would still restart
  `bo_cov_s71001` from zero.

Local-only, 2026-11-16 late (**`feat/bo-gui` merged locally; `diagnose` proven on real studies**):
- Merged `origin/feat/bo-gui` (`b0f669d`) into `feat/sab-home-2026-11-14` (`5b78c6c`). **Not merged to
  `main`** - owner gate unchanged. The branch now contains the diagnostics artifact, the Bayes nav group
  and the study Live tab.
- `diagnose` verified against real studies with the bayes-venv: scalar n=185/d=6 41.9 kB, Pareto n=136/d=8
  112.9 kB; `loo.rows` == training rows, 25 points per active knob, 6 front ids, `hv_trace` non-decreasing.
  **Real bug fixed:** prefix hypervolume jittered *down* by 3.5e-15 (BoTorch box-decomposition order);
  clamped at the running maximum with `HV_REL_TOL=1e-12` plus a regression test that reproduces it.
- Fixed: dead `#/analysis/study/<id>` deep link ("Unknown view" - now `/overview`, `?phase=` honoured),
  Live tab first-load detection (`package_present` in the panel payload), `compare_methods.js` breadcrumb,
  and the stale balloon-route test.
- **Open (owner):** `bo_multityp_2026-11-16` still contains arm 1 (`bo_cov_s71001`), which already ran the
  20:08 pilot. Launching that night would re-run `prep_cov` and restart the study from zero observations,
  discarding its 25 solved designs. Drop or re-point arm 1 before the night runs.
- **Open (owner):** all prepared packages now fail the execution-code pin check because `gui/**` is inside
  `EXECUTION_CODE_FILES` and the GUI/study code changed. Finished studies cannot be resumed (expected); the
  three staged arms have no package and preflight clean, so their own prep job will bake current pins.
  Excluding `gui/**` from `EXECUTION_CODE_FILES` remains the owner's call.
- **Open (small UI):** the studies list header still links "Analysis reports" to the legacy CMA-era
  `#/analysis`; `#/analysis/studies` and `#/analysis/compare-methods` redirect correctly. No other stale
  `#/analysis/...` link exists in the static JS.
- **Open (tool):** `tools/night_status.py` prints "running job <id>" for abandoned nights whose queue log
  ends "finished <night> (exit 1); queue done" (`QUEUE_LOG_FRESH_S` is 24 h and the END pattern matches a
  job id, not the night). The authoritative "Running now (search processes)" line is correct; the stale
  lines only make the STEP-0 gate noisy. Evidence: `runs/nights/queue_home_e_2026-11-15.log` tail.
- **Open (latent, diagnostics lane):** `_slices` iterates `X.shape[1]` instead of `len(active_keys)` (a
  training matrix with unprojected inactive columns would emit `x{k}` slices); Pareto per-objective LOO
  uses the `select_subset` fit (cap 256), so a study above the cap can show fewer per-objective rows than
  training rows; `payload["size_bytes"]` undercounts the file by ~20 B. None triggered on today's studies.
- **Doc debt:** CONTINUITY still carries 547 `â€` / 65 `Ã` / 185 `Â` legacy mojibake sequences in pre-11-15
  entries (the merge kept the correctly encoded side and added none). Not repaired wholesale - it would
  rewrite ~800 lines of history for no functional gain.

Local-only, 2026-11-16 (**section-pucker / square-X 25x2 pilot; no active GPU job was interrupted**):
- The old `rf__section_axial_strong_v7` box was a visual-study box (fixed 417x203, depth 194-202,
  `h_depth_scale` 0.99-1.01, crown 18-22, fixed junction 32). It is now labelled visual reference only.
  The optimization cell is `rf__section_axial_home_v7` (width 480-600, height 220-420, depth 170-300,
  `h_depth_scale` 0.9-1.1, crown 10-40, junction 16-48, axial pucker 0-12/0-14; 8 active keys).
- 25x2 pilot (seeds 1234/5678): section home best **17.3982 / 17.3970**; square X best **8.8171 / 8.2046**.
  Square X is 9.2 J better and closer to the reference look.
- **Open, next:** create `rf__section_axial_home_v8` with `g_axial_v_mm` fixed at 0 (the pilot drove it to
  0.37-3.35 mm), `g_axial_h_mm` 0-12 optional, and junction bounds 12-48 (pilot pinned 16.0-16.1). Width
  is at the 600 mm envelope; if more headroom is wanted, the envelope must change, not the generator.
- **Open, next:** square X had 12/8 `invalid_envelope` refusals in 25 draws. Tighten the a_h/a_v/L/lip/wrap
  coupling or add a preflight filter before a larger run. Pilot best `sf_amt` is 0.42-0.47, below the 0.60
  visual seed; update the seed when the next cell is cut.
- **Open, decision:** square X is the better acoustic path but is a look-first square mouth (50 deg vertical
  at 700 Hz does not fit); decide whether to promote it or keep the 80x50 landscape target.
- 25 evaluations is a coarse pilot for 8 dimensions. A real comparison needs 60-96 per arm.
- GUI: restart/hard-refresh after pulling; the parameter catalog and the section-pucker bridge preview changed.
  The home optimization cell, the square-X cell and the strong visual reference are in group `home`.
- No solve was merged into any older campaign; `bo_cov_pilot_2026-11-16` finished at 01:47:41Z before the queue ran.

Local-only, 2026-11-16 (latest, **BO GUI cloud pass on `feat/bo-gui`; no solves**):
- `feat/bo-gui` is pushed but deliberately unmerged (merge gate: no study running). It adds `diagnose` (BoTorch LOO/slices/HV),
  the Bayes nav group and the study Live tab. `diagnose` is untested against a real study; run it locally on the fixture
  studies after the solves finish. 8 offline failures remain that are environment-only or pre-existing (see CONTINUITY).

Local-only, 2026-11-15 (**GUI full-circle globe; no solves**):
- `Directivity (isobars)` gains a `Full globe` mode beside `Rectangular | Globe`: the stored balloon
  is re-sliced around a closed 360° H/V great circle (the back half is interpolated from the existing
  sphere grid), so no new data or solves are required. `Globe` stays the ±90° cut half-circle.
- `charts.js::globePlot` draws a real circle for a ±180° span (rim, rings, f0 ring, one `±180°`
  label). `data.design_curves` now returns `angles360` + `polar_h360`/`polar_v360`, omitted when a
  run has no balloon. **Restart the GUI server after pulling**: the API process caches imports, and
  a stale process shows blank full-globe panels even though the static JS is current (`no-store`).
- Verification: `tests/test_gui_globe_full.py` + `pytest -k gui` pass; only the pre-existing
  `test_targets` failure on `examples/catalog.gui.yaml` remains (tracked in HEAD, unrelated).

Local-only, 2026-11-15 late (**BoTorch readiness: staged, still owner-held**):
- Closed in code: 25/30-screen budget profiles, `prepare_study --config/--brief/--budget-profile`,
  four registered v7 study tasks with >=100-row strict cohorts, GUI TuRBO card (Python + JS),
  `tools/bo_compare/preflight_arms.py`, and an optional night-runner `--admission` packet gate.
  Fused qLogEHVI now compiles and caches (ninja + MSVC vcvars64), so the Pareto fallback warning is gone.
- LAUNCHED 2026-11-15 20:08 (owner-authorised): single-arm pilot `bo_cov_pilot_2026-11-16` (cov, 231 rows, seed 71001, 25+6; the staged three use `comparison-25x0` = 25 screens and no
  verification per owner decision, i.e. screen-only arms with no verified finalist). The other three arms stay staged and unadmitted in `docs/queue/bo_multityp_2026-11-16.yaml`.
  Read `docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md` first.
- Still open (owner): brief/DI-slope decision and the lip/waist law (v7 J is what these arms optimise);
  the 17:15 solve pause; Crowe/rolled bridge typologies cannot execute in the study worker; Le Cleac'h
  and rounded-rect are ~25 CMA screens short of the 100-row floor. GPU/torch device policy is documented
  and intentionally CPU-float64.
Local-only, 2026-11-15 19:15 (**spiral admission decisions committed; release still owner-held**):
- The concurrent rolled-readiness pass approved the `hl__rolled_es_spiral_v7` cell at gate level in
  `docs/queue/rolled_readiness_2026-11-15/admission.json`, with the senior decision record in
  `docs/research/typologies/audit_2026-11-15/ADMISSION_DECISIONS.md`. `full_search_released` remains false: no
  controller was launched and no solve was released.
- The pilot freezes the existing v7 brief for comparability; the smooth brief stays an offline experiment. This
  does not settle the final-ranking brief: brief/DI-slope, lip/waist geometry, Crowe-section junction rebuild and
  night F remain owner-gated. Night E remains stopped; no new solves.

Local-only, 2026-11-15 19:00 (**GUI bridge cells viewable; home-horn packet; commit/push**):
- Resolved: all home-landscape cells appear in the GUI. The 8 stock cells are in `examples/catalog.yaml`; the 3
  bridge cells are in `examples/catalog.gui.yaml` and preview through `tools/geometry/gui_preview.py`. The sandbox
  renders 2D sections, 3D shape, sliders and tooltips; launch stays preview-only because the stock campaign cannot
  load their custom rows kinds. Live GUI verified; 186 GUI/parameter tests pass; `gen_param_catalog.py --check`
  passes.
- Open (owner-gated): brief/DI-slope decision, lip/waist geometry law, Crowe-section junction rebuild, night F.
  Night E remains stopped; no new solves.
- This commit also preserves the concurrent rolled-family documentation/evidence audit. No generator or solve
  behavior changed by that pass; preserve its source/config/run history.

Local-only2026-11-15 (**rolled readiness audit; no GitHub issue state changed**):
- Complete current pickup: `docs/research/typologies/audit_2026-11-15/HANDOFF.md` and `READINESS.md`.
- Two isolated spiral acoustic diagnostics completed under updated owner permission; no full searches or Bayesian jobs. New guarded30x2 spiral draft and26 load-checked frozen configs: `docs/queue/rolled_readiness_2026-11-15/README.md`. Source/objective/body/cost gates remain; admission held. Preserve all old D/E records and original designs.


Local-only2026-11-15 (**rolled readiness audit; no GitHub issue state changed**):
- Complete current pickup: `docs/research/typologies/audit_2026-11-15/HANDOFF.md` and `READINESS.md`.
- Two isolated spiral acoustic diagnostics completed under updated owner permission; no full searches or Bayesian jobs. New guarded30x2 spiral draft and26 load-checked frozen configs: `docs/queue/rolled_readiness_2026-11-15/README.md`. Source/objective/body/cost gates remain; admission held. Preserve all old D/E records and original designs.


**TOP PRIORITY (owner, 2026-11-15 17:15): brief / DI-slope scoring investigation before any new solves.**
- Night E paused: runner (11172) and controller (36556) stopped; `e_crowe_home_s5678` stopped at ~62/96 (62/62 valid rows rescore: smooth 6.83 vs base 17.06); GPU cleaned.
- The v7 fixed DI target (`di_slope_target 0`) and `diag` fixed-round reference are not supported by the listening
  literature; there is no primary source for the "Harman 1-3 dB/oct" claim. Settle the objective/brief before
  queueing anything. Sources: `docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md`,
  `STARTING_SEEDS_PLAIN_2026-11-15.md`, `SCORING_NON_CD_SOURCES_2026-11-15.md`.
- Geometry law gap: current cells have no true under-surface lip return and no waist term; the Crowe-section mesh
  also has a 153-176 deg outer-body/lip fold with inverted triangles. Fix/decide before more GPU.
- GUI typology exposure (resolved 2026-11-15): 8 stock-loadable home cells in `examples/catalog.yaml`; the 3 bridge
  cells in `examples/catalog.gui.yaml`; the sandbox preview now runs them through `tools/geometry/gui_preview.py`
  in a fresh process (2D/3D, sliders, sections). Launch stays disabled for the bridge cells because the stock
  campaign path cannot materialize their custom rows kinds; the GUI shows a `preview only` pill. Live GUI restarted
  and verified: 56 typologies, all 6 audited cells present, bridge previews `available=True`. The generated parameter
  catalog now includes the 3 GUI-only cells (`source_status: gui-only`, `preview_only: true`) so the sandbox has
  knob docs/tooltips; `tools/gen_param_catalog.py --check` passes. Tests: `tests/test_gui_bridge_preview.py`
  (7 passed) plus the 179 GUI/param tests = 186 passed. Do not queue night F or new Crowe/Crowe-X/ES solves until
  the owner signs off on the brief and the geometry law.
- Commit scope when requested: include `examples/catalog.gui.yaml`, `tools/geometry/gui_preview.py`, the two
  `rosse_rect` bridge files, the 5 new home cell configs, `hl__crowe_es_biradial_rr_v7.yaml` (it is listed in
  `examples/catalog.yaml` and currently untracked), the decision-packet docs/images, and the GUI/param/test changes.
  Do not include `scratch/` or other sessions' WIP (the rolled-family handoff/evidence folders).

Local-only, 2026-11-15 16:45 (**biradial fix merged; four cells rendered; scoring research; owner decisions open**):
- Resolved: biradial throat-blend fix merged (7124902); biradial refusal cause = US4308932A cone closure
  (`rm >= r0 + tan(a) L`), new box 64/64 valid; ES-spiral `resample_strict` + `budget_counts: valid` set;
  four cells rendered and visually reviewed (sheets in `docs/research/typologies/img_biradial_crowe_2026-11-15/`).
- Open: owner decision on base vs smooth brief for night F; whether to run the biradial at all (no waist/lip law);
  whether to invest in a lip/wrap or waist term before more Crowe-X/ES GPU time; `diag` fixed-round reference
  structurally penalises rectangular mouths; no primary source for the "Harman 1-3 dB/oct DI slope" claim;
  night F not written; OSSE rounded-rect BoTorch registration waits for >=100 rows. Full detail:
  docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md s8.
- Night E running: Crowe home seed 1234 done, smooth rescore best J 6.84 vs base 16.92; seed 5678 running.
  Objective mesh check: Crowe-section outer-body/lip junction has a 153-176 deg fold with inverted triangles
  (inner flare smooth); scores provisional, fix the junction before print/final ranking.
- External research (2026-11-15): `HORN_WHITEPAPERS_2026-11-15.md` (annotated bibliography, BEM/metrics/
  optimization checklist, corrections) and `STARTING_SEEDS_PLAIN_2026-11-15.md` (six 360-degree turntables,
  plain-language decision brief). K-law correction: A=0.9B -> 496/794 mm at 700 Hz; 480 mm V holds 50 deg only
  to ~1157 Hz. 270-degree wrap and waist/bow-tie claims remain unverified/visual.

Local-only, 2026-11-15 15:50 (**biradial / Crowe / rolled-mouth study handoff; no GitHub issue state changed**):
- Open: merge biradial throat-blend fix (worktree `fix/biradial-throat-blend`); biradial box 32/64 refused (cause
  unknown); ES-spiral cell needs resample_strict; render/owner look review of the new cells; scoring decision
  (base vs smooth brief; is `diag` fair for creased rectangular mouths); verify DI-slope literature numbers;
  night F not written. Handoff: docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md.


Local-only, 2026-11-15 14:25 (**BO cohort encoder fix, BO data gate, nights D/E; no GitHub issue open**):
- Fixed: `bo/data.py` refused `morph_target = 0` rows, so night B trained on 0 rows and never solved.
- New gate: `prepare_study.py --min-rows` (default 100); BoTorch only on typologies with existing data.
- Crowe: replica cell kept running (owner); home-sized `hl__crowe_panel_home_v7` queued in night E (2 x 96 + verify).
- Open: ES450-style biradial throat not round (generator fix needed); study rows do not feed
  `study_cohort`; Crowe swept-H construction limited to depth <= 0.57 x width; OSSE rounded-rect needs a
  registered BO task once night E gives it >= 100 rows.


Local-only, 2026-11-15 (**section-based H/V relief extension; no GitHub issue state changed**):
- Done: exact zero-pucker control, independent H/V relief, source/attachment preservation,
  three seeded configs, all 72 corners, 192 random box meshes, 145 CPU checks and 15 renders.
- Running: home_section_pucker_2026-11-15, control/moderate/strong 48 attempts each plus
  top1 verification; controller 10256. Five sampled geometry refusals are charged flat.
- Open: acoustic readout, 5D treatment basin estimation and spatial mesh convergence.


Local-only, 2026-11-15 (**verification clarification**):
- Confirmed section-study verification refines the frequency grid (18 to29 points), with
  unchanged mesh spacing. Score sensitivity is frequency-related; spatial convergence is untested.


Local-only, 2026-11-15 (**horn pilot completion; no GitHub issue state changed**):
- Done: four searches, 128/128 valid screen evaluations, successful top1 verification
  for every arm; both controllers exited0. Results and winner renders published.
- Open: 5-9 percent screen-to-verify score sensitivity, further acoustic mesh convergence,
  meeting target loading/coverage, and exact reference exterior/intermediate geometry.


Local-only, 2026-11-15 (**ES-600 section correction; no GitHub issue state changed**):
- Done: independent drawing readings, section-based surface/body, 126 CPU checks, 63/64
  sampled feasibility, four-seed gallery with cut views and versioned replay.
- Queued: home_crowe_sections_2026-11-15, search32 + top1 verify, controller31224 after42084.
- Open: acoustic verification/readout, exact intermediate reference sections and exterior
  fillets, acoustic mesh convergence, and print/structural acceptance. Reconstruction is approximate.


Local-only, added 2026-11-15 (**original rolled-rectangle geometry pilot; no GitHub issue state changed**):
- Done: source research/corrections, original base + moderate/strong H/V-pucker geometry,
  round-coupling/envelope/mesh checks, 64-sample feasibility per box, versioned replay adapter,
  sequential verification helper and multi-angle gallery.
- Queued: `home_rolled_rect_2026-11-15`, three budget-32 arms + top-1 verify each, after active C.
- Open: acoustic loading/coverage/diagonal/DI/flatness evidence, winner readout, print mounting
  and structural checks; stock GUI/catalog registration is outside this experimental slice.
- Existing B preparation failed with needs_initial_data n=0; preserved, not fixed by this task.


Mirror of the GitHub issues at https://github.com/llevaachingada/Hornfab/issues. ID, title, status, owner, plan reference.
Updated in the same commit as `docs/CONTINUITY.md` on every push. Last synced 2026-11-14 (**owner decisions executed: cohort gap closing (+50 resume at 38e5b1f), caps 12kâ†’24k on the four live configs, batch-12 approved for heavy verify/final-style runs; plus the scalar-Bayes and CI work; no GitHub issue state changed**).

Local-only, added 2026-11-15 (20:3x local): BO GUI cloud handoff written; no GitHub issue state changed.

Local-only, added 2026-11-15 (02:0x local) (**BO GUI slices 1-6; no GitHub issue state changed**):
- Done: read-only BO view models + study-root index + study chart panels + compare-methods board
  + per-proposal prediction/trust-region/hyperparameter persistence (worktree `feat/bo-gui`).
- Done: safe slice 6 - queue writes a new night file and never launches a runner; child study
  clones the parent spec with an explicitly chosen policy.

**OPEN / DO NOT FORGET - merge after the testing finishes:**
- Merge gate: wait for `bo_vs_cma_2026-11-15` AND `sab_home_gpu_rest_2026-11-15` to finish, then
  confirm `tools/night_status.py` shows no runner/Julia host and no queued study.
- The branch is committed and pushed as `origin/feat/bo-gui` (`ef6a38a` + merge `56a3eb8`);
  merge `feat/bo-turbo-pareto` first if needed, then `feat/bo-gui`; resolve docs in the merge
  commit. Owner decision 2026-11-15: keep it branch-only until the nights finish; it is 21 commits
  ahead of `origin/main` because it contains the in-flight `feat/sab-home` integration.
- Run `compileall` + the offline GUI/study suite; check a new package preflight.
- Do not merge while any study is queued/running: `hornlab_search/gui/**` is still in
  `EXECUTION_CODE_FILES`.
- Open: scalar-arm Pareto metric rows/hypervolume comparison needs a CPU job (the board shows the
  missing state rather than computing coverage/ripple from J).
- Open: partial-dependence curves are optional; the lengthscale sensitivity bar is the first pass.

Local-only, added 2026-11-15 (09:3x local) (**report deeper analysis; docs only**):
- Open: the study journal does not log adaptive-pick predictions (needed for calibration without a replay).

Local-only, added 2026-11-15 (09:xx local) (**BoTorch vs CMA collaborator report, docs only; no GitHub issue state changed**):
- Done: `docs/status/2026-11-15-bo-vs-cma/` (README + index.html + data.json). BoTorch wins the matched home-task test.
- Open: cold-start BoTorch vs CMA comparison (this test was a warm start from a converged CMA optimum).
- Open: TuRBO/Pareto modes (branch feat/bo-turbo-pareto) and the night re-order branch are not on main yet.

Local-only, added 2026-11-14 (15:3x local) (**project atlas tool + snapshot; no GitHub issue state changed**):
- Done: `tools/atlas/` whole-project report; snapshot at `docs/atlas/` (GitHub Pages).
- Open: atlas verdict thresholds (`RULES` in build_atlas.py) are first-pass heuristics; tune after owner review.

Local-only, added 2026-11-14 (15:2x local) (**GitHub Pages enabled from main /docs; no GitHub issue state changed**):
- Done: Pages live; `docs/.nojekyll` added. HTML reports under `docs/` now have browser links.

Local-only, added 2026-11-14 (15:1x local) (**collaborator status brief, docs only; no GitHub issue state changed**):
- Done: `docs/status/2026-11-14/` brief (README + index.html). Open items it lists are the existing ones below.

Local-only, added 2026-11-14 (06:4x local) (**GUI / data-viz UX pass; no GitHub issue state changed**):
- Done: decision-first analysis report, verdict-first run detail, Boundary Lab isobars + Globe view,
  single New run entry, shared viz kit (docs/GUI_UX_PASS_2026-11-14.md). Front-end only.
- Open: Quick launch cannot carry family-bound edits; analysis bounds actions say so. Typology-config
  briefs are not saved brief files, so `?brief=` prefill for them shows a note instead.

Local-only, added 2026-11-14 (01:xx local) (**CI repair hardening; no GitHub issue state changed**):
- Done: CI now installs `ribs==0.12.0` (QD failure-isolation suite runs on CI: +38 real tests); fixture drift guard for
  the S11 pilot overlays. Verified #56 validator against tampering and #55 merge integrity.

Local-only, added 2026-11-13 (20:4x local) (**CI repair; no GitHub issue state changed**):
- Done: main CI red on 8 env/portability clusters fixed (manifest locator portability + fixtures, PureWindowsPath in
  bo_sensitivity, requires_ribs, mesher split/gates, sklearn in CI + `[analysis]` extra, pinned SHAs in marker test;
  freq_batch_size was fixed separately on main in 50b6f06).
 No tolerance/expected value changed; evidence sha256 unchanged. Then PR #55 refresh + merge.
Local-only, added 2026-11-13 (20:2x local) (**S8/S7 analysis panels landed; no GitHub issue state
changed**):
- Resolved: the four S8/S7 tools now render in `#/analysis` â€” geometry descriptors (scale-aware
  table + resolver SHA + navigation map), hypothesis cards (parents, six roles, ablations), equal-cost
  QD/Pareto (ledger, front, frozen reference) and advisory surrogate validation (split, Brier,
  regression, OOD proposals). `gui/data.py` exposes `tool_files` and selects the newest complete
  keyed `surrogate_validation-<hash>.json`, listing all candidates. 432 GUI tests pass, exit 0.
- Open (by design): the QD scatter plots only the nondominated `arm.front`; the payload carries no
  full eligible list, so excluded/duplicate rows stay in tables.
- Open (by design): surrogate candidates are disclosed but not selectable; the newest complete
  payload is shown. Add a selector only if a real multi-run workflow needs it.
- Open (by design): the tools refuse `--out` under `runs/`, so the GUI needs
  `--analysis-dir <set>`; no exception was added.

Local-only, added 2026-11-14 (~02:0xZ) (**speed program ADOPTED: solver 38e5b1f at -25/-28% wall, parity ~1e-5 dB, zero spill; batching default rejected by the pre-declared bar; A5 re-based on measured anchors; no GitHub issue state changed**):
- Adopted: beat pin â†’ `38e5b1f8ca840ebf6351c54611a08fedb1a0750f` (`pyproject.toml` + `TOOLCHAIN.md`); whole-candidate
  wall âˆ’24.7 % (osse) / âˆ’28.0 % (ath); parity max diffs â‰¤ 4.4e-05 dB / 3.6e-05Â° (bar 0.039 dB / 1Â°, computed by hand â€”
  `compare` is report-only); `solve_hash` identical across all 12 arms; zero shared spill anywhere (lane watcher shared
  peak 80 MiB; `tools/bench/run_with_memwatch.py` now exists for future runs). Evidence: `docs/evidence/SPEED_ADOPTION_2026-11-14.md`.
- Rejected (pre-declared bar): batch-12 default (median ratios 0.8512/0.8653 > 0.85 after the mandated repeats) and the
  batch-4 fallback (0.8771/0.9131). `solve.freq_batch_size` lands as default-None provenance key; env var = owner trial knob.
- Re-based (measured): `solve/feasibility.py` fused-CUDA anchors â€” 20,237 refusal falsified by measurement; 24,973
  quarter-DOF fits (risky band); refuse â‰¥ ~26k; `tests/test_solve_feasibility.py` re-based by fix. Cap values unchanged
  (owner decision).
- Next: E9 production relaunch (print night's un-run jobs) under the adopted solver â€” **COMPLETE:
  exit 0 at 2026-11-14T02:25:18Z, 400/400 evals at `38e5b1f8â€¦`, zero shared spill on the production tail
  (watchdog final record `scratch/speed_runs/memwatch_e9.json`); production rates 45.22 s/cand (ath) and
  52.33 s/cand (osse-s5678) after the expected one-time cold-cache re-solve.**
- Still open from earlier: A1 cache namespace means the pin swap invalidates solve caches ONCE (expected; first
  post-merge runs re-solve at `38e5b1f`).

Local-only, added 2026-11-13 (20:2x local) (**speed program: review landed + E0 done + C3/C4 landed; no GitHub issue state changed**):
- Resolved (senior review): `SPEED_ARCHITECTURE_PLAN_2026-11-13.md` ADOPTED with corrections (Â§14); all 12 open questions
  decided: one rep per arm + hardened repeat rule (fresh roots, median-of-3, gray median rejects); keep `--budget 1`;
  `solve.freq_batch_size` config key behind a rule-3 note; one install SHA `38e5b1f`; keep 0.039 dB / 1Â° and record max
  diffs (0.0 expected; no bitwise gate); no non-fused control; ceiling sweep stays after Round B; A5 refit (`8NÂ² + c`,
  â‰¥ 30 % refusal margin) only after measurement; mesher pin stands â€” **C5 answered: the pin predates upstream `d740c28`**
  (fetch + `merge-base --is-ancestor` exit 1), bump is a post-beta program; `worker_restart_every` unset in arms,
  batch-4 fallback on spill; batch 12 lands in the two print configs at the adopt merge.
- Done: **E0** â€” resume night finished runner exit 0, 200/200 rows. Deviation recorded: 1 of 200 was a transient
  `solve_failed` (10054 worker reset, n=187), left as an honest failure row, not re-run.
- Done: **C3** `solve.freq_batch_size` (config key + â‰¥ 1 validation + `_prepare` plumbing; env fallback preserved when the
  key is absent; refused for `bempp_cpu`; offline tests pass; `config_sha` unchanged for key-absent configs) and **C4**
  `tools/bench/run_with_memwatch.py` (spawn + attach modes; shared-usage/WDDM-spill observer; offline tests pass; live
  attach smoke sane). Landed before Round A so the arms' `lib_shas` record a clean HEAD.
- Done: **C5** mesher ancestry check (zero GPU).
- Running: **E1b** Julia CPU suite + analytic-exterior raw-evidence rerun (first attempt archived 0 bytes â€” julia.exe's
  Windows wrapper drops `Start-Process` redirections; now under `cmd /c` with inline exit stamps). **Round A is armed
  behind E1b** (`-WaitPid` chain). Execution authority: `docs/queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md`.
- Open (from the review): A5 stale `20,237 â†’ refuse` test must be RE-BASED (fix, not weaken) at the merge, per plan Â§14.


Local-only, added 2026-11-13 (20:3x local) (**CI speed live; C3 contract break fixed; no GitHub issue state changed**):
- [measured] CI test step 385.3 s -> **201.9 s** (job 8m18s -> 4m15s) with one trigger + pip cache +
  `-n 2 --dist loadscope`. Skips unchanged (296-297).
- Fixed: 66d8509's `SolveSettings.freq_batch_size` (documented `None = absent`) was missing from
  `tests/test_config.py::OPTIONAL_FIELDS`; 5 example-param failures. Declared optional, assertions
  untouched. The new `Docs check` job surfaced it in 31 s.
- Still open: the 23 pre-existing CI failures below (unchanged ids).

Local-only, added 2026-11-13 (20:0x local) (**CI topology integrated; two pre-existing repo issues surfaced**):
- Applied: single CI trigger (PR + main), pip cache, docs paths ignored by the full job, a new
  `docs.yml` fast lane, and `-n 2 --dist loadscope` in CI. No GitHub issue state changed.
- **RESOLVED 2026-11-13 (21:0x local): `gen_param_catalog.py --check` can be gated.** The
  hand-maintained search/solve keys moved to `docs/reference/SEARCH_CONFIG_KEYS.md`; the generated
  `PARAMETERS.md` carries a pointer emitted by `catalog.render_parameters_markdown`. `--check` passes
  and `docs.yml` gates it. Remaining follow-up (optional): teach the generator to emit those keys and
  delete the separate file.
- **Fixed: `.gitignore` `reference/` was unanchored** and matched `docs/reference/`, silently ignoring
  every new file added there. Now `/reference/` (root CAD dir only).
- Note for the docs job: `--check` imports the mesher (29/33 `code_ref`s), so `docs.yml` installs the
  pinned mesher. Do not add it to the main test job â€” it would turn 199 `requires_mesher` skips into
  runs. Both gates are green on main as of `0e1364a` (CI 4m21s, Docs check 27s).
- **Open (pre-existing): CI is red on main** â€” 23 failed + 24 errors, identical on the four commits
  before the test-suite change. Groups: `test_search_qd_failure_isolation` (10, ribs missing in CI â†’
  ImportError instead of a skip), `test_bo_sensitivity_real` (2, absolute path baked into the test),
  `test_tools_analysis_parameter_study` (4, KeyErrors), `test_tools_analysis_geometry_descriptors` +
  `_hypothesis_cards` (2, no `hornlab_mesher` in CI), `test_design_generated` (1),
  `test_tools_experiments_manifest` (4 + 24 errors, local `scratch/` data). Needs its own lane.

Local-only, added 2026-11-13 (19:3x local) (**test-suite speed + GPU lane; no GitHub issue state changed**):
- Applied (branch `test/testspeed-2026-11-13`, merged to main): `pytest-xdist -n 6 --dist loadscope` with
  single-thread BLAS/OpenMP caps takes the offline suite from **18.2 min to 5.9 min (3.1x)** at equal
  coverage; `-n 8` measured worse (poles 56 s -> 186 s) and is excluded.
- GPU lane now runs the shipping **fused CUDA** path (`cuda_fused=True` in `test_solve_beat.py`,
  `meta["cuda_fused"] is True` pinned); `slow` retired from `tests/`.
- GPU lock default changed to `warn` (was refuse); `HORNLAB_GPU_LOCK=refuse` for nights/measurements.
- **Open / pre-existing failure:** `tests/test_tools_experiments_manifest.py` fails 4 + 24 collection
  errors with `FileNotFoundError` on a local path, under a *serial* run in `oc-wt/testspeed`. It is not
  caused by this work. Owner or the file's author needs to decide whether it should be a `local_data`
  skip (the audit's category) or a fixture that materialises its input.
- **Open / pre-existing gap (safety):** 18 `requires_botorch` tests never run in CI or the default venv;
  they need the isolated `bayes-venv`. Decide: `[bayes]` CI job or a documented gap.
Local-only, added 2026-11-13 (23:5xZ) (**S8/S7 GUI handoff written; no GitHub issue state changed**):
- Open: the four S8/S7 tools have no GUI panels. They are absent from `ANALYSIS_TOOL_JSONS`
  (`gui/data.py:4044`) and `ANALYSIS_SECTION_TOOLS` (`app.js:2644`), so their JSON is never parsed
  and the page shows only `extra_tools` name pills ("no dedicated renderer"). Plan, contracts and
  implementation paths: `docs/HANDOFF_S8_S7_GUI_2026-11-13.md`. S10 row in
  `docs/research/COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md:235`.
- Open (decision): `surrogate_validation` writes keyed `surrogate_validation-<hash>.json` files with
  no `.md`, so the exact-name analysis lookup never finds them. Options are a GUI glob of the newest
  complete file, a tool-side stable alias (needs owner approval and a tool test), or deferral.
- Open (decision): the S8/S7 tools refuse `--out` under `runs/`, while the GUI default analysis root
  is `runs/analysis/`; today the supported path is `--analysis-dir <scratch set>`. Keep that workflow
  or add a narrow tested exception.

Local-only, added 2026-11-13 (23:3xZ) (**senior implementation plan for review; six verification corrections; no GitHub issue state changed**):
- Ready for review (not executed): `docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md` - C1-C6 inventory, I1-I8
  invariants, E0-E9 gated sequence, H1-H4 test design with statistics, R1-R10 risks, rollback, 12 open questions.
  C2 is now DONE at fork **`38e5b1f`** (pushed to `ourfork`); the installed-SHA target for the trial is `38e5b1f`.
- Fixed (test design): the Round A/B arms shared a cache, so the second arm on the same seed would have been a cache
  hit and faked the speedup. Per-arm `cache_dir`/`dataset_dir` under `scratch/` now; both night files re-dry-run clean.
- Corrected: resume `--budget` counts new evals (45, not 200); the interrupted run is not strict, so the library-SHA
  resume guard is inert; night files must be copied to `runs/nights/`; `kind: search` needs `config:` even on resume;
  `selftest --analytic` is not fused-path parity.
- Running: resume job live (159/200); part-two fork edit under CPU test; pin unchanged; no other GPU work.
- Open (owner/reviewer): answer the 12 questions in the plan, in particular the repeat policy (one rep vs two), the
  `--budget 1` probe shape, and whether a bitwise fused-response comparison should replace the 0.039 dB bar.

Local-only, added 2026-11-13 (23:3xZ) (**Oracle-reviewed speed program replaces the campaign design; no GitHub issue state changed**):
- Ready (not launched): `docs/queue/SPEED_PROGRAM_2026-11-13.md`; `speed_round_a` (2 arms) and `speed_round_b`
  (4 arms), both `--dry-run` exit 0. Old campaign doc superseded, its night files deleted.
- **Ordering is binding:** finish the interrupted night (`--resume runs/20261113T193536Z-screen-81c964 --budget 200`)
  **before** the solver swap - `search/cma.py:702` refuses a strict resume after a library-SHA change.
- Open (next, no GPU): write solver upgrade part two (host-side identity guard) on top of the existing fork commit,
  one new SHA; Julia CPU testset green.
- Open: batching must become `solve.freq_batch_size` (config key) if adopted, so it appears in `config_sha`; the env
  var is the trial mechanism only.
- Open: shared (WDDM) spill is still unmeasured by the night runner; the <512 MiB bar needs the `_bench_common`
  counter on the batch-12 arms.
- Open: mesher ancestry check - `merge-base --is-ancestor d740c28 55da4f46` after fetching from `jamescollinharky`
  (the local checkout's `origin` is upstream `m3gnus`, the pin is on the fork).

Local-only, added 2026-11-13 (23:3xZ) (**combined speed campaign designed; no GitHub issue state changed**):
- Ready (not launched): `docs/queue/speed_combo_2026-11-14_{oldpin,newpin}.yaml`, a pin x batch factorial on two print
  cells, `--dry-run` exit 0. Design + pre-declared rules: `docs/queue/SPEED_COMBINED_2026-11-13.md`. ~45-55 GPU-min.
- Open: the pin swap between blocks is an operator step, not a night job (`pip install` + `provision --backend cpu`).
- Open: shared (WDDM) memory is still not recorded by the night runner, so the zero-spill gate needs one arm through
  `tools/bench/_bench_common.GpuMemPeak`.
- Open: `HORNLAB_FREQ_BATCH_SIZE` is an env var, not a config key, so an adopted batching value would not appear in
  `config_sha`; add `solve.freq_batch_size` if adopted.
- Open (candidate B, Lane C): the fused route builds two dense host N x N identity matrices per request that it never
  reads (`BeatEngineDriver.jl:1534-1535`); a second A3-shaped fork patch, ~0.5 GB host RAM + O(N^2) host assembly per
  request at 8k DOF. Not implemented.
- Open: the mesher fork checkout is stale (branch `hornlab-search/base` @ `b922e80`; the pinned `55da4f4` object is
  absent locally), so any fork-state conclusion from it is unreliable until a fetch.

Local-only, added 2026-11-13 ~23:5xZ (**PR #55 reconciled with main; worktrees consolidated; no GitHub issue state changed**):
- Resolved: main went green (`46a28ec` fixture adaptation, `dc64fd7` S8 contracts + S7 hardening) and the PR merged
  `origin/main` (`a717650`) as `4d6f4da`, taking main's `surrogate_validation.py` + tests. S7's v4
  `--advisory-stored-j` mode is main's answer; this branch's S7 draft is gone. S8 closed.
- Verified: compileall exit 0; 151 passed (durable launch, B8 e2e, seed_pack, lane_parity, S7, S8 trio), 116
  passed for the b8/study/gui/builder/native-gate neighbours, analysis-tool suite green.
- Resolved (housekeeping): worktrees 28 -> 3 (main, `hf-wt/pr55`, `oc-wt/gui-int`); 25 clean+merged worktrees
  removed with every branch ref kept. Safety: `backup/main-pre-reconcile`, `backup/pr55-pre-reconcile` tags and a
  verified all-refs bundle; 4 local-only branches pushed to origin.
- Open: merge PR #55 on GitHub, then remove `hf-wt/pr55` / delete `pr55-local`.
- Open: `feat/gui-integration` (`oc-wt/gui-int`, now on origin) needs a deliberate merge-or-retire decision.
- Not weakened: no gate, tolerance or test was changed to force green.

Local-only, added 2026-11-13 ~25Z (**PR #55 merged up to main, verified offline; no GitHub issue state changed**):
- Resolved: `main` (`9019cbd`) merged into the PR; only doc conflicts (`CONTINUITY`, `ISSUES`), both sides kept.
- Verified: compileall exit 0; 72 new tests passed; 62 neighbouring b8/study/gui-study tests passed; INDEX
  dedupe confirmed against main by link-target set (one intended pre-archive row dropped).
- Decided (S7 v4): main's `--advisory-stored-j` mode is the v4 path (canonical `score_spec` + label evidence);
  see the ~23:5xZ block. No constant was widened.
- Open: S8 discovery/QD-Pareto tooling not started.
- Open: full offline suite not re-run in this environment.

Local-only, added 2026-11-13 ~24Z (**bo-study B4/B5/B8; no GitHub issue state changed**):
- Resolved: launch idempotency is durable across GUI restarts (`launches` table, migration 2).
- Resolved: B8 offline end-to-end through CLI and HTTP.
- Resolved: S7 surrogate validation tool, S5 config round-trip + local search hints, lane_parity pooled mode.
- Open: S8 discovery/QD-Pareto analysis tooling not started.
- Decided (S7 v4): main's `--advisory-stored-j` mode is the v4 path; see the ~23:5xZ block.

Local-only, added 2026-11-13 (23:1xZ) (**G2 independently reviewed; evidence corrected; no GitHub issue state changed**):
- Open (owner): G2 verdict is adopt-with-conditions. Adopt = pin `9ec86b0` + `pyproject.toml`/`TOOLCHAIN.md` +
  A5 recalibration; rollback = old SHA. The pin is unchanged until the owner decides.
- Open (must do before the bump is final): fused-path output parity A/B (`docs/FORKS.md` 6.3) - the analytic selftest
  does not exercise the fused route; ceiling re-measurement on pin B at ~15.9k/20.2k/24k with dedicated **and shared**
  memory; one production-shape screen solve per pin.
- Corrected: the G2 evidence doc's mechanism section (skipped payload is `8(NÂ²+NÂ·E)`, not `8NÂ²` plus pool rounding) and
  its parity claim (non-fused only). Both were fixed in `docs/evidence/G2_FORK_AB_2026-11-13.md`.
- Open: `docs/evidence/FUSED_CUDA_2026-10-24.md`'s 12,000 caps and the 20,237-DOF refusal predicate are pin-A
  arithmetic and are plausibly stale by 1.5-2x under pin B; do not raise them before the ceiling re-measurement.
- Not a real item: `julia/coupled_solver.jl:909-910` builds the same identity cache but is unreachable from the worker
  (`solver.jl` includes only `BeatEngineCore.jl`/`BeatEngineDriver.jl`); dormant duplicate.

Local-only, added 2026-11-13 (23:0xZ) (**G2 measured and passed; GPU night paused; no GitHub issue state changed**):
- Resolved: G2 measured - 18 solves, 3 quarter-DOF points x 3 fresh-process reps x 2 commits. A3 `9ec86b0` saves
  55 / 66 / 70 % fused peak VRAM and 20-30 % per-frequency wall with an identical analytic self-test. Evidence
  `docs/evidence/G2_FORK_AB_2026-11-13.md`.
- Open (owner): adopt = bump the pin to `9ec86b0` in `pyproject.toml` + the `TOOLCHAIN.md` pin table, and
  recalibrate A5's 4.0x fused factor (~1.2x from the measured 1,343 MiB at 12k). Rollback = the old SHA.
- Open: GPU night `home80x60_day_2026-11-13` paused at job 2 153/200 (`20261113T193536Z-screen-81c964`); job 3 never
  ran; the GPU rerun night is on disk but NOT queued. Resume: `search --resume runs/20261113T193536Z-screen-81c964
  --budget 200`, then job 3 as its own job.
- Note: `pip install --force-reinstall` of hornlab-beat-bem drops the per-backend CPU readiness marker - run
  `python -m hornlab_beat_bem.provision --backend cpu` after any pin swap (the GPU runtime is unaffected).

Local-only, added 2026-11-13 23:0xZ (**S8 discovery contracts + S7 advisory validation finished;
no GitHub issue state changed**):
- Resolved: `geometry_descriptors.py`, `hypothesis_cards.py`, `qd_compare.py` and
  `surrogate_validation.py` ship with tests on `main`; 308 analysis tests pass (exit 0) and the
  S8-scope broad run is 329 passed (exit 0). Docs `research/S8_DISCOVERY_RESOLUTION_2026-11-13.md`
  and `tools/analysis/schema.md` now name the admitted families (`ICW`, `OSSE`, `R-OSSE`,
  `FREEFORM`) and the MEH/`mid_ports`/CAD/GRID refusals.
- Open (by design): `qd_compare` equal budgets are integer attempt-equivalent evaluations, so any
  speed or efficiency claim still needs a separate wall-time ledger; the tool reports no timing result.
- Open (by design): `surrogate_validation --advisory-stored-j` validates supplied stored v4 label
  evidence only. It cannot reconstruct raw arrays, and production metric-surrogate capability for v4
  remains absent (`surrogate/capability.py` untouched).
- Open (by design): PCA and k-means descriptors are navigation views; their neighbourhoods are not
  acoustic similarity or causal evidence.
- Open (unchanged): MEH stays paused, and no offline S8 artifact establishes acoustic improvement or
  optimizer superiority.

Local-only, added 2026-11-13 22:4xZ (**bo-study-v1.1 local pass: strict native gate, GUI QA fixes,
S11 rebuild, home/S5 readiness; no GitHub issue state changed**):
- Open: replay metric regeneration drift in `hornlab_search/objective/replay.py` â€” a brief target that
  differs **only** in `driver_exit_radius_mm` regenerates `di`/`dislope`/`distd` and moves stored J
  1.813 to 4.187 (row 57/387) and frozen row 37/356 from 2.969 to 5.338. Evidence
  `docs/evidence/bo_study_2026-11-12/m2/gate/target_probe.json`, finding `m2/GATE.md` section 6.
  The R0 changed-target variant is suspect until `objective/replay.py` is reviewed.
- Open: `tools/analysis/seed_pack.py::_hex40` rejects the real 12-hex design hash (30,723/30,723
  catalog rows), so both S5 seed packs are empty. The cloud PR owns the parser; regenerate the packs
  after it merges. Evidence `docs/evidence/bo_study_2026-11-12/s5/STATUS.md`.
- Open: GUI study panels emit no actions, so every phase renders "No action available" (S10
  headless QA; screenshots under `docs/evidence/bo_study_2026-11-12/s10/`). Bounded previews,
  recorded decisions and the Execute package fallback are fixed; the upstream action payload is not.
- Open: `propose` needs BoTorch (isolated `bayes-venv`) and `hornlab_mesher` (project venv) in one
  interpreter; no single sanctioned venv has both, so a live fit + revalidation cannot run here.
- Open: the M2 gate verdict is `insufficient_evidence`: the frozen native cohort is one connected
  experiment group (197 rows), not the five independent groups that group-held-out validation
  requires. `m2/GATE.md`; no pooling or invented groups.
- Open (home task): 217 catalog-ok rows >= n_min 16, but zero replayable score rows â€” the offline
  scan is ATH-target-only, replay dispatches v1-4 only (home is objective v7), and all 217 rows are
  missing `impedance_matrix` while loading weight is 1.0. `home/READINESS.md`.
- Fixed in this pass: `bo.data.build_native_training_set` now enforces the strict
  version/ripple/policy gate and applies the `morph_exponent` no-op only when the key exists (the
  six-knob home task uses the identity projection); GUI study panels get bounded previews, recorded
  decisions and the Execute package fallback; `studies.js` no longer renders `#/run/undefined`
  links. Tests: `test_bo_native_policy_gate.py` (9), `test_gui_studies_qa_fixes.py` (5). Also
  updated the two stale A1 failure-marker assertions (`test_design_generated.py`,
  `test_mesh_build_grid.py`) to read the physics-namespaced solve cache, and gave the
  `test_study_builders.py` tiny fixture the strict policy fields; both were red on the full suite
  before the update and pass after.

Local-only, added 2026-11-13 (22:3xZ) (**backlog committed and pushed; no GitHub issue state changed**):
- Resolved: the bo/gui/analysis backlog is on `main` and pushed (`5f15275`, 73 files; `a4dccef` surrogate
  refinements). 63 + 21 tests green; compileall clean. C1's configs + audit doc also land on `main`.
- Open: `tools/analysis/geometry_descriptors.py` and `tests/test_tools_analysis_surrogate_validation.py` were
  being written live at commit time and remain uncommitted for their author.
- Open (housekeeping): `solver-speed-orch2` is content-redundant on `main` except for its C1 CONTINUITY/ISSUES
  write-up; leave it for review or delete after merging that text.

Local-only, added 2026-11-13 (22:2xZ) (**CPU jobs re-queued on the GPU lane, fused CUDA; no GitHub issue state changed**):
- Queued: `home80x60_gpu_rerun_2026-11-13` - 2 fused-CUDA command jobs (osse_ext_throat seed 9012 budget 120;
  ath_core_14in seed 5678 budget 80) behind `home80x60_day_2026-11-13`; starts when that runner exits, cutoff 23:59.
  Queue pid 39096, log `runs/nights/queue_gpu_rerun_2026-11-13.log`; `--dry-run` exit 0.
- Open: if the running GPU night overruns 23:59 the cutoff skips the queued night and it must be re-queued.
- Open: the CPU-lane eval-rate baseline for the 80x60 extended-throat config is still missing; the queued jobs are
  the GPU path, not a CPU measurement.
- Not affected: the running GPU night continues; its measured rate (~100 evals / 81 min) sizes the queued timeouts
  at 3 h and 2 h.

Local-only, added 2026-11-13 (22:1xZ) (**CPU lane night stopped by owner; no GitHub issue state changed**):
- Open: `home80x60_cpu_2026-11-13` job 1 was stopped at 5/120 evals (~9.4 min/eval measured, vs the ~103 s/eval
  the night file budgeted); job 2 never started. Partial run `runs/20261113T212428Z-screen-2c4d56`, resumable
  (`search --resume`, or `resume: <dir>` in a night job).
- Open (owner decision): run the two CPU jobs on the GPU lane after 23:30 (`--backend cuda`, fresh run), or
  resume on CPU with a timeout sized from the measured rate. No CPU-lane eval-rate baseline exists for the
  80x60 extended-throat config; measure it before scheduling CPU nights on it.
- Not affected: GPU night `home80x60_day_2026-11-13` continued untouched (verified before and after the kill).

Local-only, added 2026-11-13 (22:05Z) (**CPU lane GUI progress parity; no GitHub issue state changed**):
- Resolved: CPU lane runs/solves now show status, progress bar, session %, rate/h, ETA, best/start
  score and failures on Home and Status, matching the GPU running card; `/api/lanes` rows carry
  rate/ETA/session/budget and resolve fresh `--config` jobs for both lanes.
- Open (pre-existing, not introduced here): the lanes table matches queue logs by filename
  (`queue_*gpu*`), so a GPU night named without `gpu` (e.g. `queue_home80x60_day_...`) shows idle
  there while its full-width card is correct. A browser visual pass of the new cards is still
  pending after a server restart.

Local-only, added 2026-11-13 ~21Z (**solver speed plan; no GitHub issue state changed**):
- Resolved: A1 namespaced caches landed. (was: solve/mesh cache does not check solver/mesher SHA (blocker before any fork pin bump). Plan: SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13 A1.
- Resolved: A2 seam probe fixed.
- Open: fused CUDA allocates unused GPU identity cache (A3 fork patch, G2 validation).
- Resolved: A4 mesh fidelity tool landed; dense-memory preflight module landed, wiring pending (A5.4); beat_metal unmapped.
- Closed (rev 2 review): replay v5-v7 already refuses explicitly (`R_REPLAY_VERSION_UNSUPPORTED`); former A6 dropped.
- Open: A1b `compare/` and `tools/m3_measurement_pack.py` build their own cache roots; route through `solve.cache.namespace()`; only real caller is `tools/m3_measurement_pack.py:340` (compare/ only uses explicit paths).

Local-only, added 2026-11-13 ~21:2xZ (**final 2026-11-12 night report; no GitHub issue state changed**):
- Resolved: `docs/evidence/NIGHT_2026-11-12.md` (final, all six night files + section-6 orchestrator
  analysis) supersedes `NIGHT_2026-11-12_PARTIAL.md`; the 2026-11-12 GPU staged-vs-joint A/B verdict
  (joint wins, J 2.4389 vs 2.6290) is appended to `STAGED_SEARCH_AB_2026-10-31.md` and indexed.
- Resolved (correction, ~22:0xZ): the earlier claim that the CPU lane slowed GPU evals/h (~-14%) is retracted; timeline audit shows ~10 min real GPU/CPU overlap, CPU lane filled GPU-down time after the 17:41Z restart (see NIGHT_2026-11-12.md correction section). Whether sustained two-lane fresh-search concurrency costs GPU rate remains unmeasured.
- Open (owner/operator): L5.7 dataset re-pack + HF upload (`tools\hf_sync.py pack --groups
  text, dataset`, then `upload`) must run at the next GPU job boundary - the print-day p80x60
  searches write the dataset continuously until the 23:30 cut-off. Keep `HF_HUB_DISABLE_XET=1`.

Local-only, added 2026-11-13 (**local-work audit; no GitHub issue state changed**):
- Resolved: the canonical checkout is fully committed and pushed (`main == origin/main == adc1e15`):
  `8f5ae9e` home 80x60/700 brief + cells and S5 seed packs; `adc1e15` Elites thumbnails as frozen
  shaded 3D renders. Audit verification: `node --check app.js` exit 0; 49 tests passed
  (`tests/test_gui_elites_ui.py`, `tests/test_tools_analysis_seed_pack.py`).
- Open (SENIOR DECISION): 57 local-only branch refs; only 4 commits are on no remote (`bf7f003`
  backup/consolidation/T - superseded; `aa9011c` backup/consolidation/L1 - commit-msg scratch only;
  `1078cd2` feat/gui-integration - merge whose parents are already in main; `65c03de`
  dev/fused-cuda-pin - `file://` fork pin, dev-only). Push-as-archive, leave, or prune?
- Open (SENIOR DECISION): four orphaned stash-like commits are the only copy of their states and are
  GC-eligible (`f4bddb6` old Elites app.js/css, `3bdb50e` bo_sensitivity, `1f6750d` swarm-H rescue,
  `0d3c8c1` profiles). Rescue into one archive ref, or let GC take them?
- Open (SENIOR DECISION): `C:\Users\hunte\Hrns` is a 0-commit home-level repo (remote
  `llevaachingada/Hrns`, empty) with 30,123 untracked paths, 30,066 of them under `oc-wt/` because
  worktree `.git` files make git recurse into 28 full checkouts. Owner chose "leave alone, log only".
  Needs a `.gitignore` or removal before any tooling runs `git add -A` there.
- Open (SENIOR DECISION): BO/studies code is already public on `origin/main` although an earlier
  CONTINUITY entry said it would live on a local `bo-study` branch (which does not exist). Accept, or
  route future BO work to a local branch (no history rewrite)?
- Open: `adc1e15` did not update this file (push rule asks for CONTINUITY + ISSUES together).
  `oc-wt/bo-study/CONTINUATION_SLICE_MAP_2026-11-13.md` is not mirrored under
  `docs/research/bo_study/`; commit it (BO-local or docs) or leave it as a local handoff.

Local-only, added 2026-11-13 ~20Z (**no GitHub issue state changed**):
- Resolved: CP-7b GPU/CPU lane parity, closed in aggregate (4 pairs, max 0.079 dB).
- Open: StudyRunBridge launch idempotency is in-memory; make it durable before any real launcher is wired.
- Open (owner): BO/studies code is on main, though the owner preferred a local fork; reverting it would be a separate decision.
- Open: lane_parity.py should pool pairs, so the per-pair FAIL label stops being misleading.

Local-only, added 2026-11-13 (**S5 seed packs + home task registry; no GitHub issue state changed**):
- Resolved: `tools/analysis/seed_pack.py` (S5) created with 47 fake-fixture tests; greedy max-min
  diversity selection, full provenance, no fabricated warm starts, hash-identity round-trip.
- Resolved: home target task `p80x60__osse_ext_throat_home700_v7` (objective v7, 80x60/700) added to
  `studies/builders.py` task registry. Home task returns Unavailable (insufficient data) until an
  explicit evidence source is provided; M0 freeze contract unchanged.
- Open (unchanged): production launcher/factory not wired (503); no combined BoTorch+mesher venv; home
  task evidence root does not exist until first cohort; S5 full geometric round-trip requires config loading.

Local-only, added 2026-11-13 (**bo-study-v1.1 offline completion: F0/F1/S1/S2 + B7 + M3 builders/API/GUI; no GitHub issue state changed**):
- Resolved: F0 typed outcomes/strict plain-CMA policy (`resample_strict`, same-candidate retry,
  bounded draws, `cma/strict_state.json`), S1 CMA-ME seed identity, F1 QD failure exclusion in both
  archives + pending/cumulative resume, B7 Pareto/constraint/cost/trust-region exports + unified
  `bo/policy.py`, M3 study builders/evaluator/API endpoints/package policy gate, GUI policy selector
  + package/launch/cancel/artifact lifecycle, S2 read-only cache-producer audit, and the explicit
  surrogate v1-only capability refusal. M0 freeze signed with the ATH eligibility statement;
  `pyproject.toml` `bayes` extra registered.
- Fixed during the pass: strict cache hits no longer consume new/valid/attempt budget; failed seeds
  are never `best`; unmeasured-gate penalties are not tell-eligible; QD transient stops are
  resumable from durable rows; QD cumulative caps persist/refuse shrink/extensions; strict stop
  reasons name the cap that fired; a capability/model/pool-refusal proposal cannot be packaged.
- Open (by design, not implementation gaps): no production `pipeline_factory`/launcher is wired, so
  GUI/API launch returns 503 until an integrator injects the real lane/journal adapter; real BEM
  execution, acoustic validation, and pilots remain owner-scheduled. No single sanctioned venv has
  both BoTorch and `hornlab_mesher`, so a live study proposal fit+revalidation is not executable
  here; the M2 proposal is the real precomputed evidence. GUI lifecycle is a DOM-stub test (no
  jsdom/Playwright), not a full browser render. S2 is audit-only; no producer enforcement.
- Verification: project venv 3577 passed / 18 skipped / 21 deselected, exit 0; isolated bayes venv
  131 passed / 4 skipped, exit 0; compileall and node checks clean.

Local-only, added 2026-11-13 (**bo-study-v1.1 final integration; offline; no GitHub issue state changed**):
- Fixed: `parameter_study` artifact predated the independent-evidence gate (claimed recommendation
  allowed); regenerated suppressed with parity 197/200 max|dJ| 0. `source_fidelity` now joins the
  authoritative 200-row scores artifact (197/197 cards, was 50). Both under
  `docs/evidence/bo_study_2026-11-12/{s4,s6}/`.
- Fixed: explicit study cancellation was reported `stale`; `studies/runner.py` checks
  `journal.cancelled()` before `is_current()` (regression pinned in `tests/test_b8_regressions.py`).
- Fixed: 6 engine-only bo tests now carry `requires_botorch`; the project venv skips them honestly
  while the isolated bayes venv runs them. Stale rev2 GUI K-law pin aligned to the shipped wording.
- S11 complete: both pilot manifests validate through the live CLI (`errors=0 warnings=0`), with
  committed validation records; the superseded prototype test was removed.
- Resolved in the newer F0/F1/M3 entry: `PipelineStudyEvaluator` + `build_production_wiring` provide
  the production-shaped evaluator contract and are offline-tested with injected fakes; the real
  BEM pipeline/lane launcher still requires an integrator injection, so launch is an explicit 503
  and the S9 A/B matrix/pilots remain owner-scheduled.
- Resolved: `studies/cli.py` `snapshot`/`analyze`/`propose` now build and attach snapshot/training/
  analysis/model/pool/proposal artifacts; a proposal that is a capability/model/pool refusal is
  reported as such and cannot be packaged.
- Resolved: `pyproject.toml` now registers the optional `bayes` extra (`botorch==0.18.1`,
  `gpytorch==1.15.2`, `linear_operator==0.6.1`, `torch>=2.2`); the sanctioned engine is still the
  isolated `C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv`, and the live venv is unchanged.
- Open: 3 native rows (shard 57, rows 276-278) were uncatalogued at snapshot time; a later catalog
  regeneration picks them up. The S4 artifact records its own snapshot counts/timestamp.
- Note: untracked `cache_probe/` and `dataset_probe/` probe artifacts were produced by the parallel
  rev2 CPU-parity session (real CPU solves, `beat_cpu`); this session left them untouched.

Local-only, added 2026-11-13 (**next-queue handoff + HF dataset upload COMPLETE; no GitHub issue state changed**):
- `docs/research/NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md`: verified night-queue status, decision
  lineage (compute-allocation study -> ATH 50x50 first task -> hardening/bo-study-v1.1), data
  inventory, K-law/8 GB retarget limits, constraints, adversarial verdict and three alternatives.
- **TO-DO (next round, owner-gated):** plan the next queue around the owner's 60-80 deg / ~700 Hz
  goal. Recommended order: (1) freeze a new brief (prefer 80x80 @ f0 700, band 300-5500 for screen
  solvability, or the owner's chosen pair) as a new score identity; (2) zero-solve rescore of existing
  raw responses under it (R0/`offline_scores`), asserting zero backend calls; (3) one or two CMA
  seeds, 300-400 evals each, plus verify 4-6; (4) keep 50x50 and v7 ext-throat as benchmark data
  only; (5) re-check the M0 freeze (origin still DRAFT) and CPU/GPU parity before trusting the day
  report. Owner must confirm coverage pair, driver (2-inch vs 1.4-inch), band top, envelope and
  build-vs-study.
- **HF upload COMPLETED 2026-11-13 21:37Z:** stage `C:\Users\hunte\Hrns\.hf_stage_hunter`
  (8 tars, 12.82 GB, SHA-256 verified) uploaded to the root of
  `chingadalleva/hornlab-search-data`; repo `last_modified 2026-11-13 21:36:46Z`; sizes and LFS
  SHA-256 match `stage_hashes.json` (`ALL_MATCH=True`). Scheduled bulk task failed (non-interactive
  session); succeeded via `ops/hf_upload_retry.ps1` per-file retry (commits `f0a403a`, `a3c7e01`,
  `3babbe7`, `0e7d367`, `4cb907a`, `a1d4bee`, `f529366`, `ef36d14`); task unregistered. Stage cutoff
  ~04:51-04:56Z (1,501/1,726 g9 rows). **L5.7 remains open for the final re-pack after the print-day
  23:30 cut-off** (the `p80x60` searches keep writing). Record: `docs/evidence/HF_UPLOAD_2026-11-13.md`.

Local-only, added 2026-11-13 (**Rev2 implementation pass, additive; no GitHub issue state changed**):
- Open from Rev2: GUI balloon range selector, frequency-grid fidelity factor, J1/L1 generators, archive-wide manifest sweep. See QUEUE_PLAN_REV2 status table.

Local-only, added 2026-11-13 (**Rev2 queue prepared, not launched; no GitHub issue state changed**):
- `docs/research/QUEUE_PLAN_REV2_2026-11-13.md`, configs `examples/typologies/ablation_2026-11-13/`, night files `docs/queue/`. Open: mesh-check on owner machine; E8 parity pending these runs.

Local-only, added 2026-11-12 (**GUI finishing pass; no GitHub issue state changed**):
- WP9+WP10 merged into `feat/gui-integration`; merge regression fixed (app.js used `logTicks` without importing it â€” run detail threw `logTicks is not defined`).
- `data_verify.py` root-cause fix: `config.yaml` was read via `_read_json` (YAML â‰  JSON), nulling the verify report's name/band; `brief` added to the payload. `verify.js` header/chips/30Â°-ticks fixes; verify-mode run pages hide search-history panels (WP4 item 5).
- WP7: `gui/jobs.py` verify job accepts `designs`/`designs_file` CLI-mirrored (+24 tests); verify view "Verify selected" posts them, disabled while the GPU lock is alive (verified live).
- Owner decision (2026-11-12): Home "Best horn per brief" window 14 â†’ 31 days.
- Live acceptance `docs/GUI_VERIFY_ACCEPTANCE_2026-11-12.md`: Appendix B 1â€“16 pass; screenshots `docs/images/gui-acceptance-2026-11-12/`.
- Known cosmetic (NOT a GitHub issue): browser-default `/favicon.ico` 404 â€” one console error per session; index.html declares no favicon.
- Known cosmetic (NOT a GitHub issue, visual audit 2026-11-12): light theme â€” 3D-balloon annotations/wireframe and the circular-polar outer grid are faint grey-on-white (candidates for `docs/GUI_CONTRAST_PLAN.md`); verify scatter labels crowd when several designs share a J value (cluster on ed1da9); DI and On-axis render one card each with H+V series (Beamwidth has separate H/V cards â€” C6 small multiples cover BW only). Run-detail per-parameter Ïƒ, circular polar overflow, verify/gate-audit table clipping, and the dishonest "0 failed" convergence footer were all fixed before this push (see `docs/GUI_VERIFY_ACCEPTANCE_2026-11-12.md`).

Local-only, added 2026-11-12 (**GUI verify view front end WP3+WP6 implemented; no GitHub issue state changed**):
- `verify.js` WP3+WP6 front end: pure-helper exports for the verify table, KPI strip, polar plot,
  per-design panel, compare-two, checklist. `balloon.js` tier param added. CSS block appended.
  37 new tests green; full -k gui suite 362/0.

Local-only, added 2026-11-12 (**refusals / CMA trajectory handoff, PR #49; no GitHub issue state changed**):
- `docs/research/REFUSALS_AND_OPTIMIZER_HANDOFF_2026-11-12.md`: plain-CMA resample vs CMA-ME/
  CMA-MAE, exact code/tests, measured refusal counts, dataset failure metadata (4,634/28,573 main;
  16/237 dataset_cpu; D.3 no ok filter), over-constraint guardrails. No code/queue/default changes.

Local-only, added 2026-11-12 (**partial day evidence committed, PR #48; no GitHub issue state changed**):
- `docs/evidence/DAY_2026-11-12_ANALYSIS_PARTIAL.md` (A.8 partial + 10 charts; A.7 PASS, 24-run
  fidelity census, 25-seed variance, D.3 dry-run) and `docs/evidence/NIGHT_2026-11-12_PARTIAL.md`
  saved while the GPU queue runs. No code/queue/default changes; final report supersedes after
  g2-g9.

Local-only, added 2026-11-12 (**research plan + external review handoff saved, PR #46; no GitHub issue state changed**):
- `docs/research/DATA_GA_RESEARCH_PLAN_2026-11-12.md` and
  `docs/research/COUNCIL_REVIEW_HANDOFF_2026-11-12.md` saved (raw/pending external review). No code,
  queue, or default changes. The handoff records the verified state and the freeform_sculpt census
  correction (25 equal-budget seeds, spread 4.780; 26th is a 777-row seed-1234 base).

Local-only, added 2026-11-12 (**G follow-up: measured v8 tolerances + full re-score, PR #47; no GitHub issue state changed**):
- `scalar_v8.py` now ships the full-dataset per-class tolerances (23,833 rows scored) instead of
  the 1.0 placeholders; brief Â§4 has the counters/tolerance/tau tables and the class-B 87%
  hard-refusal caveat; a regression test pins the measured values. v8 remains unregistered and no
  defaults changed. Targeted 40/0/0/0; CI.

Local-only, added 2026-11-12 (**fix: verify outputs per backend, PR #44; no GitHub issue state changed**):
- `verify --backend X` wrote every backend into `<run>/verify/`, overwriting the other lane's
  `response.npz`/`metrics.json` and mixing the rows. New `--verify-dir PATH`; a `--backend` mismatch now
  gets its own run dir with `verify_of.backend`; an explicit dir refuses mixed-backend rows. Defaults
  unchanged. Tonight's c2b/g1c responses recovered from the per-lane caches for A.7 (PASS, 5/5 within
  0.2 dB); no re-solve. Queue-branch GUI `_cpu_activity` must learn the new dirs when it merges.

Local-only, added 2026-11-12 (**GUI verify/high-res view plan; plan only, no GitHub issue state changed**):
- `docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md`: verify sub-view inside run detail (`#/run/<id>/verify` + Verification
  card), verify runs as fidelity-badged rows linked to their parent, per-design high-res panel (Hz scrubber ->
  balloon isobars + H/V cuts with screen ghost + curves + isobars map), compare-two-verified. Grounded in the
  actual GUI code; Boundary Lab v0.5.0 borrowings folded in. Slices 1-6 + risks; not implemented.

Local-only, added 2026-11-12 (**day plan group G: objective v8 PROPOSAL; no GitHub issue state changed**):
- `hornlab_search/objective/scalar_v8.py` + `tools/analysis/v8_rescore.py` + owner brief landed as an
  OFFLINE PROPOSAL (not registered; no brief uses v8; no default changed). Re-score: tau v8 vs
  v4/v6/v7 = 0.683/0.792/0.668, top-20 overlap 13/11/12 of 20 on 400 stored rows. Owner sign-off
  required; an A/B night (>=5 seeds per class) must precede any brief switch. 39 targeted tests green.

Local-only, added 2026-11-12 (**test-suite efficiency review; proposal only, no GitHub issue state changed**):
- `docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md`: measured suite/churn (2706 tests/588 s local;
  122 CI runs + 824 run-minutes today; 24 tests = 51% of suite time) and proposals R1-R8 (single CI
  trigger + main, pip cache, docs-only fast lane, `slow`-marking heavy integration tests, CI-as-gate,
  required checks, optional xdist, GPU smoke-vs-full ladder). Owner decides; nothing applied.

Local-only, added 2026-11-12 (**day plan group E merge, PR #36; no GitHub issue state changed**):
- E.1 `#/analysis` page + `/api/analysis` routes (renders Group A outputs read-only; new
  `gui --analysis-dir` flag); E.2 home lanes panel via `GET /api/lanes` (local duplicate of D.1,
  never imports tools/); E.3 `#/elites` gate-audit catalog (J vN, gate chips, coverage cell, run link).
  Targeted + full offline suite green on the branch.

Local-only, added 2026-11-12 (**day plan group B merge, PR #40; no GitHub issue state changed**):
- B.1-B.9 landed opt-in (warm start, links, narrow/widen subcommand, valid-only budget, round-throat
  gate flag, infeasible resample, lq surrogate, CMA-MAE option, PARAMETERS.md sections). Defaults
  unchanged (78ed1f4 goldens green). 97 targeted tests green. `cma_me` + `resample` is a ConfigError
  (ribs 0.12 `Scheduler.tell` cannot drop refused solutions) â€” documented. Open follow-up:
  fold the hand-written search-key section into `tools/gen_param_catalog.py`.
  CI also required adding the new opt-in keys to `tests/test_config.py::OPTIONAL_FIELDS`
  (they are None by design when absent) and gating the three CMA-MAE runtime tests on `ribs`
  (optional dep absent in CI; same importorskip pattern as the CMA-ME suite) â€” no product code changed.

Local-only, added 2026-11-12 (**day plan group C merge, PR #37; no GitHub issue state changed**):
- C.1/C.2 calibration planner + verdicts landed; C.3 N1 throughput evidence + C.4 screen-fidelity
  proposal written (recommendations are proposals only; owner flips defaults after the calibration
  night). 13 targeted tests green.

Local-only, added 2026-11-12 (**fix: Group-A test CLI helper ran with a hard-coded interpreter path; no GitHub issue state changed**):
- PR #38 merged with CI red (repo does not enforce status checks): `run_cli` in
  `tests/test_tools_analysis_common.py` hardcoded the box's venv path; CI (Linux) failed ~25 tests with
  `FileNotFoundError`. Fixed with `sys.executable` in PR (this one); no product code touched.
- Second cause found by the fix PR's CI: three sensitivity tests asserted surrogate availability
  (sklearn optional by contract; absent on CI) â€” tests now assert the availability/degradation
  contract instead. No product code touched.

Local-only, added 2026-11-12 (**day plan group D merge, PR #35; no GitHub issue state changed**):
- D.1-D.4 landed: two-lane `night_status.py` (locks, running jobs, row ages, stale-lane ALERT), night-runner
  robustness (GPU-busy -> blocked + one retry, lane/backend/status/attempts rows, --dry-run argv path
  validation, explicit stale-lock takeover), parity-gated `tools/data/merge_lane_dataset.py` (dry-run default,
  provenance.lane=cpu, atomic + idempotent), per-lane `tools/night_report.py`. 66 targeted tests; full suite
  green on the branch. D.3 gate tolerance documented (top-level `pass`; fail closed on unrecognised).

Local-only, added 2026-11-12 (**day plan group F merge, PR #33; issue #13 state changed on GitHub**):
- **F.4 DONE:** GitHub issue #13 CLOSED by the orchestrator 2026-11-12 (comment cites fixes merged
  2026-10-22: FF to 6d1d5c7 = e0b9b61 + 11304f6 + 152a829; suite 533 PASS). Mirrored in the row below.
- P15 added to NEXT_DEV_PRIORITIES (day plan, PR #32); P14 lanes L1-L5 marked DONE (#29/#26/#27/#28; #25 open, merges last);
  owner decisions recorded (v6/v7 loading split per PR #27 tau evidence, round-throat default, sysmem, Collin HF write, printing).
- SENIOR_PLAN_2026-11-12.md gained a per-WP status column (done / in this plan / open).
- CONTINUITY reorder delivered as `docs/history/continuity_reorder_2026-11-12.patch` (apply LAST, after all today's merges).

Local-only, added 2026-11-12 (**lane L1 CPU second lane; no GitHub issue state changed**):
- **PR `lane/L1-cpu-lane` â†’ `main` (open draft):** CPU second solve lane wired end-to-end (L1.1-L1.6, L1.8);
  `solve.julia_threads`, lane-scoped host cleanup, `lane_env()`, two-lane night runner, `lane`+`backend` rows,
  `examples/profiles/`, AGENTS.md / CLAUDE.md "Two lanes" paragraph. L1.7 (GUI objective versions) is out of scope.
Local-only, added 2026-11-12 (**lane L5: data-interop; no GitHub issue state changed**):
- **WP-F / L5 DONE:** dataset MANIFEST.json, two-way HF labs sync, design mesher-config export, foreign ingestion
  (CP-7b parity gate), campaign tables grouped by objective_version+backend. Runbook updated. Owner actions: grant
  Collin HF write access; run L5.7 pack+upload between GPU jobs.

Local-only, added 2026-11-12 (**integration; GitHub: PRs #19, #22, #23 close as merged with the integration PR; #13 to close**):
- Objective numbering: 5 = MEH, 6 = loading_smooth (Collin), **7 = the hardened objective** (was "5" on
  `feat/hardened-plan-2026-10-29`; data relabelled, see CONTINUITY 2026-11-12). Plan: `docs/SENIOR_PLAN_2026-11-12.md`.
- Open: HF dataset re-pack after the relabel (WP-E4); GUI objective versions 4-7 (WP-D1); loading objectives
  reconciliation (WP-B1); two-way data interop with Collin (WP-F / handoff L5). `swarm/B` + `swarm/C` merged in #24.

Local-only, added 2026-11-12 (day queue): staged-search brief path fix; narrowed ath_core cell; two-lane day queue live.
Local-only, added 2026-11-12 (GUI diagnosis, read-only pass; owner chose "diagnose only" â€” no code changed; no GitHub issue state changed):

Local-only, added 2026-11-12: day hardening plan (groups A-F) in `docs/IMPLEMENTATION_PLAN_2026-11-12_DAY.md`; #25 held until queues end; #13 to close (plan F.4).

| ID | Title | Status | Owner | Plan ref |
|---|---|---|---|---|
| GUI-1 | Recent runs/queue progress not shown on Home/Status/Runs | CLOSED 2026-11-12 (all root causes fixed; see below) | owner-decided | gui/data.py, gui/static/app.js |
| GUI-2 | "J from different objective versions is not comparable" banner reads as an error | CLOSED 2026-11-12 (info note + version filter) | owner-decided | app.js guard helpers |

**GUI-1 root causes (all verified live, branch `day/2026-11-12-queue` HEAD d638231):**
1. `status()` picks `runs/overnight/queue_*.log` by LEXICOGRAPHIC name, not mtime (`data.py:1328-1333`): of 28 logs it selects `queue_v5_continue_2026-10-29.log`, so tonight's `gpu_day_2026-11-12_cont` / `cpu_day_2026-11-12_cont` steps never show. Fix: newest-by-mtime (+ per-lane list, additive).
2. CPU lane never "current": `status()` reads only the GPU lock (`data.py:1309-1313`); `runs/.cpu.lane.lock` (`gpulock.py:44,99,271`) is never read. Fix: add CPU lane lock/current row.
3. Verify outputs live in `<run>/verify/search.ndjson` (`cli.py:894-898`) which `list_runs`/`run_detail` never scan (`data.py:140,512`) â€” c1b/g1c-style jobs are structurally invisible (also hides `runs/elites_20261030_hypex`). Fix: additive `verify` block per run detail.
4. Runs/detail views fetch once, no refresh timer (`app.js:1308,2025`); only Status/pill/Launch poll. Fix: refresh button/timer.
5. Resumed runs: table sorted by original `started` (a resumed run sits ~26th of 425, "13d ago"); `current_run` scans only `[:30]` dirs (`data.py:1466-1470`); `run_progress` compares total rows to the SESSION budget (resumed run prints "892/117 (762%) over budget", `data.py:1452-1463`). Fixes: activity sort / drop slice / session-budget handling.

**Not the cause (checked):** no run-list cache or snapshot (`runs/.gui_cache` holds only evolution/umap artefacts keyed by `(size,mtime)`); no date/runcount/night filters; browser cache is `no-store`; live growth 885â†’892 observed across reads. Empty reboot leftover `runs/20261112T114355Z-screen-7ee43f` (n=0) lists with default v1.

**GUI-2:** informational guard banner (`J_VERSION_BANNER`, `app.js:1909-1933`, commit 0751895 2026-11-12 03:41) meeting a genuinely mixed corpus: v1Ã—228, v2Ã—7, v3Ã—54, v4Ã—100, v5Ã—7, v6Ã—2, v7Ã—27. Table IS correctly grouped per version and rows labelled `J vN`. Not errors: no mixed rows inside a run, no None versions (absent=v1 by contract), no best-across-runs mixing. If desired later: reword as `role="note"` with per-version counts (do NOT re-label old runs; `tests/test_gui_views_l2.py:199` pins the string â€” update with it).

**GUI-2 CLOSED 2026-11-12:** banner reworded to `role="note"` / `.alert.info` â€” "J is only comparable within one objective version â€” the table is grouped by version" with per-version count chips (`objectiveVersionCounts`, exported); NEW version dropdown filter on Runs (All versions / J vN with counts). `tests/test_gui_views_l2.py` node guard updated (new string + counts + `verifyBlockHtml` Î”J pin). Do NOT re-label old runs.

**GUI-1 FULLY CLOSED 2026-11-12 (second pass, owner-approved A+B+C):** on top of the partial fixes above â€” (i) Runs page: default sort **Recently active** (by `last`), `active` flag in `run_summary` (fresh on every call incl. cache hits), pulsing â— LIVE cell, resumed badge `sess N`, `has_verify` marker; (ii) Run detail: **Verify re-solves** block from `<run>/verify/search.ndjson` with Î”J=CPUâˆ’GPU pairing (verified live on 377bbe: |Î”J| â‰¤ 7e-05); (iii) Runs version filter; (iv) CPU-lane generality: night-queued CPU `search` jobs resolve their run dir from the job log's `output <dir>` line and get session/rate/ETA; `current_run` now skips runs whose last row is lane-tagged `cpu` (lane attribution can't be swallowed by a concurrent CPU run); (v) Watchdog pane removed (stale by ~3 weeks); (vi) queue tabs: the newest 5 queue logs are switchable on Status (selection persists across polls); (vii) `_run_summary` sessions on `run.json "resumes"`. Deferred remainder (gates display WP-D2, elites catalog D4, balloon W6, compose classes P8d, P9 sandbox, leaderboard latency, Kill-run typed-confirm â€” owner deferred): NOTES_FOR_SENIOR.md 2026-11-12 entry (updated at 14:05).

**Safety note while night queues run:** GUI restart is safe; app.js fixes need only a browser reload; data.py fixes need one GUI restart. Never use the GUI's `gpu-clean` / "Kill run" / stop-current during a live night â€” they `taskkill /T` the GPU-lock pid (jobs.py:399-449, server.py:185-194).

| ID | Title | Status | Owner | Plan ref |
|---|---|---|---|---|
| #13 | hardening-review: Stage A surrogate gate-integrity and real-data traps | **closed 2026-11-12** (fixes had MERGED to main 2026-10-22: FF to 6d1d5c7 carries e0b9b61 + 11304f6 + cloud reconciliation 152a829 verbatim; oracle pre-merge sign-off; full offline suite 533 PASS at the merged tree; closed per day-plan F.4) | phase-2 (cloud) | `docs/plan/11_PHASE2_SURROGATE.md` Â§4 |

Local-only, added 2026-11-03 (**CPU-vs-CUDA audit; no GitHub issue state changed**):
- **PR #19 (`meh/integration`, open):** its conclusion "CPU is the faster engine for the MEH" is withdrawn - the
  CUDA arm spilled into shared system memory (`docs/evidence/BENCH_AUDIT_2026-11-03.md`). Body/doc correction
  pending owner approval to edit the PR.
- **Pin `0850ef3`** (multi-channel fused CUDA): fork branch `hornlab-search/meh-fused-cuda` is pushed (verified 2026-11-12).
- **Owner:** set CUDA Sysmem Fallback Policy to Prefer No Sysmem Fallback for `julia.exe`.
Local-only, updated 2026-11-05 (**CI param-catalog fix on PR #22; no GitHub issue state changed**):
- Fixed `test_param_catalog` failures: `mid_ports` NATIVE_KNOBS, native-count/CAD-only gates, regenerated param catalog.

Local-only, updated 2026-11-05 (**objective v6 loading_smooth; no GitHub issue state changed**):
- **Landed:** `objective.version: 6` (`load_near`, `z_smooth`, `cov_pat`, `di_rise`) for Le ClÃ©ac'h / rollback; dossier + briefs + offline tests. Open: re-score full records that carry `z_throat` so load_near/z_smooth dominance can be confirmed; calibrate `di_slope_target` (seed slopes ~8 dB/dec vs default +5).

Local-only, updated 2026-11-03 (**PR to main; no GitHub issue state changed**):
- Opening PR `feat/solana-sawmod-wg-bench` â†’ `main` (Solana/SAWMOD, mid_ports, cloud tooling, UMAP evidence + GUI Design cloud).

Local-only, updated 2026-11-03 (**GUI design-cloud view; no GitHub issue state changed**):
- **Landed:** run explorer **Design cloud** (`/api/umap`, `#/run/<id>/umap`) â€” PCA always, UMAP if umap-learn installed.

Local-only, updated 2026-11-03 (**UMAP HTML param panel fix; no GitHub issue state changed**):
- **Fix:** UMAP evidence HTML embeds `window.UMAP_DATA`, 18-knob dropdown, full param table on click.

Local-only, updated 2026-11-03 (**UMAP evidence HTML for CMA-1000; no GitHub issue state changed**):
- **Landed:** `docs/evidence/UMAP_SOLANA_OSSE_MEH_SF_CMA1000.{html,md}` â€” interactive param/J-colored UMAP of run `20261103T053926Z-screen-8b32a1` (htmlpreview link in the md).

Local-only, updated 2026-11-03 (**Ath OSSE+SF mid_ports fork + solana_osse_meh_sf; no GitHub issue state changed**):
- **Mesher fork landed:** `hornlab-search/osse-midports` @ `55da4f4` (tag-10 L1 flush on native OSSE); pin in pyproject/TOOLCHAIN.
- **Solana MEH-context path:** `solana_osse_meh_sf`; 4090 screen **J=39.604**; CMA live best **Jâ‰ˆ22.3** (`20261103T052647Z-screen-cd22a5`). Flat CAD MEH = fallback. CMA-1000 `20261103T053926Z-screen-8b32a1` still LIVE (~gen 70+, best **7.75**).
- **Solana owed:** finish/pull CMA-1000; mouth-matched CD (`gcurve_off`) verify; enclosure/LF.
- **SAWMOD owed:** Ath knuckle+ports (not flat MEH), LF 10â€³, BL refine.

Local-only, updated 2026-11-02 evening (**Solana/SAWMOD + RunPod path on `feat/solana-sawmod-wg-bench`; no GitHub issue state changed**):
- **Cloud landed:** `tools/cloud/*`, `docs/CLOUD_GPU_RUNBOOK.md`, POSIX orphan-julia cleanup; **4090 CP-9a 0.020/0.039 dB**; Solana CUDA screen; `osse_baseline_4090` CMA in flight / owed finish+pull.
- **Solana landed:** Ath WG + evidence; MEH CAD `solana_meh` / `solana_meh_search` + brief; mouth probes `_solana_mouth_probes/`.
- **Solana owed:** mouth-matched CD (`gcurve_off`) 4090 screen+verify; Ath midports; enclosure/LF.
- **SAWMOD landed:** control WG + knuckle + `walls: lr` MEH probe; CAD/`step_build` accept `lr`.
- **SAWMOD owed:** Ath knuckle+ports (not flat MEH), LF 10â€³, BL refine.

Local-only, added 2026-11-01 late afternoon (**Solana 2.0 phase 1 + SAWMOD phase-2 probes; no GitHub issue state changed**):
- **Solana landed:** DIY Guide + `athscript.cfg` snapshot, dossier, `solana_osse` / `solana_control_1in_90x90`, Metal screen 4284 dofs J=41.9
- **Solana caveats:** freestanding; `a_deg` inferred 45; SF mouth ~450 vs Ath morph 353 / STL ~376.
- **Solana owed:** mid ports + 4Ã—6NDL38 MEH, enclosure/LF, mouth-delta diagnosis. (MEH CAD seed landed evening 2026-11-02; Ath midports still owed.)
- **SAWMOD phase-2 probes landed:** knuckle Metal J=241 (`3c1938`); MEH lr2 multi-source path exercised.
- **SAWMOD still owed:** Ath knuckle+ports (not flat MEH), LF 10â€³, BL refine; SAWMOD MEH follow-ups.

Local-only, added 2026-11-01 afternoon (**SAWMOD control WG bench phase 1; no GitHub issue state changed**):
- **Landed:** whitepaper PDF snapshot, dossier, pinned `sawmod_control_osse` + brief.
- **Still owed:** Ath knuckle+ports, LF 10â€³ slot, Boundary Lab `Multi_region_SAWMOD` refine.

Local-only, added 2026-11-01 (**PR #17 merged to main + the hardware-neutrality rule; no GitHub issue state changed**):
- **Merged (squash):** Metal backend + Mac path, Hansen budget hint, staged A/B harness, CMA
  covariance dump, CMA pin plan, restart controls (jamescollinharky's PR #17). Two merge defects
  fixed before landing: spawn-free `auto_backend()` (Apple Silicon -> Metal, else `None`, never a
  silent CPU swap) and `--backend` applied before config validation (drops `cuda_fused` off CUDA,
  so `config_sha` / snapshot / `run.json.backend` agree).
- **Rule (owner):** results and data must not depend on the solver backend. No silent backend
  swaps; the backend is explicit, hashed into `SolveSpec`, and recorded in `run.json.backend` and
  dataset provenance; cross-backend pooling only after a measured parity check.
- **Owed:** (a) GPU-box staged A/B (`tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`,
  paste COMPARE.md); (b) Mac<->4060 Metal parity <=0.2 dB before Metal enters campaign/compare;
  (c) a cross-backend parity test (one design, CPU vs CUDA vs Metal) behind a marker, plus a
  comparison view that surfaces the backend; (d) move `gui.data.sensitivity` out of the GUI layer
  (`pin-plan` imports it).
- **CI:** unblocked main's red Actions run (a collection error from `tests/test_gui_preview_shape.py`
  when the optional mesher is absent under `--no-deps`). The suite now skips in that environment
  instead of aborting the whole run; a changed mesher pin still fails.
- **CI (part 2):** the remaining ~24 red tests were un-gated optional-dep users (`hornlab_mesher`,
  `hornlab_beat_bem`, `ribs`) plus 3 Windows-only assertions. All gated/fixed; a missing dep now
  skips instead of failing. Re-enable real coverage for those areas by installing the pins in CI
  (or a second job) when that is worth the runner cost.

Local-only, added 2026-10-31 (**staged search A/B protocol + chaining harness; no GitHub issue state changed**):
- **Landed:** `examples/typologies/staged_ab_2026-10-31/` (joint 60 vs A/B/C 20+20+20 on crease__core_law),
  `tools/run_staged_search.py`, `tests/test_tools_staged_search.py`, evidence
  `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`.
- **Synthetic coupled A/B:** staged+polish wins (J 0.100 vs joint 0.302) â€” keep the tools/ harness;
  do **not** change the default `search` path until the GPU acoustic A/B runs on the CUDA box.
- **Owed (GPU box):** `python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`
  (one job at a time); paste COMPARE.md numbers into the evidence doc.
- **Still higher leverage than staging:** objective term normalisation (smoke night); diagonal
  balloon scoring for crease knobs.

Local-only, added 2026-10-31 evening (**CMA pin-plan; no GitHub issue state changed**):
- **Landed:** `pin_from_cma` + `hornlab-search pin-plan` + run-detail Pin plan table
  (recommend-only; optional `--write-config`).

Local-only, added 2026-10-31 evening (**CMA covariance dump; no GitHub issue state changed**):
- **Landed:** `cma_covariance` on `run.json` + run-detail GUI table (ÏƒâˆšCáµ¢áµ¢ shares + eigen loadings).
  Complements Spearman sensitivity; not a Sobol acoustic decomposition.

Local-only, added 2026-10-31 evening (**staged knob schedule in COMPARE/plan; no GitHub issue state changed**):
- **Landed:** `plan.json` / `COMPARE.md` list active vs fixed knobs per staged arm.

Local-only, added 2026-10-31 evening (**Mac .venv + Metal; no GitHub issue state changed**):
- **Landed:** project `.venv` + `[dev,crosscheck]`; Metal ready; dry-runs + budget-5 Metal
  smokes (tractrix / freeform_hv / conical); GUI auto `--backend beat_metal` when CUDA absent.
- **Still owed:** Macâ†”4060 A/B (<0.2 dB) before mixing Metal into CUDA datasets; doctor still
  FAILs the CUDA checks on Mac (expected).

Local-only, added 2026-10-31 evening (**Hansen budget heuristic; no GitHub issue state changed**):
- **Landed:** `search/budget_heuristic.py` + `GET /api/budget-hint`; Launch/Compose suggest
  `max(150, 100Â·N)` (Hansen) with IPOP/BIPOP restart inflation; GUI cap 5000.

Local-only, added 2026-10-31 evening (**Launch IPOP/BIPOP controls; no GitHub issue state changed**):
- **Landed:** Launch + Compose search forms â€” CMA restarts mode (config default / off / IPOP / BIPOP)
  + max; CLI `--restarts-mode` / `--restarts-max`; `jobs.py` allow-list. Run detail still shows
  the schedule read-only after the fact.

Local-only, added 2026-10-31 later (**beat_metal + Mac staged path; no GitHub issue state changed**):
- **Landed:** `beat_metal` in `BACKEND_NAMES` / `BeatBackend` / CLI; staged harness `--backend auto`
  â†’ Metal on Darwin (clears `cuda_fused`). See staged README + evidence doc Mac section.
- **Owed on this Mac:** create `.venv` with Python 3.12/3.13, `pip install -e ".[dev,crosscheck]"`,
  `doctor`, then the staged A/B; Macâ†”4060 A/B (<0.2 dB) before mixing Metal into CUDA datasets
  (P3 remainder).

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) â€” see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, 2026-11-01 (**hardware decision study; no GitHub issue state changed**):
- **DONE (decision study, not rental benchmarks):** owner clarified theoretical rent-versus-buy scope; $0 rental spend. `docs/evidence/HARDWARE_2026-11-01.md` audits stored timings and backend/lane code and gives current rates with labeled cost scenarios.
- **MEASURED (CPU mesh sizing):** fixed T2 seed first globally validates at 12 kHz among tested sizes at 33,959 dofs / 67,245 triangles (EPW 8.4). EPW 6 gives 33,938 triangles but only 8.58 kHz global validity. This does not establish acoustic convergence or a universal minimum.
- **SOURCE-DERIVED capacity constraint:** unchanged standard CUDA multi-channel path requires at least 85.410 GiB for operators+identities+LHS at that full-wall seed, before additional workspace. The 80 GB tier cannot fit that path. H200 141 GB is a test candidate, not a measured solution; cheaper 24/32 GB coarse-screen tests answer a different fidelity question.
- **OPEN:** successful exact 41-frequency request on candidate hardware, root cause of CUDA 719, actual billed cold/warm costs, unified-backend C4 parity and 1/2/4/8-lane results. Flat `nvidia-smi` peaks do not establish invariant live workspace. Historical seed/winner mesh attribution and current overwritten/unknown-baseline VRAM trace limitations are corrected in the study.
- **OPEN (implementation if shared-host lanes are selected):** per-device locks/monitoring, owned-host-only cleanup, private registries/cache staging, parent-only dataset writes and deterministic CMA coordination. Existing evaluator has side effects; the current one-writer/global-cleanup code is unsafe for naive concurrent workers. Separate machines, one brief each, are the simpler future deployment test.

Local-only, 2026-10-31 (**3D evolution transparency, re-landed on `meh/integration`**):
- **Recurring owner report (run `20261031T202159Z-screen-ba7648`): mesh renders as see-through triangles.**
  Not a renderer regression: the hole-free decimation fix (`64ccb20`) lived only on
  `feat/hardened-plan-2026-10-29`; this worktree is `meh/integration`, whose `gui/data.py` still stride-sampled
  (`M3D_VERSION=1`, cap 6000 -> 11.5k-tri frames cut to 5.8k). Code files cherry-picked here, cache key bumped
  to `[2,30000]`, stale per-run cache regenerated (`decimated:false`). The long-running GUI on :8765 must be
  restarted after any such change; a branch switch also silently reverts the working tree. 131 GUI tests pass.
  Detail: CONTINUITY 20:28Z.

Local-only, pushed 2026-10-30 late (**chief-implementer hand-off; no GitHub issue state changed**):
- **OPEN:** owner/lead agent to pull branch `ccr-4978c80b-tvvcgv` locally and run `docs/meh/CHIEF_IMPLEMENTER_HANDOFF.md`.

Local-only, not pushed 2026-10-31 (**MEH wave 1 merging into `meh/integration`; no GitHub issue state changed**):
- **DONE:** M4 network layer (merged, `meh/M4-network` parts 1+2: drivers, network, dsp, limits, synthesis).
- **DONE:** M4 inner optimiser (`hornlab_search/meh/inner.py`; merged `meh/M4c-inner`, commit `0cdfd7a`).
- **DONE (M8 step 1):** solver fork validated on CPU and CUDA - superposition, reciprocity, single-tag parity,
  reduced-vs-full symmetry all pass. The M2 Julia testset needed three fixture fixes (commit `93ef848`/`1efdc6f`);
  properties and tolerances unchanged.
- **DONE (M8 step 2):** single-tag parity vs the current pin <= 5.91e-5 dB on two finalists (floor 0.039 dB).
- **DONE (M8 screen):** T2 40-eval CMA + verify -> J 9.530 -> 11.894 (best `ed11d2cd3acc`); T1 40-eval CMA + verify
  -> J 13.228 -> 14.512 (best `704051ae928c`). Runs `20261101T004552Z-screen-427d57` and
  `20261101T015657Z-screen-fc1d24`; evidence `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **BLOCKED on this hardware (screen band):** the contracted 120-12,000 Hz 1/6-octave grid has no legal operating
  point on the 8 GB card. A 12 kHz-resolving mesh needs >= ~8,600 dofs (7.9/8.19 GB peak; the 41-frequency sweep dies -
  CUDA 719 / worker_exit, measured); the smallest legal mesh (epw 4.05, 8,044 dofs) leaves CMA neighbours at
  8,296-8,485 dofs, over any cap that keeps VRAM safe. `cuda_fused` refuses multi-channel by design. Resolving the band
  needs a >= 12 GB card. Stopped by owner direction.
- **DONE (docs accuracy):** the M8 evidence doc and its INDEX line now state the full result set (links 1/2/5/6 PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks); no number changed.
- **CI FIXED (PR #18):** `tests/test_solve_worker_restart.py` now gates `hornlab_beat_bem` with
  `pytest.importorskip`, so CI (which does not install the solver) skips it instead of failing at collection.
- **MERGED main (2026-11-01):** `origin/main` merged into `meh/integration`; 16 MEH-touched files normalized to
  LF (main is LF), logs unioned so no entry from either side was dropped, and main's Metal/backend-override work
  coexists with the MEH config changes. PR conflicts resolved.
- **DONE (GUI visibility, 2026-11-03):** the MEH searchable typologies are registered in `examples/catalog.yaml`
  under a new `meh` group, with the three derived artifacts regenerated. The three CAD-only seeds are
  intentionally not catalogued (the native domain requires knobs; multicell_3x3 is its only CAD exception), and
  the catalog comment records that choice.
- **SUPERSEDED (four-operator CUDA arm, spill; see `BENCH_AUDIT_2026-11-03.md`):** CUDA completes the 41-point 120-12k band at 38.5 s/frequency
  (1,577 s, 7,924 MiB) while CPU is ~18.2 s/frequency; on the real 12-point screen grid CUDA is 4.0x faster
  (25.7 vs 103.0 s). Julia threads 1/8/24 make CUDA slower (0.88/0.96x) - it is GPU-bound. Concurrent CUDA
  solves are ruled out on 8 GB by the 7.9 GB single-solve peak.
- **SUPERSEDED by the fused multi-channel path (`BENCH_AUDIT_2026-11-03.md`; four-operator CUDA arm):** neither backend wins outright. CPU beats CUDA below 1k dofs and
  above ~7k dofs (8.5k: 18.9 vs 53.6 s); CUDA is 1.5-4x faster at 1-7k. Physics parity 3.6e-05 dB. Practical
  rule: CUDA screens for 1-7k dofs, CPU above ~7k. Script `tools/bench/cuda_cpu_40designs.py`.
- **WITHDRAWN 2026-11-03 (CUDA arm spilled to shared memory; `docs/evidence/BENCH_AUDIT_2026-11-03.md`):** CPU is 6.4x faster than the 8 GB card at the production 8,044-dof MEH
  mesh (5.86 vs 37.2 s/frequency, SPL parity 5.0e-4 dB) and solves the 25,171-dof 16 kHz mesh in 100.7 s,
  which needs ~47 GiB of CUDA storage. **Revisit the GPU-first hardware conclusion for screening** (CPU may be
  the cheaper engine for this dof regime); the 16 kHz wall-resolution caveat (~10.3 kHz walls) still stands.
- **PACKAGED (handoff, PR #18):** `docs/meh/MEH_QUICKSTART.md`, `tools/meh/run_screen.ps1`, and
  `docs/evidence/meh_2026-11-01/` (both verified winners + README). No production code changed.

- **PR OPENED (wrap-up):** `meh/integration` -> `main`, carrying the full MEH implementation, the owner-approved
  pin bump, both verified screens, the six-line readiness proof, and the hardware audit/hand-off. Final offline
  suite green at the tip (exit 0). Open items inside the PR body: 8 GB band ceiling, M9 blocked, step 3 blocked,
  link 4 budget decision.
- **TIDIED (hand-off):** the withdrawn VRAM reading no longer appears as fact in s5/s5b; both now carry the
  source-derived operator-storage statement and point at the s2a corrections. Duplicate table row removed.
- **CORRECTED (hand-off):** four claims withdrawn after the audit - wrong mesh attribution (winners are
  5,872/6,249 dofs), the 12x scaling claim, the flat-VRAM reading (and its backing CSV was overwritten), the
  25-35k element sizing (first valid whole-wall mesh is 33,959 dofs, ~85 GiB), and 'lanes are one line'.
  The audit's rent-first conclusion and 141 GB tier stand.
- **UPDATED (compute brief):** the hand-off now carries the measured baseline (3.6 vs ~45 s/frequency;
  ~12x for 1.44x elements) and an explicit unified-memory section (GH200/GB200, Apple Metal, MI300A ROCm,
  APU negative control, CPU-only) with a required validation gate for any non-CUDA recommendation.
- **OPEN (next agent, compute/hardware):** `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` - fit the s/frequency and
  VRAM scaling laws, benchmark bandwidth vs compute tiers, measure candidate-level lanes on rented GPUs, and
  return a machine table in candidates/hour and $/candidate. Nothing in the MEH code blocks that work.
- **OPERATIONAL NOTE:** stale BEAT hosts from an earlier fused probe were adopted by a later run and produced a
  misleading fused/multi-channel error. Kill Julia hosts before launching a screen (`gpu-clean`).
- **DONE (worker recycling):** opt-in `solve.worker_restart_every` (fake-tested), set to 8 in both MEH search
  configs; it does not rescue the 8 GB ceiling but is committed for larger cards.
- **OPEN (verify fidelity):** `verify` reports that the verify mesh equals the screen mesh at the current band/caps;
  only the frequency count and balloon size change. A true higher-fidelity mesh needs a raised dof cap or a lower band.
- **DONE (readiness, measured on the stored T2 winner):** link 1 PASS, link 2 PASS, link 5 PASS, link 6 PASS (J
  9.530 -> 9.727 with a different mid driver and hp_hz, cached, no new solve).
- **FAIL (readiness link 4):** the inner optimiser takes 6.58 s for 1,224 CMA evaluations on the shipped T2 brief,
  3.3x the hand-off's < 2 s gate. Per-evaluation cost is 5.4 ms, so this is an evaluation-budget/combo decision.
- **PARTIAL (readiness link 3):** with the mid drive muted, a 9.19 dB notch appears between 1200 and 1300 Hz
  (+18.7 % to +28.6 % of the 1-D 1.0108 kHz), so the +-20 % gate is met only at the lower edge of that interval. A
  25 Hz sweep over 1150-1350 Hz is needed to place the centre.
- **BLOCKED (M8 step 3):** the meh CAD tool refuses a full model (quarter open shell only), so quarter-vs-full cannot
  be measured without extending the tool.
- **BLOCKED (M9):** Boundary Lab is not present in this workspace; it needs its own environment (pins BEAT 0.6.0).
- **OPEN (M8 step 4):** L0 vs L1 notch comparison is not run.
- **DONE (M10):** bass box - 7 woofer files, `tools/bassbox.py`, 65 tests, `BASSBOX_2026-10-31.md`. Recommendation:
  1 x FaitalPRO 18XL1800 sealed 55 L net + LT; pair = +6 dB; smallest = 1 x 15XL1400 sealed 38 L.
- **OPEN (task text):** M10's "B4 (fs = fb, Qts 0.383, alpha 1) is -3 dB at fs" is wrong for the lossless vented
  box (alpha = 1 gives 0.0 dB at fs; the B4 constant is alpha = sqrt(2)). The test asserts both; amend the task file.
- **OPEN (datasheets):** 15TBX100 (7.8 %) and 18NLW9601 (4.5 %) Vas/Mms vs Fs are internally inconsistent; Beyma
  15LX60V2 Xmax 8 mm vs +/-9 mm. Files follow C8 and say so in `notes`.
- **DONE:** M6 objective v5 + brief `meh:` block (merged, `meh/M6-objective-v5`).
- **OPEN (M7):** `search/evaluate.py` currently only bridges version 5 (params class + scorer registration); the MEH
  evaluation branch that builds `meh_ctx`, runs the inner optimiser and synthesises the response is M7's.
- **OPEN (M1/M5):** cone `frame_od_mm` / `motor_od_mm` / `dish_mm` and CD `duct_mm` are not in the s8 table; M5 keeps
  the C9 [inferred] placeholders (CD duct 40 / 25 / 25 mm) until a drawing is read or M8 measures it.
- **DONE:** M3 multi-tag solve adapter (merged, `meh/M3-solve-adapter`).
- **OPEN (M8 gate):** the installed `hornlab-beat-bem` has no `SolveConfig.impedance_matrix`; every multi-tag solve
  raises ConfigError until M2's fork branch is validated on the GPU and the pin is bumped (owner approves the bump).
- **OPEN (M5 follow-up):** seed renders not produced - `hornlab-render` needs `pyvista`, absent from the venv and no
  installs are permitted. `cd_duct_mm = 0` is not modelled (no disc face without a bore). Unknown cone
  (cutout, depth) pairs are refused until M1's driver files land.
- **OPEN (local, not mine to commit):** the integrator's checkout carried unrelated regenerated catalog work
  (cone_plughorn_2026-10-28 entries typed 2026-10-31 in `examples/catalog.yaml`, `docs/reference/PARAMETERS.md`,
  `TYPOLOGIES.md`, `param-catalog.v1.json`); preserved as a patch outside the MEH branch.

Local-only, pushed 2026-10-30 18:10 EDT (**MEH integration started on the owner's box; no GitHub issue state changed**):
- **IN PROGRESS:** `meh/integration` created from `origin/ccr-4978c80b-tvvcgv` (hand-off section 0); baseline suite
  green after fixing two pre-existing reds (stale sandbox.js dispose pin, CRLF-committed `param-catalog.v1.json`).
- **OPEN (blocker, GPU):** night queue `n2_gapfill_2026-10-30` occupies the only GPU; M8 GPU validation/pin bump waits
  for it to finish (CLAUDE.md: never start GPU work while a night queue runs).
- **OPEN (owner):** confirm the 380 mm box depth assumption (M8 readiness step 1 + layout feasibility depend on it).

Local-only, pushed 2026-10-30 (**MEH implementation hand-off; no GitHub issue state changed**):
- **OPEN (wave 1, dispatch-ready):** M1 driver files, M2 solver fork multi-tag + impedance matrix, M3 solve adapter,
  M4 network + inner optimiser, M5 CAD tool + multi-label STEP, M6 objective v5 + brief block, M10 bass box
  (`docs/meh/README.md`).
- **OPEN (wave 2/3):** M7 pipeline + configs; M8 GPU validation, pin bump, first screen (owner's box); M9 Boundary Lab.
- **OPEN (owner):** confirm the 380 mm box depth assumption.
- **CLOSED:** dossier s13 questions answered by the owner 2026-10-30 (dossier s14).

Local-only, pushed 2026-10-29 20:15 EDT (**mini MEH research pass complete for this round; no GitHub issue state changed**):
- **OPEN (owner decisions):** mini MEH targets - bass route (top + sub / one-box PR-vent ~106 dB / 3-way), size number, use and
  coverage, 4 x 4-inch vs 2 x 6.5-inch, DSP per channel, new J terms, commercial intent (Synergy patent)
  (`docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` s13).
- **OPEN (senior, `NOTES_FOR_SENIOR.md` 2026-10-29):** attribution fix in `docs/DRIVER_MODEL.md:42` (issue #78 is
  timini/horn-simulation); frozen-plan MEH tag note; BL symmetry note.
- **CLOSED (research):** web-lane findings folded into the dossier s7-s8 with orchestrator spot-checks.
- **FINDING:** compression-driver internal depth sets the mid ceiling in a mini MEH (1-D); any MEH model must include it.

Local-only, pushed 2026-10-29 18:45 EDT (**mini MEH research pass, draft; no GitHub issue state changed**):
- **OPEN (owner decisions):** mini multiple-entry horn targets - separate sub vs bass in the box, size number, use case /
  coverage, 4 x 4-inch vs 2 x 6.5-inch mids, DSP per channel, new J terms
  (`docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` s13).
- **CLOSED 2026-10-29 20:15:** web-lane findings folded into the dossier s7-s8.
- **FINDING / correction:** the mesher has MEH tag names 8-12 only, no builder; MEH geometry needs the CAD -> STEP route
  (multi-label) or a new builder. Python `SolveConfig` refuses more than one source tag although the engine supports it.
Closed rows #1-#11 (all closed before 2026-10-30) now live in [docs/history/ISSUES_closed.md](history/ISSUES_closed.md).


Local-only, added 2026-10-30 (**3D evolution transparency bug fixed; no GitHub issue state changed**):
- **FIXED (owner report): randomly transparent triangles in the evolution 3D time-lapse.** `data.evolution_frames3d` stride-sampled (`tris[::k]`) above the frame cap, so above-cap frames lost ~half their faces as scattered holes. Replaced by hole-free vertex-clustering decimation (`_cluster_decimate`), also used by `mesh_surface` in place of `tris[:max_tris]` truncation; symmetry-plane vertices snap to zero so the mirror seam stays closed. `M3D_DEFAULT_CAP` 6000 -> 30000 and `M3D_VERSION` -> 2 invalidate the stale stride caches. Real run `20261029T155433Z-screen-5b871c` now renders all 6 frames undecimated. 131 GUI/reader tests pass. Detail: CONTINUITY 16:00Z.

Local-only, added 2026-10-30 (**data consolidation executing; no GitHub issue state changed**):
- **Owner decisions (2026-10-30):** hardlinks are allowed in the run/cache copy path (amends
  `docs/plan/01_CONTRACTS.md` section 14 to "copy or hardlink, never symlink"); the off-machine
  backup gate in `docs/DATA_CONSOLIDATION_PLAN_2026-10-29.md` Phase 0 is waived by the owner.
  Correctness therefore rests on every writer into `runs/<run>/designs/<hash>/` being atomic
  (`os.replace` over a temp file), never an in-place truncate of a possibly linked inode.
- **Phase 0 done:** the 51 previously-uncommitted files on `feat/hardened-plan-2026-10-29` are
  committed (`chore(repo)`); no data deleted, moved or linked.
- **Phase 1 DONE (2026-10-30):** link-first `copy_entry`/`_copy_entry`, atomic
  `save_response`/`_write_json`, unlink-before-mesh-write on all three mesh routes; then
  `tools/data/dedupe_runs.py --apply` linked 49,968 run files and freed 13.30 GiB (0 errors,
  3,954 unmatched by design). Real-consumer gate passed on `ca15be` and `9766f0` (GUI detail,
  curves, surface, balloon, 3D evolution, `cli report`, `loudness_report`). `tools/data/doctor.py`
  is the standing health check.
- **DONE (2026-10-30):** consolidation complete. Dedupe 13.30 GiB, NTFS compression c. 4.8 GB,
  verified deletions c. 1.1 GB, `vizenv` relocated out of the repo. ~32.6 GB of repo data is now
  ~12.5 GB with +17.3 GB drive space; no solve was lost. Result doc:
  `docs/DATA_CONSOLIDATION_RESULT_2026-10-30.md`.
- **OPEN (data inconsistency, pre-existing, found by the dedupe safety check):** 143 run
  `response.npz` files do not match their cache entry byte-for-byte. In a sample the complex
  pressures agree to 1.2e-4 while `spl_h_db` differs by up to 4.7 dB and `spl_balloon_db` by up to
  19 dB, i.e. the same solve stored under two SPL conventions (an older/re-scoring write path).
  Both copies are intact; nothing was linked. Decide which SPL convention is canonical before
  re-scoring or training on mixed sources.
- **OPEN (known gap R8, unchanged):** dataset records still carry no `brief_hash`, `run_id` or
  `typology`. `tools/data/keepers.py` works around it with a `target`-block hash and a
  `family+grid/cad` label; adding the optional record fields is on the HANDOFF_BETA list.

Local-only, added 2026-10-29 12:20Z (**b3a retargeted to 80x80/600 + driver-exit f11 + gate-aware search; no GitHub issue state changed**):
- **Loading-window source (owner decision 2026-10-29):** the Re z >= 0.50 hold's upper bound now
  resolves `target.loaded_hi_hz` (explicit) > **driver-exit f11** from `driver.exit_radius_mm`
  (`1.8412*c/(2*pi*a)`) > stored `metrics.scalars.f11_hz` (the extended MAIN throat) > `BAND_HI`.
  The hold runs over `[F_X, min(BAND_HI, loaded_hi_hz)]`; LFP20/LFP50 and the other gates unchanged.
  Landed in `tools/rescore/gate_audit.py` and `hornlab_search/objective/scalar_v5.py`; the target
  fields live in `targets/spec.py` (config surfaces the brief's driver radius on the typed target
  only, so `config_sha` is unchanged). 65 focused gate/objective tests pass.
- **80x80/600 cell:** new brief
  `examples/briefs/hardened_2026-10-29_v5/b3a_pa_80x80_600_square_v5.yaml` (`loaded_hi_hz: 5653.0`)
  and config `examples/typologies/hardened_2026-10-29_v5/b3a__osse_ext_throat_80x80_600_v5.yaml`
  (budget 100, distance 10, seed 588x588). 80x80 natural pattern: H 89.65/80 = 1.121 and
  V 1.121 at 1.07 kHz, H/V 0.866 at 8 kHz.
- **Seed A1 (cache hit, run `20261029T121930Z-screen-10b954`): 0 pass-all, J = 3.24955.** H/V/DI/
  BW8K/Throat pass; **Loading FAIL** (`Re z 0.291` at 827.75 Hz inside [600, 5653]).
- **Correction retained:** the 72x72 target failed H at 1.07 kHz (89.65/72 = 1.245); the 0.291 Re z
  dip is a genuine ~828 Hz loading failure, not an above-f11 artifact.
- **COMPLETE (2026-10-29 13:42Z):** gate-aware 100-eval search
  `runs/20261029T122018Z-screen-9766f0` (100 new + 10 cached); best J **2.9053** (seed 3.2495);
  A1 **0/110 pass-all**; H 68, V 108, DI 109, BW8K 96, Throat 110, **Loading 0**. LFP20 110/110
  (min 282.3 Hz); best loading Re z **0.3767** (best-J 0.2763; seed 0.291 at 827.75) vs the 0.5
  floor. The 827 Hz dip is structural in the b3a ext-throat family. A1:
  `scratch/gate_audit_b3a80x80_search/`. No code/solver/fork change; no commit.
- **Next (owner choice):** change family/throat; native ATH core 2" is the only prior all-gate pass
  set (42 designs). Do not run another b3a 80x80/seed/target.
- **OPEN (feature, owner-gated):** a single typology with a searchable throat-style switch is
  feasible for generated (FREEFORM) typologies via an integer `throat_style` index +
  `throat_length_mm` (generator layer; no mesher/cache/search change). Native OSSE/ATH-core needs a
  mesher/fork change. No implementation started.

Local-only, added 2026-10-29 12:00Z (**b3a retargeted to 72x72/600 + f11 loading hold; no GitHub issue state changed**):
- **Loading definition (owner decision 2026-10-29):** the Re z >= 0.50 hold now runs over the solved
  frequencies in `[F_X, min(BAND_HI, f11_hz)]`, where `f11_hz` is the design's own first throat
  cross-mode from the stored `metrics.scalars.f11_hz`; absent/null falls back to `BAND_HI` (old
  behaviour). LFP20/LFP50 and the other gates are unchanged. Landed in `tools/rescore/gate_audit.py`
  and `hornlab_search/objective/scalar_v5.py` (`_load_v5`; `f11_hz`/`loaded_hi_hz` are unweighted
  diagnostics, no new weighted key). 56 focused tests pass.
- **72x72/600 cell:** new brief
  `examples/briefs/hardened_2026-10-29_v5/b3a_pa_72x72_600_square_v5.yaml` and config
  `examples/typologies/hardened_2026-10-29_v5/b3a__osse_ext_throat_72x72_600_v5.yaml` (budget 100,
  seed 588x588). The 75x60 files stay (75x60 passed H, failed V 90/60 = 1.50; 60x30 fails V 90/30).
- **Seed A1 (cache hit, run `20261029T115645Z-screen-567db8`): 0 pass-all, J = 3.43861.** H FAIL
  (1 of 14, worst at 1.07 kHz 89.65 vs 72, +24.5 %); V/DI/BW8K/Throat pass; **Loading FAIL** (Re z
  0.291 at 827.75 Hz inside [600, 3809.38]).
- **Premise correction:** the seed's stored f11 is **3,809 Hz** (design r0 = 26.385 mm extended
  throat), not 5,584 Hz (that is the 18 mm driver exit). The 0.291 Re z dip is at ~828 Hz, not 8 kHz
  (8 kHz Re z = 0.981), so the f11 hold does not rescue this seed. Recorded, not re-scored away.
- **Next:** a 100-eval GATE-AWARE search on the 72x72/600 cell (H pre-filter over [f_x, f11] or
  [f_x, 8k], loading pre-filter, feasible box), not another J-polishing pass. Do not run it without
  owner queuing.

Local-only, added 2026-10-29 04:05Z (**cone source model plan; no GitHub issue state changed**):
- **OPEN (plan, owner-gated):** `cone_plughorn` directivity above ~1 kHz is unearned - the cone face is a rigid
  axial piston, but a 10-inch paper cone stops being pistonic around 0.7-1.5 kHz. Plan:
  `docs/CONE_SOURCE_MODEL_PLAN_2026-10-29.md`, priorities **P0b**, WPs C0-C7.
- **OPEN (cheap, no risk):** C0 - stop calling `Sd_eff(f)` a directivity model (it scales level only) and print
  the piston-valid band on every cone report.
- **OPEN (blocker for C3):** `solve/bempp.py` drives tag 2 uniformly, so no profile can be cross-checked on the
  CPU yet; and beat enforces ONE `source_tag` (`velocity_sources` singleton) with `source_profile_alpha`
  fused-CUDA-only.
- **OPEN (hardware):** the settling measurement is an in-situ scanning LDV (fallback: 3-5 ring accelerometers);
  no published 10-inch-cone-horn vs compression-horn polar comparison below cutoff was found.
- **Do not:** rank cone_plughorn designs on 1-4 kHz pattern/DI until C2+C3 pass.

Local-only, added 2026-10-29 03:35Z (**typology links resolve by catalog name; no GitHub issue state changed**):
- **CLOSED:** `#/typology/cone_plughorn_7sh` still showed no geometry. The typology page links carry the
  CATALOG name, while `_preview_config` matched only the config's own `name:` (catalog
  `cone_plughorn_7sh` vs config `cone_plughorn__evo7sh_narrow`), so the endpoint returned 404.
  `_preview_config` now falls back to `catalog_name` (exact name wins); the same resolver serves
  `save_bounds`, so sandbox bound edits work from the same link. Verified over HTTP for all five catalog
  names (4002-4452 verts each; 5-7 s warm). Test `test_typology_link_resolves_by_catalog_name`.

Local-only, added 2026-10-29 03:10Z (**cone_plughorn 3D sandbox preview working; no GitHub issue state changed**):
- **CLOSED:** "preview endpoint unavailable" on the plughorn typologies. The GUI process on `:8765` was
  from 2026-10-27, before `_plughorn_preview` existed, so it answered `available=false, reason="generator
  needs profile_h"`. Restarted; all five configs now return sections + 3D (5-6 s warm, 46.8 s first call).
- **CLOSED:** `cone_plughorn__morph_wide_8in` returned no 3D. One planar boolean-remnant face (634 mm^2)
  has no triangulation and `build123d`'s whole-solid `tessellate` turns that into an empty payload.
  Added `_tessellate_part` (per-face fallback + `shape3d.warnings`), display-only; the solid/STEP/mesh
  are unchanged and gmsh meshes it (3,182 tris). Verified: 3720 v / 3294 t with the warning shown.
- **OPEN (cosmetic):** the 8-inch morph view is missing that one face; the durable fix is in the CAD
  boolean, not the preview. Also open: the ~45 plughorn knobs are catalog placeholders with raw key names.
- **Note:** the sandbox sliders were verified through the API (`length_mm 400->430` moves the sections,
  `plug_tip_x_mm 190` rebuilds the solid). No GPU solve involved - the 3D preview is CAD tessellation.

Local-only, added 2026-10-29 02:50Z (**cone_plughorn exposed in the GUI catalog; no GitHub issue state changed**):
- **CLOSED (this pass):** the Funktion-One cone mid horn was invisible in the GUI. Cause: the five configs
  sit in `examples/typologies/cone_plughorn_2026-10-28/` and `_config_sources` globs only the top level, so
  without an `examples/catalog.yaml` entry they never reached `build_catalog` (no catalog name, group,
  description, or knob list; absent from `param-catalog.v1.json` and both reference docs). Five entries +
  new group `cone` added, artifacts regenerated (41 -> 46 typologies), guard test added.
- **OPEN:** the plughorn knobs are catalog placeholders (`documented: false`, raw key labels) - a ~45-key
  prose pass in `knobs_generators.py` is still needed for the tooltips to say what each CAD key does.
- **OPEN (not from this pass):** `tests/test_gui_sandbox_page.py::test_3d_hot_swap_never_scenes_per_frame`
  asserts a literal `sandbox.js` line that no longer exists (the file now disposes via a `ridgeCache.delete`
  block). Stale test on the committed tree.

Local-only, added 2026-10-29 02:20Z (**cone driver model + bowl + cone fill; no GitHub issue state changed**):
- **CLOSED (this pass):** axe-head cone fill not modelled. The fill is now one lofted solid with the base;
  Evo 7SH front chamber 0.848 L gross -> 0.201 L net, front-chamber cut-off 419 -> 1792 Hz.
- **CLOSED (this pass):** the driver model had no cone path. `kind: cone`, `rear_box_l`, `rear_box_q`,
  LR-2 semi-inductance, `air_load_g`, `f_breakup_hz` [inferred]; compression path bit-identical.
- **OPEN (blocker):** thin-gap CPU cross-check cannot run at the correct cone drive -
  `source_motion: axial` is refused on `bempp_cpu` (beat backends only); `beat_cpu` needs
  `python -m hornlab_beat_bem.provision --backend cpu` and a free machine. bempp at ~9k dofs did not
  finish one frequency in ~20 min during a live night. Mesh is cached at `scratch/thin_gap/epw6/`.
- **OPEN (hardware):** the real paper-cone driver's T/S, Mmd split, net bowl volume and break-up are
  still unmeasured; protocol in `docs/research/MEASUREMENT_CONE_DRIVER_2026-10-28.md`. Four published
  stand-in files exist (`examples/drivers/bc_10mbx64`, `faital_10pr300`, `bc_8mbx51`, `faital_8pr155`).
- **OPEN:** `cone_plughorn` still never solved (GPU night was live).

Local-only, added 2026-10-29 02:35Z (**CPU second-lane hardening pass; proposal only, no GitHub issue state changed**):
- **OPEN (senior sign-off):** CPU second solve lane beside the GPU lane - plan/alternatives/risks in
  `docs/research/CPU_SECOND_LANE_HARDENING_2026-10-28.md`; 8 decisions in Â§12; expected ~1.5-1.7x screen throughput, not 2x.
- **OPEN (blocker before any CPU work):** CPU engine unprovisioned on this install (`backend_ready("cpu") == False`;
  installed fingerprint `4ef2da0d...` != recorded `a19e67a0...`). Re-run
  `python -m hornlab_beat_bem.provision --backend cpu` with the GPU idle; add a `doctor` check.
- **OPEN (code):** `--backend beat_cpu` on a `cuda_fused: true` config raises in `BeatBackend.__init__`
  (`solve/beat.py:395-401`) because the override runs after validation (`cli.py:371-373`); drop `cuda_fused` for non-CUDA
  backends or re-validate after the override.
- **OPEN (ops):** campaign after-job hygiene (`search/campaign.py:411-419`) and `gpu-clean`/the night runner
  (`search/hygiene.py:117-144`, `tools/run_campaign_night.py:~431`) kill every project Julia by keyword; a live CPU lane needs a
  `.cpu.lane.lock` marker or those paths must be lane-aware.

Local-only, pushed 2026-10-28 20:50 EDT (**cone mid horn typology + research; no GitHub issue state changed**; 8 commits to origin/main):
- **OPEN:** `cone_plughorn` never solved on the GPU; first screen should use `source_motion: axial` and a CPU cross-check of the
  2.4 mm axe-head/throat gap (thin-gap risk).
- **OPEN (handoff):** paper-cone driver T/S unknown (Funktion-One publishes none); axe-head cone fill not modelled (front-chamber
  cut-off estimate too low); see `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md`.
- **OPEN:** compression-driver library lacks Sd/Mmd for every driver (absolute sensitivity model cannot run on them yet).
- **LOCAL ONLY:** `third_party/` (LibreDWG, ODA File Converter) and `reference/` (Funktion-One CAD) are gitignored by design.

Local-only, added 2026-10-28 17:45 EDT (**no GitHub issue state changed**):
- **OPEN:** round-throat `rt__b1t__rosse_morph` and `rt__b2t__rosse_morph` scored J 1000 on every eval (infeasible); diagnose before re-queueing.
- **OPEN:** verify slips 0.9-2 J for ATH 2in core / ridge and Salmon / Le Cleac'h tall shapes vs screen; screen ranking of those is optimistic.

Local-only, added 2026-10-28 afternoon (**skills + tools, no GitHub issue state changed**):
- **OPEN:** `tools/night_queue/queue.ps1` and `launch_detached.ps1` are parse-checked only; first live use should be the next queue launched
  when no night is running (watch the log and the controller's parent process).

Local-only, pushed 2026-10-28 15:05 EDT (**render sheets for the day's solved styles, no GitHub issue state changed**):
- **OPEN (owner decision):** the new b3a leader `hy__osse_flare_curl` J 1.113 wins on pattern but is weakly loaded (output gap at f0
  11.5 dB, loaded from 1.76 kHz) and `objective.load` is weighted 0 in that brief, so J cannot see loading. Decide: accept EQ, or add a
  load-weighted re-score of the day's top designs before the verify night.
- **OPEN:** screen-only. None of the 2026-10-28 winners has been through `verify`; the D_verify night has not started.
- **FINDING:** non-square mouths (60x40, 72x44) score 11.9-21.6 J on the 90x90 brief (3 of the 4 worst results of the day) - drop that lane
  unless the brief changes. Four-petal Salmon quatrefoils land in the chanterelle band (9-12), not the hybrid band.
- **OPEN:** full offline suite not re-run since the `osse_rollback` / `fc_fold` / `fc_union` changes (blocked by the live GPU night).

Local-only, pushed 2026-10-28 11:36 EDT (**shape work + night queue, no GitHub issue state changed**; 9 commits to origin/unified-typologies):
- **OPEN, first result:** constant-directivity hybrid `hybrid__os_ruffle` J 3.83 (b3a 90x90, 40 solves) vs best Salmon chanterelle 10.73. Refined
  petal/lobe horns (`examples/typologies/petal_os_2026-10-28_v4/`) queued in night `v4_day_H2_hybrids_2026-10-28`; not yet solved.
- **OPEN:** the full offline suite has not been re-run since the osse_rollback / fc_fold / fc_union changes; run it when no GPU night is live.
- **OPEN (owner):** round-throat A/B cells (`examples/typologies/round_throat_2026-10-28_v4/`) queued; the non-round effect is still unmeasured.
- **LEFT ALONE:** `hornlab_search/gui/static/sandbox.js` and `view3d.js` carry uncommitted changes not made in this session.

Local-only, added 2026-10-27 late evening (**P12 senior pass, zero GPU - no GitHub issue state changed; to-dos are P0 in `docs/NEXT_DEV_PRIORITIES.md`**):
- **OPEN, owner inputs:** driver list per brief + use case (tube-amp hi-fi / PA); gate levels (hi-fi sensitivity floor at 1 W / 1 m,
  PA max-SPL target); scoring decisions (output-at-f0 term, stricter hi-fi pattern, 10 m, half weight above f11); woofer block per brief.
- **DEFECT (new):** OSSE / R-OSSE `aspect_ratio` stretches the driver coupling plane (24x36 ... 50x36 mm on 36 mm briefs; 8 of 30
  winners). Owner rule decided: round coupling plane at the exit size, no adapter. Fix: lock `aspect_ratio = 1` in the next night's
  OSSE/R-OSSE copies, then a pre-mesh refusal via `mesh/throat_check.py` (after the night).
- **IN PROGRESS:** ripple/ridge night stopped after 6/10 jobs (runner killed from outside ~20:08 EDT, job 7 at 87/100); re-run
  night `v4_ripple_rerun_2026-10-27` launched 21:27 EDT, detached via WMI (resume job 7 + the three flute jobs that never started).
- **FIXED 2026-10-28:** the night runner now takes over a dead holder's `runs/.gpu.lock` (`gpu-clean` still does not).
- **OPEN (owner challenge):** how much a non-round driver coupling matters is unmeasured; round-throat A/B cells run 2026-10-28;
  a one-design A/B with a round source + built-in transition section is owed (new geometry option).
- **FINDING:** the b3a 90x90 / 400 Hz brief has no acceptable horn yet (leading cells 11-13 dB short of loading; 1.4" OS-type throats
  cannot load there) - needs loading-capable families or a 2" exit, not a re-rank.
- **OWED:** calibration night (band-split screen, 10 m vs 2 m, epw 6 vs 9 presence band, verify-grid rank check); new screen grid
  (low band to 0.7 f0, ~7 presence-band points); budget = valid solves; reduced knobs / two stages / successive halving; CMA-ME shape
  axes; `report --driver` in `cli.py`.
- **Small bug (pre-existing):** `tools/gen_param_catalog.py --check` prints its `committed=` / `fresh=` labels swapped (line 108).

Local-only, added 2026-10-26 (**campaign Phase 0 Steps 2C/3/4/5 LANDED â€” CPU only, no GPU/Julia; no GitHub issue state changed**):
- **What is now in the tree**: six lane reports (`docs/research/campaign_2026-10-26/`), 14 briefs (`examples/briefs/campaign_2026-10-26/`), 23 configs (`examples/typologies/campaign_2026-10-26/`), and `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md`. All 23 cells dry-run green; dofs 921â€“9,871; envelope 0; mouth within 10 % of K-law on tall/square and inside-envelope on wide; LHS invalid 0â€“37.5 %; grids 12/29/36; no cell dropped.
- **Open items for the campaign owner/gates (unchanged, now with measured seeds):** (1) the one BEM verify seed per portrait morph/rows class before a long campaign (geometry is proven, coverage is not); (2) `beat_bem` rejects the xz native symmetry plane, so `native__lecleach_asym_odd` keeps `span: full` / quadrants `'1234'` and the `half_xz` 2Ã— saving stays unused on GPU (ISSUES entry in the Phase-0 code commit); (3) Phase B items 1â€“4 still own the fused s/candidate and the >15,984-dof go/no-go; (4) the D-11 option (a)/(b) choice is now encoded per cell (tall cells strict K-law, wide cells commercial convention) but remains the owner's ruling if the campaign is re-frozen; (5) `cov_band_hz` (D-3) is not implemented and is not needed by these cells (f11 is disclosed per brief instead).
- **Non-blocking residuals recorded in the evidence doc:** LHS invalid rates of 31â€“37.5 % on four cells (below the >40 % narrowing trigger) are envelope/geometry refusals, not crashes; one `b3bt__rosse_morph` LHS corner is above 12,000 dofs and is graded infeasible; the biradial/hypex generator rows print a pre-existing H/V throat-tangent warning while meshing validly.


Local-only, added 2026-10-27 (**campaign smoke night LANDED - report only, no code/config change; no GitHub issue state changed**):
- **Report:** `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` - 41 jobs, 376 evaluations, 252 valid / 124 refused (33 %), 157.8 valid evals/hour, T0 26/27, crease A/B at equal budget 60, WALLS, the 8 kHz fused ladder, and the observer phase split.
- **Crease class confirmed on GPU:** `crease__core_law` J 19.022 -> 2.784 (-85 %) keeping the crease (a(45) - mean(a0,a90) = +9.97 deg); `crease__osse_b1w` no gain; control -46 %. One seed each - no typology-vs-typology claim yet.
- **DEFECTS / OWED (new):**
  - `gcurve__osse_b1w` seed was **outside its brief envelope** (783 x 581 vs 380 x 300 mm) -> invalid, its T1 found 0 valid designs. **FIXED 2026-10-27:** the curve station now sits at the mouth (`gcurve_dist 1.0`, width 335; dist box 0.2-1.0, width box 100.5-368.5). Full mirrored mouth **335.2 x 291.5 mm**, T0 **J 9.85253, 1,855 dofs, 3,543 triangles**, v3 dataset record written. A dist-0.5/width-130 workaround was measured valid (367 x 292, J 6.289) but rejected because it changed the intended mouth scale. **Still open:** it pins `aspect_ratio 1.0` while the control runs 1.15, so it is not a clean A/B; and J sees only H/V planes.
  - **The objective terms are not normalised**, so weights do not mean influence: `load 0.5` is 2 % of J on `native__lecleach_rollback` while flat is 45 %. Four of eight scored cells are single-term >70 %. Normalise before any weight tuning.
  - `f_load_hz` = 500 Hz on that seed is the **grid floor**, not a measurement (screen grid starts at 500 Hz).
  - Per-frequency assembly dominates (73-96 % of one frequency's cost), so **frequency count is the throughput knob**; the 8 kHz ceiling binds just above 14k dofs (13,999 = 88 % VRAM, 16,960 = 96 % unusable).
- **Open gates unchanged:** BEM verify seed for the portrait morph/rows cells; T3 diagonal-balloon check for crease vs control (queued); full offline suite; LHS audit of the widened boxes; `tools/expand_walls.py`; sandbox law card browser check; catalog generator recursion into campaign folders; `osse_baseline` 803 x 643 vs its own 750 x 600 envelope; parked `make_shape_variants.py`.
- **Throughput (observer, to be re-measured):** over a ~6-minute search window the GPU solved only ~33 % of the time (`between_evals` 39 %, `refusal_or_mesh` 24 %), median utilisation 24 % at 931 MiB / 19 W, while the ladder rungs were GPU-bound at 100 %. The window is too short to schedule pipeline work from; relaunch `tools/observe_run.py` with the next full search night.

Local-only, added 2026-10-26 (**read-only run observer added - `tools/observe_run.py`; no GitHub issue state changed**):
- Samples GPU util / VRAM / power / clocks, CPU per process, the running job and the newest run's eval rows to `runs/nights/<night>/observe.ndjson`, then writes `observe_summary.md` (phase shares, utilisation histogram). Read-only: no solver launch, no writes into run dirs.
- **First measured facts (smoke night):** GPU is at 100 % during solves but idle through the CPU phases; the card was using 695 MiB at a 4.8k-dof cell while `python.exe` (128 %) and `julia.exe` (144 %) ran the mesh/metrics side at 22.6 % total CPU. Feeds the "2x faster" analysis: pipeline ceiling, concurrency headroom, VRAM per cell size.

Local-only, added 2026-10-26 (**senior scoring review of the native campaign briefs - text only; no GitHub issue state changed**):
- **Changed:** `native_ath_core_2in` and `native_twinray_380_14in` -> objective v3 with K-law f0 (1280 Hz; 743 / 1397 Hz per plane, computed from the published mouth dimensions); `native_lecleach_1200_1in` -> scored on loading (cov 0.3, load 0.5, z_min 0.7; dislope 0). **J on those three brief names is not comparable with earlier results.**
- **Deliberately unchanged:** all B1/B2/B3 briefs (already v3 + f0, wide ones with f0_v), the `*_rows` briefs (dislope 0), the B3b briefs (load 0.5 / z_min 0.7).
- **Known scoring limits, no code change tonight:** H/V planes only (diagonal crease/X-shape effects invisible); the screen grid starts at 500 Hz so the 400 Hz "loads to" claim is only judged at verify; the loading term is band-averaged and diluted by the always-loaded high end; coverage still graded to 8 kHz past the 1.4-inch driver's ~5.6 kHz cross-mode (owner's choice). A T3 diagonal-balloon check for the best crease vs best control is **queued, not run**.
- **DEFECT found during the smoke run (FIXED 2026-10-27): objective-v3 runs wrote no dataset records.** `hornlab_search/dataset/record.py` rejected `objective_version` 3 (`'objective_version' must be 1 or 2, got 3`), logged by **all 27** T0 jobs. `search.ndjson`, `best.json` and reports were unaffected; the phase-2 surrogate data was what was lost. Fixed by moving the allowed set to `hornlab_search/objective/versions.py::SUPPORTED_OBJECTIVE_VERSIONS`, shared with the `search/evaluate.py::_score` dispatch (import-time table check); records now reject anything outside it (`99`, `0`, `4`, `"2"`, `True`) and still treat a missing field as v1. Tests: `tests/test_dataset_record.py` (v3 write/validate/read + dispatch-table equality + end-to-end store), offline **1689 passed, 20 deselected, 1 warning**. A live v3 T0 wrote `dataset/shard-0030.jsonl`. **Records lost on the smoke night are NOT reconstructable from `runs/nights/smoke_2026-10-27/`** (logs + job-level `summary.jsonl` only); the per-eval `search.ndjson`/`metrics.json` survive in the referenced run dirs, so a bespoke backfill is possible from those, but no tool was written.

Local-only, added 2026-10-26 (**campaign boxes re-opened + 4 crease cells ADDED - config/text only, no GPU/Julia; no GitHub issue state changed**):
- **Owner ruling on record:** a search box is never the binding constraint; the brief envelope + mesh validity are. 180 searched knob boxes across the 23 Phase-0 cells were widened to physical ranges (never narrowing an existing edge, seeds byte-identical 23/23, 25 pins intact, `infeasible_penalty: graded` everywhere). Tool: `tools/widen_campaign_boxes.py` (`--dry-run` table / `--write`); table + rationale: `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md` Â§8.
- **New crease class:** `crease__core_law`, `crease__osse_b1w` (per-direction `az_*` law) and `gcurve__osse_b1w` (superellipse guiding curve) against the existing `control__osse_morph_b1w`, all native OSSE with fused CUDA / 12,000 caps / Morph rect at the seed mouth. **Aspect-ratio divergence is an open interpretation:** 1.0 for CORE + gcurve (mesher requirement / circular), b1w's 1.15 for the two b1w cells (1.0 would break the 300 mm envelope). Senior to adjudicate.
- **Open gates:** the widened boxes are **NOT re-audited** - the invalid rate will show in the mini-T1; a T3 diagonal-balloon check (crease vs control, same budget) is **queued but not run**; the crease cells still need a BEM verify seed before any long campaign (same rule as the portrait morph/rows cells).
- **Still owed from Phase 0:** LHS audit of the widened boxes; `tools/expand_walls.py` (auto-widen a box edge best designs press against); the shipped `osse_baseline` 803 x 643 mm vs its 750 x 600 envelope (reseed or widen the brief - owner decision); `tools/make_shape_variants.py` + `examples/typologies/shape_variants/` stay parked and uncommitted ("pre-research ranges; superseded by the campaign crease cells"); campaign-folder configs get no catalog tooltips until `gen_param_catalog.py` recurses.

Local-only, added 2026-10-26 (**per-direction OSSE law LANDED - `az_*` knobs; no GitHub issue state changed**):
- **In the tree:** `design/families.py` folds 11 `az_*` knobs into the mesher's own `p`-expressions for `a`/`n`/`s` (the T0 validity gate for tonight's crease cells), `tests/test_design_azlaw.py` (6 pins), the sandbox law card, and ATH dossier section 5b. Focused gate 125/0/0/0; catalog `--check` OK (no regeneration); `node --check` OK.
- **Open, low priority:** the sandbox law card is committed **unverified in a browser** (owner deferred GUI click-testing); the full offline suite is **deferred** (owner: no CPU time on a night that has GPU work queued); `tools/gen_param_catalog.py` does not recurse into `examples/typologies/campaign_*/`, so campaign cells still have no parameter tooltips; `az_sf_m` is limited to multiples of 4 for quarter symmetry (a `half`/`full` model would need the mirror restriction relaxed deliberately, not silently).

Local-only, added 2026-10-25 (**PLANNED ONLY â€” nothing started, no code/config/bound touched**; owner-directed; filed as `docs/NEXT_DEV_PRIORITIES.md` **P9**, decision record in `NOTES_FOR_SENIOR.md`):
- **Defect on record (to fix)**: search time-lapse page â€” the `3D` checkbox renders **checked** while the canvas prints `3D off â€” flip the 3D toggle above.` Control state and render state disagree, or the render throws into the off-state placeholder. Exact grep anchor is that placeholder string. Not yet confirmed in code (code-map lane still running when recorded).
  **LANDED 2026-10-25 on `unified-typologies` @ cd71c1c** â€” root cause was a duplicate DOM id (checkbox and 3D container both `id="evo-3d"`); the checkbox is now `evo-3d-toggle` (container id untouched â€” an existing source pin pins the container markup), box state made coherent, and the stranded `_dispose3d`-on-the-input leak closed; `tests/test_gui_evolution_3d_toggle.py` (4 pins + verified negative control) added; the GUI trio 107/0/0/0 + node --check + compileall green. WebGL painting itself remains an owner eyes-on confirm (headless cannot render).
- **Owner ask 1 â€” per-parameter descriptions as hover text** on BOTH the Run page and the Typologies page, phrased as *what the parameter does to the geometry/acoustics* (the equation term it moves and the physical effect), grounded in the research dossiers rather than invented. Verified gap: `gui/static/glossary.js` has objective/metric terms only and **zero** geometry-knob entries; `app.js` has brief-field labels only.
  **LANDED 2026-10-25 on `unified-typologies` @ 711b856 (designer lane)** â€” `gui/static/paramtips.js` reads the committed catalog (graceful raw-key fallback everywhere, never a wrong-family guess); wired onto evolution knob rows, run-detail sensitivity table, seed-derivation card, compose seed preview, and the Typologies cards (knob chips); `tests/test_gui_param_tips.py` 10/10 + GUI trio 118/0/0/0 + node --check green.
- **Owner ask 2 â€” an interactive typology sandbox**: click a typology â†’ a page that draws the H/V wall section AND the 3D shape, where the owner drags knobs by hand and both views update live (replacing the run page's read-only "evolution" scrub for this purpose). Each slider shows the parameter name beside it, an editable **min and max on either side** of the track, and can **save those min/max as that typology's default**.
  **SPIKE PASSED 2026-10-25 (fix-5, measured):** live-drag 3D is real for generator/grid/native kinds (8-35 ms per full tick); rows kinds are march-bound (148-580 ms -> honest `slow: true` + release-debounce); `multicell_3x3` (CAD) is the only hard `available:false`; one silent-wrong-geometry hazard pinned (the preview entry point builds a default OSSE for unrecognized params - the endpoint must branch on kind first). Endpoint sketch + seam-module rule-2 compliance path recorded in CONTINUITY.
  **LANDED 2026-10-25 on `unified-typologies` @ 8715d88 (backend) + d5e3363 (page)** â€” full offline suite 1593/0/0/0 + node --check x8 + compileall + catalog --check green; details, timings and honest limits: `docs/CONTINUITY.md` sandbox entry.
  **Owner-screenshot follow-up (fixed):** the quarter mouth ring is now mirrored into a closed outline (both pages), the evolution frame-player's mm-vs-metre rig mismatch that left the 3D panel blank is fixed, and rollback meridians keep their own point order instead of being z-sorted (the striped vertical-plane fringe). Pins added for the ring quadrants and the rollback order.
- **Owner ask 3 â€” one findable source of truth** joining *typology â†’ design â†’ formula â†’ parameter â†’ min/max â†’ design characteristic â†’ the code that implements it*, for users and agents both. Proposed as an annotation layer over the existing authorities (`families.KeySpec` hard limits, `registry.DEFAULT_KNOBS`, `examples/typologies/*.yaml` bounds) plus a generated reference doc and a drift-gate test â€” explicitly **not** a hand-written fourth copy of the numbers (`AGENTS.md` line 29).
  **LANDED 2026-10-25 on `unified-typologies`** (P9, commits 4005e8a + bf20807 + 19cad0a): `hornlab_search/design/params/` (generators 26 / rows 36 base names / native 63 knob docs; 39 typologies; zero authored horn numbers), `tools/gen_param_catalog.py --write/--check`, the FAIL-not-warn both-ways drift gate (`tests/test_param_catalog.py`, 37 tests), the generated `docs/reference/{PARAMETERS,TYPOLOGIES}.md`, and the GUI wire contract `gui/static/param-catalog.v1.json` served through the existing static handler. Every knob carries `bounds_source = {file, key}` â€” the exact home a saved bounds edit must target. Details + honest contract gaps: `docs/CONTINUITY.md` 2026-10-25 parameter-SSOT entry.
- **Verified inputs for it**: 36 catalog ids in `examples/catalog.yaml`; 4 mesher families; 11 generator types; overloaded knob names `n`, `q`, `a_deg`, `T`, `stop_deg`/`max_wall_deg`; open doc/code mismatch `exponent` default 2.0 (`12_RESEARCH_BASIS.md:158`) vs 4.0 (`registry.DEFAULT_KNOBS`).
- **Hard dependency / guard**: the sandbox shows real bounds and must NOT let a "save as default" widen one. Bounds widen only via **W8** (per-typology search-box audit), per config, measured â€” consistent with the owner's recorded over-constraint remark and the oracle's S1/S5 tables.
- **Still owner-decided** (updated as of the parameter-SSOT landing): metadata package location â€” **resolved: `design/params/`** (built and landed there; import-light, numpy-blocked proven); whether saved slider bounds are a personal preference or an owner-gated edit to `examples/typologies/*.yaml` â€” **owner ruled 2026-10-25: edits save to where the bounds live** (to be built safely in the sandbox lane: write only the exact `bounds_source` key, validate against the hard `KeySpec` clamps, never touch a frozen contract, config_sha churn on resume is expected and honest); whether the sandbox may render an out-of-envelope design (and with what marker) â€” still open, will reuse the run page's at-limit red-marker language + `registry.envelope_overshoot_estimate`; which `exponent` default is canonical â€” **deferred, not blocking**: tooltips state each typology's actual seed instead, and the 2.0-vs-4.0 mismatch is surfaced with both claims, no winner picked.
- **Brief-set correction (2026-10-26, from the owner's killed run):** the 90Â° brief was paired with a non-CD Le ClÃ©ac'h and with an envelope smaller than its K-law mouth, and the Freeform narrow brief was unreachable because `mouthAngleDeg` is bounded â‰¥35Â°. Corrected briefs saved at 500â€“10,000 Hz; the 10 kHz dof ceiling (largest mouth 284 mm at the 5,000-dof screen cap / 379 mm at the 8,900 hard ceiling) makes most low-f0 briefs infeasible at that top. Full table + reasoning: `docs/CONTINUITY.md` 2026-10-26 entry. Open owner decision: whether the wide/narrow design briefs should keep a 10 kHz top (verify-only / mostly `mesh_too_large`), drop to 2â€“4 kHz for screen work, or move to a larger-VRAM card.
- **MEASURED GPU ceiling (2026-10-26, stress ladder, real VRAM):** 8 kHz is safe to **474 mm** mouth (5.8 GB peak, 2.4 GB headroom); 500 mm works at 7.2 GB (under 1 GB headroom, too tight for a search); â‰¥550 mm saturates the card. At 10 kHz: safe to **353 mm** (4.9 GB), edge at 403 mm (7.3 GB), â‰¥424 mm saturated. **No crash occurred** â€” the failure mode is CUDA OOM / host-backed pool oversubscription (pool reserved 15.9 GiB), logged as `Out of GPU memory â€¦ 100.00% (7.996 GiB)` at the top rungs, with hosts cleared afterwards. Three cap-500 briefs saved (`cap500_90x90_650hz_1p4in` â€” 90x90 at f0 650 Hz, 434 mm mouth; `cap500_90x60_850hz_1p4in`; `cap500_60x40_1270hz_1in`) plus the owner-override `narrow_60x40_800hz_1in` (794 mm mouth, no cap, may exceed the card at 8 kHz â€” accepted); practical home is a 5.5â€“6 kHz screen + 8 kHz verify. Superseded: `cap500_100x100_500hz_1p4in`, `cap500_90x90_565hz_1p4in`, `narrow_60x40_880hz_1in`. Details + full ladders: `docs/CONTINUITY.md` 2026-10-26 MEASURED GPU CEILING entry.

Local-only, added 2026-10-25 (typology pass completion + GPU smoke matrix + Phase-D baseline/R9 audit + GUI hybrid seeds; 6 lanes, exact-path commits; offline 1461/0/0/0 + BYTE-CHECK 24/24 + node/compileall gates):
- **Orphaned WIP landed** (docs-only commit): the prior pass's Â§16.7/Â§16.8 + INDEX line â€” validated against the committed dossiers (append-only, honest labels, no contradiction), prior author's voice preserved.
- **GPU smoke matrix** (the S1a configs' first GPU evidence, M4 pattern, one job at a time): biradial_keele GREEN (J 22.9837, 2086 dofs, 1301â†’2427 MiB), qtw_waveguide GREEN (J 37.4656, 1616, 1334â†’2104), lecleach_asym_odd FULL-RING GREEN (J 60.1446, 2815, 1337â†’3147); salmon_x_signed seed FAILS mesh_too_large (14,414 tris > 11,275; envelope overshoot 0.2201 pinned by the new test file), salmon_ripple12 seed FAILS (5,358 dofs > 5,000 screen cap) â€” both = owner-gated PROPOSALS (reseed / verify-tier), machinery healthy. Evidence `docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md`, bytecheck `tools/evidence_bytecheck_typology_smoke.py` (24/24 PASS + negative control).
- **Phase-D baseline settings**: `docs/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md` â€” five new configs' knobs/bounds/seeds verified per dossier + tier recipe + measured findings; **PROPOSAL-ONLY** default flips (rear_res_factor 1.5 AXI, balloon screenâ†’1024); objective-v3 DECISION CAPSULE for the owner (opt-in today; nothing flipped).
- **R9 audit**: `docs/research/typologies/R9_AUDIT_2026-10-25.md` â€” all 36 names walked (15 published / 18 labeled / 3 utility) + the do-not-cite ledger + five owner-gated PROPOSALS (lecleach_iwata_ar name, biradial_keele year suffix, C4 prose-vs-entries, Â§13.4 label hygiene, salmon_x pairing). No silent edits.
- **GUI**: /api/configs + generator_block/seed_params (verbatim); Compose hybrid captions from block shape ("hybrid â€” A + B"; rows kinds captioned "rows â€” {types}" after the orchestrator copy-fix) + per-pick seed preview (display-only, payload-fidelity pinned); objective-v3/mixed-key warn surfaces verified landed (4b42862). New test file: signed/ripple config pins (8/8).
- **Still owner-decided**: C4 catalog block (backend); the two smoke-matrix reseed proposals; the five R9 proposals; `examples/briefs/user/` gitignore-or-keep.

Local-only, added 2026-10-25 (evening; 3D render settings LANDED â€” owner screenshot â†’ fixer lane; brief_authoring 21/21 + node + compileall):
- **Landed**: persisted `hl-v3d-render` (surface satin/matte/metallic/studio Â· ridges on/thin/off Â· light Ã—0.5â€“2.0), shared `applyRenderLook`/`applyRenderControls` on both `init3d` and `init3dFrames`, clickable overlay chip (pointer-events:auto), immediate apply + global persistence ("swap easily in the 3D view or globally"); defaults = today's look byte-for-byte (existing captures/pins hold); disposal intact; no new hex; app.js untouched.
- **Honest limits**: WebGL cannot run headless â€” runtime paths source-pinned; chip interaction + cross-surface persistence in a live page await the owner's eyes-on pass.

Local-only, added 2026-10-25 (evening; S1a DRIVER PASS LANDED â€” oracle-decided/owner-directed; suite 1509/0/0/0; dry-run matrix 15/15; BYTE-CHECK 29/29):
- **Landed**: the brief family `{hifi_90x60, organic_rollback, lecleach_rollback} Ã— {1in, 14in, 2in}` (all f0 + v3, honest f0 derivations in-header); config research: `config.py` closure-aware biradial derivation (rm floored at r0 + tan(a)Â·L; the ONE owner-directed `widened_to_closure` exception, flagged + test-pinned) + the envelopeâˆ’2Ã—wall margin; reseeds (biradial L 195 + rm 210/230 bounds; x_signed stop 150/amp âˆ’0.15 â€” the 180Â° asymptote crossing; ripple12 stop 150; lecleach eps 0.20 + own family brief; elliptical stop 150 = the same recipe from my 4-test triage); C4 catalog (five entries incl. `symmetry: full`); decision record preserved verbatim (`S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md`) + research basis Â§16.9 pointer + NOTES_FOR_SENIOR.
- **Test-premise repairs (dated, nothing weakened)**: the salmon family's f0 briefs made three fixtures derivation-active â€” restored via derivation-inert fixture briefs with original assertions/tolerances intact; the salmon_elliptical derived-seed overshoot fixed by the measured reseed; derived-seed invariant drift (saddle 1.129 / x_shape 1.3025 report-only) disclosed â€” the seed-derivation card shows the clamps.
- **Solve-side**: the OWNER's own screen campaign (pid 14484, `user/7040use.yaml` Ã— the five families) ran against the repaired tree â€” the queued GPU re-smokes defer behind it / are superseded by its run evidence; J values non-comparable with the pre-repair matrix (new record groups).
- **Still owner-decided**: W8 the per-typology search-box audit (owner-directed, from the at-limit finding; bounds widen per-config only after the audit + cap checks); lecleach_iwata_ar naming (the owner's campaign runs it â€” the name decision remains open); stale user-brief descriptions (samonrip/75x35) â€” owner's files; `examples/briefs/user/` tracking decision.

Local-only, added 2026-10-25 (GUI S1a + G6 pass LANDED, re-grounded @ abcbebf; 114 offline tests green (+7) + compileall + node checks Ã—5; two disjoint fixer lanes, orchestrator reconciliation in place of Oracle per standing owner directive):
- **Landed (objective v3 / S1a)**: brief editor + Compose wizard expose objective version 3 ("scoring floor f0 â€” cov + dislope score only f â‰¥ f0"); run-detail KPI "Scoring floor" (target.f0_hz, present-only) explains the below-f0 mask; the seed-derivation card renders the K-law feasibility record from the run's committed config.yaml (per-knob derived/applied, `clamped to bound` pills, below-f0 solved-freq counts). The `J v3` badge is the already-generic `objective_version` renderer â€” verified, no edit.
- **Landed (G6 mounting)**: badge data verified live pre-edit on both WP12 enclosure runs (`solve_group.mounting` = the normalized block); `mesh_surface` now serves `mounting` additively from `mesh_meta.json`; `view3d.js` draws the dashed enclosure outline from the mirrored mesh's own bounding box (no invented geometry) + an on-canvas themed chip with the real depth/edge/margin values (chip is position:absolute over the canvas â€” the lanes' after-canvas caption would have been clipped by the fixed-height containers); compare gains the explicit "never rank across mountings" warn when `mixed_keys` includes mounting.
- **Verified-not-built**: axisymmetric-refuses-hv compat refusal already renders readably (campaign reader carries skip_reason; typologies compat reasons per brief) â€” pinned by a fixture test, no change needed. G5 (P6b owner gate), WP13 (owner-deferred), W7 (backend-gated), C4 catalog picker (pending backend) all stay gated.
- **Plan-doc addendum** appended to `docs/GUI_INTEGRATION_PLAN_2026-10-25.md` (Â§14): WP12/14/16/17 DONE, W6 landed, Â§3.8 `source_plug` naming resolved (GUI contract = `source_profile*` diagnostics), Â§3.11 mounting editor scaffolding superseded by the full-schema briefs editor.
- **Cross-lane note**: the backend stream's docs WIP (`docs/INDEX.md`, `docs/plan/12_RESEARCH_BASIS.md` Â§16.7/16.8) stayed unstaged/uncommitted here; `examples/briefs/user/` still untracked (owner decides keep vs ignore).

Local-only, added 2026-10-25 (GUI kill-current pass; owner screenshot markers; 107 offline tests green + compileall + node gates; orchestrator direct implementation per "just code it yourself"):
- **Kill run control for EXTERNALLY-started runs** (owner marker A: sidebar pill; marker B: Home running-card action row â€” both carry it now): two-step armed `â–  Kill run` â†’ `POST /api/stop-current` â†’ `jobs.stop_external()` kills exactly the pid recorded in OUR gpu lock file + its child tree, then gpu-clean (never an arbitrary pid; refuses while a GUI-started GPU job runs â€” the two stop paths never race; refuses killing the GUI's own pid). Safety contract changed by owner direction: the old "GUI only stops its own jobs" rule is superseded for the lock-holder pid our own lock file records.
- **Pill now ALWAYS visible**: idle renders a muted "no run in progress" indicator (owner: "I don't see it" â€” the old idle rendered literally nothing); external = `â–  Kill run`; stopped search = `â–¶ Resume search`; GUI GPU job = `â–  Stop`.
- **Removed**: the transient footer-holder guess (pre-observer) â€” the markers pointed at the sidebar pill and the Home card; plus the branch-order crash in `toolbarPillHtml(null)` (idle evaluated after the job read) â€” now node-tested.
- **Kill-safety contract on record**: the kill targets the pid+command OUR lock file records (whoever took our GPU lock wrote it), so the web GUI can never kill an arbitrary process â€” only the holder of our own lock; the lock file is bounded to the runs dir.

Local-only, added 2026-10-25 (GUI run-controls pass LANDED: Stop + Resume; owner-directed; 103 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per standing owner directive):
- **Landed**: Status-card Stop (three-state ownership rule: GUI-job two-step armed button / external-lock pill naming the pid / nothing; startup-window card), always-visible left-toolbar pill (app.js-injected `#nav-runctl`, 10 s poll, shared two-step arm, all four states), and the GUI `search --resume` plumbing (`resume: <run_id>` â†’ `search --resume <abs dir>`; config optional â€” the run dir's config.yaml is reused unless `--allow-config-change`; budget omitted = the run's own cfg.search.budget; mode passed from the run's record because the CLI's resume default is screen and rewrites run.json mode; `resume: true` bare-flag refused â€” the CLI contract takes a DIRECTORY).
- **Semantics on record**: Stop is a hard kill + gpu-clean (no graceful pause exists on Windows â€” "pause" = stop + resume, which is lossless for searches thanks to deterministic resume: cached rows replay free); budget is PER-INVOCATION, not auto-remaining â€” deliberate top-ups stay an owner action, never a pill side-effect (the pill guards budget-exhausted runs as finished); resumable markers = run.json status "running" (stale after GUI stop â€” no "stopped" value exists) / "interrupted"; "finished"/"aborted" not auto-resumed.
- **Honesty engineering on record**: every resume previews first (`POST /api/preview`) and the confirm click is blocked unless the previewed argv carries `--resume*` ("â€¦would start a FRESH search, not aResume; nothing was started"); resume id sourcing = the stopped job's own log_tail, validated against /api/runs (exists + budget not exhausted); Launch-row Resume deliberately skipped (Launch's 2 s re-render wipes a row-level arm mid-confirm â€” the always-visible pill covers it).
- **Owner visibility note**: the run-controls work was tree-uncommitted when first reported invisible (editable install serves static live but the Python process needs a restart for jobs.py) â€” after this commit, restart the GUI (`tools/launch_gui.ps1`) and the pill appears in the left toolbar on every page.

Local-only, added 2026-10-25 (GUI deferred-provenance pass LANDED, grounded @ 26a1de1; 93 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per standing owner directive):
- **Landed** (the four deferred items from the CAD-hold deferral): CAD STEP inventory projection onto the chip contract from `mesh_meta.json["cad"]` (verified against the CURRENT step_build keys incl. the WP12 WIP's non-change to the provenance block; sidecar wins; band{k}/meta fallback for WP8 designs added beyond the original spec), `cad_route` solve-group marker via the best-objective-row proxy, `cma_files` run_detail key + restart-card direct log chips, and the `source_profile_alpha` fingerprint pin test.
- **Verified-not-stale**: run-export STEP naming re-confirmed on disk (`<cfg.name>_<rank|seed>_<hash12>.step`; matcher covers both; the listed `STEP_NAME` contract unchanged) â€” the earlier draft regex would have missed `seed` exports.
- **W6 balloon integration verified already-wired** (the balloon commit's own route/button/back-links) and pinned by a test; zero overlap with the provenance/chips regions.
- **Future G6 note**: the in-flight WP12 mounting WIP was read read-only (brief.mounting normalized block; `mounting_key()` freestanding-safe; `mesh_meta.provenance.mounting` echo) â€” the mounting badge/preview builds when WP12 lands; nothing pinned against uncommitted code.

Local-only, added 2026-10-25 (docs pass: BL balloon research recorded + density TODO + CAD deferral; docs-only, no code touched):
- **Boundary Lab balloon rendering/resolution/frequency facts recorded** as the owner-directed append-only Â§12 in `docs/plan/12_RESEARCH_BASIS.md` (sources: committed BL extraction `research/boundary_lab_0.5/bl_inventory.md` + the W6 source recon; GPL-3.0 attribution carried): BL freq defaults 41 log-spaced 200â€“20 kHz (+ van-der-Corput non-monotonic GUI ordering quirk), balloon = equal-area Fibonacci sphere at `round(41253/angleÂ²)` points from a 0.5â€“15Â° precision dial (2.5Â° default â‰ˆ 6 600 pts), DI as a plain mean over the equal-area balloon, dB-to-radius blob rendering with tubed isobars/radar slicer/octave-smoothed slice.
- **W7 priority recorded** (`docs/NEXT_DEV_PRIORITIES.md`, mirrored in `NOTES_FOR_SENIOR.md`): raise verify/final-tier density â€” `balloon_points_verify` 512â†’1024â†’2592 ladder into 1 000â€“6 600, verify freqs 25 â†’ ~41 log-spaced â€” gated on the M3/WP5 Î”DI ladder + 8 GB GPU cost disclosure; feeds the W6 balloon view.
- **CAD deferral on record** (owner directive "GUI-only round"): my CAD reader lane cancelled, its partial code removed from the working tree (verified: `gui/data.py` diff carries only the parallel agent's balloon work); deferred design preserved verbatim in `NOTES_FOR_SENIOR.md` (cad block real key names, filenameâ†’hash regex, `cad_route` proxy, cma-files direct-chip listing). The backend M5/M6 CAD stream belongs to the parallel orchestrator session â€” its live edits in `config.py`/`design/families.py`/`mesh/build.py` untouched; the STOP record in NOTES_FOR_SENIOR is the cross-session signal.
- **Encoding-hygiene lesson**: PowerShell 5.1 `Add-Content` writes the ANSI default codepage â€” it silently corrupted NOTES_FOR_SENIOR.md's UTF-8 (cp1252 bytes, lossy special chars); caught by byte-level decode check; restored to HEAD (the append-only rule protects committed blocks only) and re-appended ASCII-safe via explicit-UTF-8 Python. All doc files byte-verified valid UTF-8 before commit.

Local-only, added 2026-10-25 (GUI 3D pass: inline run-page 3D + 3D evolution time-lapse LANDED; owner requests; 72 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per owner directive):
- **Commit-hygiene disclosure**: `599997d` (the GUI 3D commit) unintentionally swept in the M5B lane's staged-but-uncommitted files (35 files) â€” the M5B landing was mid-shared-index at commit time; its authoritative record is `94243df` + its CONTINUITY entry + evidence (bytecheck 33/33). Post-sweep tree verified coherent: offline suite **1335/0/0/0** at HEAD (`runs/m5b_rectify/suite.xml`), `test_mesh_pin` RESOLVED. Lesson recorded: verify `git diff --cached --stat` per-file before every commit when lanes share an index.
- **Landed**: inline ~300px 3D on run detail (lazy fetch, shared persisted shadows toggle, full 3D tab unchanged), `data-v3d` disposal sweep in route() + `isConnected` source-bails (no renderer leaks), `view3d.js::init3dFrames` frame player (union-bounds camera, lazy per-frame geometry build + hot-swap, decimation disclosure, 2D CDN fallback), evolution "3D time-lapse" with the disclosed RULE3D (3D âŸº improvements-only; "every candidate" stays 2D), `GET /api/evolution/<id>/frames3d` (shared `_improvement_flags` rule with the 2D reader â€” the two players cannot disagree; cache keyed incl. cap + per-frame mesh mtimes; mesh-less improvements SKIPPED + disclosed in `note`).
- **Open small items**: (a) frame count gaps between 2D "every candidate" and 3D are explained on screen by the reader's skip note â€” if the owner later wants mesh-less improvements rendered as interpolated ghosts, that is new work; (b) theme/resize re-render resets evolution playback to 2D (pre-existing control-state behavior; disclosed); (c) animation frames are improvement-chain only by design (every-candidate 3D would fetch every evaluated design's mesh â€” a deliberate honesty/payload trade).

Local-only, added 2026-10-25 (GUI integration plan G1-G4 phase LANDED; owner decision to start now; 63 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per owner directive):
- **Landed**: provenance badge strip on run detail (single source `solve_group`, tooltips = key path, f11 caveat conditional), restart schedule card + QD provenance caption (atlas canvas untouched), compare solve-group banners + DI-guard twin, `verify` GPU job kind (engine-true directory contract), C-5 raw pycma log serving (strict regex + containment), C-2 compare fingerprints (backend + freqs_hz identity always; WP16/WP12 keys read defensively for when their lanes land).
- **Deviation on record**: C-1's `step_files` stays a byte-identical string list (frozen test) â€” inventory rides the additive `step_files_detail` [{name, inventory|null}]; the GUI plan Â§5's "entries gain inventory" wording is thus implemented additively. `qd_algorithm` joined the fingerprint beyond Â§3.9's parenthetical (mixing CMA vs CMA-ME warns â€” judged correct, disclosed). The plan's "`GPU_KINDS` gain nothing" line predates G-1 and is superseded by the phase spec.
- **Open small items left to later passes**: (a) restart-log direct file chips need a file listing endpoint (C-5 serves files only; the card caption names the URL shape today); (b) STEP-inventory sidecars will populate chips only when the WP14 lane deploys its writer (plain-chip absence is the honest default); (c) `mounting`/`source_profile_alpha` fingerprints fire when WP12/WP16 land their config keys.

Local-only, added 2026-10-25 (GUI Compose wizard pass; owner UX direction "typology first"; LANDED on #/compose â€” 48 offline tests green, compileall + node --check clean, orchestrator review in place of Oracle per owner directive):
- **`#/compose` wizard landed** (app.js +534/âˆ’16 + one nav line + tests): typology-group multi-select first (per-group select-all; disabled configs visible-marked-unselectable with the engine seed-gate reason; uncatalogued configs selectable only as the sole pick, auto-deselected with a stated reason otherwise) â†’ brief step reusing the committed editor (new-from-scratch / typology brief_file / existing-brief-as-is; save-before-launch gate mirrors `jobs._repo_file` refusing non-existent paths) â†’ run step (1 config: dry-run/run/search; 2+: campaign tier + --families verbatim; preview shows the exact command; gpu_busy disables launch with server's reason; job id links to #/launch).
- **Pinned honesty finding**: campaign `--seeds`/`--budget` exist in the CLI but `jobs.build_argv("campaign")` reads only brief/families/tier â€” values passed via /api/jobs would silently vanish; the wizard therefore ships NO override fields (engine-default budget captions shown) and `test_campaign_budget_and_seeds_are_not_gui_plumbed` pins the pairing. If the CLI flags are ever plumbed into build_argv, BOTH must change together.
- **Disclosed UX behaviors on record**: re-picking a brief source restarts the editor (unsaved edits replaced, not merged); verify_only briefs remain selectable as existing-brief with the "only verify --brief" warning; family compat is never re-implemented client-side â€” the preview command + per-entry engine skips are the truth.
- **Open small item**: campaign seeds/budget plumbing into `jobs.build_argv` (owner-gated when wanted; the tests above are the guardrail).

Local-only, added 2026-10-25 (GUI briefs pass = c7d2bbf + hardening 95306db; user request + owner UX direction; editor LANDED â€” 39 offline tests green at the editor commit, 48 after the wizard; compileall clean):
- **Brief-authoring editor landed** (app.js + tests/test_gui_brief_authoring.py): New-brief-from-scratch, start-from-typology picker, every `load_brief` schema key exposed (symmetry/throat_angle_policy/objective/verify_only/description/z_min/freq_weights), payload fidelity (nothing silently dropped), and the GUI-invented 5500 Hz band clamp REMOVED (blamed to 77aac53b with no authored intent; the 8 GB dof-cap hardware note stays as an always-visible hint). Consequence worth knowing: band_hi can now be saved at any value (e.g. 12 kHz verify-only briefs are created from the GUI); search/run/campaign refuse verify_only briefs regardless â€” server-validated, GUI never clamps.
- **RESOLVED by the Compose wizard pass (block above)**: the typology-first wizard owner direction â€” shipped as `#/compose` in the next commit; campaign seeds/budget plumbing remains the only open small item (see above).
- **Post-commit Oracle read (returned after c7d2bbf was pushed; verdict GO-with-fixes, all applied in the follow-up commit 95306db)**: remaining suggestions on record â€” (a) `examples/briefs/user/` is untracked and NOT gitignored: the GUI creates real user briefs there at runtime; a `.gitignore` entry (or an explicit keep-with-sample decision) belongs to the 03-owning lane; (b) `z_min` input accepts values above 1 (spinner-only bound; `Target.from_dict` does not bound it; harmless, hint explains semantics).
- **Oracle waiver on record**: owner directive 2026-10-25 "no more new Oracle passes this round" â€” the editor's verification was the pasted test output + orchestrator diff read + live schema-fidelity save checks; the already-in-flight read DID land post-commit and its verdict + fixes were incorporated (see the 95306db commit + CONTINUITY).

Local-only, added 2026-10-25 (GUI 3D-quadrant fix pass; user-reported "3D views render just a quarter slice"; fixed + tested â€” tests/test_gui_mesh_quadrants.py 6/6, tests/test_gui.py 35/35, compileall clean):
- **GRID route writes no `mesh_meta.json`** (by design, `mesh/build.py:273` build_mesh docstring refers to the GRID route): the 3D route (`gui/data.py::mesh_surface`) previously defaulted those designs to `quadrants="1234"` (full model) and so rendered the raw meshed wedge instead of reconstructing the full horn. FIXED GUI-side (fallback chain meta â†’ search.ndjson row â†’ config.yaml â†’ "1234"); the DATA-SIDE follow-up stands open: the GRID route SHOULD write mesh_meta.json for provenance parity (`search/evaluate.py:500-516` logs absence only at debug) â€” ask for the grid lane.
- **2D mouth doubling covers only `'1'`** (data.py:873-884): for GRID half-models ('14'/'12') the mouth/front-view outline shows the meshed half only â€” same semantics class as the 3D bug; small follow-up, NOT fixed here.
- **Briefs page: user request RESOLVED (delivered across the briefs + Compose wizard passes, blocks above)** â€” create a NEW brief from scratch with asymmetric envelopes (wâ‰ h legal for every symmetry value â€” the engine only refuses axisymmetric briefs with unequal COVERAGE), symmetry control with the verbatim server rule shown, and typology-first picking; the confusing "symmetric horns" behaviour of the old editor was the missing symmetry control + the silent axisymmetric-coverage carry â€” both fixed.

Local-only, added 2026-10-25 (M5B pass; evidence `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md`, byte-check `tools/evidence_bytecheck_m5b.py` **33/33**; nothing flipped â€” every new key opt-in, absent = bit-for-bit):

**DEFERRED WP14 physics (owner ruling 2026-10-25 â€” "table the multicell horn thing for now; landing the category is cool"). The category IS landed (CADâ†’STEP route, tests green); THE PHYSICS IS NOT TRUSTED YET. The full resume recipe:**
1. **Focal-pair gate result (preserved, NOT to be used for trust decisions):** same mesh both arms (byte-identical `mesh.msh`, `mesh_hash 79c17524af5d`, 4501 dofs, 12 freqs 500â€“4000, 73-pt balloon): CUDA J=172.566 (17.3 s) vs CPU near+double J=471.984 (314.1 s); compare = **on-axis 11.28 dB / DI 14.59 dB / bw_v 159.1Â° max diffs** (re-captured `runs/m6_fork/compare_focal.log`) â†’ official gate **NOT ALLOWED** (bar 0.2 dB) on this fixture. bw_h = 180.0Â° saturated in BOTH arms (no information).
2. **ora-2's diagnosis (the reframe):** (F1, dominant) the fixture's mouth is a rigid `wall` and the driver is the REAR disk facing âˆ’z â†’ the exterior BEM solve measures **diffraction around a closed body, not horn radiation**: throat impedance matches a FREE UNBAFFLED DISK within 2â€“8% in BOTH arms (analytic (ka)Â²/4), DI is NEGATIVE in both arms (4Î» apertures cannot; self-shadowing signature) â€” **no far-field metric of this fixture is horn evidence until the mouth radiates** (open-mouth wall-shell topology like the OSSE lane, or an explicit mouth BC). (Gate restatement) the 4 kHz gate is unanswerable on this mesh â€” the validator's own global ceiling is **2891.68 Hz**; re-gate ONLY in the valid band and ONLY on non-threshold metrics (bw_v's 180Â° readings are âˆ’6.0206 dB threshold flips, verified `metrics/polar.py:17-34`; the 1287 Hz valley sits 1.05 dB from the crossing). (Attribution, ranked) #1 = arm-A's **near-correction omission** over ~O(10âµ) septa/second-ring pairs (the library's own refusal names this silent-wrong mode) â†’ **WP17 stage 1 (now LANDED + GPU-validated) is required, not optional, for any multicell GPU screen**; #2 mesh under-resolution near the driver (walls valid 3085.11 Hz vs 4000 requested; DistMax-400 rebuild = 12,694 tris / 6,349 dofs > the 5,000 screen cap â€” cap raise owner-gated, NOT made); #3 metric amplification (bw_v flips + dislope 597 vs 98); #4 FP32-vs-FP64 unlikely primary; #5 per-frequency-vs-single-call granularity unresolved (arm D never ran).
3. **Resume recipe (in order):** [a] fix the fixture topology: the mouth must radiate (export with the mouth `wall` faces REMOVED from the solid â€” open aperture â€” or an explicit treatment; re-prove closed/manifold + the solver's exterior contract for open-aperture geometry per the enclosure route); [b] optionally rebuild the mesh at DistMax 400 mm; [c] run the four CPU arms (plain-single, plain-double, near-single, near-double per-freq) on the SAME mesh + band-restricted (â‰¤2892 Hz) per-frequency table (on-axis/DI; NOT bw_v/dislope); [d] IF #1 attribution confirmed â†’ CPU-near arm re-validated vs the analytic/crosscheck references; [e] then the real gate: CUDA-fused-with-near (WP17) vs CPU with near, < 0.2 dB in the valid band â†’ ONLY THEN are multicell GPU screens allowed. Evidence preserved: `runs/m5_wp14_focal/*` (4 configs: cuda / cpu_near / cpu_plain [arm C ran â€” read `cpu_plain.log`; NO conclusions drawn], cpu_near_single [arm-D config only]) + the 2 focal run dirs `20261025T112316Z-screen-b22f31` (cuda) / `20261025T112519Z-screen-c6b2d8` (cpu near) + `mesh_meta.json` frequency-validation blocks + `run.json` bodies (cad echo + grid-honesty verified `available:false` in both arms).
4. **WP17 stage 2** (fused CUDA + per-image symmetry near caches): future fork work, refused by design until built (stage 1 = no-symmetry only).
5. **`near_correction*`/`solve_precision`/`source_profile_alpha` are NOT echoed per-row into `Response.meta`/records yet** (the GUI-planning pass's G-3/G-4 gap): the keys ride solve-spec `extra` (hash-distinct) and the WP16/17 diagnostics prove the path in the result â€” but per-row provenance parity remains a small follow-up lane (echo the set keys into the record's provenance solve block like `mesh_policy` does). GUI reads config.yaml meanwhile (per the GUI plan's disclosed contract).
6. **WP16/17 fork branches + pin state (landed, for reference):** `hornlab-search/wp16-source-profile` @ `f4ef05c`, `hornlab-search/wp17-cuda-near` @ `760a1ec` (test-env tip `a40a204` = CUDA@6.2.0 in the JULIA TEST project only) â€” pin on main = `760a1ec` (installed == pinned; `test_mesh_pin` green). Fork hosted: github.com/llevaachingada/hornlab-beat-bem (public, GPL-3.0). The pre-existing dev-pin note (`dev/fused-cuda-pin` @ `65c03de`) is SUPERSEDED by the hosted pin.

Local-only, added 2026-10-25 (GUI-integration planning pass; deliverable `docs/GUI_INTEGRATION_PLAN_2026-10-25.md`; docs-only, no GUI code, no GPU, nothing flipped):
- **In-flight WIP disclosed at planning time (owner lanes, untouched by this pass)**: WP14 + M4-debts WIP uncommitted on main (`config.py`, `solve/beat.py`, `gui/data.py` seed-gate memoize, `mesh/grid_build.py` EOF mesh-cache sketch, `pyproject.toml`, `tests/conftest.py`, test files, `examples/typologies/salmon_saddle.yaml`; untracked `tools/cad/` + `tests/test_cad_multicell.py` landed in-tree mid-pass; plus GUI-runtime untracked `examples/briefs/user/7040.yaml` â€” disclosed, left alone). FORK STATE RE-VERIFIED mid-pass: WP16 **committed** (`f4ef05c` on `hornlab-search/wp16-source-profile`, 7 files) and **pushed** to `ourfork/hornlab-search/wp16-source-profile` (github.com/llevaachingada/hornlab-beat-bem); fork checkout now on `hornlab-search/wp17-cuda-near` (at f4ef05c, zero WP17 commits) with fresh uncommitted WIP in 3 files â€” the WP17 lane's scope; owner gate B ("fork hosting") is an owner call, not asserted. Lanes own their commits (fix-3/fix-6 pattern; work lands late).
- **G-1** â€” `verify` missing from the GUI job allow-list (`gui/jobs.py:113-141`): verify runs are only reachable via CLI today; GUI plan G4 adds the (GPU) kind, contained to the allow-list + tests.
- **G-2** â€” `run.json.restarts`/`qd` written since M5 but never read by any view; GUI plan G2 surfaces them (reader additive keys + restart strip + raw `cma/restart_k/*` download route).
- **G-3** â€” `solve.near_correction*`/`solve_precision` ride `SolveSpec.extra` (solve-hash-distinct) but are NOT echoed into `Response.meta` (beat.py WIP emits only cuda_fused/mesh_policy/source_motion): per-row provenance parity gap; GUI reads config.yaml meanwhile, per-row echo is a WP14-lane ask.
- **G-4** â€” handoff's `source_plug` provenance field does NOT exist (rg = 0 hits): WP16 lane must add it to dataset `provenance` or confirm the GUI keys on the fork's `source_profile*` diagnostics; GUI plan adopts the diagnostics as contract (no invented keys).
- **G-5** â€” WP17 condition: fused-CUDA near-corrected records need a discriminative near-correction-path diagnostic (assembly_path="fused_cuda" alone is ambiguous with WP15); lane note, not GUI work.
- GUI-integration plan itself: P5 W4 `compare --bar` judge still MISSING in cli.py (planned hook, W4 owner-gated); WP6 demo-sheet searches confirmed ABANDONED (owner: 12 kHz capability banked via WP15) â€” the plan does not carry it.

Local-only, added 2026-10-25 (M5 WP11 pass; evidence `docs/evidence/M5_WP11_2026-10-25.md`; nothing flipped â€” all new keys opt-in, absent = bit-for-bit):
- **VRAM per-job baseline/peak MISSING for the first three GPU screens** (ipop/bipop/cma_me): the screen lane ran the jobs correctly (durable run.json artifacts carry their proof) but never started its external VRAM sampler; only the fired-restarts screen has the [measured] pair (baseline 430 MiB / peak 2305 MiB). M4 precedent (peak-per-job disclosed MISSING) applies; re-runs cost ~4 min GPU each on FRESH cache dirs (owner's call).
- **QD atlas browser render not exercised live**: route tests (34/0/0) + reader tests + `node --check` cover the served contract; a one-minute manual GUI check on `runs/20261025T080717Z-screen-fd13a7` (has atlas artifacts) remains owner-side.
- **`tools/launch_gui.ps1` â€” untracked stray predating this pass** (present in the tree before the first WP11 lane): NOT committed, NOT deleted; owner decides commit/delete/leave.
- **`qd` extra transitive weight**: `ribs==0.12.0` pulls numba/pandas/scikit-learn â€” confined to the optional `qd` extra; noted at Oracle review (exact pin justified: archive semantics are version-sensitive).
- **BIPOP schedule divergences from pycma documented in `_RestartSchedule` docstring** (small-run maxiter cap omitted â€” the global eval budget governs; our `max` counts all restarts incl. small ones, pycma's counts non-small only): behavior deliberate, next reader diffing against pycma should read the docstring first.
- Resume determinism caveat (inherited, not regressed): `solve_failed` rows are never memoised â†’ a resume after a solver-unhealthy abort re-solves them and may legitimately diverge from the uninterrupted replay (docstring caveat per Oracle; behavior unchanged from cma.py).

Local-only, added 2026-10-25 (M4 pass; evidence `docs/evidence/M4_SMOKE_2026-10-25.md`; Proposals owner-gated â€” nothing flipped): 
- **P-M4-1** â€” matched-sampling GRID-vs-FREEFORM equality run before the strict WP10-step-5 J-equivalence claim: the zero-modulation compare (grid_ellipse 1298 dofs vs conical 1319 dofs) is between two DIFFERENT design hashes (`d0dc9b5a8999` vs `f8b94e104f80` â€” same yaml seed, different surface authorings); measured deltas â‰¤ 0.110 dB on-axis / â‰¤ 3.45Â° bw / â‰¤ 0.071 dB DI; construction-level equality is proven offline (closed forms â‰¤ 1e-9); the run-level equality needs GRID n_phi/n_s matched to the FREEFORM mesher segmentation (owner-gated).
- **P-M4-2** â€” rows-route `stop_deg` bounds [120, 240] include graded-infeasible stops near the Salmon 180Â° cap-area asymptote (the march refuses 180Â°; seeds hand-tuned to avoid the zone; lecleach_f90 feasibility sweep: 57/224 knob combos graded `_generator_error`). Consider narrowing (owner gate).
- **P-M4-3** â€” legacy internal rows kinds (`lecleach_mod`, `lecleach_ar`, plain-lecleach `g_r_lip_mm`) remain in `design/generators/grid.py` unlisted/unconfigured (the shipped contract is the list-harmonic kinds + iwata_ar/toroidal_rollback); a cleanup pass may delete them.
- GRID-route mesh-cache absence (documented `mesh/grid_build.py`): every GRID/rows evaluation re-meshes (screen-size meshes are 0.2â€“1.2 s â€” acceptable for smokes, real for searches); a cache keyed on the design recipe + mesh hash is the follow-up if GRID enters search campaigns.
- GRID STEP export unwired (`export_step` â†’ `families.to_mesher_config` KeyError on a grid design; contained per-design by the CLI catch; failure = clean "FAILED: KeyError" line); SHOULD: a clean refusal raising `GeometryInvalidError` instead.
- GUI `list_configs` latency: the data-driven disabled gate materializes every config's seed per refresh (rows marches are brentq loops â€” saddle ~25 rows); memoize on (path, mtime) + pin the gate with a test.
- salmon_saddle emits the mesher outer-shell clearance warning (wants 3.866 mm on 6 of 33 rings, holding at 5.197 mm) â€” inner acoustic surface unaffected; seed uses epw 6 to fit the 5,000 screen cap.
- Final offline suite 1194/0/1/0 â€” the single failure is the intended `tests/test_mesh_pin` tripwire (installed beat-bem fork `fa99ee594087` vs main pin `38544d214ba2`); +226 tests additive-only; never hand-fixed (resolves when the owner hosts the fork pin, docs/FORKS.md).

Local-only, added 2026-10-24 (GUI contrast/visibility pass, docs-only): the local web GUI's rendered dark-theme state fails WCAG in spots â€” primary button text 2.07:1 on `--accent`, hairlines 1.36:1, chart micro-labels dim, `wallSection` "filled" legend a no-op (fill â‰¡ plot bg, dashed start profile ~90 % occluded), 3D horn shadow side merges into the canvas, isobar white contours lost on warm bands, budget-over-limit unflagged, theme-toggle first-click no-op + stale SVG after toggle. Full measured list + six-phase fix plan (tokens, theme boot + `?theme=` capture, charts, wallSection, 3D light-gray horn + lighting/shadows, semantics/tests): `docs/GUI_CONTRAST_PLAN.md` (designer-authored, Oracle-reviewed â€” all MUST/SHOULD/NICE applied). Owner approved implementation 2026-10-24: Phase 1 (tokens/type tiers) landed + verified (`tests/test_gui.py` 30/30; both dark CSS blocks in sync); Phase 2 (theme-boot first-click fix + `?theme=` capture override + async route/scroll/filter restore on toggle) landed + verified (30/30; both themes pixel-checked via the override); Phase 3 (chart contrast: two-pass isobar halo contours, brighter dots/hlines, `--label` target lines + legend swatches, seed strokes 1.7) landed + verified (30/30); Phase 4 (wallSection redesign: even-odd wall-band fill, dashed-start last, throat dots, plain labels) + Phase 5 (3D light-grey horn, 4-light rig, themed canvas, toggleable shadows + light-tone wireframe retained per owner) landed + pixel-verified in both themes. Phase 6 (over-budget flag + literal text at all three readouts, rank/leader/noise text badges, timeline-dot shape+color redundancy, `evolution.js` in the syntax gate) landed + verified (`tests/test_gui.py` 31/31). ALL SIX PLAN PHASES IMPLEMENTED 2026-10-24. Unrelated observed failure: `test_mesh_pin` fails on the WP15 fork lane's in-flight install (hornlab-beat-bem `fa99ee594087` vs pinned `38544d214ba2`) â€” outside GUI scope, that lane to reconcile per FORKS.md. No GitHub issue opened.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

Local-only, added 2026-10-13 (local GPU box, data digest): `osse_baseline` bound-pinning follow-up â€” **corrected per senior review** â€” the best designs sit at the LOWER bound of `n` (2.0; top-6 6/6 â€” the strong signal), while `q` is attracted to its lower bound (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but is top-6 0/6 (an earlier "5/6" here was the in-flight 13:40 snapshot, not final data); `a_deg`/`exponent` are interior. The mesher only needs `n > 0`, `q > 0` while `s != 0`, so a future widening of `n`/`q` is indicated (CP-8b handled `a_deg`/`exponent` only). Evidence: `docs/evidence/CP-8c_data_summary.md`.

Local-only, added 2026-10-13 (local GPU box): CP-8 evidence lives in `docs/evidence/` â€” verbatim checkpoint output (`CP-8a.md`, `CP-8b.md`, `CP-8c_*.md`), live monitor logs (`logs/`), and `manifest.sha256` (SHA-256 + size of the metadata-layer artifacts (run books/ndjson/store JSONLs; label .npz covered by dataset verify, not bit-identity)). Raw `dataset/`, `runs/`, `cache/` stay local and gitignored by design (dataset already 180.6 MB at 1128 records; CP-5 projects 0.78-1.4 GB at 10k) â€” verify against the manifest instead of committing blobs; use a data branch/release asset to move raw data.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): CP-8a PASS (480 offline + 18 GPU-marked tests, doctor 10/10, outputs pasted); CP-8b PASS (bounds widened a_deg 25->5 / exponent 2->1, rerun no longer pinned); CP-8c CLOSED - PARTIAL on the literal criterion, verify OK: four runs done - osse_baseline 1500 (best J 6.106 vs seed 22.592, -73%), icw_termination 800 (12.201 vs 55.736, -78%), freeform_hv 722/800 on cma: tolfun (30.543 vs 33.309, -8.3%, low-diversity plateau, 3 searchable keys), throat_adapter 400/400 with ZERO failures (5.983 vs 9.159, -35%); final dataset 3556 records / 8 shards / 587.2 MB, dataset verify OK (0 bad, 0 bad arrays); families OSSE 2034 + ICW 800 + FREEFORM 722 = 3 of 4 (R-OSSE has no example config; the literal all-four-families criterion is unsatisfiable - amended criterion in evidence). Campaign wall ~14.9 h, GPU solve 13.0 h. CP-8d next (indicative): OSSE pool kept 1501 of 1634 -> held-out 225 < 500 -> expect GATES REFUSED (indicative only); propose runs with --allow-unvalidated. **CP-8d OUTCOME (2026-10-14 ~01:10 local): FAILED â€” GATES FAILED twice** (epochs 300: topk 5/20 + bw_mae 2.110 fail; epochs 600: 5/6 gates pass incl. Spearman 0.9861 / topk 15 / bw 1.704 / di 0.232 / inv 0.952, but monotonic_flips 1 (needs 0)); held-out 285 < 500; model NOT used (propose/round not run); hard rule 8 stop + NOTES_FOR_SENIOR `2026-10-14 cp-8d` block (questions: approve ~10.2 h OSSE top-up to clear the 500 floor; classify monotonic_flips=1). Tables: `docs/evidence/CP-8d.md`. **Flip diagnosis (addendum)**: seed-stable 2-4 % flip rate (seeds 0-5: flips 1/1/1/2/2/2 of 50); three causes â€” invalid-transition degeneracy, genuine 1-3.7 J undulation on fully-valid lines, and flat-tolerance wiggle sensitivity (tol 0.021-0.023 J); marginal, not a hard defect; NOTES cp-8d ADDENDUM wants owner rulings on sweep-tolerance semantics / invalid-crossing category (thresholds untouched).

Local-only, added 2026-10-13 (local GPU box, icw run): (a) ICW mesher warning "outer wall self-intersects / normal flip near azimuth row 0" â€” 24 warning LINES, all timestamped 17:06:25, plausibly ONE design of 800 (per-design attribution not recorded); zero new after 17:06; rows still validate and the acoustic (inner) surface is unaffected â€” caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. (b) ICW bound-pinning follow-up: best designs fully pinned at the `hold_end` LOWER bound (0.55, top-6 6/6) and 4/6 near `kappa0` lo = 0.0 (median 0.0016); candidate `hold_end` widening subject to the repo's `hold_start < hold_end` rule + mesher validation. (c) OSSE bound-pinning follow-up from run 1 â€” **corrected per senior review**: `n` fully pinned at lo 2.0 (top-6 6/6; the strong signal); `q` strongly attracted to lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but top-6 0/6 (an earlier "5/6" was a stale in-flight snapshot); mesher needs only `n>0, q>0` while `sâ‰ 0`. Both (b)/(c) recorded, NOT changed mid-campaign.

Local-only, added 2026-10-22 (local merge lane, glm-5.3 oracle pre-merge review): follow-ups recorded, none blocking the merge â€”
(a) `cli.py::_cmd_compare` would raise an uncaught `IndexError` (`ma.freqs_hz[0]`) on the unrealistic empty-frequency-set edge (cosmetic traceback risk only);
(b) the `exponent` alias resolves to the FIRST superellipse station only â€” pre-existing design-layer semantics; document in config-template comments before any future multi-station FREEFORM config;
(c) `docs/BOUNDARY_LAB_*` + `docs/research/boundary_lab_0.5/` are PROPOSED research awaiting user approval â€” do not treat as accepted backlog.

Local-only, added 2026-10-22 (local merge lane, user request): GPU-run summary layer committed at `docs/evidence/runs/` â€” for each of the 7 local `beat_cuda` run dirs (seed screen d627d9, resume smoke 7e6e5b, CP-8b smoke 9e5a5c, CP-8c runs 1-4 ca15be/6bdcbd/ff569c/852be3), the summarized metadata+log layer (run.json, config.yaml, best.json, search.ndjson, cma/*, verify; 108 files, ~16.6 MB) is now IN GIT (previously only in gitignored `runs/`), with index README + `runs/manifest.sha256`. Raw `designs/` blobs, `dataset/`, `cache/` remain gitignored by design; this is an approved exception to the evidence-README "never the data itself" rule (noted in `docs/evidence/runs/README.md`).

Local-only, added 2026-10-13 (senior read-only review of CP-8c/CP-8d readiness, glm-5.3 oracle, branch claude/wave-3-implementation-review-2dk4qe):

**(a) CP-8c yields THREE families, not four** â€” `examples/throat_adapter.yaml` is `family: OSSE`,
so after run 4 the store holds OSSE+ICW+FREEFORM and R-OSSE stays 0. HANDOFF_LOCAL Â§5's pass
criterion ("all four families present") is unsatisfiable as planned, and `stats()`'s family
warning (fires only when one family >80%) will never flag a MISSING family (OSSE â‰ˆ56% after
run 4). Fix: re-scope the criterion to "OSSE+ICW+FREEFORM present; R-OSSE deliberately absent
(no example config)"; add `missing_families` to `dataset stats` (store.py:441-446, 658).

**(b) CP-8d misreading guards (14-item list in the review)** â€” (1) CLI must distinguish
"GATES REFUSED (indicative only): held-out 225 < 500" from "GATES FAILED" (cli.py:675 vs
gates.py:115); (2) `round_report`'s `random_true_J` = CMA gen-0 samples, not random, and J=1000
penalty rows inflate medians â€” pass solved rows only and print the baseline provenance
(ismo.py:56-72); (3) print exploit vs explore medians separately; (4) print the proposals'
parameter spread (the 30 exploits are near-clones of one basin); (5) freeze `pred_J` from
proposals.json and record bundle/config_sha/store count at train; (6) write `ismo_round1.json`
into a run dir and paste it into a new `docs/evidence/CP-8d.md`. Items overlapping #13
(skipped-count printing, verdict persistence, dedupe-by-hash before the holdout split) LANDED
in commit e0b9b61 â€” none of CP-8d's numbers are quoted before that.

**(c) Data-pipeline integrity at 10k â€” IMPLEMENTED (commit 11304f6; full offline suite 498 PASS)** â€”
`verify_store` now checks metric array shapes vs each record's own `solve.freqs_hz` (reported as
`bad_arrays`; `dataset verify` exits 1 on `bad` OR `bad_arrays`); `dataset stats` gained
`n_duplicate_designs` + a `missing families` line in `stats_report` (R-OSSE expected); `search
--resume` compares `run.json["config_sha"]` and REFUSES on mismatch unless `--allow-config-change`;
`surrogate train` splits `GATES FAILED: <names>` from `GATES REFUSED (indicative only): held-out
<X> < 500`; new `surrogate round` subcommand solves proposals through the normal `evaluate` path
into a fresh run dir with its own ndjson and writes atomic `ismo_round1.json` (report + rows +
`random_true_J` provenance + exploit/explore medians + exploit spread + store counts + bundle gate
status + config_sha). `manifest.sha256` README reworded (metadata layer only) and line 3 indent
fixed for `sha256sum -c`.

**(d) Evidence corrections** â€” CP-8c_osse_baseline.md "5/6 near q lo" contradicted its own table
(fixed: top-6 0/0, median 0.9033 â€” stale snapshot claim); the 13:11 snapshot's "seed J 22.07" was
the smoke seed (fixed: 22.592); ICW warning "~a few % of designs" unsupported (fixed: 24 lines,
one timestamp, plausibly one design of 800); `data_summary.json` `generated_local` lacks a
timezone (add `generated_utc`).

CP-9a..d (cloud GPU pod proof, cap study, campaign, train/gate; see `docs/CLOUD_GPU_REPORT.md` section 6): proposed, awaiting user decisions on provider and spend cap; no GitHub issue yet.

CP-10a..d (high-frequency options, 12 kHz; see `docs/HIGH_FREQUENCY_OPTIONS.md` section 6): proposed, none run; CP-10d needs the user to approve contacting Collin.

Added 2026-10-14 (cloud): **#13 fixes F1-F6 ready on `ccr-455d2184-yj5zk4` (draft PR #14). Merge into this branch AFTER CP-8c, BEFORE CP-8d.** #13 stays open until then.
**[SUPERSEDED locally, 2026-10-13 ~23:00: the SAME issue-#13 fixes are already on this branch â€” local commits e0b9b61 (8 items) + 11304f6 (store/CLI follow-ups), full offline suite WITH the mesher: 498 PASS / 0 failures. Do NOT merge PR #14 on top â€” that would double-apply overlapping changes in `surrogate/**`. Cloud owner: diff e0b9b61+11304f6 against PR #14 and adopt ONE set. CP-8d proceeds on this branch's fixed code either way; `propose` here refuses unvalidated bundles by default with `--allow-unvalidated` for the runbook's indicative round.]**

Added 2026-10-14 ~05:00 UTC (cloud): PR #14 REBUILT on `622776a` â€” local issue-#13 set (e0b9b61/11304f6) adopted, cloud duplicates dropped; adds FREEFORM sculpt config, FREEFORM training-export fix (dotted keys were NaN), `compare`, DI-provenance guard, NaN refusal, FREEFORM throat radius. Merge, then HANDOFF section 6b. Open, no GitHub issue: FREEFORM full-vs-quarter GPU check + bar ruling; mesher wall-port feature request; HornLab author naming (user to confirm).

Added 2026-10-21 (cloud): Boundary Lab 0.5.0 integration PROPOSED (`docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`; research `docs/BOUNDARY_LAB_0.5_RESEARCH.md`). No GitHub issue yet; open decisions: phase order A->B->C, ownership rows, BL env on the GPU box, contacting JW Sound / HornLab author.

Added 2026-10-22 (cloud): senior architecture report `docs/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md` (Boundary Lab: sidechain, plugin parked; priority and to-do list). On `main` (`2311f92` + this commit).

Local-only, added 2026-10-22 (local GPU box, HANDOFF 6b): FREEFORM quarter-vs-full symmetry check PASSED (max 0.0043 dB, beamwidth 0.051 deg; bar 0.1 dB / 1 deg, not frozen - owner may freeze it); `freeform_sculpt` 60-eval search 0 failures, J 30.945 -> 24.213. Follow-ups (non-blocking): (1) `compare` header prints `quadrants None` for both runs although they solved 451 vs 1636 dofs (reads the wrong field; cosmetic); (2) dry-run throughput estimate 2 s/candidate vs measured 6.7 s for `freeform_sculpt` (TOOLCHAIN M3 extrapolation under-predicts; affects budget planning only); (3) watch `profileH.mouthAngleDeg` (2/6 at hi 70) and `profileV.points.3.1` (2/6 at lo 108) on any longer sculpt run before widening. CP-8d must not be re-run before the OSSE top-up (CONTINUITY Next action corrected). Evidence `docs/evidence/HANDOFF_6b.md`.

Local-only, added 2026-10-22 ~11:40 (local GPU box): follow-up (1) `compare` quadrants label FIXED (regression test). New `export-step` CLI (senior report s3 item 4) DONE. Sculpt budget 400: J 30.945 -> 16.789, **3 wall anchors PINNED** (`profileH/V.points.3.1` at lo, `profileV.points.4.1` at hi) - the disjoint per-anchor radius boxes now bind; options for the owner: widen/overlap the boxes with a mesher monotonicity check, or reparametrise as positive increments. Bound-limited families awaiting a widening decision: OSSE `n` (6/6 lo), ICW `hold_end` (6/6 lo) + `kappa0` (4/6 lo), throat_adapter `throat_ext_angle_deg`/`k` (6/6 hi) + `a0_deg` (6/6 lo), FREEFORM sculpt anchors above. No widening done (user OK required).

Added 2026-10-22 PM (cloud): Boundary Lab learnings implemented (`docs/BL_LEARNINGS_IMPLEMENTATION.md`): pre-solve topology + symmetry-domain checks, `solve/phasor.py`, runtime provenance, report-only SPDI / beam shape. 

**NEXT DEVELOPMENT ROUND, TOP PRIORITY (user decision 2026-10-22): read `docs/NEXT_DEV_PRIORITIES.md`.**
- [ ] **P1 Fused / direct CUDA Burton-Miller assembly** in the exterior driver (post-beta; Magnus's OK or a pinned fork). Fused path is CPU/Metal only (`hornlab_beat_bem/julia/BeatEngineDriver.jl` ~l.1215); the CUDA single-matrix assembler `assemble_burton_miller_neumann_system_cuda` (`julia/src/BeatEngineCudaBurtonMiller.jl:350`) is called only by `runtests.jl`. Engine work, not a flag flip. Expected: 8 GB ceiling ~9k -> ~20k quarter dofs (~12.6 kHz at epw 6 on the large OSSE seed) [inferred]. Validate with selftest --analytic, --crosscheck (< 0.2 dB) and an A/B vs today's CUDA path before any data counts. NOT enabled for the 2026-10-22/23 overnight queue (one solver for the compare tier and surrogate top-up).
- [x] **P2 12 kHz finalist verify pass on the 4060**: DONE 2026-10-23 (see the item below and `docs/evidence/HF12K_VERIFY_2026-10-23.md`).
- [ ] **P3 `beat_metal` backend** for the collaborator's Apple Silicon MacBook (fused path on, unified memory); Mac selftests + 3-design A/B vs the 4060 before mixing data.

TO-DO (no GitHub issue yet; owner / plan ref):
- [x] Merge the learnings PR, run its section-4 test plan on the GPU box: DONE 2026-10-22 (FF to 265133f; `docs/evidence/BL_LEARNINGS_GPU.md`).
- [x] Early rejection offline replay: DONE 2026-10-22 (`docs/evidence/EARLY_REJECTION_REPLAY.md`): < 0.1 % GPU saved at K = 4 / 25 % margin, no top-20 lost; recommend NOT implementing as specified (owner ruling).
- [x] (closed 2026-10-23 by the failure cache) Search budget counts uncached failures: a re-run with the same CMA seed replays cached successes for free but re-evaluates every earlier failure, which consumes budget without solving (OSSE budget 40 -> 0 new solves, 2026-10-22). Options for the owner: cache failures by design hash, or count only solver-reaching evaluations (task 08; `search/cma.py`).
- [ ] CPU-vs-CUDA qualification screen per pinned-library change (GPU box; frozen CP-7b rule; s2 item 8). Note: beat_cuda vs bempp_cpu re-run 2026-10-22: 0.039 dB (`docs/evidence/SOLVER_VERIFY_2026-10-22.md`).
- [x] Typology plan v2 implemented 2026-10-22 (generators, hybrids, briefs, `families`/`campaign`, failure cache, loading metrics). GPU checks V4/V5/V7 in progress.
- [ ] Le ClÃ©ac'h / spherical-wave generator DISABLED (R9): implement only from a verifiable published construction (ETF 2010 lecture PDF too large to fetch, diyaudio thread 403, sphericalhorns.net calculator disclaims fidelity to JMLC). Needs a human-supplied reference.
- [ ] Brief `source.cap: auto` not applied: FREEFORM keys in `families.py` do not expose the mesher's source-cap radius/auto-angle; every design uses the mesher default cap (consistent within a campaign). Add the keys (task 04) and tie to the brief.
- [ ] Generated horns use a 3 mm outer shell (mesher FREEFORM curvature guard); Magnus-family configs use the mesher default shell. Outer-shell thickness differs between the two groups; small acoustic effect at the mouth rim, recorded per design.
- [ ] `search_smoke` (legacy) cannot be dry-run under a 5.5 kHz brief (seed exceeds its dof cap); harmless, legacy only.
- [x] `search --brief/--cma-seed` were silently ignored (fixed 2026-10-22; first campaign's native-family entries invalid and re-run).
- [x] Campaign fairness: cached replays gave native configs 6-15x more search; `--max-evals` caps all evaluations (fixed 2026-10-22).
- [x] Hygiene left BEAT `worker_host` processes (which respawn julia) alive; now cleared with their julia children (fixed 2026-10-22).
- [ ] `perturbed_osse_hv`: 36 % invalid in the screen run and `L_mm` pinned; revisit its bounds/u_max before a compare run (widening needs user OK).
- [x] Brief size envelope now enforced for every family (outer mesh bbox); native configs sized for other targets (osse_baseline, freeform_sculpt under the 400x300 brief) have no valid design and are labelled so in the leaderboard. Beta users: use typology configs or size a native config for the brief.
- [ ] Mesher upstream 4573bc90 is 57 commits past our pin b922e807 (FREEFORM corner topology `d740c28`, `68ed646`, joins `967db56`; ATH import; new geometry keys). Signatures and the 0.4 curvature guard unchanged. Owner 2026-10-22: keep the pin for the beta; post-beta bump candidate with its own verification ladder.
- [x] R8 brief provenance: dataset records carry optional `provenance` {config, brief, brief_hash, generator} (2026-10-22).
- [x] C2 epw 6 vs 8: axi seed DI 0.124 dB > 0.1 -> axi typologies at epw 8 (owner); H/V within 0.05 dB stays epw 6.
- [x] GPU lock + `gpu-clean` (2026-10-22); overnight queue + watchdog in `tools/overnight/`.
- [x] GPU lock liveness on Windows: `os.kill(pid, 0)` made a live holder in another console look stale (takeover / gpu-clean would hit a running solve). Fixed 2026-10-23 with OpenProcess/GetExitCodeProcess + tests.
- [ ] OSSE `exponent` presses its upper bound (7.9 of 8) in the 2026-10-23 top-up (seen in the time-lapse): bound decision for the owner, like the other pinned bounds.
- [x] **Search does not recover a dead BEAT worker host** (2026-10-23; FIXED 2026-10-23 ~14:30, offline-tested: root cause = `hornlab_beat_bem.worker.get_worker` caches a `HostedBeatWorker` that keeps its dead socket after a send fails, so every later solve wrote to it; `recover_after_failure` now also calls `detach_workers` (drops the cache), `BeatBackend` re-warms and retries a `worker_exit` candidate once, and `search` stops RESUMABLY (status aborted, `SolverUnhealthyError`) after 3 consecutive `solve_failed` instead of ending on `tolflatfitness`; `to_training_arrays` drops `solve_failed` records from labels (`meta.skipped_solve_failed`). Tests `tests/test_solve_beat_recovery.py`, `test_search_cma.py`, `test_dataset_store.py`. The host death itself is still unexplained, GPU rule 7. Original report: OSSE top-up seed 4101 lost its host at 03:58:48 EDT (`ConnectionResetError` 10054, `solve_failed [worker_exit]`); every later candidate failed in ~3 s (21 rows), J went flat at the 1000 penalty and CMA-ES stopped on `tolflatfitness` at 411 of 950 evaluations. Cause of the reset unknown (second unexplained reset tonight; first in the C2 check 21:46, not reproduced from clean, CLAUDE.md GPU rule 7). Fix proposal (task 05/08): on `worker_exit`, re-warm the host once and retry the candidate before scoring a failure; never let a run of solver failures end a search. The 21 `solve_failed` dataset records are failures of the solver, not of the designs (non-deterministic kind, never failure-cached); exclude `solve_failed` from the surrogate's validity labels.
- [x] Local web GUI `hornlab-search gui` (2026-10-23, `docs/GUI_PLAN.md`). Open: macOS untested; 3D view needs the three.js CDN. Launch GPU-busy state now LIVE (polls `/api/status` every ~6 s, toggles note / Start button, toast; 2026-10-23 14:30; the server still re-checks on launch). Senior UX pass done 2026-10-23; typology picker, Typologies page and graphics pass done 2026-10-23 (09:00); search time-lapse player 2026-10-23 (10:40); beta hardening + Boundary Lab-style isobars 2026-10-23 (11:30, d0a04ea).
- [x] Wire `surrogate.features.require_surrogate_config` into `cli._cmd_surrogate`: done 2026-10-23 (merged).
- [x] Beta-readiness pass per `docs/HANDOFF_BETA.md` (F timed rehearsal DONE 2026-10-23 16:30, 8 friction points fixed, `docs/evidence/BETA_READINESS.md` F; G session plan refreshed with measured timings; A-G; A-D done (D3 Ctrl-C PASS on the GPU 2026-10-23 after a campaign fix; D5 paths PASS); E running overnight; F, G pending): upstream audit, R8 brief provenance in dataset records, epw convergence above 2.5 kHz, GPU lock / gpu-clean, rehearsal, session pack.
- [x] `compare` tier (2 CMA seeds) on the leaders: DONE 2026-10-23 (`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`).
- [ ] Bound proposals from the compare tier (osse_axi `h_s`, hypex/exponential `L_mm` lo, perturbed_osse_hv `L_mm`/`v_a_deg`, hybrid `v_rm_mm`): owner decision; NOT applied.
- [ ] rosse_baseline is seed-sensitive (12.3 vs 14.3): more seeds or budget before any ranking claim.
- [x] Failure cache: deterministic failures cached by design+mesh+solve key across runs (fixes the OSSE seed-replay budget burn).
- [ ] Stage 2 transient analysis (impulse, step, CSD waterfall, group delay, dense throat impedance) on finalists: research + design in `docs/research/TIME_DOMAIN_RINGING.md`; needs a dense uniform frequency list per evaluation (today only 12/25/36-point log grids, too sparse: Magnus's `plot_impulse_response` interpolates over resonances). After the typology campaign; not in the search loop.
- [x] R-OSSE: `examples/rosse_baseline.yaml` added 2026-10-22 and run in the hifi screen + compare campaigns (seed-sensitive: 12.3 vs 14.3, see below).
- [ ] ICW rollback termination never exercised (categorical; needs its own config). In the typology plan.
- [ ] `freeform_hv.yaml` solves the full domain although FREEFORM quarter == full within 0.0043 dB (4x dofs wasted). In the typology plan.
- [x] STEP-export CLI: DONE locally 2026-10-22 (`hornlab-search export-step`, b822dd5).
- [x] OSSE data top-up for the surrogate gates: DONE 2026-10-23 (user OK 22:14): seed 4101 411 evals (host death 03:58), seed 4102 951 evals. Retrain + CP-8d gates next (CPU).
- [ ] Boundary Lab BL-1 export (cloud; `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`).
- [x] `compare` IndexError on empty frequency list: fixed 2026-10-23 (merged).
- [x] `verify --brief` was parsed and silently IGNORED (found 2026-10-23 preparing P2; would have re-verified at 5.5 kHz). Fixed: the brief is applied and the results go to their own run dir `runs/<ts>-verify-<id>` (listed by the GUI; `run.json.verify_of`); `verify` without `--brief` unchanged. Test `tests/test_search_verify_brief.py`.
- [ ] Collaborator pulling `main` 2026-10-23 evening: `docs/HANDOFF_COLLABORATOR_2026-10-23.md` (branch + PR; owner merges after the GPU jobs).
- [x] P2 12 kHz finalist verify pass: DONE 2026-10-23 16:07 (`docs/evidence/HF12K_VERIFY_2026-10-23.md`): 14 designs, 0 failures; epw converged at 12 kHz (<= 0.058 dB, <= 0.31 deg); rankings as in the compare tier; peak VRAM 7,360 MiB above baseline at 6,049 dofs (edge of 8 GB). 8-12 kHz compares geometries, not drivers (f11 7,914 Hz).

- [x] Docs index `docs/INDEX.md` and code map `docs/CODE_MAP.md` added 2026-10-22, linked from CLAUDE.md / AGENTS.md / .claude/CLAUDE.md; keep them current.
- [x] Campaign Ctrl-C and host hygiene (2026-10-23): `run_job` killed a Ctrl-C'd child mid clean-up and skipped the leaderboard; a campaign never cleared its Julia/BEAT hosts (snapshots only). Fixed (grace period, partial INTERRUPTED leaderboard, exit 130, hosts cleared after every job); D3 PASS live (`docs/evidence/BETA_READINESS.md` D).
- [ ] Surrogate retrain 2026-10-23 (`docs/evidence/CP-8d_retrain_2026-10-23.md`): GATES FAILED (topk 11/20, invalid_accuracy 0.80, monotonic_flips 4) at 600 epochs; held-out 463 < 500 (indicative). Model NOT used. Owner: ~250 more OSSE records for the floor; flips semantics; why the ranking/validity gates got worse with more data.
- [x] `*_12k` verify-only briefs were accepted by search/run/campaign and offered by Launch (2026-10-23 rehearsal): `verify_only: true` brief key; search/run/campaign refuse (exit 2), Launch hides them; tests in `tests/test_search_verify_brief.py`.
- [ ] Live demo on a shipped brief replays from the cache (~1 min, same CMA seed): use a saved brief copy (5.5 min measured). A `--cma-seed` option for `campaign` would make fresh live runs possible on shipped briefs (owner, task 08).

Local-only, added 2026-10-24 (senior pass): implementation backlog WP1-WP17 in `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` (objective v2, driver pinning, fused CUDA in our fork, 12 kHz screens, GRID shapes, multicell); owner gates: WP13 third-party axisymmetric solver, GitHub hosting of forks, v2 as default.

Local-only, added 2026-10-24 evening (orchestrator, M1 implemented + Oracle-verified; pushed): WP1, WP2, WP3, WP4 (offline parts) and WP15 repo-side plumbing LANDED (see `docs/CONTINUITY.md` 2026-10-24 entry; Oracle verdict GO, all 3 must-fixes in the push commit; 933 offline tests pass, no test loosened).
- [x] WP1 objective v2 + offline re-score: DONE (`docs/evidence/OBJECTIVE_V2_RESCORE.md`; rho 0.989, claims survive, v1 drift 0; v2 stays OPT-IN â€” making it the brief default is an owner decision).
- [x] WP2 driver pins with embedded-brief grandfather: DONE (2 pre-WP2 runs with an embedded 12.7 brief on a 17.78 OSSE config now load byte-for-byte; new `--brief`/`brief_file:` runs enforce; `osse_baseline` is skipped under 1-inch briefs by the campaign compat check).
- [x] WP3 shape-only perturb + pre-mesh `invalid_envelope` + graded penalty (opt-in `search: {infeasible_penalty: graded}`): DONE; all shipped typology seeds estimate 0.0.
- [x] WP4 `freq_weights` (v2-only, v1 warns once) + `verify_points_per_octave` HF verify grid: DONE.
- [x] WP15 repo side (`solve.cuda_fused`, env gating, `assembly_path == "fused_cuda"` proof + refusal): DONE offline; fork branch `hornlab-search/fused-cuda` @ fa99ee5 (Julia tests green). Gpu ladder + ceiling measurement NOT RUN yet (M2; owner: do not pin a file:// URL on main).
- [ ] Oracle non-blocking follow-ups (recorded, none urgent): (1) `invalid_envelope` not failure-memoized (brief-dependent; revisit with a brief-aware marker key in M2); (2) envelope estimator adds full wall thickness radially â€” conservative by ~2.5 mm at 80 deg mouths (documented; no shipped seed affected); (3) dataset record lacks an explicit `objective_version` field (config_sha covers it today â€” add in M2); (4) solve-cache/`ctx.known` reuse keys exclude the objective version â€” never flip objective version on a resume; start a new run; (5) v2 solve-cache hits re-score with the CURRENT weights like v1 (documented behaviour, unchanged by design); (6) `_verify_only_precheck` precedence note for the CLI docs (verify_only wins over a broken config â€” intended); (7) `tools/rescore` duplicates the balloon-collapse block of `metrics_from_response` (drift-0 verified; keep in sync); (8) cosmetic tautology in `test_solve_fused_flag.py` last assert.
- [ ] `tools/launch_gui.ps1` (pre-existing untracked, benign): owner decides; kept out of the M1 commit.
- [ ] Owner decisions queued from M2 onward: fork GitHub hosting + push; v2 default; WP13.

Local-only, added 2026-10-24 late (orchestrator, M2 executed; pushed): WP15 fused CUDA **validated on the GPU** (see `docs/CONTINUITY.md` 2026-10-24 M2 entry; evidence `docs/evidence/FUSED_CUDA_2026-10-24.md`; raw logs gitignored under `runs/m2_fused_cuda/`).
- [x] WP15 install + validation ladder: DONE â€” analytic **0.020 dB** (bar 0.5; = base reference), crosscheck **0.0390 dB** (bar 0.2; = base reference), from clean GPU states.
- [x] WP15 3-arm A/B vs the base pin's stored runs (flag OFF): osse_axi seed `d04e8697a87d`, perturbed_osse_hv best `fed761193da7`, freeform_sculpt seed `892bb3551903` re-solved with FRESH scratch cache dirs (**finding: the solve cache is NOT keyed by lib SHA** â€” stale cache entries would otherwise have silently served old-SHA responses as "A/B") then `hornlab-search compare`: design hashes match; max diffs **â‰¤ 2.9e-6 dB / â‰¤ 2.1e-05 deg** (bars 0.039 dB / 1Â°). This is the step-8 old-path reproduction proof; A/B run dirs confirm `lib_shas.hornlab_beat_bem == fa99ee5â€¦` and `meta.cuda_fused == False`/absent everywhere.
- [x] WP15 fused GPU test: DONE â€” `[measured]` fused-vs-default @ 2 kHz: on-axis max diff **0.0000 dB** (bar 0.01), bw H 76.65â†’76.65 / V 84.18â†’84.18 deg (bar 0.1), z_throat rel **3.35e-07** (rtol 1e-3); the stale-host fused REQUEST (env flipped on a host spawned before it) was REFUSED. **Determinism finding (rule-7 trail):** the test's zero-tolerance bit-identity assertion FAILED on the fork **AND identically on the BASE PIN 38544d2** after a rollback reinstall â€” two identical CUDA requests differ at one Float32 ulp (order-varying reductions; worst observed **1.74e-05 dB**); pre-existing upstream property, not a fork regression. Rebarred to a documented **1e-4 dB** floor with the measured evidence in the docstring + a `[measured]` print (NOTES_FOR_SENIOR 2026-10-24 block); the fused-vs-default bars themselves are untouched; **Oracle adjudicated: rebar PASS (base-pin reproduction decisive; all three measurements now in the docstring; full rulings in CONTINUITY)**.
- [x] WP15 ceiling re-measure (owner capped the sweep â€” no 24k point; the clean-state 20k confirm was interrupted): fused **FITS 15,984 dofs** (peakâˆ’baseline **7,637 MiB**; assembly already memory-pressured at **437 s/freq**); **FAILS 20,237** (BEAT worker-host death on the attempt AND the in-process re-warm retry; peak 7,831 MiB â€” recorded **provisional**, clean-confirm not completed per owner). Old path on the SAME 8,919-dof mesh: **7,389 MiB / 59.6 s** vs fused **2,217 MiB / 9.1 s**. The "~20k inferred" did NOT materialize on this card/protocol. Measured SAFE caps: **verify/final 12,000 dofs** (measured 12,183: 4,744 MiB, 13.72 s/freq). Harness `tools/measure_fused_ceiling.py` (fresh process, threaded external nvidia-smi poll, verified shutdown; `--mesh-only` calibration â€” note: TOOLCHAIN M1's resâ†’dof table was measured on a SMALLER horn: the osse_baseline seed at 3/1.5 mm is 43,993 dofs, so the sweep calibrated mouth-res 6.72/5.74/5.02/4.45 mm).
- [x] `_fusedcuda` configs: DONE â€” 4 NEW files (`osse_baseline`, `osse_axi`, `perturbed_osse_hv`, `freeform_sculpt`), caps 5000/**12000/12000** + `solve.cuda_fused: true`, provenance headers; originals untouched (`git diff -- examples/` empty on the originals).
- [x] 12 kHz verify on the flag: DONE â€” ONE verify job `runs/20261025T013051Z-verify-be4adb`: osse_axi seed via the fused config's run dir + `verify --brief axi_90x90_1in_12k`: verify J **17.0339** (not comparable with screen J â€” different band/grid), **4,438 dofs** / 8,626 tris (below the raised 12,000 cap â€” the epw rule chose the mesh), **52.89 s / 25 freqs â‰ˆ 2.1 s/freq**, response.npz `cuda_fused: True` + **25Ã— `assembly_path: fused_cuda`**; **f11 = 7,914 Hz caveat applies (8â€“12 kHz compares GEOMETRIES, not drivers)**.
- [x] Suite: dev-pin tree = **938 passed / 0 failed / 0 errors / 20 deselected** (junitxml `runs/m2_fused_cuda/suite_dev.xml`, 217.9 s; total collected 958). Main tree (base pin vs installed fork): same selection, exactly 1 failure = `test_mesh_pin` â€” the INTENDED pinned-SHA tripwire until the owner lands a hosted pin (expected state, documented in CONTINUITY + TOOLCHAIN). Selection +3 vs M1's 935 = the new `_fusedcuda` configs in parametrized config sweeps + the concurrently-landed GUI-contrast lane's tests. Nothing loosened.
- [x] Pin policy: `pyproject.toml` + `TOOLCHAIN.md` pin @ `fa99ee5` committed ONLY on **`dev/fused-cuda-pin` (65c03de, LOCAL ONLY â€” not pushed, not merged)**; a file:// pin must never reach main. **Owner asks: host the fork on GitHub + push, then replace the dev pin; then M3 (WP5â€“WP8).**
- Deferred to M3+ for time: M1 follow-up (3) explicit dataset-record `objective_version` field (config_sha covers it today); M1 follow-up (1) `invalid_envelope` memoization (revisit with a brief-aware marker key â€” Oracle: the fix is one line, add brief_hash to the marker's replay-validity; the graded penalty already recomputes on replay so only the stale *verdict* is the hazard). **BOTH DONE in M3 (commit `1dda493`, 2026-10-25): explicit `objective_version` written by every record + absence-tolerant v1 reads; the `invalid_envelope` marker stores + requires `brief_hash` on replay (graded penalty unchanged; test where a different brief re-evaluates).**
- ~~Owner advisory (pre-existing on origin/main): the 2026-10-24 night entries reference `docs/NEXT_DEV_PRIORITIES.md` section "P4", which exists only in the owner's local uncommitted note â€” commit it separately or treat those references as pointing to the local note.~~ **RESOLVED (~00:30 2026-10-25): the P4 note is now committed verbatim** (in the same commit that adds the P5 easy-wins section: W1 rank audit / W2 dense finalist net = P4a scheduled / W3 named screen-grid group, gated / W4 `compare --bar` / W5 freq-weights emphasis); the night references resolve to actual file content now.
- Handoffs issued for the next two passes (2026-10-24 late, owner directive: the shipped demo briefs are NOT their design intent â€” never GPU-search demo sheets): (1) **M3 execution** (full text in chat, owner holds it): carry-over fixes (`objective_version` field; `invalid_envelope` brief_hash marker) + WP5 calibration + WP7/WP8 speed checks on STORED designs, ZERO new searches, ~15â€“20 GPU solves; (2) **brief design** committed as `docs/HANDOFF_BRIEF_DESIGN_2026-10-24.md`: study list â†’ 10-question owner interview (verbatim capture) â†’ real-driver web grounding â†’ 2â€“4 real briefs + baseline settings, offline-validated â†’ GPU = ONLY the owner-approved POC (budget 20 + one fused 12 kHz verify). Sequence: M3 first, then brief design. Band stays 700â€“12,000 (14 kHz+ screens would blow the 5,000 cap and ~2Ã— per-candidate cost above f11 with no realism gain; a screen-cap raise for band_hi > 12,000 is OWNER-GATED). Handoff GROUNDED (same evening): full capability map (Â§2b) of what the later plan lands â€” M3 in flight (carry-overs `1dda493` + WP5 proposals + WP7 rear factor + WP8 band-split), M4 (WP9 generators, WP9b JMLC/Kugelwellen/organic/X T1â€“T7, WP10 GRID Fourier sections, WP12 mounting), M5 (WP11 restarts, WP16 >f11 realism, WP17 near-correction, WP14 multicell CPU-first) â€” plus four forward-compatibility rules for the briefs (landed keys only; stated family-allow-list assumption; variant briefs pre-planned for curl/organic appetite; every future-dependent item marked "awaiting WPxx").

- **OWNER ITEM (agent-tooling, 2026-10-25 early):** THREE opencode project skills landed after Oracle hardening passes â€” `.opencode/skills/hornlab-gpu-job/` (per-GPU-job hygiene/capture recipe; exit-3 + FORKS-tripwire semantics; fresh-measurement + fresh-cache rules), `.opencode/skills/hornlab-evidence/` (evidence assembly + pre-publish byte-check of EVERY quoted block) and `.opencode/skills/hornlab-typology-research/` (the horn-design grounding protocol: sourced dossiers + R9/rename-gate discipline before typology/shape work; AGENTS.md + CLAUDE.md carry the block). Applied on the next opencode run (config-time files). **Owner config decision:** the slim preset gates skills per role (`orchestrator: ["*"]`, but fixer/explorer/librarian/designer/council: `[]`) â€” lane sessions never see the skills; either add the three names to those roles' arrays in `.opencode/oh-my-opencode-slim.json` (one-line each) or keep embedding the ceremony in dispatch prompts.
- **W6 balloon GUI view: LANDED (2026-10-25, ~01:10):** the Balloon 3D view + radar slicer + isobar slice are implemented in the web GUI (own implementation of BL's display grammar; GPL attribution in code; server routes read-only + path-safe; `tests/test_gui_balloon.py` +9; gui tests 44/0; both-theme screenshots under `runs/gui_balloon/`). Ships with today's stored balloon densities (screen 16Ã—32; verify 23Ã—45); the verify-balloon density upgrade stays gated on the M3/WP5 Î”DI ladder (W7 in NEXT_DEV_PRIORITIES).

Local-only, added 2026-10-24 night (user request, docs-only; full write-up: `docs/NEXT_DEV_PRIORITIES.md` section "P4"):
- [ ] **Narrow-resonance blind spot + dense finalist check (P4a, idea)**: the screen grid is 12 log-spaced points
  (500 Hzâ€“~5.5 kHz), verify 25 points â€” a horn defect narrower than the ~1/3-octave gap (mouth-reflection
  resonance, organ-pipe mode, narrow cancellation) can fall entirely between solved frequencies; nothing is
  simulated between grid points, interpolated plots render smoothly over the defect, and the objective cannot
  score it, so a peaky horn can outrank a clean one. Proposed safety net: re-solve the FINALIST shortlist only on
  a dense uniform in-band grid (24â€“48 points or the WP4 8/octave pattern over the whole band) and diff vs sparse
  metrics; auto-flag families whose dense J degrades. No contract change needed; cheap (a handful of designs).
- [ ] **Perceptually weighted non-uniform frequency grid (P4b, idea; FROZEN-CONTRACT matter)**: extra solved
  points at hearing-critical/problematic regions (~2â€“3 kHz, ~4â€“5.5 kHz, possibly the 0.5â€“1 kHz mouth-reflection
  onset) instead of even log spacing. Requires an owner-approved amendment of the frozen 01_CONTRACTS Â§8 grid
  (2026-10-13 ruling declined per-user YAML grid keys; a changed grid changes the solve hash and cannot train/
  cache with existing grids) â€” must be a NEW NAMED grid group with the point list fixed in the contract (the
  `*_12k` brief / WP4 `verify_hf` pattern), not a free-form key. Related: WP4's `verify_points_per_octave`
  (verify-only, >5 kHz) and v2 `freq_weights` (reweights solved points only) already landed.

Local-only, added 2026-10-25 (orchestrator, M3 executed; pushed): carry-overs + WP5/WP7/WP8 calibration on EXISTING stored designs, ZERO new searches (owner directive). Evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (17 GPU jobs, 728 s GPU wall, no crash/OOM); harness `tools/m3_measurement_pack.py`. Oracle verdict GO-with-fixes â€” ALL applied (MUST: `rear_res_factor` also keys the solve cache/failure markers/resume memo via solve-spec `extra`; the evidence doc's counter wording fixed; SHOULD: Â§5.1 Band-2-dofs + seam-walls honesty notes, row-echo pinned by tests; NICE: a failed seam solve is recorded in `meta["seam_check"][edge]["error"]`, pre-M3 marker backcompat docstring).
- [x] M3 carry-overs: dataset-record explicit `objective_version` field + `invalid_envelope` brief_hash-scoped failure marker (commit `1dda493`; 6 tests) â€” DONE.
- [x] M3 framework keys (opt-in, absent = byte-identical config/mesh/solve hashes, tested): `solve.source_motion`, `mesh.rear_res_factor` (rear-only scale; READ-FIRST honored â€” MeshDensity `rear_res_mm` drives ONLY outer shell + rear cap), `mesh.band_split {edges_hz}` + `stack_responses` (exact tiling) + verify-only seam check + `mesh_policy: band_split_v1` provenance â€” DONE (24 tests).
- [ ] **Owner-gated PROPOSALS (nothing adopted, no default flipped):** (1) `distance_m: 10` for v2 briefs â€” 2â†’50 m |Î”bw| > 1Â° in-band on ALL THREE finalists; max |Î”DI| 2â†’50: AXI 1.61 / HV 0.59 / RO 0.54 dB (residual 2â†’10 m up to 8.66Â°/0.86 dB â€” better, not converged); (2) raise the screen balloon 512 â†’ 1024 â€” max |Î”DI| 0.1545 dB (AXI @ 7,567 Hz) / 0.1110 (HV @ 12 kHz), fires 2/3 (1035â†’2592 â‰¤ 0.0407); (3) `mesh.rear_res_factor: 2.0` â€” AXI screen dofs 1,397 â†’ 1,060 (**âˆ’24.1 %**), J âˆ’0.00697, top-5.5 kHz CP-7f bars all pass (1.5 also passes, âˆ’18.8 %; 3.0 unmeasured); (4) `source_motion: axial` measured only (AXI/HV â‰¤ 0.007Â°; RO up to 0.4331Â° bw @ 12 kHz, above the f11 = 7,914 Hz caveat) â€” no proposal mechanism, default stays "normal".
- [ ] **WP8 band-split verdict: FAILS the CP-7f acceptance gate on BOTH designs** (in-band maxima AXI 1.2476Â°/1.2166Â°/0.1529 dB/0.4218 dB raw on-axis, HV 1.0957Â°/0.9259Â°/0.1021/0.4041; failure concentrated in band 0, band 2 bit-identical to the single mesh; seam deltas âˆ’0.237/âˆ’0.111 dB AXI, âˆ’0.271/âˆ’0.043 dB HV in `meta["seam_check"]`) despite measured walls **âˆ’53.5 %** (AXI, 29.64 vs 63.68 s) / **âˆ’28.2 %** (HV, 33.82 vs 47.08 s) vs the same-code single-mesh solve. Machinery + provenance landed opt-in only; the band-0 fidelity issue must be addressed before any adoption (owner decision).
- [ ] Suites at the final state: focused post-fix subset 68/0/0/0 (`runs/m3_code/suite_oracle_fixes.xml`), full offline **968 tests / 1 failure (= the expected `test_mesh_pin` tripwire) / 0 errors / 0 skipped** (`runs/m3_code/suite_final.xml`); compileall clean.

Local-only, added 2026-10-25 (orchestrator, M3 executed; pushed): carry-overs + WP5/WP7/WP8 calibration on EXISTING stored designs, ZERO new searches (owner directive; WP6 cut). Evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (17 GPU jobs / 728 s GPU wall, no crash, no OOM, verbatim logs, MISSING cells disclosed); harness `tools/m3_measurement_pack.py`; raw logs gitignored under `runs/m3_wp5a|wp5b|wp5c|wp7|wp8/`. Oracle verdict **GO-with-fixes â€” ALL applied** (MUST-1: `rear_res_factor` also keys the solve cache/failure markers/resume memo via solve-spec `extra`; MUST-2: the evidence doc's stale "no junitxml counters" claim replaced with the real suite files/counters; SHOULD: Â§5.1 Band-2-dofs ambiguity closed + seam-inclusive-walls honesty note + row-echo pinned by tests; NICE: a failed seam solve records `{"error": ...}` in `meta["seam_check"]`, pre-M3-marker backcompat docstring).
- [x] M3 carry-overs: explicit dataset-record `objective_version` field + brief_hash-scoped `invalid_envelope` failure marker (commit `1dda493`, 6 offline tests) â€” DONE.
- [x] M3 framework keys (opt-in; ABSENT = byte-identical config/mesh/solve hashes, tested): `solve.source_motion`, `mesh.rear_res_factor`, `mesh.band_split {edges_hz}` + new `stack_responses` (exact-tiling assertions) + verify-ONLY seam check + provenance `mesh_policy: band_split_v1` in ndjson rows + records â€” DONE (24 offline tests).
- [ ] **Owner-gated PROPOSALS from M3 (NOTHING adopted; every flip is the owner's):** (1) `distance_m: 10` for v2 briefs â€” 2â†’50 m |Î”bw| > 1Â° in-band on ALL THREE finalists (max |Î”DI| 1.61/0.59/0.54 dB; residual 2â†’10 m up to 8.66Â°/0.86 dB â€” better, not converged); (2) raise the screen balloon 512 â†’ 1024 â€” max |Î”DI| 0.1545 dB (AXI @ 7,567 Hz) / 0.1110 (HV @ 12 kHz); 1035â†’2592 â‰¤ 0.0407 (fires 2/3); (3) `mesh.rear_res_factor: 2.0` â€” AXI screen dofs 1,397 â†’ 1,060 (**âˆ’24.1 %**), J âˆ’0.00697, top-5.5 kHz bars all pass (1.5: âˆ’18.8 %; 3.0 unmeasured); (4) source_motion axial measured ONLY (AXI/HV â‰¤ 0.007Â°; RO up to 0.4331Â° @ 12 kHz, above the f11 = 7,914 Hz caveat) â€” no proposal mechanism.
- [ ] **WP8 band-split verdict: FAILS the CP-7f acceptance gate on BOTH designs** (in-band maxima AXI 1.2476Â°/1.2166Â°/0.1529 dB/0.4218 dB on-axis; the failure concentrates in band 0; band 2 is bit-identical to the single mesh) despite wall âˆ’53.5 % (AXI, 29.64 vs 63.68 s) / âˆ’28.2 % (HV, 33.82 vs 47.08 s) vs the SAME-CODE single-mesh solve. Machinery + provenance landed opt-in; adoption and any band-0 fidelity fix are owner decisions.
- [ ] Suites at the pass's final state: focused post-fix subset 68 / 0 / 0 / 0 (`runs/m3_code/suite_oracle_fixes.xml`); full offline **968 tests / 0 errors / 1 failure / 0 skipped** â€” the single failure is exactly the expected `tests/test_mesh_pin.py` tripwire (installed fork `fa99ee5` vs main's base pin `38544d2`; clears via the dev pin when the owner hosts) (`runs/m3_code/suite_final.xml`).

Local-only, added 2026-10-25 (docs-only, owner request, follow-through): the P6 research was hardened into a **full implementation plan v1.0** via two parallel web-research lanes â€” `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md` REWRITTEN (dossier folded in). **P6a basis now evidence-grade:** quarter-domain superformula rules (m âˆˆ {4, 8, 12} integer multiple-of-4; m1 = m2 mandatory for quarter meshes [derived]; non-integer m = open curves; the `n1 < 2 âˆ§ max(n2,n3) > 10` degeneracy guard from Symmetry 2022; a/b ratio-only search; canonical Ath reference values quoted incl. User Guide Â§6.4.2; mouth-theory record: no published non-elliptical-mouthâ†’HOM claim, gradual axial shape change is the defensible rule, Dong JASA 2024 enclosure masking; **no public repo searches superformula horn parameters â€” verified GitHub-wide, a genuine first**). **P6b basis:** fixed-budget primary (anytime-slice {100,200,400}), gap-closed normalization, 30 surrogate / 10-15 real-GPU seeds with honest power framing, Wilcoxon rank-sum + Holm + Ã‚12 with ONE pre-registered endpoint; **GSA library audit â†’ own ~120-line module + 8 named tests + 10 pitfall requirements** (no maintained GSA exists: nevergrad/mealpy/pagmo = no, NiaPy = retuned variant, canonical MATLAB port = unlicensed; GSA-NGC = unverifiable, still barred from configs/docs); the crippled-GSA budget trap handled by a mandatory offline N/g0 tuning stage; decision rule D17 pre-registered. Plan structure: work packages WP-P6a-1/2 + WP-P6b-1/2/3 + WP-P6-GUI-1/2 (mouth-outline SVG preview + `#/bakeoff` view) + WP-P6-4 senior pass; FOUR parallel Wave-1 lanes with zero file overlap + verbatim dispatch prompts; checkpoints CP-P6-0..4. **Execution gates unchanged (both required): WP1-WP17 complete + owner GO (P6a/P6b independently runnable).** Still open: the collaborator's "AVE" spelling. No code, configs, tests, or GPU touched; committed and pushed with this commit (owner directive, 2026-10-25).

Added 2026-10-25 (typology-expansion + scoring full-repair pass, CLOSE OF ROUND - see CONTINUITY entry same date):

- [ ] **Open (next handoff): C4 catalog completion** - add the 5 new configs (biradial_keele / qtw_waveguide / salmon_x_signed / salmon_ripple12 / lecleach_asym_odd) + the salmon_saddle_v2 + the iwata_ar-2in + the toroidal JMLC-350 variants to examples/catalog.yaml (the header/fields already document them; lecleach_asym_odd = the NEW symmetry value full, quadrants 1234).
- [ ] **Open: C3 the Tritonia-law rows kind** (the published alpha(theta) power laws over the OS-SE base, amplitudes as genes; fully specified in 12_RESEARCH_BASIS 13.7 - primary pages fetched + verified) + the segmentizing genes (seg-horn eqs 2-4) as the follow-on.
- [ ] **Open: P8b owner decision - the diagonal-consistency objective term** (45/135 vs H/V from the stored balloon; no new solves) - the only scoring change that DIRECTLY rewards the figure-8/puckered class.
- [ ] **Open: GPU smoke matrix** for the 5 new configs (M4 pattern: ONE job machine-wide, runs/.gpu.lock, gpu-clean before/after, fresh cache-dir, external VRAM poll; bytecheck evidence per the m4/m5b template).
- [ ] **Open: Phase D baseline tables** - per-typology K-law default knobs + default briefs carrying target.f0_hz + objective v3 (the landed axi_2in_large.yaml = the template).
- [ ] **Open: GUI hybridization (P8d)** - compose-wizard multi-typology hybrid runs + the seed-gate fixed to the SELECTED brief (gui/data.py:958-969 finding) + feasibility/derived-mouth in the compose preview.
- [ ] **Open: Oracle physics review** of the new typology claims (the house norm for typology code).
- [x] LANDED this round: biradial + qtw_waveguide generator types (R9-sourced) + the splice C1 fix (0.5-deg bar) + signed x_amp v2 + the lecleach_asym odd-cosine full-ring rows kind (mesh-proven on the real adapter) + the even-lobe mouth ripple + the full span + objective v3 (the below-f0 mask + freq-weighted cov) + the K-law feasibility preflight + the brief-derived seed/bounds (clamp-only) + the axi-brief compat refusal + graded penalty on the organic configs + the stale-Le-Cleac'h/docstring catalog fixes + 5 research dossiers + 12_RESEARCH_BASIS 13.1-13.8 + NEXT_DEV_PRIORITIES P8 + NOTES record. Suite 1461/0/0/0 (runs/s1a_suite/suite_final.xml).
- [ ] **Infra: opencode restart needed** - the subagent provider fallback (.opencode/oh-my-opencode-slim.json flipped to ollama-cloud primary after the deepseek outage killed 5 launches with empty results) binds at the next opencode start.

Added 2026-10-25 (ATH framework pass, local-only):
- [x] Native morph_* (incl. morph_exponent, target 3) on OSSE / R-OSSE / ICW / FREEFORM; generator opt-in through the same knobs; absent target = byte-identical.
- [x] `ath_core` (native OSSE, 15 searchable knobs incl. Morph target/exponent/width/height/corner/rate/fixed) + `ath_twinray_380` (published-dimension superellipse reconstruction, 12 knobs); catalog + briefs + catalog/param artifacts.
- [x] First GPU seeds + dry-runs + 1606/0/0/0 offline suite; evidence docs/evidence/ATH_TYPOLOGIES_2026-10-25.md; dossier docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md.
- [ ] Open: exact CORE a(phi) law (needs a rows/generator extension); FREEFORM rectangle morph on an elliptical H/V base trips the mesher non-convex guard (measured); Mesh.Roundover / Ath Rollback / enclosure fidelity; an owner-approved morph campaign.
- [x] Senior review 2026-10-26: morph_target 0..3 guard (R-3) + test; ATH lane committed; suite 1607/0/0/0.
- [ ] Open (campaign 2026-10-26): Phase 0 code fixes (seed_policy explicit, target.f0_v_hz, ICW nested r0 pin, rows span half_xz), campaign briefs/configs, night runner, smoke night - handed off to another agent.

Added 2026-10-26 (campaign Phase 0, implementation lane code-1):
- [x] `generator.seed_policy: explicit`: skips the f0 seed/bounds derivation while keeping the K-law feasibility block; `derive`/absent is byte-identical (config_sha + derived seeds pinned). Validation refuses any other value as `generator.seed_policy`. Directive stripped before materialize/mesher. Tests `tests/test_config_seed_policy.py` (10/10); gate 1626/0/0/0 (`runs/step2a/suite.xml`).
- [ ] Open (this lane next): ICW nested `icw_seed.r0_mm` WP2 driver pin (Step 2C). Other Phase 0 items (target.f0_v_hz, rows span half_xz, campaign configs, night runner) remain with their owning lanes.
- [x] ICW nested driver pin: `icw_seed.r0_mm` is now forced/refused by the same WP2 `_force_pin` rule as root `r0_mm`; new `tests/test_config_icw_driver_pin.py` (4/4); gate 1630/0/0/0 (`runs/step2c/suite.xml`). Remaining Phase 0 items stay with their owning lanes.

Added 2026-10-26 (campaign Phase 0, implementation lane code-2):
- [x] Objective v3 amendment: optional per-plane `target.f0_v_hz` (owner-directed). When set, cov is the sum of the H error over `f >= f0_hz` and the V error over `f >= f0_v_hz` (freq_weights restricted per mask); `dislope` keeps the H/f0 mask. Validation refuses `f0_v_hz < f0_hz` or `> band_hi_hz`, naming `target.f0_v_hz`. Absent = the pre-amendment expression verbatim (config_sha/seed/solve-spec/J goldens pinned bit-identical; dataset/feasibility records emit the key only when set). New `tests/test_objective_v3_f0v.py` (9/9); gate 1639/0/0/0 (`runs/step2b/suite.xml`). `docs/plan/01_CONTRACTS.md` untouched (frozen); dated amendment in CONTINUITY + NOTES_FOR_SENIOR.
- [ ] Open (this lane next): Phase 0 Step 2D (`span: half_xz` rows model for `lecleach_asym_odd`) and Step 2E doc fixes; the GPU half-vs-full equivalence A/B stays Phase B item 5.

- [x] Overnight campaign night runner landed (RUNNER lane files, committed by impl-code2): `tools/run_campaign_night.py` + `tests/test_tools_night_runner.py` (9/9). Sequential one-GPU protocol (julia kill + `gpu-clean` + lock wait + VRAM baseline, per-job timeout/tee, ndjson eval accounting instead of `--budget`, `summary.jsonl` + `SUMMARY.md`, no retries). Gate 1639/0/0/0 (`runs/step2-runner/suite.xml`).

- [x] Phase 0 Step 2D `span: half_xz`: rows span phi 0..180 (ODD n_phi >= 25, upper half across xz, quadrants `'12'`) for `lecleach_asym` (its `cos(phi)` term is even under the up/down mirror; plain `span: half` stays refused). `_GRID_SYMMETRY_AXES` now derives `'12' -> ('y',)` from `sizing.SYMMETRY_PLANE`; `grid_outer_points(half_xz=True)`; mesh/outer-shell call sites updated. Measured CPU: half mirrors the full ring to 1.7e-13 mm, 1,485 tris vs 3,036 (2.04x). New `tests/test_design_generators_grid_halfxz.py` (5/5); param catalog regenerated; gate 1644/0/0/0 (`runs/step2d/suite.xml`).
- [ ] Open: Phase B item 5 GPU half-vs-full A/B (<=0.05 dB / <=1 deg) before switching `lecleach_asym_odd` from `span: full` to `half_xz` in campaign cells. **Backend gap found while landing 2D:** `hornlab_beat_bem` rejects `native_symmetry_plane='xz'` (BEAT mirrors x=0 / x+y only) while `hornlab_bempp_bem` accepts it, so the A/B needs the bempp route or a pinned-fork change; no solver code was changed here. Step 2E doc fixes remain for this lane.

- [x] Phase 0 Step 2E doc fixes: dated correction at the TOP of the S1A verbatim oracle record (the biradial `widened_to_closure` widening is K-law-driven, reached 396.9/352.8 mm, past closure; body unchanged). CONTINUITY records that the scalar `n_in_band` is the COV-SCORED point count (screen 9 / verify 21 for an f0-850 brief), not the band count, and that the field is NOT renamed (stored records + frozen terms key set); with `f0_v_hz` set it is the H-mask count. INDEX/CODE_MAP untouched (no new doc/module). Gate 1644/0/0/0 (`runs/step2e/suite.xml`). No GPU/Julia work.
- [x] GUI discovery 2026-10-26: configs/briefs at any depth, no run cap, auto per-brief leaderboards from run folders, night runner on the Status page.
- [ ] Campaign config lane: b1t__lecleach_iwata_ar.yaml spells a retired product name (neutral-naming test fails) - fix before the smoke night.
- [x] Sandbox 2026-10-26: free/search-limits switch, explore ranges, fixed-knob sliders, Morph card + save-as-search-rows, refused shapes drawn, measured size/envelope, 3D fold tolerance; self-approach chord-vs-arc false refusal fixed.
- [ ] Param catalog generator scans examples/typologies/*.yaml only - campaign subfolder configs get no tooltips until it recurses (sandbox falls back to the config file).
- [x] Ath crease class: OS-SE guiding curve exposed in the sandbox (OSSE); mesher config refusals shown, not 500.
- [ ] Open: native-OSSE TwinRay/CORE typology that searches gcurve_* + Morph (the crease class); per-azimuth a(p) expression knobs.
- [x] README rewrite with GUI screenshots; main fast-forwarded (2026-10-26).
- [x] 2026-10-26 learnings recorded (docs/research/LEARNINGS_2026-10-26.md).


Local-only, added 2026-10-27 (no GitHub issue state changed): objective v4 implemented + two v4 GPU nights (first + resume); open: re-run crease__osse_b1w (resume startup failure), biradial_keele cells refuse ~90 % of candidates, HF data sync tabled (P11), merge of unified-typologies to main.

Local-only, added 2026-10-27 (evening; no GitHub issue state changed): resume night done; ripple/ridge night running (10 jobs); P12 sim-vs-real investigation opened (loading weight 0 on most briefs, ideal source, generous cov) with the SIM_VS_REAL research report; pushed to main.

Local-only, added 2026-11-02 (no GitHub issue state changed): GUI frequency-axis band + scoring-floor f0 marker landed with offline pins (37 tests pass across the three GUI test files); MEH CPU-vs-CUDA benchmark scripts committed under tools/bench/.
Local-only, added 2026-11-02 (no GitHub issue state changed): **P11 HF data sync DONE** - public dataset repo <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> (7 tar shards, 10.77 GB packed: text/solve/dataset; meshes not uploaded), `tools/hf_sync.py` corrected to `hf upload`. Owner-machine finding: Xet uploads stall here; upload with `HF_HUB_DISABLE_XET=1`. Still open in P11: merge to `main` (which branches) and the two v4 re-runs.
# ISSUES

## 2026-11-16 (20:10) - P0 non-CD scoring truth LANDED; P1 awaits owner gates

- DONE: `targets/scoring_view.py` + additive run/campaign/compare/report payloads; web GUI scored-range targets,
  one-sided/mask handling, 8 kHz floor lines, DI level-only-if-scored, display-only slope guide, per-side compare
  targets; report `ref_lines` truth incl. the v2+ Gaussian DI fix; zero J change (objective replay exact).
- OPEN (owner): approve/rework the 12 gates in
  `docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md` §7 (v9 vs opt-in block; corridor strength;
  HF floor origin; diag fate; brief naming). P1 implementation is gated on this decision.
- OPEN (owner, from evidence): score-fairness for non-CD typologies — Crowe ES-600 run `20261115T205453Z-screen-32f7c4`
  was scored on the BASE CD brief (J 16.92, `dislope` 7.40) while the Klangfilm ran on the smooth brief (J 8.92);
  decide the fair same-brief rescore comparison before ranking (docs/evidence/NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md).
- OPEN (local, pre-existing, other lane): `tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_
  or_process_kill_paths` — `study_jobs.py:829` holds `subprocess.Popen` (content from 2026-11-15 commit 6791bfa,
  before this work; belongs to the BO-GUI lane). `test_tools_klangfilm_lame_hv` passes standalone (24/24) and is red
  only under -n 6 xdist load.


Local-only, 2026-11-14 (**scalar Bayesian integration; no GitHub issue state changed**):
- Validation follow-up: live 18+6 pilot completed; 116 study tests and 25 final guard tests pass.
  Broad release: 3840 passed / 19 skipped / 3 failures; targeted reruns fixed polling and passed
  dataset timing, but the unmodified mesh refusal timing guard still measured 104.4 ms against
  100 ms while owner CPU/GPU lanes were active. No tolerance changed; full suite not claimed green.
- Completed: production scalar v4/v7 study worker and GUI actions; canonical task geometry,
  v7 replay/intake, historical-plus-new adaptive training/resume, immutable full pool,
  measured dependency/source pins, journal-owned retries and duplicate-worker protection.
- Measured pilot: 18 screen + 6 verify/audit calls, 24 exact replays, zero unresolved attempts;
  see [integration evidence](evidence/BAYESIAN_STUDY_INTEGRATION_2026-11-14.md).
- Open by design: production Pareto execution, a matched CMA benefit campaign, and automatic
  resolution of genuinely unknown attempts. Scalar adoption remains explicit/opt-in.

Mirror of the GitHub issues at https://github.com/llevaachingada/Hornfab/issues. ID, title, status, owner, plan reference.
Updated in the same commit as `docs/CONTINUITY.md` on every push. Last synced 2026-11-12 (WP9/WP10 chart standards + search history merged; no open issues changed; 349 GUI tests pass).

| ID | Title | Status | Owner | Plan ref |
|---|---|---|---|---|
| #1 | [04] Design space and mesh | closed, CP-2 green | 04 | `docs/plan/04_TASK_DESIGN_MESH.md` |
| #2 | [05] Solve backends and warm worker | closed, CP-3 green | 05 | `docs/plan/05_TASK_SOLVE.md` |
| #3 | [06] Metrics and targets | closed, CP-4 green (3 conventions ruled by senior) | 06 | `docs/plan/06_TASK_METRICS.md` |
| #4 | [07] Dataset record and store | closed, CP-5 green | 07 | `docs/plan/07_TASK_DATASET.md` |
| #5 | [08] Objective, search, report, CLI | closed, CP-6 green (5 items ruled by senior) | 08 | `docs/plan/08_TASK_PIPELINE.md` |
| #6 | [09] Physics checkpoints CP-7a to CP-7f | **closed, CP-7 green** (noise floor 0.039 dB) | 09 | `docs/plan/09_CHECKPOINTS.md` |
| #7 | [Q] Collin: is a Robin/admittance BC planned for BEAT? | closed (answered: bempp-only, later phase) | user | `docs/plan/02_TASK_ENV.md` C3 |
| #8 | [Q] Collin: surface_traces ordering and bempp field recovery | closed (answered by test) | user | `docs/plan/02_TASK_ENV.md` C2b |
| #9 | [Q] Collin: can build_point_grid be public API? | closed (use privately, keep pin + guard test) | user | `docs/plan/02_TASK_ENV.md` C4 |
| #10 | [Q] Collin: confirm BEAT driver excitation on tag 2 | closed (confirmed tag 2 / unit-acceleration) | user | `docs/plan/02_TASK_ENV.md` C5 |
| #11 | [Q] Collin: OK with the hornlab-search name? | closed (keep until objection) | user | `docs/plan/README.md` |
| #13 | hardening-review: Stage A surrogate gate-integrity and real-data traps | **closed 2026-11-12** (fixes had MERGED to main 2026-10-22: FF to 6d1d5c7 carries e0b9b61 + 11304f6 + cloud reconciliation 152a829 verbatim; oracle pre-merge sign-off; full offline suite 533 PASS at the merged tree; closed per day-plan F.4) | phase-2 (cloud) | `docs/plan/11_PHASE2_SURROGATE.md` Â§4 |

Local-only, added 2026-11-06 (**Boundary Lab A/B check on branch `ccr-80a29f93-dxnmdm`; no GitHub issue state changed**):
- **Open (owner + friend, `docs/ab/BOUNDARY_LAB_AB.md`):** first real A/B of one design: `ab-bl demo --fake`, `export`, `solve --dry-run`, `solve --symmetric` on the GPU, friend runs Boundary Lab, `compare`. Plan ref `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md` BL-1 / BL-2 (this is a file-interchange route; no BL code is imported).
- **Open (needs the friend's first run):** the generated `.blab.json` opens in the BL GUI untouched; whether the Acoustic Impedance dock exports text; RMS vs peak pressure (3.01 dB); BL version actually used (source now pins BEAT Engine 0.7.0).
- **Open (ruling):** ownership of the new `hornlab_search/compare/` package and its tests (`tests/test_compare_ab_*.py`); tolerances are starting points pending the first measured agreement.
- **Constraint recorded:** the 8 GB RTX 4060 cannot solve a 20 kHz mesh (`TOOLCHAIN.md` ceilings), so full-band A/B means up to the highest frequency the exported mesh resolves; larger needs the CPU backend or a bigger GPU.

Local-only, added 2026-11-04 (**throughput packet on branch `ccr-80a29f93-dxnmdm`; no GitHub issue state changed**):
- **Open (owner GPU runs, `docs/throughput/RUNBOOK.md`):** baseline throughput matrix (WP0); WP2 prefetch on/off gate
  (real-mesher main-thread behaviour unverified); WP5 batch-size A/B (1/2/4/12, then 41 if safe); WP4 curvature study +
  converged-reference check; WP3 CPU+GPU concurrent pilot.
- **Open (solver fork, not started):** WP1 skip of the unused GPU identity cache on fused CUDA
  (`docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md`, unverified against source lines).
- **Not started:** WP6 multi-source fused CUDA / shared LU; WP7 report-only metric deferral (profile first).

Local-only, added 2026-11-01 (**PR #17 merged to main + the hardware-neutrality rule; no GitHub issue state changed**):
- **Merged (squash):** Metal backend + Mac path, Hansen budget hint, staged A/B harness, CMA
  covariance dump, CMA pin plan, restart controls (jamescollinharky's PR #17). Two merge defects
  fixed before landing: spawn-free `auto_backend()` (Apple Silicon -> Metal, else `None`, never a
  silent CPU swap) and `--backend` applied before config validation (drops `cuda_fused` off CUDA,
  so `config_sha` / snapshot / `run.json.backend` agree).
- **Rule (owner):** results and data must not depend on the solver backend. No silent backend
  swaps; the backend is explicit, hashed into `SolveSpec`, and recorded in `run.json.backend` and
  dataset provenance; cross-backend pooling only after a measured parity check.
- **Owed:** (a) GPU-box staged A/B (`tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`,
  paste COMPARE.md); (b) Mac<->4060 Metal parity <=0.2 dB before Metal enters campaign/compare;
  (c) a cross-backend parity test (one design, CPU vs CUDA vs Metal) behind a marker, plus a
  comparison view that surfaces the backend; (d) move `gui.data.sensitivity` out of the GUI layer
  (`pin-plan` imports it).
- **CI:** unblocked main's red Actions run (a collection error from `tests/test_gui_preview_shape.py`
  when the optional mesher is absent under `--no-deps`). The suite now skips in that environment
  instead of aborting the whole run; a changed mesher pin still fails.
- **CI (part 2):** the remaining ~24 red tests were un-gated optional-dep users (`hornlab_mesher`,
  `hornlab_beat_bem`, `ribs`) plus 3 Windows-only assertions. All gated/fixed; a missing dep now
  skips instead of failing. Re-enable real coverage for those areas by installing the pins in CI
  (or a second job) when that is worth the runner cost.

Local-only, added 2026-10-31 (**staged search A/B protocol + chaining harness; no GitHub issue state changed**):
- **Landed:** `examples/typologies/staged_ab_2026-10-31/` (joint 60 vs A/B/C 20+20+20 on crease__core_law),
  `tools/run_staged_search.py`, `tests/test_tools_staged_search.py`, evidence
  `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`.
- **Synthetic coupled A/B:** staged+polish wins (J 0.100 vs joint 0.302) â€” keep the tools/ harness;
  do **not** change the default `search` path until the GPU acoustic A/B runs on the CUDA box.
- **Owed (GPU box):** `python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`
  (one job at a time); paste COMPARE.md numbers into the evidence doc.
- **Still higher leverage than staging:** objective term normalisation (smoke night); diagonal
  balloon scoring for crease knobs.

Local-only, added 2026-10-31 evening (**CMA pin-plan; no GitHub issue state changed**):
- **Landed:** `pin_from_cma` + `hornlab-search pin-plan` + run-detail Pin plan table
  (recommend-only; optional `--write-config`).

Local-only, added 2026-10-31 evening (**CMA covariance dump; no GitHub issue state changed**):
- **Landed:** `cma_covariance` on `run.json` + run-detail GUI table (ÏƒâˆšCáµ¢áµ¢ shares + eigen loadings).
  Complements Spearman sensitivity; not a Sobol acoustic decomposition.

Local-only, added 2026-10-31 evening (**staged knob schedule in COMPARE/plan; no GitHub issue state changed**):
- **Landed:** `plan.json` / `COMPARE.md` list active vs fixed knobs per staged arm.

Local-only, added 2026-10-31 evening (**Mac .venv + Metal; no GitHub issue state changed**):
- **Landed:** project `.venv` + `[dev,crosscheck]`; Metal ready; dry-runs + budget-5 Metal
  smokes (tractrix / freeform_hv / conical); GUI auto `--backend beat_metal` when CUDA absent.
- **Still owed:** Macâ†”4060 A/B (<0.2 dB) before mixing Metal into CUDA datasets; doctor still
  FAILs the CUDA checks on Mac (expected).

Local-only, added 2026-10-31 evening (**Hansen budget heuristic; no GitHub issue state changed**):
- **Landed:** `search/budget_heuristic.py` + `GET /api/budget-hint`; Launch/Compose suggest
  `max(150, 100Â·N)` (Hansen) with IPOP/BIPOP restart inflation; GUI cap 5000.

Local-only, added 2026-10-31 evening (**Launch IPOP/BIPOP controls; no GitHub issue state changed**):
- **Landed:** Launch + Compose search forms â€” CMA restarts mode (config default / off / IPOP / BIPOP)
  + max; CLI `--restarts-mode` / `--restarts-max`; `jobs.py` allow-list. Run detail still shows
  the schedule read-only after the fact.

Local-only, added 2026-10-31 later (**beat_metal + Mac staged path; no GitHub issue state changed**):
- **Landed:** `beat_metal` in `BACKEND_NAMES` / `BeatBackend` / CLI; staged harness `--backend auto`
  â†’ Metal on Darwin (clears `cuda_fused`). See staged README + evidence doc Mac section.
- **Owed on this Mac:** create `.venv` with Python 3.12/3.13, `pip install -e ".[dev,crosscheck]"`,
  `doctor`, then the staged A/B; Macâ†”4060 A/B (<0.2 dB) before mixing Metal into CUDA datasets
  (P3 remainder).

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) â€” see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, 2026-11-01 (**hardware decision study; no GitHub issue state changed**):
- **DONE (decision study, not rental benchmarks):** owner clarified theoretical rent-versus-buy scope; $0 rental spend. `docs/evidence/HARDWARE_2026-11-01.md` audits stored timings and backend/lane code and gives current rates with labeled cost scenarios.
- **MEASURED (CPU mesh sizing):** fixed T2 seed first globally validates at 12 kHz among tested sizes at 33,959 dofs / 67,245 triangles (EPW 8.4). EPW 6 gives 33,938 triangles but only 8.58 kHz global validity. This does not establish acoustic convergence or a universal minimum.
- **SOURCE-DERIVED capacity constraint:** unchanged standard CUDA multi-channel path requires at least 85.410 GiB for operators+identities+LHS at that full-wall seed, before additional workspace. The 80 GB tier cannot fit that path. H200 141 GB is a test candidate, not a measured solution; cheaper 24/32 GB coarse-screen tests answer a different fidelity question.
- **OPEN:** successful exact 41-frequency request on candidate hardware, root cause of CUDA 719, actual billed cold/warm costs, unified-backend C4 parity and 1/2/4/8-lane results. Flat `nvidia-smi` peaks do not establish invariant live workspace. Historical seed/winner mesh attribution and current overwritten/unknown-baseline VRAM trace limitations are corrected in the study.
- **OPEN (implementation if shared-host lanes are selected):** per-device locks/monitoring, owned-host-only cleanup, private registries/cache staging, parent-only dataset writes and deterministic CMA coordination. Existing evaluator has side effects; the current one-writer/global-cleanup code is unsafe for naive concurrent workers. Separate machines, one brief each, are the simpler future deployment test.

Local-only, 2026-10-31 (**3D evolution transparency, re-landed on `meh/integration`**):
- **Recurring owner report (run `20261031T202159Z-screen-ba7648`): mesh renders as see-through triangles.**
  Not a renderer regression: the hole-free decimation fix (`64ccb20`) lived only on
  `feat/hardened-plan-2026-10-29`; this worktree is `meh/integration`, whose `gui/data.py` still stride-sampled
  (`M3D_VERSION=1`, cap 6000 -> 11.5k-tri frames cut to 5.8k). Code files cherry-picked here, cache key bumped
  to `[2,30000]`, stale per-run cache regenerated (`decimated:false`). The long-running GUI on :8765 must be
  restarted after any such change; a branch switch also silently reverts the working tree. 131 GUI tests pass.
  Detail: CONTINUITY 20:28Z.

Local-only, pushed 2026-10-30 late (**chief-implementer hand-off; no GitHub issue state changed**):
- **OPEN:** owner/lead agent to pull branch `ccr-4978c80b-tvvcgv` locally and run `docs/meh/CHIEF_IMPLEMENTER_HANDOFF.md`.

Local-only, not pushed 2026-10-31 (**MEH wave 1 merging into `meh/integration`; no GitHub issue state changed**):
- **DONE:** M4 network layer (merged, `meh/M4-network` parts 1+2: drivers, network, dsp, limits, synthesis).
- **DONE:** M4 inner optimiser (`hornlab_search/meh/inner.py`; merged `meh/M4c-inner`, commit `0cdfd7a`).
- **DONE (M8 step 1):** solver fork validated on CPU and CUDA - superposition, reciprocity, single-tag parity,
  reduced-vs-full symmetry all pass. The M2 Julia testset needed three fixture fixes (commit `93ef848`/`1efdc6f`);
  properties and tolerances unchanged.
- **DONE (M8 step 2):** single-tag parity vs the current pin <= 5.91e-5 dB on two finalists (floor 0.039 dB).
- **DONE (M8 screen):** T2 40-eval CMA + verify -> J 9.530 -> 11.894 (best `ed11d2cd3acc`); T1 40-eval CMA + verify
  -> J 13.228 -> 14.512 (best `704051ae928c`). Runs `20261101T004552Z-screen-427d57` and
  `20261101T015657Z-screen-fc1d24`; evidence `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **BLOCKED on this hardware (screen band):** the contracted 120-12,000 Hz 1/6-octave grid has no legal operating
  point on the 8 GB card. A 12 kHz-resolving mesh needs >= ~8,600 dofs (7.9/8.19 GB peak; the 41-frequency sweep dies -
  CUDA 719 / worker_exit, measured); the smallest legal mesh (epw 4.05, 8,044 dofs) leaves CMA neighbours at
  8,296-8,485 dofs, over any cap that keeps VRAM safe. `cuda_fused` refuses multi-channel by design. Resolving the band
  needs a >= 12 GB card. Stopped by owner direction.
- **DONE (docs accuracy):** the M8 evidence doc and its INDEX line now state the full result set (links 1/2/5/6 PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks); no number changed.
- **CI FIXED (PR #18):** `tests/test_solve_worker_restart.py` now gates `hornlab_beat_bem` with
  `pytest.importorskip`, so CI (which does not install the solver) skips it instead of failing at collection.
- **MERGED main (2026-11-01):** `origin/main` merged into `meh/integration`; 16 MEH-touched files normalized to
  LF (main is LF), logs unioned so no entry from either side was dropped, and main's Metal/backend-override work
  coexists with the MEH config changes. PR conflicts resolved.
- **PACKAGED (handoff, PR #18):** `docs/meh/MEH_QUICKSTART.md`, `tools/meh/run_screen.ps1`, and
  `docs/evidence/meh_2026-11-01/` (both verified winners + README). No production code changed.

- **PR OPENED (wrap-up):** `meh/integration` -> `main`, carrying the full MEH implementation, the owner-approved
  pin bump, both verified screens, the six-line readiness proof, and the hardware audit/hand-off. Final offline
  suite green at the tip (exit 0). Open items inside the PR body: 8 GB band ceiling, M9 blocked, step 3 blocked,
  link 4 budget decision.
- **TIDIED (hand-off):** the withdrawn VRAM reading no longer appears as fact in s5/s5b; both now carry the
  source-derived operator-storage statement and point at the s2a corrections. Duplicate table row removed.
- **CORRECTED (hand-off):** four claims withdrawn after the audit - wrong mesh attribution (winners are
  5,872/6,249 dofs), the 12x scaling claim, the flat-VRAM reading (and its backing CSV was overwritten), the
  25-35k element sizing (first valid whole-wall mesh is 33,959 dofs, ~85 GiB), and 'lanes are one line'.
  The audit's rent-first conclusion and 141 GB tier stand.
- **UPDATED (compute brief):** the hand-off now carries the measured baseline (3.6 vs ~45 s/frequency;
  ~12x for 1.44x elements) and an explicit unified-memory section (GH200/GB200, Apple Metal, MI300A ROCm,
  APU negative control, CPU-only) with a required validation gate for any non-CUDA recommendation.
- **OPEN (next agent, compute/hardware):** `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` - fit the s/frequency and
  VRAM scaling laws, benchmark bandwidth vs compute tiers, measure candidate-level lanes on rented GPUs, and
  return a machine table in candidates/hour and $/candidate. Nothing in the MEH code blocks that work.
- **OPERATIONAL NOTE:** stale BEAT hosts from an earlier fused probe were adopted by a later run and produced a
  misleading fused/multi-channel error. Kill Julia hosts before launching a screen (`gpu-clean`).
- **DONE (worker recycling):** opt-in `solve.worker_restart_every` (fake-tested), set to 8 in both MEH search
  configs; it does not rescue the 8 GB ceiling but is committed for larger cards.
- **OPEN (verify fidelity):** `verify` reports that the verify mesh equals the screen mesh at the current band/caps;
  only the frequency count and balloon size change. A true higher-fidelity mesh needs a raised dof cap or a lower band.
- **DONE (readiness, measured on the stored T2 winner):** link 1 PASS, link 2 PASS, link 5 PASS, link 6 PASS (J
  9.530 -> 9.727 with a different mid driver and hp_hz, cached, no new solve).
- **FAIL (readiness link 4):** the inner optimiser takes 6.58 s for 1,224 CMA evaluations on the shipped T2 brief,
  3.3x the hand-off's < 2 s gate. Per-evaluation cost is 5.4 ms, so this is an evaluation-budget/combo decision.
- **PARTIAL (readiness link 3):** with the mid drive muted, a 9.19 dB notch appears between 1200 and 1300 Hz
  (+18.7 % to +28.6 % of the 1-D 1.0108 kHz), so the +-20 % gate is met only at the lower edge of that interval. A
  25 Hz sweep over 1150-1350 Hz is needed to place the centre.
- **BLOCKED (M8 step 3):** the meh CAD tool refuses a full model (quarter open shell only), so quarter-vs-full cannot
  be measured without extending the tool.
- **BLOCKED (M9):** Boundary Lab is not present in this workspace; it needs its own environment (pins BEAT 0.6.0).
- **OPEN (M8 step 4):** L0 vs L1 notch comparison is not run.
- **DONE (M10):** bass box - 7 woofer files, `tools/bassbox.py`, 65 tests, `BASSBOX_2026-10-31.md`. Recommendation:
  1 x FaitalPRO 18XL1800 sealed 55 L net + LT; pair = +6 dB; smallest = 1 x 15XL1400 sealed 38 L.
- **OPEN (task text):** M10's "B4 (fs = fb, Qts 0.383, alpha 1) is -3 dB at fs" is wrong for the lossless vented
  box (alpha = 1 gives 0.0 dB at fs; the B4 constant is alpha = sqrt(2)). The test asserts both; amend the task file.
- **OPEN (datasheets):** 15TBX100 (7.8 %) and 18NLW9601 (4.5 %) Vas/Mms vs Fs are internally inconsistent; Beyma
  15LX60V2 Xmax 8 mm vs +/-9 mm. Files follow C8 and say so in `notes`.
- **DONE:** M6 objective v5 + brief `meh:` block (merged, `meh/M6-objective-v5`).
- **OPEN (M7):** `search/evaluate.py` currently only bridges version 5 (params class + scorer registration); the MEH
  evaluation branch that builds `meh_ctx`, runs the inner optimiser and synthesises the response is M7's.
- **OPEN (M1/M5):** cone `frame_od_mm` / `motor_od_mm` / `dish_mm` and CD `duct_mm` are not in the s8 table; M5 keeps
  the C9 [inferred] placeholders (CD duct 40 / 25 / 25 mm) until a drawing is read or M8 measures it.
- **DONE:** M3 multi-tag solve adapter (merged, `meh/M3-solve-adapter`).
- **OPEN (M8 gate):** the installed `hornlab-beat-bem` has no `SolveConfig.impedance_matrix`; every multi-tag solve
  raises ConfigError until M2's fork branch is validated on the GPU and the pin is bumped (owner approves the bump).
- **OPEN (M5 follow-up):** seed renders not produced - `hornlab-render` needs `pyvista`, absent from the venv and no
  installs are permitted. `cd_duct_mm = 0` is not modelled (no disc face without a bore). Unknown cone
  (cutout, depth) pairs are refused until M1's driver files land.
- **OPEN (local, not mine to commit):** the integrator's checkout carried unrelated regenerated catalog work
  (cone_plughorn_2026-10-28 entries typed 2026-10-31 in `examples/catalog.yaml`, `docs/reference/PARAMETERS.md`,
  `TYPOLOGIES.md`, `param-catalog.v1.json`); preserved as a patch outside the MEH branch.

Local-only, pushed 2026-10-30 18:10 EDT (**MEH integration started on the owner's box; no GitHub issue state changed**):
- **IN PROGRESS:** `meh/integration` created from `origin/ccr-4978c80b-tvvcgv` (hand-off section 0); baseline suite
  green after fixing two pre-existing reds (stale sandbox.js dispose pin, CRLF-committed `param-catalog.v1.json`).
- **OPEN (blocker, GPU):** night queue `n2_gapfill_2026-10-30` occupies the only GPU; M8 GPU validation/pin bump waits
  for it to finish (CLAUDE.md: never start GPU work while a night queue runs).
- **OPEN (owner):** confirm the 380 mm box depth assumption (M8 readiness step 1 + layout feasibility depend on it).

Local-only, pushed 2026-10-30 (**MEH implementation hand-off; no GitHub issue state changed**):
- **OPEN (wave 1, dispatch-ready):** M1 driver files, M2 solver fork multi-tag + impedance matrix, M3 solve adapter,
  M4 network + inner optimiser, M5 CAD tool + multi-label STEP, M6 objective v5 + brief block, M10 bass box
  (`docs/meh/README.md`).
- **OPEN (wave 2/3):** M7 pipeline + configs; M8 GPU validation, pin bump, first screen (owner's box); M9 Boundary Lab.
- **OPEN (owner):** confirm the 380 mm box depth assumption.
- **CLOSED:** dossier s13 questions answered by the owner 2026-10-30 (dossier s14).

Local-only, pushed 2026-10-29 20:15 EDT (**mini MEH research pass complete for this round; no GitHub issue state changed**):
- **OPEN (owner decisions):** mini MEH targets - bass route (top + sub / one-box PR-vent ~106 dB / 3-way), size number, use and
  coverage, 4 x 4-inch vs 2 x 6.5-inch, DSP per channel, new J terms, commercial intent (Synergy patent)
  (`docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` s13).
- **OPEN (senior, `NOTES_FOR_SENIOR.md` 2026-10-29):** attribution fix in `docs/DRIVER_MODEL.md:42` (issue #78 is
  timini/horn-simulation); frozen-plan MEH tag note; BL symmetry note.
- **CLOSED (research):** web-lane findings folded into the dossier s7-s8 with orchestrator spot-checks.
- **FINDING:** compression-driver internal depth sets the mid ceiling in a mini MEH (1-D); any MEH model must include it.

Local-only, pushed 2026-10-29 18:45 EDT (**mini MEH research pass, draft; no GitHub issue state changed**):
- **OPEN (owner decisions):** mini multiple-entry horn targets - separate sub vs bass in the box, size number, use case /
  coverage, 4 x 4-inch vs 2 x 6.5-inch mids, DSP per channel, new J terms
  (`docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` s13).
- **CLOSED 2026-10-29 20:15:** web-lane findings folded into the dossier s7-s8.
- **FINDING / correction:** the mesher has MEH tag names 8-12 only, no builder; MEH geometry needs the CAD -> STEP route
  (multi-label) or a new builder. Python `SolveConfig` refuses more than one source tag although the engine supports it.

Local-only, pushed 2026-10-28 20:50 EDT (**cone mid horn typology + research; no GitHub issue state changed**; 8 commits to origin/main):
- **OPEN:** `cone_plughorn` never solved on the GPU; first screen should use `source_motion: axial` and a CPU cross-check of the
  2.4 mm axe-head/throat gap (thin-gap risk).
- **OPEN (handoff):** paper-cone driver T/S unknown (Funktion-One publishes none); axe-head cone fill not modelled (front-chamber
  cut-off estimate too low); see `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md`.
- **OPEN:** compression-driver library lacks Sd/Mmd for every driver (absolute sensitivity model cannot run on them yet).
- **LOCAL ONLY:** `third_party/` (LibreDWG, ODA File Converter) and `reference/` (Funktion-One CAD) are gitignored by design.

Local-only, added 2026-10-28 17:45 EDT (**no GitHub issue state changed**):
- **OPEN:** round-throat `rt__b1t__rosse_morph` and `rt__b2t__rosse_morph` scored J 1000 on every eval (infeasible); diagnose before re-queueing.
- **OPEN:** verify slips 0.9-2 J for ATH 2in core / ridge and Salmon / Le Cleac'h tall shapes vs screen; screen ranking of those is optimistic.

Local-only, added 2026-10-28 afternoon (**skills + tools, no GitHub issue state changed**):
- **OPEN:** `tools/night_queue/queue.ps1` and `launch_detached.ps1` are parse-checked only; first live use should be the next queue launched
  when no night is running (watch the log and the controller's parent process).

Local-only, pushed 2026-10-28 15:05 EDT (**render sheets for the day's solved styles, no GitHub issue state changed**):
- **OPEN (owner decision):** the new b3a leader `hy__osse_flare_curl` J 1.113 wins on pattern but is weakly loaded (output gap at f0
  11.5 dB, loaded from 1.76 kHz) and `objective.load` is weighted 0 in that brief, so J cannot see loading. Decide: accept EQ, or add a
  load-weighted re-score of the day's top designs before the verify night.
- **OPEN:** screen-only. None of the 2026-10-28 winners has been through `verify`; the D_verify night has not started.
- **FINDING:** non-square mouths (60x40, 72x44) score 11.9-21.6 J on the 90x90 brief (3 of the 4 worst results of the day) - drop that lane
  unless the brief changes. Four-petal Salmon quatrefoils land in the chanterelle band (9-12), not the hybrid band.
- **OPEN:** full offline suite not re-run since the `osse_rollback` / `fc_fold` / `fc_union` changes (blocked by the live GPU night).

Local-only, pushed 2026-10-28 11:36 EDT (**shape work + night queue, no GitHub issue state changed**; 9 commits to origin/unified-typologies):
- **OPEN, first result:** constant-directivity hybrid `hybrid__os_ruffle` J 3.83 (b3a 90x90, 40 solves) vs best Salmon chanterelle 10.73. Refined
  petal/lobe horns (`examples/typologies/petal_os_2026-10-28_v4/`) queued in night `v4_day_H2_hybrids_2026-10-28`; not yet solved.
- **OPEN:** the full offline suite has not been re-run since the osse_rollback / fc_fold / fc_union changes; run it when no GPU night is live.
- **OPEN (owner):** round-throat A/B cells (`examples/typologies/round_throat_2026-10-28_v4/`) queued; the non-round effect is still unmeasured.
- **LEFT ALONE:** `hornlab_search/gui/static/sandbox.js` and `view3d.js` carry uncommitted changes not made in this session.

Local-only, added 2026-10-27 late evening (**P12 senior pass, zero GPU - no GitHub issue state changed; to-dos are P0 in `docs/NEXT_DEV_PRIORITIES.md`**):
- **OPEN, owner inputs:** driver list per brief + use case (tube-amp hi-fi / PA); gate levels (hi-fi sensitivity floor at 1 W / 1 m,
  PA max-SPL target); scoring decisions (output-at-f0 term, stricter hi-fi pattern, 10 m, half weight above f11); woofer block per brief.
- **DEFECT (new):** OSSE / R-OSSE `aspect_ratio` stretches the driver coupling plane (24x36 ... 50x36 mm on 36 mm briefs; 8 of 30
  winners). Owner rule decided: round coupling plane at the exit size, no adapter. Fix: lock `aspect_ratio = 1` in the next night's
  OSSE/R-OSSE copies, then a pre-mesh refusal via `mesh/throat_check.py` (after the night).
- **IN PROGRESS:** ripple/ridge night stopped after 6/10 jobs (runner killed from outside ~20:08 EDT, job 7 at 87/100); re-run
  night `v4_ripple_rerun_2026-10-27` launched 21:27 EDT, detached via WMI (resume job 7 + the three flute jobs that never started).
- **FIXED 2026-10-28:** the night runner now takes over a dead holder's `runs/.gpu.lock` (`gpu-clean` still does not).
- **OPEN (owner challenge):** how much a non-round driver coupling matters is unmeasured; round-throat A/B cells run 2026-10-28;
  a one-design A/B with a round source + built-in transition section is owed (new geometry option).
- **FINDING:** the b3a 90x90 / 400 Hz brief has no acceptable horn yet (leading cells 11-13 dB short of loading; 1.4" OS-type throats
  cannot load there) - needs loading-capable families or a 2" exit, not a re-rank.
- **OWED:** calibration night (band-split screen, 10 m vs 2 m, epw 6 vs 9 presence band, verify-grid rank check); new screen grid
  (low band to 0.7 f0, ~7 presence-band points); budget = valid solves; reduced knobs / two stages / successive halving; CMA-ME shape
  axes; `report --driver` in `cli.py`.
- **Small bug (pre-existing):** `tools/gen_param_catalog.py --check` prints its `committed=` / `fresh=` labels swapped (line 108).

Local-only, added 2026-10-26 (**campaign Phase 0 Steps 2C/3/4/5 LANDED â€” CPU only, no GPU/Julia; no GitHub issue state changed**):
- **What is now in the tree**: six lane reports (`docs/research/campaign_2026-10-26/`), 14 briefs (`examples/briefs/campaign_2026-10-26/`), 23 configs (`examples/typologies/campaign_2026-10-26/`), and `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md`. All 23 cells dry-run green; dofs 921â€“9,871; envelope 0; mouth within 10 % of K-law on tall/square and inside-envelope on wide; LHS invalid 0â€“37.5 %; grids 12/29/36; no cell dropped.
- **Open items for the campaign owner/gates (unchanged, now with measured seeds):** (1) the one BEM verify seed per portrait morph/rows class before a long campaign (geometry is proven, coverage is not); (2) `beat_bem` rejects the xz native symmetry plane, so `native__lecleach_asym_odd` keeps `span: full` / quadrants `'1234'` and the `half_xz` 2Ã— saving stays unused on GPU (ISSUES entry in the Phase-0 code commit); (3) Phase B items 1â€“4 still own the fused s/candidate and the >15,984-dof go/no-go; (4) the D-11 option (a)/(b) choice is now encoded per cell (tall cells strict K-law, wide cells commercial convention) but remains the owner's ruling if the campaign is re-frozen; (5) `cov_band_hz` (D-3) is not implemented and is not needed by these cells (f11 is disclosed per brief instead).
- **Non-blocking residuals recorded in the evidence doc:** LHS invalid rates of 31â€“37.5 % on four cells (below the >40 % narrowing trigger) are envelope/geometry refusals, not crashes; one `b3bt__rosse_morph` LHS corner is above 12,000 dofs and is graded infeasible; the biradial/hypex generator rows print a pre-existing H/V throat-tangent warning while meshing validly.


Local-only, added 2026-10-27 (**campaign smoke night LANDED - report only, no code/config change; no GitHub issue state changed**):
- **Report:** `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` - 41 jobs, 376 evaluations, 252 valid / 124 refused (33 %), 157.8 valid evals/hour, T0 26/27, crease A/B at equal budget 60, WALLS, the 8 kHz fused ladder, and the observer phase split.
- **Crease class confirmed on GPU:** `crease__core_law` J 19.022 -> 2.784 (-85 %) keeping the crease (a(45) - mean(a0,a90) = +9.97 deg); `crease__osse_b1w` no gain; control -46 %. One seed each - no typology-vs-typology claim yet.
- **DEFECTS / OWED (new):**
  - `gcurve__osse_b1w` seed was **outside its brief envelope** (783 x 581 vs 380 x 300 mm) -> invalid, its T1 found 0 valid designs. **FIXED 2026-10-27:** the curve station now sits at the mouth (`gcurve_dist 1.0`, width 335; dist box 0.2-1.0, width box 100.5-368.5). Full mirrored mouth **335.2 x 291.5 mm**, T0 **J 9.85253, 1,855 dofs, 3,543 triangles**, v3 dataset record written. A dist-0.5/width-130 workaround was measured valid (367 x 292, J 6.289) but rejected because it changed the intended mouth scale. **Still open:** it pins `aspect_ratio 1.0` while the control runs 1.15, so it is not a clean A/B; and J sees only H/V planes.
  - **The objective terms are not normalised**, so weights do not mean influence: `load 0.5` is 2 % of J on `native__lecleach_rollback` while flat is 45 %. Four of eight scored cells are single-term >70 %. Normalise before any weight tuning.
  - `f_load_hz` = 500 Hz on that seed is the **grid floor**, not a measurement (screen grid starts at 500 Hz).
  - Per-frequency assembly dominates (73-96 % of one frequency's cost), so **frequency count is the throughput knob**; the 8 kHz ceiling binds just above 14k dofs (13,999 = 88 % VRAM, 16,960 = 96 % unusable).
- **Open gates unchanged:** BEM verify seed for the portrait morph/rows cells; T3 diagonal-balloon check for crease vs control (queued); full offline suite; LHS audit of the widened boxes; `tools/expand_walls.py`; sandbox law card browser check; catalog generator recursion into campaign folders; `osse_baseline` 803 x 643 vs its own 750 x 600 envelope; parked `make_shape_variants.py`.
- **Throughput (observer, to be re-measured):** over a ~6-minute search window the GPU solved only ~33 % of the time (`between_evals` 39 %, `refusal_or_mesh` 24 %), median utilisation 24 % at 931 MiB / 19 W, while the ladder rungs were GPU-bound at 100 %. The window is too short to schedule pipeline work from; relaunch `tools/observe_run.py` with the next full search night.

Local-only, added 2026-10-26 (**read-only run observer added - `tools/observe_run.py`; no GitHub issue state changed**):
- Samples GPU util / VRAM / power / clocks, CPU per process, the running job and the newest run's eval rows to `runs/nights/<night>/observe.ndjson`, then writes `observe_summary.md` (phase shares, utilisation histogram). Read-only: no solver launch, no writes into run dirs.
- **First measured facts (smoke night):** GPU is at 100 % during solves but idle through the CPU phases; the card was using 695 MiB at a 4.8k-dof cell while `python.exe` (128 %) and `julia.exe` (144 %) ran the mesh/metrics side at 22.6 % total CPU. Feeds the "2x faster" analysis: pipeline ceiling, concurrency headroom, VRAM per cell size.

Local-only, added 2026-10-26 (**senior scoring review of the native campaign briefs - text only; no GitHub issue state changed**):
- **Changed:** `native_ath_core_2in` and `native_twinray_380_14in` -> objective v3 with K-law f0 (1280 Hz; 743 / 1397 Hz per plane, computed from the published mouth dimensions); `native_lecleach_1200_1in` -> scored on loading (cov 0.3, load 0.5, z_min 0.7; dislope 0). **J on those three brief names is not comparable with earlier results.**
- **Deliberately unchanged:** all B1/B2/B3 briefs (already v3 + f0, wide ones with f0_v), the `*_rows` briefs (dislope 0), the B3b briefs (load 0.5 / z_min 0.7).
- **Known scoring limits, no code change tonight:** H/V planes only (diagonal crease/X-shape effects invisible); the screen grid starts at 500 Hz so the 400 Hz "loads to" claim is only judged at verify; the loading term is band-averaged and diluted by the always-loaded high end; coverage still graded to 8 kHz past the 1.4-inch driver's ~5.6 kHz cross-mode (owner's choice). A T3 diagonal-balloon check for the best crease vs best control is **queued, not run**.
- **DEFECT found during the smoke run (FIXED 2026-10-27): objective-v3 runs wrote no dataset records.** `hornlab_search/dataset/record.py` rejected `objective_version` 3 (`'objective_version' must be 1 or 2, got 3`), logged by **all 27** T0 jobs. `search.ndjson`, `best.json` and reports were unaffected; the phase-2 surrogate data was what was lost. Fixed by moving the allowed set to `hornlab_search/objective/versions.py::SUPPORTED_OBJECTIVE_VERSIONS`, shared with the `search/evaluate.py::_score` dispatch (import-time table check); records now reject anything outside it (`99`, `0`, `4`, `"2"`, `True`) and still treat a missing field as v1. Tests: `tests/test_dataset_record.py` (v3 write/validate/read + dispatch-table equality + end-to-end store), offline **1689 passed, 20 deselected, 1 warning**. A live v3 T0 wrote `dataset/shard-0030.jsonl`. **Records lost on the smoke night are NOT reconstructable from `runs/nights/smoke_2026-10-27/`** (logs + job-level `summary.jsonl` only); the per-eval `search.ndjson`/`metrics.json` survive in the referenced run dirs, so a bespoke backfill is possible from those, but no tool was written.

Local-only, added 2026-10-26 (**campaign boxes re-opened + 4 crease cells ADDED - config/text only, no GPU/Julia; no GitHub issue state changed**):
- **Owner ruling on record:** a search box is never the binding constraint; the brief envelope + mesh validity are. 180 searched knob boxes across the 23 Phase-0 cells were widened to physical ranges (never narrowing an existing edge, seeds byte-identical 23/23, 25 pins intact, `infeasible_penalty: graded` everywhere). Tool: `tools/widen_campaign_boxes.py` (`--dry-run` table / `--write`); table + rationale: `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md` Â§8.
- **New crease class:** `crease__core_law`, `crease__osse_b1w` (per-direction `az_*` law) and `gcurve__osse_b1w` (superellipse guiding curve) against the existing `control__osse_morph_b1w`, all native OSSE with fused CUDA / 12,000 caps / Morph rect at the seed mouth. **Aspect-ratio divergence is an open interpretation:** 1.0 for CORE + gcurve (mesher requirement / circular), b1w's 1.15 for the two b1w cells (1.0 would break the 300 mm envelope). Senior to adjudicate.
- **Open gates:** the widened boxes are **NOT re-audited** - the invalid rate will show in the mini-T1; a T3 diagonal-balloon check (crease vs control, same budget) is **queued but not run**; the crease cells still need a BEM verify seed before any long campaign (same rule as the portrait morph/rows cells).
- **Still owed from Phase 0:** LHS audit of the widened boxes; `tools/expand_walls.py` (auto-widen a box edge best designs press against); the shipped `osse_baseline` 803 x 643 mm vs its 750 x 600 envelope (reseed or widen the brief - owner decision); `tools/make_shape_variants.py` + `examples/typologies/shape_variants/` stay parked and uncommitted ("pre-research ranges; superseded by the campaign crease cells"); campaign-folder configs get no catalog tooltips until `gen_param_catalog.py` recurses.

Local-only, added 2026-10-26 (**per-direction OSSE law LANDED - `az_*` knobs; no GitHub issue state changed**):
- **In the tree:** `design/families.py` folds 11 `az_*` knobs into the mesher's own `p`-expressions for `a`/`n`/`s` (the T0 validity gate for tonight's crease cells), `tests/test_design_azlaw.py` (6 pins), the sandbox law card, and ATH dossier section 5b. Focused gate 125/0/0/0; catalog `--check` OK (no regeneration); `node --check` OK.
- **Open, low priority:** the sandbox law card is committed **unverified in a browser** (owner deferred GUI click-testing); the full offline suite is **deferred** (owner: no CPU time on a night that has GPU work queued); `tools/gen_param_catalog.py` does not recurse into `examples/typologies/campaign_*/`, so campaign cells still have no parameter tooltips; `az_sf_m` is limited to multiples of 4 for quarter symmetry (a `half`/`full` model would need the mirror restriction relaxed deliberately, not silently).

Local-only, added 2026-10-25 (**PLANNED ONLY â€” nothing started, no code/config/bound touched**; owner-directed; filed as `docs/NEXT_DEV_PRIORITIES.md` **P9**, decision record in `NOTES_FOR_SENIOR.md`):
- **Defect on record (to fix)**: search time-lapse page â€” the `3D` checkbox renders **checked** while the canvas prints `3D off â€” flip the 3D toggle above.` Control state and render state disagree, or the render throws into the off-state placeholder. Exact grep anchor is that placeholder string. Not yet confirmed in code (code-map lane still running when recorded).
  **LANDED 2026-10-25 on `unified-typologies` @ cd71c1c** â€” root cause was a duplicate DOM id (checkbox and 3D container both `id="evo-3d"`); the checkbox is now `evo-3d-toggle` (container id untouched â€” an existing source pin pins the container markup), box state made coherent, and the stranded `_dispose3d`-on-the-input leak closed; `tests/test_gui_evolution_3d_toggle.py` (4 pins + verified negative control) added; the GUI trio 107/0/0/0 + node --check + compileall green. WebGL painting itself remains an owner eyes-on confirm (headless cannot render).
- **Owner ask 1 â€” per-parameter descriptions as hover text** on BOTH the Run page and the Typologies page, phrased as *what the parameter does to the geometry/acoustics* (the equation term it moves and the physical effect), grounded in the research dossiers rather than invented. Verified gap: `gui/static/glossary.js` has objective/metric terms only and **zero** geometry-knob entries; `app.js` has brief-field labels only.
  **LANDED 2026-10-25 on `unified-typologies` @ 711b856 (designer lane)** â€” `gui/static/paramtips.js` reads the committed catalog (graceful raw-key fallback everywhere, never a wrong-family guess); wired onto evolution knob rows, run-detail sensitivity table, seed-derivation card, compose seed preview, and the Typologies cards (knob chips); `tests/test_gui_param_tips.py` 10/10 + GUI trio 118/0/0/0 + node --check green.
- **Owner ask 2 â€” an interactive typology sandbox**: click a typology â†’ a page that draws the H/V wall section AND the 3D shape, where the owner drags knobs by hand and both views update live (replacing the run page's read-only "evolution" scrub for this purpose). Each slider shows the parameter name beside it, an editable **min and max on either side** of the track, and can **save those min/max as that typology's default**.
  **SPIKE PASSED 2026-10-25 (fix-5, measured):** live-drag 3D is real for generator/grid/native kinds (8-35 ms per full tick); rows kinds are march-bound (148-580 ms -> honest `slow: true` + release-debounce); `multicell_3x3` (CAD) is the only hard `available:false`; one silent-wrong-geometry hazard pinned (the preview entry point builds a default OSSE for unrecognized params - the endpoint must branch on kind first). Endpoint sketch + seam-module rule-2 compliance path recorded in CONTINUITY.
  **LANDED 2026-10-25 on `unified-typologies` @ 8715d88 (backend) + d5e3363 (page)** â€” full offline suite 1593/0/0/0 + node --check x8 + compileall + catalog --check green; details, timings and honest limits: `docs/CONTINUITY.md` sandbox entry.
  **Owner-screenshot follow-up (fixed):** the quarter mouth ring is now mirrored into a closed outline (both pages), the evolution frame-player's mm-vs-metre rig mismatch that left the 3D panel blank is fixed, and rollback meridians keep their own point order instead of being z-sorted (the striped vertical-plane fringe). Pins added for the ring quadrants and the rollback order.
- **Owner ask 3 â€” one findable source of truth** joining *typology â†’ design â†’ formula â†’ parameter â†’ min/max â†’ design characteristic â†’ the code that implements it*, for users and agents both. Proposed as an annotation layer over the existing authorities (`families.KeySpec` hard limits, `registry.DEFAULT_KNOBS`, `examples/typologies/*.yaml` bounds) plus a generated reference doc and a drift-gate test â€” explicitly **not** a hand-written fourth copy of the numbers (`AGENTS.md` line 29).
  **LANDED 2026-10-25 on `unified-typologies`** (P9, commits 4005e8a + bf20807 + 19cad0a): `hornlab_search/design/params/` (generators 26 / rows 36 base names / native 63 knob docs; 39 typologies; zero authored horn numbers), `tools/gen_param_catalog.py --write/--check`, the FAIL-not-warn both-ways drift gate (`tests/test_param_catalog.py`, 37 tests), the generated `docs/reference/{PARAMETERS,TYPOLOGIES}.md`, and the GUI wire contract `gui/static/param-catalog.v1.json` served through the existing static handler. Every knob carries `bounds_source = {file, key}` â€” the exact home a saved bounds edit must target. Details + honest contract gaps: `docs/CONTINUITY.md` 2026-10-25 parameter-SSOT entry.
- **Verified inputs for it**: 36 catalog ids in `examples/catalog.yaml`; 4 mesher families; 11 generator types; overloaded knob names `n`, `q`, `a_deg`, `T`, `stop_deg`/`max_wall_deg`; open doc/code mismatch `exponent` default 2.0 (`12_RESEARCH_BASIS.md:158`) vs 4.0 (`registry.DEFAULT_KNOBS`).
- **Hard dependency / guard**: the sandbox shows real bounds and must NOT let a "save as default" widen one. Bounds widen only via **W8** (per-typology search-box audit), per config, measured â€” consistent with the owner's recorded over-constraint remark and the oracle's S1/S5 tables.
- **Still owner-decided** (updated as of the parameter-SSOT landing): metadata package location â€” **resolved: `design/params/`** (built and landed there; import-light, numpy-blocked proven); whether saved slider bounds are a personal preference or an owner-gated edit to `examples/typologies/*.yaml` â€” **owner ruled 2026-10-25: edits save to where the bounds live** (to be built safely in the sandbox lane: write only the exact `bounds_source` key, validate against the hard `KeySpec` clamps, never touch a frozen contract, config_sha churn on resume is expected and honest); whether the sandbox may render an out-of-envelope design (and with what marker) â€” still open, will reuse the run page's at-limit red-marker language + `registry.envelope_overshoot_estimate`; which `exponent` default is canonical â€” **deferred, not blocking**: tooltips state each typology's actual seed instead, and the 2.0-vs-4.0 mismatch is surfaced with both claims, no winner picked.
- **Brief-set correction (2026-10-26, from the owner's killed run):** the 90Â° brief was paired with a non-CD Le ClÃ©ac'h and with an envelope smaller than its K-law mouth, and the Freeform narrow brief was unreachable because `mouthAngleDeg` is bounded â‰¥35Â°. Corrected briefs saved at 500â€“10,000 Hz; the 10 kHz dof ceiling (largest mouth 284 mm at the 5,000-dof screen cap / 379 mm at the 8,900 hard ceiling) makes most low-f0 briefs infeasible at that top. Full table + reasoning: `docs/CONTINUITY.md` 2026-10-26 entry. Open owner decision: whether the wide/narrow design briefs should keep a 10 kHz top (verify-only / mostly `mesh_too_large`), drop to 2â€“4 kHz for screen work, or move to a larger-VRAM card.
- **MEASURED GPU ceiling (2026-10-26, stress ladder, real VRAM):** 8 kHz is safe to **474 mm** mouth (5.8 GB peak, 2.4 GB headroom); 500 mm works at 7.2 GB (under 1 GB headroom, too tight for a search); â‰¥550 mm saturates the card. At 10 kHz: safe to **353 mm** (4.9 GB), edge at 403 mm (7.3 GB), â‰¥424 mm saturated. **No crash occurred** â€” the failure mode is CUDA OOM / host-backed pool oversubscription (pool reserved 15.9 GiB), logged as `Out of GPU memory â€¦ 100.00% (7.996 GiB)` at the top rungs, with hosts cleared afterwards. Three cap-500 briefs saved (`cap500_90x90_650hz_1p4in` â€” 90x90 at f0 650 Hz, 434 mm mouth; `cap500_90x60_850hz_1p4in`; `cap500_60x40_1270hz_1in`) plus the owner-override `narrow_60x40_800hz_1in` (794 mm mouth, no cap, may exceed the card at 8 kHz â€” accepted); practical home is a 5.5â€“6 kHz screen + 8 kHz verify. Superseded: `cap500_100x100_500hz_1p4in`, `cap500_90x90_565hz_1p4in`, `narrow_60x40_880hz_1in`. Details + full ladders: `docs/CONTINUITY.md` 2026-10-26 MEASURED GPU CEILING entry.

Local-only, added 2026-10-25 (typology pass completion + GPU smoke matrix + Phase-D baseline/R9 audit + GUI hybrid seeds; 6 lanes, exact-path commits; offline 1461/0/0/0 + BYTE-CHECK 24/24 + node/compileall gates):
- **Orphaned WIP landed** (docs-only commit): the prior pass's Â§16.7/Â§16.8 + INDEX line â€” validated against the committed dossiers (append-only, honest labels, no contradiction), prior author's voice preserved.
- **GPU smoke matrix** (the S1a configs' first GPU evidence, M4 pattern, one job at a time): biradial_keele GREEN (J 22.9837, 2086 dofs, 1301â†’2427 MiB), qtw_waveguide GREEN (J 37.4656, 1616, 1334â†’2104), lecleach_asym_odd FULL-RING GREEN (J 60.1446, 2815, 1337â†’3147); salmon_x_signed seed FAILS mesh_too_large (14,414 tris > 11,275; envelope overshoot 0.2201 pinned by the new test file), salmon_ripple12 seed FAILS (5,358 dofs > 5,000 screen cap) â€” both = owner-gated PROPOSALS (reseed / verify-tier), machinery healthy. Evidence `docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md`, bytecheck `tools/evidence_bytecheck_typology_smoke.py` (24/24 PASS + negative control).
- **Phase-D baseline settings**: `docs/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md` â€” five new configs' knobs/bounds/seeds verified per dossier + tier recipe + measured findings; **PROPOSAL-ONLY** default flips (rear_res_factor 1.5 AXI, balloon screenâ†’1024); objective-v3 DECISION CAPSULE for the owner (opt-in today; nothing flipped).
- **R9 audit**: `docs/research/typologies/R9_AUDIT_2026-10-25.md` â€” all 36 names walked (15 published / 18 labeled / 3 utility) + the do-not-cite ledger + five owner-gated PROPOSALS (lecleach_iwata_ar name, biradial_keele year suffix, C4 prose-vs-entries, Â§13.4 label hygiene, salmon_x pairing). No silent edits.
- **GUI**: /api/configs + generator_block/seed_params (verbatim); Compose hybrid captions from block shape ("hybrid â€” A + B"; rows kinds captioned "rows â€” {types}" after the orchestrator copy-fix) + per-pick seed preview (display-only, payload-fidelity pinned); objective-v3/mixed-key warn surfaces verified landed (4b42862). New test file: signed/ripple config pins (8/8).
- **Still owner-decided**: C4 catalog block (backend); the two smoke-matrix reseed proposals; the five R9 proposals; `examples/briefs/user/` gitignore-or-keep.

Local-only, added 2026-10-25 (evening; 3D render settings LANDED â€” owner screenshot â†’ fixer lane; brief_authoring 21/21 + node + compileall):
- **Landed**: persisted `hl-v3d-render` (surface satin/matte/metallic/studio Â· ridges on/thin/off Â· light Ã—0.5â€“2.0), shared `applyRenderLook`/`applyRenderControls` on both `init3d` and `init3dFrames`, clickable overlay chip (pointer-events:auto), immediate apply + global persistence ("swap easily in the 3D view or globally"); defaults = today's look byte-for-byte (existing captures/pins hold); disposal intact; no new hex; app.js untouched.
- **Honest limits**: WebGL cannot run headless â€” runtime paths source-pinned; chip interaction + cross-surface persistence in a live page await the owner's eyes-on pass.

Local-only, added 2026-10-25 (evening; S1a DRIVER PASS LANDED â€” oracle-decided/owner-directed; suite 1509/0/0/0; dry-run matrix 15/15; BYTE-CHECK 29/29):
- **Landed**: the brief family `{hifi_90x60, organic_rollback, lecleach_rollback} Ã— {1in, 14in, 2in}` (all f0 + v3, honest f0 derivations in-header); config research: `config.py` closure-aware biradial derivation (rm floored at r0 + tan(a)Â·L; the ONE owner-directed `widened_to_closure` exception, flagged + test-pinned) + the envelopeâˆ’2Ã—wall margin; reseeds (biradial L 195 + rm 210/230 bounds; x_signed stop 150/amp âˆ’0.15 â€” the 180Â° asymptote crossing; ripple12 stop 150; lecleach eps 0.20 + own family brief; elliptical stop 150 = the same recipe from my 4-test triage); C4 catalog (five entries incl. `symmetry: full`); decision record preserved verbatim (`S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md`) + research basis Â§16.9 pointer + NOTES_FOR_SENIOR.
- **Test-premise repairs (dated, nothing weakened)**: the salmon family's f0 briefs made three fixtures derivation-active â€” restored via derivation-inert fixture briefs with original assertions/tolerances intact; the salmon_elliptical derived-seed overshoot fixed by the measured reseed; derived-seed invariant drift (saddle 1.129 / x_shape 1.3025 report-only) disclosed â€” the seed-derivation card shows the clamps.
- **Solve-side**: the OWNER's own screen campaign (pid 14484, `user/7040use.yaml` Ã— the five families) ran against the repaired tree â€” the queued GPU re-smokes defer behind it / are superseded by its run evidence; J values non-comparable with the pre-repair matrix (new record groups).
- **Still owner-decided**: W8 the per-typology search-box audit (owner-directed, from the at-limit finding; bounds widen per-config only after the audit + cap checks); lecleach_iwata_ar naming (the owner's campaign runs it â€” the name decision remains open); stale user-brief descriptions (samonrip/75x35) â€” owner's files; `examples/briefs/user/` tracking decision.

Local-only, added 2026-10-25 (GUI S1a + G6 pass LANDED, re-grounded @ abcbebf; 114 offline tests green (+7) + compileall + node checks Ã—5; two disjoint fixer lanes, orchestrator reconciliation in place of Oracle per standing owner directive):
- **Landed (objective v3 / S1a)**: brief editor + Compose wizard expose objective version 3 ("scoring floor f0 â€” cov + dislope score only f â‰¥ f0"); run-detail KPI "Scoring floor" (target.f0_hz, present-only) explains the below-f0 mask; the seed-derivation card renders the K-law feasibility record from the run's committed config.yaml (per-knob derived/applied, `clamped to bound` pills, below-f0 solved-freq counts). The `J v3` badge is the already-generic `objective_version` renderer â€” verified, no edit.
- **Landed (G6 mounting)**: badge data verified live pre-edit on both WP12 enclosure runs (`solve_group.mounting` = the normalized block); `mesh_surface` now serves `mounting` additively from `mesh_meta.json`; `view3d.js` draws the dashed enclosure outline from the mirrored mesh's own bounding box (no invented geometry) + an on-canvas themed chip with the real depth/edge/margin values (chip is position:absolute over the canvas â€” the lanes' after-canvas caption would have been clipped by the fixed-height containers); compare gains the explicit "never rank across mountings" warn when `mixed_keys` includes mounting.
- **Verified-not-built**: axisymmetric-refuses-hv compat refusal already renders readably (campaign reader carries skip_reason; typologies compat reasons per brief) â€” pinned by a fixture test, no change needed. G5 (P6b owner gate), WP13 (owner-deferred), W7 (backend-gated), C4 catalog picker (pending backend) all stay gated.
- **Plan-doc addendum** appended to `docs/GUI_INTEGRATION_PLAN_2026-10-25.md` (Â§14): WP12/14/16/17 DONE, W6 landed, Â§3.8 `source_plug` naming resolved (GUI contract = `source_profile*` diagnostics), Â§3.11 mounting editor scaffolding superseded by the full-schema briefs editor.
- **Cross-lane note**: the backend stream's docs WIP (`docs/INDEX.md`, `docs/plan/12_RESEARCH_BASIS.md` Â§16.7/16.8) stayed unstaged/uncommitted here; `examples/briefs/user/` still untracked (owner decides keep vs ignore).

Local-only, added 2026-10-25 (GUI kill-current pass; owner screenshot markers; 107 offline tests green + compileall + node gates; orchestrator direct implementation per "just code it yourself"):
- **Kill run control for EXTERNALLY-started runs** (owner marker A: sidebar pill; marker B: Home running-card action row â€” both carry it now): two-step armed `â–  Kill run` â†’ `POST /api/stop-current` â†’ `jobs.stop_external()` kills exactly the pid recorded in OUR gpu lock file + its child tree, then gpu-clean (never an arbitrary pid; refuses while a GUI-started GPU job runs â€” the two stop paths never race; refuses killing the GUI's own pid). Safety contract changed by owner direction: the old "GUI only stops its own jobs" rule is superseded for the lock-holder pid our own lock file records.
- **Pill now ALWAYS visible**: idle renders a muted "no run in progress" indicator (owner: "I don't see it" â€” the old idle rendered literally nothing); external = `â–  Kill run`; stopped search = `â–¶ Resume search`; GUI GPU job = `â–  Stop`.
- **Removed**: the transient footer-holder guess (pre-observer) â€” the markers pointed at the sidebar pill and the Home card; plus the branch-order crash in `toolbarPillHtml(null)` (idle evaluated after the job read) â€” now node-tested.
- **Kill-safety contract on record**: the kill targets the pid+command OUR lock file records (whoever took our GPU lock wrote it), so the web GUI can never kill an arbitrary process â€” only the holder of our own lock; the lock file is bounded to the runs dir.

Local-only, added 2026-10-25 (GUI run-controls pass LANDED: Stop + Resume; owner-directed; 103 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per standing owner directive):
- **Landed**: Status-card Stop (three-state ownership rule: GUI-job two-step armed button / external-lock pill naming the pid / nothing; startup-window card), always-visible left-toolbar pill (app.js-injected `#nav-runctl`, 10 s poll, shared two-step arm, all four states), and the GUI `search --resume` plumbing (`resume: <run_id>` â†’ `search --resume <abs dir>`; config optional â€” the run dir's config.yaml is reused unless `--allow-config-change`; budget omitted = the run's own cfg.search.budget; mode passed from the run's record because the CLI's resume default is screen and rewrites run.json mode; `resume: true` bare-flag refused â€” the CLI contract takes a DIRECTORY).
- **Semantics on record**: Stop is a hard kill + gpu-clean (no graceful pause exists on Windows â€” "pause" = stop + resume, which is lossless for searches thanks to deterministic resume: cached rows replay free); budget is PER-INVOCATION, not auto-remaining â€” deliberate top-ups stay an owner action, never a pill side-effect (the pill guards budget-exhausted runs as finished); resumable markers = run.json status "running" (stale after GUI stop â€” no "stopped" value exists) / "interrupted"; "finished"/"aborted" not auto-resumed.
- **Honesty engineering on record**: every resume previews first (`POST /api/preview`) and the confirm click is blocked unless the previewed argv carries `--resume*` ("â€¦would start a FRESH search, not aResume; nothing was started"); resume id sourcing = the stopped job's own log_tail, validated against /api/runs (exists + budget not exhausted); Launch-row Resume deliberately skipped (Launch's 2 s re-render wipes a row-level arm mid-confirm â€” the always-visible pill covers it).
- **Owner visibility note**: the run-controls work was tree-uncommitted when first reported invisible (editable install serves static live but the Python process needs a restart for jobs.py) â€” after this commit, restart the GUI (`tools/launch_gui.ps1`) and the pill appears in the left toolbar on every page.

Local-only, added 2026-10-25 (GUI deferred-provenance pass LANDED, grounded @ 26a1de1; 93 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per standing owner directive):
- **Landed** (the four deferred items from the CAD-hold deferral): CAD STEP inventory projection onto the chip contract from `mesh_meta.json["cad"]` (verified against the CURRENT step_build keys incl. the WP12 WIP's non-change to the provenance block; sidecar wins; band{k}/meta fallback for WP8 designs added beyond the original spec), `cad_route` solve-group marker via the best-objective-row proxy, `cma_files` run_detail key + restart-card direct log chips, and the `source_profile_alpha` fingerprint pin test.
- **Verified-not-stale**: run-export STEP naming re-confirmed on disk (`<cfg.name>_<rank|seed>_<hash12>.step`; matcher covers both; the listed `STEP_NAME` contract unchanged) â€” the earlier draft regex would have missed `seed` exports.
- **W6 balloon integration verified already-wired** (the balloon commit's own route/button/back-links) and pinned by a test; zero overlap with the provenance/chips regions.
- **Future G6 note**: the in-flight WP12 mounting WIP was read read-only (brief.mounting normalized block; `mounting_key()` freestanding-safe; `mesh_meta.provenance.mounting` echo) â€” the mounting badge/preview builds when WP12 lands; nothing pinned against uncommitted code.

Local-only, added 2026-10-25 (docs pass: BL balloon research recorded + density TODO + CAD deferral; docs-only, no code touched):
- **Boundary Lab balloon rendering/resolution/frequency facts recorded** as the owner-directed append-only Â§12 in `docs/plan/12_RESEARCH_BASIS.md` (sources: committed BL extraction `research/boundary_lab_0.5/bl_inventory.md` + the W6 source recon; GPL-3.0 attribution carried): BL freq defaults 41 log-spaced 200â€“20 kHz (+ van-der-Corput non-monotonic GUI ordering quirk), balloon = equal-area Fibonacci sphere at `round(41253/angleÂ²)` points from a 0.5â€“15Â° precision dial (2.5Â° default â‰ˆ 6 600 pts), DI as a plain mean over the equal-area balloon, dB-to-radius blob rendering with tubed isobars/radar slicer/octave-smoothed slice.
- **W7 priority recorded** (`docs/NEXT_DEV_PRIORITIES.md`, mirrored in `NOTES_FOR_SENIOR.md`): raise verify/final-tier density â€” `balloon_points_verify` 512â†’1024â†’2592 ladder into 1 000â€“6 600, verify freqs 25 â†’ ~41 log-spaced â€” gated on the M3/WP5 Î”DI ladder + 8 GB GPU cost disclosure; feeds the W6 balloon view.
- **CAD deferral on record** (owner directive "GUI-only round"): my CAD reader lane cancelled, its partial code removed from the working tree (verified: `gui/data.py` diff carries only the parallel agent's balloon work); deferred design preserved verbatim in `NOTES_FOR_SENIOR.md` (cad block real key names, filenameâ†’hash regex, `cad_route` proxy, cma-files direct-chip listing). The backend M5/M6 CAD stream belongs to the parallel orchestrator session â€” its live edits in `config.py`/`design/families.py`/`mesh/build.py` untouched; the STOP record in NOTES_FOR_SENIOR is the cross-session signal.
- **Encoding-hygiene lesson**: PowerShell 5.1 `Add-Content` writes the ANSI default codepage â€” it silently corrupted NOTES_FOR_SENIOR.md's UTF-8 (cp1252 bytes, lossy special chars); caught by byte-level decode check; restored to HEAD (the append-only rule protects committed blocks only) and re-appended ASCII-safe via explicit-UTF-8 Python. All doc files byte-verified valid UTF-8 before commit.

Local-only, added 2026-10-25 (GUI 3D pass: inline run-page 3D + 3D evolution time-lapse LANDED; owner requests; 72 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per owner directive):
- **Commit-hygiene disclosure**: `599997d` (the GUI 3D commit) unintentionally swept in the M5B lane's staged-but-uncommitted files (35 files) â€” the M5B landing was mid-shared-index at commit time; its authoritative record is `94243df` + its CONTINUITY entry + evidence (bytecheck 33/33). Post-sweep tree verified coherent: offline suite **1335/0/0/0** at HEAD (`runs/m5b_rectify/suite.xml`), `test_mesh_pin` RESOLVED. Lesson recorded: verify `git diff --cached --stat` per-file before every commit when lanes share an index.
- **Landed**: inline ~300px 3D on run detail (lazy fetch, shared persisted shadows toggle, full 3D tab unchanged), `data-v3d` disposal sweep in route() + `isConnected` source-bails (no renderer leaks), `view3d.js::init3dFrames` frame player (union-bounds camera, lazy per-frame geometry build + hot-swap, decimation disclosure, 2D CDN fallback), evolution "3D time-lapse" with the disclosed RULE3D (3D âŸº improvements-only; "every candidate" stays 2D), `GET /api/evolution/<id>/frames3d` (shared `_improvement_flags` rule with the 2D reader â€” the two players cannot disagree; cache keyed incl. cap + per-frame mesh mtimes; mesh-less improvements SKIPPED + disclosed in `note`).
- **Open small items**: (a) frame count gaps between 2D "every candidate" and 3D are explained on screen by the reader's skip note â€” if the owner later wants mesh-less improvements rendered as interpolated ghosts, that is new work; (b) theme/resize re-render resets evolution playback to 2D (pre-existing control-state behavior; disclosed); (c) animation frames are improvement-chain only by design (every-candidate 3D would fetch every evaluated design's mesh â€” a deliberate honesty/payload trade).

Local-only, added 2026-10-25 (GUI integration plan G1-G4 phase LANDED; owner decision to start now; 63 offline tests green Ã—2 + compileall + node gates; orchestrator review in place of Oracle per owner directive):
- **Landed**: provenance badge strip on run detail (single source `solve_group`, tooltips = key path, f11 caveat conditional), restart schedule card + QD provenance caption (atlas canvas untouched), compare solve-group banners + DI-guard twin, `verify` GPU job kind (engine-true directory contract), C-5 raw pycma log serving (strict regex + containment), C-2 compare fingerprints (backend + freqs_hz identity always; WP16/WP12 keys read defensively for when their lanes land).
- **Deviation on record**: C-1's `step_files` stays a byte-identical string list (frozen test) â€” inventory rides the additive `step_files_detail` [{name, inventory|null}]; the GUI plan Â§5's "entries gain inventory" wording is thus implemented additively. `qd_algorithm` joined the fingerprint beyond Â§3.9's parenthetical (mixing CMA vs CMA-ME warns â€” judged correct, disclosed). The plan's "`GPU_KINDS` gain nothing" line predates G-1 and is superseded by the phase spec.
- **Open small items left to later passes**: (a) restart-log direct file chips need a file listing endpoint (C-5 serves files only; the card caption names the URL shape today); (b) STEP-inventory sidecars will populate chips only when the WP14 lane deploys its writer (plain-chip absence is the honest default); (c) `mounting`/`source_profile_alpha` fingerprints fire when WP12/WP16 land their config keys.

Local-only, added 2026-10-25 (GUI Compose wizard pass; owner UX direction "typology first"; LANDED on #/compose â€” 48 offline tests green, compileall + node --check clean, orchestrator review in place of Oracle per owner directive):
- **`#/compose` wizard landed** (app.js +534/âˆ’16 + one nav line + tests): typology-group multi-select first (per-group select-all; disabled configs visible-marked-unselectable with the engine seed-gate reason; uncatalogued configs selectable only as the sole pick, auto-deselected with a stated reason otherwise) â†’ brief step reusing the committed editor (new-from-scratch / typology brief_file / existing-brief-as-is; save-before-launch gate mirrors `jobs._repo_file` refusing non-existent paths) â†’ run step (1 config: dry-run/run/search; 2+: campaign tier + --families verbatim; preview shows the exact command; gpu_busy disables launch with server's reason; job id links to #/launch).
- **Pinned honesty finding**: campaign `--seeds`/`--budget` exist in the CLI but `jobs.build_argv("campaign")` reads only brief/families/tier â€” values passed via /api/jobs would silently vanish; the wizard therefore ships NO override fields (engine-default budget captions shown) and `test_campaign_budget_and_seeds_are_not_gui_plumbed` pins the pairing. If the CLI flags are ever plumbed into build_argv, BOTH must change together.
- **Disclosed UX behaviors on record**: re-picking a brief source restarts the editor (unsaved edits replaced, not merged); verify_only briefs remain selectable as existing-brief with the "only verify --brief" warning; family compat is never re-implemented client-side â€” the preview command + per-entry engine skips are the truth.
- **Open small item**: campaign seeds/budget plumbing into `jobs.build_argv` (owner-gated when wanted; the tests above are the guardrail).

Local-only, added 2026-10-25 (GUI briefs pass = c7d2bbf + hardening 95306db; user request + owner UX direction; editor LANDED â€” 39 offline tests green at the editor commit, 48 after the wizard; compileall clean):
- **Brief-authoring editor landed** (app.js + tests/test_gui_brief_authoring.py): New-brief-from-scratch, start-from-typology picker, every `load_brief` schema key exposed (symmetry/throat_angle_policy/objective/verify_only/description/z_min/freq_weights), payload fidelity (nothing silently dropped), and the GUI-invented 5500 Hz band clamp REMOVED (blamed to 77aac53b with no authored intent; the 8 GB dof-cap hardware note stays as an always-visible hint). Consequence worth knowing: band_hi can now be saved at any value (e.g. 12 kHz verify-only briefs are created from the GUI); search/run/campaign refuse verify_only briefs regardless â€” server-validated, GUI never clamps.
- **RESOLVED by the Compose wizard pass (block above)**: the typology-first wizard owner direction â€” shipped as `#/compose` in the next commit; campaign seeds/budget plumbing remains the only open small item (see above).
- **Post-commit Oracle read (returned after c7d2bbf was pushed; verdict GO-with-fixes, all applied in the follow-up commit 95306db)**: remaining suggestions on record â€” (a) `examples/briefs/user/` is untracked and NOT gitignored: the GUI creates real user briefs there at runtime; a `.gitignore` entry (or an explicit keep-with-sample decision) belongs to the 03-owning lane; (b) `z_min` input accepts values above 1 (spinner-only bound; `Target.from_dict` does not bound it; harmless, hint explains semantics).
- **Oracle waiver on record**: owner directive 2026-10-25 "no more new Oracle passes this round" â€” the editor's verification was the pasted test output + orchestrator diff read + live schema-fidelity save checks; the already-in-flight read DID land post-commit and its verdict + fixes were incorporated (see the 95306db commit + CONTINUITY).

Local-only, added 2026-10-25 (GUI 3D-quadrant fix pass; user-reported "3D views render just a quarter slice"; fixed + tested â€” tests/test_gui_mesh_quadrants.py 6/6, tests/test_gui.py 35/35, compileall clean):
- **GRID route writes no `mesh_meta.json`** (by design, `mesh/build.py:273` build_mesh docstring refers to the GRID route): the 3D route (`gui/data.py::mesh_surface`) previously defaulted those designs to `quadrants="1234"` (full model) and so rendered the raw meshed wedge instead of reconstructing the full horn. FIXED GUI-side (fallback chain meta â†’ search.ndjson row â†’ config.yaml â†’ "1234"); the DATA-SIDE follow-up stands open: the GRID route SHOULD write mesh_meta.json for provenance parity (`search/evaluate.py:500-516` logs absence only at debug) â€” ask for the grid lane.
- **2D mouth doubling covers only `'1'`** (data.py:873-884): for GRID half-models ('14'/'12') the mouth/front-view outline shows the meshed half only â€” same semantics class as the 3D bug; small follow-up, NOT fixed here.
- **Briefs page: user request RESOLVED (delivered across the briefs + Compose wizard passes, blocks above)** â€” create a NEW brief from scratch with asymmetric envelopes (wâ‰ h legal for every symmetry value â€” the engine only refuses axisymmetric briefs with unequal COVERAGE), symmetry control with the verbatim server rule shown, and typology-first picking; the confusing "symmetric horns" behaviour of the old editor was the missing symmetry control + the silent axisymmetric-coverage carry â€” both fixed.

Local-only, added 2026-10-25 (M5B pass; evidence `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md`, byte-check `tools/evidence_bytecheck_m5b.py` **33/33**; nothing flipped â€” every new key opt-in, absent = bit-for-bit):

**DEFERRED WP14 physics (owner ruling 2026-10-25 â€” "table the multicell horn thing for now; landing the category is cool"). The category IS landed (CADâ†’STEP route, tests green); THE PHYSICS IS NOT TRUSTED YET. The full resume recipe:**
1. **Focal-pair gate result (preserved, NOT to be used for trust decisions):** same mesh both arms (byte-identical `mesh.msh`, `mesh_hash 79c17524af5d`, 4501 dofs, 12 freqs 500â€“4000, 73-pt balloon): CUDA J=172.566 (17.3 s) vs CPU near+double J=471.984 (314.1 s); compare = **on-axis 11.28 dB / DI 14.59 dB / bw_v 159.1Â° max diffs** (re-captured `runs/m6_fork/compare_focal.log`) â†’ official gate **NOT ALLOWED** (bar 0.2 dB) on this fixture. bw_h = 180.0Â° saturated in BOTH arms (no information).
2. **ora-2's diagnosis (the reframe):** (F1, dominant) the fixture's mouth is a rigid `wall` and the driver is the REAR disk facing âˆ’z â†’ the exterior BEM solve measures **diffraction around a closed body, not horn radiation**: throat impedance matches a FREE UNBAFFLED DISK within 2â€“8% in BOTH arms (analytic (ka)Â²/4), DI is NEGATIVE in both arms (4Î» apertures cannot; self-shadowing signature) â€” **no far-field metric of this fixture is horn evidence until the mouth radiates** (open-mouth wall-shell topology like the OSSE lane, or an explicit mouth BC). (Gate restatement) the 4 kHz gate is unanswerable on this mesh â€” the validator's own global ceiling is **2891.68 Hz**; re-gate ONLY in the valid band and ONLY on non-threshold metrics (bw_v's 180Â° readings are âˆ’6.0206 dB threshold flips, verified `metrics/polar.py:17-34`; the 1287 Hz valley sits 1.05 dB from the crossing). (Attribution, ranked) #1 = arm-A's **near-correction omission** over ~O(10âµ) septa/second-ring pairs (the library's own refusal names this silent-wrong mode) â†’ **WP17 stage 1 (now LANDED + GPU-validated) is required, not optional, for any multicell GPU screen**; #2 mesh under-resolution near the driver (walls valid 3085.11 Hz vs 4000 requested; DistMax-400 rebuild = 12,694 tris / 6,349 dofs > the 5,000 screen cap â€” cap raise owner-gated, NOT made); #3 metric amplification (bw_v flips + dislope 597 vs 98); #4 FP32-vs-FP64 unlikely primary; #5 per-frequency-vs-single-call granularity unresolved (arm D never ran).
3. **Resume recipe (in order):** [a] fix the fixture topology: the mouth must radiate (export with the mouth `wall` faces REMOVED from the solid â€” open aperture â€” or an explicit treatment; re-prove closed/manifold + the solver's exterior contract for open-aperture geometry per the enclosure route); [b] optionally rebuild the mesh at DistMax 400 mm; [c] run the four CPU arms (plain-single, plain-double, near-single, near-double per-freq) on the SAME mesh + band-restricted (â‰¤2892 Hz) per-frequency table (on-axis/DI; NOT bw_v/dislope); [d] IF #1 attribution confirmed â†’ CPU-near arm re-validated vs the analytic/crosscheck references; [e] then the real gate: CUDA-fused-with-near (WP17) vs CPU with near, < 0.2 dB in the valid band â†’ ONLY THEN are multicell GPU screens allowed. Evidence preserved: `runs/m5_wp14_focal/*` (4 configs: cuda / cpu_near / cpu_plain [arm C ran â€” read `cpu_plain.log`; NO conclusions drawn], cpu_near_single [arm-D config only]) + the 2 focal run dirs `20261025T112316Z-screen-b22f31` (cuda) / `20261025T112519Z-screen-c6b2d8` (cpu near) + `mesh_meta.json` frequency-validation blocks + `run.json` bodies (cad echo + grid-honesty verified `available:false` in both arms).
4. **WP17 stage 2** (fused CUDA + per-image symmetry near caches): future fork work, refused by design until built (stage 1 = no-symmetry only).
5. **`near_correction*`/`solve_precision`/`source_profile_alpha` are NOT echoed per-row into `Response.meta`/records yet** (the GUI-planning pass's G-3/G-4 gap): the keys ride solve-spec `extra` (hash-distinct) and the WP16/17 diagnostics prove the path in the result â€” but per-row provenance parity remains a small follow-up lane (echo the set keys into the record's provenance solve block like `mesh_policy` does). GUI reads config.yaml meanwhile (per the GUI plan's disclosed contract).
6. **WP16/17 fork branches + pin state (landed, for reference):** `hornlab-search/wp16-source-profile` @ `f4ef05c`, `hornlab-search/wp17-cuda-near` @ `760a1ec` (test-env tip `a40a204` = CUDA@6.2.0 in the JULIA TEST project only) â€” pin on main = `760a1ec` (installed == pinned; `test_mesh_pin` green). Fork hosted: github.com/llevaachingada/hornlab-beat-bem (public, GPL-3.0). The pre-existing dev-pin note (`dev/fused-cuda-pin` @ `65c03de`) is SUPERSEDED by the hosted pin.

Local-only, added 2026-10-25 (GUI-integration planning pass; deliverable `docs/GUI_INTEGRATION_PLAN_2026-10-25.md`; docs-only, no GUI code, no GPU, nothing flipped):
- **In-flight WIP disclosed at planning time (owner lanes, untouched by this pass)**: WP14 + M4-debts WIP uncommitted on main (`config.py`, `solve/beat.py`, `gui/data.py` seed-gate memoize, `mesh/grid_build.py` EOF mesh-cache sketch, `pyproject.toml`, `tests/conftest.py`, test files, `examples/typologies/salmon_saddle.yaml`; untracked `tools/cad/` + `tests/test_cad_multicell.py` landed in-tree mid-pass; plus GUI-runtime untracked `examples/briefs/user/7040.yaml` â€” disclosed, left alone). FORK STATE RE-VERIFIED mid-pass: WP16 **committed** (`f4ef05c` on `hornlab-search/wp16-source-profile`, 7 files) and **pushed** to `ourfork/hornlab-search/wp16-source-profile` (github.com/llevaachingada/hornlab-beat-bem); fork checkout now on `hornlab-search/wp17-cuda-near` (at f4ef05c, zero WP17 commits) with fresh uncommitted WIP in 3 files â€” the WP17 lane's scope; owner gate B ("fork hosting") is an owner call, not asserted. Lanes own their commits (fix-3/fix-6 pattern; work lands late).
- **G-1** â€” `verify` missing from the GUI job allow-list (`gui/jobs.py:113-141`): verify runs are only reachable via CLI today; GUI plan G4 adds the (GPU) kind, contained to the allow-list + tests.
- **G-2** â€” `run.json.restarts`/`qd` written since M5 but never read by any view; GUI plan G2 surfaces them (reader additive keys + restart strip + raw `cma/restart_k/*` download route).
- **G-3** â€” `solve.near_correction*`/`solve_precision` ride `SolveSpec.extra` (solve-hash-distinct) but are NOT echoed into `Response.meta` (beat.py WIP emits only cuda_fused/mesh_policy/source_motion): per-row provenance parity gap; GUI reads config.yaml meanwhile, per-row echo is a WP14-lane ask.
- **G-4** â€” handoff's `source_plug` provenance field does NOT exist (rg = 0 hits): WP16 lane must add it to dataset `provenance` or confirm the GUI keys on the fork's `source_profile*` diagnostics; GUI plan adopts the diagnostics as contract (no invented keys).
- **G-5** â€” WP17 condition: fused-CUDA near-corrected records need a discriminative near-correction-path diagnostic (assembly_path="fused_cuda" alone is ambiguous with WP15); lane note, not GUI work.
- GUI-integration plan itself: P5 W4 `compare --bar` judge still MISSING in cli.py (planned hook, W4 owner-gated); WP6 demo-sheet searches confirmed ABANDONED (owner: 12 kHz capability banked via WP15) â€” the plan does not carry it.

Local-only, added 2026-10-25 (M5 WP11 pass; evidence `docs/evidence/M5_WP11_2026-10-25.md`; nothing flipped â€” all new keys opt-in, absent = bit-for-bit):
- **VRAM per-job baseline/peak MISSING for the first three GPU screens** (ipop/bipop/cma_me): the screen lane ran the jobs correctly (durable run.json artifacts carry their proof) but never started its external VRAM sampler; only the fired-restarts screen has the [measured] pair (baseline 430 MiB / peak 2305 MiB). M4 precedent (peak-per-job disclosed MISSING) applies; re-runs cost ~4 min GPU each on FRESH cache dirs (owner's call).
- **QD atlas browser render not exercised live**: route tests (34/0/0) + reader tests + `node --check` cover the served contract; a one-minute manual GUI check on `runs/20261025T080717Z-screen-fd13a7` (has atlas artifacts) remains owner-side.
- **`tools/launch_gui.ps1` â€” untracked stray predating this pass** (present in the tree before the first WP11 lane): NOT committed, NOT deleted; owner decides commit/delete/leave.
- **`qd` extra transitive weight**: `ribs==0.12.0` pulls numba/pandas/scikit-learn â€” confined to the optional `qd` extra; noted at Oracle review (exact pin justified: archive semantics are version-sensitive).
- **BIPOP schedule divergences from pycma documented in `_RestartSchedule` docstring** (small-run maxiter cap omitted â€” the global eval budget governs; our `max` counts all restarts incl. small ones, pycma's counts non-small only): behavior deliberate, next reader diffing against pycma should read the docstring first.
- Resume determinism caveat (inherited, not regressed): `solve_failed` rows are never memoised â†’ a resume after a solver-unhealthy abort re-solves them and may legitimately diverge from the uninterrupted replay (docstring caveat per Oracle; behavior unchanged from cma.py).

Local-only, added 2026-10-25 (M4 pass; evidence `docs/evidence/M4_SMOKE_2026-10-25.md`; Proposals owner-gated â€” nothing flipped): 
- **P-M4-1** â€” matched-sampling GRID-vs-FREEFORM equality run before the strict WP10-step-5 J-equivalence claim: the zero-modulation compare (grid_ellipse 1298 dofs vs conical 1319 dofs) is between two DIFFERENT design hashes (`d0dc9b5a8999` vs `f8b94e104f80` â€” same yaml seed, different surface authorings); measured deltas â‰¤ 0.110 dB on-axis / â‰¤ 3.45Â° bw / â‰¤ 0.071 dB DI; construction-level equality is proven offline (closed forms â‰¤ 1e-9); the run-level equality needs GRID n_phi/n_s matched to the FREEFORM mesher segmentation (owner-gated).
- **P-M4-2** â€” rows-route `stop_deg` bounds [120, 240] include graded-infeasible stops near the Salmon 180Â° cap-area asymptote (the march refuses 180Â°; seeds hand-tuned to avoid the zone; lecleach_f90 feasibility sweep: 57/224 knob combos graded `_generator_error`). Consider narrowing (owner gate).
- **P-M4-3** â€” legacy internal rows kinds (`lecleach_mod`, `lecleach_ar`, plain-lecleach `g_r_lip_mm`) remain in `design/generators/grid.py` unlisted/unconfigured (the shipped contract is the list-harmonic kinds + iwata_ar/toroidal_rollback); a cleanup pass may delete them.
- GRID-route mesh-cache absence (documented `mesh/grid_build.py`): every GRID/rows evaluation re-meshes (screen-size meshes are 0.2â€“1.2 s â€” acceptable for smokes, real for searches); a cache keyed on the design recipe + mesh hash is the follow-up if GRID enters search campaigns.
- GRID STEP export unwired (`export_step` â†’ `families.to_mesher_config` KeyError on a grid design; contained per-design by the CLI catch; failure = clean "FAILED: KeyError" line); SHOULD: a clean refusal raising `GeometryInvalidError` instead.
- GUI `list_configs` latency: the data-driven disabled gate materializes every config's seed per refresh (rows marches are brentq loops â€” saddle ~25 rows); memoize on (path, mtime) + pin the gate with a test.
- salmon_saddle emits the mesher outer-shell clearance warning (wants 3.866 mm on 6 of 33 rings, holding at 5.197 mm) â€” inner acoustic surface unaffected; seed uses epw 6 to fit the 5,000 screen cap.
- Final offline suite 1194/0/1/0 â€” the single failure is the intended `tests/test_mesh_pin` tripwire (installed beat-bem fork `fa99ee594087` vs main pin `38544d214ba2`); +226 tests additive-only; never hand-fixed (resolves when the owner hosts the fork pin, docs/FORKS.md).

Local-only, added 2026-10-24 (GUI contrast/visibility pass, docs-only): the local web GUI's rendered dark-theme state fails WCAG in spots â€” primary button text 2.07:1 on `--accent`, hairlines 1.36:1, chart micro-labels dim, `wallSection` "filled" legend a no-op (fill â‰¡ plot bg, dashed start profile ~90 % occluded), 3D horn shadow side merges into the canvas, isobar white contours lost on warm bands, budget-over-limit unflagged, theme-toggle first-click no-op + stale SVG after toggle. Full measured list + six-phase fix plan (tokens, theme boot + `?theme=` capture, charts, wallSection, 3D light-gray horn + lighting/shadows, semantics/tests): `docs/GUI_CONTRAST_PLAN.md` (designer-authored, Oracle-reviewed â€” all MUST/SHOULD/NICE applied). Owner approved implementation 2026-10-24: Phase 1 (tokens/type tiers) landed + verified (`tests/test_gui.py` 30/30; both dark CSS blocks in sync); Phase 2 (theme-boot first-click fix + `?theme=` capture override + async route/scroll/filter restore on toggle) landed + verified (30/30; both themes pixel-checked via the override); Phase 3 (chart contrast: two-pass isobar halo contours, brighter dots/hlines, `--label` target lines + legend swatches, seed strokes 1.7) landed + verified (30/30); Phase 4 (wallSection redesign: even-odd wall-band fill, dashed-start last, throat dots, plain labels) + Phase 5 (3D light-grey horn, 4-light rig, themed canvas, toggleable shadows + light-tone wireframe retained per owner) landed + pixel-verified in both themes. Phase 6 (over-budget flag + literal text at all three readouts, rank/leader/noise text badges, timeline-dot shape+color redundancy, `evolution.js` in the syntax gate) landed + verified (`tests/test_gui.py` 31/31). ALL SIX PLAN PHASES IMPLEMENTED 2026-10-24. Unrelated observed failure: `test_mesh_pin` fails on the WP15 fork lane's in-flight install (hornlab-beat-bem `fa99ee594087` vs pinned `38544d214ba2`) â€” outside GUI scope, that lane to reconcile per FORKS.md. No GitHub issue opened.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

Local-only, added 2026-10-13 (local GPU box, data digest): `osse_baseline` bound-pinning follow-up â€” **corrected per senior review** â€” the best designs sit at the LOWER bound of `n` (2.0; top-6 6/6 â€” the strong signal), while `q` is attracted to its lower bound (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but is top-6 0/6 (an earlier "5/6" here was the in-flight 13:40 snapshot, not final data); `a_deg`/`exponent` are interior. The mesher only needs `n > 0`, `q > 0` while `s != 0`, so a future widening of `n`/`q` is indicated (CP-8b handled `a_deg`/`exponent` only). Evidence: `docs/evidence/CP-8c_data_summary.md`.

Local-only, added 2026-10-13 (local GPU box): CP-8 evidence lives in `docs/evidence/` â€” verbatim checkpoint output (`CP-8a.md`, `CP-8b.md`, `CP-8c_*.md`), live monitor logs (`logs/`), and `manifest.sha256` (SHA-256 + size of the metadata-layer artifacts (run books/ndjson/store JSONLs; label .npz covered by dataset verify, not bit-identity)). Raw `dataset/`, `runs/`, `cache/` stay local and gitignored by design (dataset already 180.6 MB at 1128 records; CP-5 projects 0.78-1.4 GB at 10k) â€” verify against the manifest instead of committing blobs; use a data branch/release asset to move raw data.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): CP-8a PASS (480 offline + 18 GPU-marked tests, doctor 10/10, outputs pasted); CP-8b PASS (bounds widened a_deg 25->5 / exponent 2->1, rerun no longer pinned); CP-8c CLOSED - PARTIAL on the literal criterion, verify OK: four runs done - osse_baseline 1500 (best J 6.106 vs seed 22.592, -73%), icw_termination 800 (12.201 vs 55.736, -78%), freeform_hv 722/800 on cma: tolfun (30.543 vs 33.309, -8.3%, low-diversity plateau, 3 searchable keys), throat_adapter 400/400 with ZERO failures (5.983 vs 9.159, -35%); final dataset 3556 records / 8 shards / 587.2 MB, dataset verify OK (0 bad, 0 bad arrays); families OSSE 2034 + ICW 800 + FREEFORM 722 = 3 of 4 (R-OSSE has no example config; the literal all-four-families criterion is unsatisfiable - amended criterion in evidence). Campaign wall ~14.9 h, GPU solve 13.0 h. CP-8d next (indicative): OSSE pool kept 1501 of 1634 -> held-out 225 < 500 -> expect GATES REFUSED (indicative only); propose runs with --allow-unvalidated. **CP-8d OUTCOME (2026-10-14 ~01:10 local): FAILED â€” GATES FAILED twice** (epochs 300: topk 5/20 + bw_mae 2.110 fail; epochs 600: 5/6 gates pass incl. Spearman 0.9861 / topk 15 / bw 1.704 / di 0.232 / inv 0.952, but monotonic_flips 1 (needs 0)); held-out 285 < 500; model NOT used (propose/round not run); hard rule 8 stop + NOTES_FOR_SENIOR `2026-10-14 cp-8d` block (questions: approve ~10.2 h OSSE top-up to clear the 500 floor; classify monotonic_flips=1). Tables: `docs/evidence/CP-8d.md`. **Flip diagnosis (addendum)**: seed-stable 2-4 % flip rate (seeds 0-5: flips 1/1/1/2/2/2 of 50); three causes â€” invalid-transition degeneracy, genuine 1-3.7 J undulation on fully-valid lines, and flat-tolerance wiggle sensitivity (tol 0.021-0.023 J); marginal, not a hard defect; NOTES cp-8d ADDENDUM wants owner rulings on sweep-tolerance semantics / invalid-crossing category (thresholds untouched).

Local-only, added 2026-10-13 (local GPU box, icw run): (a) ICW mesher warning "outer wall self-intersects / normal flip near azimuth row 0" â€” 24 warning LINES, all timestamped 17:06:25, plausibly ONE design of 800 (per-design attribution not recorded); zero new after 17:06; rows still validate and the acoustic (inner) surface is unaffected â€” caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. (b) ICW bound-pinning follow-up: best designs fully pinned at the `hold_end` LOWER bound (0.55, top-6 6/6) and 4/6 near `kappa0` lo = 0.0 (median 0.0016); candidate `hold_end` widening subject to the repo's `hold_start < hold_end` rule + mesher validation. (c) OSSE bound-pinning follow-up from run 1 â€” **corrected per senior review**: `n` fully pinned at lo 2.0 (top-6 6/6; the strong signal); `q` strongly attracted to lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but top-6 0/6 (an earlier "5/6" was a stale in-flight snapshot); mesher needs only `n>0, q>0` while `sâ‰ 0`. Both (b)/(c) recorded, NOT changed mid-campaign.

Local-only, added 2026-10-22 (local merge lane, glm-5.3 oracle pre-merge review): follow-ups recorded, none blocking the merge â€”
(a) `cli.py::_cmd_compare` would raise an uncaught `IndexError` (`ma.freqs_hz[0]`) on the unrealistic empty-frequency-set edge (cosmetic traceback risk only);
(b) the `exponent` alias resolves to the FIRST superellipse station only â€” pre-existing design-layer semantics; document in config-template comments before any future multi-station FREEFORM config;
(c) `docs/BOUNDARY_LAB_*` + `docs/research/boundary_lab_0.5/` are PROPOSED research awaiting user approval â€” do not treat as accepted backlog.

Local-only, added 2026-10-22 (local merge lane, user request): GPU-run summary layer committed at `docs/evidence/runs/` â€” for each of the 7 local `beat_cuda` run dirs (seed screen d627d9, resume smoke 7e6e5b, CP-8b smoke 9e5a5c, CP-8c runs 1-4 ca15be/6bdcbd/ff569c/852be3), the summarized metadata+log layer (run.json, config.yaml, best.json, search.ndjson, cma/*, verify; 108 files, ~16.6 MB) is now IN GIT (previously only in gitignored `runs/`), with index README + `runs/manifest.sha256`. Raw `designs/` blobs, `dataset/`, `cache/` remain gitignored by design; this is an approved exception to the evidence-README "never the data itself" rule (noted in `docs/evidence/runs/README.md`).

Local-only, added 2026-10-13 (senior read-only review of CP-8c/CP-8d readiness, glm-5.3 oracle, branch claude/wave-3-implementation-review-2dk4qe):

**(a) CP-8c yields THREE families, not four** â€” `examples/throat_adapter.yaml` is `family: OSSE`,
so after run 4 the store holds OSSE+ICW+FREEFORM and R-OSSE stays 0. HANDOFF_LOCAL Â§5's pass
criterion ("all four families present") is unsatisfiable as planned, and `stats()`'s family
warning (fires only when one family >80%) will never flag a MISSING family (OSSE â‰ˆ56% after
run 4). Fix: re-scope the criterion to "OSSE+ICW+FREEFORM present; R-OSSE deliberately absent
(no example config)"; add `missing_families` to `dataset stats` (store.py:441-446, 658).

**(b) CP-8d misreading guards (14-item list in the review)** â€” (1) CLI must distinguish
"GATES REFUSED (indicative only): held-out 225 < 500" from "GATES FAILED" (cli.py:675 vs
gates.py:115); (2) `round_report`'s `random_true_J` = CMA gen-0 samples, not random, and J=1000
penalty rows inflate medians â€” pass solved rows only and print the baseline provenance
(ismo.py:56-72); (3) print exploit vs explore medians separately; (4) print the proposals'
parameter spread (the 30 exploits are near-clones of one basin); (5) freeze `pred_J` from
proposals.json and record bundle/config_sha/store count at train; (6) write `ismo_round1.json`
into a run dir and paste it into a new `docs/evidence/CP-8d.md`. Items overlapping #13
(skipped-count printing, verdict persistence, dedupe-by-hash before the holdout split) LANDED
in commit e0b9b61 â€” none of CP-8d's numbers are quoted before that.

**(c) Data-pipeline integrity at 10k â€” IMPLEMENTED (commit 11304f6; full offline suite 498 PASS)** â€”
`verify_store` now checks metric array shapes vs each record's own `solve.freqs_hz` (reported as
`bad_arrays`; `dataset verify` exits 1 on `bad` OR `bad_arrays`); `dataset stats` gained
`n_duplicate_designs` + a `missing families` line in `stats_report` (R-OSSE expected); `search
--resume` compares `run.json["config_sha"]` and REFUSES on mismatch unless `--allow-config-change`;
`surrogate train` splits `GATES FAILED: <names>` from `GATES REFUSED (indicative only): held-out
<X> < 500`; new `surrogate round` subcommand solves proposals through the normal `evaluate` path
into a fresh run dir with its own ndjson and writes atomic `ismo_round1.json` (report + rows +
`random_true_J` provenance + exploit/explore medians + exploit spread + store counts + bundle gate
status + config_sha). `manifest.sha256` README reworded (metadata layer only) and line 3 indent
fixed for `sha256sum -c`.

**(d) Evidence corrections** â€” CP-8c_osse_baseline.md "5/6 near q lo" contradicted its own table
(fixed: top-6 0/0, median 0.9033 â€” stale snapshot claim); the 13:11 snapshot's "seed J 22.07" was
the smoke seed (fixed: 22.592); ICW warning "~a few % of designs" unsupported (fixed: 24 lines,
one timestamp, plausibly one design of 800); `data_summary.json` `generated_local` lacks a
timezone (add `generated_utc`).

CP-9a..d (cloud GPU pod proof, cap study, campaign, train/gate; see `docs/CLOUD_GPU_REPORT.md` section 6): proposed, awaiting user decisions on provider and spend cap; no GitHub issue yet.

CP-10a..d (high-frequency options, 12 kHz; see `docs/HIGH_FREQUENCY_OPTIONS.md` section 6): proposed, none run; CP-10d needs the user to approve contacting Collin.

Added 2026-10-14 (cloud): **#13 fixes F1-F6 ready on `ccr-455d2184-yj5zk4` (draft PR #14). Merge into this branch AFTER CP-8c, BEFORE CP-8d.** #13 stays open until then.
**[SUPERSEDED locally, 2026-10-13 ~23:00: the SAME issue-#13 fixes are already on this branch â€” local commits e0b9b61 (8 items) + 11304f6 (store/CLI follow-ups), full offline suite WITH the mesher: 498 PASS / 0 failures. Do NOT merge PR #14 on top â€” that would double-apply overlapping changes in `surrogate/**`. Cloud owner: diff e0b9b61+11304f6 against PR #14 and adopt ONE set. CP-8d proceeds on this branch's fixed code either way; `propose` here refuses unvalidated bundles by default with `--allow-unvalidated` for the runbook's indicative round.]**

Added 2026-10-14 ~05:00 UTC (cloud): PR #14 REBUILT on `622776a` â€” local issue-#13 set (e0b9b61/11304f6) adopted, cloud duplicates dropped; adds FREEFORM sculpt config, FREEFORM training-export fix (dotted keys were NaN), `compare`, DI-provenance guard, NaN refusal, FREEFORM throat radius. Merge, then HANDOFF section 6b. Open, no GitHub issue: FREEFORM full-vs-quarter GPU check + bar ruling; mesher wall-port feature request; HornLab author naming (user to confirm).

Added 2026-10-21 (cloud): Boundary Lab 0.5.0 integration PROPOSED (`docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`; research `docs/BOUNDARY_LAB_0.5_RESEARCH.md`). No GitHub issue yet; open decisions: phase order A->B->C, ownership rows, BL env on the GPU box, contacting JW Sound / HornLab author.

Added 2026-10-22 (cloud): senior architecture report `docs/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md` (Boundary Lab: sidechain, plugin parked; priority and to-do list). On `main` (`2311f92` + this commit).

Local-only, added 2026-10-22 (local GPU box, HANDOFF 6b): FREEFORM quarter-vs-full symmetry check PASSED (max 0.0043 dB, beamwidth 0.051 deg; bar 0.1 dB / 1 deg, not frozen - owner may freeze it); `freeform_sculpt` 60-eval search 0 failures, J 30.945 -> 24.213. Follow-ups (non-blocking): (1) `compare` header prints `quadrants None` for both runs although they solved 451 vs 1636 dofs (reads the wrong field; cosmetic); (2) dry-run throughput estimate 2 s/candidate vs measured 6.7 s for `freeform_sculpt` (TOOLCHAIN M3 extrapolation under-predicts; affects budget planning only); (3) watch `profileH.mouthAngleDeg` (2/6 at hi 70) and `profileV.points.3.1` (2/6 at lo 108) on any longer sculpt run before widening. CP-8d must not be re-run before the OSSE top-up (CONTINUITY Next action corrected). Evidence `docs/evidence/HANDOFF_6b.md`.

Local-only, added 2026-10-22 ~11:40 (local GPU box): follow-up (1) `compare` quadrants label FIXED (regression test). New `export-step` CLI (senior report s3 item 4) DONE. Sculpt budget 400: J 30.945 -> 16.789, **3 wall anchors PINNED** (`profileH/V.points.3.1` at lo, `profileV.points.4.1` at hi) - the disjoint per-anchor radius boxes now bind; options for the owner: widen/overlap the boxes with a mesher monotonicity check, or reparametrise as positive increments. Bound-limited families awaiting a widening decision: OSSE `n` (6/6 lo), ICW `hold_end` (6/6 lo) + `kappa0` (4/6 lo), throat_adapter `throat_ext_angle_deg`/`k` (6/6 hi) + `a0_deg` (6/6 lo), FREEFORM sculpt anchors above. No widening done (user OK required).

Added 2026-10-22 PM (cloud): Boundary Lab learnings implemented (`docs/BL_LEARNINGS_IMPLEMENTATION.md`): pre-solve topology + symmetry-domain checks, `solve/phasor.py`, runtime provenance, report-only SPDI / beam shape. 

**NEXT DEVELOPMENT ROUND, TOP PRIORITY (user decision 2026-10-22): read `docs/NEXT_DEV_PRIORITIES.md`.**
- [ ] **P1 Fused / direct CUDA Burton-Miller assembly** in the exterior driver (post-beta; Magnus's OK or a pinned fork). Fused path is CPU/Metal only (`hornlab_beat_bem/julia/BeatEngineDriver.jl` ~l.1215); the CUDA single-matrix assembler `assemble_burton_miller_neumann_system_cuda` (`julia/src/BeatEngineCudaBurtonMiller.jl:350`) is called only by `runtests.jl`. Engine work, not a flag flip. Expected: 8 GB ceiling ~9k -> ~20k quarter dofs (~12.6 kHz at epw 6 on the large OSSE seed) [inferred]. Validate with selftest --analytic, --crosscheck (< 0.2 dB) and an A/B vs today's CUDA path before any data counts. NOT enabled for the 2026-10-22/23 overnight queue (one solver for the compare tier and surrogate top-up).
- [x] **P2 12 kHz finalist verify pass on the 4060**: DONE 2026-10-23 (see the item below and `docs/evidence/HF12K_VERIFY_2026-10-23.md`).
- [ ] **P3 `beat_metal` backend** for the collaborator's Apple Silicon MacBook (fused path on, unified memory); Mac selftests + 3-design A/B vs the 4060 before mixing data.

TO-DO (no GitHub issue yet; owner / plan ref):
- [x] Merge the learnings PR, run its section-4 test plan on the GPU box: DONE 2026-10-22 (FF to 265133f; `docs/evidence/BL_LEARNINGS_GPU.md`).
- [x] Early rejection offline replay: DONE 2026-10-22 (`docs/evidence/EARLY_REJECTION_REPLAY.md`): < 0.1 % GPU saved at K = 4 / 25 % margin, no top-20 lost; recommend NOT implementing as specified (owner ruling).
- [x] (closed 2026-10-23 by the failure cache) Search budget counts uncached failures: a re-run with the same CMA seed replays cached successes for free but re-evaluates every earlier failure, which consumes budget without solving (OSSE budget 40 -> 0 new solves, 2026-10-22). Options for the owner: cache failures by design hash, or count only solver-reaching evaluations (task 08; `search/cma.py`).
- [ ] CPU-vs-CUDA qualification screen per pinned-library change (GPU box; frozen CP-7b rule; s2 item 8). Note: beat_cuda vs bempp_cpu re-run 2026-10-22: 0.039 dB (`docs/evidence/SOLVER_VERIFY_2026-10-22.md`).
- [x] Typology plan v2 implemented 2026-10-22 (generators, hybrids, briefs, `families`/`campaign`, failure cache, loading metrics). GPU checks V4/V5/V7 in progress.
- [ ] Le ClÃ©ac'h / spherical-wave generator DISABLED (R9): implement only from a verifiable published construction (ETF 2010 lecture PDF too large to fetch, diyaudio thread 403, sphericalhorns.net calculator disclaims fidelity to JMLC). Needs a human-supplied reference.
- [ ] Brief `source.cap: auto` not applied: FREEFORM keys in `families.py` do not expose the mesher's source-cap radius/auto-angle; every design uses the mesher default cap (consistent within a campaign). Add the keys (task 04) and tie to the brief.
- [ ] Generated horns use a 3 mm outer shell (mesher FREEFORM curvature guard); Magnus-family configs use the mesher default shell. Outer-shell thickness differs between the two groups; small acoustic effect at the mouth rim, recorded per design.
- [ ] `search_smoke` (legacy) cannot be dry-run under a 5.5 kHz brief (seed exceeds its dof cap); harmless, legacy only.
- [x] `search --brief/--cma-seed` were silently ignored (fixed 2026-10-22; first campaign's native-family entries invalid and re-run).
- [x] Campaign fairness: cached replays gave native configs 6-15x more search; `--max-evals` caps all evaluations (fixed 2026-10-22).
- [x] Hygiene left BEAT `worker_host` processes (which respawn julia) alive; now cleared with their julia children (fixed 2026-10-22).
- [ ] `perturbed_osse_hv`: 36 % invalid in the screen run and `L_mm` pinned; revisit its bounds/u_max before a compare run (widening needs user OK).
- [x] Brief size envelope now enforced for every family (outer mesh bbox); native configs sized for other targets (osse_baseline, freeform_sculpt under the 400x300 brief) have no valid design and are labelled so in the leaderboard. Beta users: use typology configs or size a native config for the brief.
- [ ] Mesher upstream 4573bc90 is 57 commits past our pin b922e807 (FREEFORM corner topology `d740c28`, `68ed646`, joins `967db56`; ATH import; new geometry keys). Signatures and the 0.4 curvature guard unchanged. Owner 2026-10-22: keep the pin for the beta; post-beta bump candidate with its own verification ladder.
- [x] R8 brief provenance: dataset records carry optional `provenance` {config, brief, brief_hash, generator} (2026-10-22).
- [x] C2 epw 6 vs 8: axi seed DI 0.124 dB > 0.1 -> axi typologies at epw 8 (owner); H/V within 0.05 dB stays epw 6.
- [x] GPU lock + `gpu-clean` (2026-10-22); overnight queue + watchdog in `tools/overnight/`.
- [x] GPU lock liveness on Windows: `os.kill(pid, 0)` made a live holder in another console look stale (takeover / gpu-clean would hit a running solve). Fixed 2026-10-23 with OpenProcess/GetExitCodeProcess + tests.
- [ ] OSSE `exponent` presses its upper bound (7.9 of 8) in the 2026-10-23 top-up (seen in the time-lapse): bound decision for the owner, like the other pinned bounds.
- [x] **Search does not recover a dead BEAT worker host** (2026-10-23; FIXED 2026-10-23 ~14:30, offline-tested: root cause = `hornlab_beat_bem.worker.get_worker` caches a `HostedBeatWorker` that keeps its dead socket after a send fails, so every later solve wrote to it; `recover_after_failure` now also calls `detach_workers` (drops the cache), `BeatBackend` re-warms and retries a `worker_exit` candidate once, and `search` stops RESUMABLY (status aborted, `SolverUnhealthyError`) after 3 consecutive `solve_failed` instead of ending on `tolflatfitness`; `to_training_arrays` drops `solve_failed` records from labels (`meta.skipped_solve_failed`). Tests `tests/test_solve_beat_recovery.py`, `test_search_cma.py`, `test_dataset_store.py`. The host death itself is still unexplained, GPU rule 7. Original report: OSSE top-up seed 4101 lost its host at 03:58:48 EDT (`ConnectionResetError` 10054, `solve_failed [worker_exit]`); every later candidate failed in ~3 s (21 rows), J went flat at the 1000 penalty and CMA-ES stopped on `tolflatfitness` at 411 of 950 evaluations. Cause of the reset unknown (second unexplained reset tonight; first in the C2 check 21:46, not reproduced from clean, CLAUDE.md GPU rule 7). Fix proposal (task 05/08): on `worker_exit`, re-warm the host once and retry the candidate before scoring a failure; never let a run of solver failures end a search. The 21 `solve_failed` dataset records are failures of the solver, not of the designs (non-deterministic kind, never failure-cached); exclude `solve_failed` from the surrogate's validity labels.
- [x] Local web GUI `hornlab-search gui` (2026-10-23, `docs/GUI_PLAN.md`). Open: macOS untested; 3D view needs the three.js CDN. Launch GPU-busy state now LIVE (polls `/api/status` every ~6 s, toggles note / Start button, toast; 2026-10-23 14:30; the server still re-checks on launch). Senior UX pass done 2026-10-23; typology picker, Typologies page and graphics pass done 2026-10-23 (09:00); search time-lapse player 2026-10-23 (10:40); beta hardening + Boundary Lab-style isobars 2026-10-23 (11:30, d0a04ea).
- [x] Wire `surrogate.features.require_surrogate_config` into `cli._cmd_surrogate`: done 2026-10-23 (merged).
- [x] Beta-readiness pass per `docs/HANDOFF_BETA.md` (F timed rehearsal DONE 2026-10-23 16:30, 8 friction points fixed, `docs/evidence/BETA_READINESS.md` F; G session plan refreshed with measured timings; A-G; A-D done (D3 Ctrl-C PASS on the GPU 2026-10-23 after a campaign fix; D5 paths PASS); E running overnight; F, G pending): upstream audit, R8 brief provenance in dataset records, epw convergence above 2.5 kHz, GPU lock / gpu-clean, rehearsal, session pack.
- [x] `compare` tier (2 CMA seeds) on the leaders: DONE 2026-10-23 (`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`).
- [ ] Bound proposals from the compare tier (osse_axi `h_s`, hypex/exponential `L_mm` lo, perturbed_osse_hv `L_mm`/`v_a_deg`, hybrid `v_rm_mm`): owner decision; NOT applied.
- [ ] rosse_baseline is seed-sensitive (12.3 vs 14.3): more seeds or budget before any ranking claim.
- [x] Failure cache: deterministic failures cached by design+mesh+solve key across runs (fixes the OSSE seed-replay budget burn).
- [ ] Stage 2 transient analysis (impulse, step, CSD waterfall, group delay, dense throat impedance) on finalists: research + design in `docs/research/TIME_DOMAIN_RINGING.md`; needs a dense uniform frequency list per evaluation (today only 12/25/36-point log grids, too sparse: Magnus's `plot_impulse_response` interpolates over resonances). After the typology campaign; not in the search loop.
- [x] R-OSSE: `examples/rosse_baseline.yaml` added 2026-10-22 and run in the hifi screen + compare campaigns (seed-sensitive: 12.3 vs 14.3, see below).
- [ ] ICW rollback termination never exercised (categorical; needs its own config). In the typology plan.
- [ ] `freeform_hv.yaml` solves the full domain although FREEFORM quarter == full within 0.0043 dB (4x dofs wasted). In the typology plan.
- [x] STEP-export CLI: DONE locally 2026-10-22 (`hornlab-search export-step`, b822dd5).
- [x] OSSE data top-up for the surrogate gates: DONE 2026-10-23 (user OK 22:14): seed 4101 411 evals (host death 03:58), seed 4102 951 evals. Retrain + CP-8d gates next (CPU).
- [ ] Boundary Lab BL-1 export (cloud; `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`).
- [x] `compare` IndexError on empty frequency list: fixed 2026-10-23 (merged).
- [x] `verify --brief` was parsed and silently IGNORED (found 2026-10-23 preparing P2; would have re-verified at 5.5 kHz). Fixed: the brief is applied and the results go to their own run dir `runs/<ts>-verify-<id>` (listed by the GUI; `run.json.verify_of`); `verify` without `--brief` unchanged. Test `tests/test_search_verify_brief.py`.
- [ ] Collaborator pulling `main` 2026-10-23 evening: `docs/HANDOFF_COLLABORATOR_2026-10-23.md` (branch + PR; owner merges after the GPU jobs).
- [x] P2 12 kHz finalist verify pass: DONE 2026-10-23 16:07 (`docs/evidence/HF12K_VERIFY_2026-10-23.md`): 14 designs, 0 failures; epw converged at 12 kHz (<= 0.058 dB, <= 0.31 deg); rankings as in the compare tier; peak VRAM 7,360 MiB above baseline at 6,049 dofs (edge of 8 GB). 8-12 kHz compares geometries, not drivers (f11 7,914 Hz).

- [x] Docs index `docs/INDEX.md` and code map `docs/CODE_MAP.md` added 2026-10-22, linked from CLAUDE.md / AGENTS.md / .claude/CLAUDE.md; keep them current.
- [x] Campaign Ctrl-C and host hygiene (2026-10-23): `run_job` killed a Ctrl-C'd child mid clean-up and skipped the leaderboard; a campaign never cleared its Julia/BEAT hosts (snapshots only). Fixed (grace period, partial INTERRUPTED leaderboard, exit 130, hosts cleared after every job); D3 PASS live (`docs/evidence/BETA_READINESS.md` D).
- [ ] Surrogate retrain 2026-10-23 (`docs/evidence/CP-8d_retrain_2026-10-23.md`): GATES FAILED (topk 11/20, invalid_accuracy 0.80, monotonic_flips 4) at 600 epochs; held-out 463 < 500 (indicative). Model NOT used. Owner: ~250 more OSSE records for the floor; flips semantics; why the ranking/validity gates got worse with more data.
- [x] `*_12k` verify-only briefs were accepted by search/run/campaign and offered by Launch (2026-10-23 rehearsal): `verify_only: true` brief key; search/run/campaign refuse (exit 2), Launch hides them; tests in `tests/test_search_verify_brief.py`.
- [ ] Live demo on a shipped brief replays from the cache (~1 min, same CMA seed): use a saved brief copy (5.5 min measured). A `--cma-seed` option for `campaign` would make fresh live runs possible on shipped briefs (owner, task 08).

Local-only, added 2026-10-24 (senior pass): implementation backlog WP1-WP17 in `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` (objective v2, driver pinning, fused CUDA in our fork, 12 kHz screens, GRID shapes, multicell); owner gates: WP13 third-party axisymmetric solver, GitHub hosting of forks, v2 as default.

Local-only, added 2026-10-24 evening (orchestrator, M1 implemented + Oracle-verified; pushed): WP1, WP2, WP3, WP4 (offline parts) and WP15 repo-side plumbing LANDED (see `docs/CONTINUITY.md` 2026-10-24 entry; Oracle verdict GO, all 3 must-fixes in the push commit; 933 offline tests pass, no test loosened).
- [x] WP1 objective v2 + offline re-score: DONE (`docs/evidence/OBJECTIVE_V2_RESCORE.md`; rho 0.989, claims survive, v1 drift 0; v2 stays OPT-IN â€” making it the brief default is an owner decision).
- [x] WP2 driver pins with embedded-brief grandfather: DONE (2 pre-WP2 runs with an embedded 12.7 brief on a 17.78 OSSE config now load byte-for-byte; new `--brief`/`brief_file:` runs enforce; `osse_baseline` is skipped under 1-inch briefs by the campaign compat check).
- [x] WP3 shape-only perturb + pre-mesh `invalid_envelope` + graded penalty (opt-in `search: {infeasible_penalty: graded}`): DONE; all shipped typology seeds estimate 0.0.
- [x] WP4 `freq_weights` (v2-only, v1 warns once) + `verify_points_per_octave` HF verify grid: DONE.
- [x] WP15 repo side (`solve.cuda_fused`, env gating, `assembly_path == "fused_cuda"` proof + refusal): DONE offline; fork branch `hornlab-search/fused-cuda` @ fa99ee5 (Julia tests green). Gpu ladder + ceiling measurement NOT RUN yet (M2; owner: do not pin a file:// URL on main).
- [ ] Oracle non-blocking follow-ups (recorded, none urgent): (1) `invalid_envelope` not failure-memoized (brief-dependent; revisit with a brief-aware marker key in M2); (2) envelope estimator adds full wall thickness radially â€” conservative by ~2.5 mm at 80 deg mouths (documented; no shipped seed affected); (3) dataset record lacks an explicit `objective_version` field (config_sha covers it today â€” add in M2); (4) solve-cache/`ctx.known` reuse keys exclude the objective version â€” never flip objective version on a resume; start a new run; (5) v2 solve-cache hits re-score with the CURRENT weights like v1 (documented behaviour, unchanged by design); (6) `_verify_only_precheck` precedence note for the CLI docs (verify_only wins over a broken config â€” intended); (7) `tools/rescore` duplicates the balloon-collapse block of `metrics_from_response` (drift-0 verified; keep in sync); (8) cosmetic tautology in `test_solve_fused_flag.py` last assert.
- [ ] `tools/launch_gui.ps1` (pre-existing untracked, benign): owner decides; kept out of the M1 commit.
- [ ] Owner decisions queued from M2 onward: fork GitHub hosting + push; v2 default; WP13.

Local-only, added 2026-10-24 late (orchestrator, M2 executed; pushed): WP15 fused CUDA **validated on the GPU** (see `docs/CONTINUITY.md` 2026-10-24 M2 entry; evidence `docs/evidence/FUSED_CUDA_2026-10-24.md`; raw logs gitignored under `runs/m2_fused_cuda/`).
- [x] WP15 install + validation ladder: DONE â€” analytic **0.020 dB** (bar 0.5; = base reference), crosscheck **0.0390 dB** (bar 0.2; = base reference), from clean GPU states.
- [x] WP15 3-arm A/B vs the base pin's stored runs (flag OFF): osse_axi seed `d04e8697a87d`, perturbed_osse_hv best `fed761193da7`, freeform_sculpt seed `892bb3551903` re-solved with FRESH scratch cache dirs (**finding: the solve cache is NOT keyed by lib SHA** â€” stale cache entries would otherwise have silently served old-SHA responses as "A/B") then `hornlab-search compare`: design hashes match; max diffs **â‰¤ 2.9e-6 dB / â‰¤ 2.1e-05 deg** (bars 0.039 dB / 1Â°). This is the step-8 old-path reproduction proof; A/B run dirs confirm `lib_shas.hornlab_beat_bem == fa99ee5â€¦` and `meta.cuda_fused == False`/absent everywhere.
- [x] WP15 fused GPU test: DONE â€” `[measured]` fused-vs-default @ 2 kHz: on-axis max diff **0.0000 dB** (bar 0.01), bw H 76.65â†’76.65 / V 84.18â†’84.18 deg (bar 0.1), z_throat rel **3.35e-07** (rtol 1e-3); the stale-host fused REQUEST (env flipped on a host spawned before it) was REFUSED. **Determinism finding (rule-7 trail):** the test's zero-tolerance bit-identity assertion FAILED on the fork **AND identically on the BASE PIN 38544d2** after a rollback reinstall â€” two identical CUDA requests differ at one Float32 ulp (order-varying reductions; worst observed **1.74e-05 dB**); pre-existing upstream property, not a fork regression. Rebarred to a documented **1e-4 dB** floor with the measured evidence in the docstring + a `[measured]` print (NOTES_FOR_SENIOR 2026-10-24 block); the fused-vs-default bars themselves are untouched; **Oracle adjudicated: rebar PASS (base-pin reproduction decisive; all three measurements now in the docstring; full rulings in CONTINUITY)**.
- [x] WP15 ceiling re-measure (owner capped the sweep â€” no 24k point; the clean-state 20k confirm was interrupted): fused **FITS 15,984 dofs** (peakâˆ’baseline **7,637 MiB**; assembly already memory-pressured at **437 s/freq**); **FAILS 20,237** (BEAT worker-host death on the attempt AND the in-process re-warm retry; peak 7,831 MiB â€” recorded **provisional**, clean-confirm not completed per owner). Old path on the SAME 8,919-dof mesh: **7,389 MiB / 59.6 s** vs fused **2,217 MiB / 9.1 s**. The "~20k inferred" did NOT materialize on this card/protocol. Measured SAFE caps: **verify/final 12,000 dofs** (measured 12,183: 4,744 MiB, 13.72 s/freq). Harness `tools/measure_fused_ceiling.py` (fresh process, threaded external nvidia-smi poll, verified shutdown; `--mesh-only` calibration â€” note: TOOLCHAIN M1's resâ†’dof table was measured on a SMALLER horn: the osse_baseline seed at 3/1.5 mm is 43,993 dofs, so the sweep calibrated mouth-res 6.72/5.74/5.02/4.45 mm).
- [x] `_fusedcuda` configs: DONE â€” 4 NEW files (`osse_baseline`, `osse_axi`, `perturbed_osse_hv`, `freeform_sculpt`), caps 5000/**12000/12000** + `solve.cuda_fused: true`, provenance headers; originals untouched (`git diff -- examples/` empty on the originals).
- [x] 12 kHz verify on the flag: DONE â€” ONE verify job `runs/20261025T013051Z-verify-be4adb`: osse_axi seed via the fused config's run dir + `verify --brief axi_90x90_1in_12k`: verify J **17.0339** (not comparable with screen J â€” different band/grid), **4,438 dofs** / 8,626 tris (below the raised 12,000 cap â€” the epw rule chose the mesh), **52.89 s / 25 freqs â‰ˆ 2.1 s/freq**, response.npz `cuda_fused: True` + **25Ã— `assembly_path: fused_cuda`**; **f11 = 7,914 Hz caveat applies (8â€“12 kHz compares GEOMETRIES, not drivers)**.
- [x] Suite: dev-pin tree = **938 passed / 0 failed / 0 errors / 20 deselected** (junitxml `runs/m2_fused_cuda/suite_dev.xml`, 217.9 s; total collected 958). Main tree (base pin vs installed fork): same selection, exactly 1 failure = `test_mesh_pin` â€” the INTENDED pinned-SHA tripwire until the owner lands a hosted pin (expected state, documented in CONTINUITY + TOOLCHAIN). Selection +3 vs M1's 935 = the new `_fusedcuda` configs in parametrized config sweeps + the concurrently-landed GUI-contrast lane's tests. Nothing loosened.
- [x] Pin policy: `pyproject.toml` + `TOOLCHAIN.md` pin @ `fa99ee5` committed ONLY on **`dev/fused-cuda-pin` (65c03de, LOCAL ONLY â€” not pushed, not merged)**; a file:// pin must never reach main. **Owner asks: host the fork on GitHub + push, then replace the dev pin; then M3 (WP5â€“WP8).**
- Deferred to M3+ for time: M1 follow-up (3) explicit dataset-record `objective_version` field (config_sha covers it today); M1 follow-up (1) `invalid_envelope` memoization (revisit with a brief-aware marker key â€” Oracle: the fix is one line, add brief_hash to the marker's replay-validity; the graded penalty already recomputes on replay so only the stale *verdict* is the hazard). **BOTH DONE in M3 (commit `1dda493`, 2026-10-25): explicit `objective_version` written by every record + absence-tolerant v1 reads; the `invalid_envelope` marker stores + requires `brief_hash` on replay (graded penalty unchanged; test where a different brief re-evaluates).**
- ~~Owner advisory (pre-existing on origin/main): the 2026-10-24 night entries reference `docs/NEXT_DEV_PRIORITIES.md` section "P4", which exists only in the owner's local uncommitted note â€” commit it separately or treat those references as pointing to the local note.~~ **RESOLVED (~00:30 2026-10-25): the P4 note is now committed verbatim** (in the same commit that adds the P5 easy-wins section: W1 rank audit / W2 dense finalist net = P4a scheduled / W3 named screen-grid group, gated / W4 `compare --bar` / W5 freq-weights emphasis); the night references resolve to actual file content now.
- Handoffs issued for the next two passes (2026-10-24 late, owner directive: the shipped demo briefs are NOT their design intent â€” never GPU-search demo sheets): (1) **M3 execution** (full text in chat, owner holds it): carry-over fixes (`objective_version` field; `invalid_envelope` brief_hash marker) + WP5 calibration + WP7/WP8 speed checks on STORED designs, ZERO new searches, ~15â€“20 GPU solves; (2) **brief design** committed as `docs/HANDOFF_BRIEF_DESIGN_2026-10-24.md`: study list â†’ 10-question owner interview (verbatim capture) â†’ real-driver web grounding â†’ 2â€“4 real briefs + baseline settings, offline-validated â†’ GPU = ONLY the owner-approved POC (budget 20 + one fused 12 kHz verify). Sequence: M3 first, then brief design. Band stays 700â€“12,000 (14 kHz+ screens would blow the 5,000 cap and ~2Ã— per-candidate cost above f11 with no realism gain; a screen-cap raise for band_hi > 12,000 is OWNER-GATED). Handoff GROUNDED (same evening): full capability map (Â§2b) of what the later plan lands â€” M3 in flight (carry-overs `1dda493` + WP5 proposals + WP7 rear factor + WP8 band-split), M4 (WP9 generators, WP9b JMLC/Kugelwellen/organic/X T1â€“T7, WP10 GRID Fourier sections, WP12 mounting), M5 (WP11 restarts, WP16 >f11 realism, WP17 near-correction, WP14 multicell CPU-first) â€” plus four forward-compatibility rules for the briefs (landed keys only; stated family-allow-list assumption; variant briefs pre-planned for curl/organic appetite; every future-dependent item marked "awaiting WPxx").

- **OWNER ITEM (agent-tooling, 2026-10-25 early):** THREE opencode project skills landed after Oracle hardening passes â€” `.opencode/skills/hornlab-gpu-job/` (per-GPU-job hygiene/capture recipe; exit-3 + FORKS-tripwire semantics; fresh-measurement + fresh-cache rules), `.opencode/skills/hornlab-evidence/` (evidence assembly + pre-publish byte-check of EVERY quoted block) and `.opencode/skills/hornlab-typology-research/` (the horn-design grounding protocol: sourced dossiers + R9/rename-gate discipline before typology/shape work; AGENTS.md + CLAUDE.md carry the block). Applied on the next opencode run (config-time files). **Owner config decision:** the slim preset gates skills per role (`orchestrator: ["*"]`, but fixer/explorer/librarian/designer/council: `[]`) â€” lane sessions never see the skills; either add the three names to those roles' arrays in `.opencode/oh-my-opencode-slim.json` (one-line each) or keep embedding the ceremony in dispatch prompts.
- **W6 balloon GUI view: LANDED (2026-10-25, ~01:10):** the Balloon 3D view + radar slicer + isobar slice are implemented in the web GUI (own implementation of BL's display grammar; GPL attribution in code; server routes read-only + path-safe; `tests/test_gui_balloon.py` +9; gui tests 44/0; both-theme screenshots under `runs/gui_balloon/`). Ships with today's stored balloon densities (screen 16Ã—32; verify 23Ã—45); the verify-balloon density upgrade stays gated on the M3/WP5 Î”DI ladder (W7 in NEXT_DEV_PRIORITIES).

Local-only, added 2026-10-24 night (user request, docs-only; full write-up: `docs/NEXT_DEV_PRIORITIES.md` section "P4"):
- [ ] **Narrow-resonance blind spot + dense finalist check (P4a, idea)**: the screen grid is 12 log-spaced points
  (500 Hzâ€“~5.5 kHz), verify 25 points â€” a horn defect narrower than the ~1/3-octave gap (mouth-reflection
  resonance, organ-pipe mode, narrow cancellation) can fall entirely between solved frequencies; nothing is
  simulated between grid points, interpolated plots render smoothly over the defect, and the objective cannot
  score it, so a peaky horn can outrank a clean one. Proposed safety net: re-solve the FINALIST shortlist only on
  a dense uniform in-band grid (24â€“48 points or the WP4 8/octave pattern over the whole band) and diff vs sparse
  metrics; auto-flag families whose dense J degrades. No contract change needed; cheap (a handful of designs).
- [ ] **Perceptually weighted non-uniform frequency grid (P4b, idea; FROZEN-CONTRACT matter)**: extra solved
  points at hearing-critical/problematic regions (~2â€“3 kHz, ~4â€“5.5 kHz, possibly the 0.5â€“1 kHz mouth-reflection
  onset) instead of even log spacing. Requires an owner-approved amendment of the frozen 01_CONTRACTS Â§8 grid
  (2026-10-13 ruling declined per-user YAML grid keys; a changed grid changes the solve hash and cannot train/
  cache with existing grids) â€” must be a NEW NAMED grid group with the point list fixed in the contract (the
  `*_12k` brief / WP4 `verify_hf` pattern), not a free-form key. Related: WP4's `verify_points_per_octave`
  (verify-only, >5 kHz) and v2 `freq_weights` (reweights solved points only) already landed.

Local-only, added 2026-10-25 (orchestrator, M3 executed; pushed): carry-overs + WP5/WP7/WP8 calibration on EXISTING stored designs, ZERO new searches (owner directive). Evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (17 GPU jobs, 728 s GPU wall, no crash/OOM); harness `tools/m3_measurement_pack.py`. Oracle verdict GO-with-fixes â€” ALL applied (MUST: `rear_res_factor` also keys the solve cache/failure markers/resume memo via solve-spec `extra`; the evidence doc's counter wording fixed; SHOULD: Â§5.1 Band-2-dofs + seam-walls honesty notes, row-echo pinned by tests; NICE: a failed seam solve is recorded in `meta["seam_check"][edge]["error"]`, pre-M3 marker backcompat docstring).
- [x] M3 carry-overs: dataset-record explicit `objective_version` field + `invalid_envelope` brief_hash-scoped failure marker (commit `1dda493`; 6 tests) â€” DONE.
- [x] M3 framework keys (opt-in, absent = byte-identical config/mesh/solve hashes, tested): `solve.source_motion`, `mesh.rear_res_factor` (rear-only scale; READ-FIRST honored â€” MeshDensity `rear_res_mm` drives ONLY outer shell + rear cap), `mesh.band_split {edges_hz}` + `stack_responses` (exact tiling) + verify-only seam check + `mesh_policy: band_split_v1` provenance â€” DONE (24 tests).
- [ ] **Owner-gated PROPOSALS (nothing adopted, no default flipped):** (1) `distance_m: 10` for v2 briefs â€” 2â†’50 m |Î”bw| > 1Â° in-band on ALL THREE finalists; max |Î”DI| 2â†’50: AXI 1.61 / HV 0.59 / RO 0.54 dB (residual 2â†’10 m up to 8.66Â°/0.86 dB â€” better, not converged); (2) raise the screen balloon 512 â†’ 1024 â€” max |Î”DI| 0.1545 dB (AXI @ 7,567 Hz) / 0.1110 (HV @ 12 kHz), fires 2/3 (1035â†’2592 â‰¤ 0.0407); (3) `mesh.rear_res_factor: 2.0` â€” AXI screen dofs 1,397 â†’ 1,060 (**âˆ’24.1 %**), J âˆ’0.00697, top-5.5 kHz CP-7f bars all pass (1.5 also passes, âˆ’18.8 %; 3.0 unmeasured); (4) `source_motion: axial` measured only (AXI/HV â‰¤ 0.007Â°; RO up to 0.4331Â° bw @ 12 kHz, above the f11 = 7,914 Hz caveat) â€” no proposal mechanism, default stays "normal".
- [ ] **WP8 band-split verdict: FAILS the CP-7f acceptance gate on BOTH designs** (in-band maxima AXI 1.2476Â°/1.2166Â°/0.1529 dB/0.4218 dB raw on-axis, HV 1.0957Â°/0.9259Â°/0.1021/0.4041; failure concentrated in band 0, band 2 bit-identical to the single mesh; seam deltas âˆ’0.237/âˆ’0.111 dB AXI, âˆ’0.271/âˆ’0.043 dB HV in `meta["seam_check"]`) despite measured walls **âˆ’53.5 %** (AXI, 29.64 vs 63.68 s) / **âˆ’28.2 %** (HV, 33.82 vs 47.08 s) vs the same-code single-mesh solve. Machinery + provenance landed opt-in only; the band-0 fidelity issue must be addressed before any adoption (owner decision).
- [ ] Suites at the final state: focused post-fix subset 68/0/0/0 (`runs/m3_code/suite_oracle_fixes.xml`), full offline **968 tests / 1 failure (= the expected `test_mesh_pin` tripwire) / 0 errors / 0 skipped** (`runs/m3_code/suite_final.xml`); compileall clean.

Local-only, added 2026-10-25 (orchestrator, M3 executed; pushed): carry-overs + WP5/WP7/WP8 calibration on EXISTING stored designs, ZERO new searches (owner directive; WP6 cut). Evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (17 GPU jobs / 728 s GPU wall, no crash, no OOM, verbatim logs, MISSING cells disclosed); harness `tools/m3_measurement_pack.py`; raw logs gitignored under `runs/m3_wp5a|wp5b|wp5c|wp7|wp8/`. Oracle verdict **GO-with-fixes â€” ALL applied** (MUST-1: `rear_res_factor` also keys the solve cache/failure markers/resume memo via solve-spec `extra`; MUST-2: the evidence doc's stale "no junitxml counters" claim replaced with the real suite files/counters; SHOULD: Â§5.1 Band-2-dofs ambiguity closed + seam-inclusive-walls honesty note + row-echo pinned by tests; NICE: a failed seam solve records `{"error": ...}` in `meta["seam_check"]`, pre-M3-marker backcompat docstring).
- [x] M3 carry-overs: explicit dataset-record `objective_version` field + brief_hash-scoped `invalid_envelope` failure marker (commit `1dda493`, 6 offline tests) â€” DONE.
- [x] M3 framework keys (opt-in; ABSENT = byte-identical config/mesh/solve hashes, tested): `solve.source_motion`, `mesh.rear_res_factor`, `mesh.band_split {edges_hz}` + new `stack_responses` (exact-tiling assertions) + verify-ONLY seam check + provenance `mesh_policy: band_split_v1` in ndjson rows + records â€” DONE (24 offline tests).
- [ ] **Owner-gated PROPOSALS from M3 (NOTHING adopted; every flip is the owner's):** (1) `distance_m: 10` for v2 briefs â€” 2â†’50 m |Î”bw| > 1Â° in-band on ALL THREE finalists (max |Î”DI| 1.61/0.59/0.54 dB; residual 2â†’10 m up to 8.66Â°/0.86 dB â€” better, not converged); (2) raise the screen balloon 512 â†’ 1024 â€” max |Î”DI| 0.1545 dB (AXI @ 7,567 Hz) / 0.1110 (HV @ 12 kHz); 1035â†’2592 â‰¤ 0.0407 (fires 2/3); (3) `mesh.rear_res_factor: 2.0` â€” AXI screen dofs 1,397 â†’ 1,060 (**âˆ’24.1 %**), J âˆ’0.00697, top-5.5 kHz bars all pass (1.5: âˆ’18.8 %; 3.0 unmeasured); (4) source_motion axial measured ONLY (AXI/HV â‰¤ 0.007Â°; RO up to 0.4331Â° @ 12 kHz, above the f11 = 7,914 Hz caveat) â€” no proposal mechanism.
- [ ] **WP8 band-split verdict: FAILS the CP-7f acceptance gate on BOTH designs** (in-band maxima AXI 1.2476Â°/1.2166Â°/0.1529 dB/0.4218 dB on-axis; the failure concentrates in band 0; band 2 is bit-identical to the single mesh) despite wall âˆ’53.5 % (AXI, 29.64 vs 63.68 s) / âˆ’28.2 % (HV, 33.82 vs 47.08 s) vs the SAME-CODE single-mesh solve. Machinery + provenance landed opt-in; adoption and any band-0 fidelity fix are owner decisions.
- [ ] Suites at the pass's final state: focused post-fix subset 68 / 0 / 0 / 0 (`runs/m3_code/suite_oracle_fixes.xml`); full offline **968 tests / 0 errors / 1 failure / 0 skipped** â€” the single failure is exactly the expected `tests/test_mesh_pin.py` tripwire (installed fork `fa99ee5` vs main's base pin `38544d2`; clears via the dev pin when the owner hosts) (`runs/m3_code/suite_final.xml`).

Local-only, added 2026-10-25 (docs-only, owner request, follow-through): the P6 research was hardened into a **full implementation plan v1.0** via two parallel web-research lanes â€” `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md` REWRITTEN (dossier folded in). **P6a basis now evidence-grade:** quarter-domain superformula rules (m âˆˆ {4, 8, 12} integer multiple-of-4; m1 = m2 mandatory for quarter meshes [derived]; non-integer m = open curves; the `n1 < 2 âˆ§ max(n2,n3) > 10` degeneracy guard from Symmetry 2022; a/b ratio-only search; canonical Ath reference values quoted incl. User Guide Â§6.4.2; mouth-theory record: no published non-elliptical-mouthâ†’HOM claim, gradual axial shape change is the defensible rule, Dong JASA 2024 enclosure masking; **no public repo searches superformula horn parameters â€” verified GitHub-wide, a genuine first**). **P6b basis:** fixed-budget primary (anytime-slice {100,200,400}), gap-closed normalization, 30 surrogate / 10-15 real-GPU seeds with honest power framing, Wilcoxon rank-sum + Holm + Ã‚12 with ONE pre-registered endpoint; **GSA library audit â†’ own ~120-line module + 8 named tests + 10 pitfall requirements** (no maintained GSA exists: nevergrad/mealpy/pagmo = no, NiaPy = retuned variant, canonical MATLAB port = unlicensed; GSA-NGC = unverifiable, still barred from configs/docs); the crippled-GSA budget trap handled by a mandatory offline N/g0 tuning stage; decision rule D17 pre-registered. Plan structure: work packages WP-P6a-1/2 + WP-P6b-1/2/3 + WP-P6-GUI-1/2 (mouth-outline SVG preview + `#/bakeoff` view) + WP-P6-4 senior pass; FOUR parallel Wave-1 lanes with zero file overlap + verbatim dispatch prompts; checkpoints CP-P6-0..4. **Execution gates unchanged (both required): WP1-WP17 complete + owner GO (P6a/P6b independently runnable).** Still open: the collaborator's "AVE" spelling. No code, configs, tests, or GPU touched; committed and pushed with this commit (owner directive, 2026-10-25).

Added 2026-10-25 (typology-expansion + scoring full-repair pass, CLOSE OF ROUND - see CONTINUITY entry same date):

- [ ] **Open (next handoff): C4 catalog completion** - add the 5 new configs (biradial_keele / qtw_waveguide / salmon_x_signed / salmon_ripple12 / lecleach_asym_odd) + the salmon_saddle_v2 + the iwata_ar-2in + the toroidal JMLC-350 variants to examples/catalog.yaml (the header/fields already document them; lecleach_asym_odd = the NEW symmetry value full, quadrants 1234).
- [ ] **Open: C3 the Tritonia-law rows kind** (the published alpha(theta) power laws over the OS-SE base, amplitudes as genes; fully specified in 12_RESEARCH_BASIS 13.7 - primary pages fetched + verified) + the segmentizing genes (seg-horn eqs 2-4) as the follow-on.
- [ ] **Open: P8b owner decision - the diagonal-consistency objective term** (45/135 vs H/V from the stored balloon; no new solves) - the only scoring change that DIRECTLY rewards the figure-8/puckered class.
- [ ] **Open: GPU smoke matrix** for the 5 new configs (M4 pattern: ONE job machine-wide, runs/.gpu.lock, gpu-clean before/after, fresh cache-dir, external VRAM poll; bytecheck evidence per the m4/m5b template).
- [ ] **Open: Phase D baseline tables** - per-typology K-law default knobs + default briefs carrying target.f0_hz + objective v3 (the landed axi_2in_large.yaml = the template).
- [ ] **Open: GUI hybridization (P8d)** - compose-wizard multi-typology hybrid runs + the seed-gate fixed to the SELECTED brief (gui/data.py:958-969 finding) + feasibility/derived-mouth in the compose preview.
- [ ] **Open: Oracle physics review** of the new typology claims (the house norm for typology code).
- [x] LANDED this round: biradial + qtw_waveguide generator types (R9-sourced) + the splice C1 fix (0.5-deg bar) + signed x_amp v2 + the lecleach_asym odd-cosine full-ring rows kind (mesh-proven on the real adapter) + the even-lobe mouth ripple + the full span + objective v3 (the below-f0 mask + freq-weighted cov) + the K-law feasibility preflight + the brief-derived seed/bounds (clamp-only) + the axi-brief compat refusal + graded penalty on the organic configs + the stale-Le-Cleac'h/docstring catalog fixes + 5 research dossiers + 12_RESEARCH_BASIS 13.1-13.8 + NEXT_DEV_PRIORITIES P8 + NOTES record. Suite 1461/0/0/0 (runs/s1a_suite/suite_final.xml).
- [ ] **Infra: opencode restart needed** - the subagent provider fallback (.opencode/oh-my-opencode-slim.json flipped to ollama-cloud primary after the deepseek outage killed 5 launches with empty results) binds at the next opencode start.

Added 2026-10-25 (ATH framework pass, local-only):
- [x] Native morph_* (incl. morph_exponent, target 3) on OSSE / R-OSSE / ICW / FREEFORM; generator opt-in through the same knobs; absent target = byte-identical.
- [x] `ath_core` (native OSSE, 15 searchable knobs incl. Morph target/exponent/width/height/corner/rate/fixed) + `ath_twinray_380` (published-dimension superellipse reconstruction, 12 knobs); catalog + briefs + catalog/param artifacts.
- [x] First GPU seeds + dry-runs + 1606/0/0/0 offline suite; evidence docs/evidence/ATH_TYPOLOGIES_2026-10-25.md; dossier docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md.
- [ ] Open: exact CORE a(phi) law (needs a rows/generator extension); FREEFORM rectangle morph on an elliptical H/V base trips the mesher non-convex guard (measured); Mesh.Roundover / Ath Rollback / enclosure fidelity; an owner-approved morph campaign.
- [x] Senior review 2026-10-26: morph_target 0..3 guard (R-3) + test; ATH lane committed; suite 1607/0/0/0.
- [ ] Open (campaign 2026-10-26): Phase 0 code fixes (seed_policy explicit, target.f0_v_hz, ICW nested r0 pin, rows span half_xz), campaign briefs/configs, night runner, smoke night - handed off to another agent.

Added 2026-10-26 (campaign Phase 0, implementation lane code-1):
- [x] `generator.seed_policy: explicit`: skips the f0 seed/bounds derivation while keeping the K-law feasibility block; `derive`/absent is byte-identical (config_sha + derived seeds pinned). Validation refuses any other value as `generator.seed_policy`. Directive stripped before materialize/mesher. Tests `tests/test_config_seed_policy.py` (10/10); gate 1626/0/0/0 (`runs/step2a/suite.xml`).
- [ ] Open (this lane next): ICW nested `icw_seed.r0_mm` WP2 driver pin (Step 2C). Other Phase 0 items (target.f0_v_hz, rows span half_xz, campaign configs, night runner) remain with their owning lanes.
- [x] ICW nested driver pin: `icw_seed.r0_mm` is now forced/refused by the same WP2 `_force_pin` rule as root `r0_mm`; new `tests/test_config_icw_driver_pin.py` (4/4); gate 1630/0/0/0 (`runs/step2c/suite.xml`). Remaining Phase 0 items stay with their owning lanes.

Added 2026-10-26 (campaign Phase 0, implementation lane code-2):
- [x] Objective v3 amendment: optional per-plane `target.f0_v_hz` (owner-directed). When set, cov is the sum of the H error over `f >= f0_hz` and the V error over `f >= f0_v_hz` (freq_weights restricted per mask); `dislope` keeps the H/f0 mask. Validation refuses `f0_v_hz < f0_hz` or `> band_hi_hz`, naming `target.f0_v_hz`. Absent = the pre-amendment expression verbatim (config_sha/seed/solve-spec/J goldens pinned bit-identical; dataset/feasibility records emit the key only when set). New `tests/test_objective_v3_f0v.py` (9/9); gate 1639/0/0/0 (`runs/step2b/suite.xml`). `docs/plan/01_CONTRACTS.md` untouched (frozen); dated amendment in CONTINUITY + NOTES_FOR_SENIOR.
- [ ] Open (this lane next): Phase 0 Step 2D (`span: half_xz` rows model for `lecleach_asym_odd`) and Step 2E doc fixes; the GPU half-vs-full equivalence A/B stays Phase B item 5.

- [x] Overnight campaign night runner landed (RUNNER lane files, committed by impl-code2): `tools/run_campaign_night.py` + `tests/test_tools_night_runner.py` (9/9). Sequential one-GPU protocol (julia kill + `gpu-clean` + lock wait + VRAM baseline, per-job timeout/tee, ndjson eval accounting instead of `--budget`, `summary.jsonl` + `SUMMARY.md`, no retries). Gate 1639/0/0/0 (`runs/step2-runner/suite.xml`).

- [x] Phase 0 Step 2D `span: half_xz`: rows span phi 0..180 (ODD n_phi >= 25, upper half across xz, quadrants `'12'`) for `lecleach_asym` (its `cos(phi)` term is even under the up/down mirror; plain `span: half` stays refused). `_GRID_SYMMETRY_AXES` now derives `'12' -> ('y',)` from `sizing.SYMMETRY_PLANE`; `grid_outer_points(half_xz=True)`; mesh/outer-shell call sites updated. Measured CPU: half mirrors the full ring to 1.7e-13 mm, 1,485 tris vs 3,036 (2.04x). New `tests/test_design_generators_grid_halfxz.py` (5/5); param catalog regenerated; gate 1644/0/0/0 (`runs/step2d/suite.xml`).
- [ ] Open: Phase B item 5 GPU half-vs-full A/B (<=0.05 dB / <=1 deg) before switching `lecleach_asym_odd` from `span: full` to `half_xz` in campaign cells. **Backend gap found while landing 2D:** `hornlab_beat_bem` rejects `native_symmetry_plane='xz'` (BEAT mirrors x=0 / x+y only) while `hornlab_bempp_bem` accepts it, so the A/B needs the bempp route or a pinned-fork change; no solver code was changed here. Step 2E doc fixes remain for this lane.

- [x] Phase 0 Step 2E doc fixes: dated correction at the TOP of the S1A verbatim oracle record (the biradial `widened_to_closure` widening is K-law-driven, reached 396.9/352.8 mm, past closure; body unchanged). CONTINUITY records that the scalar `n_in_band` is the COV-SCORED point count (screen 9 / verify 21 for an f0-850 brief), not the band count, and that the field is NOT renamed (stored records + frozen terms key set); with `f0_v_hz` set it is the H-mask count. INDEX/CODE_MAP untouched (no new doc/module). Gate 1644/0/0/0 (`runs/step2e/suite.xml`). No GPU/Julia work.
- [x] GUI discovery 2026-10-26: configs/briefs at any depth, no run cap, auto per-brief leaderboards from run folders, night runner on the Status page.
- [ ] Campaign config lane: b1t__lecleach_iwata_ar.yaml spells a retired product name (neutral-naming test fails) - fix before the smoke night.
- [x] Sandbox 2026-10-26: free/search-limits switch, explore ranges, fixed-knob sliders, Morph card + save-as-search-rows, refused shapes drawn, measured size/envelope, 3D fold tolerance; self-approach chord-vs-arc false refusal fixed.
- [ ] Param catalog generator scans examples/typologies/*.yaml only - campaign subfolder configs get no tooltips until it recurses (sandbox falls back to the config file).
- [x] Ath crease class: OS-SE guiding curve exposed in the sandbox (OSSE); mesher config refusals shown, not 500.
- [ ] Open: native-OSSE TwinRay/CORE typology that searches gcurve_* + Morph (the crease class); per-azimuth a(p) expression knobs.
- [x] README rewrite with GUI screenshots; main fast-forwarded (2026-10-26).
- [x] 2026-10-26 learnings recorded (docs/research/LEARNINGS_2026-10-26.md).


Local-only, added 2026-10-27 (no GitHub issue state changed): objective v4 implemented + two v4 GPU nights (first + resume); open: re-run crease__osse_b1w (resume startup failure), biradial_keele cells refuse ~90 % of candidates, HF data sync tabled (P11), merge of unified-typologies to main.

Local-only, added 2026-10-27 (evening; no GitHub issue state changed): resume night done; ripple/ridge night running (10 jobs); P12 sim-vs-real investigation opened (loading weight 0 on most briefs, ideal source, generous cov) with the SIM_VS_REAL research report; pushed to main.

Local-only, added 2026-11-02 (no GitHub issue state changed): GUI frequency-axis band + scoring-floor f0 marker landed with offline pins (37 tests pass across the three GUI test files); MEH CPU-vs-CUDA benchmark scripts committed under tools/bench/.
Local-only, added 2026-11-02 (no GitHub issue state changed): **P11 HF data sync DONE** - public dataset repo <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> (7 tar shards, 10.77 GB packed: text/solve/dataset; meshes not uploaded), `tools/hf_sync.py` corrected to `hf upload`. Owner-machine finding: Xet uploads stall here; upload with `HF_HUB_DISABLE_XET=1`. Still open in P11: merge to `main` (which branches) and the two v4 re-runs.

Local-only, added 2026-10-29 (owner-delegated hardened solve plan; no GitHub issue state changed): A1 canonical gate-audit tool/output under tools/rescore/gate_audit.py + docs/data/gate_audit_2026-10-29/; B1 published TwinRay 380 seed verify PASS (LFP20 566.6 Hz, acceptance 518-651); C0 extended-throat r0/a0 derivation; B2 explicit grid.screen_extra_hz [250,315,400,2573,3311,4260] -> 18-point screen grid; C1-C5 objective v5 (loading/LFP, flat_cv, CD pattern, round-throat refusal, asymmetric V); D searches b3bt-600, b3a-480, b1w-850, room-shelf-800. Stop after top-10 verify + A1 rerun; no 12/16 kHz pass and no print. Detailed owner decisions: docs/CONTINUITY.md 2026-10-29 entry.

Local-only, added 2026-10-29 (fast-BEM research; no code/GPU; no GitHub issue state changed):
- [ ] **OPEN: quadrature order A/B (highest value).** Order 4 = 36 point-pairs/element-pair, order 2 = 9 (4x fewer; `forks/hornlab-beat-bem/docs/beat-engine-CUDA.md:53`; `forks/hornlab-beat-bem/hornlab_beat_bem/config.py:32,405`). The fork's wavelength selector (`kh` cutoffs q1_max=0 / q2_max=2.0) exists but is CPU-only and discarded on CUDA (`julia/BeatEngineDriver.jl:186-187,1766-1773`). Validate order 2 at 500 Hz / 2 kHz / 8 kHz; expose `solve.quadrature_order` through `SolveSpec.extra` (hashed); port the selector only if 8 kHz fails while low/mid pass. Report: `docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md` section 5.
- [ ] **OPEN: GMRES-on-CUDA A/B (second).** No CUDA GMRES exists; the fused CUDA solve is a direct `lu!` (`julia/src/BeatEngineCudaBurtonMiller.jl:642-648`). Reuse `BeatEngineDenseSolve.jl` GMRES with a CUDA matvec; keep FP64 Krylov; no silent default. Expected 1.0-1.4x speed plus ~1.0-1.8 GB peak-VRAM saving [inferred] - the memory win is the point.
- [ ] **OPEN: bempp FMM/OSRC CPU probe (third, off the GPU lane).** bempp-cl 0.4.2 ships an ExaFMM hook but `exafmm` is not installed in `.venv`; our adapter also refuses Burton-Miller + native symmetry (`NOTES_FOR_SENIOR.md:150`), so a probe runs full meshes. Use it to calibrate FMM constants at kD ~ 100, not as a production path.
- [ ] **OPEN: PVFMM/FMM3D only if the quadrature path fails and a 14k+ workflow is actually required.** PVFMM is GPU but the Burton-Miller layer is months; FMM3D `hfmm3d` is CPU (Apache-2.0). Stop rules in the report section 9.
- [ ] **OPEN: owner sign-off needed for any fork change** (pinned SHA + validation ladder per `docs/FORKS.md`); no new solver written (hard rule 2).
- [ ] **OPEN: do NOT default GMRES.** The cost-model router (`BeatEngineDenseSolve.jl:317-355`) exists because a threshold is wrong across machines and backends.
- [ ] **OPEN: any new flag must ride `SolveSpec.extra` and change the solve hash** (`hornlab_search/types.py:96-101`); absent = byte-identical to today. Also fix the double-misnomer: `gmres_tol` is hashed/recorded but never applied on Beat (`solve/beat.py:24-25`), and `CAMPAIGN_SMOKE`'s "iterative solve" is a dense LU.
- Report path: `docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md`; priorities `NEXT_DEV_PRIORITIES.md` P13; research basis `plan/12_RESEARCH_BASIS.md` section 18.

Local-only, added 2026-11-13 (**bo-study-v1.1 pushed; cloud completion kickoff in docs/research/bo_study/; no GitHub issue state changed**):
- Open: runner production evaluator adapter (blocks the S9 A/B matrix execution) ï¿½ owner `docs/throughput/BO_STUDY_PERF_PREP_2026-11-12.md`.
- Open: execute the validated S11 pilot manifests (execution_authorized=false by design; wall deadline owner-gated).
- Open: M2 sensitivity/pool diagnostic evidence over the real 197-row native TrainingSet (`hornlab_search/bo/data.py::build_native_training_set`).
- Open: B8 full adversarial loop (fake evaluator through service/CLI/API/GUI, crash/idempotency matrix).
- Open: pyproject optional `bayes` extra registration (isolated `bayes-venv` remains the sanctioned engine env).
- Data note: 3 native shard-57 rows (276-278) uncatalogued at the S0 snapshot; refused at join (`catalog_row_missing`), recoverable by a fresh catalog export.





