# X3 remaining parts - A7

Run: 2026-11-17, HEAD `4e05da5` when the analysis started (`git rev-parse --short HEAD`; the lane
brief said 87e3311 or later, and 4e05da5 is later). While the lane ran, the parent integrator
committed other lanes' work and HEAD is now `754a3a8`; that is not this lane's mutation (this lane
made none), and **no input used here changed between the two commits** - `git diff --name-only
4e05da5..HEAD` over `.fable`, `.e1`, `.x3`, `.n1b`, `.tmp` and the three X1/X3 briefs is empty, so
the numbers reproduce from either HEAD. Read-only CPU: no GPU or BEM solve, no solving CLI, no
pytest, no mesh build, no git mutation. Scripts and captured logs in
`scratch/fable_architecture/.x3c/`. Only `scratch/fable_architecture/` was written. A pre-existing
dirty `examples/.../b3_soft.yaml` and `.claude/worktrees/` were present and untouched (the same file
was committed by another lane during the run).

Data: the 1,715-design `.x3/extended.npz` sample (35 lanes, 22 sibling groups, 3 engines: OSSE 537 /
GRID 1,038 / GEN-FF 140; 29 lanes have >=30 designs), and the 70 contract-v2 surface records
`.n1b/build/*.npz` (65 stations x 61 azimuths). Targets are the stored archived curves
(`rows.pkl` bwh/bwv/di + `metrics.json` z/ripple/on-axis); no metric was regenerated, so
`compute_metrics` is never used. `.tmp/fable_replay_harness.py` is imported as `H` in
`.x3c/a7_common.py` to keep the replay rule's import in force, but no score is recomputed from a
response, and the 1,715-row target join is the one already validated by `.x3/extended.py` (all rows
finite).

Splits are byte-for-byte the `.x3/strict.py` lane / sibling / engine groups and the `sibling()` map;
`.x3/strict.py` at this HEAD reproduces `.x3/results.txt` exactly (`.x3c/strict_repro.txt`). Pass
lines below were copied before the new runs and not moved.

## Headline

1. **Whole-surface inputs do not meet the line and are underpowered as a representation test.** The
   60 N1b-passing records give scheme-3 pooled H/V/DI skill +.04 / -.02 / +.07; best engine GEN-FF
   H .370 / V .635, GRID .099 / -.055, OSSE -.202 / -.134 -> **0 of 3 engines** reach both planes
   >= .6. On the same 60 designs the 27-number profile baseline collapses to H -.06 / V .29 / DI .06
   (vs .75 / .87 / .78 on all 1,715), so the sample, not the representation, is the main limit.
2. **Explicit wavelength scaling (WL-1) raises skill but still fails the H plane.** Scheme 3:
   GEN-FF H/V/DI .582/.690/.434, GRID .288/.628/.527, OSSE .425/.770/.499. V >= .6 in **3/3**
   engines, H >= .6 in **0/3**, so the both-plane line is not met. Against the identical
   row-structure frequency-conditioned baseline (WL-2, which reproduces Part E exactly) WL-1 gains
   H +.092/+.031, V +.016/+.041, DI +.093/+.174 on GEN-FF/GRID, with one regression (OSSE H -.033).
3. **The transfer prior is worth a median of about 8 local solves, not 15.** The sibling-holdout
   prior alone reaches within-lane rank .621; the local-only curve reaches .618 at 48 designs
   (aggregate crossing >48), but per lane the prior is matched by 8 solves in 13/23 lanes and only
   10/23 need >=16. Transfer decays with position in the lane (.695 -> .575 across chronological
   quarters), and each extra solve buys about +.019 rank at 8->16, +.006 at 16->32, ~0 beyond 32.

## Representations fixed before the runs

