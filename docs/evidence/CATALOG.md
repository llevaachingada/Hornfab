# Evidence catalog

One line per `docs/evidence/` folder, loose evidence document and committed `docs/queue/` copy.
Sections are ordered by their newest entry; inside a section, newest first. Each line is
`path — date — outcome`. Rows tagged **superseded** or **negative** are history, not current
guidance.

Folder links open the directory; read its `README.md` (or the newest `.md` inside) for the full
record. Evidence is *about* data and never holds raw data. A folder's `queue_files` column in
`docs/handoffs/repo_findability_2026-11-25/inventory/I3_evidence.csv` lists the night configs it
used.

Companion catalogs: [research by topic](../research/README.md) ·
[queue sources of truth](../queue/README.md).

## CD backbone

- [docs/evidence/cd_variants_2026-11-25/](cd_variants_2026-11-25) — 2026-11-25 — **negative** — No variant passes all six rules (14 solves): 8 kHz H tops 59.9 deg; mid-band fails; hypothesis rejected.
- [docs/evidence/cd_backbone_2026-11-25/](cd_backbone_2026-11-25) — 2026-11-25 — Rolled transfers (J 7.683 -> 4.562, six rules) but LamAc does not converge; loading floor missed.
- [docs/evidence/home_xo900_2026-11-20/](home_xo900_2026-11-20) — 2026-11-20 — GO for small matched BEM study, NO-GO for full optimization; three score identities locked; FAV-001 protected.
- [docs/evidence/cd_v11_2026-11-20/](cd_v11_2026-11-20) — 2026-11-20 — After completion, 8/8 lanes have 50 valid evals; initial matrix had 1/8 complete.

## Coverage, constancy and room fit

- [docs/evidence/coverage_pull_2026-11-25/](coverage_pull_2026-11-25) — 2026-11-25 — No: corridor charges zero inside and ignores preferred_deg; constancy is separate opt-in; best J 1.3882 replays.
- [docs/evidence/cd_pm5const_2026-11-25/](cd_pm5const_2026-11-25) — 2026-11-25 — New constancy briefs built; replay moves favL best J 1.388 -> 6.363; jobs queued, verify pending.
- [docs/evidence/home_crowe_v9_offline_2026-11-17/](home_crowe_v9_offline_2026-11-17) — 2026-11-17 — Five not-queued v9 scenarios; slope-0 best J 0.940, others ~9.3-9.96; cross-brief rank refused.
- [docs/evidence/HOME_CROWE_V9_OFFLINE_CANDIDATES_2026-11-17.md](HOME_CROWE_V9_OFFLINE_CANDIDATES_2026-11-17.md) — 2026-11-17 — PASS: identity delta 0.000e+00; v9 DI-slope term dominates; five scenarios proposed.

## Compact 400, favL and size policy

- [docs/evidence/favL_2in_c500_continue_2026-11-25/](favL_2in_c500_continue_2026-11-25) — 2026-11-25 — Predeclared continuation of parent best J 1.870458; box 1.15 and new identity; no results yet.
- [docs/evidence/size_aware_2026-11-24/](size_aware_2026-11-24) — 2026-11-24 — Product lead 490 mm J 2.757/verify 2.694; larger discovery design 770 mm verifies J 1.608; descriptive only.
- [docs/evidence/expand_2026-11-20/](expand_2026-11-20) — 2026-11-20 — 5/8 reached 80 valid, zero failures; 3 s2c lanes stopped by owner, moved to another night.
- [docs/evidence/compact400_cont_2026-11-19/](compact400_cont_2026-11-19) — 2026-11-19 — Report-only XO diagnostics: Re z and per-unit-velocity levels; load_raw 0.000 for both fold and morph.

## BO studies and GUI

- [docs/evidence/cd_bo_cohort_2026-11-25/](cd_bo_cohort_2026-11-25) — 2026-11-25 — Predeclared four 100-valid CMA cohorts under v11 open115; builds and space preflight present; no results yet.
- [docs/evidence/metric_bo_gui_2026-11-23/](metric_bo_gui_2026-11-23) — 2026-11-23 — C3 tests and rehearsal pass; metric canary remains HELD pending B4; held packages launch disabled.
- [docs/evidence/overview_phase234_2026-11-20/](overview_phase234_2026-11-20) — 2026-11-20 — 79+4 tests pass; live payload 305 runs, 11 identities; no GPU or solver used.
- [docs/evidence/hw_gui_2026-11-20/](hw_gui_2026-11-20) — 2026-11-20 — GUI browser evidence: final 104/104 sweep (13 routes x 4 widths x dark/light) and 14-step keyboard-only report.
- [docs/evidence/bo_gui_2026-11-15/](bo_gui_2026-11-15) — 2026-11-15 — Screenshots of bo_s31001: panels render; compare verdict incomplete; no study started or solved.
- [docs/evidence/BAYESIAN_STUDY_INTEGRATION_2026-11-14.md](BAYESIAN_STUDY_INTEGRATION_2026-11-14.md) — 2026-11-14 — PASS: 24 call units, best screen J 3.1055, replay delta zero.
- [docs/evidence/bo_study_2026-11-12/](bo_study_2026-11-12) — 2026-11-12 — M0-M2 snapshot: native rescore parity 197/200 (max dJ 0); S2 lacks producer pins; S5 seed packs blocked.
- [docs/evidence/campaigns/](campaigns) — 2026-10-23 — compare campaign: perturbed_osse_hv best J 10.297; hyb 15.065; rosse baseline 12.314.

