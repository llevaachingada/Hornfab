# bo-study-v1.1: continuation and original slice map

**Next agent: read this file first, then `C:\Users\hunte\Hrns\oc-wt\bo-study\AGENT_HANDOFF_2026-11-12.md` for the frozen task, data locations, prior evidence and constraints.** This document records a snapshot on 2026-11-13; inspect live state again before editing because another process was still working in the shared checkout during this handoff.

## Authority and checkout

- Repository: `C:\Users\hunte\Hrns\hornlab-search`, branch `main`. Read `AGENTS.md`, then `docs/research/HORN_OPTIMIZATION_HARDENING_2026-11-12.md`, `docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`, and the full relevant verbatim slice blocks in `docs/research/DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md`. Also read `C:\Users\hunte\Hrns\oc-wt\bo-study\PARENT_M0_FREEZE.md` and `PARENT_DEPENDENCY_DECISION.md`. The original older handoff remains useful, but its statements about running lanes and commit state have aged.
- Last observed `HEAD` was `c4fc315`, local `main` two commits ahead of `origin/main`: `3a48c27` (M0 artifacts) and `c4fc315` (S4/S6 artifacts). This is a point-in-time observation, not an assertion that the whole plan is committed. Run `git status --short --branch` and inspect `git log` first. Many `bo/`, `studies/`, GUI, tests, tools and docs files are untracked or modified. Preserve all of them, including changes from other sessions. Do not stage whole directories blindly or overwrite unrelated GUI work. Only the integrating parent performs Git mutations; no push without task authorization and repository rules.
- **Concurrent work:** after this chat's agents were interrupted, a separate PowerShell/Python process was observed generating B2 metric and native TrainingSet scratch artifacts, and files including `bo/data.py`, `bo/metrics.py`, and `tools/experiments/manifest.py` changed. Another integrator made the two commits above. Coordinate with the other active owner before assigning overlapping files, and recheck processes/file mtimes; do not kill processes. Earlier passing test results may no longer describe current code.
- The night GPU queue, search, worker host and GUI were observed active. **Do not run BEM/GPU/CPU solves, edit live queues/datasets/caches, clean hosts, or kill workers.** Preserve live data read-only; follow snapshot-hash rules. Real pilot execution, default flips, v8 registration and spending remain separately gated.
- Project Python: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`. Isolated CPU BoTorch Python: `C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe`. No dependency changes to the live solver venv.

## Immediate integration break discovered during handoff

The combined project-environment test collection failed:

```text
ImportError: cannot import name 'parse_results' from 'tools.experiments.manifest'
  tests/test_experiment_manifest.py:6
