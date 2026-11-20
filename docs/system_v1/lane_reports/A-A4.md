# Pass A lane A4 — backend defect fixes (B18, B19, B21, B22, B23, B26)

**Branch:** `claude/system-v1-pass-a` (clone `hornlab-pass-a`). **No new modules.**
**Status:** all six fixes implemented; tests pass; no touched-area regression. Nothing committed.

## Files changed

- `hornlab_search/system/optimize.py` — B18: fidelity label `LF_TS_SCREENING` -> ladder label `SCREEN_MAGNITUDE`.
- `hornlab_search/system/score.py` — B19: `dominates` unwraps `{value, direction}` cells, uses embedded direction (`"-"` minimises) when no explicit `axis_directions` entry exists; NaN still never dominates. Plain-number rows unchanged.
- `hornlab_search/system/woofer_seed.py` — B21: `RESERVED_SPEC_KEYS`, `reserved_spec_keys()`, `warn_reserved_spec_keys()`; `main()` emits one `UserWarning` per spec naming the reserved keys present. Nothing implemented.
- `hornlab_search/system/boundarylab/stage.py` — B22: `detail.overrides` now `spec.get("source", {})`; B23: module-level `BEM_SURFACE_ROLES = frozenset({"bem_surface"})`, clearance uses membership.
- `hornlab_search/system/dsp.py` — B26: `filter_bank(..., ranges=None)` calls `validate_dsp_point` at entry when ranges are supplied.
- `tests/system/test_optimize_fixes.py` (new) — B18, B19, B21, B26.
- `tests/system/test_stage_fixes.py` (new) — B22, B23.
- `docs/system_v1/lane_reports/A-A4.md` (this file).

## Commands and counters (PowerShell, workdir = clone root)

```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -o addopts="" tests/system/test_optimize_fixes.py tests/system/test_stage_fixes.py
=> collected 6 items ... 6 passed in 0.58s
```

```
& "...\.venv\Scripts\python.exe" -m pytest -o addopts="" tests/system/test_horn_import.py tests/system/test_score.py tests/system/test_dsp_complex.py tests/system/test_combine.py tests/system/test_reference_cli.py tests/system/test_woofer_seed.py tests/system/test_bl_stage.py tests/system/test_clearance.py
=> collected 121 items ... 116 passed, 5 skipped, 5 warnings in 2.78s
```

(`test_optimize.py`, `test_stage.py`, `test_dsp.py` do not exist in this tree; the touched areas are covered by `test_horn_import.py`, `test_score.py`, `test_dsp_complex.py`/`test_combine.py`/`test_reference_cli.py`, `test_woofer_seed.py`, `test_bl_stage.py`/`test_clearance.py`.) Skips are the existing `HORNLAB_BL_REAL_TESTS` gates, not new skips. Warnings are the pre-existing A3 B24 diagnostic.

## Per-fix outcome

- **B18** PASS — documented `run_pilot(..., geometry_path=...)` path completes; driver geometry is retained.
  *Superseded at integration:* the integration branch's `df0e20f` landed its own B18 fix first
  (drop the label call; authority is `SCREEN_MAGNITUDE`), and this pass adopts that version.
- **B19** PASS — dict axis cells normalise to numbers; a strictly worse dict-axis row is dominated (reverse is not).
  *Superseded at integration:* `df0e20f` made scalar `numeric_axes` + `axis_directions` the contract
  and added `score.validate_axes()`, which rejects nested axes at `render_report` instead of ranking
  them. This pass adopts that version and drops the `dominates` unwrapping; the test now asserts the
  canonical schema (`test_nested_axes_cannot_produce_an_all_pareto_report`).
- **B21** PASS — one warning per spec names every reserved key present (`port_nfr_range`, the three placement ranges, both beamwidths, `dsp.active`); silent when absent.
- **B22** PASS — staged run records the resolved `spec.source` (provider defaults + caller overrides) in `detail.overrides`.
- **B23** PASS — clearance finds the horn surface via `BEM_SURFACE_ROLES` membership; adding a declared role keeps the gate working.
- **B26** PASS — `filter_bank` range-checks when given a `DspRanges`; out-of-range xo raises `SchemaError`.

## Requests / notes for other lanes

- B26 is opt-in at the call site (`ranges=...`) to keep existing callers byte-compatible (notably
  `combine.recombine_with_dsp`'s fixture uses `gain_db_horn=1.5`, outside default `DspRanges`).
  If a caller owns the spec ranges, pass them into `filter_bank`; no source change requested here.
- B21 warning is emitted on the `woofer_seed` CLI path (where the raw spec exists). Other callers
  that parse a raw spec should call `woofer_seed.warn_reserved_spec_keys(spec_doc)` themselves.
- No contract/API changes outside the owned files; `contracts.py`, `combine.py`, `gui/**` untouched by this lane.
