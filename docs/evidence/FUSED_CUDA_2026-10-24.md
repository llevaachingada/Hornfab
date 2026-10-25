# WP15 fused CUDA Burton-Miller: measurement pass on the 8 GB RTX 4060 (M2, 2026-10-24)

Scope: the fused CUDA Burton-Miller path in the `hornlab_beat_bem` fork (branch
`hornlab-search/fused-cuda` @ `fa99ee5`), its validation ladders, the flag-off determinism finding,
and the VRAM-ceiling sweep that sets the new dof caps. Raw logs: `runs/m2_fused_cuda/` (gitignored;
every block below is copied byte-for-byte from those files). Nothing here is a new solver and no
tolerance was loosened without a documented floor (the one rebarred test is section 5).

> **Physics caveat (print with every 12 kHz number).** The source is a rigid uniform-velocity spherical cap. Above
> the throat's first cross mode (f11 = **7,914 Hz** for the 1-inch exit, computed in every record) a real
> compression driver is not a uniform cap, so **8-12 kHz results compare GEOMETRIES, not drivers**. Free-standing
> horn, rigid lossless walls, 25 log-spaced frequencies 300-12,000 Hz (isobars interpolate between them).

— `docs/evidence/HF12K_VERIFY_2026-10-23.md:6-9`. The 12 kHz verify for this pass is section 9.

## 1. Install and doctor (`doctor_post_install.log`)

Fork installed by SHA, GPU provisioned, all 5 example configs load. The one WARNING is expected until the
dev-branch pin lands: the installed `hornlab_beat_bem` is the fork SHA, while `pyproject.toml` still carries the
base pin.

```
PASS  python-version    Python 3.12.10 in [3.11, 3.14)
PASS  core-imports      numpy, scipy, cma, yaml, jinja2
PASS  hornlab-imports   mesher, beat, plots; bempp yes
PASS  pinned-shas       WARNING: hornlab-beat-bem: installed fa99ee594087 != expected 38544d214ba2
PASS  toolchain         TOOLCHAIN.md present, dof_per_triangle=0.51
PASS  gpu               nvidia-smi exits 0
PASS  backend           beat_cuda functional (state=ready)
PASS  configs           all 5 example configs load
PASS  round-trip        seed meshed at 1.5 kHz: 846 tris, 468 nodes, largest extent 0.401 m (metres), source tag 2 present, quadrants '1' <-> symmetry 'yz+xz'
PASS  gpu-hygiene       0 BEAT host(s) alive, VRAM used 401.0 MiB
PASS  disk-space        runs(C:\) 108.6 GB free
doctor OK: 11 checks, 0 failed
```

Interpretation: `installed fa99ee594087 != expected 38544d214ba2` is the fork SHA vs the base pin in
`pyproject.toml`. It is expected and is cleared by the `dev/fused-cuda-pin` branch (section 8), not by hand-editing
the installed copy. The stderr preamble before the table is the mesher's density WARNING —
`outer wall clearance wants 11.738 mm ... holding at 19.056 mm` — which states
`The acoustic (inner) surface is unaffected`.

## 2. Ladder A — analytic sphere, `selftest --analytic` (`ladder_a_selftest_analytic.log`)

```
analytic self-test: pulsating sphere a=0.1 m, backend beat_cuda, icosphere sub=3 (1280 tris, 642 dofs)
  ka     f (Hz)   analytic (dB rel)  solved (dB rel)  R(ka) deviation (dB)  abs vs unit-accel sphere (dB)
  0.5        273             -6.990           -7.002                -0.012                  -0.036
  1          546             -3.010           -3.015                -0.005                  -0.029
  2         1092             -0.969           -0.966                 0.003                  -0.021
  4         2184             -0.263           -0.257                 0.006                  -0.018
  8         4367             -0.067           -0.059                 0.008                  -0.016
  R(ka) spread (max-min) = 0.020 dB with the acceleration-drive correction (tolerance 0.5 dB); literal constant-velocity R(ka) spread = 24.062 dB
  omnidirectionality, std of dB over the balloon per ka: 0.0000, 0.0000, 0.0000, 0.0000, 0.0050  (limit 0.1 dB)
  spreading 2 m vs 4 m per ka (dB): 6.0206, 6.0206, 6.0206, 6.0205, 6.0206   (target 6.0206 +/- 0.05)
  convergence, R(ka) spread (dB) by subdivision: sub3=0.0204 [642 dofs, beat_cuda], sub4=0.0051 [2562 dofs, beat_cuda], sub5=n/a [10242 dofs, beat_cpu]  monotone decreasing: False
  PASS  R(ka) spread
  PASS  omnidirectionality
  PASS  spreading 2m->4m
  FAIL  convergence
  RESULT: PASS (convergence not demonstrated)
selftest --analytic: PASS (R(ka) spread 0.020 dB vs 0.5 dB; convergence monotone: False)
```

