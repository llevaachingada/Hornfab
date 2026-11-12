# CPU second solve lane — hardening and alternatives pass (2026-10-28)

**Status: PROPOSAL ONLY — for senior review, hardening and sign-off.**
No code changed, no GPU/Julia/mesher run, no pytest suite, no solve. This pass is static reading
plus two read-only probes (CPU-engine readiness; a re-parse of the stored observer log). It
supersedes the first-pass recommendation in two places: the **lane identity mechanism** (H1) and the
**recommended topology** (shared `runs/`, separate cache/dataset — see §5, D1).

Reviewer shortcut: §1 verdict, §4 options, §6 hardening findings, §12 decisions needed. Everything
else is evidence and detail.

---

## 1. Plain-language verdict

The GPU is the expensive worker and it is idle a lot: in the measured search window it was solving
only **33%** of the wall clock, and across a full night the card was idle **43%** of the time
(`docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` §8). The machine's CPU was only ~17–19% busy in the
same window. So the CPU — already paid for — is sitting mostly still while the GPU waits.

The proposal is a **second, completely separate search on the CPU** while one search runs on the GPU.
Same software, slower engine, separate run folder, separate results. The two never share a search,
a result series, or a solver.

What that buys, in plain terms:

- **About 1.5–1.7x as much searching per night for small/medium screen models.** A night that
  currently produces ~1,000 evaluations would produce roughly 1,500–1,700. It is **not 2x**: the CPU
  engine is 1.8x slower per frequency at 2.4k dofs and 2.3x at 5.1k (`TOOLCHAIN.md` M4), and both
  lanes still pay the same modelling and bookkeeping cost.
- **At the top of the size range the CPU adds capability more than speed.** The CPU can solve models
  the 8 GB card cannot hold (above ~14k quarter dofs) and it is the only engine for
  `near_correction` and `solve_precision: double`. At 8.9k dofs it is only 1.3x slower.
- **It does not speed up a single solve.** A verify solve still takes the same time (slightly longer
  under load). It increases the *number of solves per hour*.

What it costs: about **0.5–1 engineering day** for the hygiene/lock change + tests + docs, one extra
long-running process, a second dataset folder until merged, and a permanent "lane" concept in the
cleanup code. The solver itself needs no change.

What makes it risky: **not the solver — the cleanup code.** Several routines are deliberately written
to kill *every* Julia solver on the machine (`solve/worker.py`, `search/hygiene.py`, `gpu-clean`).
Add a second lane without teaching them the difference and one lane silently kills the other. That is
the work.

The bigger theoretical win remains pipelining mesh preparation ahead of the GPU solve (the observer's
own note says `1 / gpu_solve_share` is the ceiling, up to ~3x). That is a much larger architectural
change; it should be judged after this one is measured. See §4 Option C and §7.

---

## 2. Scope and method (what was and was not done)

Read (static):

- solver/backends: `hornlab_search/solve/{base,beat,bempp,worker,cache}.py`
- library internals: `.venv/Lib/site-packages/hornlab_beat_bem/{worker,worker_client,worker_host,
  worker_registry,provision,runtime,sweep,capabilities}.py`
- search/CLI: `search/{evaluate,cma,campaign,gpulock,hygiene,rundir}.py`, `cli.py`
- storage: `dataset/store.py`, `mesh/build.py`
- config/types: `config.py`, `types.py`
- tools: `tools/run_campaign_night.py`, `tools/observe_run.py`, `tools/hf_sync.py`
- docs/evidence: `CLAUDE.md`, `AGENTS.md`, `TOOLCHAIN.md` M2/M3/M4, `docs/plan/00_ORCHESTRATOR.md`,
  `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md`, `docs/evidence/SOLVER_VERIFY_2026-10-22.md`,
  `docs/HIGH_FREQUENCY_OPTIONS.md`, `docs/CLOUD_GPU_REPORT.md`

Read-only probes (no solver/GPU):

1. `hornlab_beat_bem.provision.backend_ready("cpu")` + `package_fingerprint(...)` + stored
   `state-cpu.json` / `state-cuda.json` under `%LOCALAPPDATA%\hornlab-beat\runtime`.
