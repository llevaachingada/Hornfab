# HornLab + Horn/Woofer System — Complete Senior Handoff Handbook

**Snapshot:** 2026-11-19 (evening US Eastern); canonical checkout `C:/Users/hunte/Hrns/hornlab-search`,
branch `hornfab-all-2026-11-18`, HEAD at scan time `ddfba68`. The tree also contains uncommitted GUI
work from another lane; this handbook documents the working tree as found, and flags where the
committed state differs.

**Post-handbook update (2026-11-20):** the owner authorised and the local orchestrator ran the
`system_evidence_2026-11-19` CPU queue (LF 20–200 Hz, 2×2 motor×box, 10 m vs 2 m, 25 vs 49
frequency sampling, screen replay). Current census: **47 case dirs / 14 solved / 29 staged /
3 refused / 2 invalid**; readout and caveats in
`docs/evidence/system_evidence_2026-11-19/README.md`. The §0/§6 counts below are the pre-queue
snapshot; use the evidence/export files for current numbers.

**Audience:** a senior architecture/implementation agent working in the cloud, with no access to the
local `runs/`, `system_runs/`, GPU, or Boundary Lab install. The goal is that you can plan the final
architecture and next implementation round **without re-reading the repository or re-deriving the
session**.

**What this one file covers**

1. The pure horn search engine (design → mesh → solve → metrics → objective → dataset/report).
2. The horn + vented-woofer system layer (CPU screen → Boundary Lab stage/validate → coupled solve →
   DSP/recombination), including every schema and configuration key.
3. The current GUI/UX, route by route, control by control, with implemented vs backend-only vs planned.
4. The solve/computational data package and the two reusable export scripts.
5. Remaining implementation, owner decisions, known front-end/back-end issues, doc drift, and
   architecture recommendations.

**What this file is not:** a new acoustic claim, a replacement for the frozen contracts
(`docs/plan/01_CONTRACTS.md`), or a licence to rank J across objective versions. Where a number is
quoted, its label `[measured]`, `[inferred]`, or `provisional` is preserved.

**How this was produced:** read-only recon of the canonical tree, plus synthesis of the system
research docs and living logs. Code claims were checked against code where cheap; doc claims that
could not be checked are marked. The generated data exports were verified by loading them.

---

## 0. Two-minute executive summary

### 0.1 The three products in one repository

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. PURE HORN SEARCH (mature)                                                │
│    YAML brief/config → design generator → gmsh mesh → BEM solve (CUDA/CPU)  │
│    → metrics → objective J (v1..v10) → CMA-ES → run dir + dataset record    │
│    Outputs: runs/**, dataset/**, docs/top_designs/**                        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ saved horn asset (design.json, mesh.msh,
                                │ response.npz, status.json, run.json)
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. HORN + VENTED-WOOFER SYSTEM (v0 research, CPU-only)                      │
│    system spec + saved horn + driver T/S + box ranges                       │
│    → CPU screen/Pareto (woofer_seed)                                        │
│    → Boundary Lab stage/validate (real BL 0.5.0, its own interpreter)       │
│    → coupled BEM/FEM solve (beat_cpu; 2 independent excitations)            │
│    → per-excitation complex bases → DSP replay / (refused) coherent sum     │
│    Outputs: system_runs/** (gitignored, immutable, sha-self-checked)        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ case manifests, run manifests, screen studies
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. GUI (stdlib server + vanilla JS; 127.0.0.1 only)                          │
│    Horn side: Home, Runs, Campaigns, Elites, Compare, Analysis, Briefs,      │
│    Typologies/sandbox, New run (Compose/Launch), Bayes, Status, Glossary     │
│    Horn+woofer side: Screens, Screen detail, Cases, Case detail, Readiness   │
│    G0/P1/P2 shipped; P3/P4/P5 backends partly wired; P6-P9 remain            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 0.2 Current status in numbers

| Area | Number / state | Source |
|---|---|---|
| Dataset records | **42,179** (36,016 ok, 6,163 failed) in 85 shards | `hornlab-search dataset stats`, 2026-11-19 |
| Dataset families | OSSE 17,776 · FREEFORM 21,649 · R-OSSE 1,730 · ICW 1,024 | same |
| Search runs | **710** timestamped run dirs under `runs/` (866 directories total incl. non-runs) | filesystem |
| GPU-solve export | **807** `search.ndjson` files, **51,192** rows scanned, **43,379** GPU rows, **37,588** unique scored physical solves | `docs/top_designs/README.md` |
| Top-design bundle | **52** `(typology, score-set)` groups, **437** selected designs, 437/437 with stored response arrays | `docs/top_designs/top_designs.json` |
| System cases | **37 case dirs**: **5 solved**, **27 manifest-only**, **3 refused**, **2 invalid/empty**; among the 9 readiness-declared solve cases: **5 solved**, **2 solve-relevant staged**, **1 BL refusal**, **1 proven clearance violation** | `docs/system_data/system_cases.json` + `readiness.yaml` |
| System screens | study `65f6db3e8c8e8f86` (pre-panel-fit), `27616eedee09009f` (re-ranked), portfolio `1a509f87c01fd6fd` | `SCREENING_EVIDENCE.md`, `PORTFOLIO_EVIDENCE.md` |
| Current GPU lane | free at the last recorded check; a live compact400 night had been appending solves | `docs/ACTIVE_STATE.md`, `docs/CONTINUITY.md` |
| Current system GUI | `#/hw/screens`, `#/hw/screen/<id>`, `#/hw/cases`, `#/hw/case/<exp>/<case>`, `#/hw/readiness` | `gui/static/app.js` ROUTES |
| Missing GUI views | Overview, New system wizard, Compare UI, Crossover UI, stage/validate/solve actions (backends exist in part) | `docs/.../GUI_COMPLETION_HANDOFF` |

### 0.3 The five things that matter most

1. **The horn engine is mature; the system layer is a v0 research bridge.** The horn side has tens of
   thousands of scored GPU solves and a frozen data/provenance discipline. The system side has five
   solved coupled cases and no scalar system objective.
2. **The horn and woofer channels are not comparable references.** Woofer bases are Pa per 2.83 V;
   the horn is an ideal normal-velocity source per 1 m/s. `combine()` correctly refuses a coherent
   sum without an explicit calibration record (risk **R1**). Every cross-channel number is therefore
   manual/illustrative, not a system score.
3. **Every "BL-buildable" box today is conditional on Boundary Lab's demo transducer shape.** The real
   12PR300 Sd-derived moving diameter (0.2605 m) cannot coexist with the recorded port on the
   371.2 mm front: 0.1821 m required vs 0.1501 m available (risk **R2**). Real-shape staging needs
   maker CAD/measurement and a taller-panel re-screen.
4. **No data exists below 200 Hz.** Every solved grid starts at 200 Hz, so box tuning (Fb ≈ 30–53 Hz)
   and the LF alignment are invisible (risk **R3**). A cheap 20–200 Hz request overlay on the
   existing cases is the next measurement.
5. **The GUI has more backend than front-end.** P2 screens and P3/P4/P5 backends exist and are tested,
   but the nav exposes only Screens/Cases/Readiness; the wizard, compare page, 3D viewer wiring,
   stage actions, solve gate, and crossover page are incomplete (P6–P9).

### 0.4 Owner decisions still open

| # | Decision | Why it blocks |
|---|---|---|
| 1 | Accept the demo transducer shape for v0, or procure 12PR300 maker CAD now? | Gates all real box-axis/installed-geometry work (R2, WP7). |
| 2 | Allow taller fronts (e.g. 560 mm) and re-screen, or keep 371 mm and select drivers that fit? | Both paths need real geometry; the 371 mm front is the binding constraint. |
| 3 | Channel-calibration policy: explicit per-channel calibration records vs velocity-driven re-solves vs electrodynamic conversion? | Blocks the coherent system sum, DSP ranking, and the crossover page (R1, WP4). |
| 4 | Keep analog DSP prototypes this round, or add a digital biquad realization now? | Blocks digital-realization claims; analog prototypes are already implemented (R8). |
| 5 | Far-field/observation standard (distance, angular grid, seat window) | Blocks any declared listening-window curve or DI/power claim (R5). |
| 6 | BL solve authorization record shape (who/why/scope; typed registry vs free string) | Blocks GUI-launched solves and any batch solve policy (R14). |

GUI-specific gates **B** and **C** were answered "Yes to both (Recommended)" and "Yes (Recommended)":
the GUI may launch CPU screen jobs and write user specs; GUI-launched CPU stage + validate is allowed.
Solve remains disabled until decision 6. Gates **D**/**E** are decisions 6/3. See §7.4.

### 0.5 Recommended first hour for a cloud senior

1. Read this file §§1–5 for the mental model (backend + GUI), then §6 for the data package.
2. Read `docs/research/system_woofer_2026-11-18/SENIOR_REVIEW_HANDOFF_2026-11-19.md` §2–§7 (the risk
   register and work packages this handbook reconciles).
3. Load `docs/system_data/system_cases.json` (the compact system census) and
   `docs/top_designs/top_designs.json` + `docs/top_designs/top_designs_acoustics.npz` (the horn
   solve corpus). Do **not** try to fetch `runs/` or `system_runs/`; they are local-only.
4. Confirm the invariants in §2.3 before proposing any score, sum, or ranking change.
5. Use §7 as the work queue and §8 as the defect list; do not re-litigate the non-goals in §7.6.

---

## 1. Repository and system map

### 1.1 Canonical paths

| Path | What it is | Cloud-visible? |
|---|---|---|
| `hornlab_search/` | Python package: design/mesh/solve/metrics/objective/search/dataset/report + `system/` + `gui/` | yes |
| `examples/` | Horn configs, briefs, typologies, drivers, system specs | yes |
| `docs/` | Plans, research, evidence, generated reference tables, this handbook | yes |
| `tests/` | Offline + env-gated real-solver tests | yes |
| `tools/` | Operational scripts (`tools/data/top_designs.py`, `tools/data/system_cases.py`, GUI checks, render, queue) | yes |
| `runs/` | 710+ local search run dirs; full complex `response.npz`; **gitignored** | no |
| `dataset/` | 42,179-record training/solve store; 7.9 GB; gitignored? (index/shards present locally) | partially exported |
| `system_runs/` | System cases, screens, full-domain horn meshes; gitignored; Windows junction in the canonical tree to the worktree store | no |
| `docs/top_designs/` | Committed export of the best GPU-solved horn designs | yes |
| `docs/system_data/` | Committed export of the system cases/screens (companion script) | yes |
| `C:/Users/hunte/Github/boundary-lab` | Installed Boundary Lab 0.5.0 @ `15f9a892…`; read-only, invoked through its own interpreter | no |

The umbrella rule still binds: `hornlab-woofer-system-wt/`, `forks/`, `consolidation-backup-*`,
`hf_stage_hunter*`, archived copies are provenance, not current execution paths. The canonical
checkout is the only current tree. The system store was moved/joined into the canonical tree during
P0; `system_runs` is a directory junction to the worktree store, so the absolute paths inside
manifests still resolve.

### 1.2 The two GPU/CPU lanes

- **Horn search GPU lane:** one CUDA BEM solve at a time, machine-wide. `HORNLAB_GPU_LOCK=refuse` for
  nights/measurements/checkpoints; default is `warn`. Persistent Julia hosts hold ~1 GB VRAM each;
  `gpu-clean` before measurements.
- **CPU lane:** a CPU-backend search and the system `beat_cpu` work can run beside the GPU lane. Lane
  identity is the BEAT worker registry directory; do not kill processes by image name.
- **System solves are CPU** (`beat_cpu`) in every recorded case. They do not take the GPU lock.

### 1.3 The entity model

| Entity | Definition | Where it lives | Key identity |
|---|---|---|---|
| `Design` | A parameter set for a horn family/generator | `design/space.py`, `design/generated.py` | `design_hash` |
| `Mesh` | gmsh mesh in metres, with groups and symmetry | `mesh/build.py` | `mesh_hash` |
| `Solve` | One BEM response for a design/mesh/spec | `solve/*` | `solve_hash` |
| `Response` | SPL cuts, balloon, complex pressures, throat impedance, meta | `solve/base.py`, `response.npz` | content |
| `Run` | A search/verify invocation with config, budget, best, ndjson | `runs/<UTC>-<mode>-<id>/` | `run_id`, `config_sha` |
| Dataset record | One frozen solve record with params/metrics/objective/lib SHAs | `dataset/shard-*.jsonl` | `design/mesh/solve` hashes |
| `HornAsset` | A saved horn solve exposed to the system layer | `system/horn_assets.py` | `asset_id` (domain-separated sha16) |
| `SystemSpecV1` | The system experiment YAML | `examples/systems/*.yaml` | schema v1 |
| `Case` | One immutable system run/stage dir with self-checksummed manifest | `system_runs/system/<exp>/<case>/` | `<exp>/<case>` |
| `Screen` | A deterministic CPU seed study | `system_runs/woofer_seed*/woofer_seed.json` | `study_id` |
| `BL project` | Boundary Lab PhysicalSystem project | `<case>/case.blab.json` | `project_sha256` |
| `BL run` | A headless BL solve result tree | `<case>/run/` | `run/manifest.json` SHA |
| DSP point | LR/PEQ/delay/polarity settings | `system/dsp.py` | point dict |

### 1.4 Vocabulary that is easy to confuse

| Term | Not to be confused with |
|---|---|
| **Horn side** | The pure horn search engine (`runs/`, `dataset/`). |
| **System side** | The horn + vented-woofer assembly (`system_runs/`). The GUI's existing "System" nav group means host/status, not this. |
| **HornFab** | The working name for the horn+woofer system/GUI workstream and its knowledge base; it is not a separate code package in this repository. |
| **Screen** | A CPU heuristic shortlist (no solver, no winner). Not a BEM solve and not a measurement. |
| **Verify** | A horn-side re-solve of top designs at higher fidelity. Not a Boundary Lab validate. |
| **Validate** | Boundary Lab's own project validation (`blab project validate`), not our screen. |
| **Solve** | One frequency-domain BEM solve (horn side) or one coupled BL run (system side). |
| **Combine** | Coherent complex sum of the two per-excitation bases; refused across mixed per-input references. |
| **Recompose** | The reference report's recorded illustrative sum with explicit per-channel calibration; not a system score. |
| **Fidelity label** | `SCREEN_MAGNITUDE`, `SCREEN_COMPLEX_APPROX`, `INSTALLED_EXTERIOR_BEM`, `COUPLED_VENTED_FEM_BEM_LEM`, `MEASURED_VALIDATED`. Never inferred in JS. |

---

## 2. Binding conventions and invariants

### 2.1 Units, phasors, references

| Quantity | Horn side | System/BL side |
|---|---|---|
| Geometry | Mesher writes **metres**; `SolveConfig(mesh_scale=1.0)`; bbox guard 0.1–1 m in `mesh/build.py` | BL expects metres; imported horn mesh `scale_factor 1.0`; `full_domain` enforces 0.1–10 m |
| Drive | Stored responses: **unit normal acceleration**, `exp(-iωt)` | Horn channel: **ideal normal velocity** per **1 m/s**, `exp(+iωt)`; woofer: **Pa per 2.83 V rms** |
| Phase | Stored `p_*` is acceleration/`exp(-iωt)`; conversion via `compare.hornfab_side.accel_to_canonical` (`np.conj(p·(-1jω))`) | `combine()` phase-once rule; no spatial phase factor; refuses mixed per-input refs |
| Impedance | `z_throat`, ohms; `meta` carries the convention | Not used in the system sum |
| SPL | `spl_h_db`/`spl_v_db`/`spl_balloon_db`; relative curves | BL `exterior_pressure` Pa; per-excitation axis 0 |
| Frequency | Screen 500–10k (12), verify 300–16k (25), final 250–20k (36), finalist 300–16k (36) | Recorded grids: 3 freqs (250/700/1100), 25 log 200–2500 Hz; **no <200 Hz** |

### 2.2 Fidelity ladder

| Label | Meaning | What may be claimed |
|---|---|---|
| `SCREEN_MAGNITUDE` | Stored magnitudes only; no phase | Relative shape/level trends |
| `SCREEN_COMPLEX_APPROX` | Converted complex basis with a declared approximation | Relative phase/delay screening only |
| `INSTALLED_EXTERIOR_BEM` | BL exterior BEM of the installed geometry | Installed exterior response |
| `COUPLED_VENTED_FEM_BEM_LEM` | BL coupled vented enclosure + BEM exterior + lumped motor | Coupled per-excitation bases; not absolute system SPL |
| `MEASURED_VALIDATED` | Physical measurement | Never granted in this repo yet |

`drivers.geometry_completeness` refuses `INSTALLED_*`/`MEASURED_*` when cone depth/surround/cap/mounting
depth are missing. `bl_results.to_system_response` refuses to guess a label; the GUI reads fidelity
from `readiness.yaml` only, else shows `UNDECLARED`.

### 2.3 Invariants (do not violate)

1. **One GPU BEM solve at a time.** CPU system work may run beside it.
2. **Never write a solver/mesher/gmsh writer/Green's function/plot library.** Extend via pinned forks.
3. **Never change a frozen contract** (`docs/plan/01_CONTRACTS.md`).
4. **J is minimised and comparable only within one objective version** (and ideally one
   `score_config_sha`). Absence of `objective_version` means v1.
5. **Never sum the woofer and horn channels** without an explicit recorded calibration; the two
   references are not comparable.
6. **Never infer a fidelity label, real-vs-demo motor, or transducer shape.** Undeclared is
   `UNDECLARED`.
7. **Refusal tokens are shown verbatim**, with a plain-English gloss; never hidden or rephrased.
8. **No Boundary Lab solve without an authorization record.** `authorized_by` must be non-empty;
   `run.solve_project` is intentionally inert.
