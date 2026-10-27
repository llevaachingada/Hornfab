# Campaign smoke night - 2026-10-27

First smoke night of the 2026-10-26 campaign set: a T0 validity gate over all 27 cells, mini-T1
comparisons (crease A/B at equal budget), and the fused-CUDA ceiling ladder. One GPU job at a time,
sequential, runner = `tools/run_campaign_night.py`, night file = `runs\nights\smoke_2026-10-27.yaml`
(runtime, not committed). Local wall clock ~19:53 to ~02:00; interpreter `.venv\Scripts\python.exe`;
RTX 4060 (8,188 MiB).

## 0. Scoring note - read this before comparing J with anything

Three native briefs were rescored by the 2026-10-26 senior review, immediately before this run:

| brief | change | why |
|---|---|---|
| `native_ath_core_2in` | objective v2 -> **v3**, `target.f0_hz 1280` | CORE's 397 mm mouth holds 50 deg from 25,400,000 / (397 x 50) |
| `native_twinray_380_14in` | v2 -> **v3**, `f0_hz 743`, `f0_v_hz 1397` | published 380 x 303 mm mouth, per plane |
| `native_lecleach_1200_1in` | `cov 1.0 -> 0.3`, `load 0.0 -> 0.5`, `z_min 0.0 -> 0.7` | a Le Cleac'h narrows by design; loading is its job |

**J on those three brief names is not comparable with any earlier result.** `crease__core_law` and
`native__ath_core` / `native__ath_twinray_380` run on the first two; `native__lecleach_asym_odd`
and `native__lecleach_rollback` run on the third. Every other brief is unchanged.

Scoring is still H/V-plane only: a creased wall's diagonal (45/135 deg) behaviour is **invisible** to
J. The screen grid starts at 500 Hz, so "loads to 400 Hz" can only be judged at verify (300 Hz
floor). Coverage is graded to 8 kHz, past the 1.4-inch driver's ~5.6 kHz cross-mode (owner's choice).

## 1. Night totals

- **41 jobs** (27 T0 + 9 mini-T1 + 5 ladder rungs), **all 41 recorded** in `summary.jsonl`.
- **376 evaluations, 252 valid, 124 refused**: `invalid_geometry` 89, `invalid_envelope` 26,
  `mesh_too_large` 9 → **33 % refused overall**. The Phase-0 LHS audit measured 0-37.5 % before the
  boxes were widened, so **the physical-range widening did not increase the refusal rate** - the
  owner's ruling cost nothing in validity.
- **157.8 valid evaluations per hour** (5,750 s of search jobs), at 0.9k-9.9k dofs.
- GPU: median **100 %** utilisation while solving, mean 61 %; **43 % of sampled time the card was
  idle** in a CPU phase (see section 8).

## 2. Phase B - fused-CUDA ceiling ladder at 8 kHz

One solve per fresh process, `--freq 8000`, 73 angles, quarter domain, `gpu-clean` between points.

| rung | dofs | triangles | assembly s | solve s | s/freq | peak-baseline MiB | peak MiB | % of 8,188 |
|---|---|---|---|---|---|---|---|---|
| `phaseB_dof5k` | 5,106 | 9,956 | 1.85 | 0.068 | 2.55 | 950 | 1,736 | 21 % |
| `phaseB_dof8k9` | 8,919 | 17,500 | 4.06 | 0.267 | 6.62 | 2,433 | 3,324 | 41 % |
| `phaseB_dof12k` | 12,183 | 23,973 | 6.69 | 0.636 | 11.00 | 5,183 | 5,972 | 73 % |
| `phaseB_dof14k` | 13,999 | 27,578 | 8.54 | 0.937 | 13.78 | 6,028 | 7,199 | **88 %** |
| `phaseB_dof17k` | 16,960 | 33,460 | - | - | - | - | **7,908** | **97 % - TIMEOUT (1,800 s, exit 124)** |

