# Throat Coupling: Round Driver Plane, Shape Transitions & ATH Practice

**Date:** 2026-10-27
**Author:** Research pass (Sonnet subagent), reviewed by the senior pass the same evening

> **Reviewer note (senior pass, 2026-10-27).** Strong, multi-source: the coupling plane must be round at the
> driver exit (owner rule confirmed; ATH, Geddes US7068805, JBL practice). Non-round entries exist only where
> the DRIVER has a non-round exit (JBL slot-throat, US6744899 / US11877120) or with an external adapter.
> Weak, inferred: the "keep round for the first 20-30 % of length" figure in s3 / (b) - no source gives a
> number, and ATH's own Core example runs `Morph.FixedPart = 0.0` (the morph starts at the throat but with
> zero amount there, growing with `Morph.Rate`). Treat 20-30 % as a starting guess to test, not a rule; our
> own morph cells (`morph_fixed` 0-0.6) can measure it. One number corrected below (cross-mode frequency).

## Bottom Line (plain language)

The acoustic evidence strongly supports the owner's rule: the coupling plane must match the round driver exit exactly at the driver throat diameter, with no shape change at z = 0. Every published waveguide design that ships with a standard compression driver starts from a circular throat at z = 0. Where non-round throats exist in practice (JBL slot-throat systems, line-array waveguides), the round-to-slot transition occurs entirely inside the driver via a special phase plug—the driver exit itself is non-round and the horn throat matches it directly. ATH (Mabat/Marcel Batik) also starts from a circular Throat.Diameter; the Morph and GCurve machinery changes the cross-section downstream of that plane, not at z = 0. The cross-section may then diverge from round gradually, and the literature says this must be "gradual" but provides no quantitative minimum length. The practical recommendation from acoustics literature and ATH design practice: preserve the circular cross-section for at least a meaningful fraction of the horn before introducing aspect-ratio stretching, and keep any wall-angle step at z = 0 close to zero so the driver exit angle is matched. Flutes and ridges that significantly alter the cross-sectional shape should start downstream, not at the coupling plane.

---

## 1. ATH (Ath4 / ath-horns) Throat at the Driver Plane

**Does ATH support a non-round throat at the driver coupling plane?**

No, in standard ATH designs the throat at z = 0 is always a circle defined by a single scalar `Throat.Diameter`. [published — at-horns.eu ATHEX and EXAR400 design pages, ATH 4.8.2 User Guide (image-rendered PDF, paraphrased from page summaries)]

Key parameter summary [published — ATH User Guide 4.8.2; at-horns.eu/core.html; at-horns.eu/tritonia.html]:
- `Throat.Diameter`: single scalar (mm) → circular cross-section at z = 0.
- `Throat.Angle`: single opening half-angle (degrees), matched to the compression driver's exit half-angle. The Tritonia page notes "α₀ (throat opening angle) is still used independently," implying one angle for a rotationally symmetric throat.
- `GCurve.AspectRatio`: sets the height/width ratio of the **guiding curve** cross-section, which is placed at a distance `GCurve.Dist` downstream from the throat plane. If GCurve.Dist > 0 (the typical case), the cross-section at z = 0 is still circular.
- `Morph.TargetShape`: target **mouth** cross-section shape (0 = no morph, 1 = rounded rectangle). This morphs the mouth, not the throat.
- `Morph.FixedPart = 0.0`: the morph transformation starts at the throat position (z = 0), meaning cross-section shaping can begin immediately; however, because the morph operates by interpolating between the "raw" OS cross-section (circular at z = 0) and the target mouth shape, the throat cross-section at z = 0 remains the circle from `Throat.Diameter`. [published — ATH documentation at-horns.eu/core.html; Morph.FixedPart defined as "portion of the horn length from the throat kept fixed during the final morph transformation", 0 = start at throat]
- `Morph.Rate = 3.0`: exponent controlling how fast the cross-section departs from round toward the target mouth shape. Higher values keep the shape nearer to circular for more of the horn length before accelerating the transition near the mouth.
- `Morph.AllowShrinkage`: not documented in accessible sources for this pass; name suggests it controls whether the morph may shrink the cross-sectional dimension.

