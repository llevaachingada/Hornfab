# Spiral pucker vs ATH-style radial ridges — 2026-11-15

Contact sheet for the 2026-11-15 research note
[`docs/research/typologies/SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15.md`](../../research/typologies/SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15.md).

`pucker_compare.png` (2 × 3, straight-on front views, same grey material/renderer):

| Cell | Geometry | What it shows |
|---|---|---|
| top-left | `hl__rolled_es_spiral_v7` seed | Axial pucker H 6 / V 8: horizontal/vertical faces forward, diagonal valley, slightly wavy rim |
| top-right | `hl__crowe_x_osse_cd_v7` seed | Superformula X + 130° rolled lip; closest saved cell to the owner screenshot |
| middle-left | `hl__ath_core_petal_hvlaw_v7` seed | ATH CORE-style per-direction law, 80 × 50 landscape compromise |
| middle-right | `rf__rect_radial_wide_v7` seed | Same spiral base, radial inward H 12 / V 16: diagonal ridges, triangular facets, clean lip |
| bottom-left | scratch signed radial 16 / 22 mm outward | H/V faces bulge, diagonal valley (the current bow-out look, in-plane) |
| bottom-right | `rf__rect_control_v7` | Same spiral base, no relief |

`relief_versions.png` — straight-on front-view progression on the same spiral base:

| Suggested start | H / V inward | What to expect |
|---|---:|---|
| subtle | 3 / 4 mm | slight diagonal ridge, close to the control |
| medium | 6 / 8 mm | clear ridge, still gentle |
| clear (new seed) | 12 / 16 mm | strong triangular facets, visible inner waist |
| dramatic | 16 / 22 mm | deep facets, pronounced waist; use with care |
| outward | -16 / -22 mm | H/V faces bulge, diagonal valley (the opposite experiment) |

The search bounds in `rf__rect_radial_wide_v7.yaml` are **0–30 mm H / 0–40 mm V**; the generator caps both at 15% of the mouth height (44.85 mm). The relief window is **0.50 / 0.80 / 0.96**; keep the end at or below 0.96 so the returned lip stays clean.

`rf__rect_radial_wide_v7_card.png` — front 3/4, straight-on front and side of the new seed.

`strong_a_vs_canonical.png` — legacy `sp__strong_v7` (`strong_a.png`) versus canonical `rf__section_axial_strong_v7`; identical within 9.6e-7 mm point difference.

`rf__section_axial_strong_card.png` — front 3/4, straight-on front and side of the exact `strong_a` visual reference.

`rf__section_axial_home_card.png` — the home-scaled optimization cell `rf__section_axial_home_v7` (580 × 290 × 274 mm, 3,988 DOF): size/depth/H-V depth split/crown/junction searched; axial pucker 7/9 as a secondary rim lever. The fixed 417 × 203 `rf__section_axial_strong_v7` is the visual reference, not the optimization cell.

**Section pucker is a parameter, not a typology:** `rf__section_axial_strong_v7` is the canonical `rolled_family_section_v1` cell with `g_axial_h_mm=7`, `g_axial_v_mm=9`, window `0.30/0.80/0.96`. The legacy `sp__strong_v7` bridge cell is kept as historical evidence but removed from the GUI typology list.

**GUI exposure:** open `#/typology/rf__rect_radial_wide_v7` (or pick it in the typology list under group `home`). The sandbox header prints the suggested starts. The typology is listed in `examples/catalog.gui.yaml` as `rf__rect_radial_wide_v7` (group `home`, `hv`, enabled). The parameter catalog was regenerated with `tools/gen_param_catalog.py --write`, so the sandbox shows the inward H/V, axial H/V and relief-window knobs with their documented ranges. The sandbox preview path was also fixed to resolve `rolled_family` through its canonical `resolve_grid`; `preview_shape(..., {"detail": ["3d"]})` now returns `available: true`, `shape3d.available: true`, dims **535.7 × 294.7 × 235.1 mm**. Hard-refresh the GUI and restart the server (the preview fix is Python code) to pick everything up.

Source renders are scratch artifacts:

- `scratch/render_current/spiral_c.png`
- `scratch/render_crowex/views/crowex_c.png`
- `scratch/render_petal/views/petal_c.png`
- `scratch/render_signed/wide/views/wide_c.png`
- `scratch/render_signed/views/outward_c.png`
- `scratch/render_relief/views/control_c.png`

Regenerate the shapes with `tools/shape_check.py --save-mesh` and render with
`%LOCALAPPDATA%\hornlab\vizenv\Scripts\python.exe tools/render/render_views.py`.
No GPU solve was run; these are shape-only images. The new
`rf__rect_radial_wide_v7.yaml` is uncommitted.
