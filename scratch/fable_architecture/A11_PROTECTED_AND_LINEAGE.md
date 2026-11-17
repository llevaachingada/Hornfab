# A11 — Protected families and run lineage

Run: 2026-11-17 01:39 local, HEAD `caa37d0`. Read-only, CPU. Scripts:
`scratch/fable_architecture/.n2/{inspect,classify,diagnose,lineage_final,emit_table}.py`.
Inputs: `scratch/fable_architecture/.fable/rows.pkl` (3,802 rows / 75 runs), the 75
`runs/<id>/config.yaml` snapshots, `.fable/rows.pkl` best rows, `.x5/lineage.json` (extended, not
redone), `docs/queue/HOME_18H_PLAN_2026-11-16.md`, `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md`,
`runs/nights/**/*.yaml` dated 2026-11-15..17, and grep-only hits in `docs/CONTINUITY.md`.

## Headline

- **17 of 21 lanes carry owner evidence; 4 have no evidence found** (ext-throat H/V-law, OSSE
  rounded-rect, section-pucker pilot, wide radial-relief orphan).
- **Of 75 runs: 58 hand-written seed, 16 best design of an earlier run, 1 warm start, 0 unknown.**
- **15 of the 17 parented runs are "seeded"** (first valid row within 0.17 J of the parent's best).
  The two exceptions are the fold-added seed (0.30 J worse) and the H-only A/B (0.26 J worse).

## Result table — lanes and owner requests

Denominator: **21 lanes** (all config families present in the 75-run inventory). "yes
(family-level)" means the owner request names the family or the family's published source, not this
exact cell; the distinction is repeated in *What failed / what is unknown*. No owner-requested lane
is recommended for cutting.

| Lane (configs in the inventory) | Owner-requested | Evidence (file:line and exact line) |
|---|---|---|
| `hl__ext_throat_hvlaw_v7`, `_v8` | no evidence found | `docs/queue/HOME_18H_PLAN_2026-11-16.md:152-153`: "Dropped: ext-throat H/V-law v7/v8 ... (owner: not grounded in a published horn)". No request line found; the owner direction is a drop. |
| `hl__ath_core_petal_hvlaw_v7` | yes | `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md:5`: "Owner direction (15 Nov): ... more BoTorch and more interesting shapes (ATH-style ripples/petals/ridges, salmon, Le Cléac'h, X)." |
| `hl__osse_rrect_morph_v7`, `_v8` | no evidence found | `docs/queue/HOME_18H_PLAN_2026-11-16.md:152-154`: owner dropped OSSE rounded-rect v8, "best design's isobars look worse than its seed". Owner preferred the v7 design (`hl__osse_rrect_fold_warm_v7.yaml:1-2`) but no request line found. |
| `hl__es_style_rollback_v7` | yes | `runs/nights/home_landscape_c_2026-11-15.yaml:5`: "ES-600-style exponential rollback (owner request; josephcrowe.com technical library)." |
| `hl__biradial_es_style_v7`, `_smooth_v7` | yes | `runs/nights/home_landscape_c_2026-11-15.yaml:5`: "ES450-style Bi-Radial ... (owner request; josephcrowe.com technical library)"; `runs/nights/home18_a_2026-11-16.yaml:68`: "A/B: bi-radial on the smooth brief (owner: is this ES-mouth variant really CD?)". |
| `hl__lecleach_iwata_ar_landscape_v7`, `_smooth_v7` | yes | `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md:5`: "Le Cléac'h". The construction was later replaced by owner direction (`HOME_18H_PLAN_2026-11-16.md:219-235`), not the lane withdrawn. |
| `rr__reference_v7`, `rr__pucker_hv_moderate_v7`, `rr__pucker_hv_strong_v7`, `rr__crowe_panel_es600_v7` | yes | `runs/nights/home_rolled_rect_2026-11-15.yaml:1`: "Owner-authorized 2026-11-15: closest Crowe-family seed, then short H+V pucker arms." |
| `sp__control_v7`, `sp__moderate_v7`, `sp__strong_v7` | no evidence found | No owner line in `docs/CONTINUITY.md:969-990` or the night YAML. It is a canonicalisation/verification check of the Crowe-section family. |
| `hl__crowe_panel_home_v7` | yes | `runs/nights/home_landscape_e_2026-11-15.yaml:8,21`: "Home-sized Crowe ES-600 family (owner: keep Crowe, make it work)"; `docs/CONTINUITY.md:1233`: "owner overruled (14:42): keep the Crowe jobs and make them work." |
| `hl__rolled_es_spiral_v7` | yes (family-level) | `examples/typologies/home_landscape_2026-11-15/hl__rolled_es_spiral_v7.yaml:1`: "HOME CROWE ES-STYLE EXPONENTIAL-SPIRAL ROLLED RECTANGLE"; `docs/CONTINUITY.md:1109-1110`: admission approved at gate level but "`full_search_released` remains **false**". No lane-specific request line; owner held full release. |
| `rf__rect_radial_wide_v7` | no evidence found | `docs/queue/HOME_18H_PLAN_2026-11-16.md:92`: "`rf__rect_radial_wide_v7` (orphan partial run ... owner decides)". A pending owner decision, not a request. |
| `rf__section_axial_home_v7`, `_smooth_v8` | yes (family-level) | `runs/nights/home_landscape_e_2026-11-15.yaml:8,21`: owner keep Crowe; config header `rf__section_axial_home_smooth_v8.yaml:4`: "Digitized Crowe ES sections." |
| `hl__crowe_x_square_v7` | yes (family-level) | `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md:5`: "X"; `runs/nights/home_landscape_e_2026-11-15.yaml:8,21` and `docs/CONTINUITY.md:1233`: keep Crowe / make it work. |
| `hl__lecleach_hv_landscape_smooth_v7` | yes | `runs/nights/home18_b_2026-11-16.yaml:44-47`: "Le Cleac'h H/V pair, REPAIRED 2026-11-16 (item 13, owner-approved renders) ... Owner seed = option 12"; config `examples/typologies/home_landscape_2026-11-15/hl__lecleach_hv_landscape_smooth_v7.yaml:73`: "owner-picked seed 12 2026-11-16". |
| `hl__ath_tritonia_landscape_v7`, `_v8`, `_v9` | yes | `runs/nights/home18_a_2026-11-16.yaml:11`: "ATH OSSE + MERIDIAN FOLD (inserted ~22:55, owner): published Tritonia / TwinRay-380 seeds + warm start"; `docs/CONTINUITY.md:757-781`: owner verdict on the v7 run and "skip them, fix, put them back". |
| `hl__ath_twinray380_landscape_v8` | yes | `runs/nights/home18_a_2026-11-16.yaml:11`: "published Tritonia / TwinRay-380 seeds + warm start" inserted by the owner. |
| `hl__rosse_rect_cd_v7` | yes | `runs/nights/rosse_r120_2026-11-16.yaml:2`: "launched detached because the owner asked for a 120-solve run"; `rosse_r50_refine_2026-11-17.yaml:2`: "Owner paused the 120-run and asked to restart from the best seed ...". |
| `hl__crowe_x_osse_cd_v7` | yes (family-level) | `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md:5`: "X"; `runs/nights/home_landscape_e_2026-11-15.yaml:8,21` / `docs/CONTINUITY.md:1233`: keep Crowe / make it work. |
| `hl__osse_rrect_fold_warm_v7` | yes | `runs/nights/home18_a_2026-11-16.yaml:11`: "ATH OSSE + MERIDIAN FOLD (inserted ~22:55, owner)". |
| `hl__klangfilm_lame_curved_v1` (+ seed variants) | yes | `docs/CONTINUITY.md:703`: "Klangfilm elliptical horn (owner-supplied `Klangfilm_Elliptical_Horn_Calculator_diy_v10.xlsm`)"; `examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1_seedP1.yaml:1`: "SEED P1 (owner structured seed set 2026-11-16)"; `_seedE2.yaml:1`: "SEED E2 (owner 2026-11-16, rev 3)". |
| `klangfilm_hv__a0_exact_incumbent_control`, `a1_h_only_single_axis`, `a2_v_only_single_axis` | yes (session-note basis) | `docs/CONTINUITY.md:703` records the owner-supplied Klangfilm calculator; `examples/typologies/klangfilm_hv_2026-11-16/configs/a0.yaml:1`: "Phase A Klangfilm-Lame H/V throat core". The H/V A/B was owner-directed on 2026-11-16 per the session note in the task brief; no file line states the request itself. |

Counts: **17 yes / 4 no evidence found** of 21 lanes.

## Result table — run lineage (75 runs)

Denominator: **75 runs**. Every run is classified; **0 unknown**. "Earlier run best" means
`config.yaml` `seed_params` matched the earlier run's best row within 1e-6, or a contemporaneous
config comment names that run as the seed source. "Hand-written seed" means the start is the
config's declared `seed_params` and does not match an earlier solved best within 1e-6 (it may still
be a published or owner-authored design). `search.seed` was read for every run and is recorded in
`.n2/lineage_final.json`; it is the CMA random seed and carries no design provenance, so it does
not change a category. "Seeded?" applies only where a parent exists; it is
`first valid row J <= parent best + 0.17`.