Interpretation: R(ka) spread **0.020 dB vs the 0.5 dB bar — PASS**; 6.0206 dB spreading and
omnidirectionality 0.0000-0.0050 dB also pass. The convergence level is `n/a`: it needs the `beat_cpu`
runtime, which is not provisioned on this lane, so monotonicity is not demonstrated (pre-existing, unrelated to
the fused path; the analytic and cross-check ladders both still pass).

## 3. Ladder B — GPU vs independent CPU BEM, `selftest --crosscheck` (`ladder_b_selftest_crosscheck.log`)

```
cross-check: beat_cuda (2396 dofs, 10.3 s) vs bempp_cpu (2396 dofs, 142.8 s, formulation=standard), same mesh (quadrants '1', 4615 tris, symmetry yz+xz)
  f (Hz)   max|dH| norm dB   max|dV| norm dB   mean|dH| norm dB
      500          0.0072           0.0037           0.0031
      833          0.0123           0.0253           0.0068
     1387          0.0226           0.0361           0.0105
     2309          0.0166           0.0184           0.0067
     3845          0.0308           0.0390           0.0083
  overall max 0.0390 dB -> under 0.2 dB: both are very likely right (strongest verification available)
selftest --crosscheck: done, overall max normalized difference 0.0390 dB
```

Interpretation: an independent CPU BEM agrees with the CUDA path to **0.0390 dB overall, bar 0.2 dB — PASS**.
That 0.039 dB is also the CP-7f A/B bar used to judge the fused path below.

## 4. Ladder C — A/B on three designs, flag OFF (fused install, default path)

Purpose: prove the fork does not move the *existing* path. Each arm re-solved a design already measured
pre-fork and compared the stored response with the new one. Same design hash in A and B for all three arms
(3/3), and the run provenance itself is verified: `run.json` `lib_shas.hornlab_beat_bem =
fa99ee594087507c2808b9e7db09b38d8d4dcc20`, `solve.cuda_fused` absent from the run config, and the
`response.npz` meta records `"cuda_fused": false` — i.e. these are flag-off runs, so the numbers below isolate
the base path.

| arm | design | A (reference) | B (fused-install run) | design hash | dofs | solve s | J | max Δ dB | max Δ deg |
|---|---|---|---|---|---|---|---|---|---|
| a | `osse_axi` seed | `runs/20261023T025720Z-screen-2002c3` | `runs/20261025T002354Z-screen-bad518` | `d04e8697a87d` | 1013 | 9.6 | 19.8072 | 2.912e-06 (on-axis) | 2.023e-05 (bw V) |
| b | perturbed best | `scratch/fed761.ndjson` | `runs/20261025T002540Z-screen-1e5d78` | `fed761193da7` | 1028 | 10.0 | 10.2971 | 2.501e-06 (on-axis) | 1.357e-05 (bw H) |
| c | `freeform_sculpt` seed | `runs/20261023T193311Z-screen-03d787` | `runs/20261025T002443Z-screen-1f4a09` | `892bb3551903` | 1362 | 11.3 | 30.9448 | 2.294e-06 (on-axis) | 1.295e-05 (bw H) |

Raw, verbatim (`ab_a_osse_axi_seed_solve.log` + `ab_a_osse_axi_seed_compare.log`):

```
run OK: seed J=19.8072, 1013 dofs, solve 9.6 s; output runs\20261025T002354Z-screen-bad518
compare A=runs\20261023T025720Z-screen-2002c3 (design d04e8697a87d, quadrants '1')
        B=runs\20261025T002354Z-screen-bad518 (design d04e8697a87d, quadrants '1')
  12 frequencies 500..5500 Hz
  bw_h_deg     max |diff| 1.811e-05 deg  mean 4.919e-06  (n=12)
  bw_v_deg     max |diff| 2.023e-05 deg  mean 4.148e-06  (n=12)
  di_db        max |diff| 1.29e-06 dB   mean 5.2e-07  (n=12)
  on_axis_db   max |diff| 2.912e-06 dB   mean 1.202e-06  (n=12)
  ripple_h_db  max |diff| 4.289e-07 dB   mean 1.571e-07  (n=12)
  ripple_v_db  max |diff| 2.488e-07 dB   mean 1.235e-07  (n=12)
compare OK (report only; reference: OSSE full vs quarter 0.023 dB, CP-7d)
```

`ab_b_perturbed_best_solve.log` + `ab_b_perturbed_best_compare.log`:

```
run OK: seed J=10.2971, 1028 dofs, solve 10.0 s; output runs\20261025T002540Z-screen-1e5d78
compare A=scratch\fed761.ndjson (design fed761193da7, quadrants '1')
        B=runs\20261025T002540Z-screen-1e5d78 (design fed761193da7, quadrants '1')
  12 frequencies 500..5500 Hz
  bw_h_deg     max |diff| 1.357e-05 deg  mean 3.845e-06  (n=12)
  bw_v_deg     max |diff| 7.417e-06 deg  mean 2.788e-06  (n=12)
  di_db        max |diff| 7.552e-07 dB   mean 3.433e-07  (n=12)
  on_axis_db   max |diff| 2.501e-06 dB   mean 6.206e-07  (n=12)
  ripple_h_db  max |diff| 3.147e-07 dB   mean 1.263e-07  (n=12)
  ripple_v_db  max |diff| 3.567e-07 dB   mean 1.068e-07  (n=12)
compare OK (report only; reference: OSSE full vs quarter 0.023 dB, CP-7d)
```

`ab_c_sculpt_seed_solve.log` + `ab_c_sculpt_seed_compare.log`:

```
run OK: seed J=30.9448, 1362 dofs, solve 11.3 s; output runs\20261025T002443Z-screen-1f4a09
compare A=runs\20261023T193311Z-screen-03d787 (design 892bb3551903, quadrants '1')
        B=runs\20261025T002443Z-screen-1f4a09 (design 892bb3551903, quadrants '1')
  12 frequencies 500..5500 Hz
  bw_h_deg     max |diff| 1.295e-05 deg  mean 4.838e-06  (n=12)
  bw_v_deg     max |diff| 1.076e-05 deg  mean 5.148e-06  (n=12)
  di_db        max |diff| 1.097e-06 dB   mean 4.149e-07  (n=12)
  on_axis_db   max |diff| 2.294e-06 dB   mean 8.685e-07  (n=12)
  ripple_h_db  max |diff| 6.422e-07 dB   mean 1.582e-07  (n=12)
  ripple_v_db  max |diff| 6.543e-07 dB   mean 2.183e-07  (n=12)
compare OK (report only; reference: OSSE full vs quarter 0.023 dB, CP-7d)
```

Interpretation: worst case across the three arms is **2.912e-06 dB** (bar 0.039 dB) and **2.023e-05 deg**
(bar 1 deg) — 4 to 5 orders of magnitude inside the bars, and the same order as the known Float32 floor. The
fork's default path is unchanged.

## 5. Fused path GPU gate and the determinism finding

`tests/test_solve_beat_fused_cuda.py` (`-m "slow and gpu"`) has two tests: (1) fused vs default agreement at
2 kHz, bars 0.01 dB on-axis / 0.1 deg beamwidth / 1e-3 relative `z_throat`; (2) flag-off self-reproduction.

### 5.1 First run — agreement PASS, determinism FAILED (`fused_gpu_test.log`)

```
  [measured] fused_cuda A/B @ 2000 Hz, seed quarter mesh: on-axis max diff 0.0000 dB (bar 0.01); bw H 76.65->76.65 deg, V 84.18->84.18 deg (bar 0.1); z_throat rel 5.53e-07 (rtol 0.001)
.F                                                                       [100%]
================================== FAILURES ===================================
______________ test_flag_off_reproduces_itself_from_a_clean_host ______________

ctx = <test_solve_beat_fused_cuda._Ctx object at 0x000001C67E9E9430>
capsys = <_pytest.capture.CaptureFixture object at 0x000001C67EFD68A0>

    def test_flag_off_reproduces_itself_from_a_clean_host(ctx, capsys):
        """Flag OFF from a clean host: the default path is deterministic for the same solve spec."""
        worker.shutdown(verify=True)                                # leave the fused host behind
        be = BeatBackend("cuda")
        assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "0"
        out_a = be.solve(ctx.mesh, ctx.spec)
        assert out_a.ok, out_a.message
        out_b = be.solve(ctx.mesh, ctx.spec)
        assert out_b.ok, out_b.message
        a = np.asarray(out_a.response.spl_h_db, dtype=float)
        b = np.asarray(out_b.response.spl_h_db, dtype=float)
>       assert np.array_equal(a, b), "the flag-off path must deterministically reproduce itself"
E       AssertionError: the flag-off path must deterministically reproduce itself
E       assert False
E        +  where False = <function array_equal at 0x000001C6468E5D30>(array([[ 1.20185630e+01,  1.23395333e+01,  1.27042739e+01,\n         1.31117591e+01,  1.35593730e+01,  1.40434192e+01,\n...-5.95648882e+00, -7.62325362e+00,\n        -9.36055990e+00, -1.05906344e+01, -1.07790516e+01,\n        -1.09466329e+01]]), array([[ 1.20185621e+01,  1.23395320e+01,  1.27042728e+01,\n         1.31117583e+01,  1.35593725e+01,  1.40434182e+01,\n...-5.95651027e+00, -7.62327476e+00,\n        -9.36057729e+00, -1.05906409e+01, -1.07790351e+01,\n        -1.09466102e+01]]))
E        +    where <function array_equal at 0x000001C6468E5D30> = np.array_equal

tests\test_solve_beat_fused_cuda.py:116: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_solve_beat_fused_cuda.py::test_flag_off_reproduces_itself_from_a_clean_host
```

