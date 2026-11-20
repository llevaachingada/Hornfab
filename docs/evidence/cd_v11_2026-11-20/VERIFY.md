# CD v11 verify grid — five verify solves (2026-11-20)

Scope: jobs A1–A5 of the night `cd_v11_verify_and_expand_2026-11-20`. One verify-grid
(`--mode verify`, 29 frequencies / 1024 balloon points, `dof_cap_verify: 24000`) solve of each
of the five v11 CD completion bests from `fable_expand`/completion runs. The expansion lanes
(jobs B1–B8) are separate evidence: `docs/evidence/expand_2026-11-20/COMPLETION.md`.

Machine (one line; numbers live in `TOOLCHAIN.md`): RTX 4060 Laptop 8 GB (8188 MiB), i7-14650HX,
Windows 11 10.0.26200; Julia 1.12.7 / Python 3.12.10 (`runs/*/run.json`).

All five jobs: queue exit code 0, one evaluation each, zero failures. No solve was rescored,
cached or pooled: each job is a single fresh verify-grid evaluation of the seed parameters.

## What ran

Configs: `examples/typologies/cd_v11_verify_2026-11-20/cd11v__*.yaml`, each a `seed_params`
replay of the completion best named in its file header, with `run --mode verify` only.

RECONSTRUCTED invocation (from the night file and the per-job logs; the exact argv is pasted
below):

```
.venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/<lane>.yaml --mode verify
```

## Queue / runner log (verbatim, decoded)

Source: `runs/overnight/queue_cd_v11_verify_and_expand_2026-11-20.log` (UTF-8; the file is not
UTF-16). Verbatim:

```
=== 2026-11-20T13:54:11 START cd11v__ext_throat_hvlaw : .venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/cd11v__ext_throat_hvlaw.yaml --mode verify
=== 2026-11-20T13:55:15 END cd11v__ext_throat_hvlaw exit 0
=== 2026-11-20T13:55:15 START cd11v__osse_fold_warm : .venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/cd11v__osse_fold_warm.yaml --mode verify
=== 2026-11-20T13:56:12 END cd11v__osse_fold_warm exit 0
=== 2026-11-20T13:56:12 START cd11v__osse_morph : .venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/cd11v__osse_morph.yaml --mode verify
=== 2026-11-20T13:57:11 END cd11v__osse_morph exit 0
=== 2026-11-20T13:57:11 START cd11v__ath_core_petal : .venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/cd11v__ath_core_petal.yaml --mode verify
=== 2026-11-20T13:58:27 END cd11v__ath_core_petal exit 0
=== 2026-11-20T13:58:27 START cd11v__crowe_x_osse_cd : .venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/cd11v__crowe_x_osse_cd.yaml --mode verify
=== 2026-11-20T13:59:28 END cd11v__crowe_x_osse_cd exit 0
```

`summary.jsonl` rows (all five, exit_code 0):

