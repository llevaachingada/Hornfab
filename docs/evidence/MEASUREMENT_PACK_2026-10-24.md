# M3 measurement pack on stored designs: distance, balloon, source motion, rear shell, band split (2026-10-24)

Scope: the M3 GPU measurement pass of `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md`
WP5(a)(b)(c), WP7 and WP8, run on **existing stored designs** — no search, no new brief, no default
flipped, no config edited. Every number below comes from a job log or a job JSON under
`runs/m3_*` (gitignored); the console blocks are copied byte-for-byte from those logs (the
PowerShell `Tee-Object` logs are UTF-16, re-read with `Get-Content -Encoding Unicode`).

Subjects (all stored, unchanged): AXI `59f57bc457cb` (`osse_axi` best), HV `fed761193da7`
(`perturbed_osse_hv` best), RO `47e1259ad615` (`rosse_baseline` best). Stored 12 kHz verify
baselines: `runs/20261023T195300Z-verify-bdae12` (6049 dofs), `runs/20261023T200104Z-verify-4fdec8`
(4540 dofs), `runs/20261023T200406Z-verify-602ef1` (4729 dofs).

> **Physics caveat (printed with every 12 kHz number).** The source is a rigid uniform-velocity
> spherical cap. Above the throat's first cross mode (**f11 = 7,914 Hz** for the 1-inch exit,
> `scalars.f11_hz = 7914.281563679812` in every 12 kHz record here) a real compression driver is not
> a uniform cap, so **8–12 kHz results compare GEOMETRIES, not drivers**. Free-standing horn, rigid
> lossless walls, 25 log-spaced frequencies 300–12,000 Hz, observation at **2.0 m** unless stated.
> — `docs/evidence/HF12K_VERIFY_2026-10-23.md:6-9`, `docs/evidence/FUSED_CUDA_2026-10-24.md:9-14`.

## 0. Protocol, provenance and per-job bookkeeping

One GPU job per fresh process; before every job `Get-Process julia` (nothing to kill: the tool
prints `CLEAN: no stale BEAT hosts`), then `nvidia-smi --query-gpu=memory.used` = **PRE baseline**;
the tool records its own in-process **baseline**, polls `nvidia-smi` from a daemon thread for
**peak**, and ends with `worker.shutdown(verify=True)`; after every job `hornlab-search gpu-clean`
and another `nvidia-smi` read. **Every job's fresh cache dir** is a new `scratch/m3_*` directory
(the mesh/solve caches are not keyed by library SHA, so an old entry would serve a stale response).
No two GPU jobs ran at once.

New solves use the installed fork (`hornlab_beat_bem` **fa99ee5** — `direct_url.json`
`commit_id fa99ee594087507c2808b9e7db09b38d8d4dcc20`), via the **fused** path (`solve.cuda_fused:
true`) for every 12 kHz job (VRAM headroom) and the **flag-off** path for the two WP7 screen jobs
(small mesh, and the flag-off fork path is the M2-proven identical-to-`38544d2` path). The stored
baselines are from beat `38544d2`; see section 7 for the measured A/B distance between a stored
baseline and its fresh re-solve.

Tool: `tools/m3_measurement_pack.py` (`solve` / `traces` / `compare` subcommands). Each job
reconstructs the design from `designs/<hash>/design.json` (`Design(family, params)`, hash asserted),
re-loads the stored run's `config.yaml` through the **normal config validator** with the override
applied, and runs the normal `search.evaluate.evaluate` path (mesh cache, solve cache,
`metrics_from_response`, objective, ndjson row, dataset record).

| job | topic | invocation (tool args after `tools/m3_measurement_pack.py`) | log | JSON | PRE MiB | baseline MiB | peak MiB | dofs | solve/wall s |
|---|---|---|---|---|---|---|---|---|---|
| AXI traces | WP5(a) | `traces --run-dir runs/20261023T195300Z-verify-bdae12 --design-hash 59f57bc457cb --mode verify --cuda-fused --balloon-from runs/20261023T025720Z-screen-2002c3/designs/59f57bc457cb/response.npz --cache-dir scratch/m3_wp5a_axi_cache` | `runs/m3_wp5a/axi.log` | `runs/m3_wp5a/axi.json` | 463 | 463 | 1774 | 6049 | 58.87 solve (+6.83 mesh) |
| HV traces | WP5(a) | same, `--run-dir runs/20261023T200104Z-verify-4fdec8 --design-hash fed761193da7 --balloon-from runs/20261023T043339Z-screen-d74ea3/designs/fed761193da7/response.npz --cache-dir scratch/m3_wp5a_hv_cache` | `runs/m3_wp5a/hv.log` | `runs/m3_wp5a/hv.json` | 463 | 463 | 1262 | 4540 | 35.39 solve (+10.46 mesh) |
| RO traces | WP5(a) | same, `--run-dir runs/20261023T200406Z-verify-602ef1 --design-hash 47e1259ad615 --balloon-from runs/20261023T055352Z-screen-483828/designs/47e1259ad615/response.npz --cache-dir scratch/m3_wp5a_ro_cache` | `runs/m3_wp5a/ro.log` | `runs/m3_wp5a/ro.json` | 463 | 463 | 1326 | 4729 | 38.62 solve (+1.21 mesh) |
| AXI b1024 | WP5(b) | `solve --run-dir runs/20261023T195300Z-verify-bdae12 --design-hash 59f57bc457cb --mode verify --cuda-fused --set solve.balloon_points_verify=1024 --cache-dir scratch/m3_wp5b_axi_b1024_cache` | `runs/m3_wp5b/axi_b1024.log` | `runs/m3_wp5b/axi_b1024.json` | 463 | 463 | 1774 | 6049 | 63.68 |
| AXI b2592 | WP5(b) | same, `=2592`, `scratch/m3_wp5b_axi_b2592_cache` | `runs/m3_wp5b/axi_b2592.log` | `runs/m3_wp5b/axi_b2592.json` | 463 | 463 | 1774 | 6049 | 64.40 |
| HV b1024 | WP5(b) | `--run-dir runs/20261023T200104Z-verify-4fdec8 --design-hash fed761193da7 --set solve.balloon_points_verify=1024` | `runs/m3_wp5b/hv_b1024.log` | `runs/m3_wp5b/hv_b1024.json` | 463 | 463 | 1262 | 4540 | 47.08 |
| HV b2592 | WP5(b) | same, `=2592` | `runs/m3_wp5b/hv_b2592.log` | `runs/m3_wp5b/hv_b2592.json` | 463 | 463 | 1262 | 4540 | 48.10 |
| RO b1024 | WP5(b) | `--run-dir runs/20261023T200406Z-verify-602ef1 --design-hash 47e1259ad615 --set solve.balloon_points_verify=1024` | `runs/m3_wp5b/ro_b1024.log` | `runs/m3_wp5b/ro_b1024.json` | 463 | 463 | 1326 | 4729 | 39.92 |
| RO b2592 | WP5(b) | same, `=2592` | `runs/m3_wp5b/ro_b2592.log` | `runs/m3_wp5b/ro_b2592.json` | 463 | 463 | 1326 | 4729 | 40.55 |
| AXI axial | WP5(c) | `--run-dir runs/20261023T195300Z-verify-bdae12 --design-hash 59f57bc457cb --set solve.source_motion=axial` | `runs/m3_wp5c/axi_axial.log` | `runs/m3_wp5c/axi_axial.json` | 463 | 463 | 1783 | 6049 | 69.54 |
| HV axial | WP5(c) | `--run-dir runs/20261023T200104Z-verify-4fdec8 --design-hash fed761193da7 --set solve.source_motion=axial` | `runs/m3_wp5c/hv_axial.log` | `runs/m3_wp5c/hv_axial.json` | 460 | 460 | 1256 | 4540 | 55.84 |
| RO axial | WP5(c) | `--run-dir runs/20261023T200406Z-verify-602ef1 --design-hash 47e1259ad615 --set solve.source_motion=axial` | `runs/m3_wp5c/ro_axial.log` | `runs/m3_wp5c/ro_axial.json` | 457 | 457 | 1320 | 4729 | 42.68 |
| AXI rear 1.5 | WP7 | `--run-dir runs/20261023T025720Z-screen-2002c3 --design-hash 59f57bc457cb --mode screen --no-cuda-fused --set mesh.rear_res_factor=1.5` | `runs/m3_wp7/axi_rear1.5.log` | `runs/m3_wp7/axi_rear1.5.json` | 457 | 457 | 880 | 1135 | 7.17 |
| AXI rear 2.0 | WP7 | same, `=2.0` | `runs/m3_wp7/axi_rear2.0.log` | `runs/m3_wp7/axi_rear2.0.json` | 457 | 457 | 848 | 1060 | 7.03 |
| AXI band | WP8 | `--run-dir runs/20261023T195300Z-verify-bdae12 --design-hash 59f57bc457cb --mode verify --cuda-fused --set mesh.band_split.edges_hz=[3000,6000]` | `runs/m3_wp8/axi_band.log` | `runs/m3_wp8/axi_band.json` | 457 | 457 | 1814 | 6049 (max band) | 29.64 |
| HV band | WP8 | `--run-dir runs/20261023T200104Z-verify-4fdec8 --design-hash fed761193da7 --mode verify --cuda-fused --set mesh.band_split.edges_hz=[3000,6000]` | `runs/m3_wp8/hv_band.log` | `runs/m3_wp8/hv_band.json` | 555 | 641 | 1180 | 4540 (max band) | 33.82 |

Every job's `SPEC` line records the exact spec; e.g. (`runs/m3_wp5b/axi_b1024.log`):

```
SPEC mode=verify backend=beat_cuda cuda_fused=True source_motion=normal rear_res_factor=1 band_split=None distance_m=2 angles=73 balloon_requested=1024 balloon_grid=[23, 45]
MESH dofs=6049 triangles=11810 res_mm={'throat': 1.7864583333333333, 'mouth': 3.5729166666666665, 'rear': 3.5729166666666665} mesh_seconds=6.00 solve_seconds=56.91 wall_seconds=63.68
J 9.437805  terms={"cov": 3.144584109122419, "di": 0.5229737535282514, "di_estimated": 0.0, "dislope": 0.030211781462243542, "flat": 3.9742484996958156, "load": 0.20182058735924668, "n_in_band": 19, "n_nan": 0, "penalty": 0.0, "rip": 4.033188363012543, "total": 9.43780503245209}
META balloon_grid=[23, 45] source_motion=normal mesh_policy=None cuda_fused=True assembly_paths=['fused_cuda']
SCALARS f11_hz=7914.3 di_mean=9.5705 bw_h_mean=88.226 bw_v_mean=88.223 ripple_mean=2.0166 flatness=3.9742
VRAM baseline=463 MiB peak=1774 MiB peak-baseline=1311 MiB
```

(That is a fresh-process, fresh-cache fused re-solve of the stored spec: **J 9.437805 vs stored
9.437804**, DI within 8.2e-5 dB — the reconstruction is exact.)

**GPU wall.** Sum of the GPU-bearing job walls printed by the tool: **728 s ≈ 12.1 min** across
16 successful jobs plus one discarded AXI band attempt (27.12 s, section 7.2). The WP5(a) jobs add
~330 s of **CPU** BEMPP trace evaluation each (not GPU).

