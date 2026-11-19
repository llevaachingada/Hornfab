# SCREENING_EVIDENCE — Stage-5 fixed-horn seed screen (CPU-only, screen_only)

Date 2026-11-18. Worktree `C:/Users/hunte/Hrns/hornlab-woofer-system-wt`, branch
`feat/woofer-system-v0`. Everything below was executed on this machine from the worktree venv
with CPU thread caps set. **No solver, no GPU, no Julia, no Boundary Lab contact, no write into
`runs/`.** The fidelity cap is `screen_only`; the words "good match" below mean the explicitly
defined relative-shape label, not a validated crossover.

## 1. What drove the shortlist

The screen consumed the real saved horn asset **`0062fb59fbf63eae`** (stored design hash
`9e02db06ecc3`; family FREEFORM; brief `lecleach_rollback_1in_v6`; 12 stored frequencies
500-5500 Hz; stored fields include `p_h`, `p_v`, `p_balloon`, `spl_h_db`, `spl_v_db`,
`spl_balloon_db`, `balloon_dirs`). Under the system contract it is **MAGNITUDE_ONLY** as stored
(unit normal acceleration, `exp(-i omega t)`); this screen uses stored magnitudes only and makes
no phase/delay claim.

The real outer envelope came from the existing full-domain rebuild, not from the illustrative
spec range:

- source: `system_runs/system/ref_case/horn_full/lecleach_rollback_1in_v6_9e02db06ecc3/provenance.json`
- full-domain design hash: **`f04827bc5973`** (`full_params_sha256`
  `89b5d9800d74b41392c74498ef971890d52c2e8578a22b31f159e7196783719e`)
- full bbox (metres): x/y `+/-0.1166727878710462`, z `-0.003 .. 0.1398738872624888`
- envelope used by the placement rule: **233.35 x 233.35 x 142.87 mm**
- envelope identity: `620c91ea7cca89e1`

The derived-legal minimum placing distance therefore is **285.2 mm** for the 317 mm-wide
10-inch cabinets and **312.3-312.7 mm** for the 371-372 mm-wide 12-inch cabinets (cabinet frame
half-height + horn lower half-extent + 10 mm clearance). The illustrative
`woofer_center_y_mm_range [90, 400]` was **not** used as truth.

## 2. Metric specification as implemented

Implemented in `hornlab_search/system/compatibility.py` (report-only extension) and
`hornlab_search/system/piston.py` (relative pattern), with the new seed enumerator in
`hornlab_search/system/woofer_seed.py`.

- Horn relative fingerprint, per plane:
  `L_h,rel(f, dir) = SPL_h(f, dir) - SPL_h(f, on_axis)`, from the **stored** cut arrays
  (`spl_h_db`/`spl_v_db`, falling back to `|p_h|`/`|p_v|` magnitudes) and, only if cuts are
  absent, from the stored balloon. The on-axis sample must exist in the stored grid; a missing
  0-degree sample is a refusal, not an interpolation.
- Woofer relative fingerprint: labelled **ideal rigid rigidly-moving circular piston in an
  infinite baffle**, `D(theta) = 2 J1(x)/x`, `x = k a sin(theta)`, effective
  `a = sqrt(Sd/pi)` from the driver T/S. Continuous normalization at 0 degrees is explicit
  (`D(0)=1`), with a finite reporting floor **-120 dB** and a separate deep-null flag at
  **-40 dB**. This is not a real driver model: no cone breakup, no finite baffle, no cabinet,
  no horn loading.
- Candidate overlap band: for each candidate `f_x`, the stored frequency samples inside
  `[f_x * 2^(-1/3), f_x * 2^(+1/3)]` (a one-third-octave half-width; on the stored
  third-octave asset grid this selects the centre sample plus its two neighbours). The band is
  candidate-specific, not a universal 700-1300 Hz window. A band with fewer than **3 stored
  frequencies** is rejected with an explicit reason; no frequency or angle is interpolated.
- Directions: the listening front region only, H plane `|angle| <= 30 deg`, V plane
  `|angle| <= 15 deg` (from the spec target). H and V are evaluated **separately**; no
  back-hemisphere comparison is made.
