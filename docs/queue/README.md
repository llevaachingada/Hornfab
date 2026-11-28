# Nights and the queue directory

A "night" is one YAML file listing sequential GPU jobs. Two copies of that file matter, and they
are not interchangeable.

| Where | Role |
|---|---|
| `runs/nights/<night>.yaml` | **Live.** Gitignored (`/runs/` in `.gitignore`). `run_campaign_night.py` re-reads it before **every** job, so edits apply to jobs that have not started. |
| `docs/queue/<name>.yaml` | **Committed copy.** Tracked history of what was queued; not the live file a running night re-reads. |

The live file wins. A committed `docs/queue/` copy records intent and provenance, not the current
plan; if the two differ while a night is live, the live file is authoritative. `--no-live` makes the
runner read the night file once (old behaviour) instead of re-reading it per job.

Also in `docs/queue/`: admission packets (`*.admission.json`), plans and audit notes (`*.md`), seed
and render sheets (`.png`), and reference-image subfolders. Those support a night but are not night
configs. The committed entries are catalogued one line each in
[`docs/evidence/CATALOG.md`](../evidence/CATALOG.md) under "Committed queue configs" (the 112
`docs/queue/` rows in the I3 inventory; newer files are not separate inventory rows).

## Finding a night's summary

Each night writes a directory beside its live YAML:

- `runs/nights/<night>/summary.jsonl` — one JSON record per finished job (id, start/end, exit code,
  best J, run directory, and rows/VRAM details where the runner recorded them).
- `runs/nights/<night>/SUMMARY.md` and per-job `*.log` files, when the runner or
  `tools/night_report.py` wrote them.

To turn the records into a morning report:

```powershell
.venv\Scripts\python.exe tools/night_report.py --night <night> --out docs/evidence/NIGHT_<date>.md
```

`--night` is repeatable; `--runs-root` defaults to `<repo>/runs`. For live progress use
`tools/night_status.py` (read-only) rather than re-running a report.

## Splice a job into a live night

Edit `runs/nights/<night>.yaml` while the runner is live: insert, reorder or remove **unstarted**
jobs. The running job is never interrupted and a finished id never re-runs. A broken edit logs
`RELOAD FAILED` and the last good plan continues; `night` and `lane` are fixed.

Validate the edit before the runner reaches it:

```powershell
.venv\Scripts\python.exe tools/run_campaign_night.py --night runs/nights/<night>.yaml --dry-run
```

`--dry-run` prints the resolved job list and launches nothing. Add `--only <id>` to resolve one job.
An `--admission <json>` packet is checked before any job, dry-run included.

## Operating rules

- One GPU solve at a time; never start a second runner while one is live.
- Pause or stop with `runs/nights/<night>/PAUSE` or `STOP` (or top-level `pause:`/`stop:` in the
  YAML).
- Do not edit a brief or config a queued/running night uses; copy it to a new file instead.
- Re-read the live file and the status tool before adding work. A committed `docs/queue/` copy is
  not evidence that a job ran.

Full mechanics, watchdog keys and recovery procedures:
[`hornlab-night-queue`](../../.claude/skills/hornlab-night-queue/SKILL.md). Single-job GPU
mechanics stay with `hornlab-gpu-job`.
