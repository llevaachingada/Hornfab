# NOTES FOR SENIOR

**Append only.** Every agent may add to this file; nobody edits or deletes an existing block.
Use this for contract gaps, files you need but do not own, installed-package bugs, and anything
you were blocked on twice (hard rules 1, 3, 5 and 8 in `docs/plan/00_ORCHESTRATOR.md`).

Format for each block:

```
## YYYY-MM-DD  <task id>  <one-line subject>
What I was doing:
What happened (exact error / output):
What I tried:
What I need decided:
```

---

## 2026-10-12  task-02  machine deviation: GPU is RTX 4060 Laptop, not RTX 4070
What I was doing: recording the CP-0 target machine.
What happened: the plan names an RTX 4070 Laptop 8 GB; the machine reports an RTX 4060 Laptop with 8 GB and driver CUDA 13.3.
What I tried: proceeded anyway. VRAM is the same (8 GB), so the dof caps are unchanged; expect slower seconds/candidate.
What I need decided: nothing — recorded as an approved deviation; reflected in TOOLCHAIN.md.

## 2026-10-12  task-03  no YAML key for frequency-grid edges
What I was doing: implementing config.freq_grid / mode_freqs.
What happened: 01_CONTRACTS §8 fixes a log grid per mode but there is no YAML key for the grid edges.
What I tried: used the §8 table (screen 500-10000/12, verify 300-16000/25, final 250-20000/36), with the top edge clipped to target.band_hi_hz so the mesh is never asked to resolve frequencies the objective ignores.
What I need decided: whether a future YAML key should expose the grid edges.

## 2026-10-12  task-03  CP-1 test 3 deviation (angle step)
What I was doing: tests/test_config.py test 3.
What happened: the plan's literal wording "(angle_count - 1) divides 180 evenly" fails for the contracted default 73 (180/72 = 2.5).
What I tried: the test instead asserts 18000 % (n-1) == 0, i.e. the step 180/(n-1) is a whole number of hundredths of a degree (73 -> 2.50 deg) and the -90..+90 grid hits 0 exactly.
What I need decided: confirm the intent is a clean angular step, not literal divisibility of 180.

## 2026-10-12  task-06  cardioid threshold is -6.0206 dB, not -6.0
What I was doing: writing the fake_response cardioid fixture and its assertions.
What happened: (1+cos theta)/2 at +/-90 deg is exactly -6.0206 dB, so a strict -6.0 dB threshold reads about 179.7 deg instead of the contract's 180.0.
What I tried: the fixture asserts the -6 dB total included beamwidth is 180.0 using the exact 20*log10(0.5) value.
What I need decided: task 06 metrics must use the exact cardioid value; flagged for the task 06 issue.

## 2026-10-12  task-03  ICW termination is categorical; coverage_angle convention unconfirmed
What I was doing: writing examples/icw_termination.yaml from the mesher schema.
What happened: the mesher `termination` key is categorical (default flat_baffle) and cannot take a lo/hi bound, so it lives in seed_params only. The `coverage_angle`/`coverage_angle_deg` half-vs-total convention is not confirmed by the schema.
What I tried: kept termination in seed_params; flagged the coverage convention.
What I need decided: confirm coverage_angle is a half-angle or a total included angle.

## 2026-10-12  task-02  solver API drift: SolveResult, not Response
What I was doing: CP-0 step 6 first solve and schema dump.
What happened: plan 02 predicts a `Response` with `p1_dof_count`, `native_diagnostics`, `metal_pipeline`. The installed hornlab-beat-bem 0.2.0 returns a `SolveResult` with `mesh_info.n_vertices` / `n_triangles` (no p1_dof_count / native_diagnostics).
What I tried: confirmed n_vertices IS the P1 dof count; recorded the real schema in TOOLCHAIN.md.
What I need decided: task 05 adapts to SolveResult, not the plan's guessed Response.

## 2026-10-12  task-02  MB2/M6: dense 8N^2 storage OOMs at ~20k dofs on the 8 GB card
What I was doing: M2 VRAM vs dofs and M6 symmetry pairing.
What happened: a single-frequency solve at 20,193 dofs tried to allocate 3.038 GiB and raised "Out of GPU memory ... 100.00% (7.996 GiB/7.996 GiB)". 8 * 20193^2 bytes = 3.04 GiB, confirming dense complex64 8N^2 storage. At the default mouth_res_mm=26 the 8 kHz result is under-resolved: full-vs-quarter agree to <=0.26 dB at 1/2/4 kHz but diverge by up to 22.7 dB at 8 kHz (discretization, not a symmetry bug).
What I tried: measured dof/triangle = 0.50 (full) and ~0.51 (quarter, wall-boundary overhead at coarse res).
What I need decided: the plan's dof caps (verify 16000, final 24000) will OOM; caps must be lowered to the measured ceiling. UNRESOLVED: the exact max dof that fits.

