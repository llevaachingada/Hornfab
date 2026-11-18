# OWNER DECISIONS PACKET — 2026-11-17 (local orchestrator pass)

> Everything below is **evidence**, not a decision. No config, brief, bound, envelope or queue was
> changed. C1–C4 carry no recommendation (owner standing instruction); C5, C6, provenance and the
> envelope convention carry the senior review's recommendation, restated with what this pass added.
> Source of every number: `scratch/fable_architecture/space_cards/*.json|md`,
> `.evidence/links/*/links.json`, `.evidence/translate.json`,
> `EVIDENCE_VERIFY_2026-11-17.md`. Branch `ccr-260b4b76-fi6b8j`.

---

## 1. The one result that changes the proposals: the data rejects every geometric link

`space_card.recommend()` now carries `data_agrees` from `links.py` on each lane's latest run (step 7
of the handoff). Result [measured], 20 link proposals with a real run behind them:

| lane | proposed link | links.py verdict |
|---|---|---|
| `p80x60__ath_core_14in_home700_v7` | `a0_deg` | **false** |
| `p80x60__ath_core14_corelaw_v7` | `morph_fixed`, `az_a_sf_amp` | **false** |
| `atlas__ath_core` | `k` | **false** |
| `atlas__core_law` | `a_deg`, `morph_fixed`, `az_n_cos2_amp` | **false** |
| `hl__ath_core_petal_hvlaw_v7` | `q`, `az_a_sf_amp` | **false** |
| `hl__ath_tritonia_landscape_v7` | `morph_fixed`, `n` | **false** |
| `hl__ath_tritonia_landscape_v8` | `s` | **false** |
| `hl__ath_tritonia_landscape_v9` | `s`, `k` | **false** |
| `hl__ath_twinray380_landscape_v8` | `n`, `q`, `a0_deg` | **false** |
| `hl__crowe_x_osse_cd_v7` | `g_wrap_deg` | **false** |
| `hl__osse_rrect_fold_warm_v7` | `n`, `k` | **false** |
| `hl__osse_rrect_fold_warm_v7_w1` | `n`, `k` | unknown (no run) |

**Consequence for the four proposals already in review:**
- **Crowe X OSSE CD**: the `g_wrap_deg` link is **withdrawn** (data disagrees). The two bound trims
  remain: `g_L_mm.hi 285 -> 268`, `g_s.hi 0.45 -> 0.40`; box refusals 23/96 -> 2/32; seed shift 0.
  But see §2: no tested `sigma0` keeps the predicted bad rate ≤ 15 % in that box.
- **OSSE rrect fold-warm**: both links (`n<-s`, `k<-a_deg`) are **withdrawn**. What remains is
  `a0_deg` fixed at its seed (whole range moves 0.42 mm, under the ~1 mm mesher fit): searched
  18 -> 17, seed shift 0, box 96/96 feasible.
- **ext-throat H/V law**: unchanged — `sigma0 0.20 -> 0.10`, seed shift 0; the joint envelope
  constraint still needs `search.record_gate` (now implemented, §4).
- **Klangfilm b3_soft**: the senior-pass `g_theta_h1_deg.hi 60 -> 55.3` trim **no longer reproduces
  at the handoff's 96-point box**: its top slice is 9/19 refused (47 %), just under the trigger that
  fired on the smaller sample. Either the trim is accepted on the 64-point evidence, or the lane
  waits for more evidence. The automatic proposal is "no change".

## 2. Changed proposals (12 of 29; the other 17 are "no change justified")

Box counts are 96 points before, 32 after; sigma0 is the largest tested value with predicted bad
rate ≤ 15 % after the change; seed shift is the record's max deviation.

