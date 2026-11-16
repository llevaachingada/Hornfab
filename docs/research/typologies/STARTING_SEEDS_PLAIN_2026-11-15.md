# Six starting points for the home horn: a plain-language decision brief

**Date:** 2026-11-15. **Status:** the owner paused new solves at 17:15; the night-E runner and the
current Crowe-section run were stopped. This brief is for the decision that comes **after** the
brief/DI-slope question and the lip/waist geometry are settled. **Purpose:** help the owner choose
which shapes get the next GPU search night. This is a shape-finding decision, not a listening
verdict. The 3D files are the visual evidence; the citations are the outside design/measurement
evidence. Where a claim is our own inference, it says so.

3D turntables (open in a browser or image viewer; they rotate through 360 degrees). The full
decision packet with shaded renders, H/V sections, parameter tables, the issues log and the
decision matrix is `STARTING_SEEDS_2026-11-15.html`.

| Seed | File | Size (W x H x D) | What it is |
|---|---|---|---|
| Ext-throat constant-directivity | `img_biradial_crowe_2026-11-15/seed_ext_throat.gif` | 528 x 366 x 370 mm | the current best-scoring family; a smooth CD waveguide, not a Crowe look |
| R-OSSE rounded rectangle | `img_biradial_crowe_2026-11-15/seed_rosse_rect.gif` | 560 x 360 x 186 mm | a modern smooth waveguide with a landscape rounded-rectangle mouth |
| Crowe-X on a CD throat | `img_biradial_crowe_2026-11-15/seed_crowe_x.gif` | 588 x 398 x 244 mm | the Crowe X/bow-tie look applied to a constant-directivity throat |
| Crowe ES-600 sections | `img_biradial_crowe_2026-11-15/seed_crowe_panel.gif` | 560 x 280 x 273 mm | the digitized Crowe section construction, scaled to the home box; currently running in night E |
| ES exponential spiral | `img_biradial_crowe_2026-11-15/seed_es_spiral.gif` | 542 x 299 x 242 mm | a log-spiral / exponential-spiral analogue of Crowe's ES flare |
| Keele Bi-Radial | `img_biradial_crowe_2026-11-15/seed_biradial.gif` | 560 x 350 x 258 mm | the classic Keele/JBL two-plane Bi-Radial, now with a valid throat blend |

Also useful: `img_biradial_crowe_2026-11-15/starting_seeds_2026-11-15.png` (all six in one
sheet) and `img_biradial_crowe_2026-11-15/crowe_panel_best_night_e.gif` (the best Crowe-section
design found so far in night E). The exact Crowe reference photos remain in `scratch/crowe_ref/`
only, because they are copyrighted.

---

## 1. How a horn works, in one page

A horn does four jobs:

1. **It loads the driver.** The narrowing throat and expanding flare present a higher acoustic
   impedance than free air, so the driver works against a stiffer load at low frequencies. This is
   why a horn can play a 700 Hz crossover with low distortion. Exponential-type flares load best;
   conical flares load less at low frequencies. [Kolbrek, *Horn Theory: An Introduction*]
2. **It sets the coverage angle.** The flare near the throat and the mouth size decide how wide
   the sound spreads, and how that width changes with frequency. A "constant-directivity" (CD)
   horn tries to hold the same angle at all frequencies. A "narrowing" horn lets the beam get
   narrower as frequency rises. [Keele US4071112; Geddes OS waveguide]
3. **It terminates at the mouth.** The mouth is where the wave leaves the horn. A sharp edge
   diffracts sound (bends it around the edge), which shows up as ripples in the response and in the
   polar pattern. Geddes' rule is that a mouth radius of at least a quarter wavelength at the
   lowest frequency you want clean removes most of that diffraction: a 35 mm radius is clean above
   about 2.46 kHz, 50 mm above about 1.72 kHz, and 86 mm above about 1 kHz. A 40-50 mm lip is
   therefore a rational hi-fi choice. The effect is small at 700 Hz and grows with frequency.
   [Geddes, loudspeaker design philosophy; ATH twinray roundover study, which recommends a 35 mm
   enclosure-edge radius]
4. **It shapes the in-room sound.** The direct sound, the early reflections and the reverberant
   field all matter. A smooth, gradual change of directivity is easier to live with than a horn
   that holds a pattern and then jumps. The listening research rewards smoothness more than any
   single DI number. [Olive 2004; Toole/Olive; CTA-2034 PIR]

