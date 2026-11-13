# Next-queue planning handoff — hornlab-search / bo-study

**Compiled:** 2026-11-12 ~22:45 local (2026-11-13 ~05:45Z). **Audience:** the senior agent who will
plan and authorize the next solve queue. **Rule of use:** this document is a briefing plus evidence
index. It records what is verified, what is inference, and what is still open. It does not itself
authorize a solve, a brief change, or a data write.

**At compile time:** the GPU night queue `gpu_day_2026-11-12_cont2` has finished g3b-g8 and is
running its last job, g9 (`atlas__ath_core` resume, 400 evals, 50x50 brief). Re-check status before
planning; do not assume it is still true.

**Status update (2026-11-13 ~13:45Z):** `origin/main` has advanced past this snapshot. The
bo-study-v1.1 M2/M3 offline integration is landed (`c7dd6a3`, `9b798f5`, `1e02e88`, `79b6651`);
F0/F1 strict outcomes are in local `main` (`d9493cb`, unpushed at compile time); the live night
queue finished g9 at `2026-11-13 06:26:53Z` (1,726 rows, best J 1.66554). The canonical checkout
also has untracked `examples/briefs/print_80x60_2026-11-13/` and
`examples/typologies/print_80x60_2026-11-13/`, so the 80x60 direction may already be in progress —
verify before duplicating. The queue/status facts in section 3 are the 03:52Z night state and
remain historical; the K-law/retarget conclusion in section 7 is unchanged. `origin/main` still
carries the DRAFT `PARENT_M0_FREEZE.md`, so re-check the freeze state before planning.

---

## 0. If you read only one thing

1. The queue that ran tonight was chosen by a **compute-allocation study** (`study_2026-11-12/COMPUTE_STUDY.md`),
   not by a product acoustic objective. Its criteria were: still-improving runs, strong knob
   sensitivity, missing seed variance, bound walls, and GPU throughput.
2. The 50x50 task came from the **bo-study first-task selection**: `native__ath_core_v4` was chosen
   because it is a *native* OSSE task (no generator-surrogate dependency) with an existing cohort —
   not because 50x50 is the desired horn. Its brief is 50x50, f0 1280 Hz, band 300-8000 Hz, 2-inch.
3. The owner has now stated the actual product goal: **60-80 degree coverage, solid down to about
   700 Hz**, for a horn that could eventually be printed and used at home. The current 50x50 queue
   does not serve that goal, and 50 degrees at 700 Hz is not reachable in the current 650 mm
   envelope (K-law: 726 mm mouth required). 60-80 degrees at 700 Hz is reachable.
4. **Recommended next queue:** freeze a new brief (80x80 or 80x60 at f0 700, band top reduced to
   ~5.5 kHz for screen solvability), run a **zero-solve rescoring pass** over existing raw
   responses, then a small new-solve pilot (one or two CMA seeds, 300-400 evals each, plus verify).
   Keep the 50x50 work as optimizer-benchmark data; do not extend it.
5. **BoTorch is not in question.** The hardening decision and bo-study-v1.1 keep BoTorch through
   engine, GUI, propose, run, verify and feedback. Retargeting the acoustic brief changes the frozen
   *task/scoring identity*, not the engine or the workflow.

---

## 1. Owner directive and product objective

Owner statement (this session, 2026-11-12):

> "I'm honestly less interested in building these 50 degree by 50 degree horns that's currently
> solving for because they aren't that useful from a standpoint of us as the designers who are
> trying to eventually find a horn we're going to 3D print and use in our house. I'm more interested
> horns that go down to lower frequencies and are wider dispersion ... maybe 60 to 80 degree range
> emit our solid down to 700 hertz."

Interpretation that matters for planning:

- **"Solid to 700 Hz" is a directivity-control requirement, not a band change.** The current ATH
  brief already scores a 300-8000 Hz band (`native_ath_core_2in_v4.yaml`), so 700 Hz is inside the
  measured band. What is missing is the *pattern-control* target at 700 Hz: `f0_hz` is the mask /
  pattern-control frequency in the brief, and it is currently **1280 Hz**.
- **"60-80 degrees" is a coverage target**, and the brief has separate `coverage_h_deg` and
  `coverage_v_deg`. The pair chosen (e.g. 80x80, 80x60, 70x60) materially changes mouth size and
  solvability; see section 7.
- The user also said explicitly: **"BoTorch remains committed through GUI/propose/run/verify."**
  Treat that as a constraint, not a preference.

---

## 2. Where everything lives

