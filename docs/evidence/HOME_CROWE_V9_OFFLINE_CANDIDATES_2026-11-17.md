# HOME / CROWE v9 offline candidates — WP3 objective/brief-truth replay

**Date:** 2026-11-17 · **Lane:** WP3 (implementation) · **Repo:** `C:/Users/hunte/Hrns/hornlab-search`
· **Status:** `[measured]` stored BEM responses replayed; `[derived]` recomputed metrics/scores;
`[proposed]` v9 corridor scenarios; `[unavailable]` anything not stored. Zero GPU, zero solver,
zero queued jobs. No stored run/result was written.

Tool: `tools/analysis/brief_truth_replay.py` · Tests: `tests/test_brief_truth_replay.py`
· Candidate briefs and matrices: `scratch/home_v9_offline_2026-11-17/`

---

## 1. Bottom line

1. **Legacy identity replay is exact `[measured]`.** Both named designs replay through the canonical
   pathway (`objective.replay.replay_run_dir` → `search.evaluate.metrics_from_response` →
   `objective_v7`) to their captured J with **delta = +0.000e+00** and **max |term delta| = 0.000e+00**.
   The November-17 2×2 matrix is reproduced to the 6 displayed decimals.
2. **The legacy November-17 finding survives under the implemented v9 corridor `[derived]`.** On
   both horns the DI-slope term dominates: at 0 dB/decade target and weight 1 it is 77 % (Crowe) and
   92 % (Klangfilm-Lame) of v9 J. Setting the slope weight to 0 collapses J from 9.5767 to 2.1727
   (Crowe) and 11.1114 to 0.9404 (Klangfilm).
3. **The corridor's `preferred_deg` is not scored inside `[min, max]` `[derived]`.** For these two
   stored designs the measured H beamwidth stays at/under 90° and mostly above 60° inside the scored
   band, so a 90→70 preferred taper and a constant-80 preferred corridor give **identical** J. Only
   the bounds bite. The scored corridor is therefore `[60, 90] H / [40, 60] V`, not the descriptive
   80 × 50 nominal.
4. **Frequency-grid stability `[derived]`.** On 60 stored same-mesh screen/verify pairs, v9 J differs
   between the 18-point and 29-point solved grids by sd 0.208 (all) / 0.112 (best 28), rank
   correlation 0.986 / 0.893. On the common interpolated analysis grids the screen-vs-verify sd is
   0.193 (58 pt) / 0.190 (116 pt); 58→116 changes J by sd 0.026–0.032, rank 0.996. **Interpolation
   removes grid-definition noise; it does not create acoustic resolution.**
5. No production default changed; no v9 objective became a default; original stored v7 J unchanged
   (source hashes identical before/after).

---

## 2. Provenance and method

### 2.1 Capture (tool writes `provenance` into every JSON)

`git rev-parse HEAD` at every run:

```
8b255f074cb12e80a0a53fa2176dfba1d5802f75
```

`git status --porcelain` (37 entries at capture; pasted verbatim, complete list also in
`identity/identity_replay.json`, `scenarios/replay_matrix.json`, `grid/grid_stability.json`):

```
 M docs/CONTINUITY.md
 M docs/INDEX.md
 M docs/knowledge/README.md
 M hornlab_search/cli.py
 M hornlab_search/config.py
 M hornlab_search/gui/jobs.py
 M hornlab_search/objective/scalar_v9.py
 M hornlab_search/search/cma.py
 M hornlab_search/search/evaluate.py
 M scratch/fable_architecture/space_cards/b3_soft.json
 M scratch/fable_architecture/space_cards/b3_soft.md
 M scratch/fable_architecture/space_cards/hl__biradial_es_style_v7.json
 M scratch/fable_architecture/space_cards/hl__biradial_es_style_v7.md
 M scratch/fable_architecture/space_cards/hl__crowe_x_osse_cd_v7.json
 M scratch/fable_architecture/space_cards/hl__crowe_x_osse_cd_v7.md
 M scratch/fable_architecture/space_cards/hl__osse_rrect_fold_warm_v7.json
 M scratch/fable_architecture/space_cards/hl__osse_rrect_fold_warm_v7.md
 M scratch/fable_architecture/space_cards/summary.json
 M tests/test_search_qd_failure_isolation.py
 M tests/test_targets.py
 M tools/analysis/space_card.py
?? .claude/worktrees/
?? docs/evidence/PATTERN_QUALITY_READONLY_2026-11-17.md
?? docs/evidence/pattern_quality_readonly/
?? docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md
?? examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1_c200w.yaml
?? hornlab_search/metrics/pattern_quality.py
?? tests/test_brief_truth_replay.py
?? tests/test_cli_finalist_mode.py
?? tests/test_gui_jobs_finalist_mode.py
?? tests/test_metrics_pattern_quality.py
?? tests/test_search_record_gate.py
?? tests/test_tools_analysis_space_card_data_agrees.py
?? tests/test_v9_polar_window.py
?? tools/analysis/brief_truth_replay.py
?? tools/analysis/crowe_mesh_truth.py
?? tools/analysis/pattern_quality_report.py
```

