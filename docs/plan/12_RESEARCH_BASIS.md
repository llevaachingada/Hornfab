# 12 RESEARCH BASIS

What the hardening pass found, what it changed, and what is still unknown. Read this if you want to know why the plan looks the way it does. Agents do not need it.

Every claim is labeled **[verified]** (read from a primary source this session), **[inferred]** (derived from verified facts, with the derivation shown), or **[open]** (must be measured).

---

## 1. The finding that restructured the plan

**[verified]** Collin already built a modular HornLab ecosystem. These are separate, installable repositories:

| Repo | Import | What it is | License | Commits |
|---|---|---|---|---|
| `m3gnus/hornlab-waveguide-mesher` | `hornlab_mesher` | Canonical OSSE / R-OSSE / ICW / FREEFORM waveguide geometry and gmsh mesher, extracted from HornLab. CLI `hornlab-waveguide`. | AGPL-3.0 | 250 |
| `m3gnus/hornlab-beat-bem` | `hornlab_beat_bem` | BEAT Engine Julia BEM packaged as a Python library. GPU-first: CUDA, ROCm, Metal, CPU. | GPL-3.0-or-later | 67 |
| `m3gnus/hornlab-bempp-bem` | `hornlab_bempp_bem` | bempp-cl BEM solver, same `solve_frequencies` / `SolveConfig` shape. Cross-platform OpenCL / Numba. | AGPL-3.0 | 81 |
| `m3gnus/hornlab-metal-bem` | | Apple Silicon Metal solver | AGPL-3.0 | |
| `m3gnus/hornlab-plots` | `hornlab_plots` | Directivity heatmaps, polar plots, FR, DI, impedance, beamwidth, group delay, sphere power metrics. 11 themes. | AGPL-3.0 | 57 |
| `m3gnus/waveguide-generator` | | The React + FastAPI app that consumes all of the above. v0.3.5. | AGPL-3.0 | 1,341 |

**Three consequences:**

1. **The name `hornlab` is taken.** The v1 plan named our package `hornlab`, which would collide with four of Collin's packages in the same Python environment. Renamed to `hornlab-search` / `hornlab_search`, which reads as a sibling module in his family rather than a competitor. If Collin would rather we stayed out of his namespace, rename to `hornseek`; it is one line in `pyproject.toml`.

2. **We should not write a mesher or a solve harness.** `hornlab_mesher.build_from_config()` and `hornlab_beat_bem.solve_frequencies()` do those jobs, are maintained, and are what Collin's GUI uses, so our results stay comparable with his. The v1 plan's task 04 (write a mesher) and most of task 05 (drive a CLI, parse NDJSON, read run directories) are deleted.

3. **What is actually missing from this ecosystem is a search layer.** Nothing in any of those six repos optimizes anything. That is the honest scope of our contribution and it is a much better-defined one.

### A correction to the v1 plan

**[verified]** The v1 plan built task 05 around `blab project solve <project>.blab.json --request overlay.json --events ndjson --output <dir>`.

The `boundary-lab` README documents only `blab gui` and `blab server --host ... --port ... --solver ...`. The `--request ... --events ndjson --output ...` CLI shape is **waveguide-generator's** `wg solve`, not Boundary Lab's. The v1 plan conflated the two. A full task would have been built against a command that may not exist.

The `.blab.json` project format, the solve-request overlay, and the run-directory reader are all gone from the plan. We call a Python function instead.

---

## 2. The precision question, answered without installing anything

**[verified]** `hornlab-beat-bem`'s README states the formulation is **"Float32 throughout"**, with the GMRES Krylov space carried in Float64 over the Float32 operator.

This reverses the v1 plan's central worry. Float64 on a consumer GeForce runs at 1/64 of Float32, which would have made the RTX 4070 a poor BEM card. It does not apply. The solver is Float32, and the 4070 is a reasonable card for it.

### The memory model is now exact, not estimated

**[verified]** The README gives two operator-memory datapoints for the fused Burton-Miller path:

| P1 dofs | Operator memory |
|---|---|
| 1,974 | 31 MB |
| 20,422 | 3,337 MB |

**[inferred]** Both are exactly `8 * N^2` bytes:

```
8 * 1974^2  = 31.2 MB    ✓
8 * 20422^2 = 3337 MB    ✓
```

8 bytes per entry is `complex64`, which is Float32 complex. So the operator is a **dense complex64 matrix**, and memory scales as `N^2` in **P1 dofs**, not elements.

```
VRAM_MB  =  8 * N_dof^2 / 1e6
N_dof_max =  sqrt( usable_bytes / 8 )
```

On an 8 GB card with ~6.5 GB usable, that is **28,500 dofs**. The plan caps at 24,000 for headroom.

**[inferred]** For a closed triangular surface mesh, Euler's formula gives `V = F/2 + 2`, so **dofs are about half the triangle count.** The v1 plan's caps were stated in elements and were conservative by a factor of two on top of a wrong precision assumption. Net effect: the usable mesh is roughly **4x larger** than v1 assumed, which raises the frequency ceiling by about 2x.

**[verified]** Boundary Lab's own documentation elsewhere publishes roughly 800 MB at 20,000 elements, which does not match `8N^2`. The fused path is documented as using **6.00x less** operator memory than the four-operator path, so the 800 MB figure is not the four-operator path either. The two numbers are not reconciled. The plan uses `8N^2`, because it is confirmed by two independent datapoints to three significant figures, and task 02 measures the real peak anyway.

### A throughput model, grounded in bandwidth

**[verified]** RTX 4070 Laptop GPU: AD106, 4,608 CUDA cores, 8 GB GDDR6, 128-bit bus, **256 GB/s**, 15.6 TFLOPS FP32, 35 to 115 W TGP.

**[verified]** The solver uses GMRES with `BLAB_BEAT_GMRES_TOL` defaulting to `1e-5`, measured iteration counts of **51 to 119** at a stricter 1e-6, a budget of one LU's matvecs before falling back to LU, and an adaptive crossover near **3,000 dofs** below which it uses a direct solve.

**[inferred]** A dense GMRES matvec reads the whole operator, so it is bandwidth-bound:

```
t_matvec = 8 * N^2 / 256e9 seconds
```

| N dofs | Operator | One matvec | ~100 iters | x12 freqs (screen) | x25 freqs (verify) |
|---|---|---|---|---|---|
| 8,000 | 0.51 GB | 2.0 ms | 0.20 s | **2.4 s** | |
| 16,000 | 2.05 GB | 8.0 ms | 0.80 s | | **20 s** |
| 24,000 | 4.61 GB | 18.0 ms | 1.80 s | | 45 s |

Assembly is `N^2` kernel evaluations, roughly 1.3e10 flops at 8,000 dofs, which is well under a second at 15.6 TFLOPS and is not the bottleneck at these sizes.

**[inferred] Screening should land near 4 to 8 seconds per candidate including meshing and Python overhead, so roughly 450 to 900 candidates per hour.** The v1 plan assumed 10 to 120 seconds. This is the single number that decides what kind of search is possible, and it must be measured in task 02 before anyone trusts it.

**[verified]** Cold start is 12 to 15 s on CPU and about 41 s on Metal; a **persistent worker drops later starts to about 0.01 s**. CUDA's first run "pulls several GB". This makes worker lifecycle a first-class requirement: warm once per search, `detach_workers()` between runs, never `shutdown_workers()` mid-search. At 4 s per candidate, a 12 s cold start per candidate would quadruple the cost of the entire project.

---

## 3. The three DISCOVER items from v1, all resolved from source

### DISCOVER-1: precision. **Resolved.** Float32 throughout, Float64 Krylov. See above.

### DISCOVER-2: symmetry. **Resolved.**

**[verified]** `hornlab_mesher` takes `quadrants` of `1234`, `12`, `14`, or `1`, and maps reduced grids to a solver flag:

| `quadrants` | Solver `native_symmetry_plane` | Domain |
|---|---|---|
| `1` | `yz+xz` | quarter |
| `12` | `xz` | half |
| `14` | `yz` | half |
| `1234` | none | full |

`SolveConfig(native_symmetry_plane="yz+xz")` is the quarter case and appears in the README's own example. Quarter symmetry is a 4x reduction in dofs, which is a 16x reduction in operator memory, which is roughly a 2x gain in frequency ceiling. Use it by default for symmetric designs.

**[verified]** The mesher warns that quarter meshes must be solved with the matching flag. A mismatch is a silent wrong answer, so the plan makes the two values derive from a single source and tests the pairing.

### DISCOVER-3: physical tags. **Resolved exactly.**

**[verified]** From `hornlab_mesher/tags.py`:

| Tag | Name | Meaning |
|---|---|---|
| 1 | `SD1G0` | rigid wall |
| 2 | `SD1D1001` | primary source (the driver) |
| 3 | `SD2G0` | enclosure wall |
| 4 | `I1-2` | interface |
| 8 | `mid_chamber` | MEH mid chamber |
| 9 | `mid_port_interior` | MEH port interior |
| 10 | `mid_port_exit_left` | MEH port exit |
| 11 | `mid_port_exit_right` | MEH port exit |
| 12 | `mouth_aperture` | mouth aperture |

These are ABEC-compatible names. The v1 plan invented `throat` / `wall` / `mouth_rollback` / `baffle`, which would have produced meshes the solver could not bind.

**Tags 8 through 11 are multiple-entry-horn structures.** The mesher already has MEH scaffolding, which means the MEH line of the project is reachable through this stack rather than needing a separate one.

---

## 4. The geometry we would have written already exists

**[verified]** `hornlab_mesher` supports four formula families:

| Family | Parameters |
|---|---|
| **OSSE** | `r0_mm`, `a_deg` (coverage), `a0_deg` (throat angle), `L_mm`, `n`, `s`, `q`, `k`, `rot_deg`, `h`, `s1`, `s2` |
| **R-OSSE** | `R_mm`, `tmax`, `m`, `r`, `b`, `s1`, `s2`, `k`, `q` |
| **ICW** | `termination` (flat_baffle or rollback), curvature controls `kappa0`, `theta1`, `hold_start`, `hold_end`, `kappa_abs_max`, `dkappa_ds_abs_max`, `n_coeff`, `icw_coeffs` |
| **FREEFORM** | `profileH` and `profileV`, each 2 to 64 `[z, r, angleDeg]` points; `crossSections` at 2 to 32 stations using `circle`, `ellipse`, `superellipse` (exponent 2 to 16), or `rounded_rectangle` |

**FREEFORM is, almost exactly, the parameterization the v1 plan specified from scratch**: independent horizontal and vertical meridional profiles, with superellipse cross-sections blending along the length. Writing it again would have been a week spent reproducing something that exists and is tested.

Also present, which v1 listed as future "forks":

- **Gielis superformula**, as `gcurve_sf_a`, `gcurve_sf_b`, `gcurve_sf_m1`, `gcurve_sf_m2`, `gcurve_sf_n1` to `n3`, `gcurve_se_n`. OSSE only.
- **Superellipse cross-section** via `exponent` (default 2.0) and `aspect_ratio`.
- **Rounded-rectangle morphing** via `morph_target`, `morph_width_mm`, `morph_height_mm`, `morph_corner_mm`, `morph_rate`.
- **Throat extensions and slots**: `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm`, plus driver-adapter convenience keys. This is the throat-adapter bet, directly supported.
- **Enclosures** with fillet or chamfer edges and rounded-rectangle, ellipse or superellipse plan shapes.
- **ATH text import**, so any existing ath design can be read in as a seed.

### What the mesher explicitly refuses, which is where our geometry work goes

**[verified]** From the config schema: per-azimuth throat stretch raises `ConfigError` with the message "per-azimuth throat stretch is not supported yet". Native JSON strings, expressions, and per-azimuth forms are rejected; stretch must be a plain finite number.

**[verified]** Out of scope for the mesher entirely: slot, port, driver, rectangular horn, and cabinet builders, with a cabinet bridge in `hornlab_mesher.experimental` that is not supported API.

So the geometry gap is specific and nameable: **full per-azimuth control of the flare.** FREEFORM gives two profiles, H and V, and interpolates. Nobody has a low-order Fourier series in azimuth over the flare parameters. That is the geometry novelty opening, and the plan reserves a module for it rather than pretending it is covered.

### Mesh sizing does not take a frequency

**[verified]** The mesher takes `throat_res_mm`, `mouth_res_mm`, `rear_res_mm` in millimeters, and **"removed frequency, EPW, and curvature-sizing keys raise `ConfigError`."**

So elements-per-wavelength is ours to convert:

```
res_mm = 1000 * c / (epw * f_max)
```

**[verified]** `scale_to_metres` defaults to `true`, so the output `.msh` is in **metres**, which means `SolveConfig(mesh_scale=1.0)`, not the `0.001` in the beat-bem README's millimetre example. A factor-of-1000 error here would produce a perfectly plausible wrong answer, so the plan pins and tests it.

**[verified]** `max_triangles` defaults to 18,000 as a full-domain-equivalent ceiling, with `allow_large_mesh` to bypass. The plan sets `max_triangles` explicitly from the dof budget and leaves `allow_large_mesh` false, so the mesher keeps guarding us.

---

## 5. Two independent solvers, which is a better check than any test we could write

**[verified]** `hornlab-bempp-bem` exposes `solve(mesh, config)` and `solve_frequencies(mesh, frequencies_hz, config)` with a `SolveConfig` and `ObservationConfig`, returning a `SolveResult` carrying **complex pressure**, SPL, impedance and solver logs. It runs on OpenCL CPU or a Numba fallback, so it works on the same Windows box.

**[verified]** It ships ASRO68 validation gates comparing against pinned library results and an **independent ABEC fixture**, plus a smoke script asserting OpenCL and Numba agree. It warns that open-mesh results differ from the Metal backend because of the P1 space choice.

Two independently implemented solvers, in different languages, through a nearly identical Python interface, on the same mesh. Agreement between them is far stronger evidence than any self-consistency test, and it costs one CPU run. The plan makes this **CP-7b** and makes the solver layer a protocol with two implementations so swapping is a config value, not a code change.

**[verified]** BEAT also has a required CPU reference gate with **464 checks**. Our analytic sphere test is still worth having, but it is no longer the only external check.

---

## 6. Physics re-checked

| Claim | Status | Detail |
|---|---|---|
| Pattern-control break frequency | **[verified]** | `f0 = K / (d * theta)` with `K = 2.54e4 m*deg*Hz` (equivalently `1e6 in*deg*Hz`). Charlie Hughes, *Understanding Horn Directivity Control*. Worked example: 12 in mouth, 90 deg gives ~926 Hz, which the article rounds to "just above 900 Hz"; 45 deg gives ~1.85 kHz against the article's "approximately 1.8 kHz". The v1 plan hedged to 23,600 from a line-source derivation; the published constant is **25,400** and the two agree within 7%. **Use 25,400.** |
| Narrow axis needs the larger mouth | **[verified]** | Same source: halving the coverage angle requires doubling the mouth dimension to hold the same `f0`. For two axes to lose control together, the narrower axis needs a mouth larger by the ratio of the angles. |
| Higher-order throat mode | **[inferred, standard]** | `f11 = 1.8412 * c / (2*pi*a)`. At c = 343: 1 in gives 7,914 Hz, 1.4 in gives 5,653 Hz, 2 in gives 3,957 Hz. Recomputed and consistent. |
| Solid angle and DI | **[inferred, exact]** | `Omega = 4*arcsin(sin(th_h/2)*sin(th_v/2))`, `DI = 10*log10(4*pi/Omega)`. 75 x 45 deg gives 0.941 sr and 11.3 dB. Recomputed. |
| Pulsating sphere | **[inferred, standard]** | `|p(r)| = rho*c*U0 * (ka/sqrt(1+(ka)^2)) * (a/r)`. Still the right analytic benchmark. |
| Dipole and cardioid directivity factor | **[inferred, exact]** | Both integrate to Q = 3, DI = 4.771 dB. Two different patterns, same exact answer, which is why the plan tests both. |
| Lo's 1/N law for random arrays | **[verified earlier in project]** | Sidelobe floor approximately `-10*log10(N)`. 15 cells gives -11.8 dB. This is the combinatorial reason the tiling study came back at 0.12 dB. |
| Forward axis | **[verified]** | `hornlab-beat-bem`: horizontal cut in x-z, vertical cut in y-z, **+z forward**, centred on the global mesh origin. Confirms the v1 frame contract. |
| Balloon / DI grids | **[verified]** | "Spherical balloon/DI grids (theta-major) are also supported." DI is obtainable. The exact grid convention is **[open]** and task 02 reads it. |

