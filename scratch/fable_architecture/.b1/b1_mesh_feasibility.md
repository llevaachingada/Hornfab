# B1 mesh convergence — CPU sizing feasibility (no solves)

Prepared 2026-11-18 against the owner decision: **B1 tests MESH convergence**, not frequency
fidelity. All ten designs from `b1_selection.md` are sized here on CPU with the real mesher
(`hornlab_search.mesh.build.build_mesh`, gmsh); **no BEM solve ran, no GPU lock was taken**.

Fixity (same for every candidate):
- same ten designs, same home brief, same objective v7, same source/mounting, same run config;
- the **same screen frequency grid as the reference solve** — the refined solve's `SolveSpec` hash
  is asserted equal to the stored row's (the grid, backend, observation and tolerances are
  byte-identical; only `MeshSpec` changes);
- the **only** change is `mesh.epw` × factor. `mesh/sizing.py` derives throat `res/2`, mouth
  `res`, rear `res` from `epw` and `f_max`, so all three tighten at unchanged `f_max`.
- `quadrants` is untouched (all ten are `1` = quarter, with the config's own symmetry plane).

Reference = the stored screen row (not re-solved). For the sizing dry run the reference mesh was
rebuilt at the stored `epw`; all ten **reproduce the stored triangle/DOF counts exactly** (a
reproducibility check on the build path).

## Command

```
.venv\Scripts\python.exe tools/night_queue/fidelity_pairs.py --designs-file scratch/fable_architecture/.b1/b1_designs.csv --dry-run --build-meshes --refine-factors 2,3 --out scratch/fable_architecture/.b1/b1_mesh_dryrun
```

Output: `b1_mesh_dryrun/mesh_dryrun.json`, log `b1_mesh_dryrun.log`, meshes under
`b1_mesh_dryrun/meshes/`. Exit 0: 10/10 reference builds succeeded; 12 refined candidate builds
were refused (the findings below).

## Feasibility table (realized triangles / quarter-domain DOF)

Measured ceiling (TOOLCHAIN M2, 8 GB RTX 4060): **quarter-domain OOM transition 8.9 k–15.7 k DOF**
(full-domain 5.5 k–9.2 k; memory pressure above ~5 k). Verdict rule: ≤8.9 k fits · 8.9–15.7 k
*borderline* · >15.7 k **mesh check infeasible on this card**.

| design | config | ref tri / DOF | x2 (epw 12) tri / DOF | x3 (epw 18) tri / DOF | cap-bound? | verdict |
|---|---|---|---:|---:|---|---|
| `2f7307c06023` | fold_warm | 7 220 / 3 751 | 28 489 / **14 530** | 65 246 / 33 276 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `507e7257c091` | fold_warm | 7 304 / 3 791 | 28 547 / **14 559** | 63 799 / 32 538 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `ced63c6a01a1` | fold_warm | 7 408 / 3 844 | 28 979 / **14 780** | 64 739 / 33 017 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `688ffe811b6a` | fold_warm | 7 313 / 3 796 | 29 221 / **14 903** | 63 877 / 32 578 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `78f599e8a1d2` | fold_warm | 7 391 / 3 837 | 28 859 / **14 719** | 64 521 / 32 906 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `3a1038da45d0` | ext_throat_v7 | 10 175 / 5 275 | refused (geometry) | refused (geometry; cap-bound) | x2 no · x3 **yes @24 k** | **mesh check infeasible on this card (est. 21 100 / 47 475 DOF)**; mesher refuses at epw 12/18 |
| `9fcd21fc1904` | ext_throat_v8 | 10 173 / 5 274 | refused (geometry) | refused (geometry; cap-bound) | x2 no · x3 **yes @24 k** | **mesh check infeasible on this card (est. 21 096 / 47 466 DOF)**; mesher refuses at epw 12/18 |
| `766c9b1ba8a9` | ext_throat_v7 | 7 149 / 3 725 | 27 953 / **14 270** | 62 439 / 31 844 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `508f907726d3` | ext_throat_v7 | 7 685 / 3 999 | 30 164 / **15 388** | 67 421 / 34 385 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |
| `b996da551021` | ext_throat_v7 | 7 714 / 4 009 | 30 081 / **15 342** | 96 642 / 49 288 † | x2 no · x3 **yes @24 k** | x2 borderline (needs a probe) · x3 infeasible |

† **x3 is cap-bound at the job's 24 000-DOF screen cap** (the pre-mesh estimate is over 1.5× the
cap; `build.py` refuses before meshing). The x3 triangles/DOF are the *diagnostic* build with the
cap lifted only to size it — **the approved job cannot build x3 at the existing cap**, and the true
size is far past the card anyway.

