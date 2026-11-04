# WP1: skip the unused GPU identity cache on the fused CUDA route (proposal for the solver fork)

**Status: PROPOSAL, UNVERIFIED AGAINST SOURCE LINES.** Written 2026-11-04 in a container that does not contain the
solver fork. The line numbers and variable names below come from the throughput handoff packet
(`hornlab-beat-bem@1efdc6f934e16f288880b6d68e8dce8480b7a421`, `BeatEngineDriver.jl` ~1533-1535, 1639-1667,
1848-1881, 1997-2022, 2220-2221; `BeatEngineCore.jl` ~1417; `BeatEngineCudaBurtonMiller.jl` ~350-500). Nobody has
read those lines for this document. **Step 1 of the checklist below is to read them.** Nothing here has been run.
This is a change to Magnus's Julia code, so it follows `docs/FORKS.md` exactly (fork branch, commit, install by SHA,
pin, validate, evidence). It is NOT part of the Hornfab Python change set.

## Hypothesis (from the packet, not measured)

On the fused CUDA route the driver builds two dense GPU identity matrices (P1xP1 and P1xDP0, complex64) before it
decides to use fused assembly, and the fused assembler builds its own identity contribution, so the two dense
matrices are allocated and never read. Nominal bytes avoided: `8 * (N^2 + N*E)`; for N = 13,999, E = 27,578 that is
4.656 GB (4.337 GiB). **That is a memory estimate, not a measured saving and not a speedup.** Allocator reuse, Julia
GC and lifetimes can make the real peak difference smaller or larger.

## Proposed change (pseudo-diff, names unverified)

Goal: when the fused flag is on, do not construct the GPU identity cache. Everything else keeps today's code.

```julia
# BeatEngineDriver.jl, near the unconditional GPU identity-cache construction (~1639-1667).
# `fused_burton_miller_cuda` is the flag the packet names for the fused branch (~1848).
# BEFORE (shape, unverified):
#     identity_gpu_cache = build_gpu_identity_cache(identity_p1_p1, identity_p1_dp0)   # always
# AFTER:
identity_gpu_cache = if backend_is_cuda && !fused_burton_miller_cuda
    build_gpu_identity_cache(identity_p1_p1, identity_p1_dp0)    # unchanged for the standard CUDA path
else
    nothing                                                      # fused CUDA: never read, never built
end

# Every reader of the cache must tolerate `nothing`; the packet says the standard per-channel path (~1997-2022)
# reads it, and the fused branch (~1848-1881) does not. Add an explicit guard at each read site:
@assert identity_gpu_cache !== nothing "internal: GPU identity cache requested on the fused CUDA route"

# Release (~2220-2221): only release what was built.
identity_gpu_cache === nothing || release_identity_cache!(identity_gpu_cache)
```

Optional second step (separate commit, separate A/B, only if step 1 passes): the CPU identity matrices at
~1533-1535 may also be skippable on fused CUDA. Do not combine the two.

## Verification checklist (do in order; stop at the first failure)

1. **Read the source.** In the fork checkout (`C:\Users\hunte\Hrns\forks\hornlab-beat-bem`), at the pinned SHA, open
   the three files at the line ranges above. Confirm or correct: the flag name, the variable names, that the fused
   branch never touches the GPU identity cache, that nothing else (field evaluation, impedance, near correction,
   `source_profile_alpha`, WP17 near correction) reads it, and where it is released. Record what you found.
2. `grep -n identity` across `julia/` to list every reader/writer of both cached matrices, including
   `BeatEngineCore.jl` ~1417. Every reader must be on a non-fused path.
3. Branch in the fork from the current pin: `git checkout -b hornlab-search/wp1-fused-no-identity-cache`. Make the
   change behind no new flag (it is a pure no-op on every path except fused CUDA). Commit.
4. Fork tests: `julia/tests/runtests.jl`, including the four CUDA testsets, from a clean GPU state (CLAUDE.md
   hygiene: list and clear stale hosts, confirm `nvidia-smi` near idle).
5. Install by SHA (never editable), per `docs/FORKS.md` step 4. Do NOT change `pyproject.toml` yet.
6. A/B with the Hornfab harness, same mesh, one fresh process per arm, hosts cleared between arms (see commands).
7. Parity gate: `hornlab-search selftest --analytic` (spread <= 0.5 dB, reference 0.020 dB) and
   `selftest --crosscheck` (< 0.2 dB, reference 0.039 dB); and the A/B arrays below must match the old pin to
   within 1e-6 dB (expected bit-identical, because no arithmetic changed).
8. VRAM gate: peak live and reserved VRAM per arm, baseline recorded next to each peak; a near-limit mesh (the
   15,984-DOF ceiling mesh from `tools/measure_fused_ceiling.py`) still solves, and one failure injection
   (kill the host mid-solve) still recovers.
9. Only if 1-8 pass: bump the pin in `pyproject.toml` + `TOOLCHAIN.md`, write `docs/evidence/`, and adopt only if the
   measured benefit exceeds the variance (packet section 5, rule 7). Report a negative result honestly.

## A/B commands (Windows PowerShell, repo root; one arm per fresh process)

```powershell
# 0. hygiene first (CLAUDE.md): no stale hosts, VRAM near idle
.\.venv\Scripts\python.exe -m hornlab_search.cli gpu-clean
nvidia-smi --query-gpu=memory.used --format=csv

# 1. OLD pin: install it, then
.\.venv\Scripts\python.exe tools\bench\throughput_matrix.py --config examples\osse_baseline_fusedcuda.yaml `
    --mesh fixture=runs\<run>\designs\<hash>\mesh.msh --freq-sets 12 --batch-sizes default --warm-reps 3 `
    --out runs\wp1_old
# 2. NEW fork SHA: install it, hygiene again, then the same command with --out runs\wp1_new
# 3. Compare: medians in summary.csv (warm_median_s), smi_peak_mib_max / peak_vram_mib_max, and parity:
.\.venv\Scripts\python.exe tools\bench\compare_search_runs.py runs\wp1_old runs\wp1_new   # only for search runs
```
For the array parity use the same fixture in both runs and compare `response` arrays (the matrix keeps the last
rep's fingerprint in memory per arm; to compare ACROSS processes run `hornlab-search run` on the same config with
the old and new pin and use `hornlab-search compare`, tolerance 0.039 dB / 1 degree, as FORKS.md step 6.3 says).
Repeat the 12/25 sets and, last and only when safe, the 41-frequency set.

## Rollback

Reinstall the previous pin and restore the `pyproject.toml` line (FORKS.md step 8):
```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps --force-reinstall "git+https://github.com/llevaachingada/hornlab-beat-bem.git@1efdc6f934e16f288880b6d68e8dce8480b7a421"
```
No Hornfab code depends on this change, and no data written under the new SHA is mixed with the old: every record
carries `lib_shas`. Delete the fork branch if abandoned. Never reuse a SHA for different code.
