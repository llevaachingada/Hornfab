# Reaching 12 kHz on the 8 GB card: options and evidence

Written 2026-10-13 (cloud session, orchestrator: Claude). Labels: **[verified]** read in our repo or the solver source
(`hornlab-beat-bem` at the pinned SHA 38544d2, read-only clone), **[reported]** from a web page, **[inferred]** my
arithmetic, **[unverified]** from memory or not checked. Nothing here was run on a GPU.

## 1. Bottom line
- The 5.5 kHz ceiling is **our throughput cap, not a hard limit of the card**. The cap (5,000 quarter dofs) came from
  timing; the measured out-of-memory ceiling is between 8.9k (works) and 15.7k (fails) quarter dofs [verified, TOOLCHAIN.md M2].
- **Top frequency depends on horn size.** Dofs scale with surface area over element size squared. The shipped seed is a
  large horn (quarter area 0.282 m2); a smaller horn reaches 12 kHz inside the existing caps (table in section 3).
- Biggest unused lever: **the CUDA path in the pinned solver assembles four separate dense operators; the memory-saving
  "fused" path (6x less operator memory) is switched on only for CPU and Metal** [verified, `BeatEngineDriver.jl`
  line ~1217: `fused_burton_miller = beat_backend in (:cpu, :metal) && ...`]. A tested CUDA single-matrix assembler
  (`assemble_burton_miller_neumann_system_cuda`) exists in the library but the exterior driver never calls it [verified by grep].
  Wiring it in should lift the GPU ceiling from about 9k to about 20k quarter dofs [inferred]. That is a change to
  Collin's package, so it needs his OK or a pinned fork of ours (hard rule 1).
- "Swapping" GPU memory to RAM is **not** a practical fix (section 4).

## 2. The local agent's explanation: what holds up
| Claim | Verdict |
|---|---|
| Small meshes give many candidates per hour; bigger ones are much slower (45 s per frequency at 8.9k vs 2.8 s at 5.1k) | Accurate [verified, TOOLCHAIN.md M3] |
| One solve at a time, margin kept for the desktop (~0.4 GB), worker reserves ~1.7 GB | Accurate [verified] |
| Memory column "actually needed" (1.3 / 5.6 / 7.5 GB) | **Imprecise.** TOOLCHAIN.md defines those as peak minus baseline including the worker's memory pool, an upper bound, not the need |
| "Filling the card means bigger meshes, which are dramatically slower" | True at 8.9k, but part of that slowdown is memory pressure, which the fused path would relieve [inferred] |
| Frames 5.5 kHz as unavoidable for this hardware | **Incomplete.** It is the cap for the current (large) seed horn and an unfused CUDA path; see sections 3 and 5 |
| Options list (parallel solves, raise caps, re-test the one-frequency cliff, CPU hybrid, rent a GPU) | Reasonable, but it misses the fused-path finding and the horn-size effect |

## 3. What 12 kHz costs (quarter domain, epw = elements per wavelength) [inferred from `mesh/sizing.py` constants]
Dofs needed at 12 kHz:
| Quarter area of horn | epw 6 | epw 5 | epw 4 |
|---|---|---|---|
| 0.282 m2 (shipped seed, about 0.8 x 0.64 m mouth) | 19,000 | 13,200 | 8,450 |
| 0.150 m2 | 10,100 | 7,000 | 4,500 |
| 0.100 m2 | 6,700 | 4,700 | 3,000 |
| 0.050 m2 | 3,400 | 2,300 | 1,500 |

