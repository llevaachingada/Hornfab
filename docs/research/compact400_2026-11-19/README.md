# compact400: horns inside a 400 mm cube, plus the next-10 queue (2026-11-19)

Fable senior lane, owner-directed ("make sure everything is ready for 10x next items to add to the
queue ... focus on best opportunities for improvement and new horns under a 400 mm cubed bounding
box"). **CPU only.** No BEM solve and no queue launch. No default, objective, historical identity or
stored run was changed. The night is **staged, not launched**, because GPU budget stays with the owner.

## 1. Why a new identity was needed (measured)

`scratch/fable_architecture/compact400_2026-11-19/scan_400cube.py` scans every stored solved
design whose **outer** bbox fits 400 × 400 × 400 mm. Summary: [`evidence/scan_400cube_summary.json`](evidence/scan_400cube_summary.json).

- **16,270** solved designs fit the cube.
- **At 850 Hz the corridor is mostly out of reach.** Only 273 designs hold H 60–100° with V ≤ 75° at 850 Hz; 4,587 do at 1 kHz.
- **Median V −6 dB beamwidth:** 106° at 850 Hz, 95° at 1 kHz, 81° at 1.25 kHz. The best 10 % reach ≤ 69° and ≤ 60°.
- **Only 2 qualifying designs have the 1.4-inch throat.** 393 designs meet V ≤ 75° at 1 kHz, V ≤ 70° at 1.25 kHz, H 60–100° at 1 kHz and lfp20 ≤ 625 Hz. Of those:
  - 375 are **2-inch (r0 25.4) ATH core-law** horns;
  - 2 are at the HF1440 1.4-inch exit, both `hl__ath_twinray380_landscape_v8`.
- **Conclusion:** the 1.4-inch horn inside a 400 mm cube is the least-explored cell in the archive.
- **The existing briefs don't fit this size:**
  - v10 and compact_xo900 use a 600 × 480 × 480 envelope and an 850 Hz onset;
  - no HF1440 brief with an envelope of 400 mm or less exists.

## 2. The brief identity

[`examples/briefs/compact400_2026-11-19/compact400_xo1000_1400_hf1440_v10xo.yaml`](../../../examples/briefs/compact400_2026-11-19/compact400_xo1000_1400_hf1440_v10xo.yaml)

It is built exactly like `compact_xo900`: the objective v10 scalar is unchanged and only the brief differs.

- **Envelope:** mouth W 400 and H 400, depth 385. The post-mesh gate adds 15 mm, so every admitted design is ≤ 400 mm on every axis, shell included.
- **F_X 1000 Hz.** Zero load penalty requires lfp20 ≤ 625 Hz.
- **Corridor:** H 60–100° (pref. 80) and V 40–75° (pref. 50), from 1 kHz, held from 1.4 kHz to 8 kHz.
- **Band 350–8000 Hz** is retained, with `cov_below_f0: one_sided`.
- **Identity rules:** it is never rankable against v7, v10, v10_slope5 or compact_xo900.

**Grounding (`hornlab-acoustic-grounding`).**
- The onset and corridor come from the solved population in §1, not from the Keele relation (KH-001: an empirical, Keele-scoped heuristic).
- The corridor is a chosen scoring target, not a CD law.
- **Applicability gap:** the population that justifies the 1 kHz onset is mostly 2-inch ATH. Whether a 1.4-inch throat matches it in this box is exactly what lanes c4_01–c4_08 measure.
- The 2° exit tangent is a source-model assumption (knowledge base, line 455).
- Every result is an ideal-source screen, not a real-driver or installed claim.

## 3. Floor (published)

| quantity | value |
|---|---|
| frequency part, top-28 screen→verify pairs (257 pairs) | 0.12911 J |
| mesh part (B1, fixed, `floor_record.json`) | 0.00768 J |
| **combined floor** | **0.1293 J** |

- **Command:** `rescore_identity.py floor --brief <brief> --runs-root runs --top 28 --out runs/analysis/compact400_floor_2026-11-19`. Exit 0. Output: [`evidence/floor/`](evidence/floor/).
- **Caveat:** the pairs come from the whole fleet, which is mostly 600 mm-class home horns. This is the score-consistency floor of this target set, not a repeatability floor measured on 400 mm horns.
- **Rule:** re-measure it once the compact400 lanes have their own screen→verify pairs. Until then, treat gains below about 0.13 J as ties.

## 4. The bar the new lanes must beat (CPU rescore, no solve)

`rescore_identity.py rescore` was run on 15 stored runs that contain HF1440 designs inside the cube. Output: [`evidence/rescore/`](evidence/rescore/).
- 1,281 designs were exact-complete; 978 of those fit the cube.
- 470 were not replayable (466 `record_not_ok`, 4 `target_regeneration_unsupported`).

| compact400 J | run config | design | W × H × D mm | H/V at 1 kHz | V at 1.25 kHz | lfp20 |
|---|---|---|---|---|---|---|
| **1.7302** | `hl__ath_twinray380_landscape_v8` | `bbe858b5b6a4` | 367 × 377 × 255 | 75 / 74 | 62 | 523 |
| 2.1441 | `gcurve__osse_b1w_v4` | `29db088d5512` | 351 × 291 × 157 | 81 / 96 | 86 | 643 |
| 2.1917 | `crease__osse_b1w_v4` | `db29e432869d` | 335 × 297 × 170 | 80 / 88 | 75 | 643 |
| 2.2250 | `control__osse_morph_b1w_v4` | `c44af5245e12` | 336 × 293 × 171 | 80 / 88 | 73 | 643 |
| 2.3114 | `control__osse_morph_b1w_round_v4` | `27b39f6bbc5c` | 335 × 291 × 219 | 76 / 84 | 69 | 500 |
| 3.5621 | `hl__ath_core_petal_hvlaw_v7` | `63659dcd0b16` | 376 × 333 × 315 | 76 / 85 | 69 | 387 |
| 7.9161 | `scout40__lecleach_iwata_ar_smooth_v7` | `752158259856` | 338 × 304 × 230 | 94 / 100 | 84 | 440 |

The October 90 × 60 horns lose on V because they are only about 290 mm tall. The TwinRay design is
the bar: **1.7302**, and a real win needs J ≤ 1.60.

## 5. The ten staged jobs

- **Night file:** [`docs/queue/compact400_next10_2026-11-19.yaml`](../../queue/compact400_next10_2026-11-19.yaml), with an admission file. `--dry-run` lists all ten.
- **Configs:** `examples/typologies/compact400_2026-11-19/`, generated deterministically by `scratch/fable_architecture/compact400_2026-11-19/make_configs.py`.
- **What the generator changes.** Each config is a loadable source config with only these changes:
  - name and brief;
  - search block: CMA, a valid-eval budget and a new seed;
  - seed taken from the family's best stored design;
  - the size knobs re-bounded: morph W 300–392, H 240–392, L 150–300;
  - the mouth morph switched on.

  Every other knob is inherited.
- **Refusal handling.** OSSE lanes use `resample_strict` with `error_policy: retry_same_then_stop`, because their sampled refusals are `invalid_geometry`, where `graded` has no effect. The rows lane keeps `graded`, because its refusals are envelope refusals.

| # | job | config sha | seed | mesh seed (shape_check) | preflight valid / 32 |
|---|---|---|---|---|---|
| 1 | c4n__01_fold_warm | `75101fc6a59e` | fold_warm v10 best `00826f071b24`, shrunk | 383 × 333 × 363, 2,890 dof | 31 |
| 2 | c4n__02_morph | `c5fcd0d1699f` | morph `436a4d221328`, shrunk | 382 × 333 × 363, 2,809 | 30 |
| 3 | c4n__03_ext_throat | `13017071218c` | ext-throat `a23763f1c6fc`, morph on | 380 × 330 × 333, 3,318 | 18 † |
| 4 | c4n__06_twinray | `b7284e6215a0` | **in-cube bar `bbe858b5b6a4`** | 367 × 377 × 255, 3,072 | 32 |
| 5 | c4n__04_petal_hvlaw | `5e47a7251c1a` | register A1 `74d8eed97268`, morph on | 380 × 330 × 322, 2,603 | 29 |
| 6 | c4n__05_tritonia_v8 | `81c1f0627c37` | register A3 `cded84a911d2`, shrunk | 383 × 334 × 305, 3,390 | 32 |
| 7 | c4n__07_ath_core_14in | `9eb4ab9f8893` | ATH core law re-thrown at r0 18 | 380 × 380 × 359, 3,471 | 17 ‡ |
| 8 | c4n__08_lecleach_iwata_ar | `a792a8f643d6` | Iwata AR best `04501fa6edc8` | 400 × 305 × 244, 1,677 | 22 (envelope, graded) |
| 9 | c4n__09_fold_warm_v10_s2w | `d93f9c619d2a` | **home v10:** published best `00826f071b24`, L_mm hi 271.9→330 | 589 × 402 × 374, 3,929 | 32 |
| 10 | c4n__10_ext_throat_v10_s2w | `ac7414c53f10` | **home v10:** published best `a23763f1c6fc`, `az_a_cos_pow` lo→0.5 | 598 × 390 × 333, 4,068 | 11 † |

- **Preflight samples** are uniform over the whole search box. That is an upper bound on refusals, because CMA concentrates near the seed.
- **† ext-throat:** the unwidened source config `b6 …_s2` also refuses 21 of 32, so the rate belongs to the family's box, not to the widened knob. Its real s1 run was 31 valid of 39 attempts.
- **‡ ATH core:** the dof caps were raised from 12,000 to 24,000 to match the other lanes; 2 of 32 samples still exceed them. Its box is the atlas campaign's wide one, which is deliberate for a family not yet searched at 1.4 inches.
- **Jobs 9–10** answer the open ISSUES item from the Q3 night. The leaders are bound-pinned, so each job widens the pinned knob AND starts from the published best, not the lane seed. They stay on the home v10 identity (floor 0.4677).
- **Expected GPU time:** compact lanes at 2–3.5k dof run about 10–20 s per eval. Expect about 3–5 h in total, less where the no-gain watchdog stops a lane.

**Launch, once the owner approves the GPU time.** Check the lanes first (`tools/night_status.py`); no runner may be live.
```
copy docs\queue\compact400_next10_2026-11-19.yaml runs\nights\
powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights compact400_next10_2026-11-19 -Log runs\nights\queue_compact400.log"
```

## 6. Reading the results

- **Ranking.** Compare compact400 lanes only with each other and with the 1.7302 bar, using the 0.1293 floor. Compare jobs 9–10 only with the published v10 bests (1.4214 / 1.5710), using the 0.4677 floor.
- **Promotion.** Before any compact400 winner is promoted:
  1. run a verify solve;
  2. re-measure the floor on compact400 screen→verify pairs;
  3. run `tools/analysis/xo_loading_report.py` (report-only) for the velocity-referenced loading and a 32-driver bracket at a 1 kHz high-pass.

## 7. Not done

- No GPU solve and no launch.
- No woofer, cabinet or installed solve.
- No real-driver claim.
- The floor has not yet been measured on 400 mm horns.
