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

## Run `20261013T234724Z-screen-ff569c` — freeform_hv (FREEFORM, screen)
- command: `hornlab-search search --config examples\freeform_hv.yaml --budget 800`; config budget 200, CLI --budget 800; status at snapshot: finished
- **bound pinning (top-6)**: fully pinned at LOWER bound: none; at UPPER bound: none
- rows 722 = ok 721 + failed 1 (torn 0); kinds {'invalid_geometry': 1}
- J over ok rows: min 30.543433 / median 30.545342 / mean 30.610275 / max 36.346565; seed J 33.308642
- best: J 30.543433 at n=253 (8c40f5583635), n_dof 2744
- timing medians: solve 9.344578 s, mesh 3.358861 s, total 12.723466 s; rate 283.507853 rows/h over 2.547 h
- di_source {'balloon': 721}; quadrants {'1234': 721}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|

Categorical params (ok rows): {'crossSections': {'__unique_count': 721, '__note': 'non-numeric container key (nested dict/list); values not enumerated'}, 'profileH': {'__unique_count': 721, '__note': 'non-numeric container key (nested dict/list); values not enumerated'}, 'profileV': {'__unique_count': 721, '__note': 'non-numeric container key (nested dict/list); values not enumerated'}}

Failure detail (what the search refused, and where it sits):
- `invalid_geometry`: 1 rows; e.g. invalid_geometry: FREEFORM outward wall offset fails the surface-curvature guard near t=0.9998, phi=26.96 deg: max(0, -wallThickness*kappa_i)=0.447 >= margin=0.

Term medians over ok rows: cov=26.556392, di=0.613222, di_estimated=0.0, dislope=0.047033, flat=2.726082, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=2.417888, total=30.545342

## Run `20261013T204408Z-screen-6bdcbd` — icw_termination (ICW, screen)
- command: `hornlab-search search --config examples\icw_termination.yaml --budget 800`; config budget 200, CLI --budget 800; status at snapshot: finished
- **bound pinning (top-6)**: fully pinned at LOWER bound: ['hold_end']; at UPPER bound: none
- rows 800 = ok 787 + failed 13 (torn 0); kinds {'invalid_geometry': 5, 'mesh_too_large': 8}
- J over ok rows: min 12.200862 / median 12.867557 / mean 19.042996 / max 224.088189; seed J 55.735745
- best: J 12.200862 at n=190 (bf6cb40a5d5c), n_dof 2823
- timing medians: solve 11.041775 s, mesh 1.962985 s, total 13.053283 s; rate 277.911802 rows/h over 2.879 h
- di_source {'balloon': 787}; quadrants {'1': 787}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|
| L_mm | 160.0 | 160.0 | 160.0 | 160.0 | 160.0 | 160.0 | - | - | - | -/- |
| R_mm | 130.0 | 80.0 | 220.0 | 80.13245 | 138.854811 | 219.990341 | 0.329211 | 0.003812 | 0.010165 | 0/0 |
| a0_deg | 14.5 | 14.5 | 14.5 | 14.5 | 14.5 | 14.5 | - | - | - | -/- |
| coverage_angle_deg | 50.0 | 20.0 | 80.0 | 20.048172 | 57.068038 | 79.92899 | -0.199714 | 0.006353 | 0.003812 | 0/0 |
| dkappa_ds_abs_max | 10.0 | - | - | 10.0 | 10.0 | 10.0 | - | - | - | -/- |
| hold_end | 0.7 | 0.55 | 0.9 | 0.55 | 0.550678 | 0.899706 | 0.640544 | 0.753494 | 0.002541 | 6/0 |
| hold_start | 0.3 | 0.1 | 0.45 | 0.106708 | 0.344056 | 0.449979 | 0.153429 | 0.001271 | 0.027954 | 0/0 |
| kappa0 | 0.25 | 0.0 | 0.5 | 0.0 | 0.001563 | 0.300683 | 0.55779 | 0.740788 | 0.0 | 4/0 |
| kappa_abs_max | 1.0 | - | - | 1.0 | 1.0 | 1.0 | - | - | - | -/- |
| r0_mm | 12.7 | 12.7 | 12.7 | 12.7 | 12.7 | 12.7 | - | - | - | -/- |
| theta1_deg | 16.0 | 2.0 | 30.0 | 2.296906 | 16.477297 | 28.614085 | -0.209677 | 0.003812 | 0.0 | 0/0 |
| theta_max_deg | 91.0 | - | - | 91.0 | 91.0 | 91.0 | - | - | - | -/- |

Categorical params (ok rows): {'termination': {'flat_baffle': 787}}

