# Biradial / Crowe-style / rolled-mouth horns: study + senior handoff (2026-11-15, ~15:50 local)

**For:** the next senior agent. **Status:** study done, four corrected cells written and box-checked. The biradial
throat-blend fix is merged (7124902, 2026-11-15 16:0x); the four cells are rendered and visually reviewed. No new
solves and no night F yet. Read all of this before touching a config. Owner is frustrated with this line: every claim
below is labelled with how it was checked.

Sources: `BIRADIAL_CROWE_SOURCES_2026-11-15.md` (Keele / Crowe / ATH / roundover research, with a correction header)
and `SCORING_NON_CD_SOURCES_2026-11-15.md` (is the v7 objective fair to non-CD horns). Earlier repo dossiers it
builds on: `BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md` (US4308932A Bi-Radial), `JMLC_LECLEACH_RESEARCH_2026-10-25.md`,
`ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md`, `SECTION_PUCKER_RESEARCH_2026-11-15.md`,
`../CROWE_X_HORN_HANDOFF_2026-11-15.md` (fork's handoff: owner's look requirements, reference images in
`scratch/crowe_ref/` - copyrighted, never commit). Renders: `img_biradial_crowe_2026-11-15/`.

## 1. Target (unchanged)

Home hi-fi horn, FaitalPRO HF1440 1.4" (18 mm exit radius, 2 deg exit), XO 700 Hz, brief
`examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`: 80 H x 50 V (acceptable 60-90 /
40-60), vertical half-weighted, envelope 600 W x 480 H x 480 D, landscape only, no K-law mouth sizing
(`generator.seed_policy: explicit` INSIDE the generator block). Owner look (fork handoff s1): Crowe ES Bi-Radial
look - X creases throat->corners, bow-tie outline, straighter sides, thick roll, ~1.8:1, depth ~0.45 W, smooth.

## 2. What was wrong (verified)

| # | Problem | Evidence | Cells hit |
|---|---|---|---|
| 1 | Knobs frozen: mouth W/H locked at the drawing, 9-13 knobs fixed, depth +-2-8 %, H/V depth ratio +-1-3 % | inventory of bounds (this session) | `rr__*`, `sp__*`, `rf__*`, `rr__crowe_panel_es600_v7` |
| 2 | Rolled-rect log spiral: wall angle == turning parameter, so the wall leaves the throat axially and keeps turning (no constant-angle section -> HF beam narrows by construction); H and V share ONE normalised contour (no H/V coverage control); `decay`/`rect_turn`/`terminal` shape the drawing, not the acoustics (its own research doc says so) | `tools/geometry/rolled_rect.py` `surface_at` | `rr__*`, `rf__rect_*` |
| 3 | Roll size tied to `decay`: past 90 deg the wall keeps going out ~31 % of mouth radius and returns ~35 % of depth by 270 deg -> boomerang side view | spiral reference table in ROLLED_RECT research | same |
| 4 | Crowe ES section cells reproduce Crowe's exponential(-spiral) flare: throat region ~17 deg -> beam narrows (H 90->46, V 137->41 deg). This matches Crowe's own data (ES-600 45 deg -4..-10 dB above 2 kHz; ES-290 ~90 deg to 7 kHz, ~50 deg above 10 kHz) | stored metrics; sources file | `rr__crowe_panel_*`, `sp__*`, `rf__section_*`, `hl__crowe_panel_home_v7` |
| 5 | Crowe-X OSSE "chunky bar" rim = lip `r_lip` 30-50 mm with `wrap` 130-160 deg; flat-plate side = OSSE termination `n` 4 packs the mouth flare into the last ~20 mm | renders `crowe_x_cd_termination_and_lip.png` | fork seeds, `hl__es_style_rollback_v7` |
| 6 | Fork's z-round Crowe-X seeds used `a_h/a_v` 24/14 deg (~48 x 28 deg at HF) to fit 600 mm | config read | `scratch/crowe_x_attempts/z_round3_unchecked/` |
| 7 | Biradial throat kink: US4308932A law starts at its full wall angle (36-38 / 22 deg) at the 2-deg driver exit; mesher closes it with a 4.8 mm domed source cap -> throat check "not round 1.04x" (17/19 refused). `biradial` was missing from `THROAT_BLEND_TYPES` | mesh source-tag measurement | `hl__biradial_es_style_v7` |
| 8 | Scoring: 3 of 9 v7 terms encode constant directivity (`dislope` target 0; `cov` fixed 80x50 with narrowing x2; `di` fixed ~10.1 dB). Remaining 6 terms are typology-agnostic | `scalar_v7.py`, scoring sources file | every non-CD family |

