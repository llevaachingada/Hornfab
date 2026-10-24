# Report 3. Analysing horns to 12 kHz (and beyond): GPU, CPU, and smarter physics

Senior pass, 2026-10-24. Builds on `docs/HIGH_FREQUENCY_OPTIONS.md` (2026-10-13), `NEXT_DEV_PRIORITIES.md`,
`docs/evidence/HF12K_VERIFY_2026-10-23.md`, `TOOLCHAIN.md` M2–M4, the solver source in `.venv`, and Appendix B
(Sonnet methods survey). Labels as in Report 1.

## 0. Bottom line

1. **For horns sized to the current 1-inch briefs, 12 kHz already fits the 4060, and so does a 12 kHz *search*, not
   just verify.** Measured at 12 kHz: 3,527 dofs (axi 90×90, epw 6), 4,540–4,655 (hifi 90×60, epw 6), 31–83 s per
   design for 25 frequencies. A 12-frequency screen to 12 kHz is about 25–35 s per candidate [inferred from M3's
   per-frequency curve], versus about 6 s at 5.5 kHz today: about 75 min for a 150-evaluation run. The briefs'
   comment "never search at 12 kHz on 8 GB" is wrong for these sizes.
2. **For large horns (the 0.8 m OSSE seed), the limit is a measured live footprint of about 80·N² bytes in the
   non-fused CUDA path.** The fused single-matrix path needs about 8–16·N², so the ceiling goes from ~9k to
   ~20k quarter dofs. **We now do this ourselves in our fork** (owner decision 2026-10-24, `docs/FORKS.md`; plan
   WP15). It is mostly driver wiring, because the CUDA assembler already handles our symmetry images and is
   tested. Until it is validated, use `beat_cpu` (fused is already on for CPU) for large-horn finalists: about 6–9 min
   per frequency at 19k dofs [inferred], so run them overnight.
3. **Two physics-side shortcuts beat any memory trick:** (a) **axisymmetric BEM** for the axisymmetric families. Only
   the m = 0 azimuthal mode is excited by a uniform cap, so it is a 1-D boundary integral with a few hundred unknowns
   at 20 kHz: milliseconds per frequency on a CPU. (b) **Band-split meshing**: the low frequencies don't need the
   12 kHz mesh. It does not change the frequency grid (contrary to `HIGH_FREQUENCY_OPTIONS.md` option 6), only which
   mesh solves which frequency.
4. Above 12 kHz the binding problems become **frequency sampling** (≥ 6–8 points/octave to see mouth structure) and
   **the source model above f11 = 7.9 kHz**, not memory.

## 1. Memory model of the current CUDA path (why ~9k is the wall)

From `TOOLCHAIN.md` M2 (clean-state, one frequency):

| case | dofs N | used at peak or OOM, minus ~1 GB context | bytes per N² |
|---|---|---|---|
| quarter, ok but 74 s | 8,941 | ≈ 6.5 GB | **≈ 81** |
| full, OOM | 9,193 | ≈ 6.4 GB live when an 8N² alloc failed | **≈ 76** |

So **live footprint ≈ 80·N² bytes** [inferred from the two rows above; CUDA.jl retries GC/reclaim before raising OOM,
so the arrays were live]. The non-fused path keeps, among other things, four operators in split real/imaginary
Float32 [verified, `julia/src/BeatEngineCudaAssembly.jl:71-78`]: single-layer and adjoint at N × N_faces
(N_faces ≈ 2N) and double-layer and hypersingular at N × N. That is 48·N² before the system matrix, LU and
intermediates. Usable ≈ 6.5 GB, so `N_max ≈ √(6.5e9/80) ≈ 9.0k`, which matches "8.9k works, 15.7k OOM".

The fused path (`assemble_burton_miller_neumann_system_cuda`, `BeatEngineCudaBurtonMiller.jl:350`) stores one
`2 × N × N` Float32 matrix and factors in place (`lu!`, line 646). With a 2× safety factor, ~16·N², so
`N_max ≈ 20k`. It also avoids the N×2N single-layer and adjoint blocks entirely, because with rigid walls the
Neumann data is non-zero only on the source faces, so only those columns are needed. That is why it is "6× less operator
memory" [inferred; consistent with `HIGH_FREQUENCY_OPTIONS.md`].

**Time cliff.** Per-frequency cost (M3): 0.4 s at 2.4k, 2.8 s at 5.1k, 7.5 s at 7.0k, **45 s at 8.9k**. Past ~7k the
card is in memory pressure. Keep screens at ≤ 6k dofs on the current path even when they fit.

## 2. What fits today (no code change)

f_max at a dof budget scales as √budget for a fixed horn (dofs ∝ f²·area). From the measured 12 kHz dof counts
[measured, `HF12K_VERIFY_2026-10-23.md`]:

