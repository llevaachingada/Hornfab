# HornFab CROWE-style horn: senior research, geometry specification, and controlled experimental plan (V2)

**Research date:** 2026-11-16 (US Eastern). **Status:** read-only research and proposed implementation. No repository changes or fresh acoustic solves were performed. This replaces *recommendations*, not historical data, in the earlier `HornFab_Crowe_Vertical_Control_Engineering_Handoff_2026-11-16.md`.

> **Repository landing note (2026-11-16, CPU geometry only).** This file was moved here from the
> owner's Downloads folder and is the V2 senior research. The forward (no returned lip) area/aspect
> family described in §7 is implemented as the versioned FREEFORM generator
> `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py` (generator name
> `crowe_hv_area_aspect_v1`, schema `crowe-hv-area-aspect-v1`). Geometry-diagnostic configs live in
> `examples/typologies/crowe_hv_area_aspect_2026-11-16/`; they are not queued and no solve was
> launched. Deferred exactly as this document's Phase 2 says: returned lip/roll, rim setback, the
> X crease, `p_progress_start/rate`, the throat-length source study, and any CMA/BoTorch default
> change. The implementation's exact identities, source-tangent construction, validity domain and
> open acoustic gates are recorded in
> `docs/evidence/CROWE_HV_AREA_ASPECT_V1_2026-11-16.md`.
>
> **V2A update (2026-11-16).** The companion
> [`CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md`](CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md)
> supersedes this document on throat transition and parameter count. The implementation now exposes
> exactly four search dimensions (`height_v_active_mm`, `L_forward_mm`, `area_mid_bias`,
> `aspect_timing_u50`); `width_h_active_mm`, `p_mouth` and `throat_round_hold_mm` are fixed
> generator-block values. The 15-40 mm circular-hold rule is withdrawn. Current evidence:
> [`docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md`](../../evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md).
> No solve was launched.

## Executive decision

Retain the current Crowe-reconstruction, rolled-section, Keele Bi-Radial and OSSE-Crowe-X configurations as immutable reference experiments. Build **one new, versioned, canonical CROWE-inspired waveguide geometry family** whose primary coordinates are (i) a constrained cross-sectional area/expansion law, (ii) a separately constrained H/V aspect-development law, (iii) smooth section shape, and (iv) explicitly separated terminal roll. Use the legacy Crowe section as one visual/shape prior, not as the only permitted acoustical trajectory. Preserve the requested bow-tie/X and waisted, substantial rolled lip, but test their effect rather than presuming they improve coverage.

**High-confidence:** the current section family's H/V meridians are largely copies of fixed, digitized contours with size/depth scaling; the existing axial pucker shifts z near the rim and does not create a new vertical mid-flare law. The latest pictured `rf__section_axial_home_smooth_v8` run has a ~293 mm tall shell, markedly broad V near 700 Hz, and a mostly stationary geometry. **Not established:** the best attainable V beamwidth at fixed 480 mm shell height, any guaranteed gains from new curvature variables, or equivalence to Joseph Crowe's unpublished CAD.

## 1. What the literature actually supports

