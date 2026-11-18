# Construction contract: rolled family, section pucker, and radial inward relief

Drafted 2026-11-18 against HornFab main @1d6ebc8. Read-only review of code and dossiers; no solves, tests or meshes were run in this pass. Labels: [published] [derived] [reconstruction] [original-hypothesis] [code-verified] [unverified].

## 1. Identity

| Construction | Route and code | Status |
|---|---|---|
| `rolled_family_rect_v1` (rows.type) | `hornlab_search/design/generators/rolled_family.py` (canonical), base `_rolled_rect_v1.py` | Parent rolled rectangle: [original-hypothesis] inspired by Crowe ES-600/450 appearance, not Crowe's equation. Relief: [original-hypothesis]. |
| `rolled_family_section_v1` (rows.type) | same resolver; base `hornlab_search/design/generators/_crowe_section_v2.py` | Parent section: [reconstruction] from approximate raster readings (`examples/prototypes/rolled_rect_2026-11-15/crowe_section_reference.yaml`). Relief: [original-hypothesis]. |
| Legacy `rolled_rect_pucker` / section pucker | `tools/geometry/section_pucker.py` (schema `section-pucker-study-v1`); CLI `tools/geometry/section_pucker_cli.py`; rect via `tools/geometry/rolled_rect_cli.py` | Axial-only dz relief; [original-hypothesis], ATH-inspired, explicitly not a Tritonia reproduction (module docstring). |

- Canonical rows type is dispatched by `is_family_spec` (`rolled_family.py:26-28`) through `grid.py:2806-2807`, `build.py:507-509`, `bo/encoding.py:206-212`, `bo/data.py:680-683`. [code-verified]
- `rolled_rect_pucker` is absent from `hornlab_search/design/generators` dispatch (grep: only `gui/data.py:3506` maps it to a CLI). Configs with that rows type are CLI-only. [code-verified]
- Dates: research dossiers 2026-11-15; configs 2026-11-15/16. No code path records a publication status.

## 2. Lineage (claim each ancestor supports)

| Source (as cited by the dossiers; not re-fetched here) | Supports | Does not support |
|---|---|---|
| Batik Tritonia page, `at-horns.eu/tritonia.html` [published] | Azimuth-dependent coverage design; radial OS-SE coverage variation then rounded-rectangle morph | Any H/V inward law or dz law used here |
| OS-SE paper [published] | r(z,phi) construction; smooth termination; source matching ideas | Rolled rollback (r(z) single-valued) |
| R-OSSE rev7 [published] | Separate axial/radial folded profile; why rollback needs a separate treatment | Rolled-family equations |
| ATH user guide [published] | No-shrink morph policy; rounded-rect dimensions | Rolled family (no morph in it) |
| Crowe ES-600/450 appearance [reconstruction] | Visual proportions only | Crowe's proprietary equation |
| Rolled-family master research [original-hypothesis] | Categorical base/mode; inward H/V law; quintic windows | Any published ATH morph |
| Section pucker research [original-hypothesis] | H/V axial placement on the section base | Radial law |

Rule: a hybrid is never attributed to a parent beyond the parent's law. The Tritonia page supports the concept of azimuth-dependent mouths, not the specific radial displacement formula. Family and YAML names are not evidence.

## 3. Operator order and coordinate spaces

Coordinates: z = axial (mm, from coupling plane), phi = azimuth in [0, pi/2] (quarter model), s = station, arc fraction on the parent centre curve, psi = normalized section angle, rho = radius in the x-y plane.

| # | Stage (code) | Space | Notes |
|---|---|---|---|
| 1 | Validate spec, mode, digest, driver, knob set (`_shape`, 73-116) | none | Mode must be explicit: smooth, radial, axial, hybrid (`MODES`, line 18) |
| 2 | Validate frozen parent (`kernel.validate_shape`, 101) | parent params | |
| 3 | Check relief window order and amplitude limits (102-113) | s, mm | start < peak < end, all in [.15, .96] |
| 4 | Source check at coupling plane (`_source_check`, 125-138) | rect: turn radians; section: s | Radius equals driver exit; tangent equals tan(exit angle) |
| 5 | Parent grid (`kernel.make_grid`, 149) | (phi, s, xyz) | Rect: equal-arc turns on the phi=pi/4 centre curve (`_rolled_rect_v1.py:113-116`); section: `meta['stations']` |
| 6 | Source-end station from throat blend (151-157) | s | Relief onset must lie after it (158-159) |
| 7 | Window W(s) (`relief_window`, 119-122) | s | Product of quintic clamped smoothsteps |
| 8 | Reject relief at last two stations (161-162) | s | Protects the attachment normal |
| 9 | Normalized angle psi from the ORIGINAL sheet (165) | psi | h(s)=x(phi=0,s), v(s)=y(phi=90deg,s) |
| 10 | Radial inward relief in x-y (163-172) | rho | Scales x,y only; rejects if it reaches the centreline (169-170) |
| 11 | Axial relief in z (175-177) | z | Adds to z only; psi is not recomputed |
| 12 | Forward-roll constriction check (178-183) | rho per row | Checks monotone rho only up to the forward (max-z) station |
| 13 | Outer shell from relieved inner (184-185) | xyz | Rect: `grid.grid_outer_points`; section: `kernel.outer_points` |
| 14 | Finite, normal, self-approach checks (186-192) | xyz | |
| 15 | Envelope extents vs brief (194-198) | mm | 2max|x|, 2max|y|, ptp(z) over both sheets |

