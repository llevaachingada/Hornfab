# CD wall-angle backbone under the retained return: fixed-candidate verifies

2026-11-25, canonical checkout, v11 objective frozen. Simulated matched verifies (BEAT CUDA, 29-frequency verify
grid, 1024-point balloon DI, freestanding quarter model, 36 mm / 2° assumed source, `mesh.epw` 6 unless stated).
Not physical-driver measurements. Predictions and pass rules were written first:
[PREDECLARED.md](PREDECLARED.md). Construction, sources and literature:
[RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md](../../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md).

Two kinds, one kernel, LABELED HYPOTHESIS (no published geometry):

- `rolled_family_rect_bb_v1` — parent `rolled_family_rect_cd_v1` (anchor `fa5b207bca6d`);
- `klangfilm_lame_hv_bb_v1` — parent `klangfilm_lame_hv_cd` (Lamé `morph_frac` 0.40, i.e. the already-solved
  `lame_morph_040`).

Controls are the neutral adapters; `neutral_parity.py` shows all three build the saved verify meshes
**byte-for-byte** ([neutral_parity.json](neutral_parity.json)), so the existing solves are valid controls.

## What the evidence says

- **Update (batches 6–7, 16:00–16:08Z): the rolled recipe transfers; the Lamé does not converge.** On a second rolled
  body (`20874108fe25`, same brief) `bb_h` 0.65 / throat 0.25 passes all six rules against its own control with 6–8 kHz
  H 77.4 / 76.5 / 73.2 / 72.5 / 68.3° (first body 77.1 / 76.2 / 73.5 / 72.7 / 68.5°), 2–4 kHz H 73.3–79.3° and J
  7.683 → 4.562. On the Lamé, a longer throat transition and shorter roll-in move the 2.7 kHz waistband down to 2.3 kHz
  and lift loading only to 0.554–0.608 (floor 0.617); no Lamé candidate passes. A survey of the other freeform/rows
  families and a reusable wrap tool are in the cross-application section.
- **Update (batches 4–5, 2026-11-25 15:39–15:50Z): the loading edge moves with the throat transition, and the
  keeper becomes `bb_h` 0.65 with throat 0.25.** The 0.65 failure was Re(z) at 896 Hz, which is set by the near-throat
  flare. Lengthening the throat transition 0.15 → 0.25 lifts it 0.864 → 1.085 (min 0.993) while keeping H ≥ 68.5° at
  every 6–8 kHz bin; it passes all six rules and the epw-9 gate (deltas within 0.3°). See the batch-4 section.
- **Two doses pass every predeclared rule: rolled `bb_h` 0.45 and 0.50, with 0.50 the better of the two.** H is
  69.0 / 68.4 / 67.6 / 67.5 / 65.7° at 6085 / 6325 / 6977 / 7113 / 8000 Hz (control 62.5 / 61.6 / 59.0 / 58.4 / 54.8), H stays 72.4–80.6° across
  2–4 kHz, V at 6–8 kHz is not narrower, there is no multilobe bin, min Re(z) from 900 Hz improves 0.991 → 0.997,
  and J falls **8.1209 → 5.4070**. The 2 kHz H that sat on the 90° corridor edge is pulled back to 80.6°.
- **Rolled `bb_h` 1.0 buys more HF H than asked for and fails on the two rules designed to catch it.** H reaches
  90.7 / 89.0 / 84.2 / 83.3 / 77.9° at 6–8 kHz, but the same rotation pushes H to 87.0° at 4037 Hz (rule 2 ceiling
  85°) and min Re(z) drops 0.991 → **0.610** (rule 5 allows −0.1). Ripple/DI terms degrade (raw `rip`
  0.044 → 0.231, `di_roughness` 0.233 → 0.851, on-axis 1–8 kHz residual 0.27 → 1.19 dB).
- **The passing band is rolled `bb_h` 0.45–0.50 and the upper edge is a loading limit, not an H limit.** A post-hoc
  but predeclared dose bracket (0.35 / 0.45 / 0.65, written before those solves) gives H at 8 kHz of
  60.1 / 64.1 / 65.7 / 70.9 / 77.9° for `bb_h` 0.35 / 0.45 / 0.50 / 0.65 / 1.0. `bb_h` 0.35 misses rule 1 (60.1° at
  8000 Hz); 0.45 passes every rule (J 5.743); 0.65 passes the band, V and lobe rules and has the **lowest J of the
  whole batch (4.676)**, but min Re(z) 0.864 fails rule 5 by 0.027 beyond its allowance. J is not a selector: it
  falls to 0.65 and then rises again at 1.0.
- **The Lamé cannot reach 62° H at 8 kHz this way without a waistband.** `bb_h` 0.5 reaches only 60.5° at 8 kHz
  (short of rule 1), narrows V at 6085 (44.7 vs 45.1°, rule 3) and loses loading (0.717 → 0.597, rule 5).
  `bb_h` 1.0 does reach 69.8–75.7° at 6–8 kHz, but H collapses to **46.8–54.9° at 2037–3070 Hz** (rule 2: 65–85°)
  and min Re(z) falls to **0.487** — the waistband and the loading cost the dossier predicted for a conical body
  under a fixed return.