1. **Keele 1982, US4308932A**, and Smith, Keele & Eargle, *Improvements in Monitor Loudspeaker Systems*, JAES 1983: different sidewall functions for the two planes, smooth joining, a source-to-bell transition, and an aperture sized for the low pattern-control frequency. The 1983 figure for the JBL 2344 labels the coverage lower limit around **992 Hz**; the horn is a **100° reference**, not evidence that a 480 mm high horn holds **50° V to 700 Hz**. The paper describes avoiding abrupt flare junctions. The nominal wall/slot dimensions depend on which plane is being referenced; do not transplant them blindly into an HF1440 design.
2. **Henricksen & Ureda 1977/1978, Manta-Ray:** specifically identifies low-frequency V widening and a **tall nonradial mouth with a quadric bell** as ways to address it. This is physical support for a separately sized, late vertical flare.
3. **Cinanni 2020, Hybrid Constant Directivity Horn (AES Paper 10336):** varies mouth geometry while preserving an intended *volume/area expansion progression*. This motivates separating area and aspect controls. Its claimed benefits are not a theorem: equal cross-section area does **not** ensure equal input impedance, radiation efficiency, wavefront curvature or modal coupling in a changing non-axisymmetric horn. Full 3D BEM remains essential.
4. **Batík 2020 OS-SE:** analytic OS/GOS underlying wall + separate smooth superelliptical termination; parameter `n` changes *when* the bell becomes active, `s` changes amount, `k` changes the underlying throat/intermediate expansion. The paper's morphing section separates preserved section, target mouth and morph rate; early morphs can affect coverage. **Batík 2022 R-OSSE** adds a parametric returned termination, useful for a physically integrated free-standing rolled mouth. Do not equate OSSE and R-OSSE parameters of the same names.
5. **Gu, You & Shen 2025 JASA:** actual rectangular-horn shape optimization with loading/efficiency, smoothness and different H/V coverage. The study uses a multimodal numerical model with an algebraically differentiated objective, not an assertion that one closed-form profile solves every horn. Follow its ablation methodology.
6. **Dong et al. 2020/2021/2023 JASA/JSV:** multimodal, multiple-mode modeling; optimized loading and directivity are distinct objectives, often in tension. The 2023 resonant/subwavelength transmission results concern resonant transmission, not proof that a small passive home horn achieves uniform low-frequency pattern control.
7. **Dong, Doc & Félix 2024 JASA:** finite enclosure and baffle can alter low-frequency directivity and sometimes expand a useful control band. The analysis is axisymmetric; whether it helps this CROWE geometry must be checked in the actual cabinet model.
8. **COMSOL horn optimization example:** maximizing on-axis or one off-axis pressure can create severe nulls elsewhere. Use multidirectional, multifrequency objectives and lobe constraints.
9. **Cinanni's actual HCD simulations:** rectangular corners show wavefront and diagonal irregularities. A strong X/superellipse morph can have acoustic costs; score diagonal and entire balloon, not just H/V curves.
10. **JAX-BEM 2026 (Hipperson et al.):** differentiable BEM is a credible longer-term gradient route, but the present demonstration and JAX GPU portability do not justify replacing HornFab's fused-CUDA solver as a prerequisite. First obtain a useful, identifiable 6–10-dimensional geometry with derivative-free search.
11. **Driver source:** FaitalPRO HF1440 nominal throat **35.8 mm**, phase plug radial, exit **'Combined Exit'** with no adaptation throat. Its **minimum crossover 0.7 kHz** is a vendor rating under specified filtering, not proof of low distortion at arbitrary drive level or pattern control. The repo's 36 mm circular opening / 2° tangent / uniform source acceleration are modeling assumptions. A particular Crowe ES-600 model 3150 lists 9° H and 7° V throat half-angles, but those are **that Crowe product**, not the HF1440 exit nor necessarily every ES design. A small angle/source sensitivity matrix is warranted.
12. **Forum triangulation (not authoritative):** a diyAudio HF1440/Crowe ES-600 user reports vertical pattern loss around 1.5 kHz; another detailed discussion of asymmetric home waveguides describes lower-midrange V pattern widening with smaller mouths. These corroborate a physical concern but are not controlled evidence for HornFab's geometry.

## 2. Current repository state and why it moves so little

Repository at inspected default-branch SHA `2c0e2928e932a47975fc284401eafa74ebfc5002` (read-only GitHub connector).