**Concurrent-lane interaction (checked, not guessed).** The uncommitted edits in the scoring path
are: `search/evaluate.py` = opt-in record-gate annotation only (no metric or score change);
`config.py` = record-gate / validation additions; `objective/scalar_v9.py` = optional
`ripple_window` / `oa_excess_tol` (both absent from every candidate here). None touches v7 scoring,
which is why the v7 identity replay is exact under this tree. The v9 numbers below are results of
**the tree as it stands** (`8b255f0` + those edits); if the integrator commits a different
`scalar_v9.py`, re-run the tool.

### 2.2 Commands actually run (PowerShell 5.1; thread caps set in every invocation)

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe tools/analysis/brief_truth_replay.py identity --out scratch/home_v9_offline_2026-11-17/identity
.venv\Scripts\python.exe tools/analysis/brief_truth_replay.py scenarios --briefs `
  scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v700.yaml `
  scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1000.yaml `
  scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1250.yaml `
  scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1000_slope0.yaml `
  scratch/home_v9_offline_2026-11-17/home_v9_corridor_h80flat_v1000.yaml `
  --out scratch/home_v9_offline_2026-11-17/scenarios
.venv\Scripts\python.exe tools/analysis/brief_truth_replay.py grid --brief scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1000.yaml --runs runs/study-* --out scratch/home_v9_offline_2026-11-17/grid
.venv\Scripts\python.exe -m pytest tests/test_brief_truth_replay.py -q -p no:cacheprovider
```

Exit codes: `identity` 0, `scenarios` 0, `grid` 0 (417 s wall), `pytest` 0.
Every command reports `BACKEND_GUARD installed=11 calls=0`, i.e. every solver/backend factory,
store writer, `subprocess` and `os.system` was patched to raise and **none was called**.

### 2.3 Source immutability guard

Every `response.npz` read for a score is SHA-256-hashed before and after; a mismatch aborts.
Reported in the JSON `source_guard` blocks:

| run | files hashed | unchanged |
|---|---:|---|
| identity | 2 `response.npz` | yes |
| scenarios | 2 `response.npz` | yes |
| grid | 120 `response.npz` (60 pairs × 2 sides) | yes |

The test additionally hashes both `response.npz` **and** both `best.json` around
`BTR.identity(...)` and asserts equality.

---

## 3. Use 1 — legacy identity replay `[measured]`

Pasted output (`scratch/home_v9_offline_2026-11-17/identity/run.log`):

```
[identity] crowe_es600: recomputed J = 16.918176135266869  stored = 16.918176135266869  delta = +0.000e+00 (rel 0.000e+00)  max|term delta| = 0.000e+00  -> PASS
[identity] klangfilm_lame: recomputed J = 8.923616737684702  stored = 8.923616737684702  delta = +0.000e+00 (rel 0.000e+00)  max|term delta| = 0.000e+00  -> PASS

========================================================================================================
2x2 NOVEMBER-17 BRIEF RE-SCORE (J per design x brief; a same-brief column is the only rank)
========================================================================================================
design                       base           smooth     own cell
crowe_es600             16.918176         6.836182         base
klangfilm_lame          22.782312         8.923617       smooth

