# HornFab — Senior Engineering Decision and Next-Stage Plan

**Date:** 2026-11-19  
**Role:** senior architecture / acoustics / implementation  
**Snapshot:** canonical checkout `C:/Users/hunte/Hrns/hornlab-search`, branch
`hornfab-all-2026-11-18`, HEAD `1dd8053` (plus later local commits; the tree also carries another
lane's uncommitted GUI and ripple work). No GPU job was started and no solve was run for this report.

---

## 1. Verdict

**Keep the architecture. Do not start over.** The repository already has the three things that are
hard to retrofit: a mature horn search engine, a provenance-first system layer, and a GUI that reads
stored evidence rather than inventing it.

What it does **not** yet have is a defensible complete-system prediction. The current system layer is
a **screening and installed-reference scaffold**, not a calibrated two-way loudspeaker model. The
next milestone must therefore be a **bounded reference study**, not more speculative solves:

> one saved horn + one real woofer + one physically buildable cabinet + one declared crossover,
> with consistent complex source references, explicit driver/geometry/calibration records, documented
> LF and numerical limits, and at least one alternative system for comparison.

The single most important architectural change is to stop treating "assembled in Boundary Lab" as a
synonym for "realistic system". Fidelity must be a **multi-dimensional claim** (acoustic model,
driver state, calibration state, numerical confidence), not one label.

---

## 2. What is actually implemented and verified

### 2.1 Verified state at this snapshot

| Item | Verified fact |
|---|---|
| Canonical branch | `hornfab-all-2026-11-18`; HEAD `1dd8053`; 3 later local commits existed ahead of origin at inspection |
| System cases | **37 case dirs: 5 solved, 27 staged/manifest-only, 3 refused, 2 invalid** (`docs/system_data/system_cases.json`) |
| Readiness-declared solve cases | 9: **5 solved** (#1–#5), **2 staged** (#6 real motor/default box, R0 demo/default box), **1 refused** (R4 tower panel fit), plus the 0 mm 62864 case whose clearance violation is declared/proven by R16 replay but is **not** a `payload.clearance` status fact |
| Horn export | **437 designs / 52 `(typology, score-set)` groups**, 437 with acoustic arrays; 807 ndjson / 51,192 rows / 37,588 unique scored physical solves |
| System tests | `tests/system` passes; 7 real-Boundary-Lab tests are env-gated. Targeted pilot/score tests: **25 passed** |
| System export | 37×53 CSV + JSON + 5 screen files / 2 unique studies; manifest integrity 34 verified / 1 known-broken pilot mismatch / 2 unknown |
| GUI | Overview now lands at `#/overview`; P2/P3 views are implemented (some modules still untracked); P4/P5/P6/P8 are backend-only; P7/P9 absent; another lane has uncommitted GUI edits |
| GPU | Not used. A stale GPU lock was observed (holder pid gone); do not solve until `gpu-clean` |

### 2.2 Reconciliation: what is real, local-only, incomplete, or misleading

| Claim | Status | Evidence |
|---|---|---|
| "Six coupled cases solved" | **False** | Five solved; #6/R0 staged; R4 refused; 62864 staged with a prose/R16 clearance finding |
| "System ranking" | **Not implemented, correctly refused** | `combine()` refuses mixed per-input references; no system scalar objective |
| "Pilot Pareto" | **Was silently broken; fixed here** | nested `{value,direction}` axes + list-valued `rules_skips` made every pair unorderable |
| "`pilot --geometry`" | **Was broken; fixed here** | `LF_TS_SCREENING` is not a fidelity; now the valid T/S screening path is used and tested |
| "P4/P5/P6/P8 GUI" | **Backend only** | compare/new/stage/overview endpoints exist; no or incomplete UI wiring |
| "P2/P3 GUI" | **Implemented locally** | `hw_screen.js`/`hw3d.js`/`data_hw_stage.py` are untracked; `app.js`/`hw.js` import them |
| "CODE_MAP P4" | **Doc drift** | names `gui/static/hw_compare.js`, which does not exist |
| "Test count 261/274/355" | **Stale/inconsistent** | quoted counts come from different trees; trust the command you just ran |
| "Inert config keys" | **Confirmed** | `port_nfr_range`, `woofer_center_*`, `horn_mounting_offset_z`, `target.beamwidth_*`, `dsp.active` are parsed but have no demonstrated influence |
| "Manifest integrity" | **Mostly good** | 34 verified; the one mismatch is the known first pilot failure record (immutability), not new corruption |

### 2.3 Defects fixed in this pass

1. **Pilot fidelity label.** Removed the non-existent `LF_TS_SCREENING` call; the pilot's authority is
   `SCREEN_MAGNITUDE`, and installed tiers are refused separately. `pilot --geometry` now runs.
2. **Pilot Pareto contract.** `numeric_axes` are now scalar numbers; directions moved to
   `axis_directions`; **F3 is `-` (minimise)**, not `+`; feasibility contains only booleans;
   `rules_skips` is top-level detail. This matches the `woofer_seed.py` contract.
3. **Contract enforcement.** Added `score.validate_axes()` and call it from `render_report()`.
   Nested numeric axes and list-valued feasibility now raise `SchemaError` instead of silently
   producing an all-Pareto report.
4. **Regression tests.** Added a geometry-path pilot test, scalar-axis/F3-direction test, nested-axis
   schema test, and non-boolean-feasibility test. Targeted suite: **25 passed**; full `tests/system`
   passes with the existing 7 env-gated skips.

This fixes a real analysis bug, not just a test. It does **not** create a system objective.

---

## 3. Fidelity architecture — accepted change

### 3.1 Do not add more fidelity labels; add claim dimensions

The five acoustic labels remain:

`SCREEN_MAGNITUDE → SCREEN_COMPLEX_APPROX → INSTALLED_EXTERIOR_BEM →
COUPLED_VENTED_FEM_BEM_LEM → MEASURED_VALIDATED`.

They answer only "what acoustic model produced this number". They do not answer whether the driver
is real, whether the channels share a reference, or whether the mesh converged. Add four independent,
machine-readable dimensions to every system result/curve:

| Dimension | Values (proposal) | Meaning |
|---|---|---|
| `acoustic_model` | existing five labels | What produced the pressure field |
| `driver_state` | `DEMO`, `TS_ONLY`, `REAL_SHAPE`, `MEASURED` | What we know about the transducer |
| `calibration_state` | `NONE`, `EXPLICIT`, `MEASURED_TRANSFER` | Whether the two channel references are comparable |
| `numerics` | `SINGLE_MESH`, `REFINED`, `FLOAT64_CHECKED` | What convergence/precision evidence exists |

This prevents the central category error: a `COUPLED_VENTED_FEM_BEM_LEM` result with
`driver_state=DEMO`, `calibration_state=NONE`, `numerics=SINGLE_MESH` is an **installed-geometry
reference**, not a realistic HF1440 + 12PR300 sensitivity prediction.

### 3.2 Authority matrix (what may be claimed)

| Evidence state | May claim | Must not claim |
|---|---|---|
| Ideal-source horn geometry | Relative directivity/coverage shape of the horn | Absolute SPL, compression-driver sensitivity |
| Lumped T/S bass | Small-signal F3/Fb/port trends, box feasibility | Port turbulence/compression, nonlinear excursion, installed radiation |
| Magnitude-only compatibility screen | Relative-shape shortlist, deterministic funnel | Phase, delay, crossover sum, system ranking |
| Installed exterior BEM | Installed exterior radiation for the modelled geometry | Complete-system SPL without a driver reference |
| Coupled FEM/BEM | Per-excitation complex bases, installed coupling | Calibrated complete-system response; measured validation |
| Driver-informed electrodynamic | Absolute per-drive response **if** the transfer record exists | A transfer assumed from arbitrary gain |
| Calibrated system sum | Complex system response within the declared calibration scope | CTA/IEC certification, room performance |
| Measured hardware | Validated hardware behaviour within the measurement scope | Generalization beyond the measured units/conditions |

---

## 4. Source-normalization decision (the critical one)

### Decision

**Adopt explicit, typed calibration records as the only path to a coherent two-channel sum.** Do
**not** add a hidden fudge factor, and do **not** call a nominal 1-unit recomposition a system
prediction.

Two tracks, with different claims:

1. **Geometry/directivity track (velocity-referenced).** For radiation-shape, crossover interference
   and polar studies, drive both channels as **normal-velocity** sources (or compare within-channel
   and state the reference). This is a geometry experiment: it can show where the crossover lobing
   and directivity mismatch occur, but it cannot claim absolute sensitivity.
2. **Electroacoustic track (calibrated).** Keep the BL voltage-driven woofer (Pa per 2.83 V) and add
   a declared complex **voltage → throat-velocity** transfer for the horn driver, from measurement or
   a documented driver model. A `CalibrationRecord` carries the per-channel reference, complex
   transfer, method, evidence path, scope and approval. The sum is allowed only when every basis
   shares time convention, distance, angular frame, source geometry hash, and a compatible
   calibration record.

### Rejected alternatives

- **Arbitrary gain matching**: rejected. Matching a curve by eye is not a physical calibration.
- **Treating the exported magnitude data as sufficient for phase work**: rejected. The top-designs
  export intentionally omits `p_h/p_v/p_balloon`; phase work must use the local complex arrays or a
  bounded complex export.
- **Using a BL “demo motor” as if it were the real driver**: rejected. The measured A/B changes the
  woofer pressure basis by **120–144 % per 2.83 V**; the demo motor is not harmless.
- **Adding a sixth fidelity label for calibration**: rejected. Calibration is a separate dimension;
  overloading the acoustic ladder hides the distinction.

### Required reference example before ranking/delay optimization

A CPU-only, independently testable fixture must show, with synthetic complex data:

1. A known two-source sum (amplitude and phase) reproduces exactly.
2. Polarity flip is an exact complex subtraction; delay multiplies by `exp(-iωτ)` with the correct
   sign; no conjugation and no double propagation phase.
3. A mixed-reference response is refused (`SENSITIVITY_REFERENCE_MISMATCH` /
   `PHASE_ALIGNMENT_UNAVAILABLE`).
4. A sum is accepted only with a valid `CalibrationRecord`; the record is shown with the curve.
5. A deliberately wrong calibration flips a known null — the test must fail if the sign/scale is
   wrong.

The existing `test_combine.py` covers much of (1)–(3) on synthetic responses; the missing piece is
the **calibration record** and its accept/refuse behavior.

---

## 5. Physical evidence gaps — priority order

### P0 — LF band (highest value, CPU)

Run a bounded **20–200 Hz** overlay on the existing solved cases #4 (real motor) and #5 (demo twin),
plus one default-box cell after WP2. Compare with `tools/bassbox.py`:

- F3, Fb, port-velocity peak, cone velocity/displacement, phase.
- Record model differences: BL meshed port vs bassbox end correction; NFR 0; lumped vs FEM.
- Acceptance: complete low-frequency manifests; explicit per-frequency deltas; no claim beyond the
  band; a written statement of where bassbox is reliable and where it is not.

### P1 — Motor × box matrix and real-motor assembly

- Solve #6 (real motor, default box) and the demo-default cell → 4/4 matrix on identical geometry.
- Then stage/solve the assembled R2 case with the real 12PR300 T/S (WP3), and A/B against the demo
  assembly. Every assembled result so far uses the demo motor.
- Acceptance: rc-0 validate, 25/25, paired deltas, new identity hashes.

### P2 — Real driver shape and panel fit

The 371.2 mm / 0.1821 m-vs-0.1501 m failure is a **screening warning**, not a final cabinet law.
Need maker CAD/drawings or measurements for:

- effective moving area/diameter; actual cone, surround, dust cap; basket/frame and cutout;
- installation depth; port/brace clearance; horn/woofer body clearance.

Then parameterise the panel-fit screen with real dimensions and re-screen taller/wider fronts
(e.g. 560 mm) and alternative woofer sizes. Acceptance: BL validate rc-0 with real geometry; the
pre-check reproduces BL’s verdict on the refused cell.

### P3 — Numerical and angular validation

One or two representative cases, not hundreds:

- one mesh refinement and one frequency densification near the crossover;
- `float32` vs `float64` at a settled case (deep-null sensitivity);
- observation distance (2 m vs 10 m) and a declared far-field/seat-window policy;
- full-sphere/balloon vs H/V cuts, with DI/power labels.

Acceptance: predeclared tolerances; recorded deltas; a “converged / not converged” chip; no small-J
significance claim before the numerical floor is known.

---

## 6. What the optimization should measure

**Keep horn J and system reporting as separate contracts.** Do not rank historical v6/v7/v9/v10 J
against each other or against a future system score.

### Report-only first

Add physical metrics as report columns/Pareto axes, not a scalar:

- listening-window response and spectral consistency (CTA-2034-B-style window definitions);
- early-reflection and sound-power behaviour (where the data supports it);
- main-lobe integrity and secondary-lobe penalty;
- H/V directivity across the crossover; predicted interference/null sensitivity to polarity/delay;
- LF extension, achievable level, excursion and port-velocity limits;
- cabinet size, fit, printability, mounting practicality;
- robustness across T/S, placement and DSP tolerances.

### Scalar system objective — only after

A scalar is justified only when (a) the calibration record exists, (b) the metric definitions are
declared and tested, and (c) the ranking is stable against the numerical floor. Until then, use
Pareto/report-only. Do **not** invent a “total preference score”; Olive’s regression and CTA-2034-B
are references/definitions, not a universal target.

---

## 7. Search architecture

Near-term, the best verified-candidates-per-compute path is:

1. **Fixed saved horn → woofer/cabinet/XO screen** (current): cheap, deterministic, isolates the
   box/driver/XO variables. Keep it.
2. **Portfolio across saved horns** next: same-budget cells, report disagreements, do not rank by J.
3. **Nested/sequential search**: screen cheaply, verify only the shortlist; audit false negatives.
4. **Robust/multi-objective** after the metrics and numerical floor are declared.
5. **Joint horn + full-system optimization only after** calibration and a cheaper full-system solve;
   otherwise the search will optimize a proxy it cannot defend.

The 437-design export is a discovery asset, not a phase-ready system dataset. For phase-sensitive
reuse, use the original local complex `response.npz` or a bounded complex export with hashes; never
reconstruct phase from the magnitude NPZ.

---

## 8. GUI — trustworthy research interface

Current state: Overview is live; Screens/Cases/Readiness are real; P4/P5/P6/P8 are backend-only;
P7/P9 are absent. The highest-value fixes, in order:

1. **Commit the untracked trio** (`hw3d.js`, `hw_screen.js`, `data_hw_stage.py`) with the tracked
   `app.js`/`hw.js` edits; the tracked diff alone does not boot. Add an import smoke test.
2. **Fix the funnel**: `#/hw/new` is a dead CTA; the screen page still says stage actions “arrive in
   a later phase” although gate C is answered. Either ship the wizard/dialog or remove the dead CTA
   and state the real blocker.
3. **Overview → New system → Screen → Stage/Solve → Compare**: expose the existing backend
   capabilities; keep solve disabled behind decision 6 and the calibration gate.
4. **Make evidence dimensions visible**: acoustic model, driver state, calibration state, numerics,
   solved-vs-staged, data support (frequency/angle), and refusals. A plot must say whether it is a
   separate excitation or a valid combined response.
5. **Preview truth**: the preview must print the command that will actually run.
6. **No new frontend framework**; keep the stdlib server + vanilla ES modules.

---

## 9. What can proceed immediately vs what needs approval

| Work | Status / gate |
|---|---|
| Pilot fidelity/Pareto fix + contract tests | **Done in this pass** (25 targeted tests; full system suite passes) |
| Analytic calibration fixture + `CalibrationRecord` design | **Can start now** (CPU-only, no solve) |
| GUI import/dead-link/preview fixes | CPU-only; coordinate with the GUI lane, do not commit its untracked work blindly |
| LF overlay and 2×2 matrix | CPU `beat_cpu` solves; needs an explicit authorization record and a clean GPU/lock state; **not run here** |
| Real-motor assembled case (WP3) | CPU solve; needs the same authorization; not run here |
| Real driver shape/panel re-screen | Needs maker CAD/measurements (owner/procurement) |
| Numerical/angular validation | CPU solves; needs declared tolerances and owner time budget |
| System ranking / automatic delay optimization | **Blocked** until calibration + numerical floor + owner decision 3 |
| Digital DSP realization | Owner decision 4 |
| Far-field/observation standard | Owner decision 5 |
| 10-inch catalog re-verification | Web/source work; no GPU |

---

## 10. Acceptance criteria for the next milestone

A successful next milestone is a **bounded reference study**, not a feature count:

1. **Source consistency:** both channels carry compatible complex references and an explicit
   `CalibrationRecord`; the analytic fixture passes; no manual gain.
2. **Driver/mounting geometry:** real and placeholder fields are separated; every unresolved field is
   machine-readable.
3. **LF:** 20–200 Hz data exists for the reference cases; bassbox-vs-BL deltas and limitations are
   documented.
4. **Motor/box:** 4/4 matrix and one real-motor assembled case are solved with controlled identities.
5. **Radiation:** meaningful H/V and crossover-region results; observation/far-field limits stated;
   convergence/precision deltas recorded.
6. **Provenance:** immutable manifests, hash-verified exports, regenerable bundles; no staged case
   presented as solved.
7. **Comparison:** at least one alternative system/cabinet is compared on the same declared metrics.
8. **GUI/report:** the evidence, decisions, refusals and remaining uncertainty are visible without
   reading the source.

---

## 11. What remains outside the current model

- Nonlinear motor/thermal behaviour, port turbulence/compression, structural radiation.
- A validated room response; CTA-2034-B/IEC certification (definitions only, not compliance).
- Absolute compression-driver SPL without a voltage→throat-velocity transfer.
- A full-sphere asymptotic far field inferred from 2 m H/V cuts.
- A defensible scalar system preference score before calibration and metric validation.
- A new solver/mesher or a new frontend framework (explicitly out of scope).

---

## 12. Source assessment (use, not title-dropping)

This pass did **not** re-derive the papers; the following is the intended use and the claim limit.
Full-text review is a gate before implementing any new metric/weight.

| Source | Use | Limit |
|---|---|---|
| Gu/You/Shen 2025; multimodal horn shape optimization 2021 | Horn shape/directivity/impedance research framing | Multimodal method, not our BEM; no direct numerical benchmark |
| Dong/Doc/Félix 2024, finite-enclosure horn directivity | Justifies installed-geometry work | Does not validate our mesh/enclosure model |
| Multimodal rectangular horn in enclosure 2023 | Impedance-matching context | Not a system score |
| Makarski, professional horn development | Construction/measurement practice | Not a benchmark for our candidates |
| Thiele 1971; Small 1973 | Vented-box small-signal model (bassbox layer) | Linear, lumped; no port turbulence/nonlinearity |
| Crossover optimizer papers | Multi-objective amplitude optimization context | Mostly magnitude; not phase/calibration |
| Port design paper | Port velocity/compression risk | Does not replace a mesh/CFD model |
| JBL floating waveguide white paper | Manufacturer design claim | Not peer-reviewed; not a validation |
| Sridhar/Tylka/Choueiri 2019 | Constant-directivity metric definitions | Some metrics penalize legitimate narrowing; use selectively |
| Olive 2004 | Listener-preference research context | Room/listener dependent; not a universal target |
| Toole, loudspeakers and rooms | Room/reflection context | Not a single-number target |
| ANSI/CTA-2034-B | Measurement/reporting definitions | Compliance requires the required tests; we have none |
| IEC 60268-21 | Measurement conditions | Not a score |
| Klippel NFS docs | Near-field measurement method | Measurement tool, not a target |

---

## 13. Recommended execution sequence

1. **Now (CPU):** pilot contract fix (done), analytic calibration fixture + `CalibrationRecord`
   proposal, GUI import/dead-link/preview cleanup with the GUI lane, update ACTIVE_STATE/CONTINUITY/
   ISSUES.
2. **After authorization (CPU):** LF overlay (#4/#5 + default box), 2×2 motor×box, real-motor
   assembled R2; record deltas and model limits.
3. **After physical data:** real 12PR300 shape/panel re-screen; taller-front alternative; BL validate.
4. **After calibration:** implement the typed calibration record and the analytic reference test;
   then allow a declared system sum and report-only system metrics.
5. **Only then:** system Pareto/ranking experiments, DSP ranking, and joint horn+system search.

**Owner decisions still blocking the end state:** 1–2 (real geometry/panel policy), 3 (calibration/
sum), 4 (digital DSP), 5 (far-field standard), 6 (solve authorization). Gates D/E remain open.

---

## 14. Change log for this pass

- `hornlab_search/system/optimize.py`: removed the invalid `LF_TS_SCREENING` fidelity call; pilot
  numeric axes are scalar; added `axis_directions` with **F3 = minimise**; feasibility is boolean
  only; `rules_skips` moved to top-level detail.
- `hornlab_search/system/score.py`: added `validate_axes()` and called it from `render_report()`;
  nested axes/list feasibility now raise `SchemaError`.
- `tests/system/test_horn_import.py`: geometry-path pilot test, scalar-axis/F3-direction test.
- `tests/system/test_score.py`: nested-axis and non-boolean-feasibility refusal tests.
- Verified: targeted **25 passed**; full `tests/system` passes with 7 pre-existing env-gated skips;
  `pilot --geometry` CLI now returns a report-only result.
