# Horn + woofer system closeout — senior handoff (2026-11-21)

**Purpose.** Hand this to a senior reviewer/decision-maker. It states what is now implemented,
where the evidence lives, which owner decisions are still open, and what each decision changes in
the code. It also points at the portable CSV bundle so a cloud agent can inspect the actual solve
results without the local `system_runs/` tree.

**Canonical checkout / branch.** `C:/Users/hunte/Hrns/hornlab-search`,
`hornfab-all-2026-11-18`. Closeout code/evidence: `bdc3f037`; closeout log entry: `153788e0`.
No GPU was used by this pass.

---

## 1. What was closed or implemented

| Item | State | Evidence |
|---|---|---|
| **R5a** balloon DI/power | **Done** | `docs/evidence/system_evidence_2026-11-19/BALLOON_DI_POWER_2026-11-21.md` + `.json`; `system/balloon_metrics.py`; real CPU solve `ev_balloon_di/…49358be1`, 3/3 complete |
| **R7a** screen calibration record | **Done** | `SCREEN_ESHAPE_CALIBRATION_RECORD_2026-11-21.json`; `system/screen_calibration.py`; screen 0.035843/0.035833 vs BEM 1.607249/17.837761 dB²; factors 44.84×/497.80×; threshold unchanged |
| **WP6** deterministic funnel ledger | **Done** | `FUNNEL_LEDGER_2026-11-21.md`; `system/funnel.py`; 54 cases / 22 solved, 3 matched shortlist rows, 0 solved two-channel pairs; `FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS` |
| **B22** staging overrides record | **Fixed** | `boundarylab/stage.py`; `test_bl_stage.py` |
| **B26** DSP range gate | **Fixed** | `dsp.py` optional `ranges`; `test_dsp_complex.py` |
| **B30** dead stub | **Fixed** | `optimize.py` |
| **F19** meshio import | **Fixed** | `gui/data_hw.py`; `test_gui_hw_mesh.py` |
| **B18/B19/B28/B29** | **Already fixed** | audited against HEAD; see `BACKEND_CLOSEOUT_2026-11-21.md` |
| **B20/B25/B27** | **Accepted/documented** | B20 front test + bound comment; B25 derived-case bridge; B27 structural independence documented |
| **`system_data` CSV bundle** | **Expanded** | `docs/system_data/` now carries the full 70,457-row result CSV, the 767-row metrics CSV and the 36-row screen CSV |

All closeout evidence is indexed from
[`docs/evidence/system_evidence_2026-11-19/README.md`](evidence/system_evidence_2026-11-19/README.md)
and [`docs/system_data/README.md`](system_data/README.md).

---

## 2. Portable cloud data

`system_runs/` is git-ignored and local. The committed portable views are:

| File | Rows | What a cloud reviewer can answer |
|---|---:|---|
| `docs/system_data/system_cases.csv` | 54 | every case: status, fidelity, motor/shape, box, horn, band, hashes |
| `docs/system_data/system_case_metrics.csv` | 767 | per case/excitation/frequency on-axis level, max, and DI/power where a sphere exists |
| `docs/system_data/system_solve_results.csv` | 70,457 | **the actual solves**: raw complex pressure, magnitude, phase, angle/coords, relative levels |
| `docs/system_data/system_screen_rows.csv` | 36 | flattened screen shortlist rows (box, driver, match error, LF, placement, XO) |
| `docs/system_data/system_screens.json` | 2 studies | verbatim screen documents + rejected ledger |

Regenerate with:

```powershell
.venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
.venv\Scripts\python.exe tools\data\system_solve_results.py --root . --out docs\system_data
```

**Do not** add the two channel bases together. `per_input` is `V_rms` for the woofer and
`normal_velocity_mps` for the horn. A combined system curve needs the calibration policy below
(R1 / decision 3). DI is per-excitation only; the sphere is one 10 m distance, one mesh, and the
demo transducer shape (R2/R5b/R6).

---

## 3. Open owner decisions (with code/evidence hooks)

### Decision 3 — channel-calibration policy (CRITICAL; R1/R13/WP4)
**Question:** explicit per-channel calibration record vs velocity-driven re-solves vs
electrodynamic conversion.

**Recommendation:** explicit calibration records (option a), as in
`docs/HORNFAB_SENIOR_DECISION_2026-11-19.md`.

**Why the code needs it:** `combine.py::_require_compatible` and
`bl_results.assert_shared_sensitivity_reference` refuse a mixed `Pa/2.83 V` + `Pa/(m/s)` sum.
`reference.py::_fidelity_for` and the report labels are ready to carry a record. The new
`balloon_metrics.py` is deliberately per-excitation for the same reason.

