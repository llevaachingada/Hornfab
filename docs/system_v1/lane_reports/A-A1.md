# A1 - case schema, reader, path helper

**Status:** complete. No contract misfit found.

## Files changed (new)
- `hornlab_search/system/paths.py` - `split_any`, `to_store_relative`, `leaf_dir_name`; pure string ops, Windows/POSIX identical on any OS.
- `hornlab_search/system/case_schema.py` - `CASE_SCHEMA`, `CaseHeader`, `ClearanceBlock`, `StageBlock`, `SolveBlock`, `GeometryBlock`, `Declaration`, `SystemCase`; frozen+slots dataclasses, deterministic `to_dict()` (sorted keys, tuples -> lists, NaN -> None).
- `hornlab_search/system/read_case.py` - `read_case`, `iter_cases`, `load_readiness`; ported status rules / metadata walk / integrity checks from `tools/data/system_cases.py`; every path split/relativised via `paths.py`; never raises (invalid + diagnostics).
- `tests/system/test_paths.py`, `tests/system/test_case_schema.py`, `tests/system/test_read_case.py`.

## Tests
Exact command (clone root):

```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -q tests/system/test_paths.py tests/system/test_case_schema.py tests/system/test_read_case.py
.......................                                                  [100%]
```

The repo `addopts = "-ra -q"` plus the explicit `-q` suppresses the summary line, so the counters were
captured with `-o addopts=""` on the same files:

```
23 passed in 0.45s
```

Coverage: all four statuses + status_reason; `spec.geometry.refusals` and `BL_CAPABILITY_OK` are not
refusals; true/token refusals; manifest integrity verified/mismatch/unknown; never-raises on missing dir
and non-object manifest; Windows mesh path read on this OS; request-over-manifest walk order; clearance
and air-volume; readiness declared vs `UNDECLARED` (direct mapping and `load_readiness` YAML); iter_cases
ordering; parity with the tool's `scan_cases` row builder for status/kind/manifest_integrity/box/horn
fields (skips `horn_mesh` only where the tool differs, and asserts the correct leaf name).

## Requests for other lanes
- B1 (export): import `paths.leaf_dir_name` / `paths.to_store_relative`; this fixes N1 in
  `tools/data/system_cases.py:539`. Parity test confirms the tool's only observed divergence is that
  `horn_mesh` line on POSIX. Keep the tool's public row shape; `read_case` is the new source.
- Integrator: add `paths.py`, `case_schema.py`, `read_case.py` to `INDEX.md` / `CODE_MAP.md`.

## Open questions / choices (contract silent, documented here)
- `StageBlock.project_rel`: set to the store-relative `case.blab.json` when present, else `None`.
- `SystemCase.sources`: store-relative POSIX paths actually read, in read order (`manifest.json` first,
  then metadata documents). `manifest.payload` is not repeated as a file.
- `SystemCase.refusals`: literal `REFUSED` / `BL_*` tokens found. A phrase-only result refusal (no token)
  yields `("CASE_REFUSED",)` so a refused case never has an empty refusal list.
- Clearance: no recorded block -> `stage.clearance is None`; a block with no verdict -> `not_recorded`
  (the tool's `unknown` is not in the contract literal set). `unproven` accepted from raw status.
- Invalid cases keep `stage/solve/geometry = None`; status_reason is `NO_MANIFEST` when the file is
  absent and `UNPARSEABLE` when it exists but cannot be used.
