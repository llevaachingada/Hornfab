# ISSUES

Mirror of the open GitHub issues. ID, title, status, owner, plan reference.
Updated in the same commit as `docs/CONTINUITY.md` on every push.

GitHub issues are **not created yet** (blocked on `gh auth login`; bodies are drafted in `.github/issues/`). Statuses below track local progress.

| ID | Title | Status | Owner | Plan ref |
|---|---|---|---|---|
| — | Wave 0: finish CP-0 measurements (M2–M5) on an exclusive GPU | **done** | 02 | `docs/plan/02_TASK_ENV.md` |
| — | Wave 0: create GitHub repo, labels, and Wave 1 issues | blocked (`gh auth login`) | 03 | `docs/HANDOFF.md` |
| #04 (planned) | design + mesh | **done locally, CP-2 green** | 04 | `docs/plan/04_TASK_DESIGN_MESH.md` |
| #05 (planned) | solve | **done locally, CP-3 green** | 05 | `docs/plan/05_TASK_SOLVE.md` |
| #06 (planned) | metrics (cardioid threshold −6.0206 dB, not −6.0) | **done locally, CP-4 green (78 tests); awaiting senior review of 3 conventions** | 06 | `docs/plan/06_TASK_METRICS.md` |
| #07 (planned) | dataset | **done locally, CP-5 green (64 tests)** | 07 | `docs/plan/07_TASK_DATASET.md` |
| #08 (planned) | pipeline (wave-2, blocked by 04–07) | **unblocked, next** | 08 | `docs/plan/08_TASK_PIPELINE.md` |
| #09 (planned) | senior checkpoints (senior-review, blocked by 08) | planned | 09 | `docs/plan/09_CHECKPOINTS.md` |

## Question issues (planned)

| Title | Status |
|---|---|
| Impedance/admittance BCs: available on bempp only, not beat — confirm the intended tool | planned |
| `surface_traces` ordering/size for phase-2 surrogates | planned |
| Point-grid public-API access (`build_point_grid`, phi-major) | planned |
| Driver excitation definition on tag `SD1D1001` (single unit normal-acceleration source) | planned |
| Final package name (`hornlab-search`) | planned |

| — | Decision: baseline seed horn too large for the dof caps at 10 kHz screen | **resolved provisionally: band_hi capped per example (CONTINUITY 01:00); user may override** | orchestrator | `docs/CONTINUITY.md` |
