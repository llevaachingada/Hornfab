# HornFab CROWE vertical-control V2A addendum: throat transition, parameter economy, and geometry validation

**Companion to:** `HornFab_CROWE_Vertical_Control_Senior_Research_V2_2026-11-16.md` (read in full before implementation).  
**Research date:** 2026-11-16 US Eastern. **Inspection basis:** user's metallic/ridges-on 3D screenshot; HornFab repository default-branch source viewed via connected GitHub at `2c0e2928e932a47975fc284401eafa74ebfc5002`; cited primary research below. **Status:** design/research only. No repository edits, local meshes, new BEM simulations, or optimization runs have been executed for this addendum. Local live branch and queued studies may differ from GitHub.

> **Repository landing note (2026-11-16, CPU geometry only).** This file is the V2A companion to
> the V2 senior research and is now the authority for throat transition and parameter count. The
> forward family is implemented in `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py`
> with exactly four search dimensions (`height_v_active_mm`, `L_forward_mm`, `area_mid_bias`,
> `aspect_timing_u50`); `width_h_active_mm`, `p_mouth` and `throat_round_hold_mm` are fixed
> generator-block values (hold default 0; a fixed 20 mm A/B config exists). The prior chat's
> 15-40 mm circular-hold rule is withdrawn and is not enforced. The X crease, returned lip and rim
> setback remain Phase 2. Evidence: `docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md`.
> No solve, GPU job or queue change is authorised by this landing.

## Decision: modify V2, do not add a forest of new sliders

**Retain** V2's one new versioned CROWE-inspired **area + aspect + cross-section + separate lip** family, and its aperture-height/frontier experiment. **Tighten** V2's initial optimization from a tentative 7–9 variables to **four genuinely independent continuous variables** with a fifth added *only if* a geometry- and acoustic-sensitivity ablation establishes value. Freeze or derive throat roundness, blend onset, X onset, superellipse progression, and lip shape in the first campaign. Test a small number of categorical construction alternatives outside the optimizer, rather than sampling their settings as independent continuous GP/CMA dimensions.

The prior chat's suggestion to *require a 15–40 mm circular hold* is **withdrawn as a universal design rule**. A circular source plane, a sufficiently smooth near-throat transition, and bounded shape derivatives are necessary engineering targets; a specified straight or circular corridor of arbitrary length is not proven beneficial. It may cost axial development length and can alter modal behavior. Importantly, Marcel Batík's published ATH CORE example starts the rounded-rectangle morph **at the throat** (`Morph.FixedPart=0`, `Morph.Rate=3`) and reports favorable BEM behavior. That is an existence counterexample to a mandatory positive round-hold distance. Test zero and delayed onset under matched physical conditions if the actual section diagnostics justify the experiment. [S1][S2]

## A. What the screenshot proves, and what it does not

The screenshot shows the GUI controls `surface: metallic` and `ridges: on (default)` plus white jagged/triangular-looking lines converging near the throat. **It does not identify the run/config/mesh hash and does not establish the actual radial cross-sectional shape.**

Critical source check: `hornlab_search/gui/static/view3d.js`, `buildRidgeGeometry`, is a *rendering overlay*: it welds close vertex positions at approximately 0.01 mm in the mesh's metric units, evaluates the dihedral of paired triangle faces, retains a limited set of the sharpest edges (plus appropriate unmatched boundaries), and draws near-white lines. The user's `ridges` dropdown controls the overlay, **not the solver's mesh or physical X-ridge geometry**. Its geometry is generated from the supplied mesh, so an edge can be a genuine sharp feature, a source-cap/seam/triangulation effect, or just more visually prominent in metallic/ridges-on mode. The algorithm uses `abs(dot)` in its edge-angle calculation; this visualization is **not an orientation or inverted-triangle audit**. [R1]

**Required diagnostic before any 'fix':**

