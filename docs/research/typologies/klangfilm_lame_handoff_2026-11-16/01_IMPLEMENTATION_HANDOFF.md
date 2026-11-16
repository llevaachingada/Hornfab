# HornFab: mathematically grounded Lamé / rolled-mouth horn implementation handoff

**Revision:** Senior research v3 / HF1440 throat evidence correction, 2026-11-16. **Audience:** local OpenCode / Claude coding agent + independent reviewer. **Deliverable:** an implementation specification; **nothing here asserts that production code was changed or that new BEM simulations were run**. **Status:** implementation authorized only within a new worktree after the normal project review/merge process. Do not edit active queues, default scores, dataset records, or the live solve directory.

> **Mandatory v3 correction, read before implementing:** `03_THROAT_COUPLING_SENIOR_ADDENDUM.md` is an integral part of this handoff, not an optional appendix. Official FaitalPRO HF1440 specifications say **35.8 mm diameter, radial phase plug, "Combined Exit", no conical adaptation throat; no numerical exit angle is specified**. The old brief's **2° half-angle is a modeling assumption, NOT the verified angle of the physical HF1440**. The mathematically derived 10.617223° is the *2018 Klangfilm horn wall tangent*, NOT a measured driver angle. Consequently, a 2° tangent correction must **not** be required as driver-fidelity or optimize-by-default. Section 03 takes precedence over any older language to the contrary. Source-cap curvature and actual throat wall tangent must be separately identified, with a small source-controlled A/B before adding a new throat-angle optimization gene.

> **Decisive design decision:** Extend the existing HornFab GRID family using a reusable, versioned **Lamé geometry operator** with a separate **curved-wavefront-area-preserving mode**. Keep the proven, exact *axisymmetric Fourcade/JMLC* march and the numerically verified *2018 Ahlswede ellipse* port untouched. A 2019 higher-Lamé Klangfilm horn is **not** reproduced by simply applying `morph_exponent > 2` to the 2018 ellipse, and it is **not** reproduced by forcing planar cross-section area alone. Implement and test the corrected curved-cap math below, including a rollback-safe rim, before spending GPU time. For the owner's longer reference, also support a *JMLC-derived* parent. Do not call our generalized higher-Lamé model an exact reproduction of Ahlswede's unpublished later source.

## 0. Provenance, read-first files, and the current user brief

### Sources used for this handoff

