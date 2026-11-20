# compact400 expansion lanes — resumed run (2026-11-20)

Scope: jobs B1–B8 of the night `cd_v11_verify_and_expand_2026-11-20` — eight resumed
compact400 expansion lanes (`search --resume ... --budget 80/60`, `--mode screen`,
`watchdog: false`). The five verify jobs (A1–A5) are separate evidence:
`docs/evidence/cd_v11_2026-11-20/VERIFY.md`.

Machine (one line; numbers live in `TOOLCHAIN.md`): RTX 4060 Laptop 8 GB (8188 MiB), i7-14650HX,
Windows 11 10.0.26200.

**Identity caveat:** these are v10xo / v7-smooth `compact400` lanes (objective v10, not v11).
They are NOT comparable to the CD v11 lanes in `VERIFY.md` and are not ranked against them here.

## Outcome at a glance

- 5 of 8 expansion lanes ran and each reached its `--budget 80` (80 valid of 80); **0 failed**
  (all exit 0).
- 3 of 8 (`xr__x_s2c_morph`, `xr__x_s2c_fold`, `xr__x_s2c_twinray`) did **not** run in this
  night. An owner STOP (written 15:06:36 local) ended the night after `xr__x_s2b_ext`; the three
  s2c jobs were appended verbatim to the tail of `runs/nights/fav_crowe_2026-11-20.yaml` and the
  STOP note says so. They are **not** a failure and were **not** rerun by this monitor lane.
- Night totals: 10 of 13 planned jobs recorded in `summary.jsonl` (5 verify + 5 s2b).
- No watchdog stop occurred (`watchdog: false` in the night file).

STOP file, verbatim (`runs/nights/cd_v11_verify_and_expand_2026-11-20/STOP`):

```
owner 2026-11-20 15:08: run favorite night fav_crowe_2026-11-20 now; xr__x_s2c_* moved to its tail
```

## Queue / runner log (verbatim, decoded)

Source: `runs/overnight/queue_cd_v11_verify_and_expand_2026-11-20.log` (UTF-8). Lines B1–B8 and
the stop, verbatim:

```
=== 2026-11-20T13:59:28 START xr__x_s2b_morph : .venv/Scripts/hornlab-search.exe search --resume runs/20261120T043224Z-screen-83f65e --budget 80 --mode screen
=== 2026-11-20T14:14:40 END xr__x_s2b_morph exit 0
=== 2026-11-20T14:14:40 START xr__x_s2b_fold : .venv/Scripts/hornlab-search.exe search --resume runs/20261120T043857Z-screen-ae2855 --budget 80 --mode screen
=== 2026-11-20T14:28:48 END xr__x_s2b_fold exit 0
=== 2026-11-20T14:28:48 START xr__x_s2b_twinray : .venv/Scripts/hornlab-search.exe search --resume runs/20261120T044531Z-screen-b1626e --budget 80 --mode screen
=== 2026-11-20T14:47:27 END xr__x_s2b_twinray exit 0
=== 2026-11-20T14:47:27 START xr__x_s2b_petal : .venv/Scripts/hornlab-search.exe search --resume runs/20261120T045235Z-screen-0d3643 --budget 80 --mode screen
=== 2026-11-20T15:02:54 END xr__x_s2b_petal exit 0
=== 2026-11-20T15:02:54 START xr__x_s2b_ext : .venv/Scripts/hornlab-search.exe search --resume runs/20261120T045839Z-screen-5e8a4e --budget 80 --mode screen
=== 2026-11-20T15:20:26 END xr__x_s2b_ext exit 0
=== 2026-11-20T15:20:26 STOP requested; ending night before the next job
=== 2026-11-20T15:20:26 QUEUE DONE
```

`queue_state.json` at stop (`state: stopped`, `running: null`): `done` lists the 5 verify + 5 s2b
jobs; `pending` is `["xr__x_s2c_morph", "xr__x_s2c_fold", "xr__x_s2c_twinray"]`.

## Machine-readable rows (verbatim `summary.jsonl`, jobs B1–B5)

Injected byte-for-byte from `runs/nights/cd_v11_verify_and_expand_2026-11-20/summary.jsonl`
lines 6–10:

