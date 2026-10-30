# Matrix-free, GPU GMRES and FMM: what actually buys 2x at 5-20k dofs (2026-10-29)

**Status: research only; no code, config, example, test or D-night file changed, no GPU or solver job run.**
Owner-directed pass, branch `feat/hardened-plan-2026-10-29`. Evidence is static reading of the pinned fork,
the repo docs and the installed packages, plus arithmetic on already-recorded measurements. Every claim below
carries a label: **[measured]** (recorded by our own runs), **[reported]** (someone else's published number),
**[derived]** (arithmetic or physics from the two above), **[inferred]** (judgement, not yet measured).

Reviewer shortcut: section 0 verdict, section 4 options table, section 9 staged plan with stop rules.

**Path convention.** Short citations `julia/...`, `config.py` and `docs/beat-engine-CUDA.md` refer to the pinned
fork `forks/hornlab-beat-bem/`; `hornlab_search/...`, `docs/...`, `TOOLCHAIN.md` and `NOTES_FOR_SENIOR.md` refer to
this repo. Line numbers are as of this pass.

---

## 0. Executive verdict

1. **At 5-6k dofs nothing in this list is a 2x except quadrature order.** The CUDA path is assembly-bound
   (73-96 % of per-frequency wall, `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md:57-59`) and the fused path is
   already one-matrix assembly plus a device LU over the whole system
   (`julia/BeatEngineDriver.jl:1912-1921`, `julia/src/BeatEngineCudaBurtonMiller.jl:642-648`). Assembly is the
   work; the solve is 0.07-0.94 s. A matrix-free or FMM solver attacks the wrong 5 %.
2. **The cheapest credible 2x is quadrature order 4 -> 2, ideally wavelength-driven.** Order 4 is a 6-point
   triangle rule = 36 point-pairs per element pair; order 2 is 3 points = 9 point-pairs, i.e. **4x fewer kernel
   evaluations per regular pair** (`docs/beat-engine-CUDA.md:53`; `config.py:32,405`). The fork already ships a
   wavelength-driven 1/2/4 selector with `kh` cutoffs (`julia/BeatEngineDriver.jl:207-229`) but it is **CPU-only
   and dead code on CUDA** (`:186-187`, `:1766-1773`). At epw 6, `kh ~ 1.05`, so the selector would choose
   order 2 everywhere we actually solve. This is a port, not research.
3. **GMRES on CUDA is a 1.0-1.4x speed play and a real memory play, not a 2x.** The fork's GMRES is CPU/Metal
   only (`julia/src/BeatEngineDenseSolve.jl:72-73`) and needs 35-136 iterations at 1e-5/1e-6 with a worst case
   of 549 (`:14`, `:271`). Its honest value at 8 GB is deleting the LU factor workspace (~1.2-1.8 GB at 12k
   dofs [inferred]), which is a **feasibility** argument for 14k+, not a throughput argument.
4. **FMM is a feasibility play at 14k+, and the only path at 20k+.** Published/derived 2-5x applies in that
   band, with kD ~ 100 at 8 kHz on a ~0.7 m mouth. **10x is not supported at 5-10k by any source in this pass.**
   A 10x claim would require an O(N) method *and* an assembly-free operator *and* a preconditioner at kD ~ 100;
   we have none of those today.
5. **The 8 GB ceiling, not the algorithm, sets our near-term range:** 12,183 dofs is fast (11.0 s/freq),
   13,999 works at 88 % VRAM, 15,984 completes at 437 s assembly, 20,237 kills the worker host
   (`docs/CONTINUITY.md:696-697`, `docs/evidence/FUSED_CUDA_2026-10-24.md:309-313`).
6. **Axisymmetric/multimodal is the only 10-100x on the table, and it does not apply to our money briefs.**
   It is a round-horn method (m=0, ~400 unknowns, ms/freq), not a 90x60 or 90x90 morph method; WP13 is
   owner-deferred (`ISSUES.md:4`, `docs/GUI_INTEGRATION_PLAN_2026-10-25.md:81`).

**One-line recommendation:** run Phase 1 (quadrature A/B) before spending a single engineering week on a new
solver. If order 2 holds at 8 kHz, port the fork's existing selector to CUDA - that is the 2x. GMRES second,
FMM only if a 14k+ workflow is actually required.

---

## 1. What the stack actually does today

The names in our docs are optimistic; the code is specific. Read this table before proposing anything that
"solves iteratively" or "is matrix-free".

| Path | What is assembled | How it is solved | Evidence |
|---|---|---|---|
| **CUDA default** (`beat_cuda`) | four dense operators: SLP, DLP, adjoint DLP, hypersingular, plus two identity matrices | Burton-Miller LHS is **rebuilt per drive** (`d_lhs = 0.5*I - DLP + i/k*HYP`) and factored with a device `\` **per drive** | `julia/src/BeatEngineCore.jl:1527,1536`; `julia/BeatEngineDriver.jl:723-763,1912-1948` |
| **CUDA fused** (`solve.cuda_fused: true`) | **one** N x N Burton-Miller system | `lu!` on the device, one factorization shared across channels | `julia/src/BeatEngineCudaBurtonMiller.jl:642-648`; gate at `julia/BeatEngineDriver.jl:1425,1543-1547`; search side `hornlab_search/config.py:80,969`, `hornlab_search/solve/beat.py:223-246` |
| **CPU fused** / **Metal fused** | one N x N system | dense LU **or** diagonally-preconditioned GMRES, chosen by a cost model over (dofs, drives) | `julia/src/BeatEngineDenseSolve.jl:6-24`; `julia/BeatEngineDriver.jl:1922-1934` |
| **CUDA GMRES** | - | **does not exist** | `julia/src/BeatEngineDenseSolve.jl:72-73` ("CUDA or ROCm ... do not route through here yet") |
| **`bempp_cpu`** | dense weak forms from bempp-cl | GMRES by default (`LinearSolver.GMRES`), tolerance forwarded from `gmres_tol` | `hornlab_search/solve/bempp.py:108,168`; installed `hornlab_bempp_bem/config.py:211`; dense materialisation `hornlab_bempp_bem/symmetry.py:949` |
| **FMM / fast multipole** | - | **unused**; bempp-cl 0.4.2 ships an ExaFMM hook (`bempp_cl/api/fmm/exafmm.py`, `fmm_assembler.py`) but the standalone `exafmm` module is not installed in `.venv` and the adapter never calls it | grep for `fmm`/`multipole` in `hornlab_search/solve/*.py` and the fork's `.jl` sources returns nothing |
| **H-matrix / H2 / ACA / butterfly** | - | **does not exist** in Beat or in our bempp adapter | same grep |
| **Axisymmetric BEM** | - | **planned only**; a separate `backend: axibem` group, owner-gated | `docs/GUI_INTEGRATION_PLAN_2026-10-25.md:81`; owner-deferred `docs/ISSUES.md:4` |

Two structural consequences that the options table depends on:

- **The fused CUDA path already shares one factorization across drives.** With the usual two channel drives
  (H and V) the factorization is amortised twice, and more drives favour the LU further because GMRES pays
  per drive (`BeatEngineDenseSolve.jl:16-22`). What GMRES saves here is the factorization *memory*, not a
  repeated factorisation.
- **The default CUDA path re-factors per drive.** It is therefore the worst case for a Krylov method to beat -
  which is exactly why a CUDA GMRES would look good in a microbenchmark against that path and still deliver
  almost nothing against `cuda_fused`.

### 1.1 Gotchas already inside our own docs and tooling

- **`CAMPAIGN_SMOKE`'s "iterative solve is 0.07-0.94 s" is a misnomer on CUDA.** The campaign ran the fused
  CUDA path, and that path calls `lu!` (`docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md:57-59`;
  `julia/src/BeatEngineCudaBurtonMiller.jl:642-648`). The number is second only to the assembly share, but it
  is a *direct* solve. No iterative solve was measured.
- **`_cuda_use_matrix_free_burton_miller_rhs` is RHS-only.** It selects a matrix-free **right-hand side**
  assembly above 768 dofs (`julia/src/BeatEngineCore.jl:1509,1528`); the LHS operator matrices are always
  assembled dense (`:1527`). The name is a trap for anyone grepping for "matrix-free".
- **`gmres_tol` is hashed and recorded but not applied on Beat.** The Beat adapter documents that no
  GMRES-tolerance knob exists and writes `gmres_tol_applied: None`
  (`hornlab_search/solve/beat.py:24-25,353-354`), while the value still enters the solve hash
  (`hornlab_search/types.py:95,96-101`) and the dataset record (`hornlab_search/dataset/record.py:58`). Changing
  it today invalidates cache entries without changing a solve. Only `bempp_cpu` applies it.
- **An axisymmetric brief is not an axisymmetric BEM.** `symmetry: axisymmetric` in a brief selects a
  meridional generator and a fair target; it does not reduce the 3D boundary integral to an m=0 problem. The
  m=0 backend is WP13 and deferred.
- **bempp + Burton-Miller + native symmetry is refused**, so our cross-check adapter runs STANDARD on reduced
  meshes and Burton-Miller only on full meshes (`NOTES_FOR_SENIOR.md:150`). Any bempp FMM plan therefore pays a
  full-mesh dof count to get Burton-Miller, which eats a large part of the FMM gain at our kD.

---

## 2. Measured cost, and what the numbers say about the right lever

All at 8 kHz, fused CUDA, one frequency per call, `[measured]` unless noted.

| dofs | s/freq | VRAM share | note |
|---|---|---|---|
| 5,106 | 2.55 | 21 % | `docs/CONTINUITY.md:696` |
| 8,919 | 6.62 | 41 % | same |
| 12,183 | 11.0 | 73 % | measured safe cap (`ISSUES.md:457`) |
| 13,999 | 13.78 | 88 % | works, no GUI headroom |
| 15,984 | 458.6 (assembly 437.2, solve 16.7) | 95 % | "fits, do not use" (`docs/evidence/FUSED_CUDA_2026-10-24.md:312,344,349`) |
| 20,237 | - | - | worker-host death (`docs/evidence/FUSED_CUDA_2026-10-24.md:313`) |

Derived facts that constrain every option:

- **Empirical growth from 5,106 to 13,999 is ~N^1.67**, not N^2 or N^3 [derived: 2.74x dofs buys 5.40x time].
  At these sizes the limiting resource is memory traffic/occupancy, not arithmetic.
- **Assembly is 73-96 % of the frequency** (`CAMPAIGN_SMOKE_2026-10-27.md:57`). At 15,984 dofs assembly is
  95.6 % of the 458.6 s [derived: 437.184/458.577]. Anything that does not touch assembly cannot deliver 2x.
- **The dense operator alone is 8N^2 bytes** (`NOTES_FOR_SENIOR.md:57`, confirmed at 20,193 dofs = 3.038 GiB):
  12,183 dofs = 1.19 GB, 15,984 = 2.04 GB. The LU factorization adds a factors copy and pivots on top
  [inferred: +1.0-1.8 GB at 12k]. This is why the memory ceiling sits where it does.
- **The 8 GB card is the ceiling** (`TOOLCHAIN.md:9,94`), and the caps in force are throughput caps, not fit
  caps (`TOOLCHAIN.md:121`; `ISSUES.md:457`).

**The lever that follows from this table is assembly, not the linear solve.** Each of the four options below is
judged on how much assembly it removes and how much memory it removes.

---

## 3. Break-even arithmetic (why "matrix-free" is not automatically faster)

Dense LU is O(N^3) with a factorization shared across drives; GMRES is O(iter x N^2) per drive with no shared
factorization. The fork measured the crossing on its own ATH ladder: **2,000-5,000 P1 dofs at one drive on CPU**
(`julia/src/BeatEngineDenseSolve.jl:14-18`, `:123`). Everything else follows from machine constants:

| Comparison | Where it crosses | Confidence |
|---|---|---|
| GMRES vs dense LU, same matrix, CPU | 2k-5k dofs at 1 drive; drive crossover ~2.4 drives at 5,107, ~4.0 at 10,230, ~11 at 20,422 | **[measured]** `BeatEngineDenseSolve.jl:14-22,123` |
| GMRES vs dense LU, GPU | ~5k-10k dofs, because a device LU is fast and a device matvec is bandwidth-bound | **[inferred]** from the CPU ladder + the fork's own statement that the CUDA/ROCm LU "do not route through here yet" (`:72-73`) |
| FMM vs dense, kD ~ 100 | ~10k-20k dofs | **[reported]** broadband FMM-BEM literature (S5) plus **[inferred]** for our operator |
| Quadrature order 4 -> 2 | immediate at every size, no crossover | **[derived]** 36 -> 9 point-pairs per pair |

The decisive line for our range: at 5,106 dofs the whole solve is at most 0.94 s of 2.55 s. Even an infinitely
fast solver caps the win at **1.58x** and realistically delivers 1.05-1.25x [derived]. No Krylov or FMM variant
escapes that arithmetic **unless it also makes the assembly cheaper or the mesh smaller**.

---

## 4. Options table

Gain columns are per-frequency wall-clock at fixed accuracy and fixed epw (6 unless stated). "BM fit" = works
with our Burton-Miller coupled formulation without a new formulation.

| Option | Complexity | GPU fit | BM fit | Library / route | Effort | Risk | Gain at 5-6k | Gain at 14-20k |
|---|---|---|---|---|---|---|---|---|
| **Dense fused status quo** | already shipped | native CUDA | yes (fused BM) | our fork, `cuda_fused` | 0 | none new; memory ceiling is the known limit | 1.0x (baseline) | 1.0x at 14k; **fails** at 20k |
| **Quadrature order 2** (or the wavelength selector) | low - a rule/cache port | native CUDA | yes (same kernels) | fork `quadrature_order` + `regular_quadrature_mode` | **0.5-1 day** to expose; 2-4 days to port the selector | accuracy at 8 kHz unproven; per-order CUDA caches needed (`beat-engine-CUDA.md:145`) | **1.5-2.2x** [inferred] | **1.6-2.5x** [inferred]; also cuts register pressure at the edge |
| **GMRES on CUDA** | medium | native CUDA | yes (same matrix) | reuse `BeatEngineDenseSolve.jl` GMRES with a CUDA matvec | **3-6 days** | fallback rate, FP64 Krylov cost, no iteration-count data on CUDA | 1.0-1.25x speed; **-1.0-1.8 GB peak** | 1.1-1.4x; may lift the 14k wall [inferred] |
| **bempp-cl FMM + BM + OSRC (CPU)** | medium | CPU only | yes in principle; our adapter refuses BM + symmetry | bempp-cl + ExaFMM (S1, S2, S13) | **1-2 weeks** for a probe | ExaFMM not installed; CPU speed; symmetry refusal forces full meshes | ~1.0-1.2x (CPU lane) | 2-5x CPU vs CPU [reported] |
| **PVFMM (GPU FMM)** | high | GPU, but not CUDA-Julia native | needs a new BM layer | PVFMM (S28) + our own BM assembly | **2-4 months** | high-k GPU maturity unverified; integration is new code | not worth it | 2-5x if it works |
| **H-matrix / H2** | high | possible (S7 GPU assembly) | yes (dense blocks are fine) | H2Lib (S31), our own ACA | **1-3 months** | **ACA ranks blow up at kD ~ 100**; memory can be worse than dense | ~1.0x | poor fit at our kD |
| **HIF / butterfly** | very high | research-grade | yes | no maintained library | 3-6 months | no reference implementation we can adopt | - | - |
| **FMM3D hfmm3d** | medium-high | **CPU only** (Apache-2.0) | needs BM layer | FMM3D (S29) | 1-2 months | algorithmic fit is good; CPU throughput and BM work | - | 2-5x CPU vs CPU [reported] |
| **Axisymmetric / multimodal** | high (new backend) | CPU or GPU | yes (axisymmetric BM exists in literature) | new backend, third-party solver (S20, S22) | **1-2 months + owner gate** | only round horns; license decision; new validation ladder | **10-100x, round only** | same, round only |

---

## 5. The quadrature lever (the recommendation)

### 5.1 The arithmetic

| Rule | Points per triangle | Point-pairs per element pair | Relative kernel work |
|---|---|---|---|
| order 4 (today's default) | 6 | 6 x 6 = **36** | 4.0x |
| order 2 | 3 | 3 x 3 = **9** | 1.0x |
| order 1 | 1 | 1 x 1 = 1 | 0.25x (accuracy unusable) |

The CUDA regular kernel evaluates those point-pairs in registers per pair
(`docs/beat-engine-CUDA.md:53`), so the point-pair count is close to the kernel cost. Orders allowed are
`(1, 2, 4)` with default 4 (`config.py:32,405`); the search adapter does **not** forward
`quadrature_order` today (`hornlab_search/solve/beat.py:470-493` passes no such key).

With assembly at 73-96 % of the frequency, a 4x cheaper assembly gives a hard upper bound of
**2.2x (73 %), 2.5x (80 %), 3.6x (96 %)** [derived]. Realistically 60-70 % of that, because singular Duffy
corrections, atomics, field evaluation and the solve do not shrink: **1.5-2.2x at 5-6k** [inferred].

### 5.2 The selector already exists - on the wrong backend

The fork ships a wavelength-driven selector:

- `regular_quadrature_mode: "fixed" | "wavelength"` (`config.py:419`);
- cutoffs `wavelength_kh_q1_max` (default 0.0) and `wavelength_kh_q2_max` (default 2.0), order chosen as
  `kh <= q1 ? 1 : kh <= q2 ? 2 : base` (`julia/BeatEngineDriver.jl:225-229`);
- `kh` is computed from a mesh element-length statistic (`:207-224`);
- **it refuses to run off the CPU backend** (`:186-187`), and even on CUDA the selected rule is discarded:
  `selected_rule = beat_backend == :cpu ? ... : rule` (`:1767-1773`), where `rule` was built once at
  `base_regular_order` (`:1498`).

At epw 6, `kh = 2*pi/6 = 1.05` [derived], which is `<= 2.0`, so **the selector would pick order 2 at every
epw-6 solve** - and at epw 18 (kh ~ 0.35) too. In other words the fork's author already decided order 2 is
adequate up to `kh = 2` (~3.1 elements per wavelength); the CUDA path just never received that decision.

### 5.3 What must be validated, and the acceptance bar

Order 2 is a *quadrature* change, not a formulation change: same mesh, same BM coupling, same unknowns. The
risk is integration error on the regular (non-singular) pairs at the top of the band, where the phase varies
fastest across an element. The singular/near-singular corrections are Duffy-quadrature and unchanged.

Validate at **500 Hz / 2 kHz / 8 kHz** on the same stored meshes, order 4 vs order 2, everything else pinned:

- **SPL:** <= 0.05 dB at 500 Hz and 2 kHz; <= 0.10 dB at 8 kHz.
- **Beamwidth:** <= 0.3 deg (the CP-7c epw-6-vs-18 figure, `NOTES_FOR_SENIOR.md:187`).
- **DI:** <= 0.05 dB (CP-7c measured 0.028, `:187`; noise floor 0.039, `:193`).
- **Throughput:** >= 1.5x at ~5k dofs, or >= 1.3x at ~14k.

The bars are anchored to CP-7, not invented: the two-solver noise floor is 0.039 dB
(`NOTES_FOR_SENIOR.md:185,193`), so a 0.05 dB SPL bar is the smallest round number above it. 8 kHz is allowed
0.10 dB because it is above the CP-7 band and the phase error grows with `kh`.

**Decision rule.** If order 2 passes low/mid and fails only at 8 kHz, do **not** abandon it: that is exactly
what the wavelength selector is for (order 2 up to its `kh` cutoff, order 4 above). If it passes everywhere,
expose a fixed `solve.quadrature_order: 2` first (one-line, hash-changing), then port the selector.

### 5.4 Port notes (so the estimate is honest)

- The CUDA regular assembly cache is keyed on `mesh + rule` (`docs/beat-engine-CUDA.md:145`); per-order caches
  are required for the regular assembly, the identity matrices and the field evaluation (the CPU path already
  does this: `julia/BeatEngineDriver.jl:1779-1799`).
- A new key must ride `hornlab_search` `SolveSpec.extra` and change the solve hash
  (`hornlab_search/types.py:96-101`); it must not silently default, and old configs must stay byte-identical
  when the key is absent (the WP14/WP15/WP16 precedent, `hornlab_search/solve/beat.py:483-488`).
- Fork changes go through `docs/FORKS.md` (pinned SHA, validation ladder), never a hand-edit of `.venv`.

---

## 6. GMRES on CUDA (second)

**What exists.** A production-quality diagonally-preconditioned GMRES, fully instrumented, with a cost-model
router and an explicit "fall back to the LU, never raise" contract
(`julia/src/BeatEngineDenseSolve.jl:6-59,457-718`). It is wired to the CPU and Metal fused paths only
(`julia/BeatEngineDriver.jl:1922-1934`).

**The published iteration counts** are not one number: the ATH ladder at 1e-6 true residual needs 51-136
across 5,107-20,422 dofs with a model constant of 70 (`BeatEngineDenseSolve.jl:103-125`); the corrected
FP32-recurrence sets need 35-42 where the bad recurrence claimed 584-1000 (`:363-372`); and the branch's own
worst measured case is **549**, over three meshes and three frequencies, "not monotone in either dofs or
frequency" (`:269-276`). Sliver-rim ATH meshes floor at 1.2e-6-9.4e-6 true residual, which is why the default
tolerance is 1e-5 and why the LU fallback is "load-bearing, not a safety net" (`:46-55`).

**Why it is not a 2x here.** At 5,106 dofs the fused solve is 0.07-0.94 s of a 2.55 s frequency. Best case,
GMRES removes most of 0.94 s -> 1.5x; typical 1.05-1.2x [derived]. The honest expected band is **1.0-1.4x**, and
the 1.4x requires both the top of the solve share and a big iteration win - neither measured on CUDA.

**Where it does pay: memory.** The LU needs the factor copy plus pivots on top of the 8N^2 operator. At 12,183
dofs the operator is 1.19 GB, so removing the factorization workspace is worth roughly **1.0-1.8 GB of peak**
[inferred]. That is the difference between "12k safe / 14k at the edge" and possibly "14k safe", which is a
capability change, not a speed change.

**Hard constraints if it is built.**

- **FP64 Krylov only.** The FP32 Arnoldi recurrence loses orthogonality: 584-1000 iterations where the true
  count is 35-42 (`BeatEngineDenseSolve.jl:363-372`). Any CUDA port that defaults to FP32 to save bandwidth is
  a trap - it will look fast and converge to the wrong place.
- **No silent default.** The router must keep choosing LU when the model says LU; an explicit
  `BLAB_BEAT_DENSE_SOLVE=gmres` stays an instruction.
- **Fallback must be visible in the record**, not swallowed (`:455`, `:1003-1005`).

**Acceptance bar for the A/B:** median <= 100 iterations, p95 <= 200, zero LU fallbacks on the test set, wall
<= 0.9x the same-path LU, and fields within 0.01 dB. Anything with >20 % fallbacks or >300 iterations is a
"no" for the fused path at our sizes.

---

## 7. FMM, H-matrix and the rest (third)

**Ordering of the field is not in dispute; the constants at our kD are.** Broadband FMM-BEM has been published
from kD ~ 1e-4 to 500 (S5) and on GPU/CPU (S6), and bempp-cl ships an FMM (S1, S2). What is missing is any
evidence at **kD ~ 100-235 with a Burton-Miller formulation, a 3-8 % accuracy bar and an 8 GB card**. Note our
band: at 8 kHz a 0.5 m mouth is kD ~ 73, a 0.7 m mouth is kD ~ 103; at 12 kHz those become ~110 and ~155
[derived: kD = 2*pi*f*D/c].

- **Exafmm-t (S3)** is CPU/OpenMP, low-frequency-oriented, dormant since 2021. It is not a kD-100 GPU path.
- **bempp-cl + ExaFMM** is the cheapest *measurement*: CPU, MIT-licensed, already installed as a Python module
  hook - but `exafmm` itself is not in `.venv`, and our adapter refuses BM + native symmetry
  (`NOTES_FOR_SENIOR.md:150`), so a probe runs full meshes and loses a chunk of the gain. Use it to calibrate
  FMM constants at our kD, **not** as the production route.
- **PVFMM (S28)** is the GPU candidate. Integration is not "link a library": Burton-Miller needs at least the
  SLP/DLP pair plus the adjoint/hypersingular combination, a near-field correction, and a preconditioner
  (OSRC, S13; Calderon, S14) or the iteration count at kD ~ 100 will eat the gain. Months, not weeks.
- **FMM3D / hfmm3d (S29)** is the best *algorithmic* CPU fit (Apache-2.0, Helmholtz-specific, maintained). It
  belongs in the CPU-lane conversation, not the GPU one.
- **NiHu (S30)** is the reference implementation for BM + FMM (GPL-3, CPU, 2023). Read it; do not ship it.
- **H-matrix / ACA (S31, S7)** is the wrong tool at this frequency: ACA ranks grow with electrical size, so
  block memory at kD ~ 100 can approach dense. S7's 5.5x is GPU **assembly** speedup for H-matrices, not a
  solve at our kD. H2/HIF/butterfly are the asymptotically right answers and have no maintainable route for us.
- **Sparse inverse-LU (S17)** is a 2025 author claim (ACM TOG) on a different operator class. Not evidence for
  our problem; do not cite it as a route.

**The memory argument that does work at 20k+:** FMM turns 8N^2 storage into O(N). At 20,237 dofs the dense
operator is 3.3 GB and the factor workspace on top of it is what kills the host
(`docs/evidence/FUSED_CUDA_2026-10-24.md:313`). If a 20k workflow is genuinely needed, FMM is not "faster" -
it is "possible".

**Prototype acceptance:** >= 2x at 14k vs the fused baseline, peak < 6 GB, SPL within 0.05 dB, beamwidth within
0.3 deg, no fallback, and the same record fields we rely on today.

---

## 8. Axisymmetric / multimodal (the only 10-100x, and it is not for our briefs)

An m=0 axisymmetric BEM reduces the 3D surface integral to a meridional 1D boundary integral with a Hankel
kernel. For a round horn that is **~400 unknowns instead of 5,000-20,000, and milliseconds per frequency** -
a genuine 10-100x [reported: S20, S22; inferred for our stack]. It is also the natural formulation for the
mode-matching / multimodal view of a horn (S20, S22).

It does not apply to `b3a` (90x90 morphs) or any H/V brief, because those geometries are not surfaces of
revolution. It would cover `salmon_axisym`-class round horns and the cone_plughorn family only if those are
truly round.

Cost and gates: a **new backend** (third-party solver or a new kernel), its own dataset group, its own
validation ladder, an owner license decision, and it must stay `di_source`-honest (theta-only DI). WP13 is
owner-deferred (`ISSUES.md:4`), and the plan already calls the backend `axibem`
(`docs/GUI_INTEGRATION_PLAN_2026-10-25.md:81`). This is a product decision, not a fork tweak: do not start it
as a "speed optimisation".

---

## 9. Staged plan (cheapest first), with stop rules

**Phase 0 - phase timing (1 day, no GPU-solver changes).** Take the three stored meshes we already solve
(5,106 / 12,183 / 13,999 dofs) at three frequencies (500 Hz / 2 kHz / 8 kHz) and log the four phases
(assembly, singular correction, solve, field). We already believe assembly is 73-96 %; this makes the number
per-mesh rather than per-campaign, and it is the baseline every later phase is scored against.

**Phase 1 - quadrature A/B (highest value, 0.5-4 days).**
1. Expose `solve.quadrature_order` (1/2/4) through `SolveSpec.extra`, hashed; absent = byte-identical.
2. Run the order-4 vs order-2 A/B at 500 Hz / 2 kHz / 8 kHz on the three meshes; apply the acceptance bars in
   5.3.
3. If 8 kHz fails: port the fork's wavelength selector to CUDA (per-order caches) and re-run with `kh` cutoffs.

**Phase 2 - GMRES on CUDA (3-6 days, only after Phase 1 is measured).** Reuse `beat_gmres!` with a CUDA matvec;
keep FP64 Krylov; no silent default; record method, iterations, fallback and residual. Score on speed **and**
peak VRAM. Success = the section 6 acceptance bar; the VRAM win is the real deliverable.

**Phase 3 - bempp FMM + OSRC CPU probe (1-2 weeks, off the GPU lane).** Install `exafmm`, run a full-mesh BM
problem at our kD, measure iteration counts and wall vs the dense bempp path. This answers "what do FMM constants
look like at kD ~ 100 for our operator" without touching the CUDA path.

**Phase 4 - PVFMM or FMM3D (only if Phase 3 justifies it).** GPU PVFMM if the GPU is mandatory; hfmm3d if a CPU
lane is acceptable. Both need the BM layer and a preconditioner; treat as a project, not a task.

**Stop rules (any one ends that phase, not the programme):**

- assembly drops below 50 % of per-frequency wall (the premise of Phase 1 is gone; re-rank);
- quadrature fails the 8 kHz bar *and* the selector port does not reach 1.2x;
- GMRES exceeds 300 iterations median or > 20 % fallback on the test set;
- FMM prototype is slower than the fused baseline at 14k, or off by > 0.1 dB;
- any proposal needs epw below 6 to make the numbers work (hard no: `NEXT_DEV_PRIORITIES.md`,
  "Not recommended").

---

## 10. Risks and gotchas

1. **Do not write a solver.** Hard rule 2 (`AGENTS.md`). A PVFMM/FMM3D integration is a *backend*, owner-gated,
   with its own validation ladder; it is not a "quick experiment" inside `solve/beat.py`.
2. **Fork changes only per `docs/FORKS.md`** - pinned SHA, per-change validation, never `.venv`.
3. **Any new knob must ride `SolveSpec.extra` and change the solve hash** (`types.py:96-101`); absent must be
   byte-identical to today. Silently reusing an old cache key with new physics is the failure mode we have
   already been bitten by (WP14/WP15 precedent).
4. **Do not default to GMRES.** The cost-model router exists for a reason; hardcoding it is wrong on the next
   machine and wrong on CUDA.
5. **Do not use an FP32 Krylov space** for speed (`BeatEngineDenseSolve.jl:363-372`).
6. **Do not use an H-matrix/ACA at kD ~ 100** (rank blow-up), and do not treat S7's assembly speedup as a solve
   speedup.
7. **Do not adopt bempp + ExaFMM as the GPU path.** It is CPU, and our adapter cannot combine it with BM +
   symmetry.
8. **Do not make FMM the first 2x.** At 5-6k it is a loss (extra setup, worse constants); the quadrature lever
   is a day's work.
9. **Do not promise 10x at 5-10k.** Nothing in this pass supports it. The only 10x-class result is axisymmetric
   on round horns, which is a different product.
10. **Quadrature order 2 is not free.** It is expected to move numbers at the 0.01-0.1 dB level [inferred]; the
    acceptance bars in 5.3 exist so that a "pass" means something. Re-run the two-solver cross-check (0.039 dB
    floor) on the new order before it becomes a default.

---

## 11. What we did not verify

- **No independent 5-20k Burton-Miller GPU benchmark** was found or run in this pass. Every GPU number here is
  our own 8 GB card.
- **FMM constants at kD ~ 100-235 are unverified.** Published claims (S5, S6) are for their operators,
  tolerances and hardware.
- **bempp-cl FMM defaults are low-frequency-oriented**; no source in this pass reports bempp + ExaFMM at our kD
  with Burton-Miller.
- **The GMRES iteration study is ATH-ladder CPU/Metal** (`BeatEngineDenseSolve.jl:103-125`), not CUDA. A CUDA
  matvec has different numerical and timing behaviour.
- **Several papers were read at abstract level only** (S6, S11, S17, S26). Their numbers are cited as
  [reported] and are not load-bearing for any recommendation.
- **No solver was run for this report.** No GPU job, no timing, no A/B.

---

## 12. Sources

**Repo evidence (I-series; file:line as of this pass, pinned forks under `C:\Users\hunte\Hrns\forks`):**

| ID | Source | What it establishes here |
|---|---|---|
| I1 | `forks/hornlab-beat-bem/hornlab_beat_bem/julia/src/BeatEngineDenseSolve.jl` | GMRES 35-136 iterations at 1e-6, worst 549; CPU crossover 2k-5k dofs; FP64 Krylov (584-1000 vs 35-42 in FP32); sliver-rim floor 1.2e-6-9.4e-6; LU fallback contract (`:14-55,103-125,271,363-372,455`) |
| I2 | `forks/hornlab-beat-bem/docs/beat-engine-CUDA.md` | 36 point-pairs per element pair at order 4 (`:53`); assembly dominance (`:149`); per-order caches needed for wavelength quadrature (`:145`); fused operator + matrix-free RHS (`:111-114`) |
| I3 | `TOOLCHAIN.md` | 8 GB card (`:9`), measured memory ceiling (`:94`), per-frequency cost curve and dof caps (`:115-121`); 15,984 @ 437 s assembly and the 20,237 host death are recorded in `docs/evidence/FUSED_CUDA_2026-10-24.md:309-313,344` |
| I4 | `NOTES_FOR_SENIOR.md` CP-7 | 0.039 dB two-solver floor; epw 6 vs 18 = 0.287 deg / 0.028 dB; 4e-6 dB symmetry (`:185-193`); bempp BM + symmetry refusal (`:150`) |
| I5 | `forks/hornlab-beat-bem/hornlab_beat_bem/config.py` | `quadrature_order` in (1, 2, 4), default 4 (`:32,405`); `regular_quadrature_mode` (`:419`) |
| I6 | `forks/hornlab-beat-bem/hornlab_beat_bem/julia/BeatEngineDriver.jl` | wavelength selector + kh cutoffs `q1_max=0`, `q2_max=2.0` (`:207-229`); CPU-only refusal (`:186-187`); selected rule discarded off CPU (`:1766-1773`); fused-CUDA direct solve (`:1912-1921`) |

**External (S-series; URLs/DOIs as supplied):**

| ID | Source |
|---|---|
| S1 | bempp-cl - https://github.com/bempp/bempp-cl (MIT; FMM/OSRC; ExaFMM; CPU FMM) |
| S2 | Betcke & Scroggs 2021, JOSS - https://doi.org/10.21105/joss.02879 |
| S3 | Exafmm-t - https://github.com/exafmm/exafmm-t (BSD-3; CPU OpenMP; low-frequency; dormant 2021) |
| S5 | Gumerov & Duraiswami 2009, JASA - https://doi.org/10.1121/1.3021297 (broadband FMM-BEM, kD 0.0001-500) |
| S6 | Gumerov & Duraiswami 2017, JASA - https://doi.org/10.1121/1.4987467 (GPU/CPU FMM-BEM) |
| S7 | Vater, Betcke, Dilba 2017, arXiv - https://arxiv.org/abs/1711.01897 (GPU H-matrix assembly 5.5x) |
| S11 | Sushnikova et al. 2023, SIAM MMS - https://doi.org/10.1137/22m1514040 (FMM-LU; not highly oscillatory) |
| S13 | Antoine & Darbas 2007, M2AN - https://doi.org/10.1051/m2an:2007009 (OSRC preconditioner) |
| S14 | Fierro-Piccardo & Jerez-Hanckes 2020, JCP - https://doi.org/10.1016/j.jcp.2020.109355 (Calderon) |
| S17 | Chen, Schafer, Desbrun 2025, ACM TOG - https://doi.org/10.1145/3731196 (sparse inverse-LU; author claim) |
| S20 | Dong, Shen, Gao 2020, JASA - https://doi.org/10.1121/10.0001037 (multimodal horn optimization) |
| S22 | Dong, Doc, Felix 2024, JASA - https://doi.org/10.1121/10.0025389 (axisymmetric horn/enclosure) |
| S26 | Hipperson, Hargreaves, Cox 2026, arXiv - https://doi.org/10.48550/arxiv.2604.21431 (JAX-BEM) |
| S28 | PVFMM - https://doi.org/10.4208/cicp.020215.150515sw (GPU FMM; high-k GPU maturity unverified) |
| S29 | FMM3D - https://github.com/flatironinstitute/FMM3D (Apache-2.0; hfmm3d; CPU) |
| S30 | NiHu - https://github.com/Q-Minh/nihu (GPL-3; BM+FMM reference; CPU; 2023) |
| S31 | H2Lib - https://github.com/H2Lib/H2Lib (LGPL-3; H2; CPU; high-k ranks) |