- User uploads: `KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md` (105 lines), `HornFab_Senior_Morph_Rollback_Implementation_Handoff_2026-11-16.md` (previous version), user-supplied calculator `Klangfilm_Elliptical_Horn_Calculator_diy_v10.xlsm`, `klangfilm_v10_partial_cached_xyz.csv`, before/after render sheets and screenshot of **diyAudio post #68, March 10 2019**. The uploaded v10 workbook is the **2018 ordinary-ellipse model**, not the complete 2019 Lamé/projection calculator.
- Live connected GitHub repository: [llevaachingada/Hornfab](https://github.com/llevaachingada/Hornfab), including [Klangfilm implementation commit `c677efd`](https://github.com/llevaachingada/Hornfab/commit/c677efd727dc426e1905ffca2f8f106f0fda6126). Repo may change before your local implementation. Before editing, record `git rev-parse HEAD`, `git status --short`, branch/worktree, installed mesher version and optional local diff. **The upload's “uncommitted” label is stale: its geometry was committed on Nov 16.**
- External primary/technical sources listed in §16, with source-to-design-decision links throughout this document. Source levels: **[P]** published equation, **[O]** author's original forum/article, **[R]** repo-verified implementation, **[D]** derived here, **[H]** hypothesis to test, **[U]** not independently reproduced.

### The actual current home brief, not assumptions

Live file: [`examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml`](https://github.com/llevaachingada/Hornfab/blob/main/examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml):

| Field | Frozen value in that brief | Consequence |
|---|---:|---|
| Driver | FaitalPRO HF1440; modeled `exit_radius_mm=18`, `exit_angle_deg=2` | **36 mm modeled round source; 2° is a BRIEF ASSUMPTION**, not a verified physical angle of HF1440 |
| H/V coverage | **80° H / 50° V** | Optimize measured -6 dB radiation, **not nominal wall angles or mouth AR** |
| Crossover `f0_hz`, `f0_v_hz` | **700 / 700 Hz** | 700 Hz lower-control target, not a promise of accurate 700 Hz pattern control |
| Objective analysis band | **350–8000 Hz**; loaded-high **5600 Hz** | Respect prescribed scorer masks; do not silently replace the objective grid |
| Envelope | **600 W × 480 H × 480 D mm** | Include actual outer shell, sweep and all rollback points, not terminal-ring dimensions |
| Objective | **v7 smooth-directivity**, DI-slope target **5 dB/decade** | Not the same score as constant-directivity v7; v7 `cov_v_weight=0.5` |
| Source | cap `auto`; symmetry `hv` | Quarter model only while two mirror planes truly hold |
| Current Klangfilm geometry config | `fc=560`, `stretch=1.6`, `end_frac=1.5`, `bend_R=400`, `throat_ellipse=0.4`; `n_phi=19,n_s=64` | Geometry benchmark, **not an approved acoustic optimum** |

**Critical manufacturer finding, and v3 correction:** FaitalPRO's [HF1440 product page](https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185) says **35.8 mm throat and “Combined Exit,” not a 2° conical exit**. The 36 mm / 2° values are a documented simulation interface assumption. Preserve them for controlled comparisons, label them as modeled, and create an explicit `driver_angle_provenance` field. Do **not** invent a physical HF1440 wall half-angle. A measured phase-plug transition or driver CAD is needed for precise 8–20 kHz coupling.

### Repo code paths to inspect before editing

| File | Current fact and integration concern |
|---|---|
| [`tools/geometry/klangfilm_ellipse.py`](https://github.com/llevaachingada/Hornfab/blob/main/tools/geometry/klangfilm_ellipse.py) | Verified *2018* VBA base equations, `_NI=160` angular midpoint cap integration, `60` bisection iterations, dense `~600` raw stations; **no Lamé exponent**. 5 shape knobs; `throat_ellipse` uses a fractional power; row-wise frontal sagitta warp. No local tests in uploaded handoff. |
| [`tools/geometry/klangfilm_ellipse_cli.py`](https://github.com/llevaachingada/Hornfab/blob/main/tools/geometry/klangfilm_ellipse_cli.py) + [`rolled_rect_cli.py`](https://github.com/llevaachingada/Hornfab/blob/main/tools/geometry/rolled_rect_cli.py) | Process-local monkey-patch bridge. Keep as historical replay path, not the definitive multi-family registration design. Digest currently covers source and bridge files. |
| [`hornlab_search/design/generators/rolled_family.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/rolled_family.py) | Already contains a native, versioned, digest-bound rolled-geometry path and a **physical throat slope check**. Model new family registration after this rather than copy monkey-patches. Avoid shoehorning Lamé knobs into rolled-rectangle-specific schemas. |
| [`hornlab_search/design/generators/grid.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/grid.py) | `g_pnorm` constant superellipse for non-rows GRID; Le Cléac'h, Iwata, Salmon rows; `lecleach_ar`, `iwata_ar` pin `AR_t=1`, use planar area-preserving stretch, not curved Lamé wavefront areas. |
| [`hornlab_search/design/generators/registry.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/generators/registry.py) | Generated FREEFORM H/V profiles and native morph. Disables / pins some coincident cross-section mechanisms. |
| [`hornlab_search/design/families.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/design/families.py) | Existing `_MORPH` keys and `morph_target=3`, `morph_exponent` for OSSE/R-OSSE/ICW/FREEFORM. **They do not automatically transform GRID point arrays.** Distinguish different uses of “superellipse”: *cross-section exponent* vs *OS-SE profile termination exponent*. |
| [`hornlab_search/mesh/grid_build.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/mesh/grid_build.py) | `PointGridHornGeometry` consumes full inner/optional outer surface and `source_shape=1`, `source_auto_angle_deg` from metadata. Existing GRID outer shell default follows **in-plane meridian normals**, not necessarily true 3-D normals for a swept Lamé surface. |
| [`hornlab_search/mesh/throat_check.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/mesh/throat_check.py) | Only reports driven-source size/area; **roundness = area / ellipse-area cannot distinguish a circle from an ellipse**. Add circle-eccentricity and actual derivative diagnostics; do not break report-only legacy interface. |
| [`hornlab_search/metrics/polar.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/metrics/polar.py) | Beamwidth uses outermost -6 dB crossings; extra lobes can appear wide. Need supplemental main-lobe and sidelobe diagnostics. |
| [`hornlab_search/metrics/beam_shape.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/metrics/beam_shape.py) | Existing forward -6 dB contour **superellipse fit**; measure acoustic contour shape/residual, separately from geometry exponent. |
| [`hornlab_search/bo/data.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/bo/data.py) and `docs/research/bo_study/*` | Versioned data/cohort identity; existing *specific* native BO study drops an inactive morph exponent **only for its pinned `morph_target=1` cohort**. The new `morph_target=3` makes exponent ACTIVE; do not reuse that no-op projection. |

**Implementation boundary:** a new opt-in GRID `rows.type`, new shape kernel, source/mesh adapters, tests and example configs. Leave old `lecleach_*`, `iwata_ar`, `klangfilm_ellipse`, OSSE and the original `morph_*` meaning/byte hashes untouched. If the incoming SHA differs, inspect changed lines and reconcile, not blindly apply this text.

---

## 1. What is, and is not, actually established by the source literature

1. **[P/O] Kolbrek 2008 and Ahlswede 2018:** spherical-wave horns have a curved-cap expansion model and intrinsic rollback. This is a *wavefront model*, not a guarantee that actual isophase fronts in the radiated BEM solution are exactly the assumed mathematical caps [S01,S02,S03].
2. **[O] Ahlswede 2019 post #68** explicitly presents a rectangular variant with higher Lamé exponents and full rollback [S04]. Thus **a constant `p=2` planar ellipse cannot reproduce it**.
3. **[O] Ahlswede's August 2019 mathematical article** gives Lamé contour equation, angular parameterization, flat-area starting approximation, tri-axial **ellipsoid cap** area integral, and iterative area correction [S05]. A later 2023 article states that his spherical-wave and JMLC spreadsheets also used a transition **from Lamé 2 at the throat** toward higher exponents and warns that uniform angular parameter sampling can produce very uneven point distributions [S06].
4. **[U] His full unpublished 2019 higher-Lamé calculator is not the uploaded 2018 workbook**. The author describes vector-bending methods and stereographic projection on diyAudio [S07], but his numerical projection and geometry details are not reproduced in the available 2018 port. **Do not claim exact 2019 photographic parity from this specification.**
5. **[P] Fourcade 2015** rigorously gives an *axisymmetric* numerical Le Cléac'h march and published reference fixture [S08]; HornFab's test dossier reports excellent match, including 467.30 mm width for 400 Hz, T=0.8, 25.4 mm throat and 8° **included** exit angle (4° half-angle) [R: `JMLC_LECLEACH_RESEARCH_2026-10-25.md`]. There is **no verified original universal elliptical-JMLC formula**; HornFab `iwata_ar` is explicitly reconstructed.
6. **[P] Batík 2020 OS-SE morph formula**, intended for monotone axial `z` on an OSSE profile, is already supported natively for other families [S09,S10]. Its `n` is the exponent **of the axial termination curve**, and must not be confused with the **Lamé exponent of the H/V cross-sectional contour**. Its published morph has `(z-z_f)^gamma`, `gamma>=1`; `gamma=1` gives a slope discontinuity at onset. `Morph.FixedPart` and `Morph.Rate` are existing semantics. ATH independently has a rollback feature parametrized by actual *profile length*, confirming why axial `z` is not a universal coordinate here [S10].
7. **[P] Full-wave acoustics matters.** Webster / 1-D wavefront-area matching primarily constrains loading; it cannot predict general 3-D H/V polars or higher-order modes. Geddes, Kolbrek, Godinho et al. and 2025 Gu/You/Shen motivate Helmholtz/BEM evaluation and directivity objectives [S11,S12,S13,S14].
8. **[P] Smoothness is a mathematical optimization constraint**, not merely appearance. Bängtsson/Noreland/Berggren 2003 applied adjoint Helmholtz gradients with smoothing to avoid irregular local solutions [S15]; Schmidt/Wadbro/Berggren 2016 solved a 3-D horn shape problem with a memory-efficient adjoint representation [S16]. Our derivative-free optimization should still use a low-dimensional smooth basis and geometric regularization.

**Research-to-code test:** Every implemented feature needs a provenance label (`published_exact`, `published_principle_reconstruction`, `derived_area_preserving`, `hypothesis_visual_sweep`), its own versioned equation contract, and a test showing which published limit it reduces to.

---

## 2. The original Klangfilm/Ahlswede 2018 equations: preserve exactly as a frozen reference

Use SI inside equations, millimeters in the materialized point grid, with one explicit `c_air_m_s` value persisted. **Do not mix 343, 344, and adjustable c silently**; the uploaded port hard-codes `343 m/s`, and the Le Cléac'h fixture uses `344 m/s`.

Let `f_c` be the nominal cutoff parameter, `y_0` the circular throat radius, and `R_0` the fixed spherical construction radius:

\[
 R_0 = \frac{c}{\pi f_c},\quad m=\frac{4\pi f_c}{c}=\frac4{R_0},\quad
 h_0=R_0-\sqrt{R_0^2-y_0^2},\qquad 0<y_0<R_0.
\]

For axial wavefront-top displacement `x` and wavefront cap height `h`:

\[
 h(x)=h_0e^{mx},\quad S_{\rm sph}(h)=2\pi R_0h,\quad
 y(h)=\sqrt{2R_0h-h^2},\quad
 z_{\rm wall}(h)=\frac{\ln(h/h_0)}m-h+h_0.
\]

- `h/R0 < 1`: growing profile; `h/R0 = 1`: maximum *round* radius; `1 < h/R0 < 2`: the radius reduces as the profile rolls back; `2`: limit where the untruncated profile closes.
- The **maximum axial z** occurs when `dz_wall/dh = 1/(m h)-1=0`, i.e. `h=R0/4`, **not** at max radius `h=R0`. The mouth/aperture station, maximum-forward station, and final end are distinct.
- The current `g_end_frac` is `h_end/R0`, so it is a **dimensionless truncation or termination-location control**, not an independent lip radius.

The uploaded 2018 ellipse approximation uses `u=(y-y0)/(R0-y0)` clipped to `[0,1]` and

\[
 f_s(h)=1+(f_{s,\max}-1)\sin\!\left[\frac\pi2 u(h)\right],\qquad
 b_e(h)=\frac{R_0}{f_s(h)}.
\]

Then it finds `a_e(h)` such that the **curved tri-axial ellipsoid cap area** is `2 pi R0 h`, and the flat section semi-axes become `a(h)=a_e sin(theta_h)` and `b(h)=b_e sin(theta_h)`, where `theta_h=acos(1-h/R0)`. The original scalar `stretch` is therefore fundamentally a **minor-axis compression factor**, **not necessarily the final cross-section ratio `a/b`** once curved-cap area correction solves the major axis. Don't relabel it as true H/V aspect ratio. The port's `g_throat_ellipse` is **our later extra exponent on u**, not published 2018 math.

### Mathematically confirmed wall/source-model difference (NOT a confirmed physical driver mismatch)

For the raw spherical wave wall,

\[
 \frac{dy}{dh}=\frac{R_0-h}{\sqrt{2R_0h-h^2}},\qquad
 \frac{dz}{dh}=\frac{1}{mh}-1,\qquad
 \tan\alpha_{\rm wall}(0)=\frac{(R_0-h_0)/y_0}{1/(mh_0)-1}.
\]

At `fc=560 Hz, c=343 m/s, y0=18 mm`: `R0=194.965 mm`, `h0=0.833 mm`; the entrance wall half-angle is approximately **10.62°**. The HF1440 brief **assumes 2°** as `driver.exit_angle_deg`; FaitalPRO **does not specify any numeric exit angle** for this combined-exit driver. Thus there is an internal modeling discrepancy between the idealized 2° cap and raw 10.62° *horn* wall, **not proven physical maladaptation to the HF1440**. `source_auto_angle_deg` metadata cannot alter the wall geometry, nor does geometric agreement prove a phase-plug wavefront match. A source-cap model is itself part of the acoustic boundary and cannot be silently varied when comparing wall shapes.

**Requirement, corrected:** Preserve the exact 2018 profile as a historical reference. **Do not mandate a correction to 2°** or call one “driver-matching.” If a small controlled acoustic study justifies an optional *modeled horn-entrance-shaping* feature, parameterize `geom_entry_half_angle_deg` and a **fixed** `source_blend_mm`, and analytically verify `r(0)=y0` and `(dr/dz)(0)=tan(alpha_design)` for the new geometry. The following scalar local correction is applicable only to the **monotone-z, initially round** near-throat portion; do not apply blindly to an immediately noncircular Lamé surface. It is an experiment, not published Klangfilm math:

\[
 \Delta r(z) = \Big(\tan\alpha_{\rm model}-r_{\rm base}'(0)\Big)z\,[1-Q(z/L_b)],
 \quad Q(t)=6t^5-15t^4+10t^3,\;0\le z\le L_b,
\]

and zero for `z>L_b`. Here `Q` has zero first and second derivatives at both ends. The correction preserves source radius, controls the **chosen horn** tangent, and vanishes C² at `L_b`; **it modifies the ideal cap construction and is a derived geometric splice, not a physical HF1440 adapter**. Measure the resulting curved-cap area departure and check the *actual 3D morphed wall*. Do not infer real driver wavefront continuity from this geometry alone. Use maker CAD or measured exit-field data if available. Numerically verified local examples and their limits are in `04_THROAT_ANGLE_ANALYTIC_CHECK.py`.

---

## 3. Lamé / superellipse geometry: source mathematics and robust numerical form

**Cross-section Lamé exponent `p`** (avoid ambiguous `n`, since OS-SE calls its own termination exponent `n`):

\[
 \boxed{\left|\frac{X}{a}\right|^p+\left|\frac{Y}{b}\right|^p=1},\quad
 a,b>0,\;p\ge2.
\]

- `p=2`: circle if `a=b`, otherwise ellipse;
- `2<p\lesssim 4`: softer rounded rectangle;
- `p\approx6..8`: more squared, requires more care near corners and mesh resolution;
- `p>8`: **not first-pass search**. Ahlswede cautions about point-cloud artifacts in his 2019 article even though his later 2023 software used `p=12` after extra tuning [S05,S06].

**Published angular parameterization** [S05,S17]:

\[
 X(t)=a\operatorname{sgn}(\cos t)|\cos t|^{2/p},\quad
 Y(t)=b\operatorname{sgn}(\sin t)|\sin t|^{2/p}.
\]

For `p>2`, equal angular increments in *this parameter `t`* distribute points unevenly and produce a derivative singularity at the axes. **Do not use this naive parameterization as the meshing station map.**

**Preferred fixed-ray azimuth `phi`, from +horizontal axis** [D]:

\[
 \rho(\phi;a,b,p)=
 \left(\frac{|\cos\phi|^p}{a^p}+\frac{|\sin\phi|^p}{b^p}\right)^{-1/p},\quad
 (X,Y)=\rho(\phi)(\cos\phi,\sin\phi).
\]

This keeps each `phi` ray associated with the same H/V direction across all stations and avoids the severe tip clustering caused by naive Lamé angular parameterization. It does **not** distribute equal arc length. Mesh density must be checked using curvature/chord error and a shared azimuth distribution, with exact endpoints `phi=0, pi/2`. Don't let each cross-section choose a different `phi_i(s)` without an explicit correspondence/untwisting rule.

**Flat (planar) area:**

\[
 A_{\rm flat}(a,b,p)=C(p)\,ab,\quad
 C(p)=\frac{4\Gamma(1+1/p)^2}{\Gamma(1+2/p)}.
\]

For `p=2`, `C=pi`. For fixed `a,b`, increasing `p` increases area, so **raising the Lamé exponent without adjusting axes breaks even a planar area constraint**. Use `scipy.special.gammaln` for stable computation. If a planar `A_target` and physical aspect `q=a/b` are specified, the **unique area-locked axes** are

\[
 a=\sqrt{\frac{A_{\rm target}q}{C(p)}},\qquad
 b=\sqrt{\frac{A_{\rm target}}{q C(p)}}.
\]

This is suitable for a *flat-section approximation mode*; it is **not sufficient** for Ahlswede's curved-wavefront premise.

---

## 4. Curved superellipsoid-cap area: full derived mathematical model

### 4.1 Provenance warning

Ahlswede [S05] publishes the **`p=2` ellipsoid cap** surface integral and a numerical major-axis correction. His later work states he uses high-Lamé profiles and a projection onto construction wavefronts [S06]. **The exact full later 2019 implementation is not public in the supplied workbook.** The following is an independently derived, explicit generalized superellipsoid-cap model that reduces to his documented 2018 method when `p=2`. It is **not proven identical** to the 2019 private stereographic/vector projection. Call it `superellipsoid_cap_v1`, not `Ahlswede_2019_exact`.

### 4.2 Surface definition

Define an assumed superellipsoidal cap with a scaled Lamé outline and spherical-axis radius `c0>0`. Let `rho(phi)` be the fixed-ray Lamé radius from §3, `theta` the polar angle, and

\[
 \boxed{\mathbf P(\theta,\phi)=
 \begin{bmatrix}
 \rho(\phi)\sin\theta\cos\phi\\
 \rho(\phi)\sin\theta\sin\phi\\
 c_0\cos\theta
 \end{bmatrix}},
 \quad \theta\in[0,\theta_{\max}],\quad \phi\in[0,2\pi),
 \quad \theta_{\max}=\arccos(1-h/c_0).
\]

`a` and `b` here are equatorial semi-axes; the section at `theta_max` has semi-axes `a sin(theta_max)` and `b sin(theta_max)`. At `p=2`, this is the usual tri-axial ellipsoid. At `a=b=c0, p=2`, it is a sphere.

For azimuth in the first quadrant with `C=cos(phi), S=sin(phi)`:

\[
 D=\frac{C^p}{a^p}+\frac{S^p}{b^p},\quad
 \rho=D^{-1/p},\quad
 \frac{\rho'}{\rho}=\frac{C^{p-1}S/a^p-S^{p-1}C/b^p}{D}.
\]

Derived from the parametric metric, the **curved surface area** is

\[
 \boxed{S_{\rm cap}(a,b,c_0,h,p)=4\int_0^{\theta_{\max}}\int_0^{\pi/2}
 \sin\theta\;
 \sqrt{c_0^2\sin^2\theta[\rho^2+(\rho')^2]+\rho^4\cos^2\theta}
 \,d\phi\,d\theta.}
\]

This integration has no moving coordinate singularity in `phi` for finite `a,b,p>=2` when evaluated on the fixed-ray representation. Use the **radial** formula rather than differentiating `|sin t|^{2/p}` near axes. The four-fold factor is valid for the unwarped symmetric cap only.

**Analytical invariant:** at `p=2`, `a=b=c0=R`, `rho=R` and `rho'=0`, so

\[
 S_{\rm cap}(R,R,R,h,2)=2\pi R h.
\]

This is the **hardest non-negotiable unit test**, and the reference Python module supplied with this handoff tests it at several heights. The module also independently integrates the published **`p=2` ellipsoid cap** using the original spherical-angle integrand (arbitrary `a != b != c`), then checks agreement with the new fixed-ray formulation. This avoids validating two identical implementations against each other.

**Physical caveat:** exact numerical area conservation is **not** exact acoustic wavefront construction. The family of caps must remain appropriately nested; arbitrary `q(h)`/`p(h)` schedules can create intersecting assumed fronts or wall curvature problems. Report an independent **wavefront nesting/intersection diagnostic** at coarse/fine stations. Where a constructed wavefront normal is available, report its angular relation to the horn wall, but do **not** universally enforce wavefront-wall orthogonality: Kolbrek explicitly notes that the classic **Klangfilm spherical-wave horn does not assume wavefronts 90° to the wall**, whereas the Le Cléac'h construction uses an orthogonality principle. Treat these as **different parent physics**, not as the same constraint.

### 4.3 Area-preserving parameterization for optimization

Do **not** optimize `fc`, arbitrary curved cap target area, both `a` and `b`, and `p` simultaneously. That creates redundant or conflicting degrees of freedom and makes optimization poorly conditioned. Instead:

1. The **parent law** fixes `S_target(s)` or `S_target(h)` (Klangfilm: `2 pi R0 h`; JMLC: Fourcade's published area law).
2. One physical **aspect ratio** `q(s)=a(s)/b(s)>0` is parameterized through a smooth transition.
3. One **Lamé exponent** `p(s)>=2` is parameterized separately.
4. Hold `a=q b`, solve the **single positive scalar `b`** satisfying

\[
 F(b)=S_{\rm cap}(q b,b,c_0,h,p)-S_{\rm target}(h)=0,
 \qquad a=q b.
\]

This yields the intended aspect exactly and preserves the *assumed* curved cap area numerically. **It is not byte-equivalent to Ahlswede's original fixed-minor-axis solve**; both must be separate `area_mode` values. Use `scipy.optimize.brentq` (monotone bracket when feasible, validated) and warm starts; use a reference fallback if bracketing fails. Do not run 60 × 160×160 midpoint evaluations per station by default.

5. At chosen `h`, section axes are `a_sec=a sin(theta_max)` and `b_sec=b sin(theta_max)`. The full cross-sectional `W/H` here is `a_sec/b_sec=q`. Both `q` and `p` must be stored in the recipe and effective geometry metadata.

**Alternative `area_mode=flat_section`**: use §3's gamma-formula axes. Cheap approximation and clean ablation control, but **never describe it as curved-wavefront preservation**.

**Alternative `area_mode=published_2018`**: exactly retain the old code and its fixed `b_e=R0/fs` iterative `a_e`, including original geometry hash and seed, `p=2` only. This is a regression/benchmark, not a candidate dimension within a blended campaign.

### 4.4 Numeric algorithm, error budget, complexity

- Use tensor-product **Gauss-Legendre quadrature** on `theta ∈ [0,theta_max]` and `phi ∈ [0,pi/2]`. Quadrature points lie inside the interval; share/cache `leggauss(order)` nodes. The radial form converges substantially faster than poorly sampled Lamé parameter-angle derivatives.
- Implement adaptive orders: start at (e.g.) **24×24**, compare to **48×48**; where `p` is high or `theta_max` near a limit, allow **96×96** or additional refinement. Accept the area only if the **relative difference between two successive quadrature levels** is `<= 1e-5` for exploratory geometry and `<= 1e-7` for reference acceptance, **and** a third-level or analytic reference confirms this criterion on representative extremes. These are **implementation acceptance targets, not published physical tolerances**.
- Bracket scalar root based on flat-area estimate and expand geometrically; use `rtol <=1e-9` on axes as a numerical setting, then check actual **relative area residual**. A successful scalar root does not remove quadrature discretization error.
- Reuse **one solved cap per station** across all azimuth mesh rays. Optimize 50–100 effective loft stations, *not* individual `(s,phi)` points. Use interpolation only after high-curvature rollback and derivative checks. Consider area look-up cache keyed by `(p,q,h/c0)` and scaling invariance if verified by unit tests.
- Profile the current `_NI=160`, `60` bisection calls × ~600 stations implementation as a **baseline CPU cost**, but don't assume these counts are required for the final error tolerance. The included reference module computes many generalized caps in milliseconds on this environment; real production performance must be benchmarked on your laptop and full geometry pipeline.
- Guard `0<h<2c0` away from the singular fully closed end, `b>0`, `a>0`, and positive/finite cross-section. Do not silently clamp out-of-range values and let the optimizer believe the knob was honored.

**Independent executable reference included:** `HornFab_Lame_Cap_Math_Reference_2026-11-16.py`. It tests the sphere analytic limit, flat Lamé area at `p=2`, increasing flat area for higher `p`, **independently evaluates the original `p=2` ellipsoid-cap integral**, checks quadrature convergence, and solves ratio-locked cap-area solutions. **Not a HornFab implementation or an exact clone of the unpublished 2019 program.**

---

## 5. Precisely defined morph, rollback, and reference-shape controls

### 5.1 One unambiguous longitudinal coordinate

A rollback horn has `z(s,phi)` that **is not globally monotone**. Use `s` as normalized **wall-path coordinate** from the modeled throat (`s=0`) to the last physical lip (`s=1`), constructed from a common parent station parameter. Define `s` once by integrating a **specified reference meridian arc length** (e.g., the unmodified circular parent) and using common `s_i` for every azimuth. Do **not** separately arc-resample each warped row and then assume corresponding station indices represent the same wavefront. Record in geometry metadata exactly which reference path is used and its length in mm.

Three distinct features have separate semantics:

- `s_ap`: the identified **maximum outer shoulder** / relevant horn aperture section, which may be at different physical `z` from other azimuths. For curved rolled horns, define an **auditable reference shoulder**: the base round parent `h=R0` for Klangfilm, or a documented envelope/width functional for JMLC. Never call the final cutoff ring `s=1` the aperture by default.
- `s_forward`: **maximum-forward** axial position, which is not necessarily `s_ap`.
- `s_end=1`: physical terminal rim after rollback, with its own size and normal.

For non-axisymmetric sweeps, the true 3-D acoustic aperture is not necessarily a single plane. Report **maximum W/H of the whole inner wall**, termination-ring W/H, `s_ap`, `s_forward`, `z-range`, and their definitions separately.

### 5.2 Transition schedules: the safe replacement for fractional throat power

The existing 2018 port applies `u ** throat_ellipse` with exponent `0.3..1.0`: for `0<p<1`, the formal slope diverges as `u→0`. This can generate extreme aspect growth immediately after the source and a curvature kink. **Replace in opt-in derived mode, but do not alter the old benchmark.**

Use a bounded C² quintic gate

\[
 Q(t)=6t^5-15t^4+10t^3,\quad
 t=\mathrm{clip}\!\left(\frac{s-s_0}{s_1-s_0},0,1\right).
\]

For example, the aspect and Lamé exponent progress as

\[
 \log q(s)=\log q_0+[\log q_{\rm ap}-\log q_0]Q(t_q),\quad
 p(s)=2+(p_{\rm ap}-2)Q(t_p).
\]

`q0=1`, `p0=2` at physical coupling plane. If early ellipticity is needed, set `s0=0` and finite `s1` / a short physical `morph_length_mm`, **not** a sublinear exponent cusp. Since `Q'(0)=Q''(0)=0`, H/V radial wall tangent remains controlled by the base/source blend at `s=0`.

**To avoid duplicate knobs**, first pass uses a **single morph transition** `morph_to_shoulder_frac ∈ [0.08,0.70]` of *pre-shoulder parent arc length* for both aspect and p; only if sensitivity shows distinct benefit may `p_transition` be separated from `q_transition`. The `p` profile can be a **follow-parent-stretch** ramp or a **hold-after-shoulder** ramp in the rollback; these are **two pinned discrete hypotheses**, not an unvalidated continuous mixing key. The original 2018 stretch falls back after its maximum radius (because `y(h)` decreases); a higher-Lamé photographed full roll may or may not retain its max exponent all the way to the terminal ring. The screenshot alone does not settle that.

**Portability:** normalize by *pre-shoulder arc length* or by a verified physical millimeter length relative to throat diameter, not an arbitrary one-size-fits-all 30 mm. This lets 1-inch, 1.4-inch, 2-inch and different cutoff horns share a shape family without inheriting the wrong absolute transition.

### 5.3 Cross-sectional shape progression and boundary continuity

The primary operator takes parent `P_base(s,phi)` and supplies `(q(s), p(s))`. In `area_mode=curved_cap`, solve §4 per station, then create all radial rays `rho(phi; a_sec,b_sec,p)` at the station with **unchanged source centerline and original axial station**. Apply the optional source-angle correction from §2 in a separately named and versioned stage.

Do not apply both the existing native `morph_target=3` in the mesher and a new GRID Lamé morph to the same design. The shared **semantics** (`target shape=superellipse`, exponent, target W/H, fixed fraction/rate) should be surfaced to the UI, while the GRID **operator** implements the distinct rollback-aware mathematics. A GUI can show familiar knobs via an adapter; this does not imply identical published axial algorithms.

### 5.4 Full rollback / lip controls

**Klangfilm:** `g_end_frac=h_end/R0` is the literal parent termination coordinate and controls how deeply the intrinsic cap rolls. `g_r_lip_mm` as an additive torus **must not** quietly become interchangeable with `end_frac`. Keep parent natural curl in the first family. Only add an optional tangent-blended rim/corner radius if the reference actually requires it, and make its effect separately measurable.

**JMLC:** use `stop` in **wall-tangent degrees**, derived from Fourcade march; H/V differing stop angles make a *non-planar saddle rim*. The old `lecleach_ar` appends an inferred torus that its own code describes as **not tangent**; don't reuse its junction for a 'C2' claim. Use the existing *tangent-lip helper* or a new planar/3-D fillet with geometric continuity measured, and keep the parent Fourcade stop convention explicit. `stop` and added `rim_radius` should not both search when one is functionally inactive.

**Front sweep**: use one physically intuitive control in v1, preferably **edge setback in mm normalized by shoulder width**,

\[
 \delta_z(\phi,s)=-D_{\rm edge}\cos^2\phi\;W(s)
\]

where `W(s)` is a C² gate that starts after the source blend, reaches desired value near the shoulder, and is carried smoothly through the entire rollback. This produces symmetric H-side setback and V-side zero-offset in the quarter model. It is a **derived shape transform**, not an exact construction-vector projection.

If the user/UI insists on a front-arc radius `R`, the relationship at a chosen shoulder half-width `A` is

\[
 D_{\rm edge}=R-\sqrt{R^2-A^2},\quad R\ge A;
 \qquad R=\frac{A^2+D_{\rm edge}^2}{2D_{\rm edge}}
\]

for `D_edge>0`. **Search only one of `R` or `D_edge`**, never both. Prefer `D_edge/A` as a dimensionless search coordinate with no sqrt-domain cliff; compute/display `R` as a *derived readout*. `D_edge=0` is flat; the inverse formula is undefined there and should be represented by a distinct limit. The existing implementation's per-row sagitta displacement depends on `rim_x` inferred from **max over all stations**, and is not intrinsically a mathematically exact circle on the eventual lip. Validate with measured 3-D mouth/front-edge curvature, not a knob label.

### 5.5 Do not claim preservation of curved-wavefront area after arbitrary sweep

A `z(s,phi)` warp changes the geometry of putative wavefront sections. The cap integration in §4 is **pre-warp**. Applying a front sweep, stereographic projection or throat adapter afterward can change the area, normals and phase paths. Record separate fields:

- `cap_area_target`, `cap_area_solved_prewarp`, relative numerical residual;
- `realized_geometric_section_area` of the actual point grid and optional **explicit constructed** post-warp cap proxy;
- any `area_drift_postwarp` **only if** the post-warp wavefront proxy is clearly defined and its area numerically integrated;
- **never** assert “exact wavefront area preserved after sweep” without a valid reconstructed wavefront mapping and an explicit area constraint solve.

The acoustic solver, not a 1-D area equality, decides whether the full twisted/rolled surface performs well. Use the BEM wavefront/pressure field to test phase uniformity where the solver makes such outputs available; otherwise mark that metric not available.

### 5.6 True 3-D wall thickness and surface geometry

`grid.grid_outer_points` offsets each row in its 2-D `(rho,z)` plane. For a surface with large azimuthal sweep or rapidly varying `p(s)`, that direction is **not necessarily the 3-D surface normal**. For the new family, construct an explicit outer surface from a smoothed version of

\[
 \mathbf N(s,\phi)=\frac{\mathbf P_s\times\mathbf P_\phi}{\|\mathbf P_s\times\mathbf P_\phi\|},\qquad
 \mathbf P_{\rm outer}=\mathbf P_{\rm inner}\pm t\,\mathbf N,
\]

with sign fixed against reference geometry and consistent mesh orientation. The derivatives must be stable near symmetry axes. `t` is the physical wall thickness, not just a visual smoothing knob. Require positive Jacobian, consistent face normals, offset-neighbor separation, `t |\kappa_{max}|` below a documented conservative curvature threshold (initial guard `<=0.4` consistent with HornFab's known outer-shell limitation), watertight source and rim closure, and BEM physical tags. **Do not replace the global default `grid_outer_points` behavior** without regression proof: provide `outer_points` explicitly in this new path. Include mounting/enclosure as a separate future case: freestanding shell and mounting enclosure are structurally exclusive in current `grid_build.py`.

---

## 6. Parameterization engineered for efficient optimization across briefs

### 6.1 Avoid three common kinds of degeneracy

**(i) Area-aspect-dimensions overcomplete:** `fc` fixes ideal area law; if `q,p` are free, `a,b` are derived by the curved area root. Don't independently search `W`, `H`, `fc`, and require exact cap area. In an optional *design-to-envelope* mode, instead search **area scale** and **aspect** and treat deviation from the parent `S_target` as a diagnostic/explicit penalty, not silently as exact.

**(ii) Shape vs projection overcomplete:** one `front_sweep_ratio` or `bend_radius`, not both; no `stop_deg` + `end_frac` for the **same** Klangfilm termination semantics; no `Lamé p` with `morph_target` jumping categorically in the same CMA-ES vector.

**(iii) Profile and geometry smoothing:** don't search a high-dimensional dozen-knob Fourier basis before showing that the first 5–7 parameters each make a distinct, detectable geometric/acoustic change. A source-blend must **start disabled or fixed in a separately labeled comparison**, not exist solely to force a 2° manufacturer match. Blend length and mesh resolution must remain fixed during any subsequent geometry optimization and satisfy actual throat-size/curvature/feasibility checks.

### 6.2 Meaningful physical coordinates and initial boxes

These are **candidate bounds, not experimentally validated optimal ranges**. Final boxes must be intersected with geometry-only feasible regions of each brief. `scale_to` means no hardcoded 36 mm throat assumptions.

| Optimum-independent parameter | Units/search representation | Initial investigatory box | Driver / mathematical meaning | First-run status |
|---|---|---|---|---|
| `g_base_fc_hz` | Hz, **log** scale with bounded physical mapping | Derived from brief crossover, envelope and parent feasibility; current seed **560**; *test*, not universal range `[480,800]` | Klangfilm `R0=c/(pi fc)`; fixes cap-area law and size. **Nominal cutoff, not guaranteed acoustic cutoff** | **Search** (family-specific) |
| `g_T` | dimensionless | JMLC reference `0.3..1.0` and source-legal constraints, not for Klangfilm | Hyperbolic-sine area-law shape parameter. `T=0.5` quasi-Iwata concept is a convention, not proof of exact Iwata reproduction | Search only in *JMLC derived* run |
| `g_aperture_aspect` | true H/V ratio `q_ap=a/b` | Start `1.15..2.5`, positive; intersect width/height + curved-area feasibility | Independent physical H/V anisotropy; do **not** confuse with original 2018 minor-axis `stretch` | **Search** |
| `g_lame_p_ap` | Lamé exponent, continuous | **2..6** main; **6..8** optional curvature-refined second stage; not >8 initially | Physical cross-section rounding. **p=2 is ellipse**, and `a=b` at p=2 is circle | **Search**, once math verified |
| `g_morph_to_shoulder_frac` | fraction of **pre-shoulder arc length** | `0.08..0.70` as geometry investigation, not a law | Governs how quickly a round source becomes asymmetrically elliptical and rounded | Search **after** gate and only if effect distinct |
| `g_termination_frac` | Klangfilm `h_end/R0` | `1.05..1.80` for rolled branch; full 2018 legal `0.3..1.9` remains benchmark range | Parent rollback termination, NOT free lip radius or mouth width | **Search** |
| `g_rim_sweep_ratio` | `D_edge/A`, dimensionless | `0..0.35` initial; CPU-check curvature and shell | Swept mouth H-side setback, normalized to shoulder size | Search only after source/area tests |
| `g_source_blend_ratio` | `L_b/(2 y0)` | **Disabled on raw-parent baseline**; optional 10–30 mm examples in a separate 1-variable CPU/BEM study, never assumed universally optimal | CAD horn-entry contour experiment, **not a verified HF1440 tangent correction**; disturbs published curved-cap model | **Not searched** initially |
| `g_lame_tail_mode` | categorical pinned: `follow_parent_stretch` / `hold_after_shoulder` | Two **separate geometry experiments** | Control how squareness continues into full rollback; exact 2019 choice unknown | **Pinned**, not CMA continuous gene |
| `g_area_mode` | categorical pinned: `published_2018` / `curved_cap_ratio_locked` / `flat_section` | Separate ablations; only one source contract per campaign | What is preserved and what is adjustable | **Pinned** |
| `g_outer_thickness_mm` | mm | Manufacturing/freestanding value fixed (current seed 3 mm), curvature-safe | 3-D offset and enclosure, not an acoustic free shape coefficient | **Fixed** |

**Dimensionless brief transfer:** `D_edge/A`, `L_morph/L_shoulder`, `L_source/D_throat`, `q_ap`, `p` are meaningful across driver sizes. `fc` is family-specific; search range from realistic throat/mouth/frequency constraints. Do not **automatically** set `fc=f_cross`, `q=coverage_H/coverage_V`, or `a∝1/coverage`; those are not validated directivity laws.

**The current brief's `80×50` coverage does not imply mouth aspect 1.6 or an 80°/50° wall tangent.** Physical H/V pattern is influenced by mouth size/wavelength, driver wavefront, flare, boundary mounting and frequency [S11,S12,S13]. Optimize actual polar cuts.

### 6.3 Two useful initial optimizer campaigns, not one bloated mixed campaign

**Campaign A: `klangfilm_lame_curved_v1`.** **No compulsory 2° source_blend**. Use the raw parent or a single acoustically justified, explicitly fixed entrance design selected by the small T1 ablation; fixed `area_mode=curved_cap_ratio_locked`, fixed `tail_mode=follow_parent_stretch`, fixed v7 smooth brief. Search initially 5 continuous: `(fc_hz, q_ap, p_ap, termination_frac, rim_sweep_ratio)`. Add **morph_length fraction as a sixth dimension** only after showing meaningful acoustic sensitivity. If the zero-sweep family cannot match the long reference, do not force massive sweep values to compensate for an inherently short parent.

**Campaign B: `jmlc_swept_lame_v1`.** Parent verified Fourcade JMLC, fixed source interface and same v7 brief. Search 5–7: `(fc_hz, T or pinned T, q_ap, p_ap, stop0, H/V stop contrast [optional], rim sweep)`. One physical termination parameterization: `stop_H = stop0 + delta_stop`, `stop_V = stop0 - delta_stop`; fit to legal per-row stop range and prevent folded/self-contacting rims. **One principal cutoff + one contrast**, not independent cutoff-on-each-azimuth at first. This is a *derived* 3-D family, not a publication-verified E-JMLC formula. For JMLC, the initial meridian angle is a mathematical construction input, **not a verified HF1440 manufacturer parameter**; apply an optional local correction only after the same T0/T1 controlled source/geometry evidence, and keep its effect on wavefront math explicit.

A separate late **Lamé profile design** may optimize a gentle corner exponent schedule, H/V midflare exponent or one `cos(2phi)` term, **only after the base family is physically and statistically identifiable**.

---

## 7. Preflight geometry invariants and cheap rejection before GPU

**Geometry rejections are hard constraints** with explicit reason codes and graded distance where appropriate. Test intermediate warped inner and explicit 3-D outer points **before** gmsh and avoid generating mesh for impossible candidates.

1. **Source plane:** `W=H=2*y0` within `0.1 mm` on the **unmeshed** analytic boundary; source eccentricity `|W-H|/(W+H) < 0.005` (tune after physical source quantization); source area/shape and BEM tag are separately checked. For 1.4-inch HF1440, compare **modeled 36.0 mm** to manufacturer **35.8 mm** and report the `0.2 mm` modeling difference. Do not label ellipse-area ratio ~1 as "round" when width != height.
2. **Source tangent (v3 correction):** verify `|alpha_wall_actual - alpha_design_declared| < 0.25°` where a **modeled horn-entrance angle is intentionally specified**, and record **the actual H/V and azimuthal tangent**. For raw Klangfilm `fc=560,r_t=18`, this is **10.617°**, not the legacy brief's 2°. **Do not reject a raw candidate for not matching 2°**: HF1440 has no numeric angle specification. Distinguish wall tangent, source-cap curvature, and real driver wavefront; verify material source geometry, point normals, physical entrance circle, and triangle tag 2. Use independent refinement checks at 0.1/0.05/0.025 mm only where geometry permits. Zero-degree source design requires supported proper source closure; do not spoof a nonzero angle to force tag 2.
3. **No throat pinch:** radial opening must not fall below physical driver radius / local acoustic design minimum over the designated transition (except tiny declared numerical tolerance), particularly along the V axis; enforce monotone growing area through intended flare zone until rollback starts.
4. **Sane parent domain:** `R0>y0`, `0<h<2R0`, no capped singular endpoint, all values finite, proper `h(s)` ordering; required target aspect/exponent differentiable in `s`.
5. **Wavefront area:** `curved_cap` residual `|Scap-Sparent|/Sparent <= 1e-5` exploratory, `<=1e-7` reference after independent quadrature check; clearly separate *post-sweep* error and actual acoustic simulation.
6. **Surface metric:** `||P_s×P_phi||` positive away from degenerate boundary, consistent orientation, no two-row crossings, no self-intersection, no reversed triangles, no source/curl loops crossing, no corner strip inversion.
7. **Outer shell:** true normal shell thickness within tessellation tolerance, curvature offset guard (e.g. `t|max_kappa|<0.4` starting threshold), shell-to-shell clearance above `2 t` plus safety margin; symmetry seam welded and no accidental double caps.
8. **Envelope:** min/max over **both entire inner and entire outer surfaces**, not only final mouth ring; include mounting/rear details when relevant; record real max width/height/depth and point locations.
9. **Acoustic topology:** mesh source tag 2 present/nonzero; watertight freestanding surface or correctly declared enclosure, legal symmetry planes, no source planes accidentally converted to rigid wall, no vanished BEM triangles.
10. **Active dimensionality:** if changing a searched knob by ±1–2% changes no geometry beyond mesh tolerance (e.g. <0.1mm maximum or <1e-4 relative in meaningful descriptors), remove/pin it and do not spend BEM calls on it. Conversely, when morphology is mathematically active but its effect is too small for the present mesh, increase geometry discretization or narrow the search parameter to a measurable control, not blindly penalize.

**Additional structure metrics (report-only first):** min throat/midflare area ratio, max local transverse curvature, 95th percentile curvature, max growth of \(d\log A/ds\), no negative local curvature unsupported by parent, variance/second derivative of `q(s)` and `p(s)`, arc-length coverage of >5° normal rotations per triangle, outer-shell minimum separation. Do not add 10 new objective weights; start as feasibility and diagnostics.

---

## 8. Meshing, BEM accuracy and hardware-aware frequency work

**Do not equate a successful 5,832-DOF meshing report with accurate 8 kHz directivity.** Check a wavelength-based resolution measure AND local curvature error. At `f_max`, `lambda=c/f_max`; a first scalar estimate is

\[
 h_{\rm wave} \lesssim \frac{c}{N_{\rm epw} f_{\max}},\quad
 h_{\rm curve} \lesssim \sqrt{\frac{8\epsilon_{\rm chord}}{|\kappa|}},\quad
 h_{\rm target}=\min(h_{\rm wave},h_{\rm curve},h_{\rm throat}).
\]

This chord-error bound is a local approximation and **not a universal guarantee** for triangle quality, scattering or the GPU backend. At 8 kHz, `lambda≈42.9mm` with `c=343`; 6 EPW corresponds to ≈7.15mm **only where that criterion is actually met**. Curled high-Lamé corners and the source can need substantially finer local mesh; changing global resolution alone is wasteful.

- **Coarse geometry**: high-resolution 3-D point grid (e.g. 19×64 is a starting visualization grid, *not* a guarantee for p=8), curvature-adaptive resampling; convergence test against denser `n_phi`, `n_s`.
- **Screen acoustic**: use the repo's unchanged v7 screen frequency grid/backend/score for A/B within a frozen cohort; do not make a score claim from geometry visual match. If solver cannot reach the entire band with acceptable mesh, create a **new explicitly named lower-fidelity protocol** rather than quietly truncating frequencies from v7.
- **Verify**: re-solve same saved physical design with finer mesh and denser frequency/angle coverage, check H/V/diagonal polars, impedance and coupling. Compare response *arrays* on matched frequencies, not just the scalar objective.
- **Final**: inspect selected 8, 10, 12 and 20 kHz only if mesh counts, solver memory and source model actually support it. This new morphology should not be marketed as 20 kHz-validated simply because the HF1440 datasheet goes to 20k.
- **BEM symmetry:** quarter symmetry is valid for Lamé + `cos(2phi)` sweep and H/V stop contrast if all signs/mirror planes match. Breaking H/V or L/R reflection requires half/full model and increased DOFs. Do not turn on symmetry reduction for asymmetry modes not guaranteed by the generated surface.
- **Known external benchmark:** Kolbrek's real horn BEM examples often use around **six elements per wavelength** and an explicit constant throat velocity source [S18]; this is context, not universal clearance for a new 3-D curled shell. The 2015 Godinho paper uses image-source symmetry in 3D horns [S13].
- **Resource budgeting:** compute predicted triangles and VRAM/host-RAM before meshing; sample a couple of max-size seeds; cap 8 GB RTX 4060 peak use; record walltime and resident memory by frequency. Favor block/frequency reuse and solver improvements from your existing throughput work, not new geometry inside the acoustic solver.

---

## 9. Acoustic scoring that actually targets H/V dispersion without fooling the optimizer

Freeze the **existing objective v7** and its weights initially. **Add read-only diagnostics** to prevent exploiting weak spots in a scalar score:

1. **H/V -6.0206 dB main-lobe beamwidth**, separately from legacy `outermost crossing`. The main-lobe edges are the FIRST threshold crossings moving outward from the 0° axis on each side; if no crossing is found within angular sampling, mark **censored/unknown**, not a precise 180° beamwidth. Keep legacy value for backward compatibility.
2. **Extra crossing count**, strongest sidelobe or off-axis peak, amount of energy outside intended H/V coverage. A non-monotonic pattern with several lobes must not earn a wider-beam bonus simply because the *outermost* crossing moved outward.
3. **Diagonal and full-balloon**: average and worst irregularities near 45°, fitted -6 dB superellipse residual (`metrics/beam_shape.py`), directivity index slope, response to ±30°/±40° and vertical angles, off-axis nulls across frequency.
4. **Loading**: normalized real throat resistance, magnitude and ripple of complex `Z_throat`, response smoothness on-axis and in-window. A circular source velocity model differs from a full driver/phase-plug model; report limits.
5. **Frequency smoothness**: avoid one-point success; measure `d BW/d log f`, `d DI/d log f`, and both worst-case and weighted average errors. Use physically motivated sampling bands near XO, between 1–6k, and 6–8k if reliable.
6. **Area-vs-acoustics ablation:** compare identical parent + Lamé p=2, p=4 and p=6 with the **same derived curved cap area**, and separately with the flat-area approximation. If acoustic differences are below numerical convergence, Lamé exponent is not worth an expensive free gene at this fidelity.

**Possible new metric definition for a later scorer version (not now):** for frequency index `i`, H/V target `C_H,C_V`, measured main-lobe widths `B_Hi,B_Vi`, and weights `w_i`,

\[
 E_{\rm cov} = \frac{\sum_i w_i\,\left[(B_{Hi}-C_H)^2/\tau_H^2 + \beta_V (B_{Vi}-C_V)^2/\tau_V^2\right]}{\sum_i w_i},
\]

with `tau_H,tau_V` declared tolerances and `beta_V` taken from brief if appropriate. This is **our suggested later metric**, not the current v7 implementation. A robust H/V objective would also penalize sidelobes, ripple and underloading. Never change the scorer and geometry family in the same scientific A/B experiment; preserve the original raw BEM data to allow offline replay under new scores.

**Scientific support:** Gu, You & Shen, *JASA* 158(3), 2025 explicitly formulate simultaneous efficiency, smoothness and separate H/V directivity/coverage objectives with an algebraic gradient [S14]. The published abstract supports the *principle*, **not** copying their exact objective weights into HornFab without the full paper.

---

## 10. Compute-efficient optimization and experimental design

### Step 0 — analytic reduction and preflight (CPU only)

- Before fitting a surrogate, identify **actual independent dimensions**. Implement no-op/conditional parameter audit based on mesh and physical descriptors, not hand-authored optimism.
- Generate **64 scrambled Sobol** points (power of two, SciPy `qmc.Sobol.random_base2`) in the 5–7D normalized box [S19]. For each, evaluate physical validity, curved cap residual, geometry descriptors, shape-only silhouette and rough meshing estimate. Refine bounds/pin features based on *feasibility* and *sensitivity*, not by discarding all odd but feasible shapes.
- Add max 8–16 test corners/one-at-a-time perturbations and at least 2 distinct seeds. Critical cases `p=2,4,6,8`, `q=1`, `sweep=0`, shallow/deep rollback, source adapter off/on. **Do not sample 64 expensive BEM solves here.**
- Finite-difference a normalized shape-descriptor Jacobian `J_ij=∂descriptor_i/∂x_j` and inspect singular-value ratio, collinearity and zero columns. Choose the smallest parameter set with identifiable shape changes. This does not prove acoustic independence; it is a cheap screen.

### Step 1 — acoustic baselines / controlled ablations

Use a small **fixed 6–12 physical-design set** for first evidence, chosen after feasible shape preflight: original axisymmetric Fourcade/JMLC, `iwata_ar` reconstruction, 2018 Klangfilm base, ratio-locked `p=2` curved wavefront, `p=4` and `p=6` area-matched, a swept and unswept pair, and a fixed-source throat-angle **sensitivity** pair (neither may be labeled physically matched to HF1440 without independent manufacturer CAD or measurement). A matched design must be identical in physical driver, outside boundary, equivalent area/size, mesh fidelity and frequency sampling whenever the comparison claims the effect of one parameter.

### Step 2 — search, minimum useful budget

- **First optimizer:** existing CMA-ES, because supported/tested pipeline, or the completed versioned BoTorch implementation if compatible with this new GRID recipe. Do not switch the production campaign mid-run.
- **BoTorch:** use frozen protocol and **same geometry mode/driver/scorer/fidelity**. Candidate methods include noisy constrained log EI, cost-aware acquisition and eventually multi-fidelity KG; these are explicit documented methods, not proof that BO automatically beats CMA-ES for this problem [S20,S21,S22].
- **Separate models by fidelity** unless a cross-fidelity relationship is empirically measured. A screen solve with changed mesh/frequency sampling is **not just a noisy repeated measurement** of verify; its bias can be systematic.
- Initial acoustic design budget **12–24 strategically chosen evaluations per typology**, then extend only if feasible geometry rate, acoustic sensitivity and learning curves justify additional cost. This is a planning heuristic, **not a theory-proven optimum sample count**. Don't launch 60 solves because a YAML already contains `budget:60`.
- When comparing CMA vs BO, fix **the same feasible initial population**, scorer, resource accounting and evaluation opportunities. Compare **best verified acoustic result per unique physical mesh+solve** and **per wall-clock hour**, feasibility rate, cache hits, ability to transfer to a changed brief, and uncertainty. Include 2–3 seeds before claiming an optimizer improvement.
- Tune **7 or fewer** continuous dimensions first. An unsupported 15-gene search may be slower and less interpretable even if the optimizer can technically run it. Add degrees only when genuine acoustic residuals indicate a clear need.

### Step 3 — reusability and data integrity

Every persisted physical shape must contain: parent-family identity and version, all effective dimensions/knobs, Lamé `p(s)` and aspect schedule, area mode, source tangent policy, acoustic source model, c-air, quad rule/order/tolerances, sweep convention, geometry code SHA/digest, driver and brief hash, mesh hash/solver SHA, frequency vector, and scorer version. **Hash geometry independently from scoring policy.** A changed scorer can replay **raw complex BEM/balloon response arrays** only when the necessary information and frequency/angle sampling exist. New morphology is a new geometry and needs a new mesh + solve, but scores of **unchanged** geometries should remain reusable. Do not claim that a geometry digest is automatically a semantic proof of equivalence if floating-rounding or dependency changes affect output.

Reject and report legacy recipes with incompatible schema; do not silently reinterpret the old `g_stretch` as true aspect ratio or old `g_throat_ellipse` as a C² transition. The original 2018 CLI remains a replay path for old exact outputs.

---

## 11. Detailed integration contract for agent: exact modules and sequencing

**Implementation hierarchy:** use native library infrastructure rather than another process-global monkey-patch. Prefer a new small `hornlab_search/design/generators/lame_cap.py` (pure math) and `swept_elliptical_wavefront.py` (surface/geometry), then a versioned registration/adaptation into the existing GRID factory. Do not indiscriminately edit `hornlab_mesher` internals, `search/evaluate.py`, `bo/encoding.py`, and the scorer.

Recommended steps:

1. **Read all project rules and current diff:** `AGENTS.md`, `TOOLCHAIN.md`, `docs/CONTINUITY.md`, live configs and implementations listed in §0, `docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md`, `docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`, the Math/optimization hardening notes, the user-uploaded workbook coordinate cache. Pin HEAD and avoid concurrent worktree collisions.
2. **Add math kernel:** fixed-ray `rho`, analytic gamma flat area, `lame_cap_area`, adaptive quadrature, `area_preserving_axes`, numerical stability tests, dimensions/limits. Use the accompanying executable reference to check formulas. The public source [S05] establishes the published `p=2` limit, not our generalized-`p` identity.
3. **Freeze base parity:** old Klangfilm 2018 profile (`p=2`, published original fixed-b mode) matches the 9 cached workbook stations within 0.001 mm in the earlier local agent's report, **rerun independently**. Fourcade fixture remains unchanged. Save hashes. Unit tests for no-op/identity must precede new morph tests.
4. **Create a composable typed geometry operator:** `base_profile -> optional source_blend -> Lamé/area correction -> optional rim sweep -> explicit outer shell -> topology/preflight -> mesh`. Every operation owns a unique `version` and is opt-in. Surfaces must be emitted as `{inner_points, outer_points, meta}` or the equivalent accepted by GRID builder.
5. **GRID registration:** suggested names `rows.type: klangfilm_lame_v1` and later `rows.type: jmlc_swept_lame_v1`. Pass `n_phi`, `n_s`, symmetry and driver metadata exactly into `PointGridHornGeometry` via current `mesh/grid_build.py`. The exact `from_config` normalization and accepted knobs must be added to the central parameter catalog/prose as well as validation. **A sample new YAML without those code changes will not be loadable.**
6. **Versioned recipes and rehydration:** `schema`, math digest, original parent law and parameter names, source and c-air, quadrature tolerances, all effective schedule and termination parameters; prove an exported saved design materializes identically in a *fresh process* using both CLI and GUI. Historical unmodified hashes remain stable.
7. **Geometry/provenance test suite and CPU shape-check:** all tests in §7 plus 4 views (front/top/side/3/4), throat close-up, wireframe normals and sections at `s=0,.02,.1,.3,.6,s_ap,1`. Same camera/view scale as provided references; don't optimize 3-D geometry to arbitrary unmatched perspective photo projections.
8. **Then a separate acoustic PR / experiment:** only after peer review of geometry gates. No solver/scorer refactor bundled into geometry PR. Use same driver/brief/mesh/source conditions for comparisons.

Suggested test files:

- `tests/test_lame_area_math.py`: flat gamma area, spheroid/ellipsoid limit, real `p>2` integration convergence, bracket failures, deterministic repeated results;
- `tests/test_lame_source_tangent.py`: exact round source, prescribed source slope, finite C², incorrect 2018 raw tangent regression;
- `tests/test_lame_rollback_geometry.py`: shoulder vs terminal rim, 360° mirrored/watertight, C² transitions, no self-intersections, true 3-D offset thickness;
- `tests/test_lame_parameter_activity.py`: active knobs/no-op test, crossed bounds, source angle/driver changes, geometry-hash sensitivity;
- `tests/test_lame_rehydrate.py`: fresh-process roundtrip, old-byte/old-hash unaffected, intentional digest drift refused/versioned;
- `tests/test_lame_mesher_regression.py`: source tag 2, quadrants, valid normals and surface topology, immutable OSSE/JMLC/Iwata smoke cases.

**No double-morph:** if the new GRID mode uses Lamé operator, reject `morph_target` / `morph_exponent` passed into a second native mesher stage unless a *clear, separately versioned* composed purpose exists and was tested. The GUI may display an equivalent user-facing control, but exactly one geometry stage owns the outline.

---

## 12. Acceptance gates and explicit stop rules

| Gate | Required evidence | Stop / reject if… |
|---|---|---|
| G0. Code & license | clean worktree, version stamps, old source preserved, permission/redistribution reviewed | concurrent edits may be overwritten, or proprietary direct-port distribution restrictions unresolved |
| G1. Published limits | sphere cap analytic; p=2 matches validated area; 2018 workbook parity independently rerun; Fourcade fixture unchanged | `p=2` not correctly reduced, body differs from old reference when off |
| G2a. Mechanical aperture | round **36.0 mm legacy modeled**, **35.8 mm factory** (future candidate); no V pinch; both circles/areas measured in actual mesh | wrong entrance size, nonround coupling plane, C0 shape discontinuity |
| G2b. CAD entrance geometry | analytic H/V/azimuthal wall tangents match **chosen design target**, which may remain the raw 10.617°; do **not** require 2° | wall tangent hidden/misreported by `source_auto_angle_deg`, a C0/C1/C2 splice, inactive parameter |
| G2c. Acoustic source/driver fidelity | fixed and explicitly named source cap/velocity hypothesis, valid source tag 2, full provenance; manufacturer HF1440 physical slope **unknown**; later validation by CAD/measurement | arbitrary cap shape changes across supposedly matched A/B, source unmeshed, claim of physical HF1440 slope without evidence |
| G3. Cap math | area relative error checked at extreme p/q/h; stable 24/48/96 quadrature; ratio/axes finite | flat area equated with curved area, root solver silently clips, nonconvergent bracket |
| G4. Geometry | surface/Jacobian/shell/self-contact/phase tag tests pass; rollover and shoulder indices correct | outer shell uses wrong normal, warped fold intersects, inlet/termination conflated |
| G5. Visual | multi-view renders compared at same angle/scale with annotated reference, silhouette/shape limits documented | matching only one perspective disguises gross 3-D mismatch |
| G6. Acoustics | 6–12 representative BEM cases; H/V main lobe, diagonals, complex loading, full-balloon and frequency convergence | a few single-frequency plot peaks masquerade as coverage or GPU convergence fails |
| G7. Optimization | ≤7 meaningful genes, validated preflight, versioned frozen scorer/geometry, identified cost, independent holdouts | high invalid rate; redundant controls; best solver J unverified; old data not reusable |

**Stop early** if the long reference remains geometrically implausible for the short Klangfilm parent even with reasonable Lamé/sweep parameters. Test the JMLC-derived parent instead of using huge warped offsets to force the silhouette. Likewise, if high `p` produces no robust acoustic improvement over `p=2` in verified matched geometry, pin it and save compute.

---

## 13. Optional example config: design contract only, NOT copy-paste loadable today

The following illustrates the **desired** public config API, not existing recognized keys. Implement and test the parser, central knob catalog and source/mesh contracts before use:

```yaml
name: hl__klangfilm_lame_curved_v1
family: FREEFORM
brief_file: ../../briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml
generator:
  name: grid
  rows:
    type: klangfilm_lame_v1                  # NEW, NOT YET REGISTERED
    parent: klangfilm_2018                    # published baseline, independent of derived extensions
    area_mode: curved_cap_ratio_locked       # NEW, derived curved superellipsoid-cap model
    lame_tail_mode: follow_parent_stretch    # category PINNED for the run
  span: quarter
  n_phi: 31                                 # test resolution, not a convergence claim
  n_s: 96
  wall_thickness_mm: 3.0
  seed_policy: explicit
seed_params:
  g_base_fc_hz: 560.0
  g_aperture_aspect: 1.6
  g_lame_p_ap: 3.5
  g_termination_frac: 1.50
  g_rim_sweep_ratio: 0.12
  g_morph_to_shoulder_frac: 0.30
  g_source_blend_ratio: 0.00             # OFF: retain original 2018 throat in first campaign
bounds:
  g_base_fc_hz: {lo: 480.0, hi: 800.0}
  g_aperture_aspect: {lo: 1.15, hi: 2.30}
  g_lame_p_ap: {lo: 2.0, hi: 6.0}
  g_termination_frac: {lo: 1.05, hi: 1.80}
  g_rim_sweep_ratio: {lo: 0.0, hi: 0.30}
  g_morph_to_shoulder_frac: {lo: 0.30, hi: 0.30, search: false} # unlock only after sensitivity
  g_source_blend_ratio: {lo: 0.00, hi: 0.00, search: false} # fully disabled
mesh: {epw: 6.0, quadrants: '1'}           # fill all validated production-required fields
solve: {backend: beat_cuda}                # fill rest from *frozen* current campaign
search: {algorithm: cma, budget: 0}        # geometry-only first: NO GPU SEARCH
```

**Don't use untested bounds as a promise of 64/64 feasible shapes.** The maximum exterior W/H/depth and `R0>y0` are computed constraints, not static approximations. For an optional future *nonzero* source blend, the implementation must report its modified station interval and curved-cap area drift, and treat the result as a derived geometry rather than a faithful 2018 construction. The pinned zero blend in this illustrative initial campaign must be exactly geometry-identical to the unmodified entrance.

---

## 14. Testable independent reference file usage

The accompanying `02_LAME_CAP_MATH_REFERENCE.py` is stand-alone Python code using NumPy and SciPy. From the repo root **after placing it in a scratch/research directory, not a production package**:

```powershell
.venv\Scripts\python.exe .\scratch\02_LAME_CAP_MATH_REFERENCE.py
```

Expected: `PASS: sphere analytic cap; flat area; legacy ellipsoid cap; quadrature convergence; ratio-locked area solve`. It was executed successfully in the research container on 2026-11-16. The mathematical **model** and test code are new derivations; neither came from the full private 2019 calculator. A production port must also test analytic gradients or consistent finite differences across parameter changes and performance on the Windows 4060 laptop.

---

## 15. Exact implementation assignment to local agent

> Perform a scoped new-worktree implementation of a **versioned reusable Lamé cross-section and curved-wavefront-area kernel** for rollback GRID horns, initially the Klangfilm parent, later a JMLC-derived parent. Read this entire dossier, uploaded handoffs, previous reference images/workbook cached coordinates, current main and local worktree diffs. Preserve original `klangfilm_ellipse.py` and its old hashes. Implement §3–4 equations with analytic sphere/ellipsoid/flat-area regression, an actual **round 36.0 mm legacy modeling source** (and future **35.8 mm manufacturing-fidelity** version), **no compulsory 2° wall-tangent correction**, common arc-based morph progression, explicit 3-D outer normals and volume validity, then deterministic CPU geometry/renders before any BEM. Include the proposed Lamé exponent `p=2..6`, physical aspect and termination plus single rim sweep, but do not add extra optimizer genes prematurely. Use native typed GRID registration, not another global monkey-patch. Document hypothesis vs published math for any generalized superellipsoid area/sweep/projection claims. Publish a geometry-only PR, CPU test results and matched camera contact sheet. **Do not launch GPUs, alter score v7, change production defaults or interfere with live queue.** After geometry review, deliver a separate measured small BEM ablation and then a same-cohort CMA/BO comparison. Every config/mesh/solver/score remains reproducible and all existing raw data reusable when its physics identity is unchanged.

---

## 15A. Mandatory HF1440 source/tangent interpretation, updated 2026-11-16

**Implementation gate override:** FaitalPRO HF1440 is a 35.8 mm **Combined Exit** with no numerical manufacturer exit angle. `driver.exit_angle_deg: 2.0` is an **assumed legacy HornFab model input**, while `10.617223°` is the **derived pure Klangfilm wall half-angle at fc=560 Hz with 18 mm radius**. These must never be conflated. Do not force a 2° throat in production or interpret passing a 2° CAD tangent test as acoustic fidelity to HF1440. Perform T0 analytical source cap and wall inspection, then a small fixed-source T1 BEM ablation if throat adaptation is worth exploring, before exposing a new optimizer gene. See `03_THROAT_COUPLING_SENIOR_ADDENDUM.md` for 26 manufacturer, peer-reviewed, original-author, practitioner and repository reference records (not all are independently verified full-text) and the source/angle parameters.

## 16. Bibliography and evidence matrix (primary sources preferred)

**The source list is intentionally broader than the code we will actually implement.** A cited abstract supports its stated result, not access to undisclosed formulas or an endorsement of HornFab's particular implementation. Read actual source details before coding the associated equations.

| ID | Source (URL) | What it establishes | Use / confidence |
|---|---|---|---|
| **S01** | [Kolbrek, *Horn Theory: An Introduction*, Part 1 (audioXpress 2008)](https://www.jmargolin.com/sono/refs/ref25_2008-014_Kolbrek_-_Horn_Theory_An_Introduction_Part_1.pdf) | Classical horn area/impedance, cutoff assumptions, limits of 1-D theory | Primary tutorial [P] |
| **S02** | [Kolbrek, *Horn Theory*, Part 2 (2008)](https://espacenomeutente.altervista.org/wp-content/uploads/2019/09/Horn-Theory-An-Introduction-Part-2-By-Bjorn-Kolbrek.pdf) | Spherical-wave horn cap, intrinsic rollback, directivity/modes | Primary tutorial [P] |
| **S03** | [Ahlswede, original Klangfilm elliptical calculator (diyAudio 2018)](https://www.diyaudio.com/community/threads/klangfilm-spherical-wave-horn-calculator-from-round-to-elliptical.328970/) | DIY-released Excel/VBA approach; original round→ellipse curved-cap area solve; permission warning | Original author [O] |
| **S04** | [Ahlswede, diyAudio page 4 post #68 (2019-03-10)](https://www.diyaudio.com/community/threads/klangfilm-spherical-wave-horn-calculator-from-round-to-elliptical.328970/page-4) | Actual high-Lamé exponent *rectangular fully rolled* screenshot/text supplied by owner | Original author [O]; fragment may not deep-link |
| **S05** | [Ahlswede, *Ellipsoidal Wave Fronts in Horns* (Aug 2019)](https://sphericalhorns.net/2019/08/05/ellipsoidal-wave-fronts-in-horns/) | Lamé eqs 1–8, starting 2-D area, curved ellipsoid-cap eq 21, root solve, stretch progression, numerical warning | Primary detailed article [O/P] |
| **S06** | [Ahlswede, William Neile ALO SE horn (Feb 2023)](https://sphericalhorns.net/2023/02/25/the-first-making-of-a-william-neile-alo-se-horn/) | `p=2` at throat; downstream varying Lamé exponent; higher-p point-cloud and projected wavefront issues | Later primary experience [O] |
| **S07** | [Ahlswede, diyAudio page 2 posts #21–22 (Nov 2018)](https://www.diyaudio.com/community/threads/klangfilm-spherical-wave-horn-calculator-from-round-to-elliptical.328970/page-2) | Three construction-vector bending alternatives and stereographic projection; not in uploaded v10 | Original author [O], full math unavailable |
| **S08** | [Fourcade, *Calcul du Pavillon Le Cléac'h* (2015)](https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf) | Exact published axisymmetric march, area law, source angle/roll, reference fixture | Source primary [P]; link may require alternate mirror |
| **S09** | [Batík, *OS-SE Waveguide* (2020 PDF)](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) | OS-SE profile Eq 5, **axial** morph §5 `(z-zf)^gamma`, `gamma>=1`, non-flat rollback requires separate extension | Author primary [P] |
| **S10** | [Batík, *Ath User Guide* 4.8.2 PDF](https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf) | Morph rate/fixed semantics, rollback start specified by actual wall profile length | Author guide [P] |
| **S11** | [Geddes, *Acoustic Waveguide Theory* (JAES 1989)](https://aes.org/publications/elibrary/elibrary-page/?id=6078) | More general waveguide physics than planar Webster horn theory | Peer-reviewed [P] |
| **S12** | [Kolbrek, later horn theory clarification + higher modes](https://kolbrek.hornspeakersystems.info/index.php/horns/horn-theory) | Author cautions his 2008 introduction is not a complete physical model; mode propagation work | Author [P/O] |
| **S13** | [Godinho et al., *3D numerical modelling of acoustic horns…* (2015)](https://doi.org/10.1016/j.enganabound.2014.09.013) | 3-D horns, symmetry and MFS/domain decomposition | Peer reviewed [P] |
| **S14** | [Gu, You & Shen, *Multimodal-based shape optimization of rectangular horns…*, JASA 158 (2025)](https://doi.org/10.1121/10.0039253) | Integrated efficiency/smoothness/separate coverage goals, gradients | Recent peer reviewed [P], abstract verified |
| **S15** | [Bängtsson, Noreland & Berggren, *Shape optimization of an acoustic horn* (2003)](https://doi.org/10.1016/S0045-7825(02)00656-4) | Adjoint Helmholtz + smooth geometry updates; irregular contours harmful | Peer reviewed [P] |
| **S16** | [Schmidt, Wadbro & Berggren, *Large-Scale Three-Dimensional Acoustic Horn Optimization* (2016 PDF)](https://people.cs.umu.se/martinb/downloads/Papers/ScWaBe16.pdf) | Memory-efficient adjoint 3-D shape optimization, 1,762 variables; not an implementation recipe for HornFab's solver | Peer reviewed [P] |
| **S17** | [Wolfram MathWorld, Superellipse](https://mathworld.wolfram.com/Superellipse.html) | Lamé planar equation, angular parameterization and area identity | Mathematical reference [P] |
| **S18** | [Kolbrek's BEM horn simulation gallery](https://kolbrek.hornspeakersystems.info/index.php/horns/bem) | Practical 3-D horn BEM, mesh and uniform source context | Experienced developer [O] |
| **S19** | [SciPy, scrambled Sobol / power-of-two sampling docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html) | Balanced exploratory low-discrepancy designs | Official numerical docs [P] |
| **S20** | [BoTorch, noisy constrained BO tutorial](https://botorch.org/docs/v0.14.0/tutorials/closed_loop_botorch_only) | Constrained/log-EI acquisition; implementation patterns | Official [P] |
| **S21** | [BoTorch, cost-aware BO tutorial](https://botorch.org/docs/tutorials/cost_aware_bayesian_optimization) | Expected improvement per cost, model evaluation cost | Official [P] |
| **S22** | [BoTorch, multi-fidelity KG](https://botorch.org/docs/v0.15.0/tutorials/multi_fidelity_bo) | Multi-fidelity surrogate requires modeled fidelity/cost relationship | Official [P] |
| **S23** | [Hansen, *The CMA Evolution Strategy: A Tutorial* (2016)](https://www.cmap.polytechnique.fr/~nikolaus.hansen/cmatutorial) | CMA-ES, conditioning, restart and boundary guidance | Primary tutorial [P] |
| **S24** | [Takahashi et al., 3-D isogeometric BEM adjoint optimization (2022)](https://doi.org/10.1016/j.cad.2021.103126) | Smooth NURBS control points with Helmholtz BEM and shape gradients | Peer reviewed [P] |
| **S25** | [Ummidivarapu et al., isogeometric horn shape optimization with TLBO (2020)](https://doi.org/10.1016/j.cagd.2020.101881) | Mesh/control-point sensitivity and multi-frequency smooth shapes | Peer reviewed [P] |
| **S26** | [Khajah et al., SBFEM acoustic shape optimization (2021)](https://doi.org/10.1016/j.wavemoti.2021.102732) | Optimization demonstrated with 1–5 horn design variables | Peer reviewed [P] |
| **S27** | [Wadbro & Berggren, *Topology optimization of an acoustic horn* (2006)](https://doi.org/10.1016/j.cma.2006.05.005) | Optimal material topology can improve acoustics, distinct problem from surface param search | Peer reviewed [P] |
| **S28** | [Webster horn equation inverse problem (2012, open access)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3316681/) | Waveguide area-law dependence in 1-D, area not complete 3-D model | Peer reviewed [P] |
| **S29** | [ATH CORE published design and morph example (2026)](https://www.at-horns.eu/core.html) | Real OSSE azimuthal formulas, morph and BEM script; author warns extension affects specified source angle | Author primary [O] |
| **S30** | [FaitalPRO HF1440 official product data](https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185) | 35.8 mm diameter, radial phase plug, “Combined Exit,” 700 Hz specified crossover | Manufacturer [P] |
| **S31** | [Ahlswede, PETF applied to JMLC: simulation results (2021)](https://sphericalhorns.net/2021/05/22/petf-applied-to-jmlc-horns-simulation-results/) | JMLC loading vs HF beaming trade-off; numerical BEM examples; PETF alternatives | Original author simulations [O] |
| **S32** | [Geddes waveguide patent US7068805B2](https://patents.google.com/patent/US7068805B2/en) | Round-to-elliptical non-axisymmetric waveguide transitions and high-order mode caution | Primary patent [P] |

**Specific repo internal research:** [`JMLC_LECLEACH_RESEARCH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md), [`JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md), [`THROAT_COUPLING_2026-10-27.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/THROAT_COUPLING_2026-10-27.md), [`ATH_CORE_TWINRAY_MORPH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md), [`HORN_OPTIMIZATION_HARDENING_2026-11-12.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/HORN_OPTIMIZATION_HARDENING_2026-11-12.md), `docs/research/bo_study/*`, original user-uploaded v10 workbook.

### The principal caution to communicate to anyone implementing

This handoff provides **the best-defended public mathematical extension** based on the supplied 2018 calculator and Ahlswede's published explanations. It **does not** turn a 2019 photograph into a uniquely determined 3-D acoustic surface, does not claim to have recreated any unreleased stereographic/vector projection, and does not prove that a visually closer horn will measure better. Those three claims must come from **geometry parity against independently available reference coordinates and controlled BEM/measurement**, not from a plausible formula or a winning optimizer scalar score.
