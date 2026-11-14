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
| Repo HEAD | `707078e` (`main`, pushed; docs-only commits on top of `0980b8c`) | `git log` |
| Installed beat pin | `0850ef39b29d7c51f8fbb082184d3784d2ff8bef` | `dist-info/direct_url.json` |
| Installed beat source | local clone `file:///C:/…/forks/hornlab-beat-bem`; same SHA as the GitHub pin (`ourfork` = `llevaachingada`); E4 swaps to a GitHub-URL install | `direct_url.json`, `git ls-remote` |
| Fork branch | `perf/skip-fused-identity-cache` @ **`38e5b1f`** tip, tree clean, both commits pushed to `ourfork` | fork `git status`, `git ls-remote` |
| Part-two commit | **`38e5b1f`** (+16/−3), pushed to `ourfork` | fork `git show`, `git ls-remote` |
| Interrupted run | `runs/20261113T193536Z-screen-81c964`, **live** (189/200 at review close; `stats.failures` = 28, all pre-solve) | `search.ndjson` count, runner pids |
| Resume job | night `resume_print_night_2026-11-14`, `kind: command`, `--budget 45`, timeout 9000 s — RUNNING | `runs/nights/resume_print_night_2026-11-14.yaml`, queue log |
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

### C2 — Solver upgrade, part two (DONE: fork commit `38e5b1f`, pushed to `ourfork`)

- **Edit (+16/−3):** move the two host dense identity assemblies after the fusion decision and skip them **only** when
  `fused_burton_miller_cuda`; leave `nothing` as the explicit never-read value. Also leave `identity_cache` as an empty
  `Dict{Int,Any}()` on that route (its only reader is the CPU quadrature-order lookup, `BeatEngineDriver.jl:1827`,
  inside `beat_backend == :cpu`). Every other backend is byte-identical.
- **Why safe (verified at source, not just asserted):** `fused_burton_miller_cuda` is assigned at `:1574`, before the
  guarded assembly at `:1586-1589`; the only consumer that would break is the CUDA cache build at `:1681`, itself
  inside `if !fused_burton_miller_cuda` (`:1680`); `metal_fused_identity_cache` (`:1729`) is inside the Metal branch;
  `selected_identity_*` alias `nothing` on fused CUDA and are dereferenced only on CPU (`:2016`, `:2025`), Metal, and
  the non-fused `else` (`:2056`).
- **Evidence:** the Julia CPU suite was re-run independently by the integrator after the change: **exit 0**, 3830 pass
  / 0 fail / 4 broken (the four CUDA testsets skip because CUDA is not a dependency of the CPU project), matching the
  parent commit. `validate_analytic_exterior.jl` -> `ANALYTIC_EXTERIOR_VALIDATION_OK`, controls still failing as
  required. No GPU used.
  **SR-correction (2026-11-13):** this result exists only as prose attestation (commit messages, CONTINUITY) — no raw
  log is archived anywhere. Re-running both suites on the fork tip and archiving the raw terminal output under
  `docs/evidence/` is a REQUIRED pre-adoption step (E1; hard rule 6).
- **Gating:** installed as the **same new SHA** as C1 (fork history `0850ef3` -> `9ec86b0` -> **`38e5b1f`**), not
  measured as a separate pin level.
- **Residual risk:** `identity_cache` is empty on fused CUDA, so a future reader there fails loudly (KeyError) instead
  of silently receiving `nothing`. Recorded deliberately.

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
  (`beat.py:785-803`) recycles the host every N frequency-call **groups within one candidate** — with batch 12 there are
  4× fewer groups, so it recycles less often. Prefer the batch-4 fallback (R2) over a restart bound.

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
| E1 | C2 commit **DONE** (`38e5b1f`). Remaining: run the Julia CPU suite + `validate_analytic_exterior.jl` on the fork tip and **archive the raw terminal output** under `docs/evidence/` | integrator | archived raw logs (rule 6) | 0 fail; counts consistent with the prose attestation; analytic OK, controls still failing as required |
| E2 | C1+C2 packaged as one install SHA **`38e5b1f`** — DONE (committed and pushed to `ourfork`); the install itself is the E4 swap | integrator | fork commit, `git ls-remote` | `direct_url.json` matches at E4 |
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