### What was wrong in v1 and is now fixed

| v1 claim | Correction |
|---|---|
| `blab project solve` with a request overlay | That CLI is `wg`, not `blab`. Removed entirely; we call a Python function. |
| Physical names `throat` / `wall` / `mouth_rollback` / `baffle` | Real names are `SD1G0`, `SD1D1001`, `SD2G0`, `I1-2`, etc. |
| Assume `complex128`, cap at 6,000 / 15,000 elements | Float32 confirmed; `8N^2` bytes in dofs; caps now 8,000 / 16,000 / 24,000 **dofs**. |
| Mesh sizing via elements-per-wavelength keys | The mesher rejects EPW keys. We convert to `*_res_mm` ourselves. |
| `mesh_scale = 0.001` | The mesher writes metres by default, so `mesh_scale = 1.0`. |
| Write our own profile family, superellipse, rollback, gmsh writer | FREEFORM, superellipse, ICW rollback and the gmsh writer all exist. |
| Break-frequency constant 23,600 | Published constant is 25,400. |
| Partial results are normal and must be handled | beat-bem "raises errors rather than returning partial data silently". Simpler. |
| `beat_auto` backend | Not in the documented backend list. Backends are `cpu`, `metal`, `cuda`, `rocm` at the library level. `beat_engine_status()` does the auto-selection. |

---

## 7. Collin's proposal, checked against the literature

His message: *"an NN based approximation of the system that would allow for parallel solving of linear algebra rather than solving differential equations... If the approx is good enough, it could make using genetic much much more efficient."*

### Is it sound?

Yes, with one framing correction and one important refinement.

**The correction.** BEM already converted the differential equation into linear algebra. What the solver spends its time on is assembling a dense `N x N` complex matrix and running GMRES on it. So the NN is not replacing a PDE solve with linear algebra; it is replacing *that linear system* with a forward pass. His instinct about the target is right; the target is one layer further in than described.

**The refinement, and the part that makes the idea pay.** The efficiency argument for genetic algorithms is exactly right and it is quantifiable:

**[inferred]** NSGA-II or any population method needs roughly 100 individuals by 100 generations, so about 10,000 evaluations. At 4 s per BEM solve that is **11 hours**. At 4 ms of surrogate inference it is **40 seconds**, and batched on the GPU it is less. A surrogate does not make the search a bit faster, it moves population-based multi-objective search from "a weekend per run" to "interactive".

"Parallel" is also right in a precise sense. One BEM solve fills the card with a 0.5 to 4.6 GB operator, so the GPU does one solve at a time. A surrogate is batched: thousands of candidates in a single forward pass. The same 4070 goes from one design at a time to roughly 10^4 at a time. **The 4070 is a mediocre dense-BEM card and a genuinely good inference card**, so his idea plays to this hardware's actual strength.

### Does the literature support it?

**[verified]** Li, Ye and Liu, *A boundary-based Fourier Neural Operator (B-FNO) method for efficient parametric acoustic wave analysis*, Engineering with Computers, 2025. This is the closest published method to what Collin described:

- It writes the wave equation as a boundary integral equation and learns **the boundary solution** with a Fourier neural operator, then recovers the field anywhere through the boundary integral. Our geometry *is* a boundary, so this is the structurally correct architecture.
- **Frequency is encoded implicitly, through the incident pressure field `e^(ik.x)` on the boundary**, not as a scalar channel. The paper reports that feeding the wavenumber as a plain extra channel performed worse. That is a specific, non-obvious design decision we would otherwise have gotten wrong. Our analogue is the prescribed source field on the driver tag.
- Accuracy: 0.01% to 0.05% relative RMSE across their cases.
- Inference about 4.2 ms.
- **Training data: 3,000 to 25,600 BEM solves** depending on the case. At our inferred 4 s per screening solve, 10,000 solves is **11 hours**. That is a weekend on H's laptop, not a research program. This is the number that makes the whole idea concretely affordable.
- Limitations the authors state: errors grow near resonance; non-uniform frequency sampling was needed; heavy GPU memory in 3D (32M parameters for their 3D case); **only rigid scattering was tested, and radiation problems are left to future work**.

**[verified]** The inverse half of the idea has a direct precedent in a neighbouring field: *A neural operator-based surrogate solver for free-form electromagnetic inverse design* (arXiv 2302.01934), and *Data driven surrogate modeling of horn antennas for optimal determination of radiation pattern and size using deep learning* (Piltan, 2024) does exactly this for **electromagnetic** horn antennas.

### The caveat from our own earlier work, which still stands

The project's earlier research doc flagged **spectral bias**: ordinary networks learn smooth low-frequency functions easily and oscillatory ones badly, and Helmholtz solutions at audio frequencies are the oscillatory case. The practical implication recorded then was to train on *derived quantities* (beamwidth, DI, ripple, throat impedance), which are smooth functions of geometry, rather than on the raw field, which is not.

That is in tension with B-FNO, which learns the field. The resolution is that there are **two different surrogates** doing two different jobs, and they should be built in this order:

| | Metric surrogate | Field / operator surrogate |
|---|---|---|
| Maps | design vector to metrics | boundary geometry to boundary pressure |
| Smoothness | smooth, no spectral-bias problem | oscillatory, spectral bias is the central hazard |
| Data needed | **[inferred]** 2,000 to 5,000 solves | **[verified]** 3,000 to 25,600 solves |
| Model size | an MLP, under a million parameters | FNO, tens of millions |
| Delivers | **exactly Collin's stated goal: efficient GA** | arbitrary-geometry generalization, true inversion |
| Risk | low | real |
| Build | **phase 2, first** | phase 2, second |

The metric surrogate is the cheap, correct first step, it delivers the thing Collin actually asked for, and its training data is a free byproduct of the search we are building anyway.

### The test that decides whether a surrogate is helping

**[inferred]** Not RMSE. Hold out 500 BEM-solved designs and measure **rank correlation** between surrogate objective and true objective, plus the overlap between the surrogate's top 20 and the true top 20. A surrogate with mediocre RMSE but good ranking is useful for search; a surrogate with excellent RMSE and poor ranking is not. This is stated as a gate in `11_PHASE2_SURROGATE.md`.

**[verified, standard]** A surrogate-driven search must use an active-learning loop (ISMO or equivalent): search on the surrogate, verify the top candidates with real BEM, add those verifications to the training set, retrain. Without it, the search optimizes the surrogate's errors instead of the horn. This is not optional and it is built into the phase-2 design.

### Verdict

Collin's proposal is sound, has a 2025 published method family behind it, is affordable on the hardware in hand, and is testable with a sharp pass/fail criterion. The plan makes it reachable by building the dataset from day one rather than bolting it on later.

---

## 8. What is actually novel here

Being honest about this matters, because the project's stated aim is to do something that has not been done.

**Not novel.** BEM simulation of horns. Shape optimization of acoustic horns, which the Berggren school has done since 2003, including topology optimization since 2006. OSSE and R-OSSE waveguide families, which are ath's. Neural operators for acoustic **scattering**. Surrogate modeling of **electromagnetic** horn antennas.

**Settled by our own earlier work, and should not be reopened.** Aperiodic cell tiling. The study measured a 0.12 dB spread across six very different tilings against a 2.63 dB irreducible diffraction floor, and Lo's 1/N law explains why: it is a combinatorial limit, not a modeling-fidelity one. The sensitivity ranking from that study stands: path-length error 1.98 dB, septa blockage 0.42 dB, faceting 0.23 dB, tiling topology 0.13 dB.

**Plausibly unclaimed, in rough order of confidence:**

1. **A search layer over this specific stack.** Nothing in the six HornLab repos optimizes. The external-evaluation API says in as many words that "search ranges belong to the calling study". The hook exists and nobody has built the study.
2. **A neural operator for exterior *radiation* from a driven horn boundary.** B-FNO's authors explicitly list radiation problems as future work. Scattering is solved; radiation from a velocity-driven boundary is not.
3. **A public dataset of (waveguide geometry, full balloon) pairs.** No such corpus exists. It is a byproduct of (1) and it is the thing that makes (2) possible for anyone.
4. **Per-azimuth flare control.** The mesher refuses it today with "not supported yet". A low-order Fourier series in azimuth over the flare parameters is a geometry family nobody has searched.
5. **Mouth termination as a searched object rather than a chosen one.** Our own sensitivity ranking puts termination at the top of the list of things that control ripple, with roughly 2.6 dB available, and ICW already exposes curvature controls that nobody has optimized.

That list is modest enough to be true, and (1) and (3) are nearly certain because they are statements about what exists rather than predictions.

---

## 9. Coverage: every idea from the project docs, against this plan

| Idea | Where it was | Status in this plan |
|---|---|---|
| Aperiodic cell tiling | bet table, very high novelty | **Settled at 0.12 dB.** Recorded as closed. Do not reopen. |
| Interlocking non-convex cell mouths | bet table | Deprioritized by the same evidence. Buildable via FREEFORM if wanted. |
| Fractal / serrated mouth rim | visualization pass | Deprioritized. 0.23 dB faceting effect. |
| **Mouth termination as the real lever** | sensitivity ranking, ~2.6 dB available | **Primary target.** ICW `termination`, `kappa0`, `theta1`, `hold_*`, `kappa_abs_max` are all searchable parameters. |
| **Inverse-designed throat adapter** | bet table, "best effort-to-payoff ratio" | **Shipped as an example config.** `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm`, driver-adapter keys. Small, axisymmetric, fast, and produces a printable part. |
| Coverage-matched asymmetry | single-cell R3 | Covered. Independent H and V coverage angles are searchable in every family. |
| Energy-partition generator from a venue map | Method A | `targets/venue.py`. Cheap, no solver. Turns a room into a coverage target instead of typing 75 x 45. |
| Aperture synthesis, inverse Fourier | Method B | The Rayleigh pre-screen in `11_PHASE2`. Same FFT machinery as the tiling study. |
| Material-distribution topology optimization | Method C | Out of scope. Needs an adjoint and interior FEM. Named as a phase-3 fork with its prerequisite. |
| Differentiable BEM | Method D, "most important development" | Out of scope: requires modifying BEAT. The surrogate is the tractable substitute, and a trained surrogate is differentiable by construction. |
| **ML generative inverse design** | Method E | **`11_PHASE2_SURROGATE.md`**, with the dataset built from day one. |
| Monge-Ampere freeform wall | bet B3 | Partially reachable via FREEFORM H/V profiles. Fully reachable after per-azimuth control. Named as a fork. |
| Metamaterial / graded-admittance mouth | bet B1, highest payoff | **Blocked on a capability gap:** needs non-rigid impedance boundary conditions. Whether either solver supports them is **[open]** and task 02 checks it. Named honestly rather than promised. |
| Per-cell FIR steering, shared-aperture source | bet, highest product potential | Reachable: bempp exposes `Channel`, `Crossover`, `solve_channel_basis`, and WG has a `multi_channel` result kind. Phase 3. |
| MEH CD notch | MEH R1, "universal, documented, unsolved" | Reachable: mesher tags 8 to 11 are MEH chamber and port structures. Needs coupled interior modeling. Phase 3 with the seam identified. |
| MEH port-neighbourhood topology optimization | "best risk-adjusted bet" | Phase 3, after the search loop and the MEH geometry path are both proven. |
| Continuous annular slot entry | MEH B2 | `slot_length_mm` exists. Phase 3. |
| Quarter-wavelength MEH entry rule | physics reference | Preserved in the physics constants module as a design check, not a constraint. |
| Rhino / Grasshopper round trip | toolchain question | Not needed for search. The mesher writes **STEP** (closed B-rep solid, mm), which imports into Rhino directly. Better than the v1 answer. |
| Collaboration with Collin | explicit question | **Answered structurally:** we build in his module family, consume his packages, and emit designs in WG's parametric schema so a search result opens in his GUI. |

Two items are honestly blocked rather than quietly dropped: metamaterial termination (needs impedance BCs, capability unknown) and differentiable BEM (needs upstream changes). Everything else has a path.

---

## 10. The neural operator landscape, verified

Added after a second research pass over a survey report of neural-operator methods for acoustics. Every paper in that report was checked against a primary source. The survey was substantially sound; three claims were overstated, two findings it missed matter more than most of what it contained, and one number in it is the most decision-relevant figure in this whole document.

### 10.1 What is real

| Work | Status | What it actually does |
|---|---|---|
| **B-FNO** (Li, Ye, Liu) | **[verified]** *Engineering with Computers* 41(4):2393-2410, online 29 Jan 2025 | Boundary integral formulation plus FNO, mapping **boundary geometry and parameters** to boundary solutions; field recovered by the integral. **Exterior. 2D and 3D. Geometry varies across training samples** (ellipse semi-axes and orientation, resonator neck and cavity dimensions). Training sets 3,000 / 10,000 / 20,736. **Scattering; radiation listed as future work.** "Data will be provided upon request." No code statement. |
| **DB-FNO** (Li, Ye, Liu) | **[verified it exists]** *Journal of Sound and Vibration*, 2026, also SSRN 5572813 | Title confirms "frequency-dependent boundary conditions". The survey's specifics (rank-1 tensor decomposition, separable 1D FFTs, 0.007 to 0.010% rRMSE, submarine and speaker-matrix cases, radiation) are **[reported, unverified]**: both ScienceDirect and SSRN refused automated fetch. |
| **MAD-BNO** (H. Wu, H. Wu, Lu) | **[verified]** arXiv 2601.11222, 16 Jan 2026 | Learns boundary-to-boundary Dirichlet-Neumann maps from data **synthesized from fundamental solutions**, no simulations needed. Interior solutions recovered by boundary integral. **Validated on 2D Laplace, Poisson, Helmholtz.** No error numbers on the abstract page. No code. |
| **MscaleFNO** (You, Xu, Cai) | **[verified]** arXiv 2412.20183, *J. Comput. Phys.* 2025, DOI 10.1016/j.jcp.2025.114530. **Code: `yyc-rgb/MscaleFNO`, MIT, 19 commits** | Parallel FNOs on rescaled inputs `(c_i*x, c_i*a(x))`, trainable scales and weights, sine activations. Error reductions over plain FNO of roughly 10^4x (single frequency), 20x (multi-frequency), and 70x (Helmholtz at L=10). **Every experiment is 1D.** Higher dimensions are explicitly future work. |
| **CLBO** (Khan, Yao) | **[verified]** arXiv 2607.04407, 5 Jul 2026 | Maps **complex normal velocity on a vibrating surface to complex pressure at receivers**. Learned source and receiver bases joined by a complex surface-quadrature contraction. Reference data from a 3D lattice Boltzmann solver. Field error **0.184** versus complex DeepONet's 0.367; superposition error 1.31e-7; 1.83e4x faster than the reference solver. |
| **neuraloperator** | **[verified]** MIT, ~4.0k stars, `pip install neuraloperator` | Official FNO, plus Tucker-factorized TFNO whose README claims 10% of a dense FNO's parameters. The page does not state 3D support, GINO, DeepONet, or irregular-geometry support. |
| **EM inverse design precedent** | **[verified]** arXiv 2302.01934 | Modified FNO surrogate for EM scattering, used for gradient-based nanophotonic inverse design. Structurally the operation Collin described. |
| **AES 3D loudspeaker radiation FNO** | **[UNVERIFIED]** | The survey cites a U-shaped FNO on 3D Helmholtz in air with simplified loudspeakers, reporting **0.87 dB MAE at 500 Hz rising to 5.35 dB at 4 kHz**, 15x to 3,000x faster than BEM. The cited URL is an expired AES temp file and I could not reach the paper. **Treat the numbers as a hypothesis.** |

### 10.2 The most important number in the survey, even unverified

If the AES figures are right, a 3D FNO on loudspeaker-like radiation has **0.87 dB error at 500 Hz degrading to 5.35 dB at 4 kHz.**