**Read the table carefully:** the failure mode is design-dependent, not just VRAM:
- **fold-warm x2** builds at the existing cap. It lands at 14.27–15.39 k DOF — inside the measured
  8.9–15.7 k OOM transition but *under* its upper edge and *under* the 24 k cap. These are
  **probe-grade**: they must be measured one at a time with the Shared Usage check, and any spill
  invalidates that design.
- **ext-throat x2** does not build: the mesher refuses at epw 12 with
  `23 non-sliver triangle(s) lie entirely in the x=0 symmetry plane; the geometry is defective`
  (a resolution-induced topology refusal, not a cap or VRAM refusal). Its estimate (~21.1 k DOF)
  is over the card's quarter ceiling anyway, so it is **infeasible on this card** for two reasons.
- **x3** is cap-bound for all ten and 31.8–49.3 k DOF if the cap is lifted — infeasible on the
  card and not obtainable at the existing cap. Rejected as the default.

## Cap behaviour (checked in `hornlab_search/mesh/build.py`)

`max_triangles = max_triangles_for(dof_cap, quadrants, dof_per_triangle, slack)` is a **budget**,
not a refinement target:
- pre-mesh: refuse when the estimate is over **1.5 × cap** (`PREMESH_MARGIN = 1.5`, line 387);
- post-build: `_check_dofs` raises `MeshTooLargeError` when
  `max(estimate_dofs, n_nodes_used) > cap` and deletes the mesh (line 250).

The mesher never silently truncates or coarsens to fit; a cap-bound candidate is simply not built.
That is why x3 is reported as **cap-bound** rather than as a "refined" mesh.

## Recommendation

**Default = x2 (epw 12), fold-warm designs only, probe-grade.** x3 has the better discretization
precedent (epw 6-vs-18 is exactly the 0.028 dB DI number at `report/html.py:59`) but is not
reachable on this card: it is cap-bound at 24 k and its true size is 2–3× the quarter OOM ceiling.
For the five fold-warm designs, x2 roughly **3.9× the triangles and 3.9× the DOF** (not the naive
4×) and is the only candidate that builds at the existing cap.