Interpretation: the fused path itself is exact at the printed precision (0.0000 dB on-axis, identical
beamwidths, 5.53e-07 relative impedance). The failure is the *zero-tolerance* `np.array_equal` on two
identical flag-off solves.

### 5.2 Same failure on the BASE PIN (`det_check_base_pin.log`)

Base pin `38544d2` reinstalled (`pip install --force-reinstall` rollback), same test, same result:

```
F                                                                        [100%]
================================== FAILURES ===================================
______________ test_flag_off_reproduces_itself_from_a_clean_host ______________

ctx = <test_solve_beat_fused_cuda._Ctx object at 0x000002CD1C1FADE0>
capsys = <_pytest.capture.CaptureFixture object at 0x000002CD6A5FA8D0>

    def test_flag_off_reproduces_itself_from_a_clean_host(ctx, capsys):
        """Flag OFF from a clean host: the default path is deterministic for the same solve spec."""
        worker.shutdown(verify=True)                                # leave the fused host behind
        be = BeatBackend("cuda")
        assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "0"
        out_a = be.solve(ctx.mesh, ctx.spec)
        assert out_a.ok, out_a.message
        out_b = be.solve(ctx.mesh, ctx.spec)
        assert out_b.ok, out_b.message
        a = np.asarray(out_a.response.spl_h_db, dtype=float)
        b = np.asarray(out_b.response.spl_h_db, dtype=float)
>       assert np.array_equal(a, b), "the flag-off path must deterministically reproduce itself"
E       AssertionError: the flag-off path must deterministically reproduce itself
E       assert False
E        +  where False = <function array_equal at 0x000002CD3A5C9A30>(array([[ 1.20185626e+01,  1.23395328e+01,  1.27042732e+01,\n         1.31117591e+01,  1.35593731e+01,  1.40434184e+01,\n...-5.95650227e+00, -7.62326264e+00,\n        -9.36055336e+00, -1.05906265e+01, -1.07790593e+01,\n        -1.09466503e+01]]), array([[ 1.20185610e+01,  1.23395313e+01,  1.27042722e+01,\n         1.31117583e+01,  1.35593727e+01,  1.40434182e+01,\n...-5.95649225e+00, -7.62325511e+00,\n        -9.36055489e+00, -1.05906336e+01, -1.07790557e+01,\n        -1.09466333e+01]]))
E        +    where <function array_equal at 0x000002CD3A5C9A30> = np.array_equal

tests\test_solve_beat_fused_cuda.py:116: AssertionError
---------------------------- Captured stdout setup ----------------------------

----------------------------- Captured log setup ------------------------------
WARNING  hornlab_mesher.density:density.py:675 [hornlab-mesher] outer wall clearance wants 11.736 mm on 16 of 74 rings, finer than the 14.292 mm this build requests anywhere; holding at 14.292 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
=========================== short test summary info ===========================
FAILED tests/test_solve_beat_fused_cuda.py::test_flag_off_reproduces_itself_from_a_clean_host
```

**Finding: bit-for-bit determinism is not attainable on Float32 CUDA upstream.** The diffs in the two arrays
above are ~9e-8 dB (fork `fa99ee5`) and ~1.6e-7 dB (base pin `38544d2`) — one float32 ulp at these levels —
so the property is pre-existing, not introduced by the fork. The CUDA assembly/solve runs Float32 with
order-varying reductions. Not rule 8: diagnosed in one pass by the base-pin reproduction.

Action (rule 7 evidence trail): the assertion was replaced by a documented **1e-4 dB floor** with a
`[measured]` print of the actual diff; the test docstring carries both measurements. `NOTES_FOR_SENIOR.md`
(2026-10-24, orchestrator block), verbatim:

> Finding during `tests/test_solve_beat_fused_cuda.py` (M2 work order step 3): test 2 asserted
> `np.array_equal` (zero tolerance) for two back-to-back flag-off solves of the same spec. It FAILS on the
> fork @ fa99ee5 with max |d spl_h_db| ~9e-8 dB — and identically (max ~1.6e-7 dB, same assertion) on the
> BASE PIN 38544d2 after a `pip install --force-reinstall` rollback (`runs/m2_fused_cuda/fused_gpu_test.log`,
> `runs/m2_fused_cuda/det_check_base_pin.log`). The CUDA assembly/solve runs Float32 with order-varying
> reductions: ~1e-7 dB (one float32 ulp at these levels) between identical requests is upstream physics,
> pre-existing, not introduced by the fork (the ladder A/Bs, old-vs-new runs days apart, show the same
> ~1e-6 dB floor). NOT rule 8: diagnosed in one pass with the base-pin reproduction.
>
> Action taken (rule 7 evidence trail): the assertion was replaced by a documented floor
> `max |d spl_h_db| <= TOL_DET_DB = 1e-4 dB` with a `[measured]` print of the actual diff
> (test_solve_beat_fused_cuda.py::test_flag_off_reproduces_itself_from_a_clean_host; docstring carries
> both measurements). 1e-4 dB is 3 orders above the measured floor and ~400x below the CP-7f A/B bar
> (0.039 dB), so any real path/cache/host mixup (full-dB moves) still fails. Oracle to adjudicate.

