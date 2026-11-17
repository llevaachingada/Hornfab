# Crowe ES-600 vs Klangfilm-Lame — matched v7 brief re-score

**Date:** 2026-11-17 · **Lane:** H · **Scope:** the two named best non-CD designs re-scored under **both** home-landscape v7 briefs from the **stored BEM responses** (no GPU, no solver, no retune, deterministic).
**Script:** `scratch/rescore_crowe_klangfilm_20261117.py` · **Data:** `scratch/rescore_crowe_klangfilm_20261117.results.json`
**Designs:** Crowe ES-600 `22365b569be9` (run `20261115T205453Z-screen-32f7c4`) · Klangfilm-Lame `491efb2132b8` (run `20261116T225543Z-screen-6acf41`).
**Briefs:** BASE `room_landscape_80x50_700_hf1440_v7` · SMOOTH `room_landscape_80x50_700_hf1440_v7_smooth`.

> The stored physical response is unchanged. Every target-dependent metric (coverage, ripple, diagonal, 8 kHz floor, DI level) is **recomputed under each brief's own `Target`**; the run's own stored ripple/diag/floor values are never reused.

---

## 1. Summary — the 2×2 J matrix

| Design | Brief | J | Δ vs own run brief |
|---|---|---:|---:|
| Crowe ES-600 | **base** (own run brief) | **16.918176** | +0.000000 |
| Crowe ES-600 | smooth | **6.836182** | −10.081995 |
| Klangfilm-Lame | base | **22.782312** | +13.858695 |
| Klangfilm-Lame | **smooth** (own run brief) | **8.923617** | +0.000000 |

The two **own-brief** cells are the identity replays: they reproduce the runs' stored best J to the last digit (section 4). The two **cross-brief** cells are the new matched comparison.

## 2. Contribution deltas, base → smooth (smooth − base)

| Design | key | Δ contribution |
|---|---|---:|
| Crowe ES-600 | cov | −2.318467 |
| Crowe ES-600 | rip | +0.000000 |
| Crowe ES-600 | di | −1.290507 |
| Crowe ES-600 | dislope | −6.292328 |
| Crowe ES-600 | flat | +0.000000 |
| Crowe ES-600 | load | +0.000000 |
| Crowe ES-600 | distd | +0.589090 |
| Crowe ES-600 | diag | −0.769782 |
| Crowe ES-600 | flat_cv | +0.000000 |
| Crowe ES-600 | **J** | **−10.081995** |
| Klangfilm-Lame | cov | −3.686241 |
| Klangfilm-Lame | rip | +0.000000 |
| Klangfilm-Lame | di | −1.220630 |
| Klangfilm-Lame | dislope | −7.852859 |
| Klangfilm-Lame | flat | +0.000000 |
| Klangfilm-Lame | load | +0.000000 |
| Klangfilm-Lame | distd | +0.678044 |
| Klangfilm-Lame | diag | −1.777008 |
| Klangfilm-Lame | flat_cv | +0.000000 |
| Klangfilm-Lame | **J** | **−13.858695** |

How much of each **base** J is the CD assumption (`dislope` + `di`) rather than coverage:

| Design | dislope | di | dislope+di | cov | diag |
|---|---:|---:|---:|---:|---:|
| Crowe ES-600 | 7.404014 (43.8 %) | 1.290507 (7.6 %) | **8.694521 (51.4 %)** | 3.374751 (19.9 %) | 3.710529 (21.9 %) |
| Klangfilm-Lame | 10.170940 (44.6 %) | 1.220630 (5.4 %) | **11.391570 (50.0 %)** | 5.105361 (22.4 %) | 5.534638 (24.3 %) |

Both horns pay more than half of their *base-brief* J to the constant-directivity assumptions — measured DI slope ≈ +8.2/+9.6 dB/dec against a 0 dB/dec target (`dislope`), plus a fixed Gaussian DI level (`di`). Coverage is only ~20–22 % of base J. Dropping `di` and relaxing the slope target (smooth brief) is what collapses J; the designs themselves did not change.

