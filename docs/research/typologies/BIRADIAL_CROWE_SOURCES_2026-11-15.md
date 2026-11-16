<!-- Copied 2026-11-15 from a Sonnet research subagent (study BIRADIAL_CROWE_STUDY_2026-11-15.md). CORRECTIONS
     (second research pass, 2026-11-15 17:xx; these supersede the body where they conflict):
     (1) K-LAW DENOMINATOR IS A = 0.9*B, not B. At 700 Hz, 80 deg H needs 25,000/(0.9*80*700) = 496 mm (body says
         446 mm), and 50 deg V needs 25,000/(0.9*50*700) = 794 mm (body says 714 mm). Our 600 mm H holds 80 deg down
         to ~579 Hz; our 480 mm V holds 50 deg only down to ~1157 Hz, so at 700 Hz the vertical can support only ~83
         deg. The body's 446/714/223/240 numbers are superseded.
     (2) "Cone half-angle sets HF beamwidth" is a sound inference from US4071112 (the cone is a pulsating-sphere
         segment; the bell only fixes midrange narrowing), but the patent does NOT state an angle law.
     (3) The 55/r Hz roundover rule is NOT sourced. Geddes' verified rule is radius >= lambda/4: r=35 mm is clean
         above ~2.46 kHz, 50 mm above ~1.72 kHz, 86 mm above ~1 kHz. Use 40-50 mm as the rational hi-fi lip.
     (4) The 270-deg-wrap superiority and the 180-deg cavity-resonance claim are UNVERIFIED. No measured or BEM
         comparison of 90/130/180/270 deg was found. "Terminate the profile smoothly" is grounded; the exact wrap
         ranking is not. 270 deg is plausible-plus-cosmetic, not demonstrated.
     (5) The waisted/bow-tie outline has NO acoustic source; ATH's morph target is a convex rounded rectangle.
         Corner X creases are a curvature discontinuity (HOM/diffraction risk per Geddes) AND partly a morph
         consequence (ATH says the morph adds a shifted diagonal). Treat them as visual until diagonal polars exist.
     (6) The osse_rollback knob table below quotes a_h 22-26 / a_v 13-16 deg "for 80x50" from the fork handoff
         z-round seeds; that is WRONG (~48 x 28 deg at HF). Use ~36-42 / 22-28 (Keele 0.9 x half-coverage).
     Numbers marked "model-extracted summary" for the Crowe HF1460 report are lower confidence. -->
# Research: Biradial CD horn design, Crowe ES-style horns, and mouth rollover

Date: 2026-11-15. Labels: [verified] = read this session in a primary source; [measured] = derived arithmetic; [inferred] = our derivation from fetched material; [unverified] = single unconfirmed report or model knowledge only; [repo] = established in the cited repo doc.

---

## Source table

| Source | What it gives | Status |
|---|---|---|
| US4071112, D.B. Keele Jr., assignee Electro-Voice Inc., filed 1975-09-30 | Keele CD horn: three-section exponential+conical+bell; continuity rule; HF beamwidth knob | [verified] fetched 2026-11-15 |
| US4308932A, D.B. Keele Jr., assignee JBL, filed 1980-05-06 | JBL Bi-Radial: power-series contour, K-law, 0.9×B rule, gap | [repo] BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md |
| dbkeele.com / AES Paper 1038, Keele 1975 | CD horn abstract; full formulas behind AES paywall | [verified abstract]; AES e-lib blocks automated fetch |
| josephcrowe.com/blogs/news/es-600-biradial-horn | ES-600 design description, 270° wrap, ES flare, passive XO necessity | [verified] fetched 2026-11-15 |
| josephcrowe.com/blogs/news/faital-hf1460-compression-driver-es-600-biradial-measurement-report | Faital HF1460 on ES-600: IMD numbers, breakup at 12.6 kHz, polars to 16 kHz | [verified] fetched 2026-11-15; numerics from model-extracted summary (lower confidence) |
| josephcrowe.com/blogs/news/es-290-biradial-polar-off-axis | ES-290 measured directivity | [repo] BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md §11; refetched 2026-11-15 |
| at-horns.eu/tritonia.html | Tritonia coverage formula, mouth termination, baffle guidance | [verified] fetched 2026-11-15 |
| at-horns.eu/img/twinray/bem/roundover-study.html | BEM polar maps for 8.75/17.5/35 mm fillets and 35 mm chamfer | [verified] fetched 2026-11-15; graphical only, no formula |
| at-horns.eu/exar-story.html | OS-SE beaming mechanism: throat diameter determines HF limit | [verified] fetched 2026-11-15 |
| docs/research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md | JBL Bi-Radial construction (US4308932A); Crowe §11; Iwata R9 stop | [repo] |
| docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md | JMLC exact construction (Fourcade 2015); T parameter | [repo] |
| docs/research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md | Original log-spiral analogue construction; source table corrections | [repo] |
| docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md | H/V cos(4ψ) pucker on section family | [repo] |
| docs/research/CROWE_X_HORN_HANDOFF_2026-11-15.md | osse_rollback generator knobs; x/y/z round results | [repo] |
| Geddes, gedlee.com | Mouth diffraction; second-derivative rule; waveguide chapter | gedlee.com has permanent SSL error; not fetched |

