# SEED_SPREAD

- Repo HEAD at run: `207f97a29e2f2f31a366da95e882f9b48761ab00`
- Timestamp: `2026-11-16T22:59:37-0500`
- Read-only against `runs/`; no solve, mesher, GPU, queue or config write.
- Scope: the same 75 landscape-brief runs. Normalised config = all keys except `name`, `description`, `brief_file`, `feasibility`, `search.seed` and `seed_params`.
- Configs with at least three runs: **6**. Proceeding (>=4).
- Valid row = `ok`, finite numeric `objective`, and `objective < 900` (penalty excluded). Matched budget N = the smallest valid-row count in the config; each run uses its first N valid rows in `search.ndjson` order.

## Per-run table

| config | run | seed | start (seed_params) | valid rows | matched N | best J at N | best row | watchdog |
|---|---|---|---|---|---|---|---|---|
| `hl__klangfilm_lame_curved_v1` | `20261116T211824Z-screen-45c843` | 11021 | `{"g_aspect": 1.8, "g_end_frac": 1.45, "g_entry_half_angle…` | 57 | 22 | 9.070 | #20 `5b7700c7040c` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T213830Z-screen-51fcfe` | 11002 | `{"g_aspect": 1.72, "g_end_frac": 1.28, "g_entry_half_angl…` | 31 | 22 | 9.880 | #27 `149f0eb7b73a` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T214706Z-screen-c2febb` | 11003 | `{"g_aspect": 1.9, "g_end_frac": 1.48, "g_entry_half_angle…` | 49 | 22 | 11.384 | #24 `3899d7561e19` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T220542Z-screen-cceac4` | 11004 | `{"g_aspect": 1.75, "g_end_frac": 1.58, "g_entry_half_angl…` | 36 | 22 | 9.925 | #19 `a5d3438f7dc6` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T223230Z-screen-ac9b75` | 11005 | `{"g_aspect": 1.65, "g_end_frac": 1.1, "g_entry_half_angle…` | 54 | 22 | 10.210 | #14 `69502d1570cb` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T224336Z-screen-55f39d` | 11006 | `{"g_aspect": 1.7, "g_end_frac": 1.25, "g_entry_half_angle…` | 36 | 22 | 8.634 | #17 `563037821c92` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T225543Z-screen-6acf41` | 11007 | `{"g_aspect": 1.85, "g_end_frac": 1.2, "g_entry_half_angle…` | 40 | 22 | 12.298 | #12 `963e41ee33e6` | YES |
| `hl__klangfilm_lame_curved_v1` | `20261116T230549Z-screen-e70608` | 11008 | `{"g_aspect": 1.78, "g_end_frac": 1.02, "g_entry_half_angl…` | 22 | 22 | 9.434 | #28 `25e86d029e7d` | YES |
| `hl__ath_twinray380_landscape_v8` | `20261116T052759Z-screen-44001e` | 1234 | `{"L_mm": 200.0, "a0_deg": 2.0, "a_deg": 45.0, "aspect_rat…` | 50 | 30 | 5.517 | #11 `35485dfcedd0` | YES |
| `hl__ath_twinray380_landscape_v8` | `20261116T060140Z-screen-679c6f` | 5678 | `{"L_mm": 200.0, "a0_deg": 2.0, "a_deg": 45.0, "aspect_rat…` | 30 | 30 | 6.035 | #29 `2ce29244bb9e` | YES |
| `hl__ath_twinray380_landscape_v8` | `20261116T173311Z-screen-96f899` | 9012 | `{"L_mm": 211.498688, "a0_deg": 2.120982, "a_deg": 47.2851…` | 51 | 30 | 5.441 | #30 `47da4e0cd3ba` | no |
| `hl__biradial_es_style_v7` | `20261116T061215Z-screen-058f0d` | 1234 | `{"L_mm": 255.0, "h_a_deg": 36.0, "h_n": 5.0, "h_rm_mm": 2…` | 96 | 71 | 6.558 | #63 `27fe89821845` | no |
| `hl__biradial_es_style_v7` | `20261116T071520Z-screen-1c8608` | 5678 | `{"L_mm": 255.0, "h_a_deg": 36.0, "h_n": 5.0, "h_rm_mm": 2…` | 71 | 71 | 6.482 | #30 `5215af5401f9` | YES |
| `hl__biradial_es_style_v7` | `20261116T090751Z-screen-37b115` | 9012 | `{"L_mm": 255.0, "h_a_deg": 36.0, "h_n": 5.0, "h_rm_mm": 2…` | 142 | 71 | 6.643 | #41 `0004bf3995ed` | no |
| `hl__rosse_rect_cd_v7` | `20261116T064438Z-screen-8defc1` | 1234 | `{"g_a_diag_deg": 0.0, "g_a_h_deg": 40.0, "g_a_v_deg": 25.…` | 30 | 30 | 5.976 | #26 `22be80ea5a07` | YES |
| `hl__rosse_rect_cd_v7` | `20261116T073857Z-screen-7b9313` | 5678 | `{"g_a_diag_deg": 0.0, "g_a_h_deg": 40.0, "g_a_v_deg": 25.…` | 34 | 30 | 5.952 | #27 `b230ed907f05` | YES |
| `hl__rosse_rect_cd_v7` | `20261116T093400Z-screen-56681d` | 9012 | `{"g_a_diag_deg": 0.0, "g_a_h_deg": 40.0, "g_a_v_deg": 25.…` | 55 | 30 | 4.892 | #29 `4b1ce3e8b146` | YES |
| `hl__crowe_x_osse_cd_v7` | `20261116T065413Z-screen-a70423` | 1234 | `{"g_L_mm": 240.0, "g_a_h_deg": 38.0, "g_a_v_deg": 24.0, "…` | 58 | 19 | 5.997 | #19 `901d855c40c9` | YES |
| `hl__crowe_x_osse_cd_v7` | `20261116T074832Z-screen-620f81` | 5678 | `{"g_L_mm": 240.0, "g_a_h_deg": 38.0, "g_a_v_deg": 24.0, "…` | 64 | 19 | 5.965 | #19 `ffdea0c9c84f` | YES |
| `hl__crowe_x_osse_cd_v7` | `20261116T095336Z-screen-7fc9b7` | 9012 | `{"g_L_mm": 240.0, "g_a_h_deg": 38.0, "g_a_v_deg": 24.0, "…` | 19 | 19 | 5.691 | #24 `2c922317f1c7` | YES |
| `hl__osse_rrect_fold_warm_v7` | `20261116T130335Z-screen-ab4fb9` | 9012 | `{"L_mm": 255.830467, "a0_deg": 2.302789, "a_deg": 38.5002…` | 77 | 61 | 3.762 | #0 `8544e97bc940` | YES |
| `hl__osse_rrect_fold_warm_v7` | `20261116T131710Z-screen-f1a263` | 3456 | `{"L_mm": 255.830467, "a0_deg": 2.302789, "a_deg": 38.5002…` | 79 | 61 | 3.762 | #0 `8544e97bc940` | YES |
| `hl__osse_rrect_fold_warm_v7` | `20261116T153619Z-screen-c221aa` | 85012 | `{"L_mm": 255.830467, "a0_deg": 2.302789, "a_deg": 38.5002…` | 61 | 61 | 3.621 | #22 `6d6dd332b282` | no |

