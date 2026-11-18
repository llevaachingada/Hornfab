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
