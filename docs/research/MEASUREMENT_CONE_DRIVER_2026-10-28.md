# Measurement protocol - paper-cone mid driver + rear bowl (`cone_plughorn`)

2026-10-28. Companion to `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md`. This file is the
**hardware side**: what to measure, with what, in what order, and what tolerance counts as agreement with
the model. The software side lives in `hornlab_search/driver/compression.py` and `docs/DRIVER_MODEL.md`.

Labels follow the repo convention: **[published]** maker sheet, **[measured]** our own number,
**[inferred]** our reasoning, **[unknown]** not established.

**Status:** protocol written, nothing here has been measured yet. Every [measured] number is still
[unknown]. Do not put an unmeasured number into `examples/drivers/*.yaml`.

---

## 0. What the model needs back

| Number | Goes to | Why the model needs exactly this |
|---|---|---|
| `re_ohm` | driver YAML | DC loss, sets efficiency and the 1 W voltage |
| `fs_hz`, `qms`, `qes` (or `rms_kg_s`) | driver YAML | suspension + mechanical loss |
| `bl_tm` | driver YAML | motor; sets the impedance peak and the drive |
| `mmd_g` (dry) or `mms_g` + `air_load_g` | driver YAML | moving mass; the solver supplies the front air load, so Mms must be split |
| `sd_cm2` (projected) | driver YAML | area the BEM face represents |
| `le_mh`, or `l2_mh` + `r2_ohm` | driver YAML | voice-coil impedance above 1 kHz |
| `rear_box_l` (net) | driver YAML | sealed-bowl compliance |
| `rear_box_q` | driver YAML | bowl damping/leakage |
| `xmax_mm`, `power_aes_w` | driver YAML | max SPL (excursion and thermal limits) |
| `f_breakup_hz` | driver YAML | first break-up mode, [inferred] placeholder until measured |
| `cone_r_mm`, `cone_depth_mm`, `post_r_mm`, `front_gap_mm` | `tools/cad/plughorn.py` params | the mesh cone face and the chamber |
| bowl net volume | `rear_box_l` and the CAD cross-check | consistency between CAD and part |

---

## 1. Driver small-signal T/S (free air)

### 1.1 Preparation

1. Break the driver in before anything: 1-2 h at ~1/10 rated power, free air, below 500 Hz
   [inferred: manufacturer practice]. Record the hours.
2. Measure at **one temperature** and record it (T/S drifts ~0.3 %/K in Re and Fs). Note ambient,
   and do not measure a cold driver straight out of a van.
3. Mount the driver **free air, magnet down or horizontal, no baffle**, on a soft support. A table
   under the magnet adds a reflection; a clamped rim adds stiffness.
4. Use a 4-wire (Kelvin) connection if the meter allows it; at minimum, zero the lead resistance
   (short the leads at the driver terminals and record it).

### 1.2 Impedance sweep

- REW / ARTA LIMP / DATS, **20 Hz - 20 kHz, log spacing, >= 200 points**, 2-3 sweeps averaged.
- Small signal: drive at the lowest level the analyser still resolves well (**<= 0.1 V** across the
  driver, or <= 1 mA constant current). Higher levels heat the coil and shift Fs; that is a
  different (large-signal) measurement, useful later but not for the T/S file.
- Calibrate the rig first: a 10 ohm 0.1 % resistor as the reference, and a **short** at the driver
  terminals to remove lead inductance. Without the short, lead inductance lands in `Le`.
- Export the complex impedance (|Z| and phase), not only the magnitude.

### 1.3 Electrical parameters

From the sweep: `Re` = the flat low-frequency |Z| (below Fs, e.g. 20-50 Hz), `Fs`, `Qms`, `Qes`
(REW/ARTA/DATS compute the last three by the standard half-power method, or fit the motional
impedance), `Le` at the maker's stated frequency if one is given.

**Do not stop at a single Le.** A 10-inch paper cone's voice coil is not a single inductor above
~1 kHz [inferred: standard result; the reason the handoff asks for a semi-inductance fit]. Fit the
**LR-2 / semi-inductance block** used by the model:

```
Ze(f) = Re + j*w*Le + (j*w*L2 * R2) / (R2 + j*w*L2)
```

Fit `Le, L2, R2` to the **blocked-coil** impedance (cone clamped, or the sweep above ~5*Fs where the
motion is negligible), 20 Hz - 20 kHz, log-weighted, by least squares on complex Z. Report:
the fitted values, the frequency range used, and the **residual** (max and RMS % of |Z|). A residual
above ~5 % means the model form is wrong for this driver - say so, do not force the fit.
[inferred: LR-2 is a standard empirical form, not a physical model]