1. Retrieve the exact design ID, configuration, source/brief identity, actual stored `.msh`, mesh hash, and GUI shape payload for the screenshot. Identify which CROWE route it uses: `crowe_panel`, `rolled_family_section_v1`, `osse_rollback`/Crowe-X, or another one. **Do not extrapolate from one to the others**.
2. With identical camera/light/mesh, capture `ridges=on`, `ridges=off`, and a *true mesh wireframe* (a diagnostic mode, not the stylized ridge overlay). Include a cutaway from inside the throat facing out and a view of the driver/source cap separately.
3. From the *solver-bound inner surface*, take real sections at **z=0, 5, 10, 20, 40, 60 and 100 mm** (where present). Plot x/y shapes on the same scale and compute area, half-axes, aspect, a shape-roundness descriptor, and 0/45/90-degree wall slope and curvature. The reference is **physical z in mm measured from the coupling plane**, not an arbitrary sample index.
4. For each interval, plot minimum and 95th-percentile face dihedral, inverted/misoriented face counts by mesh role, source-cap-to-wall seam quality, local triangle aspect ratio, and analytic-vs-mesh surface deviation. Evaluate inner and exterior separately. The old Crowe section audit showed some acute junction normals, but **did not prove inverted faces**; do not call the whole family broken from an edge visualization alone. [R2]
5. If `ridges=off` removes the zigzag and the sampled sections/tangents are smooth, classify as a **viewer/mesh-display observation** and do **not** modify geometry to hide lines. If the physical section rapidly develops corners, the generator may require a **derived smoother section law**. If there is an actual geometrical kink, clearance loss, or cap/shell fold, that is a **mesh/geometry blocker**, not an optimization opportunity.

**Important station-convention trap in the existing code:** in `grid.py`, the Crowe-X `sf_start` is applied through a **normalized meridian arc length** (`l_arc/l_arc[-1]`) before the lip, not through `z/L`. In `rolled_family.py`, `relief_start_s` refers to the sampled parent arc/station coordinate, and the parent may include a return. A value of `0.25` **does not mean** the X starts 25% of the forward axial depth. The new family should define a **forward-section coordinate `u=z/L_forward`** up to its first turnaround, and report the actual x/y/z onset in millimeters. [R3][R4]

## B. What the research permits us to claim

| Evidence | Implication for the design | What it *does not* prove |
|---|---|---|
| Batík, **OS-SE**, section 5: preserves a fixed part `z<z_f` and otherwise morphs with power `γ≥1`; `γ=1` introduces a slope break at onset. [S1] | Use **smooth shape progression** and test derivatives at any activation point; if using a power onset, `γ≥3` can zero the first two derivatives at the start, assuming the underlying morph contribution is smooth. A bounded quintic smootherstep is another candidate. | That larger round-hold length is better, or that morphing at `z=0` is flawed. |
| Batík, **ATH CORE** uses fixed part `0` and morph rate `3`. [S2] | Starting *smoothly* at the throat is an accepted research/design approach. | It transfers as-is to the HF1440 or Crowe geometry. |
| Cinanni, **Hybrid Constant Directivity Horn**: reshapes aspect while retaining a selected volume-expansion law; compares wavefront/directivity and impedance. [S3] | Keep `A(z)` and `R(z)` distinct mathematical controls. | Equal geometric area makes two 3D horns acoustically equivalent. |
| Gu/You/Shen, **JASA 2025**: objectives for efficiency, H/V directivity, and smoothness; ablates objective terms. [S4] | Favor a **small, well-conditioned design space** and diagnose each term separately. | A large unrestricted spline is necessary. |
| Kolbrek, **AES 2020**: single-surface horn compromises among throat, coverage and frequency limits. [S5] | Do not expect delayed squaring or freeform shaping alone to defeat an insufficient 700 Hz V aperture. | Every apparent limitation is a software error. |
| Makarski & Behler, **AES 2004**, and Makarski dissertation: the real driver velocity/modal field can affect predicted high-frequency radiation. [S6][S7] | Freeze the source boundary for geometry experiments; test assumptions separately. | A nominally smooth 2-degree circular surrogate establishes real HF1440 coupling. |
| FaitalPRO HF1440: 35.8 mm throat, `Combined Exit`, no adaptation throat. [S8] | Do not insert an arbitrarily long constant-radius adapter; the source angle is not a published 2-degree specification. | The horn should have an imposed 15–40 mm circular duct. |
| COMSOL horn optimization, 2026 acoustic B-spline study, and classic smoothness-regularization work. [S9][S10][S11] | More control points mean more local variation, conditioning problems, and invalid shapes. Start low-order, increase rank only against evidence. | More parameters necessarily improve a global search at equal BEM budget. |
| Keele Bi-Radial and Manta-Ray precedents. [S12][S13] | Actual H/V wall progression and aperture size matter to low-frequency control. | A specific Crowe-inspired shell will hold 50° V at 700 Hz in 480 mm total height. |

