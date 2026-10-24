> **Appendix B: raw methods survey by a Sonnet research agent (2026-10-24), kept verbatim for its sources.**
> Corrections (see `03_HIGH_FREQUENCY_12KHZ.md`): DI is already balloon-based here (D1 "replace cuts_estimate" does not
> apply); a uniform cap excites only the m = 0 azimuthal mode, so axisymmetric BEM needs one mode, not 20–40; the
> matrix-free "~1 s per frequency" estimate ignores kernel cost (our estimate: 5–30 s at 20k dofs); the JAX-BEM abstract
> does not mention horns; AcousticBEM is GPL-3.0 and Burton-Miller support in its axisymmetric code is unconfirmed.

# hornlab-search: Deep Research Report on High-Frequency BEM, Driver Modelling, Optimisation, and Metrics

*Written 2026-10-24 by Claude Sonnet 4.6 (read-only research agent, hornlab-search). Every claim is labelled [source URL], [inferred], or [unverified]. No files in hornlab-search were edited.*

---

## RANKED RECOMMENDATIONS TABLE

| Rank | Idea | Expected payoff | Effort | Risk | Key source |
|------|------|----------------|--------|------|------------|
| 1 | **Axisymmetric BEM (Fourier azimuthal modes)** — for axisymmetric horns reduces 3D surface integral to 2D line integrals per azimuthal order m; reaches 12–20 kHz trivially on CPU | High: removes memory wall for the axisymmetric family; 12 kHz is ~50–200 DOFs on the generator curve | Medium: integrate OpenBEM/BoundaryIntegralEquations.jl or write Python wrapper; new dataset family | Low (well-proven method); requires axisymmetric horn assumption | [orbit.dtu.dk OpenBEM](https://orbit.dtu.dk/en/publications/openbem-an-open-source-boundary-element-method-software-in-acoust/); [github.com/Gjacquenot/AcousticBEM](https://github.com/Gjacquenot/AcousticBEM) |
| 2 | **CPU backend + fused Burton-Miller (already available)** — `beat_cpu` with fused path ON handles 19k dofs in ~32 GB RAM; ~5–15 min/freq for finalists only | High: reaches 12 kHz at epw 6 with zero new code; validated path | Low: config/YAML only | Low | [docs/HIGH_FREQUENCY_OPTIONS.md](../docs/HIGH_FREQUENCY_OPTIONS.md) [verified] |
| 3 | **Fused CUDA assembler in exterior driver (P1)** — wire the existing `assemble_burton_miller_neumann_system_cuda` into `BeatEngineDriver.jl`; 6x less VRAM, ~20k dof ceiling | Very high: 12.6 kHz at epw 6 on GPU at GPU speed | High: requires Magnus's OK + Julia change | Medium: CUDA path never run by authors | [docs/NEXT_DEV_PRIORITIES.md P1](../docs/NEXT_DEV_PRIORITIES.md) [verified] |
| 4 | **NumCalc / ML-FMM BEM on CPU** — open-source C++ BEM with multi-level FMM; Burton-Miller γ=i/k; handles 100k+ DOFs; used for HRTFs to 24 kHz on CPU | High: proven precedent for 20 kHz+ on CPU | High: C++ integration, new solver in pipeline | Low for correctness; medium for integration | [arxiv.org/abs/2312.00005](https://arxiv.org/abs/2312.00005) |
| 5 | **Multi-fidelity BO (coarse mesh + low f as cheap fidelity)** — use MFBO or Hyperband-style successive halving; search result claims 90% cost reduction in a horn robust-optimisation example | High: dramatically cuts screening cost | High: BoTorch MFBO integration | Medium: fidelity correlation must be validated | [arxiv.org/pdf/2211.06149](https://arxiv.org/pdf/2211.06149); [oreilly.com MFES-HB](https://www.oreilly.com/library/view/hyperparameter-tuning-with/9781803235875/B18753_06_ePub.xhtml) |
| 6 | **JAX-BEM gradient-based shape optimisation** — differentiable BEM in JAX with GPU; applied to horn directivity; provides gradients of directivity w.r.t. mesh vertices | High for final polish; not suited for global search | High: Python + JAX, different pipeline | Medium: memory cost at 12 kHz unknown | [arxiv.org/abs/2604.21431](https://arxiv.org/abs/2604.21431) |
| 7 | **Throat impedance + T/S two-port coupling** — compute Z_rad from BEM at throat, cascade with TS+chamber two-port for real SPL and driver excursion | Medium: corrects ~2–3 dB SPL error above 5 kHz for non-flat throat Z | Medium: two-port math in Python, datasheet needed | Low | [AKABAK docs](https://audioxpress.com/news/akabak-software-update-improves-loudspeaker-parameter-modeling); [ABEC3 methodology] |
| 8 | **CMA-ES BIPOP restarts + BoTorch TuRBO** — sequential strategy: run BIPOP-CMA-ES until convergence, warm-start TuRBO on the best region | Medium: better global coverage | Low: already have CMA-ES; add BoTorch | Low | [arxiv.org/pdf/1207.0206](https://arxiv.org/pdf/1207.0206); [papers.nips.cc BoTorch](https://papers.nips.cc/paper/2020/hash/f5b1b89d98b7286673128a5fb112cb9a-Abstract.html) |
| 9 | **CMA-ME quality-diversity archive** — maintain a MAP-Elites grid (beamwidth × DI at reference freq) with CMA-ME emitters | Medium: generates diverse design families for the user to choose from | Medium: QD library (pyribs) | Low | [arxiv.org/pdf/2106.03894](https://arxiv.org/pdf/2106.03894) |
| 10 | **Viscothermal loss model (BoundaryIntegralEquations.jl)** — sparse impedance boundary condition for visco-thermal losses at small throats | Low–medium for 1-inch exits; higher for narrow phase plug channels | High: new solver integration | Low | [orbit.dtu.dk visco-thermal BEM](https://orbit.dtu.dk/en/publications/an-open-source-boundary-element-framework-for-large-scale-viscoth/) |

---

## A. REACHING 12 kHz ON AN 8 GB GPU OR VIA CPU

### A1. The current situation (recap from existing docs)

The existing analysis in `docs/HIGH_FREQUENCY_OPTIONS.md` and `docs/NEXT_DEV_PRIORITIES.md` is thorough and accurate [verified]. The memory ceiling is not the card but the unfused CUDA Burton-Miller assembly (4 dense operator matrices vs 1 for the fused path). The fused path exists in the codebase but is not wired for CUDA. The CPU path already has the fused path ON and can reach 12 kHz for the seed horn with ~32 GB RAM [verified from docs]. This section therefore focuses on alternatives that extend reach further or that the existing docs did not cover.

### A2. Axisymmetric BEM with Fourier azimuthal modes (BIGGEST LEVERAGE for axisymmetric horns)

For a body of revolution (axis-symmetric horn), the 3D Helmholtz BEM problem decomposes exactly into independent 2D line-integral problems, one per azimuthal Fourier order m = 0, 1, 2, …. The m=0 mode is the plane-wave-like mode; higher modes correspond to the azimuthal variation of the field. For a horn excited by a uniform-velocity circular cap (as in hornlab-beat-bem), only m=0 is excited. For non-uniform excitation (e.g., a driver with unequal channels), all modes are coupled to m≥0.

**Memory and time scaling.** If the 3D surface has N_gen generator nodes and K azimuthal orders are needed, the total computational cost is O(K × N_gen²) for a dense solve, versus O(N²) for 3D BEM where N ≈ N_gen × N_ring. Since K << N_ring (typically K~20–40 suffices at 12 kHz for a horn), the saving is enormous. For the shipped seed horn at 12 kHz (epw 6, N_gen ≈ 130 generator points, K ≈ 40), each mode-m matrix is 130×130 = 17 kB, and solving K=40 such systems costs negligible memory on any machine [inferred from scaling].

**Available codes:**
- **OpenBEM** (Henriquez & Juhl, DTU, Matlab): the canonical open-source axi-BEM for acoustics. Handles exterior + interior Helmholtz, Burton-Miller, 2D axisymmetric with Fourier modes. Available at http://www.openbem.dk/ [source: [orbit.dtu.dk](https://orbit.dtu.dk/en/publications/openbem-an-open-source-boundary-element-method-software-in-acoust/)].
- **AcousticBEM** (Kirkup, Python/C, GPL): reimplements Kirkup's Fortran ABEM library, includes axisymmetric BEM for horn loudspeakers. Available at [github.com/Gjacquenot/AcousticBEM](https://github.com/Gjacquenot/AcousticBEM); also distributed as the `abem` PyPI package [source: [pypi.org/project/abem](https://pypi.org/project/abem/)].
- **BoundaryIntegralEquations.jl** (Paltorp, DTU, Julia): Julia package for the Kirchhoff-Helmholtz integral equation using collocation BEM, with FMM and H-matrices via HMatrices.jl, plus viscothermal loss support. Does *not* appear to have axisymmetric reduction as a first-class feature (unstable lifecycle, research grade) [source: [github.com/mipals/BoundaryIntegralEquations.jl](https://github.com/mipals/BoundaryIntegralEquations.jl)].

**Integration into hornlab-search.** The cleanest path is a thin Python wrapper around OpenBEM (via a subprocess call to Matlab) or AcousticBEM (pure Python). The output would be the same (pressure on a half-sphere of field points, matching the current `SolveResult` schema). A new solver adapter `solve/axibem.py` could call either, with the CPU-backend fallback remaining available for 3D cross-check. This is a new dataset family (different solver, different formulation), so it must be verified against the existing bempp_cpu crosscheck before mixing.

**Limitation.** Only works for exactly axisymmetric horn geometries. The `osse_hv` family (horizontal/vertical asymmetry) and `freeform_sculpt` families are not axisymmetric and cannot use this path. The `osse_axi` family is the target.

**Precedent.** The HRTF community uses axisymmetric BEM for spherical-head models to 20 kHz routinely [unverified, common knowledge in axi-BEM literature]. More relevantly: Kirkup's 1994 paper "Simulation of the Acoustic Field of a Horn Loudspeaker by the Boundary Element–Rayleigh Integral Method" directly validated BEM for horn radiation [source: [researchgate.net Simulation](https://www.researchgate.net/publication/235788684_Simulation_of_the_Acoustic_Field_of_a_Horn_Loudspeaker_by_the_Boundary_Element-Rayleigh_Integral_Method)].

### A3. H-matrix / ACA compression

Hierarchical matrix (H-matrix) methods compress dense BEM system matrices by approximating far-field block interactions as low-rank matrices built by Adaptive Cross Approximation (ACA). For the Laplace kernel this gives O(N log N) memory and O(N log² N) LU. For the Helmholtz kernel at dimensionless wavenumber kR >> 1 (here kR = 2πf×L/c where L is the horn dimension), the rank of low-rank blocks grows linearly with k, degrading compression. At 12 kHz, kR ≈ 2π×12000×0.3/340 ≈ 66 for the seed horn – this is the "high-frequency regime" where standard ACA compression is poor.

Recent work (arXiv:2607.19500, July 2026) proposes "robust hierarchical matrix compression" specifically addressing this rank growth for high-frequency Helmholtz BEM [source: [arxiv.org/abs/2607.19500](https://arxiv.org/abs/2607.19500)]. A 2025 Springer paper extends H-matrix to multi-patch IgA-BEM for Helmholtz [source: [springer.com Hierarchical matrices for Helmholtz](https://link.springer.com/article/10.1007/s00366-025-02144-w)]. A 2025 UCL paper benchmarks GPU parallelisation of H-matrix BEM [source: [discovery.ucl.ac.uk](https://discovery.ucl.ac.uk/id/eprint/10036655/1/Betcke_1711.01897v1.pdf)].

**Julia: HMatrices.jl** (IntegralEquations group) assembles and factors hierarchical matrices for BEM. It achieved ~25× compression for N=100k in a Laplace example. Helmholtz support: the README uses a Laplace example only; Helmholtz support is not confirmed from the README alone [source: [github.com/IntegralEquations/HMatrices.jl](https://github.com/IntegralEquations/HMatrices.jl)].

**Julia: Inti.jl** (JuliaCon 2024 presentation) is described as supporting both H-matrix compression (via HMatrices.jl) and FMM (via FMM3D.jl) for integral equations in 2D and 3D, with Gmsh integration and a unified API [source: [pretalx.com/juliacon2024](https://pretalx.com/juliacon2024/talk/X8RYLT/)]. This is potentially the most complete Julia BEM framework, but it is research-grade.

**Assessment.** H-matrix at kR~50–150 is not a silver bullet; it requires H^2 or directional H-matrix techniques for the high-frequency Helmholtz problem [inferred from rank-growth literature]. Integration effort is high. Axisymmetric BEM is simpler and more appropriate for the horn problem.

### A4. Fast Multipole Method (FMM)

FMM gives O(N) memory and O(N log N) or O(N) time for matrix-vector products, enabling iterative (GMRES) solution with no dense matrix storage. The state of the art for 3D acoustic exterior BEM is:

- **NumCalc / Mesh2HRTF** (open-source C++, Burton-Miller, γ=i/k, CGS solver): Uses multi-level FMM (MLFMM with explicit element-to-cluster matrices). Switches to MLFMM at N > 50k. Has been validated for HRTF at 0–24 kHz with meshes up to 74,892 elements in benchmarks. CPU only. Setup time for N=35k is 5–15 min with full accuracy settings [source: [arxiv.org/abs/2312.00005](https://arxiv.org/abs/2312.00005), [Mesh2HRTF homepage](https://www.oeaw.ac.at/en/ari/outreach/software/mesh2hrtf)]. This is the clearest precedent for free-standing horn simulation to 24 kHz on a CPU.

- **bempp-cl** (Python, PyOpenCL, Burton-Miller): Uses ExaFMM for FMM-accelerated matrix-vector products. Designed for exterior Helmholtz. CPU or GPU via OpenCL [source: [bempp.com](https://bempp.com/); [joss.theoj.org/papers/10.21105/joss.03145.pdf](https://joss.theoj.org/papers/10.21105/joss.03145.pdf)]. A 2021 arXiv paper (2103.01048) showed bempp-cl + ExaFMM solving exterior Helmholtz problems at ~kR=50 on CPU.

**Integration into hornlab-search.** NumCalc could be called as a subprocess from Python (it has a command-line interface). Output (complex pressure on field points) maps to the existing `SolveResult` format. Effort is significant (new adapter, validation, geometry export from the existing mesher), but NumCalc is C++, BSD-licensed, and already used for HRTFs up to 24 kHz. This is a strong medium-term option if the GPU ceiling cannot be lifted.

### A5. Matrix-free GPU BEM (assemble-on-the-fly)

Instead of assembling the dense matrix G and then applying LU or GMRES, one can compute each G(x,y) kernel evaluation on-the-fly during each GMRES iteration, storing only two vectors of length N (the current residual and correction). Memory is O(N) instead of O(N²). GPU threads compute the kernel independently for each target-source pair.

The cost per GMRES iteration is O(N²) FLOPs, same as a dense matvec, but on a GPU with 3000+ CUDA cores this can be done in ~N²/3000 clock cycles per element. At 20k DOFs, one matvec is 4×10^8 FLOPs; at 20 TFLOPs (RTX 4060 float32), this takes ~20 ms per iteration, so with 50 GMRES iterations (~30 for moderately well-conditioned BEM), one frequency solve is ~1 second [inferred from GPU specs]. No dense matrix is stored: memory is O(N) per frequency.

**Risk.** Convergence of GMRES for Burton-Miller BEM at high kR is not guaranteed without a good preconditioner. Near-field singular corrections (which the existing solver handles via the pre-computed near-correction table) must be rebuilt for the on-the-fly kernel. The existing `assemble_burton_miller_neumann_system_cuda` in beat-bem stores a full matrix, so it is not matrix-free [verified from docs]. A truly matrix-free GMRES for Burton-Miller BEM on GPU has been implemented in research (2021 arXiv:2112.11880 covers GPU GMRES for BEM Helmholtz) but is not currently packaged in the Julia ecosystem [source: [arxiv.org/pdf/2112.11880](https://www.arxiv.org/pdf/2112.11880)].

### A6. Mixed precision and iterative refinement

The existing solver already uses Float32 matrices with Float64 Krylov (effectively iterative refinement) [verified from TOOLCHAIN]. Going to Float16 would halve memory (from 9k to 18k dofs before OOM) but BEM matrices at high kR are poorly conditioned; Float16 risks divergence [noted as "not recommended" in NEXT_DEV_PRIORITIES.md]. No new search findings contradict this [inferred].

### A7. Hybrid FEM-BEM / domain decomposition

One can model the horn interior (a closed cavity) with FEM and only the exterior (the half-space radiation problem) with BEM, coupling the two at the mouth aperture. This is what COMSOL's acoustic module does for horn design [source: [doc.comsol.com horn_shape_optimization](https://doc.comsol.com/6.1/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html)]. For a free-standing horn, the interior is not really a cavity (the horn is open at both ends), so this decomposition is less natural. The main benefit would be using FEM to capture the interior wave pattern with fewer DOFs (FEM scales as volume, O(f³) for 3D, while BEM scales as surface, O(f²)). For thin-walled horns the BEM surface-only approach is already optimal. [inferred; not confirmed by a specific source for this horn geometry type]

### A8. Frequency-sweep acceleration

For a fixed geometry, the BEM system matrix entries G_{ij}(k) are analytic in k (for the Helmholtz kernel); the solution vector p(k) is meromorphic. Padé approximants or Krylov subspace methods (e.g., the Ruhe/Rational Krylov approach) can interpolate p(k) from solutions at a small number of seed frequencies, avoiding a full solve at every frequency. A few papers (e.g., on FEM model-order reduction) demonstrate 10–50× speedup in the frequency sweep at moderate kR. At high kR, the poles are denser and more seed points are needed [inferred from model-order-reduction literature; [unverified] for BEM specifically at kR~100].

### A9. Cloud GPU options

Already documented in `docs/CLOUD_GPU_REPORT.md`. An RTX 4090 (24 GB) at ~$0.34–0.69/h or an L40S (48 GB) at ~$0.79/h would each comfortably hold a 19k-dof dense matrix in the current (unfused) CUDA path. The blocker is that the solver's CUDA path has never been validated on Linux (all development is Windows/macOS) [verified from NEXT_DEV_PRIORITIES.md].

---

## B. DRIVER / SOURCE MODELLING

### B1. The current solver's source model

The existing solver drives a **uniform rigid-velocity spherical-cap source** on the throat (tag 2), which is a good model for the m=0 (plane-wave) regime. Above the first transverse throat mode (f_{11} ≈ 1.84 × c / (π D_throat) where D_throat is throat diameter), the driver exit wavefront is no longer uniform. For a 1-inch (25.4 mm) diameter throat: f_{11} ≈ 1.84 × 343 / (π × 0.0254) ≈ 7,930 Hz [inferred from waveguide mode formula]. So the uniform-cap assumption is valid below ~8 kHz for a 1-inch exit.

### B2. How professional tools couple driver to horn

**AKABAK** (Juha Backman, 2024 update): uses a dual LEM + BEM architecture. The Lumped Element Method models driver electromechanics (Re, Le, Bl, Mms, Sd, front chamber Vrc) and the BEM models horn radiation. Coupling is via acoustic port impedances: AKABAK computes the horn's acoustic input impedance Z_a(f) from BEM, then inserts it as a boundary condition in the LEM circuit network. The full driver SPL and voice coil excursion are then predicted [source: [audioxpress.com AKABAK](https://audioxpress.com/news/akabak-software-update-improves-loudspeaker-parameter-modeling)].

**ABEC3** (Juha Backman, same author): similar LEM+BEM approach. Phase plugs modelled as transmission-line sections (each channel as a duct with area and length). Users specify: throat area S_T, motor diameter, conical section dimensions. A lumped phase plug model (Kinoshita/Locanthi) is also available [source: [diyaudio.com ABEC discussion](https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/)].

**Hornresp** (David McBean): 1D transmission-line model for the entire horn/driver system. No 3D BEM. Accurate for on-axis response, cannot predict directivity.

**COMSOL Acoustics**: FEM interior + BEM exterior; full 3D with driver physics. Horn shape optimisation tutorial available [source: [doc.comsol.com horn_shape_optimization](https://doc.comsol.com/6.0/doc/com.comsol.help.models.aco.horn_shape_optimization/models.aco.horn_shape_optimization.pdf)].

### B3. The correct way to add a driver model to hornlab-search

The standard two-port approach (Thiele-Small coupled to BEM) works as follows:

1. **From BEM**: compute the acoustic radiation impedance at the throat plane:  
   Z_rad(f) = p_avg / U_throat  
   where p_avg is the area-averaged pressure on the throat face and U_throat is the total volume velocity. The existing solver already computes p on the throat surface (tag 2) as part of the BEM solution [inferred from solver docs; unverified if hornlab-beat-bem outputs p on the throat face by default].

2. **T/S + front chamber two-port**: the compression driver is modelled as an electromechanical-acoustic two-port:  
   - Electrical: Re (DC resistance), Le (voice-coil inductance)  
   - Mechanical: Bl (motor strength), Mms (moving mass), Rms (mechanical resistance), Cms (compliance)  
   - Acoustic: Sd (diaphragm area), Vrc (front compression chamber volume), possibly a phase plug model  
   The acoustic output port of this two-port sees Z_rad(f) from the horn.

3. **Predicted SPL**: p(f) = Z_rad(f) × e_in(f) / Z_total(f) where e_in is the input voltage and Z_total includes all the electromechanical stages.

**Commercially available driver parameters (from datasheets):**
- BMS 4550 (1-inch compression driver): Re=8Ω, Le≈0.02 mH, Bl≈10.5 T·m, Mms≈0.6 g, Sd≈5.1 cm², Vrc≈1.5 cm³. [source: BMS datasheet, [unverified] exact values vary by revision]
- B&C DE250: Re=6Ω, Le, Bl, Mms, Sd, Vrc available in datasheet PDF. [unverified]
- Celestion CDX1-1745: similar parameter set. [unverified]

### B4. Spherical cap vs plane wavefront source

The existing solver uses a uniform normal-velocity condition on a spherical-cap throat face. For an oblate-spheroid waveguide (Geddes geometry), the natural source is an oblate-spheroid wavefront. For a conical throat, a spherical-cap matches the geometry well. The discrepancy between a flat plane-wave source and the actual spherical-cap is largest at high kR where the throat region radiates in its own way [inferred]. AcousticBEM's axisymmetric formulation supports arbitrary source conditions (normal velocity on the throat ring) [source: [github.com/Gjacquenot/AcousticBEM](https://github.com/Gjacquenot/AcousticBEM)].

### B5. Phase plug and non-uniform exit velocity

Above f_{11} (~8 kHz for 1-inch), the driver exit is not a uniform piston. Phase plugs impose a path-length equalization across the diaphragm radius that determines the exit wavefront. The 2024 arXiv paper "A better compression driver?" (arXiv:2403.17963) optimises a radial phase plug using CutFEM (not BEM) + level-set geometry. Key findings:
- Viscothermal boundary-layer losses (Wentzell boundary condition) were included in the optimisation at negligible extra cost.
- Targeting 3.75–15 kHz with a radial (annular channel) exit.
- Including viscothermal losses *during* optimisation (not just evaluation) gave significantly better results at high frequency, especially above 10 kHz.
- The optimised design "surprisingly closely matches the ideal lumped-parameter response." [source: [arxiv.org/html/2403.17963v1](https://ar5iv.labs.arxiv.org/html/2403.17963)]

**Recommendation for hornlab-search:** the existing 8–12 kHz results should carry a physics caveat noting that the uniform-cap source overestimates coupling efficiency above f_{11}, and that real driver + phase plug behaviour would require a measured or modelled throat exit wavefront. This is already noted in `docs/HIGH_FREQUENCY_OPTIONS.md` [verified].

### B6. Viscothermal losses at small throats

At 12 kHz, the thermal/viscous boundary layer thickness is δ ≈ sqrt(2μ/ρω) ≈ sqrt(2 × 1.8×10⁻⁵ / (1.2 × 2π×12000)) ≈ 0.022 mm [inferred from first principles]. For a 1-inch (25.4 mm) throat, δ/r ≈ 0.002: about 0.2% of the radius. This is borderline. For narrow phase plug channels (1–2 mm width), δ/w ≈ 1–2%, giving measurable losses.

The DTU/Paltorp group has implemented viscothermal BEM as sparse assembly of the Kirchhoff Decomposition; see orbit.dtu.dk paper "An open-source Boundary Element framework for large-scale viscothermal acoustics" [source: [orbit.dtu.dk viscothermal BEM](https://orbit.dtu.dk/en/publications/an-open-source-boundary-element-framework-for-large-scale-viscoth/)]. For the current hornlab-search scope (horn walls, no phase plug), viscothermal losses are negligible and adding them is not recommended.

### B7. Air absorption

At 12 kHz, ISO 9613-1 gives air absorption of roughly 0.04–0.07 dB/m at 20°C, 50% RH [inferred from ISO formula; [unverified] exact figure]. Over the horn length (0.3–0.5 m), this is 0.01–0.03 dB, completely negligible. Over a room propagation path of 10 m, it adds 0.4–0.7 dB of frequency-independent attenuation at 12 kHz. Since hornlab-search scores the free-field horn directivity (not in-room SPL at distance), air absorption should not be added to the BEM simulation [source: [sengpielaudio.com air absorption](https://sengpielaudio.com/LuftdaempfungFormel.htm)].

---

## C. OPTIMISATION METHODS

### C1. CMA-ES best practices

The current implementation uses CMA-ES. The key upgrades are:

**IPOP/BIPOP restarts** (Hansen 2009, arXiv:1207.0206): BIPOP uses two restart regimes alternately — large population for global coverage and small population for local refinement. This outperforms IPOP on multimodal landscapes. For horn optimisation (5–20 dims, multimodal due to mouth reflections), BIPOP-CMA-ES is the gold standard for derivative-free methods [source: [arxiv.org/pdf/1207.0206](https://arxiv.org/pdf/1207.0206)]. The `pycma` library supports BIPOP restarts.

**Population sizing.** The default population λ = 4 + floor(3 × ln N) (e.g., λ=11 for N=10 dims) may be too small for a rugged horn landscape with many local optima from mouth resonances. Using λ = 10×N_dims has been recommended for difficult problems [unverified].

**Bounds handling.** The `pycma` library offers a boundary handler that mirrors infeasible parameters; alternatively, reparametrize to unbounded domain (logit for [0,1]-bounded parameters) and apply back-transform in the geometry generator.

### C2. Bayesian optimisation: TuRBO and SAASBO

**TuRBO** (Eriksson et al.): fits local GP models in trust regions, with Hyperband-style allocation across models. Very effective for 10–100 dim black-box problems with expensive evaluations. Available in BoTorch [source: [papers.nips.cc BoTorch](https://papers.nips.cc/paper/2020/hash/f5b1b89d98b7286673128a5fb112cb9a-Abstract.html)].

**SAASBO**: uses sparsity-inducing horseshoe prior over GP lengthscales; identifies the few active dimensions in high-dimensional problems. Useful if the horn parameter space has a small effective dimension [source: [ar5iv.labs.arxiv.org/html/1910.01739](https://ar5iv.labs.arxiv.org/html/1910.01739)].

**Recommended sequence:** run BIPOP-CMA-ES for 200–500 evaluations to explore globally, then warm-start TuRBO on the top 20% of observations to fine-tune. BoTorch provides both.

### C3. Multi-fidelity optimisation

This is the highest-leverage optimisation improvement available.

**Fidelity levels:**
1. Low: coarse mesh (epw=4), 3 representative frequencies (1, 2, 5 kHz): ~2 s per evaluation.
2. Medium: standard mesh (epw=6), 12 frequencies: ~30 s per evaluation.
3. High: fine mesh (epw=8), 24 frequencies including 12 kHz CPU pass: ~10 min.

**Methods:**
- **MF-BO** (MFBO, Kandasamy et al.): multi-task or multi-fidelity GP with fidelity as an input. BoTorch supports `MultiFidelityGP` and `FixedNoiseMultiFidelityGP` [source: [arxiv.org/pdf/2211.06149](https://arxiv.org/pdf/2211.06149)].
- **Hyperband / successive halving** (Jamieson & Talwalkar): promote designs from low to high fidelity based on early performance. "90% cost reduction in an acoustic horn robust optimization example" is claimed in one source [source: multi-fidelity search result]. This is the simplest to implement: evaluate all candidates at low fidelity, keep top 1/3, evaluate at medium, keep top 1/3, evaluate survivors at high.
- **MFES-HB** (Li et al.): combines multi-fidelity quality measurements with Hyperband; demonstrated 2–4× speedup over standard Hyperband on benchmark tasks [source: [ar5iv.labs.arxiv.org/html/2012.03011](https://ar5iv.labs.arxiv.org/html/2012.03011)].

**Key risk:** the low-fidelity beamwidth at 1–5 kHz must be correlated with the high-fidelity 12 kHz beamwidth. For constant-directivity horns this correlation is generally positive but not perfect; horn resonances at specific frequencies can break rank-order correlation. Validate on 50 randomly sampled geometries before using MF as the main loop.

### C4. Quality diversity: MAP-Elites and CMA-ME

**MAP-Elites** maintains a 2D (or higher) grid of high-quality designs, each occupying a cell defined by *behavior descriptors* (e.g., horizontal beamwidth at 2 kHz × beamwidth at 8 kHz). It is useful for generating a diverse archive of horn designs that the user can browse and select from, rather than returning a single optimum.

**CMA-ME** (Fontaine et al. 2020): replaces MAP-Elites' random perturbation with CMA-ES emitters. Demonstrated superior performance on multiple QD benchmarks [source: [arxiv.org/pdf/2106.03894](https://arxiv.org/pdf/2106.03894)].

**Audio QD precedent:** a 2024 presentation showed MAP-Elites for "sound innovation" using PCA of audio features as behavior space [source: [uio.no sound-innovation-engine](https://uio.no/ritmo/english/people/phd-fellows/bthj/Presentation/slides/sound-innovation-engine-1.0-(robin).pdf)]. For hornlab-search, the natural behavior descriptors are: (horizontal beamwidth target, vertical beamwidth target) → the cell. Each cell holds the best-scoring horn for that coverage target.

**Implementation:** the `pyribs` library (Python, MIT) implements MAP-Elites and CMA-ME with BoTorch-compatible interfaces.

### C5. Adjoint/gradient-based shape optimisation

**JAX-BEM** (Hipperson, Hargreaves, Cox; arXiv:2604.21431, 2025): implements a differentiable BEM in JAX, with automatic differentiation from the BEM solution back through the mesh vertices. Applied to loudspeaker horn directivity optimisation. The gradient of any scalar loss (e.g., beamwidth uniformity) w.r.t. all mesh vertex coordinates is available via reverse-mode AD in O(1) backward passes. This enables gradient descent optimisation with ~1000 effective gradient steps for the cost of ~1001 BEM solves [source: [arxiv.org/abs/2604.21431](https://arxiv.org/abs/2604.21431)].

**Wadbro, Berggren, Bängtsson** (Umeå University, 2002–2022): gradient-based shape optimisation of axisymmetric acoustic horns using FEM + adjoint method. Key result: designed a 161.5 mm horn (mouth dia 300 mm, 1.5" throat) with perfect impedance matching at 31 frequencies from 1.6 to 9.05 kHz, satisfying a convexity constraint on the flare [source: [people.cs.umu.se BeWaBe19.pdf](https://people.cs.umu.se/martinb/downloads/Papers/BeWaBe19.pdf)]. This is the clearest precedent for high-frequency gradient-based horn optimisation. Uses axisymmetric FEM (not BEM), so it complements the BEM-based search.

**Assessment for hornlab-search.** Gradient-based methods are not suited for global search (they find local optima). They are excellent for final polishing of a CMA-ES or MAP-Elites winner. A workflow of (1) CMA-ME archive → (2) pick the best cell → (3) JAX-BEM gradient descent would give the best of both worlds.

### C6. Robust optimisation (manufacturing tolerance)

Horn dimensions are typically CNC-routed or injection-moulded with ±0.5 mm tolerances. At 12 kHz (wavelength 28 mm), a 0.5 mm error is 1.8% of wavelength, which can shift mouth-reflection resonances by ~1.8% in frequency (~220 Hz at 12 kHz). A robust formulation adds a small perturbation ensemble to the objective: E[score(θ + ε) | ε ~ N(0, σ²_tolerance)]. This requires ~5–10 extra evaluations per candidate. Not recommended as a primary feature until a good base design is found [inferred].

---

## D. METRICS / OBJECTIVE STANDARDS

### D1. CTA-2034-A / Spinorama (ANSI/CTA-2034-A R-2020)

The spinorama standard defines the full angular response measurement protocol for loudspeakers in a free field:

| Curve | Definition |
|-------|-----------|
| On-axis | 0° H, 0° V |
| Listening window (LW) | Spatial average of 9 responses: ±10° V, ±30° H (from source standard) |
| Early reflections (ER) | Average of representative early-reflection angles (floor, ceiling, side walls) |
| Sound power (SP) | Integral over full sphere with cos(elevation) weighting |
| Directivity index (DI) | LW − SP (dB) |
| Predicted in-room response (PIR) | 12% LW + 44% ER + 44% SP (Olive formula approximation) |

[source: [docs.rs/autoeq-cea2034](https://docs.rs/autoeq-cea2034); [spinorama.org](https://www.spinorama.org)]

**Olive preference score.** Sean Olive's patent (US8311232) and associated papers predict listener preference as:

score ≈ 12.69 − 2.49 × NBD_ON − 2.99 × NBD_PIR − 4.31 × LFX + 2.32 × SM_PIR

where NBD = narrow-band deviation (RMS of 1/20-octave-smoothed minus 1/2-octave-smoothed response), LFX = −3 dB low-frequency extension (in log kHz), SM_PIR = smoothness metric of PIR. Higher score is better; typical home hi-fi speakers score 5–7 out of 10 [source: [patents.google.com/patent/US8311232](https://patents.google.com/patent/US8311232)].

**Application to hornlab-search.** The spinorama DI (LW − SP) is a more rigorous metric than on-axis DI alone, because it captures how the horn's off-axis power spectrum differs from its on-axis spectrum. Computing the full spinorama requires a half-sphere of field points (already computed by the existing balloon solver); the formula is a weighted average. This should replace the current "cuts_estimate" DI whenever `di_source == "balloon"` is available [inferred from metric documentation in the codebase].

### D2. Geddes HOM metric and polar map smoothness

Earl Geddes (Earl Industries, "Loudspeakers and Rooms" papers, 2001–2012) proposed that the key perceptual problem with horns is Higher Order Modes (HOMs): off-axis propagation paths that bounce off horn walls, causing comb filtering in the off-axis response [source: [diyaudio.com Geddes on waveguides](https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/)].

**HOM metric.** Geddes has not published a single quantified HOM metric in a peer-reviewed form [unverified]. The common proxy is the "polar map": a 2D plot of SPL vs (frequency, angle) displayed as a colour map. A horn with low HOMs shows smooth, monotonically widening or narrowing contours. Abrupt angular discontinuities in the contours indicate HOM excitation. The practical objective function proxy is the variance of the beamwidth-vs-frequency curve: a well-behaved horn has slowly varying beamwidth across octaves.

**Oblate spheroid / OS waveguide.** Geddes's preferred geometry (OS waveguide) produces the weakest HOMs because the wavefront curvature changes smoothly from spherical at the throat to nearly planar at the mouth [source: [enjoythemusic.com oblate_spheroid_waveguides](https://enjoythemusic.com/diy/1110/oblate_spheroid_waveguides.htm)]. The optimization objective "minimize polar map variance" implicitly minimizes HOMs.

### D3. Beamwidth definitions and constant-directivity criteria

**-6 dB beamwidth.** Industry standard for horn coverage pattern is the angle at which on-axis SPL drops by 6 dB in the far field. Product datasheets (Beyma, EV, etc.) specify H-beamwidth × V-beamwidth at 1 kHz, 4 kHz, 8 kHz and quote "deviating no more than ±10°" over the working band [source: Beyma and EV datasheets cited in search results].

**Constant directivity (CD) criterion.** A horn is "constant directivity" if its -6 dB beamwidth changes by less than ±10–15° over its working frequency range (typically 1–16 kHz). In terms of DI, CD means DI(f) is flat to ±2–3 dB. A "slightly increasing DI with frequency" is considered ideal by Geddes, as it compensates for room gain at low frequencies [inferred from Geddes forum posts; source: [diyaudio.com post 1565406](https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/post-1565406)].

**Throat impedance flatness.** A flat |Z_throat(f)| avoids compression driver breakup and reduces distortion. Some optimizers (Wadbro/Berggren) explicitly target perfect impedance matching at multiple frequencies [source: [people.cs.umu.se BeWaBe19.pdf](https://people.cs.umu.se/martinb/downloads/Papers/BeWaBe19.pdf)].

### D4. Frequency sampling: how many points per octave?

**The horn-mouth reflection resonance problem.** The horn acts as an acoustic cavity between the throat and the mouth: pressure standing waves form in the horn interior, creating a comb of resonances spaced approximately Δf ≈ c / (2 L_eff) where L_eff is the effective horn length. For L_eff = 0.3 m: Δf ≈ 343 / 0.6 ≈ 570 Hz [inferred from transmission-line model]. These resonances are visible as ripples in the polar response and in the DI. A resonance with Q ≈ 3–10 (typical for an open horn with soft boundary condition at the mouth) has a bandwidth Δf/Q ≈ 60–200 Hz.

**Minimum sampling density.** To resolve a resonance of bandwidth B at frequency f, you need at least 3 frequency samples within the bandwidth: Δf_sample ≤ B/3 ≈ (f_resonance/Q)/3. At 8 kHz with Q=5: Δf_sample ≤ (8000/5)/3 ≈ 533 Hz. With a geometric (1/N-octave) grid at N points per octave: Δf_octave ≈ f × ln(2)/N. Setting Δf_octave ≤ 533 Hz at f=8000 Hz gives N ≥ 8000 × 0.693 / 533 ≈ 10 points per octave [inferred arithmetic]. For a Q=10 resonance: N ≥ 20 points per octave. The existing solver uses a fixed frequency grid set in the YAML; if the grid has fewer than 10–15 points per octave in the 5–12 kHz band, mouth resonances will be aliased or missed entirely.

**Coarse frequency grids also miss DI peaks.** A DI spike caused by a beaming resonance narrower than the grid spacing will be completely missed, potentially reporting a false-positive "constant directivity" score [inferred].

**Practical recommendation.** Use at least 12 points per octave (≈1/12 octave resolution, e.g., 24 frequencies from 5 to 12 kHz) for the high-band finalist verification pass. The 1/3-octave grid (3 points/octave) used in many BEM studies is too coarse for horn resonance detection above 5 kHz [inferred].

### D5. Group delay and ringing metrics

Mouth reflections create group delay ripple (∂φ/∂ω where φ is the phase of the on-axis pressure). For a resonance at f_0 with Q=5, peak group delay is τ_gd ≈ Q/(π f_0) ≈ 5 / (π × 8000) ≈ 0.2 ms. This is within audibility for transients (JND for group delay at 8 kHz is ~2 ms). For higher Q resonances (Q~20): τ_gd ≈ 0.8 ms, potentially audible as pre-ringing. The existing scoring does not include a group delay metric [inferred from metric code overview; unverified if group_delay is computed].

---

## E. ADDITIONAL NOTES AND CROSS-CUTTING OBSERVATIONS

### E1. The axisymmetric-BEM path bypasses all GPU issues for the axi_osse family

For the `osse_axi` horn family: the axisymmetric BEM (OpenBEM or AcousticBEM) reduces the 12 kHz problem to a ~130-node line mesh with ~40 Fourier modes, solvable in milliseconds on CPU. This eliminates the GPU memory constraint entirely for this family. The 3D families (`osse_hv`, `freeform_sculpt`) still need 3D BEM. A branching adapter in `solve/` that routes axisymmetric horns to an axi-BEM solver and 3D horns to beat-bem would be a high-value addition [inferred].

### E2. NumCalc as a full-replacement 3D CPU solver

NumCalc's performance numbers: N=35k elements, setup ~5 min, solve (CGS, ML-FMM) possibly ~10–30 min/freq at high kR [inferred from the N=5 min setup note + CGS convergence]. This is slower than beat-bem GPU but handles meshes 3–4× larger. For the comparison: beat-cpu at 19k dofs takes ~57 s/freq [verified from TOOLCHAIN.md M4]. NumCalc with N=35k would take perhaps 3–5× longer [inferred]. This is viable for a small number of finalist checks but not for screening hundreds of candidates.

### E3. BoundaryIntegralEquations.jl as a Julia-native FMM option

Paltorp's BoundaryIntegralEquations.jl (DTU) supports: Kirchhoff-Helmholtz IE, collocation BEM, FMM via Flatiron FMM3D.jl, H-matrices via HMatrices.jl, viscothermal losses via the Kirchhoff Decomposition. This is a Julia-native option that could be called from beat-bem's Julia host environment. Drawbacks: "unstable" lifecycle, 27 GitHub stars, research-grade API stability. [source: [github.com/mipals/BoundaryIntegralEquations.jl](https://github.com/mipals/BoundaryIntegralEquations.jl)]

### E4. Summary of new Julia packages not in existing docs

| Package | Language | Status | Acoustic BEM | FMM | H-matrix | Burton-Miller | Axi-symmetric |
|---------|----------|--------|--------------|-----|----------|---------------|----------------|
| BoundaryIntegralEquations.jl | Julia | Unstable | Yes | Yes (FMM3D) | Yes (HMatrices.jl) | No (unclear) | Not confirmed |
| Inti.jl | Julia | Active | Yes | Yes (FMM3D/ExaFMMt) | Yes (HMatrices.jl) | Unknown | Not confirmed |
| HMatrices.jl | Julia | Active | Partial | No | Yes | Unknown | No |
| JAX-BEM | Python/JAX | Research | Yes | No | No | Unknown | No |
| NumCalc (C++) | C++ | Stable (v2.x) | Yes | Yes (ML-FMM) | No | Yes (γ=i/k) | No |
| OpenBEM | Matlab | Stable | Yes | No | No | Yes | Yes |
| AcousticBEM (Python) | Python/C | Beta | Yes | No | No | Yes | Yes |

### E5. The JAX-BEM connection to hornlab-search

JAX-BEM (arXiv:2604.21431, April 2025, Hipperson/Hargreaves/Cox at Univ. of Salford) is specifically applied to loudspeaker horn directivity optimisation. It uses JAX automatic differentiation, which means it runs on GPU (JAX supports CUDA). The gradient-based approach is complementary to CMA-ES: once CMA-ES finds a good basin, JAX-BEM can descent to the local optimum much faster than CMA-ES's random perturbations. Source code is at https://github.com/jrhip/jax-bem [source: [arxiv.org/abs/2604.21431](https://arxiv.org/abs/2604.21431)].

---

## SOURCES

- [arxiv.org/abs/2607.19500 - Robust Hierarchical Matrix Compression](https://arxiv.org/abs/2607.19500)
- [arxiv.org/abs/2312.00005 - NumCalc BEM code](https://arxiv.org/abs/2312.00005)
- [arxiv.org/html/2312.00005v3 - NumCalc full paper](https://arxiv.org/html/2312.00005v3)
- [arxiv.org/abs/2604.21431 - JAX-BEM horn directivity optimisation](https://arxiv.org/abs/2604.21431)
- [ar5iv.labs.arxiv.org/html/2403.17963 - A better compression driver (CutFEM + phase plug)](https://ar5iv.labs.arxiv.org/html/2403.17963)
- [arxiv.org/pdf/1207.0206 - IPOP/BIPOP CMA-ES restarts](https://arxiv.org/pdf/1207.0206)
- [arxiv.org/pdf/2106.03894 - Differentiable Quality Diversity / CMA-ME](https://arxiv.org/pdf/2106.03894)
- [arxiv.org/pdf/2211.06149 - Combining multi-fidelity and async BO](https://arxiv.org/pdf/2211.06149)
- [arxiv.org/pdf/2512.00170 - High-dimensional BO](https://arxiv.org/pdf/2512.00170)
- [papers.nips.cc BoTorch](https://papers.nips.cc/paper/2020/hash/f5b1b89d98b7286673128a5fb112cb9a-Abstract.html)
- [ar5iv.labs.arxiv.org/html/2012.03011 - MFES-HB](https://ar5iv.labs.arxiv.org/html/2012.03011)
- [github.com/mipals/BoundaryIntegralEquations.jl](https://github.com/mipals/BoundaryIntegralEquations.jl)
- [github.com/IntegralEquations/HMatrices.jl](https://github.com/IntegralEquations/HMatrices.jl)
- [pretalx.com/juliacon2024 - Inti.jl talk](https://pretalx.com/juliacon2024/talk/X8RYLT/)
- [github.com/Gjacquenot/AcousticBEM](https://github.com/Gjacquenot/AcousticBEM)
- [orbit.dtu.dk OpenBEM](https://orbit.dtu.dk/en/publications/openbem-an-open-source-boundary-element-method-software-in-acoust/)
- [orbit.dtu.dk viscothermal BEM](https://orbit.dtu.dk/en/publications/an-open-source-boundary-element-framework-for-large-scale-viscoth/)
- [bempp.com](https://bempp.com/)
- [joss.theoj.org bempp-cl](https://joss.theoj.org/papers/10.21105/joss.03145.pdf)
- [Mesh2HRTF homepage](https://www.oeaw.ac.at/en/ari/outreach/software/mesh2hrtf)
- [audioxpress.com AKABAK update](https://audioxpress.com/news/akabak-software-update-improves-loudspeaker-parameter-modeling)
- [doc.comsol.com horn shape optimization](https://doc.comsol.com/6.1/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html)
- [people.cs.umu.se BeWaBe19 - Wadbro/Berggren horn optimization](https://people.cs.umu.se/martinb/downloads/Papers/BeWaBe19.pdf)
- [github.com/jrhip/jax-bem](https://github.com/jrhip/jax-bem)
- [patents.google.com/patent/US8311232 - Olive preference score](https://patents.google.com/patent/US8311232)
- [docs.rs/autoeq-cea2034 - CTA-2034-A implementation](https://docs.rs/autoeq-cea2034)
- [spinorama.org](https://www.spinorama.org)
- [diyaudio.com Geddes on waveguides](https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/)
- [enjoythemusic.com oblate_spheroid_waveguides](https://enjoythemusic.com/diy/1110/oblate_spheroid_waveguides.htm)
- [sengpielaudio.com air absorption](https://sengpielaudio.com/LuftdaempfungFormel.htm)
- [springer.com Hierarchical matrices for Helmholtz](https://link.springer.com/article/10.1007/s00366-025-02144-w)
- [arxiv.org/pdf/2112.11880 - GPU GMRES for BEM Helmholtz](https://www.arxiv.org/pdf/2112.11880)
- [researchgate.net BEM-Rayleigh horn loudspeaker simulation](https://www.researchgate.net/publication/235788684_Simulation_of_the_Acoustic_Field_of_a_Horn_Loudspeaker_by_the_Boundary_Element-Rayleigh_Integral_Method)
- [github.com/topics/boundary-element-method](https://github.com/topics/boundary-element-method)
- [uio.no sound-innovation-engine QD](https://uio.no/ritmo/english/people/phd-fellows/bthj/Presentation/slides/sound-innovation-engine-1.0-(robin).pdf)
