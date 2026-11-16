# Horn design white papers and analysis practice

**External research pass, 2026-11-15.** Three read-only research lanes: (1) CD/waveguide theory,
mouth termination and the four cell families; (2) Le Cleac'h / Crowe ES / Bi-Radial measured
evidence; (3) BEM, metrics and optimization practice. The owner asked for outside white papers,
not repo opinion. Every claim is labelled [verified] (read the source), [secondary] (credible
summary/manufacturer), or [unverified] (author claim/model inference). The plain-language decision
brief is `STARTING_SEEDS_PLAIN_2026-11-15.md`; the cell handoff is
`BIRADIAL_CROWE_STUDY_2026-11-15.md`.

---

## 1. Annotated bibliography

### Keele, Bi-Radial and the CD horn

| Source | What it establishes | Confidence |
|---|---|---|
| **US4071112A**, Keele/EV, filed 1975-09-30, https://patents.google.com/patent/US4071112A/en | Three-section CD horn: exponential throat -> conical midsection (axes linear, area ~ z^2) -> bell (axes at 2x the cone rate, area 4x; length ~ half the cone). Junction slope must match. The bell exists to make on-axis pressure exceed perimeter pressure near the mouth, killing the 40-50% midrange collapse of radial/sectoral horns. Commercial unit is rectangular with a round->rectangular throat and a central flat vane (structural). The patent does **not** state an explicit angle law. | [verified] |
| **US4308932A**, Keele/JBL, filed 1980-05-06, https://patents.google.com/patent/US4308932A/en | Bi-Radial: two wall pairs at 90 deg, contour `y = a + bx + cx^n`, one pair a surface of revolution, independent H/V exponents (preferred 4-6; claim 14 says 2-8). `A = 0.9 B` ("on the order of ninety percent"). Mouth rule `W = K/(A F)` with K ~ 25,000 m-deg-Hz. Worked example: 80/36 deg, 780 x 780 mm, L=815 mm, 48.8 mm throat, 18 mm gap. The gap is fed by an exponential monotonic connector. | [verified] |
| **AES Paper 1038** (Keele 1975), "What's So Sacred About Exponential Horns?", https://dbkeele.com/7-whats-so-sacred-about-exponential-horns/ | Exponential HF horns cannot hold CD; multicell/radial suffer lobing and midrange narrowing; radial loses vertical beamwidth continuously. Abstract claims a modified conical horn with exponential throat holds CD to 16 kHz. | [verified abstract] |
| **AES Paper 933** (Keele 1973), "Optimum Horn Mouth Size", https://dbkeele.com/optimum-horn-mouth-size/ | There is an **optimum** mouth size for a given cutoff that minimises mouth reflection; bigger is not automatically better. | [verified abstract] |
| **JBL 2380A data sheet** / audio-database | 90 x 40 nominal; H uniform 500 Hz-16 kHz; V constant-directivity only above ~2 kHz; 49 mm throat, 445 x 279 x 236 mm. | [secondary, manufacturer] |

### Geddes, OS waveguide and mouth termination