---

## 3. Per-design breakdown — every weighted key, base vs smooth

`raw` is the un-normalised term (`stored_normalized × tolerance`); `contribution = weight × (raw / tolerance)`. `Σ contributions = J`.

### Crowe ES-600 (`22365b569be9`)

| key | raw base | raw smooth | w base | w smooth | tol base | tol smooth | contribution base | contribution smooth | Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cov | 10.124253 | 8.450271 | 1.00 | 1.00 | 3.00 | 8.00 | 3.374751 | 1.056284 | −2.318467 |
| rip | 0.067554 | 0.067554 | 1.00 | 1.00 | 1.00 | 1.00 | 0.067554 | 0.067554 | +0.000000 |
| di | 1.720676 | 0.000000 | 0.30 | 0.00 | 0.40 | 0.40 | 1.290507 | 0.000000 | −1.290507 |
| dislope | 66.636129 | 10.005174 | 1.00 | 1.00 | 9.00 | 9.00 | 7.404014 | 1.111686 | −6.292328 |
| flat | 0.560593 | 0.560593 | 0.50 | 0.50 | 1.50 | 1.50 | 0.186864 | 0.186864 | +0.000000 |
| load | 0.000000 | 0.000000 | 1.00 | 1.00 | 0.30 | 0.30 | 0.000000 | 0.000000 | +0.000000 |
| distd | 2.356361 | 2.356361 | 0.50 | 1.00 | 2.00 | 2.00 | 0.589090 | 1.178180 | +0.589090 |
| diag | 7.421059 | 5.881494 | 1.00 | 1.00 | 2.00 | 2.00 | 3.710529 | 2.940747 | −0.769782 |
| flat_cv | 0.442298 | 0.442298 | 1.00 | 1.00 | 1.50 | 1.50 | 0.294865 | 0.294865 | +0.000000 |
| **J** | | | | | | | **16.918176** | **6.836182** | **−10.081995** |

### Klangfilm-Lame (`491efb2132b8`)

| key | raw base | raw smooth | w base | w smooth | tol base | tol smooth | contribution base | contribution smooth | Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cov | 15.316083 | 11.352960 | 1.00 | 1.00 | 3.00 | 8.00 | 5.105361 | 1.419120 | −3.686241 |
| rip | 0.026250 | 0.026250 | 1.00 | 1.00 | 1.00 | 1.00 | 0.026250 | 0.026250 | +0.000000 |
| di | 1.627507 | 0.000000 | 0.30 | 0.00 | 0.40 | 0.40 | 1.220630 | 0.000000 | −1.220630 |
| dislope | 91.538458 | 20.862726 | 1.00 | 1.00 | 9.00 | 9.00 | 10.170940 | 2.318081 | −7.852859 |
| flat | 0.090067 | 0.090067 | 0.50 | 0.50 | 1.50 | 1.50 | 0.030022 | 0.030022 | +0.000000 |
| load | 0.000000 | 0.000000 | 1.00 | 1.00 | 0.30 | 0.30 | 0.000000 | 0.000000 | +0.000000 |
| distd | 2.712176 | 2.712176 | 0.50 | 1.00 | 2.00 | 2.00 | 0.678044 | 1.356088 | +0.678044 |
| diag | 11.069275 | 7.515258 | 1.00 | 1.00 | 2.00 | 2.00 | 5.534638 | 3.757629 | −1.777008 |
| flat_cv | 0.024639 | 0.024639 | 1.00 | 1.00 | 1.50 | 1.50 | 0.016426 | 0.016426 | +0.000000 |
| **J** | | | | | | | **22.782312** | **8.923617** | **−13.858695** |

