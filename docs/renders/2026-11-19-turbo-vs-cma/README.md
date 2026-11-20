# CMA-ES vs TuRBO, matched configs (2026-11-19)

Every TuRBO study, paired with the best CMA-ES run of the **same config name, brief and objective version**, rendered the
same way: design card = front 3/4 + front view, then horizontal and vertical dispersion maps full width
(`tools/render/render_views.py` + `compose.py --layout stack --loudness`). Screen J is the first-pass score; verify J
is the re-solve at verify fidelity where one exists. Compare J only within a pair.

| image | config / brief | CMA-ES best screen (verify) | TuRBO best screen (verify) |
|---|---|---|---|
| `turbo_vs_cma_0_p8060_ath_core_14in_home700_v7.png` | p80x60 ATH core 1.4in / room_80x60 v7 | 4.978 (-) | **4.691** (-) |
| `turbo_vs_cma_1_ath_tritonia_landscape_v8.png` | Tritonia v8 / landscape 80x50 v7 | 5.692 (6.305) | **4.628** (5.482) |
| `turbo_vs_cma_2_ath_tritonia_landscape_v9.png` | Tritonia v9 / landscape 80x50 v7 | 5.015 (6.077) | **4.546** (5.524) |
| `turbo_vs_cma_3_ath_twinray380_landscape_v8.png` | TwinRay v8 / landscape 80x50 v7 | 4.914 (-) | **4.091** (4.895) |
| `turbo_vs_cma_4_ext_throat_hvlaw_v7.png` | ext-throat hvlaw / landscape 80x50 v7 | 3.103 (-) | **2.498** (2.766) |
| `turbo_vs_cma_5_osse_rrect_fold_warm_v7.png` | OSSE rrect fold warm / landscape 80x50 v7 | 3.621 (4.274) | **3.330** (3.799) |
| `turbo_vs_cma_overview.png` | all six pairs, front view + scores | | |

`pairs.json` holds all 14 BO pairings (TuRBO, BoTorch scalar, Pareto, early BO), with run ids and valid-solve counts.

**Caveats.** TuRBO arms start from a cohort built from the CMA runs' data (warm start), so they are a continuation,
not an independent race; the valid-solve counts differ (CMA totals sum every run of that config). "-" means no verify
re-solve was found inline in that run folder (CMA verifies may live in separate `-verify-` runs).

**How these runs became visible.** BO studies write solves to `runs/study-<id>/{screen,verify}`. Since 2026-11-19,
`tools/night_queue/mirror_bo_studies.py` hard-links each study into an ordinary run folder
`runs/<start>-<policy>-<id6>/` (no copied data), so the GUI Runs list (optimizer filter + badge), run page, verify
view, Compare, leaders and these render tools treat TuRBO exactly like CMA. `run_bo_arm.py` re-runs it after every arm.