Order and rollback. Steps 10 and 11 act on disjoint components (x,y versus z), and psi is taken from the unrelaxed sheet, so the hybrid result does not depend on whether radial or axial is applied first. [code-verified by reading; not tested] The returned rear edge ("rollback" after the forward roll) is not repaired and not constrained by step 12; it is protected only by the zero window at its last two stations (step 8). A constriction before the roll raises `GeneratorError` (183). Nothing is silently rolled back.

Mode legality (`rolled_family.py:110-113`): smooth = no relief; radial = inward only; axial = axial only; hybrid = both. In a radial-mode search, axial bounds must be exactly (0,0) (`validate_search_config`, 240-244).

## 4. Mathematics as implemented

Let W(s) = S((s-s0)/(s1-s0)) * S((s2-s)/(s2-s1)), with S(v) = v^3(10-15v+6v^2) clamped to [0,1] (`_rolled_rect_v1.py:17-20`). S is C2: its first and second derivatives vanish at 0 and 1. Defaults in configs: s0,s1,s2 = .5,.8,.96 (rect radial) or .3,.8,.96 (section radial).

Let psi = atan2(y/v, x/h) on the original sheet, with h,v as in step 9.

Radial (inward), units mm, angles radians internally:
- Offset: d_rho = W(s) * (H cos^2 psi + V sin^2 psi) * cos^2(2 psi), with H,V >= 0 and H,V <= .15*height_mm (`rolled_family.py:104-106, 167-168`).
- New rho = rho - d_rho; x and y are scaled by (rho - d_rho)/rho (`172-174`).
- At psi=0 the offset is -W*H; at psi=pi/2 it is -W*V; at psi=pi/4 it is exactly 0 (cos 2psi = 0). Every direction moves inward or stays put. z is unchanged.

Axial (signed), units mm:
- dz = W(s) * (Ha cos^2 psi + Va sin^2 psi) * cos(4 psi), |Ha|,|Va| <= .1*depth_mm (`107-109, 175-177`).
- Diagonal (psi=pi/4): dz = -(Ha+Va)/2 * W; axis: +Ha, +Va. Matches the master research worked example (H4,V6 gives -5 mm diagonal). [code-verified]
- Diagonal radial offset is zero, so the radial and axial modes are categorically distinct; a signed axial cosine must never be labelled radial ATH behaviour.

Area meaning: `rolled_family.py` computes no mouth area. The envelope uses bounding extents (step 15). Planar, curved-cap, or wavefront area belong to the stock grid/mesher, not inspected in this pass. [unverified]

Endpoint and derivative conditions: W and its first two derivatives vanish at onset and end, so the rear returned attachment is unchanged. The throat is protected by requiring onset after the throat blend (158-159) and by the source-tangent check (step 4). [code-verified; C2 by formula, not numerically sampled]

Angle conventions: phi is physical azimuth on the quarter model with mirror planes at phi=0 and pi/2; rect_turn_deg, throat_turn_deg and terminal_deg are degrees in YAML and radians internally; exit_angle_deg must lie in (0,45) (`_driver`, 58-60).

## 5. Parameter ownership

Rect (`rf__rect_radial_v7.yaml`, bounds block):

| YAML key | Operator | Effect | Status | Bounds and provenance |
|---|---|---|---|---|
| g_width_mm | parent | Mouth width | fixed | 542 fixed; prototype reference |
| g_height_mm | parent | Mouth height | fixed | 299 fixed |
| g_depth_mm | parent | Axial depth | searched | 230-246; proposed in config, no rationale in header |
| g_depth_h_ratio | parent | H/V depth split | fixed | .68; prototype |
| g_decay | parent | Spiral decay | searched | .65-.75; proposed |
| g_rect_exponent | parent | Rectangle exponent | searched | 10-14; proposed |
| g_rect_turn_deg, g_throat_turn_deg, g_terminal_deg | parent | Transition and rollback turns | fixed | 65, 25, 270 |
| g_inward_h_mm | radial | Inward H at peak | searched (conditional on mode) | 0-6; proposed |
| g_inward_v_mm | radial | Inward V at peak | searched (conditional on mode) | 0-8; proposed |
| g_axial_h/v_mm | axial | Signed dz | fixed 0 in radial mode | 0 |
| g_relief_start/peak/end_s | window | Position | fixed | .5/.8/.96; ordered bounds required |

