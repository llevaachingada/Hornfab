# Objective-v11 CD completion — 7 partial lanes rerun to 50 valid (2026-11-20)

**Scope:** the completion night `cd_v11_completion_2026-11-20`, which re-ran the seven
partial objective-v11 CD lanes from the first append night
(`runs/nights/fable_expand_2026-11-19`, see `README.md` in this folder). Each lane started
from its own partial-run `best.json` design, ran 50 new valid evaluations with the night
watchdog **off**, and the eighth lane (`cd11__biradial_es`) is the already-complete
50/50 first run, not rerun. This document reports the CD metrics only; it does not re-rank
families across objective versions and does not re-score any stored response.

**Machine:** RTX 4060 Laptop 8 GB, i7-14650HX, Windows 11 (numbers in `TOOLCHAIN.md`).
**Built:** 2026-11-20, from the completion night's own logs and run dirs, after the runner exited.

**Status: 8 of 8 lanes now have 50 valid new evals.** All seven completion lanes exited 0
with `50 valid of 50 budget`; `cd11__biradial_es` remains the first-run `50 valid of 50
budget` lane. No lane is below 50 valid. Nothing was rerun or rescued for this document.

---

## 1. Queue and runner timeline (decoded, verbatim)

Both files are UTF-8 (the queue log carries a BOM); every quoted block below was decoded and
byte-checked against its source. `runs/nights/queue_cd_v11_completion_2026-11-20.log`:

```
2026-11-20T02:25:41 queue start (pid 50224): cd_v11_completion_2026-11-20; cutoff 07:00; wait pid 0
2026-11-20T02:25:41 starting cd_v11_completion_2026-11-20
2026-11-20T04:24:02 finished cd_v11_completion_2026-11-20 (exit 0)
2026-11-20T04:24:02 queue done; keep-awake released
```

The per-job START/END lines are in the night runner's own log,
`runs/overnight/queue_cd_v11_completion_2026-11-20.log`:

```
=== 2026-11-20T02:25:42 START cd11c__osse_fold_warm : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__osse_fold_warm.yaml --budget 50 --mode screen
=== 2026-11-20T02:41:38 END cd11c__osse_fold_warm exit 0
=== 2026-11-20T02:41:38 START cd11c__osse_morph : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__osse_morph.yaml --budget 50 --mode screen
=== 2026-11-20T02:55:17 END cd11c__osse_morph exit 0
=== 2026-11-20T02:55:17 START cd11c__ext_throat_hvlaw : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__ext_throat_hvlaw.yaml --budget 50 --mode screen
=== 2026-11-20T03:12:24 END cd11c__ext_throat_hvlaw exit 0
=== 2026-11-20T03:12:24 START cd11c__ath_tritonia_v9 : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__ath_tritonia_v9.yaml --budget 50 --mode screen
=== 2026-11-20T03:40:04 END cd11c__ath_tritonia_v9 exit 0
=== 2026-11-20T03:40:04 START cd11c__crowe_x_osse_cd : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__crowe_x_osse_cd.yaml --budget 50 --mode screen
=== 2026-11-20T03:56:27 END cd11c__crowe_x_osse_cd exit 0
=== 2026-11-20T03:56:27 START cd11c__klangfilm_b3_soft : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__klangfilm_b3_soft.yaml --budget 50 --mode screen
=== 2026-11-20T04:05:34 END cd11c__klangfilm_b3_soft exit 0
=== 2026-11-20T04:05:34 START cd11c__ath_core_petal : C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\hornlab-search.exe search --config examples/typologies/cd_v11_completion_2026-11-20/cd11c__ath_core_petal.yaml --budget 50 --mode screen
=== 2026-11-20T04:24:01 END cd11c__ath_core_petal exit 0
=== 2026-11-20T04:24:01 QUEUE DONE
```

All seven jobs wrote their `summary.jsonl` row and exited 0; the queue exited 0. By the end of
this monitor pass the controller pid 50224 and both runner python processes were gone (checked with
`Get-Process -Id 50224` and `Get-CimInstance Win32_Process`), so the night is fully shut down.

## 2. Per-job outcome and decoded evidence

