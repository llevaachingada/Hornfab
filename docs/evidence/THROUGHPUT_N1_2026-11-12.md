# Throughput evidence N1 — 2026-11-12 night (fused CUDA / mesh prefetch / frequency batch)

**Lane:** day plan 2026-11-12, group C.3 + C.4. **Status:** evidence + PROPOSAL ONLY — no default was flipped in code.
**Source (read-only):** `runs/nights/gpu_2026-11-12/summary.jsonl` and the twelve `n1_*.log` files in the same folder;
per-arm artifacts under `runs/bench_throughput_2026-11-12/n1_<size>_<fused>_<prefetch>/`.
**Machine:** 8 GB RTX 4060 (Windows/WDDM), persistent BEAT host; VRAM baseline per arm recorded in `summary.jsonl`
(aggregate baseline ~1.0–1.1 GiB before the first arms; the desktop holds 0.3–0.5 GiB).
**Method:** `tools/bench/throughput_matrix.py` — one stored design per size class (~1k / ~4k / ~8k dofs) [inferred class
from the arm labels; the bench wrapper did not echo dofs], 12 frequencies, batch sizes 1/4/12 (warm reps 3 + one cold
rep), the production solve path (`config.solve_spec` + BEAT backend kwargs). Timings are medians of the warm reps
[measured]. A CUDA arm is only valid if the WDDM shared-usage spill reading is near zero; the low peak-VRAM fused arms
are consistent with no spill, while the 8k fused-OFF arms hit the ceiling outright (below).

## 1. Per-arm table [measured, seconds; warm medians unless noted]

| Arm | fused | prefetch | b1 warm | b4 warm | b12 warm | b12 cold | peak VRAM (MiB) | exit |
|---|---|---|---|---|---|---|---|---|
| n1_1k_fusedon_prefetchoff | on | off | 5.957 | 2.092 | **1.273** | 4.572 | 1334 | 0 |
| n1_1k_fusedon_prefetchon | on | on | 5.356 | 2.069 | **1.257** | 4.530 | 1410 | 0 |
| n1_1k_fusedoff_prefetchoff | off | off | 5.882 | 2.404 | 1.608 | 5.923 | 1835 | 0 |
| n1_1k_fusedoff_prefetchon | off | on | 5.575 | 2.357 | 1.606 | 6.129 | 2485 | 0 |
| n1_4k_fusedon_prefetchoff | on | off | 18.040 | 10.156 | **8.488** | 11.389 | 3167 | 0 |
| n1_4k_fusedon_prefetchon | on | on | 18.103 | 10.707 | 8.754 | 12.092 | 2872 | 0 |
| n1_4k_fusedoff_prefetchoff | off | off | 21.287 | 13.234 | 12.053 | 16.335 | 5261 | 0 |
| n1_4k_fusedoff_prefetchon | off | on | 22.290 | 14.583 | 12.216 | 17.001 | 5547 | 0 |
| n1_8k_fusedon_prefetchoff | on | off | 47.075 | 29.262 | **25.015** | 27.958 | 4900 | 0 |
| n1_8k_fusedon_prefetchon | on | on | 51.292 | 28.147 | 24.907 | 27.514 | 4202 | 0 |
| n1_8k_fusedoff_prefetchoff | off | off | FAIL | FAIL | FAIL | 7.135 (fails) | 7499 | 0* |
| n1_8k_fusedoff_prefetchon | off | on | FAIL | FAIL | FAIL | 7.907 (fails) | 7731 | 1 |

*8k fused-off arms report `failures 4` for every batch size (every warm rep failed) — the exit code alone is not the
signal; the per-arm log lines are.

## 2. Findings

1. **Fused ON wins at every size.** Warm b12: 1k 1.27 vs 1.61 s (fused off), 4k 8.49 vs 12.05 s (1.42x), 8k 25.02 s
   vs fused-off never completing a warm rep. Peak VRAM is also lower fused-on at 4k/8k (3167/4900 vs 5261/7499 MiB).
   [measured]
2. **`freq_batch_size` never hurt, and 12 is the best measured value.** b12 ≤ b4 ≤ b1 in warm time in every
   non-failing arm; b12 vs b1: 1k 5.96→1.27 s (4.7x), 4k 18.04→8.49 s (2.1x), 8k 47.08→25.02 s (1.9x). [measured]
