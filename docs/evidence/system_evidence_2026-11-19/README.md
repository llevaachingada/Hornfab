# System evidence — LF, motor×box, observation and sampling controls (2026-11-19)

**Scope.** CPU-only Boundary Lab `beat_cpu` runs on existing immutable projects, launched by
`docs/queue/system_evidence_2026-11-19.yaml` and derived by `tools/system/evidence_case.py`. No GPU
job was started. The queue ran beside the live `fable_expand_2026-11-19` GPU night in the separate
CPU lane.

**Fidelity.** Every solve is `COUPLED_VENTED_FEM_BEM_LEM` for the vented-only cases and the same
BL coupled model for the assembled cases. The motors are real 12PR300 T/S in #4/#6 and BL demo
defaults in #5/R0/the assembled #2 source. The transducer acoustic **shape** remains BL's provider
default in every case. This is not a calibrated system response and is not a measurement.

**No byte-checked log quotes.** The numbers below are read-only recomputations from the stored
per-frequency `run/*.npz`/JSON via `hornlab_search.system.boundarylab.bl_results`, not retyped from
prose. Raw arrays stay local; the case paths and the recompute recipe are given so any reviewer can
repeat them.

## What ran

Queue invocation (CPU lane; no GPU lock):

```powershell
.venv\Scripts\python.exe tools\run_campaign_night.py `
  --night runs\nights\system_evidence_2026-11-19.yaml `
  --admission docs\queue\system_evidence_2026-11-19.admission.json
```

Each solve job derived a fresh case from an existing project:

```powershell
.venv\Scripts\python.exe tools\system\evidence_case.py `
  --source-case <case> --experiment-id <ev_id> --tag <tag> `
  --request docs\queue\system_evidence_2026-11-19\requests\<request>.json --solve
```