- **Whole-surface, `surface-32v1`.** Inner sheet of the stored contract record (sampled coordinates
  in mm on the quarter model, 61 azimuths); resampled to 32 uniform arc stations; per station
  half-width W = max x, half-height H = max y, mean depth z, quarter-section area A (shoelace in
  x-y), aspect W/H, shape index A/(W*H), wall angle atan2(dr/dz). Plus full mouth width 2W, full
  mouth height 2H, total depth: **227 features**. `surface-8v1` repeats it at 8 stations (59
  features) as a variance check. Units are mm (full horn = 2x the quarter record). Construction
  check against the stored quarter box: full inner W/H minus 2*bbox has median -0.38 / -0.10 mm and
  max |delta| 2.72 / 3.56 mm (per-lane medians: ATH -1.87/-2.61, biradial 0.00/-0.15, Crowe
  -0.75/-0.96, ext-throat 0.00/0.00, Klangfilm -0.06/-0.06, rounded-section -0.49/-0.07).
- **Wavelength-scaled, `WL-1`.** For design i and frequency f_k, features z(i,k) = x_i * (2*pi*f_k/c),
  with x_i the 27 mesh-derived lengths in mm (`.fable/an3.py desc`; all 27 columns are lengths) and
  **c = 343.0 m/s** (20 degC, `hornlab_search/constants.py` `C_AIR`, "not 344"). No separate
  frequency channel.
  Training rows are every training design x every stored frequency (18); held-out rows are held-out
  designs x the scoring band f >= 600 Hz (14 of 18). A fixed 1000 (mm vs m) makes the features a
  constant multiple of ka; trees are invariant to it, and it is left explicit. Model:
  ExtraTrees(40 trees, leaf 3, seed 0), the Part E model.
- **Controls.** `WL-0`: same per-frequency row structure, raw lengths, no frequency information.
  `WL-2`: `[x_i, ln f_k]`, the Part E frequency-conditioned baseline. Scaling lengths by
  2*pi*f_ref/c at f_ref = 1000 Hz is a constant monotone rescale that trees ignore, so WL-2 is the
  same representation and avoids float-threshold noise. WL-2 reproduces `.x3/augment.txt` exactly
  (Table 3).
- **Learning-curve protocol.** Per lane, order by row `created` (ties: run, hash); test = the **last
  16** designs; training = the **first n** designs (expanding window), n in {8,16,32,48}; a 10-rep
  random-prefix variant (seed 42) is reported beside it. `local` = model on X; `plus` = model on
  [X, prior coverage prediction]. Prior = ExtraTrees(100, leaf 2, seed 0) trained on every design
  whose sibling group differs (**scheme-2 rule, unchanged**); a second engine-holdout prior is
  reported only for comparison. Lanes with N >= 40 (23 lanes, 1,475 designs) are used; the target is
  the strict coverage proxy (f >= 600 Hz, asymmetric 80x50) and the metric is Spearman.

## Table 1 - three schemes against the pass lines (denominators in the first column)

Pooled skill is 1 - SSE/SSE(training-mean) over the band; rank is median within-lane Spearman of the
coverage proxy over the 29 lanes with >=30 designs (n/a where a lane cannot hold 30 held-out designs).

| Input | n / lanes / sibling groups / engines | lane H/V/DI | sibling H/V/DI | engine H/V/DI | rank lane / sibling / engine |
|---|---|---|---|---|---|
| Size | 1,715 / 35 / 22 / 3 | .558/.752/.617 | .486/.735/.582 | .193/.514/.315 | .412/.422/.423 |
| Two-plane profiles | 1,715 / 35 / 22 / 3 | .752/.871/.776 | .696/.845/.720 | .238/.565/.308 | .761/.720/.489 |
| WL-0 (per-frequency, no frequency information) | 1,715 / 35 / 22 / 3 | -1.530/-2.396/-2.508 | -1.502/-2.274/-2.450 | -.518/-.584/-.828 | .410/.280/.170 |
| **WL-1 (wavelength-scaled)** | 1,715 / 35 / 22 / 3 | **.785/.880/.809** | **.728/.853/.746** | **.336/.668/.515** | **.789/.751/.500** |
| WL-2 control (parity, engine folds only) | 1,715 / 35 / 22 / 3 | - | - | see Table 3 | - |
| Whole-surface 32v1 | 60 / 6 / 6(1) / 3 | .218/.234/.256 | .218/.234/.256(1) | .041/-.018/.074 | n/a(2) |
| Whole-surface 8v1 | 60 / 6 / 6(1) / 3 | .226/.125/.215 | .226/.125/.215(1) | .114/-.130/.058 | n/a(2) |
| Profiles at matched n=60 | 60 / 6 / 6(1) / 3 | -.060/.293/.057 | -.060/.293/.057(1) | -.154/.217/-.052 | n/a(2) |
| Profiles + surface32 at n=60 | 60 / 6 / 6(1) / 3 | .220/.287/.276 | .220/.287/.276(1) | .119/.045/.131 | n/a(2) |

