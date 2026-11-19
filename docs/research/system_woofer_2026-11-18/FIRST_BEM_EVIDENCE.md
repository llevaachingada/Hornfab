# FIRST_BEM_EVIDENCE — first assembled horn + vented-woofer coupled BEM smoke run (2026-11-18)

Scope: real headless Boundary Lab (0.5.0 @ `15f9a89245a9…`) `coupled_bem_fem` solve of the
assembled R2 case — full-domain rebuilt lecleach-brief horn (closed, imported BEM surface) above
the BL vented-enclosure control cabinet, two independent excitations, three frequencies, CPU backend.
Machine: owner's box (8 GB RTX 4060 GPU NOT used — `beat_cpu`; GPU lane held by the unrelated
night job `cd_rrect_2026-11-17` throughout; no GPU contact, no hornlab Julia host started).
What ran, in order: validate-with-request → solve → CPU checks file (`checks.py` → `checks_output.txt`).
Fidelity label of everything below: **installed_ideal_horn_reference** (handoff §W3 normalization note
quoted verbatim at the bottom).

Case directory (immutable, sha-self-checked manifest): `system_runs/system/bl_smoke/20261118T225108Z-smoke-42536-01d15001/`.
Project: `system_runs/system/bl_horn_assembly/20261118T224519Z-assembly-11000-4a85a0f8/case.blab.json`
(model_version 1, produced exclusively through BL's own host path by lane B's `stage.py`; graph
independently re-verified by the orchestrator: `vented/interior` bounded_air (FEM),
`vented/exterior` unbounded_air meshes = [`vented/mesh/exterior`, `mesh:horn`]; 1 interface
`vented/port_interface`; boundaries: cabinet inner_wall rigid / driver moving / port_mouth interface
(+ same on exterior), horn `SD1G0` rigid (5848 tris), `SD1D1001` moving (102 tris) owned by
`component:horn` `ideal_velocity_source`; excitations `vented/voltage` (voltage) +
`excitation:horn` (normal_velocity); symmetry off; no third electrical port; no orphan surface).

## Run 1 — validate with request overlay

RECONSTRUCTED invocation (exact command, not stored in a log):

```
& C:\Users\hunte\Github\boundary-lab\.venv\Scripts\blab.exe project validate system_runs\system\bl_horn_assembly\20261118T224519Z-assembly-11000-4a85a0f8\case.blab.json --request system_runs\system\bl_smoke\20261118T225108Z-smoke-42536-01d15001\smoke_request.json --backend beat_cpu --json
```

Saved verbatim with `Tee-Object` (UTF-16 on disk; decoded copy not needed — quoted fields below
re-read programmatically from the file bytes). Excerpt (fields quoted from
`blab_validate.json`, the full 16-line assumptions list elided here):

```json
  "backend_id": "beat_cpu",
  "backend_requested": "beat_cpu",
  "excitation_port_ids": ["vented/voltage", "excitation:horn"],
  "frequency_count": 3,
  "frequency_max_hz": 1100.0,
  "frequency_min_hz": 250.0,
  ...
  "purpose": "bem_surface", "sha256": "9b4057c27ba72779dc07bbf4a50f910ea9223fb982f0071cb0fb3139cf49815d"  (mesh:horn, 381105 B)
  ...
  "solve_kind": "coupled_bem_fem",
  "symmetry": "off",
  "project_schema_version": 10,
  "valid": true
```

RC=0. The elided middle contains the two cabinet mesh entries and the assumption list (16
statements; verbatim in `blab_validate.json`).

## Run 2 — the solve

RECONSTRUCTED invocation:

```
& C:\Users\hunte\Github\boundary-lab\.venv\Scripts\blab.exe project solve system_runs\system\bl_horn_assembly\20261118T224519Z-assembly-11000-4a85a0f8\case.blab.json --request system_runs\system\bl_smoke\20261118T225108Z-smoke-42536-01d15001\smoke_request.json --backend beat_cpu --output system_runs\system\bl_smoke\20261118T225108Z-smoke-42536-01d15001\run --events ndjson
```

