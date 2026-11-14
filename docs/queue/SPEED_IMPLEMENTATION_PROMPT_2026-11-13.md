# SPEED PROGRAM — IMPLEMENTATION PROMPT (rev B, senior-reviewed 2026-11-13)

**Hand this file verbatim to the executing integrator agent.** It replaces §6/§13 execution detail of
`docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md` (whose §14 verdict is binding); where the two differ, this prompt
wins. Every factual claim has been verified against source; the numbers below are ground truth, not proposals.

---

## 0. Who you are and what you own

You are the parent integrator. You alone perform git mutations (clone/fetch/commit/push), pin swaps (`pip install`
into `.venv`), and night queuing. You never write or edit `hornlab_beat_bem` source — the solver changes are already
committed in the fork; you install and verify them. You never reduce resolution, accuracy, or coverage (owner
constraint). One CUDA solve at a time; a CPU-backend search may run beside it per the two-lane rule.

Working checkout: `C:\Users\hunte\Hrns\hornlab-search` (canonical, `main`).
Fork checkout: `C:\Users\hunte\Hrns\forks\hornlab-beat-bem` (branch `perf/skip-fused-identity-cache`).
Interpreter: always `.venv\Scripts\python.exe`, never bare `python`.

## 1. Bindings (violating any invalidates the run)

1. **I1 Physics parity** — solver change adopts only with output parity ≤ 0.039 dB / 1° on **both** designs, computed
   from `hornlab-search compare` output (which is **report-only**; a passing exit code is not a pass).
2. **I2 Provenance** — installs are non-editable, by full 40-char SHA; `pyproject.toml` and `TOOLCHAIN.md` name the
   same SHA `direct_url.json` reports. Physics packages only; `hornlab_search` stays editable.
3. **I3** One GPU solve at a time; `gpu-clean` before measurements; no provisioning while measuring.
4. **I4** No resolution/fidelity trades of any kind (quadrature, angles, frequencies, epw, density, FP32, caps).
5. **I5** Cold caches per arm — **including repeats** (a repeat arm gets a *fresh* `cache_dir`/`dataset_dir`).
6. **I6** Never `pip install` inside a night job; the swap is your step between blocks.
7. **I7** No resume/extension of a run after a solver/mesher SHA change. (Tonight's resume is non-strict
   (graded/legacy) so its guard is inert — the policy still binds everything else.)
8. **I8** Data is never deleted; A1 namespaces caches by physics SHAs only (`solve/cache.py:46-49`), so repo commits
   never invalidate solve caches.
9. **Rule 6** — paste raw terminal bytes for every checkpoint; prose attestation is not evidence.
10. **Rule "blocked twice"** — same error twice: append a dated block to `NOTES_FOR_SENIOR.md` and stop.

## 2. Ground truth (verified 2026-11-13; re-check moving values at each block)

