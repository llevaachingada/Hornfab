# Typology compare tier, 2026-10-23 (overnight queue, unattended)

Queue `tools/overnight/queue_20261022.ps1`; GPU lock held per step; `gpu-clean` before and after each; watchdog
never intervened. Compare tier = 2 CMA seeds (1234, 777) per family, budget max(150, 25 x knobs), `--max-evals` =
budget (equal search). Axi typologies at **epw 8** (beta C2), H/V at epw 6. Evidence:
`campaigns/campaign_20261023T021639Z.*` (axi screen, epw 8), `campaign_20261023T024453Z.*` (axi compare),
`campaign_20261023T043338Z.*` (hifi compare).

**Ranking rule:** "A beats B" only where the medians differ by more than both spreads (spread = max - min over the
two seeds). Two seeds is a small sample: a spread is a lower bound on the seed-to-seed variation, not a confidence
interval. Screen-tier numbers are not comparable to compare-tier numbers (different budgets).

## Axi 90x90 brief (`axi_90x90_1in`, 360 x 360 x 220 mm envelope)

| Family | Knobs | Seed 1234 J | Seed 777 J | Median | Spread | Failures (of 150 each) | Pinned at bound (best design) |
|---|---|---|---|---|---|---|---|
| osse_axi | 4 | 9.641 | 9.622 | 9.631 | 0.019 | 5 / 6 | `h_s` = 0.60 (hi) |
| blend_osse_tractrix | 4 | 10.035 | 10.066 | 10.050 | 0.031 | 21 / 27 | none |
| exponential | 2 | 11.366 | 11.364 | 11.365 | 0.002 | 0 / 0 | `L_mm` = 120 (lo), `h_rm_mm` = 175 (hi) |
| hypex | 3 | 11.382 | 11.410 | 11.396 | 0.028 | 0 / 0 | `L_mm` = 120 (lo), `h_rm_mm` = 175 (hi) |

- **Claimed:** osse_axi < blend_osse_tractrix < {exponential, hypex} (gaps 0.42 and 1.3 vs spreads <= 0.03).
- **Not claimed:** exponential vs hypex (gap 0.031, at the edge of hypex's spread). Both best designs sit in the
  same corner of the box (shortest allowed horn, largest allowed mouth; outer quarter bbox 175 x 175 x 120 mm), so
  their order reflects the bounds, not the typology.
- osse_axi wants more termination (`h_s` at its upper bound) on both seeds: its lead may grow if `h_s` is freed.
- epw 8 re-screen vs the epw-6 screen of 2026-10-22 (same budget 40, seed 1234): osse_axi 10.71 -> 10.64,
  blend 11.04 -> 10.98, hypex 12.27 -> 12.16, exponential 12.59 -> 12.51; order unchanged.

## Hifi 90x60 brief (`hifi_90x60_1in`, 400 x 300 x 220 mm envelope)

| Family | Knobs | Seed 1234 J | Seed 777 J | Median | Spread | Failures | Pinned at bound (best design) |
|---|---|---|---|---|---|---|---|
| perturbed_osse_hv | 18 | 10.297 | 10.323 | 10.310 | 0.026 | 152 / 122 of 450 | `L_mm` = 140 (hi); seed 777 also `v_a_deg` = 35 (hi), `v_u1` = 0.25 (hi) |
| rosse_baseline | 11 | 12.314 | 14.339 | 13.326 | 2.025 | 92 / 87 of 275 | none |
| hyb_osse_h_hypex_v | 5 | 15.189 | 15.065 | 15.127 | 0.125 | 20 / 29 of 150 | `v_rm_mm` = 140 (hi); seed 1234 also `h_a_deg` = 47.9 (near hi 50) |

- **Claimed:** perturbed_osse_hv beats both others (gap 3.0 to rosse > rosse's 2.0 spread).
- **Not claimed:** rosse_baseline vs hyb_osse_h_hypex_v (gap 1.8 < rosse spread 2.0). R-OSSE is seed-sensitive:
  one seed found 12.3, the other 14.3 - more seeds or budget needed before any statement.
- Invalid-geometry rates stay high: perturbed_osse_hv 30 %, rosse_baseline 33 % (mostly the brief envelope and the
  FREEFORM curvature guard). Each failure costs mesh time only, no solve.

## Bound proposals (NOT applied; owner decision; widening invalidates comparison with the runs above)

Envelope limits are on the OUTER mesh bbox (shell included), half-sizes because the quarter model is meshed.

| Config | Knob | Now | Best design | Proposal | Grounding |
|---|---|---|---|---|---|
| osse_axi | `h_s` | [0, 0.6] | 0.60 both seeds | hi 0.9, after checking the mesher's accepted OSSE `s` range | OS termination parameter; the envelope is not binding (outer half-size 164-168 of 180 mm) |
| hypex, exponential | `L_mm` | [120, 220] | 120 | lo 80 | depth not binding at the short end; shorter horns are legal geometry |
| hypex, exponential | `h_rm_mm` | [60, 175] | 175 | hi 177 at most | envelope half-size 180 minus the 3 mm shell: this IS the envelope, so effectively no room |
| perturbed_osse_hv | `L_mm` | [90, 140] | 140 | hi 200 | depth envelope 220 mm; best outer depth 140 mm |
| perturbed_osse_hv | `v_a_deg` | [20, 35] | 35 (seed 777) | hi 40 | the 60 deg V target is total included angle; 35 deg half-angle is already wider than 30 |
| hyb_osse_h_hypex_v | `v_rm_mm` | [50, 140] | 140 | hi 147 | envelope half-height 150 minus the 3 mm shell |

For the mathematician: three of the five pinned cases sit against the brief envelope itself (mouth size), not an
arbitrary knob range. There, the objective is asking for a bigger mouth than the brief allows, and that is a
statement about the brief, not about the typology.
