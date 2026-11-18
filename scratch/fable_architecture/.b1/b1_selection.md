# B1 / B1f selection — ten designs, mesh-convergence feasibility, and the frequency check

Prepared 2026-11-17; **revised 2026-11-18 under the owner decision**: B1 must test **mesh
convergence**. The previous `verify,finalist` encoding is **B1f** (frequency fidelity, same mesh)
and is renamed here and in the tool. The B1 mesh encoding, its CPU sizing dry run and the
approved-for-GPU job form live in **`b1_mesh_feasibility.md`** and
**`b1_mesh_night_insert.yaml`**; the B1f job is `b1_night_insert.yaml`.

Status: **B1f** prepared, not queued (optional). **B1 mesh** sized on CPU, probe-grade and
**not queued** — it must wait for owner approval and go after the current BO arms. No GPU solve,
no mesher build outside the CPU sizing dry run, no process control, no edit outside
`tools/**` (one job tool), `tests/**` (its offline tests), and this directory.

Brief kept for every score: `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`
(`room_landscape_80x50_700_hf1440_v7`, objective v7, band 350–8000 Hz, screen grid 18 solved
points / 16 in band). Every selected design's own run recorded this brief in `run.json`.

---

## 0. Owner decision 2026-11-18 (what changed)

- **B1 = mesh convergence.** Reference = the design's stored screen row (no re-solve). Refined
  pass = the same design/brief/objective/source/mounting on the **same screen frequency grid**,
  with only `cfg.mesh.epw` raised (×2 / ×3 candidates). No `>=29` frequency requirement: the grid
  is fixed so the mesh is the only variable.
- **The old pair encoding is B1f** ("frequency-fidelity check"): same mesh, different frequency
  count. It is renamed in the tool (help/docstring/`pairs.json`/run.json) and in
  `b1_night_insert.yaml`; it must not be queued under the B1 name.
- **CPU sizing dry run (this revision):** both candidate factors built with the real mesher for
  all ten designs. Realized counts are in `b1_mesh_feasibility.md`. Headline: **x3 is cap-bound
  at the 24 000 screen cap for every design and 31.8–49.3 k DOF if lifted → infeasible on the
  card. x2 builds at the existing cap for the five fold-warm designs (14.3–15.4 k DOF,
  borderline/probe-grade); the five ext-throat designs are refused by the mesher at epw 12
  (symmetry-plane slivers) and are infeasible on the card anyway (~21.1 k DOF).**
- **Recommended default: x2**, fold-warm only, one design per night job, with per-design
  baseline/peak + Shared Usage recording and verified worker teardown.
- The throat-H/V patch set was not looked for and not applied (D3 freeze).

---

## 1. The two checks (after the owner decision)

**B1f — frequency fidelity (the old pair encoding, renamed).** Same design, same mesh, solved at
two frequency tiers (`verify` 29 points vs `finalist` 36 points on 300–8000 Hz). This is what the
pre-decision plan text described as "screen vs finalist", but the two passes build the *same*
mesh resolution, so it measures the grid, not the mesh. Tool default:
`--modes verify,finalist`; job: `b1_night_insert.yaml` (id `b1f_frequency_fidelity_20261118`).

**B1 — mesh convergence (owner decision 2026-11-18).** Reference = the stored screen row (no
re-solve). Refined pass = the same design, brief, objective, source/mounting and **same screen
frequency grid**, with only `mesh.epw` scaled (`--refine-epw-factor`). `mesh_spec` derives throat
`res/2`, mouth `res`, rear `res` from `epw`/`f_max`, so all three tighten. Candidate factors ×2
and ×3; the CPU sizing dry run and the proposed per-design jobs are in
`b1_mesh_feasibility.md` / `b1_mesh_night_insert.yaml`. **x2 recommended, probe-grade; x3
cap-bound and infeasible; ext-throat excluded (mesher refuses at epw 12, ~21.1 k DOF).**

The ten designs below are the same set for both checks (union of the stored-v7 top five and the
v9-corridor top five).

---

## 2. Method

### 2.1 Stored-v7 scan (computed, read-only)

`b1_compute.py` walked every `runs/*/run.json`, kept runs whose `config.brief_file` names the home
brief (48 run dirs), read each `search.ndjson`, and kept the **lowest-J `ok` row per design hash**.

