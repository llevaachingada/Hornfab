# Pass A: cloud foundations (6 parallel lanes, pure Python, offline tests)

**Where:** a cloud session on a branch cut from the newest `hornfab-all-*`. **Depends on:** nothing.
**Interpreter in cloud:** `python3 -m pytest` (Linux; no `.venv\Scripts`). **No GPU, no BL, no
`system_runs/`.** No lane touches `hornlab_search/gui/**`.

## Shared rules (every lane)

- Contracts: `docs/system_v1/01_CONTRACTS.md`. Implement them exactly; stop and report on misfit.
- Do not edit `hornlab_search/system/contracts.py`, `docs/plan/**`, the four shared docs
  (`CONTINUITY`, `ISSUES`, `INDEX`, `CODE_MAP`), or any path not in your lane's "Owns".
- Tests: new tests go in `tests/system/test_<module>.py`. Offline only. Use `tmp_path` fixtures; build
  fake case dirs by calling the real writers (`system.provenance.new_case_dir`, `write_manifest`)
  where possible, and copy fixture patterns from `tests/test_tools_data_system_cases.py`.
- Lane report: `docs/system_v1/lane_reports/A-<lane>.md` (files, test command + counters, requests).
- Regression command for the pass: `python3 -m pytest -q tests/system tests/test_tools_data_system_cases.py`.
  Baseline recorded 2026-11-20 on Linux: `tests/test_tools_data_system_cases.py` 15 passed / 1 failed
  (N1). Lane A1 fixes N1 in the shared helper; lane B1 wires the export to it.

---

## A1 - Case schema + reader + path helper

**Owns:** `hornlab_search/system/paths.py`, `case_schema.py`, `read_case.py`;
`tests/system/test_paths.py`, `test_case_schema.py`, `test_read_case.py`.
**Read:** contracts §1-§2; `tools/data/system_cases.py` (whole docstring + status/metadata/integrity
functions); `hornlab_search/system/provenance.py`; handbook §4.6 (on-disk schemas) and §6.3.
**Steps:**
1. `paths.py` per contract §1. Test Windows and POSIX inputs on any OS (`C:\a\b\mesh.msh` -> leaf
   `b`; `C:/Users/x/system_runs/system/e/c/run/manifest.json` -> `system/e/c/run/manifest.json`).
2. `case_schema.py` dataclasses + `to_dict()` (sorted keys, tuples to lists).
3. `read_case.py`: port the status rules, metadata walk order, integrity checks and readiness join
   from `tools/data/system_cases.py`. Use `paths.py` for every path. Never raise on bad data.
4. Tests: one synthetic case per status (solved/staged/refused/invalid), the `spec.geometry.refusals`
   and `BL_CAPABILITY_OK` non-refusal cases, integrity verified/mismatch/unknown, a Windows-path
   manifest read on Linux, readiness declared vs `UNDECLARED`, `iter_cases` ordering.
5. Parity test: build a synthetic store, run both `tools/data/system_cases.py`'s row builder and
   `read_case`, assert equal status/kind/integrity/box/horn fields for every case (skip `horn_mesh`
   where the tool is wrong; assert `read_case` gives the correct leaf name).
**Done when:** your tests pass; regression command no worse than baseline.

## A2 - Calibration record + combine hook

