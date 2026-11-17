# SEARCH_CONTROL_MAP

Investigator B — read-only. Maps the night runner's control plane: flags, thresholds, exclusions,
resume, queue controls, locks, idempotency, crash recovery, and the seam a read-only shadow advisor
would use. No queue edit, no process start/stop, no GPU lock taken or released.

## Provenance

- Repo root `C:\Users\hunte\Hrns\hornlab-search`.
  **HEAD at dispatch-time check `3efe9be` @ 19:38:34; HEAD at final check `d187c06` @ 19:49:04**
  (2026-11-16, local). The tree advanced during the pass. The tree later advanced to `50f3d8c` @ 19:55:43 (test/docs only): `git diff --stat d187c06..50f3d8c` shows **none** of the traced files changed, so all citations remain valid at `50f3d8c`.
- **Control-plane files are clean at final HEAD `d187c06`** (no working-tree diff):
  `tools/run_campaign_night.py`, `tools/night_status.py`, `tools/night_queue/queue.ps1`,
  `tests/test_night_runner_watchdog.py`, `tests/test_night_runner_live.py`. So **every
  watchdog/live-reload feature below is committed at HEAD**, not "only in uncommitted code". (The
  HOME_18H note "Nothing committed: runner live-reload + watchdog" —
  `docs/queue/HOME_18H_PLAN_2026-11-16.md:198` — is **stale relative to HEAD**.)
- Of the files this map covers, none is dirty; the concurrent lane's working-tree changes are
  elsewhere (`M design/generated.py` + new crowe_hv generator files, plus test/tool edits) and do
  not touch the control plane.
- A live controller+runner (`home_day2_2026-11-16`) and a live CUDA solve were present; nothing was
  touched. Status: **directly verified** (`git rev-parse`, `git status --short`, `git diff`).

## 1. CLI surface (flags the runner actually accepts)

`_parse_args` (`tools/run_campaign_night.py:1472-1486`):

| flag | meaning |
|---|---|
| `--night YAML` | night file, conventionally `runs/nights/<night>.yaml` |
| `--dry-run` | print resolved jobs; launch nothing, run no hygiene; fails naming every missing path-valued argv target (`:1317-1331`, `missing_arg_paths`) |
| `--only ID` | run one fixed job; disables live reload (`live = bool(live) and only is None`, `:1348`) |
| `--admission JSON` | policy gate: night name + `allowed_job_ids`; loaded and checked before any job, dry-run included (`:1480-1504`; `load_admission:651-693`; `check_admission:694-715`) |
| `--no-live` | read the night file once (old behaviour) (`:1483-1485`, `:1348`) |

Status: **directly verified**.

## 2. Search watchdog — flags, defaults, and hard-coded thresholds

Defaults (`run_campaign_night.py:99-106`), poll and exit (`:107-108`):

| key | default | meaning |
|---|---:|---|
| `min_attempts` | 25 | do not judge until this many attempts exist |
| `refusal_window` | 30 | judge the last N attempts |
| `refusal_max` | 0.30 | stop if >30 % of the window are “bad” |
| `no_gain_valid` | 30 | stop if after N valid evals best is still the seed |
| `stall_valid` | 40 | stop if best improved < `min_rel_improve` over last N valid |
| `min_rel_improve` | 0.005 | 0.5 % relative |
| `WATCHDOG_POLL_S` | 30.0 s | how often the live ndjson is re-read |
| `WATCHDOG_EXIT` | 75 | exit code that maps to `status: watchdog` |

Merge / override (`_resolve_watchdog:111-135`): defaults ← night YAML `watchdog:` ← job YAML
`watchdog:`; `watchdog: false` turns it off; `watchdog: true` keeps defaults. Unknown keys raise
`ValueError`. Resolution into `Job.watchdog` happens at load for jobs that are `kind: search`, whose
argv looks like a search, or that explicitly set a `watchdog` mapping (`:636-644`).

**Bound-pinning rule** (`:185-203`) — the only rule with **hard-coded, non-YAML thresholds**:
- `pin_min_valid = 30` (`cfg.get("pin_min_valid", 30)`, `:186`)
- `pin_frac = 0.03` (`:196`)
- `pin_count = 3` (`:199`)
- `pin_ignore` is the **only** pin key accepted from YAML (special-cased, `:122-128`).

The others are **not in `WATCHDOG_DEFAULTS` and not special-cased**, so `_resolve_watchdog` rejects
them as “unknown watchdog key” (`:129-131`). A YAML `watchdog: {pin_count: 5}` would fail load;
only `pin_ignore` is tunable. This confirms the TRITONIA audit's statement that “the live runner's
pin rule is not separately configurable” (`docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md:16`).
Status: **directly verified** (code) and **contradicted** by any assumption that `pin_*` are public
schema.

