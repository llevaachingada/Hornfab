# Scalar Bayesian design studies

The Studies workspace lives under **Analysis → Studies**. Scalar v4/v7 studies
use the existing geometry, mesh, BEM, score and dataset pipeline. Proposal fitting
runs on CPU in the optional Bayesian interpreter. Each solve study runs serially
in a separate process and takes exclusive ownership of its selected solve lane.

## Environment

The normal GUI/CMA interpreter remains `.venv/Scripts/python.exe`. Study workers
prefer a current interpreter containing Torch, BoTorch, GPyTorch and the mesher;
otherwise they select `../oc-wt/bo-study/bayes-venv/Scripts/python.exe`.
That isolated environment now contains the project's pinned HornLab dependencies.
Rebuild it from the canonical checkout with its interpreter and
`-m pip install -e ".[bayes,dev]"`. Never hand-edit installed packages.

## Prepare evidence

Use one task, objective version, backend and screen fidelity. The intake tool
reads source records and response arrays without constructing a writable dataset
store. It chooses one homogeneous dependency/grid/brief group and discloses other
groups. Replay calls the canonical scorer; predictions never become observations.

```powershell
.venv\Scripts\python.exe -m tools.analysis.study_cohort `
  --config examples/typologies/print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7_seed5678.yaml `
  --dataset dataset --out scratch/my-study-cohort --limit 256
```

The output supplies the three source fields for a new GUI study: `scores_json`,
`catalog_csv`, `dataset_root`. Use the current solver seed-5678 task for this
config. The original home config and native ATH v4 validation task are separate
tasks; they do not implicitly share historical labels. Missing dependency pins or
a cohort produced by a different installed stack prevent execution.

## GUI workflow

1. Save a question, task and the explicit source paths under Analysis → Studies.
2. Build snapshot and analyze compatible data. Inspect counts and exclusions.
3. Generate a scalar proposal. The seeded Sobol pool is generated automatically
   for home tasks; an explicit `pool_json` may supply a previously frozen pool.
4. Inspect candidate parameters and predicted uncertainty. The canonical geometry
   includes the same links and derived throat coupling used during evaluation.
5. Prepare a package with lane and a timezone-aware deadline. Review its hashes,
   initial proposal, stop rules and fixed budget: 18 screens, 6 verification/audit
   calls, 24 calls total and 120 attempts. Failed and unknown calls consume budget;
   cache hits do not consume new BEM calls.
6. Launch. Cancellation stops scheduling after the current candidate. The journal
   records intent before dispatch. Watch measured progress and refusal reasons.
7. Inspect measured finalists and audit results, then record a decision/export.

Production execution currently supports **scalar** policy. Pareto, CMA seed and
exploration adapter APIs remain separate capability-gated surfaces.

## CLI and recovery

The existing `study create/snapshot/analyze/propose/package` commands expose the
same artifacts. Paths for command output/package files must remain under the
explicit study root. Use `--expected-revision` on analyze/propose workers.

```powershell
$studyPython = 'C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe'
& $studyPython -m hornlab_search.studies.cli run `
  --root C:\path\to\study-root --package package.json --dry-run
& $studyPython -m hornlab_search.studies.cli run `
  --root C:\path\to\study-root --package package.json --execute `
  --project-root C:\Users\hunte\Hrns\hornlab-search
```

The execution flag is explicit. A package pins source config/brief bytes,
transitive artifacts, execution code and dependencies. Code/config changes
require a new package/study revision. Historical observations survive adaptive
refits and resume; verification observations do not enter the screen model.

After a worker crash, `study reconcile --root ROOT --study ID --project-root REPO`
matches exact persisted attempt evidence. It releases a crashed claim only after
proving the owning process is dead. Ambiguous attempts retain reservations and
are never automatically solved again. GUI CPU jobs recovered after a server
restart are labelled unknown and are not automatically relaunched.

Completed pipeline outputs are under `runs/study-<package-prefix>/screen` and
`verify`; worker logs/results are under `<study-root>/workers/<package-id>`.
Registry observations preserve exact candidate/result links. A successful pilot
demonstrates execution readiness; comparative acoustic benefit requires a matched
CMA campaign and independently verified finalists.