Result: **2 959 design-hash rows from 48 run dirs**. The scan reproduces the task's fold-warm
numbers exactly (`6d6dd332b282` 3.6210, `6b22bb02ec80` 3.6415, `738743cdbd47` 3.6608,
`57fc83db6e71` 3.6733, `1d8886715575` 3.6996) — but those are **ranks 6–10**, not 1–5, because
five `hl__ext_throat_hvlaw_v7/v8` rows score lower under the same brief. The task asked for exactly
this check ("whether any OTHER run dir … has a lower J"): yes, `runs/20261115T143219Z-screen-d3a1bb`
and `runs/20261116T025728Z-screen-cd60f7`.

The named check example `runs/20261116T090751Z-screen-37b115` (biradial) has best J **6.3364** under
this brief — not competitive. Best per config (top of the table):

| best J | config | run | design |
|---:|---|---|---|
| 3.1028 | `hl__ext_throat_hvlaw_v7` | `runs/20261115T143219Z-screen-d3a1bb` | `3a1038da45d0` |
| 3.1028 | `hl__ext_throat_hvlaw_v8` | `runs/20261116T025728Z-screen-cd60f7` | `9fcd21fc1904` |
| 3.6210 | `hl__osse_rrect_fold_warm_v7` | `runs/20261116T153619Z-screen-c221aa` | `6d6dd332b282` |
| 3.9236 | `hl__osse_rrect_morph_v8` | `runs/20261116T030920Z-screen-5d1082` | `5c8864decc06` |
| 3.9918 | `hl__osse_rrect_morph_v7` | `runs/20261115T154322Z-screen-07bea2` | `1f8dfa9311aa` |
| 4.5626 | `hl__rosse_rect_cd_v7` | `runs/20261116T150941Z-screen-0e777a` | `a301d2543a96` |

All rows used objective version 7 (checked per row); J is never compared across versions.

### 2.2 v9 corridor ranking (computed, CPU-only replay — WP3 stored output did not cover it)

The master-plan WP3 stored scenario output (`scratch/home_v9_offline_2026-11-17/scenarios/`,
mirrored under `docs/evidence/home_crowe_v9_offline_2026-11-17/`) scores **only the two legacy
designs** `crowe_es600` and `klangfilm_lame` under the five offline corridor briefs. The home
brief's runs are **not** in it, so the corridor ranking for them was **not recoverable from WP3
stored outputs**. Per the task rule, it was computed read-only on CPU with the existing tool.

- Tool: `tools/analysis/brief_truth_replay.py scenarios` (canonical v9 scorer; `BACKEND_GUARD`
  reported `calls=0`; every stored response hashed before/after and unchanged).
- Brief: `scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1000.yaml`
  (objective v9, H corridor 90°→70° preferred with 60–90 allowance, V 50°, V onset 1000 Hz,
  `cov_below_f0: mask`, `di_roughness` tol 0.5).
- Pool: the same 2 959 stored home-brief designs (2 911 unique hashes; 48 runs), 2 959 replay cells,
  2 314.9 s wall, one CPU process.
- Output: `v9_home_pool_v1000/replay_matrix.{json,csv}`, log `v9_home_pool_v1000.log`.

Because the live queue rewrites `run.json` of runs it is resuming, the first attempt was aborted by
the tool's **own zero-write guard** (`runs\20261116T090751Z-screen-37b115\run.json` changed
mid-read). The rerun read a frozen view (`snap/<run>/`: copied manifests + junctioned immutable
`designs/`); the original runs were never written.

Onset sensitivity (`v9_ten_onset/`): re-scored the ten selected designs under the 700 Hz and
1250 Hz V-onset variants of the same corridor — **the top five and their order are identical**; only
the ext_throat rows re-order below them (ranks 6–9). The v9 J shifts by < 0.05.

The older Fable placeholder `scratch/fable_architecture/CORRIDOR_RERANK.md` uses a **different**
corridor (H flat 80°, `cov_below_f0: one_sided`, `di_roughness` tol 1.0). Under it the v9 top five
would be 2 `hl__osse_rrect_morph_v7` + 3 fold-warm designs. It is cited for cross-reference only;
its numbers are not used here, and it is not WP3.

### 2.3 Mesh feasibility method

