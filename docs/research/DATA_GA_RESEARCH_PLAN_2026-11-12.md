# Data analysis, GA improvement, and dataset-exploitation research plan (2026-11-12)

**Status:** RAW research plan — pending senior hardening/review. Saved verbatim from the research pass so it is durable.
**Author:** research pass (oracle), 2026-11-12. **Saved by:** orchestrator.
**Scope:** inventory of today's data-analysis/GA work across the worktrees; dataset exploitation (warm starts, links, walls/narrow, sensitivity/term balance, seed variance, fidelity, v8); seed/parameter discovery; visualization; a ranked CPU-only work queue; merge dependencies; owner decisions.

## Known corrections / notes added at save time (verified)

- **c2b is not a GPU-busy failure.** The CPU continuation's `c2b_verify_core_law_top10` exited 1 after **2 BEAT worker `ConnectionResetError(10054)` failures** (designs `abca65c68a1a`, `8c42018fe94a`). The night report's `blocked` status comes from the CPU lane's expected "GPU busy" pre-hygiene line (D.2 classification), not from a GPU problem. Its 8 successful per-backend responses were salvaged for A.7.
- **Full worktree inventory at save time** (the research plan focused on the day groups): `A, AN, B, C, D, E, F, G, gui-a, gui-b, gui-c, gui-int, gui-wp01, gui-wp2, L1, L4, plan, R, T, V` plus the live checkout. The extra `gui-*` worktrees and `T` were not inventoried by the research pass; the review must classify them.
- **Paths:** the compute study is `C:\Users\hunte\Hrns\study_2026-11-12\` (outside the repo; `runs_inventory.csv`, `COMPUTE_STUDY.md` exist there).
- **Live checkout** is on `day/2026-11-12-queue` (79edc8d); it lacks `tools/analysis/**` and the B search features (those are on main). Run analyses from a main-synced worktree (e.g. `oc-wt\AN`).
- **Merge state verified:** `origin/main` = 1837f02; `d638231` is on main; `79edc8d` is not; PR #25 open; the F reorder patch exists on main but is **not applied**, and `docs/history/CONTINUITY_2026-10-22_2026-10-31.md` is absent.
- **v8 full re-score verified** (finished 16:01:47, `oc-wt\G\scratch\objective_v8_full_2026-11-12`): `rows_seen=23833`, `scored=23833`; class A 18,145 rows / 0 refusals; class B 4,063 rows / **3,545 refusals (87%)** / 518 rankable; class C 1,625 rows / 0 refusals. Per-class calibrated tolerances and τ/top-20 tables are in §A below; the merged brief §4 and `V8_MEASURED_TOLERANCES` are still placeholders and need the follow-up.

---

All research is complete. Here is the consolidated plan.

# Research plan — what today's data-analysis/GA work is real, and what to do next (2026-11-12)

## 0. Verified ground truth (branch/queue state)

- `origin/main` = **1837f02** (merge PR #44, 2026-11-12 15:45 ET — *after* the brief's "last check"). PR #44 (fix/verify-backend-dir) and #45 (GUI verify view plan) are merged.
- **Correction to the brief:** day worktrees A–G, R and fix #44 heads are **all ancestors of origin/main** (verified with `git merge-base --is-ancestor`): A=7092df7, B=88ddb8d, C=55482f5, D=b8dc237, E=6bf52a2, F=b458fa2, G=9bbf249, R=fedbc4a, V=f210d3c → MERGED. Queue commit **d638231 is already on main** (it rode in with PR #29 / lane L1); only the GUI commit **79edc8d is not on main**.
- Live checkout `hornlab-search` is on `day/2026-11-12-queue`, clean except untracked `cache_cpu/`, `dataset_cpu/`. **Important consequence:** the live working tree does *not* contain `tools/analysis/**` or the B features — those exist only on main (readable/runnable from worktrees, e.g. `oc-wt\AN`, which sits exactly on 1837f02).
- Open PRs: **#25** (lane/L4-hygiene, head e7ce42c, NOT merged), **#32** (plan doc, not ours). Uncommitted work: **AN worktree** has a modified `tools/analysis/specs/day_2026-11-12.yaml` (partial fill; branch has no commits) + `oc-wt\AN\scratch\report_day_partial\*` + `NIGHT_partial.md`. G worktree has uncommitted scratch incl. the just-finished v8 full re-score.
- **Queues (read-only check):** GPU cont night is **still running** job `g2_core_law_seed1031` (started 15:02 local; mesher warnings logged through 15:57); remaining after g2: g3 (narrow), g4 (control 1235), g5 (staged A/B), g6/g7 (v6 resume + seed 1235), g8/g9 (atlas resumes) per `runs\nights\gpu_day_2026-11-12_cont.yaml`. **CPU lane is idle since 15:15 local** (cont queue done: c1b verify ath_core ok 18 evals; c2b blocked exit 1 by "GPU busy" — the D.2 `blocked` classification worked as designed; its rows were salvaged for A.7 via `oc-wt\G\scratch\salvage_lane_parity.py`).
- **Data:** `dataset/` 57 shards, **28,414 rows**; `dataset_cpu/` 1 shard, **237 rows**; `runs/` **416** run dirs, **34,892 ndjson rows**; `runs/staged_ab_2026-11-12/` exists (Stage A configs + COMPARE.md from the fixed rerun; the *night* n7 job failed in 2 s, g5 pending). `runs/analysis/` does not exist yet.

---

## A. INVENTORY (what shipped, merged?, wired vs opt-in vs proposal)

| Group | PR | What shipped | Merged? | Status in product |
|---|---|---|---|---|
| **A** analysis toolkit | #38 (+CI #39/#41) | `tools/analysis/*`: convergence, seed_variance, sensitivity, links, walls, ab_compare, lane_parity, term_balance, fidelity, report_day + `specs/day_2026-11-12.yaml` + `schema.md` (A.0 contract) | ✅ | **Wired as standalone read-only CLI tools** (used by AN today); not invoked automatically by anything — `runs/analysis/` target folder doesn't exist yet. 75 targeted tests. |
| **B** search features | #40 | B.1 `search.warm_start` (`search/warmstart.py`), B.2 `search.links` (`search/links.py`), B.3 `hornlab-search narrow --run [--widen]` (`pin_from_cma.py`), B.4 `budget_counts: valid`+`max_attempts`, B.5 `gates: round_throat`, B.6 `infeasible_penalty: resample`, B.7 `surrogate: lq`, B.8 `search.qd.maes` (CMA-MAE) | ✅ | **All opt-in via config keys** (`config.py:118-130`); defaults unchanged (goldens 78ed1f4 hold). Docs at `docs/reference/PARAMETERS.md:10206-10328`. Not yet used by any shipped night config. Notes: B.6 incompatible with cma_me (ConfigError); B.7 unproven on our data (see E-queue item); B.8 needs the ribs CMA-MAE recipe. |
| **C** calibration + throughput | #37 | `tools/calibration/plan_calibration.py` (C.1), `compare_calibration.py` (C.2), `docs/evidence/THROUGHPUT_N1_2026-11-12.md` (C.3/C.4) | ✅ | Harness wired (generates night YAML + overlays); C.3 recommendation **proposal-only** (fused ON / prefetch OFF ≥8k / `freq_batch_size` 12 — no config key yet, env `HORNLAB_FREQ_BATCH_SIZE`); C.4 screen-grid fix proposal-only; **defaults not flipped** (owner-gated). |
| **D** night/data ops | #35 | Two-lane `night_status.py`, runner robustness (blocked+retry, `--dry-run`, lane/backend rows), `tools/data/merge_lane_dataset.py` (D.3, dry-run default, parity-gated), `tools/night_report.py` (D.4) | ✅ | **Wired; proven live today** — D.2 correctly labeled c2b "blocked"; night_report produced `NIGHT_partial.md` over 5 nights. D.3 ready but **not executed** (owner decision). |
| **E** GUI | #36 | `#/analysis` page (renders A-tool JSONs, `gui/data.py::analysis_sets` :3300 / `analysis_report` :3338, `app.js::viewAnalysis` :2240), lanes panel (`/api/lanes`, `data.py::lane_status` :3223), `#/elites` (`viewElites` :2355) | ✅ | **Wired read-only**; degrades to "not present" when no analysis outputs exist — none exist yet under `runs/analysis/`, so the page is currently empty. |
| **F** docs hygiene | #33 | NEXT_DEV_PRIORITIES P15/P14 status, SENIOR_PLAN WP status column, **CONTINUITY reorder produced as patch only** (`docs/history/continuity_reorder_2026-11-12.patch`, commit 4faf67d) | ✅ (patch **not yet applied**) | The reorder must still be applied by the orchestrator "LAST" (2026-10-31 entries are still inside CONTINUITY.md; `docs/history/CONTINUITY_2026-10-22_2026-10-31.md` absent on main). **Still pending.** |
| **G** objective v8 | #43 | `objective/scalar_v8.py` (unregistered scorer), `tools/analysis/v8_rescore.py`, owner brief `docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md`, + merged PR #42 (test-suite efficiency review, proposal-only, 122 CI runs→~140 expected) | ✅ | **Proposal only, correctly gated**: `versions.py` still 1–7; no brief uses v8. **Two known incompletenesses**: (1) `scalar_v8.py:126-130` `V8_MEASURED_TOLERANCES` = **all 1.0 placeholders** ("PLACEHOLDER-PROVENANCE" at :125); (2) brief §4 is the `<!-- V8_RESULTS -->` placeholder. The **full re-score finished at 16:01 today** in `oc-wt\G\scratch\objective_v8_full_2026-11-12\{v8_rescore.json,md}` (uncommitted) — see below for its numbers; folding them in is the G follow-up. |
| **R** research dossier | #34 | `docs/research/SEARCH_MATH_DOSSIER_2026-11.md` — 10 sections, ranked change table 1–12, honest `[TO-VERIFY]` index | ✅ | **Design dossier only** (as intended); no code. It is the source for B.6–B.9 and the v8 recipe. |
| **fix #44** verify per-backend dirs | #44 | `verify --verify-dir PATH`; other-backend override → own run dir (`verify_of.backend`); refuses mixing | ✅ | Wired; tonight's `c2b`/`g1c` ran with the *old* code and their `verify/` dirs are mixed — A.7 was still obtained from `cache_cpu`/`cache` salvage (see risk R-2). |
| — GUI verify view | #45 | `docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md` | ✅ (plan doc merged) | **Plan only, zero GUI code.** 6 shippable slices defined (§8). |
| — **AN** (uncommitted) | none | AN worktree: partial spec fill + `scratch/report_day_partial/` (13 A.8 sections ok) + `NIGHT_partial.md` | ❌ | Needs an evidence PR (see F). |

**Partial evidence numbers already produced (cited):**
- A.7 lane parity GPU↔CPU: **PASS, 5/5 designs ≤0.2 dB** (max |dSPL| **0.0356 dB**, |dJ| ≤ 3.4e-5) — `oc-wt\G\scratch\lane_parity_2026-11-12\report\lane_parity.{md,json}` (salvage from cache, pre-#44 code).
- A.8 partial (13 sections ok), `oc-wt\AN\scratch\report_day_partial\REPORT.md`: g1 core_law 1001 rows/567 valid, refusal rate oscillating **0.32–0.64/window**, best J 2.1283, **still improving** in last 20% (+7.85% headroom); g9 ath_core converged (2.0987, 1326 rows); g8 ext-throat converged but only 5/324 cells filled; v6 2-seed spread **0.704** (1.5356 vs 0.8319), normalized best-design distance 0.574; sensitivity g1: `L_mm` ρ=−0.705 (top-decile mean shift 0.220 — best designs ~309 mm vs 218 mm overall), RF R² OOS 0.49; g6: `g_fc_hz` importance 1.689, R² 0.97; links g1: one candidate `az_a_sf_amp = −0.6127·a_deg + 24.12` **R² 0.427 — below the plan's 0.8 bar, do not ship**; walls g6: `g_fc_hz` 87% at lo, `g_stop_deg` 87% at hi → widen candidates; g1: no 50% walls but 9 narrow-bound proposals; term_balance g1: cov 0.337 / dislope 0.305 / rip 0.008 (weight 1.0 again ≠ influence); **fidelity g1: median screen bias 29.2%, Spearman all 0.66, top-5 0.50** (12 pairs).
- v8 full re-score (fresh, 16:01 today, 23,833 rows): calibrated tolerances per class (A: cov 8.758, rip 0.4219, diag 8.746, dislope 0.174; B: cov 22.72; C: cov 14.38); **Kendall τ v8-vs-v4: A 0.500 (top-20 overlap 4/20), B 0.769 (0/20), C 0.815 (0/20)**; **class B: 3,545/4,063 rows (87%) refused by v8's hard loading/f11 gates** (the archive was v4/v7-searched without gates), only 518 B rows remain rankable. This is *the* headline adoption fact: v8 is a different ruler, and its gates would reject most of today's class-B archive.
- N1 throughput (throughput evidence doc): b12 fused-on warm **1.27 s (1k) / 8.49 s (4k) / 25.0 s (8k)**; fused-off at 8k fails every warm rep (peak 7,499–7,731 MiB OOM); `freq_batch_size` 12 = 4.7×/2.1×/1.9× vs b1.

---

## E. CPU-ONLY WORK QUEUE (ranked; can run on the idle CPU lane now unless noted)

`PY = C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`. Analysis tools import `_common` from their own directory — run them **from a main-synced worktree** (`oc-wt\AN` or a fresh one at 1837f02), pointing inputs at the live checkout read-only, writing `--out` into the worktree's `scratch\`. None of these touch the GPU or the queues. None need a GPU solve.

| # | Task (can-run-now unless marked) | Command | Cost | Answers |
|---|---|---|---|---|
| 1 | **Commit & land the AN evidence** (spec partial fill + 13-section REPORT + NIGHT_partial as `docs/evidence/DAY_2026-11-12_ANALYSIS.md`) | new branch from AN; see §F | min | Makes today's analysis real instead of scratch-only. |
| 2 | **Seed-group statistics on the stored 26-seed freeform_sculpt group** (only verdict-eligible group; compute paired-σ, bootstrap CI, ECDF) | `PY tools\analysis\seed_variance.py --group fs=runs\<26 dirs from study_2026-11-12\runs_inventory.csv (cma_seed col)> --out scratch\seedvar_freeform26` (dirs listed per seed in the inventory) | <2 min, ~1 core | Gives the paired-σ for §8's power formula; sets the standard for every future "A beats B". |
| 3 | **Walls across ALL runs of a family** → pin/narrow/widen list | loop `walls.py --run <dir> --out …` over `runs_inventory.csv` rows per family/config, then aggregate (tiny PowerShell/python loop, read-only) | ~min/run; ~1–2 h for 414 dirs | Which knobs sit at bounds in >50% of runs (morph_fixed 32/51, tmax 11/22 known) → B.3 pin candidates + tonight's g3/g4 A/B context. |
| 4 | **Fidelity census over every run with `verify/` rows** (currently: fbab4f 12 pairs, 377bbe, elites_20261030_hypex 34 verified) | loop `fidelity.py --run <dir>` over the ~5 verify-bearing runs; NOTE: fbab4f's verify dir is backend-mixed (pre-#44) — restrict to same-backend pairs or use the G salvage layout | <5 min | Decides C.4's top-k: is top-5 Spearman stable at 0.5, or worse elsewhere? Directly informs "verify top 15–20, rank by verify J only". |
| 5 | **dataset_cpu mining + D.3 dry-run** (parity report already exists) | `PY tools\data\merge_lane_dataset.py --src dataset_cpu --dst dataset --parity C:\...\oc-wt\G\scratch\lane_parity_2026-11-12\report\lane_parity.json` (dry-run default; NO `--apply`) | min | Prove the 237 CPU rows (lane-tagged) would merge cleanly; the actual merge is owner-GO + after the GPU queue ends. |
| 6 | **v6 tolerance recalibration proposal** (v6's "physical-ish" tolerances, `scalar_v6.py:49-59`, upgraded to measured top-decile medians) | reuse `v8_rescore.py`'s calibration section / `term_balance.py` on the v6 runs; produce a table; **needs a small script** (new code, no merges) | ~30 min | Fixes v6's `di_rise` 0.758 share vs `load_near` 0.00 (measured today, g6 term_balance). |
| 7 | **LQModel offline replay (B.7 proof-gate)** — dossier §2/Q11's τ≥0.85 test before any `search.surrogate: lq` GPU A/B | small script fitting `cma.fitness_models.LQModel` on archived (x→J) rows of one config (`runs\20261030T111108Z-screen-377bbe` 1,141 valid rows), CV Kendall τ | ~30 min, 1 core | If τ < 0.85 on our own landscape → kill B.7 without spending a GPU night. Uses installed pycma only. |
| 8 | **v8 follow-up fold-in (code+doc, owner-gated)**: put the finished re-score into §4 + real tolerances into `V8_MEASURED_TOLERANCES` | edit `scalar_v8.py:126-130` + brief §4 from `G\scratch\objective_v8_full_2026-11-12\*` | ~1 h (needs a PR) | Replaces the 1.0 placeholders; keeps v8 offline-only pending owner sign-off. |
| 9 | **Calibration night prep**: generate the runnable night file now (no GPU to *generate*) | `PY tools\calibration\plan_calibration.py --designs runs\elites_20261030_hypex runs\elites_20261030_core_law … --top 6 --list-only` then `--out runs\nights\n2_calibration_next.yaml` | min | Unblocks the owner's next-night GO (P0 item 2). The night itself needs the GPU lane (after today's queue). |
| 10 | **Cross-run dataset sweep refresh** (inventory is 414 → regenerate over 416 dirs incl. today's g1b/c2) | `PY C:\Users\hunte\Hrns\study_2026-11-12\analyze_runs.py` (writes only into `study_2026-11-12`, outside the repo) | ~10–20 min, 1 core | Updates still-improving / coverage / wall tables with today's rows. |
| 11 | *(after GPU queue ends ~several hours)* **report_day final fill** + A.6 ab_compare (g3 narrow vs g4 control; g5 staged A/B), then D.3 apply + PR #25 + reorder patch, per day-plan §3 | fill `specs/day_2026-11-12.yaml` (g2-g7, g5) → `PY tools\analysis\report_day.py --spec … --out runs\analysis\day_2026-11-12`; `PY tools\analysis\ab_compare.py --a <g3 dir> --b <g4 dir> …` | minutes each | The two decisive A/Bs (narrow-vs-control; staged-vs-joint) with A.2's spread rule. |

**Measured CPU-lane rates to size nights:** v6 CMA `screen` on CPU ≈ **543–585 evals/h** (c2: 200 evals/20.5 min); CPU verify ≈ **40–70 designs/h** for ~7k-dof designs (c1b, c3, c2b). GPU screen today: ~561 evals/h for core_law (incl. 43% refusals) — CPU and GPU screen rates are comparable at these sizes, which is why the parity result matters.

---

## B. DATASET EXPLOITATION — prioritized plan for the existing archive

Ordered by expected value ÷ cost. "Now" = read-only/CPU-only with tools on main (see §E commands); "code" = small new script/tool; "GPU/night" = needs next night or owner GO.

1. **Verify-driven finalist policy (A.10/C.4) — highest-certainty win, config + workflow only.** Data: every run with `verify/` rows (already ≥4 runs). Tool: `tools/analysis/fidelity.py`; evidence: 95%-worse / top-5 ρ 0.1–0.3 (senior) and today's g1 ρ=0.50. Action: verify top 15–20 per run, rank by verify J only; make every leaderboard say its fidelity tier (the #45 GUI plan's slice 1 is exactly this). Verify: re-run fidelity per campaign; ρ<0.3 flags a grid problem, not a finalist problem. **Now** (§E-4) + next-night policy.
2. **v8 decision package (G follow-up + owner sign-off).** Data: whole `dataset/` (23,833 rows scored today). Tool: `v8_rescore.py` (finished). Missing: fold numbers into code/doc (§E-8); owner must decide whether class B's 87% hard-refusal rate is acceptable (it is the *point* of gates, but it re-frames the entire B archive). Adoption path is written already (brief §5: paired-seed A/B ≥5 seeds before any brief flips). **Code + owner.**
3. **Warm starts (B.1) — data-backed seed selection.** Data: any finished run of same family+knots; the tool accepts `from_runs` and refuses cross-version/brief. From today: core_law resume already proves resume-replay works; seed warm start would start at the 2.1283 design. Missing: nothing in code; missing in *practice* — no shipped config uses it. Expected gain (S2-flavored): 10–30% better best-J at 150 evals. Risk: mode-collapse in re-seeds — keep 1 of N cold. Verify: 5-seed paired A/B cold vs warm (next night). **Now to prepare, GPU to measure.**
4. **Walls → narrow/widen/pin (B.3 + A.5).** Data: runs per family; g6's 87%-at-both-ends box is the ready-made case (`walls_g6` proposes widen_lo `g_fc_hz`→540 and widen_hi `g_stop_deg`→264). Tool: `hornlab-search narrow --run <dir> [--widen]` writes a config with *only* bound changes. Verify: g3 narrow vs g4 control runs land tonight — then `ab_compare.py`. **Now (analyze) + GPU (g3/g4 already queued tonight).**
5. **Sensitivity → knob reduction & pins (A.3 + senior §5).** g1: `L_mm` dominates (ρ −0.705, perm-importance 1.276); 9 knobs ≈ 0 importance → pin/narrow candidates for 2-stage searches (P0 item 4: "1–4 knobs carry ~80% of J"). Verify: a narrowed 5-knob config vs full 17-knob at equal budget, ≥5 seeds. **Now (analyze) + GPU (next night).**
6. **Feasibility resampling (B.6) — budget recovery.** Data: g1's measured 32–64% refusal windows; 43% of fbab4f's rows are refusals → `budget_counts: valid` would buy ~1.75× more real evals at the same wall time. Config-only for cma runs (`search.budget_counts: valid, max_attempts: 4×`) or `infeasible_penalty: resample`. Verify: rerun one archived config with valid-budget and compare A.1 refusal windows + best J. **Prepare now; measure on GPU next night.**
7. **Restarts (B.9 / dossier #2).** `search.restarts: {mode: bipop, max: 3}` is already implemented and off; justified by 26–59% seed spread and "still improving" runs (g1 today +7.85% at end). Verify: per-restart `restarts` entries + paired-seed A/B. **Config-only, next night.**
8. **CMA-MAE (B.8) for the atlas cells.** Coverage is 5–31/324 cells across four atlas configs (study §2c) — atlas runs are *sampling*, not converging; CMA-MAE (`qd.maes`, lr 0.05) + no emitter bounds addresses the measured bound-resampling distortion. Risks: another hyperparameter (α), one bounded code path already shipped. Verify: budget-matched cma_me vs cma_mae, 3 seeds, QD score/coverage. **Opt-in; needs GPU.**
9. **Dataset_cpu merge (D.3).** Parity PASSES (0.0356 dB max). `merge_lane_dataset.py --parity … --apply` after the queues end. Owner decision (tag provenance `lane: cpu`). **Dry-run now, apply = owner GO.**
10. **Screen-grid enrichment (C.4/R-7):** `grid.screen_extra_hz` mid-band points already exist (`config.py:344-358, 367-371`) and address the 2.5–5.5 kHz aliasing that produces the 29.2% bias. Config-only; verify with A.10 ρ before/after on stored finalists. **Owner GO (changes solve-cache validity — schedule with the calibration night, not mid-queue).**
11. **lq surrogate (B.7):** hold behind the offline LQModel τ test (§E-7). Expected 2–4× budget saving *if* τ ≥ 0.85; else dead. **Offline proof now; GPU A/B only if it passes.**
12. **Linked knobs (B.2):** the only shipped candidate today is R² 0.427 — **do not enable**; the plan's bar is R² ≥ 0.8. More data (tonight's g2/g6/g8/g9) may surface one; also check `cma_covariance*.json` eigenvectors (A.4, per dossier §9). **Wait for data.**

---

## C. SEEDS & PARAMETER DISCOVERY

**How seeds work today:** `search.seed` in the config (`config.py:114`) seeds CMA + the RNG; `--cma-seed INT` overrides (`cli.py:1549,1563,1583`); restarts add `+k` (`cma.py:700`); design seed values come from `seed_params` (`config.py:137`); `search.warm_start` (B.1) replaces mean/σ0 from prior runs; `narrow` bumps `search.seed +1` (`cli.py:1043`). The inventory CSV records `cma_seed` per run — today's groups: v6 {1234→1.5356, 1226?…}: seeds 1234 (24053e, g6, resumable), 1236 (00cf9c, c2), 1235 (g7, pending); core_law {1030→2.1283 (fbab4f), 1031 (g2, running)}; ath_core native {1234 (archived), 1235 (g4, pending)} + 26-seed freeform_sculpt group.

**Proposal (concrete, testable):**
1. **Per-brief-class seed packs from top-decile medians.** From each family's archived valid rows (inventory + ndjson), compute the top-decile per-knob median vector and the normalized spread; emit `warm_start: {from_runs:[best run], top_k: 10, sigma_from_spread: true}` — the exact keys B.1 implements. This is derivable *now* from the walls/sensitivity outputs; formalize as `tools/analysis/seed_init.py` (new small tool; "code").
2. **σ0 from top-k spread** with the clamp [0.05, σ0] — already inside B.1; for cold runs set σ0 ≈ the measured normalized spread of the top decile (g1: `L_mm` spread dominates; g6: everything is tight).
3. **Per-class links** stay closed (§B-12) until an R² ≥ 0.8 candidate appears across ≥2 runs.
4. **Seed selection for A/Bs:** always run the same seed list on both sides (paired protocol, dossier §8); ≥5 seeds before verdicts; the 26-seed group sets paired-σ (§E-2 runs today).
5. **Restart re-rolls count as seeds:** with `restarts: bipop`, each restart re-rolls scale — treat per-restart bests as pseudo-seeds when comparing budgets (already recorded in `run.json.restarts`).
6. **Tests:** (a) config-hash invariance of warm start (already in B's suite); (b) `seed_init` golden on a synthetic run dir; (c) paired A/B template using `seed_variance.py`'s ≥5-seed verdict rule.

---

## D. VISUALIZATION

**Exists today (wired):**
- **A.8 reports + PNGs** (`report_day.py` → `REPORT.md` + per-section `*.png`: convergence, walls, links, term_balance, fidelity; sensitivity/seed_variance emit JSON+MD) — currently only in `oc-wt\AN\scratch\report_day_partial\`.
- **GUI:** `#/analysis` (E.1), lanes panel (E.2), `#/elites` (E.3) — all degrade gracefully but **empty until `runs/analysis/` is populated**; run detail (still branch-side richer on the *queue* branch: verify ΔJ block, live status — commit 79edc8d, not on main); **Design cloud** PCA/UMAP per run (`gui/data.py::run_umap_cloud` :1986, `/api/umap/<run>`); Boundary-Lab A/B report view; run `report` HTML; two-lane `night_status`; night_report markdown.
- **Proposals only:** #45 verify/high-res view (slice 1 data/API first) — adds the screen-vs-verify scatter, bias KPIs, verify-J table, per-design balloon scrubber, compare-two-verified.

**Missing for the owner to *see* parameter/seed/landscape evidence, prioritized:**
1. **Populate `runs/analysis/`** (the GUI's default analysis dir) — one `report_day` run per day; the #/analysis page then lights up for free.
2. **A cross-run seed-variance violin/ECDF panel** (A.2 already computes the data; add a renderer like other tools' PNGs, plus a GUI card in #/analysis — slice-size change).
3. **A parameter-cloud across a family** (all archived valid rows of one family/config projected PCA-coloured by J, overlaying the top decile and today's per-run bests) — extends `run_umap_cloud` from per-run to per-family; informs seed/box decisions visually (the sensitivity tables are numeric, the picture is what sells a narrow/widen/pin).
4. **Walls heatmap across runs** (knob × run fraction-at-bound) — directly renders §E-3's aggregate; decides pin list at a glance.
5. **v8 ranking-shift chart** (τ / top-20 overlap bars per class, refusal share for class B) — from the finished re-score JSON; one page for the owner decision.
6. #45 slices 1–3 (verify table + KPI + scatter) — the single most useful addition for "is the winner real?"

---

## F. MERGE / DEPENDENCY MAP

- **AN evidence PR (blocking nothing):** commit the AN spec fill + partial REPORT/NIGHT evidence; it should *not* pretend to be final (g2–g7 rows pending) — label PARTIAL, supersede with the final fill tonight (day-plan §3.1).
- **G follow-up PR:** fold `objective_v8_full_2026-11-12` numbers into brief §4 and the real tolerances into `scalar_v8.py` (§E-8); keep unregistered. Do before the owner reads the brief, else they see placeholders.
- **Queue branch merge:** 79edc8d (GUI live-status; GUI-1/GUI-2 closure) merges later; per PR #44's CONTINUITY note its `_cpu_activity`/verifyBlock must first learn `--verify-dir`/`verify_of` paths.
- **Pr #25 (L4, eol renormalise):** merge LAST after both queues finish (day-plan §3.3), then the F reorder patch, then `pull --ff-only` the live checkout.
- **Blocked on the GPU queue finishing (pending jobs g3–g9):** final report_day fill; A.6 narrow-vs-control & staged A/B; g1+g2 core_law seed group; g6+g7+c2 3-seed group; D.3 apply (also owner GO); final NIGHT report; PR #25; HF re-pack (WP-E4, after D.3).
- **Blocked on owner only:** v8 adoption path; D.3 apply; C.3 default flips (fused/prefetch/batch); screen-grid change (invalidates cache); Collin HF write access; printing.

---

## G. OPEN DECISIONS / RISKS

**Owner decisions (only they can make):**
1. **v8:** adopt-offline → calibration+paired-seed A/B → class-by-class switch? The re-score's headline (class B 87% hard-refused; τ 0.5–0.8 vs v4) must be read *before* trusting any v8-based claim.
2. **D.3** merge of `dataset_cpu` → `dataset` (parity now PASSES; 237 rows).
3. **Next-night calibration GO** (C.1/C.2 harness ready) and the P0 gate levels / driver list inputs that still gate it.
4. **Default flips** from C.3 (fused ON; prefetch OFF ≥8k; freq_batch 12 once a `solve.freq_batch_size` key exists).
5. **PR #25 timing** (last today), and the screen-grid/`screen_extra_hz` cache-invalidation scheduling.

**Technical risks (with mitigations):**
- **Mixed-lane verify data (live today):** c2b/g1c wrote per-backend responses into the same `<run>/verify/` (pre-#44); any fidelity/parity analysis must either filter by backend or use the G salvage. New verifications with `--verify-dir` are clean.
- **v8 placeholder tolerances** (`scalar_v8.py:126`) — do not let anyone quote v8 numbers until §E-8 lands; the brief's §4 is still a literal TODO.
- **Screen bias** (29.2% median; 95% worse) — never rank by screen J for print decisions; the winner's-curse math says today's top-20 shortlists under v8/v4 differ (4/20, 13/20, 0/20 overlaps).
- **CPU/GPU parity** is proven for the *same* solve spec (0.036 dB), but J comparability across backends is only as good as lane purity of the runs (lane/backend tags now exist; older rows don't).
- **Stale worktrees** (L1 is 85 commits behind; day trees hold merged heads) — cheap cleanup after PR #25; no unmerged code exists in them except AN/G scratch.
- **Test flakiness under load** — one known instance today (`test_mesh_build` 100 ms timing assert under two concurrent suites; passes in isolation, documented in the #44 merge commit); CI-as-merge-gate is still off (PR #38 merged red, cost #39/#41).
- **Tolerance circularity** for v8/v6 recalibration (top decile is v4/v7-selected; v6's class top-decile p10–p90 today is razor-tight, e.g. rip 0.01557–0.01581 — a tolerance set that narrow will fragment on the next archive).

**Bottom line:** today's data-analysis and GA layers are real and merged end-to-end (A toolkit, B opt-in features, C/D harnesses, E GUI views) except precisely four open ends: `runs/analysis` is not yet populated, v8 tolerances/brief §4 are placeholders *but the full re-score just finished*, the AN evidence is uncommitted, and the F reorder patch + PR #25 are the still-pending close-out steps. Everything in the CPU work queue above can start now on the idle CPU lane; only the queued g3–g9 results and the owner's v8/D.3/grid decisions gate the rest.