```
{"id": "xr__x_s2b_morph", "start": "2026-11-20T18:59:28Z", "end": "2026-11-20T19:14:38Z", "seconds": 910.188, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T043224Z-screen-83f65e", "evals_ndjson": 97, "best_J": 1.52949, "vram_baseline_mb": 771.0, "vram_after_mb": 761.0, "note": "ok; peak 1018 MiB; stop reason: ok; last output: search OK: 97 rows in runs\\20261120T043224Z-screen-83f65e\\search.ndjson; best in runs\\20261120T043224Z-screen-83f65e\\best.json; report with: hornlab-search report runs\\20261120T043", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 97, "rows_window": 97, "valid_rows_window": 89, "best_J_window": 1.5294890526747245, "stop_reason": "ok", "log_tail": ["search: x_s2b_morph mode screen, budget 80 new evaluations, 31 bounded keys, output runs\\20261120T043224Z-screen-83f65e", "  evaluations 97 (96 new, 1 cached), failures {'invalid_envelope': 5, 'invalid_geometry': 3}, GPU 927.0 s, 13.1 s/candidate, 274/h, projected 1,000 = 3.6 h, 10,000 = 36.4 h", "  budget counts: valid, 80 valid of 80 budget, 8 refusals free, attempts 87/108", "  seed J=3.81414  best J=1.52949 (improved on the seed); stop: budget", "search OK: 97 rows in runs\\20261120T043224Z-screen-83f65e\\search.ndjson; best in runs\\20261120T043224Z-screen-83f65e\\best.json; report with: hornlab-search report runs\\20261120T043224Z-screen-83f65e"]}
{"id": "xr__x_s2b_fold", "start": "2026-11-20T19:14:40Z", "end": "2026-11-20T19:28:47Z", "seconds": 847.484, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T043857Z-screen-ae2855", "evals_ndjson": 87, "best_J": 1.18914, "vram_baseline_mb": 761.0, "vram_after_mb": 731.0, "note": "ok; peak 1018 MiB; stop reason: ok; last output: search OK: 87 rows in runs\\20261120T043857Z-screen-ae2855\\search.ndjson; best in runs\\20261120T043857Z-screen-ae2855\\best.json; report with: hornlab-search report runs\\20261120T043", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 87, "rows_window": 87, "valid_rows_window": 87, "best_J_window": 1.1891385633391967, "stop_reason": "ok", "log_tail": ["search: x_s2b_fold mode screen, budget 80 new evaluations, 35 bounded keys, output runs\\20261120T043857Z-screen-ae2855", "14:19:11 WARNING hornlab_mesher.density: [hornlab-mesher] outer wall clearance wants 1.510 mm on 25 of 214 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.", "14:23:05 WARNING hornlab_mesher.density: [hornlab-mesher] outer wall clearance wants 1.105 mm on 35 of 251 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.", "14:25:07 WARNING hornlab_mesher.density: [hornlab-mesher] outer wall clearance wants 1.480 mm on 26 of 282 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.", "  evaluations 87 (86 new, 1 cached), failures {}, GPU 895.1 s, 13.9 s/candidate, 259/h, projected 1,000 = 3.9 h, 10,000 = 38.6 h", "  budget counts: valid, 80 valid of 80 budget, 0 refusals free, attempts 80/108", "  seed J=4.10948  best J=1.18914 (improved on the seed); stop: budget", "search OK: 87 rows in runs\\20261120T043857Z-screen-ae2855\\search.ndjson; best in runs\\20261120T043857Z-screen-ae2855\\best.json; report with: hornlab-search report runs\\20261120T043857Z-screen-ae2855"]}
{"id": "xr__x_s2b_twinray", "start": "2026-11-20T19:28:48Z", "end": "2026-11-20T19:47:26Z", "seconds": 1117.922, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T044531Z-screen-b1626e", "evals_ndjson": 90, "best_J": 1.34583, "vram_baseline_mb": 731.0, "vram_after_mb": 835.0, "note": "ok; peak 1608 MiB; stop reason: ok; last output: search OK: 90 rows in runs\\20261120T044531Z-screen-b1626e\\search.ndjson; best in runs\\20261120T044531Z-screen-b1626e\\best.json; report with: hornlab-search report runs\\20261120T044", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 90, "rows_window": 90, "valid_rows_window": 89, "best_J_window": 1.345834492309212, "stop_reason": "ok", "log_tail": ["search: x_s2b_twinray mode screen, budget 80 new evaluations, 27 bounded keys, output runs\\20261120T044531Z-screen-b1626e", "  evaluations 90 (89 new, 1 cached), failures {'invalid_geometry': 1}, GPU 1263.7 s, 16.8 s/candidate, 214/h, projected 1,000 = 4.7 h, 10,000 = 46.6 h", "  budget counts: valid, 80 valid of 80 budget, 1 refusals free, attempts 81/108", "  seed J=1.73024  best J=1.34583 (improved on the seed); stop: budget", "search OK: 90 rows in runs\\20261120T044531Z-screen-b1626e\\search.ndjson; best in runs\\20261120T044531Z-screen-b1626e\\best.json; report with: hornlab-search report runs\\20261120T044531Z-screen-b1626e"]}
{"id": "xr__x_s2b_petal", "start": "2026-11-20T19:47:27Z", "end": "2026-11-20T20:02:53Z", "seconds": 925.718, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T045235Z-screen-0d3643", "evals_ndjson": 92, "best_J": 1.59407, "vram_baseline_mb": 835.0, "vram_after_mb": 884.0, "note": "ok; peak 1224 MiB; stop reason: ok; last output: search OK: 92 rows in runs\\20261120T045235Z-screen-0d3643\\search.ndjson; best in runs\\20261120T045235Z-screen-0d3643\\best.json; report with: hornlab-search report runs\\20261120T045", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 92, "rows_window": 92, "valid_rows_window": 89, "best_J_window": 1.5940712061073, "stop_reason": "ok", "log_tail": ["search: x_s2b_petal mode screen, budget 80 new evaluations, 31 bounded keys, output runs\\20261120T045235Z-screen-0d3643", "  evaluations 92 (91 new, 1 cached), failures {'invalid_geometry': 3}, GPU 925.3 s, 13.6 s/candidate, 264/h, projected 1,000 = 3.8 h, 10,000 = 37.9 h", "  budget counts: valid, 80 valid of 80 budget, 3 refusals free, attempts 83/108", "  seed J=2.85581  best J=1.59407 (improved on the seed); stop: budget", "search OK: 92 rows in runs\\20261120T045235Z-screen-0d3643\\search.ndjson; best in runs\\20261120T045235Z-screen-0d3643\\best.json; report with: hornlab-search report runs\\20261120T045235Z-screen-0d3643"]}
{"id": "xr__x_s2b_ext", "start": "2026-11-20T20:02:54Z", "end": "2026-11-20T20:20:25Z", "seconds": 1050.891, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T045839Z-screen-5e8a4e", "evals_ndjson": 91, "best_J": 1.83205, "vram_baseline_mb": 883.0, "vram_after_mb": 1061.0, "note": "ok; peak 1537 MiB; stop reason: ok; last output: search OK: 91 rows in runs\\20261120T045839Z-screen-5e8a4e\\search.ndjson; best in runs\\20261120T045839Z-screen-5e8a4e\\best.json; report with: hornlab-search report runs\\20261120T045", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 91, "rows_window": 91, "valid_rows_window": 89, "best_J_window": 1.8320460235672849, "stop_reason": "ok", "log_tail": ["search: x_s2b_ext mode screen, budget 80 new evaluations, 33 bounded keys, output runs\\20261120T045839Z-screen-5e8a4e", "  evaluations 91 (90 new, 1 cached), failures {'invalid_envelope': 2}, GPU 1119.8 s, 15.6 s/candidate, 231/h, projected 1,000 = 4.3 h, 10,000 = 43.3 h", "  budget counts: valid, 80 valid of 80 budget, 2 refusals free, attempts 82/108", "  seed J=5.085  best J=1.83205 (improved on the seed); stop: budget", "search OK: 91 rows in runs\\20261120T045839Z-screen-5e8a4e\\search.ndjson; best in runs\\20261120T045839Z-screen-5e8a4e\\best.json; report with: hornlab-search report runs\\20261120T045839Z-screen-5e8a4e"]}
```

