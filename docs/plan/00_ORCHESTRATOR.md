# 00 ORCHESTRATOR

**Read this first. If you are not the orchestrator, read `01_CONTRACTS.md` and then only your own task file.**

---

## What we are building

`hornlab-search` finds horn geometry **by objective**: you state a target (coverage, band, ripple tolerance, throat size, a room), and it generates candidate geometry, solves each with GPU boundary-element acoustics, scores it, and iterates.

It is a **search layer over Collin's existing HornLab stack.** We do not write a mesher, a solver, or a plotting library. Those exist, are maintained, and are what his GUI uses, so our results stay comparable with his.

| We consume | Import | Job | License |
|---|---|---|---|
| `hornlab-waveguide-mesher` | `hornlab_mesher` | geometry + gmsh meshing | AGPL-3.0 |
| `hornlab-beat-bem` | `hornlab_beat_bem` | GPU BEM (CUDA) | GPL-3.0+ |
| `hornlab-bempp-bem` | `hornlab_bempp_bem` | CPU BEM, the cross-check | AGPL-3.0 |
| `hornlab-plots` | `hornlab_plots` | report figures | AGPL-3.0 |

Our package is AGPL-3.0-or-later as a result. `12_RESEARCH_BASIS.md` explains why in one paragraph.

**Nothing in those six repos optimizes anything.** That gap is our scope, and it is a well-defined one.

---

## Hard rules for every agent

1. **Never modify any installed HornLab, Boundary Lab, BEAT or Julia file.** If one looks broken, write it into `NOTES_FOR_SENIOR.md` and stop that line of work.
2. **Never write a BEM solver, FEM solver, mesher, gmsh writer, Green's function, or plotting library.** All five exist in the stack. If you are writing one, you are off plan.
3. **Never invent a parameter name, a config key, a tag number, or a unit.** They come from the mesher's and solver's own schemas, reproduced in `01_CONTRACTS.md`. If you need one that is not there, it is a contract gap: `NOTES_FOR_SENIOR.md`, then stop.
4. **Never change a frozen contract.** `01_CONTRACTS.md` is frozen.
5. **Only create or edit files your task file says you own.**
6. **Paste real terminal output.** Not a summary. A checkpoint without pasted bytes is not done.
7. **Never loosen a tolerance, skip a test, add `pytest.mark.skip`, or widen an assertion to make something pass.** A reported failure is useful. A weakened passing test is a trap that costs days.
8. **Blocked twice on the same error: stop.** Append a dated block to `NOTES_FOR_SENIOR.md` and report. Do not improvise an architecture.

### The three silent killers

Acoustic BEM does not crash when it is wrong. It returns a smooth, plausible, confident, incorrect answer. Three specific ways that happens here:

| Killer | Why it is silent | Guard |
|---|---|---|
| **Wrong `mesh_scale`** | The mesher writes **metres**; the solver README's example is **millimetres**. A 1000x horn solves fine and looks smooth. | `mesh/build.py` asserts the mesh bounding box is of order 0.1 to 1 m. |
| **Quadrants and symmetry flag disagree** | A quarter mesh solved with no symmetry flag, or a full mesh solved as a quarter, both produce clean wrong polars. | Both values derive from one source and the pairing is tested. |
| **DI from cuts, labeled as DI** | The cuts estimate assumes a separable rectangular pattern and is wrong for anything lobed. | `MetricSet.di_source` is carried on every evaluation and printed in the report. No checkpoint passes on `cuts_estimate`. |

---

## Wave plan

Agents in the same wave run in parallel. A wave does not start until the previous wave's checkpoints pass.