```
{"id": "cd11v__ext_throat_hvlaw", "start": "2026-11-20T18:54:11Z", "end": "2026-11-20T18:55:13Z", "seconds": 62.687, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185416Z-verify-9d392f", "evals_ndjson": 1, "best_J": 3.3405686204251346, "vram_baseline_mb": 913.0, "vram_after_mb": 841.0, "note": "ok; peak 1247 MiB; stop reason: ok; last output: run OK: seed J=3.34057, 4259 dofs, solve 36.9 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185416Z-verify-9d392f", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 1, "rows_window": 1, "valid_rows_window": 1, "best_J_window": 3.3405686204251346, "stop_reason": "ok", "log_tail": ["  terms (raw): cov=0  rip=0.3009  di=0  dislope=0.05148  flat=0.6295  load=0  penalty=0  total J=3.34057  n_nan=0  DI source=balloon", "run OK: seed J=3.34057, 4259 dofs, solve 36.9 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185416Z-verify-9d392f"]}
{"id": "cd11v__osse_fold_warm", "start": "2026-11-20T18:55:15Z", "end": "2026-11-20T18:56:11Z", "seconds": 56.469, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185520Z-verify-fec2a6", "evals_ndjson": 1, "best_J": 3.6146314312259817, "vram_baseline_mb": 884.0, "vram_after_mb": 809.0, "note": "ok; peak 1045 MiB; stop reason: ok; last output: run OK: seed J=3.61463, 3836 dofs, solve 30.7 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185520Z-verify-fec2a6", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 1, "rows_window": 1, "valid_rows_window": 1, "best_J_window": 3.6146314312259817, "stop_reason": "ok", "log_tail": ["  terms (raw): cov=0  rip=0.203  di=0  dislope=0.4359  flat=0.31  load=0.06707  penalty=0  total J=3.61463  n_nan=0  DI source=balloon", "run OK: seed J=3.61463, 3836 dofs, solve 30.7 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185520Z-verify-fec2a6"]}
{"id": "cd11v__osse_morph", "start": "2026-11-20T18:56:12Z", "end": "2026-11-20T18:57:10Z", "seconds": 57.938, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185618Z-verify-f4c824", "evals_ndjson": 1, "best_J": 3.6645043873327854, "vram_baseline_mb": 809.0, "vram_after_mb": 856.0, "note": "ok; peak 1215 MiB; stop reason: ok; last output: run OK: seed J=3.6645, 3486 dofs, solve 32.2 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185618Z-verify-f4c824", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 1, "rows_window": 1, "valid_rows_window": 1, "best_J_window": 3.6645043873327854, "stop_reason": "ok", "log_tail": ["  terms (raw): cov=0  rip=0.2128  di=0  dislope=0.5949  flat=0.2235  load=0.1791  penalty=0  total J=3.6645  n_nan=0  DI source=balloon", "run OK: seed J=3.6645, 3486 dofs, solve 32.2 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185618Z-verify-f4c824"]}
{"id": "cd11v__ath_core_petal", "start": "2026-11-20T18:57:11Z", "end": "2026-11-20T18:58:26Z", "seconds": 74.234, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185717Z-verify-7fb1b5", "evals_ndjson": 1, "best_J": 4.443920915759051, "vram_baseline_mb": 830.0, "vram_after_mb": 780.0, "note": "ok; peak 1243 MiB; stop reason: ok; last output: run OK: seed J=4.44392, 4584 dofs, solve 44.1 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185717Z-verify-7fb1b5", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 1, "rows_window": 1, "valid_rows_window": 1, "best_J_window": 4.443920915759051, "stop_reason": "ok", "log_tail": ["  terms (raw): cov=0  rip=0.2703  di=0  dislope=0.7975  flat=0.3706  load=0.2795  penalty=0  total J=4.44392  n_nan=0  DI source=balloon", "run OK: seed J=4.44392, 4584 dofs, solve 44.1 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185717Z-verify-7fb1b5"]}
{"id": "cd11v__crowe_x_osse_cd", "start": "2026-11-20T18:58:27Z", "end": "2026-11-20T18:59:27Z", "seconds": 60.234, "exit_code": 0, "run_dir": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185832Z-verify-e5de4a", "evals_ndjson": 1, "best_J": 4.993881286003633, "vram_baseline_mb": 780.0, "vram_after_mb": 771.0, "note": "ok; peak 1099 MiB; stop reason: ok; last output: run OK: seed J=4.99388, 4487 dofs, solve 36.7 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185832Z-verify-e5de4a", "lane": "gpu", "backend": null, "status": "ok", "attempts": 1, "rows_before": 0, "rows_after": 1, "rows_window": 1, "valid_rows_window": 1, "best_J_window": 4.993881286003633, "stop_reason": "ok", "log_tail": ["  terms (raw): cov=0  rip=0.1053  di=0  dislope=0.1978  flat=0.876  load=2.728  penalty=0  total J=4.99388  n_nan=0  DI source=balloon", "run OK: seed J=4.99388, 4487 dofs, solve 36.7 s; output C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\20261120T185832Z-verify-e5de4a"]}
```

One job log line differs in whitespace by design and is quoted from
`runs/nights/cd_v11_verify_and_expand_2026-11-20/cd11v__crowe_x_osse_cd.log` (there is a blank
line between `HORNLAB_BEAT_WORKER_DIR` and `terms (raw)`; it is elided in the block above, and the
verbatim job log is reproduced below):

