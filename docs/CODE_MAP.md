# Code map

Where things live. Docs: [`INDEX.md`](INDEX.md). Ownership per path: [`../CLAUDE.md`](../CLAUDE.md) "File ownership".
Keep current: a new module or config folder gets a line here in the same commit.

## Pipeline (one candidate)
`design` (params or generator knobs → Design) → `mesh` (Magnus's mesher → .msh) → `solve` (BEM: beat_cuda / beat_cpu /
bempp_cpu) → `metrics` (beamwidth, ripple, DI, impedance) → `objective` (scalar J) → `dataset` (record) ;
`search` drives it (CMA-ES, campaigns), `report` renders it, `cli.py` exposes it.

## `hornlab_search/`
| Path | What it does |
|---|---|
| `cli.py` | All commands: doctor, run, search, verify, report, compare, export-step, families, campaign, gpu-clean, selftest, dataset, surrogate. |
| `config.py` | YAML → Config; briefs (`load_brief`, `--brief`, embedded brief), `--cma-seed`, `generator:` configs, frequency grids; WP2 driver pins (native families pinned to the brief's driver on FRESH briefs; grandfathered on embedded run-configs), WP4 `verify_points_per_octave` HF verify grid, `objective.version`, `solve.cuda_fused` (WP15, beat_cuda only). |
| `types.py`, `constants.py` | Frozen contract types (Design, MeshResult, MetricSet, …); physical constants. |
| `design/families.py` | Legal keys per family (OSSE, R-OSSE, ICW, FREEFORM), validation, mesher config. |
| `design/space.py` | DesignSpace: bounds ↔ [0,1]^k for CMA-ES; dispatches generator configs. |
| `design/generated.py` | GeneratedSpace: generator knobs → FREEFORM Design; provenance; M4: dispatches `generator: {name: grid}` recipes (radius-field + rows kinds) to `grid.design_params`. |
| `design/generators/grid.py` | GRID adapter (WP10) + WP9b rows machinery: radius-field point grid (superellipse p(s), G8 even-cosine a_k(s), G9 phi-termination) and rows kinds (salmon_axisym/salmon_elliptical/lecleach/iwata_ar/toroidal_rollback + lecleach_mod/lecleach_ar internals); quarter and HALF spans (`span: half` = quadrants '14', phi ∈ [−90°,+90°], odd n_phi ≥ 25); LIST harmonic contract (`g_stop_cos2k`/`g_stop_sin2k1`/`g_bend_sin1_mm`, lib-2 C2 basis, phi from horizontal); design_params persistence + validation dispatch + conservative envelope extents. |
| `design/generators/profiles.py` | Classical meridians (conical, exponential, hypex, tractrix) + `splice` (C1 OSSE→tractrix), `throat_blend_mm` knob (OS far-field angle brentq solve), `spherical_salmon` (neutral-name march, area law ≤2e-14), `lecleach` → `lecleach_exact` (Fourcade 2015, R9-J verified: width 0.00 mm vs fig 7), `spherical_wave` (T=1), blend, anchors, perturbation. |
| `design/generators/registry.py` | Typology spec + knobs + brief → FREEFORM params (H/V hybrids, OSSE via Magnus's `profile_points`, envelope; M4: splice/TYPES + throat-blend types + grid/rows envelope estimator branch). |
| `mesh/build.py`, `sizing.py`, `topology.py`, `grid.py` | Mesh build + cache, dof caps, STEP export; pre-solve surface/symmetry checks. |
| `mesh/grid_build.py` | M4 point-grid → mesher route: `PointGridHornGeometry` freestanding + explicit `outer_points` (never BARE), KEYWORDS-only `MeshDensity`, quadrant/symmetry from `sizing` constants ("14" → yz, factor 2), same MeshTooLargeError/topology guards as build.py; NO mesh cache yet (re-mesh per eval; wire-in note + dated SKETCH at EOF: key = recipe JSON + mesh hash, fold lib SHAs in). |
| `mesh/step_build.py` | WP14 CAD→STEP→mesh route: loads `tools/cad/multicell.py` (importlib by path), builds the labelled STEP (OCC `STYLED_ITEM` labels), gmsh OCC import + `advanced_face_order_for_surfaces`, `driver`→tag 2 / `wall`→tag 1 physical groups, 2D mesh + mesher `postprocess_mesh`/`mesh_frequency_validation` → metres `.msh` + `mesh_meta.json` (cad probe block: tool sha + recipe + step sha + face inventory + frequency/repair/topology reports); strict `FREEFORM.cad` 11-key validation. |
| `solve/beat.py`, `bempp.py`, `worker.py`, `cache.py`, `traces.py`, `phasor.py`, `base.py` | BEM backends, persistent Julia host (a dead host is recovered: library clients dropped, re-warmed, candidate retried once), solve cache, boundary traces, phase conventions. |
| `metrics/` | `compute.py` (MetricSet), `polar.py`, `smoothness.py`, `di.py`, `impedance.py`; report-only `spinorama.py`, `beam_shape.py`. |
| `objective/terms.py`, `scalar.py`, `scalar_v2.py` | The six J terms and the weighted sum. v2 (`objective: {version: 2}` in the brief, WP1 senior pass 2026-10-24): detrended ripple, detrended on-axis flatness, Gaussian-beam DI target, optional per-frequency weights — same key set, opt-in; v1 default is bit-for-bit. |
| `targets/spec.py`, `venue.py` | Target dataclass; venue helpers. `spec.py` validates optional `freq_weights` (WP4). |
| `search/evaluate.py` | One candidate end to end: failure cache, envelope check, loading scalars, ndjson rows. |
| `search/cma.py` | CMA-ES search (`budget`, `max_evals`, resume; stops resumably after 3 consecutive `solve_failed`). WP11a: `search.restarts {mode: ipop|bipop, max}` runs up to 1+max ES instances mirroring pycma's own IPOP/BIPOP schedule (`_RestartSchedule`), each with its own `cma/restart_k/` log; `n_new` (non-cached) stays the single global budget; absent key = single-ES bit-for-bit. |
| `search/cma_me.py` | WP11b CMA-ME (`search.algorithm: cma_me`): ribs 0.12.0 GridArchive + EvolutionStrategyEmitter (objectives told as -J; measures = NaN-safe in-band means of bw_h/bw_v, ranges pinned (0,180)°), writes `archive.json` + `archive_heatmap.json` (pinned contract) + `run.json` `qd` stats; deterministic resume replays cached solutions at zero spend; same budget semantics/`SolverUnhealthyError` handling as cma.py. Dispatched from `search/cma.py`. |
| `search/campaign.py`, `hygiene.py` | Multi-family campaigns and leaderboards; Julia/worker-host cleanup. Ctrl-C: child gets a grace period, partial leaderboard marked INTERRUPTED, exit 130; hosts cleared after every job. |
| `search/gpulock.py` | Process-wide GPU lock (`runs/.gpu.lock`); `gpu-clean` CLI refuses while a live job holds it. |
| `gui/` (`server.py`, `data.py`, `jobs.py`, `static/`) | Local web GUI (`hornlab-search gui`, 127.0.0.1): read-only views of runs/campaigns/briefs, allow-listed CLI launcher; stdlib server + vanilla JS, no build step. Contrast/form-visibility hardening plan (proposed 2026-10-24): `docs/GUI_CONTRAST_PLAN.md`. Capability-integration plan for WP1-WP17 + P6 GUI hooks, API contracts, provenance badge matrix, phased build order (proposed 2026-10-25): `docs/GUI_INTEGRATION_PLAN_2026-10-25.md`. |
| `search/gpulock.py` | One-GPU-job lock (if present; beta pass). |
| `search/rundir.py`, `selftest.py`, `nsga.py` | Run directories / run.json; analytic + crosscheck selftests; NSGA-II. |
| `dataset/record.py`, `store.py` | Record schema and the sharded dataset store. |
| `surrogate/` | Phase-2 Stage A surrogate (inactive: gates failed). |
| `report/html.py` | Per-run HTML report. |

## Configs and tools
| Path | What it is |
|---|---|
| `examples/catalog.yaml` | Every family/typology the `campaign` command can run (name, group, symmetry). |
| `examples/briefs/*.yaml` | Design briefs: driver, size envelope, target, weights. `*_12k.yaml`: 12 kHz VERIFY-only copies (NEXT_DEV_PRIORITIES P2; `verify --brief` writes its own `runs/<ts>-verify-<id>`). |
| `examples/typologies/*.yaml` | Generator configs (classical + hybrids + M4: grid_ellipse, grid_ellipse_mod, splice_osse_tractrix, throatblend_hypex, spherical_salmon, salmon_elliptical, salmon_x_shape, salmon_saddle (HALF), lecleach_f90, lecleach_rollback, lecleach_iwata_ar, lecleach_toroidal — `docs/evidence/M4_SMOKE_2026-10-25.md`; labels per lib-2 dossier). |
| `examples/briefs/organic_rollback_1in.yaml` | M4 organic brief: 90×60, band 700–5500 Hz, wide/shallow envelope (rollback horns); the organic catalog group's brief. |
| `examples/*.yaml` | Native-family configs (OSSE, R-OSSE, ICW, FREEFORM) and legacy smoke/adapter configs. |
| `examples/**/*_fusedcuda.yaml` | WP15 fused-CUDA copies of `osse_axi`, `osse_baseline`, `perturbed_osse_hv`, `freeform_sculpt`: `solve.cuda_fused: true`, verify/final caps 12,000 (screen 5,000 unchanged); originals untouched (`docs/evidence/FUSED_CUDA_2026-10-24.md`). |
| `tools/launch_gui.ps1` | Ops helper (owner-declared 2026-10-25): stops ONLY processes whose command line is `hornlab-search ... gui` (searches/campaigns/solver hosts untouched), then starts a fresh `hornlab-search gui` + browser. |
| `tools/review/` | Builds the self-contained review page (`build_review_data.py`, `review_template.html`, `assemble.py`). |
| `tools/rescore/rescore_v2.py` | WP1 offline re-score: v1 vs v2 J over every stored response (report `docs/evidence/OBJECTIVE_V2_RESCORE.md`; the per-record CSV stays local, regenerate with the tool). |
| `tools/overnight/` | Unattended GPU queue (`queue_20261022.ps1`) and stall watchdog (`watchdog.ps1`, keeps Windows awake). |
| `tools/measure_fused_ceiling.py` | WP15 fused-CUDA VRAM ceiling: one solve per fresh process (TOOLCHAIN M2), `nvidia-smi` polled from a daemon thread, verified `worker.shutdown`; `--mesh-only` is the CPU-only res→dof calibration. Numbers: `docs/evidence/FUSED_CUDA_2026-10-24.md`. |
| `tools/m3_measurement_pack.py` | M3 measurement harness (WP5/WP7/WP8): reconstructs a stored run-dir design (`designs/<hash>/design.json`) and re-solves it through the normal `evaluate` path with config overrides (`--set mesh.rear_res_factor=1.5` etc.); `traces` subcommand = `solve_traced` + offline `field_from_traces` field eval at arbitrary radii; `compare` subcommand; VRAM poll thread + verified shutdown; guards: reuses a fresh cache dir, refuses run dirs with ndjson rows. Numbers: `docs/evidence/MEASUREMENT_PACK_2026-10-24.md`. |
| `tools/evidence_bytecheck_m4.py` | M4 evidence byte-check: verifies every quoted token (J/dofs/run-dir + both compare blocks) against the decoded `runs/m4_smoke/final_*.log` logs; run from the repo root; result in `docs/evidence/M4_SMOKE_2026-10-25.md` §2. |
| `tools/evidence_bytecheck_m5.py` | M5 WP11 evidence byte-check: every quoted offline/GPU block (suite counters, ACCEPTANCE coverage, screen budget lines, fired-restart schedule entries, VRAM pair) against the `runs/m5_wp11*/` artifacts; result in `docs/evidence/M5_WP11_2026-10-25.md`. |
| `tools/evidence_bytecheck_m5b.py` | M5B (WP14/16/17) evidence byte-check: fork branch states, install-by-SHA, Julia CUDA testset counters, selftests, 3-arm A/B deltas, the focal-pair gate numbers, cad-echo probes, suite 1325/0/0/0 against the `runs/m6_fork/` + `runs/m5_wp14*/` artifacts; result in `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md`. |
| `tools/cad/multicell.py` | WP14 multicell CAD authoring (build123d 0.13.0, optional `cad` extra): classic WE/Altec frusta-of-pyramids cells (`x = z·tan α_i`, `y = z·tan β_j`), thickened septa (≥ 1.5 mm) from `z_s`, exponential throat manifold; CLI + importable API; exports the labelled STEP via OCC `STYLED_ITEM` styles (`driver`/`wall` exact contract) + round-trip inventory proof; used by `mesh/step_build.py`. |
| `tests/` | Offline suite; `requires_*` / `gpu` / `slow` markers in `tests/conftest.py`. |
| `.opencode/skills/` | Agent skills (opencode project scope, auto-discovered): `hornlab-gpu-job` (per-GPU-job hygiene/capture recipe; exit-3 + tripwire semantics) + `hornlab-evidence` (evidence-doc assembly + pre-publish byte-check) + `hornlab-typology-research` (horn-design grounding: typology dossiers + R9/rename-gate discipline before typology/shape work). |

## External code we depend on (pinned in `pyproject.toml` / `TOOLCHAIN.md`; changed only via our forks, `FORKS.md`)
`hornlab_mesher` (geometry + gmsh), `hornlab_beat_bem` (GPU/CPU BEM, Julia), `hornlab_bempp_bem` (CPU cross-check),
`hornlab_plots` — Magnus's (GitHub `m3gnus`) packages, installed in `.venv`.