## Per-lane results

"Pre-resume rows" = the stored `search.ndjson` prefix replayed on resume (`last_invocation.cache_hits`);
"→ ok" counts rows with `ok=true` in that prefix. "Resumed new evals" = `last_invocation.non_cached`;
"→ ok" counts `ok=true` in the appended rows. The job's own budget line (quoted in the next section)
reports `80 valid of 80 budget`; the row-level prefix/suffix split is separate accounting.
Final rows and best are from `search.ndjson` / `best.json`.

| lane | run dir | pre-resume rows→ok | resumed new evals→ok | total rows | budget line | refusals free / strict | failures (cum) | best J | best hash | eval |
|---|---|---|---|---:|---|---|---|---|---|---|
| xr__x_s2b_morph | `20261120T043224Z-screen-83f65e` | 38→31 | 59→58 | 97 | 80/80 valid, attempts 87/108 | 8 / 7 | 8 (5 envelope, 3 geometry) | 1.5294890526747245 | `c1e06aef024a` | 89 |
| xr__x_s2b_fold | `20261120T043857Z-screen-ae2855` | 31→31 | 56→56 | 87 | 80/80 valid, attempts 80/108 | 0 / 0 | 0 | 1.1891385633391967 | `b158b55bd5c9` | 70 |
| xr__x_s2b_twinray | `20261120T044531Z-screen-b1626e` | 32→31 | 58→58 | 90 | 80/80 valid, attempts 81/108 | 1 / 1 | 1 (geometry) | 1.345834492309212 | `8b57e5d15494` | 84 |
| xr__x_s2b_petal | `20261120T045235Z-screen-0d3643` | 31→31 | 61→58 | 92 | 80/80 valid, attempts 83/108 | 3 / 3 | 3 (geometry) | 1.5940712061073 | `8eae2b169ee2` | 9 |
| xr__x_s2b_ext | `20261120T045839Z-screen-5e8a4e` | 32→31 | 59→58 | 91 | 80/80 valid, attempts 82/108 | 2 / 2 | 2 (envelope) | 1.8320460235672849 | `76b0f34ec773` | 11 |

