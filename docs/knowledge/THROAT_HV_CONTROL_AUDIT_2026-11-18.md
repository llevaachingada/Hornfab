# Throat-region H/V control audit (read-only), 2026-11-18

Question: for asymmetric briefs (e.g. 90 H x 40 V), do generators change the cross-section near the
throat (z ~ 0, next to the compression driver), or only the flare end / mouth? Owner concern: H and V
cuts look the same near the throat.

Scope and method: static reading of `hornlab_search/design/generators/` (registry, grid, profiles,
rolled, klangfilm, crowe), `hornlab_search/design/params/knobs_native.py`, `hornlab_search/mesh/throat_check.py`,
`.claude/skills/hornlab-shape-check/SKILL.md`, and the example configs. No git commands, no solver runs.

Numeric check: NOT run. `scipy` is not installed here and `hornlab_mesher` (needed by the OSSE /
osse_rollback path) is not importable, so the generator kernels cannot be executed. The weight values
quoted below are hand-computed from the window formulas in code (smoothstep 3t^2-2t^3, smootherstep
6t^5-15t^4+10t^3, cubic-free power laws), not measured H/V half-widths.

Line numbers are `hornlab_search/design/generators/<file>` unless a path is shown.

## 1. Route inventory

Column key: "Near-throat H/V knobs" = knobs that differ between H and V (or vary with azimuth) and act
at z ~ 0 to 25% of length. "Mouth-only" = asymmetry that is zero or negligible before the mouth.

