# CP-8 local data digest (generated)

Machine-readable twin: `data_summary.json`. Raw artifacts are local (gitignored);
`manifest.sha256` hashes them. Everything here is derived read-only from the ndjson + store.

## How to read this
- `objective` (J) is the search's scalar cost; **lower is better**. Failure rows store
  the penalty J = 1000 (`PENALTY_INVALID`/`PENALTY_FAILED` in `objective/terms.py`).
- `frac_within_2pct_lo/hi` + `top6_pinning`: if the best designs sit at a bound, that bound
  is wrong (report.html says the same).
- `skipped_grid_mismatch` in the dataset section is the counts of records dropped because
  their frequency grid differs from the majority grid (the majority grid is `freqs_hz`).
- `held_out_at_15pct` vs `held_out_formal_floor` 500: the Stage A gate refuses below 500.

## Run `20261013T123136Z-screen-ca15be` — osse_baseline (OSSE, screen)
- command: `hornlab-search search --config examples\osse_baseline.yaml --budget 1500`; config budget 200, CLI --budget 1500; status at snapshot: running
- **bound pinning (top-6)**: fully pinned at LOWER bound: ['n']; at UPPER bound: none
- rows 1038 = ok 943 + failed 95 (torn 0); kinds {'mesh_too_large': 93, 'invalid_geometry': 2}
- J over ok rows: min 6.109354 / median 7.212181 / mean 13.1277 / max 180.453986; seed J 22.592077
- best: J 6.109354 at n=1020 (c592c114bea0), n_dof 4242
- timing medians: solve 17.543789 s, mesh 1.777564 s, total 19.436334 s; rate 209.180475 rows/h over 4.962 h
- di_source {'balloon': 943}; quadrants {'1': 943}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|
| L_mm | 260.0 | 140.0 | 420.0 | 140.03436 | 383.046493 | 419.999774 | -0.638676 | 0.005302 | 0.068929 | 0/0 |
| a0_deg | 15.5 | 2.0 | 30.0 | 4.671601 | 24.63306 | 29.999801 | 0.118387 | 0.0 | 0.080594 | 0/0 |
| a_deg | 37.5 | 5.0 | 55.0 | 5.00015 | 12.535002 | 50.775831 | 0.148742 | 0.07105 | 0.0 | 0/0 |
| aspect_ratio | 1.25 | 1.0 | 2.0 | 1.001607 | 1.872248 | 2.0 | -0.519574 | 0.007423 | 0.116649 | 0/0 |
| exponent | 4.0 | 1.0 | 8.0 | 1.000425 | 2.87905 | 7.999244 | 0.192041 | 0.015907 | 0.00106 | 0/0 |
| k | 1.0 | 0.3 | 2.5 | 0.318156 | 2.201046 | 2.499706 | -0.341571 | 0.00106 | 0.066808 | 0/0 |
| n | 4.0 | 2.0 | 8.0 | 2.0 | 2.175889 | 7.995176 | 0.755178 | 0.45175 | 0.007423 | 6/0 |
| q | 0.995 | 0.9 | 1.0 | 0.9 | 0.906355 | 0.999611 | 0.565797 | 0.250265 | 0.005302 | 5/0 |
| r0_mm | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | - | - | - | -/- |
| s | 0.7 | 0.0 | 1.0 | 0.010654 | 0.489569 | 0.99998 | 0.408998 | 0.002121 | 0.026511 | 0/0 |

Failure detail (what the search refused, and where it sits):
- `mesh_too_large`: 93 rows; e.g. mesh_too_large: pre-mesh estimate ~15386 triangles (~7847 dofs) is over 1.5x the dof cap 5000 at f_max=5500 Hz, epw=6, quadrants='1'; no mesh was generated
  - median params of these failures: {'a_deg': 18.229116, 'exponent': 3.462014, 'L_mm': 392.14133, 'a0_deg': 25.956097, 'k': 1.981461, 'aspect_ratio': 1.840204}
