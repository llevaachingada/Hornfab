# S9 — bo-study-v1.1 A/B matrix plan (preparation, 2026-11-12)

Status: **planned only**. No lane was measured, no solve was started, no queue or host was touched.
The GPU night queue owns the live lanes from this checkout. This plan is the exact later matrix;
it is not a result and it claims no speedup.

Companion: `docs/throughput/BO_STUDY_PERF_PREP_2026-11-12.md`; harness
`tools/bench/fake_harness.py`; example dry-run output
`scratch/bo_m0/s9/example_dry_run_timing.json`; measured baseline rows in
`scratch/bo_m0/s9/baseline_table.csv`.

## 1. Question

At the same total acoustic cost, does the **study-runner serial path** produce more
**verified useful designs per hour** than the **current serial evaluate path**, with identical
physics, better-or-equal shortlist recall, and no memory spill?

This is an orchestration/evaluation-path comparison, not a solver-arithmetic change. A fork change
(LU reuse, assembly change) is a separate reviewed follow-up (section 11).

## 2. Arms

| Arm | Path | Current state |
|---|---|---|
| **A — current serial evaluate** | Existing `hornlab_search/search/evaluate.py` (`evaluate(...)`) driven by the current pipeline/search or night job: screen then verify finalists, one BEM solve at a time | Today's production path |
| **B — study-runner serial path** | `hornlab_search/studies/runner.py::run_package` with `execution_mode: adaptive_serial`, explicit `lane: gpu`, `b5-journal-v1` journal and `b5-owned-lane-v1` lane adapter | Core contract exists; **no production adapter is wired** — `run_package` returns `capability_missing` unless the documented atomic journal/lane contracts are implemented. Landing that adapter is outside this prep slice |
| **A0/B0 — runner parity** | Same frozen candidate list through A's evaluator and B's evaluator adapter, no adaptivity | Isolates runner overhead and confirms identical arrays/J |

A/B candidate sequences will differ because B proposes adaptively. That is why the headline metric is
verified useful designs per hour at **matched total cost**, not a per-candidate wall-clock delta. The
A0/B0 parity arm is the only place where candidate identity is required.

## 3. Matched total cost (predeclared)

Two runs are matched only when all hold:

1. Same task/config/brief/objective version (M0 frozen native-only v4 task).
2. Same screen/verify **call counts by kind** (the runner's own caps are
   `screen_calls <= 18`, `verify_calls <= 6`, `total_calls <= 24`, `attempts <= 120`); arm A must
   execute the same 18 screen + 6 verify slots, not 24 screens.
3. Same total observed BEM calls and total observed BEM seconds; the difference must be within
   arm A's own measured warm relative spread (`warm_rel_spread` in `throughput_matrix.py`'s
   `summary.csv`). A larger difference is "not matched" and the pair is discarded, not reinterpreted.
4. Same cache state: either both start from an empty cache, or both start from the same recorded
   cache identity. Cache hits are reported separately and never counted as new work.
5. Same dof caps: screen 5,000 / verify 7,000 / final 8,900 (section 9).
6. Same verification policy and the same audit/finalist count (so "verified useful" has one meaning).

Failed, refused, cached and unknown attempts are inside the cost, not excluded.

## 4. Exact later matrix

| ID | Purpose | Arm A | Arm B | Fixed inputs | Primary record |
|---|---|---|---|---|---|
| **P0** | Runner/evaluator parity | `evaluate` on a frozen candidate list (8 screen + 4 verify) | `run_package` adapter on the same list, no adaptivity | Frozen config, meshes, frequencies, cache empty | Arrays/J identical within predeclared tolerances; per-call seconds |
| **P1** | Screen-lane matched cost | current serial path, 18 screen slots at the 5k cap | runner, 18 screen slots at the 5k cap | Same task/seed/order policy, fresh cache | New BEM calls/seconds, refusals, failures, verified useful/hour |
| **P2** | Screen+verify matched cost (headline) | current path, 18 screen + 6 verify slots | runner, 18 screen + 6 verify slots | Same task/seed, same verification policy, fresh cache | Verified useful designs/hour, shortlist recall vs common reference, all costs |
| **P3** | Cache-identity control | P2 repeated with a recorded non-empty cache | P2 repeated with the same cache identity | Same as P2 | Cache hits separated; no deletion of the active cache |
| **P4** | Memory/spill audit | P2 arm A | P2 arm B | Same as P2 | `nvidia-smi` baseline, per-host-tree dedicated/shared peaks, spill flag |
| **P5** | Separate later CPU/GPU study | — | — | Same physical spec/candidates, explicit backend treatment | Only after lane policy allows; not part of the GPU A/B verdict |

Each pair is repeated at least 5 times with independent seeds (pilot; expand from paired
variability using the existing `tools/analysis/_common.paired_summary` / `power_planning`
conventions). Counterbalance arm order within pairs where scheduling permits. Report every trial,
median and spread, cold and warm separated.

## 5. Bottleneck-first rule

Before any A/B verdict, run the stage ledger on both arms:

- `HORNLAB_STAGE_TIMING=1` stage NDJSON: `mesh_build`, `mesh_prefetch`, `solve`, `solver_path`,
  `metrics`, `meh_inner_optimize`, `score`, `cache_store`, `persist`, `candidate_total`.
- Replay with `tools/bench/fake_harness.py` semantics (S3 cost ledger): rows, attempts, cache hits,
  new BEM calls observed/inferred, cheap refusals, solver/pipeline failures, failed effort.
