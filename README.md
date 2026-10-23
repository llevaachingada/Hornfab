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

## Status (2026-10-22, pre-beta)

- **Solver verified** on the GPU (2026-10-22): GPU tests 18/18; analytic pulsating sphere within
  0.020 dB; GPU (`beat_cuda`) vs CPU (`bempp_cpu`) cross-check within 0.039 dB.
- **Typologies**: conical, exponential, hyperbolic-exponential (hypex), tractrix and OSSE-meridian
  horns, plus hybrids (H/V, convex blends, monotone perturbations), all built as ordinary FREEFORM
  designs from textbook formulas. Our implementations match the mesher's own FREEFORM evaluator
  within 0.2 mm. Le Cléac'h is **disabled** until a verifiable published construction is available.
- **Briefs** (`examples/briefs/`) fix the driver exit, size envelope, target and weights, so
  typologies are compared on one objective. The first fair screen campaigns are in
  `docs/evidence/TYPOLOGY_SCREEN_2026-10-22.md`. These are coarse rankings only: a
  "family A beats family B" claim needs the two-seed `compare` tier.
- **Dataset**: 6,055 solved or failed records (OSSE, R-OSSE, ICW, FREEFORM), `dataset verify` OK.
  The surrogate (fast-prediction) model is not active: its gates failed on too little data.
- **Beta readiness pass** in progress (`docs/HANDOFF_BETA.md`); results go to
  `docs/evidence/BETA_READINESS.md`.

Known limits: free-standing horn, no baffle, room or enclosure; rigid lossless walls, no air
absorption; rigid uniform-velocity spherical-cap source (no phase plug or compression chamber);
nothing above 5.5 kHz is scored on an 8 GB GPU; 12 log-spaced screen frequencies cannot see narrow
resonances.

## Commands

```powershell
.\.venv\Scripts\hornlab-search.exe doctor     # environment self-check (exit 0 = healthy)
.\.venv\Scripts\hornlab-search.exe families --brief examples\briefs\axi_90x90_1in.yaml
.\.venv\Scripts\hornlab-search.exe campaign --brief <brief> --families <names|group|all> --tier dry-run|screen|compare
.\.venv\Scripts\hornlab-search.exe gpu-clean  # clear this project's Julia / BEAT hosts, print VRAM
```

| Command | Does |
|---|---|
| `doctor`, `version` | environment self-check; version |
| `families` | list typologies and whether each fits a brief |
| `campaign` | run several typologies under one brief and write a leaderboard |
| `run`, `search`, `verify` | evaluate a seed; CMA-ES search; re-solve the top designs at verify fidelity |
| `report`, `compare` | HTML report of a run; how far two solved runs disagree |
| `export-step` | closed STEP solids (mm) for CAD or 3D printing |
| `selftest` | analytic sphere and GPU-vs-CPU cross-check |
| `dataset`, `surrogate` | dataset verify / stats; phase-2 surrogate (inactive) |
| `gpu-clean` | clear stale solver hosts |
| `gui` | local web GUI at http://127.0.0.1:8765: status, campaigns, runs, compare, briefs, launch, 3D view |

Only one GPU job runs at a time: a second GPU command fails fast with `GPU busy: ...`.
New users start at `docs/BETA_QUICKSTART.md`.

## The one artifact to back up

`dataset/` is gitignored but precious: it is the only artifact here that costs GPU-hours to
regenerate, and it is the entire prerequisite for phase 2. **Back up `dataset/`.**

## Docs

- `docs/plan/` — the frozen plan and contracts. Start at `docs/plan/00_ORCHESTRATOR.md`.
- `docs/CONTINUITY.md` — current wave, last checkpoint, next step, measured numbers.
- `docs/ISSUES.md` — mirror of the open GitHub issues.
- `docs/BETA_QUICKSTART.md` — first loop for beta testers; `docs/TYPOLOGY_PLAN.md` — typologies and briefs.
