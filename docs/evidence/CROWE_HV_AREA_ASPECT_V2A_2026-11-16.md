# CROWE-inspired H/V area/aspect v1 — V2A parameter hardening evidence (2026-11-16)

Research: [`docs/research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md`](../research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md)
(companion to the [V2 senior research](../research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md)).
This note records the V2A implementation, its measured geometry, and what remains unproven.
**No BEM solve, GPU job, CMA/BoTorch run or acoustic claim is in this note.**

## What the V2A addendum changed

- **Four search dimensions only:** `height_v_active_mm`, `L_forward_mm`, `area_mid_bias`,
  `aspect_timing_u50`. The prior area-early/late, aspect-mid/late, p-progress and round-hold
  knobs are gone from the search surface.
- **Fixed generator-block values:** `width_h_active_mm` 580 mm, `p_mouth` 3.25, and
  `throat_round_hold_mm` 0 (the ATH CORE-style smooth throat start). `p_mouth` and the hold are
  paired discrete A/B configs, not continuous dimensions.
- **The 15-40 mm circular-hold rule is withdrawn.** The section is kept round near the throat by
  the timing law itself, not by a mandated corridor. A fixed 20 mm expanding-circular hold exists
  only as the T2 A/B.
- **One timing coordinate:** `S_R(u)` is a warped-quintic C2 step with an exact half point
  `u50`, zero first/second derivatives at u=0 and u=1, and `log R = log(W/H) S_R`,
  `p = 2 + (p_mouth-2) S_R`.
- **One area bias:** `area_mid_bias` (log-area, normalized -0.15..+0.15) uses a C3 compact window
  that is exactly zero at both ends, so the mouth area and the source tangent are preserved.

## Exact construction

```
A(0) = pi r0^2,   A(1) = C(p_mouth) (W/2) (H/2)
log A(u) = log A(0) + log(A(1)/A(0)) [m0 u + (1-m0) u^2] + area_mid_bias B_A(u)
m0 = (L 2 tan(exit_angle) / r0) / log(A(1)/A(0)),   0 <= m0 <= 2
q = u50 / (1 - u50)
w(u) = u / (u + q (1-u))
S_R(u) = smootherstep(w(u))
log R(u) = log(W/H) S_R(u),   p(u) = 2 + (p_mouth-2) S_R(u)
a = sqrt(A R / C(p)),   b = sqrt(A / (R C(p))),
C(p) = 4 Gamma(1+1/p)^2 / Gamma(1+2/p)
```

At `u=0`: `a=b=r0`, `A=pi r0^2`, `R=1`, `p=2`, and `a'(0)=b'(0)=tan(exit_angle)` because
`S_R'(0)=p'(0)=0` and `B_A'(0)=0`. At `u=1`: `a=W/2`, `b=H/2`, `A=C(p_mouth)(W/2)(H/2)`,
`R=W/H`, `p=p_mouth`. The identity `A=C(p)ab`, `R=a/b` holds at every station (relative error
< 1e-13). `m0 > 2` is refused; it has no monotone member of this family.

### Correction: endpoint derivatives of the timing law (2026-11-16)

The first implementation used `S_R(u) = smootherstep(u/a) / smootherstep(1/a)`, solving `a` for
`S_R(u50)=0.5`. That does **not** put the mouth argument at 1 unless `u50=0.5`: at `u50=0.65` the
dimensionless first derivative at the mouth was about 1.087, not zero. The rolled-lip junction would
then inherit an unintended aspect/section slope. The implementation now uses the warped quintic
above. `timing_derivatives()` returns `(S, dS/du, d2S/du2)` analytically, and the tests check:

| u50 | S(0), S(1) | S'(0), S'(1) | S''(0), S''(1) | S(u50) |
|---|---|---|---|---|
| 0.35 | 0, 1 | 0, 0 | 0, 0 | 0.5 |
| 0.50 | 0, 1 | 0, 0 | 0, 0 | 0.5 |
| 0.65 | 0, 1 | 0, 0 | 0, 0 | 0.5 |
| 20 mm hold, raw 0.464286 | 0, 1 | 0, 0 | 0, 0 | 0.5 |

The fixed 20 mm hold shifts the raw half point to `(u50-h)/(1-h)` and keeps the same zero endpoint
derivatives; the physical half-development point remains `u50`.

## Measured section cuts, c0 (hold 0, u50 0.5, p 3.25)

`tools/geometry/crowe_hv_area_aspect_sections.py --config .../c0_four_dof_seed.yaml`

| z (mm) | a (mm) | b (mm) | area (mm^2) | area/throat | aspect a/b | p | gate | wall H (deg) | wall V (deg) | curvature H (1/mm) | curvature V (1/mm) | hold |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 18.0000 | 18.0000 | 1017.876 | 1.000000 | 1.000000 | 2.000000 | 0.000000 | 2.0000 | 2.0000 | 0.00093180 | 0.00093092 | yes |
| 5 | 18.1864 | 18.1862 | 1039.064 | 1.020816 | 1.000009 | 2.000056 | 0.000045 | 2.2702 | 2.2646 | 0.00095461 | 0.00091551 | no |
| 10 | 18.3967 | 18.3953 | 1063.246 | 1.044573 | 1.000071 | 2.000440 | 0.000352 | 2.5478 | 2.5255 | 0.00098181 | 0.00090572 | no |
| 20 | 18.8919 | 18.8817 | 1121.367 | 1.101673 | 1.000540 | 2.003343 | 0.002675 | 3.1294 | 3.0434 | 0.00104908 | 0.00090396 | no |
| 40 | 20.2081 | 20.1299 | 1283.814 | 1.261268 | 1.003886 | 2.024020 | 0.019216 | 4.4385 | 4.1123 | 0.00124610 | 0.00097522 | no |
| 60 | 22.0311 | 21.7751 | 1527.419 | 1.500594 | 1.011758 | 2.072400 | 0.057920 | 6.0360 | 5.3280 | 0.00155061 | 0.00115977 | no |
| 100 | 27.7750 | 26.6231 | 2426.471 | 2.383857 | 1.043267 | 2.262346 | 0.209877 | 10.7049 | 8.7921 | 0.00258155 | 0.00193826 | no |

