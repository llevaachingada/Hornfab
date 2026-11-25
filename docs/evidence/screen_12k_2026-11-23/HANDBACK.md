# SENIOR HANDBACK — 12 kHz SCREEN policy (2026-11-23/24)

Final. 24 designs × 7 arms (162 evaluations, 161 ok), plus epw 5/6/8 on 4 designs. Numbers come
from `GPU_BENCHMARK.csv`, `SCREEN_RANKING.csv`, `HF_FAILURES.csv`, `DECISION_TABLE.csv`,
`DECISION_REPORT.json`, `FREQUENCY_REFERENCE.csv`, `SCREEN_BASELINE.csv`.

## 1. Does current SCREEN actually solve through 10 kHz?

**No.** Zero SCREEN rows above 10 kHz in the last 10 days (`SCREEN_BASELINE.csv`: 241 screen
groups, 17 509 rows). 17 101 of those rows are 18 frequencies at **8 000 Hz**, because the active
v11 briefs set `band_hi_hz: 8000` and `mode_freqs` only ever clips the top edge downward
(`config.py:1888-1890`). 10 kHz is the frozen grid's ceiling, not the deployed policy.

## 2. Can 12 kHz run reliably on the current GPU?

**Yes, for every design in the set.** 24 designs × 2 mesh specs preflighted on CPU (0 refusals);
**160 of 161** GPU evaluations succeeded, 0 OOM, 0 refusals, up to **18 439 quarter DOF**,
dedicated-VRAM delta ≤ **2.8 GiB** on the 8 GB RTX 4060. The single failure was not memory: a
53-frequency dense solve at 18 439 DOF exceeded the solver's **900 s per-solve timeout** at 52/53
frequencies (see Q9).

## 3. How much slower is 12 kHz?

Median per candidate, same designs and brief (wall = mesh + solve + metrics):

| arm | freqs | wall | solve | vs F0 | candidates/hour |
|---|---:|---:|---:|---:|---:|
| F0 (10 kHz) | 12 | 40.3 s | 32.6 s | 1.00 | 89 |
| F0M (12 kHz mesh) | 13 | 72.2 s | 65.2 s | 1.79× | 50 |
| F1 (19) | 19 | 95.6 s | 91.5 s | **2.37×** | 38 |
| FA (21) | 21 | 106.8 s | 98.1 s | 2.65× | 34 |
| FB (27) | 27 | 130.0 s | 125.6 s | 3.23× | 28 |
| F2 (29) | 29 | 147.0 s | 137.7 s | **3.65×** | 24 |
| F3 (53) | 53 | 268.9 s | 251.2 s | 6.68× | 13 |

The deployed 8 kHz screen (18 f) costs 15–37 s of solve per candidate depending on cohort
(`SCREEN_BASELINE.csv`), so a 12 kHz screen is ≈2.5–6× deployed at 19–29 tones (≈2.5–16× for the 53-tone reference). **The mesh is the cost**: at the
same 13 frequencies the 12 kHz mesh alone is 1.79×; six extra samples on top cost +32 %.

## 4. Is 19 points sufficient?

**For ranking, almost; for defect detection, no.** Pooled Spearman vs the dense reference: 0.914
(+0.082 over F0, under the pre-registered +0.10 bar). Top-3 recall 1.0 in three cohorts, 0.667 in
morph (no better than F0 there). Mean J error −0.05…+0.25, max |ΔJ| 0.60. It catches 5 of the 6 HF
beam-collapse defects but raises **1 false alarm**, which the pre-registered rule forbids.

## 5. Is 29 points materially better?

**Yes on this evidence, at 1.54× the cost of 19.** Pooled Spearman **0.957** (+0.125 → passes),
top-3 recall **1.0 in three cohorts and 0.667 in morph (equal to F0 — it loses no finalist F0
kept)**, HF defects **6/6 with 0 false positives**, mean J error
−0.24…+0.01, max |ΔJ| 0.44. It is the only 12 kHz arm that clears both the selection and the
defect criteria. It still costs **3.65×**.

## 6. Which HF defects were newly detected?

Six of the 24 designs have a **high-frequency beam collapse** (H beamwidth at 10–12 kHz falls to
**0.46–0.585×** its 1–4 kHz width; `HF_FAILURES.csv`). The 10 kHz 12-point grid and the 12 kHz mesh
with 10 kHz sampling have **fewer than three samples in 8–12 kHz and are labelled unassessable —
they cannot see the defect at all**, not "they looked and it was fine". 19 points see 5/6 (+1 false
alarm), 21 and 27 add nothing (5/6, 1 FP each), 29 points see 6/6 with no false alarm. No notch,
ripple or DI-range defect met its threshold in this set; beamwidth collapse is the failure mode that
mattered.

