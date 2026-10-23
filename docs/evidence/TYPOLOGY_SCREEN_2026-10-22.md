# Typology screen campaigns, 2026-10-22 (first fair run)

Tier `screen`: one CMA-ES run per family (CMA seed 1234), budget = max(40, 10 × knobs) total evaluations including
cache hits (`--max-evals`), every family scored on the brief's target and weights and held to the brief's size
envelope (outer mesh bounding box, shell included). A coarse ranking only: claims that one typology beats another need
the `compare` tier (2 CMA seeds, median and spread). Raw: `docs/evidence/campaigns/`.

Bugs found and fixed before these numbers were trusted (CONTINUITY 2026-10-22 ~20:30 / ~21:00): `search` ignored
`--brief`; cached replays gave native configs 6–15× more search; worker hosts survived hygiene; the size envelope was
only enforced for generated horns; generator knob counts could fall back silently. Earlier campaign directories
(`campaign_20261022T213156Z`, `…T221610Z`, `campaign_20261023T001215Z`, `…T003052Z`) are superseded.

## Brief `axi_90x90_1in` (axisymmetric 90×90°, 1-inch driver, 360 × 360 × 220 mm, load weight 0.5, z_min 0.7)

| Family | Group | Knobs | Best J | cov | rip | dislope | load | f_load (Hz) | Note |
|---|---|---|---|---|---|---|---|---|---|
| osse_axi | classical (OSSE meridian) | 4 | **10.71** | 4.95 | 4.06 | 0.40 | 0.15 | 3556 | |
| blend_osse_tractrix | hybrid | 4 | 11.04 | 4.74 | 4.72 | **0.09** | 0.13 | 2860 | flattest DI of the leaders |
| hypex | classical | 3 | 12.27 | 5.75 | 3.81 | 0.86 | 0.08 | 1849 | loads lowest of the leaders |
| exponential | classical | 2 | 12.59 | 6.01 | 3.84 | 0.94 | 0.09 | 1849 | |
| blend_conical_exponential | hybrid | 4 | 12.98 | 6.02 | 3.91 | 1.24 | 0.09 | 1849 | |
| freeform_sculpt | Magnus | 11 | 15.81 | 7.24 | 5.59 | 0.55 | 0.07 | 1487 | 37/110 outside the envelope |
| icw_termination | Magnus | 6 | 21.45 | 11.24 | 6.08 | 1.39 | 0.26 | — | 25/60 invalid; never loads to 0.7 |
| icw_rollback | Magnus | 5 | 25.22 | 19.73 | 3.14 | 0.69 | 0.20 | 4423 | beam too wide (74–148°) |
| conical | classical | 2 | 28.21 | 17.38 | 5.88 | 1.97 | 0.19 | — | narrows to 37° at the top |
| perturbed_tractrix | hybrid | 8 | 89.75 | 22.53 | 5.94 | 59.3 | 0.00 | 1196 | |
| tractrix | classical | 1 | 103.72 | 23.83 | 6.86 | 71.2 | 0.01 | 962 | best loading, worst directivity |

## Brief `hifi_90x60_1in` (H/V 90×60°, 1-inch driver, 400 × 300 × 220 mm)

| Family | Group | Knobs | Best J | cov | rip | Note |
|---|---|---|---|---|---|---|
| perturbed_osse_hv | hybrid | 18 | **11.22** | 6.76 | 3.17 | 65/180 invalid; `L_mm` pinned at its bound |
| hyb_osse_h_hypex_v | hybrid | 5 | 15.78 | 11.00 | 3.28 | V beam 58–119° vs 60° |
| freeform_hv | Magnus | 3 | 18.80 | 14.01 | 3.24 | |
| rosse_baseline | Magnus | 11 | 19.41 | 11.05 | 3.76 | 40/110 invalid inside the envelope |
| hyb_osse_h_tractrix_v | hybrid | 4 | 46.40 | 24.50 | 4.11 | tractrix V mouth (171 mm) too small for 60° |
| freeform_sculpt | Magnus | 11 | — | | | NO VALID DESIGN: seed is outside this envelope |
| osse_baseline | Magnus | 9 | — | | | NO VALID DESIGN: seed (1.4-inch driver, 75×45 sizing) outside this envelope |

## Reading (senior, screen tier only)

1. **OSSE-derived profiles lead both briefs** at equal size and equal search, as expected for directivity briefs.
2. **The OSSE ↔ tractrix blend is within 3 % of pure OSSE with a 4× flatter DI slope**: a genuine hybrid candidate
   for the `compare` tier.
3. **Hypex and exponential horns are only ~15 % behind on the loading-weighted brief** and load the driver from about
   1.8 kHz vs 3.6 kHz for the OSSE leader: the trade-off the plan predicted (loading vs pattern control).
4. **Tractrix fails on directivity because f_c sets its mouth** (180 mm here): it cannot hold 90° down to 700 Hz and
   then beams (DI-slope term 71). Its loading is the best measured (f_load 962 Hz).
5. **On the 90×60 brief the best design is a new hybrid** (OSSE H and V, separate coverage, monotone perturbation,
   rounded-rectangle mouth), ahead of Magnus's R-OSSE and FREEFORM at the same size. It is bound-limited (`L_mm`) and
   loses 36 % of its budget to invalid geometry, so its true potential is higher than shown.
6. Native configs sized for other targets (OSSE 75×45, FREEFORM sculpt) cannot be searched inside a smaller envelope;
   beta users should use the typology configs or size a native config for their brief.

Next: `compare` tier (2 seeds) on osse_axi, blend_osse_tractrix, hypex (axi brief) and perturbed_osse_hv,
hyb_osse_h_hypex_v, rosse_baseline (hifi brief); widen `perturbed_osse_hv`'s `L_mm` only with the user's OK.
