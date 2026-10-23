# AGENTS.md — hornlab-search

Base-level instructions for every agent working in this repo, whether dispatched by OpenCode,
Claude Code, or a human. This file orients you. The numbered plan in `docs/plan/` commands you.

**Find anything:** [`docs/INDEX.md`](docs/INDEX.md) lists every doc; [`docs/CODE_MAP.md`](docs/CODE_MAP.md) maps every
module and config folder. Current state: `docs/CONTINUITY.md`; open work: `docs/ISSUES.md`; next round:
`docs/NEXT_DEV_PRIORITIES.md`. Keep the index and code map current in the same commit as any new doc or module.

---

## What this is

`hornlab-search` finds horn-loudspeaker geometry **by objective**: state a target (coverage, band,
ripple, throat size, a room), generate candidate geometry, solve it with GPU boundary-element
acoustics, score it, iterate (CMA-ES). It is a **search layer over Collin's HornLab packages**:

| Package | Job |
|---|---|
| `hornlab_mesher` | geometry + gmsh meshing (OSSE, R-OSSE, ICW, FREEFORM) |
| `hornlab_beat_bem` | GPU BEM (CUDA) |
| `hornlab_bempp_bem` | CPU BEM — the independent cross-check |
| `hornlab_plots` | report figures |

**We never write a solver, mesher, gmsh writer, Green's function, or plotting library, and never
modify any installed HornLab / Boundary Lab / BEAT / Julia file.** License: AGPL-3.0-or-later.
Every horn number is a YAML default in `examples/` — hardcoded horn numbers are bugs.

Interpreter: always `.venv\Scripts\python.exe` (absolute path in `TOOLCHAIN.md`), never bare `python`.

---

## Start here (reading order)

1. **`docs/CONTINUITY.md`** — which wave we are in, last checkpoint passed, next step, blockers,
   measured numbers. (Does not exist until Wave 0/03 creates it.)
2. **`docs/plan/01_CONTRACTS.md`** — completely, before any code. It is **frozen**.
3. **Your own task file only**: `docs/plan/02`–`08`.
4. **`TOOLCHAIN.md`** — interpreter paths, pinned SHAs, measured machine numbers.
5. **`CONTRIBUTING.md`** — branch/commit/PR rules and the 8 hard rules.

Stuck: `docs/plan/10_TROUBLESHOOTING.md` symptom table, before improvising.
Senior verifier additionally reads `docs/plan/09_CHECKPOINTS.md` and `12_RESEARCH_BASIS.md`.

---

## The 8 hard rules (verbatim from `docs/plan/00_ORCHESTRATOR.md`)

1. **Never modify any installed HornLab, Boundary Lab, BEAT or Julia file.** If one looks broken,
   write it into `NOTES_FOR_SENIOR.md` and stop that line of work.
2. **Never write a BEM solver, FEM solver, mesher, gmsh writer, Green's function, or plotting
   library.** All five exist in the stack. If you are writing one, you are off plan.
3. **Never invent a parameter name, config key, tag number, or unit.** They come from the mesher's
   and solver's own schemas, reproduced in `01_CONTRACTS.md`. Missing one = contract gap:
   `NOTES_FOR_SENIOR.md`, then stop.
4. **Never change a frozen contract.** `01_CONTRACTS.md` is frozen.
5. **Only create or edit files your task file says you own.** Read anything; write only your own.
6. **Paste real terminal output.** Not a summary. A checkpoint without pasted bytes is not done.
7. **Never loosen a tolerance, skip a test, add `pytest.mark.skip`, or widen an assertion to make
   something pass.** A reported failure is useful; a weakened passing test is a trap.
8. **Blocked twice on the same error: stop.** Append a dated block to `NOTES_FOR_SENIOR.md` and
   report. Do not improvise an architecture.

File you need but do not own? Do not edit it. Append the exact change needed to
`NOTES_FOR_SENIOR.md` (append-only for everyone) and continue your own task.

