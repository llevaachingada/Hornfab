# Implementation plan, 2026-11-12 day: hardening and search improvements while the GPU + CPU lanes run

**Reader:** an orchestrator agent (moderate reasoning) that dispatches parallel coding subagents. **Author:** the
senior lead. Every choice marked DECIDED is final; execute it, do not redesign it. If something is genuinely
blocked, append the reason to `NOTES_FOR_SENIOR.md` and move to the next task.

**Why these tasks:** a two-lane solve queue is producing replicate seeds, a narrowed-vs-control A/B, a staged-vs-joint
A/B and a CPU-vs-GPU cross-check (`runs/nights/{gpu,cpu}_day_2026-11-12.yaml`). The highest-value work while it runs
is (1) the analysis tooling that turns those runs into answers, (2) search features that use the answers (data
warm starts, linked knobs, automatic narrowing, valid-only budgets), (3) the calibration harness the next night
needs, and (4) data/ops hardening. Inputs: `C:\Users\hunte\Hrns\study_2026-11-12\COMPUTE_STUDY.md` (+ its
`sensitivity_analysis.py`, `runs_inventory.csv`), `docs/SENIOR_PLAN_2026-11-12.md`, `docs/OPENCODE_HANDOFF_2026-11-12.md`,
PR #27's evidence (v6 vs v7 top-20 shortlists disagree: tau < 0 in every class).

---

## 0. Rules (non-negotiable)

1. **Do not touch the main checkout** `C:\Users\hunte\Hrns\hornlab-search` (the queues run from its working tree on
   branch `day/2026-11-12-queue`), `.venv`, `runs/`, `cache*/`, `dataset*/`. No `pip install`, no pin bumps.
2. **No GPU, no solves, no `gpu-clean`, no `selftest`, no Julia** from any worker. Offline code and tests only.
3. **CPU budget:** the CPU lane uses 12 of 24 threads. Each worker runs only its own targeted tests while developing;
   **at most two full offline suites at once** machine-wide (orchestrator serialises them). Full suite command, run
   from inside the worktree: `PY -m pytest -q -p no:cacheprovider -m "not gpu and not slow"` where
   `PY = C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`.
4. **One worktree per task group**, from `origin/main`:
   `git worktree add C:\Users\hunte\Hrns\oc-wt\<ID> -b day/<ID>-<slug> origin/main`. Workers edit only the paths their
   group owns (section 2). Shared docs (`docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/INDEX.md`, `docs/CODE_MAP.md`)
   are edited only by the orchestrator at merge time; workers put that text in their PR body under
   `## Continuity entry` and `## Index/CODE_MAP lines`.
5. **Defaults never change** unless the task says so: every new behaviour is opt-in by config key or CLI flag, and
   existing config hashes / solve hashes / golden tests must stay identical.
6. Tests: fix the code, never weaken an assertion. Every new module gets tests; every PR body pastes the junitxml
   counters of its targeted tests and the full suite.
7. PRs: one per group, base `main`, merge commit only (never squash), CONTINUITY + ISSUES in the merging commit.
   PR bodies end with the generator line the platform uses; no model names in PRs or commits beyond the
   `Co-Authored-By` trailer.
8. **Read real data read-only:** analysis tools may READ `runs/`, `dataset/` in the main checkout (pass the path as an
   argument; default to the repo-relative path) but never write there. Outputs go to an `--out` folder.

## 1. Dispatch order

| Group | Title | Value | Size | Parallel? |
|---|---|---|---|---|
| **A** | Evolutionary-analysis toolkit | answers today's experiments | L | yes |
| **B** | Search features: warm start, linked knobs, auto-narrow, valid-only budget, round-throat gate flag | faster, better horns | L | yes |
| **C** | Calibration harness + throughput defaults evidence | unblocks the next night | M | yes |
| **D** | Night/data ops hardening | fewer failed nights | M | yes |
| **E** | GUI: analysis + elites + lanes | owner can see results | M | after A's schemas (start with D-independent parts) |
| **F** | Docs and issue hygiene | coherent state | S | yes |

