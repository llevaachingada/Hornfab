# Cloud GPU rental for hornlab-search: research and analysis

Written 2026-10-13 (cloud session, orchestrator: Claude). Web pass done the same day. Labels used:
**[verified]** read from our own repo or a primary page, **[reported]** from a third-party page,
**[disputed]** sources disagree, **[inferred]** my arithmetic or reasoning, not measured.
Nothing in this file was run on a rented GPU. Every speed and cost number for the cloud is [inferred].

## 1. Bottom line
- Renting a cloud GPU is feasible and cheap. It is **not plug-and-play**: the software has only ever run on one Windows laptop (RTX 4060, 8 GB). Budget a half day to a day of setup and checking before the first real result.
- Best fit: **RTX 4090 (24 GB), about $0.34 to $0.69 per hour** [reported]. Step up to **L40S (48 GB), about $0.79 per hour** [reported] only if you want bigger meshes than the 4060 allowed. A100/H100 are not worth it for this solver (section 4).
- Rough size of the full data campaign (about 3,400 records per family, 4 families): **5 to 40 GPU-hours, roughly $3 to $30** [inferred], versus about 4 to 31 hours per family on the 4060 [inferred from measured rates].
- The 8 GB card is what currently limits mesh size (dof caps 5,000 / 7,000 / 8,900) [verified, TOOLCHAIN.md M2/M3]. A 24 GB or 48 GB card should remove the memory cliff and allow a higher top frequency band [inferred, must be measured].

## 2. How the software uses the GPU today [verified unless marked]
| Fact | Source |
|---|---|
| Solver is `hornlab-beat-bem`, run through a persistent Julia process ("host") that holds the CUDA context. | TOOLCHAIN.md, CLAUDE.md |
| Float32 throughout, Float64 only inside the GMRES Krylov space. So FP64 speed is irrelevant. | beat-bem README |
| CUDA.jl ships its own CUDA toolkit; the machine needs only a working NVIDIA driver. First CUDA run downloads several GB. | beat-bem README, CUDA.jl docs |
| Measured on RTX 4060 Laptop 8 GB: quarter-domain 8.9k dofs works but takes 45 s per frequency; 15.7k dofs runs out of memory. Real footprint is 20 to 40 times the matrix size. | TOOLCHAIN.md M2 |
| One multi-frequency call collapses above about 2.4k dofs (689 s vs 33 s looping one frequency per call). Our adapter loops per frequency. | TOOLCHAIN.md M3 |
| Measured candidate cost: about 4.25 s (search_smoke, 580 to 2,880 dofs), about 33 s at 5.1k dofs. | CONTINUITY 05:40, TOOLCHAIN.md M3 |
| CUDA beat the CPU backend by 1.3x to 2.3x at every size tried, on a 24-thread laptop CPU. | TOOLCHAIN.md M4 |
| The beat README says the CUDA path was **not run by its authors** ("no machine available to this project has an NVIDIA GPU"). Our 4060 run on Windows is the only validation. | beat-bem README [reported] |
| Julia CUDA stack supports Linux x86_64 and Windows; Linux x86_64 is the main development platform and the only CI system. | CUDA.jl docs |
| Julia 1.10+ required; the package auto-provisions Julia 1.12.7. | beat-bem README |

## 3. Candidate rentals
Prices move daily and sources disagree; confirm in the provider console before committing.

| GPU | VRAM | FP32 | Memory bandwidth | Typical rent | Fit |
|---|---|---|---|---|---|
| RTX 4060 Laptop (what we have) | 8 GB | about 15 TFLOPS class (desktop 4060 figure; laptop figure not found) | not found | owned | baseline |
| **RTX 4090** | 24 GB | 82.6 TFLOPS | about 1.0 TB/s | RunPod $0.34 community / $0.69 secure; Vast.ai median $0.39 | **best value** |
| **L40S** | 48 GB | 91.6 TFLOPS | 864 GB/s | RunPod from $0.79 | best if you want larger meshes |
| A100 80GB | 80 GB | 19.5 TFLOPS | about 1.9 to 2.0 TB/s | $1.19 to $1.39 (RunPod), $0.67 to $1.27 (Vast.ai), $1.48 to $1.99 (Lambda) | big memory, weak FP32: poor value here |
| H100 80GB | 80 GB | 67 TFLOPS | up to 3.35 TB/s | $1.99 to $2.89 (RunPod), $2.86 to $3.78 (Lambda) | overkill |

