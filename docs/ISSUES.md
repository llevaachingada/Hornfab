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
| #13 | hardening-review: Stage A surrogate gate-integrity and real-data traps | **open — fixes IMPLEMENTED on the branch** (verdict persistence + propose refusal w/ `--allow-unvalidated`, config freeze, holdout dedup, `round_report` NaN convention, NSGA NaN guard, atomic writes, meta prints; full offline suite 488 PASS; awaiting cloud review of the diff) | phase-2 (cloud) | `docs/plan/11_PHASE2_SURROGATE.md` §4 |

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) — see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

Local-only, added 2026-10-13 (local GPU box, data digest): `osse_baseline` bound-pinning follow-up — **corrected per senior review** — the best designs sit at the LOWER bound of `n` (2.0; top-6 6/6 — the strong signal), while `q` is attracted to its lower bound (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but is top-6 0/6 (an earlier "5/6" here was the in-flight 13:40 snapshot, not final data); `a_deg`/`exponent` are interior. The mesher only needs `n > 0`, `q > 0` while `s != 0`, so a future widening of `n`/`q` is indicated (CP-8b handled `a_deg`/`exponent` only). Evidence: `docs/evidence/CP-8c_data_summary.md`.

Local-only, added 2026-10-13 (local GPU box): CP-8 evidence lives in `docs/evidence/` — verbatim checkpoint output (`CP-8a.md`, `CP-8b.md`, `CP-8c_*.md`), live monitor logs (`logs/`), and `manifest.sha256` (SHA-256 + size of the metadata-layer artifacts (run books/ndjson/store JSONLs; label .npz covered by dataset verify, not bit-identity)). Raw `dataset/`, `runs/`, `cache/` stay local and gitignored by design (dataset already 180.6 MB at 1128 records; CP-5 projects 0.78-1.4 GB at 10k) — verify against the manifest instead of committing blobs; use a data branch/release asset to move raw data.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): CP-8a PASS (480 offline + 18 GPU-marked tests, doctor 10/10, outputs pasted); CP-8b PASS (bounds widened a_deg 25->5 / exponent 2->1, rerun no longer pinned); CP-8c CLOSED - PARTIAL on the literal criterion, verify OK: four runs done - osse_baseline 1500 (best J 6.106 vs seed 22.592, -73%), icw_termination 800 (12.201 vs 55.736, -78%), freeform_hv 722/800 on cma: tolfun (30.543 vs 33.309, -8.3%, low-diversity plateau, 3 searchable keys), throat_adapter 400/400 with ZERO failures (5.983 vs 9.159, -35%); final dataset 3556 records / 8 shards / 587.2 MB, dataset verify OK (0 bad, 0 bad arrays); families OSSE 2034 + ICW 800 + FREEFORM 722 = 3 of 4 (R-OSSE has no example config; the literal all-four-families criterion is unsatisfiable - amended criterion in evidence). Campaign wall ~14.9 h, GPU solve 13.0 h. CP-8d next (indicative): OSSE pool kept 1501 of 1634 -> held-out 225 < 500 -> expect GATES REFUSED (indicative only); propose runs with --allow-unvalidated. **CP-8d OUTCOME (2026-10-14 ~01:10 local): FAILED — GATES FAILED twice** (epochs 300: topk 5/20 + bw_mae 2.110 fail; epochs 600: 5/6 gates pass incl. Spearman 0.9861 / topk 15 / bw 1.704 / di 0.232 / inv 0.952, but monotonic_flips 1 (needs 0)); held-out 285 < 500; model NOT used (propose/round not run); hard rule 8 stop + NOTES_FOR_SENIOR `2026-10-14 cp-8d` block (questions: approve ~10.2 h OSSE top-up to clear the 500 floor; classify monotonic_flips=1). Tables: `docs/evidence/CP-8d.md`. **Flip diagnosis (addendum)**: seed-stable 2-4 % flip rate (seeds 0-5: flips 1/1/1/2/2/2 of 50); three causes — invalid-transition degeneracy, genuine 1-3.7 J undulation on fully-valid lines, and flat-tolerance wiggle sensitivity (tol 0.021-0.023 J); marginal, not a hard defect; NOTES cp-8d ADDENDUM wants owner rulings on sweep-tolerance semantics / invalid-crossing category (thresholds untouched).

Local-only, added 2026-10-13 (local GPU box, icw run): (a) ICW mesher warning "outer wall self-intersects / normal flip near azimuth row 0" — 24 warning LINES, all timestamped 17:06:25, plausibly ONE design of 800 (per-design attribution not recorded); zero new after 17:06; rows still validate and the acoustic (inner) surface is unaffected — caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. (b) ICW bound-pinning follow-up: best designs fully pinned at the `hold_end` LOWER bound (0.55, top-6 6/6) and 4/6 near `kappa0` lo = 0.0 (median 0.0016); candidate `hold_end` widening subject to the repo's `hold_start < hold_end` rule + mesher validation. (c) OSSE bound-pinning follow-up from run 1 — **corrected per senior review**: `n` fully pinned at lo 2.0 (top-6 6/6; the strong signal); `q` strongly attracted to lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but top-6 0/6 (an earlier "5/6" was a stale in-flight snapshot); mesher needs only `n>0, q>0` while `s≠0`. Both (b)/(c) recorded, NOT changed mid-campaign.