`b1_compute.py` loaded each selected run's own `config.yaml` and computed
`mesh_spec("finalist", cfg)` and `mesh_spec("screen", cfg)`: DOF caps, triangle ceiling, `f_max`,
`epw`, and the resolution `res_mm = 1000·c / (epw·f_max)`. Observed screen mesh sizes are the
stored rows' `n_triangles` / `n_dof`; the finalist estimate uses the same resolution (see §5).

---

## 3. The ten designs

`v7 J` = stored screen J under the home brief (18 solved frequencies, 16 in band).
`v9 J` = WP3-tool replay under the corridor brief above, from the same stored screen response
(18 solved frequencies, 16 in band).
`tri/dof` = the stored screen mesh; the finalist mesh is built at the same resolution (§5).

| # | source | run dir | design hash | config | v7 J | v9 J | tri / dof (same at screen/verify/finalist) | tier |
|---:|---|---|---|---|---:|---:|---|---|
| 1 | v9 top1 | `runs/20261116T130335Z-screen-ab4fb9` | `2f7307c06023` | `hl__osse_rrect_fold_warm_v7` | 4.1413 | **1.6492** | 7 220 / 3 751 | GPU |
| 2 | v9 top2 | `runs/20261116T130335Z-screen-ab4fb9` | `507e7257c091` | `hl__osse_rrect_fold_warm_v7` | 3.9485 | **1.6691** | 7 304 / 3 791 | GPU |
| 3 | v9 top3 | `runs/20261116T130335Z-screen-ab4fb9` | `ced63c6a01a1` | `hl__osse_rrect_fold_warm_v7` | 3.8251 | **1.6927** | 7 408 / 3 844 | GPU |
| 4 | v9 top4 | `runs/20261116T130335Z-screen-ab4fb9` | `688ffe811b6a` | `hl__osse_rrect_fold_warm_v7` | 3.8923 | **1.7159** | 7 313 / 3 796 | GPU |
| 5 | v9 top5 | `runs/20261116T130335Z-screen-ab4fb9` | `78f599e8a1d2` | `hl__osse_rrect_fold_warm_v7` | 4.0317 | **1.7511** | 7 391 / 3 837 | GPU |
| 6 | v7 top1 | `runs/20261115T143219Z-screen-d3a1bb` | `3a1038da45d0` | `hl__ext_throat_hvlaw_v7` | **3.1028** | 2.2849 | 10 175 / 5 275 | GPU |
| 7 | v7 top2 | `runs/20261116T025728Z-screen-cd60f7` | `9fcd21fc1904` | `hl__ext_throat_hvlaw_v8` | **3.1028** | 2.2849 | 10 173 / 5 274 | GPU |
| 8 | v7 top3 | `runs/20261115T143219Z-screen-d3a1bb` | `766c9b1ba8a9` | `hl__ext_throat_hvlaw_v7` | **3.2995** | 2.2837 | 7 149 / 3 725 | GPU |
| 9 | v7 top4 | `runs/20261115T143219Z-screen-d3a1bb` | `508f907726d3` | `hl__ext_throat_hvlaw_v7` | **3.3051** | 2.1605 | 7 685 / 3 999 | GPU |
| 10 | v7 top5 | `runs/20261115T143219Z-screen-d3a1bb` | `b996da551021` | `hl__ext_throat_hvlaw_v7` | **3.5743** | 2.6499 | 7 714 / 4 009 | GPU |

The last column is **B1f** feasibility (the unchanged mesh is GPU-safe for all ten). The **B1 mesh** verdict is different and is in §5.2 / `b1_mesh_feasibility.md`: five fold-warm x2 probes are borderline, five ext-throat designs are infeasible/excluded, and x3 is cap-bound for all.

Config: `epw` 6.0, quadrants `1` (quarter), `f_max` 8000 Hz, `rear_res_factor` 1.5 (fold-warm) /
1.0 (ext_throat), balloon 512 → 1024 points, `dof_cap_screen` 24 000 → `dof_cap_finalist` 48 000,
`max_triangles` 216 471 → 432 942 (full-domain-equivalent ceilings), `dof_per_triangle` 0.51.
Frequencies: **first (verify) pass 29** (27 in band) / **finalist pass 36** (34 in band) — both
≥ 29 as required. The stored v7/v9 scores above used the design's existing screen solve (18 solved
points, 16 in band); the B1f job re-solves at the two ≥ 29-point tiers; the B1 mesh job keeps
the stored screen grid and changes only epw.

## 4. Union / dedup / top-up arithmetic

