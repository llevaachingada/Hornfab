# CP-8c run 3/4 — `freeform_hv` (budget 800) — COMPLETED EARLY on CMA convergence

Run id `runs/20261013T234724Z-screen-ff569c` (gitignored; hashed in `manifest.sha256`).
First FREEFORM-family data in the store.

## Final summary (verbatim stdout tail)

```
evaluations 722 (722 new, 0 cached), failures {'invalid_geometry': 1}, GPU 6733.8 s,
  12.7 s/candidate, 284/h, projected 1,000 = 3.5 h, 10,000 = 35.3 h
seed J=33.3086  best J=30.5434 (improved on the seed); stop: cma: tolfun
search OK: 722 rows in runs\20261013T234724Z-screen-ff569c\search.ndjson; best in \best.json
```

- **Stopped by CMA convergence (`tolfun`), not budget** — 722/800 rows. 721 ok + 1 failed
  (`invalid_geometry`), torn 0, ok rows with metrics null 0, zero in-run duplicate designs.
- Wall 2.55 h (23:48–02:21 UTC); solve median 9.35 s. All worker processes exited on their own
  (watchdog end state `julia=0 hornlab=0`); VRAM back to desktop-idle 290 MiB. Zero monitor alarms.
- `ff_stderr.log` empty: no mesher warnings of any kind on FREEFORM.

## The low-yield finding (honest, important for dataset use)

```
seed  J=33.309  (cov 28.145, rip 2.664, di 0.767, dislope 1.200, flat 3.339)
best  J=30.543  (cov 26.555, rip 2.418, di 0.613, dislope 0.048, flat 2.726)
ok J p5/p50/p95 = 30.544 / 30.545 / 30.760
median terms over ok rows: cov 26.5564 of total 30.5453 (87 % of J)
best params: profileH.mouthAngleDeg 70 -> 53.8, profileV.mouthAngleDeg 60 -> 62.2, exponent 4 -> 5.52
```

- **Only −8.3 % seed→best** (vs −73 % OSSE, −78 % ICW), and the ok-J band is razor-thin:
  p95 − p5 = 0.22 J. CMA converged onto a plateau (hence `tolfun` fired early).
- Cause: `freeform_hv` exposes only **3 searchable keys** (`profileH.mouthAngleDeg`,
  `profileV.mouthAngleDeg`, `exponent` — the profile point lists are pinned), and its objective
  is **87 % coverage term**, largely fixed by the pinned geometry. The example yaml itself notes
  the FREEFORM control-point mapping is "UNRESOLVED here (task 04's call)".
- Consequence for the dataset: FREEFORM contributes **low-diversity labels** (721 ok rows with
  nearly identical J and metrics). Fine for family *presence* (CP-8c criterion, 3 of 4) and for
  validity-head training; weak for metric-regression training on this family alone.
- Digest limitation (documented): the per-key/pinning tables skip FREEFORM because its search
  keys are dotted paths into nested containers (`profileH.mouthAngleDeg`); the generator handles
  numeric root keys only. Moot for this run (converged plateau).

## Dataset state after run 3 (new `dataset stats` features in action)

```
records 3156 (ok 3032, failed 124), shards 7, 513.6 MB
families {'OSSE': 1634, 'R-OSSE': 0, 'ICW': 800, 'FREEFORM': 722}
missing families ['R-OSSE'], duplicate designs 14
traces 4.2% of records, gpu solve seconds 42056.3
```

Three of four families present; R-OSSE listed under `missing families` (no example config —
finding (a) of the senior review). `duplicate designs 14` (0.44 % of records) = the same designs
re-solved across separate run/search pairs (known store behaviour; surfaced by the new stats
line, and the train-side hash dedup from commit e0b9b61 keeps them out of the gate arithmetic).