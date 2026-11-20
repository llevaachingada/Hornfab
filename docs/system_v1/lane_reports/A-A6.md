# A6 - fixture capture tool

**Status:** complete. No contract misfit found.

## Files changed (new)
- `tools/system/capture_fixture_cases.py` - stdlib-only, read-only over `--store` (the
  `system_runs` dir). Discovers `system/<experiment>/<timestamp-case>` dirs (same timestamp regex and
  skip parts as `tools/data/system_cases.py`), buckets by manifest `payload.kind` with a synthetic
  `invalid` bucket for missing/unreadable/malformed manifests, selects the first `--per-kind N` per
  bucket ordered by `(experiment, case)`, copies store-relative layout into `--out`, and writes
  `FIXTURE_PROVENANCE.json`.
- `tests/test_tools_capture_fixture_cases.py` - synthetic store with 3 kinds + 1 invalid, plus
  non-record dirs that must be ignored.

## Tests
Exact command (clone root):

```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -q -o addopts="" tests/test_tools_capture_fixture_cases.py
..........                                                               [100%]
10 passed in 0.25s
```

Coverage: first-N selection and `(experiment, case)` ordering; relative layout; byte equality;
`*.json`-only default; 256 KiB cap (large JSON omitted); `.npz`/`.msh` omitted unless
`--include-arrays` (still size-capped); provenance source paths + per-file sha256 + kinds covered +
tool version; byte-identical output across two runs; refusal (exit 2, no dir created, store
unchanged) when `--out` is inside `--store`; store read-only check; odd contents and a missing
`system/` dir produce diagnostics instead of raising.

## Pass 0, step 0.3 - run locally (owner)
```
.venv\Scripts\python.exe tools\system\capture_fixture_cases.py --store system_runs --out tests\system\fixtures\case_store --per-kind 2
```
Then review `tests\system\fixtures\case_store\FIXTURE_PROVENANCE.json` and commit the pack. The
output root is a valid GUI system store (`case_store\system\<experiment>\<case>\...`), so
`--system-store tests/system/fixtures/case_store` works unchanged.

## Choices where the contract was silent (documented)
- Default copy filter is `.json` files only; `--include-arrays` also admits `.npz`/`.msh`/`.vtk`.
  The 256 KiB cap always applies (arrays above it are still omitted as `too_large`).
- Provenance has **no timestamps** and is JSON with sorted keys, so an unchanged store gives
  byte-identical fixtures. Each case entry also records `omitted` files with a reason
  (`array_extension`, `not_json`, `too_large`); these are not diagnostics.
- A readable manifest whose `payload.kind` is missing/blank is not `invalid`: it is recorded as a
  diagnostic and skipped. `invalid` is reserved for missing/unreadable/non-object manifest/payload,
  matching the export's invalid status.
- Existing files under `--out` are overwritten but never pruned; the owner runs this once into an
  empty fixture dir. No cleanup is performed by the tool.

## Requests for other lanes
- None. `tools/data/system_cases.py` was read only and is untouched.
- Integrator: add `tools/system/capture_fixture_cases.py` to `INDEX.md` / `CODE_MAP.md`.
