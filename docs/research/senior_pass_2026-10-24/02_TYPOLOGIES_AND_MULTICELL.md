# Report 2. New typologies, multi-cell horns, and shapes nobody has tried

Senior pass, 2026-10-24. Built on the Sonnet literature survey (Appendix A, with corrections in section 7) and on
reading Magnus's mesher (`hornlab_mesher` 0.2.4) and solver (`hornlab_beat_bem` 0.2.0) in `.venv`.
Labels as in Report 1.

## 0. Bottom line

1. **There is a much bigger shape door than FREEFORM, and it needs no mesher code from us.** The mesher's public
   `build_mesh_with_info()` accepts a `PointGridHornGeometry` [verified, `hornlab_mesher/geometry.py:214,333`,
   `mesher.py:207`]: an arbitrary inner-surface point grid `(n_phi, n_length+1, 3)` in mm, with an optional outer
   shell, an **enclosure**, half or quarter symmetry planes, and source-cap options. Our layer only has to compute
   the points. That unlocks twisted horns, Fourier-modulated cross-sections, scalloped mouths, azimuthally varying
   terminations, up/down asymmetry and non-monotone profiles. This is the highest-value typology change.
2. **Several "missing" typologies are already in the tool under other names.** The quadratic-throat waveguide is
   OS (r² quadratic in z) with a rectangular section. Geddes OS is OSSE with s = 0. Catenoidal is hypex T = 0.
   Add them as named presets, not as new code.
3. **Le Cléac'h can be re-enabled** as a *spherical-wavefront Salmon horn* from an explicit construction (section 3).
   Ship it under a neutral name (`spherical_salmon`) until it matches a published JMLC table within 0.5 mm. That
   keeps the R9 gate honest.
4. **Multi-cell horns are feasible, but not through FREEFORM or the point grid.** Septa make the duct multiply
   connected. The route is CAD → STEP → Magnus's STEP import (it exists: `hornlab_mesher/step_import.py`). Two solver
   facts shape the design: (a) the solver needs closed surfaces (open-edge guard), so septa need finite thickness,
   and (b) near-singular correction is CPU-only (until WP17 in our fork), so thin septa are only trustworthy on `beat_cpu` with
   `near_correction=True` until the thickness is at least ~½ element. **Septa that lie on a symmetry plane are free
   for a symmetric drive** (a rigid plane on a mirror plane changes nothing), so a 4×4 multicell needs only one
   interior septum per direction per quadrant.
5. **Multi-entry horns (Synergy/Unity, "MEH") are out of scope for this plan by owner decision (2026-10-24).**
   Section 6 keeps a two-line technical note so nobody has to re-research it later.

## 1. What each geometry route can express

| Route | Topology | Can do | Cannot do | Our code needed |
|---|---|---|---|---|
| Native OSSE / R-OSSE / ICW | single duct, analytic | what exists | — | none |
| FREEFORM (H/V meridians + ≤32 stations) | single duct, one z span, star-shaped sections from 4 shape kinds | classical meridians, H/V hybrids, splices | twist, arbitrary sections, mouth scallops | generators (exists) |
| **Point grid** (`PointGridHornGeometry`) | single duct, any (φ, s) → xyz grid | twist, Fourier sections, scalloped/serrated mouths, φ-varying flare and termination, up/down asymmetry, cabinet mounting | internal septa, several throats, ports | a grid generator + a thin `mesh/` adapter |
| CAD → STEP → `step_import` | any closed solid | multi-cell septa, vanes, lenses, phase-plug-style throat inserts | — | CAD script (CadQuery/build123d), tag mapping |

Symmetry: the solver supports quadrants `1` (yz+xz), `14` (yz) and `1234` (full). `12` (xz only) raises
[verified, `solve/beat.py` docstring]. **Up/down-asymmetric horns** (symmetric left/right) therefore run as `14`
half models at 2× the dofs. **Twisted horns** break both mirrors: full model, 4× dofs. Budget accordingly.

## 2. Typology catalogue: what to add, ranked by value per effort

