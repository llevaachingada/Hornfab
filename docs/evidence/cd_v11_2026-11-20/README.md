Completion run: 7 partial lanes rerun to 50 valid + biradial 50/50 → see COMPLETION.md (2026-11-20).

# Objective-v11 CD matrix — 8-lane night run (2026-11-20)

**Scope:** the eight objective-v11 CD lanes appended to the live night
`runs/nights/fable_expand_2026-11-19.yaml`, run one at a time on the single GPU after the
night's sixteen `x_*` jobs. This document reports the CD metrics only; it does not re-rank
families across objective versions and does not re-score any stored response.

**Machine:** RTX 4060 Laptop 8 GB, i7-14650HX, Windows 11 (numbers in `TOOLCHAIN.md`).
**Built:** 2026-11-20, from the night's own logs and run dirs, after the runner exited.

**Status: 1 of 8 lanes is complete; 7 are partial.** Seven lanes were stopped by the night
watchdog before their 50-valid-eval budget; only `cd11__biradial_es` reached `50 valid of 50
budget`. Nothing here is a clean 50-eval matrix, and the partial lanes are never presented as
complete.

---

## 1. Queue and runner timeline (verbatim, decoded)

`runs/nights/queue_expand.log` (UTF-8, not UTF-16). The queue log carries no per-job lines; the
per-job START/END lines are in the night runner's own log, `runs/overnight/queue_fable_expand_2026-11-19.log`.

```
2026-11-19T23:27:37 queue start (pid 63028): fable_expand_2026-11-19; cutoff 23:59; wait pid 0
2026-11-19T23:27:37 starting fable_expand_2026-11-19
2026-11-20T02:05:53 finished fable_expand_2026-11-19 (exit 1)
2026-11-20T02:05:53 queue done; keep-awake released
```

The live-reload that added the CD block (runner log; the order list is one long line and is
elided at `...` after the first 16 entries):

```
=== 2026-11-20T00:22:17 RELOAD night file changed; order now: x_di_morph, x_di_fold, x_di_twinray, x_di_petal, x_di_tri_v9, x_di_tri_v8, x_s2b_morph, x_s2b_fold, x_s2b_twinray, x_s2b_petal, x_s2b_ext, x_s2c_morph, x_s2c_fold, x_s2c_twinray, x_r3_b3_dense_epw6, x_r3_b3_dense_epw9, cd11__osse_fold_warm, ...
```

The CD block, exactly as the runner logged it:

```
=== 2026-11-20T00:41:00 START cd11__osse_fold_warm : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__osse_fold_warm.yaml --budget 50 --mode screen
=== 2026-11-20T00:53:34 END cd11__osse_fold_warm exit 75
=== 2026-11-20T00:53:34 START cd11__osse_morph : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__osse_morph.yaml --budget 50 --mode screen
=== 2026-11-20T01:07:08 END cd11__osse_morph exit 75
=== 2026-11-20T01:07:08 START cd11__ext_throat_hvlaw : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__ext_throat_hvlaw.yaml --budget 50 --mode screen
=== 2026-11-20T01:14:11 END cd11__ext_throat_hvlaw exit 75
=== 2026-11-20T01:14:11 START cd11__ath_tritonia_v9 : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__ath_tritonia_v9.yaml --budget 50 --mode screen
=== 2026-11-20T01:26:45 END cd11__ath_tritonia_v9 exit 75
=== 2026-11-20T01:26:45 START cd11__crowe_x_osse_cd : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__crowe_x_osse_cd.yaml --budget 50 --mode screen
=== 2026-11-20T01:33:18 END cd11__crowe_x_osse_cd exit 75
=== 2026-11-20T01:33:18 START cd11__klangfilm_b3_soft : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__klangfilm_b3_soft.yaml --budget 50 --mode screen
=== 2026-11-20T01:38:20 END cd11__klangfilm_b3_soft exit 75
=== 2026-11-20T01:38:20 START cd11__ath_core_petal : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__ath_core_petal.yaml --budget 50 --mode screen
=== 2026-11-20T01:43:23 END cd11__ath_core_petal exit 75
=== 2026-11-20T01:43:23 START cd11__biradial_es : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_2026-11-20/cd11__biradial_es.yaml --budget 50 --mode screen
=== 2026-11-20T01:59:40 END cd11__biradial_es exit 0
```