First 20 mm: max `|aspect-1|` = 5.40e-4, max `|p-2|` = 3.34e-3. The area is already 1.10x at
20 mm and 1.26x at 40 mm while the section is still nearly round. This is the V2A answer to the
"round -> square too quickly" concern: the timing law starts smoothly at the throat, area expands
first, and boxiness is late (p 2.024 at 40 mm, 2.26 at 100 mm).

## Fixed 20 mm expanding-circular hold A/B (c2, not a knob)

| z (mm) | area/throat | aspect | p | gate | hold |
|---:|---:|---:|---:|---:|:---:|
| 0 | 1.000000 | 1.000000 | 2.000000 | 0.000000 | yes |
| 5 | 1.020816 | 1.000000 | 2.000000 | 0.000000 | yes |
| 10 | 1.044573 | 1.000000 | 2.000000 | 0.000000 | yes |
| 20 | 1.101673 | 1.000000 | 2.000000 | 0.000000 | yes |
| 40 | 1.261268 | 1.000965 | 2.005971 | 0.004777 | no |
| 60 | 1.500594 | 1.006573 | 2.040578 | 0.032463 | no |

The hold is an *expanding circular* corridor (the section radius still follows the area law), not
a constant-radius tube, and the gate is C2 at the 20 mm boundary. This is a controlled T2 A/B;
`throat_round_hold_mm` is never a search dimension.

## T2 identifiability (law level; 3 parents, +-10 % normalized box)

`tools/geometry/crowe_hv_area_aspect_jacobian.py --config .../c1_four_dof_bounds.yaml`

| parent | singular values | practical rank | weak keys | max abs cosine |
|---|---|---:|---|---:|
| seed | 0.821817, 0.496182, 0.418236, 0.330589 | 4 | none | 0.610025 |
| low quarter | 1.176394, 0.957112, 0.558297, 0.359409 | 4 | none | 0.565004 |
| high three-quarter | 0.909247, 0.792746, 0.497523, 0.314488 | 4 | none | 0.639860 |

This is a **law-level** Jacobian of area/aspect/p/wall-angle/curvature/mouth/timing descriptors,
not the full vertex-displacement mesh Jacobian. It supports keeping four variables at this stage;
it does not prove acoustic independence or that four is optimal.

## Real quarter mesh (CPU, offline)

`test_real_quarter_mesh_is_closed_and_round_at_the_driver` builds c0 with the config's own
screen spec (`f_max 8000 Hz`, `epw 6`, quadrants `1`):

- 8,318 triangles; tags `{1: 8262, 2: 56}`.
- `bad_open_edges = 0`, `nonmanifold_edges = 0`.
- Driven coupling plane: 36.000 x 36.000 mm, `fits_exit(36.0) = True`.

## T0 screenshot audit: what is and is not established

The addendum's source finding is confirmed in-repo: `gui/static/view3d.js`, `buildRidgeGeometry`,
is a **rendering overlay**. It welds close vertices, evaluates paired-triangle dihedrals and draws
near-white lines; the GUI `ridges` dropdown does not change the solver mesh or create physical
X-ridge geometry. The screenshot's exact design ID, config, saved `.msh`, mesh hash and shape
payload were **not supplied**, so the ridge-on/off/true-wireframe comparison and the physical
source-cap/section audit remain **open**. No geometry was changed to hide a display line.

## Not done / open gates

- No BEM, GPU, CMA-ES, BoTorch, queue or objective change. c0-c3 are not queued.
- No 40-80 candidate CPU mesh DOE; only the 100-sample law-level admission check (>=90 valid) and
  the single 8 kHz mesh above. The addendum's T2/T3/T4 remain gated.
- X crease, returned lip, rim setback, independent area-late / aspect-mid-late and a throat-angle
  search are not implemented. No knob is registered without an implemented effect.
- No catalog/`design/params` entry; GUI parameter labels remain generic for this diagnostic.
- The `a0=2 deg` source tangent is the existing simulation assumption, not an HF1440 datasheet
  value. A driver-informed source study needs new provenance and, later, new solves.
- The full-band acoustic ablation (no-X vs X, hold 0 vs 20 mm, p 2.2 vs 3.25, roll on/off) is the
  addendum's T3/T4 and is not authorised by the research documents.

## Reproduce

```powershell
.venv\Scripts\python.exe -m pytest tests\test_design_generators_crowe_hv_area_aspect.py -q
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_sections.py `
  --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c0_four_dof_seed.yaml
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_jacobian.py `
  --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c1_four_dof_bounds.yaml
```
