# Rear-shell density mesh audit (C1) — 2026-11-13

**Scope.** CPU, **mesh only**. No solve of any kind, no GPU, no `gpu-clean`, no queue or night-file
edits. A GPU night (`home80x60_day_2026-11-13`) owns the GPU until 23:30 and was not touched.
**Machine.** Owner Windows checkout `C:/Users/hunte/Hrns/hornlab-search`; interpreter
`.venv\Scripts\python.exe`. Machine numbers live in `TOOLCHAIN.md`.
**Plan:** `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md` (rev 2), §2 C1.
**Tool:** `tools/analysis/mesh_fidelity.py` (merged today, commit `7277795`), schema v1.

**Labels.** `[measured]` = read from a log/artifact produced by this run; `[inferred]` = a
conclusion drawn from measured numbers (scaling/plateau); `PROVISIONAL` = observed once, no
clean-state repeat. Nothing here is a converged-vs-reference or CAD-check fidelity claim; those
are G4/G5.

## 1. Seeds and the 16 configs

Four seeds from existing configs, copied to `examples/studies/rear_density_2026-11-13/` with
**only** `mesh.rear_res_factor` added (`1.0`, `1.5`, `2.0`, `2.5`):

| study stem | seed config | family | why |
|---|---|---|---|
| `osse_modest` | `examples/osse_baseline.yaml` | OSSE | modest 1.4 in OSSE (`epw 6`) |
| `rosse` | `examples/rosse_baseline.yaml` | R-OSSE | rolled R-OSSE, 1 in (`epw 6`) |
| `ath_like` | `examples/typologies/ath_core.yaml` | OSSE (ATH-morph) | ATH CORE-style morph (`epw 8`) |
| `t2_large` | `examples/typologies/meh_2026-10-30/meh_t2a.yaml` | FREEFORM (CAD) | T2 large MEH (`epw 4.2`) |

Files: `examples/studies/rear_density_2026-11-13/{osse_modest,rosse,ath_like,t2_large}_rear{1,1.5,2,2.5}.yaml`.

Diff against each seed: exactly one added line `  rear_res_factor: <f>` under `mesh:` for
`osse_modest`, `rosse`, `t2_large`. For `ath_like` the copied file also needs its relative
`brief_file` corrected (`../briefs/ath_core_2in.yaml` → `../../briefs/ath_core_2in.yaml`) because
the study directory is one level deeper; without it the copy cannot load. No other key changed.
All 16 files load with `load_config` and report the expected factor `[measured]`.

## 2. Mesh-only path (no solve)

`tools/bench/mesh_policy_study.py` was chosen over `hornlab-search run --dry-run` because
`run --dry-run` builds its mesh into a `TemporaryDirectory` and deletes it (`cli.py::_dry_run`), so
it cannot be audited by `mesh_fidelity.py`. `mesh_policy_study.py` calls the production
`build.build_mesh` and only solves when `--solve` is passed (it was **not** passed). It also uses no
mesh cache; output went only to the scratch directory below.

```
scratch = C:\Users\hunte\AppData\Local\Temp\opencode\rear_density_2026-11-13
cache   = <scratch>\cache        (created; unused by the chosen tool, which takes no cache dir)
```

Per config (16 times, all exit 0):

```
.venv\Scripts\python.exe tools\bench\mesh_policy_study.py ^
  --config examples\studies\rear_density_2026-11-13\<stem>_rear<f>.yaml ^
  --mode screen --curvature 0 --out <scratch>\mesh\<stem>_rear<f>
```

`--mode screen` fixes the sizing frequency to the config's screen grid top: 5500 Hz for the three
formula horns, 10000 Hz for T2 `[measured]` (`config.mode_freqs("screen", cfg)`). `--curvature 0`
is the tool's own baseline arm; it is inert on the formula route and is today's default on CAD.
No solve, GPU or cache path was touched.

## 3. Tag map: there is no separate rear physical tag

`mesh_fidelity.py` reports **per physical tag**. For the formula horns the mesher writes only:

* tag `1` = `SD1G0` — every rigid surface (inner bore, outer wall, rear cap, mouth) `[measured]`;
* tag `2` = `SD1D1001` — the driven source `[measured]`.