| # | Typology | Route | Knobs | Value | Effort | Notes |
|---|---|---|---|---|---|---|
| G1 | Named presets: OS (s = 0), QT waveguide, catenoidal | existing | as parents | medium | trivial | catalog entries plus docs; QT = OS meridian in H and V on a rounded-rectangle section |
| G2 | **Meridian splice** (A up to z_s, then B, C¹ joined) | FREEFORM generator | z_s/L, parent knobs | high | low | e.g. OS throat → tractrix/JMLC mouth. The existing `blend` is a convex blend at equal t, not a splice |
| G3 | **Throat-adapted classical** (F4 in Report 1) | FREEFORM generator | `throat_blend_mm` | high (fairness) | low | lets conical/exponential/hypex start at the driver angle |
| G4 | **Le Cléac'h (exact, Fourcade 2015)** + organic/elliptical/X family | FREEFORM (≤ 90°) / GRID (rollback) | f_c, T, stop angle, H/V cutoffs | high | low–medium | **superseded by plan WP9b** (verified construction + reference numbers) |
| G5 | Kugelwellen (Klangfilm) | FREEFORM generator | f_c | low–medium | low | agent formula needs a primary-source check (section 7) |
| G6 | **Curvature/angle-space meridian** θ(s) = θ_OS(s) + Σ c_k·cos(kπs/L) | FREEFORM generator | 4–8 DCT coefficients, mouth size | high | low | smooth, low-dimensional and CMA-friendly; wall *angle* is what governs diffraction (ICW uses the same idea) |
| G7 | **Point-grid family `GRID`** (adapter) | point grid | — | very high (enabler) | medium | section 4 |
| G8 | Fourier cross-section r(z,φ) = r_s(z,φ)·(1 + Σ a_k(z) cos 2kφ) | GRID | 2–4 a_k at throat/mouth | high | low once G7 exists | even harmonics keep quarter symmetry |
| G9 | Azimuthally varying termination (rollback on the sides only, flat top/bottom) | GRID | rollback depth per φ-sector | high | low after G7 | hi-fi H/V waveguides behave differently in each plane |
| G10 | Scalloped / serrated mouth edge | GRID | count, depth, phase | medium (speculative) | low after G7 | spreads mouth diffraction over angle; unproven, so test it, don't assume it |
| G11 | Up/down asymmetric (listening-axis tilt, floor/ceiling control) | GRID + quadrants `14` | V+ and V− meridians | high for real rooms | low after G7 | 2× dofs |
| G12 | Twisted (H/V axes rotate along z) | GRID + full model | total twist | medium (exploratory) | low after G7 | 4× dofs; screen at low f_max only |
| G13 | Non-monotone / constricted profile (opt-in) | FREEFORM or GRID | constriction depth and position | medium | low | topology-optimisation results were for *efficiency*; for directivity, constrictions usually excite HOMs. Keep it opt-in and let the BEM decide |
| G14 | Cone-waveguide coax (Uni-Q-style, HF path only) | GRID (shallow wide horn, dome source) + enclosure | cone angle and profile, surround roll | medium | medium | the tweeter's directivity in a woofer-cone "waveguide"; the woofer is not modelled |
| G15 | Diffraction-slot CD (Keele/Mantaray-like) | FREEFORM (high-aspect rounded rectangle near the throat) or GRID | slot width/length, flare angles | medium (benchmark) | medium | a classic to beat; makes the leaderboard meaningful to pro users |
| G16 | **Multi-cell** | CAD → STEP | N_h×N_v, cell f_c, septum t, cap angles | medium (historic, but QD-interesting) | high | section 5 |
| G17 | Multi-entry (Synergy/Unity, MEH), multi-throat | — | — | — | — | **DEFERRED by owner 2026-10-24**; not in the plan (section 6) |
| G18 | Vanes, slat lenses, throat inserts | CAD → STEP | — | low–medium | high | thin bodies have the same near-field caveat as septa |
| — | Metamaterial / labyrinth, line-array DOSC / Paraline, CBT | — | — | low here | very high | out of scope for a single-body BEM search (agreeing with Appendix A) |

## 3. Spherical-wavefront Salmon horn (JMLC-type): explicit construction

> **Superseded 2026-10-24:** the published exact construction (Fourcade 2015) is now in `04_IMPLEMENTATION_PLAN.md` WP9b, validated against its reference case. Use that; the sketch below is kept for history only.

Area law (Salmon 1946; JMLC applies it to wavefront areas) [Appendix A, sources there]:
`A(x) = A0·[cosh(x/x0) + T·sinh(x/x0)]²`, with `x0 = c/(2π f_c)`, where x is the axial distance travelled by the
wavefront apex.

Geometry of a wavefront orthogonal to the wall at wall point P = (z, r) with wall angle θ (from the axis)
[inferred, elementary geometry]: a sphere centred on the axis that meets the wall at a right angle has its radius
vector along the wall *tangent*. So its centre is where the tangent crosses the axis:
- centre `z_c = z − r/tan θ`, radius `R = r/sin θ`;
- cap area `A = 2π R² (1 − cos θ)`, which tends to π r² as θ → 0 (plane wave), as it should;
- apex `z_a = z_c + R`.

