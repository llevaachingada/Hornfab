# CROWE-inspired H/V area/aspect family (v1, forward flare only)

Research: [`docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md`](../../../docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md).
Evidence: [`docs/evidence/CROWE_HV_AREA_ASPECT_V1_2026-11-16.md`](../../../docs/evidence/CROWE_HV_AREA_ASPECT_V1_2026-11-16.md).
Implementation: `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py`.

This family separates the enclosed superellipse area law from the H/V aspect law:

- `A(u)` is a monotone log-area law fixed by the throat area, the mouth `W x H` area and the
  driver-exit tangent. `log A(u)` is the unique quadratic with that initial slope.
- `R(u) = a/b` is exactly 1 for the first `round_throat_mm` and then develops through a C2
  smootherstep. The superellipse exponent `p(u)` is exactly 2 over the same round length and then
  develops to `p_mouth`.
- At every station `A = C(p) a b` and `R = a/b` hold exactly by construction.
- No returned lip, rim setback or X crease exists in v1; those are Phase 2 and no knob is
  registered for them.

## Configs

| Config | What it is |
|---|---|
| `configs/c0_round30_480.yaml` | Geometry diagnostic seed: 590 x 474 mm mouth, 300 mm forward length, `round_throat_mm` 30, all bounds fixed. Not queued. |
| `configs/c1_frontier_bounds.yaml` | The proposed 8-knob Phase 1 search box (round throat 15-40 mm). **Owner-gated; not queued; no solve authorised.** |

## Section cuts

The owner review stations are 0, 5, 10, 20, 40 and 80 mm. Produce the measured table with:

```powershell
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_sections.py `
  --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c0_round30_480.yaml
```

Add `--json` for the machine-readable form or `--stations 0,5,10,20,40,80,150,300` for a
different set. The tool reads the same law the search materialises; it is a geometry measurement,
not a mesh or acoustic result.

## Rules encoded in the first redesign (owner, 2026-11-16)

1. The first 15-40 mm stays circular: `a = b` and `p = 2` exactly up to `round_throat_mm`
   (seed 30 mm, search 15-40 mm).
2. Area expands before the section becomes boxy: at 30 mm the area is 1.17x the throat while the
   section is still exactly circular; it is 1.26x at 40 mm and 1.86x at 80 mm.
3. No ridge starts early: v1 has no X crease, and even the superellipse boxiness is 2.0007 at
   40 mm and 2.07 at 80 mm. A Phase 2 ridge onset will be a separate 20-40 % knob.
4. The near-throat section is C2 at the gate: the aspect and exponent gates use smootherstep, so
   position, tangent and curvature are continuous at `round_throat_mm` and at the mouth.