```

The earlier small S11 draft API (`prepare`, `validate`, `parse_results`) was superseded in the shared checkout by a much larger `tools/experiments/manifest.py` with `build_manifest`, `validate_manifest` and other functions; a second test file, `tests/test_tools_experiments_manifest.py`, targets it. Reconcile both implementations and their tests by inspecting intent and ownership; **do not delete or skip a test to force a pass**. Determine whether adapters or a faithful test migration are appropriate and preserve failure/unknown handling and both pilot requirements. There may be other concurrent integration collisions.

Fresh read-only validation during this handoff:

- Isolated BoTorch: `& 'C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe' -m pytest -q tests/test_bo_model.py tests/test_bo_acquisition.py tests/test_bo_propose.py tests/test_bo_pareto.py -p no:cacheprovider` — **44 passed**. Warnings include qLogEHVI C++ extension fallback, a Cholesky jitter warning, PyTorch deprecation, and an unknown pytest `timeout` configuration option; no performance claim follows.
- Project venv: the broad targeted suite covering B2/B3-adjacent adapters, B1/B4/B5/B6/B7/B8 tests, new S11 tests, and S9 tests passed **when the collection-breaking older S11 test was excluded**. Exact command used:

```powershell
& '.venv\Scripts\python.exe' -m pytest -q tests/test_bo_data.py tests/test_bo_encoding.py tests/test_bo_cohort_gate.py tests/test_bo_metrics_adapter.py tests/test_bo_metrics.py tests/test_bo_pipeline.py tests/test_bo_sensitivity.py tests/test_bo_pareto.py tests/test_bo_extensions.py tests/test_b8_foundation_adversarial.py tests/test_b8_study_integration.py tests/test_gui_studies_api.py tests/test_gui_studies_module.py tests/test_gui_study_adapters.py tests/test_studies_b5_runner.py tests/test_studies_b5_integration.py tests/test_studies_registry_b1.py tests/test_tools_experiments_manifest.py tests/test_bench_s9_timing_ledger.py tests/test_tools_bench_fake_harness.py -p no:cacheprovider
```

The successful subset does not excuse the collection failure. No full repo suite, real acoustic validation, benchmark, or end-to-end CLI/API/GUI completion has been established in this handoff.

## Milestone map against protocol §7

| Original milestone | Evidence present | Remaining acceptance / status |
|---|---|---|
| **M0** | R0 replay/census, S0 cohort tools, S3 cost accounting, B2 encoding/activity/geometry exist; commits above and prior handoff record earlier offline parity and census. B2 now additionally has metrics, cohort, pipeline and native-data code in the dirty tree. | Earlier M0 evidence is historical and must be checked against live artifacts. `build_native_training_set` and `cohort`/`pipeline` are separate paths; audit that every actual model caller enforces equivalent source, score and metric policy rather than bypassing the strict gate. Check F0 typed outcome requirements rather than declaring all M0 complete. |
| **M1** | S4/S6 files committed in `c4fc315`; S10 renderer is in dirty GUI files. S4 was corrected to suppress unsupported recommendations and treat unsupported interactions conservatively. | Revalidate S4/S6 and actual current scratch artifact after changes; prove selectable actual knob → geometry → measured response → versioned score workflow in the GUI. Existing GUI state is shared and visually unverified. Some broader S4/S6 prompt acceptance remains beyond initial M1 report. |
| **M2 + parent gate** | B3 CPU scalar model/acquisition/proposal and focused tests; B2 physical metrics and a strict but caller-attested cohort gate; `tools/analysis/bo_sensitivity.py` harness. | **Gate not established.** Verify real source-evidenced comparable cohort, selected IDs, holdout/group integrity and no bypass; execute/report prespecified alternative subset, 0.1/1/10 noise, two independent pool-seed sensitivity and simple/CMA comparison where evidence exists. Harness explicitly leaves `gate_pass` null and needs real validated inputs/callbacks. A positive real optimization benchmark is not required to write offline M3, but passing tests or synthetic data does not prove M2. |
| **M3A** | Draft SQLite registry, view/job adapters, HTTP routes and study UI exist; offline temp tests run. | Full schema/readiness semantics, artifacts, service integration, available actions, actual CPU job adapters and complete UI workflow remain to be proved; current readiness intentionally marks semantic validity unverified and dispatch false. |
| **M3B** | Fake-backed serial runner/journal/lane and Pareto/constraint/cost/trust primitives exist with focused tests. A temporary SQLite + fake-evaluator crash/recovery/verification test exists. | Complete real adapter wiring and checkpoint/observation replay proof, exact package/root/budget/ownership contract, all B7 engines and B8 end-to-end acceptance. `DraftAttemptJournal` intentionally has no `durable_contract` marker; do not add it solely to bypass the gate. F1 remains separately required for QD paths. No real launch. |

## Original slice-by-slice status and next work

| Slice | Status, current implementation, required next action |
|---|---|
| **S0 / R0** | Earlier implemented and committed: `tools/analysis/{catalog,cohorts,offline_scores}.py`, `objective/replay.py`; join by `(root, shard_index, row)` and use `scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json`, not the default 50-row display artifact. Revalidate evidence/identities as needed; never mix physical, metric and score IDs. |
| **S1** | Conditional on warm-start/QD and affected search paths. Inspect existing `cma_me.py` and config tests before claiming either bug fixed; implement exact archive/failed-outcome safeguards in original S1 when needed. |
| **S2** | Original scope is read-only audit; enforcement separately gated. Verify whether audit exists, otherwise inventory producer evidence and caller paths in scratch. No cache behavior change or cleanup. |
| **S3** | Previously committed in `dabb5d1` / merge `7997259`; consult `_common.py`, `seed_variance.py`, `ab_compare.py` and prior evidence. Confirm cost/replicate compatibility when reused. |
| **S4** | `tools/analysis/parameter_study.py`, tests committed. Group evidence absent is descriptive; no supported ranking without group/stability proof. Check fresh JSON before treating previous scratch output as current, and finish any broader prompt items not covered by the M1 report. |
| **S5** | `tools/analysis/seed_pack.py` was absent at last inspection. Implement compatible diverse actual-design seed packs, generator round-trip and reviewed existing-key overlays after prerequisites; no fabricated warm starts. |
| **S6** | `tools/analysis/source_fidelity.py` and tests committed; source/fidelity cards and conservative pairing. Complete any original S6 fidelity calibration/verification acceptance not covered by cards. |
| **S7** | Original existing-surrogate/LQ validation and replay work is not established by B3. Audit and implement per original S7, especially chronological resume/leakage, only within agreed ownership. |
| **S8** | Original geometry/behavior discovery, hypothesis cards and corrected QD/Pareto comparisons are not established by B7 Pareto primitives. S1/F1 gates bind QD. New MEH remains paused. |
| **S9** | `tools/bench/timing_ledger.py`, `tools/bench/fake_harness.py`, tests and `docs/throughput/S9_PERFORMANCE_PREPARATION_2026-11-12.md` are present in the dirty tree. Reconcile any parallel work, verify fake-only preparation against the original acceptance; real benchmarking is separately scheduled. |
| **S10** | `gui/data.py`, `gui/static/app.js`, `tests/test_gui_views_analysis_m1.py` contain report additions but are mixed with unrelated pre-existing/concurrent GUI changes. Revalidate behavior and preserve others' work; browser visual QA remains open. |
| **S11** | `tools/experiments/manifest.py` now appears to have been replaced by another active implementation; two incompatible test APIs coexist. First fix collection conflict above, then map full two-pilot predeclared inputs, cost accounting, pins, outputs, practical thresholds and estimates against S11. Missing evidence must remain blocked, not invented. |
| **B1** | `studies/{schema,store,service}.py`: SQLite, immutable artifacts, revision/idempotency, draft dependency readiness and `DraftAttemptJournal`. Review schema, migrations, dependency DAG, semantics, package binding, concurrency, observation/proposal persistence and recovery. `readiness()` currently does not authorize execution. |
| **B2** | `bo/{encoding,data,metrics,cohort,pipeline}.py`: projection, numeric subset/pool, strict metric support and evidence-gated fit seam. Other work added `build_native_training_set` and another metric policy API; reconcile them and all callers, preserving exact v4 ratio 2 and response-detrended ripple. Avoid assuming caller-provided evidence proves source compatibility. |
| **B3** | `bo/{model,acquisition,propose}.py`: qLogNEI, fixed-noise checks, geometry-ID tie breaks, pending points and selected-candidate rematerialization. Isolated 44-test command above includes B3/B7; still review full provenance, immutable proposal and real sensitivity evidence. |
| **B4** | `gui/{data_studies,study_jobs}.py`, `gui/server.py`: typed panels/registry-backed job seam, basic HTTP integration. Trusted dispatcher/prerequisite/artifact validators and correct error/status mappings need full wiring and tests. Do not create a second registry. |
| **B5** | `studies/{runner,reconcile,lanes}.py`, journal in `service.py`, fake and SQLite integration tests. Inspect newest changes to observation replay and proposal RNG/cadence before claiming them complete. Finish actual adapter contracts, recovery, candidate/verify caps, launch idempotency, CPU/GPU ownership, package root binding and full crash tests. Real dispatch stays disabled until verified and separately authorized. |
| **B6** | `gui/static/studies.js`, app routes and server routes: list/create draft, six views, guarded action/UI scaffolding and return links. Current server panels are mostly missing/partial/unknown and do not offer a full actionable workflow. Wire actual validated evidence/actions and test end-to-end; preserve old routes, poll disposal, origin/host/path protections and visual QA. |
| **B7** | `bo/pareto.py`, `bo/extensions.py`: physical frontier/reference/subset, independent models, qLogNEHVI, signed loading margins, cost scoring/model and trust-region primitives. Review selected-cohort and per-observation metric binding, constrained feasible seed/boundary-data/calibration, timing provenance, cadence, revalidation and complete protocol §3.5–3.6. This is not proof the three sequential engine slices or persistent integration are complete. Multi-fidelity GP remains deferred per protocol. |
| **B8** | Focused adversarial tests plus fake SQLite runner flow exist; full create→snapshot→explain→scalar/Pareto→package→dry-run→fake screen/verify/audit→refit→decision/export/child through service, CLI, HTTP and GUI is not demonstrated. Complete independently and report all limitations. |
| **F0 / F1** | Original prompt blocks are in `DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md` after R0. Search at handoff found no `resample_strict` or `retry_same_then_stop` in `hornlab_search/search` / `config.py`; do not assume these are done. F0 typed outcome isolation and F1 QD scheduler/archive safety remain planned, with opt-in behavior and no default flips. Recheck live source before implementing. |

## Suggested next dispatch: parallel ownership, then integrate

User explicitly requested aggressive parallel work with Terra medium agents where appropriate; the parent keeps senior contract/integration decisions. Use the shared checkout with nonoverlapping ownership, coordinate with any *other* live integrator, and preserve dirty files. These prompts are self-contained; each agent must read the authoritative original slice before editing. Each worker reports exact commands/results and no commits. Do not misrepresent a fixture as a real pilot.

### Lane 1 — S11 collision and pilot preparation

```text
Model: gpt-6.1-terra | Thinking: medium
FIRST READ C:\Users\hunte\Hrns\oc-wt\bo-study\CONTINUATION_SLICE_MAP_2026-11-13.md, then AGENTS.md and original S11 in docs/research/DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md. Work in C:\Users\hunte\Hrns\hornlab-search. Coordinate any other owner first. Own tools/experiments/** and focused experiment tests only. Reconcile the current parse_results/prepare/validate test-collection failure with the later build_manifest/validate_manifest implementation without weakening or skipping tests. Preserve both pilots, truthful unknown/failure outcomes, explicit cost/pin/threshold gaps and no execution. Complete all evidence-supported S11 preparation and run both experiment test files. Return precise remaining decisions and command output; no solves, git mutations, or source-data writes.
```

### Lane 2 — B2/B3/M2 integration and diagnostics

```text
Model: gpt-6.1-terra | Thinking: medium
FIRST READ C:\Users\hunte\Hrns\oc-wt\bo-study\CONTINUATION_SLICE_MAP_2026-11-13.md, AGENTS.md, frozen M0 contract, and original B2/B3/B8 plus protocol §3. Work in the shared canonical checkout only after checking whether another owner is still modifying bo/data.py or bo/metrics.py. Own agreed bo data/cohort/pipeline/diagnostics files and uniquely named tests; do not edit B1/B4/B5/GUI. Reconcile the competing native TrainingSet and strict cohort paths; enforce actual source/score/fidelity/metric support without deriving comparability from row-specific hashes. Run real-data read-only source checks and prescribed subset/noise/pool diagnostics only where provenance supports them. Report verified vs caller-attested identity, exclusions, commands, and whether M2 gate is met; no BEM, live-data writes, dependency installs or git mutations.
```

### Lane 3 — B1/B5 recovery and B8 offline loop

```text
Model: gpt-6.1-terra | Thinking: medium
FIRST READ C:\Users\hunte\Hrns\oc-wt\bo-study\CONTINUATION_SLICE_MAP_2026-11-13.md, AGENTS.md, original B1/B5/B8 and protocol §§2,4,6. Shared checkout; coordinate B1/B5 ownership and do not edit GUI or bo math. Audit latest DraftAttemptJournal, runner, lane and replay changes; finish exact durable observation/refit/cadence/RNG resume and package/root/budget/unknown-state contracts with temporary SQLite and fake evaluators, including crash boundaries, duplicate launch, verify/audit candidates and no GPU cleanup. Exercise integrated offline workflow. Do not activate real dispatch by adding a marker without verified prerequisites; no solves, queue/runtime data writes or git mutations. Report exact remaining interface gaps and tests.
```

**Parent / subsequent lanes:** review the three outputs; fix shared integration and full UI B4/B6 with existing work, then independently validate B7 and B8. Run S5/S7/S8 and conditional S1/F0/F1 from their original blocks in dependency order and coordinate any shared search/config ownership. The user's request was the full plan, not permission to call an intermediate milestone complete.

## Notes on source evidence and verification

- Frozen task is native-only ATH v4, `active-projection-v1` d=13. Brief target is authoritative for replay, stored target is parity comparator, and parity applies only to identical target keys. Do not use `V8Params.for_class('A')`, change frozen math, register v8, rank J across versions, or label cheap candidate checks as acoustic feasibility.
- `scratch/` is gitignored and the live dataset can grow. Recheck generated timestamps and complete row support; earlier counts and prior test results are snapshots. Hash read inputs and avoid writing live roots. S10 fixtures needed by committed tests must be tracked or inlined.
- No web research was required for this status/handoff; future new feature/integration work must follow the user's instruction to check current primary-source best practices.