| Item | Value |
|---|---|
| Old solver pin | `hornlab-beat-bem @ git+https://github.com/llevaachingada/hornlab-beat-bem.git@0850ef39b29d7c51f8fbb082184d3784d2ff8bef` |
| New solver pin | same URL `@38e5b1f8ca840ebf6351c54611a08fedb1a0750f` (= C1 `9ec86b0` + C2 `38e5b1f`, both pushed to `ourfork`) |
| Install evidence | `.venv\Lib\site-packages\hornlab_beat_bem-*.dist-info\direct_url.json` → `commit_id` must equal the full SHA |
| C2 markers in installed tree | `hornlab_beat_bem\julia\BeatEngineDriver.jl`: `fused_burton_miller_cuda ? nothing`, exactly 2 hits (identity_p1_p1, identity_p1_dp0) |
| CPU provision full command | `.venv\Scripts\python.exe -m hornlab_beat_bem.provision --backend cpu` (GPU idle; a few minutes) |
| Mesher pin | `hornlab_waveguide_mesher @ 55da4f46d662d8dcd7a9f94a609eeea4009fcd62` (jamescollinharky fork; unchanged this program) |
| Resume status at review close | run `runs/20261113T193536Z-screen-81c964` live at 189/200 (`stats.failures` = 28, all pre-solve); night `resume_print_night_2026-11-14` (`kind: command`, `--budget 45`, 9000 s) RUNNING |
| E0 gate | `search.ndjson` reaches 200 rows, runner exit 0, no `solve_failed` |
| Design configs | `examples/typologies/print_80x60_2026-11-13/p80x60__{osse_ext_throat,ath_core_14in}_700_v7.yaml` — caps 12,000 (screen/verify/final), `angle_count: 73`, `balloon: true`, band 350–8,000 Hz |
| Round files | `docs/queue/speed_round_a_2026-11-14.yaml` (2 arms), `docs/queue/speed_round_b_2026-11-14.yaml` (4 arms); per-arm cold caches under `scratch/`, `HORNLAB_FREQ_BATCH_SIZE` set per arm, timeout 3600 s |
| Whole-candidate wall source | `run.json.stats` (`mean_seconds_per_candidate`, per-row `total`; `cma.py:603-614`) — the night `SUMMARY.md` is context only |
| Batch knob provenance | env-only until C3 lands — invisible in `config_sha` (`rundir.py:40-42`); archive the night YAML beside each arm's run dir |
| Parity tool | `.venv\Scripts\hornlab-search.exe compare <run_a> <run_b>` — emits max/mean |diff| for `bw_h_deg, bw_v_deg` (°) and `di_db, on_axis_db, ripple_h_db, ripple_v_db` (dB); requires `di_source: balloon` in both runs |
| Spill guard | `tools/bench/_bench_common.GpuMemPeak` — `SPILL_MIB = 512`, Windows perf counters `\GPU Process Memory(*)\{Dedicated,Shared} Usage`, pid-scoped to the host tree; anything > 512 MiB shared invalidates the arm |
| Runner hygiene | `tools/run_campaign_night.py` runs lane-aware `gpu-clean` before AND after every job (`:639-646`, `:684-687`); post-hygiene failure is note-only (`:836`, `:843`) → check each arm's baseline before trusting it |
| Ceiling tool | `tools/measure_fused_ceiling.py --mouth-res {5.03,4.46,4.09} --flag on --cache-dir scratch/ceiling_cache` → quarter DOF 15,878 / 20,152 / 23,850; one solve per invocation; you run `gpu-clean` between points |

## 3. Pre-declared decision rules (set before Round A; never moved after the fact)

Hypotheses, each on both designs (D1 = osse_ext_throat, D2 = ath_core), whole-candidate wall from `run.json.stats`:

- **H1 (upgrade):** `wall(new b1) / wall(base b1) ≤ 0.85` on both designs, with parity per I1.
- **H2 (batching):** `wall(new b12) / wall(new b1) ≤ 0.85` on both designs, shared spill ≤ 512 MiB.
- **H3 (combination):** `wall(new b12)` no worse than the best single arm on both designs.
- **H4 (ceiling):** the 15,878-DOF point fits with zero shared spill on the new solver; record 20,152 / 23,850 and
  the largest that fits.

**Repeat rule (hardened; spread data does not support fewer safe-guards):** G2's per-rep spread is ~11 % (s/freq) at
4,168 DOF and unmeasured whole-candidate. If a decision ratio lands in **[0.80, 0.92]**: re-run BOTH arms of that
pair with fresh cache/dataset roots (naming: `scratch/speed_round_<r>/<arm>_rep2`), decide on the median of the three
per-arm walls. A **median ratio above 0.85 rejects** — a gray pass never adopts. H1 repeats need the pin swapped back
to `0850ef39` and forward again (each swap ≈ 2 min; the reverse-order repeat is preferred to expose drift).

**Parity bar:** 0.039 dB / 1° comes from the CP-7f solver-disagreement noise floor (codified in `docs/FORKS.md:49-51`).
Compute it manually from `compare`'s max/mean values. Record exact max diffs: **0.0 on all six fields is the expected
diagnostic** for an untouched-kernel change — nonzero-but-in-bar passes; treat systematically nonzero diffs as a
finding to investigate, not to tolerate silently.

**Rejection handling:** if H1 or H2 fails, do NOT merge; run rollback (§7); write up the result — a measured no is a
result, not a failure. Batch-4 fallback (R2) applies only when batch-12 fails **only** on spill.

## 4. Execution steps

Preflight before EVERY block (from §13 + gate updates):