Console stream captured to `blab_solve.log.txt` (PowerShell `Tee-Object`, UTF-16 on disk; quoting
uses the decoded `blab_solve.log.utf8.txt` copy, byte-identity verified by re-decoding). Verbatim:

```
{"event":"started","output":"C:\\Users\\hunte\\Hrns\\hornlab-woofer-system-wt\\system_runs\\system\\bl_smoke\\20261118T225108Z-smoke-42536-01d15001\\run","backend_id":"beat_cpu","frequency_count":3}
{"event":"status","message":"Initializing BEAT Engine"}
{"event":"status","message":"BEAT Engine ready"}
{"event":"status","message":"Submitting solve request"}
{"event":"status","message":"Coupled float32/cpu: assembling 250.0 Hz"}
{"event":"frequency_completed","index":0,"freq_hz":250.0,"solved_count":1,"frequency_count":3}
{"event":"status","message":"Coupled float32/cpu: assembling 700.0 Hz"}
{"event":"status","message":"Coupled float32/cpu: assembling 1100.0 Hz"}
{"event":"frequency_completed","index":1,"freq_hz":700.0,"solved_count":2,"frequency_count":3}
{"event":"frequency_completed","index":2,"freq_hz":1100.0,"solved_count":3,"frequency_count":3}
{"event":"completed","output":"C:\\Users\\hunte\\Hrns\\hornlab-woofer-system-wt\\system_runs\\system\\bl_smoke\\20261118T225108Z-smoke-42536-01d15001\\run","backend_id":"beat_cpu","solved_count":3,"frequency_count":3}
```

Result manifest `run/manifest.json` [measured]: `"status": "complete"`, `completion_mask
[True, True, True]`, `solve_kind "coupled_bem_fem"`, `phasor_convention "exp(+i omega t)"`,
excitation_port_ids `["vented/voltage", "excitation:horn"]`, frequencies
`[250.0, 700.0, 1100.0]`. Engine provenance [measured]: BEAT Engine `version "0.7.0"`, runtime
`julia 1.12.7` + 8 julia threads / 12 BLAS threads, `precision "float32"`, `quadrature_order 2`,
`static_condensation: True`, `symmetry: "off"`, `transducer_reference_voltage_v: 2.83`,
`bem_backend: "cpu"`, runtime "alderlake", manifest/project SHA-256s recorded inside engine provenance.
Per-frequency NPZ quantity ids [measured, 000000.json]: `exterior_pressure` Pa for
horizontal-polar (37 pts), vertical-polar (37 pts) and the 5 point probes; `diaphragm_velocity` m/s,
`voice_coil_current` A, `interface_average_normal_velocity` m/s, `interface_radiated_pressure` Pa —
every array shape `[2, N]`: **axis 0 is the excitation port = the two independent complex bases**.

## Run 3 — CPU physics checks (no new solve; `checks.py` → `checks_output.txt`, UTF-16 on disk, quoting decoded `checks_output.utf8.txt`)

|f_Hz|woofer Pa @ 2.83 V (on-axis 2 m)|horn Pa per 1 m/s (on-axis 2 m)|
|---|---|---|
|250|2.453e-01|6.270e-02|
|700|5.140e-01|1.488e+00|
|1100|3.022e-01|2.515e+00|

Verbatim checks block:

```
--- checks (complex arithmetic, no new solve) ---
f=   250: polarity-flip residual |(h+w)-(h-w)-2w|/|2w| = 0.00e+00 | total(h+w) recomposition residual 0.00e+00 Pa | 0.1ms delay rotation on woofer =  -9.00 deg (expected  -9.00)
f=   700: polarity-flip residual |(h+w)-(h-w)-2w|/|2w| = 0.00e+00 | total(h+w) recomposition residual 0.00e+00 Pa | 0.1ms delay rotation on woofer = -25.20 deg (expected -25.20)
f=  1100: polarity-flip residual |(h+w)-(h-w)-2w|/|2w| = 0.00e+00 | total(h+w) recomposition residual 0.00e+00 Pa | 0.1ms delay rotation on woofer = -39.60 deg (expected -39.60)

700 Hz horn basis dB rel on-axis: ['on_axis:   0.00', 'up30:  -3.32', 'down30:  -2.21', 'horz_right:  -2.03', 'horz_left:  -2.03']
700 Hz woofer basis dB rel on-axis: ['on_axis:   0.00', 'up30:  -6.02', 'down30:   1.49', 'horz_right:  -2.40', 'horz_left:  -2.40']
```