2. Re-parsed `runs/nights/v4_overnight_2026-10-27/observe.ndjson` (3,895 samples) for whole-machine
   CPU and `julia.exe` usage by phase.

Not done, deliberately: no `doctor`, no `selftest`, no solve, no mesher, no pytest, no provisioning,
no code edits, no color/pixel work.

---

## 3. Evidence (measured, with anchors)

| # | Claim | Anchor |
|---|---|---|
| E1 | The pipeline was designed for this: one candidate end-to-end is a pure function, and the plan says a second accelerator is "a one-line change" | `search/evaluate.py:694`; `docs/plan/00_ORCHESTRATOR.md:80` |
| E2 | Three interchangeable engines already exist; `--backend beat_cpu` is a CLI option | `solve/base.py:34`, `:352`; `cli.py:1290` |
| E3 | CPU and GPU solver hosts are different processes by construction (different Julia project, thread count, fingerprint) | `.venv/.../hornlab_beat_bem/worker.py:446`; `worker_registry.py:166`; `provision.py:832` |
| E4 | The backend name is already in the solve hash, so the on-disk cache is already backend-separated | `types.py:89-101`; `solve/cache.py:46` |
| E5 | CPU is ~1.8x slower/frequency at 2,369 dofs, ~2.3x at 5,140, ~1.3x at 8,941; CPU has no VRAM ceiling | `TOOLCHAIN.md` M4, lines 123–144 |
| E6 | Search window: 33% `gpu_solve`, 39% `between_evals`, 24% `refusal_or_mesh`; GPU utilisation median 24%; full night 43% idle | `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` §8, lines 236–258 |
| E7 | Whole-machine CPU median 16.7% (solve), 19.2% (between evals), 16.0% (mesh) — p90 24–29%; the GPU host itself uses ~2 cores | this pass, re-parse of `runs/nights/v4_overnight_2026-10-27/observe.ndjson` |
| E8 | The project's recorded cross-solver reference is **beat_cuda vs bempp_cpu 0.039 dB** — different solver, same answer. A **beat_cpu vs beat_cuda** dB A/B is **not recorded** in the docs; Phase 2 must measure it before lanes are compared. Records already carry `backend` | `docs/evidence/SOLVER_VERIFY_2026-10-22.md`; `TOOLCHAIN.md` M4 (timings only) |
| E9 | CPU and CUDA are both usable on this host in principle; CPU is **currently unprovisioned** (fingerprint drift) | read-only probe: `backend_ready("cpu") == False`; installed `4ef2da0d…` vs recorded `a19e67a0…` |
| E10 | The dataset store is explicitly single-writer per root | `dataset/store.py:24-35` |
| E11 | The mesh cache copy into the shared entry is not atomic | `mesh/build.py:204-208` |
| E12 | Baseline throughput was 157.8 valid evals/hour on the smoke night | `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` §1 |

**Projection arithmetic** [estimate, not measured]. At 2.4k dofs a screen candidate on the CPU is
~1.8x the GPU's solve time and pays the same ~15 s of modelling/bookkeeping: roughly 33 s vs 23 s per
valid candidate → the CPU lane runs at ~0.7x the GPU lane → **157.8 + ~110 ≈ 268/hour, i.e. ~1.7x**.
At 5.1k the solve ratio is 2.3x → **~1.4–1.55x**. At 8.9k → **~1.2–1.4x, plus capability beyond the
VRAM ceiling**. These are projections built from measured ratios; §10 says how to replace them with
measurement.

---

## 4. The options, in plain language

### Option A — Two workers, two desks, stored separately

The CPU lane gets its own `runs_cpu/`, `cache_cpu/`, and `dataset_cpu/` folders. Nothing is shared
except the machine.

- **What changes:** lane-scoped cleanup + skip the GPU lock for the CPU engine + a thread cap.
- **Plain speedup:** the same **~1.5–1.7x** as B (the folders do not change speed).
- **Cost:** lowest; ~0.5–1 day.
- **Pros:** no shared state at all; the per-folder lock means no lock conflict by construction; zero
  risk to the existing dataset or mesh cache.
- **Cons:** two places to look; the GUI/night status needs the second folder in a later step; no
  mesh reuse between lanes.

