# AGENTS.md — hornlab-search

## Acoustic knowledge before decisions

Before acoustic, geometry, scoring or optimization decisions, read
[`docs/knowledge/README.md`](docs/knowledge/README.md), the relevant family card and
[`docs/knowledge/FAMILY_LAWS.md`](docs/knowledge/FAMILY_LAWS.md); use `hornlab-acoustic-grounding`.
Never generalize acoustic formulas, targets or heuristics across typologies without checking
applicability; Keele mouth sizing is not a universal limit, and CD scoring is not imposed on
intentionally non-CD horns. New construction/objective priorities: `hornlab-typology-research`.

## Precedence (which instruction wins)

1. Dated **owner amendments in this file** override older plan or handoff text.
2. `docs/plan/00_ORCHESTRATOR.md` and `docs/plan/01_CONTRACTS.md` remain binding contracts;
   `01_CONTRACTS.md` is **frozen**.
3. Historical material (wave plan, ownership tables, old worktree routing) is provenance, not
   routing: see [`docs/history/AGENTS_historical_2026-11.md`](docs/history/AGENTS_historical_2026-11.md).
   Routing = this file + START_HERE + INDEX + ACTIVE_STATE + newest CONTINUITY/ISSUES + priorities.
4. When two sources conflict, the newer dated owner amendment wins; record it in
   `NOTES_FOR_SENIOR.md` instead of improvising a third rule.

## One consolidated checkout (owner amendment 2026-11-12)

Work only in `C:/Users/hunte/Hrns/hornlab-search`; no worktrees or private copies unless the owner
asks. Parallel agents may read the shared tree and edit disjoint files; only the parent integrator
performs git mutations. Old worktree paths in evidence are provenance.

## What this is

`hornlab-search` finds horn geometry by objective: generate, solve with GPU BEM, score, iterate
(CMA-ES/BO), as a search layer over the pinned HornLab packages (`hornlab_mesher`,
`hornlab_beat_bem`, `hornlab_bempp_bem`, `hornlab_plots`). Never write a solver/mesher/gmsh
writer/Green's function/plotting library from scratch, and never hand-edit `.venv`; change Magnus's
packages via the pinned forks (`docs/guides/FORKS.md`, owner amendment 2026-10-24). License
AGPL-3.0-or-later; horn numbers are YAML defaults in `examples/`; always `.venv\Scripts\python.exe`.

## Start here (bounded reading)

1. **`docs/START_HERE.md`** — task → first file. **`docs/ACTIVE_STATE.md`** — current pointer;
   verify with `tools/night_status.py` and `git`, and keep it current in the same commit as any
   queue or priority change.
2. **`docs/CONTINUITY.md`** — first 60–80 lines only (newest first). **`docs/ISSUES.md`** — first
   60–80 lines, then search by ID. **`NOTES_FOR_SENIOR.md`** — last 60 lines, then search.
3. **`docs/plan/01_CONTRACTS.md`** (frozen) and only your own `docs/plan/02`–`08` task file.
4. **`TOOLCHAIN.md`** and **`CONTRIBUTING.md`** — interpreter/SHAs and commit/PR rules.

`docs/START_HERE.md`, `docs/INDEX.md` and `docs/CODE_MAP.md` are lookup surfaces: consult on demand
and grep them; a new doc or module gets an INDEX (and CODE_MAP) line in the same commit. Do not
bulk-read `docs/research/**`, `scratch/**` or the Fable reports. Any document over ~100 KB (or ~600
lines) is grep-only. Stuck: `docs/plan/10_TROUBLESHOOTING.md`, then `NOTES_FOR_SENIOR.md`.

## The 8 hard rules

1. **Never modify an installed HornLab, Boundary Lab, BEAT or Julia file directly.** Owner
   amendment 2026-10-24: **DO** change Magnus's packages (above all for higher-frequency GPU
   solves) via the pinned forks in `docs/guides/FORKS.md`; rule 2 still forbids writing a new
   solver/mesher from scratch. If an installed file looks broken, write it into
   `NOTES_FOR_SENIOR.md` and stop that line.
2. **Never write a BEM/FEM solver, mesher, gmsh writer, Green's function or plotting library.**
3. **Never invent a parameter name, config key, tag number or unit.** They come from the schemas
   in `01_CONTRACTS.md`. Missing one = contract gap: `NOTES_FOR_SENIOR.md`, then stop.
4. **Never change a frozen contract.** `01_CONTRACTS.md` is frozen.
5. **Only create or edit files you own.** Read anything; for another lane's file, append the exact
   change to `NOTES_FOR_SENIOR.md` (append-only for everyone).
6. **Paste real terminal output.** A checkpoint without pasted bytes is not done.
7. **Never loosen a tolerance, skip a test, add `pytest.mark.skip`, or widen an assertion** to make
   something pass. A weakened passing test is a trap.
8. **Blocked twice on the same error: stop.** Append a dated block to `NOTES_FOR_SENIOR.md` and
   report; do not improvise an architecture.

## The three silent killers

