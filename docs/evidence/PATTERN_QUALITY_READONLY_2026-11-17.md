# WP2 - report-only pattern-quality measurements over stored responses

**Date:** 2026-11-17 | **Lane:** WP2 (implementation) | **Status:** DONE (report-only; no objective change)
**Module:** `hornlab_search/metrics/pattern_quality.py` (new) | **CLI:** `tools/analysis/pattern_quality_report.py` (new)
**Tests:** `tests/test_metrics_pattern_quality.py` (new, 18 offline fixtures) | **Data:** `docs/evidence/pattern_quality_readonly/`

> This work reads **only immutable stored `response.npz` arrays**. No BEM solve, mesh, solver, GPU
> job or runs/ write occurred. No existing metric, objective, target or `metrics/polar.py`
> definition was edited; v1-v9 raw scoring is untouched by construction.

---

## 1. What is reported (and what is reused)

Per frequency, separately for the H and V cuts:

| Quantity | Definition | Reused implementation |
|---|---|---|
| legacy width | outermost on-axis-referenced -6.0206 dB crossings | `metrics.polar.beamwidth_deg` (untouched) |
| connected width | interval containing theta=0, first crossing each side | `metrics.acoustic_v2.main_lobe` |
| islands | disconnected above-threshold runs outside the connected interval, with interpolated angular extent | new on top of `normalized_db` / `_threshold_db` |
| signed edges | lower/upper main-lobe edge; censored sides are `None` + a labelled grid-edge bound | `acoustic_v2.main_lobe` |
| transitions | total threshold transitions, re-entries / islands | new (pure numpy) |
| off-axis excess | `max(0, SPL(theta) - SPL(0) - threshold)`, whole cut and in-coverage | reuses the H12 threshold `objective.scalar_v7._OA_EXCESS_THRESHOLD_DB` (0.5 dB) |
| flags | `>+0.5 dB` / `>+1.0 dB` off-axis peaks, disconnected islands, legacy-width inflation | diagnostic only, **never weighted** |
| spherical DI | linear-power sphere average with canonical sin(theta) solid-angle weights | `metrics.di.di_from_balloon` + `sin_theta_weights` (scoring path) |
| lobe map | connected main region, detached islands, outside power fraction | `metrics.acoustic_v2.balloon_lobes` / `sphere_weights` |
| diagonal overlay | 45/135 degree first-crossing width | `metrics.diagonal.diagonal_beamwidths_deg`; a no-crossing ray is labelled **censored**, not 178 deg |

A censored / unmeasurable result is `width_deg = None` with an explicit `status`; the legacy
180-degree sentinel is retained only as `legacy_sentinel_deg` for audit. A missing or too-sparse
balloon is a typed refusal (`BalloonUnavailableError` / `BalloonTooSparseError`) recorded in the
report, never replaced by fabricated DI or lobe numbers.

---

## 2. Synthetic fixtures (offline)

Command (exact):

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"; $env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe -m pytest tests/test_metrics_pattern_quality.py -q -p no:cacheprovider
```

Actual output:

```text
..................                                                       [100%]
EXIT=0
```

Fixtures cover: single Gaussian lobe; centered plateau; centered lobe **plus two detached outer
lobes** (legacy 120.1 deg vs connected 30.0 deg, island count 2); off-axis peak above on-axis
(+5.0 dB at 50 deg, both diagnostic flags); no crossing / all non-finite (censored or
unmeasurable, never 180/0); one-sided crossing (legacy 110 deg one-sided, connected censored);
non-finite and corrupted angles (typed `PatternQualityInputError`); non-finite off-axis samples
(floored, no crash); uniform omni (`DI = 0.0`); equal-area vs theta/phi unequal-area weighting
(canonical DI exceeds naive equal weights by 7.14 dB on the fixture); quarter-domain H/V symmetry
and mirror-sign symmetry; angular interpolation consistency (coarse vs fine grid both 120.412 deg
against the analytic ramp); theta=0 presence and too-sparse balloon refusal; and an assertion that
`h12_offaxis_excess_threshold_db()` equals `objective.scalar_v7._OA_EXCESS_THRESHOLD_DB` (single
source, no duplicated threshold).

---

## 3. Stored-winner demonstration

Command (exact):

```powershell
.venv\Scripts\python.exe tools\analysis\pattern_quality_report.py `
    runs\20261115T205453Z-screen-32f7c4 `
    runs\20261116T225543Z-screen-6acf41 `
    runs\20261116T153619Z-screen-c221aa `
    --out docs\evidence\pattern_quality_readonly
```

Actual output:

```text
label                              family       nf  legacyH  legacyV    connH    connV  cenH/V  isl   offax     DI balloon
hl__crowe_panel_home_v7:22365b569be9 FREEFORM     18     86.8     75.8     86.8     75.8   1/5      0   -0.00   9.70 valid
hl__klangfilm_lame_curved_v1:491efb2132b8 FREEFORM     18     90.1     91.3     90.1     91.3   0/0      0   -0.00  10.57 valid
hl__osse_rrect_fold_warm_v7:6d6dd332b282 OSSE         18     76.3     73.4     76.3     73.4   1/1      0   +0.50  10.89 valid