**The hard limit in this room.** Keele's mouth-size rule is `W = 25,000 / (0.9 x coverage x f)`
when W is in metres and coverage is the full angle in degrees. At 700 Hz an 80-degree horizontal
pattern needs about **496 mm** of mouth width, which fits your 600 mm box (the box actually holds
80 degrees down to about 579 Hz). A 50-degree vertical pattern needs about **794 mm** of mouth
height, which does **not** fit your 480 mm box; the 480 mm height holds 50 degrees only down to
about 1157 Hz, and at 700 Hz it can support only about **83 degrees** vertically. So the vertical
pattern cannot be fully controlled at the crossover in this envelope. The brief already counts
vertical misses half, which is the honest way to handle that. Do not expect a 480 mm-tall horn to
hold 50 degrees vertically at 700 Hz.

**What the X, waist and creases do.** The X-shaped creases, the bow-tie/waisted outline and the
thick lip are Joseph Crowe's visual language. The lip/termination has a real acoustic job (item 3
above). The X and waist are **not** established acoustic requirements in the Keele, Geddes or ATH
literature; they are a construction style. They can still matter: corner creases change the
diagonal pattern, and a bad crease can scatter sound. That is exactly what our `diag` score is
trying to catch, but we do not yet have measured diagonal polars for a Crowe-style horn. Treat
the X/waist as a visual choice until we measure it; treat the lip and the smooth continuous flare
as the acoustically important parts. [Keele; Geddes; ATH; Crowe pages; our inference]

---

## 2. What the outside research says about these families

### Keele / JBL Bi-Radial and the CD horn

Keele's EV patent (US4071112, 1975) describes a CD horn as an exponential throat, then a conical
midsection whose half-angle sets the high-frequency beamwidth, then a bell section. The conical
section is what holds the pattern; the bell only suppresses a midrange narrowing artifact. The
JBL Bi-Radial patent (US4308932A, 1980) uses two wall pairs with a power-series contour
`r = r0 + tan(a) z + c z^n`, a mouth-size rule `W = K/(A F)` with K ~ 25,000, a throat angle
`A = 0.9 x half-coverage`, and a narrow throat gap/slot. The published JBL 2380A data sheet shows
the practical result: 90 x 40 nominal, horizontal pattern held from 500 Hz to 16 kHz, but vertical
constant-directivity only above about 2 kHz. That is the same physical limit we hit with a
480 mm-tall box. The Bi-Radial's high-aspect gap slot is also a diffraction/velocity maximum; it
is a real liability, not just a manufacturing detail. [US4071112; US4308932A; JBL 2380A data
sheet; repo dossier]

**Implication for us:** a Bi-Radial is a credible 80-degree horizontal horn, but it is not a
constant-directivity 80 x 50 horn at 700 Hz in this box, and the classic gap slot is not something
we want to add. Our current biradial cell is a simplified two-plane contour without the slot; it
is a valid classic shape, not a Crowe look.

### Geddes / OS waveguide and mouth termination

Geddes' OS waveguide work argues for a smooth, gradually expanding wall with a round throat and a
generous mouth roundover; sharp junctions and throat-angle mismatches generate higher-order modes
and diffraction. His patent on the waveguide (US7068805) explicitly says the throat should match
the driver and that a round-to-other-shape transition must be gradual. The practical rule is:
smooth surfaces, no sudden kinks, and do not end the horn at a knife edge. [Geddes, OS waveguide
theory / US7068805; ATH roundover study]

**Implication for us:** the smooth R-OSSE rounded-rectangle and the Crowe-section surface are on
firmer ground than a sharp-edged X. A Crowe-style X is not automatically bad, but every crease is
a place where the surface curvature changes, so it needs to be checked in the polar data.

### ATH / Batik: R-OSSE and the roundover BEM study

ATH's R-OSSE is a modern constant-directivity profile that can be evaluated per azimuth and
morphed to a rounded-rectangle mouth. Their published BEM roundover study compared 8.75, 17.5 and
35 mm fillets and a 35 mm chamfer on a small waveguide; the 35 mm radius was the recommendation,
and the study is graphical rather than a formula. ATH's Tritonia page reports a large 100-degree
horn that stays fairly constant from 800 Hz to 16 kHz, and the EXAR story shows that the throat
diameter/extensions sets the high-frequency limit. [at-horns.eu: R-OSSE, Tritonia, twinray
roundover study, EXAR story]

