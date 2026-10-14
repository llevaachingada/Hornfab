# CP-8c run 4/4 — `throat_adapter` (budget 400) — COMPLETED; the cleanest run of the campaign

Run id `runs/20261014T025335Z-screen-852be3` (gitignored; hashed in `manifest.sha256`).

## Final summary (verbatim stdout tail)

```
evaluations 400 (400 new, 0 cached), failures {}, GPU 4874.5 s, 12.8 s/candidate, 281/h,
  projected 1,000 = 3.6 h, 10,000 = 35.6 h
seed J=9.15918  best J=5.98344 (improved on the seed); stop: budget
search OK: 400 rows in runs\20261014T025335Z-screen-852be3\search.ndjson; best in \best.json
```

- **400 rows = 400 ok + 0 failed** — the only zero-failure run of the campaign (`mesh_too_large`
  cannot occur here: `a_deg`/`L`/`exponent`/`aspect_ratio` are `search: false`, so every candidate
  inherits the seed's modest geometry). torn 0, metrics null 0, zero in-run dups.
- Wall 1.42 h (02:54–04:19 UTC); solve median 11.78 s; `ta_stderr.log` EMPTY (zero mesher warnings).
- Best design: n=399, J 5.9858, `n_dof` 3216, `a0_deg` 2.06 (near its lo 2.0) — see the digest for
  the full per-key/pinning table (this family has numeric root keys, so the digest's pinning
  analysis applies).

## CP-8c CLOSE-OUT (campaign totals)

Four runs, one GPU job at a time, hygiene before/after every run:

| run | config | budget | rows | ok | failed | stop | seed J | best J | wall |
|---|---|---|---|---|---|---|---|---|---|
| 1 | osse_baseline | 1500 | 1500 | 1405 | 95 | budget | 22.592 | **6.106** (−73 %) | 8.02 h |
| 2 | icw_termination | 800 | 800 | 787 | 13 | budget | 55.736 | **12.201** (−78 %) | 2.9 h |
| 3 | freeform_hv | 800 | 722 | 721 | 1 | `cma: tolfun` | 33.309 | **30.543** (−8.3 %) | 2.55 h |
| 4 | throat_adapter | 400 | 400 | 400 | 0 | budget | 9.159 | **5.983** (−35 %) | 1.42 h |

Final store state (the CP-8c criterion):

```
records 3556 (ok 3432, failed 124), shards 8, 587.2 MB
families {'OSSE': 2034, 'R-OSSE': 0, 'ICW': 800, 'FREEFORM': 722}
missing families ['R-OSSE'], duplicate designs 14
traces 4.3% of records, gpu solve seconds 46930.8 (13.0 h of GPU solve)
dates 2026-10-13T05:37:51Z .. 2026-10-14T04:19:42Z
dataset verify OK: 3556 records re-read, 0 bad, 0 bad arrays
```

- **Family total: 3 of 4** — R-OSSE has NO example config (`throat_adapter.yaml` is `family:
  OSSE`), so the runbook's literal "all four families present" is unsatisfiable; amended criterion
  (OSSE+ICW+FREEFORM) recorded per the senior review. Campaign wall ≈ 14.9 h.
- `duplicate designs 14` (0.4 %) — same designs re-solved across separate run/search pairs;
  surfaced by the new stats line and kept out of the gate arithmetic by train-side hash dedup.
- **CP-8d scope note:** training uses OSSE records only (config family filter) whose grid matches
  the majority: kept 1501 of the 1634 OSSE records (`skipped_grid_mismatch` 133 = the 4500 Hz
  smoke runs), held-out 15 % ≈ **225 < 500** → the formal gate refuses → the Stage A result is
  **indicative only** (the CLI now prints this as `GATES REFUSED (indicative only)`).