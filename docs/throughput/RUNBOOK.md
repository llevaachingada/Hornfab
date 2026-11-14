# Throughput packet: owner runbook (2026-11-04)

Plain-language checklist for the Windows box (RTX 4060, 8 GB). Everything new is **opt-in**: with nothing switched
on, searches, hashes, cache keys, record formats and numbers are exactly what they were. Spec behind this:
the throughput handoff packet of 2026-11-04 (sections 3 and 5). Rules of the road: `CLAUDE.md` ("GPU / Julia hygiene").

**Golden rules.** One GPU job at a time. Never run `taskkill /IM julia.exe`. Clear stale hosts only with
`.\.venv\Scripts\hornlab-search.exe gpu-clean` (it kills only this project's hosts and refuses while a live job holds
the GPU lock). Close other GPU programs. Read results from the output files, not from the console.

## 0. What is new (one line each)

| Piece | Switch | Default |
|---|---|---|
| Stage timer (WP0) | `$env:HORNLAB_STAGE_TIMING="1"` | off; writes `designs\<hash>\stage_timing.ndjson` |
| Throughput matrix (WP0) | `tools\bench\throughput_matrix.py` | a tool, nothing runs by itself |
| Mesh prefetch (WP2) | `$env:HORNLAB_PIPELINE_PREFETCH="2"` or `search: {pipeline_prefetch: 2}` | 0 = serial, as today |
| Frequency batching (WP5) | `--batch-sizes` in the matrix, or `$env:HORNLAB_FREQ_BATCH_SIZE="4"`, or the config key `solve.freq_batch_size` (default `None` = env fallback governs). **Owner decision 2026-11-14:** batch **12** approved for HEAVY runs (verify/final tiers, many-frequency grids) — set `$env:HORNLAB_FREQ_BATCH_SIZE="12"` (or `env:` in the night job, which the archived night YAML records as provenance). Screen-tier searches stay unbatched by default (the pre-declared whole-candidate bar rejected batch 12 there, 0.851/0.865). | off = today's grouping |
| Curvature meshing (WP4) | `mesh: {curvature_npts: 12}` (CAD/MEH route only) | 0 = off = today's meshes |
| CPU+GPU pilot (WP3) | `tools\bench\cpu_gpu_concurrent.py` | a tool, bench only |
| Solver identity-skip (WP1, G2) | **ADOPTED 2026-11-14** as solver `38e5b1f` (whole-candidate wall −24.7 %/−28.0 %, parity ~1e-5 dB, zero spill, measured ceiling 24,973 quarter-DOF; `docs/evidence/SPEED_ADOPTION_2026-11-14.md`) | on in the installed solver |
| Spill watchdog | `tools\bench\run_with_memwatch.py` (attach/spawn; shared VRAM = the counter nvidia-smi cannot see) | a tool, observer only |

## 1. Pull and run the offline tests (no GPU)

```powershell
cd <your Hornfab folder>
git fetch origin
git checkout ccr-80a29f93-dxnmdm
git pull
.\.venv\Scripts\python.exe -m pytest -q tests\test_profiling_stage_timer.py tests\test_search_pipeline_prefetch.py `
    tests\test_solve_freq_batch.py tests\test_mesh_curvature_policy.py tests\test_bench_throughput_matrix.py tests\test_bench_pilots.py