| Thing | Path |
|---|---|
| Canonical repo checkout (the one the night runs from) | `C:\Users\hunte\Hrns\hornlab-search` |
| Canonical branch / tip at compile time | `main`, `3d995a6` (2026-11-12 18:24) |
| Running-night data | `hornlab-search\runs\nights\gpu_day_2026-11-12_cont2*` |
| Night queue YAML (live) | `hornlab-search\runs\nights\gpu_day_2026-11-12_cont2.yaml` |
| CPU-lane queue YAML (live) | `hornlab-search\runs\nights\cpu_day_2026-11-12_cont.yaml` |
| Night runner output | `runs\nights\*_runner_stdout.log`, `*_runner_stderr.log`, `*\summary.jsonl` |
| Day analysis spec (partly filled) | `oc-wt\W\tools\analysis\specs\day_2026-11-12.yaml`; placeholder copy in `oc-wt\DOCS\...` |
| Day analysis output | `hornlab-search\runs\analysis\day_2026-11-12\` |
| Morning compute study | `C:\Users\hunte\Hrns\study_2026-11-12\COMPUTE_STUDY.md` |
| Morning study artifacts | `study_2026-11-12\{runs_inventory.csv,sensitivity_analysis.txt,power_calc.py,proposed_configs\}` |
| Governing hardening decision | `oc-wt\DOCS\docs\research\HORN_OPTIMIZATION_HARDENING_2026-11-12.md` (240 lines) |
| Governing study spec | `oc-wt\DOCS\docs\research\BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md` (370 lines) |
| Parent M0 contract / assessment / resume / freeze | `oc-wt\bo-study\{PARENT_M0_CONTRACT.md,PARENT_M0_ASSESSMENT.md,PARENT_M0_RESUME.md,PARENT_M0_FREEZE.md}` |
| Parent dependency decision (BoTorch venv) | `oc-wt\bo-study\PARENT_DEPENDENCY_DECISION.md` |
| BoTorch isolated env | `oc-wt\bo-study\bayes-venv` (exists; botorch 0.18.1, gpytorch 1.15.2, torch 2.14.1+cpu) |
| Senior plan (day) | `hornlab-search\docs\SENIOR_PLAN_2026-11-12.md` (185 lines) |
| OpenCode night handoff | `hornlab-search\docs\OPENCODE_HANDOFF_2026-11-12.md` (341 lines) |
| GUI Analysis page work order | `hornlab-search\docs\HANDOFF_ANALYSIS_PAGE_2026-11-12.md` (405 lines) |
| GUI verify-view plan | `hornlab-search\docs\GUI_VERIFY_VIEW_PLAN_2026-11-12.md`, `docs\GUI_HANDOFF_2026-11-12.md` |
| Repo rules | `hornlab-search\AGENTS.md` (hard rules, GPU hygiene, two lanes), `TOOLCHAIN.md`, `CONTRIBUTING.md` |
| Continuity / issues / priorities | `docs\CONTINUITY.md` (612 KB), `docs\ISSUES.md` (314 KB), `docs\NEXT_DEV_PRIORITIES.md` |
| Historical senior notes (mostly resolved Oct 12-24) | `study_2026-11-12\NOTES_FOR_SENIOR.local-backup.md` |
| Legacy surrogate audit note | `PARENT_M0_ASSESSMENT.md` §4 |

---

## 3. Current queue and status (verified from logs at compile time)

Live GPU queue `gpu_day_2026-11-12_cont2.yaml`:
`hornlab-search/runs/nights/gpu_day_2026-11-12_cont2.yaml:13-81`.

| Job | Target | Status | Evidence |
|---|---|---|---|
| g3b | ATH v4 **narrow** 50x50, 200 evals | done 00:41Z, exit 0 | 211 evals, best J **1.93281**, run `20261112T225013Z-screen-633b4f` |
| g4 | ATH v4 **control** seed 1235, 200 evals | done 01:49Z, exit 0 | 201 evals, best J **1.74155**, run `20261113T004133Z-screen-46b68c` |
| g5 | staged A/B core_law | done 02:23Z, exit 0 | `runs/staged_ab_2026-11-12/COMPARE.md`; 21 evals/stage, 63 total, ~17 min; night summary shows 0 because it only counts its own nested output |
| g6 | lecleach v6 resume | done 02:45Z, exit 0 | 450 evals in `20261112T113047Z-screen-24053e`, best J **1.52916** |
| g7 | lecleach v6 seed 1235 | done 03:02Z, exit 0 | 301 evals, `20261113T024523Z-screen-c9e865`, best J **0.831933** |
| g8 | ext-throat v7 resume +200 | done 03:27Z, exit 0 | 401 evals in `20261112T110126Z-screen-c414b1`, best J **6.6361 — unchanged**; 120/400 invalid geometry, peak 1314 MiB |
| **g9** | **atlas__ath_core resume +400 (50x50)** | **running at compile time** | process started ~22:27 local; no summary entry yet; expected ~2.2 h |
| c1b | CPU verify ATH top-10 | done, exit 0 | 18 evals; note "gpu-clean reported GPU busy; post gpu-clean rc=3" |
| c2b | CPU verify core_law top-10 | **failed**, exit 1 | 2/10 `solve_failed: [worker_exit] ConnectionResetError(10054)`; 20 eval rows |

Where status is written:
`hornlab-search/runs/nights/gpu_day_2026-11-12_cont2/summary.jsonl` (one JSON line per job) and the
runner stdout log. Re-check with:

```powershell
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont2\summary.jsonl
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont2_runner_stdout.log -Tail 40
Get-Process | Where-Object {$_.ProcessName -match "hornlab|julia"}
```

Known defects / cautions before you trust the day report:

1. **The day-analysis spec is stale.** `oc-wt/W/tools/analysis/specs/day_2026-11-12.yaml` still
   comments g2/g6/g7 as "GPU queue pending" although the summary shows them complete; it only fills
   g1, c2, g8, g9. The report at `runs/analysis/day_2026-11-12` therefore covers a subset (12
   sections, 1 honest error; see section 5.6).
2. **The `v6_seeds` error is correct, not a bug.** The spec groups g6 (beat_cuda) with c2
   (beat_cpu); `seed_variance` refuses to pool two backends. The message is
   `task_config_hash_mismatch`. `docs/HANDOFF_ANALYSIS_PAGE_2026-11-12.md:75-76,105-110`.
3. **g8 contradicted its own plan.** `COMPUTE_STUDY.md:253-254` says do not expand
   `atlas__osse_ext_throat` until the HARDENED_D evidence is re-evaluated; the executed queue did
   +200 evals anyway, for zero improvement. Do not repeat this.
4. **CPU verify is not yet comparable to GPU verify.** c2b failed on 2/10, both CPU jobs log
   "gpu-clean reported GPU busy" (they call GPU hygiene while the GPU lane holds the lock), and the
   E8 CPU-vs-CUDA parity check was never run (`COMPUTE_STUDY.md:194`). Per repo rules, cross-lane J
   comparison requires parity first.
5. **The analysis spec is not the queue.** It is a report definition. The queue is the YAML in
   `runs/nights/`.

---

## 4. Why this queue exists — decision chain

### 4.1 Morning: compute-allocation study (not acoustics)

`study_2026-11-12/COMPUTE_STUDY.md` inventoried 414 runs and ranked work by optimizer/data-quality
criteria, not by a product horn target:

- Inventory and sensitivity: lines 11-48, 65-104.
- Throughput matrix and recommendation (keep `cuda_fused: true, prefetch: false` for 8k dofs):
  lines 53-63.
- Atlas coverage table (all v4 atlas cells <10% of 324 bins; ~3,000 evals needed for 50%):
  lines 106-118.
- The actual GPU plan n0-n10 and rationale table: lines 157-173. The rationale column is the
  decision record: "highest-value still-improving atlas cell; L_mm dominates", "seed variance for
  algorithm analysis", "first real v6 search", "3 bound walls", "coverage fill", etc.
- Findings and recommendations: lines 229-257. Notable:
  `atlas__core_law` highest priority (L_mm rho -0.704); `atlas__ath_core` approaching convergence
  and further budget yields coverage fills, not algorithm gain; seed variance missing everywhere;
  the staged A/B fix is a 3-line path-resolution fix; do not expand v7 ext-throat.

### 4.2 Afternoon: the BoTorch first-task selection picked the 50x50 ATH cell

`BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md:94`:

> "First candidate task: existing `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml`,
> resolved through the normal loader and its brief. Before selecting it, M0 must demonstrate an
> adequate compatible cohort ... or return insufficient evidence for parent task selection."

Why ATH: it is a **native OSSE** task, so the GP path does not depend on unimplemented
generator-surrogate support (`spec:96`). It has an existing cohort. Its brief is 50x50, f0 1280,
band 300-8000, 2-inch. The parent M0 assessment verified the resolved values
(`PARENT_M0_ASSESSMENT.md:22-59`) and froze a draft task (`PARENT_M0_FREEZE.md:6-18`), explicitly
keeping ATH eligibility open pending R0/S0 (`PARENT_M0_FREEZE.md:70-78`; `PARENT_M0_ASSESSMENT.md:135-136`).

**Consequence:** 50x50 is an artifact of software convenience and cohort availability, not an owner
acoustic requirement. The governing doc leaves task selection to the parent when evidence changes
(`HORN_OPTIMIZATION_HARDENING...md:116`).

### 4.3 The hardening decision (the governing review)

`HORN_OPTIMIZATION_HARDENING_2026-11-12.md` is the decision record following the owner request for a
parent research pass and two independent Terra reviews. Its verdict (lines 3-5): the direction is
useful, but the prior plan put workflow infrastructure ahead of evidence and conflated nominal
controls with physical effects. It orders delivery as **M0 reusable data/rescoring + parameter audit
-> M1 existing-GUI explanation -> M2 BoTorch proposals -> M3 integrated workflow**, and states
explicitly that **BoTorch remains in the full implementation scope through engine, GUI, proposals,
serial execution, verification and feedback**.

The accepted review findings and the required changes are the table at lines 7-21. The most
queue-relevant ones:

- A searched knob can be inactive (`morph_exponent` at target 1): activity audit before feature
  selection; preserve the production config.
- Parameter hashes are not physical uniqueness: separate sampled final-geometry equivalence.
- The resolved brief matters, not inline YAML: the ATH resolved target is 300-8000/f0 1280, while
  the YAML's inline 500-5500 block is stale (`PARENT_M0_ASSESSMENT.md:51-52`,
  `PARENT_M0_FREEZE.md:8-13`).
- The first task is a directivity study with a 2-inch uniform-piston caveat above f11 ~3957 Hz and
  loading weight 0: never claim loading/efficiency/distortion/max-SPL.
- Beamwidth alone can hide lobes; report crossings/DI/missingness.
- A large 14-D global pool is unproven: compare with space-filling and CMA.
- New orchestration was too early: M1 is an immutable report plus a small existing-GUI extension;
  SQLite/new jobs are not prerequisites.
- Default cache enforcement is out of scope for M0-M2 (`:144`).

Reusable-data policy (section 4, lines 87-110) is the foundation for the retarget recommendation:

- Three identities: physical solve (immutable), derived metric (target-dependent), score
  (version/weights/tolerances/brief).
- A target/coverage change creates a **new metric/score identity** while reusing the same raw
  physics; regenerate target-dependent ripple/masks/normalization instead of only reweighting.
- Assert zero backend calls and no historical artifact mutation; output exact/partial/additional-
  solve-required per row.
- Existing v1-v7 scorer dispatch and offline tools are reused; v8 stays an explicit research
  scorer until separately registered.

M0 requirements (lines 114-118): preservation/zero-solve rescoring; real candidate cohort with
complete identity; ATH is a candidate, not assumed to have enough data; if it fails, the parent
selects an evidenced existing task without weakening compatibility.

M1 (lines 120-126): an existing-GUI report with 3-5 actual selectable designs tracing knobs ->
geometry -> measured per-band acoustics -> exact J terms; show no-op controls, source bands,
crossings, exclusions, validation; return `insufficient_evidence` honestly.

M2 (lines 128-134): pure advisory BoTorch adapter, activity-aware mapping, unchanged physical/scoring
task, diagnostics vs CMA/space-filling, equal-cost pilot with existing serial tools, no new adaptive
runner just to test one batch.

M3 (lines 136-140): full integration after M0-M2 interfaces; Pareto/constraints/cost/trust-region
retain planned interfaces; real solves and adoption remain separate gates; do not declare the task
complete at M1/M2 or silently drop BoTorch.

### 4.4 bo-study-v1.1 — what it locks

`BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`:

- Protocol ID and ordering: lines 3-9.
- Owner workflow (define -> evidence -> understand -> propose -> review -> run -> verify -> decide):
  lines 11-24.
- Architecture: `studies/` and `bo/` are additive; BoTorch optional and lazily imported; the normal
  GUI/CMA path must work without it (lines 46-60).
- The study registry is not another acoustic dataset; responses stay in normal runs/cache/dataset
  (line 60).
- Durability/revisions: SQLite at `<study_root>/studies.sqlite3` is M3, not a prerequisite; current
  M0-M2 use immutable manifests and existing report/GUI paths (lines 62-76).
- Locked numerical contract:
  - Explainability baseline: ExtraTrees, 100 observations/five groups as an eligibility screen, not
    validation proof; permutation importance, bins, finite-step interaction diagnostics
    (lines 80-88).
  - First task/eligible data: one task/brief/scoring identity and one fidelity per model; only
    successful complete observations; deduplicate physical identity; historical repeats are not
    independent replicates; `d` after active projection, not implicit reordering (lines 90-107).
  - Training selection: `n_min = max(16, 2*(d+1))`; cap 256 (64 lowest-J + 192 maximin); publish
    retained/excluded IDs; noise-floor multipliers 0.1/1/10 and two pool seeds as diagnostics
    (lines 109-113).
  - Scalar BO: minimize J by modeling `Y = -J`; `SingleTaskGP` + `ConstantMean` +
    `ScaleKernel(MaternKernel(nu=2.5, ard_num_dims=d))` + `Standardize(m=1)`; locked lengthscale
    `[0.005,4]`, initial 0.25; outputscale `[1e-3,1e3]`; `train_Yvar = 1e-6*s2`; one fit attempt,
    100 iterations; `qLogNoisyExpectedImprovement` with 128 Sobol samples, `prune_baseline=False`
    (lines 115-143).
  - Candidate pool: 4096 scrambled Sobol, cheap checks only, dedup by materialized geometry + solve
    identity + 1e-6 inf-norm, q=1 chunks of 64, every fourth proposal maximin exploration, at most
    two extra seeds then `pool_exhausted` (lines 145-155).
  - Pareto: `pareto_pool_v1` on coverage/ripple, resolved brief's `cov_narrow_ratio`,
    `cov_below_f0`, `diag_reference`; response-detrended ripple must assert `_used_resp`;
    `qLogNEHVI`; fixed hypervolume reference (lines 157-171).
  - Extensions: constrained margins, cost GP, trust-region `turbo_pool_v1`, multi-fidelity policy
    (lines 173-185).
  - Shared outcome isolation with CMA/QD: F0/F1, typed classification, strict resampling, no fake
    J=1000 (lines 187-197).
- CLI: `study validate/create/snapshot/analyze/propose/package/run ...` are **proposed, not present
  today** (lines 201-215). The queue that is running is the night queue, not a `study create` queue.
- Baseline run package: 18 new screen BEM calls, up to 6 verification candidates, 120 total attempts,
  one active solve; total new BEM cap 24; wall deadline required before scheduling (line 219).
- Runner: one proposal at a time, preflight, normal evaluator, record, update, refit; every fourth
  proposal is exploration; stop on budget/deadline/cancel/pool exhaustion/stale package/three
  infrastructure failures; verification selection fixed at up to 4 finalists + 2 audit samples
  (lines 221-225).
- Lane ownership: the study runner must explicitly hold the CPU lane lock or the GPU lock; do not
  infer lane from the generic GPU flag; CPU cancellation never invokes GPU cleanup (lines 227-229).
- GUI routes and panels: lines 231-300; API contract lines 280-298; JobManager is not a durable
  workflow engine (line 300).
- Artifacts and interfaces: lines 302-322.
- Execution order M0-M3 and required tests: lines 324-353.
- Dependencies: the project venv has Torch 2.14.1 but no BoTorch/GPyTorch; an isolated `bayes` extra
  with `botorch==0.18.1` is planned (lines 355-359). It now exists at
  `oc-wt/bo-study/bayes-venv` (`PARENT_DEPENDENCY_DECISION.md`).

### 4.5 Commit timeline that produced the current state

From `git -C C:\Users\hunte\Hrns\hornlab-search log`:

- `89a2103` docs(research): data analysis & GA improvement research plan (raw, pending review)
- `975048f` docs(research): self-contained council review handoff for the data/GA plan
- `4910c64` docs(continuity): research plan + external review handoff
- `a825f8a` merge(docs): preserve implementation plans and review hardening
- `a7828fd` merge(docs): consolidate research plan branch
- `d5c0b20` docs(research): refusals, CMA trajectories, and dataset-hygiene handoff (#49)
- `dabb5d1` feat(analysis): honest cost/replicate accounting and paired inference (S3 M0)
- `7997259` merge(analysis): S3 cost/replicate accounting (M0)
- `3d995a6` docs: continuity + issues for the main consolidation, 8765 restart, and push of all GUI waves
- GUI: `ceb962d` verify view, `9a45d5e` WP9/WP10 charts + search history, `1923ae5` finishing pass,
  `6534a69` visual-audit round 2.

The canonical checkout is dirty with uncommitted M0 work: untracked
`hornlab_search/bo/{__init__,data,encoding}.py`, `hornlab_search/objective/replay.py`,
`tools/analysis/{catalog,cohorts,offline_scores,parameter_activity,geometry_effects}.py`, matching
`tests/test_bo_*.py`, `tests/test_obj_replay.py`, `tests/test_tools_analysis_*.py`, plus
`docs/HANDOFF_ANALYSIS_PAGE_2026-11-12.md`, `cache_cpu/`, `dataset_cpu/`.

**Cleanup note (editor LSP, compile time):** type diagnostics exist in the uncommitted
`hornlab_search/objective/replay.py` (narrowing to dict at 299/441, `float | None` at 468,
optional arrays passed to `MetricSet` at 903-907), `tools/analysis/offline_scores.py:301`, and
`tests/test_obj_replay.py` (None-subscript at 165/169/193). These are not HEAD and not necessarily
test failures, but do not claim R0 is deliverable-clean until they are resolved or explicitly
accepted. `PARENT_M0_FREEZE.md:3` already says the freeze is pending R0's brief-target rerun and
S0's native-only census.

---

## 5. Data we already have — do not re-inventory this

### 5.1 Preservation / volume (parent-verified, read-only)

From `PARENT_M0_ASSESSMENT.md:14`:

| Root | Files | Size |
|---|---:|---:|
| `dataset/` | 25,212 | 4,277 MB |
| `dataset_cpu/` | 244 | 49 MB |
| `cache/solve/` | 51,214 | 6,456 MB |
| `cache_cpu/solve/` | 456 | 82 MB |
| `runs/` | 196,871 | 19,213 MB |

### 5.2 Record census (prior snapshot, not atomic; re-check before quoting)

`HORN_OPTIMIZATION_HARDENING_2026-11-12.md:232-234`:

- Main dataset **28,575 records: 23,941 ok, 4,634 failed**.
- CPU **237: 221 ok, 16 failed**.
- Main failure split: **3,079 invalid geometry, 553 envelope, 882 mesh-budget, 57 solve failures,
  63 generic exceptions**.
- Archived `fbab4f` check: **1,001 rows: 567 ok, 327 invalid geometry, 106 mesh too large,
  1 solve failed**; its archive had 17 cells and zero recorded `J>=1000` cells (that run only).

### 5.3 Run inventory (414 runs, `runs_inventory.csv`)

`COMPUTE_STUDY.md:11-48`:

| Family | Runs | Valid evals | Best J | Still-improving |
|---|---:|---:|---:|---:|
| FREEFORM | 296 | 17,553 | 1.1131 | 95 |
| OSSE | 88 | 8,697 | 1.5968 | 29 |
| R-OSSE | 23 | 1,360 | 1.0343 | 8 |
| ICW | 7 | 1,856 | 12.2009 | 4 |

Caveat: 136 runs flagged still-improving; only 46 have campaign-era v4/v6/v7 objectives and known
briefs; most of the rest are pre-v4 with no brief (`COMPUTE_STUDY.md:23-25`).

Atlas cells (`COMPUTE_STUDY.md:29-38`):

| Config | Brief | Obj | Valid | Bins / 324 | Best J |
|---|---|---|---:|---:|---:|
| `atlas__ath_core` | `native_ath_core_2in_v4` | 4 | 1,141 | 31 | 2.0987 |
| `atlas__core_law` | `native_ath_core_2in_v4` | 4 | 347 | 15 | 2.2953 |
| `atlas__hyb_osse_h_hypex_v` | `b2w_pa_60x40_1200_big_v4` | 4 | 1,102 | 19 | 2.7538 |
| `atlas__osse_ext_throat` | `b1w_hifi_90x60_850_wide_v5` | 7 | 140 | 5 | 6.6361 |
| `lecleach_rollback` | `lecleach_rollback_1in_v6` | 6 | 142 | - | 1.5357 |

Best single-objective v4 cells (`COMPUTE_STUDY.md:40-48`):

| Config | Brief | J | n_valid |
|---|---|---:|---:|
| `b3a__rosse_morph_round_v4` | `b3a_pa_90x90_400_square_v4` | 1.5968 | - |
| `native__ath_core_v4` | `native_ath_core_2in_v4` | 1.6180 | 192 |
| `b1t__lecleach_iwata_ar_v4` | `b1t_hifi_90x60_850_tall_rows_v4` | 1.6252 | - |
| `crease__core_law_v4` | `native_ath_core_2in_v4` | 1.7079 | 172 |

### 5.4 Sensitivity (`sensitivity_analysis.txt`, Spearman rho; negative = lower J at higher value)

- `atlas__ath_core` (`377bbe`, 1,141 valid): `a_deg +0.264`, `morph_rate +0.176`,
  `morph_exponent -0.127`, `k -0.119`; no bound walls. Weak signal, well explored.
- `atlas__core_law` (`fbab4f`, 347 valid): **`L_mm -0.704`**, `a_deg -0.222`, `k +0.155`,
  `s +0.142`; no bound walls. Strongest signal in any v4 atlas cell.
- `atlas__osse_ext_throat` (`c414b1`, 140 valid): **`L_mm -0.874`**, `r0_mm -0.193`,
  `throat_ext_length_mm -0.179`; 5/324 bins only.
- `native__ath_core_v4` (`d37d64`, 192 valid): `morph_corner_mm -0.326`, `n -0.315`,
  `morph_rate +0.296`, `k -0.272`, `morph_width_mm -0.270`, `L_mm -0.216`. Bound walls in top
  decile: `morph_fixed` low (8/19; range 0-0.6), `morph_width_mm` high (8/19; range 238.2-456.55),
  `q` high (7/19; range 0.9-1.0).
- `crease__core_law_v4` (172 valid, not still-improving): `n +0.385`, `a_deg -0.356`, `s +0.306`;
  walls `k` low 7/17, `morph_rate` low 9/17. Not scheduled.
- `b2w__osse_baseline_v4` (127 valid, still-improving): `k +0.450`, `n +0.361`, `L_mm -0.297`;
  `k` low wall 6/12.

Interpretation limit from the hardening doc: these are descriptive rank correlations, not causal
laws; correlated/adaptive samples and aperture growth confound shape claims (`:75-88`, `:67`).

### 5.5 Throughput (RTX 4060 8 GB, `COMPUTE_STUDY.md:53-63`)

| dofs | fused-on prefetch-off | fused-off | fused-on prefetch-on | fused-off prefetch-on |
|---|---|---|---|---|
| ~1k | 131 s / 1,334 MiB | 141 s / 1,835 MiB | 119 s / 1,410 MiB | 140 s / 2,485 MiB |
| ~4k | 232 s / 3,167 MiB | 281 s / 5,261 MiB | 234 s / 2,872 MiB | 315 s / 5,547 MiB |
| ~8k | 503 s / 4,900 MiB | 318 s / 7,499 MiB | 504 s / 4,202 MiB | OOM at 7,731 MiB |

Recommendation: keep `cuda_fused: true, prefetch: false` for 8k-dof searches. A run with
shared-memory spill >200 MiB is invalid, not "slow" (`AGENTS.md` Windows/nvidia-smi rule).

### 5.6 M0 cohort and replay evidence (bo-study)

From `PARENT_M0_FREEZE.md:53-63`:

- Native-only ATH cohort: **197 ok rows** (192 screen + 5 verify), **192 unique geometries**,
  197 unique physical solves. `run_id` absent on all native rows, so independent-experiment identity
  is `insufficient_evidence` unless recovered from provenance.
- Four-config descriptive census (the three other configs sharing the brief are descriptive only,
  never pooled for GP): **3,185 records / 2,412 complete replayable rows**.
- R0 replay pilot: **200 scored rows, 195 parity-compared, max |delta J| = 0, zero backend calls**.
  The 5 unpaired rows are stored-v3 records replayed under a v4 variant.
- Pending: R0 brief-target rescore (`2500-5500 x2`) + native-only replay counts; S0 native-only
  census. `PARENT_M0_FREEZE.md:70-78`.

The analysis report already written: `runs/analysis/day_2026-11-12/` contains `REPORT.md`,
`report_day.json`, and per-section JSON/MD/PNG for `convergence_g1|c2|g8|g9`, `sensitivity_g1|g6`,
`walls_g1|g6`, `term_balance_g1|g6`, `links_g1`, `fidelity_g1`; the only error is `v6_seeds`
(backend mismatch). `docs/HANDOFF_ANALYSIS_PAGE_2026-11-12.md:94-110`.

### 5.7 Tonight's results, with interpretation

- **g3b narrow vs g4 control (50x50):** control 1.74155 beat narrow 1.93281. The narrowing
  hypothesis failed; useful negative evidence, not a product result.
- **g6/g7 lecleach v6 seeds:** seed 1235 reached 0.831933 vs 1.52916 on the resume. This is the
  largest signal of the night and validates the seed-variance rationale. It is v6
  (`loading_smooth`, Le Cléac'h class), not the directivity task.
- **g5 staged A/B:** 21 evals/stage; stage A 11.28, stage B 4.99, stage C 2.63. A methodology
  comparison, not a candidate horn.
- **g8 ext-throat v7:** +200 evals, best J unchanged at 6.6361, 120 invalid geometries. Confirms the
  plan's own stop recommendation.
- **g9 ATH atlas:** coverage fill on a task approaching convergence; low expected product value.
- **c1b/c2b:** CPU verify not yet trustworthy; 2/10 failures; parity unmeasured.

### 5.8 What the data does NOT give you

- No stable seed-variance estimate for v4 atlas cells (only single seeds; g7 is v6).
- No CPU-vs-CUDA parity (E8), so do not pool or rank across lanes.
- No v4 ATH cohort with `run_id` / independent-experiment identity.
- No target-diverse rescoring yet: stored metrics are not universally scoring-independent; a new
  coverage target requires regenerated target-dependent masks/ripple under a new metric identity.
- No measured reference horn; no calibration to a real print (SENIOR_PLAN B6, open).
- No loading/efficiency/distortion/max-SPL validation for the ATH task (load weight 0; 2-inch
  uniform-piston caveat above ~3957 Hz).

---

## 6. The existing briefs and objective versions you must not confuse

Objective versions (`docs/SENIOR_PLAN_2026-11-12.md:43-48`):

| Version | Meaning | Use |
|---|---|---|
| 4 | tolerance-normalised pattern objective | legacy comparisons only |
| 5 | MEH system objective | MEH briefs (paused) |
| 6 | `loading_smooth` (Le Cléac'h) | Le Cléac'h / rollback |
| 7 | hardened loading + flat_cv + 8 kHz floor + signed V + round-throat gate | CD briefs (hi-fi/PA) |

**Never rank J across versions.** The GUI version guard and banner are part of `SENIOR_PLAN` D1/D2
(landed in PR #26; see `docs/ISSUES.md` for the current status).

Briefs relevant to a wider/lower target (all in `examples/briefs/`):

| Brief | Coverage | f0 | Driver | Envelope | Band | Objective |
|---|---|---:|---|---|---|---|
| `campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml` | 50x50 | 1280 | 2-inch (r0 25.4) | 650x650x520 | 300-8000 | v4 |
| `atlas_2026-10-30/b2w_pa_60x40_1200_big_v4.yaml` | 60x40 | 1200 | 1.4-inch (r0 18.0) | 650x650x520 | 300-8000 | v4 |
| `campaign_2026-10-26/b1t_hifi_90x60_850_tall.yaml` | 90x60 | 850 | 1.4-inch | 360x520x400 | 300-8000 | v3 (v4 copy exists) |
| `campaign_2026-10-26/b1w_hifi_90x60_850_wide.yaml` | 90x60 | 850 (V from 1411) | 1.4-inch | 380x300x400 | 300-8000 | v3 (v4 copy exists) |
| `campaign_2026-10-26/b3bt_pa_90x60_600_load_tall.yaml` | 90x60 | 600 | 1.4-inch | 500x740x600 | 300-8000 | v3 (v4/v7 copies exist) |
| `campaign_2026-10-26/b3bw_pa_90x60_600_load_wide.yaml` | 90x60 | 600 (V from 941) | 1.4-inch | 500x450x600 | 300-8000 | v3 (v4 copy exists) |
| `user/wide_90x60_500hz_1p4in.yaml` | 90x60 | 500 | 1.4-inch | 620x900x450 | 500-10000 | v3 |
| `user/cap500_90x60_850hz_1p4in.yaml` | 90x60 | 850 | 1.4-inch | 360x520x400 | 500-8000 | v3 |

The `user/` briefs are especially useful: they already document the K-law and the 8 GB dof reality.
`wide_90x60_500hz_1p4in.yaml` says a 500 Hz 90x60 horn needs an 847 mm vertical mouth and is **not
solvable at 10 kHz on the 8 GB card**; the search would shrink the mouth and throw away the 500 Hz
control. This is the same trade-off you face at 700 Hz.

---

## 7. Physics arithmetic for "60-80 degrees solid to 700 Hz"

The briefs use the project K-law:

```
mouth_dimension_mm = 25,400,000 / (f0_hz * coverage_deg)
```

(Verified in `native_ath_core_2in_v4.yaml:11-13`: 397 mm at 50 deg and f0 1280 ->
25,400,000/(397*50) = 1280. Also in the b2w/b1t/b3bt brief headers.)

Mouth dimensions needed at 700 Hz:

| Coverage (per plane) | Mouth dimension |
|---|---:|
| 50 deg | **726 mm** (outside the 650 mm envelope; impossible in the ATH cell) |
| 60 deg | 605 mm |
| 70 deg | 518 mm |
| 80 deg | 454 mm |
| 90 deg | 403 mm |

So:

- **A 50x50 horn solid to 700 Hz is physically impossible in the current 650x650x520 envelope.**
  The current task can at best hold 50 deg to `25,400,000/(650*50) = 781 Hz`.
- **Wider is easier, not harder.** An 80x80 target needs only 454x454 mm; a 70x60 target needs
  518x605 mm; a 60x60 target needs 605x605 mm. All fit the 650 envelope; the 50x50 at 700 does not.
- The current 397 mm seed holds 50 deg at 1280 Hz, and could hold about 91 deg at 700 Hz if the
  geometry allowed. The optimizer is not short of capability; the brief is aimed at the wrong
  target.

**Dof reality (the binding constraint on band top).** The project uses the approximation
`quarter dofs ~ 3000 * (d/400)^2 * (f/5500)^2` (`examples/briefs/user/wide_90x60_500hz_1p4in.yaml`).
Apply it with the *larger* mouth dimension:

| Target | Mouth (WxH) | ~quarter dofs at 5.5 kHz | ~quarter dofs at 8 kHz |
|---|---|---:|---:|
| 80x80 | 454x454 | ~3,900 | ~8,200 |
| 80x60 | 454x605 | ~6,900 | ~14,500 |
| 70x70 | 518x518 | ~5,000 | ~10,600 |
| 70x60 | 518x605 | ~6,900 | ~14,500 |
| 90x60 | 403x605 | ~6,900 | ~14,500 |
| 90x90 | 403x403 | ~3,100 | ~6,500 |

Caveat: the caps drift between documents. `COMPUTE_STUDY.md:2` says `dof_cap_screen 12000`; the
Oct 26 user brief says a 5,000-quarter-dof screen cap and an 8,900 measured hard ceiling. Use the
resolved config and TOOLCHAIN caps, and verify with `shape_check`/a dry run before committing a
queue.

Implications:

1. **80x80 at f0 700 is the most solver-friendly target in the owner's range.** 454x454 mm is
   screen-solvable to ~5.5 kHz and verify-able to ~8 kHz; it fits the ATH envelope. But the ATH
   config's search bounds cap `morph_width_mm`/`morph_height_mm` at **456.55 mm** (parent-resolved;
   `PARENT_M0_ASSESSMENT.md:45-47`). Verify whether 454 mm final mouth is reachable through the base
   profile; if not, a new/widened config is required (a parent-authorized new config, not a silent
   bound change).
2. **80x60 at f0 700** needs 605 mm height and is not screen-solvable at 8 kHz once the mouth is
   that tall; cap the screen band at ~5.5 kHz (which is already the meaningful band for a 2-inch
   source above f11) or accept verify-tier only.
3. **Do not promise 60 degrees vertical + 700 Hz + 8 kHz screen on 8 GB.** Pick two of three:
   coverage, low f0, high band top.
4. If the goal is a *buildable* home horn, a 1.4-inch driver (r0 18 mm) is the family the existing
   wide/low briefs use; the ATH task is 2-inch (r0 25.4) and its f11 is ~3957 Hz. Driver size is a
   second-axis owner decision that changes the brief independently of coverage.

---

## 8. Constraints and guardrails the next planner must respect

From `AGENTS.md`, `OPENCODE_HANDOFF_2026-11-12.md`, the hardening decision and the M0 documents:

1. **One CUDA solve at a time; one CPU-backend search may run beside it.** Lane identity is the BEAT
   worker registry dir; unknown hosts are never killed (`OPENCODE_HANDOFF:120-136`).
2. **No GPU/Julia work or queue edits from analysis lanes while the night runs.** The canonical
   checkout belongs to the night; analysis is read-only (`PARENT_M0_RESUME.md:7-20`).
3. **Never change frozen contracts, installed packages, tolerances, or skip tests** (AGENTS.md hard
   rules 1-8).
4. **No production cache enforcement, no objective/search default changes, no v8 registration in
   M0-M2** (`HORN_OPTIMIZATION_HARDENING:144-145`).
5. **Three identities are immutable:** physical solve, derived metric, score. A new target creates a
   new metric/score identity; never overwrite the original or relabel a parameter hash as proof of a
   different surface (`:87-97`, `PARENT_M0_FREEZE.md:20-29`).
6. **Do not rank or pool across objective versions, backends, briefs, or fidelities** unless the
   docs' parity rules are met. v8 is unregistered. CPU/GPU parity (E8) is not yet measured.
7. **No fabricated metrics, impedance, gates, or J=1000 as an acoustic observation.** Failure
   categories stay separate (`:182-197`).
8. **The 2-inch ATH source is a uniform-piston model with f11 ~3957 Hz; loading weight 0.** No
   efficiency/max-SPL/distortion claims (`:73`, `PARENT_M0_ASSESSMENT.md:72`).
9. **BoTorch is optional, lazily imported, CPU-only, float64, 2 Torch threads; the normal GUI/CMA
   path must work without it.** Use `oc-wt/bo-study/bayes-venv`; never install into the live venv
   (`PARENT_DEPENDENCY_DECISION.md`).
10. **M1-M3 are paused until the owner resumes.** `PARENT_M0_ASSESSMENT.md:137-138`.
11. **The 50x50 queue is not the product.** It is benchmark/control data; do not extend it by
    default.
12. **Never quote the inline ATH target block (500-5500) as the task.** The resolved brief is
    300-8000/f0 1280 (`PARENT_M0_ASSESSMENT.md:51-52`).
13. **`morph_fixed` resolved bound is 0-0.6, not the 0-0.1 comment.** Do not silently tighten
    (`PARENT_M0_ASSESSMENT.md:55`).
14. **Do not extend v7 ext-throat** until the HARDENED_D gate analysis is revisited
    (`COMPUTE_STUDY.md:253-254`).
15. **MEH is paused**; merged code stays green, no new MEH work packages
    (`SENIOR_PLAN_2026-11-12.md:149-151`).

---

## 9. Adversarial assessment of the remaining queue

| Remaining work | Verdict | Why |
|---|---|---|
| g9 atlas__ath_core +400 (running) | **Low value, let it finish or stop; do not repeat** | The queue's own study calls this cell approaching convergence, weak `a_deg` rho 0.264, "coverage fills, not algorithm gain" (`COMPUTE_STUDY.md:235-236`); 1,141 evals already; 31/324 bins and ~3,000 evals needed for 50% coverage. Wrong product target. |
| More 50x50 ATH narrow/control | **Stop** | g3b vs g4 already showed control wins (1.742 vs 1.933); the narrow hypothesis failed. More evals optimize the wrong coverage. |
| More `atlas__core_law` | **Keep as optimizer-math only** | Strongest v4 signal (`L_mm -0.704`) and seed variance is still thin. But it shares the 50x50 brief, so it is benchmark data, not a product horn. |
| More v6 Le Cleac'h seeds | **Keep, cheap and informative** | g7 seed 1235 (0.832) vs g6 resume (1.529) is the largest signal; v6 is a different objective class, so use it for algorithm/variance work, not for the 60-80/700 goal. |
| Staged A/B methodology | **Keep small, then stop** | 21 evals/stage is enough for a methodology read; it is not a candidate search. |
| v7 ext-throat | **Stop** | Zero improvement for 200 evals and 120 invalid geometries; the plan itself says stop. |
| CPU verify lane | **Fix before relying on it** | 2/10 solve failures, backend parity unmeasured, cross-lane hygiene messages. Use it for verify only after E8. |
| Day analysis report | **Finish/fix, but it is a report, not a queue** | The spec is stale; the GUI cannot read nested sections yet; the `v6_seeds` error is correct. |

**Bottom line:** the remaining 50-degree work is not the most useful use of the GPU for the owner's
data or product. The most useful things the data can do next are (a) rescore existing raw responses
under a wider/lower brief at zero BEM cost, (b) run a small new-solve pilot on that brief, and
(c) keep the algorithm-math lanes (seed variance, CMA vs BO, staged-vs-joint) as a separate,
explicitly labeled track.

---

## 10. Alternatives for the next queue

### Option A (recommended): retarget the brief, rescore first, small pilot

**A1. Write a versioned decision record + new brief** (parent/owner approval; new score identity,
not a silent mutation). Candidate targets, in order of solver-friendliness:

- **80x80, f0 700 Hz, band 300-5500, 1.4-inch or 2-inch driver, envelope 650x650x520.**
  Mouth 454x454; screen-solvable to ~5.5 kHz; verify to ~8 kHz; fits the range.
- **80x60, f0 700 Hz, band 300-5500.** Mouth 454x605; screen at 5.5 kHz is marginal (~6.9k quarter
  dofs); verify-tier at 8 kHz is too big for the 8 GB card.
- **70x70, f0 700 Hz, band 300-5500.** Mouth 518x518; screen ~5k dofs; verify 8 kHz ~10.6k, over
  the measured hard ceiling.
- **90x60, f0 700 Hz** only if 90 degrees horizontal is acceptable; mouth 403x605.

Keep the weights/tolerances and objective version explicit. Do not use `V8Params.for_class("A")`;
build v4 raw params from the resolved brief and preserve `cov_narrow_ratio=2`,
`cov_below_f0=mask`, `diag_reference=round`. If the target changes, the coverage/ripple masks and
normalization must be regenerated under a new metric hash.

**A2. Zero-solve rescoring pass (first, cheap, decisive).** Use the R0/offline-score machinery
(`hornlab_search/objective/replay.py`, `tools/analysis/offline_scores.py`) against
`dataset/`, `cache/solve/`, and run-dir `response.npz`. Report per row: `exact_complete`,
`partial_unsupported`, `additional_data_or_solve_required`; assert zero backend calls and no
mutation. This tells you which of the ~23.9k ok solves are already close to the new brief, and which
geometries are missing. The current R0 pilot did 200 rows with max |delta J| = 0, so the path is
proven for parity; the target-change variant is the pending piece (`PARENT_M0_FREEZE.md:61-62`).

**A3. Small new-solve pilot, not a coverage atlas.**
- One fresh CMA seed on the new brief, 300-400 evals. Start from the cell whose family/envelope
  matches the target (ATH native for 2-inch; b3bt/hyb for 1.4-inch), with a new config/brief file.
- A second seed only if the first shows a promising region; otherwise spend the budget on
  verification.
- One narrow-vs-control pair only if rescoring/geometry shows bound walls at the new target.
- Verify top 4-6 designs; use the GPU lane first, CPU lane only after E8 parity.
- Budget estimate at ~20 s/eval (OSS E, 1k-4k dofs): 400 evals ~2.2 h; verify ~0.5-1 h. A two-seed
  pilot is ~5-6 h, leaving room for the algorithm-math lane.

**A4. Keep BoTorch on the new task.** The M2 adapter is objective-agnostic once the score identity
is frozen. M0 should freeze the *new* brief (or record the old one as benchmark-only), then M2
proposes on the new brief. This does not weaken the commitment; it makes the first M1/M2 artifact a
horn in the owner's design space.

### Option B: mine the existing wide/low families first (faster path to a printable candidate)

Before a new search, rescore and verify the best existing designs from:

- `b3bt_pa_90x60_600_load_tall` (v4/v7 copies exist; 90x60 @600, 1.4-inch, 500x740x600 envelope,
  K-law mouth 470x706). This family is the closest existing "wide and low" product family. An
  80x60 @700 target fits inside its envelope (454x605).
- `b1t_hifi_90x60_850_tall` / `b1w_hifi_90x60_850_wide` (90x60 @850, smaller envelope).
- `b2w_pa_60x40_1200_big` (60x40 @1200; vertical is narrower/higher than the ask).
- `user/wide_90x60_500hz_1p4in` is a design *aspiration*, not a screen-solvable task on 8 GB; use
  it for the physical target, not as a literal screen brief.

If the goal is "a horn I can print", a rescore + verify of b3bt/b1t elites may produce a candidate
sooner than a new ATH study. The trade-off: those runs carry v3/v4/v7 objective versions and
different briefs, so you must rescore under the new brief and report the identity change honestly.

### Option C: continue the optimizer-math track (only if the owner wants math, not a product)

If the priority is the optimizer/mathematics, the useful work is:

- seed variance for v4 atlas cells (core_law seed 1031, ATH seeds), because it is missing everywhere
  and g7 shows how large it can be;
- CMA vs BoTorch vs space-filling on a fixed brief and budget, with equal-cost accounting;
- staged-vs-joint A/B as a methodology paper (g5 already gives a first read);
- rescorer/identity work (M0) as the reusable foundation.

Do not present this track as product progress. It is the "improve the optimizer and software" goal
the owner acknowledged, and it can run beside the product pilot on the CPU lane or on off-nights.

### Decision gates for the next queue

1. Owner confirms the coverage pair and driver size (80x80 vs 80x60 vs 70x70; 2-inch vs 1.4-inch).
2. Resolved geometry check: can the chosen config reach the required mouth within its bounds and the
   650 mm envelope? If not, create a new config/brief (parent-authorized), do not widen silently.
3. Dof/band check: `shape_check` or a 1-eval dry run at the screen top; if the mesh is too large,
   lower `band_hi` (e.g. 5.5 kHz) or accept verify-tier.
4. Rescore evidence: how many existing rows are `exact_complete` under the new brief? If a usable
   cohort exists, M0/M1 can proceed without new solves; if not, the pilot is the minimum.
5. Lane/queue check: GPU idle or owned, CPU lane lock, no other job, and the day report fixed.

---

## 11. Open questions for the owner (do not guess)

1. **Coverage pair:** 80x80, 80x60, 70x70, or 90x60? The choice changes mouth size, solvability and
   the achievable band top.
2. **Driver:** 2-inch (ATH control; f11 ~3957 Hz) or 1.4-inch (the wide/low families; f11 ~5638 Hz)?
   This is a separate brief axis from coverage.
3. **Band top:** is 5.5 kHz enough for the screen/verify claim, or must the analysis go to 8 kHz?
   On 8 GB, 60-80 degrees at 700 Hz and 8 kHz screen are mutually exclusive for the tall dimension.
4. **Envelope/depth:** 650x650x520 is the ATH/b2w envelope. A printable home horn may accept a
   different depth/width; that changes the feasible K-law.
5. **Build vs study:** is the immediate goal a printable candidate, or an optimizer study? Option B
   is faster for a candidate; Option A is the principled path.
6. **What counts as "solid to 700":** -6 dB coverage at 700 Hz in both planes, or horizontal only
   (with vertical control from ~850 Hz)? The brief's `coverage_h`/`coverage_v` and `f0_hz` encode
   this distinction.
7. **Do we allow 90 degrees horizontal?** If yes, 90x60 at 700 is more solver-friendly than 60x60.

---

## 12. Reproduce / verify commands

```powershell
# Queue status
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont2\summary.jsonl
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont2_runner_stdout.log -Tail 60
Get-Process | Where-Object {$_.ProcessName -match "hornlab|julia"}
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont2.yaml