### Option B — One shared runs shelf, separate working drawers

Both lanes write their run folders into the existing `runs/` (run ids are unique), so everything
appears in one place and the GUI/night status work unchanged. The mesh/solve cache and the dataset
stay **separate** for now.

- **What changes:** the same lane-scoped cleanup + lock skip, plus the lane marker. **No atomic
  mesh-cache change is needed** because the two lanes do disjoint cells, so the mesh cache is not
  shared. (Sharing the mesh cache too — "B-full" — would require the atomic copy at
  `mesh/build.py:204-208`; not worth it yet.)
- **Plain speedup:** **~1.5–1.7x**, same as A. Sharing a shelf adds convenience, not speed.
- **Cost:** the same as A (maybe +0.5 day for the lane marker/status handling).
- **Pros:** one place to look; operator sees both lanes; no new run-discovery work; still no dataset
  or mesh-cache race.
- **Cons:** slightly more coordination than A (the CPU lane must not take the GPU lock, and
  `gpu-clean`/the night runner must respect the lane marker).

### Option C — One worker, but prepare tomorrow's model while today's is solving

Keep one search and one solver, but build the next candidate's mesh while the GPU solves the current
one. This attacks the 39% "between evaluations" and part of the 24% mesh/refusal time directly.

- **What changes:** `evaluate()` splits into "prepare" and "solve" halves with a queue; meshing moves
  to a separate process (the meshing library is not safe to run concurrently in one process); plus
  failure propagation, deterministic ordering, cache-write ordering, and resume semantics.
- **Plain speedup:** the theoretical ceiling is **up to ~3x** (the GPU is busy only a third of the
  time), but a realistic first version is **~1.3–1.8x** [estimate]; the rest needs much more plumbing.
- **Cost:** several days, touching the most load-bearing file (`search/evaluate.py`) and the mesher
  boundary.
- **Pros:** highest ceiling; helps even with only one search to run; does not need the CPU engine.
- **Cons:** much higher risk of silent ordering/units/geometry bugs — exactly the project's "three
  silent killers" class. No new capability.
- **Verdict:** the follow-on project after A/B is measured, not the first step.

### Side-by-side

| | A: separate folders | B: shared runs, separate cache/dataset | C: in-run pipeline |
|---|---|---|---|
| Plain speedup [est] | ~1.5–1.7x small, ~1.3–1.5x medium | same as A | ~1.3–1.8x realistic, up to ~3x theoretical |
| Engineering | ~0.5–1 day | ~0.5–1.5 days | ~3–5+ days |
| New shared state | none | runs/ only | evaluate/mesh internals |
| Risk to existing data | none | very low | moderate/high |
| Adds CPU-only capability (>14k, double, near) | yes | yes | no |
| Operator experience | two folders | one folder | one folder |
| Recommendation | fallback | **target** | later, measured separately |

---

## 5. Decision (what this pass recommends)

**Target Option B (shared `runs/`, separate `cache_cpu/` + `dataset_cpu/`).** It is the same
engineering as A, keeps one place to look, and the two things that actually need isolation (cache
writes, dataset writes) stay isolated. A remains the zero-shared-state fallback if the senior prefers
it. C is a separate project.

**Lane rules**

- D1: exactly **one CUDA solve at a time**. The CPU lane uses zero VRAM, so it does not violate the
  GPU rule; the docs must say that explicitly (§9).
- D2: the CPU lane runs a **second independent screen search** on disjoint catalogue cells or seeds
  (owner choice). Never mix backends inside one run's J series.
- D3: measurement/checkpoint/benchmark runs stay **exclusive** (no CPU lane), so VRAM/timing numbers
  are not contaminated.
- D4: an unidentifiable solver host is **never killed**. Safety over tidiness.
- D5: the CPU lane must not take the GPU lock, and the GPU lane must not kill CPU hosts.
- D6: the CPU lane caps its Julia threads (~8–10) so meshing keeps a core.

---

## 6. Hardening findings (new or sharpened in this pass)