## 3. Evidence (offline, no GPU)

**Fair rescore** of every stored dataset row (shards 0063-0069) under the base brief and the new smooth variant
(best J per family; script pattern: `tools/rescore/rescore_v6_v7.py` helpers + `objective_v7`; NOTE the row's stored
`target.di_slope_target` must be overridden, the brief alone does not change it):

| Family | n | J base | J smooth | smooth-best residual terms |
|---|---|---|---|---|
| CD OSSE ext-throat (BO task) | 330 | 2.58 | 2.80 | balanced |
| CD OSSE rounded-rect | 78 | 3.99 | 2.32 | |
| CD ATH petal | 49 | 5.32 | 3.14 | |
| Le Cleach AR | 83 | 19.42 | 6.93 | diag 2.6, cov 1.5, distd 1.2 |
| ES-style rollback (Le Cleach) | 82 | 20.86 | 8.14 | diag 3.4 |
| Crowe ES-600 sections | 130 | 22.54 | 10.53 | diag 4.5, cov 1.8, dislope 1.6, distd 1.3 |
| Rolled-rect (ES spiral) | 33 | 27.4-29.4 | 14.3-15.9 | diag 7.0-7.7, dislope 2.7-3.1 |

**CD-agnostic listening terms** (`tools/analysis/hifi_rescore.py` raw terms: seat spread, PIR smoothness, LW
roughness, XO hand-off; tolerances = top-decile medians): Crowe ES sections 1.64 (better than the ext-throat
family's best 2.30, near OSSE rounded-rect 1.29); rolled-rect 2.8 (worst). Ignores coverage width and loading - evidence,
not a verdict.

**Conclusion:** about half of the Crowe/Le Cleach penalty was the CD assumption; under fair rules CD horns still lead,
the residual is mostly `diag` (corner creases make the diagonal beam very different from H/V).

## 4. What was built (uncommitted; all CPU-checked; none solved)

| Cell (examples/typologies/home_landscape_2026-11-15/) | Construction / entry point | Searched knobs (acoustic meaning) | Checks |
|---|---|---|---|
| `hl__rosse_rect_cd_v7.yaml` (NEW) | ATH R-OSSE per azimuth: new `tools/geometry/rosse_rect.py` evaluates Magnus's `profile_points({"type":"R-OSSE"...})` with numeric R(p), a(p); entry `tools/geometry/rosse_rect_cli.py` (rebinds the rolled_rect bridge like `crowe_panel_cli.py`) | W 480-590 / H 280-420 exact mouth (pattern control), corner exp 2.5-8, a_h 32-46 / a_v 18-30 (HF beamwidth), k 0.8-3 (throat loading), r 0.25-0.6 / b 0-0.4 / tmax 0.85-1 (rollback). Fixed m 0.85, q 3, a_diag 0 | 6 seed variants mesh, mouth exactly W x H, depth 175-219; preflight **64/64** valid. a_diag > 0 fans creases out of the throat - keep 0 |
| `hl__crowe_x_osse_cd_v7.yaml` (NEW) | `osse_rollback` grid rows (OSSE CD wall per azimuth + Gielis X + curled lip) | a_h 33-40 / a_v 20-28, L 200-260, s 0.2-0.45, n 1.8-3.2 (bowl not plate), sf_amt 0.15-0.38 (X), sf_ab 0.7-0.9, r_lip 8-30, wrap 80-160. Fixed sf_m 4, n1 1.8, n2 7, start 0.25 | seed e1 (588 x 398 x 244); preflight **58/64** (6 envelope) |
| `hl__rolled_es_spiral_v7.yaml` (NEW) | Crowe-ES-faithful log spiral, `tools/geometry/rolled_rect_cli.py`, rows `rolled_rect_pucker` | W 480-590, H 260-420, depth 200-380, decay 0.4-1.0 (ES flare rate), depth_h_ratio 0.55-1, rect_exp 4-14, rect_turn 45-85, terminal 200-275, pucker H 0-18 / V 0-24 | preflight **62/64**; WARN graded_inert -> set `search.infeasible_penalty: resample_strict` + `search.budget_counts: valid` before queueing. Not rendered across the box |
| `hl__biradial_es_style_v7.yaml` (REWRITTEN) | registry `biradial` + throat blend 25 mm both planes, superellipse mouth | L 220-400, h_a 32-42 / v_a 18-28 (Keele 0.9 x half-coverage seeds 36 / 22.5), h_rm 230-292 / v_rm 150-230, h_n / v_n 3-7, mouth_exponent 2.2-5 | **Needs the code fix merged first** (main code ignores the blend knob -> kink). With the fix: seed round, 550 x 371 x 303, fits; box **32/64 refused (invalid_geometry, cause NOT yet identified)** |
| `hl__crowe_panel_home_v7.yaml` (committed 6afeabd) | Crowe ES-600 digitized sections scaled to the envelope | size/depth/crown/junction; depth <= 0.57 x W construction limit | preflight 62/64; **queued in night E** (2 x 96 + Crowe verify) under the BASE brief |
| brief `room_landscape_80x50_700_hf1440_v7_smooth.yaml` (NEW) | smooth-directivity variant | di_slope_target 5 dB/decade, cov tol 8 + narrow ratio 1, di weight 0, distd 1 | used offline only |

Code fix (worktree `C:\Users\hunte\Hrns\biradial-wt`, branch `fix/biradial-throat-blend`, UNCOMMITTED):
`hornlab_search/design/generators/registry.py` adds `biradial` to `THROAT_BLEND_TYPES` (default 0 bit-for-bit);
`tests/test_design_generators_throat_blend.py` +2 tests. 18/18 throat-blend tests and the CI-selected design/mesh
tests pass in the worktree. GOTCHA: `tools/shape_check.py` / `search_preflight.py` put the MAIN checkout first on
`sys.path`; test worktree code with the worktree's own copy of the tool (`cd biradial-wt; <venv python> tools/...`).

Retire from optimisation (keep as visual references): `rr__reference_v7`, `rr__pucker_hv_*`, `sp__*`, `rf__*`,
`rr__crowe_panel_es600_v7` (frozen replicas, see s2). `hl__crowe_es_biradial_rr_v7` (untracked, other session) is unrun.

## 5. Compute state at handoff

- Night E `home_landscape_e_2026-11-15` is RUNNING (detached queue pid 36556, after night D). Order: TuRBO rerun
  (`d_turbo_s62001_rerun`, running since 20:07Z) -> `e_crowe_home_s1234`, `e_crowe_home_s5678` (96 each) ->
  `v_e_crowe_home_top3` -> CMA ext-throat x2 + OSSE rounded-rect x3 -> `v_e_top3` -> cohort -> BO round 2 (scalar,
  TuRBO x2, Pareto) on `hl__ext_throat_hvlaw_v7` only. Ends roughly 02:00-03:00 local.
- BoTorch only runs on `hl__ext_throat_hvlaw_v7` (136 usable rows now, ~330 after E). `prepare_study.py --min-rows`
  (default 100) refuses anything thinner. **No BoTorch on any Crowe/biradial cell** until it has >= 100 solves.
- No night F exists yet.
- Hygiene: never run un-filtered pytest while a GPU night runs (`-m "not slow and not gpu and not crosscheck"`); a
  warm-worker test killed the shared host at 14:19 and cost night D's TuRBO arm. Never edit `hornlab_search/**` while
  a BoTorch study is running (studies pin a hash of it); safe window = after the TuRBO rerun ends and before
  `prep_e_scalar_s61002` (hours later).

## 6. Remaining work, in order

1. **Merge the biradial fix** once `d_turbo_s62001_rerun` has finished and no study is running: commit in the worktree,
   merge into `feat/sab-home-2026-11-14`, run the CI-selected suite.
2. **Biradial box:** find why 32/64 box samples are refused (likely the US4308932A law's own refusals: `rm` cannot
   close the tan(a) cone at short L / large a, or end slope <= 0 - see `profiles.biradial_contour`). Couple or
   tighten L vs rm vs a (e.g. raise L lo, lower a hi) until >= 85 % valid; consider `throat_blend` 15-40 searched.
   Render seed + corners.
3. **ES spiral cell:** switch to `resample_strict` + `budget_counts: valid`; render corners; confirm the roll and
   depth split look like the ES-450 (fork handoff s2 checklist).
4. **R-OSSE rect:** render a few box corners; check rim waviness (rings at equal R-OSSE t have different depth per
   azimuth); decide whether a Crowe-X variant is wanted here (a_diag fans creases - needs a better law, e.g. a pucker
   z-term like rolled_rect's cos 4psi, not a(p)).
5. **Crowe-X OSSE:** render the box extremes; owner look review vs Crowe reference (side by side) before GPU.
6. **Scoring decision (owner):** which brief ranks the final horn. Recommendation: search CD families on the base
   brief, narrowing families (ES spiral, Crowe sections, Le Cleach) on the smooth brief, and compare ALL families
   under both briefs + `hifi_rescore` raw terms. Open: is `diag` (weight 1, tol 2) fair for rectangular creased
   mouths at home? Verify the 1-3 dB/oct DI-slope claim against Toole / Olive primaries (agent could not reach them).
7. **Night F** (after E; owner approval of looks first): CMA x 96, 1-2 seeds each for `hl__rosse_rect_cd_v7`,
   `hl__crowe_x_osse_cd_v7` (base brief), `hl__rolled_es_spiral_v7` (smooth brief variant cell), fixed
   `hl__biradial_es_style_v7`; verify top 3 each through the RIGHT entry point (rosse_rect_cli / rolled_rect_cli
   verify-night for bridge cells; `tools/night_queue/verify_night_jobs.py` for registry/grid cells). Run
   `search_preflight` first (night-queue skill step 4).
8. Rescore night E's `e_crowe_home_*` runs under the smooth brief (offline).
9. Promote a family to BoTorch only once it has >= 100 valid solves (register it like `LANDSCAPE_TASK_NAME` in
   `studies/builders.py`; code change -> only while no study is queued).
10. Commit (CONTINUITY + ISSUES in the same commit as any push), push only on owner request.

## 7. Research sources (full tables in the two sources files)

US4071112 (Keele, EV CD horn: exponential throat + conical midsection + bell; cone half-angle sets HF beamwidth) [verified];
US4308932A (Keele/JBL Bi-Radial power-series law, K-law, throat angle = 0.9 x half-coverage) [repo dossier];
AES preprint 1038 (Keele 1975, abstract only); josephcrowe.com ES-600 page, ES-600 + Faital HF1460 measurement report,
ES-290 polar post (ES flare = Exponential Spiral; 270 deg wrap) [verified, numbers lower confidence];
at-horns.eu (ATH): tritonia.html, twinray roundover BEM study (8.75 / 17.5 / 35 mm; 35 mm recommended, graphical),
exar-story.html (throat diameter sets the HF limit) [verified]; installed `hornlab_mesher.profile_formulas`
R-OSSE (`_calculate_rosse_main`) [read]; Geddes (gedlee.com unreachable); Olive 2004 / Toole / CTA-2034 for DI slope
and spinorama [inferred - primaries not reached].

## 8. Continuation (2026-11-15 16:40 local, same day)

### 8.1 Biradial fix merged and box refusal solved

- Worktree `biradial-wt` committed as `7124902` and fast-forwarded into `feat/sab-home-2026-11-14` while the
  TuRBO rerun had ended and no BoTorch study was running. CI-filtered `test_design_generators_throat_blend.py`,
  `test_design_generators_biradial.py`, `test_mesh_throat_check.py`: 30 passed.
- Refusal cause [measured]: **all 32/64 refusals were `cone_does_not_close`** (US4308932A needs
  `rm >= r0 + tan(a) L`; the old 32-42 deg / L<=400 box violated it). The `end_slope` refusal never fired on its
  own because a closed cone makes `flat >= 0`.
- New closure-coupled box [measured 64/64 meshed, envelope-fitting, round throat]:
  `L 220-320`, `h_a 32-37`, `v_a 18-24`, `h_rm 260-292` (`>= 18 + tan37*320`), `v_rm 162-230`
  (`>= 18 + tan24*320`), `h_n/v_n 3-7`, `mouth_exponent 2.2-5`; seed `560 x 350 x 258`
  (`L 255`, `h_rm 280`, `v_rm 175`, angles 36 / 22.5). Box range: W 520-584, H 328-459, D 224-321.
- Renders: `img_biradial_crowe_2026-11-15/biradial_box_corners_2026-11-15.png` (8 corners), the six-seed
  turntables and the scratch comparison with Crowe's photos. Geometry fact: the US4308932A law as implemented has
  **no mouth-waist term and no lip-rollback term**; the outline is a convex superellipse and the wall ends at a cut
  edge. Whether that is close enough to the owner's target is an owner look decision from the 3D renders, not a
  model judgment.

### 8.2 Three cells rendered and reviewed

| Cell | Build evidence | Visual QA (defect-only; NOT a Crowe-likeness ranking) |
|---|---|---|
| `hl__rolled_es_spiral_v7` | `search.infeasible_penalty: resample_strict`, `budget_counts: valid`, `error_policy: retry_same_then_stop`; preflight 62/64 (2 invalid_geometry); 9 corners mesh + fit (2870-5313 DOFs) | No build defects at the 9 sampled corners. The render shows the wall returning as a thin hook; the high-pucker corners add visible rim ripples. Whether the roll reads as Crowe's thick bead is an owner judgment from the 3D renders. |
| `hl__rosse_rect_cd_v7` | 10 corners mesh + fit (2523-4973 DOFs); W 450-590, H 280-420, D 128-343 | The mid-roll seed rim is the cleanest of the sampled corners; extreme roll radius/corner exponent corners show scalloping or corner notches; `max_cov` shows an undercut scoop. Needs a high-res defect check before printing. |
| `hl__crowe_x_osse_cd_v7` | 10 corners: 5 in envelope, 5 over 600 mm (preflight 58/64); seed 588 x 398 x 244 | The lip is a thin flange in the side view, not an under-surface return; `max_x` is 665 mm wide and over-pinched. The build checks pass for the in-envelope corners; owner judges the look from the turntables. |

Render sheets: `img_biradial_crowe_2026-11-15/rolled_es_box_corners_2026-11-15.png`,
`.../rosse_rect_box_corners_2026-11-15.png`, `.../crowe_x_box_extremes_2026-11-15.png`.
Copyrighted Crowe comparisons remain in `scratch/2026-11-15_biradial_audit/*_compare.png` only.

### 8.3 Scoring and white-paper research result

Three external-research passes (2026-11-15, after the handoff) changed the evidence base; the detailed memos are in
`STARTING_SEEDS_PLAIN_2026-11-15.md` and the correction header of `BIRADIAL_CROWE_SOURCES_2026-11-15.md`.

- **DI slope:** no primary or credible secondary source was found for "Harman prefers 1-3 dB/oct". Olive 2004 has
  no DI-slope term (NBD_ON, NBD_PIR, LFX, SM_PIR only); CTA-2034's 12/44/44 is the PIR synthesis average, not a
  preference weighting. Measured evidence for narrowing horns: Le Cleac'h FEA ~2.6 dB/oct (8.6 dB/dec); Crowe's own
  ES-600 report shows a stronger narrowing (45 deg down 4-10 dB above 2 kHz) and a 1 kHz resonance that needs a
  passive network. A smooth 2-3 dB/oct rise is acceptable **if** it is monotonic, continuous at the 700 Hz
  crossover, keeps a coverage floor through the presence band, and has no in-band resonance. The smooth brief's
  5 dB/dec target is close; 6-9 dB/dec is the fair range, and tolerance 9 already gives a +/-3 dB/dec window.
- **`diag`:** it compares the 45-deg beam to a fixed round mean (65 deg for 80x50). A rectangular/creased mouth is
  penalised for being rectangular, but a real lobe or null is a real defect. There is no measured diagonal-polar
  data for a Crowe-style horn yet. Keep `diag` as a reported diagnostic and do not let it decide the winner until
  diagonal polars exist; the smooth brief's `cov_narrow_ratio: 1` already halves the narrow-side weight.
- **K-law correction:** the denominator is the throat angle `A = 0.9 B`, not the coverage `B`. At 700 Hz, 80 deg H
  needs **496 mm** (not 446) and 50 deg V needs **794 mm** (not 714). The 600 mm H mouth holds 80 deg down to
  ~579 Hz; the 480 mm V mouth holds 50 deg only down to ~1157 Hz, so at 700 Hz the vertical can support ~83 deg.
  This is the physical reason a 480 mm-tall box cannot hold 50 deg vertically at the crossover.
- **Mouth termination:** Geddes' verified rule is radius >= lambda/4: 35 mm is clean above ~2.46 kHz, 50 mm above
  ~1.72 kHz, 86 mm above ~1 kHz. 40-50 mm is the rational hi-fi lip. The 270-deg-wrap superiority and the 180-deg
  cavity-resonance claim are **unverified**; no measured/BEM comparison of 90/130/180/270 was found. A smooth
  termination is grounded; the exact wrap angle is not.
- **Waist / X creases:** the waisted/bow-tie outline has no acoustic source; ATH's morph target is a convex
  rounded rectangle. Corner creases are curvature discontinuities (HOM/diffraction risk per Geddes) and partly a
  morph consequence. Treat them as visual until diagonal polars exist.
- **BEM practice:** the screen mesh uses 6 elements/wavelength, which is a screening mesh (~10% frequency error);
  verification/final should use 8-12 with a convergence check. A uniform-velocity throat cap is acceptable for
  pattern work but not for absolute level/loading above ~5.6 kHz (1.4-inch driver). The current "verify" refines
  the frequency grid, not the spatial mesh; this is a real fidelity gap for finalists.

### 8.4 Compute state and rescore

- Night E: TuRBO rerun ended 15:54:51; `e_crowe_home_s1234` ended 16:38:47; `e_crowe_home_s5678` started
  16:38:47; CMA/verify/BO round 2 follow. No night F exists.
- Smooth rescore of `e_crowe_home_s1234` (96/96 valid): best `J_smooth` **6.84** vs stored base **16.92**
  (`22365b569be9`, 579.7 x 292.9 x 262.1, crown 39.7). Residual terms: cov 1.06, dislope 1.11, distd 1.18,
  diag 2.94; di 0. This is the home-sized Crowe section, not the frozen replica. The stopped seed-5678 run
  (62/62 valid rows) rescores to **6.83** vs base **17.06** (`88d714f9ed8e`, 575.2 x 285.5 x 265.1), with the same
  residual pattern; the two seeds agree, so the provisional family result is stable.
- **New defect finding (objective mesh check):** the Crowe-section family has a 153-176 deg fold at the
  side-wall/lip junction with inverted triangles (seed max 176.5 deg, best design 153.2 deg, 18 edges >140 deg).
  The inner flare is smooth in the section plot; the fold is on the outer-body junction. The other cells have no
  edge above 150 deg (Crowe-X 99, ES spiral 119, R-OSSE rect 95, ext-throat 106, biradial 136). Treat the current
  Crowe-section scores as provisional and rebuild/fillet the junction before print or final ranking. The owner
  stopped the night-E runner and this run at 17:15 (~62/96 rows); no new solves until the brief and geometry are
  settled. Do not queue more section runs until the geometry is fixed.
- Decision packet: `STARTING_SEEDS_2026-11-15.html` (shaded 3D heroes, front views, 360-degree turntables, horizontal/
  vertical sections, per-cell parameter tables, issues log I1-I12, research summary, four options and a decision
  checklist) plus `STARTING_SEEDS_PLAIN_2026-11-15.md` for the text version. The owner judges Crowe likeness
  from the 3D renders; the model's visual QA is used only for defect flags, not for likeness ranking.
- Open owner decisions: one brief or split for night F; which look candidate (Crowe-X or ES spiral) gets the one
  look-first seed; whether to spend GPU on the biradial at all; whether to invest in a lip/waist law before more
  Crowe-X/ES GPU time.
