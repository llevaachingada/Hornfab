# 08 TASK PIPELINE

**Wave 2. One agent. Starts only after CP-2, CP-3, CP-4 and CP-5 all pass.**

Owner of: `hornlab_search/objective/terms.py`, `scalar.py`, `search/evaluate.py`, `cma.py`, `nsga.py`, `selftest.py`, `report/html.py`, `cli.py` (transferred from task 03), `tests/test_objective_*.py`, `test_search_*.py`, `test_report_*.py`, `test_end_to_end.py`
Reads: `01_CONTRACTS.md`, `TOOLCHAIN.md`, and all four Wave 1 reports
Imports: everything in `hornlab_search`, plus `cma`, `jinja2`, `hornlab_plots`

You connect four finished modules, add the search loop, the self-test and the report.

**Before you write a line**, read the four Wave 1 reports and extract three numbers:

| Number | From | What it decides |
|---|---|---|
| Solver idempotence disagreement | task 05, test 13 | whether the objective has usable signal |
| Mesh symmetry asymmetry | task 05, test 12 | the project's noise floor |
| Measured seconds per screening candidate | task 02, M3 | the search budget that fits in a sitting |

**Set CMA-ES `tolfun` above the noise floor, not below it.** A search converging below its own noise floor spends hours refining an artifact and reports it as a result.

---

## Build

### 1. `objective/terms.py` and `scalar.py`

```python
PENALTY_INVALID  = 1.0e3
PENALTY_FAILED   = 1.0e3

TERM_KEYS = ("cov", "rip", "di", "dislope", "flat", "load", "penalty", "total")


def objective(metrics: MetricSet | None, ok: bool,
              target: Target, weights: dict) -> tuple[float, dict]:
    """Returns (J, terms). LOWER IS BETTER. NEVER raises.
    terms always has exactly TERM_KEYS, with 0.0 for skipped terms, plus
    'n_nan' and 'n_in_band'."""
```

The formula is `01_CONTRACTS.md` section 11. Requirements:

- Only frequencies inside `[target.band_lo_hz, target.band_hi_hz]` count. The solve grid deliberately extends past the band so the report can show what happens outside it without letting it drive the search.
- Every mean is `np.nanmean`; the nan count goes in `terms`.
- `metrics is None` or `ok is False` returns `PENALTY_FAILED` with a full `terms` dict. **Never `inf`**: a single `inf` permanently poisons the CMA-ES covariance update.
- If `metrics.di_source == "cuts_estimate"`, still compute the DI terms, but set `terms["di_estimated"] = 1.0` so the report can flag it.

**Print all terms for the seed design and paste them.** The `/100` and `/10` divisors exist so the terms land in comparable ranges and the YAML weights mean what a reader expects. If one term is a hundred times the others, adjust the divisor and say so in your report. A weight the user cannot reason about is worse than no weight.

### 2. `search/selftest.py`

This is the only module in the project that compares our numbers to physics instead of to our own code.

**A scoped exception to hard rule 2.** This file contains a tiny icosphere generator and a minimal gmsh ASCII writer. That is allowed here and **only** here, because the analytic benchmark is a sphere and `hornlab_mesher` builds waveguides, not spheres. It is a test fixture, not design geometry. Nothing outside `selftest.py` may contain mesh-writing code.

```python
def icosphere(radius_m: float, subdivisions: int) -> tuple[np.ndarray, np.ndarray]:
    """Subdivided icosahedron. Exactly 20 * 4**subdivisions triangles.
    Deduplicate edge midpoints with an edge->index dict or the mesh will not
    be watertight. Project every vertex to the sphere at the end.
      sub=3 ->  1,280 tris   sub=4 ->  5,120   sub=5 -> 20,480
    """

def write_sphere_msh(points, tris, path: Path) -> None:
    """gmsh 2.2 ASCII, METRES, every triangle tagged with the PRIMARY_SOURCE
    tag from hornlab_mesher.tags (2, 'SD1D1001'), so the whole surface is the
    driven port. Node indices in $Elements are 1-BASED."""

def analytic_magnitude(a_m, r_m, ka) -> np.ndarray:
    """|p| = rho*c*U0 * (ka / sqrt(1 + ka^2)) * (a/r), with U0 = 1."""

def run_analytic(cfg, tol_db=0.5, subdivisions=3) -> dict: ...
def run_crosscheck(cfg, n_freqs=5) -> dict: ...
```