| Job | Result | Case |
|---|---|---|
| `ev_lf_motor_real` (first attempt) | **failed, retained**: wrong project port (`vented/voltage`; this project uses `bl_motor12pr/voltage`) | `ev_lf_motor_real/20261120T051055Z-lf_20_200-23176-3a9c8637` (no run) |
| `ev_lf_motor_real` (retry, manual) | complete **12/12**, 20–200 Hz | `ev_lf_motor_real/20261120T053351Z-lf_20_200-30640-c2cf0f62` |
| `ev_lf_demo_twin` | complete **12/12** | `ev_lf_demo_twin/20261120T051258Z-lf_20_200-23196-0a6370e7` |
| `ev_lf_default_real` | complete **12/12** | `ev_lf_default_real/20261120T051351Z-lf_20_200-45416-03efa73a` |
| `ev_lf_default_demo` | complete **12/12** | `ev_lf_default_demo/20261120T051425Z-lf_20_200-01448-88659fb9` |
| `ev_lf_assembled_demo` | complete **12/12** | `ev_lf_assembled_demo/20261120T051458Z-lf_20_200-35104-5973f4ef` |
| `ev_wide_default_real` | complete **25/25** | `ev_wide_default_real/20261120T051740Z-wide_200_2500-46632-3de4e1d9` |
| `ev_wide_default_demo` | complete **25/25** | `ev_wide_default_demo/20261120T051840Z-wide_200_2500-36092-b530b722` |
| `ev_farfield_g4_10m` | complete **25/25** | `ev_farfield_g4_10m/20261120T051941Z-farfield_10m-10828-d72876e6` |
| `ev_dense_g4_49` | complete **49/49** | `ev_dense_g4_49/20261120T052433Z-dense_49-50100-30d7ef04` |
| `ev_screen_variety` | study **`27616eedee09009f`** (byte-identical replay of the re-ranked screen) | `system_runs/screens/system_evidence_2026-11-19/woofer_seed.json` |
| `ev_export_system_data` | census exported to `system_runs/evidence_export_2026-11-19/` (before the #4 retry; regenerate) | — |

The first attempt failed because the #4 project's excitation id is `bl_motor12pr/voltage`, not
`vented/voltage`; the retry used `requests/lf_motor12pr_20_200.json`. The failed case is retained
because cases are immutable; its failure record is the evidence, not a bug to erase.

## LF on-axis, 20–200 Hz

Source: per-case on-axis probe (`observation:probe:on_axis_2m`, 2 m), vented voltage port (or
`bl_motor12pr/voltage` for #4). Values are dB relative to the maximum in the 20–200 Hz band
`[measured, CPU recompute]`.

| f Hz | #4 real seed | #5 demo seed | #6 real default | R0 demo default | assembled demo (#2) |
|---:|---:|---:|---:|---:|---:|
| 20.0 | −24.1 | −15.5 | −22.1 | −15.3 | −15.3 |
| 24.7 | −11.9 | −4.1 | −12.9 | −13.6 | −13.6 |
| 30.4 | −3.8 | −2.5 | −9.8 | −11.7 | −11.7 |
| 37.5 | −9.5 | −2.2 | −10.0 | −8.6 | −8.6 |
| 46.2 | −10.4 | −1.6 | −9.6 | −4.8 | −4.8 |
| 57.0 | −10.1 | −2.0 | −8.6 | −1.3 | −1.3 |
| 70.2 | −9.1 | −2.8 | −7.3 | 0.0 | 0.0 |
| 86.6 | −8.0 | −3.6 | −6.0 | −0.7 | −0.7 |
| 106.7 | −7.0 | −4.4 | −4.6 | −1.6 | −1.6 |
| 131.6 | −6.5 | −5.4 | −3.1 | −2.0 | −2.0 |
| 162.2 | −16.1 | −16.9 | −1.6 | −1.9 | −1.9 |
| 200.0 | 0.0 | 0.0 | 0.0 | −1.4 | −1.4 |

Observations (all `[measured]` on this grid):

- The real-motor seed box (#4) has a broad **−9 to −10 dB plateau around 37–70 Hz** and a deep
  **162 Hz null (−16.1 dB)**; the demo twin (#5) is smoother at 30–57 Hz but has the same 162 Hz
  null (−16.9 dB). The motor model changes the LF curve by up to **5.3 dB** and **39.6°** on this
  grid (real vs demo, seed box).
- The real-motor default box (#6) rolls off earlier and more smoothly (−9.8 dB at 30 Hz, −1.6 dB
  at 162 Hz); the demo default box (R0) peaks at **70 Hz** and is only −1.4 dB at 200 Hz. Motor
  difference on the default box reaches **5.3 dB / 40.6°** on this grid.
- The assembled demo case (#2) and the vented-only demo default box (R0) are **identical in shape**
  to within **0.06 dB / 1.8°** at LF. At this level the horn contributes no measurable LF change
  on-axis; the woofer/box dominates. This is a useful null result, not a coupling proof.
- The 162 Hz null appears in both seed-box cases but not in the default-box curves; it is a
  box/port/motor interaction, not a universal LF feature. Do not extrapolate it to another box.

### Bassbox comparison (analysis only, no new solve)

The committed `bassbox` model was evaluated on the same 20–200 Hz grid for the seed box
(115 L, 45 cm², Fb 30 Hz, effective port length 0.129569 m) and the R0 default box
(0.04216945 m³, 28.274 cm², 0.22 m, derived Fb 30.14 Hz), using the real 12PR300 T/S. Curves are
dB relative to the 200 Hz value, model output at 2 m (1 m half-space minus 6.02 dB), `[model]`.
**Mapping note (2026-11-21):** BL's default-box source uses a 0.22 m port **total incl. lips**;
the table's 0.22 m effective length is the old mapping. The physical mapping (0.22 − two 8 mm lips,
then + bassbox's end correction) gives Fb 27.99 Hz; the NFR 0.12 flare makes the true Fb a range,
not a single number. See the audit below.

| f Hz | bassbox seed | bassbox R0 default |
|---:|---:|---:|
| 20.0 | −19.9 | −22.7 |
| 24.7 | −13.3 | −20.0 |
| 30.4 | −10.0 | −17.2 |
| 37.5 | −8.3 | −14.4 |
| 46.2 | −6.9 | −11.5 |
| 57.0 | −5.5 | −8.7 |
| 70.2 | −4.2 | −6.1 |
| 86.6 | −3.0 | −3.9 |
| 106.7 | −1.9 | −2.3 |
| 131.6 | −1.1 | −1.1 |
| 162.2 | −0.5 | −0.4 |
| 200.0 | 0.0 | 0.0 |

`bassbox._f3_hz` = **53.06 Hz** (seed) and **65.01 Hz** (default). Neither curve reproduces the
BL shape:

- Seed box: BL real (#4) is **3.5–5.4 dB below** bassbox over 46–132 Hz, has a **30 Hz port peak**
  (BL −3.8 dB vs model −10.0 dB), and a **162 Hz null** (BL −16.1 dB vs model −0.5 dB) that the
  lumped model does not produce. A single bassbox F3 is not a BL F3.
- Default box: BL real (#6) is **+7.4 dB at 30 Hz**, +1.9 dB at 46 Hz, essentially equal at 57 Hz,
  and **−1.2 to −2.3 dB above 70 Hz** relative to the model; the shapes differ, not just the
  level. (The demo default #R0 is not a clean motor comparison; use #6 for the real-motor cell.)
- **Conclusion:** `bassbox` remains the fast box-feasibility/F3/port-velocity screen, but it is not
  a drop-in installed-LF reference for this cabinet. The model-difference audit is now complete:
  [BASSBOX_MODEL_AUDIT_2026-11-21.md](BASSBOX_MODEL_AUDIT_2026-11-21.md) attributes the seed-box
  offset to the demo-shape Sd deficit (4.59 dB) and the default-box 30 Hz peak to the lossless BL
  port vs the damped lumped port, and records the port-length mapping fix (R17). Do not run another
  blind F3 comparison.

## Motor × box, 200–2500 Hz wide grid

On-axis probe, same 25 log frequencies; values are `[measured]` differences between the two cases
at each frequency (real minus demo, or seed-box minus default-box). "max" is the largest absolute
per-frequency dB/phase difference, not a band statistic.

| Comparison | max \|ΔdB\| | at Hz | mean \|ΔdB\| | max \|Δphase\| | at Hz |
|---|---:|---:|---:|---:|---:|
| motor: #4 real seed vs #5 demo seed | **8.58** | 1641 | 6.85 | **34.4°** | 200 |
| motor: #6 real default vs R0 demo default | **22.25** | 1641 | 7.09 | **100.4°** | 2250 |
| box: #4 real seed vs #6 real default | **23.64** | 1823 | 3.52 | **177.8°** | 2250 |
| box: #5 demo seed vs R0 demo default | **21.28** | 1641 | 3.48 | **174.5°** | 1077 |

The large maxima are **interference nulls**, not smooth sensitivity offsets: the box comparison
moves nulls by tens of dB and flips phase near them. The motor comparison is a smooth +4.5 to
+8.6 dB over most of the band for the seed box; the default-box motor comparison is corrupted at
1641/1823 Hz by a deep null. This is exactly why a single-number motor or box delta is not used.

## Real-motor assembled case (WP3)

`ev_assembled_motor_real` derives the assembled #2 project, patches the woofer component
`vented/driver` with the real 12PR300 T/S through the same `component_parameters` fields used by
`motor_map`, runs BL `project validate` (valid true, rc 0), then solves 25/25. The transducer
**shape** remains BL's demo shape; only the motor is real. `ev_assembled_motor_real_lf` repeats the
same case at 20–200 Hz.

Against the demo-motor assembled #2 (same geometry, same 25-freq grid), on-axis `[measured]`:

- **+4.8 to +7.8 dB across 200–2500 Hz; mean 6.75 dB; max phase 32.1°**. The difference is smooth
  and positive, not a null artefact: the demo motor understates the assembled woofer basis by
  roughly 6–7 dB per 2.83 V.
- LF real vs demo assembled: **max 5.31 dB / mean 3.10 dB / max 40.6°** on 20–200 Hz. This is the
  same motor-difference magnitude as the vented-only pairs; the horn still does not change the LF
  on-axis shape.
- The real-motor assembled basis is still **not a calibrated system SPL**: the horn channel is
  per 1 m/s, the woofer per 2.83 V, and the transducer shape is demo. It is the first assembled
  case with a real woofer motor, not a complete-system answer.

## Mesh convergence

Three meshes of the same assembled geometry were solved on the same 49-frequency grid:

| mesh | interior tris | exterior tris | on-axis max \|ΔdB\| vs default | mean | RMS | max \|Δphase\| |
|---|---:|---:|---:|---:|---:|---:|
| default (0.04/0.012) | 3,954 | 2,010 | — | — | — | — |
| refine1 (0.03/0.009) | 5,976 | 3,246 | 9.75 | 1.11 | 2.64 | 174.0° |
| refine2 (0.0225/0.00675) | 9,148 | 5,688 | 15.99 | 1.27 | 3.30 | 170.5° |

Refine1 vs refine2 is **not monotonic**: max 15.51 dB / mean 1.01 / RMS 2.75 / phase 66.1°.
The large deltas are at nulls (e.g. 636, 1077, 1641, 1730, 2250, 2500 Hz) whose depth and frequency
move with the mesh. The 49-point grid agrees with the 25-point grid at shared points (≤0.03 dB), but
that does **not** mean convergence: the extra points expose nulls and the mesh refinement moves
them.

**Conclusion:** every current system case is a `SINGLE_MESH` result; mesh/frequency convergence at
nulls is **not established**. Small dB differences, J changes, or crossover rankings at these
frequencies are not defensible until a convergence protocol (finer mesh + denser frequencies around
the nulls, with predeclared tolerances) is run. This is a result, not a reason to hide the numbers.

## Observation distance: 10 m vs 2 m

`ev_farfield_g4_10m` is the same assembled #2 project and 25-freq grid with 10 m probes. After
scaling by 1/r (×5) and removing the 8 m propagation phase (`exp(+jk·8 m)`, c=343 m/s):
**max |ΔdB| = 1.38 at 1641 Hz; mean 0.25 dB; max |Δphase| = 17.3° at 1823 Hz**
`[measured, CPU recompute]`.

Without the propagation-phase correction the phase difference is hundreds of degrees, as it must
be; that is a check that the comparison is not double-applying or omitting the path phase. The
1.38 dB / 17° residual means **2 m is not an asymptotic far-field point** at the upper band, and a
2 m H/V cut cannot be relabelled a far-field balloon.

## Frequency sampling: 25 vs 49

`ev_dense_g4_49` adds 24 log frequencies on the **same assembled mesh** (49 points, 200–2500 Hz).
At the 25 shared/nearest frequencies the two curves agree to **max 0.03 dB / mean 0.00 dB**
`[measured]`. The 49-point curve also exposes narrow nulls that the 25-point grid can step over:
for example −19.5 dB at 1641, −20.5 dB at 1823, −19.2 dB at 1922 and 2025 Hz (relative to the
band max). The 25-point grid still contains some nulls but cannot establish their depth/shape.

**Interpretation:** the frequency grid matters more than a small J change; a 25-freq screen is
not a convergence proof. This is a frequency-sampling control, not a mesh-refinement study.

## What this does and does not establish

Established:

- A reproducible CPU pipeline can derive fresh cases from existing immutable projects and solve
  LF / wide / 10 m / dense requests without touching GPU or source cases.
- Real-vs-demo motor differences persist at LF (up to ~5.3 dB / ~40° on the seed box) and across
  the wide band; the demo motor is not a harmless placeholder for system work.
- The assembled horn does not change the LF on-axis shape relative to the vented-only default box
  at this fidelity (0.06 dB), while the box configuration changes the null structure strongly.
- 2 m is not far field at the upper band; 10 m differs by up to 1.38 dB after 1/r correction.
- 25 vs 49 frequency sampling can miss deep nulls even when shared points agree.

Not established:

- No calibration of the two channel references; no complete-system SPL or system score.
- No real transducer shape (BL demo shape in every case); #4/#6 use real T/S, #5/R0/#2 use demo.
- Mesh/frequency convergence is **not** established: the two refined meshes move nulls by up to
  ~16 dB (see Mesh convergence); the 25 vs 49 control tests frequency sampling only, not mesh
  convergence. A `float64` control now exists (R9, [PRECISION_FLOAT64_2026-11-21.md](PRECISION_FLOAT64_2026-11-21.md)):
  on the assembled #2 mesh it bounds the float32 error at 0.0029 dB / 0.012° and leaves null
  depths unchanged, so the null movement is a mesh/sampling effect. No full sphere.
- The bassbox-vs-BL audit is complete ([BASSBOX_MODEL_AUDIT_2026-11-21.md](BASSBOX_MODEL_AUDIT_2026-11-21.md));
  the LF curves above are BL only, and the differences are the declared model differences (demo
  shape/Sd, port end correction/NFR, losses, finite baffle), not a solver defect.

## Recompute recipe

```python
from pathlib import Path
from hornlab_search.system.boundarylab import bl_results as R

run = Path("system_runs/system/ev_lf_demo_twin/<case>/run")
res = R.read_bl_headless_result(run)
field = next(f for f in res.fields
             if f.excitation_id == "vented/voltage"
             and f.observation.domain_id == "observation:probe:on_axis_2m")
p = field.p_pa[:, 0]
# relative dB, phase differences, and the 1/r+propagation correction as above
```

Raw `run/*.npz` remain local; this document is the committed text evidence.