| Run | Config | Start came from | Parent (parent best J) | First valid J | Seeded? | Evidence |
|---|---|---|---|---:|---|---|
| 20261115T143219Z-screen-d3a1bb | `hl__ext_throat_hvlaw_v7` | hand-written seed | — | 6.8268 | — | config `seed_params`, no earlier-run match |
| 20261115T150043Z-screen-d1ebf6 | `hl__ext_throat_hvlaw_v7` | hand-written seed | — | 6.8268 | — | config `seed_params`, no earlier-run match |
| 20261115T152510Z-screen-a504f6 | `hl__ath_core_petal_hvlaw_v7` | hand-written seed | — | 8.6831 | — | config `seed_params`, no earlier-run match |
| 20261115T154322Z-screen-07bea2 | `hl__osse_rrect_morph_v7` | hand-written seed | — | 8.2747 | — | config `seed_params`, no earlier-run match |
| 20261115T161238Z-screen-1b1b6e | `hl__es_style_rollback_v7` | hand-written seed | — | 23.0084 | — | config `seed_params`, no earlier-run match |
| 20261115T162331Z-screen-2ac841 | `hl__biradial_es_style_v7` | hand-written seed | — | n/a | — | config `seed_params`, no earlier-run match |
| 20261115T162516Z-screen-e31b23 | `hl__lecleach_iwata_ar_landscape_v7` | hand-written seed | — | 21.5410 | — | config `seed_params`, no earlier-run match |
| 20261115T163824Z-screen-d4a7c4 | `rr__reference_v7` | hand-written seed | — | 30.3624 | — | config `seed_params`, no earlier-run match |
| 20261115T164910Z-screen-f94955 | `rr__pucker_hv_moderate_v7` | hand-written seed | — | 29.4472 | — | config `seed_params`, no earlier-run match |
| 20261115T165937Z-screen-4d8a33 | `rr__pucker_hv_strong_v7` | hand-written seed | — | 28.5030 | — | config `seed_params`, no earlier-run match |
| 20261115T171150Z-screen-d66ffb | `rr__crowe_panel_es600_v7` | hand-written seed | — | 23.0859 | — | config `seed_params`, no earlier-run match |
| 20261115T180109Z-screen-0f2ab5 | `sp__control_v7` | hand-written seed | — | 23.1980 | — | config `seed_params`, no earlier-run match |
| 20261115T181250Z-screen-1e22a5 | `sp__moderate_v7` | hand-written seed | — | 23.6499 | — | config `seed_params`, no earlier-run match |
| 20261115T182340Z-screen-35c541 | `sp__strong_v7` | hand-written seed | — | 24.4650 | — | config `seed_params`, no earlier-run match |
| 20261115T194455Z-screen-bf9fc8 | `rr__crowe_panel_es600_v7` | hand-written seed | — | 23.0859 | — | config `seed_params`, no earlier-run match |
| 20261115T205453Z-screen-32f7c4 | `hl__crowe_panel_home_v7` | hand-written seed | — | 17.9622 | — | config `seed_params`, no earlier-run match |
| 20261115T213849Z-screen-c35ad4 | `hl__crowe_panel_home_v7` | hand-written seed | — | 17.9622 | — | config `seed_params`, no earlier-run match |
| 20261116T001222Z-screen-b25d61 | `hl__rolled_es_spiral_v7` | hand-written seed | — | 29.9151 | — | config `seed_params`, no earlier-run match |
| 20261116T003142Z-screen-981f59 | `hl__rolled_es_spiral_v7` | hand-written seed | — | 29.9151 | — | config `seed_params`, no earlier-run match |
| 20261116T005943Z-screen-20db0d | `rf__rect_radial_wide_v7` | hand-written seed | — | 33.3415 | — | config `seed_params`, no earlier-run match |
| 20261116T015510Z-screen-e75ec8 | `rf__section_axial_home_v7` | hand-written seed | — | 17.9511 | — | config `seed_params`, no earlier-run match |
| 20261116T020629Z-screen-0d29d7 | `rf__section_axial_home_v7` | hand-written seed | — | 17.9511 | — | config `seed_params`, no earlier-run match |
| 20261116T021728Z-screen-3943f0 | `hl__crowe_x_square_v7` | hand-written seed | — | 9.2356 | — | config `seed_params`, no earlier-run match |
| 20261116T022328Z-screen-87354c | `hl__crowe_x_square_v7` | hand-written seed | — | 9.2356 | — | config `seed_params`, no earlier-run match |
| 20261116T025728Z-screen-cd60f7 | `hl__ext_throat_hvlaw_v8` | earlier run best | `20261115T143219Z-screen-d3a1bb` (3.1028) | 3.1028 | yes | examples/typologies/home_landscape_2026-11-15/hl__ext_throat_hvlaw_v8.yaml:6 — Seed = family best; new n at old fixed 6 |
| 20261116T030920Z-screen-5d1082 | `hl__osse_rrect_morph_v8` | earlier run best | `20261115T154322Z-screen-07bea2` (3.9918) | 3.9917 | yes | examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_morph_v8.yaml:5-6 — Seed = family best (J 3.992) |
| 20261116T034337Z-screen-eeef98 | `hl__lecleach_iwata_ar_landscape_smooth_v7` | hand-written seed | — | 9.3338 | — | config `seed_params`, no earlier-run match |
| 20261116T035652Z-screen-e30021 | `hl__ath_tritonia_landscape_v7` | hand-written seed | — | 32.7642 | — | config `seed_params`, no earlier-run match |
| 20261116T035949Z-screen-3e49ce | `hl__lecleach_iwata_ar_landscape_smooth_v7` | earlier run best | `20261116T034337Z-screen-eeef98` (7.0020) | 7.0189 | yes | examples/typologies/home_landscape_2026-11-15/hl__lecleach_iwata_ar_landscape_smooth_v7.yaml:5 — seed = its best after widening |
| 20261116T040157Z-screen-402831 | `hl__lecleach_hv_landscape_smooth_v7` | hand-written seed | — | 9.1889 | — | config `seed_params`, no earlier-run match |
| 20261116T040651Z-screen-e53ae9 | `hl__lecleach_hv_landscape_smooth_v7` | hand-written seed | — | 9.3352 | — | config `seed_params`, no earlier-run match |
| 20261116T041232Z-screen-b5380a | `hl__ath_tritonia_landscape_v7` | hand-written seed | — | 32.7642 | — | config `seed_params`, no earlier-run match; mechanical match is the parent run's own authored seed (20261116T035652Z-screen-e30021), not a searched best |
| 20261116T043544Z-screen-dd15d8 | `rf__section_axial_home_smooth_v8` | earlier run best | `20261116T020629Z-screen-0d29d7` (17.3970) | 7.0459 | yes | examples/typologies/rolled_family_2026-11-15/rf__section_axial_home_v8.yaml:7 — Seed = 25x2 pilot best (J 17.397) |
| 20261116T044917Z-screen-12eb61 | `hl__ath_tritonia_landscape_v8` | hand-written seed | — | 26.9033 | — | config `seed_params`, no earlier-run match |
| 20261116T052759Z-screen-44001e | `hl__ath_twinray380_landscape_v8` | hand-written seed | — | 11.4004 | — | config `seed_params`, no earlier-run match |
| 20261116T054705Z-screen-570bc6 | `hl__ath_tritonia_landscape_v8` | hand-written seed | — | 26.9033 | — | config `seed_params`, no earlier-run match |
| 20261116T060140Z-screen-679c6f | `hl__ath_twinray380_landscape_v8` | hand-written seed | — | 11.4004 | — | config `seed_params`, no earlier-run match |
| 20261116T061215Z-screen-058f0d | `hl__biradial_es_style_v7` | hand-written seed | — | 7.7759 | — | config `seed_params`, no earlier-run match |
| 20261116T064438Z-screen-8defc1 | `hl__rosse_rect_cd_v7` | hand-written seed | — | 9.6952 | — | config `seed_params`, no earlier-run match |
| 20261116T065413Z-screen-a70423 | `hl__crowe_x_osse_cd_v7` | hand-written seed | — | 6.0640 | — | config `seed_params`, no earlier-run match |
| 20261116T071520Z-screen-1c8608 | `hl__biradial_es_style_v7` | hand-written seed | — | 7.7759 | — | config `seed_params`, no earlier-run match |
| 20261116T073857Z-screen-7b9313 | `hl__rosse_rect_cd_v7` | hand-written seed | — | 9.6952 | — | config `seed_params`, no earlier-run match |
| 20261116T074832Z-screen-620f81 | `hl__crowe_x_osse_cd_v7` | hand-written seed | — | 6.0640 | — | config `seed_params`, no earlier-run match |
| 20261116T081139Z-screen-63158a | `hl__biradial_es_style_smooth_v7` | hand-written seed | — | 6.1299 | — | config `seed_params`, no earlier-run match |
| 20261116T085415Z-screen-0a228d | `hl__osse_rrect_fold_warm_v7` | earlier run best | `20261115T154322Z-screen-07bea2` (3.9918) | 4.2885 | no | examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_fold_warm_v7.yaml:1-4 — WARM START: v7 best (J 3.992) with meridian fold added |
| 20261116T090751Z-screen-37b115 | `hl__biradial_es_style_v7` | hand-written seed | — | 7.7759 | — | config `seed_params`, no earlier-run match |
| 20261116T093400Z-screen-56681d | `hl__rosse_rect_cd_v7` | hand-written seed | — | 9.6952 | — | config `seed_params`, no earlier-run match |
| 20261116T095336Z-screen-7fc9b7 | `hl__crowe_x_osse_cd_v7` | hand-written seed | — | 6.0640 | — | config `seed_params`, no earlier-run match |
| 20261116T130335Z-screen-ab4fb9 | `hl__osse_rrect_fold_warm_v7` | earlier run best | `20261116T085415Z-screen-0a228d` (3.7619) | 3.7619 | yes | seed_params match <= 1e-6; matched best row J 3.7619 |
| 20261116T131710Z-screen-f1a263 | `hl__osse_rrect_fold_warm_v7` | earlier run best | `20261116T130335Z-screen-ab4fb9` (3.7619) | 3.7619 | yes | seed_params match <= 1e-6; matched best row J 3.7619 |
| 20261116T145634Z-screen-e4c778 | `hl__rosse_rect_cd_v7` | earlier run best | `20261116T093400Z-screen-56681d` (4.8915) | 4.8908 | yes | examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7.yaml:12 — seed = best of 56681d (J 4.892) |
| 20261116T150941Z-screen-0e777a | `hl__rosse_rect_cd_v7` | earlier run best | `20261116T093400Z-screen-56681d` (4.8915) | 4.8908 | yes | examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7.yaml:12 — reuses the same config seed = best of 56681d (J 4.892) |
| 20261116T152544Z-screen-5f7d93 | `hl__crowe_x_osse_cd_v7` | earlier run best | `20261116T074832Z-screen-620f81` (5.3442) | 5.3454 | yes | seed_params match <= 1e-6; matched best row J 5.3442 |
| 20261116T153619Z-screen-c221aa | `hl__osse_rrect_fold_warm_v7` | earlier run best | `20261116T130335Z-screen-ab4fb9` (3.7619) | 3.7619 | yes | seed_params match <= 1e-6; matched best row J 3.7619 |
| 20261116T173311Z-screen-96f899 | `hl__ath_twinray380_landscape_v8` | earlier run best | `20261116T052759Z-screen-44001e` (5.5168) | 5.5167 | yes | seed_params match <= 1e-6; matched best row J 5.5168 |
| 20261116T193501Z-screen-f008ad | `hl__biradial_es_style_smooth_v7` | hand-written seed | — | 6.1299 | — | config `seed_params`, no earlier-run match |
| 20261116T205942Z-screen-8b22b5 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 12.1851 | — | config `seed_params`, no earlier-run match |
| 20261116T211549Z-screen-efe311 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 11.4017 | — | config `seed_params`, no earlier-run match |
| 20261116T211730Z-screen-7f3f2d | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 13.5351 | — | config `seed_params`, no earlier-run match |
| 20261116T211824Z-screen-45c843 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 13.5351 | — | config `seed_params`, no earlier-run match |
| 20261116T213830Z-screen-51fcfe | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 12.2694 | — | config `seed_params`, no earlier-run match |
| 20261116T214706Z-screen-c2febb | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 13.6700 | — | config `seed_params`, no earlier-run match |
| 20261116T220542Z-screen-cceac4 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 14.7372 | — | config `seed_params`, no earlier-run match |
| 20261116T221948Z-screen-7491e0 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 11.2392 | — | config `seed_params`, no earlier-run match |
| 20261116T222251Z-screen-91ddfb | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 10.0039 | — | config `seed_params`, no earlier-run match |
| 20261116T222556Z-screen-a2e7c7 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 9.7825 | — | config `seed_params`, no earlier-run match |
| 20261116T223230Z-screen-ac9b75 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 15.1570 | — | config `seed_params`, no earlier-run match |
| 20261116T224336Z-screen-55f39d | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 16.8965 | — | config `seed_params`, no earlier-run match |
| 20261116T225543Z-screen-6acf41 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 18.9362 | — | config `seed_params`, no earlier-run match |
| 20261116T230549Z-screen-e70608 | `hl__klangfilm_lame_curved_v1` | hand-written seed | — | 14.7880 | — | config `seed_params`, no earlier-run match |
| 20261117T001240Z-screen-7b664f | `hl__ath_twinray380_landscape_v8` | earlier run best | `20261116T173311Z-screen-96f899` (5.1794) | 5.1793 | yes | seed_params match <= 1e-6; matched best row J 5.1794 |
| 20261117T003115Z-screen-4f7cd5 | `hl__ath_tritonia_landscape_v9` | warm start | 12eb61 + 570bc6 (top-10 mean, sigma from spread) | 5.6873 | yes | `search.warm_start.from_runs` |
| 20261117T015442Z-screen-0afda0 | `klangfilm_hv__a0_exact_incumbent_control` | earlier run best | `20261116T205942Z-screen-8b22b5` (8.4390) | 8.4381 | yes | seed_params match <= 1e-6; matched best row J 8.4390 |
| 20261117T015600Z-screen-de1861 | `klangfilm_hv__a1_h_only_single_axis` | earlier run best | `20261116T205942Z-screen-8b22b5` (8.4390) | 8.6940 | no | seed_params match <= 1e-6; matched best row J 8.4390 |
| 20261117T015658Z-screen-7ffaad | `klangfilm_hv__a2_v_only_single_axis` | earlier run best | `20261116T205942Z-screen-8b22b5` (8.4390) | 8.5669 | yes | seed_params match <= 1e-6; matched best row J 8.4390 |