(1) On this 60-design sample the 6 lanes are 6 distinct sibling groups, so lane and sibling folds
coincide; they are not independent evidence.
(2) No lane has 30 held-out designs in a 60-design sample, so the stated within-lane rank line cannot
be computed for whole-surface inputs. The cross-design cov rank printed in the log (GEN-FF .66, GRID
.61, OSSE .75 on 10-30 points) is **not** that metric.

## Table 2 - scheme 3 per engine (the headline scheme)

| Input | GEN-FF n=140 | GRID n=1,038 | OSSE n=537 | Engines with H>=.6 and V>=.6 |
|---|---|---|---|---|
| Size | .288/.498/.271 | .127/.439/.223 | .346/.717/.493 | 0 of 3 |
| Two-plane profiles | .527/.715/.461 | .162/.506/.220 | .389/.703/.460 | 0 of 3 (GEN-FF H .527) |
| WL-1 | **.582/.690/.434** | **.288/.628/.527** | **.425/.770/.499** | **0 of 3** (H 0/3, V 3/3) |
| Whole-surface 32v1 (n=10/30/20) | .370/.635/.418 | .099/-.055/.098 | -.202/-.134/-.056 | 0 of 3 |
| Profiles at matched n=60 | .077/.182/-.009 | -.088/.300/-.016 | -.383/.035/-.125 | 0 of 3 |
| Size at matched n=60 | -.038/-.012/-.124 | .061/.104/.101 | .415/.469/.405 | 0 of 3 |

## Table 3 - WL-1 against the controlled baseline (same rows, same model, same folds)

Engine folds only, because WL-2 is the Part E model; its numbers are identical to
`.x3/augment.txt`'s unaugmented baseline (GEN-FF .4903/.6740/.3413; GRID .2569/.5871/.3538; OSSE
.4587/.7552/.5075), which is the implementation parity check.

| Engine | WL-2 [x, ln f] H/V/DI | WL-1 [x*2*pi*f/c] H/V/DI | delta H / V / DI |
|---|---|---|---|
| GEN-FF | .490/.674/.341 | .582/.690/.434 | +.092 / +.016 / +.093 |
| GRID | .257/.587/.354 | .288/.628/.527 | +.031 / +.041 / +.174 |
| OSSE | .459/.755/.508 | .425/.770/.499 | -.033 / +.015 / -.009 |

WL-0 (per-frequency rows, raw lengths, no frequency channel) scores -.38 to -2.51: without either an
explicit frequency channel or the scaling, the same model cannot serve 18 frequencies at all. The
gain in Table 3 is therefore attributable to how frequency enters, not to the extra training rows
(WL-0 has the same row count).

## Table 4 - whole-surface matched comparison (same 60 designs)

Extra targets are from stored `metrics.json` (Re Z, H/V in-coverage ripple, on-axis) at the same 14
band points. Only the pooled engine column is shown here; per-engine and per-target numbers are in
`.x3c/a7_surface.txt`.