**Research-quality clarification:** Most papers above demonstrate mechanisms, models and particular horns. They do not isolate the contribution of an early square transition in HornFab. The screenshot diagnosis requires source geometry measurement, followed by matched BEM. Treat all proposed onset distances and coefficients below as **experimental bounds, not validated optimums**.

## C. Minimal mathematical contract, tied to V2

Define the **forward-only** section for `u=z/L_forward ∈ [0,1]`; handle the returned lip with separate parametric coordinates beyond `u=1`. Let `A(u)` be positive area, `R(u)=a(u)/b(u)` positive H/V semi-axis ratio, and `p(u)` the superellipse exponent. Then

```
C(p) = 4 Γ(1+1/p)^2 / Γ(1+2/p)
a(u) = sqrt(A(u) R(u) / C(p(u)))
b(u) = sqrt(A(u) / (R(u) C(p(u))))
section: |x/a(u)|^p(u) + |y/b(u)|^p(u) = 1
```

At the driver coupling plane **exactly**: `a(0)=b(0)=r0`, `R(0)=1`, `p(0)=2`, `A(0)=πr0²`. The baseline must honor the **assumed** source tangent `a'(0)=b'(0)=tan(a0)`; equivalently, with `p'(0)=R'(0)=0`, `d log A/dz |0 = 2 tan(a0)/r0`. This is a mathematical **interface consistency check**, not validation that `a0=2°` is the actual HF1440 exit field. Freeze the historical 18 mm / 2° ideal-source *only for matched comparisons*; a later driver-informed 17.9 mm/alternative-source study requires new provenance and potentially new solves.

**Recommended construction:** use a C2-smooth, monotone, endpoint/tangent-constrained baseline for `log A(u)`, then **one** interior area-bias basis `β_A B_A(u)` where the basis and its first two derivatives vanish at the endpoints. Derive its endpoint from the chosen *active* H/V mouth dimensions and `p_mouth`. Independently interpolate `log R(u)` from 0 to the exact mouth aspect ratio through a **one-parameter monotone timing law**; constrain zero initial first/second derivatives. Let the section exponent use **the same timing envelope**, not a newly optimized start/rate:

```
p(u) = 2 + (p_mouth_fixed - 2) S_R(u)
log R(u) = log R_mouth * S_R(u)
```

Here `S_R(u)` is a bounded C2 step from 0 to 1 with **one** timing coordinate (e.g. the physical `u_50` where half of the aspect development has happened). The baseline `A(u)` and the `R(u)` law together must satisfy `a'(z)>0`, `b'(z)>0` through the forward horn and bounded curvature. The above is a proposed *coordinate system*, **not executable HornFab syntax**. The implementer must validate that actual interpolation/meshing reproduces it; mere `crossSections` endpoint declarations may not preserve a desired C2 law in the installed mesher.

This structure has an important consequence: **the horn can increase area continuously while staying close to circular near the source**, *without* an independent `round_hold_mm`, `aspect_start_s`, `aspect_mid_s`, `aspect_end_s`, `p_start_s`, and `p_rate`. All are either fixed or consequences of one physically interpretable aspect-timing coordinate.

### Smoothness is a constraint, not another search variable