`valid new` is successful, non-cached evaluations counted toward the 50-valid budget; the seed row
(`n=0`) is a cache hit of the prior partial-run best in every completion lane, so it is counted as
`cached`, not toward the budget. `rows` is the `search.ndjson` line count. `refused` groups
`ok:false` attempts by `kind` (they are free under `budget_counts: valid`). VRAM is the pre-hygiene
baseline / run peak / post-hygiene value; every job started from `gpu-clean: no project Julia/BEAT
processes found`.

| lane | status / exit | run dir | valid new / rows | cached | refused (kind) | bounded keys | VRAM base/peak/after MiB |
|---|---|---|---:|---:|---|---:|---|
| `cd11c__osse_fold_warm` | ok / 0 | `20261120T072543Z-screen-a8074a` | 50 / 51 | 1 | 0 | 35 | 604 / 1145 / 687 |
| `cd11c__osse_morph` | ok / 0 | `20261120T074140Z-screen-a65a29` | 50 / 56 | 1 | 5 (`invalid_geometry`) | 31 | 687 / 1006 / 687 |
| `cd11c__ext_throat_hvlaw` | ok / 0 | `20261120T075520Z-screen-a342b2` | 50 / 90 | 1 | 39 (25 `invalid_envelope`, 14 `invalid_geometry`) | 33 | 687 / 1102 / 687 |
| `cd11c__ath_tritonia_v9` | ok / 0 | `20261120T081227Z-screen-05f20b` | 50 / 67 | 1 | 16 (`invalid_envelope`) | 30 | 687 / 1230 / 687 |
| `cd11c__crowe_x_osse_cd` | ok / 0 | `20261120T084006Z-screen-fc4e18` | 50 / 62 | 1 | 11 (`invalid_envelope`) | 15 | 687 / 1038 / 687 |
| `cd11c__klangfilm_b3_soft` | ok / 0 | `20261120T085629Z-screen-90752f` | 50 / 51 | 1 | 0 | 21 | 687 / 974 / 687 |
| `cd11c__ath_core_petal` | ok / 0 | `20261120T090536Z-screen-6e83a9` | 50 / 89 | 1 | 38 (33 `invalid_envelope`, 5 `invalid_geometry`) | 31 | 687 / 1230 / 687 |

The three decoded budget lines per completion lane (from `runs/nights/cd_v11_completion_2026-11-20/<id>.log`,
UTF-8) are quoted below; the `evaluations` line's counts are `(new, cached)` and every lane reports
`50 valid of 50 budget`:

`cd11c__osse_fold_warm.log`
```
  evaluations 51 (50 new, 1 cached), failures {}, GPU 785.2 s, 18.7 s/candidate, 192/h, projected 1,000 = 5.2 h, 10,000 = 52.0 h
  budget counts: valid, 50 valid of 50 budget, 0 refusals free, attempts 50/200
  seed J=4.22363  best J=3.69304 (improved on the seed); stop: budget
```

`cd11c__osse_morph.log`
```
  evaluations 56 (55 new, 1 cached), failures {'invalid_geometry': 5}, GPU 670.7 s, 14.5 s/candidate, 248/h, projected 1,000 = 4.0 h, 10,000 = 40.3 h
  budget counts: valid, 50 valid of 50 budget, 5 refusals free, attempts 55/200
  seed J=3.99987  best J=3.75255 (improved on the seed); stop: budget
```

`cd11c__ext_throat_hvlaw.log`
```
  evaluations 90 (89 new, 1 cached), failures {'invalid_envelope': 25, 'invalid_geometry': 14}, GPU 779.4 s, 11.3 s/candidate, 319/h, projected 1,000 = 3.1 h, 10,000 = 31.4 h
  budget counts: valid, 50 valid of 50 budget, 39 refusals free, attempts 89/300
  seed J=3.80561  best J=3.29401 (improved on the seed); stop: budget
```