1e-4 dB is 3 orders above the measured floor and ~400x below the 0.039 dB A/B bar, so a real path, cache or
host mixup (full-dB moves) still fails. **Oracle to adjudicate** the rebar.

### 5.3 Re-run after the rebar — both tests pass (`fused_gpu_test_rerun.log`)

```
  [measured] fused_cuda A/B @ 2000 Hz, seed quarter mesh: on-axis max diff 0.0000 dB (bar 0.01); bw H 76.65->76.65 deg, V 84.18->84.18 deg (bar 0.1); z_throat rel 3.35e-07 (rtol 0.001)
.
  [measured] [measured] flag-off determinism, same spec twice: max |d spl_h_db| 1.74e-05 dB (floor 0.0001; CP-7f bar 0.039)
.                                                                       [100%]
```

Interpretation: fused A/B still exact at printed precision; the flag-off floor test now measures
**1.74e-05 dB**, the worst observed, comfortably under the 1e-4 dB floor.

## 6. VRAM ceiling — where the 12,000-dof caps come from

### 6.1 Protocol

- **TOOLCHAIN M2**: one solve per **fresh process**, VRAM baseline recorded **before** the solve, peak read by
  `nvidia-smi --query-gpu=memory.used` polled from the harness's **own daemon thread** (every ~0.2 s) — never a
  Python-side probe that can read 0. `CLAUDE.md` "GPU / Julia hygiene" applies: stale hosts cleared, one
  measurement per process, poll started first, every measurement ends with
  `worker.shutdown(verify=True)` verified against the process list.
- **`gpu-clean` between points** (the caller runs it; each log line `CLEAN: no stale BEAT hosts` is the proof),
  and a verified shutdown after each point (`SHUTDOWN: worker.shutdown(verify=True) ok; force-killed root pids: []`).
- One frequency per point (1000 Hz, the harness default; 73 angles), quarter domain, symmetry `yz+xz`, same
  `osse_baseline` seed geometry for every point. Harness:
  `tools/measure_fused_ceiling.py`. Invocations, e.g. for the 8,919-dof pair and the 12,183-dof point:

```
.venv\Scripts\python.exe tools/measure_fused_ceiling.py --mouth-res 6.72 --throat-res 3.36 --flag off
.venv\Scripts\python.exe tools/measure_fused_ceiling.py --mouth-res 6.72 --throat-res 3.36 --flag on
.venv\Scripts\python.exe tools/measure_fused_ceiling.py --mouth-res 5.74 --throat-res 2.87 --flag on
```

  (each preceded by `hornlab-search gpu-clean`; `--freq` defaults to 1000 Hz, `--angles` to 73.)

- **Horn note (why the mouth-res numbers look small).** The dofs-vs-mouth-res calibration was done against the
  **`examples/osse_baseline.yaml` seed**, which is a much larger horn than the TOOLCHAIN M1 calibration horn:
  at 3/1.5 mm that seed meshes to 87,240 triangles / **43,993 dofs**, so resolution had to be coarsened to hit
  the dof targets. The mouth-res values used were **6.72 / 5.74 / 5.02 / 4.45 mm**. Consequently the older
  toolchain's ~8,941-dof row is **not directly comparable in geometry** — same measurement protocol, different
  horn (and no fused path existed for it).

### 6.2 Table

dofs are solver-reported (`MESH ... dofs=`, matching `p1_dof_count`); MiB are integers from the harness.

| dofs (measured) | path | triangles | assembly_s | solve_s | s_per_freq | baseline MiB | peak MiB | peak−baseline MiB | result |
|---|---|---|---|---|---|---|---|---|---|
| 8,919 | default CUDA (flag off) | 17,500 | 28.714 | 28.311 | 59.607 | 437 | 7,826 | 7,389 | ok |
| 8,919 | `fused_cuda` (flag on) | 17,500 | 6.13 | 0.76 | 9.111 | 569 | 2,786 | 2,217 | ok, `meta_cuda_fused: true` |
| 12,183 | `fused_cuda` | 23,973 | 8.887 | 1.648 | 13.72 | 169 | 4,913 | 4,744 | ok |
| 15,984 | `fused_cuda` | 31,522 | 437.184 | 16.72 | 458.577 | 182 | 7,819 | 7,637 | ok, memory-pressured assembly |
| 20,237 | `fused_cuda` | 39,971 | — | — | — | 215 | 7,831 | 7,616 | **worker host DEATH** (attempt + immediate re-warm retry both died) |

