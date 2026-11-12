# Council review handoff — data-analysis / GA plan (2026-11-12)

**Purpose:** hand this file to an independent senior review board (council) so it can harden the saved research plan and produce a senior-reviewed implementation plan for the major high-value items. The orchestrator is skipping its own council pass; this handoff is self-contained.

**Status of the repo at handoff:** `origin/main` = **15644ca** (PR #47 merged: the measured v8 tolerances + brief §4; PR #46, this plan/handoff, is open). PR #25 is open and must merge last. No queue or code changes are part of this handoff.

---

## 1. Read these first (correct folders)

**The plan under review**
- `C:\Users\hunte\Hrns\oc-wt\DOCS\docs\research\DATA_GA_RESEARCH_PLAN_2026-11-12.md` — the raw research plan. It already has a "Known corrections at save time" section; verify the rest.

**Authoritative plans/context**
- `C:\Users\hunte\Hrns\oc-wt\plan\docs\IMPLEMENTATION_PLAN_2026-11-12_DAY.md` — the day plan (groups A–F, §5 amendments, group G).
- `C:\Users\hunte\Hrns\oc-wt\plan\docs\SENIOR_PLAN_2026-11-12.md` and `OPENCODE_HANDOFF_2026-11-12.md`.
- `C:\Users\hunte\Hrns\oc-wt\DOCS\docs\CONTINUITY.md` (top ~170 lines), `docs/ISSUES.md`, `docs/NEXT_DEV_PRIORITIES.md`, `docs/CODE_MAP.md`, `docs/INDEX.md`.
- `docs/research/SEARCH_MATH_DOSSIER_2026-11.md` (group R), `docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md` (merged but §4 is a placeholder), `docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md`, `docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md`.
- `docs/evidence/THROUGHPUT_N1_2026-11-12.md`, the A/B/C/D/G evidence already on main.

**Implementation to check**
- `tools/analysis/**` (schema.md, convergence, seed_variance, sensitivity, links, walls, ab_compare, lane_parity, term_balance, fidelity, report_day, specs/day_2026-11-12.yaml).
- `tools/calibration/**`, `tools/night_report.py`, `tools/night_status.py`, `tools/data/merge_lane_dataset.py`.
- `hornlab_search/search/{warmstart.py, links.py, pin_from_cma.py, cma.py, cma_me.py, evaluate.py}`, `hornlab_search/config.py` (the B keys), `hornlab_search/objective/scalar_v8.py`, `hornlab_search/gui/{data.py, static/app.js, server.py}`.
- `docs/reference/PARAMETERS.md` (the B search-key sections).

**Data / evidence (read-only)**
- Live checkout (do not edit): `C:\Users\hunte\Hrns\hornlab-search` — `runs/`, `dataset/`, `dataset_cpu/`, `cache/`, `cache_cpu/`.
- `runs/nights/*/summary.jsonl`, queue logs, `runs/nights/gpu_day_2026-11-12_cont.yaml` (the remaining GPU jobs).
- `C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\` (A.8 partial, 13 sections ok) and `NIGHT_partial.md`.
- `C:\Users\hunte\Hrns\oc-wt\G\scratch\lane_parity_2026-11-12\report\` (A.7 PASS).
- `C:\Users\hunte\Hrns\oc-wt\G\scratch\objective_v8_full_2026-11-12\{v8_rescore.json,v8_rescore.md}` (full re-score).
- `C:\Users\hunte\Hrns\study_2026-11-12\` (`COMPUTE_STUDY.md`, `runs_inventory.csv`, `sensitivity_analysis.py`; outside the repo).

## 2. Worktrees the review must classify

`git worktree list` at handoff:

```
C:/Users/hunte/Hrns/hornlab-search  79edc8d [day/2026-11-12-queue]   (live; do not touch)
C:/Users/hunte/Hrns/oc-wt/A         7092df7 [fix/run-cli-portable-interpreter]
C:/Users/hunte/Hrns/oc-wt/AN        1837f02 [day/AN-analysis-2026-11-12]
C:/Users/hunte/Hrns/oc-wt/B         88ddb8d [day/B-search-features]
C:/Users/hunte/Hrns/oc-wt/C         55482f5 [day/C-calibration]
C:/Users/hunte/Hrns/oc-wt/D         b8dc237 [day/D-night-ops]
C:/Users/hunte/Hrns/oc-wt/E         6bf52a2 [day/E-gui]
C:/Users/hunte/Hrns/oc-wt/F         b458fa2 [day/F-docs-hygiene]
C:/Users/hunte/Hrns/oc-wt/G         9bbf249 [day/G-objective-v8]
C:/Users/hunte/Hrns/oc-wt/gui-a     ceb962d [feat/gui-verify-ui]
C:/Users/hunte/Hrns/oc-wt/gui-b     18ab502 [feat/gui-charts-history]
C:/Users/hunte/Hrns/oc-wt/gui-c     22c7ece [feat/gui-shell]
C:/Users/hunte/Hrns/oc-wt/gui-int   22ac0d2 [feat/gui-integration]
C:/Users/hunte/Hrns/oc-wt/gui-wp01  b2dc507 [feat/gui-verify-wp0-wp1]
C:/Users/hunte/Hrns/oc-wt/gui-wp2   fe6edd9 [feat/gui-perf-wp2]
C:/Users/hunte/Hrns/oc-wt/L1        e1d4e59 [lane/L1-cpu-lane]
C:/Users/hunte/Hrns/oc-wt/L4        e7ce42c [lane/L4-hygiene]
C:/Users/hunte/Hrns/oc-wt/plan      90b9a49 [plan/day-hardening-2026-11-12]
C:/Users/hunte/Hrns/oc-wt/R         fedbc4a [day/R-research-dossier]
C:/Users/hunte/Hrns/oc-wt/T         a886538 [docs/gui-verify-view-plan]
C:/Users/hunte/Hrns/oc-wt/V         f210d3c [fix/verify-backend-dir]
C:/Users/hunte/Hrns/oc-wt/DOCS      <branch docs/data-ga-plan-2026-11-12-v2>
```

Classify each: ancestor of `origin/main` (merged), unmerged, WIP, stale, or unsafe. The research plan's inventory did **not** cover `gui-*`, `T`, or `DOCS`; that is part of the hardening.

## 3. Verified state to check, not trust blindly

- `origin/main` = **15644ca**; PR #46 (this plan/handoff) open; PR #25 (`lane/L4-hygiene`, head e7ce42c) open and must merge **last**; PR #32 (plan doc) is not ours.
- Day groups A–G/R and fix #44 are ancestors of main. The live checkout is on `day/2026-11-12-queue` at **79edc8d**, which is **not** on main; `d638231` **is** on main. The live tree lacks `tools/analysis/**` and the B features — run analyses from a main-synced worktree (`AN` is at 1837f02; `G2` is at 1837f02 + the merged G follow-up; use a fresh worktree from 15644ca for new work).
- F.1 continuity reorder: `docs/history/continuity_reorder_2026-11-12.patch` is on main but **not applied**; `docs/history/CONTINUITY_2026-10-22_2026-10-31.md` is absent.
- G: **the follow-up landed in PR #47 (15644ca)** — `V8_MEASURED_TOLERANCES` now has the full-dataset per-class values, brief §4 has the counters/tolerance/tau tables and the class-B caveat, and a regression test pins them. v8 remains unregistered. The full re-score: `rows_seen=23833`, `scored=23833`; class A 18,145 rows/0 refusals, τ v4 **0.5004** (top20 4/20), v7 0.4394 (3/20), v6 0.0138 (0/20); class B 4,063 rows/**3,545 refusals (87%)**/518 rankable, τ v4 0.7687 (0/20), v7 0.6719 (0/20), v6 0.2174 (7/20); class C 1,625 rows/0 refusals, τ v4 **0.8150** (13/20), v7 0.8104 (0/20), v6 0.0086 (0/20). Per-class tolerances are in the JSON.
- A.7 lane parity: **PASS** 5/5 designs ≤0.2 dB (max 0.0356 dB), reconstructed from `cache_cpu`/`cache` after the pre-#44 shared-verify collision.
- A.8 partial: 13/13 sections ok; fidelity g1 median screen bias **29.2%**, Spearman 0.66 all / **0.50 top-5**; v6 2-seed spread **0.704** (not a verdict); links candidate R² **0.427** (do not ship); g6 walls `g_fc_hz` 87% lo / `g_stop_deg` 87% hi.
- CPU lane idle since 15:15; `c2b` exited 1 after **2 BEAT worker `ConnectionResetError`** failures (the night report's `blocked` label is the CPU lane's expected GPU-busy hygiene line, not a GPU issue). GPU continuation queue is still running `g2_core_law_seed1031`; `g3`–`g9` remain per `runs/nights/gpu_day_2026-11-12_cont.yaml`.
- Full suites on the G/fix branches: 2849/1/2 and 2814/1/2; the one failure is a load-sensitive 100 ms assert in `tests/test_mesh_build.py` that passes in isolation; CI green on the merged fix head.
- **Freeform_sculpt seed census (now verified):** the equal-budget group is **25 seeds 5101–5125** (151 rows each), not 26; the 26th run (`20261023T201245Z-screen-32f5b5`, seed 1234) is a 777-row base at a different budget. The clean 25-seed A.2 result: median best J **18.589**, spread **4.780** (25.7% of median), bootstrap 95% CI [18.413, 19.186]; the 26-seed mixed-budget group gives spread 6.213 and is not a seed-variance estimate. Outputs: `oc-wt/AN/scratch/seedvar_freeform25eq/` and `...26b/`. The reviewer should use the 25-seed group.

## 4. The review task

### Part 1 — harden/review the saved plan
- Fact-check the plan's claims against the repo/worktrees/data: merge state, paths, line numbers, PRs, test counts, data counts, tool capabilities, the "26-seed freeform_sculpt" group, the staged A/B state, the GUI analysis page, CLI flags, the v8 numbers, CPU/GPU rates.
- Flag errors, overclaims, stale assertions, missing worktrees (`gui-*`, `T`, `DOCS`), missing dependencies, sequencing/merge conflicts, data-integrity risks (mixed verify dirs, lane provenance, tolerance circularity), CPU/GPU constraints, and anything that would fail in practice.
- Say which plan items are **not worth doing now** (noise, low value, blocked, owner-only) and why.

### Part 2 — senior-reviewed implementation plan
Do not restate the research plan. Prioritize ruthlessly and make it executable. Structure:
- **Executive decision:** the top 3–5 things worth doing now; what to defer.
- **Phase 0 — correctness/foundation:** G follow-up (real tolerances + brief §4 + a regression test against the placeholder table); AN evidence policy; PR #46. Exact files/commands/acceptance/tests/merge gates.
- **Phase 1 — CPU-only work that can start now** (GPU queue untouched): 26-seed variance/power, walls census across families, fidelity census, LQModel offline τ proof, `dataset_cpu` D.3 dry-run, calibration-night preparation, cross-run sweep refresh. For each: inputs, exact command (`PY = C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`), runtime/cores, outputs, acceptance criteria, decision informed. Cut weak items.
- **Phase 2 — after the GPU queue finishes:** final A.8/report_day fill + PNGs, A.6 `ab_compare` narrow-vs-control and staged-vs-joint, `NIGHT_2026-11-12.md`, A.7 evidence, D.3 dry-run→apply decision.
- **Phase 3 — close-out:** PR #25 **last**, F.1 reorder patch, pull main in the live checkout, worktree hygiene; exact gates.
- **Phase 4 — owner-gated next steps:** calibration night, warm starts, narrow/widen, valid-only budget/resample, restarts, CMA-MAE, screen grid, v8 adoption; only high-value, with prerequisites and decisions.
- **DO NOT DO** list: no live queue edits, no GPU solves from workers, no default flips, no v8 registration, no unmerged-worktree assumptions, no dataset merge without owner sign-off.
- For every work item: owner/agent, files, commands, acceptance, tests/evidence, dependencies/blocked-by, risk, merge gate.
- A short **review verdict**: what changed from the research plan, residual unknowns, owner decisions.

## 5. Suggested council procedure (if using one)

1. Dispatch this handoff + the plan path to every council seat in parallel; each seat returns factual corrections, a hardening verdict, and a critique of the proposed implementation plan.
2. Collect responses; retry an empty seat once; do not wait on stragglers.
3. Synthesize with a council chair into one hardened review + implementation plan. Preserve disagreements explicitly.
4. Do not let any seat edit, commit, run GPU/solves, or touch the live checkout/queues.

## 6. Output to save

Save the final review + implementation plan as `docs/research/COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md` (plus an INDEX row), or return it to the orchestrator for saving. Use `[measured]` labels and file:line/SHA/PR references. Do not invent values; if a claim cannot be verified, say so.

---

**Do not touch:** the live checkout working tree, `runs/`, `cache*/`, `dataset*/`, the queues, PR #25, or any unmerged branch. This is read-only research/review.
