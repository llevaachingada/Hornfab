# Predeclared candidates, predictions and pass rules — CD variants of non-CD returned-lip horns

Written 2026-11-25T16:35Z, **before** any solve in this folder. Not edited after results; outcomes go in
[README.md](README.md). Later batches get dated addenda below, each written before its own solves.

## What is being tested

The families below were designed for loading or a natural narrowing pattern, not constant directivity
(knowledge card [lecleach_iwata.md](../../knowledge/typologies/lecleach_iwata.md); Salmon dossier). This batch
builds **explicitly labeled CD hybrids** of them, new identities scored on the CD brief only:

| Label | Kind | Parent (rows type, saved design) | Source run (original brief) |
|---|---|---|---|
| "Le Cléac'h AR + CD backbone" (`lcar`) | `rows_bb_v1` | `lecleach_ar` `5f7fbfc276b9` | `runs/20261119T205130Z-screen-5dbd97` (v7 smooth) |
| "Le Cléac'h H/V + CD backbone" (`lcl`) | `rows_bb_v1` | `lecleach` (H/V `fc`) `a85be6929ad5` | `runs/20261116T040157Z-screen-402831` (v7 smooth) |
| "Iwata AR + CD backbone" (`iwar`) | `rows_bb_v1` | `iwata_ar` `06a008612260` | `runs/20261119T062638Z-screen-03ae3c` (v7 smooth) |

None of these is ranked against the family's original-brief J. The control for each is **the unmodified parent
re-solved on the CD brief** (neutral `rows_bb_v1` wrapper; `tools/geometry/apply_cd_backbone.py --base-config`
checks it builds the bare parent's verify mesh byte-for-byte, and `tests/test_cd_backbone_geometry.py` repeats
that for `lcar`). All three source briefs use the same 36 mm / 2° driver and 600 × 480 × 480 mm envelope as the
CD brief, so the control is the same surface as the saved design.

## Fixed comparison

Brief `room_landscape_80x50_900_hf1440_v11cd` (embedded, from `rolled2_bb_control.yaml`), v11 frozen,
29-frequency verify grid, 1024-point balloon DI, freestanding quarter model, BEAT CUDA, `mesh.epw` 6.
Kernel `_cd_backbone_v1.py` unchanged; new adapter `cd_backbone_rows_family.py` (kind `rows_bb_v1`, its own
module so the batch 1–7 recipe digests are untouched). `g_bb_v` 0 in every job.

Jobs (configs in `examples/typologies/cd_variants_2026-11-25/`):

| Job | `bb_h` | throat | roll-in |
|---|---:|---:|---:|
| `<p>_control` | 0 | — | — |
| `<p>_bb_h065_v000_t25_r30` (the rolled keeper recipe) | 0.65 | 0.25 | 0.30 |
| `<p>_bb_h100_v000_t25_r30` | 1.0 | 0.25 | 0.30 |

for `<p>` in `lcar`, `lcl`, `iwar`: nine solves.

## Built-geometry facts (CPU, before these solves)

From `feasibility.py` → `feasibility.json` and `tools/shape_check.py --mode verify` (all nine pass, DOF
1769–2343, cap 24000; envelope fits; driver coupling round and matching the exit):

| Parent | Extents W × H × D mm | H chord / wall at 30 % / gap | V chord / gap | θc H at t0.25 r0.30 (r0.20) | θc V |
|---|---|---|---|---|---|
| `lcar` | 537 × 340 × 224 | 39.4 / 22.0 / 17.4° | 27.6 / 13.2° | 35.3° (38.4°) | 21.2° |
| `lcl` | 507 × 264 × 238 | 41.0 / 20.7 / 20.3° | 23.4 / 12.1° | 37.5° (40.6°) | 15.0° |
| `iwar` | 428 × 306 × 239 | 35.9 / 17.6 / 18.3° | 26.9 / 14.0° | 31.2° (34.5°) | 19.9° |
| reference: rolled bodies (passed) | 581–584 × 348–366 × 203–217 | 41.5–42.3 / 24.3° | 27.5–28.0° | 38.7–39.7° | 20.7–21.3° |
| reference: Lamé m0.40 (failed) | 490 × 281 × 210 | 38.5° | 24.8° | 33.7° | 15.9° |