**Owns:** `hornlab_search/system/calibration.py`, edits to `hornlab_search/system/combine.py`
(the `calibration=` parameter and `REFERENCE_REFUSAL_TOKENS` only); `tests/system/test_calibration.py`.
**Read:** contracts §3; `combine.py`; `contracts.py` `SourceBasis`, `SystemResponse`, fidelity ladder;
handbook §2.1-§2.2, §4.5, risks R1/R13.
**Steps:**
1. Dataclasses, `from_dict`/`to_dict`, id via `domain_sha16("system.calibration", ...)`.
2. `fidelity_cap()` using the existing ladder order from `contracts.py` (do not redefine the ladder).
3. `apply_calibration` with all five refusal tokens.
4. `combine(..., calibration=None, case_key=None)`: with `None`, byte-identical behaviour (add a test
   that today's mixed-reference refusal still raises the same exception and message).
5. Tests with a synthetic 2-excitation response (horn `normal_velocity_mps`, woofer `V_rms`, shared
   distance/origin/frame/hashes): refusal without record; success with record; fidelity capped by
   `unloaded_driver_model`; each refusal token.
**Do not** add any real calibration values or files under `docs/` or `examples/`.

## A3 - Authorization + observation records; reference.py hooks and fixes

**Owns:** `hornlab_search/system/authorization.py`, `observation.py`; edits to
`hornlab_search/system/reference.py` (authorization param, B24, B25 only);
`tests/system/test_authorization.py`, `test_observation.py`, additions to `tests/system/test_reference_cli.py`.
**Read:** contracts §4-§5; `reference.py` lines ~957-1210 (`build_solve_argv`, `solve`,
`_fidelity_for`); handbook §4.8, B24, B25.
**Steps:**
1. `authorization.py` + `observation.py` per contract.
2. `reference.solve`: accept `authorization`; wrap a legacy string; write `authorization` dict into the
   record next to `authorized_by`. Existing tests must still pass unchanged.
3. B24: `_fidelity_for` must not label above `SCREEN_COMPLEX_APPROX` when the driver geometry
   completeness for `INSTALLED_EXTERIOR_BEM` is false (use `drivers.geometry_completeness`; if the
   result object does not carry it, return the current label and add a diagnostic. Report which).
4. B25: add `new_case_for_retry(case_dir) -> Path` that creates a sibling case dir with
   `retry_of: <case_key>` in the manifest; document it in the docstring of `solve`.
5. Tests for all tokens, legacy wrapping, expiry, scope, and the B24/B25 behaviours.

## A4 - Backend defect fixes (no new modules)

**Owns:** edits to `hornlab_search/system/optimize.py`, `score.py`, `dsp.py`,
`boundarylab/stage.py`, `woofer_seed.py` (B21 warning only); `tests/system/test_optimize_fixes.py`,
`tests/system/test_stage_fixes.py`.
**Read:** handbook §8.1 rows B18, B19, B21, B22, B23, B26 (each cites file:line).
**Fix list:**
- B18 `pilot --geometry` raises `SchemaError`: `require_fidelity(driver, "LF_TS_SCREENING")` uses a
  label that is not on the ladder. Use the correct ladder label for a T/S-only screen (read
  `drivers.require_fidelity` + the ladder; if no label fits, skip the check and add a diagnostic).
  Test the documented path.
- B19 pilot Pareto inert: `numeric_axes` values are dicts; `score.dominates` compares them as
  non-numbers. Normalise `{value, direction}` to signed numbers before dominance (`direction "-"`
  minimise). Test that a strictly worse row is dominated.
- B21 inert spec keys (`port_nfr_range`, placement ranges, beamwidth, `dsp.active`): emit one
  `UserWarning` per inert key present in a spec, listing them as reserved. Do not implement them.
- B22 `stage.detail.overrides` always `{}`: read from `spec.source` as the handbook says.
- B23 clearance tied to `purpose == "bem_surface"`: accept a module-level
  `BEM_SURFACE_ROLES = frozenset({"bem_surface"})` and test membership, not equality.
- B26 `dsp.filter_bank` does not range-check: call `validate_dsp_point` at entry.
Each fix: smallest diff, one test, no behaviour change elsewhere (run `tests/system`).

## A5 - JobSpec + evidence byte-check tool

**Owns:** `hornlab_search/system/jobs.py`, `tools/evidence/verify_evidence_quotes.py`;
`tests/system/test_jobs.py`, `tests/test_tools_verify_evidence_quotes.py`.
**Read:** contracts §6; `tools/system/gui_system_job.py`; `hornlab_search/system/cli.py`
(subcommands); handbook §4.12, R12/B12; the `hornlab-evidence` skill if available.
**Steps:**
1. `jobs.py`: `build_job` produces argv for each kind using `sys.executable -m
   hornlab_search.system.cli ...` (or `woofer_seed`) exactly as `gui_system_job.py` does today;
   `preview` is `shlex.join` (POSIX) / `subprocess.list2cmdline` (Windows) of that argv. Test that
   preview equals the argv joined, for every kind, and that `bl_solve` without authorization refuses.
   Do not change `gui_system_job.py` (B2/C lanes adopt `jobs.py`).
2. `verify_evidence_quotes.py`: given an evidence `.md` and one or more log files, find fenced blocks
   tagged as quotes (convention: a fenced block whose preceding line contains `quote:` or the
   `[measured]` marker; read `docs/evidence/` for the real convention and follow it), decode logs as
   UTF-16 when they have a BOM else UTF-8, and report each quote line not found verbatim. Exit 1 on
   any miss. Tests with tiny synthetic md + UTF-16 log.

## A6 - Fixture capture tool (run locally later)

**Owns:** `tools/system/capture_fixture_cases.py`, `tests/test_tools_capture_fixture_cases.py`.
**Read:** handbook §6.3; `docs/system_data/README.md`; `tools/data/system_cases.py` (case discovery).
**Behaviour:** read-only over `--store`; for each payload `kind` (and for `invalid`), copy up to
`--per-kind N` case dirs into `--out` keeping relative layout, copying only `*.json` and files
<= 256 KB, never `.npz`/`.msh`/`.vtk` unless `--include-arrays`; bytes verbatim (so hashes stay
valid); write `FIXTURE_PROVENANCE.json` (source store-relative path, sha256 of each copied file,
kinds covered, tool version). Deterministic choice: first N by `(experiment, case)`. Stdlib only.
**Tests:** synthetic store with 3 kinds + 1 invalid; verify selection, size filter, byte equality,
provenance, refusal to write inside `--store`.

---

## Integrator checklist (Pass A)

- [ ] All six lane reports present; regression command run and pasted.
- [ ] Resolve cross-lane requests (expected: A3 needs a `SystemResponse` field name from A2; A1 may
      ask A4 nothing).
- [ ] One commit: code + tests + lane reports + `CONTINUITY`/`ISSUES`/`INDEX`/`CODE_MAP` rows for
      `paths`, `case_schema`, `read_case`, `calibration`, `authorization`, `observation`, `jobs`,
      `verify_evidence_quotes`, `capture_fixture_cases`.
- [ ] Push; draft PR into `hornfab-all-*`; tell the local orchestrator to run Pass 0 step 0.3.

## Paste-ready lane brief (fill LANE)

```
You are lane <LANE> of HornFab System v1 Pass A (cloud, offline). Read
docs/system_v1/README.md sections 1, 2 and 4, docs/system_v1/01_CONTRACTS.md, and only the
"<LANE>" section plus "Shared rules" of docs/system_v1/PASS_A_CLOUD.md. Edit only the paths your
lane Owns. Run your tests with python3 -m pytest -q. Do not commit, push, or edit CONTINUITY,
ISSUES, INDEX or CODE_MAP. Finish by writing docs/system_v1/lane_reports/A-<LANE>.md with files
changed, the exact test command and its counters, and any requests for other lanes. If a contract
does not fit the code, stop and say so in the report instead of improvising.
```
