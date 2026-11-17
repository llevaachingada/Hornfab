# CROWE-inspired H/V area/aspect family (v1, V2A four-DOF)

Research: [V2 senior research](../../../docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md)
and the [V2A throat-transition / parameter-hardening addendum](../../../docs/research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md)
(the addendum supersedes V2 on throat transition and parameter count).
Evidence: [`docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md`](../../../docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md).
Implementation: `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py`.

## V2A contract

Exactly **four** continuous search dimensions:

- `height_v_active_mm`
- `L_forward_mm`
- `area_mid_bias` (log-area, normalized -0.15..+0.15)
- `aspect_timing_u50` (physical fraction where half the H/V aspect development has happened)

Fixed generator-block values, **not** search dimensions:

- `width_h_active_mm` 580 mm (held for the vertical-control study)
- `p_mouth` 3.25 (paired A/B config for 2.2)
- `throat_round_hold_mm` 0 (fixed expanding-circular A/B config for 20 mm)

The earlier 15-40 mm circular-hold rule is **withdrawn**. The section is kept round near the throat
by the timing law itself: `S_R(u)` is a normalized C2 smootherstep with an exact half point `u50`
and zero first/second derivatives at both ends. `log R = log(W/H) S_R`,
`p = 2 + (p_mouth-2) S_R`. `area_mid_bias` uses a C3 window that is exactly zero at both ends, so
the source tangent and mouth area are preserved. `A = C(p) a b` and `R = a/b` hold exactly at every
station. No X crease, returned lip or rim setback exists in v1.

## Configs

| Config | What it is |
|---|---|
| `configs/c0_four_dof_seed.yaml` | Geometry-diagnostic seed: 580 x 474 mm mouth, 300 mm forward length, hold 0, p 3.25, all four bounds fixed. Not queued. |
| `configs/c1_four_dof_bounds.yaml` | The proposed four-variable Phase-1 box. **Owner-gated; not queued; no solve authorised.** |
| `configs/c2_round20_ab.yaml` | Fixed 20 mm expanding-circular hold A/B (T2); same four coordinates, not a search. |
| `configs/c3_p22_ab.yaml` | Paired `p_mouth` 2.2 vs 3.25 A/B; same four coordinates, not a search. |

## Section cuts

The V2A review stations are 0/5/10/20/40/60/100 mm. Produce the measured table with:

```powershell
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_sections.py `
  --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c0_four_dof_seed.yaml
```

Add `--json` for the machine-readable form or `--stations 0,5,10,20,40,60,100,300` for another set.
The tool reads the same law the search materialises; it is a geometry measurement, not a mesh or
acoustic result.

## T2 identifiability

```powershell
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_jacobian.py `
  --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c1_four_dof_bounds.yaml
```

At the seed and two other bounded parents, the normalized +-10 % box Jacobian has practical rank
**4** with no weak variables and max pairwise |cosine| 0.63. This is a law-level descriptor
Jacobian, not a full vertex/mesh or acoustic Jacobian.

## Current measured facts (2026-11-16, CPU only)

- c0 near-throat: at 20 mm the area is 1.102x the throat while `|aspect-1| = 5.4e-4` and
  `|p-2| = 3.3e-3`; at 40 mm the area is 1.261x and `p = 2.024`; at 100 mm `p = 2.262`.
- c2 (fixed 20 mm hold): exactly circular through 20 mm, area 1.102x, gate C2 at the boundary.
- Real 8 kHz quarter mesh of c0: 8,318 triangles, `bad_open_edges = 0`, non-manifold 0, driven
  plane 36.000 x 36.000 mm (`fits_exit(36) = True`).
- No BEM, GPU, CMA/BoTorch, queue or objective change. c0-c3 are not queued.