- `invalid_geometry`: 2 rows; e.g. invalid_geometry: cannot fit the acoustic geometry to the requested mm resolution (throat 5.19697 mm, mouth 10.3939 mm): the axial chord is still 2.48x its limi
  - median params of these failures: {'a_deg': 34.155477, 'exponent': 1.9166, 'L_mm': 284.493181, 'a0_deg': 25.832904, 'k': 1.36656, 'aspect_ratio': 1.737548}

Term medians over ok rows: cov=1.451689, di=0.201763, di_estimated=0.0, dislope=0.208549, flat=4.076674, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=3.399257, total=7.212181

## Run `20261013T121958Z-screen-9e5a5c` — search_smoke (OSSE, screen)
- command: `hornlab-search search --config examples\search_smoke.yaml --budget 60`; config budget 60, CLI --budget 60; status at snapshot: finished
- **bound pinning (top-6)**: fully pinned at LOWER bound: none; at UPPER bound: none
- rows 60 = ok 52 + failed 8 (torn 0); kinds {'mesh_too_large': 7, 'invalid_geometry': 1}
- J over ok rows: min 10.777613 / median 24.416463 / mean 31.591388 / max 83.547244; seed J 22.067752
- best: J 10.777613 at n=58 (6060eec85910), n_dof 1392
- timing medians: solve 3.450809 s, mesh 0.812371 s, total 4.309834 s; rate 717.607973 rows/h over 0.084 h
- di_source {'balloon': 52}; quadrants {'1': 52}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|
| L_mm | 260.0 | 140.0 | 420.0 | 140.827681 | 199.759024 | 352.481073 | -0.125928 | 0.057692 | 0.0 | 0/0 |
| a0_deg | 15.5 | 2.0 | 30.0 | 2.000501 | 5.386164 | 22.736645 | 0.286178 | 0.134615 | 0.0 | 1/0 |
| a_deg | 37.5 | 5.0 | 55.0 | 7.494 | 36.705276 | 54.997678 | 0.276872 | 0.0 | 0.019231 | 0/0 |
| aspect_ratio | 1.25 | 1.0 | 2.0 | 1.000418 | 1.274122 | 1.757659 | 0.312729 | 0.096154 | 0.0 | 0/0 |
| exponent | 4.0 | 1.0 | 8.0 | 1.942949 | 5.064845 | 7.506506 | -0.101084 | 0.0 | 0.0 | 0/0 |
| k | 1.0 | 0.3 | 2.5 | 0.561792 | 1.414322 | 2.460999 | 0.036711 | 0.0 | 0.038462 | 0/0 |
| n | 4.0 | 2.0 | 8.0 | 2.014347 | 4.43194 | 6.619204 | -0.168958 | 0.038462 | 0.0 | 0/0 |
| q | 0.995 | 0.9 | 1.0 | 0.939366 | 0.975571 | 0.999491 | 0.105353 | 0.0 | 0.038462 | 0/0 |
| r0_mm | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | - | - | - | -/- |
| s | 0.7 | 0.0 | 1.0 | 0.320707 | 0.806366 | 0.999999 | 0.061641 | 0.0 | 0.115385 | 0/1 |

Failure detail (what the search refused, and where it sits):
- `mesh_too_large`: 7 rows; e.g. mesh_too_large: pre-mesh estimate ~10299 triangles (~5252 dofs) is over 1.5x the dof cap 3000 at f_max=4500 Hz, epw=6, quadrants='1'; no mesh was generated
  - median params of these failures: {'a_deg': 41.310501, 'exponent': 4.397193, 'L_mm': 294.632868, 'a0_deg': 13.240424, 'k': 1.341163, 'aspect_ratio': 1.320609}
- `invalid_geometry`: 1 rows; e.g. invalid_geometry: cannot fit the acoustic geometry to the requested mm resolution (throat 6.35185 mm, mouth 12.7037 mm): the axial chord is still 2.03x its limi
  - median params of these failures: {'a_deg': 49.899463, 'exponent': 1.025051, 'L_mm': 149.43653, 'a0_deg': 23.550295, 'k': 0.816252, 'aspect_ratio': 1.488335}