# Repo state
git -C C:\Users\hunte\Hrns\hornlab-search log --oneline -15
git -C C:\Users\hunte\Hrns\hornlab-search status --short

# Night results per job
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont2\summary.jsonl
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\staged_ab_2026-11-12\COMPARE.md

# Day analysis (already generated; do not regenerate until the final fill is reconciled)
Get-ChildItem C:\Users\hunte\Hrns\hornlab-search\runs\analysis\day_2026-11-12 -Recurse | Select-Object FullName
Get-Content C:\Users\hunte\Hrns\hornlab-search\runs\analysis\day_2026-11-12\report_day.json -TotalCount 40

# Interpreter (always the project venv)
C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe -c "import sys; print(sys.version)"

# BoTorch isolated env (do not install into the live venv)
Test-Path C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv
& C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe -c "import torch, botorch; print(torch.__version__, botorch.__version__)"
```

---

## 13. Compact file:line index for the two governing documents

`HORN_OPTIMIZATION_HARDENING_2026-11-12.md`:

- 3-5 verdict; BoTorch retained.
- 7-21 accepted review findings table.
- 24-33 four layers; 35-49 control ledger; 51 smooth-morph math.
- 53-63 geometry bridge; 65-73 size/frequency/source confounds.
- 75-85 interaction analysis; 87-110 reusable data and rescore policy; 108 surrogate gap; 110
  preservation.
- 114-118 M0; 120-126 M1; 128-134 M2; 136-140 M3.
- 142-149 guardrails (cache, defaults, coverage convention, context card, subset, limitations).
- 151-159 primary sources; 161-238 refusals/F0/F1; 232-234 census; 238 GUI policy.

`BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`:

- 3-9 protocol/order; 11-24 workflow; 46-60 architecture; 62-76 durability.
- 80-88 explainability; 90-107 first task/eligible data; 109-113 training selection.
- 115-143 scalar BO; 145-155 pool; 157-171 Pareto; 173-185 extensions; 187-197 outcome isolation.
- 199-229 execution policy; 201-215 proposed CLI (not present today); 219 package budget; 223 stop;
  225 verification selection; 227-229 lanes.
- 231-300 GUI; 302-322 artifacts/interfaces; 324-353 execution order/tests; 355-369 dependencies.

---

## 14. One-paragraph direction for the senior agent

You are inheriting a technically healthy optimizer pipeline that has been aimed at a control task
(50x50, f0 1280) chosen for software reasons. The owner's product target is a wider horn (60-80
degrees) with pattern control at 700 Hz, and the arithmetic says that target is feasible while the
current one is not. The cheapest high-value move is to freeze a new brief (prefer 80x80 @700 for
solvability, or the owner's chosen pair), rescore the existing raw archive under it at zero BEM cost,
and then spend a small, explicitly labeled pilot budget on one or two CMA seeds plus verification.
Keep BoTorch, keep the algorithm-math lane (seed variance, CMA vs BO, staged/joint) as a separate
track, stop extending the 50x50 atlas and the v7 ext-throat cell, fix the day report and CPU parity,
and do not change production defaults, cache behavior, or frozen contracts. If the rescore shows a
usable cohort, the first M1/M2 artifact can be a real candidate for the owner's house; if it does
not, say `insufficient_evidence` and run the smallest pilot that creates the missing data.