**H1 (new, improves the design).** The cleanest lane identity is the **worker registry directory**,
not parsing the host's key file. `worker_client._launch` always passes `--dir <registry>` in the host
command line (`.venv/.../hornlab_beat_bem/worker_client.py:425-437`), and the registry directory is
set by `HORNLAB_BEAT_WORKER_DIR` (`worker_registry.py:64`). So: give the CPU lane a dedicated
`HORNLAB_BEAT_WORKER_DIR`, and teach `solve/worker.py` to match hosts by their `--dir` argument.
The GPU lane keeps the default registry. Orphaned `julialauncher` processes (the existing fallback at
`solve/worker.py:207-214`) have no `--dir`; classify them by project token, and if unknown, do not
kill. This is simpler and more reliable than reading `<key>.key.json`.

**H2 (new, concrete blocker).** `--backend beat_cpu` on a config carrying `solve.cuda_fused: true`
**fails at backend construction**, because the CLI override happens *after* config validation
(`cli.py:371-373`, `:668-669`), and `BeatBackend.__init__` refuses `cuda_fused` on a non-CUDA device
(`solve/beat.py:395-401`). Campaign cells are generated with `cuda_fused: true`
(`docs/SOLVE_CAMPAIGN_PLAN_2026-10-26.md` §0.9). Fix: either drop `cuda_fused` for non-CUDA backends
in `cli._backend` and `solve_spec`, or re-validate after the override. The CPU engine's exterior solve
is always Burton-Miller and its default assembly is already the fused path (`capabilities.py`;
`docs/NEXT_DEV_PRIORITIES.md` P1 quotes the driver condition `beat_backend in (:cpu, :metal)`), with
the near-correction exception. `cuda_fused` is a **CUDA-only opt-in**, so dropping it for the CPU lane
is semantically correct, not a silent downgrade.

**H3 (confirmed).** `campaign` cannot pick a backend per job: `_build_search_argv` reads the backend
only from the config (`search/campaign.py:424-439`), and `_after_job_hygiene` calls
`hygiene.clear_julia()`, which kills **every** project Julia (`campaign.py:411-419`,
`search/hygiene.py:117-144`). A campaign-based CPU lane next to a GPU lane is therefore unsafe until
both are fixed.

**H4 (confirmed).** `gpu-clean` and `tools/run_campaign_night.py` kill Julia by project keyword, not
by lane. The night runner invokes `gpu-clean` per job (`tools/run_campaign_night.py:~431`). A live
CPU lane must be protected by a marker (D5) or the runner must never call `gpu-clean` mid-night.

**H5 (measured read-only).** `beat_cpu` is **unprovisioned on this install right now**:
`backend_ready("cpu") == False`; installed project fingerprint `4ef2da0d…` ≠ recorded `a19e67a0…`
(`state-cpu.json`, 2026-10-25). The same happens after any pinned-solver change. Add a `doctor` check
and re-provision before the first CPU lane.

**H6 (sharpened).** Sharing `runs/` is safe: `new_run_dir` appends a UUID
(`search/rundir.py:28-32`), and the GPU lock lives at `<runs>/.gpu.lock` (`search/gpulock.py:85-88`).
Sharing the **mesh cache** is not safe as written (`mesh/build.py:204-208`), so keep it separate /
atomic. The dataset must stay separate (`dataset/store.py:24-35`).

**H7 (confirmed).** `SolveSpec.backend` is in the hash, so the solve cache is already backend-safe;
no cache work is needed for correctness.

**H8 (new).** `beat_cpu` makes **one multi-frequency call** by default
(`solve/beat.py:406-408`), and `timeout_s` is only checked between calls (`beat.py:506-513`), so a
slow CPU candidate cannot be interrupted mid-call. Keep CPU-lane screens conservative; note it in the
lane runbook.

**H9 (new nuance).** The thread count is `os.cpu_count()` unless `SolveConfig.julia_threads` is set
(`lib worker.py:91-100`). Our adapter sets neither `warm_up` nor `SolveConfig` threads today
(`solve/beat.py:431`, `:470-493`). If a new knob is passed to only one of them, the worker key
differs and **a second host appears** — a silent memory/VRAM bug. One test must pin both.