- v7 top5 = `{3a1038da45d0, 9fcd21fc1904, 766c9b1ba8a9, 508f907726d3, b996da551021}`
- v9 top5 = `{2f7307c06023, 507e7257c091, ced63c6a01a1, 688ffe811b6a, 78f599e8a1d2}`
- intersection = ∅
- **|union| = 10 → top-up from v7 = 0 designs**; dedup removed 0 duplicates.

## 5. Mesh size and GPU / CPU verdict

### 5.1 The important finding: the finalist tier does **not** densify the mesh for these configs

`mesh_spec("finalist")` changes the triangle **ceiling** (216 471 → 432 942 full-domain-equivalent;
the solved quarter mesh may use at most 54 118 → 108 236 triangles, ≈ 27.6 k → 55.2 k solved DOFs
with the 1.15 slack) and the frequency grid (against screen the balloon density changes too; verify
and finalist share verify density), but the actual element size is
`res_mm = 1000·c/(epw·f_max)` and both tiers here have `epw = 6`, `f_max = 8000` (the brief's
`band_hi_hz`). The mesher treats `max_triangles` only as a budget/refusal limit — it does not refine
toward it (`hornlab_mesher/density.py::_record_and_check_triangle_estimate`; our
`mesh/build.py:387` is a pre-mesh guard). The stored screen meshes use **3.7–5.3 k of a 24 k-DOF
cap** (≈ 22 % of the screen ceiling, ≈ 8–11 % of the finalist ceiling), so the cap is not binding.

Result: the finalist mesh is **the same horn at the same 7.1458 mm resolution** — the same
7 149–10 175 triangles / 3 725–5 275 DOFs, re-meshed under a different spec hash. The old pair
encoding therefore measures **frequency-count fidelity (29 vs 36) at an unchanged mesh and a
non-binding cap** — it is **B1f**, not B1. That is the motivation for the owner's 2026-11-18
decision: B1 must change `mesh.epw` and keep the grid fixed (`b1_mesh_feasibility.md`).

If the cap ever *were* binding, `dof_cap_finalist = 48 000` is far past the measured card:
TOOLCHAIN M2 puts the quarter-domain OOM boundary at **8.9 k–15.7 k DOFs** (full-domain 5.5 k–9.2 k;
"memory-pressure territory above ~5 k"). A binding finalist cap is ≈ 48 k solved DOFs (≈ 55 k with
the 1.15 slack) — roughly **3–6× the quarter-domain ceiling**. Such a design belongs on the CPU lane
(`--backend beat_cpu`), not on the 8 GB card.

### 5.2 Verdicts after the CPU sizing dry run (2026-11-18)

Full table and provenance: **`b1_mesh_feasibility.md`**. Summary:

- **x2 (epw 12), five fold-warm designs:** build at the existing 24 000 DOF cap; realized
  **14 270–15 388 quarter DOF** (3.9× the reference). That is inside the measured 8.9–15.7 k OOM
  transition, so they are **probe-grade**: each must be measured as its own process with the
  Shared Usage record; a spill invalidates that design. **Recommended default.**
- **x3 (epw 18), all ten:** **cap-bound at 24 000** (pre-mesh estimate > 1.5× cap); a diagnostic
  build with the cap lifted realizes **31 844–49 288 DOF** — 2–3× the quarter OOM ceiling →
  infeasible. Not queued.
- **ext-throat five at x2/x3:** the mesher refuses the finer mesh
  (`non-sliver triangle(s) in the x=0 symmetry plane`); estimated 21 096/21 100 DOF at x2 and
  47 466/47 475 at x3. **Mesh check infeasible on this card** — excluded from the B1 conclusion,
  recorded, not downgraded.
- **B1f (frequency check):** all ten are GPU-safe (unchanged ~3.7–5.3 k DOF), but it is not B1.

Reference builds reproduce the stored screen mesh exactly for all ten (7 220/3 751 … 10 175/5 275),
which validates the sizing path. No solve was run.

## 6. Night-file job

### 6.1 Why not the studies package

`fidelity-ladder-10` has the right 10+10 shape, but the runner cannot spend those calls at the
finalist tier: `studies/production.py:362` maps every non-screen candidate to
`mode = 'verify'`, `studies/evaluator.py:365` builds the plan as `("verify", gid)`, and
`package.py:57-58` records the per-tier dispatch as open wiring. Running a package would produce
10 verify-tier solves, not 10 finalist-tier ones. Fixing that means editing frozen
`hornlab_search/**`, which this lane forbids. A studies package is **not** the right encoding. For B1 mesh the same applies for a second reason: no package or stock CLI path scales `mesh.epw` while keeping the solve spec fixed.