## 2026-10-12  task-02  stale persistent Julia hosts corrupt VRAM measurements and cause crashes
What I was doing: M2 VRAM sweep, one fresh Python process per mesh.
What happened: runs after the first crashed with "Warm BEAT Engine solver exited with code 1 / 4294967295" or OOMed at sizes that fit alone (quarter 5.1k dofs failed in a sweep, then succeeded alone: 25.6 s, assembly 13.1 s). `Get-Process julia` showed several ~1 GB hosts left over from earlier processes, even though each script called `shutdown_workers()`. Earlier full-domain OOMs at 9.2k-20k dofs were measured in this contaminated state and must be re-measured clean.
What I tried: killed all julia.exe between jobs and re-ran (results in TOOLCHAIN.md).
What I need decided: (1) task 05 must make `solve/worker.py` release hosts reliably and test it by process list; contract 01 section 9 assumes shutdown works. (2) The "GPU / Julia hygiene" rules are now in AGENTS.md and CLAUDE.md. (3) Consider a `doctor` check that warns when more than one julia host is alive or VRAM baseline is above 1 GB.

## 2026-10-12  task-06  RESOLVED HERE, please confirm: "-6 dB" is implemented as HALF PRESSURE (-6.0206 dB), not -6.0000 dB
What I was doing: beamwidth_deg against contract tests 1 and 2 (cardioid reads 180.0, dipole reads 120.0, both to 0.05 deg).
What happened: the orchestrator addendum suggested an epsilon of 1e-3 dB around a strict -6.0 dB threshold. That cannot work: (1+cos t)/2 is 20*log10(0.5) = -6.0206 dB at +-90 deg, which is 0.0206 dB below -6.0, i.e. 20x outside a 1e-3 dB epsilon. A strict -6.0 reads the cardioid 179.73 and the dipole 119.83 (both fail the 0.05 tolerance).
What I did: polar._threshold_db maps the conventional labels to their exact amplitude ratios: drop_db=6.0 -> 20*log10(0.5) (half pressure), drop_db=3.0 -> 10*log10(0.5) (half power); any other value is taken literally. No tolerance was loosened, the result is continuous in the pattern (no snapping), and every contract case is exact on any grid. A near-threshold epsilon of ~0.025 dB with snapping was the alternative; I rejected it because it is discontinuous and grid dependent (the piston cases at a 2.5 deg grid would see up to 0.12 deg snap error).
What I need decided: confirm 01_CONTRACTS section 10 "-6 dB" means p = 0.5 (it must, for its own cardioid/dipole numbers). Every later beamwidth in the project inherits this.

## 2026-10-12  task-06  CONTRACT GAP: di_from_cuts formula contradicts tests 14 and 15
What I was doing: contract tests 14 (target_di_db(360, 180) == 0.0) and 15 (di_from_cuts(180, 180) on an omni pattern agrees with the balloon DI, 0 dB, to 0.3).
What happened: Omega = 4*arcsin(sin(bw_h/2)*sin(bw_v/2)) gives 3.01 dB for (180, 180) (a hemisphere) and ~0 solid angle (huge DI) for (360, 180) because sin(180 deg) = 0. Test 13 (75x45 -> 11.26 dB) is fine.
What I did, minimal and documented in di.py: sin(bw/2) is clamped at 1 for bw >= 180 ("no crossing" means "at least that wide"), and if BOTH cuts are >= 180 the pattern is treated as omnidirectional (Omega = 4*pi, DI = 0). Tests 13-16 all pass as written. Consequence to know: an omni source AND a cardioid both read bw = 180/180, so a cuts_estimate DI of 0 is meaningless for them; that is the existing reason di_source must be carried and no checkpoint may pass on cuts_estimate.
What I need decided: confirm the saturation rule, or give the intended formula for bw >= 180.

## 2026-10-12  task-06  ripple_db uses the SAMPLE std (ddof=1); contract says only "standard deviation"
What I was doing: contract test 19 (alternating +1/-1 dB inside coverage -> 1.0 to 1e-9).
What happened: the on-axis sample is inside the coverage set and is exactly 0 after normalization, so with n coverage samples the population std of any +1/-1 alternation is sqrt((n-1)/n) (0.9837 for 31 samples), never 1.0. The sample std (ddof=1) is exactly 1.0 when the other n-1 samples are balanced +-1.
What I did: ddof=1 in ripple_db (documented). band_flatness_db is the plain population std after removing the mean (ddof=0), as its docstring says. Difference between the two conventions is a factor sqrt(n/(n-1)) (about 1.6 % at n=31).
What I need decided: confirm ddof=1, or say whether the earlier tiling study's ripple used ddof=0 (then test 19 needs rewriting, not the code).

## 2026-10-12  task-06  smaller ambiguities, for the pipeline owner
- constants.py quotes f11 = 7914 Hz for "1.0 in" and 3957 Hz for "2.0 in" under a comment that says "radius a". Those numbers are for a throat DIAMETER of 1.0 / 2.0 in (radius 12.7 / 25.4 mm). compute_metrics takes throat_radius_m, so pass the radius; a 1.0 in exit radius (r0 = 25.4 mm) gives 3957 Hz. The comment in constants.py (task 03) should say diameter.
- coverage_from_room: the task file gives `height_m` but no use for it next to ear_height_m and source_height_m. It is the ceiling height and is only used to reject impossible heights. It also needed a band, which the signature lacks: added keyword-only band_lo_hz=700, band_hi_hz=13000 (mirrors examples/osse_baseline.yaml). Vertical coverage assumes the horn is tilted at the middle of the ear-height elevation range.
- compute_metrics: DI uses the balloon only when BOTH spl_balloon_db and balloon_dirs are present, and always with equal weights (equal-area grid). The real solver balloon is a theta-phi grid; metrics.di.sin_theta_weights() and di_from_balloon(..., weights=) exist and are tested, but nothing converts a solver theta-phi balloon to the contract's equal-area form. Task 05/08 must either resample to an equal-area point set or pass weights; compute_metrics does not auto-detect.
- DI quadrature: 512 Fibonacci points are ample for broad patterns (cardioid error 4e-6 dB) but NOT for narrow beams: an unbaffled piston at ka=24 (10.6 deg beamwidth) reads 24.82 dB at 512 points against 24.59 true (+0.23 dB), 24.595 at 4096.

