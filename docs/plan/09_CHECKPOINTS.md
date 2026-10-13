# 09 CHECKPOINTS

**Wave 3. For the senior verifying agent, and for the human reading the reports.**

CP-0 through CP-6 live in their own task files and verify that *the code does what the task said*. This file holds **CP-7, the physics gate**, which verifies something different and more important: that the numbers are true.

Every other test in this project compares our code against our code. CP-7 compares it against closed-form solutions, against an independently written solver, against symmetry, and against published horn behavior. It is the only thing between a working pipeline and a confident wrong answer.

---

## Checkpoint map

| CP | Owner | Gate |
|---|---|---|
| CP-0 | 02 | Stack installed, a mesh solved, seven measurements, six capability answers |
| CP-1 | 03 | Skeleton, `types.py` frozen, configs load, `doctor` green |
| CP-2 | 04 | Meshes build in **metres**, quarter really is a quarter, `f_max^2` scaling |
| CP-3 | 05 | Real solve returns a valid `Response`; symmetry under 0.1 dB; warm worker works |
| CP-4 | 06 | Every metric matches a closed form; cardioid reads 180.0 and 4.771 |
| CP-5 | 07 | Dataset survives a crash; a record is sufficient to retrain without the run |
| CP-6 | 08 | End to end: selftest, cross-check, run, search, report |
| **CP-7** | **senior** | **The physics gate. This file.** |

No wave advances on a checkpoint declared passed without pasted output. "Tests pass" is not a checkpoint.

---

## CP-7a: the analytic pulsating sphere

Exact solution for a sphere of radius `a` with uniform radial surface velocity:

```
|p(r)| = rho*c*U0 * ( ka / sqrt(1 + (ka)^2) ) * (a/r)
```

The right benchmark for three reasons: it is the only 3D radiator with a simple exact closed form; it exercises Burton-Miller on a closed surface at every `ka`, including the interior-resonance frequencies where naive BEM fails; and its pattern is perfectly round, so an error is visible rather than merely numerical.

| # | Check | Pass |
|---|---|---|
| 1 | `R(ka) = |p| / (ka/sqrt(1+ka^2))` constant in dB across `ka` = 0.5, 1, 2, 4, 8 | spread under **0.5 dB** at 6 elements per wavelength |
| 2 | Omnidirectionality: std dev over the balloon | under **0.1 dB** at every `ka` |
| 3 | Spreading: 2 m versus 4 m | **6.02 dB** +/- 0.05 |
| 4 | Convergence at subdivisions 3, 4, 5 | error monotonically decreasing |

### Reading a failure

| Symptom | Almost certainly |
|---|---|
| 1 fails, 2 passes | Mesh too coarse, or the port drive is not a clean uniform velocity. Try subdivision 4 before suspecting anything else. |
| 2 fails badly, 3 passes | **The port model cannot impose uniform normal velocity on a closed surface.** Not our bug. Document it and rely on CP-7b through CP-7f, none of which depend on the port model. This is the only acceptable waiver. |
| 3 fails | Probe points are not where we think, or the probe radius is inside the near field. A frame or units bug. **Stop everything**: nothing downstream means anything. |
| 4 non-monotone | Either refinement is not uniform, or the GMRES tolerance (`1e-5`) is loose relative to the discretization error. Try `BLAB_BEAT_GMRES_TOL=1e-7` and see if it becomes monotone. |
| 1 fails only at `ka = 8` | Acceptable if 6 elements per wavelength is marginal there. Report the number. |
| Error grows as `ka^2` | Classic too-coarse-mesh signature. |
| One `ka` wildly off, neighbours fine | A spurious interior resonance leaking through, which is what Burton-Miller exists to prevent. Worth an upstream question to Collin. |

---

## CP-7b: two solvers, independently written, on the same mesh

This may be stronger evidence than the analytic test, and it exists only because Collin built both.

Solve the seed mesh at 5 frequencies with `beat_cuda` (Julia, Float32, GMRES, GPU) and `bempp_cpu` (bempp-cl, OpenCL or Numba, CPU). Report the per-frequency maximum difference in normalized dB across the horizontal cut.

| Measured | Reading |
|---|---|
| under 0.2 dB | Both are very likely right. This is the strongest verification available in the project. |
| 0.2 to 1 dB | Plausible, given different formulations and precisions. Record it and check whether it grows with frequency, which would point at discretization rather than formulation. |
| over 1 dB | A real disagreement. Do not pick a winner by preference. Run the analytic sphere through **both** and see which one matches physics. |