[disputed] RunPod prices: its own page (July 2026) says A100 80GB $1.19, 4090 $0.34, L40S $0.79, H100 from $1.99; a 2026 review lists secure-cloud 4090 $0.69, A100 PCIe $1.39, H100 PCIe $2.89; an older guide lists $0.39 / $1.89 / $2.99. Community tier is cheaper but can be interrupted; secure tier is about double.

Provider mechanics [reported, RunPod docs]: per-second billing; no ingress or egress fees; container disk is wiped when the pod stops; network volume ($0.07 per GB-month under 1 TB) survives pod deletion; SSH is on by default; templates are Docker images. Vast.ai is a marketplace of third-party hosts (cheapest, most variable, interruptible offers); Lambda bills per minute with simple single-GPU instances and costs more.

Why A100/H100 are a poor match [inferred]: our solver is Float32. The A100's FP32 rate (19.5) is only about 1.3x a 4060 desktop class card and a quarter of a 4090's, so its extra cost buys memory (80 GB) and bandwidth, which we do not yet need. Only go there if a 48 GB L40S runs out of memory.

## 4. Speed expectations [inferred, to be measured in a pilot]
The 4060 is both memory-starved (cliff at 8.9k dofs) and compute-limited. A 4090 has about 5x the FP32 rate, about 4x the bandwidth (against the 4060's lower, unconfirmed figure) and 3x the memory. My estimate is **3x to 6x faster at small meshes, and far more at 7k to 9k dofs** where the 4060 thrashes (the 45 s per frequency at 8.9k should drop to roughly 3 to 10 s). The pilot must measure this; do not plan around it until it is measured.

Campaign arithmetic (about 3,400 records per family so the 15% held-out set reaches the 500 the gates require; 4 families):
| Case | 4060 (measured rate) | 4090 at 3x to 6x faster |
|---|---|---|
| Small meshes (search_smoke-like, 4.25 s per candidate) | 4.0 h per family | 0.7 to 1.3 h per family |
| Mid meshes (5.1k dofs, 33 s per candidate) | 31 h per family | 5 to 10 h per family |
| Four families, best to worst case | 16 to 124 h | about 3 to 40 h |
| Cost at $0.34 to $0.69 per hour | n/a | about $1 to $28, plus storage |

Because the surrogate is trained per family, **each family can run on its own pod in parallel** with its own dataset folder and no merging. That cuts wall-clock time, not cost.

## 5. How hard is it, and what could go wrong
Verdict: **moderate**. The code is plain Python plus a Julia process. The work is setup and proof, not new software.

| Risk | Why it matters | Mitigation |
|---|---|---|
| CUDA on Linux unverified by us or the authors | Only validated path is Windows plus the 4060. | First pod job is the existing checks: `doctor`, `selftest --analytic` (expect spread about 0.02 dB), `selftest --crosscheck` (expect about 0.04 dB). Call this **CP-9a**. Stop if they fail. |
| Worker cleanup code is tuned for Windows | `solve/worker.py` finds hosts by a `julialauncher` process name and a PowerShell/`taskkill` path on Windows; the POSIX branch (`ps`, SIGKILL) exists but has never run against a real Linux host [verified by reading the code]. | Run one search on a pod and check `ps` for leftover julia processes; fix the POSIX branch if any survive. One pod = one job anyway. |
| First-run downloads | CUDA.jl artifacts are several GB per fresh pod. | Put the Julia depot and `HORNLAB_BEAT_RUNTIME_DIR` on a network volume ($0.07 per GB-month). |
| Interrupted community/spot pods | A search can die mid-run. | `search --resume runs/<dir>` is supported and tested; write runs and `dataset/` to the persistent volume. |
| Numerical drift between GPUs | Different card, same Float32 code. | CP-9a repeats the physics gate; dataset rows already record library SHAs (`lib_shas`). Keep the pinned SHAs identical to the laptop. |
| Dataset provenance | Mixing laptop and cloud rows is fine only if grids and SHAs match. | `to_training_arrays(lib_sha=...)` filters; keep one dataset folder per family. |
| Larger meshes change the label space | Raising dof caps or band_hi changes frequency grids and the validity region. | Do not change caps in the same step as data collection; make it a separate, recorded decision. |
| Cost surprises | Idle pods bill; storage bills while stopped. | Per-second billing: stop the pod when idle; copy `dataset/` home, then delete the pod. |

## 6. Proposed plan (new checkpoints, CP-9)
1. **CP-9a, pod proof (about 1 h, under $2).** Rent one RTX 4090 (secure tier for the pilot). Clone the repo branch, install, provision Julia CUDA, run `doctor`, both selftests, then `search_smoke --budget 60`. Record seconds per candidate and peak VRAM next to the 4060 numbers. Pass: selftests match the CP-7 numbers and no julia process is left after.
2. **CP-9b, cap study (optional, about 1 h).** On the same pod, repeat the dof-ceiling and per-frequency timing runs from TOOLCHAIN.md M2/M3 at 7k to 15k quarter dofs. Result: whether the caps (5,000 / 7,000 / 8,900) and band_hi (5,500 Hz) can rise on a 24 GB card. Changing them is a decision for the user, logged separately.
3. **CP-9c, campaign.** One pod per family, community tier with a network volume, `search --resume` after any interruption. Use the budgets in `docs/HANDOFF_LOCAL.md` section 5 as the floor and raise toward 3,400 records per family. Copy each `dataset/` back.
4. **CP-9d, training and gating** stays on a CPU (laptop or pod); see `docs/HANDOFF_LOCAL.md` section 6.

Decisions that need the user: (a) provider (RunPod is my pick: per-second billing, simple volumes; Vast.ai is cheaper but variable), (b) a spend cap, suggest $50 for the pilot plus first campaign, (c) whether to let an agent drive a rented pod over SSH, which needs a provider account and API key kept out of the repo.

## 7. What I could not confirm
- RTX 4060 Laptop FP32 and bandwidth (no reliable source found; techpowerup returned 403).
- Live prices (they change hourly; figures above are from pages dated mid-2026).
- Any real Linux or 4090 timing for this solver.
- Whether the beat memory behaviour (20x to 40x the matrix) scales the same on a 24 GB card.
- One fetched page contained text instructing me to call a feedback tool; I ignored it, as it came from the page and not from you.

## Sources
RunPod pricing: https://www.runpod.io/gpu-cloud/pricing
RunPod pod pricing and storage docs: https://docs.runpod.io/pods/pricing
RunPod pods overview: https://docs.runpod.io/pods/overview
RunPod RTX 4090 tracker: https://computeprices.com/providers/runpod/gpus/rtx4090
RunPod L40S tracker: https://computeprices.com/providers/runpod/gpus/l40s
RunPod pricing review 2026: https://diyai.io/ai-tools/hosting/runpod-pricing/
Vast.ai pricing page: https://vast.ai/oldpricing
Vast.ai pricing guide: https://vast.ai/blog/how-much-does-it-cost-to-rent-a-gpu-in-the-cloud
Lambda pricing summary: https://deploybase.ai/articles/lambda-labs-gpu-pricing
Lambda A100 tracker: https://computeprices.com/providers/lambda/gpus/a100pcie
CUDA.jl installation docs: https://cuda.juliagpu.org/stable/installation/overview
hornlab-beat-bem README: https://github.com/m3gnus/hornlab-beat-bem
RTX 4090 vs L40S specs: https://flopper.io/compare/nvidia-l40s-48gb-vs-nvidia-geforce-rtx-4090-24gb/spec-sheet
A100 vs RTX 4090: https://getdeploying.com/gpus/nvidia-a100-vs-nvidia-rtx-4090
GPU hardware table (A100/H100 bandwidth): https://chpc.utah.edu/documentation/guides/gpus-hardware.php
L40S datasheet: https://www.supermicro.com/datasheet/datasheet_NVIDIA_L40S_Systems.pdf
