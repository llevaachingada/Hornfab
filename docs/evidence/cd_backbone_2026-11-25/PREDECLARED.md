# Predeclared candidates, predictions and pass rules — CD wall-angle backbone

Written 2026-11-25T00:56Z, **before** any solve in this folder. Not edited after results; outcomes go in
[README.md](README.md).

## Fixed comparison

Construction and construction math:
[RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md](../../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md)
(section 3). Kernel `hornlab_search/design/generators/_cd_backbone_v1.py`, adapter
`cd_backbone_family.py` (kinds `rolled_family_rect_bb_v1`, `klangfilm_lame_hv_bb_v1`). LABELED
HYPOTHESIS; no published name.

Every candidate is its control with only `g_bb_h` / `g_bb_v` changed. Parent knobs, brief
`room_landscape_80x50_900_hf1440_v11cd` (embedded), 36 mm / 2° assumed source, freestanding quarter
model, BEAT CUDA, 29-frequency verify grid, 1024-point balloon DI, `mesh.epw` 6 are unchanged.
`g_bb_throat_frac` 0.15 and `g_bb_rollin_frac` 0.30 for every job; `g_bb_v` 0 everywhere.

Controls (already solved; meshes byte-identical to the neutral adapters, `neutral_parity.json`):

| Control | Run dir | J | Design hash |
|---|---|---:|---|
| rolled anchor `fa5b207bca6d` | `runs/rolled_lame_anchor_verify_2026-11-24/rolled` | 8.1209 | `fa5b207bca6d` |
| Lamé `lame_morph_040` (`g_morph_frac` 0.40) | `runs/20261124T235357Z-verify-dd210e` | 9.0845 | `69a8df8d79b4` |

Widths are full −6 dB widths at the saved verify frequencies (no interpolation).

| Bin set | Saved frequencies (Hz) |
|---|---|
| HF (6–8 kHz) | 6085, 6325, 6977, 7113, 8000 |
| 2–4 kHz | 2037, 2335, 2678, 3070, 3520, 4037 |
| Mid (1–4 kHz) | 1028 … 4037 (9 bins) |

Control values at the bins above (H / V, degrees):

| Control | 2037 | 3070 | 4037 | 6085 | 6977 | 8000 |
|---|---|---|---|---|---|---|
| rolled | 90.1 / 74.0 | 76.2 / 65.8 | 70.4 / 61.5 | 62.5 / 52.0 | 59.0 / 49.4 | 54.8 / 47.7 |
| Lamé m0.40 | 69.5 / 82.4 | 60.7 / 63.3 | 60.4 / 55.3 | 58.0 / 45.1 | 54.8 / 41.4 | 51.6 / 37.8 |

Full-bin control rows: 6325 rolled 61.6 / 51.2, Lamé 57.2 / 44.1; 7113 rolled 58.4 / 49.1, Lamé
54.3 / 40.9; 2335 / 2678 / 3520 rolled H 87.9 / 83.4 / 73.3, Lamé H 64.2 / 61.5 / 60.2 (read from the
saved metrics).

Correction 2026-11-25T01:25Z: the 2335 / 2678 / 3520 control row above was mistyped when this file was
first written (it read 83.6 / 78.6 / 73.3 and 63.6 / 61.1 / 60.2). It has been replaced with the values
read from the saved control metrics. No prediction, bin set or pass rule changed; the solves were already
complete when the correction was made.

## Built-geometry facts (CPU, before these solves)

Measured by `tests/test_cd_backbone_geometry.py` (32 tests pass with the parent suites, junitxml
`runs/cd_backbone_tests.xml`):

- Throat, roll-on station, return and rim stay within **1e-13 mm**; the V-plane row is untouched
  when `bb_v` = 0; inner extents exact. Zero strength returns the parent object unchanged
  (`neutral_parity.py`: all three controls build the saved verify meshes byte-for-byte).
- Shell re-offset changes rolled overall depth by 0.0017 mm (test bound 0.01 mm).
- Interior displacement: **15.5 / 31.0 mm** (rolled, `bb_h` 0.5 / 1.0) and **8.2 / 16.4 mm** (Lamé
  on `morph_frac` 0.40).
