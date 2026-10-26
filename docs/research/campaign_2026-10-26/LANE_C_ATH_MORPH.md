# LANE C - ATH / Morph / FREEFORM audit (2026-10-26)

Repo: `C:\Users\hunte\Hrns\hornlab-search`, branch `unified-typologies`. The ATH work is
uncommitted from another lane and was READ ONLY; no repo file was edited. All scratch
artifacts live under `...\scratchpad\audit_ath\`. Interpreter: `.venv\Scripts\python.exe`.
NO GPU solve, no Julia, no `search/run` without `--dry-run`. Every number below is a CPU
mesh-only probe (`epw 6`, `f_max 8000 Hz`, quarter domain, screen mesh) unless labelled
[E]. Probe harness: `probe.py`; raw rows: `out_*.jsonl`.

Number key: `[M]` = measured here with the real mesher (CPU, epw 6, 8 kHz); `[E]` =
estimated/inferred from formula or geometry (not meshed); `[L]` = repo's own measured limit
(fused CUDA ladder); `[G]` = given by the brief/config, not a measurement. If a numeric
result in sections 0-4 or 7 is not tagged inline, it is [M] when it is a mesh/dof/time/
failure count from `out_*.jsonl`, and [L] when it is one of the fused-CUDA caps.

---

## 0. Verdict first

1. **R-OSSE + pinned native morph is the best geometric fit for every campaign brief.**
   With `wall_thickness_mm: 5` explicit, `morph_target: 1` pinned and the target set to the
   brief mouth, all four briefs mesh inside their envelopes at 3,557-9,687 dofs [M]:
   B1 3,557 / B2 9,687 / B3a 7,468 / B3b 6,611. The R-OSSE base config currently omits
   `wall_thickness_mm`; the mesher default is 6 mm (`config_builder.py:838-845`), and that
   default - not the morph - is what made the first R-OSSE morph probes fail the shell
   self-intersection guard. Fix the config, not the morph.
2. **OSSE baseline + native morph is the second-best family**: B2 is clean (0/18 refusals,
   5,100-8,885 dofs [M]), B3b is usable but 9/18 envelope failures, B1 is 8/18 envelope
   failures, and B3a is 11/18 over the 12,000-dof safe line [M]. It is a mouth-outline/size
   family, not a coverage fix.
3. **`ath_core` cannot honestly serve 90x60 briefs.** It is a 25.4 mm, 50x50, aspect-1.0
   recipe. B1/B2/B3a/B3b all refuse at load because the brief pins 17.78/12.7 mm against the
   config's 25.4 mm pin [M]. Its `a_deg` 16-32 cannot reach 45 deg, and `aspect_ratio` is
   pinned 1.0, so it cannot represent 90x60 either. Patched to 1.4 in, it can serve B3a
   (measured 9,851 dofs, 706x706x451 [M]) - that is a new `ath_core_14in` variant, not this
   config.
4. **TwinRay 380 cannot scale to B2/B3.** L is bounded 160-240 and the a bounds cap the raw
   mouth at 494x399 mm [M]; B2 needs 529x794, B3a 706x706, B3b 470x706 [G]. Its B1 seed
   (496x337 landscape) is refused by the 360x520 envelope [M]. It is a 380x303 / 580 Hz
   device; run it only on its own brief.
5. **B1 is the genuinely over-constrained brief.** A 90x60 target with a 332x498 portrait
   mouth [G] is the inverse of the 90x60 flare aspect. A single-`a` OSSE/R-OSSE cannot be
   nominal 90 deg H / 60 deg V in a 360 mm-wide, 400 mm-deep box; morph can force the outline,
   but the H flare is then either shrunk (raw > target) or the nominal H coverage is about
   42 deg [E, from 2*atan(aspect*tan(a))], not 90 deg. The honest fix is a FREEFORM per-plane
   profile with independent effective H/V depth, or a wider/shallower envelope. B2/B3b have
   the same portrait-vs-coverage mismatch but their envelopes are larger, so R-OSSE+morph fits
   them geometrically; coverage still needs a BEM seed check.
6. **`morph_target` should be pinned per campaign cell.** As a rounded CMA gene it is a
   discontinuous categorical: a uniform unit box gives 50 % target 2 / 25 % target 1 / 25 %
   target 3 [M, 20k draws], and a sigma0 = 0.25 step flips the target 15.8 % of the time
   [M, 200k draws]. Target 2 also uses max(half_w, half_h), which expands the narrow axis and
   breaches portrait envelopes. Run three cells (or one product cell) with `search: false`.

---

## 1. What each knob does, and what f0 derivation overrides

### 1.1 OSSE (`ath_core`, `osse_baseline`, `osse_axi`)

| Knob | Plain physics | Current ath_core seed / lo-hi [G] |
|---|---|---|
| `L_mm` | Axial depth of the main OS section. With fixed `a`, mouth radius grows about `L*tan(a)` plus the SE term. It sets both mouth size and LF loading; a small L hi is a hard mouth cap. | 260 / 210-320 |
| `a_deg` | Main-flare half-angle (mesher convention). Sets HF coverage and how fast the mouth grows. CORE's published law is azimuthal; 24.2 is the H/V midpoint. | 24.2 / 16-32 |
| `a0_deg` | Throat wall half-angle; matches the driver exit. CORE's 1.2 deg is a very slow expansion. | 1.2 / pinned |
| `n` | SE termination exponent: how long the OS wall is kept before the terminal flare; higher = later, more abrupt termination. | 6.75 / 3.5-9 |
| `s` | SE termination amplitude. 0 = plain OS (no added mouth flare); CORE 0.715. | 0.715 / 0.25-0.95 |
| `q` | SE truncation coefficient (0.99-1.00 typical per the OS-SE paper). Lower q shortens the terminal arc. | 0.996 / 0.96-1.0 |
| `k` | Throat expansion factor: 1 = exact OS throat, <1 conicalises, >1 emulates a larger throat radius. | 1.0 / 0.6-1.6 |
| `s1`, `s2` | Throat-stretch length and sharpness (CORE 1.14 / 0.025). Adds axial length and rounds the throat transition; they also stretch the bbox depth (~+93 mm on CORE [M]). | 1.14 / 0-2, 0.025 / 0-0.06 |
| `exponent`, `aspect_ratio` | Cross-section superellipse exponent and width/height scale. aspect > 1 = landscape, < 1 = portrait. The current aspect >= 1 bound blocks every portrait brief (B1/B2/B3b all need about 0.67 [E]). | 2.0 / pinned 2; 1.0 / pinned 1 |
| `morph_target` | 0 off, 1 rounded rectangle, 2 circle, 3 superellipse. Ath documents 0/1/2; 3 is the mesher extension. | 1 / 1-3 |
| `morph_width_mm`, `morph_height_mm` | Full target mouth dimensions; 0 = raw mouth extent (circumscribed target). | 397 / 300-500 |
| `morph_corner_mm` | Rounded-rectangle corner radius; Ath default 35 mm, CORE 16.5. | 16.5 / 4-40 |
| `morph_exponent` | Superellipse exponent only for target 3; 2 = ellipse, 4 ~ rounded rect, 12 ~ rectangle. | 4 / 2-8 |
| `morph_rate` | Blend power `(t-zb)^rate`; Ath minimum 1 (higher = more gradual, later transition). | 3 / 1-6 |
| `morph_fixed` | Fraction of the horn from the throat kept raw (`zb`). 0 = morph starts at the throat. With fixed > 0 and a shrinking target, the raw section can bulge outside the target before the morph pulls it in [M]. | 0 / 0-0.5 |
| `morph_allow_shrinkage` | 0 auto-enlarges the target to the raw extent (Ath default); 1 allows a smaller target. Shrinkage is what lets a target fit a smaller envelope, but it changes the effective flare. | 1 / pinned 1 |

**What the f0 derivation actually does** (`config.py:878-1020`): only for configs with a
`generator:` block. For `profile: osse` it sets `{h,v}_a_deg = min(coverage/2, 45)`, clamped
to the existing bound. It does NOT set `L`, `r0`, `aspect_ratio`, `n/s/q/k`, or the morph
knobs. For conical/exponential/hypex it sets `rm = K-law d/2` (clamped to envelope minus
2*wall and to the knob bound); for biradial it sets `rm = max(K-law, r0 + tan(a)L)` and may
widen the bound; for rows it sets `fc` from the mouth x fc invariant. Native OSSE/R-OSSE/ICW/
FREEFORM configs get only the feasibility record (`feasibility` block), no seed change. It
also writes the objective-v3 below-f0 mask. Consequence: on `ath_core`/`osse_baseline`/
`rosse_baseline`, B1-B3b do not re-aim L or the mouth at all; on `perturbed_osse_hv` and
`ath_twinray_380`, `a` is re-aimed but L stays 90-140 / 160-240, so the mouth cannot reach the
brief. That is the measured root cause of the "won't scale" behaviour.

### 1.2 R-OSSE (`rosse_baseline`)

R-OSSE is a parametric, rollback-capable free-standing profile; its depth is derived, not
entered. The published sample is R 130 mm, a 39 deg, a0 7.5 deg, k 1.8, r 0.3, b 0.3, m 0.8,
q 3.7, giving a 260 mm wide, <80 mm long device. `R` sets size (and therefore depth), `a` is
the nominal coverage half-angle, `k` the throat expansion factor (0.5-4 shown in the paper),
`q` the throat-shape/blend exponent (not OSSE saturation), and `m/r/b` the axial-curve/apex/
bending shapes. `tmax` truncates the curve (<1 = smaller mouth, less rollback). `aspect_ratio`
scales the cross-section exactly as for OSSE; the current aspect 1-2 bound blocks portrait
mouths. Morph keys mean the same as above. Current `rosse_baseline` bounds [G]: R 80-220,
a 5-55, a0 2-30, tmax 0.5-1, k 0.3-2.5, q 0.5-2, m 0.3-1.5, r 0.1-1, b 0-0.5, exponent 2-8,
aspect 1-2; r0 pinned 12.7; `wall_thickness_mm` ABSENT -> mesher 6 mm [L].

### 1.3 Generated per-plane OSSE (`ath_twinray_380`, `perturbed_osse_hv`)

Same OSSE knob meanings, but `h_` and `v_` are independent, so H and V can have different
coverage/flare. `L_mm` is shared. `mouth_exponent` is the generator's superellipse mouth
(a non-native alternative to morph). `perturbed` adds `h_u0...h_u6`, `v_u0...v_u6`: monotone
increments `exp(u)` on the parent profile, |u| <= 0.25; they also move the mouth size and are
the main source of corner/curvature mesh refusals (14 of its 18 dims).

### 1.4 FREEFORM (`freeform_sculpt`, `freeform_hv`)

Control points are `[z_mm, r_mm]` anchors per meridian; z is pinned/monotone, r is searched.
`mouthAngleDeg` is the final wall angle from the axis (half-angle), `throatAngleDeg` the
initial one. A 40 deg TOTAL pattern needs about 20 deg half-angle, so the shipped 35-70 deg
range cannot make it - the proposed 12-35 deg is correct for narrow patterns. For a 90 deg
total pattern about 45 deg is correct, so 35-70 is fine there. `exponent` is the superellipse
mouth station (2 = ellipse, 4+ = squarer). `freeform_sculpt` currently searches 8 anchor
radii (4H + 4V), 2 mouth angles, 1 exponent = 11 dims; radii are forced non-overlapping so
the spline cannot pinch.

---

## 2. Per-config recommended campaign seeds/bounds

All recommended values are geometry/dof recommendations, not claims that the polar meets the
target. Coverage on the portrait briefs must be verified with one GPU seed solve before a long
campaign; that solve was out of scope here.

### 2.1 `ath_core` - CORE 50x50 cell only

| Knob | Current [G] | Recommended CORE campaign [G] | Reason |
|---|---|---|---|
| `L_mm` | 260 / 210-320 | 260 seed; 230-300 | Published recipe; wider only if the owner accepts a different CORE size. |
| `a_deg` | 24.2 / 16-32 | 22-27 | Published H/V 25.0/23.4; 16-32 is already wider than practice. |
| `n` | 6.75 / 3.5-9 | 6-7.5 | Published H/V 7.5/6.0. |
| `s` | 0.715 / 0.25-0.95 | 0.60-0.83 | Published H/V 0.83/0.60. |
| `q` | 0.996 / 0.96-1 | 0.99-1.0 | OS-SE typical 0.99-1.00. |
| `k` | 1.0 / 0.6-1.6 | 0.9-1.2 | k is a family shape; CORE uses the standard OS throat. |
| `s1`, `s2` | 1.14/0.025; 0-2 / 0-0.06 | 1.0-1.3 / 0.015-0.035 | Published throat extension; wider boxes just add depth. |
| `aspect_ratio` | 1.0 pinned | 1.0 pinned | CORE is circular-base; the morph owns the outline. |
| `exponent` | 2.0 pinned | 2.0 pinned | Circular base. |
| `morph_target` | 1 / 1-3 | 1 PINNED | Product recipe; avoids the 50 % circle cell. |
| `morph_width/height` | 397 / 300-500 | 380-430 | Published raw extent. |
| `morph_corner` | 16.5 / 4-40 | 10-30 | Published 16.5. |
| `morph_rate` | 3 / 1-6 | 2-4 | Ath default 3. |
| `morph_fixed` | 0 / 0-0.5 | 0-0.1 | Keep the morph from the throat to avoid a raw bulge. |
| `morph_allow_shrinkage` | 1 pinned | 1 pinned | Explicit target. |
| B1/B2/B3b | - | NOT SERVED | r0 pin refuses; a/aspect cannot do 90x60. |
| B3a | - | new `ath_core_14in`: r0 17.78, a 42-48, L 320-380, aspect 1.0, morph 680-730 | Measured 9,851 dofs, 706x706x451, fits 740x740x650 [M]. |

### 2.2 `ath_twinray_380` - own TwinRay cell only

| Knob | Current [G] | Recommended [G] | Reason |
|---|---|---|---|
| `L_mm` | 192 / 160-240 | 185-200 | Published 192; do not let the search move the published mouth. |
| `h_a_deg` | 34.7 / 22-46 | 33-37 | Reproduces 380 mm width. |
| `v_a_deg` | 25.9 / 16-40 | 24-28 | Reproduces 303 mm height. |
| `h_s`, `v_s` | 0.60 / 0.25-0.95 | 0.55-0.65 | Inferred termination. |
| `h_n`, `v_n` | 6.0 / 3.5-9 | 5.5-6.5 | Inferred. |
| `h_q`, `v_q` | 0.996 / 0.96-1 | 0.99-1.0 | Typical. |
| `h_k`, `v_k` | 1.0 / 0.6-1.6 | 0.9-1.1 | Standard OS. |
| `mouth_exponent` | 4 / 2-12 | 3-6 | Product is a rounded rectangle; 4 is the inferred seed. |
| B1-B3b | - | NOT SERVED | Measured max raw mouth 494x399 at L240 [M]; B1 seed 496x337 refused. L 240 is the binding cap; reaching B2/B3 would need L about 450-600 and a different design. |

### 2.3 `perturbed_osse_hv_fusedcuda` - own 1-inch hifi cell only

| Knob | Current [G] | Recommended [G] | Reason |
|---|---|---|---|
| `L_mm` | 120 / 90-140 | 110-170 | Its own 400x300x220 envelope; B1-B3b need 400-650, outside this config's purpose. |
| `h_a_deg`, `v_a_deg` | 45/30; 35-50 / 20-35 | 38-50 / 26-35 | Its brief is `hifi_90x60_1in`; the config target says 90x90. |
| `mouth_corner_mm` | 30 / 5-60 | 5-45 | Measured 24-41 % mesh refusals, almost all "corner exceeds local limit" above about 45 [M]; hi 60 is over-constraining the mesh, not the design. |
| `h_u0...h_u6`, `v_u0...v_u6` | 0 / -0.25-0.25 | -0.15-0.15 | The 14 u dims dominate; +/-0.25 produces curvature/corner refusals [M]. |
| B1-B3b | - | NOT SERVED | Measured mouths 211-445 x 163-280 [M]; all far below 529x794 / 706x706. L 140 is the binding cap. |

### 2.4 `freeform_sculpt` - own 90x90 cell, and a new narrow cell

| Knob | Current [G] | Recommended 90x90 (B3a-like) [G] | Recommended narrow (B2-like 60x40) [G] | Reason |
|---|---|---|---|---|
| `profileH.points.1..4.1` | 22-55, 58-105, 108-160, 163-200 | up to 250, 300, 330, 355 | up to 200, 230, 250, 265 | Current 200 mm mouth cap is the binding bound; B3a needs 353, B2 needs 265 [E]. |
| `profileV.points.1..4.1` | same | up to 250, 300, 330, 355 | up to 260, 320, 360, 397 | Same. |
| `mouthAngleDeg` | 35-70 both | 35-55 | 12-35 | 90 deg total needs about 45 deg half-angle; 40 deg total needs about 20 deg, so 35-70 blocks it. |
| `exponent` | 2-8 | 2-8 | 2-8 | Mouth squareness. |
| `z` anchors | 0/45/95/145/195 | add z=350-450 | add z=450 | Current 195 mm depth cannot hold the PA briefs; the 5-anchor z schedule is pinned by the config, not searched. |
| B3a | - | conditional: mouth 353, L about 350, angle 45 | - | Measured current seed 370x370x201 / 2,739 dofs [M]; too small at f0 400. |
| B2 | - | - | conditional: mouth 265x397, L about 450, angle 20 | Measured current mouth 338-397 [M]; 1/17 curvature refusal. |

### 2.5 `freeform_hv` - demo only

Current [G]: H mouthAngle 40-90, V 40-80, exponent 2-8, radii fixed 160/110, L120; seed
320x222x126, 1,430 dofs [M]. Recommended: do not campaign on B1-B3b. For a narrow B2-like
study, widen mouth angles to 12-90 and radii/L, which is a new config.

### 2.6 NEW A: `osse_baseline` + native morph

Seed for each brief [G]: `r0` = brief exit; `a_deg` = coverage_v/2 (B1 30, B2 20, B3a 45,
B3b 30); `aspect_ratio` = W/H (0.667, 0.667, 1.0, 0.676); `L_mm` = 0.75*depth (300/338/488/450);
`n` 4, `s` 0.7, `q` 0.995, `k` 1, `s1=s2=0`; morph target 1, width/height = brief mouth,
corner 35, rate 3, fixed 0, allow shrinkage 1; `wall_thickness_mm 5`.

| Knob | B1 [G] | B2 [G] | B3a [G] | B3b [G] |
|---|---|---|---|---|
| `L_mm` | 200-300 | 300-430 | 300-400 | 320-430 |
| `a_deg` | 26-34 | 26-34 | 40-50 | 26-34 |
| `aspect_ratio` | 0.62-0.72 | 0.62-0.72 | 0.97-1.03 | 0.63-0.72 |
| `n / s / q / k` | 2.5-6 / .3-.9 / .98-1 / .8-1.2 | same | same | same |
| `morph_w x h` | 320-345 x 480-510 | 500-545 x 760-800 | 690-730 x 690-730 | 450-490 x 680-720 |
| `corner / rate / fixed` | 25-60 / 2-4 / 0-0.1 | same | same | same |
| Seed dofs [M] | 4,395 | 7,014 | 12,638 | 9,093 |
| Usable LHS fraction [M] | 9/18 (1 mesh + 8 env fail) | 18/18 | 5/18 under 12k and inside env | 8/18 (1 mesh + 9 env fail; 1 over 12k) |

B1 is conditional: the seed fits only because the morph shrinks the raw H flare (raw H about
643 mm at a 30/aspect 1.73 [M]; target 332 [G]). With aspect 0.667 the nominal H is about
42 deg [E], not 90. Do not claim 90x60 coverage from this geometry.

### 2.7 NEW B: `rosse_baseline` + native morph (primary recommendation)

Set `wall_thickness_mm: 5` explicitly (the base config's absent key means 6 mm and causes
shell self-intersection on shallow large-mouth targets [M]). Pin `morph_target: 1`; set
`morph_allow_shrinkage: 0` (targets equal the raw mouth); `aspect_ratio = W/H`;
`a_deg = coverage_v/2`; `R_mm = H/2`.

| Knob | B1 [G] | B2 [G] | B3a [G] | B3b [G] |
|---|---|---|---|---|
| seed `R_mm`, `a`, `aspect` | 249, 30, 0.667 | 350, 20, 0.667 | 353, 45, 1.0 | 353, 30, 0.676 |
| `R_mm` bounds | 235-260 | 330-355 | 340-370 | 335-365 |
| `a_deg` | 28-32 | 18-22 | 42-48 | 28-32 |
| `aspect_ratio` | 0.64-0.70 | 0.64-0.70 | 0.97-1.03 | 0.65-0.70 |
| `tmax` | 0.9-1 | 0.9-1 | 0.9-1 | 0.9-1 |
| `k / q / m / r / b` | 0.8-1.2 / 0.8-1.2 / 0.7-1.0 / 0.3-0.5 / 0.15-0.25 | same | same | same |
| `morph_w x h` | 320-345 x 480-510 | 510-545 x 770-810 | 690-730 x 690-730 | 450-490 x 680-720 |
| `corner / rate / fixed` | 25-60 / 2-4 / 0-0.1 | same | same | same |
| Seed dofs / depth [M] | 3,557 / 204 | 9,687 / 454 | 7,468 / 170 | 6,611 / 289 |

Caveat: for the portrait briefs (B1/B2/B3b), `aspect = W/H` makes the nominal H coverage
about 42/27/42 deg [E, from 2*atan(aspect*tan(a))], not 90/60/90, because the mouth aspect is
the inverse of the coverage aspect. The geometry and mouth are right; whether the polar holds
the requested H coverage is the one thing a CPU mesh cannot prove. Run one BEM verify seed
before committing a campaign. B3a is the clean case: square, aspect 1.0, a 45, nominal 90x90.

---

## 3. Compatibility matrix (8 kHz dofs [M]; brief sizes [G]; caps [L])

| Config | CORE (50x50 2in) | B1 (90x60 850 1.4in) | B2 (60x40 800 1in) | B3a (90x90 400 1.4in) | B3b (90x60 600 1.4in) |
|---|---|---|---|---|---|
| `ath_core` | YES 3,777; LHS 2,832-4,674; 0/17 fail | NO load refuse (r0 25.4 vs 17.78) | NO load refuse (25.4 vs 12.7) | NO load refuse | NO load refuse |
| `ath_core_14in` (patched) | - | geometry 4,892; 10/17 env fail; conditional | - | YES 9,851, 706x706x451 | not probed; needs aspect/morph |
| `ath_twinray_380` | - | NO seed 496x337 > 360 | mesh but undersized 1,831-3,629; mouth <=492x395 | mesh but undersized 1,660-3,770; mouth <=494x399 | mesh but undersized 1,660-3,269; mouth <=494x363 |
| `perturbed_osse_hv` | - | mesh but undersized 910-1,556; 41 % mesh refuse | undersized 856-1,835; 35 % refuse | undersized 910-1,977; 24 % refuse | undersized 910-1,977; 24 % refuse |
| `freeform_sculpt` | - | 2,739 but 370x370; env width 370>360 | 2,553-3,060 but mouth <=397; too small at 800 | 2,553-3,060 but mouth <=397 vs 706; fails at 400 | 2,553-3,060 but square; aspect wrong |
| `freeform_hv` | - | 1,430 but 320x222 | 1,336-1,511 but 320x222 | 320x222 | 320x222 |
| NEW osse+morph | - | conditional 3,026-6,079; 8/18 env | YES 5,100-8,885; 0/18 fail | EDGE 7,982-17,493; 11/18 >12k | YES 5,874-12,593; 9/18 env; 2/18 >12k |
| NEW rosse+morph | - | geometry YES 3,557; coverage unproven | YES 9,687; depth 454 | YES 7,468; depth 170 | YES 6,611; depth 289 |

Mesh time (median / max, s) [M]: ath_core 0.70/1.68; core14 1.13/5.88; TwinRay 8.8/28.2;
perturbed 2.0/4.6; sculpt 1.3/2.2; ffhv 0.8/2.2; osse+morph 2.3/12.5; rosse+morph 1.4/2.55.
TwinRay's superellipse generator is the slowest by 5-10x.

Failure rates [M]: ath_core CORE 0 %; core14 B1 6 % mesh + 59 % envelope; TwinRay 0-9 %
mesh but 100 % undersized; perturbed 24-41 % mesh (corner/curvature), 0 % envelope (because
it never reaches the envelope); sculpt 6 %; ffhv 12 %; osse+morph 0-6 % mesh, 0-50 %
envelope; rosse+morph 0/4 seeds failed with wall 5 (no LHS run yet).

---

## 4. R-OSSE / ICW morph mesh proof

**R-OSSE: mesh-proven for targets 1, 2 and 3.** 17/17 R-OSSE meshes passed [M]: target
1/2/3 at R 155 and R 397, walls 5.0 and 2.5 mm, B2 529x794; plus target 1 at R 350 (B2,
9,687 dofs / 454 mm) and R 353 (B3a/B3b). The two failures in the first matrix were
`wall_thickness_mm` absent -> mesher default 6 mm [L] -> shell self-intersection at the morph
corners; with 5 mm the same geometry passes. Action: add `wall_thickness_mm: 5` to
`rosse_baseline` (and `icw_termination`) and never leave the 6 mm default on a shallow,
large-mouth morph target.

**ICW: mesh-proven for targets 1, 2 and 3.** 6/6 ICW meshes passed at 529x794 [M] (three at
the 6 mm default wall and three at 2.5 mm; targets 1/2/3). The mesher prints "outer wall
self-intersects ... acoustic (inner) surface is unaffected" near azimuth row 0 on every ICW
morph mesh; the meshes still build. One additional ICW B1 seed was refused at load (r0 12.7
pinned vs 17.78), not a mesh failure [M]. Target 2 again becomes a circle of
max(half_w, half_h) and breaches a 560 mm envelope (794 mm measured [M]) - pin target 1 for
rectangular mouths.

So the handoff risk is settled: R-OSSE and ICW native morph are mesh-proven for 1/2/3. The
remaining risk is not routing or meshing; it is the wall-thickness default and the coverage
meaning of a portrait morph target.

---

## 5. `morph_target` as a CMA gene

`morph_target` is an int KeySpec and `DesignSpace.denormalize` rounds it (`space.py:147-153`).
With bounds 1-3:
- uniform unit box -> 50 % target 2, 25 % target 1, 25 % target 3 [M, 20k draws];
- at the seed target 1, a sigma0 = 0.25 mutation flips the target 15.8 % of the time
  [M, 200k draws].

The target changes the meaning of width/height/corner (target 2 uses the max half-dimension;
target 1 uses corner; target 3 uses exponent), so the objective is discontinuous across the
gene and CMA has no gradient to follow. Recommendation: pin `morph_target` per campaign cell
(`{lo: t, hi: t, search: false}`). For the PA briefs use target 1 (rounded rectangle) as the
product cell; run target 3 (exponent 3-6) as a second cell if the owner wants a superellipse
comparison; target 2 only for circular/axisymmetric mouths and always with
`allow_shrinkage: 1` and an envelope check. Do not spend a 15-dim search learning a 3-way
categorical.

---

## 6. Web sources actually fetched (status; only these are cited)

| URL | Status | Used for |
|---|---|---|
| https://at-horns.eu/core.html | 200 | Full CORE recipe: L 260, r0 25.0, a0 1.2, a/n/s laws, q .996, s1 1.14, s2 .025, morph target 1/fixed 0/rate 3/corner 16.5, roundover 42, wall 15, angular 100. |
| https://at-horns.eu/twinray.html | 200 | 36-10-380: 36 mm throat, 10 deg total, 380x303 mm mouth, 192 mm depth, LF point 580 Hz (20 % asymptotic throat resistance); other 266/212 models. |
| https://at-horns.eu/release/OS-SE%20Waveguide.pdf (also via https://r.jina.ai/) | 200 | OS-SE formula; q typical 0.99-1.00; s=0 no flare; n>=2; morph law `r + ((z-zf)/(L-zf))^I3 (rM-r)`; rate I3 >= 1; mouth rollback needed for free-standing. |
| https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf (r.jina.ai) | 200 | R-OSSE parameters and published sample R 130, a 39, a0 7.5, k 1.8, r .3, b .3, m .8, q 3.7; k 0.5/1/2/4 comparison; R sets size; 260 mm wide / <80 mm long example. |
| https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf (r.jina.ai) | 200 | Morph.TargetShape 0/1/2, TargetWidth/Height 0=raw, CornerRadius default 35, FixedPart 0-1, Rate minimum 1, AllowShrinkage default 0; 100 angular segments typical; 5-8 mm mesh at 10 kHz; rollback. |
| https://at-horns.eu/release/Ath-AP1.pdf (r.jina.ai) | 200 | ESP note; used only for the 1 in / 2 in HF directivity ceiling context (1 in about 16 kHz, 2 in about 8 kHz). |
| https://at-horns.eu/ | 200 | Link map to the above; confirms CORE/TwinRay are the published primary sources. |
| https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/ | 403 direct; r.jina.ai 293/error | BLOCKED; no claims used. The owner asked for diyAudio practice; the site refuses this client. Primary ATH docs above are the better source. |
| https://www.diyaudio.com/forums/multi-way/354772-acoustic-horn-design-practical.html | 403 (r.jina.ai 288/error) | BLOCKED; no claims used. |
| https://html.duckduckgo.com/html/?q=diyaudio+ATH+OSSE+waveguide+parameters | 202 | No result HTML; not used. |
| Google/Bing queries (e.g. `site:diyaudio.com ATH OSSE waveguide`) | 200 but CAPTCHA/aggregator pages | Not used as sources. |

Published ranges vs our boxes: Ath documents morph rate >= 1 (our 1-6 is fine), corner default
35 (our 4-40 is fine), shrinkage default 0 (our ath_core pins 1 deliberately), q 0.99-1.00
(our 0.96-1 is slightly wide), R-OSSE k 0.5-4 (our 0.3-2.5 is narrower on the high side but
the paper's k=4 is a DI-slope trade, not a validity limit). The boxes that are actually too
tight for the campaign briefs are geometric, not Ath-practice: L, aspect, mouth radius/width,
and the missing wall_thickness_mm.

---

## 7. Over-constraining bounds vs physical limits

Over-constraints (binding, fixable):
- `ath_core.r0_mm` pinned 25.4 -> blocks all 1.4 in / 1 in briefs (hard ConfigError) [M].
- `ath_core.aspect_ratio` pinned 1.0 and `a_deg` hi 32 -> cannot represent 90x60/90x90.
- `ath_core.morph_width/height` hi 500 -> blocks B3a 706.
- `ath_twinray_380.L_mm` hi 240 -> hard mouth cap about 494 mm; B2/B3 need 450+ [M].
- `perturbed_osse_hv.L_mm` hi 140 -> hard mouth cap about 445 mm; B1-B3b need 400-650 [M].
- `perturbed_osse_hv.mouth_corner_mm` hi 60 -> 24-41 % local-curvature refusals; hi about 45 [M].
- `freeform_sculpt` mouth radius hi 200 and z max 195 -> hard cap 370x370x201 [M]; B3a needs
  353/350, B2 265x397/450 [E].
- `freeform_sculpt.mouthAngleDeg` 35-70 -> blocks any 40 deg total pattern (needs about 20).
- `osse_baseline` / `rosse_baseline.aspect_ratio` lo 1.0 -> blocks portrait mouths (B1/B2/B3b
  all about 0.67 [E]). The mesher handles aspect < 1; the bound is the limit.
- `rosse_baseline.R_mm` hi 220 -> B2 needs 330-355 [M].
- `rosse_baseline` missing `wall_thickness_mm` -> silent 6 mm default, shell failures [M].

Physical limits (do not fix by widening):
- B1 90x60 in 360x520x400: portrait mouth vs 90x60 flare aspect; a single-`a` OSSE cannot be
  nominal 90 deg H / 60 deg V without shrinking the H mouth below its raw flare [E]. Needs a
  FREEFORM per-plane effective depth or a larger/shallower envelope.
- B3a at 8 kHz: R-OSSE fits at 7,468 dofs; an OSSE at L 350 is 9,851 [M]; a deeper/larger
  OSSE crosses 12,000 [L]. The 8 kHz fused safe line is the real cap, not the shape.
- TwinRay 380 is a 380x303/580 Hz product; scaling it to 529x794 changes it into a different
  device, not a scaled TwinRay.
- R-OSSE depth is derived and much shallower than OSSE for the same mouth (B3a 170 mm vs
  OSSE 451 mm [M]). That is the formula, not a bound.

---

## 8. Risks / open questions

1. Coverage is unproven for portrait morph targets. The geometry/mouth/dofs fit, but the
   nominal H coverage from `aspect = W/H` is about 42/27/42 deg on B1/B2/B3b, not 90/60/90
   [E]. A BEM seed verify is required before a campaign; if it fails, the honest answer is
   "B1/B2/B3b need a freeform per-plane profile or a different envelope".
2. Morph shrinkage with `fixed > 0` can breach the envelope upstream even when the mouth
   target is inside it (measured: B3b LHS widths 554-857 mm with target width 490 [M]). Keep
   `fixed` 0-0.1 for shrinking cells, or set `allow_shrinkage: 0`.
3. Target 2 is not a free circle: it uses max(half_w, half_h), so a 2:1 rectangle becomes a
   circle of the long dimension (measured 794x794 on a 529x794 target, envelope breach [M]).
   Pin target 1 for rectangular mouths.
4. R-OSSE/ICW wall default: 6 mm when `wall_thickness_mm` is absent [L]. Set 5 mm (or 2.5)
   explicitly in the configs; otherwise shallow large-mouth morph targets fail.
5. TwinRay generator mesh time 3.4-28.2 s per candidate (median 8.8 [M]) versus 0.7-4 s for
   the native families. A 16-32-point probe is about 2-15 min per brief; budget accordingly.
6. The f0 derivation is not an envelope solver. It retargets `a` to coverage/2 and leaves L
   fixed; for fixed-size OSSE configs with small L bounds, the brief can never be reached.
   The next code change should either derive L from the envelope
   (`L = (mouth_half-r0)/tan(a)`) or flag `required_mouth > max_reachable_at_L_hi` before a
   campaign.
7. No GPU evidence in this lane by instruction. All dof/VRAM conclusions use the repo's
   measured fused limits (12,000 safe / 15,984 fits / 20,237 fails [L]), not a new solve.

---

## 9. Reuse

Scratch files: `probe.py` (mesh-only harness), `mk*.py` (job builders), `jobs_*.json`,
`out_*.jsonl` (raw rows), `web/` (fetched sources). No repo file was modified. To reproduce a
row: run `.venv\Scripts\python.exe probe.py jobs_<name>.json out_<name>.jsonl` from the repo
root; the harness writes only under this scratch directory and `%TEMP%`.