Our metric tolerances are 0.3 dB on DI and 2 degrees on beamwidth, and the project noise floor we are trying to establish is around 0.1 dB. **A 5 dB surrogate cannot rank horn designs.** It could not distinguish the entire 2.63 dB diffraction floor the tiling study measured.

That single datapoint, if true, says a *field* surrogate is not usable for design ranking at the frequencies we care about, and it says so for exactly the reason our own earlier research doc predicted: spectral bias on an oscillatory field.

**[inferred]** The direction of that claim is corroborated by three independently verified sources, even though the numbers are not:

- MscaleFNO exists **because** plain FNOs fail on oscillatory, high-wavenumber functions, with measured plain-FNO relative errors of O(1) at a single frequency and 0.7 for Helmholtz at L=10.
- CLBO, on 3D resonant acoustics, reports **18.4% relative field error**, which is nowhere near design-ranking accuracy.
- B-FNO's own authors report errors growing near resonance and needing non-uniform frequency sampling to control them.

So the pattern across every verified source is consistent: **boundary-field surrogates for 3D oscillatory acoustics are not yet at design-ranking accuracy, and accuracy degrades with frequency.** That is the single most important finding of this pass, and it validates the staging already in `11_PHASE2_SURROGATE.md` rather than overturning it.

### 10.3 Three claims the survey overstated

**1. "The recommended architecture is DB-FNO."** The survey then says, four subsections later, to train on derived quantities because the raw field is not smooth. Those are contradictory recommendations: DB-FNO *is* the raw-field approach. The survey re-muddles a tension this plan had already resolved. The resolution stands: a **metric surrogate** and a **field surrogate** are two different objects with different data costs, different risk, and different payoffs, and the metric one comes first.

**2. "MAD-BNO could eliminate the training-data bottleneck entirely."** The "if" is carrying enormous weight. MAD-BNO is validated on **2D interior** Laplace, Poisson and Helmholtz. The abstract page states no error numbers, says nothing about exterior or unbounded domains, and says nothing about whether geometry varies between training samples. **[inferred]** Generating artificial data from fundamental solutions for an exterior problem is plausible, since placing sources inside the body is the classical method of fundamental solutions and does work for exterior Helmholtz. But the showstopper the survey does not mention is this: a boundary-to-boundary Dirichlet-Neumann map **on a fixed geometry** is a solver, not a design surrogate. For design we need it to generalize across *geometries*, and nothing in the paper addresses that.

**3. "MscaleFNO is a candidate solution for our high-frequency problem."** Every experiment in it is 1D, and the authors list higher dimensions as future work. The idea (parallel sub-networks on rescaled inputs) is sound and cheap to port, and the code is MIT-licensed and real. But adopting it is porting a 1D method to 3D, not applying a published 3D result.

### 10.4 Two things the survey missed, both of which help us

**1. MAD-BNO is closer to Collin's literal proposal than B-FNO is.**

Collin wrote: *"an NN based approximation of the system that would allow for parallel solving of linear algebra rather than solving differential equations."* MAD-BNO learns the operator that replaces **the linear solve**, and then recovers the field by an exact boundary integral. That is, almost word for word, what he described. B-FNO replaces the whole chain and learns an end-to-end map.

The distinction matters practically. A learned Dirichlet-Neumann map is a **drop-in solver replacement**: same mesh, same boundary integral, same post-processing, only the matrix solve is learned. It plugs in behind the `Backend` protocol in `solve/base.py` as a fourth backend and nothing else in `hornlab-search` changes. That is a far smaller and far more testable integration than an end-to-end geometry-to-response surrogate, and it fails loudly rather than quietly, because the boundary integral and the metrics are still exact.

**2. CLBO's complex-linear structure is the most directly stealable idea in the set, and it is free.**

CLBO is **linear in the excitation by construction**, so complex superposition, homogeneity, and zero response to zero excitation hold exactly, not approximately. Its measured superposition error is 1.31e-7.

Acoustics at our amplitudes is linear. Any surrogate that does not enforce this is spending capacity learning a property we already know. **[inferred]** Three consequences for us:

- A model linear in the drive gets scaling and multi-driver superposition exactly right for free, which is precisely what the multi-channel and per-cell-FIR-steering fork needs.
- It is a strong physical prior, so it should need less data for the same accuracy.
- It is a free correctness test for **any** surrogate we build: predict for drive `u`, for `2u`, and for `u1 + u2`, and check superposition. A surrogate that fails that is broken regardless of its RMSE.

Its input and output are also exactly ours: complex normal velocity on the vibrating surface in, complex pressure at receivers out. Its 18.4% error is a caution, not a disqualification, since it was trained against a lattice Boltzmann reference on a harder resonant problem.

### 10.5 The structural finding that connects phase 1 to phase 2

B-FNO's 3D cases reshape boundary data into 2D arrays, for instance 61x80 and 144x114, then lift to a latent dimension of 64. FNO needs a **structured grid** with meaningful periodicity to make FFTs sensible. An unstructured triangle soup does not provide one, which is the usual reason neural operators on arbitrary 3D surfaces are hard.

**`hornlab_mesher` already builds on a structured point grid.** Its config exposes `angular_segments` (default 64) and `length_segments` (default 32), described as the sampling of the fitted surface rather than the BEM element count, plus `preserve_grid` and a `surface_fit` mode; and its internal modules are named `profiles.build_point_grid` and `geometry.PointGridHornGeometry`.

**[inferred]** That is an `angular x length` tensor on the horn boundary, with the **azimuthal axis naturally periodic**, which is exactly the layout a Fourier layer assumes and exactly the reshaping B-FNO had to construct by hand. If that grid is reachable through the mesher's API, the single hardest data-engineering problem in building an acoustic neural operator is already solved for us by the geometry layer we were going to use anyway.

This is worth checking early and cheaply, and task 02 now does. If the grid is accessible, phase 2's input representation is settled. If it is not, it is a feature request to Collin, not a research problem.

### 10.6 What changes in the plan

| Change | Where | Why |
|---|---|---|
| Boundary trace capture moves from a fork to a **contract item** | `01`, `02`, `05`, `07` | Every boundary-centric method in section 10.1 trains on boundary solutions. Far-field alone cannot train any of them. Traces must be captured from the first runs or the dataset is the wrong shape. |
| The **excitation spec** is recorded on every dataset row | `01` section 13, `07` | B-FNO's verified finding is that frequency must be encoded through the source field on the boundary, not as a scalar channel. We cannot do that later if we never recorded what the source field was. |
| **Trace-to-field recovery** is promoted to a named capability | `05` | `hornlab_bempp_bem.evaluate_exterior_from_traces` exists. The boundary integral step is exact and must not be learned. It is also how a learned DtN map gets turned into a polar. |
| **Structured point grid** access becomes a task 02 discovery item | `02` | Section 10.5. Decides phase 2's input representation for the cost of one question. |
| **Multi-family sampling** becomes a dataset design requirement | `07` | B-FNO varies geometry across training samples; our dataset must too, or it can never test generalization across families. |
| A **superposition test** is added to the surrogate gates | `11` | From CLBO. Free, exact, and catches a broken surrogate that RMSE would pass. |
| A **learned DtN map as a fourth `Backend`** is named as the lowest-risk integration | `11` | Section 10.4. Smaller, more testable, fails loudly. |
| `neuraloperator` (MIT) and `yyc-rgb/MscaleFNO` (MIT) named as the reference implementations | `11` | Neither B-FNO nor DB-FNO nor MAD-BNO released code. Do not reimplement an FNO. |

### 10.7 The honest revision to the novelty claim

Section 8 above listed "a neural operator for exterior **radiation** from a driven horn boundary" as plausibly unclaimed. That survives this pass and is now better supported: B-FNO's authors say radiation is future work, in print. DB-FNO reportedly addresses it, so **verifying what DB-FNO actually did is now the highest-value single literature action in the project**, because it either narrows that gap or confirms it.

But the pass also sharpens the risk. Every verified 3D acoustic result is at an accuracy that is **one to three orders of magnitude short of what design ranking needs**. The opening is real and so is the reason nobody has walked through it.

---

## 11. ATH, the Gielis superformula, and GSA vs CMA-ES (added 2026-10-25, owner-directed)

Added after the owner's collaborator (applied mathematician) raised two questions: *"this super equation by ATH or AVE"*, and *"we may want to do a comparison of GSA and CMA-ES"*. One research pass over the primary sources (Batík's OS-SE and R-OSSE papers, the Ath 4.8.2 User Guide, Gielis 2003, the GSA literature, the CMA-ES literature), cross-checked against our own mesher and code. Companion dossier: [`docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md`](../research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md) — rewritten later the same day (2026-10-25, owner request) into the **P6 implementation plan v1.0**: the dossier content is folded into its §2–§3, and it adds the quarter-domain symmetry rules, the settled search box and guards (D1–D20), the bake-off protocol with pre-registered statistics, the GSA library audit, and the wave/dispatch structure for four parallel implementation lanes. Labels as in this document. Append-only, like §10; nothing above changed.

### 11.1 Ath, verified — the upstream context for OSSE and R-OSSE

**[verified]** Ath ("ADVANCED TRANSITION HORNS", at-horns.eu) is Marcel Batík's Windows command-line program that generates horn/waveguide **geometry and BEM meshes** from plain-text `.cfg` description files (Ath 4.x). Freeware ("free for non-commercial use"), no published source — "closed-source" is **[inferred]** from the binary-only distribution. It is **not an optimizer and not a solver**: the User Guide has no optimization chapter; it emits meshes, ABEC projects and reports. The search gap this project fills is upstream of Ath, not beside it.

**[verified]** Ath today runs as the geometry engine inside Boundary Lab ("bundled with permission from Marcel Batik"; solver = BEAT Engine) — the ecosystem documented in our `research/boundary_lab_0.5/*`. Community: diyAudio threads 338806 ("Acoustic Horn Design – The Easy Way (Ath4)") and 354772. The `.cfg` conventions (one `ItemKey[:tag] = Value` per line, `;` comments, `ex` expression values, unknown keys silently ignored) match what `bl_inventory.md` recorded from Boundary Lab's examples.

**[verified]** The OS-SE paper gives the profile as one closed-form curve (eq. 5, 0 ≤ z ≤ L):

```
r(z) = sqrt(k^2·r0^2 + 2·k·r0·z·tan(a0) + z^2·tan(a)^2) + r0·(1-k) + (s·L/q)·[1 - (1 - (q·z/L)^n)^(1/n)]
```

— a hyperbola (coverage half-angle `a`, throat half-angle `a0`, throat expansion `k`: k=1 pure oblate-spheroid, k=0 cone) plus a superellipse flare term (amount `s`, abruptness `n`, truncation `q`≈0.995) blended in with matching slope and curvature. These are exactly the mesher's OSSE knobs. R-OSSE (rev7, 2022) is a fully parametric `[x(t), y(t)]` construction from conic sections that can fold back — the free-standing rollback — with `R/a/r0/a0/k/r/m/b/q`; **[open]** the "R" is not expanded in the paper.

**[open]** Naming check: our `research/typologies/MESHER_TYPOLOGIES.md` expands OSSE as "Oblique Spherical Surface Element"; the paper's construction is oblate spheroid + superellipse (Freehafer 1940 / Geddes 1989–93 lineage). Verify at source and date-correct the local doc (the corrections-culture pattern).

### 11.2 The "super equation" is the Gielis superformula

**[verified]** Gielis, "A generic geometric transformation that unifies a wide range of natural and abstract shapes", *American Journal of Botany* 90(3):333–338, 2003:

```
r(φ) = ( |cos(m·φ/4)/a|^n2 + |sin(m·φ/4)/b|^n3 )^(-1/n1)
```

`m` = rotational symmetry (lobes/points), `n1` = overall blobbiness, `n2`/`n3` shape the two directions, `a`/`b` scale the axes. One formula spans circle → ellipse → rounded square → polygon → star → organic outlines. **The superellipse is the m=4, n1=n2=n3 case**, which is why Ath and our mesher treat superellipse and superformula as one family of outline curves. Gielis's grander "unifies natural shapes" claim is botanical, not acoustic; in horn design it earns its place as a compact, differentiable, few-parameter curve family **[inferred]**.

**[verified]** Ath uses it in two roles:

1. **Guiding curve** — a closed loop the horn surface must pass through at `GCurve.Dist` from the throat: `GCurve.Type` 1 (superellipse) / 2 (superformula), `GCurve.SF = [a, b, m, n1, n2, n3]`, `GCurve.Width`, `GCurve.AspectRatio`, `GCurve.Rot`. The mouth outline — hence the whole 3D form — can be a star, a rounded square, etc., while the profile family fills in everything else.
2. **Azimuthal wall-angle modulation** — the 2026 ATH CORE design (CC-BY-4.0) modulates coverage angle around the horn with the built-in `sf()`: `a = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10`.

**[verified]** This is the same knob vocabulary section 4 recorded ("Gielis superformula, as `gcurve_sf_*` — OSSE only"), and those keys are **already searchable design-space rows** in `hornlab_search/design/families.py` (asserted by `tests/test_design_families.py` as table rows). The plan README's quick fork #2 — "the Gielis superformula the project docs wanted, for the cost of a table row" — is now source-verified. What is missing for a featured campaign is only a catalog family + an `examples/` config with bounds anchored to a verified Ath reference case (proposal **P6a**; R9 satisfied: Gielis 2003 and the Ath User Guide are the published references).

**[inferred]** Relation to novelty item 4 (per-azimuth flare control, section 8): the superformula guiding curve is Ath's outline-level door to the same idea — it constrains the mouth outline the wall must pass through. The Fourier-in-azimuth opening is broader (the wall angle itself varying); they are complementary, and the Ath CORE `sf()` script is evidence practitioners already want exactly this.

### 11.3 "AVE" — unresolved

**[open]** No tool, equation, algorithm or author called "AVE" exists in the Ath literature, the User Guide, or the academic indexes checked. Likely a mishearing of **ABEC** (the BEM solver Ath exports to), **Ath4** itself, or **Gielis**. Action recorded in ISSUES: ask the collaborator to spell it; do not name anything "AVE" in configs or docs before that.

### 11.4 GSA, verified

**[verified]** Rashedi, Nezamabadi-pour & Saryazdi, "GSA: A Gravitational Search Algorithm", *Information Sciences* 179(13):2232–2248, 2009. N candidate solutions = N point masses; **mass ∝ fitness** (better = heavier); masses attract each other by simulated Newtonian gravity; gravity decays `G(t) = G0·exp(−α·t/T)`; only the `Kbest` heaviest agents exert force, Kbest shrinking linearly N → 1; positions update from the accelerations. Early: broad, exploratory pull. Late: weak gravity, one attractor → collapse onto the current best. Cost: O(N²) pairwise forces, **N objective evaluations per iteration**.

**[verified]** Documented weaknesses: `G0`/`α`/N/Kbest "are determined empirically … generality is compromised", with premature convergence the named target (arXiv:2205.06770); diversity loss (Sadhana 2017; *Information Sciences* 2023); local-optimum trapping (arXiv:1706.03608); cannot handle large-scale problems "on their own" without cooperative co-evolution (arXiv:2101.06630). Strengths are all early-run and low-dimensional: simple, broad initial exploration, fast initial descent.

### 11.5 GSA vs CMA-ES for our search layer

**[verified]** CMA-ES (Hansen & Ostermeier 2001; tutorial arXiv:1604.00772) samples a small population from `N(mean, σ²·C)` and updates the mean, the step size and the **full covariance matrix C** — it learns the local shape, scale and rotation of the landscape, i.e. the couplings between design knobs. Reference method on the BBOB/COCO continuous benchmarks (GECCO 2009). Bajer et al. 2019 (*Evolutionary Computation* 27(4)): surrogate-assisted CMA-ES is competitive at **~25–100 evaluations per dimension** (25–250 for ≤10-D). The tutorial's §B.5 treats penalty functions as first-class and warns the penalty must be sized so penalized vs feasible differences have similar magnitude — **our WP3 graded penalty is exactly this pattern**, and the graded (not cliff) form is also what protects the covariance/step-size adaptation.