- Weights: uniform frequency weights and uniform direction weights by default (overridable and
  recorded in every result).
- `E_shape(f_x, plane) = sum_f w_f [ sum_dir w_dir (L_h,rel - L_w,rel)^2 / sum_dir w_dir ] /
  sum_f w_f`. This is a mean of squared **dB** differences; there is no dB power averaging.
- Uncertainty: the standard error of the per-frequency E contributions
  (`std/sqrt(n_f)`) is reported alongside `n_freqs`, `n_dirs`, weights, band edges and
  `null_fraction`.
- Good-match label: provisional threshold **9 dB^2** (3 dB RMS), only when both accepted planes
  are below threshold and the band has no deep-null samples. The shortlist search region was the
  spec's `xo_hz_range [700, 1300] Hz`.

Refusal tokens remain the existing ones: magnitude-only assets cannot take part in
phase/delay optimisation and `HornAsset.require_complex()` raises
`MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE`.

## 3. Driver catalog delta (machine-fetched, no invented values)

The two new 10-inch pairs were added as new files only; the existing 12PR300/12PR320 files were
not edited.

| driver | source page | Re | Le | Bl | Sd | Xmax | P_AES | Fs | Qms | Mms | Mmd | Cms | Vas | Rms | cutout | depth | OD | Sens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FaitalPRO 10PR300 8 ohm | `https://faitalpro.com/en/products/LF_Loudspeakers/product_details/index.php?id=101040110` | 5.4 | 0.6 | 14.1 | 348 | 4.92 | 300 | 60 | 5.8 | 28.2 | 20.0 | 0.25 | 42.2 | 1.8 | 232 | 115.3 | 261 | 98 |
| FaitalPRO 10PR320 8 ohm | `https://faitalpro.com/en/products/LF_Loudspeakers/product_details/index.php?id=101040140` | 5.3 | 0.57 | 13.5 | 347 | 7.37 | 300 | 48 | 4.6 | 35.0 | 27.7 | 0.31 | 52.7 | 2.3 | 230 | 110 | 261 | 96 |

Fetch/verification notes:

- The FaitalPRO LF listing loads products by a POST to
  `https://faitalpro.com/en/products/LF_Loudspeakers/search.php`; the site's own listing supplied
  the product ids (`10PR300` = `101040110`, `10PR320` = `101040140`). The two detail pages were
  then fetched over TLS with `Invoke-WebRequest` and parsed from their "Technical Parameters"
  tables. **No `BLOCKED_BY_VENDOR_TLS`**: both pages fetched successfully this pass.
- Published values only. `Xmax` uses the page's own definition (winding depth - gap)/2 + gap/3.
- Each new geometry document carries only the publisher-printed installed dimensions
  (`cutout_mm`, `frame_od_mm`, `depth_mm`). Cone depth, surround width, dust-cap diameter and
  mounting depth are **not printed**; they stay absent and installed-tier claims remain refused
  rather than guessed. All four catalog drivers therefore report the same four missing fields,
  with `mounting_depth_behind_baffle_mm = None`.
- Catalog load result: **4 loaded, 0 rejected**. Files and SHA-256s are recorded in the seed JSON
  under `catalog` and `input_sha256.drivers`.

## 4. Enumeration and counts

Command (exact):

```
.venv\Scripts\python.exe -m hornlab_search.system.woofer_seed --asset-id 0062fb59fbf63eae --out system_runs\woofer_seed_stage5 --limit-boxes 8 --shortlist-size 6
```

It reuses `bass_reference.feasible_boxes` (the fixed `tools/bassbox.py` lumped model), the
existing fabrication rules for port/brace/wall, the real horn envelope above, and the
compatibility shape screen. Boxes are sampled deterministically across the feasible volume grid
at their lowest and highest feasible tunings, so the LF-extension/port-velocity trade-off is
visible. LF gate: the spec's own **F3 <= 55 Hz** per driver; it is not derived from horn
beamwidth.

Counts from the generated JSON (`system_runs/woofer_seed_stage5/woofer_seed.json`):