- Solved body angle θc: **36.51° H** (rolled) and **32.22° H** (Lamé m0.40), throat 0.15, roll-in 0.30.
- `tools/shape_check.py --mode verify` (2026-11-25T00:52Z, CPU, gmsh): all four candidates yes,
  DOF 3579 / 3620 (Lamé) and 3632 / 4409 (rolled), cap 24000; envelope fits; driver coupling round
  and matching the exit; extents 581 × 366 × 217 mm (rolled) and 490 × 281 × 210 mm (Lamé).

## Candidate predictions (heuristic, extrapolated)

Source: `backbone_feasibility.py` / the dossier's station-map estimate. The heuristic was fitted on
small changes; these candidates move the interior by 8–31 mm, so the numbers are **screening
predictions, not evidence**. A linear half-strength row is an even rougher interpolation.

| Job | Change vs control | Predicted H at 2 / 4 / 6 / 8 kHz |
|---|---|---|
| `rolled_bb_h050` | `bb_h` 0.5 | ≈ 88 / 74 / 68 / 63° |
| `rolled_bb_h100` | `bb_h` 1.0 | ≈ 85 / 77 / 74 / 71° |
| `lame_bb_h050_m040` | `bb_h` 0.5 on m0.40 | ≈ 71 / 65 / 62 / 58° |
| `lame_bb_h100_m040` | `bb_h` 1.0 on m0.40 | ≈ 73 / 69 / 66 / 64° |

Expected V: unchanged on the V plane by construction (`bb_v` = 0, that row bit-identical); any V
change is indirect and predicted within ±2°.

Risk stated in advance: a conical body with a fixed return can **waistband** at 2–4 kHz (Keele;
Kolbrek), and the 2 kHz H of the rolled control already sits at the 90° corridor edge.

## Pass rule (per candidate, against its own control)

A candidate passes only if **all** of the following hold:

1. **H ≥ 62° at all five 6–8 kHz bins** (6085, 6325, 6977, 7113, 8000).
2. **H 65–85° at every 2–4 kHz bin** (2037, 2335, 2678, 3070, 3520, 4037) — no mid-band dip.
3. **V at 6–8 kHz not narrower than the control** at any of those five bins.
4. **No new multilobe bins** (`n_multilobe_h/v` = 0, as on both controls).
5. **Loading:** min Re(z) from 900 Hz not worse than the control by more than 0.1 (rolled control
   0.991, Lamé m0.40 control 0.717).
6. **J not worse** than the control (rolled 8.1209, Lamé m0.40 9.0845), v11 frozen; J alone does not
   promote and its raw terms are reported beside the widths.

Reported but not part of the pass rule: diagonal (45°) width, DI and DI slope, 1–8 kHz on-axis
residual, ripple and `di_roughness`, and the 1–4 kHz V trade-off bin by bin.

## Refined-mesh gate (predeclared)

For each family's best passing candidate only: same config with `mesh.epw` 9, and the existing
epw-9 controls (`rolled_anchor_epw9` J 8.0821, `lame_morph_040_epw9` J 9.0593 in
`runs/nights/directivity_attribution_b2_2026-11-24/summary.jsonl`). Pass = every predeclared HF-bin
delta keeps its sign and at least half its epw-6 size, the 2 kHz H change keeps its sign, and the
pass rule above still holds at epw 9.

This is one refinement step of the element size on the same surface grid, not a convergence study.


## Addendum, written 2026-11-25T01:40Z after batch 1/2 and before any dose-bracket solve

`rolled_bb_h050` passed every rule and `rolled_bb_h100` failed on the 2–4 kHz ceiling (87.0 deg at 4037 Hz) and
loading (min Re(z) 0.610). This bracket locates the boundary between them. It is a new, post-hoc extension, not a
retest: the same fixed comparison, the same bins and the same pass rule apply, and all three jobs are reported
whatever the outcome.

Jobs: `rolled_bb_h035`, `rolled_bb_h045`, `rolled_bb_h065` — `rolled_bb_h050.yaml` with only `g_bb_h` changed
(window 0.15 / 0.30, `bb_v` 0). `epw` 6, v11 frozen.

Prediction method (stated in advance): linear interpolation in `g_bb_h` between the two measured doses
(`bb_h` 0.5 and 1.0), bin by bin. It is a bookkeeping device, not a physical model.