Between the `cd11__osse_fold_warm` END and the `cd11__osse_morph` START the log carries a second
`RELOAD night file changed; order now: ...` line (the `x_r3_b3_dense2_*` pair was appended after
the CD block); it is elided above and does not change the CD order. After `cd11__biradial_es` the
runner started and finished `x_r3_b3_dense2_epw6` (exit 0) and `x_r3_b3_dense2_epw9` (exit 0), then
logged `QUEUE DONE` at `2026-11-20T02:05:52`. The queue-level `exit 1` is the night's overall
status (15 watchdog-stopped `x_*`/CD jobs); the eight CD jobs' own exits are in the table below.
When monitoring ended, runner pid 25580 and its parent wrapper 47768 had exited; all eight CD rows were already present.

## 2. Per-job outcome and decoded evidence

Run dirs are under `runs/`. `valid new` counts successful evaluations that were not cache hits; the
seed row (`n=0`) is a cache hit in all eight runs, so it is excluded from the budget count but used
for the seed column in §4. `cached` counts the re-used stored responses (the seed plus any hit found
during the search).

| lane | status | exit | run dir | valid new / rows (cached) | refused (kind) | stop reason |
|---|---|---|---:|---|---:|---|
| `cd11__osse_fold_warm` | watchdog | 75 | `20261120T054102Z-screen-9d939b` | 30 / 31 (1) | 0 | watchdog: bound-pinned `az_fold_h_deg` |
| `cd11__osse_morph` | watchdog | 75 | `20261120T055336Z-screen-e23136` | 39 / 40 (1) | 0 | watchdog: bound-pinned `q` |
| `cd11__ext_throat_hvlaw` | watchdog | 75 | `20261120T060710Z-screen-6d6b36` | 20 / 34 (10) | 4 (`invalid_envelope`) | watchdog: bound-pinned `az_a_cos_pow` |
| `cd11__ath_tritonia_v9` | watchdog | 75 | `20261120T061413Z-screen-5ad3a1` | 20 / 31 (1) | 10 (`invalid_envelope`) | watchdog: refusal rate 33% |
| `cd11__crowe_x_osse_cd` | watchdog | 75 | `20261120T062647Z-screen-9cd14e` | 17 / 26 (1) | 8 (`invalid_envelope`) | watchdog: refusal rate 31% |
| `cd11__klangfilm_b3_soft` | watchdog | 75 | `20261120T063319Z-screen-94ab7b` | 21 / 33 (11) | 1 (`invalid_geometry`) | watchdog: bound-pinned `g_beak_v_projection_mm` |
| `cd11__ath_core_petal` | watchdog | 75 | `20261120T063822Z-screen-a5a822` | 12 / 26 (1) | 13 (12 `invalid_envelope`, 1 `invalid_geometry`) | watchdog: refusal rate 50% |
| `cd11__biradial_es` | ok | 0 | `20261120T064325Z-screen-97c2af` | 50 / 61 (11) | 0 | budget |

Each run's own log (`runs/nights/fable_expand_2026-11-19/<id>.log`, UTF-8) carries the watchdog
verdict. Quoting the stop and end lines (start lines are in §1; long blank runs compressed by the
logger are not quoted):

`cd11__osse_fold_warm.log`
```
=== WATCHDOG bound-pinned: 3/6 of the top 6 sit at the high limit of az_fold_h_deg [-15, 0] - widen the box and requeue; stopping job cd11__osse_fold_warm (pid 23944)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T054102Z-screen-9d939b)

=== job cd11__osse_fold_warm stopped by watchdog 2026-11-20T05:53:34Z exit=75
VRAM peak=1115 MiB after=633 MiB
```

