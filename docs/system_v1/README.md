# System v1: senior review, architecture and implementation plan (2026-11-20)

**Input reviewed:** `docs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md` (commit `c6fcdd4`) and the
`docs/system_data/` export. **Purpose:** turn the handbook's findings into a plan that lower-effort
agents can execute in parallel lanes, pass by pass, without re-deriving the design.

**Binding docs for this effort:** this file, [`01_CONTRACTS.md`](01_CONTRACTS.md) (frozen for the
effort), and the one pass handoff you were given. Repo rules (CLAUDE.md, AGENTS.md, CONTRIBUTING.md)
still win where they conflict.

---

## 1. Verdict (read this if nothing else)

1. **The handbook is accurate and the direction is right.** Keep its invariants: no coherent sum
   without a calibration record, fidelity is declared never inferred, immutable sha-sealed cases, no
   system score before calibration. Nothing here relitigates §7.6 of the handbook.
2. **The real blocker is not acoustics, it is the data model.** Ten different writer `kind`s produce
   ten payload shapes (census: `bl_stage_horn_project` 7, `system_pilot_v0` 7,
   `boundarylab_vented_generation` 6, `system_portfolio_v0` 4, ... 2 with no manifest). The GUI,
   the export tool and the evidence docs each re-implement discovery. **One typed reader
   (`read_case`) is the foundation; build it first.**
3. **Most remaining work is CPU and cloud-doable,** if it is fed fixtures. Cloud sessions cannot see
   `system_runs/`, Boundary Lab (BL), the GPU or the untracked GUI files. So the plan splits into
   **cloud passes** (pure Python, fixtures, offline tests, Playwright on a fixture store) and **local
   passes** (anything touching BL, `system_runs/`, the untracked GUI trio, or the owner).
4. **Build the gates' mechanisms now, leave their values to the owner.** `CalibrationRecord`,
   `AuthorizationRecord` and `ObservationStandard` can be coded and tested as schemas with refusal
   paths today. They are strictly *more* restrictive than the current code. The owner only has to
   supply the first real record (decisions 3, 5, 6) to unlock the sum, the far-field label and
   GUI-launched solves.
5. **Do not start a new solve before Pass 0 + Pass A land.** The cheap measurements (WP1 LF band,
   WP2 matrix) are Pass D and should run through the funnel command so their outputs arrive in the
   new schema.

### Findings added by this review (beyond the handbook)

| ID | Finding | Evidence | Fix lane |
|---|---|---|---|
| N1 | `tools/data/system_cases.py` is not portable: `horn_mesh` is derived with `Path(...)` so a Windows path (`C:\...\mesh.msh`) is not split on Linux. Its own test fails on Linux (15 passed / 1 failed: `test_metadata_is_extracted_by_key_not_position`). The tool claims to be portable. | `tools/data/system_cases.py:539`; run 2026-11-20 on Linux, Python 3.13 | A1 (path helper) then B1 |
| N2 | Calibrating the horn channel from Pa/(m/s) to Pa/V needs a velocity-per-volt transfer `H_v(f)` that depends on the horn's acoustic load, not just the compression driver. A record built from an unloaded driver model would silently overstate fidelity. | physics; `SourceBasis.per_input` | contract: `CalibrationRecord.method` caps fidelity (01_CONTRACTS §3) |
| N3 | The uncommitted local GUI trio (`hw3d.js`, `hw_screen.js`, `data_hw_stage.py`) is imported by tracked `hw.js`. Any cloud edit to `hw.js`/`app.js`/`data_hw*.py` before the trio is committed guarantees a merge conflict or a broken boot. | handbook F14, ISSUES 2026-11-19 | Pass 0 is a hard prerequisite for Pass C and lane B2 |
| N4 | Parallel lanes cannot each update `CONTINUITY.md`/`ISSUES.md`/`INDEX.md`/`CODE_MAP.md` without conflicts. | repo push rule | lanes write `docs/system_v1/lane_reports/<lane>.md`; only the pass integrator edits the four shared docs |

---

## 2. Target architecture (adopted from handbook §9.3, made concrete)

```
L0  SOLVE LAYER (frozen)        design / mesh / solve / metrics / objective / search / dataset
        |  HornAsset adapter (read-only, exists: horn_assets, horn_import, horn_full_domain)
L1  SYSTEM DOMAIN (pure)        contracts.py (frozen v1)
                                case_schema.py   NEW  SystemCase + blocks, store-relative paths
                                calibration.py   NEW  CalibrationRecord, apply_calibration()
                                authorization.py NEW  AuthorizationRecord
                                observation.py   NEW  ObservationStandard (schema only)
                                screen modules, dsp.py, combine.py (gains calibration= param)
        |
L2  EXECUTION ADAPTERS          read_case.py     NEW  one reader for every kind (+ invalid)
                                jobs.py          NEW  JobSpec, preview == argv actually run
                                funnel.py        NEW  screen -> plan stage/validate/solve -> ledger
                                store_migrate.py NEW  absolute -> store-relative, dry-run first
                                boundarylab/*    exists (local only)
        |
L3  READ MODELS (Python)        gui/data_hw*.py all built on read_case + CaseReadModel
                                gui/data_hw_dsp.py NEW  per-channel curves; sum only with record
        |
L4  GUI (vanilla JS)            one module per view: hw_overview, hw_new, hw_screen(s), hw_cases,
                                hw_case, hw_compare, hw_crossover, hw_readiness; app.js = routes only
```

Rules that every lane inherits:

- **No acoustics in JS.** JS renders numbers and refusal tokens from read models; it never infers
  status, fidelity or Pareto.
- **No new solver, mesher, gmsh writer or Green's function.** System work calls BL through the
  existing adapters only.