BEM returns smooth, plausible, wrong answers instead of crashing.

| Killer | Guard |
|---|---|
| Wrong `mesh_scale` — mesher writes metres; beat's `0.001` is its mm example | `SolveConfig(mesh_scale=1.0)`; `mesh/build.py` asserts bbox 0.02–5.0 m |
| Quadrants vs symmetry flag disagree | Both derive from one source and are tested together |
| DI from cuts labeled as real DI | `MetricSet.di_source` is `"balloon"` or `"cuts_estimate"`; no checkpoint passes on `cuts_estimate` |

## Research grounding (before typology/shape work)

Adding or changing a typology, generator, shape law, mounting, multicell/septa geometry, a
brief-for-a-new-typology, or an objective/directivity term encoding a NEW acoustic priority runs
`hornlab-typology-research` FIRST: primary sources, corrected claims, a validatable construction,
experiential reports — before code; cite an existing dossier if it covers it. Lanes without skills
apply this plus the WP9b 9b.0 standard (`docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md`).
R9 binds: nothing ships under a published name without a verifiable reference; routine
config/GPU/evidence work skips it.

## Push rule (forever)

Every pushed commit updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit: a new
dated CONTINUITY entry at the top (newest first) with a refreshed status block, and ISSUES mirroring
open GitHub issues (ID, title, status, owner, plan reference). A push that does not touch both is
wrong. Logs rotate monthly: pre-current-month entries move verbatim to `docs/history/` with
`docs/history/manifest.json`. Branches `task/<NN>-<slug>` / `fix/<slug>`; conventional commits with
subpackage scope; PRs into `main` only with the complete unedited checkpoint output in the body.

## Tests

Offline `pytest` runs in CI (Python 3.12); solver/GPU/mesher tests are marked in `tests/conftest.py`,
deselected in CI, run locally and pasted into PRs. The `slow` marker is legacy (one test still
carries it; `pyproject.toml` declares it); the standard run deselects it.

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"; $env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider
.venv\Scripts\python.exe -m pytest -m "gpu"   # separate terminal, concurrent
```

Do not use `-n auto` or drop the thread caps (six BLAS pools inflate the suite ~1.8×). After an
interrupted solve, `hornlab-search gpu-clean` before the next measurement. Analytic expectations
(cardioid 180.0°, dipole/cardioid DI 4.771 dB) are written in advance; a failure is information.

## GPU / Julia hygiene (applies to every agent)

Persistent Julia hosts hold ~1 GB VRAM each; stale hosts cause false OOMs and 5–10× slow solves.
**Before any measurement:** `hornlab-search gpu-clean`; confirm VRAM near idle and record the
~0.3–0.5 GB desktop baseline; **never `taskkill /IM julia.exe`** (it leaves the host alive and can
kill another lane). One measurement per fresh process; record the baseline next to every peak;
**never two GPU jobs at once** (one CUDA solve; a CPU-backend search may run beside it); poll
`nvidia-smi` from a separate thread; record `\GPU Process Memory(*)\Shared Usage` (Windows hides
spills); `gpu_lock` defaults to `warn`, so set `HORNLAB_GPU_LOCK=refuse` for nights, measurements
and checkpoints, and never delete `runs/.gpu.lock`. Two-lane identity: `HORNLAB_BEAT_WORKER_DIR`
(`runs\lanes\{gpu,cpu}\workers`) plus `runs\.cpu.lane.lock`; never touch a live-locked lane. Run
scripts clear their workers; a crash/OOM counts only after it reproduces clean (`hornlab-gpu-job`).

## Agent routing and skills

All agents use `opencode-go-max` in `.opencode/oh-my-opencode-slim.json` (mirror
`Hrns/.opencode/oh-my-opencode-slim.json`; keep the preset blocks identical). Background concurrency
is set there; the hard cap here is 3 concurrent writers, and one GPU solve at a time.

Skills (`.claude/skills/`): `hornlab-gpu-job`, `hornlab-night-queue`, `hornlab-evidence`,
`hornlab-shape-check`, `hornlab-search-economy`, `hornlab-render`, `hornlab-acoustic-grounding`,
`hornlab-typology-research`, `hornlab-brief-scoring`, `hornlab-generator-family`, `hornlab-find`.
Umbrella sessions get them through `Hrns/.opencode/opencode.jsonc`; verify with
`opencode debug skill`. If a skill is unavailable, move to the canonical checkout (see
`docs/guides/AGENT_BOOTSTRAP_CONTAINER.md`).

**Current state / versions:** `docs/ACTIVE_STATE.md` + `tools/night_status.py`; a dated handoff is
not routing. Objective versions live in `hornlab_search/objective/versions.py`; never enumerate them
from memory, and never rank J across versions.

**sigma0 rule:** sigma0 and bound width are one measured decision — never ship sigma0 ≥ 0.25 with
>8 free keys or global bounds; run `tools/search_preflight.py`'s sigma sweep before queueing and
pick sigma0 for ≈≥20 % expected in-basin hits.