**ATHEX and EXAR400 explicit evidence** [published — at-horns.eu/athex.html, at-horns.eu/exar400.html]:
- ATHEX: "The waveguide shape is composed of a short **circle-to-hexagon adapter** and six smoothly connected bended petals." — circular throat at z = 0, non-round downstream.
- EXAR400 (R-OSSE, 400 mm, 1" extended throat): throat opening angle = 0°, uses a cubic Bezier curve throat extension; driver interface is a 1" reduction ring on a 1.4" driver. Explicitly round at the driver coupling plane.

**Regarding GCurve.AspectRatio at z = 0:** If a user sets GCurve.Dist = 0, the guiding curve would be placed at the throat, potentially making the cross-section at z = 0 non-circular. This appears to be a non-standard, user-configurable deviation rather than ATH's default or intended practice. [inferred — from GCurve.Dist documentation and standard ATH design examples]

**Does ATH horn morph start from a round throat?** Yes. The morph interpolates between the circular "raw" profile at z = 0 (governed by Throat.Diameter) and the target mouth shape. `Morph.FixedPart > 0` (e.g., 0.3–0.5) explicitly keeps the raw circular cross-section frozen for that fraction of the horn's axial length before any shape change is applied. When FixedPart = 0.0, the transition starts at z = 0, but the cross-section there is still the circle defined by Throat.Diameter. [published — ATH core.html documentation]

---

## 2. Commercial and Published Horns with Non-Round Driver Entry

### 2a. JBL Slot-Throat Direct-Coupled Systems (US6744899)

Patent US6744899B1 ("Direct coupling of waveguide to compression driver having matching slot shaped throats," JBL, filed 2001) [published — US6744899, Google Patents]. The compression driver is specifically designed with a **non-round (slot-shaped) exit** at the driver throat. The phase plug inside the driver performs the round-diaphragm-to-slot-exit transition entirely within the driver body. The horn/waveguide has a matching slot-shaped throat and the two mate directly without an external adapter. Target application: line-array waveguides requiring high vertical directivity.

The key distinction: **the round-to-slot transition is inside the driver, not in the horn or a separate adapter**. The driver exit is physically non-round and matches the horn directly. This is a purpose-built driver; standard 1" or 2" round-exit compression drivers cannot couple to these directly.

### 2b. US11877120 — "Compression Driver Having Rectangular Exit"

Patent US11877120 (recent, assigned to unnamed company) [published — Google Patents summary]. Same concept: phase plug internal to the driver creates a rectangular exit. Round diaphragm → rectangular aperture via blade-bullet phasing plug. Applications in HF/midrange directivity control. No external adapter.

### 2c. JBL Bi-Radial Horns (2380A, 2385A)

Throat: 49 mm (2") round. Mate directly to 49 mm round-exit compression drivers (2441, 2445, 2450, 2485J). The 2327 adapter steps down to 25 mm (1") for smaller drivers. [published — JBL Pro product pages; Adorama, fullcompass.com spec sheets]. No shape conversion at the driver coupling plane.

### 2d. Traditional Rectangular PA Horns

Round-exit compression driver + **separate external round-to-rectangular adapter** + rectangular horn. The adapter is a distinct piece with a round entrance matching the driver exit and a rectangular exit matching the horn throat. [published — US6744899 background section, which explicitly describes this as prior art requiring a "transition coupler"]

### 2e. ATH-Style Horns with ATHEX / Hexagonal Mouth

Circular throat at z = 0. Circle-to-hexagon adapter is part of the horn body. Driver coupling is round-to-round. [published — at-horns.eu/athex.html]

**Summary:** No standard compression driver (round 25 mm or 50 mm exit) couples directly to a non-round horn throat without either (a) a dedicated non-round-exit driver or (b) an external round-to-rectangular adapter. All acoustic evidence supports the conclusion that the coupling plane must be round and equal to the driver exit diameter.

---

## 3. Published Guidance on Cross-Section Shape Transitions

**The defining published statement** comes from US7068805B2 ("Acoustic waveguide for controlled sound radiation") [published — US7068805, Google Patents, verified via WebFetch]:

> "The device contours are circular at the waveguide throat, to match the driver outlet shape, and are modified to become elliptical at the mouth in order to create a radiation pattern that is not axi-symmetric. This transition is done in a gradual manner so as to not unduly disturb the wavefront propagation."

The same patent further notes: "a truly mathematically correct oblate spheroidal (OS) waveguide would have round cross sections throughout; however, satisfactory results have sometimes been obtained with waveguides which maintain the proper cross sectional area but are made to slowly form an ellipse at the mouth as these cross sections move from the throat to the mouth. Too much of this waveguide contour manipulation will yield a device with less than optimal performance." [published — US7068805 and/or adjacent Geddes work, per snippet]

**Higher-Order Modes and driver/horn junction** [published — Earl Geddes, diyaudio "Geddes on Waveguides" thread, search snippet, unverified direct quote]:
- "The junction between compression driver and horn can be a major source of HOMs if there is a significant angular mis-match there."
- "The waveguide's slope at the throat must match the compression driver's exit slope; a mismatch in slopes will cause higher order modes."
- The OS (oblate spheroid) profile generates the **weakest** HOMs of the standard flare types, and matching the entry angle to the driver exit angle is critical.

**Throat extension effect on HOMs** [inferred — diyaudio "deep throat" thread search snippet]:
- Adding a cylindrical or low-angle conical throat extension before the main flare can increase HF bandwidth without disturbing polars significantly.
- However, a junction from a cylindrical extension to an OS flare introduces a wall-curvature discontinuity; a cubic Bezier curve (as in EXAR400) avoids this.

**Minimum transition length — quantitative rules:**
- No published AES paper or equivalent primary source was found specifying a minimum transition length in mm or as a fraction of horn length for round-to-non-round shape transitions in audio-frequency compression-driver horns. [unverified — searched extensively; results returned only qualitative guidance]
- The microwave waveguide literature uses λ/2 as a reference for mode coupling (mode D > 1.22λ for TM₁₁), but this does not translate directly to audio horn practice because audio horns operate over a multi-octave range with a flared profile, not a uniform cross-section. [inferred]
- The US7068805 principle (area conservation + gradual transition) and the community experience with ATH Morph.Rate suggest that keeping the cross-section close to round for roughly the first 20–40% of the horn axial length before significant shape deviation provides acceptable results. [inferred — from ATH example configurations showing Morph.FixedPart in range 0.0–0.5]

**Diffraction slots (Keele/Henricksen):**
- A "diffraction slot" is a sharp discontinuity in flare rate that creates a secondary line source for pattern control in older CD horns. It is intentionally abrupt, which introduces reflections and comb filtering. [published — US4685532 (Keele constant-directivity patent), patent background summaries]
- Modern constant-coverage waveguides (Geddes OS, JBL PT) avoid these discrete slots in favour of continuously varying flare rates. [published — US7068805, US6581719 background]
- Flutes and ridges added to a horn surface are NOT the same as a diffraction slot if they do not create an abrupt area step; smooth ridges modulate the wall normal without a cross-sectional discontinuity.

---

## 4. Throat Mismatch Effects — Numbers Where Available

| Mismatch type | Effect | Evidence quality |
|---|---|---|
| Wall-angle step at z = 0 (driver exit angle ≠ horn throat angle) | HOMs generated; reported as "blips" in the response near the throat's first cross-mode. For a round throat of diameter d that mode starts at f11 = 1.84 c / (pi d), about 4.1 kHz for a 49 mm (2") and 5.6 kHz for a 36 mm (1.4") throat [published formula; our constants.BESSEL_J1P_11]. (The draft's "c / (2 d) = 6.7 kHz" was arithmetically wrong - c / (2 d) is 3.5 kHz - and is removed.) | [published — Geddes forum, search snippets only; no controlled dB measurement found accessible] |
| Cross-sectional area step at z = 0 (driver exit area ≠ horn throat area) | Impedance discontinuity → reflected energy, ripple in pressure response above the frequency where the diameter is λ/2 | [published — US7039211, patent background] |
| Gradual round-to-elliptical transition (area conserved) | "Satisfactory results" noted; "too much manipulation" degrades performance | [published — US7068805] |
| Non-round throat with standard round-exit driver (shape mismatch at z = 0) | No controlled study found. By analogy to the area-step and angle-step cases, a shape mismatch at z = 0 generates HOMs at and above the spatial frequency of the shape asymmetry, i.e., at frequencies where λ approaches the non-round dimension | [inferred — from HOM theory; unverified quantitatively] |