wrote docs\evidence\pattern_quality_readonly\pattern_quality_reports.json
wrote docs\evidence\pattern_quality_readonly\pattern_quality_by_frequency.csv
EXIT=0
```

`legacyH/V` and `connH/V` are band means over measurable frequencies (deg). `cenH/V` counts
frequencies whose connected width is censored. `isl` is the maximum island count; `offax` is the
largest signed off-axis level over both planes (dB re on-axis); `DI` is a band mean (dB).

Provenance (screen-tier runs, immutable responses):

| Label | Run | Design | Family | response.npz SHA-256 |
|---|---|---|---|---|
| `hl__crowe_panel_home_v7` | `20261115T205453Z-screen-32f7c4` | `22365b569be9` | FREEFORM | `8d0bc7f5310717b0db1521844c6c042778592c904724963ce49f8ffd8aa5fe62` |
| `hl__klangfilm_lame_curved_v1` | `20261116T225543Z-screen-6acf41` | `491efb2132b8` | FREEFORM | `0267dbf71bcce1699492a1310dcad1aeb9441464c5d37ff83b6fa8ff06ed7e37` |
| `hl__osse_rrect_fold_warm_v7` | `20261116T153619Z-screen-c221aa` | `6d6dd332b282` | OSSE | `e495a201ea78e350ee21d9f038d390b904fcb505d72252d4e58fb06f761a69ce` |

Per-frequency excerpt (same CLI on the OSSE run alone, `--verbose`; actual output):

```text
-- hl__osse_rrect_fold_warm_v7:6d6dd332b282 (runs\20261116T153619Z-screen-c221aa\designs\6d6dd332b282\response.npz)
     250.0 Hz  H leg/conn -/- (censored )  V leg/conn -/- (censored )  isl  0/ 0  DI   3.66  flags -
     315.0 Hz  H leg/conn  139.2/ 139.2 (valid    )  V leg/conn  159.1/ 159.1 (valid    )  isl  0/ 0  DI   5.09  flags -
     400.0 Hz  H leg/conn  112.2/ 112.2 (valid    )  V leg/conn  135.6/ 135.6 (valid    )  isl  0/ 0  DI   6.59  flags -
     500.0 Hz  H leg/conn   91.8/  91.8 (valid    )  V leg/conn  118.4/ 118.4 (valid    )  isl  0/ 0  DI   8.01  flags -
     643.3 Hz  H leg/conn   72.7/  72.7 (valid    )  V leg/conn   97.8/  97.8 (valid    )  isl  0/ 0  DI   9.76  flags -
     827.8 Hz  H leg/conn   59.0/  59.0 (valid    )  V leg/conn   78.1/  78.1 (valid    )  isl  0/ 0  DI  11.42  flags -
    1065.0 Hz  H leg/conn   70.1/  70.1 (valid    )  V leg/conn   61.1/  61.1 (valid    )  isl  0/ 0  DI  12.17  flags -
    1370.3 Hz  H leg/conn   77.0/  77.0 (valid    )  V leg/conn   53.2/  53.2 (valid    )  isl  0/ 0  DI  12.59  flags -
    1763.2 Hz  H leg/conn   70.7/  70.7 (valid    )  V leg/conn   48.4/  48.4 (valid    )  isl  0/ 0  DI  12.67  flags -
    2268.6 Hz  H leg/conn   76.7/  76.7 (valid    )  V leg/conn   48.2/  48.2 (valid    )  isl  0/ 0  DI  12.19  flags off_axis_peak_gt_0p5_db
    2573.0 Hz  H leg/conn   74.0/  74.0 (valid    )  V leg/conn   55.1/  55.1 (valid    )  isl  0/ 0  DI  12.27  flags -
    2919.0 Hz  H leg/conn   73.6/  73.6 (valid    )  V leg/conn   55.9/  55.9 (valid    )  isl  0/ 0  DI  12.24  flags -
    3311.0 Hz  H leg/conn   69.1/  69.1 (valid    )  V leg/conn   57.8/  57.8 (valid    )  isl  0/ 0  DI  12.60  flags -
    3755.7 Hz  H leg/conn   66.7/  66.7 (valid    )  V leg/conn   60.5/  60.5 (valid    )  isl  0/ 0  DI  12.44  flags -
    4260.0 Hz  H leg/conn   66.8/  66.8 (valid    )  V leg/conn   58.7/  58.7 (valid    )  isl  0/ 0  DI  12.06  flags -
    4832.4 Hz  H leg/conn   63.0/  63.0 (valid    )  V leg/conn   57.4/  57.4 (valid    )  isl  0/ 0  DI  12.45  flags -
    6217.6 Hz  H leg/conn   59.4/  59.4 (valid    )  V leg/conn   53.8/  53.8 (valid    )  isl  0/ 0  DI  13.54  flags -
    8000.0 Hz  H leg/conn   54.3/  54.3 (valid    )  V leg/conn   49.5/  49.5 (valid    )  isl  0/ 0  DI  14.32  flags -