| horn | epw | dofs @ 12 kHz | f_max @ 6k dofs (fast) | f_max @ 8.9k (edge) | f_max @ 20k (fused) |
|---|---|---|---|---|---|
| osse_axi (360×360×220 brief) | 6 | 3,527 | 15.7 kHz | 19.1 kHz | 28 kHz |
| osse_axi | 8 | 6,049 | 12.0 kHz | 14.6 kHz | 21.8 kHz |
| perturbed_osse_hv (400×300×220) | 6 | 4,540 | 13.8 kHz | 16.8 kHz | 25.2 kHz |
| shipped large OSSE seed (0.28 m² quarter) | 6 | ~19,000 [`HIGH_FREQUENCY_OPTIONS.md`] | 6.7 kHz | 8.2 kHz | 12.3 kHz |

(epw 6 vs 8 was converged to 0.06 dB / 0.3° at 12 kHz for osse_axi [measured, same file].)

**Recommendation H1 (free).** Add `*_12k_search.yaml` briefs (copies of the 1" briefs with `band_hi_hz: 12000`, no
`verify_only`), screen cap unchanged at 5,000, epw 6. Measure seconds per candidate on one family before a campaign.
These form their own frequency-grid group (already enforced by the grid check). Prerequisites: Report 1 F10 (more HF
frequency points) and the f11 caveat on every output.

## 3. Options ranked

| # | Option | Reaches | Effort | Who | Risk | Notes |
|---|---|---|---|---|---|---|
| H1 | 12 kHz screen briefs for 1" horns | 12–15 kHz now | YAML + one timing run | us | low | section 2 |
| H2 | **Band-split meshing** (one mesh per frequency band, each sized to its band top) | same ceiling, 2–4× faster | medium (`mesh/` + `search/evaluate.py`) | us | low–medium: discretization differs per band, so a seam check is needed | section 4 |
| H3 | **Coarser rear/outer shell** (`rear` res = k·mouth res) | +15–25 % f_max [inferred] | small (`mesh/sizing.py:res_mm_for`) | us | low; measure | the shell's back is often 30–50 % of the area; its field is weak at HF |
| H4 | `beat_cpu` fused for large-horn finalists | 12 kHz for the 0.8 m seed | config | us | slow: about 6–9 min/frequency at 19k [inferred: 57 s at 8.9k × (19/8.9)^3 for LU] | use `solve_precision="double"` for the reference |
| H5 | **Axisymmetric BEM backend** (m = 0) for axi families | 20 kHz+ in ms | medium–high | us with owner OK (a third-party solver, as bempp is) | low once cross-checked against `beat_cuda` at 5.5 kHz | section 5 |
| H6 | Fused CUDA in the exterior driver (P1) | ~20k dofs, 12 kHz for the big seed | moderate Julia (≈ 30–60 lines + tests) | **us, in our fork** (WP15) | medium (CUDA path never run by its authors outside tests) | validation ladder in `docs/FORKS.md` |
| H7 | Matrix-free GPU Burton-Miller + GMRES (assemble kernels on the fly) | 50k+ dofs | high | us in the fork (research-scale) | medium–high (preconditioning at kR ~ 100) | O(N) memory; ~5–40 s/frequency at 20k [inferred, section 6] |
| H8 | NumCalc (Mesh2HRTF, ML-FMM, C++) as a CPU backend | 100k+ dofs | high (new adapter) | us | medium | proven for HRTFs to 24 kHz (Appendix B) |
| H9 | Cloud 24/48 GB GPU | ~16–23k dofs on the current path | rental | us | Linux CUDA path never run (CLOUD_GPU_REPORT) | fallback only |
| — | Float16, oversubscription, fewer frequencies | — | — | — | — | not recommended (agreeing with NEXT_DEV_PRIORITIES) |

## 4. Band-split meshing (H2): design

Today one mesh, sized for `f_max`, solves every frequency. Assembly is O(N²) and LU O(N³), so the 500 Hz point pays
the 12 kHz mesh price. Split the grid into bands by octave group, mesh each band at `res_mm_for(epw, band_top)`, and
solve each frequency on its band's mesh. The frequency grid and the dataset label space are unchanged.

Cost for a 12-point 0.5–12 kHz screen [inferred]: 7 of the 12 log points (500–2,832 Hz) sit below 3 kHz, where N is
16× smaller, so they become nearly free. With bands at 3 and 6 kHz, two points run on a 4× smaller mesh and three on
the full mesh. Total ≈ 25–40 % of today's solve time, depending on the band edges and the N² vs N³ split.

Risks and controls:
- Discretization error then differs by band. Gate: at the band seams, solve the seam frequency on both meshes; they
  must agree within the CP-7f floor (0.039 dB on-axis, 1° beamwidth). If they don't, raise epw.
- Records must state `mesh_policy: band_split_v1` (provenance); keep it out of the old dataset group.
- Mesh time goes up by the number of bands (seconds of CPU each). Cache keys must include the band.