T2 adds tag `10` = `mid_port_exit_left`. The rear cap and outer shell are **inside `SD1G0`**, so a
separate "rear-tag triangles" and "rear `h_max`" are **not obtainable** from the `.msh` physical
tags, and regions must not be guessed from geometry (A4 rule). Those two plan columns are therefore
recorded as **n/a**; the measured `SD1G0` (wall-tag) triangle count and max edge are given instead,
and `mesh_meta.json` `result.res_mm.rear` gives the rear resolution the mesher actually requested
(it tracks the factor exactly) `[measured]`.

## 4. Fidelity invocation

```
.venv\Scripts\python.exe tools\analysis\mesh_fidelity.py ^
  <scratch>\mesh\<stem>_rear<f>\curv0 --fmax <mesh f_max> --epw <design epw> --out json
```

`--epw` is each design's own `mesh.epw` (6 / 6 / 8 / 4.2), not the tool default 6, so the validity
limit matches the mesh that was built. All 16 runs exit 0.

### Verbatim tool output (samples)

```
mesh: C:\Users\hunte\AppData\Local\Temp\opencode\rear_density_2026-11-13\mesh\osse_modest_rear1\curv0\mesh.msh
triangles: 7476  bbox_m: 0.0000, 0.0000, -0.0060, 0.4011, 0.3209, 0.2600
fmax: 5500 Hz  epw: 6  h_max limit: 10.394 mm
   tag  name                        tris     p50mm     p95mm     maxmm  k*h_max  valid
     1  SD1G0                       7434     9.903    11.022    19.965    2.012     no
     2  SD1D1001                      42     4.488     5.459     6.521    0.657    yes
mesh_fidelity_status: source_valid_only (source tag SD1D1001 passes; failing: SD1G0)
```

```
mesh: C:\Users\hunte\AppData\Local\Temp\opencode\rear_density_2026-11-13\mesh\osse_modest_rear2.5\curv0\mesh.msh
triangles: 5090  bbox_m: 0.0000, 0.0000, -0.0060, 0.4011, 0.3209, 0.2600
fmax: 5500 Hz  epw: 6  h_max limit: 10.394 mm
   tag  name                        tris     p50mm     p95mm     maxmm  k*h_max  valid
     1  SD1G0                       5048     9.267    25.309    35.440    3.571     no
     2  SD1D1001                      42     4.488     5.459     6.521    0.657    yes
mesh_fidelity_status: source_valid_only (source tag SD1D1001 passes; failing: SD1G0)
```

```
mesh: C:\Users\hunte\AppData\Local\Temp\opencode\rear_density_2026-11-13\mesh\ath_like_rear2\curv0\mesh.msh
triangles: 5160  bbox_m: 0.0000, 0.0000, -0.0060, 0.1986, 0.1986, 0.3526
fmax: 5500 Hz  epw: 8  h_max limit: 7.795 mm
   tag  name                        tris     p50mm     p95mm     maxmm  k*h_max  valid
     1  SD1G0                       5069     7.350    10.941    19.333    1.948     no
     2  SD1D1001                      91     3.629     4.324     4.942    0.498    yes
mesh_fidelity_status: source_valid_only (source tag SD1D1001 passes; failing: SD1G0)
```

```
mesh: C:\Users\hunte\AppData\Local\Temp\opencode\rear_density_2026-11-13\mesh\t2_large_rear1\curv0\mesh.msh
triangles: 11776  bbox_m: -0.0000, -0.0000, -0.2157, 0.2032, 0.2032, 0.1643
fmax: 10000 Hz  epw: 4.2  h_max limit: 8.167 mm
   tag  name                        tris     p50mm     p95mm     maxmm  k*h_max  valid
     1  SD1G0                      11541     7.206     9.553    11.375    2.084     no
     2  SD1D1001                      45     3.580     4.935     5.246    0.961    yes
    10  mid_port_exit_left           190     3.859     4.830     5.372    0.984    yes
mesh_fidelity_status: source_valid_only (source tag SD1D1001 passes; failing: SD1G0)
```

## 5. Results table

