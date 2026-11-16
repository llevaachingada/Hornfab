# Home landscape plan + senior queue/data review (2026-11-15)

Owner direction (15 Nov): stop making portrait horns; vertical matters less than horizontal; 780 mm tall is too big;
no more compute on solves that don't improve scores or teach us something; more BoTorch and more interesting shapes
(ATH-style ripples/petals/ridges, salmon, Le Cléac'h, X). Home range: **60-90° H, 40-60° V**.

## 1. Senior review: what the last 72 h of GPU taught us

| Finding | Evidence | Consequence |
|---|---|---|
| **Portrait bias was configuration, not physics.** The 80×60 cells used Keele's mouth rule (25.4e6/(angle·f) → 454 W × 605 H) as a 500 × 660 morph target inside a 600 W × 780 H envelope, while every wall had ONE angle in all directions. The tall mouth flared the vertical walls, so V came out wider than H. | 396 ATH-core designs: only 4 could have W > H; only 27 had beam H > V; Spearman(mouth H/W, beam V/H) = +0.55. Every home winner ≈ 66 H × 68-70 V. | New brief + cells: landscape envelope, no K-law mouth targets, per-direction wall angle. The first landscape solves read **69 H × 51 V**. |
| **BoTorch beats CMA** on a warm-started, already-optimised home horn. | Median verify J 3.189 vs 3.827; gap > both seed spreads. CMA improved 0/3 times in 60 solves and lost 14-29 solves per arm to size refusals. Report: `docs/status/2026-11-15-bo-vs-cma/`. | BoTorch is the main optimiser for home tasks. CMA's job is building cohorts and exploring new families. |
| **Restarting CMA from a converged optimum wastes solves.** | 3 CMA arms from the 18985d best: 0 improvements. Two SAB "seeds" also started from the same x0 and converged identically. | Don't queue CMA "continuations" from converged points. To measure repeatability, use different starting designs. |
| **The superformula petal on the ext-throat family: negative.** | 3 seeds × 100: best stays the no-petal incumbent (3.2325); every petal variant is worse. | The remaining seeds (3456, 7890) were cut. Petals stay in the ATH-core / ridge families. |
| **The ATH CORE-style law on ATH-core: positive, but the gain came from the cosine (H/V) term**, not the petal. | 5.39 → 4.43; cov 1.30 → 0.87, horizontal beam 61 → 65°; diag got worse. | The H/V wall-angle law is the useful lever; it is in every new landscape cell. |
| **Lip ripples don't move the field.** | rev2 ablation, 13 Nov (inside the noise at screen and verify). | Ripples are only worth testing as throat-to-mouth flutes (salmon X flute8 cell). |
| **Box narrowing from one run's top 10 %: unreliable.** | core_law narrow better (1 seed); lecleach narrow worse (2 seeds); CMA's narrowed walls would have excluded BoTorch's winner. | No auto-narrowing. Let BoTorch / TuRBO handle where to look. |
| **Screen J can mislead; verify the finalists.** | CMA incumbent: screen 3.233 → verify 3.827 (+18 %). BoTorch winners drift +3.4 % (median). | Every night ends with a verify of its finalists. Pick on verify J. |
| **The on-axis `flat` term scored the sub-crossover roll-off.** | ATH-core flat 3.46 → 1.21 dB once measured from 700 Hz up. | New brief uses `flat_band: scored`. |

## 2. Queue surgery (15 Nov ~09:30)

**Stopped** the remainder night `sab_home_gpu_rest_2026-11-15` after `h1_ext_corelaw_s9012`. Cut, about 9 GPU-hours:

| Cut job | Why it was low value |
|---|---|
| `c1_core_law_wide/narrow_s2402` + `v_c1_top5` | 2-inch 50×50 brief, not the home horn. The narrowing question is already answered ("don't auto-narrow"). Only 7 rows had run. |
| `h1_ext_corelaw_s3456`, `s7890` | The petal on ext-throat is a clear negative after 3 seeds. |
| `h2_athcore_corelaw_s5678` | Portrait-constrained geometry. Its useful finding (the cosine term) carries into the landscape cells. |
| `v_home_top` | It would verify identical incumbent designs (already known: 3.827). |

Also retired: draft `bo_ext_2026-11-16` (TuRBO/Pareto on the portrait task). It is replaced by night B on the landscape task.

## 3. New brief and cells

- Brief `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`:
  - **80 H × 50 V**; envelope **600 W × 480 H × 480 D**.
  - `cov_v_weight: 0.5`: vertical misses count half. New opt-in objective key; existing briefs are unchanged.
  - `flat_band: scored`; cov weight 1.0, tolerance 3.0.
  - No K-law.
- Cells in `examples/typologies/home_landscape_2026-11-15/`. All seeds pass `shape_check`: landscape mouth, round 18 mm
  coupling, ≤ 4.1k DOFs (~20 s per screen solve).

| Cell | Shape idea | H > V via |
|---|---|---|
| `hl__ext_throat_hvlaw_v7` (**BO task**) | OSSE + extended throat (BoTorch's winning family) | cosine wall-angle law; no morph |
| `hl__ath_core_petal_hvlaw_v7` | ATH CORE-style petals | cosine law + searchable petal amplitude |
| `hl__ath_ridge8_hvlaw_v7` | 8-lobe ridges | cosine law + ridge depth |
| `hl__petal_os_x4_landscape_v7` | mild X mouth, curled lip | H angle 34-46° vs V 20-31° |
| `hl__salmon_x_flute8_landscape_v7` | salmon X with 8 flutes through the throat | lower horizontal fc |
| `hl__chanterelle_sf_x4_stretch_v7` | sharp superformula X, stretched wide | angle pair + `sf_ab` stretch |
| `hl__lecleach_iwata_ar_landscape_v7` | Le Cléac'h with an aspect-ratio stretch | AR 1.2-2.4 |

Skipped: quatrefoil, because it is 4-fold symmetric (H = V by construction).

## 4. Queue (chained, one GPU job at a time)

| Night | Jobs | Est. | Purpose |
|---|---|---|---|
| A `home_landscape_a_2026-11-15` (running 09:32) | 2 CMA seeds × 100 of the BO task | ~70 min | first landscape solves; BoTorch training cohort |
| B `home_landscape_b_2026-11-15` (waits on A) | cohort → BoTorch **scalar**, **TuRBO**, **Pareto**, 60 + 6 each | ~3-4 h | first real TuRBO and Pareto runs, on the task that matters |
| C `home_landscape_c_2026-11-15` (waits on B) | 6 exotic families × 80 (CMA) + verify top 3 each | ~5-6 h | which shape family deserves its own BoTorch study |

## 5. Next decisions (after B and C)
- Promote the best 1-2 exotic families to BoTorch tasks (register them like `hl__ext_throat_hvlaw_v7`; the cohort comes
  from night C).
- Pick the home horn on **verify** J plus the hi-fi check (`tools/analysis/hifi_rescore.py --verify`).
  Render it, then print and measure one.
- Cold-start BoTorch vs CMA (same small random starting set) remains open.
- Log each adaptive pick's prediction in the study journal (open issue).

## 6. Night C revised and run (15 Nov ~10:00, owner review of the seeds)

The extreme seeds (8-lobe ridges, salmon X flutes, petal X, superformula X) were dropped before any GPU time: real
ATH-style waveguides are smooth OS/R-OSSE profiles with rounded-rectangle mouths, and sharp features raise
diffraction (Geddes). Renders: `img_home_landscape_seeds_v2_2026-11-15.png`. Screen results (80 each, lower J is better):

| Cell | Best screen J | Note |
|---|---|---|
| `hl__osse_rrect_morph_v7` (ATH-style OSSE, rounded-rect landscape mouth) | **3.99** | only new family near the ext-throat winner (3.10) |
| `hl__ath_core_petal_hvlaw_v7` (gentle petals) | 5.32 | |
| `hl__lecleach_iwata_ar_landscape_v7` | 19.4 | beam narrows with frequency |
| `hl__es_style_rollback_v7` | 20.9 | same |
| `hl__biradial_es_style_v7` (ES450-style) | refused | throat not round (1.03-1.05x ellipse area, tolerance 0.03): generator fix needed |

The parallel rolled-rect / Crowe-section / section-pucker pilots scored 22.8-29.4: same brief, but the mouth is frozen
small (Crowe 417 x 203 mm, 205 mm deep), so the vertical is uncontrolled below ~1.5 kHz and both beams keep narrowing.

## 7. Nights D and E (15 Nov 14:00; ~7 h of GPU)

Night B trained on 0 rows (encoder bug, see CONTINUITY 15 Nov 14:25) and solved nothing. Fixed, then:

| Night | Jobs | Purpose |
|---|---|---|
| D `home_landscape_d_2026-11-15` (13:54) | BO scalar, TuRBO, Pareto (60 + 6 each) on ext-throat; Crowe ES-600 replica x96 + verify (kept, owner) | the BO comparison night B should have been |
| E `home_landscape_e_2026-11-15` (after D) | TuRBO s62001 rerun (night D's arm stopped at 21/60: a GPU-marked test run killed the shared worker 14:19-14:30) -> home-sized Crowe `hl__crowe_panel_home_v7` 2 seeds x 96 + Crowe verify top 3 -> CMA x100: ext-throat s9012, s3456; OSSE rounded-rect s5678, s9012, s3456 -> verify top 3 of each + night C's OSSE run -> cohort rebuild -> BO round 2 (scalar, TuRBO x2, Pareto) | grow both cohorts (BO solves do not feed the cohort), get OSSE rounded-rect past 100 rows, then BO on the bigger ext-throat cohort |

**Rule (owner, 15 Nov): BoTorch only on a typology with existing data.** `prepare_study.py --min-rows` (default 100).

Crowe: the replica cell can only re-score the ES-600 drawing size; `hl__crowe_panel_home_v7` keeps the digitized
sections and searches size inside the envelope (depth <= 0.57 x width is a hard limit of the swept-H construction).

Next after E: register `hl__osse_rrect_morph_v7` as a BO task (code change, only while no study is queued), fix the
biradial throat, then pick the home horn on verify J + `hifi_rescore.py --verify`.

**STOPPED 2026-11-15 17:15 (owner):** night E's runner and the current Crowe-section run were stopped; no new solves
until the brief/DI-slope scoring question and the lip/waist geometry law are settled. Evidence and options:
`docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md` and `STARTING_SEEDS_PLAIN_2026-11-15.md`; top-priority
block in `docs/ISSUES.md` and `NOTES_FOR_SENIOR.md`. The Crowe-section outer-body/lip fold must also be fixed before
more Crowe data.