Section (`rf__section_radial_v7.yaml`): seeds width 417, height 203, depth 198, h_depth_scale 1.0, crown 20, throat_blend 20, junction_power 32, inward 3/4, start/peak/end .3/.8/.96. The common box (depth 192-204, h_depth_scale .98-1.02, crown 18-22) and H/V ranges are from `SECTION_PUCKER_RESEARCH_2026-11-15.md` (owner visual study; "provisional" per that dossier). [unverified as acoustically justified]

Driver for all canonical configs: exit radius 18 mm, exit angle 2 deg, from `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`. The guard rejects a height bound at or below twice the exit radius (`validate_search_config`, 255-256).

Activity rules enforced: dormant position keys are refused when strengths can reach zero (`validate_search_config`, 248-252); width/height bounds must keep landscape (253-254); the position bounds must not overlap (245-247).

## 6. Zero-control identities

| Setting | Recovers | Exact or tolerance | Test |
|---|---|---|---|
| Rect, inward=axial=0 (any mode) | Frozen `_rolled_rect_v1` inner and outer | Exact array equality | `tests/test_rolled_family_geometry.py:41-66` (child interpreter loads frozen `tools/geometry` modules) |
| Section, inward=axial=0 | Frozen `_crowe_section_v2` inner and outer | Exact | Same parametrized test (`family` fixture covers rect and section) |
| Legacy section pucker H=V=0 | Parent grid and outer | Exact identity by early return (`section_pucker.py:44-46`) | `tests/test_tools_section_pucker.py:33` |
| ATH OSSE az terms zero | Plain a_deg wall law | Exact by skipped terms (`families.py:192, 197`) | Partial: `tests/test_design_azlaw.py:122` zeroes `az_a_sf_amp`; not read in full [unverified] |
| ATH morph_target = 0 | No morph | Config value 0 = none (`families.py:73`) | No dedicated identity test found in this pass |

Historical claim, not re-run: the section dossier reports 145 focused CPU tests passing with zero-pucker point-for-point identity. Treat as a dated report. [unverified in this pass]

## 7. Seeds and provenance

Canonical (`examples/typologies/rolled_family_2026-11-15/`): `rf__rect_control_v7`, `rf__rect_radial_v7` (3/4 mm), `rf__rect_radial_strong_v7`, `rf__rect_radial_wide_v7` (up to 30/40 mm inward, per the spiral-pucker note; check its header), `rf__rect_axial_v7`, `rf__section_control_v7`, `rf__section_radial_v7`, `rf__section_axial_v7`, `..._strong_v7`, `..._home_v7`, `..._home_v8`, `..._home_smooth_v8`. Provenance: header comments and `docs/research/typologies/SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15.md`.

Legacy (`examples/typologies/rolled_rect_2026-11-15/`): `rr__reference_v7` (rows type `rolled_rect`, "acoustic behaviour unmeasured"), `rr__pucker_hv_moderate_v7` and `_strong_v7` (rows type `rolled_rect_pucker`; axial; "not a Tritonia reproduction"), `rr__crowe_panel_es600_v7` (section reconstruction, "original Crowe CAD/equation not reproduced").

Prototypes (`examples/prototypes/rolled_rect_2026-11-15/`): `rect_reference.yaml` and `rect_pucker.yaml` (schema `rolled-rect-experiment-v1`, width 542, height 299), `crowe_section_reference.yaml` (manual raster readings of drawing 1148-01-001; "not CAD coordinates").

Note: the directory named in the request, `rolled_rect_2026-11-15`, holds the legacy rows types. The canonical configs sit in `rolled_family_2026-11-15`.

## 8. Objective fit

Both canonical and legacy rolled configs point to the same brief, `room_landscape_80x50_700_hf1440_v7.yaml` (description "objective v7": 80 H x 50 V target, vertical half-weighted, 700 Hz crossover, 600 W x 480 H x 480 D envelope). The family defines no score. Scoring comes only from the brief and objective keys, so no family-inferred objective is asserted here.

## 9. Verification status

