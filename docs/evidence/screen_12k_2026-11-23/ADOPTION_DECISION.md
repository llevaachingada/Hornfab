# ADOPTION DECISION — 12 kHz SCREEN

**Status: DECIDED (2026-11-24). Outcome: no default change.** Measured on 4 cohorts × 6 designs
(24 designs), 7 arms, 162 evaluations (161 ok), plus epw 5/6/8 on 4 designs. The rule below was
written before any arm was solved and is applied as written.

## Decision rule (pre-registered) and measured result

| # | Criterion | Threshold | F0 | F1 (19) | F2 (29) | FA (21) | FB (27) |
|---|---|---|---|---|---|---|---|
| 1 | pooled Spearman vs dense reference | gain ≥ +0.10, no cohort recall loss | 0.832 (—) | 0.914 (**+0.082**) | 0.957 (**+0.125**) | 0.871 (+0.039) | 0.943 (+0.111) |
| 1 verdict | | | — | **fail** (gain) | **pass** | fail | fail (no twinray rows → recall unmeasurable) |
| 2 | HF defects caught of the 6 F0 cannot see | ≥50 %, 0 false positives | 0/6 (blind) | 5/6, **1 FP** | **6/6, 0 FP** | 5/6, 1 FP | 5/6, 1 FP |
| 2 verdict | | | — | fail | **pass** | fail | fail |
| 3 | median wall vs F0 | ≤ 2.0× | 1.00 | **2.37×** | **3.65×** | 2.65× | 3.23× |
| 3 verdict | | | pass | **fail** | **fail** | fail | fail |
| 4 | epw 6 vs 8 at 10–12 kHz | ≤0.5 dB, ≤2° | — | 0.012 dB / 0.12° (F3 mesh) | — | — | — |
| 4 verdict | | | — | **pass** | | | |
| **ALL** | | | — | **fail** | **fail** | fail | fail |

**Cheapest arm passing all four criteria: none.** No 12 kHz arm is adopted as a default.

One finding sharpens the decision: **detection is not demotion.** The morph design with the beam
collapse (n60) ranks first under F0, F1, F2 and F3 alike. The 12 kHz solve exposes the defect, but J
barely penalises it (8–12 kHz is ~6 % of a per-frequency mean; no `hf_floor` is declared), so a
12 kHz screen changes what is *known*, not which design wins. Making the shortlist react to HF
defects needs an HF-weighted term — a new score identity, outside this pass's scope.

## Why, in one paragraph

A 12 kHz screen *does* see something the current 10 kHz screen physically cannot: all six
high-frequency beam-collapse defects in this set are **unassessable** on the 12-point 10 kHz grid
(fewer than three samples in 8–12 kHz), while a 29-point 12 kHz screen catches **6 of 6** with no
false alarms and improves rank correlation against the dense reference from 0.832 to 0.957. But it
costs **3.65×** and the cheaper 19-point arm both misses one defect and raises one false alarm
(+0.082 rank gain, under the 0.10 bar). The pre-registered cost bar was 2.0×; the 12 kHz **mesh
alone** already costs 1.79× before any frequency is added, so no compliant 12 kHz policy exists on
this GPU.

## What is recommended instead

1. **Default stays 8 kHz / frozen grids.** Historical J keeps its meaning.
2. **Opt-in only**: a brief that declares `band_hi_hz: 12000` *and* explicitly sets
   `solve.screen_grid` (or `profile: hf12k_screen_v1` for the 19-point form) gets 12 kHz. Use
   `{lo_hz: 500, hi_hz: 12000, points_per_octave: 6}` (29 points) when HF beam collapse is the
   failure mode being screened — it is the only arm that caught all six and it does not false-alarm.
3. **Do not** use the 19-point profile as a general default: it failed both the selection bar and
   the zero-false-positive requirement.

## What changes if an opt-in run is used

* `solve.screen_grid` is the only switch; `FREQ_GRIDS["screen"]` is untouched.
* The brief must extend `target.band_hi_hz`, the coverage-profile anchors and the v11
  `objective.cd.band_hz` / `cd.offaxis.band_hz`; otherwise ~47 % of v11's weight ignores 8–12 kHz
  (audit, README §1).
* Budget ≈ 2.4–3.7× the per-candidate screen time (measured `GPU_BENCHMARK.csv`), and set
  `solve.timeout_s` ≥ 1200 for 53-frequency dense references at ≥18 k DOF — one dense solve hit the
  900 s default at 52/53 frequencies.

## What does NOT change

* `FREQ_GRIDS["screen"]` (12 pts, 500–10000) — the compatibility floor.
* `solve.freq_grid` semantics (all modes) — the `meh_*` configs depend on it.
* Objective formulas/weights — no defect was found that requires one.
* Mesh generator, `design/families.py`, sizing algorithms — other orchestrator's scope.
* Historical runs and their J.

## Residual risks

* Above f11 (≈5.6 kHz for the 35.8 mm exit, ≈7.9 kHz for 1″) a uniform-velocity source is not a
  compression driver; 8–12 kHz compares geometries, not driver output.
* MEH walls at a 12 kHz request validate only to ~6 kHz (existing evidence) — MEH is excluded from
  the 12 kHz screen class.
* The dense reference is itself a 53-point grid; "no defect" means "none at this resolution".
* Six designs per cohort: top-3/top-5 statistics are coarse; Spearman is pooled per cohort, never
  across briefs.
* Dedicated VRAM only (median 0.8 GiB, max 2.8 GiB at 18 439 DOF); WDDM shared spill is not
  observable per process on Windows.
