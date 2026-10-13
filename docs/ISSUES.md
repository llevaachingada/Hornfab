# ISSUES

Mirror of the GitHub issues at https://github.com/llevaachingada/Hornfab/issues. ID, title, status, owner, plan reference.
Updated in the same commit as `docs/CONTINUITY.md` on every push. Last synced 2026-10-13 (cloud session).

| ID | Title | Status | Owner | Plan ref |
|---|---|---|---|---|
| #1 | [04] Design space and mesh | closed, CP-2 green | 04 | `docs/plan/04_TASK_DESIGN_MESH.md` |
| #2 | [05] Solve backends and warm worker | closed, CP-3 green | 05 | `docs/plan/05_TASK_SOLVE.md` |
| #3 | [06] Metrics and targets | closed, CP-4 green (3 conventions ruled by senior) | 06 | `docs/plan/06_TASK_METRICS.md` |
| #4 | [07] Dataset record and store | closed, CP-5 green | 07 | `docs/plan/07_TASK_DATASET.md` |
| #5 | [08] Objective, search, report, CLI | closed, CP-6 green (5 items ruled by senior) | 08 | `docs/plan/08_TASK_PIPELINE.md` |
| #6 | [09] Physics checkpoints CP-7a to CP-7f | **closed, CP-7 green** (noise floor 0.039 dB) | 09 | `docs/plan/09_CHECKPOINTS.md` |
| #7 | [Q] Collin: is a Robin/admittance BC planned for BEAT? | closed (answered: bempp-only, later phase) | user | `docs/plan/02_TASK_ENV.md` C3 |
| #8 | [Q] Collin: surface_traces ordering and bempp field recovery | closed (answered by test) | user | `docs/plan/02_TASK_ENV.md` C2b |
| #9 | [Q] Collin: can build_point_grid be public API? | closed (use privately, keep pin + guard test) | user | `docs/plan/02_TASK_ENV.md` C4 |
| #10 | [Q] Collin: confirm BEAT driver excitation on tag 2 | closed (confirmed tag 2 / unit-acceleration) | user | `docs/plan/02_TASK_ENV.md` C5 |
| #11 | [Q] Collin: OK with the hornlab-search name? | closed (keep until objection) | user | `docs/plan/README.md` |

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) — see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): all pending; no GitHub issue created yet.

CP-9a..d (cloud GPU pod proof, cap study, campaign, train/gate; see `docs/CLOUD_GPU_REPORT.md` section 6): proposed, awaiting user decisions on provider and spend cap; no GitHub issue yet.