#### The analytic test, and why it asserts what it does

Sphere radius 0.1 m, `ka` of 0.5, 1, 2, 4, 8, which at `c = 343` is **273, 546, 1092, 2183 and 4367 Hz**. Observe on axis at 2 m and at 4 m.

**Assert on the shape of the frequency dependence, not the absolute level.** We do not know how the solver normalizes a port drive and we should not have to. Form

```
R(ka) = |p_solved(ka)| / ( ka / sqrt(1 + ka^2) )
```

and assert `20*log10(R)` is **constant across all five `ka` to within `tol_db`**. Any unknown constant drive scaling cancels; what survives is exactly the physics, the radiation-impedance roll-off of a pulsating sphere. Report the absolute level too, as information about the port normalization.

Separate assertions:

| Check | Pass |
|---|---|
| Spherical spreading: 2 m versus 4 m | **6.02 dB**, +/- 0.05 |
| Omnidirectionality: std dev of `|p|` over the balloon | under **0.1 dB** at every `ka` |
| Mesh convergence at subdivisions 3, 4, 5 | error **monotonically decreasing** |

The omnidirectionality check is worth its weight alone. A pulsating sphere is the only geometry whose exact answer a person can check by eye: the pattern must be perfectly round at every frequency. If it is not, something is wrong with the mesh, the normals, the probe geometry or the symmetry handling, and it is far better to find that on a sphere than on a horn.

**Known risk, bounded.** The whole surface must be driven with uniform normal velocity. Whether the solver's port model does that on a closed surface is **[open]**. If it cannot, the failure is recognizable: omnidirectionality fails badly while spreading passes. Record it, cap the attempt at two tries, and fall back to the cross-check and the convergence tests in `09_CHECKPOINTS.md`, which do not depend on the port model.

#### The cross-check, which may be stronger than the analytic test

```
hornlab-search selftest --crosscheck
```

Solve **the same mesh** at 5 frequencies with `beat_cuda` and with `bempp_cpu`, and report the per-frequency maximum difference in normalized dB across the horizontal cut.

Two independently implemented solvers, in different languages, written by different people, on the same mesh. Agreement within a few tenths of a dB is strong evidence both are right. **Do not tune anything to make them agree.** Disagreement is a finding for the senior agent, with numbers.

### 3. `search/evaluate.py`

```python
def evaluate(design, space, cfg, mode, run_dir, store, backend) -> Evaluation:
    """One candidate, end to end. NEVER raises.

      1. mspec = mesh_spec(mode, cfg); sspec = solve_spec(mode, cfg)
      2. cache lookup on (design, mspec, sspec); hit -> cached Evaluation,
         no GPU touched, no budget consumed
      3. build_mesh  -> GeometryInvalidError / MeshTooLargeError -> invalid
      4. backend.solve(mesh, sspec)  (worker already warm)
      5. compute_metrics if ok
      6. objective -> (J, terms)
      7. cache store if ok
      7b. if this candidate falls in the trace sample (default 1 in 20, by
          a DETERMINISTIC rule such as int(design_hash, 16) % 20 == 0, never
          random, so a resumed run samples the same designs), re-solve is NOT
          needed: pass capture_traces=True on the original solve and store
          them with store.append_traces
      8. dataset store.append  -- ALWAYS, including failures
      9. append to run_dir/search.ndjson, FLUSH AND FSYNC
     10. log one INFO line: hash, J, mesh s, solve s, dofs, cached

    Any unexpected exception is caught here, logged with its traceback into
    the Evaluation and the dataset record, and returned as penalized.
    """
```

Step 8 is not optional and it comes **before** the ndjson append, so a crash between them loses a log line rather than a training record.

### 4. `search/cma.py`

```python
def search(cfg, run_dir, mode="screen", resume=None) -> Evaluation:
```

```python
space = DesignSpace.from_config(cfg)
x0 = space.normalize(space.seed)
opts = {"bounds": [0.0, 1.0], "seed": cfg.search.seed,
        "maxfevals": cfg.search.budget,
        "tolfun": cfg.search.tolfun,          # ABOVE the noise floor
        "verb_filenameprefix": str(run_dir / "cma" / "")}
es = cma.CMAEvolutionStrategy(list(x0), cfg.search.sigma0, opts)
```