The five ext-throat designs are **excluded** from the B1 mesh conclusion: marked *mesh check
infeasible on this card* with their estimated DOF (and the mesher's geometry refusal at epw 12).

## Per-term data available for the solve report

The stored `search.ndjson` rows **do carry per-term and per-metric values** (checked on
`78f599e8a1d2`):
- `terms`: normalized weighted terms `cov, rip, di, dislope, flat, load, distd, diag, flat_cv,
  penalty, total` plus `n_in_band`, `lfp20_hz/lfp50_hz`, `rez_min_from_fx`, `f11_hz`.
- `metrics`: per-frequency arrays `freqs_hz, bw_h_deg, bw_v_deg, di_db, ripple_h_db, ripple_v_db,
  on_axis_db, z_throat_real`, plus `scalars` and `di_source` (`balloon` on these rows).

So the reference does not need a re-solve: the tool compares the stored row directly with the
refined solve, reporting ΔJ, Δ(weighted term) for all ten terms, and Δ of the mean in-band H/V
beamwidth, DI and ripple (`metric_summary`). The measured noise-floor inputs are
`report/html.py:59 NOISE_FLOOR_INPUTS`: solver idempotence 3.6e-5 dB, symmetry 4e-6 dB,
full-vs-quarter 0.023 dB, **epw 6-vs-18 DI 0.028 dB** (measured on 500–2500 Hz only; above 2.5 kHz
unmeasured), two-solver 0.039 dB. The J-level mesh-sensitivity threshold is the smallest
non-degenerate adjacent finalist gap in the ten-design set: **0.0057 J** (`766c…` vs `508f…`),
passed explicitly to the job (`--gain-threshold 0.0057`) because per-design jobs see one design.

## Proposed B1-mesh night jobs (APPROVED-FOR-GPU FORM — not inserted)

Five per-design jobs (one fresh process per measurement), queued **after the current BO arms**, only
after owner approval. Each job:

```yaml
- id: b1_mesh_<design>
  kind: command
  timeout_s: 10800
  env:
    HORNLAB_GPU_LOCK: refuse
  argv:
  - .venv/Scripts/python.exe
  - tools/bench/run_with_memwatch.py
  - --out
  - runs/nights/b1_mesh_2026-11-18/memwatch/b1_mesh_<design>.json
  - --
  - .venv/Scripts/python.exe
  - tools/night_queue/fidelity_pairs.py
  - --design
  - runs/<run>:<design>
  - --refine-epw-factor
  - '2'
  - --teardown-per-design
  - --record-vram
  - --gain-threshold
  - '0.0057'
  - --out
  - runs/b1_mesh_2026-11-18
```

The full five-job file is `b1_mesh_night_insert.yaml`. Hygiene encoded:
- **fresh process per measurement** (one night job per design);
- `--teardown-per-design`: `worker.shutdown(verify=True)` after each design, which raises
  `WorkerReleaseError` if a host survives (the tool then exits nonzero);
- `--record-vram`: per-design `GpuMemPeak` baseline + peak device memory + the host tree's
  dedicated **and SHARED** usage; `spilled` (shared > 512 MiB) marks the design failed;
- `run_with_memwatch.py` wraps each job for an independent dedicated/shared record;
- per-design baseline is recorded before the solve; a spilled design is excluded, not silently
  kept;
- the night runner's own pre/post `gpu-clean` and timeout still apply;
- all five jobs share `runs/b1_mesh_2026-11-18/refine.json`; the tool **merges** each per-design
  invocation into it (a re-run replaces that design's entry), so the five records accumulate.

## Judgment calls / open questions

1. **x2 is a probe, not a comfortable fit.** 14.3–15.4 k DOF sits inside the measured 8.9–15.7 k
   OOM transition. The per-design Shared Usage record is the arbiter; if the first fold-warm probe
   spills, B1-mesh is not feasible on this card at x2 either and the conclusion is "not measurable
   on this GPU".
2. **ext-throat is excluded for a geometry reason as well as VRAM.** The mesher refuses the finer
   mesh (`non-sliver triangle(s) in the symmetry plane`); a future mesher fix or a different
   surface fit could change this, but no new mesher key was invented here.
3. **x3 is rejected**, despite the 0.028 dB precedent, because the cap binds and the true size is
   31.8–49.3 k DOF. A different factor between 2 and 3 was not requested and was not probed.
4. **Single-design J threshold.** Per-design jobs cannot derive the inter-finalist gap from one
   row, so the job passes the ten-design value (`0.0057`). If the owner prefers a stricter rule,
   use the noise floor's dB terms for the metric deltas (0.028 dB) and the same 0.0057 for J.

---

## 2026-11-18 correction (local orchestrator, WP 2.2 / R5; fixes the "Recommendation" paragraph above)

The "Recommendation" paragraph says **"The five ext-throat designs are excluded"** — that count is
wrong. Only **`3a1038da45d0` (v7 leader) and `9fcd21fc1904` (v8 incumbent)** are infeasible on this
card; the other three ext-throat designs — `766c…`, `508f…`, `b996…` — are **probe-grade** and are
the subjects of batch 2 (`docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml`,
owner decision R5, conditional on batch 1 probe 1 not spilling Shared Usage). The B1 packet README
(`docs/evidence/b1_readiness_2026-11-18/README.md`, commit `681e429`) already states this; the
feasibility doc's five-design wording predates it. Batch 2 does NOT include the two leaders — the
v7/v8 incumbents remain outside the mesh floor on this card (WP 2.3 will state that).