### 6.2 Why not `hornlab-search verify`

`verify`'s parser has no `--mode`, and `cli.py:944` hardcodes `"verify"` in the `evaluate(...)` call.
`run` evaluates the config seed; `search` runs CMA candidates. **No existing CLI command evaluates a
named list of design hashes at the finalist tier.** Exact gap: a `--mode` on `verify` that is passed
to `evaluate` (one line in `cli.py`), plus the finalist tier's acceptance there. That file is frozen
here.

### 6.3 The minimal new tool

`tools/night_queue/fidelity_pairs.py` (+ `tests/test_tools_fidelity_pairs.py`, 23 offline tests).
It owns only selection, the loops, run-dir bookkeeping and the JSON records; every mesh/solve/
metrics/J call is the existing `search.evaluate.evaluate` / `mesh.build.build_mesh`. No solver,
mesher, metric or objective code. It takes the GPU lock (honouring `HORNLAB_GPU_LOCK=refuse`),
writes one run dir per (source run, tier) so two source configs never share an evaluation context
and the two responses per design hash cannot collide, skips a design/tier already ok in that run
dir (retry-safe), and refuses the whole set if any requested hash has no ok row.

Two modes, clearly labelled:
- **B1f pair mode** (`--modes`, default `verify,finalist`): frequency fidelity on one mesh; the
  JSON record carries `"check": "B1f-frequency-fidelity"` and an explicit
  "NOT mesh convergence" warning.
- **B1 mesh mode** (`--refine-epw-factor F`): reference = stored row; refined = same screen grid
  with only `mesh.epw` scaled. It asserts the refined `SolveSpec` hash equals the stored row's,
  records ΔJ vs the smallest finalist gap, per-term deltas and mean in-band H/V beamwidth / DI /
  ripple deltas, and classifies cap-bound builds. With `--teardown-per-design` and
  `--record-vram` (both default on) it also performs a verified host teardown per design and
  records baseline + peak device memory + the host tree's dedicated/SHARED usage.
- **Mesh sizing dry run** (`--dry-run --build-meshes --refine-factors 2,3`): builds the reference
  and refined meshes on CPU only and records realized triangles/DOF, cap-bound status and a
  feasibility verdict. This produced `b1_mesh_feasibility.md`.

### 6.4 The job entries

**B1f (optional, renamed; `b1_night_insert.yaml`)** — frequency fidelity, all ten designs:

```yaml
- id: b1f_frequency_fidelity_20261118
  kind: command
  timeout_s: 10800
  env:
    HORNLAB_GPU_LOCK: refuse
  argv:
  - .venv/Scripts/python.exe
  - tools/night_queue/fidelity_pairs.py
  - --designs-file
  - scratch/fable_architecture/.b1/b1_designs.csv
  - --modes
  - verify,finalist
  - --out
  - runs/b1f_freq_2026-11-18
```

**B1 mesh (proposed, NOT queued; `b1_mesh_night_insert.yaml`)** — five per-design jobs for the
fold-warm x2 probes, after the BO arms and owner approval. Each job runs
`run_with_memwatch.py --out runs/nights/b1_mesh_2026-11-18/memwatch/<job>.json -- python
tools/night_queue/fidelity_pairs.py --design <run>:<hash> --refine-epw-factor 2
--teardown-per-design --record-vram --gain-threshold 0.0057 --out runs/b1_mesh_2026-11-18`
with `HORNLAB_GPU_LOCK: refuse` and `timeout_s: 10800`. The x3 candidates and the five ext-throat
designs are deliberately absent (cap-bound / infeasible); see `b1_mesh_feasibility.md`.

All ids collide with no id in the live night file (54 jobs at validation time). The tool is a command job,
not a `search`, so no watchdog applies. The runner re-reads the file before every job and runs one
job at a time, so nothing overlaps another solve.

## 7. Validation (pasted)

