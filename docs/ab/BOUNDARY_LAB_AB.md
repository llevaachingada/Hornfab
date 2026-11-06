# A/B check: one horn, Hornfab versus Boundary Lab

Date 2026-11-06. Plain-language checklist for the owner and for the local coding agent. Code: `hornlab_search/compare/`
(CLI `hornlab-search ab-bl ...`). Nothing here changes a solver, a default, a hash or a cache key.

**What it answers.** If the *same horn mesh* is solved by Hornfab (our BEAT-based stack) and by Boundary Lab (JW Sound's
BL with the BEAT Engine, run by a friend), do the frequency response, the polar maps, the balloon / DI, the beamwidth and
the throat impedance agree? Agreement from two independent set-ups is the cheapest evidence that neither is silently wrong
(a units slip, a symmetry flag, a sign convention).

## 0. The honest limits first (read this before you spend GPU time)

* **The 8 GB RTX 4060 cannot solve a 20 kHz mesh.** `TOOLCHAIN.md`: full-domain meshes fit only to about **5,500 dofs** on
  CUDA, quarter-domain to about **8,900**. A mesh that resolves 20 kHz is far larger. So "full band, high resolution" on this
  card means: **the highest frequency your mesh resolves** (the export prints it; typically 6 to 10 kHz for the
  mouth sizes we search), on a **dense frequency grid** (1/12 octave) with **dense angles and a dense balloon**. Above that
  frequency the check would be testing mesh error, not solver agreement. The CPU backend has no VRAM limit but costs about a
  minute per frequency from 9k dofs up (`TOOLCHAIN.md`, measured; larger sizes are extrapolated, not measured).
* **Solve the same mesh.** The handoff contains the exact Hornfab mesh mirrored to a *full* mesh (no symmetry, so the friend
  sets nothing) and also the reduced mesh with BL's own `xy` symmetry (`horn_symmetric.blab.json`). Hornfab can solve the full
  mesh (`solve`, needs the CPU backend or a bigger GPU) or the reduced mesh with solver symmetry (`solve --symmetric`, fits
  the 4060). The symmetric-vs-full comparison is itself a useful check of Hornfab's quarter-symmetry handling.
* Nothing in this repository was run against a real Boundary Lab or a GPU while building it. Everything marked
  *verified* below was read from Boundary Lab's source; everything marked *inferred* needs the friend's first run to confirm.

## 1. What is verified and what is assumed about Boundary Lab

Source studied: `github.com/JWSound/boundary-lab`, commit `15f9a89` (2026-11-02, `pyproject` says version 0.5.0 and pins the
BEAT Engine **0.7.0** wheel; our 2026-10-21 notes recorded BEAT 0.6.0, so the engine has moved: record the version your friend
actually runs). Read-only clone, no code executed, nothing installed.

