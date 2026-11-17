# Klangfilm-Lame H/V throat core — Phase A geometry diagnostics (2026-11-16)

Geometry-only hypotheses for the Phase A `klangfilm_lame_hv_cd` kernel
(`tools/geometry/klangfilm_lame_hv.py`, schema `klangfilm-lame-hv-v1`). **These are not acoustic
winners and carry no readiness or queue claim.** No BEM, GPU, mesh, shell, curvature or acoustic
validation was run to produce them.

The kernel imports the stable legacy `tools/geometry/klangfilm_lame.py` read-only as its parent. Each
config is an 8-basin geometry probe over one parent design (the canonical incumbent from
`runs/20261116T205942Z-screen-8b22b5/best.json`), with every bound fixed (`search: false`). H and V
are **true wall half-angles** measured from the axis, not beamwidth halves.

- Configs: `configs/a0.yaml` … `configs/a5.yaml`.
- Preflight: `tools/geometry/klangfilm_hv_preflight.py` →
  `docs/evidence/klangfilm_hv_2026-11-16/PREFLIGHT.md` + `preflight.json`.
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
| a5 | fc 400, aspect 1.65, p 4.0, end 1.20, rim 0.10, morph 0.3, blend 0, entry 2.0 | 11 / 6 | +12 / +6 | 0.65 | different mouth aspect; does the entrance deformation travel across parent genes? | accepted |

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