- `hornlab_search/design/generators/_crowe_section_v2.py` uses fixed raster-measured H/V meridians. `_profile()` rescales radius/depth, `_sweep()` reconstructs a constrained pivot/intersection, and `_evaluate()` joins crowned panels. `validate_shape` hard-limits `h_depth_scale` to 0.9–1.1 and `junction_power` to 16–48. These protect a particular reconstruction. Broadening the box without modifying the construction risks geometric failure.
- The historical section optimizer pushes width toward 600 mm, crown toward its ceiling, and sometimes H-depth scale/junction to their bounds. That proves bound pressure, **not** proof that widening arbitrary controls improves acoustics.
- `rolled_family_section_v1` axial relief changes **z** with a localized cosine window. It does **not** give a fundamentally new V radius-versus-depth function. The pictured smooth v8 configuration fixes `g_axial_v_mm=0` after previous optimizations found weak use for it. The PDF is from `rf__section_axial_home_smooth_v8`, 54/60 screens, screen best 6.72, verification best 7.79. On page 2 the V pattern is much broader than 50° near 700 Hz and narrows with frequency.
- `tools/geometry/rolled_rect.py` shares one normalized spiral radial law between H and V, with different amplitude/dimensions and optional z shifts. It is primarily a historical ES-style visual/acoustical baseline, not independently controllable H/V coverage.
- `osse_rollback` provides independent nominal per-plane angles and X superformula blending; the roll/flare size/angle are coupled. Its existing fixed `k`, `sf_n1`, `sf_n2` and `sf_start` should be tested with a geometry/acoustics Jacobian, not all exposed indiscriminately.
- `registry.py` already supports H/V FREEFORM profiles with selectable anchor count and optional monotone-increment shape perturbation. `grid.py` already builds point-grid geometry and outer walls. **Reuse existing FREEFORM/GRID/mesher machinery** and add a versioned generator/resolver; do not create a competing mesher.
- `hl__osse_rrect_fold_warm_v7` already exposes searched `az_fold_v_deg`, `az_fold_v_width_deg`, analogous H controls. This is a useful *ablation/reference* for meridian-fold mechanisms, but it is not the same as a free V expansion-area law. Inspect angle-law code and actual surface displacements before reusing it.
- Existing legacy bridge CLI (`crowe_panel_cli.py`) installs only inside that process. New geometry must materialize canonically in GUI, worker, optimization/BoTorch adapters, caching, and verify/final without process-local monkeypatch dependence.
- The legacy section audit records very acute local faces, up to 176° in one original mesh. This **does not prove inverted triangles**; it mandates intersection, normal, wall-clearance and mesh convergence checks before trusting exceptional scores.

## 3. Stronger mathematical parameterization: area + aspect + section + termination

### 3.1 Forward flare before any returned lip

Let `u=z/L`, 0≤u≤1, where **L is the forward acoustic section length, ending at the chosen lip transition**. Define an always-positive cross-sectional area law `A(u)` and an aspect law `R(u)=a(u)/b(u)` (horizontal half-width over vertical half-height). For a superelliptic cross-section

`(|x|/a(u))^p(u) + (|y|/b(u))^p(u) = 1`, with `p(u)≥2`,

its area is `A(u)=C[p(u)]*a(u)*b(u)` and `C(p)=4*Gamma(1+1/p)^2/Gamma(1+2/p)`. Therefore

`a(u)=sqrt(A(u)*R(u)/C[p(u)])`, `b(u)=sqrt(A(u)/(R(u)*C[p(u)]))`.

This **exactly decouples the geometric enclosed area from the aspect ratio at each cross-section**. It does **not** decouple the *acoustic* phenomena: shape changes can excite transverse modes or shift radiation impedance. That is why full 3D verification is required. At the source use `A(0)=πr0²`, `R(0)=1`, `p(0)=2` and physical source-tangent continuity. For the forward horn require `a'(u)>0`, `b'(u)>0`, no interior contractions and practical curvature bounds.

Recommended implementation basis: **low-order cumulative positive B-spline or monotone Hermite parameterization of `log A(u)`**, with 2–3 localized changes (early, middle, late). Parameterize `log R(u)` separately with a smooth throat-fixed spline. Use `p(u)` as one late mouth/section mode. Use an endpoint-preserving Bézier/Bernstein deformation about a parent curve as an alternative if preserving the exact historic Crowe-like seed is more important than an explicit area law.

An equivalent fully independent H/V spline is a legitimate secondary model. **Compare their effective parameter rank and physical ablations**, rather than declaring the area/aspect construction universally superior. This directly addresses a risk the original handoff underweighted: independent H/V wall splines can inadvertently change area/loading whenever either meridian moves, making the optimizer's discoveries hard to interpret.

### 3.2 Crowe X creases without sacrificing primary shape freedom

Construct the uncreased surface using the area/aspect superellipse. Then introduce a *separate*, bounded angular modifier which is zero on both bisecting planes and strongest toward the diagonals:

`r_X(u,phi)=r_base(u,phi) * [1 + x_amp * B(u) * sin(2phi)^2]`.

Here `B(u)` is a smooth C2 window with zero amplitude and derivatives at the actual driver exit; its onset/peak are separate from the primary H/V law. Positive amplitude expands the diagonals relative to the axes, creating an X/corner-ridge tendency while leaving the exact H/V radii unchanged. A signed variant may be investigated later. **This deformation still changes area, oblique wavefronts and diagonal lobing.** If area preservation is essential for a controlled ablation, renormalize each section with its area calculated numerically and recheck resulting axis dimensions, or treat the X operation as a separate secondary study.

