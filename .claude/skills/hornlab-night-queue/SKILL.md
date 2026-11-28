---
name: hornlab-night-queue
description: Plan, launch, monitor, re-order or recover unattended GPU solve queues ("nights") in hornlab-search so they survive the Claude app closing and Windows sleep. Use when the owner asks to queue/run searches overnight or "until <time>", asks for run updates or new winners, when a night stopped early, or when jobs must be added/re-ordered while a night is live. Single-job GPU mechanics stay with hornlab-gpu-job.
---

# hornlab night queue

Tools (all in the repo): `tools/run_campaign_night.py` (one night file, strictly sequential jobs),
`tools/night_queue/queue.ps1` (several nights back to back, keep-awake, cutoff, optional wait-for-runner),
`tools/night_queue/launch_detached.ps1` (WMI launch, outside the session), `tools/night_status.py` (status).

## Hard rules (each one cost a lost night or a near miss on 2026-10-27/28)

1. **Launch detached, never from the tool shell.** A runner started by a session's shell dies when that session
   or the app closes (killed at 20:08 mid-job). Use `launch_detached.ps1` (parent becomes WmiPrvSE).
2. **Keep Windows awake.** Idle sleep at 22:21 froze a job for 11 h. `queue.ps1` holds ES_SYSTEM_REQUIRED for
   its lifetime. Wall-clock deadlines inside waiters jump across sleep.
3. **Never start a runner while another runs.** Every job's pre-hygiene KILLS `julia.exe`. Wait on the live
   runner (`-WaitPid <pid> -WaitMatch <text from its command line>`), never on a sleep. **Exception** once the
   lane-aware runner is merged (`docs/OPENCODE_HANDOFF_2026-11-12.md` L1, `lane: cpu`, `.cpu.lane.lock`): ONE
   `lane: gpu` and ONE `lane: cpu` runner may run together — only if `run_campaign_night.py` has no `taskkill /F /IM julia.exe`.
4. **During a live night: no pytest solver tests, no GPU work, and no `hornlab-search run --dry-run`** (it calls
   `worker.install_handlers()` before the dry-run branch). Mesh checks: `tools/shape_check.py` (CPU, safe).
   Offline unit tests that never touch the worker (grid/rows/catalog/night-runner) are fine.
5. **The running night file is LIVE (2026-11-16).** `run_campaign_night.py` re-reads `runs/nights/<night>.yaml`
   before every job: insert/reorder/remove unstarted jobs; the running job is never interrupted; a finished id
   never re-runs. A broken edit logs `RELOAD FAILED` and the last good plan continues; `night`/`lane` are fixed.
   Pause/stop with `runs/nights/<night>/PAUSE`|`STOP` (or top-level `pause:`/`stop:`). `--no-live` = read once.
   See "Splice jobs into a live night".
6. **Do not edit a brief/config a queued or running night uses.** Copy it (e.g. `..._deep_v4.yaml`) instead.

## Watchdog: why a search job stops at 25-85 rows (verified 2026-11-25)

The runner reads a running search's live `search.ndjson` and **stops it with exit 75** (`status: watchdog`) when
it judges the job is not going anywhere (`tools/run_campaign_night.py:96-118`, applied `:1560-1561`). A re-run
needs a **new job id**. Defaults that cut exploration campaigns (6/6 v3 jobs on 2026-11-25):

| YAML key | default | line | turns off at | meaning |
|---|---|---|---|---|
| `min_attempts` | 25 | `:110` | — | no refusal check before this many attempts |
| `refusal_max` | 0.30 | `:112` | — | stop when the refusal fraction in the last `refusal_window` (30) attempts exceeds this |
| `no_gain_valid` | 30 | `:113` | `0` | stop when best is still eval 0 after N valid evals |
| `stall_valid` | 40 | `:114` | `0` | stop when best improved < 0.5 % over the last N valid evals |
| `pin_ignore` | `[]` | `:132-137`, `:198-201` | — | knob names exempt from the bound-pinned stop |

`watchdog:` is a top-level night mapping (all search jobs) or per-job; `watchdog: false` disables it (`:105-106`).
Only the keys above (plus `pin_ignore`, a list) are accepted — an unknown key raises (`:139-141`), so
`pin_min_valid`/`pin_frac`/`pin_count` are **not** YAML-settable (code defaults only, `:196`, `:206`, `:209`).