- Implement analytic or stable numerical tests of radial/axial derivatives near the source, flare-to-lip junction, and at representative azimuths. C1 means tangent continuity; C2 means curvature continuity. Do not claim C2 because an outer mesh looks smooth at one resolution.
- Require finite, positive cross-sectional dimensions, nonnegative forward opening, bounded changes in curvature and positive inner-to-outer clearance. Feasibility envelopes should be **computed** from source geometry and current wall thickness, not represented by extra penalty-weight knobs.
- A short positive `round_hold` is *not* inherently necessary. If the design needs a fixed opening period, use a smooth **expanding circular** corridor, never automatically a constant-radius tube. With any hold/boundary, use zero first/second shape-change derivatives at the activation position to avoid a new kink.
- A ridge angular modifier must have zero deformation and derivatives at the source. Its *physical* onset should be linked to `S_R(u)` or a fixed fraction of forward depth. A lip can be C1 tangent-continuous but still have a curvature step: the existing `append_tangent_lip()` uses a circular arc fitted to the terminal tangent, and is **not automatically C2**. [R3]

## D. Parameter decision table: four at first, one conditional

### D1. Initial fixed-geometry aperture study (lowest-cost)

For matched diagnostic BEM, use **discrete** active V heights of approximately **300, 420, 480 mm** inside the production envelope, and one or two taller **discovery-only** reference sizes. Choose fixed active H width (for example ~560–580 mm) and one fixed forward length for this initial matrix, subject to actual **outer shell** limits. This factors out size, allowing 2–3 changes to the *shape* alone; do not call these a continuous optimizer yet. These values are study landmarks, not claimed optimal radiating-aperture sizes.

### D2. First real optimization, production envelope

| Control | Mode | Suggested first domain | Why keep or lock |
|---|---|---|---|
| `height_v_active_mm` | **SEARCH #1** | Approximately **300–480 mm**, but *derive a conservative inner-height upper bound* from actual lip/exterior clearance so the 480 mm total-shell brief is met | Only direct size lever to improve 700–1600 Hz V aperture; evaluate size as an objective/constraint too. |
| `L_forward_mm` | **SEARCH #2** | Approximately **220–340 mm** subject to back-of-horn footprint, driver mounting, clearance and meshing | Changes available flare development length and wall curvature. |
| `area_mid_bias` (`β_A`) | **SEARCH #3** | Start with normalized relative mid-area deviations about **-15% to +15%** (log-area bias roughly ±0.14) then trim by monotonicity/curvature feasibility; *not* a fixed raw spline-coordinate range | One meaningful loading/shape lever; no independent area-early and area-late knobs yet. |
| `aspect_timing_u50` | **SEARCH #4** | Initial geometry-only corners around **0.35–0.65** of *forward depth*; narrow/change after measuring actual wall movement and validity | Controls **when** the H/V separation develops. Replaces several redundant onset/rate controls. |
| `vertical_mid_shape` **or** a second aspect mode | **CONDITIONAL #5** | Add one bounded, endpoint/tangent-preserving V-localized basis only if #3/#4 lack useful independent V motion at fixed height and H directivity | Do not add both this and `v_mid_angle`/`v_knee`/`aspect_mid_bias`/`aspect_late_bias`. Choose the best-conditioned one from the Jacobian. |

**Initial locked/derived values** (do not make CMA/BoTorch dimensions):

