# Mesh preflight — compact-horn / woofer-crossover slate, 2026-11-19

CPU only. `tools/shape_check.py` in `--mode screen`; no `--save-mesh` was used, nothing was written
under `runs/`. Help was inspected first:

```
usage: shape_check.py [-h] [--brief BRIEF] [--mode {screen,verify,final}]
                      [--save-mesh SAVE_MESH] [--geometry-only]
                      configs [configs ...]
```

## 1. Exact command

```powershell
.venv\Scripts\python.exe tools\shape_check.py --mode screen `
  examples/typologies/scout40w2_2026-11-19/scout40w3__petal_hvlaw_v7.yaml `
  examples/typologies/scout40w2_2026-11-19/scout40w3__tritonia_v9.yaml `
  examples/typologies/scout40w2_2026-11-19/scout40w3__tritonia_v8.yaml `
  examples/typologies/ath_twinray_380.yaml `
  examples/typologies/rolled_family_2026-11-15/rf__rect_radial_wide_v7.yaml `
  examples/typologies/scout40_2026-11-19/scout40__crowe_v2a_c1.yaml `
  examples/typologies/scout40w2_2026-11-19/scout40w3__crowe_x_square_v7.yaml `
  examples/typologies/scout40w_2026-11-19/scout40w2__klangfilm_b3_soft.yaml `
  examples/typologies/fable_v2_2026-11-19/hl__klangfilm_lame_c200_vbeak_v10_v1.yaml `
  examples/typologies/fable_v2_2026-11-19/hl__rolled_rect_record_vbeak_v10_v1.yaml
```

## 2. Pasted result (unedited stdout)

```
| config | ok | dofs / cap | mouth W x H mm | depth mm | envelope | driver coupling | note |
|---|---|---|---|---|---|---|---|


| ath_twinray_380 | yes | 1987 / 5000 | 380 x 303 | 197 | fits | round, matches the exit |  |


| hl__klangfilm_lame_c200_vbeak_v10_v1 | yes | 4835 / 24000 | 585 x 255 | 196 | fits | round, matches the exit |  |


| hl__rolled_rect_record_vbeak_v10_v1 | yes | 4952 / 6000 | 542 x 299 | 236 | fits | round, matches the exit |  |


| rf__rect_radial_wide_v7 | yes | 5096 / 6000 | 541 x 299 | 241 | fits | round, matches the exit |  |


| scout40__crowe_v2a_c1 | yes | 4311 / 24000 | 580 x 474 | 303 | fits | round, matches the exit |  |


| scout40w3__crowe_x_square_v7 | yes | 4170 / 24000 | 479 x 479 | 224 | fits | round, matches the exit |  |


| scout40w3__petal_hvlaw_v7 | yes | 3085 / 24000 | 545 x 360 | 353 | fits | round, matches the exit |  |


| scout40w3__tritonia_v8 | yes | 5408 / 24000 | 586 x 474 | 297 | fits | round, matches the exit |  |


| scout40w3__tritonia_v9 | yes | 5408 / 24000 | 586 x 474 | 297 | fits | round, matches the exit |  |


| scout40w2__klangfilm_b3_soft | yes | 3102 / 24000 | 473 x 266 | 344 | fits | round, matches the exit |  |
```

## 3. What each column proves — and what it does not

- **`ok = yes`** means the mesher built the config's **seed** and the post-mesh bbox passed the
  `mesh/build._check_bbox` guard (0.1–1 m).
- **`dofs / cap`** is the screen-mode cap. Every row has large headroom: the tightest is
  `rf__rect_radial_wide_v7` at 5096/6000 (85 %), then `hl__rolled_rect_record_vbeak_v10_v1` at
  4952/6000 (83 %). The OSSE rows sit at 11–23 % of 24000.
- **`envelope = fits`** means the built bbox is inside the brief's `max_mouth_w/h/depth`.
- **`driver coupling = round, matches the exit`** means the mesher's source cap resolved round and
  the throat patch matches the brief's exit radius. It says nothing about a real compression driver:
  the screen source is an ideal normal-velocity cap, not an HF1440 phase plug.