- **The 90 % rule now has a measured edge: it binds just above 14k dofs.** 12,183 dofs is the last
  comfortable point (73 %); 13,999 is at 88 % (works, no headroom for the GUI); **16,960 peaked at
  7,908 MiB (97 %) and was killed at exactly the 1,800 s timeout with no RESULT line** - the GPU sat
  at 100 % utilisation drawing only 26-27 W, the oversubscription-into-host-memory signature
  documented in `FUSED_CUDA_2026-10-24.md`. `gpu-clean` recovered the card to 294 MiB afterwards.
- **Consequence for briefs at 8 kHz:** a 706 mm B3a horn (~10k dofs) is fine; a 90 x 60 at 400 Hz
  (~17k dofs) is **not available** - it must move to a lower top frequency or accept the
  oversubscription/host-memory path documented in `FUSED_CUDA_2026-10-24.md`.
- **The cost model changed.** Inside one frequency, **assembly is 73-96 % of the cost** and the
  iterative solve is 0.07-0.94 s. A campaign evaluation at ~11,967 dofs logs 9.5 s/frequency, which
  matches the standalone 12,183-dof number (11.0) - so **the assembly is paid per frequency**, not
  hoisted across the 12-point grid. One evaluation ~ `n_frequencies x assembly(dofs)`. That makes
  the frequency count, not the dof count, the dominant throughput knob.

## 3. T0 - the validity gate (seed only, budget 1)

**26 of 27 cells passed on the night; 27/27 after the `gcurve` reseed later the same night**
(section 7). One failure as run, not a crash: `gcurve__osse_b1w`.

| cell | seed J | dofs | s | cell | seed J | dofs | s |
|---|---|---|---|---|---|---|---|
| b1t__lecleach_iwata_ar | 16.503 | 2,640 | 43 | b3a__rosse_morph | 18.504 | 7,692 | 80 |
| b1t__rosse_morph | 23.534 | 3,814 | 34 | b3bt__lecleach_iwata_ar | 19.084 | 5,053 | 58 |
| b1t__salmon_x_signed | 16.664 | 3,419 | 47 | b3bt__rosse_morph | 19.228 | 7,096 | 79 |
| b1w__biradial_keele | 15.201 | 2,326 | 43 | b3bt__salmon_x_signed | 17.077 | 6,742 | 71 |
| b1w__osse_baseline | 13.288 | 1,796 | 37 | b3bw__biradial_keele | 6.960 | 3,285 | 46 |
| b2t__lecleach_iwata_ar | 9.289 | 2,904 | 43 | b3bw__hyb_osse_h_hypex_v | 9.136 | 3,271 | 52 |
| b2t__rosse_morph | 18.595 | 4,691 | 54 | native__ath_core | 32.179 | 3,777 | 47 |
| b2t__salmon_elliptical | 27.514 | 2,792 | 43 | native__ath_twinray_380 | 13.067 | 2,295 | 68 |
| b2w__hyb_osse_h_hypex_v | 6.319 | 1,985 | 42 | native__lecleach_asym_odd | 6.519 | 3,289 | 36 |
| b2w__osse_baseline | 36.200 | 1,992 | 38 | native__lecleach_rollback | 6.252 | 921 | 30 |
| b3a__ath_core_14in | 17.765 | 9,871 | 120 | crease__core_law | 19.022 | 5,179 | 54 |
| b3a__biradial_keele | 10.258 | 6,145 | 57 | crease__osse_b1w | 8.407 | 2,070 | 26 |
| b3a__lecleach_rollback | 33.427 | 7,416 | 72 | control__osse_morph_b1w | 15.045 | 1,836 | 25 |

**The failure, exactly:**

```
invalid_geometry: outside the brief envelope (width 783 > 380.0 mm, height 581 > 300.0 mm)
```