```json
{"boxes_considered": 32, "boxes_rejected": 18, "candidates_kept": 126, "drivers_loaded": 4, "drivers_rejected": 0, "pareto_front_rows": 42, "placements_considered": 126, "placements_rejected": 0, "shortlist_rows": 6, "xo_hypotheses": 42, "xo_rejected": 0}
```

Rejections are kept in `rejected_ledger`, never silently dropped. In this run all 18 box
rejections are the LF gate on small-volume boxes; representative verbatim reasons:

```
f3 59.849 Hz > target 55.000 Hz   (10PR300, 35 L, fb 30.0 Hz)
f3 55.006 Hz > target 55.000 Hz   (one borderline small box, rounded just over)
f3 65.830 Hz > target 55.000 Hz   (12PR300, 35 L, fb 35.83 Hz)
f3 69.531 Hz > target 55.000 Hz   (12PR320, 35 L, fb 65.0 Hz)
```

No XO candidate was rejected by missing data in this run (42 hypotheses, 0 XO rejections), and
no placement was rejected (126 considered, 0 rejected) because the legal `dy` was derived from
the real envelope and every `dz` in `{0, +25, +50} mm` passed the 3-D clearance check. The
placement gate is unit-tested on the 300 mm illegal-spacing case.

Provisional good-match bands (H and V both under 9 dB^2, no deep nulls) were identical for all
four drivers:

| driver | good-match band | hypothesis centres | fallback |
|---|---|---|---|
| 10PR300 | 773.24-1195.8 Hz | 773.24, 961.58, 1195.8 Hz | no |
| 10PR320 | 773.24-1195.8 Hz | 773.24, 961.58, 1195.8 Hz | no |
| 12PR300 | 773.24-1195.8 Hz | 773.24, 961.58, 1195.8 Hz | no |
| 12PR320 | 773.24-1195.8 Hz | 773.24, 961.58, 1195.8 Hz | no |

The 42-row Pareto front spans 61.7 L, 88.3 L and 115 L boxes (12 rows 10PR300, 15 rows 10PR320,
6 rows 12PR300, 9 rows 12PR320). The six-row display is a deterministic diverse subset (one row
per driver, then axis-best, then Pareto fill); it is **not** a ranking and absence from it is
not a rejection.

## 5. Top six seeds (display only, no winner)

| candidate | driver | Vb L | external WxHxD mm | F3 Hz | XO Hz | dy mm | dz mm | E_H dB^2 | E_V dB^2 | port v/limit | excursion margin dB | footprint m^2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `01e7d07d2bf70364` | 12PR320 | 115.0 | 372.0 x 372.0 x 1073.3 | 49.19 | 961.58 | 312.7 | 0 | 0.023 | 0.002 | 2.077 | -2.80 | 0.3993 |
| `1bb2bdc73d3da750` | 12PR300 | 115.0 | 371.2 x 371.2 x 1080.7 | 49.72 | 961.58 | 312.3 | 50 | 0.024 | 0.002 | 1.291 | -8.43 | 0.4012 |
| `23d53b6edd132c63` | 10PR320 | 61.7 | 317.0 x 317.0 x 839.2 | 51.38 | 1195.8 | 285.2 | 25 | 0.136 | 0.010 | 1.428 | -3.37 | 0.2660 |
| `6d8fe6f8041a8aa7` | 10PR320 | 115.0 | 317.0 x 317.0 x 1508.2 | 30.65 | 1195.8 | 285.2 | 0 | 0.136 | 0.010 | 1.683 | -4.80 | 0.4781 |
| `86eead4bf0753ec6` | 10PR300 | 115.0 | 317.0 x 317.0 x 1511.5 | 46.64 | 1195.8 | 285.2 | 50 | 0.135 | 0.010 | 0.925 | -9.23 | 0.4792 |
| `9ba3c003cab82690` | 12PR320 | 88.3 | 372.0 x 372.0 x 838.7 | 53.15 | 961.58 | 312.7 | 50 | 0.023 | 0.002 | 1.833 | -1.71 | 0.3120 |

How to read this table:

- `E_H`/`E_V` are relative-shape mean-squared dB differences over the stored XO overlap band.
  They are small because within the listening window the stored horn and the ideal piston have
  similar **relative** patterns at 773-1196 Hz. They say nothing about absolute level, phase,
  delay, or whether an LR4 crossover at that frequency sums correctly.