**[verified — absence]** No published GSA-vs-CMA-ES head-to-head exists (Crossref, OpenAlex, arXiv searched; GSA papers compare against PSO/GA/DE/ABC). A "comparison" is our own experiment, not a literature result.

**[inferred]** For our profile — 3–20 continuous knobs per family, 4–60 s per GPU evaluation, one solve at a time, deterministic geometry failures graded rather than cliffs — CMA-ES remains the defensible default: small population (λ grows only ~logarithmically with dimension), each generation updates a *model* so information is reused, covariance adaptation follows coupled valleys (mouth ↔ length ↔ coverage), penalty handling first-class. GSA burns N evaluations per iteration and needs many iterations for its Kbest/gravity schedule to play out; at a few hundred evaluations it reaches single-digit iterations and then its documented collapse mode. The scheduled search upgrades stay as planned: WP11 restarts (IPOP/BiPOP) + the CMA-ME quality-diversity atlas. **GSA is not in any WP.**

**[inferred]** If the owner wants the comparison anyway (proposal **P6b**), the protocol that makes it meaningful: fix the **evaluation budget**, not iterations (e.g. 200–400 simulations); identical bounds, identical graded penalty, identical initial seed design; 5–10 algorithm-seed repeats; a Latin-hypercube/random-search baseline; report best-so-far and median per budget. Run it on the cheap 2-knob exponential family, or after the metric surrogate (`11_PHASE2_SURROGATE.md`) makes evaluations ~ms — at which point the bake-off is nearly free. Nothing in the plan depends on its outcome.

---

## 12. Boundary Lab's balloon: resolution, rendering, and frequency handling (added 2026-10-25, owner-directed; recorded for the GUI Balloon view W6 + the density-upgrade TODO W7)

Source basis: the committed BL source extraction `docs/research/boundary_lab_0.5/bl_inventory.md` (line-anchored to the original checkout `JWSound/boundary-lab`, GPL-3.0 — attribution carried; the checkout itself is no longer on disk) + the 2026-10-24 W6 source recon recorded in `docs/NEXT_DEV_PRIORITIES.md` (W6). We lift design/math ideas only, never BL code.

**[verified] Frequency handling.** BL's `project_preferences` defaults: `freq_min_hz` **200**, `freq_max_hz` **20000**, `freq_count` **41** — parsed as ints and **log-spaced** (float32; `live.py`); arbitrary/non-integer frequency sets go through `--request frequencies_hz`. Two quirks a GUI consuming BL-style data must know: GUI-order frequencies in `SolvedSystem` can be **non-monotonic (van der Corput)** from GUI/plugin solves, and the renderer must therefore sort/re-bin by frequency value, never by index. Our own stored grids: screen = 12 log-spaced points 500–10 kHz, verify = 25 points 300–16 kHz (config.py `mode_freqs`), with `grid.verify_points_per_octave` as the density knob.

**[verified] Balloon resolution is an angle-precision dial with a Fibonacci point count — the actionable density fact for this repo.** BL: `balloon_angle_precision_deg` default **2.5°**, clamped **0.5–15°**; the balloon is sampled on an **equal-area Fibonacci sphere whose point count is `round(41253 / angle²)`** — i.e. 2.5° → ~6 600 points, 1° → ~41 253, 0.5° → ~165 012 (quadratic cost in density). Equal-area property matters: it makes the spherical-DI integral a plain mean — BL computes spherical DI as `−10·log10(mean(10^(SPL_rel/10)))` over the Fibonacci balloon with SPL normalised to on-axis (`ui/balloon.py`). BL also derives beamwidth/shape from a **superellipse fit of the forward −6 dB contour** (shape exponent, residual, H/V beamwidth, aspect ratio, DI). Lift the maths, never the module: BL's balloon maths lives inside its Qt-importing `ui/balloon.py`. Our equivalent: `solve.balloon_points_screen/verify` (currently ladder 512 → 1024 → 2592 measured in the M3/WP5 pack, ΔDI-gated) — **our stored density is ~8–27× coarser than BL's default 6 600-point sphere**, which is exactly the "increase balloon density on higher-level runs" TODO: at verify/final tier, raise `balloon_points_verify` toward the thousands, at the measured GPU cost (balloon points bill field evaluation, not dofs). Note our stored layout carries the **sin(θ) unequal-area weighting** (balloon_grid/balloon_layout) — a web renderer must interpolate on the sphere, not the index grid.

**[verified] Rendering (W6 source recon).** BL's Balloon Plot is NOT a textured sphere: it is a **dB-to-radius blob** — `radius = max(spl − floor, 0)`, so shape AND colour both encode level (floor default −30 dB, on the 0 dB = on-axis normalisation); PyVista/VTK **smooth shading** with the **turbo** colour map; isobars are **white tubed contour rings drawn on the surface, offset ≈ 0.2 % of the extent**; the "radar slicer" interpolates a polar cut along **any great-circle meridian at any frequency via barycentric interpolation** over the sphere triangulation; the freq × angle (±180°, log-frequency) pane is a **fractional-octave smoothed, resampled filled-contour slice**. Exports use versioned per-balloon payloads (`BALLOON_EXPORT_SCHEMA_VERSION = 2`: metadata.json + topology.npz + spl_db.npy + radius_norm.npy). Our port target: the same visual grammar in three.js r160/vanilla JS over `response.npz`'s `spl_balloon_db` + `balloon_grid`/`balloon_layout` already stored per design — a rendering feature, no new computation.

**[inferred] GUI density consequence (feeds TODO W7).** Frequency density and balloon density are independent axes: freq count bills linearly per solve (our 12→25 point verify step is the coarse one by solver cost), balloon point count bills per field evaluation on the solve GPU, and BL's evidence says 41 log-spaced freqs × ~6 600 equal-area points is the reference "publication" density for a 1″ horn on 200 Hz–20 kHz. A verify-tier upgrade to ~41 logged freqs and `balloon_points_verify` in the 1 000–6 600 range (Fibonacci or our own layout) would put our stored balloons at BL-class fidelity for the web Balloon view — gated on the M3/WP5 measured ΔDI ladder and the 8 GB GPU budget (see `docs/NEXT_DEV_PRIORITIES.md` W7, added same day).

---

## 13. Typology-expansion + scoring research pass (added 2026-10-25, owner-directed)

Owner mission for this pass: understand the existing typologies, research new ones (biradial named must-research; salmon/X expansion; ATH waveguides; a broad shape sweep across web/forums), add per-typology baseline settings, and expand the GUI hybridize workflow. Research FIRST, owner picks, then build. Four lanes ran this pass (three dossier files + one read-only audit lane + one run-forensics investigation); everything below is their consolidated record, append-only. Companion dossiers (all dated 2026-10-25, in `docs/research/typologies/`):

- `BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md` — biradial / Iwata 300 / Joseph Crowe.
- `SHAPE_DISCOVERY_SWEEP_2026-10-25.md` — the broad shape sweep (70+ shapes, tags asymmetric / organic / rippled / multi-direction-gradient).
- `SALMON_X_HORN_EXPANSION_2026-10-25.md` — Salmon lineage corrections + X readings + expansion menu.
- The every-typology R9 audit lane and the scoring/seed investigation lane recorded their verdicts in 13.4 / 13.5 below (they intentionally wrote no files).

### 13.1 Biradial / Iwata 300 / Joseph Crowe

**[verified]** The biradial primary construction exists and is reachable: **US4308932A** (D. B. Keele Jr., JBL, filed 1980). Construction: circular throat -> exponential-area connector -> thin slot gap (~18 x 416 mm, ~23:1 aspect) -> power-series flared walls `y = a + b x + c x^n` (n = 4-6) in each plane; the H pair is a surface of revolution about its vertex, the V pair overlaid. Patent reference case: 80 x 36 deg, mouth 780 x 780 mm (L 815.1, throat 48.8), n_h 5.5 / n_v 4.0, 516 mm throat-to-gap + 299.1 mm gap-to-mouth; the length and mouth sums check, but the published W rule at 36 deg is inconsistent and a naive march on the H plane needs negative c — **the H pair lives in a swept frame**. EQU1/EQU2 are image placeholders in the HTML edition (R9-5). Gate shape for shipping: topology + the two consistent scalar checks + the gap aspect, NOT one scalar equation (R9-4). Attribution note: Keele's bio mentions two JBL Bi-Radial patents; the assignee query returns only this one — cite the one we read.

**[verified, negative]** Premise correction: **Joseph Crowe does not sell Iwata kits** (27 biradial product/CAD slugs on his site, zero Iwata products/articles, 2026-10-25). His "ES" biradial line is self-published: no expansion law, no per-plane angles, no independent measurements, white paper promised not published — **R9-3: do not ship, and do not reconstruct ES from photos**.

**[verified, negative]** Iwata 300 as a construction: **no primary source reachable** (Auto-Tech datasheet only: 590 x 320 x 450 mm, throat 50.8 mm, 450 Hz; marketplace "biradial" labels). **R9-2: STOP** — the in-repo `iwata_ar` stays "our reconstruction of the principle, never the product" (`JMLC_FAMILY_VARIANTS` §2.2), which both today's dossiers confirm.

**[open]** diyAudio threads 140190/166312/230122 were blocked by Cloudflare (direct + proxy) on 2026-10-25 — the practitioner pass is thin by infrastructure, and flagged rather than fabricated. Re-rank the menus when access exists.

### 13.2 The broad shape sweep (web/forums candidate pass)

Infrastructure note for that day: DDG captcha, Bing degraded (quoted terms ignored), Brave 429, Mojeek JS-wall, diyAudio 403 — so practitioner evidence is the weak layer, labeled as such.

**[verified, negative]** **"SIBINIC" resolves to no reachable source** (at-horns.eu `/sibinic.html` 404; no Wayback snapshot; no sitemap entry; zero GitHub hits). **DO NOT SHIP the name.** Batik's real formula-level asymmetric designs are:

- **ATH CORE** (CC-BY-4.0): `a(p) = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10` with `n = 6 + 1.5*cos^2 p`, `s = 0.6 + 0.23*cos^2 p` — a superformula-law coverage angle in azimuth over an OS-SE body.
- **Tritonia**: `alpha = 48.5 - 7*cos^5(2t) - 16*sin^12 t`, `s = 0.7 + 0.2*cos^2 t`, `k = 1, n = 3.7, q = 0.995`, then morphed to a rounded rectangle.
- **Quadratic-Throat Waveguide** (Hughes/Peavey white paper — read): conical bell + circular-arc throat whose included angle equals half the dispersion angle; round->rect via elliptical fillets; published measured harmonics (second -3..-4 dB, third ~-9 dB). Coefficients are withheld, so implement the documented arc rule, not a claimed replica.
- **Helical twist** (Batik's report of his lost Tritonia ancestor): cross-section rotates down the horn, `phi0(s) = twist*(s/L)^p` — author claims superior behavior, unpublished formulas; a labeled-experiment candidate only.

The repo's genuinely-absent classes (grep-verified against code + docs): a per-azimuth wall-angle law `a(phi)`; helical twist; odd `cos(phi)` single-sided asymmetry (explicitly refused by `grid.py` symmetry guards today); diffraction slot (Mantaray/Keele-CB are concept rows only); ripples along the length; Bessel/HCD/QT flare laws. Trademark discipline: Bi-Radial / Mantaray / Progressive Transition / Image Control / Complex Conic stay generic descriptors in code/config, manufacturers cited in docs. "Geddes quadratic-lobed" attribution is unresolved — verifiable Geddes is OS/OSWG (already the OSSE lineage), and no such typology was invented. Shortlist of 7 with costs in the dossier's §5: CORE/Tritonia azimuth-modulated OS-SE (~200 LOC), twist (~60, full-360 mesh cost), odd-cosine (~40-80), QTW (~100), slot-loaded dual-radial (~250-350; thin-gap class = deferred WP14 risk), mouth ripple/serration (~50), acoustic lens (large; needs a new mesh route).

### 13.3 Salmon lineage corrections + the X reading

**[verified]** The Salmon family literature, at source: **Vincent Salmon**, JASA 17(3) 1946 — theory pp. 199-211 (doi:10.1121/1.1916316) and the family paper pp. 212-218 (doi:10.1121/1.1916317); precursors 1939 measurements (JASA 10:256) and 1941/1942 abstracts. **J. E. Freehafer** (MIT) published the exact infinite hyperbolic-horn impedance in 1940 (doi:10.1121/1.1916061) — the hyperbolic member's math, not the family. **Harry Olson did not originate it**: Olson 1940 (1st ed.) contains zero "Salmon"/"hyperbolic"; the 1947 2nd ed. §6.19 codifies `S = S0*(cosh a + T sinh a)^2` with a T = 0.5 worked example and footnotes Salmon — Olson is the codifier/popularizer. Salmon's papers are plane-wave (Webster) theory; the spherical-wavefront application is Le Cléac'h -> Fourcade. "Hypex" is **not** a Salmon/Olson word (0 hits in both Olson editions): a modern contraction of hyperbolic-exponential.

Corrections from the lane's fetches (dated tables in the dossier; route to Report 2 §7): appendix A's "hyperbolic horn is T < 0" is wrong — the rule is **T < 1** (T=0 catenoidal, T=1 exponential); "Frehaufer" -> **Freehafer**.

**[verified]** The X-horn question splits into three distinct readings, each with its own knob consequence — the owner must pick:

1. **Rectangular mouth with a smoothed diagonal transition** (the AudioHorn (France) "X-Shape" family X21-X40 reading; their published story is "the diagonal measurement is as perfect as the horizontal"). W/H 1.60-1.65, D/W 0.55-0.61 across the family; dimensions/polar **images** published, geometry not — marketing referent, not a construction source.
2. **The literal X / star rim** — what `salmon_x_shape` builds today. Measured this pass: with the current knob sign the mouth opens along the diagonals; the **opposite sign is already reachable with zero code** via `g_stop_cos2k: [0, +0.25]` (the a4-depth term), giving the diagonal-IN reading.
3. **A cross-shaped cross-section** — no audio precedent found; the closest adjacent is the RF quad-ridge flared horn (Flygare & Pantaleev, IEEE TAP 2020, doi:10.1109/TAP.2019.2940529). Labeled-experiment territory only.

Also pinned this pass: the signed `x_amp` axis is cut by the 180 deg asymptote (`x_amp <= 180/stop0 - 1`), and **P-M4-2 is worse than recorded** — `ROWS_SALMON_MOD_STOP_RANGE = (120, 240)` is defined but **never enforced**; the code accepts any stop in (0, 360) except exactly 180. Expansion menu measured in-repo (costs): X v2 signed/decoupled knobs (~20 LOC; the sign-flip version is 0 LOC today), salmon family completion (`hypex` T>1 ~5 LOC, `hypex_angle` ~50 LOC, T-gradient ~45 LOC, spherical T bound config-only), **`fc` harmonics `g_fc_cos2k`/`g_fc_sin2k1`** (~80 LOC — the missing loading direction), rows-route G8 mouth shape (~80 LOC), salmon spindle/tractrix/OSSE splices (0 LOC, config+test).

### 13.4 The every-typology-makes-sense R9 audit

**[verified in-repo; audit lane reran the R9-J tests green, 34/34]** The verified core PASSES: conical, exponential, hypex/Salmon, tractrix, OSSE, the ICW/FREEFORM entries, Le Cléac'h T1/rollback/toroidal, and the salmon hypothesis rows (all explicitly labeled), grid ellipse/mod. The R9-J chain is complete and live: dossier gate (Fourcade fig 7 mouth width 467.30 vs 467.30 mm = 0.00), the test (`test_r9j_fourcade_fig7_validation_table`), the rows-route support, and the evidence echoes; the Fourcade PDF primary resolves.

Defects recorded for the closing commit (no behavior change without owner gates):

1. **`splice_osse_tractrix` claims C1 but is C0 on the shipped range.** The 2.0 deg match tolerance (profiles.py `_SPLICE_MATCH_TOL_DEG`) produces kinks up to 1.876 deg for `zs_frac` 0.425-0.575; the test only checks 0.5 and >2. Fix: bridge whenever |dTheta| > 0.5 deg, or relabel the direct-match band honestly.
2. **`lecleach_iwata_ar` name decision** (the one R9 flag that touches a shipped name): lib-1's dossier accepts the labeled reconstruction; the sweep says rename-gate ("never as 'Iwata'"). Surfaced to the owner; strict path = neutral rename (e.g. `lecleach_ar_evolve`) with attention to the legacy `lecleach_ar` kind-name collision.
3. **Six stale "Le Cléac'h disabled" sites** (`BETA_QUICKSTART.md:48`, `BETA_SESSION_PLAN.md:70`, `HANDOFF_BETA.md:43` + its :145 echo, `ISSUES.md:192`, `catalog.yaml:6`, `spherical_salmon.yaml:7`) — all contradicted by the live code/catalog and the R9-J evidence; historical/dated records (CONTINUITY 2026-10-22, TYPOLOGY_PLAN frozen text) stay untouched.
4. Label hygiene: the `organic` group header mislabels the (verified, axisymmetric) lecleach_rollback/toroidal entries; `throat_adapter` claims `hv` but its pinned seed/bounds are axisymmetric; `osse_baseline` says "10 searchable knobs" vs actual 9; `spherical_salmon`'s registry doc promises `{p}_stop_deg` while the code uses `{p}_max_wall_deg`; the internal `salmon_axisym` rows kind silently accepts `fc_v`/`x_amp` (i.e. a non-axisymmetric shape under an axisym name; unlisted/unconfigured/untested — cleanup candidate); the biradial dossier's C2 "salmon entries removed" sentence is false (superseded by the Salmon dossier's C-4).
5. **Free v2 candidates riding EXISTING kinds** (config-only; all materialized green by the audit lane; the first three are explicitly named in the frozen TYPOLOGY_PLAN but never shipped): `hyb_osse_h_lecleach_v`, `blend_osse_lecleach`, `splice_osse_lecleach` (after the splice fix), `hyb_osse_h_exponential_v`, `salmon_saddle` v2 parameter set, `lecleach_iwata_ar` 2-inch variant (needs a 2" brief/large envelope, not code), `lecleach_toroidal` JMLC-350 class (same note). Hybrids/blends/splices are OUR constructions — label `[inferred]`/"our hybrid" per the x_shape/T5 precedent.

### 13.5 Dispersion scoring + seed derivation (owner-directed; the "75x35 brief does not look like it" investigation)

The owner symptom: an existing design + a 75 x 35 brief, short run, dispersion nowhere near the target, and the geometry the search starts from ignoring the coverage entirely. Root cause verified from the owner's own run directories plus code reads:

1. **The brief's coverage never sizes the seed or bounds.** `load_brief`/`load_config` replace only target/weights (`config.py:657-659`); `materialize` reads only driver/envelope/shared depth (`registry.py:188-202`); the organic typologies additionally pin their OWN internal brief (e.g. `organic_rollback_1in` = 90 x 60), so the owner's brief only changes scoring, never geometry. Materialized proof: the seed is **byte-identical** for 75 x 35 vs 90 x 15 vs band_lo 300 vs 700 (`freeform_sculpt` seed = 370.2 x 370.2 mm round, aspect 1.00; salmon seeds 1.37-1.57; none near a 75 x 35 or 90 x 15 aspect).
2. **The K-law exists but has no design-side consumer.** `KEELE_K = 25400` (`constants.py:10`), `required_mouth_m()` (`targets/venue.py:70-76`); consumers are only the venue-map feasibility report (HTML) and report echoes — never `load_brief`, `load_config`, `materialize`, `DesignSpace`, or the GUI.
3. **The stated target is physically impossible inside the stated envelope.** K-law: 75 x 35 at 300 Hz requires mouths 1128.9 x 2419.0 mm vs the 500 x 400 envelope (13.7x the envelope area); 75 deg from a 500 mm wide mouth only above ~677 Hz; 35 deg V from 400 mm only above ~1814 Hz; a 90 x 15 vertical from 400 mm only above ~4233 Hz. Measured across the owner's own completed 110-eval, 0-failure freeform run: the **minimum mean-V over all 110 valid designs was 71.45 deg** (target 35), and the empirical per-frequency minima average 49.08 deg — the target is outside the reachable set, not under-searched.
4. **Scoring amplifiers:** `cov` is an equal-weight mean over the 12 screen freqs (`objective/terms.py:49-54`), and 61-87% of the cov loss sits at the five freqs below each best design's V break (irreducible in-envelope); `dislope` is a hostile competitor (slope-0 is unattainable over a decade with a fixed mouth; 30-42% of J in the salmon/lecleach runs); `freq_weights` reweights **only `rip`** (`objective/scalar_v2.py:229-234`), so no brief knob can mask the impossible band today; the screen tier sees exactly 500-10000 Hz (`config.py:26-30,765-785`) so band_lo 300 is never even scored; and there is no coverage-attainment gate/flag — a 43-58 deg V miss is still a ranked "best".
5. **Secondary defects found in the same forensics:** the grid self-approach `GeneratorError` escapes the mesh error-mapping (`mesh/grid_build.py:138-188` vs the try at `:183-188`) and lands as `kind="exception"`, flat 1000, un-memoized, retried (the 40-eval salmon run wasted 29/40); the GUI seed gate loads the typology's OWN brief, not the selected one (`gui/data.py:958-969`), so `lecleach_iwata_ar`/`lecleach_toroidal` seeds die under the user's 17.4 mm/8 deg driver with zero rows (zombie GUI jobs); campaign `is_compatible` reads `brief_sym` but never uses it, so an axisymmetric brief ran hv families (the 7040 campaign's 458 x 240 mm mouths); native FREEFORM ignores the brief's throat radius entirely (seed 12.7 mm vs brief 17.4); brief data hygiene: `7040.yaml` describes 90 x 90 but targets 50 x 50 (the ~92 x 92 results were CORRECT per target), `75x35.yaml`'s description says "Eighty by 40", and `load: 0.5` with `z_min: 0` is a dead term.

**Proposed fix order** (gated parts go to the owner menu): **(A)** brief-derived seed/bounds/mouth — optional explicit `target.f0_hz` (default band_lo), per-axis `d = KEELE_K/(f0*coverage)`, seed knobs + bounds around it, envelope-clipped targets flagged `feasible=false` + `f_break` (the frozen §11 Target schema gets an ADDITIVE key — owner amendment; derivation warns/flags, never hard-refuses, per the contracts' design-check rule); **(B)** co-score the attainable band — extend frequency weighting to `cov` (or objective v3 with a below-f0 mask) so the impossible band stops dominating the gradient (owner-gated; v3 is the non-retroactive route); **(C)** the pure bug fixes above; **(D)** only then weight/budget tuning — raising the cov weight FIRST is explicitly contraindicated (cov is already 88% of J in the 110-eval run; the target is unreachable, so weights chase the same wall). Validation checks to add (CPU-only): seed-must-materialize-under-the-selected-brief for every family x brief; a seed-mouth vs brief-derived-mouth ratio gate (0.5x-2.0x or `feasible=false`); cov-weighting actually changes cov; axi-brief x hv-family refusal. Latent hazard noted: `Design.hash()` does not bind the brief's driver/envelope, so two briefs can cross caches (fixing keys invalidates caches — owner-gated).

### 13.6 Baseline-settings direction (Phase D, owner-gated as global changes)

The per-typology baseline tables derive from (A)'s rule once approved: per-axis K-law mouth defaults, envelope-aware feasibility flags, and brief weight presets ordered as (B) prescribes. Existing typology defaults (`registry.DEFAULT_KNOBS`) stay untouched; baseline settings ship as typology-side configs until the owner opens the personal-brief session (deferred per the handoff).

### 13.7 The azimuthal-modulation / segmentizing synthesis (added 2026-10-25, owner-provided document, verified this session against the primary pages)

The owner supplied a collaborator's synthesis of how the ATH-class "puckered" horns are defined
and how a GA should encode them, and asked to verify it against this repo and save it. Every
load-bearing formula was checked today against the author's own pages (fetched in full); verdicts:

**[verified]** `alpha(theta) = 48.5 - 7 cos^5(2 theta) - 16 sin^12(theta)` and
`s(theta) = 0.7 + 0.2 cos^2(theta)` with `k = 1, n = 3.7, q = 0.995`
(at-horns.eu/tritonia.html, "The design of Tritonia" section, verbatim). Corrections to the
supplied document, all sourced:

1. **Tritonia's base is OS-SE, not R-OSSE.** The page: the design "uses two basic techniques:
   1) a parametrized OS-SE profile and 2) morphing it to a rounded rectangle", with alpha(theta)
   the "variable coverage angle parameter of the OS-SE formula". R-OSSE is the segmentizing
   article's WORKED EXAMPLE base, not Tritonia's. The structure of the claim (azimuthal
   modulation of an axisymmetric base) is exactly right; the Tritonia instance's base is OS-SE.
2. **The alpha(theta) law is "purely empirical"** (Batik's own words): a design recipe, not a
   derived physical law. R9 label: ship-attributable to the published page as an empirical recipe.
3. The supplied document omitted the mouth-termination law s(theta) and the fixed
   n = 3.7 / q = 0.995 / k = 1 that complete the published recipe.

**[verified]** The segmentizing math, verbatim (at-horns.eu/seg-horn.html, Batik, February 2024):

- `r'(theta) = r_S sin(theta_S) / (sin(theta_S) cos(theta) + (1 - cos(theta_S)) sin(theta))` (eq. 1,
  the straight-segment target; the worked example theta_S = 60, r_S ~ r(t_m) ~ 64 mm).
- `m(t) = sin(pi ((t - t_0)/(t_1 - t_0))^zeta)^kappa` for t in (t_0, t_1), 0 otherwise (eq. 2, the
  meander weighting; zeta = skew, kappa = sharpness; maximum at
  `t_m = t_0 + (t_1 - t_0)/2^(1/zeta)`; worked example t_0 = 0.8, kappa = 4, zeta = 0.75 ->
  t_m ~ 0.32). Lineage: Batik's own meander function from "Spherical Wave Forming" (Ath-AP1.pdf).
- `r'(t, theta) = r(t) + m(t) (r'(theta) - r(t_m))` (eq. 3, the transformed radius).
- `r_S` variants: edges-deformed (r_S = r(t_m)/cos(theta_S/2)) or the geometric average
  `r_S = r(t_m) sqrt(1/cos(theta_S/2))`; and the general target:
  `r'(theta) = r_S + delta sin(pi (theta/theta_S)^mu)^nu` (eq. 4; delta in mm).
- Worked-example base: R-OSSE `R = 200, r_0 = 12.7, a = 35, a_0 = 5, k = 1.5, r = 0.35, m = 0.75,
  q = 3.8, b = 0` (the same numbers a prior lane banked - consistent).

**[reported, unverified here]** The IET spline+GA/PSO paper ("Synthesis and analysis of multi-mode
profile horn...") and the BEM/GA acoustic shape-optimization paper: not fetched this session; kept
as the encoding-method precedents with the owner's attribution.

**[verified]** The staged-gene encoding maps ONE-TO-ONE onto this repo's shipped machinery
(the mapping table of 2026-10-25 chat, the search-layer reading):

| Supplied stage | Our surface | Note |
|---|---|---|
| Stage 1: axisymmetric R-OSSE / OS-SE base genes | `rosse_baseline` (the R-OSSE formula family, searched since M1) / OS-SE generator knobs | the mesher's own formulas |
| Stage 2: alpha(theta) coefficients as sum-of-cos/sine genes | the rows route: `fc(phi)` (the T3 law) + `g_stop_cos2k` / `g_stop_sin2k1` + the signed `g_x_amp` + the bend | shipped |
| Stage 2b: odd/asymmetric directions | `g_eps_m` (odd-cosine, full ring) + signed x + the ripple | landed 2026-10-25 |
| Stage 3: segmentizing genes (zeta/kappa/delta/mu/nu) | NOT built; our smoothstep windows (3t^2-2t^3) are the same object at fixed shape. Candidate: a rows modulation family implementing eqs 2-4 verbatim + | |
| Spline control-point genes | `freeform_sculpt` (11 control-point knobs) | shipped |
| Fitness (CD error / ripple / impedance / off-axis lobes) | `cov`/`rip`/`flat`/`load` + DI (+ the pending diagonal-consistency term) | shipped + one pending |
| Coarse-to-fine staged search | campaign practice: the base config first, then a modulation config seeded at the winner | practice |

The visual record of the puckers (TwinRay/Opus 12 mouth renders, analyzed this session via the
image lane): the rim FRAME is planar; the flare's approach to it undulates smoothly (one pinch per
edge, corners deepest - consistent with the shipped G9 `dz(phi) = -term cos^2(phi)` law's 2-lobe
shape plus edge rounding); the "figure-8" = the interior petal rosette, the "bullet" = the
squircle throat ring; no sharp corrugation facets anywhere. Details:
`docs/research/typologies/MOUTH_RIPPLE_SERRATION_RESEARCH_2026-10-25.md`.

Links (primary pages, all fetched 2026-10-25): at-horns.eu/tritonia.html (alpha(theta) + s(theta)
+ k/n/q + the published per-model Ath codes: ext/Tritonia.txt, ext/Tritonia-S.txt, ext/Tritonia-M.txt
+ the polars + the DIY gallery post links in the thread 338806);
at-horns.eu/seg-horn.html (eqs 1-4 + the meander lineage Ath-AP1.pdf);
release/R-OSSE Waveguide rev7.pdf (the segmentizing example's base) and
release/OS-SE Waveguide.pdf (the Tritonia base) remain the formula primaries.

---

### 13.8 Why the puckered shapes never appeared in the owner's own passes (added 2026-10-25, owner-directed diagnosis)

Owner question, verbatim intent: "I have not seen any of those types of geometry in any of the passes I've done;
I thought the software would randomly tweak knobs and do a genetic algorithm and figure out what works, without a
bunch of layers." The answer, all measured this pass:

1. **Their mental model is correct and needs no layering.** One CMA-ES run, all knobs as simultaneous genes,
   sampled within the config's bounds, scored by the balloon/beamwidth objectives - that is the whole mechanism,
   and it CAN reach the figure-8/bullet/puckered outline class, whose knob families exist (the per-azimuth
   stop/fc harmonic laws; the G8/G9 terms; and since 2026-10-25 the signed x, the odd-cosine eps, the
   mouth ripple).
2. **Why the passes still returned smooth shapes - three stacking causes, all measured:**
   a. *The objective could not reward the class.* `cov` was an equal-weight mean over the screen band, and
   61-87% of its loss sat below the geometry's K-law break frequency (physically uncontrollable in the
   envelope; §13.5). The outline/pucker details are 0.2-1 dB-class effects and were invisible under that
   handicap; `dislope`'s slope-0 target took another 30-42% of J. Fixed today: objective v3 (the below-f0
   mask + freq-weighted cov) + the K-law feasibility preflight that states honestly, per brief, what the box
   can hold BEFORE the run.
   b. *The shipped seeds and bounds never approached the class.* Every shipped typology seed sat at
   x_amp/bend/ripple = 0 with tight bounds; a short screen run (40-110 evals, sigma0 = 0.25 normalized) is a
   seed lottery around the seed - it started smooth and stayed smooth. The new-signed/eps/ripple knob families
   need campaign configs whose seeds/bounds AIM at the class (P8a).
   c. *No objective term read the diagonals.* The 45/135 deg balloon directions (stored on every design) are
   where the figure-8/puckered outlines act; nothing scored them (P8b).
3. **The collaborator's staged-gene document is an OPTIONAL refinement, not a requirement** (the owner's word
   recorded): coarse-to-fine = run the base config, then a modulation config seeded at its winner; the
   campaign's own seed plumbing supports the sequence without new machinery. The one-run search remains the
   model once the objectives/bounds are sane - which is exactly what 2026-10-25's fixes deliver.

## 14. Corner-mounted horns with room-aware asymmetric dispersion (added 2026-10-25, owner-directed)

Owner concept for this pass: a custom horn mounted where two walls meet the ceiling (an "up-corner"), one horn in each of the four corners of a rectangular room, its 3D dispersion shaped — asymmetric, tapering toward the room center — so that the four units together cover the room evenly across the frequency band. The owner's voice note read "Centennial frequency band"; we interpret it as "entire frequency band" — **[open]** confirm with the owner.

Method note, flagged rather than hidden: the librarian route was down today (four background attempts returned empty final results), so web claims below come from direct fetches by the orchestrator, labeled as usual. The practitioner-literature pass (AES/ASA papers on corner/eighth-space directivity) remains **[open]** for a librarian recovery pass.

### 14.1 Precedent: corner loading is the Klipschorn's founding idea

**[verified]** Wikipedia (fetched 2026-10-25): *"The speaker sits in the corner of two adjoining walls, using the walls and floor boundaries as extensions of the horn. Technically speaking, the K-Horn's folded bass 'corner horn' can be described as a bifurcated trihedral (floor and two walls to form the trihedral corner) exponential wave transmission line"* — patented by Paul W. Klipsch in 1946, in continuous production since; *"utilizing the room walls and floor boundaries as extensions of the bass horn helps extend the speaker's frequency response down into the 35 Hz range, considerably lower than would be possible otherwise."* The room's own surfaces are the last horn flare — that is exactly the physics the owner proposes.

**[verified]** Same page: Klipsch, "Modulation Distortion in Loudspeakers", AES Convention 34, April 1968 (elib 1448); Holland/Fahy/Newell, "The Sound of Midrange Horns for Studio Monitors", JAES 44(1/2):23–36, 1996 (honkiness causes still researched — cited there).

Three differences from the Klipschorn, and they are the concept: **(a)** up-corner (ceiling instead of floor), **(b)** the corner loading serves the FULL band, not just bass (the K-Horn's mid/tweeter horns are conventional), **(c)** dispersion is shaped against the four-source SUM over the room's listeners, not against efficiency.

**[inferred]** Image-source physics: each rigid boundary plane adds a mirrored image contribution; the classic loading ladder is full → half → quarter → eighth space (−0/−3/−6/−9 dB relative conventions). Standard acoustics (image-source method), not re-verified from a primary this pass.

### 14.2 What three boundaries buy a design

**[inferred] engineering reasoning, each item testable in our solver:**

1. **The room does the last flare.** The hardware mouth can be smaller for the same effective acoustic termination at the loading frequencies. §13.5 showed the K-law mouth is the binding constraint (75×35° at 300 Hz → mouths 1128.9 × 2419.0 mm, 13.7× the envelope area). Corner mounting moves part of that expansion out of manufactured geometry and into the room's surfaces — it relaxes the constraint exactly where it binds (low frequencies).
2. **The ceiling plane is free directivity control in the wasted direction.** Danley's stated design goal is the same instinct: *"Put the sound energy in the audience's seats, not sprayed over the side walls, ceiling and floors. Maintain directivity control at the lowest possible frequency"* **[verified]** tech page, fetched 2026-10-25. An up-corner mount removes one entire half-plane of radiation by construction.
3. **Four sources comb-filter in the low-mid band.** Corners are metres apart; the summed field at a listener is frequency-dependent. An even-coverage objective must therefore co-consider per-unit band/level/timing (or accept a mono-summed, symmetric-pair deployment) — **[open]** design study.
4. **Walls are rigid only up to their material absorption.** The solver assumes rigid lossless boundaries (`TOOLCHAIN.md:182-183`); a corner brief should carry a wall-treatment assumption. **[open]**.

### 14.3 External software landscape (fetched 2026-10-25 unless noted)

- **AFMG EASE 5 —[verified] product page:** the reference discipline for "even coverage in a room": GLL loudspeaker data format (~3,000 datasets / ~300 brands, "simulation accuracy of up to 1 dB"), Acousteer real-time engine, Direct SPL coverage maps, loudspeaker coverage overlap, loudspeaker density (3/6/10 dB), STI per IEC 60268-16:2020, D/R ratio, critical distance, audience areas + listener seats, DWG import. This is what "coverage engineering" looks like in industry practice — our room-aware objective can mirror its vocabulary.
- **Danley Synergy Horn / Cohearix —[verified] tech page:** full-range point-source horn; multiple drivers *"behave as a single full range loudspeaker"*; Cohearix Lens (patent-pending, announced 2025-06-11) produces segmented radiation arcs that *"sum into a true single source"* with adjustable focal length. The nearest modern product philosophy to coverage-tapered dispersion.
- **ATH (Batík) as the practice tool for asymmetry — already verified in this document (§11/§13):** superformula azimuthal coverage-law modulation (ATH CORE formula), Tritonia morphing, superellipse outlines; exports meshes toward ABEC. No new research needed to reuse those findings.
- **Hornresp —[open]**: site unreachable this pass (direct fetch fails; the Wayback capture list covers 2013–2026 but snapshot content did not render). The practitioner-known quarter/eighth-space radiation-angle modeling is **[reported, unverified]**.
- **d&b ArrayCalc —[reported, unverified]**: product page unreachable twice today; industry-standard coverage-mapping ecosystem by reputation only.
- **Neural surrogates (§10) — not usable for design ranking** at our tolerances; corner work stays on the real-solver path.

### 14.4 In-repo reality check — what supports the concept today

All claims **[verified in-repo]** from the recon pass (paths cited):

Support that already exists:

- **Quarter-symmetry already models a two-boundary corner.** `SolveConfig(native_symmetry_plane="yz+xz")` + `quadrants: "1"` mirrors the geometry across two orthogonal rigid planes — the physical equivalent of a horn mouth flush with two walls (or wall + ceiling). The owner's trihedral corner has THREE boundaries; **two of the three are representable today** (`mesh/sizing.py:16-17` single source; `01_CONTRACTS.md:353-368`).
- `brief.mounting` end-to-end plumbing (block validator, normalized keys, cache/provenance): `config.py:136-149,276-340`, `design/families.py:476-511`, `mesh/build.py:244-274` — a new mounting type rides the existing pattern.
- Independent H/V asymmetric geometry exists: FREEFORM `profileH`/`profileV` (`design/families.py:141-142,363-371`) and per-azimuth GRID rows (`design/generators/grid.py:107-124,465-484`).
- `targets/venue.py:18-107` already holds `coverage_from_room` plus the Keele K-law mouth rule (verified §13.5) — but it is unreachable from any brief today.

Gaps (**[verified, negative]**):

1. **No third mirror plane anywhere** — BEAT symmetry modes are `off`/`x`/`xy` only (`forks/hornlab-beat-bem/.../config.py:~104-116`), `ground_plane` (y=0) exists but is refused in combination with native symmetry (`capabilities.py:204-236`, single image-transform set); the bempp path and mesher likewise top out at two planes.
2. **No wall/ceiling/corner mounting type** — `brief.mounting` supports `enclosure` only; the CAD/STEP route refuses mounting entirely (`mesh/step_build.py:488-499`).
3. **No room-aware coverage objective** — Target is a single included H/V angle pair (`targets/spec.py:7-16`); no room dims, listener positions, per-azimuth/per-elevation profiles, or SPL-on-map term.
4. **No asymmetric-dispersion target** — geometry can BE asymmetric (GRID/FREEFORM); nothing can SCORE asymmetry.
5. **No room/listener coverage visualization** — balloon view exists (`gui/data.py:699-780`); no floor-plane multi-source map.
6. **Scale** — full-domain CUDA ceiling ~5,500 dofs binds a fully asymmetric mesh at high f (12,000 for fused-CUDA quarter). **[inferred]** An eighth-domain (three mirror planes) would REDUCE dofs to roughly half of the quarter model for the same horn — the missing solver feature is also the cheaper-simulation one.

Note: senior-pass grid row G11 ("up/down asymmetric — listening-axis tilt, floor/ceiling control", `research/senior_pass_2026-10-24/02_TYPOLOGIES_AND_MULTICELL.md:58`) was already flagged "high for real rooms" — this concept is its systematic version.

### 14.5 Implementation menu, ranked (owner-gated per house rules)

- **Route 1 — evidence first, zero new code: measure the corner-loading delta in our own solver.** A/B screen of the same seed horn: quarter-symmetry flush with two planes vs freestanding. Delivers the ΔDI/ΔJ/dofs numbers that justify (or kill) everything else, under existing checkpoint rules and GPU etiquette. Days, not weeks.
- **Route 2 — the trihedral fork feature (`eighth-space` symmetry).** Add a third mirror plane through the FORKS.md ladder (BEAT symmetry mode + mesher snap axis + our sizing/topology/contract plumbing). Bounded and mechanical; unlocks true trihedral solves and makes them cheap (14.4.6). Naming: nothing ships under a published name without a verifiable published reference (R9) — §14.1 anchors the concept; a coined typology name waits for the practitioner-literature pass.
- **Route 3 — coverage-aware brief, additive contract keys** (the §13.5 owner-amendment pattern): optional `room` block (dimensions, listener plane) + per-elevation coverage targets + a coverage-map objective term (four-source sum over listener positions). `venue.py` already holds half the machinery.
- **Route 4 — asymmetric dispersion targets** so the objective can score what GRID/FREEFORM can already build (per-elevation/per-azimuth target profile).
- **Route 5 — report/GUI: four-source floor-plane coverage map** per frequency band — a rendering feature over stored response data, in the §12 balloon-grammar lineage.
- **Route 0 — desk study: done (this section).** The next concrete step is the owner Q&A below, then Route 1.

**[open], for a later librarian recovery pass:** AES/ASA literature on corner/eighth-space directivity and corner-array practice; Hornresp help-file verification; quadraphonic-era four-corner practice; wall-absorption sensitivity.

### 14.6 Sources for this section

- Wikipedia, Klipschorn (fetched 2026-10-25): https://en.wikipedia.org/wiki/Klipschorn
- P. W. Klipsch, "Modulation Distortion in Loudspeakers", AES Convention 34 (1968), elib 1448: http://www.aes.org/e-lib/browse.cfm?elib=1448
- Holland, Fahy, Newell, "The Sound of Midrange Horns for Studio Monitors", JAES 44(1/2):23–36, 1996: http://www.aes.org/e-lib/browse.cfm?elib=7915
- Danley Sound Labs, technology page (fetched 2026-10-25): https://www.danleysoundlabs.com/about/danley-technology/
- AFMG EASE 5 product page (fetched 2026-10-25): https://www.afmg.eu/en/ease
- audioroundtable.com, Keele "Optimum Horn Mouth Size" PDF (binary fetched this pass; analysis deferred — the K-law's use in this repo is verified from code in §13.5): https://audioroundtable.com/misc/Optimum_Horn_Mouth_Size.pdf
- hornresp.net — unreachable this pass (direct + Wayback capture index 175 captures 2013–2026):
- d&b ArrayCalc — unreachable this pass: https://www.dbaudio.com/
- In-repo anchors already verified in §11/§13: Ath user guide, OS-SE/R-OSSE papers, US4308932A, Salmon JASA 1946.

---

## 15. Boundary Lab interop, refreshed against the newest upstream (added 2026-10-25, owner-directed)

Owner question for this pass: *look at the newest version of Boundary Lab and how we could push our best designs to BL for room modeling, and vice versa.* No code changed — research + plan refresh only.

### 15.1 Version check

**[verified]** The latest published Boundary Lab release is **v0.5.0** (2026-10-20, tag commit `6c9185b`, BEAT 0.6.0 wheel pinned, SHA `10db2ee2…7dd3`; main at 409 commits at fetch time). The repo's `docs/research/boundary_lab_0.5/bl_inventory.md` was written against exactly 0.5.0 — **it remains the current-version inventory**; no new solver/mesh/API surface to relearn, and all of its docs-stale caveats stay valid.

**[verified]** 0.5.0 adds vs our 0.4.x-era knowledge (release notes): geometry-provider plugins + transactional multi-mesh assemblies + a bundled parametric vented-enclosure generator; near-coincident-vertex detect/repair; interface geometry measurements; **axial prescribed sources** (`rigid_translation` motion — piston-driver models); thermoviscous wall loss (supported FEM regions); generic driver text import/export; radiated SPL contributions from coupled interfaces; `.blabsp` speaker-package export (with `--viewport-model`); Deploy moved to a separate app; BEAT 0.6.0's projected FEM-BEM interface correction **changes coupled-model numerics** (exterior-only solves unaffected **[inferred]**); known CUDA low-current 50 Hz caveat (0.134 % vs CPU) — use CPU where low-current accuracy matters (sub-relevance, not horn DI).

### 15.2 Boundary Lab Deploy — the room-modeling bridge

**[verified]** README + release notes: `boundary_lab_deploy` is a **standalone array prediction tool that consumes `.blabsp` speaker packages** and depends directly on BEAT Engine; BL retains speaker-package export. The pipeline for the owner's "push designs to room modeling" is therefore:

```
hornlab-search best design
  → export-blab (BL-1, .blab.json schema 10)
  → blab project solve / BL GUI solve (or export-speaker directly)
  → .blabsp
  → Boundary Lab Deploy (array/room prediction)
```

**[open]** Deploy's actual feature set (rooms, surfaces, delay/level per element) is unverified — its repo was not fetched this pass; it is the first item for the librarian recovery pass.

### 15.3 Push-out (ours → BL), status and mechanics

**[verified in-repo]** `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md` (PROPOSED; priority order BL-1 export → BL-2 cross-check → BL-3 plugin PARKED per the 2026-10-22 senior report) is designed against **exactly this 0.5.0 surface** (project schema 10, request overlay v1, result manifest v2, `provider_api` 1):

- **BL-1 `export-blab`** (~300 LOC, ~15 offline tests, no GPU, CP-11b): minimal exterior fixture pattern + request.json with exact frequencies; symmetry map `yz+xz→xy` from the **single source** `sizing.SYMMETRY_PLANE` (BL has no Y-only symmetry; `"xz"` refuses); boundary roles from `$PhysicalNames`; `metadata.hornlab` provenance survives loading; refusal cases (bbox, scale, unknown groups, `quadrants "12"`).
- **BL-2 headless cross-check** (~300 LOC, 1 GPU, CP-11c): `blab project solve … --backend beat_cuda --events ndjson` as the third independent solver against the frozen CP-7b < 0.2 dB rule; **GPU hygiene mandatory** — BL does not shut down its Julia worker, so the wrapper must kill and verify per `AGENTS.md` rules.
- **BL-3 geometry-provider plugin (PARKED)**: the native two-way GUI route (provider manifest + "Load best from hornlab run" + subprocess worker); not the optimization driver, per the plan's own risk analysis.
- Headless `.blabsp`: `blab project export-speaker --fidelity {pattern,fixed,coupled}` already writes the Deploy-consumable package from the CLI **[verified]** (`bl_inventory.md` §1.2) — no GUI needed for the room-modeling pipeline.
- **Never-in-venv rule unchanged**: BL hard-pins `beat_engine == 0.6.0` at import; BL gets its own environment and is subprocess-called (`HORNLAB_BLAB_EXE`).

### 15.4 Pull-in (BL → ours), two concrete routes

- **BL project meshes → our scoring**: BL projects carry Gmsh 2.2 ASCII `.msh` (expanded + reduced variants); our mesher's **LOOKUP** typology (`research/typologies/MESHER_TYPOLOGIES.md`) exists for foreign geometry — **[inferred]** a small adapter task makes any BL- or Ath-authored mesh a hornlab-search candidate (score/optimize it against our objectives). Needs a bounded design study before a plan.
- **Ath `.cfg` authoring**: BL bundles Ath and only interprets `Mesh.Quadrants`; the cfg vocabulary `Coverage.Angle` expressions (`36 + 17*cos(p)^2`), `GCurve.SF` superformula, and `Morph.TargetWidth/TargetHeight` are verified in BL's examples (`bl_inventory.md` §7) — i.e., **asymmetric H/V and azimuth-law coverage are natively authorable on the BL side today**. **[inferred]** An Ath-cfg source row in our search layer would let a BL-authored brief be scored and optimized here, closing the loop both ways.
- Conversions that must be tested closed-form before either route (plan-mandated): unit acceleration vs `normal_velocity` 1 m/s; `exp(+i ωt)` vs `exp(−i ωt)` conjugation.

### 15.5 Corner-concept tie-in

**[verified]** BL/Ath can author asymmetric coverage today (morph/superformula/coverage-expression keys); our sf-rows do superformula azimuth laws (§11). A corner brief travels both directions through the routes above, and **[verified]** BL itself solves exterior/free-space BEM only — the room boundaries live in Deploy, not in the BL solver — so the corner concept's room modeling rides the `.blabsp`→Deploy pipeline, while the corner *horn geometry* rides the BEM pipelines (ours and BL's **[inferred]**).

### 15.7 Boundary Lab Deploy, verified against its repo (recorded 2026-10-25, librarian lane lib-5)

All claims **[verified]** from the repo/docs/API fetches below unless labeled.

- **What it is**: standalone desktop app (Electron/React + Python/Julia worker), GPL-3.0, for *"loudspeaker-array placement, coverage, and loading analysis"*; BL is the speaker-package *authoring* app, not a runtime dependency. **Current version `0.1.0rc4`** (tag 2026-09-28; BEAT pins: rc4 tag → 0.3.0, `main` → **0.5.1** since 2026-10-15). **No published GitHub Release** — four rc tags only; post-rc4 `main` (Metal/macOS readiness, scene editing, captures, 2026-10-17) is unreleased. Prototype scale: 67 commits, 2 stars.
- **Three calculation levels** (User Guide): **Pattern L1** = packaged directional responses + distance/phase propagation + coherent array summation + rigid-ground reflections (TypeScript side; no Julia needed); **Boundary L2** = exterior BEM with fixed distributed sources + ground/scene scattering; **Coupled L3** = exterior coupled to reduced interiors (rank-32-per-sector parity Petrov–Galerkin ROM) incl. **mutual loading and transducer feedback** between cabinets.
- **"Room modeling" is PARTIAL — rigid-boundary only.** There is no feature named room modeling; the physical scene is an **always-on, infinite, perfectly rigid ground plane** (cannot be disabled or assigned a material) plus imported **sound-hard (rigid) objects** ("do not model material absorption or transmission"). No acoustic surface materials anywhere (OBJ/.mtl are viewport-display only). **[inferred] consequence for the corner concept: Deploy does not model an interior room — walls/ceiling cannot be represented (no ceiling plane, no absorbing surfaces); its frame is outdoor/arena-style scenes over rigid ground.** The corner concept's even-coverage study therefore needs OUR room-aware objective (§14.5 Route 3), not Deploy, unless the owner accepts a rigid-floor-only approximation.
- **Coverage prediction exists**: audience planes (position/orientation/dimensions/resolution; 0.5–10 points/m, 250,000-point ceiling per plane), **single-frequency** SPL / real / imaginary pressure maps, average-and-spread statistics (average = **arithmetic mean of dB values**; spread = P90−P10 — not energy/broadband measures), point-microphone probes with frequency sweeps.
- **Per-element DSP**: level/delay/polarity/mute per instance (`levels and delays add, polarities multiply`); drive `g(f) = σ·10^(L/20)·exp(+i2πfτ)`; **EQ filter banks implemented on `main`** (schema 10: peq/shelf/allpass LP/HP, max 64 per bank) — the user-guide text calling EQ "placeholders" is contradicted by `docs/filter-banks.md` + code; treat the guide as stale.
- **`.blabsp` format** (schema `"boundary-lab-speaker-package"` v1, versioned ZIP64; produced by BL's `blab project export-speaker --fidelity {pattern|fixed|coupled}`): L1 `data/patterns.npz` (complex pressure on a Fibonacci sampling sphere), L2 adds `data/fixed-sources.npz` + `geometry/exterior.msh`, L3 adds `data/coupled-rom.npz`; coordinates rotated `(x, y, z) → (x, z, −y)` (BL +Z-forward → package +Y-forward); phasor `exp(+iωt)` preserved; provenance + SHA-256 checksums; Deploy validates strictly (schema v1 only; mixed packages must share medium; solves at the frequency intersection).
- **Worker hygiene good news**: Deploy's worker calls BEAT directly and *"owns and terminates its own workers"* (extraction doc) — compliant with our GPU rules when/if we ever drive it.
- **Disclaimer honored in any report**: Deploy is *"intended for array design studies, not rigging approval…"*; no independent accuracy validation exists; single-machine benchmark only.
- **Pipeline update** (supersedes §15.2's sketch): the room-prediction leg requires **a BL solve first** (packages are authored in BL from a solved physical system; L3 additionally requires a coupled FEM-BEM system and temporarily expands symmetry to full domain before export). Full chain: `export-blab → blab solve → export-speaker (CLI, no GUI) → .blabsp → Deploy`. **[open]** Authoring `.blabsp` directly from our own solves would skip BL, but the manifest/ROM contract makes it a bigger, riskier route — not proposed now.

Sources: https://github.com/JWSound/boundary_lab_deploy (README; `desktop/docs/user-guide.md` last commit 2026-10-17; `desktop/docs/system-model.md` 2026-09-22; `docs/extraction.md` 2026-09-21; `docs/filter-banks.md` 2026-09-22; `docs/solver-backends.md` 2026-10-09; `docs/plane-sampling.md` 2026-09-23; `docs/releases/0.1.0rc1-4.md`; tags/releases API 2026-10-25) · BL side: `docs/Inputs and Outputs.md`, `docs/advanced/cli-workflow.md` 2026-10-07, `src/blab/speaker_package.py`, `src/blab/ui/speaker_package_dialog.py`.

---

## 16. Typology expansion: white papers, formulas, drivers (added 2026-10-25, owner-directed)

### 16.1 The typology map, dated and sourced

**[verified]** unless noted (fetches of 2026-10-25: Wikipedia horn-loudspeaker + compression-driver + Keele pages; SynAudCon Hughes article).

| Typology | Origin | Source | Core idea | In our repo |
|---|---|---|---|---|
| Conical / megaphone | oldest | Peavey QTW paper claim: conic sections radiate spherical wavefronts — no phase/amplitude distortion **[reported]** | straight walls; basis of QTW and OS bodies | conical row verified |
| Exponential | 1924 | Hanna & Slepian, AIEE (JAES 25:573–585 reprint 1977) | `S = S0·e^(mx)`; loading advantage; beaming drawback | verified (salmon/exponential rows) |
| Multicell | patent **1936** (E. C. Wente, Western Electric); in use since 1933; Altec Duplex 601/604 1943–1998 | | array of narrow cells; lobing up to ~10 dB between lobes **[reported, Eargle]** | WP14 banked (dossier holds deferred first attempt + resume recipe) |
| Radial / sectoral / diffraction | 1940s–; JBL "Smith" horn (2397, 1978; 2405H 90°×35° @ 20 kHz) | | exponential surfaces on two walls, straight walls set pattern | concept rows only (§13) |
| Tractrix | patented **1927**, P. G. A. H. Voigt | | tangent-length construction; cutoff sets mouth | lecleach/tractrix entries |
| Constant Directivity | **May 1975**, AES 51st Convention paper, D. B. Keele (Electro-Voice); first CD patent assigned to EV (US4071112A, 1975-09-30 per the Keele Wikipedia patent list) | | exponential throat (low-f loading) + conical body (constant beamwidth) + mouth flange | K-law verified; direct AES-paper pass **[open]** |
| Mantaray | 1977-ish | C. A. Henricksen & M. S. Ureda (Altec) | horizontal-diffraction slot: **H/V patterns decoupled**; apparent apex varies with frequency → ellipsoidal wavefront, one-plane arrayability | H/V decoupling = our `hv` brief; slot grep-verified absent (§13) |
| Bi-Radial | **1980** | Keele (JBL), US4308932A | two radial formulas, smooth hybrid | verified §13.1 |
| Twin Bessel | ~1980s | Ramsa (Panasonic) | dual-series Bessel flare | absent **[inferred effort ~50 LOC]** |
| Quadratic-Throat Waveguide | **1999** patent | C. Hughes (Peavey); white paper verified §13 | conic body + circular-arc throat; 3–4 dB lower 2nd / ~9 dB lower 3rd harmonics vs CD horns; no slot → no apex problem | QTW ~100 LOC (§13 shortlist) |
| Multiple-entry / CoEntrant / Unity / Synergy | 1996 (R. Heinz, Renkus-Heinz); Unity 2001–02 (Danley, Yorkville); Synergy 2002+ (Danley) | | several drivers enter one horn at band-dependent distances; single acoustic source | driver-placement design space, not a mesher typology **[inferred]** |
| OSWG | 1990s– | E. Geddes — the OSWG section: directivity control above 1 kHz; **higher-order-mode mitigation claim [reported, unverified — gedlee.com unreachable both attempts this pass]** | oblate spheroid body | OSSE lineage verified (§11) |
| CBT | 2000s | D. B. Keele — "has published on Constant Beamwidth Transducers" **[verified general]**; paper titles/years unverified this pass **[open]** | shaded array with near-constant beamwidth | absent; an array-level alternative to horns (multi-driver) |
| HCD | Dec 2019 (Voice Coil) / AES 148, Jun 2020 | D. Cinanni | transform any expansion into CD on one plane, preserving acoustic load | absent; needs the Cinanni paper **[open]** |
| JMLC / Le Cléac'h | 2000s–2010s | Fourcade 2015 (verified, lib-1 in-repo) | | live per R9-J |
| OS-SE / R-OSSE / superformula | 2020/2022/2026 | Batík PDFs (verified §11) | | live rows |

### 16.2 The formula that rules feasibility — re-verified at source

**[verified]** The Hughes/SynAudCon article (fetched 2026-10-25) gives the Keele 1975 K-law exactly as the repo constant: mouth dimension `d = K/(θ·f0)` with **K = 1×10⁶ in·deg·Hz = 2.54×10⁴ m·deg·Hz** — confirming `KEELE_K = 25400` (`constants.py:10`, §13.5) against a second source. Three designer-facing rules come with it:

1. **The mouth-dimension ratio sets the per-plane loss-of-control frequencies.** A 90°×45° horn with a square 12-inch mouth loses vertical control at 2× the horizontal f0; to equalize both planes, the narrow-coverage axis' mouth must be wider by the coverage ratio (12×24 in example). **→ For an asymmetric corner horn: the envelope's H/V mouth ratio must follow the coverage-angle ratio, or the K-law predicts misaligned per-axis f0s — this is the one-line design rule §13.5's brief-derived-seed fix (A) can encode.**
2. **"Pattern flip":** a wide-and-short mouth (12×6 in at 90°×45°) throws the VERTICAL beam wider than the horizontal below ~2 kHz — the spec-sheet coverage is not maintained down low. Every corner brief should print the per-axis f0 next to its per-axis coverage target (fix A/B does exactly this).
3. **"Pick any two"** of {narrow coverage, low f0, small size}. The corner concept's value proposition is precisely that the third boundary buys the third constraint for free.

### 16.3 Drivers — the other half of the typology

**[verified]** History chain (compression-driver page, fetched 2026-10-25): **Hanna & Slepian 1924** (compression concept; AIEE; JAES 25:573–585 reprint 1977) → **Wente & Thuras 1928** (first phase plug; "A High-Efficiency Receiver for a Horn-Type Loudspeaker of Large Power Capacity", Bell System Technical Journal; JAES 26:139–144 reprint 1978) → **Western Electric 555** (first commercial compression driver, 1933) → **Bob Smith 1953** ("An Investigation of the Air Chamber of Horn Type Loudspeakers", JASA 25(2):305–312, doi:10.1121/1.1907038 — the air-chamber resonance-suppression methodology behind most modern phase plugs; popularized by Fancher Murray, AES 61st Convention preprint 1384, 1978) → **Dodd & Oclee-Brown 2007** (AES 123rd Convention preprint 7258 — FEA-confirmed improved plug guidelines).

**[inferred]** For the search layer: the driver is already a brief input (§13.5's 17.4 mm/8° example), so a natural bounded study is the **typology × driver coupling** — the same geometry across 1"/1.4"/2" exits to see how the `load` term ranks throats; no new objective needed.

**[verified]** DSP correction exists as prior art for horn distortion: "Gunness Focusing" (Dave Gunness, Eastern Acoustic Works) reduces diaphragm/phase-plug time-smear while retaining dispersion control.

### 16.4 Absent-classes menu update (grep state unchanged)

§13's shortlist stands unchanged. Additions from this pass: **Twin Bessel** flare (~50 LOC **[inferred]**, needs the Bessel-law definition pinned at source first); **HCD** transform (idea-level; gate = obtain the Cinanni paper); **CBT** is an array-level feature (out of mesher scope today; relevant only to a future multi-driver corner deployment study).

### 16.5 Open items for the librarian recovery pass

Keele 1975/1977 AES paper exact titles + e-library ids (his Wikipedia page lists only two early papers and says "more than forty technical papers"); CBT paper titles/venues; Geddes OSWG primary sources (site unreachable); AES/ASA corner/eighth-space directivity literature; the `boundary_lab_deploy` repository's feature set; diyAudio practitioner pass (Cloudflare-blocked).

### 16.6 Sources for §15/§16

- Boundary Lab README (fetched 2026-10-25): https://github.com/JWSound/boundary-lab
- Boundary Lab releases — v0.5.0 notes (fetched 2026-10-25): https://github.com/JWSound/boundary-lab/releases
- Boundary Lab Deploy (NOT fetched this pass; reported, unverified): https://github.com/JWSound/boundary_lab_deploy
- Hughes, "Understanding Horn Directivity Control", SynAudCon (fetched 2026-10-25): https://www.prosoundtraining.com/2010/05/24/understanding-horn-directivity-control/
- Wikipedia, Horn loudspeaker (fetched 2026-10-25): https://en.wikipedia.org/wiki/Horn_loudspeaker
- Wikipedia, Compression driver (fetched 2026-10-25): https://en.wikipedia.org/wiki/Compression_driver
- Wikipedia, D. B. Keele, Jr. (fetched 2026-10-25): https://en.wikipedia.org/wiki/D._B._Keele,_Jr.
- Smith 1953: doi:10.1121/1.1907038 · In-repo: `docs/research/boundary_lab_0.5/bl_inventory.md` (0.5.0-current) · `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`

### 16.7 Typology citations verified (librarian lane lib-6, recorded 2026-10-25)

Method note: aes.org blocks automated fetch (403), so AES records were verified via Wayback snapshots of the e-library pages; JASA/JAES items via Crossref/OpenAlex. Full table lives in the lane result; the load-bearing subset follows. **All [verified] unless labeled.**

**Corner-loading primary literature — the §14 concept's own anchors (upgrades the §14.2 image-source physics from [inferred] to a cited basis):**

- Klipsch, "A Low Frequency Horn of Small Dimensions", *JASA* 13(2):137–144, 1941, doi:10.1121/1.1916155.
- Klipsch, "Improved Low Frequency Horn", *JASA* 14(3):179–182, 1943, doi:10.1121/1.1916216.
- Klipsch, "Corner Speaker Placement", *JAES* 7(3):106–114, 1959 (elib=565).
- Korn, "A Corner Loudspeaker with Coaxial Acoustical Line", *JAES* 5(3):138–141, 1957 (elib=263).
- **Allison, "The Influence of Room Boundaries on Loudspeaker Power Output", *JAES* 22(5):314–320, June 1974 (elib=2760) — the standard primary citation for the half/quarter/eighth-space boundary-gain physics** (supersedes §14.2's [inferred] label).
- Artarski, Valtchev, Dimitrov, Handzhiev, "Multiple Low-Frequency Corner Folded Horn Designs", AES 134th Convention, paper 8848, May 2013 (elib=16749) — modern corner-horn work.

**Negative result, stated explicitly:** no dedicated AES/JASA paper on quarter-/eighth-space *directivity of waveguides* exists in the reachable records — searches on "corner" + "waveguide"/"quarter space" return nothing on point. The corner-concept typology space is a genuine literature gap filled only by secondary/practice sources; cite Allison 1974 for the physics and do not cite an adjacent paper for directivity claims. (Supports the R9 novelty rationale.)

**CD lineage pinned:** Keele's 1975 paper is **"What's So Sacred About Exponential Horns?"**, preprint 1038, 51st AES Convention, May 1975 (elib=2394; no DOI for pre-DOI preprints) — not titled "constant-directivity horn"; the CD-horn content claim rests on the paper plus the patent (US 4,071,112, "Horn loudspeaker", Keele/EV — issued 31 Jan 1978 per Wikipedia; **number secondary-sourced, exact dates [open]** — our §16.1 table's "1975-09-30" reading is unconfirmed). **"Optimum Horn Mouth Size" is 1973, not 1977**: preprint 933, 46th AES Convention, Sept 10–13, 1973, verified from the PDF's own cover page (the audioroundtable.com copy); e-lib elib=1693 (records it as August 1973; discrepancy noted, do not propagate either as gospel).

**CBT pinned (answers §16.1's [open]):** "The Application of Broadband Constant Beamwidth Transducer (CBT) Theory to Loudspeaker Arrays", preprint 5216, 109th AES Convention, Aug 2000 (elib=9122); "Practical Implementation of Constant Beamwidth Transducer (CBT) Loudspeaker Circular-Arc Line Arrays", preprint 5863, 115th AES Convention, 2003 (elib=12369); "Full-Sphere Sound Field of CBT Loudspeaker Line Arrays", *JAES* 51(7):611–624, July 2003; Button & Keele, "Ground-Plane CBT Loudspeaker Circular-Arc Line Arrays", paper 6594, 119th AES Convention, Oct 2005 (elib=13350 — note the boundary/ground-plane member of the CBT family, adjacent to our corner question); US 8,170,223 B2, "Constant-beamwidth loudspeaker array", Keele/Harman, filed 2003-05-27, granted 2012 (Google Patents verified).

**Geddes/OSWG pinned (upgrades §16.1's OSWG row from [reported] to cited):** "Acoustic Waveguide Theory", *JAES* 37(7/8):554–569, 1989; "Acoustic Waveguide Theory Revisited", *JAES* 41(6):452–461, 1993; Bauman, Adamson & Geddes, "Acoustic Waveguides: In Practice", *JAES* 41(6):462–470, 1993; "Computer Simulation of Horn-Loaded Compression Drivers", *JAES* 35:556–566, 1987 (elib=5190, partially verified); Geddes & Lee distortion/perception papers (5890/115th 2003 elib=12464; "Audibility of Linear Distortion…", paper 6888, 121st, Oct 2006, elib=13722 — GedLee's site cites this for HOM audibility); Geddes, Lee & Magalotti, "Subjective Testing of Compression Drivers", *JAES* 53(12):1152–1157, 2005; book *Audio Transducers* (GedLee LLC, ~2002 — year/ISBN unverified); patents US 2005/0008181 A1 (filed 2003-07-11) and US 2007/0102232 A1 (phase plug). **Terminology correction:** the patent's claim language names **elliptic-cylinder and prolate-spheroidal** contours; "oblate spheroidal waveguide" is community usage — keep manufacturers' terms generic in code/config per §13's discipline. **Do-not-cite:** no Geddes paper titled around "honkiness" exists — source the HOM case to the 1989/2002/2006 chain.

**Mantaray pinned:** Henricksen & Ureda, "Blasphemy–The Manta-Ray Horns!", preprint 1288, 58th AES Convention, Oct 1977 (elib=3066); "The Manta-Ray Horns", *JAES* 26(9):629–634, Sept 1978 (elib=3249); patent US 4,187,926 (Altec, 1980 — number/date secondary-sourced; JASA patent-review doi:10.1121/1.384649); Ureda, "Directivity Phase Response of Horns", preprint 3593, 94th AES, Feb 1993 (elib=6571); "Analysis of Loudspeaker Line Arrays", *JAES* 52(5):467–495, 2004. **Do-not-cite:** Ureda's 1981 preprint 1793 ("horn antenna transfer functions") could not be verified in any reachable record — hold at [open].

**Still open after this pass:** diyAudio practitioner threads (Cloudflare-blocked); CD patent dates at Google Patents; *Audio Transducers* ISBN/year; Ureda 1981 preprint.

### 16.8 Consolidated implementation order (research + interop, owner-gated)

1. **Owner Q&A** (§14.5): up-corner confirmation, room dims/listeners, full-band vs multi-way, "Centennial band" reading.
2. **Route 1 — corner-loading delta A/B** in our own solver (quarter-symmetry vs freestanding, zero new code) — now anchored to Allison 1974 for the physics expectation.
3. **BL-1 export + BL-2 cross-check** (existing PROPOSED plan, designed against the current BL 0.5.0): get our best designs into BL and third-solver-verified; then `export-speaker --fidelity pattern` → **`.blabsp` handoff** (Deploy verified ready to consume it per §15.7, with the rigid-ground caveat).
4. **Route 2 — trihedral (`eighth-space`) fork feature**, with Allison 1974 as the published physics reference and §14.1/§16.7 as the corner-anchor set (R9 satisfied for the feature; any coined typology NAME still waits on a published reference).
5. **Routes 3–5 (coverage-aware brief, asym targets, coverage-map view)** and the §16.4 absent-classes menu, per owner priorities; Pull-in adapters (§15.4) after BL-1/BL-2 numbers exist.
6. Remaining [open] citations (§16.7) are doc-level debts, not blockers.

### 16.9 The S1a driver-pass finalization (added 2026-10-25, owner-directed; oracle decision record)

The owner directed an oracle decision pass for the typology-completion repair (briefs, per-config
parameters, driver classes) — the complete final output is preserved verbatim in
`docs/research/typologies/S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md` with a provenance header;
this section is the pointer. Summary of the applied decisions (all measured on the tree via march
+ envelope + real gmsh dry-runs): **the driver class lives in the BRIEF** (WP2 pins the throat;
shipped family `hifi_90x60_{1in,14in,2in}` / `organic_rollback_{1in,14in,2in}` /
`lecleach_rollback_{1in,14in,2in}`, every brief f0-carrying + objective v3 with the K-law break
of its binding axis — the salmon family additionally uses the measured 1.8× rollback-extent
correction, the lecleach full ring a measured dof-honest f0 1200 floor); **biradial's un-closeable
seed repaired two ways** (seed L 210→195 so one seed closes under every driver class; a
closure-aware derivation `rm = max(K-law d/2, r0 + tan(a)·L)` with the one owner-directed
`widened_to_closure` exception to the clamp-only contract, flagged per note); **the two failing
salmon demos reseeded** (stop 150; x_amp −0.15 — the shipped seed crossed the 180° cap-area
asymptote) and **lecleach eps 0.25→0.20** (the full-ring self-approach window at r0 ≥ 17.2) with
lecleach moving to its own family brief; **the C4 catalog block landed** (five entries incl.
`symmetry: full` for the seam-free ring; closes R9-audit P3). The scored-guide and
which-brief-for-which-typology tables live in `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md`.
**Owner note on record (2026-10-25):** the owner suspects some min/max parameters may
over-constrain the designs — explicitly deferred to a later round, not acted on in this pass.
Validation plan applied: the driver-brief test file (offline), the offline suite, then the GPU
dry-run matrix + re-smokes recorded in the smoke-matrix evidence addendum.

---

hornlab-waveguide-mesher: https://github.com/m3gnus/hornlab-waveguide-mesher
hornlab-waveguide-mesher config schema: https://raw.githubusercontent.com/m3gnus/hornlab-waveguide-mesher/main/docs/config-schema.md
hornlab-waveguide-mesher tags.py: https://raw.githubusercontent.com/m3gnus/hornlab-waveguide-mesher/main/hornlab_mesher/tags.py
hornlab-beat-bem: https://github.com/m3gnus/hornlab-beat-bem
hornlab-bempp-bem: https://github.com/m3gnus/hornlab-bempp-bem
hornlab-plots: https://github.com/m3gnus/hornlab-plots
waveguide-generator: https://github.com/m3gnus/waveguide-generator
WG external evaluation API: https://github.com/m3gnus/waveguide-generator/blob/main/docs/reference/EXTERNAL-EVALUATION.md
Boundary Lab: https://github.com/JWSound/boundary-lab
BEAT Engine: https://github.com/JWSound/BEAT_Engine
Understanding Horn Directivity Control (Hughes): https://www.prosoundtraining.com/2010/05/24/understanding-horn-directivity-control/
Keele, Optimum Horn Mouth Size: https://audioroundtable.com/misc/Optimum_Horn_Mouth_Size.pdf
B-FNO, Engineering with Computers 41(4):2393-2410: https://link.springer.com/article/10.1007/s00366-024-02103-x
B-FNO full text mirror: https://d-nb.info/136288975X/34
DB-FNO, Journal of Sound and Vibration: https://www.sciencedirect.com/science/article/abs/pii/S0022460X26003792
DB-FNO preprint on SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5572813
MAD-BNO, operator learning on domain boundary from fundamental-solution artificial data: https://arxiv.org/abs/2601.11222
MscaleFNO paper: https://arxiv.org/abs/2412.20183
MscaleFNO code, MIT: https://github.com/yyc-rgb/MscaleFNO
Quadrature-aware complex-linear neural operator (CLBO): https://arxiv.org/abs/2607.04407
neuraloperator library, MIT: https://github.com/neuraloperator/neuraloperator
Neural operator surrogate for free-form electromagnetic inverse design: https://arxiv.org/abs/2302.01934
Data driven surrogate modeling of horn antennas: https://onlinelibrary.wiley.com/doi/abs/10.1002/mop.33702
Neural-operator surrogates for outdoor acoustics, JASA: https://pubs.aip.org/asa/jasa/article/160/3/2653/3405543/Neural-operator-surrogates-for-outdoor-acoustics
RTX 4070 Laptop GPU specifications: https://www.notebookcheck.net/NVIDIA-GeForce-RTX-4070-Laptop-GPU-Benchmarks-and-Specs.675690.0.html

Section 11 sources:
Ath (Batík) — at-horns.eu: https://at-horns.eu
OS-SE Waveguide, M. Batík, Oct 2020: https://at-horns.eu/release/OS-SE%20Waveguide.pdf
R-OSSE Acoustic Waveguide rev7, Dec 2022: https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf
Ath 4.8.2 User Guide: https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf
ATH CORE design (2026, CC-BY-4.0): https://at-horns.eu/core.html
diyAudio "Acoustic Horn Design – The Easy Way (Ath4)": https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/
Gielis 2003, American Journal of Botany 90(3):333-338: doi:10.3732/ajb.90.3.333
Superformula (summary and plots): https://en.wikipedia.org/wiki/Superformula
GSA, Rashedi et al. 2009, Information Sciences 179(13):2232-2248: doi:10.1016/j.ins.2009.03.004
GSA survey, Swarm and Evolutionary Computation 41:141-158: doi:10.1016/j.swevo.2018.02.018
GSA parameter sensitivity / premature convergence: https://arxiv.org/abs/2205.06770
GSA diversity (Sadhana 2017): doi:10.1007/s12046-017-0674-0
GSA diversity / chaos (Information Sciences 2023): doi:10.1016/j.ins.2023.03.138
GSA local-minimum trapping (GSABC): https://arxiv.org/abs/1706.03608
GSA large-scale + cooperative co-evolution: https://arxiv.org/abs/2101.06630
CMA-ES, Hansen & Ostermeier 2001, Evolutionary Computation 9(2):159-195: doi:10.1162/106365601750190398
CMA-ES tutorial (incl. §B.5 penalties): https://arxiv.org/abs/1604.00772
CMA-ES evaluations per dimension, Bajer et al. 2019, Evolutionary Computation 27(4):665-697: doi:10.1162/evco_a_00244
BIPOP-CMA-ES on BBOB (GECCO 2009): doi:10.1145/1570256.1570333
pycma: https://github.com/CMA-ES/pycma
CMA-ES portal: https://cma-es.github.io/

Section 13 sources:
US4308932A — Keele/JBL Bi-Radial horn, filed 1980: https://patents.google.com/patent/US4308932A/en
Quadratic-Throat Waveguide white paper (Hughes/Peavey; J. Murray): https://excelsior-audio.com/Publications/QTWaveguide/QTWaveguide_WhitePaper.pdf (archived: https://web.archive.org/web/20160303231128/http://peavey.com/media/pdf/aa/qwp1.pdf)
ATH CORE (Batik, CC-BY-4.0): https://at-horns.eu/core.html
Tritonia (Batik): https://at-horns.eu/tritonia.html
TwinRay (Batik): https://at-horns.eu/twinray.html
Augspurger, Acoustical Lens (Audio magazine): https://www.tnt-audio.com/clinica/acoustic_lens.pdf
Salmon 1946 theory paper: doi:10.1121/1.1916316
Salmon 1946 family paper: doi:10.1121/1.1916317
Freehafer 1940 (exact infinite hyperbolic-horn impedance): doi:10.1121/1.1916061
Olson, Acoustical Engineering, 1947 2nd edition, s 6.19: verified via library copy (no DOI; per the salmon dossier)
Flygare & Pantaleev, quad-ridge flared horn, IEEE TAP 2020: doi:10.1109/TAP.2019.2940529
Joseph Crowe catalogue/products + sitemaps: https://josephcrowe.com (full per-page list in the biradial dossier)
JBL Pro directivity technology: https://jblpro.com/en/innovation-directivity
Full per-claim source tables: the three §13 dossiers in docs/research/typologies/ carry every URL/status label; this section records the load-bearing subset only.

## 17. Simulation fidelity: does an ideal-source BEM behave like a built horn? (added 2026-10-27, owner-directed; P12)

Full report: `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` (source table there; this section is the summary for the senior pass).

- **[published + measured]** Far-field pattern (polars, DI, beamwidth) above the horn's cutoff is predicted well by BEM with a velocity/piston source
  (Kolbrek BEM pages, Panzer & Macey BERIM, diyAudio Ath/ABEC print-and-measure threads; our own CP-7: 0.039 dB two-solver, epw6 vs 18 <= 0.29 deg bw /
  0.028 dB DI). **Level, efficiency, low-frequency loading, cutoff peaks and distortion are NOT predicted**, and on-axis normalisation hides the error.
  Also missing: the real throat/driver exit wavefront (our f11 cross-mode ~5.7 kHz on 1.4 in), baffle diffraction, wall vibration, print-wall effects;
  epw 6 is the ~10 % modal-error class.
- **Other tools:** Hornresp (1-D + measured T/S), Akabak (LEM driver + BEM; output power ~ Re Z_throat), ABEC/Ath (ideal source for pattern, driver
  coupling for level), Boundary Lab (monolithic FEM-BEM-LEM with dry Mmd; post-hoc Mms coupling double-counts radiation mass). An ideal source for
  pattern plus a separate loading/level stage is normal practice; our gap is that the second stage is mostly switched off (loading weight 0 on most briefs).
- **Loading criteria:** mouth circumference >~ one wavelength at cutoff; Keele d = K/(theta * f_theta), K ~ 2.54e4 m*deg*Hz; designers want Re(z) >~ 0.5-0.7
  in band. Our `load_term = mean_f max(0, z_min - Re z)`: shape fine, but the band-mean dilutes a deep sub-cutoff deficit; recommend max or a sub-f0
  integral, weights 0.3-0.5 (CD waveguide), 0.8-1.0 (PA to 400-600 Hz), 1.0 (low-reach).
- **Scoring honesty:** `cov` err^2/100 with tolerances 2/4.5 is ~14/21 deg RMS per unit (generous); the mask below f0 should be one-sided; keep `distd`
  (std of DI, one of the two best CD metrics per Sridhar/Tylka/Choueiri, AES 140, 2016) and down-weight `dislope` on CD briefs; consider polar
  cross-correlation as a report metric.
- **Validation plan:** compare against a published measured horn (Ath-generated + builder measurements, JBL 2380-class, Geddes OS): beamwidth +-5 deg
  (+-3 in the presence band), DI +-1 dB, f_theta within ~1/6 octave, Re(z) transition within ~1/3 octave [inferred thresholds]. Add a lumped
  compression-driver circuit over the stored BEM throat impedance (cheap). Build and measure two printed finalists (the J-winner and a loading-aware winner)
  on a turntable with a large roundover baffle.
- **Not verified by the research pass:** the gedlee.com directivity PDF (TLS error), the Panzer/Macey IOA PDF (404), the exact 2nd-harmonic figures of the
  ICA2019 distortion paper.