March in x (apex position), with unknowns (z, r, θ) at each step `x_{i+1} = x_i + Δx`:
1. `2π (r/sin θ)² (1 − cos θ) = A(x_{i+1})`
2. `z − r/tan θ + r/sin θ = z_a0 + x_{i+1}`
3. `r − r_i = tan(½(θ + θ_i)) · (z − z_i)` (trapezoidal wall continuity)

Eliminate z and r with (2) and (3) for a given θ, then root-find θ on (1) (brentq on [θ_i, max_wall]). Start at
`(0, r0, θ0 = driver exit angle)`; stop at `max_wall_deg` or the envelope. Use Δx ≈ 0.25 mm, then resample to the
16–32 FREEFORM anchors with the existing `select_anchors`. T = 1 is the "spherical exponential" case.

**Validation gate (keeps R9 honest).** (a) T = 0.999 with θ0 → 0 and a small f_c must approach a plane-wave Salmon
horn near the throat. (b) Compare against one published JMLC table (Fourcade 2015 PDF or the ETF10 lecture,
Appendix A) within 0.5 mm. Only after (b) may the generator be called `lecleach`; until then it is
`spherical_salmon`.

## 4. The GRID family (point-grid adapter): design

`hornlab_search/design/generators/grid.py` (new) produces `inner_points` (n_phi × n_s × 3, mm) from a
**radius field** `r(s, φ)` on a single z grid:
```
r(s, φ) = r_H(s)·r_V(s) / ((|r_V(s) cos φ|^p(s) + |r_H(s) sin φ|^p(s))^(1/p(s)))   # superellipse with exponent p(s)
          · (1 + Σ_k a_k(s) cos(2kφ))                                            # G8 Fourier modulation (even → quarter-symmetric)
z(s, φ) = s·L + δz_mouth(φ)·w_mouth(s)                                            # G9/G10 φ-varying termination or scallop
(x, y) = r·(cos(φ + τ(s)), sin(φ + τ(s)))                                         # G12 twist τ(s) (full model only)
```
`r_H`, `r_V` come from any existing meridian generator (OSSE, tractrix, JMLC-type, splice, angle-space), so every
classical typology automatically gets the new cross-section freedoms. Quarter models generate φ ∈ [0, 90°] only and
set `closed=False, symmetry_planes=("x","y")`. Half up/down-asymmetric models generate φ ∈ [−90°, 90°] with
`("x",)`. The outer shell is either the mesher's offset (`outer_points=None` plus `wall_thickness_mm`) or an
explicit offset grid.

