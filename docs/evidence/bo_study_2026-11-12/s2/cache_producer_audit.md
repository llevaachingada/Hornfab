# S2 cache producer compatibility audit (read-only)

- generated_utc: `2026-11-13T13:57:12Z`
- tool: `cache_producer_audit 1.0.0`
- behavior_changed: `false`
- no_cache_writes: `true`

## Key / validity finding

- key: `{design_hash}-{mesh_hash}-{solve_hash}` (`hornlab_search/solve/cache.py::key`)
- lookup validity: status.json with ok:true AND a loadable response.npz; nothing else. Corrupt/absent/ok:false is a miss, never an error.
- producer library pins checked on lookup: **false**
- v7 throat gate: search/evaluate.py runs the v7 throat gate before the solve-cache lookup, so a stored response cannot bypass that one newer physical check; this is not a general producer-pin guard.

## Cache inventory (bounded sample)

| root | exists | entries (names) | sampled | producer present | producer unknown | score-only reusable |
| --- | --- | --- | --- | --- | --- | --- |
| C:\Users\hunte\Hrns\hornlab-search\cache\solve | True | 25707 | 200 | 0 | 200 | 200 |
| C:\Users\hunte\Hrns\hornlab-search\cache_cpu\solve | True | 224 | 200 | 0 | 200 | 199 |

- sample cap: 200 per root; sampled bytes: 136846859
- markers in sample: {'band_split': 0, 'seam': 0, 'trace': 399, 'normal': 399}

## Source-level caller coverage

| file | line | function | role |
| --- | --- | --- | --- |
| hornlab_search/compare/fake.py | 117 | write_hornfab_side | fake-response fixture writer (not a solve-cache entry) |
| hornlab_search/compare/hornfab_side.py | 110 | load_hornfab | independent compare-side response reader/writer (not the search cache) |
| hornlab_search/compare/hornfab_side.py | 302 | solve_reference | independent compare-side response reader/writer (not the search cache) |
| hornlab_search/mesh/build.py | 316 | prebuilt_key | mesh cache key builder (design+mesh+mounting/rear factor) |
| hornlab_search/mesh/build.py | 341 | build_mesh | mesh cache key builder (design+mesh+mounting/rear factor) |
| hornlab_search/mesh/build.py | 364 | build_mesh | mesh cache key builder (design+mesh+mounting/rear factor) |
| hornlab_search/mesh/build.py | 367 | build_mesh | mesh cache reader: load cached mesh metadata |
| hornlab_search/mesh/build.py | 370 | build_mesh | mesh cache reader: load cached mesh metadata |
| hornlab_search/mesh/build.py | 371 | build_mesh | mesh cache reader: copy a cached mesh into the run directory |
| hornlab_search/mesh/build.py | 372 | build_mesh | mesh cache reader: load cached mesh metadata |
| hornlab_search/mesh/build.py | 461 | build_mesh | mesh cache writer: copy the built mesh into the shared mesh cache |
| hornlab_search/report/html.py | 267 | _design_figures | report reader: load a run's response artifact |
| hornlab_search/search/evaluate.py | 828 | _seam_check | band-split seam probe: read a one-frequency response then write it; no producer-pin check |
| hornlab_search/search/evaluate.py | 830 | _seam_check | band-split seam probe: read a one-frequency response then write it; no producer-pin check |
| hornlab_search/search/evaluate.py | 842 | _seam_check | band-split seam probe: read a one-frequency response then write it; no producer-pin check |
| hornlab_search/search/evaluate.py | 1011 | prefetch_candidate | mesh cache read/write entry point |
| hornlab_search/search/evaluate.py | 1015 | prefetch_candidate | mesh prefetch key builder |
| hornlab_search/search/evaluate.py | 1179 | _compute_band_split | band-split per-band solve: read hit or write response; key is design+per-band-mesh+band-solve |
| hornlab_search/search/evaluate.py | 1211 | _compute_band_split | band-split per-band solve: read hit or write response; key is design+per-band-mesh+band-solve |
| hornlab_search/search/evaluate.py | 1212 | _compute_band_split | band-split per-band solve: read hit or write response; key is design+per-band-mesh+band-solve |
| hornlab_search/search/evaluate.py | 1234 | _compute_band_split | band-split per-band solve: read hit or write response; key is design+per-band-mesh+band-solve |
| hornlab_search/search/evaluate.py | 1397 | _compute_meh | MEH single-mesh solve: read hit or write the BEM response for CPU re-scoring; no producer-pin check |
| hornlab_search/search/evaluate.py | 1421 | _compute_meh | MEH single-mesh solve: read hit or write the BEM response for CPU re-scoring; no producer-pin check |
| hornlab_search/search/evaluate.py | 1492 | _compute_meh | MEH single-mesh solve: read hit or write the BEM response for CPU re-scoring; no producer-pin check |
| hornlab_search/search/evaluate.py | 1534 | _compute | normal single-mesh solve: read hit or write response; no producer-pin check |
| hornlab_search/search/evaluate.py | 1571 | _compute | normal single-mesh solve: read hit or write response; no producer-pin check |
| hornlab_search/search/evaluate.py | 1611 | _compute | normal single-mesh solve: read hit or write response; no producer-pin check |
| hornlab_search/search/evaluate.py | 1654 | _persist | run artifact copy of the response (not a cache lookup) |