Term medians over ok rows: cov=15.138948, di=0.262164, di_estimated=0.0, dislope=3.312226, flat=2.97934, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=2.255769, total=24.416463

## Run `20261013T053757Z-screen-7e6e5b` — search_smoke (OSSE, screen)
- command: `hornlab-search search --config examples/search_smoke.yaml --resume runs/20261013T053757Z-screen-7e6e5b --budget 0`; config budget 60, CLI --budget 0; status at snapshot: finished
- **bound pinning (top-6)**: fully pinned at LOWER bound: none; at UPPER bound: none
- rows 70 = ok 63 + failed 7 (torn 0); kinds {'mesh_too_large': 6, 'invalid_geometry': 1}
- J over ok rows: min 7.363234 / median 23.498383 / mean 25.742863 / max 106.689237; seed J 22.067756
- best: J 7.363234 at n=69 (5b7ada586de1), n_dof 2191
- timing medians: solve 3.131983 s, mesh 0.371046 s, total 3.560081 s; rate 794.952681 rows/h over 0.088 h
- di_source {'balloon': 63}; quadrants {'1': 63}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|
| L_mm | 260.0 | 140.0 | 420.0 | 140.432983 | 192.723337 | 300.160009 | -0.293395 | 0.111111 | 0.0 | 0/0 |
| a0_deg | 15.5 | 2.0 | 30.0 | 2.043323 | 20.675822 | 29.986457 | -0.084725 | 0.015873 | 0.015873 | 0/0 |
| a_deg | 37.5 | 25.0 | 55.0 | 25.027466 | 31.911837 | 45.442357 | 0.147369 | 0.095238 | 0.0 | 2/0 |
| aspect_ratio | 1.25 | 1.0 | 2.0 | 1.017936 | 1.438857 | 1.910381 | -0.152362 | 0.015873 | 0.0 | 0/0 |
| exponent | 4.0 | 2.0 | 8.0 | 2.000604 | 2.739709 | 5.202464 | 0.066532 | 0.238095 | 0.0 | 1/0 |
| k | 1.0 | 0.3 | 2.5 | 0.384519 | 1.310725 | 2.488244 | -0.02957 | 0.0 | 0.015873 | 0/0 |
| n | 4.0 | 2.0 | 8.0 | 2.014347 | 3.706727 | 6.526743 | -0.182556 | 0.047619 | 0.0 | 0/0 |
| q | 0.995 | 0.9 | 1.0 | 0.921429 | 0.975363 | 0.99992 | 0.14881 | 0.0 | 0.126984 | 0/0 |
| r0_mm | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | - | - | - | -/- |
| s | 0.7 | 0.0 | 1.0 | 0.001792 | 0.660615 | 0.999969 | 0.199597 | 0.015873 | 0.047619 | 0/0 |

Failure detail (what the search refused, and where it sits):
- `mesh_too_large`: 6 rows; e.g. mesh_too_large: mesh build failed: generated mesh contains 6,968 triangles, exceeding the effective limit 6,900; increase the relevant mm resolution, raise max_
  - median params of these failures: {'a_deg': 37.312439, 'exponent': 3.95284, 'L_mm': 301.148219, 'a0_deg': 16.2025, 'k': 1.363232, 'aspect_ratio': 1.509847}
- `invalid_geometry`: 1 rows; e.g. invalid_geometry: cannot fit the acoustic geometry to the requested mm resolution (throat 6.35185 mm, mouth 12.7037 mm): the axial chord is still 2.03x its limi
  - median params of these failures: {'a_deg': 44.939678, 'exponent': 2.43195, 'L_mm': 149.43653, 'a0_deg': 23.550295, 'k': 0.816252, 'aspect_ratio': 1.488335}

Term medians over ok rows: cov=12.920841, di=0.242634, di_estimated=0.0, dislope=5.268333, flat=2.947319, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=2.382823, total=23.498383

