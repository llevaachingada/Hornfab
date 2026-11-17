# CORRIDOR_RERANK

- Repo HEAD at run: `207f97a29e2f2f31a366da95e882f9b48761ab00`
- Timestamp: `2026-11-16T22:59:09-0500`
- Read-only against `runs/`; no solve, mesher, GPU, queue or config write.
- Scope: **3414** ok rows from **75** landscape runs / **35** configs (80x50, 600x480x480, 2026-11-15 onward).
- v7 baseline: the standard landscape brief `room_landscape_80x50_700_hf1440_v7` applied to every row (not each row's own variant). Metrics are read from each design's stored `metrics.json`; their `di_db` is the sin(theta)-weighted theta-phi balloon DI recorded by the solve path (parity-exact against the stored J).
- v9 candidates are **placeholders awaiting the owner's choice**; they live under `.tmp/v9_candidates/`, not `examples/`. Only the V onset differs (700 / 1,000 / 1,250 Hz); H is 60-90 deg from 700 Hz in all three. `cov_below_f0: one_sided` means a wide pattern below onset is free while a narrow one is charged.
- v9 J is **not numerically comparable** to v7 J: the term sets differ (v9 drops weighted `di`/`distd`, adds `di_roughness`, and scores a corridor). Only ranks and overlaps are compared.

## Top-20 overlap with v7

| candidate | rows valid | top-20 overlap | Spearman within v7 top 100 | v9-penalised rows |
|---|---|---|---|---|
| V onset 700 Hz | 3414 | 4/20 | 0.266 | 0 |
| V onset 1000 Hz | 3414 | 4/20 | 0.292 | 0 |
| V onset 1250 Hz | 3414 | 4/20 | 0.294 | 0 |

**Reading (important confound).** All three candidate top-20 sets are the **same 20 rows**; the V onset only shifts their v9 J by <0.05 and swaps the last two positions. The 4/20 overlap with v7 is therefore **not** caused by the corridor onset. It is driven by the v9 term-set change: v9 drops weighted `di` and `distd`, adds `di_roughness`, and scores the corridor instead of a point target. The clearest evidence is that two `hl__osse_rrect_morph_v7` rows ranked **461** and **497** under v7 enter the v9 top 20; their v7 J is dominated by terms v9 does not weight. Literal answer: corridor **presence** (v9 vs v7) is a first-order change (top 20 moves to 4/20 overlap), while the **V-onset choice** is a refinement (top 20 unchanged). Do not attribute the movement to the corridor shape alone, because this test does not hold the term set constant.

### Candidate V onset 700 Hz

Top 20 under the candidate (v7 rank in brackets):

| # | row | J v9 | J v7 | v7 rank |
|---|---|---|---|---|
| 1 | `20261115T154322Z-screen-07bea2` #40 `436a4d221328` (hl__osse_rrect_morph_v7) | 1.192 | 5.645 | 461 |
| 2 | `20261115T154322Z-screen-07bea2` #23 `f369080ddcb1` (hl__osse_rrect_morph_v7) | 1.227 | 5.712 | 497 |
| 3 | `20261116T130335Z-screen-ab4fb9` #19 `688ffe811b6a` (hl__osse_rrect_fold_warm_v7) | 1.318 | 3.892 | 41 |
| 4 | `20261116T130335Z-screen-ab4fb9` #11 `507e7257c091` (hl__osse_rrect_fold_warm_v7) | 1.337 | 3.949 | 59 |
| 5 | `20261116T130335Z-screen-ab4fb9` #50 `78f599e8a1d2` (hl__osse_rrect_fold_warm_v7) | 1.360 | 4.032 | 81 |
| 6 | `20261116T153619Z-screen-c221aa` #1 `084fe296d123` (hl__osse_rrect_fold_warm_v7) | 1.375 | 3.777 | 20 |
| 7 | `20261115T154322Z-screen-07bea2` #21 `229fe0c31365` (hl__osse_rrect_morph_v7) | 1.392 | 5.565 | 436 |
| 8 | `20261116T130335Z-screen-ab4fb9` #64 `57fc83db6e71` (hl__osse_rrect_fold_warm_v7) | 1.404 | 3.673 | 8 |
| 9 | `20261116T130335Z-screen-ab4fb9` #55 `ced63c6a01a1` (hl__osse_rrect_fold_warm_v7) | 1.411 | 3.825 | 27 |
| 10 | `20261116T130335Z-screen-ab4fb9` #75 `1d4712edeba2` (hl__osse_rrect_fold_warm_v7) | 1.424 | 3.712 | 13 |
| 11 | `20261116T131710Z-screen-f1a263` #4 `30c8c4f07d1f` (hl__osse_rrect_fold_warm_v7) | 1.433 | 3.829 | 29 |
| 12 | `20261116T130335Z-screen-ab4fb9` #48 `455b8e0cf490` (hl__osse_rrect_fold_warm_v7) | 1.451 | 3.825 | 28 |
| 13 | `20261116T153619Z-screen-c221aa` #23 `b2db1f826a28` (hl__osse_rrect_fold_warm_v7) | 1.460 | 4.370 | 144 |
| 14 | `20261116T131710Z-screen-f1a263` #18 `1dac9f75cc1f` (hl__osse_rrect_fold_warm_v7) | 1.495 | 4.334 | 135 |
| 15 | `20261116T153619Z-screen-c221aa` #20 `2bdbb9f07658` (hl__osse_rrect_fold_warm_v7) | 1.514 | 3.847 | 32 |
| 16 | `20261116T130335Z-screen-ab4fb9` #66 `8a1211c9b5ee` (hl__osse_rrect_fold_warm_v7) | 1.518 | 4.081 | 94 |
| 17 | `20261116T131710Z-screen-f1a263` #10 `457bd54b9fde` (hl__osse_rrect_fold_warm_v7) | 1.524 | 4.223 | 113 |
| 18 | `20261116T130335Z-screen-ab4fb9` #58 `c96b118a99b6` (hl__osse_rrect_fold_warm_v7) | 1.538 | 4.624 | 187 |
| 19 | `20261116T153619Z-screen-c221aa` #22 `6d6dd332b282` (hl__osse_rrect_fold_warm_v7) | 1.548 | 3.621 | 6 |
| 20 | `20261116T130335Z-screen-ab4fb9` #59 `9e3a6b43bdbd` (hl__osse_rrect_fold_warm_v7) | 1.549 | 3.937 | 55 |

Configs moving more than three places (by best row per config):

| config | v7 rank | candidate rank | move |
|---|---|---|---|
| `hl__lecleach_iwata_ar_landscape_smooth_v7` | 26 | 17 | -9 |
| `hl__lecleach_hv_landscape_smooth_v7` | 24 | 16 | -8 |
| `hl__lecleach_iwata_ar_landscape_v7` | 25 | 19 | -6 |
| `hl__rosse_rect_cd_v7` | 6 | 11 | +5 |
| `hl__ath_tritonia_landscape_v7` | 15 | 10 | -5 |
| `hl__osse_rrect_morph_v7` | 5 | 1 | -4 |
| `hl__ath_twinray380_landscape_v8` | 7 | 3 | -4 |
| `hl__crowe_panel_home_v7` | 16 | 20 | +4 |
| `rf__section_axial_home_smooth_v8` | 17 | 21 | +4 |
| `rf__section_axial_home_v7` | 18 | 22 | +4 |
| `klangfilm_hv__a1_h_only_single_axis` | 23 | 27 | +4 |

### Candidate V onset 1000 Hz

Top 20 under the candidate (v7 rank in brackets):

| # | row | J v9 | J v7 | v7 rank |
|---|---|---|---|---|
| 1 | `20261115T154322Z-screen-07bea2` #40 `436a4d221328` (hl__osse_rrect_morph_v7) | 1.160 | 5.645 | 461 |
| 2 | `20261115T154322Z-screen-07bea2` #23 `f369080ddcb1` (hl__osse_rrect_morph_v7) | 1.189 | 5.712 | 497 |
| 3 | `20261116T130335Z-screen-ab4fb9` #19 `688ffe811b6a` (hl__osse_rrect_fold_warm_v7) | 1.286 | 3.892 | 41 |
| 4 | `20261116T130335Z-screen-ab4fb9` #11 `507e7257c091` (hl__osse_rrect_fold_warm_v7) | 1.305 | 3.949 | 59 |
| 5 | `20261116T130335Z-screen-ab4fb9` #50 `78f599e8a1d2` (hl__osse_rrect_fold_warm_v7) | 1.331 | 4.032 | 81 |
| 6 | `20261116T153619Z-screen-c221aa` #1 `084fe296d123` (hl__osse_rrect_fold_warm_v7) | 1.347 | 3.777 | 20 |
| 7 | `20261115T154322Z-screen-07bea2` #21 `229fe0c31365` (hl__osse_rrect_morph_v7) | 1.353 | 5.565 | 436 |
| 8 | `20261116T130335Z-screen-ab4fb9` #64 `57fc83db6e71` (hl__osse_rrect_fold_warm_v7) | 1.373 | 3.673 | 8 |
| 9 | `20261116T130335Z-screen-ab4fb9` #55 `ced63c6a01a1` (hl__osse_rrect_fold_warm_v7) | 1.379 | 3.825 | 27 |
| 10 | `20261116T130335Z-screen-ab4fb9` #75 `1d4712edeba2` (hl__osse_rrect_fold_warm_v7) | 1.391 | 3.712 | 13 |
| 11 | `20261116T131710Z-screen-f1a263` #4 `30c8c4f07d1f` (hl__osse_rrect_fold_warm_v7) | 1.400 | 3.829 | 29 |
| 12 | `20261116T130335Z-screen-ab4fb9` #48 `455b8e0cf490` (hl__osse_rrect_fold_warm_v7) | 1.413 | 3.825 | 28 |
| 13 | `20261116T153619Z-screen-c221aa` #23 `b2db1f826a28` (hl__osse_rrect_fold_warm_v7) | 1.431 | 4.370 | 144 |
| 14 | `20261116T131710Z-screen-f1a263` #18 `1dac9f75cc1f` (hl__osse_rrect_fold_warm_v7) | 1.462 | 4.334 | 135 |
| 15 | `20261116T153619Z-screen-c221aa` #20 `2bdbb9f07658` (hl__osse_rrect_fold_warm_v7) | 1.486 | 3.847 | 32 |
| 16 | `20261116T130335Z-screen-ab4fb9` #66 `8a1211c9b5ee` (hl__osse_rrect_fold_warm_v7) | 1.489 | 4.081 | 94 |
| 17 | `20261116T131710Z-screen-f1a263` #10 `457bd54b9fde` (hl__osse_rrect_fold_warm_v7) | 1.490 | 4.223 | 113 |
| 18 | `20261116T130335Z-screen-ab4fb9` #58 `c96b118a99b6` (hl__osse_rrect_fold_warm_v7) | 1.511 | 4.624 | 187 |
| 19 | `20261116T130335Z-screen-ab4fb9` #59 `9e3a6b43bdbd` (hl__osse_rrect_fold_warm_v7) | 1.520 | 3.937 | 55 |
| 20 | `20261116T153619Z-screen-c221aa` #22 `6d6dd332b282` (hl__osse_rrect_fold_warm_v7) | 1.523 | 3.621 | 6 |

Configs moving more than three places (by best row per config):

| config | v7 rank | candidate rank | move |
|---|---|---|---|
| `hl__lecleach_iwata_ar_landscape_smooth_v7` | 26 | 17 | -9 |
| `hl__lecleach_hv_landscape_smooth_v7` | 24 | 16 | -8 |
| `rf__section_axial_home_v7` | 18 | 24 | +6 |
| `hl__rosse_rect_cd_v7` | 6 | 11 | +5 |
| `hl__ath_tritonia_landscape_v7` | 15 | 10 | -5 |
| `hl__lecleach_iwata_ar_landscape_v7` | 25 | 20 | -5 |
| `hl__osse_rrect_morph_v7` | 5 | 1 | -4 |
| `hl__ath_twinray380_landscape_v8` | 7 | 3 | -4 |
| `rf__section_axial_home_smooth_v8` | 17 | 21 | +4 |

### Candidate V onset 1250 Hz

Top 20 under the candidate (v7 rank in brackets):

| # | row | J v9 | J v7 | v7 rank |
|---|---|---|---|---|
| 1 | `20261115T154322Z-screen-07bea2` #40 `436a4d221328` (hl__osse_rrect_morph_v7) | 1.160 | 5.645 | 461 |
| 2 | `20261115T154322Z-screen-07bea2` #23 `f369080ddcb1` (hl__osse_rrect_morph_v7) | 1.186 | 5.712 | 497 |
| 3 | `20261116T130335Z-screen-ab4fb9` #19 `688ffe811b6a` (hl__osse_rrect_fold_warm_v7) | 1.285 | 3.892 | 41 |
| 4 | `20261116T130335Z-screen-ab4fb9` #11 `507e7257c091` (hl__osse_rrect_fold_warm_v7) | 1.304 | 3.949 | 59 |
| 5 | `20261116T130335Z-screen-ab4fb9` #50 `78f599e8a1d2` (hl__osse_rrect_fold_warm_v7) | 1.331 | 4.032 | 81 |
| 6 | `20261116T153619Z-screen-c221aa` #1 `084fe296d123` (hl__osse_rrect_fold_warm_v7) | 1.347 | 3.777 | 20 |
| 7 | `20261115T154322Z-screen-07bea2` #21 `229fe0c31365` (hl__osse_rrect_morph_v7) | 1.351 | 5.565 | 436 |
| 8 | `20261116T130335Z-screen-ab4fb9` #64 `57fc83db6e71` (hl__osse_rrect_fold_warm_v7) | 1.372 | 3.673 | 8 |
| 9 | `20261116T130335Z-screen-ab4fb9` #55 `ced63c6a01a1` (hl__osse_rrect_fold_warm_v7) | 1.378 | 3.825 | 27 |
| 10 | `20261116T130335Z-screen-ab4fb9` #75 `1d4712edeba2` (hl__osse_rrect_fold_warm_v7) | 1.390 | 3.712 | 13 |
| 11 | `20261116T131710Z-screen-f1a263` #4 `30c8c4f07d1f` (hl__osse_rrect_fold_warm_v7) | 1.400 | 3.829 | 29 |
| 12 | `20261116T130335Z-screen-ab4fb9` #48 `455b8e0cf490` (hl__osse_rrect_fold_warm_v7) | 1.411 | 3.825 | 28 |
| 13 | `20261116T153619Z-screen-c221aa` #23 `b2db1f826a28` (hl__osse_rrect_fold_warm_v7) | 1.431 | 4.370 | 144 |
| 14 | `20261116T131710Z-screen-f1a263` #18 `1dac9f75cc1f` (hl__osse_rrect_fold_warm_v7) | 1.462 | 4.334 | 135 |
| 15 | `20261116T153619Z-screen-c221aa` #20 `2bdbb9f07658` (hl__osse_rrect_fold_warm_v7) | 1.486 | 3.847 | 32 |
| 16 | `20261116T130335Z-screen-ab4fb9` #66 `8a1211c9b5ee` (hl__osse_rrect_fold_warm_v7) | 1.488 | 4.081 | 94 |
| 17 | `20261116T131710Z-screen-f1a263` #10 `457bd54b9fde` (hl__osse_rrect_fold_warm_v7) | 1.490 | 4.223 | 113 |
| 18 | `20261116T130335Z-screen-ab4fb9` #58 `c96b118a99b6` (hl__osse_rrect_fold_warm_v7) | 1.511 | 4.624 | 187 |
| 19 | `20261116T130335Z-screen-ab4fb9` #59 `9e3a6b43bdbd` (hl__osse_rrect_fold_warm_v7) | 1.519 | 3.937 | 55 |
| 20 | `20261116T153619Z-screen-c221aa` #22 `6d6dd332b282` (hl__osse_rrect_fold_warm_v7) | 1.523 | 3.621 | 6 |

Configs moving more than three places (by best row per config):

| config | v7 rank | candidate rank | move |
|---|---|---|---|
| `hl__lecleach_iwata_ar_landscape_smooth_v7` | 26 | 17 | -9 |
| `hl__lecleach_hv_landscape_smooth_v7` | 24 | 16 | -8 |
| `rf__section_axial_home_v7` | 18 | 24 | +6 |
| `hl__rosse_rect_cd_v7` | 6 | 11 | +5 |
| `hl__ath_tritonia_landscape_v7` | 15 | 10 | -5 |
| `rf__section_axial_home_smooth_v8` | 17 | 22 | +5 |
| `hl__osse_rrect_morph_v7` | 5 | 1 | -4 |
| `hl__ath_twinray380_landscape_v8` | 7 | 3 | -4 |
| `hl__crowe_panel_home_v7` | 16 | 20 | +4 |

## Best row per config

| config | v7 best J | v700 best J | v1000 best J | v1250 best J |
|---|---|---|---|---|
| `hl__ath_core_petal_hvlaw_v7` | 5.322 | 1.912 | 1.865 | 1.863 |
| `hl__ath_tritonia_landscape_v7` | 11.177 | 3.095 | 3.066 | 3.065 |
| `hl__ath_tritonia_landscape_v8` | 5.692 | 2.517 | 2.509 | 2.509 |
| `hl__ath_tritonia_landscape_v9` | 5.015 | 2.703 | 2.696 | 2.696 |
| `hl__ath_twinray380_landscape_v8` | 4.914 | 1.568 | 1.555 | 1.555 |
| `hl__biradial_es_style_smooth_v7` | 6.835 | 4.846 | 4.798 | 4.795 |
| `hl__biradial_es_style_v7` | 6.447 | 5.090 | 5.054 | 5.054 |
| `hl__crowe_panel_home_v7` | 16.918 | 9.337 | 8.974 | 8.695 |
| `hl__crowe_x_osse_cd_v7` | 5.344 | 3.907 | 3.861 | 3.857 |
| `hl__crowe_x_square_v7` | 8.205 | 5.254 | 5.223 | 5.216 |
| `hl__es_style_rollback_v7` | 20.855 | 10.131 | 9.880 | 9.756 |
| `hl__ext_throat_hvlaw_v7` | 3.103 | 1.722 | 1.665 | 1.659 |
| `hl__ext_throat_hvlaw_v8` | 3.103 | 1.765 | 1.710 | 1.705 |
| `hl__klangfilm_lame_curved_v1` | 18.250 | 9.798 | 9.087 | 8.694 |
| `hl__lecleach_hv_landscape_smooth_v7` | 19.151 | 8.802 | 8.566 | 8.477 |
| `hl__lecleach_iwata_ar_landscape_smooth_v7` | 19.436 | 8.859 | 8.707 | 8.654 |
| `hl__lecleach_iwata_ar_landscape_v7` | 19.418 | 9.231 | 9.031 | 8.940 |
| `hl__osse_rrect_fold_warm_v7` | 3.621 | 1.318 | 1.286 | 1.285 |
| `hl__osse_rrect_morph_v7` | 3.992 | 1.192 | 1.160 | 1.160 |
| `hl__osse_rrect_morph_v8` | 3.924 | 1.931 | 1.898 | 1.898 |
| `hl__rolled_es_spiral_v7` | 17.707 | 9.169 | 8.854 | 8.671 |
| `hl__rosse_rect_cd_v7` | 4.563 | 3.235 | 3.200 | 3.198 |
| `klangfilm_hv__a0_exact_incumbent_control` | 18.248 | 9.798 | 9.158 | 8.735 |
| `klangfilm_hv__a1_h_only_single_axis` | 18.984 | 10.140 | 9.500 | 9.077 |
| `klangfilm_hv__a2_v_only_single_axis` | 18.518 | 9.965 | 9.326 | 8.902 |
| `rf__rect_radial_wide_v7` | 32.738 | 17.462 | 16.749 | 16.305 |
| `rf__section_axial_home_smooth_v8` | 17.105 | 9.416 | 9.044 | 8.736 |
| `rf__section_axial_home_v7` | 17.397 | 9.618 | 9.241 | 8.909 |
| `rr__crowe_panel_es600_v7` | 22.542 | 12.654 | 11.563 | 11.106 |
| `rr__pucker_hv_moderate_v7` | 28.434 | 15.160 | 14.619 | 14.287 |
| `rr__pucker_hv_strong_v7` | 27.407 | 14.544 | 14.060 | 13.718 |
| `rr__reference_v7` | 29.423 | 15.715 | 15.226 | 14.844 |
| `sp__control_v7` | 22.765 | 12.667 | 11.576 | 11.133 |
| `sp__moderate_v7` | 22.938 | 12.747 | 11.656 | 11.201 |
| `sp__strong_v7` | 23.794 | 13.293 | 12.202 | 11.721 |

## Candidate files

- `scratch/fable_architecture/.tmp/v9_candidates/candidate_v_onset_700.yaml`
- `scratch/fable_architecture/.tmp/v9_candidates/candidate_v_onset_1000.yaml`
- `scratch/fable_architecture/.tmp/v9_candidates/candidate_v_onset_1250.yaml`

_Script: `scratch/fable_architecture/.tmp/r3_corridor_rerank.py`; runtime 1658.9s._