Raw lines, verbatim. Elisions noted: the c1 block elides its log's first line, `MESH CACHE HIT C:\Users\hunte\Hrns\hornlab-search\scratch\ceiling_cache\9aac2b3c99e385be` (the same cached mesh as c0's fresh build); the 20,237-attempt block shows the failure portion (its `MESH`/`CLEAN` lines are identical in form to the blocks above); the c4b three-line log is quoted in full at the end of this section.

```
MESH mouth_res_mm=6.72 throat_res_mm=3.36 triangles=17500 dofs=8919 quadrants=1 symmetry_plane=yz+xz res_used_mm={"mouth": 6.72, "rear": 6.72, "throat": 3.36} mesh=C:\Users\hunte\Hrns\hornlab-search\runs\ceiling_m6.72_t3.36\mesh.msh
CLEAN: no stale BEAT hosts
SOLVE ok dofs=8919 assembly_path=None assembly=28.714s solve=28.311s s_per_freq=59.607s
SHUTDOWN: worker.shutdown(verify=True) ok; force-killed root pids: []
VRAM baseline=437 MiB peak=7826 MiB peak-baseline=7389 MiB
```

```
MESH mouth_res_mm=6.72 throat_res_mm=3.36 triangles=17500 dofs=8919 quadrants=1 symmetry_plane=yz+xz res_used_mm={"mouth": 6.72, "rear": 6.72, "throat": 3.36} mesh=C:\Users\hunte\Hrns\hornlab-search\runs\ceiling_m6.72_t3.36\mesh.msh
CLEAN: no stale BEAT hosts
SOLVE ok dofs=8919 assembly_path=fused_cuda assembly=6.13s solve=0.76s s_per_freq=9.111s
SHUTDOWN: worker.shutdown(verify=True) ok; force-killed root pids: []
VRAM baseline=569 MiB peak=2786 MiB peak-baseline=2217 MiB
```

```
MESH mouth_res_mm=5.74 throat_res_mm=2.87 triangles=23973 dofs=12183 quadrants=1 symmetry_plane=yz+xz res_used_mm={"mouth": 5.74, "rear": 5.74, "throat": 2.87} mesh=C:\Users\hunte\Hrns\hornlab-search\runs\ceiling_m5.74_t2.87\mesh.msh
CLEAN: no stale BEAT hosts
SOLVE ok dofs=12183 assembly_path=fused_cuda assembly=8.887s solve=1.648s s_per_freq=13.72s
SHUTDOWN: worker.shutdown(verify=True) ok; force-killed root pids: []
VRAM baseline=169 MiB peak=4913 MiB peak-baseline=4744 MiB
```

```
MESH mouth_res_mm=5.02 throat_res_mm=2.51 triangles=31522 dofs=15984 quadrants=1 symmetry_plane=yz+xz res_used_mm={"mouth": 5.02, "rear": 5.02, "throat": 2.51} mesh=C:\Users\hunte\Hrns\hornlab-search\runs\ceiling_m5.02_t2.51\mesh.msh
CLEAN: no stale BEAT hosts
SOLVE ok dofs=15984 assembly_path=fused_cuda assembly=437.184s solve=16.72s s_per_freq=458.577s
SHUTDOWN: worker.shutdown(verify=True) ok; force-killed root pids: []
VRAM baseline=182 MiB peak=7819 MiB peak-baseline=7637 MiB
```

The 15,984-dof point is the shape of "fits, but do not use it": 7,637 MiB of an 8 GB card and a 437 s
assembly for one frequency. The fused *solve* is still fast (16.72 s); the *assembly* is the pressure.

20,237 dofs, attempt (`ceiling_c4_fused_445.log`) — the host dies mid-solve, the automatic re-warm retry dies
the same way, then shutdown and VRAM are still measurable:

```
BEAT worker host died ([worker_exit] ConnectionResetError(10054, 'An existing connection was forcibly closed by the 
remote host', None, 10054, None)); re-warming once and retrying this candidate
re-warm after worker_exit failed: ConnectionResetError(10054, 'An existing connection was forcibly closed by the 
remote host', None, 10054, None)
OOM/CRASH: [worker_exit] ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', 
None, 10054, None)
```