wrote C:\Users\hunte\Hrns\hornlab-search\scratch\home_v9_offline_2026-11-17\identity\identity_replay.json
BACKEND_GUARD installed=11 calls=0
```

**Residuals:** absolute delta `0.0`, relative `0.0`, term-level max `0.0` for both designs
(target was `~1e-9` relative). The tool asserts `|ΔJ| ≤ 1e-9·max(|J|,1)` and each per-term delta
`≤ 1e-9`, and fails loudly otherwise (no papering over).

**Why this is trusted:** each design is replayed under its **own captured run brief**
(`config.load_config` → `brief:`), metrics are **regenerated** from `response.npz`
(`regenerate_metrics=True`, `diagnostics.stored_metrics_used = False`), and the 2×2 cells match the
November-17 report to 6 decimals (`NOV17_J_TOL = 1e-5`).

### 3.1 Per-term identity breakdown (raw = normalized × tolerance; contribution = weight × normalized)

| design | brief | key | raw | weight | tol | contribution |
|---|---|---|---:|---:|---:|---:|
| Crowe | base | cov | 10.124253 | 1.00 | 3.0 | 3.374751 |
| Crowe | base | rip | 0.067554 | 1.00 | 1.0 | 0.067554 |
| Crowe | base | di | 1.720676 | 0.30 | 0.4 | 1.290507 |
| Crowe | base | dislope | 66.636129 | 1.00 | 9.0 | 7.404014 |
| Crowe | base | flat | 0.560593 | 0.50 | 1.5 | 0.186864 |
| Crowe | base | load | 0.000000 | 1.00 | 0.3 | 0.000000 |
| Crowe | base | distd | 2.356361 | 0.50 | 2.0 | 0.589090 |
| Crowe | base | diag | 7.421059 | 1.00 | 2.0 | 3.710529 |
| Crowe | base | flat_cv | 0.442298 | 1.00 | 1.5 | 0.294865 |
| **Crowe** | **base** | **J** | | | | **16.918176** |
| Crowe | smooth | cov | 8.450271 | 1.00 | 8.0 | 1.056284 |
| Crowe | smooth | di | 0.000000 | 0.00 | 0.4 | 0.000000 |
| Crowe | smooth | dislope | 10.005174 | 1.00 | 9.0 | 1.111686 |
| Crowe | smooth | distd | 2.356361 | 1.00 | 2.0 | 1.178180 |
| Crowe | smooth | diag | 5.881494 | 1.00 | 2.0 | 2.940747 |
| **Crowe** | **smooth** | **J** | | | | **6.836182** |
| Klangfilm | base | cov | 15.316083 | 1.00 | 3.0 | 5.105361 |
| Klangfilm | base | di | 1.627507 | 0.30 | 0.4 | 1.220630 |
| Klangfilm | base | dislope | 91.538458 | 1.00 | 9.0 | 10.170940 |
| Klangfilm | base | diag | 11.069275 | 1.00 | 2.0 | 5.534638 |
| **Klangfilm** | **base** | **J** | | | | **22.782312** |
| Klangfilm | smooth | cov | 11.352960 | 1.00 | 8.0 | 1.419120 |
| Klangfilm | smooth | dislope | 20.862726 | 1.00 | 9.0 | 2.318081 |
| Klangfilm | smooth | diag | 7.515258 | 1.00 | 2.0 | 3.757629 |
| **Klangfilm** | **smooth** | **J** | | | | **8.923617** |

(Full 36-row table, including the unchanged `rip`/`flat`/`load`/`flat_cv` rows, is
`identity/identity_terms.csv`.)

---

## 4. Use 2 — experimental v9 scoring view `[proposed]` (NOT-QUEUED)

### 4.1 Candidate briefs — `scratch/home_v9_offline_2026-11-17/`

| file | H corridor (preferred / min / max) | V onset | dislope weight | status |
|---|---|---|---|---|
| `home_v9_corridor_h90_70_v700.yaml` | 90 → 70 / 60 / 90 | 700 Hz | 1.0 | `[proposed]` NOT-QUEUED |
| `home_v9_corridor_h90_70_v1000.yaml` | 90 → 70 / 60 / 90 | 1000 Hz | 1.0 | `[proposed]` NOT-QUEUED |
| `home_v9_corridor_h90_70_v1250.yaml` | 90 → 70 / 60 / 90 | 1250 Hz | 1.0 | `[proposed]` NOT-QUEUED |
| `home_v9_corridor_h90_70_v1000_slope0.yaml` | 90 → 70 / 60 / 90 | 1000 Hz | 0.0 | `[proposed]` NOT-QUEUED |
| `home_v9_corridor_h80flat_v1000.yaml` | 80 flat / 60 / 90 | 1000 Hz | 1.0 | `[proposed]` NOT-QUEUED |

Schema: **implemented** `target.coverage_profile` — `mode: corridor`, `interpolation:
log_frequency`, per-anchor `(hz, preferred_deg, min_deg, max_deg)`; a corridor needs ≥ 2 anchors with
`0 < min ≤ preferred ≤ max`. Objective v9 with `flat_band: scored`, `cov_v_weight: 0.5`,
`cov_narrow_ratio: 2.0`, `cov_below_f0: mask`, and the v9 tolerances
`cov_profile 3.0 / rip 1.0 / flat 1.5 / load 0.3 / dislope 9.0 / di_roughness 0.5 / flat_cv 1.5`.
No `bw8k_floor`, no `hf_floor` (the latter remains the supported optional HF channel).
Descriptive nominal `coverage_h_deg: 80 / coverage_v_deg: 50` is carried **separately** from the
scored corridor; it is not the scored shape. Every file carries `[proposed] OFFLINE / NOT-QUEUED` in
its header.

All five load through `config.load_brief` → `Target.from_dict` → `V9Params.from_block` in
`tests/test_brief_truth_replay.py`. The 2026-11-16 RFC's early `frequency_envelope` example is not
used (the test asserts the key form is absent).

### 4.2 Pasted output (first cell, plus the refusal line; full log in `scenarios/run.log`)

```
crowe_es600      home_v9_corridor_h90_70_v700               v9 J=9.96094006749582     status=exact_complete
  cov_v_weight=0.5 flat_band=scored below=mask narrow=2.0 onsetH=700.0 onsetV=700.0 di_src=none(v9 has no scored DI level) di_slope_tgt=0.0 measured_slope=8.163095566628673
  diag_scored=False distd_weight=0 n_in_band=16 n_cov_H=13 n_cov_V=13
  8k: objective.bw8k_floor refused under v9; the corridor min_deg is the HF narrow-side constraint; no hf_floor declared; measured (unscored) BW @ 8000 Hz = 48.10 H / 35.18 V deg
  contributions: {"cov_profile": 1.130344, "di_roughness": 0.939323, "diag": 0.0, "dislope": 7.404014, "distd": 0.0, "flat": 0.186864, "flat_cv": 0.294865, "load": 0.0, "rip": 0.005529}