```
WAVE 0   serial, one agent, nothing else starts
  02_TASK_ENV ............. install the HornLab stack, verify CUDA, calibrate
  03_TASK_SCAFFOLD ........ repo skeleton, types.py, config, doctor
        |
        v
WAVE 1   four agents in parallel, zero shared files
  04_TASK_DESIGN_MESH ..... design/ + mesh/      drive hornlab_mesher
  05_TASK_SOLVE ........... solve/               two backends, warm worker
  06_TASK_METRICS ......... metrics/ + targets/  closed-form tested
  07_TASK_DATASET ......... dataset/             the phase-2 prerequisite
        |
        v
WAVE 2   one agent
  08_TASK_PIPELINE ........ objective/ search/ report/ cli.py
        |
        v
WAVE 3   senior agent, verification only, writes no code
  09_CHECKPOINTS .......... the physics gate
```

Then, separately and later: `11_PHASE2_SURROGATE.md`.

**Why these four in Wave 1:** they are the only four modules with zero file overlap and zero import dependency on each other. Design makes meshes. Solve consumes a mesh path. Metrics consume a `Response`. Dataset consumes everything but imports only `types`. They meet in Wave 2 through the dataclasses in `01_CONTRACTS.md`.

### Parallelism means writing code in parallel, not solving in parallel

One GPU. One BEM solve at a time: the operator is a dense matrix that occupies 0.5 to 4.6 GB of an 8 GB card. Nothing in this plan runs concurrent solves and no agent should add that. `search/evaluate.py` stays a pure function of its arguments so that the day a second GPU exists, parallelism is a one-line change.

This is also precisely the constraint that `11_PHASE2_SURROGATE.md` removes: a trained surrogate evaluates thousands of candidates in one batched forward pass. The card is a mediocre dense-BEM device and a good inference device.

---

## File ownership

An agent may **create and edit** only its own paths. It may **read** anything.

| Path | Owner |
|---|---|
| `TOOLCHAIN.md` | 02 |
| `pyproject.toml`, `.gitignore`, `README.md` | 03 |
| `hornlab_search/__init__.py`, `types.py`, `constants.py`, `config.py` | 03 |
| `hornlab_search/cli.py` | 03 until Wave 2, then 08 |
| `tests/conftest.py`, `tests/test_config.py` | 03 |
| `examples/*.yaml` | 03 creates; 04 may add family examples |
| `hornlab_search/design/**`, `mesh/**` | 04 |
| `hornlab_search/solve/**` | 05 |
| `hornlab_search/metrics/**`, `targets/**` | 06 |
| `hornlab_search/dataset/**` | 07 |
| `hornlab_search/objective/**`, `search/**`, `report/**` | 08 |
| `tests/test_design_*.py`, `test_mesh_*.py` | 04 |
| `tests/test_solve_*.py` | 05 |
| `tests/test_metrics_*.py`, `test_targets_*.py` | 06 |
| `tests/test_dataset_*.py` | 07 |
| `tests/test_objective_*.py`, `test_search_*.py`, `test_report_*.py`, `test_end_to_end.py` | 08 |
| `NOTES_FOR_SENIOR.md` | everyone, **append only** |

Need a file you do not own? Do not edit it. Append the exact change to `NOTES_FOR_SENIOR.md` and continue with the rest of your task.

---

## Dispatch prompt template

Paste this verbatim, filling the brackets. Do not paraphrase it: it carries the hard rules.

```
You are implementing one task in the hornlab-search project.

Read these completely, in this order, before writing any code:
  1. <path>/01_CONTRACTS.md
  2. <path>/[YOUR TASK FILE]
  3. <repo>/TOOLCHAIN.md
  4. The "Hard rules for every agent" section of <path>/00_ORCHESTRATOR.md

Your task file lists the exact files you own. Create and edit only those.
Do not edit any file owned by another task. Do not modify any installed
HornLab, Boundary Lab, BEAT or Julia file. Do not write a solver, a mesher,
a gmsh writer, or a plotting library: all of those already exist in the
stack and your task file says which function to call instead. Do not invent
a parameter name, config key, tag number, or unit; every one you need is in
01_CONTRACTS.md.

Work through your task file's Build steps in order. Each names the functions
to write and their exact signatures. Where the task file gives code, use it.

At your checkpoint, run every command listed and paste the complete, unedited
terminal output into your report. Do not summarize it. If a test fails,
report the failure with its full traceback. Do not loosen a tolerance, skip a
test, or widen an assertion to make something pass.

Blocked twice on the same error: stop, append a dated block to
NOTES_FOR_SENIOR.md saying what you tried and what the error was, and report.
Do not design an alternative architecture.

Your final report contains, in this order:
  1. Every file you created, with its line count.
  2. The complete output of every checkpoint command.
  3. Anything in your task file you did not finish, and why.
  4. Anything you appended to NOTES_FOR_SENIOR.md.
```