- **The HF mechanism is the body angle and it scales monotonically with the blend.** ΔH at 8 kHz is +10.8°
  (rolled 0.5), +23.1° (rolled 1.0), +9.0° (Lamé 0.5), +18.2° (Lamé 1.0); at 6 kHz the same ordering holds. This
  is the same lever the 2026-11-24 batch identified at 55–110 mm from the throat, now driven from a solved CD
  schedule instead of an additive bump.
- **The gain survives one mesh refinement.** Re-solved at `epw` 9 (6,749 DOF vs 3,632): every predeclared delta
  keeps sign and size within 0.2° (worst: 8000 Hz +10.8 → +10.9°; 6977 Hz +8.6 → +8.4°), the control moves
  ≤ 0.25°, and J 5.4070 → 5.3770. Predeclared mesh rule: **pass**.
- **Nothing is gained in V.** `bb_v` was 0 in every candidate; the V-plane row is bit-identical by construction.
  The observed V changes are indirect (≤ +4.9° at 6977 Hz on rolled 1.0) and low-band V is unchanged and still
  mouth-limited, as before.

## Pass-rule check ([PREDECLARED.md](PREDECLARED.md), applied by `analyze.py`)

| Job | H ≥ 62° at 5 HF bins | H 65–85° at 2–4 kHz | V HF not narrower | No multilobe | min Re(z) ≥ control − 0.1 | J ≤ control | Verdict |
|---|---|---|---|---|---|---|---|
| `rolled_bb_h035` | **no** (60.1 @ 8000) | yes (71.1–83.4) | yes (+0.2…+1.1) | yes | yes (1.000) | yes (6.474) | fail (rule 1) |
| `rolled_bb_h045` | **yes** (min 64.1) | **yes** (71.8–81.5) | **yes** (+0.2…+1.3) | yes | **yes** (0.998) | **yes** (5.743) | **PASS** |
| `rolled_bb_h050` | **yes** (min 65.7) | **yes** (72.4–80.6) | **yes** (+0.3…+1.6) | yes | **yes** (0.997 vs 0.991) | **yes** (5.407) | **PASS** |
| `rolled_bb_h065` | yes (min 70.9) | yes (72.7–78.3) | yes (+0.1…+2.2) | yes | **no** (0.864) | yes (4.676) | fail (rule 5) |
| `rolled_bb_h100` | yes (min 77.9) | **no** (max 87.0 @ 4037) | yes (+1.3…+4.9) | yes | **no** (0.610) | yes (5.559) | fail (rules 2, 5) |
| `lame_bb_h050_m040` | **no** (60.5 @ 8000) | **no** (54.2–61.2) | **no** (−0.44 @ 6085) | yes | **no** (0.597) | yes (7.857) | fail (rules 1, 2, 3, 5) |
| `lame_bb_h100_m040` | yes (min 69.8) | **no** (46.8–61.2) | yes (+0.1…+5.7) | yes | **no** (0.487) | yes (7.994) | fail (rules 2, 5) |
| `rolled_bb_h050_epw9` | yes (min 66.0) | yes (72.5–80.6) | yes (+0.4…+1.6) | yes | yes (0.997) | yes (5.377) | refined-mesh **PASS** |

## Rolled hybrid `fa5b207bca6d`

Control: [rolled_bb_control.yaml](../../../examples/typologies/cd_backbone_2026-11-25/rolled_bb_control.yaml)
(`bb_h` = `bb_v` = 0, byte-identical to the anchor verify). Throat fraction 0.15, roll-in 0.30 in every candidate.

| Candidate | J | H 2037 | H 3070 | H 4037 | H 6085 / 6325 / 6977 / 7113 / 8000 | V 8000 | Diag 8000 | DI 8k | min Re z | on-axis 1–8k std |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| control | 8.121 | 90.1 | 76.2 | 70.4 | 62.5 / 61.6 / 59.0 / 58.4 / 54.8 | 47.7 | 47.8 | 14.54 | 0.991 | 0.27 dB |
| `bb_h` 0.35 | 6.474 | 83.4 | 73.6 | 71.1 | 65.2 / 64.4 / 62.6 / 62.2 / 60.1 | 48.4 | 51.3 | 14.13 | 1.000 | 0.21 dB |
| `bb_h` 0.45 | 5.743 | 81.5 | 73.2 | 71.8 | 67.4 / 66.9 / 65.6 / 65.4 / 64.1 | 48.8 | 54.6 | 13.77 | 0.998 | 0.27 dB |
| `bb_h` 0.5 | **5.407** | 80.6 | 72.9 | 72.6 | **69.0 / 68.4 / 67.6 / 67.5 / 65.7** | 48.9 | 56.1 | 13.63 | 0.997 | 0.32 dB |
| `bb_h` 0.65 | 4.676 | 77.8 | 72.7 | 75.0 | 74.6 / 74.5 / 73.8 / 73.4 / 70.9 | 49.8 | 62.0 | 13.01 | **0.864** | 0.51 dB |
| `bb_h` 1.0 | 5.559 | 70.6 | 74.1 | **87.0** | 90.7 / 89.0 / 84.2 / 83.3 / 77.9 | 51.8 | 69.9 | 12.28 | **0.610** | 1.19 dB |

