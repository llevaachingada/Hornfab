# HornFab HF1440 / Klangfilm throat coupling: senior evidence-based correction

**Date:** 2026-11-16. **Revision:** throat-3.0 (overrides any assertion in the earlier handoff that `brief.driver.exit_angle_deg: 2` is a physically verified HF1440 exit half-angle). **Scope:** HF1440 at a modeled 36.0 mm round acoustic source; JMLC, Klangfilm, and Lamé morph implementations. **Decision:** do not enforce any published-manufacturer angle match for HF1440 because none exists. Do enforce whatever *chosen modeled geometry and source boundary* are declared, test its continuity, and experimentally evaluate whether it predicts the real driver.

> **Provenance convention:** `[M]` manufacturer, `[P]` peer-reviewed/primary paper, `[A]` horn author's firsthand technical account, `[F]` knowledgeable forum/practitioner but not a controlled measurement, `[D]` independently derived/calculated, `[R]` HornFab code/brief, `[U]` unresolved physical fact. References below provide direct URLs. Never upgrade `[D]/[F]/[R]` to `[M]` for actual HF1440 behavior.

## Executive decision for implementation

1. **Keep the factory physical entrance circular at 35.8 mm diameter**. The existing `room_landscape_80x50_700_hf1440_v7_smooth.yaml` models a diameter of 36.0 mm (radius 18.0) and a `2.0` degree *half angle*. The diameter difference is 0.2 mm, acceptable as a legacy modeling approximation, but it must be acknowledged and should be changed to 35.8 mm for *new driver-fidelity candidate designs* after matched benchmark comparison. Do not silently change legacy brief values and invalidate historical hashes. `[M1,R1]`
2. **The HF1440 manufacturer does NOT give a numeric 2° exit angle**. Its exit is **"Combined Exit"** and it has a **radial phase plug with no separate conical adaptation throat**; the flange drawing gives external mounting dimensions, not the internal phase-plug outlet velocity field. The actual local material slope, emitted wavefront phase, and spatial velocity distribution at the plane are *unknown*. `[M1,M2]`
3. **The raw 2018 Klangfilm construction mathematically produces a 10.617223° half-angle at f_c=560 Hz, r_t=18 mm**. This is a horn-geometry result, NOT a property of HF1440. The manufacturer's label "Combined Exit" cannot be translated into 0°, 2°, 10.6°, or any other numeric wall-angle. `[D1]`
4. **Do not make `abs(alpha_horn0 - 2°) < 0.25°` a universal physical acceptance gate.** Instead validate (i) actual entrance circle, (ii) declared *design* tangent when a specified angle parameter is used, (iii) local C1/C2 smoothness and monotone opening, (iv) source cap construction and seams, (v) measured acoustic outcomes. If a physical driver CAD or measured exit field later becomes available, add a separate calibrated fidelity gate. `[P1,A1,R1]`
5. **The fastest investigation is a small acoustic ablation**, not wide optimization over angle plus Lamé plus aspect plus rollback. Hold the parent horn, aperture, source convention and full downstream shape fixed; compare 3–5 local throat variants with a compact, smoothly vanishing correction before introducing a new search gene. One of the variants must retain the raw 10.617° entrance. With no reliable source-field data, evaluate at least two defensible boundary conditions if the mesher/solver actually supports them (e.g., same *planar axial velocity disk* vs. a separately versioned *pulsating-cap* source). Do not fake a comparison by changing the source cap geometry without recording it. `[P1,P2,A1,D2]`
6. **Do not use the 2018 Klangfilm parent as a geometry-fit surrogate for the long JMLC example without separate verification.** Any local throat splice alters the ideal parent wavefront/cap law inside the splice. Leave the original parent untouched; store the modification as a derived, versioned operator. `[P3,D2]`

## 1. What manufacturers actually specify