`total DOF` = mesh vertices `summary.n_nodes_used` (the P1 DOF the solver would see);
`SD1G0 tris` / `SD1G0 h_max` = the measured wall physical tag (rear + outer + inner + mouth —
see §3); `requested rear` = `mesh_meta.json` `result.res_mm.rear`; `DOF saved` = vs that design's
own factor 1.0. All numbers `[measured]` from `<scratch>/fidelity_epw/*.json` and
`<scratch>/mesh/*/curv0/mesh_meta.json`.

| design | factor | total DOF | DOF saved | total tris | SD1G0 tris | SD1G0 h_max (mm) | requested rear (mm) | f_max (Hz) | fidelity status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Modest OSSE | 1.0 | 3850 | 0.0 % | 7476 | 7434 | 19.965 | 10.394 | 5500 | source_valid_only |
| Modest OSSE | 1.5 | 3043 | 21.0 % | 5890 | 5848 | 21.845 | 15.591 | 5500 | source_valid_only |
| Modest OSSE | 2.0 | 2771 | 28.0 % | 5357 | 5315 | 29.660 | 20.788 | 5500 | source_valid_only |
| Modest OSSE | 2.5 | 2635 | 31.6 % | 5090 | 5048 | 35.440 | 25.985 | 5500 | source_valid_only |
| R-OSSE | 1.0 | 1071 | 0.0 % | 2036 | 2009 | 19.307 | 10.394 | 5500 | source_valid_only |
| R-OSSE | 1.5 | 896 | 16.3 % | 1696 | 1669 | 31.340 | 15.591 | 5500 | source_valid_only |
| R-OSSE | 2.0 | 845 | 21.1 % | 1597 | 1570 | 37.625 | 20.788 | 5500 | source_valid_only |
| R-OSSE | 2.5 | 834 | 22.1 % | 1576 | 1549 | 43.306 | 25.985 | 5500 | source_valid_only |
| ATH-like morph | 1.0 | 3232 | 0.0 % | 6174 | 6083 | 13.499 | 7.795 | 5500 | source_valid_only |
| ATH-like morph | 1.5 | 2711 | 16.1 % | 5160 | 5069 | 19.333 | 11.693 | 5500 | source_valid_only |
| ATH-like morph | 2.0 | 2711 | 16.1 % | 5160 | 5069 | 19.333 | 15.591 | 5500 | source_valid_only |
| ATH-like morph | 2.5 | 2709 | 16.2 % | 5156 | 5065 | 19.333 | 19.489 | 5500 | source_valid_only |
| T2 large MEH (CAD) | 1.0 | 6032 | 0.0 % | 11776 | 11541 | 11.375 | 8.167 | 10000 | source_valid_only |
| T2 large MEH (CAD) | 1.5 | 6032 | 0.0 % | 11776 | 11541 | 11.375 | 12.250 | 10000 | source_valid_only |
| T2 large MEH (CAD) | 2.0 | 6032 | 0.0 % | 11776 | 11541 | 11.375 | 16.333 | 10000 | source_valid_only |
| T2 large MEH (CAD) | 2.5 | 6032 | 0.0 % | 11776 | 11541 | 11.375 | 20.417 | 10000 | source_valid_only |

`mesh_fidelity_status` is `source_valid_only` for all 16: the source tag passes at the design's
`epw`; the wall tag fails because it contains the inner bore/mouth, which are not the coarsened
rear region and were already above the limit at factor 1.0 `[measured]`. The status is a whole-mesh
statement, not a rear-region statement.

## 6. Where the guard cancelled the reduction

* **Modest OSSE** — DOF falls at every step (3850 → 3043 → 2771 → 2635). No plateau: the outer-wall
  clearance guard does **not** cancel the reduction through 2.5 `[inferred from the measured DOF]`.
* **R-OSSE** — DOF falls (1071 → 896 → 845 → 834) but 2.0 → 2.5 adds only 1.0 pt for a 25 % larger
  requested rear (20.788 → 25.985 mm): effectively saturated at 2.0 `[measured]`; the remaining
  rear area is small and/or partly capped `[inferred]`.