A fourfold Gielis surface can be retained as an alternate appearance mode, but avoid stacking high-dimensional Gielis, Fourier and spline families together initially. Use at most one X strength and one onset parameter in the first acoustic contrast.

### 3.3 A genuine roll and its acoustic attachment

Terminate the *forward* horn into a **C1 and preferably C2 tangent/curvature-compatible parametric return**. The returned portion cannot be expressed as one-valued `r(z)` if it turns backward; represent it as `[z(t,phi),r(t,phi)]`. Suitable reference mechanisms: Batík R-OSSE, smooth circular/Bezier/clothoid-like return constrained by tangent and curvature, or a tested local transition constructed from the forward contour. No unsupported claim that the original Crowe CAD follows one of these equations.

Expose independently: return-start station, effective lip radius, roll extent/wrap, and (if valid) mild H/V differential rim setback. **Do not allow the exterior bead to masquerade as a larger active aperture.** Record first forward-radial/axial turning station per azimuth and projected opening size. That is a *geometric proxy*, not a direct measurement of acoustic aperture velocity participation.

### 3.4 Check characteristic surfaces beyond the axial bisectors

Record curvature, flare/tangent angle, normal smoothness and acoustic output at H, V, 22.5°, 45°, 67.5°. A horn can have excellent H/V curves and poor diagonals or side lobes. A highly squared superellipse or aggressive X ridge deserves a particularly severe diagonal audit, consistent with Cinanni's rectangular-mouth examples and existing HornFab `diag` residual.

## 4. Prioritized additional parameters

**Phase 1: immediately test/optimize, approximately 7–9 active dimensions after rank pruning**

| Parameter or coordinate | Purpose | Initial proposed range or contrasts | Caveat |
|---|---|---|---|
| `height_v_active_mm` | True V aperture budget | 300, 420, 480; 600–800 in discovery | Actual external shell may be larger; test independent height vs shape effects |
| `width_h_active_mm` | Preserve H control | near 550–600 production, held where possible | H may change if constrained area law forces coupling |
| `L_forward_mm` | Length/time for expansion and modal development | 220–340 initial exploration | Larger horns expensive; hard source geometry remains fixed |
| `area_mid_rate` | Early/mid loading progression | 3-level normalized perturbation about parent | Must remain positive and geometrically smooth |
| `area_late_rate` | Where terminal expansion accelerates | 3-level localized perturbation | Can move mouth and loading, needs controlled endpoints |
| `aspect_mid` | Round-to-landscape development timing | early vs late | Interacts with acoustic modes and oblique polars |
| `aspect_late` | Independent final V/H development | 3-level perturbation | Check a', b' monotonic and dimensions |
| `v_exit_angle_mid` or `v_curve_knee` | Sets middle V tangent near HF pattern | alternate basis to area/aspect coefficients | Do not keep if near-collinear with aspect_mid |
| `p_mouth` | Cross-section roundness | 2, ~3.5, ~5 as ablation | Rectangle corners can worsen diagonals |

**Phase 2: expose only after actual sensitivity evidence**

- `x_amp`, `x_start`, optionally one X station peak. These are styling *and* acoustic variables; add when base H/V aperture goal is working.
- `lip_radius_mm`, `roll_start`, `roll_wrap_deg`, **independent** H/V roll size/forward setback only when mesh validity and strong sensitivity are proven. A/B rolled versus short smooth termination first.
- `v_mid_slope` and `v_late_curvature` as alternative coordinates to `aspect_mid/aspect_late` if those provide poorer conditioning. Prefer the basis that exposes orthogonal surface motions, not the largest raw knob list.
- `p_progress_start` and `p_progress_rate`, but not both together unless geometry Jacobian shows distinct responses.
- `throat_blend_length_mm` / driver-interface tangent **as a source-uncertainty study**, not as an unconstrained extra scoring knob; Faital's combined exit angle is unspecified, so optimization against an invented throat boundary risks false precision.
- `rim_setback_hv` if terminal phase/window interference warrants it, but beware returning-surface self-contact and shell clearance.
- `flange/baffle width, enclosure chamfer/fillet, baffle inset` as separately **frozen product conditions or paired studies**, never as nuisance parameters swept inside the core horn search without a declared mounting target.

