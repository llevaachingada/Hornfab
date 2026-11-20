# SCOUT40W2/W3 evidence bundle (2026-11-19)

The owner-directed requeue of the eight SCOUT40 lanes stopped by the runner's watchdog (exit 75),
plus their W3 continuations. 15 jobs, `QUEUE DONE`. Each entry has the same schema as the SCOUT40
bundle: `config.yaml` (seed + bounds), `run.json` (objective version, warm start, lib SHAs),
`search.ndjson` + `scores.csv` (every eval: params, score terms, H/V beamwidth, DI, ripple, on-axis,
throat impedance arrays + scalars), `summary.json`, and the best design's `design.json`,
`metrics.json`, `mesh_meta.json`, `mesh.msh`, `response.npz`.

J is comparable only within a brief. The home lanes use `room_landscape_80x50_700_hf1440_v7`;
the Klangfilm lanes use `..._v7_smooth`. The compact400 lanes are a separate bundle.

## Result chains (best J per attempt; the original SCOUT40 control in brackets)

| lane | control | W2 | W3 | read |
|---|---|---|---|---|
| petal_hvlaw_v7 | 4.892 | 4.196 | **4.162** | +0.73, WIN (above the 0.31 floor) |
| tritonia_v8 | 5.325 | 5.373 | **4.891** | +0.43, WIN (n widened 4..10) |
| tritonia_v9 | 5.289 | **4.878** | 5.003 | +0.41, WIN at W2 (the W3 angle widen regressed) |
| crowe_x_square_v7 | 7.911 | 7.618 | 7.598 | +0.31, at the floor edge |
| fold_warm_v7 | 3.754 | 3.682 | 3.695 | tie, CLOSED (no gain after 3) |
| morph_v8 | 3.402 | 3.232 | 3.757 | tie + 48% storm persisted, CLOSED |
| crowe_x_osse_cd_v7 | 5.345 | 5.345 | - | no gain, no-headroom, not requeued |
| rosse_rect_cd_v7 | 4.560 | 4.560 | 4.690 | tie |

The Klangfilm smooth-brief chain (b3_soft 3.540 -> 2.841 -> 2.800) is in the SCOUT40 bundle.

## Runs

| run | config | family | obj | rows/valid | best J | best design | night status |
|---|---|---|---|---|---|---|---|
| `20261119T144231Z-screen-c57a35` | `scout40w2__crowe_x_osse_cd_v7` | FREEFORM | v7 | 38/30 | 5.345396237349772 | `9b5428e6dec8` | watchdog / watchdog |
| `20261119T144903Z-screen-0ec862` | `scout40w2__crowe_x_square_v7` | FREEFORM | v7 | 26/16 | 7.618312117278556 | `b35c19653487` | watchdog / watchdog |
| `20261119T134012Z-screen-50fbd8` | `scout40w2__fold_warm_v7` | OSSE | v7 | 31/31 | 3.681759353674477 | `b6430673c2e9` | watchdog / watchdog |
| `20261119T135116Z-screen-28debc` | `scout40w2__morph_v8` | OSSE | v7 | 25/14 | 3.232488693018465 | `69aca6e15dca` | watchdog / watchdog |
| `20261119T143027Z-screen-401992` | `scout40w2__petal_hvlaw_v7` | OSSE | v7 | 40/30 | 4.196013028240638 | `fab20de9dd19` | watchdog / watchdog |
| `20261119T145406Z-screen-afaf16` | `scout40w2__rosse_rect_cd_v7` | FREEFORM | v7 | 33/32 | 4.559601646366622 | `efe4a8959d85` | watchdog / watchdog |
| `20261119T140149Z-screen-f8fffb` | `scout40w2__tritonia_v8` | OSSE | v7 | 33/30 | 5.372771250487765 | `3f90557b9b31` | watchdog / watchdog |
| `20261119T141723Z-screen-433f54` | `scout40w2__tritonia_v9` | OSSE | v7 | 30/30 | 4.878473401275163 | `5f689f0f4865` | watchdog / watchdog |
| `20261119T161820Z-screen-9fda2a` | `scout40w3__crowe_x_square_v7` | FREEFORM | v7 | 26/10 | 7.598245619219523 | `be9ab290d3cf` | watchdog / watchdog |
| `20261119T145538Z-screen-a277c4` | `scout40w3__fold_warm_v7` | OSSE | v7 | 30/30 | 3.6945142598615806 | `680d4bcde649` | watchdog / watchdog |
| `20261119T150842Z-screen-18b29b` | `scout40w3__morph_v8` | OSSE | v7 | 25/13 | 3.7573643031639703 | `b0caf1a829a5` | watchdog / watchdog |
| `20261119T155454Z-screen-d1a61d` | `scout40w3__petal_hvlaw_v7` | OSSE | v7 | 55/41 | 4.161632688418152 | `74d8eed97268` | ok / ok |
| `20261119T162153Z-screen-d2b7d3` | `scout40w3__rosse_rect_cd_v7` | FREEFORM | v7 | 33/33 | 4.690277471589399 | `018057bc29c9` | watchdog / watchdog |
| `20261119T152446Z-screen-d98c8d` | `scout40w3__tritonia_v8` | OSSE | v7 | 30/30 | 4.891129482719315 | `cded84a911d2` | watchdog / watchdog |
| `20261119T153950Z-screen-5d766f` | `scout40w3__tritonia_v9` | OSSE | v7 | 36/30 | 5.003223187167279 | `3ea64988763d` | watchdog / watchdog |

## Watchdog (exit 75) note

Exit 75 is `WATCHDOG_EXIT`: designed stops (bound-pinned / refusal storm / no gain), partial results
kept. Two chains were deliberately closed as ties (fold, morph) rather than chasing further pins;
crowe_x osse was a no-headroom negative. See `docs/CONTINUITY.md` (2026-11-19 entries) for the
per-stop reasons and the box/pin_ignore changes.

