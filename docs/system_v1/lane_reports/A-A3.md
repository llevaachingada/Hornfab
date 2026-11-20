# A-A3 — Authorization + observation records; reference hooks + B24/B25

## Files
- `hornlab_search/system/authorization.py` (new): `AuthorizationRecord`, `from_legacy_string`,
  `load_authorization`, `check`; tokens `AUTH_MISSING`, `AUTH_EXPIRED`, `AUTH_SCOPE_MISMATCH`,
  `AUTH_ACTION_NOT_GRANTED`; ids from `domain_sha16("system.authorization", payload)`.
  Legacy strings use a fixed epoch `created_utc` so wrapping is deterministic.
- `hornlab_search/system/observation.py` (new): `ObservationStandard`, `to_dict`/`from_dict`
  (id derived), `label_for` returning the exact contract fallback string.
- `hornlab_search/system/reference.py`: `solve` accepts `authorization=` (record or legacy string),
  wraps `authorized_by`, checks before spawning BL, and writes `authorization` beside
  `authorized_by`; added `new_case_for_retry`; B24 fidelity cap.
- `tests/system/test_authorization.py`, `tests/system/test_observation.py`,
  `tests/system/test_reference_cli.py` (new A3 cases appended).

## Test command + counters
```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -q tests/system/test_authorization.py tests/system/test_observation.py tests/system/test_reference_cli.py
```
pytest 9.1.1 with `-q` prints progress but no final count line. Same selection with `-v`:
`collected 53 items` — **51 passed, 2 skipped, 5 warnings in 1.87s**. The 2 skips are the
pre-existing real-BL (`HORNLAB_BL_REAL_TESTS`) cases. No failures.

## B24 outcome
`boundarylab/bl_results.BLHeadlessResult` does **not** carry driver-geometry completeness (its
own docstring says the reader cannot see it; `data_quality` has no geometry key). So the
"does not carry it" branch is the live one today: `_fidelity_for` keeps the current label and
emits a `RuntimeWarning` naming the unverified `INSTALLED_EXTERIOR_BEM` /
`COUPLED_VENTED_FEM_BEM_LEM` claim. The code already accepts a future reader's data via
`data_quality` (or attributes) under `geometry_fields`/`driver_geometry_fields`/
`installed_geometry_fields`, or a precomputed `geometry_completeness`/
`driver_geometry_completeness`; incomplete `INSTALLED_EXTERIOR_BEM` caps at
`SCREEN_COMPLEX_APPROX`. `drivers.geometry_completeness` is the classifier used for fields.

## Requests / open questions
- B3: call `authorization.check(..., action="bl_solve", case_key=<row.case_key>, now_utc=...)`.
  `funnel_run` scope entries are matched as case keys (exact), like `case`; list the planned
  case keys, or use `"*"` deliberately.
- Pass E GUI: pass a typed `AuthorizationRecord`; a free string still works but is marked
  `legacy_free_string=True` in the record.
- `contracts.canonical_json` renders `None` as the string `"None"`, so a solve record stores
  `expires_utc: "None"`. `AuthorizationRecord.from_dict` (and `ObservationStandard.from_dict`
  for `approved_by`) tolerates that literal. Preserving real JSON null needs a change outside
  this lane (`_write_record` / `canonical_json`).
- `new_case_for_retry` copies the source manifest payload and adds `retry_of`; it does not copy
  `case.blab.json` or the request file. The task asked for the manifest only — confirm whether
  the retry helper should also copy the project/request.
- A1/read_case: `retry_of` is additive manifest metadata; no reader change assumed.
