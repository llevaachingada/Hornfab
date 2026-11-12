# OpenCode orchestrator handoff, night of 2026-11-12

**Reader:** an OpenCode orchestrator agent with parallel worker agents. **Author:** the senior lead (Claude),
who made every architecture decision below; your job is to execute, verify and report, not to redesign. Where
this document says DECIDED, do not reopen it. Where something is genuinely blocked, write it to
`NOTES_FOR_SENIOR.md` (append only) and move on to the next item.

Background (read once, do not re-derive): `docs/SENIOR_PLAN_2026-11-12.md` (the plan this executes),
`CLAUDE.md` (rules: GPU hygiene, file ownership, push rule), `docs/research/CPU_SECOND_LANE_HARDENING_2026-10-28.md`
(the CPU lane design; its section 12 questions are answered in section 4 below).

---

## 0. Ground rules (non-negotiable)

1. **Repo:** `C:\Users\hunte\Hrns\hornlab-search`, GitHub `llevaachingada/Hornfab`. Interpreter is always
   `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` (call it `PY` below). Never bare `python`.
2. **The main checkout belongs to the GPU night.** After step 1.2 it sits on `main` and NOBODY edits, checks out,
   pulls, or runs pytest in it until the night ends. The night imports code from it.
3. **Workers code in their own worktrees** under `C:\Users\hunte\Hrns\oc-wt\<lane>` (step 1.3). Run pytest from
   inside the worktree (`cd` there, then `PY -m pytest ...`): the worktree's code is what gets imported.
4. **Never change `.venv`** (no `pip install`, no pin bumps) while the night runs. The pins are DECIDED:
   mesher `jamescollinharky/hornlab-waveguide-mesher@55da4f4`, beat-bem `llevaachingada/hornlab-beat-bem@0850ef3`.
5. **Offline tests only in worktrees:** `PY -m pytest -q -p no:cacheprovider -m "not gpu and not slow"`. Never
   run GPU-marked tests, `selftest`, or any solve from a worktree while the night runs.
6. **Never kill `julia.exe` by image name** and never `taskkill /T` a runner. Use `hornlab-search gpu-clean` only
   between jobs, and only from the night controller.
7. **Push rule:** every pushed commit updates `docs/CONTINUITY.md` (new dated entry at the TOP, newest first) and
   `docs/ISSUES.md` in the same commit. Branch per lane, PR per lane, merge commit (not squash). Commit trailer:
   `Co-Authored-By: <your model> <noreply@...>` per your platform; no model names in PR bodies.
8. **File ownership:** each lane below lists the ONLY paths it may edit. Two lanes never edit the same file. The
   shared docs (`CONTINUITY.md`, `ISSUES.md`, `INDEX.md`, `CODE_MAP.md`) are edited ONLY by the orchestrator at
   merge time (step 5), never by workers. Workers put their CONTINUITY text in their PR body under
   `## Continuity entry`.

## 1. Setup (orchestrator, serial, ~15 min)

1.1 Confirm the integration PR has merged: `gh pr view 24 --json state` must say `MERGED`. If it is still open,
    STOP and wait (the senior is landing it); do not merge it yourself.
1.2 In the main checkout: `git fetch origin`, `git checkout main`, `git reset --hard origin/main` only if
    `git status --short` is empty (if not empty, STOP and report). Then
    `PY -c "import hornlab_search, importlib.metadata as m; print(m.distribution('hornlab-beat-bem').read_text('direct_url.json'))"`
    must show `0850ef3`, and the same for `hornlab-waveguide-mesher` must show `55da4f4`.
1.3 Worktrees (one per lane, each on a new branch from `origin/main`):
    ```
    git worktree add C:\Users\hunte\Hrns\oc-wt\L1 -b lane/L1-cpu-lane origin/main
    git worktree add C:\Users\hunte\Hrns\oc-wt\L2 -b lane/L2-gui-versions origin/main
    git worktree add C:\Users\hunte\Hrns\oc-wt\L3 -b lane/L3-scoring-truth origin/main
    git worktree add C:\Users\hunte\Hrns\oc-wt\L4 -b lane/L4-hygiene origin/main
    git worktree add C:\Users\hunte\Hrns\oc-wt\L5 -b lane/L5-data-interop origin/main
    ```