Launch A, B, C, D, F at once (5 workers). Start E when A's output schema (A.0) is committed to A's branch (E reads
the JSON schema, not A's code). Merge order: F (docs only) -> D -> A -> C -> B -> E. Finally, **after both queues
have finished** (check `tools\night_status.py`), merge PR #25 (line endings) last, then pull `main` into the main
checkout with `git checkout main && git pull --ff-only`.

---

## 2. Task groups

### Group A - evolutionary-analysis toolkit (owns `tools/analysis/**`, `tests/test_tools_analysis_*.py`)

DECIDED: pure-Python + numpy/scipy (already installed); optional `sklearn` only behind `try/except` (permutation
importance falls back to Spearman). Each command: `PY tools\analysis\<name>.py --runs-dir <path> ... --out <dir>`,
writes `<name>.json` (machine-readable, schema in A.0) + `<name>.md` (tables) + PNG charts via matplotlib
(`Agg` backend). Never import from the GUI. Never write into `runs/`.

- **A.0 Schema** `tools/analysis/schema.md`: one JSON shape per report (fields, units). Commit FIRST (E depends on it).
- **A.1 `convergence.py --run <dir> [--run <dir> ...]`**: best-so-far J vs valid-evaluation index (and vs wall
  seconds when timestamps exist), evals-to-within-1%/5% of final best, last-20%-improvement, refusal rate by kind
  per window of 50. Reads `search.ndjson` (`objective`, `ok`, `kind`, `cached`, `n`). Cached rows count as
  replays, not new evals.
- **A.2 `seed_variance.py --group name=<dir>,<dir>,...`**: for runs of the SAME config and brief with different CMA
  seeds: per-seed best J, median, spread (max-min), the 2026-10-23 rule "A beats B only when medians differ by more
  than both spreads", and the distance between best designs in normalised knob space. Refuse groups mixing
  objective version, brief or family (error, not warning).
- **A.3 `sensitivity.py --run <dir>`**: per-knob Spearman rho vs J on valid evals; top-decile vs all distribution
  shift; permutation importance if sklearn; productionise `study_2026-11-12/sensitivity_analysis.py` (copy logic,
  cite it).
- **A.4 `links.py --run <dir>`**: candidate linked knobs: |rho| >= 0.6 between knob pairs in the top decile, plus the
  CMA covariance (`cma_covariance*.json` in the run dir if present: eigenvectors with one dominant direction across
  2-3 knobs). Output proposed link expressions `knob_b = a * knob_a + b` (least squares on the top decile) with R².
  These feed B.2.
- **A.5 `walls.py --run <dir>`**: bound walls (top-decile fraction within 3% of lo/hi per knob) and a proposed
  narrowed/widened box. Feeds B.3.
- **A.6 `ab_compare.py --a <dir>[,<dir>] --b <dir>[,<dir>] --label-a --label-b`**: equal-budget comparison (best J at
  matched valid-eval counts, final medians and spreads, the rule from A.2). Used for narrow-vs-control and
  staged-vs-joint.
- **A.7 `lane_parity.py --gpu <verify run dir> --cpu <verify run dir>`**: per design (same design_hash) max |dSPL| over
  frequencies and angles from the stored responses (`designs/<hash>/response.npz` or the solve cache path the run
  records), J difference; PASS when >= 3 designs agree within 0.2 dB (CP-7b). This decides whether `dataset_cpu`
  may join `dataset/` (D.3).
- **A.8 `report_day.py --spec <yaml>`**: runs A.1-A.7 from one YAML spec and writes one `REPORT.md` with every chart.
  Ship `tools/analysis/specs/day_2026-11-12.yaml` with today's groups (orchestrator fills the run dir names from
  `runs/nights/{gpu,cpu}_day_2026-11-12/summary.jsonl` when the jobs end; the job ids are: g0/c1 parity; g1+g2
  core_law seeds 1030/1031; g3 narrow vs g4 control; g5 staged A/B dir `runs/staged_ab_2026-11-12`; g6+g7+c2 v6
  seeds 1234/1235/1236; g8, g9 atlas resumes).
- Tests: synthetic run dirs built in `tmp_path` (write small `search.ndjson`/`config.yaml`/`run.json`); one golden per
  tool. No real data in tests.

### Group B - search features (owns `hornlab_search/config.py`, `hornlab_search/search/cma.py`, `hornlab_search/search/evaluate.py`, `hornlab_search/search/pin_from_cma.py`, new `hornlab_search/search/warmstart.py`, `hornlab_search/search/links.py`, `tests/test_search_*.py`, `tests/test_config_*.py` new files only, `docs/reference/PARAMETERS.md`)

All opt-in; absent keys = today's behaviour byte for byte (prove with a test that the default config hash and the
first 5 CMA asks for `examples/osse_baseline.yaml` seed 1234 are unchanged).

- **B.1 Data warm start** `search.warm_start: {from_runs: [<dir>...], top_k: 10, sigma_from_spread: true}`:
  the CMA mean starts at the best valid design among those runs that has the SAME family and knob names (normalised
  in this config's box; designs outside the box are clipped and counted); `sigma0` = clamp(median top-k spread per
  knob, 0.05, sigma0). Refuse (ConfigError) runs of another objective version or brief unless
  `allow_cross_brief: true`. Record the warm-start source hashes in `run.json`. DECIDED: warm start never changes
  the solve hash.