| Level | Status | Evidence |
|---|---|---|
| Analytic | Window smoothstep, radial/axial diagonal values | Formulas read at `_rolled_rect_v1.py:17-20`, `rolled_family.py:167-177`; legacy test `test_quintic_window_boundaries_and_derivatives` (`tests/test_tools_section_pucker.py:75`) |
| Sampled | Bound corners and interior boxes, uniform 62/64 and corners 32/32 for section arms | Historical dossier only; `docs/queue/section_pucker_validation_2026-11-15.json` not opened here |
| Meshed | Not verified in this pass | Dossiers say assembled mesh tests are required; not confirmed |
| BEM / acoustic | None for this family | `docs/research/typologies/ROLLED_FAMILY_EVIDENCE_HANDOFF_2026-11-15.md:13` records an owner hold on all new solves; the rect reference says acoustics unmeasured |
| Measured | None | n/a |

Known gaps: no acoustic evidence; no scoring evidence; no mesh-convergence study (dossier states "not a mesh-convergence study"); the ATH Tritonia radial law is not reproduced.

## 10. CPU-first checks and open questions

Proposed CPU checks (no GPU, no solves):
1. Run `pytest tests/test_rolled_family_geometry.py tests/test_tools_section_pucker.py -q` once to confirm the zero-control and window tests still pass at this commit.
2. Numerically sample W and dW/ds at onset and end to confirm C2 (expected zero first and second derivatives).
3. Confirm at psi=pi/4 that the radial offset is zero and the axial offset is -(Ha+Va)/2 * W at peak, for both kinds.
4. Check that the rect station parameter is arc fraction on the phi=pi/4 centre curve, not on each azimuth row (see Q2).

Open questions for senior review:
- Q1. Rollback guard: step 12 checks monotone radius only before the forward roll. Should the returned lip also be checked for self-clearance by the family itself, or is that left to `check_self_approach`? [unverified]
- Q2. Station definition: rect s is arc fraction on the phi=pi/4 centre curve (`_rolled_rect_v1.py:113-116`); the section dossier says "reference vertical-meridian arc fraction". These are different meridians. Which is canonical for section?
- Q3. Normalization: the canonical radial path uses h,v from the original sheet at phi=0/90; the legacy section pucker uses h,v from the section sweep (`section_pucker.py:50-53`). Two normalizations exist for the same nominal law.
- Q4. Outward (negative H/V) relief is rejected in v1 (`rolled_family.py:104-106`). The spiral note proposes a recipe-level outward mode. Not implemented.
- Q5. Whether the rect parent's `_rolled_rect_v1.py` and `tools/geometry/rolled_rect.py` remain byte-identical; both carry the same SHAPE_KEYS. Not checked here.
- Q6. Owner hold: no new solves until lifted (`ROLLED_FAMILY_EVIDENCE_HANDOFF_2026-11-15.md:13, 246-253`).

## 11. Contrast with ATH-derived azimuthal configs (not the rolled family)

Both ATH configs are OSSE, not rolled, and use the same brief. Their azimuthal law is a native wall-angle law `a(p) = a_deg + az_a_sf_amp*SF(p) + az_a_cos_amp*|cos p|^az_a_cos_pow` (`hornlab_search/design/families.py:192-198`; knob doc `params/knobs_native.py:662-668`). It is not the rolled family's inward/axial displacement.

| Config | az_a_sf_amp | morph_target | Other azimuth keys | Relation to this contract |
|---|---|---|---|---|
| `examples/typologies/home_landscape_2026-11-15/hl__ath_core_petal_hvlaw_v7.yaml` | Seed 3.0, bounds 0-8 deg (searched) | 0 = none (inactive; `families.py:73`) | az_a_cos_amp 14 (0-25), az_a_cos_pow 2 (1-6); az_n_cos2 and az_s_cos2 fixed 0 | Wall-angle petal creases ("gentle", config header). No radial relief keys. |
| `examples/typologies/home_landscape_2026-11-15/hl__ath_tritonia_landscape_v9.yaml` | Key absent, so 0 by default (`families.py:154`) | 1 = rectangle, ACTIVE; shrinkage allowed | az_a_cos_amp -14.6; az_fold_v_deg -28.8 (width 23); az_fold_h_deg 0 (width 20) | "Kit-era anchored fold", warm-started from prior runs. Not the published Tritonia radial law. |

Points for the contrast: (a) az_a_sf_amp is a native hypothesis knob, not a published coefficient; the knob doc's "Ath CORE: a_deg 5, amp 35" is a note, and the core config was deliberately softened to 0-8 by owner review. (b) morph_target 0 means the morph is off in the core config; v9 has it on. (c) The OSSE az laws change wall angle in a(p), while the rolled family changes rho and z after the parent is built; the two must not be compared on a single parameter.

## 12. Immediate reading path

`docs/knowledge/README.md`; `docs/knowledge/typologies/experimental_morphs.md` (it states radial and axial relief are different mechanisms); `docs/research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md`; `docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md`; `docs/research/typologies/SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15.md`; `docs/research/typologies/ROLLED_FAMILY_EVIDENCE_HANDOFF_2026-11-15.md`.
