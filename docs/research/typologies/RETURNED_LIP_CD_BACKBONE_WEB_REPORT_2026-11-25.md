# Agent-collected web research report (verbatim), 2026-11-25

Raw report of a research subagent (Sonnet) dispatched for [RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md](RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md). Kept verbatim (corrections live in the consuming dossier, section 3). Its status labels are the agent's own; only the R-OSSE rev7 items marked *re-read* in the dossier were checked again against the PDF in the parent session. diyAudio items are search snippets (the site blocks automated reading).

---

# Horn HF Beamwidth, CD Construction Laws, and BEM Optimization
## Web Research Report — 2026-11-24

---

## Source Table

| Source (URL) | What it gives us | Status |
|---|---|---|
| Keele, D.B. Jr., "What's So Sacred About Exponential Horns?", AES Preprint 1038, 51st Convention, 1975. PDF: https://audioroundtable.com/misc/Keele_Horn_Design_AES_1038.pdf | CE horn design (exponential throat + conical body + mouth flare); formula X = K/(θ·fT), K = 2.5×10⁴ m·deg·Hz; midrange narrowing fix; round→rect throat transition; product examples 90×40°, 60×40°, 40×20° | primary (author) — READ |
| Kolbrek, B., "Horn Theory: An Introduction, Parts 1 & 2", audioXpress 2008. PDFs: audioxpress.com/assets/upload/files/kolbrek2884.pdf and kolbrek2885.pdf | OS waveguide formula r = √(rt² + tan²(θ₀)·x²); CE horn synthesis; spherical wave horn construction; Manta-Ray waistbanding; intercept frequency formula f_I = 25106/(x·θ); Freehafer/Geddes/Putland references | secondary, peer-reviewed — READ |
| Batík, M., "OS-SE Waveguide", at-horns.eu, October 2020. PDF: https://www.at-horns.eu/release/OS-SE%20Waveguide.pdf | OS-SE formula with generalized OS + superellipse flare (eq. 1–5); morphing algorithm; throat opening angle parameterization; references Geddes 1989/1993/2002 | primary (author) — READ |
| Batík, M., "R-OSSE Acoustic Waveguide", at-horns.eu, December 2022. PDF: https://www.at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf | Complete R-OSSE parametric formula (9 parameters: R, a, r0, a0, k, r, m, b, q); BEM results for ST260 reference case (a=39°, R=130mm, 1" throat); throat expansion factor k effect on DI slope; throat mismatch: "virtually no impact on normalized polar response"; throat opening angle analysis | primary (author) — READ |
| Geddes, E.R., "Acoustic Waveguide Theory", JAES 37(7/8):554-569, 1989. | OS waveguide theory; oblate spheroidal coordinates; formula r(x) = √(rt² + (tan θ₀·x)²); HOMs above cutoff dictated by throat radius and angle | primary (author) — NOT READ (paywalled AES eLib) |
| Geddes, E.R., diyAudio "Geddes on Waveguides" thread (snippets). https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/ | OS formula confirmation; throat/driver angle matching ("for extreme accuracy, initial angle and radius should match exit angle and radius of driver"); B&C driver 6.5° exit mismatch causes more HOMs; 1.5" driver HF to 10–12 kHz on true CD, 2" to 9–10 kHz | primary (author, forum) — snippet only (diyAudio bot-blocked) |
| Henricksen, C.A. & Ureda, M.S., "The Manta-Ray Horns", JAES 26(9):629-634, 1978. | Manta-Ray constant directivity design; non-radial walls avoid waistbanding; improved H and V intercept frequency independence | primary (authors) — NOT READ (paywalled AES eLib; abstract/snippet only) |
| Bängtsson, E., Noreland, D. & Berggren, M., "Shape Optimization of an Acoustic Horn", Comput. Methods Appl. Mech. Eng. 2003. Report: https://www.it.uu.se/research/publications/reports/2002-019 | 8th-order Bernstein polynomial parameterization; BFGS quasi-Newton; vertex-displacement as design variables → "disastrous ragged results"; optimized for impedance matching | secondary, peer-reviewed — snippet only (301 redirect) |
| Udawalpola, R. & Berggren, M., "Optimization of an Acoustic Horn with Respect to Efficiency and Directivity", IJNME 2007. | Gradient/adjoint optimization; efficiency + directivity; "explicit directivity requirements obtainable but with substantial loss of efficiency"; manufactured horn with near-perfect impedance matching | secondary, peer-reviewed — snippet only |
| Morgans, R., Zander, A., Hansen, C. & Murphy, D., "EGO Shape Optimization of Horn-Loaded Loudspeakers", Optim. Eng. 9(4):361-374, 2008. | Spline parameterization; EGO/kriging surrogate; targets frequency-independent beamwidth; BEM evaluation | secondary, peer-reviewed — snippet only (DSpace DNS fail) |
| Kasolis, F., Wadbro, E. & Berggren, M., "Fixed-Mesh Curvature-Parameterized Shape Optimization of an Acoustic Horn", Struct. Multidisc. Optim. 46:727-738, 2012. PDF: people.cs.umu.se/martinb/downloads/Papers/KaWaBe12M.pdf | Curvature (angle-between-segments) parameterization; L-BFGS; FE Helmholtz; "handful of control points defies the purpose of numerical optimization"; discrete curvature = robust smoothness | secondary, peer-reviewed — READ |
| Hipperson, J., Hargreaves, J.A. & Cox, T.J., "JAX-BEM: Gradient-Based Acoustic Shape Optimisation via a Differentiable BEM", Forum Acusticum 2026, Graz. PDF: dael.euracoustics.org/confs/fa2026/data/articles/000191.pdf | Differentiable BEM; spline control points for axial profile; L-BFGS; target 70°H × 50°V, 4–18 kHz; key result: "smooth edge termination contributes the most to improvements in directivity"; 948-element quadrant; Funktion-One R&D | secondary, peer-reviewed — READ |
| Holland, K.R., Fahy, F.J. & Morfey, C.L., JAES, May 1991. PDF excerpt: ioa.org.uk/...THROAT_IMPEDANCE... | Wavefront shapes in horns; one-parameter model accuracy; throat impedance prediction | secondary, peer-reviewed — NOT READ (found abstract/title only via search) |
| audioxpress.com article "Understanding Horn Directivity Control" (Keele formula summary). | Mouth dimension formula d = K/(Θ×fΘ), K = 2.54×10⁴ m·deg·Hz; pattern flip explained; physical size trade-offs | secondary (practitioner reports) — READ |
| diyAudio forum snippets on R-OSSE, waistbanding, CD, pattern flip. Various URLs. | Rollback "shadows edge, lowers diffraction intensity, smoothens frequency response"; "any horn with continuously flaring wall has higher directivity at HF, lower at LF"; conical shape required for consistent LF directivity; waistbanding is a "pinch" of pattern at LF | secondary (practitioner reports) — snippet only (diyAudio bot-blocked) |