No published paper with dB-level quantification of shape-mismatch (as distinct from area-mismatch or angle-mismatch) ripple at the driver/horn junction was accessible during this pass.

---

## Concrete Recommendations for Modelling

**(a) Coupling plane must be round at driver exit diameter**

The coupling plane (z = 0, the source surface in the BEM simulation) must be a circle with diameter equal to the nominal driver exit diameter. This is [published] from US7068805 and confirmed by every standard commercial and ATH horn design surveyed. The owner's rule is correct. Any deviation from a circular coupling plane at z = 0 requires either a dedicated non-round-exit driver (where the non-round geometry is internal to the driver, not a BEM source assumption) or an external adapter—neither of which is part of the brief. **Evidence strength: strong (multiple independent published primary sources).**

**(b) Recommended minimum transition behaviour after the coupling plane**

- Preserve a circular cross-section for at least the first segment of the horn before introducing aspect-ratio stretching. For ATH use, this means `Morph.FixedPart` ≥ 0.2–0.3 (20–30% of axial horn length) when using a non-round mouth target. Use `Morph.Rate` ≥ 3 to keep the transition slow near the throat and accelerate only near the mouth.
- For the BEM simulation cells (OSSE / R-OSSE): set `aspect_ratio = 1.0` (circular cross-section) at z = 0 and ramp the aspect ratio smoothly over the first ≥ 20% of axial length, so that the cross-section at the coupling plane is circular. A linear ramp of aspect ratio from 1.0 at z = 0 to the target value at some fraction of horn length is the simplest implementable approach.
- No published quantitative minimum distance (in mm) or fraction of horn length was found. The guidance "gradual" and "area conservation" from US7068805 is the strongest available statement. The 20% figure above is [inferred] from ATH community practice with Morph.FixedPart, not from a controlled acoustic experiment.
- **Evidence strength: moderate (qualitative guidance published; no validated quantitative rule found).**