## Rolled and Klangfilm-Lame families

- [docs/evidence/directivity_attribution_2026-11-24/](directivity_attribution_2026-11-24) — 2026-11-24 — Wall angle at 20-40% of pre-roll arc sets 6-8 kHz; H amplitude causes 2 kHz overshoot; gains survive epw 9.
- [docs/evidence/throat_hv_2026-11-18/](throat_hv_2026-11-18) — 2026-11-18 — Phase 1 7/7 OK; B_o50 best B beats control by 0.251; Phase 3 best J 5.608; differences survive epw 8.
- [docs/evidence/klangfilm_hv_2026-11-16/](klangfilm_hv_2026-11-16) — 2026-11-16 — **negative** — No: offsets move pattern <=2.74 deg in wrong direction and score worse; Phase B monotone core warranted.
- [docs/evidence/KLANGFILM_HV_THROAT_AUDIT.md](KLANGFILM_HV_THROAT_AUDIT.md) — 2026-11-16 — **negative** — Phase A throat-only rejected; Phase B core built, B3 improves DI but H 65.2 deg below 70 floor.

## Mesh, frequency and termination policy

- [docs/evidence/variable_mesh_2026-11-23/](variable_mesh_2026-11-23) — 2026-11-23 — PASS at factor 1.5 with margin; 2.0 passes but not adopted; CAD rear coarsening absent, grid saturates.
- [docs/evidence/screen_12k_2026-11-23/](screen_12k_2026-11-23) — 2026-11-23 — **negative** — No default change: 162 evaluations (161 ok, 1 timeout); no adoption of 12 kHz screen policy.
- [docs/evidence/termination_overlay_2026-11-20/](termination_overlay_2026-11-20) — 2026-11-20 — Hold at geometry gate: archived meshes reproduce, but overlay changes outer wall and excitation patch.
- [docs/evidence/b1_readiness_2026-11-18/](b1_readiness_2026-11-18) — 2026-11-18 — Yes: zero-free-dimension search refused in three places; B1/B1f lines already use kind command; no GPU.
- [docs/evidence/b1_mesh_2026-11-18/](b1_mesh_2026-11-18) — 2026-11-18 — 8/8 probes complete, no VRAM spill; 6/8 mesh-sensitive; both leaders remain infeasible at epw 12.
- [docs/evidence/REAR_DENSITY_MESH_AUDIT_2026-11-13.md](REAR_DENSITY_MESH_AUDIT_2026-11-13.md) — 2026-11-13 — Factors 1.5 and 2.0 recommendable; 1.5 lowers DOF 16-21% with no plateau.
- [docs/evidence/HF12K_VERIFY_2026-10-23.md](HF12K_VERIFY_2026-10-23.md) — 2026-10-23 — Finalists verified; peak VRAM 7,360 MiB at 6,049 dofs; 12 kHz at the 8 GB edge.

## System, mounting, measurement and MEH

- [docs/evidence/horn_over_cabinet_2026-11-22/](horn_over_cabinet_2026-11-22) — 2026-11-22 — One pose resolved, legal and CPU-solved at three placements; one pose refused for penetration; not calibrated.
- [docs/evidence/system_evidence_2026-11-19/](system_evidence_2026-11-19) — 2026-11-19 — CPU BL cases run; wrong-port attempt retained; all single-mesh; 10 m vs 2 m max 1.38 dB.
- [docs/evidence/anchor_st260_2026-11-18/](anchor_st260_2026-11-18) — 2026-11-18 — Config corrected to STL refit; no admissible measured build; ST260 not solved.
- [docs/evidence/meh_2026-11-01/](meh_2026-11-01) — 2026-11-01 — Two winners: T2 screen/verify J 9.530/11.894; T1 13.228/14.512; mesh-limited top band.
- [docs/evidence/HARDWARE_2026-11-01.md](HARDWARE_2026-11-01.md) — 2026-11-01 — Decision: rent a pilot; 12 kHz full-wall needs H200-class memory; no purchase proven.
- [docs/evidence/MEH_M8_2026-10-31.md](MEH_M8_2026-10-31.md) — 2026-10-31 — Links 1,2,5,6 pass; link 4 fails (network 6.58 s); M9 blocked.
- [docs/evidence/MEH_M2_FORK_2026-10-31.md](MEH_M2_FORK_2026-10-31.md) — 2026-10-31 — Python tests pass and defaults stay byte-identical; Julia testsets deferred to M8.
- [docs/evidence/M6_WP12_2026-10-25.md](M6_WP12_2026-10-25.md) — 2026-10-25 — Measured on both finalists; cost/sensitivity only, not a quality verdict; 21/21 byte-check.
- [docs/evidence/MEASUREMENT_PACK_2026-10-24.md](MEASUREMENT_PACK_2026-10-24.md) — 2026-10-24 — Proposes distance 10 m, balloon 1024, rear factor 2.0; band split fails and is not adopted.