`cd11c__ath_tritonia_v9.log`
```
  evaluations 67 (66 new, 1 cached), failures {'invalid_envelope': 16}, GPU 1496.7 s, 24.8 s/candidate, 145/h, projected 1,000 = 6.9 h, 10,000 = 68.9 h
  budget counts: valid, 50 valid of 50 budget, 16 refusals free, attempts 66/300
  seed J=5.59436  best J=5.18257 (improved on the seed); stop: budget
```

`cd11c__crowe_x_osse_cd.log`
```
  evaluations 62 (61 new, 1 cached), failures {'invalid_envelope': 11}, GPU 900.7 s, 15.6 s/candidate, 231/h, projected 1,000 = 4.3 h, 10,000 = 43.2 h
  budget counts: valid, 50 valid of 50 budget, 11 refusals free, attempts 61/300
  seed J=5.29515  best J=4.99646 (improved on the seed); stop: budget
```

`cd11c__klangfilm_b3_soft.log`
```
  evaluations 51 (50 new, 1 cached), failures {}, GPU 493.7 s, 10.5 s/candidate, 343/h, projected 1,000 = 2.9 h, 10,000 = 29.1 h
  budget counts: valid, 50 valid of 50 budget, 0 refusals free, attempts 50/300
  seed J=7.18309  best J=7.0484 (improved on the seed); stop: budget
```

`cd11c__ath_core_petal.log`
```
  evaluations 89 (88 new, 1 cached), failures {'invalid_envelope': 33, 'invalid_geometry': 5}, GPU 920.1 s, 12.3 s/candidate, 292/h, projected 1,000 = 3.4 h, 10,000 = 34.3 h
  budget counts: valid, 50 valid of 50 budget, 38 refusals free, attempts 88/300
  seed J=4.93493  best J=4.23158 (improved on the seed); stop: budget
```

Every completion `run.json` is `"status": "finished"`, `"stop_reason": "budget"`,
`"budget_counts": {"mode": "valid", "valid": 50}` and `objective_version: 11`; config SHAs are
`3aa9da76aa34`, `bc50183be98a`, `41d47de9848d`, `f6ce9bf0270a`, `27ab56e27e78`, `91cf5e02090b`,
`5405ad80709d` in the order above. Every job's post-hygiene reports
`gpu-clean: killed 2 process(es): [...]` and `gpu-clean: VRAM used 687 MiB`; the run peaks above
match each log's final `VRAM peak=... after=687 MiB` line.

The eighth (not rerun) row is the first-run `cd11c`-equivalent lane `cd11__biradial_es`,
`runs/20261120T064325Z-screen-97c2af`, `"status": "finished"`, exit 0,
`50 valid of 50 budget` (61 rows: 50 new, 11 cached, 0 refusals), best `69f07277dc3c` at `n=59`.
Its decoded log lines (from `runs/nights/fable_expand_2026-11-19/cd11__biradial_es.log`):

```
  evaluations 61 (50 new, 11 cached), failures {}, GPU 693.4 s, 19.0 s/candidate, 189/h, projected 1,000 = 5.3 h, 10,000 = 52.8 h
  budget counts: valid, 50 valid of 50 budget, 0 refusals free, attempts 50/200
  seed J=8.40614  best J=7.70811 (improved on the seed); stop: budget
```

## 3. CD matrix — best design per lane (v11 only, [measured])

Raw CD values reconstructed exactly from the stored normalised terms in `best.json` using the
v11 brief's tolerances (`objective.cd.lw.tolerance_db: 1.5`, `di_std.tolerance_db: 1.0`,
`nacc.tolerance: 0.02`, `offaxis.tolerance_db: 1.0`; `scalar_v11.py::_norm_cd/_norm_nacc`):
`cd_lw_db = cd_lw*1.5`, `cd_di_std_db = cd_di_std*1.0`, `NACC = 1 - cd_nacc*0.02`,
`offaxis_db = offaxis_smooth*1.0`. `cd_omega_2pi` and `cd_status_code` are stored raw. The
inversion is arithmetic on the stored terms; no response was re-solved or re-scored.

