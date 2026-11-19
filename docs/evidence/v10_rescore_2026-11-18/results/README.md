# v10 rescore RESULTS — owner-directed reuse pass (2026-11-18, local orchestrator)

Directive followed: protect all original `runs/` data (read-only; nothing deleted, overwritten or
rewritten), reuse completed row-level results, recompute only what was genuinely missing, max 3
CPU workers (thread caps 1; GPU night undisturbed), verify before accepting. **Net recomputation:
2 sample passes of 166 designs + 1 floor pass. Zero re-scoring of the completed full-fleet columns.
The full-fleet columns' J values are byte-identical to the first pass.**

## What was reused vs newly computed

| Artifact | Status | Where |
|---|---|---|
| v7 full fleet (3,949 rows / 3,661 scored) | REUSED (first pass, rows untouched) | `runs/analysis/v10_rescore_2026-11-18/v7/` → summary re-emitted at `reuse_v7/` |
| v9 full fleet (3,949 rows) | REUSED (unchanged; not part of the 3-column decision display) | `.../v9/` |
| v10-offline full fleet (3,949 rows) | REUSED | `.../v10/` → `reuse_v10_offline/` |
| v10-shipped | **NEW, owner-directed sample** (stratified 166) | `reuse_v10_shipped_sample/` → `results/summary_v10_shipped_sample166.json` |
| v10_slope5 | **NEW, sample 166** (diagnostic — R2: ranks nothing until its floor exists) | `reuse_v10_slope5_sample/` |
| Floors (freq part, top-28 same-mesh pairs, 257 pairs) | REUSED v7 + v10-offline; **NEW** slope5 | `floor_v7/`, `floor_v10/`, `floor_v10_slope5_owner/` |
| compare_all (3 columns) | NEW, on reused rows | `compare_all/` → `results/compare_all_summary.json`, `lane_bests_side_by_side.csv` |
| mixed_identity flags | FIXED (tool); re-emitted from brief inputs — see below | all summaries |

Scripts (committed here as provenance): `reuse_summary_emitter.py` (re-emit summaries from
preserved rows; no re-scoring), `select_rescore_sample.py` (stratified 166: 58 lane-best union +
16 per-lane diversity + 70 stratified-random (seed 20261118) + 12 worst-J + 10 failure cases),
`sample_rescore.py` (canonical-replay-only scorer for a sample), `sample_selection.json`.

## The mixed_identity fix and the acceptance

The compare flag previously counted per-design `score_id` values (every design carries a unique
`score_id` because it folds `metric_id`), so `mixed_identity` was always True on real data — the
README's "must be false" check was unsatisfiable. Fixed in `tools/analysis/rescore_identity.py`
(+ tests in `tests/test_rescore_identity_v10.py`): identity = (score code, objective version,
weights, objective block, brief hash/name) — the replay's score payload minus the per-design
part; per-row values collected, flag = count > 1. **All three compare columns now report
`mixed_identity: false`** [measured].

## v10-shipped vs v10-offline agreement (the README's J-parity check)

`shipped_vs_offline_agreement.json`: same 166-design sample scored under the shipped
`examples/briefs/home_landscape_2026-11-18_v10/….v10.yaml` and the offline brief; on all 122
matched scored rows **max |ΔJ| = 0.0 exactly** (tolerance 1e-12). The offline full-fleet column IS
the shipped column numerically; score ids differ by brief name only. **The shipped column's
ranking = the v10 full-fleet column's ranking** [verified on the sample].

## Floors (frequency part only; the mesh part comes from B1 — WP 2.3 pending)

| Identity | pairs | sd_diff_top (J) | note |
|---|---|---|---|
| v7 | 257 | **0.310** | ⚠ the PUBLISHED v7 floor is 0.13 J (D8), measured on a different protocol; see tension below |
| v10 (corridor, preferred_edge) | 257 | **0.468** | first published v10 freq floor (WP 1.5) |
| v10_slope5 (constancy dense grid) | 257 | **0.486** | first published slope5 freq floor (R2 gate now satisfied: it may rank, diagnostics only) |

**Floor tension flag [measured, senior item]:** this pass's `floor` subcommand (top-28 pairs,
same screen/verify mesh) measures the v7 frequency floor at 0.310 J, ~2.4× the published D8 v7
floor (0.13 J). Both numbers are recorded in `results/floor_v7_summary.json` and the D8 record;
until the senior pass reconciles the protocols, ties keep using the PUBLISHED 0.13 (README
acceptance #3 wording preserved) — but see NOTES_FOR_SENIOR 2026-11-18.

**Resolved 2026-11-19 (senior verdict 2, `scratch/fable_architecture/SENIOR_VERDICTS_2026-11-19.md`):**
tie calls on stored-grid v7 J use **0.31 J** (combined 0.3105). 0.13 J is A4's dense-232-J residual
and applies only to dense-scored J. Effect: fold_warm v7 ties the throat cluster.

## Per-lane bests and ties (floor-aware) — the top of the compare

- **v7:** ext_throat_hvlaw_v7 2.4976 → A_r15 3.0836 → (v8 3.1028, A_r20 3.1271 within 0.13 J = tie
  pair) → osse_rrect_fold_warm 3.3297. Full table: `lane_bests_side_by_side.csv`.
- **v10:** osse_rrect_fold_warm_v7 1.4214 ≈ osse_rrect_morph_v7 1.4305 (Δ 0.009 — tie under the
  0.468 floor) ≈ ext_throat_hvlaw_v7 1.5710 (Δ 0.150 — also within floor) → ath_twinray380_v8
  1.7726 → ext_throat v8 1.9075. The v10 top-3 **span three different constructions within one
  floor** — exactly the B6 (WP 6.2) matched-rerun set per R19/R20b.
- **Throat block under v10 (G5/R9 follow-up):** v8 1.9075 < A_r15 1.9760 < A_r20 2.0468; best B
  4.6704. Same ordering as v7; B remains ~2.7 J outside any floor → **the "park on A" reading is
  unchanged by v10**; the rho20 per-band finding remains a separate open item (NOTES 2026-11-18).

## Sampling caveat (explicit)

The slope5 column is a 166-design sample (marked `sampled: true, full_fleet_column: false` in its
summary). It is for diagnosis only; if anyone later needs slope5 fleet ranks, run the same
`rescore` command with the slope5 brief on the full fleet (single command, ~30 min CPU; out dir
must be new). The shipped column needs NO full-fleet run (agreement above).

## Scoring policy for the upcoming home-brief nights (owner-decision input, R1)

- v10's corridor + preferred_edge window prefers the fold-warm/morph constructions by ~1.1 J over
  v7's leader (identity-relative ranks, never absolute cross-identity J).
- Both scores agree on: ext_throat v7 leads its lane, the throat block is parked, fold-warm/morph
  lead the OSSE-rrect family. They disagree on family ordering (v7 favours ext-throat overall;
  v10 favours fold-warm/morph) — exactly the question the physical anchor was to settle (D6).
  **With the anchor unmeasurable this pass (see anchor evidence), the nights' score stays v7 (R1)
  until the fallback anchor or D6 step 2 produces a measured comparison.**
