# hornlab-search implementation plan, v2

**Hardened and ready to hand off.** Thirteen files. Give an orchestrator `00_ORCHESTRATOR.md` and it dispatches the rest.

This is a rewrite of the first plan after a verification pass against the live repositories. Nine findings changed it materially; `12_RESEARCH_BASIS.md` lists every one with sources.

---

## What gets built

A command-line tool that **finds horn geometry by objective** instead of drawing a horn and measuring what it does.

```
hornlab-search doctor                                       # is the stack real
hornlab-search selftest --analytic                          # does the solver tell the truth
hornlab-search selftest --crosscheck                        # do two solvers agree
hornlab-search run      --config examples/osse_baseline.yaml
hornlab-search search   --config examples/search_smoke.yaml --budget 60
hornlab-search report   runs/<latest>
hornlab-search dataset  stats
```

It is a **search layer over Collin's existing HornLab packages**, not a parallel stack:

| Consumed | Job |
|---|---|
| `hornlab-waveguide-mesher` | geometry and meshing: OSSE, R-OSSE, ICW, FREEFORM |
| `hornlab-beat-bem` | GPU BEM on the 4070 |
| `hornlab-bempp-bem` | CPU BEM, the independent cross-check |
| `hornlab-plots` | report figures |

We write the design space, the objective, the search, the dataset, the report, and the geometry the mesher refuses. **Nothing in those four packages optimizes anything.** That gap is the scope.

---

## The nine findings that changed the plan

| # | Finding | Effect |
|---|---|---|
| 1 | **Collin already built a modular HornLab ecosystem**: a mesher, two solvers, and a plotting library, all pip-installable | We delete the mesher and solve-harness tasks and consume his packages instead |
| 2 | **The name `hornlab` is taken** by four of his packages | Renamed to `hornlab-search`, which reads as a sibling in his family |
| 3 | **`blab project solve` is not Boundary Lab's CLI.** That `--request / --events ndjson / --output` shape is waveguide-generator's `wg`. The v1 plan built a whole task on it | Gone. We call a Python function |
| 4 | **The solver is Float32 throughout**, with a Float64 GMRES Krylov space | The fp64-on-consumer-GeForce worry is void. The 4070 is a fine card for this |
| 5 | **Operator memory is exactly `8 * N_dof^2` bytes**, confirmed to three figures by two published datapoints | dof caps rise from 6,000/15,000 to 8,000/16,000/24,000, and the usable mesh is about 4x larger than v1 assumed |
| 6 | **The mesher's FREEFORM family is, almost exactly, the geometry v1 specified from scratch** | A week of work deleted. Superformula and superellipse are already there too |
| 7 | **Physical tags are `SD1G0`, `SD1D1001`, and seven more**, with tags 8 to 11 being MEH chamber and port structures | v1's invented tag names would have produced meshes the solver could not bind. MEH is reachable through this stack |
| 8 | **A warm worker starts in 0.01 s versus 12 to 15 s cold** | Worker lifecycle is a first-class requirement, not a detail. It is a 4x cost difference on every search |
| 9 | **The published break-frequency constant is 25,400**, verified against the source's own worked examples | v1 hedged to a derived 23,600 |

Plus one estimate that replaced a guess: **screening should cost roughly 4 to 8 seconds per candidate**, from a bandwidth model of the GMRES matvec, against v1's assumed 10 to 120 seconds. Task 02 measures it.

---

## The files

| File | For | Read when |
|---|---|---|
| `00_ORCHESTRATOR.md` | the orchestrator | first, always |
| `01_CONTRACTS.md` | **every agent** | before any code, completely |
| `02_TASK_ENV.md` | Wave 0 | installing and measuring |
| `03_TASK_SCAFFOLD.md` | Wave 0, same agent | after CP-0 |
| `04_TASK_DESIGN_MESH.md` | Wave 1A | |
| `05_TASK_SOLVE.md` | Wave 1B | |
| `06_TASK_METRICS.md` | Wave 1C | |
| `07_TASK_DATASET.md` | Wave 1D | |
| `08_TASK_PIPELINE.md` | Wave 2 | after CP-2 through CP-5 |
| `09_CHECKPOINTS.md` | the senior verifier | Wave 3, and whenever a number looks wrong |
| `10_TROUBLESHOOTING.md` | anyone stuck | symptom lookup, before improvising |
| `11_PHASE2_SURROGATE.md` | later | Collin's proposal, fully specified |
| `12_RESEARCH_BASIS.md` | you, and the senior verifier | what is verified, what is inferred, what is novel |

```
WAVE 0   02 env  ->  03 scaffold                               serial, one agent
WAVE 1   04 design+mesh | 05 solve | 06 metrics | 07 dataset    four agents, parallel
WAVE 2   08 pipeline                                            one agent
WAVE 3   09 checkpoints                                         senior, verify only
```

