# Cloud handoff: finish the BoTorch GUI on `feat/bo-gui` (token-lean)

**Authoritative scope for the cloud session.** It supersedes the work-package list in
`BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md`. Most of that plan **already exists on this branch**
(see `BO_GUI_DESIGN_2026-11-15.md` §10 slice log: study-root index, convergence, calibration,
sensitivity from lengthscales, trust region, Pareto, method board, safe queue, hyperparameter +
prediction persistence). Do not rebuild any of it.

**Why the owner sees nothing:** this branch is deliberately unmerged (merge gate: no study
running). The local GUI runs from `feat/sab-home-2026-11-14`. The owner will pull this branch back
and merge locally after the current solves finish. **The cloud session never merges to main and
never runs solves.** The cloud box has no `runs/` data, no GPU and no bayes-venv. All checks are
offline pytest with synthetic fixtures.

## Tasks (in order, stop when done)

### T1: bring the branch up to date (main agent, ~small)
`git merge origin/feat/sab-home-2026-11-14` into `feat/bo-gui`. Resolve conflicts. Docs
(`CONTINUITY`, `ISSUES`, `INDEX`, `CODE_MAP`) are a union, newest first. For code, keep both
sides' intent. Then run
`python -m pytest -q tests/test_gui_* tests/test_study* tests/test_studies_* -x` once. Fix only
what the merge broke.

### T2: model diagnostics via BoTorch (one subagent, Python only)
New `hornlab_search/bo/diagnostics.py` + a `diagnose` subcommand in `hornlab_search/studies/cli.py`.
It produces artifact kind `diagnostics`, schema `study-model-diagnostics-v1`, exactly as in
`BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md` §1.1. Use BoTorch 0.18.1 APIs (verified in the installed source):
- `botorch.cross_validation.efficient_loo_cv(model, observation_noise=True, untransform=True)` →
  LOO mean/sd per training row (no refit; caption it so).
- `model.posterior(X)` on a 25-point grid per active knob through the incumbent → 1-D slices.
- `botorch.utils.multi_objective.pareto.is_non_dominated` and
  `botorch.utils.multi_objective.hypervolume.Hypervolume(ref_point).compute(Y)` → `front_ids`
  and `hv_trace` (Pareto studies only; ref point from `study-pareto-metrics-v1`).
- Reuse `bo/model.py::fit_model` (same seed/policy as the stored model manifest). Keep it under
  128 KB, and truncate LOO rows at 400 with a flag.
- `diagnose` refits from the stored training dataset, so it works for every old study.
- Test `tests/test_bo_diagnostics.py` with `pytest.importorskip("botorch")`: synthetic n=12, d=2
  → valid artifact. Write one Pareto case. If botorch is not installable in the cloud box,
  `pip install botorch==0.18.1` CPU. If that fails, skip the test and say so.

### T3: wire diagnostics into the GUI (main agent after T2, small)
- `gui/data_bo.py`: `sensitivity_view` prefers the diagnostics artifact (adds slices). Add a
  `calibration_view` "LOO on training data" half from it. `pareto_view` uses its `front_ids` and `hv_trace` when present.
  When absent, return `available:false, can_compute:true`.
- Register `diagnose` as a CPU job kind in `gui/study_jobs.py`/`server.py`, mirroring existing
  kinds (it runs in the Bayesian subprocess, so no torch is imported in `gui/**`).
- `static/study_charts.js`: add the slice small-multiples (mean line + ±2σ band + incumbent
  tick) and the LOO scatter (whiskers, y=x, coverage/Spearman/RMSE chips) using `charts.js`
  helpers, plus a "Compute diagnostics" button when `can_compute`.
- Extend `tests/test_gui_bo_views.py` with one case per new view branch (synthetic artifact).

### T4: navigation + Live tab (one subagent, frontend only, parallel with T2)
Owns only `static/index.html`, `static/app.js` (routes/nav), `static/studies.js`, `static/app.css`.
- Top-level nav group **Bayes**: Studies (`#/bayes/studies`), Method board (`#/bayes/board`).
  The old `#/analysis/studies*` and `#/analysis/compare-methods` redirect.
- Study page opens on a **Live** tab when a package exists. It shows a KPI strip (budget
  used/total screens|verify, best verify J, best screen J, ETA, refusals), plus the existing convergence chart
  and the current-pick card from existing panel data. It polls every 10 s while running. The existing phases stay as the
  other tabs.
- Keep `tests/gui_study_lifecycle.mjs` and `tests/test_gui_studies_module.py` green.

### T5: docs + push
Update `CONTINUITY.md` (new top entry) and `ISSUES.md` (local-only line) in the **same commit** as
each push (repo rule). Update `CODE_MAP.md`/`INDEX.md` for new files. Add a slice-7 line to
`BO_GUI_DESIGN_2026-11-15.md` §10. Push `feat/bo-gui`. Do not open a PR to main and do not merge.

## Token discipline (read this, it is the point)
- **Main agent: Sonnet. Run 2 subagents only**: T2 (Sonnet, it touches BoTorch) and T4 (Haiku is
  OK, it is a mechanical frontend edit). Run them in parallel after T1. Do not fan out further, and
  do not spawn reviewers or verifiers.
- Give each subagent **only** its task section + the file paths it owns. Do not have it read the
  design doc, the handoffs or CONTINUITY.
- Do not read big files whole: `app.js` (9k lines), `data.py` (4.6k) and `param-catalog.v1.json`
  must be grepped, then read in ranges.
- Run tests narrowly (`-k`, single files) while iterating, and the full study/GUI set once at the end.
  Do not loop on flaky or environment-only failures. Note them and move on.
- No screenshots in the cloud. The visual pass happens locally after pull.

## After the cloud session (owner, local, once solves finish)
1. `tools/night_status.py` shows no runner/Julia, and no study is queued.
2. `git fetch && git -C ..\bogui-wt pull`. Merge `feat/bo-gui` into the GUI's checkout branch.
3. Run `diagnose` (bayes-venv interpreter) on the finished fixture studies, start the GUI and look.
4. Re-prepare any staged-but-unprepared study arms (code pins changed).