- `width_h_active_mm`: **fixed** at a reference production value (~560–580 mm) during the *vertical-control* experiment. If it produces serious H-pattern sacrifices, **replace** the weakest shape parameter with H width or add it later as the only sixth control. Do not give up H control silently.
- Driver throat diameter, source cap and tangent: **fixed to the existing source model for matched tests**; run separate source-assumption A/B later. There is no independent `throat_angle`, `throat_blend`, or `round_hold` search during the first campaign.
- `p_mouth`: fixed to a *visually tolerable* intermediate section exponent (provisional **~3–3.5**); `p(0)=2`, with its transition **derived from** `S_R`. Compare mouth p≈2.2 vs 3.5 (or another small pair) as a separate A/B test, not a fifth continuous dimension.
- `x_strength` / `x_start` / `x_peak` / `sf_n1` / `sf_n2`: no independent search initially. Preserve a restrained, predefined CROWE-inspired aesthetic version and a **zero-X control**. With X on, derive its onset from the same aspect law; preserve zero derivatives at the source. Report any change in section area/diagonal polar response.
- `lip_radius`, `roll_wrap`, `roll_start`, `h/v_roll_setback`: fixed to one physically validated reference termination **while studying the forward flare**. Run a small rolled-vs-unrolled or 2-radius A/B at identical forward surfaces. Do not search lip and forward shape simultaneously before knowing which affects the physical objective.
- `throat_round_hold_mm`: **not a default search variable** and **not forced to 15–40 mm**. If the exact-mesh diagnosis finds rapid early cross-section distortion or poor source-mode sensitivity, evaluate two discrete onset policies such as `onset=0` and `~20 mm expanding-circular hold` under identical mouth/end conditions. Record the loss of flare length and compare broadband loading/HF polars.
- `p_progress_start`, `p_progress_rate`, `ridge_start`, `ridge_width`, `ridge_decay`, extra Fourier orders, `junction_power`, wall thickness, mesh station counts and regularization weights: fixed or derived engineering/model choices, not independent search coordinates initially.

**Why four?** Adding a knob does not directly make each BEM solve slower, but it increases the volume and interaction structure of the search, usually requiring more unique expensive solves for CMA-ES/GP models to learn useful effects. The literature offers no universal optimum dimension count. Four is a **deliberate pilot budget**, to be revised based on physical Jacobian rank, geometry feasibility and acoustic value, not a claim that a fifth variable is mathematically unnecessary. [S4][S9][S10]

### D3. Explicit 'two alternatives, not five knobs' rule

If the first geometry shows poor V development, compare two low-dimensional bases **with the same four-variable budget**:

- **Basis A:** area-bias + aspect-transition timing (default).
- **Basis B:** area-bias + one bounded vertical-mid curvature/tangent perturbation, with aspect timing derived.

Choose whichever makes physically independent and useful wall motion **without** producing throat kinks or problematic H/diagonal modes. Do not combine them as three simultaneous shape variables merely because all controls can be coded.

## E. Implementation locations and test requirements

### Versioning, code-path and ownership

- **New canonical generator:** `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py` (V2 recommendation), or an equivalently versioned code path. **Do not modify** `hornlab_search/design/generators/_crowe_section_v2.py` or the original `tools/geometry/crowe_panel.py`: their original metrics, digests and replay are evidence.
- **Dispatch/meshing:** reuse `hornlab_search/design/generators/grid.py`, native `FREEFORM`/point-grid infrastructure and the existing `hornlab_mesher`. Only select `FREEFORM` if the actual solver-bound loft matches `A/R/p` and derivatives; otherwise add a **single canonical point-grid resolver**, not CLI monkeypatches. Pin full inner+outer surfaces and all generator-dependency digests in design identity.
- **Source/mesh verification:** `hornlab_search/mesh/throat_check.py`, existing grid self-approach checks, `docs/research/typologies/audit_2026-11-15/geometry_controls.py`, and topology/orientation checks. The legacy design uses explicit exterior geometry and a short source blend: don't replace it with an unrelated dummy shell.
- **GUI:** `hornlab_search/gui/static/view3d.js` documents the nonphysical ridge-line overlay. Keep that for display, but provide a **clear diagnostic toggle** or export demonstrating actual triangles/dihedrals and physical sections. Label the white edge overlay *rendered mesh edges*, not actual ridge geometry. Use the very same saved solve-bound mesh to avoid GUI/solver disagreement.
- **Search/BO:** the new version needs verified identity in `DesignSpace`/`GeneratedSpace`, search worker and `hornlab_search/bo/data.py` materialization. Existing BO does **not** automatically support arbitrary point-grid recipes. Preserve old data; never train on old [0,1] vectors as if they were the new parameter domain. Use the existing 100-row or other runtime admission gate as implemented, do not claim this pilot is automatically BO-ready.

### Non-negotiable tests and acceptance