---

## Q1: What physically sets high-frequency beamwidth?

**Physics of HF beamwidth in horn/waveguide types:**

In an exponential horn, the directional characteristics are "highly dependent on the flare rate" [Keele 1975, verified: read]. At HF, the wavelength becomes small relative to the throat region, so the wavefront detaches from the horn walls and the guide behaves increasingly as a radiating piston of the throat diameter — the horn begins to beam. This is a consequence of the horn walls becoming acoustically transparent when λ ≪ local horn dimension: energy that entered the throat region continues on the throat's solid angle, narrowing with frequency.

In a conical horn, the wall angle is constant and sets a fixed solid angle for the wavefront throughout. The result is that "the conical taper is the only one which provides a constant solid angle to wavefronts travelling through the horn" [Keele 1975, verified: read]. At HF the conical body behaves like a solid-angle-defining guide; the beamwidth tracks the half-angle of the cone. This is why all CD horn designs incorporate a predominantly conical (or quasi-conical) body section for HF control.

In an oblate spheroidal (OS) waveguide, r(x) = √(rt² + tan²(θ₀)·x²), where θ₀ is the half coverage angle. Here the wall angle is not constant — it rises from zero at the throat to θ₀ asymptotically — but above a frequency set by the throat radius and θ₀, the waveguide acts like a conical guide and the HF beamwidth tracks θ₀ [Kolbrek 2008, verified: read; Batík OS-SE 2020, verified: read]. The effective coverage is thus "set by the angle of the guide" (Geddes, snippet only).

**The role of the throat region and early wall angle:**