**Implication for us:** the R-OSSE rectangle is the most acoustically defensible shape in the
set for a 700 Hz home crossover. Its weakness is visual (no X/waist) and constructional (the
per-azimuth meridians can leave a wavy rim at extreme roll/corner settings). A mid-roll,
mid-corner-exponent seed is the safe starting point.

### Le Cleac'h / JMLC and Crowe ES: narrowing by design

The Le Cleac'h horn is an exact hyperbolic/exponential family with a mouth that rolls back past
180 degrees. Fourcade's 2015 paper gives the equations; the JMLC reference case (fc 400 Hz,
T = 0.8, 360-degree stop) is about 321 mm long with a 467 mm mouth. Independent FEA by Sheerin
shows the Le Cleac'h DI rising from about 4 dB at 1.4 kHz to about 12 dB at 12 kHz, i.e. roughly
2.6 dB/octave, with smooth off-axis curves; the horn decays cleanly, unlike a conical horn. That
is a measured, smooth narrowing horn. [Fourcade 2015; Le Cleac'h ETF 2010; Sheerin FEA]

Joseph Crowe's ES-600 is described as an "exponential spiral" with a 270-degree wrap, golden-ratio
proportions (417 x 203 x 198 mm) and a 1.4-inch throat. Crowe claims the wrap reduces edge
diffraction and mouth resonance; no independent measured or BEM comparison of 90, 130, 180 and
270-degree wraps was found in this research pass, so treat the exact wrap angle as unproven. What
is grounded is the general rule: terminate the profile smoothly instead of cutting it at a sharp
edge. A 90-130-degree roll already does most of that; 270 degrees is plausible and visually
distinctive, but not demonstrated to be better. His own measurement report on the ES-600
with a Faital HF1460 shows 0/15-degree curves nearly identical, 30-degree down 2-3 dB, 45-degree
down 4-10 dB above 2 kHz, a 6 dB/octave treble fall from 5-10 kHz and a 12 dB/octave fall above
10 kHz, plus a 12.6 kHz driver breakup. He also says the ES-600 needs a passive crossover to damp
resonances near 1 kHz and cannot be used active without compromise. His ES-290 polar post claims
near-CD behavior from 500 Hz to 7 kHz and narrowing to about 50 degrees above 10 kHz. There is no
independent third-party polar/DI data for the ES family in the sources we could reach. [Crowe,
ES-600 page and HF1460 measurement report; ES-290 post]

**Implication for us:** the ES/Crowe family narrows by design. A 2-3 dB/octave smooth rise is
acceptable in a DSP home system if it is monotonic, continuous at the 700 Hz crossover, keeps a
reasonable coverage floor through the presence band, and has no in-band resonance. Crowe's own
1 kHz resonance warning shows that a narrowing horn can still fail on coloration. The faithful ES
shape is a legitimate research path, not a guaranteed good-sound answer.

### What the analysis literature says about how to design and judge these

- **BEM mesh:** 6 elements per wavelength is a screening mesh (roughly 10% frequency error);
  verification/final should use 8-12, with a convergence check on one finalist. A uniform-velocity
  throat cap is acceptable for pattern work but not for level/loading above the throat's first
  cross-mode (about 5.6 kHz for a 1.4-inch driver). [Kolbrek BEM notes; Boundary Lab solver report;
  COMSOL horn optimization]
- **What to score:** balloon DI and full polars, listening-window/PIR smoothness, beamwidth in H,
  V and diagonal, throat loading `Re Z`, and crossover DI continuity. On-axis-only optimization is
  explicitly pathological: COMSOL's horn-shape example shows an on-axis optimum can create deep
  off-axis minima. [COMSOL; CTA-2034; Olive 2004; repo `hifi_rescore`]
- **Optimization:** CMA-ES is a solid baseline at this budget; Bayesian optimization/TuRBO is
  competitive and more sample-efficient on expensive BEM. Keep 2-3 objectives, treat refusals as
  constraints, and verify the top finalists on the dense grid. [Hansen CMA-ES tutorial; TuRBO;
  Smolen & Halley 2021; repo search dossier]
- **Measurement:** a printed waveguide can show 1-4 kHz artifacts from secondary transmission
  paths; a sand layer fixes the measurement, not the horn. Baffle-edge diffraction and mic-boom
  reflections corrupt wide-angle data. The driver exit also limits HF directivity (about 8-9 kHz
  for a 1.4-inch driver). [JASA 2025 sand-layer paper; MTG waveguide shootout]
- **Preference:** Olive's 2004 model uses narrow-band on-axis and PIR deviation, bass extension
  and PIR smoothness; it has **no DI-slope term**. The claim that "Harman prefers 1-3 dB/octave DI
  slope" did not survive a source check in this session; do not present it as a published result.
  [Olive 2004; our source check]

### Best-practice checklist from the sources

This is the checklist the external research supports, in plain language:

1. **Size the mouth to the crossover.** Use Keele's `W = 25,000/(0.9 x coverage x f)` or the
   wavelength rule. For 80 x 50 at 700 Hz: 496 mm H (fits your 600 mm box; 80 degrees down to
   ~579 Hz) and 794 mm V (does not fit; 50 degrees only down to ~1157 Hz, so the vertical will be
   wider than target at 700 Hz). Accept the vertical limit; do not pretend a 480 mm height can
   hold 50 degrees at 700 Hz. [US4308932A; Geddes]
2. **Keep the wall continuous in slope and curvature.** No slots, steps or sharp creases that
   survive into the mouth. The OS/OSSE family is the minimum-HOM smooth contour; the Keele
   tri-section is a historical hybrid. [Geddes; ATH OS-SE/R-OSSE]
3. **Match the throat to the driver.** 36 mm diameter, about 2 degrees for the HF1440; keep it
   round; an extended throat/ring insert can add LF resistance without changing directivity.
   [ATH R-OSSE; EXAR story; Geddes]
4. **Use a real lip radius.** Geddes' quarter-wave rule: 35 mm is clean above ~2.46 kHz, 50 mm
   above ~1.72 kHz, 86 mm above ~1 kHz. A 40-50 mm lip is the rational hi-fi choice. A 270-degree
   wrap is visually distinctive but not proven better than 90-130 degrees. [Geddes; ATH roundover
   study; Crowe claim]
5. **Keep the baffle small and round its edges.** ATH's simulations use a 35 mm enclosure-edge
   radius; a large flat flange behind the mouth causes diffraction. [ATH TwinRay/Tritonia]
6. **Judge the full polar map, including the diagonal.** Require no midrange narrowing, no pattern
   flip, and a smooth/gentle DI change. A rectangular or creased mouth needs the diagonal checked,
   not just H and V. [ATH; Geddes; our `diag` term]
7. **Cross-check BEM against measurement.** BEM uses an ideal source cap and no driver; absolute
   level, loading and HOM are not predicted. Screen at 6 elements/wavelength, verify at 8-12, and
   measure a prototype before calling a winner. [Kolbrek; ATH; Boundary Lab solver report]
8. **Do not use the K-law as a directivity predictor.** It is an empirical mouth-sizing rule; the
   actual polar comes from the throat angle, mouth shape and termination. [US4308932A]

---

## 3. What our own checks say so far (facts, not opinions)

| Seed | Box check | Solves | Notes |
|---|---|---|---|
| Ext-throat CD | existing | 330 rows in the family | the current best-scoring family (base J ~2.6, smooth ~2.8); the sound reference, not a look candidate |
| R-OSSE rect | 64/64 random samples mesh, fit, round throat | none | seed 560 x 360 x 186 mm; mid-roll/mid-exponent is the clean-rim region |
| Crowe-X | 58/64 (6 over the 600 mm envelope) | none | seed 588 x 398 x 244 mm; 5/10 sampled box extremes exceed 600 mm |
| Crowe ES sections | 62/64 preflight; night E running | 96 valid rows for seed 1234 | best so far 579.7 x 292.9 x 262.1 mm, crown 39.7; smooth rescore J 6.84 vs base 16.92. **Mesh defect found:** a 153-176 deg fold at the side-wall/lip junction with inverted triangles (objective dihedral check). The inner flare is smooth; the fold is on the outer-body junction. Treat the scores as provisional and fix the junction before printing. |
| ES spiral | 62/64; 9 corners mesh/fit | none | seed 542 x 299 x 242 mm; the log-spiral wall returns as a thin hook in the render |
| Biradial | 64/64 random samples mesh, fit, round throat (after the fix) | none | seed 560 x 350 x 258 mm; no law waist/lip term |

The Crowe-section smooth rescore is the most informative number: its remaining weighted penalty
is dominated by `diag` (2.94 of 6.84). Without the diagonal term it would be about 3.9, close to
the CD families. That does not prove the horn is good; it shows that the diagonal question is now
the main thing standing between the Crowe sections and a competitive score. The `diag` term
compares the 45-degree beam to a fixed round reference (65 degrees for an 80 x 50 target), so a
rectangular or creased mouth is penalized for being rectangular. We should report it separately
and decide whether it belongs in the final ranking after we have measured/simulated diagonal
polars. [repo rescore; `scalar_v4._diag_term`]

**New defect finding (objective mesh check, 2026-11-15).** The Crowe-section family has a real
153-176 degree fold at the side-wall/lip junction, with inverted triangles; the section plot shows
the inner flare itself is smooth, so the fold is on the outer-body junction rather than the
acoustic bore. The other cells have no edge above 150 degrees (Crowe-X max ~99, ES spiral ~119,
R-OSSE rect ~95, ext-throat ~106, biradial ~136). This is not a shading artefact. It is a
print/visual defect and may affect outer-shell scattering; treat the current night E scores as
provisional and rebuild the junction (enforce consistent winding, fillet the side-wall-to-flare
transition) before using the family for the final horn.

---

## 4. The trade-off

- **Sound-first:** the R-OSSE rounded rectangle is the safest 700 Hz home horn. It is a modern CD
  profile, it has a landscape mouth, and the published ATH evidence supports the family. It does
  not have Crowe's X/waist.
- **Look-first:** the Crowe ES sections and the Crowe-X are the two shapes that carry Crowe's
  visual language. The ES sections are the closest to his actual construction and already have
  data, but their current mesh has the outer-body fold described above; fix that before trusting
  the scores. The Crowe-X is the closest to his front-view crease pattern, but its lip is a thin
  flange in our current geometry, not a thick roll.
- **The gap:** neither Crowe-style cell has a real under-surface lip return yet. The law can make a
  rolled edge, but not the 270-degree bead Crowe shows. If the thick bead is the part you care
  about most, the honest next step is a lip geometry change, not more CMA on the same knobs.
- **What a GPU night can tell us:** whether the search can find a coherent Crowe-X or ES shape that
  also scores well on coverage, loading, flatness and smoothness. It cannot tell us how it sounds
  in your room, and it cannot validate the Crowe likeness; that is your eyes and, later, a
  prototype measurement.

---

## 5. Options for night F (after night E ends, ~02:00-03:00)

| Option | What runs | GPU cost | What it buys | Risk |
|---|---|---|---|---|
| **A. Balanced (recommended)** | one look candidate of your choice (Crowe-X **or** ES spiral) 1 seed + R-OSSE rect 1 seed, all on the smooth brief; Crowe sections already running in E (scores provisional until the fold is fixed); cut biradial | ~3-4 h | one look-first and one sound-first candidate, plus provisional Crowe data from E | the chosen look cell still has the law's lip limitation; R-OSSE rect may be judged too plain; the Crowe-section fold needs a fix |
| **B. Look-first** | Crowe-X 1 seed + ES spiral 1 seed, smooth brief; cut biradial and R-OSSE rect | ~4-5 h | maximum look exploration; the two most Crowe-like shape languages | no sound-first fallback if both disappoint; ES roll is thin |
| **C. Sound-first** | R-OSSE rect 2 seeds + keep ext-throat data; Crowe sections already running; no new look cells | ~2-3 h | the best chance of a good-sounding 700 Hz horn in this box | may not satisfy the Crowe look |
| **D. Pause and fix the lip/waist law** | no new GPU; add a real lip return (and decide whether a waist term is wanted), test/render, then run | 0 h GPU now | highest chance of a true Crowe bead; avoids more data on a shape we know is limited | no new acoustic data tonight; code/test time |

**My recommendation: option A.** It keeps the faithful Crowe sections (already paid for in night
E), adds one look candidate of your choice, and adds one R-OSSE seed as the sound-first
alternative. It cuts the biradial (classic but not Crowe, and the law has no waist/lip). Which look
candidate to run is your call after looking at the turntables:

- **Crowe-X** if you prefer the front-view X/bow-tie and are willing to accept that its current
  lip is a thin flange, and that the creases need a diagonal-polar check.
- **ES spiral** if you prefer the smoother Crowe-style flare and a real (if thin) roll, and are
  willing to accept that it narrows with frequency by design.

Use one brief for all cells (the smooth brief) so the comparison is apples-to-apples; re-score
everything under the base brief and the `hifi_rescore` listening terms afterward. Report `diag`
separately and do not let it decide the winner until we have diagonal polars.

If you want the most authentic Crowe shape even at the cost of sound, choose B. If you want the
best chance of a good-sounding horn and are willing to give up the X, choose C. If the thick bead
is non-negotiable, choose D; more GPU on the current lip geometry will not produce it.

---

## 6. What would change this recommendation

1. **Your look judgment.** Open the six turntables. If the Crowe-X or ES is not close enough, do
   not spend GPU on it; choose C or D. If the R-OSSE rectangle is too plain, choose A or B.
2. **A measured/simulated diagonal polar.** If the Crowe-X creases produce a clean diagonal that
   sits between H and V, the `diag` penalty is unfair and the Crowe cells deserve more budget. If
   the creases produce a lobe or a null, the penalty is real and the X is a bad acoustic choice.
3. **Loading at 700 Hz.** The current scores can reward a horn that is not actually loaded at the
   crossover. A built prototype's `Re Z`/LFP20 measurement would settle it.
4. **The lip.** If a real rolled lip is added and the ES/Crowe cells still score competitively,
   the look-first path becomes much stronger.
5. **Your room/crossover.** The final choice depends on the woofer's directivity at 700 Hz and the
   room; the search cannot see either.

---

## 7. What the knobs do (the search ranges, in plain language)

The search does not know what a "lip" or a "waist" is. It only knows a vector of numbers inside
the ranges below, and it is told to make the score smaller. If a knob changes the drawing but not
the sound, the search may still move it because the score includes shape/visual proxies; that is
budget spent on cosmetics. The tables below say which is which.

### 7.1 Keele Bi-Radial (`hl__biradial_es_style_v7`)

| Knob | Range | What it changes in the geometry | What it does to the sound / score |
|---|---|---|---|
| `L_mm` | 220-320 | axial depth | deeper = more gradual flare and more loading, but the K-law closure limits how deep the mouth can be for a given angle |
| `h_a_deg` | 32-37 | horizontal initial wall angle | sets the HF horizontal coverage (about `a/0.9`); higher = wider H beam |
| `v_a_deg` | 18-24 | vertical initial wall angle | sets the HF vertical coverage; higher = wider V beam |
| `h_rm_mm` | 260-292 | horizontal mouth half-width | mouth width and low-frequency H pattern control; bigger = control lower |
| `v_rm_mm` | 162-230 | vertical mouth half-height | mouth height and low-frequency V pattern control; bigger = control lower |
| `h_n`, `v_n` | 3-7 | flare exponent | higher = more of the flare packed near the mouth (slower initial, faster final); changes midband/HF beam and loading |
| `mouth_exponent` | 2.2-5 | superellipse corner squareness | higher = squarer mouth; mostly visual, can change the diagonal |
| throat blends | 25 fixed | round-to-contour transition at the throat | acoustically important (round throat, no kink); fixed because the fix is now correct |
| `max_wall_deg` | 80 fixed | safety limit on wall angle | not acoustic; prevents over-vertical walls |

The law has **no waist term and no lip return**. It can make a clean two-plane Bi-Radial; it
cannot make Crowe's bow-tie lip or a 270-degree bead.

### 7.2 R-OSSE rounded rectangle (`hl__rosse_rect_cd_v7`)

| Knob | Range | What it changes in the geometry | What it does to the sound / score |
|---|---|---|---|
| `g_width_mm` | 480-590 | mouth width | low-frequency H pattern control; bigger = control lower |
| `g_height_mm` | 280-420 | mouth height | low-frequency V pattern control; bigger = control lower |
| `g_rect_exponent` | 2.5-8 | corner squareness of the rounded rectangle | higher = sharper corners; visual, and a sharper corner can change the diagonal |
| `g_a_h_deg` | 32-46 | horizontal coverage half-angle | HF H beamwidth; higher = wider |
| `g_a_v_deg` | 18-30 | vertical coverage half-angle | HF V beamwidth; higher = wider |
| `g_k` | 0.8-3 | throat expansion | ATH: `k` sets the DI slope and throat loading; higher = faster throat expansion |
| `g_r` | 0.25-0.6 | rollback radius | how tight the mouth roll is; affects mouth termination/diffraction |
| `g_b` | 0-0.4 | roll bend / curvature decay | how quickly the roll develops |
| `g_tmax` | 0.85-1 | how far the roll runs | end of the profile; affects the mouth termination |
| `g_a_diag_deg` | 0 fixed | diagonal angle | must stay 0: a nonzero value fans creases out of the throat, which is not the Crowe X |
| `g_m`, `g_q` | 0.85, 3 fixed | profile constants | ATH-typical; not searched |

Depth is **not** a knob here; it follows from the coverage, mouth size and roll. The seed is
560 x 360 x 186 mm, which is shallow; a deeper seed (around 220 mm) is a better starting point for
the sound, and a mid roll/exponent is the clean-rim region.

### 7.3 Crowe-X on a CD throat (`hl__crowe_x_osse_cd_v7`)

| Knob | Range | What it changes in the geometry | What it does to the sound / score |
|---|---|---|---|
| `g_a_h_deg` | 33-40 | horizontal coverage half-angle | HF H beamwidth |
| `g_a_v_deg` | 20-28 | vertical coverage half-angle | HF V beamwidth |
| `g_L_mm` | 200-260 | depth | longer = more gradual flare and a longer roll |
| `g_s` | 0.2-0.45 | OSSE termination flare | higher = stronger outward curve near the mouth; too high overshoots the 600 mm width |
| `g_n` | 1.8-3.2 | termination exponent | high = flare packed into the last ~20 mm (flat-plate side); low = bowl |
| `g_r_lip_mm` | 8-30 | lip radius | thicker roll; too high overshoots the width |
| `g_wrap_deg` | 80-160 | how far the lip curls | more wrap; the current render is still a flange, not an under-surface bead |
| `g_sf_ab` | 0.7-0.9 | superformula stretch | lower = wider mouth |
| `g_sf_amt` | 0.15-0.38 | X/crease strength | higher = stronger creases and waist; can over-pinch and make the rim wavy |
| `g_sf_m`, `g_sf_n1`, `g_sf_n2`, `g_sf_start` | 4, 1.8, 7, 0.25 fixed | four corners, corner sharpness, edge straightness, where the X starts | the Crowe-like crease language; fixed to keep the look |
| `g_k`, `g_q` | 1, 0.996 fixed | OSSE constants | not searched |

**The lip is the limitation.** The current OSSE lip term curls the wall but does not return under
the mouth, so no setting in this table produces Crowe's thick bead. More search here can make a
better flange, not a bead.

### 7.4 ES exponential spiral (`hl__rolled_es_spiral_v7`)

| Knob | Range | What it changes in the geometry | What it does to the sound / score |
|---|---|---|---|
| `g_width_mm` | 480-590 | mouth width | LF H control; bigger = lower |
| `g_height_mm` | 260-420 | mouth height | LF V control; bigger = lower |
| `g_depth_mm` | 200-380 | depth | longer = more spiral turns / more roll |
| `g_depth_h_ratio` | 0.55-1.0 | H/V depth split | how far the top/bottom lips project forward of the sides; the ES look, and a possible asymmetry |
| `g_decay` | 0.4-1.0 | log-spiral decay (flare rate) | higher = faster outward growth per turn; changes the flare and the roll |
| `g_rect_exponent` | 4-14 | corner squareness | more rectangular mouth; visual and diagonal |
| `g_rect_turn_deg` | 45-85 | where the round-to-rectangle transition starts | shape; too early can make the mouth lumpy |
| `g_terminal_deg` | 200-275 | how far the wall wraps | more roll; the render's roll is thin/hooked, not a bead |
| `g_pucker_h_mm`, `g_pucker_v_mm` | 0-18, 0-24 | local mouth relief/creases | more X/pucker; high values add rim ripples |
| `g_throat_turn_deg`, `g_pucker_start_deg` | 25, 55 fixed | throat turn and where the pucker starts | not searched |

The wall leaves the throat **axially** and keeps turning, so the beam narrows with frequency; `decay`,
`rect_turn` and `terminal` change the drawing/roll more than the coverage. That is why this cell is
scored on the smooth brief, and why its low-frequency pattern control is limited by the mouth size.

### 7.5 Crowe ES-600 sections (`hl__crowe_panel_home_v7`)

| Knob | Range | What it changes in the geometry | What it does to the sound / score |
|---|---|---|---|
| `g_width_mm` | 480-590 | mouth width | LF H control |
| `g_height_mm` | 220-420 | mouth height | LF V control |
| `g_depth_mm` | 170-300 | depth | flare rate; the swept-H construction needs depth <= ~0.57 x width |
| `g_h_depth_scale` | 0.9-1.1 | H/V depth ratio | top/bottom vs side depth; shape/asymmetry |
| `g_crown_mm` | 10-40 | top/bottom panel crown | more curved panels; the best night-E design went to the top of this range |
| `g_junction_power` | 16-48 | corner junction sharpness | shape; can create hard corners/folds |
| `g_throat_blend_mm` | 20 fixed | round throat transition | acoustically important |
| section profiles | fixed | digitized Crowe H/V meridians | the actual Crowe construction; not searched |

The current construction has a **153-176 degree fold** at the outer side-wall/lip junction (inner
flare smooth). That is a geometry bug, not a knob setting; fix the junction before more runs.

### 7.6 What the search is actually doing

CMA-ES samples numbers inside these ranges, starting at the seed with a step of about 20% of each
range, and tries 96 candidates per seed. It gets a score from the chosen brief. It does not know
which numbers are acoustic and which are cosmetic. So the design of the ranges and the brief
matters as much as the optimizer:

- If a range includes a geometry the law cannot build, the candidate is refused (or penalized);
  the box checks above are there to keep that fraction low.
- If a knob only changes the drawing, the search may still move it because the score has shape
  proxies (coverage, diagonal, ripple); that is wasted budget.
- If the brief rewards the wrong thing (for example, a flat DI target on a horn that narrows
  smoothly by design), the search will chase the wrong shape. That is why the brief/DI-slope
  investigation is now the top priority, ahead of any new solves.

## 8. Sources (external, with confidence)

| Source | What it supports | Confidence |
|---|---|---|
| Keele, US4071112 (EV CD horn, 1975) | exponential throat + conical midsection + bell; cone half-angle sets HF beamwidth | primary patent |
| Keele, US4308932A (JBL Bi-Radial, 1980) | power-series wall law, K-law mouth size, A=0.9B throat angle, gap slot | primary patent |
| Keele, AES 1038 (1975) / AES 933 (1973) | exponential HF horns cannot hold CD; optimum mouth size minimises mouth reflection (not "bigger is better") | primary abstracts |
| JBL 2380A data sheet | 90 x 40; H held 500 Hz-16 kHz; V CD only above ~2 kHz | manufacturer data |
| Geddes, "What is a Waveguide?", "Sound Quality Improvements...", "Loudspeaker System Design Philosophy", US7068805 | OS/catenoid waveguide, minimum HOM, gradual throat, mouth radius >= lambda/4, small rounded baffle | primary/secondary |
| ATH / Batik: R-OSSE, Tritonia, twinray roundover BEM, EXAR story | modern CD profile; 35 mm roundover recommendation; throat diameter sets HF limit | author/measurement pages |
| Fourcade, *Calcul du Pavillon Le Cleac'h* (2015); Le Cleac'h ETF 2010 | exact JMLC equations; T-family; rollback | primary/secondary |
| Sheerin, Le Cleac'h vs conical FEA | LC DI ~4 dB at 1.4 kHz to ~12 dB at 12 kHz (≈2.6 dB/oct), smooth off-axis, clean decay | strong secondary |
| Crowe, ES-600 page / HF1460 measurement report / ES-290 post | ES flare, 270-degree wrap, 417 x 203 x 198 mm, measured narrowing and 1 kHz resonance caveat | author-measured; no third party |
| Kolbrek, *Horn Theory: An Introduction*; BEM notes | exponential vs conical loading; BEM mesh/far-field practices | strong secondary |
| COMSOL, *Optimizing the Shape of a Horn* | on-axis optimum can create deep off-axis minima; mesh from f_max | primary application note |
| Smolen & Halley, JAES 2021 | parametric CAD -> FEM+BEM -> objective optimization -> measured validation | primary abstract |
| Sridhar, Tylka, Choueiri, JAES 2019 | generalized constant-directivity metrics; no established measure | primary abstract |
| TuRBO (Eriksson et al., 2019); Hansen CMA-ES tutorial | sample-efficient BO; CMA-ES defaults | primary |
| JASA 2025 sand-layer paper | 3D-printed waveguide secondary-path artifacts at 1-4 kHz | primary abstract |
| Olive 2004; Toole/Olive; CTA-2034 | preference model; PIR definition; smoothness over fixed slope | formula verified in repo; primaries paywalled |

The "Harman prefers 1-3 dB/octave DI slope" claim did **not** survive this source check: no primary
or strong secondary source was found, and Olive's model has no DI-slope term. Treat a smooth
2-3 dB/octave rise as acceptable under the conditions above, not as a published target.
