# ISSUES

Mirror of the GitHub issues at https://github.com/llevaachingada/Hornfab/issues. ID, title, status, owner, plan reference.
Updated in the same commit as `docs/CONTINUITY.md` on every push. Last synced 2026-10-24 (senior pass + fork policy + local GUI-contrast plan docs; no GitHub issue state changed).

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
| #13 | hardening-review: Stage A surrogate gate-integrity and real-data traps | **open — fixes MERGED to main** (FF to 6d1d5c7 on 2026-10-22 carries e0b9b61 + 11304f6 + cloud reconciliation 152a829 verbatim; oracle pre-merge sign-off; full offline suite 533 PASS at the merged tree; awaiting owner close) | phase-2 (cloud) | `docs/plan/11_PHASE2_SURROGATE.md` §4 |

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) — see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, added 2026-10-24 (GUI contrast/visibility pass, docs-only): the local web GUI's rendered dark-theme state fails WCAG in spots — primary button text 2.07:1 on `--accent`, hairlines 1.36:1, chart micro-labels dim, `wallSection` "filled" legend a no-op (fill ≡ plot bg, dashed start profile ~90 % occluded), 3D horn shadow side merges into the canvas, isobar white contours lost on warm bands, budget-over-limit unflagged, theme-toggle first-click no-op + stale SVG after toggle. Full measured list + six-phase fix plan (tokens, theme boot + `?theme=` capture, charts, wallSection, 3D light-gray horn + lighting/shadows, semantics/tests): `docs/GUI_CONTRAST_PLAN.md` (designer-authored, Oracle-reviewed — all MUST/SHOULD/NICE applied). Owner approved implementation 2026-10-24: Phase 1 (tokens/type tiers) landed + verified (`tests/test_gui.py` 30/30; both dark CSS blocks in sync). No GitHub issue opened.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

Local-only, added 2026-10-13 (local GPU box, data digest): `osse_baseline` bound-pinning follow-up — **corrected per senior review** — the best designs sit at the LOWER bound of `n` (2.0; top-6 6/6 — the strong signal), while `q` is attracted to its lower bound (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but is top-6 0/6 (an earlier "5/6" here was the in-flight 13:40 snapshot, not final data); `a_deg`/`exponent` are interior. The mesher only needs `n > 0`, `q > 0` while `s != 0`, so a future widening of `n`/`q` is indicated (CP-8b handled `a_deg`/`exponent` only). Evidence: `docs/evidence/CP-8c_data_summary.md`.

Local-only, added 2026-10-13 (local GPU box): CP-8 evidence lives in `docs/evidence/` — verbatim checkpoint output (`CP-8a.md`, `CP-8b.md`, `CP-8c_*.md`), live monitor logs (`logs/`), and `manifest.sha256` (SHA-256 + size of the metadata-layer artifacts (run books/ndjson/store JSONLs; label .npz covered by dataset verify, not bit-identity)). Raw `dataset/`, `runs/`, `cache/` stay local and gitignored by design (dataset already 180.6 MB at 1128 records; CP-5 projects 0.78-1.4 GB at 10k) — verify against the manifest instead of committing blobs; use a data branch/release asset to move raw data.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): CP-8a PASS (480 offline + 18 GPU-marked tests, doctor 10/10, outputs pasted); CP-8b PASS (bounds widened a_deg 25->5 / exponent 2->1, rerun no longer pinned); CP-8c CLOSED - PARTIAL on the literal criterion, verify OK: four runs done - osse_baseline 1500 (best J 6.106 vs seed 22.592, -73%), icw_termination 800 (12.201 vs 55.736, -78%), freeform_hv 722/800 on cma: tolfun (30.543 vs 33.309, -8.3%, low-diversity plateau, 3 searchable keys), throat_adapter 400/400 with ZERO failures (5.983 vs 9.159, -35%); final dataset 3556 records / 8 shards / 587.2 MB, dataset verify OK (0 bad, 0 bad arrays); families OSSE 2034 + ICW 800 + FREEFORM 722 = 3 of 4 (R-OSSE has no example config; the literal all-four-families criterion is unsatisfiable - amended criterion in evidence). Campaign wall ~14.9 h, GPU solve 13.0 h. CP-8d next (indicative): OSSE pool kept 1501 of 1634 -> held-out 225 < 500 -> expect GATES REFUSED (indicative only); propose runs with --allow-unvalidated. **CP-8d OUTCOME (2026-10-14 ~01:10 local): FAILED — GATES FAILED twice** (epochs 300: topk 5/20 + bw_mae 2.110 fail; epochs 600: 5/6 gates pass incl. Spearman 0.9861 / topk 15 / bw 1.704 / di 0.232 / inv 0.952, but monotonic_flips 1 (needs 0)); held-out 285 < 500; model NOT used (propose/round not run); hard rule 8 stop + NOTES_FOR_SENIOR `2026-10-14 cp-8d` block (questions: approve ~10.2 h OSSE top-up to clear the 500 floor; classify monotonic_flips=1). Tables: `docs/evidence/CP-8d.md`. **Flip diagnosis (addendum)**: seed-stable 2-4 % flip rate (seeds 0-5: flips 1/1/1/2/2/2 of 50); three causes — invalid-transition degeneracy, genuine 1-3.7 J undulation on fully-valid lines, and flat-tolerance wiggle sensitivity (tol 0.021-0.023 J); marginal, not a hard defect; NOTES cp-8d ADDENDUM wants owner rulings on sweep-tolerance semantics / invalid-crossing category (thresholds untouched).