| lane | change | searched | box ok/outside/refused | max safe sigma0 | seed shift |
|---|---|---|---|---|---|
| `atlas__ath_core` | fix `morph_exponent`; `L_mm.hi 520 -> 436.8`; `a_deg.hi 80 -> 66` | 14 -> 13 | 57/37/2 -> 28/4/0 | none ≤ 15 % | 0 |
| `atlas__core_law` | `sigma0 0.25 -> 0.05`; joint envelope constraint flagged | 17 -> 17 | 32/42/22 -> 10/15/7 | 0.05 | 0 |
| `hl__ath_core_petal_hvlaw_v7` | `sigma0 0.20 -> 0.05`; `q.hi` cut skipped (seed above it); constraint flagged | 11 -> 11 | 60/36/0 -> 23/9/0 | 0.05 | 0 |
| `hl__ath_tritonia_landscape_v7` | fix `morph_exponent`; `sigma0 0.20 -> 0.05` | 22 -> 21 | 78/13/5 -> 26/4/2 | none ≤ 15 % | 0 |
| `hl__crowe_x_osse_cd_v7` | `g_L_mm.hi -> 268`, `g_s.hi -> 0.40` (link withdrawn) | 9 -> 9 | 73/0/23 -> 30/0/2 | none ≤ 15 % | 0 |
| `hl__ext_throat_hvlaw_v7` | `sigma0 0.20 -> 0.10`; constraint flagged (R² 0.91) | 8 -> 8 | 27/37/0 -> 14/18/0 | 0.15 | 0 |
| `hl__lecleach_iwata_ar_landscape_smooth_v7` | `g_fc_hz.lo 300 -> 420`; `g_stop_deg.lo 60 -> 88`; `sigma0 0.20 -> 0.10` | 5 -> 5 | 63/0/33 -> 32/0/0 | 0.20 | 0 |
| `hl__osse_rrect_fold_warm_v7` | fix `a0_deg` (links withdrawn) | 18 -> 17 | 96/0/0 -> 32/0/0 | 0.25 | 0 |
| `hl__osse_rrect_fold_warm_v7_w1` | links `n<-s`, `k<-a_deg` (**data unknown — needs a run or a 2-run A/B**) | 18 -> 16 | 96/0/0 -> 32/0/0 | 0.25 | 0 |
| `rf__section_axial_home_v7` | `sigma0 0.20 -> 0.15` | 8 -> 8 | 89/3/4 -> 30/1/1 | 0.10 | 0 |
| `sab__lecleach_ctrl` (run `88d19c`) | `g_T.lo 0.30 -> 0.44` | 3 -> 3 | 80/0/16 -> 30/0/2 | 0.25 | 0 |
| `sab__lecleach_fc540` (run `86e077`) | `g_T.lo 0.30 -> 0.44` | 3 -> 3 | 77/0/19 -> 29/0/3 | 0.25 | 0 |
| `p80x60__ath_core_14in_home700_v7` (run `db8e2f`) | fix `morph_exponent`; `a0_deg` weak 0.97 mm (review) | 15 -> 14 | 33/62/1 -> 11/20/1 | none ≤ 15 % | 0 |
| `p80x60__ath_core14_corelaw_v7` (run `22931c`) | fix `morph_exponent`; `sigma0 0.15 -> 0.10` | 18 -> 17 | 18/50/28 -> 11/13/8 | 0.10 | 0 |

Not changed (17): `hl__biradial_es_style_v7` and `_smooth_v7`, `hl__crowe_x_square_v7`,
`hl__es_style_rollback_v7`, `hl__klangfilm_lame_curved_v1_c200`, `hl__lecleach_hv_landscape_smooth_v7`,
`hl__lecleach_iwata_ar_landscape_v7`, `hl__ath_tritonia_landscape_v8`, `hl__ath_tritonia_landscape_v9`,
`hl__ath_twinray380_landscape_v8`, `rf__section_axial_home_smooth_v8`, `b3_soft`, `a0`,
`a1_h_only_single_axis`, `a2_v_only_single_axis`. The three Klangfilm HV `a*` configs search **no
key at all** (box sample 0/0/0) — they are controls, and a card on them is only informative for the
record/shape checks.

Proposal files: `space_cards/proposals/<lane>__space_v1.yaml` (+ `.report.json`); one subdirectory
per remaining lane. None is applied; the originals are untouched.

## 3. Categorical configs → one config per category (WP 5.2; needs owner approval)

