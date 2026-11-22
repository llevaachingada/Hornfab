# Balloon DI/power control (R5a, 2026-11-21)

**Scope.** Risk R5's second half: the stored system cases carry 1-D H/V cuts and probes only, so
there was no DI or power response. This control adds one CPU `beat_cpu` solve with Boundary Lab's
full-sphere observation enabled, then computes per-excitation DI and power from the equal-area
Fibonacci balloon. It does **not** declare a far-field or listening-window standard (owner
decision 5) and does **not** combine the two channel references (R1).

**Fidelity.** `COUPLED_VENTED_FEM_BEM_LEM` on the assembled #2 source, real 12PR300 T/S, BL's
**demo 200 mm transducer shape** (R2), one default mesh, three frequencies (200, 1000, 2500 Hz).
The sphere is a single 10 m equal-area Fibonacci set. No convergence, absolute-SPL, or combined
system claim is made.

## Case and invocation

Source case: `system/ev_assembled_motor_real/20261120T150709Z-wide_assembled-01612-383da940`.
The derived balloon case is declared `status: proposed` in
`docs/research/system_woofer_2026-11-18/cases.d/30_balloon_2026-11-21.yaml`.

```powershell
.venv\Scripts\python.exe tools\system\evidence_case.py `
  --source-case ev_assembled_motor_real/20261120T150709Z-wide_assembled-01612-383da940 `
  --experiment-id ev_balloon_di --tag balloon `
  --request docs\queue\system_evidence_2026-11-19\requests\balloon_di_10m_3f.json `
  --project-preferences docs\queue\system_evidence_2026-11-19\requests\balloon_prefs_10m_5deg.json `
  --balloon-deg 5 --store system_runs `
  --authorized-by "system-evidence-r5-2026-11-21" --solve
```

Verified solve result from the command's own JSON:

```text
"returncode": 0,
"run_dir": ".../system_runs/system/ev_balloon_di/20261121T140048Z-balloon-62680-49358be1/run",
"status": "complete"
```

The derived case's `case.blab.json` records the exact merged preferences:

```json
{"balloon_angle_precision_deg": 5.0, "polar_observation_distance_m": 10.0,
 "spherical_sampling_enabled": true}
```

BL's `project validate` ran before the solve (`reference_validate.json`, blockers empty). The run
manifest has `completion_mask: [true, true, true]`, backend `beat_cpu`.

## Balloon geometry [measured]

| Property | Value |
|---|---|
| Domain | `observation:sphere` (`spherical_observation`) |
| Points | **1650** = `round(41253 / 5²)` |
| Distance | **10.0 m** (radius min 9.999999999999998, max 10.000000000000002) |
| Quadrature | equal-area Fibonacci; `di_source = "balloon"` |
| Exact +Z sample | **No** (max z/r = 0.999393939…); the on-axis probe is used instead |

## Result [measured, CPU recompute]

Axis reference: the same-excitation `observation:probe:on_axis_10m` at the sphere distance
(`axis_source = "on_axis_probe"`). Power is the equal-area mean of `|p|²` in Pa²; DI is
`10 log10(|p_axis|² / mean |p|²)`.

| Excitation | Per-input | f Hz | DI dB | Power Pa² |
|---|---|---:|---:|---:|
| `vented/voltage` (woofer) | `V_rms` | 200 | **2.406952** | 3.400102e-03 |
| `vented/voltage` (woofer) | `V_rms` | 1000 | **2.867904** | 5.624680e-03 |
| `vented/voltage` (woofer) | `V_rms` | 2500 | **7.195447** | 2.232208e-04 |
| `excitation:horn` | `normal_velocity_mps` | 200 | **1.863021** | 4.989266e-05 |
| `excitation:horn` | `normal_velocity_mps` | 1000 | **7.463739** | 6.185444e-02 |
| `excitation:horn` | `normal_velocity_mps` | 2500 | **12.119238** | 6.639661e-02 |

The committed machine record is
[`BALLOON_DI_POWER_2026-11-21.json`](BALLOON_DI_POWER_2026-11-21.json). The per-excitation
separation is deliberate: voltage and normal-velocity bases are different references and are
never summed into one DI.

## What this closes and what it does not

Closes: R5a, the "no DI/power" half. A valid BL balloon exists and the system layer computes
per-excitation DI/power without a cuts-derived estimate.

Does not close: the observation-standard half (R5b) stays blocked by owner decision 5. These
curves are **not** a declared far-field, listening-window, or CTA-style standard, and 10 m at
200 Hz is still a single-distance diagnostic. The R2 demo shape and R6 single-mesh limits also
travel with the numbers.

## Reproduce

```python
from pathlib import Path
from hornlab_search.system import balloon_metrics as BM
from hornlab_search.system.boundarylab import bl_results as R

run = Path("system_runs/system/ev_balloon_di/"
           "20261121T140048Z-balloon-62680-49358be1/run")
result = R.read_bl_headless_result(run)
metrics = BM.per_excitation_metrics(
    result, axis_probe_id="observation:probe:on_axis_10m")
for excitation, values in metrics.items():
    print(excitation, values["per_input"], values["di_db"], values["power_pa2"])
```

Focused tests: `tests/system/test_balloon_metrics.py` and `tests/system/test_evidence_case.py`
(27 passed on 2026-11-21). No GPU was used.