- `port v/limit` is the worst peak port velocity at the driver's AES voltage ceiling divided by
  `bassbox.PORT_AIR_MPS_MAX` (17 m/s). Values above 1 are a **headroom warning**, not a
  construction rejection; the geometric port-fit rule is the buildability gate.
- The 10-inch cabinets are 317 mm square and the 12-inch cabinets 371-372 mm square. The 115 L
  boxes are tall towers (about 1.07-1.51 m deep in the bassbox external-depth convention); BL's
  own vented-provider validation remains the geometry authority and may reshape them.
- All four drivers have only three of seven installed-geometry fields. No seed claims installed
  BEM fidelity; the "installed" numbers above are lumped LF + ideal-piston shape only.

## 6. Deterministic replay identity

Two independent CLI runs into different output directories produced byte-identical files:

```
study_id: 65f6db3e8c8e8f86
study_id: 65f6db3e8c8e8f86
92254745522C00212282C1B433C8DB9A8FA04F1B82F88C81CA9EF574C4B92D64  ...\seed_replay_a\woofer_seed.json
92254745522C00212282C1B433C8DB9A8FA04F1B82F88C81CA9EF574C4B92D64  ...\seed_replay_b\woofer_seed.json
49F0DA58C6102598036A4A920C1EAB1410ADC4ACDBDC1C3105DA279CDB0AD5B7  ...\seed_replay_a\woofer_seed.md
49F0DA58C6102598036A4A920C1EAB1410ADC4ACDBDC1C3105DA279CDB0AD5B7  ...\seed_replay_b\woofer_seed.md
```

No timestamp or absolute path is serialised into `woofer_seed.json`/`.md`; the study id is
`65f6db3e8c8e8f86`. The unit test `test_identical_inputs_produce_byte_identical_outputs` pins
the same property on synthetic inputs.

## 7. Tests and the SYS-01 check

Commands and verbatim output tails (thread caps set as shown):

```
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"; $env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe -m pytest tests/system/test_woofer_seed.py tests/system/test_compatibility.py tests/system/test_piston.py -q -p no:cacheprovider
```

```
..........................                                               [100%]
```

```
.venv\Scripts\python.exe -m pytest tests/system -q -p no:cacheprovider
```

```
.................................................sss..........s......... [ 30%]
........................................................................ [ 61%]
.....................................................................ss. [ 92%]
..................                                                       [100%]
=========================== short test summary info ===========================
SKIPPED [3] tests\system\test_bl_stage.py:179: real Boundary Lab staging gated off (set HORNLAB_BL_REAL_TESTS=1)
SKIPPED [1] tests\system\test_boundarylab_geometry.py:217: real Boundary Lab generation gated off (set HORNLAB_BL_REAL_TESTS=1)
SKIPPED [2] tests\system\test_reference_cli.py:474: real Boundary Lab workflow gated off (set HORNLAB_BL_REAL_TESTS=1)
```

The required existing red→green SYS-01 check (already fixed at `928488f`) also passes, and was
not re-fixed or re-reported:

```
.venv\Scripts\python.exe -m pytest "tests/test_bassbox.py::test_z_in_ohm_is_voltage_invariant_non_unit_drive" -q -p no:cacheprovider
.                                                                        [100%]
```

New/updated tests cover: piston on-axis unity and the finite/flagged null; H left/right parity
and a deliberate asymmetry scoring worse; H/V kept separate with a deliberate V mismatch scoring
worse; missing frequency/angle refusal (no interpolation); magnitude-only phase/delay refusal
with the existing tokens; 300 mm illegal spacing refused by derived legality; the +x/+z transform
sign convention; a 1000x unit-scale bbox/offset error; an unbuildable port refused; a missing
driver geometry field recorded as `None` rather than guessed; and byte-stable replay.

## 8. Files touched (owned paths only)

Filtered status:

```
 M hornlab_search/system/compatibility.py
 M hornlab_search/system/piston.py
 M tests/system/test_compatibility.py
 M tests/system/test_piston.py
?? examples/systems/driver_geometry/faitalpro_10pr300.yaml
?? examples/systems/driver_geometry/faitalpro_10pr320.yaml
?? examples/systems/driver_ts/faitalpro_10pr300.yaml
?? examples/systems/driver_ts/faitalpro_10pr320.yaml
?? hornlab_search/system/woofer_seed.py
?? tests/system/test_woofer_seed.py
?? docs/research/system_woofer_2026-11-18/SCREENING_EVIDENCE.md
```

The worktree also contains pre-existing modifications/untracked files from the other lanes
(`hornlab_search/system/cli.py`, `reference.py`, `boundarylab/*`, the other research docs,
`NOTES_FOR_SENIOR.md`, etc.). This lane did not edit or stage them. `geometry/rules.py` was not
edited because the ownership list for this lane excluded it; the 3-D placement/collision check is
implemented in `woofer_seed.py` and reuses the existing `rules.check_port_fits`,
`rules.check_driver_and_brace_clearance` and `rules.check_wall_thickness`.

## 9. Remaining work before any Boundary Lab validation

1. **Installed coupled BL solve of a chosen seed**: assemble the full-domain horn above the
   vented cabinet, run BL's `coupled_bem_fem` on the CPU/GPU lane at the candidate overlap band,
   and compare installed H/V patterns and complex phase. This is the first measurement that can
   replace the ideal-piston shape proxy.
2. **BL geometry authority**: run BL's own vented-provider validation on the 115 L tower
   candidates; the bassbox depth/port feasibility is a lumped screen, not a BL mesh verdict.
3. **Installed driver geometry**: add the missing cone depth, surround width, dust-cap diameter
   and mounting depth for the drivers (maker CAD or measurement) before any installed-boundary
   claim.
4. **Absolute level and phase**: establish the compression driver's voltage→throat-velocity
   transfer and the woofer's absolute sensitivity/phase; until then no calibrated SPL, coherent
   sum, delay optimisation or system score is allowed.
5. **Port/headroom validation**: most shortlisted boxes exceed the 17 m/s port convention at the
   AES ceiling; validate port noise/compression or choose a larger port before treating the LF
   headroom axis as sufficient.
6. **Crossover integration**: the good-match band is a relative-shape label; an LR4 acoustic
   crossover needs measured/installed complex responses and a sum test over the actual overlap.

## 10. Closing statement

**The shortlist above is a heuristic fixed-horn screen, not a validated ranking.** It is a
deterministic, CPU-only funnel built from one real saved horn asset, sourced driver data, the
fixed lumped bass model, a labelled ideal-piston shape proxy and an explicit placement rule. It
does not claim a coherent system response, absolute SPL, installed directivity, port turbulence,
or a final crossover. BL validation is the next gate.

## 11. BL-generator panel-fit pre-check (hardening, 2026-11-19)

### 11.1 Recorded refusal

The parent's R4-class staging of the previous top cell (`1bb2bdc73d3da750`: 12PR300, 115 L,
371.2 x 371.2 x 1080.7 mm, 170 cm^2 port) was refused by Boundary Lab's own generator validator:

- case: `system_runs/system/bl_r4_tower_box/20261119T001041Z-ref_case-40216-b32bb5a2/manifest.json`
- verbatim `result.error`: `Driver must fit inside the enclosure walls with 3 mm clearance.`
- traceback: `.../geometry_providers/vented_enclosure/enclosure/parameters.py`, line 103, in `validate`
- BL provider (manifest): git head `15f9a89245a9adfec8c2f0006c164953ce381e58`, `parameters.py`
  sha256 `51f8e82071ce9984ff651d1266a208d2ba51ff0e9df2fcb2edd22ff3cc0d78c5`
- read-only source cited: `C:/Users/hunte/Github/boundary-lab/geometry_providers/
  vented_enclosure/enclosure/parameters.py` - `validate()` lines 100-109, `port_profile()`
  lines 46-73, demo defaults `FIELDS` lines 14-26 / `DEFAULTS` line 33.

### 11.2 Rule and the recorded arithmetic

