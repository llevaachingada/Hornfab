# Parent M0 resume brief — canonical checkout

Status: resumed 2026-11-12 after owner consolidation. Supersedes the worktree layout in
`PARENT_M0_CONTRACT.md` for execution paths. The owner amendment in `AGENTS.md` now governs:
**one consolidated checkout**.

## Canonical execution tree

- Work in `C:\Users\hunte\Hrns\hornlab-search` on branch `main` (current `3d995a6`).
- Do **not** create worktrees, switch branches, stash, reset, rebase, commit, or push. Only the
  parent performs git mutations.
- The tree may be edited concurrently by other lanes. Touch only your owned files; never reformat
  or revert another lane's work.
- A GPU night queue is running from this checkout. **No BEM/GPU solves, no host cleanup, no killing
  processes, no queue edits.** The analysis lanes are CPU-only and read `dataset*`, `cache*`, `runs`
  read-only.
- Interpreter: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`.
- The S3 slice is already on main: `tools/analysis/_common.py` now has cost/replicate/compatibility
  helpers. Read them and reuse; do not edit `_common.py` or `schema.md` (parent owns the shared
  schema update).

## Lanes and ownership

| Lane | Owns | Must not edit |
|---|---|---|
| R0 | `hornlab_search/objective/replay.py` (new), `tools/analysis/offline_scores.py` (new), focused tests under `tests/test_obj_replay*.py`, `tests/test_tools_analysis_offline_scores*.py`; scratch `scratch/bo_m0/r0/` | `_common.py`, `schema.md`, dataset writer, solver, config, GUI, frozen contracts |
| S0 | `tools/analysis/catalog.py`, `tools/analysis/cohorts.py` (new), focused tests `tests/test_tools_analysis_catalog*.py`, `tests/test_tools_analysis_cohorts*.py`; scratch `scratch/bo_m0/s0/` | `_common.py`, `schema.md`, dataset writer, config, solver, GUI |
| B2 | `tools/analysis/parameter_activity.py`, `tools/analysis/geometry_effects.py` (new), `hornlab_search/bo/{__init__,encoding,data}.py` (new), focused tests; scratch `scratch/bo_m0/b2/` | `_common.py`, `schema.md`, scorer math, production configs/cache/search/writer/GUI |

Read the authoritative slice blocks in
`docs/research/DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md` (S0, R0, B2) and the governing
decisions in `docs/research/HORN_OPTIMIZATION_HARDENING_2026-11-12.md` and
`docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`. If a conflict remains, the
hardening decision + bo-study-v1.1 win.

## Resolved candidate task (parent-verified)

`examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml`, resolved through
`examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml`:

- objective v4; band 300–8000 Hz; 50°/50°; f0 1280 Hz; `cov_narrow_ratio=2.0`,
  `cov_below_f0=mask`, `diag_reference=round`
- weights: cov 1.0, rip 1.0, di 0.3, dislope 0.5, flat 0.5, load 0.0, distd 0.5, diag 0.5
- search keys (alphabetical, d=14): L_mm, a_deg, k, morph_corner_mm, morph_exponent, morph_fixed,
  morph_height_mm, morph_rate, morph_width_mm, n, q, s, s1, s2; seed hash `b930c6c35b14`
- `morph_exponent` is statically inactive only because `morph_target=1`; prove with source +
  geometry sampling, target 3 must be active. `morph_fixed` resolved bound is 0–0.6 (comment
  says 0–0.1; do not change the bound).
- ATH eligibility is still unproven; count it honestly. `insufficient_evidence` is a valid result.

## Priority deliverables (complete these first)

### R0
1. `replay.py`: pure, backend-free replay from stored `Evaluation`/record arrays and/or run-dir
   `response.npz`; original v4 parity first, then changed weights/tolerances and supported target
   changes. Emit the three identity hashes (physical/metric/score) and
   `exact_complete | partial_unsupported | additional_data_or_solve_required` per row with reasons.
2. `offline_scores.py` CLI: bounded read-only pilot over ATH-compatible rows; assert zero backend
   calls (monkeypatch/guard all solver factories) and no source mutation; JSON/MD with counts.
3. Preservation inventory: bounded counts/checksums for dataset/dataset_cpu, cache/solve,
   cache_cpu/solve, run/config/provenance, traces; a temp-root restore + rescore test.
4. Legacy surrogate audit: exact source lines, supported objective/input matrix, refusal/adapter
   gap; do not fabricate impedance or metrics.

### S0
1. `catalog.py`: stream closed shards / committed prefixes; validate metadata/index/NPZ coherence;
   separate rows, records, unique geometry/solve/score/experiment identities; preserve provenance
   and explicit unknowns; deterministic JSON/CSV export.
2. `cohorts.py`: operation-specific comparability (performance, backend parity, fidelity, optimizer
   A/B), allowed differences, exclusions; ATH census by brief/objective/mesh/solve/software.
3. Bounded pilot into `scratch/bo_m0/s0/`; exact ATH counts or `insufficient_evidence`.

### B2
1. `parameter_activity.py`: searched/fixed/derived/conditional/inactive/unresolved ledger for the
   ATH config; source refs, units, predicates; static + geometry-test evidence.
2. `geometry_effects.py`: canonical final-surface sampler using installed
   `hornlab_mesher`/geometry/profile APIs; H/V/diagonal contours, physical/normalized z, units,
   convergence; target-1 exponent invariance, target-3 activity; never change cache keys.
3. `bo/encoding.py` + `bo/data.py`: alphabetical key order, `active-projection-v1` (only proven
   no-ops, reversible), full-vector reconstruction, bound/log transforms, min/cap subset and
   deterministic IDs; `TrainingSet` fixture. **Do not implement scorer math**; `bo/metrics.py` is
   deferred until R0 lands.
4. Pool 4096: cheap checks only, dedup/novelty/rejection report, "mesh/acoustic eligibility
   unknown"; no mesh builds.

## Reporting

Return: changed files + `git status --short`; exact commands and pass/fail counts; API signatures
and reason codes; real counts/exclusions; blockers with file:line; untested limits. No commits,
pushes, merges, BEM/GPU, live-data writes, or changes outside your ownership.

If blocked twice on the same error, stop and report the exact error. Do not improvise an
architecture or substitute a different algorithm.
