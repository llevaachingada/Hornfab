# BoTorch vs CMA-ES on the home horn — 15 Nov 2026

**Live page (interactive charts, light/dark):** https://llevaachingada.github.io/Hornfab/status/2026-11-15-bo-vs-cma/

Task: OSSE extended-throat home horn, brief `room_80x60_700_hf1440_v7` (objective v7; **lower J is better**).

## Verdict

**BoTorch wins under the pre-declared rule.** Median **verify** J 3.189 vs 3.827: a gap of 0.638, larger than both seed spreads (BoTorch 0.145, CMA 0.435).

| | |
|---|---|
| **3.107** | best verified horn (BoTorch s31001) |
| **0 / 3** | CMA arms that improved on their starting design in 60 solves |
| **+18 %** | how much worse CMA's best design scored when re-solved finer (screen 3.233 → verify 3.827) |
| **14–29 vs 0–3** | solves lost to "too large" refusals, CMA vs BoTorch |

## Setup

- **Same starting knowledge for both:** 185 solved designs from an earlier CMA run (best J 3.2328). BoTorch learns from all of them; CMA starts from the best one.
- **Equal budget:** 60 new screen solves + 6 verify solves per arm, 3 seeds per method, same GPU, solver pin and brief.
- **Methods:** BoTorch uses a Gaussian process (Matérn 5/2, per-knob length scales) + qLogNoisyExpectedImprovement over a 4096-design candidate pool that is pre-checked for size. CMA-ES uses σ₀ 0.15 from the prior best.

![Best-so-far per new solve](img/convergence.png)

![Screen vs verify](img/screen_vs_verify.png)

![Best verified horn per arm](img/best_verify.png)

| Arm | best screen J | best verify J | solved / refused | solves to beat start | run |
|---|---:|---:|---:|---:|---|
| BoTorch s31001 | 3.146 | **3.107** | 60 / 0 | 6 | `study-f269f257b24e00f2` |
| BoTorch s31002 | 3.090 | **3.251** | 60 / 0 | 23 | `study-24b6cdf8614ff2bc` |
| BoTorch s31003 | 3.242 | **3.189** | 60 / 3 | never | `study-82b9e51a51d7325c` |
| CMA s3101 | 3.233 | **3.827** | 31 / 29 | never | `20261115T052416Z-screen-cdbc27` |
| CMA s3102 | 3.233 | **3.827** | 44 / 16 | never | `20261115T085601Z-screen-0c9c90` |
| CMA s3103 | 3.233 | **3.392** | 46 / 14 | never | `20261115T105220Z-screen-e0be04` |

## What BoTorch found

- **A shorter, steeper throat extension:** all three BoTorch arms converged on about 110–127 mm at 4.3–4.8°, against the incumbent's 172 mm at 3.2°.
- **Independent confirmation:** CMA arm 3's best verified design went to the same region (120 mm).
- **Coverage is similar:** about 66 × 68–71° (1–8 kHz).

## Caveats

- **Warm start from an already-optimized horn.** The shared prior was a finished 200-design CMA run, and its best design (J 3.2328) is where two independent CMA seeds had already converged. CMA restarted from that converged point with a small step (σ₀ 0.15), so it had little room left in that basin; BoTorch's global model could jump to a different basin. This test answers "which method improves an already-optimized design?", not "which searches better from scratch". A cold-start comparison is still to do.
- **Narrow test:** one task, objective v7 and 3 seeds per method, warm-started from CMA data. A cold start was not tested.
- **Speed:** a BoTorch step takes about 73 s against about 55 s for CMA, because of the model refit. The comparison counts solves, not wall time.
- **Next:** the TuRBO (trust-region) and Pareto (coverage × ripple) BoTorch modes, tested the same way.

Data: [`data.json`](data.json).
