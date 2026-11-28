# CLAUDE.md — hornlab-search

Project instructions live in [`AGENTS.md`](AGENTS.md); where this file conflicts, `AGENTS.md` wins.

## Acoustic scope (keep: `tests/agent_bench/cases/case_16.yaml` reads this file)

Before acoustic, geometry, scoring or optimization decisions, read
[`docs/knowledge/README.md`](docs/knowledge/README.md) and the relevant family card; use
`hornlab-acoustic-grounding` and `hornlab-typology-research`. A UI/copy-only change needs no acoustic
review.

## Start here

- Find anything: `docs/START_HERE.md` → `docs/INDEX.md` (docs; search it) and `docs/CODE_MAP.md`
  (modules). Current state: `docs/ACTIVE_STATE.md`, then the newest `docs/CONTINUITY.md` entry —
  never the whole log.
- Interpreter: always `.venv\Scripts\python.exe`, never bare `python`.
- One canonical checkout: `C:/Users/hunte/Hrns/hornlab-search`; no new worktrees unless the owner
  asks; only the parent integrator performs git mutations.

## Push rule

Every pushed commit updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit. Logs rotate
monthly into `docs/history/` (see `docs/history/manifest.json`).

GPU hygiene, the 8 hard rules, tests and file ownership: see `AGENTS.md`.
