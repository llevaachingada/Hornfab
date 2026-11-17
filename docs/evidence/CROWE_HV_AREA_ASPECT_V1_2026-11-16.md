# CROWE-inspired H/V area/aspect v1 — implementation and geometry evidence (2026-11-16)

Research: [`docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md`](../research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md).
This note records what was implemented, what was measured, and what remains unproven. **No BEM
solve, GPU job, CMA/BoTorch run or acoustic claim is in this note.**

> **Superseded for throat transition and parameter count by V2A (2026-11-16).** The 15-40 mm
> circular-hold rule recorded below is withdrawn by the
> [V2A addendum](../research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md).
> The current implementation exposes four search dimensions and fixes the hold at 0 (with a
> 20 mm A/B). The c0/c1 diagnostic configs were renamed to `c0_four_dof_seed.yaml` /
> `c1_four_dof_bounds.yaml`; the section-cut numbers below are historical V1 evidence. Current
> evidence: [`CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md`](CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md).

## What landed

- `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py` — versioned FREEFORM generator
  (`generator.name: crowe_hv_area_aspect_v1`, schema `crowe-hv-area-aspect-v1`). It materialises
  H/V meridians plus superellipse cross-section stations, so the existing mesher builds every
  surface. Historical `_crowe_section_v2.py`, the Crowe-X/OSS/rolled families, configs, runs and
  objectives are untouched.
- `hornlab_search/design/generated.py` — dispatch and provenance for the new generator; search-box
  validation at `GeneratedSpace` construction.
- `examples/typologies/crowe_hv_area_aspect_2026-11-16/` — `c0_round30_480.yaml` (fixed geometry
  diagnostic) and `c1_frontier_bounds.yaml` (proposed 8-knob box; owner-gated, not queued).
- `tools/geometry/crowe_hv_area_aspect_sections.py` — the owner's section-cut table.
- `tests/test_design_generators_crowe_hv_area_aspect.py` — 18 tests, including a real 8 kHz
  quarter mesh.

## Exact construction

For `u = z/L`:

```
A(0) = pi r0^2,   A(1) = C(p_mouth) (W/2) (H/2)
log A(u) = log A(0) + log(A(1)/A(0)) * [m0 u + (1 - m0) u^2]
m0 = (L * 2 tan(exit_angle) / r0) / log(A(1)/A(0)),   0 <= m0 <= 2
R(u) = a/b = exp(gate(u) * [log(W/H) + mid/late perturbations])
p(u) = 2 + (p_mouth - 2) * gate(u)
gate(u) = smootherstep((u - round_throat_mm/L) / (1 - round_throat_mm/L))
a = sqrt(A R / C(p)),   b = sqrt(A / (R C(p))),
C(p) = 4 Gamma(1 + 1/p)^2 / Gamma(1 + 2/p)
```

Consequences, each tested:

- `A = C(p) a b` and `R = a/b` at every station (relative error < 1e-13).
- Throat: `a = b = r0`, `A = pi r0^2`, `R = 1`, `p = 2`.
- Mouth: `a = W/2`, `b = H/2`, `A = C(p_mouth) (W/2) (H/2)`, `R = W/H`, `p = p_mouth`.
- `d a/dz(0) = d b/dz(0) = tan(exit_angle)`: the source tangent is the driver-exit tangent
  (the 2 deg value remains a simulation assumption, not an HF1440 datasheet claim).
- Inside `round_throat_mm`, `R = 1` and `p = 2` **exactly**, while `A(u)` keeps increasing.
- Rejected, never silently distorted: `m0 > 2` (no monotone member of this family), a mouth
  smaller than the throat, a non-monotone forward radius, a mouth/depth outside the brief
  envelope.

## Owner rules (2026-11-16) encoded in the first redesign

1. **First 15-40 mm almost circular.** `round_throat_mm` is a physical search knob (15-40 mm in
   `c1`, seed 30 mm). Inside it `a = b` and `p = 2` exactly; `max |aspect-1|`, `max |p-2|` and
   `max |a-b|` are all 0.0 in the measured cuts.
2. **Area can expand before shape gets boxy.** At the 30 mm gate the area is 1.173x the throat
   while the section is still exactly circular; 1.262x at 40 mm; 1.859x at 80 mm.
3. **Ridges cannot start early.** v1 contains no X crease/ridge at all. Even the superellipse
   boxiness is `p = 2.000720` at 40 mm and `p = 2.070759` at 80 mm. A Phase 2 ridge onset will be
   a separate 20-40 % knob, not this one.
4. **Near-throat section C2.** The aspect and exponent gates are smootherstep with zero first and
   second derivatives at the gate; position, tangent and curvature are continuous at
   `round_throat_mm` and at the mouth. The wall tangent at z=0 is the driver-exit tangent.