| Job | Predicted H at 2 / 4 / 6 / 8 kHz | Predicted 2–4 kHz H band | Predicted V 6–8 kHz | Predicted J |
|---|---|---|---|---|
| `rolled_bb_h035` | 84 / 68 / 63 / 62 | 68.2–83.6 | 48.1–51.9 | ≈ 5.36 |
| `rolled_bb_h045` | 82 / 72 / 66 / 64 | 71.1–81.6 | 48.7–52.1 | ≈ 5.39 |
| `rolled_bb_h065` | 78 / 75 / 73 / 69 | 73.3–78.6 | 49.8–52.6 | ≈ 5.45 |

Loading is expected to fall with dose, but it is not interpolable from two points; it is reported, not predicted.
Boundary criterion (for the record): the largest `g_bb_h` that still satisfies all six rules of the main pass rule
above; if `bb_h` 0.65 already fails, the passing interval is bracketed to (0.5, 0.65).

## Addendum, written 2026-11-25T15:39Z after batch 3 and before any batch-4 solve

**Why this batch.** The only rule `rolled_bb_h065` failed is loading, and its minimum sits at **896 Hz** (Re z 0.864 vs
the 0.891 floor). Re(z) at 896 Hz falls monotonically with dose (control 1.63, `bb_h` 0.35/0.45/0.50/0.65/1.0:
1.17/1.06/1.01/0.86/0.61) and is identical to two decimals at epw 6 and epw 9 for both the control and `bb_h` 0.50.
So the handoff's epw-9 re-check of 0.65 is **dropped** (loading has shown no mesh sensitivity), and the knob that
should govern low-frequency loading is the near-throat flare, i.e. `g_bb_throat_frac` (fixed at 0.15 so far). The
handoff's roll-in hypothesis is tested alongside as the competing explanation.

Jobs (`rolled_bb_h050.yaml` with only the listed knobs changed; `bb_v` 0, epw 6, v11 frozen, same control
`fa5b207bca6d`; configs and CPU predictions written by `predict_b4.py`, `predict_b4.json`; `shape_check --mode verify`
all pass, DOF 3614–3822):

| Job | Change | Predicted H 2037 / 6085 / 6325 / 6977 / 7113 / 8000 (heuristic, vs measured reference) | H wall at u 0.10 (ref) |
|---|---|---|---|
| `rolled_bb_h065_th025` | `bb_h` 0.65, throat 0.25 | 79.5 / 76.3 / 76.2 / 75.5 / 75.1 / 72.6 (ref `h065`) | 11.6° (21.3°) |
| `rolled_bb_h065_th030` | `bb_h` 0.65, throat 0.30 | 80.5 / 77.2 / 77.1 / 76.5 / 76.1 / 73.6 | 9.3° |
| `rolled_bb_h065_ri022` | `bb_h` 0.65, roll-in 0.22 | 79.7 / 76.4 / 76.3 / 75.7 / 75.3 / 72.8 | 22.4° |
| `rolled_bb_h065_ri038` | `bb_h` 0.65, roll-in 0.38 | 75.7 / 72.4 / 72.3 / 71.7 / 71.3 / 68.8 | 20.0° |
| `rolled_bb_h050_th025` | `bb_h` 0.50, throat 0.25 | 81.9 / 70.3 / 69.7 / 68.9 / 68.8 / 67.0 (ref `h050`) | 10.6° (18.0°) |
| `rolled_bb_h080_th030` | `bb_h` 0.80, throat 0.30 (exploratory) | 80.2 / 77.7 / 77.7 / 77.2 / 76.9 / 75.0 (ref `h065`) | 9.7° |

Predictions stated in advance:

- **H1 (throat length governs loading):** Re(z) at 896 Hz rises above 0.864 for both throat variants at `bb_h` 0.65,
  and is higher at throat 0.30 than at 0.25; at least one of them passes rule 5 (min Re z ≥ 0.891).