## 2026-10-13  task-04  to_mesher_config is SECTIONED, not flat (task file sketch drops max_triangles)
What I was doing: implementing families.to_mesher_config from the 04 task sketch (flat dict: formula, mode, **params, quadrants, *_res_mm, max_triangles, ... at top level).
What happened: measured against hornlab-waveguide-mesher 0.2.4: a TOP-LEVEL `max_triangles` is silently ignored (default 18000 applies; a quarter mesh was then refused at "effective limit 4,500" although I passed 50000). Unknown profile keys are also silently ignored (`bogus_key` builds fine). Pinned by tests/test_mesh_build.py::test_mesher_defaults_are_not_trusted_flat_dict_drops_max_triangles.
What I tried: emit the mesher's own sectioned form (profile / cross_section / mesh / morph / gcurve + top-level formula, mode, output), routing each key by KeySpec.section. Tests 8 etc. read cfg["mesh"][...].
What I need decided: nothing; recorded so task 08 and anyone reading the DEBUG repr is not surprised.

## 2026-10-13  task-04  contract gap: config.mesh_spec and sizing.max_triangles_for disagree when dof_per_triangle != 0.5
What I was doing: mesh/sizing.py max_triangles_for (task file: ceil(dof_cap / dof_per_triangle * qf * slack)).
What happened: task 03's hornlab_search/config.py mesh_spec uses ceil(2 * cap * qf * slack) (01_CONTRACTS section 6 literal), which ignores dof_per_triangle. With the shipped 0.51 the two differ by 2 percent (72157 vs 73600 for screen/quarter). I cannot edit config.py.
What I tried: build_mesh takes `mode=` (preferred; cap = cfg.mesh.dof_cap(mode)); without it sizing.dof_cap_for infers the mode by matching max_triangles against BOTH formulas, and as a last resort inverts max_triangles_for. Tested in test_mesh_sizing.py.
What I need decided: whether config.mesh_spec should call sizing.max_triangles_for (one source). Task 08 should pass mode= to build_mesh regardless.

## 2026-10-13  task-04  the shipped baseline seed does not fit the plan's dof caps at the screen top frequency
What I was doing: CP-2 table for examples/osse_baseline.yaml.
What happened: this horn is large (bbox 0.401 x 0.321 x 0.26 m, mouth wall area 0.282 m^2 per quarter, 1.129 m^2 full), not the 0.125 m^2 the contracts section 6 table assumed. Measured quarter-domain triangles: 3 kHz 2331, 6 kHz 8819, 9 kHz 19546, 12 kHz 34893 (dofs 1189 / 4498 / 9969 / 17796 est, vertex counts 4530 at 6 kHz). `build_mesh(seed, mesh_spec("screen", cfg), cfg, d, mode="screen")` (f_max 10000, cap 8000) raises MeshTooLargeError (pre-mesh estimate ~13.9k dofs); verify (13000 Hz, cap 16000) is also refused (40,839 triangles); final (13000, cap 24000) builds. f_max_for_dofs (effective c=3.0): screen cap 8000 buys ~7.8 kHz, verify 16000 ~11.0 kHz, final 24000 ~13.5 kHz for this horn.
What I tried: nothing to change; it is a budget decision, and the dof caps themselves are already flagged unsafe on the 8 GB card (TOOLCHAIN M2), so the real caps will be lower still.
What I need decided: with the final caps, either (a) shrink the screen grid top edge / band_hi, (b) lower epw for screen, or (c) accept a smaller seed horn. Search cannot start on the baseline seed as configured.

## 2026-10-13  task-04  decisions on things the examples left open (freeform_hv.yaml, icw_termination.yaml)
What I was doing: DesignSpace.from_config on the shipped YAMLs.
What happened: (1) icw_termination.yaml bounds `kappa0` and `theta1_deg` but its seed_params omit both; they change the geometry (1692 vs 3474 triangles at the same resolution). DesignSpace fills a searchable key that is absent from the seed with the bound midpoint (log-mid for log bounds), logs a WARNING naming the keys, and stores the filled seed (kappa0 0.25, theta1_deg 16.0). (2) freeform_hv.yaml bounds `profileH.mouthAngleDeg`, `profileV.mouthAngleDeg` and a bare `exponent`. Search keys therefore accept dotted paths into the seed (`a.b.0.c`, integers index lists) and, for FREEFORM only, bare `exponent` resolves to the first superellipse station of crossSections. (3) The contract table lists FREEFORM `throatAngleDeg`/`mouthAngleDeg` as keys; in the mesher they live inside profileH/profileV, so those are validated there (top-level use is rejected). (4) The ICW coverage_angle_deg convention (half vs total) is still unconfirmed; I did not touch it.
What I tried: kept every rule in one place (design/families.py param_get/param_set/resolve_path, design/space.py __post_init__) with tests.
What I need decided: confirm midpoint-fill is acceptable, or add kappa0/theta1_deg to the ICW example seed (task 03 owns examples).