| Device / source | Reported aperture | Exit description | What is established |
|---|---:|---|---|
| FaitalPRO **HF1440** `[M1,M2]` | 35.8 mm | **Combined Exit**, radial plug, end of plug at mounting plane, no conical adaptation throat | No maker numerical outlet slope or wavefront curvature; **2° not validated** |
| FaitalPRO **HF1400** `[M3]` | 35.6 mm | **12° Conical**, annular plug, recessed plug plus conical adapter | A manufacturer numerical conical exit label exists for *this different driver*. Document does not resolve the HornFab half/included convention without separate interpretation. |
| FaitalPRO **HF144** `[M4]` | 35.6 mm | **29° Conical**, annular plug plus adapter | A genuinely different, larger-angle conical-exit family, not an HF1440 substitute |
| B&C **DE250** `[F1]` | 1 in nominal | Manufacturer allegedly gave **14.8° included**, per owner of dated correspondence; separate forum author cites 14.6° drawing | Credible practitioner lead, but distinguish forum evidence from a current manufacturer datasheet |
| Peerless/Faital/ATH examples `[A2,A3]` | mixed | Selected horn throat angles are **designer geometry choices** | A good waveguide may use rapid expansion without claiming the selected `alpha0` is the actual internal phase-plug velocity field |

**Answer to the owner's skepticism:** Some compression drivers *do* include conical adapters with real geometrical outlet angles, but not every compression driver has a single externally specified or meaningful angle. This particular HF1440 is a notable example. Do not force all compression drivers into a scalar-angle model. `Exit Angle` may refer to an **included full cone angle** in one catalog and a **half-angle** in HornFab; conversions require verified convention, not guesswork. `[M1,M3,M4,F1]`

Manufacturer's datasheet for the HF1440 says the driver was measured attached to the **LTH142** horn, as Faital uses for several different 1.4-inch drivers. This **does not tell us the exit wavefront on our custom horn**, nor does it prove an arbitrary 10.6° horn is unacceptable. A participant in the *very Klangfilm diyAudio thread* points out that Faital uses the same LTH142 with multiple conical exit angles and cautions against overemphasizing a nominal throat-angle match when the phase plug differs. Treat that as practitioner analysis, not controlled proof. `[M1,F2]`

## 2. Verified geometry: why the pure Klangfilm throat has 10.617°

The Ahlswede 2018 **spherical** starting construction, as implemented in `tools/geometry/klangfilm_ellipse.py` (its elliptical stretch vanishes at the start), uses millimeters in these formulas:

\[
R=\frac{c}{\pi f_c},\quad m=\frac{4\pi f_c}{c}=\frac4R,\quad
h_0=R-\sqrt{R^2-r_t^2}.
\]

\[
r(h)=\sqrt{2Rh-h^2},\qquad
z(h)=\frac{\ln(h/h_0)}m-h+h_0.
\]

\[
\frac{dr}{dh}=\frac{R-h}{r(h)},\qquad
\frac{dz}{dh}=\frac{1}{mh}-1=\frac{R}{4h}-1.
\]

Consequently the physical horn-wall **half-angle of the mathematical surface** at the initial row is

\[
\boxed{\alpha_{\mathrm{wall},0}=\arctan\left(\frac{(R-h_0)/r_t}{R/(4h_0)-1}\right).}
\]

Using `c=343000 mm/s`, `fc=560 Hz`, `r_t=18.0 mm`, the independent standard-library check gives `R=194.9648053 mm`, `h0=0.83269743 mm`, `dr/dz=0.18745606`, and **10.61722310°**. This is confirmed in `04_THROAT_ANGLE_ANALYTIC_CHECK.py` and `04_THROAT_ANALYTIC_RESULTS.txt`. It is **not** a claim of physical driver matching.

| `fc` at the same 18 mm radius | Raw Klangfilm wall half-angle |
|---:|---:|
| 450 Hz | 8.521° |
| 480 Hz | 9.092° |
| 560 Hz | 10.617° |
| 700 Hz | 13.298° |
| 800 Hz | 15.224° |

Approximately for `r_t << R`, `tan(alpha0) ≈ 2*r_t/R = 2*pi*f_c*r_t/c`. Achieving a **2° mathematical raw-wall slope by changing only `f_c`** would require approximately 106 Hz at 18 mm radius, implying `R≈1.03 m`, wildly different size/coverage/cutoff from the 560 Hz candidate. **Do not tune `f_c` to fix the unverified 2° mismatch**; it would destroy the intended horn. Nor should 10.6° be labeled automatically wrong acoustically.