| # | Route | file:line | Axisymmetric by design? | Near-throat H/V-independent knobs (key, where it acts) | Mouth-only asymmetry knobs | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Typology registry, per-meridian (conical, exponential, hypex, tractrix, lecleach, spherical_wave, osse, splice, spherical_salmon, biradial, qtw_waveguide) | registry.py:77-101 (types, DEFAULT_KNOBS), :142 `_throat_blended`, :163 `build_meridian`, :242 `materialize` | No when `profile_v` != `same`. `same` = axisymmetric meridian | Per-prefix `h_*` / `v_*`: `a_deg` (osse, biradial, qtw), `fc_hz` (tractrix, lecleach, spherical_wave), `T`, `rm_mm` (whole length, linear). `{p}_throat_blend_mm` (registry.py:89, :142) acts on [0, L_b] per meridian. `perturb` increments `h_u*` / `v_u*` act from throat | None intrinsic. `morph_*` (mesher side, see row 17) | Near-throat control: YES | H and V both start at r0 (round throat). Differences grow from z=0 via each meridian's own wall. Throat blend is per prefix, so H and V can be blended differently. |
| 2 | GRID superellipse field (`rows` absent) | grid.py:61-64 (GRID_DEFAULTS), :399 `_shape_knobs`, :442 `_meridians`, :488 `_radius_field`, :561 `grid_points` | No: r = rH*rV / (|rV cos|^p + |rH sin|^p)^(1/p) blends H and V meridians at every station | `g_a1_throat` (and a2..a16): factor 1 + a_k(s) cos(2k phi), a_k(s) = (1-s) a_throat + s a_mouth (grid.py ~ :500). At throat H = r0(1+a1), V = r0(1-a1): a real throat H/V control, default 0. `g_pnorm` (default 2.0): changes the throat section for p != 2 but leaves H/V axis half-widths unchanged (diagonal only) | `g_a_k_mouth` (linear ramp in s, not a mouth-only switch). `g_term_side_mm` (grid.py ~ :600): axial rollback dz = -term cos^2(phi) w(s), w = smoothstep(s) = 0 at throat, 0.16 at 25%, 0.5 at 50% | Near-throat control: YES, but only via `a_k_throat`, which defaults to 0 | Round throat holds only when pnorm = 2 and all a_k_throat = 0. Mesher-side throat check exists (`mesh/throat_check.py`). |
| 3 | rows `lecleach` (Fourcade, fc split) | grid.py:2171-2190 (branch), :1304 `_rows_lecleach_hv_marches`, :1288 `rows_fc_law` | Yes when `fc_v_hz` is unset (grid.py docstring). Not when set | `g_fc_h_hz`, `g_fc_v_hz`: cutoff law 1/fc(phi) = cos^2/fc_h + sin^2/fc_v. Plane marches start at the shared throat angle a0 and r0, so the H/V rate differs from z = 0 | `g_stop_deg` and harmonic stop law (`stop_cos2k`, `stop_sin2k1`): end of march only | Near-throat control: YES via the fc split (uses the plane marches, not a mouth stretch) | The H/V difference is the expansion itself (grid.py:1330-1340 comment). Magnitude near the throat not measured. |
| 4 | rows `lecleach_mod` (lib-2 harmonic stop) | grid.py:1270 `rows_harmonic_law`, :2235-2250, :2546 (rows_per_azimuth) | No: stop(phi) and fc(phi) vary with azimuth | `g_fc_h_hz` / `g_fc_v_hz` through `rows_fc_law` (near-throat, from z = 0) | `stop(phi)` harmonic terms (a2, a4, b1, b3). Shapes only the end of the march | Near-throat control: YES via fc; stop is mouth/end only | Labeled reconstruction in grid.py docstring. Half-model only when b-terms are used. |
| 5 | rows `lecleach_asym` (odd-cosine single-sided) | grid.py:748-805 (knobs), :807 `_rows_eps_window`, :2204-2233 (march) | No, by design: r *= 1 + eps_m w(s) cos(phi) | `g_eps_start` default 0 (ROWS_KNOB_DEFAULTS, grid.py:202): window opens at throat. Weight w = 0 at arc 0 (throat exact), then smoothstep: w(10%) = 0.028, w(25%) = 0.156, w(50%) = 0.5. So eps_m at 10% of arc is 2.8% of its full value | Everything past ~50% of arc is near full strength | Weak near-throat control: TECHNICALLY YES (window starts at 0), practically MOUTH-WEIGHTED | Throat is exact by construction. Full ring needed for eps_m != 0 (grid.py docstring). Example: examples/typologies/lecleach_asym_odd.yaml, eps_m 0.2. |
| 6 | rows `lecleach_ar` (area-preserving AR stretch) | grid.py:1226-1267 (knobs, AR_t = 1 at :270), :1431 `lecleach_ar_profile`, :2325, :2578 | Quarter-only, doubly even in phi (AR swaps semi-axes at 90 deg) | None near throat: AR(0) = AR_t = 1 is locked | `g_AR_m` (ratio at mouth) and `g_p`. AR = 1 + (AR_m - 1)(l/L0)^p. H/V ratio = AR. Fraction of (AR_m-1) reached: p = 2 gives 1% at 10%, 6% at 25%, 25% at 50%, 100% at mouth | `g_p` large -> purely mouth | Throat-locked by design. Near-throat H/V only via small p (p ~ 1 gives 10% at 10%) | Area-preserving (y_h y_v = y^2). Labeled reconstruction. |
| 7 | rows `iwata_ar` | grid.py:1873 (knobs), :2267-2300, :2605 | Same AR law as row 6, AR_t = 1 | None near throat | `ar_m`, `ar_p` as row 6 | Throat-locked, same weighting as row 6 | Shares the AR_t = ROWS_AR_THROAT_RATIO constant. |
| 8 | rows `toroidal_rollback` | grid.py:2074 (knobs), :2299-2324, :2633 | Yes: span full forbidden (grid.py:2164-2166); axisymmetric by construction | None | None | None (no H/V knob) | Lip torus only; `r_lip_mm`. |
| 9 | rows `osse_rollback` (OS wall + superformula + flutes + curled lip) | grid.py:1912-1918 (defaults), :1939 knobs, :2010 `_rows_osse_rollback_marches`, :2030 a(phi), :2052 sf window, :2057 ripple window, :2663 rows_per_azimuth | No: a(phi) = a_h cos^2(ang) + a_v sin^2(ang) (grid.py ~:2030) | `g_a_h_deg`, `g_a_v_deg` (range 5-85 deg): each is the OSSE flare angle per azimuth, so H and V flare from the throat. `g_a_fold` / `g_a_union` change the angle law | `g_sf_m`, `g_sf_amt`, `g_sf_start` (default 0, grid.py:1916): superformula weight w(arc) opens at sf_start = 0, so it acts from the throat with smoothstep weight. `g_ripple_start` (default 0, grid.py:203/162) similarly. Lip (`r_lip_mm`, `wrap_deg`) is mouth only | Near-throat control: YES via a_h/a_v (flare angle). sf/ripple windows open at 0 but ramp weakly (same weights as row 5) | This is the route that answers the owner question best. Near-throat H/V magnitude not measured (mesher OSSE unavailable here). |
| 10 | rows `salmon_elliptical` / `salmon_axisym` (Salmon rows, fc split, pleats) | grid.py:2727 (rows_per_azimuth salmon branch), :1288 `rows_fc_law`, :200 ROWS_KNOB_DEFAULTS, :1008 ripple doc | Elliptical: No (fc split). Axisym: Yes | `g_fc_h_hz`, `g_fc_v_hz` (from z = 0, same law as row 3). `g_T` (shared march) | `g_stop_deg` (end of march). Mouth pleats: `g_ripple_lobes`, `g_ripple_amp_mm`, `g_ripple_start`, shipped range 0.7-0.95 of arc (grid.py:1008), default 0 | Near-throat control: YES via fc (same as row 3). Pleats: mouth-only in shipped range | `g_ripple_start` default is 0, but the shipped range starts at 0.7. Keep the shipped range when searching. |
| 11 | crowe_hv_area_aspect_v1 (H/V area + aspect, forward flare) | crowe_hv_area_aspect_v1.py:59-95 (keys, ranges), :176-222 (timing + gate), :257 (log aspect = log(w/h) * gate), :348 (section exponent 2 at hold) | No: H/V aspect gate, the intended cross-section change | `aspect_timing_u50` (range 0.15-0.75): timing of the aspect ramp, starts at u = 0 (throat). `throat_round_hold_mm` (default 0, not a search knob): optional circular hold | Area mid-window `(4u(1-u))^4` (:218) is mid-length | Near-throat control: YES, by design. Throat is round (gate = 0 at u = 0) | Hand-computed gate for u50 = 0.5: 0.9% at 10%, 10% at 25%, 50% at 50%. For u50 = 0.25: 10% at 10%, 50% at 25%. A smootherstep ramp, not a step. |
| 12 | crowe-section-study-v2 (`_crowe_section_v2.py`) | _crowe_section_v2.py:42-60 (`_profile`, `section_profiles`), SHAPE_KEYS (:14) | No: independent H and V raster meridians (`horizontal_mm`, `vertical_mm`), each rescaled from r0 | `width_mm` / `height_mm` (radial scale from r0 for each meridian, whole length). `h_depth_scale` (H depth, whole length). `throat_blend_mm` (shared, throat region, not per-plane) | `crown_mm` (transverse crown; placement not read in detail), `junction_power` (intersection; not read in detail) | Near-throat control: YES via per-plane meridians; `throat_blend_mm` is shared, so it does not create H/V difference by itself | Study (not Crowe's ES equation, per module docstring). Mesher OSSE used downstream. |
| 13 | klangfilm LAME H/V core | _klangfilm_lame_hv_core_v1.py:65-66 (keys), :86-88 (defaults), :142-148 `_lame_p`, :150 beak offsets | No: H and V meridians a(z), b(z) are separate, but the section exponent p(z) is SHARED | Per-plane meridians `a` / `b` (whole length from throat). Section exponent p(z) = 2 (ellipse) until `lame_start_frac` (default 0.25 of core), then ramps to `lame_p_mouth` at `lame_end_frac` | `beak_*` offsets are exactly zero before `beak_start_frac` (default 0.85, range 0.5-0.99), so mouth only | Near-throat control: YES via per-plane meridians. The shared p is locked to 2 for the first 25% | At the throat a = b = r0, so the section is round whatever the exponent. |
| 14 | rolled family (rolled_rect_v1 / rolled_family) | rolled_family.py:102 (window bounds), :119-122 `relief_window`, :141-158 (source check), _rolled_rect_v1.py:48 (throat_turn < rect_turn) | No: H/V relief and pucker amplitudes | `throat_turn_deg` / `rect_turn_deg` (rule at throat, not an H/V split). `pucker_h_mm`, `pucker_v_mm` act only inside the relief window | Relief window: `relief_start_s` must be in [0.15, 0.96) (rolled_family.py:102), so the first 15% of stations are unrelieved. Peak and end follow | NONE in first 15%. H/V relief starts at >= 15% of stations | Source-end check (rolled_family.py:158) refuses relief inside the source. This is the clearest case of a mid/mouth-only H/V knob. |
| 15 | biradial (US4308932A contour) | profiles.py:257 `biradial_contour`; registry.py:89 THROAT_BLEND_TYPES (includes biradial) | No: per-plane `a_deg` (notes: 38 H / 22 V example) | Per-plane `h_a_deg` / `v_a_deg` and `{p}_throat_blend_mm` (per prefix, registry.py:142). The blend starts the wall at the driver exit angle and lands on the patent contour at L_b | `n` (exponent, claim 14) acts along the whole contour | Near-throat control: YES (per-plane a_deg plus per-plane throat blend) | Notes in registry.py:83-88 say the blend was added to remove a throat kink (domed cap). |
| 16 | qtw_waveguide (arc-throat rule) | profiles.py:331 `qtw_waveguide`; registry.py `{p}_R_arc_mm`, `{p}_a_deg` | No: per-plane `R_arc_mm` and `a_deg` | Per-plane `R_arc_mm` and `a_deg` set the throat arc and turn; wall parallel at the throat perimeter | Straight bell after the arc | Near-throat control: YES (arc is the throat rule) | Labeled "per the published rule; not a claimed replica" (registry.py docstring). |
| 17 | Native morph (mesher-side, all families) | registry.py:93-101 (DEFAULT_KNOBS: morph_fixed 0, morph_rate 3); knobs_native.py:440-456 (formula) | Depends on the target. Morph target 2 = circle, 1 = rectangle, 3 = superellipse | `morph_fixed` default 0 "starts at the throat" (knobs_native.py:453). Factor = clamp((t - fixed)/(1-fixed))^rate: with rate 3 this is 0.001 at 10%, 0.016 at 25%, 0.125 at 50%, 1 at mouth | Default rate 3 makes the morph mouth-weighted | Near-throat control: WEAK (present from throat, but cubic) | ATH core starts its morph at the throat (crowe_hv_area_aspect_v1.py docstring around :40; throat_round_hold default 0). |
| 18 | OSSE / R-OSSE `aspect_ratio` (mesher-side) | mesh/throat_check.py:1-9 (docstring); knobs_native.py:307-318; families.py:66, :293-303 | No: `aspect_ratio` scales H and V half-widths. Documented to stretch the throat (24x36, 26x36, 41x36, 50x36 mm on 36 mm briefs) | `aspect_ratio` acts AT the throat, since the mesher scales the whole outline | None | Throat-locking rule, not a control: `aspect_ratio: 1` (and `exponent: 2` for R-OSSE) per hornlab-shape-check SKILL.md:37-40 | The one route where H/V difference at the throat is present and known to be non-round. Owner rule: keep round at the coupling plane. |
| 19 | MEH mid-ports | knobs_native.py:1300-1312 | Not a section control | None | Ports open as flush exits mid-range on OSSE walls | NONE for cross-section H/V | Port placement only. |
| 20 | multicell | mesh/build.py, mesh/step_build.py (not in generators/) | Not inventoried | Not read in depth | Not read in depth | NOT ASSESSED | Out of generator scope; no `multicell` type found in `design/generators/`. |
| 21 | ATH core / Tritonia pucker | knobs_native.py:799-810 (pucker notch, Tritonia sin(p)^12 19.3 deg); _rolled_rect_v1.py:122 (construction label: not ATH Tritonia) | Azimuth-varying (pucker vs p) | Tritonia pucker notch is azimuth-only, from the mesher side | Pucker controls `pucker_start_deg` (rolled, row 14) | Not verified near throat | Mesher-side; no generator code read for ATH core. |

## 2. Answers to the owner question

- Routes with a true near-throat H/V knob (differs between H and V, acts from z = 0): typology registry
  per-meridian knobs (row 1), biradial and qtw per-plane wall or arc (rows 15-16), crowe H/V aspect
  gate (row 11, round at throat by design), fc split in lecleach and salmon rows (rows 3, 4, 10),
  osse_rollback a_h / a_v (row 9), klangfilm per-plane meridians (row 13), crowe-v2 per-plane
  meridians (row 12).
- Routes where the near-throat H/V knob exists but is default-off or weak: grid superellipse
  `a_k_throat` (row 2, default 0), lecleach_asym `eps_start` (row 5, cubic weight), morph (row 17,
  cubic weight), lecleach_ar / iwata_ar (rows 6-7, throat-locked, p sets onset).
- Routes with no near-throat H/V knob: rolled family (row 14, relief starts at >= 15%), toroidal
  rollback (row 8), MEH ports (row 19), salmon pleats in their shipped range (row 10, 0.7-0.95).

## 3. Routes that most need a near-throat H/V control

1. rolled family (row 14): relief floor of 0.15 leaves the first 15% identical in H and V. Reusable:
   the relief window shape (`relief_start_s`, `relief_peak_s`). Genuinely missing: an early-onset
   pucker or relief term that is H/V-specific and starts at or near 0.
2. lecleach_asym / lecleach_ar / iwata_ar (rows 5-7): both use a smoothstep or power weight from the
   throat. Reusable: `eps_start` (already 0) and `p` (AR onset). Genuinely missing: an H/V-specific
   throat-region weight with a faster onset, e.g. a linear or linear-with-floor ramp.
3. Native morph (row 17): default cubic with morph_fixed 0. Reusable: `morph_fixed`, `morph_rate`
   (set rate near 1 for early onset). Genuinely missing: a native H/V-specific morph (currently
   axisymmetric, targets are whole-outline).
4. grid superellipse (row 2): `a{k}_throat` is the only H/V-specific throat knob and is default 0.
   Reusable as is. The owner should decide whether a(1)_throat should be searched.

Reuse candidates: window start fractions (`sf_start`, `ripple_start`, `eps_start`, `relief_start_s`,
`morph_fixed`), `throat_blend_mm` (per prefix in the registry), `a_k_throat`, and `aspect_timing_u50`.
Genuinely missing: a near-throat, H/V-specific wall or aspect term for the rolled family and the AR
rows, and a native H/V-specific morph.

## 4. Caveats

- Numeric H/V half-width comparison at 10/25/50/100% was not run (no scipy, no hornlab_mesher). The
  weights above are hand-computed from the code's window formulas.
- Mesher-side behaviour (OSSE aspect_ratio, native morph, multicell, MEH) is taken from docstrings
  and knob descriptions in this repo, not from the mesher source (not present here).
- "Searched" usage is not checked: whether a near-throat H/V knob is actually varied in configs was
  not audited.

## Parent-integrator addendum (2026-11-18): root cause in the OS family

- `a0` (throat angle) comes from one brief value, `driver.exit_angle_deg`, and `k` is a single scalar.
  Both are shared by every azimuth (`grid.py:449`, `grid.py:2037-2038`). Only the coverage angle
  `a(phi)` varies around the horn. [code-verified]
- Plain OS with r0=18, a0=2, k=1: H45 vs V20 gives an H/V half-width ratio of 1.5 at z=25 mm and 2.0
  at z=50. Raising the shared `k` to 6 cuts that to 1.13 and 1.44: a large `k` delays the H/V split
  in **both** planes together. [derived, numeric]
- `hl__ext_throat_hvlaw_v8`: `throat_ext_length_mm` (40-220, best ~80) adds a **round** tube ahead
  of the OS flare (`aspect_ratio: 1` locked). Its header records top-10 rows pinned at the old 60 mm
  lower edge, so the bound was lowered. Search pressure is to shorten the round section. [code-verified]
- Implication: give the throat its own H/V controls (`a0_h/a0_v` or `a0(phi)`, `k(phi)`, an
  elliptical or ramped throat extension), each with an H=V zero-control. Proposal only; needs owner
  approval before generator code changes.