**Reseeded and fixed the same night** (see section 7). The root cause was the curve STATION, not
just the width: at `gcurve_dist 0.5` the 335 mm outline sat halfway down the horn while the flare
kept growing to the mouth, so the full mirrored mouth measured 783 x 581 mm. The final seed puts the
outline at the mouth (`gcurve_dist: 1.0`, width 335), which caps the mouth at the pinned Morph
target: **335.2 x 291.5 mm** (depth 146 mm), **J 9.85253, 1,855 dofs, 3,543 triangles** (v3 T0).

A smaller-width workaround (dist 0.5, width 130) also measured valid (367 x 292, J 6.289) but was
rejected because it changed the intended mouth scale; its calibration table is kept as history:

| `gcurve_width` @ dist 0.5 | quarter bbox | full mouth | verdict |
|---|---|---|---|
| 150 | 204 x 158 | 408 x 316 | over |
| 192 | 247 x 188 | 494 x 376 | over |
| 280 | 336 x 252 | 673 x 503 | over |
| 140 | 194 x 147 | 388 x 294 | 8 mm over in width |
| 130 | 184 x 146 | 367 x 292 | valid: J 6.289, 2,047 dofs |

The width response at dist 0.5 is strongly non-linear near the top (a candidate at 142 already
measures 433 x 420 mm), which is why that workaround was fragile. At dist 1.0 the envelope is set
by the curve at the mouth, not by the width alone.

## 4. Mini-T1 - seed to best, with the term breakdown

Budget 60 for the three crease-class cells (equal budgets), 30 for the rest.

| cell | evals | valid | seed J | best J | gain | best dofs | s |
|---|---|---|---|---|---|---|---|
| crease__core_law | 61 | 39 | 19.022 | **2.784** | **85 %** | 4,835 | 2,005 |
| crease__osse_b1w | 61 | 44 | 8.407 | 8.407 | 0 % | 2,070 | 495 |
| control__osse_morph_b1w | 61 | 40 | 15.045 | 8.064 | 46 % | 1,902 | 446 |
| gcurve__osse_b1w | 11 | 0 | 1000 | - | - | - | 95 |
| b1t__rosse_morph | 31 | 14 | 23.534 | 17.575 | 25 % | 3,319 | 301 |
| b1w__osse_baseline | 31 | 25 | 13.288 | 10.165 | 24 % | 1,826 | 183 |
| b2t__lecleach_iwata_ar | 31 | 21 | 9.289 | 8.547 | 8 % | 3,079 | 194 |
| b3bt__salmon_x_signed | 31 | 12 | 17.077 | 13.154 | 23 % | 5,296 | 309 |
| native__lecleach_rollback | 31 | 31 | 6.252 | 5.600 | 10 % | 557 | 204 |

Raw terms with their **weighted** share of J (raw terms are unweighted; the share is
`weight x term / total`):

| cell | row | cov | rip | di | dislope | flat | load | total | dominant |
|---|---|---|---|---|---|---|---|---|---|
| crease__core_law | seed | 2.99 | 0.10 | 0.77 | 30.32 | 1.08 | 0 | 19.022 | dislope 80 % **>70 %** |
| crease__core_law | best | 0.68 | 0.15 | 0.71 | 2.13 | 1.37 | 0 | 2.784 | dislope 38 % |
| crease__osse_b1w | seed = best | 4.31 | 0.14 | 0.74 | 4.27 | 3.20 | 0 | 8.407 | cov 51 % |
| control__osse_morph_b1w | seed | 5.85 | 0.12 | 0.80 | 14.34 | 3.33 | 0 | 15.045 | dislope 48 % |
| control__osse_morph_b1w | best | 6.11 | 0.25 | 0.95 | 0.08 | 2.77 | 0 | 8.064 | cov 76 % **>70 %** |
| b1t__rosse_morph | best | 14.36 | 0.36 | 0.48 | 2.64 | 2.77 | 0 | 17.575 | cov 82 % **>70 %** |
| b1w__osse_baseline | best | 6.79 | 0.19 | 0.91 | 2.40 | 3.42 | 0 | 10.165 | cov 67 % |
| b2t__lecleach_iwata_ar | best | 7.84 | 0.01 | 1.90 | 84.19 | 0.24 | 0 | 8.547 | cov 92 % **>70 %** |
| b3bt__salmon_x_signed | best | 11.61 | 0.11 | 0.90 | 54.12 | 2.24 | 0.09 | 13.154 | cov 88 % **>70 %** |
| native__lecleach_rollback | best | 8.00 | 0.02 | 1.83 | 55.46 | 5.05 | 0.22 | 5.600 | flat 45 % |