- **B.2 Linked knobs** `links: {<knob>: {from: <knob>, scale: a, offset: b, min: .., max: ..}}`: the linked knob is
  removed from the CMA dimension and computed from its parent before meshing (then clipped to its own bounds).
  `params` stored in `search.ndjson` include the computed value; `run.json` records the links. Seed params for a
  linked knob are ignored with a warning. One level only (no chains); cycles and unknown knobs are ConfigError.
- **B.3 `hornlab-search narrow --run <dir> [--wall-frac 0.03] [--out <yaml>]`**: writes a config copied from the run's
  `config.yaml` with ONLY the bound changes from A.5-style wall analysis (implement the analysis in
  `search/pin_from_cma.py` or a new helper, not by importing `tools/analysis`), a new seed (+1), `name: <name>_narrow`,
  and a header comment listing exactly what changed and why (the hand-made
  `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4_narrow.yaml` is the reference format). Never
  touch any other key (the study's auto-generated version changed six unannounced keys; a test must catch that).
  DECIDED: add the subcommand in `cli.py` - Group B owns `cli.py` for this subcommand only.
- **B.4 Valid-only budget** `search.budget_counts: valid` (default `new`, today's semantics): refusals (invalid
  geometry / envelope / too-large) do not consume budget, with a hard ceiling `search.max_attempts` (default
  4 x budget) so a box that refuses everything still stops. Report both counts in the final summary line.
- **B.5 Round-throat gate as a brief flag** `gates: {round_throat: true}` in briefs: applies the existing C4 refusal
  (`_refuse_if_throat_misfits` in `search/evaluate.py`, today v7-only) to any single-entry objective version when
  set; v7 keeps it on regardless. Default off for every existing brief.
- Docs: `docs/reference/PARAMETERS.md` section per new key with one example each.

### Group C - calibration harness + throughput evidence (owns `tools/calibration/**`, `tests/test_tools_calibration*.py`, `docs/evidence/THROUGHPUT_N1_2026-11-12.md`, `examples/calibration/**`)

- **C.1 `tools/calibration/plan_calibration.py --designs <csv|run dir> --top N --out <night.yaml>`** generates a
  runnable night file (runner format, `tools/run_campaign_night.py`) for the P0 calibration (NEXT_DEV_PRIORITIES P0
  item 2): for each stored finalist, `verify --designs <hash>` under (a) band-split vs single mesh, (b) observation
  distance 2 m vs 10 m, (c) epw 6 vs 9 in 2.5-5.5 kHz. Variants are produced as temporary config overlays written
  to `examples/calibration/<date>/` (use `extends:` from PR #29 so each overlay is 3-6 lines). Acceptance thresholds
  from P0: Re z +-0.03, beamwidth +-2 deg, DI +-0.2 dB.
- **C.2 `tools/calibration/compare_calibration.py --night <dir> --out <dir>`**: reads the verify run dirs the night
  produced, pairs variants per design, reports pass/fail per threshold and whether the screen ranking survives
  (Spearman of J across variants). Synthetic tests only.
- **C.3 Throughput evidence** `docs/evidence/THROUGHPUT_N1_2026-11-12.md` from `runs/nights/gpu_2026-11-12/summary.jsonl`
  and its `n1_*.log` files (read-only): table per arm (dofs, fused, prefetch, freq batch, s/batch, peak VRAM, exit),
  the 8k fused-off+prefetch OOM, and the DECIDED recommendation: fused ON for every CUDA config; prefetch OFF at
  >= 8k dofs; `freq_batch_size` 12 ("never hurt"). Do NOT flip defaults in code in this group; write the exact
  config diff as a proposal (the owner flips after the calibration night).

### Group D - night/data ops hardening (owns `tools/run_campaign_night.py`, `tools/night_status.py`, `tools/night_queue/**`, `tools/data/merge_lane_dataset.py` (new), `tools/night_report.py` (new), `tests/test_night_*.py`, `tests/test_tools_night*.py`, `tests/test_tools_data_merge*.py`)

- **D.1 Two-lane `night_status.py`**: show both lanes (queue logs `runs/nights/queue_*`), the running job per lane, its
  run dir row count and newest-row age, lock holders (`runs/.gpu.lock`, `runs/.cpu.lane.lock`, alive or stale), and
  an ALERT line when a lane's newest row is older than 30 min while its job is running.
- **D.2 Runner robustness** (`run_campaign_night.py`): (a) a job whose log contains `GPU busy` is recorded as
  `blocked` (not `ok`) and retried ONCE after 120 s; (b) the stale-lock takeover is logged explicitly; (c) the
  summary row for every job records `lane`, `backend` (parsed from argv/config), and the parsed run dir for both job
  kinds (search and command); (d) `--dry-run` validates every argv path exists (config, brief, resume dir, run dir)
  and fails listing all missing paths. Regression test for the 2026-11-12 failure modes: `--lane` passed to
  `gpu-clean`, GPU-busy cascade, "0 evals" for command jobs.
- **D.3 `tools/data/merge_lane_dataset.py --src dataset_cpu --dst dataset --parity <A.7 json>`**: dry run by default;
  merges CPU-lane records into the main dataset ONLY when the A.7 parity report says PASS; tags each merged row
  `provenance.lane = "cpu"`; backup + atomic writes (model: `tools/data/renumber_objective_v5_to_v7.py`); idempotent.
- **D.4 `tools/night_report.py --night <name> [--night <name>] --out docs/evidence/NIGHT_<date>.md`**: generates the
  morning report from summary.jsonl + run dirs (per lane: jobs, exits, evals, valid/refused, best J per run, wall
  time, evals/hour, VRAM peaks, blocked/failed jobs with the first error line). Uses `[measured]` labels per the
  hornlab-evidence skill. Synthetic-night tests.

### Group E - GUI (owns `hornlab_search/gui/**`, `tests/test_gui_*.py` new files only)

Start after A.0 is on A's branch (read the schema from that branch: `git show day/A-analysis:tools/analysis/schema.md`).
- **E.1 Analysis page** `#/analysis`: lists `REPORT.md`/JSON outputs found under a configurable folder
  (default `runs/analysis/`), renders convergence (best-so-far curves, one colour per seed), seed-variance table
  with the "A beats B" verdict, sensitivity bars, link candidates, walls. Read-only; never runs analysis itself.
- **E.2 Lanes panel** on the home page: the D.1 status as JSON from a new `GET /api/lanes` (implement the status
  read inside `gui/data.py`; do not import `tools/`).
- **E.3 Elites catalog** `#/elites`: cards for designs listed in a gate-audit CSV (`docs/data/gate_audit_*/` or
  `scratch/gate_audit_elites_*`), each with J vN, coverage cell, gate chips (reuse L2's chips), links to the run.
- Headless tests per view (follow `tests/test_gui_views_l2.py`).

### Group F - docs and issue hygiene (owns `docs/history/**`, `docs/NEXT_DEV_PRIORITIES.md`, `docs/SENIOR_PLAN_2026-11-12.md`, `docs/OPENCODE_HANDOFF_2026-11-12.md`)

- **F.1** `docs/CONTINUITY.md` order is broken by merges: produce the re-ordered file (entries sorted newest first by
  their leading `YYYY-MM-DD` + time when present, stable otherwise; entries before 2026-11-01 moved to
  `docs/history/CONTINUITY_2026-10-22_2026-10-31.md`). DECIDED: F produces it as a patch file
  `docs/history/continuity_reorder_2026-11-12.patch` for the orchestrator to apply LAST (CONTINUITY is edited by every
  merge today).
- **F.2** `docs/NEXT_DEV_PRIORITIES.md`: add P15 = this plan; mark P14 lanes L1-L5 DONE with PR numbers (#25-#31);
  record the open owner decisions (loading objective split v6/v7 confirmed by PR #27's tau evidence; round-throat
  default; sysmem setting; HF write access for Collin; printing).
- **F.3** `docs/SENIOR_PLAN_2026-11-12.md`: status column per WP (done / in this plan / open).
- **F.4** Orchestrator action (not a worker): close GitHub issue #13 with a comment citing its fixes merged on
  2026-10-22 (`gh issue close 13 --comment "..."`), then mirror in `docs/ISSUES.md`.

---

## 3. After merges (orchestrator)

1. When both queues are done: `PY tools\night_status.py --since-hours 24`; then run Group A on today's runs:
   `PY tools\analysis\report_day.py --spec tools\analysis\specs\day_2026-11-12.yaml --out runs\analysis\day_2026-11-12`
   (fill run dirs first), and D.4 for both nights. Commit the generated `REPORT.md` as
   `docs/evidence/DAY_2026-11-12_ANALYSIS.md` (+ PNGs under `docs/evidence/day_2026-11-12/`).
2. If A.7 parity PASSES: `PY tools\data\merge_lane_dataset.py --src dataset_cpu --dst dataset --parity <json> --apply`.
3. Merge PR #25 (line endings) last, pull main into the main checkout.
4. Next night (owner GO): C.1's calibration night first; then the configs B.3 generates for the walls A.5 finds, with
   B.1 warm starts from today's best runs and B.2 links proposed by A.4 (only links with R² >= 0.8).

## 4. Out of scope today
MEH work; objective v8; pin bumps / fork changes (WP1 identity-cache patch waits for the calibration night); flipping
any default; HF upload (do it after the merge of D.3, between nights); anything needing the owner.
