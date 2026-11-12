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
`(Mms!)` in the tables. When the sheet publishes `Mms` *and* the front free-air load, give both: with
`air_load_g` set, `m = mms_g - air_load_g`, the Mms flag is cleared, and the model mass is the dry Mmd.

## Cone driver in a sealed rear bowl (2026-10-28)

`kind` defaults to `"compression"`, so every earlier driver file gives the same numbers; `kind: "cone"`
adds the paper-cone path used by the cone_plughorn mid driver (research:
`docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md` s4). Nothing here is a new solver, a search term
or a config key - it is the report-only lumped circuit.

| Key | Unit | Meaning |
|---|---|---|
| `kind` | `"compression"` / `"cone"` | driver kind; default `"compression"`, anything else is an error |
| `rear_box_l` | litres | sealed rear bowl's **net** air volume (driver motor volume already subtracted). `Cab = Vb/(rho c^2)`, a series compliance referred to the diaphragm by `Sd^2` |
| `rear_box_q` | - | optional box-loss Q: series acoustic resistance at the driver's fs, `Rr = 1/(2 pi fs Qb Cab)`; [inferred] leak/stuffing model, off by default; must be > 0 |
| `l2_mh` + `r2_ohm` | mH, ohm | semi-inductance LR-2 alternative to a plain `le_mh`: `Z_L = jw Le + (jw L2 R2)/(R2 + jw L2)`; both or neither (an error names the missing one). `drive()` reports `inductance_model` = `"plain"` / `"lr2"` |
| `air_load_g` | g | front free-air load split out of a published `mms_g`; `m = mms_g - air_load_g`, no Mms flag; must be < `mms_g`; only with `mms_g` |
| `rear_air_mass_g` | g | **diagnostic upper bound, default off (0)**: a folded-column mass `rho Vb/Sd^2` in series with `Cab`. This is not the physical sealed-box load (the lumped box is compliance-only; the mass would wrongly raise fs) |
| `f_breakup_hz`, `breakup_exponent` (default 2.0) | Hz, - | [inferred] break-up placeholder: `Sd_eff(f) = Sd / (1 + (f/f_b)^n)`. Applies to the acoustic load (`Sd_eff^2 (Zf + Zr)`) **and** to the radiated volume velocity (`Ud = Sd_eff v`), so the circuit stays lossless. Off when `f_breakup_hz` is omitted |

For `kind: "cone"` the front chamber (`front_chamber_cm3`) must be 0: the cone chamber and throat ring are
already in the BEM mesh, so the circuit must not add a second front compliance (V1 = 0). The model uses
the cone face's area projected on the axis as `Sd`; `z_throat` from the BEM is already averaged over the
driven face.

**Why the LR-2 block?** A 10-inch paper cone's voice-coil impedance is not a plain `Le` above ~1 kHz. The
LR-2 form is standard (Leach/Wright); the values come from the impedance measurement's fit, never from a
guess. **Why the break-up law?** A rigid-piston model is only defensible to ~1-1.5 kHz on a paper cone;
`f_breakup_hz` is a labelled [inferred] placeholder until a laser/accelerometer profile exists - it is an
assumption, not a datasheet value.

**What this section does NOT cover: directivity.** The circuit only produces level, impedance and excursion.
The pattern comes from the BEM solve, whose source is the cone face driven as a **rigid axial piston** at every
frequency. That is defensible to the first cone break-up (roughly 0.7-1.5 kHz on a 10-inch paper cone) and not
to 4 kHz: above break-up the real surface velocity changes sign across the cone, which must produce lobes and
nulls a uniform piston cannot. `Sd_eff(f)` scales radiated area; it cannot change a polar. So every
cone-band pattern/DI number above ~1 kHz is geometry-only until the source model lands - plan and owner
decisions: `docs/CONE_SOURCE_MODEL_PLAN_2026-10-29.md` (NEXT_DEV_PRIORITIES P0b).

**Cone output labels:** `tools/loudness_report.py` marks such a driver `(cone, bowl 6.10 L)`, keeps the
`(Mms!)` flag but says the air-load split is missing, notes the break-up assumption when set, and adds an
`sd_eff_m2` CSV column (the effective area it used). Checks: `kind` alone leaves the compression-path
arrays identical (`np.array_equal`, `z_in` included); a sealed bowl raises the system resonance and lowers
the excursion peak; box-loss plus compliance conserve energy to machine precision; LR-2 tends to 0 (w -> 0)
and to `R2` at high frequency and matches a plain `le_mh` for very large `R2`; `mms_g + air_load_g` equals
the equivalent `mmd_g`; every bad combination in the table above raises `ValueError`.

**The bowl belongs to the horn, not to the driver.** Two horns need two different bowls, so
`tools/loudness_report.py --rear-box-l <L>` overrides `rear_box_l` for every `kind: cone` driver
(it is refused with a warning for compression drivers), and the four stand-in driver files in
`examples/drivers/` deliberately carry no bowl volume. Pass the **net** volume (motor subtracted):
the Evo 7SH CAD's gross 6.14 L and the Evo 2SH's 2.79 L are gross and need the measured motor
volume taken off, per `docs/research/MEASUREMENT_CONE_DRIVER_2026-10-28.md` s2.

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