## Sculpted / R-OSSE, ripple and HF

- [docs/evidence/sculpted_xo900_v11_2026-11-21/](sculpted_xo900_v11_2026-11-21) — 2026-11-21 — R3 best J 2.694; R2 3.106; controls 2.9-3.4; single-seed matched comparison, 7/7 queue complete.
- [docs/evidence/sculpted_meridians_2026-11-20/](sculpted_meridians_2026-11-20) — 2026-11-20 — Nine derivatives plus two byte-matched controls; geometry checkpoint only; no acoustic ranking claimed.
- [docs/evidence/ripple_program_2026-11-20/](ripple_program_2026-11-20) — 2026-11-20 — Not redundant across 748 runs; source.cap inert on grid path; HF width cannot widen inside envelope.
- [docs/evidence/spectral_ripple_audit_2026-11-19/](spectral_ripple_audit_2026-11-19) — 2026-11-19 — Reproduces exactly; 24 v7 runs; report-only, zero solver calls, no score changed.
- [docs/evidence/HANDOFF_6b.md](HANDOFF_6b.md) — 2026-10-22 — PASS: suite/doctor/dry-run/symmetry pass; 60-candidate best J 30.945 to 16.789.

## Scoring and objective versions

- [docs/evidence/xo_loading_gateA_2026-11-19/](xo_loading_gateA_2026-11-19) — 2026-11-19 — Report-only: parity exact; under-loaded horns 5-8 dB below 2 kHz; levels per unit acceleration; duplicate hashes differ.
- [docs/evidence/v10_rescore_scout40w4_2026-11-19/](v10_rescore_scout40w4_2026-11-19) — 2026-11-19 — 74 of 88 rows re-scored; best J 1.959 at 3eb0103a511e; 0 brief-mismatch skips.
- [docs/evidence/v10_rescore_2026-11-18/](v10_rescore_2026-11-18) — 2026-11-18 — Tool ready, not run: replay gate admits v10; new CLI filters and compares; no results in folder.
- [docs/evidence/pattern_quality_readonly/](pattern_quality_readonly) — 2026-11-17 — Report-only diagnostics pass parity (max angle delta 0.0 deg); 18 fixtures; v1-v9 scoring untouched.
- [docs/evidence/PATTERN_QUALITY_READONLY_2026-11-17.md](PATTERN_QUALITY_READONLY_2026-11-17.md) — 2026-11-17 — Report-only tool added; parity 0.000e+00; 22 tests pass; nothing weighted into J.
- [docs/evidence/CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md](CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md) — 2026-11-17 — Identity replays exact; Crowe 16.918 to 6.836 smooth, Klangfilm 22.782 to 8.924 smooth.
- [docs/evidence/NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md](NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md) — 2026-11-16 — Four-run truth table: Crowe on base CD brief, Klangfilm on smooth; J not like-for-like.
- [docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md](HOME_OSSE_HIFI_RERANK_2026-11-16.md) — 2026-11-16 — Spearman +0.87/+0.89 vs J_v7; top-N overlap 18; dsp and passive rankings reported.
- [docs/evidence/RESCORE_V6_V7_2026-11-12.md](RESCORE_V6_V7_2026-11-12.md) — 2026-11-12 — 22,928 rows rescored; top-20 overlap 2/20, Kendall tau 0.32 (class A): rankings diverge.
- [docs/evidence/OBJECTIVE_V4_TOLERANCES.md](OBJECTIVE_V4_TOLERANCES.md) — 2026-10-27 — Recommends Option A physical tolerances with per-class blocks and floors.
- [docs/evidence/objective_v2_rescore/](objective_v2_rescore) — 2026-10-24 — 18,059 records: Spearman rho 0.989; both compare-tier claims survive; v1 drift 0.
- [docs/evidence/OBJECTIVE_V2_RESCORE.md](OBJECTIVE_V2_RESCORE.md) — 2026-10-24 — Verdicts recomputed: v1 medians reproduce; v2 claim tables printed, several survive.

## Search, cohorts and verification