| lane (mesher family) | status / exit | valid new / rows (cached) | best J | design hash | CD LW dB | Omega/2pi | sigma_DI dB | NACC | offaxis dB | cd_status | best eval n |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---:|
| `cd11c__osse_fold_warm` (OSSE) | ok / 0 | 50 / 51 (1) | 3.6930 | `68001408e339` | 0.449 | 0.579 | 0.617 | 0.9911 | 1.644 | balloon (0) | 47 |
| `cd11c__osse_morph` (OSSE) | ok / 0 | 50 / 56 (1) | 3.7525 | `0636d3f22d5c` | 0.390 | 0.543 | 0.763 | 0.9918 | 1.614 | balloon (0) | 6 |
| `cd11c__ext_throat_hvlaw` (OSSE) | ok / 0 | 50 / 90 (1) | 3.2940 | `e85cdd7c61f6` | 0.731 | 0.604 | 0.613 | 0.9902 | 0.585 | balloon (0) | 79 |
| `cd11c__ath_tritonia_v9` (OSSE) | ok / 0 | 50 / 67 (1) | 5.1826 | `81d3b70fc9d8` | 0.599 | 0.603 | 0.540 | 0.9933 | 2.014 | balloon (0) | 54 |
| `cd11c__crowe_x_osse_cd` (FREEFORM) | ok / 0 | 50 / 62 (1) | 4.9965 | `4140768780f0` | 0.346 | 0.725 | 0.425 | 0.9959 | 0.543 | balloon (0) | 44 |
| `cd11c__klangfilm_b3_soft` (FREEFORM) | ok / 0 | 50 / 51 (1) | 7.0484 | `0e2cd51de51c` | 0.804 | 0.470 | 1.258 | 0.9737 | 2.314 | balloon (0) | 12 |
| `cd11c__ath_core_petal` (OSSE) | ok / 0 | 50 / 89 (1) | 4.2316 | `2683984c802c` | 0.417 | 0.563 | 0.871 | 0.9928 | 1.665 | balloon (0) | 45 |
| `cd11__biradial_es` (FREEFORM, first run) | ok / 0 | 50 / 61 (11) | 7.7081 | `69f07277dc3c` | 0.559 | 0.652 | 0.784 | 0.9843 | 1.288 | balloon (0) | 59 |

All 418 valid rows across the eight dirs are `cd_status_code 0` (balloon), with zero
`NAN_TERM_FILL` terms and zero unmeasurable `cd_omega_2pi` (`-1.0`).

### 3.1 Median over the 50 new valid evals

Median of each raw CD metric over the run's **new** valid evaluations (the cached seed row and any
other cache hits excluded), i.e. exactly the 50 evaluations that counted toward the budget. Every
lane now has N = 50.

