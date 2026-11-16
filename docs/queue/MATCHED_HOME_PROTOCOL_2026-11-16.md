# Home comparison protocol

`tools/night_queue/run_matched_home.py` prepares one frozen cohort per task, then
runs six serial arms. Use a separate fresh root for each task; do not pool J across
briefs or tasks. Preparation builds a strict single-fidelity native training set,
requires at least 100 selected rows and matching dependency pins, and snapshots
exactly those selected designs and their replayed scores for the CMA warm start.
The manifest records hashes, seed order, selected IDs and budget conventions.
Each arm rebuilds the training selection and refuses changed inputs or records.

Order: CMA, scalar, TuRBO for seed 88101; TuRBO, CMA, scalar for 88102. CMA uses
the same cohort's best design and top-ten spread, with 80 new candidate attempts;
BO uses an 80 screen-call cap. Each arm selects up to two screened finalists for
verification. A missing or failed verification is incomplete, not a zero score.
Normal project caching is shared. The two budgeting systems do not guarantee an
equal number of physical BEM calls: report cache hits, refusals, observed and
inferred calls, wall time, and the best verified result, plus best-so-far curves
against a common achieved successful-query prefix. Compare normalized gain from
each task's own baseline; two seeds provide exploratory evidence, not a general
optimizer ranking. Acquisition/model setup and verification wall time matter.

```powershell
.venv\Scripts\python.exe tools\night_queue\run_matched_home.py prepare --root runs\matched_example --config examples\typologies\home_landscape_2026-11-15\hl__osse_rrect_fold_warm_v7.yaml
# Invoke each arm in the manifest order with the Bayesian interpreter and an outer timeout:
# run_matched_home.py arm --root runs\matched_example --method cma|scalar|turbo --seed 88101|88102
.venv\Scripts\python.exe tools\night_queue\run_matched_home.py report --root runs\matched_example
```

The report is descriptive and records incomplete arms. Inspect the underlying
study journals and run metadata for physical attempts and full wall-clock costs;
its observed/inferred ledger is not an exact physical-call audit. Use the same
verification and acoustic review standard on each finalist. Preparation alone
does not authorize or start a GPU job.