BL's validator (lines 100-109) uses external width/height/depth `w/h/d`, wall `t`, driver
(moving) radius `r`, port outer radius `r_p`, and front-panel vertical centres `driver_y`,
`port_y`:

- each component: `radius + 0.003 < w/2 - t` and `abs(y) + radius + 0.003 < h/2 - t` (line 102,
  `>=` rejects);
- `abs(driver_y - port_y) > r + r_p + 0.003` (line 104, strict `>`, `<=` rejects);
- `length <= t + lip + 0.003` or `length + 2*mouth >= d - t` (line 106);
- `cone_depth + 0.003 >= d - t` (line 108).

For the recorded box, NFR=0: `throat = sqrt(0.017/pi) = 0.073561 m`,
`mouth = throat + 0.008 = 0.081561 m`, `r_p = mouth + 0.003 = 0.084561 m`,
`r = 0.200/2 = 0.100 m`, so the required strict separation is `0.187561 m`. On the 371.2 mm
front, `h/2 - t = 0.1676 m`; the largest legal `|y|` values are `0.0646 m` (driver) and
`0.0800 m` (port), giving a maximum achievable separation of `0.144639 m < 0.187561 m`.
**No legal `y` pair exists on that panel.** BL's literal first failure at the supplied demo
offsets (`driver_y=+0.100`, `port_y=-0.130`) is the driver wall check
(`0.100 + 0.100 + 0.003 = 0.203 >= 0.1676`); the port wall check also fails
(`0.130 + 0.084561 + 0.003 = 0.217561 >= 0.1676`). The new pre-check returns the
separation token because that is the binding geometric cause; the verdict is still BL's
verdict (refuse).

### 11.3 Implementation and screen wiring

`hornlab_search/system/woofer_seed.py` (owned) adds pure, deterministic
`bl_panel_fit_feasible(box, *, driver_moving_diameter_m=0.200, driver_y_m=0.100,
port_y_m=-0.130, port_wall_m=0.003, port_roundover_m=0.008, cone_depth_m=0.040,
clearance_m=0.003) -> tuple[bool, str | None]`. Defaults are BL's demo plugin defaults
(constants `BL_DEMO_*` / `BL_VALIDATE_CLEARANCE_M`, cited to the source above). It imports and
invokes nothing from BL. Tokens: `BL_PANEL_FIT_DRIVER_WALL`, `BL_PANEL_FIT_PORT_WALL`,
`BL_PANEL_FIT_DRIVER_PORT_SEPARATION`, `BL_PANEL_FIT_PORT_REAR_WALL`,
`BL_PANEL_FIT_CONE_REAR_WALL`, plus contract-gap tokens.