```
$ .venv\Scripts\python.exe scratch/fable_architecture/.b1/b1_validate.py
live jobs: 54
design rows: 10 unique: 10

yaml ok: b1_night_insert.yaml: night=b1f_frequency_fidelity_2026-11-18 lane=gpu jobs=1
  ids: ['b1f_frequency_fidelity_20261118']
  collisions with live: []
  argv path .venv/Scripts/python.exe: exists=True
  argv path tools/night_queue/fidelity_pairs.py: exists=True
  argv path scratch/fable_architecture/.b1/b1_designs.csv: exists=True

yaml ok: b1_mesh_night_insert.yaml: night=b1_mesh_2026-11-18 lane=gpu jobs=5
  ids: ['b1_mesh_2f7307c06023_20261118', 'b1_mesh_507e7257c091_20261118', 'b1_mesh_ced63c6a01a1_20261118', 'b1_mesh_688ffe811b6a_20261118', 'b1_mesh_78f599e8a1d2_20261118']
  collisions with live: []
  argv path .venv/Scripts/python.exe: exists=True
  argv path tools/bench/run_with_memwatch.py: exists=True
  argv path runs/nights/b1_mesh_2026-11-18/memwatch/b1_mesh_2f7307c06023_20261118.json: exists=False
  ... (same for the other four; the memwatch JSON is an OUTPUT path, created by the wrapper)
  design runs/20261116T130335Z-screen-ab4fb9:<hash> ok_row=True fold_warm_scope=True   (x5)

mesh job ids not in the five-design scope: []

same-screen-grid contract (stored solve_hash == config screen solve hash):
  2f7307c06023: 94eb7eb4369d == 94eb7eb4369d -> True
  507e7257c091: 94eb7eb4369d == 94eb7eb4369d -> True
  ced63c6a01a1: 94eb7eb4369d == 94eb7eb4369d -> True
  688ffe811b6a: 94eb7eb4369d == 94eb7eb4369d -> True
  78f599e8a1d2: 94eb7eb4369d == 94eb7eb4369d -> True
  3a1038da45d0: ca3243f60c10 == ca3243f60c10 -> True
  9fcd21fc1904: ca3243f60c10 == ca3243f60c10 -> True
  766c9b1ba8a9: ca3243f60c10 == ca3243f60c10 -> True
  508f907726d3: ca3243f60c10 == ca3243f60c10 -> True
  b996da551021: ca3243f60c10 == ca3243f60c10 -> True

$ .venv\Scripts\python.exe tools/run_campaign_night.py --night scratch/fable_architecture/.b1/b1_night_insert.yaml --dry-run
night: b1f_frequency_fidelity_2026-11-18 lane=gpu (1 job(s))
  1. b1f_frequency_fidelity_20261118 [command] timeout=10800s
     argv: .venv/Scripts/python.exe tools/night_queue/fidelity_pairs.py --designs-file scratch/fable_architecture/.b1/b1_designs.csv --modes verify,finalist --out runs/b1f_freq_2026-11-18
exit=0

$ .venv\Scripts\python.exe tools/run_campaign_night.py --night scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml --dry-run
night: b1_mesh_2026-11-18 lane=gpu (5 job(s))
  1. b1_mesh_2f7307c06023_20261118 [command] timeout=10800s
     argv: .venv/Scripts/python.exe tools/bench/run_with_memwatch.py --out runs/nights/b1_mesh_2026-11-18/memwatch/b1_mesh_2f7307c06023_20261118.json -- .venv/Scripts/python.exe tools/night_queue/fidelity_pairs.py --design runs/20261116T130335Z-screen-ab4fb9:2f7307c06023 --refine-epw-factor 2 --teardown-per-design --record-vram --gain-threshold 0.0057 --out runs/b1_mesh_2026-11-18
  2. b1_mesh_507e7257c091_20261118 [command] timeout=10800s
     ...
  5. b1_mesh_78f599e8a1d2_20261118 [command] timeout=10800s
     ...
exit=0

$ .venv\Scripts\python.exe tools/night_queue/fidelity_pairs.py --designs-file scratch/fable_architecture/.b1/b1_designs.csv --dry-run --build-meshes --refine-factors 2,3 --out scratch/fable_architecture/.b1/b1_mesh_dryrun
  ... (30 CPU mesh builds; per-design lines in b1_mesh_dryrun.log)
fidelity_pairs mesh sizing COMPLETE: 10 designs; 12 candidate build(s) refused (expected findings recorded); record scratch\fable_architecture\.b1\b1_mesh_dryrun\mesh_dryrun.json
exit=0

$ .venv\Scripts\python.exe -m pytest tests/test_tools_fidelity_pairs.py -q
........................                                                 [100%]
```