### 1.4 Mmd vs Mms (added mass)

The datasheet `Mms` includes the driver's own front and rear air load. The solver supplies the front
air load through the horn, so the circuit wants the **dry** mass `Mmd`.

Added-mass method:

1. Sweep free air -> `Fs`.
2. Add a known mass `m_add` at the cone/dust-cap centre, as close to rigidly as possible: plasticine
   or a small brass disc, weighed to 0.01 g. Use **20-40 % of the expected Mms** (a 10-inch pro mid
   is typically 20-40 g, so 5-10 g; an 8-inch 4-8 g). Too little mass = the Fs shift is inside the
   noise; too much = the suspension becomes non-linear.
3. Sweep again -> `Fs'`.
4. `Mms = m_add / ((Fs/Fs')^2 - 1)`.
5. Repeat with a second, different mass. Two masses that agree within ~5 % is the acceptance test;
   if they do not, the added mass was not rigid, or the suspension is non-linear. Do not average a
   disagreement away - find it.
6. Subtract the **front free-air air load** to get `Mmd`: for a piston in free space the radiation
   mass at low frequency is `M_air = (8/3) * rho * a^3` with `a = sqrt(Sd/pi)` [inferred: standard
   piston result; evaluate at the band centre, not at DC]. Put the result in `air_load_g`; the YAML
   keeps `mms_g` + `air_load_g`, or `mmd_g` directly. State which path was used.

Cross-check: `Vas = rho*c^2*Sd^2*Cms`, and `Cms = 1/((2*pi*Fs)^2*Mms)`. If Vas disagrees with the
maker's figure by more than ~15 %, one of the inputs is wrong (usually Sd or the mass).

### 1.5 Sd

Measure the **effective** diameter to the **middle of the surround** (the standard convention), in two
orthogonal directions, and average. `Sd = pi*(D/2)^2`. Record the raw diameters: a 10-inch with a
wide surround can be 5-8 % off the nominal-area figure, and Sd enters the model squared in the load.

### 1.6 Cone geometry for the mesh

| CAD parameter | What to measure |
|---|---|
| `cone_r_mm` | effective radius, same convention as Sd |
| `cone_depth_mm` | axial distance from cone rim plane to the cone/dust-cap apex |
| `post_r_mm` | radius of the axe-head post at the cone; if no dust cap is removed, this is the flat the fill lands on |
| `front_gap_mm` | axial gap from the cone **rim** to the throat plane in the assembled horn |

Also record: dust cap present/removed, cone angle, surround width, and the **measured gap between the
axe-head fill and the cone** at the rim and at the centre. That gap is the front chamber; a 1 mm error
matters at 4 kHz.

---

## 2. Rear bowl (the back chamber)

### 2.1 Net air volume [measured]

`PlughornParams.rear_chamber_l()` is the **gross** bowl volume with wall thickness removed but with
**no driver** in it. The number the model needs is the **net** volume with the motor, basket and
terminals subtracted.

1. Seal the bowl's driver opening with tape/plate and fill with **dry rice** (or water in a bag) to
   the mounting plane. Weigh the fill, divide by its measured bulk density (measure it: fill a known
   graduated container the same way). Repeat three times, take the spread as the uncertainty.
2. Measure the **motor/basket displaced volume** the same way (bag + rice around the magnet, or water
   displacement with the terminals sealed).
3. `V_net = V_gross_part - V_motor`. Target uncertainty <= 5 %; below that the compliance error is
   under ~0.5 dB in the model.
4. Compare with `rear_chamber_l()` and report both. A CAD-vs-part difference above ~10 % means the
   simplified bowl in the CAD does not match the moulding - the measurement wins.

### 2.2 Compliance and damping

`Cab = V_net / (rho*c^2)`; at 20 C that is `V_net[L] * 7.1e-8` F roughly (compute it in code, do not
use a hand constant).

Damping, two independent routes:

- **Stuffed or not:** record the stuffing (material, mass, where). Unstuffed and lightly stuffed bowls
  are close to lossless at these volumes; a stuffed bowl is not.
- **Measured Qb:** mount the driver in the bowl, sweep the impedance, and read the box resonance
  `Fc` and the system `Qtc` by the same half-power method. Then
  `Vb = Vas / ((Fc/Fs)^2 - 1)` and `1/Qb = 1/Qtc - 1/Qms - 1/Qes`
  [inferred: standard sealed-box relations]. Use the Vb here as a **cross-check** of the rice volume,
  never as a replacement: it inherits every error in Vas and Qms.
