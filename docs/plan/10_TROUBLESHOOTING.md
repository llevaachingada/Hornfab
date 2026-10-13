# 10 TROUBLESHOOTING

Look up the symptom. **Before anything else:** take the `DEBUG`-logged mesher config dict or `SolveConfig` repr and run it by hand in a REPL. Roughly half of what looks like a pipeline bug is a key, a path, or a unit, and running it by hand tells you which in ten seconds.

---

## Install and toolchain

| Symptom | Cause | Fix |
|---|---|---|
| `hornlab_beat_bem.provision` runs for 40 minutes | Normal. Downloading and precompiling the Julia environment; CUDA's first run pulls several GB. | Wait. Do not interrupt, do not run twice concurrently. |
| `nvidia-smi` works but Julia sees no CUDA device | Driver too old for the `CUDA.jl` artifact, or a hybrid-graphics laptop parking the discrete GPU | Update the NVIDIA **driver** only. Force the discrete GPU for `julia.exe` in the NVIDIA control panel. Do not install a CUDA Toolkit. |
| `pip install` of a HornLab package fails on git | Network, or the SHA does not exist | None are on PyPI. Check the SHA against the repo. |
| Installed SHA does not match `pyproject.toml` | Someone reinstalled without pinning | `doctor` warns with both values. Reinstall at the pinned SHA, or deliberately bump the pin and **mark the dataset**: rows from two solver commits have inconsistent labels. |
| `hornlab_bempp_bem` will not install | No OpenCL runtime | Install the Intel CPU OpenCL runtime on Windows; it works on AMD parts too. Or accept the Numba fallback. Two attempts, then record it as unavailable and move on. |
| Julia found but wrong version | `juliaup` default not set, or another Julia earlier on PATH | `juliaup default 1.12`, or set `HORNLAB_BEAT_JULIA` to the absolute path. |
| Worked yesterday, not today | A dependency moved | `pip freeze | grep hornlab` and compare with `TOOLCHAIN.md`. The SHAs are pinned for exactly this. |

---

## Geometry and meshing

| Symptom | Cause | Fix |
|---|---|---|
| **Everything solves cleanly but the polars are smooth nonsense** | **The mesh is in the wrong units.** The mesher writes metres; the beat README's example uses millimetres. | `mesh/build.py`'s bounding-box guard should have caught this. Confirm `scale_to_metres: True` is written explicitly and `mesh_scale=1.0` in `SolveConfig`. This is the first thing to check for any inexplicable result. |
| Mesher raises `ConfigError` on a key you expect to work | The key is family-specific, or is on the refused list | Read `docs/config-schema.md` in the installed package. R-OSSE rejects `rot_deg` and explicit `L_mm`; ICW rejects OSSE shape keys, `zmap` and `z_map_points`. |
| `ConfigError: per-azimuth throat stretch is not supported yet` | Exactly what it says | Not a bug. That capability is the geometry novelty opening; see `design/custom.py` and `04_TASK_DESIGN_MESH.md` forks. Pass a plain finite number instead. |
| Triangle count far above expectation | `throat_res_mm` set too fine, or `quadrants` not applied | Remember `throat_res_mm` defaults to half `mouth_res_mm` in our sizing. Check the mesh actually came out reduced. |
| `max_triangles` refused despite being set high | A second hard check | Task 02's M7 answers this. Either raise it further, or set `allow_large_mesh: True` deliberately and record that the mesher's guard is off. |
| Quarter mesh is not roughly a quarter of the full | `quadrants` is not doing what we assume | CP-2a. Stop and re-read task 02's M6 before trusting any dof budget. |
| Triangle count scales linearly with `f_max`, not quadratically | The resolution keys are not controlling element size the way we assume | Every dof budget in the project is then wrong. Senior problem. |
| `MeshTooLargeError` on most candidates | `L_mm` or `R_mm` upper bound too large for the mode's `f_max` | Tighten the bound, or lower `band_hi_hz` for screening. A search where most candidates die explored nothing. |
| Mesh generation is not deterministic | gmsh seeding | Breaks the cache, the resume and the dataset. Measure the magnitude and report it; this is a senior problem. |