For both horns the raw values of `rip`, `distd`, `flat`, `flat_cv` and `load` are **identical across briefs** (they are target-coverage/band-invariant here — both briefs share the same 80×50 Target, so this is expected). What changes is `cov` (tolerance 3→8 and narrow ratio 2→1), `dislope` (target 0→+5 dB/dec), `di` (weight 0.3→0, so contribution → 0) and `diag` (measured diagonal response scored against the same 65° reference, but the target-coverage term shifts via the recomputed metrics).

---

## 4. Per-cell facts block

Both briefs carry the **same** `Target` (80×50, band 350–8000 Hz, f0 = f0_v = 700 Hz, `cov_v_weight 0.5`); only the objective block and weights differ. So the window / DI-level / 8 kHz-floor / diagonal facts are identical for a given design; the DI **scored** flag and slope target flip with the brief.

### Crowe ES-600

| fact | BASE | SMOOTH |
|---|---|---|
| per-plane scored window | `h_lo = v_lo = 700 Hz`; band 350–8000 Hz; `n_in_band = 13` | same |
| below-f0 mode | `mask` | `mask` |
| narrow-side ratio | **2.0** | **1.0** |
| cov `cov_v_weight` (vertical share) | 0.50 | 0.50 |
| DI level source / level | `gaussian` / 13.080 dB | `gaussian` / 13.080 dB |
| DI level **scored** | **True** (di weight 0.3) | **False** (di weight 0.0) |
| DI slope target / measured scored-band slope | 0.0 / **+8.163 dB/dec** | +5.0 / **+8.163 dB/dec** |
| 8 kHz floor @ `8000 Hz` | 60.00° H / 37.50° V (0.75×80 / 0.75×50) | same |
| measured BW @ 8 kHz | 48.10° H / 35.18° V | same |
| 8 kHz raw penalty (rides inside `cov`) | **1.470840** → 0.490280 contribution (14.5 % of base cov) | 1.470840 → 0.183855 contribution (17.4 % of smooth cov) |
| diagonal reference / scored | 65.00° = (80+50)/2 / True | 65.00° / True |

### Klangfilm-Lame

| fact | BASE | SMOOTH |
|---|---|---|
| per-plane scored window | `h_lo = v_lo = 700 Hz`; band 350–8000 Hz; `n_in_band = 13` | same |
| below-f0 mode | `mask` | `mask` |
| narrow-side ratio | **2.0** | **1.0** |
| cov `cov_v_weight` (vertical share) | 0.50 | 0.50 |
| DI level source / level | `gaussian` / 13.080 dB | `gaussian` / 13.080 dB |
| DI level **scored** | **True** (di weight 0.3) | **False** (di weight 0.0) |
| DI slope target / measured scored-band slope | 0.0 / **+9.568 dB/dec** | +5.0 / **+9.568 dB/dec** |
| 8 kHz floor @ `8000 Hz` | 60.00° H / 37.50° V | same |
| measured BW @ 8 kHz | 39.48° H / 33.85° V | same |
| 8 kHz raw penalty (rides inside `cov`) | **4.343779** → 1.447926 contribution (28.4 % of base cov) | 4.343779 → 0.542972 contribution (38.3 % of smooth cov) |
| diagonal reference / scored | 65.00° = (80+50)/2 / True | 65.00° / True |

Both designs are **below** the 8 kHz narrow-only floor in H (and marginally in V); the floor is a raw addition inside `cov`, so it never disappears when the smooth brief relaxes the cov tolerance — it only gets divided by the larger tolerance.

---

## 5. Method notes

### 5.1 Identity replay (the gate) — exact

Each design was replayed under **its own run brief** (the immutable `config.yaml` embedded `brief:` block), recomputing metrics from the stored `response.npz`, then scored with `objective_v7`. The script asserts `|recomputed J − stored best J| ≤ 1e-6`. Actual output:

```
[identity] crowe_es600: recomputed J = 16.918176135266869  stored = 16.918176135266869  delta = +0.000e+00  -> PASS
[identity] klangfilm_lame: recomputed J = 8.923616737684702  stored = 8.923616737684702  delta = +0.000e+00  -> PASS
```