The `bad(r)` predicate (`:166-168`) is `(not r.get("ok")) or not finite objective or objective >= 900`.
See WATCHDOG_REPLAY §hypothesis for the conflation this causes.

## 3. What the watchdog is applied to (exclusions)

- `_is_search_argv` requires a path component exactly named `search` and **not** `verify-night`
  (`:138-140`). `load_night` watches a job if `kind == "search"`, or `_is_search_argv`, or an
  explicit per-job `watchdog:` mapping (`:636-644`).
- Therefore **verify jobs, cohort/prep jobs, and BoTorch study jobs are never watched** unless a
  mapping is attached; a study argv (`... hornlab_search.studies.cli run`) has no `search` component.
  The in-code comment states “verify, cohort and BoTorch study jobs are never watched” (`:97-98`),
  and the test `test_only_search_jobs_are_watched` (`tests/test_night_runner_watchdog.py:112-126`)
  asserts a verify-night job and a studies job resolve `watchdog = None`.
- A geometry-bridge CLI that takes a `search` subcommand **is** watched (`rosse_rect_cli.py search`),
  also asserted in the same test. Status: **directly verified**.

## 4. Stop / save mechanics (live poll → kill → record)

`NightRunner.run` (`:966-1122`):
- Tees child stdout, enforces `job.timeout_s` (`:986`, `:1087-1097`).
- Every `watchdog_poll_s`, if a run dir was found (`_find_new_run_dir:214+`) it calls
  `watchdog_verdict(rows[wd_base:], wd_cfg, _run_bounds(wd_run))` (`:1071-1076`).
- On a reason: writes `=== WATCHDOG <reason>; stopping job …` and `search ABORTED: watchdog …`
  (`:1077-1080`), kills the process tree (`_kill_tree`), waits ≤60 s then `proc.kill()` (`:1081-1086`),
  and returns `(WATCHDOG_EXIT, False)` (`:1115-1117`).
- `classify_status` maps exit 75 + `=== WATCHDOG` to `STATUS_WATCHDOG = "watchdog"` (`:84`, `:428-445`).
- **Save on stop**: the search writes its own `search.ndjson`; the runner does not snapshot CMA state.
  The `search ABORTED` line names the partial run dir. `summary.jsonl` gets a row with
  `evals_ndjson`, `best_J`, `notes` (`:1178-1215`). `best_J` is parsed from the **log**, and a
  watchdog kill happens before the search prints its final summary line, so `best_J` is frequently
  `None` for watchdog rows (observed: all 38 watchdog rows in `runs/nights/*/summary.jsonl` have
  `best_J: null`). Status: **directly verified**.
- `status` values: `ok`, `watchdog`, `timeout`, `blocked` (GPU busy marker + non-zero), `failed`
  (`:428-445`). Status: **directly verified**.

Resume nuance: with `--resume DIR`, `wd_base` = row count already in `DIR/search.ndjson`
(`:1028-1035`), so only the **new** rows are judged. Test:
`test_resumed_run_judges_only_new_rows` (`tests/test_night_runner_watchdog.py:175-192`).
Status: **directly verified**.

## 5. Live queue controls

Re-read before every job (`:1232-1275`, `:1369-1371`):
- **Reorder / insert / remove / change** any job that has not started; the running job is never
  interrupted (`:1234-1238`). Test `test_reorder_insert_and_remove_take_effect_after_current_job`
  (`tests/test_night_runner_live.py:54-62`).
- **Finished ids never re-run** within this process — `done` list (`:1352`, `next_job:1356-1365`);
  test `test_finished_ids_never_rerun_even_if_moved_back` (`:65-71`). To re-run, a **new id**.
- **Bad edit keeps the last good plan**: `_reload_plan` catches any `ValueError`, logs
  `RELOAD FAILED (keeping previous plan)` once per distinct error (`:1253-1275`); test
  `test_invalid_edit_keeps_last_good_plan` (`:73-80`).
- **`night` and `lane` are immutable mid-night** (`:1258-1261`); test
  `test_night_name_change_is_refused` (`:83-88`).
- **PAUSE**: file `runs/nights/<night>/PAUSE` or top-level `pause: true`; runner polls and re-reads
  while paused, resumes on removal (`:1372-1383`); test
  `test_pause_file_holds_then_resumes_with_edits_made_while_paused` (`:109-132`).
- **STOP**: file `STOP` or top-level `stop: true`; ends cleanly before the next job (`:1384-1387`);
  tests `test_stop_file_ends_after_current_job` (`:91-98`), `test_stop_key_in_yaml` (`:101-106`).
- **Admission**: a reloaded id outside `allowed_job_ids` is skipped and logged (`:1360-1363`);
  test `test_admission_skips_unlisted_reloaded_job` (`:135-140`). `load_admission` rejects wrong
  night, empty list, non-string, duplicates (`:651-693`).
