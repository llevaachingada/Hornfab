# CUDA vs CPU for the MEH solve, and 16 kHz on CPU (2026-11-03 UTC)

Machine: owner's box (RTX 4060 Laptop 8 GB, i7-14650HX 16C/24T, 31.7 GB RAM). Solver pin unchanged
(`hornlab-beat-bem @ 1efdc6f`). BEAT CPU runtime provisioned for this run (`provision --backend cpu`, 25 s).
Script: `tools/bench/cpu_vs_cuda_meh.py`. Raw log and JSON: `runs/bench_cpu_cuda_20261103T013105Z/`
(local, gitignored). **Budget: 900 s; the run took 372 s.** No tolerances, configs or pins were changed.

What this deliberately did **not** repeat: TOOLCHAIN's single-source cuda-vs-cpu timings, the bempp
cross-check, and the earlier MEH screens (CUDA only). The gaps filled here are (A) multi-tag on the CPU
backend, (B) the production MEH mesh on CPU vs CUDA at matched settings, (C) a 16 kHz mesh on CPU.

## A. The CPU backend does support multi-tag solves

2-tag tetrahedron, 1 kHz, `velocity_sources={2:1,10:1}`, `impedance_matrix=True`:

| backend | result | wall |
|---|---|---|
| beat_cpu | OK, `channel_tags (2, 10)`, SPL `(1, 2, 37)` | **2.34 s** (cold) |

So the MEH path is not CUDA-only. (The bempp cross-check backend still refuses `source_tags`; that is
separate and unchanged.)

## B. Production MEH mesh (T2 seed, 8,044 dofs / 15,758 triangles), 2 tags

Warm protocol: one warm-up call at 1 kHz, then the **same two-frequency call twice** (1 kHz + 5 kHz).
The second repeat is the rate; subtracting two different calls is invalid when call 1 absorbs startup.

| arm | warm-up | repeat A (2 freqs) | repeat B (2 freqs) | **warm per frequency** | peak VRAM |
|---|---|---|---|---|---|
| CUDA | 55.8 s | 71.6 s | 74.5 s | **37.2 s** | 7,853 MiB |
| CPU | 8.4 s | 11.6 s | 11.7 s | **5.86 s** | - (host RAM) |

- **CPU is 6.4x faster than CUDA at this mesh size** (ratio 0.16). Results agree: max |dSPL| **5.03e-04 dB**.
- This is consistent with the documented CUDA behaviour in TOOLCHAIN: fast at ~4–6k dofs (the 12-frequency
  screen at 5,872 dofs measured 3.6 s/frequency), then a cliff by ~8k. The CPU path scales gently.
- Caveat: one mesh size, two frequencies, one machine; the CPU arm uses the host's BLAS threads while the
  CUDA arm is a dense per-channel LU on an 8 GB card. Do not extrapolate beyond this dof range without
  re-measuring.

## C. 16 kHz mesh: CPU runs it, CUDA cannot hold it

The earlier 16 kHz attempts were refused by the **application's dof cap (8,900)**, not by the mesh or the
card. With the cap raised to 45,000 for this diagnostic build only:

| item | value |
|---|---|
| mesh (T2 seed, epw 5.4, 16 kHz request) | **49,757 triangles / 25,171 dofs**, built in 5.0 s |
| CPU solve, 1 kHz, 2 tags, 37-angle cuts + balloon | **100.7 s** |
| CUDA static storage at this mesh (audit formula 24·N·E + 32·N²) | **46.9 GiB** before workspace → cannot fit 8 GB |

**Wall-resolution caveat, unchanged and important:** at epw 5.4 the validator reports the driven patches
resolve to ~21.8 kHz but the rigid walls only to ~10.3 kHz. So "16 kHz capable" here means
driven-patch-accurate, wall-coarse above ~10 kHz. It is not a claim of a converged 16 kHz acoustic mesh.

## What this changes

1. **The CPU backend is a first-class option for this workload, not a fallback.** At the production MEH
   mesh it is 6.4x faster than the 8 GB card and needs no VRAM. The earlier hardware conclusion (rent a
   GPU) should be revisited for the MEH specifically: a CPU solve may already be the cheaper path for
   screens, with the GPU reserved for the cases where it is actually faster.
2. **16 kHz is reachable today on CPU** (100.7 s per frequency at 25k dofs), at the wall-resolution caveat
   above. The same mesh is unreachable on the 8 GB card by a factor of ~6 in memory.
3. **The dof cap is a setting.** Both 16 kHz attempts failed with `exceeds the dof cap 8900`; raising it is a
   config change, not new hardware. Any "we cannot go above 12 kHz" statement must say *on an 8 GB card with
   the current caps*.

## Reproduce

```powershell
.venv\Scripts\python.exe -m hornlab_beat_bem.provision --backend cpu   # once, ~25 s
.venv\Scripts\python.exe tools\bench\cpu_vs_cuda_meh.py --budget 900
```

Logs land in `runs/bench_cpu_cuda_<UTC>/log.txt` with a per-step timestamped line and a `summary.json`.