The screen calls it per box through `_bl_panel_fit_for_screen` (each component at its maximum
legal `|y|`, then BL's exact check). Rejected boxes go to `rejected_ledger` with
`stage: "bl_panel_fit"`, the token, the derived `driver_y_m`/`port_y_m` and the box dimensions;
they are counted under `bl_panel_fit_rejected` and are never silently dropped. The gate parameters
are part of `metric_spec`, so the study id changes (schema unchanged).

### 11.4 Re-ranked shortlist

Command (same fixed-horn asset/spec; new output dir):

```
.venv\Scripts\python.exe -m hornlab_search.system.woofer_seed --asset-id 0062fb59fbf63eae --out system_runs\woofer_seed_stage5_blfit --limit-boxes 8 --shortlist-size 6
```

New study id: **`27616eedee09009f`** (previous: `65f6db3e8c8e8f86`). Counts:

```
{"bl_panel_fit_rejected": 11, "boxes_considered": 32, "boxes_rejected": 29, "candidates_kept": 27,
 "drivers_loaded": 4, "drivers_rejected": 0, "pareto_front_rows": 9, "placements_considered": 27,
 "placements_rejected": 0, "shortlist_rows": 6, "xo_hypotheses": 9, "xo_rejected": 0}
```

The recorded cell is in the ledger verbatim as
`faitalpro_12pr300, 115.0 L, [371.2, 371.2, 1080.690776151898] mm, 170.0 cm^2,
BL_PANEL_FIT_DRIVER_PORT_SEPARATION, driver_y=+0.0646 m, port_y=-0.0800 m`. The 11 panel-fit
rejections are all nine sampled 10-inch boxes (317 mm front) plus both 12-inch 115 L / 170 cm^2
boxes (371.2/372 mm fronts). Only 45 cm^2 ports survive on the 12-inch fronts.

Shortlist delta (6 rows before and after; 2 kept, 4 dropped, 4 new):

| candidate | driver | Vb L | external WxHxD mm | port cm^2 | before | after | why |
|---|---|---|---|---|---|---|---|
| `01e7d07d2bf70364` | 12PR320 | 115.0 | 372.0 x 372.0 x 1073.3 | 45 | row 1 | row 1 | kept (panel budget feasible) |
| `1bb2bdc73d3da750` | 12PR300 | 115.0 | 371.2 x 371.2 x 1080.7 | 170 | row 2 | - | dropped: BL panel fit (separation) |
| `23d53b6edd132c63` | 10PR320 | 61.7 | 317.0 x 317.0 x 839.2 | 45 | row 3 | - | dropped: 317 mm front cannot separate |
| `6d8fe6f8041a8aa7` | 10PR320 | 115.0 | 317.0 x 317.0 x 1508.2 | 45 | row 4 | - | dropped: 317 mm front cannot separate |
| `86eead4bf0753ec6` | 10PR300 | 115.0 | 317.0 x 317.0 x 1511.5 | 170 | row 5 | - | dropped: 317 mm front cannot separate |
| `9ba3c003cab82690` | 12PR320 | 88.3 | 372.0 x 372.0 x 838.7 | 45 | row 6 | row 4 | kept (panel budget feasible) |
| `42d171062dcda386` | 12PR300 | 115.0 | 371.2 x 371.2 x 1078.8 | 45 | - | row 2 | new (same 115 L box, 45 cm^2 port) |
| `627b9184c3a26662` | 12PR320 | 115.0 | 372.0 x 372.0 x 1073.3 | 45 | - | row 3 | new (dz = 25 mm variant) |
| `ccedbe0146d6b922` | 12PR300 | 115.0 | 371.2 x 371.2 x 1078.8 | 45 | - | row 5 | new (dz = 25 mm variant) |
| `d972180f3eb1e854` | 12PR320 | 115.0 | 372.0 x 372.0 x 1073.3 | 45 | - | row 6 | new (dz = 50 mm variant) |

Top three after the re-rank (display only; still no winner):
`01e7d07d2bf70364` (12PR320 115 L, 372 x 372 x 1073.3, 45 cm^2, dz 0),
`42d171062dcda386` (12PR300 115 L, 371.2 x 371.2 x 1078.8, 45 cm^2, dz 50),
`627b9184c3a26662` (12PR320 115 L, same box as row 1, dz 25).

Consequence for the next gate: the square bassbox fronts are the blocker, not the LF alignment.
The recorded 371.2 mm front cannot host BL's 200 mm demo driver plus a 170 cm^2 port at any legal
`y`; a height-reshaped 560 mm front passes (unit-tested), and 45 cm^2 ports fit the 371-372 mm
fronts. Any BL staging must use a reshaped/re-oriented cabinet or a smaller port, and the BL
adapter's height/depth mapping is outside this lane (see `NOTES_FOR_SENIOR.md` if it needs a
change).

### 11.5 Tests (this pass)

```
.venv\Scripts\python.exe -m pytest tests/system/test_woofer_seed.py -q -p no:cacheprovider
...............                                                          [100%]
```

```
.venv\Scripts\python.exe -m pytest tests/system -q -p no:cacheprovider
.................................................sss..........s......... [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
.ss.............................                                         [100%]
=========================== short test summary info ===========================
SKIPPED [3] tests\system\test_bl_stage.py:179: real Boundary Lab staging gated off (set HORNLAB_BL_REAL_TESTS=1)
SKIPPED [1] tests\system\test_boundarylab_geometry.py:217: real Boundary Lab generation gated off (set HORNLAB_BL_REAL_TESTS=1)
SKIPPED [2] tests\system\test_reference_cli.py:474: real Boundary Lab workflow gated off (set HORNLAB_BL_REAL_TESTS=1)
```