---

## Solver

| Symptom | Cause | Fix |
|---|---|---|
| First solve takes 15 s, every solve takes 15 s | **The worker is not warm.** | `solve/worker.py`. `warm()` once per run, `detach_workers()` not `shutdown_workers()` between runs. At 4 s per candidate this quadruples every search. |
| VRAM stays occupied after a failed or cancelled solve | An orphaned Julia worker | Kill the process **group**, not the child. `install_handlers()` must detach on SIGINT. Check for leftover `julia` processes before the next run; an orphan poisons every later solve with an OOM that looks like a mesh problem. |
| `CUDA out of memory` | The dof cap is wrong for this mesh | Operator memory is `8 * N_dof^2` bytes. Lower the cap, measure the real peak, update `TOOLCHAIN.md`. Then check for orphans. |
| Solve raises on an incomplete sweep | Documented behavior: beat-bem raises rather than returning partial data | Treat as a solve failure, penalize, continue. There is no partial path to handle. |
| Results differ run to run | GPU reductions are not associative | Measure it. At 1e-6 dB ignore it. At 1e-2 dB the search cannot see real differences; raise `tolfun` or change backend, and tell the senior agent. |
| CUDA slower than CPU | Unexpected: the solver is Float32 throughout, so the fp64 penalty does not apply | Re-time at a larger dof count. Check the GPU is not power-limited at 35 W TGP. Check it is the discrete GPU and not an iGPU. |
| GMRES not converging, falling back to LU | Hard geometry, or a tolerance mismatch | The documented budget is one LU's worth of matvecs before fallback (`BLAB_BEAT_GMRES_BUDGET`). Falling back is correct behavior, just slower. If it happens on most candidates, something about the geometry family is ill-conditioned and that is worth knowing. |
| Two solvers disagree by more than 1 dB | A real disagreement | Run the analytic sphere through **both**. Whichever matches physics is right. Do not pick by preference. |
| Polars look mirrored | Arc built descending, or probe order reversed | CP-3a and CP-7d. Nothing downstream can catch this: a mirrored polar is completely plausible. |
| Solve result is fine but DI is wrong | `di_source == "cuts_estimate"` | Expected if the balloon is unavailable. The report must say so, and no checkpoint may pass on it. |

---

## Metrics

| Symptom | Cause | Fix |
|---|---|---|
| Beamwidth exactly half what it should be | Per-side instead of total included angle | CP-4a. The cardioid must read 180.0. |
| Beamwidth always 180.0 | The pattern never drops 6 dB in range, or the reference level is wrong | If every arc sample has the same level, the arc is degenerate: check the frame and that the observation actually swept. |
| DI about 3 dB high everywhere | Hemisphere instead of full sphere | CP-4a. Dipole and cardioid must both read 4.771. |
| DI and beamwidth disagree by more than 3 dB | One is on the wrong probe set | They come from different probes, which is why the check is valuable. Confirm the balloon array is the balloon. |
| DI is a strange constant | Averaging dB instead of linear power | Convert to linear power before averaging. The most common error in directivity code. |
| `nan` in the objective | `log10(0)`, or an empty slice in a mean | `normalized_db` floors at -120; every aggregate is `nanmean`. Find the frequency and look at that solve. |
| Ripple suspiciously low | The -40 dB floor is excluding most of the coverage region | Check the surviving sample count. Fewer than 5 must return `nan`. |
| `scalars` missing a key | A code path that skips a metric | Test 35 in task 06 asserts set equality for a reason: the report and the dataset both index by key. |

---

## Search