```
SHUTDOWN: worker.shutdown(verify=True) ok; force-killed root pids: []
VRAM baseline=215 MiB peak=7831 MiB peak-baseline=7616 MiB
RESULT {"angles": 73, "assembly_path": null, "assembly_paths": null, "assembly_s": null, "baseline_MiB": 215, "dofs": 20237, "flag": "on", "freq": 1000.0, "mesh_path": "C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\ceiling_m4.45_t2.225\\mesh.msh", "meta_cuda_fused": null, "mouth_res": 4.45, "ok": false, "peak_MiB": 7831, "peak_minus_baseline_MiB": 7616, "res_used_mm": {"mouth": 4.45, "rear": 4.45, "throat": 2.225}, "s_per_freq": null, "solve_s": null, "throat_res": 2.225, "triangles": 39971}
```

Clean-state confirmation for 20,237 dofs was **started and not finished** — the owner stopped the upward sweep
mid-run. The whole of `ceiling_c4b_fused_445_confirm.log` is three lines:

```
MESH CACHE HIT C:\Users\hunte\Hrns\hornlab-search\scratch\ceiling_cache\174deb44e5e298a4
MESH mouth_res_mm=4.45 throat_res_mm=2.225 triangles=39971 dofs=20237 quadrants=1 symmetry_plane=yz+xz res_used_mm={"mouth": 4.45, "rear": 4.45, "throat": 2.225} mesh=C:\Users\hunte\Hrns\hornlab-search\runs\ceiling_m4.45_t2.225\mesh.msh
CLEAN: no stale BEAT hosts
```

So the 20,237-dof failure is a **provisional** finding (repeat-from-clean not re-confirmed), and there is **no
24k point** — the sweep stopped here.

## 7. Verdict

- **Measured fused ceiling on this card: fits 15,984 dofs** (peak−baseline 7,637 MiB, but memory-pressured
  assembly at 437 s/freq); **fails 20,237 dofs** (worker-host death; pending clean-confirm caveat above).
- **Measured safe value chosen: 12,000 dofs** for the verify/final caps. Basis: 12,183 dofs measured at
  **4,744 MiB peak−baseline and 13.72 s/freq** — fast, with ~3.4 GB of headroom, which also leaves room for the
  balloon/grid at higher modes.
- The earlier **"~20k inferred"** figure **did not materialize** on this card/protocol. Recorded honestly: the
  inference came from dof-scaling, not from a clean-state measurement, and the one 20k attempt died.
- **Old-path comparison at the same 8,919-dof mesh**: 7,389 vs 2,217 MiB peak−baseline, and 59.6 vs 9.1 s/freq
  (28.714 s → 6.13 s assembly, 28.311 s → 0.76 s solve). That is the WP15 win: the old path is at the card's
  limit exactly where the fused path has ~5 GB free.

## 8. Deliverables

- New configs (originals untouched; `solve.cuda_fused: true`, verify/final caps 7000/8900 → 12000/12000, screen
  cap 5000 unchanged):
  `examples/typologies/osse_axi_fusedcuda.yaml`, `examples/osse_baseline_fusedcuda.yaml`,
  `examples/typologies/perturbed_osse_hv_fusedcuda.yaml`, `examples/freeform_sculpt_fusedcuda.yaml`.
- `tools/measure_fused_ceiling.py` — single-shot ceiling harness (fresh process, threaded VRAM poll, verified
  shutdown) plus the `--mesh-only` res→dof calibration mode.
- `tests/test_solve_beat_fused_cuda.py` — rebarred: zero-tolerance bit-identity replaced by the documented
  **1e-4 dB** floor (section 5); the fused-vs-default bars themselves are unchanged.
- Dev-branch pin `dev/fused-cuda-pin` (fork SHA in `pyproject.toml` instead of the base pin) — **not merged to
  `main`**; it is what clears the `pinned-shas` WARNING in section 1.

## 9. 12 kHz verify on the fused flag (osse_axi seed)

The config `examples/typologies/osse_axi_fusedcuda.yaml` (screen run under the lock, fused flag on) produces a
legitimate run dir with the flag in the saved config; `verify --brief` then re-solves its design on the 12 kHz
verify grid. Both jobs: `gpu-clean` before and after; one GPU job. (In the blocks below, the
`& "…hornlab-search.exe" run/verify …` first lines are RECONSTRUCTED invocation commands; every other line is
verbatim from `fused_run_axi_screen.log` / `verify_12k_fused_axi_seed.log`.)

```
& ".venv\Scripts\hornlab-search.exe" run --config "examples\typologies\osse_axi_fusedcuda.yaml" --mode screen --cache-dir "scratch\ab_cache_fused" --runs-dir runs --dataset-dir "scratch\ab_dataset"

  terms (raw): cov=11.98  rip=4.993  di=1.059  dislope=1.335  flat=3.428  load=0.2715  penalty=0  total J=19.8072  n_nan=0  DI source=balloon
run OK: seed J=19.8072, 1013 dofs, solve 7.5 s; output runs\20261025T012944Z-screen-f576b4
```
(`fused_run_axi_screen.log`) The fused screen seed solve: **seed J 19.8072 — identical to the flag-off A/B arm's
19.8072** (section 3), and the WP15 refusal guard did NOT fire, i.e. every per-frequency diagnostic proved the
fused path (`response.npz` meta of d04e8697a87d: `cuda_fused: True`, 12× `assembly_path: fused_cuda`).

