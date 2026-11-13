# BO-study performance preparation (S9, 2026-11-12)

Status: **offline preparation only.** No solve, benchmark, host cleanup, provisioning, queue edit or
Git mutation was performed in this slice. The GPU night queue owns the live lanes from this
checkout. This document prepares the measurement matrix; it is not a performance result and it
claims no speedup.

Scope: the bo-study-v1.1 M2 question — does the study-runner serial path beat the current serial
evaluate path at matched total cost, with identical physics and no spill? The full operational
plan (arms, matched-cost definition, exact matrix, parity/identity checklists) is in
`scratch/bo_m0/s9/AB_MATRIX_PLAN.md`; measured baseline rows are in
`scratch/bo_m0/s9/baseline_table.csv`.

## 1. Fake harness (`tools/bench/fake_harness.py`)

`tools/bench/fake_harness.py` is a deterministic, offline fake-evaluator harness. It:

- synthesises `search.ndjson`-shaped rows and `stage_timing.ndjson`-shaped rows from a seed;
- replays them through the S3 cost ledger (`tools/analysis/_common.py::cost_ledger`, consumed
  read-only as-is) so rows/attempts/cache/new-BEM/refusals/failures use the same semantics;
- emits its own stage reconciliation (whole-run elapsed vs candidate totals vs nested stages vs
  overlapping prefetch) without modifying `hornlab_search/profiling.py`;
- never imports a solver or mesher, never starts a process and never writes an acoustic record.

Stage rows mirror the opt-in `HORNLAB_STAGE_TIMING` format (`stage`, `seconds`, `design_hash`,
`key`, `thread`, `unix_time`; constants are imported from `hornlab_search.profiling`, which is not
modified).

CLI:

```powershell
# Accounting rehearsal: in-memory only, writes just the timing JSON.
.\.venv\Scripts\python.exe tools\bench\fake_harness.py --dry-run --seed 7 `
    --candidates 24 --prefetch-depth 2 --meh `
    --out scratch\bo_m0\s9\example_dry_run_timing.json

# Same fixture, but persist the synthetic rows + stage NDJSON + a timing-ledger manifest.
.\.venv\Scripts\python.exe tools\bench\fake_harness.py --seed 7 --candidates 24 `
    --fixtures-dir scratch\bo_m0\s9\fixture