| Topic | Status | Evidence in Boundary Lab |
|---|---|---|
| `.blab.json` schema 10 shape for an exterior BEM model (mesh `bem_surface` with `scale_to_m`, `unbounded_air` region, `rigid` + `moving` boundaries by tag/name, `ideal_velocity_source`, `normal_velocity` port, `symmetry` off/x/xy) | **verified** | `tests/fixtures/remote-exterior.blab.json`, `examples/Simple_Sealed/*.blab.json` |
| `project_preferences` names and meaning (`freq_min/max/count`, `polar_angle_step_deg`, `polar_observation_distance_m`, `spherical_sampling_enabled`, `balloon_angle_precision_deg`, `normalized_channel_correction`, `spl_min/max_db`) | **verified** | `src/blab/project/model.py` |
| Frequency grid = `logspace(log10 min, log10 max, count)` with integer min/max | **verified** | `live.py::build_log_frequencies` (same grid as our `geomspace`) |
| Polar arcs: -180..180 at the step, H in the XZ plane (`x = r sin a`), V in YZ, +Z forward | **verified** | `system_solve.py::_polar_observation_points` |
| Balloon: equal-area Fibonacci sphere, count `round(41253 / a^2)`, `a` clamped 0.5..15 deg | **verified** | `headless.py`, `system_solve.py` |
| Polar text export: one file per angle `H <a>.txt` / `V <a>.txt`, tab separated frequency, SPL **normalized to the 0 degree sample**, optional phase relative to on-axis | **verified** | `exporting/polar.py`, `channel_synthesis.py` |
| On-axis text export: frequency, **absolute** SPL (dB re 20 uPa), phase with the propagation delay `distance / c` removed | **verified** | `exporting/on_axis.py`, `live.py` |
| Balloon export folder: `metadata.json`, `topology.npz` (`freq_hz`, `directions_xyz`), `spl_db.npy` (nf x npoint), **normalized and clipped** to the SPL Min/Max preference | **verified** | `exporting/balloon.py`, `balloon.py` |
| **Normalized Channel Correction (default ON) divides each channel by its on-axis magnitude before export** | **verified** | `channel_synthesis.py::flat_target_corrections`. The project we write switches it off; the friend must check it |
| Phasor convention `exp(+i omega t)`; legacy data conjugated on import | **verified** | `phasor.py`, `docs/Inputs and Outputs.md` |
| Headless solve: `blab project validate|solve PROJECT --request overlay.json --backend ... --output NEWDIR`; run folder `manifest.json`, `domains.json/npz`, `frequencies/NNNNNN.json/npz` with quantity ids `acoustic:pressure:horizontal-polar`, `...:vertical-polar`, `...:sphere`, `acoustic:radiation-impedance` (generalized, N s/m; the radiator domain carries `effective_area_m2`) | **verified** | `docs/advanced/cli-workflow.md`, `headless.py`, `system_solve.py` |
| Normalized impedance shown in BL is `Z / (rho c Sd)` | **verified** | `docs/User Guide.md`, `acoustic_impedance.py` |
| BL solves a **1 m/s** normal velocity; Hornfab a unit normal **acceleration**: `+20 log10(2 pi f)` dB and a conjugate (`solve/phasor.py`, tested against the time domain) | verified (BL docs / our code) | `docs/BOUNDARY_LAB_0.5_RESEARCH.md` section 2 |
| BL opens our generated `.blab.json` unmodified (empty `generator_documents` falls back to defaults in the loader) | **inferred** | never opened in BL; the manual steps in `FOR_YOUR_FRIEND.md` are the fallback |
| Whether the Acoustic Impedance dock can write a text file | **inferred** | a generic tabular exporter exists; the headless run is the sure route for impedance |
| Whether BL pressures are RMS or peak (a 3.01 dB question) | **unverified** | docs say "RMS phasors" for plane plots; the checker flags a 3.01 dB offset if it shows up |
| `ideal_velocity_source` moves the surface along its normal (like our `source_motion: normal`) | **inferred** | fixture default parameters are empty |

If BL cannot be reached or its format changes, the generic CSV importers (`ab-bl import --polar-csv ...`) read any
tool's data; see section 7.

## 2. What counts as a pass

Differences are always **Hornfab minus Boundary Lab**, on a common frequency grid (the coarser side's points inside the
overlap; the other side is interpolated only if its points do not coincide, and the report says so). Each metric is judged per
band (below 1 kHz, 1-5 kHz, 5-10 kHz, above 10 kHz): **PASS** if the largest difference in the band is within the tolerance,
**WARN** if the RMS is within it or the largest is within twice it, **FAIL** otherwise. The overall verdict is the worst
metric. These tolerances are **starting points for a first sanity check, not standards**; change them with
`--tolerances file.json`.