1.4 Launch the GPU night (section 2) BEFORE dispatching workers. Then dispatch L1-L5 in parallel (section 3).

## 2. GPU night (starts immediately, single GPU lane)

Night file `runs\nights\gpu_2026-11-12.yaml` (runtime, not committed), jobs strictly in this order. Every config
path exists on `main`; if one does not load (`PY -m hornlab_search.cli search --config <cfg> --budget 1
--dry-run` where supported, or `PY tools\shape_check.py <cfg>`), drop that job, note it, keep going.

```yaml
night: gpu_2026-11-12
jobs:
  - {id: n1_throughput, kind: command, timeout_s: 9000,
     argv: [".venv\\Scripts\\python.exe", "tools\\bench\\throughput_matrix.py", "--help"]}
  - {id: n3_core_atlas_resume, kind: search, mode: screen, budget: 400,
     config: examples/typologies/atlas_2026-10-30/atlas__ath_core.yaml}
  - {id: n4_ext_throat_atlas, kind: search, mode: screen, budget: 200,
     config: examples/typologies/atlas_2026-10-30/atlas__osse_ext_throat.yaml}
  - {id: n5_lecleach_v6, kind: command, timeout_s: 10800,
     argv: [".venv\Scripts\python.exe", "-m", "hornlab_search.cli", "search",
            "--config", "examples\typologies\lecleach_rollback.yaml",
            "--brief", "examples\briefs\lecleach_rollback_1in_v6.yaml",
            "--budget", "150", "--mode", "screen"]}
  - {id: n7_staged_ab, kind: command, timeout_s: 10800,
     argv: [".venv\\Scripts\\python.exe", "tools\\run_staged_search.py", "--out", "runs\\staged_ab_2026-11-12", "--both"]}
  - {id: n6_verify_core_atlas, kind: command, timeout_s: 7200,
     argv: [".venv\Scripts\python.exe", "-m", "hornlab_search.cli", "verify",
            "--run", "runs\20261030T111108Z-screen-377bbe", "--top", "8"]}
```

DECIDED details:
- **n1:** before the night, open `tools/bench/throughput_matrix.py --help` in a worktree and replace the `--help`
  argv with its real arguments for: fused on vs off, mesh prefetch on vs off, `freq_batch_size` 1 vs 4 vs 12,
  on three stored designs of ~1k, ~4k and ~8k dofs (pick from `runs/elites_20261030_*/designs/`). Each CUDA
  timing must record the WDDM shared-usage reading (`tools/bench/_bench_common.GpuMemPeak`); a run with shared
  usage > 200 MiB is a spill and is reported as invalid, not as slow.
- **n3:** RESUME the existing ATH CORE atlas: make n3 a `command` job with argv
  `search --config examples\typologies\atlas_2026-10-30\atlas__ath_core.yaml --resume runs\20261030T111108Z-screen-377bbe --budget 400 --mode screen`
  (the replay is cache hits). If the CLI refuses the resume (config hash changed by the merge), add
  `--allow-config-change` once; if it still refuses, start fresh with the plain `search` job above.
- **n4:** the config exists on main (`atlas_2026-10-30/atlas__osse_ext_throat.yaml`, cma_me). Before queuing,
  confirm it loads: `PY tools\shape_check.py examples\typologies\atlas_2026-10-30\atlas__osse_ext_throat.yaml`
  (or `--help` for its args). It scores whatever objective its brief names; if that brief says `version: 7`, fine.
- **n5:** the first real objective-v6 search (Collin's Le Cléac'h objective); feeds L3.
- **n7:** the staged-search A/B that Collin's PR #17 left owed on the GPU box
  (`docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`); check `tools\run_staged_search.py --help` first; append its
  COMPARE.md to that evidence doc in the morning report.