- **No change to `hornlab_search/system/contracts.py` v1** except where `01_CONTRACTS.md` says so
  (it does not, for this effort). New types live in new modules.
- **Refusals are data.** Every refusal is a stable `UPPER_SNAKE` token plus a human message.
- **Determinism.** Same inputs, byte-identical outputs (sorted keys, fixed column order, ids from
  `contracts.domain_sha16`).
- **Offline tests only in cloud lanes.** Anything needing BL, GPU or `system_runs/` is marked and
  run locally.

---

## 3. Pass map

| Pass | Where | Parallel lanes | Depends on | Owner gate | Handoff |
|---|---|---|---|---|---|
| **0** | LOCAL (Windows canonical checkout) | 1 (orchestrator) | nothing | answer decisions 3/5/6 *shape* (defaults offered) | [PASS_0_LOCAL.md](PASS_0_LOCAL.md) |
| **A** | CLOUD | 6: A1-A6 | nothing (can run beside Pass 0) | none | [PASS_A_CLOUD.md](PASS_A_CLOUD.md) |
| **B** | CLOUD | 5: B1-B5 | A merged; B2 also needs Pass 0 | none | [PASS_B_CLOUD.md](PASS_B_CLOUD.md) |
| **C** | CLOUD (Playwright on fixture store) + LOCAL acceptance | 1 shell lane, then 6 view lanes | Pass 0, B2, B5 | none | [PASS_C_GUI.md](PASS_C_GUI.md) |
| **D** | LOCAL (BL `beat_cpu`, no GPU) | serial jobs, 1 operator | A + B3 merged | owner approves the CPU solves | [PASS_D_LOCAL_MEASURE.md](PASS_D_LOCAL_MEASURE.md) |
| **E** | mixed | per item | D, owner | decisions 1, 2, 3 values, 6 values | [PASS_E_GATED.md](PASS_E_GATED.md) |

```
Pass 0 (local) ─────────────┐
Pass A (cloud, 6 lanes) ────┼──> Pass B (cloud, 5 lanes) ──> Pass C (GUI) ──> Pass E (gated)
                            │                     └────────> Pass D (local CPU solves) ─┘
```

**Pass A and Pass 0 can run at the same time.** Pass A touches no GUI file and no `hw*.js`.

---

## 4. Lane protocol (every lane, every pass)

1. Read: this README §1-§4, `01_CONTRACTS.md`, your pass handoff's "Shared rules" and **your lane
   only**. Do not read the 1,903-line handbook end to end; the handoff cites the sections you need.
2. Edit **only** the paths your lane owns. Need another file changed? Write the exact change in your
   lane report under "Requests for other lanes"; do not edit it.
3. Tests: `python -m pytest -q <your test files>` must pass; then the pass's regression command must
   not get worse than its recorded baseline. Locally use `.venv\Scripts\python.exe`.
4. Write `docs/system_v1/lane_reports/<PASS>-<LANE>.md`: files changed, test command + counters
   copied from the terminal, open questions, requests for other lanes. Max ~60 lines.
5. **Do not commit, push, or edit `docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/INDEX.md`,
   `docs/CODE_MAP.md`.** The pass integrator does that once, in one commit, from the lane reports.
6. Stop and report instead of guessing when: a contract in `01_CONTRACTS.md` does not fit the code,
   a test outside your lane breaks, or a task needs BL/GPU/`system_runs/`.

## 5. Integrator protocol (the parent session of each pass)

1. Launch lanes in parallel with the lane brief text from the handoff, verbatim.
2. When all lanes report: run the pass regression command, resolve "requests for other lanes"
   yourself (small) or defer them to the next pass's lane list.
3. One commit per pass on the working branch, touching `CONTINUITY.md` (new top entry),
   `ISSUES.md` (mirror), `INDEX.md` / `CODE_MAP.md` (new modules/docs). Push, open a draft PR into
   `hornfab-all-*` (R21: the local orchestrator integrates).
4. Record in the CONTINUITY entry: pass id, lanes done/not done, test counters, deferrals.

## 6. Owner decisions: what is needed, and when

| Decision | Needed by | Recommended default (handbook §7.3 + this review) | What the plan builds without it |
|---|---|---|---|
| 3 Calibration policy | Pass E sum | (a) explicit per-channel `CalibrationRecord`; method caps fidelity (N2) | the record type, validation, `combine(calibration=...)`, refusal paths |
| 6 Solve authorization | GUI solve button (Pass E) | typed who/why/scope record written into the manifest | `AuthorizationRecord`, legacy-string wrapping, refusal paths |
| 5 Observation standard | any DI / listening-window claim | declare distance + grid + window in a record; keep 2 m cuts labelled "near-field cuts" until then | `ObservationStandard` schema + label helper |
| 1, 2 Real geometry / taller front | WP7 | procure 12PR300 drawings; decide front height after | nothing (Pass E) |
| 4 DSP realization | digital claims | analog prototypes this round | nothing |

The plan never commits a real `CalibrationRecord`, `AuthorizationRecord` value or observation
values. Those are owner artifacts.

## 7. Definition of done for system v1

- One `read_case()` reads all 37 known cases (fixture pack) with zero writer-specific branches in the
  GUI or export.
- The export, the GUI and the evidence docs agree on every census number (one source).
- Store is relocatable (store-relative paths; migration dry-run clean).
- `funnel` produces a deterministic ledger from a spec, with fidelity tags, in dry-run and real mode.
- WP1 (20-200 Hz) and WP2 (2x2 motor x box) solved and in the ledger.
- GUI: Overview, New system, Screens, Cases, Case, Compare, Crossover (per-channel; sum gated),
  Readiness; lifecycle test + browser checklist green at 1280/1009/768/375.
- Known defects B18, B19, B21-B26, F1-F22, N1 closed or explicitly deferred with a reason.