**Deprioritize:** more axial-pucker amplitude alone; unrestricted junction-power extension from 16–48; dozens of radial Fourier coefficients; diffraction slots/fins/multicell elements as an immediate patch; optimizing high-frequency response with the current ideal uniform throat acceleration beyond its known model confidence. The slots/fins and newer 1P wave-shaping literature are interesting *separate architectures*, not a free replacement for missing V aperture at 700 Hz.

## 5. Geometry-only admission gate before BEM

Sample at least 40–80 Sobol/geometric candidates and full-range ± perturbations around 3 representative parents. For every knob, generate actual **inner and outer** acoustic surfaces using the same canonical resolver that production solves call.

Record:
- H/V/diagonal meridian overlays in actual millimeters, local tangents and curvature vs forward z; 3D same-camera comparisons.
- Projected `width`, `height`, `forward_lip_station`, total shell dimensions; `A(z)`, `d log A/dz`, `log R(z)`, `p(z)` at standardized fractions of L; X/lip as separately identified geometry.
- A standardized **geometry Jacobian**: normalized 0–1 parameter perturbations against sampled inner surface coordinates and derived area/aspect/curvature descriptors. SVD/effective rank, singular vectors, near-collinear parameter pairs. Drop dormant or redundant dimensions, not just near-zero steps in a UI.
- Exactly round driver coupling, bounded/continuous tangent, monotone forward radial expansion, positive thickness, no collision/near-contact of inner and outer, no cross-row surface intersection, proper orientation and triangle quality after meshing. Test a few extremes at increased angular/station sampling to catch missed intersections.
- Compare source/mesh/geometry hashes across GUI preview, CLI/cold subprocess, CMA evaluation, BoTorch materialization and verify. Any path producing a different surface is a blocker. A preview alone does not prove canonical BEM geometry.

**Acceptance:** at least six distinguishable parameter directions cause intentional localized inner-wall changes (not only exterior lip or near-duplicate uniform scaling); no unexamined dormant or collinear knobs; preflight valid fraction >85% for initial bounded DOE, excluding deliberately oversized/report-only designs; exact legacy saved-geometry replay unchanged. Do not set arbitrary 10–50 mm movement minima independent of the control and mesh scale; use relevance to physical scale and numerical resolution.

## 6. Acoustic screening and objectives: no cosmetic score victories

### 6.1 First evaluate the attainable V aperture-height frontier

Use **the same** HF1440 ideal source assumption, mount condition, H mouth and background solver settings. Design a small matched factorial:

- 3 production heights near 300, 420, 480 mm, plus 2 discovery heights 600 and ~780 mm. These are **requested forward-mouth targets**, subject to realized shell/inner dimensions.
- Two meridian laws at each height: original scalable section reconstruction, and controlled-area/aspect redesigned flare. Include a Keele/OSSE H/V geometry of comparable size as an external control.
- At a few points A/B vary area progression with height held fixed, and vary aspect progression with area trajectory held fixed, to identify mechanisms.
- Include one return-on/off pair at fixed forward-mouth contour and one X-ridge-on/off pair after the main controls are understood.

A dozen or two low-band screens is a plausible bounded pilot. Actual number depends on the geometry feasibility and matched controls found in existing solve cache.

**Crucial confound:** varying total horn height and its internal flare simultaneously does not isolate the effect of vertical aperture. At least one matched geometry subset must change height while keeping the normalized contour law fixed, and another must change law at the same height.

### 6.2 Low-frequency screening avoids needless full-high-frequency dense meshes

Do an initial **600–2500 Hz** band covering 600, 700, 800, 900, 1000, 1100, 1200, 1400, 1600, 2000, 2500 Hz, and add interpolated/anomaly points on finalists. Use a convergence-tested mesh *for this band*, separately versioned and never compared numerically as if it were an 8 kHz full-band solve. This may be substantially cheaper for larger horns on an 8-GB CUDA GPU. The mesh/solver must obey tested wavelength/curvature/source constraints, not simply force fewer nodes to fit VRAM. Select finalists for full **350 Hz–8 kHz** verification and an appropriate higher-frequency spot check if desired. Do not train one BO GP on mixed and unlabeled solver/frequency fidelities.