```
=== job cd11v__crowe_x_osse_cd start 2026-11-20T18:58:27Z timeout=1800s
=== argv: .venv/Scripts/hornlab-search.exe run --config examples/typologies/cd_v11_verify_2026-11-20/cd11v__crowe_x_osse_cd.yaml --mode verify
=== HORNLAB_BEAT_WORKER_DIR: C:\Users\hunte\Hrns\hornlab-search\runs\lanes\gpu\workers

  terms (raw): cov=0  rip=0.1053  di=0  dislope=0.1978  flat=0.876  load=2.728  penalty=0  total J=4.99388  n_nan=0  DI source=balloon
run OK: seed J=4.99388, 4487 dofs, solve 36.7 s; output C:\Users\hunte\Hrns\hornlab-search\runs\20261120T185832Z-verify-e5de4a
=== job cd11v__crowe_x_osse_cd end 2026-11-20T18:59:27Z exit=0
```

Per-job VRAM seen in the job logs (baseline → peak → after): ext 913→1247→841 MiB; fold
884→1045→809; morph 809→1215→856; ath 830→1243→780; crowe 780→1099→771.

## Verify results (measured, `runs/<run>/best.json`)

All five: `penalty=0`, `n_nan=0`, `di_source=balloon`, `cd_status_code=0` (balloon). Verify J is
comparable **only within this five-job verify-grid group**.

| # | lane | run dir | seed hash | verify J | dofs | solve s |
|---|---|---|---|---|---|---|
| 1 | ext_throat_hvlaw | `20261120T185416Z-verify-9d392f` | `e85cdd7c61f6` | 3.3405686204251346 | 4259 | 36.9 |
| 2 | osse_fold_warm | `20261120T185520Z-verify-fec2a6` | `68001408e339` | 3.6146314312259817 | 3836 | 30.7 |
| 3 | osse_morph | `20261120T185618Z-verify-f4c824` | `0636d3f22d5c` | 3.6645043873327854 | 3486 | 32.2 |
| 4 | ath_core_petal | `20261120T185717Z-verify-7fb1b5` | `2683984c802c` | 4.443920915759051 | 4584 | 44.1 |
| 5 | crowe_x_osse_cd | `20261120T185832Z-verify-e5de4a` | `4140768780f0` | 4.993881286003633 | 4487 | 36.7 |

## CD matrix, physical units (verify grid)

`terms` stores each CD value normalised by its tolerance; the physical values below are
`cd_lw*1.5`, `cd_di_std*1.0`, `NACC = 1 - cd_nacc*0.02`, `offaxis*1.0`; `cd_omega_2pi` and
`cd_status_code` are report-only (weight 0). `cov` and `load` are the objective terms (cov
normalised by 3.0, load by 0.3; shown as terms). Every cell is from the lane's `best.json`.

| lane | LW dB (cd_lw*1.5) | DI std dB | NACC | off-axis dB | Omega/2pi | status | cov term | load term |
|---|---|---|---|---|---|---|---|---|
| ext_throat_hvlaw | 0.617690 | 0.654553 | 0.989481 | 0.640736 | 0.598212 | 0 balloon | 0.004707 | 0.000000 |
| osse_fold_warm | 0.430080 | 0.629436 | 0.990159 | 1.493416 | 0.592223 | 0 balloon | 0.023598 | 0.067072 |
| osse_morph | 0.339168 | 0.771270 | 0.991309 | 1.394183 | 0.562704 | 0 balloon | 0.037706 | 0.179087 |
| ath_core_petal | 0.357107 | 0.908084 | 0.992281 | 1.544309 | 0.574137 | 0 balloon | 0.103207 | 0.279468 |
| crowe_x_osse_cd | 0.317803 | 0.461760 | 0.995392 | 0.419403 | 0.754742 | 0 balloon | 0.006983 | 2.728388 |

Additional verify-grid scalars from `designs/*/metrics.json`: mean H/V beamwidth
(ext 74.22/69.52, fold 69.72/67.24, morph 69.37/67.99, ath 65.35/64.84, crowe 76.25/71.50) deg;
DI slope 3.69/4.19/4.68/5.28/3.39 dB/dec; `z_mean_band` 1.015/1.036/1.010/0.973/0.810.
The crowe lane's `load` term 2.728 is consistent with its sub-unity `z_mean_band` 0.810.

## Screen completion J next to each (context ONLY)

Screen J is the completion-night `best.json` of the run each verify config replays. Screen and
verify use **different grids** (screen: 512 balloon points / 12 frequencies, `n_in_band=16`;
verify: 1024 balloon points / 25–29 frequencies, `n_in_band=27`). These are not equal and are
never pooled or ranked across grids.

