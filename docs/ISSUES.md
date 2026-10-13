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
| #13 | hardening-review: Stage A surrogate gate-integrity and real-data traps | **open** (circle-back; fix before/with CP-8d; do not weaken gate thresholds) | phase-2 (cloud) | `docs/plan/11_PHASE2_SURROGATE.md` §4 |

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) — see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

Local-only, added 2026-10-13 (local GPU box, data digest): `osse_baseline` bound-pinning follow-up — the best designs sit at the LOWER bound of `n` (2.0; top-6 6/6) and 5/6 at `q` lo (0.9), while `a_deg`/`exponent` are interior. The mesher only needs `n > 0`, `q > 0` while `s != 0`, so a future widening of `n`/`q` is indicated (CP-8b handled `a_deg`/`exponent` only). Evidence: `docs/evidence/CP-8c_data_summary.md`.

Local-only, added 2026-10-13 (local GPU box): CP-8 evidence lives in `docs/evidence/` — verbatim checkpoint output (`CP-8a.md`, `CP-8b.md`, `CP-8c_*.md`), live monitor logs (`logs/`), and `manifest.sha256` (SHA-256 + size of every raw artifact). Raw `dataset/`, `runs/`, `cache/` stay local and gitignored by design (dataset already 180.6 MB at 1128 records; CP-5 projects 0.78-1.4 GB at 10k) — verify against the manifest instead of committing blobs; use a data branch/release asset to move raw data.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): CP-8a **PASS** (480 offline + 18 GPU-marked tests, doctor 10/10, outputs pasted in CONTINUITY 2026-10-13); CP-8b **PASS** (`a_deg` lo 25→5, `exponent` lo 2→1 in `search_smoke`/`osse_baseline`, rerun no longer pinned, report table pasted); CP-8c (multi-family dataset) and CP-8d (train/gate/propose, ≥ 500 held-out) pending user go-ahead on GPU hours.

CP-9a..d (cloud GPU pod proof, cap study, campaign, train/gate; see `docs/CLOUD_GPU_REPORT.md` section 6): proposed, awaiting user decisions on provider and spend cap; no GitHub issue yet.
