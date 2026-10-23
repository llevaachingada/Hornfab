# Next development round: priorities (after the beta)

Written 2026-10-22 22:35 EDT by the local orchestrator, at the user's request. **Read this before planning any work
after the beta session.** Items are in priority order. Background: `docs/HIGH_FREQUENCY_OPTIONS.md` (2026-10-13),
`docs/CLOUD_GPU_REPORT.md`, `TOOLCHAIN.md` M2/M3.

## P1 (top priority). Fused / direct CUDA Burton-Miller assembly in the exterior driver

**Why it matters.** The 8 GB RTX 4060 runs out of memory between 8.9k (works, 74 s per frequency under memory
pressure) and 15.7k (OOM) quarter-domain dofs (`TOOLCHAIN.md` M2). That ceiling, not the card, is what holds screening
at 5.5 kHz for large horns. The solver already has a memory-saving path that forms the Burton-Miller combination in
one matrix (about 6x less operator memory), but it is switched off for CUDA. Turning on an equivalent for CUDA should
lift the ceiling to about 20k quarter dofs [inferred], i.e. about 12.6 kHz at epw 6 even on the large OSSE seed, and
make 7k–9k-dof solves much faster (less memory pressure).

**Evidence (pinned `hornlab_beat_bem` 0.2.0, installed under `.venv\Lib\site-packages\hornlab_beat_bem`).**
- `julia/BeatEngineDriver.jl` ~line 1215: `fused_burton_miller = beat_backend in (:cpu, :metal) && near_selection
  === nothing && ...` — the fused path is CPU and Metal only.
- A CUDA single-matrix assembler exists: `julia/src/BeatEngineCudaBurtonMiller.jl:350`,
  `assemble_burton_miller_neumann_system_cuda` (re-exported in `julia/src/BeatEngineCore.jl:85, 1357`). Only
  `julia/tests/runtests.jl` (lines ~1214, ~1300) calls it; the exterior driver never does.
- The package states its CUDA path was never run by its authors (no NVIDIA hardware); our 4060 is its only
  real-world validation. `hornlab_beat_bem/config.py` also documents a CUDA-specific silent-error hazard (single
  image-near cache under multi-image symmetry), so CUDA changes need extra care.

**It is NOT a flag flip.** Adding `:cuda` to that condition routes into the fused pair-kernel path, which is not the
CUDA assembler. The work is to call the CUDA direct-system assembler from the exterior driver and make sure it:
1. handles our quarter-domain symmetry images (`yz+xz`) exactly as the current CUDA path does;
2. applies the same singular corrections (near-correction stays refused on CUDA, as today);
3. keeps the same excitation (unit acceleration on tag 2) and output conventions (exp(−iωt));
4. keeps the per-frequency call pattern our adapter uses (`solve/beat.py`, TOOLCHAIN M3).

**Ownership.** This is Magnus's package (CLAUDE.md hard rule: we never modify installed HornLab/BEAT/Julia files).
Route: (a) ask Magnus (m3gnus) to wire it upstream, offering the 4060 as the test bed and our TOOLCHAIN numbers; or
(b) with his OK, a pinned fork of `hornlab-beat-bem` under our control, with the SHA recorded in `pyproject.toml` and
`TOOLCHAIN.md` and `doctor`'s pinned-SHA check updated.

**Validation before any data from it counts (all on the GPU, from a clean state).**
1. `hornlab-search selftest --analytic`: spread ≤ 0.5 dB (today 0.020 dB).
2. `hornlab-search selftest --crosscheck` vs `bempp_cpu`: < 0.2 dB (frozen CP-7b rule; today 0.039 dB).
3. A/B against today's CUDA path on the same meshes (osse_axi seed, perturbed_osse_hv best, freeform_sculpt seed):
   `hornlab-search compare` within the 0.039 dB noise floor and ≤ 1° beamwidth.
4. Memory ceiling re-measured as in `TOOLCHAIN.md` M2 (VRAM baseline recorded, one solve per fresh process).
5. Records carry the new library SHA, so old and new solver data never mix silently (`lib_shas` filter).

**Decision recorded 2026-10-22.** The overnight queue of 2026-10-22/23 (epw-8 screen, compare tier, OSSE top-up,
sculpt searches) stays on the current verified CUDA path, so the compare tier and the surrogate data come from one
solver. Do not enable P1 mid-campaign.

## P2. High-frequency finalist pass at 12 kHz on the 4060 (no solver change)

Typology horns are small: measured 700–1,400 quarter dofs at 5.5 kHz, so about 3.3k–6.8k at 12 kHz (dofs scale with
f²), inside the 8.9k ceiling. Add 12 kHz briefs and a `verify` pass for the top designs only (about 1–5 min per
design). Prerequisite: the epw-convergence check above 2.5 kHz (`docs/HANDOFF_BETA.md` item C2; the overnight queue's
epw-8 screen feeds it). Physics caveat for every report: above the throat's first cross mode (about 7.9 kHz for a
1-inch exit) a real compression driver is not a uniform cap, so 8–12 kHz results compare geometries, not drivers.
A 12 kHz brief is a separate frequency grid: its records form their own group (already kept apart by the grid check).

## P3. Apple Silicon (Metal) backend for the collaborator's MacBook

`hornlab_beat_bem` supports `metal` (`config.py` `BEAT_BACKENDS`), with the fused path ON, and unified memory holds
dense systems far beyond 8 GB. Our layer only exposes `beat_cuda`, `beat_cpu`, `bempp_cpu`: add a `beat_metal`
backend option, macOS process hygiene (`search/hygiene.py` POSIX branch), then on the Mac: `doctor`, both selftests,
and the same 3-design A/B against the 4060 (< 0.2 dB) before mixing data. Metal has no near-correction (same as CUDA
under symmetry).

## Not recommended (recorded so nobody re-proposes it without new evidence)
- Half precision or other "quantization" of the BEM system: the solver is Float32 with a Float64 Krylov space; dense
  high-frequency BEM systems are poorly conditioned.
- Lowering epw below 6 without a measured convergence check.
- GPU memory oversubscription to system RAM: Linux-only, and a dense factorisation over PCIe crawls.
- Fewer high-frequency sample points: saves time, not peak memory.

## Fallback
Cloud RTX 4090 (24 GB, about $0.34–0.69/h) or L40S (48 GB, about $0.79/h): `docs/CLOUD_GPU_REPORT.md` CP-9a pod proof
first (Linux CUDA never run with this solver).