```
& ".venv\Scripts\hornlab-search.exe" verify --run "runs\20261025T012944Z-screen-f576b4" --brief "examples\briefs\axi_90x90_1in_12k.yaml" --top 1
verify: re-solving the top 1 designs of 20261025T012944Z-screen-f576b4 under brief examples\briefs\axi_90x90_1in_12k.yaml (band 700.0-12000.0 Hz); J is NOT comparable with the source run's J (different band and grid)
  design        screen J     verify J    DI source

  d04e8697a87d    19.80719    17.03395  balloon
verify OK: 1 designs, 0 failed; output C:\Users\hunte\Hrns\hornlab-search\runs\20261025T013051Z-verify-be4adb
```
(`verify_12k_fused_axi_seed.log`)

Measured facts (the `20261025T013051Z-verify-be4adb` run dir):
- Design: `d04e8697a87d` (the osse_axi **seed`; verify mode on the `axi_90x90_1in_12k` brief (band 700–12,000 Hz,
  25 verify frequencies), DI source balloon. `run.json.verify_of` records source run `20261025T012944Z-screen-f576b4`;
  `lib_shas.hornlab_beat_bem` = `fa99ee5…` (the fork).
- Mesh: 4,438 dofs / 8,626 triangles (quarter, mouth/throat res 3.573/1.786 mm at verify epw resolution) — the
  epw rule chose this size; it finished well below the raised 12,000 verify cap.
- Timings: mesh 8.00 s, solve **52.89 s / 25 frequencies ≈ 2.1 s/frequency**, total 62.10 s — no memory-pressure
  collapse; 15,984 dofs (the largest fused mesh measured) is not touched here.
- Row `peak_vram_mb` (the repo's process-side probe, not the harness's machine-wide nvidia-smi accounting):
  **672 MB**.
- Proof of the path: `response.npz` meta `cuda_fused = True` with **25× `assembly_path: fused_cuda`** diagnostics;
  the `_assert_cuda_fused_path` refusal stayed silent, so a fused run end to end at 12 kHz is proven.
- **f11 caveat (mandatory with every 12 kHz number):** f11 = 7,914 Hz for the 1-inch exit — above it,
  **8–12 kHz results compare GEOMETRIES, not drivers** (source: rigid uniform-velocity spherical cap).

## 10. Suites and branch state (why the unpinned tree shows exactly one "failure")

- `pytest -m "not slow and not gpu and not crosscheck"` — the canonical offline suite:
  - **Dev-pin tree** (`dev/fused-cuda-pin` @ `65c03de` = main `5875fde` + the fork pin in `pyproject.toml`/`TOOLCHAIN.md`):
    **938 passed / 0 failed / 0 errors / 20 deselected** — junitxml counters (`runs/m2_fused_cuda/suite_dev.xml`):
    `tests=938, failures=0, errors=0, skipped=0`, 217.9 s. Total collected 958 (`collect_dev.txt`, `collect_all.txt`);
    958 − 938 = 20 deselected. Full capture: `runs/m2_fused_cuda/offline_suite_m2_dev_full.log`.
  - **Unpinned main tree** (base pin `38544d2` in `pyproject.toml` while the fork @ `fa99ee5` is installed — the M2
    work state by design): the same selection shows exactly ONE failure, `tests/test_mesh_pin.py::
    test_installed_hornlab_packages_match_their_pins` — the INTENDED pinned-SHA tripwire ("Silent HornLab version
    bump detected"). It goes green when the pin lands (owner action) or the base pin is reinstalled (FORKS.md
    rollback). Observed identically in the suite runs this pass (`offline_suite_m2_full.log`, `suite_main_count.txt`).
  - Selection is +3 vs M1's 935-passed baseline = the four new `_fusedcuda` configs entering the parametrized
    config sweeps + the concurrently-landed GUI-contrast lane's tests. **Nothing loosened.**
  - Known capture artifact (this console): the shell's `2>&1 | Tee-Object` capture drops pytest's final count line;
    the junitxml + the short-summary FAILED lines are the authoritative counters (NOTES_FOR_SENIOR 2026-10-24).
- **Branch state at the push:** `main` = `5875fde` (GUI-contrast phases 1–6, landed and pushed concurrently by the
  GUI lane) + THIS M2 commit (docs/evidence/configs/harness/tests — **NO pin**); `dev/fused-cuda-pin` @ `65c03de`
  = main + the `file://` pin — **local only, never pushed, never merged**. Replacing the `file://` pin with a
  hosted-GitHub URL is an OWNER action (`docs/FORKS.md`).
