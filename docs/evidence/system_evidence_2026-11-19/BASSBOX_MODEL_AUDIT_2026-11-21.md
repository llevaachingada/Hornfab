# Bassbox vs Boundary Lab LF model-difference audit (2026-11-21)

**Scope.** Risks R3 and R17: the LF band has been solved as a separate 20–200 Hz control, and the
committed `tools/bassbox.py` lumped model is not the same object as BL's meshed port. This audit
compares the recorded BL cases with the committed bassbox model on the same driver and box,
attributes the differences to declared model choices, and records the port-length mapping fix.
It is a read-only CPU recomputation; **no new solve was run** and the GPU lane was untouched.

**Fidelity.** All BL numbers are from the recorded `COUPLED_VENTED_FEM_BEM_LEM` CPU cases. The
transducer **shape** remains BL's provider default in every case (R2); the real 12PR300 T/S is
used in #4/#6. Bassbox uses the same 12PR300 T/S with the real Sd. Nothing below is a measurement.

## Cases and boxes

| | Seed box #4/#5 | Default box #6/R0 |
|---|---|---|
| BL case | `ev_lf_motor_real/…30640` (real), `ev_lf_demo_twin/…23196` (demo) | `ev_lf_default_real/…45416` (real), `ev_lf_default_demo/…01448` (demo) |
| External W×H×D | 371.2 × 371.2 × 1078.79 mm | 320 × 500 × 360 mm |
| Wall | 18 mm | 18 mm |
| BL meshed air volume | **0.117201504 m³** | **0.042169450 m³** |
| Bassbox Vb | 115.0 L | 42.169450 L |
| BL port source | area 45.0 cm², **total length incl. lips 0.081229 m**, NFR 0.0 | area 28.274 cm², **total length incl. lips 0.22 m**, NFR 0.12 (provider default) |
| Derivation path | `motor_map.vented_source`: effective length → neck → + both 8 mm lips | BL provider default source (not the `assemble` helper) |

The seed box is the clean comparison: its BL source was derived through the sanctioned
`motor_map.vented_source` path, which already subtracts bassbox's end correction and adds the two
provider lips. The default box used BL's own provider-default source, so its 0.22 m is BL's
total-incl-lips number, not a bassbox effective length.

Bassbox equivalents used here (same 12PR300 T/S, `tools/bassbox.py` defaults `Q_LEAK=7`,
`Q_PORT=10`, `N_END=2`, end correction `0.85 r_eq`):

| Model | Neck | L_eff | Fb |
|---|---:|---:|---:|
| Seed, physical mapping | 65.229 mm | 0.129569 m | **30.00 Hz** |
| Default, physical mapping (0.22 − two 8 mm lips) | 204.0 mm | 0.255000 m | **27.99 Hz** |
| Default, old README mapping (0.22 used as effective) | 169.0 mm | 0.220000 m | **30.14 Hz** |

The provider port is flared (NFR 0.12, 8 mm roundover); a straight-neck `0.85 r_eq` correction is
an approximation, so the default-box Fb is a **range** (27.99–30.14 Hz), not a single truth. The
seed box (NFR 0) is the case where the bassbox derivation is directly applicable.

## BL port-interface velocity

The BL result stores `acoustic:interface-average-normal-velocity` at the port interface. The peak
of `|u|` over 20–200 Hz is shown for orientation only; it is **not** a direct Fb readout (bassbox's
own port-velocity peak also sits below its Fb):

| Case | interface area | \|u\| peak | at |
|---|---:|---:|---:|
| #4 seed, real motor | 0.006528285 m² | 3.935 m/s | 30.398 Hz |
| #5 seed, demo motor | 0.006528285 m² | 4.387 m/s | 24.657 Hz |
| #6 default, real motor | 0.005936796 m² | 2.744 m/s | 24.657 Hz |
| R0 default, demo motor | 0.005936796 m² | 2.630 m/s | 20.000 Hz (grid edge) |

The 20 Hz edge peak in R0 means the 12-point LF grid cannot resolve the default-box port peak;
the dense/mesh controls already show the same limitation.

## On-axis shape difference, BL vs bassbox

Both curves are normalized to their own 20–200 Hz band maximum, so this is a shape comparison, not
a sensitivity claim. BL frequencies are the recorded 12-point LF grid; bassbox is evaluated on the
same frequencies (`[measured, CPU recompute]`).

| Comparison | max \|Δ\| | at | mean Δ | 46–132 Hz Δ |
|---|---:|---:|---:|---:|
| #4 seed real vs bassbox seed | 15.68 dB | 162.2 Hz (BL null) | −3.50 dB | −3.51 … −5.42 dB |
| #5 seed demo vs bassbox seed | 16.47 dB | 162.2 Hz (BL null) | +1.13 dB | +5.33 … −4.32 dB |
| #6 default real vs bassbox neck-204 | 7.38 dB | 30.4 Hz | +1.04 dB | +1.83 … −1.96 dB |
| #6 default real vs bassbox eff-220 | 7.20 dB | 30.4 Hz | +0.98 dB | +1.83 … −1.96 dB |
| R0 default demo vs bassbox neck-204 | 7.44 dB | 20.0 Hz | +3.75 dB | +6.59 … −0.86 dB |

