# Review: night `cd_rrect_2026-11-17` record (cloud senior, 2026-11-18)

Source: commit `2b35194` on `hornfab-all-2026-11-18`,
`archive/2026-11-18-unintegrated/night_cd_rrect_2026-11-17/` (`summary.jsonl` 58 rows,
`queue_state.json` at 15:30:48Z, night file + backup, `held_and_edited_2026-11-18.md`,
`poll_throat.log`). The pushed data has **no CSVs**; the per-job logs (`runs/nights/<night>/<id>.log`)
were not pushed, so failure causes beyond the summary's `note` field are open.
Plan anchors: WP 0.6 / 0.7 (night truth), WP 7.2 / 7.3 / D8 (continuation advice), WP 2.2 / D7.
Labels: [verified] computed here from the archived files · [inferred] · [open] needs the logs.

## 1. Throat rows cross-check: PASS [verified]

All 7 Phase 1 rows, both Phase 2 rows and the Phase 3 row carry exactly the J in
`docs/evidence/throat_hv_2026-11-18/` (`phase1_summary.csv`, `p2_evals.csv`, part3). The three
burned `kind: search` ids show the pycma crash verbatim (`search ABORTED: TypeError: ufunc 'isinf'`,
`search.ndjson missing`), which is the case `681e429` now refuses up front. The plan §10.2
authority table therefore stands on the night's own ledger.

## 2. Where the night's 20.2 GPU-hours went [verified]

| Status | Rows | Hours |
|---|---:|---:|
| ok | 32 | 14.67 |
| failed | 14 | 3.49 |
| blocked | 12 | 2.06 |

- **07:02-07:51 on 11-17: six blocked rows, ~50 min**, all "GPU lock still present … after 300 s"
  or "gpu-clean reported GPU busy". A stale-lock episode, not a job fault.
- **Largest single losses:** `cont_p80_athcore_corelaw_200` failed after 2 h 10 min with no rows
  counted; `t_trit80_rc2` ran 2 h 01 min and is recorded **`ok` with 0 evals and `best_J: null`**;
  `cont_biradial_smooth_200` failed after 33 min. [open: causes are in the logs]

## 3. BO arms: none finished, and the handoff undercounts why [verified + open]

`HANDOFF_2026-11-18.md` says two BO arms were skipped (owner-authorized). The ledger shows **9 BO
arm jobs, 0 completed**:

| Arm | Status | Exit | Note (verbatim start) | Reading |
|---|---|---|---|---|
| `t_klame_turbo100` | failed | 1 | `exit code 1` (20 min) | [open] |
| `t_klame_scalar100` | failed | 1 | `exit code 1` (18 min) | [open] |
| `t_ath14_turbo100` | failed | 2 | `BO screen 30 … observations 29 … refusing: C:\Users\…` (1 s) | a stock-resume refusal (package exists) [inferred]; **not** one of the two owner-skipped arms |
| `t_ath14_scalar100` | blocked ×2 | 1, 2 | 75 then 78 observations, best 5.983 | the owner-authorized kill; resume with a fresh `--root` |
| `t_hvlaw_turbo100` | failed | 3 | `refusing: task hl__ext_throat_hvlaw_v7 h…` (2 s) | **refused by design**: the text matches `tools/bo_compare/prepare_study.py:166` "refusing: task … has N usable training rows (< --min-rows …); build a CMA cohort first" (owner rule 2026-11-15, exit 3) [code-verified]. N itself is in the log [open] |
| `t_hvlaw_scalar100` | failed | 3 | same | same: not enough training rows for BoTorch |
| `t_corelaw_turbo100` | failed | 1 | `training rows: 206 (min 100)` (163 s) | the second owner-authorized skip per part3 |
| `t_corelaw_scalar100` | running at 15:30Z | | | |
| `t_atlas_*_turbo300` ×2 | pending (moved to the end) | | | |