Local-only, added 2026-10-13 (local GPU box, icw run): (a) ICW mesher warning "outer wall self-intersects / normal flip near azimuth row 0" — 24 warning LINES, all timestamped 17:06:25, plausibly ONE design of 800 (per-design attribution not recorded); zero new after 17:06; rows still validate and the acoustic (inner) surface is unaffected — caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. (b) ICW bound-pinning follow-up: best designs fully pinned at the `hold_end` LOWER bound (0.55, top-6 6/6) and 4/6 near `kappa0` lo = 0.0 (median 0.0016); candidate `hold_end` widening subject to the repo's `hold_start < hold_end` rule + mesher validation. (c) OSSE bound-pinning follow-up from run 1 — **corrected per senior review**: `n` fully pinned at lo 2.0 (top-6 6/6; the strong signal); `q` strongly attracted to lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but top-6 0/6 (an earlier "5/6" was a stale in-flight snapshot); mesher needs only `n>0, q>0` while `s≠0`. Both (b)/(c) recorded, NOT changed mid-campaign.

Local-only, added 2026-10-22 (local merge lane, glm-5.3 oracle pre-merge review): follow-ups recorded, none blocking the merge —
(a) `cli.py::_cmd_compare` would raise an uncaught `IndexError` (`ma.freqs_hz[0]`) on the unrealistic empty-frequency-set edge (cosmetic traceback risk only);
(b) the `exponent` alias resolves to the FIRST superellipse station only — pre-existing design-layer semantics; document in config-template comments before any future multi-station FREEFORM config;
(c) `docs/BOUNDARY_LAB_*` + `docs/research/boundary_lab_0.5/` are PROPOSED research awaiting user approval — do not treat as accepted backlog.

