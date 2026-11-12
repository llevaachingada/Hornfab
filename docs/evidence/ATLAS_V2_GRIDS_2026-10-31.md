# Atlas v2 screen grids (2026-10-31, swarm lane C)

Spec: docs/SWARM_PLAN_2026-10-30.md section C. Grids printed with `hornlab_search.config.mode_freqs("screen", load_config(cfg))`
from this worktree [measured]. Base grid: `freq_grid(500, 10000, 12)` clipped to band_hi 8000, then `grid.screen_extra_hz`
merged by `_merge_screen_extra` (top-clipped, bottom never clipped).

## Added points (both v2 briefs)
`screen_extra_hz: [315, 400, 1850, 2150, 2500]`
- 315, 400: the v5 18-point low end that is inside band 300-8000 (250 is below band_lo, so left out).
- 1850 (4.9 % from 1763.18), 2150 (5.2 % from 2268.63), 2500 (new): 1.8-3.2 kHz fill.
- 2900 skipped: 0.65 % from 2918.96 (rule: skip within 3 %).

## Grids per brief (Hz)

| config | brief | before (n) | after (n) |
|---|---|---|---|
| atlas2__hyb_osse_h_hypex_v | atlas_v2_2026-10-31/b2w_pa_60x40_1200_big_v4_atlas2 | 12 | 17 |
| atlas2__ath_core | atlas_v2_2026-10-31/native_ath_core_2in_v4_atlas2 | 12 | 17 |
| atlas2__core_law | atlas_v2_2026-10-31/native_ath_core_2in_v4_atlas2 | 12 | 17 |
| atlas2__osse_ext_throat | hardened_2026-10-29_v5/b1w_hifi_90x60_850_wide_v5 (unchanged) | 18 | 18 |

| Hz | v4 briefs before | v4 briefs after (v2) | v5 osse_ext_throat (unchanged) |
|---|---|---|---|
| 250 | | | x |
| 315 | | x (new) | x |
| 400 | | x (new) | x |
| 500 | x | x | x |
| 643.33 | x | x | x |
| 827.75 | x | x | x |
| 1065.04 | x | x | x |
| 1370.35 | x | x | x |
| 1763.18 | x | x | x |
| 1850 | | x (new) | |
| 2150 | | x (new) | |
| 2268.63 | x | x | x |
| 2500 | | x (new) | |
| 2573 | | | x |
| 2918.96 | x | x | x |
| 3311 | | | x |
| 3755.72 | x | x | x |
| 4260 | | | x |
| 4832.36 | x | x | x |
| 6217.63 | x | x | x |
| 8000 | x | x | x |

## Expected time factor [inferred]
Screen solves scale roughly with frequency count: 17/12 = 1.42x per eval for the three v4-brief configs (inside the
plan's 1.3-1.5x). Two of the five new points are low (315/400 Hz), which are cheap on a fixed mesh, so the real factor
may be slightly lower; unmeasured. osse_ext_throat: 1.0x (grid unchanged). The solve hash changes, so v2 runs use a
new cache.

## osse_ext_throat
The v5 brief `examples/briefs/hardened_2026-10-29_v5/b1w_hifi_90x60_850_wide_v5.yaml` exists on this branch (added in
bd257cd, an ancestor of swarm/C-2026-10-31) and `load_config` + shape_check pass, consistent with the night failure
being only the missing file on the branch it ran from [inferred: no failure log for it was found under docs/].

## Validation [measured]
`load_config` OK for all four. `tools/shape_check.py examples/typologies/atlas_v2_2026-10-31/*.yaml` (CPU, gmsh only):

| config | ok | dofs / cap | mouth W x H mm | depth mm | envelope | driver coupling |
|---|---|---|---|---|---|---|
| atlas2__ath_core | yes | 3777 / 12000 | 397 x 397 | 359 | fits | round, matches the exit |
| atlas2__core_law | yes | 5179 / 12000 | 552 x 399 | 359 | fits | round, matches the exit |
| atlas2__hyb_osse_h_hypex_v | yes | 1985 / 12000 | 335 x 294 | 218 | fits | round, matches the exit |
| atlas2__osse_ext_throat | yes | 1879 / 12000 | 332 x 300 | 185 | fits | round, matches the exit |