| Input | H | V | DI | Re Z | H ripple | V ripple | On-axis |
|---|---|---|---|---|---|---|---|
| surface-32v1, lane/sibling | .218 | .234 | .256 | -.026 | .210 | .205 | -.127 |
| surface-32v1, engine | .041 | -.018 | .074 | .077 | .161 | .057 | -.006 |
| surface-8v1, engine | .114 | -.130 | .058 | .136 | .211 | -.028 | .020 |
| profiles at n=60, engine | -.154 | .217 | -.052 | -.172 | -.312 | -.444 | -.144 |
| profiles+surface32, engine | .119 | .045 | .131 | .072 | .188 | .073 | .014 |
| size at n=60, engine | .149 | .195 | .184 | -.141 | .154 | .010 | -.065 |

Against the matched profile baseline, surface-32v1 is better on H (+.278 lane-pooled, +.18 to +.29
per engine), worse on V at lane level (-.06) and mixed per engine (+.45 GEN-FF, -.36 GRID, -.17
OSSE), and better on DI (+.20 lane-pooled). Adding the surface descriptor to the profiles gives the
best whole-surface-sample result (OSSE rises from -.38/-.04 to +.11/+.13) but still nowhere near .6.

## Table 5 - within-lane learning curve (rank of coverage error)

Medians over lanes; the prior row is the prior model alone, not a curve point.

| n local designs | local, chronological prefix | plus (prior as feature) | local, random prefix | plus, random prefix | lanes |
|---:|---:|---:|---:|---:|---:|
| 0 - prior only | .621 | - | .621 | - | 23 |
| 8 | .240 | .218 | .376 | .478 | 23 |
| 16 | .585 | .459 | .524 | .585 | 23 |
| 32 | .576 | .612 | .615 | .698 | 20 |
| 48 | .618 | .722 | .614 | .724 | 16 |

- **Value of the prior.** Of the 13 lanes matched at n=8, 7 have a negative prior, so that mode is a
  ceiling rather than a gain. Aggregate crossing (local median reaches prior .621): **>48 local
  solves** on both prefixes. Per lane: 13 matched at n=8, 4 at 16, 1 at 32, 1 at 48, and 4 need more
  than 48; 10 of 23 need >=16. The prior is positive in 16/23 lanes and negative in 7.
- **Value of an additional solve.** +.019 rank per solve over 8->16, +.006 over 16->32, ~0 over
  32->48 (random-prefix curve). The chronological curve is flat after 16 because its prefix is the
  seed region, not a random sample of the lane.
- **Prior as a feature.** Harmful at n=8/16 (-.02/-.13) and helpful at n=32/48 (+.04/+.10): with a
  handful of rows the forest cannot use a single scalar channel, and the prior alone is better than
  a 16-design local model.
- **Engine-holdout prior** (the Part F regime): last-16 median .497 versus .621 for the
  sibling-holdout prior, so the solve-equivalent is prior-dependent.

## Table 6 - transfer against position in the lane's chronological order

23 lanes with N >= 40, each cut into four contiguous chronological blocks; median within-block
Spearman of true vs prior coverage error.

| Quarter of lane history | median rank | IQR | lanes |
|---|---:|---|---:|
| 1 (earliest) | .695 | .354 / .883 | 23 |
| 2 | .643 | .056 / .787 | 23 |
| 3 | .642 | -.042 / .869 | 23 |
| 4 (latest) | .575 | -.055 / .779 | 23 |

The prior is most useful on a lane's early (near-seed) designs and decays on the optimised tail.

## Table 7 - per-lane prior rank and solve value (last 16 designs)

`prior` is the sibling-holdout prior alone; `worth` is the smallest tested n whose local model
matches that lane's prior.