- Launch detached so it survives sessions:
  ```
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights gpu_2026-11-12 -Log runs\nights\queue_2026-11-12.log"
  ```
- Skip list (do not queue): b3a 80x80 (structural 827 Hz Re z dip); any MEH job (MEH is paused).

## 3. Lanes (parallel workers, each in its worktree)

### L1 - CPU second lane (the big one; ~3-4 h) - worktree `oc-wt\L1`

**Goal:** a second, independent search on the CPU BEM backend runs at the same time as the GPU night, safely,
with per-lane logging, so tonight's run IS the measurement. No separate pre-test.

**Owns:** `hornlab_search/solve/worker.py`, `hornlab_search/search/hygiene.py`, `hornlab_search/search/gpulock.py`,
`hornlab_search/config.py` (only the `solve.julia_threads` knob), `tools/run_campaign_night.py`,
`tools/night_queue/queue.ps1`, `tests/test_solve_worker*.py`, `tests/test_search_hygiene*.py`,
`tests/test_night_runner*.py` (create), `tests/test_config_julia_threads.py` (create), `CLAUDE.md` GPU rules
section ONLY (one paragraph, see L1.6).

**DECIDED (answers to CPU_SECOND_LANE section 12):**
1. Topology = Option B: shared `runs/`, but the CPU lane uses its OWN `--cache-dir cache_cpu` and
   `--dataset-dir dataset_cpu`. Merging `dataset_cpu` into `dataset/` is a later tool, not tonight.
2. "One GPU solve at a time" means one CUDA solve; one CPU-backend search may run beside it. Amend CLAUDE.md.
3. Lane identity = the BEAT worker registry directory: each lane sets its own `HORNLAB_BEAT_WORKER_DIR`
   (`runs\lanes\gpu\workers`, `runs\lanes\cpu\workers`). Host-cleanup code kills ONLY host trees whose
   command line carries its own lane's worker dir. **A host whose lane cannot be determined is NEVER killed**
   (logged as `unknown host, left alone`).