---

## Definition of done

Six commands, run on the real machine, with pasted output:

```bash
hornlab-search doctor                                     # toolchain is real
hornlab-search selftest --analytic --tol-db 0.5           # solver tells the truth
hornlab-search selftest --crosscheck                      # two solvers agree
hornlab-search run --config examples/osse_baseline.yaml --mode screen
hornlab-search search --config examples/search_smoke.yaml --budget 60
hornlab-search report runs/<latest> --out report.html
```

Plus: `dataset/index.jsonl` has one line per evaluation, including the failures.

**If the search does not beat the seed, that is a result, not a failure**, and it goes at the top of the report in plain words. The plan fails only if the machinery does not run or the numbers are not honest.

---

## Phase 1 scope boundary

Build these later, each as its own phase, each with a named seam in the code today:

| Not now | Seam that exists today | Why it waits |
|---|---|---|
| Neural surrogate, inverse design | `dataset/` written from day one with the excitation block, sampled boundary traces, and the structured-grid record; `solve/base.py`'s `Backend` protocol; `search/nsga.py` stub | Needs the dataset the phase-1 search produces, in the right shape. Four small things in Wave 1 make it reachable and cannot be backfilled: the excitation spec on every row, sampled `surface_traces`, exact trace-to-field recovery, and multi-family sampling. `11_PHASE2_SURROGATE.md` section 11 is the contract. |
| NSGA-II Pareto fronts | `search/nsga.py` | At 4 to 8 s per solve we cannot afford 10,000 evaluations. The surrogate is what unlocks it. |
| Per-azimuth flare control | `design/custom.py`, empty | The mesher refuses it today. This is the geometry novelty opening, not a bug fix. |
| MEH ports and chambers | mesher tags 8 to 11 exist | Needs coupled interior modeling. The geometry path is already there. |
| Metamaterial / graded-admittance termination | none | **Blocked on a real capability gap:** non-rigid impedance boundary conditions. Task 02 checks whether either solver supports them. |
| Multicell septa, aperiodic tiling | none | **Settled.** The earlier study measured 0.12 dB across six tilings against a 2.63 dB floor. Do not reopen. |
| Differentiable BEM / adjoint | none | Requires modifying BEAT. Rule 1. A trained surrogate is differentiable by construction and is the tractable substitute. |
| Any GUI | none | The CLI plus the HTML report is the interface. Collin's GUI is the GUI. |
| Concurrent GPU solves | `evaluate()` is a pure function | One card. |

---

## Where the reasoning lives

- `12_RESEARCH_BASIS.md`, in this folder: everything verified this pass, with sources, the corrections to the previous plan, and a coverage matrix of every project idea.
- Horn project: context and reference: https://claude.ai/code/artifact/7242baee-bc60-47d6-8fee-d678348dbe67
- Building the tool: https://claude.ai/code/artifact/82a65157-95d5-4cb1-bc92-bbf23794367f

Agents need none of them. The senior verifier should read `12_RESEARCH_BASIS.md`.

---

## One standing note on targets

Every number describing a horn in this plan (75 x 45 degrees, 700 Hz, the band edges, the dof caps) is a **configurable default in `examples/*.yaml`**, not a requirement. They exist so something concrete runs on day one. A horn number found hardcoded in a module is a bug.
