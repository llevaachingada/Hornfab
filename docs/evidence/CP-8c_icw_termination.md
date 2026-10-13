# CP-8c run 2/4 — `icw_termination` (budget 800) — COMPLETED

Run id `runs/20261013T204408Z-screen-6bdcbd` (gitignored; hashed in `manifest.sha256`), branch
`claude/wave-3-implementation-review-2dk4qe`. First ICW-family data in the store.

## Final summary (verbatim stdout tail)

```
evaluations 800 (800 new, 0 cached), failures {'invalid_geometry': 5, 'mesh_too_large': 8},
  GPU 8688.4 s, 13.0 s/candidate, 278/h, projected 1,000 = 3.6 h, 10,000 = 36.0 h
seed J=55.7357  best J=12.2009 (improved on the seed); stop: budget
search OK: 800 rows in runs\20261013T204408Z-screen-6bdcbd\search.ndjson; best in \best.json
```

- 800 rows = **787 ok + 13 failed** (`invalid_geometry` 5, `mesh_too_large` 8), torn 0, ok rows
  with metrics null 0, zero in-run duplicate designs. Best design n=190, `n_dof` 2823.
- Wall 2.9 h (20:45–23:37 UTC); solve/median 11.04 s, mesh 1.96 s. Monitoring: zero alarms;
  post-run hygiene reaped the idle worker hosts (incl. one `julialauncher.exe`), VRAM back to 411 MiB.
- `nvidia-smi` never exceeded ~2 GiB on this family (smaller meshes than OSSE).

## ICW mesher warning (data-quality note, bounded)

```
WARNING hornlab_mesher.profile_sampling: outer wall self-intersects: ICW generated outer offset
grid has a normal flip near azimuth row 0, axial interval 0 ... the acoustic (inner) surface
is unaffected
```
- 24 occurrences total, **zero new after 17:06 local** (~a few % of designs; the mesher emits it
  as a warning and the rows still validate). It concerns the freestanding OUTER shell offset;
  the acoustic inner surface is unaffected, so the computed metrics stand.
- Recorded as a caveat for ICW-family records. If ICW exterior physics beyond the inner surface
  are ever trusted (CP-7 physics gates were OSSE-only), a senior/oracle pass over this warning is
  warranted first.

## Bound pinning (final data, from `CP-8c_data_summary.md`)

- **`hold_end` fully pinned at its LOWER bound 0.55** (top-6 6/6; Spearman vs J **+0.64**) and
  `kappa0` 4/6 near lo = 0.0 (median 0.0016 — the search wants κ₀ ≈ 0; 0.0 is already the schema
  floor, so nothing to widen there). Candidate follow-up: widen `hold_end` lo below 0.55, subject
  to the repo's `hold_start < hold_end` rule and mesher validation. Recorded, NOT changed
  mid-campaign (same policy as the OSSE `n`/`q` finding).

## Dataset state after run 2

```
records 2434 (ok 2311, failed 123), shards 5, 395.3 MB
families {'OSSE': 1634, 'R-OSSE': 0, 'ICW': 800, 'FREEFORM': 0}
backends {'beat_cuda': 2434}  lib_sha {'b922e807a5+38544d214b': 2434}
```
Two of four families present; the single-family warning is gone. `dataset verify` will be
re-run after all four configs. Note: CP-8d trains on OSSE, so the ICW pool does not enter the
OSSE gate arithmetic (digest OSSE-pool numbers unchanged: kept 1501 of 1634, held-out 225.2 < 500).