| Source | What it establishes | Confidence |
|---|---|---|
| Geddes, "What is a Waveguide?", archived at https://web.archive.org/web/20211021013927/http://www.gedlee.com/Papers/What%20is%20a%20Waveguide.pdf | Webster/Horn equation assumes a flat wavefront and cannot predict directivity. Waveguide theory is an exact separable-coordinate solution; the OS contour is the canonical case. Diffraction-based CD is what to avoid. | [verified] |
| Geddes, "Sound Quality Improvements in Compression Driver Systems" (ALMA 2008) | HOM are the dominant coloration; they travel a longer path and are level-dependent. OS minimises HOM. Summa = OS + 30 ppi open-cell foam plug that attenuates HOM and mouth reflections. Slit/diffraction horns generate "enormous" HOM. | [verified] |
| Geddes, "Loudspeaker System Design Philosophy" | Quantitative mouth/edge rule: "If the edge has a radius of 1/4 wavelength ... above this frequency little to no diffraction will occur"; all waveguides have some mouth reflection ("a large radius will reduce this, but not eliminate it"). Summa mouth area = 15-inch woofer area for 90 deg CD to 800 Hz; enclosure edge radius ~2 in. | [verified] |
| Geddes, AudioXPress "Horn Theory reply" | Separable-coordinate boundaries are catenoids `y(x)=sqrt(y0^2+(x tan theta0)^2)`; waveguide theory minimises internal diffraction/HOM; any throat discontinuity generates HOM. | [verified] |
| Geddes, JAES "Acoustic Waveguide Theory" 37(7) 1989; "...Revisited" 41(6) 1993 | The primary OS theory (paywalled; cited in Batik's reference list). | [secondary] |
| Geddes, US7068805 | Throat circular to match the driver; a round-to-elliptical transition must be gradual; angular mismatch at the driver/horn junction generates HOM. | [verified] |

### ATH / Batik

| Source | What it establishes | Confidence |
|---|---|---|
| Batik, **OS-SE Waveguide** (2020), https://at-horns.eu/release/OS-SE%20Waveguide.pdf | OS hyperbola + superellipse termination; `s` = termination flare amount, `n` = how abruptly it engages, `q` = truncation. Explicitly half-space: needs a baffle. For a free-standing waveguide, terminate the profile further (e.g. a clothoid rollback) to reduce mouth diffraction/reflection. | [verified] |
| Batik, **R-OSSE Waveguide rev7** (2022), https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf | Parametric profile that can fold back (self-terminating, free-standing). `a0` = throat half-angle, `k` = throat expansion; `k` sets the DI slope; throat diameter sets HF directivity; wavefront mismatch at the driver causes impedance ripple but little effect on normalised polars; a ring insert fixes it. Optimised with BEM on a pulsating spherical cap, not a real driver. | [verified] |
| ATH **Tritonia**, https://at-horns.eu/tritonia.html | Explicit formulas (rare): `alpha(theta)=48.5-7 cos^5 2theta-16 sin^12 theta`; `s=0.7+0.2 cos^2 theta`; k=1, n=3.7, q=0.995; mouth aspect ~0.86. Morph to rounded rectangle is "partly motivated by the looks" and adds a slightly shifted diagonal. Recommends a small baffle with generously rounded edges. | [verified] |
| ATH **TwinRay** + **roundover study**, https://at-horns.eu/twinray.html and https://at-horns.eu/img/twinray/bem/roundover-study.html | "Rounding the enclosure edges is highly recommended (35 mm radius was used in the simulations)." The study compares 8.75/17.5/35 mm fillets, a 35 mm chamfer, a sharp edge, and a sharp edge with no flat front; images only, no numbers/conclusion text. Note: this is the **enclosure edge**, not the waveguide lip. | [verified text; graphical study] |
| ATH **EXAR story**, https://at-horns.eu/exar-story.html | Extended throat raises throat resistance ~10x near 700 Hz; predicts no directivity change (confirmed by measurement); the end diameter of the extension determines the HF directivity. | [verified] |

### Le Cleac'h, Crowe ES and measured narrowing

| Source | What it establishes | Confidence |
|---|---|---|
| Fourcade, *Calcul du Pavillon Le Cleac'h* (2015), https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf | Exact JMLC construction: `S(l)=S0[cosh(ml/2)+T sinh(ml/2)]^2`, `m=4 pi fc/c`; march equations; stop rule. Reference case (fig. 7): fc 400 Hz, T=0.8, 25.4 mm, 8 deg included exit, stop 360 deg -> L 321.35 mm, mouth width 467.30 mm, L0 at 90/180/270/360 deg = 394/467/496/511 mm. | [verified in repo; fetched] |
| Le Cleac'h, *ETF 2010 lecture*, https://rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf | Isophase surfaces parallel and normal to the wall; T-family list; Kugelwellen double-radius; tractrix cap law. | [verified in repo] |
| Sheerin, *LeCleac'h horn vs Conical Horn*, https://jhsaudio.com/conical.html | Fully-coupled FEA, 2 kHz JBL 2402, LC T=1.4 vs conical. LC DI rises ~4 dB at 1.4 kHz to ~12 dB at 12 kHz (~2.6 dB/oct); off-axis curves similar except 140-160 deg; conical shows angle-dependent 3-4 kHz dip and chaotic 10-20 kHz. LC decays to -60 dB in ~7 ms vs conical -25/-30 dB. Author states the directivity predictions were validated in an anechoic/NIST-traceable system. | [secondary, strong] |
| Crowe, **ES-600 Biradial Horn**, https://josephcrowe.com/blogs/news/es-600-biradial-horn | 270-deg wrap mouth, golden-ratio W/H, "ES flare" (exponential), 417 x 203 x 198 mm, 1.4-inch; passive XO "critical ... damping resonances in the 1 kHz region"; active use explicitly rejected. | [verified, author claim] |
| Crowe, **Faital HF1460 on ES-600 measurement report** | 0/15/30/45 deg; 6 dB/oct fall 5-10 kHz, 12 dB/oct 10-20 kHz, mild 12.6 kHz peak; SMPTE IMD 1.64% vs TAD TD-2002 3.08%, B&C DCM50 1.89%; D2/D3 <0.1%. | [verified, self-measured; no third party] |
| Crowe, **ES-290 polar** / ES-1200 | +10/+7/+5 dB loading at 400-800/1.6k/3k; "near-CD 500 Hz-7 kHz", narrows to ~50 deg above 10 kHz (driver breakup); ES-1200 H "perfect", V irregular ~17 kHz. | [verified, author] |
| Kolbrek, *Horn Theory: An Introduction* (audioXpress 2008) | Exponential loading reaches ~80% of throat resistance by ~270 Hz vs ~1200 Hz conical (comparable horns); T=0-5 family; slow near-throat flare gives better LF loading at the cost of HF beaming. | [secondary, strong] |
| Batik, **Tritonia** / **EXAR** | Large Tritonia 100 deg fairly constant 800 Hz-16 kHz; typical enclosure can cause midrange narrowing; a short expanding adapter adds LF loading with no directivity change. | [verified] |

### Analysis, metrics and optimization

| Source | What it establishes | Confidence |
|---|---|---|
| Kolbrek, *BEM Simulations - Horns*, https://kolbrek.hornspeakersystems.info/index.php/horns/bem | Constant 1 m/s throat velocity, no driver; 6 elements/lambda; 3 m far field; BERIM = infinite baffle, ASEM = thin walls, AEBEM = closed exterior; throat-impedance error is a discretisation artefact; Le Cleac'h mouth wrap: 90 deg worst, 270 deg ~ 360 deg. | [verified] |
| horn-simulation issue #78, https://github.com/timini/horn-simulation/issues/78 | Boundary Lab/Solver study: P1 tetrahedra need ~17 EPW for 1% modal error, 12 for 2%, 8 for 5%, 6 for 10%; use `Mmd` not `Mms`; open-aperture BEM != closed-surface BEM; on-axis normalisation hides level/loading. | [secondary] |
| COMSOL, *Optimizing the Shape of a Horn*, https://doc.comsol.com/6.3/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html | Mesh from f_max and elements/lambda; PML + symmetric/infinite-hard boundary; circular port with incident mode; explicitly warns an on-axis SPL optimum creates deep off-axis minima. | [verified] |
| AKABAK docs, https://www.randteam.de/AKABAK3/AKABAK-Introduction.html and `AKABAK-Studies.html` | BEM+LEM fully coupled at the observation stage; sub-domain modelling for infinite-baffle radiation; BEM for bell/radiation, LEM for driver. | [verified vendor] |
| Smolen & Halley, "An Approach for the Optimization of 3D Loudspeaker Horns", JAES 2021, https://doi.org/10.17743/jaes.2020.0061 | Parametric CAD -> FEM+BEM -> objective-function optimisation -> measured validation of a non-axisymmetric horn. | [verified abstract] |
| Sridhar, Tylka, Choueiri, "Generalized Metrics for Constant Directivity", JAES 2019, https://doi.org/10.17743/jaes.2019.0022 | Proposes metrics for invariance of polar pattern/sensitivity with frequency; notes no established measure existed. | [verified abstract] |
| Newell & Holland, "Do all midrange horn loudspeakers have a recognisable characteristic sound?", Reproduced Sound 2024, https://doi.org/10.25144/21421 | Perceptual study of midrange horns (content not accessible). | [verified metadata] |
| JASA 2025, "Improving transfer function measurements for 3-D printed waveguides using a sand layer", https://doi.org/10.1121/10.0035803 | 3D-printed waveguides showed unexpected 1-4 kHz deviations from secondary transmission paths; a sand layer removes them, improves repeatability and distortion robustness. | [verified abstract] |
| TuRBO, Eriksson et al., NeurIPS 2019, https://arxiv.org/abs/1910.01739 | Local trust-region GP models beat global BO and are competitive with CMA-ES at high dimension; defaults tau_succ=3, tau_fail=ceil(d/q), L_init=0.8, L_max=1.6, L_min=2^-7. | [verified] |
| Hansen, *CMA-ES Tutorial*, https://arxiv.org/abs/1604.00772 | Default population ~4+3 ln d; covariance adaptation; penalty sizing must keep feasible/infeasible differences comparable. | [verified] |
| MTG Waveguide Shootout, https://www.mtg-designs.com/tips-tricks-tests/waveguide-shootout | Baffle-edge diffraction and mic-boom reflections corrupt >=60-90 deg; roundovers + foam fix it; driver exit limits HF directivity (~12-13 kHz on 1 inch, ~8-9 kHz on 1.4 inch). | [verified practitioner] |
| Olive 2004 AES 116th; Toole & Olive JAES 36(3) 1988; CTA-2034 | Preference model `Pref = 12.69 - 2.49 NBD_ON - 2.99 NBD_PIR - 4.31 LFX + 2.32 SM_PIR`; PIR = 12% LW + 44% ER + 44% SP; low-Q resonances more audible than high-Q. | [formula verified in repo; primaries paywalled] |

---

## 2. What sets coverage, loading and mouth termination

### Coverage

- **HF beamwidth is set by the conical-section included angle** in the Keele tri-section. The
  cone is a pulsating-sphere segment; the bell only fixes midrange narrowing. This is a sound
  inference from US4071112, but the patent does **not** state an explicit angle law. The
  Bi-Radial makes it explicit: throat angle `A = 0.9 B` for coverage `B`. [US4071112;
  US4308932A]
- **Mouth size sets the lowest frequency the pattern can be controlled.** The corrected K-law is
  `W = 25,000/(A F)` with `A = 0.9 B` (W in metres, B the full coverage angle in degrees). At
  700 Hz: 80 deg H needs **496 mm**, 50 deg V needs **794 mm**. Our 600 mm H holds 80 deg down to
  ~579 Hz; our 480 mm V holds 50 deg only down to ~1157 Hz, so at 700 Hz the vertical supports
  ~83 deg. This is the physical limit, not a cell bug. [US4308932A; measured arithmetic]
- **A round mouth is the only shape where one polar orbit describes the whole far field.**
  Rectangular mouths trade that for independent H/V control and expose a distinct diagonal plane;
  ATH's rectangle morph is "partly motivated by the looks" and adds a shifted diagonal. A
  rectangular/creased mouth must be judged on the diagonal, not just H/V. [Geddes; ATH Tritonia;
  Keele]

### Loading

- Exponential-type flares load best at low frequencies; conical flares load less. Kolbrek's
  comparison reaches ~80% of throat resistance at ~270 Hz for an exponential vs ~1200 Hz for a
  comparable conical horn. [Kolbrek]
- The Le Cleac'h family's `fc` is the loading corner; pattern control starts around 1.5-1.8 fc.
  [Fourcade; repo]
- The Bi-Radial is usable from ~500 Hz (2380A); the Crowe ES-600 loads from ~500 Hz in his
  measurement, with a passive network handling a 1 kHz resonance. [JBL; Crowe]
- A short expanding throat adapter can add LF resistance with no measured directivity change
  (EXAR). [ATH EXAR]

### Mouth termination

- A sharp mouth edge diffracts; a rounded lip reduces it. Geddes' verified rule is radius >=
  lambda/4 at the lowest frequency you want clean: 35 mm is clean above ~2.46 kHz, 50 mm above
  ~1.72 kHz, 86 mm above ~1 kHz. A 40-50 mm lip is therefore a rational hi-fi choice. [Geddes,
  Loudspeaker System Design Philosophy]
- The ATH roundover study recommends a 35 mm **enclosure-edge** radius; it is graphical only.
  [ATH TwinRay]
- **Wrap angle:** Crowe claims 270 deg reduces edge diffraction and mouth resonance. No measured
  or BEM comparison of 90/130/180/270 deg was found. The grounded claim is "terminate the profile
  smoothly instead of cutting it"; a 90-130 deg roll already does much of that. The 180 deg
  cavity-resonance argument (`c/4d`) is our inference, not a sourced result. [Crowe claim;
  verified absence of comparison; inference]
- **Waist/bow-tie:** no acoustic source. ATH's morph target is a convex rounded rectangle.
  Crowe's waist is an artefact of separate lens-shaped top/bottom panels. Treat as visual.
- **X creases:** weak and double-edged evidence. Creases are curvature discontinuities (HOM and
  diffraction risk per Geddes) and partly the geometric consequence of morphing a round throat to
  a rectangle. ATH says the morph adds a shifted diagonal. Treat as aesthetic until diagonal
  polars exist; do not claim an acoustic benefit.

---

## 3. Measured behaviour of the families

| Family | Coverage vs frequency | DI slope | Loading | Known coloration / resonances | What the data supports |
|---|---|---|---|---|---|
| **Le Cleac'h / JMLC (T~0.8)** | Monotonic narrowing; Sheerin LC DI 4 -> 12 dB over 1.4-12 kHz | ~2.6 dB/oct (8.6 dB/dec) [secondary] | fc is the loading corner; pattern control ~1.5-1.8 fc | Smooth, low mouth reflection if rolled past 180 deg; simulated 7/10 kHz ridges shared with conical = driver; 160-200 deg stop traps a lambda/4 cavity [inferred] | Best-evidenced smooth narrowing; 2-3 dB/oct is real, not necessarily a defect |
| **Crowe ES-600/450** | 0/15 deg near-identical; 30 deg -2..3 dB; 45 deg -4..10 dB above 2 kHz; H 90 -> 46 deg and V 137 -> 41 deg (repo model summary) | ~4.1 dB/oct (13.6 dB/dec) [unverified/model] | Loading from ~500 Hz (Hornresp/rear-chamber assisted) | Explicit 1 kHz resonance requiring passive damping; treble -6 dB/oct 5-10k, -12 dB/oct >10k; 12.6 kHz driver breakup | Author-measured polars are smooth, but coverage narrows hard; no independent data |
| **Bi-Radial (JBL 2380A / Keele)** | H 90 deg held 500 Hz-16 kHz; V 40 deg only above ~2 kHz | Near-flat H in band; V rises below 2 kHz | 500 Hz usable limit | High-aspect gap slot (~21:1) is a diffraction/velocity maximum; Iwata adds AR evolution but no primary construction | H-plane CD well supported; V deliberately not CD; gap is the liability |
| **Exponential / tractrix** | Strong progressive beaming with f | Steep, rises toward HF | Best LF loading (~80% resistance at 270 Hz vs 1200 Hz conical) | Mouth reflection without roll; throat kink excites HOM | Good loading, poor pattern; only defensible with a large rolled mouth |

---

## 4. Acoustically grounded vs cosmetic

- **Mouth lip / wrap:** grounded in principle (rounding suppresses edge diffraction above
  `c/(4r)` and reduces mouth reflection). Wrap beyond ~90 deg is weakly grounded; 270 deg is
  cosmetic-plus-plausible, not demonstrated. Build 130-180 deg if the generator caps at 200 deg;
  do not spend envelope depth chasing 270 deg on acoustic grounds alone.
- **Waist / bow-tie:** visual only; no acoustic source.
- **Corner creases / X:** aesthetic with a measurable polar risk; verify the diagonal.
- **Rectangular mouth:** grounded for independent H/V control, but costs azimuthal symmetry and
  one-orbit verifiability. Defensible for a rectangular room/baffle; not acoustically superior to
  round.
- **Throat blend:** strongly grounded (Geddes, R-OSSE, EXAR). Match diameter and `a0`; avoid slots;
  an extended throat buys LF resistance without changing directivity.
- **Flare law:** grounded. Exponential beams; conical/CD holds angle; OS/OSSE is the minimum-HOM
  smooth family; the Keele tri-section is a historical hybrid. "ES spiral" is an unpublished
  vendor law; our log-spiral analogue is a construction, not a reproduction.

---

## 5. Analysis and optimization best practice

### BEM setup

- Size the mesh from `f_max`: `h = c/(EPW f_max)`. Use **6 EPW for screening** (~10% frequency
  error), **8-12 EPW for verification/final**, and run a lambda/6 -> lambda/12 -> lambda/17
  convergence check on one finalist. Refine the throat and mouth/rollback. [Kolbrek; Boundary Lab
  solver report; COMSOL]
- A uniform-velocity throat cap is acceptable for pattern work but not for level/loading above the
  throat's first cross-mode: `f11 = 1.8412 c/(2 pi a)` -> ~7.9 kHz (1 inch), 5.65 kHz (1.4 inch),
  3.96 kHz (2 inch). For loading/level, couple a lumped driver (Re, Le, Bl, **Mmd** dry mass, Cms,
  Rms) to the BEM throat impedance. [Boundary Lab report; AKABAK; repo constants]
- Declare infinite baffle vs free field per study; they are different operators. Prefer a closed
  exterior surface or an explicit half-space Green's function. Add a PML/radiation condition and
  verify no interior-resonance contamination. [Kolbrek; COMSOL]
- Export balloon DI and full polars, not cuts-only DI. Extract `Re Z` per frequency and report
  absolute level at a declared observation point, not mouth-plane pressure. [repo rule; Kolbrek;
  Boundary Lab report]
- Cross-check with a second solver and published measured horns. Proposed acceptance: beamwidth
  +/-5 deg (+/-3 deg in the presence band), DI +/-1 dB, pattern-control corner +/-1/6 octave,
  `Re Z` transition +/-1/3 octave. Report per-frequency residuals. [repo CP-7b; inferred from
  SIM_VS_REAL]

### Metric hierarchy

- **Must-have:** listening-window and PIR smoothness/slope (CTA-2034); balloon DI and its
  smoothness; beamwidth vs frequency in H, V and diagonal; throat loading `Re Z` across the
  passband; absolute level/efficiency via the lumped-driver model.
- **Should-have:** DI slope/level as context (not a target); ERDI/SPDI; seat-to-seat/listening-
  window spread; crossover DI continuity (`xo_spread`); group delay; distortion vs level.
- **Diagnostic-only:** a single scalar J; on-axis-only flatness; a fixed DI target (v7
  `di_slope_target=0` penalises a smooth rise by 8-9 normalized units); cuts-estimated DI; raw
  polar ripple without balloon context; beamwidth from outermost crossings alone (can hide lobes).
- **Pitfalls:** optimising on-axis only is explicitly pathological (COMSOL shows deep off-axis
  minima); normalising polars to 0 dB hides level and LF loading; broad deviations are more
  audible than narrow ones and EQ cannot repair angle-dependent errors. [COMSOL; Boundary Lab;
  Toole/Olive]

### Optimization at 100-300 solves/night

- CMA-ES with BIPOP restarts, population ~`4+3 ln d`, 3 seeds, warm start from the same brief's
  archive. At this budget warm starting matters more than longer runs. [Hansen]
- GP-BO (BoTorch `qNEHVI`/`qEI`) at d~8-20: 40-60 space-filling points then 100-200 model-selected
  points in batches of 4-8. Use TuRBO if d>20, the landscape is heterogeneous, or you need
  multiple basins. [TuRBO; BoTorch]
- Keep 2-3 objectives; do not scalarise until the Pareto front shows the trade-off is real.
  Treat refusals as constraints, not a 1000-point penalty; never feed fake scores to `tell`.
  [repo hardening; TuRBO]
- Verify the top 15-20 on the dense grid and rank by verify-J; report screen->verify Spearman.
  Rho < 0.3 means a fidelity problem, not a finalist-count problem. [repo search dossier]

---

## 6. Design implications for the four cells

| Cell | Closest to the owner's look | Acoustically defensible at 700 Hz | Key risk | Verdict |
|---|---|---|---|---|
| **Biradial** | Medium (classic two-plane, not Crowe X) | Partly: H 80 deg feasible; V 50 deg impossible at 700 Hz (480 mm supports ~83 deg); gap slot is a liability | Gap slot/diffraction; new throat blend | Keep as reference, not the 700 Hz primary |
| **ES spiral** | High (smooth exponential flare + rolled lip) | Plausible but unmeasured; loading depends on fc/flare; roll >=180 deg suppresses mouth reflection | No published ES law; our construction; thin roll in the current render; beam narrows | Best look/acoustics compromise; needs BEM |
| **R-OSSE rect** | Medium-low (clean landscape rim, less Crowe) | Most defensible CD option; 540 x 300 mm mouth, a_h ~36-40 deg, a_v ~24-26 deg, gradual morph, round throat | Morph transition and mouth termination; less visual match | Safest acoustic baseline for 700 Hz |
| **Crowe-X** | Highest front-view X/bow-tie | Unproven; corner creases are potential diffraction sources | Crease/pucker HOMs; no measured polars; current lip is a thin flange | Pursue only with measured/simulated diagonal polars |

For a 700 Hz home crossover the mouth should be >=~496 mm wide for 80 deg H control, with DI at
700 Hz matched to the woofer (typically 4-7 dB for a 10-12 inch direct radiator); the repo's
`xo_spread` gate is the right check. If the target is Crowe-like appearance, ES-spiral/Crowe-X are
the look-matched families, but R-OSSE-rect is the one whose acoustics are already supported by
ATH's published CD results.

---

## 7. What still needs measurement

1. **Independent Crowe polars/DI.** All ES data is the designer's own; no third-party balloon
   exists. A 270 deg wrap vs a 130-160 deg roll has never been A/B measured.
2. **ES-spiral and Crowe-X BEM/anechoic polars**, especially the 45 deg diagonal and the
   pucker/crease modes. These are our constructions, not Crowe's equation.
3. **Bi-Radial gap-slot penalty** at 1.4-inch scale: quantify the ~21:1 slot's diffraction/ripple.
4. **HF1440 + adapter:** 18 mm radius / 2 deg exit should be coupled round-to-round; the exact
   adapter length/expansion for the HF1440 is unmeasured.
5. **Loading at 700 Hz in the real mount** (`LFP20`, `Re_Z_min`) for each cell.
6. **In-room / seat-spread:** no fetched source measures a narrowing horn in a domestic room
   against a CD horn; the "smooth narrowing is fine at home" case rests on Olive/Toole preference
   modelling, not a horn-specific listening test.
7. **Printed-waveguide measurement artefacts:** the JASA 2025 sand-layer result suggests a real
   1-4 kHz secondary-path issue; measure a prototype with and without damping.

---

## 8. Corrections to earlier repo notes

1. **K-law denominator:** `A = 0.9 B`, not `B`. At 700 Hz, 80 deg H = 496 mm (not 446), 50 deg V =
   794 mm (not 714). The 600 mm H holds 80 deg to ~579 Hz; the 480 mm V holds 50 deg only to
   ~1157 Hz (~83 deg at 700 Hz).
2. **"Cone half-angle sets HF beamwidth"** is a sound inference from US4071112, not a statement in
   the patent.
3. **The 55/r Hz roundover rule is not sourced.** Use Geddes' radius >= lambda/4 rule: 35 mm ->
   ~2.46 kHz, 50 mm -> ~1.72 kHz, 86 mm -> ~1 kHz.
4. **270-deg wrap superiority and the 180-deg cavity-resonance claim are unverified.** No measured
   or BEM comparison of wrap angles was found.
5. **The waist/bow-tie outline has no acoustic source.** ATH's morph target is a convex rounded
   rectangle. X creases are a measurable diagonal-polar risk, not an established benefit.
6. **"Diffraction proportional to surface second derivative"** is a paraphrase; Geddes' actual
   criterion is boundary continuity/catenoid and HOM generation.