1. **Exact throat:** identical round source cross-section in all azimuths at z=0; no double-applied throat blend; finite a/b derivatives matching the chosen *model* interface angle; first/second radial and normal derivative continuity over the transition. Test angle-vs-reconstructed-source secants with sampling refinement.
2. **Physical shape:** sections at 0/5/10/20/40/60/100 mm; plot area, aspect, `p(z)`, 0/22.5/45/67.5/90-degree radial and axial tangents. No false `z/L` labels for arc length. `A(z)` monotone, both half-axes expand, positive wall-to-shell clearance, bounded curvature, no negative area or self intersections.
3. **Optimization identifiability:** perturb each of the four variables by ±10% of **its normalized box** at three distinct parent designs; collect normalized vertex-displacement/area/aspect/curvature Jacobian. Compute SVD and pairwise collinearity; remove a variable if dormant, a disguised scale of another, or consistently below a mesh-resolvable displacement. Do not make thresholds arbitrary: compare against observed discretization and intended acoustic resolution.
4. **Geometry work budget:** 40–80 Sobol points plus extreme/paired corners; real CPU meshing and fresh-process replay, full inner and outer surfaces, exact source role tags and orientation. Require high valid fraction (initial design goal **≥85%** for the regular box), or redesign the box before expensive optimization.
5. **Visual/source artifacts:** `ridges=on/off`, true wireframe, section plot, analytic-to-mesh distance and high-dihedral coordinates for the screenshot's original saved design. Do not treat the ridge overlay as acoustic truth or simply hide an invalid mesh with smoother material.
6. **Acoustic ablations:** at matched *actual active height and H width*, compare no-X vs restrained-X, immediate smooth morph vs delayed expanding-circular morph (only if geometry suggests it), with/without mouth roll. Keep each A/B isolated and compare 700/900/1200/1600/2500 Hz V/H/diagonal, loading and full balloon. Include **4–8 kHz spot checks** on shortlisted variants because a throat/morph transition may affect upper-band modes while low-band-only screening misses them.
7. **Full-band finalists:** same mesh/source/mount and frequency grid, directivity, vertical control-onset, DI, loading, sidelobes, H/V/diagonals, high-frequency behavior and print constraints. Any improvement must be **verified at the same effective active aperture** and without major H/diagonal/loading regression. Do not substitute a better v7 scalar J; historical base-vs-smooth scores remain separate.
8. **No default mutation:** No production geometry/scoring default changes, no active queue change, no new solve launch from this addendum. Stage new configs under new names and freeze their source/brief/mounting identities.

## F. Agent task tickets (execute in order)

**T0 – screenshot forensic audit, no GPU.** Identify the exact saved mesh, turn ridge overlay off, reconstruct source-cap/wall and physical station sections, check real mesh seams/dihedrals. Produce one compact annotated comparison. **STOP if true geometry defect:** fix canonical geometry before search; **STOP if view-only:** do not invent throat constraints to cure the viewer.

**T1 – four-DOF canonical kernel, CPU-only.** Implement V2 area/aspect/mouth/lip baseline with throat `A'(0)`, roundness/angle constraints and C2 shape onset. Lock p/X/lip/source for run A; expose only four named continuous coordinates. Supply exact H/V/diagonal and section-area plots and source/shell hashes.

**T2 – rank and feasibility.** 40–80 geometry candidates and independent perturbations; remove redundant variables. Run 0 vs controlled positive round-hold *only if T0 shows a real concern*; do not promote this to a search dimension by default. Test `p_mouth` and X treatment as paired discrete alternatives.

**T3 – bounded low-/mid-band BEM experiment.** Reuse compatible cached physical data when possible. Run a matched aperture/shape matrix before any CMA/BO campaign; preserve original source, mesh/frequency provenance and verify controls. Establish whether 480 mm shell buys significant verified V improvement or whether height remains the fundamental constraint.

**T4 – four-variable optimizer.** Choose basis A or B after Jacobian rank and small physical ablations. Use a named, reproducible CMA run first; BO only after canonical materialization/cohort eligibility. Add #5 only with an explicit acoustic/geometry benefit case. Save both raw polars and full geometry provenance. Re-run full-band finals with matched fidelity.

## G. Evidence and references

**Primary technical sources**