- [docs/evidence/Q3_MORE_SOLVES_2026-11-19.md](Q3_MORE_SOLVES_2026-11-19.md) — 2026-11-19 — Crowe v2a gained 6.4779 but stays a tie; fold/ext lanes box-limited; map gaps listed.
- [docs/evidence/PRIORITY10_QUEUE_2026-11-19.md](PRIORITY10_QUEUE_2026-11-19.md) — 2026-11-19 — Control gate passed; v10 lanes tie above floor; do not requeue from lane seeds.
- [docs/evidence/P12_VERIFY_2026-11-19.md](P12_VERIFY_2026-11-19.md) — 2026-11-19 — PASS: screen order holds (morph > fold > twinray); ext-throat lane closed.
- [docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md](SIGMA0_ANALYSIS_2026-11-17.md) — 2026-11-17 — Guidance: pick sigma0 via preflight per bound span; retuned b3 cut J 56% in 102 evals.
- [docs/evidence/UMAP_SOLANA_OSSE_MEH_SF_CMA1000.md](UMAP_SOLANA_OSSE_MEH_SF_CMA1000.md) — 2026-11-03 — Method documented: UMAP over 18 unit knobs; interactive view, not a term decomposition.
- [docs/evidence/STAGED_SEARCH_AB_2026-10-31.md](STAGED_SEARCH_AB_2026-10-31.md) — 2026-10-31 — Joint wins: staged 2.6290 vs joint 2.4389; promotion stays not-yet, helper kept.
- [docs/evidence/HARDENED_D_2026-10-29.md](HARDENED_D_2026-10-29.md) — 2026-10-29 — **negative** — Negative: 389+100 rows, 0 pass-all; H and loading remain the blockers.
- [docs/evidence/M5_WP11_2026-10-25.md](M5_WP11_2026-10-25.md) — 2026-10-25 — Pass: all four screen jobs OK; QD coverage 5.08%; suite 1234/0/1/0.
- [docs/evidence/EARLY_REJECTION_REPLAY.md](EARLY_REJECTION_REPLAY.md) — 2026-10-22 — **negative** — Negative: rejects under 0.1-0.5% of candidates; too loose to pay off, no top-20 lost.

## Typologies and geometry authority

- [docs/evidence/wp43_b2_authority/](wp43_b2_authority) — 2026-11-18 — Only V terminal width passes (32.32 deg V) but costs +2.30 J; four others inert below 3 deg.
- [docs/evidence/wp42_u3_biradial/](wp42_u3_biradial) — 2026-11-18 — PASS: max band delta 0.997 deg against the 1 deg bound; bandwidth check true.
- [docs/evidence/SOLANA_WG_2026-11-01.md](SOLANA_WG_2026-11-01.md) — 2026-11-01 — Screen seed solves J 41.906 at 4,284 dofs; CD-only, qualitative guide comparison.
- [docs/evidence/SAWMOD_CONTROL_WG_2026-11-01.md](SAWMOD_CONTROL_WG_2026-11-01.md) — 2026-11-01 — Screen seed solves J 345.246 at 1,464 dofs; CD-only, qualitative whitepaper comparison.
- [docs/evidence/ATLAS_V2_GRIDS_2026-10-31.md](ATLAS_V2_GRIDS_2026-10-31.md) — 2026-10-31 — PASS: 12 to 17 points on three briefs; all four load and shape-check.
- [docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md](TYPOLOGY_SMOKE_MATRIX_2026-10-25.md) — 2026-10-25 — Three of five solve (J 22.98/37.47/60.14); two fail mesh_too_large; byte-check 29/29.
- [docs/evidence/M4_SMOKE_2026-10-25.md](M4_SMOKE_2026-10-25.md) — 2026-10-25 — PASS with margin: matrix verified, byte-check 44/44; two disclosure gaps noted.
- [docs/evidence/ATH_TYPOLOGIES_2026-10-25.md](ATH_TYPOLOGIES_2026-10-25.md) — 2026-10-25 — PASS: both mesh and seed-solve (J 42.448, 38.357); suite 1606 passed.
- [docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md](TYPOLOGY_COMPARE_2026-10-23.md) — 2026-10-23 — osse_axi leads axi (9.631); hybrid leads hifi; bound proposals listed, not applied.
- [docs/evidence/TYPOLOGY_VERIFY.md](TYPOLOGY_VERIFY.md) — 2026-10-22 — PASS V1-V5: unit properties, evaluator fidelity, mesher 11/11, anchors, textbook physics.
- [docs/evidence/TYPOLOGY_SCREEN_2026-10-22.md](TYPOLOGY_SCREEN_2026-10-22.md) — 2026-10-22 — osse_axi best on axi (J 10.71); new hybrid best on 90x60; tractrix fails directivity.

## Campaigns, nights and artifacts

- [docs/evidence/night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md](night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md) — 2026-11-18 — Throat cross-check PASS; nine ids triaged, one clean arm; no code fixed.
- [docs/evidence/gpu_queue_resolved_2026-11-18/](gpu_queue_resolved_2026-11-18) — 2026-11-18 — Approved job files for the ST260 anchor and R15 BO-arm reruns; no results in folder.
- [docs/evidence/day_2026-11-12_partial/](day_2026-11-12_partial) — 2026-11-12 — Partial day report charts only (10 PNGs); run still in progress; final report will supersede.
- [docs/evidence/NIGHT_2026-11-12_PARTIAL.md](NIGHT_2026-11-12_PARTIAL.md) — 2026-11-12 — **superseded** — PARTIAL snapshot: 2 CPU jobs, one blocked on GPU busy; superseded by the full night report.
- [docs/evidence/NIGHT_2026-11-12.md](NIGHT_2026-11-12.md) — 2026-11-12 — Rollup across six nights; retracts CPU-concurrency slowdown claim; per-lane best J reported.
- [docs/evidence/DAY_2026-11-12_ANALYSIS_PARTIAL.md](DAY_2026-11-12_ANALYSIS_PARTIAL.md) — 2026-11-12 — PARTIAL: multiple run best-J and analysis sections; final report deferred.
- [docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md](CAMPAIGN_SMOKE_2026-10-27.md) — 2026-10-27 — Smoke ran; seed/best J reported per cell; several follow-ups left open.
- [docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md](CAMPAIGN_DRYRUN_2026-10-26.md) — 2026-10-26 — PASS: 23/23 cells mesh, under 12,000 dofs, pass envelope and K-law checks.
- [docs/evidence/runs/](runs) — 2026-10-22 — 11 CUDA run summaries; best J 5.983, worst 41.781; raw designs excluded; metadata manifest present.
- [docs/evidence/logs/](logs) — 2026-10-13 — Committed CP-8c tick and watchdog logs; no stated outcome.