| Symptom | Cause | Fix |
|---|---|---|
| Objective never improves | Bounds too tight, the seed already good in this parameterization, or `sigma0` too small | Read the bounds-pinning table. Then check the noise floor: if the available improvement is below it, the search cannot see it. |
| Every candidate hits a bound | Bounds are the binding constraint, not the physics | Widen them and re-run. **A pinned parameter is a finding, not an answer.** |
| Half the candidates fail | Bounds admit invalid geometry, or the dof cap is too low | Read the failure table by reason and fix whichever dominates. |
| Resume re-solves everything | Hash not stable across processes | Must be `hashlib`, never Python's salted `hash()`. Task 03 test 4. |
| Two runs with the same seed diverge | Something unseeded, usually the mesher | Task 04 test 20. |
| CMA-ES stalls immediately | `inf` or `nan` returned from `evaluate` | Penalties must be large and **finite**. `inf` poisons the covariance update permanently. |
| Search finds a 0.05 dB improvement | Below the noise floor | Not a result. CP-7f. |
| Best design is physically absurd but scores well | The objective is missing a constraint the designer holds in their head | The objective is working correctly and telling you something. Add the missing term, usually size, depth or throat loading. **Write down what it was**: an objective that needed a new term is the most informative output a search produces. |
| A search that ran for hours produced no dataset records | The dataset append was skipped on a code path | Task 08 test 18 asserts one record per evaluation. Those GPU-hours are not recoverable. |

---

## Dataset

| Symptom | Cause | Fix |
|---|---|---|
| `json.dumps` raises mid-search | A numpy scalar leaked into the metadata | `validate_record` checks for this. Convert at the boundary with `float()`, `int()`, `.tolist()`. |
| `index.jsonl` last line is truncated | A hard kill | Expected and handled. The store must read every complete line and report the partial one. Task 07 test 10. |
| Records from two solver SHAs mixed | A dependency moved mid-project | Filter by `lib_sha` at export. This is why the field exists on every record. |
| Export returns far fewer rows than the store holds | Frequency-grid mismatch filtering | Check `meta['skipped_grid_mismatch']`. Screen-grid and verify-grid rows are not the same label space. |
| `dataset/` is huge | Balloon arrays at 1024 points across many frequencies | Check the per-record disk from CP-5. Consider a smaller screening balloon, or storing surface traces for a sampled subset only. |

---

## Reports

| Symptom | Cause | Fix |
|---|---|---|
| HTML is 60 MB | dpi too high, or too many designs rendered | `hornlab_plots` returns base64 PNGs; lower the dpi and the top-N count. |
| Blank sections for some designs | Missing `response.npz` from a failed evaluation | Render what exists and mark the gaps. A missing design must never break the whole report. |
| Figures do not show in a browser | File paths instead of base64 data URIs | One self-contained file, no sidecar directory. |

---

## When to stop and escalate

| Trigger | Why it is a senior problem |
|---|---|
| CP-7a check 3 fails (spherical spreading) | A frame or units error invalidates every number produced so far. |
| Mesh bounding box in the wrong units anywhere | Same. Everything prior is suspect. |
| CP-7d asymmetry over 1 dB | A real bug, and no downstream test will catch what it is doing. |
| Full-versus-quarter solves disagree (task 02 M6) | The symmetry mapping is wrong and every reduced-domain result is wrong. |
| Two solvers disagree by more than 1 dB | One of them is wrong about physics, and we need to know which. |
| Solver idempotence worse than 1e-2 dB | The objective has no usable signal; the strategy needs rethinking. |
| Non-deterministic meshing | Breaks cache, resume and dataset simultaneously. |
| Anything that makes modifying an installed HornLab or Julia file look like the fix | It never is, and it unpins the dependency. |
| Two agents needing the same file | A file-ownership problem, which is the orchestrator's. |
| **A result that seems too good** | **Especially this one.** |

That last row deserves its emphasis. The failure mode of this kind of tool is not a crash, it is a beautiful plot of something that cannot happen. A horn holding 75 by 45 degrees flat from 300 Hz to 16 kHz with 0.2 dB of ripple does not exist, and every gate in `09_CHECKPOINTS.md` exists to catch exactly that. The human's instinct that a result looks too clean is a legitimate reason to stop and re-verify.