All five: `stop_reason=budget`, status `finished`, exit 0, `watchdog: false`, so no watchdog stop
and no remaining job failure. Every lane improved on its seed (seed J: morph 3.81414, fold 4.10948,
twinray 1.73024, petal 2.85581, ext 5.085; job logs).

## Budget / failures, verbatim per-lane lines

From each lane's job log (`runs/nights/cd_v11_verify_and_expand_2026-11-20/xr__x_s2b_*.log`):

```
xr__x_s2b_morph
  evaluations 97 (96 new, 1 cached), failures {'invalid_envelope': 5, 'invalid_geometry': 3}, GPU 927.0 s, 13.1 s/candidate, 274/h, projected 1,000 = 3.6 h, 10,000 = 36.4 h
  budget counts: valid, 80 valid of 80 budget, 8 refusals free, attempts 87/108

xr__x_s2b_fold
  evaluations 87 (86 new, 1 cached), failures {}, GPU 895.1 s, 13.9 s/candidate, 259/h, projected 1,000 = 3.9 h, 10,000 = 38.6 h
  budget counts: valid, 80 valid of 80 budget, 0 refusals free, attempts 80/108

xr__x_s2b_twinray
  evaluations 90 (89 new, 1 cached), failures {'invalid_geometry': 1}, GPU 1263.7 s, 16.8 s/candidate, 214/h, projected 1,000 = 4.7 h, 10,000 = 46.6 h
  budget counts: valid, 80 valid of 80 budget, 1 refusals free, attempts 81/108

xr__x_s2b_petal
  evaluations 92 (91 new, 1 cached), failures {'invalid_geometry': 3}, GPU 925.3 s, 13.6 s/candidate, 264/h, projected 1,000 = 3.8 h, 10,000 = 37.9 h
  budget counts: valid, 80 valid of 80 budget, 3 refusals free, attempts 83/108

xr__x_s2b_ext
  evaluations 91 (90 new, 1 cached), failures {'invalid_envelope': 2}, GPU 1119.8 s, 15.6 s/candidate, 231/h, projected 1,000 = 4.3 h, 10,000 = 43.3 h
  budget counts: valid, 80 valid of 80 budget, 2 refusals free, attempts 82/108
```

(The `evaluations N (M new, 1 cached)` counter is cumulative over the run's history and includes
the pre-resume rows; `last_invocation.non_cached` in the table is the per-resume new-solve count.)

## Lanes not run (still short)

| lane | run dir | pre-resume rows | status |
|---|---|---:|---|
| xr__x_s2c_morph | `20261120T050543Z-screen-29377f` | 61 | not run; moved to `fav_crowe_2026-11-20` tail |
| xr__x_s2c_fold | `20261120T052219Z-screen-c1c895` | 30 | not run; moved to `fav_crowe_2026-11-20` tail |
| xr__x_s2c_twinray | `20261120T053053Z-screen-32a9e3` | 30 | not run; moved to `fav_crowe_2026-11-20` tail |

The three are present in `runs/nights/fav_crowe_2026-11-20.yaml` (ids and the same `--resume` dirs).
Their rows were unchanged at the stop (`search.ndjson` line counts still 61/30/30); no s2c job log
or summary row exists in this night. They remain short by their full s2c budget.

## Caveats

- **Own brief identities.** These are v10 `compact400` x-lanes; their J is comparable only within
  the same brief/objective, never to the CD v11 verify Js or across objective versions.
- **No rescore.** The resume replays the stored `search.ndjson` prefix through the cache and
  appends new rows; no stored row was re-solved or rescaled.
- **Budget semantics.** `--budget N` is printed by the CLI as "budget N new evaluations"; the
  five s2b lanes were queued at 80 and each logged `80 valid of 80 budget`. The s2c jobs were
  appended with "cumulative budgets" per the `fav_crowe` night comment and did not run here.
- **STOP is not a failure.** The night stopped on an owner-requested STOP file (quoted above);
  the running `xr__x_s2b_ext` finished normally (exit 0) before the runner ended.
- Numbers were read from `summary.jsonl`, `queue_state.json`, `run.json`, `best.json`,
  `search.ndjson` and the queue/job logs; the injected `summary.jsonl` block and the queue block
  are byte-checked against their source files.