Six requirements:

1. **Evaluate the seed first**, before the loop, and log it. Every later number is meaningless without the baseline it has to beat.
2. **`backend.warm()` once**, before the seed. Never per candidate. A 12 s cold start against a 4 s solve quadruples the cost of the run.
3. **`write_best` after every improvement**, not at the end. A four-hour run that dies at hour three must still leave the best design on disk.
4. **`search.ndjson` appended, flushed and fsynced per evaluation.** Open in append mode per write rather than holding a handle for hours.
5. **Resume is free.** On startup, if `search.ndjson` exists, load it into the cache and continue. A re-run of the same config performs zero solves for work already done. Test it.
6. **`--budget` caps non-cached evaluations only.** A cache hit does not consume budget.

At the end, log and write into `run.json`:

```
evaluations, cache hits, failures by reason, total GPU seconds,
mean seconds per candidate, candidates per hour,
projected hours for 1,000 and for 10,000 evaluations
```

That last line is the honest answer to "how fast is this", and it is the number that tells the user when the surrogate in `11_PHASE2_SURROGATE.md` becomes worth building.

### 5. `search/nsga.py`

**A stub in phase 1**, with the interface defined and a `NotImplementedError`:

```python
"""Multi-objective search. Phase 2.

NSGA-II needs roughly 100 individuals x 100 generations = 10,000 evaluations.
At the measured seconds per candidate (see run.json), that is impractical
against real BEM. It becomes the right algorithm the moment a surrogate can
evaluate a population in one batched forward pass. See 11_PHASE2_SURROGATE.md.
"""

def search_pareto(cfg, run_dir, evaluator) -> list[Evaluation]:
    raise NotImplementedError("phase 2")
```

Note the `evaluator` argument: it is what lets phase 2 swap a surrogate in without touching the search code.

### 6. `report/html.py`

One self-contained HTML file. Use `hornlab_plots` for the figures; it returns base64 PNG strings directly, which is exactly what we want to embed. Jinja2 for the template. **Do not import matplotlib yourself.**

Useful `hornlab_plots` entry points: `directivity_heatmap_b64()`, `frequency_response_b64()`, `frequency_response_multi_b64()`, `directivity_index_b64()`, `impedance_b64()`, `save_beamwidth_plot()`, `sphere_power_metrics()`, and `set_theme()`.

Contents, in this order:

1. **Header.** Run id, config, mode, date, machine and backend from `TOOLCHAIN.md`, all four library SHAs, evaluations, cache hits, total GPU time.
2. **The noise floor, at the top, in a box.** The largest of solver idempotence, mesh asymmetry and discretization error, with the sentence: *no claimed improvement smaller than this number means anything.*
3. **Feasibility.** `targets.feasibility_report()`: the mouth dimension each axis needs to hold the target coverage down to `band_lo_hz`, next to the actual mouth dimensions. If the target is impossible at this size, say so here in plain words.
4. **Convergence plot.** Objective versus evaluation, seed as a horizontal line, running best as a step curve.
5. **The honest summary line.** Best, seed, improvement as a percentage. **If the best did not beat the seed, say so in plain words at the top.** Burying that is the one thing that would make this tool untrustworthy.
6. **Term breakdown.** Stacked bars for the seed and the top N.
7. **Per design** (seed and top N): the parameter table with each value shown as a fraction of its bound range; H and V polar overlays; beamwidth versus frequency with the target band; DI versus frequency with the target line and the DI slope; the directivity heatmap; `f_break` and `f11` marked as vertical lines on the frequency plots.
8. **Bounds report.** For each searchable key, how often the top designs sat within 2% of a bound. **A pinned parameter means the bound is wrong, not that the answer is optimal.** This is the most actionable table in the report.
9. **Failure table.** Every invalid or failed evaluation grouped by reason, with counts. If 60% failed, the user paid for a search that explored 40% of what they thought.
10. **DI provenance.** Whether DI came from the balloon or the cuts estimate, for every design shown.
11. **Dataset line.** Records written this run, cumulative records, disk used, trace fraction, and the family balance. If one family is over 80% of the store, print the warning: a dataset that is all one geometry family cannot answer whether a surrogate generalizes.
12. **Reproduction block.** The exact command, config SHA, library SHAs, CMA seed.