.\.venv\Scripts\python.exe -m pytest -q
```
Expected: the new files all pass; the full suite passes (on the Windows box the report tests also pass because the
plotting package is installed; in the build container 5 report tests fail only because that package is absent).
If anything fails, stop and send the output.

## 2. GPU steps, in this order (one at a time; hygiene before EVERY step)

**Hygiene (before each GPU step).**
```powershell
Get-Process julia -ErrorAction SilentlyContinue          # should list nothing from an old run
.\.venv\Scripts\hornlab-search.exe gpu-clean              # clears only our stale hosts
nvidia-smi --query-gpu=memory.used --format=csv           # desktop alone is ~0.3-0.5 GB; write the number down
```

**Fixtures.** You need a mesh `.msh` (metres). Easiest: use a finished run, e.g.
`runs\<run>\designs\<hash>\mesh.msh`, or let the matrix mesh the config's seed with `--build-seed`. Use the
`*_fusedcuda.yaml` config so the solve really is the fused path (the matrix prints and records `cuda_fused` and the
solver's own `assembly_paths`; **if that column does not say `fused_cuda`, the run does not count**).

### Step A. Baseline matrix (the scorecard for everything else)
```powershell
.\.venv\Scripts\python.exe tools\bench\throughput_matrix.py --config examples\osse_baseline_fusedcuda.yaml `
    --build-seed --freq-sets 12 --batch-sizes default --warm-reps 3 --out runs\tp_baseline_12
```
Then repeat with `--freq-sets 25` and `--mesh small=...` / `--mesh mid=...` fixtures (small 2-3k DOF, 5-9k DOF, and a
real two-tag MEH mesh with `examples\<meh config>.yaml`). Only add `--freq-sets 41` for meshes you know fit. Each arm
gets a fresh host (cold rep first, then 3 warm reps) so VRAM numbers are comparable; do not use `--no-cold` for
VRAM comparisons.

### Step B. WP2 prefetch on/off (real search, same seed, same budget)
```powershell
.\.venv\Scripts\hornlab-search.exe search --config examples\osse_baseline_fusedcuda.yaml --budget 24
# note the run folder it prints (runs\<A>), then:
$env:HORNLAB_PIPELINE_PREFETCH="2"
.\.venv\Scripts\hornlab-search.exe search --config examples\osse_baseline_fusedcuda.yaml --budget 24
Remove-Item Env:HORNLAB_PIPELINE_PREFETCH
.\.venv\Scripts\python.exe tools\bench\compare_search_runs.py runs\<A> runs\<B>
```
(Use a fresh cache folder or `--budget` on a config whose cache is empty; cached hits would hide the effect.)
Optionally also run the second search with `$env:HORNLAB_STAGE_TIMING="1"` to get `stage_timing.ndjson`
(`mesh_prefetch` rows are the work moved off the critical path).

### Step C. WP4 curvature study (no solve needed)
```powershell
.\.venv\Scripts\python.exe tools\bench\mesh_policy_study.py --config examples\<a CAD/MEH config>.yaml --curvature 0,8,12,20
```
Add `--solve` only after reading the table, and then compare against a **finer converged reference** before
believing any smaller mesh. Formula/grid designs ignore the policy; the tool says so.

### Step D. WP5 frequency batching A/B
```powershell
.\.venv\Scripts\python.exe tools\bench\throughput_matrix.py --config examples\osse_baseline_fusedcuda.yaml `
    --mesh mid=runs\<run>\designs\<hash>\mesh.msh --freq-sets 12 --batch-sizes default,1,2,4,12 --warm-reps 3 --out runs\tp_batch_12
```
Do 41 frequencies only if the 12-set shows no VRAM trouble. The old 689 s cliff was on the pre-fused path; do not
assume it, and do not assume it is gone.

### Step E. WP3 CPU+GPU pilot (last; it loads the whole machine)
```powershell
.\.venv\Scripts\python.exe tools\bench\cpu_gpu_concurrent.py --config examples\osse_baseline_fusedcuda.yaml `
    --mesh-gpu runs\<run>\designs\<hashA>\mesh.msh --mesh-cpu runs\<run>\designs\<hashB>\mesh.msh `
    --n-per-lane 3 --freq-set 12 --cpu-threads 4
