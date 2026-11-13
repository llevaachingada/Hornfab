# Cohorts

- operation: **ath_census**
- status: **eligible_with_provenance_gaps**
- generated: `2026-11-12T23:53:53Z`

- reason codes: `experiment_identity_unknown_for_some_rows`
- required equal: ``
- allowed differences: ``

## Resolved ATH task

- config: `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\campaign_2026-10-26_v4\native__ath_core_v4.yaml`
- brief: `native_ath_core_2in_v4` (`fa45251216b5`)
- objective v4; target {'coverage_h_deg': 50.0, 'coverage_v_deg': 50.0, 'band_lo_hz': 300.0, 'band_hi_hz': 8000.0, 'f0_hz': 1280.0, 'freq_weights': {'band_hz': [[2500.0, 5500.0, 2.0]]}}
- matched records: **3185**; excluded: `{'brief_mismatch': 13950, 'brief_missing': 11541}`
- group rule: screen/verify, backend and external dependency identity are separate cohorts; a total across groups is descriptive only

## Groups

### `{'fidelity': 'screen', 'backend': 'beat_cuda', 'dependency_hash': 'e3614d0ba5956ded'}` — eligible_with_provenance_gaps
- records/ok/failed: **1913 / 1499 / 414**
- unique solves / geometries / experiments known: **1499 / 1499 / 0**
- complete replayable: **1499**; partial unsupported/loading/gate/torn: **0 / 0 / 0 / 0**
- missing arrays: `{}`; failures: `{'invalid_geometry': 299, 'mesh_too_large': 115}`
- experiment id unknown rows: **1913**
### `{'fidelity': 'screen', 'backend': 'beat_cuda', 'dependency_hash': '84709bd8e737cca4'}` — eligible_with_provenance_gaps
- records/ok/failed: **1236 / 878 / 358**
- unique solves / geometries / experiments known: **878 / 878 / 4**
- complete replayable: **878**; partial unsupported/loading/gate/torn: **0 / 0 / 0 / 0**
- missing arrays: `{}`; failures: `{'invalid_geometry': 257, 'mesh_too_large': 98, 'solve_failed': 3}`
- experiment id unknown rows: **425**
### `{'fidelity': 'verify', 'backend': 'beat_cuda', 'dependency_hash': 'e3614d0ba5956ded'}` — eligible_with_provenance_gaps
- records/ok/failed: **20 / 20 / 0**
- unique solves / geometries / experiments known: **20 / 20 / 0**
- complete replayable: **20**; partial unsupported/loading/gate/torn: **0 / 0 / 0 / 0**
- missing arrays: `{}`; failures: `{}`
- experiment id unknown rows: **20**
### `{'fidelity': 'verify', 'backend': 'beat_cuda', 'dependency_hash': '84709bd8e737cca4'}` — insufficient_evidence
- records/ok/failed: **16 / 15 / 1**
- unique solves / geometries / experiments known: **15 / 15 / 1**
- complete replayable: **15**; partial unsupported/loading/gate/torn: **0 / 0 / 0 / 0**
- missing arrays: `{}`; failures: `{'solve_failed': 1}`
- experiment id unknown rows: **6**