The throat region sets how early the guide "takes hold" of the wavefront. In exponential horns, the slow early flare means the wavefront separates from guidance early (at high frequency the guide looks like a narrow-angle short cone), causing HF beaming. In a CE horn, Keele found the transition from exponential to conical should occur at a point where the conical section's solid angle is an optimum termination for the exponential, formulated as r = 0.95 sin(θ)/kc where kc is the cutoff wave number [Kolbrek 2008 eq. (27), verified: read]. This junction is at 5–11 inches from the throat in Keele's 90×40°, 60×40° and 40×20° designs [Keele 1975, verified: read]. In practice, Keele defines the coverage angle as the angle the straight walls subtend from this junction point, making the coverage angle prescription direct and unambiguous.

The consistent finding from our BEM experiments (6–8 kHz width tracks ~2× wall angle at 55–110 mm from the throat, 20–40% of arc) matches this theory: the early wall angle in the region before the rollback body sets HF coverage. Moving the wall-angle bump earlier to create a ~31° quasi-conical plateau gave flat ~70° H from 2.3–8 kHz — consistent with the conical body acting as the HF director.

**Mouth rollback and low-frequency diffraction:**

Batík's OS-SE paper explicitly states: "In a case of free standing waveguide, this profile should be terminated further to eliminate diffraction and reflection at the mouth. One possible solution is to extend the profile by connecting a segment of a clothoid, 'rolling' the profile naturally further back." [Batík OS-SE 2020, verified: read]. The R-OSSE paper BEM results confirm this: the rolled termination smoothens the frequency response and cleans the DI, primarily by reducing edge diffraction [Batík R-OSSE 2022, verified: read]. The JAX-BEM 2026 result independently confirms: "A smooth edge termination contributes the most to the improvements seen in the directivity plot" [Hipperson et al. 2026, verified: read]. 

The rolled/returned mouth lip therefore **controls diffraction ripple and near-field off-axis behaviour, not HF beamwidth**. HF beamwidth is set by the wall angle in the main body of the horn at 20–50% of the pre-roll arc. The mouth lip extends directivity control slightly toward lower frequencies and smoothens the response but cannot steer the core HF pattern.

---

## Q2: Construction laws for CD — formulas and reference cases

**OS and OS-SE (Batík) formula:**

Pure OS profile (infinite, zero throat opening angle):
> r_OS(z) = √(r₀² + z² tan²(α)) &nbsp;&nbsp;(Batík OS-SE eq. 1)

Generalized with non-zero throat opening angle α₀:
> r_OS(z) = √(r₀² + 2r₀z·tan(α₀) + z²·tan²(α)) &nbsp;&nbsp;(Batík OS-SE eq. 2)

Generalized with throat expansion factor k:
> r_GOS(z) = √((kr₀)² + 2kr₀z·tan(α₀) + z²·tan²(α)) + r₀(1–k) &nbsp;&nbsp;(Batík OS-SE eq. 3)

Note: for k=0 this collapses to a conical: r = r₀ + z·tan(α). The parameter α is the nominal coverage angle (half the included beamwidth); α₀ is the throat opening half-angle.

OS-SE adds a superellipse flare termination to the GOS base:
> r_OSSE(z) = r_GOS(z) + (sL/q)·[1–(1–(qz/L)^n)^(1/n)] &nbsp;&nbsp;(Batík OS-SE eq. 5, 0 ≤ z ≤ L)

Parameters: s = superellipse aspect ratio (amount of flare), n = exponent (controls how early the flare activates), q = truncation coefficient (~0.99-1.00). "The parameter n mainly affects how far from the throat the terminating term becomes effective." [Batík OS-SE, verified: read]

**R-OSSE (Batík 2022) — free-standing waveguide formula:**

Fully parametric, 9 design parameters: R (outer radius mm), a (nominal coverage angle half, deg), r0 (throat radius mm), a0 (throat opening half-angle, deg), k (throat expansion factor), r, m, b (shape modifiers), q (throat shape factor). The parametric equations use two conic sections each for x(t) and y(t) (0 ≤ t ≤ 1), with auxiliary constants c1 = (kr₀)², c2 = 2kr₀·tan(a₀), c3 = tan²(a) and arc length L derived from these.

