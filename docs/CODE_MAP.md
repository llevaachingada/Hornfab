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
| `design/generated.py` | GeneratedSpace: generator knobs → FREEFORM Design; provenance. |
| `design/generators/profiles.py` | Classical meridians (conical, exponential, hypex, tractrix; Le Cléac'h disabled), blend, anchors, perturbation. |
| `design/generators/registry.py` | Typology spec + knobs + brief → FREEFORM params (H/V hybrids, OSSE via Magnus's `profile_points`, envelope). |
| `mesh/build.py`, `sizing.py`, `topology.py`, `grid.py` | Mesh build + cache, dof caps, STEP export; pre-solve surface/symmetry checks. |
| `solve/beat.py`, `bempp.py`, `worker.py`, `cache.py`, `traces.py`, `phasor.py`, `base.py` | BEM backends, persistent Julia host (a dead host is recovered: library clients dropped, re-warmed, candidate retried once), solve cache, boundary traces, phase conventions. |
| `metrics/` | `compute.py` (MetricSet), `polar.py`, `smoothness.py`, `di.py`, `impedance.py`; report-only `spinorama.py`, `beam_shape.py`. |
| `objective/terms.py`, `scalar.py`, `scalar_v2.py` | The six J terms and the weighted sum. v2 (`objective: {version: 2}` in the brief, WP1 senior pass 2026-10-24): detrended ripple, detrended on-axis flatness, Gaussian-beam DI target, optional per-frequency weights — same key set, opt-in; v1 default is bit-for-bit. |
| `targets/spec.py`, `venue.py` | Target dataclass; venue helpers. `spec.py` validates optional `freq_weights` (WP4). |
| `search/evaluate.py` | One candidate end to end: failure cache, envelope check, loading scalars, ndjson rows. |
| `search/cma.py` | CMA-ES search (`budget`, `max_evals`, resume; stops resumably after 3 consecutive `solve_failed`). |
| `search/campaign.py`, `hygiene.py` | Multi-family campaigns and leaderboards; Julia/worker-host cleanup. Ctrl-C: child gets a grace period, partial leaderboard marked INTERRUPTED, exit 130; hosts cleared after every job. |
| `search/gpulock.py` | Process-wide GPU lock (`runs/.gpu.lock`); `gpu-clean` CLI refuses while a live job holds it. |
| `gui/` (`server.py`, `data.py`, `jobs.py`, `static/`) | Local web GUI (`hornlab-search gui`, 127.0.0.1): read-only views of runs/campaigns/briefs, allow-listed CLI launcher; stdlib server + vanilla JS, no build step. |
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
| `examples/typologies/*.yaml` | Generator configs (classical + hybrids). |
| `examples/*.yaml` | Native-family configs (OSSE, R-OSSE, ICW, FREEFORM) and legacy smoke/adapter configs. |
| `tools/review/` | Builds the self-contained review page (`build_review_data.py`, `review_template.html`, `assemble.py`). |
| `tools/rescore/rescore_v2.py` | WP1 offline re-score: v1 vs v2 J over every stored response (report `docs/evidence/OBJECTIVE_V2_RESCORE.md`; the per-record CSV stays local, regenerate with the tool). |
| `tools/overnight/` | Unattended GPU queue (`queue_20261022.ps1`) and stall watchdog (`watchdog.ps1`, keeps Windows awake). |
| `tests/` | Offline suite; `requires_*` / `gpu` / `slow` markers in `tests/conftest.py`. |

## External code we depend on (pinned in `pyproject.toml` / `TOOLCHAIN.md`; changed only via our forks, `FORKS.md`)
`hornlab_mesher` (geometry + gmsh), `hornlab_beat_bem` (GPU/CPU BEM, Julia), `hornlab_bempp_bem` (CPU cross-check),
`hornlab_plots` — Magnus's (GitHub `m3gnus`) packages, installed in `.venv`.
