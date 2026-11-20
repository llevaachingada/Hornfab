# Expansion night evidence - 2026-11-19 (`fable_expand_2026-11-19`, 16 jobs)

**What this is.** The owner-directed 3-4 h GPU expansion night assembled from the ISSUES report:
(A) full-polar/balloon DI on the compact400 trio and the v7 leaders (ranker tie-break evidence);
(B) compact400 (new identity) data expansion with independent CMA seeds; (C) ripple-mandate item 3
(dense-frequency B3 re-solve). One `run_campaign_night` queue, `HORNLAB_GPU_LOCK=refuse`, UTC dirs.

All runs: `mode` as stated, 73 angles / balloon 512-1024 points, epw 6 (B3 epw9 variant 9), dof cap
24k. Driver HF1440 unless stated. The archive holds `run.json` (full config + brief snapshot +
knobs), `search.ndjson`, `best.json`, the best `design.json` + `mesh.msh` + `response.npz`.

## A. Full-polar DI tie-breakers (181 angles / 2048 balloon points, verify mode)

Same grid for all three compact runs, so these J values ARE comparable:

| run | design | J (verify DI) |
|---|---|---|
| x_di_morph | 151d74ef7d39 | **1.1692** |
| x_di_fold | d1f652b9a9fa | **1.2558** |
| x_di_twinray | 4274295bcb87 | **1.3591** |

morph < fold < twinray at both resolutions (73/1024 pass: 1.1864 / 1.2763 / 1.3734). Gaps 0.087 and
0.103 are inside the compact floor (0.1293), so it remains a 3-way tie by the floor, but the ordering
is stable and morph leads.

The v7 leaders were run through the same DI pass: petal **4.8991** (151d74ef7d39), tritonia v9
**6.8367** (d1f652b9a9fa), tritonia v8 **5.5564** (4274295bcb87). These are 29-frequency verify-grid J
and are **NOT comparable** to the 18-frequency screen J (4.1202 / 4.878 / 4.7503); recorded so the
ranker does not mix grids.

## B. Compact400 new-identity expanded data (independent CMA seeds)

SeedB (CMA seed 2027, 80 valid evals budget, screen): morph 1.7219, fold 1.4425, twinray 1.4873,
petal 1.5941, ext 1.8320. SeedC (seed 2028, 60 evals): morph 1.6143, fold 1.2144, twinray 1.6883.
None beats the warm-started winners - intended dataset growth rather than a winner hunt. Note seedC
fold 1.2144: an independent cold start reaches the same basin as the warm winner (1.2071), which is
useful robustness evidence for the fold family.

## C. Ripple-mandate item 3 - dense-frequency B3 re-solve (STATUS: first attempt invalid, dense2 pending)

The first two runs (x_r3_b3_dense_epw6/epw9, archived here) came back with **n=18 frequencies**: the
config-level top-level `grid:` block is IGNORED by the runner (brief.grid wins), so the 73 dense
frequencies never applied and the two runs are identical 18-freq spectra (mean|d| 0.00 dB). They are
kept for the record only; they do NOT answer item 3.

Fix applied: `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth_dense.yaml`
(screen_extra_hz = the 6 v7 extras + 1.8-3.6 kHz @25 Hz = 79 extras) and `x_r3_b3_dense2_epw6/9`
appended to the live night after the other agent's 8 jobs. The predeclared criterion stands: the
2.27-3.31 kHz deviation must persist with stable amplitude at both mesh densities (epw 6 and 9) on
the dense grid; the epw6-vs-epw9 agreement is the mesh-independence check.

## Provenance

- Interpreter `.venv\Scripts\python.exe`; git `079e227`+ (docs/queue) at run time.
- Configs `examples/typologies/expand_2026-11-19/`; night `docs/queue/fable_expand_2026-11-19.yaml`.
- Owner-directed; all launches `HORNLAB_GPU_LOCK=refuse`; no solve was ever concurrent.