## 2026-10-13  task-04  hard-failure exception classes live in mesh/build.py; task 08 must not swallow them
What I was doing: implementing the bbox and symmetry guards.
What happened: types.py has only three exceptions. The bbox-units guard and the quadrants/symmetry-flag guard are not "bad candidate" cases (01_CONTRACTS section 15: units bug, stop the run), so I added MeshConsistencyError(RuntimeError) with subclasses MeshUnitsError and SymmetryMismatchError in mesh/build.py. They deliberately do NOT inherit GeometryInvalidError / MeshTooLargeError.
What I tried: n/a.
What I need decided: search/evaluate.py (task 08) must let MeshConsistencyError propagate (stop the run) rather than turning it into a penalty row. build_mesh also deletes the mesh it just wrote when any post-mesh guard fires, so an unusable .msh is never reachable by a solver.

## 2026-10-13  task-04  note on private-ish mesher API use
What I was doing: the sub-100 ms pre-mesh dof guard (04 test 18).
What happened: the mesher only estimates triangle count after building OCC/gmsh geometry (1.8 s to 17 s before it refuses). The cheap estimate calls hornlab_mesher.config_builder.resolve_geometry (not in public-api.md "Stable") on a 20 mm copy of the config (about 25-60 ms for a quarter domain), sums inner/outer point-grid area, and applies the mesher's own 2.3 tri per A/h^2. It tracks real counts at 0.81x to 1.13x across OSSE / ICW / FREEFORM, 3-12 kHz, so the 1.5x reject margin cannot reject a mesh the cap would accept. It returns None on any exception, in which case only the mesher's checks and the exact post-mesh dof check apply.
What I tried: n/a.
What I need decided: nothing; if resolve_geometry moves in a later mesher SHA the pre-mesh guard silently degrades to the post-mesh one (test_premesh_estimate_tracks_real_counts will fail first).

## 2026-10-13  task-07  dataset: contract gaps and choices the pipeline owner (task 08) must know
What I was doing: implementing dataset/record.py and store.py against 01_CONTRACTS section 13 and 07_TASK_DATASET.
What I decided (all minimal, all documented in the module docstrings; please confirm or rule otherwise):
1. SCHEMA GAP: rule 6 / task item 2b say "the fraction recorded in each record's metadata", but the section 13 metadata schema has no field for it. I added `traces.sample_fraction` (inside the existing `traces` block) and validate_record requires it. No other field was added.
2. lib_shas: the schema example shows 3 entries; task rule 3 says "all four packages plus hornlab_search". validate_record requires FIVE: hornlab_mesher, hornlab_beat_bem, hornlab_bempp_bem, hornlab_plots, hornlab_search (non-empty strings; "unknown" is acceptable for hornlab_search, absence is not). The pipeline must pass all five from TOOLCHAIN.md.
3. ARRAY LAYOUT: I took the task's accepted alternative, ONE uncompressed .npz PER RECORD in `shard-NNNN/rec-RRRR.npz` (plain array names as keys), not 01_CONTRACTS' `shard-NNNN.npz` keyed `<row>/<name>`. Reason: one fsync per record instead of one per array (500 appends in ~3.6 s with three fsyncs each), no zip step, nothing to recover from a crash during shard close. The phase-2 loader must use DatasetStore.read / iter_records / to_training_arrays, not np.load on a shard archive.
4. index.jsonl carries more than {design_hash, shard, row, objective, ok}: also family, backend, mode, lib_sha (= "<mesher10>+<beat10>"), created_utc, solve_seconds, traces (bool). Needed so stats() and the exporter filters read only the index (task rule 6).
5. build_record(ev, target, lib_shas) is the task signature, but an Evaluation does not carry the SolveSpec (mode, observation, gmres_tol, requested freqs), the mesh area_m2, or the mesher grid segment counts / availability. I added keyword-only `solve_spec=`, `area_m2=`, `grid=`, `traces=`, `trace_sample_fraction=`, `excitation=`, `created_utc=`. Task 08 should pass solve_spec, area_m2 and grid on every call; without them those fields are written as null (grid.available False). MeshResult has no area_m2 field and no grid field.
6. DatasetStore.append validates first and RAISES ValueError on an invalid record (nothing is written). The search loop must wrap the call in try/except, log ERROR, and continue: a dataset write must not kill a search.
7. append_traces never overwrites: a second capture for one design_hash goes to traces/<hash>-1.npz and the returned path says so. should_capture_traces(design_hash, fraction) is a deterministic hash-based 1-in-N sampler for the pipeline to use.
8. Single writer: thread lock only, no process lock.
9. Family-imbalance warning fires at >80% one family once the store has >= 10 records (the 10 is mine; a one-record store is trivially 100%).
10. Exporter defaults: X is float32 (as specified); y arrays stay float64. Non-numeric params (ICW termination, FREEFORM point lists) are not X columns and are listed in meta['skipped_keys']; pass keys=DesignSpace.keys() to fix the columns.
What I need decided: items 1, 2 and 3 only; the rest is FYI for task 08.