**Four of the eight scored cells are effectively single-term** (cov 82-92 % on `b1t__rosse_morph`,
`b2t__lecleach_iwata_ar`, `b3bt__salmon_x_signed`, `control`), and the crease seed was 80 %
dislope. Two things follow:

- The weighted sum is being driven by whichever term happens to be numerically largest, not by the
  weights. The `dislope` term is ~30 raw with weight 0.5 while `rip` is 0.1 - a factor of 300 in
  numerical scale for the same nominal weight. **Normalise the terms** (divide by a per-term
  tolerance) before trusting any weight.
- **The Le Cleac'h loading experiment did not work.** `native__lecleach_rollback` has
  cov 0.3 / load 0.5 by design, yet the load term contributes `0.5 x 0.22 = 0.11` of 5.60 J - **2 %**.
  Flatness (45 %) and coverage (43 %) still own the score. `load 0.5` does not mean "loading
  matters"; the term's raw scale is 0.02-0.22 while flat is ~5. The intent of the scoring review
  needs the load term rescaled, not reweighted.

`f_load_hz` (from `metrics.scalars`, the first frequency where Re(z) stays >= 0.7): 500 Hz for
`native__lecleach_rollback` seed, 2,919 Hz for its best. Note the 500 Hz value is the **grid floor**,
not a measurement of the horn.

## 5. WALLS - what the best designs press against

Best 10 % of valid designs per cell (3-4 designs), within 3 % of a box edge.

| cell | knob | box | at lo | at hi | wall? |
|---|---|---|---|---|---|
| crease__core_law | `k` | 0.3..5 | 2/4 | 0/4 | **lo, half the best designs** |
| crease__core_law | `a_deg` | 0..40 | 1/4 | 0/4 | no |
| crease__core_law | `morph_fixed` | 0..0.6 | 1/4 | 0/4 | no |
| control__osse_morph_b1w | `n` | 1..10 | 2/4 | 0/4 | **lo** |
| control__osse_morph_b1w | `q` | 0.9..1 | 0/4 | 2/4 | **hi** |
| control__osse_morph_b1w | `a_deg` | 10..80 | 1/4 | 0/4 | no |
| crease__osse_b1w | `morph_fixed` | 0..0.6 | 1/4 | 0/4 | no |
| b1t__rosse_morph | `tmax` | 0.6..1 | 0/3 | 1/3 | no |
| b1t__rosse_morph | `exponent` | 2..10 | 1/3 | 0/3 | no |

Read: `k` at its lower edge and `n` at its lower edge / `q` at its upper edge are the only
repeated hard presses, and all three are **physical terminations** (a low `k`/`n` is a fast flare,
`q -> 1` is the smooth wall) rather than a brief-envelope artefact - the refusals that did occur were
`invalid_geometry` (89), not envelope (26). With only 3-4 designs in the top decile this table is
indicative; a 60-eval run gives too few designs to be confident. `tools/expand_walls.py` is still
owed.

## 6. Crease vs control - equal budget 60, same b1w brief

