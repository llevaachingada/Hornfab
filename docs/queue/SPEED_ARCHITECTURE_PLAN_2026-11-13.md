# Solver-speed adoption — senior implementation & architecture plan (2026-11-13)

**Audience:** a senior/reviewing agent, then the integrator who executes it.
**Status:** design for review. **Nothing in §6 has been executed except where explicitly marked DONE / RUNNING.**
**Supersedes:** `docs/queue/SPEED_COMBINED_2026-11-13.md` (superseded) and deepens
`docs/queue/SPEED_PROGRAM_2026-11-13.md` (operational summary; keep as the one-pager).
**Owner constraint (binding):** nothing may reduce frequency, angular or mesh resolution, accuracy or coverage on
numbers that count as results.

---

## 1. Executive summary

1. **Two solver changes, one batching change, one measurement wrapper, one question.** The solver changes are the same
   idea twice (GPU-side and host-side identity-matrix waste on the fused route). Batching is an existing, unused switch.
   The measurement wrapper exists because the night runner cannot see Windows shared-memory spill. The mesher is a
   question, not a change, and is out of scope.
2. **The ordering constraint is real but different from what was first written.** The interrupted run is *not* a strict
   run (`infeasible_penalty: graded`, `error_policy: legacy`), so the strict library-SHA guard is inert; the real
   arithmetic is that `--budget` on a resume counts **new** evaluations, so the run needs 45, not 200.
3. **A test-design flaw was found and fixed during this review:** every arm must have its own cold cache. With a shared
   cache, the second arm solving the same seed design is a cache hit and its wall time collapses.
4. **Adoption is gated on measured whole-candidate wall and output parity**, not on solver-only numbers, with
   pre-declared thresholds and a repeat-if-ambiguous rule.
5. **The largest open upside is the memory ceiling.** The 12,000 verify/final caps and the 20,237-DOF refusal were set
   on the memory-hungry solver; the measured 55–70 % reduction plausibly moves the ceiling 1.5–2×. That is worth more
   than any single micro-optimisation and is measured, not assumed.

---

## 2. Verified current state (ground truth at write time)

| Item | Value | How verified |
|---|---|---|
| Repo HEAD | `0980b8c` (`main`, pushed) | `git log` |
| Installed beat pin | `0850ef39b29d7c51f8fbb082184d3784d2ff8bef` | `dist-info/direct_url.json` |
| Fork branch | `perf/skip-fused-identity-cache` @ `9ec86b0` + **uncommitted part-two edit** | `git status` in fork |
| Part-two diff shape | `BeatEngineDriver.jl` +16/−3, under test | fork `git diff --stat` |
| Interrupted run | `runs/20261113T193536Z-screen-81c964`, **158/200** rows, resume job RUNNING | `search.ndjson` count, runner pids |
| Resume job | night `resume_print_night_2026-11-14`, budget **45**, timeout 9000 s | `runs/nights/queue_resume_print_2026-11-14.log` |
| GPU | busy with the resume (~2 GB), no other Julia host | `nvidia-smi`, process list |
| Mesher pin | `55da4f46…` installed from `jamescollinharky` fork (correct) | `direct_url.json` |
| Local mesher checkout | `b922e80`, 60 behind, pin object absent | `git` in fork |

**Cache provenance (A1) as it affects this plan:** `solve/cache.py:46-49` namespaces solve/mesh caches by
`{"hornlab_beat_bem","hornlab_bempp_bem","hornlab_mesher"}` only — `hornlab_search`/`hornlab_plots` are deliberately
excluded. Therefore repo commits do **not** invalidate solve caches, but a beat or mesher SHA change does, once.

---

## 3. Architecture — where each change sits

```
CLI  hornlab-search search
  └─ search/cma.py            CMA loop, budget/accounting, resume replay     ← C3 batching value plumbed here
      └─ search/evaluate.py   cache lookup, mesh build, solve, metrics
          └─ solve/beat.py    BeatBackend: one request per frequency today   ← C3 frequency grouping
              └─ solve/worker.py  persistent Julia host (default on), disk-staged request
                  └─ hornlab_beat_bem/worker_host
                      └─ julia/BeatEngineDriver.jl  solve_request_impl
                          ├─ host setup: mesh, spaces, quadrature,
                          │   TWO DENSE HOST IDENTITY MATRICES              ← C2 (patch two)
                          ├─ device caches (regular/field/singular/near)
                          ├─ per-frequency loop
                          │   ├─ fused CUDA assembly  O(N²)  (dominant cost)
                          │   ├─ device LU factor+solve  O(N³)
                          │   └─ field evaluation → host
                          └─ finally: releases, GC + cuda.reclaim()

Ops layer
  tools/run_campaign_night.py  night YAML → jobs, env per job, lane env, hygiene, logs, summary
  tools/night_queue/queue.ps1  sequential nights, cutoff, wait-for-pid; night files must live in runs/nights/
```