Failure detail (what the search refused, and where it sits):
- `invalid_geometry`: 5 rows; e.g. invalid_geometry: ICW target set is infeasible: max|dkappa/dsigma| 32.8701 exceeds cap 10.0 (hint: {'dkappa_ds_abs_max': 'raise dkappa_ds_abs_max or relax the g
  - median params of these failures: {'L_mm': 160.0, 'a0_deg': 14.5}
- `mesh_too_large`: 8 rows; e.g. mesh_too_large: 5176 dofs (10086 triangles, 5176 vertices) exceeds the dof cap 5000 for quadrants '1'; lower f_max or epw
  - median params of these failures: {'L_mm': 160.0, 'a0_deg': 14.5}

Term medians over ok rows: cov=6.357764, di=0.835041, di_estimated=0.0, dislope=0.112263, flat=3.994997, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=4.236229, total=12.867557

## Run `20261013T123136Z-screen-ca15be` — osse_baseline (OSSE, screen)
- command: `hornlab-search search --config examples\osse_baseline.yaml --budget 1500`; config budget 200, CLI --budget 1500; status at snapshot: finished
- **bound pinning (top-6)**: fully pinned at LOWER bound: ['n']; at UPPER bound: none
- rows 1500 = ok 1405 + failed 95 (torn 0); kinds {'mesh_too_large': 93, 'invalid_geometry': 2}
- J over ok rows: min 6.106092 / median 6.449177 / mean 10.821545 / max 180.453986; seed J 22.592077
- best: J 6.106092 at n=1477 (1dc5af689b1c), n_dof 4213
- timing medians: solve 20.326738 s, mesh 1.873973 s, total 22.224207 s; rate 187.149095 rows/h over 8.015 h
- di_source {'balloon': 1405}; quadrants {'1': 1405}

| key | seed | lo | hi | ok min | median | max | spearman vs J | frac 2% lo | frac 2% hi | top6 lo/hi |
|---|---|---|---|---|---|---|---|---|---|---|
| L_mm | 260.0 | 140.0 | 420.0 | 140.03436 | 396.314404 | 419.999774 | -0.541983 | 0.003559 | 0.046263 | 0/0 |
| a0_deg | 15.5 | 2.0 | 30.0 | 4.671601 | 22.850012 | 29.999801 | 0.328085 | 0.0 | 0.054093 | 0/0 |
| a_deg | 37.5 | 5.0 | 55.0 | 5.00015 | 13.534254 | 50.775831 | -0.06574 | 0.047687 | 0.0 | 0/0 |
| aspect_ratio | 1.25 | 1.0 | 2.0 | 1.001607 | 1.886798 | 2.0 | -0.352387 | 0.004982 | 0.078292 | 0/0 |
| exponent | 4.0 | 1.0 | 8.0 | 1.000425 | 2.840486 | 7.999244 | 0.164442 | 0.010676 | 0.000712 | 0/0 |
| k | 1.0 | 0.3 | 2.5 | 0.318156 | 2.275041 | 2.499706 | -0.497823 | 0.000712 | 0.04484 | 0/0 |
| n | 4.0 | 2.0 | 8.0 | 2.0 | 2.036305 | 7.995176 | 0.617185 | 0.632028 | 0.004982 | 6/0 |
| q | 0.995 | 0.9 | 1.0 | 0.9 | 0.903327 | 0.999611 | 0.487483 | 0.230605 | 0.003559 | 0/0 |
| r0_mm | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | 17.78 | - | - | - | -/- |
| s | 0.7 | 0.0 | 1.0 | 0.010654 | 0.436229 | 0.99998 | 0.536083 | 0.001423 | 0.017794 | 0/0 |

Failure detail (what the search refused, and where it sits):
- `mesh_too_large`: 93 rows; e.g. mesh_too_large: pre-mesh estimate ~15386 triangles (~7847 dofs) is over 1.5x the dof cap 5000 at f_max=5500 Hz, epw=6, quadrants='1'; no mesh was generated
  - median params of these failures: {'a_deg': 18.229116, 'exponent': 3.462014, 'L_mm': 392.14133, 'a0_deg': 25.956097, 'k': 1.981461, 'aspect_ratio': 1.840204}
- `invalid_geometry`: 2 rows; e.g. invalid_geometry: cannot fit the acoustic geometry to the requested mm resolution (throat 5.19697 mm, mouth 10.3939 mm): the axial chord is still 2.48x its limi
  - median params of these failures: {'a_deg': 34.155477, 'exponent': 1.9166, 'L_mm': 284.493181, 'a0_deg': 25.832904, 'k': 1.36656, 'aspect_ratio': 1.737548}

Term medians over ok rows: cov=0.845744, di=0.175149, di_estimated=0.0, dislope=0.028743, flat=4.173958, load=0.0, n_in_band=10.0, n_nan=0.0, penalty=0.0, rip=3.314984, total=6.449177

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
records 3156 (ok 3032, failed 124), shards 7, 513.6 MB
families {'OSSE': 1634, 'R-OSSE': 0, 'ICW': 800, 'FREEFORM': 722}
missing families ['R-OSSE'], duplicate designs 14
backends {'beat_cuda': 3156}  lib_sha {'b922e807a5+38544d214b': 3156}
traces 4.2% of records, gpu solve seconds 42056.3
dates 2026-10-13T05:37:51Z .. 2026-10-14T02:21:07Z
```

### OSSE training pool (what `surrogate train --config osse_baseline.yaml` will see)
- considered 1634 → kept 1501 (skipped_grid_mismatch **133**, skipped_bad_arrays 0)
- majority frequency grid (12 pts): [500.0, 621.79, 773.24, 961.58, 1195.8, 1487.07, 1849.28, 2299.72, 2859.87, 3556.47, 4422.73, 5500.0]
- ok/failed in kept: 1406/95; di_source {'balloon': 1406, '': 95}
- held-out at 15% = **225.2** vs formal floor 500 → gate will REFUSE (indicative only)
- X NaN fraction per key: {'L_mm': 0.0, 'a0_deg': 0.0, 'a_deg': 0.0, 'aspect_ratio': 0.0, 'exponent': 0.0, 'k': 0.0, 'n': 0.0, 'q': 0.0, 's': 0.0}
- y-metric NaN fraction on ok rows: {'bw_h_deg': 0.0, 'bw_v_deg': 0.0, 'di_db': 0.0, 'ripple_h_db': 0.0, 'ripple_v_db': 0.0, 'on_axis_db': 0.0}
- ok rows with ALL metrics NaN: 0
- design_hash duplicates: 1 hashes appear >1 time (top: [['8443a5763be5', 2], ['c54661892c59', 1], ['16905720dfc2', 1]])
