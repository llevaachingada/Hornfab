# Rectangular rolled-mouth family: construction study, 2026-11-15

Status: CPU geometry prototypes, acoustics unmeasured. Original construction inspired by the
Crowe ES-600/ES-450 appearance; **not a reconstruction of Crowe's proprietary ES equation**.
The optional puckered variant belongs to this experimental family, not to the published Tritonia model.
Owner brief remains the HF1440, 36 mm round exit, 700 Hz crossover, 80 H x 50 V target,
600 W x 480 H x 480 D envelope. These targets are not predictions of the geometry.

## Sources and what they establish

| Source | What it gives us | Status |
|---|---|---|
| [Crowe ES-600 introduction](https://josephcrowe.com/blogs/news/es-600-biradial-horn), also [original user reference](https://croweaudio.blogspot.com/2019/11/es-600-biradial-horn.html) | Section/front photographs, 417 x 203 x 198 mm, 1.4 inch throat, stated 270 degree wrap; says a design white paper was planned | primary (author, commercial); dimensions verified as published, acoustic interpretation author-reported |
| [Legacy ES-600 CAD listing](https://josephcrowe.com/products/es-600-bi-radial-horn-3d-cad-file) | Full and half CAD renders and dimensioned drawings; IGES/STL available commercially | primary (author, commercial) |
| [ES-600 No.1978](https://josephcrowe.com/products/es-600-bi-radial-wood-horn-no-1978) | Photos of finished/raw wood and revised mounting; 416 x 203 x 198 nominal dimensions | primary (author, commercial); separate revision |
| [ES-600 No.3150](https://josephcrowe.com/products/es-600-biradial-horn-no-3150-baffle-mount-version) | Baffle-mounted variant; 400 x 260 x 183, 9 degree H and 7 degree V throat half-angles | primary (author, commercial); not transferable specifications for legacy model |
| [Crowe circular baffle](https://josephcrowe.com/products/circular-baffle-for-fostex-fe108ez-drawing-plans), [actual linked white paper](https://cdn.shopify.com/s/files/1/0142/2848/8292/files/ES_Circular_Baffle_White_Paper.pdf?19=) | Describes progressively decreasing curve radius; white paper is comparative measurements, not ES construction math | primary (author); no disclosed ES equation found |
| [Batík OS-SE paper](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) | OS throat plus smooth termination and azimuth-dependent parameters/morphing | primary (author) |
| [Batík R-OSSE rev7](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) | Parametric folded contour, contrasted with single-valued OS-SE r(z) | primary (author); geometrical baseline, not Crowe construction |
| [Batík Tritonia design](https://at-horns.eu/tritonia.html) | Published azimuth-dependent OS-SE coverage/termination, followed by rectangle morph; enclosure dependence | primary (author); attribution reference, not a claim all ATH mouths share one law |
| [Keele patent US4308932A](https://patents.google.com/patent/US4308932A/en) | Distinct wall-pair/surface-of-revolution bi-radial construction and throat transition | primary (inventor); no evidence Crowe uses that construction |
| [Geddes waveguide chapter](https://www.gedlee.com/downloads/AT/Chapter_6.pdf), [What is a Waveguide](https://www.gedlee.com/Papers/What%20is%20a%20Waveguide.pdf) | Mouth diffraction, wavefront/mode concerns; area-only horn equations do not determine full directivity | primary (author); physical context |

The Blogspot reference returned HTTP 429. Its migrated author article was readable.
The existing local study set comprises 28 photographs, CAD renders, sections and drawings in
`scratch/crowe_ref/` (copyrighted references, local only). The contact sheet was inspected along
with enlarged ES-600 section/front and ES-450 front, half-section and drawing views. The
ES-450 drawing shows **542 W x 299 H x 238 D**, with 337 including the illustrated driver.
Driver/mounting details from that model do not transfer to the HF1440.

## Corrections to the previous handoff

| Previous assumption | Correction and consequence |
|---|---|
| ES means an exponential area law | Not established. A spiral wall curve is not the Webster area law A=A0 exp(mx). Hypex T=1 does not reproduce ES. |
| The X should be made by pushing the mouth corners into a star | Front/section images instead show a nearly rectangular perimeter, broad upper/lower panels and narrower side panels; much of the X is an interior transition/highlight. Do not confuse projected seams with silhouette. |
| Every CAD edge is an acoustic crease | Some lines are CAD patch boundaries, half-body seams or tangent-edge displays. Photos cannot establish a tangent discontinuity. Use smooth junctions unless curvature data establish otherwise. |
| sf_ab independently controls aspect, n2 independently controls straightness | Current superformula couples ab, n1 and n2; its diagonal maximum shifts. Those labels were unjustified. |
| s=0 produces a straight cone | OSSE remains a hyperbolic OS profile; it can look nearly conical away from the throat. |
| A C1 circular meridian lip proves a smooth 3-D roll | It proves only matching row tangent. Curvature and azimuthal joins need separate checks. Current base wrap is capped at 200 degrees; its wrap and Crowe's stated 270 degrees have no verified common angle convention. |
| The rectangular typology already guarantees diagonal creases | Its circle-to-rectangle interpolation does not explicitly construct shared wall-pair intersection curves. Inspect its actual surface. |
| The golden ratio determines W/H | Legacy published W/H is 417/203=2.054; ES-450 drawing is 542/299=1.813. Do not force 1.618. |
| A 700 Hz crossover proves 80 x 50 control there | Loading, crossover capability and pattern control are distinct. The seed is unmeasured. |
| Night C is stopped | A live controller was found waiting behind B, despite the last log line saying stopped. No queue edits/launches are authorized by this geometry task. |

## Original, testable construction (before implementation)

Use the existing point-grid mesh adapter; no mesher, solver or gmsh writer is added. The experiment
lives under `tools/geometry/`, outside the `hornlab_search/**/*.py` files pinned by the active studies.
Its YAML shape description is deliberately a **prototype schema**, not a new production config key.
An unchanged existing production config supplies mesh resolution and brief only. Original surface:

1. Define a dimensionless shrinking-curvature reference contour by tangent parameter t:
   `dz/dt = exp(-b*t) cos(t)`, `du/dt = exp(-b*t) sin(t)`, b > 0.
   Thus `z=(exp(-bt)(-b cos t + sin t)+b)/(1+b^2)` and
   `u=(exp(-bt)(-b sin t - cos t)+1)/(1+b^2)`.
   This is our logarithmic-spiral analogue, **not Crowe's equation**. Normalize z at pi/2
   to the selected depth and u at pi to unit radial expansion. Scale choices mean the
   finished anisotropic surface is not itself an exact logarithmic spiral in every section.
2. Independent half-width/height evolve as `r0 + F(t)*(R_axis-r0)` with F=u/u(pi).
   Add a short, isotropic throat-slope correction `tan(a0)*z*(1-S(t/t_throat))`.
   S is clamped quintic smoothstep; this protects an exactly round throat and matching
   first derivative without imposing Crowe's driver-dependent throat angles.
3. Cross-sections obey `(abs(x)/h(t))^p(t)+(abs(y)/v(t))^p(t)=1`.
   Increase p smoothly from 2 to the selected rectangular exponent. This separates
   aspect ratio, corner rounding and profile progress rather than using one star formula.
   A high finite p forms smooth corner transitions, not mathematically sharp creases.
4. Continue the same contour through its axial maximum (t=pi/2) and radial maximum
   (t=pi) toward the selected terminal parameter (initially 270 degrees). This supplies
   a real return around the edge rather than a flat flange or short circular attachment.
   The terminal parameter is **our reference-contour parameter**, not a verified
   interpretation of Crowe's advertised wrap angle or final 3-D wall tangent.
5. Optional original puckering: add `A*W(t)*cos(4*psi)` to z, where
   `psi=atan2(y/v,x/h)` and W is a quintic window beginning after the selected turn.
   Positive A advances the centres of the four walls relative to their diagonal junctions.
   This leaves x/y unchanged and cannot produce a star silhouette. Zero A is the base
   family exactly. It is an ATH-influenced experiment, not Batík's Tritonia formula.

Reference case for independent checks, b=0.7 (unit scale):

| t degrees | z | u |
|---:|---:|---:|
| 0 | 0 | 0 |
| 90 | 0.6933009634040033 | 0.5146893256171977 |
| 180 | 0.5218999294328434 | 0.7455713277612048 |
| 270 | 0.4450119663002113 | 0.6884916235898522 |

For a 238 mm reference depth, z is 238, 179.16055, 152.76605 at the last three rows.
These numbers validate our formula, not the proprietary product. Tests compare analytical
integrals against independent numerical quadrature, throat coupling/tangent, dimension controls,
zero-pucker identity and shape convergence. The assembled mesh must pass existing topology,
envelope and source-tag checks; shell thickness uses the existing meridian-offset approximation,
not a claim of constant normal thickness in 3-D or a print-ready structural design.

## Parameters, starting ranges and honest acceptance

| Prototype control | Initial range | Purpose |
|---|---:|---|
| Maximum inner W / H | 520-570 / 280-320 mm | Landscape proportions, independent of target coverage |
| Reference depth | 220-270 mm | Gradual throat-to-bell development |
| H / V depth ratio | seed 0.68; initially fixed | Side walls develop less far forward than broad upper/lower panels; visual inference, not recovered ES dimensions |
| Curvature decay b | 0.55-0.85 | Distribution of growth/return, not acoustic cutoff |
| Rectangular exponent | 8-16 | Straighter wall edges with rounded transitions; inspect corner resolution |
| Rectangular transition end | 50-85 reference degrees | Where separate wall panels become apparent |
| Terminal contour parameter | 240-275 degrees | Return depth and open-shell clearance |
| Pucker amplitude | H 0/12/24, V 0/16/28 mm | Matched geometry arms; base typology fixed at zero |
| Pucker window start | 35-75 reference degrees | Preserve throat; place relief in main bell/mouth |

These are geometry ranges, not acoustic recommendations. The owner explicitly authorized queueing
the close visual seed and short pucker comparisons in this chat, after geometry checks. Target <= about 6k
screen DOFs; count actual nodes rather than inflating the cap to force acceptance. Screen
mesh density is not a substitute for converged corner/lip geometry.

Expected strengths [inferred]: separates outline, corner transitions, depth and roll; clean
round coupling; gradual folded mouth; optional pucker without star lobes. Weaknesses [unverified]:
no established CD/load behaviour, original cross-section blend, meridian-offset shell approximation,
possible corner under-resolution, and potential pucker-induced modes. More roll is not automatically
better sound. Designer testimony about low coloration is not independent validation.

Acoustic acceptance later: H/V and diagonal polars, -6 dB coverage versus frequency, balloon DI,
normalized impedance/loading around crossover, on-axis/off-axis ripple with DSP distinguished
from raw response, and comparison at common fidelity against incumbent families. Include the
actual freestanding shell/mounting and HF1440 source assumptions. Printed mounting, bolt pattern,
wall strength and distortion remain separate engineering checks.

## Implemented refinement and results

The first homothetic prototype shared the same forward development at all azimuths and still
looked too much like a flat rim. Inspection of the half-section and multiple ES-450 views
motivated an independent H/V depth ratio. This is a **visual inference**, not a digitized
measurement of Crowe's surface. Let `psi=atan2(y/v,x/h)`; multiply the reference z by
`1+(depth_h_ratio-1)*cos(psi)^2*S(t/t_rect)` before adding pucker. The throat derivative is
unchanged. With depth_h_ratio=0.68, upper/lower wall centres develop further forward than
side-wall centres, producing a much more pronounced eye-shaped interior and waisted side view.
The front x/y outline remains convex and rectangular. A normal-view photograph does not
uniquely determine this axial law; it remains an original hypothesis for the acoustic pilot.

The production-compatible experiment uses `generator.name: grid`, distinct rows types
`rolled_rect` and `rolled_rect_pucker`, and the opt-in entry point
`tools/geometry/rolled_rect_cli.py`. It delegates to existing CMA, evaluation, meshing and BEM.
All custom dispatch hooks are confined to that process. The stock entry point **rejects** these
recipes; it cannot silently replay a different shape. Every persisted design includes the
implementation digest and throat dimensions. Search, shape check and verification all use the
same wrapper. No file under `hornlab_search/` was changed, so prior study execution pins remain intact.

CPU seed checks, final depth-split geometry:

```text
| rr__pucker_hv_moderate_v7 | yes | 4465 / 6000 | 542 x 299 | 244 | fits | round, matches the exit |  |
| rr__pucker_hv_strong_v7 | yes | 4459 / 6000 | 542 x 299 | 246 | fits | round, matches the exit |  |
| rr__reference_v7 | yes | 4499 / 6000 | 542 x 299 | 241 | fits | round, matches the exit |  |
```

Each arm's uniform search-box preflight meshed 64/64 valid samples with zero refusals, hard
findings or warnings. This is CPU feasibility evidence, not acoustic evidence. Local raw logs:
`scratch/2026-11-15_rolled_rect/final-preflight-{reference,moderate,strong}.json`.
Focused geometry/grid/verification regression run: `72 passed in 21.67s`.
The full offline suite is recorded separately; the concurrent GPU lane was left running.

The initial publication gallery includes all three seeds from five camera angles. The local
side-by-side source comparison stays in scratch; public assets contain only our own renders.
See [the queue plan](../../queue/ROLLED_RECT_PLAN_2026-11-15.md).