**MISSING / not measured here (stated, not invented).**
- Per-band **mesh** seconds are not recorded by the pipeline (`status.json` holds only the last
  band's mesh seconds), so WP8 reports total wall + the summed solve timings from `Response.meta`.
- The three WP5(a) jobs do not print a whole-process wall (only mesh + solve seconds and the
  per-radius BEMPP evaluation seconds, `axi`: 120.9/106.9/107.1 s for r=2/10/50 m).
- Offline suite counters (`--junitxml`): `runs/m3_carryover/suite.xml` 944 tests / 0 errors / 1 failure (the expected `test_mesh_pin` tripwire) / 0 skipped at the carry-over commit; `runs/m3_code/suite_final.xml` 968 tests / 0 errors / 1 failure (the same tripwire) / 0 skipped at the FINAL working-tree code state (after the Oracle-pass fixes; the focused post-fix subset `runs/m3_code/suite_oracle_fixes.xml`: 68 / 0 / 0 / 0). The row-echo change is additionally covered by the focused subset: `tests/test_config.py` + `tests/test_search_evaluate.py` + `tests/test_mesh_sizing.py` = 68 collected, 68 passed (`runs/m3_code/suite_oracle_fixes.xml`); earlier row-echo log: `runs/m3_code/offline_tests_after_row_echo.log`.

## 1. WP5(a) — distance sensitivity from ONE traced solve per design

Method (`traces` subcommand): one `BeatBackend.solve_traced` at the stored 12 kHz verify spec
(25 freqs, 73 angles, ball 1024 → the direct response), `package_traces`, then **offline**
`field_from_traces` on a single combined point set per radius (H cut + V cut at 73 angles +
`r × balloon_dirs` on the stored screen **16×32** grid) and a `Response` per radius with
`meta['balloon_grid'] = [16, 32]`, so `metrics_from_response` runs the sin(theta)-weighted DI path.
No `distance_m` re-solve was needed: **the traces answer the question**.

Validation, same job (`runs/m3_wp5a/axi.log`):

```
TRACED solve dofs=6049 triangles=11810 solve_seconds=58.87 traces pressure=(25, 6049) neumann=(25, 11810)
VALIDATION r=2 direct-solve vs trace-evaluated (same spec, different field path)
  max|d spl_h|=0.000128236 dB  max|d DI|=0.154522 dB  max|d bw_h|=0.000129462 deg
```

The cuts reproduce the solver's own 2 m response to **1.3e-4 dB** and beamwidth to **1.3e-4 deg**.
The DI line is **not** an error: the direct response carries the 1035-point balloon while the
trace evaluation uses the 512-point grid; 0.154522 dB is exactly the 512→1035 AXI DI change
measured independently in WP5(b) (0.1545 dB at 7567 Hz). HV: 2.4e-4 dB cuts, 0.1110 dB = the
WP5(b) 512→1035 HV maximum. RO: 2.0e-4 dB cuts, 0.0786 dB = the WP5(b) RO maximum.

### 1.1 Why the pattern moves with r (physics check, `runs/m3_wp5a/axi_pattern_probe.log`)

A dense H-cut probe at 2/10/50/1000 m (same traces, CPU only) shows the on-axis level is **not**
exactly 1/r:

```
ON-AXIS LEVEL vs 1/r (spreading must be 20*log10(r2/r1))
  f=  475.8 Hz  r=2:   12.678 (d=  +0.000)  r=10:   -1.829 (d= -14.508)  r=50:  -15.913 (d= -28.592)  r=1000:  -41.959 (d= -54.637)
  f= 1026.0 Hz  r=2:   19.109 (d=  +0.000)  r=10:    4.809 (d= -14.300)  r=50:   -9.237 (d= -28.346)  r=1000:  -35.274 (d= -54.382)
  f= 3008.9 Hz  r=2:   17.420 (d=  +0.000)  r=10:    4.283 (d= -13.137)  r=50:   -9.526 (d= -26.946)  r=1000:  -35.507 (d= -52.926)
  f= 7567.0 Hz  r=2:   13.118 (d=  +0.000)  r=10:   -2.075 (d= -15.193)  r=50:  -16.253 (d= -29.371)  r=1000:  -42.317 (d= -55.435)
```

20·log10(10) = 13.979 dB and 20·log10(50) = 27.959 dB: the measured 2 m→50 m spreading is
26.95–29.37 dB, i.e. up to **1.4 dB away** from a point source at the origin. The 50 m and 1000 m
deviations are the same to 0.04 dB (+1.01 vs +1.05 dB at 3 kHz), i.e. the field **has converged
by 50 m** and what remains is a fixed effective-source offset, not a diverging near field. At
7567 Hz the aperture Fresnel distance D²/λ ≈ 2 m (D = 0.335 m mouth), so 2 m is genuinely inside
the near field there; at the low end the sphere centred on the **throat** sits ~0.1–0.2 m behind
the acoustic centre, which shows up as a 0.3–1.4 dB level deviation from 1/r and a several-degree
pattern difference between 2 m and 50 m, both of which saturate as r grows. The L/R asymmetry of
the H cut is **0.000000 dB** at every radius (the axisymmetric horn), so the symmetry/image
handling is not the cause.

**Reading the beamwidth deltas below:** at low frequency a handful of frequencies sit within
~1 dB of the −6 dB level at ±90°, so a sub-dB pattern change toggles the −6 dB crossing over a
large angle (e.g. AXI 475.75 Hz: 90° level −7.09 dB at 2 m vs −6.28 dB relative at 50 m → the
crossing moves from ±77° to ±86°). The DI and the on-axis level deltas are the more physical
numbers; all three are reported.

### 1.2 Tables (absolute values at 2/10/50 m and deltas vs 2 m)

### WP5(a) tables: absolute values at 2 / 10 / 50 m and the deltas vs 2 m

#### AXI (59f57bc457cb, 6049 dofs, traced solve 58.87 s)

| f (Hz) | bw_H 2m | bw_H 10m | bw_H 50m | dBW_H 2->10 | dBW_H 2->50 | bw_V 2m | bw_V 50m | dBW_V 2->10 | dBW_V 2->50 | DI 2m | DI 10m | DI 50m | dDI 2->10 | dDI 2->50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 300.00 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 2.425 | 1.780 | 1.650 | -0.645 | -0.774 |
| 349.84 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 3.058 | 2.449 | 2.326 | -0.609 | -0.731 |
| 407.97 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 3.869 | 3.305 | 3.191 | -0.564 | -0.678 |
| 475.75 | 154.198 | 168.861 | 172.381 | +14.663 | +18.183 | 154.198 | 172.381 | +14.663 | +18.183 | 4.815 | 4.300 | 4.195 | -0.516 | -0.620 |
| 554.79 | 134.439 | 143.457 | 145.396 | +9.018 | +10.957 | 134.439 | 145.396 | +9.018 | +10.957 | 5.801 | 5.332 | 5.237 | -0.469 | -0.564 |
| 646.97 | 121.860 | 129.063 | 130.608 | +7.203 | +8.748 | 121.860 | 130.608 | +7.203 | +8.748 | 6.736 | 6.307 | 6.220 | -0.428 | -0.516 |
| 754.46 | 111.209 | 117.181 | 118.468 | +5.972 | +7.259 | 111.209 | 118.468 | +5.972 | +7.259 | 7.597 | 7.204 | 7.124 | -0.393 | -0.474 |
| 879.81 | 100.424 | 105.216 | 106.250 | +4.792 | +5.826 | 100.424 | 106.250 | +4.792 | +5.827 | 8.444 | 8.086 | 8.011 | -0.359 | -0.433 |
| 1025.99 | 89.265 | 92.898 | 93.697 | +3.633 | +4.432 | 89.265 | 93.697 | +3.633 | +4.432 | 9.360 | 9.041 | 8.974 | -0.319 | -0.387 |
| 1196.45 | 78.556 | 81.176 | 81.759 | +2.620 | +3.203 | 78.556 | 81.759 | +2.620 | +3.203 | 10.364 | 10.096 | 10.039 | -0.268 | -0.325 |
| 1395.23 | 69.300 | 70.976 | 71.374 | +1.676 | +2.074 | 69.300 | 71.374 | +1.676 | +2.074 | 11.287 | 11.096 | 11.052 | -0.191 | -0.235 |
| 1627.04 | 63.293 | 63.639 | 63.806 | +0.346 | +0.512 | 63.293 | 63.806 | +0.346 | +0.512 | 11.667 | 11.604 | 11.584 | -0.063 | -0.084 |
| 1897.37 | 69.655 | 65.235 | 64.662 | -4.420 | -4.993 | 69.654 | 64.662 | -4.420 | -4.992 | 11.195 | 11.337 | 11.353 | +0.142 | +0.159 |
| 2212.60 | 82.209 | 77.673 | 76.681 | -4.536 | -5.528 | 82.209 | 76.681 | -4.536 | -5.528 | 10.775 | 11.138 | 11.195 | +0.363 | +0.419 |
| 2580.22 | 85.809 | 82.303 | 81.679 | -3.507 | -4.130 | 85.810 | 81.680 | -3.507 | -4.130 | 9.806 | 10.512 | 10.631 | +0.705 | +0.825 |
| 3008.91 | 105.105 | 96.447 | 94.584 | -8.658 | -10.520 | 105.107 | 94.587 | -8.656 | -10.519 | 7.313 | 8.168 | 8.341 | +0.855 | +1.028 |
| 3508.82 | 104.808 | 104.532 | 104.142 | -0.276 | -0.667 | 104.807 | 104.141 | -0.276 | -0.666 | 6.928 | 7.190 | 7.307 | +0.263 | +0.379 |
| 4091.79 | 88.592 | 92.449 | 93.135 | +3.857 | +4.543 | 88.590 | 93.134 | +3.857 | +4.543 | 9.480 | 8.692 | 8.554 | -0.789 | -0.926 |
| 4771.62 | 86.076 | 87.403 | 87.913 | +1.327 | +1.837 | 86.073 | 87.910 | +1.327 | +1.837 | 10.750 | 10.300 | 10.174 | -0.450 | -0.576 |
| 5564.41 | 89.135 | 85.780 | 85.573 | -3.355 | -3.562 | 89.130 | 85.569 | -3.355 | -3.562 | 9.807 | 10.404 | 10.461 | +0.597 | +0.654 |
| 6488.90 | 100.463 | 96.390 | 95.601 | -4.072 | -4.862 | 100.458 | 95.601 | -4.068 | -4.857 | 7.331 | 8.337 | 8.579 | +1.005 | +1.248 |
| 7567.00 | 90.474 | 95.693 | 96.514 | +5.218 | +6.039 | 90.475 | 96.515 | +5.219 | +6.040 | 10.018 | 8.645 | 8.412 | -1.372 | -1.606 |
| 8824.22 | 88.080 | 83.804 | 83.769 | -4.275 | -4.311 | 88.064 | 83.753 | -4.278 | -4.311 | 10.289 | 10.690 | 10.677 | +0.402 | +0.389 |
| 10290.32 | 92.643 | 92.323 | 91.311 | -0.320 | -1.332 | 92.634 | 91.303 | -0.322 | -1.331 | 8.999 | 9.146 | 9.351 | +0.147 | +0.351 |
| 12000.00 | 81.206 | 81.011 | 82.009 | -0.196 | +0.802 | 81.184 | 81.991 | -0.192 | +0.806 | 11.157 | 11.004 | 10.825 | -0.153 | -0.333 |
- MAX |delta| 2->50 m, all 300-12000 Hz: bw_h_deg 18.1828 (at 475.75 Hz); bw_v_deg 18.1829 (at 475.75 Hz); di_db 1.6057 (at 7567 Hz)
- MAX |delta| 2->50 m, in-band 700-12000 Hz: bw_h_deg 10.5205 (at 3008.91 Hz); bw_v_deg 10.5194 (at 3008.91 Hz); di_db 1.6057 (at 7567 Hz)

#### HV (fed761193da7, 4540 dofs, traced solve 35.39 s)

| f (Hz) | bw_H 2m | bw_H 10m | bw_H 50m | dBW_H 2->10 | dBW_H 2->50 | bw_V 2m | bw_V 50m | dBW_V 2->10 | dBW_V 2->50 | DI 2m | DI 10m | DI 50m | dDI 2->10 | dDI 2->50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 300.00 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 2.970 | 2.234 | 2.087 | -0.736 | -0.883 |
| 349.84 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 3.718 | 3.028 | 2.890 | -0.689 | -0.828 |
| 407.97 | 155.703 | 178.736 | 180.000 | +23.033 | +24.297 | 167.115 | 180.000 | +12.885 | +12.885 | 4.618 | 3.982 | 3.854 | -0.636 | -0.764 |
| 475.75 | 131.684 | 143.283 | 145.862 | +11.599 | +14.179 | 142.938 | 158.546 | +12.784 | +15.608 | 5.593 | 5.011 | 4.893 | -0.582 | -0.700 |
| 554.79 | 116.682 | 125.220 | 127.105 | +8.538 | +10.423 | 129.761 | 141.753 | +9.878 | +11.993 | 6.549 | 6.016 | 5.907 | -0.533 | -0.642 |
| 646.97 | 104.464 | 110.990 | 112.440 | +6.526 | +7.976 | 119.896 | 130.175 | +8.454 | +10.279 | 7.442 | 6.952 | 6.852 | -0.490 | -0.590 |
| 754.46 | 93.014 | 97.764 | 98.841 | +4.750 | +5.827 | 110.322 | 119.136 | +7.244 | +8.814 | 8.303 | 7.856 | 7.763 | -0.447 | -0.539 |
| 879.81 | 82.242 | 85.379 | 86.112 | +3.137 | +3.870 | 99.889 | 107.131 | +5.952 | +7.242 | 9.198 | 8.802 | 8.718 | -0.397 | -0.480 |
| 1025.99 | 73.281 | 74.839 | 75.267 | +1.558 | +1.985 | 88.891 | 94.613 | +4.690 | +5.723 | 10.125 | 9.798 | 9.727 | -0.327 | -0.398 |
| 1196.45 | 69.805 | 68.937 | 68.943 | -0.869 | -0.862 | 77.947 | 82.326 | +3.585 | +4.379 | 10.847 | 10.627 | 10.576 | -0.219 | -0.271 |
| 1395.23 | 84.146 | 78.031 | 76.884 | -6.115 | -7.262 | 67.519 | 70.550 | +2.469 | +3.031 | 11.023 | 10.956 | 10.932 | -0.067 | -0.091 |
| 1627.04 | 91.333 | 88.594 | 87.956 | -2.739 | -3.377 | 61.787 | 62.710 | +0.670 | +0.923 | 11.060 | 11.156 | 11.162 | +0.095 | +0.102 |
| 1897.37 | 91.334 | 89.694 | 89.418 | -1.641 | -1.916 | 66.499 | 62.470 | -3.604 | -4.029 | 10.740 | 11.051 | 11.099 | +0.311 | +0.359 |
| 2212.60 | 98.693 | 93.508 | 92.717 | -5.185 | -5.976 | 73.061 | 68.426 | -3.636 | -4.635 | 9.838 | 10.222 | 10.296 | +0.384 | +0.458 |
| 2580.22 | 99.727 | 97.965 | 97.280 | -1.762 | -2.447 | 74.010 | 73.609 | -0.266 | -0.401 | 9.941 | 10.217 | 10.282 | +0.276 | +0.341 |
| 3008.91 | 96.400 | 98.250 | 98.577 | +1.850 | +2.177 | 78.020 | 77.746 | -0.221 | -0.275 | 9.425 | 9.284 | 9.278 | -0.142 | -0.148 |
| 3508.82 | 89.196 | 87.517 | 87.399 | -1.678 | -1.797 | 69.921 | 67.570 | -1.966 | -2.351 | 10.423 | 10.405 | 10.389 | -0.018 | -0.034 |
| 4091.79 | 89.503 | 90.562 | 90.842 | +1.059 | +1.340 | 75.608 | 72.724 | -2.589 | -2.884 | 9.896 | 10.267 | 10.312 | +0.371 | +0.416 |
| 4771.62 | 94.903 | 92.496 | 90.815 | -2.407 | -4.088 | 77.459 | 76.121 | -0.933 | -1.338 | 9.113 | 9.450 | 9.549 | +0.337 | +0.436 |
| 5564.41 | 83.603 | 86.082 | 86.591 | +2.479 | +2.988 | 76.373 | 75.013 | -1.098 | -1.360 | 10.252 | 9.883 | 9.833 | -0.369 | -0.419 |
| 6488.90 | 83.519 | 82.240 | 82.001 | -1.279 | -1.518 | 77.555 | 76.917 | -0.866 | -0.638 | 10.250 | 10.502 | 10.498 | +0.252 | +0.248 |
| 7567.00 | 89.839 | 88.162 | 87.610 | -1.677 | -2.229 | 83.422 | 83.206 | -0.078 | -0.216 | 8.818 | 9.272 | 9.407 | +0.454 | +0.589 |
| 8824.22 | 93.149 | 93.118 | 93.179 | -0.031 | +0.030 | 81.491 | 83.693 | +1.887 | +2.202 | 9.439 | 9.090 | 9.031 | -0.349 | -0.408 |
| 10290.32 | 86.065 | 86.430 | 86.718 | +0.365 | +0.653 | 73.662 | 74.868 | +0.961 | +1.206 | 10.796 | 10.519 | 10.436 | -0.277 | -0.360 |
| 12000.00 | 82.748 | 81.872 | 81.539 | -0.875 | -1.209 | 71.346 | 71.262 | +0.196 | -0.085 | 11.016 | 11.063 | 11.116 | +0.046 | +0.100 |
- MAX |delta| 2->50 m, all 300-12000 Hz: bw_h_deg 24.2966 (at 407.97 Hz); bw_v_deg 15.6077 (at 475.75 Hz); di_db 0.8833 (at 300 Hz)
- MAX |delta| 2->50 m, in-band 700-12000 Hz: bw_h_deg 7.2620 (at 1395.23 Hz); bw_v_deg 8.8136 (at 754.46 Hz); di_db 0.5892 (at 7567 Hz)

#### RO (47e1259ad615, 4729 dofs, traced solve 38.62 s)

| f (Hz) | bw_H 2m | bw_H 10m | bw_H 50m | dBW_H 2->10 | dBW_H 2->50 | bw_V 2m | bw_V 50m | dBW_V 2->10 | dBW_V 2->50 | DI 2m | DI 10m | DI 50m | dDI 2->10 | dDI 2->50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 300.00 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 3.068 | 2.351 | 2.208 | -0.716 | -0.860 |
| 349.84 | 180.000 | 180.000 | 180.000 | +0.000 | +0.000 | 180.000 | 180.000 | +0.000 | +0.000 | 3.838 | 3.172 | 3.038 | -0.666 | -0.800 |
| 407.97 | 152.062 | 170.677 | 175.463 | +18.614 | +23.401 | 162.166 | 180.000 | +17.834 | +17.834 | 4.746 | 4.135 | 4.012 | -0.611 | -0.734 |
| 475.75 | 130.671 | 141.412 | 143.791 | +10.742 | +13.121 | 141.361 | 155.523 | +11.632 | +14.162 | 5.703 | 5.147 | 5.034 | -0.556 | -0.670 |
| 554.79 | 116.692 | 124.798 | 126.588 | +8.106 | +9.895 | 129.483 | 140.761 | +9.286 | +11.279 | 6.620 | 6.112 | 6.008 | -0.508 | -0.612 |
| 646.97 | 104.889 | 111.129 | 112.518 | +6.240 | +7.629 | 120.284 | 130.058 | +8.035 | +9.773 | 7.467 | 7.001 | 6.905 | -0.466 | -0.562 |
| 754.46 | 93.556 | 98.108 | 99.142 | +4.552 | +5.586 | 110.995 | 119.379 | +6.888 | +8.383 | 8.294 | 7.869 | 7.781 | -0.424 | -0.513 |
| 879.81 | 82.902 | 85.937 | 86.643 | +3.035 | +3.742 | 100.636 | 107.476 | +5.619 | +6.840 | 9.172 | 8.795 | 8.716 | -0.376 | -0.456 |
| 1025.99 | 74.226 | 75.853 | 76.280 | +1.627 | +2.054 | 89.703 | 95.067 | +4.394 | +5.365 | 10.089 | 9.778 | 9.710 | -0.312 | -0.379 |
| 1196.45 | 69.668 | 69.616 | 69.741 | -0.052 | +0.072 | 78.887 | 82.956 | +3.327 | +4.068 | 10.863 | 10.640 | 10.588 | -0.224 | -0.275 |
| 1395.23 | 72.425 | 68.993 | 68.565 | -3.431 | -3.860 | 69.213 | 72.029 | +2.289 | +2.817 | 11.291 | 11.186 | 11.156 | -0.106 | -0.135 |
| 1627.04 | 86.442 | 81.018 | 79.815 | -5.424 | -6.628 | 62.853 | 64.175 | +1.025 | +1.322 | 11.307 | 11.353 | 11.352 | +0.046 | +0.045 |
| 1897.37 | 89.468 | 86.592 | 85.998 | -2.875 | -3.469 | 61.898 | 60.312 | -1.479 | -1.586 | 11.214 | 11.395 | 11.420 | +0.181 | +0.206 |
| 2212.60 | 90.875 | 88.321 | 87.861 | -2.554 | -3.015 | 77.358 | 69.228 | -6.797 | -8.130 | 10.726 | 11.069 | 11.127 | +0.344 | +0.401 |
| 2580.22 | 95.069 | 91.551 | 90.959 | -3.518 | -4.109 | 79.659 | 75.875 | -2.980 | -3.784 | 10.047 | 10.443 | 10.517 | +0.396 | +0.470 |
| 3008.91 | 98.057 | 93.403 | 92.322 | -4.654 | -5.735 | 80.148 | 78.986 | -0.923 | -1.161 | 9.871 | 10.326 | 10.413 | +0.455 | +0.542 |
| 3508.82 | 101.507 | 100.424 | 100.141 | -1.083 | -1.366 | 81.999 | 80.638 | -1.204 | -1.361 | 8.655 | 9.040 | 9.133 | +0.386 | +0.478 |
| 4091.79 | 100.346 | 99.238 | 98.759 | -1.108 | -1.587 | 83.397 | 80.068 | -2.552 | -3.329 | 8.689 | 8.802 | 8.849 | +0.113 | +0.161 |
| 4771.62 | 93.252 | 95.575 | 96.051 | +2.323 | +2.799 | 81.096 | 82.735 | +1.315 | +1.640 | 9.307 | 9.092 | 9.048 | -0.215 | -0.259 |
| 5564.41 | 90.378 | 89.719 | 89.682 | -0.659 | -0.697 | 79.340 | 78.450 | -0.852 | -0.890 | 9.432 | 9.574 | 9.577 | +0.142 | +0.144 |
| 6488.90 | 87.396 | 87.064 | 86.922 | -0.332 | -0.474 | 79.564 | 78.390 | -0.790 | -1.175 | 9.550 | 9.618 | 9.659 | +0.068 | +0.109 |
| 7567.00 | 82.482 | 82.895 | 83.032 | +0.412 | +0.549 | 73.882 | 75.428 | +1.284 | +1.546 | 10.515 | 10.257 | 10.211 | -0.257 | -0.304 |
| 8824.22 | 80.919 | 79.843 | 79.744 | -1.076 | -1.175 | 71.405 | 71.094 | -0.333 | -0.310 | 11.079 | 11.041 | 11.022 | -0.038 | -0.057 |
| 10290.32 | 75.589 | 74.065 | 73.789 | -1.524 | -1.799 | 70.669 | 69.633 | -0.892 | -1.036 | 11.622 | 11.771 | 11.793 | +0.149 | +0.171 |
| 12000.00 | 58.956 | 58.970 | 58.876 | +0.015 | -0.080 | 71.188 | 70.305 | -0.701 | -0.883 | 12.470 | 12.588 | 12.618 | +0.117 | +0.147 |
- MAX |delta| 2->50 m, all 300-12000 Hz: bw_h_deg 23.4012 (at 407.97 Hz); bw_v_deg 17.8337 (at 407.97 Hz); di_db 0.8600 (at 300 Hz)
- MAX |delta| 2->50 m, in-band 700-12000 Hz: bw_h_deg 6.6277 (at 1627.04 Hz); bw_v_deg 8.3832 (at 754.46 Hz); di_db 0.5418 (at 3008.91 Hz)

Verbatim key lines (`runs/m3_wp5a/*.log`, UTF-16 decoded): AXI

```
  max|d spl_h|=0.000128236 dB  max|d DI|=0.154522 dB  max|d bw_h|=0.000129462 deg
WORST |dBW_H|=18.1828 deg at (475.75, 50.0)  |dBW_V|=18.1829 deg at (475.75, 50.0)  |dDI|=1.60567 dB at (7567.0, 50.0)
VRAM baseline=463 MiB peak=1774 MiB peak-baseline=1311 MiB
```

HV:

```
  max|d spl_h|=0.000237388 dB  max|d DI|=0.110965 dB  max|d bw_h|=0.000119484 deg
WORST |dBW_H|=24.2966 deg at (407.97, 50.0)  |dBW_V|=15.6077 deg at (475.75, 50.0)  |dDI|=0.883334 dB at (300.0, 50.0)
```

RO:

```
  max|d spl_h|=0.000203433 dB  max|d DI|=0.0785639 dB  max|d bw_h|=3.57264e-05 deg
WORST |dBW_H|=23.4012 deg at (407.97, 50.0)  |dBW_V|=17.8337 deg at (407.97, 10.0)  |dDI|=0.860038 dB at (300.0, 50.0)
```

### 1.3 Decision — distance_m

**Rule:** propose `distance_m: 10` for v2 briefs **only if** |Δbw| > 1° between 2 m and 50 m
anywhere decisive in-band (700–12 000 Hz).

| design | max in-band \|Δbw_H\| (2→50 m) | max in-band \|Δbw_V\| (2→50 m) | max in-band \|ΔDI\| (2→50 m) | rule |
|---|---|---|---|---|
| AXI | **10.5205°** at 3008.91 Hz | **10.5194°** at 3008.91 Hz | 1.6057 dB at 7567 Hz | **FIRES** |
| HV | **7.2620°** at 1395.23 Hz | **8.8136°** at 754.46 Hz | 0.5892 dB at 7567 Hz | **FIRES** |
| RO | **6.6277°** at 1627.04 Hz | **8.3832°** at 754.46 Hz | 0.5418 dB at 3008.91 Hz | **FIRES** |

Residual at the proposed 10 m (same tables, 2→10 m columns), for the owner: max in-band |Δbw|
2→10 m is 8.658° / 8.656° (AXI), 7.262° / 7.244° (HV), 5.424° / 6.797° (RO); max in-band |ΔDI| is
0.855 / 0.454 / 0.455 dB. So **10 m is a large improvement over 2 m but is not the far field either**
(50 m is converged with 1000 m, section 1.1). Proposal only: `distance_m: 10` for v2 briefs → owner gate.

## 2. WP5(b) — balloon resolution

**Work-order wording vs the stored spec (stated explicitly):** the order asks for deltas "vs the
stored 512-point baseline", but the stored **12 kHz verify** runs used `balloon_points_verify:
1024` → grid **23×45 = 1035** (`response.npz` `meta.balloon_grid = [23, 45]`). The screen runs used
512 (`[16, 32]`). So the 512 DI on the 12 kHz grid is obtained from the WP5(a) trace evaluation at
r = 2 m on the exact stored 16×32 directions (same solve, exact field); the stored 1035 DI is the
baseline; the 1024 re-solve checks the A/B identity; the 2592 re-solve (36×72) is the fine grid.

### WP5(b) tables: DI at 512 (16x32) / 1035 (23x45) / 2592 (36x72) points

DI512 comes from the WP5(a) trace evaluation at r=2 m on the stored screen 16x32 grid (same solve, exact field); DI1035 is the stored verify baseline and the 1024 re-solve; DI2592 is the 36x72 re-solve.

#### AXI (59f57bc457cb)

| f (Hz) | DI 512 | DI 1035 (stored) | DI 1035 (re-solve) | DI 2592 | dDI 512->1035 | dDI 1035->2592 |
|---|---|---|---|---|---|---|
| 300.00 | 2.4246 | 2.4215 | 2.4215 | 2.4198 | -0.0030 | -0.0017 |
| 349.84 | 3.0577 | 3.0534 | 3.0533 | 3.0510 | -0.0044 | -0.0024 |
| 407.97 | 3.8694 | 3.8631 | 3.8630 | 3.8598 | -0.0063 | -0.0033 |
| 475.75 | 4.8150 | 4.8062 | 4.8062 | 4.8016 | -0.0088 | -0.0046 |
| 554.79 | 5.8009 | 5.7890 | 5.7890 | 5.7828 | -0.0119 | -0.0062 |
| 646.97 | 6.7357 | 6.7202 | 6.7202 | 6.7121 | -0.0155 | -0.0080 |
| 754.46 | 7.5972 | 7.5776 | 7.5776 | 7.5675 | -0.0196 | -0.0101 |
| 879.81 | 8.4442 | 8.4196 | 8.4196 | 8.4068 | -0.0246 | -0.0127 |
| 1025.99 | 9.3603 | 9.3286 | 9.3286 | 9.3123 | -0.0317 | -0.0163 |
| 1196.45 | 10.3639 | 10.3222 | 10.3222 | 10.3009 | -0.0417 | -0.0213 |
| 1395.23 | 11.2870 | 11.2335 | 11.2335 | 11.2063 | -0.0535 | -0.0272 |
| 1627.04 | 11.6675 | 11.6077 | 11.6077 | 11.5774 | -0.0598 | -0.0302 |
| 1897.37 | 11.1946 | 11.1411 | 11.1411 | 11.1143 | -0.0535 | -0.0268 |
| 2212.60 | 10.7754 | 10.7277 | 10.7277 | 10.7038 | -0.0477 | -0.0239 |
| 2580.22 | 9.8064 | 9.7691 | 9.7691 | 9.7505 | -0.0373 | -0.0186 |
| 3008.91 | 7.3134 | 7.2973 | 7.2973 | 7.2888 | -0.0162 | -0.0084 |
| 3508.82 | 6.9276 | 6.9142 | 6.9142 | 6.9073 | -0.0134 | -0.0069 |
| 4091.79 | 9.4805 | 9.4450 | 9.4450 | 9.4289 | -0.0354 | -0.0161 |
| 4771.62 | 10.7503 | 10.6964 | 10.6964 | 10.6716 | -0.0539 | -0.0248 |
| 5564.41 | 9.8073 | 9.7756 | 9.7756 | 9.7554 | -0.0317 | -0.0202 |
| 6488.90 | 7.3312 | 7.3661 | 7.3661 | 7.3575 | +0.0349 | -0.0087 |
| 7567.00 | 10.0177 | 9.8632 | 9.8632 | 9.8479 | -0.1545 | -0.0153 |
| 8824.22 | 10.2886 | 10.3112 | 10.3112 | 10.2912 | +0.0226 | -0.0200 |
| 10290.32 | 8.9992 | 8.9191 | 8.9191 | 8.9534 | -0.0802 | +0.0343 |
| 12000.00 | 11.1573 | 11.1234 | 11.1234 | 11.1642 | -0.0338 | +0.0407 |
- MAX |dDI| 512->1035: 0.1545 dB at 7567 Hz (in-band 0.1545 dB at 7567 Hz)
- MAX |dDI| 1035->2592: 0.0407 dB at 12000 Hz (in-band 0.0407 dB at 12000 Hz)
- A/B identity: the 1024 re-solve reproduces the stored DI to 8.17e-05 dB; J 9.437805 vs stored 9.437804

#### HV (fed761193da7)

| f (Hz) | DI 512 | DI 1035 (stored) | DI 1035 (re-solve) | DI 2592 | dDI 512->1035 | dDI 1035->2592 |
|---|---|---|---|---|---|---|
| 300.00 | 2.9698 | 2.9658 | 2.9658 | 2.9637 | -0.0040 | -0.0022 |
| 349.84 | 3.7177 | 3.7120 | 3.7120 | 3.7090 | -0.0057 | -0.0030 |
| 407.97 | 4.6181 | 4.6101 | 4.6100 | 4.6058 | -0.0081 | -0.0042 |
| 475.75 | 5.5932 | 5.5821 | 5.5821 | 5.5764 | -0.0111 | -0.0057 |
| 554.79 | 6.5494 | 6.5348 | 6.5348 | 6.5272 | -0.0146 | -0.0076 |
| 646.97 | 7.4420 | 7.4233 | 7.4233 | 7.4136 | -0.0187 | -0.0097 |
| 754.46 | 8.3029 | 8.2792 | 8.2792 | 8.2671 | -0.0236 | -0.0122 |
| 879.81 | 9.1982 | 9.1680 | 9.1680 | 9.1525 | -0.0302 | -0.0155 |
| 1025.99 | 10.1253 | 10.0864 | 10.0864 | 10.0666 | -0.0388 | -0.0199 |
| 1196.45 | 10.8468 | 10.7997 | 10.7997 | 10.7757 | -0.0471 | -0.0240 |
| 1395.23 | 11.0226 | 10.9735 | 10.9735 | 10.9485 | -0.0492 | -0.0249 |
| 1627.04 | 11.0604 | 11.0109 | 11.0109 | 10.9859 | -0.0494 | -0.0250 |
| 1897.37 | 10.7403 | 10.6953 | 10.6953 | 10.6725 | -0.0450 | -0.0228 |
| 2212.60 | 9.8376 | 9.8040 | 9.8040 | 9.7867 | -0.0336 | -0.0173 |
| 2580.22 | 9.9411 | 9.9073 | 9.9073 | 9.8897 | -0.0338 | -0.0176 |
| 3008.91 | 9.4253 | 9.3960 | 9.3960 | 9.3809 | -0.0293 | -0.0151 |
| 3508.82 | 10.4228 | 10.3815 | 10.3815 | 10.3610 | -0.0413 | -0.0205 |
| 4091.79 | 9.8963 | 9.8621 | 9.8621 | 9.8446 | -0.0342 | -0.0175 |
| 4771.62 | 9.1131 | 9.0988 | 9.0988 | 9.0858 | -0.0143 | -0.0131 |
| 5564.41 | 10.2520 | 10.2089 | 10.2089 | 10.1892 | -0.0431 | -0.0197 |
| 6488.90 | 10.2499 | 10.1938 | 10.1938 | 10.1734 | -0.0561 | -0.0204 |
| 7567.00 | 8.8178 | 8.8268 | 8.8268 | 8.8188 | +0.0090 | -0.0080 |
| 8824.22 | 9.4391 | 9.3750 | 9.3750 | 9.3758 | -0.0642 | +0.0009 |
| 10290.32 | 10.7961 | 10.7345 | 10.7345 | 10.7312 | -0.0616 | -0.0033 |
| 12000.00 | 11.0163 | 10.9053 | 10.9053 | 10.8981 | -0.1110 | -0.0072 |
- MAX |dDI| 512->1035: 0.1110 dB at 12000 Hz (in-band 0.1110 dB at 12000 Hz)
- MAX |dDI| 1035->2592: 0.0250 dB at 1627.04 Hz (in-band 0.0250 dB at 1627.04 Hz)
- A/B identity: the 1024 re-solve reproduces the stored DI to 5.36e-05 dB; J 10.536487 vs stored 10.536482

#### RO (47e1259ad615)

| f (Hz) | DI 512 | DI 1035 (stored) | DI 1035 (re-solve) | DI 2592 | dDI 512->1035 | dDI 1035->2592 |
|---|---|---|---|---|---|---|
| 300.00 | 3.0677 | 3.0635 | 3.0634 | 3.0612 | -0.0043 | -0.0022 |
| 349.84 | 3.8382 | 3.8322 | 3.8322 | 3.8290 | -0.0060 | -0.0031 |
| 407.97 | 4.7458 | 4.7373 | 4.7373 | 4.7329 | -0.0085 | -0.0044 |
| 475.75 | 5.7032 | 5.6918 | 5.6918 | 5.6859 | -0.0114 | -0.0059 |
| 554.79 | 6.6200 | 6.6052 | 6.6052 | 6.5975 | -0.0149 | -0.0077 |
| 646.97 | 7.4671 | 7.4484 | 7.4484 | 7.4387 | -0.0187 | -0.0097 |
| 754.46 | 8.2936 | 8.2701 | 8.2701 | 8.2580 | -0.0235 | -0.0121 |
| 879.81 | 9.1715 | 9.1417 | 9.1417 | 9.1263 | -0.0298 | -0.0154 |
| 1025.99 | 10.0894 | 10.0512 | 10.0512 | 10.0315 | -0.0383 | -0.0196 |
| 1196.45 | 10.8632 | 10.8161 | 10.8161 | 10.7921 | -0.0470 | -0.0240 |
| 1395.23 | 11.2913 | 11.2387 | 11.2387 | 11.2119 | -0.0527 | -0.0267 |
| 1627.04 | 11.3066 | 11.2538 | 11.2538 | 11.2272 | -0.0527 | -0.0267 |
| 1897.37 | 11.2138 | 11.1628 | 11.1628 | 11.1370 | -0.0511 | -0.0258 |
| 2212.60 | 10.7258 | 10.6812 | 10.6812 | 10.6587 | -0.0446 | -0.0225 |
| 2580.22 | 10.0472 | 10.0113 | 10.0113 | 9.9929 | -0.0359 | -0.0183 |
| 3008.91 | 9.8709 | 9.8371 | 9.8371 | 9.8198 | -0.0338 | -0.0173 |
| 3508.82 | 8.6548 | 8.6326 | 8.6326 | 8.6210 | -0.0222 | -0.0116 |
| 4091.79 | 8.6886 | 8.6672 | 8.6672 | 8.6555 | -0.0214 | -0.0117 |
| 4771.62 | 9.3068 | 9.2811 | 9.2811 | 9.2663 | -0.0257 | -0.0148 |
| 5564.41 | 9.4324 | 9.4017 | 9.4017 | 9.3863 | -0.0307 | -0.0154 |
| 6488.90 | 9.5505 | 9.5343 | 9.5343 | 9.5196 | -0.0161 | -0.0147 |
| 7567.00 | 10.5147 | 10.4722 | 10.4722 | 10.4507 | -0.0425 | -0.0215 |
| 8824.22 | 11.0788 | 11.0217 | 11.0217 | 10.9958 | -0.0571 | -0.0259 |
| 10290.32 | 11.6217 | 11.5630 | 11.5630 | 11.5356 | -0.0586 | -0.0274 |
| 12000.00 | 12.4704 | 12.3919 | 12.3919 | 12.3622 | -0.0786 | -0.0297 |
- MAX |dDI| 512->1035: 0.0786 dB at 12000 Hz (in-band 0.0786 dB at 12000 Hz)
- MAX |dDI| 1035->2592: 0.0297 dB at 12000 Hz (in-band 0.0297 dB at 12000 Hz)
- A/B identity: the 1024 re-solve reproduces the stored DI to 1.40e-05 dB; J 12.508847 vs stored 12.508851

Verbatim (`runs/m3_wp5b/axi_b2592.log`):

```
SPEC mode=verify backend=beat_cuda cuda_fused=True source_motion=normal rear_res_factor=1 band_split=None distance_m=2 angles=73 balloon_requested=2592 balloon_grid=[36, 72]
MESH dofs=6049 triangles=11810 res_mm={'throat': 1.7864583333333333, 'mouth': 3.5729166666666665, 'rear': 3.5729166666666665} mesh_seconds=6.10 solve_seconds=57.10 wall_seconds=64.40
J 9.441125  terms={"cov": 3.14458513385319, "di": 0.5174882050308981, "di_estimated": 0.0, "dislope": 0.04013990999133279, "flat": 3.9742486361935607, "load": 0.20182061753710318, "n_in_band": 19, "n_nan": 0, "penalty": 0.0, "rip": 4.033188400732495, "total": 9.441124577955954}
META balloon_grid=[36, 72] source_motion=normal mesh_policy=None cuda_fused=True assembly_paths=['fused_cuda']
VRAM baseline=463 MiB peak=1774 MiB peak-baseline=1311 MiB
```

and the compare maxima (`runs/m3_wp5b/axi_b2592.compare.log`):

```
  MAXIMA
    bw_h_deg     max |diff| 0.00124669 deg at 475.75  bar 1 deg: WITHIN
    bw_v_deg     max |diff| 0.00125625 deg at 475.75  bar 1 deg: WITHIN
    di_db        max |diff| 0.0407151 dB at 12000.0  bar 0.1 dB: WITHIN
    on_axis_db   max |diff| 0.000197193 dB at 349.84  bar 0.039 dB: WITHIN
```

### 2.1 Decision — balloon

**Rule:** propose raising the screen balloon **only if** |ΔDI| > 0.1 dB from 512 → 1024.

| design | max \|ΔDI\| 512→1035 | where | rule |
|---|---|---|---|
| AXI | **0.1545 dB** | 7567 Hz (8–12 kHz) | **FIRES** |
| HV | **0.1110 dB** | 12000 Hz | **FIRES** |
| RO | 0.0786 dB | 12000 Hz | does not fire |

2 of 3 designs exceed 0.1 dB, both in the high band (AXI at 7,567 Hz, just below f11 = 7,914 Hz;
HV at 12,000 Hz, above it). The 1035→2592 change is ≤ 0.0407 dB on all three, i.e. the 23×45 grid
is already converged to within 0.04 dB of 36×72 while 16×32 is not. **Proposal (owner gate): raise
`solve.balloon_points_screen` 512 → 1024**, which makes a screen DI comparable with the verify DI
it is screened against.

## 3. WP5(c) — source_motion: axial vs normal (measurement only)

Same 12 kHz verify spec, `solve.source_motion: "axial"` (rigid piston along +z) vs the stored
`normal` (breathing cap). f11 = 7,914 Hz caveat applies to every row above 7,914 Hz.

### WP5(c) tables: source_motion axial vs normal, above 5 kHz

#### AXI (59f57bc457cb), J 9.438050 (normal 9.437804)

| f (Hz) | bw_H normal | bw_H axial | dBW_H | bw_V normal | bw_V axial | dBW_V | DI normal | DI axial | dDI | dOnAxis(metric) |
|---|---|---|---|---|---|---|---|---|---|---|
| 5564.41 | 89.135 | 89.135 | -0.0000 | 89.130 | 89.130 | -0.0000 | 9.7756 | 9.7756 | +0.0000 | -0.0001 |
| 6488.90 | 100.463 | 100.463 | -0.0001 | 100.458 | 100.458 | -0.0001 | 7.3661 | 7.3662 | +0.0000 | -0.0000 |
| 7567.00 | 90.474 | 90.474 | -0.0002 | 90.475 | 90.475 | -0.0002 | 9.8632 | 9.8632 | +0.0000 | +0.0000 |
| 8824.22 | 88.080 | 88.079 | -0.0006 | 88.064 | 88.063 | -0.0007 | 10.3112 | 10.3113 | +0.0001 | +0.0001 |
| 10290.32 | 92.643 | 92.641 | -0.0019 | 92.634 | 92.632 | -0.0019 | 8.9191 | 8.9194 | +0.0003 | +0.0004 |
| 12000.00 | 81.207 | 81.200 | -0.0070 | 81.185 | 81.178 | -0.0070 | 11.1234 | 11.1242 | +0.0007 | +0.0009 |
- MAX |delta| above 5 kHz: bw_h_deg 0.0070 (at 12000 Hz); bw_v_deg 0.0070 (at 12000 Hz); di_db 0.0007 (at 12000 Hz); on_axis_db 0.0009 (at 12000 Hz)

#### HV (fed761193da7), J 10.536490 (normal 10.536482)

| f (Hz) | bw_H normal | bw_H axial | dBW_H | bw_V normal | bw_V axial | dBW_V | DI normal | DI axial | dDI | dOnAxis(metric) |
|---|---|---|---|---|---|---|---|---|---|---|
| 5564.41 | 83.603 | 83.603 | -0.0000 | 76.373 | 76.373 | +0.0000 | 10.2089 | 10.2089 | +0.0000 | -0.0000 |
| 6488.90 | 83.519 | 83.519 | -0.0000 | 77.555 | 77.555 | +0.0000 | 10.1938 | 10.1938 | -0.0000 | -0.0000 |
| 7567.00 | 89.839 | 89.839 | -0.0000 | 83.422 | 83.422 | +0.0000 | 8.8268 | 8.8268 | -0.0000 | +0.0000 |
| 8824.22 | 93.149 | 93.149 | -0.0003 | 81.491 | 81.491 | +0.0000 | 9.3750 | 9.3750 | +0.0000 | +0.0001 |
| 10290.32 | 86.065 | 86.064 | -0.0009 | 73.662 | 73.662 | -0.0002 | 10.7345 | 10.7346 | +0.0001 | +0.0001 |
| 12000.00 | 82.748 | 82.744 | -0.0036 | 71.346 | 71.344 | -0.0023 | 10.9053 | 10.9057 | +0.0004 | +0.0006 |
- MAX |delta| above 5 kHz: bw_h_deg 0.0036 (at 12000 Hz); bw_v_deg 0.0023 (at 12000 Hz); di_db 0.0004 (at 12000 Hz); on_axis_db 0.0006 (at 12000 Hz)

#### RO (47e1259ad615), J 12.536788 (normal 12.508851)

| f (Hz) | bw_H normal | bw_H axial | dBW_H | bw_V normal | bw_V axial | dBW_V | DI normal | DI axial | dDI | dOnAxis(metric) |
|---|---|---|---|---|---|---|---|---|---|---|
| 5564.41 | 90.378 | 90.393 | +0.0142 | 79.340 | 79.338 | -0.0020 | 9.4017 | 9.4010 | -0.0008 | -0.0041 |
| 6488.90 | 87.396 | 87.427 | +0.0305 | 79.564 | 79.560 | -0.0039 | 9.5343 | 9.5324 | -0.0019 | -0.0054 |
| 7567.00 | 82.482 | 82.533 | +0.0508 | 73.882 | 73.871 | -0.0106 | 10.4722 | 10.4691 | -0.0031 | -0.0068 |
| 8824.22 | 80.919 | 80.946 | +0.0273 | 71.405 | 71.373 | -0.0318 | 11.0217 | 11.0213 | -0.0004 | -0.0044 |
| 10290.32 | 75.589 | 75.384 | -0.2042 | 70.669 | 70.583 | -0.0861 | 11.5630 | 11.5854 | +0.0224 | +0.0191 |
| 12000.00 | 58.956 | 58.523 | -0.4331 | 71.188 | 71.024 | -0.1647 | 12.3919 | 12.4346 | +0.0428 | +0.0406 |
- MAX |delta| above 5 kHz: bw_h_deg 0.4331 (at 12000 Hz); bw_v_deg 0.1647 (at 12000 Hz); di_db 0.0428 (at 12000 Hz); on_axis_db 0.0406 (at 12000 Hz)

Verbatim (`runs/m3_wp5c/ro_axial.log`):

```
SPEC mode=verify backend=beat_cuda cuda_fused=True source_motion=axial rear_res_factor=1 band_split=None distance_m=2 angles=73 balloon_requested=1024 balloon_grid=[23, 45]
J 12.536788  terms={"cov": 6.424685081138708, "di": 0.18451262528979528, "di_estimated": 0.0, "dislope": 0.8337946629883148, "flat": 4.509724552541674, "load": 0.0, "n_in_band": 19, "n_nan": 0, "penalty": 0.0, "rip": 3.3849891557306897, "total": 12.536787632221332}
META balloon_grid=[23, 45] source_motion=axial mesh_policy=None cuda_fused=True assembly_paths=['fused_cuda']
VRAM baseline=457 MiB peak=1320 MiB peak-baseline=863 MiB
```

**Reading.** AXI and HV have a **5.0° throat angle**, so a breathing cap and an axial piston are
nearly the same boundary datum: above 5 kHz they differ by ≤ 0.007° / 0.0009 dB. RO's R-OSSE throat
is **a0 = 12.37°**, and there the motion model does move the beam: up to 0.433° / 0.165° beamwidth,
0.043 dB DI and **0.0406 dB on-axis at 12 kHz — 0.0016 dB above the CP-7f 0.039 dB on-axis bar**
(at 12 kHz only, i.e. above f11, geometry-comparison region). Measurement only: WP5(c) carries **no
proposal mechanism**; the default stays `normal`.

## 4. WP7 — coarser rear/outer shell (AXI `59f57bc457cb`, screen spec 12 pts 500–5500)

The mesher's `rear_res_mm` drives only the **outer shell + rear cap** (`rear` / `rear_cap` tag
groups — `hornlab_mesher/shell_facets.py:174-175`; `MeshDensity` in `hornlab_mesher/geometry.py:388`),
never the acoustic bore/mouth/throat. `mesh.rear_res_factor` multiplies that one resolution
(`mesh/build.py::res_mm_for_spec`). Stored baseline reused, not re-solved at 1.0: screen run
`runs/20261023T025720Z-screen-2002c3`, design `59f57bc457cb`, **1397 dofs / 2656 triangles**,
rear_res_mm **7.7955**, J **9.62194719939414**, objective version **1** (the ndjson row carries
`"objective_version":1`). Both WP7 jobs ran the fork's **flag-off** path so the A/B isolates the
mesh change (that path is the M2-proven `38544d2` behaviour; section 7.1).

Framework-note (added at review, 2026-10-24): as shipped the factor rode only the mesh-cache key;
the solve-spec extra now carries `rear_res_factor` when != 1.0 (same commit), so solve cache /
failure markers / resume memo cannot replay across factors.

### WP7 tables: rear_res_factor on AXI at the screen spec

Stored baseline: 9.621947 J, 1397 dofs, 2656 triangles, rear_res_mm 7.7955 mm.

#### factor 1.5: 1135 dofs, 2150 triangles, rear_res_mm 11.6932 mm, saved 262 dofs (18.8%), J 9.619486 (delta -0.002461)

| f (Hz) | dBW_H | dBW_V | dDI | dOnAxis(metric) | dRipH |
|---|---|---|---|---|---|
| 500.00 | -0.0197 | -0.0191 | +0.00055 | +0.00069 | +0.00012 |
| 621.79 | -0.0100 | -0.0095 | +0.00052 | +0.00058 | +0.00011 |
| 773.24 | -0.0043 | -0.0038 | +0.00040 | +0.00024 | +0.00007 |
| 961.58 | +0.0005 | +0.0012 | +0.00010 | +0.00006 | -0.00002 |
| 1195.80 | +0.0013 | +0.0024 | -0.00018 | -0.00039 | -0.00007 |
| 1487.07 | +0.0015 | +0.0019 | -0.00020 | -0.00062 | -0.00014 |
| 1849.28 | +0.0102 | +0.0005 | -0.00039 | -0.00074 | -0.00040 |
| 2299.72 | -0.0000 | -0.0031 | +0.00004 | -0.00054 | +0.00003 |
| 2859.87 | -0.0149 | -0.0077 | +0.00108 | -0.00001 | +0.00041 |
| 3556.47 | +0.0023 | -0.0131 | +0.00150 | +0.00043 | -0.00025 |
| 4422.73 | -0.0029 | -0.0006 | +0.00206 | +0.00102 | -0.00042 |
| 5500.00 | -0.0078 | +0.0111 | +0.00113 | +0.00055 | +0.00047 |
- TOP 5500 Hz: dBW_H -0.0078 deg, dBW_V +0.0111 deg, dDI +0.00113 dB, dOnAxis +0.00055 dB  (CP-7f: 1 deg / 1 deg / 0.1 dB / 0.039 dB)
- MAX over the 12 screen frequencies: bw_h_deg 0.01966 (at 500 Hz); bw_v_deg 0.01912 (at 500 Hz); di_db 0.00206 (at 4422.73 Hz); on_axis_db 0.00102 (at 4422.73 Hz)

#### factor 2.0: 1060 dofs, 2006 triangles, rear_res_mm 15.5909 mm, saved 337 dofs (24.1%), J 9.614973 (delta -0.006974)

| f (Hz) | dBW_H | dBW_V | dDI | dOnAxis(metric) | dRipH |
|---|---|---|---|---|---|
| 500.00 | -0.0280 | -0.0296 | +0.00102 | -0.00057 | +0.00016 |
| 621.79 | -0.0122 | -0.0137 | +0.00094 | -0.00116 | +0.00012 |
| 773.24 | -0.0032 | -0.0042 | +0.00065 | -0.00169 | +0.00004 |
| 961.58 | +0.0043 | +0.0051 | +0.00003 | -0.00165 | -0.00014 |
| 1195.80 | +0.0062 | +0.0108 | -0.00079 | -0.00249 | -0.00034 |
| 1487.07 | +0.0063 | +0.0096 | -0.00112 | -0.00316 | -0.00055 |
| 1849.28 | +0.0147 | +0.0071 | -0.00082 | -0.00255 | -0.00045 |
| 2299.72 | -0.0019 | -0.0039 | -0.00020 | -0.00201 | +0.00017 |
| 2859.87 | -0.0069 | -0.0119 | +0.00157 | -0.00135 | -0.00010 |
| 3556.47 | -0.0335 | -0.0367 | +0.00851 | +0.00488 | +0.00090 |
| 4422.73 | -0.0119 | -0.0278 | +0.00360 | -0.00062 | +0.00047 |
| 5500.00 | -0.0989 | -0.0431 | +0.01156 | +0.01064 | +0.00527 |
- TOP 5500 Hz: dBW_H -0.0989 deg, dBW_V -0.0431 deg, dDI +0.01156 dB, dOnAxis +0.01064 dB  (CP-7f: 1 deg / 1 deg / 0.1 dB / 0.039 dB)
- MAX over the 12 screen frequencies: bw_h_deg 0.09890 (at 5500 Hz); bw_v_deg 0.04312 (at 5500 Hz); di_db 0.01156 (at 5500 Hz); on_axis_db 0.01064 (at 5500 Hz)

Verbatim (`runs/m3_wp7/axi_rear2.0.log`):

```
SPEC mode=screen backend=beat_cuda cuda_fused=False source_motion=normal rear_res_factor=2 band_split=None distance_m=2 angles=73 balloon_requested=512 balloon_grid=[16, 32]
MESH dofs=1060 triangles=2006 res_mm={'throat': 3.897727272727273, 'mouth': 7.795454545454546, 'rear': 15.590909090909092} mesh_seconds=1.32 solve_seconds=5.12 wall_seconds=7.03
J 9.614973  terms={"cov": 4.078296006959807, "di": 0.5393103457165157, "di_estimated": 0.0, "dislope": 0.0334795108663424, "flat": 2.173851248036234, "load": 0.2737454959131724, "n_in_band": 10, "n_nan": 0, "penalty": 0.0, "rip": 4.134345724786941, "total": 9.614972962869578}
SCALARS f11_hz=7914.3 di_mean=9.4998 bw_h_mean=87.801 bw_v_mean=87.797 ripple_mean=2.0672 flatness=2.1739
VRAM baseline=457 MiB peak=848 MiB peak-baseline=391 MiB
```

and the compare maxima (`runs/m3_wp7/axi_rear2.0.compare.log`):

```
  MAXIMA
    bw_h_deg     max |diff| 0.0989045 deg at 5500.0  bar 1 deg: WITHIN
    bw_v_deg     max |diff| 0.0431244 deg at 5500.0  bar 1 deg: WITHIN
    di_db        max |diff| 0.0115569 dB at 5500.0  bar 0.1 dB: WITHIN
    on_axis_db   max |diff| 0.0106389 dB at 5500.0  bar 0.039 dB: WITHIN
```

### 4.1 Decision — rear_res_factor

| factor | dofs (saved vs 1397) | J (Δ vs 9.621947) | top 5.5 kHz Δon-axis | top Δbw_H / Δbw_V | top ΔDI | CP-7f |
|---|---|---|---|---|---|---|
| 1.0 (stored) | 1397 (0) | 9.621947 | — | — | — | reference |
| 1.5 | 1135 (−262, −18.8%) | 9.619486 (−0.002461) | +0.00055 dB | −0.0078° / +0.0111° | +0.00113 dB | **PASS** |
| 2.0 | 1060 (−337, −24.1%) | 9.614973 (−0.006974) | +0.01064 dB | −0.0989° / −0.0431° | +0.01156 dB | **PASS** |

Both factors are inside every CP-7f bar by 10× (beamwidth), 8.6× (DI) and 3.7× (on-axis) at the
top frequency, and inside them at all 12 frequencies (the worst cells are also at 5.5 kHz).
**Proposal (owner gate): `mesh.rear_res_factor: 2.0`** — the largest factor tested and passing;
3.0 was **not** measured, so nothing above 2.0 is claimed. No config was edited. (J falls slightly
with the coarser shell; that is the design's own sensitivity, not a gate failure — the gate is the
per-frequency CP-7f set.)

## 5. WP8 — band-split meshing (`edges_hz: [3000, 6000]`), AXI + HV

12 kHz verify spec unchanged (25 freqs, ball 1024, epw 8 / 6, 2 m). `solve.extra` gets
`mesh_policy: band_split_v1` + `band_edges_hz`; each band is meshed at its **upper bound** as
`f_max` (band 0 → 3000 Hz, band 1 → 6000 Hz, band 2 → 12000 Hz), solved on that mesh and stacked
(`solve/base.py::stack_responses`); verify mode adds the seam check (first frequency above each
edge re-solved on the lower band's mesh, `Response.meta.seam_check`).

### 5.1 Per-band structure, wall time, dofs

| design | band 0 (300–2580 Hz) | band 1 (3009–5564 Hz) | band 2 (6489–12000 Hz) | single-mesh (same code) | wall saving |
|---|---|---|---|---|---|
| AXI | 15 freqs, 3000 Hz mesh, **497 dofs** / 912 tris, 14.29 mm | 5 freqs, 6000 Hz, **1636 dofs** / 3122 tris, 7.15 mm | 5 freqs, 12000 Hz, **6049 dofs** / 11810 tris, 3.57 mm | 6049 dofs, 63.68 s | **29.64 s → 53.5% less** |
| HV | 15 freqs, 3000 Hz, **435 dofs** / 792 tris, 19.06 mm | 5 freqs, 6000 Hz, **1202 dofs** / 2281 tris, 9.53 mm | 5 freqs, 12000 Hz, **4540 dofs** / 8840 tris, 4.76 mm | 4540 dofs, 47.08 s | **33.82 s → 28.2% less** |

(The single-mesh comparator is the **same-code** 1024 re-solve, not the old-path stored run, so
the saving is not a fork artefact.) Summed solve timings from `Response.meta`: AXI
`assembly_s 9.127, solve_s 0.678, field_s 0.356, total_s 18.081`; HV `assembly_s 6.439,
solve_s 0.420, field_s 0.519, total_s 16.974`.

Band 2's `f_max` (12,000 Hz) equals the single-mesh `f_max`, so band 2's mesh IS the single mesh —
its 6,049 dofs are a per-band value that coincides with the single-mesh count, not a sum; the
banded path's total mesh work is 497 + 1,636 + 6,049 dofs across three meshes.

Honesty note on the walls: the band-split walls (29.64 / 33.82 s) INCLUDE the two verify-only seam
solves while the single-mesh comparator has none — the seam work makes the MEASURED saving an
UNDERESTIMATE of band-split's pure mesh-and-solve saving (the direction is conservative against
band-split, not flattering to it).

### 5.2 Seam check (`Response.meta.seam_check`, verbatim from the logs)

```
SEAM (first frequency above each edge re-solved on the LOWER band's mesh)
  edge   3000 Hz  f=3008.91 Hz  on_axis_delta=-0.237126 dB  bw_h_delta=-0.295665 deg  bw_v_delta=-0.218850 deg
  edge   6000 Hz  f=6488.90 Hz  on_axis_delta=-0.110981 dB  bw_h_delta=-0.103269 deg  bw_v_delta=-0.082317 deg
```

(HV, `runs/m3_wp8/hv_band.log`)

```
  edge   3000 Hz  f=3008.91 Hz  on_axis_delta=-0.270660 dB  bw_h_delta=+0.297718 deg  bw_v_delta=-0.444589 deg
  edge   6000 Hz  f=6488.90 Hz  on_axis_delta=-0.043031 dB  bw_h_delta=+0.285446 deg  bw_v_delta=-0.482456 deg
```

### 5.3 Tables vs the stored single-mesh 12 kHz baselines

### WP8 tables: band_split edges [3000, 6000] at the 12 kHz verify spec

#### AXI (59f57bc457cb)

- J band-split 9.490815; same-code single-mesh 9.437805 (delta +0.053010); stored old-path single-mesh 9.437804
- wall 29.64 s vs same-code single-mesh 63.68 s (53.5% less)
- bands: band 0 300.0-2580.2 Hz x15 freqs, f_max 3000 Hz -> 497 dofs / 912 tris, res_mm 14.292; band 1 3008.9-5564.4 Hz x5 freqs, f_max 6000 Hz -> 1636 dofs / 3122 tris, res_mm 7.146; band 2 6488.9-12000.0 Hz x5 freqs, f_max 12000 Hz -> 6049 dofs / 11810 tris, res_mm 3.573
- seam: edge 3000 Hz, first above 3008.91 Hz on the lower mesh -> on-axis -0.237126 dB, bw_H -0.295665 deg, bw_V -0.218850 deg; edge 6000 Hz, first above 6488.90 Hz on the lower mesh -> on-axis -0.110981 dB, bw_H -0.103269 deg, bw_V -0.082317 deg

| f (Hz) | dBW_H | dBW_V | dDI | dOnAxis(metric) | dOnAxis(raw SPL) | dRipH |
|---|---|---|---|---|---|---|
| 300.00 | +0.0000 | +0.0000 | -0.0254 | -0.2409 | -0.4208 | -0.0047 |
| 349.84 | +0.0000 | +0.0000 | -0.0328 | -0.2586 | -0.4384 | -0.0058 |
| 407.97 | +0.0000 | +0.0000 | -0.0398 | -0.2799 | -0.4598 | -0.0066 |
| 475.75 | +1.2996 | +1.2898 | -0.0441 | -0.2982 | -0.4781 | -0.0071 |
| 554.79 | +0.7113 | +0.7008 | -0.0438 | -0.2909 | -0.4709 | -0.0074 |
| 646.97 | +0.5062 | +0.4953 | -0.0398 | -0.2375 | -0.4176 | -0.0079 |
| 754.46 | +0.4330 | +0.4233 | -0.0353 | -0.2057 | -0.3858 | -0.0091 |
| 879.81 | +0.4013 | +0.3960 | -0.0330 | -0.2182 | -0.3982 | -0.0110 |
| 1025.99 | +0.3566 | +0.3614 | -0.0324 | -0.2387 | -0.4188 | -0.0133 |
| 1196.45 | +0.2591 | +0.2844 | -0.0284 | -0.2417 | -0.4218 | -0.0134 |
| 1395.23 | +0.0811 | +0.1447 | -0.0092 | -0.1879 | -0.3679 | -0.0010 |
| 1627.04 | -0.2882 | -0.2074 | +0.0316 | -0.1297 | -0.3098 | +0.0344 |
| 1897.37 | -1.2476 | -1.2166 | +0.0497 | -0.1416 | -0.3216 | +0.0430 |
| 2212.60 | -0.4820 | -0.4529 | +0.0518 | -0.0902 | -0.2702 | +0.0200 |
| 2580.22 | -0.7564 | -0.7499 | +0.1529 | -0.0029 | -0.1830 | +0.0285 |
| 3008.91 | -0.0794 | -0.0830 | -0.0054 | +0.1203 | -0.0598 | +0.0065 |
| 3508.82 | +0.1240 | +0.1252 | -0.0204 | +0.0936 | -0.0865 | +0.0176 |
| 4091.79 | +0.1942 | +0.1880 | -0.0550 | +0.0619 | -0.1181 | -0.0011 |
| 4771.62 | +0.1283 | +0.1438 | -0.0265 | +0.0948 | -0.0853 | -0.0048 |
| 5564.41 | -0.5422 | -0.5282 | +0.0678 | +0.1857 | +0.0056 | +0.0055 |
| 6488.90 | +0.0000 | +0.0000 | -0.0000 | +0.1801 | -0.0000 | -0.0000 |
| 7567.00 | -0.0000 | +0.0000 | -0.0000 | +0.1801 | +0.0000 | -0.0000 |
| 8824.22 | +0.0000 | +0.0000 | -0.0000 | +0.1801 | +0.0000 | -0.0000 |
| 10290.32 | +0.0000 | +0.0000 | -0.0000 | +0.1801 | +0.0000 | -0.0000 |
| 12000.00 | +0.0000 | -0.0000 | -0.0000 | +0.1801 | -0.0000 | -0.0000 |
- MAX in-band 700-12000 Hz: bw_h_deg 1.2476 (at 1897.37 Hz); bw_v_deg 1.2166 (at 1897.37 Hz); di_db 0.1529 (at 2580.22 Hz); on_axis_db 0.2417 (at 1196.45 Hz); raw on-axis 0.4218 dB (at 1196.45 Hz)  (CP-7f: 1 deg / 1 deg / 0.1 dB / 0.039 dB)

#### HV (fed761193da7)

- J band-split 10.528828; same-code single-mesh 10.536487 (delta -0.007659); stored old-path single-mesh 10.536482
- wall 33.82 s vs same-code single-mesh 47.08 s (28.2% less)
- bands: band 0 300.0-2580.2 Hz x15 freqs, f_max 3000 Hz -> 435 dofs / 792 tris, res_mm 19.056; band 1 3008.9-5564.4 Hz x5 freqs, f_max 6000 Hz -> 1202 dofs / 2281 tris, res_mm 9.528; band 2 6488.9-12000.0 Hz x5 freqs, f_max 12000 Hz -> 4540 dofs / 8840 tris, res_mm 4.764
- seam: edge 3000 Hz, first above 3008.91 Hz on the lower mesh -> on-axis -0.270660 dB, bw_H +0.297718 deg, bw_V -0.444589 deg; edge 6000 Hz, first above 6488.90 Hz on the lower mesh -> on-axis -0.043031 dB, bw_H +0.285446 deg, bw_V -0.482456 deg

| f (Hz) | dBW_H | dBW_V | dDI | dOnAxis(metric) | dOnAxis(raw SPL) | dRipH |
|---|---|---|---|---|---|---|
| 300.00 | +0.0000 | +0.0000 | -0.0303 | -0.2520 | -0.4284 | -0.0066 |
| 349.84 | +0.0000 | +0.0000 | -0.0383 | -0.2759 | -0.4522 | -0.0080 |
| 407.97 | +1.7681 | +1.7927 | -0.0444 | -0.3009 | -0.4773 | -0.0090 |
| 475.75 | +0.9234 | +0.8432 | -0.0464 | -0.3077 | -0.4842 | -0.0099 |
| 554.79 | +0.6441 | +0.5555 | -0.0442 | -0.2570 | -0.4334 | -0.0108 |
| 646.97 | +0.5231 | +0.4499 | -0.0402 | -0.1975 | -0.3739 | -0.0124 |
| 754.46 | +0.4459 | +0.4292 | -0.0372 | -0.1995 | -0.3760 | -0.0148 |
| 879.81 | +0.3546 | +0.4244 | -0.0351 | -0.2215 | -0.3979 | -0.0165 |
| 1025.99 | +0.1827 | +0.3895 | -0.0283 | -0.2277 | -0.4041 | -0.0085 |
| 1196.45 | -0.3371 | +0.3228 | -0.0040 | -0.1815 | -0.3580 | +0.0277 |
| 1395.23 | -1.0957 | +0.1184 | +0.0194 | -0.1511 | -0.3276 | +0.0350 |
| 1627.04 | -0.3754 | -0.4640 | +0.0378 | -0.1363 | -0.3128 | +0.0218 |
| 1897.37 | -0.5775 | -0.9259 | +0.0879 | -0.0515 | -0.2280 | +0.0208 |
| 2212.60 | -0.7358 | +0.0652 | +0.0174 | -0.1222 | -0.2987 | +0.0094 |
| 2580.22 | -0.8057 | -0.6983 | +0.1021 | -0.0410 | -0.2175 | +0.0747 |
| 3008.91 | +0.2655 | +0.0997 | -0.0449 | +0.0583 | -0.1182 | -0.0034 |
| 3508.82 | -0.5644 | -0.4323 | +0.0208 | +0.1223 | -0.0542 | +0.0175 |
| 4091.79 | +0.2214 | +0.1475 | +0.0015 | +0.0936 | -0.0829 | -0.0289 |
| 4771.62 | +0.1967 | -0.0721 | +0.0125 | +0.1133 | -0.0632 | -0.0108 |
| 5564.41 | +0.3373 | +0.0775 | -0.0495 | +0.0624 | -0.1141 | -0.0116 |
| 6488.90 | +0.0000 | +0.0000 | -0.0000 | +0.1765 | +0.0000 | -0.0000 |
| 7567.00 | +0.0000 | +0.0000 | -0.0000 | +0.1765 | -0.0000 | -0.0000 |
| 8824.22 | -0.0000 | -0.0000 | +0.0000 | +0.1765 | -0.0000 | +0.0000 |
| 10290.32 | +0.0000 | +0.0000 | -0.0000 | +0.1765 | +0.0000 | -0.0000 |
| 12000.00 | -0.0000 | +0.0000 | -0.0000 | +0.1765 | -0.0000 | +0.0000 |
- MAX in-band 700-12000 Hz: bw_h_deg 1.0957 (at 1395.23 Hz); bw_v_deg 0.9259 (at 1897.37 Hz); di_db 0.1021 (at 2580.22 Hz); on_axis_db 0.2277 (at 1025.99 Hz); raw on-axis 0.4041 dB (at 1025.99 Hz)  (CP-7f: 1 deg / 1 deg / 0.1 dB / 0.039 dB)

**How to read `dOnAxis(metric)` vs `dOnAxis(raw SPL)`.** `MetricSet.on_axis_db` is normalised to
the band mean (`metrics/compute.py:107-116`), so a level shift in one sub-band re-references the
whole curve: at ≥ 6,489 Hz the mesh is **identical** to the single-mesh solve (raw Δon-axis
0.0000) yet the metric shows a constant +0.1801 dB (AXI) / +0.1765 dB (HV) because the band mean
moved. The physical per-frequency error is the **raw** column: −0.18 … −0.48 dB on band 0,
−0.12 … +0.006 dB on band 1, exactly 0 on band 2.

Verbatim (`runs/m3_wp8/axi_band.log`):

```
FREQS n=25 300..12000 Hz
MESH dofs=6049 triangles=11810 res_mm={'throat': 1.7864583333333333, 'mouth': 3.5729166666666665, 'rear': 3.5729166666666665} mesh_seconds=5.97 solve_seconds=19.69 wall_seconds=29.64
J 9.490815  terms={"cov": 3.2454963168031488, "di": 0.5291243572351318, "di_estimated": 0.0, "dislope": 0.035492022067723505, "flat": 3.844612088609875, "load": 0.20653099924593796, "n_in_band": 19, "n_nan": 0, "penalty": 0.0, "rip": 4.043264029555627, "total": 9.490815208491084}
BANDS
  band            f range n_f   f_max   dofs   tris res_mm
     0      300..    2580  15    3000    497    912 {'mouth': 14.291666666666666, 'rear': 14.291666666666666, 'throat': 7.145833333333333}
     1     3009..    5564   5    6000   1636   3122 {'mouth': 7.145833333333333, 'rear': 7.145833333333333, 'throat': 3.5729166666666665}
     2     6489..   12000   5   12000   6049  11810 {'mouth': 3.5729166666666665, 'rear': 3.5729166666666665, 'throat': 1.7864583333333333}
META balloon_grid=[23, 45] source_motion=normal mesh_policy=band_split_v1 cuda_fused=True assembly_paths=['fused_cuda']
VRAM baseline=457 MiB peak=1814 MiB peak-baseline=1357 MiB
```

and the stock CLI comparison (`runs/m3_wp8/axi_band.compare_cli.log`):

```
compare A=runs\20261023T195300Z-verify-bdae12 (design 59f57bc457cb, quadrants '1')
        B=runs\m3_wp8\axi_band\run (design 59f57bc457cb, quadrants '1')
  25 frequencies 300..12000 Hz
  bw_h_deg     max |diff| 1.3 deg  mean 0.3156  (n=25)
  bw_v_deg     max |diff| 1.29 deg  mean 0.3116  (n=25)
  di_db        max |diff| 0.1529 dB   mean 0.033  (n=25)
  on_axis_db   max |diff| 0.2982 dB   mean 0.1808  (n=25)
  ripple_h_db  max |diff| 0.04297 dB   mean 0.009949  (n=25)
  ripple_v_db  max |diff| 0.04334 dB   mean 0.01  (n=25)
compare OK (report only; reference: OSSE full vs quarter 0.023 dB, CP-7d)
```

HV (`runs/m3_wp8/hv_band.compare_cli.log`): `bw_h_deg max 1.768 deg`, `bw_v_deg 1.793 deg`,
`di_db 0.1021 dB`, `on_axis_db 0.3077 dB`, `ripple_h_db 0.07466`, `ripple_v_db 0.03672` (n=25).

### 5.4 Provenance in the normal path

The run dir is a normal `search.ndjson` + dataset-store run (`DatasetStore` under the job dir), so
`mesh_policy` comes from `search/evaluate.py::_record_provenance` and — for the ndjson row — from
the two-line echo added to `_persist` (section 7.2). Pasted AXI row (`runs/m3_wp8/axi_band/run/search.ndjson`,
long `params`/`metrics` arrays elided here as `…`; every other field is byte-identical):

```
{"n":0,"mode":"verify","key":"59f57bc457cb-27b99ae77cf8-fe65fa8d7fcd","design_hash":"59f57bc457cb","mesh_hash":"27b99ae77cf8","solve_hash":"fe65fa8d7fcd","family":"FREEFORM","params":{…},"objective_version":1,"objective":9.490815208491084,"terms":{"cov":3.2454963168031488,"rip":4.043264029555627,"di":0.5291243572351318,"dislope":0.035492022067723505,"flat":3.844612088609875,"load":0.20653099924593796,"penalty":0.0,"total":9.490815208491084,"n_nan":0,"n_in_band":19,"di_estimated":0.0},"ok":true,"error":"","kind":"","cached":false,"seconds":{"mesh":5.969126899988623,"solve":19.6937542000378,"total":29.627213700005086},"n_dof":6049,"n_triangles":11810,"quadrants":"1","symmetry_plane":"yz+xz","bbox_m":[0.0,0.0,-0.003,0.1676232829999999,0.1676232829999999,0.114183523],"res_mm":{"throat":1.7864583333333333,"mouth":3.5729166666666665,"rear":3.5729166666666665},"peak_vram_mb":null,"metrics":{…},"created_utc":"2026-10-25T03:46:03Z","mesh_policy":"band_split_v1"}
```

Dataset record provenance (`runs/m3_wp8/axi_band/dataset/shard-0000.jsonl`):

```
{
 "brief": "axi_90x90_1in_12k",
 "brief_hash": "67036cb8a4e1",
 "config": "osse_axi",
 "mesh_policy": "band_split_v1"
}
```

### 5.5 Decision — band_split

**Acceptance gate:** J + per-frequency metrics within the CP-7f bars (0.039 dB on-axis /
1° beamwidth / 0.1 dB DI) of the single-mesh solve.

| design | wall | J | in-band max \|Δbw_H\| | in-band max \|Δbw_V\| | in-band max \|ΔDI\| | in-band max raw \|Δon-axis\| | seam on-axis | verdict |
|---|---|---|---|---|---|---|---|---|
| AXI | 29.64 s (−53.5%) | 9.490815 (+0.053010) | **1.2476°** @1897 Hz | **1.2166°** @1897 Hz | **0.1529 dB** @2580 Hz | **0.4218 dB** @1196 Hz | −0.237 dB / −0.111 dB | **FAIL** |
| HV | 33.82 s (−28.2%) | 10.528828 (−0.007659) | **1.0957°** @1395 Hz | 0.9259° @1897 Hz | **0.1021 dB** @2580 Hz | **0.4041 dB** @1026 Hz | −0.271 dB / −0.043 dB | **FAIL** |

**Both designs fail the gate at these edges.** The time saving is real (28–54%) and the 6–12 kHz
band is bit-identical (same mesh), but the low band (≤ 2580 Hz meshed at 3000 Hz / epw 8) carries a
systematic **−0.18 … −0.48 dB raw on-axis** and up to 1.25° (AXI) / 1.10° (HV) beamwidth in-band
(1.77° out of band at 408 Hz), and the seam delta (−0.24 / −0.27 dB at 3,008.91 Hz) is ~6× the
0.039 dB bar. **No proposal to adopt** and no config was changed. A follow-up would have to change
the band tops or the per-band epw and re-measure; that is an owner decision, not taken here.

## 6. Decision-rule tables (proposals only — the owner gates any flip)

| # | rule (verbatim intent) | measured | threshold crossed? | proposal |
|---|---|---|---|---|
| D1 | `distance_m: 10` for v2 briefs **only if** \|Δbw\| > 1° between 2 m and 50 m anywhere decisive in-band | AXI 10.52°/10.52° (H/V) @3008.91 Hz; HV 7.26° @1395 Hz / 8.81° @754 Hz; RO 6.63° @1627 Hz / 8.38° @754 Hz | **YES — all three** | **PROPOSE `distance_m: 10` for v2 briefs.** Owner gate. Residual 2→10 m still up to 8.66° (AXI @3.0 kHz) / 0.86 dB DI — 10 m is better, not converged (50 m ≈ 1000 m). |
| D2 | raise the screen balloon **only if** \|ΔDI\| > 0.1 dB from 512 → 1024 | AXI **0.1545 dB** @7567 Hz; HV **0.1110 dB** @12 kHz; RO 0.0786 dB | **YES — 2 of 3** | **PROPOSE `solve.balloon_points_screen: 512 → 1024`** (1035 points, matches verify). Owner gate. |
| D3 | `source_motion`: measurement only, **no proposal mechanism** | AXI/HV ≤ 0.007° / 0.0009 dB above 5 kHz; RO 0.433° / 0.0406 dB on-axis @12 kHz | n/a | **No proposal.** Default stays `normal`. Note RO's 0.0406 dB is 0.0016 dB over the CP-7f on-axis bar at 12 kHz (above f11). |
| D4 | WP7: adopt the largest factor within the CP-7f bar | 1.5 PASS, **2.0 PASS** (top 5.5 kHz: 0.0106 dB / 0.099° / 0.0116 dB; band max 0.0106 dB / 0.0989° / 0.0116 dB); dofs 1397→1060 | 2.0 within all bars | **PROPOSE `mesh.rear_res_factor: 2.0`.** Largest tested factor; 3.0 unmeasured. No config edit. Owner gate. |
| D5 | WP8: J + per-frequency metrics within CP-7f of the single mesh | AXI and HV both exceed (see 5.5) | **YES (fails)** | **No proposal.** Do not adopt `edges_hz: [3000, 6000]` as-is. |

Untouched by this pass, as ordered: `NEXT_DEV_PRIORITIES.md`, `tools/launch_gui.ps1`, every
`examples/**` config, every brief, every default (`distance_m 2.0`, `balloon_points_screen 512`,
`balloon_points_verify 1024`, `source_motion normal`, `rear_res_factor 1.0`, no `band_split`).

## 7. Integrity notes, code changes and suites

### 7.1 Fresh re-solve of a stored baseline (the A/B distance used everywhere)

Every 12 kHz re-solve here is the fork's fused path; the stored baselines are beat `38544d2`
default path. Measured on the same designs/spec (this pass, `runs/m3_wp5b/*.compare.log`):

| design | J stored | J re-solve | max \|ΔDI\| | max \|Δbw\| |
|---|---|---|---|---|
| AXI | 9.437803769692346 | 9.437805 | 8.17e-5 dB | 0.0013° |
| HV | 10.536482194312132 | 10.536487 | 5.36e-5 dB | 0.0014° |
| RO | 12.508851005880057 | 12.508847 | 1.40e-5 dB | 0.0006° |

That is 2–3 orders inside the CP-7f bars and is the reason the WP5/WP8 comparisons are read against
those bars; the WP7 jobs ran flag-off precisely so their sub-0.1° deltas are not inflated by the
fused/default difference.

### 7.2 Code changes (this pass)

1. `tools/m3_measurement_pack.py` — **new**, the whole pack (no GPU work on import; `--help` is
   inert). Subcommands `solve`, `traces`, `compare`; one job per process; VRAM poll from a daemon
   thread; `worker.shutdown(verify=True)` in a `finally`; JSON payload with spec / dofs / freqs /
   per-frequency metrics / J / `meta` (seam_check, source_motion, balloon grid, timings) / VRAM.
   Two self-protection guards were added after they proved necessary: (a) refuse to run when the
   job's run dir already holds `search.ndjson` rows (an `evaluate` on it returns the in-run cache
   hit and measures nothing); (b) `--set` values fall back to YAML when JSON fails (PowerShell
   strips the inner quotes of `--set mesh.band_split={"edges_hz": [3000, 6000]}`).
2. `hornlab_search/search/evaluate.py` — **+3 lines** in `_persist`: when `st["mesh_policy"]` is
   set, the ndjson row carries `"mesh_policy": "band_split_v1"` (WP8 plan step 4 visibility in the
   run rows; single-mesh rows are byte-identical to before, the key is absent).
   `tests/test_search_evaluate.py` + `tests/test_config.py`: **46 collected, 46 passed, exit 0**
   (`runs/m3_code/offline_tests_after_row_echo.log`; the console capture drops pytest's count line,
   so the count is from `--collect-only -q`: `tests/test_config.py: 32`, `tests/test_search_evaluate.py: 14`).
3. Nothing else touched. No config, brief, default, tolerance or test was modified.

### 7.3 Two discarded AXI band attempts (and why they are not findings)

- **First AXI band run** (23:43:28): the solve completed (J 9.490815) but the console printer raised
  `ValueError: Unknown format code 'd' for object of type 'float'` on the per-band table **after**
  the JSON was written. The run dir and JSON existed; the log lacked the tail. Fixed the formatter
  and re-ran from a clean GPU state with a fresh cache dir (23:45:16) — same J (9.490815), full log.
  The discarded attempt's 27.12 s is included in the GPU-wall figure.
- **Second attempt** (23:44:30) hit the first run's `search.ndjson` and returned the in-run cache
  hit (`wall_seconds=0.00`, empty meta). That exposed the guard now in the tool (7.2a); the job dir
  was deleted and the measured run is the third attempt. No number from either attempt is used except
  the J that the third run reproduced exactly.

No solver crash and no OOM occurred in any job, so rule 7 (reproduce from clean state) was not
triggered; every VRAM peak-baseline stayed ≤ 1,357 MiB.

### 7.4 What the offline suite covers here

Only the two edited/new files were exercised: the focused 46-test subset above. The full offline
suite at the FINAL state of the pass (after the Oracle-review fixes) is
`runs/m3_code/suite_final.xml`: 968 tests / 0
errors / 1 failure (`tests/test_mesh_pin`) / 0 skipped at the final code state (and
`runs/m3_carryover/suite.xml` 944 / 0 / 1 / 0 at the carry-over commit); the junitxml does not
record the run's 20 deselections. The focused post-fix subset is `runs/m3_code/suite_oracle_fixes.xml`
(68 / 0 / 0 / 0, covering the renamed rear-factor test, the row-echo assertions and the seam-error
change). This pass adds one additive ndjson key and one new tool file,
and re-runs the affected subset only. No desktop/PySide code is touched by this pass.