## Verdict against the brief's pass and failure lines

N2 has no numeric pass/fail line. Its stop condition is met: all **75/75** runs are classified and
**0** are unknown. The owner-confirmable protected-family list is the 21-lane table above, with 17
lanes carrying owner evidence and 4 marked "no evidence found". No owner-requested family is
recommended for cutting.

## What failed / what is unknown

- **The "hand-written" label is operational, not biographical.** It says the start is the config's
  declared seed and not an earlier solved best within 1e-6. It does not prove a human typed the
  numbers. Several are published or owner-authored designs (Tritonia T1 and TwinRay T3 published
  ATH scripts; Keele biradial; Crowe ES-600; Le Cléac'h references; the 14 Klangfilm runs, which
  are the base plus the owner's structured seed variants).
- **Strict 1e-6 matching is too tight for the recorded seeds.** Config `seed_params` are rounded to
  5-7 significant figures, and some rows re-derive `r0_mm`/`a0_deg`. Five documented seeds fail the
  1e-6 test and were resolved by a config comment instead: `cd60f7`, `5d1082`, `0a228d`, `3e49ce`,
  `dd15d8`. Without those comments they would be "unknown". The affected diff is up to 3.7e-4 on a
  254.9 mm length; `r0_mm` differs by 3.03 mm because the generator re-derives it.
- **One mechanical parent match was rejected.** `b5380a`'s seed matches `e30021`'s only valid row
  within 1e-6, but that row is the same authored Tritonia seed, not a searched best. It is therefore
  counted as a hand-written seed. `0e777a` is the opposite case: its seed is the config seed =
  `56681d`'s best, so it is counted as an earlier-run best even though the literal match was to
  `e4c778`'s seed row.
- **One "seeded" verdict is cross-brief and not a J comparison.** `dd15d8` is on the smooth brief
  while its parent `0d29d7` is on the base brief; its 7.0459 J is within 0.17 of 17.397 only because
  the J scales differ. Marked "yes" mechanically, not as evidence of continuity.
- **Owner-request evidence is family-level for four yes rows**: rolled ES spiral, section-axial-home,
  Crowe-X square, Crowe-X OSSE CD. The owner lines name the Crowe/X family, not those exact cells.
  The spiral also has owner-held full release (`full_search_released: false`), so "owner-requested"
  should not be read as a search mandate.
- **Klangfilm H/V has no file line that states the request.** The basis is the task's session note
  plus the owner-supplied Klangfilm calculator (CONTINUITY 703) and the Phase A H/V config header.
  This is the one yes row whose evidence is not a quoted request line.
- **Two lanes have owner counter-evidence, not a request**: ext-throat H/V-law (owner dropped it as
  not grounded in a published horn) and OSSE rounded-rect (owner dropped the v8, preferring the v7
  design). They are marked "no evidence found"; this does not label the underlying typology
  invalid.
- **The inventory stops at 2026-11-17T01:56Z.** Later 2026-11-17 runs (ROSSE r120/r50, Klangfilm
  Phase B) are not in `rows.pkl`. The ROSSE lane is marked yes from the later owner request, but its
  in-inventory runs predate that request. No claim is made about runs outside the 75.
- **`.x5/lineage.json` is not identical to this table.** `.x5` compared the first row's `params`
  (or `knobs`) at 1e-5 relative; this table compares `config.yaml` `seed_params` at 1e-6. The match
  sets therefore differ. `.x5` was reused for its classification of run starts and the 0.17
  "within noise" field, not assumed to be complete.

## What this does not prove

- It does not prove owner intent, only that a request/authorisation line exists. A lane with no
  evidence may still have been discussed verbally.
- It does not prove a seed was the first evaluated design. Two runs have first-row params different
  from `seed_params` (`d3a1bb`, `cd60f7`); the config comments attribute this to per-design
  `r0`/`a0` re-derivation, not a hidden warm start.
- It does not prove acoustic lineage, convergence, or that a seeded run "continued" its parent. The
  0.17 J check is start proximity only.
- It does not rank or validate any family. J is not comparable across briefs (base vs smooth vs
  ROSSE briefing) or objective versions.
- It does not establish that the 17 owner-evidenced lanes are exhaustive for the whole project; it
  covers the 75 runs in `rows.pkl` and the 2026-11-15..17 planning sources named in the brief.
- It does not prove the four "no evidence found" lanes are owner-disliked; it only records that no
  request line was found in the named sources.

## Next action enabled

The owner can confirm or correct the 21-lane protected list, especially the four "no evidence
found" lanes, the four family-level yes rows, and the Klangfilm H/V session-note row. The run-level parent map is then available for
sibling grouping (E2/X3), "which family earned its data" reads, and any later warm-start inventory.
No solve, queue change, config edit or git mutation is needed.

## Reproduce

```powershell
.venv\Scripts\python.exe scratch\fable_architecture\.n2\inspect.py
.venv\Scripts\python.exe scratch\fable_architecture\.n2\classify.py
.venv\Scripts\python.exe scratch\fable_architecture\.n2\diagnose.py
.venv\Scripts\python.exe scratch\fable_architecture\.n2\lineage_final.py
.venv\Scripts\python.exe scratch\fable_architecture\.n2\emit_table.py
```

Outputs: `.n2/config_dump.json`, `.n2/classify.json`, `.n2/lineage_final.json`,
`.n2/lineage_table.md`. All script writes are under `scratch/fable_architecture/.n2/`; the only
other write is this report. No GPU/BEM solve, no solving CLI command, no pytest, no process
control, no git mutation.