---

## The three silent killers

BEM does not crash when wrong — it returns smooth, plausible, confident, wrong answers.

| Killer | Guard |
|---|---|
| **Wrong `mesh_scale`** — mesher writes **metres**; the beat README's `0.001` is for its mm example | `SolveConfig(mesh_scale=1.0)`; `mesh/build.py` asserts bbox is 0.1–1 m |
| **Quadrants vs symmetry flag disagree** | Both derive from one source and are tested together |
| **DI from cuts labeled as real DI** | `MetricSet.di_source` = `"balloon"` or `"cuts_estimate"`; no checkpoint passes on `cuts_estimate` |

---

## Wave plan — and what "parallel" means here

```
WAVE 0   02 env -> 03 scaffold                               serial, one agent     (CP-0, CP-1)
WAVE 1   04 design+mesh | 05 solve | 06 metrics | 07 dataset  four agents, parallel (CP-2..CP-5)
WAVE 2   08 pipeline                                          one agent             (CP-6, CP-7 entry)
WAVE 3   09 checkpoints                                       senior, verify only   (CP-7 physics gate)
```

- A wave starts only after the previous wave's checkpoints pass with **pasted terminal output**.
- Wave 1's four tasks have zero file overlap and zero import dependency; they meet in Wave 2
  through the dataclasses in `01_CONTRACTS.md`. Dispatch them as parallel background agents.
- **Parallelism means writing code in parallel, not solving in parallel. One GPU, one BEM solve
  at a time.** No agent adds concurrent solves. `search/evaluate.py` stays a pure function so a
  second GPU later is a one-line change.
- Dispatch prompts come **verbatim** from `docs/plan/00_ORCHESTRATOR.md`. Do not paraphrase them;
  they carry the hard rules.
- An orchestrator reads `docs/plan/00_ORCHESTRATOR.md` first, always, and dispatches the rest
  per the wave plan and file-ownership table there.

### Checkpoint map (from `docs/plan/09_CHECKPOINTS.md`)

| CP | Task | Gates |
|---|---|---|
| CP-0 | 02 | Stack installed, a mesh solved, seven measurements, six capability answers |
| CP-1 | 03 | Skeleton, `types.py` frozen, configs load, `doctor` green |
| CP-2 | 04 | Meshes build in metres; quarter really is a quarter; `f_max^2` scaling |
| CP-3 | 05 | Real solve returns valid `Response`; symmetry < 0.1 dB; warm worker works |
| CP-4 | 06 | Every metric matches closed form; cardioid reads 180.0 and 4.771 |
| CP-5 | 07 | Dataset survives a crash; a record is sufficient to retrain without the run |
| CP-6 | 08 | End to end: selftest, cross-check, run, search, report |
| CP-7 | senior | The physics gate — closed forms, two independent solvers, symmetry, published behavior |

**If the search does not beat the seed, that is a result, not a failure.** The plan fails only if
the machinery does not run or the numbers are not honest.

---

## File ownership (summary)

Full table: `docs/plan/00_ORCHESTRATOR.md`. Create and edit only your own paths (by task):

- `TOOLCHAIN.md` → 02 · `pyproject.toml`, `.gitignore`, `README.md`, `types.py`, `constants.py`,
  `config.py`, `cli.py`, `tests/conftest.py`, `test_config.py`, `examples/*.yaml` → 03
- `hornlab_search/design/**`, `mesh/**` → 04 · `solve/**` → 05
- `metrics/**`, `targets/**` → 06 · `dataset/**` → 07
- `objective/**`, `search/**`, `report/**`, `cli.py` (Wave 2) → 08
- `NOTES_FOR_SENIOR.md` → everyone, **append only**
- `docs/CONTINUITY.md`, `docs/ISSUES.md` → everyone, on every push
- `docs/plan/**` → **frozen, nobody edits** · `CLAUDE.md`, `CONTRIBUTING.md`, `.github/**`, `AGENTS.md` → orchestrator

