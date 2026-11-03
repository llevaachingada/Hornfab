# 40 existing designs, one identical solve each: CUDA vs CPU (2026-11-03 UTC)

Machine: RTX 4060 Laptop 8 GB, i7-14650HX (16C/24T), 31.7 GB RAM. Pin unchanged (`1efdc6f`). Script:
`tools/bench/cuda_cpu_40designs.py` (budget 2,400 s; **ran 358.6 s**). Raw log and per-design JSONL:
`runs/bench_40designs_20261103T015652Z/` (local, gitignored).

Design set: **40 stored designs, no CAD and no re-meshing** — 30 single-source (tags {1,2}, drive tag 2)
stratified across the dof range, plus 10 multi-entry designs (tags {1,2,10}, drive tags 2 and 10). Same
frequency (1 kHz), same observation (2 m, 37 angles, 2 planes), same impedance-matrix flag, one solve per
design per arm. Hosts cleared before each arm, so the first design in an arm is the cold start.

## Headline

| | CUDA | CPU |
|---|---|---|
| cold first call (96-dof design) | **26.47 s** | **2.45 s** |
| warm mean per design | 3.54 s | 4.18 s |
| sum over all 40 | 164.4 s | 165.5 s |
| median CPU/CUDA | — | **2.23x** (CPU slower) |
| designs where CPU won | — | **6 / 40** |
| SPL parity | — | max |d| **3.6e-05 dB**, median 8.0e-06 dB (all 40 paired) |
| CUDA peak VRAM | 7,841 MiB | — |

**The crossover is not a single point — it is a shape.** CPU wins at the two ends and loses badly in the
middle:

| dof band | n | median CPU/CUDA |
|---|---|---|
| 0–1,500 | 15 | 1.60 |
| 1,500–3,000 | 7 | 2.82 |
| 3,000–6,000 | 14 | **3.85** |
| 6,000–10,000 | 4 | 1.16 (two designs at 8.4–8.5k: CPU **2.3–2.8x faster**) |

- **Tiny meshes (<1k dofs): CPU faster** (0.17–0.22 s vs 0.35–0.72 s). GPU launch/serialisation dominates.
- **1k–7k dofs: CUDA faster by 1.5–4x**, peaking near 4x at 3–6k dofs.
- **Above ~7k dofs: CUDA falls off its cliff.** 6,929 dofs costs 5.81 s; 8,472 dofs costs **41.63 s** and
  8,530 dofs **53.56 s** — 7–9x more for +22 % dofs — while CPU scales smoothly (11.0 → 18.1 → 18.9 s).
  That cliff is the same one documented in TOOLCHAIN/M8; here it is located between 6.9k and 8.4k dofs.

## Full table (warm, paired, 1 kHz)

| dofs | tags | CUDA s | CPU s | CPU/CUDA |
|---:|---|---:|---:|---:|
| 96 | 1,2 | 26.47* | 2.45 | 0.09 |
| 639 | 1,2 | 0.72 | 0.17 | 0.23 |
| 801 | 1,2 | 0.35 | 0.20 | 0.59 |
| 918 | 1,2 | 0.38 | 0.22 | 0.58 |
| 1052 | 1,2 | 0.39 | 0.46 | 1.17 |
| 1251 | 1,2 | 0.42 | 0.70 | 1.68 |
| 1314 | 1,2 | 0.45 | 0.65 | 1.44 |
| 1344 | 1,2 | 0.45 | 0.74 | 1.63 |
| 1367 | 1,2 | 0.46 | 0.75 | 1.64 |
| 1386 | 1,2 | 0.45 | 0.71 | 1.60 |
| 1403 | 1,2 | 0.47 | 0.71 | 1.54 |
| 1415 | 1,2 | 0.45 | 0.84 | 1.87 |
| 1427 | 1,2 | 0.46 | 0.76 | 1.65 |
| 1442 | 1,2 | 0.46 | 0.78 | 1.70 |
| 1469 | 1,2 | 0.46 | 0.80 | 1.74 |
| 1607 | 1,2 | 0.46 | 0.92 | 2.02 |
| 1863 | 1,2 | 0.53 | 1.18 | 2.22 |
| 2069 | 1,2 | 0.53 | 1.33 | 2.51 |
| 2327 | 1,2 | 0.60 | 1.75 | 2.92 |
| 2496 | 1,2 | 0.62 | 1.75 | 2.82 |
| 2611 | 1,2 | 0.64 | 1.95 | 3.06 |
| 2751 | 1,2 | 0.70 | 2.22 | 3.19 |
| 3087 | 1,2 | 0.77 | 2.68 | 3.50 |
| 3369 | 1,2 | 0.83 | 2.85 | 3.42 |
| 3793 | 1,2 | 0.96 | 3.52 | 3.67 |
| 4202 | 1,2 | 1.17 | 4.31 | 3.68 |
| 4370 | 1,2 | 1.29 | 4.70 | 3.64 |
| 4823 | 1,2 | 1.56 | 5.53 | 3.55 |
| 5701 | 1,2,10 | 2.02 | 8.15 | 4.03 |
| 5740 | 1,2,10 | 1.97 | 4.39 | 2.23 |
| 5752 | 1,2 | 1.86 | 7.72 | 4.14 |
| 5779 | 1,2,10 | 2.02 | 8.20 | 4.06 |
| 5788 | 1,2,10 | 2.01 | 8.16 | 4.06 |
| 5800 | 1,2,10 | 2.03 | 8.32 | 4.10 |
| 5809 | 1,2,10 | 1.99 | 8.31 | 4.18 |
| 5916 | 1,2,10 | 2.11 | 8.55 | 4.04 |
| 6401 | 1,2,10 | 3.93 | 10.04 | 2.55 |
| 6929 | 1,2 | 5.81 | 11.00 | 1.89 |
| 8472 | 1,2,10 | **41.63** | 18.13 | **0.44** |
| 8530 | 1,2,10 | **53.56** | 18.90 | **0.35** |

\* cold start of the CUDA arm, not a warm measurement; the CPU arm's cold start was 2.45 s.

## Reading it

- **Neither backend wins.** A screen at 1–5k dofs should stay on CUDA (1.5–4x faster). A screen at 8k+ dofs
  should be on CPU, where the 8 GB card hits its cliff and then its memory ceiling.
- **Cold start matters**: 26.5 s vs 2.5 s. For short jobs (few designs, few frequencies) that alone can
  flip the total, which is why the sums here (164.4 vs 165.5 s) are nearly equal despite the medians.
- **Physics is identical**: max |dSPL| 3.6e-05 dB across all 40, so switching backend is safe for search.
- **Caveats**: one frequency (1 kHz), one design per dof value, and CPU cost is mesh-dependent (a separate
  8,044-dof MEH mesh measured 5.86 s/frequency where these 8.5k designs take ~18 s). Do not extrapolate to
  other frequencies or geometries without re-measuring.

## Reproduce

```powershell
.venv\Scripts\python.exe tools\bench\cuda_cpu_40designs.py --designs 40 --max-seconds 2400
```

Per-design rows land in `runs/bench_40designs_<UTC>/results.jsonl` (backend, mesh, dofs, tags, seconds,
spl0, peak VRAM) and a rolled-up `summary.json`.