## Infrastructure, provenance and releases

- [docs/evidence/wp09_d9_provenance_2026-11-18/](wp09_d9_provenance_2026-11-18) — 2026-11-18 — 48,471 rebuildable / 3 bridge / 0 refused / 0 unverified; classification counts only.
- [docs/evidence/AGENT_PING_2026-11-17.md](AGENT_PING_2026-11-17.md) — 2026-11-17 — PASS: all 8 hornlab skills discoverable, no rbassist grant in canonical or container.
- [docs/evidence/HF_UPLOAD_2026-11-14.md](HF_UPLOAD_2026-11-14.md) — 2026-11-14 — PASS: all 8 files committed smallest-first by 19:10Z; hub commit list is the record.
- [docs/evidence/HF_UPLOAD_2026-11-13.md](HF_UPLOAD_2026-11-13.md) — 2026-11-13 — **superseded** — Scheduled run and manual retry failed on S3/DNS; no commit landed.
- [docs/evidence/CP-8d_retrain_2026-10-23.md](CP-8d_retrain_2026-10-23.md) — 2026-10-23 — **negative** — FAILED: topk_overlap, invalid_accuracy, monotonic_flips fail; model not used.
- [docs/evidence/BETA_READINESS.md](BETA_READINESS.md) — 2026-10-23 — Items pass with documented gaps; pin kept, cache and 12k brief fixes noted; D3 Ctrl-C PASS.
- [docs/evidence/README.md](README.md) — 2026-10-22 — Evidence about data, never data; manifest covers run/store structure, not raw npz arrays.
- [docs/evidence/BL_LEARNINGS_GPU.md](BL_LEARNINGS_GPU.md) — 2026-10-22 — All steps PASS; early-rejection replay rejects under 0.1-0.5% of candidates, not worth adopting.
- [docs/evidence/CP-8d.md](CP-8d.md) — 2026-10-14 — **negative** — FAIL: gate failed twice (topk_overlap, bw_mae, monotonic_flips); model not used.
- [docs/evidence/CP-8c_throat_adapter.md](CP-8c_throat_adapter.md) — 2026-10-14 — COMPLETED: 400 evals, 0 failures, best J 5.98344 vs seed 9.15918.
- [docs/evidence/CP-8c_data_summary.md](CP-8c_data_summary.md) — 2026-10-14 — Digest: 3,156 records, 3 families, held-out 225 below the 500 gate floor.
- [docs/evidence/CP-8c_osse_baseline.md](CP-8c_osse_baseline.md) — 2026-10-13 — COMPLETED: 1500 evals, best J 6.10609 vs seed 22.5921; n pinned at lower bound.
- [docs/evidence/CP-8c_icw_termination.md](CP-8c_icw_termination.md) — 2026-10-13 — COMPLETED: 800 evals, best J 12.2009 vs seed 55.7357; hold_end pinned low.
- [docs/evidence/CP-8c_freeform_hv.md](CP-8c_freeform_hv.md) — 2026-10-13 — COMPLETED EARLY on CMA convergence; 722 evals, best J 30.5434 vs seed 33.3086.
- [docs/evidence/CP-8b.md](CP-8b.md) — 2026-10-13 — PASS: a_deg lo 5.0 and exponent lo 1.0 mesh; no key remains pinned.
- [docs/evidence/CP-8a.md](CP-8a.md) — 2026-10-13 — PASS: 10/10 doctor checks pass; dataset 134 records, 100% OSSE warning.

## Crowe typology and geometry truth

- [docs/evidence/crowe_v2a_geometry_truth/](crowe_v2a_geometry_truth) — 2026-11-17 — 12 admitted four-DOF cases (seed, interiors, single-variable pairs, corners); no invalid corner dropped; no outcome claimed.
- [docs/evidence/CROWE_V2A_SOLVER_SURFACE_TRUTH_2026-11-17.md](CROWE_V2A_SOLVER_SURFACE_TRUTH_2026-11-17.md) — 2026-11-17 — DONE: p99 error about 0.11-0.13 mm across 12 cases; rank 4; 26 tests pass.
- [docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md](CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md) — 2026-11-16 — Four search dimensions only, hold fixed at 0; law-level and mesh evidence, no BEM solve.
- [docs/evidence/CROWE_HV_AREA_ASPECT_V1_2026-11-16.md](CROWE_HV_AREA_ASPECT_V1_2026-11-16.md) — 2026-11-16 — **superseded** — Geometry evidence only: generator lands, 18 tests, real mesh; superseded for throat by V2A.

## Solver, compute and benchmarking

