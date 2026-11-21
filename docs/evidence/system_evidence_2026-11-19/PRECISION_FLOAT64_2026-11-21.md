# Float32 vs float64 precision control — assembled #2, 6 frequencies (2026-11-21)

**Scope.** Risk R9: every stored system solve is `float32`; deep nulls might be precision-limited.
This is a CPU-only `beat_cpu` control on the **same assembled #2 project and mesh** as the
recorded `ev_assembled_motor_real` 25-frequency case. No GPU was used; the live favourite queue
held the GPU lane. No owner decision is involved.

**Fidelity.** The case is the same `COUPLED_VENTED_FEM_BEM_LEM` model with the real 12PR300 T/S
and BL's provider-default transducer shape. The comparison is numerical precision only; it is
not a measurement and does not remove the R2 shape limitation.

## Case and invocation

- Case: `system_runs/system/ev_precision_f64/20261121T084807Z-f64_6f-33768-3be6fcf6/`
- Source (float32) case: `system_runs/system/ev_assembled_motor_real/20261120T150709Z-wide_assembled-01612-383da940/`
- Request: `docs/queue/system_evidence_2026-11-19/requests/precision_f64_6f.json`
  (committed; sha256 `ba7834f512647083b604903586d39b1066f16233976ba2ee558030042a0fd30a`)
- Project sha256 (both cases): `5b2e0b83de1d6c1ed6cc0a156f5bd5beaa3e6730fcadd422ba6d5bf688bd631d`
- Mesh sha256 (both runs): interior `92dce03b328cdcd51b78c3fdef297bd3b7967710968f92041148c65637b685d7`,
  exterior `e5b3955d3dae2491ff746391d2ab2790ea263ceef05e746e4f3c3545b0229887`,
  horn `9b4057c27ba72779dc07bbf4a50f910ea9223fb982f0071cb0fb3139cf49815d`.
- Frequencies: 200.0, 969.6137, 1641.0495, 1823.1662, 2025.4934, 2500.0 Hz — the last four
  bracket the deep nulls exposed by the 49-point dense control.

RECONSTRUCTED invocation (the exact argv is stored in `reference_solve.json`; this is the
committed wrapper call):

```powershell
.venv\Scripts\python.exe tools/system/evidence_case.py `
  --source-case system_runs/system/ev_assembled_motor_real/20261120T150709Z-wide_assembled-01612-383da940 `
  --experiment-id ev_precision_f64 --tag f64_6f `
  --request docs/queue/system_evidence_2026-11-19/requests/precision_f64_6f.json `
  --notes "R9 float64 precision control: real-motor assembled #2, 6 freqs around the 1.6-2.5 kHz nulls; CPU only; same mesh as the float32 25-freq case" `
  --authorized-by "readiness R9 2026-11-21: CPU float64 precision control (no owner decision required)" `
  --solve --timeout-s 1800
```

Result: `status complete`, `6/6` frequencies, `returncode 0`, 85 s wall time
(`2026-11-21T08:48:08Z` → `2026-11-21T08:49:33Z`). The run manifest records `precision:
"float64"` and the solver used `lu_float64` with zero refinement iterations:

<!-- evidence-quote: source=system_runs/system/ev_precision_f64/20261121T084807Z-f64_6f-33768-3be6fcf6/run/frequencies/000000.json mode=lines decode=utf-8 -->
```
    "dense_refinement_iterations": 0,
    "dense_solver": "lu_float64",
    ...
    "precision": "float64",
```

The float32 source run is the already-recorded `ev_assembled_motor_real` (`precision: "float32"`,
`dense_solver: "lu_float32_refined"`); its 25-frequency grid contains every float64 frequency
exactly.

## Comparison method

Read both run directories with `hornlab_search.system.boundarylab.bl_results.read_bl_headless_result`,
match fields by `(excitation_id, observation.domain_id, quantity_id)`, and match frequencies
exactly (the float32 grid contains all six float64 frequencies). For every complex point:

- `ΔdB = 20 log10(|p_float64| / |p_float32|)`
- `Δphase = angle(p_float64 / p_float32)` in degrees.

14 common fields (H/V polars, five probes, both excitations) × 6 frequencies × observation
points = **948 compared complex points**.

## Result [measured, CPU recompute]

| Quantity | Value |
|---|---:|
| max \|ΔdB\| (all 948 points) | **0.00286 dB** at 1823.166 Hz, vertical-polar |
| max \|Δphase\| (all 948 points) | **0.01187°** at 2500.0 Hz |
| median \|ΔdB\| | 0.00000 dB |
| null-depth delta, H plane (max over both excitations) | **≤0.0005 dB** |
| null-depth delta, V plane (max over both excitations) | **≤0.0005 dB** |

On-axis magnitudes at the six frequencies (Pa; float32 source run vs float64 control):

| f Hz | woofer f32 | woofer f64 | ΔdB | horn f32 | horn f64 | ΔdB |
|---:|---:|---:|---:|---:|---:|---:|
| 200.0 | 3.909846743e-01 | 3.909842483e-01 | -0.00001 | 4.681366963e-02 | 4.681373675e-02 | +0.00001 |
| 969.6137 | 4.835382654e-01 | 4.835402954e-01 | +0.00004 | 3.114832084e+00 | 3.114826885e+00 | -0.00001 |
| 1641.0495 | 1.724592812e-01 | 1.724560598e-01 | -0.00016 | 4.480883921e+00 | 4.480889900e+00 | +0.00001 |
| 1823.1662 | 1.571514788e-01 | 1.571144435e-01 | -0.00205 | 4.338385528e+00 | 4.338385875e+00 | +0.00000 |
| 2025.4934 | 1.852683097e-01 | 1.852697953e-01 | +0.00007 | 3.988389659e+00 | 3.988383131e+00 | -0.00001 |
| 2500.0 | 1.650232758e-01 | 1.650223821e-01 | -0.00005 | 5.228360842e+00 | 5.228378132e+00 | +0.00003 |

Null depths are unchanged (e.g. 1823.166 Hz H-plane woofer −17.971 dB float32 vs −17.970 dB
float64; V-plane woofer −19.096 vs −19.097 dB). The largest single-point difference
(0.0029 dB / 0.012°) is far below any acoustic interpretation threshold and is not concentrated
at the nulls.

## Interpretation and closure

On this assembled #2 mesh, **float32 is not the limiting factor for null depth or fine
interference structure**: a float64 solve using `lu_float64` changes the complex field by at
most 0.0029 dB and 0.012°, and the null depths by at most 0.001 dB. The large null movement
reported in the mesh-convergence control (up to ~16 dB) is therefore a mesh/frequency-sampling
effect, not a float32 precision effect.

This closes the R9 precision question **for this mesh and band**. It does not establish that
another mesh, a higher frequency band, or a different solver path is precision-insensitive; the
control is one settled case, as R9 asked. The stored `float32` cases need no re-solve.

## Recompute recipe

```python
from pathlib import Path
from hornlab_search.system.boundarylab import bl_results as R

f32 = Path("system_runs/system/ev_assembled_motor_real/"
           "20261120T150709Z-wide_assembled-01612-383da940/run")
f64 = Path("system_runs/system/ev_precision_f64/"
           "20261121T084807Z-f64_6f-33768-3be6fcf6/run")
r32, r64 = R.read_bl_headless_result(f32), R.read_bl_headless_result(f64)
# match (excitation_id, observation.domain_id, quantity_id) fields and exact frequencies,
# then compute 20*log10(|p64|/|p32|) and angle(p64/p32) per complex point.
```

Raw `run/*.npz` remain local (gitignored); this document is the committed text evidence.