- **`--no-live`** restores read-once (`:143-148` test).
- State file `queue_state.json` (done/running/pending) is written atomically after each change
  (`_write_queue_state:1278-1286`); queue log `runs/overnight/queue_<night>.log`.
Status: **directly verified** for all the above; each claim has a named test.

**Contradicted documentation**: `tools/night_queue/queue.ps1:21-22` says “A night file a runner
already started is read once at start: appending jobs to it does nothing.” That is the **old**
behaviour; the live runner re-reads before every job (`:1234-1246`). Status: **contradicted by code
and by `docs/queue/HOME_18H_PLAN_2026-11-16.md:95-109`**.

## 6. Lock ownership, idempotency, crash recovery

- **Lane lock**: `night_lane_lock` holds the **CPU** lane marker (`.cpu.lane.lock`) for the whole
  night; a GPU night takes no lane lock here (`:1218-1229`). Status: **directly verified**.
- **GPU lock**: the runtime is a persistent `.gpu.lock` with PID record (`gpulock.py`). Policy env
  `HORNLAB_GPU_LOCK` ∈ {`refuse`,`warn`,`off`}, default **warn** (`gpulock.py:42-45`, `:193`):
  a live holder emits a loud warning and the command **proceeds unlocked** unless `refuse`.
  Stale (dead-PID) lock is removed and re-acquired (`gpulock.py:228-247`). Reentrancy via env
  `HORNLAB_GPU_LOCK_OWNER` (`gpulock.py:37-38`, `:218`). Status: **directly verified**.
- **Pre-hygiene lock takeover (runner)**: `NightRunner.pre_hygiene` waits up to `lock_wait_s` for
  `.gpu.lock`; a dead recorded holder is removed with an explicit `STALE LOCK TAKEN OVER` log line
  (`:923-942`). It also runs lane-aware `gpu-clean` (`:898-904`, `:906-913`). Status: **directly
  verified**.
- **Idempotency is per-process only**: `done` starts empty every `run_night` (`:1352`) and is never
  loaded from `queue_state.json`. A controller/runner restart therefore **re-runs jobs that a
  previous process already finished**, unless the operator edited them out or an admission packet
  excludes them. Status: **plausible inference from code** (no restart test). This is the main
  crash-recovery caveat.
- **Retry exactly once on `blocked`** (GPU busy): `attempts` loop runs at most twice, `attempts > 2`
  breaks (`:1394-1399`); a blocked first attempt sleeps `retry_wait_s` then retries, writing a
  second `summary.jsonl` row with `attempts: 2` and one RETRY line between the START/END pair
  (`:1404-1411`, doc `:1304-1308`). Status: **directly verified in code**; no test in the two named
  files (test coverage for retry lives elsewhere or not at all — see §8).
- **Process-tree kill**: watchdog and timeout both call `_kill_tree` then wait/kill (`:1081-1086`,
  `:1092-1096`); a child that closes stdout is still governed by the deadline (`:1050-1069`), tested
  by `test_stdout_eof_does_not_report_success_before_exit` and `..._still_obeys_deadline`
  (`tests/test_night_runner_watchdog.py:18-60`).
- `queue.ps1` (controller) never kills anything itself; it keeps Windows awake and waits for a
  named runner (`-WaitPid`+`-WaitMatch`), starts each night's runner in order, and refuses to start
  a night after `-Cutoff` (`queue.ps1:1-23`, `:50-74`). Status: **directly verified**.

## 7. Smallest seam for a future read-only shadow advisor

The control plane already isolates the decision from the action:
- `watchdog_verdict(records, cfg, bounds)` is a **pure** function (`:164-211`; no I/O, no globals).
- The kill is a separate loop (`:1076-1086`), so a shadow mode can compute the verdict and **not**
  kill.

A safe between-jobs read-only adapter needs exactly:
1. the resolved per-job watchdog mapping (`Job.watchdog`, `:636-644`);
2. the run dir (`_find_new_run_dir`, `:214+`) and its rows (`_read_ndjson`);
3. the searched bounds (`_run_bounds`, `:154-161`);
4. the current `current.jobs` / `done` / `skipped` state (`:1351-1354`, `:1419-1420`).

The natural hook is the **`between_jobs` state** (`_write_queue_state(..., "between_jobs")`,
`:1419-1420`) and the **paused** loop (`:1372-1383`). A shadow advisor would call
`watchdog_verdict` (and a proposed `recommend()` wrapper) and write a sidecar
(`advice.json`/`advice.log`) only; it must not unlink PAUSE/STOP, edit the YAML, or kill. Because
`watchdog_verdict` treats only rows passed to it, a shadow advisor must pass the same `[wd_base:]`
slice the runner would (`:1035`, `:1076`) or it will re-judge a resumed run's old rows.
Status: **proposed seam; all named functions exist and are directly verified.**