**Provenance chain:** `search/evaluate.py::collect_lib_shas()` records five SHAs in every `run.json` and dataset row
(the four HornLab packages from `direct_url.json`, plus this repo's `git rev-parse HEAD`). Any solver/mesher change is
therefore visible in the data, and A1's cache namespace keys on the three physics SHAs.

---

## 4. Change inventory

### C1 — Solver upgrade, part one (DONE, measured, not adopted)

- **Fork commit** `9ec86b0`: wrap `cuda_solve_identity_cache = build_cuda_burton_miller_identity_cache(...)` in
  `if !fused_burton_miller_cuda` (`BeatEngineDriver.jl:1667-1669`).
- **Why safe:** the only reader is `pressure_for_drives` (`:757-758`), whose sole call site is the non-fused `else`
  (`:2033-2051`); the `nothing` init (`:1632`) makes the `finally` release guard (`:2253`) correct.
- **Measured (G2):** −55/−66/−70 % peak VRAM, −20/−30 % per-frequency wall at 4,168/8,021/11,938 DOF; analytic selftest
  numerically identical.
- **Known gap:** fused-path output parity is **not** measured (§7 H1 closes it). Shared memory not recorded (§8).

### C2 — Solver upgrade, part two (RUNNING; uncommitted in the fork)

- **Edit:** skip the two host dense identity assemblies (`BeatEngineDriver.jl:1534-1535`) and their immediate
  consumers **only** when `beat_backend == :cuda && fused_burton_miller_cuda`. Every other backend unchanged.
- **Why safe:** the fused CUDA assembler writes the analytic identity directly (`BeatEngineCore.jl:443-460`); the host
  matrices are consumed only by CPU/Metal (`:1931-1932`, `:2012`) and non-fused CUDA (`:758`).
- **Blast radius:** `identity_cache` dict (`:1636`), `metal_fused_identity_cache` (`:1716`),
  `selected_identity_p1_p1/dp0` (`:1809-1821`). The implementer must prove none is reachable on fused CUDA or stop.
- **Gating:** folded into the **same new installed SHA** as C1; not measured as a separate pin level.
- **Evidence required before adoption:** Julia CPU suite (parent: 3830 pass / 0 fail / 4 broken) and the analytic
  exterior validation, both green.

### C3 — Batching becomes a real setting (NOT written)

- **Today:** `HORNLAB_FREQ_BATCH_SIZE` is read in `solve/beat.py:626-661`; `search/cma.py:376-384` never passes it, so
  production is `per_frequency_calls=True` (one request per frequency). N1: batch 12 vs 1 = 1.9–4.7× solver-only.
- **Change:**
  1. `hornlab_search/config.py` — add `SolveSettings.freq_batch_size: int | None = None`; validate `None` or `>= 1`.
  2. `search/cma.py::_prepare` — pass it to the backend constructor alongside `cuda_fused`/`julia_threads`.
  3. Keep the env var as an override for trials; the config value is what appears in `config_sha`.
  4. Docs/example configs: set `solve.freq_batch_size: 12` only in the CUDA example configs after adoption.
- **Why safe:** `frequency_groups` concatenates back to exactly the input list (`beat.py:599-612`); no frequency is
  dropped and the Julia loop is unchanged.
- **Provenance note:** adding a default does not change existing config hashes (they hash `cfg.raw`, not defaults).
- **Risk:** the CUDA pool stays alive across frequencies inside a request, so peak VRAM may rise; `worker_restart_every`
  (`beat.py:789-803`) bounds the host's pool if needed.

### C4 — Shared-memory measurement wrapper (NOT written)

- **Why:** the night runner records dedicated VRAM only; `plan` G2/G1 require zero Windows shared spill.
  `tools/bench/_bench_common.py` already has `GpuMemPeak` (`dedicated_peak_mib`, `shared_peak_mib`, `spilled()` with
  `SPILL_MIB = 512`).
- **Change:** `tools/bench/run_with_memwatch.py <out.json> -- <argv…>` — spawn the child, poll `GpuMemPeak` for the
  child tree, write `{dedicated_peak_mib, shared_peak_mib, spill_mib, wall_s, exit}`; exit with the child's code.
- **Use:** wrap the batch-12 arms and the ceiling points. A non-zero spill above `SPILL_MIB` invalidates that arm.

### C5 — Mesher question (OUT OF SCOPE)

Decide only: does the pin predate upstream's FREEFORM density/cost fix? Three commands, zero GPU (§9). If it does and a
live typology is FREEFORM, that becomes its own program — a mesher bump invalidates every mesh hash, every solve cache,
the dataset `lib_sha` key and strict resumes.

### C6 — Test isolation (DONE in the night files)

Per-arm `cache_dir` + `dataset_dir` under `scratch/`, so every arm solves cold. Without it the second arm on the same
design is a cache hit and the measured "speedup" is an artefact.

---

## 5. Invariants (violating any of these invalidates a run)

1. **I1 Physics parity:** a solver change is adopted only with output parity inside 0.039 dB / 1° on **both** designs,
   measured on the fused path (not the analytic selftest, which never sets `cuda_fused`).
2. **I2 Provenance:** installs are non-editable by SHA; `pyproject.toml` and `TOOLCHAIN.md` name the same SHA that
   `direct_url.json` reports; no hand edits under `.venv`.
3. **I3 One GPU solve at a time.** No second lane, no concurrent night, `gpu-clean` before measurements.
4. **I4 No resolution/fidelity trades.** Quadrature order, rear-shell density, coarser `epw`, fewer angles/frequencies,
   FP32 Krylov, reduced-order sweeps, UI fidelity selector: all excluded.
5. **I5 Cache isolation per arm** (C6); never measure an arm against a warm cache.
6. **I6 Never `pip install` inside a night job; the swap is an integrator step** between blocks.
7. **I7 Never resume or extend a run after a solver/mesher SHA change** (mix-version provenance). Finish before swap.
8. **I8 Data is never deleted.** Old caches/run dirs stay; A1 keeps legacy entries byte-for-byte.

---

## 6. Execution sequence (E0–E9) with gates

| # | Step | Owner | Artifact/proof | Gate to next |
|---|---|---|---|---|
| E0 | Finish the interrupted run (RUNNING, 158/200, budget 45) | night queue | `search.ndjson` = 200, runner exit 0 | row count 200 and no solve failures |
| E1 | Review + commit C2 in the fork; run Julia CPU suite + analytic exterior | fixer + integrator | fork SHA, test lines | 0 fail; dataflow proof |
| E2 | Build the new installed SHA = C1+C2; record it | integrator | fork commit + push to `ourfork` | `git ls-remote` shows it |
| E3 | Round A (2 arms, cold caches) | night queue | `speed_round_a` summary + run dirs | both arms complete, shared recorded (C4 first) |
| E4 | Swap install + `provision --backend cpu`; verify SHA and patch markers | integrator | `direct_url.json`, grep markers, tests | exact SHA match |
| E5 | Round B (4 arms, cold caches) + shared watcher | night queue | `speed_round_b` summary | all arms complete, no spill |
| E6 | Ceiling sweep (3 points × 2 reps, fresh process) | integrator | `RESULT` lines ×6 | fits/does-not-fit recorded |
| E7 | Compare + decide against §7 bars | integrator | comparison table | bars met or rejected |
| E8 | Merge: pin lines, `freq_batch_size` key, A5 re-base, docs | integrator | one commit | tests green; docs updated |
| E9 | Relaunch production fresh (absorbs the old night's third job) | night queue | new run dirs | — |

**C2 must be committed before E3** so Round A measures "old solver" and Round B "new solver", not a moving tree.

---

## 7. Test design

### Hypotheses

- **H1 (upgrade):** at batch 1, the new solver reduces whole-candidate wall ≥ 15 % on both designs, with parity.
- **H2 (batching):** at the new solver, batch 12 reduces whole-candidate wall ≥ 15 % on both designs, no spill.
- **H3 (combination):** the combined arm is at least as fast as the best single arm on both designs.
- **H4 (ceiling):** at least the 15,878-DOF point fits with zero spill on the new solver (and record 20,152 / 23,850).

### Design and arms

Two real print cells per arm set: **D1** `p80x60__osse_ext_throat_700_v7` and **D2** `p80x60__ath_core_14in_700_v7`
(both fused, caps 12,000, 73 angles, balloon on, 350–8,000 Hz screen). `--budget 1` = seed candidate only, deterministic.

| Arm | Solver | Batch | Cache | Proves |
|---|---|---|---|---|
| base_b1_osse / base_b1_ath | old `0850ef39` | 1 | cold, per arm | baseline wall + VRAM |
| new_b1_osse / new_b1_ath | new SHA | 1 | cold | H1 + **fused parity** |
| new_b12_osse / new_b12_ath | new SHA | 12 | cold | H2 + H3 + spill |
| ceiling 5.03/4.46/4.09 mm × 2 | new | — | ceiling scratch | H4 |

**Dropped deliberately:** old-solver batch-12 arms (N1 covers batching on a solver that is being replaced); a third
measured level for C2; batch-4 unless batch 12 fails a bar; MEH/non-fused controls (paused / provably untouched).

### Metrics (per arm)

1. Whole-candidate wall from the run's `stats` block and the night summary (**primary**).
2. Mean seconds/candidate and candidates/hour as reported.
3. Peak dedicated VRAM (night runner) and peak shared (C4 watcher).
4. Frequency count and DOF per arm (so a hidden mesh difference cannot hide in a timing win).
5. Parity: `hornlab-search compare base_b1_<D> new_b1_<D>` — bar 0.039 dB / 1°.

### Statistics and confounders

- Observed replicate spread in G2 was ≤ 5 % at each point; a 15 % effect is ≈ 3× that noise, so **one rep per arm is
  defensible**, with a pre-declared **repeat-if-ambiguous** rule: if a decision ratio lands in **[0.80, 0.92]**, run one
  more rep of that pair and use the median; outside that band, decide on one.
- **Cold-start bias:** each `--budget 1` arm includes host warm-up and mesh build, which production amortises across
  candidates. This biases ratios **toward 1** (conservative for adoption). Recorded as a limitation, not corrected.
- **Order/thermal:** run arms in the order b1, b12 per design; if a ratio is ambiguous, the repeat is run in reverse
  order (b12 then b1) to expose drift.
- **Baseline drift:** report `peak − baseline`, not absolute peak; baselines vary with the desktop.
- **Cache state:** per-arm cold caches (C6) — the single most important control.

### Falsification

H1 fails if parity fails or wall ratio > 0.85 on either design. H2 fails if ratio > 0.85 or shared spill > 512 MiB.
H3 fails if the combined arm is slower than the better single arm on either design. H4 fails if the 15,878 point does
not fit; record the largest that does.

---

## 8. Measurement infrastructure

- **Per point:** `hornlab-search gpu-clean`, record baseline (`nvidia-smi`), then measure, then verify shutdown.
- **Ceiling points:** one solve per fresh process (`tools/measure_fused_ceiling.py`, M2 protocol), `--flag on`,
  `scratch/ceiling_cache`, 73 angles, 1 kHz. Calibrated quarter-DOF: **5.03 mm = 15,878**, **4.46 = 20,152**,
  **4.09 = 23,850**.
- **Shared memory:** C4 wrapper; `SPILL_MIB = 512` (`tools/bench/_bench_common.py:23`). A non-zero spill invalidates.
- **Run identity:** every arm's `run.json` carries the five `lib_shas`, so a mixed-version arm cannot be mistaken for a
  clean one.

---

## 9. Mesher check (zero GPU)

**Existing owner policy, already on record** (`docs/ISSUES.md:1166`, 2026-10-22): the upstream mesher is 57 commits past
our pin, the FREEFORM corner-topology fix `d740c28` is in that delta, and the decision was **keep the pin for the beta;
post-beta bump candidate with its own verification ladder**. This check is therefore informational, not a gate for this
program — it only tells us whether a post-beta bump would change meshes.

```powershell
git -C C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher fetch https://github.com/jamescollinharky/hornlab-waveguide-mesher.git hornlab-search/osse-midports
git -C C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher merge-base --is-ancestor d740c28 55da4f46
echo $LASTEXITCODE   # 0 = upstream FREEFORM cost fix already in the pin; question closed
```

Remotes differ: the checkout's `origin` is upstream `m3gnus` (contains `d740c28`); the pin lives on `jamescollinharky`.

---

## 10. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | C2 guard misses a fused-path consumer | implementer must produce the dataflow table and stop if any site is reachable; otherwise guard covers all |
| R2 | Batch 12 grows the pool and raises peak VRAM | per-arm peak recorded; spill > 512 MiB → batch 4, same night |
| R3 | Cold-start bias hides a real gain or fakes one | declared; ratios biased toward 1; repeat-if-ambiguous; run ids carry DOF |
| R4 | Pin swap invalidates caches | expected once; A1 namespaces; first post-merge run re-solves |
| R5 | The old night cannot be resumed after the swap | finish first (E0) — in progress |
| R6 | Concurrent agent session edits/runs on the same checkout | freeze: no other GPU/queue activity during E3–E6; verify process list before each block |
| R7 | Ceiling sweep finds a lower limit than hoped | a result, not a failure; caps stay, A5 re-based on measurement |
| R8 | Mesher question reopened | out of scope by design; its own program |
| R9 | Timeout too short for a cold 12k arm | 3600 s per arm; a timeout is recorded as a failed arm, not silently retried |
| R10 | A5 model re-based on arithmetic | forbidden: rule 7 requires the measured 20,152 point |

---

## 11. Rollback

- **Install:** `pip install --force-reinstall --no-deps "hornlab-beat-bem @ git+…@0850ef39…"` + `provision --backend cpu`.
- **Repo:** revert the single adoption commit (pin lines, config key, A5 constant, docs).
- **Data:** no rollback needed; A1 keeps old cache entries and old records keep their `lib_shas`.
- **Time to restore:** ~2 minutes.

---

## 12. Open questions for the reviewing agent

1. Is one rep per arm acceptable given the 15 % bar and the ≤ 5 % replicate spread, with the [0.80, 0.92] repeat rule —
   or should every arm be run twice regardless?
2. Is `--budget 1` the right probe? It measures a cold candidate including host warm-up and mesh build (conservative
   ratios). Alternative: budget 2 and time only the second candidate — worth the extra GPU time?
3. Is `solve.freq_batch_size` the right home for C3, or should it be a `search.*` key? (Proposal: solve, because it is a
   solver-call concern and rides in the solve spec.)
4. Should C1 and C2 ship as one installed SHA (proposed) or as two, with a bisect-ready pair of commits (they remain two
   commits in the fork either way)?
5. Is the 0.039 dB / 1° parity bar meaningful when the fused kernels are untouched? Should we additionally require
   bitwise-identical response `.npz` for the same design, and if so, is the current harness capable of it?
6. Is a non-fused control arm needed after all, to demonstrate the patches left the default path identical?
7. For H4, is 23,850 DOF the right top point, or should the sweep go higher (e.g. 4.0 mm ≈ 24k) to find the actual edge?
8. Should the ceiling sweep precede Round B, in case the 12,000 caps would be raised and the round re-run with bigger
   meshes? (Proposal: no — the round's designs are fixed by config, and caps do not change the arms.)
9. What is the correct A5 model shape: `8N² + constant` (proposed, constants 187/212/256 MiB observed) or a piecewise
   fit? And what is the safe refusal margin?
10. Is the 2026-10-22 owner policy still current — "keep the mesher pin for the beta; bump post-beta with its own
    verification ladder" (`docs/ISSUES.md:1166`)? If yes it removes the mesher from this program entirely.
11. Is `worker_restart_every` the right pool bound for batch 12, or should a batch-specific value be derived from the
    ceiling measurements?
12. Should the batch default land only in print configs, or in a shared profile (`examples/profiles/fused_cuda.yaml`)?

---

## 13. Execution checklist (preflight, per block)

```powershell
git status --porcelain                     # expect only known untracked scratch
git log --oneline -1                       # record the exact commit
(Get-Content .venv\Lib\site-packages\hornlab_beat_bem-*.dist-info\direct_url.json)  # SHA must match the pin
nvidia-smi --query-gpu=memory.used --format=csv,noheader
.venv\Scripts\hornlab-search.exe gpu-clean
Get-CimInstance Win32_Process -Filter "Name='julia.exe' OR Name='python.exe'"        # no stray solver/night
.venv\Scripts\python.exe tools\run_campaign_night.py --night runs\nights\<file>.yaml --dry-run
```

**Corrections log (verified during this review):**
- `--budget` on a resume counts **new** evaluations → 45, not 200.
- The interrupted run is **not** strict (`graded`/`legacy`), so the library-SHA resume guard is inert; the ordering
  advice stays as a general rule.
- Night files must be copied to `runs/nights/` before queuing.
- `kind: search` requires a `config:` key even with `resume:` → the resume job uses `kind: command`.
- Round A/B arms need **per-arm cold caches** (C6), otherwise the second arm is a cache hit.
- The G2 mechanism is `8(N²+N·E)`, not pool rounding (see `docs/evidence/G2_FORK_AB_2026-11-13.md`).
- The analytic selftest does **not** exercise the fused path.