- **This is the SEED, not the best design.** It does not measure the promoted geometry. The accurate
  per-row measured geometry is in `candidate_register.json` (saved best mesh row + inner-aperture
  rebuild). The gap is large on three rows:

| ID | `shape_check` seed W×H×D | saved best measured outer W×H×D | note |
|---|---|---|---|
| A1 | 545 × 360 × 353 | 567.9 × 379.3 × 322.3 | seed is 23 mm narrower and 31 mm deeper |
| C1 | 580 × 474 × 303 | 580.0 × 301.1 × 328.2 | seed is 173 mm taller (search moved height to 300.5) |
| K1 | 473 × 266 × 344 | 486.9 × 287.2 × 285.4 | seed is near the v10 best, not the v7 best |
| C2 | 479 × 479 × 224 | 461.4 × 460.5 × 231.4 | seed is 18 mm wider |

Using the seed row as the candidate geometry would therefore be wrong on A1, C1 and C2 — which is
exactly why the register takes the saved best.

## 4. Rows the preflight and the register could **not** resolve

These are serialized as unresolved rather than filled by inference.

1. **A4 `ath_twinray_380.yaml` — no candidate-grade J.** `shape_check` proves the reconstruction
   builds (1987/5000, 380 × 303 × 197, fits). There is no v7/v10 run for this `config_sha`
   (`1673ccbc240c`); the only runs are v3/v4 campaign copies. `best_saved.J = NOT_YET_AVAILABLE`.
2. **A4's quoted 1.7726 belongs to a different config.** Run `20261117T001240Z-screen-7b664f`,
   design `85c59331e4a3`, J_v10 1.7726 lives under
   `hl__ath_twinray380_landscape_v8.yaml` (`3b51e02f2bd8`, shape L 311.6 mm / mouth 535 × 440).
   It is recorded as `derived_lane_context`, never as A4's J.
3. **A5 `rf__rect_radial_wide_v7` — saved recipe does not replay.** `shape_check` builds the current
   seed (5096/6000, 541 × 299 × 241, fits), but calling `rows_grid_points` on the saved best grid
   raises `GeneratorError: rolled-family schema or implementation differs from saved recipe`. The
   saved run is also aborted after 2 valid evals (J 32.7379, home-v7). Its saved-mesh bbox is still
   readable (541.3 × 298.6 × 238.1 mm), but the design cannot be rebuilt from its own recipe.
4. **A2/A3/C2/K2/R1 `run.json` still says `status: running`.** Those runs were stopped by the night
   watchdog (exit 75, `no_gain_valid`) so `run.json` was never finalized. The authoritative valid
   counts come from `runs/nights/*/summary.jsonl` (`valid_rows_window`) and the `search.ndjson` row
   counts, and are recorded as such: A2 30, A3 30, C2 10, K2 30, R1 30.
5. **K1's v10 best has only v7 terms stored.** Design `3545b3e078ac` has stored (v7) terms
   `total 2.9700, dislope 0.037, flat 0.428, flat_cv 0.258, load 0` and a rescored **v10 J 3.7428**.
   The two are different identities and are never summed or ranked together.
6. **Panel fit / real centre spacing: `NOT_YET_AVAILABLE` for every row.** `bl_panel_fit_feasible`
   needs a real `C.BoxPoint`; this slate defines none. The spacing in the register is a
   moving-diameter lower bound (210.5 mm for a 10-inch Faital 10PR300 Sd, 260.5 mm for a 12-inch
   12PR300 Sd from the senior handoff), not a frame-clearance verdict. There is no frame/baffle
   dimension in `examples/drivers/*.yaml`.
7. **No capsule/coupling case.** `driver coupling` here is the mesher's throat-patch check only. No
   BL case id exists for any candidate, so an installed/exterior claim is `NOT_YET_AVAILABLE`.
8. **A5's live config values vs the archived run.** The config sha matches the archived run
   (`e53a0c3ebe76`), so the YAML did not drift; the *generator implementation* did. Re-emitting the
   rows from the current generator is a prerequisite for any A5 work.