```powershell
git status --porcelain                       # expect only known untracked scratch
git log --oneline -1                         # record the exact commit
Get-Content C:\Users\hunte\Hrns\hornlab-search\.venv\Lib\site-packages\hornlab_beat_bem-*.dist-info\direct_url.json
nvidia-smi --query-gpu=memory.used --format=csv,noheader   # near-idle ≤ ~0.7 GB, else gpu-clean and re-check
.venv\Scripts\hornlab-search.exe gpu-clean
Get-CimInstance Win32_Process -Filter "Name='julia.exe' OR Name='python.exe'"   # no stray solver/night/agent
.venv\Scripts\python.exe tools\run_campaign_night.py --night runs\nights\<file>.yaml --dry-run
```

Record `vram_baseline_mb` next to every measured number. If a baseline is abnormal, STOP the block, clear, and
re-run — do not normalize post-hoc.

**E0 — finish the interrupted run (RUNNING now).** Wait for the resume night: `search.ndjson` = 200 rows, runner
exit 0, zero `solve_failed`. If the budget exhausts before 200 rows: diagnose before touching anything
(pre-solve `invalid_geometry`/`mesh_too_large` rows are failures *within* rows, not missing rows). **Gate → E1b.**

**E1b — archive the suite evidence (was E1; ~15 min, GPU idle, no install).** In
`C:\Users\hunte\Hrns\forks\hornlab-beat-bem` (branch tip `38e5b1f`, tree must be clean):
run the Julia CPU test suite and `julia scripts/validate_analytic_exterior.jl`; save the COMPLETE raw output
(stdout+stderr, exit codes) to
`docs/evidence/JULIA_CPU_SUITE_38e5b1f_2026-11-13.log` and `docs/evidence/ANALYTIC_EXTERIOR_38e5b1f_2026-11-13.log`,
and paste the pass/fail counts into `notes_for_senior`-style prose only as a pointer to the logs.
Expected: exit 0, 3830 pass / 0 fail / 4 broken (the four CUDA testsets `@test_skip` without a device — confirmed
code-reading), analytic OK with controls still failing as required. Any count mismatch vs the attestation = STOP (the
committed forks are not what the attestation describes). **Gate → E2.**

**E2 — (DONE.)** C1+C2 packaged as one install SHA `38e5b1f`, pushed to `ourfork`. No action.

**E3 — Round A (~15-20 min GPU).** Copy `docs\queue\speed_round_a_2026-11-14.yaml` to `runs\nights\`, then queue it
detached, chained behind the live resume runner:

```powershell
Copy-Item docs\queue\speed_round_a_2026-11-14.yaml runs\nights\ -Verbose
powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 `
  -Script tools\night_queue\queue.ps1 `
  -ScriptArgs "-Nights speed_round_a_2026-11-14 -WaitPid <resume_runner_pid> -WaitMatch resume_print_night -Log runs\nights\queue_speed_round_a.log"