Reference builds reproduced the stored screen mesh for all ten (7 220/3 751 … 10 175/5 275); the
CPU sizing run wrote `b1_mesh_dryrun/mesh_dryrun.json`. No BEM solve ran. The memwatch JSON paths
listed as `exists=False` are output paths the wrapper creates at night.

## 8. Reused vs computed

**Reused (not re-measured):**
- Stored v7 J / rows / meshes / responses from `runs/**` (read-only).
- Each run's own `config.yaml` for caps, `epw`, `f_max`, frequency grids.
- The WP3 brief files and the WP3 replay tool (its canonical scorer, not a reimplementation).
- TOOLCHAIN M2 VRAM numbers and M3 per-frequency costs.
- `scratch/fable_architecture/CORRIDOR_RERANK.md` as a cross-reference only (different corridor).

**Computed here:**
- The stored-v7 ranking (dedup by hash, best row per hash) over 2 959 rows / 48 runs.
- The v9 corridor ranking for the home-brief pool (WP3 stored scenarios did not cover it):
  2 959 offline replay cells on CPU, 0 GPU calls, plus a 3-onset stability check on the ten.
- The B1 mesh sizing dry run: reference + epw x2/x3 meshes built with the real mesher for all
ten designs, realized triangles/DOF, cap-bound classification (1_mesh_feasibility.md).
- The near-duplicate check (below) and all validation output.

## 9. Judgment calls

1. **v7 top five = ext_throat_hvlaw, not fold-warm.** The task's list was fold-warm-only; the
   instruction to check other home-brief runs found five lower-J ext_throat rows. The fold-warm
   five are ranks 6–10. The selection follows the stated rule ("top five under stored v7").
2. **Corridor = the WP3 h90→70 placeholder (v1000), not the older Fable h80-flat placeholder.**
   The task points at WP3; WP3's stored scenarios only cover the two legacy designs, so the ranking
   was recomputed with the existing tool. The older placeholder would pick 2 morph + 3 fold-warm.
   The owner has not chosen a corridor (WP5) — this is a placeholder, not a decision.
3. **One job, two tiers, both freshly solved.** `--cache-dir` is omitted, so the first (verify) pass
   really solves instead of replaying tonight's cached response: that is the matched pair the plan
   asks for. If the owner prefers to save GPU time, adding `--cache-dir cache` turns that pass
   into a cache hit (the finalist pass is new work either way).
4. **Near-duplicate pair.** `3a1038da45d0` (`ext_throat_hvlaw_v7`) and `9fcd21fc1904`
   (`ext_throat_hvlaw_v8`) have the same OSSE parameters differing only by stored rounding
   (≤ 4e-4 mm on `L_mm`/`r0_mm`, ~1e-6 relative on every knob), the same mesh size (10 175 vs
   10 173 triangles), and the same J to 3e-6.
   They are different design hashes, so the stated dedup keeps both — but they are effectively one
   horn, and B1 spends 2 of its 20 solves on it. One-line alternative if the orchestrator prefers
   ten distinct horns: replace `9fcd21fc1904` with `6d6dd332b282`
   (`runs/20261116T153619Z-screen-c221aa`, fold-warm J 3.6210, v9 J 2.0103) in `b1_designs.csv`.
   I did **not** make that swap: it deviates from the requested union rule.
5. **`runs/20261116T025728Z-screen-cd60f7` has `run.json status: "running"`** (stale: no job for it
   in the live night file). Its stored rows and responses are fixed and content-addressed, so the
   design is usable; only note that the run may be resumed later.
6. **The `fidelity-ladder-10` profile is not used.** It stays a valid budget description, but the
   night file has no budget-profile field and the studies runner cannot dispatch its verify calls
   at the finalist tier. The job encodes the same 10 + 10 shape directly.
7. **Mesh default = x2, not x3, and it is probe-grade.** x3 (epw 18) has the 0.028 dB DI
   precedent but is cap-bound at 24 000 for all ten and 31.8–49.3 k DOF when lifted → infeasible.
   x2 builds at the existing cap for the fold-warm five (14.3–15.4 k DOF) but lands inside the
   8.9–15.7 k measured OOM transition, so each design is its own job with a Shared Usage check.
   See `b1_mesh_feasibility.md`.