`cd11__osse_morph.log`
```
=== WATCHDOG bound-pinned: 3/6 of the top 6 sit at the high limit of q [0.9, 1] - widen the box and requeue; stopping job cd11__osse_morph (pid 37552)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T055336Z-screen-e23136)
=== job cd11__osse_morph stopped by watchdog 2026-11-20T06:07:08Z exit=75
VRAM peak=924 MiB after=637 MiB
```

`cd11__ext_throat_hvlaw.log`
```
=== WATCHDOG bound-pinned: 3/6 of the top 6 sit at the low limit of az_a_cos_pow [1, 6] - widen the box and requeue; stopping job cd11__ext_throat_hvlaw (pid 57360)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T060710Z-screen-6d6b36)
=== job cd11__ext_throat_hvlaw stopped by watchdog 2026-11-20T06:14:10Z exit=75
VRAM peak=1045 MiB after=630 MiB
```

`cd11__ath_tritonia_v9.log`
```
=== WATCHDOG refusal rate 33% over the last 30 attempts > 30%; stopping job cd11__ath_tritonia_v9 (pid 45668)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T061413Z-screen-5ad3a1)
=== job cd11__ath_tritonia_v9 stopped by watchdog 2026-11-20T06:26:44Z exit=75
VRAM peak=1072 MiB after=617 MiB
```

`cd11__crowe_x_osse_cd.log`
```
=== WATCHDOG refusal rate 31% over the last 26 attempts > 30%; stopping job cd11__crowe_x_osse_cd (pid 39028)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T062647Z-screen-9cd14e)
=== job cd11__crowe_x_osse_cd stopped by watchdog 2026-11-20T06:33:17Z exit=75
VRAM peak=936 MiB after=617 MiB
```

`cd11__klangfilm_b3_soft.log`
```
=== WATCHDOG bound-pinned: 4/6 of the top 6 sit at the low limit of g_beak_v_projection_mm [0, 5] - widen the box and requeue; stopping job cd11__klangfilm_b3_soft (pid 26552)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T063319Z-screen-94ab7b)
=== job cd11__klangfilm_b3_soft stopped by watchdog 2026-11-20T06:38:20Z exit=75
VRAM peak=904 MiB after=617 MiB
```

`cd11__ath_core_petal.log` (its 11 mesher `outer wall clearance` warnings and one
`interpolating surface fit` fallback warning are elided; the watchdog line is the byte that matters)
```
=== WATCHDOG refusal rate 50% over the last 26 attempts > 30%; stopping job cd11__ath_core_petal (pid 62968)
search ABORTED: watchdog (partial results in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T063822Z-screen-a5a822)
=== job cd11__ath_core_petal stopped by watchdog 2026-11-20T06:43:22Z exit=75
VRAM peak=1256 MiB after=617 MiB
```

`cd11__biradial_es.log` (the only complete lane)
```
  evaluations 61 (50 new, 11 cached), failures {}, GPU 693.4 s, 19.0 s/candidate, 189/h, projected 1,000 = 5.3 h, 10,000 = 52.8 h
  budget counts: valid, 50 valid of 50 budget, 0 refusals free, attempts 50/200
  seed J=8.40614  best J=7.70811 (improved on the seed); stop: budget
search OK: 61 rows in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T064325Z-screen-97c2af\search.ndjson; best in C:\Users\hunte\Hrns\hornlab-search\runs\20261120T064325Z-screen-97c2af\best.json; report with: hornlab-search report C:\Users\hunte\Hrns\hornlab-search\runs\20261120T064325Z-screen-97c2af
=== job cd11__biradial_es end 2026-11-20T06:59:38Z exit=0
VRAM peak=904 MiB after=617 MiB
```