- `examples/typologies/ath_core.yaml`: `bounds.morph_target: {lo: 1, hi: 3}` — searched inside a
  continuous box, so the optimizer sees a staircase and CMA spends a dimension on it.
  `ath_core.yaml:46` even says `morph_exponent` is "active only when the searched target becomes 3".
- `examples/studies/rear_density_2026-11-13/ath_like_rear{1,1.5,2,2.5}.yaml`: same searched key.
- Proposal: **3 configs per source** — `morph_target` pinned 1 (rounded rectangle), 2 (circle),
  3 (superellipse) — 15 files total, each a new versioned name; `morph_exponent` searched only in
  the target-3 variant (the cards independently label it `inactive` → `fix` in the target-1 lanes).
  No original edited; nothing written until approved.

## 4. `search.record_gate` (implemented this pass, opt-in, off)

- `shadow`: adds `record_margin_mm` + `record_gate_agrees` per row only. `resample`: replaces an
  outside-record candidate before evaluation (seed never replaced). Default absent = today.
- Evidence for a switch: `record_shadow.py` over the 22 most recent lane runs = **0
  `record_inside_but_refused`**, 28 outside-but-ok, 429 record-build failures (all `route: null`,
  concentrated in rosse_rect r120/r50 and the two klangfilm_lame runs).
- Recommendation (senior review, unchanged): keep `shadow` on the lanes with records; do **not**
  switch `resample` until a lane's shadow report shows zero `record_inside_but_refused` **and** its
  route builds records at all. ext-throat is the first candidate (`R² 0.91` joint constraint).

## 5. Cross-family seeding residuals (`geometry/translate.match_descriptors`)

Targets are the best stored design of family A; B is fitted in its own box. Residuals in the
descriptor's own units (mm / deg); RMS is scale-normalised (mouth/height/depth in mm, angles in deg).

| A (best stored) | B | RMS | largest residuals |
|---|---|---:|---|
| `hl__biradial_es_style_v7` `d24016b7ab8a` | `hl__osse_rrect_fold_warm_v7` | **31.8** | depth **+83.0 mm**, h_halfwidth_mid −11.5 mm, v_halfwidth_mid +6.4 mm |
| `hl__biradial_es_style_v7` `d24016b7ab8a` | `hl__ext_throat_hvlaw_v7` | **11.6** | V wall angle +16.7°, mouth height +15.8 mm, depth +17.9 mm |
| `hl__ath_tritonia_landscape_v9` best | `hl__biradial_es_style_v7` | **4.2** | wall angles −5.7° both planes, h_halfwidth_mid +7.2 mm |

Reading: fold-warm's box is 83 mm away in depth from the biradial design — a B6 "matched-size"
comparison there would compare different sizes; the tritonia→biradial pair is the only one close
enough to call matched (mouth and depth within 2 mm, angles differ by ~6°).

## 6. Frequency counts actually used (record in every floor/B1 report)

`FREQ_GRIDS` at HEAD: **screen 12 points (500-10 000 Hz), verify 25 (300-16 000), final 36
(250-20 000)**. The plan's "18 / 29" is what a brief gets only when it sets
`screen_extra_hz` / `verify_points_per_octave`. Question for the owner: should the new home brief set
them, and to what?

## 7. Decisions still reserved to the owner

| ID | Decision | What it changes | Blocked work |
|---|---|---|---|
| **C1** | coverage target: keep v7 point 80×50 / v9 `mode: target` / v9 corridor (H 60-90, V 40-60) and V onset 700/1000/1250 | a new home brief file; rankings stay as today under (a) | stage-1 brief, rescore, floor, B1 selection |
| **C2** | constancy: strict / slope-limited / none | opt-in term + 116 dense points instead of 58 | 1.1 use, floor identity |
| **C3 / C3b** | dead bands; ripple window (listening window vs corridor width) | tolerances in the new brief only | stage-1 brief |
| **C4** | deliverable: one winner or a menu | report format | stage 7 |
| **C5** | protected list: confirm the 29 entries; decide the 4 no-evidence lanes; may refusal storms in protected lanes still stop? | queue/watchdog behaviour | WP 7.1 confirmation |
| **C6** | solve budget: B1 20; equivalence 2; B2 12-16; B6 later | every GPU item | all GPU work |
| **provenance** | gate rebuilds on the geometry digest (recommendation) | recipe schema v2 | WP 0.9 digests |
| **envelope** | acoustic box vs build box (480 mm variant fits one, not the other) | brief gate definition | WP 0.9 / C1 |
| **U3 host** | best `ext_throat_hvlaw_v7` or best `biradial_es_style_v7` | which record goes to WP 4.2 | 2 + 12-16 solves |
| **§2 proposals** | approve / modify / reject each | config versions in `examples/` | stage-5 landing |
| **§3 categoricals** | approve the 3-per-source split | 15 new config files | WP 5.2 |

