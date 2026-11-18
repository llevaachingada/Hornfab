# PORTFOLIO_EVIDENCE — Stage 3 diverse-horn screening (research-only, screen_only)

Date 2026-11-18, worktree `feat/woofer-system-v0`. CPU-only; no GPU, no solver, no canonical
writes. Study id **`1a509f87c01fd6fd`**, immutable manifest at
`system_runs/system/portfolio_screen/20261118T213057Z-portfolio-39052-dae2d753/manifest.json`
(sha-self-checked; rerun reproduces it byte-identically).

## 1. Command

```
python -m hornlab_search.system.cli portfolio ^
  --spec examples/systems/two_way_80x50_700_research.yaml --k 8 --scan-limit 240 --limit-boxes 6
  --out system_runs            # drivers default to the two verified 12-inch stems
```

## 2. Pool and selection (stratified, never by J)

- Pool: 602 assets from the 240 newest canonical run dirs (read-only inventory).
- 8 selected by round-robin over `(family, brief)` buckets, deterministic asset_id order:
  6 × FREEFORM across 6 distinct briefs (home_hifi_range, lecleach_rollback, organic_rollback,
  rosse_rect_v7, v7, v7_smooth) + 2 × OSSE (`native_ath_core_2in_v4`, `_atlas2`).
- **542 lost-candidate rows** remain in the report/manifest with reasons (dominant reason:
  "no p_balloon field") — nothing silently dropped. The pool is newest-first, so family coverage
  is FREEFORM-heavy by recency; a deeper scan (or brief-targeted pool) is the recorded next step
  for OSSE/R-OSSE/bi-radial breadth, not a defect of the picker.

## 3. Identical budget per cell (16 cells = 8 horns × 2 drivers)

Every (horn, driver) cell gets the same spec ranges, the same volume-spread box sample,
the same crossover grid (700/1000/1300 Hz), gains 0, delay 0 — verified equal row counts per
cell (unit-tested: `tests/system/test_portfolio.py::test_portfolio_budget_identity_and_visibility`).
Per cell: 6 box rows, LF (F3 ≤ 55 Hz) gates → 3 PASS (larger boxes) / 3 FAIL (35–60 L), feasible
construction PASS everywhere, crossover axis FAIL everywhere (the Stage-2 700 Hz piston
half-space finding, consistent across every horn).

## 4. Two independent screens; disagreements reported, never corrected

Primary screen: converted balloon 6 dB **angular radius** (`SCREEN_COMPLEX_APPROX` label).
Alternate screen: plane-cuts max(H,V) −6 dB **chord/2** (same quantity, from H/V cuts).
Disagreements > 8° are report rows:

| asset (short) | cuts half-angle @700/1000/1300 | max disagreement | flagged |
|---|---|---|---|
| 067bee h12_pilot | 77.5 / 68.1 / 65.0 | 17.5° | yes |
| 000e18 lecleach_rollback | 63.2 / 49.1 / 42.1 | 1.7° | no |
| 21ab08 organic_rollback | 67.5 / 70.0 / 67.0 | 3.6° | no |
| 013eba rosse_rect_v7 | 45.8 / 33.7 / 36.5 | 8.9° | yes |
| 0014e1 v7 | 49.2 / 35.0 / 28.5 | 10.4° | yes |
| 0037af v7_smooth | 82.5 / 61.9 / 50.1 | 35.5° | yes |
| 00cd71 ath_core_2in | 40.0 / 29.4 / 29.5 | 2.4° | no |
| 165495 ath_core_atlas2 | 41.5 / 33.0 / 37.9 | 2.6° | no |

Off-agreement cells are exactly the honest "screen uncertainty" surfacing the plan asked for
(balloon-peak direction vs on-axis reference; narrow/rolled families). Disagreement is a report
column with a note; no rejection/selection was changed because of it. **Unit bug found and fixed
on the way:** the alternate screen first published full chords (chord-vs-radius = factor 2
mismatch, false 40–95° "disagreements"); normalized to half-angles before any comparison, with
`max(nan(x))` Python-semantics bug also fixed.

## 5. Claims and refusals (same as Stage 2, portfolio-wide)

Report-only Pareto under `system_objective_version=1`; **no horn is ranked, no horn v7/v9 J is
loaded anywhere in this module**; winner is refused when rows carry FAIL (all cells do at the
handoff axis). The result is a screening funnel for Stage 4, not a leaderboard.

## 6. Reproduce

Re-run the §1 command (deterministic; identical study id and rows — unit-tested). The manifest
carries the full asset list, per-cell rows, alternate-screen values and the lost-candidate ledger.