## Config spread and ranking gaps

| rank | config | runs | matched N | best J | median J | within spread | sd | watchdog runs |
|---|---|---|---|---|---|---|---|---|
| 1 | `hl__osse_rrect_fold_warm_v7` | 3 | 61 | 3.621 | 3.762 | 0.141 | 0.081 | 2/3 |
| 2 | `hl__rosse_rect_cd_v7` | 3 | 30 | 4.892 | 5.952 | 1.085 | 0.620 | 3/3 |
| 3 | `hl__ath_twinray380_landscape_v8` | 3 | 30 | 5.441 | 5.517 | 0.594 | 0.323 | 2/3 |
| 4 | `hl__crowe_x_osse_cd_v7` | 3 | 19 | 5.691 | 5.965 | 0.306 | 0.168 | 3/3 |
| 5 | `hl__biradial_es_style_v7` | 3 | 71 | 6.482 | 6.558 | 0.161 | 0.080 | 1/3 |
| 6 | `hl__klangfilm_lame_curved_v1` | 8 | 22 | 8.634 | 9.902 | 3.664 | 1.209 | 8/8 |

Adjacent gaps (rank order, best J): 1.271, 0.549, 0.250, 0.791, 2.152.

**Ratio: median within-config spread / median adjacent gap = 0.450 / 0.791 = 0.569.**

