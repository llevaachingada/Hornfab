# CD-backbone CMA cohort on the open v11 CD XO900 brief — predeclaration

Written 2026-11-25T17:35Z, before any solve. Outcomes go in README.md.

## Why

Owner request (2026-11-25): keep improving directivity and score, stay compatible with the metric-aware BO tools,
score on the newest scorer and brief, use the recent size control, and run about 100 solves per improved design.

- **Scorer:** objective v11 (newest; no v12 exists). **Brief:** `room_landscape_80x50_900_hf1440_v11cd_open115`
  = the v11 CD XO900 brief used by every backbone result, with the 2026-11-22/24 size policy: `envelope.enforce:
  false`, `max_utilization: 1.15` → candidate box 690 × 552 × 552 mm (product box 600 × 480 × 480). Over-cap
  candidates are refused before meshing and redrawn (`resample_strict`); every row records `size_feasibility`.
  **There is no soft size term in J** in this codebase (the graded `invalid_envelope` penalty only applies past
  the cap, and family adapters carry no overshoot value, so it is flat for them). Size inside 1.0–1.15 is
  therefore not penalised in J; it is filtered post hoc / on the Pareto axis. New identity: J is not ranked
  against the closed v11cd brief.
- **BO compatibility:** each campaign's bounds are a frozen identity of continuous knobs, ≤ 20 active dims
  (17 / 17 / 8 / 9); `bo.encoding.ActiveProjection` round-trips every seed to its exact design hash; 60/60
  random draws per space materialise (`space_preflight.json`). The metric-BO gate needs ≥ 100 usable screen rows
  per identity: 100 valid per campaign meets it, and the two rolled campaigns share one identity (200 rows).
  Generic-rows families (`rows_bb_v1`) still need the generated-space intake path before strict admission
  (metric BO handoff §1, `study_cohort._metric_candidates`).

## Campaigns (CMA-ES, screen tier, 100 VALID solves each, `sigma0` 0.12)

| Campaign | Kind | Seed design | Active knobs | CMA seed |
|---|---|---|---|---:|
| `rolled_bb_cohort_s1` | `rolled_family_rect_bb_v1` | body-1 keeper `rolled_bb_h065_th025` (passes all six rules) | 13 parent + 4 backbone | 81501 |
| `rolled_bb_cohort_s2` | same space | body-2 keeper `rolled2_bb_h065_th025` (passes all six rules) | same | 81502 |
| `lcl_bb_cohort` | `rows_bb_v1` / `lecleach` | `lcl_bb_h100_v000_t25_r20` (closest non-CD variant) | `T`, `fc_h`, `fc_v`, `stop` + 4 backbone | 81503 |
| `iwar_bb_cohort` | `rows_bb_v1` / `iwata_ar` | `iwar_bb_h100_v000_t25_r20` | `T`, `ar_m`, `ar_p`, `fc`, `stop` + 4 backbone | 81504 |

Bounds: `build_configs.py` (rolled parent ranges from the source campaign `a07561`, widened where a keeper sat
at an edge and the family law allows; backbone `bb_h` 0.45–0.85 rolled / 0.6–1.0 rows, `bb_v` 0–0.5, throat
0.15–0.30, roll-in 0.20–0.40 rolled / 0.15–0.30 rows). The rows campaigns let CMA move the parent's `fc`/`stop`,
i.e. the roll-on station — the lever batch 2 pointed to.

## Predictions

- Each campaign finds a design with screen J below its seed's screen J on this brief.
- **Risk stated in advance:** J falls while the six CD rules fail (shown on the dose axis), so the J-best design is
  not automatically the best CD horn. Selection after the cohort: the top 5 by screen J per campaign are checked
  against the six predeclared rules on verify against their seed as control; only rule-passers are promoted.
- Rolled: at least one top-5 design passes all six rules on verify. Rows (`lcl`, `iwar`): 50/50 that any design
  reaches H ≥ 62° at 8 kHz without a 2–4 kHz waistband.
- Rows campaigns will drift toward larger mouths (lower `fc`) — expected and recorded through `size_feasibility`.