- Only a **reproducible** stage that dominates total elapsed is a candidate for optimization.
  Prefix/postfix numbers, single runs and synthetic harness numbers are not a bottleneck claim.

The fake harness proves the accounting; it cannot identify the real bottleneck.

## 6. Identity record (required per run)

Record before the first solve and keep with the results:

- config path + config SHA, brief name + brief hash, objective version, weights, tolerances,
  resolved target, `cov_narrow_ratio`, cohort rule (native-only).
- physical identity: design/mesh/solve/excitation/dependency hashes + raw array digests
  (`objective/replay._physical_identity`).
- metric identity: metric code + target key + `metric_source` + `di_source`.
- score identity: metric id + objective version + weights + objective block + brief hash/name.
- cache identity (cache root/digest), solver/mesher package pins and `lib_shas`
  (BEAT, mesher, bempp), backend, symmetry/quadrant flags, frequency array and order,
  observation angle count, balloon grid, screen/verify batch sizes, `HORNLAB_*` environment.
- hardware/driver, lane (`gpu`/`cpu`), worker registry dir, host tree, start/end UTC.

Unknown or mismatched identity makes the comparison descriptive only. Never pool across a
different task/objective/grid/software identity.

## 7. Parity gates (predeclared, before looking)

- Exact requested frequency array and order; same row count.
- Same presence and shape for horizontal and vertical polar cuts, balloon and complex throat
  impedance.
- Values equal within tolerances fixed before the experiment; inspect per-frequency residuals,
  not only a summary hash.
- Pressure/phase and impedance, beamwidth, DI and objective/gates checked against an
  independent/converged reference where the treatment could alter physics.
- `compare_search_runs.py` checks its documented row keys only; it does not prove full response
  parity. `throughput_matrix.py` summaries likewise do not prove array parity — archive and
  compare the arrays.
- Reject failed/partial arrays and unexpected cache hits.

## 8. Memory / spill gates

- Before every GPU measurement: confirm lane availability and near-idle VRAM; record
  `nvidia-smi memory.used` baseline. The desktop alone is ~0.3–0.5 GiB.
- Sample the host tree's dedicated **and shared** GPU memory with
  `tools/bench/_bench_common.GpuMemPeak`.
- **A CUDA timing is valid only when shared usage is near zero.** `_bench_common.SPILL_MIB = 512`
  MiB is the spill threshold; above it the solve is PCIe paging, not GPU speed. Cite:
  `AGENTS.md` GPU hygiene rule 8 and `TOOLCHAIN.md` M2 (WDDM shared-memory fallback).
- Record peak VRAM, baseline, dedicated/shared peaks and `spilled` next to every timing.
- One CUDA solve at a time; respect lane host dirs and live lane locks. No host cleanup, process
  kill, provisioning or queue edit while the night queue is live.

## 9. Two study lanes (measured expectations)

Measured caps in force (quarter domain): **screen 5,000 dofs / verify 7,000 / final 8,900**
(`TOOLCHAIN.md` M3). Full-domain verify/final are not available on this 8 GB card.

Measured screen-lane expectation (`TOOLCHAIN.md` M3, quarter mesh, 73 angles, 512-point balloon,
12 frequencies + balloon, solve only, loop per frequency):

| Lane | dofs | measured per candidate | measured throughput |
|---|---|---|---|
| screen | ~2,369 | 5.04 s (12+balloon; assembly 3.85 s, solve 0.20 s) | **~700 candidates/hour** |
| screen | ~5,140 | 33.3 s for 12 single-frequency calls (2.3–3.0 s each) | **~110 candidates/hour** |
| verify | 7,000 | 7.5 s per frequency; 25 × 7.5 s ≈ 3 min per candidate | ≈20/hour by arithmetic from the measured 7.5 s; **not separately measured** |

These are solve-only warm numbers. They exclude meshing, metrics, persistence, verification,
training/analysis overhead, failures and cold starts — the A/B metric must include all of them.
The N1 night also showed the screen cannot rank its own finalists reliably (verify J worse in
95% of 104 pairs; within-run Spearman of screen top-5 vs verify often 0.1–0.3), which is why the
headline is **verified useful designs/hour**, not screens/hour.

## 10. Decision rule

Accept a performance change only when all hold:

1. Repeated benefit exceeds observed run-to-run variability (the 2026-10-23 beats rule:
   medians differ by more than both spreads, with >= 5 runs for a verdict).
2. Verified quality and shortlist recall are maintained against a common reference.
3. Zero failures attributable to the treatment; no spill in any accepted CUDA arm.
4. All costs are counted (failed/refused/cached/verification/training/analysis/startup).

Otherwise record **no gain** or **inconclusive**. Negative results are results.

## 11. Open items (not in this slice)

- **Production runner adapter**: implement the documented `b5-journal-v1` /
  `b5-owned-lane-v1` contracts before P1/P2 can run. Separate reviewed slice.
- **Fork arithmetic/memory change** (e.g. LU reuse across changed geometry/frequency): separate
  follow-up with exact owner, pinned commit, analytic + independent-backend + same-mesh response
  parity gates and memory gates per `docs/FORKS.md`; never edit installed `.venv` packages and
  never assume LU reuse without proof. Current pin `0850ef39b29d7c51f8fbb082184d3784d2ff8bef`
  already fuses multi-channel assembly with one LU per frequency for identical geometry/frequency.
- **Real measurement**: waits for explicit lane-owner authorisation. The harness is not a
  substitute.
- **Index maintenance**: parent integrator updates `docs/INDEX.md` / `docs/CODE_MAP.md` when
  committing this new doc/tool (no push from this slice).