---

## 1. Keele biradial / constant-directivity design law

### 1a. Keele CD horn (US4071112, 1975 — the EV HR series ancestor)

Three-section channel structure [verified, US4071112]:

1. **Exponential throat section**: cross-sectional area increases exponentially with axial distance. Purpose: low-frequency loading efficiency. Wall is convex and transitions smoothly into the conical section.

2. **Conical midsection**: cross-sectional axes increase *linearly* with axial distance (area ∝ distance²). This is the constant-directivity section. At frequencies where the wavelength is small relative to the cone, the horn radiates as a spherical segment and maintains constant beamwidth. This is **the section whose half-angle sets the HF beamwidth** [verified].

3. **Bell section**: axes increase at twice the rate of the conical section (area rate 4× the cone). Bell length = approximately half the cone length. Suppresses midrange narrowing artifact only; does not change the HF angle [verified].

**Continuity requirement** at the exponential/conical junction: wall slope must match exactly (rate of axis increase must equal the cone rate throughout the cone). This eliminates the kink-reflections that plague pure exponential horns [verified].

**Cross-section**: rectangular in the commercial embodiment. This decouples H and V coverage angles independently [verified].

**Demonstrated performance**: constant beamwidth from ~500 Hz to ~20 kHz. The mid-range collapse (40–50% of HF beamwidth) seen in radial/sectoral horns is absent [verified].

**The specific knob controlling HF beamwidth**: the **half-angle of the conical section** (= the throat angle at the exponential/conical junction). At HF the horn is acoustically a solid angle, so coverage = 2 × cone half-angle [verified, inferred from US4071112].

**The 0.9×B rule and K-law** (from US4308932A, not US4071112):
- Throat angle A = 0.9 × B (half-coverage angle B). "Empirically determined to be on the order of ninety percent of beamwidth" [verified, US4308932A; repo].
- Mouth dimension W = K / (A × F), K ≈ 25,000 m-deg-Hz [verified, US4308932A; repo].
- For our target: H = 80°, F = 700 Hz: W_H = 25,000 / (0.9 × 80 × 700) = 0.496 m = 496 mm. V = 50°, F = 700 Hz: W_V = 25,000 / (0.9 × 50 × 700) = 794 mm. **Note:** the K-law gives the size needed for pattern control at F; for our 600 × 480 mm envelope at 700 Hz, the H mouth is feasible (80° down to ~579 Hz) but V is over-constrained (50° only down to ~1157 Hz; at 700 Hz the vertical supports ~83°) — the owner brief accepts 40–60° V partly for this reason [measured; inferred].

### 1b. JBL Bi-Radial (US4308932A, 1980) — established in repo [repo]

Already fully covered in `BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md`. Key facts for this study:

- Two wall pairs at 90°; power-series contour y = a + bx + cx^n; H pair is a surface of revolution.
- Reference case: 80° H × 36° V, 780 × 780 mm mouth, L = 815 mm, 48.8 mm throat, 18 mm gap at x = 516 mm.
- Flare exponents: H preferred n = 5.5, V preferred n = 4.0 (range 2–8 per claim 14).
- For 1.4" driver (r₀ = 18 mm) at 700 Hz with our targets, K-law gives: H throat angle = 0.9 × 40° = 36°, mouth half-width ≈ 248 mm, total W = 496 mm [measured].

### 1c. Round-throat transition — the "throat region" problem for our cells

The Keele Bi-Radial uses an **exponential connector** from the round throat to the gap (a slot). For a round 36 mm exit:
- The gap at x_gap must have area ≥ throat area (monotone divergence). For gap width w_g ~ 0.37 × 36 mm = 13 mm, the gap height must exceed throat area / 13 = π×18² / 13 ≈ 78 mm [measured, inferred from US4308932A proportions].
- Our current cells use OS-SE or OSSE marches that maintain a smoothly expanding round cross-section, then morph to rectangular. This is acoustically cleaner than the Keele gap (no high-aspect slot) but does not reproduce the Bi-Radial's separate-pair geometry [repo; inferred].
- The repo's current DI rise of 2→16 dB over band [user-stated] is likely dominated by **wall angle too shallow at HF** (insufficient cone half-angle) or **mouth too small relative to K-law requirement** at 700 Hz [inferred from US4071112 §1a above].

---

## 2. Joseph Crowe ES-style horns

### 2a. ES flare — what "Exponential Spiral" means