## Owner review stations (measured from the law, not a preview)

`tools/geometry/crowe_hv_area_aspect_sections.py --config .../c0_round30_480.yaml --stations 0,5,10,20,40,80,150,300`

| z (mm) | a (mm) | b (mm) | area (mm^2) | area/throat | aspect a/b | p | wall H (deg) | wall V (deg) | curvature H (1/mm) | curvature V (1/mm) | round |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 18.0000 | 18.0000 | 1017.876 | 1.000000 | 1.000000 | 2.000000 | 2.0000 | 2.0000 | 0.00093788 | 0.00093788 | yes |
| 5 | 18.1865 | 18.1865 | 1039.073 | 1.020824 | 1.000000 | 2.000000 | 2.2725 | 2.2725 | 0.00096462 | 0.00096462 | yes |
| 10 | 18.3971 | 18.3971 | 1063.281 | 1.044608 | 1.000000 | 2.000000 | 2.5535 | 2.5535 | 0.00099563 | 0.00099563 | yes |
| 20 | 18.8942 | 18.8942 | 1121.516 | 1.101820 | 1.000000 | 2.000000 | 3.1451 | 3.1451 | 0.00106951 | 0.00106951 | yes |
| 40 | 20.2202 | 20.2180 | 1284.499 | 1.261940 | 1.000105 | 2.000720 | 4.4758 | 4.4397 | 0.00125098 | 0.00112703 | no |
| 80 | 24.5101 | 24.2583 | 1892.526 | 1.859289 | 1.010380 | 2.070759 | 8.0261 | 7.1883 | 0.00193193 | 0.00137408 | no |
| 150 | 41.5796 | 38.1212 | 5413.132 | 5.318066 | 1.090723 | 2.595031 | 21.4092 | 16.8535 | 0.00480333 | 0.00375766 | no |
| 300 | 295.0000 | 237.0000 | 254202.607 | 249.738281 | 1.244726 | 3.500000 | 78.3639 | 75.6233 | 0.00077119 | 0.00115613 | no |

Reading: the section is exactly round through 30 mm; the area has grown 26 % by 40 mm while
`p` has moved only 0.0007; the boxiness/ridge region is genuinely late. The 300 mm seed's mouth
wall angle is 78 deg H / 76 deg V. That is a property of the chosen seed (a 590 x 474 mm mouth
at 300 mm depth with a 2 deg source tangent), **not** a claim that 78 deg is acoustically good.
The frontier study must trade it against depth/mouth/area.

## Real quarter mesh (CPU, offline)

`test_real_quarter_mesh_is_closed_and_round_at_the_driver` builds `c0` with the config's own screen
spec (`f_max 8000 Hz`, `epw 6`, quadrants `1`):

- 8,447 triangles; bbox `(0, 0, -0.003, 0.295, 0.237, 0.300)` m; tags `{1: 8391, 2: 56}`.
- `bad_open_edges = 0`, `nonmanifold_edges = 0`, `near_coincident = 0`.
- Driven coupling plane: 36.00 mm round, `fits_exit(36.0) = True`; mesh polygon roundness
  0.9936 (a triangle-fan discretisation of the exactly round law).

At a deliberately low 2 kHz test mesh the mesher warns about outer-wall chord density; at the
brief's 8 kHz band that warning does not appear. The acoustic (inner) surface is the same.

## Search-box preflight (law level only)

- All 18 bound endpoints of `c1` pass `validate_search_config`.
- 500/500 uniform random samples of the `c1` box materialise a lawful monotone surface.
- This is **not** the research document's 40-80 candidate mesh DOE; mesh validity across the box,
  the Jacobian/effective-rank check and the canonical GUI/CLI/CMA surface-hash comparison remain
  open.

## Not done / open gates

- No BEM, GPU, CMA-ES, BoTorch, queue or objective change. `c1` is not queued.
- Returned lip/roll, rim setback, X crease, `p_progress_start/rate`, throat-length source study and
  per-plane roll setback are Phase 2; no knob is registered for them.
- No catalog/`design/params` entry yet, so GUI parameter labels are generic for this diagnostic.
- Mesh validity across the whole `c1` box, the geometry Jacobian/effective rank, cold-worker
  mesh hashes across GUI/CLI/CMA, and every acoustic question remain open. The research
  document's go/no-go criteria still bind.
- The source tangent is the 2 deg driver-exit assumption; it is not an HF1440 datasheet value.
  A curvature jump at the driver/cone interface is inherent to starting a flared wall at a finite
  source tangent; the horn itself is C2 after the throat. A source-blend study is Phase 2.