| lane | median J | median LW dB | median Omega/2pi | median sigma_DI dB | median NACC | median offaxis dB | N (new valid) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cd11c__osse_fold_warm` | 5.0383 | 0.620 | 0.579 | 0.877 | 0.9884 | 1.891 | 50 |
| `cd11c__osse_morph` | 5.5442 | 0.695 | 0.533 | 1.062 | 0.9870 | 1.981 | 50 |
| `cd11c__ext_throat_hvlaw` | 4.2424 | 0.651 | 0.522 | 0.934 | 0.9865 | 0.762 | 50 |
| `cd11c__ath_tritonia_v9` | 5.7007 | 0.547 | 0.571 | 0.835 | 0.9919 | 1.859 | 50 |
| `cd11c__crowe_x_osse_cd` | 5.2668 | 0.438 | 0.734 | 0.423 | 0.9950 | 0.574 | 50 |
| `cd11c__klangfilm_b3_soft` | 7.9354 | 0.915 | 0.459 | 1.382 | 0.9720 | 2.447 | 50 |
| `cd11c__ath_core_petal` | 5.2923 | 0.483 | 0.479 | 1.193 | 0.9888 | 1.844 | 50 |
| `cd11__biradial_es` | 8.3050 | 0.715 | 0.617 | 0.883 | 0.9831 | 1.310 | 50 |

### 3.2 Leaderboard by best J (within v11 only — equal 50-valid budget, not a cross-version rank)

| # | lane | best J | new valid evals |
|---|---|---:|---:|
| 1 | `cd11c__ext_throat_hvlaw` | 3.2940 | 50 |
| 2 | `cd11c__osse_fold_warm` | 3.6930 | 50 |
| 3 | `cd11c__osse_morph` | 3.7525 | 50 |
| 4 | `cd11c__ath_core_petal` | 4.2316 | 50 |
| 5 | `cd11c__crowe_x_osse_cd` | 4.9965 | 50 |
| 6 | `cd11c__ath_tritonia_v9` | 5.1826 | 50 |
| 7 | `cd11c__klangfilm_b3_soft` | 7.0484 | 50 |
| 8 | `cd11__biradial_es` | 7.7081 | 50 |

This ordering is "best design found in a fresh 50-eval continuation run", not convergence: the
per-lane best eval index (`n`) in §3 shows some lanes found their best early (`osse_morph` n=6,
`klangfilm` n=12). All eight lanes now share the same budget, so the ordering is budget-equal within
v11.

## 4. Seed vs completion-best (raw CD terms)

Seed = each lane's **first-run partial best** (the completion config's `seed_params`), which the
completion run re-evaluates as its cached `n=0` row; it is byte-identical to the seed hash/design in
`README.md` §3. Delta = seed − completion-best, so a positive J/LW/offaxis delta is an improvement
and a negative NACC delta is an improvement. This compares a 50-eval continuation against a
partially-improved seed, not against the first run's own `n=0` seed.

| lane | seed J | seed hash | best J | best hash | dJ | d LW | d sigma_DI | d NACC | d offaxis | d Omega | best eval n |
|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| `cd11c__osse_fold_warm` | 4.2236 | `58f158e85aa1` | 3.6930 | `68001408e339` | +0.5306 | +0.0896 | +0.1019 | -0.00052 | +0.0781 | +0.0162 | 47 |
| `cd11c__osse_morph` | 3.9999 | `737be630b12e` | 3.7525 | `0636d3f22d5c` | +0.2473 | +0.0440 | +0.0845 | -0.00352 | -0.0651 | -0.1038 | 6 |
| `cd11c__ext_throat_hvlaw` | 3.8056 | `6ff2d4a3bef0` | 3.2940 | `e85cdd7c61f6` | +0.5116 | +0.1935 | -0.0117 | -0.00189 | +0.2024 | +0.0432 | 79 |
| `cd11c__ath_tritonia_v9` | 5.5944 | `ed66bfa3ab71` | 5.1826 | `81d3b70fc9d8` | +0.4118 | -0.1038 | +0.3830 | -0.00198 | -0.1679 | +0.0266 | 54 |
| `cd11c__crowe_x_osse_cd` | 5.2952 | `4be8fdb4b00d` | 4.9965 | `4140768780f0` | +0.2987 | +0.1072 | -0.0020 | -0.00145 | +0.0245 | +0.0149 | 44 |
| `cd11c__klangfilm_b3_soft` | 7.1831 | `3bfcc80b743a` | 7.0484 | `0e2cd51de51c` | +0.1347 | +0.0390 | -0.0087 | -0.00025 | +0.1196 | +0.0023 | 12 |
| `cd11c__ath_core_petal` | 4.9349 | `928733968160` | 4.2316 | `2683984c802c` | +0.7034 | +0.0366 | +0.2133 | -0.00257 | +0.2865 | -0.0746 | 45 |

Every completion lane improved J on its first-run best. The two CD trade-offs worth noting are
`tritonia`, which improved J by 0.412 while its LW term worsened by 0.104 dB and offaxis by 0.168 dB,
and `osse_morph`/`ath_core_petal`, which traded a slightly worse offaxis term for J. These are
within-run, same-identity comparisons only.

## 5. What changed relative to the first append night

These are the runnability/box changes that let the seven partial lanes reach 50 valid; they are not
acoustic results.

1. **Watchdog off.** `runs/nights/cd_v11_completion_2026-11-20.yaml` sets `watchdog: false`; the first
   night stopped seven lanes on `bound-pinned` / refusal-rate verdicts (`README.md` §2). No completion
   job logged a WATCHDOG line.
2. **Seed = the partial-run best.** Each `cd11c__*.yaml` carries the first-run `best.json`
   `params` as `seed_params`, e.g. `cd11c__osse_fold_warm.yaml` `description` reads
   `seed = best of 20261120T054102Z-screen-9d939b (58f158e85aa1, J 4.2236)`. The seed is re-evaluated
   as the cached `n=0` row, so the 50 counted evals are genuinely new.
3. **Box widening, fold lane.** `az_fold_h_deg` hi limit raised `0.0 -> 10.0` (lo stays `-15.0`); the
   first night stopped this lane because 3/6 of its top designs sat at the high limit.
4. **Box widening, ext_throat lane.** `az_a_cos_pow` lo limit lowered `1.0 -> 0.5` (hi stays `6.0`) —
   the first night stopped this lane because 3/6 of its top designs sat at the low limit.
5. **klangfilm pin, not the stated widening.** The night YAML header comment says
   `klangfilm g_beak_v_projection_mm lo -5`, but the actual lane config does not widen that key: it
   pins it at its first-run best value, `g_beak_v_projection_mm: {lo: 0.0411280271, hi: 0.0411280271,
   search: false}` (21 bounded keys in the job log). This document reports the config that actually
   ran; the lane reached 50 valid with 0 refusals. The mismatch between the YAML header comment and
   the config is recorded here rather than resolved.
6. **`resample_strict` + `retry_same_then_stop`.** The three lanes with the worst first-night refusal
   rates now use `infeasible_penalty: resample_strict` and `error_policy: retry_same_then_stop`:
   `ath_tritonia_v9`, `crowe_x_osse_cd`, `klangfilm_b3_soft` (first night `graded`, no
   `error_policy`). `osse_morph`, `ext_throat_hvlaw` and `ath_core_petal` already carried these
   settings in the first night; `osse_fold_warm` remains `infeasible_penalty: graded` (it had zero
   refusals in both nights).
7. **Attempt cap.** `max_attempts` raised for `ath_tritonia_v9` (`260 -> 300`) and
   `klangfilm_b3_soft` (`250 -> 300`); the other lanes keep their first-night caps (200 or 300).
   `sigma0` is unchanged for every lane (`0.10`–`0.20`). All refusals were free and no lane exhausted
   its attempt cap.

## 6. The two runnability substitutions (not results)

The eight-lane plan named two home-landscape sources whose rows types are not in the stock generator,
so each lane was filled with the runnable current construction. This is carried over unchanged from
`README.md` §5; quoting that section verbatim:

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

1. **`cd11c__ath_tritonia_v9` replaces the bridge-only R-OSSE-rect source.** The `rosse_rect` rows
   type exists only in the GUI preview bridge, so a stock search refuses the seed.
2. **`cd11c__klangfilm_b3_soft` (Klangfilm LAME HV core, B3 soft) replaces the legacy
   `klangfilm_lame` rows type.** The legacy type is superseded by `klangfilm_lame_hv_core` in the
   package generator; this lane runs that shipped HV-core construction.

The substitutes are measured from their own fresh 50-eval completion runs, not assumed from the
research doc's archived-response rows.

## 7. Caveats — read before quoting any number

1. **Completion, not convergence.** All seven completion lanes reached `50 valid of 50 budget`, so
   every lane in this document is a complete 50-eval run. A 50-eval best is still best-so-far, not a
   converged optimum; §3.2 is an ordering at equal budget, not a ranking claim.
2. **Continuation, not the first run's budget.** Each completion lane started from its first-run
   **best design** and ran a further 50 valid evals. Its best J is therefore not comparable as "the
   lane's 50-eval result from cold" — it is a 50-eval continuation from a partially improved seed.
   The seed column in §4 is that starting design, not the first run's `n=0` design (the first run's
   own seed-vs-best deltas are in `README.md` §4).
3. **No pooled J, no cross-version rank.** These are objective-v11 numbers and are not comparable
   to v7/v9/v10 (the configs and `run.json` both record `objective_version: 11`, a new score
   identity with a new brief). The §3.2 ordering is within v11 only.
4. **CD-only comparison.** The delivered matrix is the six CD outputs plus `cov_profile`/`load`
   guards. J is reported as the v11 total, but no term-level attribution outside the CD set is
   claimed, and no family is re-ranked on non-CD terms. (The non-CD terms are present in each
   `best.json` for follow-up work; they are not analysed here.)
5. **Screen resolution.** All lanes ran `mode: screen` with `balloon_points_screen: 512`,
   `angle_count: 73`, `epw: 6.0`, `distance_m: 10.0`, `dof_cap_screen: 24000`. The CD metrics are
   screen-resolution numbers; no verify-resolution re-run was done, and none is claimed.
6. **No rescore was run.** Every number here comes from these fresh runs. No stored v7/v9/v10
   response was re-scored to build this matrix.
7. **Inversion, not measurement.** The four weighted raw CD values are arithmetic inversions of the
   stored normalised terms (tolerances from the v11 brief, verified in
   `objective/scalar_v11.py`); only `cd_omega_2pi`/`cd_status_code` are stored raw. An inversion
   cannot recover precision the normalised float lost, though the terms are stored at full double
   precision so the round-trip error is at the last bit.
8. **Measurement environment.** The night runs one GPU job at a time. Every completion job's
   pre-hygiene reported `gpu-clean: no project Julia/BEAT processes found`; every post-hygiene
   reported `gpu-clean: killed 2 process(es): [...]` and returned VRAM to 687 MiB. VRAM pairs are
   in §2; baselines were 604 MiB for the first job and 687 MiB thereafter.
9. **Refusals are free, not failures.** The refusal counts in §2 are `infeasible_penalty` /
   envelope rejections under `budget_counts: valid`; they did not consume the 50-valid budget and
   no job failed. The frozen response count is 50 new valid per lane.
10. **One config-comment mismatch.** See §5 item 5: `klangfilm_b3_soft`'s `g_beak_v_projection_mm`
    was pinned (search off) in the config that ran, despite the night YAML header describing a
    widening. Quote the config, not the header comment, for that lane.

## 8. Inputs

- Queue log: `runs/nights/queue_cd_v11_completion_2026-11-20.log`;
  night: `runs/nights/cd_v11_completion_2026-11-20.yaml`.
- Runner log: `runs/overnight/queue_cd_v11_completion_2026-11-20.log`.
- Summary: `runs/nights/cd_v11_completion_2026-11-20/summary.jsonl` (7 rows, one per job).
- Per-job logs: `runs/nights/cd_v11_completion_2026-11-20/cd11c__<lane>.log` (UTF-8).
- Completion run dirs (gitignored): `runs/20261120T072543Z-screen-a8074a`,
  `runs/20261120T074140Z-screen-a65a29`, `runs/20261120T075520Z-screen-a342b2`,
  `runs/20261120T081227Z-screen-05f20b`, `runs/20261120T084006Z-screen-fc4e18`,
  `runs/20261120T085629Z-screen-90752f`, `runs/20261120T090536Z-screen-6e83a9`, each with
  `best.json`, `search.ndjson`, `run.json`, `config.yaml`.
- First-run (seed and biradial) dirs: `runs/20261120T054102Z-screen-9d939b`,
  `runs/20261120T055336Z-screen-e23136`, `runs/20261120T060710Z-screen-6d6b36`,
  `runs/20261120T061413Z-screen-5ad3a1`, `runs/20261120T062647Z-screen-9cd14e`,
  `runs/20261120T063319Z-screen-94ab7b`, `runs/20261120T063822Z-screen-a5a822`,
  `runs/20261120T064325Z-screen-97c2af` (biradial).
- Configs: `examples/typologies/cd_v11_completion_2026-11-20/cd11c__*.yaml`; first-run configs and
  brief in `examples/typologies/cd_v11_2026-11-20/` and
  `examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml`.
- First-run partial tables and substitution rationale: `README.md` in this folder;
  `docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md` §4.1.

Numbers in §3 and §4 were generated directly from `summary.jsonl`, each `best.json` and each
`search.ndjson` by a read-only script (no solver, no re-score); the quoted blocks in §1, §2 and §6
were byte-checked against the decoded source files.