**Do not tune anything to make them agree.** A disagreement is a finding with numbers attached.

Note from the bempp README: open-mesh results differ from the Metal backend because of the P1 space choice. Our meshes are closed, so this should not apply, but confirm which mode was tested.

---

## CP-7c: mesh convergence on a real horn

The sphere proves the solver. This proves **the mesh sizing we chose for horns**, which is a separate question: a horn has a throat where the field is strong and a mouth rim with high curvature.

Take the seed design. Solve at `epw` of **6, 9, 12 and 18**, same frequencies, same probes.

| epw | dofs | mesh s | solve s | peak VRAM | mean &#124;bw_h - bw_h(18)&#124; | mean &#124;DI - DI(18)&#124; | max &#124;SPL - SPL(18)&#124; in coverage |
|---|---|---|---|---|---|---|---|
| 6 | | | | | | | |
| 9 | | | | | | | |
| 12 | | | | | | | |
| 18 | | | | reference | reference | reference | reference |

**The gate: at `epw = 6`, beamwidth error under 2 degrees and DI error under 0.3 dB against the 18 reference.**

If not, raise `epw` in the config until it is and accept the cost. The entire search runs at screening fidelity, so a systematic bias at `epw = 6` is a bias in every ranking the tool ever produces. Being five times faster at the wrong answer is not a trade worth making.

**Also report the wall time and VRAM at each level.** Those four rows are the real cost curve of the project and they decide what kind of search is affordable. They are worth more than any estimate in `01_CONTRACTS.md`.

---

## CP-7d: symmetry, free and catching almost everything

The seed is mirror-symmetric about `x = 0` and `y = 0`, so:

```
| |p(+theta)| - |p(-theta)| |  <  0.05 dB     every theta, every frequency
```

One check catches, at once: an asymmetric mesh, a wrong quadrant-to-flag mapping, a probe sign error, a wrong axis convention, and an off-by-one in the response adapter. It costs one solve that was happening anyway.

Report the **maximum asymmetry across all angles and frequencies** as a single number.

| Measured | Meaning |
|---|---|
| under 0.01 dB | Clean, and it tells you the solver's own noise floor. |
| 0.01 to 0.1 dB | Fine. Note it as the noise floor and make sure `tolfun` sits above it. |
| 0.1 to 1 dB | Something is slightly wrong. Most likely the mesh is not actually symmetric, or the quadrant reduction and symmetry flag disagree. Re-read task 02's M6. |
| over 1 dB | A real bug. Do not proceed. |

Then confirm task 02's **M6** independently: the same physical horn solved as a full mesh with no symmetry flag, and as a quarter mesh with `yz+xz`, must agree. This is the single most valuable number produced anywhere in this project, because it validates the mesher, the solver, the symmetry mapping and the frame convention simultaneously.

---

## CP-7e: plausibility against published horn behavior

Three relations the baseline must roughly obey. They are rules of thumb, so the tolerances are loose on purpose. They catch gross errors, like a factor of two or a half-angle-versus-full-angle confusion, that every internally consistent test would miss.

### 1. Pattern control breaks at the mouth-size limit

```
f0 = 25400 / ( d_m * theta_deg )
```

Verified against the source's own worked examples: a 12 inch mouth at 90 degrees gives 926 Hz, and at 45 degrees gives 1.85 kHz.

For the seed, compute `f0` for both axes from the **actual mouth dimensions in the mesh bounding box** and the **measured** beamwidths, not the targets.

**Check:** on the beamwidth-versus-frequency plot, each axis should hold near its measured value above its `f0` and widen rapidly below it. The narrow axis always needs the larger mouth, so vertical control should break at a higher frequency than horizontal for the same mouth aspect.

**Reject if:** the pattern holds flat two octaves below `f0`, which means the beamwidth extraction is reading the wrong thing; or it collapses two octaves above, which means the geometry is far smaller than intended or the units are wrong.

### 2. Higher-order throat modes

```
f11 = 1.8412 * c / (2*pi*a)
```

| Throat | f11 |
|---|---|
| 1.0 in | 7,914 Hz |
| 1.4 in | 5,653 Hz |
| 2.0 in | 3,957 Hz |

**Check:** on a 1.4 inch throat, expect the polars to become visibly less well behaved somewhere above roughly 5.7 kHz. A model that stays perfectly smooth to 16 kHz is suspicious: either the mesh is too coarse to resolve the modes, or the throat is driven as a flat uniform piston that cannot excite them. Both are useful to know, and the second is a real limitation of a velocity-port model that belongs in the report.