**Exploration preset** for a job that must not stop before the metric-BO floor of ~100 valid rows:
```yaml
watchdog:
  no_gain_valid: 0      # no "best still eval 0" stop (exploration may start at the seed)
  stall_valid: 0        # no stall stop
  refusal_max: 0.60     # tolerate a wide-box refusal storm (raise from 0.30)
  min_attempts: 50      # do not judge refusals on the first 25 draws
  pin_ignore: [g_stop_deg, g_depth_h_ratio]   # knobs legally pinned at a hard family/envelope limit
```

Put only genuinely hard-pinned knobs in `pin_ignore`. `verify`/cohort/BoTorch jobs are never watched (`:107-108`).

## Launch

1. Write `runs/nights/<night>.yaml` (format in the `tools/run_campaign_night.py` docstring; `kind: search` with
   `config`, `budget`, `mode`, `timeout_s`, optional `resume:`; `kind: command` with `argv`). Resume a killed
   search in its run dir with `budget` = the ORIGINAL cumulative cap (strict resume refuses a shrink; rows already
   in the run dir count, so you get cap-minus-rows — see `cumulative budget cap would shrink (200 -> 109)`).
2. `--dry-run` each night file (prints jobs, runs no hygiene - safe any time).
3. Mesh-check every new config with `tools/shape_check.py` (dofs <= cap, envelope, round coupling).
4. Economy-check every search job with `tools/search_preflight.py` (`--from-runs`, `--samples 64`; skill
   `hornlab-search-economy`). A job starting at the converged incumbent is a wasted night even if every eval succeeds.
5. Pre-flight: `Get-Process julia` (none unless a night is live), `nvidia-smi` baseline, `runs/.gpu.lock` (a dead
   holder's lock is taken over automatically since 2026-10-28; a LIVE holder means wait).
6. Launch:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights A,B,C -Cutoff 17:30 -Log runs\nights\queue_<date>.log"
   ```
7. Verify within a minute: controller pid alive with parent `WmiPrvSE`, log says "starting <night>", a `julia`
   host appears, and the active run's `search.ndjson` gains rows.

Budget a day from measured s/eval (`tools/night_status.py` shows minutes/job; horns 2-7k dofs ~10-30 s/eval,
7-12k dofs 40-60 s/eval). Owner priority first; the cutoff drops the tail.

## Splice jobs into a live night (no restart)

`runs/nights/<night>.yaml` is **re-read before every job** (`run_campaign_night.py:1753-1764`), so insert,
reorder, remove or edit jobs that have not started; the running job is never interrupted and a finished id never
re-runs (give a re-run a new id).

1. **Insert after the running job's id** (or before a not-yet-started id) by a byte-preserving text splice —
   `yaml.safe_dump` the new jobs, split the file on the `- id: <anchor>` line, then re-load and assert the old
   job set is a subset (`len == old + added`). Worked example: `docs/evidence/cd_pm5const_2026-11-25/queue_pm5.py`
   (inserts 7 jobs before an anchor, writes `newline='\n'`, prints `N -> N+7 jobs`).
2. **Validate before the runner sees it:**
   `.venv\Scripts\python.exe tools/run_campaign_night.py --night runs\nights\<night>.yaml --dry-run`
   (checks every path-valued `--config`/`--brief` exists and search jobs have free dimensions, `:1862-1885`; runs
   no hygiene, so it is safe during a live night).
3. A malformed edit is logged `RELOAD FAILED`; `queue_state.json` shows done/running/next (`:1772-1800`). Edit the
   live copy under `runs/nights/`, never `docs/queue/`.

Restarting the *controller*: `taskkill /PID <controller>` (NO `/T` — its child runner must keep running), confirm
the runner survives, then launch `queue.ps1` with `-WaitPid <runner pid> -WaitMatch <night>` and the new list
(`Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'run_campaign_night' }`).

## Status / "any new winners?"

`.venv\Scripts\python.exe tools/night_status.py --since-hours 12` -> queue log tail, each night's finished jobs
(best J, evals, minutes, failures), the live job's progress, and best designs **per brief** (J is comparable only
within a brief). Render winners with hornlab-render.

## Recovery

- Job timed out / killed: its run dir keeps the rows; re-run with `resume:` and the missing budget.
- `exit 124` with `run dir not parsed`: the runner buffers job logs; find the run dir by time (`ls -t runs`).
- Record every stop, re-run and re-order in `docs/CONTINUITY.md` (and ISSUES on a push).

## BoTorch jobs need data (owner, 2026-11-15)
Queue a BoTorch study only on a typology whose cohort already has >= 100 usable training rows
(`tools/bo_compare/prepare_study.py` refuses below `--min-rows`, default 100: `:76`, `:165-167`). New families get
CMA first; BoTorch comes after.
