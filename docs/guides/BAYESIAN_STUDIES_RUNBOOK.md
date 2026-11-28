# Bayesian design studies

The Studies workspace lives under **Analysis → Studies**. Scalar, TuRBO and
Pareto v4/v7 studies use the existing geometry, mesh, BEM, score and dataset
pipeline. Proposal fitting runs on **CPU** in the optional Bayesian interpreter.
Each solve study runs serially in a separate process and takes exclusive
ownership of its selected solve lane.

## Environment

The normal GUI/CMA interpreter remains `.venv/Scripts/python.exe`. Study workers
prefer a current interpreter containing Torch, BoTorch, GPyTorch and the mesher;
otherwise they select `../oc-wt/bo-study/bayes-venv/Scripts/python.exe`.
That isolated environment now contains the project's pinned HornLab dependencies.
Rebuild it from the canonical checkout with its interpreter and
`-m pip install -e ".[bayes,dev]"`. Never hand-edit installed packages.

Installed engine (measured 2026-11-15): `torch 2.14.1+cpu`, `botorch 0.18.1`,
`gpytorch 1.15.2`, `linear_operator 0.6.1`, `ninja 1.13.2`. The main `.venv`
has `torch` but **no** `botorch`/`gpytorch`, so it cannot run a proposal.

### Why the GP fit stays on the CPU (RTX 4060 present)

The model is locked to `float64` (`bo/model.py:14`, spec §3.3) and that is not an
oversight:

| Fact | Consequence |
|---|---|
| Consumer Ada (AD107/RTX 4060) runs FP64 at **1/64** of FP32 — ~0.23 TFLOPS from the 15 TFLOPS FP32 spec ([Ada whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/ada/nvidia-ada-gpu-architecture.pdf), [4060 specs](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4060-4060ti/)) | A `n=256` Cholesky is ~24 µs of FP64 arithmetic; kernel launch + cuSOLVER dispatch costs the same order. No throughput win. |
| BoTorch maintainers: BO tensors are small, so GPU utilisation — and speedup — is limited ([#2318](https://github.com/meta-pytorch/botorch/issues/2318)); float64 is strongly recommended ([#1444](https://github.com/meta-pytorch/botorch/discussions/1444)) | An exact GP with `n ≤ 256`, `d ≤ 20` is a CPU-sized problem. |
| A PyTorch CUDA context costs ~0.5–1.2 GB VRAM on Windows ([measurement](https://forums.developer.nvidia.com/t/how-to-understand-the-memory-footprint-of-cuda-context/320393)), and WDDM silently backs allocations with system RAM ([WDDM 2.0](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/gpu-virtual-memory-in-wddm-2-0)) | On an 8 GB card shared with the BEM solver, a torch CUDA context buys nothing and risks the exact "false OOM / 5-10x slow solve" failure mode this repo already documents. |
| BoTorch's fused `qLogEHVI` kernel **only runs on CPU** ([source](https://github.com/meta-pytorch/botorch/blob/main/botorch/acquisition/multi_objective/logei.py)) | Moving the loop to CUDA would *lose* the Pareto speedup, not gain one. |

So: BEM solves use the GPU; the surrogate, acquisition and refits stay on the CPU
in float64. If a future profile shows acquisition dominating the loop, test a
**CUDA float32 acquisition-only** variant in isolation — never fit the exact GP in
float32 and call it equivalent.

### Fused `qLogEHVI` kernel (ninja + MSVC, built once and installed)

`pip install ninja` alone is not enough on Windows: the JIT also needs MSVC `cl.exe`, which is only on
`PATH` inside a Developer Command Prompt — and BoTorch checks `ninja`/`cl` *before* it reuses its own
build cache, so a plain shell kept falling back to the pure-Python kernel even with a cached build.

Fixed 2026-11-15 by compiling once and installing the module where BoTorch looks first
(`import logei_fused_ext`), so no shell setup is needed at run time:

```powershell
$bayes = 'C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe'
# one-off build inside a vcvars shell
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set PATH=C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts;%PATH%
& $bayes -m pytest tests/test_bo_pareto.py -q          # triggers the JIT build into the torch cache
# install the built module so BoTorch imports it directly (no ninja/cl/PATH needed afterwards)
copy "%LOCALAPPDATA%\torch_extensions\torch_extensions\Cache\py312_cpu\logei_fused_ext\logei_fused_ext.pyd" `
     "C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Lib\site-packages\logei_fused_ext.pyd"
```

Verified: `botorch.acquisition.multi_objective.logei._C is not None` and the Pareto suites run with no
"Falling back to the pure-Python implementation" warning and no venv on `PATH`.

The compiled module is ABI-bound to **this** Python (3.12) and torch (2.14.1+cpu). After a torch or
Python upgrade in the bayes venv, delete the `.pyd` and repeat the four lines. If it is missing, BO is
still correct — only the Pareto acquisition is ~3x slower.

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
   initial proposal, stop rules and fixed budget. Named budget profiles
   (`hornlab_search/studies/package.py`): `baseline` = 18 screens + 6 verification
   calls (24 total, 120 attempts, the frozen bo-study-v1.1 budget and the default);
   `comparison-25` = 25 + 6 (31, 150); `comparison-30` = 30 + 6 (36, 180);
   `comparison-60` = 60 + 6 (66, 300). Verify stays 6 in every profile because the
   verification rule is frozen at 4 finalists + 2 audits. Failed and unknown calls
   consume budget; cache hits do not consume new BEM calls. A package cannot carry
   a budget that differs from its named profile.
6. Launch. Cancellation stops scheduling after the current candidate. The journal
   records intent before dispatch. Watch measured progress and refusal reasons.
7. Inspect measured finalists and audit results, then record a decision/export.

Production execution supports **scalar**, **turbo** and **pareto** policies
(`studies/production.py:50`). `cma_seed` and `exploration` are non-BO adapter
surfaces: they are capability-gated and are refused by the production worker.
The GUI offers all five cards, including "scalar, trust region" (TuRBO); `turbo`
needs a candidate pool and a training set, and `pareto` additionally needs frozen
`pareto_metrics` bindings.

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