Interior displacement at full strength 18.8 / 25.4 / 20.6 mm. These parents are sampled on a 15 × 32 grid
(rolled 65 × 129); the backbone is evaluated only at those stations.

## Predictions (stated in advance)

The predictor is θc at the keeper window relative to the two references: rolled (38.7–39.7°, passed) and
Lamé (33.7°, failed with a 2–3 kHz waistband and lost loading).

- **Controls show the HF defect.** Each control has H < 62° at 8 kHz on the CD brief (large gaps, slow early
  flare).
- **`lcl` 0.65: passes all six rules** (θc 37.5°, closest to the rolled bodies). Risk: its V body is the
  narrowest (θc V 15°), but V is untouched here.
- **`lcar` 0.65: passes rule 1** (H ≥ 62° at all five 6–8 kHz bins); all six rules are uncertain, called 50/50.
- **`iwar` 0.65: fails rule 1** (θc 31.2°, below the Lamé), and at 1.0 a 2–4 kHz waistband (rule 2) is expected.
- At full strength 1.0, every target fails at least one of rules 2 or 5 (rolled 1.0 did: 87° at 4 kHz and
  loading).
- ΔH at 8 kHz (candidate − control) ranks `lcl` ≥ `lcar` > `iwar` at both doses.
- V at 6–8 kHz changes by ≤ ±2° (indirect only).

## Pass rule (per candidate, against its own control)

Identical to [../cd_backbone_2026-11-25/PREDECLARED.md](../cd_backbone_2026-11-25/PREDECLARED.md), applied by
the same `analyze.py::check()`:

1. H ≥ 62° at 6085 / 6325 / 6977 / 7113 / 8000 Hz.
2. H 65–85° at every 2–4 kHz bin (2037, 2335, 2678, 3070, 3520, 4037).
3. V at 6–8 kHz not narrower than the control at any of the five bins.
4. No multilobe bins.
5. Minimum Re(z) from 900 Hz not worse than control − 0.1.
6. J not worse than the control (v11 frozen; J never selects alone).

If a control already fails rule 2 (it may, as the Lamé's did), that is reported; the candidate rule is unchanged.

Keeper per family: highest minimum 6–8 kHz H, then the narrowest 2–4 kHz H spread, then loading margin; **not J**.

## Refined-mesh gate (predeclared)

For each family's keeper only: control and keeper re-solved at `mesh.epw` 9. Pass = every HF-bin delta keeps
its sign and at least half its epw-6 size, and all six rules still hold at epw 9.

## Contingency (decided now, solved only after a dated addendum)

If a family waistbands (any 2–4 kHz bin below 65° where its control was not) or misses rule 1 at 0.65: try
roll-in 0.20 (raises θc, CPU above), then throat 0.30 for loading. If that still fails, stop and record the
reason; the next lever is mouth or depth, which is a separate, labeled scale step.

## Not in this batch, and why

- `salmon_elliptical` `63034eff4baf`: on the CD brief its outer height is **608.7 mm > 480 mm**; a CD variant
  needs a scale change first (separate, labeled step; owner's call on the look).
- `lecleach_asym` `fd63b53adeaf` and the 1-inch `lecleach` `5a5fa1c976c2`: designed for a 25.4 mm source and
  rebuilt here at 265–321 mm mouth and 138–149 mm depth, far below the brief's mouth; `lecleach_asym` is also
  full-span (`rows_bb_v1` is quarter-only) with ε ≈ 0.0004, i.e. effectively the axisymmetric case `lcl` covers.
- `iwata_ar` `b01fcfa4b50a` (b3bt): H chord 33.7°, θc 28.2° — below the 32° floor; held unless `iwar` passes.
- `klangfilm_lame*`: already tested (batch 6 of the backbone folder); the next Lamé lever is depth or mouth.
- `toroidal_rollback`: low priority (J 53 on its own brief).