**Wider issue:** The new Lamé morph can be C0 round at `z=0` but has an unsafe derivative with the current `u^p` morph when `p<1`. Geometry must be checked after the actual radial elliptic morph, not just for the underlying circular parent. `g_throat_ellipse=0.4` is especially important to inspect. `[R2,D1]`

## 3. Research on the acoustic significance (and why angle matching is not sufficient)

- **Maker research, Marcel Batík R-OSSE rev7, pp.21–27 `[A1]`:** a conical driver duct attached to a smooth waveguide can reflect even when the slopes agree, because its **curvature jumps**. Models with 10/20/40 mm ducts show pronounced impedance resonance changes, but his particular normalized polar comparisons barely change. *Inference:* angle mismatch matters, but imposing an exact angle is neither sufficient nor universally the highest-value optimization variable. His ring insert is a **different architecture** designed for a driver *with a conical adapter*, and should **not** be copied to the HF1440 whose manufacturer states it has no such adapter.
- **HF1440's unknown actual exit velocity and phase:** Makarski's 2004 experiments `[P1,P2]` measured spatial velocity at the horn/driver interface. A uniform plane-wave source can be useful but become misleading at high frequencies. The reported source-distribution modes depend on frequency and driver; artificial HOMs in numerical models may not be strongly excited by actual drivers. The first *permitted* higher-order mode of a circular 36 mm waveguide is around `f11≈1.841*c/(pi*d)≈5.6 kHz`, but this is **not** a statement that HF1440 physically starts radiating that mode at 5.6 kHz. A model with `v_n=constant` is a hypothesis, particularly toward 8–20 kHz.
- **Compression driver phase plug literature `[P3,P4]`:** Dodd and Oclee-Brown analyze radial/annular plug channel geometry and modal excitation. Internal acoustic transformation and wavefront shape are not characterized by a single external geometric angle. More recent 3-D compression-driver shape optimization `[P5]` further supports treating phase plug as its own acoustic subsystem, not an assumed spherical cap.
- **Geddes `[P6,F3]`:** emphasizes the driver/waveguide junction and initial radius/slope match as a sound design principle. The publication record does **not** establish an HF1440-specific 2° or an exact dB penalty for an 8.6° difference in this particular source.
- **ATH Tritonia `[A3]`:** published design with ~20° throat opening and a rapidly expanding section; author explicitly says the exact throat angle is *not especially critical in that design*. This is an existence proof against a universal small-angle constraint, not evidence that 20° is optimum for this Klangfilm horn.
- **Optimized horn literature `[P7,P8,P9,P10,P11]`:** objectives balance impedance matching, smoothness, and directivity, including H/V asymmetry. None provides a universal compression-driver throat half-angle for a combined-exit driver. Their strong, transferable finding is to use a **small, smooth parameterization and test its actual acoustic performance** under a clearly declared source condition.

## 4. Three distinct variables: don't conflate them

| Quantity | Model name (proposed) | What it means / provenance | Optimizable? |
|---|---|---|---|
| **Known physical mount circle** | `driver.exit_radius_mm`, `manufacturer_exit_diameter_mm` | 18 mm legacy modeling versus 17.9 mm manufacturer physical; validate exact mechanical fit | **No.** Physical driver constraint, not an optimization dimension |
| **Chosen CAD throat entrance tangent** | `geom_entry_half_angle_deg` (new, opt-in) | Tangent of constructed horn wall at z=0; **not** HF1440 manufacturer angle | **Only after 3–5 fixed variants show value**. Do not add by default to first Lamé search |
| **Assumed acoustic source cap curvature / velocity** | `source_model_id`, `source_cap_half_angle_deg` (or equivalent persisted boundary data) | Geometry of driven cap / prescribed source velocity; **not** interchangeable with material wall angle or real driver wavefront | Treat as **model-sensitivity axis**, not an ordinary shape gene; each source model must have its own cohort / hash |

**Naming policy**: In a future schema, `driver.exit_angle_deg` cannot truthfully serve all three roles. To preserve byte-for-byte legacy config and hashes, keep old key accepted but annotate `angle_provenance: assumed_legacy` and introduce explicit new values at a *new opt-in schema version*. Never mutate old data. Store original `brief` values and effective physical geometry values in provenance. Before adding schema keys, verify `config.py` accepted key validation and the installed mesher source-closure contract.

