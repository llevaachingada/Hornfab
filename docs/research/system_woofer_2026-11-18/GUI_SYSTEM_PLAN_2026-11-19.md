# GUI additions for the horn + vented-woofer system — design plan (2026-11-19)

Status: **G0 built 2026-11-19 (uncommitted in the worktree)**; G1–G4 proposed. G0 as built:
`gui/data_hw.py` (read-only data layer), `gui/static/hw.js` (`#/hw/cases`, `#/hw/case/<exp>/<case>`,
`#/hw/readiness`), the `hw` dispatch in `gui/server.py` (`App(system_store=…)`, default
`<root>/system_runs`), and the committed registry `readiness.yaml`. Changes from the plan below:

- Fidelity labels are declared in `readiness.yaml`, not read from run files. The run files carry no
  label and `bl_results.to_system_response` refuses to guess one; undeclared cases show `UNDECLARED`.
- Geometry is two to-scale 2-D elevations (front x–y, side z–y) with the clearance dimension, not
  `view3d.js`. That module is single-horn and mm/quadrant-specific; a two-body 3-D scene moves to G1.
- Staging failures are labelled `STAGE_FAILED[<error type>]`, not "refused". The runner reports
  BL refusals, its own assertions and adapter bugs the same way (the demo twin #5 carries an adapter
  air-volume assertion, yet was solved through a separate validate).