Parallelism means writing code in parallel. One GPU, one solve at a time.

---

## Handoff

1. Put these thirteen files where the agents can read them.
2. Give the orchestrator `00_ORCHESTRATOR.md`.
3. It dispatches task 02 using the verbatim prompt in that file.
4. Nothing advances past a checkpoint without **pasted terminal output**.

---

## Four things to know before you start it

**Tell Collin.** Five of this plan's decisions are really questions for him: whether he minds the `hornlab-search` name in his namespace; whether either solver supports **impedance boundary conditions** (task 02's C3, which gates the metamaterial-termination idea); what `surface_traces` actually returns and how big it is (C2b); whether the mesher's **structured `angular x length` point grid** is reachable through the public API (C4, which would settle phase 2's input representation for free); and how the **driver excitation** on tag `SD1D1001` is defined (C5, the frequency-encoding channel). One message saves a day each.

**The dataset is the long game, and its shape matters as much as its size.** Every evaluation writes a record from the first run, failures included. Four details in that record cost almost nothing now and cannot be backfilled: the **excitation spec** (B-FNO's verified finding is that frequency must be encoded through the boundary source field, not as a scalar, so a dataset recording only a frequency list is the wrong shape for the method it was collected for), **sampled boundary traces** at 1 in 20 (every boundary-centric surrogate trains on boundary solutions; far-field polars alone train none of them), the **structured-grid record**, and **multi-family balance**. `dataset/` is gitignored and precious: back it up. The methods it feeds needed 3,000 to 25,600 solves, roughly a weekend of GPU time you get free as a byproduct of searching.

**A field surrogate is not yet accurate enough to rank horns, and that shapes phase 2.** Every verified 3D acoustic neural-operator result is one to three orders of magnitude short of design-ranking accuracy: 18.4% relative field error on 3D resonant acoustics, plain-FNO errors of O(1) on oscillatory 1D problems, and an unverified but corroborating report of 0.87 dB at 500 Hz degrading to 5.35 dB at 4 kHz for 3D loudspeaker radiation. Our tolerances are 0.3 dB on DI. So phase 2 builds a **metric surrogate first** (smooth, low risk, and it is what actually makes NSGA-II affordable), then a **learned Dirichlet-to-Neumann solver backend** that keeps the exact boundary integral downstream and therefore fails loudly, and only then the field surrogate. `12_RESEARCH_BASIS.md` section 10 has the evidence.

**The noise floor decides what counts as a result.** CP-7f collects four numbers: solver repeatability, mesh symmetry, discretization error at 6 elements per wavelength, and the two-solver disagreement. The largest is the smallest difference this tool can legitimately see, and it goes at the top of every report. This matters concretely here: the earlier aperture study measured a 0.12 dB spread across six very different cell tilings. If the pipeline's floor lands near 0.3 dB, that question is below the tool's resolution, which is worth knowing rather than discovering later.

**Nothing here is a requirement.** Every horn number (75 by 45 degrees, 700 Hz, the band edges, the dof caps) is a default in `examples/*.yaml`. They exist so something concrete runs on day one. A horn number hardcoded in a module is a bug.

---

## The three forks worth taking first

Two of them are table rows, not code.

| Fork | Where | Why |
|---|---|---|
| **ICW curvature parameters as the search space** | `04`, trivial | `kappa0`, `theta1_deg`, `hold_start`, `hold_end` and friends already exist. Mouth termination is the top of the project's own sensitivity ranking, with roughly 2.6 dB available, and nobody has optimized these. `examples/icw_termination.yaml` exists for it. |
| **Guiding-curve superformula keys** | `04`, trivial | `gcurve_sf_m1`, `gcurve_sf_n1..n3` and the rest are already in OSSE. This is the Gielis superformula the project docs wanted, for the cost of a table row. |
| **Rayleigh-integral pre-screen** | `05` and `08`, medium | Roughly 100x cheaper per candidate. The difference between tuning a known shape and actually searching. Slots in as a third `Backend`. |

---

## What is settled and should not be reopened

Aperiodic cell tiling. The earlier study measured a **0.12 dB** spread across six very different tilings against a **2.63 dB** irreducible diffraction floor, and Lo's 1/N law explains why it is a combinatorial limit rather than a modeling-fidelity one. The sensitivity ranking from that work stands and should steer effort: path-length error 1.98 dB, septa blockage 0.42 dB, faceting 0.23 dB, tiling topology 0.13 dB.

`12_RESEARCH_BASIS.md` section 9 is a coverage matrix of every idea from the project docs against this plan, including the two that are honestly blocked rather than quietly dropped.

---

## Where the reasoning lives

Horn project: context and reference: https://claude.ai/code/artifact/7242baee-bc60-47d6-8fee-d678348dbe67
Building the tool: https://claude.ai/code/artifact/82a65157-95d5-4cb1-bc92-bbf23794367f