Pre-hygiene: seven of the eight logs contain a stale-lock takeover from a dead pid, e.g.
`STALE LOCK TAKEN OVER: removed .gpu.lock (the gpu lane's lock) whose recorded holder pid 2100 is gone`
(`cd11__biradial_es.log`); `cd11__osse_fold_warm.log` is the only one without it. Every job started
from `gpu-clean: no project Julia/BEAT processes found`, baseline 617–637 MiB, and `HORNLAB_GPU_LOCK:
refuse`. `cd11__biradial_es`'s post-hygiene also reports `gpu-clean: killed 2 process(es): [9156, 62060]`.

`run.json` state: the seven stopped dirs keep `"status": "running"` (the run was aborted, not
finalised); `20261120T064325Z-screen-97c2af` has `"status": "finished"`. All eight are
`objective_version: 11`, config SHA-256 differs per lane
(`b8a895497b43`, `f93a709e3bc3`, `cf2eb9344284`, `82bfd801a5af`, `05d9fbf7c59a`, `9bbe52128fe9`,
`75ce79cdb63c`, `0b7db3be47fd` in lane order), same brief
`examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml`.

## 3. CD matrix — best design per lane (v11 only, [measured])

Raw CD values reconstructed exactly from the stored normalised terms in `best.json` using the
v11 brief's tolerances (`objective.cd.lw.tolerance_db: 1.5`, `di_std.tolerance_db: 1.0`,
`nacc.tolerance: 0.02`, `offaxis.tolerance_db: 1.0`; `scalar_v11.py::_norm_cd/_norm_nacc`):
`cd_lw_db = cd_lw*1.5`, `cd_di_std_db = cd_di_std*1.0`, `NACC = 1 - cd_nacc*0.02`,
`offaxis_db = offaxis_smooth*1.0`. `cd_omega_2pi` and `cd_status_code` are stored raw. The
inversion is arithmetic on the stored terms; no response was re-solved or re-scored.

| lane (mesher family) | status / exit | valid new / rows (cached) | best J | design hash | CD LW dB | Omega/2pi | sigma_DI dB | NACC | offaxis dB | cd_status | cov_profile | load |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---:|---:|
| `cd11__osse_fold_warm` (OSSE) | watchdog / 75 | 30 / 31 (1) | 4.2236 | `58f158e85aa1` | 0.539 | 0.596 | 0.718 | 0.9905 | 1.722 | balloon (0) | 0.0193 | 0.1240 |
| `cd11__osse_morph` (OSSE) | watchdog / 75 | 39 / 40 (1) | 3.9999 | `737be630b12e` | 0.434 | 0.439 | 0.847 | 0.9883 | 1.549 | balloon (0) | 0.0517 | 0.0000 |
| `cd11__ext_throat_hvlaw` (OSSE) | watchdog / 75 | 20 / 34 (10) | 3.8056 | `6ff2d4a3bef0` | 0.924 | 0.647 | 0.601 | 0.9883 | 0.788 | balloon (0) | 0.0080 | 0.0000 |
| `cd11__ath_tritonia_v9` (OSSE) | watchdog / 75 | 20 / 31 (1) | 5.5944 | `ed66bfa3ab71` | 0.496 | 0.629 | 0.923 | 0.9913 | 1.846 | balloon (0) | 0.0322 | 0.9524 |
| `cd11__crowe_x_osse_cd` (FREEFORM) | watchdog / 75 | 17 / 26 (1) | 5.2952 | `4be8fdb4b00d` | 0.453 | 0.740 | 0.423 | 0.9945 | 0.567 | balloon (0) | 0.0075 | 2.7354 |
| `cd11__klangfilm_b3_soft` (FREEFORM) | watchdog / 75 | 21 / 33 (11) | 7.1831 | `3bfcc80b743a` | 0.843 | 0.472 | 1.249 | 0.9734 | 2.434 | balloon (0) | 0.1500 | 0.0000 |
| `cd11__ath_core_petal` (OSSE) | watchdog / 75 | 12 / 26 (1) | 4.9349 | `928733968160` | 0.454 | 0.489 | 1.084 | 0.9902 | 1.952 | balloon (0) | 0.0536 | 0.0000 |
| `cd11__biradial_es` (FREEFORM) | ok / 0 | 50 / 61 (11) | 7.7081 | `69f07277dc3c` | 0.559 | 0.652 | 0.784 | 0.9843 | 1.288 | balloon (0) | 0.0153 | 3.3143 |