...
[cross-brief pooled ranking] REFUSED: raw J is not a common ranking across objective versions or briefs: versions=[9], 5 distinct brief hash(es), names=['home_v9_corridor_h80flat_v1000', 'home_v9_corridor_h90_70_v1000', 'home_v9_corridor_h90_70_v1000_slope0', 'home_v9_corridor_h90_70_v1250', 'home_v9_corridor_h90_70_v700']. Compare only the same-brief column, or decompose the terms.
```

A bare `--response <path/to/response.npz>` input is also accepted (diagnostic cell, no stored J to
compare). It is routed through the same canonical run-dir adapter on a temporary copy, so the
production `sin(theta)` balloon quadrature is preserved: the bare Crowe response under `v1000`
reproduces the run-dir cell's J (`9.57672093289535`) to 1e-12. Calling `compute_metrics` on the raw
theta-phi balloon would have been ~7 dB wrong in DI, which is why the tool never does that.

### 4.3 v9 J matrix (same-brief column only; J across briefs is a different objective)

| design | own v7 J (stored) | v700 | v1000 | v1250 | v1000 slope0 | h80flat v1000 |
|---|---:|---:|---:|---:|---:|---:|
| Crowe ES-600 | 16.918176 | 9.960940 | 9.576721 | 9.273817 | **2.172707** | 9.576721 |
| Klangfilm-Lame | 8.923617 | 11.398108 | 11.111374 | 11.000010 | **0.940435** | 11.111374 |

`[derived]`. Note the two `h80flat` cells are identical to `v1000` — see §4.6.

### 4.4 Per-term breakdown — v1000 corridor (raw / weight / tolerance / normalized / contribution)

Crowe ES-600:

| key | raw | weight | tol | normalized | contribution | share of J |
|---|---:|---:|---:|---:|---:|---:|
| cov_profile | 2.238375 | 1.00 | 3.0 | 0.746125 | 0.746125 | 7.8 % |
| rip | 0.005529 | 1.00 | 1.0 | 0.005529 | 0.005529 | 0.1 % |
| flat | 0.560593 | 0.50 | 1.5 | 0.373729 | 0.186864 | 2.0 % |
| load | 0.000000 | 1.00 | 0.3 | 0.000000 | 0.000000 | 0.0 % |
| dislope | 66.636129 | 1.00 | 9.0 | 7.404014 | 7.404014 | **77.3 %** |
| di_roughness | 0.469662 | 1.00 | 0.5 | 0.939323 | 0.939323 | 9.8 % |
| flat_cv | 0.442298 | 1.00 | 1.5 | 0.294865 | 0.294865 | 3.1 % |
| diag | 7.421059 | 0 (raw, unweighted) | — | — | 0.000000 | — |
| distd | 2.356361 | 0 (raw, unweighted) | — | — | 0.000000 | — |
| **J** | | | | | **9.576721** | |

Klangfilm-Lame:

| key | raw | weight | tol | normalized | contribution | share of J |
|---|---:|---:|---:|---:|---:|---:|
| cov_profile | 1.614225 | 1.00 | 3.0 | 0.538075 | 0.538075 | 4.8 % |
| rip | 0.000939 | 1.00 | 1.0 | 0.000939 | 0.000939 | 0.0 % |
| flat | 0.090067 | 0.50 | 1.5 | 0.060045 | 0.030022 | 0.3 % |
| load | 0.000000 | 1.00 | 0.3 | 0.000000 | 0.000000 | 0.0 % |
| dislope | 91.538458 | 1.00 | 9.0 | 10.170940 | 10.170940 | **91.5 %** |
| di_roughness | 0.177486 | 1.00 | 0.5 | 0.354972 | 0.354972 | 3.2 % |
| flat_cv | 0.024639 | 1.00 | 1.5 | 0.016426 | 0.016426 | 0.1 % |
| diag | 11.069275 | 0 (raw, unweighted) | — | — | 0.000000 | — |
| distd | 2.712176 | 0 (raw, unweighted) | — | — | 0.000000 | — |
| **J** | | | | | **11.111374** | |

Slope-weight-0 sensitivity (same corridor, `dislope` weight 0.0): every other term is unchanged;
J drops to **2.172707** (Crowe) / **0.940435** (Klangfilm). This isolates exactly what the 0 dB/dec
assumption costs: 7.404014 / 10.170940 contribution units.

### 4.5 Scoring facts per cell (all v9 cells; from `replay_matrix.csv`/JSON)

| design | brief | cov_v_w | flat_band | below | onset H / V | n_cov H / V | DI level | DI slope target | measured slope | 8 kHz condition |
|---|---|---:|---|---|---|---:|---|---:|---:|---|
| Crowe | v700 | 0.5 | scored | mask | 700 / 700 | 13 / 13 | none (v9) | 0.0 | +8.163 dB/dec | floor refused; measured 48.10 H / 35.18 V @ 8000 Hz |
| Crowe | v1000 | 0.5 | scored | mask | 700 / 1000 | 13 / 12 | none (v9) | 0.0 | +8.163 dB/dec | same |
| Crowe | v1250 | 0.5 | scored | mask | 700 / 1250 | 13 / 11 | none (v9) | 0.0 | +8.163 dB/dec | same |
| Crowe | v1000 slope0 | 0.5 | scored | mask | 700 / 1000 | 13 / 12 | none (v9) | 0.0 | +8.163 dB/dec | same |
| Crowe | h80flat v1000 | 0.5 | scored | mask | 700 / 1000 | 13 / 12 | none (v9) | 0.0 | +8.163 dB/dec | same |
| Klangfilm | v700 | 0.5 | scored | mask | 700 / 700 | 13 / 13 | none (v9) | 0.0 | +9.568 dB/dec | floor refused; measured 39.48 H / 33.85 V @ 8000 Hz |
| Klangfilm | v1000 | 0.5 | scored | mask | 700 / 1000 | 13 / 12 | none (v9) | 0.0 | +9.568 dB/dec | same |
| Klangfilm | v1250 | 0.5 | scored | mask | 700 / 1250 | 13 / 11 | none (v9) | 0.0 | +9.568 dB/dec | same |
| Klangfilm | v1000 slope0 | 0.5 | scored | mask | 700 / 1000 | 13 / 12 | none (v9) | 0.0 | +9.568 dB/dec | same |
| Klangfilm | h80flat v1000 | 0.5 | scored | mask | 700 / 1000 | 13 / 12 | none (v9) | 0.0 | +9.568 dB/dec | same |

`diag_scored = False`, `distd_weight = 0` in every v9 cell (owner-locked raw diagnostics).
`cov_below_f0: mask` excludes below-onset frequencies entirely; `one_sided` is **not** used here.
`n_solved_in_band = 16` for all cells (band 350–8000 Hz on the 18-point solved grid); `n_cov_H/V`
is the coverage-scored count after each plane's onset (13/13, 13/12, 13/11 for V onset 700/1000/1250).
The `8 kHz condition` text for v9 is exactly "objective.bw8k_floor refused under v9; the corridor
min_deg is the HF narrow-side constraint; no hf_floor declared; measured (unscored) BW @ 8000 Hz =
<value>"; Klangfilm's measured values there are 39.48 H / 33.85 V deg.

### 4.6 Target profile at sampled frequencies `[proposed]` (log-linear in frequency)

| f (Hz) | h90_70 H pref [min,max] | h80flat H pref [min,max] | V pref [min,max] |
|---:|---|---|---|
| 700.00 | 90.000 [60, 90] | 80.000 [60, 90] | 50 [40, 60] |
| 827.75 | 88.624 [60, 90] | 80.000 [60, 90] | 50 [40, 60] |
| 1065.04 | 86.554 [60, 90] | 80.000 [60, 90] | 50 [40, 60] |
| 2268.63 | 80.347 [60, 90] | 80.000 [60, 90] | 50 [40, 60] |
| 4832.36 | 74.139 [60, 90] | 80.000 [60, 90] | 50 [40, 60] |
| 8000.00 | 70.000 [60, 90] | 80.000 [60, 90] | 50 [40, 60] |

Per-frequency values are also in `replay_matrix.json` →
`facts.target_profile_at_solved_hz` for every cell.

### 4.7 Observed H/V pattern `[derived]` (same stored responses; target only changes the window)

| f (Hz) | Crowe H / V (deg) | Klangfilm H / V (deg) |
|---:|---:|---:|
| 643.33 | 96.22 / 180.00 | 120.77 / 144.03 |
| 827.75 | 89.32 / 129.27 | 104.82 / 118.32 |
| 1065.04 | 87.37 / 119.22 | 96.37 / 95.61 |
| 1370.35 | 83.87 / 97.17 | 92.10 / 87.27 |
| 2268.63 | 81.00 / 82.25 | 75.87 / 66.02 |
| 3311.0 | 66.87 / 66.43 | 63.84 / 54.11 |
| 4832.36 | 64.58 / 51.38 | 52.48 / 43.85 |
| 6217.63 | 59.69 / 41.52 | 45.62 / 38.48 |
| 8000.0 | 48.10 / 35.18 | 39.48 / 33.85 |

Consequences visible in the numbers:

* **Preferred is not scored inside the corridor.** At every scored frequency the Crowe H beamwidth
  is ≤ 90° (89.32° at 827.75 Hz is the maximum), so it is always inside or below the corridor.
  Klangfilm H is above 90° only at 827–1370 Hz and inside or below elsewhere. Inside `[min,max]`
  the v9 corridor cost is 0 regardless of `preferred`, so a 90→70 taper and flat-80 produce the same
  `cov_profile` (2.238375 / 1.614225) and identical J.
* **V onset changes what the wide low-frequency V pattern costs.** 827.75 Hz V = 129° (Crowe) /
  118° (Klangfilm) is far above the 60° upper bound. Masking it at 1000 Hz lowers `cov_profile`
  contribution 1.130344 → 0.746125 (Crowe) and 0.824809 → 0.538075 (Klangfilm); masking 1065.04 Hz
  too at 1250 Hz lowers it further to 0.443221 / 0.426710.
* **The HF lower bound is binding.** At 8000 Hz both planes sit below the corridor minima
  (H 60°, V 40°), so these designs are charged for HF narrowing through `cov_profile` — which is
  exactly the role v9 assigns to `min_deg` instead of a `bw8k_floor`.

`[unavailable]`: no solved data at 1000/1250 Hz changes the physics; the V onset variants are
scoring-window scenarios on the same stored responses. No new acoustic information was created.

---

## 5. Use 3 — frequency-grid stability `[derived]`

Method: 60 stored same-mesh screen/verify pairs (`runs/study-*/screen/designs/<h>` vs
`runs/study-*/verify/designs/<h>`; same mesh, 18 vs 29 solved frequencies). Each side is scored
natively and on the canonical v9 `objective.score_grid` (`dense_log`, PCHIP in log f, 58 and 116
points) through `objective.replay`, using `rescore_identity.floor_stats` for the statistics.
Runtime 417 s, zero GPU.

Pasted output (`grid/run.log`):

```
========================================================================================================
FREQUENCY-GRID STABILITY under home_v9_corridor_h90_70_v1000 (v9)
========================================================================================================
[pairs] 60 same-mesh screen/verify pairs; solved freqs: screen [18] samples, verify [29] samples
[solved    ] n=60 mean(screen-verify)=-0.16698 sd_all=0.20832 spearman_all=0.9859 sd_top28=0.11185 spearman_top=0.8927
[dense_58  ] n=60 mean(screen-verify)=-0.03991 sd_all=0.19268 spearman_all=0.9909 sd_top28=0.11409 spearman_top=0.9584
[dense_116 ] n=60 mean(screen-verify)=-0.04451 sd_all=0.19025 spearman_all=0.9917 sd_top28=0.11326 spearman_top=0.9589
NOTE: the dense grid is PCHIP interpolation of the stored solved response; it does NOT create acoustic resolution.
      dense analysis points = [58, 116] vs solved [18]/[29] samples. Only a future denser SOLVED pass can confirm missing narrow resonances.