Keep it under about 10 MB. `hornlab_plots` returns PNGs; do not raise the dpi chasing crispness.

### 7. `cli.py`

Keep `doctor` and `version`. Add:

```
hornlab-search selftest --analytic [--tol-db 0.5] [--subdivisions 3]
hornlab-search selftest --crosscheck
hornlab-search run      --config <yaml> [--mode screen|verify|final] [--dry-run]
hornlab-search search   --config <yaml> [--budget N] [--mode screen] [--resume DIR]
hornlab-search verify   --run <dir> [--top 5]
hornlab-search report   <run_dir> [--out report.html] [--top 5]
hornlab-search dataset  stats|verify|export
```

| Flag | Behavior |
|---|---|
| `--dry-run` | Build meshes, report element and dof counts and the estimated wall time, **launch no solver.** Makes the whole CLI testable with no GPU and lets a user sanity-check a config before committing four hours. |
| `--backend` | Overrides the config. Needed for CPU-versus-CUDA comparison. |
| `-v` / `-vv` | `INFO` / `DEBUG` |

Call `worker.install_handlers()` once at startup. Every command exits 0 or 1 and prints one clear final line saying what happened and where the output is.

---

## Tests

`tests/test_objective_*.py`

1. All of `TERM_KEYS` present for a complete `MetricSet`, and the weighted terms sum to `total`.
2. A perfect design scores exactly `0.0` to 1e-12.
3. `metrics=None` gives exactly `PENALTY_FAILED` and does not raise.
4. A `nan` ripple at one frequency gives a finite `J` and `n_nan == 1`.
5. Out-of-band frequencies do not affect `J`: append a terrible out-of-band frequency and assert `J` is unchanged.
6. 2 dB of ripple scores strictly worse than 1 dB, all else equal.
7. `di_source == 'cuts_estimate'` sets `terms['di_estimated'] == 1.0`.

`tests/test_search_selftest.py` (offline parts)

8. `icosphere(0.1, n)` has exactly `20*4**n` triangles for `n` in 0 to 4, is watertight (every undirected edge appears exactly twice), has positive signed volume, and at `n=4` its volume is within 2% of `4/3*pi*r^3`.
9. Every icosphere vertex is at `radius` to 1e-12.
10. `write_sphere_msh` round-trips through `mesh.build.read_msh_summary` with the right triangle count, a bounding box near +/-0.1 m, and every triangle carrying tag 2.
11. `analytic_magnitude` goes to `rho*c*U0*a/r` within 1% at `ka = 100`, and to `rho*c*U0*ka*a/r` within 1% at `ka = 0.01`, and is monotone increasing in `ka`.

`tests/test_search_cma.py` (mocked evaluator, no GPU)

12. Monkeypatch `evaluate` with a deterministic analytic function and assert CMA-ES reduces the objective over 60 evaluations.
13. Same seed twice gives the identical sequence of sampled designs. **Reproducibility is a contract.**
14. A budget of 25 produces exactly 25 non-cached evaluations.
15. Resume: run 20, kill, resume, assert zero solves for the first 20 and a final best matching an uninterrupted 40-evaluation run.
16. One candidate raising an arbitrary exception does not stop the loop, and its traceback lands in both `search.ndjson` and the dataset record.
17. After a simulated hard kill, every line of `search.ndjson` parses and the last line is complete.
18. Every evaluation, including failures, produced exactly one dataset record. Assert `len(store)` equals the evaluation count.
18b. Trace sampling is **deterministic**: the same config run twice samples the same design hashes for trace capture, and the sampled fraction is within 30% of the configured rate over 200 synthetic evaluations. A random sampler would make a resumed run capture a different subset, which quietly biases the dataset.

`tests/test_report_*.py`

19. `build_report` on a synthetic run produces non-empty HTML containing the run id and at least 6 base64 PNG URIs.
20. It renders when the best is **worse** than the seed, and contains the plain-language statement that it did not improve.
21. It renders from a run with zero successful evaluations without raising.
22. Size on a 200-evaluation synthetic run is under 10 MB.
23. The noise-floor box and the feasibility section are present and contain numbers.

