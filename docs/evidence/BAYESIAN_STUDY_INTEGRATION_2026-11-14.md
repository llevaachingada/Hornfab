# Scalar Bayesian study integration — 2026-11-14

Scope: real v7 proposal → serial GPU screens → adaptive refits → finalist/audit
verification, with normal pipeline persistence and canonical replay eligibility.
Machine: local Windows workstation; hardware and solver pins are in TOOLCHAIN.md.

## Real pilot [measured]

Study `4804816e4ac745eeb61f0dd43dde6d68`; package
`72834b64942a29f1dd7d3e1cfb34bd39e8bb45a0d68979803a3bec027b9a0247`.
The source task is `p80x60__osse_ext_throat_home700_v7_seed5678`, objective v7,
with 64 canonical screen observations selected from 185 compatible source rows.
The frozen 4096-Sobol pool retained 1692 cheap-check-passed candidates. The
mesher pin is `55da4f46d662d8dcd7a9f94a609eeea4009fcd62`; BEAT pin is
`38e5b1f8ca840ebf6351c54611a08fedb1a0750f`. Torch is CPU-only in the isolated
combined Bayesian interpreter; the actual BEM solves use CUDA.

RECONSTRUCTED invocation (canonical checkout as working directory):

```powershell
$env:HORNLAB_GPU_LOCK='refuse'
& ..\oc-wt\bo-study\bayes-venv\Scripts\python.exe -m hornlab_search.studies.cli run --root scratch/2026-11-14_bayes/pilot --package package.json --execute --project-root C:\Users\hunte\Hrns\hornlab-search
```

Verbatim terminal result, from `scratch/2026-11-14_bayes/live_pilot_final.log`
(the preceding library warnings are omitted):

```json
{"ok":true,"package_id":"72834b64942a29f1dd7d3e1cfb34bd39e8bb45a0d68979803a3bec027b9a0247","progress":{"attempts":26,"consecutive_failures":0,"reservations":{"screen_calls":0,"total_calls":0,"verify_calls":0},"screen_calls":18,"total_calls":24,"unresolved":false,"verify_calls":6,"verify_candidates":6},"run_dir":"C:\\Users\\hunte\\Hrns\\hornlab-search\\runs\\study-72834b64942a29f1","status":"pool_exhausted"}
```

The runner's terminal `pool_exhausted` means there are no remaining permitted
screen/verification candidates under this package. All 24 call units completed;
the candidate pool itself still contains unselected designs. The 26 attempts
include two cheap refusals that consumed no BEM-call unit. The four finalists
and two seeded audits all verified, with zero selection shortfall.

The read-only `scratch/2026-11-14_bayes/summarize.py` checks the result sidecars
and registry. Its `summary.json` records 24 `exact_complete` canonical replays,
maximum absolute live/replay score delta zero, and best measured screen J
`3.105495448486849`. These are integration observations, not a matched comparison
against CMA or a claim of acoustic superiority. Raw response files remain in
`runs/study-72834b64942a29f1/{screen,verify}`; measured records remain in dataset.

## Interrupted rehearsal and final hardening

The earlier package `3e3fa8aa05b730bcdf90a6aa17907b6d624255d427d3a12dd6f60d679d1e79ab`
encountered a worker-host connection reset and an existing backend-internal retry.
It was cooperatively cancelled after one successful, exact-replayed screen.
That rehearsal does not establish correct call-budget accounting because its
retry occurred inside one journal reservation. The completed pilot above uses
`retry_worker_exit=False`; each subsequent backend attempt is journal-owned.

After the completed pilot, duplicate-execution ownership publication was moved
after a successful atomic claim, and conflicting executions were prevented from
rewriting the original process/run/result identity. Package source coverage was
expanded to all executable Python files. These final guards are regression-tested;
the live pilot ran the numerical/execution path before those two guards changed.
Its completed package is therefore historical evidence, not a resumable package
under the final code hashes. Prepare a new study/package for the next run.

## Validation artifacts and GUI

The broad pre-hardening offline suite completed with 3833 passed and 19 optional
engine skips; its source is `scratch/2026-11-14_bayes/offline_final.{log,xml}`.
The combined-engine integration run had 128 tests, zero failures/errors/skips,
recorded in `integration_final.{log,xml}`. Final hardening tests and the final
broad release suite are recorded separately as `hardening.{log,xml}` and
`release.{log,xml}` so earlier intermediate passes are not mistaken for signoff.

Browser clickthrough verified task/source inputs, the ready scalar proposal and
its credible interval, package budgets, durable running counters, duplicate
launch disabling, cooperative stop controls, and the export link. Final-stage
render/lifecycle checks are in `tests/study_gui_final_stages.mjs` and
`tests/gui_study_lifecycle.mjs`. No default optimizer or horn brief was changed.

## Final release validation and remaining timing limit

The final broad run (`release.xml`) recorded **3840 passed, 19 skipped, three
failures** in 771.29 s. Two were existing wall-clock assertions (500 dataset
appends <5 s and the pre-mesh refusal guard <100 ms). The third was the previous
polling contract collected before its source/test update. The corrected lifecycle
and ownership guard set subsequently passed all 25 tests (`final_guards.xml`),
and all 116 study-focused tests passed (`study_release.xml`).

The unchanged thresholds were rerun without the six-worker suite. Dataset append
and the corrected polling test passed. The mesh guard still failed at **104.4 ms**
against its existing **100 ms** limit; its no-mesh-written assertion passed.
`release_rerun.xml` therefore records two passes and one failure. Separate owner
CPU/GPU jobs were active; they were preserved. No timing threshold was loosened.
The full suite is **not claimed green**. This remaining unmodified performance
check needs a quiet-host rerun or its own measured performance investigation.

Verbatim tail from `release_rerun.log` (preceding traceback omitted):

```text
MeshTooLargeError raised in 104.4 ms
=========================== short test summary info ===========================
FAILED tests/test_mesh_build.py::test_too_large_is_refused_before_any_mesh_is_written
```

The implementation was included by a concurrent owner-authorized commit
`5e86c8b`; final validation is recorded separately without rewriting that commit.
