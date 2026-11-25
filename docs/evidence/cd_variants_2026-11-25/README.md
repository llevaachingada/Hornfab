# CD variants of non-CD returned-lip horns: Le Cléac'h AR, Le Cléac'h H/V, Iwata AR + CD backbone

2026-11-25, canonical checkout, v11 objective frozen. Simulated matched verifies (BEAT CUDA, 29-frequency verify
grid, 1024-point balloon DI, freestanding quarter model, 36 mm / 2° assumed source, `mesh.epw` 6). Not
physical-driver measurements. Predictions and pass rules were committed before each batch:
[PREDECLARED.md](PREDECLARED.md) (`4b0e4ddc` batch 1, `09b58272` batch 2). Construction and typology grounding:
[RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md, section 5](../../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md).

**Every design here is a LABELED CD HYBRID** ("<parent> + CD backbone", kind `rows_bb_v1`), a new identity scored
only on `room_landscape_80x50_900_hf1440_v11cd` against its own control: the unmodified parent re-solved on the
same brief. None is compared with its family's original-brief J. Neutral controls build the bare parent's verify
mesh byte-for-byte (`apply_cd_backbone.py --base-config`, and `tests/test_cd_backbone_geometry.py`).

## What the evidence says

- **No CD variant passes all six rules (14 solves, 11 candidates).** The H corridor misses at the 8 kHz bin
  every time (best 59.9°, `iwar` roll-in 0.20; rule floor 62°), and every candidate fails rule 2 somewhere in
  2–4 kHz (the controls already fail it at 3.5–4 kHz).