**What the record must decide:** reference basis per channel, polarity, relative delay, relative
gain, validity band, provenance (case/project/solve hashes), and whether a calibration is a
measurement or a declared approximation. Also unifies the two guard tokens (R13).

**Research/data basis:** G5 DSP replay (polarity 0.0, delay 4.9e-16 rad, mixed sum refused) in
`FIRST_BEM_EVIDENCE.md`; the 2×2 motor×box deltas and assembled real-motor A/B in
`docs/evidence/system_evidence_2026-11-19/README.md`; the explicit-calibration recommendation in
`HORNFAB_SENIOR_DECISION_2026-11-19.md`.

**Unblocks:** WP4, R13, a coherent crossover sum, DSP ranking, GUI crossover page (G3/P7), and any
system-level scalar metric. **Do not build a system score before this.**

### Decision 5 — far-field / observation standard (HIGH; R5b)
**Question:** distance, angular grid and seat window for declared curves.

**Recommendation:** declare one before any listening-window curve. The new 10 m balloon is a
diagnostic, not that standard.

**Why the code needs it:** the 2 m probes are not asymptotic at 200 Hz (10 m control differs by
1.38 dB / 17.3° after 1/r + propagation correction). `BLObservationSet` and
`balloon_metrics.per_excitation_metrics` can compute DI/power from a sphere, but the repo has no
declared distance/angular-resolution/seat-window policy.

**Research/data basis:** `docs/evidence/system_evidence_2026-11-19/README.md` §Observation
distance; `BALLOON_DI_POWER_2026-11-21.md` (10 m, 5°, 1650 equal-area points, 200/1000/2500 Hz);
Boundary Lab 0.5 sphere contract in `docs/research/boundary_lab_0.5/bl_inventory.md` and
`docs/ab/BOUNDARY_LAB_AB.md`. CTA-2034/ANSI-style listening-window frameworks are the usual
external reference, but a simulation cannot claim certification; the owner must choose the
declared standard.

**What the standard must decide:** distance(s), full-sphere vs H/V cuts, angular spacing
(BL clamps 0.5–15°), equal-area vs structured grid, axis normalization, seat window, and whether
DI/power are report-only or rank-bearing. **Unblocks:** R5b, declared curves, any system directivity
claim.

### Decision 1/2 — real transducer shape and front height (CRITICAL; R2/R7b/WP7)
**Question:** procure 12PR300 drawings now, or accept the demo shape for v0? Allow 560 mm fronts
or keep 371 mm and pick drivers that fit?

**Recommendation:** procure the 12PR300 drawings; it gates real box-axis work. Both height paths
need real geometry first.

**Why the code needs it:** `woofer_seed.py::bl_panel_fit_feasible` uses BL's demo 200 mm shape;
12PR300 needs 0.1821 m separation vs 0.1501 m available on the 371.2 mm front. Every BL-buildable
box is therefore demo-shape-conditional. The R7a calibration and R5a balloon are both confounded
by the demo shape.

**Research/data basis:** live FaitalPRO re-verification (every numeric T/S and mechanical field
matches) in `DRIVER_CATALOG_REVERIFY_2026-11-21.md`; `BASSBOX_MODEL_AUDIT_2026-11-21.md`
(demo-shape Sd deficit 4.59 dB); `BL_PARITY.md`; `woofer_seed.py` panel-fit arithmetic mirroring BL
`parameters.py` 100–109.

**Unblocks:** R2, R7b, real panel fit, taller-front re-screen, a real-shape assembled case.
**Next concrete step:** obtain the maker CAD/mechanical drawing; then parameterise the panel-fit
and re-screen before any new rank.

### Decision 6 — solve authorization record (LOW procedural; R14)
**Question:** per-case token registry vs free-form token.

**Recommendation:** typed record (who/why/scope) written into the case manifest.

**Why the code needs it:** `reference.solve` refuses without `authorized_by`, but the field is a
free string. The GUI solve button is disabled for this reason. CPU evidence solves used a
handoff-string; that is not a registry.

**Research/data basis:** `R11` real-BL lane and `reference.py` refusal behavior; `readiness.yaml`
R14. **Unblocks:** GUI-started solves and a reproducible authorization audit.

### Decision 4 — digital DSP realization (MEDIUM; R8)
**Question:** keep analog prototypes for research, or add digital biquads now?

**Recommendation:** analog for research; biquads later. `dsp.py` is analog-prototype only and
excursion is not a joint constraint. **Unblocks:** R8, digital-latency claims, excursion-aware
optimization. No owner data is needed beyond the choice.