| Lane | N | Engine | prior | local 8 | local 16 | local 32 | worth (solves) |
|---|---:|---|---:|---:|---:|---:|---|
| `hl__crowe_panel_home_v7` | 70 | GRID | .912 | .906 | .944 | .956 | 16 |
| `hl__lecleach_iwata_ar_landscape_v7` | 70 | GRID | .891 | .690 | .855 | .688 | >48 |
| `hl__ath_tritonia_landscape_v8` | 70 | OSSE | .824 | .069 | .356 | .353 | >48 |
| `hl__osse_rrect_fold_warm_v7` | 70 | OSSE | .779 | .176 | .324 | .506 | >48 |
| `hl__ath_tritonia_landscape_v9` | 70 | OSSE | .765 | .094 | .153 | .556 | >48 |
| `hl__ath_twinray380_landscape_v8` | 70 | OSSE | .726 | .029 | .194 | .341 | 48 |
| `rf__section_axial_home_v7` | 51 | GRID | .794 | .784 | .876 | .832 | 16 |
| `hl__ath_core_petal_hvlaw_v7` | 46 | OSSE | .771 | .677 | .776 | - | 16 |
| `hl__ext_throat_hvlaw_v7` | 70 | OSSE | .741 | .765 | .835 | .750 | 8 |
| `rf__section_axial_home_smooth_v8` | 55 | GRID | .721 | .858 | .850 | .853 | 8 |
| `hl__crowe_x_osse_cd_v7` | 70 | GRID | .624 | .820 | .792 | .676 | 8 |
| `hl__klangfilm_lame_curved_v1` | 70 | GRID | .621 | .818 | .809 | .915 | 8 |
| `hl__rolled_es_spiral_v7` | 61 | GRID | .579 | .056 | .624 | .703 | 16 |
| `hl__lecleach_iwata_ar_landscape_smooth_v7` | 70 | GRID | .324 | .706 | .570 | .596 | 8 |
| `hl__es_style_rollback_v7` | 70 | GRID | .121 | .556 | .683 | -.100 | 8 |
| `sp__moderate_v7` | 47 | GRID | .115 | .144 | .244 | - | 8 |
| `hl__biradial_es_style_smooth_v7` | 70 | GEN-FF | -.053 | .071 | .441 | .379 | 8 |
| `rr__crowe_panel_es600_v7` | 70 | GRID | -.082 | .240 | -.624 | -.479 | 8 |
| `sp__control_v7` | 48 | GRID | -.147 | -.040 | .585 | .535 | 8 |
| `hl__biradial_es_style_v7` | 70 | GEN-FF | -.335 | .550 | .709 | .541 | 8 |
| `sp__strong_v7` | 47 | GRID | -.376 | -.297 | .109 | - | 8 |
| `hl__rosse_rect_cd_v7` | 70 | GRID | -.468 | .053 | -.026 | .679 | 8 |
| `hl__osse_rrect_morph_v7` | 70 | OSSE | -.579 | -.779 | -.647 | .112 | 32 |

Strongest lane: **`hl__crowe_panel_home_v7`** (prior .912, local 16 already .944). Weakest:
**`hl__osse_rrect_morph_v7`** (prior -.579, while its warm-start sibling lane
`hl__osse_rrect_fold_warm_v7` has +.779: the name-normalised sibling map does not capture that
construction link, see Table 8). The GEN-FF lanes are the clearest failure of the prior itself
(biradial -.05 and -.34): the sibling holdout for biradial is the only GEN-FF construction in the
sample, so the prior is trained entirely on other engines.

## Table 8 - sibling lineage of the groups in the base

Full table (22 groups, 75 runs) in `.x3c/a7_lineage.txt`. Versions/twins are merged exactly as
`.x3/strict.py`; seed comparisons are from `.x3/seeds.json`.

| Group (multi-lane only) | Lanes (n) | Engine | Runs | Start categories | Seed check |
|---|---|---|---|---|---|
| ATH Tritonia | v7 (15), v8 (70), v9 (70) | OSSE | 5 | 4 hand-written, 1 warm start | 14-19 fields differ; same generator |
| Biradial ES | smooth_v7 (70), v7 (70) | GEN-FF | 6 | all hand-written | 9 fields differ |
| Ext-throat H/V-law | v7 (70), v8 (24) | OSSE | 3 | 2 hand-written, 1 parent-best | 8 fields differ |
| Le Cleac'h Iwata AR | smooth_v7 (70), v7 (70) | GRID | 3 | 2 hand-written, 1 parent-best | **0 fields differ** |
| OSSE rounded-rect | morph_v7 (70), v8 (32) | OSSE | 2 | 1 each | 14 fields differ |
| `rf__section_axial_home` | smooth_v8 (55), v7 (51) | GRID | 3 | 2 hand-written, 1 parent-best | 8 fields differ |
| Reference/pucker | reference_v7, pucker moderate/strong (32 each) | GRID | 3 | all hand-written | 2 pucker fields |
| sp control/moderate/strong | 48/47/47 | GRID | 3 | all hand-written | 2 pucker fields |
| Klangfilm H/V axis variants | a0/a1/a2 (1 each) | GRID | 3 | all parent-best | 2-3 axis fields |

