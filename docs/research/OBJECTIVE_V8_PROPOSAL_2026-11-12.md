# Objective v8 proposal (2026-11-12) — linear units, calibrated tolerances, gates as hard refusals

**STATUS: PROPOSAL ONLY. Owner sign-off required.**
Nothing in this document is registered or active: `objective/versions.py` still dispatches versions 1-7,
no shipped brief uses `version: 8`, and no default changed. Day-plan group G (§5). The scorer is
`hornlab_search/objective/scalar_v8.py`; the evidence run is `tools/analysis/v8_rescore.py`
(read-only over the committed dataset); this page is the one-page owner brief.

---

## 1. Owner summary (plain language)

- **The problem v4 has.** The composite J adds squared errors (`cov`, `diag`, `dislope`) to linear errors
  (`rip`, `flat`) and divides each by a fixed tolerance. A weight therefore does not mean "influence": on
  28,790 stored solves the v4 median share of J was cov 0.42 while rip (weight 1.0, same as cov) was 0.01,
  and `load` 0.00. Two terms with the same weight can move J by 40x different amounts, and the ratio changes
  with distance from the target.
- **What v8 changes.** Every weighted term is scored in its own **linear** error unit (RMS degrees for
  coverage/diagonal, RMS dB for ripple/DI/flatness, dB/decade for slope), so a term's J contribution is
  proportional to the error itself. Each term is divided by a **tolerance measured from the data** (median
  raw value over the top decile of stored valid rows, per brief class). Loading, f11 and round-throat stop
  being weights and become **hard refusals** (the 1e3 failure penalty), because a gate is a constraint, not a
  preference to trade off.
- **What the re-score shows.** [measured] Full committed dataset (23,833 scored rows): Kendall tau
  v8-vs-v4 is **0.500 / 0.769 / 0.815** for classes A/B/C, with top-20 overlap **4/20, 0/20, 13/20**.
  Class B is the critical caveat: **3,545 of 4,063 rows (87%) are hard-refused** by the loading/f11
  gates (the archive predates them), leaving only 518 rankable rows. v8 is a different ruler, not a
  better-ranked version of the same shortlist; the change must be evaluated with a paired-seed A/B
  night, never switched silently.
- **What I recommend.** Do **not** register v8 or switch a brief today. (1) Owner reviews this brief.
  (2) If approved, the calibration night (Group C) and a paired-seed A/B (v4/v7 control vs v8, >= 5 seeds per
  class) run before any brief is switched. (3) v8 stays an offline scorer until that A/B is read.
- **Risk.** Tolerances are calibrated on the *current* archive, which is v4/v7-selected; the next archive will
  shift the top decile. Recalibration is a one-command measurement, not a code change.

## 2. Design

### 2.1 Linear units (the fix for "weights do not mean influence")