| | `crease__core_law` | `crease__osse_b1w` | `control__osse_morph_b1w` |
|---|---|---|---|
| brief | native CORE 2in (v3, f0 1280) | b1w (v3, f0 850) | b1w (v3, f0 850) |
| evals / valid | 61 / 39 | 61 / 44 | 61 / 40 |
| refusals | 16 geom + 6 too-large | 17 geom | 21 geom |
| seed J -> best J | 19.022 -> **2.784** | 8.407 -> 8.407 | 15.045 -> **8.064** |
| best dofs | 4,835 | 2,070 | 1,902 |
| a(p) 0/45/90, seed | 25.0 / 33.8 / 23.4 | 30.0 / 34.8 / 25.8 | - |
| a(p) 0/45/90, best | 18.0 / 34.7 / 31.5 | unchanged | - |
| crease strength (a45 - mean(a0,a90)) | +9.56 -> **+9.97 deg** | +6.86 | n/a |

- **The CORE law is the story of the night**: an 85 % J reduction that *kept* the diagonal crease and
  redistributed the walls (`a_deg` 5 -> 15.1, `az_sf_n1` 12 -> 21.9, `az_sf_n2` 15 -> 10.3,
  `morph_corner` 16.5 -> 5.9). It moved 13 of its 17 searched knobs; 5 of them by >15 % of the box.
- **`crease__osse_b1w` found nothing** - 44 valid designs, best = seed. The b1w seed with the law is
  already a local J optimum, so at equal budget the control, starting 6.98 J worse, ends lower
  (8.06 vs 8.41). **Indicative only: one seed each, and J cannot see the diagonals** - the crease
  cell may well be the better horn at 45 deg.
- **Queued, not run:** a T3 diagonal-balloon check on the best crease design vs the best control
  (45/135 deg planes), which is the only way to see what the crease actually buys.

## 7. `gcurve__osse_b1w` - failed as run, fixed by moving the curve to the mouth

**As it ran:** seed invalid (section 3); the T1 consumed only **11 of its 30 evaluations** and found
**0 valid designs**, so J stayed flat at 1000 and CMA-ES hit its flat-fitness stop after roughly one
generation (8 `invalid_geometry`, 3 `mesh_too_large`). That is what a flat penalty does to a search:
one generation, then nothing.

**The fix** (`gcurve_dist 0.5 -> 1.0`, width back to 335, box hi 0.9 -> 1.0): the mesher solves the
coverage angle so the wall meets the curve at `gcurve_dist x L`; at 1.0 that station is the mouth,
so 335 mm is the mouth width and the full mirrored mouth is bounded by the pinned Morph target.
Measured 335.2 x 291.5 mm (depth 146 mm). A budget-1 v3 T0:

```
search: gcurve__osse_b1w mode screen, budget 1 new evaluations, 24 bounded keys, output runs/20261027T030310Z-screen-f45d04
  evaluations 1 (1 new, 0 cached), failures {}, GPU 5.7 s, 7.1 s/candidate, 510/h
  seed J=9.85253  best J=9.85253 (did NOT improve on the seed); stop: budget
```

- **T0 result:** J **9.85253**, **1,855 dofs**, 3,543 triangles, objective v3. The dataset record
  landed (`dataset/shard-0030.jsonl`), so the same run also confirms the v3 record fix.
- **Trade-off:** the dist-0.5 / width-130 workaround measured J **6.289** (2,047 dofs, 367 x 292)
  and was the best b1w-based seed of the night, but it got there by changing the mouth scale. The
  dist-1.0 seed is the structurally correct one, beats the control seed 15.045, and is still worse
  than `crease__osse_b1w` 8.407 and the width-130 workaround. **One seed each - no ranking claim.**
- **Caveats:** it still cross-section-pins `aspect_ratio 1.0` while the control runs 1.15, so it is
  not a clean A/B; J sees only the H/V planes, so the diagonal effect of the guiding curve is
  invisible until the queued T3 balloon check.

## 8. Where the time went (observer)