So beyond the two owner skips, **three arms refused at launch** (`t_ath14_turbo100`; both
`t_hvlaw`, which lack the training rows BoTorch needs, so a CMA cohort comes first) and **two
failed** (`t_klame` ×2). Before the BO arms are re-queued, the local agent reads the
`t_klame` ×2 and `t_ath14_turbo100` logs and records each cause, and the row count N for `t_hvlaw`.
Exit code 3 also means "GPU busy" in the CLI, but the runner classifies `blocked` from the
`GPU busy` marker in the job's own output, not from the exit code (`classify_status`,
`run_campaign_night.py:465-479`) [code-verified], so the `t_hvlaw` rows are correctly `failed`.

## 4. Night-truth defects visible in the ledger (WP 0.7) [verified]

1. **`ok` with no result:** `t_trit80_rc2` (2 h, `evals_ndjson: 0`, `best_J: null`, status `ok`).
   Either the job wrote its rows somewhere the runner does not parse (BO package, not
   `search.ndjson`) or it did nothing. An `ok` row should never be indistinguishable from "nothing
   happened". Proposal: when a job exits 0 with no parsed run dir, no rows and no BO progress,
   record `status: ok_no_result` (new rows only). Fits WP 0.7.
2. **Failed rows without a run dir or stop reason** for the 11-17 rows (`b3_soft_resume`,
   `c_rrect_100w`, `cont_p80_athcore_corelaw_200`, `cont_biradial_smooth_200`): these predate the
   `04dd5af` night-truth fields; the 11-18 rows do carry `stop_reason`. No action beyond reading
   the logs.

## 5. Results that must not be compared [verified]

The ok rows span many briefs and objective blocks (home v7, 80x60 v7, hifi verify, the `range15`
rows at J ≈ 88-95, Klangfilm-Lame at ≈ 7.4-8.6, Le Cléac'h AR at 19.0). Per invariant 7 these J
are **only** comparable within one run's own identity. Two within-lane notes [verified]:
`c_warm_resume_c221aa` 3.62101 and `c_warm_resume_ab4fb9` 3.66079 are the same fold-warm family
under the home brief and differ by 0.040 (a **tie** under the 0.13 floor); `cont_r50_refine_200`
reached 3.41738 under its own identity. The four `home_range15_*` rows (15 evals each, J 88.7-94.8)
look like penalty-dominated scores [inferred]; do not read them as horn quality.

## 6. Pending queue vs the new zero-dimension guard [verified in the cloud]

`zero_dimension_searches` logic applied to every job from `t_corelaw_scalar100` on: **no pending job
has zero free dimensions.** Stock `_w1` lanes have 3-18 free keys; the 5 bridge-type lanes
(`rosse_rect`, `crowe_panel`, `klangfilm_lame`, `section_pucker` rows) and the warm-start lanes
cannot load on the stock path (or without `runs/`), so `--dry-run` prints a NOTE for them and does
not fail. The live night needs no edit for `681e429`.

Note for the queue owner [verified]: `w_lecleach_ctrl/fc540/fc540_T_narrow_200w1` run with
`--backend beat_cpu` inside a `lane: gpu` night. That is legal (no GPU lock), but each is a
200-eval CPU search in the GPU lane's serial order (CPU measured ~4x slower per frequency on the
screen grid, `BENCH_FULLRANGE_THREADS_2026-11-03`). If they were meant for the CPU lane, they
belong in a `lane: cpu` night beside the GPU work.

## 7. Process note

`2b35194` added a new top-level `archive/` tree without CONTINUITY, ISSUES or INDEX entries (the
push rule in CLAUDE.md). This review's commit adds the INDEX line and the log entries.

## 8. Local agent actions (CPU, read-only)