**(c) Flutes and ridges**

- Flutes and ridges that primarily modulate the **wall normal direction** (curvature) without a large cross-sectional area step are less likely to generate HOMs than shape changes that alter the cross-sectional shape at the coupling plane. [inferred]
- Flutes or ridges that significantly alter the cross-sectional symmetry (e.g., converting from round to multi-lobed profile at z = 0) are equivalent to a shape mismatch at the coupling plane and should be avoided at z = 0.
- **Recommendation**: start any flute or ridge feature at least one throat-diameter (≈ 36 mm for the brief's driver) downstream from the coupling plane to allow the wavefront to become established in the circular/axisymmetric geometry before encountering the perturbation. For smooth Salmon-style ridges (gradual wall-curve modulation), earlier introduction may be tolerable but remains unverified. **Evidence strength: weak (inferred from HOM coupling theory; no published measurement for audio-frequency horns).**

---

## Source Table

| Title | Author(s) | Year | URL | Supports | Verified |
|---|---|---|---|---|---|
| "Acoustic waveguide for controlled sound radiation" (US7068805) | Earl Geddes (GedLee LLC) | 2006 | https://patents.google.com/patent/US7068805 | Q1 (throat must be circular), Q3 (gradual transition rule), Q4 (qualitative mismatch effect) | Fetched |
| "Direct coupling of waveguide to compression driver having matching slot shaped throats" (US6744899) | Keith Heist (JBL) | 2004 | https://patents.google.com/patent/US6744899 | Q2 (slot-throat driver mechanism), Q1 (traditional round driver coupling via adapter) | Fetched (Google Patents summary) |
| "Compression driver having rectangular exit" (US11877120) | — | 2024 | https://patents.google.com/patent/US11877120 | Q2 (non-round driver exit built inside driver) | Fetched (partial) |
| ATH EXAR400 waveguide page | Marcel Batík (at-horns.eu) | 2024–2026 | https://at-horns.eu/exar400.html | Q1 (ATH uses circular coupling plane) | Fetched |
| ATH ATHEX waveguide page | Marcel Batík (at-horns.eu) | 2024–2026 | https://at-horns.eu/athex.html | Q1 (circle-to-hexagon: circular throat at z=0) | Fetched |
| ATH Core design page | Marcel Batík (at-horns.eu) | 2024–2026 | https://at-horns.eu/core.html | Q1 (Morph.FixedPart=0.0 definition, throat parameters) | Fetched |
| ATH 4.8.2 User Guide (PDF) | Marcel Batík | 2024 | https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf | Q1 (Throat.Diameter = single scalar, Morph parameters) | Fetched (image-scanned PDF; parameters from page summaries, not direct text extraction) |
| "Compression driver and horn structure" (US8477979) | Robert M. O'Neill | 2013 | https://patents.google.com/patent/US8477979 | Q2 (equivalent-throat driver with non-round internal geometry) | Fetched (Google Patents summary) |
| JBL 2380A/2385A Spec Sheets | JBL Pro | — | https://jblpro.com/products/2380A | Q2 (49 mm round throat coupling) | Search snippet only |
| diyaudio "Geddes on Waveguides" thread | Earl Geddes et al. | 2007–ongoing | https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872 | Q3/Q4 (HOM from angular mismatch at throat, entry angle importance) | Search snippet only (forum blocked WebFetch) |
| "Horn Theory: An Introduction" (audioXpress) | Bjørn Kolbrek | 2008 | https://audioXpress.com/assets/upload/files/kolbrek2885.pdf | Q3/Q4 (exit angle matching practice) | Search snippet + PDF binary (unreadable) |
| diyaudio "Acoustic Horn Design – The Easy Way (Ath4)" thread | Marcel Batík, community | 2018–2026 | https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806 | Q1 (ATH throat parameters, Morph.FixedPart definition) | Search snippets only (forum blocked WebFetch) |
