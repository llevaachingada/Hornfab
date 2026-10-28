# Senior pass: scoring, search speed, and "will the printed horn measure like the sim?" (2026-10-27, evening)

Written while the ripple/ridge night was running. **Zero GPU, zero solves, nothing in scoring, briefs or configs changed.**
Everything below comes from the stored runs (`runs/nights/v4_*`, 27 campaign cells + 2 finished ripple cells, ~5,100 rows,
4,094 stored responses) re-read offline, plus the earlier research report
`docs/research/SIM_VS_REAL_HORN_2026-10-27.md` (not repeated here). Labels: **[measured]** our own numbers from stored
data, **[published]** outside source, **[inferred]** my reasoning. Scripts (read-only) are listed at the end.

---

## 0. Bottom line

1. **The ranking, not the solver, is the main reason a top-scoring horn may disappoint when built.** The solver is
   self-consistent and textbook-correct (CP-7, TYPOLOGY_VERIFY V5). But J scores only the *shape* of the pattern,
   normalised to on-axis, so it cannot see that most of our winners on the PA briefs are **8-14 dB down in output** at
   500-830 Hz compared with a properly loaded horn [measured]. On the 400 Hz brief J even pushes the search
   toward *shorter* horns (`b3a__ath_core_14in`: length vs J Spearman +0.84, winner on the lower length bound) [measured].
   Loaded horns exist in the stored data (depth correlates with throat loading at 500 Hz, r = 0.64-0.92); J ranked them down.
   The physics is simple and the sim gets it right: an OS / R-OSSE waveguide loads like a cone that starts
   r0/tan(a) behind the throat, so on a 1.4" exit a 90 deg waveguide cannot load at 400-600 Hz at any mouth size;
   the families with a slow-starting throat (Le Cleac'h, ATH core law, hypex sections) can (s1.1).
   Re-scoring all 4,094 stored designs with loading on (s1.7) changes the cell winner in 10-13 of 27 cells, mostly to
   close neighbours; the 90x90 / 400 Hz brief's three leading cells contain **no** design within 3 dB of loading, so
   that brief needs a new search with loading-capable families, not a re-rank.
2. **The search is under-powered for its number of knobs.** R-OSSE/OSSE cells search 9-17 parameters with 100-250
   solves; 1-4 parameters carry ~80 % of what moves J; many cells were still improving when their budget ran out
   (best found in the last 10 % of the run in 11 of 25 cells). Cutting each cell to its 4-6 knobs that matter, then
   polishing, is the single biggest speed-up for the GA. Refused designs use 23 % of every budget [measured].
3. **Five things the sim does not see today that a measurement will:** throat loading/output (above), anything
   below 500 Hz (the 400 Hz brief's own f0 is never solved), the presence band at only 3 points (a coarse grid missed
   the narrowest beam there by up to 12 deg on stored designs), a 2 m observation
   distance centred on the throat (near-field for big mouths: up to ~10 deg beamwidth error in band, measured), and the
   woofer: spacing at the crossover and directivity match (owner's point; several winners put the first vertical null
   **inside** the coverage window with a typical woofer under them) [measured/inferred].
4. **What I would do, in order:** (A) zero-GPU scoring fixes with a rank-change table for approval (sections 2-3),
   (B) one calibration night that checks the cheaper/more honest solve settings before using them, (C) re-search with
   fewer knobs, two stages and budget moved to the leaders, (D) validate against one published measured horn and print
   two contrasting finalists, measured exactly the way the sim "measures".

---

## 1. What the stored data says

### 1.1 Throat loading = real output at the bottom of the band  [measured]

`Re z` is the normalised throat resistance (1.0 = fully loaded). Radiated power is `|U|^2 x Re(Z_throat)` [published:
Akabak docs, Kolbrek; see `SIM_VS_REAL_HORN_2026-10-27.md` s3]. If the diaphragm motion did not depend on the load,
`10 log10(Re z)` would be the output loss versus a fully loaded throat; a real compression driver moves a little more
when the load drops, so the true loss is somewhat smaller - roughly 60-100 % of that figure in dB depending on how
strongly the driver is damped (e.g. Re z 0.04 -> about -8 to -14 dB) [inferred, simple lumped model; the driver model
in s4 D2 gives the per-driver number]. Best design of each cell (screen grid), upper-bound loss:

| cell (brief f0) | Re z at 500 / 643 / 828 Hz | output gap vs fully loaded at 500 / 643 / 828 Hz (upper bound) | depth mm |
|---|---|---|---|
| **b3a__rosse_morph** (400 Hz) - J 1.31, best J anywhere | 0.04 / 0.07 / 0.12 | **-14 / -11 / -9 dB** | 229 |
| b3a__ath_core_14in (400) | 0.05 / 0.11 / 0.20 | -13 / -10 / -7 dB | 250 |
| b3a__biradial_keele (400) | 0.05 / 0.08 / 0.15 | -13 / -11 / -8 dB | 178 |
| b3a__lecleach_rollback (400) | 0.08 / 0.44 / 0.69 | -11 / -4 / -2 dB | 165 |
| b3bt__rosse_morph (600, load weighted) | 0.08 / 0.14 / 0.41 | -11 / -9 / -4 dB | 231 |
| b3bt__lecleach_iwata_ar (600) | 0.52 / 0.68 / 0.85 | **-3 / -2 / -1 dB** | 248 |
| b3bt__salmon_x_signed (600) | 0.14 / 0.54 / 0.81 | -9 / -3 / -1 dB | 370 |
| native__ath_twinray_380 (743) | 0.09 / 0.12 / 0.28 | -11 / -9 / -6 dB | 223 |
| b1w / b1t hi-fi cells (850) | 0.06-0.07 / 0.11-0.20 / 0.17-0.26 | -12 / -8 to -10 / -6 to -8 dB | 125-221 |
| crease__core_law, native__ath_core (1280) | 1.1-1.6 / 1.5-1.7 / 1.3-1.4 | loaded | 411-442 |

Reading it: a horn that is 8-14 dB down at its own design frequency needs that much EQ there, i.e. roughly 2.5-5x the
diaphragm excursion, which is exactly where compression drivers distort and fail [published: SIM_VS_REAL s3; inferred numbers].
The hi-fi OSSE cells at 850 Hz are 6-8 dB down at 828 Hz: usable with a crossover at ~1.1-1.4 kHz (table below), not at 850 Hz.

**Lowest loaded frequency of each winner** (first frequency from which Re z stays >= 0.5, i.e. within ~3 dB of a
loaded throat; roughly the lowest sensible crossover for that horn) [measured, interpolated on the screen grid]:

| brief (f0) | winners: lowest loaded frequency (x f0) |
|---|---|
| b3a 90x90 PA (400 Hz) | rosse_morph **1,600 Hz (4.0x)**, ath_core_14in 1,230 (3.1x), biradial 2,090 (5.2x), lecleach_rollback 680 (1.7x) |
| b3bt / b3bw 90x60 PA (600 Hz) | lecleach_iwata <= 500 (OK), salmon_x 630 (1.05x), hypex hybrid 820 (1.4x), rosse_morph 890 (1.5x), biradial 1,780 (3.0x) |
| b1 90x60 hi-fi (850 Hz) | lecleach_iwata 915 (1.1x), salmon_x / flutes 900-1,000 (1.1-1.2x), OSSE winners 1,120-1,430 (1.3-1.7x) |
| b2 60x40 PA (1,200 Hz) | all 500-860 (0.4-0.7x): fine |
| native / crease core law (1,200-1,280 Hz) | all <= 750 (fine) |

**It is a ranking problem, not (mostly) a search-space problem.** In 11 of 27 cells at least 10 % of the explored designs
load properly at 643 Hz (Re z >= 0.5; `b3a__lecleach_rollback` 71 %, `b3bt__lecleach_iwata_ar` 100 %, `b2t__lecleach_iwata_ar`
99 %), and horn depth correlates with Re z at 500 Hz at r = 0.64-0.92 [measured]. **But family matters as much as depth:**
R-OSSE and biradial cells never reached Re z 0.5 at 643 Hz at any depth they tried (up to 534 mm in `b3a__rosse_morph`);
Le Cleac'h, ATH core law and the hypex/OSSE hybrids do. The throat law decides loading; the mouth decides pattern.

**Why the OS-family horns cannot load low: the throat, not the mouth** [published theory + measured match]. An OS /
R-OSSE waveguide is, below its pattern-control region, close to a cone whose apex sits `x0 = r0 / tan(a)` behind the
throat (r0 throat radius, a wall half-angle). A cone's throat resistance is `Re z = (k x0)^2 / (1 + (k x0)^2)` (Kolbrek;
our TYPOLOGY_VERIFY V5 already passed this check on a conical seed). For the b3a winner (r0 18 mm, a 34.1 deg) this predicts
0.06 / 0.09 / 0.14 at 500 / 643 / 828 Hz; the BEM gave **0.04 / 0.07 / 0.12** - so the solver is right and the shortfall is
physics. Re z reaches 0.5 only where `k x0 = 1`, i.e. **f = c tan(a) / (2 pi r0)**: about 2.0 kHz for that horn, 3.0 kHz
for a 1.4" exit at 45 deg. Mouth size does not enter. Across the cells, the knob that drives loading at 643 Hz is the wall
angle a_deg in R-OSSE (Spearman -0.76 to -0.84) and the length L in OSSE (+0.77 to +0.98) [measured]. Consequence: on a
1.4" exit, a 90 deg OS-type waveguide cannot be loaded at 400-600 Hz whatever the search does; the low PA briefs need a
throat law that starts slowly (Le Cleac'h, ATH core law, hypex/exponential throat sections - the cells that do load),
a larger exit (2"), or a higher crossover. Budget on b3 briefs should move to those families.

### 1.2 J pushes the 400 Hz brief the wrong way  [measured]

`b3a__ath_core_14in`: Spearman(length L, J) = **+0.84** (shorter scores better), winner at the lower length bound
(normalised position 0.03). Shorter horns load worse, but J has no loading term on b3a, and its one-sided below-f0 rule
cannot fire because nothing below 500 Hz is solved while the brief's f0 is 400 Hz. The screen grid is
`500-10,000 Hz, 12 points` clipped to band_hi (`config.py FREQ_GRIDS`), so **the b3a brief's 300-500 Hz is never solved**.

### 1.3 The GA is under-powered for its number of knobs  [measured]

| | value |
|---|---|
| searched parameters per cell | 3-17 (R-OSSE + morph: 17; OSSE + morph: 8-15; FREEFORM generators: 3-8) |
| solves per cell (two nights) | 100-250 (popsize 10-12 -> ~10-20 CMA generations) |
| cells whose best design came in the last 10 % of the run | 11 of 25 (cells with >= 100 rows) |
| share of the total gain made in the last quarter | gcurve 63 %, b3bw hybrid 28 %, b3bt R-OSSE 27 %, b2w OSSE 23 %, b2w hybrid 15 %, b2t Le Cleac'h 15 % (still climbing) |
| refused (invalid geometry/envelope) | 1,166 of 5,108 new evaluations = **23 %**, 0.45 h of wall time, but **each counts against the budget** |

CMA-ES learns its search shape at rates of order 2/n^2 per generation (n = number of knobs) [published: Hansen, CMA-ES
tutorial]; at n = 17 and popsize 12 that is about 1.5 % per generation [inferred from the tutorial's default formulas],
so after ~15 generations the search shape has barely adapted and the run is close to a random walk with step-size
control. At n = 5 the same rates are ~8x faster. **Which knobs matter** (gradient-boosted model per cell, permutation importance, share of explained
effect on log J) [measured]:

| cell | knobs | knobs carrying 80 % | the ones that matter |
|---|---|---|---|
| b3a__rosse_morph | 17 | 3 | a_deg 64 %, b 11 %, aspect 7 %, a0 4 %, m 4 %; the six morph_* knobs 0-3 % each |
| b2t__rosse_morph | 17 | 1 | a_deg 88 %, r 6 %, m 3 %; everything else <= 1 % |
| b3bt__rosse_morph | 17 | 2 | a_deg 42 %, m 39 % |
| b1t__rosse_morph | 17 | 3 | a_deg 59 %, aspect 17 %, m 10 % |
| crease__osse_b1w | 14 | 2 | L 79 %, morph_rate 9 %; ten azimuthal crease knobs ~0-6 % |
| gcurve__osse_b1w | 9 | 1 | L 94 % |
| native__ath_core | 14 | 4 | L 47 %, s 13 %, morph_rate 13 %, a_deg 11 % |
| b1w / b2w osse_baseline | 9 | 3-4 | L, a_deg, aspect / n, k |
| crease__core_law | 17 | 6 | n, L, morph_rate, a_deg, s, az_a_sf_amp (model fit weak, R^2 0.06) |

Caveat: importance is measured over what the search explored. Re-checked under the loading-aware + strict score (s1.7):
the same 1-5 knobs carry 80 %, because the knobs that set loading (a_deg in R-OSSE, L in OSSE, k in ATH core) are the
same knobs that set the pattern [measured].

### 1.4 Observation distance and centre  [measured, `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` s1]

Polars are taken on a 2 m arc around the **mesh origin = the throat plane**, not the mouth. Measured on stored
hi-fi-size horns (335 mm mouth): beamwidth changes up to **10.5 deg in band** between 2 m and 50 m (AXI, 3 kHz),
DI up to 1.6 dB; 2 -> 10 m captures ~80 % of the 2 -> 50 m change. Below ~1 kHz the 2 m arcs read 4-15 deg **narrower**
than the far field (the sim flatters pattern control near f0); around 2-3 kHz some read 4-10 deg wider. PA mouths (600-700 mm) are deeper inside the
near field (Fresnel distance D^2/lambda = 5.7 m at 4 kHz for a 700 mm mouth). The 10 m proposal (WP5) has been waiting
for an owner decision since 2026-10-24.

### 1.5 Woofer integration (owner's question)  [measured geometry + inferred rule]

Horn directly above the woofer, frames touching, crossover at the brief's f0, typical woofer frame radius
(12" 155 mm, 15" 195 mm, 10" 130 mm - assumptions, change per real driver). Two in-phase sources of equal level a
distance d apart cancel where the path difference is half a wavelength, so the **first vertical null sits at
sin(theta) = lambda / (2 d)** [published, two-source array textbook result]. Keeping it outside the vertical coverage
needs **d <= lambda / (2 sin(V/2))**: 1.0 lambda for 60 deg V, 1.46 lambda for 40 deg, 0.71 lambda for 90 deg.

| cell | f0 | V cov | mouth h | woofer | c-c / lambda | first null | verdict |
|---|---|---|---|---|---|---|---|
| crease__core_law | 1280 | 50 | 520 | 12" | 1.55 | 19 deg | **null inside coverage** |
| native__ath_core | 1280 | 50 | 420 | 12" | 1.36 | 22 deg | **null inside coverage** |
| native__lecleach_rollback / asym_odd | 1200 | 90 | 313-316 | 10" | 1.00 | 30 deg | **null inside coverage** |
| ripple flute8 cells (b1t brief) | 850 | 60 | 499-514 | 12" | 1.00-1.02 | 29-30 deg | **null at/inside the edge** |
| b1t__rosse_morph, b1t__salmon_x_signed | 850 | 60 | 436-452 | 12" | 0.92-0.94 | 32-33 deg | edge |
| b2t cells (tall) | 1200 | 40 | 370-495 | 12" | 1.19-1.41 | 21-25 deg | edge |
| b3bt__salmon_x_signed | 600 | 60 | 609 | 15" | 0.87 | 35 deg | edge |
| b1w, b3bw, other b3bt, twinray | 600-850 | 60 | 255-462 | 12-15" | 0.67-0.80 | 39-48 deg | OK |
| all b3a (90x90, 400 Hz) | 400 | 90 | 354-681 | 15" | 0.43-0.62 | 53-90 deg | OK (lambda is long) |

General rule that falls out of the K-law [inferred]: a mouth sized for pattern control to f0 is 74/V wavelengths tall
at f0, so **crossed at its own f0 a K-law horn is already at the edge of the spacing rule with a typical woofer**;
any horn taller than K-law (the "tall" and fluted variants) or a 90 deg-vertical horn crossed above ~800 Hz breaks it.
Ways out: allow the mouth to overlap the woofer (common in hi-fi; reduces d by the overlap), a smaller woofer, cross
lower (needs a loaded throat - s1.1), or a coaxial/multi-entry layout (deferred by owner decision).

**Directivity match at the crossover** [measured horn DI; inferred piston DI]: horn DI at f0 exceeds a baffled piston
woofer's DI by +2.3-2.8 dB (b1w), +3.1-4.0 dB (b3bt), **+4.6-5.7 dB (b3a)**, +4.9-5.5 dB (ath core / crease core law).
A step of this size is a step in the off-axis / room sound through the crossover - the "even coverage across frequency"
priority applied to the whole speaker. Nothing in today's briefs knows about the woofer.

### 1.6 The presence band is under-sampled  [measured]

Today's screen grid has **3 points in 2.5-5.5 kHz** (2,919 / 3,756 / 4,832 Hz, ~0.36 octave apart) - the band the owner
ranks as the worst place to narrow. 15 stored designs were solved on both an older screen grid (4 points in the band) and
the 25-point verify grid (5 points in the band). Interpolating the screen beamwidth onto the verify frequencies misses the
verify value by a **median 7 deg, 90th percentile 10.6 deg, worst 13.9 deg**, and the **narrowest beam in the band was
missed by up to 12.4 deg** (median 1.4 deg). With only 5 verify points the true narrowest is likely narrower still.
So both the screen and the verify grid need more points there (s4 C: ~7 points in the band).

### 1.7 Re-score with loading and stricter pattern scoring (P12a)  [measured, offline, exact]

Every stored valid design with a response (4,094) re-scored through the real `objective_v4` on rebuilt metrics; the
run's own brief reproduces the stored J **exactly** (max |error| 0.0). Variants:
**L** = today's brief with `load` replaced by the output-at-f0 term of s2.1 (worst case from 0.95 f0, 3 dB = one unit,
weight 1.0 PA / 0.5 hi-fi); **S** = stricter pattern (s2.2); **L+S** = both.

| | winner changes (of 27 cells) | median Spearman vs today | median top-5 overlap |
|---|---|---|---|
| L | 10 | 0.99 (min 0.07) | 4/5 |
| S | 13 | 0.99 (min -0.22) | 4/5 |
| L+S | 13 | 0.99 (min -0.23) | 4/5 |

Within a cell, most winner changes are to a near neighbour (today's rank 2-6). The big reorders are the class-B loading
controls under S: `native__lecleach_*` (Spearman -0.22, new winner today's rank 70-92) and `b3bt__lecleach_iwata_ar`
(0.38) - S scores narrow beams below f0 there for the first time, so S for class B needs the calibration night first.

**The important result is what re-ranking cannot do.** Best design in each cell that is within 3 dB of a loaded throat
at f0, and what it costs in today's pattern score:

| cell | today's winner J (output gap at f0) | best design within 3 dB: J (gap) | cost |
|---|---|---|---|
| **b3a__rosse_morph / biradial_keele / ath_core_14in** | 1.31 / 1.96 / 2.05 (11-13 dB) | **none explored** | - |
| b3bw__hyb_osse_h_hypex_v | 3.29 (5.4) | none explored | - |
| b3a__lecleach_rollback | 12.38 (9.3) | 14.07 (2.8) | +14 % |
| b3bt__rosse_morph | 3.75 (6.9) | 5.15 (2.1) | +37 % |
| b3bt__salmon_x_signed, b3bt__lecleach_iwata_ar | 4.02 (1.2), 5.45 (0.1) | already loaded | 0 |
| native__ath_twinray_380 | 3.00 (4.0) | 4.66 (1.8) | +55 % |
| b1w hi-fi OSSE cells (crease, control, gcurve, baseline) | 3.86-5.47 (4.4-6.0) | 6.24-6.98 (2.4-2.8) | +14 % to +75 % |
| b1t__rosse_morph / b1t__salmon_x_signed | 8.43 (6.1) / 6.99 (5.6) | 14.22 (2.9) / 7.87 (2.9) | +69 % / +13 % |
| ripple flute8 cells | 9.41-9.85 (3.8-4.2) | 9.87-10.33 (1.8-2.3) | +5 % |
| all b2 (60x40, 1.2 kHz), native ath core, crease core law, native Le Cleac'h | - | already loaded | 0 |

Reading it:
* **The 90x90 / 400 Hz brief has no acceptable horn yet.** Its three leading cells never explored a design within
  3 dB of loading (they are 11-13 dB short), and s1.1 says why: 1.4" OS-type throats cannot load there. Even with the
  L term on, `b3a__ath_core_14in` still prefers shorter horns (Spearman of length with J: +0.84 today, +0.80 under L),
  because no explored length gets close enough for the loading term to pay. Fixing b3a needs a new search with
  loading-capable families (or a 2" exit), not a re-rank.
* **Per brief, the leader changes once loading is in.** b3bt (600 Hz): `salmon_x_signed` (1.2 dB gap) leads its brief
  under every variant; the R-OSSE cell that led on a separate brief copy is 7 dB short. Hi-fi b1w: every OSSE design
  in that box is 4-6 dB short at 850 Hz; being loaded costs 14-75 % of pattern score, so the honest choices are a
  ~1.1-1.4 kHz crossover (s1.1 table) or a deeper / different throat - an owner trade-off, not a scoring bug.
* **Loading-aware scores mainly steer future searches.** The stored searches followed today's J, so they rarely went
  where loaded designs are. That is why s3 (reduced knobs, seeds that load, budget by brief) matters as much as s2.
* Knob importance under L+S is essentially unchanged (same 1-5 knobs carry 80 %: L, a_deg, aspect, m, morph_rate,
  s/n), so the lock table in s3.2 holds under the new score [measured, `importance_ls.py`].

### 1.8 The simulated throat is not always the driver's exit  [measured, added after the first pass]

Measured from the stored meshes (driven source patch = where the driver couples): in every OSSE / R-OSSE cell
with `aspect_ratio` != 1 the coupling plane itself is stretched - `b3bt__rosse_morph` 24 x 36 mm,
`b3a__rosse_morph` 26 x 36 (and squarish), `b1t__rosse_morph` 26 x 36, `crease__osse_b1w` 41 x 36,
`b1w__osse_baseline` 50 x 36 - on briefs whose driver exit is a round 36 mm. The radius pin (WP2) holds, but
the aspect stretch was never pinned. Generator families, ATH core and all aspect-1 cells couple round at the
right size. **Owner rule (2026-10-27): no separate adapter; only the coupling plane must be round at the
exit size; morph, ridges and non-round shapes are fine right after it.** How fast the horn may leave round
has no published number (`docs/research/THROAT_COUPLING_2026-10-27.md`: confirmed round coupling plane from
ATH, Geddes and JBL practice; the transition rate is qualitative - test it with our own `morph_fixed` cells). Check:
`hornlab_search/mesh/throat_check.py`, column in `tools/loudness_report.py`; method page `docs/DRIVER_MODEL.md`.

---

## 2. What I would change in the scoring (owner approval needed; all zero-GPU to try)

**2.1 Add an "output at f0" term (replaces today's `load` on every brief).** In dB, worst case, from f0 up:
`Ldb = max over solved f >= 0.95 f0 of max(0, 10 log10(0.7 / Re z(f)))`, tolerance 3 dB = one unit.
Weight 1.0 for PA / low-reach (classes B, C), 0.5 for hi-fi waveguides (class A). Why this form: it is in the units a
system designer thinks in ("8 dB short at 600 Hz"), a worst case cannot be averaged away by well-loaded high
frequencies (today's band-mean hinge can), and 0.7 is the research report's z_min (-1.5 dB allowed free). Optional
hard version: treat `Ldb > 6 dB at f0` as infeasible (graded penalty) so the search never spends solves near it.

**2.2 Stricter pattern scoring** (the "S" variant above): cov tolerance 2 -> 1 (class A) and 4.5 -> 2 (B, C), presence band
2.5-5.5 kHz weight 2x -> 3x, one-sided below f0 for every class (wide below f0 is free, narrow is not).

**2.3 System block in the brief (new, geometry only, pre-mesh, free).** `system: {woofer_in, woofer_frame_mm,
crossover_hz, woofer_side: below, max_overlap_mm}`. Two uses: (a) a feasibility rule on mouth height in the woofer
plane, `h/2 + woofer_r - overlap <= lambda_xo / (2 sin(V/2))`, refused before meshing so it costs nothing; (b) a
report-only (later scored) DI-match number: horn DI at the crossover minus the woofer piston DI.

**2.4 Score at 10 m** (polars and balloon), keep a report-only 2 m field for comparison with a 2 m measurement.
Free per solve (field evaluation is ~0.4 s of ~45 s), but it changes the solve-cache key, so it applies to new solves.

**2.5 Above the driver's throat cross-mode** (1.4" exit: f11 ~ 5.7 kHz, 1": higher, 2": lower) the ideal flat source is
wrong for any real driver [published: SIM_VS_REAL s1]. Halve the frequency weight above f11 so the search does not
optimise a behaviour no driver will reproduce; keep it in the reports.

Not recommended: more weight on DI slope (it fights constant directivity; keep `distd` instead), more terms of the same
kind (the v4 review already showed term dominance is the risk).

---

## 3. Making the GA reach the best horn in fewer solves

**3.1 Count only real solves against the budget.** Refusals are cheap (median 0.4 s) but consume 23 % of the budget.
Make the budget "valid solves" (or GPU-seconds). Then make sizes feasible by construction where possible: mouth width
and height as a fraction of the envelope / K-law size instead of absolute millimetres (most `invalid_envelope` rows),
and the new woofer-spacing rule checked before meshing.

**3.2 Fewer knobs, two stages.** Stage 1 searches only the 4-6 knobs that matter (table in 1.3, re-checked on the
re-scored table) with sigma 0.25; stage 2 unlocks the next 4-6 at sigma 0.08 around the stage-1 winner. Proposed
locks [measured importance + inferred physics]:

| family | search in stage 1 | lock (or stage 2 only) |
|---|---|---|
| R-OSSE + morph | a_deg, a0_deg (throat: loading), m, b, R, morph_rate | **aspect_ratio = 1** (s1.8: it stretches the coupling plane; the mouth aspect comes from the morph), k, q, r, tmax, exponent, morph_corner/exponent/fixed; morph width/height pinned to the brief's K-law mouth |
| OSSE + morph (incl. ATH core) | L, a_deg, s or n, a0_deg, morph_rate; k for ATH core (drives loading there, Spearman +0.53) | **aspect_ratio = 1** (s1.8), q, exponent, morph_corner/fixed/exponent; mouth aspect via the morph target |
| crease / pucker (OSSE + azimuthal) | L, a_deg, morph_rate, the 2 strongest az knobs | the other 8 az knobs in stage 2 |
| FREEFORM generators (3-8 knobs) | as now | - |

Also bound `a0_deg` to the driver's real exit half-angle +- 1 deg (b3a: driver 2 deg, box 1-4 deg, winner 1.0 deg):
the printed throat must continue the driver exit without a kink.

**3.3 Seeds from physics and from the data, several per cell.** Seed with (a) the K-law mouth, (b) a depth that loads
(from the stored data: loaded designs at 643 Hz start around 160-200 mm depth in the families that can load; R-OSSE and
biradial did not load at any explored depth), and (c) the top 2-3 *distinct* designs of the earlier runs re-ranked under
the new score - the stored responses already contain loaded designs in 11 cells, so those searches do not start from
zero (the b3a OS-type cells have none; s1.7).

**3.4 Put the budget where the leaders are (successive halving per brief).** First, by physics (s1.1): on the
400-600 Hz PA briefs give R-OSSE, OSSE-90 and biradial cells no more budget unless they get a slow throat section;
spend it on Le Cleac'h, ATH core law, hypex hybrids and salmon-X, which can load. Then, instead of today's equal budget
per cell, per brief: all its cells to ~60 valid solves; keep the top half; extend to ~150; keep the top one or two; extend to
~300 with restarts. Same GPU hours, roughly 3x the solves on the eventual winner.

**3.5 Try pycma's built-in surrogate (lq-CMA-ES)** [published: Hansen 2019; `cma.fitness_models.SurrogatePopulation`
is present in our pinned pycma 4.5.0, measured]: it fits a linear/quadratic model to the evaluated points and spends
real solves only where the model is unsure. Reported savings are large on smooth problems and smaller on rugged ones;
our J is rugged (threshold-crossing beamwidths), so this is an A/B on one or two cells, not a default.
(Our own neural surrogate failed its top-k gate on 2026-10-23; do not use it for selection.)

**3.6 Make the cheap part of the solve do the filtering.** The band-split mesher (WP8, measured 28-54 % wall saving)
meshes each band at its own top frequency; a band below ~2 kHz has ~10x fewer unknowns and assembly time grows
about as unknowns^1.6 [measured over 3,942 stored solves; assembly is 28 of 45 s on a 7,700-unknown b3a solve]. So: solve the low band
first (adding 0.7 f0 and f0 points costs almost nothing there), compute loading and low-frequency pattern, and
**skip the expensive high band when the design is already hopeless** (e.g. Ldb > 9 dB). This makes the loading-aware
search cheaper than today's. Needs the calibration in s4 B1 first (throat faceting on a coarse mesh can bias Re z).

---

## 4. Getting from here to the best horn per brief - the sequence

**A. Now (zero GPU, during the night):** owner reviews s1.7 and picks the score changes (2.1-2.5). Re-rank the stored
designs under the chosen score; re-run the importance table; write the reduced search sets and seeds (3.2, 3.3).

**B. One calibration night (~3-4 h, after the current night ends):** on 6 stored finalists spanning hi-fi and PA:
(1) band-split screen vs today's single mesh (acceptance: Re z within 0.03, beamwidth within 2 deg, DI within 0.2 dB);
(2) 10 m vs 2 m (expect the s1.4 deltas); (3) epw 6 vs 9 in the presence band (the residual-risk item still open);
(4) the verify grid on the top 5 per brief under the new score - **does the screen ranking survive 25 points?**
If (4) flips winners, the screen grid needs presence-band points before any more nights.

**C. Search nights under the new score:** new screen grid = band-split at 2 kHz; the low band keeps today's 6 points
and adds 0.7 f0 ... f0 at ~6 points/octave; the high band keeps today's 6 points and adds ~4 in 2.5-5.5 kHz (about 7 points
there instead of 3); 10 m; reduced knobs; two stages; successive halving; budget = valid solves.
**Estimated cost: about 0.9x today's time per design** [inferred from measured scaling: solve time ~ unknowns^1.3 over
3,942 stored solves; a 2 kHz mesh has ~1/12 of the unknowns of the 8 kHz mesh (WP8 measured 6,049 -> 497 for a 4x lower
top frequency), so each low-band point costs ~4 % of a full point; meshing is 0.7 s median, 14 % of wall time]. So the
grid gets better in both places that matter and the night gets slightly shorter - subject to the B1 calibration.

**D. Reality:** (1) one published measured horn through our pipeline (P12b), acceptance beamwidth +-5 deg (+-3 deg in
the presence band), DI +-1 dB, pattern-control corner within 1/6 octave; (2) a lumped compression-driver model over
the stored throat impedance for finalists only (predicted on-axis level, excursion; needs real T/S data with Mmd);
(3) print two contrasting finalists for one brief - today's J-winner and the loading-aware winner - and measure both
(s5). If the loading-aware one measures better where the J-winner is unloaded, the scoring change is confirmed.

---

## 5. Printing and measuring so the comparison is fair  [inferred, from the sim's own conventions]

The sim is a **free-standing rigid horn with a 5 mm shell, measured on 2 m arcs around the centre of the throat
plane**, ideal flat source at the throat, no cabinet, no woofer. Measure the print the same way first, then in the box.

* **Geometry:** print from the exported STEP of the exact design hash; check the throat diameter and exit angle against
  the actual driver (a step or kink at the junction reflects energy at high frequency); dowel the 4 pieces and fill/sand
  seams to < 0.3 mm; walls >= 5 mm (as simulated), 4-6 perimeters, gyroid; knock-test large flat panels, add damping if
  they ring.
* **Rig:** horn free-standing on a turntable, **rotation axis through the throat-plane centre** (where the sim's arcs are
  centred), mic at 2.0 m from that point for the comparison with the 2 m report field; H and V at 5 deg steps, plus 45 deg
  for crease/pucker cells. Gated impulse indoors is fine above ~400-500 Hz; for the loading region use outdoor or
  ground-plane measurements.
* **Compare:** beamwidth vs frequency, DI, normalised polar map (pattern accuracy), then on-axis level at fixed voltage and
  the driver's electrical impedance on the horn (loading accuracy: impedance ripple below ~1 kHz shows the throat
  loading the sim predicted).
* **Start small:** a b1-size horn (~340 x 300 x 150 mm) calibrates pattern accuracy at a fraction of the print time of
  a 700 mm PA horn; then print the loading-aware PA finalist.

---

## 6. Balancing hi-fi sensitivity, PA power and "organic" shapes (owner question, added)

**Pattern is the score; "does it work" is a gate.** J stays pattern quality (coverage, presence band,
smoothness, constant DI) - the thing shapes compete on. Whether a horn works becomes pass/fail per brief, so an
unusual shape is never penalised for looking different, only for failing:

1. coupling plane round at the driver exit (geometry, before meshing, free);
2. woofer spacing at the crossover (geometry, free; s1.5);
3. output at f0 within a set number of dB of a loaded throat (from the solve; s2.1);
4. per use case, against the **brief's driver list** (pairing is a free post-process, `docs/DRIVER_MODEL.md`):
   hi-fi for tube amps = sensitivity at 1 W / 1 m above a floor over the passband on at least one listed driver;
   PA = maximum SPL at f0 and across the band above a target (rated power or excursion) on at least one
   listed high-power driver.

Why gates and not more weights: a weight trades pattern against loudness at an exchange rate nobody can
defend, while a gate says "be at least this loud, then make the pattern as good as possible" - which is how a
designer writes a brief. It also keeps the store of "working" shapes clean for the GA work.

**Diversity, for a handful of non-typical candidates.** One CMA-ES run converges on one shape. The repo already
has CMA-ME (`search/cma_me.py`, quality-diversity: it keeps the best design in each cell of a map), but its map
axes are mean H/V beamwidth. With shape axes instead - mouth non-roundness (morph amount / superellipse), ridge
or flute amplitude, azimuthal lobing (crease/pucker), depth - each organic family returns a gallery: the best
design for each "look", all passing the gates, and the owner picks by eye among horns that work.

**The cache.** The solve cache is keyed on geometry + solver settings, not on scoring, gates or drivers, so all
of it is reused when those change. What does invalidate it: the frequency grid, the observation distance and
the mesh settings. Settle those in the calibration night (s4 B) first; every later night then adds to one
consistent data set for the GA / surrogate work.

---

## 7. Owner decisions

1. Output-at-f0 term (2.1): adopt, and the weights 1.0 PA / 0.5 hi-fi?
2. Stricter pattern scoring (2.2): adopt fully, partly, or not?
3. Woofer system block (2.3): which woofer and crossover per brief (or the defaults in s1.5)? Is mouth-over-woofer overlap
   allowed, and how much?
4. Score at 10 m (2.4) and halve the weight above f11 (2.5)?
5. Calibration night (s4 B) as the next GPU job after the ripple/ridge night?
6. Reduced knobs + two-stage + successive halving (s3) for the next search nights?
7. The driver list per brief, and the gate levels: sensitivity floor (1 W / 1 m) for the tube-amp hi-fi briefs,
   maximum-SPL target for the PA briefs (s6).
8. Decided 2026-10-27: no separate throat adapter; only the coupling plane must be round at the driver exit (s1.8).

---

## Sources

| Source | Kind | Supports | Verified this pass |
|---|---|---|---|
| Stored v4 runs, `runs/nights/v4_{overnight,resume,ripple_ridge}_2026-10-27/` (search.ndjson, designs/*/response.npz, config.yaml) | [measured] | s1 all tables | yes (re-read; stored J reproduced exactly) |
| `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` s1 (2/10/50 m) and s5 (band split) | [measured] | s1.4, s3.6 | yes (read) |
| 15 designs stored on both a screen and a verify grid (`runs/20261023T19*-verify-*`, `runs/20261025T013051Z-verify-*` vs their screen runs; `metrics.json`) | [measured] | s1.6 | yes (re-read) |
| `docs/evidence/TYPOLOGY_VERIFY.md` V5 (Re z vs Webster/conical theory) | [measured] | s0 solver correctness | yes (read) |
| `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` (Kolbrek, Akabak, Boundary Lab #78, Panzer/Macey, Keele/Hughes, Sridhar et al.) | [published] via that report | output ~ Re z, ideal-source limits, f11, validation thresholds | that report's own table |
| N. Hansen, "The CMA Evolution Strategy: A Tutorial", arXiv:1604.00772 | [published] | learning rates ~2/n^2 (s1.3) | from memory, not re-fetched |
| N. Hansen, "A Global Surrogate Assisted CMA-ES" (lq-CMA-ES), GECCO 2019; pycma `cma.fitness_models` (https://github.com/CMA-ES/pycma) | [published] / [measured: present in pycma 4.5.0] | s3.5 | module presence checked; paper from memory |
| Two-source interference: first null at sin(theta) = lambda/(2d); piston DI = 10 log10((ka)^2 / (1 - J1(2ka)/ka)) | [published, standard acoustics texts, e.g. Kinsler et al., *Fundamentals of Acoustics*] | s1.5 | textbook results, not re-fetched |
| Fresnel / far-field distance ~ D^2/lambda | [published, standard] | s1.4 | textbook |

Not verified: exact lq-CMA-ES speed-up figures (deliberately not quoted); real T/S data for the brief drivers (needed
for the driver model, s4 D2); woofer frame radii and effective cone radii are typical values, not measured drivers.

Scripts and outputs in `scratch/p12_senior_pass/` (gitignored, local only; read-only analysis; `p12a_rows.csv` holds
every re-scored design; `gather.py <out.pkl>` first, then each script on that pickle): `gather.py` (rows + stored responses), `analyse.py`
(convergence, loading, sensitivity), `importance.py` (knob importance), `rescore_p12a.py` (variant objectives through
`objective_v4` on rebuilt metrics), `p12a_table.py` (s1.7 tables), `importance_ls.py` (importance under L+S),
`cc.py` / `dimatch.py` (woofer spacing, DI match), `screen_verify_pairs.txt` (s1.6 design pairs).