### 7b. Night lifecycle state machine (written to `queue_state.json`)

`_write_queue_state` is called with one of these `state` values (`:1278-1286`):

| state | written when | next transition |
|---|---|---|
| `running` | just before a job starts (`:1391-1392`) | `between_jobs` on completion |
| `between_jobs` | after a job ends, before the next (`:1419-1420`) | `running` / `paused` / `stopped` / `done` |
| `paused` | PAUSE file or `pause:true` observed (`:1373-1378`) | `running` after removal (`:1382-1383`) |
| `stopped` | STOP file or `stop:true` observed (`:1384-1387`) | terminal |
| `done` | loop exhausted with no STOP (`:1421-1422`) | terminal |

`queue_state.json` is **informational**: it is written atomically via a `.tmp` + `os.replace`
(`:1284-1286`) but is **never read back** (`run_night` rebuilds `done=[]` at `:1352`). So a new
process cannot reconstruct what a previous process finished — see §6 idempotency. Status:
**directly verified**.

### 7c. Exposure matrix — YAML-exposed vs hard-coded

| control | YAML-exposed? | default | source |
|---|---|---|---|
| `min_attempts`, `refusal_window`, `refusal_max` | yes | 25 / 30 / 0.30 | `:99-106`, `:129-134` |
| `no_gain_valid`, `stall_valid`, `min_rel_improve` | yes | 30 / 40 / 0.005 | `:99-106` |
| `pin_ignore` | **yes (only pin key)** | `()` | `:122-128` |
| `pin_min_valid` | **no** | 30 | `:186` |
| `pin_frac` | **no** | 0.03 | `:196` |
| `pin_count` | **no** | 3 | `:199` |
| `watchdog_poll_s` | **no (runner attribute)** | 30.0 | `:107`, `:894` |
| job timeout | yes (`timeout_s`) | `COMMAND_TIMEOUT_S` | `:629` |
| PAUSE / STOP | files **and** top-level `pause`/`stop` | — | `:1248-1250`, `:1373-1387` |
| admission allowed set | JSON packet | none | `:651-715` |

Status: **directly verified**.

## 8. Documented functionality vs tested claims

Tested (named assertions) — `tests/test_night_runner_watchdog.py`:
- refusal rate after `min_attempts` and recent-window only (`:71-80`);
- no-gain when seed still best (`:83-87`);
- stall after progress (`:90-95`);
- improving run left alone (`:98-100`);
- `_resolve_watchdog` merge / off / unknown-key (`:103-109`);
- only search-ish jobs watched (`:112-126`);
- a **real subprocess** is stopped and recorded `status: watchdog` and run dir parsed (`:129-156`);
- bound-pinning stops; widened box does not (`:159-163`);
- `pin_ignore` skips a hard-limit knob and rejects a non-list (`:166-172`);
- resumed run judges only new rows (`:175-192`).

`tests/test_night_runner_live.py`: reorder/insert/remove, finished-never-rerun, invalid-edit keeps
last good, night-name refused, STOP file, STOP key, PAUSE+edit-resume, admission skip, `--no-live`,
`pause` must be bool — ten tests (`:54-159`).

**Untested / unverified claims:**
- **`pin_min_valid` / `pin_frac` / `pin_count` tunability** — no test; and the resolver **rejects**
  them (contradicted, §2).
- **Restart idempotency / crash recovery** — no test; `done` is not persisted (§6).
- **Retry-on-`blocked`** — no test in the two named files.
- **Admission duplicate/edge cases** — `load_admission` validates, but only the “skip unlisted
  reloaded job” path is tested; wrong-night/duplicate refusal is code-only.
- **`night_status.py`** has no dedicated test file in this pass; its `ALERT` threshold is
  `NEWEST_ROW_ALERT_S = 30 min` (`tools/night_status.py:34`), lock status is `lock_status:144-161`,
  running-job scan `scan_running_jobs:164-199`. Treated as documented-only here.
- The HOME_18H claim “the 54 existing night-runner tests still pass” (`HOME_18H:98`) is a
  **historical record**, not re-run in this read-only pass.

## Counterevidence / limits

- `queue.ps1` documentation contradicts the live-reload code (§5) — trust the code at HEAD.
- The runner's `summary.jsonl` cannot report `best_J` for watchdog-stopped jobs because the kill
  precedes the search's own summary print; any “best J at stop” must be recomputed from
  `search.ndjson`, not read from the summary.
- Idempotency being per-process means “finished” is not durable; a restart can double-run, which
  matters for GPU time and for the cohort definition. No test exercises this.
