# Klangfilm-Lame H/V throat core — Phase A geometry diagnostics (2026-11-16)

Geometry-only hypotheses for the Phase A `klangfilm_lame_hv_cd` kernel
(`tools/geometry/klangfilm_lame_hv.py`, schema `klangfilm-lame-hv-v1`). **These are not acoustic
winners and carry no readiness or queue claim.** No BEM, GPU, mesh, shell, curvature or acoustic
validation was run to produce them.

The kernel imports the stable legacy `tools/geometry/klangfilm_lame.py` read-only as its parent. Each
config is an 8-basin geometry probe over one parent design (the canonical incumbent from
`runs/20261116T205942Z-screen-8b22b5/best.json`), with every bound fixed (`search: false`). H and V
are **true wall half-angles** measured from the axis, not beamwidth halves.

- Configs: `configs/a0.yaml` … `configs/a5.yaml` (fixed geometry diagnostics) and
  `configs/stage_a_search.yaml` (four searched knobs; measured-lawful box).
- Preflight: `tools/geometry/klangfilm_hv_preflight.py` →
  `docs/evidence/klangfilm_hv_2026-11-16/PREFLIGHT.md` + `preflight.json`.
- Search-box lawfulness: `tools/geometry/klangfilm_hv_search_box.py` →
  `docs/evidence/klangfilm_hv_2026-11-16/SEARCH_BOX.md` + `search_box.json` (200/200 LHS samples and
  16/16 box corners lawful; no solve).
- Contact sheet: `tools/geometry/klangfilm_hv_contact_sheet.py` →
  `docs/evidence/klangfilm_hv_2026-11-16/contact_sheet_*.png`, `sections_hv.png`,
  `throat_zoom.png`, `sheet_metadata.json`.

## Seeds

Canonical parent genes (all seeds except a5): `fc_hz=494.4393461867`, `aspect=2.0759495982`,
`lame_p=5.0063549541`, `end_frac=1.7953432921`, `rim_sweep_ratio=0.004898754`, `morph_frac=0.3`,
`source_blend_ratio=0.0`, `entry_half_angle_deg=2.0`.

| seed | parent genes | θ_H / θ_V (deg) | h / v mid gain (mm) | join | purpose | expected status |
|---|---|---|---|---|---|---|
| a0 | canonical | 9.4 / 9.4 | 0 / 0 | 0.65 | exact incumbent control; blend 0 makes every Phase A key inert, so the grid must equal legacy | accepted (legacy bit-exact) |
| a1 | canonical | 10 / 5 | 0 / 0 | 0.65 | moderate biaxial entrance: independent H/V throat tangents | accepted |
| a2 | canonical | 14 / 5 | 0 / 0 | 0.65 | strong H opening with a tight V | accepted |
| a3 | canonical | 9 / 6 | +18 / −8 | 0.75 | as-specified "gentle throat, spread mid" | **rejected** — negative V mid gain constricts below the 18 mm throat |
| a3b | canonical | 9 / 6 | +18 / 0 | 0.75 | feasible respec: positive H mid spread + independent V throat angle | accepted |
| a4 | canonical | 9 / 4 | +8 / −14 | 0.65 | as-specified "V-tight interior" stress | **rejected** — negative V mid gain constricts below the 18 mm throat |
| a4b | canonical | 9 / 4 | +8 / 0 | 0.65 | feasible respec: steep independent V throat angle + modest positive H mid spread | accepted |
| a5 | fc 400, aspect 1.65, p 4.0, end 1.20, rim 0.10, morph 0.3, source_blend 0, entry 2.0 | 11 / 6 | +12 / +6 | 0.65 | different mouth aspect; does the entrance deformation travel across parent genes? | accepted, **OVER ENVELOPE** (622.6 mm inner width > 600) |

## What the expected refusals mean

`a3` and `a4` are kept exactly as specified and are **expected to be refused** by the kernel's
no-constriction invariant, not silently clamped. A negative `g_*_mid_gain_mm` makes the B2 basis
locally dominate the wall slope (B2′ scales as 1/L per mm of gain), so the forward V radius stops
being non-decreasing and can fall below the 18 mm throat. The feasible variants `a3b`/`a4b` replace
**only** that impossible negative gain with `0.0`; they keep the same throat angles, the positive H
mid spread and the join fraction. The negative-V "V-tight interior" idea is recorded as Phase B
motivation, not as a kernel bug.

Actual statuses, exact kernel exception text, sampled envelope estimates and convergence numbers are
computed by the preflight; read `docs/evidence/klangfilm_hv_2026-11-16/PREFLIGHT.md` — do not treat
this table as a substitute.

## Two things to read correctly in the renders

**a5 is over the production envelope and says so.** Its inner surface is 622.6 x 377.3 x 256.0 mm and the
sampled conservative outer estimate is 628.6 x 383.3 x 259.0 mm against 600 x 480 x 480 mm. Its config
carries the family's versioned `size_policy: report_only`, so the geometry materialises and
`meta.envelope_violations` / `meta.envelope_ok=false` record the breach instead of raising. Nothing is
clipped. `report_only` is refused for any searched knob, so it cannot be used to optimise past the
manufacturing envelope; an enlarged-envelope study needs a widened brief.

**a5's rolled-back, swept mouth is inherited, not new.** a5 has `rim_sweep_ratio = 0.10`
(`D_edge ≈ 31 mm`) and `end_frac = 1.20`, so the mouth lip is a warped loop whose axial z spans
72.7-103.8 mm. Rebuilding the *same parent genes with `cd_core_blend = 0`* gives the identical
72.7-103.8 mm loop, and setting `rim_sweep_ratio = 0` collapses it to a single plane. The visible "fin" in
the oblique sheet is therefore the legacy `klangfilm-lame-v1` rim sweep on a deep rollback, not an artefact
of the Phase A entrance deformation. It is still a geometry risk for meshing and is not certified here.

## Stage A search box

`configs/stage_a_search.yaml` searches exactly four physical knobs (theta_H 6-17 deg, theta_V 3-13 deg,
H mid gain 0-20 mm, V mid gain 0-3.75 mm) with the canonical genes, `cd_core_blend = 1.0` and join 0.65
pinned. `tools/geometry/klangfilm_hv_search_box.py` validates the box through the canonical adapter, then
materialises 200 Latin-hypercube samples and all 16 box corners:

- 200/200 samples lawful, 16/16 corners lawful.
- The box barely moves the envelope (W 541.26-541.28 mm), so it isolates the entrance/throat wall from
  mouth-size effects. That is the point of Stage A.
- Widths and heights are effectively constant because the Phase A offsets act near the throat; the
  earlier handoff stage that *did* move the mouth was Phase B's independent core length/area.
- The bounds are measured, not guessed: the H-gain wall is ~21.6 mm, the V-gain wall ~5.4 mm at
  theta_V 5 deg (falling to ~4.0 mm at 13 deg), and theta_V itself has a monotonicity wall at ~17.1 deg
  (a very steep early V slope overshoots, then the aspect gate pulls the V radius back).
