# System backend closeout — B18–B30 / F19 (2026-11-21)

**Scope.** A current-HEAD audit of the backend/GUI issues in
[`HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md`](../../HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md)
§8.1, followed by the fixes that need no owner decision and no acoustic redesign. No GPU, no
solver, no new case except the separate R5a balloon control.

## Fixed in this pass

| ID | Fix | Test evidence |
|---|---|---|
| **B22** | `build_stage_spec` now records the explicit numeric `overrides` key; `_stage`'s manifest `detail["overrides"]` is the caller's request, not always `{}`. `source` stays the merged provider view. | `test_build_stage_spec_records_the_numeric_overrides`, `test_staged_manifest_detail_records_the_overrides` |
| **B26** | `filter_bank(point, freqs, ranges=None)` accepts optional `DspRanges`; when supplied it runs `validate_dsp_point` before assembly. `ranges=None` preserves the historical contract. | `test_filter_bank_validates_the_point_when_ranges_are_given`, `test_filter_bank_accepts_an_in_range_point_with_ranges` |
| **B30** | Removed the dead `_unused` stub from `optimize.py`; the intentional `run.solve_project` gate is untouched. | no behaviour change; targeted tests |
| **F19** | Both function-level `import meshio` sites in `gui/data_hw.py` are guarded. `_geometry` degrades to `None` with a warning; `_mesh_arrays` raises a clear `RuntimeError` naming the missing dependency instead of an obscure import failure or an empty mesh. | `test_mesh_reader_without_meshio_raises_a_clear_error`, `test_geometry_without_meshio_degrades_to_none_with_a_reason` |

Command:

```text
.venv\Scripts\python.exe -m pytest tests\system\test_bl_stage.py tests\system\test_dsp_complex.py tests\system\test_gui_hw_mesh.py -p no:cacheprovider
39 passed, 3 skipped in 1.36s
```

The three skips are the pre-existing real-Boundary-Lab staging tests gated by
`HORNLAB_BL_REAL_TESTS=1`.

## Already fixed before this pass (verified at HEAD)

| ID | Current state |
|---|---|
| **B18** | `pilot --geometry` is a supported LF-screening input; no bogus fidelity label. Covered by `test_horn_import.py`. |
| **B19** | Pilot Pareto axes are scalar `numeric_axes` + `axis_directions`; nested axes/list feasibility are refused by `score.validate_axes`. Covered by `test_score.py` / `test_horn_import.py`. |
| **B28** | Motor staging accepts `path`/`ts_path`/`geometry_path`; only the convenience defaults name 12PR300. |
| **B29** | Full-domain rebuild accepts `runs_root/run_name/design_hash`; only the convenience defaults name the saved asset. |
| **B20** | Left O(n²) deliberately: the recorded kept set is ≤126 rows and the front is what callers consume. Added a strict-domination/tie front test (`test_nondominated_front_is_strict_and_keeps_ties`) and a bound comment; revisit only if breadth grows by an order of magnitude. |
| **B25** | Resolved operationally: `tools/system/evidence_case.py` derives a fresh case (source hashes, copied artifacts, optional patches) instead of retrying in place; the existing refusal already names the new-case requirement. |
| **B27** | Accepted as the declared contract: independence is structural, explicitly documented, and covered by `test_per_excitation_independence_is_structural_and_documented`; a numerical rank test is optional analysis, not a bug fix. |

## Deferred — needs a design/acoustic decision or owner input

| ID | Why it is not closed here |
|---|---|
| **B21** | Inert/partially wired spec keys (`port_nfr_range` only uses its lower bound, placement ranges, `beamwidth_*`, `dsp.active`). Removing or wiring them changes the frozen-ish contract or the acoustic objective; document as reserved until an owner/senior pass. |
| **B23** | Clearance is coupled to `purpose == "bem_surface"`; accepting a declared role set changes the BL mesh-role contract. |
| **B24** | `_fidelity_for` infers the tier from `solve_kind` only; consulting geometry completeness changes the fidelity policy. |
| **F4** | `hw.js` keeps a private `GLOSS` map beside `glossary.js`; cosmetic UI/glossary drift, not a data or backend defect. |
| **R1/R13** | Blocked by owner decision 3 (calibration policy / guard unification). |
| **R2** | Blocked by owner decisions 1–2 (real transducer shape). |
| **R8** | Blocked by owner decision 4 (digital DSP realization). |
| **R14** | Blocked by owner decision 6 (typed authorization record). |

## Verification notes

- The other new deliverables in this closeout pass have their own evidence:
  [funnel](FUNNEL_LEDGER_2026-11-21.md), [R7a screen calibration](SCREEN_ESHAPE_CALIBRATION_RECORD_2026-11-21.json),
  and [R5a balloon DI/power](BALLOON_DI_POWER_2026-11-21.md).
- The full offline profile was attempted under the live GPU lane: it reached 99% with seven
  failures before the 20-minute shell timeout, matching the seven pre-existing other-lane
  failures documented in `docs/CONTINUITY.md` (v11 registration/score_identities/dataset
  manifest, v8 registration, preflight history, B8 `study_jobs` Popen, scout40 queue count).
  The scoped suites (`tests/system`, the GUI/export neighbours) are green. No failure is in a
  file touched by this pass.
- No installed package, frozen contract, or other lane's uncommitted file was modified.