Raw v11 terms (not weighted contributions): `dislope` 5.84 → 3.49 / 0.25; `diag` 6.75 → 3.94 / 2.76;
`offaxis_smooth` 1.43 → 0.78 / 1.37; `rip` 0.044 → 0.062 / 0.231; `di_roughness` 0.23 → 0.34 / 0.85;
`flat` 0.187 → 0.223 / 0.837. Loading penalty zero everywhere. No H/V multilobe bins anywhere.

Delta table (candidate − control, `epw` 6; 2037 / 3070 / 4037 / 6085 / 6977 / 8000): `bb_h` 0.5 is
−9.5 / −3.2 / +2.2 / +6.4 / +8.6 / +10.8°; `bb_h` 1.0 is −19.5 / −2.1 / +16.7 / +28.2 / +25.2 / +23.1°.
The correlate is not monotone in 3520–4037 Hz, which is where 1.0 overshoots the 85° ceiling.

Full-bin values and isobars: [results.json](results.json), [rolled_curves.png](rolled_curves.png),
[rolled_isobars.png](rolled_isobars.png).

### Dose bracket (post-hoc extension, predeclared before its three solves)

Prediction was linear in `g_bb_h` between the measured 0.5 and 1.0 doses. It held for H and V and failed for J,
which is not monotone on this axis.

| Job | Predicted / measured H 8000 | Predicted / measured 2–4 kHz band | Predicted / measured V 8000 | Predicted / measured J | min Re(z) | Verdict |
|---|---|---|---|---|---|---|
| `bb_h` 0.35 | 62.0 / **60.1** | 68.2–83.6 / 71.1–83.4 | 48.1 / 48.4 | 5.36 / 6.474 | 1.000 | rule 1 fails (60.1 < 62) |
| `bb_h` 0.45 | 64.4 / 64.1 | 71.1–81.6 / 71.8–81.5 | 48.7 / 48.8 | 5.39 / 5.743 | 0.998 | pass |
| `bb_h` 0.65 | 69.3 / 70.9 | 73.3–78.6 / 72.7–78.3 | 49.8 / 49.8 | 5.45 / 4.676 | 0.864 | rule 5 fails (0.127 > 0.1) |

The predeclared boundary criterion (largest `bb_h` satisfying all six rules) puts the passing interval at
**0.45–0.50**; 0.65 fails only on loading, not on coverage. At 0.65 the H corridor still has headroom
(70.9–74.6° at 6–8 kHz) while the throat loading cost has crossed the allowed 0.1. Raw `dislope` falls
5.84 → 4.46 (0.35) → 3.84 (0.45) → 3.49 (0.50) → 2.31 (0.65) → 0.25 (1.0), which is why J keeps falling while the
loading gets worse: **J has no minimum on this axis and must not be used alone to pick a dose.**

### Batch 4–5: throat transition vs roll-in at the loading edge (predeclared addendum 2026-11-25T15:39Z)

`bb_h` 0.65 failed only rule 5, and its minimum Re(z) sits at **896 Hz**. Re(z) there fell with dose (control 1.63;
0.35 / 0.45 / 0.50 / 0.65 / 1.0: 1.17 / 1.06 / 1.01 / 0.86 / 0.61) and was identical at epw 6 and 9, so the handoff's
epw-9 re-check of 0.65 was dropped and the near-throat flare (`g_bb_throat_frac`, 0.15 until now) was tested against
the handoff's roll-in hypothesis. All jobs are `rolled_bb_h050.yaml` with only the named knobs changed; same control.

