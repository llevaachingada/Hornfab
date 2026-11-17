# FABLE_RESEARCH_REQUESTS — four bounded requests

All four are read-only against `runs/` and the dataset. No GPU, no BEM, no queue or config change,
no tracked-file edit. Write outputs under `scratch/fable_architecture/`. Record HEAD SHA and
timestamp. Starting point for replay code: `scratch/fable_architecture/fable_zero_gpu_checks.py`.

## R1. Is mesh error smaller than frequency-sampling error? (could change the recommendation)

- **Scope:** every design solved more than once with a different mesh: same `design_hash`, different
  `mesh_hash`, in `runs/**/search.ndjson`, `runs/study-*/{screen,verify}` and the dataset. Also
  list every config whose verify or confirm mode sets a different `res_mm` or DOF cap than screen.
- **Method:** pair the rows; interpolate both responses to one 58-point log grid (350–8,000 Hz);
  score both with the canonical replay; report per-term and J deltas against the DOF ratio.
- **Output:** `MESH_FIDELITY_PAIRS.md` with the pair count, a delta table, and one line stating the
  standard deviation of the J delta among designs with J below 5.
- **Decision affected:** whether the specification leads with grid-invariant scoring (mesh delta
  below about 0.1 J) or with a mesh-fidelity ladder (above about 0.17 J).
- **Stop:** 30 pairs, or a statement that no such pairs exist. If none exist, say so and stop; do
  not solve anything.

## R2. How many frequencies does a grid-invariant J need? (sizes the throughput gain)

- **Scope:** the 58 screen/verify pairs in `runs/study-*`.
- **Method:** first make the replay parity-exact, including the `di` term (my harness regenerates
  DI from a different source; find which and match the stored value to 1e-6). Then: (a) repeat the
  dense-grid comparison; (b) from each 29-point verify response keep 8, 10, 12, 15, 18 and 22
  log-spaced points, interpolate back to 58, and compare J with the full 29-point result;
  (c) repeat (b) with complex-pressure rational interpolation where `p_h`/`p_v` are stored.
- **Output:** `FREQUENCY_BUDGET.md`: bias, standard deviation and top-28 rank correlation versus
  point count, for both interpolants.
- **Decision affected:** the screen frequency grid, and whether J terms should be defined as
  log-frequency quadratures.
- **Stop:** the six point counts above, two interpolants, nothing more.

## R3. Does a corridor objective re-rank the top? (could change the recommendation)

- **Scope:** every `ok` row from runs whose brief is the 80×50 / 600×480×480 landscape brief
  (about 3,400 rows, 35 configs, 2026-11-15 onward).
- **Method:** write three candidate v9 `coverage_profile` blocks as scratch YAML (not under
  `examples/`): H 60–90° from 700 Hz in all three; V 40–60° with onset at 700, 1,000 and 1,250 Hz,
  free above the corridor below onset. Rescore every row with the canonical replay under v7 and
  each candidate. Mark the candidates clearly as placeholders awaiting the owner's choice.
- **Output:** `CORRIDOR_RERANK.md`: for each candidate, overlap of the top 20 with v7, rank
  correlation within the top 100, best row per config, and which configs change position by more
  than three places.
- **Decision affected:** whether the corridor is the first change (top 20 moves) or a refinement
  (it does not).
- **Stop:** three candidates. Do not tune the corridors to produce a result.

## R4. Seed spread versus config gaps (sizes how much past lane comparisons mean)

- **Scope:** the same landscape-brief runs; any config with three or more runs that differ only by
  seed or start.
- **Method:** best screen J per run at matched valid-row counts (use the smallest common count);
  report within-config spread and between-config gaps; flag runs that the watchdog stopped.
- **Output:** `SEED_SPREAD.md`: one table, plus the ratio of median within-config spread to the
  median gap between adjacent configs in the ranking.
- **Decision affected:** whether lane consolidation needs matched-budget reruns before any family
  is dropped.
- **Stop:** the existing runs only. If fewer than four configs qualify, report that and stop.