- **[S1]** M. Batík, *OS-SE Waveguide* (2020), especially section 5 morphing, `z_f`, exponent `γ`, and transition derivatives: https://at-horns.eu/release/OS-SE%20Waveguide.pdf
- **[S2]** M. Batík, *ATH CORE* published example, `Morph.FixedPart=0`, `Morph.Rate=3`, independent angular law and roundover: https://www.at-horns.eu/core.html
- **[S3]** D. Cinanni, *Hybrid Constant Directivity Horn*, AES 148 (2020), original PDF: https://www.speakerlab.it/resources/HCD.pdf ; abstract: https://aes.org/publications/elibrary/elibrary-page/?id=20753
- **[S4]** S. Gu, Y. You, Y. Shen, JASA **158** (2025), 1962–1975, DOI 10.1121/10.0039253: https://pubmed.ncbi.nlm.nih.gov/40928147/
- **[S5]** B. Kolbrek, *Limitations of Single-Surface Horns for Directivity Control*, AES 148 (2020): https://aes.org/publications/elibrary/elibrary-page/?id=20751
- **[S6]** G. Behler and M. Makarski, *On the Velocity Distribution at the Interface of Horn Driver and Horn*, AES 116 (2004): https://aes.org/publications/elibrary/elibrary-page/?id=12743
- **[S7]** M. Makarski, *Tools for the Professional Development of Horn Loudspeakers*, RWTH Aachen dissertation (2006): https://publications.rwth-aachen.de/record/61507/files/Makarski_Michael.pdf
- **[S8]** FaitalPRO, official HF1440 product/technical data: https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185
- **[S9]** COMSOL, *Optimizing the Shape of a Horn*, 8th-order Bernstein example and warning about shape/single-axis objective: https://doc.comsol.com/6.3/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html
- **[S10]** Öğüç, Okyar & Khajah, *Two-Stage PS–NM Workflow for PDE-Constrained Acoustic Shape Optimization*, *Mathematics* 2026 (2–4 horn B-spline controls; not the identical loudspeaker problem): https://www.mdpi.com/2227-7390/14/13/2329
- **[S11]** Bängtsson et al., *Shape optimization of an acoustic horn*, 2003; smoothing/regularization discussion: https://doi.org/10.1016/S0045-7825(02)00656-4
- **[S12]** D. Keele, *Loudspeaker horn*, US4308932A (1982), patent-derived Bi-Radial geometry: https://patents.google.com/patent/US4308932A/en
- **[S13]** Henricksen & Ureda, *Blasphemy – The Manta-Ray Horns!*, AES 58 (1977), tall nonradial mouth: https://aes.org/publications/elibrary/elibrary-page/?id=3066
- **[S14]** M. Batík, *R-OSSE Acoustic Waveguide* (2022), parametric free-standing return (a distinct construction, not a direct OSSE parameter copy): https://www.at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf

**Current repository source/limitations**

- **[R1]** `hornlab_search/gui/static/view3d.js`, `buildRidgeGeometry` and `applyRenderLook`: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/static/view3d.js
- **[R2]** Legacy Crowe section kernel and historical topology ledger: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/_crowe_section_v2.py ; https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/audit_2026-11-15/mesh_topology.csv
- **[R3]** `grid.py` `osse_rollback` `sf_start`, `append_tangent_lip`: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/grid.py
- **[R4]** `rolled_family.py`, inherited source/relief station semantics: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/rolled_family.py
- **[R5]** `registry.py` FREEFORM crossSections and existing throat blend: https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/registry.py
- **[R6]** Prepared geometry audit and study-context evidence: https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/audit_2026-11-15/geometry_controls.py ; https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/audit_2026-11-15/READINESS.md

## Final authority for the agent

**V2 plus this addendum** is the intended research direction. In any conflict on throat transition or parameter count, **this addendum supersedes V2 and the prior chat's 15–40 mm rule**. It does **not** supersede historical code/config/output identities. No numerical claim about the screenshot's actual cross-sectional squareness or a new optimum is justified before T0/T3. The key deliverable is **fewer independent controls with demonstrably larger, cleaner physical movement**, not more controls that merely make the optimizer more expensive.