| Job | Change | J | Re z 896 / min | H 2037 / 3070 / 4037 | H 6085 / 6325 / 6977 / 7113 / 8000 | V 8k | Rules |
|---|---|---:|---|---|---|---:|---|
| `h065` (b3) | 0.65, throat 0.15 | 4.676 | 0.864 / 0.864 | 77.8 / 72.7 / 75.0 | 74.6 / 74.5 / 73.8 / 73.4 / 70.9 | 49.8 | fails 5 |
| `h065_th025` | throat 0.25 | 4.679 | 1.085 / 0.993 | 81.7 / 76.5 / 79.9 | 77.1 / 76.2 / 73.5 / 72.7 / 68.5 | 49.0 | **all pass** |
| `h065_th030` | throat 0.30 | 5.006 | 1.227 / 0.983 | 83.9 / 78.8 / 82.0 | 76.3 / 75.2 / 72.0 / 71.3 / 66.9 | 48.6 | all pass |
| `h065_ri022` | roll-in 0.22 | 4.349 | 0.835 / 0.835 | 81.4 / 76.8 / 78.4 | 76.3 / 76.3 / 75.3 / 74.9 / 72.1 | 49.5 | fails 5 |
| `h065_ri038` | roll-in 0.38 | 5.233 | 0.899 / 0.899 | 73.6 / 70.4 / 70.0 | 72.0 / 71.8 / 71.8 / 71.6 / 69.5 | 48.9 | fails 3 (ΔV −0.75°) |
| `h050_th025` | 0.50, throat 0.25 | 5.272 | 1.212 / 0.995 | 83.5 / 75.7 / 76.1 | 73.1 / 72.3 / 69.8 / 69.3 / 65.4 | 48.2 | all pass |
| `h080_th030` | 0.80, throat 0.30 | 4.875 | 1.122 / 0.977 | 83.2 / 80.7 / 87.2 | 79.4 / 78.1 / 74.4 / 73.7 / 69.0 | 49.1 | fails 2 (87.2° at 4037) |

Against the predictions written first:

- **H1 held.** Both throat variants lift Re(z) at 896 Hz above 0.864, throat 0.30 more than 0.25 (1.227 vs 1.085), and
  both pass rule 5.