- [docs/evidence/SPEED_ADOPTION_2026-11-14.md](SPEED_ADOPTION_2026-11-14.md) — 2026-11-14 — ADOPTED solver 38e5b1f (wall -24.7/-28.0%); batching rejected; 15,878-dof ceiling fits.
- [docs/evidence/G2_FORK_AB_2026-11-13.md](G2_FORK_AB_2026-11-13.md) — 2026-11-13 — Adopt-with-conditions: peak VRAM 2,091 to 319 MiB at 4,168 dofs; parity PASS.
- [docs/evidence/THROUGHPUT_N1_2026-11-12.md](THROUGHPUT_N1_2026-11-12.md) — 2026-11-12 — Decided: fused ON, prefetch OFF at 8k+ dofs, freq_batch_size 12; owner flips defaults.
- [docs/evidence/BENCH_FULLRANGE_THREADS_2026-11-03.md](BENCH_FULLRANGE_THREADS_2026-11-03.md) — 2026-11-03 — CUDA wins 12-point screen; CPU wins 8k+ dofs and 41-point sweeps; threads no effect.
- [docs/evidence/BENCH_CPU_VS_CUDA_2026-11-03.md](BENCH_CPU_VS_CUDA_2026-11-03.md) — 2026-11-03 — **superseded** — Claimed CPU 6.4x faster and 16 kHz reachable; conclusion later superseded by the audit.
- [docs/evidence/BENCH_AUDIT_2026-11-03.md](BENCH_AUDIT_2026-11-03.md) — 2026-11-03 — Audit: the CUDA arm spilled to shared memory; the 6.4x CPU conclusion does not hold.
- [docs/evidence/BENCH_40_DESIGNS_2026-11-03.md](BENCH_40_DESIGNS_2026-11-03.md) — 2026-11-03 — Warm mean CUDA 3.54 s vs CPU 4.18 s; CPU wins 6/40; SPL parity 3.6e-05 dB.
- [docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md](M5B_WP14_WP16_WP17_2026-10-25.md) — 2026-10-25 — Landed and validated: Julia 46/46 testsets, byte-check 33/33; physics deferred.
- [docs/evidence/FUSED_CUDA_2026-10-24.md](FUSED_CUDA_2026-10-24.md) — 2026-10-24 — Measured fused ceiling 15,984 dofs; safe cap 12,000 dofs at 4,744 MiB; 20,237 fails.
- [docs/evidence/SOLVER_VERIFY_2026-10-22.md](SOLVER_VERIFY_2026-10-22.md) — 2026-10-22 — PASS: 18 GPU tests pass; crosscheck 0.039 dB vs 0.2 dB bar; analytic PASS.

## Committed queue configs

`docs/queue/` holds committed copies of night files and their support material. The live files are `runs/nights/<night>.yaml` (gitignored); see [the queue README](../queue/README.md). This list is the 112 `docs/queue/` rows in the I3 inventory; newer night files also sit in the directory but are not separate inventory rows.