The 162.2 Hz null is present in both seed-box BL cases but not in the lumped model (BL −16.1 dB
vs bassbox −0.5 dB); it is a BL box/port/motor interference feature, not a universal LF feature.
The demo-motor rows are not model-only comparisons (different T/S).

## Attribution of the differences

1. **Transducer shape / Sd (dominant on the seed box).** BL's provider-default moving diameter is
   0.2 m → Sd ≈ 314 cm²; the real 12PR300 Sd is 533 cm². `20 log10(533/314.16) = 4.59 dB`. The
   seed-box real-motor BL curve is −3.5 to −5.4 dB below bassbox over 46–132 Hz, mean −4.75 dB —
   consistent with that single declared difference. Bassbox uses the real Sd; BL cannot until
   R2's real geometry exists.
2. **Port model.** The seed box is NFR 0 and its physical total length is mapped correctly
   (0.081229 m = neck + two 8 mm lips), so the lumped derivation applies. The default box is
   NFR 0.12 with lips; a straight-neck end correction is not exact, and using 0.22 m as either
   the total or the effective length changes Fb by 2.15 Hz (27.99 vs 30.14).
3. **Losses.** BL walls/port are lossless; bassbox carries `Q_LEAK=7` and `Q_PORT=10`. The
   default-box BL curve is +7.4 dB at 30.4 Hz relative to bassbox while it is −1.1 to −2.3 dB
   above 70 Hz; an undamped BL port/box peak against a damped lumped port is the consistent
   explanation. The seed box's +6.2 dB at 30.4 Hz has the same character.
4. **Finite baffle/cabinet.** BL is a coupled 3D BEM/FEM solve of the real box + horn; bassbox is
   an infinite-baffle half-space monopole sum. The box/baffle step and port radiation differ, and
   this term is not separable from (2)–(3) on the existing grid.
5. **Air volume.** Seed: BL 0.117201504 m³ vs bassbox 115.0 L (+1.9 %); default: both
   0.042169450 m³. The seed difference is small (≈0.17 dB) and is recorded, not corrected.
6. **Observation.** BL is 2 m free field; bassbox is 1 m half-space with the README's −6.02 dB
   distance correction. Normalization cancels the level, but not the directivity; at 20–200 Hz
   this is a small term relative to (1)–(3).
7. **Motor mapping.** BL uses the datasheet dry `Mmd` plus the acoustic load from the coupled
   solve; bassbox uses `Mms` (dry + published air load). The mapping is consistent at the
   boundary and is not double-counted; the demo-motor rows are excluded from the model-only
   conclusion.

## R17 mapping fix

`assemble._box_to_vented_source` now inverts bassbox's effective length to the physical neck and
adds both 8 mm provider lips before writing BL's `port_length_m` (total incl. lips). Previously it
passed `derived_effective_port_length_m` through as the total length, which lengthened the BL port
by the end correction. Regression test:
`tests/system/test_assemble.py::test_box_to_vented_source_passes_physical_total_port_length`.

No stored case was changed: the seed cases were already staged through
`motor_map.vented_source`, and the default-box cases used BL's provider default source.

## Conclusion

- The BL-vs-bassbox differences are **explained by declared model differences**, not a solver
  defect. On the clean seed box, the broadband offset is the declared demo-shape Sd deficit
  (4.59 dB); the residual is port/loss/finite-baffle model error.
- Bassbox remains the fast **box-feasibility / F3 / port-velocity screen**. It is not an
  installed-LF reference, and a bassbox F3 must never be relabelled a BL F3 (or vice versa).
- The default-box BL port peak (+7.4 dB at 30 Hz vs the damped lumped port) is a lossless-model
  feature; do not read it as a tuning win.
- R3's LF band stays a separate 20–200 Hz control; box tuning is intentionally not merged into
  the 200–2500 Hz wide grids. The missing audit is now complete. R17's bookkeeping mismatch is
  fixed in code and no stored evidence was invalidated.
- No new solve is needed to close the audit. A future real-shape case (R2) would let the Sd term
  be removed and make the residual attribution quantitative.

## Recompute recipe

```python
import importlib.util, sys
from pathlib import Path
import numpy as np
from hornlab_search.meh.drivers import load_cone
from hornlab_search.system.boundarylab import bl_results as R

spec = importlib.util.spec_from_file_location("bassbox", "tools/bassbox.py")
bassbox = importlib.util.module_from_spec(spec); sys.modules["bassbox"] = bassbox
spec.loader.exec_module(bassbox)
cone = load_cone("faitalpro_12pr300", directory=Path("examples/systems/driver_ts"))
seed = bassbox.Box("vented", 115.0, 30.0, 45.0, 65.229)          # neck = 81.229 - 2*8 mm
default = bassbox.Box("vented", 42.169449931, 30.14, 28.27433388, 204.0)  # 220 - 2*8 mm
run = Path("system_runs/system/ev_lf_motor_real/20261120T053351Z-lf_20_200-30640-c2cf0f62/run")
res = R.read_bl_headless_result(run)
# on-axis field: observation:probe:on_axis_2m; compare dB relative to each curve's band max.
```

Raw `run/*.npz` remain local (gitignored); this document is the committed text evidence.