Reference case (approximation of ST260): R=130mm, r0=12.7mm (1"), a0=7.5°, a=39°, k=1.8, r=0.3, b=0.3, m=0.8, q=3.7. Result: 260mm wide, ~80mm long. BEM-verified with ABEC/ABEC, 100 frequency points 200Hz–20kHz, free-standing, 5mm wall [Batík R-OSSE 2022, verified: read].

**Effect of k (throat expansion factor) on directivity:**
"By adjusting this value a desired DI slope towards high frequencies can be set, trading a gently rising DI for overall smoothness and a mildly higher throat impedance." BEM results shown for k=0.5, 1, 2, 4. [Batík R-OSSE 2022, verified: read]

**Keele CE horn construction and K formula:**

The CE horn joins an exponential (or hyperbolic-exponential) throat to a conical body, with an added secondary mouth flare correcting midrange narrowing. Construction rule:
- Throat: exponential with T = 0.6 (hyperbolic-exponential), cutoff fc = 360 Hz
- Transition to conical at radius r = 0.95 sin(θ)/kc (Kolbrek eq. 27 citing Keele)
- Conical body: straight walls at the desired coverage half-angle
- Mouth flare: last ~1/3 of conical moved outward to ~double the included angle — "decreases the acoustic source size in the frequency range of midrange narrowing" [Keele 1975, verified: read]
- Round→rectangular: 0.5" throat transition section, then straight sides angled at horizontal coverage angle [Keele 1975, verified: read]

**Keele mouth-size (K) formula — scope and application:**

> X = K / (θ × fT) &nbsp;&nbsp;where K = 2.5×10⁴ m·deg·Hz (= 1×10⁶ in·deg·Hz) &nbsp;&nbsp;(Keele 1975, eq. 1, verified: read)

X = mouth dimension (m), θ = included coverage angle (°), fT = intercept frequency (Hz) below which beamwidth widens. This applies to horns that "simulate a radially vibrating sphere section" including multicell, radial, and CE horns. Kolbrek re-derives: f_I = 25106/(x·θ) where x is in mm, θ in degrees [Kolbrek 2008, verified: read].

**Critical scope caveat:** This formula is for the minimum mouth size needed to maintain a given beamwidth down to fT. It is an empirically-derived sizing rule for one-parameter sphere-segment CD horns. It does not apply to OS waveguides, R-OSSE, Klangfilm spherical-wave horns, or any form where the coverage is set by wall angle rather than mouth size alone. [Keele 1975 explicitly scopes it; docs/knowledge/README.md confirms this is not universal.]

For independent H/V coverage: mouth aspect ratio A ≈ θ_H/θ_V (for angles ≤120°); intercept frequency ratio f_IH/f_IV ≈ (θ_H/θ_V)² [Keele 1975 eq. (3,4), verified: read; Kolbrek 2008 eq. (28–30), verified: read].

**Manta-Ray / independent H and V intercept (Henricksen & Ureda 1978):**

The Manta-Ray solves the CE horn's constraint of linked H and V intercepts. It allows independent specification by starting the vertical expansion behind the horizontal start, using a tall non-radial mouth geometry. It uses mouth flaring (same as CE) to avoid midrange narrowing, but "does not use radial expansion of walls" because "radial walls produced a 'waistbanding' effect, in which the horn lost much energy out to the sides in the upper midrange." [Kolbrek 2008, verified: read; Henricksen & Ureda 1978, snippet only]

**Waistbanding and how to avoid it:**

Waistbanding = mid-band narrowing at the transition frequency where the mouth is comparable to wavelength. It is a consequence of the sphere-segment model: "beam width narrows to 40–50% of its initial value" [Kolbrek 2008, verified: read]. Keele's secondary mouth flare (doubling the angle in the last third of the conical) is the CE horn fix. The Manta-Ray avoids radial walls that exacerbate it. In OS/R-OSSE designs, the gradually flaring profile combined with rollback tends to suppress this, but it can still appear in BEM results as a dip in coverage at mid-frequencies.

**Klangfilm spherical-wave horn construction:**

Formulae for the spherical-wave (Kugelwellen) horn [Kolbrek 2008 Part 2, verified: read]:
- Constant r₀ = c/(πfc) where fc is cutoff frequency  
- Throat height: h₀ = r₀ – √(r₀² – y₀²)  
- Area grows exponentially: h = h₀·e^(mx), m = 4πfc/c  
- Profile point: y = √(S/π – h²) = √(2r₀h – h²), xh = x – h + h₀

This explicitly allows the profile to fold back on itself (unlike tractrix), making rollback a natural feature. The wave-front area grows exponentially along the construction, which provides the loading properties. Coverage is set by the global profile shape, not a simple wall angle.

---

## Q3: Shape optimization with BEM/FEM

**What parameterizations worked:**

- **Bängtsson et al. 2003**: 8th-order Bernstein polynomials (many control points). Found that using raw mesh vertex displacements as design variables causes "disastrous ragged results." Used BFGS quasi-Newton + smoothing (filtering). Objective: minimize wave reflection (maximize transmission efficiency). 2D axisymmetric. [snippet only]

- **Udawalpola & Berggren 2007/2008 (IJNME)**: Gradient-adjoint, FEM Helmholtz. Explicit directivity requirements obtainable but with "substantial loss of efficiency." Manufactured a horn with near-perfect impedance matching from gradient-based design. [snippet only]

- **Morgans et al. 2008 (EGO)**: Spline parameterization (number of control points not confirmed from readable source), EGO/kriging surrogate replaces full BEM evaluations, targets **frequency-independent beamwidth** as the primary objective. BEM-evaluated. Published in Optimization and Engineering 9(4):361-374. [snippet only — DSpace failed]

- **Kasolis, Wadbro & Berggren 2012 (Struct. Multidisc. Optim.)**: Key methodological paper. Parameterize the boundary by angles between successive segments (= discrete curvature). Result: smooth updates that naturally prevent ragged designs. L-BFGS, FE Helmholtz. Explicit statement: "A common approach [handful of control points]... somewhat defies the purpose of numerical boundary shape optimization; searching through a design space spanned by a handful of design variables may as well be done manually by trial and error, and unexpected but successful shapes can easily be missed." [verified: read]

- **JAX-BEM 2026 (Hipperson, Hargreaves, Cox; Salford/Funktion-One)**: Differentiable BEM, L-BFGS, **spline control points for axial profile** as the design variables. Target: 70°H × 50°V, 4–18 kHz in log-spaced batches of 20 frequencies. MSE loss against dB targets relative to on-axis in in-coverage (−3 dB target ±35°H/±25°V) and out-of-coverage (−10 dB target). Quadrant used with symmetry, 948 elements. Key finding: "The most significant [change] is that the optimiser has arrived at a complex mouth shape... A smooth mouth termination has been added... A smooth edge termination contributes the most to the improvements seen in the directivity plot." Note: HF diffraction was the main improvement; in-coverage width was set primarily by the initial profile. Memory: ~100 GB for 20 frequencies per iteration at N=948. [verified: read]

**Which geometric DOFs control directivity:**

Across all studies: (1) The throat region and early body wall angle sets HF beamwidth; (2) Mouth termination/edge shape controls diffraction ripple and smoothness; (3) Body profile curvature controls mid-band directivity smoothness; (4) Mouth size + angle sets the LF intercept frequency. The JAX-BEM result showing the optimizer "added a complex mouth shape" and attributed most improvement to it is consistent: the starting conical shape already had ~correct width; the remaining improvement was diffraction/edge-ripple reduction.

**Number/placement of control points:**

Kasolis et al. argue against using "a handful of control points" and recommend curvature-parameterized designs with many DOF (but smooth by construction). JAX-BEM used spline control points on the axial profile (count not specified in the readable section). Bängtsson et al. used 8th-order Bernstein polynomials. No study directly reports a minimum sufficient number; the consensus is that the parameterization should be smooth-by-construction (curvature-based, spline with regularization) rather than sparse. Morgans' EGO approach uses a surrogate to manage the BEM evaluation budget, implying ≤~20 DOF are tractable with kriging.

---

## Q4: Compression-driver exit angle and throat matching

**Convention:** Throat opening angle is universally stated as a **half-angle** in the literature (a0 in Batík; θ₀ in Kolbrek/Geddes). The included angle is 2×a0. When Geddes says "6.5 degrees on B&C drivers" this is the half-angle (included = 13°). Batík uses a0 as the half-angle throughout.

**Geddes on matching (snippet only — diyAudio forum):** "For extreme accuracy, one wants the initial angle and radius of the waveguide to match the exit angle and radius of the driver." A mismatch (zero-slope OS entry vs ~6.5° conical B&C exit) causes more higher-order modes (HOMs). HOMs "are quite significant to audibility; minimizing them yields a far better sound quality."

**Batík R-OSSE paper (verified: read):** A conical duct of 20 or 40mm between driver and waveguide interface creates a reflection visible as resonances in throat impedance, but "there is virtually no impact on the normalized polar response." Effect is resonance (frequency response ripple), not beamwidth change. A ring insert that extends the waveguide to match driver phase plug eliminates the reflection.

**Throat size and HF ceiling:** From Kolbrek eq. (24) [verified: read]: fc ≈ 0.2c·sin(θ₀)/(π·rt). For 1" throat, 60° included → fc ≈ 862 Hz. Larger throats shift the cutoff upward and limit HF via HOMs: 1.5" driver on true CD guide → response dies 10–12 kHz; 2" driver → 9–10 kHz (Geddes, snippet only). For 36mm throat (≈1.4"), HOMs become significant around 10–11 kHz on a true CD guide at moderate wall angles. A wider-exit driver (wider a0) allows a wider OS angle for the same loading but brings forward HOM onset at smaller frequencies.

