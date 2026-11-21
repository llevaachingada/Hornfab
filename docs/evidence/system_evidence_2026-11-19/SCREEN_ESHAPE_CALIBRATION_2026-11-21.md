# Screen E_shape vs installed BEM on the box axis (R7, 2026-11-21)

**Scope.** Risk R7: the stage-5 screen metric `E_shape` (horn-vs-ideal-piston level-shape
mismatch) had no box-axis or driver-family calibration; its 9 dB² "good match" label was
provisional. This is a read-only comparison of the recorded screen study with the recorded
assembled BEM case. No solve was run; no filter, no sum, no score.

**Fidelity.** The BEM case is `COUPLED_VENTED_FEM_BEM_LEM` on the assembled #2 project, real
12PR300 T/S and BL's **demo 200 mm transducer shape** (R2). The screen uses the same saved horn
asset but the real 12PR300 Sd (533 cm²) in its piston proxy. The comparison is therefore
confounded by R2; it is a calibration *check*, not a calibrated correction.

## Inputs

- Screen study: `system_runs/screens/system_evidence_2026-11-19/woofer_seed.json`
  (`study_id 27616eedee09009f`), asset `0062fb59fbf63eae`
  (`runs/20261118T200653Z-screen-31495a/designs/9e02db06ecc3/response.npz`), candidate
  12PR300 + seed box 115 L / 45 cm² / 371.2 mm front.
- BEM case: `system_runs/system/ev_assembled_motor_real/20261120T150709Z-wide_assembled-01612-383da940/`
  (same horn mesh `9b4057c27ba72779dc07bbf4a50f910ea9223fb982f0071cb0fb3139cf49815d`).
- Common front grid: 7 directions −30, −20, −10, 0, 10, 20, 30° (BEM's 10° polar grid; the
  screen asset has a 2.5° grid, so only its matching directions are used).
- Frequencies: the screen's stored band 773.24, 961.58, 1195.80 Hz; BEM uses the nearest stored
  frequencies 785.5785, 969.6137, 1196.7624 Hz (no interpolation).
- Formula: the screen's `E_shape = mean_f mean_dir (L_horn,rel − L_woofer,rel)²` in dB², each
  channel normalized at 0°.

## Result [measured, CPU recompute]

| Evaluation | H plane | V plane |
|---|---:|---:|
| Screen published (25 H dirs / 13 V dirs, 3 freqs) | **0.0242 dB²** | **0.00173 dB²** |
| Screen asset on the common 7-dir grid | 0.0358 dB² | 0.0358 dB² |
| BEM #2 on the common 7-dir grid | **1.607 dB²** | **17.838 dB²** |
| BEM horn vs ideal piston | 0.691 dB² | 3.031 dB² |
| BEM woofer vs ideal piston | 1.159 dB² | 12.391 dB² |

The BEM V-plane woofer pattern is the source of the large V value. At 969.6 Hz its relative
levels on the front grid are `-0.7, +0.6, +0.8, 0.0, -2.1, -5.9, -11.4 dB`; at 1196.8 Hz they
are `+4.2, +3.5, +1.5, 0.0, +1.2, +3.0, +4.0 dB` — an off-axis hump that the infinite-baffle
piston does not produce. The horn V pattern is smooth over the same grid.

## Interpretation

- The screen's `E_shape` is **optimistic on the box axis**: on the common grid the installed BEM
  case is 45× (H) and ~500× (V) larger in dB² than the screen proxy. The provisional 9 dB²
  good-match label is not calibrated on this axis and must not be promoted to a system verdict.
- The comparison is **confounded by R2**: the BEM woofer is the demo 200 mm shape while the
  screen piston uses the real 533 cm² Sd. Part of the V discrepancy is the missing real shape,
  not the metric alone. A true box-axis calibration needs the real-shape case and a denser
  angular grid.
- This does not invalidate the screen's intended use (ranking candidate boxes/drivers on the
  stored horn asset); it bounds the claim. The risk is **quantified but not removed**.

## Follow-up

- Do not use `E_shape` or the 9 dB² label as a system match/verdict; the GUI and research text
  already label it heuristic.
- Re-run this check after a real-shape case exists (R2) and with a 5° or finer front grid; only
  then can the threshold be recalibrated.
- No code or data change is made by this audit.

## Recompute recipe

```python
import numpy as np
from pathlib import Path
from hornlab_search.system import piston
from hornlab_search.system.boundarylab import bl_results as R

a = np.sqrt(533e-4 / np.pi)
angles = np.arange(-30.0, 30.1, 10.0)
screen = np.load("runs/20261118T200653Z-screen-31495a/designs/9e02db06ecc3/response.npz")
# select stored 773.24/961.58/1195.8 Hz and the matching ±30° indices; normalize each row at 0°
# and compare with 20*log10|piston_directivity(f, a, angles)|.
bem = R.read_bl_headless_result(Path(
    "system_runs/system/ev_assembled_motor_real/"
    "20261120T150709Z-wide_assembled-01612-383da940/run"))
# fields: (vented/voltage, excitation:horn) x (horizontal-polar, vertical-polar), nearest freqs.
```
