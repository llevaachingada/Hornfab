# hornlab-search

Objective-driven horn-loudspeaker geometry search. State a target — coverage angle, band, ripple,
throat size, a room — and `hornlab-search` generates candidate geometry, solves each candidate with
GPU boundary-element acoustics, scores it, and iterates (CMA-ES).

It is a **search layer** over Collin's HornLab packages, not a solver:

| Package | Job |
|---|---|
| `hornlab_mesher` | geometry + gmsh meshing (OSSE, R-OSSE, ICW, FREEFORM) |
| `hornlab_beat_bem` | GPU BEM (CUDA) |
| `hornlab_bempp_bem` | CPU BEM — the independent cross-check |
| `hornlab_plots` | report figures |

We never write a solver, mesher, gmsh writer, Green's function, or plotting library, and never
modify installed HornLab / Boundary Lab / BEAT / Julia files. License: **AGPL-3.0-or-later**.

## Install

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,crosscheck]"
```

Requires Python `>=3.11,<3.14`, a recent NVIDIA driver (the CUDA runtime is provisioned
automatically), and Julia 1.12 via juliaup. See `TOOLCHAIN.md` for the pinned dependency SHAs and
measured machine numbers.

## Commands

```powershell
.\.venv\Scripts\hornlab-search.exe doctor     # environment self-check (exit 0 = healthy)
.\.venv\Scripts\hornlab-search.exe version    # print the version
```

`run` / `search` / `verify` / `report` / `selftest` arrive in Wave 2.

## The one artifact to back up

`dataset/` is gitignored but precious: it is the only artifact here that costs GPU-hours to
regenerate, and it is the entire prerequisite for phase 2. **Back up `dataset/`.**

## Docs

- `docs/plan/` — the frozen plan and contracts. Start at `docs/plan/00_ORCHESTRATOR.md`.
- `docs/CONTINUITY.md` — current wave, last checkpoint, next step, measured numbers.
- `docs/ISSUES.md` — mirror of the open GitHub issues.