9. **System jobs are CPU-only** (`beat_cpu`); the GUI never takes the GPU lock.
10. **Every system case is immutable and sha-self-checked.** A failed solve still writes a record;
    retrying requires a new case dir.

### 2.4 The three silent killers (horn side)

| Killer | Guard |
|---|---|
| Wrong `mesh_scale` (metres vs mm) | `SolveConfig(mesh_scale=1.0)`; bbox assert 0.1–1 m |
| Quadrants vs symmetry flag disagree | both derive from one source; tested together |
| DI from cuts labelled as real DI | `MetricSet.di_source` = `balloon` or `cuts_estimate`; no checkpoint passes on `cuts_estimate` |

---

## 3. Pure horn backend (the engine the system consumes)

### 3.1 Pipeline

```
YAML config/brief
  → DesignSpace / generator materialise      design/space.py, design/generated.py
  → build_mesh (gmsh, metres, dof cap)       mesh/build.py
  → solve (beat_cuda/beat_cpu/bempp)          solve/beat.py, solve/bempp.py
  → compute_metrics (beamwidth, DI, ripple)   metrics/compute.py
  → objective J (versioned scalar)            objective/scalar*.py
  → search (CMA-ES / CMA-ME)                  search/cma.py, search/evaluate.py
  → run dir + dataset record                  search/rundir.py, dataset/store.py
  → report (HTML)                             report/html.py
```

Side-effect order is fixed in `search/evaluate.py:6-9`: the **dataset record is committed before the
ndjson line**, so a crash loses a log line, never a training record.

### 3.2 Typologies and generators

Two layers:

- **Native mesher families** (`design/families.py:280`): `OSSE`, `R-OSSE`, `ICW`, `FREEFORM`.
  Each has its own legal key set and refuses keys from another family.
- **Generator recipes** (`design/generators/registry.py:77`): `conical`, `exponential`, `hypex`,
  `tractrix`, `lecleach`, `spherical_wave`, `osse`, `splice`, `spherical_salmon`, `biradial`,
  `qtw_waveguide`; mouths `ellipse|superellipse|rounded_rectangle`; point-grid/rows types
  (`design/generators/grid.py:140`): `salmon_elliptical`, `salmon_axisym`, `lecleach`, `iwata_ar`,
  `toroidal_rollback`, `lecleach_mod`, `lecleach_ar`, `lecleach_asym`, `osse_rollback`.
- **Special generators**: `grid`, `plughorn`, `meh` (CAD), `crowe_hv_area_aspect_v1`, plus
  rolled/Klangfilm/Le Cléac'h swept-HV/record-body families.
- **MEH** is not a family; it is enabled by a `meh:` block in the brief (`config.py:116,281`).

The authoritative generated knob table is **`docs/reference/TYPOLOGIES.md`** (2,204 lines, generated by
`tools/gen_param_catalog.py`; per-typology knob/unit/default/search/hard-lo/hi) and
`docs/reference/PARAMETERS.md`. The GUI consumes `gui/static/param-catalog.v1.json`, byte-checked by
`tests/test_param_catalog.py`. The `reference/TYPOLOGIES.md` path named in some prompts does not
exist; use `docs/reference/`.

### 3.3 Horn config schema

Required top-level keys (`config.py:1685`): `name`, `family`, `seed_params`, `bounds`, `target`,
`weights`, `mesh`, `solve`, `search`.

| Block | Key fields | Notes |
|---|---|---|
| `seed_params` | one value per design parameter | units mm/deg; bounds are real units |
| `bounds` | `{key: {lo, hi, search, log}}` | search needs `lo<hi`; log needs `lo>0` |
| `mesh` | `epw`, `quadrants`, `dof_cap_screen/verify/final`, `dof_per_triangle`, `max_triangle_slack`, `rear_res_factor`, `band_split`, `curvature_npts` | `MeshSettings` |
| `solve` | `backend`, `distance_m`, `angle_count`, `balloon`, `balloon_points_*`, `gmres_tol`, `timeout_s`, opt-in `cuda_fused`, `source_motion`, `near_correction*`, `solve_precision`, `source_profile_alpha`, `julia_threads`, `freq_batch_size` | `SolveSettings` |
| `search` | `algorithm` (`cma`/`cma_me`), `sigma0`, `seed`, `budget`, `popsize`, `tolfun`, `infeasible_penalty` (`flat/graded/resample/resample_strict`), `restarts`, `qd`, `pipeline_prefetch`, `budget_counts`, `max_attempts`, `links`, `warm_start`, `surrogate`, `error_policy`, `record_gate` | `SearchSettings` |
| `target` | band, coverage H/V, DI target/slope, etc. | objective inputs |
| `weights` | `cov`, `rip`, `di`, `dislope`, `flat`, `load` (+ version-specific) | objective inputs |
| `brief` / `brief_file` | resolved brief, or a path applied at load | `brief_file` applies a brief |
| `generator` | typology/FREEFORM recipe + knobs | requires `family: FREEFORM` and a brief |
| `objective` | version block | selects v1–v10 |
| `grid`, `mounting`, `extends` | verify/screen grid, rear enclosure, YAML inheritance | `extends` resolved before hashes |

Frozen deadlines: `docs/plan/01_CONTRACTS.md`; record schema `SCHEMA_VERSION=1`; objective version
tuple; `config_sha`/solve-spec hash semantics; `Design` hash and alphabetical search-vector order.

CLI (`pyproject.toml` exposes `hornlab-search`):

```powershell
hornlab-search doctor | version
hornlab-search selftest --analytic
hornlab-search run      --config <yaml> [--mode screen|verify|final|finalist] [--dry-run]
hornlab-search search   --config <yaml> [--budget N] [--resume DIR]
hornlab-search verify   --run <dir> [--top N | --designs h1,h2]
hornlab-search report   <run_dir> [--out PATH] [--top 5]
hornlab-search compare  <run_a> <run_b>        # metric diffs, not A/B scoring
hornlab-search dataset  stats|verify|export
hornlab-search pin-plan | narrow | export-step | surrogate | families | campaign | gpu-clean | ab-bl | gui | study
```

`compare` is a metric-difference tool; the Boundary Lab A/B is `ab-bl` / `compare/cli.py`.

### 3.4 Objective versions and J

Registered set: `SUPPORTED_OBJECTIVE_VERSIONS = (1,2,3,4,5,6,7,9,10)` (`objective/versions.py:26`).
v8 is importable but **not registered**; there is no v11.

| Version | Module | Weighted terms | Notes |
|---|---|---|---|
| v1 | `objective/scalar.py`, `terms.py` | `cov, rip, di, dislope, flat, load` | original |
| v2 | `scalar_v2.py` | same keys, detrended | opt-in |
| v3 | `scalar_v2.py` (`objective_v3`) | v2 + per-plane `f0_v`, K-law mask | |
| v4 | `scalar_v4.py:156` | `cov rip di dislope flat load` (+ `distd`, `diag` weight 0) | every term `/tol` |
| v5 | `scalar_meh.py` | v4 terms on synthesised MEH + `lw_resid, notch, xo_lob, headroom` | MEH brief only |
| v6 | `scalar_v6.py` | `load_near, z_smooth, cov_pat, di_rise`, `flat/rip/distd/diag` | Le Cléac'h/rollback |
| v7 | `scalar_v7.py:247` | v4 + `flat_cv`, combined `load`, 8 kHz floor, signed V | hardened CD; nights' default |
| v9 | `scalar_v9.py:336` | `cov_profile, rip, flat, load, dislope, di_roughness, flat_cv` (+ optional `hf_floor`, `constancy`) | corridor/target profile |
| v10 | `scalar_v10.py:1` | v9 terms; `rip` via required `ripple_region` (`preferred_edge\|min_edge\|max_edge\|seat_zone_deg`) | shipped second score, opt-in only |

For v4+: `J = Σ_k w_k·(raw_k / tol_k) + penalty`, minimised. Penalties: `PENALTY_INVALID =
PENALTY_FAILED = 1e3`; unmeasurable term fill 30; graded envelope penalty caps at 2e3. Stored
`terms` are normalised; `total` is J. **Never rank J across versions.**

### 3.5 Run and dataset formats

**Run dir** `runs/<UTC>-<mode>-<id>/`:

| File | Key contents |
|---|---|
| `run.json` | `run_id, mode, config_name, config_path, config_sha, family, objective_version, backend, cma_seed, budget, command, created/started/finished, status, stop_reason, config (full resolved), seed {design_hash, objective, terms}, best {design_hash, eval_no, objective}, stats, last_invocation, lib_shas, toolchain, dataset_dir` |
| `best.json` | `design_hash, family, params, objective, terms, ok, mode, eval_no, written_utc, di_source` |
| `search.ndjson` | one JSON row per evaluation: `n, mode, key (<design>-<mesh>-<solve>), design_hash, mesh_hash, solve_hash, family, params, objective_version, objective, terms, ok, error, kind, cached, seconds{mesh,solve,total}, n_dof, n_triangles, quadrants, symmetry_plane, bbox_m, build_box_m, res_mm, peak_vram_mb, metrics{arrays+scalars+di_source}, created_utc`, additive `lane, backend`, optional `mounting, mesh_policy, cad, generator, record_margin_mm, record_gate_agrees` |
| `designs/<hash>/` | `design.json`, `status.json`, `response.npz`, `metrics.json`, `mesh.msh`, `mesh_meta.json` |
| `report.html` | optional HTML report |

**`response.npz` keys** (observed): `freqs_hz, h_angles_deg, v_angles_deg, spl_h_db, spl_v_db,
balloon_dirs, spl_balloon_db, z_throat, p_h, p_v, p_balloon, channel_pressure,
channel_sphere_pressure, impedance_matrix, channel_tags, tag_areas_m2, backend, n_dof, meta`.
SPL/angles are float64; `z_throat`/`p_*` complex128; `meta` is a 0-d JSON string. The raw complex
pressures are **local-only** and are not in the committed top-design bundle.

**Dataset**:

- `dataset/index.jsonl` one line per record: `{design_hash, shard, row, objective, ok, family,
  backend, mode, lib_sha, created_utc, solve_seconds, traces}`.
- `dataset/shard-NNNN.jsonl` full record: `schema_version, design_hash, mesh_hash, solve_hash,
  family, params, target, mesh{...}, solve{...}, excitation, traces, metrics_scalars, objective,
  terms, objective_version, ok, error, created_utc, lib_shas`, optional `provenance, network_solution,
  run_id, config_name, typology`.
- Per-record arrays in `shard-NNNN/rec-NNNN.npz`, keys from `dataset/record.py:38`.

**Three different things:**

- **search run** = a directory of many evaluated candidates + convergence artefacts.
- **solve record** = one candidate's frozen provenance and metrics.
- **top-design export** = a curated, regenerable cross-run subset (not a run, not a shard).

### 3.6 Top-designs export (`docs/top_designs/`)

`tools/data/top_designs.py` is read-only over `runs/` and writes only under `--out`.

- **Admission:** row `ok`, finite `objective`, and **GPU-proven** (`backend == beat_cuda` or
  `lane == gpu`, else run fallback). CPU rows excluded.
- **Version:** row `objective_version`, else run's, else `unversioned`.
- **Grouping:** typology + score set (objective version); `--group-by score-config` adds
  `score_config_sha[:8]`.
- **Dedupe:** physical key `design_hash|mesh_hash|solve_hash` inside a group keeps the lowest J.
- **Ranking:** ascending J (lower is better), top-N per group (default 10).

Outputs:

| File | Contents |
|---|---|
| `top_designs.csv` | One row per selected design; flat, 161 columns: typology, score set, rank, J, dimensions, `param_*`, `term_*`, `metric_*`, provenance, `acoustics_id` |
| `top_designs.json` | Full manifest: `tool, schema_version, generated_utc, source, grouping, counts, score_configs, runs, groups, designs, acoustics, outputs` |
| `top_designs_acoustics.npz` | `<acoustics_id>__freqs_hz`, `h_angles_deg`, `v_angles_deg`, `spl_h_db`, `spl_v_db`, `balloon_dirs`, `spl_balloon_db`, `z_throat` |

Verified snapshot: 807 `search.ndjson`, 51,192 rows, 43,379 GPU, 37,588 unique, 52 groups, 437
selected, 437 with arrays, 3,496 arrays. CSV 437 rows × 161 cols. Generated
**2026-11-19T23:40:55Z**, HEAD `ddfba68…`. The live compact400 night may have appended solves after
the snapshot; regenerate to refresh.

Caveats: never rank across score sets; selected designs are top-of-group, not a random sample;
`run_rel`/`config_sha` are local provenance; raw complex pressure is absent; a live tree changes the
snapshot.

### 3.7 How the system consumes a horn

| System module | Expects from the horn run | Turns it into |
|---|---|---|
| `system/horn_assets.py` | `<run>/designs/<hash>/{response.npz,status.json,mesh.msh,design.json}` + run `run.json` | `HornAsset` with `asset_id`, `data_quality`, provenance hashes |
| `system/horn_import.py` | asset response | `ConvertedHorn` with `SCREEN_COMPLEX_APPROX` basis (accel/`exp(-iωt)` → velocity/`exp(+jωt)`) |
| `system/horn_full_domain.py` | `design.json`, `config.yaml`, quarter `mesh.msh` | closed full-domain `mesh.msh` + `full_mesh_qa.json` + `provenance.json` |
| `system/boundarylab/stage.py` | full-domain horn mesh + source group | BL imported mesh + source port inside a staged project |

**Critical quality fact:** every native saved run has `meta["spl_reference"] = unit normal
acceleration` / `exp(-iωt)`. `derive_source_basis` cannot prove a canonical `SourceBasis`, so real
complex records classify as **`MAGNITUDE_ONLY`** for the system layer. `convert_asset` produces only
`SCREEN_COMPLEX_APPROX`; it never claims `EXACT_COMPLEX`. This is why phase/delay/system-score claims
are refused, and why a coherent sum needs the calibration policy (R1).

**Critical geometry fact:** saved horns are quarter models (162 free edges, 81 on x=0 + 81 on y=0).
A BL separate-body assembly under symmetry-off needs a **closed full-domain** mesh. The sanctioned
route is `horn_full_domain.build_full_domain_mesh` (`quadrants="1234"`, provenance gate, mesher pin
match). Non-rows point grids cannot be promoted by this lane.

### 3.8 Horn-side code risks relevant to system expansion

| Risk | Evidence | Consequence |
|---|---|---|
| Stored basis is not the system basis | `system/horn_assets.py:26-36` | Every real complex asset is `MAGNITUDE_ONLY`; no exact phase. |
| Converted assets are approximate | `system/horn_import.py:9-13` | Coherent sums are screening only. |
| Assets are quarter meshes | `system/horn_full_domain.py:5-11` | Full-domain rebuild cost + provenance gate. |
| Mesher pin must match | `horn_full_domain.py:236-243` | A geometrically identical run may refuse if the pin differs. |
| Full-domain dof/scale | `horn_full_domain.py:455-467` | Doubling/tripling surface can exceed dof/triangle caps. |
| Only rows-grid recipes promote | `horn_full_domain.py:262-269` | Non-rows point grids cannot be closed here. |
| Complex arrays local-only | `top_designs.py:74-87` | Committed export lacks `p_h/p_v/p_balloon`; phase work needs `runs/`. |
| GPU-only export filter | `top_designs.py:379-384` | CPU-lane solves never appear in the funnel. |
| Dataset index is thin | `dataset/store.py:131-141` | Index alone cannot group by version/target/typology. |
| `dataset/MANIFEST.json` lags code | manifests list objective versions 1–7 | Trust `versions.py` and per-record `objective_version`. |
| Crash window dataset vs ndjson | `evaluate.py:6-9` | A kill can undercount ndjson-keyed funnels. |

### 3.9 Horn-side commands for a cloud agent

```powershell
# Offline tests (CI profile)
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -q

# Dataset inspection (read-only)
.venv\Scripts\python.exe -m hornlab_search.cli dataset stats
.venv\Scripts\python.exe -m hornlab_search.cli dataset verify

# Regenerate the top-designs bundle (read-only over runs/)
.venv\Scripts\python.exe tools\data\top_designs.py --no-acoustics
.venv\Scripts\python.exe tools\data\top_designs.py

# System asset inventory (read-only)
.venv\Scripts\python.exe -c "from hornlab_search.system import horn_assets as h; r=h.inventory_runs(limit=5); print(r.to_dict()['by_quality'])"
```

---

## 4. Horn + vented-woofer system backend

### 4.1 Architecture as built

```
(A) CPU SCREEN — no solver, seconds to minutes
    saved horn asset ─┐
    compatibility.py ─┤   woofer_seed.py  → deterministic shortlist + rejected ledger
    piston.py ────────┤   (box × driver × XO × placement; Pareto; no winner)
    bass_reference.py ┤
    drivers.py ───────┘
         │
         ▼
(B) INSTALLED BL REFERENCE — CPU `beat_cpu`, minutes
    stage.py / runner_stage.py → BL host (generate → stage_generation →
      component_parameters patch → compile → write_project_file → blab validate)
    → reference.py solve → BL headless run/ (manifest + npz per frequency)
    → bl_results.py reader (schema-pinned, per-excitation complex bases)
         │
         ▼
(C) DSP / RECOMBINATION — pure CPU, deterministic
    dsp.filter_bank → combine.combine (refuses mixed per-input refs)
    → reference.report (per-channel + illustrative recomposition)
```

Fidelity is enforced, not aspirational: `SCREEN_MAGNITUDE | SCREEN_COMPLEX_APPROX |
INSTALLED_EXTERIOR_BEM | COUPLED_VENTED_FEM_BEM_LEM | MEASURED_VALIDATED`. The two per-channel
references are Pa per 2.83 V (woofer) and Pa per 1 m/s (horn); the sum is refused unless a
calibration record makes them comparable.

### 4.2 Module inventory