Both deltas are **exactly zero** — every weighted term matches the stored `best.json` terms to the last bit. Because the identity replay is exact, the two cross-brief cells use the same, proven-faithful machinery.

### 5.2 Stored responses unchanged; metrics recomputed per target

- `resp = hornlab_search.solve.cache.load_response(designs/<hash>/response.npz)` — the stored BEM response is read, never rewritten. Both designs' `metrics.json` and `response.npz` report `di_source == "balloon"`; the script asserts the loaded response carries a balloon (`spl_balloon_db` + `balloon_dirs`).
- Per brief, `metrics = hornlab_search.search.evaluate.metrics_from_response(resp, target)` then `J, terms = objective_v7(metrics, resp, True, target, weights, params)`.
- **Important method correction:** the task named `compute_metrics` directly. `compute_metrics` assumes an **equal-area** balloon, but the solver balloon is a **theta-phi grid** (`response.npz` meta `balloon_grid = [16, 32]`, layout "NOT equal-area: weight by sin(theta)"). Called directly, `compute_metrics` over-counts the poles and reads DI up to **~6.9 dB high** in the HF for the Crowe response; the identity replay then misses by ~4.6 J. `metrics_from_response` is the canonical run path: it applies the `sin(theta)` quadrature and hands the collapsed weighted power to `compute_metrics`, so every metric/scalar matches the run exactly. With it the identity replay is bit-exact (5.1).

### 5.3 Grid-match assertion

```
[grid] all cells share one solved grid: 18 freqs, band 350-8000 Hz  -> PASS
```

The script asserts (a) both designs' `resp.freqs_hz` are identical element-wise (atol 1e-9), (b) both briefs carry the same `band_lo_hz` / `band_hi_hz`, and (c) the two briefs' `grid:` blocks are equal. Solved grid: `250, 315, 400, 500, 643.33, 827.75, 1065.04, 1370.35, 1763.18, 2268.63, 2573, 2918.96, 3311, 3755.72, 4260, 4832.36, 6217.63, 8000` Hz. The comparison is therefore per-frequency matched.

### 5.4 Reproduce

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"; $env:NUMEXPR_NUM_THREADS="1"
.venv\Scripts\python.exe scratch\rescore_crowe_klangfilm_20261117.py
.venv\Scripts\python.exe -m pytest tests\test_scoring_view.py -q
```

---

## 6. Caveats box

> **Single best design per run — not a family rerank.** These are the two runs' *best* designs only. Nothing here says whether another design in either run would score differently under the other brief; that needs a full-dataset rescore, not a 2×2.
>
> **Screen-tier fidelity.** Both source runs are `--mode screen` (512-point balloon, `dof_cap_screen`), not verify/final tier. The numbers are internally matched (same grid, same response) but are screen-resolution.
>
> **J is NOT rank-comparable across briefs, historically.** This is the entire point of the table: base and smooth J are on different scales (different tolerances, weights and slope targets). A lower smooth J is a different objective, not a better horn. Never compare a base J to a smooth J as a ranking; compare only the *same* brief column across designs, or the decomposition.
>
> **Rescores must override the row target (BIRADIAL_STUDY).** The stored `search.ndjson`/dataset row keeps its OWN target — its metric curves were produced against it. Re-scoring under a different brief therefore **must** substitute that brief's `Target` and **recompute** target-dependent metrics (coverage, ripple, diagonal, floor, DI level), never reuse the stored ripple/diag/floor. That is exactly what this script does deliberately. (`tools/rescore/rescore_v6_v7.py` follows the opposite convention — keep the row target — which is why this is a separate purpose-built script.)
>
> **DI is balloon-derived; the smooth brief scores slope only.** `di` weight drops to 0 under smooth, so the fixed Gaussian DI *level* is not scored (translation-invariant slope-only); the measured trend still enters through `dislope`. `distd` is `std(DI)`, not residual roughness, so it stays positive even for a monotonic DI rise (see `NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md`).