All valid evaluations in all eight dirs are `cd_status_code 0` (balloon), with zero `NAN_TERM_FILL`
terms and zero unmeasurable `cd_omega_2pi` (`-1.0`); 246 of 246 valid rows checked.

### 3.1 Median over the new valid evals

Median of each raw CD metric over the run's **new** valid evaluations (cache hits and the cached
seed excluded), i.e. the evaluations that counted toward the 50-valid budget. N is shown because
seven lanes never reached 50.

| lane | median J | median LW dB | median Omega/2pi | median sigma_DI dB | median NACC | median offaxis dB | N (new valid) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cd11__osse_fold_warm` | 4.9581 | 0.649 | 0.589 | 0.854 | 0.9891 | 2.054 | 30 |
| `cd11__osse_morph` | 5.9772 | 0.670 | 0.519 | 1.116 | 0.9867 | 2.124 | 39 |
| `cd11__ext_throat_hvlaw` | 4.8476 | 0.775 | 0.558 | 0.911 | 0.9860 | 1.173 | 20 |
| `cd11__ath_tritonia_v9` | 5.9828 | 0.581 | 0.662 | 0.959 | 0.9909 | 1.698 | 20 |
| `cd11__crowe_x_osse_cd` | 5.5525 | 0.510 | 0.700 | 0.567 | 0.9933 | 0.681 | 17 |
| `cd11__klangfilm_b3_soft` | 8.0408 | 0.983 | 0.468 | 1.341 | 0.9717 | 2.706 | 21 |
| `cd11__ath_core_petal` | 6.1701 | 0.493 | 0.442 | 1.432 | 0.9848 | 1.986 | 12 |
| `cd11__biradial_es` | 8.3050 | 0.715 | 0.617 | 0.883 | 0.9831 | 1.310 | 50 |

### 3.2 Leaderboard by best J (within v11 only — not equal budget)

`ext_throat` (20 new valid) and `osse_morph` (39) are best-so-far at stop, not converged results;
`klangfilm`'s best is eval `n=1` and `fold_warm`'s is `n=6`. Treat this as ordering, not ranking.

| # | lane | best J | new valid evals |
|---|---|---:|---:|
| 1 | `cd11__ext_throat_hvlaw` | 3.8056 | 20 |
| 2 | `cd11__osse_morph` | 3.9999 | 39 |
| 3 | `cd11__osse_fold_warm` | 4.2236 | 30 |
| 4 | `cd11__ath_core_petal` | 4.9349 | 12 |
| 5 | `cd11__crowe_x_osse_cd` | 5.2952 | 17 |
| 6 | `cd11__ath_tritonia_v9` | 5.5944 | 20 |
| 7 | `cd11__klangfilm_b3_soft` | 7.1831 | 21 |
| 8 | `cd11__biradial_es` | 7.7081 | 50 |

## 4. Seed vs best (raw CD terms)

Seed = the stored `n=0` row (a cache hit in all eight runs; its stored response was re-used, not
re-solved). Delta = seed − best, so a positive number is an improvement.

| lane | seed J | seed LW dB | seed Omega/2pi | seed sigma_DI dB | seed NACC | seed offaxis dB | dJ | d LW | d sigma_DI | d NACC | d offaxis | seed hash | best eval n |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `cd11__osse_fold_warm` | 4.8444 | 0.684 | 0.605 | 0.722 | 0.9898 | 2.024 | +0.6208 | +0.145 | +0.004 | -0.00077 | +0.302 | `8544e97bc940` | 6 |
| `cd11__osse_morph` | 5.9950 | 0.657 | 0.522 | 1.264 | 0.9874 | 2.254 | +1.9952 | +0.223 | +0.416 | -0.00089 | +0.704 | `9992af67096b` | 30 |
| `cd11__ext_throat_hvlaw` | 4.5336 | 0.623 | 0.556 | 0.936 | 0.9861 | 1.047 | +0.7280 | -0.301 | +0.335 | -0.00226 | +0.259 | `64efc34b7396` | 26 |
| `cd11__ath_tritonia_v9` | 6.4673 | 0.611 | 0.691 | 1.009 | 0.9893 | 1.587 | +0.8730 | +0.115 | +0.086 | -0.00199 | -0.259 | `c535bbf5e771` | 16 |
| `cd11__crowe_x_osse_cd` | 5.4380 | 0.516 | 0.708 | 0.485 | 0.9931 | 0.614 | +0.1428 | +0.063 | +0.062 | -0.00133 | +0.047 | `9b5428e6dec8` | 25 |
| `cd11__klangfilm_b3_soft` | 7.4975 | 0.885 | 0.475 | 1.275 | 0.9730 | 2.586 | +0.3144 | +0.043 | +0.026 | -0.00038 | +0.152 | `3545b3e078ac` | 1 |
| `cd11__ath_core_petal` | 5.2995 | 0.511 | 0.485 | 1.172 | 0.9885 | 1.931 | +0.3646 | +0.057 | +0.087 | -0.00168 | -0.020 | `c73a8ae29ccb` | 12 |
| `cd11__biradial_es` | 8.4061 | 0.636 | 0.601 | 0.908 | 0.9830 | 1.666 | +0.6980 | +0.077 | +0.124 | -0.00133 | +0.378 | `7b0a1988625d` | 59 |

Every lane improved J on its seed. The one CD regression worth noting is `ext_throat_hvlaw`, whose
LW term worsened by 0.301 dB while its J improved; `tritonia` and `petal` traded a slightly worse
offaxis term for J. These are within-run, same-identity comparisons only.

## 5. The two runnability substitutions (not results)

The plan named eight home-landscape sources. Two could not run as stock searches because their
rows types are not in the stock generator, so the lane was filled with the runnable current
construction. Quoting `docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md` §4.1 (verbatim):

```
The first dry-run of the queue reported `free-dimension check skipped (GeometryInvalidError: ...
unknown rows type 'rosse_rect' / 'klangfilm_lame')`. `design/generators/grid.py::ROWS_TYPES`
(line 140) contains only the stock rows types; `rosse_rect` is a GUI-preview bridge
(`tools/geometry/gui_preview.py`), and the legacy `klangfilm_lame` rows type is superseded by
`klangfilm_lame_hv_core` in the package generator. Running either as a stock search would refuse
the seed. The two lanes were replaced with stock-runnable CD constructions (`hl__ath_tritonia_landscape_v9`
and the package `klangfilm_lame_hv_core` B3 soft). This is a runnability substitution, not a
result: the paper's CD matrix is unchanged.
```

1. **`cd11__ath_tritonia_v9` replaces the bridge-only R-OSSE-rect source.** The R-OSSE-rect
   `rosse_rect` rows type exists only in the GUI preview bridge, so a stock search refuses the seed.
2. **`cd11__klangfilm_b3_soft` (Klangfilm LAME HV core, B3 soft) replaces the legacy
   `klangfilm_lame` rows type.** The legacy type is superseded by `klangfilm_lame_hv_core` in the
   package generator; this lane runs that shipped HV-core construction.

The research doc's seed-calibration rows for these two replaced families were measured from archived
SCOUT40 responses; the research doc states the substitutes "are measured from their own first 50-eval
runs, not assumed from these rows". With seven of eight lanes watchdog-stopped, this document is
that first measurement, and it is partial for both substitutes.

## 6. Caveats — read before quoting any number

1. **Partial jobs, never complete.** Seven lanes stopped by the watchdog before 50 valid evals
   (`30, 39, 20, 20, 17, 21, 12` new valid; see §3.1). Their `best J` is best-so-far, their medians
   are over fewer than 50 evals, and none of those seven reached its budget. Only `cd11__biradial_es`
   (`50 valid of 50 budget`) is a complete run. No partial lane is presented as complete.
2. **No pooled J, no cross-version rank.** These are objective-v11 numbers and are not comparable
   to v7/v9/v10 (the configs and `run.json` both record `objective_version: 11`, a new score
   identity with a new brief). The §3.2 ordering is within v11 and unequal-budget.
3. **CD-only comparison.** The delivered matrix is the six CD outputs plus `cov_profile`/`load`
   guards. J is reported as the v11 total, but no term-level attribution outside the CD set is
   claimed, and no family is re-ranked on non-CD terms. (The non-CD terms are present in each
   `best.json` for follow-up work; they are not analysed here.)
4. **Screen resolution.** All eight lanes ran `mode: screen` with `balloon_points_screen: 512`,
   `angle_count: 73`, `epw: 6.0`, `distance_m: 10.0`, `dof_cap_screen: 24000`. The CD metrics are
   screen-resolution numbers; no verify-resolution re-run was done, and none is claimed.
5. **No rescore was run.** Every number here comes from these eight fresh runs. No stored
   v7/v9/v10 response was re-scored to build this matrix, and the two substituted lanes have no
   pre-existing CD row to compare against.
6. **Inversion, not measurement.** The four weighted raw CD values are arithmetic inversions of the
   stored normalised terms (tolerances from the v11 brief, verified in
   `objective/scalar_v11.py`); only `cd_omega_2pi`/`cd_status_code` are stored raw. An inversion
   cannot recover precision the normalised float lost, though the terms are stored at full double
   precision so the round-trip error is at the last bit.
7. **Measurement environment.** The nights run one GPU job at a time and every job's pre-hygiene
   cleared the lane. One monitor-lane observation (not from a run log): a second Julia host from a
   different project (`C:\Users\hunte\Github\boundary-lab`, `blab.exe` → `julia`, pid 42412)
   appeared at `2026-11-20T05:15:01Z` and was gone by `06:58Z`; `nvidia-smi
   --query-compute-apps` at `05:17Z` listed no GPU allocation for it. Recorded as a hygiene note,
   not as a confirmed concurrent CUDA solve.
8. **The watchdog is the night's, not the lane's.** The verdicts (`bound-pinned` on
   `az_fold_h_deg`, `q`, `az_a_cos_pow`, `g_beak_v_projection_mm`; refusal rate > 30% on three
   lanes) say the search boxes were being pushed to a limit or refusing geometry — a design/box
   signal for a re-queue, not a solver failure. No job was re-run or rescued for this document.
9. **Queue exit code.** `queue_expand.log` ends `finished fable_expand_2026-11-19 (exit 1)`; that
   is the night status with 15 watchdog jobs, not an error in the CD block. All eight CD rows were
   written before the runner exited, and no row is missing.

## 7. Inputs

- Queue: `runs/nights/queue_expand.log`; night: `runs/nights/fable_expand_2026-11-19.yaml`;
  runner log: `runs/overnight/queue_fable_expand_2026-11-19.log`.
- Summary: `runs/nights/fable_expand_2026-11-19/summary.jsonl` (25 rows at stop; 8 `cd11__*`).
- Per-job logs: `runs/nights/fable_expand_2026-11-19/cd11__<lane>.log` (UTF-8, read as bytes).
- Run dirs (gitignored): the eight `runs/20261120T*-screen-*` dirs in §2, each with `best.json`,
  `search.ndjson`, `run.json`, `config.yaml`.
- Configs: `examples/typologies/cd_v11_2026-11-20/cd11__*.yaml`; brief:
  `examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml`.
- Substitution rationale: `docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md` §4.1.

Numbers in §3 and §4 were generated directly from `summary.jsonl`, each `best.json` and each
`search.ndjson` by a read-only script (no solver, no re-score); the quoted blocks in §1 and §2 were
byte-checked against the decoded source files.