Local-only, added 2026-10-22 (local merge lane, user request): GPU-run summary layer committed at `docs/evidence/runs/` — for each of the 7 local `beat_cuda` run dirs (seed screen d627d9, resume smoke 7e6e5b, CP-8b smoke 9e5a5c, CP-8c runs 1-4 ca15be/6bdcbd/ff569c/852be3), the summarized metadata+log layer (run.json, config.yaml, best.json, search.ndjson, cma/*, verify; 108 files, ~16.6 MB) is now IN GIT (previously only in gitignored `runs/`), with index README + `runs/manifest.sha256`. Raw `designs/` blobs, `dataset/`, `cache/` remain gitignored by design; this is an approved exception to the evidence-README "never the data itself" rule (noted in `docs/evidence/runs/README.md`).

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

Added 2026-10-21 (cloud): Boundary Lab 0.5.0 integration PROPOSED (`docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`; research `docs/BOUNDARY_LAB_0.5_RESEARCH.md`). No GitHub issue yet; open decisions: phase order A->B->C, ownership rows, BL env on the GPU box, contacting JW Sound / HornLab author.

Added 2026-10-22 (cloud): senior architecture report `docs/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md` (Boundary Lab: sidechain, plugin parked; priority and to-do list). On `main` (`2311f92` + this commit).

Local-only, added 2026-10-22 (local GPU box, HANDOFF 6b): FREEFORM quarter-vs-full symmetry check PASSED (max 0.0043 dB, beamwidth 0.051 deg; bar 0.1 dB / 1 deg, not frozen - owner may freeze it); `freeform_sculpt` 60-eval search 0 failures, J 30.945 -> 24.213. Follow-ups (non-blocking): (1) `compare` header prints `quadrants None` for both runs although they solved 451 vs 1636 dofs (reads the wrong field; cosmetic); (2) dry-run throughput estimate 2 s/candidate vs measured 6.7 s for `freeform_sculpt` (TOOLCHAIN M3 extrapolation under-predicts; affects budget planning only); (3) watch `profileH.mouthAngleDeg` (2/6 at hi 70) and `profileV.points.3.1` (2/6 at lo 108) on any longer sculpt run before widening. CP-8d must not be re-run before the OSSE top-up (CONTINUITY Next action corrected). Evidence `docs/evidence/HANDOFF_6b.md`.

Local-only, added 2026-10-22 ~11:40 (local GPU box): follow-up (1) `compare` quadrants label FIXED (regression test). New `export-step` CLI (senior report s3 item 4) DONE. Sculpt budget 400: J 30.945 -> 16.789, **3 wall anchors PINNED** (`profileH/V.points.3.1` at lo, `profileV.points.4.1` at hi) - the disjoint per-anchor radius boxes now bind; options for the owner: widen/overlap the boxes with a mesher monotonicity check, or reparametrise as positive increments. Bound-limited families awaiting a widening decision: OSSE `n` (6/6 lo), ICW `hold_end` (6/6 lo) + `kappa0` (4/6 lo), throat_adapter `throat_ext_angle_deg`/`k` (6/6 hi) + `a0_deg` (6/6 lo), FREEFORM sculpt anchors above. No widening done (user OK required).

Added 2026-10-22 PM (cloud): Boundary Lab learnings implemented (`docs/BL_LEARNINGS_IMPLEMENTATION.md`): pre-solve topology + symmetry-domain checks, `solve/phasor.py`, runtime provenance, report-only SPDI / beam shape. 

**NEXT DEVELOPMENT ROUND, TOP PRIORITY (user decision 2026-10-22): read `docs/NEXT_DEV_PRIORITIES.md`.**
- [ ] **P1 Fused / direct CUDA Burton-Miller assembly** in the exterior driver (post-beta; Magnus's OK or a pinned fork). Fused path is CPU/Metal only (`hornlab_beat_bem/julia/BeatEngineDriver.jl` ~l.1215); the CUDA single-matrix assembler `assemble_burton_miller_neumann_system_cuda` (`julia/src/BeatEngineCudaBurtonMiller.jl:350`) is called only by `runtests.jl`. Engine work, not a flag flip. Expected: 8 GB ceiling ~9k -> ~20k quarter dofs (~12.6 kHz at epw 6 on the large OSSE seed) [inferred]. Validate with selftest --analytic, --crosscheck (< 0.2 dB) and an A/B vs today's CUDA path before any data counts. NOT enabled for the 2026-10-22/23 overnight queue (one solver for the compare tier and surrogate top-up).
- [x] **P2 12 kHz finalist verify pass on the 4060**: DONE 2026-10-23 (see the item below and `docs/evidence/HF12K_VERIFY_2026-10-23.md`).
- [ ] **P3 `beat_metal` backend** for the collaborator's Apple Silicon MacBook (fused path on, unified memory); Mac selftests + 3-design A/B vs the 4060 before mixing data.

TO-DO (no GitHub issue yet; owner / plan ref):
- [x] Merge the learnings PR, run its section-4 test plan on the GPU box: DONE 2026-10-22 (FF to 265133f; `docs/evidence/BL_LEARNINGS_GPU.md`).
- [x] Early rejection offline replay: DONE 2026-10-22 (`docs/evidence/EARLY_REJECTION_REPLAY.md`): < 0.1 % GPU saved at K = 4 / 25 % margin, no top-20 lost; recommend NOT implementing as specified (owner ruling).
- [x] (closed 2026-10-23 by the failure cache) Search budget counts uncached failures: a re-run with the same CMA seed replays cached successes for free but re-evaluates every earlier failure, which consumes budget without solving (OSSE budget 40 -> 0 new solves, 2026-10-22). Options for the owner: cache failures by design hash, or count only solver-reaching evaluations (task 08; `search/cma.py`).
- [ ] CPU-vs-CUDA qualification screen per pinned-library change (GPU box; frozen CP-7b rule; s2 item 8). Note: beat_cuda vs bempp_cpu re-run 2026-10-22: 0.039 dB (`docs/evidence/SOLVER_VERIFY_2026-10-22.md`).
- [x] Typology plan v2 implemented 2026-10-22 (generators, hybrids, briefs, `families`/`campaign`, failure cache, loading metrics). GPU checks V4/V5/V7 in progress.
- [ ] Le Cléac'h / spherical-wave generator DISABLED (R9): implement only from a verifiable published construction (ETF 2010 lecture PDF too large to fetch, diyaudio thread 403, sphericalhorns.net calculator disclaims fidelity to JMLC). Needs a human-supplied reference.
- [ ] Brief `source.cap: auto` not applied: FREEFORM keys in `families.py` do not expose the mesher's source-cap radius/auto-angle; every design uses the mesher default cap (consistent within a campaign). Add the keys (task 04) and tie to the brief.
- [ ] Generated horns use a 3 mm outer shell (mesher FREEFORM curvature guard); Magnus-family configs use the mesher default shell. Outer-shell thickness differs between the two groups; small acoustic effect at the mouth rim, recorded per design.
- [ ] `search_smoke` (legacy) cannot be dry-run under a 5.5 kHz brief (seed exceeds its dof cap); harmless, legacy only.
- [x] `search --brief/--cma-seed` were silently ignored (fixed 2026-10-22; first campaign's native-family entries invalid and re-run).
- [x] Campaign fairness: cached replays gave native configs 6-15x more search; `--max-evals` caps all evaluations (fixed 2026-10-22).
- [x] Hygiene left BEAT `worker_host` processes (which respawn julia) alive; now cleared with their julia children (fixed 2026-10-22).
- [ ] `perturbed_osse_hv`: 36 % invalid in the screen run and `L_mm` pinned; revisit its bounds/u_max before a compare run (widening needs user OK).
- [x] Brief size envelope now enforced for every family (outer mesh bbox); native configs sized for other targets (osse_baseline, freeform_sculpt under the 400x300 brief) have no valid design and are labelled so in the leaderboard. Beta users: use typology configs or size a native config for the brief.
- [ ] Mesher upstream 4573bc90 is 57 commits past our pin b922e807 (FREEFORM corner topology `d740c28`, `68ed646`, joins `967db56`; ATH import; new geometry keys). Signatures and the 0.4 curvature guard unchanged. Owner 2026-10-22: keep the pin for the beta; post-beta bump candidate with its own verification ladder.
- [x] R8 brief provenance: dataset records carry optional `provenance` {config, brief, brief_hash, generator} (2026-10-22).
- [x] C2 epw 6 vs 8: axi seed DI 0.124 dB > 0.1 -> axi typologies at epw 8 (owner); H/V within 0.05 dB stays epw 6.
- [x] GPU lock + `gpu-clean` (2026-10-22); overnight queue + watchdog in `tools/overnight/`.
- [x] GPU lock liveness on Windows: `os.kill(pid, 0)` made a live holder in another console look stale (takeover / gpu-clean would hit a running solve). Fixed 2026-10-23 with OpenProcess/GetExitCodeProcess + tests.
- [ ] OSSE `exponent` presses its upper bound (7.9 of 8) in the 2026-10-23 top-up (seen in the time-lapse): bound decision for the owner, like the other pinned bounds.
- [x] **Search does not recover a dead BEAT worker host** (2026-10-23; FIXED 2026-10-23 ~14:30, offline-tested: root cause = `hornlab_beat_bem.worker.get_worker` caches a `HostedBeatWorker` that keeps its dead socket after a send fails, so every later solve wrote to it; `recover_after_failure` now also calls `detach_workers` (drops the cache), `BeatBackend` re-warms and retries a `worker_exit` candidate once, and `search` stops RESUMABLY (status aborted, `SolverUnhealthyError`) after 3 consecutive `solve_failed` instead of ending on `tolflatfitness`; `to_training_arrays` drops `solve_failed` records from labels (`meta.skipped_solve_failed`). Tests `tests/test_solve_beat_recovery.py`, `test_search_cma.py`, `test_dataset_store.py`. The host death itself is still unexplained, GPU rule 7. Original report: OSSE top-up seed 4101 lost its host at 03:58:48 EDT (`ConnectionResetError` 10054, `solve_failed [worker_exit]`); every later candidate failed in ~3 s (21 rows), J went flat at the 1000 penalty and CMA-ES stopped on `tolflatfitness` at 411 of 950 evaluations. Cause of the reset unknown (second unexplained reset tonight; first in the C2 check 21:46, not reproduced from clean, CLAUDE.md GPU rule 7). Fix proposal (task 05/08): on `worker_exit`, re-warm the host once and retry the candidate before scoring a failure; never let a run of solver failures end a search. The 21 `solve_failed` dataset records are failures of the solver, not of the designs (non-deterministic kind, never failure-cached); exclude `solve_failed` from the surrogate's validity labels.
- [x] Local web GUI `hornlab-search gui` (2026-10-23, `docs/GUI_PLAN.md`). Open: macOS untested; 3D view needs the three.js CDN. Launch GPU-busy state now LIVE (polls `/api/status` every ~6 s, toggles note / Start button, toast; 2026-10-23 14:30; the server still re-checks on launch). Senior UX pass done 2026-10-23; typology picker, Typologies page and graphics pass done 2026-10-23 (09:00); search time-lapse player 2026-10-23 (10:40); beta hardening + Boundary Lab-style isobars 2026-10-23 (11:30, d0a04ea).
- [x] Wire `surrogate.features.require_surrogate_config` into `cli._cmd_surrogate`: done 2026-10-23 (merged).
- [x] Beta-readiness pass per `docs/HANDOFF_BETA.md` (F timed rehearsal DONE 2026-10-23 16:30, 8 friction points fixed, `docs/evidence/BETA_READINESS.md` F; G session plan refreshed with measured timings; A-G; A-D done (D3 Ctrl-C PASS on the GPU 2026-10-23 after a campaign fix; D5 paths PASS); E running overnight; F, G pending): upstream audit, R8 brief provenance in dataset records, epw convergence above 2.5 kHz, GPU lock / gpu-clean, rehearsal, session pack.
- [x] `compare` tier (2 CMA seeds) on the leaders: DONE 2026-10-23 (`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`).
- [ ] Bound proposals from the compare tier (osse_axi `h_s`, hypex/exponential `L_mm` lo, perturbed_osse_hv `L_mm`/`v_a_deg`, hybrid `v_rm_mm`): owner decision; NOT applied.
- [ ] rosse_baseline is seed-sensitive (12.3 vs 14.3): more seeds or budget before any ranking claim.
- [x] Failure cache: deterministic failures cached by design+mesh+solve key across runs (fixes the OSSE seed-replay budget burn).
- [ ] Stage 2 transient analysis (impulse, step, CSD waterfall, group delay, dense throat impedance) on finalists: research + design in `docs/research/TIME_DOMAIN_RINGING.md`; needs a dense uniform frequency list per evaluation (today only 12/25/36-point log grids, too sparse: Magnus's `plot_impulse_response` interpolates over resonances). After the typology campaign; not in the search loop.
- [x] R-OSSE: `examples/rosse_baseline.yaml` added 2026-10-22 and run in the hifi screen + compare campaigns (seed-sensitive: 12.3 vs 14.3, see below).
- [ ] ICW rollback termination never exercised (categorical; needs its own config). In the typology plan.
- [ ] `freeform_hv.yaml` solves the full domain although FREEFORM quarter == full within 0.0043 dB (4x dofs wasted). In the typology plan.
- [x] STEP-export CLI: DONE locally 2026-10-22 (`hornlab-search export-step`, b822dd5).
- [x] OSSE data top-up for the surrogate gates: DONE 2026-10-23 (user OK 22:14): seed 4101 411 evals (host death 03:58), seed 4102 951 evals. Retrain + CP-8d gates next (CPU).
- [ ] Boundary Lab BL-1 export (cloud; `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`).
- [x] `compare` IndexError on empty frequency list: fixed 2026-10-23 (merged).
- [x] `verify --brief` was parsed and silently IGNORED (found 2026-10-23 preparing P2; would have re-verified at 5.5 kHz). Fixed: the brief is applied and the results go to their own run dir `runs/<ts>-verify-<id>` (listed by the GUI; `run.json.verify_of`); `verify` without `--brief` unchanged. Test `tests/test_search_verify_brief.py`.
- [ ] Collaborator pulling `main` 2026-10-23 evening: `docs/HANDOFF_COLLABORATOR_2026-10-23.md` (branch + PR; owner merges after the GPU jobs).
- [x] P2 12 kHz finalist verify pass: DONE 2026-10-23 16:07 (`docs/evidence/HF12K_VERIFY_2026-10-23.md`): 14 designs, 0 failures; epw converged at 12 kHz (<= 0.058 dB, <= 0.31 deg); rankings as in the compare tier; peak VRAM 7,360 MiB above baseline at 6,049 dofs (edge of 8 GB). 8-12 kHz compares geometries, not drivers (f11 7,914 Hz).

- [x] Docs index `docs/INDEX.md` and code map `docs/CODE_MAP.md` added 2026-10-22, linked from CLAUDE.md / AGENTS.md / .claude/CLAUDE.md; keep them current.
- [x] Campaign Ctrl-C and host hygiene (2026-10-23): `run_job` killed a Ctrl-C'd child mid clean-up and skipped the leaderboard; a campaign never cleared its Julia/BEAT hosts (snapshots only). Fixed (grace period, partial INTERRUPTED leaderboard, exit 130, hosts cleared after every job); D3 PASS live (`docs/evidence/BETA_READINESS.md` D).
- [ ] Surrogate retrain 2026-10-23 (`docs/evidence/CP-8d_retrain_2026-10-23.md`): GATES FAILED (topk 11/20, invalid_accuracy 0.80, monotonic_flips 4) at 600 epochs; held-out 463 < 500 (indicative). Model NOT used. Owner: ~250 more OSSE records for the floor; flips semantics; why the ranking/validity gates got worse with more data.
- [x] `*_12k` verify-only briefs were accepted by search/run/campaign and offered by Launch (2026-10-23 rehearsal): `verify_only: true` brief key; search/run/campaign refuse (exit 2), Launch hides them; tests in `tests/test_search_verify_brief.py`.
- [ ] Live demo on a shipped brief replays from the cache (~1 min, same CMA seed): use a saved brief copy (5.5 min measured). A `--cma-seed` option for `campaign` would make fresh live runs possible on shipped briefs (owner, task 08).

Local-only, added 2026-10-24 (senior pass): implementation backlog WP1-WP17 in `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` (objective v2, driver pinning, fused CUDA in our fork, 12 kHz screens, GRID shapes, multicell); owner gates: WP13 third-party axisymmetric solver, GitHub hosting of forks, v2 as default.

Local-only, added 2026-10-24 evening (orchestrator, M1 implemented + Oracle-verified; pushed): WP1, WP2, WP3, WP4 (offline parts) and WP15 repo-side plumbing LANDED (see `docs/CONTINUITY.md` 2026-10-24 entry; Oracle verdict GO, all 3 must-fixes in the push commit; 933 offline tests pass, no test loosened).
- [x] WP1 objective v2 + offline re-score: DONE (`docs/evidence/OBJECTIVE_V2_RESCORE.md`; rho 0.989, claims survive, v1 drift 0; v2 stays OPT-IN — making it the brief default is an owner decision).
- [x] WP2 driver pins with embedded-brief grandfather: DONE (2 pre-WP2 runs with an embedded 12.7 brief on a 17.78 OSSE config now load byte-for-byte; new `--brief`/`brief_file:` runs enforce; `osse_baseline` is skipped under 1-inch briefs by the campaign compat check).
- [x] WP3 shape-only perturb + pre-mesh `invalid_envelope` + graded penalty (opt-in `search: {infeasible_penalty: graded}`): DONE; all shipped typology seeds estimate 0.0.
- [x] WP4 `freq_weights` (v2-only, v1 warns once) + `verify_points_per_octave` HF verify grid: DONE.
- [x] WP15 repo side (`solve.cuda_fused`, env gating, `assembly_path == "fused_cuda"` proof + refusal): DONE offline; fork branch `hornlab-search/fused-cuda` @ fa99ee5 (Julia tests green). Gpu ladder + ceiling measurement NOT RUN yet (M2; owner: do not pin a file:// URL on main).
- [ ] Oracle non-blocking follow-ups (recorded, none urgent): (1) `invalid_envelope` not failure-memoized (brief-dependent; revisit with a brief-aware marker key in M2); (2) envelope estimator adds full wall thickness radially — conservative by ~2.5 mm at 80 deg mouths (documented; no shipped seed affected); (3) dataset record lacks an explicit `objective_version` field (config_sha covers it today — add in M2); (4) solve-cache/`ctx.known` reuse keys exclude the objective version — never flip objective version on a resume; start a new run; (5) v2 solve-cache hits re-score with the CURRENT weights like v1 (documented behaviour, unchanged by design); (6) `_verify_only_precheck` precedence note for the CLI docs (verify_only wins over a broken config — intended); (7) `tools/rescore` duplicates the balloon-collapse block of `metrics_from_response` (drift-0 verified; keep in sync); (8) cosmetic tautology in `test_solve_fused_flag.py` last assert.
- [ ] `tools/launch_gui.ps1` (pre-existing untracked, benign): owner decides; kept out of the M1 commit.
- [ ] Owner decisions queued from M2 onward: fork GitHub hosting + push; v2 default; WP13.