```

Gates: both arms complete rc 0; arms' `run.json.stats` (mean s/candidate) and DOF/frequency counts recorded; the night
YAML copied into each arm's run dir; baselines sane. **Gate → E4.**

**E4 — pin swap (integrator only, outside any night; ~5-10 min).**

```powershell
.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps "hornlab-beat-bem @ git+https://github.com/llevaachingada/hornlab-beat-bem.git@38e5b1f8ca840ebf6351c54611a08fedb1a0750f"
# direct_url.json -> url https://github.com/llevaachingada/..., commit_id 38e5b1f8ca840ebf6351c54611a08fedb1a0750f
.venv\Scripts\python.exe -m hornlab_beat_bem.provision --backend cpu
Select-String -Path .venv\Lib\site-packages\hornlab_beat_bem\julia\BeatEngineDriver.jl -Pattern 'fused_burton_miller_cuda \? nothing' | Measure-Object   # exactly 2
```

**Gate:** SHA + marker count exact. **Gate → E5.**

**E5 — Round B (4 arms, ~40 min GPU).** Copy `speed_round_b_2026-11-14.yaml` to `runs\nights\`, queue as E3 (with
`-WaitPid <E3 runner pid> -WaitMatch speed_round_a`). Gates: all four arms rc 0; no arm's peak shared > 512 MiB
(GpuMemPeak recorded with the C4 wrapper for the b12 arms); the two b1 arms recorded for parity. **Gate → E6.**

**E6 — ceiling sweep (6 points, fresh process each, ~15 min).** For `--mouth-res` in `5.03, 4.46, 4.09` (× 2 reps):

```powershell
.venv\Scripts\hornlab-search.exe gpu-clean
.venv\Scripts\python.exe tools\measure_fused_ceiling.py --mouth-res <r> --flag on --cache-dir scratch\ceiling_cache --runs-dir runs
nvidia-smi --query-gpu=memory.used --format=csv,noheader     # verify clean after
```

Record fits / does-not-fit, dedicated peak, baseline, and the quarter-DOF count. If 4.09 mm fits, run ONE
exploratory point above it (e.g. 4.0 mm) and record the measured edge. A point that does not fit is a result,
recorded, not a failure. **Gate → E7.**

**E7 — compute the decision.** Read all six arm run dirs' `run.json.stats`; compute H1/H2/H3 ratios per design and
H4; apply the parity bar manually from `compare` output (Round A vs Round B arms on matched designs; batch-1 vs
batch-1 first, then b12 within Round B — same-solver comparison); apply the repeat rule if any ratio is in
[0.80, 0.92]. Outcome is one of: ADOPT / ADOPT-WITH-BATCH-4 / REJECT. **Gate → E8 (adopt) or §7 rollback (reject).**

**E8 — the merge (ONE commit, only on ADOPT).**

1. FIRST append to `NOTES_FOR_SENIOR.md` (append-only): contract-gap note that `solve.freq_batch_size` is a new
   `solve.*` key not enumerated in frozen `01_CONTRACTS.md`, authorized under the owner's speed program of
   2026-11-13, following the `cuda_fused` field precedent.
2. `pyproject.toml` + `TOOLCHAIN.md`: beat pin → `38e5b1f8ca840ebf6351c54611a08fedb1a0750f` (full SHA).
3. `hornlab_search/config.py`: `SolveSettings.freq_batch_size: int | None = None`, validate `None or >= 1`;
   `search/cma.py` `_prepare`: pass it to the backend alongside `cuda_fused`/`julia_threads` (only when CUDA).
4. The two print example configs: add `solve.freq_batch_size: 12`. The env var stays as an override.
5. A5 re-base (`solve/feasibility.py`): replace the pin-A `FUSED_CUDA_FACTOR = 4.0` model with the measured fit
   (`dense 8N² + intercept`, fitted across the measured points incl. the ceiling sweeps; keep a linear shape only
   if it fits all points within ~10 %). Re-base — do not delete or weaken — `tests/test_solve_feasibility.py`'s
   stale `20,237 → refuse` case to the new measured refusal boundary (first point beyond the ≥ 30 % safety-margin
   under the measured max-fit). Never touch `01_CONTRACTS.md`.
6. Update `docs/CONTINUITY.md` + `docs/ISSUES.md` in the same commit (push rule), the queue docs' stale lines, and
   mark `SPEED_PROGRAM`/`SPEED_ARCHITECTURE` adopted. Offline tests green (push includes `pytest` deselection rules).
7. Verify `config_sha` changes with the new key present in a trial config (it hashes `cfg.raw`).

**Gate → E9.**

**E9 — relaunch production fresh.** New night file (never resume across the solver change), absorbing the old
night's deferred third job. Verify the first production run's `lib_shas` show the new beat SHA and `freq_batch_size`
is present in its config, so batch is provenanced from here on.

## 5. Post-adopt reporting

- Evidence log per block: night YAML, summary, arm run dirs, raw install/verify output, E1b suite logs.
- A short `docs/evidence/SPEED_ADOPTION_2026-11-14.md`: arms table (walls, ratios, DOF), parity diffs, spill record,
  ceiling table, A5 fit, decision, and rollback state.
- Push: CONTINUITY top entry + ISSUES row in the same commit.

## 6. Stop/abort conditions

Parity beyond bar (either design) · any b12 arm shared spill > 512 MiB · E1b suite counts differ ·
budget/E0-gate arithmetic mismatch · arm OOM/timeout not reproducing from clean state · unknown worker errors after
hygiene (twice = hard stop per rule 8) · any I1-I8 violation observed, including by another agent.

## 7. Rollback (≈ 2 min, verified commands)

```powershell
.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps "hornlab-beat-bem @ git+https://github.com/llevaachingada/hornlab-beat-bem.git@0850ef39b29d7c51f8fbb082184d3784d2ff8bef"
.venv\Scripts\python.exe -m hornlab_beat_bem.provision --backend cpu
# verify direct_url.json -> 0850ef39...
```

Data needs no rollback (A1 keeps legacy entries; old runs keep their `lib_shas`). Revert the single E8 merge commit
if it existed. Cache invalidation from a SHA change is expected once; the next run re-solves.