## 7. What effect did 12 kHz have on ranking?

Pooled Spearman against the dense reference: **F0 0.832 → F1 0.914 → F2 0.957** (F3 = 1.0 by
construction). F0's misses are systematic: it *under-scores* by 0.87–1.62 J and loses a true top-3
finalist in three of four cohorts (`room` even has a false negative in its top-5). The gain is real
but modest, and most of the J shift is the **mesh**, not the tone list: at fixed 10 kHz sampling the
12 kHz mesh moves J by −0.44…+0.70, while 12→19→29 tones on that mesh move it by ≤0.60.

**Detecting a defect is not the same as demoting it.** The morph design with the beam collapse
(n60, 0.585× width) ranks **first** under F0, F1, F2 and F3 alike. The 12 kHz solve exposes the
failure, but J barely penalises it: 8–12 kHz is ~6 % of a per-frequency mean and no `hf_floor` term
is declared in these briefs. So on this evidence a 12 kHz screen buys the *diagnostic*, not a
different shortlist — changing that needs an HF-weighted objective term, which is a new score
identity and outside this pass.

## 8. What is the real memory limit?

Measured, not modelled: **median 0.8 GiB, maximum 2.8 GiB dedicated delta at 18 439 quarter DOF**
with `cuda_fused`, 512-pt balloon, 73 angles — comfortable on the 8 GB card. The calibrated model
(`FUSED_CUDA_MEASURED_ANCHORS`) is **not usable as a 12 kHz gate**: at 12 183 DOF it interpolates to
≈1.8 GiB while the fused ceiling harness measured 4 744 MiB (2.6× under-prediction). DOF is the
memory driver; the 24 k cap is the binding limit, not VRAM.

## 9. Which cases remain unsupported?

* **Very large horns**: a 0.28 m² horn needs ~34 k DOF at 12 kHz — outside 8 GB at any cap.
* **Dense reference at ≥18 k DOF**: a 53-frequency solve exceeded the default `solve.timeout_s`
  of 900 s (52/53 frequencies). Dense/finalist 12 kHz work on big designs needs ≥1200 s.
* **MEH**: at a 12 kHz request the rigid walls validate only to ~6.0 kHz (`MEH_M8_2026-10-31.md`,
  re-confirmed by `tools/shape_check.py`). Excluded from the 12 kHz screen class.
* **Above f11** (≈5.6 kHz for the 35.8 mm exit, ≈7.9 kHz for 1″): a uniform-velocity source is not a
  compression driver; 8–12 kHz compares geometries, not driver output.
* **WDDM shared-memory spill** is not observable per process on Windows; only dedicated VRAM is
  reported.
* A mesh-only control at F0's frequencies is not constructible (`f_max == max(freqs)`), so the mesh
  term is bounded, not isolated (README §4).

## 10. What default was adopted, if any?

**None. The default stays 8 kHz / frozen grids.** No arm passed all four pre-registered criteria:
F2 passed selection (0.957, +0.125), defect detection (6/6, 0 FP) and mesh convergence
(0.012 dB / 0.12°), but failed cost at 3.65× against a 2.0× bar; the 12 kHz mesh alone is 1.79×, so
no compliant 12 kHz policy exists on this GPU. `solve.screen_grid` and `SCREEN_GRID_PROFILES`
(`hf12k_screen_v1`, 19 points) ship **opt-in**, and the measurement says an HF-focused campaign
should use the 29-point form (`points_per_octave: 6`), not the 19-point profile.

## 11. What changes are required for integration?

See `HANDOVER_INTEGRATION.md`: two source files (`config.py` feature, `warmstart.py` guard), three
test files, one tool, this evidence directory. No mesh or `design/families.py` edits, no
`FREQ_GRIDS` change, no objective change, no git mutation from this pass.

## 12. What are the remaining numerical risks?

* Mesh and sampling are coupled through `f_max`; J is **not** comparable across a mesh change
  (measured spread up to 2.8 J on the same designs).
* The dense reference is a 53-point grid (6 samples above 10 kHz); a narrower feature is invisible,
  so "no defect" means "none at this resolution".
* Six designs per cohort: top-3/top-5 statistics are coarse, and a single false positive moves
  criterion 2 from pass to fail. That is the rule as pre-registered; with 24 designs it is the
  correct reading, but it is not a high-power test.
* Above f11 the source model, not the solver, is the uncertainty.
* Dedicated VRAM only; a driver-side spill would not show in these numbers.
* Greedy HF comb arms (FA/FB) matched 19 points, not 29 — HF point *placement* matters as much as
  count, so do not generalise "more HF points is better" from 29 points alone.