8. **The five ext-throat designs are excluded from B1 mesh**, not silently downgraded: the mesher
   refuses at epw 12/18 (`non-sliver triangle(s)` in the x=0 symmetry plane) and the estimate
   (~21.1 k DOF at x2) is over the card ceiling. They remain in B1f.
9. **Per-term data exists in the stored rows** (verified): `terms` carries the normalized weighted
   terms and `metrics` the per-frequency H/V beamwidth, DI, ripple and on-axis arrays. The mesh
   tool compares them directly; no reference re-solve is needed.

## 10. Open questions

1. **Accept the probe-grade x2 batch?** 14.3–15.4 k DOF is inside the measured 8.9–15.7 k
   transition. The per-design Shared Usage record is the arbiter; if the first fold-warm probe
   spills, B1-mesh is not feasible on this card at x2 either. A factor between 2 and 3 (e.g. 1.5)
   was not requested and was not probed.
2. **Which corridor is the kept placeholder?** WP3 h90→70 (used here) vs the older Fable h80-flat
   versus another owner choice (WP5). It affects the v9 half of the selection, not the mesh result.
3. **Swap the near-duplicate?** See §9.4 — one CSV line.
4. **Should the B1f first (verify) pass reuse the cache?** See §9.3 — GPU time vs a true matched
   re-solve. (B1 mesh always uses the stored reference; no reference re-solve.)
5. **Ext-throat at a finer mesh** would need a mesher fix for the symmetry-plane slivers at
   epw ≥ 12 or a different surface-fit choice; neither is in this lane and no mesher key was
   invented.

## 11. Files and commands

Deliverables in `scratch/fable_architecture/.b1/`:
- `b1_selection.md` (this file), `b1_selection.json` (machine-readable selection table)
- **`b1_mesh_feasibility.md`** — B1 mesh CPU sizing table, cap behaviour, job hygiene,
  per-term-data provenance
- `b1_night_insert.yaml` — **B1f** job (renamed; optional, not B1)
- **`b1_mesh_night_insert.yaml`** — **B1 mesh** proposed five-job spec (not inserted; after the BO
  arms, owner approval required)
- `b1_designs.csv`
- `b1_compute.py`, `b1_table.py`, `b1_v9_score.py`, `b1_snapshot.py`, `b1_best_by_config.py`,
  `b1_validate.py`, `b1_check_versions.py`, `b1_smoke_meta.py`
- `home_brief_rows.json` (2 959 rows), `v9_home_pool_v1000/` + `.log` (2 959 replay cells),
  `v9_ten_onset/` (3-onset check), `snap/` (frozen manifests + junctioned designs)
- **`b1_mesh_dryrun/`** (`mesh_dryrun.json` + built meshes) and `b1_mesh_dryrun.log`

New tool + tests (the only writes outside this directory):
- `tools/night_queue/fidelity_pairs.py`
- `tests/test_tools_fidelity_pairs.py`

Key commands (all read-only except the tool/test files and this directory):
```
.venv\Scripts\python.exe scratch/fable_architecture/.b1/b1_compute.py --json scratch/fable_architecture/.b1/home_brief_rows.json
.venv\Scripts\python.exe scratch/fable_architecture/.b1/b1_snapshot.py
.venv\Scripts\python.exe scratch/fable_architecture/.b1/b1_v9_score.py --brief scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1000.yaml --out scratch/fable_architecture/.b1/v9_home_pool_v1000
.venv\Scripts\python.exe scratch/fable_architecture/.b1/b1_table.py
.venv\Scripts\python.exe tools/analysis/brief_truth_replay.py scenarios --briefs scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v700.yaml scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1250.yaml --out scratch/fable_architecture/.b1/v9_ten_onset --design ...
.venv\Scripts\python.exe tools/night_queue/fidelity_pairs.py --designs-file scratch/fable_architecture/.b1/b1_designs.csv --dry-run --build-meshes --refine-factors 2,3 --out scratch/fable_architecture/.b1/b1_mesh_dryrun
.venv\Scripts\python.exe tools/night_queue/fidelity_pairs.py --designs-file scratch/fable_architecture/.b1/b1_designs.csv --modes verify,finalist --out scratch/fable_architecture/.b1/_dry --dry-run
.venv\Scripts\python.exe -m pytest tests/test_tools_fidelity_pairs.py -q
```