| Module | Role | Key symbols | Writes |
|---|---|---|---|
| `system/contracts.py` | Frozen v1 system schema, ids, basis/phase gates | `SystemSpecV1`, `parse_system_spec_dict`, `HornAsset`, `WooferDriver`, `SystemResponse`, `SourceBasis`, `domain_sha16`, `canonical_json` | none |
| `system/woofer_seed.py` | CPU seed screen: boxes/XO/placement, Pareto, panel-fit gate | `run_seed_screen`, `derive_horn_envelope`, `bl_panel_fit_feasible/_separation`, `placement_legality` | `woofer_seed.json/.md` |
| `system/compatibility.py` | Tier-0 questions + report-only H/V `E_shape` | `evaluate_tier0`, `extract_horn_fingerprints`, `screen_xo_bands`, `require_phase_alignment` | none |
| `system/piston.py` | Ideal rigid-piston directivity `2J1(x)/x` | `piston_directivity`, `first_minus6db_angle`, `null_mask` | none |
| `system/bass_reference.py` | Vented-box feasibility via `tools/bassbox.py` | `feasible_boxes`, `box_point_to_bassbox`, `lf_report_row`, `port_neck_length_mm` | none |
| `system/drivers.py` | T/S load + strict geometry schema + fidelity gate | `load_woofer`, `load_driver_geometry`, `geometry_completeness`, `require_fidelity` | none |
| `system/score.py` | Report-only Pareto/dominance and claim refusals | `render_report`, `dominates`, `flag_off_axis_cancellation` | none |
| `system/optimize.py` | Stage-2 fixed-horn pilot | `run_pilot`, `horn_balloon_beamwidth_screen` | optional case manifest |
| `system/portfolio.py` | Stage-3 diverse-horn screen | `run_portfolio`, `select_diverse_assets`, `cuts_beamwidth_by_xo` | optional manifest |
| `system/dsp.py` | Complex LR/PEQ/delay/polarity | `filter_bank`, `validate_dsp_point`, `LR_ORDERS` | none |
| `system/combine.py` | Phase-once coherent sum, cache key | `combine`, `recombine_with_dsp`, `recombine_cache_key`, `PHASE_REFUSAL` | none |
| `system/horn_assets.py` | Inventory saved horn solves | `inventory_runs/_run`, `asset_row`, `derive_source_basis` | none |
| `system/horn_import.py` | Stored accel/`exp(-iωt)` → canonical velocity/`exp(+jωt)` | `convert_asset`, `find_asset`, `ConvertedHorn` | none |
| `system/horn_full_domain.py` | Rebuild quarter horn as closed full-domain mesh | `build_full_domain_mesh`, `discover_asset`, `validate_full_domain_qa` | full-domain mesh + QA |
| `system/provenance.py` | Immutable case dirs, self-checksummed manifests | `new_case_dir`, `write_manifest`, `load_manifest`, `file_sha256` | `manifest.json` |
| `system/reference.py` | No-GUI `prepare/validate/solve/report` seam | `prepare`, `validate`, `solve`, `report`, `recompose_preset`, `REFERENCE_TOKENS` | `reference_*.json` |
| `system/cli.py` | Additive system CLI (module-invoked only) | `main` (`pilot`, `portfolio`, `list-assets`, `reference …`) | via modules |
| `system/geometry/rules.py` | Fabrication rules | `check_port_fits`, `check_driver_and_brace_clearance`, `check_wall_thickness`, `check_woofer_horn_clearance` | none |
| `system/boundarylab/probe.py` | Read-only BL discovery/pins | `probe_boundarylab`, `BLRoot` | none |
| `system/boundarylab/run.py` | `blab project validate`; inert solve gate | `validate_project`, `solve_project`, `BlockedByGate` | none |
| `system/boundarylab/generate.py` + `runner_vented.py` | Drive BL's vented generator | `generate_vented`, BL-side `main` | `bl_output/` meshes |
| `system/boundarylab/stage.py` + `runner_stage.py` | Stage real PhysicalSystem (vented ± horn) | `stage_reference_project`, `stage_horn_project`, BL-side `_stage_horn` | `case.blab.json`, `stage_report.json` |
| `system/boundarylab/assemble.py` | Horn mesh QA + documented draft project | `horn_mesh_qa`, `plan_assembly`, `write_draft_project` | draft project |
| `system/boundarylab/clearance.py` | Two-body AABB/vertex gap verdict | `body_clearance`, `aabb_gap_m` | none |
| `system/boundarylab/import_results.py` | Result artifact detection | `detect_result_artifact`, `read_headless_result` | none |
| `system/boundarylab/bl_results.py` | Canonical BL headless-result reader | `read_bl_headless_result`, `to_system_response`, `BL_RESULT_TOKENS` | none |
| `system/boundarylab/motor_map.py` + `runner_motor_stage.py` | T/S → BL component-parameter patch | `map_motor`, `stage_motor_project`, BL-side `main` | `case.blab.json` |
| `tools/system/gui_system_job.py` | Thin argv bridge for GUI jobs | argv → `system.cli` / `woofer_seed.main` | job outputs |

`pyproject.toml` registers only `hornlab-search = hornlab_search.cli:main`; the system CLI is
module-invoked (`python -m hornlab_search.system.cli`). The GUI's job bridge is the only other entry.

### 4.3 Pipeline A — CPU screen / shortlist

Entry: `python -m hornlab_search.system.woofer_seed --asset-id <id> --spec <yaml> --out
system_runs/woofer_seed`.

1. `parse_system_spec_dict` validates the YAML strictly; unknown keys are hard errors.
2. `horn_import.find_asset` scans the newest runs first; the envelope comes from the full-domain
   provenance, else the mirrored quarter-mesh bbox.
3. `load_driver_catalog` reads T/S via the frozen cone schema and geometry via the system schema;
   missing fields are visible rejections, not guesses.
4. `compatibility.extract_horn_fingerprints` uses stored H/V cuts, falling back to the balloon; a
   missing on-axis sample is a refusal, never an interpolation.
5. `screen_xo_bands` computes `E_shape` over stored samples in a per-candidate ±1/3-octave band, H
   and V separately.
6. `bass_reference.feasible_boxes` sweeps Vb × Fb × port area, derives the neck, and rejects
   short/long necks and shallow depth.
7. `evaluate_box` runs the lumped LF model + fabrication rules + the F3 gate;
   `_bl_panel_fit_for_screen` refuses panels BL would reject.
8. Placement: `derive_min_center_spacing_mm` uses the real envelope + cabinet + clearance, not the
   illustrative spec range; `placement_legality` adds a 3-D AABB check.
9. Kept rows → `_nondominated` → `_select_diverse` (one per driver, axis-best, Pareto fill).
10. `SeedResult.write` emits `woofer_seed.json`/`.md`; `study_id` hashes inputs, metrics and driver
    file hashes. **No scalar winner; phase claims refused.**

Pilot: `python -m …cli pilot --spec … --driver-stem faitalpro_12pr300 --limit-boxes 8`.
Portfolio: `python -m …cli portfolio --spec … --k 6`.

Refusal tokens: `TierTooHigh`, `PhaseUnavailable` / `MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE`,
`DataQualityError` (missing envelope/fingerprint/driver), `SchemaError`, `BL_PANEL_FIT_*`.

### 4.4 Pipeline B — BL stage / validate / solve / read

**Prepare:**

```powershell
python -m hornlab_search.system.cli reference prepare `
  --root C:\Users\hunte\Github\boundary-lab `
  [--horn-mesh X.msh --source-group SD1D1001] --out system_runs
```

`reference.prepare` probes BL, requires a source group when a horn mesh is supplied, resolves the
newest full-domain mesh if none is given, stages via `stage_reference_project` or
`stage_horn_project`, then writes an immutable `reference_prepare.json` with `assembly_geometry_id`,
blockers and project/stage hashes.

Inside `stage._stage`: writes `adapter_spec.json`, executes
`[BL python, -I, -B, runner_stage.py, spec]`, parses the final NDJSON, then runs
`blab project validate --json`. Staged means child rc 0, `ok` true, project exists, validate rc 0 +
`valid:true`. With a horn spec it additionally requires proven body clearance ≥1 mm.

`runner_stage.py` performs BL's host path: catalog → session → generate → stage_generation →
optional horn import → compile → `prepare_system_solve` → `write_project_file` → reopen verification.
Horn import decisions are recorded verbatim.

Refusals: `BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT`, `HORN_MESH_IS_TEST_DOUBLE`,
`REFERENCE_CASE_EXISTS`, `REFERENCE_SOURCE_GROUP_REQUIRED`, `BL_VALIDATE_REJECTED`,
`BODY_CLEARANCE_VIOLATION/UNPROVEN/UNCHECKED`.

**Solve:**

```powershell
python -m hornlab_search.system.cli reference solve <case> `
  --request req.json --backend beat_cpu --authorized-by "<record>"
```

`solve` refuses unless `authorized_by` is non-empty; resolves the project, shape-checks the request,
resolves the BL root recorded in the case manifest, rejects an existing `run/manifest.json`, and
invokes BL's own CLI with absolute argv. It writes `reference_solve.json` before raising on failure.
Success requires rc 0 **and** `status=="complete"`. `bl_run.solve_project` is deliberately inert.

**Read:** `bl_results.read_bl_headless_result(run_dir)` verifies manifest schema/version 2, non-empty
unique frequencies, excitation ids, completion mask, result alignment, phasor convention, unit `Pa`,
domain metadata, per-frequency quantity shapes, and per-excitation port kinds. Unknown port
kind/unit/axes/phasor → `DataQualityError` token. `to_system_response` assembles a `SystemResponse`
with `p_total=None`.

**Motor path:** `motor_map.stage_motor_project` builds a component-parameters patch from committed
T/S and the committed seed box; BL-side `runner_motor_stage.py` applies
`apply_configuration_patch` and verifies the serialized/reopened parameters. Fs/Vas/Mms cross-checks
are 0.41/0.05/0.67 %.

### 4.5 Pipeline C — DSP / recombination

`dsp.filter_bank(point, freqs)` returns `{"horn","woofer"}` complex arrays: horn HP / woofer LP,
PEQ + polarity on the woofer, per-channel linear gain, delay on the horn. `validate_dsp_point`
enforces ranges. `combine.combine` requires complex fields and pairwise-compatible `SourceBasis`,
then computes `Σ H_x·F_x·L_x` with **no spatial phase factor** (phase-once rule).

`reference.recompose_preset` first tries `combine`; when per-input references differ it records the
refusal and evaluates the same algebra at nominal (1 unit) input per channel. `report` renders preset
complex sums, vertical lobing and honesty labels.

### 4.6 On-disk schemas

**System case dir** `<store>/system/<experiment_id>/<UTC>-<tag>-<pid>-<uuid>/`:

| File | Contents |
|---|---|
| `manifest.json` | `created_utc, host{python,platform,cwd}, manifest_payload_sha256, payload{…}`; payload depends on writer |
| `manifest.json` payload (stage) | `kind, bl_root, bl_dependency_hashes, runner, spec, detail, result, validate, [clearance], [project_sha256]` |
| `manifest.json` payload (motor) | + `experiment_id, runner_sha256, spec_sha256, motor_mapping, geometry_overrides, yaml_sha256, configuration_patch, configuration_patch_sha256` |
| `manifest.json` payload (pilot) | `kind, study_id, asset, converted, driver, n_boxes, meta, rows` |
| `manifest.json` payload (portfolio) | `kind, study_id, asset_summary, rows, meta` |
| `case.blab.json` | BL PhysicalSystem project (schema version 10) |
| `adapter_spec.json` / `stage_report.json` | BL runner input/output |
| `blab_validate.json` / `blab_solve*.log.txt` | BL validation and logs (UTF-16 from Tee) |
| `run/manifest.json` | BL result manifest (see below) |
| `run/frequencies/NNNNNN.json` + `.npz` | per-frequency metadata/arrays |
| `run/domains.json` + `.npz` | observation domains (H/V polars, probes, sources) |
| `run/compiled-system.json` | compiled physical system |
| `reference_prepare.json` / `reference_solve.json` | our reference records |
| `g5_dsp_replay.json`, `g6_paired_delta.json`, `motor_axis_ab.json` | evidence addenda |

**BL `run/manifest.json` keys:** `backend_id, compiled_system_file, completion_mask, domains_file,
domains_metadata_file, engine_runs, excitation_port_ids, finished_at_utc, frequencies_hz, meshes,
phasor_convention, project_file, project_sha256, request_file, results, schema, schema_version,
solve_kind, solver_options, started_at_utc, status`.

**Per-frequency JSON:** `arrays_file`, `diagnostics{engine_provenance, phasor_convention}`,
`excitation_port_ids`, `freq_hz`, `quantities[]{axes, dtype, id, key, metadata, quantity, shape,
target_id, unit}`. The reader expects `quantity=="exterior_pressure"`, `unit=="Pa"`, axes
`(excitation, observation)` or reversible labels.

**`woofer_seed.json`:** `schema, system_objective_version, study_id, input_sha256, asset, envelope,
catalog, catalog_rejected, fingerprints, metric_spec, counts, xo_screens, kept_rows, shortlist,
rejected_ledger, claim`. `input_sha256` = response npz SHA + envelope SHA + per-driver
`{ts,geometry}` SHAs.

### 4.7 Configuration surface (system spec v1)

The committed example is `examples/systems/two_way_80x50_700_research.yaml`. Top level exactly
`schema_version, experiment_id, mode, horn, woofer, cabinet, assembly, dsp, target, fidelity`;
unknown keys are hard errors.

| Key | Meaning / units | Default / example | Notes |
|---|---|---|---|
| `schema_version` | contract version | required =1 | frozen |
| `experiment_id` | safe label → store path | required | `/\\:*?"<>\|` refused |
| `mode` | `fixed_horn` or `horn_portfolio` | required | enum |
| `horn.asset_id` | saved horn system asset id | `SELECT_FROM_REAL_INVENTORY` | resolved from inventory |
| `horn.driver_profile_id` | optional profile label | null | stored only |
| `woofer.driver_id` | T/S stem | `SELECT_REAL_10_OR_12_INCH_DRIVER` | `load_cone` schema |
| `woofer.geometry_file` | geometry YAML path | `examples/systems/driver_geometry/…` | parsed; seed/pilot take explicit dirs |
| `cabinet.kind` | `vented`/`sealed` | `vented` | sealed refused by `feasible_boxes` |
| `external_{width,height,depth}_mm_range` | external mm | 340–510 / 470–850 / 260–570 | advisory; actual dims derived |
| `net_volume_l_range` | net Vb L | 35–115 | swept 7 points |
| `tuning_hz_range` | requested Fb Hz | 30–65 | swept 7; Fb is an outcome |
| `wall_mm` | wall thickness mm | 18 | min-wall policy 12 mm |
| `port_type` | `round_flared/round_straight/slot` | `round_flared` | slot refused at LF tier |
| `port_throat_area_cm2_range` | port area cm² | 45–170 | swept 5 |
| `port_nfr_range` | port NFR | 0–0.2 | **inert**: only `range[0]` is carried |
| `assembly.horn_layout` | placement model | `separate_above` | used by seed placement |
| `assembly.woofer_center_y_mm_range` | y placement | 90–400 | **inert**: seed derives legal spacing |
| `assembly.woofer_center_x_mm_range` | x placement | 0–0 | **inert** |
| `assembly.horn_mounting_offset_z_mm_range` | z offset | −80–80 | **inert**: seed uses `(0,25,50)` mm |
| `dsp.active` | active flag | true | **inert** |
| `dsp.xo_hz_range` | crossover search Hz | 700–1300 | used by seed/pilot |
| `dsp.crossover_types` | LR orders | `[LR4]` | staged; DSP bench locked |
| `dsp.gain_db_range` | per-channel gain dB | −12–0 | validated by `validate_dsp_point` |
| `dsp.relative_delay_ms_range` | horn delay ms | −1.5–1.5 | validated |
| `dsp.peq_max_bands` | PEQ band cap | 2 | validated |
| `dsp.peq_max_boost_db` | boost ceiling dB | 3.0 | cuts unlimited |
| `target.beamwidth_h/v_deg` | coverage target | 80/50 | **inert**: parsed, never used by screens |
| `target.listening_angle_h/v_deg` | front region | −30..30 / −15..15 | required; drives fingerprints |
| `target.low_freq_f3_hz_max` | LF gate Hz | 55 | gate in seed/pilot |
| `fidelity` | `screen_only`/`reference` | `screen_only` | only `screen_only` implemented |

**Driver T/S YAML** (frozen C8 cone schema): `name, kind, re_ohm, le_mh, bl_tm, sd_cm2, xmax_mm,
p_aes_w, fs_hz, qms, mms_g, mmd_g, cms_mm_per_n, vas_l, rms_kg_s, source`, optional
`sens_db_2v83`. **Geometry YAML** keys are exactly `driver_id, measured_by, sourced_from,
cutout_mm, frame_od_mm, depth_mm, cone_depth_mm, surround_width_mm, dust_cap_diameter_mm,
mounting_depth_behind_baffle_mm`; omitted means unknown (not null).

**Driver catalog today:** four FaitalPRO units — 10PR300, 10PR320, 12PR300, 12PR320. All four were
loaded, none rejected. All four are missing cone depth, surround width, dust-cap diameter, mounting
depth; installed-tier claims are refused. The 12-inch 12PR300 T/S: Re 5.4 Ω, Le 0.42 mH, Bl 14.1 T·m,
Sd 533 cm², Xmax 4.92 mm, P_AES 300 W, Fs 50 Hz, Qms 9.9, Mms 43.4 g, Mmd 29.5 g, Cms 0.23 mm/N,
Vas 92.6 L, Rms 1.4 kg/s.

### 4.8 Fidelity, provenance, authorization

- **Fidelity labels** are in `contracts.py:72-76`; numbers are comparable only within one label and
  one `SYSTEM_OBJECTIVE_VERSION=1`.