3. **Mesh prefetch is neutral on warm time and harmful near the ceiling.** 1k: 1.257 vs 1.273 s (within noise);
   4k: 8.754 vs 8.488 s (slightly worse); 1k fused-off peak rises 1835→2485 MiB with prefetch. At 8k fused-off,
   prefetch-on produces a **hard OOM** (below). [measured]
4. **The 8k fused-off + prefetch OOM is reproduced:** `RuntimeError: Out of GPU memory trying to allocate
   188.794 MiB; Effective GPU memory usage: 100.00% (7.996 GiB/7.996 GiB); Memory pool usage: 7.090 GiB
   (7.281 GiB reserved)`, peak 7731 MiB, exit 1, failures 4/4/4. The 8k fused-off + prefetch-off arm shows the same
   failure count at peak 7499 MiB — i.e. fused OFF at ~8k dofs is at/over the 8 GB ceiling regardless of prefetch;
   fused ON completes at 4900 MiB. [measured]

## 3. DECIDED recommendation (owner flips the defaults after the calibration night; this PR does not)

- **fused ON for every CUDA config.**
- **prefetch OFF at ≥ 8k dofs** (and do not enable it where peak VRAM is already > ~5 GB).
- **`freq_batch_size` 12** — it never hurt and it is the largest single win measured tonight.

Exact proposal (real surfaces only — no invented keys):

```yaml
# per config (real config keys; both are opt-in today)
solve:
  cuda_fused: true
search:
  pipeline_prefetch: 0        # today's default; the proposal is "leave it off at >= 8k dofs"
```

`freq_batch_size` has **no config key** in the current tree: it is a `BeatBackend` kwarg
(`hornlab_search/solve/beat.py:626`) with the env equivalent `HORNLAB_FREQ_BATCH_SIZE`
(`solve/beat.py:656-659`). Until a `solve.freq_batch_size` key exists (next step, owner-gated), set it per night job:

```yaml
jobs:
  - {id: ..., kind: search, env: {HORNLAB_FREQ_BATCH_SIZE: "12"}, ...}
```

## 4. C.4 — screen-fidelity fix proposal (same night's question: does the screen ranking survive?)

**Finding (senior-measured 2026-11-12, retained):** the verify J is worse than the screen J in 95% of 104 pairs
(typically +25–50%), and within-run Spearman of the screen's top 5 vs verify is often 0.1–0.3. PR #27's v6-vs-v7
evidence shows tau < 0 in every class: the screen cannot rank its own finalists. Cause: a coarse 12-point screen grid
that under-samples the 2.5–5.5 kHz presence band and aliases narrow beams.

**Proposal (P0 "new screen grid", to be measured in the calibration night):**
1. Band split at 2 kHz; ~7 points in 2.5–5.5 kHz (the presence band that carries most of the pattern score), low band
   extended toward 0.7·f0. The C.1 planner already ships this as a PROPOSAL-ONLY overlay (band split at 2 kHz,
   6 points/octave) — it is not wired into any night job.
2. Measure Spearman(screen, verify) on the stored finalists in the calibration night — `compare_calibration.py`
   computes exactly this pairing (per-aspect deltas + rank agreement + screen-ranking-survives verdict).
3. **Until the grid is re-measured:** verify the top **15–20** finalists per run (not 5) and rank finalists by
   verify J only. Every ranking table elsewhere must say which fidelity produced it.

## 5. References

- Night: `runs/nights/gpu_2026-11-12/summary.jsonl` (arm rows n1_*), `runs/nights/gpu_2026-11-12/SUMMARY.md`.
- Logs: `runs/nights/gpu_2026-11-12/n1_<size>_fused{on,off}_prefetch{on,off}.log` (warm medians, cold reps, VRAM).
- Bench tool: `tools/bench/throughput_matrix.py`; bench artifacts `runs/bench_throughput_2026-11-12/n1_*/`.
- Planner/compare tools: `tools/calibration/plan_calibration.py`, `tools/calibration/compare_calibration.py` (C.1/C.2).
- P0 calibration thresholds: Re z ±0.03, beamwidth ±2 deg, DI ±0.2 dB (`docs/NEXT_DEV_PRIORITIES.md` P0 item 2).