**H10 (new).** `BeatBackend.__init__` sets `HORNLAB_BEAT_FUSED_BM_CUDA` process-wide
(`solve/beat.py:410-414`). Separate lane processes isolate this; do not try to run both backends in
one process.

**H11 (caveat).** The 33/39/24 phase split is from a ~6-minute search window on fresh cells. A
resumed night with warm mesh caches will have a lower "between evals" share, so the gain estimate
must be re-measured on the actual lane schedule (§10).

**H12 (minor).** `worker.note_solve_seconds` warns when the host pid changes between solve 1 and 2
(`solve/worker.py:329-352`). With lane-scoped discovery it should compare the lane's own hosts, or it
will produce noisy false warnings.

---

## 7. Alternatives considered and rejected

| Alternative | Why rejected / when it would win |
|---|---|
| **A1. Two GPU lanes / time-slicing one card** | One 8 GB card; the operator is 0.5–4.6 GB and assembly is memory-pressured above ~5k dofs (`TOOLCHAIN.md` M2). Two GPU jobs would contend and OOM, not add throughput. |
| **A2. Split one candidate's frequency bands across GPU and CPU** | `stack_responses` refuses mixed backends (`solve/base.py:175-177`), and a seam between two solvers would carry a step of the same order as the recorded 0.039 dB cross-solver difference; ripple/flatness would see it. Not acceptable. |
| **A3. Parallelise the CMA population on the GPU** | One GPU; the candidates still serialise on it, and it does not fill the mesh/bookkeeping idle. |
| **A4. Use `bempp_cpu` as the second lane** | It is the independent cross-check, not a throughput engine: 20–140 s per solve vs ~1.5 s for `beat_cpu` (`TOOLCHAIN.md` M4; `docs/evidence/SOLVER_VERIFY_2026-10-22.md`). |
| **A5. Background mesh prefetch (separate process)** | A viable **complement**, not a replacement: it hides some of the 39% "between evals" without a second search, but the CPU lane already uses that idle for real solves and adds capability. Estimated ~10–30% alone [est]. |
| **A6. Full in-run pipeline (Option C)** | Higher ceiling, 3–5x the engineering and much higher silent-bug risk. Judge after A/B is measured. |
| **A7. Reduce the CPU-side overhead instead (mesh/cache/grid)** | Orthogonal and worth measuring anyway; it does not add CPU-only capability. Should be instrumented in the same pass. |
| **A8. CPU lane for verify/final instead of a second screen** | A good **scheduling** choice late in a night (CPU is only 1.3x slower at 8.9k and can exceed the VRAM ceiling), but the owner chose a second screen; keep it as a Phase-3 scheduling option. |
| **A9. Cloud GPU pod** | Orthogonal; costs money. Documented in `docs/CLOUD_GPU_REPORT.md`. |
| **A10. A second physical machine** | Not available; the point is to use the idle half of this one. |

**Could there be a better way?** For *throughput per engineering hour* on this machine, no — the CPU
lane is the best ratio. For *ceiling*, the mesh/solve pipeline is better but is a separate project.
The honest ranking is: CPU lane (do now, measure) → mesh prefetch (cheap complement) → full pipeline
(only if the measured ceiling justifies it).

---

## 8. Implementation plan (not executed)

### Phase 0 — readiness (no product code)
1. Re-provision the CPU engine: `python -m hornlab_beat_bem.provision --backend cpu` (GPU idle; a few
   minutes; no VRAM). Expect to redo it after every pinned-solver change.
2. Add a `doctor` row: CPU engine readiness + project fingerprint, so H5 is visible.
3. Define the lane schedule: which cells/seeds go to the CPU lane (disjoint work).

### Phase 1 — lane-scoped hygiene and lock
1. `solve/worker.py` — add a lane filter to host discovery/cleanup:
   - match hosts by the `--dir` argument (H1) against the lane's `HORNLAB_BEAT_WORKER_DIR`;
   - GPU lane manages accelerator hosts (including orphans); CPU lane manages only its own registry;
   - unknown host → never kill (D4);
   - apply to `beat_host_roots` (`:196`), `host_tree_pids` (`:218`), `clear_stale_hosts` (`:243`),
     `shutdown` (`:369`), `recover_after_failure` (`:416`), and the `note_solve_seconds` host check
     (`:329`).