- **H2 (roll-in, the handoff's hypothesis) held for 0.22 and narrowly missed for 0.38:** 0.22 moved Re(z) by −0.029
  and still fails; 0.38 moved it by +0.035 (outside the predicted ±0.03) and clears rule 5 by 0.008, but fails rule 3.
- **The HF prediction was wrong at the top octave.** A longer throat transition does cost 8 kHz H: 70.9 → 68.5
  (0.25) → 66.9° (0.30), up to 6.7° below the heuristic; it widens 6 kHz slightly. The station-map heuristic should not
  be trusted for throat-region changes.
- `h050_th025` passes all six rules, as predicted; `h080_th030` fails the 2–4 kHz ceiling.

**Keeper by the predeclared ranking (highest minimum 6–8 kHz H, then 2–4 kHz spread, then loading; not J):
`rolled_bb_h065_th025`** — H ≥ 68.5° at every 6–8 kHz bin, 2–4 kHz H 76.5–82.3°, V not narrower, min Re(z) 0.993,
J 4.679. Refined-mesh gate (`rolled_bb_h065_th025_epw9`, 6787 DOF): every predeclared delta keeps sign and size within
0.3° (8 kHz +13.6 → +13.3°), all six rules still hold (min Re z 0.992), J 4.663. A shallow Re(z) dip to ~0.98 around
2–3 kHz appears with the longer throat transitions; it stays above the floor. Figure:
[rolled_b4_curves.png](rolled_b4_curves.png).

### Batch 6: Lamé with a longer throat transition and a shorter roll-in (predeclared 15:57Z)

| Job (`bb_h`, throat, roll-in) | θc H | J | Re z 896 (min) | H 2037 / 2335 / 2678 / 3070 / 3520 / 4037 | H 6085 / … / 8000 | V 8k |
|---|---:|---:|---|---|---|---:|
| control `lame_morph_040` | — | 9.084 | 0.717 | 69.5 / 64.2 / 61.5 / 60.7 / 60.2 / 60.4 | 58.0 / 57.2 / 54.8 / 54.3 / 51.6 | 37.8 |
| 1.0, 0.15, 0.30 (b1) | 32.2° | 7.994 | 0.487 | 54.9 / 50.9 / 46.8 / 54.8 / 60.6 / 61.2 | 73.6 / 74.3 / 75.7 / 75.5 / 69.8 | 43.5 |
| 1.0, 0.25, 0.20 | 37.0° | 7.484 | 0.559 | 57.1 / 51.3 / 64.8 / 67.0 / 69.0 / 77.5 | 80.2 / 77.9 / 71.2 / 69.9 / 63.1 | 38.8 |
| 1.0, 0.25, 0.15 | 38.5° | 8.026 | 0.554 | 56.6 / 53.6 / 69.7 / 69.1 / 72.0 / 84.6 | 79.2 / 76.2 / 69.7 / 68.6 / 63.6 | 37.9 |
| 0.75, 0.25, 0.20 | 37.0° | **6.851** | 0.605 | 59.5 / 54.6 / 60.6 / 64.9 / 66.8 / 70.4 | 74.2 / 73.1 / 68.7 / 67.8 / 61.8 | 38.9 |
| 1.0, 0.30, 0.15 | 39.4° | 8.039 | 0.608 | 59.0 / 56.9 / 71.1 / 70.3 / 74.6 / 85.8 | 76.9 / 74.1 / 67.9 / 66.8 / 61.7 | 37.8 |

Against the predictions: loading rose above the throat-0.15 runs and was highest at throat 0.30, **but none reached
the 0.617 floor** (prediction failed). The 2678 Hz waistband shrank as predicted (≥ +13.8°), but the dip moved to
2335 Hz (51–57°) and 4037 Hz now overshoots (up to 85.8°); rule 2 fails everywhere, as predicted (it fails on the
control too). HF ≥ 62° held for two of three full-strength jobs. **Conclusion:** on this 208 mm-deep Lamé the backbone
trades a 2–2.5 kHz waistband and low-end loading for HF width; body tuning does not resolve it. The next Lamé step is a
different construction (mouth/rollback or depth), not more backbone knobs.

### Batch 7: does the rolled recipe transfer to a second rolled body? (predeclared 16:10Z)

Body 2 = `20874108fe25` (`runs/20261123T221455Z-screen-a07561`, screen J 7.942, 583.9 × 347.8 mm, depth 202.7 mm,
different relief and terminal turn from the first anchor). Neutral control builds the saved mesh byte-for-byte.
Readout: `analyze_transfer.py` → `results_transfer.json` (the same six rules, against body 2's own verify control).

| Job | J | Re z 896 (min) | H 2–4 kHz (6 bins) | H 6085 / 6325 / 6977 / 7113 / 8000 | V 8k | Rules |
|---|---:|---|---|---|---:|---|
| `rolled2_bb_control` | 7.683 | 1.681 (0.992) | 85.9 / 83.3 / 78.9 / 73.9 / 71.6 / 69.9 | 62.7 / 61.7 / 58.7 / 58.1 / 54.5 | 47.2 | control |
| `rolled2_bb_h065_th025` | **4.562** | 1.155 (1.000) | 77.0 / 76.4 / 75.4 / 73.3 / 75.6 / 79.3 | **77.4 / 76.5 / 73.2 / 72.5 / 68.3** | 48.2 | **all pass** |
| `rolled2_bb_h050_th025` | 5.008 | 1.285 (1.002) | 78.9 / 77.7 / 75.6 / 72.8 / 73.6 / 75.7 | 72.9 / 72.2 / 69.7 / 69.1 / 65.4 | 47.7 | all pass |

Design cards (views plus full-width H/V dispersion maps): [first-body keeper](renders/card_body1_keeper.png), [body 2 control](renders/card_body2_control.png), [body 2 keeper](renders/card_body2_keeper.png).

Both predictions held: body 2 shows the same 6–8 kHz defect, and the recipe lands within 0.3° of the first body at every
6–8 kHz bin. The backbone sets the high-frequency width largely independent of the parent's relief, terminal turn
and small size differences.

## Cross-application to other freeform/rows horns

`survey_rows_families.py` → `survey_rows_families.json` scans every saved run with a rows recipe, keeps the best J per
(rows type, brief, mode), rebuilds the best design per type and reports the H/V straight-chord angle to the roll-on
station, the wall angle at 10/20/30/45 % of the pre-roll arc, and the gap (chord − wall at 30 %), which predicted the
backbone's effect here.

| Family | Best saved (brief) | Return | H gap / V gap | Verdict |
|---|---|---|---|---|
| `rolled_family_rect_v1` and its CD/terminal variants | J 7.942 (v11cd 900) | yes | 18.0 / 14.8° | **applies; transfer confirmed (batch 7)**. Use `tools/geometry/apply_cd_backbone.py` on any saved rolled design. |
| `klangfilm_lame_hv_cd` / `_v1` | J 7.4–8.4 (v7 smooth) | yes | 10.8–11.4 / 16.4–17.9° | applies geometrically; acoustically limited (batch 6) |
| `sculpted_rosse_meridians_v1` | J 2.071 (v11cd_sc) | yes | 5.8 / 5.7° | lever already present (conical R-OSSE body); not worth a backbone |
| `osse_rollback` | J 1.113 (b3a PA 90×90) | yes | 8.6 / 8.7° (walls 40–50°) | body angle is already a native knob (`g_a_h_deg`, `g_a_v_deg`) |
| `lecleach`, `lecleach_ar`, `lecleach_asym`, `iwata_ar` | J 0.67–8.1 (loading / DI-slope briefs) | yes | 15–17° | **do not apply**: intentionally non-CD loading families scored on loading-first or DI-slope briefs (knowledge card rule) |
| `salmon_elliptical` | J 4.022 (b3bt class B loading) | yes | 16.7 / 19.2° | **do not apply** under its brief ("narrowing can be the design"); would need a CD brief and a new identity |
| `klangfilm_lame_hv_core` | J 2.001 (v7 smooth) | no | — | no returned lip; outside the construction |
| legacy kinds (`rolled_rect`, `crowe_panel`, `section_pucker`, `rosse_rect`, `rolled_family_section_v1`, …) | — | — | — | saved recipes no longer rebuild under the current adapters (schema/digest), not assessed |

**Reusable tool.** `tools/geometry/apply_cd_backbone.py --run <run> --design <hash> --out <dir> --prefix <name>
[--recipe bb_h,bb_v,throat,rollin ...]` writes the neutral control and recipe configs from a saved
`rolled_family_rect_v1`, `rolled_family_rect_cd_v1` or `klangfilm_lame_hv_cd` design (the run's exact effective
config) and checks that the neutral control builds the saved mesh byte-for-byte. It reproduced the batch-7 configs
exactly and passed parity on both rolled bodies. Default recipe 0.65 / 0 / 0.25 / 0.30.

## Klangfilm–Lamé `morph_frac` 0.40

Control: [lame_bb_control_m040.yaml](../../../examples/typologies/cd_backbone_2026-11-25/lame_bb_control_m040.yaml)
(neutral adapter on the solved `lame_morph_040`, byte-identical).

| Candidate | J | H 2037 | H 2335 | H 2678 | H 3070 | H 4037 | H 6085 / 6325 / 6977 / 7113 / 8000 | V 8000 | Diag 8000 | DI 8k | min Re z |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| control | 9.0845 | 69.5 | 64.2 | 61.5 | 60.7 | 60.4 | 58.0 / 57.2 / 54.8 / 54.3 / 51.6 | 37.8 | 43.6 | 15.41 | 0.717 |
| `bb_h` 0.5 | 7.857 | 61.2 | 57.0 | **54.2** | 57.0 | 60.5 | 62.5 / 62.6 / 62.5 / 62.5 / 60.5 | 39.9 | 50.0 | 14.32 | **0.597** |
| `bb_h` 1.0 | 7.994 | **54.9** | **50.9** | **46.8** | **54.8** | 61.2 | 73.6 / 74.3 / 75.7 / 75.5 / 69.8 | 43.5 | 56.1 | 12.98 | **0.487** |

Raw terms: `dislope` 6.84 → 4.55 / 1.76; `diag` 7.23 → 5.63 / 4.45; `offaxis_smooth` 1.78 → 1.46 / 1.62;
`rip` 0.044 → 0.125 / 0.300; `di_roughness` 0.21 → 0.52 / 1.05; `flat` 0.228 → 0.517 / 0.946. No multilobe bins;
loading penalty zero; on-axis 1–8 kHz residual 0.33 → 0.74 / 1.35 dB.

So on the Lamé the backbone does what it was built to do at 6–8 kHz and still misses the brief: the body angle
that gives 70–76° H at 8 kHz costs the 2.4–3.5 kHz band and the throat loading. That is the waistband Keele and
Kolbrek warn about when body angle and mouth size disagree, and it is why the Lamé needs either a different
mouth/roll-on budget or a lever that adds mid-band angle at the same time.

## Refined-mesh gate (predeclared)

Same config with `mesh.epw` 6 → 9 only. Control: `rolled_anchor_epw9` (J 8.0821). Entries are candidate − control
at `epw` 6 / at `epw` 9.

| Pair | J epw 6 / 9 | ΔH 2037 | ΔH 3070 | ΔH 4037 | ΔH 6085 | ΔH 6977 | ΔH 8000 | ΔV 8000 | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| control moves (epw 9 − 6) | 8.1209 / 8.0821 | −0.05 | −0.07 | +0.01 | +0.05 | +0.12 | +0.25 | −0.01 | control |
| `rolled_bb_h050` | 5.4070 / 5.3770 | −9.5 / −9.5 | −3.2 / −3.1 | +2.2 / +2.1 | +6.4 / +6.5 | +8.6 / +8.4 | +10.8 / +10.9 | +1.3 / +1.6 | **pass** |

This is one refinement step of the element size on the same generated surface grid (rolled 65 × 129 stations),
not a convergence study, and the same BEAT backend. Lamé has no passing candidate, so no Lamé refined solve was
run; its `epw`-9 control already exists (`lame_morph_040_epw9`, J 9.0593) if one is wanted later.

## Built geometry (CPU, before the solves)

`tests/test_cd_backbone_geometry.py` with the parent suites: 32 tests pass, junitxml
`runs/cd_backbone_tests_recheck.xml` (`tests="32" errors="0" failures="0" skipped="0" time="15.688"`).

- Throat, roll-on station, return and rim stay within **1e-13 mm**; the V-plane row is untouched when `bb_v` = 0;
  inner extents exact. `bb_h` = `bb_v` = 0 returns the parent object unchanged.
- Shell re-offset changes rolled overall depth by 0.0017 mm (test bound 0.01 mm).
- Interior displacement: **15.5 / 31.0 mm** (rolled, `bb_h` 0.5 / 1.0) and **8.2 / 16.4 mm** (Lamé on m0.40).
- Solved body angle θc: **36.51° H** (rolled) and **32.22° H** (Lamé m0.40) at throat 0.15 / roll-in 0.30.
- `tools/shape_check.py --mode verify` on the four candidates: DOF 3579 / 3620 (Lamé) and 3632 / 4409 (rolled),
  cap 24000; envelope fits (production policy); driver coupling round and matching the 36 mm exit; extents
  581 × 366 × 217 mm (rolled) and 490 × 281 × 210 mm (Lamé). The three dose candidates also pass
  (DOF 3545 / 3650 / 3803, same extents).

## Figures

- [rolled_curves.png](rolled_curves.png), [lame_curves.png](lame_curves.png): H, V, diagonal −6 dB widths and DI;
  control in grey, corridor band shaded, 6–8 kHz tinted.
- [rolled_isobars.png](rolled_isobars.png), [lame_isobars.png](lame_isobars.png): H and V isobars, red = −6 dB.
- [profiles_same_scale.png](profiles_same_scale.png): H/V sections, mouth rim and wall angle vs arc fraction.
- [renders/views_same_scale.png](renders/views_same_scale.png): meshed 3D views (front, front 3/4, behind, side)
  at one scale for controls and candidates.
- `renders/card_*/`: the owner's design card (two views, full-width H and V dispersion maps, J, loading line) for
  `rolled_h050`, `rolled_h100`, `lame_control`, `lame_h050`, `lame_h100`. The rolled control card is the same
  design and mesh as [card_rolled_anchor.png](../directivity_attribution_2026-11-24/renders/card_rolled_anchor.png)
  and is not duplicated here.

## Jobs actually run

Batches 1-3: four fixed candidates, one refined mesh, three dose-bracket doses. One solve at a time, `HORNLAB_GPU_LOCK=refuse`, with
the runner's `gpu-clean --lane gpu` before and after each job; VRAM returned to its pre-job level every time. The
baseline includes the desktop and the open GUI (~1.7 GiB).

Verbatim from `runs/nights/cd_backbone_2026-11-25/rolled_bb_h050.log` (the blank lines are in the file):

```
=== pre-hygiene rolled_bb_h050 lane=gpu 2026-11-25T00:57:42Z
gpu-clean --lane gpu rc=0
gpu-clean: no project Julia/BEAT processes found
gpu-clean: VRAM used 1789 MiB

gpu lock clear; VRAM baseline=1789 MiB

=== job rolled_bb_h050 start 2026-11-25T00:57:43Z timeout=1200s
=== argv: .venv\Scripts\hornlab-search.exe run --config examples/typologies/cd_backbone_2026-11-25/rolled_bb_h050.yaml --mode verify --cache-dir runs/cd_backbone_2026-11-25/cache_rolled_bb_h050 --dataset-dir runs/cd_backbone_2026-11-25/dataset
=== HORNLAB_BEAT_WORKER_DIR: C:\Users\hunte\Hrns\hornlab-search\runs\lanes\gpu\workers

  terms (raw): cov=0  rip=0.06237  di=0  dislope=3.485  flat=0.2228  load=0  penalty=0  total J=5.40698  n_nan=0  DI source=balloon
run OK: seed J=5.40698, 3632 dofs, solve 33.8 s; output C:\Users\hunte\Hrns\hornlab-search\runs\20261125T005748Z-verify-576beb
=== job rolled_bb_h050 end 2026-11-25T00:58:52Z exit=0
=== post-hygiene rolled_bb_h050 lane=gpu 2026-11-25T00:58:52Z
gpu-clean --lane gpu rc=0
gpu-clean: killed 2 process(es): [44708, 41668]
gpu-clean: VRAM used 1771 MiB

VRAM peak=2094 MiB after=1771 MiB
```

| Batch | Job | Run dir | DOF | Solve s | Job wall s | VRAM baseline → peak MiB |
|---|---|---|---:|---:|---:|---|
| 1 | `rolled_bb_h050` | `runs/20261125T005748Z-verify-576beb` | 3632 | 33.8 | 70.0 | 1789 → 2094 |
| 1 | `rolled_bb_h100` | `runs/20261125T005859Z-verify-a8c159` | 4409 | 42.1 | 82.2 | 1771 → 2024 |
| 1 | `lame_bb_h050_m040` | `runs/20261125T010025Z-verify-9884a8` | 3579 | 26.1 | 52.6 | 1693 → 2074 |
| 1 | `lame_bb_h100_m040` | `runs/20261125T010117Z-verify-31638b` | 3620 | 27.5 | 53.1 | 1769 → 2054 |
| 2 | `rolled_bb_h050_epw9` | `runs/20261125T010331Z-verify-972a9e` | 6749 | 72.9 | 101.5 | 1688 → 2231 |
| 3 | `rolled_bb_h035` | `runs/20261125T130851Z-verify-38c04e` | 3545 | 28.5 | 84.8 | 1656 → 1899 |
| 3 | `rolled_bb_h045` | `runs/20261125T131005Z-verify-1cac90` | 3650 | 29.2 | 64.6 | 1657 → 1943 |
| 3 | `rolled_bb_h065` | `runs/20261125T131111Z-verify-1f727a` | 3803 | 31.1 | 66.9 | 1656 → 1935 |

Eight solves, 575.6 s of recorded job wall time (batch 1 257.9 s, batch 2 101.5 s, batch 3 216.2 s). These are single observations
on this machine, not guaranteed costs.


Batches 4–7 (2026-11-25 15:39–16:08Z, same hygiene; pre-job baseline 1527–1558 MiB, about 0.25 GiB below batches 1–3):

| Batch | Job | Run dir | DOF | Wall s | VRAM baseline → peak MiB |
|---|---|---|---:|---:|---|
| b4 | `rolled_bb_h065_th025` | `runs/20261125T153942Z-verify-eff909` | 3652 | 65.3 | 1558 → 1839 |
| b4 | `rolled_bb_h065_th030` | `runs/20261125T154048Z-verify-727459` | 3614 | 57.5 | 1534 → 1815 |
| b4 | `rolled_bb_h065_ri022` | `runs/20261125T154149Z-verify-d92d5e` | 3696 | 62.4 | 1534 → 1814 |
| b4 | `rolled_bb_h065_ri038` | `runs/20261125T154255Z-verify-07c9c4` | 3822 | 64.1 | 1531 → 1814 |
| b4 | `rolled_bb_h050_th025` | `runs/20261125T154402Z-verify-94038c` | 3658 | 106.1 | 1531 → 1814 |
| b4 | `rolled_bb_h080_th030` | `runs/20261125T154554Z-verify-4a2a3b` | 3778 | 65.7 | 1527 → 1796 |
| b5 | `rolled_bb_h065_th025_epw9` | `runs/20261125T154757Z-verify-9417e2` | 6787 | 105.8 | 1530 → 2073 |
| b6 | `lame_bb_h100_m040_t25_r20` | `runs/20261125T155653Z-verify-7dd572` | 3647 | 59.5 | 1535 → 1814 |
| b6 | `lame_bb_h100_m040_t25_r15` | `runs/20261125T155755Z-verify-817e63` | 3634 | 60.8 | 1533 → 1811 |
| b6 | `lame_bb_h075_m040_t25_r20` | `runs/20261125T155858Z-verify-cf126b` | 3613 | 56.3 | 1529 → 1811 |
| b6 | `lame_bb_h100_m040_t30_r15` | `runs/20261125T155957Z-verify-8dfb40` | 3616 | 57.9 | 1529 → 1811 |
| b7 | `rolled2_bb_control` | `runs/20261125T160413Z-verify-222688` | 5106 | 76.0 | 1531 → 1908 |
| b7 | `rolled2_bb_h065_th025` | `runs/20261125T160532Z-verify-48f889` | 5497 | 87.3 | 1532 → 1939 |
| b7 | `rolled2_bb_h050_th025` | `runs/20261125T160703Z-verify-62068f` | 5448 | 82.3 | 1529 → 1939 |

## Reproduce

```powershell
.venv\Scripts\python.exe tools/shape_check.py --mode verify `
    examples/typologies/cd_backbone_2026-11-25/rolled_bb_h050.yaml `
    examples/typologies/cd_backbone_2026-11-25/rolled_bb_h100.yaml `
    examples/typologies/cd_backbone_2026-11-25/lame_bb_h050_m040.yaml `
    examples/typologies/cd_backbone_2026-11-25/lame_bb_h100_m040.yaml
.venv\Scripts\python.exe docs/evidence/cd_backbone_2026-11-25/neutral_parity.py
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/cd_backbone_2026-11-25.yaml
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/cd_backbone_b2_2026-11-25.yaml
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/cd_backbone_b3_2026-11-25.yaml
.venv\Scripts\python.exe docs/evidence/cd_backbone_2026-11-25/analyze.py
```

The queue commands solve on the GPU; check the lock with `tools/night_status.py` first. `analyze.py` reads the
nights' `summary.jsonl`, so a re-run produces new run IDs.

## Not done in this pass

- **The conditional search.** The dose bracket puts the passing interval at rolled `bb_h` 0.45–0.50 and shows the
  upper edge is throat loading (0.65 fails only rule 5) while J keeps falling to 0.65. The next search step is a small
  CMA over (`bb_h` 0.35–0.70, `bb_v` ≤ 0.5, throat fraction 0.10–0.25, roll-in 0.25–0.40) seeded at 0.50, with
  sigma and bounds set through `tools/search_preflight.py`; its winners must be scored against the six pass rules,
  not J, because J has no minimum on this axis. Not run here.
- **The V lever.** V is limited by where each mouth starts to roll (backbone V body ≈ 19.5° rolled, 15.5° Lamé at
  these roll-on stations). Moving the V roll-on station outward or tightening the roll changes the visible look and
  is an owner decision; low-band V (≤ 4 kHz) stays mouth-limited regardless.
- **Spatial convergence beyond one refinement step, and the independent bempp cross-check.** Both remain open, as
  in the 2026-11-24 batch.
- **The two-inch CP-850Nd source.** Blocked on the outlet drawing; the 7° on the product page has no stated
  convention and no exit section, and in this model a source cap alone does not steer directivity.