**Practical rule (from Batík R-OSSE example, verified: read):** Reference design uses a0 = 7.5° (half-angle, included = 15°) with a 1" throat. The analysis shows a0 = 0° or a0 = 15° are both viable; the throat opening angle affects loading smoothness but not far-field directivity significantly.

---

## Q5: Returned/rolled lip — practitioner and author experience

**Batík OS-SE 2020 (verified: read):** The OS-SE profile is designed for baffle-mounted (infinite baffle) use. For free-standing use, a rolled/cloth curve termination must be added: "one possible solution is to extend the profile by connecting a segment of a clothoid, 'rolling' the profile naturally further back." The R-OSSE (2022) is the analytical solution — same formula near the throat as OSSE, but with a full parametric rollback that folds the profile to a convenient free-standing shape.

**R-OSSE BEM (verified: read):** Results show smooth DI curves for the reference ST260 approximation. The throat expansion factor k controls DI slope. Throat opening angle affects loading and near-throat response. The rollback itself is the mouth termination; its main acoustic role is diffraction reduction at the edge. The paper confirms "virtually no impact on normalized polar response" from curvature discontinuity at the driver–waveguide interface, while confirming the rolled profile provides a smooth DI.

**Kolbrek on reversed-flare horns (verified: read):** Reversed flare horns (which include the R-OSSE family) are classified as "soft diffraction horns, contrary to Manta-Ray and other modern CD designs that rely on hard diffraction." This family includes WE horns (1920s) and Levy & Cohen patent (1950s). The concept: "the wave is allowed to expand in the vertical direction only, then the direction of expansion is changed." The result is wide coverage with controlled diffraction.