## 8. New defects found this pass (no fix applied)

1. **12 `examples/typologies/walls_relieved/*/*_w1.yaml` do not load**: `brief_file:
   '../../briefs/...'` is one `../` short. They are 12 jobs in the live `cd_rrect_2026-11-17` night.
2. **10 generator-route lanes cannot be carded**: `DesignSpace.from_config` refuses `rows` types
   `rosse_rect`, `rolled_rect`, `rolled_rect_pucker`, `crowe_panel`, `klangfilm_lame` although the
   mesher registry accepts them (pre-existing on `main`).
3. **`record_for_design` fails on those same routes** (429/2055 rows, `route: null`), so no record
   gate can be proposed there yet.
4. **The one-command evidence driver is ~10 h on the full `runs\2026111*` glob**; this pass used a
   bounded 22-run set.
5. **The handoff's "three known pre-existing failures" is incomplete**: `main` also fails
   `test_objective_v8`, `test_b8_lanes_bounded_gui` and 2 `test_night_bo_arm_wrapper` tests (files
   unchanged on this branch).
6. **Sampling sensitivity of the rebound rule**: b3_soft's `g_theta_h1_deg` trim fires on a 64-point
   box but not on 96 points (top slice 47 % vs >50 %). Any rebound proposal should state its n.

## 9. Pre-approval checks on the 14 changed proposals (shape-check + economy)

**Shape check** (`tools/shape_check.py`, all 14 proposal YAMLs, exit 0, log
`.evidence/shape_check_proposals.log`): every proposal meshes, is under its screen DOF cap, fits its
brief envelope and couples round to the driver exit. Dofs/cap and mouth (W x H mm, depth mm):
`atlas__ath_core` 3777/12000, 397x397, 359 · `atlas__core_law` 5179/12000, 552x399, 359 ·
`hl__ath_core_petal_hvlaw_v7` 3085/24000, 545x360, 353 · `hl__ath_tritonia_landscape_v7`
6774/24000, 480x380, 435 · `hl__crowe_x_osse_cd_v7` 4411/24000, 593x412, 263 ·
`hl__ext_throat_hvlaw_v7` 3709/24000, 528x366, 370 ·
`hl__lecleach_iwata_ar_landscape_smooth_v7` 1746/24000, 390x334, 239 ·
`hl__osse_rrect_fold_warm_v7` and `_w1` 3828/24000, 568x399, 359 ·
`rf__section_axial_home_v7` 3988/10000, 580x290, 274 · `p80x60__ath_core_14in_home700_v7`
8007/12000, 500x660, 451 · `p80x60__ath_core14_corelaw_v7` 6568/24000, 541x628, 387 ·
the two `sab__lecleach_*` 1135/5000, 286x286, 159.

**Economy gate** (`tools/search_preflight.py --from-runs <newest same-name run>`, exit 0 on all 14):
- **seed in its own box: yes on every proposal**; no searched key missing from the seed.
- **`hl__crowe_x_osse_cd_v7`: `no_headroom`** — seed design hash `9b5428e6dec8` EQUALS the prior
  best. The bounds trim does not move the seed, so the run would start at the converged optimum
  (skill: a re-test unless it has a reason). Combined with "no tested sigma0 ≤ 15 % bad", the Crowe
  proposal needs `search.warm_start` + a stated refinement reason before a night.
