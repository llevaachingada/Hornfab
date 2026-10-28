# Horn loudness and the compression-driver model (P12, 2026-10-27)

Report-only. Nothing here changes J, a brief, a config or a solve. Research basis:
`docs/research/SIM_VS_REAL_HORN_2026-10-27.md` s2 and s5B; plan context:
`docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md`.

## Why

The solver drives an ideal throat and every pattern metric is normalised to on-axis, so a horn that is
10 dB quiet at its design frequency still scores well. The stored solve already contains what is needed to
see loudness: the absolute on-axis pressure for a known throat motion, and the throat impedance. **The horn
solve does not depend on the driver** (only on the throat it was meshed for), so any stored horn can be
paired with any driver of that exit size afterwards, with no new solve.

## What you get

| Readout | Needs | Where |
|---|---|---|
| Output gap at f0 (dB short of a loaded throat), lowest loaded frequency (Re z >= 0.5), throat-loading curve, on-axis level per 1 m/s throat velocity | nothing (horn only) | per-run HTML report (`hornlab-search report`), `tools/loudness_report.py` |
| Throat width x height and roundness versus the driver exit | the stored mesh | `tools/loudness_report.py`, `hornlab_search/mesh/throat_check.py` |
| Sensitivity at 2.83 V and at 1 W / 1 m, SPL and excursion at f0, efficiency, maximum SPL (rated power or xmax), electrical impedance | a driver file `examples/drivers/<maker>_<model>.yaml` | `tools/loudness_report.py --driver ...` (CSV has every frequency) |

```
.venv\Scripts\python.exe tools/loudness_report.py --cells-csv docs/data/campaign_v4_2026-10-27/cells_summary.csv --driver examples/drivers/<a>.yaml --driver examples/drivers/<b>.yaml --md out.md --csv out.csv
```

Compare horns on the same driver by **difference**; that is much tighter than any absolute number.

## The model (`hornlab_search/driver/compression.py`)

Standard lumped electro-mechano-acoustic circuit (Akabak / Hornresp / Boundary Lab pattern), rms
quantities, engineering time convention: voice coil `Re + jwLe`; suspension and **dry** moving mass
`Rms + jwMmd + 1/(jwCms)`; optional front (compression) chamber as a shunt compliance; optional rear chamber
(only with an explicit `Cms`, because a published `fs` already includes it); load = the BEM throat
impedance `rho c z / A` over the driven area `A`. The phase-plug channels are short and lossless, so the
effective compression ratio is `Sd / A`. The BEM stores `z` in its own `exp(-iwt)` convention (mass-like
loading has Im z < 0); the model uses `conj(z)` - a test pins that a mass-like load lowers the impedance
peak. On-axis SPL = |stored pressure per unit acceleration| x w x |throat velocity|, taken 1/r from the
stored 2 m to 1 m.

**Use the dry moving mass (Mmd).** An `Mms` that already contains air load double-counts the radiation
mass (Boundary Lab issue #78: 10-20 % low-frequency error); a driver file with only `mms_g` is flagged
`(Mms!)` in the tables.

## How far to trust it

* **Checked [measured]:** energy balance (electrical in = coil heat + suspension loss + acoustic out) to
  machine precision; the textbook matched-load 50 % efficiency; a monopole level chain; on stored solves,
  throat power `0.5 rho c Re(z) A |v|^2` equals the power through the stored 2 m balloon within
  **0.0-0.4 dB from 500 Hz to 8 kHz** on four horns - so the stored data is physically consistent and the
  area bookkeeping (mesh tag area x symmetry copies) is right. Tests: `tests/test_driver_compression.py`,
  `tests/test_metrics_loudness.py`, `tests/test_mesh_throat_check.py`.
* **Valid range [inferred]:** from about fs up to the driver's first internal phase-plug/chamber mode
  (a few kHz for 1.4-2" drivers). Above that use the maker's plane-wave-tube curve. The sensitivity band
  in the tool stops at 4 kHz for that reason.
* **Limits:** linear (no power compression, no distortion); datasheet accuracy (Bl, Mmd, Re) sets the
  absolute error; a free-standing horn in free space (a cabinet baffle adds low-frequency level); the
  ideal flat source above the throat cross-mode (f11).
* **First check against reality, before any print:** put the maker's own reference (published sensitivity
  and condition) in the driver file and compare. **On a print:** measure the driver's electrical impedance
  on the horn and the on-axis level at 2.83 V; both are model outputs.

## Throat rule (owner, 2026-10-27)

Horns are modelled and printed **without a separate throat adapter**. Only the coupling plane (where the
driver bolts on - the solver's source patch) must be round at the driver exit diameter; right after it the
horn may morph, carry ridges/flutes and go non-round, integrated into the geometry. How quickly it may
depart from round has no published number: sources say "gradually" (Geddes US7068805), and ATH's own Core
example starts its morph at the throat with zero amount there (`docs/research/THROAT_COUPLING_2026-10-27.md`). Measured on the v4 winners: OSSE / R-OSSE
`aspect_ratio` also stretches the throat (24 x 36, 26 x 36, 41 x 36, 50 x 36 mm on 36 mm briefs; some
also squarish). Generator families, ATH core and aspect-1 cells solve a round throat of the right size.
Fix for the next nights: lock `aspect_ratio` = 1 in OSSE/R-OSSE cells and shape the mouth with the morph;
later refuse such designs before meshing (needs `search/evaluate.py`, so not while a night runs).

## Driver files

Template with datasheet hints: `examples/drivers/_template.yaml`. Every number comes from the maker's
datasheet with its URL in `source`; nothing is guessed. The GUI's config list skips `examples/drivers/`.