2. `solve/beat.py` + `worker.start_beat_worker` — pass the lane/device through warm/stop/recover; add
   `solve.julia_threads` (default `"auto"` = today) passed to **both** `warm_up` and `SolveConfig`
   (H9). Keep it out of `SolveSpec.extra` so cache hashes do not change.
3. `cli.py` + `search/gpulock.py` — acquire the GPU lock only for `beat_cuda` (keep it for
   `selftest`/crosscheck); add a `.cpu.lane.lock` marker (reuse the pid-liveness helper) that
   `gpu-clean` and the night runner must respect.
4. `cli._backend` / `solve_spec` — resolve H2 (`cuda_fused` on a non-CUDA backend).
5. `search/campaign.py` — add a `--backend` passthrough and a no-clear/ lane-aware after-job hygiene
   (H3), or document that the CPU lane is launched as standalone `search` jobs.
6. Tests (offline, no solver):
   - fake process table with one CPU host and one CUDA host → each lane clears/kills only its own;
     unknown host untouched;
   - failure recovery in one lane leaves the other alive;
   - CPU backend does not acquire the GPU lock; `beat_cuda` still does;
   - thread knob reaches both `warm_up` and `SolveConfig` (one host, not two);
   - `cuda_fused` is dropped/refused correctly on `beat_cpu`.
7. Docs (same commit): `CLAUDE.md`/`AGENTS.md` rule wording, `hornlab-gpu-job` skill (+ `.claude`
   mirror), `TOOLCHAIN.md` (CPU readiness + lane numbers), `CONTINUITY.md`, `ISSUES.md`.

### Phase 2 — prove it (the measurement that replaces the projection)
Global-only, exclusive where stated:
1. **CPU-alone sanity:** one CPU screen run on a small config; confirm a sane response and record a
   **beat_cpu vs beat_cuda** dB A/B on the same mesh (no such number exists in the docs; the recorded
   CUDA-vs-bempp cross-check of 0.039 dB is the reference for "different solver, same answer").
   The open item "CPU-vs-CUDA qualification screen per pinned-library change" in `docs/ISSUES.md`
   already asks for this A/B. No heavy ladder.
2. **Dual-lane smoke:** GPU lane on cells A, CPU lane on disjoint cells B; both complete.
   Acceptance: no `worker_exit` in either log; peak VRAM equals the GPU-only baseline; two hosts
   visible (one `julia`, one `julia_cuda`); neither killed mid-run.
3. **Throughput:** per-lane valid evals/hour vs solo baselines, at one small and one ~5k-dof config.
4. Write `docs/evidence/CPU_LANE_<date>.md` with raw logs and the numbers; update the projection in
   this doc with measured values (or record that the projection was wrong).

### Phase 3 — only if Phase 2 pays
Dual-lane night runner; shared mesh cache with atomic writes; dataset merge tool; GUI lane marker;
then reconsider Option C (pipeline) and the mesh-prefetch complement.

---

## 9. Speed-up expectations, in plain terms

These are **estimates**, built from the measured CPU/GPU per-frequency ratios and the measured GPU
idle share. They are not a substitute for Phase 2.

| Workload | Option A / B (CPU lane) | Option C (pipeline) |
|---|---|---|
| Small screen, ~2.4k dofs | **~1.5–1.7x** more evaluations per night | ~1.3–1.5x realistic |
| Medium screen, ~5.1k dofs | **~1.4–1.55x** | ~1.3–1.8x |
| Large, ~8.9k dofs | **~1.2–1.4x** *plus* the ability to exceed the GPU's 14k-dof ceiling | ~1.2–1.5x |
| Single verify/final solve | no speed-up (slightly slower under load) | small speed-up if the mesh is prefetched |

**Why not 2x?** Three reasons, in plain words: (1) the CPU worker is 1.8–2.3x slower than the GPU
worker; (2) both workers still have to do the same non-solving work (building the model, scoring,
writing results), so adding a worker does not halve the work; (3) the machine still has only one GPU,
and some of its idle time is work the CPU lane must also do. A 1.5–1.7x night is a realistic,
valuable result; a "2x" claim would be dishonest.

