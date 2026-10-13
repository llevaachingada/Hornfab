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