Highest frequency reachable (kHz), shipped seed, by dof budget:
| Dofs | epw 6 | epw 5 | epw 4 |
|---|---|---|---|
| 5,000 (today's screen cap) | 6.2 | 7.4 | 9.2 |
| 8,900 (today's verified OOM-safe maximum) | 8.2 | 9.9 | **12.3** |
| 21,000 (if fused CUDA worked) | **12.6** | 15.1 | 18.9 |

Caveat: epw 6 vs 18 was validated only up to 2.5 kHz (CP-7c: 0.29 deg, 0.028 dB). epw 4 and any band above 2.5 kHz are **unmeasured**.

## 4. Options, ranked
| # | Option | Reaches 12 kHz? | Effort | Risk | Evidence |
|---|---|---|---|---|---|
| 1 | **Check your real horn size.** A mouth of about 0.3 to 0.5 m wide already fits 12 kHz at epw 6 within 7,000 dofs | yes, if horn is small | none (config) | low | section 3 [inferred] |
| 2 | **High-band verify pass at 8,900 dofs with epw 4 to 5** on a few frequencies (about 45 s each) for finalists only | seed size: 9.9 kHz (epw 5), 12.3 kHz (epw 4) | new YAML, no code | accuracy of epw 4 unknown; needs a CP-7c-style test | [inferred] |
| 3 | **CPU backend for the high band** (`--backend beat_cpu`). No VRAM limit; fused path is already on for CPU; 32 GB RAM holds a 19k-dof dense matrix (~3 GB) easily | yes, seed size at epw 6 | config only | slow: roughly 5 to 15 min per frequency at 19k dofs, so 1 to 3 h per finalist [inferred from 57 s at 8.9k CPU] | beat README, TOOLCHAIN.md M4 |
| 4 | **Wire the fused/direct CUDA assembler into the exterior driver** (6x less operator memory, 2.45x more dofs) | yes, on the GPU | moderate Julia change in Collin's package | CUDA path never run by its authors; needs his OK or our own pinned fork; I cannot test it here | beat README (fused numbers), driver source [verified] |
| 5 | **Coarser rear/outer shell** (`res_mm_for` sets rear = mouth resolution today) | helps all of the above by an unknown fraction | small, in our code | small accuracy change, must be measured | `mesh/sizing.py` [verified] |
| 6 | **Band-split evaluation** (cheap mesh for low band, fine mesh only for a few high frequencies) | speeds up, does not lift the memory cap | high; touches the frozen frequency grid and dataset label space | decision needed | [inferred] |
| 7 | **Swap GPU memory to RAM** | no | high | CUDA unified-memory oversubscription is Linux-only; on Windows neither TCC nor WDDM mode supports it [reported]; our Julia code allocates plain device arrays; dense LU thrashes over PCIe | NVIDIA forum threads |
| 8 | **Fast multipole (bempp-cl + Exafmm)**: O(N) memory, double precision, CPU | only needed above about 60k dofs | high research | Burton-Miller support unconfirmed [unverified] | arXiv 2103.01048 |
| 9 | Rent a bigger GPU | yes | see CLOUD_GPU_REPORT.md | cost | |

Recommended order: 1 (free), then 2 or 3 as a **finalist verification pass** (search stays below 5.5 kHz, high band is checked afterwards), and ask Collin about 4 with our evidence. Skip 7.

## 5. Physics caveats for anything above 5.5 kHz
- The solver drives a **uniform plane source on the throat** with rigid walls [verified, TOOLCHAIN.md C5]. The first non-planar throat mode (f11, about 5.65 kHz for the 0.7 in throat case) is above today's band. Above f11 a real compression-driver exit is not a uniform piston, so 6 to 12 kHz results show the geometry's behavior with an idealized source, not the driver's. Treat them as relative comparisons.
- The 0.039 dB noise floor (CP-7f) was measured below 2.5 kHz for discretization; above that it is unmeasured.
- Changing band_hi, caps or epw changes the frequency grid and the validity region, so those runs form a **new dataset family**. Do not mix them into the current surrogate training set (`to_training_arrays` drops records on a different grid).

## 6. Proposed checkpoints (CP-10, none run)
1. **CP-10a, size check (no GPU):** run `f_max_for_dofs` with the real horn's quarter area; report the reachable band per cap and epw.
2. **CP-10b, epw accuracy:** repeat the CP-7c comparison on the low band for epw 4 and 5 against the epw 18 reference; pass if beamwidth error under 2 deg and DI error under 0.3 dB.
3. **CP-10c, high-band verify prototype:** a new `examples/*_highband.yaml` with band_hi 12,000 for `verify`, on CPU first, one finalist, record time per frequency and RAM.
4. **CP-10d, upstream question to Collin:** wire the CUDA direct-system path into the exterior driver; offer our 4060 numbers as the test bed.

## Sources
beat-bem README (fused Burton-Miller, memory numbers, env vars): https://github.com/m3gnus/hornlab-beat-bem
beat-bem CUDA engine doc (read in the pinned clone): https://github.com/m3gnus/hornlab-beat-bem/blob/38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0/docs/beat-engine-CUDA.md
beat-bem driver, fused path condition (pinned SHA): https://github.com/m3gnus/hornlab-beat-bem/blob/38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0/hornlab_beat_bem/julia/BeatEngineDriver.jl
Bempp-Exafmm workflow paper: https://arxiv.org/abs/2103.01048
bempp-cl Exafmm API: https://bempp-cl.readthedocs.io/en/latest/docs/bempp_cl/api/fmm/exafmm/index.html
CUDA unified memory oversubscription is Linux-only (forum): https://forums.developer.nvidia.com/t/virtual-memory-paging-support-for-pascal-gpus-on-windows-10-with-wddm-2-0-model/56347
CUDA.jl installation docs: https://cuda.juliagpu.org/stable/installation/overview
Repo evidence: TOOLCHAIN.md (M2, M3, M4, C5), hornlab_search/mesh/sizing.py, NOTES_FOR_SENIOR.md task-09
