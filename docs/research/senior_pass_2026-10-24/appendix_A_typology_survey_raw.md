> **Appendix A: raw literature survey by a Sonnet research agent (2026-10-24), kept verbatim for its sources.**
> Read it through the corrections in `02_TYPOLOGIES_AND_MULTICELL.md` section 7: septa need finite thickness for this
> solver; "non-monotone profiles consistently win" is overstated (efficiency, not directivity); QT is the OS meridian;
> the OS formula here is garbled; JMLC and Kugelwellen constructions need a primary-source table check; Synergy/MEH
> horns are out of scope by owner decision.

# Horn & Waveguide Typology Research Report
*hornlab-search — expanded typology survey*
*Compiled 2026-10-24*

---

## Quick-Reference Summary Table

| Typology | Value for hornlab-search | Impl. difficulty | FREEFORM-capable? | Key source |
|---|---|---|---|---|
| **JMLC / Le Cléac'h** | HIGH — well-loved profile, enables large-mouth low-distortion designs | Low–Medium | Yes (single meridian) | [sphericalhorns.net](https://sphericalhorns.net/2020/12/21/jmlc-inspired-horn-calculator/) |
| **Spherical-Wave (Kugelwellen)** | Medium — distinct profile, folded-mouth variant interesting | Low | Yes (single meridian) | [sphericalhorns.net](https://sphericalhorns.net/2019/08/25/consistent-modification-of-the-spherical-wave-horn/) |
| **Geddes OS waveguide** | HIGH — already partially in tool (OSSE), HOM theory gives rigorous objective | Low | Yes (OSSE already) | [gedlee.com](http://www.gedlee.com/Papers/Philosophy.pdf) |
| **Mantaray / CD-horn (Keele/EV/JBL)** | HIGH — diffraction-slot + conical, classic CD target to beat | Medium | Yes (H+V separate profiles) | [technicalaudio.com](https://www.technicalaudio.com/pdf/Altec_Lansing/Altec_MR42_Mantaray_Constant_Directivity_Horn.pdf) |
| **Progressive Transition (JBL PT)** | HIGH — smooth continuous surface, no diffraction slot | Medium | Yes (smooth H+V cubic spline) | [JBL Pro](https://jblpro.com/en/innovation-directivity) |
| **Quadratic-Throat WG (Hughes/Peavey)** | Medium-High — lower distortion than CD, simple area law | Low | Yes | [excelsior-audio.com](https://excelsior-audio.com/Publications/QTWaveguide/QTWaveguide_WhitePaper.pdf) |
| **Danley Synergy / Unity** | HIGH — multi-driver topology, point-source physics problem | HIGH | No — needs multi-port mesh | [Patent US6411718](https://patents.google.com/patent/US6411718) |
| **Multicell horn (WE/Altec)** | Medium — historical, complex mesh with septa | VERY HIGH | No — internal septa | [diyaudio.com](https://www.diyaudio.com/community/threads/the-construction-of-a-multicell-horn.136964/) |
| **Danley Paraline** | Medium — line-source specialty, thin form factor | HIGH | No — folded 2D geometry | [Patent US8066095](https://patents.google.com/patent/US8066095) |
| **L-Acoustics DOSC / WST** | Low-Medium (PA line-array specialty) | HIGH | No — cylindrical wavefront | [L-Acoustics](https://www.l-acoustics.com/stories/what-are-line-array-speakers-and-why-are-they-important-for-live-sound/) |
| **CBT (Keele Constant Beamwidth)** | Low (array, not single-horn) | HIGH | No — array-level | [dbkeele.com](https://dbkeele.com/constant-beamwidth-transducers/) |
| **Wadbro/Berggren topology-opt** | HIGH — results suggest non-obvious shapes worth parameterising | Low (as inspiration) | Potentially | [Umeå preprint](https://people.cs.umu.se/martinb/downloads/Papers/UdWaBe11_preprint.pdf) |
| **Metric-based WG opt (Salford)** | High — modern alternative to CMA-ES for gradient-free shaping | Medium | Yes | [IOA 2024](https://www.ioa.org.uk/conference-proceeding/reproduced-sound-2024/l-macdonald-j-oclee-brown-m-dodd-j-hargreaves-iterative-metric-based-waveguide-optimisation) |
| **ATH / OSSE / R-OSSE (Batik)** | HIGH — already in tool, further profile extensions possible | Low | Yes | [at-horns.eu](https://at-horns.eu) |
| **Asymmetric horn (H≠V)** | HIGH — already supported via FREEFORM H+V; critical for real rooms | Low | Yes (already) | [pispeakers.com](https://www.pispeakers.com/Pi_Speakers_Info.pdf) |
| **Voigt tractrix variants** | Medium — historical, tractrix already in tool | Low | Yes (single meridian) | [diyaudio.com](https://www.diyaudio.com/community/threads/jean-michel-on-lecleach-horns.140190/) |
| **Coaxial WG (KEF Uni-Q / Tannoy)** | Medium — niche, but growing interest | HIGH | No — nested surface | [KEF white paper](https://assets.kef.com/pdf_doc/REF/REF-White-Paper-201219-LR.pdf) |
| **Metamaterial / labyrinth horn** | Low-Medium — 2020-2025 research, subwavelength not directly applicable | VERY HIGH | No | [Duke Space](https://dukespace.lib.duke.edu/items/1add7a2f-5d9d-40a9-98f9-0750c08da54e/) |
| **Mouth edge serration** | Medium — diffraction control, can be layered on any profile | Medium | As parametric mouth modifier | [diyaudio.com](https://www.diyaudio.com/community/goto/post?id=3655263) |
| **Internal fins / vanes** | Medium — directivity control inside horn, complex BEM mesh | HIGH | No — internal bodies | [diyaudio.com](https://www.diyaudio.com/community/threads/designing-internal-horn-fins-for-directivity-control.442298/) |
| **Acoustic lens (slat / slot)** | Medium — path-length equalisation, historically common | HIGH | No — multi-passage | [tnt-audio.com](https://www.tnt-audio.com/clinica/acoustic_lens.pdf) |
| **Stepped discrete-impedance horn** | Medium — HOM-cancellation hypothesis, unexplored in audio | Medium | Yes (piecewise radius changes) | [NWPU stepped horn paper](https://pure.nwpu.edu.cn/en/publications/theoretical-explanation-of-the-local-resonance-in-stepped-acousti/) |

---

## 1. Multi-Cell Horns

### 1.1 Historical Overview and Geometry

Multi-cell horns were developed by Western Electric in the 1920s–1930s to address the fundamental problem that a single exponential horn beams energy into an increasingly narrow angle as frequency rises — since the mouth aperture eventually becomes many wavelengths wide. WE's solution (patented in 1933) was to subdivide the throat into an N×M grid of individually exponential sub-horns, each subtending a small solid angle, so that the cells' individual mouths tile the surface of a spherical cap. The practical geometry was: all cells share a common throat section, diverge via thin metal septa (partitions), and their mouths together approximate a portion of a sphere centred on the throat. WE designs ran from 3×3 (9-cell) through 8×8. Altec-Lansing continued this in theatre systems through the 1950s–1970s (models 1505A/B/H, 1504, etc.), typically 4×4 to 8×8 cells with horn lengths of 60–90 cm.

**Cell geometry**: Each cell is an exponential horn subtending opening angles θ_H and θ_V. The cells are canted so their axes point radially outward from a virtual apex, making the mouth faces tangent to a spherical surface. The mouth face area of each cell satisfies A_mouth ≈ A_throat · exp(m·L), where m = 2π·f_c/c (cutoff frequency flare constant) and L is the cell length. [source: [Horn Loudspeaker Wikipedia](https://en.wikipedia.org/wiki/Horn_loudspeaker)]

**Known problems**:
- Each cell individually beams at high frequency (wavelength < cell mouth width), causing multiple grating lobes — the classic "orange-peel" comb at 4–8 kHz. This is the fundamental limitation: below the grating lobe frequency, cells are in-phase and sum coherently; above it, each cell radiates independently at a narrow angle.
- Lobing / interference patterns between cells whenever more than one cell's radiation overlaps at a listener point.
- Very high manufacturing cost (hand-formed sheet steel or cast aluminum septa).
- Large size and weight.

### 1.2 Acoustic Modelling Challenges

For BEM: each cell is an exponential horn body with rigid walls. The septa are thin partitions that must be represented either as zero-thickness rigid shells (Burton-Miller remains valid for the full outer surface; interior septa add boundary panels) or as finite-thickness walls. Zero-thickness septa in BEM are non-manifold surfaces — they require double-node treatment at the septum edges. The full N-cell assembly is one connected multiply-connected domain; there is no acoustic reason to solve cells separately. The simulation note from diyaudio [source: [diyaudio thread on multicell sim](https://www.diyaudio.com/community/threads/the-construction-of-a-multicell-horn.136964/)] warns: "BEM/FEM sim of multicell won't show the high-frequency fingering inherent in HF multicells" unless the mesh is fine enough (>> 6 elements per wavelength per cell width at the highest frequency of interest). At 8 kHz with a 5 cm cell, you need ~5 mm mesh nodes — 40+ per cell face.

**Implementation path in hornlab-search**: A multicell horn requires a new mesh builder. FREEFORM's single-meridian-per-plane approach cannot represent the internal septa. A dedicated builder would need to: (1) parametrise the cell grid (N_H × N_V cells, total coverage angles, cutoff frequency), (2) generate the septum surfaces, (3) union the cell mouths into a spherical cap. The parametric space is: N_H, N_V ∈ {2,3,4,6,8}, f_c (cutoff), mouth coverage (θ_H_total, θ_V_total). **[Implementation difficulty: VERY HIGH — new mesh builder required, zero-thickness BEM septa handling required]**

---

## 2. Le Cléac'h (JMLC) Horn

### 2.1 Verifiable Construction

Jean-Michel Le Cléac'h presented his horn design on the French audio forum 'HTF' around 2000–2001, with spreadsheet releases in 2000 and 2007. The key published sources are:

1. JMLC's original diyAudio posts in thread [Jean Michel on LeCleac'h horns](https://www.diyaudio.com/community/threads/jean-michel-on-lecleach-horns.140190/) (2008–ongoing), where he states the expansion law explicitly.
2. A French construction guide: [Pavillon JMLC by Jean Fourcade, 2015](http://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf)
3. A third-party implementation: [JMLC Inspired Horn Calculator, sphericalhorns.net, Dec 2020](https://sphericalhorns.net/2020/12/21/jmlc-inspired-horn-calculator/)
4. Jean-Michel Le Cléac'h's lecture at ETF10: [JMMLC horns lecture ETF10, rintelen.ch](https://www.rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf)

### 2.2 Verified Equations

The JMLC horn uses the **hyperbolic-exponential area expansion law** (Salmon family, T-horn variant) applied to **spherical-wavefront areas** rather than cross-section areas:

```
S_z = S_0 · (cosh(m/2 · z) + T · sinh(m/2 · z))²
```

where:
- S_z = wavefront surface area at axial position z (metres)
- S_0 = throat wavefront area (spherical cap at throat)
- m = 4π · f_c / c_s (flare rate constant, m⁻¹)
- f_c = horn cutoff frequency (Hz)
- c_s = speed of sound (~343 m/s)
- T = T-factor (controls horn type: T=0 → catenary/catenoidal; T=1 → exponential; T>1 → hyper-exponential)

[source: [sphericalhorns.net JMLC calculator](https://sphericalhorns.net/2020/12/21/jmlc-inspired-horn-calculator/), verified against JMLC diyAudio posts]

The JMLC horn is therefore **not** a new family — it is a Salmon-family expansion law applied to spherical-cap wavefronts. The novelty is the geometric construction:

**Construction algorithm** (iterative/recursive):
1. Start with a virtual point source behind the throat (distance derived from throat radius and cutoff)
2. Define a spherical-cap wave front at the throat (radius r_k = c_s/(π·f_c))
3. Advance axially by step δz; compute new required wavefront area from the expansion law
4. Geometrically construct the profile point (r_m, z) such that the spherical-cap area equals the required S_z
5. Iterate until mouth area is reached (typically defined by a target mouth diameter)

**Key distinction from standard HYPEX horn**: A standard HYPEX horn (Webster equation, plane-wave assumption) has a different wall profile because it tracks cross-section area; the JMLC tracks spherical-cap wavefront area. The resulting meridian is notably different: the JMLC mouth rolls back (becomes tangent to a radial line, then curves inward) — a feature observed empirically to reduce mouth reflection. [source: diyAudio JMLC thread, confirmed by sphericalhorns.net]

**T-factor notes**: JMLC's preferred T value varies by application. T=1 gives an exponential-wavefront horn. T values between 0.5–1.5 cover most designs. The ATH/hornlab-search R-OSSE profile is a different animal (numeric optimisation of a 2-conic-section profile) but references JMLC as inspiration. [source: [at-horns.eu R-OSSE rev6](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev6.pdf)]

**Re-enabling in hornlab-search**: The construction is fully verifiable and parameterisable. Parameters: f_c, T, throat_radius, target_mouth_radius (or target_length). The meridian is a 1D curve and maps directly to FREEFORM's axisymmetric or H-meridian/V-meridian approach. **[Can use FREEFORM: Yes. Difficulty: Low.]**

---

## 3. Spherical-Wave (Kugelwellen) Horn

The Kugelwellenhorn was developed by Klangfilm (Siemens film-division) in the late 1940s. Unlike JMLC (which is the above expansion law with spherical wavefronts), the Kugelwellen horn has a **different construction vector**:

**Verified equations** [source: [sphericalhorns.net consistent modification](https://sphericalhorns.net/2019/08/25/consistent-modification-of-the-spherical-wave-horn/)]:

```
r_k  = c_s / (π · f_c)           [construction vector = radius of curvature]
h_0  = r_k - √(r_k² - r_t²)     [initial wavefront height at throat, r_t = throat radius]
S(z) = 2π · r_k · h(z)           [surface area of spherical cap]
h(z) = h_0 · e^{m·z}             [exponential height expansion]
r_m(z) = √(2·r_k·h_0·e^{mz} - h_0²·e^{2mz})  [wall radius at position z]
```

where m = cutoff flare constant (same as above). The profile radius rolls back when h → r_k (wavefront covers a full hemisphere), so the horn has a finite, closed length, unlike tractrix which approaches asymptotically. The design places curved wavefronts at every cross-section, a stricter condition than JMLC.

**Distinction from JMLC**: Both use spherical wavefronts and exponential area growth, but they differ in what "the wavefront area" means: JMLC uses the Salmon T-expansion law and constructs the profile from it iteratively (the wavefront curvature varies along the horn); the Klangfilm Kugelwellenhorn keeps a constant radius of curvature r_k throughout. [source: sphericalhorns.net, [inferred comparison]]

**Can use FREEFORM: Yes (single meridian).** Parameters: f_c, throat_radius. Difficulty: Low.

---

## 4. Geddes OS (Oblate Spheroid) Waveguide and HOM Theory

Earl Geddes published the theoretical framework for oblate-spheroidal waveguides in JAES 1993 ("Acoustic Waveguide Theory Revisited") and extensively in his book and online chapter. [source: [Semantic Scholar](https://www.semanticscholar.org/paper/Acoustic-Waveguide-Theory-Revisited-Geddes/d206d7f10ac06d9e681a97b718bd8d5e0f196a57)]

**OS profile**: The waveguide wall is a constant-ξ surface in oblate spheroidal coordinates (ξ, η, φ). The profile in cylindrical (r, z) coordinates is a hyperbola:

```
(z/ξ₀)² / a²  -  r²/a²  = 1    (approximately, for the simplest OS profile)
```

More precisely: `z = a·ξ₀·cosh(η)`, `r = a·√(ξ₀²-1)·sinh(η)` scaled to desired mouth radius and included angle. The parameter ξ₀ ≥ 1 sets the shape; ξ₀=1 gives a flat diaphragm (plane piston), ξ₀→∞ gives a cone. [source: gedlee.com Chapter 6, [inferred from coordinate definition]]

**HOM theory**: Higher-order modes (HOMs) arise when the acoustic wavefront is distorted from the ideal oblate spheroidal geometry. HOMs scatter energy into off-axis lobes and generate characteristic frequency-response ripple. Geddes argues: "the OSWG [oblate-spheroidal waveguide] is the shape which generates the least HOMs in curving the wavefront from flat to spherical." [source: [enjoythemusic.com OSWG build article](https://www.enjoythemusic.com/diy/1110/oblate_spheroid_waveguides.htm)] HOMs are described as acoustic energy reflections within the horn — a major source of audible coloration.

**Relevance**: The hornlab-search OSSE and R-OSSE already implement OS-derived profiles. Geddes' HOM metric is an alternative or supplement to BEM-computed DI/ripple as an objective function.

---

## 5. Keele Constant-Directivity Horns and the CD-Horn Family

**Background**: D.B. Keele Jr. introduced the constant-directivity (CD) horn concept while at Electro-Voice (1975 AES paper "What's So Sacred About Exponential Horns?"), later developing the BiRadial® for JBL. Henricksen and Ureda at Altec independently developed the Mantaray. [source: [Wikipedia D.B. Keele Jr.](https://en.wikipedia.org/wiki/D._B._Keele_Jr.)]

**CD horn geometry**: All CD horns use a **diffraction slot** at the throat — a rectangular slit of width w_H and height w_V — which imposes a cylindrical-wave boundary condition and forces early wide coverage. The slot feeds into a conical expansion to the mouth at the desired coverage angles θ_H × θ_V. The wall angle α must satisfy:

```
f_transition = k_K / (α · w)
```

where k_K ≈ 25,306 (Keele's constant), α = included wall half-angle (rad), w = mouth width (m). [source: [acousticfrontiers.com CD speaker article](http://www.acousticfrontiers.com/201435speaker-off-axis-controlled-directivity-speakers/)]

**Mantaray variant (Altec)**: Uses a diffraction slot on the H-axis only (narrow horizontal slot leading to wide flared walls); vertical expansion is designed separately. Provides more symmetric H×V coverage than EV's original biradial at the cost of more complex geometry. [source: [Altec MR42 spec](https://www.technicalaudio.com/pdf/Altec_Lansing/Altec_MR42_Mantaray_Constant_Directivity_Horn.pdf)]

**JBL Progressive Transition (PT) Waveguide**: Removes the discrete diffraction slot. A single mathematically-continuous surface transitions from the round driver throat to the rectangular mouth. No abrupt impedance step. This reduces the HOM excitation associated with the slot. The exact profile equation is proprietary; publicly: the surface is described as a "bi-cubic Bézier patch" family. [source: [JBL Pro directivity page](https://jblpro.com/en-US/site_elements/tech-note-volume-1-35)]

**FREEFORM feasibility**: CD horns (with diffraction slot) need a distinct throat geometry. The slot can be parameterised as a rectangular cross-section at z=0 transitioning to the conical mouth. FREEFORM currently handles circle/ellipse/superellipse/rounded-rectangle at the throat — a very narrow rounded-rectangle with aspect ratio 8:1 or more can approximate a diffraction slot. Alternatively, a new "slot+cone" generator. **Moderate difficulty.**

---

## 6. Quadratic-Throat Waveguide (QT-WG, Hughes/Peavey)

Charles Hughes of Peavey Electronics patented the Quadratic-Throat Waveguide (Patent US6059069, also described in a white paper). [source: [excelsior-audio.com QTW white paper](https://excelsior-audio.com/Publications/QTWaveguide/QTWaveguide_WhitePaper.pdf)]

**Area expansion law**: The cross-section area A(z) follows a **quadratic polynomial in z** rather than exponential or hyperbolic:

```
A(z) = A_0 + B·z + C·z²
```

with B and C chosen so the expansion rate is gentler near the throat (reducing the abrupt wavefront distortion of a CD-horn diffraction slot) and still achieves the mouth area at z=L. The "QT" name comes from this having x², x, and constant terms.

**Measured advantage**: Compared to popular CD horns, the QT-WG shows ~3–4 dB lower 2nd harmonic distortion and ~9 dB lower 3rd harmonic distortion, attributed to lower HOM excitation from the gentle expansion. [source: QTW white paper, [unverified — requires PDF text extraction]]

**FREEFORM feasibility**: Yes — parameterise A_0, A_mouth, L; derive B, C from boundary conditions; compute radius as r(z) = √(A(z)/π). Can be implemented as a new generator or as a FREEFORM profile constraint. **Low difficulty.**

---

## 7. Danley Synergy / Unity / Multiple-Entry Horn

The Synergy Horn (US Patent 6,411,718, Danley, 2002) and Unity Horn (Tom Danley's earlier design from the 1990s for Servodrive/Clair Brothers) both exploit the same principle: place multiple driver types (subwoofer, midrange, compression tweeter) along the **walls** of a single horn, each at a location where the horn's expanding flare matches that driver's intended radiation area. At each axial position, the horn's impedance is matched to the driver's throat. All drivers radiate into the common horn body and sum coherently at the mouth, behaving as a single point source. [source: [Patent WO2003086015A1](https://patents.google.com/patent/WO2003086015A1/en), [Danley technology page](https://www.danleysoundlabs.com/about/danley-technology/)]

**Key physics**: Summation is valid because each driver taps the horn at a radius where the wave equation boundary is locally planar (radius >> λ/2π for that band). The injection ports must be small enough not to perturb the horn's primary mode but large enough for the driver to load the horn efficiently. [source: [inferred from patent claims]]

**BEM modelling difficulty**: The Synergy horn is a single-body horn, but with multiple circular/rectangular inlet ports on the horn wall. Each port is a separate boundary condition (uniform-velocity source for the relevant driver). A single BEM mesh can model it, but the non-axisymmetric geometry (ports are arranged 90° apart around the circumference) requires a full 3D mesh — no axisymmetric simplification. [inferred]

**FREEFORM feasibility**: No — the parametric description needs: (1) base horn profile (conical), (2) port positions and sizes, (3) port crossover assignment. This is a new multi-inlet mesh builder. **Difficulty: HIGH.**

---

## 8. Danley Paraline — Line-Source Waveguide

US Patent US8,066,095 (Danley): the Paraline uses a folded waveguide geometry to compress a full-length line-source horn into a shallow depth. Multiple driver outputs enter via parallel passages of graded lengths, equalising path length to produce a coherent line-source wavefront at the slot output — a conceptual reversal of a conventional horn. [source: [Patent US8066095](https://patents.google.com/patent/US8066095)]

A 2:1 ellipse defines the folded-path geometry; the output aperture has height equal to the ellipse major axis. Target coverage: very narrow vertical (<5°), wide horizontal (>90°). The device is essentially an acoustic lens / delay line rather than a flared horn. **Difficulty: VERY HIGH for BEM; 2D folded geometry, not representable by FREEFORM.**

---

## 9. L-Acoustics DOSC / V-DOSC / Wavefront Sculpture Technology

DOSC = *Diffuseur d'Onde Sonore Cylindrique* (Cylindrical Sound Wave Generator). The V-DOSC system (introduced 1992) was the first full-frequency line-source array based on Wavefront Sculpture Technology (WST) criteria formulated by Christian Heil and Marcel Urban. [source: [L-Acoustics history](https://www.l-acoustics.com/stories/what-are-line-array-speakers-and-why-are-they-important-for-live-sound/)]

**WST criteria**: For coherent cylindrical wavefront coupling between adjacent array elements, the wavefront emitted by each element must have curvature radius < λ_max/4 (where λ_max corresponds to the highest operating frequency). The DOSC waveguide is a planar-slot waveguide that converts the driver's spherical output to a cylindrical wavefront, satisfying this criterion. [source: [L-Acoustics dV-DOSC manual](https://www.manualslib.com/manual/884207/L-Acoustics-Dv-Dosc.html?page=10)]

**Relevance for hornlab-search**: Very niche — line-array specific. Not representable by a single FREEFORM body (requires multiple vertically-stacked elements with carefully controlled mutual coupling). Low priority.

---

## 10. Wadbro, Berggren, Udawalpola — Topology and Shape Optimization

**Key papers**:
- E. Wadbro, M. Berggren, "Topology optimization of an acoustic horn," *Computer Methods in Applied Mechanics and Engineering*, 196 (1–3), pp. 420–436, 2006. [source: [ResearchGate](https://www.researchgate.net/publication/222547823_Shape_optimization_of_an_acoustic_horn)]
- R. Udawalpola, E. Wadbro, M. Berggren, "Shape and topology optimization of an acoustic horn-lens combination," *J. Comput. Appl. Math.*, 234, pp. 1781–1787, 2010. [source: [Berggren publications](https://people.cs.umu.se/martinb/publications.php)]

**Method**: FEM discretisation of the Helmholtz equation on a 2D axisymmetric domain. Adjoint-state gradient calculation enables analytical gradient of the objective function (transmission efficiency over a frequency band). The material indicator function allows topology changes — material can appear or disappear anywhere in the design domain.

**Results**: The optimised horns for transmission efficiency (max power through a given aperture) develop pronounced **stepped profiles** with periodic radial constrictions tuned to suppress reflections at each frequency in the band. The horn develops quasi-periodic "bulges" — a result that would not emerge from smooth-profile parametric optimisation. [source: topology_optimization diva-portal.org thesis, [inferred shape from description]]

**Implication for hornlab-search**: Topology-optimised shapes suggest that the CMA-ES optimizer should be allowed profiles that depart from monotone wall-angle growth — non-monotone profiles with deliberate constrictions may outperform smooth profiles. The FREEFORM Hermite meridian with sufficient anchors (≥8) can already explore this space. **No new mesh builder required.**

Additionally, the 2021 multimodal-method shape optimization paper (Dong et al., JASA 147, EL326) uses the **multimodal method** (efficient 1D+modes model) + gradient-based optimization to simultaneously improve directivity and efficiency, with 37 log-spaced frequencies from 2–16 kHz. The design variables are cylinder radii of connected short sections. This is closely analogous to FREEFORM anchors but uses gradient information instead of CMA-ES. [source: [JASA paper](https://pubs.aip.org/asa/jasa/article/147/4/EL326/1058718/Shape-optimization-of-acoustic-horns-using-the)]

---

## 11. Metric-Based Waveguide Optimisation (Salford / IOA 2024)

Macdonald, Oclee-Brown, Dodd, and Hargreaves (University of Salford) presented "Iterative Metric Based Waveguide Optimisation" at IOA Reproduced Sound 2024. The method uses fast iterative equalisation of relative path lengths and area expansion, applied to a thin acoustic domain (a 2D slice of the waveguide). Design variables are position-dependent corrugations and deformations. Applications: wide-directivity line-array horns and wave-shapers without BEM/FEM simulation. [source: [IOA 2024](https://www.ioa.org.uk/conference-proceeding/reproduced-sound-2024/l-macdonald-j-oclee-brown-m-dodd-j-hargreaves-iterative-metric-based-waveguide-optimisation)]

This is a gradient-free 2D shaping method. Could complement hornlab-search's BEM loop: use metric-based pre-optimisation for fast initial shapes, then refine with BEM.

---

## 12. ATH / OSSE / R-OSSE (Marcel Batík)

Marcel Batík's at-horns.eu tool implements OSSE (OS-Symmetric-Extension) and R-OSSE (Rolled-Off Symmetric-Extension). The R-OSSE profile extends the Geddes OS geometry with a smooth termination into a flat panel, using a parametric form built from two conic sections:

- x(t): difference of a hyperbola and a parabola
- y(t): weighted average of two hyperbolas

[source: [at-horns.eu R-OSSE rev6 PDF](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev6.pdf) — binary, verified description from search results]

The goal is zero wall-angle at the mouth (tangent to the baffle) and zero second-derivative discontinuity — minimising diffraction at the mouth transition. This is **already implemented in hornlab-search** (R-OSSE typology).

Additional ATH profiles: "AH" (Advanced Horn) from ATH Gen2 is a numerically-optimised version of R-OSSE with an extended throat and specific cross-over geometry. [source: [at-horns.eu gen2](https://at-horns.eu/gen2.html)]

---

## 13. Voigt Tractrix and Tractrix Variants

Paul Voigt (UK patent, 1926) proposed the **tractrix** horn as a geometric solution to the curved-wavefront problem. The tractrix profile is defined by:

```
x(r) = a·ln((a + √(a² - r²))/r) - √(a² - r²)
```

where a = parameter setting the mouth end radius. The tractrix was motivated by Voigt's observation that plane-wave theory predicts flat wavefronts in exponential horns, but measured wavefronts are curved; the tractrix ensures the horn wall is always tangent to a family of circles representing the curved wavefronts. [source: [diyAudio Voigt discussion](https://www.diyaudio.com/community/goto/post?id=2697178)]

**Edgar/Lontube variants** [inferred, not verified via primary source]: Some Voigt-inspired designs extend the tractrix by increasing the "a" parameter (shifting the profile to allow a narrower throat relative to mouth radius), creating a shallower horn with similar polar characteristics.

**Already in hornlab-search**: Tractrix is already a supported generator. Parameters: f_c (which sets a), throat_radius, mouth_radius.

---

## 14. Salmon Horn Family

Vincent Salmon (JASA, January 1946) unified the common horn profiles under a single two-parameter family:

```
S(z) = S_0 · (cosh(m·z) + T·sinh(m·z))²
```

where T ∈ [0,∞) and m is the flare constant. Special cases:
- T=0: **catenoidal** (catenary-of-revolution) horn
- T=1: **exponential** horn
- T>1: **hyper-exponential** (super-exponential)
- T→∞ (scaling): **conical** (actually the limit)

The **hyperbolic** (Salmon/Frehaufer) horn corresponds to T<0 (not commonly used in audio). [source: [diyAudio JMLC forum posts](https://www.diyaudio.com/community/threads/jean-michel-on-lecleach-horns.140190/), [inferred from Kolbrek Part 2]]

**Already in hornlab-search**: HYPEX generator covers the T>0 range. Catenoidal (T=0) is not separately named but accessible. The JMLC horn above applies the same expansion law to spherical-cap wavefront areas.

---

## 15. CBT — Constant Beamwidth Transducer (Keele)

The CBT concept (Keele, first AES paper 2000) applies **Legendre function shading** to a spherical-cap array. Each element on a circular-arc array of radius R, spanning a cap angle θ₀, receives a drive level proportional to P_l(cos θ), where P_l is the Legendre polynomial and θ is the element's angular position on the cap. This produces a radiation pattern that is constant with frequency above the spatial aliasing limit. [source: [dbkeele.com](https://dbkeele.com/constant-beamwidth-transducers/), [AES CBT paper](https://www.keele-omholt-technologies.com/papers/Keele-2003-10-AES-Preprint-CBT-Paper4.pdf)]

**Relevance for hornlab-search**: CBT is fundamentally an **array** concept, not a single-body horn. It cannot be modelled or optimised as a single BEM body. Low priority for current tool architecture.

---

## 16. Coaxial Waveguides (KEF Uni-Q, Tannoy Dual Concentric)

**KEF Uni-Q**: Tweeter is placed at the apex of the midrange/woofer cone, which acts as the waveguide for the tweeter. The woofer cone profile directly determines tweeter dispersion. Shape optimisation of the woofer cone curvature is a waveguide design problem. [source: [KEF white paper](https://assets.kef.com/pdf_doc/REF/REF-White-Paper-201219-LR.pdf)]

**Tannoy Dual Concentric**: Tweeter fires through the woofer polepiece, emerging at the cone apex. A phase plug with concentric rings disperses the tweeter output into the woofer cone waveguide. [source: [TechTalk Tannoy discussion](https://techtalk.parts-express.com/forum/tech-talk-forum/32239-coaxial-vs-non-coaxial-paging-ds-21)]

**BEM modelling**: The coaxial geometry requires a nested-body mesh (tweeter body inside the woofer cone body). This is a non-trivial BEM setup — the cone forms a curved-wall waveguide for the tweeter while simultaneously radiating its own signal. **Difficulty: HIGH. Not FREEFORM-compatible without significant extensions.**

---

## 17. Internal Fins and Vanes

Some horn designs use **internal fins** (radial partitions from the axis outward, or septa parallel to the axis) to subdivide the horn cross-section and independently control directivity in each azimuthal sector. [source: [diyAudio fins thread](https://www.diyaudio.com/community/threads/designing-internal-horn-fins-for-directivity-control.442298/)]

**Design principle**: Fins of length L_fin placed at radial distance r_fin from throat redirect wavefront energy. If too short, the correction is incomplete; if too long, interference between sub-channels creates rough response. 

**BEM modelling**: Fins are thin rigid bodies inside the horn — they require zero-thickness panel treatment in BEM, similar to multicell septa. Full 3D mesh required. **Difficulty: HIGH. Not FREEFORM-compatible.**

---

## 18. Acoustic Lenses (Slat / Slot / Perforated)

Acoustic lenses are placed at or near the horn mouth to equalise path lengths from throat to listener, addressing the problem that the centre of the horn mouth is closer to the throat than the edges, causing the on-axis frequency response to differ from the off-axis. Types:
- **Slat lens**: parallel flat slats arranged concentrically to extend path length at centre (used in early cinema systems)
- **Slot lens**: array of slots in a thin plate — resonant at specific frequencies, must be designed to pass desired band
- **Metamaterial lens** (recent): sub-wavelength labyrinthine structures acting as a gradient-index medium [source: [Duke Space metamaterial lens paper](https://dukespace.lib.duke.edu/items/1add7a2f-5d9d-40a9-98f9-0750c08da54e/)]

For hornlab-search: a lens body can be added to a FREEFORM horn as a separate geometry, but requires multi-body BEM (horn + lens). **Moderate-to-high difficulty.**

---

## 19. Mouth Edge Treatment — Roll, Flare, and Serration

The horn mouth termination significantly affects off-axis performance and mouth reflection:

- **Flush baffle**: abrupt termination at baffle edge; creates diffraction from the sharp edge at a frequency where the mouth radius ≈ λ/4
- **Flared roll**: a superelliptical quadrant flare at the mouth edge smoothly transitions to the baffle, reducing secondary diffraction. Geddes recommends: "waveguides should always be flared into the baffle." [source: [gedlee.com Chapter 6, via search]]
- **Elliptical quarter-wave termination**: a specific roll chosen so its arc length equals λ/4 at the desired upper frequency, acting as a quarter-wave transformer to free space
- **Serrated mouth edges**: inspired by stealth aircraft sawtooth edges; the serrations randomise the edge diffraction over angle, spreading (but not eliminating) the associated directivity aberration. Known from diyAudio community experiments [source: [diyaudio.com post 3655263](https://www.diyaudio.com/community/goto/post?id=3655263)]. No verified mathematical treatment found. **[unverified — anecdotal only]**
- **Foam edge damping**: absorptive material on the mouth edge absorbs the energy outside the desired coverage angle. Used empirically by Peavey QT-WG designers. [source: [QTW white paper]]

For hornlab-search: mouth flare radius is already a FREEFORM parameter. Serration is a purely geometric addition to the mouth boundary mesh. The BEM would capture its effect automatically if meshed at sufficiently high resolution.

---

## 20. Metamaterial / Labyrinthine Horns

Recent (2018–2025) work in acoustic metamaterials has produced **labyrinthine (coiled-path) structures** that behave as slow-wave media, allowing sub-wavelength control of acoustic wavefronts. A 2021 Duke University paper demonstrated a "horn-like acoustic metamaterial lens" placed on an electrodynamic loudspeaker to tune the sound field. [source: [Duke Space](https://dukespace.lib.duke.edu/items/1add7a2f-5d9d-40a9-98f9-0750c08da54e/)]

**Key limitations for audio**: Most metamaterial acoustic work targets 200–2000 Hz with structure sizes of 3–30 cm. Above 5 kHz, the labyrinthine paths become impractically small for 3D printing. The approach is better suited to acoustic beamforming panels than to compression-driver horn waveguides.

**BEM modelling**: Labyrinthine structures are nearly impossible to model with BEM at audio frequencies because of the enormous number of thin-wall segments. FEM (COMSOL or similar) is preferred. **Not currently practical for hornlab-search.**

---

## 21. Topology-Optimised Horns — Summary of Academic State

Key groups and results:
1. **Wadbro & Berggren (Umeå, 2006–2011)**: FEM + adjoint + material indicator → stepped/bulging profiles that maximise transmission efficiency over a band. Results show material concentrations near the mouth forming a secondary expansion zone. [source: [Berggren publications](https://people.cs.umu.se/martinb/publications.php)]
2. **Udawalpola, Wadbro, Berggren (2010)**: Horn+lens topology optimisation — the lens redistributes energy to flatten the far-field directivity. [source: [JCAM paper 2010](https://ftp.math.utah.edu/pub/tex/bib/idx/jcomputapplmath2010/234/6/1781-1787.html)]
3. **Dong et al. (JASA 2020, 2021)**: Multimodal method + gradient optimisation for directivity + efficiency. The multimodal method is ~100× faster than BEM for axisymmetric geometry and produces profiles explorable by CMA-ES in future work. [source: [JASA EL326 2020](https://pubs.aip.org/asa/jasa/article/147/4/EL326/1058718/Shape-optimization-of-acoustic-horns-using-the)]
4. **Acculution (2022)**: Phase plug design via topology optimisation, acoustic COMSOL. [source: [COMSOL paper 2023](https://cn.comsol.com/paper/advancements-in-acoustic-topology-optimization-122631)]
5. **Loudspeaker cabinet topology optimisation** (Scientific Reports, 2023): cabinet walls; not directly horn-relevant but shows growing interest in AM-enabled acoustic optimisation. [source: [Nature/Sci Rep 2023](https://www.nature.com/articles/s41598-023-46170-4)]

**Take-away**: The dominant result from topology optimisation is that **non-monotone, stepped or bulging profiles** consistently outperform smooth profiles for broadband efficiency/directivity objectives. hornlab-search's FREEFORM with many anchors (≥8) and no monotone-wall constraint can explore this space. Enabling non-monotone wall angles in the optimizer bounds is a high-value, low-effort change.

---

## 22. Other Notable Typologies (Brief)

### 22.1 Asymmetric Horn (H ≠ V)
Already supported via FREEFORM H+V meridians. Confirmed best practice for installed audio (narrow V for floor-to-ceiling, wide H for audience coverage). Pi Speakers use 90°H × 45°V as a reference design. [source: [pispeakers.com](https://www.pispeakers.com/Pi_Speakers_Info.pdf)]

### 22.2 XT / XR Horns (Eighteen Sound / B&C)
Constant-directivity horns with a diffraction slot and a conical-to-exponential transition in the horizontal plane. Standard CD-horn family. No proprietary geometry visible in public documentation; behaviour matches standard Keele CD analysis. [source: [XR1064 datasheet](https://www.audiovision.ro/static/files/XR1064.pdf)]

### 22.3 Bessel / Salmon Catenoidal Horn
The catenoidal horn (T=0 in Salmon's family) is a gentler expansion than exponential, has no hard cutoff but rolls off gradually. Good for short back-loaded horns. Already parameterisable via HYPEX with T→0.

### 22.4 Stepped Discrete-Impedance Horn
A horn constructed of N cylindrical sections with abrupt diameter steps. Each step creates a partial impedance mismatch; the spacing between steps tunes the reflection to cancel HOM energy at target frequencies (analogous to a multi-layer anti-reflection coating). Academic work on stepped exponential horns for power transfer (Eindhoven, 2010; NWPU, 2019) shows local resonances tunable by step count and area ratio. [source: [TU/e stepped horns](https://research.tue.nl/en/publications/design-of-stepped-exponential-horns-for-acoustic-energy-transfer-/), [NWPU stepped horn](https://pure.nwpu.edu.cn/en/publications/theoretical-explanation-of-the-local-resonance-in-stepped-acousti/)] **FREEFORM-compatible: Yes (piecewise profile). Medium difficulty.**

### 22.5 Multi-Throat Horn (US8452038)
Patent by Harman for a "multi-throat acoustic horn for acoustic filtering" — two throat entries sharing a common mouth, used for frequency-dependent directivity. Not commercially widespread. [source: [Patent US8452038](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8452038)] **New mesh builder required.**

---

## 23. Emergent Ideas 2018–2026

### 23.1 ML-Assisted Horn Design
- **Surrogate modelling**: Deep learning surrogate for rapid directivity prediction, enabling large design space exploration without per-candidate BEM solve. Active in photonic waveguide community; no confirmed acoustic-horn loudspeaker paper found [inferred].
- **Inverse design via NN**: Map directivity target → geometry parameters. Demonstrated for RF horn antennas (Artificial Neural Network, 2024 IEEE). [source: [ResearchGate ANN horn](https://www.researchgate.net/publication/282295997_Design_of_optimum_gain_L-band_pyramidal_horn_using_Artificial_Neural_Network)] Conceptually transferable to acoustic horns with appropriate training data.
- **Quality-diversity (MAP-Elites)** applied to sonic design (2024 arXiv paper on "Exploring Definitions of Quality and Diversity in Sonic Measurement Spaces"). Not specifically about horn geometry but demonstrates QD search's applicability to acoustic design spaces. [source: [arXiv 2024](https://arxiv.org/pdf/2512.02783)]

### 23.2 Comsol / FEM Topology Optimisation (2022–2024)
Phase plug design via full topology optimisation [Acculution/COMSOL, 2022], loudspeaker cabinet by topology optimisation [Scientific Reports 2023]. These workflows demonstrate 3D-printable non-intuitive geometries that outperform classical designs.

---

## 24. Unconventional Ideas Worth Trying in an Optimizer

These are **reasoned proposals** from physical principles, not verified designs. Treat as hypotheses for CMA-ES exploration.

### 24.1 Fourier-Series Cross-Section Modulation (azimuthal ripple)
**Idea**: The cross-section at each axial position is not a simple ellipse or superellipse but a shape with N-fold azimuthal modulation: r(z, φ) = r_0(z)·(1 + Σ_k a_k·cos(k·φ + φ_k)). **Physical rationale**: Azimuthal modulation forces the acoustic energy to spread azimuthally while propagating axially, potentially smoothing the directivity index over angle without relying on a diffraction slot. **Risk**: N-fold symmetric modes may constructively interfere at specific kz values, creating a comb-filter in the off-axis response. Must be explored at small amplitudes (a_k < 0.1).

### 24.2 Non-Monotone Wall-Angle Profile (Deliberate Constrictions)
**Idea**: Allow the wall to converge (contract) at one or more positions along the horn axis before expanding again — analogous to a venturi. **Physical rationale**: Topology optimisation consistently produces this (see Section 21). Convergences reduce HOM cross-coupling between fast- and slow-varying sections. The resulting impedance profile can suppress specific reflection peaks. **Risk**: Convergences generate evanescent modes that reflect energy back to the driver. Must be short (δz < λ/10 at f_max). **FREEFORM already supports this if monotone-angle bounds are relaxed.**

### 24.3 Twisted (Chiral) Horn
**Idea**: A FREEFORM horn whose principal axes (H and V) rotate azimuthally along the axis by angle θ_twist(z). At the throat, H is horizontal; at the mouth, H is at 45° or 90°. **Physical rationale**: A twisted horn mixes H and V modes continuously along the axis, preventing the sharp H/V pattern asymmetry and directivity crossover ("pattern flip") seen at the H/V crossover frequency in conventional asymmetric horns. **Risk**: Generates helical modes; twisted horns have no axisymmetric simplification and require full 3D BEM — computationally expensive. Worth exploring at low twist rates (< 45° total twist).

### 24.4 Mouth-Edge Serration as Optimiser Variable
**Idea**: Parameterise the mouth boundary as a sinusoidal or fractal perturbation: r_mouth(φ) = R_m·(1 + ε·f(φ)), where f is a Fourier series or fractal outline. **Physical rationale**: Frequency and angle diversity in the diffraction sources at the mouth edge should average out the diffraction notch in the polar response. Inspired by the aeroacoustic trailing-edge serration literature (wind turbine noise) where serrations reduce tonal noise by 10+ dB. **Risk**: May simply spread the diffraction energy over a range of angles without eliminating it. BEM will capture this automatically.

### 24.5 Stepped-Resonance HOM Canceller
**Idea**: Insert N discrete step expansions (sudden radius jumps) at axially-tuned positions z_1...z_N inside an otherwise smooth horn. Choose z_k such that the HOM reflections from each step arrive at the throat 180° out of phase, cancelling. Analogous to a multi-section impedance transformer. **Physical rationale**: Each step generates an evanescent HOM wave that reflects back to the driver. If the round-trip phase for the dominant HOM is π at each step and the steps are λ_HOM/2 apart, destructive interference reduces the HOM amplitude reaching the listener. **Risk**: Highly frequency-specific; may only cancel one HOM family. Steps create mouth-reflection ripple in the on-axis response. Requires BEM for validation.

### 24.6 Azimuthally-Varying Throat-to-Mouth Flare Rate
**Idea**: The meridian profile (flare rate from throat to mouth) varies with azimuthal angle φ. At φ=0 (horizontal), a fast-flaring profile (aggressive coverage); at φ=90° (vertical), a slow-flaring profile (narrow coverage). These are blended continuously: r(z, φ) = r_H(z)·cos²φ + r_V(z)·sin²φ. This is a **convex blend** of H and V profiles — already described in hornlab-search's FREEFORM cross-section blending. The new idea is to make the blend angle-dependent rather than an ellipse: use a superellipse with exponent p(z) that varies from 2 at the throat (circular) to 4–8 at the mouth (sharp-cornered rectangle). **Rationale**: Controls the rate of "pattern roundness to rectangular" transition independently per frequency octave. Low risk; simple extension of existing parameterisation.

### 24.7 Phase-Plug-Inspired Throat Labyrinth Insert
**Idea**: A short (5–15 mm) phase-plug insert at the horn throat that presents multiple radial passages of graduated length, equalising the path length from the driver diaphragm centre to the horn throat in the same way a compression-driver phase plug works — but now applied at the horn throat rather than between driver diaphragm and driver exit. **Physical rationale**: In many compression driver + horn systems, the driver already has a phase plug; the mismatch between the driver's convergent phase-plug exit and the horn's divergent geometry generates HOMs. A short throat insert that continues the convergent geometry before transitioning to the divergent horn may smooth the impedance gradient. **Risk**: High manufacturing complexity; BEM mesh requires multi-passage geometry. Could be explored as a single-body optimised throat shape rather than a true labyrinth.

---

## 25. Key References

| Topic | Source |
|---|---|
| JMLC equations verified | [sphericalhorns.net, Dec 2020](https://sphericalhorns.net/2020/12/21/jmlc-inspired-horn-calculator/) |
| JMLC ETF10 lecture (Cléac'h) | [rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf](https://www.rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf) |
| Kugelwellen horn equations | [sphericalhorns.net, Aug 2019](https://sphericalhorns.net/2019/08/25/consistent-modification-of-the-spherical-wave-horn/) |
| Geddes OS waveguide theory | [Semantic Scholar 1993 JAES](https://www.semanticscholar.org/paper/Acoustic-Waveguide-Theory-Revisited-Geddes/d206d7f10ac06d9e681a97b718bd8d5e0f196a57) |
| Geddes waveguide chapter | [gedlee.com Chapter 6](http://www.gedlee.com/downloads/AT/Chapter_6.pdf) |
| Keele CB horn / Biradial | [Wikipedia D.B. Keele Jr.](https://en.wikipedia.org/wiki/D._B._Keele_Jr.) |
| Mantaray MR42 spec | [technicalaudio.com](https://www.technicalaudio.com/pdf/Altec_Lansing/Altec_MR42_Mantaray_Constant_Directivity_Horn.pdf) |
| JBL Progressive Transition | [JBL Pro directivity](https://jblpro.com/en-US/site_elements/tech-note-volume-1-35) |
| QT Waveguide white paper | [excelsior-audio.com](https://excelsior-audio.com/Publications/QTWaveguide/QTWaveguide_WhitePaper.pdf) |
| Danley Synergy patent | [Patent US6411718](https://patents.google.com/patent/US6411718) |
| Danley Paraline patent | [Patent US8066095](https://patents.google.com/patent/US8066095) |
| Multicell horn construction | [diyaudio.com thread 136964](https://www.diyaudio.com/community/threads/the-construction-of-a-multicell-horn.136964/) |
| ATH / R-OSSE | [at-horns.eu](https://at-horns.eu) + [R-OSSE PDF](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev6.pdf) |
| Wadbro/Berggren 2006 | [ResearchGate](https://www.researchgate.net/publication/222547823_Shape_optimization_of_an_acoustic_horn) |
| Multimodal shape opt (JASA 2020) | [JASA EL326](https://pubs.aip.org/asa/jasa/article/147/4/EL326/1058718/) |
| CBT theory | [dbkeele.com](https://dbkeele.com/constant-beamwidth-transducers/) |
| L-Acoustics WST/DOSC | [L-Acoustics history](https://www.l-acoustics.com/stories/what-are-line-array-speakers-and-why-are-they-important-for-live-sound/) |
| Stepped horn theory (NWPU) | [NWPU paper](https://pure.nwpu.edu.cn/en/publications/theoretical-explanation-of-the-local-resonance-in-stepped-acousti/) |
| Metamaterial lens horn | [Duke Space 2021](https://dukespace.lib.duke.edu/items/1add7a2f-5d9d-40a9-98f9-0750c08da54e/) |
| Loudspeaker cabinet topo opt | [Nature Sci Rep 2023](https://www.nature.com/articles/s41598-023-46170-4) |
| Metric-based WG opt (IOA 2024) | [IOA 2024](https://www.ioa.org.uk/conference-proceeding/reproduced-sound-2024/l-macdonald-j-oclee-brown-m-dodd-j-hargreaves-iterative-metric-based-waveguide-optimisation) |
| Kolbrek Horn Theory Part 1 | [grc.com acoustics PDF](https://www.grc.com/acoustics/An-Introduction-to-Horn-Theory.pdf) |
| Horn Theory Part 2 | [audioxpress.com PDF](https://audioxpress.com/assets/upload/files/kolbrek2885.pdf) |