### 6.3 Measurement target and constraint logic

At each frequency save H/V main-lobe `-6 dB` width, outermost threshold crossing width, disconnected lobe flags, sidelobe energy, 45°+ diagonal polars, full-balloon DI and directivity uniformity, impedance/load and on-axis response. Missing crossings are **censored/flagged**, not silently replaced with a favorable 180°.

Use a **report-only, frequency-specific vertical pattern gate**, whose feasible curve is selected *after* the aperture frontier, not an assumed universal 50° target at 700 Hz. For illustration, the diagnostic can report violations of `V_width ≤ 90° at 1200 Hz` and `V_width ≤ 60–65° at 1600 Hz`; those are research thresholds, not known feasible objectives. Preserve a lower width bound to prevent over-narrow vertical beam/crossover nulls. Define a control onset requiring sustained conformance over adjacent sampled frequencies, not a single crossing.

Compare Pareto outcomes across: (a) V lower-midrange control/onset, (b) H coverage and diagonal/lobe quality, (c) loading/efficiency and response smoothness, (d) total physical size. **Never infer success from a lower v7 scalar alone.** Do not directly compare `J_base` against `J_smooth`, whose DI slope targets, weights and coverage tolerances differ. Existing v7 smooth target +5 dB/dec still has `std(DI)` penalty and constant numeric 80°×50° H/V target; it is not an actual sloping beamwidth target.

### 6.4 Validation needed for product decisions

High-fidelity verification: at least three candidate geometries and two references, identical frequencies/receiver balloon/angle count, mesh convergence on the relevant frequency band, and independent CPU solver cross-check where affordable. The current PDF screen-to-verify difference demonstrates why. Test an actual cabinet/baffle condition and (if physically possible) a real HF1440 horn prototype before claims about full-system performance. **Minimum crossover from driver datasheet is not equivalent to realized pattern-control onset.**

## 7. What to implement in the repository, without breaking historical work

**New, versioned path:** `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py` (or a more concise name that follows the repo catalog). Generate `FREEFORM` H and V meridians with an explicit bounded smooth section/shell and, if necessary, new canonical point-grid return to preserve the true roll. Do not hard-edit `_crowe_section_v2.py`, `tools/geometry/crowe_panel.py`, the current config names, or frozen run observations. Add new YAMLs and schema/implementation digest that pins all dependencies.

1. **Math/unit and identity tests:** circle/ellipse/superellipse exact area; throat `R=1,p=2`; positive axis derivatives; C1/C2 continuity; numerical surface convergence; source and shell equivalence; duplicate detection; deterministic seed recreation in cold workers; real geometry differs predictably when each knob moves.
2. **3D geometry tests:** full inner and outer surface closed/clear; no self-contact, split winding, degenerate role tags, bogus source cap or invalid full exterior. Validate at quarter symmetry and at representative full reconstructed surfaces.
3. **Renderer + GUI:** expose `A(z)`, aspect(z), vertical tangent/flare, first forward lip, roll control and H/V/diagonal sections, plus shape parameter sensitivity overlay. Reuse the **solver's actual mesh** in 3D. Do not let a simplified preview pass tests while solve-bound geometry differs.
4. **CMA and optional BoTorch:** initially compare a bounded DOE and CMA-ES on 6–10 rank-validated variables. BoTorch can be enabled only after materializer supports both inner and outer surfaces and the cohort is comparable in brief/source/fidelity. Warm-start only from data re-parameterized in physical units under the **new** bounds; never relabel old normalized vectors.
5. **Objective:** maintain existing historical v7 scores; store raw physical outputs and a separately versioned `crowe_vertical_frontier` diagnostic/Pareto score. Avoid inserting a new universal optimizer default before physical tests.
6. **Queues:** inspect local **live** status before touching a running job. Repo manifests are historical/plan evidence; not authority for whether jobs finished. No new solve is authorized by this document. Do not edit a live worker's versioned code or its pinned study package.

## 8. Go/no-go criteria

**Go from geometry to BEM only when:** the new family produces meaningfully different vertical wall contours at fixed overall height, can keep H/diagonal contours reasonably smooth, passes real inner/outer mesh tests across its bounded domain, and cold replay is identical.

