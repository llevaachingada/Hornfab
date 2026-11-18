# ORCHESTRATOR HANDOFF — 2026-11-17 LATE (paused mid-directive, for the senior-thinking successor)

> **Who this is for:** the next orchestrator/senior-thinking agent taking over
> `C:\Users\hunte\Hrns\hornlab-search`, branch `ccr-260b4b76-fi6b8j` (PR #67).
> **Written by:** the local orchestrator pausing on owner instruction — *stop; do not commit or
> push; hand off*. **Authority for this pass:**
> `scratch/fable_architecture/SENIOR_DIRECTION_2026-11-17_EVENING.md` (the evening senior
> direction — read it first; where it differs from earlier reviews it wins), plus the owner's
> §4 answers reproduced verbatim-in-substance in §3 below. This file grounds CURRENT state;
> `ORCHESTRATOR_HANDOFF_2026-11-17.md` (morning) remains the plan/verification reference.
>
> **The stop instruction is live:** nothing after the two commits in §1.2 has been committed or
> pushed. The working tree is deliberately left uncommitted. Do not commit/push until you have
> re-derived the commit plan in §6.7 and cleared it with the owner.

---

## 1. Ground state

### 1.1 Repository

- Canonical checkout `C:/Users/hunte/Hrns/hornlab-search` (owner amendment 2026-11-12). Umbrella
  `Hrns/` is NOT the working tree.
- Branch `ccr-260b4b76-fi6b8j` (PR #67). HEAD at pause: **`3682173`** — see 1.2.
- Read `AGENTS.md` rules before anything: hard rules 1-8, D3 freeze (§1.4), one-GPU rule,
  `HORNLAB_GPU_LOCK=refuse` for night jobs, never delete `runs/.gpu.lock` by hand, interpreter
  is always `.venv\Scripts\python.exe`, bounded reading budget for CONTINUITY/ISSUES/NOTES.

### 1.2 Commits (PUSH STATE CORRECTED 2026-11-18: everything through HEAD is on origin)

**Owner verification 2026-11-18:** PR #67 on GitHub has head `3682173` with `750223e` directly
under it, and `84339a7` is linked — so ALL commits through HEAD are pushed; only the **uncommitted
files (§1.3)** are at risk in the commit/push plan (§6.9). Do not treat `84339a7`/`750223e`/
`3682173` as at-risk work.

| SHA | What | Who | Note |
|---|---|---|---|
| `3682173` | fix(analysis): harden WP1-WP3 analyzers (guard order, typed refusals, grid mesh evidence, committed parity mode, CI-safe existing-mesh) | **second writer** (concurrent session, landed mid-my-session) | D10 governance item: a second writer is committing to this branch. Count: `f5db35e` was the first. Write the note into `NOTES_FOR_SENIOR.md` and ask the owner who integrates (senior D10). |
| `750223e` | merge: main into PR branch (D2, done by me) | me | Conflict resolved in `docs/CONTINUITY.md` keeping BOTH entry blocks (evening stage-5 entries first, then main's 07:4x/07:1x entries). Merge touched only `docs/CONTINUITY.md`, `tools/night_queue/run_bo_arm.py`, `tools/night_queue/refresh_watchdog.py`, new `tests/test_night_refresh_gate.py` (4 tests, I ran them: pass). **No `hornlab_search/**` change → no package pin moved.** This is the merge the owner asked for before the BO arms started; it landed in time. |
| `84339a7` | fix(examples): correct brief_file depth in the 14 `_w1` space proposals (BOM stripped) (D1, done by me) | me | One line per file (`../../briefs/…` → `../../../briefs/…`), CRLF preserved (verified: 197 CRLF/0 LF), all 14 BOMs stripped and re-verified 0 remaining. This made the 13 queued walls-relieved jobs runnable. |

### 1.3 Working tree at pause (uncommitted — owner-ordered stop)

| File | Author of change | Status |
|---|---|---|
| `tools/run_campaign_night.py` (+344) | my C1 lane | verified (see §2.3), **uncommitted** |
| `tools/night_status.py` (+125) | my C1 lane | verified (§2.3), uncommitted |
| `tests/test_night_status_truth.py` (new, 13 tests) | my C1 lane | pass |
| `tools/analysis/space_card.py` (+44) | my C2 lane | tested (§2.4), uncommitted |
| `tests/test_space_card_data_agreement.py` (new, 7 tests) | my C2 lane | pass |
| `tools/night_queue/fidelity_pairs.py` (new, 309 lines) | my B1 lane | tested (§2.5), uncommitted; **see §4.1 before using** |
| `tests/test_tools_fidelity_pairs.py` (new, 11 tests) | my B1 lane | pass |
| `scratch/fable_architecture/.b1/**` (selection evidence + helper scripts) | my B1 lane | read §2.5/§4.1; commit later with `git add -f` past `/scratch/` ignore |
| `hornlab_search/objective/scalar_v9.py` (+62) | **concurrent author, predates my session** (F9 context) | **NOT MINE — do not commit.** C6 rule: commit only after its test file passes AND its author is identified. |
| `tests/test_v9_polar_window.py` (untracked), `examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1_c200w.yaml` (untracked) | concurrent author | leave alone |
| `AGENTS.md` (+10), `.opencode/oh-my-opencode-slim.json` (+11) | **NOT from my lanes** — appears during session; diff renames preset `deepseek-flash-max` → `opencode-go-max` and adds `fallback`/`backgroundJobs` config | provenance unclear (user tooling change?). **Do not commit; ask the owner.** |
| `.claude/worktrees/` (untracked) | tooling | ignore |

### 1.4 The D3 freeze (STILL IN FORCE)

`hornlab_search/**` must not be edited while any BO arm is preparing or running (senior F10:
`studies/package.py:75` pins every `.py` under `hornlab_search/`; an edit invalidates live
packages). As of pause the night had just entered its BO arms (`cont_biradial_smooth_200` and
`cont_r50_refine_200` finished exit 0; the runner log's last line shows
`[cont_r50_refine_200] exit=0 evals=114 best_J=3.41738 status=ok` — it improved on its seed
3.79567). Check `runs/nights/cd_rrect_2026-11-17/queue_state.json` `running`/`pending` for the
current job before any `hornlab_search/**` edit. `tools/**`, `docs/**`, `examples/**`,
`scratch/**` stay writable.

### 1.5 Live night `cd_rrect_2026-11-17` — queue at pause

File `runs/nights/cd_rrect_2026-11-17.yaml` (the runner re-reads it before every job; the
refresh watchdog may also rewrite/repair it — keep every edit valid YAML, ids unique, and
validate with `python -c "import yaml; yaml.safe_load(open('runs/nights/cd_rrect_2026-11-17.yaml'))"`).

Done (36+): b3_soft_resume, c_rrect_100w + rc1, t_rrect80 + rc1 (both failed: "no successful
screen records"), t_trit80/rc1/rc2, c_rrect_100w_rc2, c_warm_resume_ab4fb9/c221aa,
k_lame_cont_S4/E2, c_klame_200, t_klame_turbo100/scalar100 (klame BO = unsupported point-grid,
removed from file earlier), cont_p80_ath_core14_700_200 (448 evals, best 4.97799),
cont_p80_athcore_corelaw_200 (truth: 182 rows/159 valid — see §2.3),
6× hifi_verify_*, 4× home_range15_*, cont_p80_hvlaw_cov_200 (320 evals, 4.69353),
cont_hlc_lecleach_ar_200, cont_hl_spiral_200, cont_biradial_style_200 (exit 0 19:12),
cont_r50_refine_200 (exit 0, best 3.41738, improved on seed).

Pending in file order: `t_ath14_turbo100`, `t_ath14_scalar100`, `t_hvlaw_turbo100`,
`t_hvlaw_scalar100`, `t_corelaw_turbo100`, `t_corelaw_scalar100`, `t_trit_scalar100`,
`t_rrect_turbo300` (timeout 86400), `t_atlas_corelaw_turbo300`, `t_atlas_athcore_turbo300`,
then the 13 walls-relieved jobs `w_*_200w1` (incl. `w_osse_rrect_fold_warm_v7_200w1`), ending
`w_control_v7_200w1`. Verify against `queue_state.json` at takeover — cont jobs were draining
fast (~20-90 min each); the BO arms may already be live.

### 1.6 CPU night `bo_cpu_2026-11-17`

All 4 attempts failed earlier (klame BO unsupported point-grid ×2, atlas ×2 blocked by
`gpu-clean` rc 3 while GPU lane live). Check whether a runner is still up
(`Get-Process` / the night's runner log) before assuming.

---

## 2. What is implemented, and how it was verified

### 2.1 D1 — committed (§1.2 `84339a7`). No action left except the NOTES_FOR_SENIOR item in §6.6.

### 2.2 D2 — committed (§1.2 `750223e`). Owner confirmed it should precede the BO arms; it did
(the fresh `run_bo_arm.py` launches pick up `ffb5e25`'s lock fix). Done.

### 2.3 C1 — night truth (tools only; uncommitted; lane-verified + I re-verified on real data)

- `tools/run_campaign_night.py` now records per job, additively (old keys/order intact):
  `rows_before`, `rows_after`, `rows_window`, `valid_rows_window`, `best_J_window`,
  `log_tail` (last ~15 lines), `stop_reason` (classes: ok, timeout, watchdog,
  blocked_gpu_busy, launch_failed, pre_hygiene_failed, crash_traceback, error_message,
  exit_nonzero_no_cause), `bo_progress`; `run_dir` falls back to the argv-named resume dir;
  `best_J` falls back to the window best.
- `tools/night_status.py` prefers the new fields and re-derives old rows read-only from job
  argv + run-dir rows inside the recorded window; a resume row with unattributable real rows
  reports `unknown`, never `0 evals`.
- **Re-verified by me on real data:** `cont_p80_athcore_corelaw_200: best J 4.8097, 182 evals,
  (window 182/282 rows, valid 159)` and `t_trit80_rc2: best J 5.5235, 82 evals (BO screen 80
  verify 2 observations 80)` — both match the senior's F3 ground truth exactly.
- Tests: `tests/test_night_status_truth.py` 13 pass; regression over
  `test_tools_night_status.py`, `test_tools_night_runner.py`, `test_night_runner_live.py`,
  `test_night_report.py` — 46 pass. Known pre-existing unrelated failure:
  `tests/test_night_bo_arm_wrapper.py` (2 tests — monkeypatch `subprocess.call/run` vs the
  `Popen` the tool has used since `1482304`; not touched by C1).
- **The live runner process still runs the OLD code** — new summary fields appear only on the
  next runner launch. Do NOT restart the night to "activate" C1 without the owner's OK.

### 2.4 C2 — data_agreement gate (tools only; uncommitted; lane-verified)

- `tools/analysis/space_card.py`: `MIN_LINK_ROWS = 10`; `_data_agreement` returns `"unknown"`
  when the top decile is absent or n < 10 (True/False only at n ≥ 10); `recommend()` emits
  `data_n` + `data_verdict` (`agrees (n=…)` / `disagrees (n=…)` / `unconfirmed (n=…)` /
  `unknown (no top-decile rows)` / `unknown`); `action: link` for unknown stays geometric-only
  (no data claim); `link_rejected_by_data` now only reachable at n ≥ 10. `data_agrees` field
  values unchanged (true/false/"unknown") for backward compat.
- Tests: new file 7 pass; with existing space-card tests 26 pass.
- **Not yet done by anyone:** a diff-level review of the 44 added lines, and a re-run of
  `space_card.py` on one of the three lanes that were falsely marked "data disagrees" on 0 rows
  to see the new rendering on a real card (successor hardening item, §7.2).

### 2.5 B1 — prepared, NOT queued, and NOT yet correct in one respect (§4.1)

Lane artifacts in `scratch/fable_architecture/.b1/`: `b1_selection.md` (full arithmetic),
`b1_night_insert.yaml`, `b1_designs.csv` (the ten `run,design` rows), `b1_selection.json`,
`home_brief_rows.json`, `v9_home_pool_v1000/`, `v9_ten_onset/`, `snap/`, plus throwaway helper
scripts (`b1_compute/table/v9_score/snapshot/validate/check_versions/smoke.py`).

Selection (all objective v7, brief `room_landscape_80x50_700_hf1440_v7`; v9 J from CPU replay
under WP3 corridor `home_v9_corridor_h90_70_v1000`; tri/dof from stored meshes):

| # | src | run dir | hash | config | v7 J | v9 J | tri/dof |
|---|---|---|---|---|---|---|---|
| 1 | v9#1 | runs/20261116T130335Z-screen-ab4fb9 | 2f7307c06023 | fold_warm | 4.1413 | 1.6492 | 7220/3751 |
| 2 | v9#2 | ab4fb9 | 507e7257c091 | fold_warm | 3.9485 | 1.6691 | 7304/3791 |
| 3 | v9#3 | ab4fb9 | ced63c6a01a1 | fold_warm | 3.8251 | 1.6927 | 7408/3844 |
| 4 | v9#4 | ab4fb9 | 688ffe811b6a | fold_warm | 3.8923 | 1.7159 | 7313/3796 |
| 5 | v9#5 | ab4fb9 | 78f599e8a1d2 | fold_warm | 4.0317 | 1.7511 | 7391/3837 |
| 6 | v7#1 | runs/20261115T143219Z-screen-d3a1bb | 3a1038da45d0 | ext_throat_v7 | 3.1028 | 2.2849 | 10175/5275 |
| 7 | v7#2 | runs/20261116T025728Z-screen-cd60f7 | 9fcd21fc1904 | ext_throat_v8 | 3.1028 | 2.2849 | 10173/5274 |
| 8 | v7#3 | d3a1bb | 766c9b1ba8a9 | ext_throat_v7 | 3.2995 | 2.2837 | 7149/3725 |
| 9 | v7#4 | d3a1bb | 508f907726d3 | ext_throat_v7 | 3.3051 | 2.1605 | 7685/3999 |
| 10 | v7#5 | d3a1bb | b996da551021 | ext_throat_v7 | 3.5743 | 2.6499 | 7714/4009 |

Union disjoint → 10 designs, 0 top-up. **v7 top five are ext_throat_hvlaw, not the biradial/
fold-warm lanes I had guessed in my first brief** — the lane verified this over 2,959 rows/48
runs. WP3's stored v9 output covered only the 2 legacy designs, so the corridor ranking was
recomputed (2,959 replay cells, 2,314.9 s CPU, 0 backend calls — no GPU, no re-solve). All ten
sit below the measured quarter-domain OOM ceiling (8.9k-15.7k DOF); **no CPU fallback needed
at the STORED mesh sizes** — but see §4.1 for the densified-mesh case.

Proposed job (validated: YAML ok, no id collision among 55 live jobs, argv paths exist,
`run_campaign_night --dry-run` exit 0, tool `--dry-run` selected 20 pairs):

```yaml
- id: b1_fidelity_ladder_20261117
  kind: command
  timeout_s: 10800
  env:
    HORNLAB_GPU_LOCK: refuse
  argv:
  - .venv/Scripts/python.exe
  - tools/night_queue/fidelity_pairs.py
  - --designs-file
  - scratch/fable_architecture/.b1/b1_designs.csv
  - --modes
  - verify,finalist
  - --out
  - runs/b1_ladder_2026-11-17
```

`fidelity_pairs.py` itself is sound on read (per-(run,mode) output run dirs; resume-safe by
ok-row skip; raises if ANY requested hash lacks an ok row; `gpu_lock`; GpuBusyError → exit 3;
writes a first-class run.json/config snapshot per output dir; dispatches all mesh+solve+metric
work to `hornlab_search.search.evaluate.evaluate` — no solver/mesher code). Hardening list in §7.3.

---

## 3. Owner's §4 answers (received during the pass — binding)

1. **Tonight's queue.** YES to B1, inserted right after the running job (1-3 h GPU estimate;
   the night file is re-read before every job and the GPU is cleaned before each one). The
   agent should check each design's mesh size first; **any too big for 8 GB go to the CPU lane
   instead.** Why now: every later decision depends on B1; draining could take >1 day (three
   24 h-timeout turbo300 arms). **Fix the R-OSSE rect job rather than running its BO arm:**
   `t_rrect_turbo300` will fail (BO sampler rejects grid-route designs — same root cause as the
   klame arms; the route also needs successful runs of the 100w config which never ran tonight;
   last failure was the budget mismatch "cumulative budget cap would shrink 110 → 109").
   Swap it for **`c_rrect_100w` requeued with `--budget 110`, resuming its run**
   (`runs/20261117T070118Z-screen-8627f8`). **Optional:** move the two atlas 300-solve arms
   behind the 13 walls-relieved home jobs (they were originally added as the end of the queue;
   the home jobs serve the main goal). Merge main before the BO arms — **done** (`750223e`).
2. **U3 host: ext-throat first** (the clear home leader, J 3.10 ≈ 4× the noise floor below the
   rest; three of its seven test freedoms stay inside the envelope: two section-steering +
   the diagonal pull), **plus a small biradial extra (~5 solves)** — biradial is the only host
   where the vertical-timing freedom stays inside the envelope, and vertical control at
   700-1100 Hz (nothing reached below 66°) is the one gap every design shows.
3. **Brief: keep v7 for the nights; add v9 as a free second score on CPU only** — H 60-90°
   from 700 Hz; V 40-60° from 1000 Hz; loading on. Constancy in that view: **slope-limited**,
   with its noise floor measured on stored data before it counts. Strict is wrong for this
   owner (it would penalise the gentle 90→70° narrowing). Use both scores: designs near the
   top under both are the safe picks. Do NOT switch the nights' scoring until a measurement
   (answer 4) shows which score predicts a real horn better. This SUPERSEDES the senior §3
   question "does C1 = keep v7 still stand?" — answered, keep v7.
4. **Physical check: yes, two steps.** Step 1 now (no build): run ONE published horn through
   our pipeline — a Geddes OSSE or ATH waveguide with published geometry AND measured polars;
   pass = beamwidth within ±5° (±3° in the presence band per senior D6) and DI within ±1 dB;
   cost = research time + 1-2 solves. Step 2 after B1: print two horns — the ext-throat
   **design `3a1038da45d0`** (if B1 confirms its lead), and the top design under the v9 score
   if it is a different construction, else fold-warm OSSE (3.62). Measuring two horns ~0.5 J
   apart settles decision 3 with data.

---

## 4. Blocking decisions / discrepancies needing senior or owner resolution FIRST

### 4.1 B1 does not yet measure what the owner asked for (the big one)

The lane discovered: for these configs `mesh_spec("finalist")` changes only the DOF **cap**
(24,000 → 48,000); the actual mesh is set by `epw=6`/`f_max=8000` and is only 3,725-5,275
quarter-DOF, so the cap never binds and **verify and finalist build the SAME mesh**. The
proposed `verify,finalist` pair therefore measures a 29-vs-36 frequency-grid difference —
(a) not the "finer mesh" the owner explicitly asked for, and (b) close to re-measuring
frequency floors that N3 and WP3 already measured (senior do-not rule).

Resolution requires a decision (owner owns it; senior frames it):
- **(a) Densified mesh pair (true mesh noise):** pass 1 = production mesh at ≥29 freqs (the
  `verify` tier already equals the screen cap here), pass 2 = same design with a genuinely
  denser mesh (raise `epw` 6→8, or f_max) at ≥29 freqs. Needs a config/brief-level mesh
  override the existing CLI cannot express per fixed design — the cleanest route is a small
  `fidelity_pairs.py` extension accepting a mesh-density override per mode, or a brief/config
  variant. Feasibility redo required: DOF ×(8/6)² ≈ 1.78 → 6.6k-9.4k quarter-DOF vs the
  measured OOM ceiling 8.9k-15.7k → the two ext_throat designs (~5.3k → ~9.4k) are
  **borderline**; apply the owner's rule (too big → CPU lane).
- **(b) Keep the lane's encoding** and accept that B1 measures frequency-grid fidelity only —
  cheap, but conflicts with the owner's wording and the do-not rule. Probably wrong.
- Either way: settle the cache question (lane Q4: should pass 1 reuse the cache instead of a
  true re-solve? For mesh noise you want both passes really solved), the near-duplicate
  question (lane Q3: swap `9fcd21fc1904` → `6d6dd332b282` for ten distinct horns), and which
  corridor is authoritative for the v9 half of the selection (WP3 `h90→70 v1000` vs owner's
  answer-3 brief "H 60-90, V 40-60 from 1000" — NOT the same corridor; lane Q2).

My recommendation to carry: option (a), with the ext_throat pair split to CPU only if the
densified estimate exceeds the ceiling, and the near-duplicate swapped. But get the owner's
one-word pick before inserting — the owner said "Add B1 now", so this is a same-turn question.

### 4.2 D4 item 1 (brief_file word-for-word) — resolved as "do NOT revert"; write it up

I traced this fully. The `_w1` copies sit at `examples/typologies/walls_relieved/<family>/`
(3 levels below `examples/`), their parents at `examples/typologies/home_landscape_2026-11-15/`
(2 levels), briefs only exist at `examples/briefs/`. `config.py:1341` `_resolve_path` tries
CWD, config dir, then repo root: the parents' string `../../briefs/…` resolves at the parents'
depth; the copies' pre-D1 string did NOT resolve at the copies' depth (that was the real
"one ../ short" bug — the queued jobs would have died at config load); D1's `../../../briefs/…`
resolves and matches the same physical brief file. `warmstart._identity`
(`hornlab_search/search/warmstart.py:34-45`, compare at `:79`) and
`tools/search_preflight.py:497-513` (generator-history fallback) compare the RAW string, so
word-for-word identity and resolution are irreconcilable at different depths — C5 (digest-based
identity, owner-gated) is the real fix. The 13 queued `_w1` jobs are fresh searches with NO
`warm_start` block (verified on `control_v7_w1.yaml`), so today only the preflight fallback is
affected. **Do not revert D1** (it would kill tonight's 12 remaining walls-relieved jobs).
Append the explanation to `NOTES_FOR_SENIOR.md` (append-only) and note that C5 remains the
owner-gated fix.

### 4.3 D4 item "Card only the 5 cardable `_w1` lanes" — ambiguous; resolve empirically

The first review's §4 is not in the repo (grep confirms; it was chat-only). My count: of the 14
`_w1` lanes, the 5 whose generator routes `DesignSpace.from_config` refuses are crowe_panel,
klangfilm_lame ×2, rosse_rect ×2 (F7) — leaving 9 cardable, not 5. Either the first review
meant "card only the cardable ones (of which 5 were already done / need doing)", or counted
differently. Resolve by running `tools/analysis/space_card.py` over the 14 with the current
(fixed) configs and cards/`--run` for whichever lanes have matching runs, then present the
cardable set to the senior with the count discrepancy flagged. Do not silently pick an
interpretation.

---

## 5. Owner-approved queue edits still TO APPLY (I was interrupted before editing)

Do these before/while resolving §4.1 (they are independent of it). At pause both `cont_*` jobs
were DONE and the first BO arm was starting — re-check `queue_state.json` first.

1. **Insert B1** (`b1_night_insert.yaml`, possibly re-encoded per §4.1) at the top of pending.
2. **Replace `t_rrect_turbo300`** with a new job (suggest id `c_rrect_100w_rc3`), argv = the
   existing rc2 argv (`tools/geometry/rosse_rect_cli.py search --config
   examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7_r100w.yaml --mode screen
   --cma-seed 5679 --resume C:\Users\hunte\Hrns\hornlab-search\runs\20261117T070118Z-screen-8627f8`)
   with `--budget 110` (rc2's 109 triggered the shrink refusal; the run's cumulative cap is
   110). `kind: command`, `timeout_s: 10800`, `HORNLAB_GPU_LOCK: refuse`. Delete the
   `t_rrect_turbo300` entry.
3. **Move `t_atlas_corelaw_turbo300` + `t_atlas_athcore_turbo300`** to after
   `w_control_v7_200w1` (end of pending).
4. **Hold `w_osse_rrect_fold_warm_v7_200w1`** (senior D4: hold it; its warm-start identity is
   broken pending C5 and its links were withdrawn). Remove from pending; keep a note (in the
   night dir or ISSUES) that it is HELD, not dead, so the watchdog does not "repair" it back —
   check `tools/night_queue/refresh_watchdog.py` behavior on missing-but-referenced jobs before
   editing.
5. After every edit: YAML-parse the whole file; confirm ids unique; confirm `queue_state.json`
   pending list matches your intent after the runner next transitions jobs.

Owner rule in force: do not pause/cut/reorder owner jobs without asking — items 2-4 are owner-
and senior-approved as above; anything else needs a question first.

---

## 6. Remaining implementation, in order (senior D-numbering + owner answers)

1. **§4.1 B1 encoding decision (owner) → insert B1** (§5.1).
2. **§5.2-5.4 queue edits.**
3. **D4 remainder:** rerun `tools/shape_check.py` over the 14 (was 14/14 mesh pre-fix; rerun on
   the fixed files, log to `scratch/fable_architecture/.evidence/`), rerun
   `tools/search_preflight.py --from-runs <newest same-name run>` per lane to get the
   expected-hits numbers (C2's fix + the current brief_file strings make these computable for
   lanes with runs), mark Crowe **"not queueable without warm_start + reason"** in
   `OWNER_DECISIONS_PACKET_2026-11-17.md` (+ the card), resolve §4.3.
4. **D5-D10 plan amendments** — write into `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` §10 /
   ISSUES as proposals, nothing auto-applies: D5 merge the two plans into F1's one table; D6
   "Stage 2b: physical anchor" — now OWNER-APPROVED per §3.4, so upgrade from proposal to
   scheduled (P12b published horn first, P12d prints after B1); D7 B1 scheduling (this pass);
   D8 continuation rule (propose only when last-100-eval improvement > the identity's published
   floor ≈ 0.13 J for v7 at 12/25 freqs; restate after B1); D9 provenance one package (WP 0.9 +
   C3 surfaceFit echo + Q5 both-boxes rule + master-plan WP4; `record_digest` only after the
   owner's provenance decision); D10 governance (nights should run main; full offline suite with
   thread caps `-n 6` after the drain, then ask the owner to merge PR #67; one integrator per
   branch — record the `f5db35e` AND `3682173` second-writer commits in NOTES_FOR_SENIOR and ask
   who integrates master-plan work).
5. **C2 explanation to the owner** — SUPERSEDED as a question (owner answered), but the §3
   corrections + table must still be recorded in the packet/report: slope mode fits a line in
   log-frequency, tilt capped at ±`slope_max_deg_per_decade`, penalises deviation from the line
   (`scalar_v9.py:619-647`); strict penalises tilt+wiggle around a flat level; both use H +
   `cov_v_weight`×V from each plane's onset, centre clamped into the corridor in corridor mode.
   The 116-point / 0.205 J costs were measured for STRICT only (N3 §method); slope is
   unmeasured; 0.113-vs-0.205 is the top-28 error between 18 and 29 solved frequencies. DELETE
   "CD lanes gain, non-CD lanes lose" (unmeasured, classifies by family). Use S1's numbers:
   strict on top of the v9 corridor keeps 13 of the top 20; strict and slope share 18 of 20; no
   first place survives every range choice. Add the "what J pays for today" table (F4): under
   the kept v7 brief `load` is 55% of J and nearly constant (3.47-3.59), `cov` only 9%, top-20
   spread 0.10 J inside the sd 0.11-0.13 floor → statistical ties; under the v9 corridor it is
   mostly DI slope (77-92% of J) and `preferred_deg` is inert inside `[min, max]`.
6. **Owner answer 3 work item (CPU):** create the v9 second-score brief per §3.3 parameters and
   score every stored home design under it on CPU (`rescore_identity.py` / replay — no GPU);
   measure the slope-limited constancy noise floor on stored data BEFORE it counts. Note the
   owner's brief ≠ WP3's corridor (different H corridor and same V onset) — a new brief file in
   `examples/briefs/home_landscape_2026-11-15/`, never overwrite originals.
7. **Physical anchor step 1 (owner-approved, GPU 1-2 solves):** research a published Geddes OSSE
   or ATH waveguide with published geometry + measured polars (use `hornlab-acoustic-grounding`
   + `hornlab-typology-research` discipline; R9 gate: verifiable published reference), build the
   config through the pipeline (hornlab-shape-check before any GPU), then schedule the 1-2
   solves — with the owner: night job vs interactive slot (one GPU solve at a time; the night
   owns the GPU right now).
8. **U3 host wiring (owner answer 2):** record ext-throat + biradial-extra in the plan (WP 4.2
   equivalence 2 solves → WP 4.3 B2 12-16 on ext-throat, +~5 biradial vertical-timing solves);
   the record-route equivalence precondition (SD-2) still gates B2.
9. **Commit plan (ONLY when the owner lifts the stop):** one push must carry (per the push
   rule) CONTINUITY + ISSUES in the same commit: C1 files + C2 files + `fidelity_pairs.py` +
   their tests (+ `.b1/` evidence `git add -f`), message `feat(tools): night truth (C1),
   data-agreement gate (C2), B1 fidelity-pairs tool`. EXCLUDE: `scalar_v9.py` + its
   `test_v9_polar_window.py` (concurrent author's, C6), `AGENTS.md` + `.opencode/…json`
   (provenance unclear — ask), `hl__klangfilm_lame_curved_v1_c200w.yaml` (untracked, other
   session). **Push-state correction 2026-11-18:** everything through `3682173` is ALREADY on
   origin; only these uncommitted files are at risk.
10. **After the night drains:** full offline suite (thread caps, `-n 6 --dist loadscope`, GPU
    lane concurrently), then the PR #67 merge ask (D10). `hornlab_search/**` code fixes C3/C4/C6
    wait for the freeze to lift (§1.4).
11. **Throat-H/V patch set (owner-approved integration plan, 2026-11-18):** 4 patches rebased
    onto `3682173`, touching NONE of the dirty-tree files, 0 new test failures, waiting in the
    isolated clone `.claude/worktrees/agent-a527a7d28dc77734a` (tip `5af0048` "fix(A/B/C/D): H12
    oa_excess_tol, directivity guard, watchdog auto-widen, GUI seed panel"). Integration order
    (owner-ordered): AFTER this agent's commit/push + post-drain full suite → apply to the
    canonical branch, open a draft PR → then the GPU throat steps (onset sweep, config A vs v8)
    queued after B1 + the BO arms, as a separate budget line. **DO NOT APPLY IT YOURSELF
    (owner rule) beyond the isolated-clone CPU test run, which is safe to run now.**

---

## 7. Hardening / review checklist on the implemented code (do this before committing)

1. **C1 runner diff (344 lines) — I verified behavior on real data but did NOT line-review
   the diff.** Check: (a) log-tail reading handles PS 5.1 `Tee` UTF-16 logs (the hornlab-gpu-job
   skill's known gotcha) — the lane caps lines at 400 chars; confirm encoding detection;
   (b) BO progress opens `studies.sqlite3` strictly read-only (uri mode) so it cannot lock a
   live study; (c) summary-row writing is exception-safe (a dying child must still produce a
   row with stop_reason); (d) consumers of `summary.jsonl` (`tools/night_report.py`,
   `gui/data_bo.py`) tolerate the new keys (lane says night_report untouched and formats kept).
2. **C2 diff (44 lines)** — line-review; then re-run `space_card.py` on one of the three lanes
   that were falsely "data disagrees" on 0 rows and eyeball the card's `data_verdict`.
3. **`fidelity_pairs.py` before a GPU night slot:** (a) confirm the `evaluate()` call signature
   against `hornlab_search/search/evaluate.py` (lane used injected fakes + one real-config
   smoke); (b) wrap or pair with `tools/bench/run_with_memwatch.py` + record the nvidia-smi
   BASELINE next to every peak (gpu-job rule 3) — the proposed night job has neither; the
   sibling `verify_night_jobs.py` pattern (batch-12 `HORNLAB_FREQ_BATCH_SIZE=12` for ≥29-freq
   tiers) should be applied to the B1 job's env; (c) confirm rows record their `mode` so
   `tools/analysis/fidelity.py` can pair screen/verify rows later; (d) confirm a mid-job crash
   leaves per-(run,mode) dirs resumable (design-level resume exists; verify the ctx rebuild
   path after a crash — `_write_mode_meta` rewrites run.json on resume: acceptable?).
4. **Merge-state sanity:** `tests/test_night_refresh_gate.py` passes post-merge (I ran it).
   The two `test_night_bo_arm_wrapper.py` failures are PRE-EXISTING (Popen-vs-monkeypatch,
   since `1482304`) — do not "fix" them in this pass; note in ISSUES if not already there.
5. **Second-writer commits (`f5db35e`, `3682173`)**: read `git show --stat` for each; confirm
   neither touched `hornlab_search/**` in a way that invalidates prepared packages (3682173
   touched analysis tools per its message — verify no `hornlab_search/` files, else the next
   BO package prepare pins change mid-arm: check before the next arm starts).

---

## 8. Do-not list (senior §5, still binding)

Do not edit `hornlab_search/**` while a BO arm prepares or runs; do not pause/cut/reorder owner
jobs without asking; do not treat any `night_status` "0 evals" as real until C1-verified rows
say so; do not rank designs closer than the floor (v7 ≈ 0.11-0.13 J at 12/25 freqs; restate
per identity once B1 lands); do not re-measure frequency floors N3/WP3 measured; do not build a
second replay or sampler; never claim "data disagrees" for any link with n < 10 (C2 enforces);
never modify `.venv`; never `taskkill /IM julia.exe`; one CUDA solve at a time machine-wide;
`HORNLAB_GPU_LOCK=refuse` for night/measurement/checkpoint jobs.

## 9. Open questions carried (from lanes + me)

1. §4.1 B1 encoding (blocks the owner's "Add B1 now").
2. §4.3 the "5 cardable" count.
3. Which v9 corridor/brief is authoritative for selection vs scoring (WP3 h90→70 v1000 vs the
   owner's answer-3 brief).
4. Lane Q3: near-duplicate swap in B1's ten (9fcd21fc1904 ↔ 6d6dd332b282).
5. Lane Q4: cache reuse for B1 pass 1.
6. C1 open: retro-classify stop reasons for OLD summary rows? (cheap; owner-visible value).
7. C2 open: powered n≥10 payload with zero proposed links reads "disagrees (n=…)" — kept as a
   genuine no-correlation result; confirm the senior is happy.
8. AGENTS.md/.opencode preset changes (§1.3) — whose, and commit or not.
9. Who integrates master-plan work (D10) — ask with the §9 governance note.
10. Fold-warm held: does the owner want its queue slot used by anything else, or just shorter
    night? (Default: just remove; do not refill without asking.)