- [docs/queue/source_sensitivity_2026-11-20.yaml](../queue/source_sensitivity_2026-11-20.yaml) — 2026-11-20 — committed copy of a night/queue config
- [docs/queue/source_sensitivity4_2026-11-20.yaml](../queue/source_sensitivity4_2026-11-20.yaml) — 2026-11-20 — committed copy of a night/queue config
- [docs/queue/source_sensitivity3_2026-11-20.yaml](../queue/source_sensitivity3_2026-11-20.yaml) — 2026-11-20 — committed copy of a night/queue config
- [docs/queue/source_sensitivity2_2026-11-20.yaml](../queue/source_sensitivity2_2026-11-20.yaml) — 2026-11-20 — committed copy of a night/queue config
- [docs/queue/hf_width_2026-11-20.yaml](../queue/hf_width_2026-11-20.yaml) — 2026-11-20 — committed copy of a night/queue config
- [docs/queue/hf_width2_2026-11-20.yaml](../queue/hf_width2_2026-11-20.yaml) — 2026-11-20 — committed copy of a night/queue config
- [docs/queue/q3_more_solves_2026-11-19.yaml](../queue/q3_more_solves_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/q3_more_solves_2026-11-19.admission.json](../queue/q3_more_solves_2026-11-19.admission.json) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/p12_verify_2026-11-19.yaml](../queue/p12_verify_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/p12_verify_2026-11-19.admission.json](../queue/p12_verify_2026-11-19.admission.json) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/p11_s2w_2026-11-19.yaml](../queue/p11_s2w_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/p11_s2w_2026-11-19.admission.json](../queue/p11_s2w_2026-11-19.admission.json) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/fable_vt_b6_2026-11-19.yaml](../queue/fable_vt_b6_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/fable_scout40w2_2026-11-19.yaml](../queue/fable_scout40w2_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/fable_priority10_2026-11-19.yaml](../queue/fable_priority10_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/fable_priority10_2026-11-19.admission.json](../queue/fable_priority10_2026-11-19.admission.json) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/fable_expand_2026-11-19.yaml](../queue/fable_expand_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/compact400_next10_2026-11-19.yaml](../queue/compact400_next10_2026-11-19.yaml) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/compact400_next10_2026-11-19.admission.json](../queue/compact400_next10_2026-11-19.admission.json) — 2026-11-19 — committed copy of a night/queue config
- [docs/queue/rosse_r50_refine_2026-11-17.yaml](../queue/rosse_r50_refine_2026-11-17.yaml) — 2026-11-17 — committed copy of a night/queue config
- [docs/queue/top3_last16h_2026-11-16.png](../queue/top3_last16h_2026-11-16.png) — 2026-11-16 — committed queue-support image (seed/render sheet), not a config
- [docs/queue/rosse_r120_2026-11-16.yaml](../queue/rosse_r120_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/img_lecleach_hv_seed_2026-11-16.png](../queue/img_lecleach_hv_seed_2026-11-16.png) — 2026-11-16 — committed queue-support image (seed/render sheet), not a config
- [docs/queue/home_extension_2026-11-16.yaml](../queue/home_extension_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/home_day_2026-11-16.yaml](../queue/home_day_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/home_day2_2026-11-16.yaml](../queue/home_day2_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/home18_b_2026-11-16.yaml](../queue/home18_b_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/home18_a_2026-11-16.yaml](../queue/home18_a_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_multityp_r2_2026-11-16.yaml](../queue/bo_multityp_r2_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_multityp_r2_2026-11-16.admission.json](../queue/bo_multityp_r2_2026-11-16.admission.json) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_multityp_2026-11-16.yaml](../queue/bo_multityp_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_multityp_2026-11-16.admission.json](../queue/bo_multityp_2026-11-16.admission.json) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_ext_2026-11-16.yaml](../queue/bo_ext_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_cov_pilot_2026-11-16.yaml](../queue/bo_cov_pilot_2026-11-16.yaml) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/bo_cov_pilot_2026-11-16.admission.json](../queue/bo_cov_pilot_2026-11-16.admission.json) — 2026-11-16 — committed copy of a night/queue config
- [docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md](../queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/MATCHED_HOME_PROTOCOL_2026-11-16.md](../queue/MATCHED_HOME_PROTOCOL_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/HOME_SCORE_AUDIT_2026-11-16.md](../queue/HOME_SCORE_AUDIT_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/HOME_SCORE_AUDIT_2026-11-16.json](../queue/HOME_SCORE_AUDIT_2026-11-16.json) — 2026-11-16 — committed queue-support analysis JSON, not a config
- [docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md](../queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/HOME_CONTINUATION_2026-11-16.md](../queue/HOME_CONTINUATION_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/HOME_18H_PLAN_2026-11-16.md](../queue/HOME_18H_PLAN_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md](../queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/BO_EXT_PLAN_2026-11-16.md](../queue/BO_EXT_PLAN_2026-11-16.md) — 2026-11-16 — committed queue plan/notes, not a config
- [docs/queue/section_pucker_validation_2026-11-15.json](../queue/section_pucker_validation_2026-11-15.json) — 2026-11-15 — committed queue-support analysis JSON, not a config
- [docs/queue/sab_home_gpu_rest_2026-11-15.yaml](../queue/sab_home_gpu_rest_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/radial_25x2_2026-11-15.ps1](../queue/radial_25x2_2026-11-15.ps1) — 2026-11-15 — committed queue-support script, not a config
- [docs/queue/img_home_landscape_seeds_v3_2026-11-15.png](../queue/img_home_landscape_seeds_v3_2026-11-15.png) — 2026-11-15 — committed queue-support image (seed/render sheet), not a config
- [docs/queue/img_home_landscape_seeds_v2_2026-11-15.png](../queue/img_home_landscape_seeds_v2_2026-11-15.png) — 2026-11-15 — committed queue-support image (seed/render sheet), not a config
- [docs/queue/img_home_landscape_seeds_2026-11-15.png](../queue/img_home_landscape_seeds_2026-11-15.png) — 2026-11-15 — committed queue-support image (seed/render sheet), not a config
- [docs/queue/home_section_pucker_2026-11-15.yaml](../queue/home_section_pucker_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_rolled_rect_2026-11-15.yaml](../queue/home_rolled_rect_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_landscape_e_2026-11-15.yaml](../queue/home_landscape_e_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_landscape_d_2026-11-15.yaml](../queue/home_landscape_d_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_landscape_c_2026-11-15.yaml](../queue/home_landscape_c_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_landscape_b_2026-11-15.yaml](../queue/home_landscape_b_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_landscape_a_2026-11-15.yaml](../queue/home_landscape_a_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/home_crowe_sections_2026-11-15.yaml](../queue/home_crowe_sections_2026-11-15.yaml) — 2026-11-15 — committed copy of a night/queue config
- [docs/queue/SECTION_PUCKER_PLAN_2026-11-15.md](../queue/SECTION_PUCKER_PLAN_2026-11-15.md) — 2026-11-15 — committed queue plan/notes, not a config
- [docs/queue/ROLLED_RECT_PLAN_2026-11-15.md](../queue/ROLLED_RECT_PLAN_2026-11-15.md) — 2026-11-15 — committed queue plan/notes, not a config
- [docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md](../queue/HOME_LANDSCAPE_PLAN_2026-11-15.md) — 2026-11-15 — committed queue plan/notes, not a config
- [docs/queue/speed_round_b_rep2_2026-11-14.yaml](../queue/speed_round_b_rep2_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/speed_round_b_2026-11-14.yaml](../queue/speed_round_b_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/speed_round_b4_2026-11-14.yaml](../queue/speed_round_b4_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/speed_round_a_2026-11-14.yaml](../queue/speed_round_a_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/sab_lecleach_cpu_2026-11-14.yaml](../queue/sab_lecleach_cpu_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/sab_home_gpu_2026-11-14.yaml](../queue/sab_home_gpu_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/resume_print_night_2026-11-14.yaml](../queue/resume_print_night_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/print80x60_jobs23_2026-11-14.yaml](../queue/print80x60_jobs23_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/cohort_extend50_2026-11-14.yaml](../queue/cohort_extend50_2026-11-14.yaml) — 2026-11-14 — committed copy of a night/queue config
- [docs/queue/SAB_HOME_PLAN_2026-11-14.md](../queue/SAB_HOME_PLAN_2026-11-14.md) — 2026-11-14 — committed queue plan/notes, not a config
- [docs/queue/rev2_gpu_ablation_2026-11-13.yaml](../queue/rev2_gpu_ablation_2026-11-13.yaml) — 2026-11-13 — committed copy of a night/queue config
- [docs/queue/rev2_cpu_parity_2026-11-13.yaml](../queue/rev2_cpu_parity_2026-11-13.yaml) — 2026-11-13 — committed copy of a night/queue config
- [docs/queue/rev2_E0_manifest_2026-11-13.json](../queue/rev2_E0_manifest_2026-11-13.json) — 2026-11-13 — committed queue-support analysis JSON, not a config
- [docs/queue/SPEED_PROGRAM_2026-11-13.md](../queue/SPEED_PROGRAM_2026-11-13.md) — 2026-11-13 — committed queue plan/notes, not a config
- [docs/queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md](../queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md) — 2026-11-13 — committed queue plan/notes, not a config
- [docs/queue/SPEED_COMBINED_2026-11-13.md](../queue/SPEED_COMBINED_2026-11-13.md) — 2026-11-13 — committed queue plan/notes, not a config
- [docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md](../queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md) — 2026-11-13 — committed queue plan/notes, not a config
- [docs/queue/lecleach_saddle_wide_ratio_deep.png](../queue/lecleach_saddle_wide_ratio_deep.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_vs_ref.png](../queue/lecleach_saddle_vs_ref.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_v3_seed.png](../queue/lecleach_saddle_v3_seed.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_v3_cornerB.png](../queue/lecleach_saddle_v3_cornerB.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_v3_cornerA.png](../queue/lecleach_saddle_v3_cornerA.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_stop_lo.png](../queue/lecleach_saddle_stop_lo.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_stop_hi_deep_roll.png](../queue/lecleach_saddle_stop_hi_deep_roll.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_shaded.png](../queue/lecleach_saddle_shaded.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_seed.png](../queue/lecleach_saddle_seed.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_narrow_ratio_shallow.png](../queue/lecleach_saddle_narrow_ratio_shallow.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_a2_lo_T_lo.png](../queue/lecleach_saddle_a2_lo_T_lo.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_a2_hi_T_hi.png](../queue/lecleach_saddle_a2_hi_T_hi.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_shallow_s.png](../queue/lecleach_saddle_FULL_shallow_s.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_shallow_a.png](../queue/lecleach_saddle_FULL_shallow_a.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_seed_s.png](../queue/lecleach_saddle_FULL_seed_s.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_seed_b.png](../queue/lecleach_saddle_FULL_seed_b.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_seed_a.png](../queue/lecleach_saddle_FULL_seed_a.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_deep_s.png](../queue/lecleach_saddle_FULL_deep_s.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/lecleach_saddle_FULL_deep_a.png](../queue/lecleach_saddle_FULL_deep_a.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_throat_closeup.png](../queue/klangfilm_throat_closeup.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_param_sheet_hires.png](../queue/klangfilm_param_sheet_hires.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_param_sheet.png](../queue/klangfilm_param_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_start_sheet.png](../queue/klangfilm_lame_start_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_shallowV_sheet.png](../queue/klangfilm_lame_shallowV_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_ellipse_beak_sheet.png](../queue/klangfilm_lame_ellipse_beak_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_ellipse_E2_sheet.png](../queue/klangfilm_lame_ellipse_E2_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_V5_sheet.png](../queue/klangfilm_lame_V5_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_PS_seed_sheet.png](../queue/klangfilm_lame_PS_seed_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_P1-P4_sheet.png](../queue/klangfilm_lame_P1-P4_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_lame_DE_variants_sheet.png](../queue/klangfilm_lame_DE_variants_sheet.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_ellipse_v2.png](../queue/klangfilm_ellipse_v2.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_ellipse_throat.png](../queue/klangfilm_ellipse_throat.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_ellipse_renders.png](../queue/klangfilm_ellipse_renders.png) — undated — committed queue-support image (seed/render sheet), not a config
- [docs/queue/klangfilm_ellipse_bend.png](../queue/klangfilm_ellipse_bend.png) — undated — committed queue-support image (seed/render sheet), not a config