| Metric | Default tolerance | Notes |
|---|---|---|
| On-axis SPL, absolute | 1.0 dB | needs the on-axis export or the headless run (polar files are normalized) |
| On-axis SPL, shape | 1.0 dB | both sides minus their own 1-5 kHz mean (isolates level from shape) |
| Off-axis family 15/30/45/60/90 deg, H and V | 1.5 dB | re on-axis |
| Polar map difference (RMS over angle, points above -30 dB) | 2.0 dB | H and V |
| -6 dB beamwidth, H and V | 5 deg | computed on each side's own angle grid first |
| DI | 0.5 dB | from the balloon on both sides. **A DI from cuts only can never pass** (WARN at best, project rule) |
| Balloon difference (RMS over 1500 equal-area directions, above -30 dB) | 2.0 dB | both sides interpolated by a local quadratic fit; clipped to BL's export range if BL clipped |
| On-axis phase, propagation delay removed | 20 deg | needs complex pressure (Hornfab reference, BL headless run) or BL's on-axis export |
| Relative phase map (within 20 dB of on-axis) | 20 deg | needs complex data |
| Throat impedance real / imaginary (`Z / rho c`) | 0.15 / 0.15 | `exp(+i omega t)`; Hornfab converts its own |

Also expected, and not a failure: float32 rounding (BL writes complex64), a different air density (the project sets
Hornfab's 1.204 kg/m^3; BL's default 1.21 would change level by 0.043 dB), different meshes if the friend re-meshed (do not).

## 3. The five steps (owner, Windows PowerShell, from the Hornfab folder)

Hygiene first for anything that touches the GPU (`CLAUDE.md`, "GPU / Julia hygiene"): one GPU job at a time, close other GPU
programs, and let the tool clear stale hosts (it calls the same code as `gpu-clean`). **Never** run `taskkill /IM julia.exe`.

```powershell
cd <your Hornfab folder>
git pull
# 0. does the tool work here? (no GPU, no Boundary Lab, 10 seconds)
.\.venv\Scripts\hornlab-search.exe ab-bl demo --fake
```
Expect: `none  PASS`, and every injected fault `FAIL` with a named cause. If not, stop and send the output.

**Step 1. Pick a design and write the handoff folder.** A run's best design, or the seed of a config:
```powershell
.\.venv\Scripts\hornlab-search.exe ab-bl export --source runs\<run folder> --rank 0
# or: --source examples\osse_baseline.yaml
```
It prints the workspace (`runs\ab_bl\<label>`), the triangle and dof count, and the highest frequency the mesh resolves. It uses
the design's existing `designs\<hash>\mesh.msh`. For a finer mesh (needs the mesher, can be refused by the dof cap):
`--rebuild-mesh --mesh-f-max 8000 --hi-hz 8000`. The default grid is 1/12 octave from 100 Hz (`--lo-hz`, `--ppo`);
`--hi-hz` defaults to 20 kHz or what the mesh resolves, whichever is lower (whole Hz, Boundary Lab needs that).