**What "1.5x" feels like:** a night that now produces ~1,000 evaluations produces ~1,500; if the GPU
lane alone finishes a campaign in 10 hours, the two lanes finish the same amount of work in about
6–7 hours, or the same 10 hours covers ~50% more cells.

**Capability is separate from speed.** Above ~14k quarter dofs the GPU is unusable (`TOOLCHAIN.md`
M2), while the CPU is ~1 min/frequency. That is not a throughput multiple; it is access to results
the GPU cannot produce at all. Same for `near_correction` and `double`, which are CPU-only
(`config.py:82-94`; `solve/beat.py:74-87`).

---

## 10. Cost / benefit summary

**Benefits**
- +50–70% screening throughput on one machine [estimate], using otherwise-idle CPU.
- Zero VRAM cost; the GPU lane keeps its full 8 GB.
- Access to CPU-only work (>14k dofs, near correction, double precision).
- CPU results are bitwise reproducible; the CUDA path is not (`capabilities.py:682-689`).
- Reuses the existing pure-function seam; no change to the scientific pipeline or cache semantics.

**Costs**
- ~0.5–1 engineering day (Phase 1) + one night (Phase 2) + docs.
- One more long-running process, one more log, a second dataset folder until merged.
- A permanent "lane" concept in cleanup code and docs.
- Machine load: ~8–10 Julia threads + one meshing core; roughly 1–3 GB RAM at the top end; more
  heat/power; laptop throttling unmeasured.
- One-time CPU provisioning, repeated after every pinned-solver change.

**Net:** a real ~1.5x, cheap relative to the pipeline, and it unlocks capability the GPU lacks. It is
the right first move; the pipeline remains the larger, riskier project.

---

## 11. Risk register

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Cleanup kills the other lane's solver | Critical | lane-scoped hygiene (H1), unknown = never kill, explicit tests |
| R2 | Two writers corrupt the dataset | High | separate `--dataset-dir`; single-writer preserved |
| R3 | Shared mesh cache race | High if shared | separate cache now; atomic copy before sharing |
| R4 | CPU lane starves meshing | Medium | `solve.julia_threads` 8–10; measure |
| R5 | Mixed solver provenance in one result series | Medium | never mix backends in one run; records carry `backend`; measure the beat_cpu vs beat_cuda A/B in Phase 2 (0.039 dB is the CUDA-vs-bempp reference, not this pair) |
| R6 | `gpu-clean`/night runner wipes the CPU lane | High operationally | `.cpu.lane.lock` + runner rule |
| R7 | CPU readiness silently invalidated | Medium | `doctor` check + re-provision note |
| R8 | Measurements contaminated | Medium | keep checkpoint/benchmark runs exclusive |
| R9 | CPU multi-frequency call cannot be cancelled mid-call | Low | conservative screen sizes/timeouts; note in runbook |
| R10 | `cuda_fused` config + `--backend beat_cpu` fails | Medium | H2 fix + test |
| R11 | Thermal/power limits | Low/unknown | measure; cap threads |
| R12 | Two hosts appear from a thread-knob mismatch | Medium | H9 test (warm vs solve identical) |

---

## 12. Decisions needed from the senior

1. Accept **Option B** (shared `runs/`, separate cache/dataset) as the target, with A as fallback?
2. Accept the reading that "one GPU solve at a time" permits one CUDA solve + one CPU lane (D1), and
   amend `CLAUDE.md`/`AGENTS.md`/the GPU-job skill accordingly?
3. Approve the lane identity by registry directory (H1) and the "unknown → never kill" rule (D4)?
4. Approve `solve.julia_threads` as a config knob, kept out of the solve hash (H9)?
5. Approve a `.cpu.lane.lock` marker and the rule that `gpu-clean`/the night runner respect it (H4)?
6. Approve resolving H2 by dropping `cuda_fused` for non-CUDA backends (rather than re-validating
   after the override)?
7. Is a second dataset root acceptable for Phase 1–2, with a merge tool deferred to Phase 3?
8. Confirm the measurement gates in §8 Phase 2 and that no GPU work is scheduled until this is
   signed off.