- **Per-input references:** `SourceBasis.per_input` ∈ `{V_rms, normal_velocity_mps}`;
  `compatible_for_sum_with` requires equal time/quantity/per-input plus declared distance, origin,
  angular frame and source geometry hash.
- **Phase refusals:** `HornAsset.require_complex` / `SystemResponse.require_phase` raise
  `PhaseUnavailable` with `MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE`; `combine.PHASE_REFUSAL` is
  byte-exact; the reader-side token is `SENSITIVITY_REFERENCE_MISMATCH`.
- **Manifest self-check:** `write_manifest` records the canonical-JSON SHA; `load_manifest`
  recomputes and raises `SchemaError` on mismatch. Reference records refuse overwrite.
- **Authorization:** `reference.solve` requires non-empty `authorized_by`, else
  `REFERENCE_SOLVE_UNAUTHORIZED`. `run.solve_project` is inert even with `HORNLAB_BL_ALLOW_SOLVE=1`.
  The GUI adds `HORNLAB_GUI_ALLOW_BL_SOLVE` in `gui/data_hw_stage.py`.

### 4.9 Evidence ledger — what has actually been solved

All recorded system solves used **CPU `beat_cpu`**. Engine provenance per run: BEAT Engine 0.7.0,
Julia 1.12.7, `float32`, quadrature 2, static condensation on, symmetry off, transducer reference
voltage 2.83 V, phasor `exp(+iωt)`.

| # | Case | Content | Result |
|---|---|---|---|
| 1 | `bl_smoke/20261118T225108Z-smoke-42536-01d15001` | assembled horn + vented, 3 freqs (250/700/1100) | complete 3/3; polarity/recomposition residual 0.0; 0.1 ms delay exactly −ωτ (−9.00/−25.20/−39.60°); woofer 700 Hz asymmetry up30 −6.02 dB / down30 +1.49 dB |
| 2 | `bl_smoke_wide/20261118T231115Z-g4wide-56836-b5d6490a` | same assembly, 25 log freqs 200–2500 Hz | complete 25/25; H/V polars 37 pts each; 5 probes |
| 3 | `bl_g6_offset30/20261118T235110Z-assembly-21668-c17f7cf6` | same, horn +10 mm forward | complete 25/25; paired max rel delta 0.356–0.575; XO band 0.064–0.371; woofer channel changed although only the horn moved |
| 4 | `bl_motor12pr/20261119T010548Z-motor12pr-17944-fa37ab5e` | vented-only; real 12PR300 T/S via BL `component_parameters` patch; seed box 115 L / 371.2×371.2×1078.79 mm / 45 cm² | validate rc 0; complete 25/25 |
| 5 | `bl_motor12pr_demo_twin/20261119T013209Z-ref_case-11372-452574f9` | identical geometry, demo motor | validate rc 0; complete 25/25; A/B vs #4: pressure basis differs 120–144 % per 2.83 V (LF 120 %, XO 140–149 %), current 0.366 A vs 0.477 A @200 Hz, velocity 102 % |
| 6 | `bl_motor12pr/20261119T010537Z-real_driver-48792-9d89b3df` | real motor + default box 0.32×0.50×0.36 | validate rc 0 — **STAGED, NOT SOLVED** |
| R0 | `bl_ref_case/20261118T223335Z-ref_case-61644-32976a2a` | vented-only, demo motor, default box | validate rc 0 — **STAGED, NOT SOLVED** |
| R4 | `bl_r4_tower_box/20261119T001041Z-ref_case-40216-b32bb5a2` | screen top cell attempt | **REFUSED by BL**: "Driver must fit inside the enclosure walls with 3 mm clearance." |
| — | `bl_ref_case/20261118T231100Z-assembly-62864-f62bf799` | 0 mm horn offset, staged/validated, never solved | **proven `BODY_CLEARANCE_VIOLATION`** by the R16 gate: horn rear 3 mm inside the enclosure front plane, vertex min 0.7 mm. BL had accepted it. Do not solve. |