**Go from pilot to optimization only when:** at least one area/aspect change improves **verified V behavior at the same effective aperture height** without a worse H/diagonal lobe disaster or loading collapse, or an oversized reference quantitatively establishes the trade-off frontier. If only larger apertures improve the low-frequency V pattern, stop inventing ever more spline controls and revisit the size/target/crossover trade-off.

**Product success:** compare the best printable ≤600W×480H×480D horn to the historically best verified reference on the *same source, mounting, fidelity and objective/physical metrics*. Show beamwidth at 700/900/1200/1600/2500 Hz with both vertical and horizontal polars, full balloon, on-axis, loading, cross-over relevance, shell dimensions and verified computational cost. Report absolute degrees and uncertainty, not only percent J improvement.

## 9. Primary research and useful contrary evidence (links)

1. Keele US4308932A: https://patents.google.com/patent/US4308932A
2. Smith/Keele/Eargle 1983 JBL monitor paper with Fig. 1: https://www.cieri.net/Documenti/JBL/Documenti%20tecnici/JBL%20-%20Improvements%20in%20Monitor%20Loudspeaker%20Systems%20%28Smith%2C%20Keele%2C%20Eargle%29%20%281983%29.pdf
3. JBL 2344A beamwidth and DI: https://jblpro.com/ko/site_elements/2344a-information
4. Henricksen & Ureda 1978: https://aes.org/publications/elibrary-page/?id=3249
5. Cinanni 2020 HCD: https://www.speakerlab.it/resources/HCD.pdf and https://aes.org/publications/elibrary-page/?id=20753
6. Batík 2020 OS-SE: https://at-horns.eu/release/OS-SE%20Waveguide.pdf
7. Batík 2022 R-OSSE: https://www.at-horns.eu/release/R-OSSE%20Waveguide.pdf
8. Gu/You/Shen JASA 2025: https://doi.org/10.1121/10.0039253
9. Dong/Gao/Feng/Shen JASA 2021: https://doi.org/10.1121/10.0003568
10. Dong/Shen/Gao JASA 2020: https://doi.org/10.1121/10.0001037
11. Dong/Doc/Félix JSV 2023: https://www.sciencedirect.com/science/article/pii/S0022460X23001955
12. Dong/Doc/Félix finite enclosure JASA 2024: https://doi.org/10.1121/10.0025389
13. COMSOL horn optimization caution: https://doc.comsol.com/6.3/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html
14. FaitalPRO HF1440 primary: https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185
15. Joseph Crowe ES-600 spec and claimed roll: https://josephcrowe.com/blogs/news/es-600-biradial-horn
16. Crowe ES-600 model 3150 baffle version: https://josephcrowe.com/products/es-600-biradial-horn-no-3150-baffle-mount-version
17. HornFab own audit: https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/audit_2026-11-15/READINESS.md
18. HornFab own section source: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/_crowe_section_v2.py
19. HornFab own rolled master: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/rolled_family.py
20. HornFab source-generation registry (existing FREEFORM): https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/registry.py
21. DIY horn-waveguide caution: https://www.diyaudio.com/community/threads/is-it-best-to-use-a-non-axisymmetric-waveguide.375799/
22. DIY user HF1440 + Crowe anecdote: https://www.diyaudio.com/community/threads/hf1440-new-ring-compression-driver-from-faital-pro.336505/page-13
23. JAX-BEM 2026 for *later* gradients: https://arxiv.org/abs/2604.21431
24. 2022 single-parameter wave-shaping and 2023 iterative metrics, alternative architecture: https://aes.org/publications/elibrary/elibrary-page/?id=21894 and https://aes.org/publications/elibrary-page/?id=22300
25. Cinanni experimental wavefront, corner issue: https://www.speakerlab.it/resources/HCD.pdf

### Research standards

Patent/academic/manufacturer papers establish mathematical construction, authors' models and measured examples, not guaranteed transfer to this setup. Crowe's original proprietary ES geometry is **not available**; geometry claimed as Crowe-inspired must remain labeled reconstruction. The preserved repo PDF and historical runs establish what occurred with the recorded source and scoring identities; they do not prove high-fidelity physical validity. Future acoustic gains, best parameters, exact coverage frequency, effect of X ridges and lips, and final system loading remain open until the matched experiments above are completed.