## Run `20261013T053716Z-screen-d627d9` — osse_baseline (OSSE, screen)
- command: `hornlab-search run --config examples/osse_baseline.yaml --mode screen -v`; config budget 200, CLI --budget -; status at snapshot: finished
- **bound pinning (top-6)**: fully pinned at LOWER bound: none; at UPPER bound: none
- rows 1 = ok 1 + failed 0 (torn 0); kinds {}
- J over ok rows: min 22.592076 / median 22.592076 / mean 22.592076 / max 22.592076; seed J 22.592076
- best: J 22.592076 at n=0 (8443a5763be5), n_dof 3850
- timing medians: solve 17.983824 s, mesh 0.824873 s, total 19.313745 s; rate None rows/h over 0.0 h
- di_source {'balloon': 1}; quadrants {'1': 1}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|
| L_mm | 260.0 | 140.0 | 420.0 | 260.0 | 260.0 | 260.0 | - | 0.0 | 0.0 | 0/0 |
| a0_deg | 15.5 | 2.0 | 30.0 | 15.5 | 15.5 | 15.5 | - | 0.0 | 0.0 | 0/0 |
| a_deg | 37.5 | 25.0 | 55.0 | 37.5 | 37.5 | 37.5 | - | 0.0 | 0.0 | 0/0 |
| aspect_ratio | 1.25 | 1.0 | 2.0 | 1.25 | 1.25 | 1.25 | - | 0.0 | 0.0 | 0/0 |
| exponent | 4.0 | 2.0 | 8.0 | 4.0 | 4.0 | 4.0 | - | 0.0 | 0.0 | 0/0 |
| k | 1.0 | 0.3 | 2.5 | 1.0 | 1.0 | 1.0 | - | 0.0 | 0.0 | 0/0 |
| n | 4.0 | 2.0 | 8.0 | 4.0 | 4.0 | 4.0 | - | 0.0 | 0.0 | 0/0 |
| q | 0.995 | 0.9 | 1.0 | 0.995 | 0.995 | 0.995 | - | 0.0 | 0.0 | 0/0 |
| r0_mm | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | - | - | - | -/- |
| s | 0.7 | 0.0 | 1.0 | 0.7 | 0.7 | 0.7 | - | 0.0 | 0.0 | 0/0 |

Term medians over ok rows: cov=19.22029, di=0.285641, di_estimated=0.0, dislope=0.19295, flat=3.387968, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=1.495635, total=22.592076

## Dataset

```
records 1172 (ok 1062, failed 110), shards 3, 189.6 MB
families {'OSSE': 1172, 'R-OSSE': 0, 'ICW': 0, 'FREEFORM': 0}
backends {'beat_cuda': 1172}  lib_sha {'b922e807a5+38544d214b': 1172}
traces 4.2% of records, gpu solve seconds 16585.1
dates 2026-10-13T05:37:51Z .. 2026-10-13T17:30:00Z
WARNING: dataset is 100% OSSE (1172/1172): a surrogate trained on it cannot be tested on other families; run the other example configs
```

### OSSE training pool (what `surrogate train --config osse_baseline.yaml` will see)
- considered 1172 → kept 1039 (skipped_grid_mismatch **133**, skipped_bad_arrays 0)
- majority frequency grid (12 pts): [500.0, 621.79, 773.24, 961.58, 1195.8, 1487.07, 1849.28, 2299.72, 2859.87, 3556.47, 4422.73, 5500.0]
- ok/failed in kept: 944/95; di_source {'balloon': 944, '': 95}
- held-out at 15% = **155.8** vs formal floor 500 → gate will REFUSE (indicative only)
- X NaN fraction per key: {'L_mm': 0.0, 'a0_deg': 0.0, 'a_deg': 0.0, 'aspect_ratio': 0.0, 'exponent': 0.0, 'k': 0.0, 'n': 0.0, 'q': 0.0, 's': 0.0}
- y-metric NaN fraction on ok rows: {'bw_h_deg': 0.0, 'bw_v_deg': 0.0, 'di_db': 0.0, 'ripple_h_db': 0.0, 'ripple_v_db': 0.0, 'on_axis_db': 0.0}
- ok rows with ALL metrics NaN: 0
- design_hash duplicates: 1 hashes appear >1 time (top: [['8443a5763be5', 2], ['c54661892c59', 1], ['16905720dfc2', 1]])