The handoff summary line says "6 solved"; the disk and the readiness table say **5 solved** (cases
#1–#5) plus #6/R0 staged and the 62864 violation. Use the disk census; do not "fix" the ledger to 6.

**G5 DSP replay:** on the exact wide basis, 12 presets (LR4 @ 700/900/1100 × polarity ±1 × horn delay
±1 ms); polarity arithmetic residual 0.0; pure-delay max phase residual 4.9e-16 rad; the reader and
`combine` refuse the mixed-per-input sum verbatim. The illustrative unity-gain LR4@700 row shows an
on-axis interference dip ~23.5 dB below the band max; it is calibration-dependent and demonstrates
capability, not a ranking.

### 4.10 Screen studies and measured numbers

| Study | Command | Counts | Notes |
|---|---|---|---|
| `65f6db3e8c8e8f86` | `woofer_seed --asset-id 0062fb59fbf63eae --out system_runs/woofer_seed_stage5 --limit-boxes 8 --shortlist-size 6` | 32 boxes considered, 18 rejected, 126 kept, 42 Pareto, 6 shortlist, 42 XO hypotheses, 0 XO/placement rejected | pre-panel-fit |
| `27616eedee09009f` | same with `--out system_runs/woofer_seed_stage5_blfit` | 11 BL panel-fit rejected, 32 considered, 29 rejected, 27 kept, 9 Pareto, 6 shortlist, 9 XO | post-panel-fit; 2 kept / 4 dropped / 4 new |
| `783043edcbecf2fe` / `0352ca1af0532aba` | `cli pilot` for 12PR300 / 12PR320 | 8 boxes each; 4/8 pass F3; crossover axis FAIL all rows at 700 Hz | pilot: no winner |
| `1a509f87c01fd6fd` | `cli portfolio --k 8 --scan-limit 240 --limit-boxes 6` | 602 assets, 8 selected, 16 cells, 542 lost-candidate rows | two independent screens; disagreements reported |

Post-panel-fit top three (display only, no winner):

| candidate | driver | Vb L | external W×H×D mm | port cm² | dz mm | E_H | E_V | F3 Hz | XO Hz |
|---|---|---|---|---|---|---|---|---|---|
| `01e7d07d2bf70364` | 12PR320 | 115.0 | 372.0 × 372.0 × 1073.3 | 45 | 0 | 0.023 | 0.002 | 49.19 | 961.58 |
| `42d171062dcda386` | 12PR300 | 115.0 | 371.2 × 371.2 × 1078.8 | 45 | 50 | 0.024 | 0.002 | 49.72 | 961.58 |
| `627b9184c3a26662` | 12PR320 | 115.0 | 372.0 × 372.0 × 1073.3 | 45 | 25 | 0.023 | 0.002 | 49.19 | 961.58 |

Key reading: the square bassbox fronts are the blocker, not the LF alignment. The recorded 371.2 mm
front cannot host BL's 200 mm demo driver plus a 170 cm² port at any legal `y`; a height-reshaped
560 mm front passes a unit test; 45 cm² ports fit the 371–372 mm fronts. The screen metric is
relative-shape only: it says nothing about absolute level, phase, delay, or whether an LR4 sums.

### 4.11 System code defects and fragile spots (verified in code)

| Location | Finding | Consequence |
|---|---|---|
| `system/optimize.py:167-168` | `require_fidelity(driver, "LF_TS_SCREENING")`; that string is not a known fidelity (`drivers.py:150-152`) | Any `pilot --geometry <yaml>` raises `SchemaError`; no test exercises the path |
| `system/optimize.py:255-262` vs `system/score.py:123-128` | Pilot `numeric_axes` are `{value,direction}` dicts; `_finite_number` returns `None` for a dict | `dominates` is always false ⇒ every pilot row is Pareto; the pilot "Pareto" output is effectively unranked |
| `system/woofer_seed.py:1127-1142` | `_nondominated` is O(n²) over all kept rows | Runtime grows quadratically with driver/box/offset breadth |
| `system/woofer_seed.py:696-702` | Panel-fit defaults are BL's demo transducer (200 mm dia, 40 mm cone, 8 mm roundover) | "BL-buildable" is demo-shape-conditional; real 12PR300 changes the refusal |
| `system/woofer_seed.py:296-303`, `contracts.py:347-349` | `woofer_center_*`, `horn_mounting_offset_z`, `target.beamwidth_*`, `dsp.active` are parsed but unused | User edits silently do nothing |
| `system/boundarylab/stage.py:289` | `detail["overrides"] = spec.get("overrides", {})`, but `build_stage_spec` writes `source` | Manifest audit field is always `{}`; actual values live in `spec.source` |
| `system/boundarylab/stage.py:259-283` | Clearance selects meshes only when `purpose=="bem_surface"` | A BL purpose-label change can fail every horn stage as `BODY_CLEARANCE_UNCHECKED` |
| `system/reference.py:1201-1207` | `_fidelity_for` derives the label from `solve_kind` alone | A vented-only run can be labelled `INSTALLED_EXTERIOR_BEM` without checking driver geometry |
| `system/reference.py:1089-1108,170-173` | A failed solve still writes `reference_solve.json`; overwrite refused | Retrying in the same case dir is impossible; create a new case |
| `system/dsp.py:65-80,109-117` | `filter_bank` does not range-check; range validation is a separate optional call | A caller can build out-of-range filters; built-in presets are in range |
| `system/combine.py:64-66` vs `boundarylab/bl_results.py:536-548` | Two overlapping per-input guards with different tokens | Duplicate semantics; callers need both token families |
| `system/boundarylab/bl_results.py:478-534` | Independence is structural only (one column per port, finite, non-zero); no rank test | Collinear/symmetric ports pass; do not read it as numerical independence |
| `system/boundarylab/motor_map.py:67-72` | Hard-coded TS/geometry paths and seed candidate (12PR300 only) | Motor staging is a single-driver research path |
| `system/horn_full_domain.py:80-84` | Hard-coded default run name/design hash/case tag | Full-domain rebuild defaults to one reference asset |
| `tests/system` | 355 `def test_` across 35 modules (grep), real-BL tests env-gated | Docs quote 149/159/261/274; treat those as stale. No test covers `pilot --geometry` or pilot dominance |

### 4.12 System commands (no GPU)

```powershell
# Inventory (read-only)
.venv\Scripts\python.exe -m hornlab_search.system.cli list-assets --limit 10
.venv\Scripts\python.exe -m hornlab_search.system.cli list-drivers

# CPU screen / pilot / portfolio (no solver)
.venv\Scripts\python.exe -m hornlab_search.system.woofer_seed `
  --asset-id <ASSET_ID> --spec examples/systems/two_way_80x50_700_research.yaml `
  --limit-boxes 4 --out system_runs\woofer_seed_recon
.venv\Scripts\python.exe -m hornlab_search.system.cli pilot `
  --spec examples/systems/two_way_80x50_700_research.yaml `
  --driver-stem faitalpro_12pr300 --limit-boxes 4 --out system_runs
.venv\Scripts\python.exe -m hornlab_search.system.cli portfolio `
  --spec examples/systems/two_way_80x50_700_research.yaml --k 4 --out system_runs

# BL staging dry-run (creates nothing, no BL execution)
.venv\Scripts\python.exe -m hornlab_search.system.cli reference prepare `
  --root C:\Users\hunte\Github\boundary-lab --dry-run

# DSP/report on the committed offline fixture (no BL, no solve)
.venv\Scripts\python.exe -m hornlab_search.system.cli reference report `
  tests\system\fixtures\bl_results\reference_run --json

# Offline system tests
.venv\Scripts\python.exe -m pytest tests\system -q
```

A **real Boundary Lab install** is required for non-dry-run prepare/validate/solve and the
`HORNLAB_BL_REAL_TESTS=1` tests. GPU is only involved if BL's chosen backend is CUDA; every recorded
system solve used `beat_cpu`.

---

## 5. GUI: architecture, routes, controls, UX

### 5.1 App architecture

| Layer | Implementation | Notes |
|---|---|---|
| HTTP server | Python stdlib `ThreadingHTTPServer` on `127.0.0.1` only | `gui/server.py:926-948`; `--port`, `--no-browser`, `--root`, `--runs`, `--study-root`, `--analysis-dir`, `--system-store` |
| Request guards | Host allowlist (`127.0.0.1:<port>`, `localhost:<port>`); POST Origin + `application/json` + body-size cap | `server.py:707-800`; GET is read-only; POST is JSON-only |
| API | `App.get` / `App.post` dispatch into `data*.py` readers | single-flight GET coalescing (`server.py:254-284`); `data.py` caches by file stamp |
| Static | `gui/static/` served as-is; no build step | `index.html`, ES modules, `app.css` |
| Router | `app.js` `ROUTES` array, hash-based | `#/...`; query strings handled per route |
| 3D | three.js r160 via importmap (CDN) + `view3d.js` / `hw3d.js` | `index.html:10-20`; `[data-v3d]` dispose sweep in `route()` |
| Charts | `charts.js` SVG helpers (`chart`, `polarMap`, `globePlot`, `sparkline`, `stackBarHtml`) | no chart library, no acoustics in JS |
| Theme | `?theme=dark\|light` → localStorage `hl-theme` → OS `prefers-color-scheme` | `index.html` boot script; tokens in `app.css` |
| Jobs | `gui/jobs.py` `JobManager`; `jobs.py` kinds and argv builders | preview → launch → log/progress → cancel; CPU lane lock respected |
| System store | `App(system_store=…)`, default `$HORNLAB_SYSTEM_STORE` or `<root>/system_runs` | P0 step 0; the canonical tree uses a junction to the worktree store |

**Data flow:** browser `fetch('/api/...')` → `App.get` → `_get_uncoalesced` → `data*.py` reader →
JSON. The JS never computes an acoustic number; it formats and plots. The system layer adds
`/api/hw/*` readers (`data_hw.py`, `data_hw_screen.py`, `data_hw_compare.py`, `data_hw_new.py`,
`data_hw_stage.py`) and one `hw` dispatch (`server.py:485-537`).

### 5.2 Navigation and route inventory

Current left nav (`gui/static/index.html:37-58`):

```
Results        Home · Runs · Campaigns · Elites · Compare · Analysis
Start work     Briefs · Typologies · New run
Bayes          Studies · Method board
Horn + woofer  Screens · Cases · Readiness
System         Status
footer         Glossary · theme toggle
```

| Route | View function | Purpose | State |
|---|---|---|---|
| `#/` / `#/home` | `viewHome` | landing: lane cards, recent runs, next actions | — |
| `#/status` | `viewStatus` | GPU/CPU lanes, jobs, lock, logs | polls while open |
| `#/campaigns` | `viewCampaignsList` | campaign list | — |
| `#/campaign/<id>` | `viewCampaignDetail` | campaign detail | — |
| `#/runs` | `viewRunsList` | run list, filters/sort | query |
| `#/run/<id>` | `viewRunDetail` | verdict-first run page + charts | — |
| `#/run/<id>/3d` | `viewRun3D` | horn 3D | — |
| `#/run/<id>/balloon` | `viewBalloon` | balloon 3D | query (`mode`) |
| `#/run/<id>/evolution` | `viewEvolution` | search evolution | — |
| `#/run/<id>/umap` | `viewUmap` | design cloud (UMAP/PCA) | — |
| `#/run/<id>/archive` | `viewRunArchive` | QD atlas | — |
| `#/run/<id>/verify` | `viewVerify` | verify table | query |
| `#/run/<id>/verify/compare` | `viewVerify` (compare) | verify A/B | query |
| `#/analysis` / `#/analysis/<set>` | `viewAnalysis` | analysis report | — |
| `#/elites` | `viewElites` | elite catalog | — |
| `#/compare` | `viewCompare` | two-run metric compare | `?a=&b=` |
| `#/briefs` | `viewBriefs` | brief list/editor | — |
| `#/compose` | `viewCompose` | guided New run | — |
| `#/launch` | `viewLaunch` | quick launch | `?brief=` |
| `#/typologies` | `viewTypologies` | typology catalog | — |
| `#/typology/<id>` | `viewTypologySandbox` | interactive sandbox | — |
| `#/bayes/studies` | `mountStudyList` | study list | — |
| `#/bayes/study/<id>/<phase>` | `mountStudy` | live/overview/data/explain/propose/execute/decide | query |
| `#/bayes/study/<id>/{results,horns,explore}` | `mountStudyResults` | results workspace | query |
| `#/bayes/board` | `mountCompareMethods` | method board | — |
| `#/glossary` | `viewGlossary` | glossary | — |
| `#/hw/screens` | `viewHwScreens` | screen studies list | — |
| `#/hw/screen/<study>` | `viewHwScreen` | screen detail (4 tabs) | `?tab=&row=` |
| `#/hw/cases` | `viewHwCases` | case ledger | `?f=&show=` |
| `#/hw/case/<exp>/<case>` | `viewHwCase` | case detail (5 tabs) | `?tab=&probe=&phase=` |
| `#/hw/readiness` | `viewHwReadiness` | risk/decision board | — |

**Backend-only / missing UI**

| Backend | Endpoint | UI state |
|---|---|---|
| Overview | `GET /api/hw/overview` | **no route/page/nav** |
| New system | `GET /api/hw/assets`, `/drivers`, `/spec-defaults`, `/specs`; `POST /api/hw/spec/{validate,save}` | **no `#/hw/new` / `#/hw/launch`** |
| Compare | `GET /api/hw/compare`, `/compare-matrix` | **no `#/hw/compare`**; no `hw_compare.js` |
| Stage/validate/solve | `data_hw_stage.py` + job kinds; only argv reachable via preview/jobs (`stage_options`, `solve_presets`, `authorization_state` are not exposed over HTTP) | **no dialogs/UI**; solve disabled |
| DSP/crossover | none (`data_hw_dsp.py` absent) | **no `#/hw/case/.../crossover`** |
| Mesh 3D | `GET /api/hw/mesh/<exp>/<case>?part=box\|horn` | wired in `hw.js` via `hw3d.js` (untracked) |
| Panel fit | `POST /api/hw/panel-fit` | wired in `hw_screen.js` (untracked) |

### 5.3 Controls inventory — horn side

| View | Inputs / controls | Actions | URL state |
|---|---|---|---|
| Home | "How to use" guide (remembered in `hl-guide-seen`); running/idle GPU card; CPU lane card; leaders filter "show all"; queue tabs; quick links | navigate | guide flag |
| Runs | search box; brief / family / version / objective selects; mode select (screen/verify/has-verify); sort (active/date/best J/name); default recent-active, all versions/briefs | open run; compare | **no URL state** |
| Run detail | KPI strip; tabs Overview/3D/Balloon/Evolution/Design cloud/QD atlas (conditional)/Compare; `Full report ↗` or `Make full report`; **Export STEP (top 3)**; global "show starting design" checkbox; isobar `Rectangular \| Globe \| Full globe`; beamwidth H/V, DI, on-axis, impedance, wall-section, 3D; "Continue this run" card with N evals | report, STEP, continue, compare | tab via path; toggles local |
| Compose | **1 Shape**: multi-select typology/config cards, disabled entries visible with reason, seed preview; **2 Brief**: source radio (new / from typology / reuse existing), full editor (description, symmetry, verify_only, objective version, coverage H/V, band low/high, DI target/slope, z_min, six weights, envelope W/H/D, exit radius/angle, throat policy, frequency-weight rows), validation; **3 Run**: run mode, exact `<pre>` command, Launch | Clear picks; Save brief; Preview; Launch | no draft persistence |
| Quick launch | Job type radio (Campaign/Search/Dry-run); campaign: brief, tier (dry-run/screen/compare, default screen), family picker with fit reason; search: config, budget **200 (1–5000)**, CMA seed **1234**, restarts mode + max **2 (0–64)**, brief; dry-run: config; command preview; job list 2 s poll | Start; cancel | reads `?brief&families&tier`, does not write |
| Briefs | source grouping/filter; typology-brief picker; "New brief"; editor; save name; per-field hints; server validation | Save; launch from brief | — |
| Typologies | family cards grouped; per-brief "▶ screen" pills; disabled entries marked | Open sandbox; launch | — |
| Typology sandbox | per-knob sliders with editable min/max; "edit search boxes"; "search limits only"; Morph / Guiding-curve / AZ-law cards with per-knob search toggles; H/V + mouth sections; live 3D; Save bounds with all-or-nothing rejection | Save bounds; launch | writes URL state |
| Compare | two run selects; filter; "Run B same brief as A" checkbox (default on) | Compare | reads `?a=&b=`, **does not write it**; reload loses the pair |
| Analysis | set selector; headline KPIs; "what to change" actions; scoreboard; objective balance; search-box walls; sensitivity; screen-vs-verify scatter | follow action links; open run | — |
| Elites | elite catalog entries | open designs | — |
| Bayes | study list/roots; phase tabs (live/overview/data/explain/propose/execute/decide); policy cards; candidate table; decision select + rationale; package lane/deadline; results tabs (overview/horns/explore); search/sort/state filters; 3D/balloon inspector | create/revise/child/queue/launch/cancel/decide/verify | `?root&solve&tier&design` |
| Status | GPU lock card, CPU lane, VRAM, hosts, disk, night card, current run, queue tabs; stop is two-step (arm); `gpu-clean` confirm | stop/clean (as permitted); 10 s in-place poll | no URL state |
| Glossary | searchable terms | — | — |

### 5.4 Controls inventory — horn + woofer side

#### Screens list (`#/hw/screens`)

| Element | Behaviour |
|---|---|
| KPI pills | study count, file count, schema chips, unreadable-file count |
| Table (desktop) | Study id/dir · When (file mtime) · Horn (brief, design hash, quality) · Drivers · Shortlist · Panel-fit rejected · Claim + replay chip |
| Cards (<700 px) | same fields as a `<dl>` card grid |
| Row click / Enter / Space | opens `#/hw/screen/<study_id>` |
| Empty state | "No screens yet" + "Start a new system →" (link to a **missing** route today) |
| No filters/sort; query string ignored | unlike Cases; a known polish gap (the route accepts state nothing produces) |

#### Screen detail (`#/hw/screen/<study_id>`)

| Element | Behaviour |
|---|---|
| Header | eyebrow `Horn + woofer · Screen`, study id, pills, claim warn "Heuristic screen — no single winner, not a validated ranking" |
| KPIs | drivers, boxes considered, kept, Pareto front, shortlist, panel-fit rejected |
| Tabs | `Shortlist` · `Trade-offs` · `Rejected` · `Panel fit` (URL `?tab=`) |
| Shortlist | sortable columns; driver, reason, box W×H×D, net L, tuning, port cm², F3, XO, match error H/V, excursion margin, port velocity ratio, footprint, feasibility chips; **radio** row pick; Enter on row picks |
| Trade-offs | X/Y axis selects over `numeric_axes`; kept dots, Pareto ringed, shortlist filled, rejected hollow; click selects the same row |
| Rejected | ledger grouped by stage; filter by reason prefix and driver; verbatim reasons |
| Panel fit | row picker; **Real driver (Sd-derived)** vs **BL demo transducer** toggle; front-height slider 100–2000 mm; port-area slider 5–600 cm²; verdict + exact reason; `POST /api/hw/panel-fit` recompute (pure Python) |
| Toolbar action | "Check in Boundary Lab…" **disabled** with "arrives in a later phase" (P6) |
| URL | `?tab=<shortlist\|tradeoffs\|rejected\|panel>&row=<candidate_id>` |

#### Cases (`#/hw/cases`)

| Element | Behaviour |
|---|---|
| KPI strip | solved, staged, stage failed, solve failed, recorded, empty |
| Filters | Boundary Lab cases · In registry · Solved · Problems · Everything (`?f=`) |
| "Show superseded / empty" | reveals `empty`/`stage_failed`/`solve_failed` (`?show=all`) |
| Groups | collapsible by experiment; newest expanded; row: case, state pill, motor/shape badges, box, horn offset + clearance, solved band |
| Row | click/Enter opens `#/hw/case/<exp>/<case>`; token sub-row shows verbatim tokens + note |
| Readiness link | opens the risk board |

#### Case detail (`#/hw/case/<exp>/<case>`)

| Element | Behaviour |
|---|---|
| Header | eyebrow, title (`#ref · gate` or experiment), mono key, pills: state, fidelity, motor, shape, clearance, manifest integrity, kind |
| Status band | reconciles solved vs staging; refusal tokens; placeholders |
| KPIs | freqs and band, on-axis woofer @1 kHz dB/2.83 V, on-axis horn @1 kHz dB/(m/s), gap mm, box L |
| Tabs | `Overview` · `Geometry 3D` · `Response` · `Polars` · `Provenance` (`?tab=`) |
| Overview | to-scale 2-D front/side elevations + clearance dimension; box/horn table; Related (parent staged project, paired case, all cases); registry note |
| Geometry 3D | lazy three.js two-body scene: box opacity 15/45/85 %, horn visibility, clearance line, reset; probe positions disabled with "not recorded"; 2-D fallback; dispose on route change |
| Response | per-excitation \|p\| and phase; probe `<select>`; `Phase: wrapped`/`unwrapped` toggle; LF "not solved" hatch + Fb marker; observation caption |
| Polars | H/V heatmaps; per-channel; observation caption; no DI-from-cuts |
| Provenance | engine (BEAT 0.7.0, Julia, float32, quadrature, condensation, symmetry), BL version/SHA pins, phasor, request/run/log SHAs, validate verdict, motor cross-checks; Copy buttons |
| Toolbar | only `← All cases` today; **no Compare, Crossover, Validate, Solve** actions yet |
| URL | `?tab=&probe=&phase=` |

#### Readiness (`#/hw/readiness`)

| Element | Behaviour |
|---|---|
| Risk table | R1–R17: level, status, WP, title, evidence, blocked_by |
| Decisions | 6 owner decisions with recommendation and status |
| Source | `docs/research/system_woofer_2026-11-18/readiness.yaml` (never inferred) |
| Filters | planned by level/status (P1) |

### 5.5 Design system and UX patterns

| Pattern | Implementation | Use |
|---|---|---|
| Typography | Bricolage Grotesque / Spline Sans / Spline Sans Mono (Google Fonts) | brand + data |
| Themes | CSS custom properties; dark default, light toggle; `?theme=` override | all pages |
| Page header | eyebrow + `<h2>` + mono id + provenance `pill-row` | hw pages (P1) |
| Verdict-first KPIs | `.kpis` strip | Overview, Screen, Case, Run |
| Toolbar | `.run-toolbar` = `nav.run-tabs` + `.run-actions` | tabs + actions |
| Figures | `.fig` + `.fig-head` + `.seg-toggle` + `.cap` + `.legend` | every chart |
| Tables | `.tbl-wrap` with sticky headers; `.hw-table-view` scroll hints; card fallback <700 px | lists |
| State chips | `.pill.good/warn/bad`, `.alert.{error,warn,info}`, `.hint[role=status]` | fidelity, refusal, placeholder |
| Skeletons | `skel()`/`busyDone()` | async pages |
| Glossary | `glossary.js` `TERMS` + `tip(key,label)` | technical labels |
| Charts | SVG, `data-chart`, `aria-label`, width measured after insertion | dispersion, response, polars |
| 3D | three.js r160 importmap, `[data-v3d]` dispose | run geometry, balloon, hw case |
| Theme preference | `hl-theme` localStorage + OS fallback | global |
| Accessibility | `aria-pressed` toggles, `aria-current` tabs, `role=status/alert`, keyboard rows, focus return on dialogs | target |
| URL state | tab/filter/row/probe/phase/run pairs in the hash | back/forward/reload |
| Responsive | 1280 / 1009 / 768 / 375 px checks; tables scroll inside `.tbl-wrap`; charts measure container | target |

Owner-recorded preferences (from the 2026-11-14 UX pass): keep the rainbow 3 dB isobar bands with thin
inter-band lines (no chunky lines/halos); Boundary Lab is the reference for directivity layout; verdict
first; long ids must wrap, not widen the page.

### 5.6 Front-end bugs and weaknesses

| ID | Issue | Evidence | Impact |
|---|---|---|---|
| G1 | No Overview route/page/nav | `app.js` ROUTES; `hw_overview` backend | users land on Cases with no "where am I / next step" |
| G2 | No New-system wizard / Quick-launch; `#/hw/new` CTA is a dead route | `data_hw_new.py` backend; `hw_screen.js` empty-state link; no `app.js` route | P5 backend unusable; the only funnel CTA ends in "Unknown view" |
| G3 | No Compare UI; CODE_MAP names a phantom `hw_compare.js` | `data_hw_compare.py` + `/api/hw/compare`; no file/route | P4 backend invisible; docs overstated |
| G4 | No crossover/DSP page | no `data_hw_dsp.py`; decision 3 | P7 absent; system sum impossible by design |
| G5 | No stage/validate/solve dialogs; `stage_options`/`solve_presets`/`authorization_state` are not exposed over HTTP; the screen button still says "arrives in a later phase" although gate C is answered | `data_hw_stage.py` untracked; only argv via preview/jobs | P6 actions absent; stale copy; solve intentionally gated |
| G6 | **Partial commit breaks the app** | `app.js:21` imports untracked `hw_screen.js`; `hw.js:19` imports untracked `hw3d.js` | blank page / boot watchdog on a tracked-only checkout |
| G7 | hw pages use `<h1>` + section-header | G0 handoff §11.1 | house-style inconsistency (P1 fix in flight) |
| G8 | Clearance verdict shown three times on one case page | pill + KPI + box table (`hw.js:486,641-648,711-713`) | redundancy, not the intended "once per surface" |
| G9 | Cases KPIs omit recorded/empty in old build | G0 §11.3 | fixed in current code — verify |
| G10 | `hw.js` keeps a private `GLOSS` | G0 §11.4 | glossary drift; `glossary.js` grew 65 lines uncommitted |
| G11 | Polar chart measured 300 px then CSS-stretched | G0 §8.5 | distorted maps |
| G12 | 375 px overflow | ISSUES 156-157; CONTINUITY 277 | mobile layout; claimed fixed, verify |
| G13 | Shortlist row height/radio, screens clipping, panel-fit semantics, trade-off plot size | ISSUES 156-157 | P1/P2 polish |
| G14 | Disabled actions often tooltip-only | UX rule §8.2; 3D probe control | accessibility |
| G15 | `data_hw.py` imports `meshio`; static analysis reports unresolved import | `data_hw.py:394,439` | mesh endpoints may fail if `meshio` absent in a cloud env |
| G16 | No browser checklist in CI | `tools/gui/browser_check.py` exists; default routes only Cases+Readiness | regressions slip |
| G17 | Preview can lie for bridge geometry jobs | non-hw preview hardcodes `"hornlab-search "` (`server.py:680-683`) while the job runs `python tools/geometry/<cli>.py` | user sees a different command from the one executed |
| G18 | `hw_overview` backend not routed | `server.py:534`; no `app.js` route | dead endpoint |
| G19 | Readiness source is a YAML file, not live case data; evidence not linked | `readiness.yaml`; `hw.js` renders text only | stale labels if cases change; no evidence jump |
| G20 | Compare selection is read from `?a&b` but never written | `app.js` Compare view | reload/share/back loses the pair |
| G21 | Theme switch/resize can wipe forms | `app.js` mutation observer re-route + limited snapshot | Compose picks, family checkboxes, brief rows lost |
| G22 | Static assets are `Cache-Control: no-store`; run-summary cache is unbounded | `server.py:716-721,799-807`; `data.py:217-229` | slow first load; memory grows with run count |
| G23 | System jobs have no home in Status | Status renders no job list; Launch list is horn-side | a GUI `hw-*` job is invisible except on Launch |
| G24 | GPU-busy gating is inconsistent in Launch | only search disabled; campaign checked at click; init forces enabled | button looks live during a busy GPU, then errors |
| G25 | Document title/focus never update on route change | `index.html:6`; `app.js:264-310` | tab ambiguity; screen readers not told the view changed |
| G26 | Static type diagnostics in `server.py`/`data_hw.py` | LSP: `Timer.warm_done`, `log_message` signature, None subscripts, meshio | not verified runtime failures; clean up for maintainability |

### 5.7 Ranked UX/architecture recommendations

| # | Problem | Change | Effort | Dependency | Benefit |
|---|---|---|---|---|---|
| 0 | **Tracked diff is not runnable alone** | Commit `hw3d.js`, `hw_screen.js`, `data_hw_stage.py` together with the `hw.js`/`app.js` edits; add an import smoke test | S | none | stops a boot-breaking partial commit |
| 1 | No "next step" page | Ship `#/hw` Overview: KPIs, 7-step progress, next-step card, recent screens/cases | M | backend `hw_overview` exists | orients every user |
| 2 | No way to start a system | Ship `#/hw/new` 4-step wizard + `#/hw/launch` | L | P5 backend, gate B answered | unlocks the funnel |
| 3 | Cases are inert | Add toolbar actions Compare…, Crossover… (locked), Validate, Solve… (gated) | M | P6 + decision 6 | turns ledger into workflow |
| 4 | Compare backend unused | Ship `#/hw/compare` + 2×2 matrix; mismatch tokens | M | P4 backend | decision support |
| 5 | Funnel is manual | `system funnel` command + GUI launcher; deterministic ledger | L | WP6, decisions 3/6 | reproducibility |
| 6 | Module-load fragility (repeat of #0) | Keep the trio in one commit; add the import smoke test to CI | S | — | stops a broken GUI |
| 7 | Monolithic `hw.js` | Split per view (`hw_cases.js`, `hw_case.js`, `hw_readiness.js`) with shared helpers | M | — | reviewable, testable |
| 8 | Fidelity/refusal ambiguity | One badge component + one token gloss source, used everywhere | S | — | honesty at a glance |
| 9 | Charts distort | Set `data-chart`/width before draw; add browser check to CI | S | — | legible maps |
| 10 | Accessibility gaps | Visible reasons for disabled actions; keyboard dialogs; focus return; ARIA labels | M | — | usable without a mouse |
| 11 | Mobile reflow | Test 375 px every page; card fallbacks; table scroll wrappers | M | — | field use |
| 12 | Store drift | Relocatable manifests + `--system-store` UI hint; no absolute paths | M | migration | cloud/CI portability |
| 13 | Doc drift | Generate CODE_MAP/INDEX rows from the tree; delete phantom rows | S | — | less senior time wasted |
| 14 | No system data view | Add a case-table export button and a "download CSV" link | S | export script | lets users take data |
| 15 | No real-BL smoke in GUI | "Validate" action + last-20-log error surface | M | R11, gate C answered | catches BL regressions early |

### 5.8 The intended 7-step story, mapped

| Step | Copy | Route today | State |
|---|---|---|---|
| 1 | Pick a horn | none (`#/hw/new` missing) | backend inventory exists (`/api/hw/assets`) |
| 2 | Pick woofer drivers | none | backend catalog exists (`/api/hw/drivers`) |
| 3 | Set box limits/targets | none | backend spec defaults/validate/save exist |
| 4 | Screen | `#/hw/screens` (read-only) | screen UI works; launch wizard missing |
| 5 | Check in Boundary Lab | none | stage/validate backend partly exists; dialogs missing |
| 6 | Solve | none | solve backend exists; gated by decision 6 |
| 7 | Read results / compare / crossover | `#/hw/case/...` (read-only) | case detail works; compare/crossover missing |

The fastest UX win is step 1/2/3 (the wizard) because the backend already exists and gate B is
answered. The fastest trust win is step 5/6 (actions) because it turns the read-only ledger into a
verified pipeline — but it must wait for decision 6 and the R11 real-BL lane.

---

## 6. Data package: what exists, how to consume it, how to regenerate it

The local `runs/` and `system_runs/` trees are gitignored and not available to a cloud agent. Two
committed exports bridge that gap. **Use these; do not try to reconstruct local paths.**

### 6.1 The four data surfaces

| Surface | Size / count | Visibility | Best for |
|---|---|---|---|
| `dataset/` | 42,179 records (36,016 ok), 85 shards, 7,880 MB, 2026-10-13..2026-11-19 | local (index/shards present; per-record npz local) | Full solve distribution, training, metric statistics |
| `runs/` | 710 timestamped run dirs (866 dirs total), 807 `search.ndjson`, 51,192 rows | local only | Convergence, per-run config, full complex response |
| `docs/top_designs/` | 52 groups, 437 designs, 437 with arrays, 3,496 arrays; 632 KB CSV + 6.4 MB JSON + 13.8 MB NPZ | committed export | Cross-typology top designs, acoustic comparison |
| `docs/system_data/` | 37 case rows × 53 columns; 5 screen files / 2 unique studies | committed export | Horn+woofer case census, screen shortlists, provenance |
| `system_runs/` | 37 case dirs: 5 solved, 27 manifest-only staged, 3 refused, 2 invalid/empty; 5 BL run trees | local only (junction) | Full BL manifests, per-frequency npz, evidence |

### 6.2 Horn export — `docs/top_designs/`

**Script:** `tools/data/top_designs.py` (read-only over `runs/`).

```powershell
.venv\Scripts\python.exe tools\data\top_designs.py                    # all three files
.venv\Scripts\python.exe tools\data\top_designs.py --no-acoustics     # fast manifest
.venv\Scripts\python.exe tools\data\top_designs.py --group-by score-config
.venv\Scripts\python.exe tools\data\top_designs.py --exclude-unversioned
```

**Files:**

| File | Schema |
|---|---|
| `top_designs.csv` | 437 rows × 161 cols: `typology, score_set, rank, objective, design_hash, param_*, term_*, metric_*, dimensions, run_rel, config_sha, score_config_sha, target_sha, acoustics_id` |
| `top_designs.json` | `tool, schema_version, generated_utc, source{runs_root, repo_head, tool_path}, grouping, counts, score_configs, runs, groups, designs, acoustics, outputs` |
| `top_designs_acoustics.npz` | `<acoustics_id>__freqs_hz`, `h_angles_deg`, `v_angles_deg`, `spl_h_db`, `spl_v_db`, `balloon_dirs`, `spl_balloon_db`, `z_throat` |

**Verified snapshot:** generated **2026-11-19T23:40:55Z**, HEAD `ddfba68`; counts: 51,192 rows
scanned, 44,532 ok, 43,379 GPU, 6,660 failed, 1,153 not GPU, 807 ndjson files, 37,588 unique scored
physical solves, 52 groups, 437 selected, 0 missing design dirs. CSV is 437 × 161.

**Quick queries:**

```python
import json, csv, numpy as np
rows = list(csv.DictReader(open("docs/top_designs/top_designs.csv", encoding="utf-8")))
best_v10 = min((r for r in rows if r["score_set"] == "v10"),
               key=lambda r: float(r["objective"]))
print(best_v10["typology"], best_v10["design_hash"], best_v10["objective"])
z = np.load("docs/top_designs/top_designs_acoustics.npz")
aid = best_v10["acoustics_id"]
spl = z[f"{aid}__spl_balloon_db"]
```

**Caveats:** never rank J across score sets; a version group can contain multiple briefs (use
`score_config_sha` + `target_sha`); selected designs are top-of-group, not a random sample; raw complex
pressure is absent; the live night may have appended solves after the snapshot.

### 6.3 System export — `docs/system_data/`

**Script:** `tools/data/system_cases.py` (read-only over `system_runs/`; stdlib export).

```powershell
.venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
```

**Files:**

| File | Contents |
|---|---|
| `system_cases.csv` | 37 rows × 53 columns; one row per case dir; flat, spreadsheet-friendly |
| `system_cases.json` | full manifest: `tool, schema_version, generated_utc, source, readiness, census, diagnostics, cases` |
| `system_screens.json` | 5 screen files / 2 unique study ids; counts + shortlist/kept rows |
| `README.md` | schema, usage, caveats (generated by the export lane) |

**Verified census (2026-11-19T23:57:50Z):**

| Metric | Value |
|---|---|
| Cases scanned / included | 37 / 37 |
| By status | solved **5**, staged **27**, refused **3**, invalid **2** |
| Experiments | 12 |
| Declared in `readiness.yaml` | 9 (0 declared missing on disk; 28 on disk not declared) |
| By fidelity | `COUPLED_VENTED_FEM_BEM_LEM` 7, `UNDECLARED` 30 |
| Manifest integrity | verified 34, mismatch 1, unknown 2 |
| Run-manifest integrity | verified 2, unknown 35 |
| Diagnostics | 3 (2 missing manifests, 1 known pilot payload-SHA mismatch) |
| Screens | 5 files, 2 unique study ids (`65f6db3e8c8e8f86`, `27616eedee09009f`), 30 shortlist rows, 432 kept rows |
| Exporter tests | `tests/test_tools_data_system_cases.py`: **16 passed** (2026-11-20 verification) |

**Important semantics**

- `status` is derived from the case dir: `solved` = `run/manifest.json` with `status=="complete"`;
  `staged` = manifest only; `refused` = a recorded BL/own refusal; `invalid` = missing/malformed.
- **30 of the 37 dirs are not "solve cases."** They include vented generator outputs, assembly
  prep, pilots, portfolios, and stage attempts. Only the readiness-declared 9 are the solve-relevant
  registry: 5 solved, 2 staged (#6/R0), 1 refused (R4 tower), and the 0 mm-offset 62864 case
  (staged; its `BODY_CLEARANCE_VIOLATION` verdict is declared in readiness/handoff and proven by the
  R16 replay, but the case dir carries **no `payload.clearance` block**, so the flat export reports
  `clearance_status=not_recorded` — a status-fact/prose distinction, not a contradiction).
- Fidelity/motor/transducer shape/gate come **only** from `readiness.yaml`; undeclared is
  `UNDECLARED`. Status facts come from the case dirs.
- `clearance_status` is `not_recorded` on any case whose manifest carries no `clearance` block —
  solve-only cases (the gate runs on the parent staged case) and the 62864 staged case (its verdict
  exists in readiness/handoff/R16 replay, not in `payload.clearance`). The GUI resolves the parent;
  the flat CSV does not.
- The one manifest mismatch is the **known broken first pilot manifest** from `PILOT_EVIDENCE` §5
  (left untouched by immutability as the failure record), not a new corruption.
- The two invalid dirs are abandoned/empty stage dirs (`63032`, `06644`).

**Quick queries:**

```python
import json
j = json.load(open("docs/system_data/system_cases.json", encoding="utf-8"))
print(j["census"])
solved = [c for c in j["cases"] if c["status"] == "solved"]
for c in solved:
    print(c["case_key"], c["n_frequencies"], c["freq_min_hz"], c["freq_max_hz"],
          c["motor"], c["fidelity"])
```

### 6.4 How the two datasets join

| Join key | From horn export | To system export |
|---|---|---|
| `design_hash` | top-designs `design_hash` | system case `notes` / horn mesh provenance; system `asset_id` is a domain-separated hash, not the design hash |
| `asset_id` | not in top-designs CSV | `readiness.yaml` / case manifest `asset_id` |
| `project_sha256` | — | system case + BL run manifest |
| `mesh` SHA | top-designs `acoustics_id` includes mesh/solve hashes | case manifest `horn_mesh_sha256` |
| `score` | horn `objective` per version | **no system score**; do not join on J |

**Do not** join a horn J to a system case as if it were a system score. The system layer has no
scalar objective and no calibration yet.

### 6.5 What the exports deliberately do not contain

- Raw complex pressure `p_h/p_v/p_balloon` (local `response.npz` only).
- The full BL per-frequency arrays (local `system_runs/<case>/run/frequencies/*.npz`).
- The BL engine's internal assumptions list beyond the manifest fields.
- Any inferred fidelity/motor/label.
- Any fabricated/summed system curve.

### 6.6 Recommended analysis questions the data can answer

1. **Horn side:** per typology/version, what are the best J, dimensions, DI/ripple/beamwidth
   trade-offs, and which knobs saturate at bounds? (Use `top_designs.json` + `groups`.)
2. **Horn side:** which typologies are under-represented or never solved? (Use `groups` census and
   `docs/reference/TYPOLOGIES.md`.)
3. **System side:** which cases are solved vs staged vs refused, and what exactly differs between
   paired cases (motor A/B #4/#5, G6 #2/#3)? (Use `system_cases.json` + `pair_with`.)
4. **System side:** which screen shortlist rows survive the BL panel-fit gate, and why were the
   others rejected? (Use `system_screens.json` + `rejected_ledger`.)
5. **Funnel:** how many screen rows are declared, how many reach stage, how many solve, and what is
   the loss at each gate? (Join screens → cases by `study_id`/`candidate_id`; currently manual.)

### 6.7 Reproduce and verify

```powershell
# horn export
.venv\Scripts\python.exe tools\data\top_designs.py
.venv\Scripts\python.exe -m pytest tests\test_tools_data_top_designs.py -q

# system export
.venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
.venv\Scripts\python.exe -m pytest tests\test_tools_data_system_cases.py -q
```

Both exports are deterministic apart from `generated_utc` and any live-tree changes. Regenerate after
a night finishes and commit the refreshed bundle with the code that produced it.

---

## 7. Remaining implementation, decisions, and sequencing

### 7.1 Status ledger

#### System stages and gates

| Item | Status | What exists | Missing |
|---|---|---|---|
| W0 baseline | DONE | machine/repo/BL truth, driver YAMLs, frozen `contracts.py` v1, 149 passed + 1 skip at W0 | — |
| W1 full-domain horn | DONE | closed full-domain mesh `f04827bc5973`, 5,950 tri / 2,977 pts, 0 free edges | — |
| W2 BL staging | DONE | vented R0 + horn assembly R2 staged through BL host; validate rc 0; generation reproducible except mesh bytes | — |
| W3 smoke solve | DONE | 3/3 freqs, complete manifest, residuals 0.0, delay exact | — |
| G4 wide basis | DONE | 25/25, 200–2500 Hz, 5 probes + 37-pt H/V polars | — |
| G5 DSP replay | DONE (limited) | 12 presets; polarity 0.0; delay 4.9e-16 rad; mixed-ref sum refused | calibration policy for a real sum |
| G6 geometry challenge | DONE | +10 mm horn offset; max rel delta 0.356–0.575 | only one offset step |
| G7 false-negative audit | NOT STARTED | — | the audit |
| WP1 LF band | NOT STARTED | no data <200 Hz | 20–200 Hz overlay, Fb/port check |
| WP2 motor×box matrix | PARTIAL | #4/#5 solved; #6/R0 staged | solve #6 + demo-default = 4/4 |
| WP3 real-motor assembled | NOT STARTED | no assembled case with real motor | stage+solve R2 with real T/S |
| WP4 calibration/guards | BLOCKED | guards exist, no policy | decision 3; unify R13 |
| WP5 convergence | NOT STARTED | one mesh/case, 25 freqs | refinement + densification control |
| WP6 funnel + G7 | PARTIAL | screen/stage/DSP separately | deterministic funnel command + audit |
| WP7 real-shape geometry | BLOCKED | demo shape only | maker CAD, parameterised panel fit, taller-front re-screen |
| WP8 tooling hardening | PARTIAL | R16 clearance gate built; R12/R11/R14 open | byte-check tool, real-BL lane, typed authorization |

#### GUI phases

| Phase | Status | Exists | Missing |
|---|---|---|---|
| G0 | DONE (committed) | Cases, Case detail, Readiness; `data_hw.py`, `hw.js`, `--system-store` | P1 polish |
| G1 | IMPLEMENTED (uncommitted) | Screens list/detail + panel-fit UI in untracked `hw_screen.js`; case polars | commit + browser acceptance |
| G2 | BACKEND ONLY | compare backend + matrix endpoint + tests | no `hw_compare.js`, no route/UI |
| G3 | BLOCKED | nothing | decision 3 + WP4; no `data_hw_dsp.py` |
| G4 | BACKEND ONLY / BLOCKED | hw-stage/validate/solve job kinds; untracked `data_hw_stage.py`; options/auth not exposed over HTTP | dialogs/UI; solve disabled |
| P0 | DONE | merge, `--system-store`, junction, `#/hw/cases` verified | — |
| P1 | PARTIAL (uncommitted) | header/KPIs/glossary/charts/375 px fixes | commit + browser checklist |
| P2 | IMPLEMENTED (uncommitted) | backend committed/tested; `hw_screen.js` untracked | commit UI; browser acceptance |
| P3 | IMPLEMENTED (uncommitted) | mesh endpoint committed/tested; `hw3d.js` untracked but imported by `hw.js` | commit + lifecycle/dispose test |
| P4 | BACKEND ONLY | backend + 8 tests | UI module + route |
| P5 | BACKEND ONLY | backend `data_hw_new.py` + tests | wizard/quick-launch UI |
| P6 | BACKEND ONLY | stage backend + job kinds; options/auth not exposed | dialogs; solve authorization |
| P7 | NOT STARTED | no `dsp-preview` endpoint/UI | locked crossover page + gated sum |
| P8 | BACKEND ONLY | `hw_overview` backend | route/page/nav |
| P9 | NOT STARTED | — | lifecycle tests, screenshots, handback |

### 7.2 Risk register

| Risk | Level | Status | WP | Core issue |
|---|---|---|---|---|
| R1 | CRITICAL | open | WP4 | mixed per-input references; no calibration policy |
| R2 | CRITICAL | open | WP7 | BL-buildable boxes are demo-shape-conditional |
| R3 | CRITICAL | open | WP1 | LF band <200 Hz never solved |
| R4 | HIGH | open | WP2/3 | motor×box matrix incomplete; no real-motor assembly |
| R5 | HIGH | open | — | 2 m not far field; cuts only; no DI/power |
| R6 | HIGH | open | WP5 | no convergence check |
| R7 | MEDIUM | open | WP6 | `E_shape` uncalibrated on box/driver axes |
| R8 | MEDIUM | open | — | analog DSP only; excursion not a joint constraint |
| R9 | MEDIUM | open | WP5 | `float32` null depths |
| R10 | MEDIUM | open | — | BL/BEAT drift; record, don't upgrade mid-study |
| R11 | MEDIUM | open | WP8 | no scheduled real-BL lane |
| R12 | MEDIUM | open | WP8 | evidence byte-checks manual |
| R13 | LOW | open | WP4 | duplicate reference guards |
| R14 | LOW | open | WP8 | `authorized_by` free string |
| R15 | LOW | open | WP7 | 10-inch catalog unverified |
| R16 | LOW | in_progress | WP8 | clearance gate built; commit/replay |
| R17 | LOW | open | WP1 | BL meshed port vs bassbox end correction |

### 7.3 Owner decisions and gates

| Gate | State | Answer / recommendation | Unblocks |
|---|---|---|---|
| A (foreign GUI edits) | RESOLVED | edits were committed by the other lane (`143ff08`) | merge |
| B (P5) | ANSWERED | **"Yes to both (Recommended)"** — GUI may launch CPU screen jobs and write user specs | screen jobs, Save-as |
| C (P6) | ANSWERED | **"Yes (Recommended)"** — GUI-launched CPU stage + validate allowed | stage/validate CPU jobs |
| D | OPEN | decision 6: typed authorization record (who/why/scope) | GUI-started solves |
| E | OPEN | decision 3: calibration policy | crossover sum, DSP ranking, G3/P7 |
| F | NOT TRIGGERED | any frozen-contract/BL-install change | — |

Decisions 1–6 remain `open` in `readiness.yaml`. Recommendations recorded there:

1. Procure 12PR300 drawings; it gates real box-axis work.
2. Both taller-front and keep-371 mm paths need real geometry first.
3. Explicit per-channel calibration records (option a) — recommended.
4. Analog DSP for research; biquads later.
5. Declare a far-field/observation standard before any listening-window curve.
6. Typed who/why/scope authorization record written into the case manifest.

### 7.4 Dependency-ordered plan to a usable v1

| Step | Work | Depends on | Lane / acceptance |
|---|---|---|---|
| 0 | Keep the canonical GUI pointed at the physical store (`--system-store` / junction); never copy or move the store | — | ops; `#/hw/cases` loads, 37 case dirs |
| 1 | **Commit the untracked trio first** (`hw3d.js`, `hw_screen.js`, `data_hw_stage.py`) with the `hw.js`/`app.js` edits; then commit/finish P1–P6 front-end; fix the seven G0 issues; run the browser checklist at 1280/1009/768/375 | P0 | CPU/front-end; every hw page passes console/width/chart/a11y/reload checks |
| 2 | WP8 tooling: `verify_evidence_quotes.py`; one-command real-BL lane; typed authorization record; commit clearance gate | decision 6 for record shape | CPU; scripted checks committed + exercised |
| 3 | WP1 LF band: 20–200 Hz overlay on #4/#5 (+ default-box cell after WP2); Fb/port-velocity check | WP2 optional | CPU `beat_cpu`; complete low-freq manifest, explicit deltas |
| 4 | WP2 matrix: solve #6 + demo-default; record 2×2 deltas | — | CPU; 4/4 cells solved on identical geometry columns |
| 5 | WP3 real-motor assembled R2; A/B vs demo | WP2 geometry | CPU; rc-0 validate, 25/25, deltas recorded |
| 6 | WP5 convergence: one mesh refinement + frequency densification on R2; predeclared tolerances | WP3 preferred | CPU; complex-pressure delta at crossover documented |
| 7 | WP4 calibration policy + guard unification; then G3/P7 crossover sum | **decision 3** | CPU; no manual recomposition; refusal tokens tested |
| 8 | WP7 real-shape geometry: procure 12PR300 drawings; parameterise panel fit; re-screen; taller-front staging | **decisions 1–2** | CPU/procurement; BL validate rc 0 with real geometry |
| 9 | WP6 funnel + G7: shortlist → stage/validate/solve → DSP → Pareto ledger; false-negative audit | WP1–WP5, WP7 | CPU; one deterministic command produces the ledger |
| 10 | P6 actions UI: stage/validate; solve behind authorization record | decision 6 + R11 | CPU; preview shows the real command; solve refused without record |
| 11 | P8 Overview + P9 QA/evidence/handback | P1–P8 | CPU; next step correct for empty/screen/staged/solved states |
| 12 | GPU / CUDA BL backend only if the owner authorizes it | owner | GPU; one solve at a time |

**CPU-only:** all GUI phases, WP1/WP2/WP3/WP5 (BL `beat_cpu`), WP8 tooling, P9.
**Needs real Boundary Lab:** any non-dry-run stage/validate/solve; WP7 acceptance.
**Needs owner decision:** 1/2 (real geometry), 3 (calibration/sum), 5 (far-field), 6 (solve authorization).
**Needs procurement:** 12PR300 cone depth/surround/cap drawings.
**GPU-only:** none required for system v1.

### 7.5 What a senior should do first

1. **Do not start with a new solve.** Start by making the existing evidence legible: commit the P1–P6
   front-end, run the browser checklist, and fix the data/export drift so the cloud can see what the
   local machine already has.
2. **Then close the cheap measurement gaps:** WP1 LF band and WP2 matrix are ~4 CPU solves and resolve
   the two biggest unknowns (Fb and the box axis).
3. **Do not build a system score before decision 3.** Any ranking before a calibration policy is a
   false precision; the current code correctly refuses it.
4. **Do not claim real box buildability before decision 1/2.** The demo-shape panel fit is a filter,
   not a manufacturing verdict.
5. **Keep every new number on the same provenance discipline:** immutable case, sha-self-checked
   manifest, explicit label, refusal token, no inferred fidelity.

### 7.6 Non-goals / do not relitigate

- BEAT/BL compatibility (accepted) and dependency pins (recorded, not a gate).
- Solver/mesher rewrites, new BEM codes, surrogate/backbone work.
- GUI purchase/port from Boundary Lab; everything extends the existing stdlib + vanilla-JS GUI.
- Nonlinear/thermal/port-turbulence claims from a linear model.
- Ranking DSP settings on magnitude-only data.
- CTA-2034 certification claims from simulation.
- Treating the `runs/` or `system_runs/` trees as cloud-visible; they are local provenance.

---

## 8. Known issues — consolidated

### 8.1 Backend / system issues

| ID | Issue | Severity | Evidence | Impact | Suggested fix |
|---|---|---|---|---|---|
| B1 | Mixed per-input references cannot be summed | CRITICAL | R1; `combine.py::_require_compatible`; G5 | every cross-channel number is manual | decide calibration policy (WP4) |
| B2 | Box feasibility assumes BL's demo 200 mm transducer | CRITICAL | R2; `woofer_seed.py:696-702` | real 12PR300 fails panel fit | procure CAD, parameterise panel fit, re-screen |
| B3 | No LF <200 Hz data | CRITICAL | R3 | Fb/LF alignment invisible | 20–200 Hz overlay on #4/#5 |
| B4 | Motor×box matrix incomplete | HIGH | R4 | only seed-box column solved | solve #6 + demo-default |
| B5 | 2 m probes not far field; cuts only | HIGH | R5 | no DI/power claims | declare observation standard |
| B6 | No convergence check | HIGH | R6 | null depths unquantified | WP5 refinement/densification |
| B7 | `E_shape` uncalibrated on box/driver axes | MEDIUM | R7; `SCREENING_EVIDENCE` §2 | screen ranking not validated | G7 false-negative audit |
| B8 | Analog-prototype DSP only | MEDIUM | R8 | no biquad/latency claims | decision 4 |
| B9 | `float32` solves | MEDIUM | R9 | deep nulls precision-limited | one `float64` control |
| B10 | BL/BEAT drift | MEDIUM | R10; `BL_PARITY` §2 | future upgrades need re-validation | record, don't upgrade mid-study |
| B11 | No scheduled real-BL lane | MEDIUM | R11 | two real bugs caught only by real runs | WP8 one-command lane |
| B12 | Evidence byte-checks manual | MEDIUM | R12 | evidence can drift from logs | `verify_evidence_quotes.py` |
| B13 | Duplicate reference guards | LOW | R13 | two token families | unify with WP4 |
| B14 | `authorized_by` free string | LOW | R14 | no registry/scope | decision 6 |
| B15 | 10-inch catalog unverified | LOW | R15 | real-geometry risk | re-verify vendor fields |
| B16 | Clearance gate uncommitted at one point | HIGH | R16; `GUI_SYSTEM_PLAN` §0 | 62864 violation | commit + replay test |
| B17 | BL port vs bassbox end correction | LOW | R17 | tuning comparison ambiguous | document band; WP1 |
| B18 | `pilot --geometry` raises `SchemaError` | HIGH | `optimize.py:167-168`; `drivers.py:150-152` | documented path broken | use a real fidelity label; add test |
| B19 | Pilot "Pareto" is inert | HIGH | `optimize.py:255-262`; `score.py:123-128` | every pilot row dominates | normalise axis dicts to numbers; add test |
| B20 | `_nondominated` is O(n²) | MEDIUM | `woofer_seed.py:1127-1142` | superlinear runtime | sort/dominance tree if breadth grows |
| B21 | Inert spec keys (`port_nfr_range`, placement ranges, beamwidth, `dsp.active`) | MEDIUM | `woofer_seed.py:296-303`, `contracts.py:347-349` | user edits silently do nothing | remove, implement, or document as reserved |
| B22 | `stage.detail.overrides` always `{}` | LOW | `stage.py:289` vs `build_stage_spec` | misleading audit field | read from `spec.source` |
| B23 | Clearance coupling to `purpose=="bem_surface"` | MEDIUM | `stage.py:259-283` | BL label change can fail all horn stages | accept a declared mesh role set |
| B24 | `_fidelity_for` infers from `solve_kind` only | MEDIUM | `reference.py:1201-1207` | label can overstate | consult geometry completeness |
| B25 | Failed solve writes a record; retry in same dir refused | MEDIUM | `reference.py:1089-1108` | operational trap | document; add a `--new-case` helper |
| B26 | `filter_bank` does not range-check | LOW | `dsp.py:65-80` | out-of-range callers | call `validate_dsp_point` inside |
| B27 | Independence check is structural only | MEDIUM | `bl_results.py:478-534` | collinear ports pass | document; optionally rank test |
| B28 | Motor staging hard-codes 12PR300 | LOW | `motor_map.py:67-72` | single-driver path | parameterise |
| B29 | Full-domain rebuild hard-codes one asset | LOW | `horn_full_domain.py:80-84` | other assets need args | parameterise defaults |
| B30 | `run.solve_project` inert / dead `_unused` | INFO | `run.py:101-123`; `optimize.py:336` | not a solver seam | document |

### 8.2 Front-end / GUI issues

| ID | Issue | Severity | Evidence | Impact |
|---|---|---|---|---|
| F1 | hw pages use `<h1>` + `section-header`; house style is eyebrow + `<h2>` | LOW | `GUI_COMPLETION` §11.1 | visual inconsistency |
| F2 | Clearance verdict shown twice (pill row + token row) | LOW | §11.2; `hw.js` comment | duplication |
| F3 | Cases KPIs omit recorded/empty counts | LOW | §11.3 | incomplete census |
| F4 | `hw.js` keeps a private `GLOSS` map | LOW | §11.4 | glossary drift; move to `glossary.js` |
| F5 | Clearance replayed on first load (~0.5 s) | LOW | §11.5 | fine <200 cases; prefetch later |
| F6 | "6 solved" copy vs 5 on disk | MEDIUM | §11.6 | trust the ledger; fix copy |
| F7 | `STAGE_FAILED[<type>]` conflates BL refusal/adapter bug | MEDIUM | §11.7 | don't relabel all as BL refusals |
| F8 | G0 polar chart measured 300 px then CSS-stretched | MEDIUM | §8.5 | distorted charts |
| F9 | 375 px overflow/reflow | MEDIUM | `ISSUES.md:156-157`; `CONTINUITY.md:277` | mobile layout broken; P1 says fixed — verify |
| F10 | Shortlist row height/radio, screens clipping, panel-fit semantics, trade-off plot size | MEDIUM | `ISSUES.md:156-157` | P1/P2 polish |
| F11 | No Overview route/page/nav | HIGH | `app.js` ROUTES; `hw_overview` backend | no "where am I / next step" |
| F12 | No New-system wizard/Quick-launch UI | HIGH | `data_hw_new.py` backend; no `hw_new.js` | P5 unusable |
| F13 | No Compare UI | HIGH | `data_hw_compare.py`; no `hw_compare.js` | P4 backend unseen |
| F14 | 3D viewer is wired but fragile | MEDIUM | `hw3d.js` untracked; `hw.js` imports it | a partial commit breaks module load; no lifecycle test |
| F15 | No stage/validate dialogs | MEDIUM | `data_hw_stage.py` untracked; no UI | P6 actions absent |
| F16 | No crossover page / DSP bench | HIGH | no `data_hw_dsp.py`; decision 3 | P7 absent |
| F17 | Solve button gated with no authorization record | HIGH | decision 6; `HORNLAB_GUI_ALLOW_BL_SOLVE` | P6 blocked |
| F18 | CODE_MAP names `hw_compare.js` which does not exist | MEDIUM | `CODE_MAP.md:158` | docs ahead of code |
| F19 | `data_hw.py` imports `meshio`; LSP reports unresolved import | MEDIUM | LSP diagnostic; `data_hw.py:394,439` | mesh endpoints may fail if meshio absent |
| F20 | GUI job preview may print the wrong prefix for hw kinds (handoff says fix required) | MEDIUM | `GUI_COMPLETION` §5.7 | misleading command preview |
| F21 | Disabled controls sometimes have a tooltip only | MEDIUM | UX rule §8.2 | accessibility |
| F22 | Charts/3D dispose risk across route changes | MEDIUM | P3/P9 plan; `data-v3d` sweep | WebGL leaks if wiring misses |

### 8.3 Docs / operations / integration issues

| ID | Issue | Severity | Evidence | Impact |
|---|---|---|---|---|
| D1 | Test counts quoted as 149/159/261/274/355/861/862 | MEDIUM | multiple docs | stale baselines; always record the command + counters |
| D2 | "6 solved" vs 5 | MEDIUM | `SENIOR_REVIEW_HANDOFF` §3 vs readiness | wrong census |
| D3 | `ACTIVE_STATE.md` last verified 2026-11-18 but contains 11-19 state; omits system GUI and gates B/C | MEDIUM | `docs/ACTIVE_STATE.md` | stale pointer |
| D4 | CODE_MAP system/P4/P5 rows describe files not present | MEDIUM | `CODE_MAP.md:158-159` | doc drift |
| D5 | Worktree vs canonical vs junction | HIGH | `CONTINUITY.md:725-733` | data path confusion; never copy/move |
| D6 | Absolute paths in manifests | HIGH | case manifests; P0 step 0 | store is not relocatable |
| D7 | `R4`/Gate A/decision 3/P0 naming collisions | MEDIUM | readiness/GUI/Fable docs | ambiguous routing |
| D8 | No system `G0–G3`; GUI has G0–G4 | MEDIUM | docs | naming confusion |
| D9 | Pre-existing GUI test failure `test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths` | MEDIUM | P0 baseline | red baseline; do not grow |
| D10 | `dataset/MANIFEST.json` advertises objective versions 1–7 while code has 9/10 | LOW | `dataset/MANIFEST.json` vs `versions.py` | misleading |
| D11 | `docs/INDEX.md` uncommitted with unrelated rows | LOW | git status | merge hygiene |
| D12 | Live night may append after the top-designs snapshot | LOW | README | regenerate after night |
| D13 | Boundary Lab install is read-only and version-pinned | INFO | `BL_PARITY` | upgrades need re-validation |
| D14 | GPU lock defaults to `warn` | INFO | AGENTS.md | measurements must set `refuse` |

### 8.4 What is *not* an issue

- The absence of a scalar system score is intentional until decision 3.
- The refusal to sum mixed references is a feature, not a bug.
- `run.solve_project` being inert is intentional; the sanctioned solve path is `reference.solve` + BL CLI.
- The demo motor's effect is not a code bug; it is a measured limitation (120–144 % basis change).
- A screen shortlist is not a ranking; it is a deterministic funnel.

---

## 9. Architecture assessment and improvement options

### 9.1 What is strong

1. **Provenance discipline.** Domain-separated ids, immutable case dirs, sha-self-checked manifests,
   explicit refusal tokens, and a fidelity ladder are already better than most research codebases.
   Keep them; they are the reason the evidence survives review.
2. **Separation of concerns.** The CPU screen, the BL installed reference, and the DSP replay are
   distinct fidelities with distinct claims. The code refuses to blur them.
3. **Reuse of the horn engine.** `horn_assets`/`horn_import`/`horn_full_domain` reuse the existing
   solve/response/mesh paths instead of forking a second solver.
4. **Honest evidence.** The G5/G6/motor A/B results include the negative results (demo motor is not
   harmless; 10 mm offset changes the woofer channel; the 62864 case is a violation). This is the
   right culture.
5. **No-build GUI.** The stdlib server + vanilla JS + existing chart components keep the GUI
   inspectable and portable; no dependency churn.

### 9.2 What is weak

1. **The system data model is screen-centric, not experiment-centric.** A "case" can be a vented
   generator, a staged assembly, a pilot, a portfolio, a solve, or a failed attempt; the manifest
   payload shape varies by writer. There is no single case schema with optional blocks, so every
   consumer (GUI, export, evidence) re-implements discovery.
2. **The store is not relocatable.** Absolute paths from the worktree leak into manifests. The
   junction works on this machine but is fragile for a cloud/CI consumer.
3. **The GUI is a monolith with backend-first layering.** `hw.js` is 64 KB; `app.js` still owns the
   router and shared helpers; P4/P5/P6 backends exist without UI modules. The code-map docs run ahead
   of the tree.
4. **The system objective is undefined.** The screen has a report-only Pareto; the solve has no
   scalar objective; the DSP has no ranking. That is correct today, but the final architecture needs
   a declared system-level decision function once calibration exists.
5. **Testing is broad but uneven.** 355 test functions in `tests/system`, yet the `pilot --geometry`
   path and pilot dominance are untested; the real-BL lane is manual; the browser checklist is
   scripted but not in CI.
6. **Docs drift faster than code.** Test counts, solved-case counts, file names, and ACTIVE_STATE
   are stale in several places. A cloud agent must reconcile before planning.

### 9.3 Target architecture (recommended)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ L0. SOLVE LAYER (existing, frozen interfaces)                                │
│    design/mesh/solve/metrics/objective/search/dataset/report                 │
│    Contract: Design/Mesh/Solve/Response + run.json + dataset record          │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ HornAsset adapter (read-only)
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ L1. SYSTEM DOMAIN (pure, no BL, no GUI)                                      │
│    contracts.py  (SystemSpec v1, SourceBasis, SystemResponse, ids)            │
│    screen/       (compatibility, piston, bass_reference, drivers, score)      │
│    dsp/          (filter_bank, validate_dsp_point)                            │
│    combine/      (explicit calibration record -> coherent sum)                │
│    calibration/  (NEW: typed per-channel reference records; decision 3)       │
│    objective/    (NEW: declared system objective, versioned; only after cal)  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ SystemCase (typed schema)
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ L2. EXECUTION ADAPTERS (CPU-only unless explicitly authorized)                │
│    boundarylab/  (probe, stage, validate, solve, read; BL's own interpreter)  │
│    jobs/         (one system job at a time; CPU lane lock; preview=real argv)  │
│    provenance/   (immutable case, sha manifest, store-relative paths)         │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ typed case + study index
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ L3. READ MODELS / API (Python readers; no acoustics in JS)                    │
│    cases, case detail, screens, compare, dsp-preview, overview, readiness     │
│    Every number traceable to a manifest/file; refusal tokens as data          │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ JSON
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ L4. GUI (vanilla JS modules, small shared surface)                            │
│    hw_overview.js, hw_new.js, hw_screens.js, hw_cases.js, hw_case.js,         │
│    hw_compare.js, hw_crossover.js, hw_readiness.js                           │
│    app.js: routes + nav only; charts.js/view3d.js reused                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Five concrete moves**

1. **Introduce a typed `SystemCase` schema** with a common header and optional payload blocks
   (`screen`, `stage`, `validate`, `solve`, `dsp`, `report`). Write a single `read_case()` used by the
   GUI, export, and evidence tools. This removes the writer-specific payload branching.
2. **Make the store relocatable.** Write `source_path` relative to `--system-store`; keep an optional
   `original_abs_path` only as provenance. Add a `system-store migrate` dry-run that rewrites
   manifests atomically (never in place without a backup).
3. **Add a calibration record type** (`CalibrationRecord`: per-channel reference, method, evidence,
   scope) and make `combine()` require it. Do not add a system score until this exists; then add a
   versioned system objective that is explicitly not comparable to horn J.
4. **Finish the GUI as modules, not a monolith.** One `hw_*.js` per view, each owning its mount and
   dispose; `app.js` only routes/nav. Keep `data_hw_*.py` one reader per view family. Add a
   `tests/gui_hw_lifecycle.mjs` harness for mount/unmount and a Playwright checklist in CI.
5. **Make the system funnel a single command.** `hornlab-search system funnel --spec … --shortlist N`
   → screen → stage/validate top-N → solve (authorized) → DSP replay → a deterministic ledger with
   fidelity tags. This is WP6; it turns the current manual chain into a reproducible pipeline.

### 9.4 Interface contracts to freeze next

| Interface | Shape | Why |
|---|---|---|
| `SystemCase` header | `case_id, experiment_id, kind, created_utc, status, fidelity, source{...}, payload{...}, integrity` | one reader for GUI/export/evidence |
| `CalibrationRecord` | `channels[{id, per_input, reference_value, reference_unit}], method, evidence_path, scope, approved_by` | makes a coherent sum possible without guessing |
| `SystemScore` (later) | `version, terms[], weights, target, calibration_record_sha, label` | a declared, versioned decision function; never mixed with horn J |
| `JobSpec` | `kind, argv[], cwd, env, inputs_sha, preview, lane, authorization` | one preview/launch path for all hw jobs |
| `CaseReadModel` | JSON with `facts`, `declared` (readiness), `derived`, `refusals`, `links` | stops JS from inferring anything |

### 9.5 Migration order (low risk → high value)

1. Freeze the read model and case schema; write `read_case()` + tests against all 37 existing case
   dirs (including malformed/empty).
2. Move all GUI readers to the read model; keep the URLs unchanged.
3. Commit the P1–P6 UI modules against the read model; browser checklist.
4. Add the export script's schema to the read model so `system_cases.json` and the GUI agree.
5. Add `CalibrationRecord` + `combine()` requirement; then the crossover page.
6. Add the system funnel command; then the system objective (versioned) only if the owner wants one.
7. Only then consider a second GPU or a web deployment; neither is needed for v1.

### 9.6 What not to do

- Do not build a second solver or a second mesher.
- Do not sum the two channels with a hidden fudge factor.
- Do not infer fidelity from file presence in JS.
- Do not make the GUI a job runner without a preview/authorization/lane lock.
- Do not move `system_runs/` while absolute paths are in manifests.
- Do not rank horn J against a system score.
- Do not treat the demo motor or demo transducer shape as harmless.

---

## Appendix A — File map

### A.1 New / changed in this handoff

| Path | Status | Purpose |
|---|---|---|
| `docs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md` | new | this packet |
| `tools/data/system_cases.py` | new (export lane) | reusable system-case/screen exporter |
| `tests/test_tools_data_system_cases.py` | new (export lane) | synthetic tests for the exporter |
| `docs/system_data/system_cases.csv` | new (generated) | flat system case ledger |
| `docs/system_data/system_cases.json` | new (generated) | full system case manifest + diagnostics |
| `docs/system_data/system_screens.json` | new (generated) | screen studies and shortlist rows |
| `docs/system_data/README.md` | new (hand-written) | exporter schema/usage/caveats |
| `tools/data/top_designs.py` | existing | pure-horn GPU-solve exporter |
| `docs/top_designs/*` | existing | committed horn solve bundle |

### A.2 System backend (key files)

```
hornlab_search/system/
  contracts.py            frozen v1 spec/ids/basis
  woofer_seed.py          CPU screen/Pareto/panel-fit
  compatibility.py        E_shape / tier questions
  piston.py               ideal piston
  bass_reference.py       vented-box feasibility
  drivers.py              T/S + geometry schema + fidelity
  score.py                report-only dominance
  optimize.py             pilot
  portfolio.py            diverse-horn screen
  dsp.py                  LR/PEQ/delay/polarity
  combine.py              coherent sum (refuses mixed refs)
  horn_assets.py          saved-horn inventory
  horn_import.py          accel->velocity basis conversion
  horn_full_domain.py     quarter->closed full-domain rebuild
  provenance.py           immutable case/manifest
  reference.py            prepare/validate/solve/report
  cli.py                  module CLI
  geometry/rules.py       fabrication rules
  boundarylab/
    probe.py, run.py, generate.py, runner_vented.py,
    stage.py, runner_stage.py, assemble.py, clearance.py,
    import_results.py, bl_results.py, motor_map.py,
    runner_motor_stage.py
```

### A.3 GUI (key files)

```
hornlab_search/gui/
  server.py               HTTP server, API dispatch, --system-store
  jobs.py                 job kinds, argv, preview, lane locks
  data.py                 horn-side read model
  data_bo.py              Bayesian studies
  data_hw.py              cases/case detail/basis/polars/mesh/overview
  data_hw_screen.py       screens + panel-fit recompute
  data_hw_compare.py      A/B + matrix
  data_hw_new.py          assets/drivers/specs/validate/save
  data_hw_stage.py        stage/validate/solve job payloads (untracked)
  data_studies.py         Bayes study model
  data_verify.py          verify view
  preview.py, study_*.py  helpers
  static/
    index.html, app.js, app.css
    charts.js, glossary.js, view3d.js, sandbox.js
    studies.js, study_charts.js, study_results.js,
    compare_methods.js, verify.js, evolution.js, umap.js, balloon.js
    hw.js                 cases/readiness + case detail
    hw_screen.js          screens list/detail (untracked)
    hw3d.js               two-body 3D viewer (untracked)
```

### A.4 Uncommitted at snapshot (verify before committing)

`docs/CODE_MAP.md`, `docs/CONTINUITY.md`, `docs/INDEX.md`, `docs/ISSUES.md`,
`hornlab_search/gui/jobs.py`, `gui/static/{app.css,app.js,glossary.js,hw.js,index.html}`,
`tools/gui/browser_check.py`, `tools/system/gui_system_job.py`; untracked `data_hw_stage.py`,
`hw3d.js`, `hw_screen.js`, `tests/system/test_gui_hw_stage.py`, `tools/data/top_designs.py`,
`docs/top_designs/`, plus the export lane's new files. Do not stage another lane's work
indiscriminately.

---

## Appendix B — Read-first document index

| # | Doc | Why |
|---|---|---|
| 1 | `docs/research/system_woofer_2026-11-18/SENIOR_REVIEW_HANDOFF_2026-11-19.md` | architecture, R1–R17, WP1–WP8, decisions |
| 2 | `docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md` | P0–P9 build order, acceptance, gates, G0 issues |
| 3 | `docs/research/system_woofer_2026-11-18/GUI_SYSTEM_PLAN_2026-11-19.md` | GUI IA and G0-as-built deviations |
| 4 | `docs/research/system_woofer_2026-11-18/readiness.yaml` | machine-readable risks, decisions, case registry |
| 5 | `docs/research/system_woofer_2026-11-18/FIRST_BEM_EVIDENCE.md` | the only real coupled solves; G4/G5/G6; motor A/B |
| 6 | `docs/research/system_woofer_2026-11-18/SCREENING_EVIDENCE.md` | screen metric, study ids, panel-fit refusal/re-rank |
| 7 | `docs/research/system_woofer_2026-11-18/FIRST_REFERENCE_CASE.json` | case freeze, engine baseline, full-domain mesh |
| 8 | `docs/research/system_woofer_2026-11-18/BASELINE_CONTINUATION.md` | W0 truth and live blockers |
| 9 | `docs/research/system_woofer_2026-11-18/BASELINE.md` | machine/repo/BL install, driver provenance |
| 10 | `docs/research/system_woofer_2026-11-18/BL_PARITY.md` | BL SHA pins, upstream delta, staging evidence |
| 11 | `docs/research/system_woofer_2026-11-18/PILOT_EVIDENCE.md` | screen-only pilot, phase conversion |
| 12 | `docs/research/system_woofer_2026-11-18/PORTFOLIO_EVIDENCE.md` | diverse-horn screen, disagreements |
| 13 | `docs/CONTINUITY.md` lines 245–320, 692–734 | gates B/C verbatim, P2–P4, P0 merge/store |
| 14 | `docs/ISSUES.md` lines 126–176, 317–352 | current GUI status, open D/E, polish |
| 15 | `docs/ACTIVE_STATE.md` | current pointer (stale; read with care) |
| 16 | `docs/CODE_MAP.md` lines 153–159 | system/GUI map (watch `hw_compare.js` phantom) |
| 17 | `docs/meh/M10_BASS_BOX.md` + `docs/meh/00_MEH_CONTRACTS.md` | lumped bass-box/port model |
| 18 | `docs/research/system_woofer_2026-11-18/SOURCES.md` | provenance ledger |

---

## Appendix C — Command cookbook

```powershell
# Interpreter
C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe

# ---- offline tests ----
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" `
    -n 6 --dist loadscope -p no:cacheprovider

# system + GUI focused
.venv\Scripts\python.exe -m pytest tests\system tests\test_gui*.py tests\test_b8_lanes_bounded_gui.py -q `
    --junitxml=<tmp>\hw.xml

# real Boundary Lab staging/validate (no solve)
$env:HORNLAB_BL_REAL_TESTS="1"
.venv\Scripts\python.exe -m pytest tests\system\test_bl_stage.py -q

# ---- dataset / exports ----
.venv\Scripts\python.exe -m hornlab_search.cli dataset stats
.venv\Scripts\python.exe -m hornlab_search.cli dataset verify
.venv\Scripts\python.exe tools\data\top_designs.py
.venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty

# ---- system screen / pilot / portfolio ----
.venv\Scripts\python.exe -m hornlab_search.system.cli list-assets --limit 10
.venv\Scripts\python.exe -m hornlab_search.system.cli list-drivers
.venv\Scripts\python.exe -m hornlab_search.system.woofer_seed `
  --asset-id <ASSET_ID> --spec examples/systems/two_way_80x50_700_research.yaml `
  --limit-boxes 4 --out system_runs\woofer_seed_recon
.venv\Scripts\python.exe -m hornlab_search.system.cli pilot `
  --spec examples/systems/two_way_80x50_700_research.yaml `
  --driver-stem faitalpro_12pr300 --limit-boxes 4 --out system_runs

# ---- BL reference (CPU; real BL for non-dry-run) ----
.venv\Scripts\python.exe -m hornlab_search.system.cli reference prepare `
  --root C:\Users\hunte\Github\boundary-lab --dry-run
.venv\Scripts\python.exe -m hornlab_search.system.cli reference report `
  tests\system\fixtures\bl_results\reference_run --json

# ---- GUI (canonical; store is the physical worktree store) ----
.venv\Scripts\python.exe -m hornlab_search.gui --port 8799 --no-browser --root . `
  --system-store C:\Users\hunte\Hrns\hornlab-woofer-system-wt\system_runs

# browser checklist (Playwright Python 3.13)
& "C:\Users\hunte\AppData\Local\Programs\Python\Python313\python.exe" `
  tools\gui\browser_check.py --base http://127.0.0.1:8799 `
  --out docs\evidence\hw_gui_2026-11-19 `
  --routes "/#/hw/screens,/#/hw/cases,/#/hw/readiness"
```

---

## Appendix D — Glossary

| Term | Definition |
|---|---|
| `asset_id` | Domain-separated sha16 identity of a `HornAsset`; not a design hash |
| `BL` | Boundary Lab, the installed 0.5.0 external system/BEM app; read-only |
| `case` | Immutable `system_runs/system/<exp>/<case>/` directory with a sha-self-checked manifest |
| `CMA-ES` | The horn search optimizer |
| `coupled_bem_fem` | BL solve kind: BEM exterior + FEM interior/vented air |
| `design_hash` | Hash of a horn design parameter set |
| `E_shape` | Relative-shape mean-squared dB difference between horn and ideal piston in an XO band |
| `F3` | Frequency where the LF response is 3 dB below the passband reference |
| `Fb` | Box tuning frequency |
| `fidelity` | The declared tier of a response (`SCREEN_*`, `INSTALLED_*`, `COUPLED_*`, `MEASURED_*`) |
| `full-domain` | Closed horn mesh (not the quarter patch) required by BL under symmetry off |
| `HornAsset` | A saved horn solve exposed to the system layer |
| `J` | Scalar objective, minimised; versioned |
| `manifest` | Self-checksummed JSON provenance record |
| `MAGNITUDE_ONLY` | Complex fields exist but the canonical basis is unproven; phase claims refused |
| `per_input` | The drive reference for a basis (`V_rms` vs `normal_velocity_mps`) |
| `readiness.yaml` | The declared registry for fidelity/motor/shape/gate and R1–R17 |
| `run` | A horn search invocation directory |
| `SCREEN_COMPLEX_APPROX` | Converted complex basis with a declared approximation |
| `study_id` | Deterministic hash of a screen/portfolio input set |
| `system_store` | The root of all system cases/screens (default `<root>/system_runs`) |
| `throat_ext` | Throat extension knobs on the horn |
| `verify` | Horn-side higher-fidelity re-solve of selected designs |
| `WP` | Work package in the senior review handoff |
| `Xmax` | One-way peak excursion, per the driver vendor's definition |
| `z_throat` | Complex throat impedance, ohms |

---

## Appendix E — Data dictionary (exports)

### E.1 `docs/top_designs/top_designs.csv/json`

The CSV is the flat convenience view; the JSON is authoritative for nested blocks.

| Group | Fields |
|---|---|
| Identity | `typology`, `score_set`, `rank`, `design_hash`, `n_selected`, `n_scored` |
| Score | `objective`, `term_*` (normalised terms), `version_source` |
| Params | `param_*` (union of every typology's knobs; blank if unused) |
| Metrics | `metric_*` scalars (`di_mean_db`, `ripple_mean_db`, `flatness_db`, `bw_h/v_mean_deg`, `f11_hz`, …) |
| Dimensions | `bbox_m`, `bbox_quadrant_mm`, `bbox_full_est_mm`, `mouth_width_mm_est`, `mouth_height_mm_est`, `depth_mm_est`, `area_m2_*` |
| Provenance | `run_rel`, `config_sha`, `score_config_sha`, `target_sha`, `acoustics_id` |

JSON adds `score_configs`, `runs`, `groups`, `designs[].metrics` arrays, `designs[].generator`,
`designs[].dimensions`, and `acoustics` metadata. NPZ keys are `<acoustics_id>__<array>`.

### E.2 `docs/system_data/system_cases.csv/json`

The exporter's schema is generated by `tools/data/system_cases.py`; see
`docs/system_data/README.md` for the authoritative field list. At minimum it carries:

| Group | Fields |
|---|---|
| Identity | `experiment`, `case`, `case_key`, `created_utc`, `kind`, `gate`, `ref` |
| Status | `status` (`solved/staged/refused/invalid`), `solved`, `n_frequencies`, `freq_min_hz`, `freq_max_hz`, `backend_id`, `solve_kind`, `completion` |
| Declared | `fidelity`, `motor`, `transducer_shape`, `horn_source`, `pair_with`, `evidence` (from `readiness.yaml`, else `UNDECLARED`) |
| Geometry | box W/H/D, net L, port cm², tuning Hz, horn mesh, offset mm, clearance status/min mm, driver |
| Provenance | `project_sha256`, `run_manifest_sha256`, `request_sha256`, `manifest_payload_sha256`, `manifest_integrity` |
| Notes | `authorized_by`, `notes`, `diagnostics` |

`system_screens.json` carries the screen studies (`study_id`, `input_sha256`, counts, shortlist rows).

---

## Appendix F — Open questions for the owner

1. Real driver geometry: procure 12PR300 drawings now, or accept the demo shape for v0?
2. Box policy: taller front (560 mm) + re-screen, or keep 371 mm and select fitting drivers?
3. Calibration policy: explicit per-channel calibration records (recommended), velocity-driven
   re-solves, or electrodynamic conversion?
4. DSP: analog prototypes for research, or biquad realization in this round?
5. Far-field/observation standard: distance, angular grid, seat window?
6. Solve authorization: typed who/why/scope record (recommended), or a free-form token?
7. Should the GUI launch a system **funnel** (screen → stage → solve → DSP) once decisions 3/6 land,
   or stay a read-only viewer with manual CLI steps?
8. Is a declared system objective wanted at all, or is the system layer permanently a
   report-only/Pareto tool?

---

## Appendix G — Verification log for this handbook

| Check | Result |
|---|---|
| Canonical branch/HEAD | `hornfab-all-2026-11-18`, `ddfba68` at scan; later `9714b39` in docs |
| `dataset stats` | 42,179 records (36,016 ok, 6,163 failed), 85 shards, 7,880.1 MB, 2026-10-13..2026-11-19 |
| `top_designs.py` tests | 11 passed |
| `top_designs.json` | 52 groups, 437 designs, generated 2026-11-19T23:40:55Z |
| `top_designs.csv` | 437 rows × 161 columns |
| System case census | 37 case dirs: 5 solved, 27 manifest-only, 3 refused, 2 invalid/empty; readiness declares 9 (5 solved, 2 staged, 1 refused, 1 violation) |
| System export tests | `tests/test_tools_data_system_cases.py`: 16 passed |
| System export census | 37 rows × 53 cols; manifest integrity 34 verified / 1 mismatch (known broken pilot) / 2 unknown |
| System tests | 355 `def test_` across 35 modules (function count, not pytest cases) |
| GUI focused-data tests | 64 passing (P3/P4 entry) |
| This handbook | code-claim checks by three read-only recon lanes; doc claims marked where unverified |

**Known verification gaps:** the exact current pytest counters were not re-run in this pass (the
repo's tests are expensive and other lanes were writing); the GUI browser checklist was not run;
Boundary Lab was not exercised; no GPU job was started. All are deliberate read-only constraints.

---

## Appendix H — Regenerating this packet

1. Re-run the exports:
   ```powershell
   .venv\Scripts\python.exe tools\data\top_designs.py
   .venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
   ```
2. Re-run the focused tests and the browser checklist (Appendix C).
3. Refresh the census numbers in §0.2 and §4.9–4.10 from the exports, not from prose.
4. Update `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit (repo push rule).
5. Add a row to `docs/INDEX.md` for this handbook and to `docs/CODE_MAP.md` for the export tools.
6. Keep the invariants in §2.3 unchanged unless the owner amends a frozen contract in writing.
