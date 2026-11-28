# AGENTS / CLAUDE historical material (moved 2026-11-25)

Historical routing and ownership. Current routing is `AGENTS.md`, `docs/START_HERE.md`,
`docs/INDEX.md`, `docs/ACTIVE_STATE.md`, and the newest `docs/CONTINUITY.md` / `docs/ISSUES.md`
entries. Nothing here is current ownership or a current queue; the invariants under the wave plan
still bind every pass.

## Original wave plan (historical)

The original build sequence — Wave 0 (02 env -> 03 scaffold), Wave 1 (04 design+mesh | 05 solve |
06 metrics | 07 dataset), Wave 2 (08 pipeline), Wave 3 (09 checkpoints) — is preserved in
`docs/plan/00_ORCHESTRATOR.md`. It is historical routing; do not dispatch from it today.

Invariants that still bind every pass:

- A checkpoint passes only with pasted terminal output; a summary is not a checkpoint.
- Parallelism means writing code in parallel, not solving in parallel. One GPU, one BEM solve at a
  time. No agent adds concurrent solves. `search/evaluate.py` stays a pure function so a second GPU
  later is a one-line change.
- Dispatch prompts keep the hard rules. Do not paraphrase them away.
- Only the parent integrator performs git mutations; parallel writers get disjoint file ownership.
- A slice starts only after the previous gate passes on current evidence.
- Senior verifier additionally reads `docs/plan/09_CHECKPOINTS.md` and `12_RESEARCH_BASIS.md` when
  the pass requires it — not on every pass.

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

**If the search does not beat the seed, that is a result, not a failure.** The plan fails only if the
machinery does not run or the numbers are not honest.

## Original file ownership — AGENTS.md table (historical)

Full table: `docs/plan/00_ORCHESTRATOR.md`. The per-task split below describes the original build;
for current work, ownership comes from the task or handoff you were given, and the same rule still
binds: create and edit only files you own, and append needed changes to `NOTES_FOR_SENIOR.md`
instead of touching another lane's files.

- `TOOLCHAIN.md` -> 02 · `pyproject.toml`, `.gitignore`, `README.md`, `types.py`, `constants.py`,
  `config.py`, `cli.py`, `tests/conftest.py`, `test_config.py`, `examples/*.yaml` -> 03
- `hornlab_search/design/**`, `mesh/**` -> 04 · `solve/**` -> 05
- `metrics/**`, `targets/**` -> 06 · `dataset/**` -> 07
- `objective/**`, `search/**`, `report/**`, `cli.py` (Wave 2) -> 08
- `NOTES_FOR_SENIOR.md` -> everyone, append only
- `docs/CONTINUITY.md`, `docs/ISSUES.md` -> everyone, on every push
- `docs/plan/**` -> frozen, nobody edits · `CLAUDE.md`, `CONTRIBUTING.md`, `.github/**`, `AGENTS.md`
  -> orchestrator

## Original CLAUDE wave diagram (historical)

```
WAVE 0   02 env  ->  03 scaffold                               serial, one agent      (CP-0, CP-1)
WAVE 1   04 design+mesh | 05 solve | 06 metrics | 07 dataset    four agents, parallel  (CP-2..CP-5)
WAVE 2   08 pipeline                                            one agent              (CP-6, CP-7)
WAVE 3   09 checkpoints                                         senior, verify only
```

A wave starts only after the previous wave's checkpoints pass. Parallelism = writing code in
parallel. One GPU, one solve at a time. Dispatch prompts: verbatim template in
`docs/plan/00_ORCHESTRATOR.md`.

## Original file ownership — CLAUDE.md table (historical)

Current ownership comes from your task/handoff (`AGENTS.md`). The rule still binds: create and edit
only your assigned paths; read anything.

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
| `hornlab_search/surrogate/**`, `tests/test_surrogate_*.py` | phase 2 (orchestrator) |
| `hornlab_search/objective/**`, `search/**`, `report/**` | 08 |
| `tests/test_design_*.py`, `test_mesh_*.py` | 04 |
| `tests/test_solve_*.py` | 05 |
| `tests/test_metrics_*.py`, `test_targets_*.py` | 06 |
| `tests/test_dataset_*.py` | 07 |
| `tests/test_objective_*.py`, `test_search_*.py`, `test_report_*.py`, `test_end_to_end.py` | 08 |
| `NOTES_FOR_SENIOR.md` | everyone, append only |
| `docs/CONTINUITY.md`, `docs/ISSUES.md` | everyone, on every push |
| `docs/plan/**` | frozen; nobody edits |
| `CLAUDE.md`, `CONTRIBUTING.md`, `.github/**` | orchestrator |

**MEH effort (owner, 2026-10-30):** tasks M1-M10 own the paths in `docs/meh/00_MEH_CONTRACTS.md` C13
(additive to the table above); `docs/meh/**` is orchestrator-owned and frozen for the effort.

**Fable plan (owner delegation, 2026-11-18, R21):** `hornlab_search/geometry/**`,
`tools/analysis/**`, `tools/night_queue/fidelity_pairs.py`, `examples/protected_lanes.yaml` and
`scratch/fable_architecture/**` are owned by the Fable senior lane; the local orchestrator is the
single integrator of `hornfab-all-*` and `main` (cloud work arrives only as PRs into `hornfab-all-*`).
Decisions: `scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md`.

## Log-archival note (2026-11-17, superseded 2026-11-25)

The 2026-11-17 proposal (`docs/AGENT_ORCHESTRATION_REVIEW_2026-11-16.md` §P3) became the approved
monthly rotation on 2026-11-25: entries dated before the current month move verbatim to
`docs/history/`, with `docs/history/manifest.json`. The push rule still appends a new entry to both
live logs.