Mesh adapter `hornlab_search/mesh/grid_build.py` (new): wraps `build_mesh_with_info(PointGridHornGeometry(...), density)`.
It must reuse the existing metre-scale, bbox, symmetry and topology checks in `mesh/build.py` and `mesh/topology.py`
unchanged, which is where the silent killers are caught. **This is not a mesher: gmsh authoring stays inside
Magnus's builder.** It does call a non-`__init__` API, so pin it with a guard test like `tests/test_mesh_pin.py`
(issue #9 precedent).

## 5. Multi-cell horns: how to actually model them

**Geometry.** Classic WE/Altec cells are frusta of pyramids sharing a virtual apex at the throat, with mouths tiling
a spherical cap (Appendix A §1). Every septum lies on a plane through the apex: H-septa on `x = z·tan α_i`, V-septa on
`y = z·tan β_j`. The outer body is a rectangular or spherical-sector horn. Parameterization: `N_h`, `N_v`, total cap
angles, cell flare (exponential from a manifold throat), septum thickness t, septum start z_s (where the single
throat splits).

**Build.** CadQuery/build123d (OCP, Apache-2.0) builds the horn air volume as a solid. It subtracts thickened septum
plates (from z_s to the mouth), adds the outer shell and the source face, and exports STEP with named faces. Magnus's
`step_import` maps faces to tags and validates the surface mesh [verified that it exists; API details to be read
before use]. Licences: OCP Apache-2.0, AGPL-compatible.

**Solve: the three traps.**
1. *Closed surfaces only.* The solver has an open-edge guard (mesher enclosure docstring [verified]), so
   zero-thickness septa are not allowed. Use t ≥ 1.5 mm, which is printable anyway. (Appendix A's statement that
   zero-thickness septa work with Burton-Miller is wrong for this solver.)
2. *Thin-gap quadrature.* A septum's two faces sit t apart, far closer than the element size (λ/6 = 5–10 mm). Regular
   Gauss quadrature between near-coincident faces is inaccurate, and near-singular correction is **CPU-only**
   [verified, `hornlab_beat_bem/config.py` `near_correction` docstring]. So validate every multicell result on
   `beat_cpu` with `near_correction=True` (and `solve_precision="double"`) against CUDA before trusting CUDA screens.
   Expect to need local refinement near septum edges.
3. *Symmetry is a gift.* For a symmetric drive the field already has zero normal velocity on the mirror planes, so a
   septum *on* a mirror plane is acoustically invisible apart from its thickness. In the quarter model a 4×4
   multicell needs only the off-axis septa (one H and one V per quadrant). A 2×2 "multicell" is the plain horn.
   Corollary: an *odd* cell count puts a cell centred on axis, which is what the classic designs did.

**What the BEM will show.** Below the cell-width/λ ≈ 1 frequency the cells sum like one horn. Above it, each cell
beams and the array shows grating-lobe "fingering" [Appendix A]. That is exactly the frequency-dependent pattern a
quality-diversity search can exploit: multi-cell as a *coverage-control* device in the 0.5–3 kHz band of a large
horn, not as a full-band HF horn.

**Sizing.** Septa add surface: (N_h−1)+(N_v−1) plates, two faces each. For a 4×4 quarter model that is about 1 extra
plate per direction, roughly +30–60 % dofs [inferred]. Start at f_max = 4 kHz on CUDA and verify on CPU.

## 6. Multi-entry horns (Synergy/Unity, MEH): deferred

Left out of this plan by owner decision (2026-10-24). Record for later only: they need several source tags, which
the Python `SolveConfig` refuses today, although the Julia driver already loops several channels on one
factorization [verified, `BeatEngineDriver.jl:1145-1196, 1577-1600`]; ports would come from the CAD → STEP route.

## 7. Corrections to the Sonnet survey (Appendix A)

| Claim in Appendix A | Correction |
|---|---|
| Zero-thickness septa are fine with Burton-Miller | not for this solver (open-edge guard); use finite thickness (section 5) |
| "Non-monotone profiles consistently outperform smooth ones; unlock now" | the cited topology-optimisation results target *transmission efficiency*. For directivity, constrictions excite HOMs. Make it opt-in (G13), not a default |
| QT waveguide is a new area law to implement | A(z) quadratic for a round section is the OS hyperbola; QT is the OS meridian on a rectangular/rounded section (G1) |
| Geddes OS formula `(z/ξ₀)²/a² − r²/a² = 1` | garbled; the ATH/OS form is r(z) = √(r0² + 2·r0·z·tan θ0 + z²·tan² α), which OSSE already has with s = 0 |
| JMLC is "fully verifiable" from sphericalhorns.net | that page disclaims matching the original. Use the explicit construction in section 3 with a table-match gate |
| Kugelwellen formulas | plausible, but the constant-sphere-radius construction does not obviously keep the wavefront orthogonal to the wall. Check against Kolbrek & Dunker (2019) or another primary source before shipping G5 [unverified] |
| JAX-BEM is "applied to horn directivity" | the arXiv abstract (2604.21431, Apr 2026) mentions general acoustic shape optimisation only; horn use unconfirmed [checked 2026-10-24] |

## 8. Ideas nobody seems to have tried (search-side novelty)

These are hypotheses for the optimizer, each cheap once G6/G7 exist.

1. **Design atlas via quality-diversity.** CMA-ME (pyribs, MIT) over descriptors (H coverage at 2 kHz, V coverage at
   2 kHz) or (mouth width, depth). The output is a map: the best horn for each coverage/size cell from one campaign.
   No horn tool offers this, and it answers "what can a 300×200×150 mm horn do?" directly.
2. **Co-optimized horn + cabinet edge.** With F13's enclosure, make `edge_mm` (roundover) and the baffle margins
   design knobs. Baffle diffraction is usually tuned after the horn, by hand.
3. **HOM proxy from boundary traces.** Score the phase flatness of the pressure on the mouth aperture relative to the
   ideal spherical wavefront from the virtual apex (surface traces already exist). It is a cheap, Geddes-style metric
   that needs no new solve [inferred]. Report-only first, then correlate it with polar ripple.
4. **φ-split hybrids.** OS in the horizontal sectors and JMLC or tractrix in the vertical ones, joined by the point
   grid's φ blend instead of the elliptical H/V interpolation (an extension of G9).
5. **DI-match to the woofer.** A brief names the woofer size and crossover f_x. An analytic baffled-piston DI for
   the woofer becomes a target for the horn's DI over about ±½ octave around f_x (one extra term, no extra solve).
   This is the classic "DI match" goal that is usually done by intuition.
6. **Robust horns.** Score E[J] over ±0.3 mm surface perturbations at finalist stage only, which rewards designs
   whose good behaviour is not a knife-edge resonance alignment (the F10 aliasing makes this matter).