Local-only, added 2026-10-13 (senior read-only review of CP-8c/CP-8d readiness, glm-5.3 oracle, branch claude/wave-3-implementation-review-2dk4qe):

**(a) CP-8c yields THREE families, not four** — `examples/throat_adapter.yaml` is `family: OSSE`,
so after run 4 the store holds OSSE+ICW+FREEFORM and R-OSSE stays 0. HANDOFF_LOCAL §5's pass
criterion ("all four families present") is unsatisfiable as planned, and `stats()`'s family
warning (fires only when one family >80%) will never flag a MISSING family (OSSE ≈56% after
run 4). Fix: re-scope the criterion to "OSSE+ICW+FREEFORM present; R-OSSE deliberately absent
(no example config)"; add `missing_families` to `dataset stats` (store.py:441-446, 658).

**(b) CP-8d misreading guards (14-item list in the review)** — (1) CLI must distinguish
"GATES REFUSED (indicative only): held-out 225 < 500" from "GATES FAILED" (cli.py:675 vs
gates.py:115); (2) `round_report`'s `random_true_J` = CMA gen-0 samples, not random, and J=1000
penalty rows inflate medians — pass solved rows only and print the baseline provenance
(ismo.py:56-72); (3) print exploit vs explore medians separately; (4) print the proposals'
parameter spread (the 30 exploits are near-clones of one basin); (5) freeze `pred_J` from
proposals.json and record bundle/config_sha/store count at train; (6) write `ismo_round1.json`
into a run dir and paste it into a new `docs/evidence/CP-8d.md`. Items overlapping #13
(skipped-count printing, verdict persistence, dedupe-by-hash before the holdout split) LANDED
in commit e0b9b61 — none of CP-8d's numbers are quoted before that.

**(c) Data-pipeline integrity at 10k — IMPLEMENTED (commit 11304f6; full offline suite 498 PASS)** —
`verify_store` now checks metric array shapes vs each record's own `solve.freqs_hz` (reported as
`bad_arrays`; `dataset verify` exits 1 on `bad` OR `bad_arrays`); `dataset stats` gained
`n_duplicate_designs` + a `missing families` line in `stats_report` (R-OSSE expected); `search
--resume` compares `run.json["config_sha"]` and REFUSES on mismatch unless `--allow-config-change`;
`surrogate train` splits `GATES FAILED: <names>` from `GATES REFUSED (indicative only): held-out
<X> < 500`; new `surrogate round` subcommand solves proposals through the normal `evaluate` path
into a fresh run dir with its own ndjson and writes atomic `ismo_round1.json` (report + rows +
`random_true_J` provenance + exploit/explore medians + exploit spread + store counts + bundle gate
status + config_sha). `manifest.sha256` README reworded (metadata layer only) and line 3 indent
fixed for `sha256sum -c`.

**(d) Evidence corrections** — CP-8c_osse_baseline.md "5/6 near q lo" contradicted its own table
(fixed: top-6 0/0, median 0.9033 — stale snapshot claim); the 13:11 snapshot's "seed J 22.07" was
the smoke seed (fixed: 22.592); ICW warning "~a few % of designs" unsupported (fixed: 24 lines,
one timestamp, plausibly one design of 800); `data_summary.json` `generated_local` lacks a
timezone (add `generated_utc`).

CP-9a..d (cloud GPU pod proof, cap study, campaign, train/gate; see `docs/CLOUD_GPU_REPORT.md` section 6): proposed, awaiting user decisions on provider and spend cap; no GitHub issue yet.

CP-10a..d (high-frequency options, 12 kHz; see `docs/HIGH_FREQUENCY_OPTIONS.md` section 6): proposed, none run; CP-10d needs the user to approve contacting Collin.

Added 2026-10-14 (cloud): **#13 fixes F1-F6 ready on `ccr-455d2184-yj5zk4` (draft PR #14). Merge into this branch AFTER CP-8c, BEFORE CP-8d.** #13 stays open until then.
**[SUPERSEDED locally, 2026-10-13 ~23:00: the SAME issue-#13 fixes are already on this branch — local commits e0b9b61 (8 items) + 11304f6 (store/CLI follow-ups), full offline suite WITH the mesher: 498 PASS / 0 failures. Do NOT merge PR #14 on top — that would double-apply overlapping changes in `surrogate/**`. Cloud owner: diff e0b9b61+11304f6 against PR #14 and adopt ONE set. CP-8d proceeds on this branch's fixed code either way; `propose` here refuses unvalidated bundles by default with `--allow-unvalidated` for the runbook's indicative round.]**

Added 2026-10-14 ~05:00 UTC (cloud): PR #14 REBUILT on `622776a` — local issue-#13 set (e0b9b61/11304f6) adopted, cloud duplicates dropped; adds FREEFORM sculpt config, FREEFORM training-export fix (dotted keys were NaN), `compare`, DI-provenance guard, NaN refusal, FREEFORM throat radius. Merge, then HANDOFF section 6b. Open, no GitHub issue: FREEFORM full-vs-quarter GPU check + bar ruling; mesher wall-port feature request; HornLab author naming (user to confirm).