- **The backbone does turn these narrowing parents toward CD.** The controls narrow monotonically to 39.4–40.2°
  H at 8 kHz (the rolled control was 54.8°). At full strength with roll-in 0.20 the 6–7 kHz H reaches 61–69° and
  8 kHz gains +17.2 to +20.5° over the control. `lcl` (Le Cléac'h H/V) becomes nearly flat in H at ~59–75° from 1.5 to 8 kHz
  ([card](renders/lcl_bb_h100_v000_t25_r20.png)); its 2–4 kHz H is 61.8 / 71.0 / 67.3 / 69.9 / 71.3 / 75.0°, failing
  rule 2 only at 2037 Hz, and loading is unchanged (min Re z 0.988 vs 0.983).
- **The body angle these parents can host is the limit, not the construction.** At the keeper window the solved
  θc is 31–38° (rolled bodies 38.7–39.7°); shortening the roll-in to raise it (0.30 → 0.20, +3.1 to +3.3°) was
  the most effective knob tried (+1.3 / +3.0 / +3.1° at 8 kHz for `lcar` / `lcl` / `iwar`, up to +11.3° at 6 kHz), and it moved the mid-band
  waistband instead of removing it (`lcar` 53.0° at 2335 Hz, `iwar` 49.6° at 2335 Hz) — the Lamé pattern.
- **The section hypothesis is rejected.** Applying the backbone to the V-side rows as well (`bb_v` 1.0) moved
  8 kHz H by only +0.6° (`lcar`) and −0.1° (`lcl`), collapsed V by 12–17° at 6–8 kHz (V θc only 15–21°) and
  cost loading (min Re z 0.44 / 0.68). V on these parents is mouth- and roll-on-limited, as on the rolled body.
- **Loading.** `lcl` and `iwar` keep their loading through every arm. `lcar` (Le Cléac'h AR, stop 185°) loses
  it at full strength (0.67 vs floor 0.736).
- **J does not select.** J falls 11–12 → 5.4–6.7 while no candidate passes; `iwar` roll-in 0.20 has the lowest J
  (5.43) and a 49.6° waistband.

Predictions vs outcome: the controls' HF defect held. `lcl` 0.65 passing (predicted) **failed** (8 kHz 51.7°).
`lcar` 0.65 reaching rule 1 (called 50/50) failed. `iwar` 0.65 failing rule 1 held. The predicted ΔH ranking
`lcl` ≥ `lcar` > `iwar` failed: `iwar` gained most at roll-in 0.20. The roll-in addendum's "no job reaches 62° at
all five bins" held; its "+1 to +5° at 8 kHz" held (+1.3 to +3.1°). Section arm: rejected as written.

## Pass-rule check (applied by [analyze.py](analyze.py) via `../cd_backbone_2026-11-25/analyze.py::check`)

| Job | J | H 6085 / 6325 / 6977 / 7113 / 8000 | H 2–4 kHz (6 bins) | ΔV HF min | min Re z (ctl) | Rules failed |
|---|---:|---|---|---:|---|---|
| `lcar_control` | 11.704 | 45.5 / 44.5 / 42.5 / 42.2 / 40.2 | 73.7 / 69.7 / 65.1 / 62.0 / 58.6 / 54.9 | — | 0.836 | control |
| `lcar` 0.65, t.25 r.30 | 7.923 | 56.3 / 56.0 / 54.6 / 54.3 / 51.2 | 62.4 / 58.6 / 55.2 / 55.9 / 55.6 / 54.9 | −0.89 | 0.748 | 1, 2, 3 |
| `lcar` 1.0, t.25 r.30 | 6.744 | 64.1 / 63.4 / 61.1 / 60.5 / 56.1 | 57.7 / 52.6 / 51.1 / 55.1 / 58.6 / 58.5 | +1.23 | 0.673 | 1, 2, 5 |
| `lcar` 1.0, t.25 r.20 | 6.645 | 69.0 / 67.5 / 63.3 / 62.5 / 57.4 | 55.7 / 53.0 / 61.2 / 63.6 / 63.0 / 68.4 | −0.77 | 0.668 | 1, 2, 3, 5 |
| `lcar` 1.0 + `bb_v` 1.0 | 10.010 | 57.9 / 58.0 / 57.8 / 57.7 / 56.7 | 61.7 / 52.5 / 49.1 / 50.7 / 56.7 / 55.2 | −17.17 | 0.442 | 1, 2, 3, 5 |
| `lcl_control` | 11.998 | 45.1 / 44.3 / 42.5 / 42.1 / 39.9 | 77.5 / 76.1 / 70.3 / 66.0 / 61.4 / 56.2 | — | 0.983 | control |
| `lcl` 0.65, t.25 r.30 | 7.195 | 54.3 / 54.2 / 53.4 / 53.2 / 51.7 | 66.7 / 65.9 / 64.3 / 60.4 / 58.4 / 57.0 | −1.49 | 0.989 | 1, 2, 3 |
| `lcl` 1.0, t.25 r.30 | 6.071 | 61.7 / 61.0 / 58.9 / 58.6 / 55.7 | 61.6 / 61.9 / 65.8 / 62.9 / 62.5 / 63.5 | 0.00 | 0.985 | 1, 2 |
| **`lcl` 1.0, t.25 r.20** | 6.640 | 65.2 / 63.7 / 61.0 / 60.6 / 58.7 | 61.8 / 71.0 / 67.3 / 69.9 / 71.3 / 75.0 | −1.48 | 0.988 | 1, 2 (2037 only), 3 |
| `lcl` 1.0 + `bb_v` 1.0 | 8.827 | 61.6 / 60.7 / 58.6 / 58.2 / 55.6 | 66.1 / 64.6 / 66.8 / 60.9 / 64.6 / 64.9 | −12.13 | 0.680 | 1, 2, 3, 5 |
| `iwar_control` | 10.949 | 43.5 / 43.0 / 41.8 / 41.6 / 39.4 | 75.2 / 73.5 / 68.7 / 67.3 / 60.1 / 54.0 | — | 0.953 | control |
| `iwar` 0.65, t.25 r.30 | 8.514 | 48.4 / 48.9 / 49.9 / 49.9 / 50.2 | 62.4 / 61.4 / 56.0 / 53.9 / 50.8 / 48.5 | −2.57 | 0.988 | 1, 2, 3 |
| `iwar` 1.0, t.25 r.30 | 7.647 | 56.1 / 56.9 / 57.8 / 57.9 / 56.8 | 56.9 / 55.4 / 50.3 / 48.3 / 47.1 / 50.4 | −5.77 | 0.954 | 1, 2, 3 |
| `iwar` 1.0, t.25 r.20 | 5.428 | 67.4 / 67.3 / 65.8 / 65.2 / 59.9 | 54.5 / 49.6 / 54.4 / 59.6 / 60.0 / 58.3 | +2.51 | 0.955 | 1, 2 |

No multilobe bins anywhere. Rules 4 and 6 pass everywhere. The closest to the corridor is
**`lcl_bb_h100_v000_t25_r20`** ("Le Cléac'h H/V + CD backbone"): it misses the 7–8 kHz floor by 1.0–3.3°, the
2037 Hz floor by 3.2° and V by ≤ 1.5°. It is not a passer and gets no refined-mesh gate (predeclared: passers only).

Full bins: [results.json](results.json). Figure: [curves.png](curves.png) (H and V −6 dB widths per family).
Design cards (views + full-width H/V maps): `renders/<job>.png` for the three controls and the full-strength
roll-in 0.30 and 0.20 jobs, e.g. [lcl control](renders/lcl_control.png) →
[lcl 1.0 r.20](renders/lcl_bb_h100_v000_t25_r20.png).

## Why the rolled recipe did not transfer (CPU diagnostics)

- [feasibility.json](feasibility.json): chord and θc per parent on the CD brief, envelope fit. Salmon
  (608.7 mm tall > 480) and the 1-inch Le Cléac'h designs (265–321 mm mouth) were excluded before any solve.
- [arc_diagnostic.json](arc_diagnostic.json): the 55–110 mm lever band sits at arc fraction 0.16–0.36 on every
  parent, as on the rolled body (0.20–0.40), so it is not an arc-scaling artefact. `lcl` at full strength has an H
  wall of 30.7 / 37.3 / 37.5° at 55 / 80 / 110 mm, close to the rolled keeper's 28.8 / 33.2 / 36.8°, yet 8 kHz H is
  55.7° vs 68.5°. The controls are already ~15° narrower at 8 kHz than the rolled control at similar early walls;
  what sets that offset (the round/elliptical section and short late wall — the rolled body reaches 45° at 150 mm,
  these 28–34° — or the rollback geometry) is **not** isolated by these runs. The `bb_v` arm ruled out the simplest
  section explanation.

## Next lever (not run; owner's call on the look)

Body-angle knobs are exhausted by the predeclared stop rule. What is left changes the visible form, so each would
be its own labeled step:

1. **`lcl` only, a wider late wall / mouth:** the 8 kHz shortfall is 3.3° and the parent's H chord is 41°; raising
   the roll-on station outward (larger H `fc` reduction or a later rollback) raises the chord and so θc [inferred, untested]. This is the
   cheapest candidate to finish a "Le Cléac'h H/V + CD" identity.
2. **Salmon elliptical:** needs a height scale step to fit 480 mm before a CD variant is meaningful (largest H/V
   chords of all targets, 45.5 / 36.3°).
3. A rows-level CD construction (a different parent law, not a blend) if the owner wants these families'
   rollbacks with a true CD body; that is a new typology, not a variant.

## Jobs actually run

One solve at a time, `HORNLAB_GPU_LOCK=refuse`, runner hygiene before and after each job, 0 failures. Queues
[cd_variants_b1](../../queue/cd_variants_b1_2026-11-25.yaml), [cd_variants_b2](../../queue/cd_variants_b2_2026-11-25.yaml).

| Batch | Job | Run dir | DOF | Job wall s | VRAM baseline MiB |
|---|---|---|---:|---:|---:|
| 1 | `lcar_control` | `runs/20261125T163109Z-verify-6aaa2d` | 2233 | 43.7 | 1305 |
| 1 | `lcar_bb_h065_v000_t25_r30` | `runs/20261125T163155Z-verify-a6e3e4` | 2311 | 45.4 | 1332 |
| 1 | `lcar_bb_h100_v000_t25_r30` | `runs/20261125T163245Z-verify-40d7d8` | 2343 | 50.9 | 1332 |
| 1 | `lcl_control` | `runs/20261125T163340Z-verify-2a61aa` | 1777 | 49.7 | 1334 |
| 1 | `lcl_bb_h065_v000_t25_r30` | `runs/20261125T163430Z-verify-6802e7` | 1885 | 47.4 | 1332 |
| 1 | `lcl_bb_h100_v000_t25_r30` | `runs/20261125T163521Z-verify-8e0cad` | 1967 | 46.0 | 1332 |
| 1 | `iwar_control` | `runs/20261125T163609Z-verify-ebd20a` | 1769 | 41.9 | 1334 |
| 1 | `iwar_bb_h065_v000_t25_r30` | `runs/20261125T163652Z-verify-b4eac0` | 1838 | 42.7 | 1396 |
| 1 | `iwar_bb_h100_v000_t25_r30` | `runs/20261125T163737Z-verify-33eb2a` | 1882 | 44.7 | 1334 |
| 2 | `lcar_bb_h100_v000_t25_r20` | `runs/20261125T164016Z-verify-0eecac` | 2368 | 46.8 | 1313 |
| 2 | `lcl_bb_h100_v000_t25_r20` | `runs/20261125T164108Z-verify-5ee4d1` | 2007 | 45.7 | 1348 |
| 2 | `iwar_bb_h100_v000_t25_r20` | `runs/20261125T164155Z-verify-53f19e` | 1930 | 46.2 | 1332 |
| 2 | `lcar_bb_h100_v100_t25_r30` | `runs/20261125T164244Z-verify-aad998` | 2392 | 48.9 | 1332 |
| 2 | `lcl_bb_h100_v100_t25_r30` | `runs/20261125T164337Z-verify-12b4fc` | 2015 | 47.5 | 1396 |

## Caveats

- These parents are sampled on a 15 × 32 grid (rolled 65 × 129); the backbone is evaluated at those stations
  only, and verify DOF is 1769–2392. No refined-mesh solve was run (no passer).
- 36 mm assumed source; no bempp cross-check; real driver wavefronts not modelled.

## Reproduce

```powershell
.venv\Scripts\python.exe docs/evidence/cd_variants_2026-11-25/feasibility.py
.venv\Scripts\python.exe tools/geometry/apply_cd_backbone.py --run runs/20261116T040157Z-screen-402831 --design a85be6929ad5 `
    --out examples/typologies/cd_variants_2026-11-25 --prefix lcl `
    --base-config examples/typologies/cd_backbone_2026-11-25/rolled2_bb_control.yaml --recipe 1.0,0,0.25,0.20
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/cd_variants_b1_2026-11-25.yaml
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/cd_variants_b2_2026-11-25.yaml
.venv\Scripts\python.exe docs/evidence/cd_variants_2026-11-25/analyze.py
.venv\Scripts\python.exe docs/evidence/cd_variants_2026-11-25/arc_diagnostic.py
```
