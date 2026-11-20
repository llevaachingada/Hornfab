# A2 - Calibration record + combine hook

Branch `claude/system-v1-pass-a`, clone `C:\Users\hunte\AppData\Local\Temp\opencode\hornlab-pass-a`.

## Files

- `hornlab_search/system/calibration.py` (new): `CAL_SCHEMA`, `CALIBRATION_TOKENS`,
  `CalMethod`, `METHOD_FIDELITY_CAP`, `CalibrationError` (`.token`/`.detail`),
  `ChannelCalibration`, `CalibrationRecord` (`to_dict`/`from_dict`/`compute_id`/
  `fidelity_cap`/`covers`), `apply_calibration`, plus `new_record()` which derives the id with
  `contracts.domain_sha16("system.calibration", payload_without_id)`.
- `hornlab_search/system/combine.py`: `combine(..., calibration=None, case_key=None)` (None is a
  no-op path), module-level `REFERENCE_REFUSAL_TOKENS` (R13 alias tuple), `__all__` update.
  `_require_compatible`, `_require_complex`, DSP and phase-once logic unchanged.
- `tests/system/test_calibration.py` (new): 20 tests - record round-trip/stable id/hand-picked id
  refusal, ladder-ordered `fidelity_cap`, apply success + frame preservation + input purity,
  fidelity caps (`loaded`, `unloaded`, `measured`), `combine` None-path byte equality, exact
  legacy mixed-reference `IncompatibleBasis` type+message, calibrated sum, and every refusal
  token (`CAL_SCOPE_MISMATCH`, `CAL_FREQ_GRID_MISMATCH`, `CAL_CHANNEL_MISSING`,
  `CAL_UNIT_MISMATCH`, `CAL_NONFINITE`).

No real calibration values, files under `docs/` or `examples/`, or edits to `contracts.py`,
`gui/**` or any other module. Not committed/pushed.

## Test command and counters

Task command (workdir = clone root):

```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -q tests/system/test_calibration.py tests/system/test_combine.py
```

`pyproject.toml` already sets `addopts = "-ra -q"`, so that exact command is double-quiet and
prints progress dots only (`..............................  [100%]`, exit 0). To capture the counter
line I ran the same file set with the duplicate quiet flag removed:

```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -q -o addopts="" tests/system/test_calibration.py tests/system/test_combine.py
..............................                                           [100%]
30 passed in 0.28s
```

30 = 20 in `test_calibration.py` + 10 existing in `test_combine.py` (no regressions).

## Requests for other lanes

None.

## Open questions (for the integrator / senior)

1. `REFERENCE_REFUSAL_TOKENS` (contract §3, R13): `combine._require_compatible` has no token
   text today (it raises `IncompatibleBasis` with a `compatible_for_sum_with` reason string), and
   `bl_results.assert_shared_sensitivity_reference` uses `SENSITIVITY_REFERENCE_MISMATCH`. I
   aliased the two families as `("INCOMPATIBLE_BASIS", "SENSITIVITY_REFERENCE_MISMATCH")`
   without changing any message. If the senior wants the combine family listed as its existing
   reason strings instead, that is a 4-line change in `combine.py`.
2. `from_dict` structural violations (unknown/missing keys, bad schema, non-UTC time) raise
   `contracts.SchemaError`; `CalibrationError.token` is restricted to the five contract tokens
   (grid, unit, scope, channel, non-finite conditions use the declared tokens).
3. `CalibrationRecord.to_dict()` includes `"schema": CAL_SCHEMA` as envelope metadata; it is part
   of the hashed payload. `record_id` is always derived, never accepted from a caller
   (`from_dict` recomputes and rejects a mismatch).
4. `apply_calibration` leaves `p_total` untouched (contract only mandates bases + fidelity); it is
   intended to run before `combine`, which owns the total.
