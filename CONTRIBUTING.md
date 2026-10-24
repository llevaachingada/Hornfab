# Contributing to hornlab-search

Read `CLAUDE.md` first, then `docs/CONTINUITY.md`. The plan in `docs/plan/` is the spec;
`docs/plan/01_CONTRACTS.md` is **frozen**.

## Workflow

- **One branch per task**, named `task/<NN>-<slug>`, e.g. `task/04-design-mesh`, `task/05-solve`,
  `task/06-metrics`, `task/07-dataset`, `task/08-pipeline`. Bug fixes: `fix/<slug>`.
- **Conventional commits**: `feat(solve): ...`, `fix(mesh): ...`, `test(metrics): ...`,
  `docs: ...`, `chore: ...`, `ci: ...`. Scope = subpackage name.
- **PRs into `main`** only. Fill in `.github/pull_request_template.md`.
- **Checkpoint output pasted in the PR body**: complete and unedited terminal output of every
  checkpoint command your task file lists. A summary is not a checkpoint.
- **Every push updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit.** No exceptions.
- CI runs offline tests only (tests needing a real solver/GPU are marked and deselected). Solver
  checkpoints are run on the real machine and pasted.

## The 8 hard rules (verbatim from `docs/plan/00_ORCHESTRATOR.md`)

> **Owner amendment 2026-10-24 to rule 1:** never hand-edit the installed copies in `.venv`; changes to Magnus's packages (Python or Julia) are allowed through our pinned forks, following `docs/FORKS.md` (branch, commit, install by SHA, pin in `pyproject.toml` + `TOOLCHAIN.md`, validate before data counts). Rule 2 still means no new solver/mesher from scratch.

1. **Never modify any installed HornLab, Boundary Lab, BEAT or Julia file.** If one looks broken, write it into `NOTES_FOR_SENIOR.md` and stop that line of work.
2. **Never write a BEM solver, FEM solver, mesher, gmsh writer, Green's function, or plotting library.** All five exist in the stack. If you are writing one, you are off plan.
3. **Never invent a parameter name, a config key, a tag number, or a unit.** They come from the mesher's and solver's own schemas, reproduced in `01_CONTRACTS.md`. If you need one that is not there, it is a contract gap: `NOTES_FOR_SENIOR.md`, then stop.
4. **Never change a frozen contract.** `01_CONTRACTS.md` is frozen.
5. **Only create or edit files your task file says you own.**
6. **Paste real terminal output.** Not a summary. A checkpoint without pasted bytes is not done.
7. **Never loosen a tolerance, skip a test, add `pytest.mark.skip`, or widen an assertion to make something pass.** A reported failure is useful. A weakened passing test is a trap that costs days.
8. **Blocked twice on the same error: stop.** Append a dated block to `NOTES_FOR_SENIOR.md` and report. Do not improvise an architecture.