**Step 2. Solve the same design in Hornfab (GPU).**
```powershell
.\.venv\Scripts\hornlab-search.exe ab-bl solve --workspace runs\ab_bl\<label> --dry-run     # size and time estimate, no solver
.\.venv\Scripts\hornlab-search.exe ab-bl solve --workspace runs\ab_bl\<label> --symmetric   # quarter mesh + solver symmetry (fits the 4060)
```
Without `--symmetric` it solves the exact full handoff mesh (refused above the dof cap; use `--backend beat_cpu` and
`--max-dof N` to run it on the CPU). Output: `<workspace>\hornfab_reference\` (`response.npz` with complex pressure, `reference_meta.json`,
`abdata\`). The command takes the GPU lock, prints the VRAM baseline, clears stale hosts before and verifies the host is gone after.

**Step 3. Send the folder.** Zip `<workspace>\bl_handoff` and send it. Inside, `FOR_YOUR_FRIEND.md` is click by click.
The friend returns the zipped `results_from_friend` folder.

**Step 4. Drop the results.** Unzip so that the files sit in `<workspace>\results_from_friend\` (`polar\`, `on_axis\`, `balloon\`,
`impedance\` and/or `headless_run\`, plus `NOTES.txt`).

**Step 5. Compare and read the verdict.**
```powershell
.\.venv\Scripts\hornlab-search.exe ab-bl import --workspace runs\ab_bl\<label>     # optional: what was found, in one line
.\.venv\Scripts\hornlab-search.exe ab-bl compare --workspace runs\ab_bl\<label>
start runs\ab_bl\<label>\compare\report.html
```
`compare` writes `report.html` (self-contained, charts embedded), `summary.json`, `verdict.txt`, `comparison_arrays.npz`.
Exit code 0 = PASS, 10 = WARN, 11 = FAIL (report still written), 1 = error. Read the verdict table first, then "Likely causes".

## 4. What the friend needs to decide (listed in `FOR_YOUR_FRIEND.md`)

CPU or CUDA, and the BL version; full project or the symmetric one if memory runs out; Route A (windows) or Route B
(`blab project solve`, cleanest data: raw complex pressure, nothing normalized or clipped, impedance included). Everything else
is fixed in the project file: metres, symmetry off, the frequency list, radius 2 m (or the config's), balloon density,
normalized channel correction off, wide SPL clip range.

## 5. If it fails: what to do for each kind

| You see | Probable cause | What to do |
|---|---|---|
| **Constant on-axis offset of 6.02 dB** | half-space (2 pi) vs full-space (4 pi), or a factor 2 in source amplitude/area | check the BL model has no baffle/infinite plane; check driven area in `handoff.json` against BL's source area |
| **3.01 dB** | RMS vs peak pressure convention | note it; judge with the "shape" row and the normalized metrics |
| **12.04 dB** | factor 4: a quarter model whose source is counted 4 times (or once) in one tool | export again and compare the symmetric project (`xy`) with the full one |
| **60 dB or 120 dB** | mm vs m in distance or area | Meshes scale must be 1; radius in metres |
| On-axis difference has a **+-20 dB/decade slope** | velocity vs acceleration drive, or the `20 log10(2 pi f)` conversion applied twice/not at all | check `reference_meta.json` (`spl_reference`) and BL's source type (`normal_velocity` 1 m/s) |
| Level differs by `20 log10(rB/rA)` | different observation radius | set Polar Observation Distance to the handoff value |
| Phase mirrored | opposite time convention (Hornfab `exp(-i w t)`, BL `exp(+i w t)`) | confirm B is BL-native; do not conjugate a second time |
| Phase off by 180 deg | polarity: source normal flipped | check mesh winding (mirrored images keep outward normals; a hand-edited mesh may not) |
| Phase has a constant delay | different reference distance, or the on-axis file was not propagation-aligned | same radius on both sides |
| Mirrored angles / H and V swapped | sign of the angle axis, or `x`/`y` interchanged | +angle toward +X (H) and +Y (V); H files are named `H *.txt` |
| Beamwidth shifts with frequency (curve scaled) | mesh scale (mm / m / inch) | Meshes scale must be 1 |
| Everything fine up to some kHz, then diverges | the mesh stopped resolving the wavelength (6 elements per wavelength) | lower `--hi-hz`, or re-export with `--rebuild-mesh` |
| Only balloon / DI fail, cuts agree | balloon clipped by BL (SPL Min/Max) or a coarse balloon | project sets -90..30 dB; confirm in Preferences; check the report notes |
| Impedance real part matches, imaginary does not | conjugation or normalization (`Z / rho c Sd`, driven area from `handoff.json`) | use the headless run, which carries the raw value and the area |
| Mild, smooth, frequency-dependent differences (1-3 dB) with no named cause | real solver or mesh differences | open `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md` BL-2; re-run with `solve_precision`/near-correction options on the CPU backend; ask for BL's double-precision run (`request_float64.json`) |

Rule from the project: if a conversion has to be "adjusted" to make a comparison pass, stop and write the closed-form check
first (`tests/test_compare_ab_model.py` shows how). Never adjust a number to match.

## 6. AGENT QUICKSTART (local agent: follow verbatim)

```text
REPO=<the Hornfab folder>; PY=.\.venv\Scripts\python.exe; CLI=.\.venv\Scripts\hornlab-search.exe
0. git pull; run: & $PY -m pytest -q tests\test_compare_ab_model.py tests\test_compare_ab_import.py tests\test_compare_ab_analysis.py tests\test_compare_ab_conventions.py tests\test_compare_ab_report.py tests\test_compare_ab_export.py tests\test_compare_ab_cli.py   (all pass; 1 skipped only if matplotlib is missing)
1. & $CLI ab-bl demo --fake            (expect exit 0; clean case PASS, injected faults FAIL with a cause)
2. GPU hygiene (CLAUDE.md): Get-Process julia (do not kill by name); & $CLI gpu-clean; nvidia-smi --query-gpu=memory.used --format=csv  (desktop ~0.3-0.5 GB; write the number down). One GPU job only.
3. & $CLI ab-bl export --source <run dir | config yaml> [--rank N | --design-hash H] [--rebuild-mesh --mesh-f-max F --hi-hz F]
      read the printed workspace W, the dof count and "mesh resolves up to ...". If it warns the mesh does not reach hi-hz, lower --hi-hz.