| term | v4 unit | v8 raw unit | definition |
|---|---|---|---|
| `cov` | squared, tolerance-normalised | **RMS deg** | sqrt(weighted mean of side-weighted squared H/V edge error), planes combined; v4 masks kept (f0, f0_v, narrow ratio, below-f0) |
| `diag` | squared, tolerance-normalised | **RMS deg** | sqrt(mean side-weighted squared 45/135 -6 dB beamwidth error vs the round reference) |
| `rip` | linear dB / tol | **RMS dB** | sqrt(weighted mean of squared per-f `ripple_h + ripple_v`) (v2 detrended when `Response` present) |
| `di` | squared error / tol | **RMS dB** | sqrt(mean (di - DI target)^2) |
| `dislope` | squared error / tol | **dB/decade** | \|slope - target\|, linear (the repo's only defined slope unit; 1 dB/decade = 0.301 dB/oct) |
| `flat` | linear dB / tol | **dB** | v2 detrended band flatness (already a dB std) |
| `distd` | linear dB / tol | **dB** | v4's DI std over the scored band (weight 0.0 by default) |
| `flat_cv` | linear dB / tol | **dB** | v7 constant-velocity on-axis flatness (weight 0.0 by default) |
| `load` | weighted penalty term | **not a term** | loading is a gate (§2.3) |

J = sum_k w_k * raw_k / tol_k, unchanged in form. Default weights are v4's defaults minus `load`:
`{cov 1.0, rip 1.0, di 0.3, dislope 0.5, flat 0.5, distd 0.0, diag 0.0, flat_cv 0.0}`.
Unmeasurable in-band samples keep the repo convention: `NAN_TERM_FILL / tol` (finite, unflattering, never 0).

### 2.2 Calibrated tolerances

`tol_k = median(raw_k over the top decile of the class's stored valid rows)`, top decile =
`max(3, ceil(n/10))` rows, ranked under the **class-matched v4 brief** (one version-consistent ruler per
class). This is the A.9 `term_balance` top-decile method applied to v8's raw units: near the optimum every
weighted term then contributes ~equally per unit weight. The measured values are in §4; they are
descriptive calibration defaults for the proposal, not an independently validated tolerance set.

Tolerances live in `V8_MEASURED_TOLERANCES` (per class A/B/C) and can be overridden per brief through the
`objective:` block (`version: 8`, `tolerances: {...}` — every weighted key is required, no silent defaults).

### 2.3 Gates as hard refusals

A gate returns `PENALTY_FAILED` (1e3) with `gate_failed=1`, never a weighted term:

- **`loading`** — the canonical 2026-10-29 loading gate (LFP20 x 1.6 <= F_X and Re z >= 0.50 over the
  loaded window). Fires only for a loading-scored target (`target.z_min >= 0.5`, the repo's class-B marker).
- **`f11`** — the loaded window must resolve and be non-empty; an empty/unmeasurable window refuses.
- **`round_throat`** — the existing C4 refusal (`search/evaluate.py`), applied when the caller supplies the
  throat-shape dict; absent throat data means "not applied" because in-search enforcement stays with C4.
  The dataset stores no mesh, so the re-score cannot exercise this gate (documented in every table).

A gate that is applied but unmeasurable **refuses** (`tools/rescore/gate_audit.py` convention: unresolved
fails). Gate trigger rules are fixed and documented, never silent.

## 3. Method of the re-score

1. Walk `dataset/shard-*.jsonl` + `shard-NNNN/rec-NNNN.npz` read-only through the canonical
   `tools/rescore` readers (`gate_audit.parse_stored_row`, `rescore_v6_v7` target classification). One
   implementation of dataset parsing; no copy.
2. Re-score every stored valid row under the class-matched **v4**, **v6** (the only shipped v6 brief) and
   **v7** briefs, and under **v8** with the per-class calibrated tolerances.
3. Per class and per baseline version: **Kendall tau** over shared unique `(design, target)` keys with both
   scores below the 1e3 penalty floor, **top-20 shortlist overlap**, tau on the union of the two top-20 sets,
   and gate-refusal/penalty counts. Never compare absolute J across versions; only rankings.
4. Zero GPU, zero solver. `dataset/` is never written; outputs go to `--out` only.

## 4. Measured results — full committed dataset

Run: `PY tools/analysis/v8_rescore.py --dataset <main-checkout>/dataset --out
scratch/objective_v8_full_2026-11-12` (2026-11-12 16:01; no GPU, no solver; `dataset/` read-only).
Counters: **23,833 rows seen and scored**; this tool version increments only `rows_seen` and
`scored` (no separate parse/target/scoring counters). Per class: **A 18,145 rows / 17,930 unique /
0 refusals**; **B 4,063 / 3,705 / 3,545 refusals (87%) / 518 rankable**; **C 1,625 / 1,596 / 0
refusals**.

### 4.1 Calibrated v8 tolerances (per class)

`tol_k = median(raw unit value of term k over the class's top decile, ranked under the
class-matched v4 brief)`; top decile = `max(3, ceil(n/10))` (A.9 method). Units are the v8 linear
units in §2.1.

| term | class A | class B | class C |
|---|---:|---:|---:|
| `cov` (RMS deg) | 8.757689 | 22.719222 | 14.381958 |
| `rip` (RMS dB) | 0.421918 | 0.522207 | 0.351929 |
| `di` (RMS dB) | 1.443739 | 1.939936 | 1.209070 |
| `dislope` (dB/decade) | 0.174394 | 1.695258 | 0.433611 |
| `flat` (dB) | 0.928464 | 2.098825 | 2.116956 |
| `distd` (dB) | 0.564775 | 1.594934 | 0.771823 |
| `diag` (RMS deg) | 8.745682 | 20.855939 | 15.445944 |
| `flat_cv` (dB) | 0.764295 | 1.360802 | 1.123577 |

The full-dataset p10/p90 per term are in the run JSON; the code ships these medians as
`V8_MEASURED_TOLERANCES` (see `hornlab_search/objective/scalar_v8.py`).

### 4.2 v8 vs v4 / v6 / v7 — per class

Tau is over every shared unique `(design, target)` key with both scores below the 1e3 penalty
floor; top-20 overlap counts shared entries; union tau pairs the two rankings on the union of the
two top-20 sets. v6 has one shipped brief applied to every class; treat it as a control.

| class | baseline | rankable | Kendall tau | top-20 overlap | union tau | v8 / base penalties |
|---|---|---:|---:|---:|---:|---:|
| A | v4 | 17,930 | 0.5004 | 4 / 20 | -0.3365 | 0 / 0 |
| A | v6 | 17,930 | 0.0138 | 0 / 20 | -0.3308 | 0 / 0 |
| A | v7 | 17,930 | 0.4394 | 3 / 20 | -0.2883 | 0 / 0 |
| B | v4 | 518 | 0.7687 | 0 / 20 | -0.3833 | 3,187 / 0 |
| B | v6 | 518 | 0.2174 | 7 / 20 | -0.3485 | 3,187 / 0 |
| B | v7 | 518 | 0.6719 | 0 / 20 | -0.6462 | 3,187 / 0 |
| C | v4 | 1,596 | 0.8150 | 13 / 20 | 0.1909 | 0 / 0 |
| C | v6 | 1,596 | 0.0086 | 0 / 20 | -0.4923 | 0 / 0 |
| C | v7 | 1,596 | 0.8104 | 0 / 20 | -0.4205 | 0 / 0 |

### 4.3 Reading the numbers

- **Class A:** tau(v8,v4)=0.500 and top-20 overlap 4/20; v7 0.439/3/20; v6 0.014/0/20. v8 reorders
  the class-A archive substantially — only 4 of the v4 top-20 survive.
- **Class B:** 3,545/4,063 rows (87%) are hard-refused by loading/f11; the 518 rankable rows have
  tau(v8,v4)=0.769 but top-20 overlap 0/20. The refusal rate is a data-eligibility/selection result,
  not a v8 quality result. Any class-B A/B is conditional on 518 rows and must report the censoring.
- **Class C:** tau(v8,v4)=0.815 with top-20 overlap 13/20 (the strongest shortlist agreement);
  v7 tau=0.810 but top-20 0/20; v6 tau=0.009.
- The tolerance table is derived from the same archive it is evaluated on (top decile ranked under
  v4). It is a descriptive calibration, not an independent validation; recalibrate after a v8
  campaign and read §4 again.

## 5. What adoption would require (owner checklist)

1. Owner sign-off on this brief and on the §4 numbers.
2. Register `version: 8` in `objective/versions.py` **and** add a v8 brief next to the class-matched v4/v7
   briefs (one per class) in a separate PR. Defaults stay: every existing brief keeps its version.
3. Calibration night (Group C.1/C.2, P0 thresholds) plus a **paired-seed A/B**: v4/v7 control vs v8, >= 5
   seeds per class (3-4 seeds are "indicative" only, per A.2), equal budget, verify-J-only finalist ranking
   (C.4). Read with A.2/A.6 statistics, not single-run J.
4. If the A/B is neutral or better: switch one class at a time, freeze the old briefs, and record the config
   hash change as an owner decision in CONTINUITY.

## 6. Risks and open questions

- **Calibration circularity.** Tolerances are the top-decile median of the *v4/v7-selected* archive. After a
  v8 campaign the top decile shifts; recalibrate and re-read §4 before trusting the numbers for a new class.
- **v6 has one shipped brief** (`native_lecleach_1200_1in_v6`) applied to every class here; v6 comparisons
  are a control, not a class-matched baseline.
- **Round-throat gate is untested offline** (no mesh in the dataset). In-search behaviour is C4's existing
  code path and its own tests.
- **`dislope` units.** dB/decade is kept because it is the repo's only defined slope unit; if the owner wants
  dB/oct, the tolerance absorbs the constant factor (x0.301) — a calibration, not a code change.
- **Reference targets.** `diag` compares to the round-reference beamwidth; class B/C targets that deliberately
  depart from round are still scored against it (weight 0.0 by default, so this only matters if enabled).

## 7. Provenance

- Scorer: `hornlab_search/objective/scalar_v8.py` (not registered anywhere).
- Re-score: `tools/analysis/v8_rescore.py` (read-only over `dataset/`; writes `v8_rescore.json` +
  `v8_rescore.md` under `--out`).
- Tests: `tests/test_objective_v8.py`, `tests/test_tools_analysis_v8_rescore.py` (synthetic rows only; no
  real data in tests).
- Command (this box, 2026-11-12 16:01, no GPU, no solver):
  `PY tools/analysis/v8_rescore.py --dataset <main-checkout>/dataset --out scratch/objective_v8_full_2026-11-12`
  (23,833 rows scored; `rows_seen`/`scored` counters; class A/B/C split in §4). The run JSON/MD
  stay in `scratch/objective_v8_full_2026-11-12/`; §4 is the durable summary.
- Benchmark archive: `docs/research/SEARCH_MATH_DOSSIER_2026-11.md` §6; A.9 data in
  `tools/analysis/term_balance.py`.