- **H2 (roll-in governs loading, the handoff's hypothesis):** predicted **null** — both roll-in variants keep Re(z) at
  896 Hz within 0.03 of 0.864 and still fail rule 5.
- HF H within ±3° of the heuristic rows above; a longer throat transition does **not** cost 6–8 kHz H (θc rises to
  compensate).
- `rolled_bb_h050_th025` passes all six rules.
- `rolled_bb_h080_th030`: no loading prediction; reported whatever the outcome.

Pass rule unchanged (six rules against the rolled control). Keeper selection among passing jobs: highest minimum
6–8 kHz H, then the narrowest 2–4 kHz H spread, then loading margin; **not J** (J has no minimum on the dose axis).

## Addendum, written 2026-11-25T15:57Z after the commit `3dd1b815` and before any batch-6 solve

**Lamé, batch 6.** The two earlier Lamé backbone runs (throat 0.15, roll-in 0.30) widened 6–8 kHz H but failed
loading (Re z at 896 Hz 0.597 / 0.487 vs the 0.617 floor) and waistbanded at 2–4 kHz (2678 Hz H 54.2 / 46.8°). The rolled
batch 4 showed the throat transition governs 896 Hz loading. For the Lamé the solved body angle (32.2°) also sits
below the parent's late wall; a shorter roll-in raises it (CPU: 37.0° at roll-in 0.20, 38.5° at 0.15, 39.4° at throat
0.30 / roll-in 0.15). Jobs are `lame_bb_h100_m040.yaml` with only the listed knobs changed; control `lame_morph_040`
(J 9.0845, min Re z 0.717, 2–4 kHz H 60.2–69.5°, which already fails rule 2). Shape check (verify cap) passes, DOF
3613–3647, extents 490 × 281 × 210 mm.

| Job | `bb_h` | throat | roll-in | θc H (CPU) |
|---|---:|---:|---:|---:|
| `lame_bb_h100_m040_t25_r20` | 1.0 | 0.25 | 0.20 | 37.0° |
| `lame_bb_h100_m040_t25_r15` | 1.0 | 0.25 | 0.15 | 38.5° |
| `lame_bb_h075_m040_t25_r20` | 0.75 | 0.25 | 0.20 | 37.0° (blend 0.75) |
| `lame_bb_h100_m040_t30_r15` | 1.0 | 0.30 | 0.15 | 39.4° |

Predictions (stated in advance; the station-map heuristic is not used, it failed near the throat):

- **Loading:** every job lifts Re(z) at 896 Hz above the throat-0.15 runs (0.487 at full strength) and passes rule 5
  (≥ 0.617); throat 0.30 highest.
- **Mid band:** the 2678 Hz H waistband shrinks (≥ +5° vs `lame_bb_h100_m040`'s 46.8°), but rule 2 (65–85° at every
  2–4 kHz bin) is still expected to **fail** for all four, as it does for the control.
- **HF:** H ≥ 62° at all five 6–8 kHz bins for the three full-strength jobs; V at 6–8 kHz not narrower than control.
- Keeper: the job passing the most rules, ties broken by the predeclared ranking. A Lamé pass of all six rules is not
  expected.

## Addendum, written 2026-11-25T16:10Z before any batch-7 solve — transfer test on a second rolled body

**Question:** does the rolled keeper recipe (`bb_h` 0.65, throat 0.25, roll-in 0.30, `bb_v` 0) transfer to a
different rolled design scored on the same brief? Body 2 is `20874108fe25` (`runs/20261123T221455Z-screen-a07561`,
screen J 7.942, `rolled_family_rect_v1`, same parent digest `9bab8261…`): 583.9 × 347.8 mm, depth 202.7 mm, inward
relief H 3.5 / V 0.2 mm, axial −8.6 / +20.0 mm, terminal 279.7°. Its pre-roll walls look like the first anchor's
(H chord 42.3°, wall at 10/20/30/45 % = 8.2/14.2/24.3/37.1°; `survey_rows_families.json`). The neutral control
`rolled2_bb_control.yaml` builds the saved mesh byte-for-byte (screen and verify mesh identical, 9936 triangles).

Jobs (verify, epw 6, v11 frozen): `rolled2_bb_control` (the matched control; the saved run is screen-tier only),
`rolled2_bb_h065_th025` (the recipe), `rolled2_bb_h050_th025` (the weaker passing recipe from batch 4).

Predictions: the control shows the same defect (8 kHz H below 60°); the recipe passes all six rules against its
own control, with 8 kHz H within ±4° of the first body's 68.5° and loading within 0.1 of control; `h050_th025`
also passes. A failure is reported as a failure of transfer, not re-tuned in this batch.