- method: Python AST over the fixed consumer list; no module is imported or executed; call sites: 28
- missing consumer files: none

## Risk summary

- The key is design-mesh-solve. A successful lookup checks ok/readability but not the library pins that produced the response, so a legacy entry is reusable by identity alone.
- sampled unknown producer evidence: 400 (fraction 1.0)
- legacy reuse exposure: sampled unknown-producer entries are potentially reusable under today's lookup; this is a bounded sample, not a measured reuse count
- explicit unknowns:
  - producer provenance of unsampled entries
  - whether legacy entries were produced by the currently installed pins
  - actual reuse frequency and acoustic impact (no solves were run)
  - band-split/seam/trace coverage outside the sample

## Proposal (no enforcement)

- status: `proposal_only_no_enforcement`; behavior_changed: `false`
- policy: opt_in_producer_pin_v1 (default off (today's key/validity behavior is unchanged))
- rollout: ship the audit artifact only; no cache behavior change
- rollout: add a config/tool flag that is off by default and covers every solve-cache caller
- rollout: in an isolated temp root, prove producer evidence is written on new entries and that an unknown/mismatched legacy entry misses while an unchanged score-only hit still hits
- rollout: only after a separate approved slice, enable the flag for a bounded lane
- rollback: turn the opt-in flag off (default path is byte-compatible)
- rollback: delete only the temp-root fixtures, never production cache entries
- rollback: the audit artifact records the pre-change key/validity finding for comparison

Temp-only compatibility fixtures:
- new entry with producer pins -> hit
- entry with no producer pins -> unknown, opt-in miss
- entry with mismatched pins -> miss
- score-only re-scoring of an unchanged response -> hit
- band-split seam entry -> covered by the same policy
- trace/normal entry -> covered by the same policy

Callers an approved guard must cover:
- search/evaluate.py:_compute (normal single-mesh read/write)
- search/evaluate.py:_compute_band_split (per-band read/write)
- search/evaluate.py:_seam_check (seam-only read/write)
- search/evaluate.py:_compute_meh (MEH read/write)
- mesh/build.py (mesh-cache read/write, separate key space)
- report/compare/replay readers (run artifacts, not the shared solve cache)

## Completeness / exclusions

- runs/, dataset/, dataset_cpu/ (not solve-cache roots)
- mesh cache roots (different key space; source coverage only)
- unsampled entries beyond --sample-limit
- the real reuse fraction of legacy entries cannot be measured from a bounded sample
- whether every legacy producer used the same installed library pins is unknown
- band-split/seam/trace marker coverage is sampled, not an exhaustive census
- no measured solve-cost or ranking impact is claimed here