`tests/test_end_to_end.py` (`@requires_beat @pytest.mark.slow`)

24. `hornlab-search run --config examples/osse_baseline.yaml --mode screen` exits 0 and writes `response.npz`, `metrics.json`, `status.json`, and one dataset record.
25. `hornlab-search search --config examples/search_smoke.yaml --budget 8` exits 0, writes 8 ndjson rows, 8 dataset records, and `best.json`.
26. `hornlab-search report <run>` exits 0.
27. `hornlab-search run --dry-run` exits 0 with **no solver call**, asserted by monkeypatching `backend.solve` to raise.
28. `hornlab-search dataset stats` exits 0 and reports the right count.

---

## Checkpoint CP-6

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
.\.venv\Scripts\hornlab-search.exe doctor
.\.venv\Scripts\hornlab-search.exe selftest --analytic --tol-db 0.5
.\.venv\Scripts\hornlab-search.exe selftest --crosscheck
.\.venv\Scripts\hornlab-search.exe run --config examples\osse_baseline.yaml --mode screen -v
.\.venv\Scripts\hornlab-search.exe search --config examples\search_smoke.yaml --budget 60 -v
.\.venv\Scripts\hornlab-search.exe report runs\<latest> --out report.html
.\.venv\Scripts\hornlab-search.exe dataset stats
```

Paste all of it, plus six tables.

**Table 1, the analytic self-test**

| ka | f (Hz) | analytic (dB rel) | solved (dB rel) | R(ka) deviation (dB) |
|---|---|---|---|---|
| 0.5 | 273 | | | |
| 1 | 546 | | | |
| 2 | 1092 | | | |
| 4 | 2183 | | | |
| 8 | 4367 | | | |

Plus omnidirectionality std dev per `ka`, the 2 m versus 4 m spreading check, and the three-level convergence errors.

**Table 2, the cross-check**: per-frequency max difference between `beat_cuda` and `bempp_cpu` in normalized dB, or an explicit note that bempp is unavailable.

**Table 3, objective terms at the seed**, raw and weighted, all six.

**Table 4, measured throughput**: dofs, mesh seconds, solve seconds, total per candidate, peak VRAM, candidates per hour, projected hours for 1,000 and 10,000 evaluations.

**Table 5, the 60-evaluation search**: seed objective, best objective, improvement, the evaluation where the best appeared, failures by reason, and the bounds-pinning table.

**Table 6, seed versus best parameters**, each as a fraction of its bound range.

**CP-6 passes when:** every test passes, `selftest --analytic` passes at 0.5 dB or the documented port-model reason is given, the cross-check is reported, the 60-evaluation search completes, and the report opens in a browser with the noise floor at the top.

**CP-6 does not require the search to have found a better horn.** It requires the machinery to work and the numbers to be honest.

---

## Forks

| Fork | Difficulty | Value | Notes |
|---|---|---|---|
| **Multi-fidelity promotion** | low | **high, do it next** | Have `search` promote the top 10% to a `verify` solve and rank on that. Cheap, directly improves answer quality, and it generates both screen and verify labels for the same designs, which is exactly what a multi-fidelity surrogate wants later. |
| **Rayleigh pre-screen as a `Backend`** | medium | **highest throughput win** | Roughly 100x cheaper per candidate. Slots into the existing protocol and cache with no changes elsewhere. |
| NSGA-II on real BEM | low to write | **low now** | The stub exists. At the measured cost per candidate it is unaffordable. Build it when the surrogate lands, which is the point. |
| Warm-start the search from an ATH import | low | medium | The mesher imports ATH text. Seeding from a published design makes "did we beat the state of the art" a direct comparison instead of an argument. |
| Seed from several known-good designs | low | medium | CMA-ES takes one `x0`; run several short searches from different seeds and compare, or use a restart strategy. |
| Sensitivity analysis from the dataset | low | **high and underrated** | With a few hundred records, a simple variance-based sensitivity analysis says which parameters actually matter. That tells you which bounds to widen, which to pin, and where the physics really lives. Nearly free once the dataset exists. |