**JAX-BEM 2026 (verified: read):** The BEM optimizer independently converged on adding a "complex mouth shape" with "a smooth mouth termination... varying from a very large flare at 45° to a sharper termination in horizontal and vertical planes." The smooth edge termination contributed the most to directivity improvement — confirming that rollback/termination geometry primarily reduces diffraction ripple rather than changing the core beamwidth prescription.

**diyAudio snippets on R-OSSE rollback (snippet only — bot-blocked):** The rollback "shadows the edge of the waveguide and lowers the intensity of a reflection and/or diffraction from this edge, really smoothening the frequency response." Increasing rollback angle (from 180° to 220°) can "remove on-axis ripple and clean the listening window, though with potential trade-offs in lower frequencies." Short circular arc extensions "help remove on-axis ripple without affecting low frequencies as much."

**On rectangular/rolled mouths:** The Klangfilm spherical-wave construction naturally allows profile folding [Kolbrek 2008, verified: read; at-horns.eu experimental_morphs.md, read from local files]. In rectangular horns (Keele biradial), independent H/V wall angles are prescribed; the mouth aspect ratio follows θ_H/θ_V. Morphing to a rectangular or superellipse mouth (from the axisymmetric OS/R-OSSE base) is handled in ATH's morphing algorithm [Batík OS-SE eq., verified: read]: from a fixed z_f (the start of the morph) the profile is blended toward the target mouth outline r_M(φ) with rate γ. The morphing starts late (preserving the throat/body) and affects only the mouth transition region, consistent with the finding that the throat/body sets HF and the mouth sets LF and diffraction.