Cross-group lineage that the fixed map does **not** merge (4 parent links, all "best design of an
earlier run"):

- `hl__osse_rrect_fold_warm_v7` <- `hl__osse_rrect_morph_v7` best (J 3.992).
- `klangfilm_hv__a0`, `a1`, `a2` <- `hl__klangfilm_lame_curved_v1` best (J 8.439).

Direction of bias: scheme 2 can leak along these two families, so its scores are optimistic. The
conclusion that the headline scheme fails does not depend on it. The map is otherwise conservative:
it merges deliberate A/B variants (pucker/control/strong) that share a generator but differ in 2
seed fields.

## Verdict against the stated pass lines

| Pass line (fixed before the run) | Denominator | Result | Status |
|---|---|---|---|
| Scheme 3 skill R^2 >= .6 on **both** H and V for **at least 2 of 3** engines | 3 engines per input row (5 rows) | Best H anywhere = .582 (WL-1 GEN-FF); best both-plane engine count = 0/3 for size, profiles, WL-1, whole-surface | **Not met** (also not met for either new input) |
| Within-lane rank >= .6 median | 29 lanes >=30 designs (1,715 inputs); n/a for 60-design inputs | Profiles .761/.720/.489; WL-1 .789/.751/.500; whole-surface n/a | **Not met on scheme 3** (.489/.500); met on schemes 1-2 |
| Prior worth >= 15 local solves | 23 lanes >=40 designs | Per-lane median 8; 10/23 >=16; aggregate curve crossing >48 | **Not demonstrated** (metric-dependent; Table 5) |
| Part D residual skill > .2 | 3 engines | Unchanged from `.x3/results.txt` (.382/.122/.179 GEN-FF, .166/.235/.164 GRID, -.292/-.198/-.106 OSSE) | **Not re-run; still not established** |

## What failed / what is unknown

- **The whole-surface verdict is not attributable to the representation.** Only 60 designs have
  contract records (10 in each of the 6 N1b-passing lanes); 25 of the 60 lie outside the
  per-lane-capped 1,715 sample; the 6 lanes are 6 distinct constructions, so the matched profile
  baseline also collapses (-.06 H). With 227 features and about 30-50 training rows the model is
  fitting noise; `surface-8v1` behaves differently (V -.13 vs +.23), a variance symptom rather than a
  stable ranking.
- **Whole-surface geometry has two stated mismatches.** The description is the generator inner sheet;
  for Crowe the mesher departs by <=1.64 mm and for rolled by <=0.70 mm at corners (X1B v2 rule 3),
  and the stored box includes the outer sheet/rim (per-lane inner-vs-box bias above). The acoustic
  truth remains the solved mesh.
- **Le Cleac'h is excluded, not substituted.** Its 10 records are not N1b-passing (not reproducible at
  HEAD). No other surface family was substituted, per the lane instruction.
- **Wavelength scaling: H is still short everywhere.** WL-1 is a real gain over WL-2 on GEN-FF and
  GRID but slightly worse on OSSE H; the 27 length columns carry no section shape/aspect/angle, so
  the residual may be representational rather than a scaling failure. `c` is fixed at 343 m/s (no
  temperature sensitivity), no scale-copy augmentation is combined with WL-1, and no prospective
  design was ranked.