The current `hornlab_search/mesh/grid_build.py` hardcodes `source_shape=1` and passes `source_auto_angle_deg` into `PointGridHornGeometry` to build a source cap; zero angles are refused because this cap would disappear. The source cap is **a piece of acoustic model geometry**. If changing `source_auto_angle_deg` changes the source cap while also changing a throat slope, that does **not** isolate the acoustic effect of throat slope. For proper A/B experiments, hold the source boundary fixed; if the installed mesher cannot model different wall tangents joining the same source disk smoothly, either implement an opt-in compatible closure or report the A/B as **joint throat+source comparisons**, not as single-variable tests. Do not spoof zero using `0.001°`. `[R3]`

## 5. Practical geometric fix: optional, not compulsory, and not an adapter fitted inside the HF1440

Implement the 2018 parent unchanged. For a **derived** Klangfilm/Lamé horn, offer a small, local analytic shape correction that changes the first portion of the horn wall and decays to zero *before the first axial turning point*:

\[
\Delta r(z)=\bigl[\tan\alpha_{\rm design}-r'_{\rm parent}(0)\bigr]z\bigl[1-Q(z/L_b)\bigr],
\quad Q(t)=6t^5-15t^4+10t^3,\quad t=z/L_b.
\]

Let `r_new(z)=r_parent(z)+Delta r(z)` for `0<=z<=Lb`; unchanged afterwards. It enforces `r_new(0)=r_t`, `r_new'(0)=tan(alpha_design)`, and zero value/first/second correction derivatives at `Lb`, provided the base is sufficiently smooth. It is **C2 local geometry**, not a physical driver adaptor, not exact spherical-wavefront area conservation inside `Lb`, and not a proven acoustic improvement.

Analytic derivative, useful for preflight without noisy finite differences:

\[
r'_{\mathrm{new}}(z)=r'_{\mathrm{parent}}(z)+k[1-Q(t)-tQ'(t)],\quad k=\tan\alpha_{\rm design}-r'_{\rm parent}(0).
\]

The bundled **standard-library-only** script independently evaluates parent + correction at `fc=560 Hz`, `r_t=18 mm` for target model half-angles `[0°,2°,5°,8°,10.617°]` and blend lengths `[10,20,30,40] mm`. Across those 20 examples, the analytical local checks found **no radial pinch** and exact radius/slope endpoint matching at the tested numerical tolerance. This is **not** a triangulation or BEM verification, and **not** evidence that 2° sounds best. Zero-degree candidate is math-only until the mesher's nonzero-cap contract has a physically meaningful handling.

**If we use Lamé/ellipse in the first few millimeters:** a scalar radial correction only works while the throat is still round and each azimuth has the same local meridian. If morphing starts immediately, derive separate H/V first derivatives and enforce true shape velocity/normal continuity for the **full 3-D surface** using Cartesian tangents; do not force the radial circular formula on an already eccentric near-throat section. If a Lamé round-to-nonround transition begins at `z=0`, require `p(0)=2`, `q(0)=1`, finite `p'(0)`, `q'(0)` and their impact on local wall derivative. Prefer `p'(0)=q'(0)=0` initially to avoid an instant azimuth-dependent cone. The 2018 exact cap area law only applies to the unmodified parent; record cap-area deviation after throat surgery and optimize morphology only once it passes the prescribed limits.

**Possible stronger alternative, later:** replace the entire independent blend by a constrained spline/Bezier throat segment solved with boundary conditions for position, tangent and curvature at both ends, and with positive section area growth. It is more flexible but adds parameters and numerical conditioning risk; require comparative evidence before implementing it. Avoid attaching a long straight throat tube merely to make the angle "look right" because Batík demonstrates it can introduce impedance resonances `[A1]`.

## 6. Cost-aware acoustic validation before optimizing this parameter

**Stage T0 (no GPU, mandatory)**

- Record exact `main` SHA, local worktree, installed mesher/solver SHAs, old baseline config/brief, source cap mode and `SourceTag 2` geometry; avoid altering live GPU queues or existing design hashes.
- Verify the **old exact** Klangfilm source remains ~10.617° before its `throat_ellipse` post-morph; check actual H/V post-morph derivatives, because the `u^0.4` schedule may be non-C1 right at the entrance.
- Check **manufacturer 35.8 mm** vs historical model 36.0 mm, both in documentation. Keep historical data immutable and produce at least one future 35.8 mm manufacturing fit case.
- Materialize different angle variants from a **single base parent**, and compare geometry fingerprints, full surfaces, r(z), d r/dz at 0/Lb, C2 continuity, minimum area/relative expansion, no wall curvature spikes, no throat pinch, no shell collisions. Verify the actual meshed aperture, BEM source boundary and point-normal orientation, not just metadata.
- For each candidate, record `geom_entry_half_angle_deg`, `source_model_id`, `source_cap_half_angle_deg`, `throat_blend_mm`, `manufacturer_angle_known=false`, `actual_wall_tangent_h/v_deg`, `k`, first forward turning point and `cap_area_error`. Reject duplicate shapes/zero-activity knobs before any solver evaluation.

**Stage T1 (small controlled BEM study, *only after* T0 passes)**

- Candidate set: old raw Klangfilm **10.617°**; derived **2°** (historical assumption), **5°**, **8°** or comparable length-fixed variants at `Lb≈10–30 mm` (provided each is mesh-valid); add **0°** only with a legitimate zero-angle source closure. A fixed three-way subset (raw/2°/5°) is enough for first differences.
- Hold parent profile, `fc`, stretch, Lamé exponent, mouth geometry, front sweep, flange, source velocity convention, mesh accuracy, actual source boundary geometry, and frequencies constant wherever possible. If this is geometrically impossible, mark the changed factors and avoid single-cause attribution.
- Do first high-leverage comparison at ~700 Hz, 1, 2, 4, 5.6, and 8 kHz, with extra frequencies added around measured impedance irregularities. Same full polar angles/diagonal coverage. The 5.6 kHz circular duct figure is a **modal-availability reference**, not the measured HF1440 high-frequency limit.
- Evaluate **complex acoustic input impedance** and its sharp resonances, on-axis **absolute** response for a common source normalization, H/V/diagonal polars, low-frequency loading, and BEM mesh-refinement changes. The primary A/B endpoint is whether the throat modification improves acoustic performance, **not whether its selected angle equals 2°**.
- If acoustic differences are under mesh/source uncertainty, **freeze angle in optimization**, and do not create a sixth weakly identified BoTorch variable. If differences are material and reproducible, use a bounded 1D angle / blend follow-up under fixed source model; only then consider joint search with `q_mouth`, `p_mouth` and roll/sweep.
- For engineering accuracy above ~5–8 kHz, do not claim validation with the uniform or cap-velocity source alone. Actual driver wavefront / directivity comparison is needed; `HF1440 frequency range to 20k` is **not** evidence of HornFab BEM fidelity to 20k.

**Stage T2 (physical corroboration when available)**

- Ask FaitalPRO engineering for the HF1440 throat/phase-plug outlet **internal mechanical section**, effective wavefront (phase/velocity) or recommended horn entrance profile, its gasket/standoff, and whether 35.8 mm is the clear opening at the physical attachment plane. Manufacturer might not disclose proprietary geometry; record unavailable rather than hallucinating.
- If physical driver available: inspect outlet mechanically without damaging diaphragm, measure the exact mating circle/gasket gap; later use short high-resolution printed throat variants and repeated impedance + on/off-axis/polar measurements in a consistent mount. Use manufacturer LTH142 horn response as only an external **system benchmark**, not a transferable outlet boundary condition.
- A measured complex pressure/velocity profile at throat or a trusted full driver FEM/CAD model could be substituted as a versioned source definition. Frequency-dependent input is needed for strong 8–20k conclusions. The cited Makarski paper provides one experimental method, not a ready HF1440 lookup table.

## 7. Mandatory corrections to the older implementation dossier

1. Strike as **false physical requirement**: `source tangents must match 2° because HF1440 exit is 2°`.
2. Replace with **true geometry requirement**: `actual wall derivative must match the chosen CAD design alpha within the declared tolerance; driver geometry remains unknown, and its modeled BEM source is separately versioned`.
3. Change `G2` to separate **mechanical throat fit**, **analytical geometry/tangent continuity**, **source closure correctness**, and **calibrated driver fidelity (future)**. No source metadata alone can certify wall tangent or driver matching.
4. Do not optimize `geom_entry_half_angle_deg`, `source_cap_half_angle_deg` and `source_blend_mm` together with Lamé/aspect/roll until an inexpensive identifiability test shows distinct objective sensitivity. Keep `source_model_id` categorical and outside the initial morphology vector.
5. Do not re-label a new derived parent with a modified source zone as `klangfilm_exact`, and do not claim area lock holds there unless recomputed after that deformation.
6. Preserve historical 36.0 mm/2° designs and their caches; new profiles that use 35.8 mm or a different source curvature are **new geometries and must be re-solved**. Replay unchanged solves only when geometry/source/frequency/method identity is preserved.
7. Keep the owner’s primary 80°H/50°V dispersion objective unchanged. Wall `alpha` or aspect ratio cannot be mapped directly into acoustic beamwidth; only computed H/V/diagonal radiation pattern answers it.

## 8. Direct reference matrix and evidence quality (26 source and repository records)

- **[M1]** FaitalPRO, official *HF1440 product specification*, throat `35.8mm`, radial phase plug, **Combined Exit**, outlet equals phase plug termination, no conical adapter: https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185
- **[M2]** FaitalPRO, *HF1440 datasheet*, Feb 5 2024, manufacturer PDF mirrored as supplied: https://www.lautsprechershop.de/pdf/faital_pro/faital_pro_hf1440.pdf . The dimension drawing gives outer envelope and bolt circles, **not a numerical internal exit angle or measured wavefront**.
- **[M3]** FaitalPRO *HF1400*, `12° Conical` adaptation (different device): https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020105
- **[M4]** FaitalPRO *HF144*, `29° Conical` adaptation (different device): https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020170
- **[A1]** Marcel Batík, *R-OSSE Acoustic Waveguide rev7* (2022), **pp. 21–27**, controlled impedance/radiation model of conical duct, wavefront/curvature mismatch and ring insert: https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf
- **[A2]** Marcel Batík, *Extended-Throat Waveguides / EXAR story* (author's physical experiments and caveats on actual driver input wavefront): https://at-horns.eu/exar-story.html
- **[A3]** Marcel Batík, *Tritonia Waveguides*: 20° throat entrance not especially critical in that *specific rapid-expansion design*, alternate construction/morph: https://at-horns.eu/tritonia.html
- **[P1]** Michael Makarski, *On the Velocity Distribution at the Interface of Horn Driver and Horn* (CFA/DAGA 2004), actual boundary-plane velocity measurement and mode-dependent prediction: https://pub.dega-akustik.de/DAGA_1999-2008/data/articles/001430.pdf
- **[P2]** G. K. Behler and M. Makarski, AES Convention 116, Paper 6097 (2004), *On the Velocity Distribution at the Interface of Horn Driver and Horn*, abstract and provenance: https://aes.org/publications/elibrary/elibrary-page/?id=12743
- **[P3]** Mark Dodd and Jack Oclee-Brown, *A New Methodology for the Acoustic Design of Compression Driver Phase-Plugs with Radial Channels*, Proceedings of the Institute of Acoustics (2009): https://www.ioa.org.uk/system/files/proceedings/m_dodd_jack_oclee-brown_a_new_methodology_for_the_acoustic_design_of_compression_driver_phase_plugs_with_radial_c.pdf . Search-index text available; original PDF reader intermittently returned 404 at review. Claims therefore based on indexed paper excerpts, not full line-by-line inspection.
- **[P4]** Mark Dodd and Jack Oclee-Brown, *A New Methodology for the Acoustic Design of Compression Driver Phase-Plugs with Concentric Annular Channels*, Proceedings of the Institute of Acoustics (2008): https://www.ioa.org.uk/system/files/proceedings/m_dodd_j_oclee-brown_a_new_methodology_for_the_acoustic_design_of_compression_driver_phase-plugs_with_conce.pdf . Same reader limitation.
- **[P5]** *Cut Finite Element 3D Acoustic Shape Optimization of a Compression Driver Taking Viscothermal Losses Into Account*, *International Journal for Numerical Methods in Engineering* (2026), DOI 10.1002/nme.70284, distinguishes internal driver modes/phase plug and loss sources: https://onlinelibrary.wiley.com/doi/full/10.1002/nme.70284
- **[P6]** Earl Geddes, *Acoustic Waveguide Theory*, AES Convention 83 (1987), source model assumption and higher modes: https://aes.org/publications/elibrary/elibrary-page/?id=4855
- **[P7]** Bängtsson, Noreland and Berggren, *Shape Optimization of an Acoustic Horn*, *Comput. Methods Appl. Mech. Eng.* (2003), DOI 10.1016/S0045-7825(02)00656-4: https://www.sciencedirect.com/science/article/pii/S0045782502006564
- **[P8]** Dong, Shen and Gao, *Shape optimization of acoustic horns using the multimodal method*, *JASA* 147 (2020), DOI 10.1121/10.0001037, gradient optimization with mode coupling and experimental validation: https://pubmed.ncbi.nlm.nih.gov/32359259/
- **[P9]** Gu, You and Shen, *Multimodal-based shape optimization of rectangular horns for improved radiation efficiency and directivity control*, *JASA* 158 (2025), DOI 10.1121/10.0039253, explicitly balances efficiency and independent H/V coverage: https://pubmed.ncbi.nlm.nih.gov/40928147/
- **[P10]** Udawalpola and Berggren, *Optimization of an acoustic horn with respect to efficiency and directivity*, *Int. J. Numer. Methods Eng.* (2007), DOI 10.1002/nme.2132, trade-off between impedance and DI: https://www.scilit.com/publications/e73021666bd281e3230ae56290d8ca53
- **[P11]** Barbieri and Barbieri, *Acoustic horns optimization using finite elements and genetic algorithm*, *Applied Acoustics* 74 (2013), DOI 10.1016/j.apacoust.2012.09.007, compact C1/Hermite smoothing of horn boundary: https://www.sciencedirect.com/science/article/pii/S0003682X12002939
- **[F1]** diyAudio 2018 *DE250 exit angle is 14.8°*, named forum member reports B&C correspondence and clarifies angle as included, ATH author corroborates earlier drawing near 14.6: https://www.diyaudio.com/community/threads/de250-exit-angle-is-14-8.321543/
- **[F2]** diyAudio *Klangfilm spherical wave horn calculator* page 2, participant explicitly notes common Faital LTH142 horn used across different conical exits and emphasizes phase plug importance: https://www.diyaudio.com/community/threads/klangfilm-spherical-wave-horn-calculator-from-round-to-elliptical.328970/page-2
- **[F3]** Earl Geddes's firsthand diyAudio *Geddes on Waveguides* discussion, importance of initial radius/angle match, qualitative (not calibrated HF1440 result): https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/
- **[F4]** audiohorn.net *Compression Driver* engineering guide, labels HF1440/1460 slow-flare devices and contrasts larger conical exits: https://audiohorn.net/guide/compression-driver/
- **[R1]** HornFab home brief, `exit_radius_mm=18`, `exit_angle_deg=2`, **this is a modeled input**: https://github.com/llevaachingada/Hornfab/blob/main/examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml
- **[R2]** HornFab Klangfilm geometry implementation, derived 2018 interface: https://github.com/llevaachingada/Hornfab/blob/main/tools/geometry/klangfilm_ellipse.py
- **[R3]** HornFab GRID builder, `source_shape=1`, `source_auto_angle_deg` and source cap mesher contract: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/mesh/grid_build.py
- **[P12]** Jean Fourcade, *Calcul du Pavillon Le Cléac'h* (2015), pp.6/12, circular cap throat initial half angle as a **construction input** and required tangent continuity in idealized model: https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf

**Research saturation summary:** checked manufacturer pages/drawings, 3 ATH primary technical sources, Geddes/Fourcade first-hand theory, multiple peer-reviewed horn/driver papers, and diyAudio independent-practitioner counterarguments. No HF1440 internal outlet-angle specification, calibrated complex source map, or controlled HF1440 horn-angle A/B study was found. Those remain **open physical evidence gaps**, not grounds to assert either 2° or 10.6° is acoustically superior.