```
Pick `--n-per-lane` so the two lanes finish at about the same time (the CPU lane is slower per candidate: use a
smaller mesh for it). Repeat with `--cpu-threads 2` and `8`. Do not run anything else heavy meanwhile.

## 3. What the output files mean

| File | Meaning |
|---|---|
| `results.csv` (matrix) | one row per solve: `rep` is `cold` or 1..N; `wall_s` end to end; `solve_s` solver call; `assembly_paths` must read `fused_cuda`; `vram_baseline_mib`/`vram_peak_mib` from the backend, `smi_baseline_mib`/`smi_peak_mib` from the separate nvidia-smi poller; `timings_json` the solver's own stage seconds |
| `summary.csv` / `summary.json` | one row per arm: warm median/min/max, `warm_rel_spread` (how noisy), `candidates_per_hour_warm`, `cold_wall_s`, `speedup_vs_<first batch>`, `parity_vs_<first batch>` (frequencies equal, shapes equal, max SPL difference in dB), failures |
| `env.json` | git SHA, python, platform, nvidia-smi name/driver, pinned library SHAs, `HORNLAB_*` environment, the exact arguments |
| `gpu_samples.csv` | raw nvidia-smi polls (memory, utilisation) |
| `designs\<hash>\stage_timing.ndjson` | per candidate: `mesh_build`, `mesh_prefetch`, `solve`, `solver_path`, `metrics`, `meh_inner_optimize`, `score`, `cache_store`, `persist`, `candidate_total` (seconds each) |
| `run.json` -> `pipeline_prefetch` | prefetch depth, meshes built ahead, seconds the main loop waited for a build, whether it disabled itself |
| `mesh_policy_study.csv` | per curvature value: triangles (E), vertices (N = dofs), edge length min/mean/p95/max, build seconds, ratios vs baseline |
| `report.json` (WP3) | per-lane time alone vs together, `slowdown`, aggregate candidates/hour vs GPU alone vs ideal sum, per-candidate parity, `adopt_hint` |

## 4. Pass / fail gates (packet section 5; decide only from repeated runs)

1. **Always:** every requested frequency present, in order (`freqs_equal` true, same row count); polar, balloon,
   impedance arrays present and equal within the comparison tolerance; `assembly_paths` = `fused_cuda`.
2. **WP2 prefetch:** `compare_search_runs.py` says IDENTICAL (same candidates, same order, same objectives), the
   ndjson is intact, and candidates/hour is higher by more than the run-to-run spread. If `pipeline_prefetch.disabled`
   is `true` in `run.json`, the mesher refused to run off the main thread on this machine: result is "no gain",
   nothing is broken.
3. **WP5 batching:** `parity_vs_default` max SPL difference ~0 dB, no failures, no new VRAM peak above the 1-frequency
   arm, and a warm median lower than `default` beyond `warm_rel_spread`. Any OOM or worker exit = reject that size.
4. **WP4 curvature:** fewer dofs (`N_ratio` < 1) AND, with `--solve`, agreement with a finer converged reference at
   12-20 kHz, beamwidth, DI, throat impedance; never accept on mesh-time alone (mesh build is a few percent of a
   candidate; the saving is fewer solver dofs).
5. **WP3 pilot:** aggregate candidates/hour above the GPU alone by more than the spread, `cuda_slowdown` small,
   zero failures, parity ok, a clean process list afterwards (`Get-Process julia` empty after the run). Otherwise reject.
6. **Everywhere:** one GPU solve at a time, no stray hosts, results reported as valid candidates per hour end to end
   (not a faster mesh command or a one-frequency timing). Report negative results too.

## 5. If something goes wrong

- A solve crashes or a host lingers: run `hornlab-search gpu-clean`, check `nvidia-smi`, repeat from a clean state.
  A crash only counts as a finding if it reproduces from a clean state.
- `--resume` and the cache work as before with prefetch on or off.
- To turn everything back to "as before": unset the environment variables (`Remove-Item Env:HORNLAB_PIPELINE_PREFETCH`,
  `Remove-Item Env:HORNLAB_STAGE_TIMING`, `Remove-Item Env:HORNLAB_FREQ_BATCH_SIZE`) and leave `curvature_npts` out of configs.
- The old scripts in `tools\bench\` (`cuda_threads.py`, `full_range_cuda_cpu.py`, `cuda_cpu_40designs.py`,
  `cpu_vs_cuda_meh.py`) no longer kill Julia by image name, and still run the historical NON-fused path unless you set
  `$env:HORNLAB_BENCH_FUSED="1"` and `$env:HORNLAB_BENCH_SYMMETRY="yz+xz"` first. For production-path numbers use
  `throughput_matrix.py`.