wrote C:\Users\hunte\Hrns\hornlab-search\scratch\home_v9_offline_2026-11-17\grid\grid_stability.json, grid_pairs.csv, grid_term_sensitivity.csv
BACKEND_GUARD installed=11 calls=0
```

### 5.1 Screen-vs-verify score differences (the frequency part of the noise floor)

| grid | n | mean Δ (screen − verify) | sd all | sd best-28 | rank corr all | rank corr best-28 |
|---|---:|---:|---:|---:|---:|---:|
| 18 vs 29 solved (native) | 60 | −0.16698 | 0.20832 | 0.11185 | 0.9859 | 0.8927 |
| common dense 58 | 60 | −0.03991 | 0.19268 | 0.11409 | 0.9909 | 0.9584 |
| common dense 116 | 60 | −0.04451 | 0.19025 | 0.11326 | 0.9917 | 0.9589 |

### 5.2 Definition change (same side, same response)

| comparison | n | mean Δ | sd all | sd best-28 | rank corr all | rank corr best-28 |
|---|---:|---:|---:|---:|---:|---:|
| dense 58 − solved / screen | 60 | +0.34328 | 0.26402 | 0.16886 | 0.9741 | 0.8429 |
| dense 116 − solved / screen | 60 | +0.32921 | 0.26223 | 0.16553 | 0.9736 | 0.8347 |
| dense 58 − solved / verify | 60 | +0.21620 | 0.19802 | 0.16016 | 0.9854 | 0.9009 |
| dense 116 − solved / verify | 60 | +0.20673 | 0.19637 | 0.15211 | 0.9831 | 0.8894 |
| **dense 116 − dense 58 / screen** | 60 | **−0.01407** | **0.02574** | **0.01258** | **0.9996** | **0.9962** |
| **dense 116 − dense 58 / verify** | 60 | **−0.00947** | **0.03177** | **0.01870** | **0.9994** | **0.9967** |

Convergence: 58 → 116 points moves v9 J by sd 0.026–0.032 with rank 0.999 — i.e. the score is
grid-definition-stable by 58 points, consistent with FABLE N3 (0.032 all / 0.019 top, different
corridor/weights). The residual from *solved* frequency count (18 vs 29) is sd 0.208 all / 0.112
top — **not removable by interpolation**.

### 5.3 Rank stability from the solved grid to the common dense grids

| side / change | n | Spearman | max rank shift | max shift in top 28 |
|---|---:|---:|---:|---:|
| screen, solved → dense 58 | 60 | 0.9741 | 14 | 1 |
| screen, solved → dense 116 | 60 | 0.9736 | 15 | 1 |
| verify, solved → dense 58 | 60 | 0.9854 | 12 | 1 |
| verify, solved → dense 116 | 60 | 0.9831 | 12 | 1 |

Near-best rank is stable (≤ 1 place) even where the value moves; mid/lower ranks move more.

### 5.4 Per-term sensitivity (weighted contribution, mean / sd of screen − verify)

| term | solved grid | dense 58 | dense 116 |
|---|---:|---:|---:|
| cov_profile | −0.02156 / 0.05936 | +0.00740 / 0.01730 | +0.00696 / 0.01707 |
| rip | −0.00868 / 0.00535 | −0.00253 / 0.00337 | −0.00253 / 0.00336 |
| flat | −0.00663 / 0.02355 | −0.01415 / 0.03394 | −0.01472 / 0.03291 |
| load | −0.06903 / 0.10682 | −0.02437 / 0.04387 | −0.02501 / 0.04572 |
| dislope | +0.03771 / 0.14865 | +0.02668 / 0.09454 | +0.02621 / 0.09435 |
| di_roughness | +0.02048 / 0.06638 | −0.00106 / 0.07248 | −0.00014 / 0.07353 |
| flat_cv | −0.11927 / 0.07978 | −0.03188 / 0.09361 | −0.03528 / 0.09172 |

On the native grid the frequency-count residual is carried by `flat_cv`, `load` and `dislope` —
the same terms FABLE N3 found for v7/v9; on the dense grid those shrink and
`di_roughness`/`flat_cv` sd dominates the remaining spread.

### 5.5 Solved sample inventory (what is actually measured)

* Screen: 18 solved frequencies — `250, 315, 400, 500, 643.33, 827.75, 1065.04, 1370.35, 1763.18,
  2268.63, 2573, 2918.96, 3311, 3755.72, 4260, 4832.36, 6217.63, 8000` Hz.
* Verify: 29 solved frequencies on the same mesh (same response identity, more samples).
* Dense analysis points: 58 and 116 — **interpolated**, per side.

> **Interpolation is not resolution.** 58/116 points are PCHIP interpolation of the stored solved
> response; they reduce grid-definition noise and make screen/verify comparable, but they cannot
> reveal an unsolved narrow resonance. Only a future denser **solved** pass can.

---

## 6. Scoring-rule enforcement (tool + tests)

| rule | implementation | test |
|---|---|---|
| Cross-version / cross-brief raw J is not a ranking | `pooled_ranking()` raises `CrossVersionRankingRefused` unless one version **and** one brief hash; `rank_within_brief()` refuses mixed versions | `test_pooled_ranking_refuses_cross_version`, `..._cross_brief_even_within_one_version`, `test_rank_within_brief_...` |
| Cross-target rescoring recomputes target-dependent metrics | every cell replays with `regenerate_metrics=True`; a cross-target cell that reused stored metrics raises `ScoreRuleError`; the v9 cell asserts `stored_metrics_used = False` | `test_v9_cross_target_cell_recomputes_metrics_and_keeps_diag_raw_unweighted` |
| v9 uses `cov_profile` / `di_roughness`; `diag`/`distd` raw, unweighted | `term_table()` marks them `unweighted_raw`, contribution 0; J equals the sum of weighted contributions | same test |
| `objective.bw8k_floor` refused under v9 | `refuse_bw8k_floor_under_v9()` + `config.load_brief`/`V9Params.from_block` | `test_bw8k_floor_is_refused_under_v9_by_block_and_by_the_tool`, `test_bw8k_floor_is_refused_under_v9_by_config` |
| Explicit `hf_floor` remains available | `V9Params.weighted_keys()` adds it only when declared | `test_v9_hf_floor_is_accepted_as_its_own_weighted_term` |
| Candidate YAMLs are valid, implemented-schema, NOT-QUEUED | loaded through `config.load_brief`; header/`[proposed]` assertions; anchors, onsets, nominal | `test_candidate_yamls_exist_and_use_the_implemented_schema`, `test_slope_weight_zero_variant_...` |
| Zero backend, zero source mutation | `BackendGuard` (11 patches, 0 calls) + SHA guards | `test_identity_replay_reproduces_stored_j_exactly_and_does_not_mutate_sources` |

Pasted pytest run:

```
$ .venv\Scripts\python.exe -m pytest tests/test_brief_truth_replay.py -q -p no:cacheprovider
..............                                                           [100%]
EXIT=0
```

(The archive-dependent tests are `skipif` only when the local `runs/` archive is absent, and the
candidate-brief tests only when the gitignored `scratch/` briefs are absent. Both are present here,
so all 14 ran and passed. Neither `runs/` nor `scratch/` is part of the repo checkout.)

---

## 7. Acceptance checklist

| requirement | result |
|---|---|
| No stored run/result mutation | 124 `response.npz` hashed before/after: unchanged (`source_guard`) |
| Reproducible zero-GPU comparison | 3 commands, exit 0, `BACKEND_GUARD calls=0` |
| Original v7 stored J unchanged | identity replay delta `0.0`, stored files hashed unchanged |
| No v9 production default changed | candidates are `[proposed]` files under `scratch/`; no `hornlab_search/**` edit |
| Same-brief identity proven | `delta = +0.000e+00`, `max|term delta| = 0.000e+00` |
| Cross-version pooled ranking refused | `CrossVersionRankingRefused` (tool + tests) |
| v9 YAMLs valid through the real loader | 5/5 load via `config.load_brief`; tests pin the schema |
| Frequency fidelity reported distinctly | solved / dense-58 / dense-116 in §5, with the "not resolution" caveat |
| Labels preserved | `[measured]` `[derived]` `[proposed]` `[unavailable]` used throughout |

---

## 8. Open questions

1. **Should the v9 corridor score `preferred` at all if it is never binding?** For these two designs
   a preferred-only corridor is observationally equivalent to a constant corridor. If the owner
   wants a scored *shape*, that is `mode: target` (quadratic against `preferred`) or a narrower
   corridor — a decision, not a measurement.
2. **V onset is a scoring-window choice, not physics.** 1250 Hz simply excludes the wide 827–1065 Hz
   V pattern. Which onset reflects the intended room/crossover is an owner decision.
3. **The DI slope target (0 dB/dec here) still dominates.** A 5 dB/decade target variant (the v7
   `_smooth` assumption) was *not* scored in this pass; only weight 0 was. Both are cheap follow-ups.
4. **Only two stored designs.** Nothing here reranks either run or any family; the grid study is the
   only cohort-level result (60 same-mesh pairs, study runs that skew to better designs).
5. **Constancy / `hf_floor` are untested here.** v9 exposes both; neither was declared in these
   scenarios, and N3 measured that constancy needs a 116-point grid.
6. **Template provenance.** The doc renders `CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md` with a
   mis-encoded arrow in its title; the numbers above come from recomputation, not from that text.

## 9. Next step

Owner review of the five `[proposed]` corridor scenarios (H preferred shape, V onset, slope weight),
then — only on approval — a **zero-solve** broader rescore of one existing run family under the
chosen brief (`brief_truth_replay.py scenarios --runs <run>`), followed by a small GPU pilot
(separate lane, one solve at a time) if the owner wants realised designs rather than stored ones.