- **Solve value depends on which prior and which curve.** Sibling-holdout prior .621 vs engine-holdout
  .497; chronological prefix .618 at 48 vs random prefix .614; the aggregate crossing says >48 while
  the median lane says 8. The smallest tested n is 8, so the brief's "<5 solves" failure line cannot
  be resolved in either direction.
- **Chronology is row `created`.** Within a run that is solve order; concurrent lanes interleave but
  each lane's own order is preserved. The last-16 test window is a small, late, tightly clustered
  region, so each lane's rank has a wide interval (P1 IQRs are large).
- **The prior is not free.** It embodies roughly 1,400 designs from other lanes of the same brief; a
  "worth" in local solves is not a saving measured against no prior work.
- **Two documented sibling-lineage links sit outside the fixed map** (Table 8), so scheme 2 is
  optimistic in those families. Seed differences are not proof of different constructions; the
  sibling map still lacks a full all-run construction reconstruction (A11's remaining item).

## What this does not prove

- Nothing acoustic: every number is a retrospective model-vs-stored-response skill on already-solved
  designs. No candidate geometry is proposed or scored, and no design outside the training support is
  reported as a prediction - such a design would have to be marked outside.
- That whole-surface descriptors are useless: the 60-design, 6-lane sample cannot test the claim, and
  the surface+profile combination is better than profiles alone on H/DI there.
- That wavelength scaling solves transfer: the both-plane line fails on H in all three engines.
- That the prior's rank is a solve saving: it is a retrospective rank on visited, clustered designs.
- That any lane or family should be cut or re-prioritised; no owner-requested family is implicated.

## Next action

1. **Do not commission another whole-surface transfer test at n = 60.** The blocking gap is record
   coverage, not modelling: extend `.n1b`-style contract records to every design in the six
   N1b-passing lanes (~420 designs, generator-only CPU builds, no BEM). Then repeat `a7_surface.py`
   unchanged; the lane/sibling folds stop coinciding and the rank line becomes computable.
2. **If the H plane matters, add the contract's section curves.** `surface-32v1` already carries
   area/aspect/shape/angle, but the 27-number input has none. Table 3 shows the frequency treatment
   is worth having; the residual H deficit is the input's missing section shape.
3. **Prospective learning-curve replay** (CPU): hold out a lane's future run, not its last 16 rows,
   and evaluate the prior + n local solves on that run. That is the only way to convert Table 5 into
   a campaign solve-value claim; the present curves are retrospective.
4. **Leave the sibling map as specified**; report the two cross-group lineage links to whoever owns
   the lineage inventory (A11). If a stricter scheme is wanted, it must be declared before the run.
5. The owner-approval 20-solve prospective BEM test remains a proposal and was not run.

## Reproduce

From `C:\Users\hunte\Hrns\hornlab-search`:

```powershell
git rev-parse --short HEAD                                   # 4e05da5
.venv/Scripts/python.exe scratch/fable_architecture/.x3/strict.py
.venv/Scripts/python.exe scratch/fable_architecture/.x3c/a7_wl.py
.venv/Scripts/python.exe scratch/fable_architecture/.x3c/a7_wl.py --wl2
.venv/Scripts/python.exe scratch/fable_architecture/.x3c/a7_surface.py
.venv/Scripts/python.exe scratch/fable_architecture/.x3c/a7_learning.py
.venv/Scripts/python.exe scratch/fable_architecture/.x3c/a7_lineage.py
.venv/Scripts/python.exe scratch/fable_architecture/.x3c/a7_rankcheck.py
```

Captured output: `.x3c/strict_repro.txt`, `a7_wl.txt`, `a7_wl2.txt`, `a7_surface.txt`,
`a7_learning.txt`, `a7_lineage.txt`, `a7_rankcheck.txt`, `a7_probe.txt`, `a7_import_check.txt`.
`a7_wl.py` takes about 7 min on CPU; the rest are under a minute each. No file outside
`scratch/fable_architecture/` was written; `runs/`, `examples/`, `hornlab_search/` and `tools/` were
read only.