---

## Push rule (forever)

**Every commit that is pushed updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in that same
commit.** CONTINUITY gets a new dated entry at the top (newest first) with its status block
refreshed; ISSUES mirrors open GitHub issues (ID, title, status, owner, plan reference).
A push that does not touch both is wrong.

Branches: `task/<NN>-<slug>`, fixes `fix/<slug>`. Conventional commits with subpackage scope.
PRs into `main` only, with complete unedited checkpoint output pasted in the body.

---

## Tests

- Offline `pytest` tests run in CI (Python 3.12). Tests needing a real solver/GPU/mesher are
  marked in `tests/conftest.py`, deselected in CI, run locally, and pasted into PRs.
- Analytic expectations (cardioid = 180.0°, dipole/cardio DI = 4.771 dB) are written down in
  advance. Failing one is information; do not round it away.

---

## Agent routing (opencode, this repo)

Configured in `.opencode/oh-my-opencode-slim.json` (preset `fm-cloud`):

- **Orchestrator + designer**: `ollama-cloud/glm-5.3-flash`
- **fixer / explorer / librarian / council**: `deepseek/deepseek-flash` (DeepSeek V4.1 Flash —
  the live DeepSeek API's flash tier; the older `deepseek-v4-flash` ID appears in public model
  registries but is no longer served by the live DeepSeek or ollama-cloud APIs), falling back to
  `ollama-cloud/deepseek-v4.1-flash` if deepseek is rate-limited or out of tokens
- **oracle**: `ollama-cloud/glm-5.3` on variant `high`
- **Background agents**: up to 3 concurrent on deepseek and 3 on ollama-cloud (up to 6 total)
- **Council critics** (global config, all live-verified): `nemotron-3-super`, `minimax-m3`,
  `kimi-k3` — all on ollama-cloud, run in parallel

Even with 6 background agents, the same rule binds: **one GPU solve at a time.**
## GPU / Julia hygiene (measured 2026-10-12; applies to every agent)

`hornlab_beat_bem` runs solves in a **persistent Julia host** (`HORNLAB_BEAT_PERSISTENT_HOST=1`, idle
timeout 1800 s). Each host holds ~1 GB of VRAM (CUDA context) plus its memory pool. Measured on the
8 GB RTX 4060: `shutdown_workers()` does **not** reliably end the host, so hosts from earlier
processes pile up, and a later solve then crashes with `Warm BEAT Engine solver exited with code
1 / 4294967295`, or OOMs at a dof count that fits fine alone. Several "OOM" numbers were this, not
the real ceiling.

Rules:
1. **Before any GPU measurement, benchmark, or checkpoint run**, list and clear stale hosts, and confirm
   VRAM is near idle (the desktop alone uses ~0.3-0.5 GB):
   `Get-Process julia` then `taskkill /F /IM julia.exe`, then `nvidia-smi --query-gpu=memory.used --format=csv`.
   Only Julia processes this project started may be killed. On a shared machine, check the
   command line first.
2. **One measurement per fresh process, with Julia cleared between jobs.** Never compare VRAM or
   timings across solves of different meshes inside one warm worker (the pool keeps growing).
3. **Record the baseline** (`memory.used` before the solve) next to every peak-VRAM number.
4. **Never run two GPU jobs at once**, and don't run provisioning while measuring.
5. **Poll `nvidia-smi` from a separate process or thread.** A Python-side poll that reads 0 is a bug in
   the probe, not a result.
6. Every run script ends by clearing its workers. Task 05 (`solve/worker.py`) must verify the host
   really exits (check the process list) and test it. `detach_workers()` leaving a host warm is
   intended inside a search; it is not acceptable at the end of a measurement or checkpoint.
7. A solver crash or OOM is only a finding once it reproduces from a clean state (rule 1).
