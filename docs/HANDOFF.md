# HANDOFF — Wave ladder complete (Waves 0-3), CP-7 physics gate GREEN

Rewritten 2026-10-13 ~06:40 EDT by the orchestrator (OpenCode). Supersedes all earlier handoffs.
Repo: https://github.com/llevaachingada/Hornfab (local: `C:\Users\hunte\Hrns\hornlab-search`, branch `main`,
Wave-3 commit `73548a5`, CI green at push). The Python package and CLI are still named
`hornlab_search` / `hornlab-search` (issue #11 closed: keep until Collin objects).

## Read first, in this order
1. `docs/CONTINUITY.md` (newest entry on top: state, numbers, open items, next action).
2. `CLAUDE.md` and `AGENTS.md` (rules; includes the **GPU / Julia hygiene** section, mandatory).
3. `TOOLCHAIN.md` (every measured number and the real solver API).
4. `NOTES_FOR_SENIOR.md` — the task-09 block at the end is the durable record of the Wave-3
   rulings and the CP-7 results; earlier blocks (tasks 03-08) are now RULED.
5. `docs/plan/01_CONTRACTS.md` (frozen) and `docs/plan/09_CHECKPOINTS.md` (the checkpoint you
   must never weaken) and `docs/plan/11_PHASE2_SURROGATE.md` (only if phase 2 is wanted).

**Standing rule:** every push updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit.
**Check the real pytest exit code before committing** (a `| tail` once hid a failure).
**One GPU solve at a time; one orchestrator session.** Before any GPU run: `Get-Process julia`
(expect none) and `nvidia-smi` (expect ~0.15-0.45 GB baseline). Verify hosts are actually gone after.

## Where things stand
| Wave | Tasks | Status |
|---|---|---|
| 0 | 02 env, 03 scaffold | done, CP-0 and CP-1 green |
| 1 | 04 design+mesh, 05 solve, 06 metrics, 07 dataset | done, CP-2..CP-5 green |
| 2 | 08 pipeline | done, CP-6 green |
| 3 | 09 senior checkpoints CP-7a..f | **done, CP-7 GREEN** (all six PASS) |

**CP-7 measured numbers** (full pasted output in CONTINUITY 06:20):
- CP-7a analytic sphere: R(ka) spread 0.020 dB (limit 0.5), spreading 6.0205-6.0206 dB, convergence sub3/4/5 = 0.0204/0.0051/0.0013 dB monotone. Acceleration-drive reading CONFIRMED (raw constant-velocity 24.06 dB/octave is expected, not a failure).
- CP-7b two solvers: beat vs bempp **0.039 dB** (limit 0.2).
- CP-7c mesh convergence: PASS on reduced band **500-2500 Hz** (epw=18 full-band reference needs ~40k quarter dofs → OOM on 8 GB): epw=6 → 0.287° bw error, 0.028 dB DI error.
- CP-7d symmetry: 4e-6 dB max asymmetry; M6 full-vs-quarter on the seed **0.023 dB** (≤3 kHz).
- CP-7e plausibility: f0 = 343 Hz (H) / 480 Hz (V) below the 500 Hz band floor; DI-vs-beamwidth 2.15 dB max (borderline vs 1.5 dB guideline, far under the 3 dB "wrong" threshold); f11 = 5653 Hz just above the clipped 5500 Hz band.
- CP-7f **noise floor: 0.039 dB** — dominated by the two-solver disagreement; the epw=6 DI discretization (0.028 dB) sits just below it. The floor is NOT mesh-limited.

**Wave-3 rulings:** every NOTES_FOR_SENIOR block is ruled and the changes are applied
(`config.mesh_spec` → `sizing.max_triangles_for`; ICW wall-half-angle + explicit seed;
acceleration note in `record.py`; pin guard test; `mesh/grid.py` seam). See the task-09 block.
**GitHub:** ALL issues #1-#11 closed. No open issues exist.

## What to do next (in order) — all post-Wave-3, none blocking
1. **Widen `a_deg` and `exponent` bounds** in the example configs (the best design sat at their
   lower bounds in the 60-evaluation smoke search; the report's bound-pinning section names them).
2. **Run the other four example configs** (`osse_baseline`, `throat_adapter`, `icw_termination`,
   `freeform_hv`) to get a multi-family dataset before any surrogate work (CONTINUITY 00:25, item 4).
3. **View `report.html` in a browser** — it has never been visually checked (5.3 MB, inline SVG + hornlab_plots PNGs).
4. Only if wanted: `docs/plan/11_PHASE2_SURROGATE.md` (needs the multi-family dataset from step 2).
   Phase 2 must read the dataset through `DatasetStore` (never `np.load` on a shard archive) and
   regenerate structured grids only via `hornlab_search.mesh.grid.build_point_grid`.

## Residual risks, known and recorded (NOT blockers; in NOTES_FOR_SENIOR task-09)
1. epw=6 discretization above ~2.5 kHz is UNMEASURED (the epw=18 reference cannot be built there on 8 GB). A systematic epw=6 bias in the 2.5-5.5 kHz screening band would bias every ranking; no test catches it.
2. The higher-order throat mode f11 (5653 Hz) is never exercised — the screen band clips at 5500 Hz.
3. DI-vs-beamwidth agreement is not a regression test (only the analytic cardioid/dipole closed forms are).
4. Cross-run solve cache does not dedup the seed across separate `run` then `search` invocations (74 records contain two seed rows).
5. Task 07's `test_append_500_typical_records_is_fast` (5 s limit) can flake under heavy disk load; do not loosen it.
6. `hornlab_mesher.config_builder.resolve_geometry` (pre-mesh guard) and `build_point_grid` are not stable API; the mesher is pinned and guarded by `tests/test_mesh_pin.py`.

## Environment and how to run things
- Interpreter: ALWAYS `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` — never bare `python`.
- Tests: `.venv\Scripts\python.exe -m pytest -q -m "not slow and not gpu and not crosscheck"` — check `$?`.
- CLI: `.venv\Scripts\hornlab-search.exe doctor | version | selftest --analytic | selftest --crosscheck |
  run --config examples\<cfg>.yaml --mode screen | search --config examples\search_smoke.yaml --budget N |
  verify | report runs\<dir> --out report.html | dataset stats|verify|export`.
- `gh` is at `C:\Program Files\GitHub CLI\gh.exe` (logged in as llevaachingada). Multi-line comment
  bodies must go through `gh issue comment <n> --body-file <file>` — a multi-line here-string passed
  inline as `--comment` gets split into multiple arguments by PowerShell.
- BEAT stale-registry hazard (diagnosed during CP-7): old worker records in
  `%LOCALAPPDATA%\HornLab\BEAT\workers` cause `ConnectionResetError 10054` on warm-up. Set
  `HORNLAB_BEAT_WORKER_DIR=<fresh dir>`, or run with `HORNLAB_BEAT_PERSISTENT_HOST=0`.
- `runs/`, `cache/`, `dataset/`, `scratch/`, `report.html` are gitignored; `dataset/` is precious (back it up).
- A fresh Julia host idles at ~1800 s and holds ~1 GB VRAM; `shutdown_workers()` DOES release it
  when polled to completion (task 05), but verify with the process list anyway.
- Known GPU limits (8 GB RTX 4060 Laptop): quarter-domain ~8.9k dofs OK / 15.7k OOM; full-domain 5.5k OK / 9.2k OOM.
  Seed horn (0.40 x 0.32 x 0.26 m) at epw=6 resolves to ~6.3 kHz within the 5,000-dof screen cap.

## Measured facts you will need (full tables in TOOLCHAIN.md)
- Real solver API: `hornlab_beat_bem` 0.2.0 returns `SolveResult`; dofs = `mesh_info.n_vertices`; dof/triangle 0.500 full, ~0.51 quarter.
- One multi-frequency `solve_frequencies` call thrashes above ~2.4k dofs; the CUDA adapter loops per frequency.
- Per-frequency warm cost (quarter): 2.4k ≈ 0.4-0.8 s, 5.1k ≈ 2.8 s, 7.0k ≈ 7.5 s, 8.9k ≈ 45 s.
- Throughput: `search_smoke` ~4.25 s/candidate (~847/h); the `osse_baseline` seed alone ~18 s. Cold start 17-29 s.
- Impedance (Robin) BCs exist only in bempp (`impedance_sources`, not with Burton-Miller) — settled, issue #7.
- Traces: 111 kB/frequency at 2.4k dofs; pressure in .msh node order, Neumann in triangle order (issue #8).
- The balloon is a theta-phi grid (not equal-area): DI must use sin(theta) weights (as task 08 already does).

## Loose ends
- The report HTML was never viewed in a browser (see next-work item 3).
- `timeout_s` is checked between frequencies only; bempp makes one call.
- beat uses dense LU: `gmres_tol` is recorded as requested, not applied.
- The `report.html` noise-floor box says 0.055 dB "limited by beat vs bempp, epw=6 not measured" — superseded by CP-7 (0.039 dB floor, mesh not limiting); it can be refreshed from run.json["noise_floor"] on the next report run.
- `hornlab_search.egg-info/` and `.opencode/` are gitignored local artifacts.