## 5. Axisymmetric BEM (H5): why it is the cheapest 20 kHz

For a body of revolution with an axisymmetric drive (our uniform cap), only the m = 0 Fourier mode exists. The 3-D
Burton-Miller problem collapses to a line integral along the meridian (inner wall + lip + outer shell + rear cap). At
20 kHz and 10 elements per wavelength, h ≈ 1.7 mm; a ~0.7 m generator curve is ≈ 400 unknowns [inferred]. Dense LU
of a 400×400 complex matrix takes milliseconds. Polars come from the same m = 0 field (H = V by symmetry). DI needs
no balloon: integrate over θ only.

Candidates: **AcousticBEM** (Kirkup, Python/C, GPL-3.0, has "RAD" axisymmetric operators [checked 2026-10-24];
Burton-Miller support **not** confirmed: check the source, and if absent use CHIEF points or the hypersingular
operator it provides) and **OpenBEM** (DTU, Matlab, axisymmetric with Burton-Miller). GPL-3.0 is compatible with this
repo's AGPL-3.0 [inferred; confirm the licence file].

Integration: a `solve/axibem.py` backend that takes the *meridian* (not the 3-D mesh), from the generator's anchors or
`hornlab_mesher.profile_formulas.profile_points`, plus the shell thickness, and returns a `Response` with H = V cuts.
Gate before any data counts: (1) analytic pulsating sphere; (2) `beat_cuda` vs `axibem` on osse_axi and tractrix
seeds at 0.5–5.5 kHz within 0.2 dB on-axis and 1° beamwidth (CP-7b-style); (3) its own dataset group.

Payoff beyond 12 kHz: an **axi-first search**, where thousands of evaluations a minute are possible. Axisymmetric
optima then seed H/V searches (OSSE H/V and GRID families start from the best axi meridian). It is also the right
tool for the Le Cléac'h/tractrix mouth studies, which are axisymmetric by nature.

## 6. Matrix-free GPU estimate (H7), long-term fork project

Per GMRES matvec with quarter symmetry (4 images), N_faces ≈ 40k at N = 20k: (4·10⁴)²·4 ≈ 6.4e9 pair interactions.
Far pairs with a 1-point rule cost ≈ 40 flops (exp, sincos, multiply-adds), so 2.6e11 flops. On a 4060 at an
effective 3–6 TFLOP/s FP32 that is 45–90 ms per matvec. With 100–300 iterations (Burton-Miller at kR ~ 100,
diagonal or near-field preconditioner) it comes to **5–30 s per frequency at O(N) memory**, plus a sparse near-field
correction table [inferred; order-of-magnitude only]. Appendix B's "~1 s" ignores the kernel cost. Forks are allowed
now (`docs/FORKS.md`), but this is a research-scale solver project: do it only after WP15 is in production.

## 7. Accuracy above 5.5 kHz: what must accompany every 12 kHz number

1. **Source above f11 (7.9 kHz for 1").** A real exit is not a uniform cap. Quantify sensitivity cheaply: re-solve
   two finalists with `source_motion: "axial"` (rigid piston, supported [verified, `config.py`]) and compare 8–12 kHz
   beamwidth. If the two idealized sources disagree by more than ~2°, rank horns only below f11. Longer term, add a
   non-uniform velocity profile on the source tag in our fork (WP16; for example a J0(k_r·r) mode component) to model
   a phase-plug exit.
2. **Frequency density.** The 25-point 300 Hz–16 kHz verify grid is 4.6 points/octave. Use ≥ 8/octave in 5–12 kHz for
   finalists (Report 1 F10). It costs linear time, and these are small meshes.
3. **Far field.** At 12 kHz, 2D²/λ = 6–11 m for 300–400 mm mouths (Report 1 F8); check 2 m vs 10 m vs 50 m from traces.
4. **Balloon resolution.** At 12 kHz use at least 1,024 points; measure DI convergence (Report 1 F9).
5. **epw.** Shipped epw is converged at 12 kHz for two designs [measured]. Re-check per family; GRID and multicell
   surfaces have more curvature.

## 8. Recommended sequence (fits the existing NEXT_DEV_PRIORITIES)

1. H1 + Report 1 F10 (YAML and one timing run): 12 kHz screening for 1" briefs this week.
2. H3 (coarser rear shell) with a convergence check: pure gain if it passes.
3. H2 band-split meshing: the time lever for every search.
4. H5 axisymmetric backend (owner decision on a third-party solver): the 20 kHz lever and a 1000× screening lever
   for axi families.
5. **H6 = WP15 in our fork: start it now, in parallel with steps 1–3** (it is the owner's priority and touches
   only the fork plus one solver flag here).
6. H4 CPU overnight verify for large horns whenever needed; cloud (H9) only if H6 stalls.
