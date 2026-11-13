# Home task readiness — `p80x60__osse_ext_throat_home700_v7`

**Status: NOT READY for a training-set build or an advisory study (2026-11-13, offline).**

Read-only probe. No solve, mesh, GPU, queue, cache or live dataset write. A temporary
`StudyService` was created under the OS temp directory; the snapshot artifact it published is
discarded with that temp root. The real inputs were only read.

- Task: `p80x60__osse_ext_throat_home700_v7` (objective **v7**), resolved through
  `examples/briefs/print_80x60_2026-11-13/room_80x60_700_hf1440_v7.yaml`.
- Reproduce with `scratch/bo_m0/home/readiness_probe.py` (scratch-only; not committed) or the
  same calls: `StudyService(temp/registry)`, `create_study(spec, key)`, then
  `builders.freeze_snapshot(service, sid, root=REPO)` and
  `builders.build_training(service, sid, root=REPO)` with
  `task.name = p80x60__osse_ext_throat_home700_v7` and
  `source = {catalog_csv: scratch/bo_m0/m2_gate/catalog_20261113/catalog.csv,
  scores_json: scratch/bo_m0/home/offline_scores_home_v7/offline_scores.json,
  dataset_root: dataset}`.

## Inputs (SHA-256)

| Input | SHA-256 |
|---|---|
| `examples/typologies/print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7.yaml` | `c026277105f91d57809c675c57c46d423cdc55336cdf597b59bb66178b64f35d` |
| `examples/briefs/print_80x60_2026-11-13/room_80x60_700_hf1440_v7.yaml` | `5ef075a14dd0ca6827d0a5160640b6cdd3a029e1df892c7489949340196a8712` |
| `scratch/bo_m0/m2_gate/catalog_20261113/catalog.csv` | `5e1eb62dca302b7437a86fd2f78a9ca3f3051c949d6f1e9df0b7d1151aa61e10` |
| `scratch/bo_m0/home/offline_scores_home_v7/offline_scores.json` | `572b255da9a5f080a1a11fc0388a15223e4531a1573443f0e2405160957c3c6d` |

The catalog hash matches the fresh read-only catalog used by the M2 gate
(`docs/evidence/bo_study_2026-11-12/m2/GATE.md`).

## Data quantity: 217 catalog-ok rows vs n_min 16

| Count | Value |
|---|---:|
| Catalog rows for this config | 250 |
| `ok` rows | **217** |
| Failed rows | 33 (`completeness=failed`, `npz_readable=False`, `unknowns=mesh_n_dof_missing`) |
| All ok rows | `completeness=partial_loading_inputs`; `missing_loading_arrays=impedance_matrix` |
| Fidelity / backend / objective version | screen / beat_cuda / 7 (250/250) |
| Run and experiment identity | `20261113T163054Z-screen-51328c` (one run, one experiment id) |

The home config has six searched knobs (`L_mm`, `a_deg`, `morph_rate`, `s`,
`throat_ext_angle_deg`, `throat_ext_length_mm`) and no `morph_exponent`; with the identity
projection `d = 6`, so `n_min = max(16, 2*(d+1)) = **16**`. **The 217 ok rows are enough
quantity for a TrainingSet.** Quantity is not the blocker.

The probe also fixed the builder path needed to reach that answer: `bo.data.build_native_training_set`
hardcoded the native `morph_exponent` no-op and raised `UnsupportedSpaceError` for the six-knob home
space. It now applies that no-op only when the key exists; the home task uses the identity
projection.

## What the probe actually returned

**`freeze_snapshot` → `ok`** (temp-only artifact `1d764a9100f37611b0e27b865b948533829c9daf31e450f0f941d52347aa5f4d`;
the hash includes the temp study id and generation time, so it is an identity example, not a
reproducible byte constant):

| Snapshot field | Value |
|---|---:|
| `cohort.scores.records` | 0 |
| `cohort.scores.ok` | 0 |
| `cohort.catalog.rows` | 30,723 |
| `parity.n` / `parity.n_compared` | 0 / 0 |
| `task.objective_version` | 7 |
| `source.scores_json_sha256` | `572b255d…` |
| `source.catalog_csv_sha256` | `5e1eb62d…` |

**`build_training` → `Unavailable`**: `training set is 'needs_initial_data'; n_min=16 n=0`.
Zero score rows, so the builder correctly refuses to fabricate a training set even though the
catalog has 217 usable rows.

## Blockers (all must clear before a home study)

1. **The home target is not in the offline replay's candidate family.**
   `tools/analysis/offline_scores.py::ath_compatibility` selects only the frozen ATH target
   (`50°/50°`, 300–8000 Hz, f0 1280 Hz, ATH `z_min`/slope/frequency weights). The home target is
   `80°/60°`, 350–8000 Hz, f0 700 Hz, `loaded_hi_hz 5600`, so `core=False` for every home row and
   the replay candidate list is empty. The home replay artifact's `ath_full_native=393` counts
   ATH-family records, not home records; `scored=0`.
2. **The replay adapter dispatches only objective versions 1–4.**
   `hornlab_search/objective/replay.py` returns `R_REPLAY_VERSION_UNSUPPORTED` for v5+; the home
   task is objective **v7**. Even with a home-compatible candidate scan, v7 cannot be replayed
   until a v7 path is authored and validated.
3. **No loading inputs.** All 217 ok home rows are missing `impedance_matrix`, so loading is
   `partial`. The home v7 brief sets loading weight `load: 1.0` and `loaded_hi_hz: 5600`; a
   loading-complete score cannot be produced from this archive. (The 33 failed rows also have no
   mesh dof/loading data.)
4. **One experiment group only.** All 250 rows carry the same run/experiment id, so independent
   experiment identity is still one group, the same M2 limitation.

## What would change the verdict

- A home-target candidate scan (not ATH-only) plus a v7 replay/scoring path with zero backend
  calls, validated against stored runtime J.
- `impedance_matrix` (or a documented loading-free variant whose weight change is a separate,
  reviewed revision) for the 217 screen rows.
- Additional independent home runs for group-held-out evidence; one run is descriptive only.

Until then the honest state is: **n=217 catalog-ok rows ≥ n_min=16, but n=0 replayable score rows;
`build_training` is `Unavailable`.** No home study, proposal or claim is supported.