1. Read and quote the cause lines from `runs\nights\cd_rrect_2026-11-17\` logs for:
   `t_klame_turbo100`, `t_klame_scalar100`, `t_ath14_turbo100`, `t_hvlaw_turbo100`,
   `t_hvlaw_scalar100`, `t_trit80_rc2`, `cont_p80_athcore_corelaw_200`,
   `cont_biradial_smooth_200`, `c_rrect_100w_rc2`. PowerShell:
   `Get-Content runs\nights\cd_rrect_2026-11-17\<id>.log -Encoding Unicode | Select-String -Pattern 'refusing|Error|Traceback|ABORTED' | Select-Object -Last 5`
   (logs are UTF-16 from PS 5.1 Tee; use `-Encoding Unicode`).
2. Append the causes to this file as a dated section; open an ISSUES entry per distinct cause.
3. Only then re-queue BO arms (fresh `--root` each) with owner approval.

## 2026-11-18 - failure causes (STEP 2c, WP 0.7)

**Encoding correction (supersedes section 8 item 1).** The night logs are **UTF-8**, not UTF-16.
`tools/run_campaign_night.py` writes each per-job log with
`open(log_path, "a", encoding="utf-8", errors="replace")` (L1448, also L859), decodes the child pipe
as `encoding="utf-8", errors="replace"` (L1403) and reads it back `encoding="utf-8"`
(`_read_text`, L1596 -> L1197). `-Encoding Unicode` is therefore the wrong decoder: on
`t_hvlaw_turbo100.log` it matches `refusing` **0** times, while `Get-Content -Encoding UTF8` returns
the line quoted below. Every quote in this section was decoded with `-Encoding UTF8`; nothing was
paraphrased. Logs were read from `runs/nights/cd_rrect_2026-11-17/<id>.log`; the `runs/` trees were
not modified and no GPU process was touched.

### t_klame_turbo100 / t_klame_scalar100 - code fault in a tool (silent builder/package step)

Both arms build their cohort (the manifest printed `"exact_complete": 200`), clear the row gate, then
die with a bare exit 1 and no traceback. Verbatim tail of `t_klame_turbo100.log`:

```
L42: training rows: 200 (min 100)
L43: === job t_klame_turbo100 end 2026-11-17T11:16:37Z exit=1
```

`t_klame_scalar100.log` is identical except the end line:
`=== job t_klame_scalar100 end 2026-11-17T11:34:56Z exit=1` (its `training rows: 200 (min 100)` is
also L42). No `Traceback`, no `search ABORTED`, and the package manifest that
`prepare_study.py` prints with `flush=True` after the four builders (L187-190) never appears.
`prepare_study.py` itself only returns 0/2/3, so the bare 1 was produced after the row gate and
without a surfaced cause.

- fix candidate: `tools/bo_compare/prepare_study.py` - the `create_study` + four builder calls +
  `prepare_run_package` block (L176-190) has no per-step failure report/flush, so a step that dies
  abnormally leaves `training rows:` as the last visible line and exit 1 as the only evidence.
- fix candidate: `tools/run_campaign_night.py` - `build_job_env` (L441-447) does not set
  `PYTHONUNBUFFERED=1` for the child, so block-buffered stdout is lost on a non-flushing death.

### t_ath14_turbo100 - environment (BEAT host reset) + config/queue fault (stale `--root`)

The log holds two launches. First launch `2026-11-18T01:52:31Z`, verbatim:

```
L11: training rows: 219 (min 100)
L85: ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host
L87: solve failed for 188843809b45: [worker_exit] ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None)
```

The BO arm survived (it kept writing gpytorch warnings) but attempt 1 has **no** `=== job ... end`
marker: the log jumps straight to `=== pre-hygiene t_ath14_turbo100 ... 2026-11-18T13:36:31Z` (L191),
i.e. the first attempt was cut off outside the runner's normal loop. The relaunch was then refused:

```
L198: === job t_ath14_turbo100 start 2026-11-18T13:36:33Z timeout=25200s
L201: refusing: C:\Users\hunte\Hrns\hornlab-search\runs\night31_2026-11-17\t_ath14_turbo100\package.json exists (use a fresh --root)
L202: === job t_ath14_turbo100 end 2026-11-18T13:36:33Z exit=2
```

- fix candidate: `hornlab_search/solve/beat.py:_attempt` - a `worker_exit` ConnectionReset(10054) is
  retried into the same dead worker registration; the worker replace/re-warm aspect is the one to
  inspect (two consecutive solve failures on mesh `188843809b45`).
- fix candidate: night queue entry for `t_ath14_turbo100` - the re-queue reuses
  `runs/night31_2026-11-17/t_ath14_turbo100`; a fresh `--root` (or an explicit resume path) is
  required, and `run_bo_arm.py` (L44) passes `--root` through without a pre-existence check.

### t_hvlaw_turbo100 / t_hvlaw_scalar100 - config-owner fault (empty cohort), N = 0

Both refuse before any study is created. Verbatim (`t_hvlaw_turbo100.log` L11-12; the scalar log has
the same L11 with `... end 2026-11-18T15:05:58Z exit=3` on L12):

```
L11: refusing: task hl__ext_throat_hvlaw_v7 has 0 usable training rows (< --min-rows 100); build a CMA cohort first
L12: === job t_hvlaw_turbo100 end 2026-11-18T15:05:55Z exit=3
```

The training-row count is **N = 0** (verbatim from the refusal line). `--min-rows` is 100, so this
is the intended refusal, not a crash: task `hl__ext_throat_hvlaw_v7` has no solved CMA cohort yet.

- fix candidate: cohort/task owner for `hl__ext_throat_hvlaw_v7` - build the CMA cohort before any
  BO arm is queued (or drop these two arms from the BO comparison; exit 3 is the documented guard).

### t_trit80_rc2 - not-a-failure (exit 0), but the pool was exhausted at 82 calls

Verbatim:

```
L47: {"study_id": "1ff9fb9cb6d04e358685213206425478", "policy": "turbo", "package_id": "3ddea3acb9d6fd512e858945e598b5e28da498f7d0263522e3c6aa5647eb3fb9", "budget": {"screen_calls": 80, "verify_calls": 2, "total_calls": 82, "attempts": 400}, "budget_profile": "comparison-80x2", "deadline": "2026-11-17T17:40:58.483555+00:00", "steps": {"freeze_snapshot": "ok", "build_training": "ok", "build_analysis": "ok", "build_proposal": "ok"}, "preflight": {"status": "ok", "reason": null, "detail": null}}
L531: {"ok":true,"package_id":"3ddea3acb9d6fd512e858945e598b5e28da498f7d0263522e3c6aa5647eb3fb9","progress":{"attempts":82,"consecutive_failures":0,"reservations":{"screen_calls":0,"total_calls":0,"verify_calls":0},"screen_calls":80,"total_calls":82,"unresolved":false,"verify_calls":2,"verify_candidates":2},"run_dir":"C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\study-3ddea3acb9d6fd51","status":"pool_exhausted"}
L532: === job t_trit80_rc2 end 2026-11-17T13:36:08Z exit=0
```

This is the healthy arm: all four build steps `ok`, preflight `ok`, 80 screen + 2 verify calls, exit
0. `pool_exhausted` means the candidate pool ran dry at 82 of the 400 permitted attempts, i.e. the
arm spent its comparison-80x2 budget, not a fault.

### cont_p80_athcore_corelaw_200 - code fault in a tool (silent exit 1, no cause line)

Verbatim:

```
L9: === argv: .venv/Scripts/hornlab-search.exe search --resume runs/20261115T020650Z-screen-22931c --budget 200
L11: 11:49:52 WARNING hornlab_search.solve.worker: beat_cuda: BEAT host changed between solve 1 and 2 ((52032, 62388) -> (52032, 58168)): the warm worker is not being reused
L39: === job cont_p80_athcore_corelaw_200 end 2026-11-17T18:57:58Z exit=1
```

The only visible child output is mesher **stderr** warnings; the last one is at local `13:54:11`
(the log mixes local-time `logging` stamps with `Z` runner stamps, EST offset), ~2h07m after the
`16:47:53Z` start. There is no `search: <name> mode ...` banner, no `search ABORTED`/`search FAILED`
line, no `Traceback`. The runner's own kill paths did not fire (no `=== WATCHDOG` / `=== TIMEOUT`
line), so the child returned 1 on its own and its stdout diagnostics were never flushed into the
log. `_search_body` has no return-1 path that does not print first, so the printed cause was lost
with the stdout buffer (block-buffered pipe, `PYTHONUNBUFFERED` unset).

- fix candidate: `hornlab_search/cli.py` - flush the search banner (L771) and the terminal
  ABORTED/FAILED/INTERRUPTED lines (L779-783), so a hard exit cannot erase the cause.
- fix candidate: `tools/run_campaign_night.py` - `build_job_env` (L441-447) sets no
  `PYTHONUNBUFFERED=1`; add it so non-flushing exits still deliver the child's stdout.

### cont_biradial_smooth_200 - code fault in a tool (silent exit 1, zero child lines)

Verbatim, the complete child-visible output:

```
L9: === argv: .venv/Scripts/hornlab-search.exe search --resume runs/20261116T193501Z-screen-f008ad --budget 200
L11: === job cont_biradial_smooth_200 end 2026-11-18T00:44:49Z exit=1
```

Start was `2026-11-18T00:12:11Z`; that is 32m38s of work with **no** child line at all - not even a
mesher warning - then exit 1. Same family and same fix candidates as `cont_p80_...` (stdout not
flushed; no watchdog/timeout marker; `_search_body` prints before every return-1 path).

### c_rrect_100w_rc2 - config-owner fault (budget cap would shrink)

Verbatim:

```
L9: === argv: .venv/Scripts/python.exe tools/geometry/rosse_rect_cli.py search --config examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7_r100w.yaml --mode screen --budget 109 --cma-seed 5679 --resume C:\Users\hunte\Hrns\hornlab-search\runs\20261117T070118Z-screen-8627f8
L12: search ABORTED: ConfigError: C:\Users\hunte\Hrns\hornlab-search\runs\20261117T070118Z-screen-8627f8: strict resume refused: cumulative budget cap would shrink (110 -> 109); caps persist unless explicitly extended (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261117T070118Z-screen-8627f8)
L13: === job c_rrect_100w_rc2 end 2026-11-17T13:36:35Z exit=1
```

The guard fired exactly as designed: the run dir already carried a cumulative cap of 110 and the
queue asked for 109. No code is wrong here; the queue entry is.

- fix candidate: night queue entry for `c_rrect_100w_rc2` - request `--budget` >= the persisted cap
  (110 against this run dir), or extend the cap explicitly, instead of 109.

### Against the prior-pass expectations [checked]

- t_klame x2: confirmed `training rows: 200 (min 100)` then exit 1 with no traceback. Added: the
  cohort manifest (`"exact_complete": 200`) is present, and the package JSON is absent.
- t_ath14_turbo100: confirmed the ConnectionResetError(10054) and the `package.json exists (use a
  fresh --root)` refusal. Added: the log contains **two** launches and attempt 1 has no end marker;
  the summary records 30 screen evaluations for the arm, final exit 2.
- t_hvlaw x2: confirmed exactly, N = 0, exit 3.
- t_trit80_rc2: partially different - exit 0 and `status: pool_exhausted` are confirmed, but the arm
  did **not** run 0 evals: progress reports `"screen_calls":80`, `"verify_calls":2`,
  `"total_calls":82`. The `0 evals` figure is the night summary's `evals_ndjson` counter, not work.
- cont_p80 / cont_biradial: confirmed quiet exit 1 with no diagnostic line (biradial has zero child
  lines; corelaw has stderr-only mesher warnings for ~2h07m). The run dirs
  (`runs/20261115T020650Z-screen-22931c`, `runs/20261116T193501Z-screen-f008ad`) were not opened in
  this pass; a stop reason recorded there is the next place to look.
- c_rrect_100w_rc2: confirmed exactly (110 -> 109).

Per-id verdicts above feed the BO-arms decision (owner decision 8, night review): of the nine ids
only `t_trit80_rc2` is a clean arm result; `t_ath14_turbo100` is one environment reset plus one
stale-root re-queue; three are guard refusals with a config-owner cause (`t_hvlaw` x2,
`c_rrect_100w_rc2`); and four (`t_klame` x2, `cont_p80`, `cont_biradial`) are tool-side silent
failures whose diagnostics this pass could not recover. **No code was fixed in this pass** - the
`fix candidate:` lines are candidates only, and the owner decision 8 call stays open.