### Decision 3-adjacent / not an owner decision: R7b threshold recalibration
**State:** R7a records the screen→BEM gap; the 9.0 dB² good-match label is unchanged
(`THRESHOLD_UNCHANGED_9DB2`, `recalibrated=false`). Recalibration needs the real shape (R2) and a
5° or finer grid. The G7 false-negative audit cannot run statistically: 0 shortlist candidates
reach a solved two-channel case, and the only candidate-joined solved case is woofer-only. The
funnel ledger now makes that gap explicit. Do not derive a new threshold from n≤1 confounded
cases.

---

## 4. Items for senior review / potential issues

1. **R1 guard unification (R13):** two refusal token families (`combine._require_compatible`,
   `bl_results.assert_shared_sensitivity_reference`) overlap. Unify only when the calibration
   record schema is chosen; do not silently collapse the tokens first.
2. **R7 / G7:** the screen proxy is optimistic on the box axis (45× H, ~500× V in dB² on the common
   grid) and confounded by the demo shape. The funnel has no pairs. If the next round wants a
   false-negative audit, it must generate paired shortlist → solved two-channel cases first.
3. **B23 clearance role coupling:** the R16 gate keys on `purpose == "bem_surface"`. A BL label
   change would fail every horn stage. A declared mesh-role set is the likely fix; it touches the
   BL adapter contract.
4. **B24 fidelity inference:** `_fidelity_for` maps only `solve_kind`; it does not consult geometry
   completeness. This can overstate a label. Acoustic/fidelity semantics need a decision before
   code.
5. **B21 inert spec keys:** `port_nfr_range` only uses its lower bound; placement ranges,
   `beamwidth_*` and `dsp.active` are parsed but not wired. They are documented as reserved; do
   not claim they are effective.
6. **Full-suite verification debt:** the offline profile reached 99% with the documented seven
   pre-existing other-lane failures before a 20-minute shell timeout. `tests/system` (512 passed,
   7 skipped) and the GUI/export neighbours (42 passed) are green. Re-run the full profile on an
   idle machine before a release verdict.
7. **Cross-lane integration:** the closeout code/evidence landed inside the concurrent
   `bdc3f037` commit (the other lane used a broad staging operation). The closeout log entry is
   `153788e0`. The other lane's optimizer/sculpted work remains uncommitted in the tree; review it
   separately.

---

## 5. Next-round implementation options (dependency order)

1. **WP4 calibration records** (after decision 3): schema + tests for polarity/delay/relative gain,
   one guard family, report labels carrying the record; then G3/P7 crossover sum and DSP ranking.
2. **R2/R7b real-shape lane** (after decision 1): ingest the 12PR300 drawing, parameterise the
   panel fit, re-screen, stage/solve one real-shape case, then re-run the R7 calibration on a 5°
   grid.
3. **R5b observation standard** (after decision 5): encode the chosen distance/angular/seat policy
   in the request/observation contract; regenerate DI/power labels; keep the 10 m control as the
   reference diagnostic.
4. **WP6 pair generation** (after decision 6/authorization): funnel shortlist → stage/validate/solve
   top-N so G7 can actually compare screen classes against solved two-channel cases.
5. **B23/B24 contract pass** (senior/design): declared mesh-role set and geometry-aware fidelity.
6. **Release checks:** full offline profile on an idle box, `gpu-clean` before any measurement,
   and a single-solve-at-a-time GPU policy.

---

## 6. Reproduce the closeout evidence

```powershell
# scoped suites
.venv\Scripts\python.exe -m pytest tests\system -m "not slow and not gpu and not crosscheck" `
  -p no:cacheprovider
.venv\Scripts\python.exe -m pytest tests\test_gui_hw_lifecycle.py tests\test_gui_overview_health.py `
  tests\test_gui_overview_registry.py tests\test_tools_data_system_cases.py `
  tests\test_tools_data_system_solve_results.py -p no:cacheprovider

# portable data
.venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
.venv\Scripts\python.exe tools\data\system_solve_results.py --root . --out docs\system_data

# R7a record (read-only; needs the local store)
.venv\Scripts\python.exe -m hornlab_search.system.cli screen-calibration `
  system_runs\screens\system_evidence_2026-11-19\woofer_seed.json `
  system_runs\system\ev_assembled_motor_real\20261120T150709Z-wide_assembled-01612-383da940 `
  --out docs\evidence\system_evidence_2026-11-19\SCREEN_ESHAPE_CALIBRATION_RECORD_2026-11-21.json

# WP6 ledger (read-only)
.venv\Scripts\python.exe -m hornlab_search.system.cli funnel --root .
```

The real R5a solve command and the exact case path are in
`BALLOON_DI_POWER_2026-11-21.md`. Raw `run/*.npz` remain local; the committed
`system_solve_results.csv` is the portable result view.
