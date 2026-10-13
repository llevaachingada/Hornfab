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
