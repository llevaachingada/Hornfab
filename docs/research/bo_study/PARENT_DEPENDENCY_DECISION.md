# Parent dependency decision — BoTorch (M2)

Date: 2026-11-12. Scope: isolated proposal engine only. The live solving venv
`C:\Users\hunte\Hrns\hornlab-search\.venv` is unchanged; BoTorch is absent there by design.

## Isolated environment (created, smoke-tested)

- Path: `C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv`
- Python: 3.12.10 (same minor as the project venv)
- CPU-only torch; no CUDA initialization and no `.cuda()` allowed in proposal jobs.

Resolved pins (actual installed versions, verified by import):

| Package | Version |
|---|---|
| torch | 2.14.1+cpu |
| botorch | 0.18.1 |
| gpytorch | 1.15.2 |
| linear_operator | 0.6.1 |
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| scikit-learn | 1.9.1 |
| multipledispatch | 1.0.0 |
| pyre_extensions | 0.0.32 |
| threadpoolctl | 3.8.0 |
| ninja | 1.13.2 |

BoTorch 0.18.1 metadata requires Python >=3.11, torch>=2.4, gpytorch>=1.15.2,
linear_operator>=0.6.1; these pins satisfy it.

## Execution contract

- Run proposal/model code with the isolated interpreter and the canonical checkout as cwd, e.g.
  `& C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe -m pytest <bo tests>` from
  `C:\Users\hunte\Hrns\hornlab-search`.
- Import BoTorch lazily inside the optional engine; never at GUI/CMA startup.
- `torch.set_num_threads(2)`; float64 tensors on CPU only.
- No installation, upgrade, or removal in the live venv. No shared lockfile changes until the
  parent reviews the extra.
- The study engine must return a tagged `model_unavailable` / `capability_missing` result when the
  optional engine is absent; the normal GUI/CMA path must work without this venv.
