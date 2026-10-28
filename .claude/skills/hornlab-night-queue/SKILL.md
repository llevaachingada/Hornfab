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
   runner (`-WaitPid <pid> -WaitMatch <text from its command line>`), never on a sleep.
4. **During a live night: no pytest solver tests, no GPU work, and no `hornlab-search run --dry-run`** (it calls
   `worker.install_handlers()` before the dry-run branch). Mesh checks: `tools/shape_check.py` (CPU, safe).
   Offline unit tests that never touch the worker (grid/rows/catalog/night-runner) are fine.
5. **A running night file is read once.** Appending jobs to it does nothing. Put new jobs in a NEW night file and
   restart the controller (below), or edit a night file that has not started yet.
6. **Do not edit a brief/config a queued or running night uses.** Copy it (e.g. `..._deep_v4.yaml`) instead.

## Launch

1. Write `runs/nights/<night>.yaml` (format: the module docstring of `tools/run_campaign_night.py`; `kind: search`
   with `config`, `budget`, `mode`, `timeout_s`, optional `resume: runs\<run_dir>`; `kind: command` with `argv`).
   Resume a killed search in its own run dir with `budget` = the missing new evals.
2. `--dry-run` each night file (prints jobs, runs no hygiene - safe any time).
3. Mesh-check every new config with `tools/shape_check.py` (dofs <= cap, envelope, round coupling).
4. Pre-flight: `Get-Process julia` (none unless a night is live), `nvidia-smi` baseline, `runs/.gpu.lock` (a dead
   holder's lock is taken over by the runner automatically since 2026-10-28; a LIVE holder means wait).
5. Launch:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights A,B,C -Cutoff 17:30 -Log runs\nights\queue_<date>.log"
   ```
6. Verify within a minute: the controller pid is alive with parent `WmiPrvSE`, the log says "starting <night>",
   a `julia` host appears, and the active run's `search.ndjson` gains rows.

Budget a day from measured s/eval (`tools/night_status.py` shows minutes per job; quarter-model rows horns
2-7k dofs run ~10-30 s/eval, 7-12k dofs 40-60 s/eval). Put the owner's priority first; the cutoff drops the tail.

## Re-order or add work while live

`taskkill /PID <controller>` (NO `/T` - its child runner must keep running), confirm the runner survives, then
launch a new `queue.ps1` with `-WaitPid <that runner's pid> -WaitMatch <its night name>` and the new night list.
Find the runner: `Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'run_campaign_night' }`.

## Status / "any new winners?"

`.venv\Scripts\python.exe tools/night_status.py --since-hours 12` -> queue log tail, each night's finished jobs
(best J, evals, minutes, failures), the live job's progress, and the best designs **per brief** (J is comparable
only within a brief). Then render the winners with the hornlab-render skill.

## Recovery

- Job timed out / killed: its run dir keeps the rows; re-run with `resume:` and the missing budget.
- `exit 124` with `run dir not parsed`: the runner buffers job logs; find the run dir by time (`ls -t runs`).
- Record every stop, re-run and re-order in `docs/CONTINUITY.md` (and ISSUES on a push).
