# AUDIT LANE B - Salmon / X-shape rows typology family

2026-10-26. Repo `C:\Users\hunte\Hrns\hornlab-search` (branch `unified-typologies`), read-only.
Scratch: `...\scratchpad\audit_salmon\`. CPU only: no solve, no Julia, no `hornlab-search run/search`
without `--dry-run`; every number below comes from the pure-Python rows march or a real gmsh mesh
with the dof caps raised in a scratch config copy. No repo file was edited.

**Labels.** `[measured]` = produced this session by the commands in section 9 (or arithmetic on
those numbers, with the arithmetic named). `[estimated]` = extrapolated from measured numbers.
`[web]` = text fetched this session; maker performance wording is a claim, not a measurement.
`[inferred]` = physics reasoning, not measured.

---

## 0. Headline findings

1. **Every campaign brief derives the SAME square seed: fc_h = fc_v = 600 Hz** `[measured]`.
   The f0 derivation sets `fc = 1.88e5 / (mouth)` and clamps to the config's `[600,1200]`; for
   B1/B2/B3a/B3b the required mouths are 332-794 mm, so both fc's clamp to 600. A 90x60, a 60x40
   and a 90x90 target therefore all start as a 1:1 horn. The H/V aspect - the only mechanism the
   rows route has for a rectangular pattern - is destroyed by the lower bound, not by physics.
2. **The 1.88e5 constant belongs to the exact Fourcade/Le Cleac'h construction, not to this
   rows march.** The rows' own mouth product is `mouth x fc = 3.23e5 mm-Hz at stop 150`
   (2.57e5 at 120, 3.65e5 at 170) `[measured]`; the exact march gives 1.47e5 at 90 deg, 1.71e5 at 120, and saturates at ~1.87e5 by 150-360 deg (p1/p2, and the in-repo Fourcade reference case) `[measured]`. At the same fc/T/stop the rows
   horn is 1.29x fatter at 90 deg and ~1.75x at 150 deg. Consequences:
   - the campaign-brief seeds are ~1.7x too large in mouth, so they hit the envelope (B1/B3b
     overshoot 45-51% / 4-10%) and are clamped to 600/600;
   - the organic-brief geometry is fine in its envelope, but its claimed f0 is ~1.7x too high:
     420 mm H at 60 deg holds only ~35 deg if the mouth is the rim, or 60 deg at ~1.0-1.1 kHz.
3. **External check: commercial rollback-family horns sit at `mouth x fc = 2.7-3.8e5`** `[web +
   arithmetic]`: AudioHorn X21/25/28/33/34/40 = 294/313/350/380/271/306 (x1e3) mm-Hz; Auto-Tech
   JMLC-350 = 595 mm x 520 Hz = 309e3; IWATA-300 = 590 x 450 = 266e3. That is the rows' rim
   product (2.6-3.7e5), not 1.88e5. The 1.88e5 number is `mouth x cutoff`, and the commercial
   minimum frequency is ~1.5x the model number (JMLC-350: 520/350 = 1.49). Both facts are
   self-consistent: a r90 mouth of 1.88e5/fc holds a 90 deg pattern at 1.5 fc. The rows march is
   fatter than that construction, so the same equation under-seeds it.
4. **The stop upper bound 240 is worse than useless.** `[measured]` stop 190 deg reproduces the
   170 deg rim exactly, 230 reproduces 130, 240 reproduces 120: everything in (180,240] is a
   mirrored duplicate. Near 180 the march length and depth diverge (179.9 deg: L = 913 mm,
   3,654 steps; 90.5 deg: L = 239 mm, 958 steps) and the mesher cost explodes. The useful
   window is 120-155; 160-175 is deep/expensive; 178-180 is pathological.
5. **The X knob is a rim-lobe knob, not the AudioHorn diagonal fix, and it is expensive.**
   `[measured]` at the organic 1in seed (fc 1200/843.8, stop 150): x_amp 0 -> 270x383 mm,
   1,555 dofs, 0.49 s; +0.15 -> 320x358, 3,139 dofs, 0.75 s; +0.25 -> 330x377, 5,348 dofs,
   5.35 s; +0.30 -> 332x386, 6,013 dofs, 14.5 s; -0.30 -> 289x396, 4,839 dofs, 9.8 s.
   Positive = corner-out (literal X), negative = corner-in/plus. The lobes extend the
   axis-aligned bbox, not just the diagonal. The X costs 2-4x the dofs/mesh of the plain
   elliptical (mostly because +x_amp pushes the diagonal stop past 180: at base stop 150,
   +0.25 gives a 187.5 deg diagonal row; at base stop 130 the same +0.28 is 2,405 dofs /
   1.34 s) and it makes the diagonal pattern *narrower* than H/V (the diagonal rows are the
   deep ones for +x_amp), the opposite of the commercial "diagonal as good as horizontal" goal.
6. **`salmon_x_shape`'s seed is broken under the f0 briefs.** `[measured]` at the derived
   fc 1200/843.8, stop 130, x_amp 0.25 the outer-shell self-approach is 7.997 mm < 8.0 mm
   (2t+2) -> mesh refused; the same happens at 2in (7.998). x_amp 0.22 and 0.28 are green
   (1,778 / 2,405 dofs); the failure is an isolated knife-edge at 0.25. The config header's
   2,239-dof claim was measured at the old 800/1100 seed, not the derived one.
7. **`salmon_ripple12`'s lobe knob is unusable in a continuous search.** `[measured]` 16/16
   LHS points were refused with "ripple_lobes must be a non-negative integer" because the
   sampler interpolates 6..24 continuously. Even at integers, n_phi 25 half-span admits at
   most 12 lobes (4 samples/lobe); 14-24 are refused by the resolution guard. Pinning
   lobes = 12 makes 14/17 points legal (3 envelope refusals).
8. **`salmon_saddle` is a half-model (2x dofs) with its side rows past 180 deg at the shipped
   stop 160.** The fixed a2 0.25 / b1 0.2 law gives side stop = 1.25*160 = 200 deg (a duplicate
   of 160 on the folded branch). `[measured]` stop 160: 13,299 tris / 6,738 dofs / 5.7 s;
   stop 140: 8,071 / 4,107 / 0.97 s; stop 130: 4,806 / 2,470 / 0.72 s. At B3a it reaches
   28,053 tris / 14,142 dofs / 22.7 s.
9. **`salmon_spherical` cannot serve any of these briefs.** It is axisymmetric (no 90x60 or
   60x40), the f0 derivation has no rule for the typology route (its seed stays 800/0.8/80
   under every brief) `[measured]`, `h_max_wall_deg <= 88` means it never rolls back, and its
   fc bounds [600,1200] block the 235-266 Hz a 90 deg/400 Hz horn needs.
10. **The 8 kHz top, not the cap, is the real campaign limit.** `[measured]` mesh dofs at
    epw 6, band_hi 8000: B1 reseeds 2,590-4,993; B2 reseeds 6,774-8,544; B3a 6,848-9,302;
    B3b 5,242-10,370. The measured 8 kHz ladder (CONTINUITY 2026-10-26) is safe to ~5,300 dofs,
    edge ~5,900, saturated >=7,000 `[measured, OSSE quarter]`. So B2/B3a/B3b-x are edge-to-OOM
    at 8 kHz; the shipped 5,000/7,000/8,900 caps are stale in the other direction (they block
    the 5-10k designs the fused solver would fit).

---

## 1. What each knob does (plain physics)

The rows route is **one spherical Salmon march per azimuth**: `1/fc(phi) = cos^2/fc_h +
sin^2/fc_v`, same `T`, same throat `r0`/`theta0`, then every row is resampled to `n_s` equal
arc-length stations. The mouth is the last station of each row; the wall angle at that station
is the row's stop. `P = (y cos phi, y sin phi, x)` with `x` the march's axial abscissa, which
becomes non-monotone past 90 deg (the rollback).

| knob | what it does | current seed / bounds | notes |
|---|---|---|---|
| `g_fc_h_hz`, `g_fc_v_hz` | per-azimuth cutoff. Low fc starts the Salmon flare earlier -> fatter/longer row; high fc -> tighter. The pair sets the H/V aspect (W*fc_h ~ H*fc_v). | seed 800 / 1100; bounds 600-1200 | f0 derivation OVERWRITES both from `1.88e5/(env-6)`, clamped to [600,1200]. Measured row mouth*fc = 3.23e5 at stop 150 (2.57e5 at 120, 3.65e5 at 170). This is the primary pattern-size knob and the one the bounds break. |
| `g_T` | Salmon family parameter: 0 catenoidal, 1 exponential, >1 steeper. Changes the early flare/loading and the march legality floor. | 0.8; 0.3-1.0 | `[measured]` T 0.5/0.8/1.0 at the organic seed: mouth 269.5/268.4/267.5 mm, depth 165.7/161.0/158.3 mm - <2% at the mouth. T's real roles are throat loading and the low-fc floor (below). |
| `g_stop_deg` | wall angle where each row ends. <90 no roll; 90-180 increasing roll (rim grows, depth shrinks); 180 cap-area asymptote (refused); >180 mirror duplicate of 360-stop. | 150 (130 x_shape, 160 saddle); 120-240 | `[measured]` stop 120/130/140/150/170 at the 1in X seed: 216x306/234x332/252x357/268x381/300x394 mm; 1,134/1,299/1,546/2,031/5,176 dofs; 0.38/0.43/0.51/0.59/3.07 s. 160 refused (8 non-sliver tris in x=0); 175 over envelope. 190=170, 230=130, 240=120. |
| `g_x_amp` | `stop(phi)=stop*(1+x_amp cos4(phi-45deg))`. + = diagonal rows deeper (corners out, literal X rim); - = cardinal rows deeper (corner-in / plus). | x_shape +0.25 [0,0.35]; x_signed -0.15 [-0.4,0.4] | `[measured]` see headline 5. |x_amp| > 180/stop - 1 puts a row past 180 (0.20 at stop 150, 0.385 at 130). |
| `g_x_fc` | `fc *= 1 - x_fc cos4(phi-45deg)` whenever x_amp != 0. Decouples the diagonal loading from the stop. | 0.15; 0-0.3 | At phi=0/90 the factor is 1+x_fc (up to 1.3): the cardinal rows shrink, the diagonal rows grow. Recommend <=0.2. |
| `g_ripple_lobes` | even-lobe radius ripple `r *= 1 + (amp/rowmax) w(s) cos(N phi)`. | 12; 6-24 | MUST be an integer; at n_phi 25 half, 4 samples/lobe admits N <= 12. A continuous sampler refuses 100% of LHS points `[measured]`. |
| `g_ripple_amp_mm` | ridge height in mm at the widest station. | 3.0; 0.5-6 | 12 lobes at a 270 mm mouth: lobe arc ~70 mm vs epw6 8 kHz mouth res 7.15 mm -> the lobe pattern is resolved; the 3 mm height is 1.1% of the radius (a 0.2-1 dB class effect, per the in-repo faceting/tiling evidence). |
| `g_ripple_start` | smoothstep window opening (fraction of arc); throat stays clean. | 0.8; 0.7-0.95 | No dof effect; 0.75-0.92 is ample. |
| `g_stop_cos2k` | list harmonic `a2 cos 2phi` (sides deep for a2>0). | saddle 0.25, FIXED | Not searched. At stop 160 the side stop is 1.25*160 = 200 deg. |
| `g_stop_sin2k1` | list harmonic `b1 sin phi` (top deep, bottom shallow) - up/down asymmetry; forces the half model. | saddle 0.2, FIXED | 2x the quarter dofs; no H/V objective can score the asymmetry it creates. |
| `g_r_lip_mm` | torus lip at the mouth (0-100 mm). | absent -> 0, not searched | The commercial rollback practice (AudioHorn 25-40 mm "direct ending at 180 deg"; JMLC r~30 mm) is exactly this knob. Adding 20 mm at the organic seed overshoots the envelope by 1.6%; 40 mm by 11% `[measured]`. Any campaign that compares with commercial horns must budget 2*r_lip. |
| `n_phi` / `n_s` | azimuth rows / stations per row. | 15 quarter (x/ell), 25 half (ripple/saddle), n_s 32 | 15 is the quarter minimum; 25 odd is the half minimum. More rows = more tris/dofs; ripple needs >=4 samples/lobe. |
| `wall_thickness_mm` | outer shell offset; sets the self-approach bar 2t+2 = 8 mm. | 3.0, not searched | The saddle/x_shape knife-edge failures at 7.997-7.999 mm would clear at 2.5 mm (bar 7.0). |
| `epw` | elements per wavelength at f_max; mouth res = 343000/(epw*f_max). | 8 (x/ell/ripple), 6 (saddle) | `[measured]` 8k epw6 mouth res 7.15 mm; epw8 5.36 mm. Dofs ~1/epw^2. |
| `quadrants` / `span` | quarter ('1') vs half ('14'). | x/ell quarter, ripple/saddle half | Half = 2x the quarter dofs for the same surface. |
| `dof_cap_screen/verify/final` | triangle/dof budget. | 5000/7000/8900 | Stale vs the fused solver (safe 12,000, fits 15,984). They caused the 2026-10-25 smoke failures (ripple 5,358 > 5,000). |

### What the brief's f0 derivation actually overrides

`_brief_preflight_and_derive` (config.py) runs only for a `generator:` block (grid rows) and only
when the brief's target has `f0_hz`. It:
- computes `req = 25400e3/(f0*coverage)`, caps it at `env - 2*wall` (3 mm default), then
  `fc = 1.88e5/capped_req`, clamped to the knob's existing bounds;
- records `feasible_w/v`, the "held coverage at the envelope", and the screen/verify frequency
  counts below f0;
- overwrites ONLY `g_fc_h_hz` / `g_fc_v_hz`. T, stop, x_amp, x_fc, ripple, saddle harmonics,
  span, n_phi, n_s, wall, r_lip, epw all stay at the config seed/bounds.
For the typology route (`spherical_salmon`) there is **no rule** - the seed is unchanged.

Measured effect `[measured]`:

| brief | required W x H (mm) | derived fc_h / fc_v | result |
|---|---|---|---|
| B1 850/90x60 | 332.0 x 498.0 | 566 -> **600** / 377 -> **600** | square seed; rim 538x538, W over 360 by 50% |
| B2 800/60x40 | 529.2 x 793.8 | 355 -> **600** / 237 -> **600** | square seed; rim 538x538 |
| B3a 400/90x90 | 705.6 x 705.6 | 266 -> **600** / 266 -> **600** | square seed; 118x118 deg at 400, never 90 |
| B3b 600/90x60 | 470.4 x 705.6 | 399 -> **600** / 266 -> **600** | square seed; W 538 > 500 |
| organic 1in 1900 | 148.5 x 222.8 | 1266 -> **1200** / 843.8 | H at the bound; true W90 157, rim 269 |
| organic 14in 1800 | 156.8 x 235.2 | 1199 / 799.4 | inside bounds |
| organic 2in 1550 | 163.9 x 273.1 | 1032.5 / 688.3 | inside bounds |

The three "held coverage" numbers the preflight prints (B1 83.0/57.5, B2 56.7/38.3, B3a
85.8/85.8, B3b 84.7/57.2) are the K-law coverage of a *straight* horn with the envelope mouth.
They are not what the rollback rows produce; the rows' rim adds the k(stop) factor.

---

## 2. Measured campaign reseeds (rim-honest fc)

Method: solve, with the generator's own march and modulation laws, the fc pair whose outer
width/height (rim + 2*wall) lands on `env - 6 mm`; then mesh that seed at epw 6, band_hi 8000,
caps raised. "cov@f0" is the rim K-law `25400e3/(f0*mouth)`; the W90 proxy would be
`135.1*fc/f0`. All rows `[measured]`.

| brief | config | fc_h/fc_v (T, stop) | mouth WxH | outer WxHxD | cov@f0 H/V | tris | dofs@8k | mesh s |
|---|---|---|---|---|---|---|---|---|
| B1 | x_signed | 926 / 633 (0.8, 150) | 348x508 | 354x514x210 | 85.8 / 58.8 | 6,617 | 3,427 | 0.93 |
| B1 | elliptical | 931 / 636 (0.8, 150) | 348x508 | 354x514x157 | 85.9 / 58.8 | 4,987 | 2,590 | 0.74 |
| B1 | ripple12 | 947 / 644 (0.8, 150, 12 lobes) | 348x508 | 354x514x154 | 85.8 / 58.8 | 9,756 | 4,993 | 1.32 |
| B1 | saddle | 991 / 645 (0.8, 160) | - | - | - | - | - | envelope over 6.9% |
| B2 | elliptical | 584 / 392 (1.0, 150) | 553x823 | 559x829x351 | 57.5 / 38.6 | 13,199 | 6,774 | 1.55 |
| B2 | x_signed | 584 / 392 (1.0, 150) | 551x819 | 557x825x378 | 57.7 / 38.8 | 16,685 | 8,544 | 1.64 |
| B2 | x_signed at T=0.8 | 584 / 392 | - | - | - | - | - | march refused (fc_v 392 < floor 468) |
| B3a | elliptical | 444 / 444 (0.8, 150) | 727x727 | 733x733x267 | 87.3 / 87.3 | 13,342 | 6,848 | 1.35 |
| B3a | x_signed | 441 / 441 (0.8, 150) | 729x729 | 735x735x365 | 87.2 / 87.2 | 18,186 | 9,302 | 1.90 |
| B3b | elliptical | 663 / 444 (0.8, 150) | 488x727 | 494x733x267 | 86.8 / 58.2 | 10,195 | 5,242 | 1.28 |
| B3b | x_signed | 659 / 441 (0.8, 150) | 489x729 | 495x735x317 | 86.6 / 58.1 | 13,143 | 6,744 | 1.58 |
| B3b | ripple12 | 671 / 447 (0.8, 150, 12) | 494x733 | 500x739x267 | 85.8 / 57.7 | 20,392 | 10,370 | 2.28 |
| B3b | saddle | 706 / 450 (0.8, 160) | - | - | - | - | - | envelope over 7.9% |

Shipped (derived) seeds for comparison `[measured]`: all four campaign briefs 600/600
(see the table in section 1); organic 1in/14in/2in 1200/843.8, 1199/799.4, 1032.5/688.3.

Organic seed measurements at epw 6 / band 8000 `[measured]`:

| config | 1in (f0 1900) | 14in (1800) | 2in (1550) |
|---|---|---|---|
| elliptical | 1,555 dofs / 0.58 s | 1,645 / 0.59 | 2,173 / 0.64 |
| x_signed | 2,031 / 0.71 | 2,183 / 0.70 | 2,924 / 0.80 |
| ripple12 | 3,012 / 1.00 | 3,218 / 0.96 | 4,281 / 1.16 |
| saddle | 6,738 / 5.69 (stop 160; 6,603 / 5.14 at stop 145) | 6,289 / 1.48 | 7,616 / 1.68 |
| x_shape | **refused** (self-approach 7.997) | 1,972 / 1.05 | **refused** (7.998) |
| spherical | 1,429 / 1.63 (fc 800, 80 deg; not f0-derived) | - | - |

`x_shape` at x_amp 0.22 (1in, stop 130): 1,778 dofs / 0.51 s, 294x323x127 `[measured]`.
Saddle at stop 140 (1in): 4,107 dofs / 0.97 s, 316x339x209 `[measured]`.

---

## 3. Compatibility matrix (config x brief)

Verdict key: **RUN** = the measured seed fits the 8 kHz safe envelope and dofs; **RUN-CHG** =
feasible but needs the listed seed/bound/band change; **NO** = not honestly testable in this
brief.

| config | B1 90x60/850 | B2 60x40/800 | B3a 90x90/400 | B3b 90x60/600 | organic 90x60 |
|---|---|---|---|---|---|
| salmon_elliptical | **RUN-CHG**: 931/636, stop 150; 2,590 dofs, 0.74 s; 8k safe | **RUN-CHG**: T=1.0, 584/392; 6,774 dofs; 8k edge -> epw5 or band 6.5k | **RUN-CHG**: 444/444; 6,848 dofs; 8k edge -> band 5.5-6k | **RUN-CHG**: 663/444; 5,242 dofs; 8k borderline safe | **RUN** (1,555/1,645/2,173) but f0 is 1.7x too high; see 4.3 |
| salmon_x_signed | **RUN-CHG**: 926/633; 3,427; 0.93 s; 8k safe | **RUN-CHG**: T=1.0, 584/392; 8,544; 8k over -> epw5/6.5k | **RUN-CHG**: 441/441; 9,302; 8k over -> band 5.5k | **RUN-CHG**: 659/441; 6,744; 8k edge | **RUN** (2,031/2,183/2,924); stop <=150 |
| salmon_x_shape | **NO**: derived seed 45% over envelope; no clean rim-honest reseed (diagonal row hits the march floor) | **NO** for 60x40: derived seed is a 516x516 square (61x61), 5,095 dofs; V 21 deg too wide | **NO** for 90x90: 516x516 -> 123x123; fc 600 floor blocks 441; 4,474 dofs | **NO**: 4.4% over envelope; no clean reseed | **RUN-CHG only**: 14in green (1,972); 1in/2in refused -> seed x_amp 0.22 (1,778, 0.51 s) |
| salmon_saddle | **NO**: 6.9% envelope over at the fitted fc (fixed harmonics) | **NO**: 7.8% over; 1in floor also blocks 40 deg V | **NO at 8k**: 28,053 tris / 14,142 dofs / 22.7 s; over fused safe and 8k VRAM | **NO**: 7.9-14.3% over at all tried seeds | **RUN-CHG**: stop 140 (4,107/0.97 s at 1in); 2in 7,616 dofs -> edge; stop 160 is 5.7 s |
| salmon_ripple12 | **RUN-CHG**: 947/644, lobes pinned 12; 4,993; 1.32 s; 8k safe | **NO at 8k**: 7,400 dofs / 14,532 tris; edge/over. epw5/6k only | **NO at 8k**: fitted 447 -> half model ~10k dofs; derived 600 is 117 deg | **NO at 8k**: 10,370 dofs / 20,392 tris / 2.28 s -> solve OOM | **RUN-CHG**: lobes pinned 12; 3,012/3,218/4,281; safe |
| spherical_salmon | **NO**: axisymmetric, cannot be 90x60 | **NO**: axisymmetric | **NO**: needs fc 235-266 (bound 600) and a 0.7 m mouth (8k OOM) | **NO**: axisymmetric | **NO**: hv brief; axi briefs only (no f0 rule) |

**Is a constant-directivity brief fair to a rollback horn?** Only if (a) coverage is scored above
the horn's honest f0 (objective v3's mask does this), (b) loading is scored (`load 0.5`,
`z_min 0.5-0.7`), and (c) the envelope is the *rim* size, not the K-law W90 size. B3b is the only
campaign brief that scores loading; B1/B2/B3a use `load 0`/`z_min 0`, i.e. they judge a
rollback/loading family on a waveguide's objective. The organic briefs do score loading but their
f0 is 1.7x too high.
**Can an X-shape reach 90x60 / 60x40?** The axis-aligned coverage comes from the cardinal rows,
which +x_amp makes shallower (wider) and -x_amp deeper (narrower); the diagonal rows do the
opposite. So the *H/V* targets are reachable (x_signed B1/B3b fits at 85-87/58), but the diagonal
pattern is then narrower than H/V. An H/V-only brief cannot see that, which makes it unfair to
the X. A fair X brief needs a 45/135 diagonal-consistency term (the AudioHorn dossier's own
measurement-hygiene point) and a diagonal envelope check.

---

## 4. Over-constraining bounds vs physical limits

### 4.1 Bounds that block sensible designs `[measured]`

| bound | current | what it blocks | recommended |
|---|---|---|---|
| `g_fc_v_hz` lo | 600 | B2 V-40 (needs 392), B3b V-60 (441), B3a both (441), spherical B3a (235-266). The derivation clamps to 600 -> square seed. | per-brief: 380 (B2), 420 (B3a/B3b), 600 only for organic 1in/14in |
| `g_fc_h_hz` lo | 600 | B3a (441), B3b (659 is fine), B2 H (584 is fine) | 420-570 per brief |
| `g_fc_h_hz` hi | 1200 | organic 1in/14in H at 1900 (needs ~1450/1370 to shrink the rows' fat rim to the claimed 90); x_shape H reseeds | 1500 if the f0 stays 1900; otherwise keep 1200 |
| `g_stop_deg` hi | 240 | 43% of the box is a mirror duplicate (180+); near-180 depth/step explosion; deep-roll dof cost | 155 (1in), 165 (14in/2in); never >175 |
| `g_x_amp` | -0.4..0.4 | rows past 180 for |x_amp| > 180/stop-1 (0.20 at stop 150); envelope/dof/ mesh blow-ups | +/-0.18 at stop 150; +/-0.28 at stop 130 |
| `g_x_fc` hi | 0.3 | cardinal/diagonal fc split too extreme; diagonal rim dominates the bbox | 0.2 |
| `g_ripple_lobes` | 6..24 continuous | non-integers refused 100%; integers 14-24 refused by the 4-samples/lobe guard at n_phi 25 | pin 12 (search amp/start); or n_phi 49 for 24 |
| `g_ripple_amp_mm` lo | 0.5 | amp 0.5 mm is a 0.2% radius modulation - effectively invisible (acoustic effect << 0.2 dB) | 2.0 |
| `g_r_lip_mm` | absent (0) | commercial-style 180 deg roundover; adding 20 mm at the organic seed already overshoots by 1.6% | search 15-30 mm with a 2*r_lip envelope budget |
| `dof_cap_*` | 5000/7000/8900 | the 5-10k designs the fused solver fits; caused the ripple/saddle smoke failures | 12,000 all tiers with `cuda_fused: true` |

### 4.2 Physical/legality limits (not bounds)

- **Low-fc march floor.** `[measured]` `fc_min * r0 = K(T)`, K = 15,711 (T=0.3), 9,483 (T=0.5),
  5,940 (T=0.8), 4,753 (T=1.0) mm-Hz, independent of stop (90-170). For a 1-inch throat:
  1,237 / 747 / 468 / 374 Hz. This is why B2's 40 deg V (fc_v 392) refuses at T=0.8 and only
  works at T>=0.96. It is a property of the fixed 5 deg throat + area-law march, not a bound.
- **180 deg cap-area asymptote.** Exactly 180 is refused; 179.9 gives L 913 mm / 3,654 steps;
  the geometry is continuous but the depth diverges. >180 is a mirror duplicate.
- **Self-approach >= 2t+2 = 8 mm.** Measured knife-edge failures: x_shape 0.25 (7.997),
  saddle square-aspect LHS points (7.998-7.999). A 2.5 mm wall (bar 7.0) clears them.
- **Mesher sliver defect.** 8 non-sliver triangles in x=0 at stop 160, x_amp -0.15 (and at
  -0.25/stop 150 per the S1a record). Not a bound; a mesh-quality region.
- **8 kHz VRAM.** Measured ladder: safe ~474 mm / ~5,300 dofs; edge ~500 mm / ~5,900 dofs;
  saturated >=550 mm / ~7,000 dofs. Rows with 6.8-10.4k dofs are edge/OOM `[estimated from the
  ladder, OSSE quarter]`.

### 4.3 The organic f0 is the other over-constraint

If the rim is the acoustic mouth (the commercial `mouth x fc` ~3e5 and the exact Fourcade
~1.87e5 both support a rim-based rule), the organic briefs' f0 should be
`25400e3/(coverage*(env-6))`:
1in: 25400e3/(60*414) = **1,022 Hz** (not 1,900); 14in: **975 Hz** (not 1,800);
2in: **857 Hz** (not 1,550). The geometry does not change - only the mask moves. That is a
one-line brief edit with no dof cost. If instead the W90 is the acoustic mouth, the current
organic f0 is right and the campaign B1-B3b are 1.7x too tight. **One GPU A/B solve of the two
seeds settles it; this audit cannot.** Until then, treat the organic f0 as optimistic by ~1.7x.

---

## 5. Failure rates and high-failure regions

Groups from `out\lhs.jsonl` etc., recommended boxes unless stated `[measured]`:

| group | n | ok | envelope | true march | mesh | comment |
|---|---|---|---|---|---|---|
| x_signed x B1 (10 LHS + 22 corners) | 32 | 19 | 13 (41%) | 0 | 0 | LHS-only 8/10 ok (20 %); the failures are the shipped-range corners (stop 165+, x_amp +/-0.35..0.4, x_fc 0) |
| elliptical x B1 (16 LHS) | 17 | 16 | 1 (6%) | 0 | 0 | |
| x_signed x B2 (16 LHS) | 17 | 11 | 6 (35%) | 0 | 0 | high-fc/high-x_amp corner of the box is over-wide/envelope |
| x_signed x B3b (16 LHS) | 17 | 12 | 4 (24%) | 0 | 1 (6%) | one x=0 sliver |
| elliptical x B3a (16 LHS) | 17 | 15 | 2 (12%) | 0 | 0 | |
| x_signed x organic 1in | 17 | 14 | 2 (12%) | 0 | 1 (6%) | |
| elliptical x organic 1in | 17 | 14 | 3 (18%) | 0 | 0 | |
| saddle x organic 1in | 17 | 13 | 2 (12%) | 0 | 2 (12%) | self-approach at square-aspect points |
| ripple x organic 1in, lobes free | 17 | 1 | 0 | 16 (94%) | 0 | every LHS lobe count non-integer |
| ripple x organic 1in, lobes pinned 12 | 17 | 14 | 3 (18%) | 0 | 0 | |
| saddle x B1/B3b reseed | 5 | 0 | 5 (100%) | 0 | 0 | fixed harmonics add 7-14% |

High-failure regions: stop 165-180 and >180; |x_amp| > 180/stop-1; fc below K(T)/r0;
square-ish fc_h/fc_v in the saddle; stop 160 with a negative x_amp; ripple lobes non-integer or
>12 at n_phi 25; any 8 kHz mouth >550 mm (VRAM).

---

## 6. Web research (real fetches this session)

| source | HTTP | what it gave |
|---|---|---|
| https://api.crossref.org/works/10.1121/1.1916317 | 200 | Salmon, "A New Family of Horns", JASA 17(3), 1946, DOI. Bibliographic record. |
| https://api.openalex.org/works/https://doi.org/10.1121/1.1916317 | 200 | Same, abstract: exponential as the central member; perturbation family. |
| https://rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf | 200 (12.7 MB) | Le Cleac'h ETF10 lecture (text extracted, 839 lines): isophase surfaces perpendicular to the wall (p.37-38); the Salmon family appears in the family list (p.~70). Primary author source for the spherical-cap application. |
| https://horns-diy.pl/horns/jmlc/jmlc-350/ | 200 | Auto-Tech JMLC-350, "Minimal frequency from 520 Hz". |
| https://horns-diy.pl/wp-content/uploads/2015/07/JMLC-3501.pdf | 200 (817 KB) | JMLC-350 datasheet, image-only (pdftotext empty). The dimension string (mouth O595 mm, 435/382/372/325 mm, throat 25.4/35.8/38.1/50.8 mm) is the in-repo verified read of this PDF, not machine-extracted today. |
| https://horns-diy.pl/horns/e-jmlc/e-jmlc-300/ | 200 | E-JMLC-300, min 500 Hz. |
| https://horns-diy.pl/horns/iwata/iwata-300/ | 200 | IWATA-300, min 450 Hz. |
| https://horns-diy.pl/horns/spherical/spherical-185/ | 200 | SPHERICAL-185, min 200 Hz. |
| https://audiohorn.net/x-shape-horn/ | 200 | X-Shape 21/25/28/33/34/40: W x H x D 210x130x120 ... 408x248x230 mm; recommended crossovers 1400/1250/1250/1150/800/750 Hz; 1 in and 1.4/1.5 in drivers (18Sound, BMS, Faital, TAD, JBL); roundover 25-40 mm; verbatim "the horn allow it by a direct ending at 180 deg"; "The diagonal measurement of the X-shape is as perfect as the horizontal one." W/H 1.60-1.65, D/W 0.55-0.61 [arithmetic]. |
| https://audiohorn.net/sciences/cross-wavefront-syndrome/ | 200 | The maker's mechanism: abrupt round->rect transitions diffract on the diagonals; "A proper wavefront should be round or elliptical, not cross shaped. The horn mouth is not in cause, it's the overall profile."; measure diagonals, not just H/V. |
| https://audiohorn.net/next-gen-bi-radial-horn/ | 200 | "follows the Hypex formula surface law"; 48-60 cm wide, 30-36 cm long, 1 in or 1.4/1.5 in, 90 deg H, effective crossing 500/700 Hz. |
| https://at-horns.eu/core.html | 200 | Ath CORE: `Mesh.Roundover = {Radius=42; Segments=6}` (a segmented roundover), `Morph.*`, "smoothest profiles"; source for the visible "pleats" = segmented roundover reading. |
| https://en.wikipedia.org/wiki/Horn_antenna | 200 | Corrugated/scalar horn class: parallel slots/grooves small vs a wavelength, transverse to the axis, Kay 1962; the nearest physical neighbour to a mouth ripple. |
| https://html.duckduckgo.com/html/?q=Salmon+%22A+New+Family+of+Horns%22+1946 | 202 | Challenge page; general search unavailable. No result was used from it. |
| http://www.arduman.com/aa/Sayfalar/lecleach/lecleach.htm | 200 | Le Cleac'h's system page (TAD TD2001); practitioner context, not a construction. |
| https://www.bing.com/search?...&format=rss | 200 | RSS returned off-topic results; not used. |

No fabricated URL or spec: the only unverified-by-crawl numbers are the JMLC-350 datasheet
dimensions (marked as the in-repo verified read of the fetched image-only PDF).

**Commercial cross-check** `[web + arithmetic]`, assuming 90 deg H (the bi-radial page states
90 deg; the X-Shape page gives crossovers, not angles):

| product | mouth (mm) | xo/min (Hz) | mouth*fc | K-law 90 deg break | xo vs break |
|---|---|---|---|---|---|
| X-Shape 21 | 210 | 1400 (1200) | 294e3 | 1344 | 1200 optimistic, 1400 safe |
| X-Shape 25 | 250 | 1250 (1200) | 313e3 | 1129 | safe |
| X-Shape 28 | 280 | 1250 | 350e3 | 1008 | safe |
| X-Shape 33 | 330 | 1150 (1000) | 380e3 | 855 | safe |
| X-Shape 34 | 339 | 800 (700) | 271e3 | 832 | 700 optimistic |
| X-Shape 40 | 408 | 750 (650) | 306e3 | 692 | 650 optimistic |
| JMLC-350 | 595 | 520 | 309e3 | 473 | safe |
| IWATA-300 | 590 | 450 | 266e3 | 478 | 450 slightly optimistic |
| E-JMLC-300 | 920 | 500 | 460e3 | 306 | very safe |

The products cluster at 2.7-3.8e5 mm-Hz, the rows' rim product at stop 120-170 (2.6-3.7e5).
That is the strongest external evidence that the *rim* is the mouth and that 1.88e5 is the
`r90 x fc` (equivalently `mouth x model-number`) constant, with the pattern holding to ~1.5x
the model number.

**Mouth serration/ripple.** No fetched audio maker claims a rippled/corrugated acoustic surface;
the visible X-Shape "puckers" are consistent with a segmented roundover (Ath Segments=6) or a
printed kit. The corrugated-horn class is the physical neighbour (grooves << wavelength). Our
even-lobe radius ripple remains a labeled experiment; its honest objective is rim-diffraction
coherence / diagonal smoothness, not coverage. The 2026-10-25 dossier's 0.2-1 dB expectation
stands.

---

## 7. Recommended campaign seeds/bounds per brief

Numbers are `[measured]` rim-honest seeds unless marked. "fc" is the Salmon cutoff (not f0);
f0 is the brief's coverage break.

### B1 - 90x60, f0 850, 1.4 in, env 360x520x400
- **ellipse**: fc 931/636, T 0.8, stop 150, x_amp 0, x_fc 0; bounds fc [880,1050]/[600,720],
  stop [125,158], T [0.7,1.0]. 2,590 dofs, 0.74 s, 8k safe.
- **x_signed**: fc 926/633, x_amp -0.15 (or +0.15 for the literal X), x_fc 0.15; bounds
  x_amp +/-0.18, x_fc [0.05,0.18]. 3,427 dofs, 0.93 s, safe.
- **ripple**: fc 947/644, lobes **pinned 12**, amp [2,6], start [0.75,0.92]. 4,993 dofs, 1.32 s,
  safe.
- **saddle**: not envelope-true (6.9% over); if tried, stop 140 and re-fit fc.
- **x_shape**: don't; the diagonal row needs an fc below its march floor.
- Caps: 12,000; `cuda_fused: true`; epw 6.
- This is the best rollback brief of the four: its envelope is the rim size for 90x60 at 850,
  the reseed is inside the shipped fc bounds, and the 8k dofs are safe for every kind except
  the saddle.

### B2 - 60x40, f0 800, 1 in, env 560x830x450
- **ellipse**: fc 584/392, **T 1.0** (march floor 374 at 1 in; T 0.8 floor 468 refuses 392);
  stop 150; bounds fc [560,640]/[380,430], T [0.99,1.0], stop [145,158]. 6,774 dofs, 1.55 s;
  8k edge -> screen epw 5 or band_hi 6.5k, verify at 8k one at a time.
- **x_signed**: same, x_amp -0.15/+0.15, x_fc 0.1; 8,544 dofs -> 8k over; epw 5/6.5k only.
- **ripple/saddle**: no at 8k (7.4k / envelope-over).
- If the 600 fc floor is kept, this brief cannot hold 40 deg V; the honest target becomes
  ~60x50 or f0 ~1.05 kHz.

### B3a - 90x90, f0 400, 1.4 in, env 740x740x650
- **ellipse**: fc 444/444, T 0.8, stop 150; bounds fc [420,520], stop [140,165], T [0.7,1.0].
  6,848 dofs, 1.35 s; 8k edge -> screen at 5.5-6k.
- **x_signed**: 441/441; 9,302 dofs, 1.90 s; 8k over -> band 5.5k.
- The shipped 600 floor makes a 544 mm / 118x118 horn; it can never reach 90x90 at 400. This
  brief is the cleanest proof that the fc lo bound is over-constraining.
- **saddle/ripple**: no at 8k (saddle 14,142 dofs; ripple half >10k).

### B3b - 90x60 from 600, loading 0.5, 1.4 in, env 500x740x600
- **ellipse**: fc 663/444, T 0.8, stop 150; bounds fc [640,760]/[420,500], stop [140,160],
  T [0.7,1.0]. 5,242 dofs, 1.28 s; 8k borderline safe.
- **x_signed**: 659/441; 6,744 dofs, 1.58 s; 8k edge.
- **ripple**: 671/447, lobes 12; 10,370 dofs, 2.28 s; 8k OOM -> band 5.5k only.
- **saddle**: envelope over 7.9-14.3% at the tried seeds; no.
- This is the only campaign brief that scores loading, so it is the fairest of the four for a
  rollback family; it just needs the fc_v lo bound lowered to ~420.

### Organic 1in/14in/2in - f0 1900/1800/1550
- Keep the shipped seeds for now (ell 1200/843.8 etc.; x_signed 2031/2183/2924; ripple
  3012/3218/4281; saddle 6738/6289/7616). Caps 12,000.
- **But fix the f0 mask**: if the rim is the mouth, the honest f0 is ~1,022/975/857 Hz; the
  current 1,900/1,800/1,550 masks ~1.7x too much of the band. Either lower f0 (one-line brief
  edit, geometry unchanged) or raise fc to ~1,450/1,370/1,183 and narrow the mouth (the 1in/
  14in need fc > 1200, so the hi bound would have to widen). The GPU A/B decides which.
- Bound/seed hygiene: stop 120-150 (1in), 120-160 (14in/4in), x_amp +/-0.2, x_fc 0-0.2,
  ripple lobes pinned 12, saddle stop 130-140, saddle fc_h >= 1.2*fc_v (avoid the square-aspect
  self-approach). Add `g_r_lip_mm` 15-30 mm with a 2*r_lip envelope budget if the commercial
  180 deg return is in scope.

### spherical_salmon
- Not for any of these briefs. Use an axisymmetric brief (`axi_90x90_1in`) only; add an f0
  derivation rule for the typology route (none exists), or set `h_fc_hz` manually. Its
  `h_max_wall_deg <= 88` means it is a spherical Salmon, never a rollback.

---

## 8. Risks / open questions

1. **W90 vs rim is unresolved by CPU work.** The measured geometry is unambiguous; the
   acoustic pattern is not. One GPU seed solve of B1-reseed vs organic-reseed at ~1 kHz would
   settle the 1.7x question. Until then every "cov@f0" here is a geometric K-law proxy.
2. **Rows march vs exact Fourcade.** The rows mouth is 1.29x (90 deg) to 1.75x (150 deg) the
   exact construction at the same fc/T/stop. That is a generator-level difference, not a config
   knob; this audit did not change it. If the exact construction is the intended family, the
   rows' fc derivation must use the rows' own product or the march must be replaced.
3. **8k VRAM numbers are extrapolated from the OSSE quarter ladder**, not rows BEM. Treat
   +/-1 GB; verify finalists one at a time with Julia cleared.
4. **Caps were raised to 1e6** in the scratch copies; the campaign must set 12,000 and rely on
   the band/VRAM rules.
5. **Self-approach is knife-edge** for x_shape/saddle; a 0.003 mm change flips meshability.
   Budget a re-seed test per brief and consider a 2.5 mm wall.
6. **Web specs are maker claims**; no independent measurements of the X-Shape/JMLC polars were
   available (the JMLC PDF is image-only; the X-Shape polars are images). The commercial
   `mouth x fc` check is arithmetic on published dimensions, not a measured polar.
7. **No BEM metrics** (DI, ripple, load) were produced; the objective's actual ranking of these
   seeds is untested. This is a geometry/bounds audit.

---

## 9. Reproduction

Interpreter: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`,
workdir `C:\Users\hunte\Hrns\hornlab-search`.