## 2026-10-13  task-05  solve/: plan-vs-reality mappings the pipeline and metrics owners must know
What I was doing: adapting hornlab_beat_bem 0.2.0 / hornlab_bempp_bem to Backend; all numbers below measured on the RTX 4060 (CP-3 run).
What I decided (read from the installed source, then verified on real solves):
1. ANGLES: the solver takes the signed range directly (ObservationConfig angle_min/max = -90/+90, angle_count=73), H sample a at (R sin a, 0, R cos a), V at (0, R sin a, R cos a) (BeatEngineDriver.jl polar_observation_points). So NO mirroring of a 0..180 sweep; spl_h_db[:, i] is angle -90+2.5*i, +angle = +X (H) / +Y (V). Verified by test 18 (horn shifted to -X / -Y is quieter on the +angle side, 100% of angle pairs, 1-2 dB). Response angles are arc_angles_deg(n) (exact 0); the solver's Float32 echo is asserted equal within 1e-3 deg.
2. LEVELS: spl_h_db/spl_v_db are ABSOLUTE dB re 20 uPa for UNIT NORMAL ACCELERATION of tag 2 (beat spl_db), recomputed from pressure_complex for bempp (whose own spl_db is on-axis normalised). Metrics normalise anyway.
3. z_throat = impedance * (-i*omega) / (rho*c): beat's `impedance` is the area-weighted mean source pressure per unit ACCELERATION in exp(-i omega t); this converts it to specific impedance / rho c in the SAME time convention, so mass-like loading has Im < 0 (the conftest fake uses the opposite sign; only Re is used). Re(z) = 0.075, 0.30, 0.78, 0.97, 1.01 at 500, 1k, 2k, 3k, 4k Hz on the seed, and bempp agrees to 3 digits.
4. n_dof comes from solver_log[i]['native_diagnostics']['p1_dof_count'] (the plan's top-level attribute does not exist); it equals mesh_info.n_vertices and the .msh node count on every mesh tried (2316/2316, 4941/4941).
5. spec.gmres_tol: beat has NO tolerance knob and used a direct dense LU solve ('dense_solve_method': 'lu') on every run, so it is recorded as gmres_tol_requested with gmres_tol_applied=None. bempp takes it.
6. beat refuses native symmetry 'xz' (quadrants '12'). bempp refuses Burton-Miller together with native symmetry, so BemppBackend uses STANDARD on reduced meshes and Burton-Miller on full ones (recorded in meta['formulation']). The cross-check below is therefore Burton-Miller/LU vs STANDARD/bempp: two independent formulations as well as codes.
7. BALLOON: beat's sphere grid is a theta-phi grid (theta 0..180 incl. both poles, phi 0..360 no wrap, theta-major), NOT equal area, and the pole rows are duplicated points. Response.balloon_dirs are built from sphere_theta_deg/phi_deg; Response.meta['balloon_grid']=[n_theta,n_phi] ((16,32) for 512 points; (23,45)=1035 for 1024). DI from it MUST use weights=sin_theta_weights(theta_deg_from_dirs(balloon_dirs)) (task 06); equal weights over-count the poles. I did not resample.
8. CUDA needs one solve_frequencies call per frequency (TOOLCHAIN M3). Measured on beat_cpu: no cliff (4,530 dofs x 4 freqs: one call 18.3 s vs per-frequency 19.2 s; 2,316 dofs x 6: 7.2 vs 7.7 s), so BeatBackend('cpu') makes one call.
9. SEED HORN SIZE vs THE SCREEN BAND (task 04/08/09 should look at this): the osse_baseline seed is 0.80 x 0.64 x 0.27 m. Real builds at epw=6: quarter 4,200 Hz -> 2,316 dofs; 6,000 Hz -> 4,530; the pre-mesh guard estimates 12.6k dofs at 9,528 Hz. So the screen cap (5,000 quarter dofs) resolves the seed only to about 6.3 kHz, not the 10 kHz screen f_max; build_mesh(mode='screen') will raise MeshTooLargeError for the default screen MeshSpec on this seed. My tests mesh at f_max chosen per dof target instead.
10. CUDA OOM / worker-exit handling: BeatBackend turns both into SolveOutcome(ok=False, message='[cuda_oom] ...' / '[worker_exit] ...'), kills the poisoned host (worker.recover_after_failure) and, for cuda_oom, appends one block per process to this file via solve.base.note_failure_for_senior (the dof cap is then suspect; clear stale hosts and reproduce from a clean state first, AGENTS.md rule 7). There is no per-solve timeout hook in the library: timeout_s is checked between frequencies only (CPU makes one call, so it does not apply there).
11. TRACES: beat's traces are in .msh NODE order (pressure, n_vertices) and .msh TRIANGLE order (Neumann, n_faces), no merging. bempp's grid vertices/elements equal those exactly and the symmetry context's reduced P1 space is vertex-ordered, so the dof permutation is the identity (checked by coordinate matching, which refuses unless one-to-one). The plain function_space(grid,'P',1) of an OPEN reduced mesh has FEWER dofs than nodes (2143 vs 2316: free-boundary vertices are constrained), so never use it for a symmetry-reduced solve. Test 19: exact recovery matches the solver far field to 8e-5 dB.
12. PROCESS SHAPE (worker.py): a BEAT host on Windows is venv python -> system python (both `-m hornlab_beat_bem.worker_host`) -> julialauncher.exe -> julia.exe (bare command line). Hosts are found by that marker and killed as a TREE; `taskkill /IM julia.exe` would take anyone's solver. In my runs shutdown_workers() DID stop the host every time (force_killed_roots=[] in all checkpoint runs); the force path is exercised only with a fake process table. A host spawned by a pytest/script process is its child, so killing that process tree (taskkill /T) also ends the host.
What I need decided: nothing blocking; item 9 is the one with consequences.

## 2026-10-13  task-08  pipeline: findings, deviations and decisions for the senior verifier
What I was doing: tasks 1-7 of 08_TASK_PIPELINE and the live CP-6 runs (RTX 4060, exclusive GPU).
FINDINGS (numbers are in the task-08 report):
1. SELFTEST --analytic: the task text assumes the unknown port drive scaling is a CONSTANT. For beat it is not: the port is a unit normal ACCELERATION (TOOLCHAIN C5), so |p| carries 1/omega. Literal constant-velocity R(ka) spread = 24.06 dB (exactly 6.02 dB per octave of ka). run_analytic therefore multiplies |p| by omega first (`drive="acceleration"`, default) and ALWAYS also reports the literal uncorrected spread (`r_spread_raw_db`). With the documented convention: R(ka) spread 0.020 dB (limit 0.5), and independently the ABSOLUTE level matches the unit-acceleration sphere to 0.016-0.036 dB at every ka (rows[].abs_vs_unit_accel_db), omnidirectionality 0.000-0.005 dB, 2 m -> 4 m spreading 6.0205-6.0206 dB, convergence sub3/4/5 = 0.0204 / 0.0051 / 0.0013 dB (sub 5 = 10,242 dofs full domain, solved on beat_cpu in 34 s because it does not fit CUDA). Please confirm the acceleration reading is acceptable for CP-7a #1; it uses only the documented convention and the absolute match is the stronger evidence.
2. The icosphere + gmsh 2.2 writer are in search/selftest.py, the scoped exception the task file grants. Nothing else in the tree writes meshes.
3. LIVE BUG found and fixed: the Julia host resolves a RELATIVE mesh path against its own cwd. `search --resume runs\<dir>` failed every solve ("opening file ... No such file"). evaluate() and cma._prepare now resolve run_dir to an absolute path (test added). The 10 failed records that run wrote to the first dataset were moved aside with that dataset (scratch/polluted/), and the live chain was re-run from empty runs/ cache/ dataset/ directories.
DECISIONS the contract left open (all minimal; rule on them if you disagree):
4. terms in Evaluation.terms are RAW (unweighted); weighted = weights[k]*terms[k] (objective.weighted_terms). Key set is always TERM_KEYS + n_nan, n_in_band, di_estimated. A term whose every in-band value is NaN is set to NAN_TERM_FILL = 30.0 (finite, worse than a working design, far below the 1e3 failure penalty). Out-of-contract number, flagged. Target.freq_weights is not used (the contract defines no semantics for it). n_nan counts in-band FREQUENCIES with an unmeasurable input.
5. DI from the solver's theta-phi balloon: metrics/compute.py is not mine and assumes equal weights. search/evaluate.py:metrics_from_response computes the sin(theta)-weighted DI with di_from_balloon(weights=...) per frequency and hands compute_metrics a one-column balloon holding that weighted power, so every metric/scalar/di_source comes out of compute_metrics unchanged and DI is exactly the weighted one (tested against the exact cardioid DI 4.77 dB; equal weights are off by >0.25 dB). A balloon without meta['balloon_grid'] is treated as equal-area.
6. Cache/resume semantics: (a) in-run memo `ctx.known`, preloaded from search.ndjson, serves successful rows AND deterministic failures (invalid geometry, mesh too large); a hit writes no ndjson row, no dataset record, consumes no budget. Solver failures are not memoized (a retry may succeed). (b) cross-run solve cache cache/solve/<design>-<mesh>-<solve>/ (hit needs ok:true) re-scores the stored Response with the CURRENT weights; it appends an ndjson row flagged cached and a dataset record only if the store has none for (design, mode, ok). (c) --budget counts non-cached evaluations of THIS invocation, the seed included, checked before every candidate, so a run can stop mid-generation (the partial generation is not told to CMA); cma maxfevals is deliberately unused. (d) run.json stats are cumulative over resumes (from the ndjson); the last invocation's own numbers are under last_invocation. A resume starts best from the best row already on disk, so a short resume cannot overwrite best.json with a worse design (live-found, test added).
7. Dataset: one record per NON-CACHED evaluation (failures included); mesh.grid.available is True (the grid is regenerable through hornlab_mesher.config_builder.build_point_grid from the recorded params; it is not stored per record), angular/length segments are read from the mesher config (defaults 64/32). The trace fraction is a CLI flag/argument (--trace-fraction, default record.DEFAULT_TRACE_FRACTION 0.05), not a YAML key (none exists in the contract); traces come from BeatBackend.solve_traced on the ORIGINAL solve.
8. Report: convergence, stacked term bars and beamwidth/DI-vs-frequency (with f_break/f11 marker lines and the target band) are small inline SVGs written in report/html.py because hornlab_plots has no equivalent and the task asks for them; all physics PNGs (heatmaps, polars, DI, impedance) come from hornlab_plots, no matplotlib import. The noise-floor box uses NOISE_FLOOR_INPUTS (idempotence 3.6e-5 dB, full-vs-quarter 0.031 dB, beat-vs-bempp 0.055 dB from the task 05 report; epw=6 discretization error NOT YET MEASURED, CP-7c), overridable via run.json["noise_floor"]. It says the floor is a lower bound until CP-7c is done.
9. OBJECTIVE SCALE (task asked to print the terms and flag a 100x term): osse_baseline seed, raw/weighted: cov 19.22/19.22, rip 1.496/1.496, di 0.286/0.086, dislope 0.193/0.096, flat 3.388/1.694, load 0/0, J = 22.59. cov is 224x the weighted di term. This is the SEED being far from the 75x45 target (bw_h about 95, bw_v about 84 deg), not a wrong divisor; the /100 and /10 are in the frozen contract, so I did NOT change them. If you want di/dislope to matter during the search, raise their YAML weights (they are data, not code).
10. Seed J is reproducible across processes (osse_baseline 22.5921 twice; search_smoke 22.0678 twice and an identical 60-evaluation trajectory in two separate searches): GPU nondeterminism is below anything CMA sees.
11. verify mode: verify and final meshes still equal the screen mesh (bands are clipped to band_hi), so `verify` differs from `screen` only by the 25-point frequency grid and the larger balloon; screen vs verify J differed by 0.04-0.35 on the top 3 designs, which is a measure of how much the 12-point screen grid can mis-rank.
12. search_smoke is much cheaper than the plan assumed: 580-2,880 dofs, 4.2 s/candidate (mesh 0.45 s, solve 4.15 s), 847 candidates/h => 1,000 evaluations = 1.2 h, 10,000 = 11.8 h. osse_baseline's seed alone is 3,850 dofs / 18 s (first solve, includes JIT).
What I need decided: item 1 (acceleration reading), items 4, 5, 6c, 7 as listed.

## 2026-10-13  task-09  Wave 3 senior rulings + CP-7 results (RESOLUTIONS, append-only record)
What I was doing: Wave 3 — the CP-7 physics gate (verifier lane, oracle) and the senior rulings over every open
NOTES_FOR_SENIOR block (rulings lane, oracle). Both ran; the user confirmed/adjusted the rulings. This block is the
durable record so no future agent has to re-derive any of it from chat.
CP-7 results (all PASS, pasted output in the verifier report, mirrored in docs/CONTINUITY.md):
  - CP-7a analytic sphere PASS: R(ka) spread 0.020 dB (<0.5), omnidirectionality <=0.005 dB, spreading 6.0205-6.0206 dB,
    convergence sub3/4/5 = 0.0204/0.0051/0.0013 dB (monotone). Acceleration-drive reading CONFIRMED (the raw
    24.06 dB/octave constant-velocity spread is expected, NOT a failure).
  - CP-7b two solvers PASS: beat_cuda vs bempp_cpu 0.039 dB overall (<0.2 dB).
  - CP-7c mesh convergence PASS on a REDUCED band 500-2500 Hz (quarter, symmetry) because the seed at epw=18 over the
    full band needs ~40k quarter dofs (OOM). GATE met: epw=6 vs epw=18 -> mean|dbw_h|=0.287 deg (<2), mean|dDI|=0.028 dB (<0.3).
  - CP-7d symmetry PASS: max asymmetry 4e-6 dB (imposed symmetry -> solver noise floor); M6 full-vs-quarter on the SEED
    = 0.023 dB (<=3 kHz).
  - CP-7e plausibility PASS (borderline): f0 = 343 Hz (H) / 480 Hz (V) from mesh bbox + measured beamwidth, both below
    the 500 Hz band floor; DI-vs-beamwidth max diff 2.15 dB (slightly over the 1.5 dB guideline, well under the 3 dB
    "computed wrong" threshold); f11 = 5653 Hz sits just ABOVE the clipped 5500 Hz band -> onset NOT resolved.
  - CP-7f noise floor = 0.039 dB (two-solver disagreement dominates; epw=6 DI discretization 0.028 dB just below it;
    idempotence 3.6e-5 and asymmetry 4e-6 are ~1000x smaller). Report's prior "0.055 dB, epw=6 unmeasured" is superseded:
    the floor is NOT mesh-limited and was already the floor.
RULINGS (each block -> outcome -> change applied):
  1. task-08 item 1 (acceleration drive) -> CONFIRM (no waiver; the absolute unit-acceleration match 0.016-0.036 dB is the stronger evidence).
  2. task-06 "-6 dB" half-pressure (-6.0206) -> CONFIRM.
  3. task-06 di_from_cuts clamp (bw>=180 saturation; both>=180 -> omni DI=0) -> CONFIRM.
  4. task-06 ripple ddof=1 (sample std) -> CONFIRM; the earlier tiling study's sigma convention is NOT recorded anywhere (evidence gap, no code change).
  5. task-06 small items -> CONFIRM: constants.py comment now says "throat diameter" (edited); coverage_from_room band kwarg ok; 512-pt DI quadrature bias (narrow-beam +0.23 dB) affects no gate.
  6. task-03 no YAML freq-grid key -> CONFIRM (grid shape is frozen; a user key would silently split the dataset label space).
  7. task-03 CP-1 test 3 angle step (18000 % (n-1) == 0) -> CONFIRM.
  8. task-03 ICW coverage_angle_deg -> CONFIRM HALF-angle (read from mesher source: theta0 < coverage_angle < 90); "UNCONFIRMED" removed from families.py + YAML.
  9. task-04 sectioned to_mesher_config -> CONFIRM (mesher silently ignores top-level max_triangles; tests pin it).
  10. task-04 vs task-03 mesh_spec -> OVERRULE: config.mesh_spec now calls sizing.max_triangles_for (single source, honours dof_per_triangle=0.51). EDITED config.py + docstring (was a 2% drift). Pass mode= to build_mesh -> CONFIRM.
  11. dof caps + band_hi lowered -> CONFIRM (user: "keep the lowered top band edges; override only with a smaller seed or fewer epw").
  12. task-04 midpoint-fill -> USER OVERRULED the silent fill for kappa0/theta1_deg: explicit seeds added to examples/icw_termination.yaml (kappa0 0.25, theta1_deg 16.0 keep geometry); the fill remains only as a defensive net (test rewritten: test_design_space.py).
  13. MeshConsistencyError taxonomy (not swallowed) -> CONFIRM.
  14. task-07 traces.sample_fraction / lib_shas=5 / one-npz-per-record -> all CONFIRM (phase-2 must use DatasetStore).
  15. task-08 raw terms + NAN_TERM_FILL 30.0; sin(theta)-weighted balloon DI; cache/resume/budget semantics; dataset record choices -> all CONFIRM; Target.freq_weights stays unused (contract defines the field with no semantics - gap).
Also applied: record.py excitation note now states the unit-ACCELERATION convention (user edit); new tests/test_mesh_pin.py (fails on a silent HornLab pin bump) and hornlab_search/mesh/grid.py + tests/test_mesh_grid.py (single seam over build_point_grid, issue #9).
RESIDUAL RISKS (recorded, NOT resolved - for phase 2 / post-Wave-3):
  1. epw=6 discretization above ~2.5 kHz is UNMEASURED (the epw=18 reference cannot be built there on this 8 GB card); a
     systematic epw=6 bias in the 2.5-5.5 kHz screening band would bias every ranking, and no test catches it.
  2. The higher-order throat mode f11 (5653 Hz on the 1.4 in seed throat) is never exercised - the screen band clips at 5500 Hz.
  3. DI-vs-beamwidth is NOT a regression test (only the analytic cardioid/dipole closed forms are); the real seed shows
     2.15 dB max balloon-vs-cuts difference, the known non-separable-rectangular signature.
  4. Secondary: the cross-run solve cache did not dedup the seed across separate `run` then `search` invocations (both
     cached:False), so the seed was solved twice and the dataset holds two seed records.
What I need decided: nothing blocking. Phase 2 (11_PHASE2_SURROGATE) is "separately and later"; post-Wave-3 follow-ups
(widen a_deg/exponent bounds, run the other 4 example configs for a multi-family dataset, browser-check report.html) are
the natural next work, not part of Wave 3.

## 2026-10-14  cp-8d (local GPU box)  Stage A train failed twice on real data: epochs 300 then 600; propose/round NOT run
What I was doing: CP-8d step 1 of the runbook — `surrogate train --config examples/osse_baseline.yaml` on the real OSSE
pool (all 8 gate inputs are real BEM records; 5 gate measurements per table). CPU-only torch.
What happened (exact gate tables):
- epochs 300:  spearman 0.96734 PASS | topk_overlap 5 (need >= 12 of 20) FAIL | bw_mae_deg 2.11007 (need < 2.0) FAIL |
  di_mae_db 0.28669 PASS | invalid_accuracy 0.85714 PASS | monotonic_flips 0 PASS. Held-out 285 (< 500). Exit 1.
- epochs 600:  spearman 0.98613 PASS | topk_overlap 15 PASS | bw_mae_deg 1.70415 PASS | di_mae_db 0.23190 PASS |
  invalid_accuracy 0.95238 PASS | monotonic_flips 1 (need == 0) FAIL. Same pool. Exit 1.
Both: pool considered 2034 (all OSSE-family records incl. throat_adapter), selected 1501,
skipped_grid_mismatch 533 (133 search_smoke-grid + 400 throat_adapter-grid records), skipped_bad_arrays 0,
1 duplicate dropped before the cluster holdout, objective delta (recomputed vs stored) 0 — zero weight/target drift.
What I tried: the runbook's own fix list in order — more epochs (300 -> 600: every measured gate IMPROVED, but
monotonic_flips went 0 -> 1); --lib-sha is moot (every record carries one lib_sha, b922e807a5+38544d214b).
`propose` / `surrogate round` were NOT run (runbook: propose only when gates pass; "do NOT use the model" otherwise).
Per hard rule 8 (failed twice on the same step): stopped and appended this block.
What I need decided: (1) approve the remaining runbook fix — an OSSE top-up of ~1900 records
(`search --config examples/osse_baseline.yaml --resume runs/20261013T123136Z-screen-ca15be --budget 1900`,
~10.2 h at the measured 187/h) taking the OSSE pool to ~3400 so held-out clears the 500 floor and the formal
gates can legitimately pass; (2) is monotonic_flips = 1 at 600 epochs expected sweep-boundary/validity-boundary
noise (the oracle's earlier reading of sweep_sign_flips' tolerance vs invalid-region crossings), or a genuine
model defect to fix in code (NOT by touching gates.py thresholds)? Repro command is the epochs-600 line above;
training is seeded/deterministic. (3) Should the built `surrogate round` helper ever be run as a clearly-labelled
DIAGNOSTIC on a gate-failed model, or stay unusable until a formal pass (current behaviour per the runbook)?
