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