- Put the result in `rear_box_q` (the model's series-loss form) and say in the YAML `notes` that it
  was derived from Fc/Qtc, not from a leak measurement.

### 2.3 What the bowl does NOT include

The rear chamber compliance is the **bowl only**. Do not also add the driver's own rear volume: the
published `Fs` already contains it, which is why the model derives `Cms` from `Fs` + mass. Adding both
double-counts the rear compliance exactly the way a published `Mms` double-counts the front air load.

---

## 3. Printed horn validation

Print, assemble, and measure in this order. Every one of these is a **model output**, so each is a
falsifiable check, not a demo.

### 3.1 Impedance in the horn

- Same rig and level as 1.2, driver in the horn + bowl, 20 Hz - 20 kHz.
- Compare against `drive(...)["z_in_ohm"]` fed by the stored BEM `z_throat`.
- Accept: resonance frequencies within 5 %, |Z| at the peaks within 15 %, and the *shape* between
  500 Hz and 4 kHz within 1 dB. A systematic 20 % offset in the peak height is usually Bl or Re, not
  the horn.
- The horn loading shows as a **damped** main resonance and extra small peaks above it. If the model
  shows sharp peaks the mesh's throat impedance is wrong (thin-gap error, see 5.1).

### 3.2 On-axis SPL at 1 W / 1 m

- Free field or a large ground plane; gated far field; mic at 1.00 m on axis, calibrated, with the
  calibration file and the chain recorded.
- 1/24-octave sweep, 200 Hz - 5 kHz; report the drive voltage and the **actual** impedance at each
  frequency if the amp is not ideal.
- Drive at 1 W into the **measured** impedance at 1 kHz, and also at 2.83 V - record both. F1's
  number (112 dB at 4.9 V into 24 ohm) is a 1 W figure, so the 1 W column is the comparable one.
- Accept: mean difference within **±1.5 dB from 300 Hz to 2 kHz** and **±3 dB from 2 to 4 kHz**, with
  the same trend (the model is linear, so it cannot follow a break-up peak; see 3.5).
- Report temperature and humidity. `rho*c` moves ~1 % per 10 K.

### 3.3 Polars

- H and V, every 10 deg, -90 to +90, at 1/3-octave centres 250 Hz - 4 kHz (5 deg steps within
  ±30 deg if the turntable is fast enough).
- Normalise to on-axis for the shape, but keep the absolute data: the model's directivity claim is
  about the shape, and its loudness claim is absolute.
- Accept: -6 dB beamwidth within ±10 % of the model's, and the on-axis level within the 3.2 band.

### 3.4 Excursion

- Laser or dial gauge on the dust cap / cone centre (or a known point), at 0.5 V / 1 V / 2 V,
  100-600 Hz, steady sine, reading **peak-to-peak**; the model reports `excursion_mm_peak`, so
  divide p-p by 2.
- Accept: within ±20 % at the band bottom (below ~400 Hz), degrading above it where the cone is no
  longer a piston.
- Do not exceed `xmax` while doing this; a paper cone that has been over-driven is a different driver.

### 3.5 Break-up

The rigid-piston model stops being true at the first break-up mode. Measure it, do not guess it.

- Accelerometer (small, < 2 g, glued at the cone/dust-cap junction and at the rim) or a scanning
  laser vibrometer if one is available.
- Sweep 200 Hz - 5 kHz at low level; plot rim vs centre velocity.
- Define `f_breakup_hz` as the **lowest frequency where the rim velocity exceeds the centre velocity
  by 3 dB** (or where the mode shape stops being uniform), and record it with its mode shape if you
  can. That single number is what `f_breakup_hz` takes.
- Until this exists, treat every model curve above ~1-1.5 kHz as `[inferred]` and say so in the
  report. The model's break-up law (`Sd_eff = Sd/(1+(f/f_b)^n)`) is a placeholder, not physics.

---

## 4. The order to do it in (one afternoon + one evening)

1. Break-in, temperature, free-air sweep, 4-wire zero (30 min).
2. Blocked-coil sweep for the LR-2 fit (15 min) - do this first, because it needs the cone clamped
   anyway.
3. Added mass, twice (60 min with the glue/plasticine drying).
4. Cone geometry and Sd with calipers (15 min).
5. Bowl rice volume + motor displacement (45 min).
6. Bowl Qb from the impedance shift (30 min).
7. Only now fill the YAML, run `loudness_report --driver`, and compare with 112 / 111 dB.
8. Print, then 3.1-3.5.

---

## 5. Known traps (each one has already burned someone)

1. **The 2.4-2.7 mm axe-head/throat gap** is below the mesh's comfortable gap/edge ratio. Before
   trusting `z_throat`, run the CPU cross-check on one frequency (bempp vs beat, and a finer mesh) and
   check `near_correction`. If the two solvers disagree at the throat, the horn model is wrong no
   matter how good the driver file is.

   **Status 2026-10-29 [measured, partial]:** the 7SH mesh builds at epw 6 (cached at
   `scratch/thin_gap/epw6/mesh.msh`), but the cross-check is blocked twice over: (a) `source_motion:
   axial` is **refused on `bempp_cpu`** (`ConfigError: only implemented for the beat backends`), so the
   bempp route can only test mesh convergence at the wrong (`normal`) drive; (b) a single bempp_cpu
   frequency at ~9k dofs did not finish inside ~20 min on a machine with a solve night running. To
   close it: provision `beat_cpu` (`python -m hornlab_beat_bem.provision --backend cpu`) when the box is
   free, then compare `beat_cpu axial` vs `bempp_cpu normal` on the SAME mesh and vs a finer mesh - the
   mesh-convergence part is the pass/fail, the drive difference is a known offset.
2. **Front chamber double count.** The cone chamber and the throat ring are in the mesh. A cone driver
   file must not also set a front compliance (`front_chamber_cm3`) - the model refuses it on
   `kind: cone` for that reason.
3. **Mms vs Mmd.** A driver file with only `mms_g` is flagged `(Mms!)` in the report. That flag means
   "the front air load is counted twice"; it is not cosmetic.
4. **A single Le** at 1 kHz reads ~30-50 % low on a big paper cone. Use the LR-2 fit.
5. **Lead inductance** measured as driver inductance: short the leads and subtract before fitting.
6. **Nominal vs Re for the 1 W voltage.** 1 W is `sqrt(1*Z_nominal)` in the report, which is the
   convention F1 uses (4.9 V into 24 ohm). Say which convention a number uses, every time.
7. **The motor is not air.** `rear_chamber_l()` is gross. A 10-inch magnet can be 1-2 L.
8. **Free air vs in-baffle.** The model's horn is free-standing in free space. A measurement on a
   large baffle or in a corner is not the same number at low frequency.
9. **A quiet model is not a wrong model.** The BEM drives a unit throat; absolute level depends
   entirely on the driver file. Compare shapes first, then absolute.

---

## 6. Acceptance summary (what "measures like the model" means)

| Quantity | Accept | Fail action |
|---|---|---|
| T/S fit (|Z|, 20 Hz-20 kHz) | RMS residual <= 5 %, peaks within 5 % | refit / check rig |
| Mmd from two added masses | the two values agree within 5 % | find the non-rigidity before trusting it |
| Bowl net volume | <= 5 % vs the rice measurement | re-measure, check the motor subtraction |
| Impedance in horn | peaks within 5 % (f), 15 % (|Z|) | check Bl/Re, then the throat `z` |
| SPL 1 W / 1 m | ±1.5 dB (300 Hz-2 kHz), ±3 dB (2-4 kHz) | check Sd, Mmd split, then the mesh |
| Polars | -6 dB beamwidth within ±10 % | check the throat/gap, then the mesh resolution |
| Excursion | ±20 % below 400 Hz | check Mmd and the horn load |
| Break-up | `f_breakup_hz` measured, then re-run | do not tune the placeholder to fit |

---

## 7. Open items carried from the handoff

- **Cone fill: LANDED 2026-10-29.** The axe head's rear now fills the cone chamber as ONE lofted solid
  with the base; Evo 7SH front chamber **0.848 L gross -> 0.201 L net** (ratio 0.237) and the
  front-chamber cut-off **419 -> 1792 Hz** (`cone_fill: 0` reproduces the old numbers). `tools/cad/plughorn.py`,
  tests 13 + 22 pass. The remaining unknown is the real driver's cone depth, which changes the gap volume.
- **Thin-gap cross-check**: blocked as recorded in s5.1 (`axial` refused on bempp; beat_cpu not provisioned;
  a CPU solve did not finish in 20 min during a night). Re-run when the box is free.
- **No stand-in driver numbers until they are fetched from a datasheet**: the substitute drivers live
  in `examples/drivers/` with their URL in `source`, published values only - four exist now
  (`bc_10mbx64`, `faital_10pr300`, `bc_8mbx51`, `faital_8pr155`). No maker publishes a semi-inductance
  fit, so s1.3 is mandatory for the real driver, not optional.
- **Cone size is still an assumption** in the CAD (10-inch r 105 on the 7SH, r 90 on the 2SH); the
  measurement in 1.5/1.6 replaces it.
- **The bowl is a horn property**: driver files carry no `rear_box_l`; pass the measured NET volume with
  `tools/loudness_report.py --rear-box-l <L>`.