```

`--dry-run` reports `solve_processes_started: 0`, `acoustic_records_written: 0` and
`fixture_files_written: 0`; it creates no fixture directory and only writes the requested timing
JSON. Without `--dry-run` and with `--fixtures-dir`, it writes three **synthetic** files
(`search_fixture.ndjson`, `stage_timing.ndjson`, `timing_manifest.json`) and still starts no solve
and writes no acoustic record. The generated manifest is directly consumable by
`tools/bench/timing_ledger.py`.

Reconciliation identity emitted by the harness (and asserted by
`tests/test_tools_bench_fake_harness.py`):

```
elapsed = candidate_total_sum + run_overhead_s + prefetch_wait_s
```

`candidate_total` already contains `mesh_build`, `solve`, `metrics`, `score`, `cache_store` and
`persist`; `solver_path` and `meh_inner_optimize` are nested subsets; `mesh_prefetch` runs on
another thread and overlaps the main loop. Summing every stage row therefore overcounts; the
harness reports that overcount explicitly instead of treating it as overhead.

Limits: every number is fabricated and labelled `synthetic`. The harness proves that the
accounting reconciles; it cannot identify the real bottleneck, measure a solver, or support a
speedup/physics claim. Attempts carry `verified_useful: null` — verification is operator-supplied,
never inferred.

Focused tests: `tests/test_tools_bench_fake_harness.py` (6 tests: same-seed byte determinism,
zero-solve/zero-fixture dry run, ledger + stage reconciliation, failure-path accounting, stage
schema, CLI dry run).

## 2. Measured baseline (existing evidence only)

No new number is introduced here. Full rows and line citations are in
`scratch/bo_m0/s9/baseline_table.csv`; the sources are:

- `TOOLCHAIN.md` M3 (warm quarter mesh, 73 angles, 512-point balloon, solve only):
  per frequency 2,369 dofs 0.4 s; 5,140 dofs 2.8 s; 7,001 dofs 7.5 s; 8,941 dofs 45 s.
  Screen-like 12 + balloon: 5.04 s at ~2.4k dofs; 33.3 s at ~5.1k dofs (12 single-frequency calls;
  a multi-frequency sweep was 688.9 s). Candidates per hour: **~700 at 2.4k**, **~110 at 5.1k**.
  Verify at the 7,000 cap: 25 × 7.5 s ≈ 3 min per candidate.
- `TOOLCHAIN.md` M2: measured VRAM ceiling full domain between 5.5k and 9.2k dofs, quarter domain
  between 8.9k and 15.7k dofs; both are memory-pressure territory above ~5k.
- `TOOLCHAIN.md` M4: CUDA vs CPU warm per frequency — 2,369 dofs 0.8 vs 1.45 s; 5,140 dofs 2.8 vs
  6.6–7.6 s; 7,001 dofs 7.5 vs 12.6–37.4 s; 8,941 dofs 45 vs 56.6–57.8 s.
- `docs/evidence/THROUGHPUT_N1_2026-11-12.md`: warm 12-frequency batching at ~1k/~4k/~8k dofs
  (class inferred in that document) — fused ON b12 1.273 / 8.488 / 25.015 s; b1 5.957 / 18.040 /
  47.075 s; fused OFF b12 1.608 / 12.053 / every warm rep failed. Peak VRAM 1334 / 3167 / 4900 MiB
  (fused ON). Prefetch was neutral on warm time (1k 1.257 vs 1.273 s; 4k 8.754 vs 8.488 s) and the
  8k fused-OFF arm OOM'd at 7,731 MiB.
- `docs/evidence/THROUGHPUT_N1_2026-11-12.md` §4: verify J was worse than screen J in 95% of 104
  stored pairs; within-run Spearman of the screen top-5 vs verify was often 0.1–0.3. This is why
  the outcome metric is **verified useful designs/hour**, not screens/hour.

## 3. Two study lanes

Device caps in force (quarter domain): **screen 5,000 dofs / verify 7,000 / final 8,900**
(`TOOLCHAIN.md` M3). Full-domain verify/final are not available on the 8 GB RTX 4060.

| Lane | dof cap | measured basis | measured/derived expectation |
|---|---|---|---|
| screen | 5,000 | 5.04 s at ~2.4k; 33.3 s at ~5.1k (12 frequencies + balloon, solve only) | ~700/h at 2.4k; ~110/h at 5.1k (`TOOLCHAIN.md` M3) |
| verify | 7,000 | 7.5 s per frequency; 25 × 7.5 s ≈ 3 min/candidate | ≈20/h by arithmetic; **not separately measured** |

These are solve-only warm figures. They exclude meshing, metrics, persistence, verification,
training/analysis overhead, cold starts, failures and refusals. The A/B metric must include all of
them.

## 4. Later A/B matrix (summary)

Full matrix: `scratch/bo_m0/s9/AB_MATRIX_PLAN.md` §4.

| ID | Purpose |
|---|---|
| P0 | frozen-candidate runner/evaluator parity (arrays and J) |
| P1 | screen-lane matched cost (18 screen slots at the 5k cap) |
| P2 | headline: 18 screen + 6 verify slots, verified useful designs/hour |
| P3 | cache-identity control (same recorded cache state) |
| P4 | memory/spill audit on the P2 arms |
| P5 | separate later CPU/GPU study, only where lane policy allows |

Arms: **A** = current `hornlab_search/search/evaluate.py` serial path; **B** =
`hornlab_search/studies/runner.py::run_package` (`adaptive_serial`, explicit `gpu` lane,
`b5-journal-v1` + `b5-owned-lane-v1`). B's production adapter is not wired in this slice, so P1/P2
are blocked on that separate reviewed work.

Matched total cost means the same task/objective, the same screen/verify call counts by kind, the
same total observed BEM calls/seconds (within arm A's measured `warm_rel_spread`), the same cache
state, the same dof caps and the same verification policy. A/B candidate sequences may differ
because B proposes adaptively; only P0 requires candidate identity.

Requirements carried by the matrix:

- **Measured bottleneck first**: run the stage ledger on both arms before proposing any change;
  only a reproducible dominant stage counts. Synthetic harness numbers never identify a bottleneck.
- **Memory/spill baseline**: record the `nvidia-smi` baseline, per-host-tree dedicated and shared
  peaks and the spill flag for every GPU arm.
- **Frequency/array parity**: exact requested frequency array and order; matching presence/shape
  for H/V polar cuts, balloon and complex throat impedance; predeclared tolerances; inspect
  per-frequency residuals. `compare_search_runs.py` and `throughput_matrix.py` summaries do not
  prove full array parity.
- **Cache/spec/library identity**: cache identity, config/brief/objective hashes, physical/metric/
  score identities, solver/mesher pins and `lib_shas`, backend, symmetry, grids and `HORNLAB_*`
  environment recorded with every run. Unknown identity makes the comparison descriptive only.
- **CUDA timing validity**: a CUDA timing is valid only when the host tree's
  `\GPU Process Memory(*)\Shared Usage` is near zero. `AGENTS.md` GPU hygiene rule 8 and
  `TOOLCHAIN.md` M2 document the Windows WDDM shared-memory fallback; `tools/bench/_bench_common.py`
  samples it and sets `SPILL_MIB = 512`. Above that, the solve is paging, not GPU speed.
- **Decision**: accept only when the repeated benefit exceeds run-to-run variability (2026-10-23
  beats rule, >= 5 runs for a verdict), quality/shortlist recall are maintained, zero
  treatment-attributable failures occur and no accepted CUDA arm spilled. Otherwise record no gain
  or inconclusive.

## 5. Open items

- Production runner adapter (`b5-journal-v1` / `b5-owned-lane-v1`): separate reviewed slice needed
  before P1/P2 execute.
- Fork arithmetic/memory change (e.g. LU reuse across changed geometry/frequency): separate
  follow-up with exact owner, pinned commit, analytic + independent-backend + same-mesh response
  parity and memory gates per `docs/FORKS.md`. Current pin
  `0850ef39b29d7c51f8fbb082184d3784d2ff8bef` already fuses multi-channel assembly with one LU per
  frequency for identical geometry/frequency; no new reuse is assumed.
- Real measurements wait for explicit lane-owner authorisation. The harness is a rehearsal only.
- Parent integrator should update `docs/INDEX.md` / `docs/CODE_MAP.md` when committing this new
  tool/doc (this slice does not push).

## 6. References

- `scratch/bo_m0/s9/AB_MATRIX_PLAN.md`, `scratch/bo_m0/s9/baseline_table.csv`,
  `scratch/bo_m0/s9/example_dry_run_timing.json`.
- `tools/bench/fake_harness.py`, `tools/bench/timing_ledger.py`, `tools/analysis/_common.py`.
- `TOOLCHAIN.md` M2–M4; `docs/evidence/THROUGHPUT_N1_2026-11-12.md`;
  `docs/throughput/RUNBOOK.md`; `AGENTS.md` GPU/Julia hygiene.
- `docs/research/DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md` S9;
  `docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`.