4. & $CLI ab-bl solve --workspace W --dry-run ; if est_dof <= the GPU ceiling (full ~5.5k, quarter ~8.9k): & $CLI ab-bl solve --workspace W --symmetric
      (full mesh on GPU only if it fits; otherwise --backend beat_cpu --max-dof N). Exit 3 = GPU busy: wait, do not retry in a loop.
5. Zip W\bl_handoff and give it to the owner (the friend follows FOR_YOUR_FRIEND.md). Wait for results_from_friend.
6. Put the returned files in W\results_from_friend\ ; & $CLI ab-bl import --workspace W ; & $CLI ab-bl compare --workspace W
7. Report: the verdict.txt table, the "LIKELY CAUSES" lines, the notes, and the path W\compare\report.html. Do not change tolerances to get a PASS;
   if you must change one, state the new value and why in the report. Exit code 0 PASS, 10 WARN, 11 FAIL.
8. Hygiene after: Get-Process julia should list nothing from this job (solve ends by shutting its host down and verifying).
Generic data from another tool: & $CLI ab-bl import --polar-csv P.csv --on-axis-csv O.csv --impedance-csv Z.csv --level normalized --distance-m 2 --out DIR ; then compare --bl DIR
```

## 7. Formats the importers read

* **Boundary Lab, window route:** `polar\H <angle>.txt` / `V <angle>.txt` (`freq<TAB>spl_norm[<TAB>phase]`), `on_axis\on_axis*.txt`
  (`freq<TAB>spl<TAB>phase`), `balloon\{metadata.json,topology.npz,spl_db.npy}`, `impedance\*.txt` (`# ` header with Real/Imag columns; a
  physical `N s/m` unit is normalized with the driven area from `handoff.json`).
* **Boundary Lab, headless route:** the `blab project solve` output folder (`manifest.json` ...). When both routes are present the
  headless run is used (raw, complex, unclipped).
* **Generic CSV** (header names exact): polar `freq_hz,plane,angle_deg,spl_db[,phase_deg]` with `--level absolute|normalized`;
  on-axis `freq_hz,spl_db[,phase_deg]`; impedance `freq_hz,z_real,z_imag`. Missing cells are an error; nothing is filled in.
* **Hornfab:** `response.npz` (solve-cache layout, so any cache entry or design folder with a `response.npz` works), converted to the
  canonical basis (1 m/s, `exp(+i omega t)`) on load. Older records that stored only SPL still compare (phase is skipped, with a note).

## 8. Files

| Path | What |
|---|---|
| `runs\ab_bl\<label>\bl_handoff\` | what the friend gets (mesh in metres, `.blab.json` projects, request overlays, frequency list, `handoff.json`, `FOR_YOUR_FRIEND.md`, empty `results_from_friend\`) |
| `runs\ab_bl\<label>\hornfab_reference\` | the Hornfab solve (`response.npz`, `reference_meta.json`, `abdata\`) |
| `runs\ab_bl\<label>\results_from_friend\` | where the friend's files go |
| `runs\ab_bl\<label>\compare\` | `report.html`, `summary.json`, `verdict.txt`, `comparison_arrays.npz` |

`runs\` is not committed. Keep `handoff.json` with any numbers you quote: it holds the mesh hash, driven area, frequency list and
observation set-up. `compare` warns when the Hornfab reference or the BL run used a different mesh hash than the handoff.