- Every other lane: seed hash differs from the prior best (headroom by construction).
- **`history_unusable` on every lane with a history** — the warm-start reader refuses the run
  ("objective version/brief mismatch (run v7, this config v7)"), so the recommended sigma and the
  **expected in-basin hits cannot be computed**. Cause and the run-selection question are recorded in
  `NOTES_FOR_SENIOR.md` (2026-11-17 local orchestrator block). Do not read a missing hits number as
  a good one.
- `hl__osse_rrect_fold_warm_v7_w1`: no run exists, so no headroom check; its two links stay
  `data_agrees: unknown`.

**Caveat on §1's scope.** The `links.py` verdict was taken on the newest run that carries the same
`name:` string. That file is not always the run under the lane's current brief (see the note in
`NOTES_FOR_SENIOR.md`); the verdict "data disagrees" is therefore "under the newest same-name run",
which is still a refusal of the link, not a confirmation of it.

## D4-marking (2026-11-18): Crowe not queueable without warm_start + reason

`hl__crowe_x_osse_cd_v7` is **not queueable** as a fresh/no-warm-start search. Per the 2026-11-17
pre-approval entry it is `no_headroom`: its seed design hash `9b5428e6dec8` EQUALS the prior best, so
a bounds trim that leaves the seed in place does not create headroom and the run would re-test the
converged optimum. Any bound trim on this lane must be declared a refinement with `search.warm_start`
plus a stated reason; until then it stays out of the queue. This is an append-only evidence marking:
no config, brief, bound or queue file was changed here.

## C2 explanation (final corrected form, 2026-11-18, per senior section 3)

**Slope mode vs strict.** Slope mode fits a line in log-frequency with its tilt capped at
± `slope_max_deg_per_decade`, then penalises every deviation from that line
(`hornlab_search/objective/scalar_v9.py:619-647`): it allows a gentle tilt but still charges
wiggle. Strict penalises tilt AND wiggle around a flat level. Both use H plus
`cov_v_weight`×V from each plane's onset; in corridor mode the centre is clamped into the
corridor.

**What is measured.** The 116-point grid and the 0.205 J noise cost were measured for STRICT
only (N3 §method); slope is unmeasured. "0.113 vs 0.205" is the top-28 error between 18 and 29
solved frequencies — i.e. the plan's grids, not production's 12/25.

**Range choices (S1, replaces the withdrawn "CD lanes gain, non-CD lanes lose" phrasing, which
was unmeasured and classified by family):** strict on top of the v9 corridor keeps 13 of the top
20; strict and slope share 18 of 20; no first place survives every range choice.

**What J pays for today** [measured, `runs/*/search.ndjson`, sum(w·t)/J = 1.000; plus WP3]:

| Lane (brief) | Biggest terms in the top 20 | Top-20 J spread | Reading |
|---|---|---|---|
| `hl__biradial_es_style_v7` (kept v7 brief, `room_landscape_80x50_700_hf1440_v7`) | **`load` 55 % of J, nearly constant (3.47-3.59)**; `cov` only 9 % | **0.10 J** | the whole top 20 sits inside the measured frequency floor (sd ≈ 0.11-0.13 J) — statistical ties |
| `p80x60__ath_core14_corelaw_v7` (`room_80x60_700_hf1440_v7`) | `diag` 24 %, `flat` 22 %, `cov` 20 % | 1.11 J | differences are real, above the floor |

Under the v9 corridor J is mostly DI slope (77-92 % of J, 0 dB/decade target), and
`preferred_deg` scores nothing inside `[min, max]`, so only the bounds bite (WP3).

**Owner decision (2026-11-17 evening, supersedes the pending question):** keep v7 for the
nights' scoring; add v9 as a free second score on CPU — H 60-90° from 700 Hz, V 40-60° from
1000 Hz, loading on; constancy slope-limited, its noise floor measured on stored data before it
counts. Designs near the top under both scores are the safe picks; the nights' scoring does not
switch until a physical measurement (stage 2b) shows which score predicts a real horn better.