1. Whole-candidate wall from the run's `stats` block in `run.json` (`mean_seconds_per_candidate`, per-row `total`;
   `cma.py:603-614`) (**primary**). The night `SUMMARY.md` records whole-job wall incl. hygiene — context only, never a
   decision source.
2. Mean seconds/candidate and candidates/hour as reported.
3. Peak dedicated VRAM (night runner) and peak shared (C4 watcher).
4. Frequency count and DOF per arm (so a hidden mesh difference cannot hide in a timing win).
5. Parity: `hornlab-search compare base_b1_<D> new_b1_<D>` — bar 0.039 dB / 1° (provenance: the CP-7f solver-disagreement
   noise floor, codified for fork A/B in `docs/FORKS.md:49-51`). `compare` is **report-only** (`cli.py:1305-1307`):
   compute the bar from the emitted max/mean |diff| — a passing exit code is NOT a parity pass. Record the max diffs;
   0.0 on all fields is the expected diagnostic for an untouched-kernel change.

### Statistics and confounders

- **SR-correction (2026-11-13):** the previously claimed "≤ 5 % observed replicate spread" is **not in the G2 evidence** —
  G2's own 4,168-DOF row shows ~11 % spread in s/freq (2.89/3.20/2.93) and ~18 % in peak VRAM
  (`docs/evidence/G2_FORK_AB_2026-11-13.md:40`). Whole-candidate arms average many frequencies, so noise should be lower
  than solver-only, but it is unmeasured. **One rep per arm stands only with the hardened repeat rule:** if a decision
  ratio lands in **[0.80, 0.92]**, re-run BOTH arms of that pair with **fresh** `cache_dir`/`dataset_dir` roots (H1 pairs
  need the pin swapped back to `0850ef39` and forward again); decide on the median of the three per-arm walls; a median
  ratio above 0.85 **rejects** — a gray pass never adopts.
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
- **Baseline gate:** verify `nvidia-smi` shows near-idle (≤ ~0.7 GB) before every measured arm; a post-hygiene failure is
  note-only in the runner (`run_campaign_night.py:836`, `:843`), so the recorded baseline is the tripwire.
- **Env-only knobs:** `HORNLAB_FREQ_BATCH_SIZE` is invisible in `config_sha`/`run.json` until C3 lands (`rundir.py:40-42`
  hashes `cfg.raw`). Archive the night YAML beside each arm's run dir so the batch value is on record.
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

**ANSWERED (2026-11-13, E-step executed):** after fetching `jamescollinharky:hornlab-search/osse-midports`,
`git merge-base --is-ancestor d740c28 55da4f46` → exit **1** — the pin **predates** the upstream FREEFORM
density/cost fix. Consequence: a post-beta mesher bump would change FREEFORM meshes (and via A1 invalidate every
mesh hash + strict resumes). Per the standing owner policy (`docs/ISSUES.md:1167`) the pin stays for the beta; the
bump candidate inherits this program's verification ladder. Zero GPU used; pin object now present locally from the
fetch. The question is closed — no action in this program.

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
| R10 | A5 model re-based on arithmetic | forbidden: the throughput-program rule (`docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md:67`, packet §5 rule 7) requires a measured re-base; the frozen plan's rule 7 (tolerance-loosening) is unrelated |

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
4. C1 and C2 ship as one installed SHA (**`38e5b1f`**) over two commits (`9ec86b0`, `38e5b1f`). Is that the right
   packaging, and is the bisect pair sufficient for attribution if the bundle ever looks slow?
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
- C2 is committed as `38e5b1f` (on top of `9ec86b0`); the CPU suite was re-run independently by the integrator after
  the change: exit 0, counts unchanged (3830 / 0 / 4).

---

## 14. Senior review verdict (2026-11-13, appended)

**Verdict: ADOPT the plan with the corrections below.** All four evidence domains were independently verified against
ground truth (repo/run state, `hornlab_search` code, fork/Julia dataflow, evidence-doc provenance). The core holds:

- **C2 guard provably complete.** The full consumer dataflow pass (every read of `cuda_solve_identity_cache`, the two
  host identity matrices, `identity_cache`, `selected_identity_*`, `metal_fused_identity_cache`) finds every consumer
  behind `!fused_burton_miller_cuda`, `beat_backend == :cpu`, `beat_backend in (:cpu,:metal)`, the Metal/ROCm branches,
  or the non-fused `else`. The fused CUDA assembler forms its own identity **on device** (`area/6` diagonal, `area/12`
  off-diagonal; `BeatEngineCudaBurtonMiller.jl:20-29`) and takes no host matrices, so the skipped host work cannot alter
  fused-CUDA output.
- **Batch composition is output-irrelevant on the fused-CUDA route.** Caches are keyed by quadrature order, not
  frequency (`BeatEngineDriver.jl:1804-1835`); per-frequency arithmetic is identical at any batch; batch changes only
  the number of host requests (`beat.py:784-795`). The one shared-state caveat (`dense_sweep_state`) is Metal-only, out
  of scope.
- **Resume arithmetic confirmed in code:** replayed rows are cached and skipped by `budget_count`
  (`cma.py:204-205`), `budget_exhausted` counts `n_new` (`cma.py:221-222`); validated live 153 → 155 with a 2-eval
  probe. The strict library-SHA guard is inert for this run (graded/legacy; `cma.py:936, 702-703`).
- All pins, round YAMLs, night-file semantics, `--budget 1` determinism, hygiene automation, and the 12,000-cap
  design configs verified as written.

**Binding corrections:**

1. §7 spread claim replaced with G2's actual numbers + hardened repeat rule (fresh roots; both arms; median-of-3;
   gray median → REJECT).
2. A5: the implemented model is `FUSED_CUDA_FACTOR 4.0 × 8N²` (`solve/feasibility.py:17-37`); "8N² + 187/212/256 MiB"
   is proposal-only (G2 :122-125). Re-base after measurement, and re-base the "provably stale" `20,237 → refuse` test
   by fix, not weakening (`tests/test_solve_feasibility.py:12-15`).
3. Julia suite evidence must be archived raw (rule 6) — E1.
4. `compare` is report-only; bars are computed (§7 metric 5).
5. The batch knob is env-only and invisible to `config_sha` until C3 lands; archive night YAMLs; C3 lands as
   `solve.freq_batch_size` with a contract-gap note appended to `NOTES_FOR_SENIOR.md` first (hard rule 3 procedure).
6. Repeats need fresh cache/dataset roots (I5 applies to repeats too).
7. Night summary cannot gate decisions; `run.json stats` is primary (§7 metric 1).
8. Baseline gate per arm — post-hygiene failures are note-only in the runner.
9. C2's line refs drifted with the commits — current refs: nothing-init `:1640`, C1 guard `:1680-1682`, non-fused
   `else` `:2049-2068`; all other cited constructs are exact.

**Decisions on §12 (binding for execution):**

1. One rep per arm **with the hardened repeat rule**. 2. Keep `--budget 1` (identical-design determinism + parity
requirement; conservative bias accepted as a recorded limitation). 3. `solve.*` — land C3 as dataclass field
following the `cuda_fused` precedent, with the rule-3 note first. 4. One install SHA over two commits; the bisect
pair suffices for attribution. 5. Keep 0.039 dB / 1° + record max diffs (expect 0.0); no bitwise gate (GPU reduction
nondeterminism would make it flaky). 6. No non-fused control (CPU suite + dataflow table + byte-identical non-fused
paths + MEH paused). 7. The three calibrated ceiling points stand; one exploratory point above 4.09 mm only if 4.09
fits. 8. Ceiling stays after Round B (arms' configs are fixed; wall-time adoption unaffected by later cap changes).
9. Refit `8N² + intercept` from the six measured points post-E6; adopt the shape only if it fits all points within
~10 %; refusal margin ≥ 30 % headroom below the measured max-fit. 10. Mesher policy stands (keep pin for beta, owner
2026-10-22, `docs/ISSUES.md:1167`; upstream now 60 commits ahead). 11. Leave `worker_restart_every` unset in the
arms; batch-4 fallback on spill. 12. Land batch 12 in the two print example configs post-E8; the env var stays as
override.

Execution authority passes to `docs/queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md`; where execution detail differs
from §6, the prompt wins.