### 3. DI versus measured beamwidth

In the band where the pattern is controlled, computed DI should sit within about **1.5 dB** of the value implied by the measured beamwidths through `10*log10(4*pi/Omega)`.

**This is the best cross-check in the project**, because the two quantities come from completely different probe sets: beamwidth from two arcs, DI from a balloon. A disagreement over about 3 dB means one of them is computed wrong.

**It only works if DI came from the balloon.** If `di_source == "cuts_estimate"`, this check is circular and must be skipped, and said so. Do not pass CP-7e on estimated DI.

---

## CP-7f: the noise floor and what it permits

Collect four numbers that earlier checkpoints already produced:

| Number | From |
|---|---|
| Solver idempotence disagreement | task 05 test 13 |
| Mesh asymmetry | CP-7d |
| Discretization error at `epw = 6` | CP-7c |
| Two-solver disagreement | CP-7b |

**The largest is the smallest difference this tool can legitimately resolve.** It goes at the top of every report, and CMA-ES `tolfun` sits above its objective-space equivalent.

Why this matters here specifically: the project's earlier aperture study measured a **0.12 dB** spread across six very different cell tilings, against a 2.63 dB irreducible diffraction floor. If the pipeline's noise floor lands at 0.3 dB, then that entire question is **below the resolution of this tool** and no amount of searching will answer it. That is a genuinely important finding and it should be stated plainly rather than discovered later.

---

## What the senior agent must refuse

| Refuse | Because |
|---|---|
| A checkpoint declared passed with summarized rather than pasted output | The summary is where the failure hides. |
| A tolerance widened to make a test pass | Worse than a failing test: it stops anyone looking again. |
| A `pytest.mark.skip` added during implementation | A silent permanent waiver. |
| CP-7a waived for anything but a documented port-model limitation | It is one of only two external checks on the solver. |
| CP-7b skipped because bempp was inconvenient to install | It is the other one. Two independent implementations agreeing is the strongest evidence available. |
| CP-7c skipped because the mesh "looks fine" | Coarse-mesh BEM errors are smooth and plausible. Looking fine is the failure mode, not the absence of one. |
| CP-7e passed on `cuts_estimate` DI | The check becomes circular. |
| Any claimed improvement smaller than the CP-7f floor | It is not a result. |
| A dof cap raised without a VRAM measurement | A CUDA OOM can orphan a Julia worker that poisons every later solve in the session. |
| A modified file inside any HornLab, Boundary Lab, BEAT or Julia install | Rule 1. Unpins the dependency and makes every result and every dataset row irreproducible. |
| A new BEM, mesher or gmsh writer in our tree, outside `selftest.py` | Rule 2. |
| Non-deterministic mesh generation or hashing | Breaks the cache, the resume and the dataset simultaneously, and silently. |
| A dataset record missing its `lib_shas` | A row you cannot attribute to a solver version is a row you will have to throw away. |

---

## Verification dispatch prompt

```
You are verifying hornlab-search against physics, not against its own tests.
Read 09_CHECKPOINTS.md in full, then 01_CONTRACTS.md, then
12_RESEARCH_BASIS.md.

You have the completion reports from tasks 02 through 08, each with pasted
terminal output. Work through CP-7a, 7b, 7c, 7d, 7e and 7f. Run the commands
yourself; do not take a prior report's word for a number.

For each, report PASS, FAIL, or WAIVED with a reason, the measured numbers,
and your reading of what any failure means.

Then confirm, from the pasted tables rather than by reading code:
  - beamwidth is a TOTAL included angle (cardioid reads 180, not 90)
  - DI is a full-sphere average (dipole AND cardioid both read 4.771 dB)
  - every mesh bounding box is in METRES, not millimetres
  - the quarter mesh and the symmetry flag are paired, and task 02's M6
    full-versus-quarter comparison agrees
  - DI and measured beamwidth agree within 1.5 dB in the controlled band,
    with DI from the balloon and not the cuts estimate
  - the two solvers agree, or the disagreement is quantified
  - every evaluation produced exactly one dataset record, including failures

Finish with:
  1. The project's noise floor, as one number in dB, and what it permits.
  2. Any claim in any report that the evidence does not support.
  3. The three things most likely to be wrong that no current test would catch.

Do not fix anything. Report.
```

The last line is deliberate. A verifier that also repairs stops being an independent check: it ends up verifying its own edits. Findings go back to the owning task.