* **ATH-like morph** — DOF falls 3232 → 2711 at 1.5 and then stops: 2711 → 2711 → 2709 while the
  requested rear rises 11.693 → 15.591 → 19.489 mm. Further coarsening **is cancelled** by a
  constraint other than the requested rear size; the outer-wall clearance guard is the most likely
  constraint `[plateau measured; guard attribution inferred]`. The wall-tag max edge also freezes
  at 19.333 mm across 1.5/2.0/2.5, consistent with a hard cap `[measured]`.
* **T2 large MEH (CAD)** — no effect at any factor: 6032 DOF / 11776 triangles for all four, even
  though `res_mm.rear` grows 8.167 → 20.417 mm. The CAD route (`mesh/step_build.py`) sizes from
  `res_mm["mouth"]`/`res_mm["throat"]` only; `rear_res_factor` is a **no-op on the CAD/MEH route**
  `[measured]`.

T2 CAD mesh warning, verbatim from the build (pre-existing; not caused by the factor):

```
cad mesh: requested max frequency exceeds conservative global mesh limit (10000 Hz > 5025.51 Hz); global coarse regions are reported but only active source patches hard-fail; driver rigid walls within the transition distance are underresolved for 10000 Hz (wall valid 5240.94 Hz, patch valid 10896.3 Hz); entry_mid rigid walls within the transition distance are underresolved for 10000 Hz (wall valid 5104.5 Hz, patch valid 10640.8 Hz); the mesh is written with the frequency report on its record
```

## 7. Recommendation for G4

**Test `rear_res_factor` 1.5 and 2.0.** 1.5 is the largest factor that lowers DOF on every formula
horn with no plateau (OSSE −21.0 %, R-OSSE −16.3 %, ATH-like −16.1 %); 2.0 adds 7.0 pts on OSSE and
4.8 pts on R-OSSE, but the ATH-like horn is already flat at 16.1 % from 1.5 (requested rear
11.693 → 15.591 mm with 0 DOF change), and 2.5 adds only 3.5 pts on OSSE / 1.0 pt on R-OSSE while
raising the wall max edge to 35.4 / 43.3 mm. T2 is excluded from the factor decision on mesh
evidence: the CAD route ignores the factor.

This rests on the measured DOF/triangle table in §5 and the plateaus in §6; it is a **mesh-resolution
recommendation only**. G4 still has to pass the acoustic bars (beamwidth ≤ 2°, DI ≤ 0.2 dB, ReZ
≤ 0.03 normalized) against 1.0 and a finer reference.

## 8. Caveats and what was not measured

* **No acoustic result.** This audit measures mesh size/resolution only. It says nothing about
  on-axis pressure, beamwidth, DI or throat impedance; that is G4.
* **Screen mode only.** `--mode screen` (f_max 5500 / 10000 Hz). Verify/final meshes would use a
  higher f_max and are not covered here.
* **No per-rear-region edge statistics** are possible with the current tag contract (§3). The
  `SD1G0` numbers are a whole-wall proxy. The mesher's `outerWallClearance.capActive` flag is not
  persisted by `build.build_mesh` into `mesh_meta.json`, so guard activation is inferred from the
  DOF plateau, not read directly.
* **No T2 skip needed:** the T2 CAD mesh built in ~3 s, far under the 10-minute cap.
* **Artifacts** (`.msh`, `mesh_meta.json`, `fidelity_epw/*.json|*.txt`) live only in the scratch
  directory above; nothing was written to `runs/`, an existing cache, or the dataset.
* Per the C1 write scope, `docs/INDEX.md` / `docs/CODE_MAP.md` were **not** touched; the integrator
  should add this doc to `docs/INDEX.md` in the commit.

## 9. Run log (exit statuses)

| step | command class | count | exit |
|---|---|---:|---:|
| config generation | Python copy + insert `rear_res_factor` | 16 files | 0 |
| config load preflight | `load_config` on all 16 | 16 | 0 |
| mesh (formula) | `mesh_policy_study.py --curvature 0` (no `--solve`) | 12 | 0 |
| mesh (CAD T2) | `mesh_policy_study.py --curvature 0` (no `--solve`) | 4 | 0 |
| fidelity | `mesh_fidelity.py --fmax --epw` | 16 | 0 |

Build wall times: formula horns 1.1–2.6 s each; T2 CAD 3.9–4.0 s each `[measured]`, so no timeout
and no skipped config. No config failed to mesh.
