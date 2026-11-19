# SCOUT40 night evidence bundle (2026-11-19)

Night `fable_scout40_2026-11-19`: 24 jobs, launched 2026-11-18 23:35 local, `QUEUE DONE`
2026-11-19 05:02 local. Sixteen search jobs + the re-run rescores were stopped by the runner's
**watchdog** (exit 75) where the search box or the brief envelope was the limiter; those partial
results are included. The owner-directed requeues (`s40w__*`, `s40w2__*`) are included too.

## What is in each run directory

| file | contents |
|---|---|
| `config.yaml` | the exact config: brief path, family, **seed_params**, searched bounds, search settings, warm-start |
| `run.json` | objective version, config snapshot, lib SHAs, run identity, warm-start record (at the end) |
| `search.ndjson` | one row per evaluation: params, design/mesh/solve hashes, objective J, **terms**, **metrics arrays**, scalars, n_dof, bbox, res_mm, solve times |
| `scores.csv` | flattened per-eval table (terms + every metric array + scalar; arrays are `;`-joined) |
| `summary.json` | config identity, seed, searched bounds, best J/design, warm-start, row counts |
| `designs/<best>/design.json` | the full geometry recipe of the best design (the **geometry + seed** record) |
| `designs/<best>/metrics.json` | the best design's scored metrics (same arrays as the row) |
| `designs/<best>/mesh_meta.json` | mesh resolution/dof metadata |
| `designs/<best>/mesh.msh` | the screen mesh actually solved |
| `designs/<best>/response.npz` | the stored BEM response (angular cut/balloon data) for the best design |

`metrics` arrays (per solved frequency): `freqs_hz`, `bw_h_deg`, `bw_v_deg` (**horizontal and
vertical -6 dB beamwidth**), `di_db` (**directivity index**), `ripple_h_db`, `ripple_v_db`,
`on_axis_db`, `z_throat_real`; `scalars` adds mean/slope/break/SPDI/flatness and loading checks.
`terms` are the score terms (`cov`, `rip`, `di`, `dislope`, `flat`, `load`, `distd`, `diag`,
`flat_cv`, `penalty`, `total`) plus band/LFP diagnostics. J = `objective` (objective version in
`run.json`; **never compare J across versions/briefs**).

The requeue configs are in `examples/typologies/scout40w_2026-11-19/` (tracked in git); the
original configs are in `examples/typologies/scout40_2026-11-19/`.

## Runs