---

## Implications for Our Parameterization

**1. The parameterization is the binding constraint — the wall-angle schedule must be directly prescribed.**

All evidence agrees that HF beamwidth in the 6–8 kHz range is set by the wall angle in the zone 20–50% from the throat (pre-rollback). Our current approach of small perturbations on a fixed parent profile is bounded by that parent's angle schedule. The fix is to directly parameterize the wall-angle schedule θ_H(s) and θ_V(s) as functions of arc length in each plane, independent of each other, then generate the profile from that schedule. This is what Keele's CE horn does (explicitly prescribing θ_H and θ_V as the straight-wall angles), what Batík's k and a0 parameters approximate in the OS/R-OSSE family, and what gradient-based optimization implicitly discovers.

**2. Recommended parameterization structure for a CD-targeted rolled rectangular horn:**

a. **Throat region (0–15% of arc, ~0–20mm for a ~130mm radius horn):** Match a0 to the driver exit half-angle (for 36mm exit with conical duct, start at ~7–10°). Use OS-type curvature (r = √(r₀² + 2r₀z·tan(a₀) + z²·tan²(a)) with a as the nominal CD angle). This is the driver-loading region; fix it to match driver geometry and do not perturb it in search.

b. **Body region (15–70% of arc, ~20–90mm):** This is the HF-authority zone. Prescribe a monotonically rising or piecewise-linear wall-angle schedule. For CD at 70°H × 50°V, target ~35° half-angle in H and ~25° half-angle in V by ~40% of arc. Each plane gets its own schedule: θ_H(s) and θ_V(s) independently. Use 3–5 angle control points per plane in this region (following Kasolis et al. — curvature-based, not vertex displacement). The 31° quasi-conical plateau we found that gave flat ~70°H from 2.3–8 kHz is exactly this: a prescribed target angle reached early in the body.

c. **Late body / pre-rollback (70–85% of arc):** This region transitions toward 90° (the rollback tangent). Keep the wall angle rising smoothly; this region sets lower mid-frequency coverage (2–4 kHz). One or two angle control points here.

d. **Rollback / returned lip (85–100% of arc, the mouth proper):** This is a fixed termination feature. Its shape (rollback radius, angle span) affects diffraction ripple and the low-frequency intercept (Keele fT-equivalent). Keep the existing rollback construction; do not search this in HF optimization passes. It has negligible effect on 6–8 kHz beamwidth.

**3. H/V independence: prescribe both planes separately.**

The Klangfilm–Lamé family uses a Lamé (superellipse) cross-section that couples H and V profiles. Use Batík's morphing algorithm (or the construction contract in contracts/klangfilm_lame_hv.md) to blend from circular throat to rectangular mouth: set z_f at the end of the body region (~85% of arc); prescribe θ_H(s) ≠ θ_V(s) independently through the body. This directly achieves the asymmetric H/V targets (80×50°) without coupling them through a single OS angle.

**4. The Keele K-formula does not bound our design; mouth size does.**

For 80°H / 50°V at 900Hz/1kHz intercepts with our mouth dimensions (~260–360mm wide), Keele's formula gives x_H ≈ 2.5×10⁴/(80×900) ≈ 347mm, x_V ≈ 2.5×10⁴/(50×1000) ≈ 500mm. The V dimension (500mm) would require a larger horn. However, the K formula applies to sphere-segment CD horns (CE type), not OS/R-OSSE designs where the CD behavior relies on wall angle rather than pure mouth-size diffraction. Our rolled family is more constrained by the wall-angle schedule and can achieve lower intercept frequencies relative to its physical size (confirmed by our BEM showing flat 70°H from 2.3kHz), but the formula is a useful sanity check for whether HF-only CD is insufficient for coverage maintenance into the mid-range.

**5. Optimization should directly prescribe the target angle schedule, not perturb a parent profile.**

Treat θ_H(s) and θ_V(s) as the fundamental search variables (piecewise-linear, 3–5 knots each in the body zone). CMA-ES over {knot angles} in both planes, with the throat and rollback sections fixed. The profile is then integrated from the angle schedule. This follows the Kasolis et al. principle (curvature as design variable, inherently smooth) and directly targets the physics (wall angle in body sets HF coverage). 6–10 total search parameters per solve is tractable with the existing GPU BEM infrastructure.
