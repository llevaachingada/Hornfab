# CONTINUITY

## Archive

Entries dated before 2026-11-01 are archived verbatim; every November entry stays live.

- 2026-10-12 to 2026-10-22 (44 blocks): [docs/history/CONTINUITY_2026-10-12_2026-10-22.md](history/CONTINUITY_2026-10-12_2026-10-22.md) (rotated 2026-10-30).
- 2026-10-23 to 2026-10-31 (158 blocks): [docs/history/CONTINUITY_2026-10-23_2026-10-31.md](history/CONTINUITY_2026-10-23_2026-10-31.md) (rotated 2026-11-25).
- Machine-readable index: [docs/history/manifest.json](history/manifest.json).

## 2026-11-27 - Consolidation: uncommitted 11-25 work committed, metric-BO docs restored, branches synced

- **Owner ask:** commit everything left uncommitted, sync local main/hornfab-all/GitHub, toward one checkout.
- **Committed:** `2ad05ba0` throat-sculpt typology pilot (generator `throat_sculpt_family.py`, 6 geometry tools,
  configs, research, evidence; 11 tests pass; not yet in the generator registry) and this commit: the
  2026-11-25 repo-findability docs reorganisation (slim AGENTS/CLAUDE, START_HERE/TOOLS/SCORING_REFERENCE/
  FAMILY_LAWS, family cards, 3 skills, ~50 docs archived, CONTINUITY Oct entries split to `docs/history/`).
  Link check: live-tree broken links ~12 (the reorg's own report: 29 before / 31 after); 405 more sit in
  verbatim history snapshots. Code/tests mention moved docs only in comments/docstrings.
- **Restored:** 10 `docs/research/metric_bo_2026-11-22/` docs (02-10 + ADR) that existed only on
  `feat/metric-aware-bo` (its code was already integrated 2026-11-25).
- **Not done:** `cd_bo_cohort_2026-11-25` night died 2026-11-26 ~14:33 (`rolled_r8` exit 1, `lcl_beak_cohort`
  no exit record); GPU lock stale - run `gpu-clean` before the next solve. PRs #75/#77 still open. Fix D open.

## 2026-11-25 - Metric-aware BO: real canary, adaptive continuation, cohort admission and handoff

- Integrated the `feat/metric-aware-bo` stack (`8c815e2e`) into the canonical tree. Feature-only
  modules now live in `bo/metric_*.py`, `bo/physical_composite.py`, `studies/metric_study.py`,
  `studies/metric_refit.py`, `studies/metric_lineage.py`, `studies/metric_intake.py` and
  `dataset/catalog_identity.py`; canonical `builders.py`/`bo/metrics.py`/`config.py` admission and
  v11 policy freeze remain authoritative. `studies/production.py` keeps `objective_admission` and
  adds the metric measurement path; `search/evaluate.py` records `dataset_position` and supports a
  study-scoped `run_id`.
- Real worker + durable refit: `metric_composite_v1` routes through `MetricTrainingBinding` and
  `fit_and_propose(require_identity=True)`; refit every 4 accepted unique screens; immutable
  `metric-refit-snapshot-v1` published before the append-only pointer; verify/cache/duplicate/
  failed/parity-refused rows excluded; backend calls counted once and recovered from the journal.
- Clean Home v11 Fold canary (study `46cd5e1d...`, package `3bf53815...`): 8 screen + 2 verify,
  refits at 4 and 8 (snapshots `c1c35661...` n=178 and `f4962d41...` n=182), post-refit proposals,
  best screen 5.121289, verify 4.791516 (`30e9fc43aa80`, 285x256x432 mm, DI 12.45->15.36 dB).
  A first rehearsal package (`3e16eab7...`) spent 8+2 calls with no refit because the refit
  validator required a 64-hex catalog id; fixed to the real 16-hex `physical_solve_id`, validated
  on a copy of the journal, then re-run.
- Acquisition confirmation (frozen 174 rows): 81271 HOLD (recall 0.50 vs 0.75), 81281 PASS,
  81291 PASS -> **PASS FOR EXPLORATORY PILOT** on the pre-frozen 2-of-3 rule. The 81271 HOLD stands
  unretuned; the pre-declared LMC arm passed 81281 but lost on both opened diagnosis slates and was
  not promoted. Evidence: `runs/v11_bo_day_planning/acquisition_confirmation_2026-11-23/`.
- Adaptive continuation staged/held: `metric_lineage.promote_metric_refit` promotes the gen-2
  artifact into child `a5d78f8d...` (182 rows) with explicit lineage; package `7c64fd32...`
  (`metric-adaptive-20x2`, 20 screen + 2 verify = 28 total), approvals and held queue; dry run 0
  calls, held execute exit 6.
- Cohort admission (canonical replay + strict 170-190 row artifact + frozen chronological holdout):
  PASS `home_morph_v11_port` (metric median 3.654 vs 4.359), `home_twinray_v11_open` (recall 0.75),
  `home_core_petal_v11_open` (tie), `photo_twinray_xo900_v11` (tie), `r3_c500` (recall 0.00 vs
  0.50); HOLD `c400_v11_open` (recall 0.25/0.00, best-at-k loss) and `photo_osse_morph_xo900_v11`
  (recall 0.50/0.75); `home_ext_throat_v11_open` is 1/180 replay (projection mismatch) and not
  admissible with the current config.
- Held canaries prepared: home_morph `9c6264f5...`, home_twinray `80cacbf7...`, home_petal
  `4b09ef22...`, photo twinray 900 `506a72fa...`; combined held queue
  `docs/queue/v11_bo_day_2026-11-23/native_metric_canaries_HELD.yaml` and the 900 Hz queue. Each
  dry run made 0 backend calls; held execute refused with exit 6. No launch.
- Generated-space seam fixed: `study_cohort._metric_candidates` and the run-dir `cohort_lib` are
  recipe-aware (`metric_intake._historical_design`); c500 211/211, FAV 184/184, room_w90x50 193/193
  replay. c500 strict artifact (study `77ed21b5...`, checksum `1ec02ccc...`) and holdout PASS;
  `build_metric_pool` still returns no candidates for the generated study, blocking a c500 package.
- GUI: opt-in metric panel with identity/revision/observed-vs-predicted/refusal state and the same
  release gate; 12 new tests plus 123 GUI/study neighbours pass. Generated-space intake 33 tests.
- Regression: integrated combined suite **512 passed, 0 failed, 0 errors, 0 skipped** (291.8 s);
  canary/refit/package/CLI 37 passed; generated/cohort seam 45 passed. Pre-existing, not this pass:
  `test_dataset_manifest` expects objective versions without 11; the dataset-store 500-append
  timing test is load-sensitive under the live GPU night.
- Handoff and inventory: `docs/research/metric_bo_2026-11-22/12_HANDOFF_2026-11-24.md`,
  `runs/v11_bo_day_planning/{CANARY_2026-11-24.md,NEXT_COHORTS_2026-11-24.md}`. Tree committed as
  a consolidated snapshot; the live night and its screen12k jobs were left untouched.

## 2026-11-25 - variable mesh audit: 1.5 supported; CAD/mounted inert; density view

- Scope: spatial mesh resolution only; the 12 kHz SCREEN grid/scoring was untouched. Evidence executed 2026-11-23/24; packet `docs/evidence/variable_mesh_2026-11-23/`.
- The formula routes already graded correctly: class-1 throat p50 3.55 mm vs inner bore 6.12 vs mouth 7.01; outer shell p50 7.15 -> 10.71 -> 14.05 mm at factor 1.0/1.5/2.0, with inner/throat/mouth unchanged. Unknown-region fraction is 0.00% on formula classes after the audit fixes.
- DOF: factor 1.5 is -21.96..-22.32% on the four formula classes; 2.0 is -29.68..-29.94%; point-grid -7.4% (saturates at 1.5 under the wall-clearance guard); CAD and mounted/enclosure 0% (inert, now recorded as not applied).
- Acoustic A/B on frozen grids (`beat_cpu` CPU lane): worst deviations vs the epq-9 reference are 8 kHz 0.0241 dB on-axis / 0.0183 dB DI / 0.162 deg / 0.00227 z; 10 kHz 0.0126 / 0.0064 / 0.054 / 0.00132; 12 kHz leader 0.0230 / 0.0224 / 0.122 / 0.00169. The predeclared criteria (0.20 dB / 0.15 dB / 1.0 deg / 0.03) pass with 6-9x margin at 12 kHz and >15x at 10 kHz. Diagonal maxima sit at rear nulls; bounded complex error 0.0030-0.0107.
- CPU solve time is 37-40% lower and complete candidate 31-43% lower at 1.5. GPU wall time was NOT measured because the 12 kHz queue owned the GPU; the DOF target is met.
- Implemented `tools/analysis/mesh_region_audit.py`, `mesh_policy_ab.py`, `mesh_acoustic_ab.py`; GUI density payload/view with decimation and solved/stored disclosure; additive mesher/grid/CAD/mounting provenance. Focused tests: 107 passed in 58.75 s (`logs/tests.txt`).
- Decision: keep `rear_res_factor: 1.5` explicit for new formula-class runs; do NOT change `config.py`'s 1.0 default (resume/hash semantics); 2.0 opt-in only; CAD and mounted/enclosure rear coarsening unsupported. Integration contract: `ADOPTION_DECISION.md`; rollback = set 1.0.
- Open: GPU wall-time/VRAM confirmation when the queue frees; CAD T2 is valid only to 5023 Hz at a 10 kHz request; the point-grid fine-reference cap remains.

## 2026-11-25 (evening) - favL__2in_c500 continuation: walls opened, inert knobs narrowed, 150 valid running

- Owner ask: open the wall-pinned knobs on run `20261121T003823Z-screen-75c147` (80 valid, best J 1.870458, `0ae816f04c06`), narrow the inert ones, continue 150 solves, and keep the rows usable by scalar and metric-aware BO. Built `examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115.yaml` (`envelope.enforce: false`, `max_utilization: 1.15`; there is no soft size term in J, `size_feasibility` is post-hoc) and `examples/typologies/favL_2026-11-20/favL__2in_c500_open115.yaml`.
- Box: `g_k` 0.85-1.35 (was 1.0-2.2; best 1.001, rho +0.58, 2/6 low), `g_a_v_deg` 27.5-34.5 (was 20-31; best 31.0, rho -0.55, 5/6 high), `g_throat_hv_ratio` 0.85-1.8 (was 1.0-4.0; 3/6 low), `g_s` 0.30-0.40; inert `g_sf_amt` 0.19-0.26, `g_sf_ab` 0.86-0.91, `g_n` 2.5-3.1, `g_a_h_deg` 32.2-34.5, `g_L_mm` 230-275, `g_wrap_deg` 70-130, `g_r_lip_mm` 13-23. Seed = parent best; warm start from `75c147`, top-10 spread 0.2696 -> sigma0 0.12, `allow_cross_brief` because the only brief delta is the envelope policy (every parent row is inside the open cap; the solve hash is untouched).
- Gates: `shape_check` yes (4117/24000 DOF, mouth 491x436 mm, depth 255 mm, round coupling); `search_preflight --samples 64` 64/64 meshed valid, 0 refusals; legal-range probe covers the desired box; uniform admission 128/128 through the generator and the canonical `DesignSpace`; BO `ActiveProjection` d=11 round-trip.
- Launched 15:47 EST as job `favl_c500_open115_150` at the FRONT of the paused `cd_bo_cohort_2026-11-25` night (owner choice) and resumed it; run `runs/20261125T204727Z-screen-02b4bf`. First rows: n=0 1.870457 (parent best replay), n=1 1.807058, n=4 **1.691470** (-9.6 %); 12/12 valid, 0 refusals at the first read. The run continues unattended; the cohort's 5 pending jobs follow under the same runner.
- BO identity: the open brief + changed box is a NEW frozen identity; the parent's 80 closed-identity rows are not pooled (intake fail-closed). 150 valid clears the >= 100 metric-BO gate on its own and stays under the 256 cap. Partial-data smoke: `study_cohort` -> 6/6 `exact_complete`, one dependency/grid/brief group, d=11, zero exclusions; `needs_initial_data` only at n_min 24. After completion: strict metric-BO artifact + frozen holdout for this identity, then verify the finalist on the common grid.
- Evidence: `docs/evidence/favL_2in_c500_continue_2026-11-25/` (`PREDECLARED.md`, `probe.json`, preflight/shape-check/cohort outputs). Reusable builder: `build.py`.

## 2026-11-25 (afternoon) — CD variants of non-CD returned-lip horns: none passes, Le Cléac'h H/V closest

- New kind `rows_bb_v1` (`hornlab_search/design/generators/cd_backbone_rows_family.py`, own module so the batch 1–7 backbone digests are unchanged) wraps generic rows parents (`lecleach`, `lecleach_ar`, `iwata_ar`, …) as LABELED CD HYBRIDS; `apply_cd_backbone.py --base-config` re-scores a parent from another brief and checks neutral = bare parent verify mesh byte-for-byte. Tests: 51 pass (`runs/cd_variants_tests.xml`).
- 14 predeclared verify solves (2 batches, v11cd brief, epw 6) on Le Cléac'h AR `5f7fbfc276b9`, Le Cléac'h H/V `a85be6929ad5`, Iwata AR `06a008612260`: **no candidate passes the six rules**. Controls narrow to 39–40° H at 8 kHz; the backbone adds +17 to +21° there, but best 8 kHz H is 59.9° (floor 62°) and 2–4 kHz waistbands appear. Closest: `lcl_bb_h100_v000_t25_r20` (6–8 kHz H 65.2–58.7°, 2–4 kHz 61.8–75.0°, loading kept). Section hypothesis (`bb_v` 1.0) rejected. Salmon excluded (608.7 mm tall > 480). Stop rule applied; next lever is a labeled mouth/roll-on change. [Readout](evidence/cd_variants_2026-11-25/README.md).

## 2026-11-25 (noon) — CD backbone: recipe transfers to a second rolled body; Lamé stops; cross-application survey

- Batch 6 (4 Lamé solves): longer throat + shorter roll-in move the 2.7 kHz waistband to 2.3 kHz and lift loading to 0.554–0.608 (floor 0.617); no pass, best J 6.851. Lamé line stopped: needs a mouth/rollback or depth change, not body knobs.
- Batch 7 (3 solves): rolled keeper `bb_h` 0.65 / throat 0.25 on a second rolled body `20874108fe25` passes all six rules vs its own control; 6–8 kHz H within 0.3° of the first body (8 kHz 54.5 → 68.3°), J 7.683 → 4.562.
- Survey of saved rows families: lever applies to rolled designs on the CD brief; sculpted R-OSSE and OSSE rollback already carry it natively; Le Cléac'h/Iwata/Salmon are on loading-first briefs and must not get a CD backbone. New tool `tools/geometry/apply_cd_backbone.py` wraps any saved rolled/Lamé Phase A design (neutral parity checked). [Readout](evidence/cd_backbone_2026-11-25/README.md).

## 2026-11-25 (late morning) — CD backbone batches 4–5: throat transition fixes the loading edge

- 7 verify solves (6 at epw 6, 1 at epw 9), predeclared in `docs/evidence/cd_backbone_2026-11-25/PREDECLARED.md` (batch-4 addendum). The `bb_h` 0.65 loading failure sits at 896 Hz and follows the near-throat flare: `g_bb_throat_frac` 0.15 → 0.25 lifts Re z 0.864 → 1.085 (min 0.993); roll-in changes it by ≤ 0.035.
- New rolled keeper `rolled_bb_h065_th025`: H ≥ 68.5° at all 6–8 kHz bins (8 kHz 54.8 → 68.5°), 2–4 kHz H 76.5–82.3°, all six rules pass, epw-9 gate passes (deltas ≤ 0.3°), J 8.121 → 4.679. A longer throat costs top-octave H (8 kHz 70.9 / 68.5 / 66.9° at throat 0.15 / 0.25 / 0.30), which the station-map heuristic missed.
- Not committed. [Readout](evidence/cd_backbone_2026-11-25/README.md).

## 2026-11-25 — CD wall-angle backbone: rolled bb_h 0.5 passes, Lamé waistbands

- Versioned kernel `hornlab_search/design/generators/_cd_backbone_v1.py` + adapter `cd_backbone_family.py` (kinds `rolled_family_rect_bb_v1`, `klangfilm_lame_hv_bb_v1`), wired through `grid.py` / `generated.py` / `mesh/build.py`. Each pre-roll row is blended at equal arc fraction toward a CD schedule (throat angle -> theta_c -> the parent's own tangent at its roll-on station) with `lam(psi) = bb_h cos^2 + bb_v sin^2`; throat/roll-on stations, return and rim stay within 1e-13 mm and zero strength returns the parent bit-for-bit (`neutral_parity.json`). Tests `tests/test_cd_backbone_geometry.py` + parents: 32 pass, 0 failures.
- 5 predeclared verify solves (4 at epw 6, 1 refined; v11 frozen, 29-frequency grid). Rolled `bb_h` 0.5: H 69.0 / 68.4 / 67.6 / 67.5 / 65.7 deg at 6085-8000 Hz (control 62.5 -> 54.8), H 72.4-80.6 deg across 2-4 kHz, V not narrower, no multilobe, min Re(z) 0.991 → 0.997, J 8.121 → 5.407; deltas hold within 0.2 deg at epw 9 (J 5.377). Rolled 1.0 fails the 2-4 kHz ceiling (87.0 deg at 4037 Hz) and loading (min Re(z) 0.610).
- Lame on `morph_frac` 0.40: `bb_h` 0.5 misses 8 kHz (60.5 deg) and loses loading; `bb_h` 1.0 reaches 69.8-75.7 deg at 6-8 kHz but waistbands to 46.8 deg at 2678 Hz and min Re(z) 0.487 → fails the predeclared band and loading rules. V remains capped by the roll-on budget (moving the V roll-on outward is an owner decision); the conditional CMA over (bb_h, bb_v, throat fraction, roll-in fraction) is unlocked for rolled but not run.
- Dose bracket (predeclared addendum, 3 more solves): H at 8 kHz 60.1 / 64.1 / 70.9 deg for bb_h 0.35 / 0.45 / 0.65. 0.35 misses the 62 deg HF floor and has J 6.474; 0.45 passes every rule (J 5.743); 0.65 passes the H band, V and lobe rules with the lowest J of the batch (4.676) but fails loading (min Re(z) 0.864, 0.127 worse than control). Passing interval 0.45-0.50; J has no minimum on this axis, so the conditional CMA (still not run) must be scored against the six pass rules. [Evidence](evidence/cd_backbone_2026-11-25/README.md).

## 2026-11-24/25 — directivity attribution: early-wall levers widen 6–8 kHz H on both anchors

- 14 fixed-candidate verify solves (8 at epw 6, 6 refined-mesh/source), predeclared in `docs/evidence/directivity_attribution_2026-11-24/PREDECLARED.md`; v11 frozen. A first launch failed before any solve (relative forward-slash argv[0]; see NOTES_FOR_SENIOR).
- Rolled `fa5b207bca6d`: H amplitude causes the 2 kHz overshoot; V-only carries the combined J gain. Moving the existing CD law earlier (H +10°, window 0.12/0.40/0.65) gives H +7.6…+8.4° at 6–8 kHz, 8 kHz H 63.1° (in corridor), 2 kHz H 79.4°, J 8.121 → 6.533; deltas hold within 0.3° at epw 9. Late window: no HF authority.
- Lamé `0782945027ae`: `morph_frac` 0.40 (H +5.3…+5.6°, V +3.7…+5.1°, J 9.084) and H mid gain −2 mm (H +3.9…+4.4°, J 10.736) both widen 6–8 kHz H with throat, rim and return held; 8 kHz H still ≤ 51.6°.
- Driver exit angles: Beyma states 7–29.5° (convention unstated); CP-850Nd datasheet has no angle or outlet section. Next experiments and promotion criteria: [readout](evidence/directivity_attribution_2026-11-24/README.md).
- Geometry limit (2026-11-25): both parents keep the HF-critical wall at 5–23° while straight walls to their roll-on stations would sit near the target; a CPU-only CD-backbone blend that keeps return and rim bit-identical resolves on both anchors. No solve yet. [Dossier](research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md).

## 2026-11-24 — size-aware constraints and retained-return verify

- First local slice centralizes production/open/epsilon candidate limits, adds mesh size records, and retains compatible oversized rolled BO rows. Related score versions and historical solve keys are preserved. Strict cross-envelope cohort compatibility and family-wide geometry promotion are open.
- Exact-anchor and variant verify evidence documents a lower-J rolled result with continued H narrowing and a worse Lamé H mid-gain result. Size evidence includes three independent offline cohorts and the matched Compact500 verification queue.
- [Handoff, audited routes and runnable next slices](evidence/size_aware_2026-11-24/HANDOFF.md).

## 2026-11-23 (noon) - seedspread landed: all six round3 cohorts BO-ready (121-213 usable rows)

- **bo_data_seedspread_2026-11-23 complete (6/6):** fresh-seed CMA tranches (`--cma-seed` 31011-31016, 60 evals each) per round3 identity. Verified pooled usable (ok screen rows across all run dirs of each identity): **c500 213, fav 186, home_fold_a 177, c400a 151, c400b 145, v11_fold 121** - every cohort above the owner's >=100 data gate, five of six in the 145-213 comfort band (training-selection cap 256). Fleet bests unchanged: c400b 0.968, c400a 1.024, c500 1.705, home_fold_a 1.193, fav 3.308, v11_fold 3.429.
- **Seed-spread value:** the fresh-seed rows are sigma0-scale box coverage the resumed-CMA rows lacked (incumbent-concentrated); the maximin half of the cohort selection and the composite GP's out-of-region validity are the beneficiaries. No fresh-seed arm beat its incumbent in 60 evals (expected) - their value is coverage and seed-variance evidence for the doc-08 pilot, not new winners.
- **Mechanics:** the runner's `kind: search` argv has no `--cma-seed` passthrough (dry-run caught it), so the tranche ran as `kind: command` jobs with explicit argv - which also means the bound-pinning watchdog cannot truncate them; each tranche ran its full budget.
- **GPU spend since round3:** ~1,100 additional screen solves total across topup1/topup2/topup2b/seedspread, all dual-use (CMA progress + BO training rows). Zero queue modifications to other lanes; canonical checkout untouched.
- **Next:** Phase B cohort build + CPU validation (doc 07) on these six identities - the data side is now ready; production promotion stays owner-gated (doc 09).

## 2026-11-23 (morning) - BO data topups landed: six round3 cohorts at 90-152 usable rows; fresh-seed tranche running

- **Landed:** topup1 (6/6, +30-40 evals/arm), topup2 (3/6 - c400b/c400a refused by strict-resume cap shrink, c500 ran to **152 ok**; the home_fold_a/v11_fold/fav jobs never ran because the runner exited after c500 when its controller was killed - known-confirmed), topup2b (2/2 replacement blocks: c400b -> **114 ok**, c400a -> **121 ok**). New bests along the way: c500 **1.705** (was 1.815), fav **3.308**, v11_fold **3.429** (was 3.617). All stops after round3 were the watchdog **bound-pinning** rule (each arm's top 6 pin a box edge: L_mm/morph_corner_mm/g_L_mm/az_a_cos_pow) - round4 box-widening evidence.
- **Usable rows now (ok screens per identity):** c400b 114, c400a 121, c500 152, home_fold_a 147, v11_fold 90, fav 125. Five of six above the owner's >=100 BoTorch-data gate; v11_fold crosses it with the running seed tranche.
- **Fresh-seed tranche (running since 10:30):** `bo_data_seedspread_2026-11-23` - six FRESH CMA runs (`--cma-seed` 31011-31016, kind: command because the runner's search argv has no seed passthrough), one per config, 60 evals each. Rationale: resumed-CMA rows concentrate near the incumbent; the composite cohort selection is 64 lowest-J elites PLUS maximin diversity to 256, and GP validity outside the incumbent region needs input-space coverage. CMA seed is not part of the metric-composite identity contract, so fresh-seed rows pool with the resumed rows. Expected after this tranche: ~145-210 usable per arm, all six BO-ready. Chain note: seeded from the topup2b CONTROLLER pid (11120), which had already exited - so it started immediately; sequencing was verified collision-free (single lock holder = the seedspread solve).
- **Ops notes:** queue.ps1 `-Cutoff` is today-only (a 06:00 cutoff at 22:24 refuses to start - one relaunch lost); killing the queue controller leaves the runner alive but the runner exited after its next job anyway; strict resume refuses ANY cap shrink - raise caps, never lower; stale `.gpu.lock` holders auto-taken-over; `gpu-clean --lane gpu` cleared 2 stale hosts (VRAM idle 1.4 GiB).
- **Next:** Phase B cohort build + CPU validation (doc 07) on these six real identities; production promotion stays owner-gated (doc 09).

## 2026-11-22 (late) - bo_data_topup night: round3 cohorts extended to BO-training size

- **Topup 1 landed:** 6/6 jobs ran, +30-40 evals each (c400b 34, c400a 30, c500 30, home_fold_a 30, v11_fold 30, fav 40; zero solve failures). Cohort totals now (usable ok rows): **home_fold_a 147, fav 125, c500 122, c400a 90, v11_fold 90, c400b 84**. New bests: c500 **1.705** (was 1.815), fav **3.308**, v11_fold **3.429** (was 3.617). All arms stopped early by the watchdog **bound-pinning** rule (c400b L_mm low; c400a morph_corner low; c500 g_L high; home az_a_cos_pow low; v11_fold morph_corner low; fav g_L high) - the searches are shouting which box edge to widen in round4.
- **Topup 2 (running since 08:59):** finishing tranche to cross the >=100 owner gate everywhere and reach ~150-200. Caps must EXCEED the persisted caps topup 1 wrote (strict resume refuses a shrink: c400b/c400a were refused 151/152 < 157/162 - fixed by chaining a replacement night). Live-file caps raised for the not-yet-started jobs (home_fold_a/v11_fold/fav -> 200); `pin_ignore` set per arm for the pinned knob (boundary rows are valid, informative BO training data). Replacement night `bo_data_topup2b` (c400b/c400a, cap 200) chained via `-WaitPid 31244 -WaitMatch run_campaign_night`. Expected final usable: ~140-200 per arm, all six BO-ready.
- **Ops notes:** queue.ps1 `-Cutoff` is today-only (a 06:00 cutoff at 22:24 refuses to start - cost one relaunch); killing the controller leaves the runner alive by design; a stale `.gpu.lock` holder is auto-taken-over; `gpu-clean --lane gpu` cleared 2 stale hosts between nights (VRAM idle 1.4 GiB).

## 2026-11-22 (late) - bo_data_topup night: round3 cohorts extended to BO-training size

- **Why:** the metric-composite BO (feat/metric-aware-bo, Pass 2 complete at `39b6c9aa`) needs >=100 usable screen rows per frozen identity (recommended ~150, hard training-selection cap 256). The round3 open-envelope night left seven fresh cohorts at 53-117 usable rows (its watchdog stopped arms at 60 no-gain valid). This night resumes six of those run dirs in place - same config/brief/backend/fidelity/lib_sha, so new accepted screens pool with each existing cohort AND continue the CMA search (dual-use).
- **Headroom (owner ask):** each cap adds ~25% more evals than the to-150 usable target (round3 measured ok-rates 89-100%, invalid_geometry mostly; one timeout). Watchdog no_gain_valid/stall_valid raised 60 -> 150 so data collection is not truncated. Expected result ~145-175 usable rows per arm.
- **Queue:** `runs/nights/bo_data_topup_2026-11-22.yaml` (runner live-file), 6 resume blocks, sequential, lane gpu, `HORNLAB_GPU_LOCK=refuse`: c400b_topup (cap 157, best J 0.9679), c400a_topup (162, 1.0243), c500_topup (162, 1.815), home_fold_a_topup (194, 1.193), v11_fold_topup (161, 3.617), fav_topup (155, timeout in round3 - retry with 5400s). Dry-run validated all resume dirs/configs. First detached launch used `-Cutoff 06:00` which is today-only and refused to start; relaunched without cutoff at 22:25:53 - controller pid 44660 (parent WmiPrvSE), log `runs/nights/queue_bo_data_topup_2026-11-22.log`, julia host up, c400b rows 57 -> 59 within the first minute. Identity note: these are `*_open` briefs (envelope.enforce false, 1200 mm ceiling) - their J never ranks against closed-envelope cohorts.
- **After the night:** each top-up cohort is BO-training ready (Phase B cohort build + CPU validation per `docs/research/metric_bo_2026-11-22/07_DEFERRED_REAL_DATA_PLAN.md`); production BO runs still need the separately-gated policy promotion (doc 09 recommended next authorization).

## 2026-11-21 - Optimizer audit P0/P1 implementation (local, offline)

- Placed the senior optimizer audit at `docs/research/optimizer_audit_2026-11-21/` with [CURRENT_STATE_CHECK.md](research/optimizer_audit_2026-11-21/CURRENT_STATE_CHECK.md) (verified HEAD `bdc3f037`, clean tree, GPU lock free, ribs 0.12.0, cma 4.5.0, botorch/gpytorch absent) and [IMPLEMENTATION_STATUS.md](research/optimizer_audit_2026-11-21/IMPLEMENTATION_STATUS.md).
- **P0a:** CMA-MAE now has two distinct archives. Only the search archive is soft under `search.qd.maes`; the result archive is always hard (`learning_rate=1.0`, `threshold_min=-inf`) and is the sole source of `archive.json`/`archive_heatmap.json`. The soft archive is a labelled `archive_learning.json` diagnostic. QD protocol is `cma-me-archive-v3`; v2 runs are refused on resume with an explicit old-semantics message. Two historical v2 run dirs (`20261114T235641Z-screen-dfd27f`, `20261115T005614Z-screen-6d55fa`) are frozen read-only evidence.
- **P0b:** `tools/analysis/floor_registry.py` keys floors to objective version, resolved brief content, score identity, backend/fidelity/grid, method and sample size, with a three-part uncertainty record. Entries: v7 0.310479, v10 home 0.467739, v10 slope5 0.486317, compact400 v10xo 0.1293 (whole-fleet caveat). Unknown identity returns "no applicable published floor"; compact400 never gets the generic v10 floor. `optimizer_switch` reports typed per-kind outcome counts and no dominant failure kind on a clean run.
- **P0c:** opt-in v10/v11 production studies. v11 has a separate metric schema/hash carrying the `objective.cd` block and scalar_v11/metrics.cd code shas; v4/v7 contracts are unchanged. Admission is registry-driven (`compact400__fold_warm_v10xo`, `home_v10__morph`, `home900__landscape_v11cd`) and additionally admits a derived arm config with unchanged non-search task identity. Pareto/training metric dispatch is explicit; mixed stored versions are refused.
- **P1a:** `tools/analysis/optimizer_evidence.py` composes the run-level evidence with per-number provenance, at most two suggestions, no dispatch and no cross-version raw-J ranking; unknown floors suppress only floor-dependent advice.
- **P1b:** opt-in `search.warm_start.covariance` transfers the source mean's full `C` through the bound-span transform, with eigen floor/cap, identity blending, SPD verification and explicit scale convention; plain single-ES only, restarts/CMA-ME refused at config validation.
- **P1c:** `tools/analysis/benchmark_orchestrator.py` writes a pre-registered matched plan with self-contained arm configs and compares completed runs with seed/identity/parity checks and floor-aware verdicts; template `tools/analysis/specs/matched_optimizer_pilot_2026-11-21.yaml`. Nothing was launched.
- **Evidence:** focused CLI/suite **364 passed, 1 pre-existing botorch skip** in 78.21s; full offline profile **7 failures**, all the previously recorded other-lane items (v8 registration x2, score_identities, preflight history, B8 `study_jobs` Popen, v11 dataset census, scout40 queue count), **none in a touched file**. No GPU/solve was used.
- **Deferred:** P2 QD descriptor study and cost-aware BO pilot stay gated on the audit's matched-real-BEM authorization and owner GPU approval. No production default, score version or queue was changed.

## 2026-11-21 - System closeout: R5a, R7a, WP6 ledger, backend hardening

- **R5a done:** CPU `beat_cpu` 10 m / 5 deg equal-area Fibonacci balloon on assembled #2 (1650 points, 200/1000/2500 Hz), BL validate rc 0, solve 3/3 complete. Per-excitation DI: horn 1.86/7.46/12.12 dB, woofer 2.41/2.87/7.20 dB. R5b (declared observation standard) stays owner decision 5. [Evidence](evidence/system_evidence_2026-11-19/BALLOON_DI_POWER_2026-11-21.md).
- **R7a done:** machine record reproduces screen 0.035843/0.035833 dB2 vs BEM 1.607249/17.837761 dB2 (factors 44.84x/497.80x), stamps `DEMO_SHAPE_CONFOUNDED_R2` and `THRESHOLD_UNCHANGED_9DB2`; R7b needs the real shape plus a 5 deg or finer grid. [Record](evidence/system_evidence_2026-11-19/SCREEN_ESHAPE_CALIBRATION_RECORD_2026-11-21.json).
- **WP6 ledger:** deterministic screen->case join reports 54 cases / 22 solved, 3 matched shortlist rows, 0 solved two-channel pairs, and emits `FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS`. [Evidence](evidence/system_evidence_2026-11-19/FUNNEL_LEDGER_2026-11-21.md).
- **Backend:** B22/B26/B30 and F19 fixed; B18/B19/B28/B29 verified fixed; B20/B25/B27 accepted/documented; B21/B23/B24/F4 deferred to a design/owner pass. [Evidence](evidence/system_evidence_2026-11-19/BACKEND_CLOSEOUT_2026-11-21.md).
- **Verification:** `tests/system` **512 passed, 7 skipped**; GUI/export neighbours **42 passed**; compileall OK; real BL CPU balloon solve 3/3. The full offline profile reached 99% with the same seven documented pre-existing failures before a 20-minute shell timeout; no scoped failure.
- **State:** `docs/system_data` regenerated to 54 cases / 22 solved / 29 staged / 3 refused, 27 declared; readiness R5/R7 record R5a/R7a done with R5b/R7b still blocked. No GPU was used for this pass.

## 2026-11-21 — Sculpted home-900 V11 CMA pilot

- `sculpted_xo900_cma_pilot_2026-11-21` launched detached at 08:57 EST. R3, K axial and Crowe k-home get up to 30 valid screen solves initially. Each may reach 60 after a matched finalist check and evidence of gains continuing after call 20. Verify admission requires at least 0.08 J gain, source-patch parity, and bounded loading and preferred-width regressions.
- Normal GRID meshing reproduced the three seed meshes byte-for-byte. Each box passed 64 CPU mesh samples. A final check with the 8,900 DOF cap also passed all 20 corners. The common pilot brief keeps packaging advisory and requires complete complex full-balloon V11 results. [Queue](queue/sculpted_xo900_cma_pilot_2026-11-21.yaml).
- The first R3 screen row in `20261121T135752Z-screen-8c15a8` completed with J 2.11985792, objective 11, full-balloon CD and 41.44 seconds of GPU solve time.
- R3 exposes body sweep, diagonal opening and aperture scale. K exposes H setback and V projection, with diagonal finish coupled to H and neutral K1 reachable. Crowe retains the verified k-home seed and varies depth, H opening and core expansion. Physical roundover and protected-host C1/C2 remain in geometry validation. Focused CPU tests: 34 passed.

## 2026-11-21 — Sculpted V11 acceptance and native rollback probe

- R2 passed the fixed-mesh V11 acceptance gate with its actual CUDA response, full-balloon CD and J 3.10632665. Normal Runs shows the reused measurement with objective version 11. Packaging-advisory and primary replay matched exactly. The R0 archived field has its own offline V11 rescore and the staged coverage result remains separate.
- The dedicated discovery queue finished 7/7 at 08:30 EST. It reused six measured controls and ran one fresh GPU solve at the locked mesh and observation tier. Native R2 truncation gave J 3.12889124, +0.02256 versus R2. Source connectivity matched with about 0.00000114 mm drift. Truncation also refits the body, so an isolated physical roundover remains open. No CMA started.
- The matched R3 gain held at −0.406 J at 7 epw. K2’s finish gained −0.056 J at 8 epw while changing the projected opening. The V11 readout retains raw H/V patterns, all weighted terms, complex impedance and provenance. [Evidence](evidence/sculpted_xo900_v11_2026-11-21/README.md).

## 2026-11-21 — Eight-hour GPU validation queue

- Launched `hornfab_gpu8_2026-11-21` at 04:21 EST via detached controller PID 16772. Structural dry-run accepted seven blocks. The canonical GPU lock showed the first `R2_6` arm running. Its repeat completed at J 3.10632665 versus 3.10632670 in the first campaign, and R3 followed.
- R3 repeated at J 2.69395123. A concurrent docs-only commit changed the checkout SHA and initially stopped the comparison. A CPU replay confirmed the paired delta of −0.41237542 after checking the changed paths. The live queue file schedules the R refinement immediately after K, reusing the completed 6 epw responses.
- Six hours are reserved for sculpted R-OSSE, landscape K returns, Klangfilm B3 and Crowe P1 ridge/beak. Two hours are reserved for home-900 v11 benchmarks, Compact500 v11 and the v10 follow-ups. The local night YAML, paired response diffs and readout index are under `runs/nights/`. CPU admission and scripts are under `scratch/hornfab_gpu8_2026-11-21/`.
- Matched R2/R3 refinement uses 7 epw under the local node cap. R4 uses 7 epw because its 6 epw source patch differed. K1/K2 refinement uses 8 epw. B3 H +2° and +4° exceed the frozen 60° limit. Crowe P1's effective refinement is 7 epw due to 8 epw patch drift. The verified 2-inch compact result is reused. Crowe C1/C2 and the rolled C-return remain held.
- The original Compact500 continuation box incurred 43 envelope refusals in 64 CPU samples. The queued follow-up passed 64/64 samples with narrower depth, H angle and expansion bounds around the same verified seed. Both that search and the optional Crowe search require 64/64 clean real-mesh CPU samples immediately before admission, and each is capped at 40 attempts for 30 valid solves.
- Owner then removed packaging-size admission for this campaign. Pending CLI blocks use local brief copies with nonbinding numeric maxima because the brief schema requires three limits. Fixed-mesh admission reports dimensions without rejecting on packaging. The original Compact500 parameter bounds are back in use with the same verified seed and 30-valid budget. Source, shell, mesh and generator validity still gate admission.
- The restored Compact500 range passed 64/64 CPU mesh samples. A 528.6 mm-wide probe failed the original 500 mm packaging limit and passed under the campaign brief with a round driver interface and 4,456 DOFs. The five brief copies resolved to the same target, score, seed/bounds and mesh/solve settings before any intentional search-range change.

## 2026-11-21 - System readiness audit batch: R3/R6/R10/R11/R15/R16/R17 closed, R7 quantified

- **R3/R17:** [bassbox model-difference audit](evidence/system_evidence_2026-11-19/BASSBOX_MODEL_AUDIT_2026-11-21.md) complete (CPU recompute, no new solve). Seed box is the clean comparison: BL real is −3.5…−5.4 dB vs bassbox over 46–132 Hz (mean −4.75), matching the declared demo-shape Sd deficit 4.59 dB; the 162 Hz null is a BL interference feature. Default box: +7.4 dB at 30.4 Hz vs the damped lumped port, −1.1…−2.3 dB above 70 Hz; the NFR/end-correction mapping gives Fb 27.99–30.14 Hz, not one number. Bassbox stays a feasibility/F3/port-velocity screen. R17 port mapping fixed in the earlier commit.
- **R6 closed:** the mesh-refinement readout is in the evidence README (refine1/refine2, nulls move 9.75–15.99 dB; refine1 vs refine2 not monotonic). Convergence is **not** established; every current case is `SINGLE_MESH`. R9's float64 control rules out precision as the cause.
- **R7 quantified, stays in_progress:** [screen E_shape box-axis check](evidence/system_evidence_2026-11-19/SCREEN_ESHAPE_CALIBRATION_2026-11-21.md): screen 0.024/0.0017 dB² vs assembled BEM 1.61/17.84 dB² on the common 7-dir/3-freq grid. The proxy is optimistic and confounded by the demo 200 mm shape (R2); the 9 dB² label stays heuristic, not a system verdict.
- **R10 closed** as the recorded policy (pins in every manifest; record, don't upgrade mid-study). **R15 closed:** [10-inch catalog re-verification](evidence/system_evidence_2026-11-19/DRIVER_CATALOG_REVERIFY_2026-11-21.md) against live FaitalPRO pages; every numeric field matches, no YAML edited. **R16 closed:** clearance gate + tests; the real two-body stage case records PASS at 0.017 m aabb gap.
- **R11 closed:** [one-command real-BL lane](evidence/system_evidence_2026-11-19/REAL_BL_LANE_2026-11-21.md) (`tools/system/real_bl_lane.py`) exercised probe + stage + BL validate + 3-freq CPU solve (3/3 complete, 08:56–08:57 UTC); 8 hermetic tests.
- Readiness registry: 26 declared cases (20 approved / 6 proposed; the new R9 precision case is proposed), R3/R6/R9/R10/R11/R12/R15/R16/R17 closed, R7 in progress, R1/R2/R5/R8/R13/R14 open. Focused suite 94 passed, 3 real-BL skips. No GPU was touched.
- Census cleanup: removed the three empty aborted-case dirs (`ev_mesh_refine/...52652` and two `bl_ref_case` empties; no manifest, no project, no evidence). `docs/system_data` now exports 53 cases / 26 declared / 1 diagnostic (the pre-existing `two_way_80x50_700_pilot` manifest-payload mismatch); its README/INDEX snapshot (53 × 53; 21 solved / 29 staged / 3 refused / 0 invalid) was refreshed. Full offline profile ran: **7 failures, all pre-existing other-lane items** (v11 registration/score_identities/dataset manifest, v8 registration, preflight history, B8 study_jobs Popen, scout40 queue count); no failure in a file this pass touched.

## 2026-11-21 - System readiness R17 port mapping + R12 evidence byte-check

- **R17 fixed:** `assemble._box_to_vented_source` now inverts bassbox's effective length to the physical neck and adds both 8 mm BL provider lips before writing BL's `port_length_m` (total incl. lips). It previously passed the effective length through, lengthening the BL port by the end correction. Regression test `test_box_to_vented_source_passes_physical_total_port_length`; `tests/system/test_assemble.py` 8 passed. Existing seed-box cases were staged through `motor_map.vented_source` and already used the correct physical length; no stored case was changed.
- **R12 closed:** new `tools/system/verify_evidence_quotes.py` + `tests/system/test_verify_evidence_quotes.py` (8 passed). The three sourced blocks in `FIRST_BEM_EVIDENCE.md` are annotated; the tool reports `annotated=3 passed=3 failed=0 skipped=2 result=PASS`. The two reconstructed invocation blocks remain deliberately unannotated (no source file).
- **v2 census loader fixed:** `tools/data/system_cases.py::load_readiness` accepts `hw_readiness_v2`, reads only `cases.d/*.yaml` (or narrower `case_files` globs under `cases.d/`), merges rows and reports/excludes duplicate keys instead of last-wins; v1 behaviour unchanged. Live export: 55 cases on disk, 25 declared, 0 declared-missing; `docs/system_data` regenerated. `tests/test_tools_data_system_cases.py` 25 passed.
- **R9 closed:** float64 CPU control on the real-motor assembled #2 mesh, 6 frequencies incl. the 1641/1823/2025 Hz nulls: 948 compared complex points, max |ΔdB| 0.0029, max |Δphase| 0.012°, null depths identical to ≤0.001 dB. `precision=float64`, `lu_float64`; case `system_runs/system/ev_precision_f64/20261121T084807Z-f64_6f-33768-3be6fcf6`; [evidence](evidence/system_evidence_2026-11-19/PRECISION_FLOAT64_2026-11-21.md). Float32 is not precision-limiting this mesh.
- Open readiness work: R3 bassbox audit, R11 real-BL lane, v2 census loader, R6/R7/R10/R16 status updates. No GPU was used; the live favourite queue held the GPU lane.

## 2026-11-20 — Home 900 Hz engineering decision

- Replayed the existing named home-900 v11 identity. FAV-001 2.607618 leads the five archived finalists. The k-home verify design is effectively tied at 2.604181 with earlier loading and weaker off-axis smoothness. Same-design 900 screen/verify replay shifts reached 0.359 J.
- Added a separate experimental staged brief and report-only pattern and impedance diagnostics. The compact 500 mm envelope remains a separate identity.
- Rechecked actual sculpted mesh and source pairs. R2/R3 and K1/K2 are the initial matched comparisons. C2 source and exterior fidelity remain open. The live favorite queue owns the GPU. [Senior decision and evidence](evidence/home_xo900_2026-11-20/README.md).

## 2026-11-20 — Sculpted H/V returning meridians

- Exact R-OSSE R0 `823dc1721a76` and FAV-001 C0 `4140768780f0` remeshed byte-for-byte. R0 archive v7 replay exact. Archived-field v11 rescore 4.77995.
- Nine derivatives built at 6 epw. Same-opening R-series forward sweep spans 29–215 mm. Landscape K1/K2 span 136–149 mm. Crowe C1/C2 reach 64/121 mm.
- CPU preflight and lossless triangulated export passed. The source tessellation and Crowe exterior fidelity remain open before BEM. Geometry review and same-scale views are in [the sculpted meridians checkpoint](evidence/sculpted_meridians_2026-11-20/README.md).

## 2026-11-20 — Archived-host axial termination overlay review

- CPU rebuilds matched the original Crowe-X, extended-throat OSSE and fold-warm verify meshes byte-for-byte. All three stored v11 scores replayed exactly.
- Retaining both native sheets reproduced the extended-throat mesh through GRID. The existing record wrapper rebuilds the shell and changes its zero-arm mesh. Crowe's untouched native sheets reproduced its mesh but its wrapper acquired a different design ID.
- Hold the overlay at the geometry gate. Matched 6 epw Crowe H/V/diagonal probes moved upstream outer samples and altered the discretized source patch. The archived rolled soft-bend config reproduced its 0.932237 mm clearance failure at 5.9 epw. The 6 epw build completed, so the clearance rejection stands independently of mesh completion.
- 57 focused tests passed with pytest capture disabled. The live favorite lane held the GPU. Review, machine-readable CPU evidence and plots are in [the overlay checkpoint](evidence/termination_overlay_2026-11-20/README.md).

## 2026-11-20 ~18:50 - ATH-style diagonal ridge + H/V beak knobs on osse_rollback; lanes at the end of fav8

- Owner: ATH-style ridges for diagonal dispersion + beak on H and V. Optional knobs `g_a_d_deg` (radial diagonal angle,
  per SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15) and `g_beak_h_mm/_v_mm/_d_mm/_start` (axial C2 lip offset, Klangfilm
  hv-core law, signed). Absent = byte-identical. Tests grid + mesh + catalog **210 passed / 0 failed**.
- Lanes `examples/typologies/favRB_2026-11-20/` (3 singles + 2 CMA + verify) appended at the END of the live fav8.
  Record: `docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md` s8.

## 2026-11-20 ~18:45 - Room-targeted coverage lanes (20x16x9 ft, speakers on the 20 ft wall, wide sweet spot)

- Owner questioned 80x50 for the room. Derived: floor bounce ~35 deg below / ceiling ~48 deg above axis at ~3 m, so V 50-60
  fits; wide sweet spot -> H ~90 with toe-in crossfire. Note: `docs/research/favorites_2026-11-20/ROOM_TARGETS.md`.
- New briefs `examples/briefs/room_2026-11-20/` (w90x50/w90x60 home 700 Hz; compact 400 cube 1 kHz in w90x50, w90x60, 80x50;
  own identities). Five P1 lanes `examples/typologies/room_2026-11-20/` + verify queued after `favA9_verify_top3` in the live fav8.

## 2026-11-20 ~18:30 - 9-deg driver exit-angle brief + lanes queued

- Owner: try the 9-deg throat angle (some drivers exit at ~9 deg). Brief `examples/briefs/a9_2026-11-20/` (only
  `driver.exit_angle_deg` 9; own identity). Lanes `favA9s__fav_plain/_p1/_core` singles + `favA9__core_fav` CMA +
  verify, queued after `favSC_verify_top3` in the live fav8. shape_check 4/4, preflight no HARD. Record:
  `docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md` s7.

## 2026-11-20 ~18:27 - SplitCore variant (owner fixture) built as optional osse_rollback knobs and queued

- **Owner:** try the ideas of `HornFab_SplitCore_Analytic_Reference_Fixture.py` as a geometry variant, without
  disturbing P1. Added optional `g_k_v_log` (geometric k(phi)) and `g_v_exp_mm` (V-only exponential throat,
  quintic C2 blend back to the base V wall); absent = P1/parent unchanged. Fixture a0 9 deg not adopted (driver 2 deg).
- Tests +6 in `tests/test_design_generators_grid_osse_split.py`; grid + mesh + catalog **204 passed / 0 failed**.
- Queue (live fav8): `favSCs__fav_core`, `favSC__core_fav`, `favSC__core_polish`, `favSC_verify_top3` after
  `favP1_verify_top3`. Record: `docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md` s6.

## 2026-11-20 ~18:10 - P1 split-plane OS-SE knobs built (`g_k_v`, `g_s_v`) and queued next

- **Owner:** "Yes, build P1". `osse_rollback` gains optional `g_k_v` / `g_s_v`: k(phi) = k cos^2 + k_v sin^2,
  s(phi) = s cos^2 + s_v sin^2 (H row keeps k and s exactly); absent = byte-identical; refused together with
  `throat_hv_ratio` != 1. Tests `tests/test_design_generators_grid_osse_split.py`; grid + mesh + param-catalog
  **198 passed / 0 failed** (CPU, during the live night).
- **Queue (live fav8):** `favP1s__fav_kv3_sv` single, `favP1__split_fav`, `favP1__split_polish`, `favP1__split_2in`,
  `favP1_verify_top3` placed after the running `favL__2in_home`; `favL__kv_home`, `favM__polish_kv`,
  `favM__polish_2in_kv` (+ their verifies) removed before starting as superseded. Record:
  `docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md` s5.

## 2026-11-20 evening - FAV split-plane findings, proposal dossier, favM lanes queued

- **Measured (favL singles):** V-only k (k_H 1, k_V 3) J 4.657 vs FAV-001 4.996 with 8 kHz H unchanged (70 deg) and
  off-axis 0.574 (FAV 0.543); 2-inch same shape load 2.645 -> 0.696 (2" identity); 2" + k_V 2 overshoots (V 43 deg).
  `fav8__k1_cd_polish` best non-load `392276e62470` beats FAV-001 on every CD-matrix term (lip wrap 105, L 274).
  Table: `docs/research/favorites_2026-11-20/THROAT_LOADING_LEVERS.md` s4.
- **Proposal (owner ask: improve geometry / new typology):** `docs/research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md`.
  P1 split-plane OS-SE (new knobs `g_k_v`, `g_s_v`; H kept pure OS) recommended; P2 Keele-in-V hybrid gated on P1.
  NOT implemented (owner decision pending).
- **Queued (no code):** `favM__polish_kv` (1.4") and `favM__polish_2in_kv` (2") seeded at `392276e62470`, + verify,
  inserted after `favL_verify_top3` in the live `fav8_2026-11-20`.

## 2026-11-20 evening - FAV-001 throat-loading levers (V-only k, 2-inch exit) moved to the FRONT of fav8

- **Owner ask:** improve throat loading without losing FAV-001's directivity, a new parameter allowed; then
  "also consider a two inch compression driver size".
- **Diagnosis [measured]:** the k = 2/3/4 solves equal FAV-001 below ~2.3 kHz; the whole cost is HF beaming
  (8 kHz H 69 -> 52 deg, DI 12.5 -> 14.8 dB at k 4). V narrowing is toward target; H narrowing is the harm.
- **Levers:** 2-inch exit with the same OS law (proxy load term 2.88 -> 1.44) and V-only k through the
  EXISTING `g_throat_hv_ratio` (k = sqrt(K), rho = K -> k_H 1, k_V K; no code change). Note:
  `docs/research/favorites_2026-11-20/THROAT_LOADING_LEVERS.md`. New briefs `examples/briefs/hf2in_2026-11-20/`
  (driver r0 25.4 mm, loaded_hi 3957 Hz; own identities).
- **Queue:** 3 singles + 3 CMA lanes (80 valid) + verify inserted after the running `fav8__k1_cd_polish` in the
  live `fav8_2026-11-20` (night now ~10 h). shape_check 6/6, preflight no HARD.

## 2026-11-20 evening - FAV-001 8-hour variation night `fav8_2026-11-20` launched

- **Owner ask:** "queue up like 8 hours of solves related to variations on this new FAV horn".
- **Launched 17:14** detached (queue.ps1 pid 61992); GPU was free (fav_crowe night + xr__x_s2c tail done).
  12 CMA lanes x 80 valid + verify top 3 of every lane; est. ~8 h. Plan + lane table:
  `docs/research/favorites_2026-11-20/FAV8_NIGHT_PLAN.md`; configs `examples/typologies/fav8_2026-11-20/`.
- **New brief:** `examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml` (v11 home,
  envelope unchanged, F_X 900): own J identity. Three identities in the night; rank within each only.
- shape_check 12/12 fit; preflight no HARD (envelope-refusal WARNs only; `max_attempts` 450).

## 2026-11-20 - Consolidation: everything on hornfab-all, local main fast-forwarded, stale worktrees removed

- **Owner ask:** merge all local work into one local `main` and remove worktrees once integrated.
- **Committed (was live but uncommitted):** `22ae1f7` v11 CD-matrix objective (`objective/scalar_v11.py`,
  `metrics/cd.py`, v11 briefs/configs/queues/evidence; tests pass) and `f460398` the GUI lane's pending edits +
  hw GUI screenshot evidence. Merged `claude/hungry-sinoussi-4bc609` (score breakdown + favorites star);
  3 text conflicts (CONTINUITY/ISSUES tops, app.css tail) resolved keep-both.
- **Branch audit:** every side branch is contained in `hornfab-all` or superseded by newer content; the only
  unlanded change is agent-a527's Fix D (0.9 Keele factor) + its night-runner guard, already an OPEN owner
  decision. `main` fast-forwarded to `hornfab-all`. Nothing pushed (origin/main stays behind until the owner pushes).

## 2026-11-20 - GUI: full v11 score breakdown + owner favorites star (FAV-001 GUI items)

- **Ask:** the two GUI items from the FAV-001 entry (main-checkout working copy, ISSUES "FAV-001 favorite +
  objective/GUI findings"): the run page breakdown hid the v11 CD terms, and there was no way to star a horn.
- **Bug fixed:** "Score breakdown: start vs best" drew the fixed v1 list (`cov rip di dislope flat load`) with
  the brief's top-level weights. On FAV-001 (`runs/20261120T084006Z-screen-fc4e18`, J v11 4.996464) it showed
  3.247 of J; missing were `cov_profile` 0.005, `flat_cv` 0.276, `di_roughness` 0.108 and the CD block 1.360
  (`cd_lw` 0.346, `cd_di_std` 0.319, `cd_nacc` 0.153, `offaxis_smooth` 0.543). New `gui/data_breakdown.py`
  resolves the weighted key set + weights per objective version through the objective package's own resolvers
  (v11: `scalar_v11.resolve_v11_weights` when importable, else v10 resolver + `objective.cd.<term>.weight`;
  both paths give the identical sum on FAV-001), `run_detail` returns it as `score_breakdown`, and the chart
  lists all 11 v11 terms with a sum line (start sum 5.2952 = stored J; best sum 4.9965 = stored J). A gap to
  the stored total (penalty, v7 `oa_excess`) shows as an explicit `unattributed` row.
- **Feature:** `gui/favorites.py` + `GET/POST /api/favorites`. Run page: star toggle under the title (owner
  note required; optional title) appends an entry built from `best.json`/`run.json`/config brief (J read from
  best.json); un-star retires (`status: retired` + `retired_note`), never deletes; re-star re-activates.
  Writes are append-only text edits with a re-parse check (file untouched on any mismatch). Runs list: star
  marker + "Favorites" filter (by run id or best design hash). Elites: star marker + "Favorites" toggle.
- **Tests:** `tests/test_gui_score_breakdown.py` (5, incl. v11 sum == stored J on FAV-001's numbers, fallback
  path, node rows helper) + `tests/test_gui_favorites.py` (9, incl. append-only bytes, retire/re-activate,
  broken-registry refusal, HTTP, node helpers): 14 passed. Existing GUI suite: see the commit's test note.
- **Browser check:** preview (worktree GUI on :8767, `--runs` = main `runs/`) of FAV-001's run page shows the
  full 11-term breakdown and the FAV-001 star; Runs filter shows the 2 FAV-001 runs; a star -> retire
  round-trip on another run wrote then retired FAV-002 in a scratch copy (restored afterwards).
- **Integrated:** merged into `hornfab-all-2026-11-18` in the 2026-11-20 consolidation (entry above).

## 2026-11-20 - Rolled H terminal/rollback: width-500 size win, C look not accepted (senior handoff)

- **Owner ask:** width ~500 mm; start the H rollback at the yellow mark (x≈220/z≈160, lip x≈190/z≈125),
  keep the throat/V/depth, trim the horizontal face. Mid-pass: "a bunch of these do not look right and
  don't really get to what I was asking" → senior handoff.
- **Measured:** width-500 neutral `20261120T165651Z-screen-6a36c3` J 9.0033 (H 111.0/90.5/67.2/49.2,
  V 111.8/70.6/56.9/42.9, 500x344x242; 4036 dofs). Width 520 J 9.055; original 576 J 9.305. Sharp C
  `20261120T165805Z-screen-01eebe` J 9.6015, rip 0.1593; soft lip C `20261120T182453Z-screen-63c7f7`
  J 9.5780, rip 0.1576; soft bend mesh fail 0.932 mm. Both C variants match the yellow 220/190 x/z but
  the max-width point is z 174.8 vs the parent 159.0 (forward bulge); H 8k stays 48.8-49.0.
- **Front-load CD** `20261120T162808Z-screen-accb39` J 8.3264, V 8k 47.8, H 8k 50.8; score seed, not the
  HF answer. **HF reference:** ext-throat `925868ab64d9` verify `20261120T161054Z-verify-bf45ad` J 1.9693,
  H 70.8/V 61.2 at 8k, DI slope 0.14.
- **Handoff (new):** `docs/HANDOFF_ROLLED_TERMINAL_2026-11-20.md` — lead issue the C max-width z 174.8
  vs parent 159.0; H/V 40° blend; outer shell 0.95 mm/6.0 fail; Hermite/lip; width-only vs local trim;
  5.9/6.0; open questions. 59 geometry tests pass; no search queued.
- **New code:** `_rolled_rect_cd_v1.py`, `rolled_cd_family.py`, `_rolled_rect_terminal_v1.py`,
  `rolled_terminal_family.py`; additive dispatch `grid.py`, `generated.py`, `mesh/build.py`; dossier
  `docs/research/typologies/ROLLED_CD_WALL_ANGLE_RESEARCH_2026-11-20.md`.
- **Not done:** no full suite; no corrected-C render; the C is look-only until the senior re-anchors it.
  Other lane's cd_v11/favorites/GUI work left uncommitted and untouched.

## 2026-11-20 - FAV-001 favorite: Crowe-X on OS-SE CD research pass + favorites registry + night queued

- **Owner ask:** the v11 completion best `4140768780f0` (`runs/20261120T084006Z-screen-fc4e18`) has "some
  of the best directivity plots and esthetics" so far. Add it to a favorites list agents can find, explain
  why it does not score higher, do a senior research pass on improving it, queue variants. Then, mid-pass:
  a variant for a **500 mm cube max bounding box designed around a 900 Hz crossover**.
- **Registry (new):** `docs/favorites/FAVORITES.yaml` (+ `README.md`), FAV-001. Indexed in `docs/INDEX.md`.
- **Finding:** verify J 4.9939; it is best of the five v11 verify finalists on all four CD-matrix metrics. The
  `load` term is 2.73 of J (LFP20 674 Hz, Re z 0.21-0.52 at 682-1028 Hz). CPU replay (parity exact):
  F_X 900 puts it 0.17 J behind ext_throat; F_X 1000 or load weight 0 makes it **#1 by 0.67-1.08 J**.
  The competitors' `load` ~0 comes with throat resonances (peak Re z 3.23/1.95/1.71/1.39 rho c) that the
  one-sided term does not charge. Lever: OS `k` (frozen at 1.0 in every Crowe-X lane); Webster proxy at
  k 3 / L 286.7 (same mouth) gives Re z 0.5-0.9 at 700-1000 Hz. Report:
  `docs/research/favorites_2026-11-20/CROWE_X_FAVORITE_RESEARCH.md` (CPU scripts in `cpu/`).
- **New brief:** `examples/briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml`:
  v11 CD with envelope 500x500x500 and F_X 900; own J identity.
- **Configs:** `examples/typologies/fav_crowe_2026-11-20/` (3 k-attribution single solves, `fav__crowe_k_home`,
  `fav__crowe_c500_xo900`); shape_check 5/5 fit; preflight no HARD.
- **Queued (GPU, launched detached):** night `fav_crowe_2026-11-20` (`docs/queue/`, live copy `runs/nights/`),
  controller pid 52188 (parent WmiPrvSE) waiting on the `cd_v11_verify_and_expand_2026-11-20` runner pid 26752;
  cutoff 23:30. Jobs: k3/k2/k4 hold-mouth, k-home CMA 60, c500_xo900 CMA 60, verify top 3 of both.
- **Not done:** no objective change (v11 frozen); GUI favorite star and score-breakdown fix are proposals.
  Committed in this commit (not pushed).
- **Re-order 15:08 (owner: "run some more solves on this improved design" now):** `STOP` placed in
  `runs/nights/cd_v11_verify_and_expand_2026-11-20/` so that night ends cleanly after `xr__x_s2b_ext`; its three
  unstarted jobs `xr__x_s2c_morph/fold/twinray` were appended VERBATIM (same `--resume` dirs, cumulative budget
  60) to the tail of `fav_crowe_2026-11-20` (now 9 jobs), so they are deferred, not dropped. The chained
  queue.ps1 (pid 52188) starts the favorite night as soon as runner 26752 exits.
- **Results (16:15; research addenda):** k-attribution k2/k3/k4 J 4.800/5.177/5.603 vs FAV-001 4.996: each k step
  trades directivity for loading ~1:1. k-home CMA verify best `cd7e60025f70` 4.649 (FAV-001 verify 4.994); no row
  matched FAV-001's non-load. compact500_xo900 verify `746d33134776` 2.809 / `c6f0d22ff2b0` 2.824 (tie; own
  identity). `xr__x_s2c_*` resumed at 16:15 on the tail of the night.

## 2026-11-20 - GUI senior-review pass (steps 1-14)

- **Mandate:** `docs/research/system_woofer_2026-11-18/GUI_SENIOR_REVIEW_2026-11-20.md` §4 steps 1-14,
  in order, staging only this lane's hunks; stop at owner gates G and H. Companion handoff:
  `GUI_COMPLETION_HANDOFF_2026-11-19.md` (rules/UX/handback format).
- **Owner gate G (verbatim answer):** "Gate G: yes to both. Lock the woofer worktree and back up
  system_runs to E:\hornlab-system-evidence-backup-2026-11-20, following
  GUI_SENIOR_REVIEW_2026-11-20.md section 8.3 (copy from the physical path, robocopy /E not /MIR
  with /XJ, sha256 manifest of source and destination must match, after the CPU lane lock is
  released). Quote this answer in CONTINUITY."
  (The review has no §8.3; the written method in the answer was followed exactly.)
- **Owner gate H (verbatim answer):** "Approve the 11 README-covered". Applied: the 11
  README-covered evidence entries are `status: approved`, `approved_by: owner 2026-11-20`; the 2 WP3
  assembled real-motor cases and 3 mesh-refinement controls remain `proposed` (greyed + chip).
  Committed-registry test: 20 approved / 5 proposed.
- **Executed:** `git worktree lock --reason "holds system_runs evidence store; do not remove"
  C:/Users/hunte/Hrns/hornlab-woofer-system-wt`; `robocopy "…\hornlab-woofer-system-wt\system_runs"
  "E:\hornlab-system-evidence-backup-2026-11-20" /E /XJ /COPY:DAT`; **1,424/1,424 files**;
  source and destination sha256 manifests both
  `06d1e55a2155c72528deb3e33e8dee0b07de322ddc9c7c273c7ac30b79d6fd02` (`ok: true`, 0 missing/extra/diffs).
  No CPU-lane lock and no solve process was live at the copy.
- **Committed:** `9b90e25` HEAD consistency, `01a67b3` hermetic hw tests, `b6c9ccc` registry v2,
  `05af010` control links, `aa71c68` clearance removal, `ef415fa` CPU-lane lock for evidence solves,
  `be05284` compare grid tolerance + README acceptance, `61582c6` overview next-step + dialog routes,
  `5ab291e` locked DSP preview, `99358c2` P5 study identity, `71da083` shortlist table,
  `337feaf` shortlist follow-ups, `6f488b7` Overview + menu, `8fe7fa4` project-registry v2,
  `fe868d2` wizard/Quick launch, `405d741` P6 dialogs + overview polish, `909181c` Compare +
  Crossover pages, `cfa7846` lifecycle harness + gate-H approvals, plus the final `docs(gui)`
  handback commit. `GUI_HANDBACK_2026-11-20.md` is the packet.
- **Tests:** §9 command 1 **1,117 tests / 1 failure (pre-existing B8 host-cleanup, introduced in
  `b019623`; review §1 recorded it) / 0 errors / 7 skipped**; full profile **5,586 / 7 failures
  (1 pre-existing B8 + 6 other-lane: v11 registration, score_identities, scout40 queue, preflight) /
  29 skipped**; real-BL staging `tests/system/test_bl_stage.py` **11 passed**; final hw browser
  sweep **104/104 combinations, 0 failures**; keyboard-only story **14/14 steps, 0 console errors**;
  hw lifecycle harness `node …` exit 0 + pytest 1 passed.
- **Store state:** `system_runs` remains the junctioned worktree store; the worktree is locked and
  the E: copy is verified. No GPU lock or `gpu-clean` was touched by this pass.
- **Done:** steps 1-14 of the senior review. Gates: B/C yes (2026-11-19), D/E open, G/H answered
  above. Handback: `docs/research/system_woofer_2026-11-18/GUI_HANDBACK_2026-11-20.md`.

## 2026-11-20 - System evidence queue ran (CPU only, no GPU)

- **Owner ask:** queue a variety of runs whose data will guide the open system questions. The owner
  then authorised the launch; the queue ran beside the live `fable_expand_2026-11-19` GPU night in
  the separate CPU lane. **No GPU job was started.**
- **Queue:** `docs/queue/system_evidence_2026-11-19.yaml` (11 CPU-lane `command` jobs) + runbook
  `...md` + admission `...admission.json` + six request overlays under `requests/`.
- **Results:** 9 solves complete (LF 20-200 Hz on #4/#5/#6/R0 and assembled #2; two wide 2x2
  cells; 10 m vs 2 m; 49-freq sampling), screen replay `27616eedee09009f` byte-identical, census
  export. Then the **real-motor assembled case** (validate valid true; 25/25 wide + 12/12 LF) and
  **two refined-mesh** 49-freq cases. Current census: **54 cases / 19 solved / 29 staged /
  3 refused / 3 invalid**.
- **First #4 LF attempt failed** on the wrong project port (`vented/voltage`; #4 uses
  `bl_motor12pr/voltage`). The case is retained; the corrected request
  `requests/lf_motor12pr_20_200.json` completed 12/12 in a manual retry.
- **Tool:** `tools/system/evidence_case.py` copies an existing `case.blab.json` + `bl_output/` into
  a fresh case, copies/validates the request, writes a self-checksummed source/project/request/BL
  manifest, then calls the existing authorized `reference.solve`. `--dry-run` writes nothing;
  `--solve` refuses without `HORNLAB_EVIDENCE_AUTHORIZED_BY` or `--authorized-by`.
- **Tests:** `tests/system/test_evidence_case.py` **6 passed**; `tests/test_night_runner_live.py`
  11 passed after the CPU-lane `gpu-clean --force` fix; per-job dry-runs 9/9; night dry-run 11 jobs.
- **Readout:** `docs/evidence/system_evidence_2026-11-19/README.md`: wide motor difference up to
  ~8.6 dB / 40 deg; box/null structure up to 23.6 dB; 10 m vs 2 m after 1/r and propagation
  correction max 1.38 dB / 17.3 deg; 25 vs 49 shared points agree to 0.03 dB but the denser grid
  exposes -20 dB nulls; assembled LF matches vented-only default within 0.06 dB. Real-motor
  assembled vs demo = +4.8..+7.8 dB (mean 6.75, phase 32 deg) on the wide grid. **Mesh convergence
  is NOT established**: default/refine1/refine2 nulls move; max delta up to ~16 dB, RMS 2.6-3.3 dB.
- **Not done / still gated:** real 12PR300 shape/panel fit (needs maker CAD), calibration/system
  ranking (decision 3), `float64` control, full-sphere far field.

## 2026-11-20 - Senior engineering decision + pilot Pareto/fidelity repair (CPU only, no GPU)

- **Mandate:** adversarial reconciliation of the horn + woofer stack, a fidelity/source-
  normalization decision, and the next bounded reference study.
- **Report:** `docs/HORNFAB_SENIOR_DECISION_2026-11-19.md`. Keeps the three-layer architecture;
  separates acoustic model / driver state / calibration state / numerical confidence; adopts explicit
  calibration records as the only route to a coherent sum (arbitrary gain matching rejected);
  prioritises LF 20-200 Hz, the 2x2 motor-box + real-motor assembly, real driver shape, and
  convergence/angular validation; report-only system metrics before any scalar; fixed-horn screen as
  the near-term search.
- **Fixed (real defects):** `pilot --geometry` called the non-existent `LF_TS_SCREENING` fidelity;
  pilot Pareto axes were nested `{value,direction}` dicts and `rules_skips` was a list inside boolean
  feasibility; F3 direction was `+` (maximise). The pilot now uses scalar axes + `axis_directions`
  with F3 `-`, boolean feasibility, top-level `rules_skips`. `score.validate_axes()` now rejects
  nested axes/list feasibility in `render_report` instead of silently making every row Pareto.
- **Tests:** targeted `tests/system/test_score.py` + `test_horn_import.py` = **25 passed**; full
  `tests/system` passes with the 7 real-BL env gates; `pilot --geometry` CLI verified.
- **State:** no GPU, no solve; `runs/`/`system_runs/` read-only. Other lane's uncommitted GUI/ripple
  work left untouched. System census unchanged: 37 cases = 5 solved / 27 staged / 3 refused / 2 invalid.

## 2026-11-20 - P12 verify night: the tie cluster ranked on the verify grid (6/6 jobs, ~20 min GPU)

- **Compact400 trio (one identity, mesh normalized):** screen order **holds on the verify grid** -
  morph_cont 1.2271 -> **1.1864**, fold_cont 1.3147 -> **1.2763**, twinray_cont 1.4351 -> **1.3734**.
  Pairwise gaps (0.090/0.097) are still inside the compact400 floor 0.1293: a three-way tie, ordered
  but not separated. Full polars are the next (and only) separator.
- **Home v10 fold pair:** the widened-box winner `56203404ce56` **beats the published best** on the
  same verify grid, 1.4867 vs **1.6704** (0.184 J) - the fold-family s2w improvement is real, not a
  screen-grid artefact. (Verify J > screen J is expected on a finer grid; only same-grid comparisons
  count.)
- **Ext-throat closed** [measured]: the p11 fallback (narrower az_a_cos_pow widen, refusal-tolerant
  watchdog) ran 30 valid / 47 attempts and never left its seed (1.5710). Two independent attempts now
  fail to improve `a23763f1c6fc`; no further ext-throat v10 work without a new freedom.
- Mechanics: 5 one-solve `run --mode verify` replays of stored screen bests + 1 screen fallback,
  chained behind `compact400_next10_2026-11-19` with `-WaitPid` (that night was never touched).
  Evidence: `docs/evidence/P12_VERIFY_2026-11-19.md`; queue `docs/queue/p12_verify_2026-11-19.yaml`.

## 2026-11-20 - Ripple program: 730-design corpus sweep, an INERT source knob, HF width bound by the envelope

- **Owner ask:** proceed with every next step, GPU time allowed, and establish what is needed to improve
  these horns. Two background lanes (corpus sweep tool; audit compare + bridge refusal) while the
  orchestrator ran the GPU work.
- **Corpus sweep (CPU, 730 designs):** `tools/analysis/spectral_corpus_sweep.py` (report-only) walks
  `runs/`, computes V±25/V±35/V+45/H+25/H+35 trend + V+25/V+35 band-mean residuals per best design via
  `metrics/spectral.py`, groups by `brief.name`, and reports per-identity Spearman. **730 usable, 0
  refused, 25 skipped (no resolvable design).** Pooled rho(rip, V+35) = **0.615**; **25 of 28 identities
  below 0.8** — `organic_rollback_1in` -0.871 (n=29), `axi_90x90_1in` 0.050 (n=82), `freeform_sculpt`
  0.014 (n=36), `compact400` 0.089 (n=27), `room_landscape_v7` 0.713 (n=112), `v7_smooth` 0.929 (n=58).
- **REVISED CONCLUSION:** the earlier "largely redundant with `rip`" (rho 0.885) was a property of the
  **v7_smooth family only**. The fixed-angle residual is a genuine second axis on most lines of work, so
  item 6 is no longer dismissed on redundancy grounds — the remaining gate is acoustic, not statistical.
- **Source sensitivity (6 jobs, 2 real solves):** three briefs differing only in `source.cap`
  (auto / 150 / 60) gave **identical mesh hashes (`7abdb66729…`) and identical responses** — `source.cap`
  is an **inert key**: `mesh/grid_build.py` hardcodes `source_auto_angle_deg` and never passes
  `source_radius_mm`, so every grid-family solve we have ever stored uses the auto cap. Item 5 is
  blocked by a bug, not by physics; fix in flight (thread the brief cap in, with an `auto`-path
  byte-identical test).
- **HF width (3 jobs, 2 real solves):** base = Crowe X OSSE `9b5428e6dec8`, all knobs pinned.
  `wall_lo` (angles x0.85) → 8 kHz width **74.0 → 62.2 H / 53.9 → 47.2 V deg**, +25 deg level
  -5.08 → -6.77 dB, J 5.3454 → 6.7169. `lip_lo` (18.28 → 9.14 mm) → **+0.2 deg / +0.06 dB** (inert),
  J 5.5866. `shape_check` refused the two *wider* variants (wall x1.15 → 672 mm, lip x1.5 → 614 mm
  mouth, envelope 600 mm), so the space is one-sided: **HF width tracks the wall angle and is already at
  the envelope limit** — widening needs a bigger envelope or a different mouth law, not more wall angle.
- **Tooling landed (lanes):** `--compare A B` in `spectral_ripple_audit.py` (per-design deltas + rank
  correlation + the grid-dependence warning; reproduces rho 0.9636 / max 0.467 dB screen-vs-verify);
  `verify` now REFUSES a bridge-cell run before any GPU work, naming `tools/geometry/<cell>_cli.py`
  and the exact replacement command.
- **GPU accounting:** `source_sensitivity_2026-11-20` (6 jobs; baselines 737-848 MiB, peaks 887-1697 MiB)
  and `hf_width_2026-11-20` (3 jobs; 18.7 s / 22.1 s real solves). One night's first job was refused
  `GPU busy` by a foreign job, waited, then ran — no concurrent solve. `gpu-clean` before/after each job.
- **Evidence:** `docs/evidence/ripple_program_2026-11-20/README.md` (all three experiments, the
  pre-declared readings and the "what we now know we need" section).

- **source.cap FIXED (2026-11-20 ~17:00):** two halves were needed. `mesh/grid_build.py` now passes the brief's cap as `source_radius_mm` (and records `meta["source_cap"]`), and `MeshSpec` gained `source_cap_mm` which enters `MeshSpec.hash()` only when non-zero - without the second half the geometry would be right while the mesh/solve caches still keyed on the auto mesh. Verified: stored 8 kHz run keeps `8e789cd0deef`, 12 kHz auto keeps `7abdb667298f`, cap 150/60 give `bcf9a8cec98b` / `c42751b96235`. 8 tests in `tests/test_mesh_source_cap.py`, 118 in the mesh/config gate. Re-run night `docs/queue/source_sensitivity2_2026-11-20.yaml` launched (new output dirs; the pre-fix runs under `runs/source_sensitivity/` stay as evidence of the bug).
- **KNOWN GAP (not fixed):** `design/recipe_meta.py` still resolves the AUTO radius into `design.json["generator"]["recipe_meta"]["source_cap"]` for explicit-cap runs, so the design provenance disagrees with the mesh that was built. The grid meta (`meta["source_cap"]`) is correct; the record-side one-liner belongs to that file's owner.

- **source.cap RESULT (re-run with the knob live, 6 jobs):** for the grid route the wavefront assumption is irrelevant where the handoff compared and decisive where it warned - **8 kHz: width moves <=0.2 deg and the +25 deg level <=0.05 dB** across cap auto -> 60 mm (0.31 -> 2.73 mm dome); 10 kHz: up to 3.1/3.5 deg; **12 kHz: H width 65.7 -> 55.6 deg (-10.1) and +25 deg level -5.11 -> -3.89 dB (+1.2)**. So "8-16 kHz is source-conditional" is right in substance, wrong in scope: the conditionality starts near 10 kHz. Meshes now differ (`884b6eef` / `f3cb5316` / `d59e8c75`).
- **NEW GAP (native route):** OSSE/FREEFORM configs do not go through `grid_build`, so `source.cap` still does nothing there - OSSE morph built three **byte-identical** meshes (`c59ec195`) while the recorded `mesh_hash` differed, because `MeshSpec` now carries the cap on every route. Safe for the response, misleading for provenance; the native spec path needs the same wiring or an explicit refusal.

- **CORPUS HYGIENE + CORRECTION (later 2026-11-20):** the sweep now dedupes by `design_hash` (748 runs hold 545 unique designs) and groups by `(brief, objective version)`, not brief name alone. Corrected numbers: pooled rho 0.662; **21 of 24 identities below 0.8**; only `v7_smooth` 0.929 (n=52), `native_ath_core_2in` 0.893 (n=7) and `b1w_hifi_90x60_850_wide` 0.881 (n=8) reach 0.8. The `organic_rollback_1in` -0.871 is **RETRACTED**: it mixed five Oct-25 runs with no declared objective version (salmon/iwata/lecleach rows, J 45-86) with five Nov-13 v3 runs (salmon, J ~40); split by version it reads -0.500 and +0.300 on n=5 each. The second-axis conclusion stands; the anti-correlated identity was era, not acoustics.

- **ITEM 4 SECOND FACTOR - mouth law is envelope-bound too (2026-11-20):** three one-knob mouth-law variants of the Crowe X OSSE base through `shape_check` before any solve: `g_sf_amt` 0 -> 610 mm (OVER 600) and `g_s` 0.55 -> 663 mm (OVER), both refused and deleted; `g_sf_amt` 0.5 -> 596 mm fits and is staged as `docs/queue/hf_width2_2026-11-20.yaml` (1 job, NOT launched - another lane's search resume owns the GPU lane). Conclusion so far: **neither wall angle nor mouth law can widen HF inside the 600 mm home envelope**; a wider horn needs a bigger envelope or a different construction.

## 2026-11-20 - Ripple audit grid test RUN: PASS (rho 0.964) + DENSE verdict: the B3 feature is broad, not a resonance

- **Launched (owner: "Launch"):** `ripple_audit_2026-11-20`, detached pid 2900 at 08:34 local,
  finished 08:48 **exit 0** in two passes (11 jobs, then 2 retry jobs); GPU baseline 474-491 MiB,
  per-job peaks 473-1,118 MiB, `gpu-clean` before/after every job, no concurrent solve.
- **Result - predeclared criterion:** ten SCOUT40 bests re-solved at verify fidelity (25 log freqs +
  balloon 1024 vs 18/512, same mesh) give **Spearman(V+35 screen, verify) = 0.964** (p = 7.3e-6),
  **max |delta| = 0.467 dB**, mean 0.143 dB. The *ranking* survives a frequency-grid change.
- **Dense readout (item 3, answered):** the first dense pair in `fable_expand` is VOID - it ran 00:39
  with the old brief (18 freqs, `cached: true`) and its configs were corrected at 00:46. The second
  pair (`x_r3_b3_dense2_epw6/epw9`, 06:59/07:01, 91 freqs, `cached: false`, 69.8 s / 251.9 s) is
  valid. At 25 Hz through 1.8-3.4 kHz, B3 +25 deg is a **broad smooth double-dip** (-6.7 dB shelf to
  2.3 kHz, -2.8 dB at 2.75 kHz, -4.9 dB at 3.2 kHz), **identical on epw 6.0 and 9.0 to <=0.1 dB** -
  mesh-converged, and **not a narrow resonance**, which answers the handoff's open hypothesis in the
  negative for this design.
- **Metric consequence (revised, honest):** the three grids read B3 V+35 = 1.441 (screen, 10 samples),
  1.908 (verify, 11) and **1.313 (dense, 80)**. Agreement is not accuracy - quote the metric
  comparatively only, prefer the screen grid, and never set an absolute threshold.
- **FOUND (needs owner/owner-lane action):** `runs/20261119T085256Z-screen-c2203f` (R-OSSE
  rectangular) **cannot be verified or resumed from the plain CLI**: `generator.rows.type: rosse_rect`
  is an opt-in bridge cell, so `hornlab-search verify` refuses with `GeometryInvalidError: unknown rows
  type 'rosse_rect'`. It re-solved only through `tools/geometry/rosse_rect_cli.py verify ...`. Any
  bridge-cell best (`n`, `rolled_rect`, `crowe_panel`, `rosse_rect`) needs its own entry point.
- **Also confirmed:** verify `J` != screen `J` (B3 2.80022 -> 3.49921; R-OSSE rect 4.55960 -> 5.08620);
  the frequency grid enters J, so never pool the tiers.
- **Evidence:** `docs/evidence/spectral_ripple_audit_2026-11-19/VERIFY_GRID_TEST.md` +
  `verify_v2/` (ten verify rows) + `dense_91/` (the 91-frequency audit).
- **Queue file edited in place while live** (same night): `ra_rosse_rect_bridge` + `ra_audit_verify_v2`
  added after the first pass; the failed `ra_rosse_rect` / `ra_audit_verify` ids stay in
  `queue_state.json` as history (a finished id never re-runs). A throwaway dense re-run night was
  created, proved to be cache hits only (0.0 s solve, 91 freqs already present from `dense2`), and
  deleted rather than committed.

## 2026-11-20 - Ripple audit test night staged (11 jobs) - launched and read out the same morning

- **Owner ask:** add queue items that test the fixed-angle spectral audit. Staged, nothing launched.
- **New night `docs/queue/ripple_audit_2026-11-20.yaml`** (+ launch-ready copy in `runs/nights/`,
  `--dry-run` clean, 11 jobs, `lane: gpu`): ten SCOUT40 bests that span the measured range (B3
  current/previous, C200, OSSE morph, ext-throat, R-OSSE rect, Crowe X OSSE, Tritonia v8, Lame,
  Le Cleac'h) are re-solved at **verify fidelity** via `hornlab-search verify --designs <hash>
  --verify-dir runs/ripple_audit/<id>` - 25 log frequencies + balloon 1024 instead of 18/512, same
  mesh, reusing each source run's own config/brief (no new config, no brief edited) - then one CPU
  job runs `tools/analysis/spectral_ripple_audit.py` over the ten verify responses.
- **Predeclared test (written before any number):** is the residual a property of the horn or of the
  18-point screen grid? Pass = Spearman(screen V+35, verify V+35) >= 0.8, no design moving > 0.5 dB,
  B3 notch still present at 25 frequencies. Fail is informative: the 10-sample number is grid-limited
  and must not be quoted as a design property (item 6 stays closed).
- **Why this and not item 3 twice:** item 3's dense 1.8-3.6 kHz B3 re-solve at epw 6/9 is already
  staged by the concurrent lane in `docs/queue/fable_expand_2026-11-19.yaml` (x_r3_b3_dense_*); not
  duplicated. This night tests the metric, that one tests the anomaly.
- **Tooling:** the audit now falls back to `run.json` for `objective_version`, because a
  `verify --verify-dir` output has no `summary.json` (verified end-to-end on an existing verify run
  dir: 29 frequencies, `v7` recovered, 14 tests still pass).
- **State:** GPU untouched by me - `fable_expand_2026-11-19` (gpu) and `system_evidence_2026-11-19`
  (cpu) were live at write time; its x_s2b_* tail recorded `watchdog` status on 5 consecutive jobs
  (not investigated - that lane's). Launch only after a `gpu-clean` and with `-WaitPid` behind the
  live runner.

## 2026-11-20 - Fixed-angle spectral ripple audit (handoff item 1 done; report-only, no GPU)

- **Owner ask:** move `HornFab_Data_Backed_Ripple_and_HF_Handoff_2026-11-19.md` into the repo and
  begin its implementation; up to two background lanes while the orchestrator integrates; flag the
  human-review items, update CONTINUITY, commit and push.
- **Moved (verbatim, SHA-256 `D2DE2A79…8D066`):** `docs/research/ripple_hf_2026-11-19/HANDOFF_2026-11-19.md`
  plus a bundle index, `MANDATE_STATUS.md` (items 1–6 + flags **H1–H6**) and `MEASUREMENT_TAXONOMY.md`
  (seven phenomena P1–P7, band-mean vs trend reference, Sridhar/Tylka/Choueiri metrics with the three
  we must not adopt, 5.61 kHz throat cut-on, per-family applicability, sources S1–S9).
- **Built (mandate item 1, report-only, zero solver calls):** `hornlab_search/metrics/spectral.py`
  (`fixed_angle_residual_db/_curve` with `reference="trend"|"band_mean"`, `symmetric_pair_report`,
  `cut_identity_check`, `sensitivity_scan`) and `tools/analysis/spectral_ripple_audit.py` (design- or
  run-dir scan, `audit.json` + `disagreement.md`, non-empty `--out` refusal, rank column only within
  one objective version); tests `tests/test_metrics_spectral.py` +
  `tests/test_tools_analysis_spectral_ripple_audit.py` — **14 passed**.
- **Measured (24 SCOUT40 bests, all `objective_version` 7):** every handoff number reproduces to
  ≤0.002 dB (incl. Crowe X OSSE 0.266/0.351 and B3 1.151/1.441) and its B3 claim holds in the arrays
  (−6.88 dB at 1,763 Hz, −6.74 at 2,269; `z_throat` 0.966−0.122j / 1.016−0.135j / 0.983−0.136j, no
  large feature); `metrics.json on_axis_db` is band-mean-normalised (shape matches npz to 1.8e-15);
  all 864 ± pairs agree to ≤1.1e-6 dB, i.e. ± is **not** an independent check under `symmetry: hv`.
- **Two results that qualify the handoff:** the trend and band-mean references are effectively
  orthogonal (Spearman **ρ = −0.018**; band-mean punishes the Le Cleac'h/Iwata/Lame taper at 2.1–2.4
  dB while they are best on trend at 0.04–0.12 dB), and the fixed-angle residual is largely redundant
  with `rip` (**ρ = 0.885**, 44/276 discordant pairs). Detrend order is stable (ρ 0.955/0.959) but
  absolute values move up to 0.559 dB. Conclusion: no term promotion; `J` under-charges a defect it
  partly sees rather than being blind to a class.
- **Evidence:** `docs/evidence/spectral_ripple_audit_2026-11-19/` (README + `audit/audit.json` +
  `audit/disagreement.md`; regenerable per-design JSONs not committed).
- **State:** GPU untouched — no solve, no lock change; the lock was observed stale-held (holder pid
  gone) after `p12_verify_2026-11-19` exit 1 and needs `gpu-clean` before any solve. Mandate items 3–5
  (dense-frequency validation, controlled HF-width experiment, source validity) need owner approval;
  item 6 (scoring) stays deferred. A second GUI lane's unstaged `app.js`/`app.css`/`hw*` work was left
  untouched; the previously staged Overview phases 2–4 were committed separately (`3fd2027`, 79 tests
  re-verified).
- **Tests (2026-11-20, after the concurrent lane pushed):** targeted gate for these files **140
  passed** (`tests/test_metrics_spectral.py`, `test_tools_analysis_spectral_ripple_audit.py`,
  `test_metrics_smoothness{,_v2}.py`, `test_metrics_pattern_quality.py`,
  `test_metrics_integration.py`, `test_objective_v7/v10.py`,
  `test_replay_versions_single_source.py`). Full offline suite, run against that lane's *uncommitted*
  WIP, gave **5 failed / 5464 passed / 29 skipped** in 8:39 — all five outside this change and
  reviewed in `docs/ISSUES.md`; none touches `metrics/spectral.py`.
- **Provenance note:** the commit meant for this slice was carried by the concurrent queue commit
  `f9f5ac5` (already pushed); `3032a0c` records it. Nothing of this change is left uncommitted.

## 2026-11-20 - GUI Overview phases 2-4 built (findings, registry, parameters, snapshots; CPU only)

- **Owner ask:** follow `docs/overview/OVERVIEW_IMPLEMENTATION_PLAN_2026-11-19.md` for phases 2-4;
  owner decisions = the document's recommendations; up to two parallel background sub-agents while
  the orchestrator integrates. **No GPU; `runs/` read-only** apart from the plan's two GUI-written
  files and an explicit snapshot job.
- **Built (phases 2-4, plan §4):** findings engine (`gui/data_overview_findings.py`: budget
  tail-gain with `resolved_by`, refusals, tie-verify, stale, probe-only, unregistered registry,
  existing `walls.json` only; stable 16-hex ids, `100*impact*confidence*currency`, one identity per
  finding); persisted index (`gui/data_overview_index.py`, `runs/overview/index.json`); per-line
  states (`gui/data_overview_states.py`); software health (`gui/data_overview_health.py`);
  project readiness registry (`docs/registry/project_readiness.yaml` + `gui/data_overview_registry.py`,
  HW file merged with `area: hw`, 45 rows, 0 errors); finding state (owner O4,
  `gui/data_overview_state.py` + `POST /api/overview/findings/<id>`); parameters
  (`gui/data_overview_params.py`, bounds + 2 % bound hits); snapshot spec
  (`tools/analysis/overview_snapshot_spec.py`) and the CPU-only `overview-snapshot` job
  (`gui/data_overview_snapshot.py`, entry script, **not** a GPU kind).
- **GUI:** `#/overview` tabs Briefing / Leaders / Typologies / Next solves / Decisions / Parameters;
  state pills on leader and typology rows; frozen-snapshot card + "Generate snapshot" button; O1
  applied as the default landing route (`#/` and an empty hash go to `#/overview`; Home stays a
  route). New files `gui/static/overview_findings.js`, `overview_registry.js`, `overview_params.js`;
  the other lanes' uncommitted `app.js`/`app.css`/`hw.js`/`index.html` edits were preserved (only
  the 2-line O1 hook added to `app.js`).
- **Measured (14-day window, 305 runs):** cold 9.98 s (index build) -> 0.06 s records / 0.82 s full
  payload warm; 43 ranked lines; 19 engine findings (13 open / 6 resolved) in 1.57 s; health adds 11
  software findings; params covers 10 identities / 43 lines (28 at-bound rows); snapshot smoke
  (`--days 1`): 27 lines -> 102 sections, **102 ok / 0 errored**, exit 0.
- **Tests:** overview modules **79 passed** (phase 1 + findings + index + states + registry + state +
  health + params + snapshot) and API routes **4 passed**; `-o addopts=""` needed to see the summary
  (repo `addopts` is `-ra -q`).
- **Browser check:** `tools/gui/browser_check.py` against the separate `gui-verify-8766` server
  (owner's 8765 untouched), Python 3.13 because the `.venv` has no Playwright: **24/24 combinations
  pass** (6 tabs x 1280/375 x dark/light), zero console errors, no horizontal scroll, URL state
  restored. Evidence + verbatim bytes: `docs/evidence/overview_phase234_2026-11-20/`.
- **Deferred:** wiring the snapshot into the night runner (O3) needs an edit to `tools/night_queue`
  and an owner-approved unattended path; the job is available from the Overview button instead. A
  full 14-day snapshot was not run (smoke only).
- **Visual QA (same day, follow-up commits):** an independent image review of the six tabs found 16
  issues — 2 blockers (the Parameters table lost BEST J / bound-hit columns at 375 px; an expanded
  findings group repeated its own header) and 14 cosmetic bugs (`WP WP4`, a character-broken SOURCE
  column, a risk counter implying missing rows, a duplicated timestamp, severity order). All fixed:
  narrow params rows carry a labelled `J 2.498 · 0 hits` group (nowrap segments, header printed once,
  no tab timestamp); findings groups follow the payload's severity-tied order, the severity tiles
  count the *matching* subset with a sentence saying so ("…match the filters below; the payload holds
  N") and the counter reads `X of Y groups · X of Y findings shown`; the registry hides an all-empty
  Decided column, moves `source:` under the recommendation and states
  `33 risks + 12 decisions = 45 rows`. Tie-verify evidence now prints 4-decimal J values instead of
  raw floats. A severity tie-break (`F.sort_key`: status, −score, severity) keeps HIGH above MEDIUM
  at equal score. Final Playwright pass 24/24 clean at 1280/375 dark/light, URL state reload-safe
  (also verified with `tab=next&status=all&sort=newest&kind=budget`). Screenshots refreshed.
- **State:** GPU lane untouched (no solve, no lock change). `runs/overview/{index.json,finding_state.json}`
  are the only GUI-written state; both are git-ignored with `runs/`.

## 2026-11-19 - GUI Overview phase 1 + implementation plan (CPU only, no GPU)

- **Owner ask:** review the three-week analysis report as an entry point, propose a better structure,
  then build phase 1 and write a sub-agent-parallel plan for the rest. **No GPU; `runs/` read-only.**
- **Review (measured):** the report is 199 convergence sections only (no walls/sensitivity/term
  balance), its 78 "Do first" items are one budget rule, it counts run folders (10 `_backup` copies,
  15 study dirs), never resolves continued lines (>= 11), cannot group by typology (`family` is only
  OSSE/FREEFORM) and treats v10xo as v10. Since the snapshot: 110 runs, 6,669 evals.
- **Built:** `#/overview` (Briefing / Leaders / Typologies) from `gui/data_overview.py` +
  `gui/static/overview.js` + `GET /api/overview?days=&legacy=`; `examples/score_identities.yaml`
  (9 identities, floors 0.4677 home v10 / 0.1293 compact400); typology = knowledge-hub family card
  + construction; lines of work = identity x construction; probes (< 10 valid) never lead; ties =
  within floor. 14-day window: 302 runs, 13.2 s cold / 0.4-0.7 s warm.
- **Fixed:** GPU lane card read a stale `queue_*gpu*.log` (showed a Nov-15 job); the GPU lane now
  reads every non-`cpu` queue log, newest first.
- **Tests:** `tests/test_gui_overview.py` + lane tests **24 passed**. Wider `-k gui` run: one
  pre-existing failure (`test_b8_lanes_bounded_gui::test_study_modules_have_no_host_cleanup...`,
  `study_jobs.py` untouched).
- **Plan:** `docs/overview/OVERVIEW_IMPLEMENTATION_PLAN_2026-11-19.md` (P2-P4, 11 WPs in 4 waves,
  owner decisions O1-O6). Other lanes' uncommitted GUI edits were left unstaged.

## 2026-11-19 - Senior handbook + system solve-data export (CPU only, no GPU)

- **Owner ask:** one consolidated cloud-ready handoff for the horn + woofer system and GUI, package the
  solve data as CSV/JSON with a reusable script, identify remaining work/issues, and commit/push.
- **Handbook:** `docs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md` (1,903 lines): pure-horn pipeline,
  system backend/schemas/config surface, GUI routes/controls/UX, both data exports, remaining work
  (R1-R17, WP1-WP8, P0-P9), known issues, target architecture. Four read-only recon lanes plus one
  export writer lane; code claims checked against the tree, unverified doc claims marked.
- **System data export (new):** `tools/data/system_cases.py` +
  `tests/test_tools_data_system_cases.py` (**16 passed**) +
  `docs/system_data/{system_cases.csv (37x53),system_cases.json,system_screens.json,README.md}`.
  Deterministic, stdlib, read-only over `system_runs/`. Census: **5 solved / 27 staged / 3 refused /
  2 invalid**; 9 readiness-declared cases (5 solved, 2 staged, 1 refused, the 62864 clearance case).
  Readiness is joined, never inferred; known diagnostics: 2 missing manifests, 1 known broken pilot
  payload hash.
- **Horn solve export:** already committed (`9714b39`): `docs/top_designs/` +
  `tools/data/top_designs.py`; 807 ndjson / 51,192 rows / 37,588 unique / 52 groups / 437 designs;
  tests **11 passed**.
- **Docs:** INDEX/CODE_MAP/ACTIVE_STATE updated. Unrelated uncommitted GUI edits (another lane) and
  the budget-driver audit were NOT staged. No GPU used; `runs/` and `system_runs/` were read-only.
- **State:** GPU lane free at the last check; nothing queued by this pass.

## 2026-11-19 - TuRBO/BO study runs now viewable like CMA runs; CMA vs TuRBO render set (CPU only)

- **Owner ask:** make TuRBO results as viewable as CMA (GUI, graphics, runs), apples to apples.
- **Cause:** BO studies write solves to `runs/study-<id>/{screen,verify}` (same files as a CMA run, one
  folder deeper), so the GUI run list (RUN_ID pattern), run page, Compare, leaders and render tools never saw them.
- **Fix:** `tools/night_queue/mirror_bo_studies.py` hard-links each study into `runs/<start>-<policy>-<id6>/`
  (no copied data; own run.json with `algorithm`/`bo_seed`/`source_study`, best.json, bo_mirror.json;
  idempotent, `--prune`). `run_bo_arm.py` runs it after every arm. 22 studies mirrored (8 TuRBO, 11 BO
  scalar, 1 Pareto, 2 early BO). GUI: summary `algorithm`/`source_study`, Runs optimizer filter + badge,
  run header names optimizer/study, BO note instead of the empty CMA covariance panel, Compare labels.
  BoTorch training reads dataset shards, not run folders, so mirrors cannot double-count rows.
- **Measured (screen J, same config/brief/v7):** TuRBO beats the best CMA run in all 6 pairs: ext-throat
  hvlaw 2.498 vs 3.103, fold warm 3.330 vs 3.621, TwinRay v8 4.091 vs 4.914, Tritonia v9 4.546 vs 5.015,
  Tritonia v8 4.628 vs 5.692, p80x60 ATH core 4.691 vs 4.978 (TuRBO is cohort-warm-started from CMA data).
  BO scalar wins 3/6. Renders + pairs.json: `docs/renders/2026-11-19-turbo-vs-cma/`.
- **Tests:** `tests/test_night_mirror_bo_studies.py` 4 passed; GUI suites pass except the pre-existing
  `test_b8_lanes_bounded_gui::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  (`gui/study_jobs.py` Popen, from 6791bfa; untouched). Browser-checked on a private 8811 instance.
- **Owner action:** restart the 8765 GUI to load the new summary fields. The other lane's uncommitted hw
  GUI edits (app.js/app.css/INDEX) were excluded from staging.

## 2026-11-19 - Top-designs export for cloud agents (CPU only, no GPU)

- **Owner ask:** export the top-10 highest-scored designs for every typology and score set from GPU
  solves, with all available acoustic data, typology, score, dimensions and geometry parameters; make
  it a reusable script, register it in CODE_MAP/INDEX, commit and push. **No GPU was used; `runs/`
  was read-only.**
- **Tool:** `tools/data/top_designs.py` scans every real `runs/**/search.ndjson` (archive/`_inputs`/
  `_backup*` skipped), admits provable CUDA rows, dedupes physical solves, ranks ascending J within
  typology + objective version, and writes the bundle. `--group-by score-config` splits one version
  by resolved objective+weights+target when strict same-brief comparison is needed. Tests:
  `tests/test_tools_data_top_designs.py` (**11 passed**).
- **Measured scope:** 807 ndjson files, 51,192 rows scanned (43,379 GPU), 37,588 unique scored
  physical solves, **52 typology×score-set groups, 437 selected designs**, 437/437 with stored
  response arrays. Snapshot 2026-11-19T23:40:55Z, repo HEAD `ddfba68`; the live compact400 night was
  still appending runs, so regenerate after it finishes to capture new solves.
- **Data:** `docs/top_designs/` — README (schema/grouping/caveats/queries), `top_designs.csv`
  (632 KB, 161 flat columns), `top_designs.json` (6.4 MB; shared score configs/runs + nested designs
  with metric arrays), `top_designs_acoustics.npz` (13.8 MB; H/V cuts, full balloon SPL+directions,
  complex throat impedance). Raw complex pressure is not copied (local `response.npz` is the source).
- **Registered:** CODE_MAP and INDEX rows in the same commit. The other lane's uncommitted GUI edits
  and its budget-driver INDEX row were left untouched and excluded from staging.

## 2026-11-19 - Commit-scope note (local orchestrator)

- The expansion-night commit f9f5ac5 also carried another lane's ALREADY-STAGED spectral-mandate files
  (docs/research/ripple_hf_2026-11-19/, docs/evidence/spectral_ripple_audit_2026-11-19/, 
  hornlab_search/metrics/spectral.py, its two tests, tools/analysis/spectral_ripple_audit.py). They were in the git
  index when this lane committed; no work was lost or modified. Recorded for the log.

## 2026-11-20 02:10 - Item 3 RESOLVED: B3 deviation is real and mesh-independent (local orchestrator)

- Expansion night closed 26/26 (my 16 + the other agent's 8 + 2 dense2), no interruption. The other
  agent has since launched their own `ripple_audit_2026-11-20` night (live, GPU lock held).
- Item 3 (dense B3): 91-freq grid (1.8-3.6 kHz @25 Hz + base), epw 6/9. The 2.27-3.31 kHz deviation
  is a smooth ~2.1 dB dip at 2800 Hz (band -8.28..-6.18 dB); epw6-vs-epw9 mean|d| 0.00, max 0.01 dB.
  Verdict: physical, not a grid artifact. Dense J 2.1509/2.1492 (not comparable to screen 2.8000).
- Bundle extended to 18 runs; MANDATE_STATUS item 3 marked DONE.

## 2026-11-20 00:50 - Expansion night 16/16 done; item 3 grid bug found + re-queued (local orchestrator)

- All 16 expansion jobs completed. The other agent then appended 8 `cd11__*` jobs to the LIVE
  `runs/nights/fable_expand_2026-11-19.yaml`; the same runner picked them up - their queue ran after
  mine, no interruption (the owner's intended flow).
- **SeedB (independent CMA seed 2027):** morph 1.7219, fold 1.4425, twinray 1.4873, petal 1.5941,
  ext 1.8320. **SeedC (seed 2028):** morph 1.6143, fold 1.2144, twinray 1.6883. None beats the warm
  winners (intended dataset growth); note seedC fold 1.2144 confirms the fold basin is reachable cold.
- **BUG: ripple item 3 first attempt invalid.** A config-level top-level `grid:` block is IGNORED; the
  runner uses `brief.grid` only. Both dense runs came back n=18 (the v7 screen grid) with identical
  spectra. Fix: new brief `room_landscape_80x50_700_hf1440_v7_smooth_dense.yaml` (screen_extra_hz =
  the 6 v7 extras + 73 dense 1.8-3.6 kHz @25 Hz = 79 extras), both configs re-pointed at it, and
  `x_r3_b3_dense2_epw6/9` appended to the live night (26 jobs). They run after the other agent's 8;
  the item-3 criterion is not yet tested.

## 2026-11-19 23:40 - Full-polar DI results: compact trio separated (local orchestrator)

- The 181-angle / 2048-point verify DI pass (same grid for all three) gives the compact400 trio:
  **morph 1.1692 < fold 1.2558 < twinray 1.3591**. Gaps 0.087 / 0.103 sit inside the compact floor
  0.1293, so it is still a 3-way tie by the floor, but morph leads at both resolutions (p12 73/1024:
  1.1864/1.2763/1.3734) - the ranker has a consistent ordering and the data now covers both
  resolutions.
- The v7 leaders got the same pass (petal 4.8991, tritonia v9 6.8367, v8 5.5564). Those are 29-freq
  verify-grid J; they are NOT comparable to the 18-freq screen J (4.1202 / 4.878 / 4.7503) - recorded so no
  cross-grid ranking happens.
- SeedB expansion running (morph seedB 1.7219 at 38 evals - an independent exploration, not a winner).

## 2026-11-19 23:27 - Expansion night LAUNCHED (local orchestrator)

- The other queue did not appear after ~15 min of polling and the GPU had been idle since p12; launched
  able_expand_2026-11-19 detached at 23:27:36 (controller pid 63028, parent WmiPrvSE; 16 jobs;
  cutoff arg 23:59 = a no-op for a single night, per-line timeouts bound it). If the other agent's queue
  appears it will find the GPU busy (its pre-hygiene refuses; no interruption).
- First job x_di_morph (full-polar DI, 181 angles/2048 points): verify J **1.1692** vs the p12
  73/1024 verify 1.1864 - the higher-resolution DI pass is separating the compact trio.

## 2026-11-19 - Expansion night STAGED (3-4 h): DI tie-breakers + new-identity data (local orchestrator)

- **`fable_expand_2026-11-19` staged (16 jobs, all shape-check PASS, dry-run clean)**, to be appended
  at the END of whatever queue the other agent adds (owner: wait for it, do not interrupt):
  - **A. Full-polar/balloon DI tie-breakers (6 solves, verify mode, 181 angles / 2048 points):** the
    compact400 trio (morph/fold/twinray) - the ISSUES' only step that separates their 0.09-0.19 gaps -
    plus the three v7 leaders (petal, tritonia v9/v8) for the ranker's evidence.
  - **B. Compact400 new-identity data expansion:** seedB (CMA 2027, 80 evals) on morph/fold/twinray/
    petal/ext + seedC (CMA 2028, 60 evals) on morph/fold/twinray - 8 independent explorations.
  - **C. Ripple mandate item 3:** the B3 design ee85bcd2ad67 re-solved on 1.8-3.6 kHz at 25 Hz steps
    (73 extra frequencies) at epw 6 and epw 9; success criterion predeclared in the configs
    (the 2.27-3.31 kHz deviation must persist with stable amplitude at both densities).
- Files: configs `examples/typologies/expand_2026-11-19/` (16), night
  `docs/queue/fable_expand_2026-11-19.yaml` + `runs/nights/`. Mixed briefs by design (compact400 v10xo,
  v7 home for the v7 DI, v7 smooth for B3); J is not comparable across groups.
- Estimated GPU: DI solves ~2-4 min each (6), seedB ~8-10 min each (5), seedC ~6-8 min each (3), B3
  dense ~10-20 min each (2) -> ~2.5-3.5 h.
- **State:** GPU idle, p12 done, the stale `.gpu.lock` holder (pid 54748) is dead (next runner takes
  it over). Waiting for the other agent's queue; on appearance the 16 jobs are appended at its end.

## 2026-11-19 - v10 rescore of the W4 v7 bests + compact XO loading (local orchestrator)

- **v10 rescore** (`docs/evidence/v10_rescore_scout40w4_2026-11-19/`, the shipped v10 scalar on the
  stored responses, same brief family):
  - petal (v7 4.1202) -> **v10 1.9591**
  - tritonia v9 (v7 4.878) -> **v10 3.0658**
  - tritonia v8 (v7 4.7503) -> **v10 3.6076**
  Against the v10 leaders (fold 1.3738 / ext 1.5710 / morph 1.5769) petal is 0.585 behind the fold
  leader - **outside the v10 floor 0.4677** - so the v7-home gains do NOT translate into v10 leaders;
  the B6 set should treat them as ties/candidates, not leaders. (Same-brief comparison; the smooth
  Klangfilm lane stays on its own identity.)
- **Compact XO loading** (`docs/evidence/compact400_cont_2026-11-19/xo_loading.json`, report-only):
  fold (1.2071) and morph (1.2258) both **load_raw 0.000**, driver on-axis within -1.9/+1.8 dB at
  828 Hz - healthy crossover loading. The compact winners clear the stored bar 1.7302 by 0.50-0.52
  with the floor 0.1293.
- Remaining: B6 lane set (owner approval) and the compact400 floor re-measure on its own
  screen->verify pairs (GPU, owner-approved action); the open design decisions (rolled cap 225 vs
  180-200; KL-HV-B returning lip).

## 2026-11-19 - compact400 queue DONE; continuation bundle + final chains (local orchestrator)

- The live `compact400_next10` night finished (`QUEUE DONE` 20:36:41, controller exit 1 = watchdog
  stops, partial results kept). All 19 jobs ran; my appended 9 produced:
  - **compact400 fold: 1.4677 -> 1.3147 -> 1.2071** (0.52 under the stored bar 1.7302; the cont2 gain
    alone is 0.108, just inside the 0.1293 floor, but the chain is real).
  - **compact400 morph: 1.4243 -> 1.2271 -> 1.2258** (converged; 0.50 under the bar).
  - compact400 twinray: 1.4568 -> 1.4351 (tie; pinned at the 400 mm envelope).
  - v7 petal 4.162 -> 4.1202 (+0.042, sub-floor tie); v7 tritonia_v8 4.891 -> 4.7503 (+0.141, sub-floor
    tie); v7 tritonia_v9 4.878 -> 5.566 (regression in the evaluated set; the 4.878 W2 best stands);
    v7 smooth b3_soft 2.800 -> 2.8187 (no gain; 2.800 stands).
- **Evidence bundle `docs/evidence/runs/compact400_cont_2026-11-19/`** (9 runs, ~9.9 MB): configs/seeds,
  run.json, search.ndjson + scores.csv (all terms + H/V beamwidth/DI/ripple/on-axis/impedance), best
  designs with meshes + responses; README has the chains. `mesh.msh`/`response.npz` force-added.
- The W2/W3 bundle is `docs/evidence/runs/scout40w2_2026-11-19/` (15 runs, 18.5 MB).
- Next measured actions: v10 rescore of the v7 rows; compact400 floor re-measure on its own pairs;
  `xo_loading_report --fx 1000` on the compact fold/morph winners; then the B6 lane set.

## 2026-11-19 - SCOUT40W2/W3 evidence bundle published (local orchestrator)

- `docs/evidence/runs/scout40w2_2026-11-19/`: all **15** W2/W3 runs (18.5 MB) with the same schema as
  the SCOUT40 bundle - `config.yaml` (seed + bounds), `run.json` (objective/warm start/lib SHAs),
  `search.ndjson` + `scores.csv` (per-eval terms + H/V beamwidth, DI, ripple, on-axis, impedance arrays
  + scalars), `summary.json`, and each best design's `design.json`/`metrics.json`/`mesh_meta.json`/
  `mesh.msh`/`response.npz`. Plus the night yaml, queue log/state, summary and the preflight logs.
  README carries the result chains: petal 4.892->4.196->4.162 (+0.73), tritonia v8 5.325->4.891
  (+0.43), tritonia v9 5.289->4.878 (+0.41), crowe_x square 7.911->7.598 (+0.31), fold/morph closed
  as ties, crowe_x osse no-headroom, rosse tie.
- Commit with the bundle (mesh.msh/response.npz force-added). The live compact400 queue continues
  independently (w4__tritonia_v9 running, then w4 b3, c4x_04, c4x_05).

## 2026-11-19 - Queue verification + fold cont2 (local orchestrator)

- **End-to-end verification of the live queue passed** (`scratch/verify_live_queue.py`, exit 0): 19 jobs,
  every config loads, every warm start reads (hairline table in the log), budgets 80 / timeouts 5400 /
  `HORNLAB_GPU_LOCK=refuse`, the live `runs/nights` file is byte-identical to the `docs/queue` copy, and
  the GPU lock is held by the running job (w4__tritonia_v9). The runner's queue_state shows 15 done,
  the rest pending (it re-reads before each job, so the last appends are picked up).
- Appended-job results so far: c4x_01 morph **1.2271** (from 1.4243, +0.197 above the compact400
  floor), c4x_02 twinray **1.4351** (from 1.4568, tie), c4x_03 fold **1.3147** (from 1.4677, +0.153
  above the floor), w4__petal **4.1202** (from 4.162, tie), w4__tritonia_v8 **4.7503** (from 4.891,
  tie). Pins: twinray at the 400 mm morph_height envelope (tie, no further), fold at az_a_cos_amp low
  8.13 (kernel allows -60..60).
- **c4x_05_fold_cont2** appended (job 19): az_a_cos_amp low widened to 0 (neutral cosine term), budget
  80, warm from 1.3147 (mean d805f33c65b2), pin-ignore q + az_a_cos_amp; shape-check PASS.
- Live order now: ... w4__klangfilm_b3_soft, c4x_04_morph_cont2, c4x_05_fold_cont2.

## 2026-11-19 - c4x_01 morph: 1.4243 -> 1.2271 (real win); cont2 appended (local orchestrator)

- **`c4x_01_morph_cont`: best 1.2271** (37 evals) from the compact400 run's 1.4243 -> **0.197 J, ABOVE
  the compact400 floor 0.1293**. It is the strongest compact result so far (the stored bar was 1.7302).
  It then pinned at the LOW limit of `a0_deg [1, 3]`; a0 is a wall half-angle with no hard spec range,
  so `c4x_04_morph_cont2` widens the low side to 0.25 (positive, cylindrical-throat limit), keeps
  budget 80, warm-starts from 1.2271 (mean 11870ed193af) and pin-ignores `morph_width_mm` + `a0_deg`.
  Appended as job 18 (shape-check PASS 2809/24000).
- `c4x_02_twinray_cont` running (9 evals, best 1.443 from 1.4568). Then c4x_03, the four w4 v7 lanes,
  and c4x_04.
- Housekeeping note: `runs/nights/p11_s2w_2026-11-19/queue_state.json` still shows its dead runner's
  job as "running" (stale state from the GPU-busy exit); the p11 lane's STOP file is present and the
  runner is gone, so it is a display-only artifact (not touched: another lane's bookkeeping).

## 2026-11-19 - p11_s2w night: superseded, not relaunched (local orchestrator)

- The other lane's `p11_s2w_2026-11-19` night (v10 s2w fold/ext, 80 valid) was launched at 18:35
  **while the compact400 night was mid-job**. Its pre-hygiene got `gpu-clean --lane gpu rc=3`
  (**GPU busy** on the compact400 solve) and it exited 1 with no solve - i.e. the GPU lock prevented a
  concurrent solve exactly as designed; nothing was interrupted. A STOP file is present in its night
  dir (its lane's own stop).
- **No relaunch needed: the same v10 s2w work already ran in the compact400 night** as
  `c4n__09_fold_warm_v10_s2w` (best **1.3738** vs the published 1.4214 -> 0.048 better, inside the v10
  0.4677 floor = tie) and `c4n__10_ext_throat_v10_s2w` (best **1.5710** = the published leader -> tie).
  Re-running `p11_s2w` would duplicate a tie.
- My appended continuations are running behind them (`c4x_01_morph_cont` at 15 rows, GPU lock held by
  it). No GPU conflict remains: one live runner (compact400), one lock holder.

## 2026-11-19 - Appended 7 x 80-eval continuations to the LIVE compact400 queue (local orchestrator)

- **Live queue polled first:** `compact400_next10_2026-11-19` is running (controller pid 23752,
  runner 27612/46928, GPU lock held by the job); job 9/10 (`c4n__09_fold_warm_v10_s2w`) was at 6 rows.
  No interruption was made; the jobs below were APPENDED to `runs/nights/compact400_next10_...yaml`
  and its `docs/queue` source; the runner re-reads the file at every job boundary.
- **My night `fable_scout40w2` finished 15/15** (recorded earlier): petal 4.162, tritonia v8 4.891,
  tritonia v9 4.878, crowe_x square 7.598, fold/morph ties (closed), rosse tie, crowe_x osse no-headroom.
  These are the v7 home/smooth briefs; the compact400 night runs the v10xo compact brief - J is NOT
  comparable across the groups (the append header says so in the file).
- **Appended (jobs 11-17, each budget 80, 5400 s, HORNLAB_GPU_LOCK=refuse, warm start at its best):**
  1. `c4x_01_morph_cont` (compact400): from 1.4243, morph_width widened to the 400 mm envelope.
  2. `c4x_02_twinray_cont` (compact400): from 1.4568, k widened to 2.5 (osse_baseline documented range).
  3. `c4x_03_fold_cont` (compact400): from 1.4677, q widened to the OSSE cap 1.0.
  4. `w4__petal_hvlaw_v7` (v7 home): from 4.162, q cap pin-ignored.
  5. `w4__tritonia_v8` (v7 home): from 4.891, az_fold_v widened to -10, fold knobs pin-ignored.
  6. `w4__tritonia_v9` (v7 home): from 4.878 (the W2 best; the W3's az_fold_v widen regressed), keep
     the W2 angle box, az_fold_v_width widened to 3..40, fold knobs pin-ignored.
  7. `w4__klangfilm_b3_soft` (v7 smooth): from 2.800 (3.540 -> 2.841 -> 2.800), hard ceilings pin-ignored.
- **Gates:** all 7 production warm starts read OK (means 2.8002 / 4.1616 / 4.8911 / 4.8785 / 1.4243 /
  1.4568 / 1.4677 at budget 80); `shape_check` all PASS (2.8-5.4k / 24000 dof). Configs:
  `examples/typologies/scout40w4_2026-11-19/` and `examples/typologies/compact400_2026-11-19/c4x_*`.
- **Overlap check:** the live night already reuses my `scout40w3` petal/tritonia_v8 configs at the
  400-cube brief (c4_04/c4_05), and its jobs 9-10 are the other lane's v10 s2w widenings. The appended
  compact continuations target the lanes that BEAT the compact400 bar 1.7302 (morph/twinray/fold); the
  v7 lanes are distinct briefs. No duplication of the v10 s2w work.

## 2026-11-19 - compact400: 400 mm-cube horns + next-10 night STAGED (Fable senior, CPU only)

- **Owner ask:** have 10 next queue items ready, focused on the best improvement opportunities and on
  new horns inside a 400 mm cube. GPU and CPU lanes were free and nothing ran on the GPU. **The night is staged, not launched**,
  because GPU budget stays with the owner.
- **Measured gap** (`scratch/fable_architecture/compact400_2026-11-19/scan_400cube.py`): 16,270 stored
  solved designs fit 400^3. 393 hold H 60-100 / V <= 75 at 1 kHz with lfp20 <= 625 Hz, but 375 of those are
  2-inch ATH core-law and only **2 are HF1440 1.4-inch** (TwinRay). At 850 Hz only 273 of 16,270 hold the
  corridor, so the compact_xo900 onset is out of reach at this size. The "compact" register
  slate is 460-590 mm wide; none of it was a 400 mm horn.
- **New brief identity** `examples/briefs/compact400_2026-11-19/compact400_xo1000_1400_hf1440_v10xo.yaml`:
  objective v10 scalar unchanged; envelope 400/400/385 (+15 gate); F_X 1 kHz; H 60-100 / V 40-75 from
  1 kHz, held 1.4-8 kHz; never rankable against v7/v10/compact_xo900. **Floor 0.1293 J** (257 pairs,
  fleet-sourced; re-measure on compact400 pairs). CPU rescore of 978 stored in-cube HF1440 designs:
  the **bar is 1.7302** (TwinRay `bbe858b5b6a4`, 367x377x255); the October 90x60 horns are 2.14-2.31
  (too short, V too wide at 1 kHz).
- **Night `docs/queue/compact400_next10_2026-11-19.yaml` (+ admission), dry-run OK, 10 jobs:**
  8 cube lanes c4_01-08 (fold_warm, morph, ext-throat, TwinRay seeded at the bar, petal A1, tritonia
  A3, ATH core law at r0 18, Iwata AR) + 2 home v10 s2w (fold_warm L_mm hi 330; ext-throat
  `az_a_cos_pow` lo 0.5; both seeded at the published bests, closing the Q3 open item). All 10
  `shape_check` PASS (cube seeds 367-400 mm max side, 1.7-3.5k dof) and load; `search_preflight`
  --samples 32 on each. OSSE lanes use `resample_strict` (their refusals are `invalid_geometry`,
  which `graded` does not touch). ext-throat's 34-56 % uniform-box refusal rate is the family's box: the
  unwidened source shows the same 21 of 32.
- **Files:** configs `examples/typologies/compact400_2026-11-19/` (generator
  `scratch/fable_architecture/compact400_2026-11-19/make_configs.py`); readout and evidence
  `docs/research/compact400_2026-11-19/`. INDEX and CODE_MAP rows were added. The other lane's uncommitted GUI
  edits and its budget-driver audit (and its INDEX line) were left out of this commit.
- **State.** GPU free; nothing running. Launch command in the README section 5.

## 2026-11-19 - Compact slate: owner decisions executed (CPU only, no GPU)

- **Owner decisions.** Next compact-horn move = author the crossover-aware identity first (no new
  GPU); assembled-BL prerequisite = real 10-inch geometry + panel fit first. GPU and CPU lanes were
  free and nothing was queued; **no GPU time was spent**.
- **Three CPU lanes delivered and verified:**
  1. **A5 re-emit** `examples/typologies/compact_2026-11-19/rf__rect_radial_wide_v8_currentgen.yaml`.
     The archived 2026-11-15 recipe is refused by design (`rolled_family.py:97-99`); the re-emit
     materialises 541.397 × 298.591 × 238.118 mm vs the archived saved-mesh 541.3 × 298.6 × 238.1 mm
     — the drift is **provenance-only, not geometric**. `shape_check` PASS 5096/6000 dof;
     `search_preflight` ok; `rows_grid_points` round-trip OK. No solve run.
  2. **Crossover-aware identity** `examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml`
     (objective v10 scalar unchanged; F_X 850 Hz; H 65-100 / V 40-75 anchored 850-1250; band
     350-8000 retained; never rankable vs v7/v10). **Floor 0.2783 J** (top-28-pair protocol, 257
     pairs; same command reproduces v10's 0.4677 exactly). CPU replay of six solved designs:
     **fold_warm 1.0624 < A3 1.6028 ≈ A1 1.6578 ≈ A2 1.7074 < C2 2.4680 < K1 3.4445**. Read: even
     under the crossover-aware identity the petal/tritonia candidates do not beat fold_warm
     (0.540 J, real); A1/A3/A2 tie inside the new floor.
  3. **10-inch panel fit** `driver_10inch_fit.md`: **10PR300 is LEGAL on the recorded 371.2 mm BL
     front only with the 45 cm² port** (required 157.095 vs available 175.105 mm, +18.0 mm);
     12PR300 stays illegal (−32.0 mm); 170 cm² port fails even the 10-inch (−53.4 mm) — port area
     is the binding lever. Correction: `frame_od_mm: 261` / `cutout_mm: 232` are `[measured]` in
     `examples/systems/driver_geometry/faitalpro_10pr300.yaml`, so the register's "frame radius
     NOT_YET_AVAILABLE" is superseded (radius 130.5 mm; spacing table was a lower bound). Still
     missing: cone depth, surround, dust cap, mounting depth; BL still stages the demo cone.
- **Registered.** `docs/CODE_MAP.md` and `docs/INDEX.md` rows added (same commit);
  register amended (§5 parent amendment 2). Uncommitted GUI edits from the other lane remain
  untouched and were excluded from staging.
- **State.** GPU/CPU lanes free; nothing queued. Not done: no GPU solve, no BL staging, no PR #75
  action (still OPEN/draft, superseded locally at 627b880), no push.

## 2026-11-19 - Horn sheets: set B added, dated, larger text

- Rendered 2026-11-19 17:24 EST. Set A: 61 horns solved 2026-11-18 14:00 to 2026-11-19 13:51 EST (sheets 01-21).
  Set B: 4 newly solved horns 2026-11-19 15:22 to 15:59 EST (sheets 22-23). Every sheet and row carries its date.
- Text enlarged (scores column, labels, titles). Older sheet versions removed from the folder; history keeps them.
  Index: `docs/renders/2026-11-19-last-day-horns/README.md`.

## 2026-11-19 - Last-24h horn sheets: score column added (renders)

- Sheets re-rendered at 200 dpi with a scores column per design: J (total), the saved `best.json` terms
  (not additive to J), f11 and lfp20, and -6 dB coverage, DI and ripple at 1.07 and 2.27 kHz. Row labels
  moved above each row so they are not clipped. Files and per-sheet design list:
  `docs/renders/2026-11-19-last-day-horns/README.md`. Supersedes the score-less sheets in `6960f19`.

## 2026-11-19 - Last-24h solved horns: contact sheets (renders only, no solves)

- **61 unique best designs** from runs dated 2026-11-18 14:00 local onward, each with a completed solve
  (`ok: true`, balloon DI). Rendered as 21 contact sheets at 200 dpi (3 designs/sheet): isometric,
  top-skew (camera from +y, added in `render_last_day.py`, not in `tools/render/render_views.py`), V cut
  (x=0), H cut (y=0), V and H dispersion. Durable copies + per-sheet design list:
  `docs/renders/2026-11-19-last-day-horns/README.md`.
- Caveats: J is comparable only within a brief; two design hashes repeated across runs and were kept once;
  a small `x10^4` frequency offset remains on some heatmaps (cosmetic). No GPU or CPU solve was started.
- Uncommitted GUI edits from another lane remain in the tree and were not included.

## 2026-11-19 - Q3 night: more solves + never-run typologies (complete, ~45 min GPU)

- **Night `q3_more_solves_2026-11-19` DONE, 6/6 jobs, ~45 min GPU** (the three continuations were
  nearly free: the CMA trajectory replays deterministically and the identical design/mesh/solve triples
  are solve-cache hits - two of them closed in 61 s). Evidence: `docs/evidence/Q3_MORE_SOLVES_2026-11-19.md`.
- **The two v10 leaders are box-limited, not budget-limited** [measured]: the fold_warm continuation
  pinned `L_mm` at its HIGH limit (3/6 of the top 6) and ext_throat pinned `az_a_cos_pow` at its LOW
  limit (5/6) - both stopped by the bound-pin watchdog in ~61 s with unchanged bests. A v10 s2 must
  widen those two knobs AND warm-start at the published best designs; more evals at the current boxes
  are provably wasted.
- **Crowe v2a v10 closed**: continuation improved 6.7324 -> 6.4779 in 117 evals then stalled
  (<0.5 % / 40 valid). The gain is below the v10 floor 0.4677 = a tie; no further continuation.
- **First-ever solves of never-run constructions**: Le Cleach H/V per-plane pair 7.8865 (66 valid, ok;
  beats the family's previous 8.037 on the same smooth-v7 identity - likely a tie by the 0.3105 floor);
  Crowe ES biradial 9.2355 (37 valid, ok; only solved instance of that generator).
- **New rows type `lecleach_ar` configured and storm-limited** [measured]: a NEW config for the
  area-preserving AR stretch (a rows type with no prior config anywhere) reached 8.0791 at only 15
  valid before a 44 % refusal storm. Seed is meshable (588x397x271, 2953 dofs); the box corners
  (AR_m up to 2.2 x stop 230) are not. Next: narrow the box, re-preflight, rerun.
- **Coverage map published**: of 48 home_landscape configs, 28 never ran and 3 of those are DEAD (rows
  types removed from the generator: klangfilm_ellipse, rolled_rect_pucker, rosse_rect); rows types
  salmon_axisym / lecleach_mod have no config anywhere; the October sculpture families are portrait/
  square by construction and need their own brief identity + measured floor before a fair test.
- Queue provenance: `docs/queue/q3_more_solves_2026-11-19.yaml` (+ admission); not-queueable list with
  reasons is in the night file header. GPU lane free at the end; nothing queued.

## 2026-11-19 - PRIORITY10 night complete (11/11, 2.18 h) + compact-horn register (push)

- **Night `fable_priority10_2026-11-19` is DONE**, 11/11 jobs, 7,865 s GPU (2.18 h) — the no-gain
  watchdog ended stalled lanes, so the feared 7-9 h never materialised. Chained behind the W2/W3 night
  with `queue.ps1 -WaitPid`; no overlap, no duplicate job. Manifest + per-job evidence:
  `docs/evidence/PRIORITY10_QUEUE_2026-11-19.md` §11.
- **Result: no promotion, no verify.** Recording checks: fold_warm 1.5433 (published 1.4214) and morph
  1.5769 (1.4305) tie inside the v10 floor 0.4677; ext-throat 1.7919 (1.5710) ties; twinray 2.5748 is
  0.80 J worse than its published 1.7726. Failures worth keeping: c200 vbeak +0.029 and rolled record
  +0.227 J because `dislope` is 71-75 % of those hosts' v10 cost; vt_v1 +0.015 J because `load` is 52 %;
  b3_soft +0.144 J with `load 0.0` but `dislope 2.10`. The rolled whole-family hybrid is the one real
  mover: 15.549 -> 9.3054 (+6.24 J) at 30 valid.
- **B6 seeding defect (measured).** All four B6 s1 configs start at the lane seed, not at the design that
  produced the published v10 best (twinray 13/27 knobs differ, morph 14/31). Any s2 must warm-start at
  `00826f071b24` / `436a4d221328` / `a23763f1c6fc` / `85c59331e4a3`.
- **Fable v2** landed earlier today by reviewed diff (627b880): record-edit knobs + 4 configs + beak
  tests, 29/7 tests green, shape/preflight gates recorded. Upstream `main` is still 138d88a, so PR #75 is
  unmerged; `gh` could not resolve the repo from this session (UNVERIFIED, refs confirmed by ls-remote).
- **Compact-horn / woofer handoff.** Reconciled state, dispatched one CPU-only agent (C-SCOUT), verified
  its artifacts. Register (10 rows, measured config_sha + inner/outer bbox from saved bests), mesh
  preflight and a bounded solver proposal are in `docs/research/compact_horn_system_2026-11-19/`.
  Parent filled the named blocker with CPU v10 rescores: A1 petal 1.9858, A3 2.7734, A2 2.8813, C2
  4.8193. A1 misses its own 0.4677 gate by 0.10 J, so **no GPU was authorised**; the ask was 0
  unconditional anyway. Every assembled-horn claim stays `NOT_YET_AVAILABLE` (no BL case).
- **State.** GPU and CPU lanes free; nothing queued. `docs/ACTIVE_STATE.md` updated. Not done here: no
  verify pass, no s2, no new brief identity, no push of `main`.

## 2026-11-19 - Fable senior: score-term audit + Gate A crossover-loading diagnosis (CPU only, committed)

- **Verdict.** The "650-900 Hz loading hump" reported earlier today was unit-acceleration referencing, not acoustics.
  - The solver drives unit normal acceleration (`meta.spl_reference`).
  - Per unit velocity, fold_warm 00826f071b24 is +1.3/+2.8 dB of power at 643/828 Hz relative to 2 kHz. That equals 10 log10 of its Re z ratio (1.93/1.03).
  - Balloon power over throat input power is 0.95-1.00 for all six audit designs on both grids.
  - The feature is one near-cutoff Re z overshoot, not a resonance train.
  - rosse_rect_cd and tritonia_v9 are 5-8 dB under-loaded at 643-828 Hz, so `load` charges a real deficit.
  - The real ripple is ext_throat a23763f1c6fc: Re z 0.59 at 1.2-1.4 kHz.
- **Driver-independent.** The ranking holds for all 32 members of an [inferred] 1.4"-exit driver bracket.
  - The owner has said the driver is open; it need not be the HF1440.
  - No 1.4" pro driver checked publishes Mmd, Sd or fs.
- **Score policy.** v10 and `dislope` are unchanged, and no v11 is justified.
  - dislope = 0 promotes beaming horns (audit F1). Side lobes (F3) and max_edge (F4) were rejected.
  - Screen->verify floor: `load` explains 56% of the variance. The directivity sub-J SD is 0.055 J on the top-28. That is a grid sensitivity, not a confidence interval.
  - Audit decision 3 (the hold on J-only continuations) is lifted. Decision 2 (no B6 reruns on the current grid) stands.
- **Code.**
  - New `tools/analysis/xo_loading_report.py`, report-only XO diagnostics. 6 tests, including a pulsating-sphere energy-balance check.
  - `tools/analysis/rescore_identity.py` rows now also carry `run_path` (audit F8: 35 nested rows had stored only `screen`). `run` is unchanged.
  - 19 targeted tests pass.
- **Evidence.**
  - Reproducible outputs: `docs/evidence/xo_loading_gateA_2026-11-19/`.
  - Reports and scripts, force-added under `scratch/fable_architecture/`: `score_term_audit_2026-11-19/` (F6 banner-corrected) and `xo_loading_gateA_2026-11-19/`.
- **Provenance.** 205 hashes have more than one design dir. 9 of them are on different meshes (up to 0.21 dB), so the same hash is not the same field.
- **Not done (owner-gated).** Optional dense re-solve: 3 designs, 1/24 oct, 450-1800 Hz, `HORNLAB_GPU_LOCK=refuse`. No GPU, queue, default or score identity was touched. Unrelated uncommitted GUI edits in the tree were left alone.

## 2026-11-19 - Fable v2 integrated + PRIORITY10 ten-horn queue staged (superseded by the completion entry above)

- **Fable v2 landed by explicit reviewed diff** (branch `claude/adoring-ramanujan-1m4b3g`, commits
  `a93ac18`+`d902a33`, 2 commits on a stale base): `geometry/edits.vertical_beak` +
  `lip_clearance_mm`, `design/generators/record_body.py` record-edit knobs (`g_vt_mm`, `g_vt_hold`,
  `g_beak_v_mm`, `g_beak_start`) and `outer_offset: normal`, the 4 `examples/typologies/fable_v2_2026-11-19/`
  configs, `tests/test_design_record_body_beak.py`, and the research doc. Both code files were
  byte-identical to the merge base, so the patch is additive. **Not** taken: the branch's edit to
  `docs/queue/fable_scout40_2026-11-19.yaml` (4 new jobs above a completed night) and its coupled
  `tests/test_queue_fable_scout40.py` (would assert 22 jobs) - the new jobs were extracted into a
  separate night instead, so the old night can never be rerun wholesale.
  Verification: `compileall` OK; `tests/test_design_record_body_beak.py` 7 passed;
  `-k "record_body or vertical_timing or edits"` 29 passed / 1 skipped (botorch absent);
  `shape_check` OK on all 4 configs; `search_preflight --samples 48` -> c200 beak 0/48, rolled
  record 20/48 mesh-cap, rolled hybrid 2/48.
- **Night `fable_priority10_2026-11-19`** (`docs/queue/fable_priority10_2026-11-19.yaml` + admission):
  11 jobs, the owner handoff's ten experiments deduplicated by physical identity, ordered #1 #2 #3,
  B6 s1 (#4, #5), #8, B6 s1 (#7, #6), then #9/#10. Launch is serialized behind
  `fable_scout40w2_2026-11-19` (`queue.ps1 -WaitPid`) - no concurrent GPU runner.
- **CPU-first v10 re-scores** (`runs/analysis/v10_priority10_2026-11-19/`, identity
  `8892be0f…`, `mixed_identity: false`): Klangfilm b3_soft best 3.7428 (seed = `3545b3e078ac`),
  CROWE v2a best 7.0685 (seed `1c206df9912f` = 10.4104), biradial vt_v1 best 5.2808. Scale check:
  the published-corridor brief reproduces J byte-identically on a fresh run.
- **Promotion holds**: petal W3 4.16163 vs W2 4.1960 = tie (no v10 campaign); tritonia v8 W3 4.8911
  is a real +0.48 but tritonia v9 W3 5.0032 is worse than its W2 - both wait for `verify` polars.
- State/provenance: `docs/evidence/PRIORITY10_QUEUE_2026-11-19.md`. Note local `main` is 22 commits
  ahead of this branch (GUI P2/P3), unrelated uncommitted GUI edits were left untouched.

## 2026-11-19 - Owner gates B and C answered (horn + woofer GUI)

- **Gate B** (before P5): asked "May the GUI launch CPU screen jobs, and may it write user specs to
  examples/systems/user/?" Owner answer, exact: **"Yes to both (Recommended)"**. Build: the wizard
  launches CPU screen jobs into `system_runs/screens/<study>/` and Save-as writes
  `examples/systems/user/<name>.yaml` (explicit Replace confirm; parser-message refusals).
- **Gate C** (plan question 3, before P6): asked "Is GUI-launched CPU stage + validate acceptable
  (no solve)?" Owner answer, exact: **"Yes (Recommended)"**. Build: Stage + Validate are CPU jobs
  through `JobManager` (one system job at a time, CPU lane lock respected); Solve stays disabled
  until decision 6 (gate D).
- Owner asked why system solves do not appear in "recent solves": answer recorded in the same
  thread - the horn-side Runs/lanes views read `runs/` (horn searches), while the BL cases live in
  the separate `system_runs/` store shown under Horn + woofer -> Cases; GUI-launched system jobs do
  not exist until P5/P6. Screens was added to the nav (it was URL-only).
- Owner UI feedback (twice) on the first P1 build: "looks like total shit / doesn't make sense" and
  a second visual review. Fixed: 665 px ledger rows -> <=124 px with tokens on a full-width
  sub-row; all groups open; reconciled solved-vs-staging band; readiness risk KPIs; 260/190 px
  charts with connected phase and a wrapped/unwrapped toggle (`phase_unwrapped_deg` in Python);
  matched polar panels + colour legend; enlarged annotated geometry; 375 px overflow fixes.

## 2026-11-19 - P3 mesh endpoint + P4 A/B compare layer (horn + woofer GUI)

- `data_hw.py::hw_mesh` (additive): `GET /api/hw/mesh/<exp>/<case>?part=box|horn` -> flat mm
  verts/tris + bbox; box = staged `exterior.msh` (parent resolved for solve-only cases), horn =
  manifest mesh read only through `_inside` with scale/translation applied. Deterministic
  vertex-cluster decimation above 60 k triangles (`decimated` flag); non-triangle meshes and
  out-of-store paths refused by name. Real calls: wide box 2010 tris (9.3 ms warm), horn 5950 tris.
- `data_hw_compare.py` (new): `GET /api/hw/compare?a=&b=` refuses `GRID_MISMATCH` /
  `PROBE_SET_MISMATCH` / `EXCITATION_MISMATCH` as data; on success per-probe/per-excitation
  |B_a/B_b| dB + wrapped delta phase + per-band rows. The recorded-evidence statistic
  `100*max|p_a-p_b|/max|p_b|` reproduces motor A/B LF 119.835 % and XO 140.2-149.4 % (probe band
  600-1200 Hz) and G6 0.5751 (woofer down30) / 0.3558 (horn down30) exactly; the display bands
  (LF<500, XO 500-1500, HF>1500) are labelled as display choices. `hw_compare_matrix` emits cells +
  adjacent-pair edges (`GET /api/hw/compare-matrix?keys=a,b`), wired and tested.
- Tests: `tests/system/test_gui_hw_mesh.py` (11) + `test_gui_hw_compare.py` (8) + dispatch
  assertions in `test_gui_hw.py`; the recorded motor/G6 numbers are asserted against the real dirs
  (skip when absent), not widened. Total focused GUI-data tests: 64 passing.

## 2026-11-19 - P2 screen data layer + panel-fit recompute (horn + woofer GUI)

- New `gui/data_hw_screen.py`: allow-listed screen-study reads (`system_runs/woofer_seed*`,
  `system_runs/screens/*`), grouped by 16-hex `study_id` (replay count + byte-identical flag),
  verbatim shortlist/kept rows, rejection ledger grouped by stage, and `pareto_ids` recomputed in
  Python via `system.score.dominates` (9 == the recorded Pareto count). `panel_fit()` is the pure
  `POST /api/hw/panel-fit` recompute; it refuses unknown/out-of-range fields by name.
- `system/woofer_seed.py` additive: the panel-fit arithmetic is one private chain; new
  `bl_panel_fit_separation()` reports `required_m`/`available_m`; `bl_panel_fit_feasible()` keeps
  its exact signature and tuple return. Verified: real 12PR300 on 371.2 mm -> 0.182097 required vs
  0.150103 available (`BL_PANEL_FIT_DRIVER_PORT_SEPARATION`); the recorded 170 cm2 demo cell ->
  0.187561 vs 0.144639, refused.
- `server.py` wiring: `GET /api/hw/screens`, `GET /api/hw/screen/<study>`, `POST /api/hw/panel-fit`
  (dispatch test added in `tests/system/test_gui_hw.py`). New tests:
  `tests/system/test_gui_hw_screen.py` (31) + 2 appended in `test_woofer_seed.py`.
- P1 backend: ledger `counts` now always carries solved/staged/stage_failed/solve_failed/recorded/empty.
- Tooling: `tools/gui/browser_check.py` (Playwright §8.6 checklist: console errors, page scroll,
  chart width/aria, no `<h1>` on hw pages, keyboard reach, reload-restores-hash, screenshots).
- Owner feedback on the first P1 build: ledger rows were 665 px tall (verbatim token + gloss in an
  89 px cell) and only one experiment group was expanded, plus a "solved 25/25" case showing a
  "Staging failed" banner without reconciliation. A UI revision is in flight (P1 rev).

## 2026-11-19 - SCOUT40W2: morph chain closed; tritonia v8 W3 improving (local orchestrator)

- **morph_v8: 3.402 -> 3.232 (W2) -> 3.757 (W3) = tie/no gain, and the refusal storm PERSISTED (48%)
  even with `resample_strict` + `error_policy`.** The lane is storm-prone and not improving; per the
  economy rule the chain is CLOSED (no W4). Recorded: morph_v8 does not move on this brief; a future
  attempt needs a box narrowing, not another penalty/step change.
- `s40x3__tritonia_v8` (n widened to 4..10): running, best **4.917** at 8 evals vs the W2 5.373 and the
  SCOUT40 control 5.325 -> a real ~+0.41 gain and already above the 0.31 floor. This vindicates the n
  widen. Remaining: tritonia v9, petal, square, rosse W3s.

## 2026-11-19 - SCOUT40W2: fold chain closed as a tie; morph W3 running (local orchestrator)

- **fold_warm: 3.754 -> 3.682 (W2) -> 3.695 (W3) = tie, no gain after three runs.** The W3 (both fold
  widths widened to the kernel floor) did not improve and pinned on a DIFFERENT, peripheral knob
  (`az_a_cos_pow` low 1.23779), i.e. the lane is at its local optimum and the box is no longer the
  story. Per the economy rule (stop the arm rather than chase pins), the fold chain is CLOSED as a
  tie; no W4. Recorded for the B6/readout: fold_warm does not move on this brief.
- `s40x3__morph_v8` running (7 evals, best 3.757 vs the W2 3.232 - the warm mean is at 3.232 and the
  early samples are above it). Remaining W3s: tritonia v8/v9, petal, square, rosse.

## 2026-11-19 - SCOUT40W2: square (+0.29) & rosse W3s appended (local orchestrator)

- `s40x__crowe_x_square_v7` (W2, resample_strict): best **7.618** vs the control 7.911 -> +0.29 J (just
  under the 0.31 floor), then a **refusal storm 38%** persisted. Per the economy ordering
  (step -> budget -> box), the W3 halves the step: `sigma0 0.20 -> 0.12`, resample_strict kept,
  warm-started from 7.618 (mean b35c19653487) - appended as `s40x3__crowe_x_square_v7`.
- `s40x__rosse_rect_cd_v7` (W2, tmax pin_ignore): best 4.560 (= the control; no gain), pinned at the
  LOW limit of `g_b [0, 0.4]`. The R-OSSE kernel documents and tested b < 0 down to **-0.10** (still
  inside the 480 mm envelope, tools/geometry/rosse_rect.py:62-68) - a real widen, not a hard floor.
  W3 `scout40w3__rosse_rect_cd_v7` has `g_b -0.10..0.4` with `pin_ignore: [g_tmax, g_b]` on the
  command job. Shape-check pass (4737/24000).
- Night at 8/15: W3 `s40x3__fold_warm` running (5 evals, 3.762). Queued after: morph W3, tritonia v8/v9
  W3s, petal W3, square W3, rosse W3.

## 2026-11-19 - SCOUT40W2: petal WIN (+0.70) -> w3; crowe_x osse no-headroom (local orchestrator)

- **`s40x__petal_hvlaw_v7`: best 4.196 vs the control 4.892 -> +0.70 J, ABOVE the floor.** The
  resample_strict fix is validated by a real gain. It then pinned at the HIGH limit of `q [0.9, 1]`;
  every shipped OSSE config caps q at 1 (37 configs; no OSSE q > 1 exists), so this is a pin_ignore
  case. W3 `scout40w3__petal_hvlaw_v7` keeps resample_strict, warm-starts from 4.196 (mean
  fab20de9dd19) and is appended as `s40x3__petal_hvlaw_v7` with `watchdog: {pin_ignore: [q]}` (job 13).
- **`s40x__crowe_x_osse_cd_v7`: no gain - the best was still the seed (J 5.345) after 30 valid evals.**
  The preflight had predicted `no_headroom` (the config seed IS the lane best). A requeue with the
  same seed/box repeats it, so this lane is recorded as a **no-headroom negative, not requeued**;
  it needs a new DOF/box or a different seed to be worth GPU time.
- `s40x__crowe_x_square_v7` running (11 evals, best 7.907 vs the 7.911 control - flat so far).

## 2026-11-19 - SCOUT40W2: tritonia v9 WIN (+0.41) -> w3; petal running (local orchestrator)

- **`s40x__tritonia_v9`: best 4.878 vs the SCOUT40 control 5.289 -> +0.41 J, ABOVE the v7 0.31 floor.**
  This is the first W2 lane with a real gain (the morph_width pin_ignore let it continue past the
  envelope). It then bound-pinned at the HIGH limit of `az_fold_v_deg [-31, -27.5]`; the kernel allows
  +/-40 (families.py:126), so W3 widens the high side to -10
  (`examples/typologies/scout40w2_2026-11-19/scout40w3__tritonia_v9.yaml`, warm from 4.878, mean
  5f689f0f4865) and is appended as `s40x3__tritonia_v9` (job 12). Shape-check pass.
- `s40x__petal_hvlaw_v7` running (16 evals, best 4.561 vs the 4.892 control, i.e. improving; the
  resample_strict fix is holding).
- Night at 4/12 done; the two W3 fold/morph continuations and the rest remain queued.

## 2026-11-19 - SCOUT40W2: tritonia v8 w3 appended; v9 running (local orchestrator)

- `s40x__tritonia_v8` (W2, morph_width pin_ignore): best **5.373** (33 evals) vs the control 5.325
  (slightly worse; the morph_width pin did not buy a gain), then bound-pinned at the HIGH limit of
  `n [4, 7.5]`. The OSSE profile exponent is documented 2..16, so W3 widens `n` to 4..10 in one step
  (`examples/typologies/scout40w2_2026-11-19/scout40w3__tritonia_v8.yaml`), warm-started from 5.373
  (mean 3f90557b9b31); appended as `s40x3__tritonia_v8` (job 11). Shape-check pass.
- Night `fable_scout40w2_2026-11-19` is on job 4: `s40x__tritonia_v9` (3 evals, best 5.030 vs the
  5.289 control; morph_width pin_ignore active).

## 2026-11-19 - SCOUT40W2: morph W3 appended; tritonia v8 running (local orchestrator)

- `s40x__morph_v8` (W2, morph_rate widened): best **3.232** (25 evals) vs the control 3.402 (+0.17,
  sub-floor), then stopped by a **refusal storm 44%** over the last 25 attempts (not a pin). The
  documented remedy is `infeasible_penalty: resample_strict` + `error_policy: retry_same_then_stop`
  (a widen would add illegal territory). W3 continuation
  `examples/typologies/scout40w2_2026-11-19/scout40w3__morph_v8.yaml` keeps the widened morph_rate,
  adds that pair, and warm-starts from 3.232 (mean 69aca6e15dca); appended as `s40x3__morph_v8`
  (job 10). Shape-check pass.
- Night `fable_scout40w2_2026-11-19` is on job 3: `s40x__tritonia_v8` (21 evals, best 5.373 vs the
  5.325 control; the morph_width pin_ignore is active).

## 2026-11-19 - SCOUT40W2 progress: fold w3 appended; morph running (local orchestrator)

- `s40x__fold_warm` (W2, az_fold_h widened): best **3.682** (31 evals) vs the SCOUT40 control 3.754
  (+0.07, sub-floor) and then bound-pinned at the LOW limit of `az_fold_v_width_deg [8, 40]`. The
  kernel allows 3..60 for both fold half-widths (families.py:127,129), so a W3 continuation widens
  **both** fold widths to 3..40 in one step (not one knob at a time) and warm-starts from 3.682:
  `examples/typologies/scout40w2_2026-11-19/scout40w3__fold_warm_v7.yaml`, appended to the live night
  as `s40x3__fold_warm` (job 9). Shape-check pass; warm start mean b6430673c2e9 J 3.682.
- Night `fable_scout40w2_2026-11-19` is on job 2: `s40x__morph_v8` (9 evals, best 3.733 so far vs
  the control 3.402; the warm start is at 3.402 and the early samples are above it).

## 2026-11-19 - SCOUT40W2 preflight notes (local orchestrator)

- Focused preflight of the three resample_strict lanes (`scratch/preflight_scout40w2_2026-11-19.log`,
  exit 0, no hard faults):
  - `petal_hvlaw_v7`: 24/64 sampled refusals (37.5%, invalid_geometry), predicted 25 valid of 40 -
    the box/genotype, not the penalty, is the limiter; `resample_strict` keeps the budget valid but
    the lane may run slowly. Recorded; the run continues.
  - `crowe_x_osse_cd_v7`: `no_headroom` - the seed design hash EQUALS the prior best (the config seed
    was set to the lane best), so this run is a local continuation, not a new search; 18/64 refusals
    (invalid_envelope), expected hits 2.23. Recorded; the run continues as the owner-directed requeue.
  - `crowe_x_square_v7`: report section empty in the mixed-encoding log; the script exited 0 (no hard
    fault). Recorded as such.
- Night `fable_scout40w2_2026-11-19` running: `s40x__fold_warm` at 24 evals, best J 3.682 vs the
  SCOUT40 control 3.754 (+0.07 so far, sub-floor). Remaining jobs follow sequentially.

## 2026-11-19 - SCOUT40W2 follow-on night launched (8 tail watchdog lanes)

- The eight remaining SCOUT40 lanes stopped by the watchdog are requeued as
  `examples/typologies/scout40w2_2026-11-19/` + `docs/queue/fable_scout40w2_2026-11-19.yaml`, each with
  the measured fix and a warm start from its stopped run (same brief/objective; originals are the
  controls):
  - `fold_warm_v7`: `az_fold_h_deg` -15..0 -> **-15..+10** (kernel allows +/-40; families.py:128).
  - `morph_v8`: `morph_rate` 1..6 -> **0.5..6** (kernel >=0; Ath documents >=1).
  - `tritonia_v8` / `tritonia_v9`: `morph_width_mm` pinned at 590 = the 600 mm brief envelope ->
    **watchdog pin_ignore**, boxes unchanged.
  - `petal_hvlaw_v7`, `crowe_x_osse_cd_v7`, `crowe_x_square_v7`: refusal storms 41/33/31% ->
    **infeasible_penalty: resample_strict** + `error_policy: retry_same_then_stop` (the documented
    remedy; a widen would add illegal territory).
  - `rosse_rect_cd_v7`: `g_tmax` pinned at 1 = the bridge kernel max (tools/geometry/rosse_rect.py:68)
    -> **pin_ignore** on the command job.
- **Gates:** shape_check all eight pass (search configs 3085-5408/24000 dof; rosse 4737/24000 via the
  bridge CLI). The production warm start reads all seven search configs OK (mean = the stopped run's
  best, sigma = the config sigma0). The three resample_strict lanes get a focused preflight
  (`scratch/preflight_scout40w2_2026-11-19.log`, running; they start later).
- **Launched** `fable_scout40w2_2026-11-19` at 08:40Z / 05:40 local: controller pid 41892 (parent
  WmiPrvSE), 8 jobs x 40 valid, 1 h timeout each, GPU lane. First job `s40x__fold_warm` in
  `runs/20261119T134012Z-screen-50fbd8`. VRAM baseline 718 MiB, no stale host/lock before launch.
- The SCOUT40 evidence bundle is pushed and verified on the remote (`c2803ab`: 281 files, 48
  binaries incl. best-design meshes + responses).

## 2026-11-19 - SCOUT40 night complete; full evidence bundle pushed (local orchestrator)

- **Night `fable_scout40_2026-11-19` is DONE** (24/24 jobs, `QUEUE DONE` 05:02 local). Fourteen jobs
  were stopped by the runner's **watchdog** (exit 75) with partial results kept: five early requeues
  plus `s40w2` handled them; the later tail stops are: fold_warm_v7 (az_fold_h_deg high 0 -> a widen
  case, kernel allows +/-40), morph_v8 (morph_rate low 1 -> widen to 0.5), tritonia_v8/v9
  (morph_width high 590 -> brief-envelope limit -> pin_ignore), rosse_rect_cd_v7 (g_tmax high 1 ->
  kernel max -> pin_ignore), and three refusal storms (petal 41%, crowe_x osse 33%, crowe_x square
  31%) -> step/box fix (`resample_strict`), not a widen.
- **Evidence bundle: `docs/evidence/runs/scout40_2026-11-19/`** (24 runs, ~48.6 MB). Per run:
  `config.yaml` (seed + bounds), `run.json` (objective version, warm start, lib SHAs),
  `search.ndjson` + `scores.csv` (every eval's params, score `terms`, and the per-frequency
  `bw_h_deg`/`bw_v_deg` beamwidth, `di_db` directivity, ripple, on-axis, throat impedance arrays +
  scalars), `summary.json`, and the best design's `design.json` (geometry), `metrics.json`,
  `mesh_meta.json`, `mesh.msh`, `response.npz` (angular cut/balloon data). Plus the night yaml,
  queue log, summary, preflight and warm-start audit logs, and a README that states the schema and
  the comparability rules (J only within a brief/version; v10 is an offline rescore).
- **New tool:** `tools/analysis/archive_run.py` (reusable run->evidence packer; INDEX + CODE_MAP
  updated). `mesh.msh`/`response.npz` are force-added (gitignored under `runs/`).
- Headline results (v7 scores; see the bundle table for all): klangfilm b3_soft **2.800**
  (3.540 -> 2.841 -> 2.800), rolled pair **19.72 / 19.71** (terminal 225 vs 270 made no difference),
  fold_warm 3.754, ext_throat 3.565, morph 3.402, petal 4.892 (16 valid, refusals), tritonia v8
  5.325 / v9 5.289, rosse 4.560, crowe_x osse 5.345 / square 7.911.
- Open next: the follow-on requeue night for the eight later watchdog lanes (not yet queued), then
  the morning v10 rescore + B6 lane set. The GUI lane still has uncommitted working-tree files (not
  this lane's).

## 2026-11-19 - Requeues all closed: b3_soft 2.800; stage_a tie (local orchestrator)

- **`s40w2__klangfilm_b3_soft` (v2 continuation): best J 2.800** (41 evals, exit 0) from 2.841. The
  chain is **3.540 -> 2.841 -> 2.800**: 0.74 J below the original SCOUT40 control and slightly better
  than the historical 2.819 (100-eval) b3 run. The lane is the strongest SCOUT40 result so far and a
  B6 candidate; the block is its known construction gap (no returning lip), not the search.
- **`s40w__klangfilm_lame_hv_stage_a`: 8.350 vs 8.393** -> +0.043 (tie, sub-floor). The Phase A lane
  does not move on this brief; the two hard-floor pins (mid-gains at 0) are physics, not box.
- Requeue summary (all same v7-smooth briefs, originals as controls):
  b3_soft 2.841+2.800 (win); lecleach 8.036 (tie); iwata 6.671 (+0.09, tie); c200mouth 10.02 (tie);
  stage_a 8.350 (tie).
- Night now at 13/20: `s40__fold_warm_v7` running (warm start removed; seed = lane best), then
  ext_throat_v7, morph_v8, petal, tritonia v8, rosse_rect (command), crowe_x osse, tritonia v9,
  crowe_x square, rolled 225/270 pair.

## 2026-11-19 - c200mouth requeue closed; continuous-read notes (local orchestrator)

- **`s40w__klangfilm_hvcore_c200mouth`: best J 10.02** (43 evals, exit 0) vs 10.156 before -> +0.14 J,
  **below the 0.31 floor (tie)**. Widening only the binding H setback 0->30 removed the pin (no
  watchdog stop) but did not make the c200 mouth competitive. The core's own b3 seed (2.841 in this
  night) remains far better; the c200-mouth seeding is answered: not the lever.
- **Warm-start read note (prevents a false alarm):** a warm-started run's `n=0` row is the CONFIG SEED
  baseline (e.g. b3_soft n=0 hash 5819e3b98420 J 6.401), not the warm mean; the CMA mean starts at the
  prior best and the first samples are near it (b3_soft n=1 3.961 -> best 2.841). The warm record is
  written to run.json at the end. So judge a warm start by the early samples and the run.json record,
  not by n=0.
- `s40w__klangfilm_lame_hv_stage_a` running (11 evals at the time of writing, best 8.473; seed
  baseline 9.825, CMA mean = the prior 8.393). `s40w2__klangfilm_b3_soft` queued next after it.

## 2026-11-19 - Requeue results 1-3; b3_soft v2 continuation queued (local orchestrator)

- **`s40w__klangfilm_b3_soft`: best J 2.841** (34 evals) from the SCOUT40 control 3.540 -> a
  **0.70 J gain, above the 0.31 floor**. It was then stopped by the bound-pinned watchdog at the HIGH
  limit of `g_theta_h1_deg [36.5, 60]`; 60 is the KERNEL's hard ceiling (`_CORE_BOUNDS` theta_h1/v1
  5..60), so this is a pin_ignore case. Requeued as **`s40w2__klangfilm_b3_soft`** (position 12,
  `watchdog: {pin_ignore: [g_beak_v_projection_mm, g_theta_h1_deg, g_theta_v1_deg]}`), warm-started
  from the 2.841 best (mean hash 15a8c964d592, sigma 0.1), same smooth v7 brief; shape-check pass,
  warm start verified.
- **`s40w__lecleach_hv_smooth`: 8.036 vs 8.037** -> tie; the widened V floor (400) bought nothing
  (seed start, no warm start), so the lecleach lane is not promising on this brief.
- **`s40w__iwata_ar_smooth`: 6.671 vs 6.763** -> 0.09 J gain, below the 0.31 floor (tie).
- **`s40w__klangfilm_hvcore_c200mouth`** still running (24 evals, best 10.108, i.e. no gain from the
  H-setback widening so far); watch for a third pin at the 30 mm box or a stall.
- Night order: ... six originals, five s40w requeues, s40w2__klangfilm_b3_soft, s40__vt_v1, then the
  rest of the tail.

## 2026-11-19 - Requeue preflight closed; first requeue read (local orchestrator)

- Focused preflight of the two narrowed Klangfilm requeues (`scratch/preflight_scout40w_klangfilm_2026-11-19.log`,
  exit 0): b3_soft expected hits **5.53** (>3), 14/64 sampled refusals; c200mouth expected hits
  **23.08** (>3), 27/64 sampled refusals (uniform box, upper bound); both `ok` with `graded_inert`
  notes only. The earlier all-four-widening pass (31/64 and 20/64 refusals, hits 0.29 and 1.15) is why
  the boxes were narrowed to the binding key.
- **First requeue read:** `s40w__lecleach_hv_smooth` finished its 40 evals at **best J 8.186** vs the
  original's 8.037 (which stopped at 34 valid). The widened V floor (400) did not produce a gain; the
  requeue also starts from the seed (its warm start is unreadable), so this is a no-gain flag, not a
  controlled win/loss on the floor alone. The v10 rescore + the remaining requeues decide the lane.
- Remaining requeues in order: iwata (340 floor, warm start OK), b3_soft (pin_ignore, warm start OK),
  c200mouth (H setback 0-30, warm start OK), stage_a (pin_ignore, warm start OK).

## 2026-11-19 - Warm-start fix + requeue corrections (local orchestrator, owner-directed)

- **Production warm start could not read generated rows.** `families.resolve_path` only walks
  top-level keys / dotted paths, but grid rows store the adapter knobs at `params.grid.knobs`, so
  `mean_and_sigma` raised (refused) on every warm-started generated lane. Fixed in
  `hornlab_search/search/warmstart.py::_param_get` with a fallback that is only tried when the normal
  path raises (native/flat rows unchanged); test
  `test_generated_grid_rows_are_readable_by_the_warm_start`, focused suite 8/8.
- **Audit of every night config with the production path** (`scratch/warmstart_audit_2026-11-19.log`):
  now OK for iwata, b3_soft, c200mouth, stage_a, morph_v8, petal, tritonia v8/v9, crowe_x osse/square.
  Two still unreadable and fixed in the configs: **fold_warm_v7 and ext_throat_v7** point at
  `runs/study-*/{screen,verify}` whose `run.json` has NO config snapshot (study-level record), so the
  warm start refuses the objective/brief and then the searched knobs. Their `warm_start` blocks are
  removed; the seed_params are the lane bests (only the prior top-10 spread is lost).
- **Requeue corrections after the economy preflight** (the first pass was too aggressive):
  - `s40w__klangfilm_b3_soft`: beak boxes REVERTED to the b3 seed's box (H 0-10, V 0-5, diag -5..5,
    start 0.85-0.99). Widening all four to the kernel ranges sampled 31/64 illegal designs; the stop
    was the hard-floor pin, so the night job's `pin_ignore` is the whole fix.
  - `s40w__klangfilm_hvcore_c200mouth`: widen ONLY the binding H setback (0-10 -> 0-30); the other three
    boxes stay at the seed's (all-four widening sampled 20/64 illegal designs). 6/6 of its first run's
    top designs sat at 10, so this is the attributable treatment.
  - `s40w__lecleach_hv_smooth`: NO warm start (the prior rows lack the searched `g_stop_a2`; they store
    `g_stop_cos2k` instead), seed start; the V-floor widening to 400 stays.
  - `s40w__iwata_ar_smooth`, `s40w__klangfilm_lame_hv_stage_a`: warm starts kept (now readable);
    stage_a is pin_ignore-only (hard floor at 0).
- All five requeues re-shape-checked: pass (same mouths/dofs as reported). A focused preflight of the
  two narrowed Klangfilm configs runs detached (`scratch/preflight_scout40w_klangfilm_2026-11-19.log`).
- Night is live on `s40__vt_v1`; the requeues start at the next job boundary (positions 7-11).

## 2026-11-19 - Five bound-pinned lanes requeued with widened boxes (local orchestrator, owner-directed)

- **Exit 75 = `WATCHDOG_EXIT`**, not a crash: the runner stops a search whose box is the limiter and
  keeps the partial results. Five SCOUT40 lanes were **bound-pinned** (the sixth, crowe_v2a, exited 0 at
  its budget). The five are requeued as `s40w__*`, inserted at night positions 7-11 in the LIVE file
  (`runs/nights/fable_scout40_2026-11-19.yaml`) and the tracked copy (`docs/queue/...`), 23 jobs total,
  dry-run clean. Same brief/objective (v7 smooth) as the originals so J stays comparable; the originals
  are the controls; every requeue warm-starts from its lane's box-limited best (top 10,
  `sigma_from_spread: false` so the widened region is sampled at the config sigma0).
- **Widening basis (measured, not guessed):**
  - `s40w__lecleach_hv_smooth`: `g_fc_v_hz` 450 -> **400**. Shape-check sweep
    (`scratch/sweep_widen_2026-11-19/shape_check.log`): 400 Hz -> V mouth 471 mm (fits the 480
    envelope), 380 Hz -> 495 mm (OVER). 400 is the last feasible step; the family's H box already
    allows 300.
  - `s40w__iwata_ar_smooth`: `g_fc_hz` 420 -> **340**. Sweep: 340 Hz -> 524 x 449 mm (31 mm margin),
    320 Hz -> 476 mm (mesh edge), 300 Hz -> 507 mm OVER. The R19 space card had raised 300 -> 420
    because the edge was mostly refused, so 340 keeps headroom rather than re-opening that slice.
  - `s40w__klangfilm_b3_soft`: beak boxes widened to the kernel ranges (H setback 0-60, V projection
    0-45, diagonal -20..20, start 0.50-0.99; `_klangfilm_lame_hv_core_v1.py:79`) + night-job
    `watchdog: {pin_ignore: [g_beak_v_projection_mm]}` because 0 is the hard floor (the watchdog's
    "widen the box" cannot apply below a legal minimum).
  - `s40w__klangfilm_hvcore_c200mouth`: the 0-10 mm beak-setback box was our copy of b3_soft's box,
    not a physical limit (6/6 of its top designs sat at 10). All four beak boxes widened to the kernel
    ranges; the 585 x 255 mm c200-mouth seed and the beak-only search are unchanged.
  - `s40w__klangfilm_lame_hv_stage_a`: bound-pinned at the hard floor `g_h_mid_gain_mm` 0 (negative
    mid-gain is refused; contract s5 "lawful box positive-only"). Night-job
    `watchdog: {pin_ignore: [g_h_mid_gain_mm, g_v_mid_gain_mm]}`; theta boxes unchanged.
- **Gates:** shape_check all five pass (lecleach 2553/24000 dof, 553x364x242; iwata 1746/24000,
  390x334x239; b3_soft 3102/24000, 473x266x344; c200mouth 3907/24000, 585x255x408; stage_a
  7453/24000, 541x261x234). Economy preflight (`--from-runs <lane run> --samples 64`) runs detached
  for the four widened configs (`scratch/preflight_scout40w_2026-11-19.log`); stage_a has no new region
  (pin-only change), so its check is the shape check + the prior run.
- `s40__vt_v1` started at 01:05:14 (before the insert), so the requeues begin at the next job boundary.
- Standing rule: any further exit-75 in this night gets the same treatment (widen within the documented
  range, or pin_ignore at a hard limit) and a new job id.

## 2026-11-19 - Correction: the SCOUT40 watchdog stops are BOX limits, not failures (local orchestrator)

- **Exit 75 is `WATCHDOG_EXIT`** (`tools/run_campaign_night.py:118`), the runner's designed stop for a
  search that is not going anywhere (owner rule 2026-11-16, rules at `:96-118`, verdict at
  `:175-221`). Partial results stay in the run dir; status `watchdog`. Four finished jobs are all
  **bound-pinned** (>=3 of the top 6 within 3% of a searched box limit), none stalled or refused:
  - `s40__klangfilm_hvcore_c200mouth`: 6/6 of the top 6 at the HIGH limit of
    `g_beak_h_setback_mm [0, 10]`. **CORRECTION to the previous entry:** the flat 10.156 is box-limited,
    not a proven bad basin — the kernel's documented beak range is 0..60 mm, and we copied b3_soft's
    0..10 box. Requeue with the beak box widened before judging the c200 mouth.
  - `s40__klangfilm_b3_soft`: 3/6 at the LOW limit of `g_beak_v_projection_mm [0, 5]`; 0 is the
    kernel's hard floor, so this is the `watchdog: pin_ignore` case, not a widen-the-box case.
  - `s40__lecleach_hv_smooth`: 3/6 at the LOW limit of `g_fc_v_hz [450, 1000]` — widen the box.
  - `s40__iwata_ar_smooth`: 3/6 at the LOW limit of `g_fc_hz [420, 900]` — widen the box.
- `s40__crowe_v2a_c1` finished normally (exit 0, budget 40, best 4.879, 29 min, 42.3 s/candidate).
- Night 5/18 by 01:00: 5 done, `stage_a` running, 12 pending. Actions for the morning pass: widen the
  three boxes above, add `pin_ignore` for the hard-limit pin, requeue the affected lanes (new job ids),
  then run the v10 rescore on the new rows.

## 2026-11-19 - SCOUT40 preflight result + first lanes (local orchestrator)

- **Preflight `--samples 64` complete over the 20 scout40 + vt_v1 configs: 1 HARD, and it is the
  expected one.** `scout40__rosse_rect_cd_v7` (`DesignSpace.from_config` refuses the bridge rows type
  `rosse_rect`); the night runs it as a `kind: command` job via `tools/geometry/rosse_rect_cli.py`,
  whose shape-check passed (4737/24000 dof). No other hard faults.
- **WARNs (small sampled refusal fractions, box upper bound):** lecleach_hv_smooth 5/64
  invalid_geometry, iwata_ar_smooth 1/64, morph_v8 3/64 + `graded_inert`, tritonia_v8 2/64 +
  `graded_inert`, rf_section_axial_home_v7 1/64 (that job is no longer queued). Predicted valid evals
  38-39/40. `graded_inert`: the sampled refusals are post-mesh/geometry, so `infeasible_penalty:
  graded` is inert (only pre-mesh estimates are graded) -- `resample_strict` + `budget_counts: valid`
  would replace them; not changed mid-night.
- **History checks not run:** `--from-runs` was not passed (the handoff command omitted it), so
  seed-headroom/spread/expected-hits are informational only; warm starts come from the lane bests per
  the night plan. A `--from-runs` pass remains a morning option.
- **Finished lanes by 00:50 (v7 scores; not comparable across briefs):** crowe_v2a_c1 4.879 (29 min);
  lecleach_hv_smooth 8.037; iwata_ar_smooth 6.763; klangfilm_b3_soft **3.540** (65 valid, 12 searched
  keys); `klangfilm_hvcore_c200mouth` **seed 10.258 -> best 10.156** (30 evals, beak-only, flat).
  The c200-mouth core seed is ~4 J worse than the b3 core seed on the same smooth brief; consistent
  with the BEM finding that widening the mouth 472->595 mm did not widen H (the parent's H comes with
  the rolled lip). Scout-grade comparison (30 vs 65 evals, 4 vs 12 keys), not a controlled A/B.
- Night 5/17 at 00:50; Phase A `stage_a` running (19 evals). Preflight log:
  `scratch/preflight_scout40_2026-11-19.log`.

## 2026-11-19 - resolve_warm_runs: study-layout fix (local orchestrator, CPU)

- `tools/night_queue/resolve_warm_runs.py` now finds `runs/<study>/<screen|verify>/designs/<hash>` and
  writes the full `runs/<study>/<mode>` relative path (before: the one-level glob missed the study
  layout, and the substitution emitted `runs/verify`, losing the study dir). Selection is newest by
  run-dir mtime with a path tiebreak. Regression test
  `test_study_layout_screen_and_verify_resolve`; focused suite 3/3 pass. Safe during the live night
  (the runner does not use this tool; the SCOUT40 configs are already hand-resolved).

## 2026-11-19 23:35 - SCOUT40 night LAUNCHED (local orchestrator)

- Launched detached able_scout40_2026-11-19 (18 jobs) at 23:35 local / 04:35Z: controller pid **16596**
  (parent WmiPrvSE), log 
uns/nights/queue_scout40.log, GPU lock held.
- **GPU hygiene:** gpu-clean before launch: no project Julia/BEAT processes; VRAM baseline **1328 MiB**;
  no live \
uns/.gpu.lock\. First job \s40__crowe_v2a_c1\ running in \
uns/20261119T043506Z-screen-54878f\
  (3 valid rows by +2.5 min, J 8.602, VRAM 1286 MiB).
- **Cutoff limitation (recorded):** \queue.ps1 -Cutoff\ is HH:mm **today** and only gates STARTING later
  nights; it cannot express tomorrow 13:33, and the runner has only per-job timeouts (1 h), no wall-clock cap.
  The 18-job night therefore runs to its job list (estimate 6-12 h; stop cleanly with a \STOP\ file in
  \
uns/nights/fable_scout40_2026-11-19/\ if needed). The \-Cutoff 23:59\ arg is a no-op for a single night.
- Preflight \--samples 64\ runs detached (CPU lane) and is advisory; results recorded when it finishes.
- First launch attempt with \-Cutoff 13:33\ refused (parse = today, already past) — recorded so the next
  cross-midnight launch does not repeat it.
## 2026-11-19 - Owner-directed construction fixes for the SCOUT40 night (local orchestrator)

- **Klangfilm: the parent/record lane is out, the Phase B H/V core is in.** New
  `scout40__klangfilm_hvcore_c200mouth` (`klangfilm_lame_hv_core`, blend 1) seeded to the c200 record
  mouth **585.000 x 255.000 mm INNER** (theta_h1 54.4980605893 / theta_v1 24.1725588357 solved
  against the frozen kernel from the b4 seed), with the four beak keys searched. Offline check
  (`scratch/verify_construction_2026-11-19.py`): theta_h 7.000->54.498, theta_v 6.000->24.173,
  **0 angle inflections on both axes**, radii strictly increasing, axial 400 mm. This is the
  construction that cannot pinch or S-curve (monotone Q law, `_klangfilm_lame_hv_core_v1.py:120-125`).
  shape_check: ok, 3907/24000 dof, mouth 585 x 255, depth 408, envelope fits.
- **Rolled: section lane replaced by a whole-shape rect PAIR.** The section kind has no
  `terminal_deg` (`_crowe_section_v2.py:16`); the rect kind does (gate 180 < t <= 280,
  `_rolled_rect_v1.py:50-51`). New `scout40__rf_rect_axial_cap225` (terminal 225, depth_h_ratio
  opened 0.68-1.05, seed 1.0) + `scout40__rf_rect_axial_control270` (same, terminal 270) so the cap
  is attributable. Offline: at the old fixed 0.68 the H wall has **2 inflections**; at 1.0 it has
  **0** (the shoulder is the depth split, and it disappears). Effective wall turn 222.6 vs 267.9 deg;
  lip return 33.6% vs 35.8% of depth. shape_check: both ok (3554 and 5142 / 6000 dof).
- **Research basis (reused; no new dossier needed for a bounds/seed tweak):** the owner's "no gain
  past 180 deg" is NOT in the repo sources. The sources warn 160-200 deg traps a lambda/4 cavity
  (~4.3 kHz) and favour 220-280 deg / 270 (BIRADIAL_CROWE_SOURCES_2026-11-15:150-157, :218;
  HORN_WHITEPAPERS_2026-11-15:136; imported KB :453 [X] measured-superior 270, optimum not
  established). The implemented cap is therefore **225** (top of the owner's 200-225 band, outside
  the warned band) with the 270 control; literal 180-200 is flagged, not implemented.
- **No rolled "record-beak" variant exists** (verified: no record/beak keys in the rolled family);
  the S-curve-inheriting lane dropped is the rolled **section** lane (replaced by the rect pair).
  The Klangfilm record lane is the c200w parent (swapped, per the prior owner message).
- **ext_throat_v8 dropped** (shape_check refusal: throat 42.1 x 42.1 vs 36.0 mm exit mismatch);
  bounds not widened. `ext_throat_v7`/`fold_warm_v7` `from_runs` resolved by hand to
  `runs/study-4e1a6a9cd4bb5201/verify` and `runs/study-0c9805ad97208a2e/screen` (the resolver's
  one-level glob does not see `runs/study-*/{screen,verify}/designs`; `2.82`-family evidence:
  b3_soft run `20261117T071329Z-screen-e4f90d` J 2.8192 vs parent c200 run `20261117T091346Z-screen-517217`
  J 7.4458, same v7-smooth brief but NOT a same-mouth controlled A/B).
- Night now 18 jobs (dry-run exit 0, all listed); preflight `--samples 64` running detached.
- **Open construction decision:** KL-HV-B still has **no returning/curled lip** (contract
  `klangfilm_lame_hv.md:118,123`; BEM: B3 DI win but 65.2 deg H coverage vs >=70, and widening the
  mouth did not widen H). A returning-lip module (section-normal spine) is the contract's recommended
  next step and is owner-gated (digest change); NOT implemented in this pass.
## 2026-11-19 - feat/woofer-system-v0 integrated into hornfab-all-2026-11-18 (horn + woofer GUI, P0)

- Merged `feat/woofer-system-v0` (worktree `C:/Users/hunte/Hrns/hornlab-woofer-system-wt`, tip `d7453a1`)
  into `hornfab-all-2026-11-18` (base `3a3a4ee`): the whole `hornlab_search/system/` package (contracts,
  provenance, screen, DSP, combine, BL adapters), `tools/system/*`, driver YAMLs, 30 system test files,
  the R16 clearance gate, and GUI G0 (`gui/data_hw.py`, `gui/static/hw.js`, `hw` dispatch in
  `gui/server.py`, `readiness.yaml`) plus the system_woofer research docs. Conflicts resolved additively:
  `server.py` (keep `_inflight` single-flight GETs from `143ff08` AND `system_store`/`--system-store`),
  `NOTES_FOR_SENIOR.md` (both append-only blocks kept). Owner gate A: the foreign GUI edits had been
  committed by the other lane as `143ff08` ("Should be good now").
- Pre-merge baseline on hornfab-all (tests/test_gui*.py + test_b8_lanes_bounded_gui.py): 574 tests,
  1 failure (`test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`,
  PRE-EXISTING), 0 errors, 0 skips (junit `hw_base_canonical_premerge.xml`).
- INDEX/CODE_MAP: 13 research rows for `docs/research/system_woofer_2026-11-18/`, 3 CODE_MAP rows
  (`system/`, `system/boundarylab/`, `gui/data_hw.py`+`hw.js`).
- GUI runs from the canonical checkout with `--system-store C:/Users/hunte/Hrns/hornlab-woofer-system-wt/system_runs`
  (the store is gitignored and holds absolute worktree paths; never copy or move it).
- Post-merge baseline (same command): 862 tests, 1 failure (`test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`,
  PRE-EXISTING, same as the pre-merge baseline), 0 errors, 7 env-gated real-BL skips
  (junit `hw_p0_baseline.xml`). The worktree's 2 `test_gui_preview_shape` failures do not exist on
  hornfab-all; they were base-version artifacts, not G0-caused.
- Environment: `hornlab-search/system_runs` is a Windows directory junction to the worktree store
  (`New-Item -ItemType Junction`), because `motor_map.SEED_PATH` and the clearance replay tests
  hardcode `<repo>/system_runs`. Single physical store; removing the junction leaves the data intact.
- `#/hw/cases` verified live in the canonical checkout (HTTP 200, 38 cases) with the §9 command.

## 2026-11-18 - Run artifacts archived to docs/evidence/runs (owner request)

- Owner asked that three run dirs be committed/pushed with geometry + scores. `runs/` is gitignored,
  so per the established `docs/evidence/runs/<run-id>/` convention each run got: best.json, config.yaml,
  run.json, search.ndjson, cma/*, per-design `designs/<hash>/design.json` (geometry params) and
  `metrics.json` (scores), the **best design's mesh.msh**, and a new `scores.csv` (per-eval: params,
  objective terms, dof/timing, plus the full per-frequency response columns — freqs_hz, bw_h_deg,
  bw_v_deg, di_db, on_axis_db, ripple_h_db, ripple_v_db, z_throat_real, metric_* scalars; built
  from search.ndjson):
  - `20261117T085651Z-screen-f30bd2` hl__klangfilm_lame_curved_v1 — best b5f460f0313f J 8.4289
    (104 evals; 75 with metrics; 29 mesh refusals).
  - `20261117T091346Z-screen-517217` hl__klangfilm_lame_curved_v1_c200 — best 88973b1e44e9 J 7.4458
    (201 evals, 200 metrics). This is the c200 best that SCOUT40 job 5 warm-starts from.
  - `20261117T190640Z-screen-643de7` home_range_pilot_rolled_control_h12 — best 445dafb7e760
    J 92.61 (15/15 evals; rolled_family_rect_v1 control pilot, brief home_range_v9_h12).
- Not archived: per-design mesh.msh/response.npz except the best design's mesh (large generated
  artifacts; every mesh is reproducible from its committed design.json).
- Follow-up: `*.msh` is globally gitignored, so the three best-design meshes were force-added
  (`git add -f`) in a second commit; per-design response.npz stays local-only.

## 2026-11-19 - PR #74 merged into hornfab-all-2026-11-18 (local orchestrator, R21)

- Merged `claude/adoring-ramanujan-1m4b3g` @ 37da1ee into `hornfab-all-2026-11-18` (merge commit
  `4e27afd`, clean, strict descendant of bc22d6c). Contents: senior verdicts (rho20 borderline park
  stands; v7 stored-J tie floor re-pinned 0.31 / combined 0.3105; steer planes confirmed), u3_authority
  se_deg+grade, WP 4.4 record_body g_vt_mm + g_vt_hold (seed = host, host V mouth 386.7 mm, bounds
  320-465 / 0-0.5), continuation_advice.py, night_queue/resolve_warm_runs.py, Le Cleac'h H/V
  "published" -> "reconstruction" relabel, SCOUT40 night (18 jobs) + configs, B6 night DEFERRED.
- Tests local (cloud container lacked cma/hornlab_mesher): offline batch 72/72 pass
  (test_queue_fable_scout40, test_queue_fable_vt_b6, test_night_queue_resolve_warm_runs,
  test_design_record_body_vt, test_tools_analysis_continuation_advice, test_tools_analysis_u3_authority,
  test_design_generators_lecleach_hv, test_design_generators_lecleach, test_wp09_d9_provenance);
  mesher-gated batch pass exit 0 (test_design_generated, test_geometry_record, test_geometry_edits,
  test_tools_analysis_u3_jobs, all 8 test_design_generators_grid*).
- Next: SCOUT40 preflight (resolve_warm_runs, shape_check, search_preflight, dry-run) then GPU launch
  with a 14 h cutoff; B6 stays deferred until SCOUT40 results.

## 2026-11-19 - SCOUT40 owner edits: smooth group first, +2 Klangfilm-Lame, morph v7 / twinray v8 out (cloud Fable senior)

- Night `docs/queue/fable_scout40_2026-11-19.yaml` now 18 jobs: 1-6 SMOOTH brief (Crowe V2A c1, Le Cleac'h H/V,
  Iwata-AR smooth, Klangfilm b3_soft, **Klangfilm-Lame parent c200w** (seed = c200 best J 7.446),
  **Klangfilm-Lame H/V Phase A stage_a_search** (4 knobs)); 7 vt_v1; 8-17 home v7 warm-started lanes; 18 tail.
  Removed: osse_rrect_morph_v7, ath_twinray380_v8 (owner).
- Rejected as Lame candidates: Phase B b2_wide / b4_wide_h (0 searched dims: geometry diagnostics; the runner
  refuses them); hl__klangfilm_lame_curved_v1 base (legacy bridge rows type `klangfilm_lame`).
- Tests: night guard + all session suites pass offline (see PR #74).

## 2026-11-19 - SCOUT40 night written (owner: budget ~40, more typologies, <= 14 h); B6 deferred

- **Night** `docs/queue/fable_scout40_2026-11-19.yaml` (18 jobs, dry-run clean, 1 h timeout each, est. 6-12 h):
  vt_v1; 12 home-v7 lanes warm-started from each lane's own best (top 10, sigma from spread; run dirs from
  the v10 rescore `lane_best`): fold_warm v7, morph v7/v8, ext_throat v7/v8, twinray380 v8, ATH CORE petal
  (R19 sigma 0.05), Tritonia v8/v9, R-OSSE rect CD (bridge CLI command job), Crowe-X OSSE CD and Crowe-X
  square (R19 no_headroom -> warm start); smooth-brief group from seed: Crowe V2A c1, Le Cleac'h H/V,
  Iwata-AR smooth (R19), Klangfilm b3_soft; tail rf section-axial (R19).
- Configs `examples/typologies/scout40_2026-11-19/` (17). Offline load check passed for 13; 4 need the owner box
  (mesher / runs/). New `tools/night_queue/resolve_warm_runs.py` fills the 2 `@design:` warm starts
  (fold_warm, ext_throat v7: the rescore lost their run names) and checks every warm-start dir; tests 2/2;
  night guard test 1/1.
- Found: `rosse_rect` is a bridge rows type (only via `tools/geometry/rosse_rect_cli.py`); plain `search`
  refuses it ("unknown rows type"), so it runs as a command job.
- B6 night (`fable_vt_b6_2026-11-19`) kept but deferred: SCOUT40 picks which lanes earn the 120-eval matched rerun.

## 2026-11-19 - Night plan for the new freedom + B6 written (not launched; cloud Fable senior)

- **Night file** `docs/queue/fable_vt_b6_2026-11-19.yaml` (9 jobs, dry-run parses): 1) vt_v1 probe
  (80 evals, v7, from the exact host); 2-7) **B6 / WP 6.2** matched reruns of the three v10 leaders
  that tie inside one floor (ext_throat_hvlaw_v7, osse_rrect_fold_warm_v7, osse_rrect_morph_v7):
  120 VALID evals, v10 brief, seeds 61901/61902, s1 for all before any s2; 8-9) twinray380 v8 tail.
- **Configs** `examples/typologies/b6_2026-11-19/` (8): R19 `__space_v1` applied for ext_throat
  (sigma0 0.10) and fold_warm (a0 fix); R20b `record_gate: shadow` on ext_throat; v10 brief replaces
  target/weights (all load as objective 10). Guard test `tests/test_queue_fable_vt_b6.py`.
- Estimate [inferred, skill table: 10-30 s/eval for 2-7k dof quarter models]: vt ~0.5-1 h; each B6 arm
  ~0.5-1.5 h incl. refusals -> 6-10 h for jobs 1-7. Owner box: shape_check + search_preflight, then launch.

## 2026-11-19 - vt floor 320 (owner); typology correctness review (cloud Fable senior)

- **Owner: vt bounds now 320-465 mm** (floor raised from 275 to limit the pinched lip). `vt_v1.yaml` +
  test updated; 10/10 pass.
- **Typology review** (`docs/research/typologies/TYPOLOGY_CORRECTNESS_REVIEW_2026-11-19.md`, 45 entries):
  no wrong published formula in code; every research correction is coded and test-pinned. Grade A
  (published numeric test): JMLC march, Keele BR sizing, ATH CORE, Tritonia, twin-ray, JMLC350,
  R-OSSE (ST260 STL refit 0.08 mm). Fixed: Le Cleac'h H/V pair mislabelled "published" ->
  "reconstruction" (metadata only; seed hash 7fb9d2951deb unchanged); lecleach card + WP9 dossier
  half-angle notes. Keele rule and CD scoring: not imposed across typologies [code-verified].
- Open (owner/other lanes): close lecleach R9 gate (Fourcade test passes); Klangfilm workbook
  fixture; ICW/FREEFORM cards; dead `lecleach_mod`/`lecleach_ar` kinds.

## 2026-11-19 - WP 4.4 vt route built (owner bounds 275-465); D8 continuation tool; doc re-pins (cloud Fable senior)

- **Owner decision (2026-11-19): vt bounds 275-465 mm.** Built as a searched route on the explicit
  record body: `record_body` takes knobs `g_vt_mm` (V-axis mouth height) + `g_vt_hold` (early V-wall
  hold, 0 = none). Seed (386.73, 0) reproduces the U3 control **exactly** (max diff 6e-14);
  `validate_search_config` refuses bounds that exclude the host (old [440, 465] now refused).
  Config `examples/studies/u3_biradial_es_style_v7/vt_v1.yaml` (budget 80; loads; GeneratedSpace builds).
- **Corrections from the real host record:** best biradial V mouth = **386.7 mm** (350 was the seed).
  Below ~350 the V axis drops faster than the shoulders: g_vt_mm 275 -> overall mouth 324 mm (pinched
  lip). Top: 470 fits the 480 envelope incl. 3 mm wall, 475 fails; 465 keeps 9 mm.
  The single-knob vt_460 edit (hold 0.5) cannot reproduce the control (33 mm RMS at h=350), hence 2 knobs.
- **D8 / WP 7.2 advisory:** `tools/analysis/continuation_advice.py` (last-100 gain vs identity floor
  v7 0.3105 / v10 0.4677 / slope5 0.4863; "no floor" otherwise). Tests 3/3.
- **Docs:** v10 README floor note resolved to 0.31; plan §10.2 A_r15/A_r20 rows written (verified /
  borderline); `classify_recipes` legacy detail now "digest-unverified".
- Tests: `test_design_record_body_vt.py` 10/10, continuation 3/3; design/geometry/u3 suites: the only 3
  failures are pre-existing container gaps (no `cma`, no `hornlab_mesher`), identical before/after.
- **Needs the owner box:** `shape_check` + dof cap on vt_v1 (mesher), then the budget-80 probe.

## 2026-11-19 - Senior verdicts §2.3 + §2.4 complete; u3_authority gains SE + grade (cloud Fable senior)

- **§2.3:** accept mixed_identity fix, B1 sd(dJ) (note: all 8 dJ negative, use RMS ~0.015 J for
  absolute J), 0.0057 threshold, 166-sample (needs one brief-YAML diff on the owner box), ST260
  STL basis. **Amend** legacy `rebuildable` (digest-unverified; 20-record rebuild sample before any
  legacy finalist). **Overrule** vt bounds: [350, 465] (the control is 350 mm; [440, 465] boxes
  the search around the +2.30 J point).
- **§2.4:** steer_early/late = ("h","v") confirmed; inert only at this 1.3-1.5 mm edit on this host.
- **Code:** `tools/analysis/u3_authority.py` adds `se_deg` + `grade` (authority/borderline); the
  predeclared `authority` flag is unchanged. Tests 5/5 (`tests/test_tools_analysis_u3_authority.py`).
- All four senior items of HANDBACK_LOCAL_2026-11-18 §2 are now answered in
  `scratch/fable_architecture/SENIOR_VERDICTS_2026-11-19.md`.

## 2026-11-19 - Senior verdicts on handback §2.1 (rho20) and §2.2 (v7 floor) (cloud Fable senior)

- **Verdict file:** `scratch/fable_architecture/SENIOR_VERDICTS_2026-11-19.md` (CPU, committed data only).
- **§2.1 rho20: park stands.** v8 -> A_r20 meets the U3 3 deg rule by 0.12 deg (H 2.5-5.5 kHz +3.12,
  SE 0.44 over 6 freqs, no mesh floor, dJ +0.024 tie). rho's own swing r15 -> r20 is 1.28 deg H:
  the rho knob is inert. §10.2 rows to write: A_r15 no authority; A_r20 *borderline*. U3 keeps 3 deg
  and adds a grade: authority needs (move - 3) >= 1 SE, else borderline (changes no decision alone).
- **§2.2 v7 floor: re-pin to 0.31 J (combined 0.3105) for stored-J tie calls.** 0.13 is A4's
  dense-232-J sampling residual (no grid-weighting shift); every critical-path J is stored-grid J.
  Effects: fold_warm v7 (dJ 0.20-0.25) becomes a tie with the throat cluster (already in B6);
  WP 4.4 vt success test becomes > 0.3105 J; D8 continuation rule uses 0.31 for v7.
- Not reviewed yet: handback §2.3 judgment calls, §2.4 steer_early/late planes.

## 2026-11-18 - WP 4.3 complete (5/5) -> B2 authority table; vt V-freedom has 3x-threshold authority; WP 4.4 proposal written (local orchestrator)

- **WP 4.3: five tool-valid variants solved at verify tier in ~4 min** (night fable_wp43_2026-11-18,
  5/5 exit 0, ~44 s per solve). **B2 authority table published**
  (`docs/evidence/wp43_b2_authority/README.md` + authority.json + CSV sets): **vt_460 has REAL
  V-plane authority — +32.32 deg in 1100-2500 Hz with H secondary (−5.1 deg < half)** at a cost of
  +2.30 J at that fixed shape (authority ≠ a better design; the search would decide how to spend
  it). term_topbottom / steer_early / steer_late / diag_pull are INERT in this envelope (max moves
  1.55-2.66 deg < 3 deg). vt_480 and term_sides were excluded pre-solve by the u3_jobs validity
  table (invalid reach) — an owner-approved dedicated probe could still measure them.
- **WP 4.4 proposal recorded** (senior + owner gated): open the V terminal-width freedom as a
  searched knob (`hl__biradial_es_style_v7__vt_v1`, bounds ~[440, 465], shape_check first, then a
  budget-80 CMA probe on the v7 brief; success = beat the control by > the v7 combined floor
  0.1302 J). NOT implemented — new config version per the never-retrofit rule.
- Everything is on `hornfab-all-2026-11-18`/`main`; the cloud-alignment handoff is in the chat
  transcript (2026-11-18 evening) and the pointers live in ACTIVE_STATE + HANDOFF.

## 2026-11-18 - B1 batch 1 + 2 COMPLETE; WP 2.3 floor record; WP 4.2 PASS; queue trimmed to Fable-only; WP 4.3 launched (local orchestrator)

- **B1 complete: 8/8 probes exit 0** (5 fold-warm + 3 ext-throat), no Shared-Usage spill anywhere
  (host shared 80 MiB constant; peaks ~2.6-3.0 GB dedicated). dJ range −0.003…−0.0252,
  6/8 mesh-sensitive at the 0.0057 threshold. Published: `docs/evidence/b1_mesh_2026-11-18/`
  (README + b1_probes_table.json + floor_record.json). **WP 2.3 combined floor: mesh part
  sd(dJ) = 0.00768 J → combined = sqrt(freq²+mesh²): v7 0.1302 (published-D8 basis) / 0.3105
  (protocol basis) / v10 0.4677 / v10_slope5 0.4863 — the floor stays frequency-dominated; the
  v7 0.310-vs-0.13 tension stands unchanged.** The two leaders (3a1038/9fcd21) remain outside the
  mesh floor (infeasible at epw 12) [recorded, unchanged].
- **WP 4.2 PASS** [measured]: record-route control (verify solve of the U3 biradial control,
  `20261118T235528Z-verify-72cdcc`, design `f07cbf168091`, J 6.4994) vs the stored normal-route
  host (`37b115/9b05b8756526`): band deltas |dh| ≤ 0.19°, |dv| ≤ 0.76° — ALL within the predeclared
  1° bound (`docs/evidence/wp42_u3_biradial/equivalence.json` + hv_beamwidth CSVs). The record
  route is VALID on the biradial host (R8 condition); no silent host switch needed.
- **Ext-throat w1 lane continuation finished** (resume2, exit 75 = budget end): best J 5.7239
  (`104ea26b21ca`, 135 rows total). Rows/reports stay in the run dir for the lane owner.
- **Owner directive executed (2026-11-18 ~19:00): the night queue was trimmed to Fable-plan work
  only.** Removed pending blocks: 4 w-lane continuation searches (rosse_rect r120/r50-refine,
  lecleach_iwata_ar, control_v7), both atlas BO arms (`t_atlas_*_turbo300` — BoTorch-vs-CMA
  experiment PAUSED by the owner until a lane's CMA cohort + explicit approval; roots untouched),
  and the 2 re-added `_r2` copies of the killed w_* jobs (klangfilm/ath_core14: nothing lost —
  both had 0-1 evals). Backups: `cd_rrect_2026-11-17.yaml.bak-20261119-fable-trim`. The previous
  night printed QUEUE DONE; its jobs: see the ledger. **WP 0.7 hardening shipped**:
  `run_campaign_night.build_job_env` defaults `PYTHONUNBUFFERED=1` (silent-exit class),
  `prepare_study` builders-loop guard names the failed step + traceback (klame class),
  `run_bo_arm` echoes the child tail on nonzero rc; `test_night_bo_arm_wrapper` rewritten to mock
  the real Popen streaming surface (the two order-dependent failures were tests mocking
  call/run only — they passed when a sibling leaked a Popen stub); focused suites 55/55 green.
  NOTE: the env fix applies from the NEXT runner start (the live runner had the old module loaded).
- **WP 4.3 launched as its own night** (`fable_wp43_2026-11-18`, detached via queue.ps1, cutoff
  23:59): the FIVE tool-valid variants at verify tier (`vt_460`, `term_topbottom`, `steer_early`,
  `steer_late`, `diag_pull`) — `vt_480` and `term_sides` are EXCLUDED by the u3_jobs validity
  table (invalid reach), recorded here; ~44 s per solve observed on the first two.

## 2026-11-18 - B1 batch 1 COMPLETE (5/5 exit 0, no spill); batch 2 + WP 4.2 queued (local orchestrator)

- **B1 batch 1 ran clean after the backend-object fix**: all five fold-warm x2 probes exit 0,
  ~3.5-4 min each (refined solve + memwatch + verified teardown), GPU peaks ~2.6 GB dedicated,
  **no Shared-Usage spill on any probe** → the R5 batch-2 gate is MET. First datum:
  `2f7307c06023` ref J 4.14130 → refined J 4.12597 (dJ −0.01533 > the 0.0057 threshold →
  **mesh-sensitive**), 28,489 tri / 14,519 dof. Full per-design records accumulate in
  `runs/b1_mesh_2026-11-18/` (+ memwatch JSONs per probe under runs/nights/b1_mesh_2026-11-18/).
  B1 evidence document + combined floor record (WP 2.3): next commit batch once batch 2 lands.
- **Queued behind the probes** (gate-satisfied per R5/R6, dry-run exit 0):
  3 × ext-throat x2 probes (`b1_mesh_*_20261118_batch2`, from the cloud-verified insert file) and
  the **WP 4.2 biradial-control verify solve** (`wp42_biradial_control_verify_20261118`,
  `--mode verify` on the U3 control — kind: command per the single-design rule).
- Live now: `w_ext_throat_hvlaw_cov_v7_200w1_resume2` with `budget: 200`
  (strict-resume cumulative cap — accepted; 92 rows preserved, ~108 new evals to run).

## 2026-11-18 - owner-directed queue jump: B1 probes to the front; two tool faults fixed on the way (local orchestrator)

- **Owner asked for B1 at the front of the live night.** Executed with the runner's own mechanics:
  PAUSE -> reorder night file -> stop the in-flight search(es) -> corrections -> unpause. Backups:
  `cd_rrect_2026-11-17.yaml.bak-20261118-b1front`, `.bak-20261118-b1rc2`. Stopped: w_ext_throat
  partial at **92/200 rows** (kept; resume2 queued with `budget: 200` — strict resume treats
  `--budget` as the CUMULATIVE cap and refused 109, matching the recorded c_rrect_100w_rc2 cause);
  w_klangfilm fresh run killed at **0 evals** (nothing lost); w_ath_core14 at ~23 s (~1 row).
  Both killed w_* jobs re-queued under `_r2` ids after the atlas arms. PAUSED/RESUMED logged by
  the runner; every stop recorded in the queue log.
- **Fault 1 (committed `8eca641`):** `fidelity_pairs` passed the backend STRING to
  `worker.warm`/`evaluate` (both need the object) — the first five probes
  (`b1_mesh_*_20261118`) each burned in ~6 s. Fixed via `cli._backend`-mirroring
  `_backend_obj` at all four call sites + regression tests.
- **Fault 2 (no code, doc fix):** the night-queue skill's resume rule said "budget = the missing
  new evals" — wrong; fixed to "budget = the ORIGINAL cumulative cap" (strict resume refuses a
  shrink). The empirical rule now matches the c_rrect_100w_rc3 precedent (budget 110 → ok).
- **Now solving:** `b1_mesh_2f7307c06023_20261118_rc2` — first probe went past the previous crash
  point in ~3 min, GPU 2538 MiB / 100 % (refined fold-warm solve with memwatch + VRAM record).
  Queue order now: 5 × b1_rc2 → w_ext resume2 (budget 200) → w_* backlog → atlas BO arms →
  re-added w_klangfilm/w_ath_core14 `_r2` → (burned old b1 ids skipped).

## 2026-11-18 - integration carried to main; cloud-resume pointer set (local orchestrator)

- The `classify_recipes` close-out (`e13a1ad`) landed on `hornfab-all-2026-11-18` AFTER PR #70
  merged, so a short PR carries it (plus this pointer) to `main`. From here on: `main` and
  `hornfab-all-*` are current; integration continues per R21 (PRs into `hornfab-all-*`).
- **Cloud-resume pointer:** `cloud/fable-next-2026-11-18` is PROVENANCE (stale at `1e9f71b`);
  a resuming Fable senior session branches from `hornfab-all-2026-11-18` (or `main`) and reads
  `docs/ACTIVE_STATE.md` (updated tonight) + the HANDOFF evening section item 0.

## 2026-11-18 - legacy-recipe classification executed over runs/ (R12b/D9 close-out; read-only)

- `tools/analysis/classify_recipes.py` run over the real `runs/` tree (48,474 design.json records
  in 18.4 s, single process, thread caps 1, read-only): **48,471 rebuildable** (30,147 of them the
  legacy `{family, params}` schema — rebuildable from params by construction), **3 bridge**
  (klangfilm_lame_hv_core designs from 2026-11-17, kernel digest moved since save — informational
  only per R12b), **0 record_refused, 0 unverified**. Two tool fixes on the way: the legacy-schema
  class and `importlib` for the live kernel digest. Summary:
  `docs/evidence/wp09_d9_provenance_2026-11-18/classify_summary.json` (+ classify_rows.jsonl kept
  under runs/analysis/classify_recipes_2026-11-18/, untracked). WP 0.9/D9 is now complete through
  its full STEP 4f description.

## 2026-11-18 - reuse rescore published (v7/v10 floors + ties), WP 0.9/D9 merged, mixed_identity fixed (local orchestrator, owner-directed)

- **Owner directive executed (protect → reuse → ≤3 CPU workers → verify → report).** Zero re-scoring
  of completed columns; only 2×166-design samples + 1 floor pass computed. All `runs/` data
  read-only; GPU night untouched; thread caps 1. A relaunched full sequence that would have
  overwritten the completed outputs was killed before its first write (its out dirs are created at
  write time). Scripts + provenance: `docs/evidence/v10_rescore_2026-11-18/results/` (README with
  the full reading).
- **mixed_identity FIXED** (`tools/analysis/rescore_identity.py` + tests): the old flag counted
  per-design `score_id`s (each folds `metric_id`) → always True on real data. New flag = count of
  score identities (score code + version + weights + objective block + brief) per column.
  compare_all v7/v10/v10_slope5: **False, False, False** [measured]. Same design set scored under
  shipped-vs-offline v10 briefs on the sample: **max |ΔJ| = 0.0 exactly (n=122)** → the offline
  full-fleet v10 column IS the shipped column numerically.
- **Floors published (freq part, top-28 pairs, 257 pairs):** v7 **0.310 J**, v10 **0.468 J**,
  v10_slope5 **0.486 J**. ⚠ v7 0.310 vs the published D8 0.13 — protocol reconciliation flagged
  (NOTES_FOR_SENIOR item 3; ties keep 0.13 until resolved). slope5's R2 gate is now satisfied
  (diagnostic ranks only). Combined floor (WP 2.3) waits on B1's mesh part.
- **Ties under each identity's own floor:** v7: v8/A_r20 tie-pair behind A_r15, fold-warm next;
  v10: fold_warm ≈ morph ≈ ext_throat_v7 within 0.468 (three constructions inside one floor — the
  B6 matched-rerun set per R19/R20b). Throat block under v10: v8 < A_r15 < A_r20, best B ~2.7 J
  out — the G5 park is unchanged by v10.
- **v10 slope5 sample** (166, diagnostic): lane bests consistent with v10's ordering; its column is
  marked `sampled: true` — fleet ranks would need one full run (~30 min CPU).
- **WP 0.9 / D9 (R12/R12b) implemented locally** (the dispatched lane produced nothing and was
  taken over): `mesh_meta.json` now echoes the mesher `surfaceFit` resolved mode + flags the
  auto→approximate fallback (`_surface_fit_meta`, additive; explicit interpolate never retried per
  config_builder); `recipe_meta` gains the `record_digest` block (surface_record /
  canonical_record_v2 / not_recorded) — record digests GATE rebuilds (canonical_record_v2 gate
  pre-existing, restated as THE gate), kernel `implementation_sha256` stays informational;
  evaluation rows gain additive `build_box_m` (acoustic bbox + resolved wall, R12/R10);
  `tools/analysis/classify_recipes.py` classifies legacy recipes (rebuildable / bridge /
  record_refused / unverified) CPU-only over runs/. Tests `tests/test_wp09_d9_provenance.py`
  (9 tests) + regression `test_design_recipe_meta.py` green; no stored row rewritten.
- **Night causes (WP 0.7)** appended to the night review by the fixer lane: UTF-8 decode rule,
  9/9 ids classified byte-verbatim; t_trit80_rc2 actually ran 82 calls (counter artifact found);
  t_ath14 had two launches (10054 crash, then stale-root refuse). Fix candidates listed, no code
  changed (owner decision 8 pending).
- B1 batch 1 sits in the live night queue (inserted earlier today, dry-run exit 0); batch 2 /
  WP 4.2 verify solves / BO `_r2` queue after the probe gates per R6.

## 2026-11-18 - integration STEP 1 closed on hornfab-all; STEP 2 CPU evidence 2b/2d/2e/2f committed (local orchestrator, R21/R22)

- **PRs merged [verified]:** #69 (cloud→hornfab-all, merge `382c682`), #67 (plan→main, merge
  `63c23a8`), with the owner-box suite result pasted (4861 passed / 4 known failures / 22 skipped;
  +23 tests confirmed by def-count deltas 8+7+2+3+2+1, no parametrize). `hornfab-all→main` PRs and
  #68 close-out follow after the STEP 2 commits. Local `hornfab-all` advanced to `382c682`.
- **CLAUDE.md R21 ownership row added** (STEP 1.5) above "Need a file you do not own?".
- **R22 resolved:** uncommitted `scalar_v9.py` v9-math edit DISCARDED
  (patch archived outside the repo); `tests/test_v9_polar_window.py` deleted (tested only the
  discarded API); AGENTS.md/`.opencode` agent-config sync committed as doc/config-only (matches the
  umbrella preset text); `hl__klangfilm_lame_curved_v1_c200w.yaml` KEPT after `tools/shape_check.py`
  PASS (mesh ok, 4853/24000 dofs, mouth 585x255, depth 196, envelope fits, round coupling).
- **2b throat authority (R9 follow-up):** `u3_authority.py --csv-dir` runs committed
  (`authority_A_vs_v8.{json,csv/}`, `authority_B_p3_vs_o50.{json,csv/}`). rho15: authority FALSE
  (max 1.84° H) as expected; **rho20: authority TRUE (3.12° H, 2500-5500, V < half)** — contradicts
  §10.2's "v8 → A_r20 no [inferred]" at the threshold; §10.2 rows left for the senior pass
  (NOTES_FOR_SENIOR 2026-11-18 entry). Phase 3 winner vs B_o50: authority FALSE (fills the
  "not judged" row as a verified no-authority/tie, ΔJ 0.0896 < 0.13).
- **2d ST260 anchor (R4):** source check done. Config values were the rev7 PAPER example; the real
  ST260 device (page + STL) differs: refit of `ST260-19.stl` gives a0 9.45° (19° total), k 2.13,
  m 0.86, q 5.05 at RMS 0.08 mm (old values 1.33 mm RMS) — `anchor__rosse_st260_v1.yaml` CORRECTED
  before any solve. **No admissible measured build exists** (6 linked builds checked; distance/
  gating/step never stated together; one is a simulation): R4 fallback (ATH CORE/Tritonia) recorded;
  ST260 NOT solved; the 2 approved anchor solves unspent. Evidence:
  `docs/evidence/anchor_st260_2026-11-18/README.md` (+ `measured/ST260-19.stl`). shape_check:
  corrected config meshes 944/12000 dofs, mouth 260 ✓, depth 88 ✓; the table's ok=NO is the
  pre-existing brief-less-config throat-"unknown" property (pre-correction file fails identically).
- **2e B1 doc fix (WP 2.2):** dated correction appended to
  `scratch/fable_architecture/.b1/b1_mesh_feasibility.md` — only `3a1038da45d0` and `9fcd21fc1904`
  are infeasible; `766c…`/`508f…`/`b996…` are probe-grade (batch 2, R5).
- **2f U3 host (R8):** best stored `hl__biradial_es_style_v7` = run
  `runs/20261116T090751Z-screen-37b115`, design `9b05b8756526`, J 6.336386 (v7 home brief identity,
  verified against run.json/best.json/status.json). `u3_jobs.py` wrote
  `examples/studies/u3_biradial_es_style_v7/` (control + 7 variants; vt_480 and term_sides invalid
  per the tool's reach table). Control shape_check PASS (3270/24000 dofs, fits, round coupling).
  WP 4.2 verify solves are queue-ready.
- **STEP 3 B1 batch 1 inserted into the LIVE night (GPU, R5/R6):** 5 fold-warm ×2 probe jobs
  (`scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml`) appended AFTER existing pending work
  of `runs/nights/cd_rrect_2026-11-17.yaml` (backup `cd_rrect_2026-11-17.yaml.bak-20261118-b1`);
  `run_campaign_night.py --dry-run` exit 0. Batch 2 / anchor / 4.2+ wait on the probe-1 spill gate;
  the anchor batch is CANCELLED (2d outcome). GPU lane was and stayed BUSY (live job
  `w_crowe_panel_es600_v7_200w1`); zero direct solves by the orchestrator.
- **Dry-run NOTE recorded:** 4 queued `home_range15_*` jobs reference
  `briefs/home_range_v9_h12.yaml` with `oa_excess_tol`+`ripple_window` keys — these exist only in
  the DISCARDED scalar_v9 math; they will refuse at start against the merged tree (owner/range-lane
  decision pending: re-home on v10 `ripple_region preferred_edge` or re-pin).
- **STEP 2a running:** the full rescore sequence (v7/v9/v10 offline + shipped/slope5 + floors +
  compares) is executing in the background; results commit follows with the acceptance checks.

## 2026-11-18 - owner-box integration started: cloud branch suite green after digest-pin fix (local orchestrator)

- Suite on `cloud/fable-next-2026-11-18` (offline, thread caps 1, -n 6 --dist loadscope):
  **4861 passed, 4 failed, 22 skipped, 18:42 min** — failures exactly the known 4
  (`test_v8_key_set…`, `test_b8_lanes…`, 2 × `test_night_bo_arm_wrapper`).
- Fixed before merge (R7 / WP 0.9): `tests/test_klangfilm_hv_digest_pin.py` pinned the cloud
  container's `implementation_digest()` values (`ee160698…`/`c65beb16…`), but
  `implementation_digest()` folds `numpy=<v>;scipy=<v>` into the hash, so those constants cannot
  hold on another dependency set. Owner box (numpy 2.5.4 / scipy 1.18.1) computes
  `1304dea3…`/`a032f660…` — and the stored local recipes carry exactly those digests
  (runs/20261117T071329Z-screen-e4f90d design.json; docs/evidence/klangfilm_hv_2026-11-16/search_box.json),
  so nothing is locked out. The test now pins the frozen FILE BYTES (same file list + CRLF
  normalisation as the digest recipe: adapter, kernel, parent, cap, shell) and independently
  re-checks the digest recipe + version suffix. Kernel files verified byte-identical to
  pre-b06a938 (`git diff b06a938^ -- <both kernel files>` empty).
- R22 on the owner box: the uncommitted `scalar_v9.py` edit (adds `ripple_window`/`oa_excess_tol`
  v9 math) DISCARDED per R22 (copy saved outside the repo);
  `tests/test_v9_polar_window.py` deleted (it tested only the discarded API);
  AGENTS.md/.opencode agent-config sync (opencode-go-max preset text + mirror of the umbrella
  fallback/backgroundJobs block) kept as doc/config-only;
  `hl__klangfilm_lame_curved_v1_c200w.yaml` kept pending shape_check.

## 2026-11-18 - cloud senior: ALL owner questions resolved under owner delegation (R1-R25) + code

- `scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md`: research frame (CTA-2034
  listening window, Olive preference model, Geddes, Sridhar, repo S1/N3/SIM_VS_REAL) and 25 decisions,
  each with evidence and a reversal condition. Plan §10.3 summarises them.
- Code/config set here: v10 home briefs `examples/briefs/home_landscape_2026-11-18_v10/` (base +
  slope5 constancy on 116 points; R1-R3); Klangfilm H/V kernels restored to pre-b06a938 bytes +
  `tests/test_klangfilm_hv_digest_pin.py` (R7; facts moved to the contract errata); protected list
  `status: confirmed`, refusal storms stop protected lanes (R11); night status `ok_no_result` (R16);
  `replay.REPLAY_VERSIONS` single list + test (R17); `u3_authority --csv-dir` (R18); Crowe-X /
  Le Cleach YAML comments (config_sha unchanged, verified; R13/R14); GPU job files
  `docs/evidence/gpu_queue_resolved_2026-11-18/` (anchor, BO `_r2`; dry-run clean).
- Not done from the cloud: CLAUDE.md ownership row (R21) - the session guard refused the edit; the
  local prompt adds it.
- Tests (cloud): 4826 collected, failure set identical to the 18ec991 baseline (no new failures).
- Execution: `LOCAL_AGENT_PROMPT_2026-11-18.md` (STEP 1 integrate, 2 CPU evidence, 3 GPU order,
  4 evidence + WP 0.9/D9).

## 2026-11-18 - cloud senior: review of the pushed night record (WP 0.7 / 7.2 / D8)

- Merged `2b35194` (archive of worktree drafts + night cd_rrect_2026-11-17 ledger) into
  `cloud/fable-next-2026-11-18`. That commit had no CONTINUITY/ISSUES/INDEX entries; INDEX line
  added here.
- `docs/evidence/night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md`: throat rows match the evidence
  exactly; 14.7 h ok / 3.5 h failed / 2.1 h blocked; 0 of 9 BO arms finished (2 owner skips,
  t_hvlaw x2 refused for too few training rows [code-verified], t_ath14_turbo100 refused,
  t_klame x2 failed); t_trit80_rc2 recorded ok with 0 evals and no J; pending queue clean under
  the zero-dimension guard. Handback §9 added.

## 2026-11-18 - cloud senior G6 (Fable D10): HANDOFF refreshed, PR plan, HANDBACK_CLOUD_2026-11-18.md

- `HANDOFF_2026-11-18.md`: cloud additions table, corrections (A_r15 vs v8 is a tie; no A-family
  onset search; #68 code byte-identical to this branch [verified]), PR plan: #67 -> main; cloud
  draft -> hornfab-all; one PR hornfab-all -> main; close #68; nights to main at a night boundary.
- `HANDBACK_CLOUD_2026-11-18.md` (repo root): status summary, per-commit verdicts (all approve),
  test sets (cloud baseline 20 F + 19 E, final identical, +15 new passing tests), 7 numbered
  owner decisions, ordered local work list A-H with commands, queue lines, off-plan proposals.

## 2026-11-18 - cloud senior G5 (Fable WP 4.4): throat block parked on A (proposal)

- `docs/evidence/throat_hv_2026-11-18/G5_RECOMMENDATION_2026-11-18.md`: park on A as inert in
  this envelope; no A_r15 + onset/ramp test. Code-verified: A's seed (`morph_target 0`,
  `morph_fixed`/`morph_rate` present) makes `families.py:647-651` refuse `hv_onset_frac` /
  `section_exp_ramp`; native morph keys load but are inert with no morph target.
- B kept as "H authority, not competitive under v7"; free CPU check via the v10 rescore column.
- No config written, nothing queued.

## 2026-11-18 - cloud senior G1: plan §10.2 "Status 2026-11-18" (Fable plan §4, §8.2, §10.1)

- `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` §10.2: one status row per WP (done /
  tool-done-not-run / blocked-on-owner / not started), placement of the 11-18 work (throat block =
  stage-4 freedom built ahead of its gate; v10 = the §10.1 new-identity fix; agent_bench +
  contracts = off-plan knowledge track), the throat authority table, critical path, next three
  owner decisions.
- Throat authority, re-derived from the part3 CSVs with `u3_authority.authority()` [verified]:
  A (rho on ext-throat) INERT (≤ 1.28° per band; A_r15 vs v8 ΔJ 0.0192 = TIE under the 0.13
  floor); B onset has H authority (up to ~10°, V < half; best onset beats B_ctl by 0.251 > floor);
  B not competitive under v7 (load ~3.2 J); Phase 3 gain 0.0896 over its seed = TIE.
- INDEX: throat evidence folder line added (was missing).

## 2026-11-18 - cloud senior G4 (Fable D6 step 1): physical anchor = R-OSSE ST260 (research only)

- Pick: Batik's R-OSSE rev7 "ST260" example (1-inch, round, 260 mm; full parameter set published,
  CC BY-NC-SA 4.0; ST260 page links user builds with measurements). Geddes OS rejected (no exact
  published dimensions). Dossier: `docs/research/typologies/ANCHOR_ST260_RESEARCH_2026-11-18.md`.
- Config: `examples/typologies/anchor_2026-11-18/anchor__rosse_st260_v1.yaml` (all bounds pinned,
  loads + validates [verified]; NOT meshed, shape_check required).
- Predeclared pass rule: -6 dB beamwidth ±5° per 1/3-octave band (±3° in 2-5 kHz), DI ±1 dB,
  1-8 kHz, same DI method both sides.
- Limits: at-horns.eu / diyAudio unreachable from the cloud; values come from the repo's 2026-11-16
  fetch and must be re-read locally; the measurement set is not yet chosen.

## 2026-11-18 - cloud senior G3 (Fable WP 2.2 / D7): zero-dimension searches refused; B1 readiness

- Truth fix: `search/cma.py::require_free_dimensions` (called first in `search()`), the
  `hornlab-search search` CLI (exit 2, empty run dir removed) and `tools/run_campaign_night.py
  --dry-run` now refuse a search whose config leaves CMA-ES no free dimension, naming
  `hornlab-search run --config <yaml> --mode screen|finalist` / `kind: command`. This is the part3
  pycma `x0=[]` crash. Tests: `tests/test_search_zero_dimensions.py` (7).
- Checked: the B1 and B1f lines from b6d3ba4 are `kind: command` -> fidelity_pairs.py (calls
  evaluate directly), so they never hit the crash; all three night files dry-run clean.
- Finding: b1_mesh_feasibility.md excludes "the five ext-throat designs" but its own table shows
  766c/508f/b996 build at x2 (probe grade). Optional 3-job batch written:
  `docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml`. The v7 leader 3a1038 and
  v8 incumbent 9fcd21 remain infeasible on the 8 GB card.
- No GPU, no queue edit, no default changed.

## 2026-11-18 - cloud senior G2 (Fable WP 1.4 / 1.5): v10 rescore is one local command

- Bug fixed: `objective/replay.py` dispatched v10 but its version gate `(1,2,3,4,7,9)` refused it
  (`objective_version_not_supported_by_replay`), so a v10 rescore scored zero rows. Gate now
  includes 10. No stored J, row, config_sha or default changed (v10 is opt-in; no brief in
  `examples/` uses it).
- `tools/analysis/rescore_identity.py`: `--run-brief <stem>`, `--runs-root <dir>`, rows carry
  `stored_j` / `parity_delta`, new `compare` subcommand (per-lane bests side by side, one column
  per identity, ranks within a column only).
- New: `docs/evidence/v10_rescore_2026-11-18/` (README with exact local commands + two OFFLINE
  rescore briefs: v9 corridor = owner's 11-17 second score, v10 = same + `preferred_edge`).
- Tests: new `tests/test_rescore_identity_v10.py` (8); `test_obj_replay_v9_parity.py` gate string.
- NOT RUN: needs `runs/` (local agent; commands in the README).

## 2026-11-18 - throat H/V sweep: Phases 1-3 DONE on this branch (owner-authorized GPU)

- Phase 1 (7 single solves, \hornlab-search run\): all ok, v7 identity = v8 stored
  (20261116T025728Z-screen-cd60f7). **A_r15 (rho 1.5) 3.08361 beats the v8 incumbent 3.10281
  by 0.0192**; A_r20 3.12713 worse by 0.0243. B family (no ext throat): best B_o50 5.69735
  (B_ctl 5.94839; the ~5.7-6.4 level is the v7 load term, load 3.2 vs 0.0 - mechanism study).
- Job-line correction (IMPORTANT): \kind: search, budget: 1\ + every bound \search: false  crashes pycma (x0=[] / ufunc isinf TypeError) - single-design night jobs must be
  \kind: command\ -> \hornlab-search run --config <yaml> --mode screen\. Three part2 ids
  (throat_hv_B_*) burned on this; reinserted as throat_hv_run_*.
- Phase 2 (2 epw8 solves): |dJ| 0.00857/0.01013 -> gate PASSED (0.0101 << 0.25104).
- Phase 3 (budget 40 search, seed B_o50): 41/41 ok, best J 5.60780 at rho 1.371 / onset 0.320 /
  ramp 2.160 (run 20261118T150846Z-screen-9a04c5). Track used 9 single solves + one 40-eval
  search (cap respected; the +1 v8 identity re-solve was unnecessary, identity byte-verified).
- Evidence: docs/evidence/throat_hv_2026-11-18/ (part3 + phase1_summary.csv + per-config
  hv_beamwidth/di CSVs + p2/p3 eval CSVs + overlay PNGs). New configs: 3 files in
  examples/typologies/throat_hv_2026-11-18/sweep/ (2 epw8 + B_search40, shape_checked).
- Night cd_rrect_2026-11-17 resumed (stale lock pid 15952 taken over); night file edits: 9
  throat jobs inserted, backup at runs/nights/cd_rrect_2026-11-17.yaml.bak-20261118. Owner
  authorized skipping the running BO arm; t_ath14_scalar100 (78 obs) and t_corelaw_turbo100
  were killed and recorded blocked - resume with a FRESH --root. Watcher task
  HornLabThroatPhase1Poll deleted (track finished).

## 2026-11-18 - BO metric policy for objective v10 staged (PR-D, OWNER-GATED with PR-A)

- `bo/metrics.py`: new `freeze_metric_policy_v10` / `measure_metrics_v10` (schema
  `bo-physical-metric-v10/1`). Coverage = the v9 profile cost (raw), ripple = the v10
  `ripple_region` window. `freeze_metric_policy` is unchanged and still accepts v4/v7 only.
- `assert_single_objective_cohort`: refuses any cohort mixing v4/v7/v9/v10 labels.
  `bo.cohort.validate_cohort` already refuses mixed versions; a new test pins v7+v10 and v9+v10.
- Tests: `tests/test_bo_metrics_v10.py`. No wiring into proposals or studies.

## 2026-11-18 - Objective v10 staged (PR-A, OWNER-GATED): v9 + explicit required ripple_region

- New `hornlab_search/objective/scalar_v10.py`, registered as version 10 in `versions.py`,
  `search/evaluate.py`, `objective/replay.py` and `config.py`. `scalar_v9.py` is NOT edited; v9 J
  and the v9 tests are unchanged.
- Code-verified semantics: profile `preferred/min/max_deg` are FULL beamwidths (the v9 cov term
  compares them with `beamwidth_deg`'s total included angle). So v9 corridor mode inspects
  +/-(max-min)/2 and v9 target mode inspects +/-preferred (twice the -6 dB edge). The v9
  docstring's "half-angle" reading does not hold.
- v10 requires `objective.ripple_region` (no default): `preferred_edge` (+/-preferred/2), `max_edge` (+/-max/2, corridor only; added after E1),
  `min_edge` (+/-min/2, corridor only) or `{mode: seat_zone_deg, h_deg, v_deg}` (declared total
  angles). Every other term is v9's. New identity: `v10_score_identity` (sha256 of the block).
- `tests/test_objective_v8.py` registration assertion updated to the new tuple (still exact).
- No brief uses v10. The owner picks the region policy before any brief does.

## 2026-11-18 - Agent science benchmark fixtures (WP-K1): tests/agent_bench/

- 24 frozen cases (`cases/case_NN.yaml`): a prompt, the paths the agent may read, and an answer key
  (must_include / must_not_include / must_cite_any / defer_ok). Keys are sourced from the repo,
  except case 16, which is `spec_only`. All 7 negative controls are embedded.
- `scorer.py` grades SAVED answers only; it makes no model calls. Sample good and bad answers live
  under `answers/`. `tests/test_agent_bench.py` checks the schema, that every path exists, that
  every regex compiles, and the sample grading.

## 2026-11-18 - Klangfilm H/V kernels: stale seed-mouth comments and frozen-copy SHA docstrings corrected (comments only)

- `_klangfilm_lame_hv_core_v1.py` SEEDS comments now give the recomputed mouths (b1 479.6x239.7,
  b2 595.0x232.8, b3 472.5x266.1, b4 562.5x261.6 mm; these match PHASE_B_GEOMETRY). The frozen-copy
  docstrings of both H/V kernels now record the original SHA and today's tools-file SHA.
- No geometry change. The klangfilm_lame_hv and hv_core family `implementation_sha256` DO change
  (the digests hash these files), so saved recipes that require the old digest will be refused.

## 2026-11-18 - Construction contracts moved from DRAFT to REVIEWED (senior, docs only)

- All 4 contracts end with a "Senior review" section listing their open items.
- Klangfilm: the seed-mouth and SHA findings were confirmed by re-running the kernel; the code
  comments are fixed in a separate owner-gated patch (it changes the family digests).
- Crowe-X: the header claims `g_L_mm` hi 320 but the bounds say 285. The header comment is
  annotated; the bounds are unchanged.
- Le Cleach H/V pair: relabelled [reconstruction]. The YAML `description:` still says "published";
  rewording it is an owner decision because the value is parsed config.

## 2026-11-18 - Throat H/V follow-ons: rolled rho, iwata_ar onset, R-OSSE verdict, block contract

- Rolled family: `throat_hv_ratio` now maps to the radial scale `rho**(cos(2psi)/2 * w)` inside the
  relief window `w` (LABELED HYBRID). The window is zero through the source-matching region and at
  the mouth attachment, so rho = 1 is the identity and the throat and mouth are unchanged. Legal on the
  v7 seeds for roughly 0.6-1.3; larger values are refused by the existing constriction, envelope and
  self-approach guards. Searchable; a ratio box that excludes 1 keeps the window position live. The
  patch's own refusal test was replaced by behaviour tests. The rolled `implementation_sha256`
  changes again.
- `lecleach_iwata_ar` (rows `iwata_ar`): `hv_onset_frac` delays the AR law,
  `AR = 1 + (AR_m - 1) clamp((s - s_on)/(1 - s_on))**ar_p`. Onset 0 equals today's law, to 1e-9.
  `section_exp_ramp` is an alias of `ar_p` (giving both is refused); rho is refused there. LABELED
  HYBRID.
- R-OSSE: no rho. The rev7 primary source describes only an axisymmetric profile.
- New `docs/knowledge/contracts/throat_hv_block.md`.

## 2026-11-18 - Shared near-throat H/V block implemented (CPU only; mesher and BEM checks pending)

- New `hornlab_search/design/throat_hv.py`: `throat_hv_ratio` (rho), `hv_onset_frac`,
  `section_exp_ramp`, with one meaning in every family. Absent keys = byte-identical configs,
  geometry and hashes; rho = 1 = the parent law.
- Native OSSE: rho -> per-azimuth `k(p) = k*rho**(-cos2p/2)` mesher expression (inside the OS-SE
  parent; keeps the driver-exit slope). Onset/ramp alias `morph_fixed`/`morph_rate` (the Ath
  morph). Refused without `morph_target` or alongside the native key.
- osse_rollback: per-azimuth k; the superformula window uses the Ath ramp (LABELED HYBRID).
- Le Cleac'h H/V pair: per-plane march T (larger T = faster near-throat growth, eq. 42 plus a
  numeric test). The onset ramp blends the round core to the H/V ellipse (LABELED HYBRID).
  `iwata_ar` is untouched.
- Rolled family: onset/ramp replace the relief window start (now allowed down to 0) and are
  searchable. rho != 1 is refused (no per-plane throat growth parameter exists yet). Editing
  `rolled_family.py` changes its `implementation_sha256`, so saved recipes that require the old
  digest will be refused.
- Example configs (NOT RUN): `examples/typologies/throat_hv_2026-11-18/` (A: v8 incumbent + rho; B:
  no round extension + morph to the mouth extent + all three knobs).
- Tests: 4 new test files. The full suite shows the same 30 failed / 76 errors on main and on this
  change (all from absent `cma`/`hornlab_mesher` etc.), so there are 0 new failures.

## 2026-11-18 - Near-throat H/V control: audit, research (KH-002), option literature (KH-003)

- Docs only; no code. Root cause in OS generators: `a0` (from `driver.exit_angle_deg`) and `k`
  are shared by every azimuth, so only `a(phi)` splits H/V, and that split grows late. The
  `throat_ext_length_mm` extension is round (search pressure pins it short). The rolled and
  toroidal routes have no near-throat H/V term.
- Primary-verified: Batík OS-SE allows its parameters to vary around the device, so a per-azimuth
  `a0`/`k` stays inside the OS-SE parent. R-OSSE is unclassified. Smoothstep section ramps and
  OS-SE plus elliptical throat extensions are labeled hybrids.
- Proposed (owner approval pending): one shared throat H/V block (asymmetry ratio, onset fraction,
  section-exponent ramp), off for symmetric briefs, with H=V reproducing the parent exactly.
  Family one-off onset knobs are frozen neutral in new configs.

## 2026-11-18 - WP-K0/K1 docs-only: four draft construction contracts, CLAUDE.md routing, Keele scope fix

- Docs and skill text only. No code, config, brief, queue, scoring or GPU change. PR #67 not touched.
- Added `docs/knowledge/contracts/` (DRAFT, senior review pending): Klangfilm–Lamé H/V and core,
  CROWE V2A and Crowe-X/OS-SE CD, rolled section pucker, and Le Cléac'h/Iwata H/V. The drafting
  environment lacked scipy/hornlab_mesher, so no tests were run.
- Findings for review (not fixed): Klangfilm `cd_core_blend` is a switch (no parent reduction), and
  the Phase A cap-area residual is pre-deformation. Crowe-X `g_L_mm` header says 320, bounds say 285.
  The Le Cléac'h H/V plane meridians lose their axial coordinate (arc-fraction stations, `πab`
  report-only). The rolled station definition is ambiguous.
- `CLAUDE.md`: added a routing section deferring to `AGENTS.md` precedence. The wave plan and the
  ownership table are marked historical. Start-here now reads `ACTIVE_STATE` plus the newest log
  entry only.
- `hornlab-shape-check`: the Keele K-law is now scoped to a Keele/Bi-Radial starting estimate (KH-001),
  not a mouth target for every family.
- Added `docs/knowledge/AGENT_BENCHMARK_SPEC_2026-11-18.md` (24 cases plus negative controls;
  spec only).

## 2026-11-18 (local orchestrator) - Night truth (C1) + data-agreement gate (C2) landed; B1 encoding owner-decided; queue repaired

- **C1 night truth** (`tools/run_campaign_night.py`, `tools/night_status.py`, new
  `tests/test_night_status_truth.py`, 13 tests): the runner now records, additively, per summary
  row: `rows_before/rows_after/rows_window/valid_rows_window/best_J_window` (a `--resume` job
  reports the work IT did), `bo_progress` (BO arms read `studies.sqlite3` read-only), a ~15-line
  `log_tail`, and a `stop_reason` class (9 values); `night_status` prefers the new fields and
  re-derives old rows read-only - a resume row with real rows but no attribution reads
  "unknown", never "0 evals". Verified on real data [measured]:
  `cont_p80_athcore_corelaw_200: best J 4.8097, 182 evals (window 182/282, valid 159)`;
  `t_trit80_rc2: best J 5.5235, 82 evals (BO screen 80 verify 2, observations 80)`. The live
  runner picks the new fields up on its next launch (not mid-night). Known pre-existing failure
  `tests/test_night_bo_arm_wrapper.py` (2, monkeypatch-Popen mismatch since `1482304`) untouched.
- **C2 data-agreement gate** (`tools/analysis/space_card.py`, new
  `tests/test_space_card_data_agreement.py`, 7 tests): `_data_agreement` is "unknown" when the
  top decile is absent or n < 10 (True/False only at n >= 10, `MIN_LINK_ROWS = 10`); cards render
  `unconfirmed (n=...)`; unknown never yields a data-justified `action: link`; `data_agrees`
  values unchanged for backward compatibility. Senior rule enforced: never claim "data
  disagrees" for n < 10.
- **B1 (mesh fidelity) - owner encoding decision 2026-11-18**: B1 must test MESH convergence
  (same ten designs/brief/identity, SAME frequency grid as the reference solve; refinement =
  higher epw and/or tighter throat/mouth/rear resolution; realized triangle/DOF counts reported
  for both meshes; per-design |ΔJ| + per-term deltas vs the numerical floor; "mesh-sensitive"
  flags; 8 GB feasibility per design before queuing with the quarter/half model; non-fitting
  designs marked "mesh check infeasible on this card" and left out of the conclusion; memwatch +
  baseline/peak VRAM + sysmem Shared-Usage check mandatory). The frequency-grid pair encoding is
  renamed **B1f** and never read as mesh convergence. Key coding finding: `dof_cap_finalist`
  does NOT densify the mesh for these configs (epw/f_max unchanged; the cap is not binding) -
  the finalist tier changes frequency grids only. B1 CPU dry-run (build both meshes, no solves,
  epw x2 and x3 candidates) and the feasibility table are in preparation
  (`scratch/fable_architecture/.b1/`); GPU slots wait for owner approval of the table.
- **Queue edits on the live night `cd_rrect_2026-11-17`** (owner-approved; documented in
  `runs/nights/cd_rrect_2026-11-17/held_and_edited_2026-11-18.md`): `t_rrect_turbo300` replaced
  by `c_rrect_100w_rc3` (`rosse_rect_cli search --resume 20261117T070118Z-screen-8627f8 --budget
  110`); the two atlas turbo300 arms moved to the end; `w_osse_rrect_fold_warm_v7_200w1` HELD
  (warm-start identity pending C5; links withdrawn). **argv repair:** all 12 queued
  `w_*_200w1` jobs had bare `search` argv[0] (kind:command runs argv verbatim, which would have
  failed at launch with FileNotFoundError); fixed to `.venv/Scripts/hornlab-search.exe` (8
  stock) and `.venv/Scripts/python.exe tools/geometry/<bridge>_cli.py search` (5 bridge:
  control->section_pucker_cli, crowe->crowe_panel_cli, klame->klangfilm_lame_cli, rosse
  r120/r50->rosse_rect_cli). Post-fix: full YAML parse, 54 unique ids, argv audit clean, runner
  `--dry-run` clean. Owner's manual PAUSE (0-byte, set 2026-11-17 20:12, unrelated to this
  work) removed with the owner's word; night resumed into the BO arms (`t_ath14_turbo100`
  running, merged lock fix in effect).
- **D4 evidence (rerun on the fixed state)** (`scratch/fable_architecture/.evidence/
  shape_check_proposals_20261118.log`, `search_preflight_20261118/`): shape check **9/14** -
  the 5 bridge-type `_w1` lanes fail the STOCK `DesignSpace.from_config`/`shape_check` path
  (`unknown rows type '...'` for section_pucker/crowe_panel/klangfilm_lame/rosse_rect; they are
  bridge-CLI configs); the 9 loadable lanes pass everything. `search_preflight --from-runs`:
  seed in own box everywhere (exit 0), but **history refused on every loadable lane** - native
  lanes via `warm_start`'s brief-identity refusal, generator lanes via the raw-string fallback
  (`../../briefs/...` vs `../../../briefs/...`) - so **no expected-hits number computed** (C5,
  digest identity, remains the owner-gated fix; the path fix alone cannot unblock it). New
  `no_headroom`: `hl__klangfilm_lame_curved_v1_c200_w1` (seed = prior best). Crowe marking
  "not queueable without warm_start + reason" appended to the decision packet + the lane card.
- **Plan amendments D5-D10** written into `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` §10.1
  (proposals, nothing auto-applies); the corrected C2 explanation + the "what J pays for today"
  table recorded in the owner decision packet. Full handoff:
  `scratch/fable_architecture/ORCHESTRATOR_HANDOFF_2026-11-17_LATE.md`. Second-writer commits
  `f5db35e`/`3682173` recorded for the D10 one-integrator question; the throat-H/V patch set
  (4 patches, clone `.claude/worktrees/agent-a527a7d28dc77734a`, tip `5af0048`) waits for
  integration after this push + the post-drain suite. Isolated-clone test run re-verified by a
  second independent agent (`tmp_thv_test`: 0 new failures, mesher accepts k-expression); my
  duplicated pytest run in the clone was stopped on owner instruction.
- **B1 CPU dry-run landed (2026-11-18, real mesher, no solves).** Realized sizing
  (`scratch/fable_architecture/.b1/b1_mesh_feasibility.md`): epw ×2 (12) builds at the existing
  24 k screen cap for the five fold-warm designs at 14 270-15 388 quarter DOF — INSIDE the
  measured 8.9-15.7 k OOM transition, i.e. **probe-grade**, each a per-design fresh-process job
  with Shared-Usage spill adjudication; epw ×3 (18) is cap-bound for every design (true size
  31.8-49.3 k DOF; build.py refuses at 1.5× cap pre-mesh and deletes above cap post-build, so
  "cap-bound" = not built, never coarsened); the five ext-throat designs are **excluded**
  ("mesh check infeasible on this card, est. ~21.1 k DOF" — the mesher also refuses the finer
  geometry: symmetry-plane slivers at epw 12/18). Same-grid contract verified: refined
  SolveSpec.hash == stored solve hash for all ten. Per-term deltas read from stored rows
  (`terms` + `metrics`, di_source balloon) — no reference re-solve needed; mesh-sensitivity
  gain threshold 0.0057 J (smallest non-degenerate finalist gap in the set). Hygiene hooks in
  `tools/night_queue/fidelity_pairs.py`: --teardown-per-design (verified worker shutdown),
  --record-vram (baseline/peak/dedicated/SHARED per design; shared > 512 MiB = spilled = failed),
  memwatch per job. B1f (frequency-fidelity) renamed and labelled NOT-mesh-convergence in its
  outputs. Five-job B1 mesh spec proposed in `.b1/b1_mesh_night_insert.yaml`, NOT queued —
  owner approves GPU slots first. Heavy raw intermediates (replay pools ~40 MB JSON, dry-run
  meshes ~56 MB .msh) left uncommitted, reproducible from the committed dry-run command.
- **Scoring-truth addendum applied (2026-11-18, carrier
  `hornfab_patches/SENIOR_DIRECTIVE_2026-11-18.md` §5).** Confirmed in the cloud against
  `b6d3ba4`: v9 corridor-mode ripple-mask bug at `hornlab_search/objective/scalar_v9.py:493`
  (passes `hi - lo` as the inspected angle — a 70-90° corridor scores only ±10°). **All v9
  corridor-mode second scores are now marked PROVISIONAL** (decision packet, plan §10.1,
  handoff §9.3/9.11): no ranking, winner-pick or queue decision from them until the owner
  settles the ripple inspection-region policy (preferred edge / guaranteed minimum edge /
  declared seat zone / other). `scalar_v9.py` untouched while the uncommitted other-author
  edits exist; any fix becomes a NEW versioned objective identity. v7, the throat sweep and
  B1/B1f are unaffected. The scoring-truth track (PR-A..F proposals, qLogNEI/qLogNEHVI later,
  BO `freeze_metric_policy` accepts v4/v7 only) folds into the plan as one track; the throat
  agent's isolated clone runs the read-only evidence E1-E4 into the carrier
  `evidence_scoring_2026-11-18/`. **Follow-up (same day): the owner answered the ripple
  policy — `preferred_edge` — and the fix is objective v10, draft PR #68
  (`feat/objective-v10` @ `2ecfdd5`, verified stacked on this branch, base `ccr-260b4b76-fi6b8j`,
  to be retargeted to `main` after PR #67; 4790 passed / 40 skipped / 4 known failures, none
  new). v9 corridor scores remain PROVISIONAL for decisions in this branch until v10 lands
  canonically; still gated: `0007` (Klangfilm H/V digests), v10 rip tolerance/weight, the
  throat-block landing target, and the GPU onset sweep.**
- Commit/coverage note: this entry's code lands in the same push (C1 in
  `feat(tools): night truth`, C2 in `feat(analysis): data-agreement gate`); the queue file is
  untracked (`runs/`), so the queue edits travel as the held-note above, not as commits.


## 2026-11-17 (acoustic-truth lane) — WP1–WP3 hardening pass (independent review + reproduction)

- Two read-only lanes (static compliance review; independent fresh-input reproduction) audited the
  WP0–WP3 commit `f5db35e`. Every headline claim reproduces on inputs the authors did not use:
  2 new c1 corners (bias −0.0174/−0.0282 mm, p99 0.133/0.125 mm, rank 4, FABLE pass); parity on 2
  fresh stored winners 0.000e+00° / 0.0/8.882e-16 dB; identity Δ exactly 0.0; v700 scenario J exact;
  stored response/best hashes unchanged before/after; determinism diff = `meta.utc` only.
- 24 repairs applied to the three tools + test files (no measured value changed, re-verified):
  `brief_truth_replay` hash guard now snapshots **before** any read in all three subcommands (was
  post-hoc in scenarios/grid → the guard could not fail), grid skips one-sided design dirs as typed
  skipped pairs (was KeyError abort), identity raises on an empty term set (was vacuous pass), a
  bad-v9 brief prints one typed `ConfigError` line and exits 2, `grid_stability.json` gains per-side
  `mesh_hash`/`n_dof`/`mesh_epw` ("same-mesh" now evidenced from stored manifests);
  `crowe_mesh_truth` stores full 64-hex config digests (+short aliases), exits 1 when any case is
  refused, narrows the broad except so tool bugs fail loudly, reuses `geometry/record.py::
  native_points`, divides one-sided Jacobian steps by the achieved step, and is mesher-optional in
  `--existing-mesh` mode (CI-safe); `pattern_quality` refuses a balloon without `balloon_grid`
  (`BalloonGridUnavailableError`, no silent equal-area DI) and renames the censored-width key to
  `censored_legacy_width_deg`; the report CLI requires `--out` and gained a committed `--parity`
  mode. Candidate-YAML tests now load the committed `docs/evidence/home_crowe_v9_offline_2026-11-17/`
  copies, so the load proof runs in a clean checkout.
- Tests **53 → 68** (26 + 22 + 20), 0 failed. Published measured numbers unchanged (identity Δ=0.0,
  v700 J 9.96094006749582/11.398108088494078, c0 p99 0.12630539225424334 rank 4, parity
  0.000e+00/8.882e-16).
- Committed artifacts upgraded: `identity/` and `grid/` JSON/CSV regenerated inside
  `docs/evidence/home_crowe_v9_offline_2026-11-17/` (previously gitignored-scratch only);
  `pattern_quality_readonly` JSON/CSV regenerated + `parity_check.json` added; the three evidence
  docs carry hardening addenda, including the WP3-vs-FABLE reconciliation (60 vs 58 pairs, screen−verify
  sign convention, v7 vs v9 corridor, all-vs-top-28 rank) and the WP2 provenance/identity block.
- Provenance caveat (owner-facing): the v9 scenario J numbers were captured while the working tree
  carried uncommitted concurrent edits to `objective/scalar_v9.py`/`search/evaluate.py`/`config.py`;
  `f5db35e`+this pass do not include them. If that lane commits changed v9 code, re-run
  `brief_truth_replay.py scenarios` before relying on the v9 J columns.
- Owner-gated decisions unchanged: WP5 production-brief choice (corridor vs point, V onset, slope
  weight, dead band, `preferred`-in-bounds semantics); WP6 pilot scheduling.

## 2026-11-17 (local orchestrator, stage 5) - Pre-approval checks on the 14 changed proposals

- `tools/shape_check.py` on all 14 changed `__space_v1` proposals: **14/14 mesh, under their screen
  DOF cap, fit their brief envelope, round coupling matches the driver exit** (exit 0; log
  `scratch/fable_architecture/.evidence/shape_check_proposals.log`).
- `tools/search_preflight.py --from-runs <newest same-name run>`: exit 0 everywhere, seed in its own
  box everywhere. **`hl__crowe_x_osse_cd_v7` is `no_headroom`** (seed hash equals the prior best), so
  its bounds trim must be declared a refinement (warm_start + reason) or it re-tests the optimum.
  **`history_unusable` on every lane with history** ("objective version/brief mismatch (run v7, this
  config v7)"), so the expected in-basin hits cannot be computed - question appended to
  `NOTES_FOR_SENIOR.md`, not improvised.
- Same-name runs are not always the run under the lane's current brief; §1's link verdicts are
  scoped to "newest same-name run" in `OWNER_DECISIONS_PACKET_2026-11-17.md` §9.

## 2026-11-17 (local orchestrator, stage 5) - Data agreement rejects every geometric link; 29 proposals

- `space_card.recommend()` now carries `data_agrees` from `links.py` on each lane's latest run. Of 20
  link proposals with a real run behind them, **all 20 are `false`** (`hl__crowe_x_osse_cd_v7`
  `g_wrap_deg`, `hl__osse_rrect_fold_warm_v7` `n`/`k`, the tritonia/twinray/ath/atlas pairs, ...).
  The links in the already-reviewed Crowe and fold-warm proposals are therefore **withdrawn**;
  the fold-warm `a0_deg` fix (18 -> 17, seed shift 0) remains. Only the `_w1` variant keeps its
  links, flagged `unknown` (no run) and needing a run or a 2-run A/B.
- 29 proposals in `scratch/fable_architecture/space_cards/proposals/` (12 apply a change, 17 are
  "no change justified"); originals untouched, nothing applied. Biggest: `atlas__ath_core`
  14 -> 13 keys with `L_mm.hi 520 -> 436.8`, `a_deg.hi 80 -> 66` (box outside 37/96 -> 4/32);
  `atlas__core_law` sigma0 0.25 -> 0.05; `hl__lecleach_iwata_ar_landscape_smooth_v7` two bound
  raises + sigma0 0.20 -> 0.10. Every proposal keeps the incumbent seed (seed shift 0.0 mm).
- `b3_soft`: the senior-pass `g_theta_h1_deg.hi 60 -> 55.3` trim does NOT reproduce at the handoff's
  96-point box (top slice 9/19 = 47 %, under the trigger); it is sampling-sensitive and now needs
  owner judgement rather than an automatic trim.
- `OWNER_DECISIONS_PACKET_2026-11-17.md`: C1-C6 with what each changes, the proposal table, the
  categorical split (ath_core + 4 rear_density -> 3 configs each = 15 files), cross-family residuals
  (biradial -> fold-warm RMS 31.8, depth 83 mm away; tritonia_v9 -> biradial RMS 4.2), and the
  frequency counts actually in use (screen 12 / verify 25 / final 36).
- No config, brief, bound, envelope or queue changed; no GPU job started.

## 2026-11-17 (local orchestrator) - First-session verification on the Windows checkout

- Branch `ccr-260b4b76-fi6b8j` (PR #67). Handoff §2 test list: **187 passed** (log
  `scratch/fable_architecture/.evidence/verify_20261117/pytest_targeted.log`). Full offline suite:
  **8 failed / 4557 passed / 22 skipped**. Triage: 2 load flakes (both pass alone), 4 pre-existing on
  `main` and NOT in the handoff's list of three (`test_objective_v8` `oa_excess_raw` from `4db1453`;
  `gui/study_jobs.py` Popen; 2 `run_bo_arm` wrapper tests - those files are unchanged on this branch),
  2 branch-caused and repaired (`protected_lanes.yaml` in the brief glob; the QD generator-links test
  now asserts the WP 0.2 reduction instead of the removed refusal).
- Code (opt-in/additive, verified by the orchestrator): `search.record_gate: shadow|resample`
  (absent = today; shadow adds exactly `record_margin_mm` + `record_gate_agrees`; resample replaces an
  outside-record candidate before evaluation, seed never replaced, strict path untouched);
  `space_card.recommend()` `data_agrees` (no `link` action when the data disagrees);
  `--mode finalist` wired in `cli.py` (run/search/export-step) and GUI `SEARCH_MODES`, with
  `screen`/`verify`/`final` specs pinned unchanged.
- Evidence `scratch/fable_architecture/EVIDENCE_VERIFY_2026-11-17.md`: U3 CPU 8/8 variants mesh on both
  candidate hosts; record shadow over the 22 most recent lane runs (2055 designs) = **0
  `record_inside_but_refused`**, 28 `record_outside_but_ok`, 429 `record_failed` (all `route: null`,
  concentrated in rosse_rect r120/r50 and the two klangfilm_lame runs).
- Stage 5 cards: 29 cards + `shared_map.md` + `summary.json` in
  `scratch/fable_architecture/space_cards/`. 22 configs could not be built: 12
  `examples/typologies/walls_relieved/*/*_w1.yaml` have `brief_file: '../../briefs/...'` one `../`
  short (12 queued live-night jobs - flagged, not edited); 10 generator-route lanes are refused by
  `DesignSpace.from_config` (`unknown rows type` for rosse_rect/rolled_rect/rolled_rect_pucker/
  crowe_panel/klangfilm_lame) although the mesher registry accepts them (pre-existing).
- Committed the four reports that existed only on this machine: `A4_GRID_INDEPENDENT_SCORE.md`,
  `A5_SOLVER_CALL_TIMING.md`, `A9_CORRIDOR_VS_TERM_SET.md`, `X1_ADDENDUM_KLANGFILM_PROVENANCE.md`
  and the `.a4/` + `.a9/` script/output folders (force-added past `/scratch/`).

## 2026-11-17 — Acoustic-truth master plan: WP0–WP3 implemented (CPU/read-only, no GPU)

- Owner master plan saved at `docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md` (+ INDEX /
  knowledge-hub links). WP4 optional (not done); WP5/WP6 owner-gated. No GPU job started, queued or
  touched; the live GPU search (`runs/20261115T020650Z-screen-22931c` → hifi queue handover) was only
  observed, never interrupted.
- **WP1** `tools/analysis/crowe_mesh_truth.py` (no-solve CPU tool): 12-case CROWE V2A law vs actual BEM
  inner wall. Worst prescribed p99 **0.1286 mm** (`area_bias_low`; dense 97×73 scan max 0.2195 mm,
  `u50_low`), signed bias −0.019…−0.027 mm (mesh slightly inside law), native floor p99 0.0142–0.0243 mm,
  FABLE v2 relative rule 12/12 pass — the absolute p99, not the flag, is the result. Resolution study on
  c0: epw 6/9/12 → p99 0.126/0.080/0.071 mm, so the residual is mesh discretisation/surface fit, not a law
  defect; no mesher change needed for V2A. Mesh-surface rank 4/4, max pairwise |cos| 0.19 (L > H >
  area bias ≈ u50), topology clean (0 bad open/nonmanifold edges, source tag `SD1D1001`, 36×36 mm section,
  shell stand-off median 3.00 mm). 21 offline tests incl. a stored c0 quarter-mesh fixture
  (`tests/fixtures/crowe_v2a/c0_quarter_screen_8k`, force-added past the `*.msh` ignore like the dual-Lamé
  meshes). Evidence: `docs/evidence/CROWE_V2A_SOLVER_SURFACE_TRUTH_2026-11-17.md` +
  `docs/evidence/crowe_v2a_geometry_truth/`.
- **WP2** `hornlab_search/metrics/pattern_quality.py` + `tools/analysis/pattern_quality_report.py`
  (report-only; no objective/metric file touched): legacy outermost vs boresight-connected −6 dB width,
  disconnected islands, off-axis excess at the existing v7 H12 threshold, censored statuses, canonical
  sin(theta) balloon DI. 18 fixtures (legacy-vs-connected distinction, censored, omni DI=0, weighting
  difference…). On 3 stored winners legacy/DI parity: 0.000e+00 deg / 8.882e-16 dB. Evidence:
  `docs/evidence/PATTERN_QUALITY_READONLY_2026-11-17.md` + `docs/evidence/pattern_quality_readonly/`.
- **WP3** `tools/analysis/brief_truth_replay.py` (read-only): legacy identity replay exact — Crowe
  ES-600 16.918/6.836 and Klangfilm 22.782/8.924 reproduced to 6 dp, Δ=+0.000e+00; five NOT-QUEUED v9
  corridor candidates (`scratch/home_v9_offline_2026-11-17/`, committed copies in
  `docs/evidence/home_crowe_v9_offline_2026-11-17/`): dislope is 77 %/92 % of v9 J at 0 target, slope-0
  collapses J to 2.1727/0.9404, corridor `preferred` is not scored inside bounds (h80flat ≡ h90_70);
  grid stability on 60 same-mesh screen/verify pairs: 18-vs-29 sd 0.208 (top-28 0.112), rank
  0.986/0.893; interpolated 58/116 sd 0.193/0.190, rank 0.991/0.958; interpolation removes grid noise,
  not acoustic resolution. 14 tests incl. cross-version pooling refusal + v9 `bw8k_floor` refusal.
  Evidence: `docs/evidence/HOME_CROWE_V9_OFFLINE_CANDIDATES_2026-11-17.md`.
- OPEN (owner): WP5 production-brief decision (corridor vs point, V onset, DI slope weight, dead band);
  WP6 pilot scheduling is a separate authorization. OPEN (semantics): v9 corridor `preferred_deg` is
  unscored inside `[min,max]` — decide whether preferred should contribute in-bounds.

## 2026-11-17 13:58 ET — owner-directed queue priority

- Owner directed stopping the non-improving `cont_p80_athcore_corelaw_200` to advance the home-hi-fi jobs. The exact search process tree was stopped; existing run rows in `runs/20261115T020650Z-screen-22931c` were preserved. Runner recorded exit 1, performed lane cleanup, and live-reloaded the queue.
- At 13:58 ET `hifi_verify_rosse_r50_20261117` started; six hi-fi verification jobs then four 15-evaluation home-range pilots are first in the live `runs/nights/cd_rrect_2026-11-17.yaml`. The current job and subsequent results must be checked in the live queue log; start is not completion.


## 2026-11-17 (senior pass) - Orchestrator handoff + first parameter-space proposals

- `scratch/fable_architecture/ORCHESTRATOR_HANDOFF_2026-11-17.md`: rules, inventory, first-session
  verification commands, stage-5 workflow, ordered remaining tasks, owner decisions.
- Proposals (not applied) in `scratch/fable_architecture/space_cards/proposals/`: Crowe 9 -> 8 knobs,
  bad box share 23 % -> 6 %; ext-throat sigma0 0.20 -> 0.10 (predicted bad 34 % -> 12.5 % at 0.15);
  fold-warm 18 -> 15 knobs; b3_soft one bound trimmed. Seed shift 0 on all four.

## 2026-11-17 (senior pass, code) - Shared-descriptor translation between families

- New `hornlab_search/geometry/translate.py`: seed family B from family A's shared descriptors
  (records only). Biradial seed -> fold-warm: width exact, depth 70 mm short (fold-warm's box cannot
  reach it); -> ext-throat: one step then every larger step leaves the envelope (consistent with its
  58 % outside box). Residuals are reported, never hidden. `tests/test_geometry_translate.py` 3 passed.

## 2026-11-17 (senior pass, code) - Stage 5 core: geometric parameter-space identifiability, space cards, proposals

- New `hornlab_search/geometry/sensitivity.py`: for any native or generator config, finite-difference
  surface and shared-descriptor Jacobians in unit coordinates at Sobol points; knob labels
  (`weak` = whole range moves no point > 1 mm, the mesher fit); coupling, effective dimension,
  greedy chain-free link proposals (weaker knob follows); feasible steps from the seed; box
  feasibility by slice; a linear envelope-margin constraint (WP 5.4); and the predicted
  bad-candidate rate of the first CMA generations per sigma0 - all from records, no mesh/GPU.
- `geometry/record.py` grid route now resolves exactly like `mesh/build.py` (Klangfilm H/V core,
  rows recipes, explicit bodies).
- New tools `space_card.py` (cards + `shared_map.md`) and `space_propose.py` (proposed
  `__space_v1.yaml` + before/after + seed shift). Cards for five home lanes in
  `scratch/fable_architecture/space_cards/`. Findings: ext-throat 58 % of the box outside the
  envelope, predicted bad rate 6 % at sigma0 0.10 vs 34 % at 0.15, one linear constraint explains
  it (R^2 0.89, width binds 65 %); fold-warm 18 searched / ~12 effective, `a0_deg` weak (0.39 mm),
  OSSE n~s and k~a_deg parallel; Crowe top 20 % of g_L_mm and g_s mostly refused; b3_soft top
  20 % of g_theta_h1_deg refused.
- Merged WP 2.1 (helper): `finalist` tier resolves in config (2x screen DOF cap, 36 freqs, budget
  profile `fidelity-ladder-10`); CLI/GUI/evaluate wiring open. Helper flagged: today's screen grid
  is 12 points (18 only with `screen_extra_hz`), verify 25 (29+ only with
  `verify_points_per_octave`) - the plan's "18/29" is brief-dependent.
- Tests: `tests/test_geometry_sensitivity.py` 8 + geometry suites 27 passed; config tiers 78 passed.

## 2026-11-17 (senior pass) - Plan §10 implementation-status table added

- `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` §10 lists every WP's status, file and what still needs
  the Windows machine or an owner decision.

## 2026-11-17 (senior pass, code) - WP 4.2/4.3 decision rules coded before any solve

- New `tools/analysis/u3_authority.py`: the equivalence rule (1 deg per band, both planes, bands
  0.7-1.1 / 1.1-2.5 / 2.5-5.5 kHz; optional dJ vs floor) gates the variants; the authority rule is
  U3's unchanged (>= 3 deg intended plane, other plane < half; steering/diagonal try both planes).
  Written before any data exists, so the lines cannot drift after seeing results. 3 tests pass.

## 2026-11-17 (senior pass, code) - WP 4.2/4.3 made runnable: explicit record body + U3 job writer

- New `design/generators/record_body.py`: `rows.type: canonical_record_v2` recipes carry the record
  points inline with their digest; resolve/validate re-check the digest (a silent geometry change
  is refused). Registered in the explicit-body tuples of `grid.py` and `mesh/build.py`.
- New `tools/analysis/u3_jobs.py`: for `runs/<run>/designs/<hash>` writes `control.yaml` + 7 variant
  configs (seed = record body) and `manifest.json` (digests, validity, reach, margins). A control
  config loads and meshes to the host's box (560 x 350 mm on the biradial seed).
- GPU next (owner C6): `hornlab-search run --config <out>\\control.yaml` at verify fidelity, compare
  with the stored response (WP 4.2 rule: mean BW within 1 deg per band, dJ within the floor); only
  then the 7 variants (WP 4.3). Tests: 2 new + 1 mesher test pass; grid/generated suites unchanged
  (the one pre-existing failure only).

## 2026-11-17 (senior pass, code) - One-command evidence driver for the Windows checkout

- New `tools/analysis/senior_plan_evidence.py`: record shadow + rescore + floor + U3 CPU variants on
  each named lane's best stored design, into `scratch/fable_architecture/.evidence/<utc>/`.
  Smoke-tested on a synthetic biradial run (2 passed). Finding: the "vertical timing -> 480 mm"
  variant fits the acoustic box but is 6 mm over a 480 mm brief in the build box (3 mm wall) - the
  envelope-convention decision decides whether it is admissible; 460 mm passes both.

## 2026-11-17 (senior pass, code) - Stage 5 WP 5.2: categorical knobs in continuous boxes are flagged

- `config.categorical_searched_keys` + a load-time WARNING when a native config searches
  `morph_target` / `morph_allow_shrinkage` / `gcurve_type` inside a continuous box (rounded =
  staircase for CMA/BoTorch). Warning, not refusal, so running configs are untouched. Shipped
  configs that trigger it: `examples/typologies/ath_core.yaml` and the four
  `examples/studies/rear_density_2026-11-13/ath_like_rear*.yaml` (`morph_target`). Recommended
  (owner): split them into one config per morph target.

## 2026-11-17 (senior pass, code) - Stage 7 WP 7.1: protected lanes as data; watchdog only advises on them

- `examples/protected_lanes.yaml` (status: proposed, awaiting owner C5): the A11 lanes with
  owner-request evidence; the 4 no-evidence lanes are NOT listed.
- `tools/run_campaign_night.py`: jobs whose config stem is listed are `protected`; a watchdog
  verdict on them writes `=== WATCHDOG ADVISORY (protected lane) ...` once and does NOT kill.
  Night YAML `protected_lanes: <path>` picks another file; `protected_lanes: false` turns it off.
- **Behaviour change once merged:** live nights read the default file automatically, so refusal
  storms in protected lanes (e.g. a mis-sized sigma0) are logged, not stopped. Owner can opt out
  per night. Tests: night-runner suites 86 passed.

## 2026-11-17 (senior pass, code) - Stage 1 WP 1.4/1.5: rescore and noise-floor tool

- New `tools/analysis/rescore_identity.py`: `rescore` (history under one brief, per-lane bests,
  unscorable designs reported) and `floor` (frequency part of the floor from study screen/verify
  pairs: sd of screen-verify J over all and top-N, Spearman). Uses the parity-exact replay, so v9
  `score_grid` and `constancy` apply when the brief declares them.
  `tests/test_tools_analysis_rescore_identity.py` 3 passed. Needs `runs/` (Windows) to produce numbers.

## 2026-11-17 (senior pass, code) - Stage 3 WP 3.3/3.4: record shadow gate tool

- New `tools/analysis/record_shadow.py`: offline shadow of a record-based envelope gate. For each
  design in the given runs it rebuilds the record (pre-mesh refusals re-materialised from
  `_knobs`), writes digest/descriptors/margins (acoustic and build-box) to `records.jsonl`, and
  counts disagreements with the stored outcome. No hot-path change; the switch stays an owner
  decision after the report. `tests/test_tools_analysis_record_shadow.py` 2 passed.
- To run on history (Windows, needs `runs/`):
  `.venv\Scripts\python.exe tools\analysis\record_shadow.py runs\<run> ... --out scratch\rec_shadow`.

## 2026-11-17 (senior pass, code) - Stage 0 WP 0.5: GRID extent false refusals measured and fixed

- T4 (`scratch/fable_architecture/.t4/t4.py`, gmsh, no solve; 64 Sobol knob vectors per config):
  `grid_ellipse_mod` had 3/3 pre-mesh envelope refusals that the real mesh fits (false refusals),
  0 misses; `grid_ellipse` 0/0. On the home landscape brief these bounds never reach the box, and
  no home lane uses the generic radial GRID route, so the realised loss on home campaigns is ~0.
- Fix (`design/generators/grid.py::envelope_extents`): width/height per plane
  (`2(max r cos phi + t)`, `2(max r sin phi + t)`) instead of `2(max r + t)` on both. Re-measured:
  1 false refusal left (1.5 % over by the estimate; the radius-field mouth modulation), 0 misses.
- Tests touching the estimator: 267 passed; 3 failures all pre-existing at `1d6ebc8`
  (`test_grid_self_approach...`, two `test_gui_preview_shape` tests).

## 2026-11-17 (senior pass, code) - Stage 4 WP 4.1: U3 freedoms as record edits, meshed for real

- New `hornlab_search/geometry/edits.py`: pinned-throat radial edits; the seven U3 variants; U2
  validity; `record_to_grid` hand-off. Installed libGLU in the container so gmsh runs: control
  plus all seven variants of the biradial seed build real point-grid meshes.
- CPU result (`scratch/fable_architecture/U3_RECORD_EDITS_CPU_2026-11-17.md`): all 8 valid; vertical
  timing reaches 460/480 mm (failure line not met); 3/7 variants reach >= 5 mm RMS outside the last
  5 % (termination split is lip-confined; steering small on this seed). Line not moved.
- Tests: `tests/test_geometry_edits.py` 9 passed (one real-mesh test, `requires_mesher`).
- With gmsh available, re-ran the 11 mesh tests that failed earlier: all pass except
  `test_grid_self_approach_classifies_invalid_geometry_and_is_memoized`, which fails identically
  at `1d6ebc8` (pre-existing: the test's context has no solve cache root).

## 2026-11-17 (senior pass, code) - Stage 1 WP 1.2: dense-grid score identity for objective v9

- New `hornlab_search/metrics/dense_grid.py` (A4/N3 method packaged: PCHIP in log f, uniform
  58/116/232 points inside the solved range, pressures dropped, no extrapolation). Objective v9
  takes an opt-in `objective.score_grid: {kind: dense_log, points: N}`; when declared, metrics are
  re-derived on the dense grid with the production DI rule (`metrics_from_response`) before
  scoring; it rides `to_block`, so it is part of the score identity. Absent = unchanged. Replay
  inherits it through the v9 dispatch. Plan: 58 points for v9, 116 with constancy (N3).
- Tests: 7 new; scoring/replay/config suites 99 passed.

## 2026-11-17 (senior pass, code) - Stage 1 WP 1.1: opt-in constancy term in objective v9

- `objective.constancy: {mode: strict|slope, weight, tolerance[, slope_max_deg_per_decade]}`,
  ABSENT by default (J unchanged; terms carry `constancy: 0.0`, like `hf_floor`). Declared by a
  brief only, never from a family name. Strict reproduces S1's formula exactly
  (`mean(d^2)/25` == raw/100 at tolerance 0.25); slope mode forgives a steady narrowing up to the
  declared deg/decade. Counted in `worst_valid_v9_j`. Owner decision C2 picks whether any home
  brief turns it on. Tests: v9 + GUI corridor + replay + config suites 73 passed (the pinned
  optional-key test now lists `constancy`).

## 2026-11-17 (senior pass, code) - Stage 3 WP 3.1/3.2: canonical surface record module

- New `hornlab_search/geometry/record.py`: the N1b/X4-validated contract-v2 sampler packaged
  (65 arc-length stations x 61 azimuths, mm), generator routes without meshing (native via
  `resolve_geometry`, grid, rolled, Klangfilm), record digest, contract §7 descriptors, signed
  envelope margins (acoustic and build-box views), typed refusals (CAD, ports, zero meridian,
  non-monotone azimuth). Read-only: no identity, solver or stored-row change.
- `tests/test_geometry_record.py`: 11 passed (analytic elliptic cone: area, shape index pi/4,
  wall angle; determinism/digest; refinement; rollback; refusals; real hypex seed without mesh).
- Ownership of the new `geometry/` package needs orchestrator assignment (CLAUDE.md table).

## 2026-11-17 (senior pass, code) - Stage 0 WP 0.2: search.links now work with generator blocks

- `GeneratedSpace.apply_knob_links` applies links in KNOB space before `materialize`;
  `search.links.reduce_space` builds a reduced GeneratedSpace (linked knobs leave the CMA
  dimension, seed recomputed); `apply_links` is a no-op on generator designs; the config refusal
  is lifted. No links = byte-identical default. The old "refused" test is replaced by real
  hypex-config tests. `tests/test_search_links.py` + neighbours: 88 passed.

## 2026-11-17 (senior pass, code) - Stage 0 WP 0.1 refusal taxonomy and WP 0.4 parity replay landed

- WP 0.1 (`search/evaluate.py`): post-mesh envelope violations are now kind `invalid_envelope`
  with error text `post_mesh: ...` (3 sites; were `invalid_geometry`); family errors such as
  `GeneratorError: invalid_envelope: ...` now map to `invalid_envelope` through
  `_generator_error_kind` (was a bare `startswith`). New rows only; penalty values unchanged
  (graded penalty falls back to the flat value without an overshoot). `tests/test_search_refusal_taxonomy.py`.
- WP 0.4 (`objective/replay.py`): replay dispatches objective v9 (V9Params, objective_v9,
  resolve_v9_weights) and regenerates metrics with production `metrics_from_response`
  (sin-theta balloon DI) instead of plain `compute_metrics`. `tests/test_obj_replay_v9_parity.py`.
- Merged the helper lane's WP 0.3/0.6/0.7 (cohort gate by declared version; night-runner restart
  idempotency; watchdog best_J and outcome counts).
- Tests (Linux container, system Python): new + replay + v9 suites green; refusal-kind suites green
  except 11 mesh tests that fail identically without these changes (libGLU missing for gmsh here).

## 2026-11-17 - Stage-0 fixes WP 0.3 / 0.6 / 0.7 (offline, no GPU, no solves)

- **WP 0.6** `tools/run_campaign_night.py`: `run_night` seeds `done` from an existing
  `queue_state.json` (same night only; not with `--only`), so a restarted runner never re-runs a
  finished job. Absent file: unchanged; unreadable/foreign file: warning, unchanged behaviour.
- **WP 0.7** same file: a watchdog stop now recomputes `best_J` from that run's `search.ndjson`
  (lowest finite objective among ok rows) and adds an additive `outcome_counts` field
  (ok / invalid_geometry / invalid_envelope / mesh_too_large / solve_failed / other) plus a note.
  Historical `summary.jsonl` rows are not rewritten; other records gain no new keys. The
  `pin_min_valid` / `pin_frac` / `pin_count` exposure part of the plan row is not done here.
- **WP 0.3** `hornlab_search/bo/cohort.py`: the hard `objective_version != 4` gate is now an
  identity check: R0 `objective_version` must be known and equal across rows (or equal to the
  optional `objective_version=` argument), and equal to S0's when S0 stores one. v4 cohorts behave
  as before; uniform v7 cohorts pool; mixed/missing refuse as `incompatible`. Target, weights,
  `metric_source` and score/metric policy claims were already compared across rows.
  Tests: `tests/test_night_runner_restart_and_stop_truth.py`, additions in `tests/test_bo_cohort_gate.py`.
## 2026-11-17 (senior pass) - Fable senior review: generator decision taken, architecture and staged plan written

- **Senior (high-thinking) reviewer pass** picking up for Fable; not the owner. Docs only, HEAD
  `1d6ebc8`: no code, config, queue, solve, mesh build or pytest. Two new documents in
  `scratch/fable_architecture/`: `FABLE_SENIOR_REVIEW_2026-11-17.md` and
  `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md`; they now take precedence over the handoff.
- **Lane review confirmed in substance.** Amended: U3 freedoms are tested as canonical-record edits
  through the point-grid route (after a new 2-solve record-route equivalence check) before any are
  built, and then only inside the specialist whose construction carries them; U1-bis deferred with a
  reopen condition and a predeclared parameter cap; X1 ruled accepted for geometry, open for metadata.
- **Reserved decisions taken:** plural specialist generators, one shared description (record v2); no
  unified backbone or common carrier; U2 closed, B3/B5 withdrawn; no cross-family model (BoTorch within
  lanes, CMA-ES builds rows, seeds from stored bests); watchdog stays a reviewed safety net; B1 design
  selection decoupled from the owner's scoring choice (union of v7 and v9-placeholder top fives).
- **Corrections registered:** "80x50 is physically unreachable" is a measured observation on sampled
  designs, not physics (KH-001 scopes Keele to Bi-Radial); constancy is a brief-declared CD intent,
  never a family default (owner lock: no classification by family name); the noise floor is per score
  identity (v9 0.113 J vs v9+constancy 0.205 J at the top, N3); the Klangfilm Phase B result
  (construction-level core moved the beam 25-40 deg; b3_soft 6.401 -> 2.819) was missing from the
  corpus; `A4_GRID_INDEPENDENT_SCORE.md`, `A5_SOLVER_CALL_TIMING.md`, `A9_CORRIDOR_VS_TERM_SET.md`
  and `X1_ADDENDUM_KLANGFILM_PROVENANCE.md` are cited but not in git.
- **Plan:** stages 0-8 with exit gates. Stage 0 (nine truth fixes, all re-verified live at HEAD) and
  the record module (stage 3.1) are ready to become task files now with no owner input. GPU before
  matched reruns: B1 20 + equivalence 2 + B2 12-16 = 34-38 solves.
- **Owner decisions open:** C1-C4 scoring (cards say what each changes; no recommendation, per the
  standing instruction), C5 protected list, C6 budget (recommended order B1, equivalence, B2, B6),
  provenance rule (recommended: gate on a record digest of the generated surface, keep the kernel
  digest informational), envelope convention (recommended: record acoustic and build boxes; brief
  names which one gates), commit the four missing reports.
## 2026-11-17 05:0x - Stage 0 WP 0.8 (doc truths + E-012 guard) and WP 0.9 (recipe metadata, additive)

- **WP 0.8.** `tools/night_queue/queue.ps1` header corrected: a started night IS live-reloaded
  (reorder / insert / remove, PAUSE / STOP; `run_campaign_night.py` ~1233-1250; only `--no-live`
  reads once). `budget_counts` semantics written in `docs/reference/SEARCH_CONFIG_KEYS.md` from
  `search/cma.py`: cache hits are free in both modes, refusals consume budget under `new`, are free
  under `valid`, solve/metrics failures always consume. `flat` (ddof=2, `metrics/smoothness.py`) vs
  `flat_cv` (ddof=0, `objective/scalar_v7.py`) documented in the new
  `docs/reference/OBJECTIVE_STD_CONVENTIONS.md` (docstring note in `smoothness.py`); NO math changed
  and no objective code touched. E-012 guarded: `design/families.py` `to_mesher_config` now refuses a
  design `mode` key that contradicts `brief.mounting` (GeometryInvalidError) instead of silently
  overwriting the enclosure flip; freestanding runs and all shipped configs are byte-identical.
- **WP 0.9 (metadata only; digest rule still owner-pending).** New `design/recipe_meta.py`;
  `GeneratedSpace.provenance` now carries `recipe_meta` (schema `recipe_meta_v2`: termination kind
  where knowable else explicit `None`, wall thickness the mesher actually uses with its source -
  mesher default 6.0 mm freestanding / 0 enclosure, grid route 3.0 mm - and source-cap
  shape/radius/curvature/angle, radius resolved only on the point-grid route). It is NOT an input of
  `Design.hash()`, mesh/solve hash or `config_sha` (tested), and `evaluate.py` copies only a fixed key
  list into dataset provenance. Gap: plain-family (non-generator) designs have no generator block, so
  they get no metadata until `search/evaluate.py` `_persist` calls `recipe_metadata` (other agent's
  file; request in NOTES_FOR_SENIOR).
- Tests: `tests/test_design_recipe_meta.py` (7). gmsh-dependent tests fail in this container
  (libGLU missing) as before; no GPU.
## 2026-11-17 - WP 2.1: finalist fidelity tier resolves in config (offline, no solves)

- Added mode `finalist` additively: `FREQ_GRIDS["finalist"]` = 36 points on 300-16,000 Hz (>= 29;
  same band edges as verify, clipped to `band_hi_hz` like the others), `MODES` gains `finalist`,
  `types.Mode` likewise. `MeshSettings.dof_cap("finalist")` = `mesh.dof_cap_finalist` when the YAML
  sets it (new optional key), else `FINALIST_DOF_FACTOR` (2) x `dof_cap_screen`. `mesh_spec("finalist")`
  and `solve_spec("finalist")` therefore carry their own max_triangles, f_max, freqs and mode, so the
  finalist mesh and solve identities are distinct. Balloon density follows verify.
- screen / verify / final specs, hashes and `config_sha` are unchanged (absent key leaves `raw`
  untouched; `tests/test_config_fidelity_tiers.py` pins this). Budget profile `fidelity-ladder-10`
  (10 screen + 10 finalist-tier solves counted as `verify_calls`, B1 shape) added to
  `studies/package.py`; existing profiles unchanged.
- Findings: frozen screen grid is 12 points (18 only with `screen_extra_hz`) and frozen verify is 25
  (>= 29 only with `verify_points_per_octave`); the plan's 18/29 describe configured briefs, not the
  frozen defaults. The pre-existing `final` mode (36 pts, `dof_cap_final`) is untouched and is NOT the
  finalist tier (its cap equals screen in most examples).
- OPEN wiring: CLI `--mode` choices (cli.py, gui/jobs.py SEARCH_MODES) still list screen/verify/final;
  `evaluate.py`/runner dispatch of `finalist` (evaluate.py:1277 is verify-only, owned by another
  agent); `cli.py:562` and mesh build already accept `mode="finalist"` via `dof_cap`. No example YAML
  sets `dof_cap_finalist` (default 2x is used). B1 itself (WP 2.2) is not run.
## 2026-11-17 07:4x - Queue addition: ten "best J still falling" continuations (+200 evals each), live-reloaded

- Owner asked for the ten GUI "give this run more evaluations" candidates at **+200 solves each if not
  already queued**. None were: no queued job resumed any of the ten run dirs (checked both live night
  files for the dir ids), so all ten were added as `kind: command` resumes.
- **8 on the GPU night** (`cd_rrect_2026-11-17`), inserted as jobs 15-22 - after the in-flight
  `c_rrect_100w_rc2` repair, before the TuRBO pairs - so the newest owner instruction leads.
  Valid rows before the addition / run dir: `p80x60__ath_core_14in_home700_v7` 171
  (`20261114T015916Z-screen-db8e2f`), `p80x60__ath_core14_corelaw_v7` 89 (`...020650Z-screen-22931c`),
  `p80x60__ext_throat_hvlaw_cov_v7` 113 (`...060011Z-screen-9e3528`),
  `hl__lecleach_iwata_ar_landscape_v7` 80 (`...162516Z-screen-e31b23`), `hl__rolled_es_spiral_v7` 30
  (`...001222Z-screen-b25d61`), `hl__biradial_es_style_v7` 142 (`...090751Z-screen-37b115`),
  `hl__biradial_es_style_smooth_v7` 107 (`...193501Z-screen-f008ad`), `hl__rosse_rect_cd_v7_r50_refine`
  51 (`20261117T053153Z-screen-15f0e4`).
- **2 on the CPU night** (`bo_cpu_2026-11-17`), after atlas: `sab__lecleach_ctrl` 143
  (`20261114T220720Z-screen-88d19c`) and `sab__lecleach_fc540` 142 (`20261114T223630Z-screen-86e077`),
  keeping their original `--backend beat_cpu --cache-dir cache_cpu --dataset-dir dataset_cpu`. A search
  job inside a cpu night inherits `HORNLAB_BEAT_WORKER_DIR=runs/lanes/cpu/workers`, so
  `cli._solve_lock` returns a null lock and the GPU lock is not touched.
- **Resume form is `--budget 200` = 200 NEW evals** (`cli.py:761` prints "budget N new evaluations";
  `refresh_watchdog` converts its own repairs with total-minus-valid, which is the other convention).
  No `--config` is passed, so each resume loads its run's own `config.yaml`; stored vs current
  `config_sha` verified equal for all ten, so none will refuse. Bridge kinds use their own CLI -
  `rolled_rect_cli.py` (spiral, `grid/rolled_rect_pucker`) and `rosse_rect_cli.py` (r50_refine,
  `grid/rosse_rect`); the other six use the generic `hornlab-search.exe`.
- Both files pass `--dry-run` with no MISSING paths: 45 GPU jobs / 3 CPU jobs, no duplicate ids. The
  GPU runner re-reads the file before every job, so the block takes effect when `t_trit80_rc2`
  (running, 29 observations) ends.
- Wall clock of the addition: ~17 h GPU (2.8 / 3.6 / 2.8 / 0.4 / 2.1 / 1.2 / 1.0 / 2.3 h at each run's
  measured s/eval) plus ~1.4 h CPU, on top of the three 300-solve crowns and 13 x 200 walls jobs
  already pending. `queue.ps1`'s 14:30 cutoff only stops STARTING new nights, so this runner drains
  into 2026-11-18 unless the owner trims (`STOP`) or re-orders.

## 2026-11-17 07:1x - Lane review: gate false-PAUSE fixed; klame BO arms are unsupported point-grid designs

- **Both lanes verified on the right queue.** GPU night `cd_rrect_2026-11-17` ran `t_trit80_rc2` under
  `runs/.gpu.lock` (pid 41452, command `study 1ff9fb9cb6d04e358685213206425478`) with worker dir
  `runs/lanes/gpu/workers`; CPU night `bo_cpu_2026-11-17` held `runs/.cpu.lane.lock` (pid 57892,
  `night bo_cpu_2026-11-17`) with `runs/lanes/cpu/workers` and logged `cpu lane: GPU lock and VRAM
  accounting skipped`. `package.json` carries `lane: gpu|cpu` and `studies/lanes.py` takes the matching
  lock, so a CPU arm cannot take the GPU lock.
- **BoTorch recording verified.** `turbo_trit80_rc2`: package `running`, `observation_seq=20` and
  attempts 20 = observations 20 = `screen/search.ndjson` rows 20 = design dirs 20, with per-row
  objectives (best J 4.9386). `launches: 0` is not a defect - it is the GUI-launch idempotency ledger
  (`studies/service.py`); the night executes `studies.cli run --execute` directly.
- **Gate false-PAUSE (root cause + fix).** `runs/nights/<night>/PAUSE` said `foreign GPU-lock holder`
  from 06:42:33 while the lock was our own study; the runner honours PAUSE before every job
  (`run_campaign_night.py:1373`), so all 37 jobs would have stalled after `t_trit80_rc2`. `gate()`
  attributed holders by argv tokens, but a BO arm holds the lane as `study <study_id>`
  (`studies/lanes.py`), sharing no token with `run_bo_arm.py --root ...`. Fix:
  `_study_arm_holder_ours()` resolves that id through the running job's `--root` registry
  (`<root>/studies.sqlite3`); `gate()` gained an injectable `root`. Regression
  `tests/test_night_refresh_gate.py` (4 tests pass). Same file: `refresh()` referenced an undefined
  `young` (a rename to `complete_elsewhere` left it behind), so the "budget covered by a sibling
  thread" deferral would have raised `NameError` and silently killed a deep tick.
- **klame BO root cause: unsupported geometry, not the pipe hang.** `t_klame_turbo100` (1238 s, exit 1),
  `t_klame_scalar100` (1098 s, exit 1) and `t_klame_turbo_cpu` (1521 s, killed after review) all died
  in `build_proposal` after `training rows: 200`. Direct probe: `status=pool_exhausted,
  candidates=0`, counts `{'generated': 24, 'geometry_rejected': 24, ...}`; exception
  `UnsupportedGeometryError: CAD/point-grid designs are unsupported by the canonical radial surface
  sampler` (`bo/data.py:materialize_geometry`). The c200 config is `generator: {name: grid, rows:
  {type: klangfilm_lame_v1}}`, so every Sobol candidate is rejected; the 18-20 min was the 513 x 3
  candidate pool build at ~1-2 s each. The `1482304` stream fix is confirmed good (trit's ~140 KB prep
  JSON packaged).
- **Consequences.** No TuRBO/SCALAR arm can run on a klangfilm_lame (grid/point-grid) config, so the
  backlog's hand-built `c200w` + its TuRBO/SCALAR pair stays unqueued until the BO sampler supports
  CAD/point-grid; CMA `search` on the same config is unaffected (`c_klame_200`: 201 evals, best J
  7.4458). Removed `t_klame_turbo100`, `t_klame_turbo100_rc1`, `t_klame_scalar100` from the GPU night
  file (also stops the watcher re-appending `_rc1`: it needs the job spec present to repair) and the
  dead arm from the CPU night file; `w_klangfilm_lame_curved_v1_200w1` is a CMA search job and stays.
  `runs/` is untracked, so those edits are local state only.
- **Open.** `gpu-clean --lane cpu` returns rc 3 while the GPU lane is live, so CPU jobs record
  `status: blocked` and take one 120 s retry round trip (observed: RETRY `t_klame_turbo_cpu` -> rc 2 ->
  `t_atlas_corelaw_turbo_cpu` start). The CPU lane should not be blocked by a GPU holder.
  Review report (untracked): `runs/nights/refresh/lane_review_20261117T1205Z.md`.

## 2026-11-17 04:1x - Lane review of the Fable corpus handed to the senior reviewer (not a senior decision)

- The **lower-cost continuation lane agent** (not Fable, not the owner) reviewed all 54 documents in
  `scratch/fable_architecture/` (spine read directly; four read-only digest lanes) plus its own
  measured results, and wrote `LANE_REVIEW_FOR_FABLE_2026-11-17.md`,
  `X1_ACCEPTANCE_TABLE.md` and `OWNER_DECISIONS_2026-11-17.md`. Per handoff §8 and the N4 rule the
  generator decision is **reserved to the senior reviewer**; the review's decision set is
  explicitly a recommendation for confirmation, and **nothing is a gated decision** — no pass line,
  threshold, split, frozen contract or brief was changed, and **no code was implemented**.
- Verdict registered: the unified backbone is falsified at its own predeclared gate (U1: 0/5 lanes
  at <= 0.5 mm, 5/5 above 2 mm); the response-model spine is not supported at full J (E1 +
  `E1_FOLLOWUP_WHOLE_SURFACE.md`); construct-then-correct is closed (E2); frequency staging
  (0.124 %) and lane racing (0 %, protected-family violation) are not demonstrated; predictor hooks
  A/B/C fail with 0 strict unbiased designs anywhere. The canonical record is validated (6/6 lanes
  at 65 x 61; 55/55 in `X4_COMPLETION.md`) and ranges-plus-constancy scoring remains the
  best-supported change.
- The four senior-authored position documents (`FABLE_OPTIONS_REVIEW.md`, `ARCHITECTURE_SYNTHESIS.md`,
  `PREDICTOR_AND_WORKFLOW.md`, `VALIDATION_EXPERIMENTS.md`) and the handoff §10 table now carry
  authorship prefaces and evidence-only lane notes; `X1_ACCEPTANCE_TABLE.md` consolidates the X1
  per-test verdict (pass line not met as written, because several exact metadata fields exist in no
  stored recipe - a recipe-schema finding, proposed not decided). Owner menu with **options only**
  (no C1-C4 recommendation, per the owner's instruction) is in `OWNER_DECISIONS_2026-11-17.md`.

## 2026-11-17 03:4x - X3 remaining parts: wavelength scaling lifts V but not H; prior worth ~8 solves

- Scheme 3 (held-out engine), 1,715 designs / 35 lanes / 3 engines. `WL-1` (all 27 lengths times
  `2*pi*f/c`, c = 343 m/s, per-frequency rows) gives lane H/V/DI .785/.880/.809 and engine
  .336/.668/.515; per engine GEN-FF .582/.690/.434, GRID .288/.628/.527, OSSE .425/.770/.499. V is
  >= .6 in 3/3 engines, H in 0/3, so the both-plane line is not met; the within-lane rank line also
  fails on scheme 3 (.489/.500). WL-1 beats its row-matched frequency-conditioned control on GEN-FF
  and GRID (+.09/+.03 H, +.09/+.17 DI) with one OSSE H regression (-.03); without either scaling or a
  frequency channel the same model collapses (-.38 to -2.51).
- Whole-surface descriptors (227 features from the contract-v2 records; 60 N1b-passing designs, six
  lanes) do not beat the matched baseline and cannot be read as a representation verdict: the
  27-number profile baseline also collapses on the same 60 designs (H -.06 vs .75 on all 1,715), and
  no lane can supply the 30 held-out designs the rank line needs. Le Cleac'h excluded, not replaced.
- Learning curve / solve value: sibling-holdout prior alone .621 within-lane rank; local-only reaches
  .618 at 48 designs (aggregate crossing >48), but per lane the prior is matched by 8 solves in 13 of
  23 lanes and >=16 in 10 of 23 (7 of the 13 have a negative prior, so that is a ceiling). Marginal
  value of an extra solve: +.019 rank (8->16), +.006 (16->32), ~0 after 32. Transfer decays with lane
  position .695 -> .575 across chronological quarters. Two cross-group lineage links sit outside the
  fixed sibling map (fold_warm<-morph, 3x klangfilm_hv<-klangfilm_lame), reported but not merged.
  Report `scratch/fable_architecture/X3_REMAINING.md`.

## 2026-11-17 03:2x - X4 completion: sampler validated on five lanes; ROSSE digest drift is validator-only

- Five `.x4` lanes (11 designs each): 55/55 design hashes reproduced and 55/55 pass contract-v2
  rule 2 at 65 × 61 (Crowe worst p99 1.646 mm vs 1.712 threshold; medians <= 0.051 mm), including the
  native rounded-rectangle lane N1b never tested. Labels: family 100 % on all five; typology 100 % on
  three and 96.5-98.0 % on Crowe/biradial, all from verify-mode records that omit the generator block.
  Envelope margins bind (ext W +1.13 mm, ATH H +1.35 mm inside; one-knob corners cross on
  ext/ATH/Crowe); the wall gap does not (+4.10 mm minimum).
- **`hl__rosse_rect_cd_v7` resolved.** The stored `9b040e37...` digest vs HEAD `601056d0...` is a
  validator-only change in `a10e784` (`rosse_rect.py` `validate_shape` `b` floor 0.0 -> -0.10); the
  geometry kernel is untouched. With only the persisted-digest equality bypassed in memory, 11/11
  grids rebuild and match the stored meshes (p99 0.468-0.918 mm, native floor 0.343-0.721, all pass;
  W/H exact; depth difference is the 3 mm rear closure). The stock bridge still refuses the old
  digest; the bypass is a read-only diagnostic.
- Unresolved rematerialisations now: **lecleach only** (no digest, `d6c9abd` H/V change) plus 2 of
  the 11 old Klangfilm sample designs (`e3a1f4a3...`). Part B/D gates are not testable/not run and
  the full 2^k corner scan is not testable. Report `scratch/fable_architecture/X4_COMPLETION.md`.

## 2026-11-17 03:0x - E1 follow-up at full J: response modelling still gives no advantage; the proxy was the illusion

- A3 repeats E1 with parity-exact full J (10 lanes x 10 starts, E1's protocol unchanged; parity gate
  0.0 J and 0.0 term on 2,595 CD rows; E1 reproduced exactly under its own proxy truth). Full-J median
  reveals: score 18.5, score-on-descriptors 18.25, E1 curve head 24.0, nine-term head 18.25, actual
  history 87.25, random 55.25. Part A, Part B and Part C all fail their lines, so E1's composite
  failure criterion is now fully met - it was not under the proxy truth.
- The proxy objective is the identified cause of the earlier proxy-level picture: the same curve
  selector needs 10.0 reveals on cov+DI versus 24.0 on full J, the proxy-best design is outside the
  full-J top decile in 4 of 10 lanes, and cov+DI is only 28.5 % of mean J.
- Error shares of the full-J term head: `diag` 0.287, `dislope` 0.228, `cov` 0.211, `load` 0.105,
  `flat_cv` 0.061. Whole-surface descriptors built and versioned (A3-WS-v1, 404 numbers, 60 records)
  but the arm is under-powered at 10 designs/lane; pool vs real absence cannot be separated without
  new solves. Report `scratch/fable_architecture/E1_FOLLOWUP_WHOLE_SURFACE.md`.

## 2026-11-17 (latest) - sigma0/bound-width failure mode measured; guidance into skill + AGENTS.md; no solver code changed

- **What happened:** the Klangfilm b3_soft search (`20261117T070714Z-screen-2dabac`) burned 45 GPU
  evals with ZERO improvement — sigma0 0.25 on global generator bounds over 12 free keys produced a
  refusal storm (24/45 rows at the flat 1000 penalty) and a flat trace. Same config relaunched with
  sigma0 0.10 + seed-centered ±30 % bounds (`20261117T071329Z-screen-e4f90d`) reached best J 2.819
  vs seed 6.401 (−56 %) with 9 refusals. Controlled A/B, only sigma0 + bound width changed.
- **Retrospective** (~80 runs ≥15 valid rows since 11-15, script `scratch/sigma_analysis.py`, table
  `scratch/sigma_out2.txt`): refusal storms track sigma0 × free-keys × bound width (0.22–0.25 on
  wide boxes: 25-48 % median refusal, flat tails 32-45; 0.20 on modest boxes: 1.2 % refusal),
  while refinement at 0.12 near a live basin gains ~8 %. The four corelaw screens flat at J 3.233
  (0.15, 59-100/60-101 evals) are converged-incumbent attribution, not step size.
- **Official grounding** (explorer lane): pycma docstring — sigma0 is the per-coordinate std in
  optimizer units, no default; Hansen tutorial 1604.00772 §1/§5 σ semantics, §B.5 repair warning;
  Practical Hints — x0 ± 2σ0 coverage, local-improvement σ0 ∈ [0.001, 0.1] on [0,10]-scaled vars;
  small-budget note: C stays ≈ I, so sigma0 decides basin sampling. Our `search/cma.py` runs a
  unit box [0,1]^k, so sigma0 IS in per-knob normalized units.
- **Institutionalized (no hardcoding, `search/cma.py` untouched):** measured section + storm
  signature + stage-based starting points added to the `hornlab-search-economy` skill (check 3);
  one `AGENTS.md` routing line requires the preflight sigma sweep before non-trivial queues;
  dated entry in `docs/ISSUES.md`. CMA-ES source citations live in
  `docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md` (plan/** frozen, incl. 12_RESEARCH_BASIS).
- **Also this pass:** `examples/typologies/klangfilm_hv_2026-11-16/configs/b3_soft.yaml` bounds
  moved to seed-centered ±20-30 % windows with all 12 hv-core knobs searchable (parent knobs stay
  pinned — the adapter hard-rejects them in hv_core mode; 5 relaunches caught that one inert key
  at a time before `klangfilm_lame_hv_core_family.py` L41-42 was read). Live b3 run was NOT
  interrupted by the commit.
- **Status:** GPU lane live (b3_soft e4f90d, budget 100); CPU lane free; no queue started or
  changed. Owner decision open: preflight `--strict` sigma gate for nights (NOTES_FOR_SENIOR).

## 2026-11-17 03:2x - Consolidation: preserved refs, docs + H12 landed, worktrees/branches collapsed

- Preservation: 18 `archive/consolidation-2026-11-17/*` tags plus verified bundles in
  `scratch/consolidation_2026-11-17/` (all-refs, both agent branches, a pre-concurrent snapshot, and
  the outer `495e58f` commit); dirty/untracked files and ignored mild render/seed evidence snapshotted.
- Landed: 17 additive docs from the 2026-11-14 handoff (`caa37d0`); H12 opt-in off-axis excess
  (`oa_excess_tol` / `oa_excess_raw`, default off, config_sha preserved) plus its hifi brief
  (`0a451db`). GUI `seed_policy` and the Le Cleac'h saddle code were already on main.
- Cleanup: worktrees 13 -> 2 (main + the live `agent-a527` owner worktree); local branches 29 -> 4
  (`main`, `feat/sab-home-2026-11-14`, `agent-a473`, `agent-a527`). 25 branches were deleted only
  after archive-tag/SHA checks; empty top-level leftovers removed.
- Tests: H12 objective/config/target suites 135 passed. The full offline suite has one pre-existing
  failure, `test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
  (`subprocess.Popen` in `gui/study_jobs.py` since `b019623`), and 22 optional-engine skips; the test
  was not weakened.
- Open (owner): Fix D `0.9` mouth factor; A527 night-runner directivity guard while keeping
  `pin_ignore`; sab-home `rim_sweep_ratio` floor (existing seedV5 uses `-0.18`); A473 v3 configs
  (2/3 fail main's 240 deg stop gate); outer `Hrns/.git` 13.4 GB quarantine; `.hf_stage_hunter*`
  25.3 GB remote verification.
- This push adds this entry plus ISSUES/INDEX/CODE_MAP updates. `configs/b3_soft.yaml` remains
  another lane's uncommitted edit and was not staged.

## 2026-11-17 02:4x - P1 predictor replay: no unbiased pool exists; hooks A, B and the skip test fail

- Strict unbiased designs (solved but not rule-selected): **0 of 8 study lanes**; every solved row in
  the BoTorch studies is a CMA/BoTorch acquisition pick. Six of eight lanes stay under 30 even on the
  cadence-derived upper bound, so the P1 fair-pool replay was **not run** and no optimizer-visited
  substitute is reported as a finding. Report `scratch/fable_architecture/P1_PREDICTOR_REPLAY.md`.
- Biased replay (19 lanes, sibling + engine holdout, all valid rows, stored full J): **A** lane order
  rank correlation vs the lanes' best full J is 0.733 (line >= 0.8, only 1 of 5 true top-five lanes
  recovered); the cov+DI comparator gives 0.944 but is diagnostic only. **B** the predictor's single
  pick beats the first solve in 11/19 (line 13/19) and equals one random stored design (11/19).
  **C** predictor top 8/16/32 beat the first rows 14/16/13, but random draws from the same pool beat
  them 18/17/14 and beat the predictor 10/12/10 - the pool, not the predictor. Skip test: 8.9 % of
  skipped designs are in the lane's true top 10 % (line < 2 %).
- The an7 published result reproduces exactly on its own sample (0.55 / 0.43 / 0.30; 12/19, 9/19),
  which validates the pipeline; the replay differs only in sample, split map and lane order.

## 2026-11-17 06:4x - Owner-directed walls scan: 13 walls-relieved 200-solve continuations queued

- Ran tools/analysis/walls.py across every run of the last ~3 days (81 runs, 41 distinct configs,
  grouped by config name; walls of the family's most recent run). 14 families produced widen
  proposals and 13 walls-relieved successors were generated (`examples/typologies/walls_relieved/*/
  *_w1.yaml`: seed = the family's best J genes, bounds moved exactly per the walls tool's
  widen_hi/widen_lo, budget 200 valid, resample_strict) and appended as jobs 28-40 of
  `cd_rrect_2026-11-17`. Each was preflighted; only non-HARD configs were appended. The klangfilm
  c200 family is excluded from the auto-generator because a hand-built c200w covers it MORE Widely
  (adds negative rim_sweep and the end_frac roll cap 1.55 at owner direction).
- walls found (family -> wall -> relief): lecleach ctrl/fc540/T_narrow (g_stop_deg pinned low
  -> widened), tritonia (s.lo -> widened), crowe es600 (widen per report), ext_throat_hvlaw_cov,
  klangfilm base (fc/aspect per walls), corelaw14, fold_warm, rosse r120/r50 (per-run boxes),
  lecleach_iwata smooth, rrect r50/r120 boxes, sp_control. Detailed per-family tables in
  `scratch/walls_continuations/` and `runs/nights/refresh/walls_<ts>.md`.

## 2026-11-17 02:5x - CORRECTION: fat banked cohorts DO exist; atlas 300-solve TuRBO arms queued

- Owner pushed back on the "max 231 banked rows" claim and was right: the 2026-10-13/30 campaigns have
  722-1726 attempt runs (`atlas__ath_core` 1726 attempts/1438 valid; `atlas__hyb_osse_h_hypex_v` 1381/1102;
  `atlas__core_law` 1001/567 run + 710 dataset rows/427 valid, best J 2.128). My claim had only counted the
  recent `bo_multityp` cohorts.
- Cohort probe (CPU): `atlas__core_law` refreshes to **418 exact-complete rows** in its dependency group
  (old beat_bem pin 0850ef39, consistent within the group) - clears the 100-row gate comfortably.
- Appended as final jobs 23-24: `t_atlas_corelaw_turbo300` and `t_atlas_athcore_turbo300`
  (`exploration-300x4` = 300 screens + 4 verify, seeds 71011/71012) - TuRBO trained on the fattest
  banked histories, per the owner's "how much can BO move the needle vs the best CMA solve there".
  Readout rule fixed: needle = cohort-best J (2.128 for core_law) minus the arm's best after 300 calls.
- Queue is 24 jobs; the runner drains the file; STOP file trims.

## 2026-11-17 02:3x - Night refresher (90 min) + backlog typologies appended to `cd_rrect_2026-11-17`

- First pass burned jobs: all four main legs exited 1 while a foreign supervisor storm repeatedly
  relaunched `b3_soft` (5+ orphan dirs, one healthy holder at a time) and raced the GPU lock; the
  rrect TuRBO arm then failed on a correct guard (`no successful screen records`) because its CMA
  sibling had died first. The gate loop (2-min cadence) pauses our night while a FOREIGN holder
  solves and resumes when free; the deep repair tick (90 min) reads the night's summary ledger and
  mechanically resumes: generic runs (`--resume` + missing budget), bridge runs (same argv/seed so
  old candidates replay as free cache hits), depend-gated TuRBO re-arms (fresh `_rc` root/cohort only
  once their config family holds >= 100 fresh rows), and defers duplicates/journal-only failures.
  Tools: `tools/night_queue/refresh_watchdog.py` + `refresh_loop.ps1` (controller 43928 detached).
- Repairs queued: `t_trit80_rc1` (tritonia cohort 120 rows), `c_rrect_100w_rc1` (bridge resume, 108
  remaining of 110; 2 valid already banked), `t_rrect80_rc1` (after its CMA sibling). `b3_soft_resume`
  is DEFERRED while the foreign b3 covers that thread (duplicate guard).
- Lockdown audit: no queued config is super locked down (b3 17/21, rrect 9/12, tritonia 14/30, fold
  18/35 searched; the k_lame seed cells are 5/8 with the fixed three being inert gates).
- Backlog appended (insurance depth; cutoff 14:30 governs): Klangfilm smooth CMA-200
  (`hl__klangfilm_lame_curved_v1_c200.yaml`: 6 genes, `g_morph_frac` exposed for the first time,
  8.439 incumbent as seed, canonical `klangfilm_lame_v1` type so all 200 rows share one dependency
  group; preflight 24/24 valid) then TuRBO-100 + SCALAR-100 on it; ath_core_14in (219 frozen rows)
  and ext_throat_hvlaw (231 frozen rows) TuRBO-100 + SCALAR-100 each with hash-pinned cohorts.
  New budget profile `comparison-100x2` (100 screen + 2 verify; additive key, tests extended).
- The 12-h cutoff estimate is now overtaken by the backlog: the runner keeps going until the file
  is exhausted or a STOP file is placed; trim with `runs/nights/cd_rrect_2026-11-17/STOP` any time.

## 2026-11-17 02:0x - Overnight queue `cd_rrect_2026-11-17` launched (owner-directed ~12 h GPU)

- Owner brief: CMA ("COA") arms with >=100 solves first, then two BoTorch TuRBO arms at 80-100 solves
  (budget profile `comparison-80x2`), plus continuing queue solves that were not done previously;
  targets = recent high scorers with room to improve, boxes widened where the data showed edges
  binding. Plan + evidence in the night header `runs/nights/cd_rrect_2026-11-17.yaml`.
- Findings at planning: the other lane's `b3_soft` Phase B search DIED mid-run at 01:55 (parent console
  gone; 11 rows; stale dead lock) - folded into the night as job 1, a `--resume` for its remaining 89
  valid solves (rows growing again after launch). The rrect CD family had only ~51 dataset rows under
  its config name (below the owner's 100-row TuRBO gate) and its r50 box had near-binding edges
  (best height 442.5 vs 450 high). The staged tritonia TuRBO arms (ext_v9_turbo_first/_followup)
  never ran (exit 3, GPU busy).
- New config `hl__rosse_rect_cd_v7_r100w.yaml`: r50 best 02283e214be8 (J 3.48913) as seed, every bound
  widened around the winning region (width 520-600, height 400-460, rect 4.2-7.5, a_h 34-42, a_v
  14-22, k 1.6-3.0, r 0.20-0.40, tmax 0.9-1.0, g_b 0-0.09), budget 110 valid, sigma0 0.12 (preflight:
  expected in-basin hits 6.69 >= 3; no_headroom WARN expected for a continuation), resample_strict +
  retry_same_then_stop so ~9% corner refusals are replaced. Shape-check: mouth 578 x 441, depth 459.
- Queue order: b3 resume -> c_rrect_100w (110 valid CMA) -> TuRBO arm 1 rrect80 (cohort built from
  those rows) -> TuRBO arm 2 trit80 -> fold_warm resumes (ab4fb9 +23, c221aa +39, to 100 total each)
  -> two cheap Klangfilm continuations (S4/E2 fresh runs, same seeds; old candidates replay as cache
  hits that do not consume budget). Controller 49896 detached (parent WmiPrvSE), started 01:58:59,
  cutoff 14:30. Measured-rate budget ~6.5-8.5 h of the 12 h allowance; the file is LIVE-editable to
  append a third TuRBO arm (ath_core_14in, 219 rows) while it runs.

## 2026-11-17 - N3: v9 J converges at 58 dense points; with constancy it needs 116

- 58 study pairs, v9 corridor plus the strict constancy cost (`.s1/replay.py`, weight 1 H / 0.5 V).
  J_v9: dense 58 → 116 changes it by sd 0.032 (all) / 0.019 (best 28), rank 0.999/0.997; 116 → 232 by
  0.012/0.008 - inside A4's 0.05 comparison line. Residual from 18 vs 29 solved frequencies: sd 0.193
  all / 0.113 at the top, rank 0.953 (A4's v7 size).
- J_v9 + constancy is not converged at 58 points (sd 0.175 all / 0.055 top) and needs 116 (0.058 /
  0.014); its 18-vs-29 residual is 0.370 all / 0.205 top. Constancy is ~55 % of the augmented level
  and J-independent; the H fitted level (~69.5 deg) never reaches the upper clip, so the [60,80] and
  [60,90] windows are identical on this cohort.
- Residual carried by `flat_cv`, `load`, `flat` (as A4 found for v7), not `rip`. A4's best-28 set is
  reproduced 28/28 at 0.00 J; the v9 best-28 overlaps it 25/28. Report
  `scratch/fable_architecture/N3_GRID_INDEPENDENCE_V9.md`.

## 2026-11-17 - Fable architecture: contract v2 passes all six lanes; the layered backbone fails U1

- **N1b, contract v2 (65 stations x 61 azimuths):** all six contract lanes pass Test 2 on the
  native-floor rule, 10/10 each, medians <= 0.14 mm - ext-throat 0.108 mm record p99 (native floor
  0.068), ATH morph 0.247 (0.048), Crowe 1.353 (1.160, threshold 1.451), rolled 0.856 (0.555),
  Klangfilm 1.155 (1.116), biradial 0.101 (0.047). The 61-azimuth record removes N1's rolled and
  Crowe failures. Provenance gate: the 72 Klangfilm designs carrying digest `e3a1f4a3...` (N1's ten
  included) are not reproducible at HEAD and were excluded; ten digest-verified replacements pass
  10/10; rolled's 51 recipes match HEAD; Crowe/native lanes store no digest. Envelope: stored box =
  mesh box in 70/70; every depth deficit is the rear closure exactly; biradial's +1.9...+3.5 mm is
  the generator's outward `outer_points` shell, absent from the meshed box (which equals the inner
  sheet in 10/10); 0 of 309 stored biradial designs sit within 3.5 mm of the 600 W / 480 H limits.
  A seventh lane added for N4, lecleach, is **not rebuildable at HEAD**: `d6c9abd` changed its H/V
  realization after both stored runs, and its recipes carry no implementation digest.
- **N4, U1 layered reproduction (failure line met; handed back):** three ribs + one superellipse per
  station with exact psi reproduces every rib to <= 6e-14 mm but misses the surface by 48.26 mm
  (ext-throat), 3.43 (biradial), 29.90 (Crowe), 48.25 (rolled), 3.88 (Klangfilm) - 0/5 at <= 0.5 mm,
  5/5 above 2 mm. Cause is the section law, not azimuth sampling: the 45-degree radius forces a
  near-rectangular exponent that overshoots 30-60 degrees. Extra ribs with a Pchip blend: 5 ribs ->
  1.00-27.08 mm, 9 -> 0.25-11.43 (only ext reaches 0.5), 17 -> 0.12-3.36. Psi splines through 4/6/8
  control values are worse (8.97-208.11 mm). Rolled substituted for lecleach; U2/U3 not run.
- **N2, A11 protected families and lineage:** 21 lanes - 17 carry owner-request evidence (4
  family-level), 4 have no request found (ext-throat H/V-law and OSSE rounded-rect carry owner
  *drop* evidence). All 75 runs classified, 0 unknown: 58 hand-written seed, 16 best design of an
  earlier run, 1 warm start (ATH v9); 15 of 17 parented runs seeded within 0.17 J. No family is
  recommended for cutting.
- Reports: `scratch/fable_architecture/X1B_CONTRACT_V2.md`, `U1_LAYERED_REPRODUCTION.md`,
  `A11_PROTECTED_AND_LINEAGE.md`; scripts in `.n1b/`, `.n2/`, `.u1/`. N3 (v9 grid independence) was
  still running at this commit.
- NOTE: `examples/typologies/klangfilm_hv_2026-11-16/configs/b3_soft.yaml` is another lane's
  uncommitted Phase B edit and was left untouched.

## 2026-11-17 - Klangfilm comparison mesh-converged: the A0-B3 H gap is structural

- Both reference horns were re-solved at `epw 9` (A0 16394 dofs, B3 6757 dofs, vs 7449 / 3087 at epw 6):
  beamwidths move <= 0.1 deg, `Var(DI)` and J are stable, and in 5.6-8 kHz the H gap *widens* (A0 63.0 vs
  B3 47.9 deg) rather than closing. Runs `20261117T063719Z-47260f` (A0@9) and `064133Z-6d2651` (B3@9).
- Confirms the convergence gap the Stage A/B comparisons had not closed: B3's DI-variance gain (-45 %)
  and smooth-J win (6.570 vs 8.438) are real, the missing H coverage (65.2 vs 69.7 deg) is the terminator,
  and the pre-declared Phase B gate verdict (FAIL on H coverage) stands on converged numbers.
- NOTE: another lane concurrently bumped `configs/b3_soft.yaml` (budget 100 / max_attempts 250); left
  uncommitted and untouched by this work.

## 2026-11-17 - Klangfilm Phase B registered and measured: DI gain, H coverage short

- Canonical adapter `klangfilm_lame_hv_core_family` (+ frozen `_klangfilm_lame_hv_core_v1.py`, registered in
  `generated.py`, `grid.py`, `mesh/build.py`, `gui/data.py`) with the versioned `size_policy` and
  class-separation guards: `cd_core_blend` must be fixed, and knobs of the inactive class must be pinned.
- B1-B4 materialise through the canonical route and mesh (3087-4153 dofs); solved on beat_cuda with the
  Stage A solver/grid/source (18 frequencies, 73 angles, 512-point balloon, 19-21 s per solve).
  Runs `20261117T062219Z-b72640` (b1), `062314Z-262183` (b2), `062347Z-4d3c1c` (b3), `062551Z-4ad99d` (b4).
- Result: **B3 is the best Phase B seed** - smooth J 6.570 vs A0 8.438, CD J 14.827 vs 14.208, Var(DI) 1.180
  vs 2.160 (-45.4 %), BW_V 47.3 deg (in range), zero multi-lobe bins, loading better (0.0 vs 0.777) - but
  BW_H 65.2 deg against the 70 deg floor. Widening the mouth does not fix it (B2 62.2 deg at 595 mm, B4
  64.0 deg at 563 mm), so the remaining structural difference is the **returning lip**.
- Verdict: the Phase B gate FAILS on H coverage only; do not start a search yet. Evidence `AB_REPORT_B.md`,
  `AB_REPORT_B.json`, `ab_plots_b/`, decision updated in `STAGE_A_VS_B_DECISION.md`.

## 2026-11-17 (later) - OpenCode Go preset active for HornLab; ping suite 8/8; availability and isolation verified

- **Active preset is now `opencode-go-max`** (owner instruction: the `deepseek-flash-max` tiers on
  the OpenCode Go provider). Per-agent variants, skills and MCP grants match `deepseek-flash-max`:
  `opencode-go/deepseek-v4.1-flash` for orchestrator, fixer, explorer, librarian, designer, council
  and observer, `opencode-go/glm-5.3-flash` for oracle, each with the other as fallback. The preset
  is defined in `hornlab-search/.opencode/oh-my-opencode-slim.json` and mirrored in
  `Hrns/.opencode/oh-my-opencode-slim.json` (the project walk stops at the git boundary, so the
  umbrella needs its own copy). Verified with `opencode debug agent orchestrator`
  (`providerID=opencode-go`, `modelID=deepseek-v4.1-flash`, `variant=max`) and live runs.
- **Go region.** `opencode-go/deepseek-v4.1-flash` first refused with "hosted outside Europe and
  the United States". The owner set Settings > Privacy > Regions to Global in the Go console; the
  model now loads skills (live: `PING-DS OK`). The workspace key was refreshed in
  `~/.local/share/opencode/auth.json` (type `api`); **no key material is in the repository**.
- **Ping suite, 8/8.** New `tools/agent/ping_agents.py` (static by default; `--live` makes model
  calls). Static: all 8 `hornlab-*` skills discoverable from both the repo and `Hrns` (26 skills),
  config parses, no rbassist skill granted to the HornLab orchestrator. Live: the orchestrator loads
  `hornlab-gpu-job`; a delegated fixer loads it; and the HornLab prompt reports
  `PING-ISOLATION: (no); rbassist skills: (none)`. Per-agent checks: designer loads
  `hornlab-render`; explorer has no skill tool (grant matrix enforced); a `Hrns` session loads
  `hornlab-acoustic-grounding`. Evidence: `docs/evidence/AGENT_PING_2026-11-17.md`.
- **Availability defect the pings exposed.** The DeepSeek provider is out of balance. With
  single-model agents the delegated lanes failed (`No model fallback chain for fixer`); adding a
  fallback list was not enough (`Model fallback did not recover`); reordering the same-tier arrays
  to put a working provider first fixed delegation. That was availability, not retiering: no
  variant changed. rbassist's presets still put DeepSeek first, so its delegated lanes remain
  blocked until that balance is restored or those arrays are reordered.
- **Prompt isolation, verified live.** Global appends are project-neutral; rbassist rules live in
  `C:/Users/hunte/Music/rbassist-merge-cloud-local/.opencode/oh-my-opencode-slim/` and are mirrored
  there because plugin appends replace rather than concatenate. The HornLab orchestrator denies the
  six globally installed rbassist skills via `skills_remove` (the files are not deleted).
- Also added: `docs/AGENT_BOOTSTRAP_CONTAINER.md` (umbrella bootstrap, skill registration, preset
  table), `docs/LOG_ARCHIVAL_PROPOSAL_2026-11-17.md` (rotation proposal, not approved), and the ping
  harness. No solve, test, queue or GPU state was started or changed; the running
  `home18_a_2026-11-16` lane was not touched.

## 2026-11-17 - ROSSE-RECT: g_b hover clarified and negative floor enabled; 120-run paused, 50-run live

- **GUI/doc:** the `g_b` hover on the `hl__rosse_rect_cd_v7` sandbox page now states the R-OSSE
  axial-bow meaning and sign convention instead of the old "dimensionless bend" line. The catalog
  was regenerated (`hornlab_search/gui/static/param-catalog.v1.json`,
  `docs/reference/PARAMETERS.md`, `docs/reference/TYPOLOGIES.md`); all 16 knobs on that page keep
  non-empty catalog hover docs. Verified from the running GUI at `/param-catalog.v1.json`.
- **Geometry:** `tools/geometry/rosse_rect.py` now accepts `b >= -0.10` (was `>= 0.0`). The new
  `tests/test_tools_rosse_rect_b.py` pins that `-0.05` meshes and bows the wall forward while
  `-0.11` is refused. A CPU real-mesher shape check at `b = -0.01, -0.02, -0.05, -0.10` built
  cleanly; axial span grew 422 -> 449 mm, still inside the 480 mm brief envelope.
- **Runs:** the 120-valid run `20261117T044541Z-screen-ffe3dc` was paused at 84 attempts / 79 valid,
  best **J 3.7957** (`7b79db514342`). The data-derived 50-valid run `rosse_r50_refine_2026-11-17`
  is live (17+/50 at commit time), best **J 3.7262** (`38aeaee3413b`); its recent designs sit at
  `b ~= 0.0002-0.0028`, i.e. the old `b >= 0` floor is binding. The prepared negative-b variant
  `hl__rosse_rect_cd_v7_r50_negb` (seed `38aeaee3413b`, `b = -0.05..0.06`, preflight 55/64 valid,
  expected in-basin hits 9.7) is committed but **not launched**; the owner's choice between
  letting the 50-run finish and restarting it is open.
- **Tests:** 40 catalog + b-term tests and 20 GUI param-tip/sandbox tests passed. This pass changed
  no solver, objective, or GPU code; the live 50-run was not restarted by the GUI/doc commit.
- The new brief `room_landscape_80x50_700_hf1440_rosse_rect_v7` (V scored from 1 kHz, `diag`
  reported but unweighted) is a new score identity; its J is not comparable with the base or smooth
  briefs.

## 2026-11-17 (04:05Z) - BoTorch round-2 READOUT: 3 arms complete (25 measured each); ath14 beat its cohort baseline

- Night `bo_multityp_r2_2026-11-16` finished 2026-11-16T23:03 local (exit 0, 7/7 jobs, ~60 min,
  GPU lane released; runner pre/post hygiene ran). Per arm, observations API reads (screen tier
  only by design — comparison-25x0, no verified finalist):
  - **ath14** (`bo_ath14_s71002`): 25 measured; best screen **J 5.3386** vs cohort baseline
    **5.3737** → beats its cohort best by 0.035 J (−0.65 %); first reached baseline at **attempt
    14**. Cohort: ATH-core 14 in, 219 rows, d=14, seed 71002.
  - **corelaw** (`bo_corelaw_s71003`): 25 measured; best screen **J 3.3308** vs cohort baseline
    **3.2325** → +0.098, did not beat; never reached the baseline in 25 screens. Cohort: 206 rows,
    d=9, seed 71003.
  - **hvlaw** (landscape) (`bo_hvlaw_s71004`): 25 measured; best screen **J 3.3533** vs cohort
    baseline **3.1028** → +0.25, did not beat; never reached the baseline. Cohort: 136 rows, d=8,
    seed 71004.
- Same-basin question and remaining §5 items (normalised distance of each arm best from the
  cohort best design; `hifi_rescore.py` on winners) stay open. Numbers above via the observations
  API (`sort=best_j` / `sort=attempt`) + each cohort's `offline_scores.json` minimum, 04:05Z.
  GUI: each arm browsable under Bayes → Studies (`● 25 measured`).
- No acoustic-quality claim and no BO-beats-CMA claim (no matched control in this campaign); J is
  per brief/objective, never ranked across arms.

## 2026-11-17 - Agent orchestration P0/P1 applied: container bootstrap, read budget, prompt isolation; P2 deferred

- Senior review of `AGENT_ORCHESTRATION_REVIEW_2026-11-16.md` returned "approve P0 with
  corrections; approve project prompt isolation conditionally; replace the blanket delegation
  threshold, hard polling prohibition and premature concurrency/model changes with measured
  pilots". Disposition and corrections are recorded in section 9 of that report.
- **P0a, canonical workspace + container fallback (measured).** New machine-local
  `C:/Users/hunte/Hrns/AGENTS.md` (thin umbrella contract) and
  `C:/Users/hunte/Hrns/.opencode/opencode.jsonc` registering
  `hornlab-search/.claude/skills`. `opencode debug skill` from `Hrns` went from **18 skills / 0
  `hornlab-*`** to **26 skills / 8 of 8 `hornlab-*`**, identical to the canonical checkout. A
  pointer `AGENTS.md` alone did not register nested skills; the explicit `skills.paths` entry does.
  Installed OpenCode is 1.17.10, which takes the object form and rejects the array form shown in
  current upstream docs.
- **P0b, read budget and precedence (`AGENTS.md`).** Bounded reading order: `docs/ACTIVE_STATE.md`
  pointer, then CONTINUITY/ISSUES first 60-80 lines, NOTES tail 60, grep-only over ~100 KB; never
  auto-read INDEX/CODE_MAP/research/scratch or the 40 Fable reports. Added an explicit precedence
  section (dated owner amendments > contracts > historical plan); marked the Wave 0-3 plan and the
  per-task file-ownership table historical while keeping their invariants; replaced the stale
  2026-11-12 "current state" paragraph with a pointer.
- **P1a, prompt isolation (measured).** Global
  `~/.config/opencode/oh-my-opencode-slim/{orchestrator,fixer}_append.md` now contain only
  project-neutral rules. The rbassist blocks moved to the verified active workspace
  `C:/Users/hunte/Music/rbassist-merge-cloud-local/.opencode/oh-my-opencode-slim/` (1,143 sessions;
  `C:/Users/hunte/rbassist` is an unrelated 2025 repo). Plugin appends **replace** rather than
  concatenate, so the rbassist files carry a marked mirror of the shared block. Verified with
  `opencode debug agent`: hornlab orchestrator/fixer have the shared block and no PySide block;
  rbassist orchestrator/fixer have both.
- **P1b, dispatch discipline.** Direct work for single lookups/commands/bounded edits that need no
  independent review; delegate on independence, research volume or high-risk verification; max 3
  concurrent writers, one writer per file cluster; child registry; same-session continuation unless
  context is bloated; terminal result retrieval via `task_status` kept; no repeated polling; no
  nested fan-out by default; parent owns git; tool-output and context caps.
- **P3 (partial).** Added `docs/ACTIVE_STATE.md` (<=60-line pointer: active GPU lane
  `home18_a_2026-11-16` running `r120_rosse_s5678`, CPU lane free, `bo_multityp_r2_2026-11-16` 7/7,
  v9 closed with default unchanged, verification commands). Added `docs/AGENT_BOOTSTRAP_CONTAINER.md`.
  Fixed `NEXT_DEV_PRIORITIES.md` routing (dated amendment; P16 `bogui-wt` -> canonical checkout).
  Audited the eight "missing" rbassist skills: **all eight exist project-locally** in the active
  rbassist workspace, so no reference was removed.
- **Not changed (deliberately).** No model or variant change; no global concurrency 6->4; no
  worktree deletion; no global rbassist skill removal; the CONTINUITY+ISSUES push rule stands with
  an archival note only. P2 pilot protocol is written into report section 9 and awaits the owner.
- Backups of every edited user/project config and prompt:
  `~/.config/opencode/backups/2026-11-17-agent-scope/`.
- The running GPU lane was not touched; no solve, test or queue was started by this pass.

## 2026-11-17 - Fable X1 contract tests finished (N1): two or more lanes fail inner-wall agreement; U1 gated

- Runbook N1 completed on 60 stored designs (10 per lane) at HEAD `01560e5`; the §0 replay parity
  check returned 0.0 (n=17). Read-only CPU work: no mesh build, solve, queue or config change.
  Report `scratch/fable_architecture/X1_CONTRACT_TESTS.md`; scripts and records in
  `scratch/fable_architecture/.n1/`; one row added to `LOW_COST_AGENT_HANDOFF.md` §10.
- **The X1 failure condition is met.** At the contract-minimum record (65 wall stations × 31
  azimuths = 3° step), inner-wall mesh agreement passes ext-throat (10/10, worst p99 0.158 mm), ATH
  morph (10/10, 0.850) and biradial (10/10, 0.142), but fails rolled (0/10, 1.696) and Crowe
  (0/10, 1.870), and one Klangfilm design (9/10, 1.457). Determinism is 60/60 in separate
  processes; refinement passes 30/30 on the three testable lanes (worst 0.198 mm).
- Causes, measured. Rolled is a record-resolution effect: 49 azimuths passes 10/10 (p99
  0.36–0.59) and 65 stations are sufficient; 31 azimuths aliases the relief. Crowe's native
  25 × 41 point grid already sits at p99 1.07 mm from the stored mesh (mesher surface fit, not
  sampling); the 31-azimuth chords add ~0.7 mm. Klangfilm's failing design does not match its
  stored mesh even at native/dense sampling, and the ten selected recipes carry digest
  `e3a1f4a3…` rather than the current legacy-bridge `ea5026…` (the addendum's verified digest
  belongs to a different run).
- Envelope: biradial width/height is +1.9…+3.5 mm (normal-offset outer surface versus the mesh's
  sharp mouth rim); Crowe is −0.3…−1.6 mm and ext-throat +0.65…+1.41 mm on H; every depth deficit
  is the rear closure at `z = −t` and is within 1 mm after that correction except one ATH design
  (+1.04). Metadata is complete except ATH wall thickness, termination kind for the three
  native/freeform lanes, and the resolved source-cap shape fields.
- **Stopped and handed back per the runbook.** N2 (protected families/lineage), N3 (v9 grid
  independence), N4 (U1) and N5 (U2/U3) were not run; N4/N5 also depend on N1. Next actions are
  recorded in the report: raise the rolled record to ≥49 azimuths, decide a Crowe tolerance from
  the ~1.1 mm mesher fit floor, resolve the Klangfilm run/provenance and the failing design, and
  revisit the mouth-rim envelope method.
- Corpus housekeeping committed with this entry: the 2026-11-16 23:40 report/handoff reconciliation
  that was still in the working tree (`A4`, `A5`, `A9`, X1 addendum context and the 40-report
  index updates). No implementation, objective, queue or GPU state changed.

## 2026-11-16 - Agent-orchestration review: sessions are slow because of prompt size, not agent count

- Review filed at [`AGENT_ORCHESTRATION_REVIEW_2026-11-16.md`](archive/2026-11/AGENT_ORCHESTRATION_REVIEW_2026-11-16.md).
  Docs-only: no code, config, prompt, queue or GPU change; **nothing applied**. Trigger was the
  owner's report of agents running long, spawning too many subagents, and re-briefing them instead
  of continuing them.
- Measured from the local OpenCode telemetry DB (7 days, read-only): 58 root sessions and 191 child
  sessions; 206 `task` calls against 40 `task_revive` in 30 days (~93 % cold starts); children
  average 111k input tokens to re-onboard (fixer 122k, designer 143k; 21.2M total); weekly spend
  $61.73 ($43.04 root, $18.69 child).
- Root cause, ranked. (1) **53 of 58 root sessions, and 241 of the 244 steps with >600k-token
  prompts, were launched from `C:/Users/hunte/Hrns`** - the container directory, which has no
  `AGENTS.md` and no skill grants, so sessions explore the worktrees and forks blind. (2) The
  documented reading order points at `docs/CONTINUITY.md` (844,727 B / 5,930 lines / 390 entries)
  with no read budget, plus `ISSUES.md` 407,673 B and `NOTES_FOR_SENIOR.md` 125,130 B; 42.6 % of
  the 16,887 measured steps ran above 200k prompt tokens, 11.3 % above 400k, max 832k. (3) A
  standing 4-7 lane fan-out ("Lane A-G") rather than occasional parallelism. (4) rbassist-only
  prompt blocks sit in the globally scoped `orchestrator_append.md` (~950 tokens on every Hornlab
  turn), and `skills: ["*"]` resolves to rbassist skills because the eight HornLab skills live in
  `hornlab-search/.claude/skills`.
- Proposed and deliberately **not applied** (each with mechanism, risk and validation in the
  report): container `Hrns/AGENTS.md` (P0-1); reading-budget amendment to `AGENTS.md` (P0-2);
  rbassist prompt blocks moved to rbassist project scope (P1-1); dispatch rewrite with a 3-lane cap
  and a <=2-file direct-work threshold (P1-2); preset retier - orchestrator `max`->`high`, `oracle`
  off `glm-5.3-flash`, fixer->`medium` (P2-1); concurrency 6->4 (P2-2).
- Decisions still needed before any of it is implemented are listed in section 7 of the report
  (8 items, including the single cost increase: the `oracle` tier).
- Method caveat: session wall-clock durations in the DB are **not** runtime (several root sessions
  were reopened across days and read 294-491 h). The review measures step prompt size, not session
  duration, and does not project a percentage speed-up.

## 2026-11-16 - Fable architecture corpus (40 reports + experiment replays) tracked on `main`; docs aligned

- The full `scratch/fable_architecture/` working corpus is now tracked on `main` on owner
  instruction ("commit push all"), force-added past the repo's `/scratch/` ignore. Two commits: the
  original 25 reports (`207f97a`), then the completed corpus — 40 top-level reports, the E1/E2/E3,
  S1 and X1-X5 experiment briefs + result records, `UNIVERSAL_HORN_FAMILY.md`,
  `PREDICTOR_AND_WORKFLOW.md`, `SCORING_RANGE_PROPOSAL.md`, `CORRIDOR_RERANK.md`, `SEED_SPREAD.md`,
  the revised `ARCHITECTURE_SYNTHESIS.md` (plain-language §8) / `LOW_COST_AGENT_HANDOFF.md` /
  `VALIDATION_EXPERIMENTS.md`, plus `fable_zero_gpu_checks.py`, the `.fable/` and `.tmp/` harnesses
  and the `.e1`-`.e3` / `.s1` / `.x1`-`.x5` reproduction directories. Only `__pycache__/` excluded.
- Everything in the experiment records was produced against HEAD `207f97a` on stored data, CPU only:
  no solves, no meshes, no queue or config writes. Headline results are negative-to-mixed (E1
  response-targeting no advantage, E2 minimum-norm inverse fails its rule, X3 held-out-engine skill
  < 0.6, X5 allocation comparison degenerate) — they weaken the predictor-first route and leave the
  brief/scoring-range question (S1) as the live one.
- Docs aligned in the same commit: `docs/INDEX.md` (the Fable entry no longer calls the corpus
  "git-ignored" and names the expanded set), `docs/research/fable_architecture_2026-11-16/README.md`
  (tracking state + `.tmp/` reproducibility), and `scratch/fable_architecture/INDEX.md` (dated
  provenance note, file map extended to all 40 reports, "Tracked digest"/"Safety" sections corrected
  — the research pass's "read-only / ignored scratch" statements stay as written history).
- Unchanged behaviour: no code, config, solve, queue or objective change. The corpus still carries
  no recommendation and no implementation authorisation.
- Size caveat: the subtree is ~42 MB, dominated by binary evidence (`.e1/descriptors.pkl` 8.8 MB,
  `.fable/rows.pkl` 6.8 MB, `.s1/records*.jsonl` ~17 MB, `.x3/extended.npz` 2.4 MB). This is the
  data-adjacent class the evidence rule normally excludes; it is in history now per "all", and
  removing it later needs a history rewrite.
- Caveat for future readers: the reports are timestamped evidence pinned to snapshot `601be8c`
  (drift-checked to `0750a30`), not a description of the current tree.

## 2026-11-16 (23:30) - OWNER RELEASE + LAUNCH: BoTorch typology round 2 (ath14, corelaw, hvlaw; 25 screens each)

- The owner released the 2026-11-15 17:15 solve hold for these three arms and asked for BoTorch runs
  now ("can we run some BoTorch stuff right now that will actually populate the GUI and get more
  typologies — we've started up the 80x60 threshold"), recorded in
  `docs/queue/bo_multityp_r2_2026-11-16.admission.json`.
- Round-2 night `bo_multityp_r2_2026-11-16` (file: `docs/queue/`, launched copy: `runs/nights/`)
  runs the three remaining staged arms of `BO_MULTITYPOLOGY_PLAN_2026-11-16.md`: ath14 (ATH-core
  14 in, 219 rows, d=14), corelaw (ext throat + core-law, 206 rows, d=9), hvlaw (landscape
  80x60/50 ext throat + H/V law, 136 rows, d=8) — each `comparison-25x0` (25 screens + 0 verify,
  the standing screen-only decision for exploratory arms). The cov arm did NOT rerun: its
  authorised pilot (2026-11-15, comparison-25 25+6) already holds 26 observations in
  `runs/bo_multityp_2026-11-16/bo_cov_s71001`.
- Gates before launch (all green): `preflight_arms.py` exit 0 on the three arms (`ready: true`,
  cohort pins match the execution interpreter, rows 219/206/136, budget {25,0,25,150});
  `run_campaign_night.py --night ... --admission ... --dry-run` → "admission accepted: 7 job(s)";
  `hornlab-search doctor` 11/11 PASS (0 BEAT hosts alive; baseline VRAM 1637 MiB); GPU lane free
  (`runs/.gpu.lock` free, no runner processes; home_day2 queue finished 20:48). Launched detached
  22:03:34 (controller pid 41600, `launch_detached.ps1` → `queue.ps1 -Nights bo_multityp_r2_2026-11-16
  -Admission docs/queue/bo_multityp_r2_2026-11-16.admission.json`). Runner log:
  `runs/nights/queue_bo_multityp_r2.log`, per-job logs `runs/nights/bo_multityp_r2_2026-11-16/`.
- Readout plan stays as written in §5 of the plan (baseline = best cohort screen J; win condition =
  arm best beating the cohort baseline; per arm, never pooled). Screens are screen J — no verified
  finalist by design; GUI populates under Bayes → Studies as observations accumulate.
- GUI restyle follow-up (same night, owner PDF comparison): the BO Results workspace now carries the
  CMA-run header grammar — mono identity strip (`STUDY RESULTS · POLICY … · REVISION … · ROOT …`),
  a KPI tile strip on the Horns tab (Coverage target / Scoring floor / Band / Best SCREEN J / Best
  VERIFIED J / Selected horn W×H×D / Observations) and the added target/floor/band tiles on the
  Overview tab, all fed only from recorded payloads (`bo.target_integrity` + observations; honest
  "scoring target unavailable" when absent, never a guess). Beamwidth ref-line chips renamed to the
  CMA vocabulary (`target H 80°`, `f0 700 Hz`). Implemented by the orchestrator (designer lane out
  of balance all session); `tests/gui_study_results_lifecycle.mjs` extended to lock the strip;
  both harnesses + `node --check` green.

## 2026-11-16 (23:20 local) - v9 FINAL: G13 corridor display green, full filtered suite green, consolidation commit

- Final gates: **G0-G13 all pass**. G13 (GUI chart==scorer equality) — `tests/test_gui_corridor_v9.py`
  (corridor band polylines/isobar curves asserted EQUAL to the scorer arrays at every grid index, nulls
  below onset produce no geometry, legacy-v7 regression intact); consolidated wave 260 tests; full filtered
  suite `-m "not slow and not gpu and not crosscheck" -n 6` green except the two documented pre-existing
  items (b8 static check - another lane's `study_jobs.py:829 subprocess.Popen` from 2026-11-15; klangfilm
  tool tests green standalone, red only under xdist load). Two test-truth updates came out of
  registration: `test_objective_v8` now pins SUPPORTED == (1..7, 9) with v8 still importable-only;
  `test_dataset_manifest` includes the registered-and-empty "9" legend bucket.
- Lane-provider notes: two background subagents died on provider "Insufficient Balance" errors AFTER
  completing their file work (GUI corridor lane) or mid-lane (schema lane, module landed / tests missing);
  both were reconciled by the integrator directly (schema test file `tests/test_target_profile.py`
  rewritten; the amendment-section-D anchor-below-plane-f0 REFUSAL was found unimplemented and added in
  `targets/profile.py::_row_tuple` + the corridor >=2-anchor rule in `targets/spec.py`). Workflow
  reminder recorded: a PowerShell string round-trip on evaluate.py corrupted encoding and was restored
  from HEAD; edit-tool only for repo files.
- v9 status: REGISTERED (`objective/versions.py` + `search/evaluate.py::9: _score_v9`), opt-in via
  `objective.version: 9` + required `target.coverage_profile`; production default unchanged; historical
  J untouched (exact replay green). No GPU, no queue, no run mutation anywhere in this wave.
- Residual OPEN (ISSUES): smooth-brief re-baselines decision per the fairness table; BO-GUI lane's
  uncommitted work in the shared tree (bo/*, gui data_bo/server/app.css/studies/study_charts app.js
  regions) left to its own session — app.js carries BOTH that lane's uncommitted view regions and the
  corridor display (their view tests green against the current tree; disclosed mixed-authorship in this
  commit).

## 2026-11-17 - Klangfilm Phase B monotone H/V core (geometry only) + Stage A/B decision report

- Stage A verdict recorded in `docs/evidence/klangfilm_hv_2026-11-16/STAGE_A_VS_B_DECISION.md`: the
  throat-only arms moved the intended axis by <= 2.74 deg (and narrowed), leaked <= 0.71 deg, and
  scored worse under both policies, so the pre-declared 3 deg rule failed and the box is not to be
  optimized.
- New `tools/geometry/klangfilm_lame_hv_core.py` (schema `klangfilm-lame-hv-core-v1`,
  `rows.type: klangfilm_lame_hv_core`): `theta_i(z)` slope law, `r_i = r0 + int tan theta_i dz`,
  shared-z planar Lamé stations with an independent `p(z)`, and a late C2 swept beak. `cd_core_blend = 0`
  is bit-identical to v1; a fold or a lip that returns into the body is refused, not clamped.
- Seeds B1-B3 reach mouths comparable to A0 (480x240, 595x233, 473x266 mm), all inside the envelope;
  `tools/geometry/klangfilm_hv_core_preflight.py` writes `PHASE_B_GEOMETRY.md`, `phase_b_geometry.json`,
  `phase_b_sections.png`, `phase_b_laws.png`. 12 focused tests in
  `tests/test_tools_klangfilm_lame_hv_core.py`.
- NOT DONE: no BEM/polar evidence for Phase B, no canonical family adapter, no returning lip (needs a
  section-normal spine), source cap unchanged. The next gate and its decision rule are fixed in the
  decision document.

## 2026-11-16 (23:15 local) - v9 G13 GUI corridor + schema-lane completion landed

- G13 GUI corridor display: `charts.js` adds `corridorBand`, the preferred ref-line dash, the
  corridor/preferred legend keys and the isobar/globe min-max edges; `app.js` feeds the BW,
  isobar and globe views from `scoring_view.profile`, dropping below-onset nulls. The node test
  `tests/test_gui_corridor_v9.py` compares the drawn SVG geometry to the real `_profile_view`
  payload exactly, including a late-H-onset case and the legacy-v7 no-corridor path.
- Schema-lane completion: `targets/profile.py` refuses an anchor below its plane's scoring floor;
  `targets/spec.py` requires >=2 anchors for corridor mode (target mode keeps the one-anchor
  constant profile); `tests/test_target_profile.py` pins both, the byte-identical no-profile
  Target and the asdict round-trip.
- Verified: 132 focused v9/GUI tests green (corridor, target-profile, scoring-view profiles,
  objective v9, scoring view, chart standards, report, globe, target curves, brief authoring);
  both JS files pass `node --check`; the v9 dispatch import is clean.
- OPEN (consolidation): full filtered suite and the G0-G13 evidence summary; owner smooth-brief
  re-baselining decision. No GPU/solve/queue change.

## 2026-11-16 (22:30 local) - v9 implemented per amended RFC (schema + objective + dispatch + identity + display); GUI corridor lane in flight

- Target schema (`targets/spec.py` + NEW `targets/profile.py`): `target.coverage_profile {mode: corridor|target,
  interpolation: log_frequency, h: [...], v: [...]}` — corridor requires strict `min < max` per anchor (refusal names
  plane+index) with preferred inside [min,max]; target mode allows a single anchor (= legacy per-anchor constant
  target; G11); every anchor below its plane's f0 is REFUSED naming `target.coverage_profile.<plane>[i].hz` + f0;
  anchors round-trip via asdict (tuple anchors accepted on re-parse); no-profile Targets are byte-identical.
- NEW `objective/scalar_v9.py` (objective v9, amended RFC 2026-11-17): weighted
  `cov_profile, rip, flat, load, dislope, di_roughness, flat_cv` (+ optional `hf_floor` with its own
  weight/tolerance), `diag`/`distd` computed but UNWEIGHTED (owner-locked); `V9Params.from_block` REFUSES
  `objective.bw8k_floor` naming both keys (the profile `min_deg` is the narrow-side HF constraint) and validates the
  optional `hf_floor` block; `cov_narrow_ratio` defaults 1.0; below-onset follows `cov_below_f0` (mask/one_sided,
  narrow-only cost vs the profile's lower bound); `rip` uses per-frequency envelope widths; `di_roughness =
  std(DI - fitted line)` over the score band (G-fixture: straight +5 dB/dec -> roughness ~1.7e-15, legacy distd > 0);
  v6/v7 semantics untouched; di_roughness <2 finite pairs -> 0.0 (RFC §5.1's "3 samples" superseded by the lane
  decision, documented).
- Registered: `objective/versions.py` + `search/evaluate.py` (_score_v9 + params resolution) — the owner-approved
  registration; gate status at this commit: G11 v7-equivalence EXACT (stub-verified Δ = 0.0 and in-repo), G12
  refusal + hf_floor terms, di_roughness/jagged fixtures, config v9 requirement (`objective.version 9 requires
  target.coverage_profile`), old-J identity replay exact (test_obj_replay) — 217-test consolidated wave green.
  `config.py` v9 briefs must carry the profile; K-law feasibility preflight uses each plane's FIRST-ANCHOR
  preferred_deg (unchanged without a profile). G13 (GUI-chart==scorer equality) lands with the in-flight GUI
  corridor lane; a G13 failure reverts the dispatch line before merge (recorded here).
- Identity + display (P0 follow-through): `tools/analysis/catalog.py` `_target_block`/`_target_identity` carry
  `coverage_profile` pop-when-absent (legacy `target_hash` byte-identical; two briefs differing only in profile can
  never collide); `tools/analysis/cohorts.py` spec/record profile gate is symmetric + strict
  (`target_coverage_profile_mismatch`); dataset records serialise tuple anchors to JSON lists automatically;
  `targets/scoring_view.py` gained the v9 `score_window` profile onsets (max(anchor1, plane f0); v9 narrow-ratio
  default 1.0), the `build_scoring_view["profile"]` block (shared 32-point log grid, per-plane arrays None below
  each plane's onset, min/max None in target mode) and the v9 `di_summary` truth (level-less, like v6).
- Lane-collision reconciliations this wave: stale `score/di_summary/build(..., 9) is None` expectations updated to
  the registered-v9 truth (`10` as the unsupported sample); cohort fixtures' brief-name mismatch fixed; evaluate.py
  integration done with edit-tool only after a PowerShell round-trip corrupted encoding (restored from HEAD, redone
  cleanly — recorded as a workflow reminder: never rewrite repo py via PowerShell string round-trips).
- Tests at commit: tests/test_target_profile.py (schema lane) + GUI corridor/G13 lane still in flight; the
  consolidated 217-test run covers v9 behaviour, config gates, v7 parity, identity truth and old-J replay. Full
  filtered suite runs at the final consolidation commit.

## 2026-11-17 - Klangfilm HV Stage A acoustic A/B: no useful authority; Phase B warranted

- Three BEM arms solved from a pinned HEAD snapshot (the live tree was temporarily inconsistent while
  another lane wired objective v9): A0 incumbent `20261117T015442Z-screen-0afda0` / `a01be912716b`,
  A1 H-only (theta_H 14) `20261117T015600Z-screen-de1861` / `e40b381aa08a`, A2 V-only (theta_V 5)
  `20261117T015658Z-screen-7ffaad` / `b6a2c90ee34d`; identical mesh/solve/grid, 7435-7464 dofs,
  18 frequencies, 73-angle cuts + 512-point balloon, 49-53 s per solve.
- Method gate: replay reproduces the stored J exactly (parity 0.0) only through `brief_from_config`;
  reading the brief YAML directly loses the resolved target (`driver_exit_radius_mm`,
  `diag_reference`) and gives 7.13 vs 8.44. Recorded in the tool so it cannot regress silently.
- Result: largest intended-axis mean -6 dB beamwidth change is 2.74 deg (A1 H, 5.6-8 kHz, a narrowing),
  0.38 deg in 1.2-5.6 kHz, and 0.00 deg for A2 V; cross-axis leak <= 0.71 deg; no new -6 dB lobes;
  cut-limit saturation unchanged. J is worse under both policies (smooth 8.438 -> 8.694 / 8.567;
  CD 14.208 -> 14.548 / 14.335).
- Pre-declared 3 deg rule: Stage A has no useful acoustic authority, so the 4-knob box must not be
  optimized and Phase B (monotonic integrated-slope core) is warranted. Report
  `docs/evidence/klangfilm_hv_2026-11-16/AB_REPORT.md` + `ab_plots/` + `ab_manifest.json`.

## 2026-11-16 (22:05) - BoTorch GUI source-audit handoff implemented (P0+P1+P2 core; CPU only, no GPU, no queue change)

- Handoff moved into the repo: `docs/research/BO_GUI_SOURCE_AUDIT_HANDOFF_2026-11-16.md` (source
  audit of public main `2c0e2928`); INDEX row added. Three parallel lanes implemented it against
  the canonical checkout; a live GPU screen search ran untouched throughout (GUI-only, CPU test
  lanes only; no solve, no queue file, no lock touched).
- **P0 read-only bridge** (`gui/study_designs.py`, new) + `gui/data.py` directory readers
  (`design_curves_at` / `mesh_surface_at` / `balloon_at`) + `gui/server.py` GET routes: a BoTorch
  study observation now resolves through `StudyIndex` + the study's own package sha to
  `runs/study-<package16>/{screen,verify}/designs/<hash>/` with tier allowlist, path containment,
  identity checks and typed states (`measured|geometry_only|predicted_only|missing_artifact|
  unsupported_geometry|stale`, each with reasons). Listing supports `sort=best_j|worst_j|attempt|
  seq|screen_j|verified_j`, `q=`, `state=/verified=/new_incumbent=/pareto=/nondominated=/
  include_predicted=` filters, converged identities arrays, and per-row dimensions/descriptors/
  family/new_incumbent/pareto facts (never guessed). Geometry is the stored mesh or a clearly
  labelled no-BEM preview (`source:"stored_mesh"` vs `preview` notice); unsupported families return
  `unsupported_geometry`, never a fake radial horn. Zero-BEM guard: GET-route test monkeypatches
  `get_backend`, `search.evaluate.evaluate`, `studies.production.execute_study/launch_study` and
  both job bridges to raise; 19/19 resolver tests (incl. a 219-observation pagination-union
  fixture) green.
- **P1 Results workspace** (`gui/static/study_results.js` new; `studies.js`/`study_charts.js`/
  `app.js`/`app.css` extended): `#/bayes/study/<id>/{results,horns,explore}` — Overview with best
  VERIFIED and best SCREEN never merged; Horns = full observations table (pagination, search,
  sorts, filters, design grouping with attempt evidence, screen-vs-verify side-by-side); Explore =
  PCA/Pareto clickable by `solve_id`/`design_hash` (hollow markers for unresolvable points);
  inspector reuses `view3d.js`/`balloon.js`/`charts.js`/`verify.js` panels; selection is the URL
  identity `?root&solve&tier&design` (best-verified → best-screen → labelled predicted-only
  defaults; never silent "Unknown"); "Solve in 3D" is demoted in the Results surface to a
  confirmed, cost-framed "Verify at higher fidelity…" fallback. Raw artifact dumps moved to a
  collapsed Advanced section with semantic cards and renamed status kinds.
- **P2 evidence truth + model panels** (`bo/diagnostics.py` presentation fields,
  `gui/data_bo.py` view models): `sequential_validation` and `efficient_loo_cv` rendered as two
  named sections with explicit `interval_evidence` (±2σ never labelled calibrated 95% without
  recorded coverage evidence); missing diagnostics read `"not recorded"`; `proposal_explanation`
  (policy/index/acquisition-as-ranking-signal/designation), `target_integrity` ("scoring target
  unavailable" verbatim, never a typology guess), real-unit posterior slices with
  `feasibility_warning`, TuRBO centre identity/inside-outside/unspent budget, Pareto
  `frontier_axes` (deg/dB only; J stays a per-point scalar), `excluded_points`,
  `hypervolume_trace`, predicted points marked, and `retrospective` provenance for refit
  predictions. Frontend renders all of these (Lane C handoff list consumed in full).
- **Verification (pasted):** focused lane suite
  `tests/test_gui_study_designs_resolver.py + test_bo_data_p2.py + test_gui_bo_views.py +
  test_gui_study_index.py + test_gui_study_solves_view.py + test_gui_study_lifecycle.py` → exit 0
  (51 tests); `node --check` on all four static JS modules exit 0; `node tests/gui_study_lifecycle.mjs
  ...` → "study lifecycle ok"; `compileall -q hornlab_search\gui hornlab_search\bo` exit 0; broader
  GUI set (studies_api/integration_phases/balloon/verify_data/scoring_view) exit 0. Read-only spot
  check against real fixture `runs/bo_vs_cma_2026-11-15/bo_s31001` (Lane A): 60 measured
  observations listed, verify-tier geometry/balloon resolved, no `runs/` write.
- **Remaining (documented, not hidden):** `study_results.js` has no DOM-stub lifecycle test (the
  `.mjs` harness cannot resolve relative imports for module files; it covers `studies.js` only);
  the legacy authoring Execute tab still carries the lifecycle-test-pinned "Solve in 3D" button
  (primary Results surface is clean); P3 (cross-method comparison arm, incumbent-evolution viewer,
  payload-budget audit) not started; browser-level acceptance tests (visual equivalence,
  desktop/mobile, screen-reader labels) still need an eyes-on pass. See ISSUES same date.
- **Follow-up same evening (owner live GUI pass):** the studies list showed empty smoke arms
  (staged, never launched) identically to populated ones, so the Studies page looked "empty".
  `studies.js::mountStudyList` now lazily loads per-study observation counts in bounded chunks
  (6/round-trip, `api.getObservations`, abort-on-dispose, graceful `? unknown` state) and renders
  honest chips: `● N measured` / `○ not launched`. CSS in `app.css` (existing tokens only).
  Validated: `node --check` exit 0; `tests/gui_study_lifecycle.mjs` → "study lifecycle ok"; GUI
  serves fresh (`no-store` static handler, no restart needed). Implemented directly by the
  orchestrator — the fixer/designer subagent lanes were unavailable this session (provider
  `Insufficient Balance` on two consecutive launches).

## 2026-11-16 (21:10 local) - Fable discovery evidence dossier delivered and tracked (read-only)

- Delivered the v3 handoff's cheap-agent research pass as a 15-file evidence dossier, now tracked
  at `docs/research/fable_architecture_2026-11-16/` (INDEX, SOURCE_INDEX, EVIDENCE_LEDGER with 59
  atomic claims, OPEN_QUESTIONS, plus geometry/failure/size/objective/optimizer/external/watchdog/
  switch/supervisor/unknowns reports). Short digest:
  `docs/research/FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md`.
- The git-ignored `scratch/fable_architecture/` copy remains the working copy; the tracked folder is
  a verbatim mirror for GitHub review (README records provenance and reading order).
- The 12 v3 handoff source documents (`00_START_HERE.md` … `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md`,
  including `03_FABLE_DISCOVERY.md`) were moved from the Downloads package into the same tracked
  folder, so the brief, its options and the evidence dossier are co-located.
- Snapshot of record `601be8c`; the tree advanced to `0750a30` during the pass and
  `git diff --stat 601be8c..0750a30` over every cited path is empty. The checkout is 12 commits
  ahead of the handoff's `origin/main = 2c0e2928`.
- Decisive findings: post-mesh envelope refusals are coded `invalid_geometry` and family
  `GeneratorError: invalid_envelope:` strings are also miscoded (`evaluate.py:1546,1580`), so the
  graded penalty is unreachable for native families; the 2026-11-16 window is 88.6% complete-BEM
  with zero resource faults (envelope/geometry is the wall, not GPU); the generic-GRID extent
  estimate is conservative on both axes but realised false refusals are **unmeasured**; the
  catalogue is mostly names/carries/briefs over six engines; v7 scores an exact 80x50 point while
  the brief states 60-90 H / 40-60 V; an untracked v9 corridor objective is in flight but imports a
  missing `targets/profile.py`; scalar BO is one frozen-task GP that excludes refusals; the watchdog
  merges five outcome classes, never watches BO studies, and would have killed a QD run that
  reached best 6.636 and a 5/324 archive.
- No solve, GPU, mesher, pytest, queue edit, threshold change, process signal or git mutation was
  performed by the research pass; the concurrent lane's work was observed and preserved. This
  commit adds only the tracked digest plus index/continuity/issues entries.

## 2026-11-16 - V2A timing-law endpoint correction (CPU geometry only)

- The V2A timing law `smootherstep(u/a)/smootherstep(1/a)` did not guarantee zero first/second
  derivatives at the mouth unless u50=0.5 (measured |dS/du| about 1.087 at u50=0.65). Replaced with
  the warped quintic `q=u50/(1-u50)`, `w=u/(u+q(1-u))`, `S=smootherstep(w)`, which keeps the single
  u50 coordinate and gives S(0)=0, S(u50)=0.5, S(1)=1, S'=S''=0 at both ends for every u50.
- Added analytic `timing_derivatives()` and tests at u50=0.35/0.50/0.65 plus the fixed 20 mm hold
  (raw half point 0.464286); endpoint S'/S'' are 0 within 1e-12.
- Regenerated evidence: c0 cuts unchanged (u50=0.5); c2 40/60 mm values updated; T2 practical rank
  remains 4 at three parents (max |cosine| 0.640); 8 kHz mesh unchanged at 8,318 tris, 0 bad open
  edges, driven plane 36.000x36.000 mm. 18 V2A tests green (one config-load test is blocked only by
  the concurrent uncommitted v9 objective registration, not by this change).
- No solve, GPU, queue or objective change.

## 2026-11-16 (21:05 local) - Fairness re-score + RFC amendment delivered (P1 v9 enters gated implementation)

- Deliverable 4/1 (owner-ordered matched re-score): `docs/evidence/CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md`
  + deterministic script `scratch/rescore_crowe_klangfilm_20261117.py` (results JSON alongside, scratch is gitignored).
  Crowe ES-600 `22365b569be9` and Klangfilm-Lame `491efb2132b8` best designs re-scored from their STORED
  `response.npz` under BOTH landscape v7 briefs; identity replays reproduce stored J EXACTLY (Δ = 0.0 both; Crowe
  16.918176135266869, Klangfilm 8.923616737684702); grid match asserted. 2x2: Crowe 16.92 base / 6.84 smooth;
  Klangfilm 22.78 base / 8.92 smooth. Findings: ~50% of each base J is the CD assumption (`dislope`+`di`), the 8 kHz
  floor contributes 14.5-28.4% of base `cov` (Crowe raw 1.4708, Klangfilm 4.3438), and under the smooth brief `diag`
  becomes Crowe's largest term (2.941 of 6.836, 43%). Method guard: use
  `search/evaluate.py::metrics_from_response` (sin-theta quadrature) — raw `compute_metrics` mis-weights the
  theta-phi balloon (up to ~6.9 dB DI over-read; identity replay missed ~4.6 J before the correction; documented).
- RFC amended, append-only: `docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md` §Amendment
  2026-11-17 implements the owner's review: direction approved, the 12 defaults NOT blanket-approved:
  (1) `mode:` split — `corridor` refuses degenerate `min==max` (refusal names plane+anchor), constant profiles are
  explicit `mode: target` (quadratic vs `preferred_deg`; G11 pins per-anchor equality to legacy cov within 1e-12);
  (2) `objective.bw8k_floor` REFUSED in v9 (error names both keys) — the profile `min_deg` is the narrow-side HF
  constraint, and any extra HF penalty exists ONLY as explicit independently weighted `objective.hf_floor
  {hz,h_deg,v_deg,weight,tolerance}` (absent by default); (3) effective per-plane onset = max(first_anchor, f0_plane),
  anchors below the plane f0 REFUSED; below-onset behaviour stays `cov_below_f0` unchanged; (4) v6 stays
  byte-identical; a future owner-gated v10 `loading_profile` imports v6's pure terms (`load_near`/`z_smooth`) with
  `cov_pat->cov_profile`, `di_roughness` in; v6 J never ranked against v9/v10 J; (5) GUI corridor display
  (v9+ runs): scored min/max band + dashed edges, dotted NON-penalized `preferred` centreline, `hf_floor` lines
  labelled with their weight, G13 charts==scorer. Owner-locked: diag unweighted but reported; `distd` weight 0
  (computed, never redefined); H/V anchors declared independently; `di_roughness` kept; historical J immutable;
  production defaults untouched. Gates extended to G0-G13; v9 registration ONLY after all gates pass with pasted
  output.
- INDEX rows updated (amendment note + re-score evidence).

## 2026-11-16 - Klangfilm-Lame independent H/V throat core (Phase A) landed; Phase B gated

- Gate 0 audit `docs/evidence/KLANGFILM_HV_THROAT_AUDIT.md`: the canonical incumbent is the 494.439 Hz
  local record (not the 382.753 screenshot seed); legacy H/V throat chords 9.4631/9.4378 deg prove the
  `Q'(0)=0` equal-tangent fault; one axial turn at z=183.962 mm with the mouth at z=-48.44 mm is intrinsic
  rollback; the saved v1 recipe digest drift is runtime-version-bound (all sources unchanged).
- New `tools/geometry/klangfilm_lame_hv.py` (schema `klangfilm-lame-hv-v1`) plus canonical
  `klangfilm_lame_hv_family` (`rows.type: klangfilm_lame_hv_cd`, frozen `_klangfilm_lame_hv_v1.py`).
  Zero blend is bit-identical to v1; independent H/V entrance tangents on the same 18 mm rim; refuses
  constriction/non-monotone forward radius instead of clamping; digest covers parent kernel + cap math;
  versioned `size_policy: enforce|report_only` (enforce stays the search default).
- Seeds `examples/typologies/klangfilm_hv_2026-11-16/` (a0-a5 + `stage_a_search`), with preflight, contact
  sheet and search-box lawfulness tools in `tools/geometry/`. Measured: a3/a4 refused (negative V gain),
  a5 over envelope and report-only, Stage A 200/200 samples and 16/16 corners lawful.
- Validation: 72 focused tests green (kernel/family/dispatch/legacy/dual), config/grid/mesh-dispatch
  suites green, all 8 diagnostic configs behave as designed. No solve, no queue, no objective change.
- NOT DONE: Phase B (monotonic CD core, shoulder/roll/beak, OS-SE comparator) is gated on a Phase A
  acoustic A/B. No BEM/polar evidence, so no CD claim. Cached CD diagnostic `J_CD_cached=17.589`, and the
  v7 smooth run is not a CD score.

## 2026-11-16 - V2A four-DOF parameter hardening (CPU geometry only; no solve, nothing queued)

- Owner supplied the V2A addendum; moved to
  `docs/research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md`. It supersedes V2
  on throat transition and parameter count; the 15-40 mm circular-hold rule is withdrawn.
- `crowe_hv_area_aspect_v1` now exposes exactly four search dimensions:
  `height_v_active_mm`, `L_forward_mm`, `area_mid_bias`, `aspect_timing_u50`.
  `width_h_active_mm` (580), `p_mouth` (3.25) and `throat_round_hold_mm` (0) are fixed
  generator-block values; c2 (20 mm hold) and c3 (p 2.2) are fixed A/B configs, not knobs.
- Timing law: normalized C2 smootherstep `S_R(u)` with exact half point `u50` and zero end
  derivatives; `log R = log(W/H) S_R`; `p = 2 + (p_mouth-2) S_R`. The area bias is a C3 compact
  window. `A = C(p) ab`, `R = a/b` and the driver-exit source tangent are preserved exactly.
- c0 cuts: at 20 mm area 1.102x while |aspect-1| = 5.4e-4 and |p-2| = 3.3e-3; at 40 mm area
  1.261x, p 2.024; at 100 mm p 2.262. c2's fixed 20 mm hold is exactly circular through 20 mm and
  C2 at its boundary.
- T2 law-level Jacobian: practical rank 4 at three parents, no weak keys, max |cosine| 0.633.
- Real 8 kHz quarter mesh of c0: 8,318 tris, bad_open_edges 0, non-manifold 0, driven plane
  36.000 x 36.000 mm, `fits_exit(36) = True`.
- Tests: 17 in `tests/test_design_generators_crowe_hv_area_aspect.py` green. Section and Jacobian
  tools added. No BEM, GPU, queue, objective or historical family change.
- T0 screenshot audit remains open (no design ID/mesh hash supplied); the in-repo source check
  confirms `view3d.js` `buildRidgeGeometry` is a display overlay, not physical ridge geometry.

## 2026-11-16 - Research library and acoustic-grounding skills integrated

- Added `docs/knowledge/README.md`, source catalog/metadata, eight compact family cards,
  claim/family templates and the supplied compilation preserved verbatim.
- Root agent entrypoints route acoustic/geometry/scoring/optimization decisions through
  family applicability checks. Keele sizing is not universal; intentionally non-CD horns
  must not silently inherit CD targets. Existing historical research remains in place.
- Claude/OpenCode/Codex skill entrypoints share one grounding workflow; existing
  typology-research remains the detailed new-construction protocol.
- Validation: 49 local links resolved; skill frontmatter, source YAML and OpenCode JSON
  parsed; scoped whitespace check passed. No runtime skill activation or new source
  verification claimed; no application code, solves or active jobs changed by this task.


## 2026-11-16 - CROWE-inspired forward area/aspect family implemented (CPU geometry only; no solve, nothing queued)

- Owner supplied the V2 senior research and four throat rules (round for 15-40 mm; area expands
  before boxiness; no ridges early; near-throat C1/C2). Moved the doc to
  `docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md` with a landing note.
- New versioned FREEFORM generator `crowe_hv_area_aspect_v1` (`design/generators/`): explicit
  `log A(u)` with the driver-exit initial slope, and `log R(u)` / `p(u)` on a C2 gate after
  `round_throat_mm`. Exact `A = C(p) ab` and `R = a/b`. H/V anchors + superellipse stations; no
  returned lip, rim setback or X crease (Phase 2).
- Owner rules are structural, not cosmetic: `a = b`, `R = 1`, `p = 2` exactly through the
  `round_throat_mm` zone (seed 30 mm, proposed search 15-40 mm) while area reaches 1.17x at the
  gate, 1.26x at 40 mm and 1.86x at 80 mm. Boxiness is only p 2.0007 at 40 mm / 2.07 at 80 mm.
- Examples `c0_round30_480.yaml` (fixed geometry diagnostic) and `c1_frontier_bounds.yaml`
  (8-knob proposed box; OWNER-GATED, not queued). Section-cut tool
  `tools/geometry/crowe_hv_area_aspect_sections.py` produces the owner's 0/5/10/20/40/80 mm table.
- Tests: 18 in `tests/test_design_generators_crowe_hv_area_aspect.py` green, including the exact
  identities, 81 extreme perturbation combinations, cold-subprocess replay, config/search-box
  validation and a real 8 kHz quarter mesh (8,447 tris, bad_open_edges 0, non-manifold 0,
  source cap 36 mm round; `fits_exit(36) = True`).
- Law-level preflight: 500/500 uniform random `c1` samples lawful; all 18 bound endpoints valid.
  This is NOT the research document's 40-80 candidate mesh DOE, a BEM result, a CMA/BoTorch run,
  or an acoustic claim. No GPU, queue, objective or historical family was changed.

## 2026-11-16 (20:10 local) - P0 non-CD scoring truth LANDED (additive, no J change) + P1 RFC + deliverable-1 table

- Spec: owner-supplied source-reviewed handoff moved into the repo as
  `docs/research/typologies/NON_CD_SCORING_TRUTH_HANDOFF_2026-11-16.md` (P0 truthful GUI / P1 opt-in profile / P2 gates).
  The P0 rules were implemented literally: no scored-vs-imaginary line confusion, the DI-slope-implied corridor is OFF
  by default and would be labelled "illustrative — NOT scored" if ever rendered.
- New pure helper `hornlab_search/targets/scoring_view.py` (45 tests): per-version scored truth — per-plane score
  windows (v1/v2 full band, v3+ f0/f0_v, v4/v5/v7/v8 `cov_below_f0` mask|one_sided + narrow ratio, v6 `cov_pat`
  onset with the EXACT `resolve_fc_hz` order), resolved DI level (v1 cuts vs v2+ Gaussian; explicit wins; v6
  level-less), level/slope scored-ness from weights, `bw8k_floor` facts at the scorer's sample index, diag reference.
- Live-run truth pinned as a test: v6 designs never store `fc_hz`/`g_fc_hz` in metrics scalars, so the v6 scored onset
  falls back to `f_pattern = pattern_beta × f0` (1920 Hz for `lecleach_rollback_1in_v6`) even though design.json
  carries varying `g_fc_hz` (~623); the helper therefore deliberately does NOT read design.json knobs
  (evidence `runs/20261112T113047Z-screen-24053e`). The first implementation consulted knobs — caught during
  reconciliation and corrected before any GUI could display a false 996 Hz onset.
- Additive payloads: `run_detail.scoring_view`, `design_curves.score_window` + `di_slope_scored`, campaign
  `scoring_view`/`weights`/`objective`, `/api/compare` `scoring_view_a`/`scoring_view_b` (3-line server emit). No
  existing key renamed; absent keys stay absent; J identity untouched.
- Web GUI (run detail, campaign best-of-family, compare, brief-editor hint): scored coverage target drawn ONLY across
  the scored window; no target artefacts in the masked region; one-sided widening region + lower bound below onset;
  plane-specific 8 kHz floor lines with the raw penalty; ±10% band labelled "visual guide, NOT the scoring tolerance";
  DI level line only when that term is weighted (v1 cuts / v2+ Gaussian), display-only slope guide anchored at the
  measured DI with the "translation-invariant in dB" note; fitted-slope caption from the scored band; compare draws
  per-side targets when the scored briefs differ and never overlays one as shared. charts.js gained polyline
  `refLines`, isobar/globe `targetLoHz`/`belowMode`/`illustrativeCurve`/`floorRays` + legend keys (old calls render
  identically; node regression tests). Report got `ref_lines` + the same truth (incl. the v2+ Gaussian DI fix).
- Docs: P1 RFC `docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md` (recommend objective v9,
  `target.coverage_profile`, soft corridor, `di_roughness` as a NEW term, envelope-derived 8k floor, 12 owner gates);
  deliverable-1 table `docs/evidence/NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md` (4 real runs; headline: Crowe ES-600
  `32f7c4` was scored on the BASE CD brief → J 16.92 with dislope 7.40, not comparable to Klangfilm-on-smooth 8.92);
  INDEX + CODE_MAP updated in this commit.
- Verification (all real runs): lane suites 45 / 54+46 / node 3 / 58 / 7 green; truth-invariant `test_obj_replay` +
  v4/v6/v7 objectives exact (96); scoring-path diff EMPTY; full filtered suite zero new failures (residual:
  klangfilm-lame tools tests green standalone 24/24 and red only under -n 6 xdist load; b8 study-module static check
  pre-exists this work — `study_jobs.py:829 subprocess.Popen` is from commit 6791bfa 2026-11-15, another lane's
  module). Reconcile fixes landed here: `test_gui_brief_authoring` per-side-target assert, `test_targets`
  `catalog.gui.yaml` index exclusion.
- NOT done: P1 v9 implementation (owner-gated on RFC §7), no scoring/J mutation anywhere, no new solves, no queue
  writes; nothing here re-ranks existing stored J.

## 2026-11-16 - Dual Lamé geometry and HF1440 seed gallery (CPU only)

- Added distinct digest-bound Klangfilm-Lamé and derived Le Cléac'h H/V GRID recipes,
  sampled 3-D normal shells, fixed geometry-only examples and GUI previews. Historical
  bridge and ellipse paths are preserved. Parent and extension assumptions, source
  dimensions and remaining validation gates are in
  `docs/research/typologies/DUAL_LAME_INTEGRATION_2026-11-16.md`.
- The 16 K and 12 derived L source seeds have matched-view sheets and reproducible
  diagnostics. K01–K16 and corrected L01–L11 mesh and pass source/envelope checks;
  L12 is refused for width 633.063 mm. CGAL detected no self-intersection in those
  27 saved open quarter meshes. This does not certify continuous surfaces, mirrored
  volumes, convergence, driver field or acoustic performance. The L lip is tangent
  to the discrete parent interpolant; its continuous-source fidelity is unproven.
- The separately supplied single-file HF1440 gallery describes six *existing*
  `iwata_ar` J seeds and six preview-only K seeds with a different mm sweep law;
  they are not identical to the earlier 28-seed pack. See
  `docs/research/typologies/hf1440_diverse_2026-11-16/RESULTS.md` for exact outcomes,
  generator compatibility and J3's 87-degree stop refusal. No new GPU or acoustic
  campaign was launched during this work. Existing concurrent queue changes are
  preserved; queue content itself is not evidence that a job ran or passed.
- Focused family tests passed; the broad run reported 259 passes, eight temporary
  Windows hard-link permission failures later passed outside the sandbox (18 worker
  tests), and two catalog failures fixed by regeneration (38 catalog tests passed).
  GUI and preview tests passed (41). No claim of a complete full-suite pass.

## 2026-11-16 (16:30) - Klangfilm-Lame geometry family implemented (CPU only; no GPU, nothing queued)

- New `tools/geometry/lame_cap.py` (superellipsoid-cap area, quintic C2 gate, ratio-locked area solve) and
  `tools/geometry/klangfilm_lame.py` + `klangfilm_lame_cli.py` (`rows.type: klangfilm_lame`, schema `klangfilm-lame-v1`).
  Knobs: fc_hz, aspect, lame_p, end_frac, rim_sweep_ratio, morph_frac; source blend OFF (`source_blend_ratio` 0,
  `entry_half_angle_deg` only used when blend > 0) and pinned. The 2018 port `klangfilm_ellipse.py` is untouched.
- Throat provenance (v3 addendum): HF1440 publishes NO numeric exit angle; `exit_angle_deg: 2` stays a simulation
  assumption (meta `angle_provenance: assumed_legacy`). Raw parent wall half-angle is derived: 10.617223 deg (tested).
  Nothing forces 2 deg. Diagnostics: `klangfilm_lame.diagnostics`.
- Tests `tests/test_tools_klangfilm_lame.py` (16, green): sphere/ellipsoid/area-lock invariants, p=2 reduction, throat
  round + area residual < 1e-8, sweep H-only, blend off/on, determinism. Cell `hl__klangfilm_lame_curved_v1` (not queued).
- NOT done (needs local machine): 3-D mesh/shell/normals checks, camera-matched renders, driver coupling A/B, BEM
  comparisons, `lame_tail_mode` follow_parent, true 3-D normal outer shell, JMLC-derived parent. Handoff copied to
  `docs/research/typologies/klangfilm_lame_handoff_2026-11-16/`. Direct port of the non-commercial 2018 workbook: check
  licence before distribution.

## 2026-11-16 (15:00) - Every watchdog-stopped run continued; watchdog: resume-aware + pin_ignore

- Runner (`tools/run_campaign_night.py`): a job with `--resume DIR` is watched on that DIR and judged only on the rows
  it adds (a converged history no longer re-trips no-gain/stall); new watchdog key `pin_ignore: [knob, ...]` skips
  bound-pin checks for knobs at a HARD limit. Tests: 2 new in `tests/test_night_runner_watchdog.py`; runner suites green.
- Continuations (same config + brief -> same cohort; only the CMA seed differed from the files): resume +60 for
  warm s9012/s3456, R-OSSE s1234/s5678 (pin_ignore g_tmax = generator max 1.0), Crowe-X s1234 (refusal_max 0.5),
  biradial s9012, Crowe sections smooth (pin_ignore g_width_mm = 600 mm envelope); TwinRay v8 `s` lo 0.6 -> 0.35,
  reseeded from its best (5.179), new CMA s9012 (pin_ignore morph_corner_mm = hygiene floor). Tritonia2/TwinRay2
  overnight stops are superseded by the v8/v9 cells + TuRBO.
- Queue handover: the live runner (started 08:03) predates the code, so `home_day_2026-11-16` gets a STOP after its
  current job and `home_day2_2026-11-16` (the 22 pending jobs, same order) runs on a chained controller (-WaitPid).
- Envelope: owner decided (14:48) to KEEP 600 mm. Context: brief_hash covers the envelope, so editing the shared brief would
  split every landscape BO cohort. Decision pending (see ISSUES).


## 2026-11-16 (14:35) - Klangfilm elliptical horn cell (Ahlswede calculator port); day-queue TuRBO beats CMA; commit to main

- **Klangfilm elliptical horn** (owner-supplied `Klangfilm_Elliptical_Horn_Calculator_diy_v10.xlsm`): the VBA macro
  `draw_klangfilm` (Dr. Bernd Ahlswede 2018; Kolbrek 2007; non-commercial) was extracted and ported line by line to
  `tools/geometry/klangfilm_ellipse.py`; parity with the workbook's stored macro output is 0.001 mm at all 9 stations.
  Knobs: `fc_hz` (r0 = c/(pi fc): size + curl radius), `stretch` (H/V aspect at the widest point), `end_frac`
  (h_end/r0: rollback depth) from the calculator; `bend_radius_mm` (front arc seen from above, per-row rigid shift -
  the per-point version folded the lip and the mesher refused it) and `throat_ellipse` (round exit -> ellipse sooner)
  added on owner request and labelled ours. Entry point `tools/geometry/klangfilm_ellipse_cli.py` (rolled-rect bridge,
  no grid.py edit); cell `hl__klangfilm_ellipse_smooth_v7` (smooth brief). Seed 5,832 DOF, 548 x 244 mm, depth 265,
  round exit, fits; preflight 14/16. **Not queued, not owner-approved:** owner says the look still differs from the
  reference (Klangfilm is inherently short/squat; reference 4.png is long/slender - likely Le Cleac'h/JMLC or the
  diyAudio bent variants, which have no published equations). No unit tests yet. Hand-off:
  `docs/research/typologies/KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md`; sweep sheet `docs/queue/klangfilm_param_sheet_hires.png`.
- **Le Cleac'h saddle** (agent worktree `worktree-agent-a4731ed7e21e33eee`, commit 22829bc, NOT merged): per-plane
  rollback + saddle rim + enclosed bell; renders `docs/queue/lecleach_saddle_v3_*.png`, `..._FULL_*.png`. Owner: still
  not the reference look (throat too short).
- **Day queue `home_day_2026-11-16`** (TuRBO > CMA): OSSE fold warm start CMA stuck at 3.762 (no gain x2) -> TuRBO
  screen 3.33 / verify 3.80; Tritonia v8 CMA 5.69 -> TuRBO screen 4.63 / verify 5.48. R-OSSE / Crowe-X CMA re-runs
  stopped by the watchdog (no gain / bound-pins g_tmax hi, s lo). TwinRay TuRBO running at commit time.
- Committed this session's remaining local files plus the concurrent session's uncommitted
  `tools/analysis/optimizer_switch.py`, `tools/analysis/queue_score_audit.py`, `tools/night_queue/run_matched_home.py`
  (+ tests, docs `HOME_OPTIMIZER_COMPARISON/HOME_SCORE_AUDIT/MATCHED_HOME_PROTOCOL_2026-11-16`). `.claude/worktrees/`
  is not committed. Merged origin/main (docs-only) before pushing to main.


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

## 2026-11-16 (05:00) - Tritonia night cell stopped; kit-era law anchored in v8 cells

- Owner verdict on `hl__ath_tritonia_landscape_v7` mid-run (`20261116T041232Z-screen-b5380a`):
  "totally wrong geometry - the mouth ridges are wrong; polar wrong; seed looks like a square
  horn; parameters maxed out." Evidence confirmed: the v7 seed was the MILD 2025 web law
  (at-horns.eu Tritonia.txt: H/V swing ~2 deg) through a faithful morph, and every fold-carrying
  knob was searched wide (cos2p amp up to +10 = inverted fold, corner down to 0, morph_fixed to 0.4,
  fold_h to 0): CMA walked into a smooth pillow bowl, no boat folds. s1/s2/morph_fixed boxes had
  the seed exactly on their lo bound; a0 maxed at hi, k at lo, L pegged at hi. The inline
  `target.coverage_v_deg: 60` disagreed with the brief it loads (80x50).
- Isolation (offline meshes, no code change): morph OFF retains the pinch; morph ON (explicit W/H
  and auto W/H) both flatten the mild-law pinch into a bowl/pyramid. The fold look therefore comes
  from the STRENGTH of the per-azimuth law, not from a mesher bug: the fork's morph matches the
  ATH law in ATH_CORE_TWINRAY_MORPH_2026-10-25.md exactly.
- Fix without changing any package: the kit-era Tritonia law was already in this repo's parity test
  (fork test 260308tritonia: a = 49.5128 - 14.8405cos^2 p - 29.2180 sin^8 p; H 34.7 / V 20.3 /
  diag 40.3 deg; a0 8.0307, k 1.091, n 6.0455, q 0.98349, s 0.9859, morph rate 1.6002, corner 18).
  New configs anchor it: `hl__ath_tritonia_landscape_v8.yaml` (law reproduced to 7e-15 deg by the
  az knobs: az_a_cos_amp -14.8405/pow 2 + az_fold_v -29.218/width 23.508 deg; fold_h and cos2p
  pinned off; s1/s2 pinned; inline target 50 V; seed r0 18 / L 280 / W 430 x H 372) and
  `hl__ath_twinray380_landscape_v8.yaml` (TwinRay T3 law kept; hygiene: corner >= 8, morph_fixed
  pinned 0, fold_h/cos2p off, s1/s2 pinned, target 50 V). Seed mesh (CPU) renders the meridian
  fold + shifted diagonals that the v7 seed lacked; polar evidence lands with the queued runs.
- Night queue `home18_a_2026-11-16`: the running `a_tritonia_s1234` was stopped (recorded, GPU
  post-hygiene clean); `a_osse_fold_warm_s1234`, `a_twinray_s1234/s5678`, `a_tritonia_s5678`
  commented out of the live file (owner: "skip them, fix, put them back"). Requeued as
  `a_tritonia2_s1234`, `a_twinray2_s1234`, `a_tritonia2_s5678`, `a_twinray2_s5678` on the v8
  configs, verify group v1_stock_top2 updated to the new ids. Evidence images in
  %TEMP%/opencode/tritonia_evidence (seed/best polars, sections, morph isolation renders).

## 2026-11-16 (23:25) - A study lists its solves and renders any measured design in 3D on demand

- Owner decision: a Bayesian study is inspectable like a run - the same solve list and the same
  best-solve plots - while its Bayesian identity (policy, engine, model/diagnostics) stays separate.
  Mechanism: an **on-demand verify job** per design. No change to `studies/**`, no code-pin change.
- `data.solves` (execute + decide phases): one row per observed attempt with an identity - design
  hash, kind, J, physical, outcome, physical coverage/ripple, params/descriptors - 50 max, J
  ascending, with `n_total`/`n_measured`/`n_refused`/`truncated`. Coverage/ripple come only from a
  physical source (normalized terms are never shown as degrees/dB); a `verify_run_id` comes only from
  the solve ledger and only while that run folder still exists.
- `solve_design` job (`gui/study_jobs.py`, GPU): writes a real standalone verify run
  `runs/<utc-ts>-studyverify-<hash6>` (config snapshot, `run.json` with `study_provenance`, one seed
  row), then runs the existing `verify --run <dir> --verify-dir <dir> --designs <hash>` body, so
  `designs/<hash>/{metrics.json,response.npz,mesh.msh,design.json}` exist and `#/run/<id>/3d` renders
  the design unchanged. The child owns the GPU lock (`HORNLAB_GPU_LOCK=refuse`, one CUDA solve at a
  time) and refuses - with a job reason and no run dir - when the lane is held, the design is
  unknown/unmeasured, or the study has no results or recorded config. `(study, design) -> run_id` is a
  small ledger beside the registry: no new artifact kind, no `studies/**` edit.
- Study page: a **Solves** table (Design -> `#/run/<id>/3d` once solved, plus a verify link; Kind, J,
  Physical, Outcome) with a per-row **Solve in 3D** and an explicit reason when disabled.
- Tests (19 new): `tests/test_gui_study_solves_view.py` (J order + missing-J last, bounded/truncated,
  physical-only units, missing artifact invents nothing, ledger link only while the run exists, active
  job) and `tests/test_gui_study_solve_design_job.py` (real standalone run dir, GPU-held refusal,
  unknown design, no results, unmeasured design, no recorded config, ledger link, duplicate submit
  reuses one run, server routing, panel exposure, a failed verify never advertises a finished run);
  `tests/gui_study_lifecycle.mjs` cases 14-15. 47 tests green.
- Built in the `studyview-wt` worktree (`feat/study-verify-view`) because a study night was live and
  `gui/**` is inside `EXECUTION_CODE_FILES`; merged here while the night was in a search step.
- **Not exercised yet:** a real GPU verify click and the resulting 3D render (the lane was busy);
  per-design curve persistence (so old designs stay viewable without a re-solve) is not done.

## 2026-11-16 (23:10) - The Runs page was still blind to BoTorch studies; it lists them now

- Follow-up to the entry below: after Status/Home/sidebar carried the night, **Runs** (`#/runs`) still
  showed only `<ts>-screen-*` folders, so a running BoTorch study - the thing being asked about - was
  absent from the page people open to see what is running.
- `viewRunsList` now fetches `/api/status` and `/api/studies` in parallel with `/api/runs` (both
  optional, an older server 404s harmlessly) and renders, above the filters:
  a **"Running now - night <name>"** card (same one as Status/Home) and a **"BoTorch studies"** table
  listing the studies the night is working on *right now* - name, registry root, revision, a `running`
  pill and a link to the study's Live tab - plus one line saying a study is a registry + package, not a
  run folder, and that completed studies stay on Bayes -> Studies.
- "Running" is not inferred: the row appears only when the study id is in an annotated open queue step
  (`open_step.study_id`, resolved server-side from the step's `--root`). With no study running the card
  says "No study is running right now." and the runs table is otherwise untouched.
- Verified in the browser against the live night: `#/runs` shows the night card (`a_turbo_ath14`,
  study run (BoTorch), 11.1m elapsed) and the BoTorch studies table with the running study, above the
  normal 537-run table. `node --check` clean; `gui_study_lifecycle.mjs` still ok.

## 2026-11-16 (23:00) - A running BoTorch study was invisible in the shell; it is not any more

- Observed live: night `home18_a_2026-11-16` (runner started 22:09) ran `prep_a_turbo_ath14`
  (bayes-venv `prepare_study.py`, 22:25:54 -> 22:32:30, exit 0) and then `a_turbo_ath14`
  (`studies.cli run --execute`, started 22:32:30). A BoTorch study was executing while Home said
  **GPU Idle**, the lane panel said "not running - stale lock left by c1_core_law_wide_s2402", and
  the nav pill said "stopped search - no resumable run folder". Each line was true about *locks*;
  together they read as "nothing is running".
- Cause: every running surface keys off a lane lock or a `runs/<ts>-screen-*` folder. A study prep
  or run takes the GPU lock only **per solve**, so between solves it holds nothing, and a study is
  not a run folder. `/api/status` already shipped `queues[].open_step`; nothing rendered it as a
  headline and nothing linked it to the study.
- Fix: (a) Status and Home get a **"Running now - night <name>"** card naming the open step, its
  kind (BoTorch prep / BoTorch run / search / verify / diagnostics), elapsed time and the study it
  belongs to, with **Open the study live view**; (b) the sidebar gets one `NIGHT <step> - <kind>`
  line under the lane chips, so every page shows it; (c) the queue timeline marks only the **last**
  unclosed START as "running" - an earlier step with no END reads "no END line" (today
  `a_ext_v8_s1234` was shown as running for 30+ min after the runner reloaded the night file and
  moved on); (d) `server.py::_annotate_night_studies` resolves the step's `--root` to the study id
  and label, reading **that one registry** (a `list_studies` walk over all 17 roots pushed the
  Status first paint past 4 s; one root lookup is ~1 s cold).
- Verified in the browser against the live night: Status/Home show `a_turbo_ath14 (study run
  (BoTorch))`, "7.6m elapsed", the study label, and the link opens the study's Live tab with the KPI
  strip live ("Screens used / total 2 / 60", verify 0/6, refusals 0) while the run is in flight.
  `pytest tests/test_gui_shell_ux.py tests/test_gui_brief_authoring.py tests/test_gui_studies_module.py
  tests/test_gui_study_adapters.py tests/test_gui_study_lifecycle.py tests/test_tools_night_status.py`
  -> 46 passed; `gui_study_lifecycle.mjs` ok.
- Still open: the Live convergence chart says "results artifact is missing" until the run writes
  results (the KPI strip already advances from the attempt journal); `tools/night_status.py` still
  lists superseded steps as "running job"; the GPU lock card reads "stale" between solves because
  the lock's pid is the per-solve worker.

## 2026-11-16 (late) - `feat/bo-gui` MERGED into the GUI branch; `diagnose` proven on real studies (one real bug); Bayes deep links fixed

- **Merge gate (STEP 0)** at 20:54: `tools/night_status.py` -> no `hornlab-search search` process, both lane
  locks free, no Julia host; the 20:08 `bo_cov_pilot` queue log ends "queue done". `feat/bo-gui`
  (`b0f669d`, which already contains its own `4808863` merge of sab-home) merged into
  `feat/sab-home-2026-11-14` as **`5b78c6c`**. **Not merged to `main`** - the owner gate is unchanged.
  A separate session started the 25x2 CMA screens at 21:06 and committed `ad1a5e0`/`ab2d807` on top of
  the merge; that work is theirs and was left alone.
- **Conflicts (4).** `CONTINUITY`: union, newest first (cloud entry -> 20:08 pilot -> section-pucker ->
  globe; the globe heading lost its "(latest)"). `BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md`: add/add, kept
  the cloud scope note (HEAD side was empty). `gui/data_studies.py`, `gui/static/studies.js`,
  `tests/test_gui_study_adapters.py`: kept the **local** turbo card (`scalar, trust region`, requires
  `training_set`+`pool`) - the cloud's `good_basin` requirement has no backend counterpart
  (`bo/policy.py` labels turbo "scalar Bayesian, trust region"; `propose_turbo` takes a pool).
- **Mojibake:** merged CONTINUITY carries the correctly encoded side (547 `â€` / 65 `Ã` / 185 `Â`
  sequences = origin/feat/bo-gui's count, down from HEAD's 568/69/188). Every heading on both parents is
  present exactly once; the 35 duplicate headings are pre-existing legacy text.
- **Suite (the STEP-2 selection, 69 files):** `pytest tests/test_gui_* tests/test_study* tests/test_studies_*
  tests/test_bo_diagnostics.py` -> **601 passed, 1 skipped** (the skip is `test_bo_diagnostics` in `.venv`,
  which has no botorch; it passes 5/5 under the bayes-venv). `compileall` exit 0;
  `node tests/gui_study_lifecycle.mjs ...` -> "study lifecycle ok". The two cloud-only failures pass
  locally as predicted: `test_gui_bridge_preview` (6) and
  `test_study_production::test_execution_requires_current_measured_cohort_dependencies` (4 params). The
  single pre-fix failure was the stale balloon test: `app.js:188` is
  `/^#\/run\/(.+)\/balloon(?:\?(.*))?$/`; the test now matches that literal with `re.escape`.
- **`diagnose` on real studies** (`oc-wt/bo-study/bayes-venv`): scalar `bo_s31001` (n=185, d=6) 41,895 B,
  185/185 LOO rows, 6 slices x 25; Pareto `pareto_s63001` (n=136, d=8) 112,868 B, 136/136, 8 slices x 25,
  6 front ids, `hv_trace` 13.6729 -> 19.7767 non-decreasing. Both attach in the registry (kind
  `diagnostics`, schema `study-model-diagnostics-v1`) and re-run idempotent.
- **Real bug found on real data (fixed):** prefix hypervolume *decreased* by 3.5e-15 eight times - BoTorch's
  box decomposition sums in an order that depends on the prefix size. `_pareto_block` now clamps at the
  running maximum and coalesces sub-tolerance steps (`HV_REL_TOL = 1e-12`); regression test
  `test_pareto_hv_trace_monotone_on_large_realistic_front` (136 rows, repeated measurements, strict
  `b >= a`) reproduces the old failure. Synthetic n=12 x d=2 could never have caught it.
- **GUI, real payloads (server restarted):** the Explain "Compute model diagnostics" button ran the CPU
  job end to end on `bo_cov_s71001` (231 rows, d=9): job `2151ab26...` -> artifact `c9fdd6b5...` (58,236 B),
  LOO scatter with ±2σ whiskers + y=x guide + chips n 231 / ±2σ coverage 92.6 % / rank rho 0.973 /
  RMSE 1.372, and 10 slice small-multiples. Before the job both places say "not computed yet" / "missing".
- **Fixed in the GUI:** (a) `#/analysis/study/<id>` redirected to `#/bayes/study/<id>`, which matched no
  route and printed "Unknown view"; it now lands on `/overview` via `studyLinkHash()`, honours `?phase=`,
  preserves other query keys, and a bare `#/bayes/study/<id>` is accepted too. (b) the Live tab decides
  from a server-side `package_present` flag in the panel payload (every phase), so it appears on first
  load instead of after visiting Execute; a package-less study at `/live` still falls back to `/overview`.
  (c) `compare_methods.js` breadcrumb `#/analysis` -> `#/bayes/studies`.
- **Pareto card uses the diagnostics** when present: front size ("6 designs across the 136 training rows"),
  a step-after prefix-hypervolume chart (`hv_trace`), and a "model front" pill on matching rows - matched on
  `observation_id` because `front_ids` are training-row ids, not the shorter `design_hash`. Absent/unusable
  diagnostics leave the card byte-identical.
- **Chart/shell polish (both themes, 1440 + 500):** one knob-name caption per slice (it printed twice), a
  filled ±2σ band via a new `chart({area})` option (was two dashed lines and no fill), LOO whiskers thinned
  to a readable envelope with all 231 rows kept, the Live KPI strip's short row no longer shows a `--rule`
  slab, and the 500 px nav wraps instead of clipping (the BAYES items were unreachable).
- **Re-prepare:** `tools/bo_compare/preflight_arms.py --budget-profile comparison-25x0 --min-rows 100` is
  exit 0 for all four staged arms with `execution_pins_match: true` (cov 231/d9, ath14 219/d14, corelaw
  206/d9, hvlaw 136/d8). Nothing was reprepared on purpose: the three unlaunched arms have no package yet
  (their own prep job creates it at launch, so it carries the then-current pins and a fresh 6 h deadline),
  and every existing package belongs to a finished study. `gui/**` is still inside
  `EXECUTION_CODE_FILES`, so any prepared package is refused after a GUI edit - unchanged owner decision.
- Not done: `main` merge/PR (owner), the legacy `#/analysis` "Analysis reports" link on the studies list,
  and the `night_status` phantom-running-job noise - all recorded in `docs/ISSUES.md`.

## 2026-11-16 (pilot) - 25 x 2 section home pucker vs square X; square X wins J

- GPU was free after `bo_cov_pilot_2026-11-16` finished; no running job was interrupted.
  Four screen searches, 25 evaluations each, seeds 1234/5678, same home brief.
- Results: `rf__section_axial_home_v7` best **17.3982 / 17.3970** (seed 17.9511);
  `hl__crowe_x_square_v7` best **8.8171 / 8.2046** (seed 9.2356). Square X is 9.2 J better
  as well as the closer reference look.
- Section home: width 593-599 (near the 600 envelope), junction 16.0-16.1 (lower bound),
  crown 33-36, axial H 6.8-8.4, axial V **0.37-3.35** (the vertical pucker collapses). The
  useful dimensions are mouth width, junction and crown; the axial pucker is secondary.
- Square X: `sf_amt` **0.42-0.47** (below the 0.60 visual seed), a_h/a_v 33-34, L 222-225,
  s 0.28-0.32, n 2.06-2.11, lip 22-27, wrap 113-121. It had 12/8 invalid_envelope refusals;
  the width/height box can exceed 600 x 480.
- Runs: `runs/20261116T015510Z-screen-e75ec8`, `...0d29d7`, `...3943f0`, `...87354c`.
  Evidence: `docs/renders/2026-11-15-25x2/README.md` + `best_designs.png`.
- 25 evals is a coarse pilot for 8 active dimensions; a real comparison needs 60-96 per arm.
- **Next:** cut `rf__section_axial_home_v8` with `g_axial_v_mm` fixed at 0, `g_axial_h_mm`
  0-12 optional, junction lower bound 12; cut a square-X v8 with `sf_amt` seed 0.45 and tighter
  envelope coupling; 60-96 evaluations. Decide whether the square X (better J, square look)
  replaces the 80x50 landscape target or stays a look-first probe. GUI restart/hard-refresh after
  pulling.

## 2026-11-16 (latest) - BO GUI cloud pass on `feat/bo-gui`: sab-home merged, BoTorch diagnostics, Bayes nav + Live tab; no solves

- Cloud session (offline, no GPU, no `runs/`, no merge to main). `feat/bo-gui` merged
  `origin/feat/sab-home-2026-11-14`; only docs conflicted (union; CONTINUITY kept the correctly encoded side).
- New `hornlab_search/bo/diagnostics.py` + `studies/cli.py diagnose`: artifact kind `diagnostics`, schema
  `study-model-diagnostics-v1` (BoTorch 0.18.1 `efficient_loo_cv` LOO, 25-point 1-D slices through the incumbent,
  Pareto `front_ids` + `hv_trace`). It refits from the stored training set, so it works for old studies.
- GUI: `sensitivity_view` adds slices, `calibration_view` adds a "LOO on training data" half, `pareto_view` adds
  diagnostics front/HV when present (else `available:false, can_compute`). `diagnose` is a CPU job kind
  (`study_jobs.py`, `server.py`, `service.reserve_cpu_job`) shown as an Explain-phase action.
  `study_charts.js` draws slice small-multiples and the LOO scatter.
- Nav: top-level **Bayes** group (`#/bayes/studies`, `#/bayes/board`); old `#/analysis/studies*` and
  `#/analysis/compare-methods` redirect. Study page gets a **Live** tab (KPI strip, convergence, current pick, 10 s poll while running).
- Tests (cloud): `tests/test_bo_diagnostics.py` (4), 3 new cases in `test_gui_bo_views.py`, `gui_study_lifecycle.mjs` ok.
  Environment-only/stale failures, not from this work: `test_gui_bridge_preview` (6, needs `hornlab_mesher`),
  `test_study_production::...current` (mesher pin), `test_gui_brief_authoring::test_balloon_entry_point_already_wired`
  (route regex changed on the sab-home branch).
- **Not verified:** `diagnose` against a real study (no data in the cloud box); no screenshots. Do the visual pass locally.
- **Next (owner, local):** after solves finish, run `diagnose` on the fixture studies, start the GUI and look; merge into the GUI checkout branch.

## 2026-11-15 (later) - Section pucker folded into canonical family; square-X cell added

- Verification: legacy `sp__strong_v7` is the canonical section family with axial pucker
  7/9 mm; `sp__strong_v7` vs `rf__section_axial_v7` at 7/9/0.30/0.80/0.96 differs by at most
  **9.6e-7 mm** on the inner grid. The pucker is a parameter, not a typology.
- Parameter correction: the fixed 417 x 203 `rf__section_axial_strong_v7` is the exact
  `strong_a.png` visual reference, not an optimization cell. Its old depth 194-202,
  `h_depth_scale` 0.99-1.01 and crown 18-22 boxes were cosmetic. The latest home-panel best
  sat at width 579.7, height 292.9, depth 262.1, `h_depth_scale` 1.098, crown 39.7,
  junction 24.4; those are the acoustic levers.
- New optimization cell `rf__section_axial_home_v7`: width 480-600, height 220-420, depth
  170-300, `h_depth_scale` 0.9-1.1, crown 10-40, junction 16-48, axial pucker 0-12/0-14;
  seed = the home best + 7/9 pucker; mesh 580 x 290 x 274 mm, 3,988 DOF. Eight active keys;
  25 evals is a coarse pilot (home panel used 96).
- GUI catalog: removed the three `sp__*` entries; added `rf__section_axial_home_v7` and kept
  `rf__section_axial_strong_v7` as the visual reference. `hl__crowe_x_square_v7` remains the
  square-X look. All preview with `available:true`, `shape3d.available:true`.
- Renders: `docs/renders/2026-11-15-pucker/strong_a_vs_canonical.png`,
  `rf__section_axial_strong_card.png`, `rf__section_axial_home_card.png`.
- 25 x 2 solve plan now targets `rf__section_axial_home_v7` and `hl__crowe_x_square_v7`
  (seeds 1234/5678), ready but **not launched**: `bo_cov_pilot_2026-11-16` holds the GPU
  lock/Julia host. Do not interrupt it.

## 2026-11-15 (20:08) - OWNER AUTHORISED ONE BOTORCH ARM; cov pilot LAUNCHED

- Owner chose a single-arm pilot instead of the four-arm night. Launched detached at 20:08 (controller pid
  26816, parent WmiPrvSE) via `tools/night_queue/launch_detached.ps1` -> `queue.ps1` ->
  `run_campaign_night.py`: night `bo_cov_pilot_2026-11-16`, admission packet
  `docs/queue/bo_cov_pilot_2026-11-16.admission.json` (3 job ids: preflight, prep_cov, bo_cov).
- Arm: `p80x60__ext_throat_hvlaw_cov_v7`, 231 strict rows, d=9, seed 71001, `comparison-25`
  (25 screens + 6 verify = 31 calls, 150 attempts). Preflight job passed (rows/pins/profile all ok);
  prep reported `training rows: 231 (min 100)`. Logs: `runs\nights\queue_bo_cov_pilot_2026-11-16.log`,
  `runs\nights\bo_cov_pilot_2026-11-16_runner_{stdout,stderr}.log`; night dir
  `runs\nights\bo_cov_pilot_2026-11-16`.
- `queue.ps1` gained `-Admission` and `-DryRun` (it previously forwarded only `--night`, which
  would have bypassed the new admission gate). Full chain dry-run tested: admission accepted, 3 jobs,
  exit 0; a bad packet aborts with exit 2.
- The other three arms (ath14, corelaw, hvlaw) remain staged and unadmitted in
  `docs/queue/bo_multityp_2026-11-16.yaml`.
- Owner decision 20:40: **skip verification entirely** for the exploratory arms. New profile
  `comparison-25x0` (25 screens + 0 verify = 25 calls, 150 attempts) in `studies/package.py`;
  the three staged arms and their admission packet use it. `comparison-25x2` (25+2) also exists.
  Evaluator change: `_build_verification_plan` now truncates to the remaining verify capacity and
  reports `shortfall`/`audit_shortfall`; with zero capacity it emits no verification candidate at
  all, so the arm ends `pool_exhausted` instead of `budget_exhausted_or_stale` (the old behaviour
  when a plan exceeded the cap). Tests: `test_study_evaluator.py` (0- and 2-verify cases) and the
  budget-profile suite. Trade-off recorded: a screen-only arm has **no verified finalist**.
  The running `cov` pilot keeps its prepared `comparison-25` package (6 verify) - repackaging
  would start a new package with zero observations and discard ~13 solved designs.
- Stale-lock observation: `runs\.gpu.lock` held pid 28408
  (`rf__rect_radial_wide_v7` screen 25 @ seed 1234, started 19:59:43) which was already dead; the
  runner took the lock over per policy. That CMA run `20261116T005943Z-screen-20db0d` stopped ~20:01
  with partial records and is NOT ours to resume; whoever owns the radial-wide cell must decide.

## 2026-11-15 - Full-circle globe view from the stored balloon; no new solves

- The `Directivity (isobars)` view now has three modes: `Rectangular | Globe | Full globe`.
  `Globe` is unchanged (the ±90° H/V cuts wrapped into a half-circle). `Full globe` re-samples the
  stored balloon around a closed 360° great circle in the H (x-z) or V (y-z) plane: 0° front at the
  bottom, ±180° at the top, log frequency outward, same 3 dB isobar bands.
- Data cost: none. The balloon already stores the full sphere (screen 16×32 = θ 12°, φ 11.25°;
  verify up to 23×45 = φ 8°), so the back half is interpolated from existing samples. The cuts stay
  finer (2.5°) but only ±90°; the balloon is the source for the full circle.
- `gui/data.py::design_curves` adds `angles360` (145 pts, −180..180), `polar_h360`, `polar_v360`
  from `_balloon_full_circles` (bilinear on the theta-major grid, wrap-aware in φ, normalised to the
  on-axis pole row, clipped at −40 dB). A run without a balloon omits the keys and the view skips
  those panels. `charts.js::globePlot` detects a ±180° span and draws a true circle (rim, rings,
  f0 ring, single `±180°` label) with no NaN.
- Verified on live run `20261116T003142Z-screen-981f59`: best and seed both return H/V 360° slices
  (18 freqs × 145 azimuth); a real-payload render produces full circles. The API must be restarted
  after the change — a running GUI holds the old `data.py` import (static JS is `no-store`), which is
  why the new mode showed blank panels until the 8765 server was relaunched.
- Tests: `tests/test_gui_globe_full.py` (balloon front/back sampling + node full-circle render) and
  the `-k gui` suite pass. The only failure is the pre-existing `test_targets` case on
  `examples/catalog.gui.yaml` (tracked in HEAD, unrelated).

## 2026-11-15 (later) - Spiral pucker vs ATH radial ridge; wide radial-relief cell visible in GUI

- Research note: `docs/research/typologies/SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15.md`.
  The rolled spiral's `pucker_*` is a z-only corrugation; its window saturates at 180 degrees
  and stays on through the 270-degree lip, so it bows the H/V faces forward and leaves a wavy
  rim. It is not ATH's radial ridge. The screenshot's `az_*` per-direction law is radial; the
  visible `b=1.2` / `amp=11.5` / `cos=-15` makes V dominant (CORE uses `b=0.618` / `amp=35`),
  which is why the vertical faces bow out. ATH Tritonia/CORE open the diagonal 7-10 degrees
  wider; the ridge is the integrated per-direction flare.
- The existing `rolled_family` radial mode pulls H/V inward and leaves the diagonal as a
  ridge. New shape-only cell `rf__rect_radial_wide_v7`: same spiral base, inward seed 12/16 mm,
  bounds 0-30 / 0-40 mm, window 0.50/0.80/0.96; mesh 541 x 299 x 241 mm, 5,096 DOF;
  `tests/test_rolled_family_geometry.py` 32 passed.
- GUI: added `examples/catalog.gui.yaml` entry and regenerated the parameter catalog
  (`param-catalog.v1.json`, `PARAMETERS.md`, `TYPOLOGIES.md`). The typology list now shows
  `rf__rect_radial_wide_v7` (enabled, 5 knobs); suggested starts 6/8 subtle, 12/16 clear,
  16/22 dramatic. The sandbox preview now resolves `rolled_family` through its canonical
  `resolve_grid` (the generic rows march rejected the `mode` key); verified `available:true`,
  `shape3d.available:true`, dims 535.7 x 294.7 x 235.1 mm. Hard-refresh and restart the GUI
  server (the preview fix is Python code).
- Evidence: `docs/renders/2026-11-15-pucker/` (six-view comparison, relief range sheet,
  three-view card). No GPU solve; the 2026-11-15 17:15 owner pause still binds. The new
  config is uncommitted.

## 2026-11-15 (late) - BoTorch readiness pass; 4-typology 25-screen campaign STAGED, not launched

- Engine/device: GP fit stays CPU float64 on purpose (consumer Ada FP64 runs at 1/64 of FP32;
  a torch CUDA context costs 0.5-1.2 GB VRAM beside the BEM solver; BoTorch's fused qLogEHVI kernel is
  CPU-only). Rationale + sources: `docs/BAYESIAN_STUDIES_RUNBOOK.md` "Why the GP fit stays on the CPU".
- `ninja 1.13.2` is present in the bayes venv; the fused qLogEHVI kernel was compiled once under MSVC
  `vcvars64` and the built module installed as `bayes-venv\Lib\site-packages\logei_fused_ext.pyd`
  (BoTorch imports that before trying the JIT, so no PATH/vcvars is needed at run time). Verified
  `logei._C is not None` and the Pareto suites run warning-free. Rebuild after a torch/Python upgrade.
- New budget profiles `comparison-25` (25+6=31 calls) and `comparison-30` (30+6=36); production
  `study package --budget-profile` and `tools/bo_compare/prepare_study.py --budget-profile`.
- `prepare_study.py` can now stage any typology with `--config/--brief` (not only a registered task
  name); the >=100-row data gate is unchanged and still runs first.
- Four objective-v7 tasks registered with measured strict cohorts: `atlas__osse_ext_throat` (256, d=6),
  `p80x60__ext_throat_hvlaw_cov_v7` (231, d=9), `p80x60__ath_core_14in_home700_v7` (219, d=14),
  `p80x60__ext_throat_corelaw_v7` (206, d=9). Below the floor: rounded-rect 75, petal 46, Le Cleac'h 1,
  ES rollback 1. Crowe panel/ES-600 cannot be trained by the strict builder (bridge rows kind unknown).
- Dependency-pin gate (`production.py:170-181`) caught the largest cohort: `atlas__osse_ext_throat` was
  solved with `hornlab_beat_bem 0850ef39` while the worker runs `38e5b1f8`, so it is NOT executable
  today. The staged night therefore uses `hl__ext_throat_hvlaw_v7` (136 rows, pins match) as arm 4;
  the atlas cohort stays on disk as evidence. `preflight_arms.py` checks pins, not just row counts.
- New `tools/bo_compare/preflight_arms.py` (read-only registry+cohort+row+profile proof) and an optional
  `run_campaign_night.py --admission PACKET` gate (night + allowed_job_ids; whole night refused otherwise).
- Staged, held: `docs/queue/bo_multityp_2026-11-16.yaml` + `.admission.json` +
  `docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md`. Four scalar arms x 25 screens + 6 verify, seeds
  71001-71004. No solve was launched; the 2026-11-15 17:15 owner pause still binds.
- GUI: TuRBO ("scalar, trust region") is now a policy card in both the Python fallback list and
  `static/studies.js` (`POLICY_MODES` previously made the card a no-op).
- Docs corrected: runbook said production supports only `scalar` (it supports scalar/turbo/pareto);
  `bo/__init__` docstring said `bo/metrics.py` was deferred (it is landed, v4+v7) and now exports
  `POLICY_TURBO`; the BO_EXT plan and the study-orchestrator spec status lines were stale.
- Verification: 172 BO tests green in the bayes venv (16 files, real torch/botorch/gpytorch), 35
  package/budget/registry tests green in `.venv`, 17 admission-gate tests + GUI studies suites green,
  `preflight_arms` ready for all four arms, night dry-run accepted with the admission packet.
## 2026-11-15 (19:15 local) - SPIRAL ADMISSION DECISIONS FROZEN FOR PILOT; RELEASE STILL OWNER-HELD

- The concurrent rolled-readiness pass completed the senior admission ledger for the priority
  `hl__rolled_es_spiral_v7` cell: source interface = explicitly idealized 18 mm / 2 deg historical interface;
  objective = the existing v7 brief frozen for pilot comparability (no slope swap; the smooth brief stays an
  offline experiment); body witness and control-sensitivity gates passed; convergence stays open and is carried
  by the pilot verification. `admission.json` records the spiral cell as approved at gate level but
  `full_search_released` remains **false**: no controller was launched and no solve was released.
- Evidence: `docs/research/typologies/audit_2026-11-15/ADMISSION_DECISIONS.md`,
  `SPIRAL_CAPABILITY.json`, `spiral_body_witness.json`, `SPIRAL_ACOUSTICS.json`, `RUNS_AND_QUEUE.md`; accounting
  and the verify route are recorded in the decision doc. No original generator/brief/recipe was edited.
- This does **not** settle the final-ranking brief. The owner gate remains: brief/DI-slope for the final ranking,
  the lip/waist geometry law, the Crowe-section junction rebuild, then night F. Night E remains stopped; no new
  solves and no Bayesian jobs.

## 2026-11-15 (19:00 local) - GUI BRIDGE CELLS VIEWABLE; HOME-LANDSCAPE PACKET; COMMIT/PUSH

- GUI typology exposure is complete: the 8 stock-loadable home cells are in `examples/catalog.yaml`; the 3 bridge
  cells (`hl__rosse_rect_cd_v7`, `hl__rolled_es_spiral_v7`, `hl__crowe_panel_home_v7`) are in
  `examples/catalog.gui.yaml` and now preview in the GUI sandbox through `tools/geometry/gui_preview.py` (fresh
  process, one bridge installed; 2D/3D, sections, sliders, tooltips). They remain launch-disabled for the stock
  campaign and show a `preview only` pill; run them via their own CLI. Live GUI: `http://127.0.0.1:8765/#/typologies`.
- The home-horn decision packet `docs/research/typologies/STARTING_SEEDS_2026-11-15.html` now has shaded 3D heroes,
  front views, 360 turntables, horizontal/vertical sections, per-cell parameter tables, issues log I1-I12, research
  summary and options. It is supported by `STARTING_SEEDS_PLAIN_2026-11-15.md`,
  `HORN_WHITEPAPERS_2026-11-15.md`, `BIRADIAL_CROWE_STUDY_2026-11-15.md`, `BIRADIAL_CROWE_SOURCES_2026-11-15.md`
  and `SCORING_NON_CD_SOURCES_2026-11-15.md`.
- Night E remains stopped (runner 11172/controller 36556 killed; seed 5678 stopped at ~62/96; GPU cleaned). No new
  solves, no night F. The brief/DI-slope + lip/waist geometry decision remains the top owner gate.
- Both night-E Crowe runs were rescored under the smooth brief: seed 1234 best 6.84 vs base 16.92; partial seed 5678
  best 6.83 vs base 17.06. The Crowe-section outer-body/lip fold is still a real defect; scores provisional.
- Verification: 186 GUI/parameter tests passed; `tools/gen_param_catalog.py --check` passed; compileall clean for the
  GUI bridge helper/data/catalog/test. This commit also preserves the concurrent rolled-family senior-audit
  documentation/evidence pass (no generator/solve changes) and leaves its source/config/run history untouched.

## 2026-11-15 â€” Rolled-family senior audit; spiral diagnostics and guarded queue

- Read `docs/research/typologies/audit_2026-11-15/HANDOFF.md` then `READINESS.md` in that directory.
- Owner subsequently allowed a few isolated acoustic diagnostics; full searches remain held on unresolved families. No Bayesian work on new typologies. Two real uncached spiral seed evaluations completed, EPW6/8, same design,4500/5277DOFs,J29.915059/29.913599. Not established convergence; GPU workers cleaned afterward.
- New queue draft `docs/queue/rolled_readiness_2026-11-15/pilot_HELD.yaml`: two guarded spiral RNGseeds1234/5678,30 valid-target evaluations each. No controller launched; admission is false.26 frozen horn/brief config copies load; other families excluded pending gates. Retry/validation cost must be reconciled before campaign release. Preserve old D/E history; do not resume its unused BO/long-run tail.
- Research corrected source/construction/objective claims: HF1440 combined exit does not establish2deg cone; Hypex mislabeled Crowe variant; distd is DI std, not detrended smoothness; actual Gaussian DI target13.079574dB; raw Crowe normal angle is not proof of inverted winding. Primary sources,600-row domains,17-run histories,32 exact offline score replays, original-mesh witnesses and bounded implementation prompts saved.
- Verification:61 native CPU tests plus9 wrapper checks and5 generic strict-resume tests; dedicated spiral real-evaluator/CPU-mesh/synthetic-backend resume preserved5 cached rows and added4, all9 full surfaces replayed. Synthetic responses are clearly segregated. Original generators/briefs/configs and concurrent dirty work preserved. No commits.


## 2026-11-15 â€” Rolled-family senior audit; spiral diagnostics and guarded queue

- Read `docs/research/typologies/audit_2026-11-15/HANDOFF.md` then `READINESS.md` in that directory.
- Owner subsequently allowed a few isolated acoustic diagnostics; full searches remain held on unresolved families. No Bayesian work on new typologies. Two real uncached spiral seed evaluations completed, EPW6/8, same design,4500/5277DOFs,J29.915059/29.913599. Not established convergence; GPU workers cleaned afterward.
- New queue draft `docs/queue/rolled_readiness_2026-11-15/pilot_HELD.yaml`: two guarded spiral RNGseeds1234/5678,30 valid-target evaluations each. No controller launched; admission is false.26 frozen horn/brief config copies load; other families excluded pending gates. Retry/validation cost must be reconciled before campaign release. Preserve old D/E history; do not resume its unused BO/long-run tail.
- Research corrected source/construction/objective claims: HF1440 combined exit does not establish2deg cone; Hypex mislabeled Crowe variant; distd is DI std, not detrended smoothness; actual Gaussian DI target13.079574dB; raw Crowe normal angle is not proof of inverted winding. Primary sources,600-row domains,17-run histories,32 exact offline score replays, original-mesh witnesses and bounded implementation prompts saved.
- Verification:61 native CPU tests plus9 wrapper checks and5 generic strict-resume tests; dedicated spiral real-evaluator/CPU-mesh/synthetic-backend resume preserved5 cached rows and added4, all9 full surfaces replayed. Synthetic responses are clearly segregated. Original generators/briefs/configs and concurrent dirty work preserved. No commits.


## 2026-11-15 (17:15 local) - OWNER PAUSED NEW SOLVES; BRIEF/DI-SLOPE INVESTIGATION IS TOP PRIORITY

- **Owner decision (17:15): pause the current Crowe-section run and do not run any new solves until the
  brief/DI-slope scoring question is investigated and settled.** The night-E runner (pid 11172) and its controller
  (36556) were stopped; `e_crowe_home_s5678` stopped at ~62/96 rows; `gpu-clean` run; no Julia hosts left.
- Why: the Crowe-section construction is not doing anything interesting in the current parameterisation (owner), and
  the curves/law do not have the right degrees of freedom. Objective mesh check confirmed a 153-176 deg fold with
  inverted triangles at the outer side-wall/lip junction (inner flare smooth); the other cells have no edge >150 deg.
  The current laws also have **no true lip return** and **no waist term** (see the white-paper research).
- Research to settle before new solves: the v7 fixed DI target (`di_slope_target 0`) and the `diag` fixed-round
  reference are not supported by the listening literature; no source for the "Harman 1-3 dB/oct" claim; measured
  narrowing is ~2.6 dB/oct (Le Cleac'h) and ~4.1 dB/oct (Crowe, author data); K-law correction A=0.9B gives 496/794
  mm at 700 Hz (480 mm V holds 50 deg only to ~1157 Hz). Full sources: `HORN_WHITEPAPERS_2026-11-15.md`,
  `STARTING_SEEDS_PLAIN_2026-11-15.md`.
- GUI typology exposure fixed: the 8 stock-loadable home cells are in `examples/catalog.yaml`; the 3 bridge cells
  (`hl__rosse_rect_cd_v7`, `hl__rolled_es_spiral_v7`, `hl__crowe_panel_home_v7`) are in
  `examples/catalog.gui.yaml` and are now previewable in the GUI sandbox through
  `tools/geometry/gui_preview.py` (fresh process, one bridge installed; 2D/3D sections and sliders). They remain
  launch-disabled (stock campaign cannot load the custom rows kind) and show a `preview only` pill. Live GUI
  restarted; `/api/typologies` returns 56 and the bridge preview API returns `available=True`. The generated parameter
  catalog now includes the 3 GUI-only cells (`source_status: gui-only`, `preview_only: true`), so the sandbox has
  knob docs/tooltips and no "not in the parameter catalog" warning; `gen_param_catalog.py --check` passes. New test
  `tests/test_gui_bridge_preview.py`: 7 passed; the GUI/param subset (fixer's 179 + new 7) = 186 passed. The live
  GUI is running detached at `http://127.0.0.1:8765/#/typologies` (home group); the three bridge cells open in the
  sandbox with 2D/3D previews.
- The six 360-degree seed turntables and the plain-language decision brief are in the research folder; owner judges
  the look, not a model ranking. Do not queue night F until the brief and the lip/waist law are decided.

## 2026-11-15 (16:45 local) - BIRADIAL FIX MERGED; FOUR CELLS RENDERED; SCORING RESEARCH

- Merged `fix/biradial-throat-blend` (7124902) in the no-study window; 30 CI-filtered design/mesh tests pass.
  Biradial refusal cause found: US4308932A needs `rm >= r0 + tan(a) L`; all 32/64 refusals were
  `cone_does_not_close`. New closure-coupled box (L 220-320, h_a 32-37, v_a 18-24, h_rm 260-292,
  v_rm 162-230) is **64/64** meshed, envelope-fitting, round throat; seed 560 x 350 x 258.
- Rendered all four cells (box corners + 360-degree turntables). Defect-only visual QA: ES spiral roll is a
  thin hook and high pucker adds rim ripples; R-OSSE rect rim scallops at extreme roll/exponent corners;
  Crowe-X lip is a thin flange, not an under-surface return, and 5/10 box extremes are over 600 mm;
  biradial law has no waist/lip term. Crowe likeness is for the owner to judge from the 3D renders, not a
  model ranking. Sheets/GIFs in `docs/research/typologies/img_biradial_crowe_2026-11-15/`.
- Scoring research: no source found for "Harman 1-3 dB/oct DI slope"; Olive 2004 has no slope term; CTA-2034
  12/44/44 is the PIR average. `diag` uses a fixed round reference and structurally penalises rectangular
  mouths. Owner decision pending on base vs smooth brief and night F scope.
- Night E: TuRBO rerun done; Crowe home seed 1234 done (smooth rescore best J 6.84 vs base 16.92), seed 5678 stopped at 62/62 valid rows (smooth 6.83 vs base 17.06)
  running. Objective mesh check found a 153-176 deg fold at the Crowe-section side-wall/lip junction (inner flare
  smooth; outer-body defect) - scores provisional until the junction is rebuilt. No night F written. Full detail:
  `docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md` s8.

## 2026-11-15 (15:50 local) - BIRADIAL / CROWE / ROLLED-MOUTH STUDY; HANDOFF (owner stopped the session here)

- Full handoff: `docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md` (+ `BIRADIAL_CROWE_SOURCES_2026-11-15.md`,
  `SCORING_NON_CD_SOURCES_2026-11-15.md`, renders `img_biradial_crowe_2026-11-15/`). Nothing below is committed.
- Found: the rolled-rect / pucker / section / Crowe-replica cells froze mouth W/H and 9-13 knobs (CMA re-scored the
  drawings); the rolled-rect log spiral has no constant-angle throat section and one shared H/V contour, so its knobs
  cannot set coverage; its roll is ~30 % of mouth radius by construction; Crowe-X "chunky bar" = 30-50 mm lips
  wrapped 130-160 deg; biradial throat kink (law starts at 36-38 deg at the 2-deg exit) -> domed source refusals;
  3 of 9 v7 terms assume constant directivity.
- Fair rescore (offline, all stored rows, smooth-directivity brief variant): Crowe ES sections 22.5 -> 10.5, Le Cleach
  19.4 -> 6.9, rolled-rect 27-29 -> 14-16; CD OSSE stays 2.3-2.8 and still leads; residual is mostly `diag`.
- Built (CPU-checked, unsolved): `hl__rosse_rect_cd_v7` (ATH R-OSSE per azimuth, new `tools/geometry/rosse_rect.py` +
  `rosse_rect_cli.py`; 64/64 box valid), `hl__crowe_x_osse_cd_v7` (58/64), `hl__rolled_es_spiral_v7` (62/64),
  rewritten `hl__biradial_es_style_v7` (needs the fix; 32/64 refused, cause open), brief
  `room_landscape_80x50_700_hf1440_v7_smooth.yaml`. Biradial throat-blend fix + 2 tests in worktree
  `../biradial-wt` branch `fix/biradial-throat-blend` (uncommitted; merge only while no BoTorch study runs).
- Compute: night E running (TuRBO rerun, home-sized Crowe x2, CMA data, verify, BO round 2 on ext-throat only).
  No night F yet. BoTorch stays on families with >= 100 solves.

## 2026-11-15 (14:25 local) - BO NIGHT B WAS EMPTY (ENCODER BUG, FIXED); NIGHTS D + E QUEUED; BO DATA GATE

- **Night B never solved.** `bo/data.py` refused every row with `morph_target != 1`; the landscape task has the morph off
  (`morph_target = 0`, where `morph_exponent` is just as inert), so the cohort's 136 usable rows became 0 training rows,
  `prepare_study` raised `needs_initial_data`, and the three `studies.cli run` jobs exited 0 in ~1 s (package missing).
  Fix: accept `morph_target` 0 or 1. Training set now 136/136; 102 BO tests pass; prep dry run ok.
- **GPU idle 13:36-13:54**: nights A, B, C and the rolled-rect / Crowe-section / section-pucker pilots had all drained.
- **Night D** (`home_landscape_d_2026-11-15`, started 13:54): the three BO arms rerun (scalar done 19 min, 60+6 solves),
  then Crowe ES600 x96. **TuRBO stopped at 21/60** (3 `worker_exit` ConnectionResets): a full local pytest run without CI's
  `-m "not slow and not gpu and not crosscheck"` filter ran a warm-worker GPU test mid-night and killed the shared host
  (Pareto lost 1 solve and continued). Rerun prepended to night E. Lesson: while a GPU night runs, only the CI-filtered suite.
  The Crowe jobs were briefly set to be cut by the new `tools/night_queue/cut_jobs.ps1`; **owner overruled (14:42): keep
  the Crowe jobs and make them work.** The cutter was stopped before it killed anything; night D's replica Crowe x96 runs. **Night E** chained behind D (~6 h): 5 CMA x 100 (ext-throat x2, OSSE rounded-rect x3), verify top 3 of each
  plus night C's OSSE run, cohort rebuild, BO round 2 (scalar, turbo, pareto, turbo) on ext-throat.
- **Why the Crowe / rolled-rect / Le Cleach / ES-rollback families score 19-29 vs 3.1**: same brief and objective as the
  winners, so the scoring is fair. They are undersized (Crowe mouth frozen at 417 x 203 mm, 205 mm deep; V pattern
  control lost below ~1.5 kHz) and their beams keep narrowing with frequency (dislope 8-10 vs 0.02; H 90->46 deg,
  V 137->41 deg).
- **Crowe made to work (owner, 14:42):** the replica cell `rr__crowe_panel_es600_v7` froze the mouth at the ES-600 drawing
  size and searched depth +-4%, so CMA could only re-score the replica. New `hl__crowe_panel_home_v7`: the same digitized
  H/V sections scaled into the home envelope - width 480-590 > height 220-420, depth 170-300, H/V depth ratio 0.9-1.1,
  crown 10-40, junction 16-48; seed = ES-600 proportions at 560 x 280 x 270. Measured: the swept-H construction needs
  depth <= 0.57 x width (0.66 x at ratio 1.1; height does not matter) - deeper raises `nonpositive sweep pivot`.
  Shape-check: seed + 5/6 corners mesh (3.3-6.1k DOFs, round throat, fit); preflight 62/64 box samples valid.
  Queued in night E right after the TuRBO rerun: 2 CMA seeds x 96 + Crowe-CLI verify of the top 3 each.
- **ES450-style biradial** (`hl__biradial_es_style_v7`): 17/19 screens refused, throat not round (area 1.03-1.05x an
  ellipse; `mesh/throat_check.py` tolerance 0.03). Needs a generator change (round throat blend before the per-plane
  laws diverge); not queued.
- **Owner rule: BoTorch only on typologies with existing data.** `tools/bo_compare/prepare_study.py --min-rows`
  (default 100) refuses before any study exists. Study rows do not enter `study_cohort`, so extra BO rounds need fresh
  CMA data first. Noted in the `hornlab-night-queue` skill.
- Also committed: the 2026-11-14 search-economy preflight (`tools/search_preflight.py`, skill) and the rolled-family
  generator work from the parallel sessions, after the full offline suite passed.

## 2026-11-15 - SECTION REFERENCE WITH H/V PUCKERING, VALIDATED / RUNNING

- Added a separate original H/V mouth-relief extension of the corrected section reference;
  parent modules and old recipes remain byte-identical. New opt-in section_pucker_cli.py
  covers the six source/reference inputs in recipe identity; same explicit body is solved/rendered.
- Control, moderate (H3/V4 mm) and strong (H7/V9 mm) seeds: 3306/3152/3134 DOFs;
  all round 36 mm, 417 x 203 mm outline, envelope fits. Common box depth 192..204,
  H depth scale .98..1.02, crown 18..22. Moderate H 0..6/V 0..8; strong H 4..10/V 6..12.
- All 72 bound corners passed (max 4055/6000 DOFs). Random boxes 63/64,62/64,62/64;
  five invalid_geometry refusals remain guarded/charged. No cap/density/tolerance widened.
  145 related CPU tests passed in 48.378 s, including 19 new geometry/replay/window checks.
- Night home_section_pucker_2026-11-15: three 48-attempt searches, control first, then
  top1 denser-frequency verification per arm. Detached controller 10256, WMI parent 35188,
  started 13:01:07 local; first run runs/20261115T180109Z-screen-0f2ab5.
- New gallery puckers/ includes 15 renders and full bounds/meshing evidence. See
  docs/queue/SECTION_PUCKER_PLAN_2026-11-15.md and SECTION_PUCKER_RESEARCH_2026-11-15.md.
  Acoustic outcomes remain pending; the surface is ATH-inspired, not the ATH formula.


## 2026-11-15 - VERIFICATION FIDELITY CLARIFICATION

- Inspected saved rows: section-study screen and verify both have3084 DOFs and identical
  throat/mouth/rear mesh spacing 3.573/7.146/10.719 mm. Verify uses29 frequency points,
  screen18. The 22.756 to24.299 score shift is frequency-grid sensitivity, not a spatial
  mesh-refinement result. All four completed searches and verifications remain successful.


## 2026-11-15 - FOUR HORN PILOTS AND VERIFICATIONS COMPLETE

- Original night completed 12:11:40 local; section-study follow-up completed 12:19:05.
  All four searches have 32/32 valid evaluations; all four top1 verifications succeeded.
- Screen / verify J: reference 29.423 / 31.796; moderate pucker 28.434 / 30.813;
  strong pucker 27.407 / 29.839; section study 22.756 / 24.299. Same objective-v7 brief;
  the smaller section study is not an equal-size pucker A/B. Further mesh convergence is open.
- Section-study winner 7e454d58122c at n29, first improvement n4; depth204.703,
  H-depth-scale1.02979, crown17.765. Seed J23.086. Saved winner renders and exact run
  provenance published in gallery results.html/results.json. Encoding corrected in builder.
- No outstanding jobs in these two queues; unrelated workers were preserved.


## 2026-11-15 - SECTION-CONSTRAINED ES-600 CORRECTION, VALIDATED AND QUEUED

- Owner rejected the front geometry; inspected manufacturer drawing 1148-01-001 B-B/C-C,
  ES-800 vector sections and additional ES-450/ES-250 sources. Replaced the unpublished
  panel loft with independently measured H/V profiles, swept intersection, bounded crown,
  rounded join and explicit rear body. This is an inferred reconstruction, not Crowe CAD.
- Separate crowe_panel.py / crowe_panel_cli.py; reference YAML included in replay digest.
  Old three arms and all core/installed source bytes unchanged. Same geometry rendered/solved.
- Seed: 3197 / 6000 DOFs, 417 x 203 x 201 mm, circular 36 mm throat, envelope fits.
  126 related CPU tests passed in 46.183 s; uniform-box sample 63/64 valid, one geometry refusal.
  New 32-attempt local search varies depth, H depth scale and crown; explicit flat penalties.
- Original night is live. Follow-up home_crowe_sections_2026-11-15 has search + top1 verify;
  detached controller 31224, WMI parent 35188, waits for original controller 42084.
  This records queue integration, not completed acoustic validation.
- Gallery now has four seeds, 20 renders and generated solid H/V section comparisons, with
  source links and inference labels. Code on the feature branch; static publication on main.


## 2026-11-15 - ROLLED RECTANGLE + H/V PUCKER PILOT, CPU VALIDATED / QUEUED

- Original shrinking-curvature contour, independent H/V axial development, round-to-rectangle
  wall transitions, optional separate H/V pucker; not a reproduction of Crowe ES or ATH Tritonia.
  Research/corrections: `docs/research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md`.
- Explicit experimental entry point `tools/geometry/rolled_rect_cli.py`; delegates to existing
  CMA, evaluator and mesh/BEM pipeline. Distinct row types, code digest and driver in saved
  recipes; stock CLI rejects them. No `hornlab_search/**/*.py` or existing config was changed.
- Three seeds: 4499 / 4465 / 4459 DOFs, 542 x 299 mm, depths 241 / 244 / 246 mm; all fit,
  circular 36 mm driver coupling. Each arm's uniform box preflight: 64/64 valid, no refusals.
  Focused regression: 72 passed. Broader offline result is recorded in the research dossier.
- Night `home_rolled_rect_2026-11-15`: three matched 32-budget searches, then top-1 verification
  per arm via its required adapter and batch-12/memwatch helper. Controller 42084, WMI parent,
  waits on active C controller 36944; no solve launched here. A completed queue setup is not
  completed acoustics. Plan: `docs/queue/ROLLED_RECT_PLAN_2026-11-15.md`.
- Existing night B ended with needs_initial_data (n_min=18, n=0); its studies did not complete.
  Preserved A/C workers and all prior dirty files. New code/configs committed on the existing
  feature branch; only the gallery/research publication is promoted to Pages on main.
- Seed gallery: `docs/renders/2026-11-15-rolled-rect/` (15 original renders, five angles, responsive
  synchronized comparison and accessible enlargement). Acoustic performance remains unmeasured.


## 2026-11-14 (23:09 local) - SEARCH-ECONOMY PREFLIGHT: THE "BEST AT n=0" GATE (skill + tool)

- Added the reusable gate behind the 22:5x night result: `.claude/skills/hornlab-search-economy/SKILL.md`
  (six pre-flight questions: seed-in-box, nested-incumbent headroom, sigma/budget power, refusal economy,
  graded inertness, A/B attribution) and `tools/search_preflight.py` +
  `tests/test_tools_search_preflight.py` (12 pass, offline). Numbers are derived from the config and the
  `--from-runs` history; there is no per-run threshold table.
- What it computes: seed-in-box HARD (`DesignSpace.normalize()` clips silently while eval 0 scores the
  unclipped seed); `no_headroom` including the nested case (same seed on every shared knob, only new keys
  added - the H1 9-knob config vs the 6-knob `51328c` prior); prior top-k spread -> recommended sigma and
  chi-square expected hits (`sigma_too_large`, `low_hits`); `--samples N` uniform box probe through the real
  validator (refusal fraction/kinds, labelled as an upper bound away from the seed because CMA concentrates
  near it); generated-family history fallback (`params.grid.knobs`, because `warmstart.mean_and_sigma` cannot
  read grid rows today); and `--ab` matched-pair / inactive-key / binding-key / added-region reporting. Exit 1
  on hard faults, `--strict` refuses warnings.
- Regressions pinned from this night: `sab__lecleach_fc540_T_narrow.yaml` seed `g_T=0.8` outside
  `[0.687, 0.777]` (HARD); H1 nested `no_headroom` (prior J 3.2325); L1 ctrl vs fc540 `sigma_too_large`
  (spread 0.017 vs sigma0 0.25), `low_hits` (0.02 expected), `ab_treatment_misses_binding_key`
  (`g_stop_deg` at lo 120.338, treatment moved `g_fc_hz`), and the added [540,600) region as INFO (the
  fc540 run did sample it: 48/125 evals below 600).
- Wired into the process: `hornlab-night-queue` launch step 4, `hornlab-shape-check` hand-off,
  `docs/INDEX.md`, `docs/CODE_MAP.md`, `AGENTS.md` OpenCode skill list, fixer grant in
  `.opencode/oh-my-opencode-slim.json`. `run_campaign_night.py --dry-run` deliberately unchanged for now
  (manual gate first). No solve/config change; no GPU time.

## 2026-11-15 (20:3x local) - BO GUI cloud handoff

- Added `docs/research/BO_GUI_CLOUD_HANDOFF_2026-11-16.md` (remaining scope: merge sab-home, BoTorch
  diagnostics artifact with LOO/slices/HV, Bayes nav + Live tab), plus the 11-16 handoff and the
  implementation plan. Docs only; merge gate unchanged (no merge while studies run).

## 2026-11-15 (02:0x local) - BO GUI SLICES 1-6 IN THE `feat/bo-gui` WORKTREE (NOT MERGED)

- Built the read-only BO analysis layer from the 15 Nov handoff: `gui/data_bo.py` (convergence,
  calibration, sensitivity, trust-region, Pareto, design-space, method-board view models),
  `gui/study_index.py` (bounded discovery and routing of night-arm study registries plus
  `runs/studies`), and `workflow_panel`/server wiring. The study page now renders the BO panels
  and deep links; `#/analysis/compare-methods` renders a declarative comparison spec.
  Slice 6 adds `gui/study_queue.py` (writes a new night file, never launches a runner) and
  `gui/study_child.py` (clone a parent spec with a child policy).
- Added `tools/analysis/specs/bo_method_board_2026-11-15.yaml` (BO-vs-CMA rules and arms) and
  `docs/research/BO_GUI_DESIGN_2026-11-15.md` (design + slice plan) with screenshots in
  `docs/evidence/bo_gui_2026-11-15/`.
- Backend instrumentation (pin-affecting, on the same branch): `bo/policy.py` now carries
  `model_hyperparameters`; `studies/builders.py` records them in the model manifest;
  `studies/evaluator.py` persists each proposal's `predicted`, `selection_reason`, `acquisition`
  and turbo `trust_region` on the candidate. Old runs stay honest (`partial`/`missing`).
- Tests (offline, no solver): `test_gui_bo_views.py`, `test_gui_bo_module.py`,
  `test_gui_study_index.py`, `test_gui_study_queue.py`, `test_study_gui_instrumentation.py`, plus the existing study/GUI
  suites and the updated adapter/contract assertions. `compileall` clean.
- **Merge gate (do not forget):** worktree `C:\Users\hunte\Hrns\bogui-wt`, branch `feat/bo-gui`,
  based on `feat/bo-turbo-pareto` (`e25da03`) + `feat/sab-home-2026-11-14`. Do not merge while
  `bo_vs_cma_2026-11-15` or `sab_home_gpu_rest_2026-11-15` is queued/running, and not while any
  study is queued or running (`runs/nights/queue_*.log`, `tools/night_status.py`).
  **Before merge:** the tree is committed and pushed as `origin/feat/bo-gui`
  (`ef6a38a` + merge `56a3eb8`); confirm no runner and no live
  Julia host; merge `feat/bo-turbo-pareto` first if the target does not already contain it, then
  merge `feat/bo-gui` (it already contains turbo + the 15 Nov docs); resolve `CONTINUITY`,
  `ISSUES`, `INDEX` and `CODE_MAP` in the merge commit; run `compileall` and the offline
  GUI/study suite. **After merge:** new packages must pass preflight; old packages keep their
  original pinned hashes; verify the `production_inputs_unavailable` line was only the
  worktree/canonical pin mismatch. Excluding `gui/**` from `EXECUTION_CODE_FILES` remains an
  owner decision.
- **Owner decision 2026-11-15:** keep the work on `origin/feat/bo-gui` only; do **not** open or
  merge a main PR until the nights finish. The branch is 21 commits ahead of `origin/main` because
  it contains the in-flight `feat/sab-home-2026-11-14` integration (turbo, v7 flat band, landscape
  configs), not GUI-only changes.
- Deferred (handoff-optional slice 7): partial-dependence curves and per-study dataset row
  identity. The lengthscale sensitivity bar is the first-pass sensitivity view.

## 2026-11-14 (22:5x local) - SUGGESTION A/B NIGHT, HI-FI SCORE PROBE, BO-VS-CMA PREP; NIGHT RE-ORDERED

- Night `sab_home_gpu_2026-11-14` (+ CPU `sab_lecleach_cpu_2026-11-14`) tests the 12 Nov report's suggestions
  (`docs/queue/SAB_HOME_PLAN_2026-11-14.md`, configs `examples/typologies/suggest_ab_2026-11-14/`). Finished:
  H1 ext-throat + ATH petal law s1234/s5678 -> best stays the nested no-law incumbent 3.23253 (petal NEGATIVE on
  that family); C1 core_law s2401 narrow 1.970 vs wide 2.128 (narrow box better, 71 vs 64 % valid; 24k cap cut
  mesh_too_large 106 -> 7); L1 lecleach fc540 / g_T-narrow WORSE on both seeds (0.839-0.896 vs ctrl 0.826; best
  designs now at fc ~640 Hz, stop 120 deg, g_T ~0.6 - the 12 Nov walls were seed-local). g_stop_deg > 240 is a hard
  generator refusal (not queued).
- Re-ordered at ~22:5x on owner request: the night is stopped right after H2 s1234 finished; the BO-vs-CMA night
  (`docs/queue/BO_VS_CMA_PLAN_2026-11-15.md`) runs next, then a remainder night with the unrun SAB jobs.
- New `tools/night_queue/verify_night_jobs.py` (verify top-N of jobs from a night's summary.jsonl; batch-12 heavy
  recipe + run_with_memwatch by default). New `tools/analysis/hifi_rescore.py` (offline CTA-2034-style DSP/passive
  re-score; 870 home designs: agrees with v7, Spearman 0.95-0.99) + `docs/research/ONAXIS_WEIGHTING_2026-11-14.md`.
- Strict-coverage brief twin `room_80x60_700_hf1440_v7_cov` + 80x60 H/V wall-angle cell (`bo_vs_cma_2026-11-15/`).
- Separate branches: `feat/study-budget-profiles` (comparison-60 study budget, study_cohort --run-id,
  tools/bo_compare) merged next; `feat/v7-flat-band` (opt-in `flat` from the XO) NOT merged yet.
## 2026-11-15 (09:3x local) - BOTORCH VS CMA REPORT: DEEPER OFFLINE ANALYSIS ADDED (docs only)

- Screen->verify drift: BoTorch median +3.4 % (rank 0.86) vs CMA +9.4 % (rank 0.76) over all verified designs.
- Model check: per-pick predictions were not logged, so they were replayed by refitting the locked model; ranking
  0.68-0.83, error near best 0.2-0.4 J, but the 95 % intervals are very wide (median ~4.6 J), so they are not informative.
  Follow-up: log each adaptive pick's prediction in the study journal.
- Hi-fi on verify data: seat-to-seat spread is a tie (0.37 vs 0.33 dB); the BoTorch winner has a smoother listening
  window (shape 0.92 vs 1.25 dB). Side-view renders of both horns were added to the report.

## 2026-11-15 (09:xx local) - BOTORCH VS CMA MATCHED TEST: BOTORCH WINS (report published, docs only)

- Home task HOME_SEED5678 (objective v7), same prior (run 18985d, 185 rows), 60 screens + 6 verify per arm, 3 seeds each.
  BoTorch best verify J 3.107 / 3.251 / 3.189 (median 3.189); CMA 3.827 / 3.827 / 3.392 (median 3.827). Gap 0.638 >
  both seed spreads (0.145 / 0.436), so BoTorch wins per the pre-declared rule. CMA never beat its start (3.2328) in 60 solves;
  its best design scores 3.233 at screen but 3.827 at verify (+18 %). CMA lost 14-29 solves to size refusals; BoTorch 0-3.
  BoTorch winners share a shorter, steeper throat extension (~110-127 mm at 4.3-4.8 deg vs 172 mm at 3.2 deg).
- Caveat (owner, 15 Nov): the CMA arms restarted from an already-converged CMA optimum, so this measures improving an
  optimized design, not cold-start search; a cold-start comparison is still to do.
- Report: `docs/status/2026-11-15-bo-vs-cma/` (README with PNGs, interactive index.html, data.json). The study code
  (budget profiles, TuRBO/Pareto) lives on unmerged branches; this commit is docs only.

## 2026-11-14 (15:3x local) - PROJECT ATLAS: REUSABLE WHOLE-PROJECT VISUAL REPORT (tools/atlas)

- New `tools/atlas/build_atlas.py` + `atlas_template.html`: read-only over every run folder (`run.json`,
  `search.ndjson`, inline `verify/`, Bayesian `study-*/screen`) -> one self-contained `index.html`
  (data embedded, vanilla JS/SVG/canvas, light+dark, phone width). ~3 s over 482 runs / 37.9k rows.
- Sections: scale + cumulative solves by family, run timeline, solves/day by objective version, solver
  seconds-per-candidate by pin and DOF-vs-seconds, refusal economy, optimiser convergence (normalised
  best/first J vs budget share; CMA-ES vs CMA-ME vs Bayes, per family), settle-time and gain distributions,
  decision map (search lines: solves vs late gain), per-brief leaderboards with verdict tags, beamwidth and
  size clouds of all solved designs, J per objective version, all screen/verify pairs, horn render gallery
  (`--gallery scratch/top2/cards`), auto-generated next steps with their printed rules.
- Snapshot published at `docs/atlas/index.html` -> https://llevaachingada.github.io/Hornfab/atlas/ .
  This snapshot: 26,914 solves (26,247 distinct), 5,253 refused (16%), 132.4 compute h, 482 runs,
  233 search lines, 227 screen/verify pairs. Verdicts are heuristics for a human decision, never applied.
- Regenerate after any checkpoint: `.venv\Scripts\python.exe tools/atlas/build_atlas.py --out docs/atlas
  --gallery scratch/top2/cards`. Tests: `tests/test_tools_atlas.py` (4 pass). No solve/config change.

## 2026-11-14 (15:2x local) - GITHUB PAGES ENABLED (owner-approved; docs only)

- Owner approved enabling GitHub Pages on llevaachingada/Hornfab: source `main` `/docs`, legacy build.
  Site root https://llevaachingada.github.io/Hornfab/ ; the status brief page is
  https://llevaachingada.github.io/Hornfab/status/2026-11-14/ (its `index.html`).
- Added `docs/.nojekyll` so Pages serves files verbatim (no Jekyll/Liquid pass over the docs tree).
  The repo was already public, so nothing new is exposed. No code/config change.

## 2026-11-14 (15:1x local) - COLLABORATOR STATUS BRIEF PUBLISHED (docs only)

- Added `docs/status/2026-11-14/`: `README.md` (GitHub-rendered brief with 19 static chart PNGs in `img/`) and
  `index.html` (the same page, self-contained with embedded data, live SVG charts). Content: the 12 Nov day report
  (`runs/analysis/day_2026-11-12`), the 12-14 Nov changes on main through `878d381`, CMA-ES internals of
  `20261112T144510Z-screen-00cf9c` (fit/sigma/stddev/xmean/covariance from its `cma/` logs), CMA-ME archive
  heatmaps, objective balance, walls, sensitivity, fidelity, best-design beamwidth/DI, pull steps, open issues.
- Numbers are a snapshot read from existing run/analysis files; no solve, queue, config or code change.


## 2026-11-14 - BAYESIAN INTEGRATION FINAL VALIDATION / COMMIT FOLLOW-UP

- Concurrent owner-authorized `5e86c8b` included the staged scalar study implementation and
  pushed it with the config decisions below; this follow-up preserves that history.
- Completed real pilot: 18 screens + 6 verification/audit calls, 24 exact canonical replays,
  zero unresolved attempts; four finalists and two audits verified with no shortfall.
- Final study-focused suite 116/0/0 and ownership/polling guard set 25/0/0. Broad release:
  3840 passed / 19 skipped / 3 failed; corrected polling and dataset timing passed targeted reruns.
  The unmodified pre-mesh refusal timing assertion still failed at 104.4 ms vs 100 ms under
  the owner's active CPU/GPU jobs. Full suite is not claimed green; no thresholds weakened.
- Details and byte-checked output: `docs/evidence/BAYESIAN_STUDY_INTEGRATION_2026-11-14.md`.
  The timing issue is recorded for a quiet-host rerun; unrelated running lanes were preserved.

## 2026-11-14 (05:4xZ) - OWNER DECISIONS EXECUTED: COHORT GAP CLOSING, CAPS 12k -> 24k, BATCH-12 FOR HEAVY RUNS

- **Cohort gap (approved):** the print80x60 day night budgeted job 1 at 250 evals but the interrupted+resumed
  run closed at 200 â€” the â‰¥250-row BO training cohort was 50 short. Night `cohort_extend50_2026-11-14`
  (`kind: command`, `search --resume runs/20261113T193536Z-screen-81c964 --budget 50 --mode screen`) launched
  07:35:05Z; rows 1-200 replay free, the 50 new evals solve at `38e5b1f` (parity ~1e-5 dB justifies mixed
  pins; every row carries its own `lib_shas`). Rows 1-200 read the cap-12,000 config at process start; the
  cap edits below landed AFTER, so the cohort extension stays cap-12,000-consistent by construction (a
  mid-run restart would re-read the edited config â€” accepted, monitored).
- **Caps raised 12,000 -> 24,000 (approved, measured basis):** edited the four LIVE config files only â€” the
  three `examples/typologies/print_80x60_2026-11-13/*.yaml` (screen/verify/final) and
  `examples/profiles/fused_cuda.yaml` (verify/final), 11 lines total. Basis: the measured envelope gives
  24,000 -> ~4.7 GiB need = `fit`; the 24,973-DOF anchor itself measured-fit at 5.8 GiB device peak, zero
  spill. Historical study/ablation configs (~40 files) deliberately left at 12,000 â€” their provenance stays
  under the policy they were run under. Tests re-based by fix (`test_config_extends.py` now pins 24,000)
  and the feasibility guard extended to hold BOTH 12,000 and 24,000 in the `fit` band. Offline pytest green
  (27 tests). Caps are UPPER BOUNDS: existing designs below the cap are unaffected; heavier mesh refinement
  is now allowed where the mesher wants it.
- **Batch 12 for heavy runs (approved recipe):** screen-tier searches stay unbatched (pre-declared bar);
  verify/final-style heavy runs set `HORNLAB_FREQ_BATCH_SIZE="12"` via the night job env (archived night
  YAML = provenance) or `solve.freq_batch_size: 12` in a config that only serves heavy runs. RUNBOOK row
  updated. Honest caveat recorded: the 13-15 % whole-candidate win was measured at screen scale (18 freqs,
  6-8k DOF); heavy-tier expectations are extrapolated â€” measure the first heavy run with
  `run_with_memwatch.py` + watch `run.json.stats`.

## 2026-11-14 - SCALAR BAYESIAN STUDIES INTEGRATED AND LIVE-PILOT VERIFIED

- Implemented the scalar v4/v7 production worker/CLI and Studies GUI actions; kept CMA defaults.
  Optional isolated Bayesian interpreter now includes the project's pinned HornLab stack.
- Fixed historical training loss on refit/resume, screen-vs-verification proposal cadence,
  task-specific projection and canonical derived-throat geometry; added v7 canonical replay and
  read-only homogeneous cohort intake. Proposed and evaluated geometry now share production links.
- Immutable packages retain complete candidate pools, measured dependency pins and executable-source
  hashes. Each solve attempt reserves its own budget; studies disable hidden backend retries.
  Unknown attempts remain conservative; duplicate workers cannot replace the active owner's files.
- Measured live pilot `72834b64942a29f1...`: 18 screen + 6 verify/audit calls, two cheap refusals,
  all 24 results exact-replayed with max absolute score delta zero; six selected designs verified,
  no shortfall or unresolved reservation. Best screen J 3.105495448486849, not a CMA benefit claim.
- Broad offline validation before final ownership/source-pin hardening: 3833 passed / 19 optional
  engine skips; combined-engine integration 128 passed / no skips; final guards 39 passed.
  Final release results are retained under `scratch/2026-11-14_bayes/release.{log,xml}`.
- Runbook: `docs/BAYESIAN_STUDIES_RUNBOOK.md`; byte-checked terminal pilot evidence:
  `docs/evidence/BAYESIAN_STUDY_INTEGRATION_2026-11-14.md`. Production Pareto and matched CMA
  adoption comparisons remain future work. Existing briefs, queues and unrelated edits preserved.

## 2026-11-14 (07:1x local) - CPU-LANE RE-REQUEST: NO RELAUNCH, LIVE NIGHT RE-VERIFIED

- Owner asked again (hornlab-night-queue skill) to add the CPU-lane search beside
  `home80x60_day_2026-11-13` (backend beat_cpu, lane cpu, own HORNLAB_BEAT_WORKER_DIR / cache_cpu /
  dataset_cpu / `runs\.cpu.lane.lock`, brief `room_80x60_700_hf1440_v7.yaml`, a typology cell the GPU
  is not running, cutoff 23:30). **Every element is already live in `home80x60_cpu2_2026-11-14`
  (launched 05:55); per skill rule 3 a second CPU-lane runner would pre-hygiene-kill the live lane's
  host, so nothing was launched.**
- Fresh live evidence: runner pids 25596 (controller 4816) + 28820 (search child, `runs\.cpu.lane.lock`
  holder, "night home80x60_cpu2_2026-11-14") alive; queue log `runs\nights\queue_2026-11-14_cpu.log`
  shows "cutoff 23:30". Run `runs/20261114T105532Z-screen-4f9fd4`: **8 evals done** (n=0..7), newest
  row n=7 created 12:11Z, rows carry `"lane":"cpu","backend":"beat_cpu"`; best-so-far J 6.413 (n=1) vs
  later 11.48/66.42 rows. `runs\.gpu.lock` absent (GPU night drained 02:25; two-lane rule still
  honored). Brief file untouched (it is the config's `brief_file`); GPU lane hosts never touched.

## 2026-11-14 (06:4x local) - GUI / DATA-VIZ UX PASS (front-end only)

- Analysis report rebuilt decision-first (next-solve actions with follow-through links, run
  scoreboard grouped by objective version, objective balance vs tolerance, search-box ranges,
  sensitivity, square screen-vs-verify scatter). Fixed the reversed "screening overstates J"
  headline and the refusal strip that summed past 100 %.
- Run detail: key numbers + Next step first, view tabs, Export STEP as the one primary action,
  setup / Continue-run collapsed below the charts. Isobars keep the Boundary Lab frame with
  rainbow 3 dB bands + hairline contours; over-range flagged only > +1 dB; new Globe view.
- One "New run" nav item (Guided | Quick launch); Launch warns instead of silently picking the
  first brief for a non-file brief. Tables/tiles wrap long ids; brief-band panel 0.30 -> 0.10.
- Shared kit in charts.js / app.css (validated categorical palette, sparkline, stacked bar,
  globePlot, seg-toggle, control-border). Details: docs/GUI_UX_PASS_2026-11-14.md.
- Tests: new tests/test_gui_report_v2.py; four source pins updated; GUI suite green. No server,
  data, solver or scoring change.

## 2026-11-14 (05:5x local) - CPU-LANE NIGHT home80x60_cpu2_2026-11-14 LAUNCHED (hornlab-night-queue skill)

- Added one `lane: cpu` night beside the `home80x60_day_2026-11-13` GPU queue:
  `runs/nights/home80x60_cpu2_2026-11-14.yaml`, job `cpu_p80x60__ath_core_14in_s7890`
  (kind command): `hornlab-search search --config examples/typologies/print_80x60_2026-11-13/p80x60__ath_core_14in_700_v7.yaml
  --mode screen --budget 300 --cma-seed 7890 --backend beat_cpu --cache-dir cache_cpu --dataset-dir dataset_cpu`.
- Cell choice: ath_core_14in's first other-seed replicate â€” the GPU night(s) ran it ONLY at seed 1234
  (osse_ext_throat replicates are covered: GPU 1234/5678, CPU 9012 earlier night), so no design overlap.
  Brief is the config's brief_file `room_80x60_700_hf1440_v7.yaml` (untouched, not edited).
- Lane isolation verified live: own `HORNLAB_BEAT_WORKER_DIR` `runs\lanes\cpu\workers` (job log line),
  stale `runs\.cpu.lane.lock` holder (pid 15196, night home80x60_cpu_2026-11-13, gone) taken over by
  the search child (pid 28820, "night home80x60_cpu2_2026-11-14"); pre/post hygiene is
  `gpu-clean --lane cpu` only (log: rc=0, "no project Julia/BEAT processes found"); the GPU lane's
  hosts and `runs\.gpu.lock` (free all morning) were never touched by this launch.
- Timing: ~103 s/eval measured (rev2_cpu_parity2) â†’ budget 300 â‰ˆ 8.6 h, expected finish ~14:45;
  job timeout 57,600 s caps it ~22:00 worst case; queue launched detached via launch_detached.ps1 +
  queue.ps1 `-Nights home80x60_cpu2_2026-11-14 -Cutoff 23:30 -Log runs\nights\queue_2026-11-14_cpu.log`
  (controller pid 4816, parent WmiPrvSE.exe, log "starting home80x60_cpu2_2026-11-14"; cutoff 23:30).
  `--dry-run` clean before launch (path validation passed).
- Launch-time GPU state (read-only): `.gpu.lock` absent, no julia.exe pre-existing (one new host
  spawned by the CPU search as expected). Note: at 05:5x the GPU queue had ALREADY drained overnight
  (print80x60_jobs23_2026-11-14 finished 02:25, all 8 speed-round nights 1-eval batches done); the
  CPU night still honors "beside the GPU night" per the two-lane rule (one CUDA solve + one CPU search).
- AMENDMENT 06:4x local (owner asked again to add this lane; it is already live, so it was NOT
  duplicated - a second CPU-lane runner would pre-hygiene-kill the live lane's host, rule 3).
  Health check from the run's own artifacts (`runs/20261114T105532Z-screen-4f9fd4`): 2 evals done,
  newest `search.ndjson` row n=1 best J 6.413; runner pid 28820 alive, lane lock holder fresh,
  `nvidia-smi` shows no CUDA process (1168 MiB / 33% is desktop-only baseline). MEASURED RATE IS
  ~10.4-10.7 min/eval, NOT 103 s/eval: eval 0 mesh 05:55:38 -> done 06:06:03, eval 1 mesh 06:06:09
  -> done 06:16:48. So budget 300 is unreachable - the 57,600 s timeout caps it near 21:55 with
  ~110-120 evals; `-Cutoff 23:30` only prevents later nights from starting. No relaunch made: the
  timeout path is the documented outcome and the rows persist (`resume:` re-runs the rest).

## 2026-11-13 (21:0x local) - PARAMETER DOC SPLIT: `--check` IS NOW A REAL CI GATE

- Resolved the last blocking contradiction from the CI integration. `docs/reference/PARAMETERS.md` is
  produced by `tools/gen_param_catalog.py`, but it carried a hand-maintained "Search-config keys"
  section the generator never emits â€” so `--check` failed on a clean tree and `--write` deleted 158
  lines of hand-written contract text. Both facts made the gate unusable.
- Fix: the hand-written block now lives in `docs/reference/SEARCH_CONFIG_KEYS.md` (with a header saying
  it is deliberately not generated and must be folded into the generator later), and the generated
  PARAMETERS.md emits a one-line pointer to it from `catalog.render_parameters_markdown`. Regenerated
  with `--write`; **`--check` now passes**: "param catalog OK: all three artifacts match a fresh build".
- `.github/workflows/docs.yml` gates `tools/gen_param_catalog.py --check` again, plus the catalog/config
  tests. `docs/INDEX.md` lists the new file.
- Verified: `--check` exit 0; `tests/test_param_catalog.py tests/test_config.py` 70 passed.
- `--check` resolves `code_ref` symbols, and 29 of the 33 point into
  `hornlab_mesher.{freeform,profile_formulas,profile_morph,throat_stretch}` â€” so the docs job installs
  the pinned mesher (full install: importing any submodule executes `hornlab_mesher/__init__.py`, which
  needs gmsh+meshio). The MAIN test job must not install it: that would flip 199 `requires_mesher` tests
  from skip to run. The docs job's path filter also covers `hornlab_search/design/**`, `examples/**`,
  the generator and the workflow itself, so a code-only PR that stales the reference is caught too.
- **Both CI gates are now green on main:** `CI` 4m21s (was 8m18s serial; the 23 pre-existing failures
  were fixed by the CI-repair lane in PR #57) and `Docs check` 27s including the `--check` step.
- No content lost: the 155-line search-key body moved verbatim and is diff-visible in this commit.
  Verified mechanically: the moved block is **byte-identical** (150 lines, normalised line endings) to
  the block removed from PARAMETERS.md.
- **Found and fixed while doing it: `.gitignore`'s `reference/` rule was unanchored**, so it matched
  `docs/reference/` as well as the root CAD dir. Every new file in `docs/reference/` was silently
  ignored â€” which is why the new doc needed no force-add after anchoring it to `/reference/`. This
  would have quietly swallowed any future generated reference doc.

## 2026-11-14 (03:2xZ) - SPEED PROGRAM COMPLETE THROUGH E9: FIRST FULLY-PROVENANCED PRODUCTION NIGHT AT 38e5b1f

- **E9 verified:** night `print80x60_jobs23_2026-11-14` finished 2026-11-14T02:25:18Z, runner exit 0,
  **400/400 evals** (ath b200: mean 45.22 s/cand, 79.6 candidates/h; osse seed5678 b200: mean 52.33 s/cand,
  68.8 candidates/h; both run dirs carry `lib_shas.hornlab_beat_bem = 38e5b1f8â€¦`). Zero GPU failures class
  unchanged; peaks 2.0-2.3 GiB. NOTE: the two runs re-solved from cold A1 caches at the new pin (expected
  one-time invalidation) and use different designs than the A/B arms â€” the mean-s/cand above are production
  rates, not a clean A/B (the clean A/B is in the adoption evidence).
- **Spill watchdog over the production tail:** `tools/bench/run_with_memwatch.py --attach` (snapshot
  mode, 120 s cadence): dedicated peak 586 MiB, **shared peak 80 MiB, no spill** â€” final record at
  `scratch/speed_runs/memwatch_e9.json`.
- **Hardening landed while the night ran (`7fa7d5e`â†’`dc8dc03`):** memwatch `--write-every-seconds`
  incremental snapshots (a lost window can no longer lose evidence); CI guard pinning production caps
  (12,000 DOF) inside the A5 `fit` band; throughput runbook rows refreshed (batch config key, adoption,
  spill watchdog).
- **Speed program E0-E9 COMPLETE.** Rollback path unchanged; the adoption evidence
  (`docs/evidence/SPEED_ADOPTION_2026-11-14.md`) is the single record of the measured campaign.

## 2026-11-14 (01:xx local) - CI REPAIR HARDENING PASS: RIBS IN CI (+38 REAL TESTS), FIXTURE DRIFT GUARD

- Senior verification of the 2026-11-13 CI repair (#56) and the #55 merge:
  - `manifest._check_task` adversarial probes on the committed pilot-1 manifest: every tamper (locator to another file,
    absolute path to another filename/truncated/None, empty or dropped locator, `../` escape, sha edit, brief=config) is
    refused; only a different host prefix with the same repo-relative locator is accepted (the intended portability).
  - #55 merge (643f05d): every CONTINUITY heading from both sides kept, none added; no conflict markers in docs. The 34
    duplicate headings in CONTINUITY pre-date this work (present at 55fbf7f).
  - Main CI confirmed: 3455 passed / 309 skipped; scikit-learn 1.9.1 installed and parameter_study runs.
- Gap found: on CI the QD failure-isolation safety suite was effectively all skipped (ribs absent; pre-existing
  `importorskip` + the new `requires_ribs`). Fix: CI installs the pinned `[qd]` extra `ribs==0.12.0`. CI-shaped venv: all 6
  ribs test files 85 passed / 0 skipped (38 previously skipped), ~36 s.
- Gap found: committed `tests/fixtures/experiments/s11/` overlays could silently drift from the scratch originals. New
  `test_s11_fixtures_match_scratch_originals`: byte-identical where originals exist, skips otherwise; verified pass on
  real originals, FAIL on a drifted copy, skip with no scratch.

## 2026-11-14 (~02:0xZ) - SPEED PROGRAM ADOPTED: SOLVER 38e5b1f (-25/-28% WALL, PARITY ~1e-5 dB, ZERO SPILL); BATCHING NOT ADOPTED; A5 RE-BASED ON MEASURED ANCHORS

- **Full campaign executed overnight per `docs/queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md`:** E0 âœ“
  (200/200, runner exit 0, 1 recorded transient documented) â†’ E1b âœ“ (raw Julia suite **3830/0/4** +
  analytic OK archived under `docs/evidence/*_38e5b1f_2026-11-13.log`; first attempt lost to the
  julia.exe Windows-wrapper redirect bug, re-run under `cmd /c` with exit stamps) â†’ E4 âœ“ (installed
  `38e5b1f` from the GitHub fork, `direct_url.json` exact, C1+C2 markers verified, CPU reprovisioned)
  â†’ E3/E5 âœ“ (10 arms) â†’ mandated repeats + b4 fallback âœ“ â†’ E6 ceilings âœ“ â†’ E7 decision â†’ **E8 merge (this commit)**.
- **H1 ADOPTED:** whole-candidate wall `new_b1/base_b1` = **0.7533 (osse, 54.47â†’41.03 s)** / **0.7201 (ath,
  83.77â†’60.32 s)** â€” outside the ambiguity band; `solve_hash` identical across all arms; `hornlab-search
  compare` max diffs â‰¤ 4.4e-05 dB / 3.6e-05Â° (bar 0.039 dB / 1Â°; compare is report-only, bars computed).
  The measured fused-CUDA ceiling is now **24,973 quarter-DOF fits** (5.8 GiB device peak; 23,850 fits at
  4.7 GiB, shared 80 MiB everywhere). Full tables: `docs/evidence/SPEED_ADOPTION_2026-11-14.md`.
- **H2 NOT ADOPTED (pre-declared rule held):** batch-12 ratios hit the ambiguity band (0.8483/0.8667) â†’
  repeated both pairs on fresh roots â†’ median ratios **0.8512 / 0.8653 > 0.85** â†’ rejected; batch-4
  fallback **0.8771 / 0.9131** â†’ rejected. N1's 1.9-4.7x solver-only win is only 13-15% whole-candidate.
  `solve.freq_batch_size` lands as a default-`None` provenance key (C3, committed `66d8509`);
  `HORNLAB_FREQ_BATCH_SIZE` stays the owner's trial knob.
- **A5 re-based on measured anchors (rule-sanctioned fix):** `solve/feasibility.py` replaces the pin-A
  `4.0 Ã— 8NÂ²` model with `FUSED_CUDA_MEASURED_ANCHORS` (piecewise envelope): the 12,000-cap fits at 1.77 GiB,
  the old 20,237 refusal is now a fit (3.35 GiB), the measured 24,973 anchor is `risky`, â‰¥ ~26k `refuse`.
  `tests/test_solve_feasibility.py` re-based by fix (the stale test G2 called "provably stale"). Offline
  pytest green (feasibility 7 + freq_batch_config 8 + config_extends 11 + memwatch 5), `compileall` clean.
- **Evidence-tool gotchas recorded:** `run_with_memwatch.py` (C4) attached over the whole Round B window:
  dedicated peak 4,074 MiB, **shared peak 80 MiB (no WDDM spill)** â€” the number nvidia-smi cannot see.
  julia.exe's Windows wrapper does not carry `Start-Process` redirections (first E1b attempt lost; archived
  0 bytes, re-run archived complete).
- **E9 RUNNING:** production relaunched fresh 2026-11-13T20:59:15Z with the print night's un-run jobs
  (`runs/nights/print80x60_jobs23_2026-11-14.yaml`: ath_core b200 + osse seed5678 b200; first run dir
  `runs/20261114T015916Z-screen-db8e2f`) under the adopted solver. Rollback unchanged (Â§9 of the prompt;
  old pin `0850ef39`).

## 2026-11-13 (20:4x local) - CI REPAIR: 7 RED CLUSTERS FIXED ON MAIN (NO TOLERANCE OR EXPECTED VALUE CHANGED)

- Main CI (55fbf7f) was red on 8 clusters, none a product regression. Fixed in `fix/ci-repair-2026-11-13`:
  1. `test_tools_experiments_manifest` (24 setup errors + 4): fixtures read gitignored `scratch/bo_m0/s11/*.yaml` -> committed
     copies under `tests/fixtures/experiments/s11/`; `manifest._check_task` re-verifies by the stored repo-relative
     `config_rel`/`brief_rel` locator (absolute path = provenance, must end in the locator, separator-agnostic); committed-manifest
     test stays zero-warning where warm-start `runs/` exist and tolerates only `warm_source_unavailable` for runs absent on the host.
  2. `bo_sensitivity`: cohort-config name read with `PureWindowsPath` (POSIX `Path` kept the whole `C:\...` string).
  3. ribs-gated QD archive tests: new `requires_ribs` marker in conftest (4 tests incl. protocol-refusal, which also needs ribs).
  4. geometry_descriptors: split; `resolve failed` under `requires_mesher`, new no-mesher test pins `canonical resolver is unavailable`.
  5. hypothesis_cards roundtrip: `requires_mesher` (build path needs the resolver).
  6. parameter_study: scikit-learn installed in CI and declared as `[analysis]` extra (no test edits).
  7. `test_failure_marker_replays_without_counting`: pinned physics SHAs so the namespaced marker path runs on every host.
  8. `test_config` freq_batch_size: already fixed on main by 50b6f06 (dropped from this change).
- Evidence bytes untouched (sha256 before = after): pilot1 `8c28c569...`, pilot2 `c7b1e243...`, native_trainingset `f24f2768...`.
- Verified: touched files 199 pass / 5 skip (owner venv); CI-shaped venv (no ribs/mesher) rc=0; owner-host shape (runs/+scratch
  linked) manifest 33/33 no skips; full suite result in PR body.
## 2026-11-13 (20:2x local) - S8/S7 ANALYSIS PANELS LAND: GEOMETRY, HYPOTHESIS, QD/PARETO, SURROGATE (GUI only; no solve)

- **`gui/data.py`:** `geometry_descriptors`, `hypothesis_cards`, `qd_compare` and
  `surrogate_validation` are now registered analysis tools; the report exposes `tool_files`
  (JSON/Markdown/PNG names per tool) and discovers keyed `surrogate_validation-<16 hex>.json`
  outputs, selecting the newest complete payload and disclosing every candidate
  (`surrogate_validation_candidates`: name/status/reason/input_key/complete/readable/mtime).
  Keyed stems are no longer misreported as `extra_tools`; a malformed keyed file is disclosed as
  `readable: false`, never raised.
- **`gui/static/app.js`:** four read-only panels in `#/analysis` after the M1 cards
  (`an-geometry-panel`, `an-hypothesis-panel`, `an-qd-panel`, `an-surrogate-panel`), with two
  inline-SVG scatters (`geometry-navigation`, `qd-front`) and the technical appendix carrying the
  stored scalars. Wording is contractual: geometry/hypothesis show no score or rank; QD states
  "attempt-equivalent ... not elapsed time" and "not a win claim", and never plots excluded rows;
  the surrogate panel prints `no prediction (outside training support)` for OOD proposals and the
  advisory-only disclaimer. Flat sections now link their `tool_files` (root route), which also
  makes the M1/other registered tools' Markdown discoverable.
- **Decisions:** keyed surrogate discovery is GUI-side (no tool change); the tools' `runs/` output
  guard is unchanged, so the workflow remains `hornlab-search gui --analysis-dir <set>`; no
  separate tab, no new dependency, no new colour, no `fetch`, no `tools/` import.
- **Verification (terminal):** `node --check hornlab_search/gui/static/app.js` -> exit 0;
  `python -m compileall -q hornlab_search/gui` -> exit 0;
  `pytest tests/test_gui_views_analysis_s8.py tests/test_gui_views_analysis.py tests/test_gui_views_analysis_m1.py tests/test_gui_chart_standards.py -q`
  -> **34 passed, exit 0**; `pytest tests/test_gui_*.py -m "not slow and not gpu and not crosscheck" -q`
  -> **432 passed, exit 0** (`scratch/2026-11-13_s8/gui-s8-final.xml`). The new node guard executes
  the real builders and page composition over literal tool payloads.
- **Docs:** `docs/HANDOFF_S8_S7_GUI_2026-11-13.md` Â§15 records the implementation and residual
  limits; `docs/CODE_MAP.md` and `docs/INDEX.md` updated. No dataset/cache/queue/installed file
  was written and no analysis ran from the GUI.

## 2026-11-13 (20:3x local) - CI SPEED IS LIVE; C3 CONTRACT BREAK FIXED (ONE LINE)

- [measured] CI test step: **385.3 s before -> 201.9 s after** (`-n 2 --dist loadscope`, one trigger,
  pip cache); job wall 8m18s -> 4m15s. Same selection, same skips (3,386 passed / 296 skipped).
- **C3 regression fixed:** 66d8509 added `SolveSettings.freq_batch_size` with
  `None = absent = today's grouping`, but `tests/test_config.py::OPTIONAL_FIELDS` did not declare it,
  so `test_examples_load_with_no_none_in_required_fields` failed for all 5 examples (+5 CI failures,
  first caught by the new docs job in 31 s). Declared `solve.freq_batch_size` optional â€” the
  mechanism the file already documents for every other opt-in key; no assertion changed.
- CI failure count on main is still **23 pre-existing** (unchanged ids; see ISSUES). This commit
  removes the +5 that C3 introduced; the remaining 23 are the other lane's lane.

## 2026-11-13 (20:2x local) - SPEED PROGRAM: SENIOR REVIEW LANDED (ADOPT WITH CORRECTIONS); E0 DONE; C3+C4 LANDED; E1b RUNNING; ROUND A ARMED

- Four independent verification lanes (repo/run provenance, `hornlab_search` code, fork/Julia dataflow, evidence provenance)
  reviewed `docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md`: verdict **ADOPT with corrections** â€” full dataflow proves the
  C2 guard complete and fused-CUDA output untouched (the fused assembler forms its identity on device,
  `BeatEngineCudaBurtonMiller.jl:20-29`); batch composition is output-irrelevant on the fused route; the 0.039 dB / 1Â° parity
  bar is the CP-7f noise floor codified in `docs/FORKS.md:49-51`. Corrections + all 12 open-question decisions recorded in a
  new plan Â§14.
- Four claims invalidated and fixed: (1) the "â‰¤ 5 % replicate spread" is not in G2 (its 4,168-DOF row shows ~11 % wall /
  ~18 % VRAM spread) â€” repeat rule hardened: both arms on fresh cache roots, median-of-3 decides, a gray median REJECTS;
  (2) A5 is implemented as `FUSED_CUDA_FACTOR 4.0 Ã— 8NÂ²` (`solve/feasibility.py:17-37`), not "8NÂ² + constant";
  (3) "repo rule 7 requires the measured 20,152" was a mis-cite (throughput-program rule,
  `docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md:67`); (4) the 3830/0/4 Julia-suite result was prose-only attestation â€”
  no raw log existed (rule 6). `hornlab-search compare` confirmed **report-only**: bars must be computed from its output.
- **E0 DONE** (gate deviation recorded): resume night finished 2026-11-13T19:22:24Z, runner exit 0, **200/200 rows**
  (170 ok; 30 recorded failures: 26 invalid_geometry + 3 mesh_too_large + **1 transient `solve_failed`** â€” 10054 worker reset
  at n=187; the recovery re-warmed the host but the design was not re-attempted and the row stays an honest failure per
  `error_policy: legacy`; not re-run: disproportionate GPU rework for a recorded infra transient).
- **C5 answered, closed (zero GPU):** after fetching `jamescollinharky:hornlab-search/osse-midports`,
  `merge-base --is-ancestor d740c28 55da4f46` â†’ exit **1**: the pin **predates** the upstream FREEFORM density/cost fix. Pin
  stays for the beta (owner policy `docs/ISSUES.md:1167`); a bump would invalidate every mesh hash â€” own post-beta program.
- **C3 implemented (env-only knob â†’ provenanced config key):** `SolveSettings.freq_batch_size: int | None = None`
  validated (`None` or int â‰¥ 1), wired into `_prepare` â€” passed **only when explicitly set**, so the
  `HORNLAB_FREQ_BATCH_SIZE` env fallback still governs absent keys (probe-verified: env 12 â†’ backend 12, config 6 â†’ 6,
  absent â†’ env). Landed AFTER the hard-rule-3 contract-gap note in `NOTES_FOR_SENIOR.md` (append-only). Edge closed: refused
  for `bempp_cpu` (would otherwise TypeError in `BemppBackend`). Offline tests: `tests/test_solve_freq_batch_config.py` (8) +
  `tests/test_config_extends.py` (11) pass; `compileall` clean; `config_sha` unchanged for configs without the key.
- **C4 implemented:** `tools/bench/run_with_memwatch.py` â€” observer-only shared/dedicated-VRAM watcher
  (`spawn` + `attach` modes), reusing `_bench_common.GpuMemPeak`/`SPILL_MIB=512` and worker-host discovery; JSON records
  `dedicated_peak_mib`/`shared_peak_mib`/`spill_mib`/`spilled`; live attach smoke against the running gpu lane recorded
  dedicated 2972 / shared 80 / no spill; `tests/test_run_with_memwatch.py` (5) pass offline. **Tooling gotcha recorded:**
  julia.exe's Windows wrapper does not carry `Start-Process` redirections (first E1b attempt archived 0 bytes) â€” E1b now runs
  under a `cmd /c ... > log` wrapper with exit codes stamped inline.
- **E1b RUNNING** (`julia -t auto --project=hornlab_beat_bem/julia .../tests/runtests.jl` + `validate_analytic_exterior.jl`,
  raw logs to `docs/evidence/*_38e5b1f_2026-11-13.log`; expected 3830 / 0 / 4 and `ANALYTIC_EXTERIOR_VALIDATION_OK`).
  **Round A is armed behind E1b** (queue `-WaitPid` chain): `runs/nights/speed_round_a_2026-11-14.yaml`, 2 arms, batch 1,
  `--budget 1`, per-arm cold caches. Pin still `0850ef39`; GPU idle at this writing.
- Execution authority for the remaining gated steps (E4 swap, Round B, ceilings, decision, merge): 
  `docs/queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md` (hand to the integrator verbatim; where it differs from plan Â§6,
  the prompt wins).
## 2026-11-13 (20:0x local) - CI INTEGRATED: ONE TRIGGER, PIP CACHE, `-n 2`, DOCS FAST LANE

- `.github/workflows/ci.yml`: triggers reduced to `pull_request` + `push: branches:[main]` (the old
  `on: push` fired a second identical run per branch push); `cache: pip`; docs paths ignored; the test
  step is now `-n 2 --dist loadscope` with the same single-thread BLAS/OpenMP env as the local lane.
- New `.github/workflows/docs.yml`: docs-only changes run the cheap guards instead of the full suite
  (`tests/test_param_catalog.py tests/test_config.py`).
- **Finding (pre-existing): `tools/gen_param_catalog.py --check` FAILS on main.** `PARAMETERS.md`
  carries a hand-maintained "Search-config keys" section the generator does not emit, so `--check`
  says STALE and `--write` **deletes 158 lines** of hand-written contract text (verified, then
  reverted). The docs job therefore does NOT gate `--check`; the reason is written in the workflow and
  in ISSUES. Fold the search/brief keys into the generator before adding that step.
- Still owner-action: branch protection / required checks on `main` (GitHub setting, not code).
- Not in scope here: CI is red on main for 23 pre-existing failures + 24 errors (listed in ISSUES);
  none of them come from the test-suite work â€” the same set fails on the four commits before it.

## 2026-11-13 (19:3x local) - TEST SUITE 3.1x FASTER (xdist), GPU LANE ON FUSED CUDA, GPU LOCK NOW ADVISORY

- Branch `test/testspeed-2026-11-13` (worktree `oc-wt/testspeed`, owner-requested isolation), merged to
  main this session. Plan/evidence: `docs/research/TEST_SUITE_OPTIMIZATION_2026-11-13.md`.
- **[measured] Serial baseline:** 3,739 cases, 975.8 s test time, **1,092 s wall (18.2 min)**, 0 failed,
  18 skipped, 21 deselected (`-m "not slow and not gpu and not crosscheck"`, full local venv).
  Cost concentration: 41 tests >= 5 s carry **57.0 %**; 2,913 tests < 50 ms carry 2 %.
- **[measured] `-n 6 --dist loadscope` + single-thread BLAS: 353.0 s wall (5.9 min) = 3.1x**, 3,766 cases.
  The BLAS/OpenMP caps are REQUIRED: without them six workers each spawn a pool and the suite inflates
  1.39x -> 1.83x (gmsh/OCCT tests 46 s -> 90 s). **`-n 8` is worse** (2,933 s test time; poles 56 s ->
  186 s); 6 is the measured sweet spot, `auto` is not allowed on this box.
- Parallel-safety fixes: `test_design_generators_grid_full_ring.py` (x2) and `test_s1a_driver_briefs.py`
  wrote fixed `runs/c2_probe*` / `runs/s1a_probe`; now `tmp_path`. `pytest-xdist>=3` added to `[dev]`.
- **GPU lane on the shipping path:** `test_solve_beat.py` builds `BeatBackend("cuda", cuda_fused=True)`,
  routes every spec through `_spec()` (`spec_with(..., cuda_fused=True)` -> `SolveSpec.extra`), and
  `test_11` asserts `meta["cuda_fused"] is True`. Rationale: fused wins at every size (1.42x at ~4k) and
  fused-off FAILS at ~8k (`THROUGHPUT_N1_2026-11-12`); 154 configs set `cuda_fused: true`, 0 set false.
  `test_solve_beat_fused_cuda.py` stays the one deliberate A/B; `test_solve_traces::test_19` stays
  unfused (the trace contract was never validated against the fused assembler).
- **`slow` retired:** removed from the 6 files that used it (16 of its 21 tests already carried
  `gpu`/`crosscheck`; the other 5 were real BEM solves). `test_end_to_end.py` is now `gpu`. No nightly
  tier; heavy CPU tests run in the parallel lane.
- **GPU lock policy (owner directive):** default is now `warn` - a live holder prints the holder and the
  command proceeds unlocked. `HORNLAB_GPU_LOCK=refuse` restores the old fatal behaviour (nights,
  measurements, checkpoints); `off` silences. `gpu-clean` keeps its own refusal unless `--force`.
  `_cmd_selftest` KEEPS its lock on purpose: its verified `worker.shutdown` would otherwise kill a live
  job's host (the 2026-10-25 bug). Lock files are still written when free - they are the ownership
  signal `worker.live_locked_lanes` uses.
- **Pre-existing, NOT caused here:** `tests/test_tools_experiments_manifest.py` fails 4 + 24 collection
  errors (FileNotFoundError on local data) under a *serial* run in this checkout, and the xdist run
  reproduces exactly that and nothing else. Reported in ISSUES.
- Verification: 42 lock/CLI/selftest tests pass (3 refusal cases now pass `policy="refuse"` explicitly;
  4 new policy tests); 51 mesher tests (full-ring + s1a) pass with no stray `runs/` dirs; `compileall`
  clean; `test_end_to_end.py` confirmed deselected from the CPU lane.
## 2026-11-13 (23:5xZ) - HANDOFF WRITTEN: GUI ARCHITECTURE FOR THE S8/S7 ANALYSIS TOOLS (docs only; no product change)

- `docs/HANDOFF_S8_S7_GUI_2026-11-13.md` records the finished S8/S7 lane (`dc64fd7`) and plans the
  GUI work an implementer needs: exact artifact contracts for `geometry_descriptors`,
  `hypothesis_cards`, `qd_compare` and `surrogate_validation`, the current `#/analysis` plumbing with
  file:line references, the gap list, per-panel data bindings, the surrogate keyed-filename problem,
  test/acceptance commands, ownership and open decisions.
- Finding recorded: the four tools are **not** registered in `ANALYSIS_TOOL_JSONS`
  (`gui/data.py:4044`) or `ANALYSIS_SECTION_TOOLS` (`app.js:2644`), so their JSON is never parsed and
  they render only as `extra_tools` name pills. The S8/S7 tools also refuse `--out` under `runs/`,
  while the GUI default root is `runs/analysis/`; the documented workflow is `--analysis-dir`.
- No code, test, default, dataset, cache, queue or installed file changed by this entry; no solve.

## 2026-11-13 (23:4xZ) - PART TWO COMMITTED (fork `38e5b1f`) AND RE-VERIFIED BY THE INTEGRATOR; PLAN READY FOR REVIEW

- Fork commit `38e5b1f` on `perf/skip-fused-identity-cache` (on top of `9ec86b0`): the two dense **host** L2 identity
  assemblies are moved after the fusion decision and skipped only on `fused_burton_miller_cuda`; `identity_cache` is
  left empty there (its only reader is the CPU quadrature-order lookup); every other backend is byte-identical.
  Pushed to `ourfork`; installed-SHA target for the trial is therefore **`38e5b1f`**.
- **Independent verification (not just the implementer's report):** I read the guard at source - flag assigned at
  `:1574`, guarded assembly at `:1586-1589`, and the only consumer that would break (the CUDA cache build at `:1681`)
  is already inside `if !fused_burton_miller_cuda` (`:1680`); `identity_cache` is read only inside
  `beat_backend == :cpu` (`:1827`). I then re-ran the Julia CPU suite myself: **exit 0**, counts unchanged
  (3830 pass / 0 fail / 4 broken; the CUDA testsets skip because CUDA is not a dependency of the CPU project).
  `validate_analytic_exterior.jl` -> `ANALYTIC_EXTERIOR_VALIDATION_OK`.
- The senior plan (`docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md`) was updated to record C2 as DONE at `38e5b1f`,
  with the verified dataflow and the residual risk (an empty `identity_cache` fails loudly if a future reader appears).
  **The plan is frozen for the owner's reviewer**; nothing in E3-E9 has been executed.
- Resume job still running: **181/200** rows at this writing; pin still `0850ef39`; no other GPU work.

## 2026-11-13 (23:3xZ) - SENIOR IMPLEMENTATION PLAN WRITTEN FOR REVIEW; SIX VERIFICATION CORRECTIONS (ONE TEST-DESIGN FLAW)

- Wrote `docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md` for a higher-thinking agent to review **before** execution:
  verified ground truth, architecture/dataflow, change inventory C1-C6, invariants I1-I8, E0-E9 sequence with gates,
  hypotheses H1-H4 with arms/statistics/falsification, measurement infrastructure, risks R1-R10, rollback, and 12 open
  questions. The program doc is now explicitly the operational one-pager; this is the implementation reference.
- **Test-design flaw found and fixed:** the Round A/B arms shared one cache, so the second arm on the same seed design
  would have been a **cache hit** and its wall time would have collapsed - faking the effect being measured. Every arm
  now has its own `cache_dir` + `dataset_dir` under `scratch/` (C6); both night files re-dry-run clean.
- **Five more corrections from the verification pass:** (1) `--budget` on a resume counts **new** evaluations, so the
  interrupted run needs **45**, not 200 (validated: 153 -> 155 with a 2-eval probe); (2) that run is
  `infeasible_penalty: graded` / `error_policy: legacy`, so the strict library-SHA resume guard is inert - the ordering
  rule stays as a general rule, not because it bites here; (3) night files must be copied into `runs/nights/` before
  queuing (queue.ps1 looks only there); (4) `kind: search` requires a `config:` key even with `resume:`, so the resume
  job is `kind: command`; (5) the analytic selftest never sets `cuda_fused`, so it is not fused-path parity evidence.
- **Running state:** resume job `resume_print_night_2026-11-14` live, run at **159/200**; part-two patch edited in the
  fork (+16/-3) and under CPU test; pin still `0850ef39`; GPU busy with the resume only.
- **Ceiling calibration (CPU-only):** mouth-res 5.03 / 4.46 / 4.09 = **15,878 / 20,152 / 23,850** quarter DOF.
- Nothing beyond the already-approved Step 1/2 has been executed; Rounds A/B, the swap and the ceiling sweep wait for
  the plan's review and for the resume to finish.

## 2026-11-13 (23:3xZ) - ORACLE-REVIEWED SPEED PROGRAM REPLACES THE CAMPAIGN DESIGN (ordering fixed; part two folded in)

- The Oracle review of the campaign found three design faults, all now fixed in
  `docs/queue/SPEED_PROGRAM_2026-11-13.md` (the campaign doc is marked SUPERSEDED; its night files are deleted):
  1. **Ordering.** The interrupted night must be finished **before** the solver swap: `search/cma.py:702` refuses a
     strict resume after any library-SHA change, so swapping first would strand the 153 candidates already paid for.
     Program order is now: finish -> write part two -> baseline -> swap -> measure -> merge.
  2. **Wasted arms.** Old-solver batch-12 arms prove batching on a solver that is about to be replaced; dropped. The
     new-solver arms (batch 1 vs 12 on both designs) carry the batching effect, the upgrade effect and the interaction.
  3. **Part two should not be a third measured level.** The host-side identity-matrix guard is folded into the **same**
     new fork SHA; if attribution is ever needed, bisect the two fork commits instead of spending 4 arms and 2 swaps.
- **Merge decisions recorded:** upgrade = merge fully (becomes the pin) if it passes the bars; part two = folded in;
  batching = merge **behind a config key** (`freq_batch_size`), default 12 in CUDA examples, env var as fallback;
  mesher = **out of scope** unless the pinned SHA provably predates upstream's FREEFORM density/cost fix **and** a live
  typology is FREEFORM.
- **Bars unchanged from the campaign** (0.85 wall ratio, 0.039 dB / 1 deg parity, peak VRAM lower, shared spill
  < 512 MiB) and every arm still records frequency count and DOF.
- **Mesher check is three commands, zero GPU** (`git fetch` the pin from `jamescollinharky`, then
  `merge-base --is-ancestor d740c28 55da4f46`). Note the remotes differ: the local checkout's `origin` is upstream
  `m3gnus`, the pin lives on the fork.
- Ceiling points calibrated CPU-only: mouth-res 5.03 / 4.46 / 4.09 = **15,878 / 20,152 / 23,850** quarter DOF.
- Night files: `docs/queue/speed_round_a_2026-11-14.yaml` (2 arms) and `..._round_b_2026-11-14.yaml` (4 arms), both
  `--dry-run` exit 0. Nothing launched; the pin is still `0850ef39`.

## 2026-11-13 (23:3xZ) - COMBINED SPEED CAMPAIGN DESIGNED (PIN x BATCHING FACTORIAL); THREE RECON LANES REPORTED

- **Why combined:** the owner wants to adopt more than G2 at once. A3 (skip the fused identity cache) and frequency
  batching (G1) both amortise *per-request* setup, and A3's per-request cache build is part of what batching would
  amortise - so sequential adoption double-counts the overlap. A factorial measures the interaction.
- **Design:** `docs/queue/SPEED_COMBINED_2026-11-13.md`; night files
  `docs/queue/speed_combo_2026-11-14_{oldpin,newpin}.yaml` (both `--dry-run` exit 0). Two blocks of four arms:
  `{batch 1, batch 12} x {p80x60__osse_ext_throat_700_v7, p80x60__ath_core_14in_700_v7}`, `--budget 1` so every arm
  solves the same seed geometry. Block 1 on pin `0850ef39` (current), block 2 after the swap to `9ec86b0`.
  Pre-declared rules: adopt a factor only at wall ratio <= 0.85, compare <= 0.039 dB / 1 deg, lower peak VRAM, zero
  shared spill. Budget ~45-55 GPU-minutes including the ceiling sweep.
- **Lane summary (three parallel recon lanes):** (1) every speed idea already documented, with status/measured
  gain/GPU cost/resolution flag; (2) the mesh state - C1 audit is the only landed mesh work, production defaults are
  untouched (`rear_res_factor 1.0`, `curvature_npts 0`), the mesher fork checkout is stale (at `b922e80`, the pinned
  `55da4f4` object is absent locally); (3) the per-frequency lifecycle - **the batching knob is not used in
  production** (`cma._prepare` never passes it; one request per frequency, so caches + `GC.gc(true)` + `cuda.reclaim()`
  recur per frequency), and the fused route also builds two dense **host** N x N identity matrices per request that it
  never reads (Lane C candidate B, a second A3-shaped patch).
- **Excluded by the owner's rule** (recorded so they are not re-proposed as speedups): rear-shell density (coarsens a
  coupled surface), quadrature order reduction, coarse epw, fewer angles/frequencies, FP32 Krylov, reduced-order sweeps,
  UI fidelity selector.
- **Docs:** INDEX row added for the campaign doc. No code, pin, GPU or queue change in this commit; the campaign is
  designed, not launched.
## 2026-11-13 (~23:5xZ) - PR #55 RECONCILED WITH MAIN (S7 TAKEN FROM MAIN); WORKTREES CONSOLIDATED 28 -> 3

- Main went green before the merge: `46a28ec` adapted the builder fixtures to the strict native gate and
  `dc64fd7` finished the S8 contracts + S7 advisory hardening (including the unit-cube OOD test). Verified on a
  clean `origin/main` worktree (`a717650`): `test_study_builders`, the S7 file and the S8 trio -> 90 passed.
- PR #55 merged `origin/main` (`a717650`) as `4d6f4da`. Conflicts were the four expected add/adds: took **main's**
  `tools/analysis/surrogate_validation.py` and `tests/test_tools_analysis_surrogate_validation.py` (its 8 tests
  contain the branch's original 4 plus 4 v4 `--advisory-stored-j` tests), merged `docs/CONTINUITY.md` /
  `docs/ISSUES.md` keeping both sides, and kept the PR's `schema.md` S7 section (now describing both modes).
- Kept from the PR: B4/B5 durable launches (`launches` table, migration 2), B8 CLI/HTTP end-to-end +
  `GET /api/studies/<id>/export`, S5 `--config-roundtrip` + local-search hints, `lane_parity --pair`,
  `docs/INDEX.md` dedupe. The branch's own S7 draft is gone; the S7 v4 question is answered by main's
  stored-label mode, and S8 is closed.
- Verified on the merged branch: `compileall` exit 0; **151 passed** (durable launch, B8 e2e, seed_pack,
  lane_parity, S7, S8 descriptors/cards/qd_compare), **116 passed** for the b8/study/gui/builder/native-gate
  neighbours, and the analysis-tool suite green (26 files, 1 skip: local S4 inputs absent).
- Worktree consolidation (owner request; nothing lost): 25 worktrees removed from the registry, each verified
  clean and merged into main; every branch ref kept (no `branch -d/-D`). Kept `hf-wt/pr55` (the PR),
  `oc-wt/gui-int` (`feat/gui-integration`, unique) and `oc-wt/bo-study` (885 MB `bayes-venv`, not a worktree).
  `oc-wt/L1`'s one scratch file was copied to `%TEMP%\opencode\L1.git-commit-msg-l3.txt` before removal.
- Safety net: tags `backup/main-pre-reconcile` (`87c0944`) and `backup/pr55-pre-reconcile` (`da09812`); a 64.6 MB
  all-refs bundle verified complete (`%TEMP%\opencode\hornlab-all-20261113.bundle`) - **copy it off-machine**.
  The four local-only unique branches are now on origin: `feat/gui-integration`, `dev/fused-cuda-pin`,
  `backup/consolidation/T`, `backup/consolidation/L1`.
- Next: merge PR #55 on GitHub (merge-commit style), then `git worktree remove hf-wt/pr55` and
  `git branch -d pr55-local`; `feat/gui-integration` still needs a deliberate merge-or-retire call.

## 2026-11-13 (~25Z) - PR #55 MERGED UP TO MAIN, VERIFIED OFFLINE; S7 v4 GATE KEPT (offline)

- Merged `main` (`9019cbd`) into `claude/eloquent-ride-owt01w`: two conflicts, both docs, both sides kept
  newest-first (`CONTINUITY`, `ISSUES`). No code conflicts. Merge done in an isolated worktree because the
  canonical checkout had unrelated uncommitted work.
- Verified (worktree code, `PYTHONPATH` pinned to it): `compileall hornlab_search tools/analysis` exit 0;
  72 passed for the new tests (durable launch, B8 CLI/HTTP end-to-end, lane_parity pooled, seed_pack
  round-trip, surrogate_validation); 62 passed for the neighbouring b8/study/gui-study tests; `docs/INDEX.md`
  dedupe checked by link-target set (166 -> 165 targets; the only dropped row is the pre-archive
  `HANDOFF_COLLABORATOR_2026-10-23.md`, whose `archive/` copy is listed).
- DECIDED (was the open senior question): S7 keeps `surrogate/capability.py` at v1-only. v4 needs
  tolerances/terms plus measured throat impedance the surrogate cannot supply, and `tools/analysis/schema.md`
  makes J comparable only within one objective version + brief/weights/tolerances â€” the S7 row contract carries
  no brief/score identity. A v4 path needs `objective/replay.py`'s `score_id` in the row contract and
  same-identity enforcement as a separate change, not a widened constant.
  **Superseded the same day by main's `a4dccef`** (`--advisory-stored-j`, canonical `score_spec` per row): see
  the ~23:5xZ entry. This branch took main's implementation at reconciliation (`4d6f4da`); the draft is gone.
- Still open: S8 (geometry/behaviour descriptors, hypothesis cards, QD-vs-Pareto) not started; full offline
  suite not re-run in this environment (targeted tests above only).

## 2026-11-13 (~24:30Z) - S7 SURROGATE VALIDATION, S5 CONFIG ROUND-TRIP, LANE_PARITY POOLED (offline)

- S7: `tools/analysis/surrogate_validation.py` (numpy kNN, advisory only): chronological split with leakage
  checks (no future rows, same-geometry rows removed from test), train-only preprocessing, OOD fallback,
  feasibility Brier/reliability, 95% interval coverage, top-k recall/regret, resume-safe keyed output,
  exploit/uncertainty/diversity proposals labelled hypotheses. Respects `surrogate/capability.py`: v2+ refused
  (so the v4 native cohort is refused today; widening capability is a separate decision). 4 tests.
- S5: `seed_pack.py --config-roundtrip CONFIG --dataset-root DIR` rebuilds native designs and compares hashes
  (needs_config when config/rows/mesher absent; generated configs not reconstructable); `local_search` advisory
  sigma0/box hints + cold control arm. 4 new tests.
- lane_parity: repeatable `--pair GPU,CPU` pooled CP-7b (hash counted once across pairs). 3 new tests.
- NOT DONE: S8 (geometry/behaviour descriptors, hypothesis cards, QD-vs-Pareto). Full suite not re-run after these.

## 2026-11-13 (~24Z) - B4/B5 DURABLE LAUNCH IDEMPOTENCY + B8 CLI/HTTP END-TO-END + INDEX DEDUPE (offline)

- B4/B5: `StudyRunBridge` launch dedup moved from the in-memory `_launched` dict into the studies SQLite
  registry (`launches` table, store migration 2). Claim is written before the launcher runs; same key replays,
  other key 409 `launch_conflict`, ambiguous launch or crash mid-launch = 503 `unknown` (never relaunched).
  Absent key returns `missing_idempotency_key` (400) on launch/cancel/CPU submit. Tests: `tests/test_study_launch_durable.py` (7).
- B8: `tests/test_b8_end_to_end_cli_http.py` (2) drives create -> snapshot -> explain -> propose -> package ->
  dry-run -> fake run -> decide -> export via `hornlab-search study` and via a real in-process HTTP server
  (restart replays the launch). New read-only route `GET /api/studies/<id>/export`.
- docs/INDEX.md: duplicated second half merged; 6 unique rows kept, 1 stale pre-archive row dropped (archived copy listed).
- Pre-existing failures on main in the cloud env (not touched): experiments_manifest (Windows paths), bo_sensitivity_real (3), design_generated (1).
- Next (same branch): lane_parity pooled mode, S5 config round-trip, S7 surrogate_validation, S8 descriptors/cards.

## 2026-11-13 (23:1xZ) - G2 INDEPENDENTLY REVIEWED: ADOPT-WITH-CONDITIONS; EVIDENCE DOC CORRECTED (MECHANISM + PARITY GAP)

- Owner asked for an independent review before deciding the pin bump. Oracle verdict: **adopt-with-conditions**
  (confidence ~0.85 memory/safety, ~0.7 wall). Adopt command and rollback are in the evidence doc; the pin is still
  `0850ef39` pending the owner's call.
- **Correction 1 (my error, retracted in the doc):** the skipped device payload is **two** matrices, `identity_p1_p1`
  (NÃ—N) **and** `identity_p1_dp0` (**NÃ—E**, E = triangles, `assemble_l2_identity_matrix` allocates
  `zeros(T, test_dof, trial_dof)`), i.e. `8Â·(NÂ² + NÂ·E)`. That matches the measured savings to within 2-4.5 %
  (390/1,453/3,227 MiB nominal vs 384/1,388/3,150 measured). The earlier "2.7-2.8x, CUDA pool segment rounding"
  explanation was wrong and is retracted; no pool effect is needed.
- **Correction 2 (gap):** `selftest.py::_spec` never sets `cuda_fused`, so the identical analytic numbers prove the
  **non-fused** path is unchanged, not the fused one. Fused-path output parity is a code argument, not a measurement;
  `docs/FORKS.md` step 6.3 compare was not run. Also the harness records dedicated VRAM only, so the plan's zero-spill
  requirement is one field short.
- **Confirmed by the review:** the only cache reader is `pressure_for_drives`, reached solely from the non-fused
  `else`; the default CUDA path is byte-identical between pins; symmetry, near-correction, MEH and warm-host routes
  cannot reach it; and `coupled_solver.jl:909-910` builds the same cache but is unreachable from the worker
  (`solver.jl` includes only `BeatEngineCore.jl`/`BeatEngineDriver.jl`), so it is dormant, not an open cost.
- **Required follow-ups, value per GPU-minute:** (1) ceiling re-measurement on pin B at ~15.9k/20.2k/24k DOF with
  dedicated **and shared** recorded - the 12,000 caps and the 20k refusal were set by pin-A memory and are plausibly
  stale by 1.5-2x; (2) fused-path output compare (FORKS 6.3); (3) one production-shape screen solve per pin;
  (4) pool live-vs-reserved instrumentation; (5) non-fused and 2-channel MEH control points.
- **A5 guidance corrected:** model pin B as `8Â·NÂ² + ~0.2-0.3 GiB`, not a multiplier (`delta/8NÂ²` drifts 2.41 â†’ 1.43 â†’
  1.24). The `20,237 -> refuse` feasibility test is stale under pin-B arithmetic but must be re-based on the measured
  20k point (rule 7), not on arithmetic.
- No pin change, no code change, no GPU work in this commit.

## 2026-11-13 (23:0xZ) - G2 MEASURED AND PASSED: A3 CUTS FUSED VRAM 55-70% AT IDENTICAL PHYSICS; GPU NIGHT PAUSED FOR IT

- **Owner request:** pause the running GPU work and run the G2 gate.
- **Paused first:** queue controller 39096 (it was waiting on the night runner and would have started the rerun the
  moment the night exited), then the GPU night `home80x60_day_2026-11-13`: runner 20608/6848, search 33268/36636
  (job 2 `p80x60__ath_core_14in`, run `20261113T193536Z-screen-81c964`) stopped at **153/200 candidates**, worker
  host 15868/40856, julia 8028. Job 3 (`p80x60__osse_ext_throat_s5678`) never started. VRAM back to 660-891 MiB.
  Resume: `search --resume runs/20261113T193536Z-screen-81c964 --budget 200`; job 3 separately. The GPU rerun
  night is still on disk but is **not** queued.
- **G2 protocol:** `measure_fused_ceiling.py` (M2: one solve per fresh process, out-of-process VRAM poll,
  `gpu-clean` between measurements), fused on, at quarter DOF **4,168 / 8,021 / 11,938** (mouth-res 10.0 / 7.1 /
  5.8, calibrated CPU-only), 3 reps per point per commit.
- **Result [measured]:** A `0850ef39` median delta **703 / 2,091 / 4,493 MiB** at **2.93 / 5.90 / 9.72 s** per
  frequency; B `9ec86b0` **319 / 703 / 1,343 MiB** at **2.15 / 4.17 / 7.82 s**. Savings **-55 % / -66 % / -70 %**
  VRAM and -27 % / -29 % / -20 % per-frequency wall. No OOM at any point on either commit.
- **Parity [measured]:** `selftest --analytic` identical on both commits - R(ka) spread 0.020 dB (tol 0.5),
  convergence 0.0204 / 0.0051 / 0.0013, spreading 6.0206 dB per ka, omnidirectionality <= 0.0050 dB.
- **Verdict:** the G2 adopt criterion is met. Evidence: `docs/evidence/G2_FORK_AB_2026-11-13.md`.
- **A5 consequence:** the 4.0x fused factor (calibrated at 12,183 DOF ~4.7 GB on the old pin) is now ~3x too
  pessimistic - 12k DOF measures 1,343 MiB. Recalibrate it with the pin bump, before A5.4 is wired.
- **Not done:** the pin is **not** bumped yet. That is one commit (pyproject + TOOLCHAIN pin table + the A5 factor)
  after owner go-ahead; rollback is the old SHA. The venv was restored to `0850ef39` and the CPU runtime
  re-provisioned, so the checkout is repo-consistent and the GPU is idle.
- **Two artefacts, not regressions** (both explained in the evidence doc): a `pip --force-reinstall` drops the
  per-backend CPU readiness marker, which made `sub5` read `n/a` until `provision --backend cpu` ran; and one B rep
  exited 1 on a Julia-host teardown race after emitting a complete result.

## 2026-11-13 (23:0xZ) - S8 DISCOVERY CONTRACTS AND S7 ADVISORY VALIDATION FINISHED (offline; no solve, no default change)

- **Scope:** four offline analysis tools plus their tests, already on `main` (`5f15275`, `a4dccef`);
  this pass finished the S7 advisory hardening and closed the S8 documentation/validation checkpoint.
  No optimizer, default, dataset, cache, queue or installed library was changed. MEH stays paused.
- **`tools/analysis/geometry_descriptors.py`:** strict `Design`-only input with a recursive,
  case-insensitive score/task-key assertion (now also `score_identity`, `score_spec`,
  `scoring_context_id`, `scalar_score`, `objective_j`, each proven by a test). Admitted native families
  are `ICW`, `OSSE`, `R-OSSE`, `FREEFORM`; MEH, `mid_ports`, CAD STEP and GRID recipes are refused
  before resolution. Uses the installed canonical point-grid resolver (no gmsh/BEM), records resolver
  SHA provenance, reports absolute length/mouth W-H, projected throat/mouth areas, oriented aspect,
  area ratio and normalized dimensions. `behavior_descriptors(MetricSet, band_hz)` is a separate
  band-aware view; standardised PCA and seeded multi-init k-means are labelled navigation-only.
- **`tools/analysis/hypothesis_cards.py`:** verifies two distinct actual parent IDs against the source
  JSON and `Design.hash()`, reconstructs every config, resolves candidate geometry canonically, and
  requires all six roles (parents, combination, both ablations, broad control). Acoustic/mesh
  feasibility stays explicitly unverified; MEH is refused.
- **`tools/analysis/qd_compare.py`:** requires one objective version, `scoring_context_id` and
  physical task/spec, two oriented physical axes with units and a frozen HV reference from the input
  manifest, and every attempted result with a checked `Design.hash()` and strict `ok`. Reuses
  `search.outcomes.classify` and nsga nondominance so failures/duplicates are charged but excluded.
  Budgets are integer **attempt-equivalent** evaluations (training/other costs included), i.e.
  accounting equality, not measured wall-time or hardware parity. `search/cma_me.py` untouched.
- **`tools/analysis/surrogate_validation.py` (S7):** the default legacy capability gate is unchanged
  and `surrogate/capability.py` untouched. `--advisory-stored-j` accepts only stored complete v4
  labels sharing one canonical `score_spec`/`score_identity` plus declared completeness evidence;
  the per-result replay `score_id` is provenance only (it embeds metric/physical identity and
  normally differs by design). Hardening: strict row contract (finite metrics/timestamps, unique IDs,
  unit-cube `x`), refusal instead of a crash on an empty chronological split, average-rank Spearman,
  code-versioned resume keys, regression support from successful training rows only, null predictions
  for OOD proposal rows, and a live-root output guard. It validates supplied evidence; it does not
  reconstruct raw arrays and does not add v4 scoring capability.
- **pr55-local:** read only. The S7 tool and tests were brought into canonical `main` earlier and
  extended here; no merge and no other PR55 files were taken.
- **Verification (this pass, terminal):**
  `python -m pytest tests/test_tools_analysis_*.py -m "not slow and not gpu and not crosscheck" -q`
  -> **308 passed, exit 0** (`scratch/2026-11-13_s8/focused-s8.xml`); the preceding S8-scope broad run
  (all analysis tests + `test_search_cma_me.py`, `test_search_qd_failure_isolation.py`,
  `test_search_nsga.py`) -> **329 passed, exit 0**
  (`scratch/2026-11-13_s8/regression-final.xml`); `python -m compileall -q tools/analysis` -> exit 0.
- **Limits:** offline machinery establishes contracts and reproducibility only. It does not establish
  acoustic improvement, family validity or optimizer superiority, and the attempt-equivalent budget is
  not a timing result.

## 2026-11-13 (22:4xZ) - BO-STUDY v1.1 LOCAL PASS: STRICT NATIVE GATE, S10 STUDY QA FIXES, S11 REBUILT, HOME/S5 READINESS (offline; no solve)

- **Strict native gate (M2 bypass audit):** `hornlab_search/bo/data.py::build_native_training_set` now enforces
  the brief objective version, response-detrended ripple evidence, target/weights presence, and one shared
  backend/brief/dependency/task/target/weights/metric-source policy across accepted rows. A disagreement is
  `incompatible_cohort`, a missing value `capability_missing`; no partial pooling. Fidelity/grid/solve-hash
  mixing is published (`ok_mixed_fidelity_declared`) and refused only with `require_single_fidelity=True`.
  The `morph_exponent` no-op is applied only when the space has that knob, so the six-knob home v7 task uses
  the identity projection instead of raising `UnsupportedSpaceError`. Tests: `test_bo_native_policy_gate.py` (9).
- **M2 gate evidence:** `m2/GATE.md` + `m2/gate/*` (fresh catalog rebuild, target probe, diagnostics, sensitivity
  rerun). Verdict `insufficient_evidence`: the interfaces pass, but the frozen native cohort is one connected
  independent group, not the five group-held-out validation requires. No BO benefit or speed-up claim.
- **Home readiness:** `home/READINESS.md`. 217 catalog-ok rows (250 total, 33 failed) >= n_min 16, but the replay
  artifact has 0 score rows (the offline scan is ATH-target-only; replay dispatches v1-4 only; home is v7) and
  all 217 ok rows lack `impedance_matrix` (loading weight 1.0). `freeze_snapshot` ok; `build_training`
  `Unavailable` (`n_min=16 n=0`). Input SHA-256s are recorded.
- **S5:** `s5/STATUS.md`. Both seed packs are empty because `seed_pack._hex40` rejects the real 12-hex design
  hash (30,723/30,723 catalog rows). The cloud PR owns the parser; regenerate the packs after it merges.
- **S11:** both pilot manifests rebuilt from the committed `s11/overlays/` (new `task.pins` /
  `task.blocked_evidence`) and re-validated against the live CLI: `errors=0 warnings=0`, exit 0. The committed
  manifests are overwritten by design; the validation JSONs are unchanged. No pin/blocker validation error.
- **GUI S10 QA fixes:** bounded artifact previews (`bounded_preview`), recorded decisions on Decide
  (`decision_panel_artifact`), Execute falls back to the prepared package when no results exist, and
  `studies.js` requires a real string id (`#/run/undefined` fixed). `tests/test_gui_studies_qa_fixes.py` (5);
  the stale Execute `missing` assertion in `test_b8_adversarial_workflow.py` now asserts the explicit package
  fallback. S10 screenshots carry a README warning that their "idle" lanes came from a temp runs root.
- **Stale A1 tests fixed:** `test_design_generated.py` and `test_mesh_build_grid.py` read failure markers from
  the physics-namespaced solve cache (`ctx.solve_cache_root/failures`), not the retired flat
  `cache/solve/failures`; the `test_study_builders.py` tiny fixture now carries the strict policy fields. All
  were red on the first full suite after A1/the strict gate and pass in the final run.
- **Verification:** full offline suite `python -m pytest -q -p no:cacheprovider tests -m "not slow and not gpu and not crosscheck"`
  -> **3721 passed, 18 skipped (optional bayes venv), exit 0**; isolated bayes-venv
  `test_bo_{model,acquisition,propose,pareto}.py` **44 passed, exit 0**. `compileall` on the changed modules,
  `node --check studies.js`, and `tests/test_tools_experiments_manifest.py` (33 passed) clean. No solve, GPU,
  queue, cache, `gpu-clean` or live dataset write; the home80x60 GPU night was untouched.
- **Docs ownership:** `docs/INDEX.md` is owned by the concurrent cloud PR, so this commit does not edit it;
  the new evidence docs are referenced here and by their parent evidence files.
- **Push rule:** this commit carries this entry, the ISSUES rows, and the evidence it describes.

## 2026-11-13 (22:3xZ) - BACKLOG COMMITTED AND PUSHED (owner request): BO STRICT GATE, GUI STUDY QA, S5/S10/S11 EVIDENCE, FOUR ANALYSIS TOOLS

- Owner request: commit and push the checkout's uncommitted work. Two commits, both pushed: `5f15275`
  (73 files: strict native training gate, GUI study-panel QA fixes, bo-study S5/S10/S11 + M2 gate evidence,
  `tools/analysis/{geometry_descriptors,hypothesis_cards,qd_compare,surrogate_validation}.py` + 4 new tests,
  `tools/lane_speed_report.py`, INDEX/CODE_MAP rows, AGENTS routing paragraph) and `a4dccef`
  (`surrogate_validation.py` refinements, committed only after its SHA was stable for 45 s).
- The C1 artifacts previously pushed on `solver-speed-orch2` (16 rear-density configs + the audit doc) also
  land on `main` with `5f15275`, so main is self-contained; the branch keeps only the C1 write-up.
- Verification before pushing: `compileall hornlab_search tools tests` exit 0; the six new test files +
  `test_b8_adversarial_workflow.py` -> **63 passed in 13.52s**; `test_tools_analysis_surrogate_validation.py`
  -> **21 passed**.
- Deliberately left uncommitted: `tools/analysis/geometry_descriptors.py` and
  `tests/test_tools_analysis_surrogate_validation.py` were being written live (mtimes 17:33:08 / 17:33:32,
  seconds before this entry). They are the other session's in-flight work, not a backlog.
- Process note: this checkout has had two agents writing at once, and the second session left its bo/gui/
  analysis work uncommitted for hours. Orchestrator 2 does not fold another session's half-written files into
  its own commits, which is why the sweep was a separate, explicitly attributed commit.

## 2026-11-13 (22:2xZ) - CPU-LANE JOBS RE-QUEUED ON THE GPU LANE (FUSED CUDA), BEHIND `home80x60_day_2026-11-13`

- **Owner request:** move the stopped CPU jobs to the GPU queue, and make sure the queue runs **fused CUDA** on the
  current repo/plan.
- **New night** `runs/nights/home80x60_gpu_rerun_2026-11-13.yaml` (night files are gitignored): 2 command jobs, same
  designs/seeds/budgets as the stopped CPU night - `p80x60__osse_ext_throat_700_v7` seed 9012 budget 120
  (timeout 3 h) and `p80x60__ath_core_14in_700_v7` seed 5678 budget 80 (timeout 2 h), both `--backend beat_cuda`,
  with no cache/dataset overrides (the GPU lane writes the shared `cache/` + `dataset/`; the 5 CPU candidates stay
  in `dataset_cpu`).
- **Fused path verified, not assumed:** `load_config(..., cma_seed=..., backend="beat_cuda")` on both configs resolves
  `solve.backend=beat_cuda`, `solve.cuda_fused=True`, caps (12000, 12000, 12000), objective v7, 73 angles, balloon on.
  `--backend beat_cuda` is the same backend, so `cuda_fused` is NOT dropped by the override path
  (`config.py::load_config` pops it only when the effective backend is not `beat_cuda`). Solver pin unchanged at
  `0850ef39`; the A3 fork patch is deliberately not installed until G2.
- **Queue launched detached** (WMI) as pid 39096: `queue.ps1 -Nights home80x60_gpu_rerun_2026-11-13 -Cutoff 23:59
  -WaitPid 20608 -WaitMatch home80x60_day_2026-11-13`, log `runs\nights\queue_gpu_rerun_2026-11-13.log`. It waits for
  the running GPU night's runner (verified alive and matching) so the two nights never overlap; the new night starts
  when that night exits (expected ~21:00-22:30 local) and no later than 23:59.
- `run_campaign_night --dry-run` on the new night: **exit 0**, both argv blocks resolve and every path exists.
- **Repo state at queue time:** local `main` `5b8e352` (`origin/main` `9019cbd`); the working tree also carries the
  other session's uncommitted bo/gui work, which is off the solve path. The queued night runs the Wave A merge
  `7277795` (A1 namespaced caches, A2 seam fix, A4, A5), so its searches populate the new
  `cache/solve/p2-<sha12>/` namespace instead of reusing legacy flat entries.
- **Not done here:** no pin change, no reordering of the running night, no GPU work now (the current night still owns
  the GPU until it exits), no code change.

## 2026-11-13 (22:1xZ) - CPU LANE NIGHT STOPPED AT OWNER REQUEST (TOO SLOW); GPU LANE UNTOUCHED; RESUME / MOVE-TO-GPU RECIPE

- **Stopped (owner request, 17:11 local / 22:11Z):** night `home80x60_cpu_2026-11-13` - `queue.ps1` pid 27472
  -> runner 14388/15196 -> search 30304/19532 (job 1 `cpu_p80x60__osse_ext_throat_s9012`, budget 120,
  `--backend beat_cpu`) -> CPU worker host 39192/37852 -> julia 34360. Killed by explicit PID, CPU lane only:
  no image-name kill, no `gpu-clean`, no forced host clear, no queue-file edit.
- **Measured reason:** the run reached **5/120 candidates in ~47 min** and its in-flight solve wrote no row for
  27 min; the GUI's independent read at 22:05Z reported 4/120 at ~6.1/h, ETA ~1141 min. The night file budgeted
  ~103 s/eval from `rev2_cpu_parity2`, so this config costs ~5-6x more per eval than that baseline and 120 evals
  could never fit the 4.5 h job timeout or the 23:30 cutoff. The Julia host was working, not wedged: +50 CPU-s in
  8 s at ~1.5 GB RSS. Cause of the per-eval cost not diagnosed [inferred: the 80x60 extended-throat mesh/band,
  not lane contention - the two-lane concurrency claim was retracted in `9019cbd`].
- **State left behind:** `runs/20261113T212428Z-screen-2c4d56` (beat_cpu, cma_seed 9012, budget 120) holds
  **5 partial candidates**, `run.json` still `status: running` (killed before the final write), `best.json`
  present; `cache_cpu/` and `dataset_cpu/` intact; job 2 `cpu_p80x60__ath_core_14in_s5678` (budget 80) never
  started. `runs/.cpu.lane.lock` is stale (holder pid 15196 gone); `cpu_lane_lock` takes over a stale holder,
  so it was left in place.
- **GPU lane verified untouched and progressing across the kill:** `home80x60_day_2026-11-13` (runner
  20608/6848, search 33268/36636 on `p80x60__ath_core_14in_700_v7`, GPU host 39760/40920, julia 40236 ->
  run `20261113T193536Z-screen-81c964`) went 129 -> 130 candidates with julia +21.9 CPU-s / 20 s right after
  the kill. It is the only julia left alive.
- **Restart A - resume on CPU (same physics):** `hornlab-search search --resume
  runs/20261113T212428Z-screen-2c4d56 --budget 120 --backend beat_cpu --cache-dir cache_cpu --dataset-dir
  dataset_cpu`; `run_campaign_night.py` also accepts `resume: <run dir>` in a job spec. Size the timeout from
  the measured ~9.4 min/eval, not 103 s.
- **Restart B - move to GPU (recommended, after 23:30 when `home80x60_day_2026-11-13` releases the GPU):** the
  same two job commands with `--backend cuda`, without `--cache-dir cache_cpu --dataset-dir dataset_cpu`.
  Prefer a **fresh** run over `--resume` of this directory so the run provenance stays single-backend; the 5
  CPU candidates stay in `dataset_cpu` for the parity record.
- Nothing was deleted: the partial run and both lane caches remain on disk for analysis.

## 2026-11-13 (22:05Z) - GUI: CPU LANE RUN PROGRESS + SPEED PARITY

- `gui/data.py`: `current_cpu_run()` resolves a fresh `--config` CPU search from the newest
  CPU-lane-tagged run folder â€” the job log's `output <dir>` line is block-buffered and can stay
  invisible for the whole run (live 2026-11-13 case: `cpu_current` was null while the run wrote rows).
  `cpu_current` now carries the GPU-card shape for BOTH job kinds: `kind`, `session {n, budget,
  resumed, n_resumes, started}`, `rate_per_h`, `eta_min`, `best_j`/`seed_j`/`session_best_j`,
  `failures_session`, `backend`. CPU verify jobs report n vs their `--top`/`--designs` target, rate
  and ETA from their own filtered rows. A 120 s session-vs-job-start guard prevents claiming an
  older completed run; unknown target/one row -> null bar/rate, never invented numbers.
- `_lane_run_info` / `GET /api/lanes`: additive `rate_per_h`, `eta_min`, `session_n`, `budget`; the
  lanes table now resolves fresh `--config` jobs for BOTH lanes (lane-tagged run fallback with the
  same guard), not only `--resume`/`--run-dir` commands.
- `gui/static/app.js`: `cpuRunningCardHtml` mirrors `currentRunCard` â€” progress bar, session %,
  ETA, Best/Started/Rate/Failures KPIs, "Open run". Home CPU card sits directly under the GPU card;
  Status gets a full-width `#st-cpu-current-card` below `#st-current-card` and the compact grid card
  is a real `.status-card` that says evals vs verified. Sidebar lane chips now read the real
  `session_n`/`n_rows` (the old `run.n` key never existed) and show rate/ETA when present.
- Tests: **90 passed, exit 0** (CPU progress/lanes/node guards/home/shell/night-status/views/visual
  audit/brief authoring/run identity/verify jobs/server warm); `compileall hornlab_search/gui` exit 0.
- Live read-only evidence: CPU run `20261113T212428Z-screen-2c4d56` (4/120, ~6.1/h, ETA ~1141 min,
  best 4.70, start 5.98) and GPU run `20261113T193536Z-screen-81c964` (125/200) resolve independently
  through `App.get('/api/status')` / `'/api/lanes'`; the real ES module renders the live payload with
  a progress bar and the expected KPI text.
- Caveats: not visually verified in a browser (server restart + hard refresh required); verify-card
  evidence is synthetic (no live CPU verify job). Pre-existing: the lanes table matches queue logs
  by filename (`queue_*gpu*`), so a GPU night named without `gpu` (today's `queue_home80x60_day_...`)
  still shows idle there â€” the GPU full-width card is unaffected.

## 2026-11-13 (~23Z) - A1 CACHE NAMESPACES + A2 SEAM FIX LANDED (offline)

- A1: shared solve/mesh caches now live under `<cache>/{solve,mesh}/p2-<sha12>/` keyed on beat/bempp/mesher SHAs
  (+gmsh); unknown SHA disables the shared cache. Legacy flat entries untouched (first run after this re-solves).
  Failure markers move with the namespace. `identity_v2.implementation_solve_id` added (unwired).
- A2: seam probe = lower band's last frequency, solved on the UPPER mesh; per-edge `pass`, `meta.seam_ok`,
  `meta.band_meshes`. Warning only.
- Tests: 41 passed, 1 skipped (build123d) across cache/evaluate/seam/feasibility/mesh_fidelity. Full suite not run here.
- Next: A5.4 wiring (feasibility into record meta); A1b `tools/m3_measurement_pack.py:340` flat root.

## 2026-11-13 (~22Z) - A4 MESH FIDELITY TOOL LANDED (offline)

- `tools/analysis/mesh_fidelity.py` + test (2 pass, fixture only). Source tag = SD1D1001; uses build.read_msh_summary
  plus a small $Elements tag loop (meshio not installed). Not yet run on a real project mesh.

## 2026-11-13 (~22Z) - A5 FEASIBILITY PREFLIGHT LANDED (offline, not wired)

- `hornlab_search/solve/feasibility.py` + `tests/test_solve_feasibility.py` (4 pass, conftest skipped: no numpy in cloud env).
- Not wired into evaluate.py yet (A5.4 after A2). Open question: beat_metal raises ValueError (unmapped).

## 2026-11-13 (~22Z) - SOLVER SPEED PLAN REV 2: SENIOR REVIEW AGAINST CODE (docs only)

- Plan rewritten as step-by-step packages a subagent can follow, checked against `a783b88`.
- A1 changed to namespaced cache roots (`<cache>/solve/<ns>/<key>`), because `cache.store()` would overwrite a
  legacy entry stored under the same key; `hornlab_search`/`hornlab_plots` SHAs excluded so commits don't empty the cache.
- A6 dropped (replay already refuses v5+). A1 and A2 now run in parallel (disjoint regions of evaluate.py).
- A5 fused-CUDA memory factor 4x calibrated on FUSED_CUDA_2026-10-24 (12,183 DOF ~4.7 GB).
- Orchestrator 2 (fork + mesher) must run on the owner's machine; Wave B waits for the home80x60 night to end.

## 2026-11-13 (~21Z) - SOLVER SPEED PLAN: TWO HANDOFFS MERGED INTO ONE PARALLEL PLAN (docs only)

- Owner asked to implement both 2026-11-13 handoffs (local-agent senior review; Huygens solver-speed review).
  Both added verbatim under `docs/throughput/`; merged plan `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md`.
- **Next:** Wave A, two orchestrators in parallel, offline only. Orch 1 (HornFab Python): A1 cache provenance
  (blocker for any pin change), A4 mesh fidelity tool, A5 feasibility preflight, A6 replay honesty, then A2 seam fix.
  Orch 2: A3 BEAT fork identity-cache patch (pin unchanged), C1 CPU-only rear-density mesh audit.
- GPU Wave B (G1 batching, G2 fork A/B, G3 screen fidelity, G4 rear, G5 band split) waits for queue slots and Gate 0.
- No code, solve, queue or cache change in this commit. Handoff claims not re-verified; each package re-reads code.

## 2026-11-13 (~21:37Z) - HF DATASET UPLOAD COMPLETE (per-file retry; verified)

- Uploaded the 8-tar stage `C:\Users\hunte\Hrns\.hf_stage_hunter` (12.82 GB) to the root of
  `chingadalleva/hornlab-search-data`. Repo `last_modified 2026-11-13 21:36:46Z`; all sizes and LFS
  SHA-256 match `stage_hashes.json` (`ALL_MATCH=True`).
- The 13:37 scheduled task verified hashes but its bulk `hf upload` exited 1 without a commit; a bulk
  retry hit repeated S3 multipart resets. The successful path was a detached per-file retry loop
  (`ops/hf_upload_retry.ps1`, commits `f0a403a`/`a3c7e01`/`3babbe7`/`0e7d367`/`4cb907a`/`a1d4bee`/
  `f529366`/`ef36d14`). The task was unregistered. Record: `docs/evidence/HF_UPLOAD_2026-11-13.md`.
- Snapshot cutoff remains ~04:51-04:56Z (1,501/1,726 g9 rows). The print-day `p80x60` searches are
  still writing; ISSUES L5.7 remains open for the final re-pack after the 23:30 cut-off. No
  code/queue/default change.

## 2026-11-13 (~22:0xZ) - TWO-LANE SLOWDOWN CLAIM RETRACTED (timeline audit, docs only)

- [measured] The section-6 night-report claim "GPU at 136/h with the CPU lane concurrent (~-14%)" is
  retracted: c2b (CPU) ran 18:37-20:12Z, g2 (GPU) 20:02-22:15Z -> real overlap ~10 min (7.5% of g2).
  c2b mostly ran while the GPU lane was DOWN (Windows-Update restart gap ~16:4x-20:02Z): the CPU lane
  delivered 285 verify/screen evals into GPU-down time, nearly free. Solo fresh-screen spread
  (g3b 114/h, g2 136/h, g4 178/h) is config/mesh variation, not a measured concurrency cost.
- [inferred] Whether sustained GPU+CPU fresh-screen concurrency costs GPU rate remains unmeasured;
  needs a window with both lanes running fresh screens for hours in parallel.
- Correction appended to docs/evidence/NIGHT_2026-11-12.md; ISSUES updated in the same commit.
## 2026-11-13 (~21:2xZ) - FINAL NIGHT REPORT 2026-11-12 LANDED; STAGED A/B CROSS-REFERENCED (docs only; L5.7 still owed at next GPU boundary)

- [measured] `docs/evidence/NIGHT_2026-11-12.md` finalised via `tools/night_report.py` across all six
  night files (gpu_2026-11-12, gpu_day_2026-11-12, cpu_day_2026-11-12, gpu_day_2026-11-12_cont,
  cpu_day_2026-11-12_cont, gpu_day_2026-11-12_cont2) with the orchestrator section-6 analysis appended:
  GPU 4818 evals (3937 valid / 903 refused), CPU 285 (273 / 17); fresh-search rates g3b 114/h, g4 178/h,
  g2 with the CPU lane concurrent 136/h (~-14% vs the 157.8/h CAMPAIGN_SMOKE baseline); ~43% GPU idle
  share over the 27.6 h chain span, dominated by the 17:41Z Windows-Update restart and human-paced
  night-file edits; n1 headlines cross-referenced (fused ON wins; b12 1.9-4.7x warm wins; 8k fused-off
  OOM at 7499-7731 MiB = hard 8 GB ceiling, no WDDM spill reading); atlas `377bbe` +398 cells
  (1328 -> 1726 rows, best J 1.666 -> 1.6655); Le Cleach v6 450 rows best J 1.52916; cross-backend
  parity c2 0.831889 (CPU, seed 1236) vs g7 0.831933 (GPU, seed 1235), dJ 4.4e-5; no section-4
  failovers taken (only the planned n1 bench OOM; n7's launch failure was repaired by g5 in cont2).
- `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`: the 2026-11-12 GPU acoustic A/B verdict is appended
  (joint control wins, J 2.438855 vs staged 2.629049 at ~equal budget; "promote staged into
  hornlab_search/search" stays NOT-YET). INDEX: final NIGHT row added; both STAGED rows carry the GPU
  result; the PARTIAL row points at the final report.
- **L5.7 still owed:** `hf_sync pack --groups text,dataset` + `upload` at the next GPU job boundary
  (dataset continuously written by the print-day p80x60 searches until the 23:30 cut-off tonight);
  recorded in `NOTES_FOR_SENIOR.md` (append-only) and `docs/ISSUES.md`.
- Push rule: this commit carries the CONTINUITY entry + ISSUES line + INDEX rows it describes.

## 2026-11-13 (~21:1xZ) - LOCAL-WORK AUDIT: MAIN CLEAN AND PUSHED; LOCAL-ONLY REFS, ORPHANED STASHES AND THE HOME-LEVEL REPO RECORDED (docs only, no code change)

- **Audit trigger (owner):** study all uncommitted local work that needs to reach GitHub. Snapshot
  2026-11-13 15:54 local (~20:54Z): `main == origin/main == adc1e15`, working tree clean. The same-day
  work was landed by the integrator while the audit ran: `8f5ae9e` (home 80x60/700 brief + cells, S5
  seed packs) and `adc1e15` (Elites thumbnails are frozen shaded 3D renders, three.js). Nothing in the
  canonical checkout is uncommitted.
- **Verification run during the audit (read-only):** `node --check hornlab_search/gui/static/app.js`
  exit 0; `.venv\Scripts\python.exe -m pytest tests/test_gui_elites_ui.py
  tests/test_tools_analysis_seed_pack.py -q -p no:cacheprovider` -> **49 passed, exit 0**.
- **Not on GitHub and outside `main` (recorded for senior review; NOT acted on):** 57 local-only branch
  refs (28 `backup/consolidation/*`, 9 `swarm/*`, 8 `meh/*`, 7 `feat/gui-*`, `pr/22`, `pr/23`,
  `integ/pr17`, `consolidation/local-main-2026-11-12`, `backup/pre-consolidation-main`,
  `dev/fused-cuda-pin`). Only FOUR commits are reachable from no remote: `bf7f003`
  (`backup/consolidation/T`; main's copy of the plan is newer, so superseded), `aa9011c`
  (`backup/consolidation/L1`; only adds `.git-commit-msg-l3.txt`), `1078cd2` (`feat/gui-integration`
  merge; both parents already in main, a topology artifact), `65c03de` (`dev/fused-cuda-pin`; a
  `file://` fork pin whose message says dev-only, never main).
- **Orphaned stash-like commits (unreachable; `git stash list` is empty):** `f4bddb6` (old Elites
  app.js/app.css WIP, 676-line payload), `3bdb50e` (`bo_sensitivity.py` +1605), `1f6750d` (swarm-H
  rescue), `0d3c8c1` (profiles). `e3081e3`, `2d445ab`, `08f849e` are byte-identical to main. The four
  differing snapshots are the only copy of those states and are GC-eligible.
- **Home-level repo `C:\Users\hunte\Hrns` (owner decision 2026-11-13: leave alone, log only):** 0
  commits, branch `master`, no `.gitignore`, remote `https://github.com/llevaachingada/Hrns.git`
  (reachable but empty), 30,123 untracked paths at audit time - 30,066 under `oc-wt/` because each
  worktree's `.git` is a file, so git recurses into 28 full checkouts. Created by Codex turn-diff
  checkpoints (`refs/codex/turn-diffs/...`; still zero commits). **Never `git add -A` there.**
- **BO-on-main policy note:** the earlier entry says BO/studies work goes to a local `bo-study` branch
  "(not pushed)", but no such branch exists and the BO commits are already public on `origin/main`
  (`6b41e0e`, `5fb0d5d`, `9b798f5`, `c7dd6a3`, `d9493cb`, `44f1c69`). No going-forward policy chosen;
  decisions listed in `docs/ISSUES.md` and `NOTES_FOR_SENIOR.md`.
- **Doc gaps found:** `adc1e15` updated CONTINUITY but not `docs/ISSUES.md` (the push rule asks for
  both); `oc-wt/bo-study/CONTINUATION_SLICE_MAP_2026-11-13.md` is the only bo-study handoff not mirrored
  under `docs/research/bo_study/` (the other eight are identical or superseded there).

## 2026-11-13 (~20:1xZ) - HOME 80x60/700 DAY QUEUE, CP-7b PARITY CLOSED, BO/CORE COMMIT SPLIT

- **Owner direction (decisions delegated):** printed horns for the living room; ~80x60 is inspiration only;
  priority is consistent directivity in both planes plus realistic loading down to a 700 Hz crossover with the
  researched 1.4-inch drivers. New brief `examples/briefs/print_80x60_2026-11-13/room_80x60_700_hf1440_v7.yaml`
  (parent room_90x60_800_shelf_v5; FaitalPRO HF1440, min_xo 700; cov weight 0.6, tolerance 4; dislope, flat_cv
  and diag weights 1.0; load 1.0, z_min 0.5, loaded_hi 5600; f0 = f0_v = 700; envelope 600x780x480).
  Cells are in `examples/typologies/print_80x60_2026-11-13/` (osse_ext_throat with seeds 1234 and 5678, plus
  ath_core_14in), and all pass shape_check. keele, lecleach and rosse were dropped because their seed mouths are 706 mm.
- **GPU night `home80x60_day_2026-11-13`** launched 11:30, cutoff 23:30, budgets 250/200/200 (runs/nights/).
  First seed: pattern break H 584-635 Hz, V 641 Hz.
- **CP-7b closed in aggregate:** four independent GPU/CPU pairs (s0, m4, s1, a1core); max |dSPL| 0.079 dB and
  every pair within 0.2 dB. lane_parity.py counts one design per pair, so each per-pair file still reads FAIL.
- **Review fixes (studies.js):** cancel no longer requires a ready panel; the policy selector reads a
  CLI-written `proposal_policy`. Open review notes: launch idempotency is in-memory (StudyRunBridge) and must become
  durable before a real launcher is wired; launch without a key returns invalid_input.
- **Git:** the owner asked for the BO/studies work to stay off main, but a concurrent integrator had already pushed it
  to main (6b41e0e..a783b88). It was left there: botorch is lazily imported, real dispatch is off by default, and the full
  offline suite is green (3642 tests, 0 failed, 18 skipped for the optional bayes venv). Moving it to a fork would mean reverting it from main
  (an owner call). This commit adds the home brief/cells and S5 `tools/analysis/seed_pack.py` (+47 tests).

## 2026-11-13 (~17:xxZ) - BO-STUDY v1.1 CONTINUATION: S5 SEED PACKS, HOME TASK REGISTRY (offline; no solve)

- Authorized continuation from the 15:0xZ session (parent integrates; no git push from this agent).
  No BEM/GPU solve, no gpu-clean, no queue edit, no dataset/cache/run-dir write.
- **S5 seed packs (`tools/analysis/seed_pack.py` + `tests/test_tools_analysis_seed_pack.py`):**
  `build_seed_pack()` reads a catalog.json/CSV (catalog.py output) and optional offline_scores.json,
  filters to complete-score records matching task/family/fidelity/objective_version, deduplicates
  by design_hash, applies optional score-percentile floor, then selects k diverse exemplars with
  greedy max-min diversity (feature: normalised J score; fallback to best-k when numpy absent).
  Every selection keeps full source provenance (shard/row/run_id/design_hash/score/fidelity/config);
  round-trip is "hash_identity" (recorded hash is non-empty hex) or "hash_missing"; full geometric
  round-trip (calling config's GeneratedSpace.to_design and comparing resulting hash) is flagged
  `needs_config=True` and NOT run here â€” no mesher dependency. Duplicate hashes, missing
  provenance, and score/shard gaps are labelled, not silently dropped. No fabricated warm starts;
  all selected hashes are verified verbatim present in the input catalog.
  47 fake-fixture tests (no mesh or BEM); all pass.
- **Home task registry (item e, `hornlab_search/studies/builders.py`):** second registered task
  `p80x60__osse_ext_throat_home700_v7` (config `examples/typologies/print_80x60_2026-11-13/
  p80x60__osse_ext_throat_700_v7.yaml`, brief `examples/briefs/print_80x60_2026-11-13/
  room_80x60_700_hf1440_v7.yaml`, objective version 7) added to `_TASK_REGISTRY` and
  `_ALLOWED_TASK_NAMES`. `_read_task()` now looks up the registry for defaults when no explicit
  config/brief paths are supplied; the M0 native contract (`DEFAULT_CONFIG`/`DEFAULT_BRIEF`/v4)
  is unchanged. Home task has no evidence root yet â€” any snapshot/training build without explicit
  source paths raises `Unavailable` (insufficient data until first cohort). M0 test suite still
  passes (7 builder + 9 evaluator + 1 lifecycle tests).
- **Verification (this session):** project venv `pytest tests/test_tools_analysis_seed_pack.py
  tests/test_study_builders.py tests/test_study_evaluator.py tests/test_gui_study_lifecycle.py
  tests/test_bo_extensions.py tests/test_bo_policy.py tests/test_bo_pareto.py
  tests/test_surrogate_capability.py tests/test_search_outcomes.py -p no:cacheprovider` â†’
  **154 passed, exit 0**; studies suite (58 tests) â†’ **58 passed, exit 0**; isolated bayes-venv
  `tests/test_bo_*.py` â†’ **101 passed, 4 skipped (mesher absent), exit 0**; `node --check`
  `hornlab_search/gui/static/studies.js` + `app.js` â†’ clean exit 0; `gui_study_lifecycle.mjs` â†’
  "study lifecycle ok", exit 0. Full offline suite running in background.
- **Committed and pushed** by the parent integrator at the owner's explicit request on 2026-11-13
  (no merge, no force-push; the working-tree changes are split into the logical commits above).

## 2026-11-13 (~15:0xZ) - BO-STUDY v1.1 COMPLETION: F0/F1/S1/S2, B7 WIRING, M3 BUILDERS/API/GUI (offline; no solve)

- Owner-authorized continuation to full offline completion (3-worker waves + parent integrator,
  one canonical checkout). No BEM/GPU solve, no gpu-clean, no queue edit, no dataset/cache write
  from this session; only read-only evidence scans and synthetic/fake tests were run.
- **M0 freeze signed** (`docs/research/bo_study/PARENT_M0_FREEZE.md`): status SIGNED 2026-11-13,
  checklist complete, ATH eligibility statement recorded. Eligible for offline advisory M2/M3
  work (197 native rows / 192 geometries / 197 physical solves; parity 197 compared / 200 replayed,
  max |dJ| 0, zero backend calls); **not** eligible for a closed-loop benefit claim because
  independent experiment groups are `insufficient_evidence`. No pooling of the four-config census,
  narrow config, other brief/version/backend/fidelity, or the stale inline target.
- **F0 (plain CMA, `cma.py`/new `search/outcomes.py`/config):** typed outcome classification
  (complete/measured-gate/deterministic geometry-envelope-resource/transient/metric/unknown), new
  opt-in `infeasible_penalty: resample_strict` + `error_policy: retry_same_then_stop`; strict
  refusals are replaced â‰¤10x and never told; transient `solve_failed` retried on the same
  candidate/spec at most 2 total backend calls, then a resumable stop before tell; metric/unknown
  stop diagnostically; bounded draw cap includes seed/replacements/cached refusals while cache hits
  consume no new/valid/attempt budget; only eligible complete scores become `best`;
  `cma/strict_state.json` restores cumulative counters/caps, records explicit extensions and refuses
  shrink/incompatible protocol. Missing-input gate penalties are **not** tell-eligible; only an
  explicitly measured gate (`gate_measured`) is (v8 remains unregistered and does not emit it yet).
- **S1/F1 (CMA-ME, `cma_me.py`):** archives the normalized geometry actually evaluated (warm mean
  stays the emitter mean); `FailureExcludingGridArchive` excludes non-complete/missing-descriptor
  rows from both search and result archives with full-batch status/value stitching and a
  failure-last ranker (`qd.protocol=cma-me-archive-v2`, disclosed non-trajectory-neutral); MAE
  thresholds are finite and `<1000`; opt-in infrastructure retry before `tell`; pending-intent
  `qd/pending_batch.json` + `qd/strict_state.json` reconcile durable failures and unknown attempts
  before any `ask`, with cumulative counters/caps persisted across resumes and explicit extensions.
  Deterministic QD refusals retain the disclosed legacy finite-penalty emitter policy; no
  feasible-only learning claim. The parent-review contract for a future constrained emitter is
  recorded in `docs/research/bo_study/QD_CONSTRAINED_EMITTER_DESIGN.md` (proposed, not active).
- **B7 wiring:** `bo/policy.py` unified `scalar`/`pareto`/`cma_seed`/`exploration` capability and
  `fit_and_propose` dispatcher; `bo/__init__` exports the Pareto/constraint/cost/trust-region
  surface; `bo.propose_by_policy` lazy delegate. Runner/GUI now select the policy; Pareto stays
  capability-gated on validated cohort + complete canonical metrics + engine.
- **M3 (studies/GUI):** `studies/builders.py` (contained snapshot/training/analysis/model/pool/
  proposal artifacts; signed native evidence reuse; capability refusals are artifacts, never fake
  candidates), `studies/evaluator.py` (`PipelineStudyEvaluator` with injected evaluate/lookup/
  preflight/fit/propose, screen caps, 4-finalist+2-audit selection, outcome mapping, progress/RNG
  restore; production wiring refuses until the real pipeline/lane are injected), `service.artifact_view`
  (bounded, path-like rejection, binary/NPZ metadata only), package `proposal_policy` + a semantic
  gate that refuses capability/model/pool-refusal proposals (accepts a selected candidate or a
  labelled exploration fallback), CLI snapshot/analyze/propose now build/attach, and API
  `GET /api/studies/<id>/artifacts/<kind-or-sha>` + `POST .../{package,launch,cancel,decision}`
  (`/decide` preserved). Launch is an explicit 503 until an integrator injects the production
  launcher; no shell/GPU cleanup path. GUI adds the frozen policy selector/capability card,
  package/budget/lane/deadline/stop-recovery/verification/progress view, Package/Launch/Cancel/
  Decision actions, typed artifact panels, idempotent duplicate-click handling, stale-generation/
  abort/timer disposal, and a DOM-stub route-lifecycle test (no jsdom/Playwright is installed; full
  browser render remains untested).
- **S2 (read-only):** `tools/analysis/cache_producer_audit.py` + evidence
  `docs/evidence/bo_study_2026-11-12/s2/{cache_producer_audit.json,md}`. Bounded sample: 25,931
  entries (25,707 main + 224 CPU), 400 sampled, **400/400 with unknown producer evidence** (no
  library pins in the status keys), 399/400 score-only reusable under today's lookup; 28
  source-level caller sites recorded. No enforcement, no cache write/deletion, no default change;
  legacy unknown stays unknown.
- **Surrogate capability:** explicit v1-only matrix (`SUPPORTED_OBJECTIVE_VERSIONS=(1,)`, typed
  `UnsupportedObjectiveError`, `capability_status`/`require_supported`); bundles record
  `objective_version`/`scoring_capability`; train/predict/round/CLI refuse v2+ and incomplete v1
  inputs instead of scoring newer objectives with v1 math or fabricating throat impedance.
- **Dependency:** `pyproject.toml` optional `bayes` extra registered (`torch`, `botorch==0.18.1`,
  `gpytorch==1.15.2`, `linear_operator==0.6.1`); the live venv is unchanged and BoTorch stays
  lazily imported.
- **Independent review:** an oracle review of F0/F1/S1/S2 found 4 real gaps (QD transient resume,
  unmeasured-gate classification, QD cumulative caps, strict stop-reason). All four were fixed and
  pinned by tests before the final suite.
- **Verification (current tree):** project venv `pytest tests -o addopts='' -q -m "not gpu and not
  crosscheck and not slow"` -> **3577 passed, 18 skipped, 21 deselected, exit 0** (23:30);
  isolated bayes venv bo suite -> **131 passed, 4 skipped, exit 0**; `compileall` over
  search/config/bo/studies/gui/surrogate/tools and `node --check` studies.js+app.js clean; CLI
  smoke: create/snapshot/analyze built artifacts in both venvs, propose returned an honest
  `capability_missing` artifact (project venv lacks BoTorch; bayes venv lacks hornlab_mesher for
  candidate revalidation), package correctly refused that proposal, and a valid fixture package
  `run --dry-run` returned exit 0 with the exact 18/6/24/120 budget/lane/deadline. No real BEM
  solve or acoustic/speed claim.
- **Environment limit:** no single sanctioned interpreter currently has **both** BoTorch and
  `hornlab_mesher`; a live study fit+revalidation needs a combined `bayes` environment (or the
  M2 split-engine path). The committed M2 proposal remains the real precomputed evidence; the
  study builder code path is fixture/engine-tested. Real pilots/adoption remain owner-gated.
- **No git push/merge** from this session; only the parent integrator edited files.

## 2026-11-13 (~06:2xZ) - BO-STUDY v1.1 FINAL INTEGRATION: M2 EVIDENCE, EXECUTION PACKAGE, B8 FULL LOOP (offline; no solve)

- Owner-authorized final offline pass (3 background lanes + parent integrator, one canonical
  checkout). No BEM/GPU solve, no gpu-clean, no queue edit, no dataset/cache write from this
  session; the live GPU night queue and a parallel rev2 CPU-parity night ran independently.
- **M2 evidence (lane A, committed `c7dd6a3`):** real 197x13 native TrainingSet sensitivity over
  7 subsets (frozen / all / stratified-64/128 / lowJ+maximin-64/128 / screen-only 192) x noise
  0.1/1/10 x two independent 4096-Sobol pools; 14 off-policy BO proposals + 2 maximin
  space-filling references; descriptive only (no independent-group links). Immutable
  `m2/proposal.json`: frozen scalar_pool_v1 fit, candidate `pool-20261112-03873-5c02b169`,
  predicted J 3.914145, unclamped sign-reversed credible interval [-4.144184, 11.972474],
  acquisition -0.174728 labelled a ranking diagnostic, materialized geometry revalidated
  (envelope/throat/hashes); predictions never appended as measured rows. `m2/pool_manifest.json`
  is content-identical to the committed B2 4096 pool (3143 cheap-check-passed candidates).
- **Execution package + study CLI (lane B, committed `9b798f5`):** `studies/package.py`
  (`prepare_run_package` binds current spec revision + snapshot/model/proposal artifact hashes +
  protocol/pins/lane; body-only canonical artifact where `package_id == artifact hash`; budget
  exactly 18 screen / 6 verify / 24 total / 120 attempts; `deadline_required: true`; stop,
  recovery, adaptive-child and 4-finalist+2-audit verification policies; "cheap-check-passed;
  mesh/acoustic eligibility unknown"). `studies/cli.py` implements validate/create/snapshot/
  analyze/propose/package/run --dry-run/reconcile/decide/export with contained `--root`, strict
  argv allow-lists, typed JSON exit codes 0/2/3/4/5/6, and a dry-run that constructs no
  service/lane/adapter and spawns no solve. Parent wired `hornlab-search study ...`
  (`hornlab_search/cli.py`, REMAINDER passthrough). ProposalHistory index/RNG now round-trips on
  resume so the every-4th-maximin cadence never resets; `StudyEvaluatorAdapter` is a
  capability-gated skeleton (`capability_missing`), not a BEM adapter.
- **B8 adversarial (lane C, committed `1e02e88`):** 23 new tests across workflow, crash/
  idempotency/concurrency, lane/bounded-GUI, CLI-leg and regression modules. Full fake-evaluator
  study create -> artifacts -> views -> package -> dry-run -> serial screen -> 4 finalists + 2
  seeded audits -> refit -> decide -> export -> child; crash injection after intent, dispatch,
  evaluator persistence, journal result and registry update; duplicate launch/retry/stale
  revision; CPU-lock ownership and no nested GPU lock; dry-run zero subprocess/dataset/NPZ/
  registry writes. One real defect found and fixed by the parent: explicit cancellation was
  reported as `stale` because `is_current()` was checked first; `runner.py` now checks
  `journal.cancelled()` before staleness at both stop boundaries (33 B8 tests green).
- **M1 regenerated (`79b6651`):** the committed `parameter_study` predated the tightened
  independent-evidence gate (said `recommendation_status: allowed` while the tool suppresses);
  regenerated to 200 replayed / 197 compared / max|dJ| 0 / 5 designs (hashes unchanged),
  recommendation suppressed. `source_fidelity` regenerated against the authoritative 200-row
  offline-scores artifact (197/197 cards carry `offline_score`, was 50; pairing unchanged at
  10 paired / 187 no-verify; DI balloon 197/197; source guard 212 files unchanged).
- **S11 complete (`9648ef9`):** both committed pilot manifests re-validated through the live
  `hornlab_search.cli` parser (no execution): `errors=0 warnings=0 ok=true`; validation records
  committed; removed the dead prototype test that imported a non-existent `parse_results/
  prepare/validate` API (superseded by 33 focused tests); `/cache_cpu/` and `/dataset_cpu/`
  ignored as CPU-lane runtime roots.
- **Suite hygiene:** 6 engine-only acquisition/propose tests now carry the existing
  `requires_botorch` marker (`829feb0`) so the project venv skips them honestly; the rev2 GUI
  honesty-copy commit left the K-law feasibility node pin stale, aligned in `ec84811` (parallel
  session) to the shipped "below the Keele ESTIMATE" wording.
- **Verification (current HEAD):** project venv `pytest tests -q -m "not gpu and not crosscheck
  and not slow"` -> exit 0 (3417 collected; optional-BoTorch tests skip honestly); isolated
  bayes venv combined bo suite -> 120 passed, 4 skipped (mesher absent there), exit 0;
  `compileall` over bo/studies/gui/tools and `node --check` app.js + studies.js clean; top-level
  `hornlab-search study package` then `study run --dry-run` smoke -> exit 0 with the exact
  budget/lane/deadline-required/artifacts. Live-dataset counters moved during the pass (expected);
  M1 artifacts record `generated_utc` and their own snapshot counts.
- Native cohort unchanged: 197 rows / 192 geometries, parity 197/200 max|dJ| = 0, zero backend
  calls; three shard-57 rows remain uncatalogued at snapshot time. v8 stays unregistered; no
  objective/default/config change; no ranking across objective versions.
- Unverified by design: production study evaluator/lane adapter (so the S9 A/B matrix is still
  not executable), real snapshot/analyze/propose builders (CLI reports existing artifacts only),
  real BoTorch in the project venv, and any acoustic benefit/speedup. Adoption/pilots remain
  owner-gated.
- Git: all slices committed; `origin/main` already contains them (the parallel rev2/GUI session
  pushed; this entry + ISSUES are committed for the push-rule). No further push from this session
  without explicit owner authorization.

## 2026-11-13 (~13:45Z) - NEXT-QUEUE HANDOFF SAVED; HF DATASET UPLOAD SCHEDULED

- Added `docs/research/NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md`: self-contained briefing for the
  next senior queue planner (verified night status, decision lineage, data inventory, K-law/8 GB
  retarget limits, constraints, adversarial verdict, three alternatives). No code/queue/default
  change. A status update inside notes that the M2/M3 integration and F0/F1 landed after the
  handoff's 03:52Z snapshot; the 50x50-vs-60-80 deg conclusion is unchanged.
- Night queue finished: g9 `atlas__ath_core` 1,726 evals, best J 1.66554 at 06:26:53Z. The 50x50
  work is benchmark data; the owner's 60-80 deg / ~700 Hz target is the product direction.
- HF dataset upload: stage `C:\Users\hunte\Hrns\.hf_stage_hunter` (8 tars, 12.82 GB) SHA-256
  verified; all tars differ from the 2026-11-03 repo state (v7 relabel + new rows/cache/text;
  `dataset-002.tar` is new). One-time task `Hornlab HF stage upload` at 2026-11-13 13:37:04 -05:00;
  log `C:\Users\hunte\Hrns\ops\hf_upload_2026-11-13.log`; `HF_HUB_DISABLE_XET=1`. The stage cutoff
  is ~04:51-04:56Z (1,501/1,726 g9 rows); a completed-night tail needs a repack. Record:
  `docs/evidence/HF_UPLOAD_2026-11-13.md`.

## 2026-11-13 - ELITES TAB REDESIGN (owner request: readable by a non-technical user)

- **Server (`gui/data.py`):** `elites_catalog()` cards now carry `brief`, `family` (typology) and
  `brief_target` `{h_deg, v_deg, f_lo_hz, f_hi_hz, max_mm}` read from the run's `config.yaml`
  (`target.coverage_h_deg/coverage_v_deg/band_lo_hz/band_hi_hz`, `envelope.max_mouth_w_mm/
  max_mouth_h_mm/max_depth_mm`; max of the envelope dims becomes `max_mm`). Per-run config reads stay
  memoized in `_elite_run_info` (once per run, not per card). Payload gains sorted distinct
  `briefs`/`families`. All existing fields, sort order, dedupe, cache stamp and `available=False`
  shape unchanged. Live check: 8,490 cards, families `[FREEFORM, OSSE, R-OSSE]`, a card carries
  `brief_target {50Â°, 50Â°, 300â€“8000 Hz, 650 mm}`.
- **Page (`static/app.js`, `static/app.css`):** replaced the audit-dump UI. New header
  ("Horn designs / Elites / Designs that passed every gate â€¦ best first") with plain counts; the CSV
  source list and per-card `Source: â€¦` lines are gone; the hash is now an 8-char chip, not the title.
  Cards show a **lazy isometric horn thumbnail** (drawn in SVG from the design's stored `profile`
  h/v polylines via `/api/design/<run>/<hash>?tier=screen`; IntersectionObserver, 4 concurrent,
  cached; placeholder when no geometry), a headline (`OSSE Â· â‰¤ 650 mm`), a constraints line
  (`brief Â· 50Â°Ã—50Â° HÃ—V Â· 300 Hzâ€“8.0 kHz`), gate pills, J and Open run. Filter bar: Brief and
  Typology selects with counts, **Best picks / All passing** toggle (brief â†’ best per typology,
  typology â†’ best per brief, both/neither â†’ best-first list), Refresh (re-pulls `/api/elites`) and
  Clear. Paginated 24 â†’ 48 â†’ â€¦ instead of rendering all 8,490 cards. Dark/light, 1500/900 px, theme
  vars only. New pure helpers exported for node tests (`elitesFilter`, `eliteHeadline`,
  `eliteConstraintLine`, `eliteThumbSvg`, `eliteCountsText`, `elitesNoteText`, `eliteCardHtml`,
  `elitesResultsHtml`, `elitesNoteText`).
- **Tests:** `tests/test_gui_elites_catalog.py` (payload) and `tests/test_gui_elites_ui.py`
  (node-stub: best-per-family/best-per-brief/all, counts, empty states, SVG builder, page shape â€”
  asserts no `docs/data`/`gate_audit`/`Source:` text). Full `-k gui` suite: 451 passed, 1 failed â€”
  the failure is the **pre-existing, other-lane pin** `test_gui_freq_range.py::
  test_feasibility_summary_and_objective_suffix` (shipped wording "V short: needs 498 mm" vs the pin's
  old "does not fit"); its correction is in flight in the main checkout and is committed with this
  merge so `main` stays green.
- **Card hierarchy (owner request, same day):** the constraint line (brief - H x V coverage - band) is now the card's largest text and the score (`J 1.975` + `J v4`) matches it; the typology/size headline is a quiet label and the green gate pills shrink to small status chips. CSS-only change in `app.css` (`.elite-constraints` 1.02rem ink, `.elite-j` 1.02rem/600, `.elite-gates .pill` 0.62rem, `.elite-title` 0.8rem muted). Verified live on 8765 (computed sizes + dark 1500/900 screenshots).
- **Thumbnail geometry fix (found live after the first ship):** `/api/design`'s `profile` is a
  **closed 2-D outline** (out along the outer wall to the mouth rim, back along the axis), not a
  radius-along-axis series. The first implementation binned every point by z and averaged the two
  branches, which flattened the wall into a midpoint (constant 203 mm in practice) â€” the cards drew
  a "lollipop" (big mouth ellipse + sliver). `_eliteProfileSeries` now splits the outline **in its
  original order** at the widest point (mouth rim), bins each branch separately and keeps the per-z
  outer wall; the series runs 25 â†’ 203 mm for `â€¦d7d61a7e4c4d`, and the thumbnails render a proper
  throat â†’ flare â†’ mouth isometric horn. Verified live on 8765 (12 thumbnails, no page errors).
- **Thumbnails are now real shaded 3D renders (owner rejected line art):** each card renders the
  design's horn as a frozen WebGL frame â€” a superellipse loft built from the stored profile
  (`eliteHornGeometry`: outer-wall axis from `_eliteProfileAxis`, section exponent from the design's
  own `params.n`, e.g. 7.58 â†’ squarish mouth like the mesher's) run through a **single shared
  offscreen three.js renderer** (`_eliteGLRender`, imported via `view3d.js::loadThree`; camera looks
  into the mouth like the reference render, transparent background, MeshStandardMaterial). One frame
  per card, captured to a data-url `<img>` and cached; one WebGL context total, disposed at each
  Elites page entry (`_eliteGLDispose`); queue concurrency 1; SVG outline stays only as the
  WebGL-unavailable fallback, and the placeholder for missing geometry. New pure helpers exported
  for node tests: `_eliteProfileAxis`, `eliteHornGeometry` (`tests/test_gui_elites_ui.py::
  test_elites_3d_geometry_guard` â€” outer-wall orientation, superellipse exponent vs ellipse, vertex
  counts, degenerate-outline refusal). Verified live on 8765: 11 WebGL thumbs + 1 fallback in the
  first viewport, no page errors.
- Screenshots (worktree server on 8801): `%TEMP%\opencode\elites_after\` â€” dark/light at 1500/900,
  brief/family/both/all filters, page 2, empty state, card zoom.

## 2026-11-13 - REV2 IMPLEMENTATION PASS (additive; nothing launched)

- Status table for every Rev2 item: `docs/research/QUEUE_PLAN_REV2_2026-11-13.md`.
- New: `metrics/acoustic_v2.py` (sphere DI quadrature, 3D lobes/islands, onsets, Keele estimate,
  analyze_response), `dataset/identity_v2.py`, `tools/analysis/acoustic_v2_report.py`, E0 manifest
  `docs/queue/rev2_E0_manifest_2026-11-13.json`. GUI balloon above-axis warning; K-law relabeled as heuristic
  (GUI + report). Solana/SAWMOD configs labeled "-inspired" (comments only, config_sha unchanged).
- Tests: `tests/test_metrics_acoustic_v2.py` 10 pass; analytic DI omni 0 / cardioid+dipole 4.77 dB.
  Wider suite not run (owner call). Smoke: report tool ran end to end on synthetic responses saved
  via `solve.cache.save_response`.
- Next: owner pulls, shape_check, launch both nights, then run acoustic_v2_report + lane_parity.

## 2026-11-13 - REV2 IMPLEMENTATION PASS (additive; nothing launched)

- Status table for every Rev2 item: `docs/research/QUEUE_PLAN_REV2_2026-11-13.md`.
- New: `metrics/acoustic_v2.py` (sphere DI quadrature, 3D lobes/islands, onsets, Keele estimate,
  analyze_response), `dataset/identity_v2.py`, `tools/analysis/acoustic_v2_report.py`, E0 manifest
  `docs/queue/rev2_E0_manifest_2026-11-13.json`. GUI balloon above-axis warning; K-law relabeled as heuristic
  (GUI + report). Solana/SAWMOD configs labeled "-inspired" (comments only, config_sha unchanged).
- Tests: `tests/test_metrics_acoustic_v2.py` 10 pass; analytic DI omni 0 / cardioid+dipole 4.77 dB.
  Wider suite not run (owner call). Smoke: report tool ran end to end on synthetic responses saved
  via `solve.cache.save_response`.
- Next: owner pulls, shape_check, launch both nights, then run acoustic_v2_report + lane_parity.

## 2026-11-13 - REV2 QUEUE PREPARED (NOT LAUNCHED): MATCHED ABLATION + FIDELITY LADDER + CPU/GPU PARITY

- From the owner's Senior Implementation Plan Rev2 (used as a guide). Plan, deviations and decision rule:
  `docs/research/QUEUE_PLAN_REV2_2026-11-13.md`.
- 12 pinned budget-1 configs in `examples/typologies/ablation_2026-11-13/` (all `load_config` ok);
  night files `docs/queue/rev2_gpu_ablation_2026-11-13.yaml` (13 jobs) and `rev2_cpu_parity_2026-11-13.yaml`
  (2 jobs), both `--dry-run` clean. Not mesh-checked (cloud session has no gmsh): run `tools/shape_check.py` first.
- Owner follow-up: ATH CORE-style arms added (5 configs, GPU night now 18 jobs). Added `metrics/acoustic_v2.py`
  (main-lobe first crossings, censoring, off-axis peaks) and unclipped above-axis stats in `gui/data.py::balloon`.
  Targeted tests passed (acoustic_v2 + gui_balloon, 13); wider suite not run per owner. Pushed to main per owner.
- No default, objective, contract or live-queue change. Large product CMA still deferred per Rev2.


## 2026-11-13 (~00:4xZ) - BO-STUDY M0-M2 LANDED, EVERYTHING COMMITTED AND PUSHED (owner-authorized, cloud completion next)

- Owner-authorized full commit+push of the two-agent bo-study-v1.1 implementation. Slices on
  main: M0 replay/rescoring + census + ledger (`3a48c27`), M1 parameter_study + source_fidelity
  (`c4fc315`), S9 harness (`2ba3bac`), then this push: `bo/` engines+policy (locked scalar
  GP/qNEI, pareto, contract/cost/TR, canonical metric policy, native TrainingSet 197x13),
  `studies/` registry+job bridge+runner foundations, GUI analysis overhaul + six-page study
  workspace + S10 renderers, `tools/experiments` pilot manifests, curated evidence
  `docs/evidence/bo_study_2026-11-12/` and parent records `docs/research/bo_study/`.
- Cloud completion kickoff: `docs/research/bo_study/CLOUD_COMPLETION_KICKOFF.md` (remaining:
  M2 sensitivity evidence, execution package + pilot package, B8 full adversarial loop,
  manifest executor fields, runner production adapter, docs rows â€” all offline).
- Verification this session: 43 studies + 65 GUI + 46 bo-metrics/cohort + 35 registry/runner +
  29 experiments + 9 bench suites green in the project venv; engine suites green in the
  isolated bayes venv (botorch 0.18.1); one bayes-venv-only failure root-caused to a missing
  hornlab_mesher and gated by the suite's existing `requires_mesher` convention (project venv
  passes the same test); node --check app.js + studies.js clean; one defensive .remove() guard
  fixed an eager route() shim TypeError that broke S10's node-execution test.
- Native cohort frozen: 197 rows / 192 geometries, replay parity 197/200 max|dJ|=0, zero
  backend calls; 3 shard-57 rows uncatalogued at snapshot (refused, recorded in ISSUES).
- No BEM/GPU solve was started; live queue untouched.

## 2026-11-13 (~00:2xZ) - GUI WORK MERGED INTO LOCAL MAIN; OWNER'S 8765 GUI RESTARTED ON IT; PUSHED (feat/gui-integration fully landed)

- The owner's own consolidation branch (`consolidation/local-main-2026-11-12`, `2ab94cf`) had already
  merged `feat/gui-integration` (up to the visual-audit fixes) + `day/2026-11-12-queue` (GUI-1/GUI-2
  session-aware status) + `lane/L4-hygiene` + `origin/main` into `main`; this session validated that
  union (duplicated-merge attempt aborted) and switched the main checkout to `main`.
- Validation on `main` before restart: full `-k gui` suite exit 0 (426 tests; includes the visual-audit
  fixes, WP7 verify jobs, session-aware status, day-queue union in app.js/data.py/CONTINUITY) and
  `test_cli_solve_lock.py` green. Day-queue union resolutions were committed on
  `feat/gui-integration` (`1078cd2`) as the lane-merge record; `main` carries the equivalent via
  `2ab94cf`.
- **Owner's desktop shortcut verified and serving the latest GUI:** the shortcut chains to
  `tools/launch_gui.ps1` (kill old `hornlab-search gui` processes â†’ start fresh on 8765) â€” unchanged
  and correct; the staleness was only local `main` not holding the GUI work. The 8765 server was
  restarted via the same script and live-verified: `/api/verify/â€¦ed1da9` returns
  `brief=b1w_hifi_90x60_850_wide_v4 band=300â€“8000` (features that did not exist this morning).
  Review server on 8799 (worktree) was used for the acceptance walk and for the browser session the
  owner opened mid-merge; it can be stopped without affecting the queue.
- Pushed `main` to origin (42 commits incl. WP0â€“WP10, finishing pass, visual-audit fixes, day-queue
  lane, L4, docs consolidation). Owner decisions today: brief-leader window 14 â†’ 31 days; direct
  main push instead of a PR (the consolidation already merged the lanes locally).

## 2026-11-12 (19:06Z) - GUI: LIVE, SESSION-AWARE STATUS FOR THE TWO-LANE NIGHT (fix(gui): A+B+C LANDED, CLOSED GUI-1 + GUI-2)

Context: the two-lane day queue (launched 14:35Z per the 14:30Z entry) was killed by the machine's
Windows-Update restart at 17:41Z; resumed at 18:13Z via `runs/nights/*_2026-11-12_cont.yaml` + the
repo's own detached `tools/night_queue/queue.ps1` chain. At entry time the GPU lane is on
g1b (`--resume runs/20261030T170642Z-screen-fbab4f --budget 117`, session ~75/117, ~100/h, best J
2.12827) with g2-g9 queued behind g1c; the CPU lane finished c1b (exit 0) and is on c2b
(core_law top-10 verify, job-relative 1/10 visible in the GUI). Nothing solver-side changed today.

GUI fixes (all data-flow only, from artifacts the CLI already wrote; no solver/queue code touched;
one GUI restart after each gui edit â€” `serve()` teardown is socket-only, proven safe twice while
both lanes solved):

- **Interrupted-queue resume state (first pass, ~18:30Z):** queue log pick by MTIME not name
  (lexicographic showed `queue_v5_continue_2026-10-29` all day); session-aware progress on
  `run.json "resumes"` boundaries (the interrupted g1 showed "894/117 (100%) over budget" in red â€”
  now "74 / 117 this session Â· resumed Ã—3 Â· 904 rows lifetime", session rate/ETA/failures; the old
  last-40-row rate window spanned the 12-day crash gap and reported 20/h vs 100/h actual);
  `current_run` scans ALL dirs (the `[:30]` cap would blank Home/Status as the queue created ~5 new
  run dirs); CPU lane lock/night/job/verify-activity + per-lane host counts (`GPU 1 Â· CPU 1 Â· 0 stale`).
- **Second pass (owner-approved A+B+C, ~19:00Z):** Runs page default sort **Recently active** +
  pulsing â— LIVE cell + `sess N` badge + `has_verify` marker (session fields from
  `run.json "resumes"`, `active` recomputed on every call incl. cache hits); Run detail
  **"Verify re-solves"** block from `<run>/verify/search.ndjson` with Î”J = CPUâˆ’GPU pairing â€”
  verified live on `20261030T111108Z-screen-377bbe`: |Î”J| â‰¤ 7e-05 J on the g0/c1 cross-check
  designs (strongest backend-parity evidence recorded); Runs version filter dropdown;
  `J_VERSION_BANNER` reworded to a neutral `role="note"` note with per-version count chips
  (**CLOSES GUI-2**; the amber alert read as an error on a corpus that always spanned v1-v7);
  CPU-lane `search` jobs get live session/rate/ETA via the night job log's `output <dir>` line;
  `current_run` skips runs whose last ndjson row is lane-tagged `cpu` (a busy CPU lane can never
  hijack the GPU lock card); watchdog pane removed (content was Oct-23); queue tabs over the newest
  5 queue logs with selection persisting across polls.
- **Tests [measured]:** `node --check` app.js + compileall + `L2 GUARD OK` (node guard in
  `tests/test_gui_views_l2.py` â€” new pins: banner string/chips/counts, active-sort, Î”J block) +
  96 offline GUI tests pass. Affected: `gui/data.py`, `gui/static/app.js`, `app.css`,
  `tests/test_gui_views_l2.py`; docs: `ISSUES.md` (GUI-1/GUI-2 CLOSED with evidence),
  `NOTES_FOR_SENIOR.md` (2026-11-12 entries, deferred list: Kill-confirm â€” untouched per owner,
  WP-D2 gates display, D4 elites catalog, W6 balloon, P8d, P9 sandbox, leaderboard latency).
- Deferred feature lanes (still open, by owner choice): see NOTES_FOR_SENIOR 2026-11-12.
- Continuation queues/artifacts live under `runs/nights/*_cont*` (gitignored run space).




## 2026-11-12 (22:15Z) - REFUSALS / CMA TRAJECTORY HANDOFF (PR #49)

- Added `docs/research/REFUSALS_AND_OPTIMIZER_HANDOFF_2026-11-12.md`: plain-CMA `resample` +
  `budget_counts: valid` + `max_attempts` as the simple "refusals never told" path vs CMA-ME
  (resample is a ConfigError; failed designs are told with seed measures; CMA-MAE is the archive-level
  mitigation), exact code paths/tests, measured refusal counts (core_law 567 ok / 434 refused; archive
  17 cells / 0 penalty), the dataset failure-metadata caveat (main 4,634/28,573 failed; `dataset_cpu`
  16/237; D.3 merge has no ok filter), over-constraint guardrails, and an offline verification plan.
- No code, queue, or default changes. The external council handoff now points to it. The GPU night
  queue is still running.

## 2026-11-12 (22:05Z) - PARTIAL DAY EVIDENCE COMMITTED (PR #48)

- Committed the PARTIAL day evidence while the GPU continuation queue (`g2`â€“`g9`) runs:
  `docs/evidence/DAY_2026-11-12_ANALYSIS_PARTIAL.md` (A.8 partial, 13 sections + 10 charts;
  appendices: A.7 PASS 5/5 <=0.2 dB, 24-run fidelity census, 25-seed variance median 18.589 /
  spread 4.780, D.3 dry-run PASS 237 rows) and `docs/evidence/NIGHT_2026-11-12_PARTIAL.md`
  (5 nights; `gpu_day_2026-11-12_cont` has g1b/g1c only; c2b BEAT worker-reset note). The partial
  `tools/analysis/specs/day_2026-11-12.yaml` fill is committed too.
- No code, queue, or default changes. Final report/A.6/PR #25/F.1/D.3 wait for `g2`â€“`g9` (or owner).

## 2026-11-12 (21:35Z) - RESEARCH PLAN + EXTERNAL REVIEW HANDOFF SAVED (PR #46)

- Saved `docs/research/DATA_GA_RESEARCH_PLAN_2026-11-12.md` (research-only: inventory of today's
  A-G/R/fix groups and all worktrees; dataset exploitation; seed/parameter discovery; visualization;
  ranked CPU-only work queue; merge map; owner decisions) and
  `docs/research/COUNCIL_REVIEW_HANDOFF_2026-11-12.md` (self-contained brief for an independent
  council review + senior implementation plan).
- No code, queue, or default changes. The plan is explicitly raw/pending external review; the
  handoff records the verified state (main 15644ca, PR #47 G follow-up merged, PR #25 last, live
  checkout 79edc8d not on main) and the freeform_sculpt census correction (25 equal-budget seeds
  5101-5125, median 18.589, spread 4.780; the 26th is a 777-row seed-1234 base).

## 2026-11-12 (21:15Z) - G FOLLOW-UP: MEASURED V8 TOLERANCES + FULL RE-SCORE (PR #47)

- The merged G proposal shipped `V8_MEASURED_TOLERANCES` as all 1.0 placeholders and brief Â§4 as
  `<!-- V8_RESULTS -->`. This lands the finished full-dataset re-score: per-class A/B/C tolerances
  in `scalar_v8.py` and the full Â§4 tables.
- [measured] `v8_rescore.py` over the committed dataset: 23,833 rows scored; class A 18,145 / 0
  refusals, tau(v8,v4)=0.5004, top-20 4/20; class B 4,063 / 3,545 refusals (87%) / 518 rankable,
  tau 0.7687, top-20 0/20; class C 1,625 / 0, tau 0.8150, top-20 13/20. The class-B refusal rate
  is a data-eligibility result, not a v8 quality result.
- Regression test pins the A/B/C `cov` values and A `dislope` and rejects an all-1.0 table. v8
  stays unregistered; no brief or default changes.
- Targeted: 40/0/0/0; full offline suite local run + CI.
- NOTE for the queue branch: its GUI `_cpu_activity` still needs the `--verify-dir` / `*-verify`
  update from PR #44 before that branch merges.

## 2026-11-12 (20:40Z) - FIX: VERIFY OUTPUTS ARE PER BACKEND (PR #44)

- `verify --backend X` used to write every backend into `<run>/verify/`; a CPU verify overwrote the GPU
  verify's `designs/<hash>/response.npz` / `metrics.json` and mixed the ndjson, making A.7 lane parity
  unmeasurable (the D.3 handoff caution). Defaults were unchanged, but the override path had no backend
  dimension.
- Fix: `verify --verify-dir PATH`; a `--backend` override that differs from the run's recorded
  `run.json.backend` gets its own run dir (mirroring `--brief`) with `verify_of.backend`; an explicit dir
  refuses rows from another backend. Same-backend verify still writes `<run>/verify/` exactly as before.
- Tests: `tests/test_cli_verify_designs.py` 9/0/0/0 (4 new); all `tests/test_cli_*.py` 26/0/0/0; local
  full suite 2814 passed / 1 failed / 2 skipped on the pre-merge head. The failure is
  `tests/test_mesh_build.py::test_too_large_is_refused_before_any_mesh_is_written`, a load-sensitive
  100 ms timing assertion (208.9 ms under two concurrent suites; passes in isolation; CI green) -- not a
  code regression and not weakened.
- Tonight's already-running `c2b`/`g1c` loaded the old code; their per-backend responses were recovered
  read-only from `cache_cpu/solve/<key>` + `cache/solve/<key>` and A.7 on the reconstructed pair is
  **PASS** (5/5 designs within 0.2 dB; max 0.0356 dB, |dJ| <= 3.4e-5). No re-solve.
- Note for `day/2026-11-12-queue`: its local GUI `_cpu_activity` reads `<run>/verify/search.ndjson`; when
  that branch merges it must also read `--verify-dir` / a `*-verify` run's `run.json.verify_of`.
## 2026-11-12 (23:5xZ) - GUI FINISHING PASS: WP9/WP10 MERGE + STEP 2 FIXES + WP7 + LIVE ACCEPTANCE (feat/gui-integration)

- Merged `feat/gui-charts-history` (WP9 chart standards C1-C15 + WP10 search history H1-H10) into
  `feat/gui-integration` (`9a45d5e`); kept both sides in `app.js`/`app.css`/docs as the handoff
  required. Full `-k gui` suite green (exit 0) and `node --check` clean after the merge.
- Step 2 defect fixes (all verified live on port 8799 vs the real runs tree, read-only):
  - `verify.js` table gate pills carry âœ“/âœ— (pass/fail in tooltip), not colour-only.
  - Verify header shows `report.name` + brief + band. **Root cause fixed in `data_verify.py`:
    `config.yaml` was read with `_read_json` (YAML â‰  JSON â†’ `{}`), so name/band were null.** `brief`
    added to the `verify_report` payload from the run config.
  - Cut charts use 30Â° ticks (`angleTicks` in `charts.js`; âˆ’90/âˆ’60/âˆ’30/0/30/60/90), not Â±50.
  - `fidelity.screen.dof_range` == verify range on `â€¦ed1da9` investigated and **legitimate**:
    `n_dof` is a mesh property (all 5 screen rows 2006â€“2380); screen DOF is read from the screen
    `response.npz`, verify DOF from the verify design dir â€” same mesh, same dof.
  - Verify-mode run pages omit every search-history panel (WP4 item 5) via a single `runIsVerify`
    branch in `viewRunDetail`; Verification card and gate audit stay.
  - WP7 "Verify selected": `cli.py` already had `--designs/--designs-file`; `gui/jobs.py` `kind==verify`
    now accepts `designs` (comma string or list, CLI-mirrored shape validation, mutual exclusivity
    with `top`) and `designs_file` (+24 new tests, `tests/test_gui_jobs_verify_designs.py`); the Verify
    view gained `renderVerifySelected` (hash checklist, select-all, POST `{kind:"verify",args:{run,designs}}`).
    GPU-busy disabling verified against the live GPU lock (button disabled + title/hint while the real
    search runs).
- **Owner decision applied:** Home "Best horn per brief" window 14 â†’ 31 days (`HOME_RECENT_DAYS`,
  boundary tests for 30/32 days in `test_gui_shell_ux.py`).
- **Merge regression caught during acceptance:** the WP10 search-dynamics block in `app.js` used
  `logTicks` without importing it (`logTicks is not defined` on run detail); import added.
- Live acceptance: `docs/GUI_VERIFY_ACCEPTANCE_2026-11-12.md` â€” Appendix B items 1â€“16 pass with
  measured evidence (Home 1.2 s; runs-verify filter 16 rows / 7 parent links / 9 standalone;
  ed1da9 verification card numbers; elites warm 2.51 s; launch 2.03 s; compare filter; both themes,
  900/1400 px; screenshots in `docs/images/gui-acceptance-2026-11-12/`).
- **Visual audit (same day, before push):** a full-page screenshot pass over run detail + verify view
  found five render defects, all fixed and re-verified live:
  - per-parameter Ïƒ heat strip was invisible (opacity encoding sent small normalised Ïƒ to ~0 alpha;
    data was present â€” all 9 params) â†’ replaced with real bars + label margin/ellipsis, minâ€“max band,
    shared x-axis (`data.py` keeps positional nulls now);
  - circular polar overflowed its card (Â±60/Â±90 labels cut or outside, "on axis" collided with "0Â°")
    â†’ container-sized square viewBox + single `0Â° Â· on-axis` annotation;
  - verify design table clipped at GATES (900 px) / pills overlapped DOF-TRIS (1400 px) â†’
    horizontal-scroll wrappers + column min-widths + nowrap;
  - gate-audit table clipped at 900 px â†’ same scroll treatment;
  - convergence footer claimed "0 failed (0%)" while 62 failures existed â†’ honesty fix: footer now
    counts null/invalid rows over the full resumed history ("139 evals ok, 62 failed (30.8%) Â· 72
    above axis range"), matching the KPI strip; â–² strip moved to the bottom per the caption.
  New/updated tests: `test_gui_run_identity.py`, `test_gui_verify_panel.py`,
  `test_gui_visual_audit_fixes.py` (new). Known cosmetic (ISSUES): light-theme balloon/polar
  faintness, scatter label crowding, DI/On-axis single-card H+V series.
- Tests: `tests/test_gui_chart_standards.py` (angleTicks), `tests/test_gui_verify_data.py`
  (name/band/brief regression), `tests/test_gui_verify_panel.py` (WP7 helpers), 
  `tests/test_gui_jobs_verify_designs.py` (24), `tests/test_gui_shell_ux.py` + `tests/test_gui_brief_authoring.py`
  (verify-run panel hiding + 31-day window). Full `-k gui` suite green (exit 0) after all changes;
  `node --check` clean on app.js/verify.js/charts.js/balloon.js/evolution.js.
- Known cosmetic: default `/favicon.ico` 404 (no favicon declared) â€” one console error per session.

## 2026-11-12 (22:10Z) - GUI VERIFY VIEW FRONT END (WP3 + WP6, feat/gui-verify-ui)

- Implemented WP3 (verify table view) and WP6 (per-design panel) in `hornlab_search/gui/static/verify.js`.
  Pure helpers exported: `parseVerifyQuery`, `buildVerifyQuery`, `deltaCellHtml`, `sortRows`,
  `fidelityPillsHtml`, `summaryHtml`, `emptyStateHtml`, `standaloneHeaderHtml`, `nearestFreqIndex`,
  `bandDeltaStats`, `checklistHtml`, `polarPlot`, `viewVerify`.
- Added optional `tier` argument to `viewBalloon` and inner `loadDesign` fetch in `balloon.js`
  (backward-compatible default `"screen"`).
- Appended `/* verify view */` CSS block to `hornlab_search/gui/static/app.css` (KPI strip,
  fidelity pills, table rows, delta text colours, panel, gates card, checklist, compare selector).
- New tests: `tests/test_gui_verify_table.py` (20 tests, WP3 pure helpers) and
  `tests/test_gui_verify_panel.py` (17 tests, WP6 pure helpers + node --check). All 37 green.
- Full `-k gui` suite: **362 passed, 0 failed**.
- Did NOT edit: `app.js`, `charts.js`, `data.py`, `data_verify.py`, `server.py`, `index.html`
  (other-agent-owned). `polarPlot` lives in `verify.js` as directed; `charts.js` untouched.

## 2026-11-12 (WP9/WP10) â€” CHART STANDARDS + SEARCH HISTORY

- **WP9 (C1â€“C15) chart standards** applied across run detail, campaign, and compare views:
  - `charts.js`: `logGrid()` (C1 minor freq gridlines), `AXES` constants (C2/C3/C4), `fixedRange()`,
    `polarPlot()` export (C12), `refLines` dotted style (C5), `markers` at solved frequencies (C7),
    `unscored` hatch (C10), over-range band in `isobarMap` (C8), freq ticks in isobar (C9),
    `ylog` parameter added for H5 sigma/axis-ratio charts.
  - `app.js` acoustic chart block replaced: H/V BW small multiples (C6), fixed ranges, C13 off-axis family,
    shared show-start toggle, C14 impedance y < 0 allowed, C15 hover crosshair via existing code.
- **WP10 (H1â€“H9/H10) search history** implemented:
  - `data.py`: `cma_dynamics()` reads `cma/fit.dat`, `stddev.dat`, `axlen.dat`; `has_atlas` added to `run_detail`.
  - Convergence (H1â€“H4): out-of-range â–² markers, failure Ã— strip, IQR band + median line per gen,
    resume vertical lines from `run.json.history`.
  - Search dynamics card (H5): sigma/axis-ratio on log-y, per-param Ïƒ heat strip.
  - Sensitivity bounds bar (H6): loâ€“hi track with best-value marker, top-6 spread band.
  - QD atlas link conditional (H7): only shown when `d.has_atlas`.
  - Evolution 3D already hidden by default (H8) â€” verified correct.
  - Score breakdown sorted by best contribution, weight shown next to each term (H9).
  - Campaign BW/DI charts updated to use `fixedRange(AXES.*)` and `refLines`/`markers`.
  - Cross-run convergence history per family (H10): lazy-loads run data, plots best-so-far curves.
  - `app.css`: appended `/* charts */` block for new element classes.
- **Tests**: `tests/test_gui_chart_standards.py` (8 tests) + `tests/test_gui_search_history.py` (16 tests).
- **All GUI tests green**: 349 passed.

## 2026-11-12 (20:20Z) - GUI VERIFY / HIGH-RES VIEW PLAN (DESIGN PASS, PLAN ONLY)

- Wrote `docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md` (design pass: designer lane + Boundary Lab research lane,
  reconciled). Plan only; no GUI code changed.
- Decision: **primary = a Verify sub-view inside run detail** (`#/run/<id>/verify`, entered from a persistent
  Verification card), **verify runs as first-class rows / second-class pages** (fidelity badge + parent link,
  redirect to the parent Verify view), optional "Verified only" filter; no new top-level nav item.
- Surfaces: (A) Verify view with KPIs (screen bias, worse-on-verify, screen-#1->verify rank, top-5 overlap,
  rank agreement), a screen-vs-verify scatter, and a verify-J-ranked table with delta + gates + density;
  (B) per-design high-res panel with one Hz-labelled frequency scrubber driving 3D balloon (dB-radius blob,
  white 6 dB isobars, guides), H/V polar cuts with a screen ghost, isobar map, and on-axis/DI/ripple/beamwidth
  curves with a screen ghost; (C) compare-two-verified with per-frequency deltas.
- Grounding corrected during the pass: GUI `run_detail`/leaderboards are screen-centric today (verify precedence
  exists only in gate audit/campaign grouping) -> the view builds the screen<->verify pairing explicitly (same
  rule as `tools/analysis/fidelity.py`); verify has two layouts (inline `<run>/verify/` without run.json; separate
  `auto_*__verify` runs with `verify_of`); default shortlist is top 5; frequency counts vary per brief.
- Boundary Lab v0.5.0 research folded in: borrow isobars->balloon->curves grouping, Hz frequency slider with k/N,
  explicit A/B state (never hidden gestures), quality/density honesty, print at full stored resolution; reject
  floating windows, turbo-only encoding, implying BL-class density.
- Slices 1-6 scoped (data/API foundation; entry points/identity; table/summary; per-design panel; compare-two;
  optional verify-selected), each with headless tests; risks listed (inline vs separate, absolute `verify_of`
  paths, cross-grid comparability, gate-audit keying, response overwrite, export ranking gap).
- Bookkeeping: ISSUES + INDEX updated in the same commit.

## 2026-11-12 (19:45Z) - DAY GROUP G: OBJECTIVE V8 PROPOSAL (OFFLINE ONLY, OWNER-GATED)

- Day-plan group G (PR #43, branch `day/G-objective-v8`): `hornlab_search/objective/scalar_v8.py`
  PROPOSAL scorer â€” every weighted term in its own **linear** unit (RMS deg for cov/diag, RMS dB for
  rip/di/flat/distd, dB/decade for dislope) divided by per-class tolerances calibrated from the stored
  dataset (median raw value of the top decile, A.9 method); loading/f11/round-throat become **hard
  refusals**, not weights. **NOT registered**: `objective/versions.py` still dispatches 1-7, no brief
  uses v8, no default changed. Owner sign-off required before any use (day-plan section 5).
- `tools/analysis/v8_rescore.py`: offline re-score (read-only dataset shards via
  `gate_audit.parse_stored_row`) of v4/v6/v7 vs v8 with calibrated tolerances + hard-refusal gates;
  per-class Kendall tau + top-20 overlap; JSON+MD to `--out`.
- [measured] Re-score on 400 stored valid rows (dataset snapshot): tau v8 vs v4 0.683 / v6 0.792 /
  v7 0.668; top-20 overlap 13/20, 11/20, 12/20; 0 v8 hard-refusal rows in the scored set.
  Interpretation: v8 is a re-weighting of the same physics, not a new landscape â€” different top-20
  shortlists, so an A/B night (>=5 seeds per class) must precede any brief switch.
- `docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md`: one-page owner brief (recipe, calibrated
  tolerances with provenance, re-score table, risks, explicit sign-off gate).
- Verified: 39 targeted tests green (39/0/0/0); no GPU/solver; dataset read-only.

## 2026-11-12 (19:25Z) - TEST-SUITE EFFICIENCY REVIEW (SENIOR PASS, PROPOSAL ONLY)

- Wrote `docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md` (senior research pass, owner-gated):
  measured the testing burden and proposed low-risk reductions **without removing any coverage**.
- [measured] Local offline suite 2706 tests / 588.3 s (~10 min); CI test step 352.8 s (~5.9 min,
  ~8 min end-to-end); today 122 CI runs (85 push + 37 PR) = 824 run-minutes; 24 tests >=5 s carry
  51% of suite time (unmarked export/STEP/GUI-preview/bassbox/report/campaign integration tests).
- Root causes ranked: dual `push`+`pull_request` triggers (2 runs/commit), no pip cache, docs-only
  commits re-running the full suite (push rule + merge-time docs commits), orchestrator full-suite
  per branch duplicating CI, unmarked heavy integration tests, and branch protection off (a red
  merge cost two fix PRs today).
- Proposals R1-R8: single trigger (+main), pip cache, docs-only fast CI lane (keeps
  gen_param_catalog --check + param-catalog tests), `slow`-mark the measured heavy tests with a
  nightly lane, CI-as-merge-gate protocol, required checks, optional xdist, and the GPU
  smoke-vs-full-checkpoint ladder (GPU tests are NOT the CI cost; only 4 marked tests, all skipped
  in CI). Expected: ~5-6x less CI time, ~2-3x less local waiting at equal coverage. **No change
  was applied** â€” owner decides; the doc carries exact diffs.
- ISSUES/INDEX/NOTES_FOR_SENIOR updated in the same commit per the push rule.

## 2026-11-12 (18:15Z) - DAY GROUP E: GUI ANALYSIS PAGE, LANES PANEL, ELITES CATALOG

- Day-plan group E (PR #36, branch `day/E-gui`): E.1 `#/analysis` read-only page renders the Group A
  analysis outputs under a configurable folder (default `runs/analysis/`, new
  `hornlab-search gui --analysis-dir` flag; `/api/analysis` + `/api/analysis/<set>` pass each
  `<tool>.json` through verbatim: convergence curves, seed-variance table + A-beats-B/indicative
  verdict chips, sensitivity bars + top-decile shift + surrogate importance, link candidates, walls,
  REPORT.md text; missing sections render "not present"; never runs an analysis). It codes against
  `tools/analysis/schema.md` (A.0) and ignores unknown fields.
- E.2 home lanes panel backed by new `GET /api/lanes` (`gui/data.py::lane_status`, a local duplicate
  of the D.1 read logic â€” never imports `tools/`): per-lane lock holders (alive/stale), the running
  job from the newest queue log, run-dir row count + newest-row age, last completed job, and an
  ALERT flag when a lane is quiet > 30 min while its job runs; missing files degrade to idle.
- E.3 `#/elites` catalog renders designs from a committed gate-audit CSV (J vN, tier, L2-style gate
  chips â€” only columns the CSV carries, a fail never becomes a pass â€” coverage cell, run link);
  absent audit = empty catalog.
- Verified: targeted GUI helper test green; full offline suite green on the main-synced branch
  (2 stored-data skips); CI green on the branch.

## 2026-11-12 (17:55Z) - DAY GROUP B: SEARCH FEATURES (ALL OPT-IN)

- Day-plan group B (PR #40, branch `day/B-search-features`): B.1 `search.warm_start` (new
  `search/warmstart.py`: mean/sigma0 from prior runs' best valid design + top-k spread; same
  family/knobs, box clip+count; version/brief mismatch ConfigError unless `allow_cross_brief`;
  never changes the solve hash); B.2 `search.links` (new `search/links.py`: linked knobs leave the
  CMA dimension, computed from the parent pre-mesh, clipped; one level; cycles/unknown ConfigError);
  B.3 `hornlab-search narrow --run <dir> [--widen]` (wall analysis in `search/pin_from_cma.py`;
  changes ONLY bounds/seed/name + header; >50%-walled knobs reported as PIN CANDIDATE);
  B.4 `search.budget_counts: valid` + `search.max_attempts` (refusals free, hard attempts cap,
  both counts in run.json + summary; pycma fitness-range stops suppressed only in valid mode);
  B.5 brief `gates: {round_throat: true}` opts any single-entry objective version into the C4
  refusal (v7 stays always-on); B.6 `search.infeasible_penalty: resample` (refusal replaced by a
  fresh ask, cap 10/slot, never told; cma_me + resample is a ConfigError â€” ribs Scheduler.tell
  cannot drop solutions); B.7 `search.surrogate: lq` (pycma SurrogatePopulation / fmin_lq_surr2
  style, seeded from prior rows on resume); B.8 `search.qd.maes` (CMA-MAE soft archive,
  learning_rate 0.01-0.1, threshold_min=-j_threshold, ranker `imp`, no emitter bounds);
  B.9 PARAMETERS.md hand-maintained section per new key.
- Defaults unchanged: the 78ed1f4 goldens (default config_sha + first 5 CMA asks for
  `examples/osse_baseline.yaml` seed 1234) stayed green after every feature; plain configs produce
  bit-identical run.json schemas.
- Verified: 97 targeted day-B tests green (97/0/0/0 junitxml); CI green on the branch.
- NOTES_FOR_SENIOR.md appended: PARAMETERS.md is generator-owned for design knobs; the day-B
  search-key section should be folded into `tools/gen_param_catalog.py` (outside group B ownership).
- CI fix in the merge window: the pre-existing `test_config.py` no-None guard flagged the new
  opt-in keys (`search.max_attempts`/`links`/`warm_start`/`surrogate` are None by design when
  absent) â€” added them to `OPTIONAL_FIELDS` per the established convention; no product code changed.
- CI fix 2: the three B.8 CMA-MAE runtime tests now `pytest.importorskip("ribs")` exactly like the
  CMA-ME suite (CI does not install ribs; optional-dep tests skip there and run on this box).

## 2026-11-12 (17:40Z) - DAY GROUP C: CALIBRATION HARNESS + N1 THROUGHPUT EVIDENCE

- Day-plan group C (PR #37, branch `day/C-calibration`): C.1 `tools/calibration/plan_calibration.py`
  (top-N finalists -> 3-6 line `extends:` overlays under `examples/calibration/<date>/` -> runnable
  night YAML in the runner format; default `--top 20`; PROPOSAL-ONLY new-screen-grid overlay,
  not wired into jobs) + C.2 `tools/calibration/compare_calibration.py` (per-aspect max |delta| vs
  Re z +-0.03 / BW +-2 deg / DI +-0.2 dB, Spearman screen-vs-verify, verify-J-only finalist ranking,
  `compare.json` + `COMPARE.md`).
- C.3 `docs/evidence/THROUGHPUT_N1_2026-11-12.md` from the N1 night (read-only `runs/nights/
  gpu_2026-11-12/summary.jsonl` + twelve `n1_*.log`): fused ON wins at every size (4k warm b12
  8.49 vs 12.05 s; 8k fused-off never completes a warm rep), `freq_batch_size` 12 never hurt
  (4.7x/2.1x/1.9x vs b1 at 1k/4k/8k), prefetch neutral on warm time and harmful near the ceiling
  (8k fused-off+prefetch OOM: 188.794 MiB alloc failure at 100.00% (7.996/7.996 GiB), peak 7731 MiB).
  DECIDED recommendation delivered as a proposal only (fused ON; prefetch OFF at >=8k dofs;
  freq_batch_size 12 via `HORNLAB_FREQ_BATCH_SIZE` until a config key exists). No default flipped.
- C.4 (same doc): screen-fidelity proposal (new screen grid: band split 2 kHz, ~7 points in
  2.5-5.5 kHz; measure Spearman(screen, verify) in the calibration night; until then verify top 15-20
  and rank finalists by verify J only).
- Verified: 13 targeted tests green (13/0/0/0); CI green on the branch incl. the Group-A test files.

## 2026-11-12 (17:35Z) - FIX: GROUP-A TEST CLI HELPER USES THE RUNNING INTERPRETER (CI GREEN RESTORED)

- `tests/test_tools_analysis_common.py::run_cli` hardcoded this box's
  `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` as the subprocess interpreter; CI
  (Linux, no such path) got `FileNotFoundError` in ~25 Group-A CLI-invocation tests, so PR #38's merge
  went in with CI red (status checks are not enforced on this repo). Fix: `PY = Path(sys.executable)`
  â€” locally that is the venv python (pytest runs under it), in CI the job's python; tools are pure
  stdlib+numpy/scipy/matplotlib+optional-sklearn so they work under either. No product code changed.
- Follow-up rule for future lanes: never put an absolute machine path in a test; derive the
  interpreter from `sys.executable`.
- Second CI-only failure (same runs): three `test_tools_analysis_sensitivity.py` tests asserted
  `surrogate.available is True`, but sklearn is OPTIONAL by contract (day plan + schema: try/except,
  Spearman fallback) and CI has no sklearn â€” the tool correctly degrades with
  `{'available': False, 'note': 'sklearn not installed; Spearman only'}`. The tests now branch on the
  availability contract (deep assertions keep running wherever sklearn exists); no tool code changed.

## 2026-11-12 (17:10Z) - DAY GROUP A: EVOLUTIONARY-ANALYSIS TOOLKIT COMPLETE

- Day-plan group A (PR #38, branch `day/A-analysis`): A.0-A.10 complete under `tools/analysis/` â€”
  `_common`, `convergence` (A.1), `seed_variance` (A.2 incl. bootstrap CIs + ECDF + >=5-seed verdict rule),
  `sensitivity` (A.3 incl. sklearn surrogate permutation importance; Sobol skipped, SALib not installed),
  `links` (A.4), `walls` (A.5), `ab_compare` (A.6), `lane_parity` (A.7 CP-7b 0.2 dB gate),
  `term_balance` (A.9 per-term share of J + raw-unit top decile â€” the v8 tolerance-recalibration inputs),
  `fidelity` (A.10 screen-vs-verify bias + top-5 rank agreement), `report_day` (A.8) +
  `specs/day_2026-11-12.yaml` (today's lanes with <FILL_*> placeholders the orchestrator fills from
  `runs/nights/{gpu,cpu}_day_2026-11-12/summary.jsonl`). Tools read run dirs read-only and write only `--out`.
- Verified: 75 targeted Group-A tests green (75/0/0/0 junitxml); full offline suite green on the branch
  (2 stored-data skips); schema.md is the output contract and stayed stable.
- GUI group E codes against this schema (PR #36 landed already).

## 2026-11-12 (16:25Z) - DAY GROUP D: NIGHT/DATA OPS HARDENING

- Day-plan group D (PR #35, branch `day/D-night-ops`): D.1 two-lane `night_status.py` (per-lane lock
  holders alive/stale, the running job per lane from the queue logs, its run-dir row count and
  newest-row age, ALERT when a lane is quiet > 30 min while its job runs); D.2 runner robustness
  (GPU-busy job -> `status: blocked` + exactly one retry after 120 s, `lane`/`backend`/`status`/
  `attempts` on every summary row incl. command jobs, `--dry-run` validates EVERY argv path,
  explicit stale-lock takeover log); D.3 `tools/data/merge_lane_dataset.py` (parity-gated on the A.7
  report, dry-run by default, `provenance.lane: "cpu"` tags, backup + atomic writes, idempotent);
  D.4 `tools/night_report.py` (per-lane morning report, [measured]/[inferred]).
- Verified: 66 targeted offline tests green (junitxml 66/0/0/0); full offline suite green on the
  branch (2 stored-data skips) at f98f024; live read-only smokes of the two-lane status and the
  night report against the 2026-11-12 day runs (GPU lock holder shown correctly; CPU lock freed).
- D.3 parity-schema tolerance (documented in PR #35): gate = top-level `pass` bool per the A.7
  schema on `day/A-analysis`; `verdict`/`status`/`result` "pass"/"passed" accepted; unrecognised
  gate = refuse (fail closed).

## 2026-11-12 (16:00Z) - DAY GROUP R: SEARCH-MATH RESEARCH DOSSIER

- Day-plan group R (research continuation, PR #34, branch `day/R-research-dossier`): wrote
  `docs/research/SEARCH_MATH_DOSSIER_2026-11.md` (docs-only, single repo file). Ten sections, owner
  summary, ranked change table. Sources: verified primary-source pack (Hansen GECCO'19 lq-CMA-ES + pycma
  `fitness_models` internals; Nomura et al. AAAI'21 arXiv:2012.06932 WS-CMA-ES â€” plan's "Shibata"
  attribution corrected; Fontaine & Nikolaidis GECCO'23 arXiv:2205.10752 CMA-MAE + pyribs v0.12.1 tutorial;
  IOHprofiler/COCO ECDF refs; SALib given-data methods) + repo file:line spot-checks at tip 2ecbc69 +
  installed pycma 4.5.0 / ribs 0.12.0 venv source (read-only). 16 claims tagged [TO-VERIFY] with exact
  reference-to-check; no fabricated refs.
- [measured] scripts (offline, READ-ONLY over `runs/`, in `C:\Users\hunte\study_2026-11-12\research\`,
  never in the repo): refusal shares over 415 runs / 34,475 ndjson rows = 13.8% total (invalid_geometry
  9.1%, mesh_too_large 2.6%, invalid_envelope 1.7%) â€” consistent with, slightly below, the senior 16%
  (scope differs, both retained); Â§8 power table: detecting delta=10% of the spread needs n=106 (group,
  spread 26%) or 546 (v6 spread 59%) â€” past n=2-10 A/Bs were underpowered.
- Key recommendations feeding B.6-B.8 and G: feasibility resampling before telling J=1000 (16% refusals),
  lq-CMA-ES only after an offline LQModel tau>=0.85 replay test, same-brief warm starts (mean/sigma/shrunk
  C0 + pycma inject), config-only BIPOP for budgets >=300, CMA-MAE on ribs 0.12 (learning_rate 0.01-0.1,
  improvement ranker, NO emitter bounds â€” two confirmed mismatch mechanisms: emitter-bounds resampling
  distortion and refused rows borrowing the seed's cell), objective v8 = linear RMS error units +
  tolerances calibrated from top-decile medians + gates as refusals.
- INDEX.md line added (research section). No code, no GPU, no solver runs; CI green required before merge.

## 2026-11-12 (15:55Z) - DAY GROUP F: DOCS AND ISSUE HYGIENE (F.4 ISSUE #13 CLOSED)

- Day-plan group F (docs lane, PR #33, branch `day/F-docs-hygiene`): `docs/NEXT_DEV_PRIORITIES.md` adds P15
  (the 2026-11-12 day hardening plan, PR #32) and marks P14 lanes L1-L5 DONE with PR numbers
  (#29/#26/#27/#28; #25 still open, merges last today); open owner decisions recorded (loading split v6/v7
  confirmed by PR #27 tau evidence; round-throat default; sysmem setting; HF write access for Collin; printing).
  `docs/SENIOR_PLAN_2026-11-12.md` got a per-WP status column (done / in this plan / open), conservative.
- CONTINUITY order fix produced as `docs/history/continuity_reorder_2026-11-12.patch` (plan F.1 DECIDED):
  reorders entries newest-first and moves the 202 entries dated 2026-10-12..2026-10-31 to
  `docs/history/CONTINUITY_2026-10-22_2026-10-31.md`. Patch verified (`git apply --check` + real apply)
  against pristine origin/main content 2ecbc69. The ORCHESTRATOR applies it LAST today, after all merges
  (CONTINUITY is edited by every merge today).
- F.4 executed by the orchestrator at merge time: GitHub issue #13 closed (comment cites the fixes merged
  2026-10-22: FF to 6d1d5c7 = e0b9b61 + 11304f6 + 152a829; suite 533 PASS); mirrored in `docs/ISSUES.md`.
- Docs-only lane; no pytest applicability; CI green on PR #33.

## 2026-11-12 (15:10Z) - DAY HARDENING PLAN WRITTEN (runs while the GPU + CPU lanes solve)

- `docs/IMPLEMENTATION_PLAN_2026-11-12_DAY.md`: six parallel groups for a delegating orchestrator, file ownership
  disjoint, defaults unchanged, no GPU: A evolutionary-analysis toolkit (answers today's seed/narrow/staged/parity
  experiments), B search features (data warm start, linked knobs, `narrow` subcommand, valid-only budget,
  round-throat brief flag), C calibration harness + n1 throughput evidence, D night/data ops (two-lane status,
  runner robustness, CPU-dataset merge behind parity, auto night report), E GUI (analysis, lanes, elites), F docs.
- State: PRs #24, #26-#31 merged; #25 (line endings) held until the queues finish. Every branch pushed.

## 2026-11-12 (14:30Z) - DAY QUEUE: GPU + CPU LANES LAUNCHED FROM THE COMPUTE STUDY

- Study: `C:/Users/hunte/Hrns/study_2026-11-12/COMPUTE_STUDY.md` (414 runs inventoried, sensitivity, bound walls). Its queue
  was corrected before launch: its "calibration" job called an evidence byte-checker (dropped), seed replicates had no
  `--cma-seed` (fixed), the narrowed config changed six unannounced knobs (rebuilt: only the three bound walls + seed).
- Fixes: `tools/run_staged_search.py` resolves a relative `brief_file` against its source (the 11-12 night's n7 "Stage A
  produced no best.json"); new `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4_narrow.yaml`.
- CPU backend provisioned (`python -m hornlab_beat_bem.provision --backend cpu`, probe solved). Queues
  `runs/nights/gpu_day_2026-11-12.yaml` (10 jobs: CPU/GPU cross-check pair, core_law resume + seed 1031, narrow vs control
  seed 1235, staged A/B, v6 resume + seed 1235, ext-throat and ath_core atlas resumes) and `runs/nights/cpu_day_2026-11-12.yaml`
  (cross-check, v6 seed 1236, hypex elites verify on CPU).

## 2026-11-12 (L1) - LANE L1: CPU SECOND SOLVE LANE WIRED END-TO-END

- **Scope:** lane L1 of the two-lane night architecture, branch `lane/L1-cpu-lane`. All eight L1
  tasks (L1.1-L1.6, L1.8) are complete; L1.7 (GUI, out-of-scope for this branch) stays open.
- **L1.1 â€” lane-scoped host cleanup (`solve/worker.py`):** `clear_stale_hosts` / `recover_after_failure`
  carry a `lane` argument; `host_lane(cmdline)` and `derive_lane()` classify hosts by their `--dir`
  BEAT worker registry arg; unknown-lane hosts logged as "unknown host, left alone" and never killed.
  Three commits prior to this session (03097f7, 9f2c990, d651845).
- **L1.2 â€” hygiene + gpu-clean lane-aware:** `hygiene.py::clear_julia()` has a `lane` argument;
  `cli.py::_cmd_gpu_clean` accepts `--lane` and routes to `lane_lock_path()`. (Also in prior commits.)
- **L1.3 â€” night runner two-lane:** `run_campaign_night.py` updated: no image-name kill anywhere; top-level
  `lane:` key in night YAMLs; `lane_env()` / `build_job_env()` pure helpers set `HORNLAB_BEAT_WORKER_DIR`
  per lane (CPU lane also sets JULIA/BLAS thread caps); per-job `backend:`, `cache_dir:`, `dataset_dir:`,
  `env:` keys plumbed to the CLI; CPU lane holds `runs/.cpu.lane.lock` for the whole night, skips GPU lock
  + nvidia-smi; COMMAND-kind jobs that wrap `hornlab-search search` have their `run_dir`/`evals`/`best_J`
  parsed from log output (same patterns as SEARCH-kind jobs).
- **L1.4 â€” `solve.julia_threads` excluded from solve hash:** `config.py` adds `julia_threads: int | None`
  to `SolveSettings`, validates as positive integer, includes in `optional` to skip the hash; `cma.py` and
  `beat.py` / `worker.py` plumb the value to the BEAT host so warm_up and SolveConfig carry the same count.
- **L1.5 â€” lane + backend fields on `search.ndjson` rows:** `evaluate.py` adds `current_lane()` (reads
  `HORNLAB_BEAT_WORKER_DIR`); `evaluation_to_row()` takes optional `lane` / `backend` and writes them
  additively (omitted outside a lane: pre-two-lane rows stay byte-identical).
- **L1.6 â€” CLAUDE.md + AGENTS.md "Two lanes" paragraph:** both files carry the paragraph describing lane
  identity, the BEAT worker registry dir convention, and the CPU lane lock.
- **L1.8 â€” profile files:** `examples/profiles/objective_v4.yaml`, `objective_v7.yaml`, and `fused_cuda.yaml`
  ship as `extends:` overlay bases. Bug fixed: fused_cuda.yaml had `dof_cap_verify`/`dof_cap_final` under
  `solve:` (causes ConfigError); moved to `mesh:` where `MeshSettings` owns them.
- **Tests [measured]:** offline suite **2537 passed, 2 skipped** (exit 0; targeted L1 tests
  42/42 passed; 2558 collected, 21 deselected by `-m "not gpu and not slow"`).
- **New test files:** `tests/test_config_extends.py`, `tests/test_config_julia_threads.py`,
  `tests/test_night_runner_lanes.py`.


## 2026-11-12 - INTEGRATION: COLLIN'S PR #22, #19, #23, THE CUDA FIX AND THE HARDENED PLAN MERGED; OBJECTIVE v5 COLLISION FIXED
## 2026-11-12 â€” LANE L5: DATA INTEROP WITH THE COLLABORATOR (TWO-WAY)

- **What:** L5 makes the dataset self-describing and two-way. All eight DECIDED tasks complete (L5.1-L5.6, L5.8;
  L5.7 is a post-merge upload step for the owner).
- **L5.1 `hornlab_search/dataset/manifest.py`:** `python -m hornlab_search.dataset.manifest` writes
  `<dataset_root>/MANIFEST.json`: `manifest_version`, `schema_version`, `lab` label (default `hunter-4060`),
  row counts broken down by `objective_version`, `family`, `backend`, `mode`, typology, and the full
  `objective_version Ã— family Ã— backend Ã— mode` grid; per-shard sha256+row count; `created_utc` min/max;
  objective versions legend (1-7 from `objective/versions.py`); the 2026-11-12 "5â†’7 relabel" note. Deterministic
  (sorted keys, sorted lists). `tools/hf_sync.py pack` calls it first so every packed snapshot carries a manifest.
- **L5.2 `tools/export_config.py`:** `--run <dir> --top N` writes `<hash>.mesher.json` (exact dict
  `families.to_mesher_config` returns) + `<hash>.meta.json` (family, params, J, objective_version, terms, brief,
  lib_sha, run_id, config_name). Generator/CAD families listed in `skipped.json` with reason.
- **L5.3 `tools/hf_sync.py`:** `pack` runs manifest first; `push --lab <name>` uploads under `labs/<name>/`;
  `pull --lab <name> --into dataset_ext/<name>`. `HF_HUB_DISABLE_XET=1` for uploads. No real network calls in
  tests (subprocess faked).
- **L5.4 `tools/data/ingest_foreign.py`:** validates pulled rows with `validate_record`, tags `lab`, never writes
  into `dataset/`. Parity report: same `design_hash + mesh_hash + solve spec`, SPL diff from `.npz` arrays. CP-7b
  rule: comparable only after >= 3 shared designs agree within 0.2 dB.
- **L5.5 `tools/export_campaign_tables.py`:** grouped and labelled by `objective_version` and `backend`; never
  ranked across groups. README.md describes the rule.
- **L5.6 `docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md`:** new section "What changed 2026-11-12" covers the v5â†’v7
  relabel, MANIFEST.json, and the labs/ two-way flow with owner actions.
- **L5.8 `tools/data/keepers.py`:** `--backfill --apply --backup <dir>` joins `runs/*/search.ndjson` +
  `runs/*/config.yaml` â†’ `run_id`/`config_name`/`typology` for old records. Dry run by default. Atomic
  os.replace with backup. Tests on a synthetic two-run tree.
- **Tests [measured]:** 35 L5-specific tests + 120 L5+dataset tests pass.
- **Owner actions:** grant Collin HF write access to `chingadalleva/hornlab-search-data` (or agree on his repo);
  ask Collin to `push --lab collin-4090` his Solana/SAWMOD runs; Collin owes Metal-vs-4060 parity check
  (â‰¤ 0.2 dB) before Metal rows join (PR #17). Then run L5.7: `tools/hf_sync.py pack --groups text,dataset` +
  `upload` from the main checkout between GPU jobs.
- **Branch:** `lane/L5-data-interop` â†’ PR to `main`.

## 2026-11-12 - INTEGRATION: COLLIN'S PR #22, #19, #23, THE CUDA FIX AND THE HARDENED PLAN MERGED; OBJECTIVE v5 COLLISION FIXED COLLIN'S PR #22, #19, #23, THE CUDA FIX AND THE HARDENED PLAN MERGED; OBJECTIVE v5 COLLISION FIXED

- **Owner directive:** merge the collaborator's work and everything outstanding into one tested main, pause new MEH
  work, then scoring truth, speed and the GUI. Plan: `docs/SENIOR_PLAN_2026-11-12.md` (P14).
- **Merged into `integ/2026-11-12`** (merge commits, authorship kept): PR #19, `fix/cuda-fused-meh-bench-audit`
  (beat-bem `0850ef3`, fork branch pushed), **PR #22 (Collin: Solana/SAWMOD, `mid_ports`, objective v6, Design
  cloud; mesher pin `jamescollinharky/hornlab-waveguide-mesher@55da4f4`)**, PR #23 (throughput packet, BL A/B),
  `feat/hardened-plan-2026-10-29` (13 commits that were never PR'd).
- **Collision found and fixed:** main's v5 = MEH; the hardened branch's loading/flat_cv/8 kHz/signed-V objective was
  also "5". It is now **v7** (`objective/scalar_v7.py`); its round-throat refusal applies to v7 only (was `>= 5`).
  Nine hardened briefs say `version: 7`. `tools/data/renumber_objective_v5_to_v7.py --apply` relabelled **1,371
  dataset rows** (shards 45-47) and **26 run dirs** (2026-10-29); MEH's 126 v5 rows untouched; backup
  `runs/_backup_renumber_v5_v7/`. The public HF dataset still carries the old labels (plan WP-E4).
- **Pins installed in `.venv`:** mesher `55da4f4` (Collin's fork), beat-bem `0850ef3`.
- **Tests [measured]:** offline suite 2,474 collected, 2,472 passed; the 2 failures were stale version-tuple asserts,
  fixed and rerun green (`runs/integ_2026-11-12/offline2.{log,xml}`); new `tests/test_tools_renumber_objective.py`.
- **Also merged:** `swarm/B` (`verify --designs/--designs-file`) and `swarm/C` (atlas v2 configs). Offline suite at the tip
  **2,481 / 2,481 passed** (`runs/integ_2026-11-12/offline3.xml`).
- **Collaborator audit:** every Collin commit is in (PR #17's 72 symbols present after its squash; PR #22 merged). The
  data path is one-way (his RunPod runs never came back; no dataset MANIFEST; no mesher-config export): handoff lane L5.
- **Night handoff for an OpenCode orchestrator:** `docs/OPENCODE_HANDOFF_2026-11-12.md` - GPU night, CPU second lane
  integrated now (decisions encoded), lanes L1-L5, hourly check-ins with GPU<->CPU failover.
- **OpenCode readiness (2026-11-12):** OpenCode reads `AGENTS.md` (never CLAUDE.md) and skills from `.claude/skills/`. AGENTS.md
  still said `taskkill /F /IM julia.exe` (would have killed the CPU lane): now matches CLAUDE.md rules 1 and 8, plus the
  skills list and current state. Duplicate `.opencode/skills/` copies removed (single source `.claude/skills/`). The
  local, untracked `.opencode/oh-my-opencode-slim.json` grants fixer/designer the hornlab skills (they had `[]`, which
  blocks skill loading). gpu-job and night-queue skills note the two-lane exception after L1.
- **Found for the plan:** the GUI brief editor offers objective versions 1-3 only; three loading definitions (v4, v6,
  v7) need reconciling; CONTINUITY is no longer newest-first after the merges.

## 2026-11-03 (01:31Z) - BENCHMARK: CPU BEATS CUDA AT THE MEH MESH SIZE; 16 kHz RUNS ON CPU

- New `tools/bench/cpu_vs_cuda_meh.py` (15-minute budget, timestamped log + JSON). Measured on the owner's box,
  pin unchanged, 372 s total: `docs/evidence/BENCH_CPU_VS_CUDA_2026-11-03.md`, raw log in
  `runs/bench_cpu_cuda_20261103T013105Z/`.
- **A. CPU does multi-tag solves** (2-tag tetra, 1 kHz, 2.34 s). The MEH path is not CUDA-only.
- **B. Production T2 mesh (8,044 dofs, 2 tags), warm protocol (warm-up call, then the same 2-frequency call twice):**
  CUDA **37.2 s/frequency** (repeats 71.6 / 74.5 s for two frequencies, peak VRAM 7,853 MiB) vs CPU
  **5.86 s/frequency** (repeats 11.6 / 11.7 s). **CPU is 6.4x faster**; max |dSPL| 5.03e-04 dB. This is the same
  documented CUDA cliff: fast at ~6k dofs (the 12-frequency screen measured 3.6 s/frequency at 5,872 dofs), then
  collapse by ~8k.
- **C. 16 kHz on CPU.** The earlier 16 kHz failures were the application's dof cap (8,900), not the mesh or the
  card. With the cap raised for the diagnostic build: 49,757 triangles / **25,171 dofs**, built in 5.0 s, CPU
  solves 1 kHz in **100.7 s**. CUDA static storage for that mesh is **46.9 GiB** (audit formula 24.N.E + 32.N^2),
  so the 8 GB card cannot hold it. Wall caveat stands: at epw 5.4 the driven patches resolve to ~21.8 kHz but the
  rigid walls only to ~10.3 kHz.
- **Implication:** for the MEH's dof regime the CPU backend is the faster engine and needs no VRAM. The
  rent-a-GPU-first conclusion in the hardware audit should be revisited for screens specifically; a CPU screen may
  already be the cheap path, with the GPU reserved for what it actually wins.


## 2026-11-03 (02:00Z) - 40-DESIGN CUDA-vs-CPU SWEEP: NO SINGLE WINNER, CROSSOVER AT BOTH ENDS

- New `tools/bench/cuda_cpu_40designs.py`: **40 stored designs, no CAD/re-meshing** (30 single-source stratified
  across the dof range + 10 multi-entry with tag 10), one identical 1 kHz solve each per backend, hosts cleared
  between arms. Ran 358.6 s. Evidence: `docs/evidence/BENCH_40_DESIGNS_2026-11-03.md`, rows in
  `runs/bench_40designs_20261103T015652Z/`.
- **Result [measured]:** CUDA cold first call 26.5 s vs CPU 2.5 s; warm means 3.54 vs 4.18 s; sums over 40 designs
  164.4 s vs 165.5 s; median CPU/CUDA **2.23x**; CPU won **6/40**; SPL parity max **3.6e-05 dB**; CUDA peak VRAM
  7,841 MiB.
- **The crossover is a shape, not a point.** CPU faster below 1k dofs (0.17-0.22 s vs 0.35-0.72 s) and at
  8,472/8,530 dofs (18.1/18.9 s vs **41.6/53.6 s**); CUDA faster by 1.5-4x from 1k to ~7k dofs. The CUDA cliff is
  located sharply between 6,929 dofs (5.81 s) and 8,472 dofs (41.63 s) - 7x for +22 % dofs - while CPU scales
  smoothly.
- **Implication for screens:** stay on CUDA at 1-7k dofs, move to CPU above ~7k. Physics is backend-independent to
  3.6e-05 dB, so the choice is purely throughput. Caveat: one frequency, one design per dof value, and CPU cost is
  mesh-dependent.


## 2026-11-03 (03:05Z) - FULL-RANGE + THREAD BENCHMARKS: 4x CUDA ON THE SCREEN GRID, NO THREAD GAIN

- **A. Contracted band (41 points, 8,044 dofs, 2 tags)** [measured, `tools/bench/full_range_cuda_cpu.py`]: CUDA
  completed **41/41** at **38.46 s/frequency, 1,577 s total, 7,924 MiB peak** - it does not crash, it is just slow;
  CPU reached 16 frequencies at 18.18 s/frequency and was stopped by the operator (cost, not failure). Parity over
  120-675 Hz: max |dSPL| 2.96e-04 dB, median CPU/CUDA 0.47.
- **B. The grid we actually screen (12 points, 5,872-dof winner mesh, 2 tags)** [measured]: CUDA **25.7 s** for the
  whole sweep (2.05-2.52 s/frequency, 7,796 MiB peak) vs CPU **103.0 s** with the app's one-call-per-grid policy
  (8.59 s/frequency effective) - **CUDA ~4.0x faster**; parity 4.19e-05 dB. The per-frequency-call CPU arm (111.7 s)
  is not the app's policy and is recorded only as a control.
- **C. Julia threads do not help CUDA** [measured, `tools/bench/cuda_threads.py`]: 1 / 8 / 24 threads on the 8,044-dof
  mesh gave warm 42.92 / 48.98 / 44.88 s - speedups 1.00 / **0.88** / **0.96**, i.e. threads make it slightly slower.
  SPL bit-identical. The CUDA path is GPU-bound; `julia_threads` is not a lever. Concurrent solves are also impossible
  on this card (one solve already peaks at 7,924 of 8,188 MiB).
- Tool fix recorded: mesh paths handed to the solver must be absolute (the Julia worker opens them from its own cwd);
  the harness now resolves them.
- Evidence: `docs/evidence/BENCH_FULLRANGE_THREADS_2026-11-03.md`.


## 2026-11-03 (03:40Z) - MEH SEARCHABLE TYPOLOGIES REGISTERED IN THE CATALOG (GUI VISIBILITY)

- `examples/catalog.yaml` gains a new **`meh`** group with the two SEARCHABLE rows:
  `meh_t2a_search` (T2-A, HF1440 + 2 x 6NDL38) and `meh_t1_search` (T1, HF108 + 4 x 4NDF34). The GUI's Typologies
  page reads this file, so the MEH family is now browsable instead of hidden in a folder.
- **The three CAD-authored seeds are deliberately NOT catalogued** (`meh_t2a`, `meh_t2b`, `meh_t1`). The catalog's
  `native` domain requires native knobs, and `multicell_3x3` is its single documented CAD-only exception; adding three
  more CAD-only entries broke `test_every_native_config_seed_and_bound_key_resolves` (expected 10 native configs, got
  13) and `test_all_native_typologies_are_documented_and_non_empty_except_multicell`. Rather than relax those
  invariants for cosmetic listing, the seeds stay documented in `examples/typologies/meh_2026-10-30/` and
  `docs/meh/MEH_QUICKSTART.md`, and the catalog comment records why.
- Regenerated the three derived artifacts as the byte-tests require
  (`tools/gen_param_catalog.py --write`): `gui/static/param-catalog.v1.json`, `docs/reference/PARAMETERS.md`,
  `docs/reference/TYPOLOGIES.md`.
- Focused gate green: `tests/test_param_catalog.py`, `tests/test_design_meh_generator.py`,
  `tests/test_design_generators_lecleach.py`, `tests/test_design_generators_grid_half.py`.

Newest entry first. Every push updates this file and `docs/ISSUES.md` in the same commit.
## 2026-11-03 - CPU-VS-CUDA AUDIT: "CPU 6.4x FASTER" WAS A VRAM SPILL; MULTI-CHANNEL FUSED CUDA FOR THE MEH

- **Finding [measured]:** PR #19's CUDA arm was the four-operator path (fused refused >1 channel), which at 8,044
  dofs needs ~14 GB and pages ~6.9 GB into WDDM shared system memory (per-process `Shared Usage` counter) -
  38.8-43.8 s/freq. `nvidia-smi` cannot see that. The "fresh host" resets were `taskkill /IM julia.exe`, a no-op
  for the worker_host tree. The 40-design bench had CUDA faster on 34/40 (median 2.2x). Full write-up and the
  withdrawn PR #19 conclusion: `docs/evidence/BENCH_AUDIT_2026-11-03.md`.
- **Fork:** beat-bem `hornlab-search/meh-fused-cuda` @ `0850ef3` (on 1efdc6f): fused CUDA accepts multi-channel -
  LHS once, `assemble_burton_miller_rhs_cuda` per extra channel, one LU. Opt-in flag unchanged; single channel
  untouched; VENDORING.md entry. Julia MEH testset CUDA **16/16** (new fused-vs-four-operator per-channel check),
  CPU 7/7. **Pin bumped to `0850ef3`** (pyproject, TOOLCHAIN) - the fork branch must be pushed before this lands.
- **Measured on the T2 mesh:** fused 2-channel **2.66 s/freq, 2.1 GB, 80 MiB shared**; CPU 5.5-6.0 (15.4 right
  after a spill); four-operator 38.8. Channel SPL fused-vs-CPU 4.2e-4 dB max, impedance matrix 3.4e-6 rel.
- **Configs:** all five `examples/typologies/meh_2026-10-30/*.yaml` set `solve.cuda_fused: true` and dof caps
  12,000 (the measured fused safe value). Config hashes change for MEH runs (intended: new solve path).
- **Tooling:** `tools/bench/_bench_common.py` (tree-kill host reset, `GpuMemPeak` with shared-memory spill
  flag); the four bench scripts use it; `cpu_vs_cuda_meh.py --cuda-fused`. CLAUDE.md GPU rule 1 no longer says
  `taskkill /IM julia.exe`; new rule 8 (spill is invisible to nvidia-smi; Prefer No Sysmem Fallback).
- `tests/test_end_to_end_meh.py::test_real_meh_end_to_end_gpu` now passes `cuda_fused` from the config, like
  cli/cma (it hand-built the backend and the fused-path proof correctly refused). Real-GPU run green.
- **Verification [measured]:** full local suite (GPU-marked tests included) **1,850 passed, 0 failed**, exit 0.
- **Owner actions (system settings, not done by an agent):** NVIDIA Control Panel `julia.exe` -> CUDA Sysmem
  Fallback Policy -> Prefer No Sysmem Fallback; move Chrome/Claude/Terminal/rbassist to the iGPU for solve sessions.
## 2026-11-06 - BOUNDARY LAB A/B CHECK: HANDOFF EXPORT, HORNFAB REFERENCE SOLVE, BL IMPORT, COMPARE + REPORT (branch `ccr-80a29f93-dxnmdm`)

- **Status:** new, default-off, additive: `hornlab-search ab-bl export | solve | import | compare | demo --fake`
  (`hornlab_search/compare/`, owner guide `docs/ab/BOUNDARY_LAB_AB.md`). No solver, hash, cache key, record format or default
  changed. Offline only: the build container has no GPU, no Julia, no mesher, no Boundary Lab. **Nothing was run against a real
  Boundary Lab or a real solve.** Owner runs the GPU/friend steps (guide section 3, agent block section 6).
- **What it does:** `export` writes a self-contained handoff folder for one design (run best / rank / hash / config seed): the exact
  Hornfab mesh mirrored to a FULL mesh in metres (`SD1G0` tag 1 rigid, `SD1D1001` tag 2 driven) plus the reduced mesh, a ready
  `.blab.json` (schema 10, symmetry off) and a symmetric alternative (BL `xy`, derived from `sizing.SYMMETRY_PLANE` only), a
  headless request overlay with the exact frequency list (default 1/12 octave from 100 Hz, top capped at what the mesh resolves),
  `handoff.json` (mesh sha256, driven area, observation set-up, conventions) and `FOR_YOUR_FRIEND.md`. `solve` runs the high-res
  reference (existing `solve_spec` + backend; only the frequency list, angle count and balloon size replaced) on the full handoff
  mesh or, with `--symmetric`, on the reduced mesh; GPU lock, VRAM baseline, hosts cleared before and verified gone after.
  `import` reads Boundary Lab GUI text exports, the balloon folder, a headless run folder and generic CSV. `compare` aligns grids
  (copies only), derives on-axis / off-axis family / H and V maps / -6 dB beamwidth / DI (balloon) / balloon difference / phase /
  impedance, per-band max / RMS / median, PASS / WARN / FAIL against tolerances (starting points, not standards; override with
  JSON), a convention checker (6.02 dB, 3.01 dB, 12.04 dB, 60 dB, +-20 dB/decade drive-basis slope, time convention, polarity,
  delay, radius, mirrored angles, H/V swap, frequency-axis scale), and writes `report.html` (charts embedded; matplotlib PNG
  when installed, otherwise built-in SVG / PNG), `summary.json`, `verdict.txt`.
- **Boundary Lab formats: verified vs inferred** (static read of `JWSound/boundary-lab` `15f9a89`, 2026-11-02; details in the
  guide section 1). Verified in source: schema-10 project keys, preference names, frequency grid formula, polar arc geometry,
  Fibonacci balloon count rule, polar / on-axis / balloon export formats, headless run layout and quantity ids, phasor
  `exp(+i w t)`. **Found:** polar exports are normalized to the on-axis sample, balloon and polar exports are clipped to the SPL
  Min/Max preference, and **Normalized Channel Correction (default ON) flattens each channel on axis before export** (the project
  switches it off; the friend must confirm). BL `pyproject` now pins BEAT Engine 0.7.0 (our 2026-10-21 notes said 0.6.0).
  Inferred, unrun: that the GUI opens the generated project untouched, an impedance dock text export, RMS vs peak (3.01 dB).
- **Physics note that shapes the plan:** Hornfab drives unit ACCELERATION, BL 1 m/s VELOCITY: `+20 log10(2 pi f)` dB and a
  conjugate, done once in `compare/hornfab_side.py` and cross-checked against `solve/phasor.py` in tests. **The 8 GB card cannot
  solve a 20 kHz mesh** (`TOOLCHAIN.md` ceilings ~5.5k full / ~8.9k quarter dofs), so "full band" means "up to what the mesh
  resolves"; the export prints that limit and `solve --dry-run` the cost.
- **Tests:** `tests/test_compare_ab_{model,import,analysis,conventions,report,export,cli}.py` (synthetic data for both sides in the
  real file formats, injected-fault detection, handoff structure, reference solve and `solve` command with a fake backend).
  Full offline suite in the build container: **5 failed, 1977 passed, 245 skipped** (`python -m pytest -q`); the 5 failures are the
  known `test_report_html` / `test_search_cli` ones that need the missing `hornlab_plots` package (identical before this change);
  the 7 new files add 67 passing tests plus 1 skip (the matplotlib chart test is skipped when matplotlib is absent; it passes when
  matplotlib is on the path).
- **Cross-owner files touched** (also in `NOTES_FOR_SENIOR.md`): `hornlab_search/cli.py` (08; one `ab-bl` subparser + dispatch),
  new package `hornlab_search/compare/` (unassigned, orchestrator to assign), `docs/INDEX.md`, `docs/CODE_MAP.md`.
- **Owner next:** guide section 3 (`demo --fake`, `export`, `solve --dry-run`, `solve --symmetric`, send `bl_handoff`, drop results,
  `compare`). The friend's decisions are listed in the guide section 4.

## 2026-11-04 - THROUGHPUT PACKET: OPT-IN PROFILING, PREFETCH, BATCH KNOB, CURVATURE MESHING, BENCH TOOLS (branch `ccr-80a29f93-dxnmdm`)

- **Status:** all new behaviour is OPT-IN; defaults, numbers, frequencies, cache keys / hashes of default configs and
  record formats are unchanged. Nothing GPU-side was run (the build container has no GPU, no Julia, no solver fork, no
  mesher). Offline suite: new tests pass; the 5 `test_report_html` / `test_search_cli` report failures in that container
  are the missing `hornlab_plots` package (they failed identically before any change). Owner runs the GPU steps:
  `docs/throughput/RUNBOOK.md`.
- **WP0:** `hornlab_search/profiling.py` stage timer (`HORNLAB_STAGE_TIMING=1` -> `designs/<hash>/stage_timing.ndjson`,
  wired in `search/evaluate.py` around mesh / solve / metrics / MEH inner optimize / score / cache store / persist; records
  the solver's backend, `assembly_paths`, VRAM from the response). `tools/bench/throughput_matrix.py` (production
  `solve_spec` + `get_backend`, 12/25/36/41 sets, batch arms, cold + warm reps, nvidia-smi poller thread, CSV/JSON, env
  info, parity). Legacy bench scripts: `taskkill /IM julia.exe` replaced by `tools/bench/_hosts.py` (kills only host
  trees the script started; pre-existing hosts are reported, not killed) and an opt-in `HORNLAB_BENCH_FUSED` /
  `HORNLAB_BENCH_SYMMETRY` for the SolveConfig they build directly (default = their old behaviour).
- **WP2:** `search.pipeline_prefetch` (config, default 0) / `HORNLAB_PIPELINE_PREFETCH` (env wins). A one-thread builder
  pre-meshes candidates i+1..i+depth while i solves (`search/pipeline.py`, `mesh/prefetch.py`); `mesh/build.build_mesh`
  takes a parked mesh first (keyed by mesh cache key + output dir + mode). Coordinator remains the only writer of
  ndjson / cache / dataset, evaluates in ask order, `tell` order unchanged; seed first, budget, cache hits, failures,
  interrupts unchanged (offline tests with fake delays prove identical rows/order and real overlap). CMA and CMA-ME wired
  (CMA-ME test needs `ribs`, skipped here). **Unverified on the real machine:** whether the real gmsh mesher accepts
  running off the main thread; if not the prefetcher disables itself with one warning and the run continues serially.
- **WP5:** `BeatBackend(freq_batch_size=N)` / `HORNLAB_FREQ_BATCH_SIZE` chunks the same ordered frequency list into
  calls of at most N (default None = today's per-frequency CUDA grouping). `throughput_matrix --batch-sizes default,1,2,4,12`.
- **WP4:** `mesh.curvature_npts` (default 0): `MeshSpec.curvature_npts` enters `MeshSpec.hash()` only when non-zero;
  `mesh/step_build.sizing_options` sets `Mesh.MeshSizeFromCurvature`, clamped `MeshSizeMax` = wavelength ceiling,
  `MeshSizeMin` = source size; CAD route only. `tools/bench/mesh_policy_study.py` (N/E, edge stats, build seconds, optional `--solve`).
- **WP3:** `tools/bench/cpu_gpu_concurrent.py`: separate lane processes, own `HORNLAB_BEAT_WORKER_DIR`, no `worker.*`
  global kills, own-tree cleanup, start barrier, serial-vs-concurrent parity, aggregate candidates/h. Bench only; real
  behaviour unmeasured.
- **WP1:** `docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md` (Julia proposal, checklist, A/B, rollback), UNVERIFIED
  against source lines, not applied.
- **Owner runbook:** `docs/throughput/RUNBOOK.md`. Cross-owner files touched are listed in `NOTES_FOR_SENIOR.md`.

## 2026-11-02 - P11 TURNED ON: PUBLIC HF DATASET REPO PUBLISHED FOR THE COLLABORATOR

- **Owner directive:** set up Hugging Face storage so the GitHub collaborator can pull "the solves we've done".
  Owner chose **public** (collaborator needs no HF account/token) and the **core groups** `text,solve,dataset`.
- **Live:** <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> â€” public dataset repo, created
  with `hf repos create ... --repo-type dataset --public`, 7 tar shards + `.gitattributes`, **11.56 GB /
  10.76 GiB** (11,556,730,880 B), **197,581 source files**, packed 2026-11-02 ~20:53 local from this worktree
  at `task/hardware-decision-2026-11-01`. Remote sizes verified byte-identical to the local tars
  (`text-000` 731,473,920 B; `solve-000..002` 2.03 GB each, `solve-003` 8,550,400 B; `dataset-000` 2.04 GB,
  `dataset-001` 1.95 GB). Seven per-shard commits (`bfbe708`, `75cf749`, `50aa0b1`, `fbcc6e4`, `42611f3`,
  `d51b17d`, `701f568`).
- **Safety gate before packing [measured]:** julia host PID 17056 idle (CPU 954.859 -> unchanged over 8 min),
  VRAM 706 MiB of 8188, newest `runs/` write 20:44 vs pack start 20:53, so no GPU night was writing.
- **Collaborator path verified end to end:** anonymous `curl -r 0-2047` on `solve-003.tar` returns **206** with
  2048 bytes (no auth), and `hf download ... --repo-type dataset --include "solve-003.tar" --local-dir .hf_stage`
  + in-place untar reproduced `cache/solve/<key>/{response.npz,status.json}` (32 cache dirs). Instructions live in
  `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 4; P11 marked done.
- **`tools/hf_sync.py` corrected** against huggingface_hub docs checked 2026-11-02: `upload` now runs
  `hf upload <repo> <dir> . --repo-type dataset` (`hf upload-large-folder` is deprecated and absent from the
  2.4.0 CLI reference; `hf_transfer`/`HF_HUB_ENABLE_HF_TRANSFER` are gone in hub v1), `pull` filters
  `--include "*.tar"`. Local CLI/hub is 1.17.0 with `hf_xet` 1.5.0.
- **Measured network finding [owner machine]:** the **Xet upload path stalls here** â€” two `hf upload` runs held
  0.1-1.2 MB/s with zero commits after 25+ min while the same link measured 8.3 MB/s upstream
  (`speed.cloudflare.com/__up`, 20 MB) and 9.7 MB/s down from `huggingface.co`; `HF_HUB_DISABLE_XET=1` then
  pushed 2.04 GB in 3.4 min. Uploads from this box must set `HF_HUB_DISABLE_XET=1`. Downloads were unaffected.
- **Not uploaded:** `cache/mesh/**` + `runs/**/*.msh` (16.81 GB) â€” pack with `--groups meshes` if the collaborator
  needs stored meshes rather than rebuilding them with the CPU mesher. Anything written after 20:53 local needs
  a re-pack.
- **Collaborator runbook added:** `docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md` â€” agent-executable
  (clone â†’ `hf download` â†’ verify sha256 per shard â†’ extract in place â†’ verify counts 124,681 / 48,817 /
  24,083 â†’ load one `response.npz`), plus the offline re-score entry points, a troubleshooting table and the
  rules for an agent working in the checkout (never commit the data, never touch `.venv`, no GPU solves, push
  rule). Linked from `docs/INDEX.md`, `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 4 and P11.
- **Shipped as PR #20 into `main`** (`task/p11-hf-sync`, cherry-picked off `origin/main` so the PR carries
  only this work, not the 47 unrelated commits on `task/hardware-decision-2026-11-01`). Files: `tools/hf_sync.py`,
  the new runbook, `docs/HANDOFF_COLLABORATOR_2026-10-27.md`, `docs/NEXT_DEV_PRIORITIES.md`, `docs/INDEX.md`,
  this entry and the `docs/ISSUES.md` note. No solves, configs, pins, tolerances or tests touched.
- **Process note:** two docs were briefly damaged by a PowerShell `Get-Content -Raw | Set-Content` round-trip
  (PS 5.1 re-encoded UTF-8 as ANSI, mangling em dashes and quotes) and were restored from git and re-edited with
  a UTF-8-safe editor before the commit; the committed diff contains no replacement characters.


## 2026-11-05 - CI fix: native param catalog for mid_ports + Solana/SAWMOD natives

- PR #22 CI failed `tests/test_param_catalog.py` (4): `OSSE.mid_ports` missing from
  `NATIVE_KNOBS`; hard-coded "10 natives" broke after Solana/SAWMOD YAMLs; CAD-only
  `sawmod_meh_lr2` / `solana_meh*` empty-knob gate; stale `param-catalog.v1.json`.
- **Fix:** document `mid_ports` (not_a_knob); core-native floor + CAD-only set in the
  test; regenerate catalog / PARAMETERS / TYPOLOGIES.

## 2026-11-05 - Objective v6 (loading_smooth) for Le ClÃ©ac'h / rollback

- **Why:** CD-shaped v4 remapping (`dislope:0`, `load:0.5`) kept the wrong math â€” band-mean
  `load` was ~2 % of J; coverage still punished natural narrowing. JMLC fc is a loading corner;
  pattern control starts ~1.5â€“1.8Ã—fc; DI rises smoothly (ETF 2010 / LANE_A).
- **Landed:** `objective.version: 6` â€” `load_near`, `z_smooth`, `cov_pat`, `di_rise`, plus
  `flat`/`rip`/`distd`/`diag`. Module `hornlab_search/objective/scalar_v6.py`; dispatch in
  `versions.py` / `evaluate.py` / `config.py`. Design `g_fc_hz` stamped into metrics for
  `f_pattern`. Dossier `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`.
- **Briefs:** `examples/briefs/campaign_2026-10-26_v6/native_lecleach_1200_1in_v6.yaml`,
  `examples/briefs/lecleach_rollback_1in_v6.yaml` (v4 briefs untouched; J not comparable).
- **Tests:** `tests/test_objective_v6.py` â€” 14 offline pins green (constant-Z load_nearâ‰ˆ0,
  sinusoidal z_smoothâ†‘, DI+5 dB/dec â†’ di_riseâ‰ˆ0, cov errors below f_pattern ignored).
- **Re-score [measured]:** campaign `docs/data/campaign_v4_2026-10-27/evals.csv` lecleach cells
  (no `z_throat` in export â†’ `load_near`/`z_smooth` take NAN fill). On available pattern terms,
  seed shares are live â€” e.g. `native__lecleach_rollback` n=209: di_rise rawâ‰ˆ9.1 (slope ~8 vs
  target +5), cov_pat rawâ‰ˆ7.0; `b1t__lecleach_iwata_ar` n=198: di_rise 36 % / cov_pat 6 % of
  pattern-term J. Full load-dominance check needs records with throat impedance.

## 2026-11-03 - PR: feat/solana-sawmod-wg-bench â†’ main

- Opening PR for Solana/SAWMOD bench path, mid_ports mesher pin, RunPod cloud tooling,
  UMAP evidence HTML, and GUI **Design cloud** (`/api/umap`, `#/run/<id>/umap`).
- Keele CMA-100 synced locally (`20261104T021231Z-screen-4347f5`, best J=13.17); sample
  PCA on 34 OK designs (not shipped as a code change).

## 2026-11-03 - Design cloud (UMAP/PCA) in the local GUI

- **Landed:** `GET /api/umap/<run>?method=auto|umap|pca` (`data.run_umap_cloud`), run page
  button **Design cloud** â†’ `#/run/<id>/umap` (`static/umap.js`). PCA always (numpy); UMAP when
  `umap-learn` is installed. Color by param unit quartiles or total J; click for full param table.
  Cached in `runs/.gui_cache/`. Offline `tests/test_gui_umap.py`.

## 2026-11-03 - UMAP HTML: full param table + safer embed

- **Fix:** `UMAP_SOLANA_OSSE_MEH_SF_CMA1000.html` now embeds data as `window.UMAP_DATA`,
  populates all 18 searchable knobs in the dropdown, and shows a side panel with every
  physical + unit value on point click (not just the active color channel).

## 2026-11-03 - Interactive UMAP of solana_osse_meh_sf CMA-1000 (GitHub-viewable)

- **Artifact:** `docs/evidence/UMAP_SOLANA_OSSE_MEH_SF_CMA1000.html` (+ `.md`) â€” standalone
  D3 page of OK designs from run `20261103T053926Z-screen-8b32a1`, color by parameter
  unit quartiles or total-J bands; click for values. Open via htmlpreview link in the
  evidence md (GitHub file view is source-only).
- **Method note:** UMAP on unit-box searchable knobs (not per-term loss); subsample of OK evals.

## 2026-11-03 - Ath OSSE+SF mid_ports mesher fork + solana_osse_meh_sf

- **Mesher fork:** `jamescollinharky/hornlab-waveguide-mesher` branch
  `hornlab-search/osse-midports` @ `55da4f46d662d8dcd7a9f94a609eeea4009fcd62`
  (base `b922e807`). Opt-in top-level `mid_ports` re-tags inner-wall triangles to
  tag 10 (flush L1 exits); absent = byte-identical. Pinned in `pyproject.toml` +
  `TOOLCHAIN.md`; `docs/FORKS.md` updated. Mac checkout:
  `~/Desktop/projects/forks/hornlab-waveguide-mesher`.
- **Search wiring:** `families.to_mesher_config` emits `mid_ports` for OSSE when
  present; `mesh/build.py` requires tag 10 and echoes `midPorts` into
  `mesh_meta.json`. Offline tests `tests/test_design_mid_ports.py` +
  `tests/test_mesh_mid_ports.py`; `test_mesh_pin` / doctor pinned-shas green.
- **Config:** `examples/typologies/solana_osse_meh_sf.yaml` â€” Ath SF seed (same as
  `solana_osse_sf_search`) + `mid_ports` tblr + brief `solana_meh_1in_90x90`.
  Shape-check [measured] Mac+4090: ~2900 dofs / 14000, mouth 450Ã—450, depth 152,
  round coupling. Flat CAD MEH (`solana_meh*`) remains the fallback; Ath+SF+MEH
  is now the Solana MEH-context estimate path.
- **MEH evaluate:** OSSE mid_ports path supplies port area via
  `mesh_meta.json["mid_ports"]` (`_meh_layout`); CAD `derived` still preferred when present.
- **4090 [measured]:** screen `20261103T052310Z-screen-ce9d4f` seed **J=39.604** (2921 dofs,
  solve 38.5 s). CMA `20261103T052647Z-screen-cd22a5` live on pod `kt44oly5cdlaps` â€” early
  best **Jâ‰ˆ22.3** (was 39.6); Mac GUI pull-loop syncs that run into local `runs/`.

## 2026-11-02 (evening) - Solana/SAWMOD bench + RunPod cloud path landed on branch

- **Branch:** `feat/solana-sawmod-wg-bench` rebased onto `origin/main` @ `0fb7d98` (PR #21
  hardware decision). WIP stashed â†’ FF â†’ restored; INDEX/ISSUES conflict merge kept main +
  Solana/SAWMOD/cloud rows.
- **Cloud GPU path:** `tools/cloud/` (`runpod_ctl.py`, `bootstrap_linux.sh`, `run_job.sh`,
  `runpod_env.example`) + `docs/CLOUD_GPU_RUNBOOK.md`. Secrets stay local (`.env.local`
  gitignored). POSIX BEAT orphan cleanup: bare `julia â€¦ solver.jl --worker` hosts now
  match in `solve/worker.py` (not only Windows `julialauncher*`); test in
  `tests/test_solve_worker.py`.
- **RunPod [measured]:** RTX 4090 pod bootstrapped; CP-9a selftest deltas **0.020 / 0.039 dB**;
  Solana CD screen Jâ‰ˆ41.9 on CUDA; `examples/osse_baseline_4090.yaml` (fused BM, band/dof
  raises for 24 GB) queued for ~200-eval CMA. One GPU at a time; hosts cleared via
  `run_job.sh`.
- **Solana:** phase-1 Ath WG (`solana_osse` + brief) + evidence; phase-2 MEH CAD seed
  `solana_meh` / `solana_meh_search` + brief `solana_meh_1in_90x90` from DIY Guide Rev 2.0
  (DH450 + 4Ã—6NDL38, face 450 mm vs DIY 410 disclosed). Mouth probes under
  `examples/typologies/_solana_mouth_probes/` (athscript / morph_fixed_0 / gcurve_off â€”
  SF mouth ~450 vs morph-only ~356).
- **SAWMOD:** control WG + knuckle + `walls: lr` MEH probe; CAD/`step_build` accept `lr`.
- **Still owed:** stop/finish live OSSE search as needed; Solana CD mouth-matched
  (`gcurve_off`) screen+verify on 4090; Ath midports MEH path; SAWMOD Ath knuckle+ports /
  LF / BL refine.

## 2026-11-02 - P11 TURNED ON: PUBLIC HF DATASET REPO PUBLISHED FOR THE COLLABORATOR

- **Owner directive:** set up Hugging Face storage so the GitHub collaborator can pull "the solves we've done".
  Owner chose **public** (collaborator needs no HF account/token) and the **core groups** `text,solve,dataset`.
- **Live:** <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> â€” public dataset repo, created
  with `hf repos create ... --repo-type dataset --public`, 7 tar shards + `.gitattributes`, **11.56 GB /
  10.76 GiB** (11,556,730,880 B), **197,581 source files**, packed 2026-11-02 ~20:53 local from this worktree
  at `task/hardware-decision-2026-11-01`. Remote sizes verified byte-identical to the local tars
  (`text-000` 731,473,920 B; `solve-000..002` 2.03 GB each, `solve-003` 8,550,400 B; `dataset-000` 2.04 GB,
  `dataset-001` 1.95 GB). Seven per-shard commits (`bfbe708`, `75cf749`, `50aa0b1`, `fbcc6e4`, `42611f3`,
  `d51b17d`, `701f568`).
- **Safety gate before packing [measured]:** julia host PID 17056 idle (CPU 954.859 -> unchanged over 8 min),
  VRAM 706 MiB of 8188, newest `runs/` write 20:44 vs pack start 20:53, so no GPU night was writing.
- **Collaborator path verified end to end:** anonymous `curl -r 0-2047` on `solve-003.tar` returns **206** with
  2048 bytes (no auth), and `hf download ... --repo-type dataset --include "solve-003.tar" --local-dir .hf_stage`
  + in-place untar reproduced `cache/solve/<key>/{response.npz,status.json}` (32 cache dirs). Instructions live in
  `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 4; P11 marked done.
- **`tools/hf_sync.py` corrected** against huggingface_hub docs checked 2026-11-02: `upload` now runs
  `hf upload <repo> <dir> . --repo-type dataset` (`hf upload-large-folder` is deprecated and absent from the
  2.4.0 CLI reference; `hf_transfer`/`HF_HUB_ENABLE_HF_TRANSFER` are gone in hub v1), `pull` filters
  `--include "*.tar"`. Local CLI/hub is 1.17.0 with `hf_xet` 1.5.0.
- **Measured network finding [owner machine]:** the **Xet upload path stalls here** â€” two `hf upload` runs held
  0.1-1.2 MB/s with zero commits after 25+ min while the same link measured 8.3 MB/s upstream
  (`speed.cloudflare.com/__up`, 20 MB) and 9.7 MB/s down from `huggingface.co`; `HF_HUB_DISABLE_XET=1` then
  pushed 2.04 GB in 3.4 min. Uploads from this box must set `HF_HUB_DISABLE_XET=1`. Downloads were unaffected.
- **Not uploaded:** `cache/mesh/**` + `runs/**/*.msh` (16.81 GB) â€” pack with `--groups meshes` if the collaborator
  needs stored meshes rather than rebuilding them with the CPU mesher. Anything written after 20:53 local needs
  a re-pack.
- **Collaborator runbook added:** `docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md` â€” agent-executable
  (clone â†’ `hf download` â†’ verify sha256 per shard â†’ extract in place â†’ verify counts 124,681 / 48,817 /
  24,083 â†’ load one `response.npz`), plus the offline re-score entry points, a troubleshooting table and the
  rules for an agent working in the checkout (never commit the data, never touch `.venv`, no GPU solves, push
  rule). Linked from `docs/INDEX.md`, `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 4 and P11.
- **Shipped as PR #20 into `main`** (`task/p11-hf-sync`, cherry-picked off `origin/main` so the PR carries
  only this work, not the 47 unrelated commits on `task/hardware-decision-2026-11-01`). Files: `tools/hf_sync.py`,
  the new runbook, `docs/HANDOFF_COLLABORATOR_2026-10-27.md`, `docs/NEXT_DEV_PRIORITIES.md`, `docs/INDEX.md`,
  this entry and the `docs/ISSUES.md` note. No solves, configs, pins, tolerances or tests touched.
- **Process note:** two docs were briefly damaged by a PowerShell `Get-Content -Raw | Set-Content` round-trip
  (PS 5.1 re-encoded UTF-8 as ANSI, mangling em dashes and quotes) and were restored from git and re-edited with
  a UTF-8-safe editor before the commit; the committed diff contains no replacement characters.


## 2026-11-02 - Cloud GPU runner (RunPod-first tooling)

- Added `tools/cloud/`: `runpod_ctl.py` (GraphQL create/status/ssh/stop/terminate),
  `bootstrap_linux.sh`, `run_job.sh` (force-clear BEAT hosts â†’ CLI with explicit
  `--backend beat_cuda` â†’ `shutdown(verify=True)` â†’ `runs/cloud_job_*.json`),
  `runpod_env.example`. Secrets stay out of git (`.env.local` gitignored).
- Runbook: `docs/CLOUD_GPU_RUNBOOK.md` (CP-9a gates, Solana screen first, ~$50 pilot
  suggestion). Research still in `CLOUD_GPU_REPORT.md`.
- POSIX worker hygiene: `beat_host_roots` now finds orphaned bare `julia â€¦ solver.jl
  --worker` hosts (Linux/macOS), not only Windows `julialauncher*`. Test added in
  `tests/test_solve_worker.py`. Offline worker tests green.
- Superseded same evening: first paid 4090 pod ran CP-9a + Solana screen (see evening
  entry above).

## 2026-11-01 (late afternoon) - Solana 2.0 WG reconstruction (phase 1) + SAWMOD phase-2 probes

- **Solana:** DIY Guide Rev 2.0 + `Advanced/athscript.cfg` snapshotted under
  `docs/research/typologies/solana_2026-11-01/` (Drive guide `1-JxZ-â€¦`, files
  `151N2rq4â€¦`). Dossier `SOLANA_WAVEGUIDE_2026-11-01.md`. Config `solana_osse` +
  brief `solana_control_1in_90x90` (verbatim Ath pins: L=140, SF m=8, morph 353Ã—353).
- Dry-run **4284 dofs**; mouth with SF **~450 mm** vs Ath morph 353 / STL outer ~376
  (morph-only ~356 â€” mesher/Ath delta disclosed). Screen Metal:
  `runs/20261101T211314Z-screen-72f3bd` â€” **J=41.9**, 27.9 s, `di_source=balloon`.
  Evidence `docs/evidence/SOLANA_WG_2026-11-01.md`. Phase 2+: mid ports / MEH / mouth delta.
- **SAWMOD phase-2 probes (same session):** knuckle CD-only
  `sawmod_knuckle_osse` (SF digitized) Metal `20261101T210541Z-screen-3c1938` J=241 /
  2948 dofs; flat-wall MEH `sawmod_meh_lr2` (`walls: lr`, cone 103/66, hp_hz 250) dry-run
  3950 dofs + multi-source Metal `20261101T210635Z-screen-ab4075` J=21.5 (v5; `n_nan=12`,
  `load=100`, z_throat null â€” provisional). beat-bem bumped to pin `1efdc6f` for MEH path.
  CAD `tools/cad/meh.py` + `step_build` accept `walls: lr`. LF/BL still later.

## 2026-11-01 (afternoon) - SAWMOD control-waveguide benchmark (phase 1)

- Whitepaper snapshot + dossier: `docs/research/typologies/sawmod_2026-11-01/`,
  `SAWMOD_CONTROL_WAVEGUIDE_2026-11-01.md`. Config `sawmod_control_osse` + brief
  `sawmod_control_1in_100x70` (pinned OS-SE L=115, morph rate 4, no knuckles).
- Mesh: L=115 mm, mouth after morph **280Ã—196** mm (`morph_allow_shrinkage: 1` required;
  raw OSSE ~395 mm). Screen Metal solve OK: **1464 dofs**, J=345.2, 5.4 s â€”
  `runs/20261101T205918Z-screen-e7b5a2`. Evidence
  `docs/evidence/SAWMOD_CONTROL_WG_2026-11-01.md` (freestanding vs paper baffle caveat).
- Phase 2+ still owed: knuckles, mid ports, LF slot, BL SAWMOD refine.

## 2026-11-01 (10:20 EDT) - PACKAGED FOR HANDOFF: QUICKSTART, SCREEN LAUNCHER, BOTH VERIFIED WINNERS

- **`docs/meh/MEH_QUICKSTART.md`**: install (pinned stack, `doctor`), the CI gate, a no-GPU `run --dry-run`, the
  screen + verify commands, what is already done, and the six traps that cost this pass time (8 GB band ceiling,
  non-comparable frequency grids, stale solver hosts producing misleading errors, LF-only repo, `fill` not carried in
  the record, quarter-only CAD).
- **`tools/meh/run_screen.ps1`**: one-brief launcher - clears stray solver hosts, runs the CMA screen, finds the run
  directory, re-solves the top N at verify fidelity, and writes `runs/nights/meh_<tag>_*.log` plus a summary line.
  Parameterised by tag/config/budget/mode; replaces the session-local `scratch/meh/*.ps1` helpers, which are
  gitignored.
- **`docs/evidence/meh_2026-11-01/`**: the two verified winners as JSON (geometry knobs, objective terms, the
  inner-network solution, the CAD layout, channel tags, library SHAs) plus a README that states the numbers and the
  caveats. Extracted from the dataset records, not retyped: T2 `ed11d2cd3acc` (screen 9.530 / verify 11.894, HF1440 +
  6NDL38, XO 651.8 Hz LR4, +0.312 ms, 4.21 L rear) and T1 `704051ae928c` (13.228 / 14.512, HF108 + 4NDF34,
  XO 1000.2 Hz LR4, +1.430 ms inverted, 0.81 L rear).
- Purpose: the next session (owner's friend or an agent) can reproduce and extend the MEH work without rebuilding the
  launchers, re-running the screens, or hunting for the winners.

## 2026-11-01 (09:40 EDT) - CI FIX ON THE PR: OPTIONAL SOLVER DEP GATED IN THE NEW TEST

- PR #18's first CI run failed at **collection**, not in a test: `tests/test_solve_worker_restart.py` imported
  `hornlab_beat_bem` at module scope, and CI does not install that package (main's 546926d deliberately gated
  optional-dependency tests). The import is now `pytest.importorskip(...)`, matching the repo's existing pattern, so
  the file skips cleanly where the solver is absent and still runs on the owner's box.
- Nothing else in the failure list was ours: the run stopped at that one collection error (3 skips, 21 deselected).
  The merge itself is already on `meh/integration` (`08f04bf`) and the focused gate over every touched area passed
  (config, solve/adapter, GUI sandbox, param catalog, all MEH/objective/bassbox tests: exit 0).

## 2026-11-01 (09:05 EDT) - MERGED origin/main INTO meh/integration: LF NORMALIZED, LOGS UNIONED

- `origin/main` had moved (46 files: the staged-search A/B work, Metal device support in `solve/beat.py`, a
  `load_config(backend=...)` override, and the same ridgeCache test fix we made independently).
- **Line endings:** main is LF; this branch had CRLF in 16 MEH-touched files, which turned every shared file into a
  whole-file conflict and would have broken the byte-identical param-catalog test on Linux CI. All 16 are now LF
  (a9720d2), so the merge is semantic rather than 100 whole-file rewrites.
- **Conflicts resolved:** `CONTINUITY` and `NOTES_FOR_SENIOR` are unions (nothing dropped: 11 main entries and one main
  block added); `tests/test_gui_sandbox_page.py` keeps this branch's version (identical assertion); `config.py` and
  `beat.py` auto-merged cleanly once the EOLs matched, so main's Metal support and this branch's freq_grid/recycling
  changes coexist.

## 2026-11-01 - HARDWARE DECISION STUDY: RENTAL FIRST; FULL-WALL MESH IS MUCH LARGER

- Owner clarified this is a theoretical rent-versus-buy decision; no rental machines configured. Rental spend $0, no new BEM solves/screens. `docs/evidence/HARDWARE_2026-11-01.md` records the study, current published rates and explicitly conditional costs.
- Four CPU-only diagnostic builds on the fixed T2 seed: EPW 4.2 => 8,625 dofs / 16,909 triangles, global valid-to 6,015 Hz; EPW 6 => 17,211 / 33,938, global 8,583 Hz; EPW 8.4 => **33,959 / 67,245, global 12,009 Hz, valid**; EPW 9 => 38,819 / 76,919, global 12,864 Hz, valid. This is validator sizing, not acoustic convergence or a proven minimum over all geometries. Shipped configs untouched.
- Source audit of unchanged pin `1efdc6f`: standard CUDA uses fixed dense direct solves, repeating LHS/refactorization per channel; CPU/Metal GMRES cost model is not the CUDA route. At N=33,959/E=67,245 the concurrently live operators+identities+LHS alone require **85.410 GiB** before extra workspace. A 24/32 GB card is a coarse-mesh test candidate; the first requested full-wall discrete tier worth testing is H200 141 GB. No fit/runtime claim was measured on it.
- Historical NPZ/NDJSON extraction corrects the handoff's seed/winner attribution: T2 winner is N=5,872/E=11,456 with baseline/peak 513/7,575 MiB; T1 winner N=6,249/E=12,205 with baseline/peak 330/7,840 MiB. Across 69 successful historical screen candidates, assembly is the largest reported engine stage (~2 s/frequency, versus ~0.2 s solve). No 12 kHz throughput inference follows.
- Flat device-use peaks do not prove constant workspace; CUDA 719 does not uniquely establish OOM. Current `vram_41f.csv` differs from the earlier trace described in M8 and has no verified idle baseline. These refine the older capacity diagnosis; the recorded failures and prior screen winners remain unchanged.
- Shared-host multi-GPU work is not a one-line change: evaluator/persistence side effects, global lock, all-host cleanup and worker registry identity need isolation. Two separate single-GPU machines, one brief each, are a simpler future deployment test. All cross-card, unified-memory, lane-scaling and overnight measurements remain open. `doctor`: 11/11 checks passed; evidence excerpts checked against decoded bytes. No production code/pins/tolerances changed.

## 2026-11-01 (08:20 EDT) - WRAP-UP: FULL OFFLINE SUITE GREEN AT THE TIP; PR TO `main` OPENED

- **Final gate [measured]:** `.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -q`
  at `task/hardware-decision-2026-11-01` -> **exit 0**, no failures. This is the first full run since the last config
  edits (epw 4.05 / screen cap 8,200 / `solve.freq_grid` / `worker_restart_every`), so the tip is gated, not just the
  code merges.
- **Contents of the PR:** the complete MEH implementation (M1-M7, M10), the solver fork pin bump to `1efdc6f` with its
  validation evidence, both 40-evaluation screens with their verified top-2 arms (T2 9.530 -> 11.894, T1 13.228 ->
  14.512), the six-line readiness proof with its one FAIL and one PARTIAL stated plainly, the hardware audit and
  hand-off, and the honest record of the three blocks (8 GB band ceiling, CAD quarter-only, Boundary Lab absent).
- PR base `main`, head `meh/integration`, which now carries the hardware branch (fast-forward; the hardware branch is
  a descendant of the integration tip). Background job board: all sessions reconciled, none active.

## 2026-11-01 (07:55 EDT) - HAND-OFF TIDIED: WITHDRAWN VRAM CLAIM REMOVED FROM THE AXES AND UNIFIED-MEMORY SECTIONS

- The s2a corrections block covered s2, but s5 (axes table) and s5b (unified memory) still asserted the withdrawn
  "flat per-frequency workspace" reading as fact. Both now state what is actually established (device use sits within
  ~300 MiB of the ceiling whenever a 12 kHz MEH mesh solves; the pinned CUDA path holds several N x N and N x E
  complex64 operators plus identity caches, ~85 GiB at the first globally valid whole-wall mesh) and point at s2a.
- Removed a duplicated 5-frequency row my earlier table patch had introduced. No measured value changed.

## 2026-11-01 (07:40 EDT) - HARDWARE AUDIT REVIEWED; FOUR OF MY CLAIMS CORRECTED IN THE HAND-OFF

- The fresh-eyes audit (`docs/evidence/HARDWARE_2026-11-01.md`, Codex session) is sound. I reproduced its two
  load-bearing numbers from the stored data: the screen winners are **5,872 / 6,249 dofs** (not the 6,032 / 6,009
  seed meshes I paired with their timings), and the winners' `meta.timings` give **assembly 23.72 s, solve 2.38 s,
  field 0.19 s, total 35.54 s over 12 frequencies** - assembly is ~67 % of engine time, as the audit says.
- **Withdrawn from my hand-off:** the "~12x for 1.44x elements" scaling claim (it divided a FAILED sweep by 41 and
  used cold-start guesses - there is no valid seconds/frequency at 8.6k dofs); the "flat ~7.9 GB workspace" reading
  (`nvidia-smi` total use + CUDA.jl caching is not live working set, and the CSV that backed it was overwritten by a
  later poller run, now 558 samples starting at 5,643 MiB with no idle baseline); the "25-35k elements" full-wall
  guess (the first globally valid T2 mesh is **33,959 dofs / 67,245 triangles**, ~85 GiB static on the pinned CUDA
  path, so 141 GB is the first viable tier); and "lanes are a one-line change" (five concrete surfaces).
- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` now carries a s2a corrections block so the repo does not hold two
  contradictory records. The audit's conclusion stands: rent a short pilot before buying, and the full-wall 12 kHz
  target is much larger than this pass assumed.

## 2026-11-01 (07:05 EDT) - HARDWARE HAND-OFF EXTENDED: UNIFIED MEMORY + THE MEASURED BASELINE

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` gained two things the next agent needs:
  1. **The measured baseline table** with every data point this campaign produced, plus the derived
     per-frequency rates: ~3.6 s/frequency at 6,032 dofs and ~40-53 s/frequency at 8,625 dofs. That is a
     **~12x cost for a 1.44x element increase**, which is not a clean exponent - it is consistent with
     elements-squared assembly PLUS a change of solver path between those sizes. Separating those terms is
     named as the first measurement of the assignment.
  2. **A unified/coherent-memory section** with the configurations worth testing and the reason the test is
     bandwidth, not capacity: the per-frequency working set is a flat ~7.9 GB, so spilling it over a
     PCIe-class link would cost 5-50x, while NVLink-C2C (GH200/GB200) and Apple's shared memory have real
     bandwidth. Table covers GH200/GB200, Apple M3/M4 Max/Ultra (Metal path), MI300A (ROCm), Strix-Halo-class
     APUs as the negative control, and CPU-only. Every non-CUDA option carries a validation task: the pinned
     fork `1efdc6f` is CUDA-validated only, so Metal/ROCm must clear single-tag parity (<= 0.039 dB) and the
     four multi-tag properties before a campaign may use them.

## 2026-11-01 (06:50 EDT) - EVIDENCE DOC AND INDEX CORRECTED TO MATCH THEIR OWN CONTENT

- `docs/evidence/MEH_M8_2026-10-31.md` was still titled "readiness links 1-2 (partial)" although it had grown to the
  six-line readiness proof, both screen pairs with verify arms, the two hard blocks and the band finding. Title
  corrected (with a dated note) and the `docs/INDEX.md` entry rewritten to state the actual verdicts: links 1/2/5/6
  PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks listed. No measured number changed.

## 2026-11-01 (06:40 EDT) - HARDWARE HAND-OFF WRITTEN (next agent: compute configuration)

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` (INDEX updated) is the whole brief for whoever works out what to run
  this on: the solver pipeline end to end, the measured performance table from this campaign, the two bottlenecks
  stated separately (**B1 capacity** - the contracted 41-frequency band needs >= ~8.6k dofs at a 7.9/8.19 GB peak and
  dies; **B2 throughput** - ~45 s per frequency, so ~20-30 h per 40-evaluation brief even with unlimited VRAM), the
  five measurements that turn "which GPU" into candidates-per-hour-per-dollar, the hardware axes worth pricing, and
  the deliverable (`docs/evidence/HARDWARE_2026-11-<date>.md`).
- Key measured fact for sizing: **VRAM is flat at ~7.9 GB from 6,032 to 8,625 dofs**, so the peak is a per-frequency
  workspace, and 24 GB gives ~3x headroom while 48 GB allows a defensible 12 kHz mesh (the current mesh resolves the
  walls only to ~6 kHz). Throughput needs candidate-level parallelism (one GPU per lane), not a bigger card - the
  pipeline is serial per candidate today and `search/evaluate.py` was left a pure function for exactly that change.

## 2026-11-01 (06:10 EDT) - CONTRACTED BAND RELAUNCH STOPPED: the CMA neighbours break the VRAM-safe cap

- The epw 4.05 relaunch was stopped after its first rows. Two distinct failures, both recorded:
  1. One candidate hit `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel` - a **stale fused worker host** from
     the earlier fused probe was adopted by the run (same package fingerprint). The config carries no `cuda_fused`;
     killing hosts before a run is the fix, not a config change.
  2. The real blocker: CMA neighbours need **8,296-8,485 dofs**, over the 8,200 screen cap, so they fail as
     `mesh_too_large`. Raising the cap to admit them puts the mesh back at ~7.7-7.9 GB - the ceiling that killed the
     sweep in the first place.
- **Conclusion [measured]:** on this 8 GB card the contracted 120-12,000 Hz 1/6-octave band has no legal operating
  point. A mesh that resolves 12 kHz on the source patches needs >= ~8,600 dofs (7.9/8.19 GB peak, sweep dies); the
  smallest legal mesh (epw 4.05, 8,044 dofs) leaves the CMA population's larger neighbours over any cap that keeps
  VRAM safe. `cuda_fused`, the documented high-dof path, refuses multi-channel by design.
- **Delivered state is unchanged and valid:** the full MEH implementation (M1-M7, M10), the owner-approved pin bump,
  and the 500-10,000 Hz screens with their verified winners (T2 9.530 -> 11.894, T1 13.228 -> 14.512). The
  contracted-band work (opt-in `solve.freq_grid`, `worker_restart_every`, epw/cap experiments) is committed and the
  offline suite is green; only the run itself is not possible here.



- **`cuda_fused` is NOT an option for the MEH**: `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel`, so the
  fused path can never do a multi-tag solve at any dof count (the queue failed 3 candidates in 90 s; stopped).
- **The 12 kHz source-patch gate sets the mesh floor.** Measured with `run --dry-run`: epw 4.2 -> 8,625 dofs (7.9/8.19 GB
  peak, sweep dies); 3.8 -> entry_mid resolves only 11.28 kHz (refused); 4.0 -> driver 11.93 kHz (refused);
  **4.05 -> 8,044 dofs (T2) / 7,977 (T1), patches valid above 12 kHz, ~15 % less VRAM.** Both configs now dry-run OK
  with the full contracted grid: **41 frequencies, 120-12,000 Hz at 1/6 octave**.
- **Screen relaunched** on that configuration (log `runs/nights/meh_{t2,t1}_screen_120_12k.log`); the estimator says
  853 s / 803 s per candidate, i.e. a multi-hour run per brief - the measured first-candidate time goes in the evidence
  doc. Wall-resolution caveat stands and is now slightly worse: at epw 4.05 the rigid walls resolve to ~5.9 kHz, so
  the top of the band is driven-patch-accurate but wall-coarse.

## 2026-11-01 (05:10 EDT) - CONTRACTED 41-FREQUENCY BAND DOES NOT FIT THE 8 GB CARD (measured twice)

- **Run 1 (plain):** one 41-frequency sweep on the T2-A seed (8,625 dofs) ran 1,851 s and died with
  `CUDA error: unspecified launch failure (code 719)`; VRAM peaked **7,908 of 8,188 MiB** (2 s poller,
  880 samples). The screen queue then failed every candidate the same way, so it was stopped.
- **Run 2 (with the new opt-in worker recycling):** `solve.worker_restart_every: 8` restarts the host every
  8 solved frequencies. The sweep still died (`[worker_exit] ConnectionResetError`) at a **7,897 MiB** peak.
- **Interpretation [measured]:** the ceiling is **per-frequency transient**, not cumulative - the 12-frequency
  500-10,000 Hz screens also peak 7.87-7.92 GB and survive only because they make fewer draws, while 41 draws
  sit close enough to the edge that one crossing kills the sweep. Recycling cannot buy margin it does not have.
- **Committed anyway (green, useful on a larger card):** `worker_restart_every` (validated at load, forwarded
  into the solve `extra` only when set, fake-tested in `tests/test_solve_worker_restart.py`), set to 8 in both
  MEH search configs; full offline suite green.
- **Blocked decision for the owner:** (A) lower the dof cap for the contracted band (about 7,000 dofs gives
  ~35 % VRAM headroom but pushes the wall-resolution floor to ~4.7 kHz); (B) run the contracted band on a
  card with more VRAM; (C) keep the 500-10,000 Hz 12-point screen and record the band gap. The 500-10k
  screens and their verified winners stand; never rank across the two grids.
- **Not yet tried:** `solve.cuda_fused: true` (WP15 fused single-matrix assembler, documented as reaching
  ~20k quarter dofs on this 8 GB card). It is the one remaining way to fit 41 frequencies at 8,625 dofs
  without coarsening the mesh; it changes the solve hash and costs a small numeric difference (M5B parity
  0.020 / 0.039 dB).

## 2026-11-01 (03:45 EDT) - CONTRACTED 120 Hz-12 kHz BAND: OPT-IN solve.freq_grid, SCREEN RELAUNCHED

- **Owner decision:** screen over the contracted 120 Hz-12 kHz band (not the frozen 500-10,000 screen grid).
- **New opt-in `solve.freq_grid: {lo_hz, hi_hz, points_per_octave}`** (config.py). It is read from `cfg.raw`, not a
  new dataclass field, because the existing invariant test forbids a `None` in any `SolveSettings` field; the block
  is validated at load (missing key, lo >= hi, density outside 1..48, unknown key all refuse) and stripped before
  `_build`. Absent = the frozen `FREQ_GRIDS`, so no other config's solve hash moves. `mesh_spec` already takes
  `max(mode_freqs(...))`, so the mesh f_max follows to 12 kHz.
- **Both MEH search configs set it** (`120 -> 12000` at 6 points/octave = **41 frequencies**). `tests/test_config_freq_grid.py`
  (9 tests) pins: absent block = the frozen 12-point grid, present = 41 points at exactly 1/6 octave with f_max 12 kHz,
  the solve hash changes, and six bad blocks refuse. Full offline suite green after the change.
- **Two test repairs on the way** (both mine, both correct additions rather than loosened assertions):
  `tests/test_end_to_end_meh.py` maps a `*_search` config to its CAD-authored sibling's reference row.
- **Contracted-band screen relaunched** (`scratch/meh/run_meh_screen_120_12k.ps1`, logs
  `runs/nights/meh_{t2,t1}_screen_120_12k.log`, summary `meh_screen_120_12k_summary.txt`); the 500-10k run and its
  evidence are untouched. Dry-run at the new grid: 8,625 dofs (cap 9,000), 41 frequencies, tool estimate
  1,420 s/candidate; the measured per-candidate time is recorded when the first evaluations land.

## 2026-11-01 (01:45 EDT) - READINESS LINK 3 MEASURED: PASSIVE-MID NOTCH FOUND, PARTIAL AGAINST +-20 %

- The CD-only BEM sweep cannot show the port notch (an undriven L1 port is a rigid patch), so the check was redone
  properly: dense MULTI-TAG solve on the T2-A seed (10 frequencies 700-1800 Hz, 679.8 s), inner optimiser on that
  response (4.82 s, xo 673.7 Hz, order 2), mid channel muted to -300 dB, then `system_response`.
- **Result [measured]:** on axis, SPL 27.08 dB at 1000 Hz, 26.18 at 1100, 24.93 at 1200, then 34.12 at 1300 - a
  9.19 dB notch whose centre lies between 1200 and 1300 Hz. That is **+18.7 % to +28.6 %** of the 1-D 1010.8 Hz
  prediction, so the +-20 % gate is met only at the very bottom of that interval; the likely centre (~1250 Hz,
  +23.7 %) is outside. **PARTIAL, not a clean pass.** Placing it needs a 25 Hz sweep over 1150-1350 Hz.
- Logs: `runs/meh_m8/readiness3_coupled.log`, `readiness3_verdict.log`; arrays
  `runs/meh_m8/link3_muted_mid.npz`. Evidence doc section 9 row 3 updated.

## 2026-11-01 (01:20 EDT) - READINESS PROOF MEASURED ON THE STORED T2 WINNER: 4 PASS, 1 FAIL, 1 NOT PROVEN

- **Link 1 geometry PASS** (tags 1/2/10, 8,625 nodes, quarter planes; seed repairs slide 10 -> 32; walls resolve to
  ~6.1 kHz at the 12 kHz request). **Link 2 solve PASS** (channel fields + force reciprocity <= 3.2e-4).
- **Link 3 physics sanity NOT PROVEN.** The dense CD-only sweep rises to 1250 Hz then falls monotonically; no notch
  in the +-20 % window around the 1-D 1010.8 Hz. At L1 the entry port is a rigid patch unless the lumped network is
  coupled, so the check needs the network-coupled response with zero mid drive - not run.
- **Link 4 network < 2 s FAILS: 6.58 s.** `optimise_network` did 1,224 CMA evaluations (5.4 ms each) for the shipped
  T2 brief (2 mid drivers x 2 xo orders x 2 polarities x up to 160). Per-evaluation budget is met; the whole-call gate
  is missed 3.3x. Fix is a budget/combo decision, not a solver change. A cache-hit evaluate is 9.31 s wall.
- **Link 5 search moves PASS.** Two 40-evaluation screens; all six knobs moved (T2 spreads: cov_h 13.3 deg, cov_v
  23.9 deg, z_frac 0.329, across 0.388, port_along 9.9 mm, slide 25.4 mm); 38/40 T2 and 31/40 T1 OK, the rest genuine
  `invalid_geometry`; no crash.
- **Link 6 re-score for free PASS.** The stored winner `ed11d2cd3acc` re-scored with `faitalpro_6pr160` and
  `hp_hz 160` without a new solve: J 9.530280 -> 9.727026, `cached True`, both finite.
- **Blocked, recorded:** M8 step 3's quarter-vs-full comparison is impossible today - `tools/cad/meh.py` refuses a
  full model (`quadrants '1234'` -> GeometryInvalidError, quarter open shell only). M8 step 4 needs link 3's coupled
  response. **M9 is blocked:** Boundary Lab is not in this workspace (`forks/` has only beat-bem and the mesher).

## 2026-11-01 (00:45 EDT) - MEH SCREEN DONE: T2 J 9.53 -> 11.89 verified, T1 J 13.23 -> 14.51 verified

- **Two 40-evaluation CMA screens + verify top 2 each, all on the new pin on the owner's GPU** [measured]:
  T2 `runs/20261101T004552Z-screen-427d57` best `ed11d2cd3acc` screen J **9.530** (second `719aeb7a4ff0` 9.550),
  verify **11.894 / 11.804**; T1 `runs/20261101T015657Z-screen-fc1d24` best `704051ae928c` screen J **13.228**
  (second `9b6548cc2a6c` 13.556), verify **14.512 / 14.636**. Details in `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **T2 beats T1 on its own brief's J** (9.53 vs 13.23 screen, 11.89 vs 14.51 verify). `lw_resid` dominates both
  (7.8 / 13.1 of J); `notch` is 0.0 in both, so the listening-window penalty is broad-band. Both winners push the
  driver to the top of the slide range (T2 `slide 35.2`, T1 36.1) and the ports low (`z_frac` 0.09 / 0.26).
- **One T2 verify design failed on a VRAM-ceiling worker reset** (7.9 GB of 8 GB) and the auto re-warm failed; after
  killing the stale BEAT host and confirming 1.36 GB idle, `verify --top 2` gave `2 designs, 0 failed`. The retry is
  recorded in the evidence doc; no tolerance changed.
- **`n_nan 12` in the winning record is not a metric failure:** `on_axis_db` is finite at all 12 frequencies and
  `n_nan_ripple 0`; the 12 NaNs are the synthesis's deliberately-NaN impedance array.
- **Two gaps opened by the screen (ISSUES):** (1) the solved grid was 12 frequencies 500-10,000 Hz, not the brief's
  120-12,000 Hz, so the objective scored `n_in_band 10` and never saw 120-500 Hz or 10-12 kHz; (2) `verify`'s own
  line says the verify mesh equals the screen mesh - only the frequency count and balloon size change, so it is a
  re-score, not a finer mesh.

## 2026-11-01 (later) - CI unblock part 2: optional-dep gates + OS-independent assertions

- Remaining pre-existing red: ~24 tests assumed optional deps that CI does not install
  (`hornlab_mesher`, `hornlab_beat_bem`, `ribs`) and 3 tests only passed on Windows. Now gated with
  the existing `requires_mesher` / `requires_beat` markers (per-test `pytest.importorskip("ribs")`
  for the three QD tests, since no `requires_ribs` marker exists).
- OS fixes, no assertion loosened: `test_cma_files_lists_every_served_pycma_log` writes fixture
  bytes and expects `len(bytes)` (Windows text mode was CRLF-inflating `version.txt` to 5 bytes);
  `test_parse_run_dir_variants_and_best_j` builds `tmp_path` paths instead of `C:/work/...`; the
  sandbox hot-swap pin now matches the shipped `if (curGeo) { ridgeCache.delete(curGeo);
  curGeo.dispose(); }`.
- Local: the 11 affected modules run 248 passed; with the three deps simulated absent, 165 passed /
  41 skipped / 0 failed. No product code changed.

## 2026-11-01 (later) - CI unblock: the preview-shape suite skips when the optional mesher is absent

- main's GitHub Actions run had been red since 2026-10-29 with a **collection error**, not a test
  failure: `tests/test_gui_preview_shape.py` imports `gui.preview`, which raises RuntimeError when
  `hornlab_mesher.preview` is not importable, and CI installs the package with `--no-deps` (the
  mesher pin is deliberately not installed there). One module-level guard now skips only when the
  mesher is absent; a **present** mesher whose pinned preview API changed still fails loudly.
- No product code changed; locally (mesher installed) the file still runs its 12 tests.

## 2026-11-01 - MERGED: PR #17 (Metal, budget hint, staged A/B, CMA covariance + pin plan) + the hardware-neutrality rule

- **Merged:** jamescollinharky's PR #17 (`36c6712`, 4 commits, 32 files, +3135/-40) squashed onto `main`: `beat_metal` backend + Mac path, Hansen `max(150, 100*N)` budget hint (`GET /api/budget-hint`), staged MACRO->SHAPE A/B harness (`tools/run_staged_search.py`), end-of-run `cma_covariance` (`run.json` + `cma/covariance.json` + GUI table), CMA-driven `pin-plan` (CLI + run-detail table), `--restarts-mode` / `--restarts-max` (CLI + Launch/Compose).
- **Docs:** all three conflicts were append-only logs. `CODE_MAP.md` was curated (took the PR's `solve/*` row; kept main's newer `metrics/`, `driver/compression`, `mesh/throat_check` rows that the PR copy would have erased); `CONTINUITY.md` ordered newest-first; `NOTES_FOR_SENIOR.md` unioned chronologically.
- **Two merge defects found by the merged test suite, fixed before landing:** (1) `auto_backend()` probed `hornlab_beat_bem` (spawning `nvidia-smi`) inside `build_argv`, so merely enqueueing a queued resume did hardware I/O and 11 GUI tests failed that pass on main; it is now platform-only - Apple Silicon -> `beat_metal`, otherwise `None`, never a silent CPU swap. (2) `--backend` was applied *after* config validation, so `cuda_fused: true` stayed in `raw` / `SolveSpec.extra` and a Metal override died at the first solve while `run.json.backend` disagreed with the snapshot; `load_config(..., backend=...)` now applies the override before validation and drops `cuda_fused` for non-CUDA backends, so `config_sha`, the snapshot and `run.json.backend` agree.
- **Owner rule (2026-11-01): results must be hardware-neutral.** The endpoint is the same data regardless of the host's solver backend (CUDA / Metal / CPU / Julia). Enforced from now on: no silent backend swapping (backend is explicit, hashed into `SolveSpec`, recorded in `run.json.backend` and dataset provenance); pooling across backends only after a measured parity check; `beat_metal` stays a lab backend until Mac<->4060 <=0.2 dB is measured.
- **Verification:** full offline suite green apart from the same 2 pre-existing environment failures as pristine `main` (`test_mesh_pin` pinned-dist mismatch; `tests/test_gui_sandbox_page.py::test_3d_hot_swap_never_scenes_per_frame`). Optimizer A/B (`osse_baseline`, budget 4, seed 1234): identical `design_hash` sequence (`8443a5763be5`, `c54661892c59`, `16905720dfc2`, `8f7d77bd7bfd`) and identical best params; J differs by <=3.0e-06 while the seed candidate - bit-identical input by construction - alone differs by 2.1e-06, i.e. solver noise, not an optimizer change. `run.json` gains only `cma_covariance` (+ `cma/covariance.json`).
- **Owed:** GPU-box `python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`, then paste COMPARE.md into `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`; Mac<->4060 Metal parity before Metal rows enter any campaign/compare.

## 2026-11-02 - GUI: FREQUENCY-AXIS RANGE FROM THE BRIEF BAND + SCORING-FLOOR f0 MARKER; MEH BENCH SCRIPTS

- **Landed (was uncommitted in this tree):** `charts.js` now clips every plot mark to the domain (the band
  rectangle no longer bleeds into the margins), derives 1/2/5 x decade ticks plus the exact endpoints
  (`logTicks`), takes its axis domain from the brief-band union with honest fallbacks (never a guessed
  range), keeps the isobar raster blank in the band margins (NaN sentinel so marching squares cannot
  extrapolate edge colour), and marks the objective scoring floor `f0` as an edge-aware dashed vertical
  marker drawn after the grid.
- `app.js`: new `freqAxisLimits` (union of the brief band and the solved grid); every run-detail frequency
  chart, the campaign overlay and compare route through it (no hardcoded FT tick list); c-bw and c-di carry
  the `f0` marker; `isobarMap` receives `xlim`/`f0`; `seedDerivationHtml(feas, objective)` names the
  objective actually in play, and the one-argument call keeps the original v3 wording.
- `gui/data.py`: `run_detail` passes the committed `objective` block through additively â€” absent stays absent,
  no shape invention.
- New offline pins `tests/test_gui_freq_range.py` (checks (a)-(d) in its docstring); the two existing pinned
  call-site assertions were updated to the new signature.
- **Verification [measured]:** `python -m compileall -q hornlab_search/gui tools/bench tests/test_gui_freq_range.py`
  -> OK; `.venv\Scripts\python.exe -m pytest tests/test_gui_freq_range.py tests/test_gui_brief_authoring.py
  tests/test_gui_param_tips.py -q` -> **37 passed**.
- `tools/bench/` committed (`cpu_vs_cuda_meh`, `cuda_cpu_40designs`, `cuda_threads`, `full_range_cuda_cpu`):
  the CPU-vs-CUDA MEH benchmark scripts behind the 2026-11-02 bench runs. `__pycache__` stays git-ignored.
- No solver, config, pin or tolerance changes.

## 2026-11-01 - HARDWARE DECISION STUDY: RENTAL FIRST; FULL-WALL MESH IS MUCH LARGER

- Owner clarified this is a theoretical rent-versus-buy decision; no rental machines configured. Rental spend $0, no new BEM solves/screens. `docs/evidence/HARDWARE_2026-11-01.md` records the study, current published rates and explicitly conditional costs.
- Four CPU-only diagnostic builds on the fixed T2 seed: EPW 4.2 => 8,625 dofs / 16,909 triangles, global valid-to 6,015 Hz; EPW 6 => 17,211 / 33,938, global 8,583 Hz; EPW 8.4 => **33,959 / 67,245, global 12,009 Hz, valid**; EPW 9 => 38,819 / 76,919, global 12,864 Hz, valid. This is validator sizing, not acoustic convergence or a proven minimum over all geometries. Shipped configs untouched.
- Source audit of unchanged pin `1efdc6f`: standard CUDA uses fixed dense direct solves, repeating LHS/refactorization per channel; CPU/Metal GMRES cost model is not the CUDA route. At N=33,959/E=67,245 the concurrently live operators+identities+LHS alone require **85.410 GiB** before extra workspace. A 24/32 GB card is a coarse-mesh test candidate; the first requested full-wall discrete tier worth testing is H200 141 GB. No fit/runtime claim was measured on it.
- Historical NPZ/NDJSON extraction corrects the handoff's seed/winner attribution: T2 winner is N=5,872/E=11,456 with baseline/peak 513/7,575 MiB; T1 winner N=6,249/E=12,205 with baseline/peak 330/7,840 MiB. Across 69 successful historical screen candidates, assembly is the largest reported engine stage (~2 s/frequency, versus ~0.2 s solve). No 12 kHz throughput inference follows.
- Flat device-use peaks do not prove constant workspace; CUDA 719 does not uniquely establish OOM. Current `vram_41f.csv` differs from the earlier trace described in M8 and has no verified idle baseline. These refine the older capacity diagnosis; the recorded failures and prior screen winners remain unchanged.
- Shared-host multi-GPU work is not a one-line change: evaluator/persistence side effects, global lock, all-host cleanup and worker registry identity need isolation. Two separate single-GPU machines, one brief each, are a simpler future deployment test. All cross-card, unified-memory, lane-scaling and overnight measurements remain open. `doctor`: 11/11 checks passed; evidence excerpts checked against decoded bytes. No production code/pins/tolerances changed.

## 2026-11-01 (08:20 EDT) - WRAP-UP: FULL OFFLINE SUITE GREEN AT THE TIP; PR TO `main` OPENED

- **Final gate [measured]:** `.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -q`
  at `task/hardware-decision-2026-11-01` -> **exit 0**, no failures. This is the first full run since the last config
  edits (epw 4.05 / screen cap 8,200 / `solve.freq_grid` / `worker_restart_every`), so the tip is gated, not just the
  code merges.
- **Contents of the PR:** the complete MEH implementation (M1-M7, M10), the solver fork pin bump to `1efdc6f` with its
  validation evidence, both 40-evaluation screens with their verified top-2 arms (T2 9.530 -> 11.894, T1 13.228 ->
  14.512), the six-line readiness proof with its one FAIL and one PARTIAL stated plainly, the hardware audit and
  hand-off, and the honest record of the three blocks (8 GB band ceiling, CAD quarter-only, Boundary Lab absent).
- PR base `main`, head `meh/integration`, which now carries the hardware branch (fast-forward; the hardware branch is
  a descendant of the integration tip). Background job board: all sessions reconciled, none active.

## 2026-11-01 (07:55 EDT) - HAND-OFF TIDIED: WITHDRAWN VRAM CLAIM REMOVED FROM THE AXES AND UNIFIED-MEMORY SECTIONS

- The s2a corrections block covered s2, but s5 (axes table) and s5b (unified memory) still asserted the withdrawn
  "flat per-frequency workspace" reading as fact. Both now state what is actually established (device use sits within
  ~300 MiB of the ceiling whenever a 12 kHz MEH mesh solves; the pinned CUDA path holds several N x N and N x E
  complex64 operators plus identity caches, ~85 GiB at the first globally valid whole-wall mesh) and point at s2a.
- Removed a duplicated 5-frequency row my earlier table patch had introduced. No measured value changed.

## 2026-11-01 (07:40 EDT) - HARDWARE AUDIT REVIEWED; FOUR OF MY CLAIMS CORRECTED IN THE HAND-OFF

- The fresh-eyes audit (`docs/evidence/HARDWARE_2026-11-01.md`, Codex session) is sound. I reproduced its two
  load-bearing numbers from the stored data: the screen winners are **5,872 / 6,249 dofs** (not the 6,032 / 6,009
  seed meshes I paired with their timings), and the winners' `meta.timings` give **assembly 23.72 s, solve 2.38 s,
  field 0.19 s, total 35.54 s over 12 frequencies** - assembly is ~67 % of engine time, as the audit says.
- **Withdrawn from my hand-off:** the "~12x for 1.44x elements" scaling claim (it divided a FAILED sweep by 41 and
  used cold-start guesses - there is no valid seconds/frequency at 8.6k dofs); the "flat ~7.9 GB workspace" reading
  (`nvidia-smi` total use + CUDA.jl caching is not live working set, and the CSV that backed it was overwritten by a
  later poller run, now 558 samples starting at 5,643 MiB with no idle baseline); the "25-35k elements" full-wall
  guess (the first globally valid T2 mesh is **33,959 dofs / 67,245 triangles**, ~85 GiB static on the pinned CUDA
  path, so 141 GB is the first viable tier); and "lanes are a one-line change" (five concrete surfaces).
- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` now carries a s2a corrections block so the repo does not hold two
  contradictory records. The audit's conclusion stands: rent a short pilot before buying, and the full-wall 12 kHz
  target is much larger than this pass assumed.

## 2026-11-01 (07:05 EDT) - HARDWARE HAND-OFF EXTENDED: UNIFIED MEMORY + THE MEASURED BASELINE

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` gained two things the next agent needs:
  1. **The measured baseline table** with every data point this campaign produced, plus the derived
     per-frequency rates: ~3.6 s/frequency at 6,032 dofs and ~40-53 s/frequency at 8,625 dofs. That is a
     **~12x cost for a 1.44x element increase**, which is not a clean exponent - it is consistent with
     elements-squared assembly PLUS a change of solver path between those sizes. Separating those terms is
     named as the first measurement of the assignment.
  2. **A unified/coherent-memory section** with the configurations worth testing and the reason the test is
     bandwidth, not capacity: the per-frequency working set is a flat ~7.9 GB, so spilling it over a
     PCIe-class link would cost 5-50x, while NVLink-C2C (GH200/GB200) and Apple's shared memory have real
     bandwidth. Table covers GH200/GB200, Apple M3/M4 Max/Ultra (Metal path), MI300A (ROCm), Strix-Halo-class
     APUs as the negative control, and CPU-only. Every non-CUDA option carries a validation task: the pinned
     fork `1efdc6f` is CUDA-validated only, so Metal/ROCm must clear single-tag parity (<= 0.039 dB) and the
     four multi-tag properties before a campaign may use them.

## 2026-11-01 (06:50 EDT) - EVIDENCE DOC AND INDEX CORRECTED TO MATCH THEIR OWN CONTENT

- `docs/evidence/MEH_M8_2026-10-31.md` was still titled "readiness links 1-2 (partial)" although it had grown to the
  six-line readiness proof, both screen pairs with verify arms, the two hard blocks and the band finding. Title
  corrected (with a dated note) and the `docs/INDEX.md` entry rewritten to state the actual verdicts: links 1/2/5/6
  PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks listed. No measured number changed.

## 2026-11-01 (06:40 EDT) - HARDWARE HAND-OFF WRITTEN (next agent: compute configuration)

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` (INDEX updated) is the whole brief for whoever works out what to run
  this on: the solver pipeline end to end, the measured performance table from this campaign, the two bottlenecks
  stated separately (**B1 capacity** - the contracted 41-frequency band needs >= ~8.6k dofs at a 7.9/8.19 GB peak and
  dies; **B2 throughput** - ~45 s per frequency, so ~20-30 h per 40-evaluation brief even with unlimited VRAM), the
  five measurements that turn "which GPU" into candidates-per-hour-per-dollar, the hardware axes worth pricing, and
  the deliverable (`docs/evidence/HARDWARE_2026-11-<date>.md`).
- Key measured fact for sizing: **VRAM is flat at ~7.9 GB from 6,032 to 8,625 dofs**, so the peak is a per-frequency
  workspace, and 24 GB gives ~3x headroom while 48 GB allows a defensible 12 kHz mesh (the current mesh resolves the
  walls only to ~6 kHz). Throughput needs candidate-level parallelism (one GPU per lane), not a bigger card - the
  pipeline is serial per candidate today and `search/evaluate.py` was left a pure function for exactly that change.

## 2026-11-01 (06:10 EDT) - CONTRACTED BAND RELAUNCH STOPPED: the CMA neighbours break the VRAM-safe cap

- The epw 4.05 relaunch was stopped after its first rows. Two distinct failures, both recorded:
  1. One candidate hit `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel` - a **stale fused worker host** from
     the earlier fused probe was adopted by the run (same package fingerprint). The config carries no `cuda_fused`;
     killing hosts before a run is the fix, not a config change.
  2. The real blocker: CMA neighbours need **8,296-8,485 dofs**, over the 8,200 screen cap, so they fail as
     `mesh_too_large`. Raising the cap to admit them puts the mesh back at ~7.7-7.9 GB - the ceiling that killed the
     sweep in the first place.
- **Conclusion [measured]:** on this 8 GB card the contracted 120-12,000 Hz 1/6-octave band has no legal operating
  point. A mesh that resolves 12 kHz on the source patches needs >= ~8,600 dofs (7.9/8.19 GB peak, sweep dies); the
  smallest legal mesh (epw 4.05, 8,044 dofs) leaves the CMA population's larger neighbours over any cap that keeps
  VRAM safe. `cuda_fused`, the documented high-dof path, refuses multi-channel by design.
- **Delivered state is unchanged and valid:** the full MEH implementation (M1-M7, M10), the owner-approved pin bump,
  and the 500-10,000 Hz screens with their verified winners (T2 9.530 -> 11.894, T1 13.228 -> 14.512). The
  contracted-band work (opt-in `solve.freq_grid`, `worker_restart_every`, epw/cap experiments) is committed and the
  offline suite is green; only the run itself is not possible here.



- **`cuda_fused` is NOT an option for the MEH**: `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel`, so the
  fused path can never do a multi-tag solve at any dof count (the queue failed 3 candidates in 90 s; stopped).
- **The 12 kHz source-patch gate sets the mesh floor.** Measured with `run --dry-run`: epw 4.2 -> 8,625 dofs (7.9/8.19 GB
  peak, sweep dies); 3.8 -> entry_mid resolves only 11.28 kHz (refused); 4.0 -> driver 11.93 kHz (refused);
  **4.05 -> 8,044 dofs (T2) / 7,977 (T1), patches valid above 12 kHz, ~15 % less VRAM.** Both configs now dry-run OK
  with the full contracted grid: **41 frequencies, 120-12,000 Hz at 1/6 octave**.
- **Screen relaunched** on that configuration (log `runs/nights/meh_{t2,t1}_screen_120_12k.log`); the estimator says
  853 s / 803 s per candidate, i.e. a multi-hour run per brief - the measured first-candidate time goes in the evidence
  doc. Wall-resolution caveat stands and is now slightly worse: at epw 4.05 the rigid walls resolve to ~5.9 kHz, so
  the top of the band is driven-patch-accurate but wall-coarse.

## 2026-11-01 (05:10 EDT) - CONTRACTED 41-FREQUENCY BAND DOES NOT FIT THE 8 GB CARD (measured twice)

- **Run 1 (plain):** one 41-frequency sweep on the T2-A seed (8,625 dofs) ran 1,851 s and died with
  `CUDA error: unspecified launch failure (code 719)`; VRAM peaked **7,908 of 8,188 MiB** (2 s poller,
  880 samples). The screen queue then failed every candidate the same way, so it was stopped.
- **Run 2 (with the new opt-in worker recycling):** `solve.worker_restart_every: 8` restarts the host every
  8 solved frequencies. The sweep still died (`[worker_exit] ConnectionResetError`) at a **7,897 MiB** peak.
- **Interpretation [measured]:** the ceiling is **per-frequency transient**, not cumulative - the 12-frequency
  500-10,000 Hz screens also peak 7.87-7.92 GB and survive only because they make fewer draws, while 41 draws
  sit close enough to the edge that one crossing kills the sweep. Recycling cannot buy margin it does not have.
- **Committed anyway (green, useful on a larger card):** `worker_restart_every` (validated at load, forwarded
  into the solve `extra` only when set, fake-tested in `tests/test_solve_worker_restart.py`), set to 8 in both
  MEH search configs; full offline suite green.
- **Blocked decision for the owner:** (A) lower the dof cap for the contracted band (about 7,000 dofs gives
  ~35 % VRAM headroom but pushes the wall-resolution floor to ~4.7 kHz); (B) run the contracted band on a
  card with more VRAM; (C) keep the 500-10,000 Hz 12-point screen and record the band gap. The 500-10k
  screens and their verified winners stand; never rank across the two grids.
- **Not yet tried:** `solve.cuda_fused: true` (WP15 fused single-matrix assembler, documented as reaching
  ~20k quarter dofs on this 8 GB card). It is the one remaining way to fit 41 frequencies at 8,625 dofs
  without coarsening the mesh; it changes the solve hash and costs a small numeric difference (M5B parity
  0.020 / 0.039 dB).

## 2026-11-01 (03:45 EDT) - CONTRACTED 120 Hz-12 kHz BAND: OPT-IN solve.freq_grid, SCREEN RELAUNCHED

- **Owner decision:** screen over the contracted 120 Hz-12 kHz band (not the frozen 500-10,000 screen grid).
- **New opt-in `solve.freq_grid: {lo_hz, hi_hz, points_per_octave}`** (config.py). It is read from `cfg.raw`, not a
  new dataclass field, because the existing invariant test forbids a `None` in any `SolveSettings` field; the block
  is validated at load (missing key, lo >= hi, density outside 1..48, unknown key all refuse) and stripped before
  `_build`. Absent = the frozen `FREQ_GRIDS`, so no other config's solve hash moves. `mesh_spec` already takes
  `max(mode_freqs(...))`, so the mesh f_max follows to 12 kHz.
- **Both MEH search configs set it** (`120 -> 12000` at 6 points/octave = **41 frequencies**). `tests/test_config_freq_grid.py`
  (9 tests) pins: absent block = the frozen 12-point grid, present = 41 points at exactly 1/6 octave with f_max 12 kHz,
  the solve hash changes, and six bad blocks refuse. Full offline suite green after the change.
- **Two test repairs on the way** (both mine, both correct additions rather than loosened assertions):
  `tests/test_end_to_end_meh.py` maps a `*_search` config to its CAD-authored sibling's reference row.
- **Contracted-band screen relaunched** (`scratch/meh/run_meh_screen_120_12k.ps1`, logs
  `runs/nights/meh_{t2,t1}_screen_120_12k.log`, summary `meh_screen_120_12k_summary.txt`); the 500-10k run and its
  evidence are untouched. Dry-run at the new grid: 8,625 dofs (cap 9,000), 41 frequencies, tool estimate
  1,420 s/candidate; the measured per-candidate time is recorded when the first evaluations land.

## 2026-11-01 (01:45 EDT) - READINESS LINK 3 MEASURED: PASSIVE-MID NOTCH FOUND, PARTIAL AGAINST +-20 %

- The CD-only BEM sweep cannot show the port notch (an undriven L1 port is a rigid patch), so the check was redone
  properly: dense MULTI-TAG solve on the T2-A seed (10 frequencies 700-1800 Hz, 679.8 s), inner optimiser on that
  response (4.82 s, xo 673.7 Hz, order 2), mid channel muted to -300 dB, then `system_response`.
- **Result [measured]:** on axis, SPL 27.08 dB at 1000 Hz, 26.18 at 1100, 24.93 at 1200, then 34.12 at 1300 - a
  9.19 dB notch whose centre lies between 1200 and 1300 Hz. That is **+18.7 % to +28.6 %** of the 1-D 1010.8 Hz
  prediction, so the +-20 % gate is met only at the very bottom of that interval; the likely centre (~1250 Hz,
  +23.7 %) is outside. **PARTIAL, not a clean pass.** Placing it needs a 25 Hz sweep over 1150-1350 Hz.
- Logs: `runs/meh_m8/readiness3_coupled.log`, `readiness3_verdict.log`; arrays
  `runs/meh_m8/link3_muted_mid.npz`. Evidence doc section 9 row 3 updated.

## 2026-11-01 (01:20 EDT) - READINESS PROOF MEASURED ON THE STORED T2 WINNER: 4 PASS, 1 FAIL, 1 NOT PROVEN

- **Link 1 geometry PASS** (tags 1/2/10, 8,625 nodes, quarter planes; seed repairs slide 10 -> 32; walls resolve to
  ~6.1 kHz at the 12 kHz request). **Link 2 solve PASS** (channel fields + force reciprocity <= 3.2e-4).
- **Link 3 physics sanity NOT PROVEN.** The dense CD-only sweep rises to 1250 Hz then falls monotonically; no notch
  in the +-20 % window around the 1-D 1010.8 Hz. At L1 the entry port is a rigid patch unless the lumped network is
  coupled, so the check needs the network-coupled response with zero mid drive - not run.
- **Link 4 network < 2 s FAILS: 6.58 s.** `optimise_network` did 1,224 CMA evaluations (5.4 ms each) for the shipped
  T2 brief (2 mid drivers x 2 xo orders x 2 polarities x up to 160). Per-evaluation budget is met; the whole-call gate
  is missed 3.3x. Fix is a budget/combo decision, not a solver change. A cache-hit evaluate is 9.31 s wall.
- **Link 5 search moves PASS.** Two 40-evaluation screens; all six knobs moved (T2 spreads: cov_h 13.3 deg, cov_v
  23.9 deg, z_frac 0.329, across 0.388, port_along 9.9 mm, slide 25.4 mm); 38/40 T2 and 31/40 T1 OK, the rest genuine
  `invalid_geometry`; no crash.
- **Link 6 re-score for free PASS.** The stored winner `ed11d2cd3acc` re-scored with `faitalpro_6pr160` and
  `hp_hz 160` without a new solve: J 9.530280 -> 9.727026, `cached True`, both finite.
- **Blocked, recorded:** M8 step 3's quarter-vs-full comparison is impossible today - `tools/cad/meh.py` refuses a
  full model (`quadrants '1234'` -> GeometryInvalidError, quarter open shell only). M8 step 4 needs link 3's coupled
  response. **M9 is blocked:** Boundary Lab is not in this workspace (`forks/` has only beat-bem and the mesher).

## 2026-11-01 (00:45 EDT) - MEH SCREEN DONE: T2 J 9.53 -> 11.89 verified, T1 J 13.23 -> 14.51 verified

- **Two 40-evaluation CMA screens + verify top 2 each, all on the new pin on the owner's GPU** [measured]:
  T2 `runs/20261101T004552Z-screen-427d57` best `ed11d2cd3acc` screen J **9.530** (second `719aeb7a4ff0` 9.550),
  verify **11.894 / 11.804**; T1 `runs/20261101T015657Z-screen-fc1d24` best `704051ae928c` screen J **13.228**
  (second `9b6548cc2a6c` 13.556), verify **14.512 / 14.636**. Details in `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **T2 beats T1 on its own brief's J** (9.53 vs 13.23 screen, 11.89 vs 14.51 verify). `lw_resid` dominates both
  (7.8 / 13.1 of J); `notch` is 0.0 in both, so the listening-window penalty is broad-band. Both winners push the
  driver to the top of the slide range (T2 `slide 35.2`, T1 36.1) and the ports low (`z_frac` 0.09 / 0.26).
- **One T2 verify design failed on a VRAM-ceiling worker reset** (7.9 GB of 8 GB) and the auto re-warm failed; after
  killing the stale BEAT host and confirming 1.36 GB idle, `verify --top 2` gave `2 designs, 0 failed`. The retry is
  recorded in the evidence doc; no tolerance changed.
- **`n_nan 12` in the winning record is not a metric failure:** `on_axis_db` is finite at all 12 frequencies and
  `n_nan_ripple 0`; the 12 NaNs are the synthesis's deliberately-NaN impedance array.
- **Two gaps opened by the screen (ISSUES):** (1) the solved grid was 12 frequencies 500-10,000 Hz, not the brief's
  120-12,000 Hz, so the objective scored `n_in_band 10` and never saw 120-500 Hz or 10-12 kHz; (2) `verify`'s own
  line says the verify mesh equals the screen mesh - only the frequency count and balloon size change, so it is a
  re-score, not a finer mesh.

## Status
- **Current (cloud senior 2026-11-18):** Owner questions RESOLVED (R1-R25, OWNER_DECISIONS_RESOLVED_2026-11-18.md); execution = LOCAL_AGENT_PROMPT_2026-11-18.md.
- **Phase:** senior-pass implementation (owner directive 2026-10-24; WP1â€“WP17, no Synergy/MEH). **M1 DONE and pushed** (WP1â€“WP4 offline parts + WP15 repo-side plumbing; Oracle GO). **M2 DONE: WP15 fused CUDA validated on the GPU** â€” ladder, fused GPU test, measured ceiling, 12 kHz verify; Oracle GO recorded in the M2 entry. **M3 DONE** (carry-overs + WP5/WP7/WP8 calibration, zero new searches; Oracle GO-with-fixes ALL applied). **M4 DONE (2026-10-25): WP9 generators (splice/throat_blend/spherical_salmon) + WP9b GRID rows (organic/elliptical/X-shape as labeled hypotheses + HALF models) + `lecleach` SHIPPED after R9-J PASSED (owner chat directive, Fourcade verified, 0.00 mm width) + WP10 GRID adapter** â€” 12 typology smokes green on the GPU, full-vs-quarter PASS, suites 1194/0/1/0 (intended tripwire only), Oracle GO-with-fixes (doc-only) applied. **M5 WP11 DONE (2026-10-25): restarts (IPOP/BIPOP mirroring pycma) + CMA-ME QD atlas (ribs 0.12.0 â€” offline-first, +40 tests, 4 GPU screens proving budget exactness incl. a fired 4-ES BIPOP run; Oracle GO-with-fixes applied; evidence `docs/evidence/M5_WP11_2026-10-25.md`, byte-check 30/30). M5B DONE (2026-10-25): WP14 multicell CATEGORY (CADâ†’STEP route: `tools/cad/multicell.py` + `mesh/step_build.py` + the `cad` recipe/echo/example + `solve.near_correction*`/`solve_precision`/`source_profile_alpha` keys) + WP16/17 fork branches LANDED AND GPU-VALIDATED (Julia 46/46 testsets incl. all four CUDA testsets; selftests 0.020/0.0390 dB; 3-arm A/B worst 4.94e-06 dB) + FORK HOSTED (github.com/llevaachingada/hornlab-beat-bem) + PIN MOVED THERE (`760a1ec`) â€” the test_mesh_pin tripwire RESOLVED, suite 1325/0/0/0; M4 debts finished; multicell PHYSICS DEFERRED (owner â€” mouth-topology defect diagnosed, evidence preserved); CLI selftest lock-kill fix; evidence `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md`, byte-check 33/33. M6/WP12 DONE (2026-10-25): enclosure mounting plumbed (brief.mounting â†’ the mesher's OWN keys, âˆ’mnt- cache keys, all echoes) AND MEASURED on two finalists â€” dofs +199.4 % / +106.5 %, both under the unchanged caps, enclosure J improves (a different objective landscape â€” never rank across mountings), reference parity 2.91e-06 dB; **WP13 OWNER-DEFERRED** ("don't know how necessary that is"); suite 1372/0/0/0; evidence `docs/evidence/M6_WP12_2026-10-25.md`, byte-check 21/21.** Waves 0â€“3 + CP-7 complete; CP-8a/b PASS, CP-8c CLOSED, CP-8d still FAILED (surrogate retrain pending more OSSE data â€” unchanged).
- **Done 2026-10-24:** M1: objective v2 (opt-in, offline re-score over 18,059 records: Spearman Ï(v1,v2) = 0.989, both compare-tier claims SURVIVE, v1 drift 0 â€” `docs/evidence/OBJECTIVE_V2_RESCORE.md`); WP2 driver pins with the embedded-brief grandfather; WP3 shape-only perturb + graded infeasibility; WP4 `freq_weights` + HF verify grid. WP15 repo side: `solve.cuda_fused` flag, env gating, diagnostics proof + refusal (fork branch `hornlab-search/fused-cuda` @ `fa99ee5` in `..\forks\hornlab-beat-bem`; Julia tests green). **M2 (late evening):** fork installed by SHA; ladder analytic **0.020 dB** / crosscheck **0.0390 dB** (both = base references); 3-arm A/B vs stored base-pin runs â‰¤ 2.9e-6 dB / 2.1e-05 deg (bars 0.039 dB / 1Â°); fused GPU test green ([measured] on-axis 0.0000 dB, bw 0.01-deg print precision, z_throat 3.35e-07; stale-host refusal); flag-off bit-determinism finding rebarred to a measured 1e-4 dB floor (base-pin reproduction logged); ceiling measured: fused **fits 15,984 / fails 20,237, SAFE = 12,000** (old path same mesh: 7,389 vs 2,217 MiB, 59.6 vs 9.1 s/freq); four `*_fusedcuda` configs (caps 5000/12000/12000); 12 kHz verify on the flag (4,438 dofs, 2.1 s/freq, 25Ã— fused proven). Evidence `docs/evidence/FUSED_CUDA_2026-10-24.md`; pin on `dev/fused-cuda-pin` ONLY (never main; GitHub hosting = owner action). **M3 (2026-10-25):** carry-overs @ `1dda493` + `solve.source_motion` / `mesh.rear_res_factor` / `mesh.band_split` (+ `stack_responses`, verify-only seam, `mesh_policy: band_split_v1` provenance) + the 17-job measurement pack on the stored WP5 finalists (`tools/m3_measurement_pack.py`); evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md`; details in the M3 entry above.
- **Next (next agent):** The implementation plan's NON-OWNER-GATED work is COMPLETE as of M6/WP12: the machine carries the brief-agnostic shape surface (classical + splice/throat-blend/salmon + GRID + organic rows + rollback lecleach/iwata_ar/toroidal + saddle halves) + restarts schedules + the QD-atlas contract + the CADâ†’STEP multicell category + the enclosure-mounting route (measured: dofs +199 %/+107 %, both under the unchanged caps) + the WP16 source plug + WP17 fused-CUDA near correction (stage 1) on the hosted fork's pinned stack (`760a1ec`; installed == pinned â€” the mesh-pin tripwire is green). **Everything remaining needs the owner: [a] the brief-design consultation (deferred) â€” 2â€“4 real briefs turn the machinery from "calibrated" into "aimed"; [b] resume-or-park the deferred WP14 multicell PHYSICS (the fixture's mouth-topology defect + the full resume recipe live in `docs/ISSUES.md`'s deferred-WP14 block; WP17 stage 1 is ready for it); [c] P6a superformula campaign + P6b GSA-vs-CMA-ES bake-off (owner-gated); [d] the small parked proposals (W7 balloon density, the M3/5 calibration proposals); [e] WP17 stage 2 (fused + per-image symmetry near caches) only when symmetric-drive multicells need the GPU. WP13 axisymmetric backend = OWNER-DEFERRED ("don't know how necessary that is" 2026-10-25).** Nothing else runs without the owner.
- **Open owner decisions:** v2 objective as brief DEFAULT (today opt-in); bound proposals (`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`); mesher bump (post-beta); surrogate OSSE top-up; GUI contrast owner click-path check remains; **P6a/P6b + W7 + the brief-design consultation + resume-or-park the deferred WP14 multicell physics (all owner-gated â€” see Next). RESOLVED 2026-10-25: fork hosting + pin (hosted fork; `760a1ec` pinned; installed == pinned â€” tripwire green); WP13 = OWNER-DEFERRED.**
- **Blockers:** none (owner gate on the pin hosting only).


