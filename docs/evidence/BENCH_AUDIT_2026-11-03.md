# CPU vs CUDA audit: the "CPU is 6.4x faster" result was a VRAM spill (2026-11-03)

Supersedes the conclusion of `BENCH_CPU_VS_CUDA_2026-11-03.md` (PR #19, `meh/integration`). Its numbers were
measured; its conclusion — "for the MEH's dof regime the CPU backend is the faster engine" — does not hold.
The CUDA arm it timed was the four-operator path overflowing the 8 GB card into Windows shared system memory.

Machine: RTX 4060 Laptop 8 GB (WDDM, driver 610.62, HAGS on), i7-14650HX, 31.7 GB RAM.
Mesh: `runs/bench_fullrange_20261103T022309Z/mesh/mesh.msh` — the T2 MEH seed, 8,044 quarter dofs,
15,758 triangles, tags 1/2/10, symmetry `yz+xz`. Solver: beat-bem fork `hornlab-search/meh-fused-cuda`.

## Method

One fresh Python process per arm, BEAT hosts cleared with `hornlab-search gpu-clean` (tree kill) before
each. Three single-frequency calls per arm: 1 kHz warm-up, then 5 kHz twice; the second 5 kHz call is the
warm rate. A thread sampled every 0.5-1 s both `nvidia-smi` and the Windows per-process
`\GPU Process Memory(*)\Dedicated Usage` / `\Shared Usage` counters for the arm's process tree.
Parity compares `channel_pressure` (both channels, both planes, 37 angles) and `impedance_matrix`.

## 1. The spill (first pass, 22:38 EST 2026-11-02)

| arm | warm s/freq | host dedicated peak | host **shared** peak |
|---|---|---|---|
| CUDA fused, 1 channel | **3.01** | 2,122 MiB | 80 MiB |
| CUDA four-operator, 1 channel | 25.93 | 7,186 MiB | **6,532 MiB** |
| CUDA four-operator, 2 channels (what PR #19 timed) | 43.77 | 7,390 MiB | **6,928 MiB** |
| CPU, 2 channels | 15.43 | — | — |

The four-operator path needs ~14 GB here; about half lives in shared system memory and is paged over PCIe.
That is NVIDIA's CUDA sysmem fallback (driver >= 536.40, default policy on Windows): an over-size
allocation succeeds in system RAM and the solve runs 5-10x slower instead of failing. `nvidia-smi` reports
only device memory (pinned at ~7.8 GB, which is also inflated by CUDA.jl's pool cache), so every earlier
"peak VRAM ~7.8 GB" reading was the card's ceiling, not the working set.

## 2. Multi-channel fused CUDA (fork `hornlab-search/meh-fused-cuda`)

The fused path refused more than one channel, which is why every MEH solve used the four-operator path. The
LHS is drive-independent, so the driver now assembles it once, builds each further channel's RHS with the
existing `assemble_burton_miller_rhs_cuda`, and solves all columns against one LU. Second pass, same
protocol (23:05 EST):

| arm | warm s/freq | host dedicated peak | host shared peak |
|---|---|---|---|
| **CUDA fused, 2 channels** | **2.66** (3.30 earlier pass) | 2,122 MiB | 80 MiB |
| CPU, 2 channels | 5.96 | — | — |
| CUDA four-operator, 2 channels | 38.82 | spilled (as above) | spilled |

Parity, max over both channels, both planes, all angles:

| pair | channel SPL max abs dB | impedance matrix max rel |
|---|---|---|
| fused vs CPU | 4.2e-04 | 3.4e-06 |
| fused vs four-operator | 1.2e-04 | 6.5e-07 |
| four-operator vs CPU | 5.1e-04 | 3.2e-06 |

Fused is at least as close to CPU as the old path. Julia gate: `impedance_matrix_tests.jl` under
`MEH_TEST_BACKEND=cuda` now also runs the fused path and compares it per channel to the four-operator result.

**CPU spread.** The same CPU arm measured 15.4 s/freq right after the spilled CUDA arms (system RAM had
just held ~7 GB of paged GPU memory) and 5.5-6.0 s/freq on two later passes. CPU timings on this laptop are
load-sensitive; report a median of repeats, never one sample. Fused CUDA beats it by ~2.2x even at its best.

## 3. What was wrong with the 2026-11-02 benches

1. **The CUDA arm was the wrong path.** Four-operator, because fused refused MEH (now fixed).
2. **Spill was invisible.** Only `nvidia-smi` was sampled. Same CUDA measurement on the same mesh gave
   5.2, 6.8 and 37.2 s/freq across three runs — the spill depends on what else holds the card.
3. **The host reset was a no-op.** `taskkill /IM julia.exe` leaves the `worker_host` python tree alive and
   it respawns julia (`solve/worker.py` documents this since 2026-10-22). `CLAUDE.md` rule 1 still said to
   do it; fixed in the same commit.
4. **The headline was one run.** The 40-design bench in the same session had CUDA faster on 34/40 designs
   (median 2.2x); CPU won only on the cold first call and on the 8.5k-dof designs, i.e. exactly the spill.
   `full_range` on the 5,872-dof winner mesh: CUDA 2.1 s vs CPU 9.3 s per frequency.
5. **Smaller:** per-frequency figures from a 2-frequency call were compared with 1-frequency calls (setup
   amortises differently); a protocol yielded a negative CPU warm time (-1.14 s); single samples; the
   idle VRAM baseline moved from ~0.4 GB to ~1.9 GB (desktop apps and rbassist on the dGPU).

The bench scripts in `tools/bench/` now reset hosts by tree (`_bench_common.kill_hosts`), sample shared GPU
memory (`GpuMemPeak`, recorded as `host_shared_peak_mib` / `spilled`), and `cpu_vs_cuda_meh.py` takes
`--cuda-fused`.

## 4. Machine recommendations (owner actions; system settings)

- NVIDIA Control Panel -> Manage 3D Settings -> Program Settings -> `julia.exe` -> CUDA - Sysmem Fallback
  Policy -> **Prefer No Sysmem Fallback**. An over-size solve then fails fast (catchable, route to CPU)
  instead of silently running 10x slower.
- Windows Settings -> Display -> Graphics: set Chrome, Claude, Terminal and rbassist to Power saving
  (integrated GPU) for solve sessions. They held 1.3-1.9 GB of the 8 GB tonight.
- Plugged in, performance power mode (the card reported a 124 W limit; on battery it drops).

## Sources

- CUDA.jl memory management (pool caching, `reclaim`, why `nvidia-smi` over-reports):
  https://cuda.juliagpu.org/stable/usage/memory
- Sysmem fallback behaviour and the Control Panel setting: https://www.sidefx.com/forum/topic/95347 ,
  https://runaihome.com/blog/shared-gpu-memory-slow-local-ai-sysmem-fallback-fix-2026/
- Raw data: scratch records `res_*.json` / `res_*.npz` from the audit session (not committed).