Crowe states the height and width "adhere to the golden ratio" and explicitly links this to the Exponential Spiral (= logarithmic spiral) geometry [verified, josephcrowe.com/blogs/news/es-600-biradial-horn]. No explicit parametric equation is published. His planned white paper has not appeared as of 2026-11.

A logarithmic spiral in polar coordinates: r = r₀ · e^(bθ). In a cross-section of a horn, the wall curve r(z) that traces a log-spiral as a function of arc angle is **equivalent to a wall that expands exponentially per unit of turn angle**, not per unit of axial length. This would produce a continuously curving wall that spirals outward and can roll past 90°, 180°, 270° naturally — consistent with the cross-section shown in `scratch/crowe_ref/es600_Section.JPG` [inferred from "ES = Exponential Spiral" + images + repo].

The repo's logarithmic-spiral analogue construction in `ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md` (using `dz/dt = exp(-bt)cos(t)`, `du/dt = exp(-bt)sin(t)`) is therefore a reasonable architectural approximation, correctly labeled "our construction, not Crowe's equation" [repo].

### 2b. Measured performance

**ES-600 with Faital HF1460** (from josephcrowe.com measurement report, confirmed verbatim intro + model-extracted summary; lower-confidence numerics):
- Off-axis angles tested: 0°, 15°, 30°, 45°.
- 0°/15° nearly identical, 30° only slightly down, 45° increasingly off at higher frequencies.
- Very low distortion: SMPTE IMD 1.64% at 95 dB SPL (vs. TAD TD-2002 at 3.08%, B&C DCM50 at 1.89%) [lower confidence — from summary portion].
- 2nd and 3rd harmonic distortion <0.1% through passband [lower confidence].
- Breakup noted at ~12.6 kHz (a Faital HF1460 driver characteristic) [lower confidence].
- Polars described as "very well behaved to 16 kHz" [qualitative, lower confidence].

**ES-1200** (from josephcrowe.com/blogs/news/es-1200-biradial-wood-horn, model-extracted summary):
- Horizontal coverage described as "basically perfect" (qualitative).
- Vertical: "a few small irregularities around 17 kHz" — otherwise very good.

**ES-290** (from josephcrowe.com/blogs/news/es-290-biradial-polar-off-axis, [repo]):
- Near-constant directivity 500 Hz–7 kHz.
- 90° window maintained 300 Hz–7 kHz.
- Narrows to ~50° above 10 kHz (partly attributed to driver breakup above 7 kHz).
- Sensitivity gain vs. unhorned: +10 dB at 400–800 Hz, +7 dB at 1.6 kHz, +5 dB at 3 kHz.

**Passive crossover claim** [verified, josephcrowe.com]: Crowe states the ES-600 "cannot be used in active systems without acoustic compromises"; a custom passive XO is essential. This is an admission that there are resonances (described elsewhere as near 1 kHz) that the passive network manages [primary author claim; not independently verified].

**Honk/coloration**: No independent user measurement found. Crowe's own framing is that the 270° wrap eliminates most coloration; his own listening reports are uniformly positive. The passive XO requirement is the only published evidence of a problematic resonance (1 kHz region) in the design [inferred from XO claim].

**Users**: Crowe's listed compatible drivers include RCF ND-850, Faital HF1460, TAD TD-2001, B&C DCX-464-16, RCF ND-940, Eminence N314X. All are 1.4" drivers. The Faital HF1440 (our driver) is not listed but is the same 1.4" family [inferred].

---

## 3. Mouth roundover / rollback acoustics

### 3a. What lip radius does acoustically

**Rule of thumb** (from general diffraction theory; *not* found in a fetched primary source; label [inferred from acoustics fundamentals]):
- A sharp edge (r ≈ 0) acts as a secondary source (Huygens) with a time delay ∝ path difference. The result is a comb filter in the radiated field.
- For a rounded edge of radius r, edge diffraction is suppressed when kr >> 1, i.e., when 2πf·r/c >> 1.
- The transition frequency is approximately f_transition ≈ c / (2π·r) = 55/r (SI).
- For r = 35 mm: f_transition ≈ 55/0.035 ≈ 1,570 Hz. Roundover helps above ~1.5 kHz.
- For r = 20 mm: f_transition ≈ 55/0.020 ≈ 2,750 Hz. Only helps above ~2.7 kHz.
- For r = 50 mm: f_transition ≈ 55/0.050 ≈ 1,100 Hz. Already helping at ~1.1 kHz.
- **For our band (700–10,000 Hz), a 35–50 mm radius lip roundover is acoustically meaningful across most of the band. A 20 mm radius matters only above ~2.7 kHz. Below 1 kHz even a 50 mm roundover is acoustically small.** [inferred; no primary numeric source reached]

**BEM study at at-horns.eu** [verified, graphical only]: compared r = 8.75, 17.5, 35 mm and a 35 mm chamfer for the HF-25-10-266 waveguide. The 35 mm radius was recommended. No text formula. The study is at https://at-horns.eu/img/twinray/bem/roundover-study.html and is graphical/image-only.