| lane | screen source run | screen J | verify J |
|---|---|---|---|
| ext_throat_hvlaw | `20261120T075520Z-screen-a342b2` | 3.294012517840451 | 3.3405686204251346 |
| osse_fold_warm | `20261120T072543Z-screen-a8074a` | 3.6930357808926613 | 3.6146314312259817 |
| osse_morph | `20261120T074140Z-screen-a65a29` | 3.752547573829025 | 3.6645043873327854 |
| ath_core_petal | `20261120T090536Z-screen-6e83a9` | 4.2315762580143925 | 4.443920915759051 |
| crowe_x_osse_cd | `20261120T084006Z-screen-fc4e18` | 4.996463749003073 | 4.993881286003633 |

## Does the screen ordering survive verify?

Screen completion ordering (best → worst): ext_throat_hvlaw (3.2940) < osse_fold_warm (3.6930) <
osse_morph (3.7525) < ath_core_petal (4.2316) < crowe_x_osse_cd (4.9965).

Verify ordering: ext_throat_hvlaw (3.3406) < osse_fold_warm (3.6146) < osse_morph (3.6645) <
ath_core_petal (4.4439) < crowe_x_osse_cd (4.9939).

**Verdict: yes — the screen winner survives verify.** The order is identical on the verify grid,
and `e85cdd7c61f6` (ext_throat_hvlaw) is still the best of the five. The verify J is not a
rescaled screen J: the gap moves by −0.088 to +0.212 across the group, and crowe is essentially
unchanged (−0.0026).

## CD metric changes (screen → verify, physical units)

| lane | LW dB | DI std dB | NACC | off-axis dB | Omega/2pi | load term |
|---|---|---|---|---|---|---|
| ext_throat_hvlaw | 0.7308 → 0.6177 | 0.6130 → 0.6546 | 0.99022 → 0.98948 | 0.5855 → 0.6407 | 0.6039 → 0.5982 | 0 → 0 |
| osse_fold_warm | 0.4494 → 0.4301 | 0.6166 → 0.6294 | 0.99106 → 0.99016 | 1.6439 → 1.4934 | 0.5795 → 0.5922 | 0 → 0.0671 |
| osse_morph | 0.3902 → 0.3392 | 0.7626 → 0.7713 | 0.99181 → 0.99131 | 1.6142 → 1.3942 | 0.5430 → 0.5627 | 0 → 0.1791 |
| ath_core_petal | 0.4172 → 0.3571 | 0.8710 → 0.9081 | 0.99280 → 0.99228 | 1.6651 → 1.5443 | 0.5635 → 0.5741 | 0 → 0.2795 |
| crowe_x_osse_cd | 0.3460 → 0.3178 | 0.4253 → 0.4618 | 0.99593 → 0.99539 | 0.5429 → 0.4194 | 0.7249 → 0.7547 | 2.6446 → 2.7284 |

No CD metric flips classification: all five remain `balloon` (`cd_status_code=0`), NACC stays
≈0.989–0.995, and Omega/2pi stays 0.56–0.75. The material moves are the off-axis smoothness
(fold/morph/ath/crowe improve by 0.12–0.22 dB; ext worsens by 0.055 dB) and the `load` term,
which is 0 on the screen grid for four lanes; on verify it becomes 0.067/0.179/0.279 for
fold/morph/ath while ext stays 0, and crowe rises 2.645→2.728 — a grid effect in how many
below-f0 / loaded frequencies are measured, not a design change.

## Caveats

- **Screen ≠ verify.** The two grids differ in frequency set, balloon points and `n_in_band`;
  the J values above are reported side by side only for ordering context. Never call a screen J
  equal to its verify J, never average or pool them.
- **No cross-version ranking.** All five are objective v11 and the same brief; J here is not
  comparable to v7/v9/v10 or to any other brief. The expansion lanes in
  `docs/evidence/expand_2026-11-20/COMPLETION.md` are v10-identity compact400 lanes and must not
  be ranked against these.
- **No rescore.** Every verify row is a fresh single evaluation (`eval_no=0`, `stats.evaluations=1`);
  no stored screen row was rescaled or reused.
- Numbers were read from `best.json`, `run.json`, `summary.jsonl` and the job/queue logs after
  each job's `exit=0`; every quoted block above is byte-checked against its source file.
