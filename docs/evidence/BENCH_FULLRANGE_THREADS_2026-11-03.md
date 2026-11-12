# Full-range + thread-count CUDA/CPU benchmarks (2026-11-03 UTC)

Machine: RTX 4060 Laptop 8 GB, i7-14650HX (16C/24T), 31.7 GB RAM. Pin unchanged (`1efdc6f`). Three runs, one
each, scripts committed under `tools/bench/`. Raw logs and JSONL are local and gitignored
(`runs/bench_fullrange_*`, `runs/bench_cuda_threads_*`).

These answer three separate questions: what the **contracted 41-point band** costs on the production mesh, what
the **grid we actually screen** costs on a real winner mesh, and whether **Julia threads** help the CUDA path.

## A. Contracted band: 41 points, 8,044 dofs, 2 tags

`tools/bench/full_range_cuda_cpu.py` (grid from `meh_t2a_search.yaml`, mesh built from the T2 seed, epw 4.05).

| arm | completed | total | per frequency | peak VRAM |
|---|---|---|---|---|
| CUDA | **41 / 41** | **1,577 s** (26.3 min) | 38.46 s | 7,924 MiB |
| CPU | 16 / 41, then stopped by the operator | 291 s to that point | 18.18 s | — |

- On the 16 paired frequencies (120–675 Hz): max |dSPL| **2.96e-04 dB**, median CPU/CUDA **0.47** (CPU ~2x faster
  per call).
- CUDA **completed** the 41-point sweep this time (it is the same harness the earlier screen used, but with one
  call per frequency): it did not crash, it simply sits at 7.9 GB and takes 26 minutes.
- The CPU arm was stopped deliberately, not failed: at ~18 s/frequency the second arm would have doubled a run
  already 33 minutes old. The partial data is sufficient to place the crossover.

## B. The grid we actually screen: 12 points, 5,872-dof winner mesh, 2 tags

Same script with `--mesh <winner mesh.msh> --grid-config meh_t2a.yaml` (the CAD-authored seed config, whose grid
is the frozen 12-point 500 Hz–10 kHz screen grid). Total 188 s.

| arm | per frequency | **12-frequency sweep** | peak VRAM |
|---|---|---|---|
| CUDA (one call per frequency, the app's CUDA policy) | 2.05–2.52 s | **25.7 s** | 7,796 MiB |
| CPU (one call per frequency — NOT the app's policy) | 8.3–10.4 s | 111.7 s | — |
| CPU (one call for the whole grid — the app's CPU policy) | 8.59 s effective | **103.0 s** | — |

- max |dSPL| **4.19e-05 dB** (median 1.30e-05).
- **CUDA is ~4.0x faster** on this grid and mesh (`103.0 / 25.7`).
- Method note: the app calls the solver once per frequency on CUDA (`per_frequency_calls` is mandatory there) and
  once per grid on CPU. The harness reproduces CUDA's policy; the CPU single-call number is the app-realistic one.

## C. Do Julia threads help the CUDA path? No.

`tools/bench/cuda_threads.py`, 8,044-dof mesh, fresh host per thread count, 1 kHz then 5 kHz:

| julia_threads | 1 kHz (cold incl. startup) | 5 kHz (warm) | speedup vs 1 thread |
|---|---|---|---|
| **1** | 76.09 s | **42.92 s** | 1.00 |
| 8 | 80.11 s | 48.98 s | **0.88** |
| 24 | 74.58 s | 44.88 s | **0.96** |

- More threads are **slightly slower**; SPL is bit-identical across settings (7.2936 / 5.5193).
- The CUDA path is GPU-bound. `julia_threads` is not a tuning lever, and the 43–49 s warm frequency matches the
  independent 41-point run's 38.5 s mean, so this is the card's real cost at this size.

## What the three runs together say

| regime | winner |
|---|---|
| screen grid (12 points), 1k–7k dofs | **CUDA, 1.5–4x** |
| 8k+ dofs, or a 41-point sweep | **CPU** (CUDA: 38.5 s/frequency, 7.9 GB pinned) |
| < 1k dofs | CPU (GPU launch overhead) |
| host threads | no effect on CUDA |

Concurrent CUDA solves are not an option on this card either: one solve already peaks at 7,924 of 8,188 MiB.

**Caveats.** One frequency pair for the thread test; one design for the full-range run; the CPU policy difference is
stated above; all numbers are one machine, one pin. Do not extrapolate to other geometries without re-measuring.

## Reproduce

```powershell
# contracted 41-point band on the production mesh (slow: ~35 min for both arms)
.venv\Scripts\python.exe tools\bench\full_range_cuda_cpu.py --max-seconds 3600
# the realistic screen grid on a stored winner mesh (~3 min)
.venv\Scripts\python.exe tools\bench\full_range_cuda_cpu.py --mesh <abs path to mesh.msh> --grid-config examples\typologies\meh_2026-10-30\meh_t2a.yaml
# threads 1 / 8 / 24 on the slow CUDA regime (~6 min)
.venv\Scripts\python.exe tools\bench\cuda_threads.py
```

Mesh paths passed to the solver must be **absolute** — the Julia worker opens the file from its own cwd; the
harness resolves them, and a relative path otherwise fails with "No such file or directory".