- The ledger counts what is on disk: 5 solved horn/woofer cases (#1–#5). The handoff summary line
  says "6 solved", but its own table lists 5 solved plus #6 staged.
- Tests: `tests/system/test_gui_hw.py` (14). Companion to `SENIOR_REVIEW_HANDOFF_2026-11-19.md` (risk
register R1–R17, work packages WP1–WP8, owner decisions §7). This plan does not reopen anything
on that handoff's do-not-relitigate list. "GUI purchase/port" stays a non-goal: everything here
extends the existing `hornlab-search gui` (stdlib server + vanilla JS, `127.0.0.1` only); nothing
is ported from Boundary Lab's GUI.

## 0. Hardening landed with this plan (uncommitted in the worktree at write time)

**R16 body clearance → enforced gate.** New `hornlab_search/system/boundarylab/clearance.py`;
`stage._stage` runs it on every two-body staging, after BL validate.

- PASS only when the axis-aligned boxes of the placed horn and the enclosure surface are
  ≥ `min_clearance_m` apart (default 1 mm). That gap is a *lower* bound, so a pass is a proof.
- `BODY_CLEARANCE_VIOLATION` when some horn vertex is closer than the minimum to an enclosure
  vertex. That distance is an *upper* bound, so this is also a proof.
- `BODY_CLEARANCE_UNPROVEN` otherwise (boxes overlap, vertices far apart). Refused.
- Any non-PASS verdict sets the staged result to not ok, records `payload.clearance` plus
  `detail.clearance_status` in the immutable manifest, and logs the token.

**Real finding while building it.** `bl_ref_case/20261118T231100Z-assembly-62864-f62bf799`
(0 mm horn offset, staged and BL-validated, never solved) has the horn's rear 3 mm *inside* the
enclosure front plane (vertex minimum 0.7 mm). BL accepted it. Re-checked from disk, it is a
proven `BODY_CLEARANCE_VIOLATION`. The 20 mm case behind the smoke/G4 solves passes with a
proven 17 mm gap; the G6 30 mm cases give 27 mm. No solved result is affected.

Tests: `tests/system/test_clearance.py` has 13 tests (synthetic PASS/VIOLATION/UNPROVEN, scale
and translation order, bad inputs, `_stage` wiring with BL mocked, replay of both real cases
when their gitignored dirs exist). The real-BL test `test_real_bl_stage_horn_project` now
asserts a PASS record; its test-double fallback offset moved 20 → 120 mm, because the 0.2 m
double cube intersected the box at 20 mm. Suite: 274 tests, 0 failures, 0 errors, 7 env-gated
skips (junitxml). The real-BL horn staging test passed with `HORNLAB_BL_REAL_TESTS=1`.

**Remaining WP8 hardening, with no owner decision needed:**
- R12: `tools/system/verify_evidence_quotes.py`.
- R11: a one-command real-BL lane (stage + validate + tiny solve).
- `docs/INDEX.md` / `docs/CODE_MAP.md` entries for the whole `system/` package and these docs.
  Neither file mentions it yet, which breaks the "new doc/module gets a line" rule.

**Held for owner decisions:** R14 authorization record shape (decision 6). R13 guard
unification waits on R1 (decision 3).

## 1. What the GUI must make impossible to misread

These rules come straight from the risk register. Every view below has to satisfy them.
Most are cheap if they are built in from the start and hard to add later.

| Rule | Source | How the GUI enforces it |
|---|---|---|
| Every curve carries its fidelity label | handoff §2 | A badge on every chart and table row: `SCREEN_MAGNITUDE`, `SCREEN_COMPLEX_APPROX`, `INSTALLED_EXTERIOR_BEM`, `COUPLED_VENTED_FEM_BEM_LEM` (`MEASURED_VALIDATED` never appears until it exists). Read from the record, never inferred in JS. |
| Refusals are shown, not hidden | §2, R1, R13 | Refusal tokens (`SENSITIVITY_REFERENCE_MISMATCH`, `MAGNITUDE_ONLY`, `BL_PANEL_FIT_*`, `BODY_CLEARANCE_*`) are shown verbatim in a refusal chip with a one-line plain-English gloss from `glossary.js`. |
| Mixed references never get summed silently | R1 | Woofer (Pa per 2.83 V) and horn (Pa per 1 m/s) are plotted on separate, unit-labelled axes. A summed system curve only renders with a recorded calibration record, and that record is shown next to the curve. |
| Placeholders are loud | §4 | Per-case banners: `DEMO MOTOR`, `DEMO TRANSDUCER SHAPE (MOTOR_GEOMETRY_INCOMPLETE)`, `IDEAL HORN SOURCE (not a compression driver)`, `ANALOG DSP PROTOTYPE`. Driven by manifest fields. |
| No data is not zero | R3 | The 20–200 Hz region is a hatched "not solved" band on every frequency plot until a case has LF data. Box tuning (Fb) is drawn as a marker inside that band so the gap is visible. |
| Observation limits travel with the plot | R5 | Polar and probe plots carry the caption "2 m — not far field at the low end (λ ≈ 1.7 m at 200 Hz); 1-D cuts; no DI/power". The GUI never computes DI from cuts. |
| Unconverged is stated | R6 | A "single mesh, 25 freqs, convergence unchecked" chip until a WP5 refinement record exists for that geometry identity. |
| GUI never starts a solve on its own | §1, R14 | Phase G4 only, and only through the existing job queue with an authorization record. Before then the GUI is read-only plus pure CPU recompute. |

## 2. Information architecture

A new nav group **"Horn + woofer"**, placed between "Bayes" and "System". (The existing "System"
group means GUI/host status, so reusing that name would be confusing.)

```
Horn + woofer
  Cases        #/hw/cases                 ledger of every staged/solved/refused BL case
  Case         #/hw/case/<case-key>       one case: geometry, bases, polars, provenance
  A/B          #/hw/ab?a=<key>&b=<key>    paired delta on identical observation grids
  Screen       #/hw/screen/<study-id>     CPU screen shortlist, Pareto, panel-fit ledger
  DSP bench    #/hw/dsp/<case-key>        LR/PEQ/delay/polarity replay (needs R1 policy)
  Readiness    #/hw/readiness             R1–R17 status + open owner decisions
```

`<case-key>` = `<experiment>/<case-dir-name>` under `system_runs/system/`. It is validated
server-side with the same id-regex plus path-containment pattern `_analysis_file` uses. User
filesystem paths are never accepted.

## 3. Views

### 3.1 Cases ledger (G0)

One row per case dir, built from its `manifest.json` (sha self-check verified on read; a
failed check makes the row a red `MANIFEST_TAMPERED` row, never skipped).

Columns:
- experiment, case, kind
- stage, validate and solve state: `staged`, `validated rc 0`, `solved n/N freqs`, `refused <token>`
- motor: real `12PR300` or `demo`; transducer shape: real or demo
- box: W×H×D, port area, Fb when known
- horn: mesh id, offset, clearance verdict
- band, fidelity label, geometry/assembly id (short hash)

Filters: solved only, horn assemblies only, refused only, motor = real.
Default sort: newest first.

Today's ledger must reproduce handoff §3 exactly (6 solved, 2 staged, 1 refused). That is the
G0 acceptance test.

### 3.2 Case detail (G0 → G1)

Four panels:

1. **Geometry.** Reuse `view3d.js` with two meshes: the horn `.msh` placed by the recorded
   translation/scale, and BL's `exterior.msh`. Overlays: the clearance gap as a dimension line
   with its verdict, the driver/port cutouts on the baffle, and the probe positions as dots.
   Read-only.
2. **Per-excitation bases.** For each excitation port, |p| and phase versus frequency at each
   probe. One small-multiple row per channel, each on its own unit axis. A probe picker drives
   all rows. The LF "not solved" band and the Fb marker follow §1.
3. **Polars.** H and V cuts as the existing dispersion-map heatmap (`charts.js`), one per
   channel, with the §1 observation caption.
4. **Provenance.** Engine (BEAT 0.7.0, Julia, `float32`, quadrature, condensation, symmetry),
   BL version and SHA pins, phasor convention, request/run/log SHA-256s, the BL validate verdict,
   and the motor-mapping cross-checks (Fs/Vas/Mms %) when present. Links to the evidence doc
   section that quotes the case.

Data comes from `bl_results.read_bl_headless_result`, the same reader the evidence used. The
GUI never re-parses `domains.npz` itself.

### 3.3 A/B compare (G2)

This view is for the pairs the handoff already reasons about: motor A/B (#4/#5), the G6 horn
offset (#2/#3), and later the WP2 2×2 matrix.

- The server refuses unless frequency grids, probe sets and excitation ids match (one token per
  mismatch).
- Output: per-probe |B_a / B_b| in dB and Δphase versus frequency, the max relative delta per
  band (LF, XO, HF), and what differs between the two identities (motor, box, horn offset).
- A 2×2 matrix mode (motor × box) lays four cases out on a grid, with each cell linking to its
  pairwise A/B. Empty cells say "staged, not solved" or "not staged".

### 3.4 Screen shortlist (G1)

Reads the deterministic screen study (`27616eedee09009f` today). Three panels:

- **Pareto scatter** of the screen objectives, colour-coded by driver. Hollow markers show cells
  refused by a gate; hovering one shows its token.
- **Ledger table**: every cell, its E_shape and floors/null flags, its panel-fit verdict, and its
  replay hash.
- **Baffle panel-fit diagram** (the most useful single picture for decisions 1 and 2): a
  to-scale front panel with walls, driver cutout and port, plus the separation required versus
  available. It has a toggle between demo transducer dims and real Sd-derived dims. With real
  dims, the 371.2 mm front visibly fails (0.1821 m required vs 0.1501 m available). A
  "front height" what-if slider only re-runs `bl_panel_fit_feasible`, a pure function that
  mirrors BL `parameters.py` lines 100–109. It is labelled "pre-check; BL's validate is the
  authority".

### 3.5 DSP bench (G3, blocked on owner decision 3 / R1)

Interactive LR order and frequency, per-channel gain, delay, polarity and PEQ, applied to a
solved case's complex bases with `combine.recombine_with_dsp`. Mechanics:

- POST `/api/hw/dsp-preview` takes the DSP point plus a calibration record and returns combined
  curves.
- The work is pure CPU, deterministic, and cached by `recombine_cache_key`.
- Without an accepted calibration policy the endpoint returns the `combine()` refusal, and the
  bench shows only per-channel filtered curves.
- Shows `validate_dsp_point` verdicts.

Permanent captions:
- "analog prototype — not a biquad realization"
- "electrical LR4 ≠ acoustic LR4"

Magnitude-only inputs refuse phase-dependent controls (`PHASE_ALIGNMENT_UNAVAILABLE`).

### 3.6 Readiness board (G0)

A table generated from a small committed `readiness.yaml` next to the handoff. It is never
hand-edited in JS. Each row is one risk (R1–R17) with its status (open, in progress, closed),
its evidence path, and the WP it closes under. A second table lists the six open owner
decisions with the handoff's recommendations. This is how the owner sees "what's blocking real
box-axis work" without reading the handoff.

## 4. Backend shape

- **`hornlab_search/gui/data_hw.py`** (new, read-only):
  - `hw_cases(root)`, `hw_case(root, key)`, `hw_basis(root, key, probe)`, `hw_polars(root, key)`
  - `hw_ab(root, a, b)`, `hw_screen(root, study)`, `hw_readiness(root)`
  - Bounded reads with per-file size caps, and mtime+sha-keyed caching like `data.py`.
  - Imports only `hornlab_search.system.*` readers, never BL. Zero solver calls (a test makes
    solver entry points raise, as `test_gui_study_designs_resolver.py` does).
- **`server.py`**: one `hw` head under `get` dispatching to `data_hw`, plus
  `POST /api/hw/dsp-preview` (G3). The existing Host/Origin/JSON guards cover them.
- **`static/hw.js`**: one module exporting the five view functions. `app.js` gains one ROUTES
  block, one nav-active clause and the nav links, and nothing else. This keeps the touch
  surface tiny; see §6.
- **Mesh serving**: reuse the existing `mesh` route's surface reader with a new `hw` source kind,
  so the two-body geometry needs no new 3D code.

## 5. Phasing and acceptance

| Phase | Ships | Needs | Acceptance |
|---|---|---|---|
| **G0** | Cases ledger, case detail (geometry + provenance + bases), readiness board | nothing beyond today's data | Ledger reproduces handoff §3; the 62864 case shows `BODY_CLEARANCE_VIOLATION` (replayed by the server against the stored meshes); every chart has a fidelity badge; LF band hatched; offline tests on fixture case dirs incl. path traversal and tampered manifest |
| **G1** | Polars, screen shortlist, baffle panel-fit diagram | screen study on disk | Diagram reproduces the recorded refusal for the 170 cm² cell and the real-dims 12PR300 failure numbers from the handoff (R2) |
| **G2** | A/B + 2×2 matrix | WP2 solves for a full matrix (the view works on #4/#5 now) | Reproduces the recorded motor A/B 120–144 % and the G6 max rel 0.356–0.575 to the stored precision |
| **G3** | DSP bench | owner decision 3 (R1) + WP4 | No manual recomposition anywhere; G5's recorded recomposition matches the bench byte-for-byte with the same calibration record |
| **G4** | Actions: stage + validate (CPU) as GUI jobs; solve behind an authorization record | decision 6 (R14), the R11 real-BL lane | Preview shows the exact command (existing `preview` pattern); solve is refused without an authorization record; CPU lane lock respected; one GPU job rule untouched |

G0 and G1 are buildable now and depend on no decision.

## 6. Integration constraints (read before building)

- **Branch base.** `feat/woofer-system-v0` branches from `1e9f71b`, which is behind
  `hornfab-all-2026-11-18`. GUI files diverged on that side, and the canonical checkout has
  uncommitted edits to `app.js`, `charts.js`, `sandbox.js` and `view3d.js` that belong to another
  lane. The GUI work should start after `feat/woofer-system-v0` is integrated into
  `hornfab-all-*`, on a branch from there. That is the integrator's call, per R21.
- **Small surface in shared files.** New code goes in `data_hw.py` and `hw.js`. Edits to
  `app.js`/`server.py` stay limited to routing.
- **No new heavy deps.** Charts use the existing `charts.js` SVG helpers and 3D uses the existing
  three.js importmap.
- **No acoustic computation in JS.** Every number shown comes from a Python reader or a pure
  recompute in `system/`. JS only formats and plots.

## 7. Questions for the owner (GUI-specific, in addition to handoff §7)

1. Nav name: "Horn + woofer" (proposed) or fold these views into "Analysis"?
2. Should G0 start before `feat/woofer-system-v0` is integrated, on a branch that later rebases,
   or wait for integration (recommended)?
3. Is a GUI-launched CPU stage + validate (G4, no solve) acceptable once R11's real-BL lane
   exists, or should the GUI stay read-only for this whole system round?