```powershell
$s = "C:\Users\hunte\AppData\Local\Temp\claude\C--Users-hunte-Hrns\06de492c-2c05-4dc9-8ec7-6da31e47c981\scratchpad\audit_salmon"
# seed / derivation / one mesh
& .venv\Scripts\python.exe "$s\probe2.py" --config salmon_x_signed `
  --brief "$s\briefs\organic_rollback_1in_8k.yaml" --tag org1in_seed `
  --out "$s\out\smoke.jsonl" --only-seed
# campaign reseed point (B1 x_signed)
& .venv\Scripts\python.exe "$s\probe2.py" --config salmon_x_signed `
  --brief "$s\..\briefs\draft_b1_hifi_90x60_850_14in.yaml" --tag b1_reseed `
  --out "$s\out\campaign_reseed.jsonl" --points-file "$s\pts_b1_xsigned.json" `
  --bounds-file "$s\bounds_fc250_1600.json"
# 16-point LHS in a recommended box
& .venv\Scripts\python.exe "$s\probe2.py" --config salmon_elliptical `
  --brief "$s\..\briefs\draft_b3a_pa_90x90_400_14in.yaml" --tag b3a_lhs `
  --out "$s\out\lhs.jsonl" --bounds-file "$s\bounds_camp_b3a_plain.json" `
  --n-lhs 16 --no-corners
# stop 180 behaviour (pure march)
& .venv\Scripts\python.exe "$s\p2_stop180.py"
```

Files in the scratch dir: `calib.py`, `probe2.py`, `recommend.py`, `p1_march.py/.txt`,
`p2_stop180.py/.txt`, `bounds_*.json`, `pts_*.json`, `briefs/*_8k.yaml`,
`briefs/b1_5p5k.yaml`, `cfgs/` (scratch config copies), `out/*.jsonl`, `web/` (fetched pages).
Raw rows: `out/seeds.jsonl`, `out/organic_seeds.jsonl`, `out/campaign_reseed.jsonl`,
`out/lhs.jsonl`, `out/shape_sweeps.jsonl`, `out/knob_effects.jsonl`, `out/fc_floor.json`,
`out/recommend.json`.