**Baffle recommendation from Tritonia** [verified, at-horns.eu/tritonia.html]: "make the front baffle around the waveguide as small as possible and round the edges generously." Free-standing (no baffle) suffers somewhat.

### 3b. Wrap angle: 90° vs 180° vs 270°

**What Crowe claims** [verified, josephcrowe.com]: the 270° wrap "reduces edge diffraction off the horn mouth and minimizes acoustical resonance to very low levels." He calls it "a first for any biradial."

**Le Cleac'h rollback**: the JMLC construction with stop angle > 180° produces a wall that curls back inward (rollback). The repo's `lecleach_rollback.yaml` uses stop angles in this range. The acoustic mechanism: by turning the mouth lip back, the outer edge of the wavefront is redirected inward; this increases the apparent effective mouth area seen by the room (the radiating aperture is bounded by the outer lip, not the inner edge), potentially reducing edge diffraction [inferred from JMLC construction; not from a primary measurement].

**Is 270° worth it vs 90–180°** [inferred; no primary comparative measurement found]: 
- A 90° roll converts a sharp edge to a quarter-cylinder; this suppresses the first-order edge diffraction mode and softens the transition.
- A 180° roll produces an interior lip; the cavity between the lip and the horn body can resonate at frequencies where cavity depth ≈ λ/4. For a 20 mm cavity depth (typical of a 50 mm radius at 180°), this resonance is at c/(4×0.020) ≈ 4,300 Hz — squarely in the passband.
- A 270° roll turns the lip fully back, eliminating the cavity by opening it to the room. Crowe's design avoids a closed cavity by rolling past 180° [inferred from geometry].
- **Conclusion [inferred]**: 270° avoids the cavity resonance that a 180° roll creates. The key advantage is not diffraction per se but resonance suppression. The practical cost is depth (the roll adds ~lip_radius to the horn's footprint behind the mouth).

**Large solid body / flange behind the mouth** [inferred from Tritonia guidance]: a large flat flange behind the mouth would act as a baffle; its edge becomes the new diffraction source, shifted outward. A small baffle with rounded edges (Tritonia guidance) minimizes this. A thick roll serves as a soft "baffle" of its own. A sealed flange behind the roll creates a trapped volume — avoid this.

---

## 4. Exponential vs conical/OS throat region and HF beaming

**Why exponential flare narrows at HF** [verified, at-horns.eu/exar-story.html; inferred from Keele patent mechanism]:
- In an exponential horn the wavefronts must curve more and more as frequency rises (to satisfy the boundary condition at the wall). Above cutoff, the wavefront geometry gradually approaches plane-wave behavior at the walls. The wall angle at the mouth therefore subtends a narrower spherical cap at high frequencies.
- Formally: the exponential law imposes a minimum cutoff frequency, and above it the wavefront radius of curvature grows with frequency, causing HF beaming.

**Why conical gives constant directivity** [verified, US4071112]:
- A conical section is geometrically a solid angle. By definition, all rays inside the cone subtend the same angle independent of frequency. The wavefront in a conical horn is spherical and the included angle of that sphere is the cone's included angle, to first order.
- **The specific knob**: the **cone's half-angle** (= the throat angle when the exponential section is matched to the cone). Once the cone angle is set, the HF beamwidth is fixed [verified, US4071112].

**What breaks the constant directivity in practice** [inferred, from Keele patent + at-horns.eu]:
1. If the throat is not round (sharp entry discontinuity), modes are excited at the throat that radiate to the sides at HF. The exponential connector in the Bi-Radial addresses this.
2. At very high frequencies the throat diameter becomes comparable to the wavelength: the throat acts as an aperture and diffracts. From at-horns.eu/exar-story.html [verified]: "The ending diameter of the extension is still what determines the high-frequency directivity." For our 36 mm throat diameter: ka = 1 at f = c/(2πa) = 344/(2π×0.018) ≈ 3,040 Hz. Above 3 kHz, the throat diffraction angle θ ≈ arcsin(0.61 λ/D) already matters [measured, Rayleigh criterion].
3. If the mouth is small relative to the K-law mouth size at the crossover frequency, the horn cannot control directivity at that frequency regardless of throat geometry [verified, US4308932A].

**OS/OSSE family**: the coverage angle α sets the target solid angle; the wall flare (k, n, q parameters) controls how gradually the wavefront is converted from cylindrical to spherical. Setting α too high relative to the mouth size produces the same problem as a too-narrow conical cone [inferred from at-horns.eu].

---

## 5. Shape knobs by family — which are acoustic, which are cosmetic

### 5a. Keele Bi-Radial family

| Knob | Acoustic effect | Range for our target | Cosmetic? |
|---|---|---|---|
| H throat angle A_h = 0.9 × B_h | Sets HF H-plane beamwidth directly | 36° for B_h = 40° (target), 36–40.5° [repo] | No |
| V throat angle A_v = 0.9 × B_v | Sets HF V-plane beamwidth | 22.5° for B_v = 25° [inferred] | No |
| Mouth width W_H | LF H pattern control via K-law | ~496 mm at 700 Hz (matches envelope) [measured] | No |
| Mouth height W_V | LF V pattern control | ~794 mm at 700 Hz (too large → accept V narrowing) [measured] | No |
| Flare exponent n | Affects midband rise from exponential→mouth; higher n = more linear horn body | 4–6 preferred [repo] | Partly |
| Gap width w_g | 21:1 slot diffraction risk | ~0.37 × r₀ per one anchor; smaller = less diffraction [inferred] | No |
| Connector law | LF loading efficiency | Exponential required [repo] | No |
| Mouth aspect | Appearance only within K-law limits | 1.8:1 target (Crowe-like) [repo] | Mostly |

### 5b. Crowe ES-style (osse_rollback + superformula X, per CROWE_X_HORN_HANDOFF)

| Knob | Acoustic effect | Range for our target | Cosmetic? |
|---|---|---|---|
| `a_h_deg` / `a_v_deg` | Wall angle: sets HF coverage (like cone half-angle in a conical) | H: 22–26°, V: 13–16° for 80×50° target [repo] | No |
| `s`, `n`, `q`, `k` (OSSE termination) | Wall curvature near mouth: `s = 0` = nearly straight cone; higher s = stronger outward curve. Controls midband roll-off and mouth reflection | s = 0.3–0.6 for gradual flare matching Crowe section profile [repo] | No (s affects radiation angle at mouth) |
| `b` (curvature decay, in ROLLED_RECT construction) | Distribution of expansion along depth; too fast = disc side, too slow = no roll | 0.55–0.85 [repo] | No |
| `sf_m = 4` | Four-corner (X) cross-section symmetry | Fixed at 4 for Crowe-style | Cosmetic only (affects azimuthal polar uniformity at HF via second derivative) |
| `sf_n1` | Corner sharpness: controls amount of star vs. round cross-section | 1.6–2.0 for the target X shape [repo] | Mostly cosmetic (sharp corners = diffraction source) |
| `sf_n2` | Edge straightness: affects how much the wall mid-panels bow | 6–8 for straight sides [repo] | Partly cosmetic |
| `sf_amt` | X strength | 0.35–0.45 [repo] | Cosmetic (secondary acoustic effect via polar azimuthal uniformity) |
| `r_lip_mm` | Lip radius: affects diffraction above f_transition ≈ 55/r Hz | 40–50 mm recommended (f_transition ≈ 1,100–1,375 Hz) [inferred from §3a] | No for in-band; cosmetic at LF |
| `wrap_deg` | Roll angle: 90–130° = thin lip; 150–200° avoids cavity resonance; 270° not achievable with current 200° cap | 130–150° with current generator (remove 200° cap if possible) [repo; §3b] | No above cavity resonance frequency |
| `L_mm` | Horn depth: sets overall flare rate and mouth size for given wall angle | 260–320 mm [repo]; ≈ 0.45 × W (Crowe ratio) | No |
| Pucker amplitude H/V | Displaces wall centres relative to diagonal; purely axial, no silhouette change | H 0–12 mm, V 0–16 mm [repo SECTION_PUCKER] | Cosmetic at small amplitude; No at large amplitude (creates ridges → diffraction) |

### 5c. Le Cleac'h rollback family

| Knob | Acoustic effect | Range for our target | Cosmetic? |
|---|---|---|---|
| `fc` (cutoff Hz) | LF loading; below fc = exponential decay. | ≤ 700 Hz to load from crossover [inferred from JMLC_LECLEACH] | No |
| `T` (Salmon parameter) | Wall curvature: T=1.0 = exponential, T=0.5 = intermediate, T=0 = conical. T ≈ 0.5–0.8 for typical JMLC | 0.5–0.8 [repo] | No |
| Stop angle > 180° | Rollback angle; 270° = full wrap à la Crowe. Avoid 180° ± 20° (cavity resonance) | 220–280° (wraps past 180°, avoids 160–200°) [inferred from §3b] | No at >180° |
| H/V asymmetry via `ar_m`, `ar_p` | Mouth height vs width; independent coverage axes | ar_m = 1.5–2.5 for 1.8:1 aspect [repo] | No |
| Throat angle φ₀ | As in JMLC: "included exit angle/2"; sets throat impedance matching | Match driver: 2° = HF1440 exit half-angle [repo] | No |

---

## 6. Known gaps (not resolved by this research)

1. **Crowe's ES equation is unpublished.** The specific exponential-spiral growth constant b, the cross-section evolution law, and the exact 270° wrap geometry are proprietary. Only indirect reconstruction is possible [verified].
2. **No primary numeric rule for kr >> 1** was found in a fetched source. The r/λ rule above is [inferred from acoustics fundamentals], not from a primary paper.
3. **Independent Crowe measurement data**: all measurement reports on josephcrowe.com are his own. No third-party polar map or DI data for any ES model was found [verified absence].
4. **The 270° vs 90–180° roll cavity resonance claim** in §3b is [inferred] from geometry; no BEM or measurement comparison was found.
5. **Geddes papers inaccessible**: gedlee.com has a permanent SSL error. His specific second-derivative rule for surface smoothness is not independently confirmable from fetched sources.
6. **HF beamwidth in OS-SE vs coverage angle alpha**: at-horns.eu confirms that throat diameter (not alpha alone) determines the HF beam ceiling [verified]; but the precise parametric formula linking alpha → HF-6dB angle in the coverage-law regime was not found in readable form.

---

## 7. Synthesis for our cells

**Why current cells have DI rise 2→16 dB (beam narrows with frequency)**:
Most likely causes, in order of likelihood [inferred from §4]:
1. **Mouth too small for K-law at 700 Hz**: cells sized to fit the 600×480 mm envelope at ~700 Hz may be under the K-law limit, so the horn cannot control the pattern at crossover. The K-law mouth at 700 Hz / 80° is 496 mm (H), which is achievable (80° down to ~579 Hz). At 50° V: 794 mm — impossible in our envelope (50° only down to ~1157 Hz; at 700 Hz the vertical supports ~83°). Conclusion: H control is feasible; V control below ~1.2 kHz will naturally be lost. This is acceptable given the brief's cov_v_weight: 0.5.
2. **Wall angle too shallow for the coverage angle target**: if a_h < 0.9 × 40° = 36°, the high-frequency cone is too narrow and the beam is narrower than 80° at HF. Set a_h ≥ 36° and a_v ≥ 22.5° [measured from K-law + 0.9×B rule].
3. **s or b too large**: a strongly flared mouth (high s) makes the near-mouth geometry more like a large disc radiator, which narrows the HF beam. Keep s ≤ 0.6 or b = 0.6–0.8 [repo guidance; inferred from Crowe section profile].
4. **Lip geometry**: a thin or absent lip at the mouth produces sharp-edge diffraction, which both narrows the beam and adds comb-filter coloration. Use r_lip ≥ 35 mm with wrap ≥ 130° [inferred from §3a; repo guidance].

---

## 8. ATH R-OSSE formula — exact implementation

Sources: `docs/geometry-contract.md` in fork `C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher` [verified, read 2026-11-15]; `profile_formulas.py` and `profile_common.py` in the installed mesher [verified, read 2026-11-15]; ATH user guide `Ath-4.8.2-UserGuide.pdf` referenced but not read this session.

### 8a. R-OSSE formula as implemented

For the main curve, `0 ≤ t ≤ tmax` (default tmax = 1):

```
c1 = (k · r0)²
c2 = 2 · k · r0 · tan(a0)
c3 = tan(a)²
L  = (sqrt(c2² − 4·c3·(c1 − (R + r0·(k−1))²)) − c2) / (2·c3)

x(t) = L·(sqrt(r²+m²) − sqrt(r²+(t−m)²))
      + b·L·(sqrt(r²+(1−m)²) − sqrt(r²+m²))·t²

throat_r(t) = sqrt(c1 + c2·L·t + c3·(L·t)²) + r0·(1−k)
mouth_r(t)  = max(0, R + L·(1 − sqrt(1 + c3·(t−1)²)))

y(t) = (1 − t^q)·throat_r(t) + t^q·mouth_r(t)
```

The mouth is at t = tmax; the throat is at t = 0. Total length = ext_len + slot_len + L (the main curve's axial extent at tmax). [verified, geometry-contract.md §R-OSSE Profile]

### 8b. Parameter definitions and acoustic meanings

| Parameter | Canonical key | Default | Acoustic role |
|---|---|---|---|
| `r0` | `r0_mm` | 12.7 mm | Throat radius. Matches driver exit. For HF1440: **18 mm**. |
| `R` | `R_mm` | 150 mm | Outer/mouth radius. L is derived to reach R from r0. This sets the mouth size for LF pattern control. |
| `a` | `a_deg` | 60° | Coverage half-angle. Sets asymptotic wall angle at the mouth end. **The HF beamwidth knob**: at HF the horn is a solid angle with opening 2a. |
| `a0` | `a0_deg` | 15.5° (default); 0° for ATH text import | Throat opening half-angle. Matches driver exit angle; for HF1440 ≈ **2°** (from brief). Affects LF impedance matching. |
| `k` | `k` | 1.0 | Throat expansion factor. k=1: standard OS; k>1: wider OS-style throat region. Primarily affects LF loading. |
| `q` | `q` | 1.0 for R-OSSE | Blend exponent: transitions from throat_r to mouth_r. Higher q = later transition (mouth-side flare). |
| `r` | `r` | 0.4 (default from `_DEFAULTS`) | Apex radius in the x(t) parametric map. Controls how the axial distance distributes along the wall profile. |
| `m` | `m` | 0.85 (default from `_DEFAULTS`) | Apex shift (position of the inflection/apex in the x(t) map). |
| `b` | `b` | 0.2 (default from `_DEFAULTS`) | Bending coefficient in the x(t) map. Higher b = more of the axial extent used near the mouth. |
| `tmax` | `tmax` | 1.0 | Truncates the main curve at t = tmax. `tmax < 1` produces an un-rolled termination; `tmax > 1` (not standard) would continue past the R point. |
| `s1`, `s2` | | 0 | Throat stretch: S(x) = x + s1·(180/π)·atan(s2·x). Stretches axial distance, leaves radius unchanged. |

### 8c. Per-azimuth expressions

Any numeric parameter can be a **string expression** evaluated at each azimuth `p`. Here `p` is normalized azimuth: `p = 0` = horizontal (x-axis), `p = 1` = vertical (y-axis) for the first quadrant (0 to pi/2). [verified, `profile_common.py` line 145: `if node.id == "p": return p`]

Standard expressions for H/V asymmetry:
- Coverage angle: `"a_h*cos(p*pi/2)^2 + a_v*sin(p*pi/2)^2"` — sets independent H and V coverage.
- Mouth radius: `"R_h*cos(p*pi/2)^2 + R_v*sin(p*pi/2)^2"` — independent H and V mouth widths (elliptical mouth).

The repo's grid rows (e.g. `hornlab_search/design/generators/grid.py` OSSE rows) pass the wall angle as `a(φ) = a_h·cos²φ + a_v·sin²φ` to produce H/V asymmetric coverage from a single OSSE/R-OSSE profile per azimuth [repo; CROWE_X_HORN_HANDOFF_2026-11-15.md §4].

### 8d. Rectangular mouths — ATH approaches

**MORPH section** (mesher `[morph]` / ATH `Morph` block): morphs the R-OSSE/OSSE round profile into a rectangular target at the mouth.
- `morph_target = 1` → rounded rectangle (ATH's standard).
- `morph_width_mm`, `morph_height_mm`: full width and height of target rectangle.
- `morph_corner_mm`: absolute corner radius of the target.
- `morph_rate = 3.0` (default): how quickly (in normalized profile-fraction units) the morph takes effect.
- `morph_fixed = 0.2` (default): fraction of horn nearest the throat that is not morphed.
- The morph is an **additive azimuthal displacement**: it shifts r(z, φ) toward the target rectangle shape, without changing the axial profile shape [verified, geometry-contract.md; ATH user guide reference].

**FREEFORM formula** (mesher `formula = "FREEFORM"`): separate `profileH` and `profileV` anchor lists with independent meridians, plus a `crossSections` schedule with `circle`, `ellipse`, `superellipse`, or `rounded_rectangle` shapes. This is the most flexible approach for rectangular-mouth horns with independent H/V wall profiles, but the two profile meridians must share the same axial endpoints and the same throat radius.

### 8e. Typical ranges for a 1–1.4" driver (R-OSSE with rollback)

| Parameter | Range for our target | Note |
|---|---|---|
| `r0` | 18 mm (HF1440) | Fixed; from driver |
| `R` | 220–290 mm for H; 150–240 mm for V | K-law at 700 Hz / 80°: R_h = 248 mm; V: accept smaller mouth |
| `a` | H: 36–40°; V: 22–26° | 0.9×(half-coverage); a_h ≥ 36° for 80° H |
| `a0` | 2° | Match driver exit half-angle |
| `k` | 1.0–1.3 | Small k values broaden the throat region smoothly |
| `b` (curvature decay) | 0.55–0.85 | Crowe-style: b ≈ 0.7 gives moderate roll-out depth [repo] |
| `tmax` / stop angle | 240–275° contour degrees | Roll past 180°; avoid 160–200° cavity resonance range [§3b] |
| `morph_corner_mm` | 15–40 mm | Governs corner radius of rectangle; small = sharper corners |
| `morph_rate` | 2–5 | Lower = more gradual morph from throat |
| `morph_fixed` | 0.15–0.30 | Keep throat round for at least 15–30% of horn length |

---

## 9. Le Cleac'h rollback criterion

This is established in the repo; cite only. From `docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md` [repo]:

- The JMLC construction continues the same expansion law past 90° (the mouth-perpendicular point) until the wall angle reaches the **stop angle** parameter. Stop angle = 90° = flat-mouthed horn. Stop angle > 90° = rollback. Stop angle = 360° = the wall completes a full revolution (toroid).
- Fourcade's reference case uses stop angle = 360°. The useful range for rollback horns is 180°–360°.
- **T parameter**: T = 0.8 → less rollback (shallower curvature); T = 0.5 → more rollback (deeper). The repo's `lecleach_rollback.yaml` uses T ≈ 0.5–0.8.
- **Physical meaning of the rolled lip**: the lip points *backward* (toward the driver) once the wall angle exceeds 180°. At stop = 270°, the lip is pointing straight back; at stop = 360°, the lip closes back to horizontal.

**Rollback and cavity resonance** [inferred from geometry; §3b of this document]:
- Stop angles between ~160° and ~200° produce a curved-over lip that traps a narrow cavity between the rolled portion and the horn body. The cavity depth is approximately R · (1 − cos(stop − 90°)). Avoid this range for stop angles.
- Stop angles ≥ 220° open the cavity to the room as the lip curves back past 90° from vertical, eliminating the trapped resonance.

**Recommendation**: target stop angle 240°–280° (rollback 150°–190° past the mouth plane). This exceeds the 200° cap in the current `osse_rollback` generator — if owner approval is given, increase the cap to 240°+.

---

## 10. Recommended parameterisation for independent acoustic control

For a rolled rectangular horn like the repo's ROLLED_RECT family (or an R-OSSE with MORPH), the acoustic intent maps to parameters as follows. The goal is a parameterisation where changing one acoustic target changes exactly one parameter group.

### 10a. The four independent controls

| Acoustic intent | Parameter(s) | Independence | Range for our brief |
|---|---|---|---|
| **H coverage angle** | `a_h` (H coverage half-angle in per-azimuth expression) | Fully independent of V; derived from 0.9 × (H half-beamwidth) | 36–40° for 80° H |
| **V coverage angle** | `a_v` (V coverage half-angle) | Fully independent of H | 22–26° for 50° V |
| **Mouth size / LF control** | `R_H`, `R_V` (H and V mouth half-widths) or `morph_width_mm`, `morph_height_mm` | Independent of wall angle; sets LF pattern-control frequency via K-law | R_H = 220–280 mm; R_V = 150–240 mm |
| **Throat loading** | `a0` (throat angle, matches driver) + `k` (throat expansion) | a0 matches driver exit; k affects LF impedance independently | a0 = 2°; k = 1.0–1.2 |
| **Rollback / diffraction** | `tmax` or `stop_angle` (terminal contour parameter) + `morph_corner_mm` or `r_lip_mm` / `wrap_deg` | Rollback angle independent of wall flare; corner radius independent of both | stop ≥ 240°; r_lip = 35–50 mm |
| **Cross-section shape** | rectangular exponent `p` in `(|x|/h)^p + (|y|/v)^p = 1` or `morph_corner_mm` | Independent of wall profile | p = 8–16 for straight sides with rounded corners |

### 10b. Why the current osse_rollback cells fail this

The current `osse_rollback` cells couple coverage angle and mouth size through the `a_h`, `a_v` OSSE parameters and the seed_policy [from CROWE_X_HORN_HANDOFF §1; repo]. The K-law was used to derive the mouth from `a_h` and `f0`, which forces the wrong W/H and portrait orientation. The fix is to use `generator.seed_policy: explicit` (inside the generator block) and set `R_H`, `R_V` or mouth dimensions independently of the coverage angle.

### 10c. Concrete starting point for our brief

For 80°×50°, 700 Hz, 600×480×480, 18 mm exit:

```yaml
# R-OSSE with MORPH approach (mesher native)
formula: R-OSSE
r0: 18          # HF1440 exit radius
R: 248          # mouth half-width H — K-law at 700 Hz is 248 mm (496 mm total)
a: "36*cos(p*pi/2)^2 + 24*sin(p*pi/2)^2"   # H: 36°, V: 24°
a0: 2.0         # HF1440 exit half-angle
k: 1.0
b: 0.70         # moderate curvature decay (Crowe-style)
q: 1.0
tmax: 1.08      # ~270° of contour — rollback; actual angle depends on b, R, r0
[morph]
  morph_target: 1
  morph_width_mm: 540    # ~540 mm → W ≤ 600 mm
  morph_height_mm: 300   # H/W ≈ 1.8:1 (Crowe ratio)
  morph_corner_mm: 25    # rounded rectangle corners
  morph_rate: 3.0
  morph_fixed: 0.20      # keep throat round for first 20%
```

**What still needs BEM validation** [inferred]:
- Whether `a_h = 36°` actually produces 80° -6 dB beamwidth (depends on the coverage-angle inversion in OSSE vs the geometric solid angle).
- Whether the MORPH transitions are smooth enough not to generate diffraction modes at the morph-onset position.
- Whether the rollback tmax = 1.08 produces the desired ~270° lip (or whether the terminal angle needs to be measured from a rendered profile).
- Throat loading from 700 Hz: requires a BEM run; loading is not predictable from geometry alone.