## Addendum 2026-11-18 (same session): G4 wide basis, G5 DSP replay, G6 geometry challenge

**G4 — widened solved grid (parent gate; same immutable R2 project, no code changes between rows):**
25 log-spaced frequencies (200.0 → 2500.0 Hz, `geomspace(200,2500,25)`), same 5 probes +
project-observation H/V polars, `--backend beat_cpu`. Result: `status "complete"`, completion
25/25, `phasor_convention "exp(+i omega t)"`; immutable case + sha-pinned manifest:
`system_runs/system/bl_smoke_wide/20261118T231115Z-g4wide-56836-b5d6490a/` (`manifest.json`
records request/run/log SHA-256s; `kind bl_wide_study_v1`).

**G5 — DSP-only replay on that exact basis (no BL solve called; `g5_dsp_replay.json` in the
same case dir, 12 presets: LR4 @ 700/900/1100 × polarity ±1 × horn delay ±1 ms):**

- polarity-flip arithmetic residual `0.0` (exact, machine precision);
- pure-delay check: ratio of the +1 ms to 0 ms horn filter banks — max phase residual
  `4.898587196589413e-16 rad` vs `exp(-i 2*pi*f*tau)` (correct sign, no conjugation);
- the landed guards refuse the mixed-per-input sum, verbatim recorded:
  reader — `"SENSITIVITY_REFERENCE_MISMATCH: excitation 'vented/voltage' is Pa per 'V_rms' but
  'excitation:horn' is Pa per 'normal_velocity_mps'; these are not comparable sensitivity
  references. Apply the electrodynamic model for the voltage port (or drive both as normal
  velocity) before any coherent sum."`; combine — `cannot coherently sum 'vented/voltage' and
  'excitation:horn': per_input 'V_rms' vs 'normal_velocity_mps'`.
  The preset table is therefore assembled with explicit, recorded per-channel dimensionless
  calibration (installed_ideal_reference; never a calibrated real-driver SPL).
- illustrative installed finding [measured, arbitrary-calibration row]: the LR4@700 unity-gain
  row shows an on-axis interference dip in the 500–1500 Hz band ~23.5 dB below the band max —
  the complex interference physics the magnitude-only screen could not represent. The exact
  dip frequency/depth is calibration-dependent (explicit arbitrary drives), so this number
  demonstrates the capability, it does not rank crossovers.

**G6 — one-geometry-variable challenge (parent gate; `assembly_geometry_id 06ff56a5a1938ec9`
vs `e16869cc3fa7dbfa` at +20 mm):** identical case otherwise; horn mount advance +10 mm
(translation_mm (0,0,30) vs (0,0,20)); staged through the landed reference CLI
(`reference prepare --root C:\Users\hunte\Github\boundary-lab --horn-mesh <full mesh>
--source-group SD1D1001 --translation-mm 0 0 30 --experiment-id bl_g6_offset30 --out
system_runs` → `valid true`, blockers none) and solved with the same wide request via
`reference solve --backend beat_cpu --authorized-by …gate G6…` → rc 0, complete 25/25.
Case: `system_runs/system/bl_g6_offset30/20261118T235110Z-assembly-21668-c17f7cf6/`.
Two real path failures were hit, fixed, and pinned by regression tests
(`tests/system/test_reference_cli.py::test_solve_builds_absolute_argv_and_writes_no_output_dir`):
relative argv paths resolved against the subprocess cwd (doubled case path), and pre-created
output dir refused by BL's crash-tolerant writer.