4. `solve.julia_threads` (int, optional) sets `JULIA_NUM_THREADS` and the BLAS thread count for that run's
   host. It is NOT part of the solve hash (it does not change results). CPU lane value: **12** (16 physical
   cores; leave 4 for gmsh meshing, the GPU lane's feeder and the OS).
5. A `runs\.cpu.lane.lock` marker (same mechanism as `search/gpulock.py`, separate file) is held by the CPU lane.
   `gpu-clean` and the night runner's pre/post hygiene must not touch hosts of a lane whose lock is live.
6. `cuda_fused` is dropped for non-CUDA backends (already the merged behaviour from PR #17: verify with a test,
   do not re-implement).
7. Second dataset root accepted (see 1).
8. No pre-measurement gate: the night's per-lane logs are the measurement (L1.5).

**Tasks:**
- L1.1 `solve/worker.py`: `clear_stale_hosts(force=...)` and `recover_after_failure` gain a `lane` argument
  (default = the lane from `HORNLAB_BEAT_WORKER_DIR`, else `None`). Classify each host by the `--dir`
  argument on its command line; kill only same-lane trees; unknown = keep. Unit-test the classifier with
  fake process tables (no real processes).
- L1.2 `search/hygiene.py` and the `gpu-clean` CLI path: same lane rule; `gpu-clean` without a lane only kills
  hosts in the GPU lane's dir and logs the rest.
- L1.3 `tools/run_campaign_night.py`: REMOVE the `taskkill /F /IM julia.exe` pre-hygiene (lines ~359-430);
  replace with `hornlab-search gpu-clean` (lane-aware). Add per-job optional keys `backend:`, `cache_dir:`,
  `dataset_dir:`, `env:` (dict) passed through to the search subprocess (`--backend`, `--cache-dir`,
  `--dataset-dir`, environment). Add a top-level `lane: gpu|cpu` key: `cpu` nights skip the GPU lock and the
  nvidia-smi VRAM accounting, take `.cpu.lane.lock`, and set `HORNLAB_BEAT_WORKER_DIR` to the cpu lane dir.
  Offline tests for argv building and the lane branching (pure helpers; the module is already import-light).
- L1.4 `config.py`: `solve.julia_threads` (positive int, optional), excluded from `solve_spec().hash()`. Test:
  two configs differing only in it have identical solve hashes.
- L1.5 Logging: every evaluation row in `search.ndjson` already has timings; add `lane` and `backend` fields
  (additive) so the morning report can compute evaluations/hour per lane. If `HORNLAB_STAGE_TIMING=1` (PR #23)
  is cheap, set it in both lanes' `env:`.
- L1.6 CLAUDE.md GPU rules: one paragraph "Two lanes" stating decisions 2, 3, 5.
- L1.7 PR `lane/L1-cpu-lane` -> main, offline suite green in the worktree. **The orchestrator merges L1 into
  main only between two GPU night jobs** (watch `night_status.py`; merge right after a job ends), then pulls
  main into the main checkout with `git pull --ff-only` (the night controller re-reads code per job).

**CPU night (starts after L1 is merged):** `runs\nights\cpu_2026-11-12.yaml`, `lane: cpu`, launched with its
own detached controller and its own log `runs\nights\queue_cpu_2026-11-12.log`. Jobs (DECIDED workload: the
CPU is relatively best on small meshes and is the only engine for big/double-precision solves):
```yaml
night: cpu_2026-11-12
lane: cpu
jobs:
  - {id: c1_verify_elites_hypex, kind: command, timeout_s: 14400,
     argv: [".venv\\Scripts\\python.exe", "-m", "hornlab_search.cli", "verify", "runs\\elites_20261030_hypex", "--top", "17", "--backend", "beat_cpu", "--cache-dir", "cache_cpu", "--dataset-dir", "dataset_cpu"]}
  - {id: c2_lecleach_rollback_small, kind: search, mode: screen, budget: 150, backend: beat_cpu,
     cache_dir: cache_cpu, dataset_dir: dataset_cpu, env: {HORNLAB_STAGE_TIMING: "1"},
     config: examples/typologies/lecleach_rollback.yaml}
```
(Check each argv against `--help` first; the verify subcommand's exact flags win over this sketch.)

### L2 - GUI: versions, gates, the new views (~2-3 h) - worktree `oc-wt\L2`

**Owns:** `hornlab_search/gui/**`, `tests/test_gui_*.py`.
- L2.1 Brief editor objective versions: `objectiveVersionOptionsHtml` in `gui/static/app.js` (~line 1884)
  offers 1-3 only. Offer 1-7 with these exact labels: 1 "v1 legacy", 2 "v2 detrended", 3 "v3 below-f0 mask",
  4 "v4 tolerance-normalised", 5 "v5 MEH system", 6 "v6 loading_smooth (Le Cléac'h)", 7 "v7 loading + CD
  gates (hi-fi/PA)". Default for a NEW brief stays as today (do not change defaults).
- L2.2 Version guard: wherever runs or designs are ranked or compared by J (run list, compare view, Design
  cloud from PR #22), show `J vN` and, when the set mixes versions, show a banner "J from different objective
  versions is not comparable" and sort within version groups. `gui/data.py` already reads
  `objective_version` (~line 665): reuse it.
- L2.3 Gates column: if a run has a gate audit CSV (`docs/data/gate_audit_*/gate_audit.csv` or
  `scratch/gate_audit_*`), show per-design pass/fail chips for the gates present (round throat, loading,
  f11, CD). Absent audit = no column (never invent).
- L2.4 Smoke the three new views headlessly against stored runs (no solves): Design cloud (`/api/umap/<run>`),
  the Boundary Lab A/B report (PR #23), the 3D evolution view. Use the existing GUI test patterns
  (`tests/test_gui_*.py`); add one test per view that loads a fixture run. Screenshots are NOT required tonight.

### L3 - Scoring truth, offline (~2-3 h, CPU-light) - worktree `oc-wt\L3`

**Owns:** `tools/rescore/**`, `docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md` (create),
`docs/evidence/RESCORE_V6_V7_2026-11-12.md` (create), `tests/test_tools_rescore*.py`.
- L3.1 Write the loading reconciliation doc: the exact definitions of v4 `load` (`objective/terms.py::load_term`),
  v6 `load_near`/`z_smooth` (`objective/scalar_v6.py`), v7 `load`/LFP (`objective/scalar_v7.py`), each with
  file:line and a 3-line plain description; then what `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` and
  `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md` say. **DECIDED recommendation to write
  down:** keep v6 for the Le Cléac'h / rollback class and v7 for CD briefs; do NOT create a v8 tonight. List
  the differences an owner would need to approve to merge them later.
- L3.2 Offline re-score: using `tools/rescore/gate_audit.py` (and its `parse_stored_row`, which is
  version-agnostic), re-score every stored valid row in `dataset/` under v6 AND v7 (use one v6 brief and one v7
  brief per brief class; pick from `examples/briefs/campaign_2026-10-26_v6/` and
  `examples/briefs/hardened_2026-10-29_v5/` which now say version 7). Output: per brief class, top-20 under
  each, Kendall tau between them, gate pass counts. Never write to `dataset/`; outputs to
  `scratch/rescore_2026-11-12/` + the evidence doc.
- L3.3 Driver check (report-only): for every `examples/drivers/*.yaml`, list missing `Mmd`/source URL/published
  sensitivity; if `hornlab_search/driver/compression.py` exposes a sensitivity prediction, compare it with the
  datasheet value and flag > 2 dB gaps. Table in the evidence doc. No code change to the driver model tonight.

### L4 - Hygiene (~1-2 h) - worktree `oc-wt\L4`

**Owns:** `docs/history/**`, `docs/NEXT_DEV_PRIORITIES.md`, `.gitattributes`, `NOTES_FOR_SENIOR.md` (moving
resolved items to `docs/history/NOTES_FOR_SENIOR_resolved.md`).
- L4.1 `.gitattributes`: `* text=auto eol=lf`, `*.ps1 text eol=crlf`, `*.bat text eol=crlf`,
  `*.npz binary`, `*.msh binary`, `*.png binary`. Then `git add --renormalize .` in its OWN commit
  ("chore(eol): renormalise"), nothing else in that commit.
- L4.2 `NEXT_DEV_PRIORITIES.md`: mark DONE: P1 (fused CUDA), P2 (12 kHz pass), P3 (Metal, PR #17), P10 items 1-3,
  P11 (HF), P13 (MEH: "implemented; follow-ups paused by owner 2026-11-12"). Keep P14 on top. Do not delete
  sections; prefix their heading with `[DONE]` or `[PAUSED]`.
- L4.3 CONTINUITY re-order is the ORCHESTRATOR's job at merge time (step 5), not L4's: L4 only creates
  `docs/history/CONTINUITY_2026-10-22_2026-10-31.md` by moving entries dated before 2026-11-01 out of
  CONTINUITY in a single commit done by the orchestrator (see 5.3).

### L5 - Data interop with the collaborator (Collin), two-way (~3 h) - worktree `oc-wt\L5`

**Why (audit 2026-11-12):** every Collin commit (PR #17 squash, PR #22) is in `main`; but the DATA path is
one-way. Collin's own runs (RunPod 4090 Solana screen J 39.6, CMA `20261103T052647Z-screen-cd22a5`, CMA-1000
`20261103T053926Z-screen-8b32a1`) exist only on his pods/machine; nothing brings them here. Two recorded
commitments were never built: a dataset MANIFEST (`docs/plan/07_TASK_DATASET.md` "makes the dataset shareable
with Collin") and design export in the mesher's own parametric config (`docs/plan/12_RESEARCH_BASIS.md` line
332, "a search result opens in his GUI"). After tonight there are also three objective versions and two
backends in the data. L5 makes the data self-describing and two-way.

**Owns:** `hornlab_search/dataset/manifest.py` (create), `tools/hf_sync.py`, `tools/export_config.py` (create),
`tools/data/ingest_foreign.py` (create), `tools/export_campaign_tables.py`,
`docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md`, `tests/test_dataset_manifest.py`, `tests/test_tools_hf_sync*.py`,
`tests/test_tools_export_config.py`, `tests/test_tools_ingest_foreign.py` (all create). NOT `cli.py` (L1 owns
the gpu-clean path there): L5's entry points are `python -m hornlab_search.dataset.manifest` and `tools/*.py`.

**DECIDED:**
- L5.1 `dataset/manifest.py` writes `<dataset_root>/MANIFEST.json`: `schema_version`, total rows, rows by
  `objective_version` x `family` x `backend` x `mode`, distinct `lib_sha`, `created_utc` min/max, per-shard
  sha256 + row count, a `objective_versions` legend (1-7, one line each, from `objective/versions.py`
  comments), the relabel note ("hardened rows dated 2026-10-29 were renumbered 5 -> 7 on 2026-11-12"), and a
  `lab` string (default `hunter-4060`). Read-only over shards; deterministic output (sorted keys). Test on a
  tmp shard fixture.
- L5.2 Export a design in the mesher's own config: `tools/export_config.py --run <run_dir> --top N [--out dir]`
  writes, per design, `<hash>.mesher.json` = the exact dict `hornlab_search` passes to `hornlab_mesher`
  (reuse `design/families.py` `to_mesher_config` or whatever `mesh/build.py` calls; do NOT re-derive keys),
  plus `<hash>.meta.json` (family, params, J, objective_version, terms, brief name, lib_sha). Families the
  mesher builds from a config (OSSE, R-OSSE, ICW, FREEFORM, LOOKUP) only; generator/CAD families are
  listed as skipped with the reason. This is the universal design format (the mesher is shared).
- L5.3 Two-way HF (`tools/hf_sync.py`): `pack` always runs L5.1 first and includes `MANIFEST.json`;
  `push --lab <name>` uploads under a `labs/<name>/` prefix of the same dataset repo (needs the owner to grant
  Collin write access, or Collin uses his own HF repo; support `--repo`); `pull --lab <name> --into
  dataset_ext/<name>` downloads a lab's shards + run dirs. Keep `HF_HUB_DISABLE_XET=1` for uploads from this box.
- L5.4 `tools/data/ingest_foreign.py`: validates every pulled row with `dataset/record.py` `validate_record`,
  tags `lab`, and NEVER writes into `dataset/` (foreign data lives in `dataset_ext/<lab>/`). It writes a
  parity report: designs solved in both labs (same `design_hash` + `mesh_hash` + solve spec) and their SPL
  difference; **rows from another lab are comparable only after >= 3 shared designs agree within 0.2 dB**
  (the CP-7b rule); until then GUI/tools show them as a separate group.
- L5.5 `tools/export_campaign_tables.py`: group and label every table by `objective_version` and `backend`;
  never rank across them (same rule as L2.2).
- L5.6 Runbook: add "what changed 2026-11-12" (v5 -> v7 relabel, MANIFEST, labs/ prefix, how Collin pushes his
  runs) to `docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md`.
- L5.7 **Tonight, after L5 merges** (CPU/network only, no GPU): re-pack and upload the dataset with the
  MANIFEST (`tools/hf_sync.py pack` then `upload`), from the main checkout BETWEEN GPU jobs is not needed (it
  only reads `dataset/` and `runs/`), but never while a job is writing a run dir that is being packed: pack
  `--groups text,dataset` only (solves were uploaded on 11-02; the dataset shards are what changed).

Owner actions for L5 (write to NOTES_FOR_SENIOR.md, do not wait on them): grant Collin write access to
`chingadalleva/hornlab-search-data` (or agree on his own repo); ask Collin to `push --lab collin-4090` his
Solana/SAWMOD run dirs; Collin owes a Metal-vs-4060 parity check (<= 0.2 dB) before Metal rows join (PR #17).

## 4. Hourly check-in loop (orchestrator, all night)

Every 60 minutes:
1. `PY tools\night_status.py --since-hours 2` (GPU) and `PY tools\night_status.py --since-hours 2 --queue-log runs\nights\queue_cpu_2026-11-12.log` (CPU, once started).
2. `nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader` (GPU lane alive?) and the CPU lane's
   newest `search.ndjson` mtime (alive = written within 30 min).
3. Worker lanes: read each worker's last message; if a worker is stuck > 45 min on the same failing test, nudge it
   with the failing test name and "fix the code, never the assertion"; after a second stall, park the lane
   (commit WIP to its branch, note in NOTES_FOR_SENIOR.md) and move on.
4. **Failover rules (DECIDED):**
   - A GPU job fails twice in a row with OOM / worker exit / `GPU busy` exit 3: run `hornlab-search gpu-clean`
     once, then re-queue THAT job in a NEW night file on the **CPU lane** (`backend: beat_cpu`, `cache_dir:
     cache_cpu`, `dataset_dir: dataset_cpu`, budget halved). Never retry the same job on the GPU a third time.
   - A CPU job takes > 2x its estimate or fails: re-queue it on the GPU lane in a new night file AFTER the
     current GPU night (the queue controller's `-WaitPid`), budget unchanged.
   - Spill detected (shared usage > 200 MiB in a log): stop queuing CUDA jobs with > 12,000 dofs; route them to
     the CPU lane.
   - Never run two CUDA jobs at once; never start a controller while another controller of the same lane runs.
5. Append a 3-line status to `runs\nights\checkin_2026-11-12.md` (time, per-lane evals in the last hour, actions).

## 5. Merge sequence (orchestrator)

5.1 Merge order: L1 first (between GPU jobs, it unlocks the CPU lane), then L5 (then run L5.7), L3, L2, L4
    (L4's renormalise commit last: it touches every file).
5.2 For each lane PR: offline suite green in its worktree; CI green; then the orchestrator adds the lane's
    `## Continuity entry` text to `docs/CONTINUITY.md` (top) plus an `ISSUES.md` line in ONE commit on the lane
    branch, then merges with a merge commit.
5.3 CONTINUITY order fix (once, after the lanes): split on `## ` headings, sort entries by their leading date
    `YYYY-MM-DD` newest first (stable for equal dates, keeping file order), move every entry dated before
    2026-11-01 to `docs/history/CONTINUITY_2026-10-22_2026-10-31.md`. One commit, no other change.
5.4 Never merge to `main` in the main checkout's working tree while a GPU job is running; merge on GitHub, then
    `git pull --ff-only` in the main checkout only between jobs.

## 6. Morning report (orchestrator, before stopping)

Write `docs/evidence/NIGHT_2026-11-12.md` (follow the `hornlab-evidence` skill's labelling: [measured] /
[inferred]): per lane evaluations, valid/refused, evaluations per hour, GPU idle share, CPU lane slowdown of the
GPU lane (GPU evals/hour tonight vs `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` section 1, 157.8/h), n1
throughput table, atlas cells gained, the n5 v6 result, failovers taken. Close with a 5-line "what to change
tomorrow". Add it to `docs/INDEX.md`. Commit with CONTINUITY + ISSUES.

## 7. Out of scope tonight (do not start)
MEH work of any kind (Collin's merged MEH path stays as is); objective v8 / any brief re-weighting; pin bumps or fork changes (the WP1 identity-cache
fork patch waits for the n1 numbers); deleting
remote branches; anything needing the owner (sysmem setting, printing, gate levels).
