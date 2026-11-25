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

## Addendum, written 2026-11-25T17:55Z (12:55 EST) before any of these solves — beak mouths

**Trigger.** Owner: the recent horns have flat mouths "like they're going to be mated to a cabinet", while they will
hang freestanding (every solve here is a freestanding quarter model). Survey of every saved campaign with a
beak-type knob (`scratch/beak_survey.py`): the beak constructions exist but were boxed in — the Klangfilm core beak
narrowed from 0–60 / 0–45 / ±20 mm to 0–10 / 0–5 (later pinned 0.04) / ±5 mm; Lamé v1 negative rim sweep pinned at
its −0.22 floor on v11; rolled `axial_*` is a late-body bump that returns to zero before the lip (≤ 10 % of depth),
so the rolled lip itself only moves through `depth_h_ratio`.

**Batch-1 observation that is also evidence:** `rolled_bb_cohort_s1` was stopped by the bound-pinned watchdog after
30 valid rows (best screen J 4.688) with 4/6 of its top 6 at `g_depth_h_ratio` = 1.0 — the SEARCH ceiling inherited
from the source campaign; the kernel allows 0.5–1.2 (> 1 = H lips ahead of V).

**New campaigns (CMA, 100 valid, same open brief, `resample_strict`):**

| Campaign | Change | Dims |
|---|---|---:|
| `rolled_beak_cohort_s1` / `_s2` | rolled + backbone with `depth_h_ratio` 0.55–1.2 (both saddle directions); new identity | 17 |
| `lcl_beak_cohort` | Le Cléac'h H/V CD hybrid + **rim-beak overlay** (new kind `beak_v1`: H, V ±60 mm, 45° scoop ±30 mm, gate start 0.4–0.85; zero = the parent's verify mesh byte-for-byte) | 12 |
| `iwar_beak_cohort` | Iwata AR CD hybrid + rim-beak overlay | 13 |
| `klangfilm_core_beak_cohort` | Klangfilm-Lamé H/V core (best of the v11 `cd11c` run), its own beak reopened to the kernel range; this kernel only sets H back / V forward | 12 |

Watchdog `pin_ignore` on beak amplitudes and on law-coupled knobs (rolled depth floor / axial relief): bound pinning
is reported post hoc instead of stopping the cohort at ~30 rows.

**Predictions.** (1) `rolled_beak` top designs leave 1.0: median `depth_h_ratio` of the top 10 > 1.0 (H ahead), and
its best screen J ≤ 4.688 (`rolled_bb_cohort_s1`'s best). (2) For `lcl_beak` / `iwar_beak` the top-10 median of
`rb_v_mm − rb_h_mm` is non-zero with |·| ≥ 10 mm (the optimizer uses the beak), sign not predicted. (3) The Klangfilm
core's best J beats nothing in the rolled set (its v11 best was 7.05 on the 700 Hz brief). (4) Same caveat as above:
every promotion is by the six CD rules on verify, never by J alone.
