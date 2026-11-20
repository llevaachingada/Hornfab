# compact400 continuation bundle (2026-11-19)

The eight owner-directed 80-eval continuations appended to the live compact400 night, plus the
morph/fold cont2. Same schema as the other bundles: `config.yaml` (seed + bounds), `run.json`
(objective/warm start), `search.ndjson` + `scores.csv` (all score terms + H/V beamwidth, DI,
ripple, on-axis, impedance), `summary.json`, and the best design's geometry, metrics, mesh and
response. J is comparable only within a brief: compact400 (v10xo) for the c4x lanes, the v7
home/smooth briefs for the w4 lanes.

## Result chains

| lane | start | run 1 | run 2 | read |
|---|---|---|---|---|
| compact400 fold | 1.4677 | 1.3147 | **1.2071** | 0.52 under the stored bar 1.7302 |
| compact400 morph | 1.4243 | 1.2271 | **1.2258** | 0.50 under the bar; converged |
| compact400 twinray | 1.4568 | 1.4351 | - | tie; pinned at the 400 mm envelope |
| v7 petal | 4.162 | 4.1202 | - | +0.042, sub-floor tie |
| v7 tritonia_v8 | 4.891 | 4.7503 | - | +0.141, sub-floor tie |
| v7 tritonia_v9 | 4.878 | 5.566 | - | regression in the evaluated set; the 4.878 W2 best stands |
| v7 smooth b3_soft | 2.800 | 2.8187 | - | no gain; the 2.800 best stands |

The compact400 stored bar was 1.7302 (TwinRay bbe858b5b6a4); the floor is 0.1293 J.

## Runs

| run | config | family | obj | rows/valid | best J | best design |
|---|---|---|---|---|---|---|
| `20261119T234133Z-screen-622538` | `c4x_01_morph_cont` | OSSE | v10 | 37/31 | 1.2270927999919121 | `11870ed193af` |
| `20261119T235108Z-screen-21e6c3` | `c4x_02_twinray_cont` | OSSE | v10 | 31/30 | 1.4351413942544358 | `d0743978d68d` |
| `20261120T000243Z-screen-4c9343` | `c4x_03_fold_cont` | OSSE | v10 | 30/30 | 1.3147367015008107 | `d805f33c65b2` |
| `20261120T010803Z-screen-ad381c` | `c4x_04_morph_cont2` | OSSE | v10 | 70/56 | 1.2258229403484977 | `d1f152db276f` |
| `20261120T012508Z-screen-61f226` | `c4x_05_fold_cont2` | OSSE | v10 | 46/46 | 1.207055665420645 | `220e2c562d45` |
| `20261120T005830Z-screen-4036c0` | `scout40w4__klangfilm_b3_soft` | FREEFORM | v7 | 33/31 | 2.8186604617471627 | `19a846460219` |
| `20261120T001246Z-screen-393829` | `scout40w4__petal_hvlaw_v7` | OSSE | v7 | 25/14 | 4.120241010962961 | `3eb0103a511e` |
| `20261120T002250Z-screen-a5dee1` | `scout40w4__tritonia_v8` | OSSE | v7 | 30/30 | 4.750275630136238 | `aa89ee2bd72f` |
| `20261120T003824Z-screen-054989` | `scout40w4__tritonia_v9` | OSSE | v7 | 32/30 | 5.566027531192951 | `9ad78de9a02c` |

## Notes

- The controller finished `exit 1` because several jobs ended by the watchdog (exit 75) / no-gain;
  all partial results are kept here. The `p11_s2w` night was superseded (GPU-busy exit) and its
  queue_state is stale (display-only).
- The night file mixes the compact400 and v7 briefs by design (owner-directed append); do not rank
  J across the groups.