```

---

## 4. Parity checks (no existing behaviour changed)

**Legacy width is bit-identical to the stored `metrics.json`** wherever the stored scalar is a
real measurement (we delegate to `beamwidth_deg`):

```text
crowe      comparable legacy cells= 30 max|report_legacy - stored_bw| = 0.000e+00 deg
klangfilm  comparable legacy cells= 36 max|report_legacy - stored_bw| = 0.000e+00 deg
osse       comparable legacy cells= 34 max|report_legacy - stored_bw| = 0.000e+00 deg
EXIT=0
```

**Spherical DI matches the canonical scoring path** (`metrics_from_response`) to machine precision:

```text
crowe      n=18 max|diag_di - stored_metrics_di| = 8.882e-16 dB
klangfilm  n=18 max|diag_di - stored_metrics_di| = 8.882e-16 dB
osse       n=18 max|diag_di - stored_metrics_di| = 8.882e-16 dB
EXIT=0
```

No objective metric or default penalty was changed; `pattern_quality.py` is imported by nothing in
`objective/**` or `search/**`.

---

## 5. Measured observations (report-only; not a ranking)

* **No detached islands in these three winners.** Legacy and connected widths coincide at every
  measurable frequency, so the legacy scalar is not misleading *for these stored responses*. The
  synthetic detached-lobe fixture is the case that separates them (120.1 vs 30.0 deg).
* **Low-frequency censoring is real and is now explicit.** Crowe is censored at 250 Hz in both
  planes and in V at 315/400/500/643 Hz (5 V cells); OSSE is censored at 250 Hz in both planes.
  These are not 180-degree beams.
* **High-frequency narrowing** (legacy definition, deg, H/V): Crowe 48.1/35.2 at 8 kHz; Klangfilm
  39.5/33.9 at 8 kHz; OSSE 54.3/49.5 at 8 kHz. This reproduces the stored 8 kHz beamwidths in
  `CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md` exactly (48.10/35.18 and 39.48/33.85).
* **One diagnostic flag on OSSE**: +0.50 dB off-axis peak at 2268.63 Hz (H plane, threshold
  `>+0.5 dB`). It is a report-only flag, not a cost. Klangfilm and Crowe have no +0.5 dB off-axis
  peaks in this report.
* **Balloon:** every response carries a valid 512-point theta-phi balloon, grid 16 x 32, so the
  canonical sin(theta) DI is used. The coarse map resolves about 12.0 deg theta x 11.25 deg phi;
  finer angular structure is not claimed. The diagonal overlay is censored (blank, with
  `censored_floor_deg = 178`) at 250 Hz for Crowe and OSSE and `partial` at one frequency for
  Klangfilm; no 178-degree sentinel is exposed as a measurement (checked in the CSV).

---

## 6. Files

Created (owned):
* `hornlab_search/metrics/pattern_quality.py`
* `tools/analysis/pattern_quality_report.py`
* `tests/test_metrics_pattern_quality.py`
* `docs/evidence/PATTERN_QUALITY_READONLY_2026-11-17.md`
* `docs/evidence/pattern_quality_readonly/pattern_quality_reports.json`
* `docs/evidence/pattern_quality_readonly/pattern_quality_by_frequency.csv`

No existing module, objective, target, `metrics/polar.py`, `runs/` entry or dataset record was
modified. No GPU lock, run or solve was touched.

---

## 7. Caveats

* **Screen tier.** All three source runs are `screen` mode (512-point balloon, screen dof cap).
  The numbers are internally matched but are screen-resolution; they are not verify/final truth.
* **Not a new score.** `pattern_quality_flags` and every value here are diagnostics. Nothing is
  weighted into J, and no pass/fail physics standard is implied by the +0.5/+1.0 dB flags.
* **Balloon resolution.** DI is a full-sphere linear-power average; it is only as good as the
  16 x 32 grid. The report states the grid spacing and refuses to attribute finer features.
* **Missing balloon.** If a future response has no balloon or too sparse a balloon, the CLI writes
  `balloon.status = unavailable/refused` with the typed error and emits no spherical values.
  `--require-balloon` turns that into exit code 2.

## 8. Reproduce

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"; $env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe -m pytest tests/test_metrics_pattern_quality.py -q -p no:cacheprovider

.venv\Scripts\python.exe tools\analysis\pattern_quality_report.py `
    runs\20261115T205453Z-screen-32f7c4 `
    runs\20261116T225543Z-screen-6acf41 `
    runs\20261116T153619Z-screen-c221aa `
    --out docs\evidence\pattern_quality_readonly
```