## Watchdog mapping

Where a run was restarted or resumed, more than one log line can map to it; the `evals`
count is the discriminator, and a `YES` in the table means at least one authoritative log
line says `watchdog` or `failed`. The evidence line for each flagged run is below.

- `20261116T043544Z-screen-dd15d8`: failed `c_section_sm` evals=0 (home_day2_2026-11-16_runner_stdout.log) — mapped by resume path in home_day_2026-11-16.yaml.
- `20261116T044917Z-screen-12eb61`: watchdog `a_tritonia2_s1234` evals=74 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T052759Z-screen-44001e`: watchdog `a_twinray2_s1234` evals=52 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T054705Z-screen-570bc6`: watchdog `a_tritonia2_s5678` evals=39 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T060140Z-screen-679c6f`: watchdog `a_twinray2_s5678` evals=31 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T064438Z-screen-8defc1`: watchdog `a_rosse_cd_s1234` evals=30 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T064438Z-screen-8defc1`: watchdog `d_rosse_s1234` evals=32 (home_day_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T065413Z-screen-a70423`: watchdog `a_crowex_cd_s1234` evals=65 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T065413Z-screen-a70423`: watchdog `d_crowex_s1234` evals=43 (home_day_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T071520Z-screen-1c8608`: watchdog `a_biradial_s5678` evals=71 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T073857Z-screen-7b9313`: watchdog `a_rosse_cd_s5678` evals=34 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T073857Z-screen-7b9313`: watchdog `d_rosse_s5678` evals=31 (home_day_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T074832Z-screen-620f81`: watchdog `a_crowex_cd_s5678` evals=78 (home18_a_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T085415Z-screen-0a228d`: watchdog `b_osse_fold_warm_s5678` evals=31 (home18_b_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T093400Z-screen-56681d`: watchdog `b_rosse_cd_s9012` evals=55 (home18_b_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T095336Z-screen-7fc9b7`: watchdog `b_crowex_cd_s9012` evals=28 (home18_b_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T130335Z-screen-ab4fb9`: watchdog `c_warm_s9012` evals=77 (home_day2_2026-11-16_runner_stdout.log) — mapped by resume path in home_day_2026-11-16.yaml.
- `20261116T131710Z-screen-f1a263`: watchdog `c_warm_s3456` evals=79 (home_day2_2026-11-16_runner_stdout.log) — mapped by resume path in home_day_2026-11-16.yaml.
- `20261116T145634Z-screen-e4c778`: watchdog `c_rosse_s1234` evals=76 (home_day2_2026-11-16_runner_stdout.log) — mapped by resume path in home_day_2026-11-16.yaml.
- `20261116T150941Z-screen-0e777a`: watchdog `c_rosse_s5678` evals=61 (home_day2_2026-11-16_runner_stdout.log) — mapped by resume path in home_day_2026-11-16.yaml.
- `20261116T152544Z-screen-5f7d93`: watchdog `c_crowex_s1234` evals=87 (home_day2_2026-11-16_runner_stdout.log) — mapped by resume path in home_day_2026-11-16.yaml.
- `20261116T205942Z-screen-8b22b5`: watchdog `k_lame_A_s1234` evals=30 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T211549Z-screen-efe311`: failed `k_lame_P1_s11001` evals=0 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T211730Z-screen-7f3f2d`: failed `k_lame_P1b_s11011` evals=0 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T211824Z-screen-45c843`: watchdog `k_lame_P1c_s11021` evals=65 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T213830Z-screen-51fcfe`: watchdog `k_lame_P2_s11002` evals=46 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T214706Z-screen-c2febb`: watchdog `k_lame_P3_s11003` evals=65 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T220542Z-screen-cceac4`: watchdog `k_lame_P4_s11004` evals=46 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T221948Z-screen-7491e0`: watchdog `k_lame_E2_s11031` evals=25 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T222251Z-screen-91ddfb`: watchdog `k_lame_E3_s11041` evals=26 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T222556Z-screen-a2e7c7`: watchdog `k_lame_V5_s11051` evals=37 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T223230Z-screen-ac9b75`: watchdog `k_lame_S1_s11005` evals=61 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T224336Z-screen-55f39d`: watchdog `k_lame_S2_s11006` evals=40 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T225543Z-screen-6acf41`: watchdog `k_lame_S3_s11007` evals=55 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261116T230549Z-screen-e70608`: watchdog `k_lame_S4_s11008` evals=35 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed.
- `20261117T001240Z-screen-7b664f`: watchdog `c_twin_wide_s9012` evals=30 (home_day2_2026-11-16_runner_stdout.log) — mapped by config path + cma seed + evals count.

Unmapped log entries (not attributed to a run):
- `a_lecleach_sm2_s1234` failed evals=0: no resume path and no config+seed match
- `a_lecleach_hv_s1234` failed evals=0: no resume path and no config+seed match
- `a_lecleach_hv2_s1234` failed evals=0: no resume path and no config+seed match
- `a_tritonia_s1234` failed evals=0: ambiguous (2 runs)
- `a_section_sm_s1234` watchdog evals=30: no resume path and no config+seed match
- `prep_b_turbo_tritonia` failed evals=0: no resume path and no config+seed match
- `b_turbo_tritonia` failed evals=0: no resume path and no config+seed match
- `prep_b_turbo_twinray` failed evals=0: no resume path and no config+seed match
- `b_turbo_twinray` failed evals=0: no resume path and no config+seed match
- `b_biradial_s9012` watchdog evals=82: no resume path and no config+seed match
- `ext_v9_cma_s89002` failed evals=0: no resume path and no config+seed match
- `ext_v9_turbo_first` failed evals=0: no resume path and no config+seed match
- `ext_v9_refine_cma` failed evals=0: no resume path and no config+seed match
- `ext_v9_turbo_followup` failed evals=0: no resume path and no config+seed match
- `ext_v9_scalar` failed evals=0: no resume path and no config+seed match
- `ext_ath_turbo_s86001` failed evals=0: no resume path and no config+seed match
- `ext_ath_scalar_s86001` failed evals=0: no resume path and no config+seed match
- `ext_core_turbo_s87001` failed evals=0: no resume path and no config+seed match
- `ext_core_scalar_s87001` failed evals=0: no resume path and no config+seed match
- `ext_ath_turbo_s86002` failed evals=0: no resume path and no config+seed match
- `ext_ath_scalar_s86002` failed evals=0: no resume path and no config+seed match
- `d_warm_s9012` watchdog evals=30: no resume path and no config+seed match
- `d_warm_s3456` watchdog evals=30: no resume path and no config+seed match
- `d_twin_s9012` watchdog evals=53: ambiguous (2 runs)
- `v_hlc_top3` failed evals=3: no resume path and no config+seed match
- `ath_a2_hex` failed evals=1: no resume path and no config+seed match
- `v_ath_a1_sf_only` failed evals=0: no resume path and no config+seed match

_Script: `scratch/fable_architecture/.tmp/r4_seed_spread.py`; runtime 1.5s._