Paired per-excitation basis delta G4(+20 mm) vs G6(+30 mm), 2 m probes
(`g6_paired_delta.json`, verbatim rows; values = max |B6−B4|/max|B4| over the grid):

| probe | channel | max rel delta | at Hz | rel delta 600–1200 Hz |
|---|---|---|---|---|
| on_axis | woofer_per_2.83V | 0.4839 | 2250.27 | 0.2332 |
| on_axis | horn_per_1_mps | 0.4551 | 2500.00 | 0.3707 |
| up30 | woofer_per_2.83V | 0.2070 | 1641.05 | 0.0755 |
| up30 | horn_per_1_mps | 0.4007 | 2250.27 | 0.1720 |
| down30 | woofer_per_2.83V | 0.5751 | 2250.27 | 0.0636 |
| down30 | horn_per_1_mps | 0.3558 | 2500.00 | 0.1430 |

[measured] A 10 mm physical offset materially invalidates the installed basis — including the
woofer channel, whose field changed although only the horn moved (installed mutual
scattering). Geometry changes ⇒ new solve (new assembly/physics id); DSP changes do not —
exactly the review's G6 hazard, now quantified rather than asserted.

## Interpretation (labels; each number above = a file byte, not a retelling)

- REF-08 [measured]: a real headless assembled coupled solve exists with a complete 3/3
  frequency manifest, per-frequency npz + quantities, engine/hash provenance. Nothing is fabricated
  or interpolated; three frequencies only — this is a smoke run, not a crossover verdict.
- REF-09/10/11 [measured, CPU recomposition on the same bases]: polarity flip reproduces as an
  exact complex subtraction (residual 0.00e+00 = float machine precision), combined = sum of the
  two independent bases recomposes exactly, and a 0.1 ms delay multiplies by exp(−iωτ) with the exact
  signed rotation (−9.00/−25.20/−39.60 deg at 250/700/1100 Hz — no conjugation anywhere).
- Directivity sanity [measured]: horn basis at 700 Hz is smooth within ±30° (−2.0…−3.3 dB) while the
  woofer basis shows the expected cabinet baffle-step vertical asymmetry (up30 −6.02 dB vs down30
  +1.49 dB) — a first installed-geometry (BEM, rigid flange/box) effect, invisible in the earlier
  isolated-horn screens.
- Units honesty [inferred from recorded conventions]: the two bases are NOT comparable
  sensitivity references — woofer is per 2.83 V (`transducer_reference_voltage_v: 2.83`), the horn
  ideal source is per 1 m/s throat normal velocity. Handoff §W3, quoted verbatim:
  "…must NOT label the result a calibrated real-driver complete-speaker SPL until the compression
  driver's complex voltage→throat-velocity transfer is established. Report this as
  installed_ideal_horn_reference."
- Cross-check anchor [inferred]: horn basis level per 1 m/s at 2 m on-axis (e.g. 1.488 Pa at
  700 Hz) is the BEM-computed installed transfer; no cross-model comparison (HornFab isolated
  solution vs BL installed) was done at these three frequencies — that parity belongs to a later
  convergence pass (W4), with matched mesh/source/observation conventions.

## Provenance / reproduce

- Case manifest: `…/manifest.json` (self-checksummed; pins project/request/validate/checks/log
  SHA-256s + run-manifest status). Run result tree `…/run/` written by BL's own
  `HeadlessResultWriter` (project.snapshot.blab.json, compiled-system.json, domains.npz/json,
  per-frequency npz + json, manifest.json).
- Reproduce commands: the two RECONSTRUCTED invocations above with the same immutable inputs.
- The BL clone was not modified at any point (`git -C C:\Users\hunte\Github\boundary-lab status
  --porcelain` clean, HEAD `15f9a89245a9adfec8c2f0006c164953ce381e58`).
- Byte-check status: every quoted block above was compared against its source file (UTF-16 decoded
  via `read_text(encoding='utf-16')` for the two Tee logs; the validate fields were re-read from
  `blab_validate.json` and re-checked as the fields listed). The `.utf8.txt` copies are decode
  artifacts, not the originals.
