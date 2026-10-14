# CONTINUITY

Newest entry first. Every push updates this file and `docs/ISSUES.md` in the same commit.

## Status
- **Wave:** 0, 1, 2 and 3 complete; Phase 2 Stage A code landed (synthetic-tested only) (tasks 04-08 done; CP-7a-f all PASS). This is the end of the plan's Wave ladder.
- **Last checkpoints:** CP-7 (senior physics gate) GREEN — noise floor **0.039 dB**. **CP-8a PASS, CP-8b PASS** (local GPU box, 2026-10-13: 480 offline + 18 GPU-marked tests, doctor 10/10; bounds widened `a_deg` 25→5 / `exponent` 2→1, rerun no longer pinned). CP-1/CP-2/CP-4/CP-5/CP-6 all green.
- **Next action:** CP-8c — multi-family dataset runs (osse_baseline 1500, icw_termination 800, freeform_hv 800, throat_adapter 400; one at a time, ~15-17 h GPU serial estimated; user consulted before starting; runs resumable). Then CP-8d train/gate (≥ 500 held-out per family, else report "indicative only"). Dataset now 134 records, 100 % OSSE.
- **PULL BEFORE CP-8d:** merge `ccr-455d2184-yj5zk4` (PR #14, issue #13 fixes) after CP-8c closes, never mid-run. See the 2026-10-14 notice below. **[SUPERSEDED locally, 2026-10-13 ~20:30: the same fixes are ALREADY on this branch as commit 567ec8b (8 items, offline suite 488 PASS with the mesher) — do NOT merge PR #14 on top; diff and adopt ONE set. See the reconciliation paragraph in the 2026-10-14 notice entry.]**
- **Blockers:** none. Issue **#13** open (hardening review — circle-back before/with CP-8d; do not weaken gate thresholds). Issues #1-#11 closed.

## 2026-10-13 (local GPU box, ~23:10) — store/CLI pipeline fixes + CP-8d glue implemented; full offline suite 498 PASS (fixer lane, CPU-only; fix queued by the senior review)

- Implemented all five queued items (offline/CPU-only while run 3 flew): (1) `dataset stats` now reports **`missing families`** (R-OSSE will be listed, by design) + **`duplicate designs`** count; (2) `verify_store` checks Y-metric array **shapes** vs the record's own `solve.freqs_hz` and reports `bad_arrays` separately — exactly what `to_training_arrays` would otherwise silently drop; `dataset verify` exits 1 on either `bad` or `bad_arrays`; (3) **resume guard**: `search --resume` compares `run.json["config_sha"]` to the current config and REFUSES on mismatch (naming both SHAs) unless `--allow-config-change` is passed — the mid-campaign weight/bound edits recorded as follow-ups can no longer silently mix old-J and new-J rows; (4) `surrogate train` headline split: `GATES FAILED: <names>` vs `GATES REFUSED (indicative only): all <N> measured gates pass; held-out <X> < 500 formal floor`; (5) **new `surrogate round` subcommand** (`hornlab_search/surrogate/round.py` + CLI): loads proposals.json, solves each through the normal `evaluate` path into a FRESH run dir with its own ndjson, computes `round_report`, and writes atomic `ismo_round1.json` with report + per-proposal rows + `random_true_J` provenance + exploit/explore-medians + exploit parameter spread + store counts before/after + bundle gate status + config_sha — the CP-8d honesty artifact the reviews demanded.
- **Behaviour changes (mid-campaign callers):** resume of a run whose `config_sha` mismatches now REFUSES (escape hatch `--allow-config-change`; known false-positive edge: a run started with `--backend` override — see its report); `dataset verify` exit code now includes bad array shapes (new failure class if legacy data has any; current store is clean); `dataset stats` prints an extra line; `surrogate train` headline wording changed; `surrogate` gained the `round` action (solve-per-proposal only when invoked). Ownership note: touches `dataset/**` + `cli.py` beyond `_cmd_surrogate` — user-authorized, flagged for cloud review like the #13 lane.
- Tests: lane's own 88 + 11 targeted pass, compileall clean; **full offline suite 498 passed, 18 deselected, exit 0** (84.83 s, alongside the GPU run). Scope check: only `dataset/store.py`, `cli.py`, `surrogate/round.py` (new), two test files; no docs/plan/examples/conftest, no GPU, no runs/dataset/cache writes.
- With this, every prerequisite the senior reviews set for CP-8d is landed: verdict persistence + propose refusal, config freeze, dedup, meta prints, NaN conventions, atomic writes, duplicate/missing-family visibility, array-shape verification, resume guard, and the persisted round artifact.
- Addendum (corrective commit, same hour): commit 11304f6 touched CONTINUITY but missed the matching `docs/ISSUES.md` update (my oldString mismatch) — the push rule was broken once; this corrective commit restores it. ISSUES now carries the (c)-IMPLEMENTED status, the second stale "5/6 at q lo" statement (line 25, digest note) corrected, and the same PR-#14 supersession annotation the cloud notice carries in CONTINUITY.

## 2026-10-13 (local GPU box, ~22:40) — senior pipeline/plan review reconciled; evidence corrections applied (glm-5.3 oracle + local agent)

- The second senior review (store/evaluate/report at scale, CP-8d plan-vs-API, evidence audit) returned 17 findings while run 3 flew. Docs corrections applied NOW (full block in ISSUES): **(1) CP-8c yields THREE families, not four** — `throat_adapter.yaml` is `family: OSSE`, so R-OSSE stays 0 and `dataset stats`' family warning (fires only above an 80 % share) will NEVER flag a MISSING family; HANDOFF §5's "all four families present" criterion is unsatisfiable as written → amended CP-8c criterion recorded in evidence: **verify OK + OSSE/ICW/FREEFORM present** (R-OSSE deliberately absent; adding a config is the cloud owner's call). HANDOFF_LOCAL.md itself left untouched (not mine to edit — the correction lives in evidence + ISSUES). (2) **OSSE `q` pinning corrected**: final data shows `q` top-6 **0/6** near lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49 — attracted, NOT pinned; the earlier "5/6" was the in-flight 13:40 snapshot); `n` stays 6/6. (3) run-1 snapshot "seed J 22.07" corrected to **22.592** (22.07 was the smoke seed). (4) ICW warning scope restated: 24 warning LINES all at one timestamp → plausibly ONE design of 800; per-design attribution is not recorded. (5) `manifest.sha256` wording corrected: it hashes the METADATA layer (run books/ndjson/index/shard JSONLs), NOT the per-record `.npz` labels or `traces/` (covered by `dataset verify` as existence/validity, not bit-identity); line-3 indent fixed so `sha256sum -c` parses. (6) the digest stamps `generated_utc` from now on.
- **CP-8d misreading guards adopted verbatim** (14-item list in ISSUES): refusal-vs-failure headline with `n_heldout` vs the 500 floor; solved-only medians AND exploit/explore reported separately; `random_true_J` provenance (CMA gen-0 samples, penalty-row convention); proposals' parameter spread (the 30 exploits are near-clones of one NSGA basin); frozen `pred_J` + bundle/config_sha/store count recorded; results persisted as `ismo_round1.json` + `docs/evidence/CP-8d.md`.
- **Next implementation lane dispatched (store/CLI small fixes, CPU-only):** `n_duplicate_designs` + `missing_families` in `stats()`/`stats_report`, Y-array shape check in `verify_store` (report `bad_arrays` separately), `config_sha` comparison on `--resume` (unmissable warning → refuse unless overridden), the refusal-vs-failure headline split in `surrogate train`, and the CP-8d round helper writing `ismo_round1.json`. These cross task-ownership lines (dataset/**, search/**, cli.py) — implemented under the user's explicit authorization, flagged for cloud review exactly like the #13 lane.
- Checked clean at scale (no action): append cost, shard roll, in-memory index, trace sampling (4.1 % vs 5 % set), torn-line recovery, ndjson durability, digest arithmetic (2434 = 1500+1+130 smoke+3 older OSSE + 800 ICW; `skipped_grid_mismatch` 133 = the 4500 Hz-grid records; held-out 225.2 = 15 % × 1501).

## 2026-10-14 (cloud, ~02:05 UTC) — NOTICE: surrogate fixes waiting on `ccr-455d2184-yj5zk4`; merge AFTER CP-8c, BEFORE CP-8d (senior reviewer: Claude)

> **LOCAL AGENT: do not run CP-8d (`surrogate train` / `propose`) on this branch's current code.** Issue #13 fixes F1-F6 are on `ccr-455d2184-yj5zk4` (draft PR #14 into this branch), with offline suite 455 passed / 30 skipped. They touch only `surrogate/**`, `_cmd_surrogate`, surrogate tests and `HANDOFF_LOCAL.md`, so the running CP-8c search is unaffected. **Do not pull mid-run.** When CP-8c is closed and julia is cleared:
> 1. `git fetch origin ccr-455d2184-yj5zk4` then `git merge origin/ccr-455d2184-yj5zk4` (conflicts expected in `docs/CONTINUITY.md` / `docs/ISSUES.md` only: keep every entry, newest first).
> 2. Run `pytest -m "not slow and not gpu and not crosscheck"` (expect ~485 with the mesher), paste it, push.
> 3. Then CP-8d. Note: `propose` now refuses a gate-failing bundle, so with ~225 held-out CP-8d stops after `train` ("indicative only"), as HANDOFF already says.
> Review: `docs/SENIOR_REVIEW_2026-10-14.md` (on the fix branch). This entry is docs-only.
>
> **LOCAL AGENT RECONCILIATION (2026-10-13, ~20:30 local): the SAME issue-#13 fixes were independently implemented on THIS branch (commit 567ec8b, next entry) before this notice arrived** — the hardening lane was user-authorized, ran offline/CPU-only, and was discovered colliding with this notice only during the push rebase. Commit 567ec8b covers EIGHT items (this notice lists six: F1-F6) and the full offline suite WITH the mesher passed 488/0-deselected-other on this branch. **Do NOT merge `ccr-455d2184-yj5zk4` on top** — that would double-apply overlapping changes in `surrogate/**`. Cloud owner: diff 567ec8b against PR #14 and adopt ONE set (drop the other). CP-8d proceeds on this branch's fixed code either way. Note one deliberate difference: `propose` here refuses by default but has `--allow-unvalidated`, so the runbook's "indicative only" CP-8d (held-out 225 < 500) can still propose and solve round 1 — which HANDOFF intends — while the notice's wording suggests CP-8d stops after `train`.

## 2026-10-13 (local GPU box, ~20:15) — issue #13 hardening IMPLEMENTED; full offline suite 488 PASS (local agent; fixer lane, CPU-only while run 3 flies)

- **All eight hardening items from the issue #13 review are implemented** (offline/CPU-only, alongside the GPU campaign): the Stage A bundle now (1) persists the gate verdict (per-gate value/threshold/pass, `n_heldout`, warnings) and (2) freezes the config contract (family / ordered keys / per-key bounds {lo,hi,log} / freqs); `surrogate propose` **refuses** a bundle with no verdict, a failing verdict, or a family/keys/bounds/freqs mismatch — `--allow-unvalidated` is the explicit escape hatch for the CP-8d indicative flow; the gate report is evaluated BEFORE saving (atomic tmp+os.replace) and a failed retrain **keeps an existing PASSING bundle** instead of clobbering it; rank-gate labels are recomputed from the metric arrays with the CURRENT weights/target (stored objective only feeds `objective_delta_max/mean`); `surrogate train` prints the `to_training_arrays` meta (`n_considered/n_selected/skipped_grid_mismatch/skipped_bad_arrays/skipped_keys`) with a loud WARN on drops; duplicate `design_hash` rows are deduped before the cluster holdout (`n_duplicates_dropped`); `round_report` coerces `true_J >= PENALTY_FAILED` to NaN (failed proposals excluded from the median, counted in `n_solved_failed`); NSGA-II maps non-finite objectives to `PENALTY_FAILED` (NaN can never rank as non-dominated); bundle/`proposals.json`/`pareto.json` writes are atomic. **`gates.py` thresholds untouched (0 diff lines).**
- **Behaviour changes a caller must know:** `propose` now refuses by default (it previously proposed from any bundle); `train` reports `kept_existing_bundle`, `n_duplicates_dropped`, `objective_delta_max/mean`; bundle `meta` gains `gate_report` + `bounds`.
- Tests: 22 focused surrogate/ISMO/NSGA tests pass (12.15 s); compileall clean; **full offline suite 488 passed, 18 deselected, exit 0** (85.93 s) — run while the freeform_hv GPU run was active. Scope check: only `surrogate/**`, `search/nsga.py`, `cli.py` (_cmd_surrogate + parser + one supporting import), and the three test files changed; no docs/plan files, no GPU, no runs/dataset/cache writes, nothing committed until this gate passed.
- This closes the gate-integrity prerequisite the two senior reviews set for CP-8d: none of CP-8d's numbers were quotable until this landed — it now has (pending the cloud owner's review of the diff).

## 2026-10-13 (local GPU box, ~19:50) — CP-8c run 2/4 COMPLETE (icw_termination 800): best J 12.20 (-78 % vs seed); dataset now two families (local agent)

- Run `runs/20261013T204408Z-screen-6bdcbd`, budget stop: **800 rows = 787 ok + 13 failed** (`invalid_geometry` 5, `mesh_too_large` 8), torn 0, ok rows with metrics null 0, zero in-run dups. **Seed J 55.7357 → best J 12.2009 (-78 %)**; median ok-J 12.87; best `n_dof` 2823.
- Throughput: **13.0 s/candidate (278/h)**, GPU solve 8688 s (~2.4 h), wall 2.9 h; VRAM never exceeded ~2 GiB on this family. Zero monitoring alarms; post-run reaped BOTH idle worker hosts (incl. one `julialauncher.exe`), VRAM 411 MiB.
- Dataset: **2434 records (2311 ok, 123 failed), 5 shards, 395.3 MB** — OSSE 1634 + **ICW 800**; the single-family warning is GONE (2 of 4 families present). `dataset verify` re-runs after runs 3-4.
- **ICW data-quality note (bounded):** mesher warning `outer wall self-intersects ... normal flip near azimuth row 0 ... the acoustic (inner) surface is unaffected` — 24 occurrences, ZERO new after 17:06 local (a few % of designs; rows still validate). Recorded as a caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. `termination` is categorical (`flat_baffle` in all ok rows) — the digest generator now handles categorical params (was crashing on `float('flat_baffle')`; fixed and re-run).
- **ICW bound pinning (new finding, follow-up):** best designs **fully pinned at the `hold_end` LOWER bound 0.55** (top-6 6/6, Spearman vs J +0.64) and 4/6 near `kappa0` lo = 0.0 (median 0.0016 — the search wants κ₀ ≈ 0; 0.0 is already the schema floor). Candidate: widen `hold_end` lo below 0.55 subject to the repo's `hold_start < hold_end` rule + mesher validation. Recorded, NOT changed mid-campaign.
- Issue #13 note: CP-8d trains on OSSE, so the ICW pool does not enter the OSSE gate arithmetic (digest OSSE pool unchanged: kept 1501 of 1634, held-out 225.2 < 500 → Stage A remains "indicative only").
- Evidence: new `docs/evidence/CP-8c_icw_termination.md`; digest/log/manifest copies refreshed (manifest includes the icw run's ndjson/json files).
- **Next: run 3/4 `freeform_hv --budget 800`** (full H/V domain — expect a slower candidate), then `throat_adapter` 400, then final stats/verify + digest to close CP-8c; then CP-8d.

## 2026-10-13 (local GPU box, ~16:50) — CP-8c run 1/4 COMPLETE (`osse_baseline` 1500): best J 6.106 (-73 % vs seed); `dataset verify` OK (local agent)

- Run `runs/20261013T123136Z-screen-ca15be`, budget stop: **1500 rows = 1405 ok + 95 failed** (`mesh_too_large` 93, `invalid_geometry` 2), torn 0, ok rows with metrics null 0, zero in-run duplicate designs. **Seed J 22.5921 → best J 6.10609 (-73 %)**; median ok-J 6.45.
- Throughput: **19.2 s/candidate (187/h)**, GPU solve 26,067 s (~7.2 h), wall 8.0 h. Live monitoring: 5-min watchdog + 30-min review ticks (11 ticks); **zero alarms the whole run** — no stall, no junk, exactly one `julia` host, VRAM cycles 511 MiB–4.3 GiB on the 8 GB card. Post-run: idle host reaped, VRAM 419 MiB.
- Dataset: **1634 records (1524 ok, 110 failed), 4 shards, 273.4 MB**, 100 % OSSE. **`dataset verify` OK — 1634 records re-read, 0 bad** (will re-run after runs 2-4).
- Bound pinning on the final data: best designs fully pinned at the `n` lower bound (2.0) and 5/6 near `q` lo (0.9); `a_deg`/`exponent` interior — the CP-8b widening held, and the active constraints for this objective are `n`/`q` (follow-up: widen `n`/`q`, mesher needs only `> 0`; recorded in ISSUES, NOT changed mid-campaign).
- Issue #13 arithmetic, final: OSSE pool kept **1501** of 1634 (`skipped_grid_mismatch` **133** = the 4500 Hz smoke records), held-out at 15 % = **225.2** < 500 → the CP-8d OSSE gate will refuse → reported as **indicative only**, as predicted. A formal OSSE pass would need ~3,400 osse_baseline-grid records (~17 h more GPU).
- Evidence refreshed and pushed this commit: `docs/evidence/{CP-8c_data_summary.md, data_summary.json, logs/*, manifest.sha256}` + the final block in `CP-8c_osse_baseline.md`.
- **Next: run 2/4 `icw_termination --budget 800`** (est ~4-4.5 h at icw's expected ~20 s/candidate), then `freeform_hv` 800, `throat_adapter` 400, then `dataset stats` + `verify` close CP-8c, then CP-8d.

## 2026-10-13 (local GPU box, ~13:40) — agent-readable data digest committed; new `n`/`q` pinning finding (local agent)

- **New: `docs/evidence/CP-8c_data_summary.md` (12 KB) + `data_summary.json` (56 KB)** — a read-only digest of every run dir + the dataset, so a cloud agent with no access to the gitignored blobs can understand the outputs: per-run row/ok/fail/torn counts; J stats (min/median/mean/max, seed vs best); a per-key table (seed/lo/hi/min/median/max, **Spearman vs J**, fraction within 2% of each bound, **top-6 pinning**); objective-term medians; failure kinds with a sample message and the median params of the refused designs; timing/throughput; `di_source`/quadrants; and a dataset section with the pool composition. Generator: temp `data_summary.py` (read-only, CPU; regenerate at the end of CP-8c).
- **Issue #13's trap, quantified:** OSSE pool considered 1170 → kept **1037**, `skipped_grid_mismatch` **133** (the smoke runs' 4500 Hz grid), majority grid = 5500 Hz / 12 pts; held-out at 15% = **155.5** vs the formal floor **500** → the Stage A OSSE gate will REFUSE (indicative only), as predicted.
- **New finding (snapshot of the still-running `osse_baseline` search, ~1036 rows):** the best designs are now INTERIOR in `a_deg`/`exponent` (CP-8b fix works), but **fully pinned at the LOWER bound of `n`** (top-6 6/6 at `n` lo = 2.0) and 5/6 at `q` lo = 0.9; Spearman vs J: `n` **+0.75**, `q` **+0.56** — both want to be *smaller*. So for this objective the active constraints are `n` and `q`, not `a_deg`/`exponent`. Mesher limits: `n > 0` and `q > 0` while `s != 0` (`families.py::_validate_osse_like`), so both could be widened downward. **Recorded as a follow-up, not changed now** (a mid-flight bound change would break the running run's consistency and the surrogate's unit cube).
- Digest data-quality facts: torn lines 0 in all runs; ok rows with all-NaN metrics 0; X NaN fractions 0; one duplicated `design_hash` (the seed, expected).

## 2026-10-13 (local GPU box, ~13:20) — CP-8 evidence committed to git; CP-8c run 1 progress (local agent)

- **New: `docs/evidence/`** — durable checkpoint evidence in git (user request): `CP-8a.md`, `CP-8b.md`, `CP-8c_osse_baseline.md` (verbatim terminal output), `logs/` (copies of the live monitor logs: 5-min watchdog + 30-min review ticks), and **`manifest.sha256`** (SHA-256 + byte size of every raw local artifact: both run dirs' `search.ndjson`/`best.json`/`config.yaml`/`run.json`, the CP-8b `report_cp8b.html`, and the dataset `index.jsonl` + 3 shards).
- **Raw-data policy (why not everything is in git):** `dataset/`, `runs/`, `cache/` are gitignored by design (`.gitignore` lines 4-6) and now large — `dataset/` is 1069 files / **180.6 MB / 1128 records** (~160 KB per record; CP-5 projected 0.78-1.4 GB at 10k records). Committing the blobs would bloat the repo and break the convention; the manifest makes them verifiable without committing them. To move raw data, use a data branch / release asset, not the code branch.
- **CP-8c run 1 of 4 (`osse_baseline`, budget 1500) — snapshot 13:11 local** (`runs/20261013T123136Z-screen-ca15be`, still running): 988 rows, ok 893 / failed 95 (`mesh_too_large` 93, `invalid_geometry` 2), torn 0, ok rows with `metrics=null` 0, no duplicate design hashes, best J **6.11** (seed 22.07, -72%), median solve 18.05 s, 213 rows/h. Live monitoring: 5-min watchdog + 30-min ticks (ticks 1-3 all clear: no stall, no junk, single `julia` host, VRAM ≤ 4.3 GiB).
- Dataset at 13:13 local: 1128 records (1018 ok, 110 failed), 3 shards, 100 % OSSE. Remaining runs: `icw_termination` 800, `freeform_hv` 800, `throat_adapter` 400.

## 2026-10-13 (local GPU box) — CP-8a PASS, CP-8b PASS, bounds widened; hardening review filed as #13 (local agent)

**CP-8a PASS (real box, mesher tests unskipped):**
- `pytest -m "not slow and not gpu and not crosscheck"`: **480 passed, 18 deselected** in 164.42 s, `$LASTEXITCODE=0` (the cloud suite's 30 skips were mesher-gated → all unskipped here, matching the expected ~480).
- `hornlab-search doctor`: **10/10 PASS** (python 3.12.10, pinned SHAs, gpu check, beat_cuda ready, config round-trip, gpu-hygiene 0 hosts, VRAM 395 MiB).
- `pytest -m "slow or gpu or crosscheck"` (hygiene first: no julia, VRAM 395 MiB): **18 passed, 480 deselected** in 500.62 s, exit 0. Post-run: stray julia host killed (`taskkill /F /IM julia.exe`, PID 28464), VRAM back to 395 MiB. Consistent with CP-7: beat vs bempp ≤ 0.055 dB on the 2,316-dof quarter mesh; full-vs-quarter ≤ 0.031 dB ≤ 3 kHz.
- `dataset stats` before CP-8b: 134 records (119 ok, 15 failed), 100 % OSSE, traces 3.7 %, GPU solve 566.9 s total.

**CP-8b PASS — widen from the mesher's own limits (empirically verified, not guessed):**
- Acceptance probe (`hornlab_mesher` 0.2.4, profile level + REAL `build_mesh` at search_smoke screen settings): `a_deg` = 0.0/2.0/5.0/10.0/15.0/25.0 all mesh (crossing `a0=30` fine; radius monotone); `exponent` 1.0/1.5/2.0/4.0 mesh, 0.5 refuses (azimuth chord). Worst combined corner → clean `MeshTooLargeError`/`GeometryInvalidError` (refusal OK, no consistency crash). **Correction to the handoff:** "must keep `a_deg > a0_deg`" is NOT enforced anywhere — the OSSE radicand can only fail with a NEGATIVE `a0` steeper than `a`; repo bounds keep `a0_deg ≥ 2` so it cannot fire. Mesher floors: `a_deg ≥ 0` (coverage_angle non-negative, `profile_formulas.py:1231`), OSSE `exponent` unvalidated (clamp max(e,1e-6) at `profile_sampling.py:481`; itself overflow-broken at 1e-6), FREEFORM-station `exponent` hard [2,16] (`freeform.py:968`, mirrored `families.py:389-392`).
- Edits (`examples/search_smoke.yaml`, `examples/osse_baseline.yaml`): `a_deg` lo 25.0 → **5.0**, `exponent` lo 2.0 → **1.0** (5 has margin over the degenerate ~0 floor; 1.0 is 2× the empirically refused 0.5). `freeform_hv.yaml` exponent stays 2.0 (mesher hard [2,16] for FREEFORM stations — widening below would only produce rejected designs); `throat_adapter.yaml` stays pinned.
- Dry-run both configs: seed still meshes (search_smoke 2,598/3,000 screen dofs; osse_baseline 3,850/5,000).
- Rerun `search_smoke --budget 60` (`runs\20261013T121958Z-screen-9e5a5c`): 60 new evals in 254.5 s GPU (5.2 s/candidate, 690/h), seed J=22.0678 → best J=10.7776, failures {invalid_geometry: 1, mesh_too_large: 7} (classified, no crash); julia host killed after.
- Report bounds table: **no key pinned** — `a_deg` best 33.54 (0/6 of top-6 near lo 5), `exponent` best 4.67 (0/6 near lo 1). Old pins (a_deg=25.0, exponent=2.0) gone → pass criterion met with one widening.
- Honest caveat: this rerun's best J (10.78) is HIGHER than the old run's (9.66) at equal budget — 60-eval CMA variance, not a regression; the actionable outcome is the bounds are no longer active constraints.

**Hardening review (senior reviewer/oracle, read-only) → filed as issue #13; circle-back before/with CP-8d.** Top risks (full table + ready-to-paste fixes in #13): 1) gate verdict not persisted — `surrogate propose` accepts a failed/never-rated bundle and a failed retrain silently overwrites a passing `--out`; 2) rank gate compares stored objectives (solve-time weights) against predictions under current weights; 3) bundle does not freeze the bounds/family/keys/freqs it was trained under (bounds edited TODAY — commit before training); 4) pooling `search_smoke` (500-4500 grid) with `osse_baseline` (500-5500) silently drops all search_smoke records in `to_training_arrays` without printed counts — the ≥ 500 held-out arithmetic must use the printed post-filter count; 5) no `di_source` guard on the surrogate path; 6) duplicate seed rows can straddle the cluster holdout. **Do NOT weaken any gate threshold.**

## 2026-10-13 (cloud, high-frequency research) — options for 12 kHz on the 8 GB card (orchestrator: Claude)

- `docs/HIGH_FREQUENCY_OPTIONS.md`. Findings: (1) the 5.5 kHz ceiling is our 5,000-dof throughput cap on a LARGE seed horn (quarter area 0.282 m2), not the card's limit (8.9k quarter dofs fit); a smaller horn reaches 12 kHz inside existing caps. (2) In the pinned beat source the memory-saving fused Burton-Miller path is enabled for `:cpu` and `:metal` only; the CUDA exterior driver assembles four dense operators, and a unit-tested CUDA direct-system assembler is never called. Wiring it in would roughly 2.45x the GPU dof ceiling [inferred]; needs Collin's OK or a pinned fork (rule 1). (3) CPU backend (fused on, 32 GB RAM) can do a 19k-dof high-band finalist check at about 5 to 15 min per frequency [inferred]. (4) GPU-to-RAM swap is not viable on Windows. (5) Review of the local agent's explanation: mostly accurate, but its "memory needed" column is an upper bound including the memory pool, and it omits the horn-size and fused-path levers.
- Proposed CP-10a..d (size check, epw 4/5 accuracy test, high-band verify prototype on CPU, upstream question). None run. Caveat: above f11 (~5.65 kHz) the uniform throat source is not a real driver exit.

## 2026-10-13 (cloud, research) — cloud GPU rental report (orchestrator: Claude)

- `docs/CLOUD_GPU_REPORT.md`: web and code research on renting GPUs. Verdict: feasible, moderate effort, cheap (RTX 4090 about $0.34 to $0.69 per hour; L40S 48 GB about $0.79; A100/H100 poor value for a Float32 solver). Campaign estimate 5 to 40 GPU-hours, roughly $3 to $30 [inferred, unmeasured].
- Key risks: CUDA on Linux unverified by us or the beat authors; `solve/worker.py` host cleanup is Windows-tuned (POSIX branch never run on a real host). New proposed checkpoints CP-9a..d (pod proof, optional cap study, campaign, train/gate). No code changed. Needs user decisions: provider, spend cap, whether an agent may drive a pod.

## 2026-10-13 (cloud, handoff) — local-agent handoff written; CP-8 defined (orchestrator: Claude)

- `docs/HANDOFF_LOCAL.md`: step-by-step for the Windows GPU agent. Defines the next checkpoints: **CP-8a** run the full suite on the real box (mesher tests unskipped) + `doctor`; **CP-8b** widen `a_deg`/`exponent` bounds within mesher limits and re-run `search_smoke`; **CP-8c** multi-family dataset (`dataset verify` OK, all four families); **CP-8d** train and gate Stage A, solve proposals with BEM, `round_report` working.
- Finding for planning: the held-out set is 15 % of a family's records and the gate needs >= 500, so one family needs ~3,400 records (~4 h of `search_smoke`-rate GPU time) before a gate can pass.

## 2026-10-13 (cloud, later) — ISMO selection + `surrogate` CLI (orchestrator: Claude)

- `surrogate/ismo.py`: `propose` (NSGA-II on the surrogate; top-30 exploit + 10 highest-ensemble-variance explore, deduped) and `round_report` (plan step 5: do BEM-solved proposals beat random designs, rank correlation on them; `working` False otherwise).
- CLI: `hornlab-search surrogate train|propose --config ...`. `train` exits 1 unless every gate passes (and says do not use the model); `propose` writes `proposals.json` for real-BEM solving. Tests on synthetic data; offline suite green.
- Still GPU-box only: solve the proposals, feed `round_report`, retrain. Stage B/C/D not started.

## 2026-10-13 (cloud session) — Wave-3 review, report fixes, Phase 2 Stage A code (orchestrator: Claude, Haiku helpers)

**Environment:** Linux cloud container, NO GPU, NO mesher/beat installed. Offline suite: 447 passed, 30 skipped (mesher-gated), 18 deselected. Nothing GPU-side was run or claimed.

**Review of 73548a5 / 2a7bafb:** CP-7 numbers in docs are internally consistent with NOTES task-09. One finding fixed: `config.QUADRANT_FACTOR` duplicated `sizing.QUADRANT_FACTOR` (silent-killer rule: one source) -> now aliases it. Not fixable here: residual risks 1-4 (need GPU).

**Done**
- Report: noise-floor box refreshed to CP-7 values (floor 0.039 dB, two-solver; epw=6 above 2.5 kHz still flagged unmeasured). Browser check (Chromium, fake-backend run, 1280 and 390 px): no console errors, 24/24 images load, noise box first. Fixed: tables overflowed on phones (now scroll), `f11` label clipped at chart edge, numbers wrapping. Left as is (cosmetic/by design): convergence y-limit clips early outliers (p90), hornlab_plots PNGs small on narrow screens, unrounded table values, dark mode and empty-run render unchecked.
- Phase 2 Stage A (`hornlab_search/surrogate/`): `gates.py` (6 plan gates; refuses to pass with < 500 held-out), `features.py` (unit-cube encoding, cluster holdout), `model.py` (MLP + frozen save/load), `train.py` (ensemble, masked Huber, validity head, gate report), `predict.py` (batched surrogate evaluator). `search/nsga.py`: real NSGA-II + `search_pareto` (was a stub). Tests: `test_search_nsga.py`, `test_surrogate_stage_a.py` (SYNTHETIC labels: proves plumbing only; scrambled labels correctly fail the rank gate). CI now installs CPU torch.
- NOT done / honest limits: the real gates are untested (dataset is 74 single-family records; plan wants >= 500 held-out, multi-family). Superposition test not applicable to Stage A. No CLI subcommand yet. ISMO active-learning loop, Stage B/C/D not started.

**Next action:** on the GPU box, follow `docs/HANDOFF.md` runbook, then `to_training_arrays(..., ok_only=False, keys=space.keys())` -> `train_surrogate`.

## 2026-10-13 (06:20) — Wave 3 complete: CP-7a-f all PASS, rulings applied (orchestrator: OpenCode)

**Done**
- **CP-7 physics gate GREEN** (senior verifier, oracle, high-reasoning). All six checkpoints PASS with pasted output:
  - CP-7a analytic sphere: R(ka) spread **0.020 dB** (<0.5), omnidirectionality ≤0.005 dB, spreading 6.0205–6.0206 dB, convergence sub3/4/5 = 0.0204/0.0051/0.0013 dB monotone. Acceleration-drive reading confirmed (raw constant-velocity spread 24.06 dB/octave is expected, not a failure).
  - CP-7b two solvers: beat_cuda vs bempp_cpu **0.039 dB** (<0.2 → "both very likely right").
  - CP-7c mesh convergence **PASS on reduced band 500–2500 Hz** (the epw=18 full-band reference needs ~40k quarter dofs → OOM): epw=6 vs epw=18 mean|Δbw_h| **0.287°** (<2), mean|ΔDI| **0.028 dB** (<0.3).
  - CP-7d symmetry: max asymmetry **4e-6 dB**; M6 full-vs-quarter on the seed **0.023 dB** (≤3 kHz).
  - CP-7e plausibility: f0 = 343 Hz (H) / 480 Hz (V) below the 500 Hz band floor; DI-vs-beamwidth max **2.15 dB** (borderline vs the 1.5 dB guideline, far under the 3 dB "wrong" threshold); f11 (5653 Hz) sits just above the clipped 5500 Hz band → onset unresolved.
  - CP-7f **noise floor = 0.039 dB** (two-solver disagreement dominates; epw=6 DI discretization 0.028 dB just below it). The report's prior "0.055 dB, epw=6 not measured" is superseded — the floor is NOT mesh-limited.
- **Senior rulings** (verifier + rulings lane + user confirmations) recorded verbatim in a `NOTES_FOR_SENIOR.md` task-09 block. One code change: `config.mesh_spec` now calls `sizing.max_triangles_for` (was a 2% drift vs the contract-literal `ceil(2·cap·qf·slack)`).
- **Collin questions #7–#11 answered by the user and closed** (bempp-only Robin BC; trace ordering answered by test; use build_point_grid privately + pin; excitation is tag 2 / unit-acceleration; keep the name).
- Code/doc edits applied this session: `constants.py` throat-diameter comment; `families.py` + `examples/icw_termination.yaml` ICW wall-half-angle convention + explicit `kappa0`/`theta1_deg` seeds; `record.py` unit-acceleration note; `test_design_space.py` rewritten to pin the explicit-seed convention (fill demoted to defensive net); new `tests/test_mesh_pin.py` (fails on a silent HornLab pin bump) and `hornlab_search/mesh/grid.py` + `tests/test_mesh_grid.py` (single seam over `build_point_grid`).
- Full offline suite green (462+ tests; the earlier "71 records" is now 74: the verify run added three).

**Residual risks (phase-2 / post-Wave-3, not resolved here)**
1. epw=6 discretization above ~2.5 kHz unmeasured (epw=18 reference cannot be built there on 8 GB).
2. f11 (higher-order throat mode) never exercised — screen band clips below it.
3. DI-vs-beamwidth is not a regression test; real seed shows 2.15 dB balloon-vs-cuts (non-separable-rectangular signature).
4. Cross-run solve cache does not dedup the seed across separate `run` then `search` (two seed records, both cached:False).

**Next action:** post-Wave-3 follow-ups (widen `a_deg`/`exponent` bounds, run the other 4 example configs, browser-check `report.html`), then phase 2 (`11_PHASE2_SURROGATE`) if wanted. Awaiting the user's go-ahead.

- Addendum 06:45: `docs/HANDOFF.md` rewritten for the post-Wave-3 state (wave ladder complete,
  CP-7 numbers, rulings applied, all issues closed, residual risks, BEAT stale-registry hazard,
  next-work list). No code changes in that doc commit.



- Per user request, work stopped after Wave 2. Final state: Waves 0-2 done (CP-0..CP-6 green), CI green on b5bc811 (the task-08 push first failed because CI lacked `hornlab_plots`; fixed by installing the pinned package rather than skipping the report tests).
- GitHub: issues #1-#5 closed; #6 (Wave 3 senior checkpoints) open and unblocked; #7-#11 are questions for Collin. `docs/ISSUES.md` is synced.
- No Julia host or solver process left running; VRAM idle (~0.28 GB).
- `docs/HANDOFF.md` rewritten: next agent runs CP-7a-f (issue #6) and rules on the `NOTES_FOR_SENIOR.md` items.
- Not done: CP-7c/7e/7f, browser check of the report, senior rulings, Collin questions.

**Next action:** read `docs/HANDOFF.md`, then run Wave 3 (issue #6) with a high-reasoning verifier.

## 2026-10-13 (05:40) — task 08 done, CP-6 green (orchestrator: Claude)

**Done**
- Task 08 (objective, search, report, CLI) DONE: 479 tests pass (462 offline). Files: `objective/{terms,scalar}.py`, `search/{evaluate,cma,selftest,rundir,nsga}.py`, `report/html.py`, `cli.py` (doctor, version, run, search, verify, report, selftest, dataset), 8 test files. `doctor` has a real round-trip check and a new `gpu-hygiene` check.
- Live checkpoints on the RTX 4060 (agent report; logs in local `scratch/`):
  - `selftest --analytic` PASS: pulsating sphere, R(ka) spread 0.020 dB (limit 0.5), omnidirectionality <= 0.005 dB, spreading 6.0206 dB; convergence sub 3/4/5 = 0.0204/0.0051/0.0013 dB. Needed a port-drive correction (beat drives unit *acceleration*, so pressure carries 1/omega): needs senior confirmation (NOTES item 1).
  - `selftest --crosscheck` PASS: beat_cuda vs bempp_cpu 0.039 dB max (2,396 dofs).
  - `run` screen: seed J = 22.59, 3,850 dofs, solve 18 s (first solve). Coverage term dominates (seed ~95 x 84 deg vs 75 x 45 target): not a wrong divisor.
  - `search` (search_smoke): 60 new evaluations in 4 m 28 s (4.25 s/candidate, ~847/h); seed J 22.07 -> best 9.66 (-56%), resume extension to 7.36 (-67%); reproducible; 5 `mesh_too_large` + 1 `invalid_geometry` rows. `a_deg` and `exponent` sit near their lower bounds: widen.
  - Resume: zero re-solves for cached rows, first 60 ndjson rows byte-identical.
  - `verify`: screen vs verify J differ by up to 0.4 (12-point grid mis-ranks).
  - `report`: HTML written (5.3 MB), noise-floor box first (0.055 dB, limited by beat vs bempp; epw=6 discretization not yet measured). Not viewed in a browser.
  - `dataset`: 71 records (64 ok, 7 failed), 100% OSSE, 5.6% with traces; verify OK.
- Live bug found and fixed by the agent: the Julia host resolved relative mesh paths against its own cwd, so `search --resume runs\<dir>` failed; paths are now absolute with a test.
- Cleaned up a leftover BEAT worker host after the agent finished (hygiene rule 6 in practice).

**Open issues**
1. Senior rulings needed (NOTES_FOR_SENIOR, task-08 block): item 1 acceleration-drive reading of the analytic test; 4 (raw terms, 30.0 for unmeasurable terms, `Target.freq_weights` unused); 5 (DI from theta-phi balloon with sin(theta) weights); 6c (budget counts only non-cached evaluations); 7 (dataset choices).
2. CP-7c (epw=6 discretization error on a real horn) not measured; the report's noise floor is a lower bound.
3. verify/final meshes equal the screen mesh (band clipped); revisit with a smaller seed or higher cap.
4. Dataset is single-family; run the other example configs before any surrogate work.
5. Questions #7-#11 are for the user to send to Collin.

**Next action:** Wave 3: run the senior physics checkpoints CP-7a..f (issue #6) with a high-effort verifier; then summarize for the user.

## 2026-10-13 (01:10) — GitHub live (orchestrator: Claude)

- `gh` authenticated (account llevaachingada). Repo: https://github.com/llevaachingada/Hornfab. Labels created (wave-1, wave-2, senior-review, phase-2, blocked, question).
- Issues created: #1-#4 (tasks 04-07, closed with CP results), #5 (task 08, open, in progress), #6 (task 09, blocked by #5), #7-#11 (questions for Collin). Mirror in `docs/ISSUES.md`.
- CI: green on the latest commit (0a96c58). Two earlier red runs were my broken commits (missing `hornlab_search/dataset` because of an unanchored `.gitignore`; a test tied to the old frequency grid), both fixed. Lesson: always check the pytest exit code before committing (a `| tail` hid a failure once).
- Task 08 dispatched with exclusive GPU use; no solver jobs run by the orchestrator meanwhile.

**Next action:** when task 08 reports, commit it, run/verify CP-6 numbers, then hand CP-7a-f (issue #6) to the senior verifier. Questions #7-#11 are for the user to send to Collin.

## 2026-10-13 (01:00) — task 05 done, example bands capped (orchestrator: Claude)

**Done**
- Task 05 (solve) DONE, CP-3 green. 86 offline + 28 worker tests; slow (10), crosscheck (2) and trace (5) tests pass on the RTX 4060. Backends: `beat_cuda` (loops ONE frequency per `solve_frequencies` call because of the multi-frequency cliff), `beat_cpu` (single multi-frequency call; no cliff seen at 4.5k dofs), `bempp_cpu` (gated; Burton-Miller is refused with native symmetry, so it runs STANDARD formulation). Worker hygiene (stale Julia host detection/clear, verified release, SIGINT/atexit) implemented and tested in `solve/worker.py`.
- Numbers: cold 17.6 s / warm 0.80 s / post-detach 0.63 s; full vs quarter 0.031 dB (<= 3 kHz); beat vs bempp <= 0.055 dB; boundary-trace recovery 8e-5 dB; idempotence 3.6e-5 dB; mismatch (quarter without flag) 29.9 dB max, ~11 dB on axis; asymmetry sign check 100%.
- Resolved the "seed horn too large for the cap" decision (flagged by 04 and 05): all five `examples/*.yaml` failed at screen resolution (seed horn 0.80 x 0.64 x 0.27 m). Set `band_hi_hz` per config from the measured caps: osse_baseline 5500, throat_adapter 6500, icw_termination 7000, freeform_hv 5500, search_smoke 4500. All 15 config x mode combinations now build (2.5k-3.8k est. dofs). **User may override**: raising a band edge requires a smaller seed or fewer elements per wavelength, not a higher cap.
  Consequence: verify/final grids are also clipped to band_hi, so verify and final meshes equal the screen mesh; they differ only in frequency count and balloon size until a larger cap or a smaller seed is chosen.
- Fixed `.gitignore`: `dataset/` ignored the source package; anchored to `/dataset/` (commit d70ba06).

**Open issues**
1. Task 08 must call `solve.worker.install_handlers()` and `worker.warm(backend)` from the CLI.
2. Balloon is a theta-phi grid: DI needs `weights=sin_theta_weights(...)` (grid shape in `Response.meta['balloon_grid']`); not equal-area.
3. `timeout_s` is checked between frequencies only (CPU makes one call).
4. beat uses direct dense LU; `gmres_tol` recorded as requested, not applied.
5. The `gh`-gated GitHub labels/issues are still not created.
6. Senior-review items: tasks 04, 05, 06, 07 `NOTES_FOR_SENIOR.md` blocks.

**Next action:** dispatch task 08 (pipeline) with the verbatim template; then CP-6/7 live runs (`selftest`, `run`, `search`) one GPU job at a time.

## 2026-10-13 (00:25) — task 07 done (orchestrator: Claude)

**Done**
- Task 07 (dataset) DONE: 64 tests pass (CP-5). Files: `dataset/record.py` (415), `dataset/store.py` (694), 3 test files. Layout: one uncompressed `.npz` per record in `shard-NNNN/` + `shard-NNNN.jsonl` + `index.jsonl` (deviates from contract section 13's single `shard-NNNN.npz`; the phase-2 loader must go through `DatasetStore`). Crash recovery tested (torn index line, torn shard line, uncommitted row).
- Disk projection for 10,000 screen records: 0.78 GB without traces, 1.40 GB with traces at 1 in 20.
- Contract gaps to rule on (NOTES_FOR_SENIOR): added `traces.sample_fraction`; `lib_shas` requires 5 entries; NaN written as JSON null.
- Test `test_append_500_typical_records_is_fast` (5 s limit) measured 1.4-1.7 s on a quiet disk but failed at 6-9 s when the disk was loaded. Not loosened; may flake under load (recorded).
- Wiring for task 08: pass `solve_spec=`, `area_m2=`, `grid=` to `build_record`; catch `ValueError` from `append`; call `reset_warning_state()` at startup; subcommand hooks `stats_report`, `verify_store`, `export_training_npz`.

**Next action:** task 05 (solve) running; when it lands, dispatch task 08 (pipeline) using the verbatim template.

## 2026-10-13 (00:15) — task 04 done, caps set, CPU provisioned (orchestrator: Claude)

**Done**
- Task 04 (design + mesh) DONE: 87 offline tests + 27 mesher-gated tests pass (CP-2). Files: `design/{families,space,custom}.py`, `mesh/{sizing,build}.py` + 4 test files. Contract deviations (all in NOTES_FOR_SENIOR): `to_mesher_config` returns a *sectioned* dict (the mesher silently ignores a top-level `max_triangles`); pre-mesh dof estimate added so over-cap designs are refused in <100 ms; new exceptions `MeshConsistencyError/MeshUnitsError/SymmetryMismatchError` that task 08 must not swallow.
- I edited one task-04 test (`test_over_cap_but_inside_mesher_slack_is_caught_after_meshing`) so it reads the screen cap from the config instead of the hard-coded plan value 8000; same intent, no tolerance loosened.
- **dof caps replaced** (quarter domain): screen 5,000 / verify 7,000 / final 8,900; full-domain (`freeform_hv`) 3,000 / 4,500 / 5,400. Basis: per-frequency cost 0.4 s @2.4k, 2.8 s @5.1k, 7.5 s @7.0k, 45 s @8.9k; 15.7k quarter and 9.2k full OOM.
- **Finding for task 05**: one multi-frequency `solve_frequencies` call falls off a cliff above ~2.4k dofs (689 s at 5.1k; 1,151 s with pipelining off) while 12 separate single-frequency calls take 33 s. The CUDA adapter must loop one frequency per call.
- M4 done: cuda 0.8 s vs cpu 1.45 s per frequency at 2.4k dofs; CPU cold start 3.7 s vs CUDA 29 s. `HORNLAB_BEAT_FORCE_CPU` does not redirect an explicit cuda request.
- First push done: https://github.com/llevaachingada/Hornfab (commit ef30d36).

**Open issues**
1. **Decision needed (task 04 finding):** the baseline seed horn is large (quarter area 0.282 m^2, bbox 0.40 x 0.32 x 0.26 m, vs the plan's 0.125 m^2 assumption). With a 5,000-dof cap, `screen` at f_max 10 kHz is refused (`MeshTooLargeError`); 5,000 quarter dofs buys roughly 6 kHz for this horn. Options: lower `band_hi_hz`/screen grid top, use fewer elements per wavelength in screen (epw 4), or a smaller seed. Not decided; `osse_baseline.yaml` unchanged beyond caps.
2. `config.mesh_spec` uses `ceil(2*cap*qf*slack)` and ignores `dof_per_triangle`, while `sizing.max_triangles_for` uses it (2% apart at 0.51). Task 03 file; fix pending.
4. Task 06 conventions awaiting senior review (half-pressure -6 dB threshold; `di_from_cuts` clamp; ddof=1 ripple).
6. Mesh time: 0.3 s -> 12 s over the f_max range for the baseline horn (task 04 table); mesh fraction of a screening candidate is small versus solve above 5k dofs.

**Next action:** collect task 07; dispatch task 05 (solve) now that the GPU is free of measurements; then task 08 once 04-07 are in.

## 2026-10-12 (night) — clean GPU measurements, Wave 1 started (orchestrator: Claude)

**Done**
- Single session now (a duplicate session had collided on the GPU; it stood down). Added "GPU / Julia hygiene" rules to `AGENTS.md` and `CLAUDE.md` after finding that stale persistent Julia hosts (~1 GB VRAM each) cause false OOMs and worker crashes.
- Clean-state M2/M3/M5/M6 and C1/C2b/C3/C4/C5 measured; `TOOLCHAIN.md` rewritten (see it for every table).
- Remote set: `origin` = https://github.com/llevaachingada/hornfab.git (package/CLI keep the names `hornlab_search` / `hornlab-search`).
- Per user instruction (23:47), Wave 1 started in parallel with the last GPU measurements. Interpretation: "task one" = Wave 1 task 04 and onward. CP-0 gate waived in part: M4 (cpu) and the dof caps are still being settled; recorded as a deviation.
- Task 06 (metrics + targets): DONE, 78 tests pass, CP-4 analytic tables in agent report. Decisions needing senior review (also in `NOTES_FOR_SENIOR.md`): -6 dB threshold implemented as half pressure (-6.0206 dB); `di_from_cuts` clamps sin(bw/2) at 1 and treats saturated cuts as omni; `ripple_db` uses ddof=1.
- Tasks 04 (design+mesh) and 07 (dataset) dispatched; 05 (solve) waits for the GPU job to finish.

**Key measured numbers**
- dof/triangle 0.500 full, ~0.51 quarter.
- Symmetry pairing (clean): full vs quarter max 0.058 dB up to 4 kHz, 0.497 dB at 6 kHz; mismatched run is 12 dB wrong on axis, 54.9 dB max.
- VRAM: operator is dense 8N^2 but the real footprint is 20-40x that. Clean OOM ceilings on the 8 GB RTX 4060 Laptop: full domain 5.5k ok / 9.2k OOM; quarter 8.9k ok (74 s) / 15.7k OOM. **The plan's dof caps (8000/16000/24000) do not hold.**
- Throughput (warm worker, quarter): 2,369 dofs, 12 frequencies + 512-point balloon = **5.0 s**; 5,140 dofs same job = **689 s** (assembly 672 s), and 1,151 s with `BLAB_METAL_PIPELINE=0`; one warm frequency at 5,140 dofs is 3.2 s. A cliff, not a smooth curve. Per-frequency looping test in progress.
- Worker: cold 27 s, warm 1.4 s, after detach 0.84 s.
- Traces: 111,280 bytes per frequency at 2,369 dofs. Balloon grid theta 0-180, phi 0-348.75, shape (F, 512).
- Impedance BC: bempp only.

**Open issues / blockers**
1. `gh` is not authenticated: labels and GitHub issues cannot be created yet. Issue bodies are drafted in `.github/issues/`. (`git push` may work through the credential manager.)
2. M4 (CPU vs CUDA): CPU backend unprovisioned; to attempt once the GPU is free.
3. dof caps in the YAMLs (8000/16000/24000) are unsafe; provisional replacement pending the per-frequency loop result.
4. Plan drift: `SolveResult` (not `Response`) and `mesh_info.n_vertices` (not `p1_dof_count`): task 05 must adapt.
5. Mesh time and mesh fraction of a candidate not yet measured.

**Next action:** collect agent reports for 04 and 07; run M4 CPU provisioning; dispatch task 05 (solve) when the GPU is free; set dof caps; commit and push.

## 2026-10-12 — Wave 0 scaffold + CP-1 green (session 2)

**Done**
- `gh` installed (v2.102.0); **not** authenticated.
- Wrote owner-03 files: `pyproject.toml` (real SHAs, `pythonpath=["."]`), `.gitignore`, `README.md`, `hornlab_search/__init__.py`, `hornlab_search/cli.py` (`doctor`+`version`), `examples/icw_termination.yaml`, `examples/freeform_hv.yaml`, `examples/search_smoke.yaml`, `.github/workflows/ci.yml`.
- `pip install -e ".[dev,crosscheck]"` succeeds (pytest 9.1.1, pyyaml, cma, jinja2 present).
- First mesh + solve: 1419 verts / 2834 tris; cold 24.618 s, warm 0.494 s. Real schema is `SolveResult` (not the plan's `Response`).
- M1 calibration, M6 symmetry, M7 max_triangles measured (see `TOOLCHAIN.md`). C1–C5 answered from source.

**Pasted CP-1 output**

`pytest -q`:
```
..................                                                       [100%]
```

`hornlab-search doctor`:
```
PASS  python-version    Python 3.12.10 in [3.11, 3.14)
PASS  core-imports      numpy, scipy, cma, yaml, jinja2
PASS  hornlab-imports   mesher, beat, plots; bempp yes
PASS  pinned-shas       all installed SHAs match pyproject.toml
PASS  toolchain         TOOLCHAIN.md present, dof_per_triangle=0.51
PASS  gpu               nvidia-smi exits 0
PASS  backend           beat_cuda functional (state=ready)
PASS  configs           all 5 example configs load
PASS  round-trip        reserved for task 04
```

`hornlab-search version`:
```
0.1.0
```

**Open CP-0 items:** M2 (VRAM vs dofs + dof ceiling), M3 (s/person-candidate), M4 (cuda vs cpu), M5 (after-detach). All blocked on exclusive GPU access.

**Next action:** dispatch the Wave 1 issues in parallel using the prompt template in `docs/plan/00_ORCHESTRATOR.md` — **only after** CP-0 is completed on a clean GPU and the repo is pushed.
