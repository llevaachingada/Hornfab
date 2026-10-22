# PR #15 (Boundary Lab learnings) — local GPU test plan, 2026-10-22

Plan: `docs/BL_LEARNINGS_IMPLEMENTATION.md` section 4. `main` fast-forwarded `b822dd5 -> 265133f` (PR #15 tip) and
pushed; package reinstalled (`pip install -e .`). RTX 4060 Laptop 8 GB, driver 610.62, Julia 1.12.7.
GPU hygiene before and after every GPU step (julia none before; the one BEAT host left after each search was killed;
VRAM 586-618 MiB throughout). End state: no julia, 618 MiB.

## Step 1 — offline suite: PASS
`pytest -m "not slow and not gpu and not crosscheck"` -> **559 passed, 0 failed, 0 skipped, exit 0**
(cloud: 553 passed + 1 skipped before the rebase, 558 after; +1 here is the mesher-gated test).

## Step 2 — doctor: PASS (10/10)
All 10 checks PASS; `gpu-hygiene: 0 BEAT host(s) alive, VRAM used 586.0 MiB`.

## Steps 3-4 — searches at budget 40

Both configs pin the CMA seed (`search.seed: 1234`), and earlier runs had already walked those trajectories, so the
literal commands mostly replayed the cache:

| Run | Command | Rows | New solves | Result |
|---|---|---|---|---|
| `20261022T162921Z-screen-6381b9` | `search --config examples\freeform_sculpt.yaml --budget 40` | 499 (459 cached) | 40 (39 ok, 1 invalid_geometry) | J 30.945 -> **16.421**: continues the budget-400 trajectory |
| `20261022T163420Z-screen-8eadb3` | `search --config examples\osse_baseline.yaml --budget 40` | 192 (152 cached) | **0 solved**: the 40 budget slots re-evaluated the 40 designs that had failed in the cached prefix (38 mesh_too_large, 2 invalid_geometry; failures are not cached but count toward the budget) | GPU 0.0 s, no new data |

To get 40 genuinely new solves per family, both were re-run from scratch copies of the configs with **only**
`search.seed: 1234 -> 777` changed (bounds, weights, target, mesh untouched; diff = 1 line each):

| Run | Family | Rows | Failures | Seed J -> best J | s/candidate (reported) |
|---|---|---|---|---|---|
| `20261022T163620Z-screen-ce97e5` | FREEFORM sculpt, seed 777 | 41 (40 new) | 0 | 30.945 -> 24.291 | 4.9 |
| `20261022T164002Z-screen-ccef24` | OSSE quarter, seed 777 | 41 (40 new) | 10 (8 mesh_too_large, 2 invalid_geometry) | 22.592 -> 8.940 | 9.8 (failures solve nothing) |

### Checks (a)-(d)

| Check | Result |
|---|---|
| (a) `run.json` `runtime` block | PASS: `gpu` "NVIDIA GeForce RTX 4060 Laptop GPU, 610.62, 8188 MiB", `julia` "julia version 1.12.7", plus `platform`, `python`, `sources` (all 4 runs) |
| (b) report-only line per design | PASS: e.g. "report-only (not in J): SPDI band mean 9.647 dB, range 2.871 dB · listening window re on-axis -1.156 dB · forward beam shape p = 2.402". All six scalars present on every ok row (0 NaN in 41 + 31 + 498 rows) |
| (c) failure kinds unchanged in character | PASS: OSSE first 41 of CP-8c 11 fails (10 mesh_too_large, 1 invalid_geometry) vs new 10 (8 + 2); both invalid_geometry messages come from the mesher ("cannot fit the acoustic geometry to the requested mm resolution"), not from the new topology checks. Sculpt: 0 failures in 40 (6b: 0 in 60) |
| (d) s/candidate within ~1 % of HANDOFF 6b | **Not met literally, but faster, not slower.** Medians per ok candidate: mesh (where the PR adds the topology check) 0.85 s vs 0.86 s in 6b, unchanged. Solve 3.80 s vs 5.58 s at the same mesh size (1364 vs 1356 dofs): 2.9 vs 4.2 ms/dof. The PR does not touch the solver, so the solve-time difference is machine state (GPU clocks / thermal / load), not the PR. OSSE: 3.97 vs 4.28 ms/dof against CP-8c's first 40 |

Note: an offline Python replay (one light CPU process, below) ran during the first, cache-replay pair of searches;
the seed-777 pair ran alone.

### Beam shape, best vs seed (report-only, qualitative at the 512-point screen balloon)

| Run | Seed p | Best p | Seed SPDI | Best SPDI |
|---|---|---|---|---|
| OSSE seed 777 | 2.047 | 1.908 | 9.23 dB | 10.71 dB |
| Sculpt seed 777 | 2.402 | 2.337 | 9.65 dB | 9.70 dB |
| Sculpt continuation | 2.402 | 2.055 | 9.65 dB | 9.34 dB |

### Pinned sculpt anchors after the 40-candidate runs (no bound widened)

| Run (report's top set) | PINNED |
|---|---|
| Continuation, 499 rows (top 50) | `profileH.points.3.1` lo 42/50, `profileV.points.3.1` lo 40/50, `profileV.points.4.1` hi 38/50, `profileV.mouthAngleDeg` lo 26/50, `profileH.points.4.1` hi 25/50 |
| Fresh seed 777, 41 rows (top 5) | no wall anchor; `profileH.mouthAngleDeg` hi 4/5 |

The fresh run is too short to reach the wall; the long trajectory confirms the budget-400 finding (mid-wall radius at
145 mm wants below 108 mm, vertical mouth radius above 200 mm).

## Item 4 offline replay (early rejection)
`docs/evidence/EARLY_REJECTION_REPLAY.md`: on 3,818 candidates of five runs, a rigorous K = 4 lower bound with a 25 %
margin would have rejected 1 candidate (< 0.1 % GPU saved); K = 6 about 0.5 % on OSSE; no top-20 design lost at any
margin. The frequency-subset lower bound is too loose to pay off as specified.

## Step 5
Julia cleared after every search; final `Get-Process julia` empty, VRAM 618 MiB.