`tools/observe_run.py` sampled every 5 s (384 samples). **The two phases must be read separately** -
the ladder rung monopolised the last 26 minutes at 100 % GPU and drags every whole-night average:

| window | samples | `gpu_solve` | `between_evals` | `refusal_or_mesh` | `cpu_idle` | GPU util median / mean |
|---|---|---|---|---|---|---|
| **search jobs (T0 + T1)** | 75 (~6 min) | **33 %** | **39 %** | **24 %** | 4 % | **24 % / 40 %** |
| ladder rungs | 309 (~26 min) | 92 % | 1 % | 0 % | 7 % | 100 % / 92 % |

- **The ladder is GPU-bound and saturated** (100 % util, 27 W median while the 17k rung thrashed in
  host memory).
- **The search is not.** In the observed search window the card spent only about a third of the
  time solving, ~39 % between evaluations (mesh/metrics/handoff) and ~24 % on refused candidates;
  median utilisation was 24 %. That is what a CPU/GPU pipeline would recover, and it is a bigger
  opening than the earlier rough estimate suggested.
- **Caveat, stated plainly:** that window is only ~6 minutes and covers the tail of one 31-eval cell
  (`t1__native__lecleach_rollback`) whose refusal rate may not be typical. The observer started at
  01:19 UTC, after most of the T1 batch. **This measurement should be repeated over a full search
  window before any pipeline work is scheduled** - it is cheap (the same tool, launched with the
  night) and it is the difference between a 1.5x and a 3x claim.
- VRAM during search: median **931 MiB** (the 7,748 MiB median in `observe_summary.md` is the rung).
  Power during search: 19 W median. Both confirm the card is idle-waiting, not working.

## 9. Known limits of this run

- **One seed per cell.** No seed-spread estimate, so no typology-beats-typology claim. The two-seed
  `compare` tier is the only way to get one.
- 30/60 evaluations is a *ranking* budget: the archive says 60 evals banks 85 % of the eventual
  improvement (median), 30 only 82 % with a p25 of 59 %.
- J reads **H/V planes only**; diagonal crease/X-shape benefit is invisible.
- Screen grid starts at **500 Hz**; the 300 Hz band floor is only exercised at verify.
- The loading term is band-averaged, diluted by the always-loaded high end, and numerically
  negligible (section 4).
- Coverage is graded to 8 kHz, past the 1.4-inch driver's ~5.6 kHz cross-mode (owner's choice).

## 10. Owed work

1. **DONE 2026-10-27:** `gcurve__osse_b1w` reseed - `gcurve_dist 1.0`, width 335, T0 J 9.853,
   1,855 dofs, 335.2 x 291.5 mm (section 7).
2. **Normalise the objective terms** before any weight tuning; the Le Cleac'h loading experiment
   shows weights do not currently mean influence (section 4).
3. **DONE 2026-10-27:** dataset records for v3 runs - the allowed versions now come from
   `objective/versions.py`, shared with the scorer dispatch; a live v3 T0 wrote a record. The smoke
   night's lost records are not reconstructable from this folder (section 10 note in CONTINUITY).
4. **Full offline suite** (deferred tonight by the owner).
5. **LHS audit of the widened boxes** (the T0/T1 refusal rates: 33 % overall) and
   `tools/expand_walls.py` (auto-widen an edge the best designs press against).
6. **Per-frequency timing instrumentation** and the 2-way concurrency A/B (section 8).
7. Sandbox per-direction law card: committed **unverified in a browser**.
8. The param-catalog generator does not recurse into `examples/typologies/campaign_*/`, so campaign
   configs still have no tooltips.
9. Shipped `osse_baseline` measures 803 x 643 mm against its own 750 x 600 envelope (+7.3 %).
10. `tools/make_shape_variants.py` + `examples/typologies/shape_variants/` stay **parked**
    (pre-research ranges, superseded by the crease cells).