---

## 13. What could invalidate this

- **The projection is not a measurement.** If meshing contention or thermal throttling is
  significant, the real gain could be ~1.2x rather than ~1.5x. Phase 2 exists to find out.
- **The phase split is a short window.** E11/H11: the 33/39/24 split came from ~6 minutes on fresh
  cells; a resumed night with warm mesh caches may show a different split.
- **CPU provisioning fragility.** H5: the CPU engine readiness is tied to the installed solver
  fingerprint. A fork install can silently invalidate it.
- **Host classification.** If the `--dir` argument is ever absent from a live host (a future library
  change), the fallback must stay conservative. Unknown hosts are never killed, so the failure mode is
  "stale host survives", not "wrong host dies".
- **Pinned-library change.** The per-frequency CPU/GPU ratios and worker-key internals are tied to
  the installed `hornlab_beat_bem` 0.2.0 / fork SHA. Re-check `TOOLCHAIN.md` after a pin change.

---

## 14. Reference index (file:line)

- `search/evaluate.py:694` — one candidate end to end (pure function seam).
- `docs/plan/00_ORCHESTRATOR.md:80` — "a second GPU is a one-line change" (the seam this uses).
- `solve/base.py:34`, `:352` — backend names and factory.
- `solve/beat.py:395-414` — `BeatBackend` (device, `cuda_fused`, env); `:428-436` warm/release;
  `:470-493` `SolveConfig`; `:516-537` worker-exit retry; `:568-580` failure recovery.
- `solve/worker.py:196` host roots; `:218` tree pids; `:243` `clear_stale_hosts`; `:297` `warm`;
  `:329` `note_solve_seconds`; `:369` `shutdown`; `:416` `recover_after_failure`.
- `search/gpulock.py:85-88`, `:134` — per-runs-root lock.
- `cli.py:357` `_dirs`; `:371-373` config load + backend override; `:381` `_backend`; `:455`, `:578`,
  `:624`, `:736` lock usage; `:1290` `--backend`.
- `config.py:70-99` `SolveSettings`; `:799-801` `cuda_fused` validation; `:957-997` `solve_spec`.
- `types.py:89-101` `SolveSpec.hash` (backend included).
- `solve/cache.py:46` cache key.
- `dataset/store.py:24-35` single-writer statement; `:276` `append`.
- `mesh/build.py:192-208` cache load/copy (non-atomic); `:278`, `:319-333` mesh cache.
- `search/campaign.py:411-419` after-job hygiene; `:424-439` search argv (no `--backend`).
- `search/hygiene.py:117-144` `clear_julia` (kills all project Julia).
- `search/rundir.py:28-32` unique run dir.
- `tools/run_campaign_night.py:~431` `gpu-clean` per job.
- `.venv/Lib/site-packages/hornlab_beat_bem/worker.py:91-100` thread resolution; `:103-127` env;
  `:446-486` worker key/cache.
- `.venv/.../worker_client.py:425-437` host launch (`--dir` argument); `worker_host.py:508-523` host
  `--key`/`--dir`.
- `.venv/.../worker_registry.py:64`, `:166-210` registry dir / worker key.
- `.venv/.../provision.py:219-242` `read_state`; `:832-854` `backend_ready`.
- `.venv/.../runtime.py:321-370` `_cpu_backend_status`.
- `.venv/.../capabilities.py:682-689` CPU bitwise-reproducible note.
- `TOOLCHAIN.md` M2 line 94; M3 lines 99–121; M4 lines 123–144.
- `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` §8 lines 236–258 (phase split).
- `docs/evidence/SOLVER_VERIFY_2026-10-22.md` — beat_cuda vs bempp_cpu 0.039 dB.
- `runs/nights/v4_overnight_2026-10-27/observe.ndjson` — re-parsed CPU/julia phase medians (E7).

---

## 15. What was deliberately not done

No GPU job, no Julia host, no mesher, no solve, no pytest, no provisioning, no code edits, no color or
pixel work. The only live checks were `backend_ready("cpu")`, `package_fingerprint`, reading the two
stored provision-state JSONs, and a read-only re-parse of an existing observer log. Nothing was
committed or pushed.