| run | config | family | obj | rows/valid | best J | best design | night status |
|---|---|---|---|---|---|---|---|
| `20261119T060516Z-screen-13c866` | `hl__biradial_es_style_v7__vt_v1` | FREEFORM | v7 | 40/40 | 6.32714095892227 | `0705e7b08d4f` | ok / ok |
| `20261119T082618Z-screen-2fb8dc` | `scout40__ath_core_petal_hvlaw_v7` | OSSE | v7 | 27/16 | 4.892450973881702 | `4d2985321ccf` | watchdog / watchdog |
| `20261119T043506Z-screen-54878f` | `scout40__crowe_v2a_c1` | FREEFORM | v7 | 40/40 | 4.8787457418045195 | `febde0373489` | ok / ok |
| `20261119T090559Z-screen-9b8767` | `scout40__crowe_x_osse_cd_v7` | FREEFORM | v7 | 51/36 | 5.345396237349772 | `9b5428e6dec8` | watchdog / watchdog |
| `20261119T092235Z-screen-690db0` | `scout40__crowe_x_square_v7` | FREEFORM | v7 | 26/18 | 7.91085417600134 | `3c5dae091e52` | watchdog / watchdog |
| `20261119T075629Z-screen-015bfc` | `scout40__ext_throat_hvlaw_v7` | OSSE | v7 | 51/41 | 3.565450827952507 | `c1d088b8b92f` | ok / ok |
| `20261119T074356Z-screen-7c9137` | `scout40__fold_warm_v7` | OSSE | v7 | 30/30 | 3.7537425208041566 | `58bde4024d87` | watchdog / watchdog |
| `20261119T051630Z-screen-ce7a3f` | `scout40__klangfilm_b3_soft` | FREEFORM | v7 | 66/65 | 3.5400116512193747 | `e4d38596e2a8` | watchdog / watchdog |
| `20261119T051833Z-screen-64eea7` | `scout40__klangfilm_hvcore_c200mouth` | FREEFORM | v7 | 30/30 | 10.156250528876068 | `14e53020adbe` | watchdog / watchdog |
| `20261119T053037Z-screen-394fb1` | `scout40__klangfilm_lame_hv_stage_a` | FREEFORM | v7 | 30/30 | 8.392965626781532 | `f2054faaa9d4` | watchdog / watchdog |
| `20261119T050354Z-screen-7ebf9c` | `scout40__lecleach_hv_smooth_v7` | FREEFORM | v7 | 42/34 | 8.03711687018752 | `5381c9cea1ec` | watchdog / watchdog |
| `20261119T050957Z-screen-53fe3d` | `scout40__lecleach_iwata_ar_smooth_v7` | FREEFORM | v7 | 41/40 | 6.76344642372337 | `04501fa6edc8` | watchdog / watchdog |
| `20261119T081214Z-screen-8470bd` | `scout40__morph_v8` | OSSE | v7 | 37/30 | 3.401628119566109 | `cf716e738ef8` | watchdog / watchdog |
| `20261119T092938Z-screen-2de348` | `scout40__rf_rect_axial_cap225` | FREEFORM | v7 | 40/40 | 19.721355561289517 | `8ba61395b295` | ok / ok |
| `20261119T094135Z-screen-382cb5` | `scout40__rf_rect_axial_control270` | FREEFORM | v7 | 40/40 | 19.706252895630566 | `9c39541262aa` | ok / ok |
| `20261119T085256Z-screen-c2203f` | `scout40__rosse_rect_cd_v7` | FREEFORM | v7 | 31/30 | 4.559601646366622 | `efe4a8959d85` | watchdog / watchdog |
| `20261119T083421Z-screen-ab2159` | `scout40__tritonia_v8` | OSSE | v7 | 34/30 | 5.325276694810406 | `2979e2d125ce` | watchdog / watchdog |
| `20261119T090801Z-screen-6a429f` | `scout40__tritonia_v9` | OSSE | v7 | 30/30 | 5.288899871054752 | `73cf78b059a5` | watchdog / watchdog |
| `20261119T073330Z-screen-723756` | `scout40w2__klangfilm_b3_soft` | FREEFORM | v7 | 41/41 | 2.800217399969265 | `ee85bcd2ad67` | ok / ok |
| `20261119T063219Z-screen-8deb7b` | `scout40w__klangfilm_b3_soft` | FREEFORM | v7 | 34/32 | 2.84115842822621 | `15a8c964d592` | watchdog / watchdog |
| `20261119T064153Z-screen-b97a4e` | `scout40w__klangfilm_hvcore_c200mouth` | FREEFORM | v7 | 43/41 | 10.019981431218907 | `00753b8200ac` | ok / ok |
| `20261119T065506Z-screen-dab24f` | `scout40w__klangfilm_lame_hv_stage_a` | FREEFORM | v7 | 41/41 | 8.34952788464452 | `7be037ff53c5` | ok / ok |
| `20261119T061856Z-screen-833a3d` | `scout40w__lecleach_hv_smooth_v7` | FREEFORM | v7 | 49/41 | 8.03630695311841 | `1dab547b5a86` | ok / ok |
| `20261119T062638Z-screen-03ae3c` | `scout40w__lecleach_iwata_ar_smooth_v7` | FREEFORM | v7 | 43/41 | 6.671130953889615 | `06a008612260` | ok / ok |

## Watchdog (exit 75) ledger

Exit 75 is `WATCHDOG_EXIT` (`tools/run_campaign_night.py`): a designed stop, partial results kept.
The reason is in each job log under `runs/nights/fable_scout40_2026-11-19/` (not archived here:
the queue log and summary list the exits). Summary of the handled cases:

- bound-pinned (box is the limiter; widened in `s40w__*` / `s40w2__*`): lecleach_hv_smooth,
  iwata_ar_smooth, klangfilm_b3_soft (twice: beak-V hard floor then theta_h1 hard ceiling),
  klangfilm_hvcore_c200mouth, klangfilm_lame_hv_stage_a.
- later tail stops: fold_warm_v7 (az_fold_h_deg high 0), morph_v8 (morph_rate low 1),
  tritonia_v8/v9 (morph_width high 590 - brief-envelope limit), rosse_rect_cd_v7 (g_tmax high 1 -
  kernel max), and three refusal storms (petal_hvlaw_v7 41%, crowe_x_osse_cd_v7 33%,
  crowe_x_square_v7 31%) - those need a step/box fix, not a widen.

## Score identity / comparability

- Two briefs are in this night: `room_landscape_80x50_700_hf1440_v7_smooth` (jobs 1-6 and their
  requeues) and `room_landscape_80x50_700_hf1440_v7` (home/CD lanes). J is comparable only
  within one brief; the smooth group has its own scale.
- v10 is the shipped second score and is computed offline from the stored responses
  (`tools/analysis/rescore_identity.py`); it is not the search score in this night (owner R1).

## Not included

- The per-eval `response.npz`/`mesh.msh` for every design (only the **best** design's are archived;
  the rows carry every eval's scored metrics and the v10 rescore needs the stored responses for
  the finalists only). The full run trees remain under `runs/` on the owner box.
- The GPU host logs / Julia internals; `run.json` records the lib SHAs and solve metadata.

