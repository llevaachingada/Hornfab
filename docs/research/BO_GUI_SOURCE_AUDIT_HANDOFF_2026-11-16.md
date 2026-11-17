# Hornfab BoTorch GUI: source audit and implementation handoff

**Reviewed:** 2026-11-16  
**Source:** `llevaachingada/Hornfab`, default branch `main`, inspected at HEAD `2c0e2928e932a47975fc284401eafa74ebfc5002`.  
**Input:** User's five-page PDF `hornlab-search(2).pdf`; read-only GitHub code and research documents.  
**Scope:** Design and source audit. No code was edited, no live local GUI was run, and no acoustic/GPU solve was executed.

## Executive decision

Give BoTorch the **same physical horn inspector** as CMA-ES, while keeping its **Bayesian model and search diagnostics distinct**. Never make the user spend a new verification BEM solve merely to view a previously measured geometry. Build one read-only route from a study observation to its already persisted acoustic files, and factor the existing CMA run viewers so they can consume an independently resolved design directory.

The relevant original-data layout already exists:

```
runs/study-<first16-of-package-id>/
  screen/
    run.json
    config.yaml
    search.ndjson
    designs/<design-hash>/
      mesh.msh
      metrics.json
      response.npz
      design.json
  verify/
    ...
  results/<solve-id>.json
```

`studies/production.py` uses that location in its production evaluator. The ordinary GUI, however, accepts only timestamped run IDs and expects `search.ndjson` at the top level. This mismatch explains why a BoTorch study is not browsable as an ordinary CMA run even when its solved design files exist.

### Source-verified diagnosis

| Finding | Evidence | Consequence |
|---|---|---|
| Study evaluator writes normal physical artifacts | `studies/production.py` around lines 289, 307, 360–433 | Reuse screen/verify acoustic artifacts directly |
| Ordinary run resolution rejects study IDs | `gui/data.py` `RUN_ID` at top and `_resolve_run` around lines 305–313 | `#/run/study-<...>` cannot use existing endpoints as-is |
| A BoTorch-specific study run ID is constructed nonetheless | `gui/data_bo.py::_run_paths`, `_run_links` | GUI can advertise inaccessible run links |
| Existing “Solve in 3D” runs another verify job | `gui/study_jobs.py:341–346`, `gui/static/studies.js:282–330` and `:715–759` | Expensive GPU action is mistaken for a viewer |
| Study observations are presented in first 50 J-sorted rows | `gui/data_studies.py::study_solves` | No browse/filter/pagination across all candidates, and duplicates aren't cleanly grouped |
| Study's selected horn is generally not the physical result | `static/studies.js::renderStudyPanel`, `renderLive` | PDF's “Selected horn: Unknown”; no persistent context |
| Explain page dumps raw artifact data by default | `static/studies.js::renderStudyPanel`, `display(visibleData)` | PDF pages 2–4 dominated by hashes and raw lists |
| Server labels available artifacts “unknown” absent semantic validation | `gui/server.py` study phase artifact path | “Unknown” can be a UI-validation status, not evidence that calculations failed |
| Model diagnostics, Pareto and trust-region charts already exist | `bo/diagnostics.py`, `gui/data_bo.py`, `static/study_charts.js` | Rework composition and interactions, do not reimplement BO math |
| Existing design-space scatter is not clickable | `static/study_charts.js::drawDesignSpace` | Plot can't open design 3D / curves |

## What the five-page PDF actually shows

- **Page 1:** `BO-vs-CMA matched comparison arm smoke_ath14`, Explain phase; missing prediction-vs-measurement and knob panels, a ready PCA plot, “Selected horn: Unknown,” broad “unknown” advisory and truncated-artifact warning.
- **Pages 2–4:** Long raw `study-analysis`, manifest, source identities, retained IDs, and parameter lists, not a human-friendly explanation. The dataset may be valid even while the *presentation status* reads unknown.
- **Page 5:** Blank trailing print page.

The missing diagnostics could mean the study has not yet published the relevant `results` or `diagnostics` artifacts; they do not establish a GP failure. The UI should say exactly which evidence is missing, whether it is computable without new BEM, and what action would create it.

## Recommended information architecture

Maintain the existing **Bayes** navigation and study authoring phases. Add a front-door **Results** workspace for completed or running studies, analogous to CMA's Run Detail. Do **not** create a second acoustic viewer.

```
Bayes / Studies
  Study summary
    Results            <- primary human review
      Overview         <- budgets, best verified/screen, convergence
      Horns            <- paginated selection table + 3D & acoustic inspector
      Explore          <- clickable PCA/cloud, search timeline, design families
    Model              <- GP prediction quality, posterior slices, uncertainty
    Strategy           <- Scalar / TuRBO / Pareto-specific panels
    Data & provenance  <- cohort, objective/brief identities, refusals
    Workflow           <- existing propose/package/execute/verify/decision actions
    Advanced           <- collapsed raw artifact data & export
```

For minimal-disruption implementation, these can be additional sub-tabs within existing `#/bayes/study/<id>/{live,overview,data,explain,propose,execute,decide}` until route stabilization. Preserve links and old routes.

### Study landing dashboard

Show task, horn typology, driver/source, objective version, actual coverage target/brief, candidate budget, solver backend, policy, state, and dates. Summary KPIs should include:

- **Best VERIFIED J**: first if available; otherwise clearly “not yet verified” (do not mislabel screen score as verified).
- **Best SCREEN J**: cheaper physical BEM result, separate from verify.
- Attempts / valid measured / cached / cheap refusals / solver failures / verified.
- Current incumbent and improvement relative to initial measured incumbent, only when objective and brief match.
- Evaluation budget and elapsed wall time. Use measured per-tier duration for a *labelled* ETA when appropriate.

The convergence chart should show measured screen J and best-so-far trace, individual proposal markers, refusals, verifier markers, and, only when comparable, a matched CMA arm. Chart marks and “Current best” should open the same horn inspector.

### Primary Horns table and inspector

**Table:** all candidates, paginated or virtualized rather than `first 50`; text/ID search; sort by verified J, screen J, attempt, geometry, feasibility, tip; filters: measured, verified, new incumbent, rejected, Pareto front, novel/exploration; show dimensions, typology, J, source tier, reason, acquisition diagnostic, and verification delta. Group repeated observations of the same physical design while keeping attempt-level evidence accessible. Preserve `attempt/solve` ordering for timeline, not only sorted-by-J order.

**Selecting any measured candidate:**

1. Large Three.js geometry viewport (front/side/top/orbit, inside vs exterior, mouth shape, optional baffle, sections and physical W×H×D).
2. Existing acoustic panels: beamwidth H/V vs frequency **with the exact actual scoring targets drawn**, isobar maps, H/V polar plots, on-axis response, DI, throat impedance/loading, acoustic ripple, and balloon if the stored responses support it. Clearly mark frequency coverage and whether a full balloon or only cuts are available.
3. Objective and normalized term breakdown (source-saved), feasibility/gate statuses, physical provenance and model inputs. Do not present normalized coverage/ripple J contributions as measured degrees/dB.
4. **Screen vs verify side-by-side** when both exist: compare frequency grid, mesh fidelity/backend/source, curves, score and gates; preserve original identities and annotate differences.
5. Optional geometry comparison: current horn vs initial incumbent or previous incumbent as translucent overlays; consistent dimensions/axis normalization. An animation of successive incumbents is optional and should be derived from the actual selected geometry snapshots, not fabricated morphs.

**Selection state:** stable `(study_root_id, study_id, package_id, solve_id, tier, design_hash)` or equivalent resolved identity. Persist in URL and within study view, survive refresh/poll/phase switching, allow back-to-list navigation. When nothing explicitly chosen: select **best verified measured candidate**, else **best screen measured candidate**, else a labelled **predicted-only proposal** with geometry preview if supported, never silently display “Unknown” when results exist.

**Zero-solve rule:** opening an existing mesh/curve/balloon is a GET only. “Verify at higher fidelity” is a separate explicitly costed GPU action. The current “Solve in 3D” must be demoted to a deliberate verification fallback, not the normal 3D view.

### Bayesian-specific panels, with plain-English explanations

1. **Model performance:** sequential predicted vs subsequently measured J and intervals, error, rank correlation, coverage %, number of samples; distinguish this **out-of-sample** tracking from `efficient_loo_cv` on the original training cohort. Both views already have foundations. Avoid claiming ±2σ is empirically a calibrated 95% interval unless evidence supports it.
2. **What knobs matter?** Existing GP lengthscale/relevance bars and 1-D posterior slices (mean and ±2σ), in real parameter units with incumbent anchor. Clarify “model sensitivity, not a proven physical effect” and “other knobs held at incumbent”; warn that a 1-D slice may travel through geometrically invalid combinations.
3. **Why was this candidate proposed?** Current policy, proposal index, model version, acquisition value/rank and meaning, predicted J interval / predicted physical objectives, selection reason, nearest training designs, cheap-check feasibility, parameter delta vs incumbent, and explicit exploration/exploitation/fallback designation. Acquisition values are optimizer *ranking signals*, not measured horn quality or probabilities of success unless defined as such.
4. **TuRBO:** trust-region length over attempts, expansion/shrink steps, success/fail counters, current center & normalized per-parameter bounds, proposals inside/outside current region, collapsed terminal state and unspent budget. Link the center to its geometry. An early collapse is not necessarily global convergence.
5. **Pareto:** actual **coverage-error(deg) vs ripple(dB)** measured frontier, optional predictions separately indicated, frozen reference, nondominated designs, hypervolume trace, excluded points, and a persistent selectable horn inspector. Don't invent an acoustics-vs-cabinet-size Pareto dimension; Hornfab's current recorded policy is coverage/ripple. J can be displayed alongside the frontier as a separate scalar ranking, without making it the frontier axis.
6. **Scalar:** optimizer convergence, observed-vs-predicted improvement and exploration, no meaningless Pareto placeholder.

### Acoustic target integrity

Do not force a flat/constant-directivity target line on all typologies. Read the **resolved brief/objective target** used in scoring and draw its H/V frequency-dependent targets when recoverable. For Le Cléac'h/Iwata/loading-oriented families a sloping beamwidth target may be appropriate, but the GUI must show *what the scorer actually used*, not a typology-based guess. If original target identity is missing, mark “scoring target unavailable” and avoid fabricating it from the family name. Keep actual curves, target curves, and tolerance regions separate and legend-labelled.

## Implementation plan, in priority order

### P0: read-only observation-to-physical-artifacts bridge

Introduce a single explicit resolver, e.g. `gui/study_designs.py` (actual name unimportant), which uses `StudyIndex` to find the owning root and `package_id`/package hash to resolve:

```
<repo>/runs/study-<package16>/{screen|verify}/designs/<design_hash>/
```

Never take a user-supplied filesystem path. Validate `study_id`+root, package artifact identity, candidate membership and hashes, tier allowlist, canonical path containment, and `mesh/solve/physical` identities. Read existing `metrics.json`, `response.npz`, `mesh.msh`, `design.json`, matching run records. Expose a small paginated observation listing; separate detail endpoints lazily load mesh, curves and balloon data. Adapt `gui/data.py` internals (`design_curves`, mesh readers, existing balloon helpers) to work with a prevalidated design directory or pre-resolved run directory; preserve timestamp-run routes unchanged. Render via existing `view3d.js`, `balloon.js`, `charts.js` and `verify.js`. No new plotting or meshing implementation.

Recommended API shape (illustrative, not a frozen contract):

```
GET /api/studies/<id>/observations?page=1&page_size=25&sort=best_j&root=<root_id>
GET /api/studies/<id>/observations/<solve_id>?root=<root_id>
GET /api/studies/<id>/observations/<solve_id>/geometry?tier=screen&root=<root_id>
GET /api/studies/<id>/observations/<solve_id>/acoustics?tier=screen&root=<root_id>
GET /api/studies/<id>/observations/<solve_id>/balloon?tier=screen&root=<root_id>
```

Return typed state `measured | geometry_only | predicted_only | missing_artifact | unsupported_geometry | stale` with explicit reasons. When existing `mesh.msh` cannot be found, offer a **geometry-only, no-BEM preview** from the pinned config/design through supported canonical mesh-preview APIs, but clearly label that the preview is not necessarily the stored solved surface. For arbitrary CAD/GRID families unsupported by `bo/data.py::materialize_geometry`, return `unsupported_geometry` rather than substituting a fake radial horn.

### P1: candidate browser, default selection and integrated run-like viewer

- Add Results/Horns views that consume paginated observations; maintain stable selection through refreshing and routing.
- Move raw phase artifact dump to `<details>`/Advanced; replace `display(visibleData)` with compact semantic cards. Hide hundreds of `retained_ids` and `sha256` values by default but retain export / provenance.
- Separate artifact validation (`unknown`/`stale`) from physical solve status (`measured`, `verified`, `refused`) and analysis availability (`diagnostics missing`). Rename misleading user-facing badges.
- Make PCA, Pareto points and convergence markers interactive by **identity**, not canvas pixel position alone; indicate if a training point lacks a resolvable design hash. Do not treat PCA axes as acoustics.
- Keep objective brief/version and actual beamwidth targets next to acoustic plots, not hidden in provenance.
- Reuse existing visual layout/scales across CMA and BO. Offer links back to study and filters after opening a design.

### P2: Bayesian explanation and method-specific insight

Keep and polish existing `data_bo.py`, `bo/diagnostics.py`, `study_charts.js` rather than building another statistics engine. Present LOO vs sequential calibration as two separate sections; mark legacy runs' missing per-attempt predictions, and support diagnostic computation as a **CPU-only artifact job** when possible. Add actual selected-design context to trust-region center and Pareto front. If posterior snapshots are refitted rather than persisted at each proposal, display which model revision/time supplied each prediction and don't relabel retrospectively refit results as historical predictions.

### P3: comparison tools and efficiency

- Enable “compare selected BO horn to selected CMA horn” only when objective, brief, source, solve fidelity and physical conditions are compatible, or show side-by-side physics with **no shared J ranking**.
- Optional incumbent-geometry evolution viewer; selected designs only, no extra BEM.
- Separate numerical validation of GPU and CPU verify metrics, source conventions and frequency coverage.
- Keep widget payloads bounded and lazy-loaded. The study panel currently has a 128 KB/50-item preview limit; do not funnel heavy mesh, curve, or 200-row listings through that same phase payload.

## Acceptance tests (must pass before merging)

1. **Zero BEM calls:** A synthetic completed BoTorch study with `screen/designs/<hash>/{mesh.msh,response.npz,metrics.json}` opens 3D and acoustic charts through GET-only routes while `solve/verify` hooks are mocked to throw if called. No new run directory, data record or GPU lock.
2. **Real study package routing:** `study-<package16>/screen` and `.../verify` resolve through the study registry even though `_resolve_run` rejects these as ordinary timestamp-run ids; no path traversal, root collision or unrelated study access.
3. **Cross-method visual equivalence:** Same stored physical design in conventional CMA and BO path produces the same 3D orientation, scale, curves and physical units. Symmetry quadrants, rolled mouths, outer shell and mounting are faithfully handled.
4. **Complete browsing:** A results artifact with at least 219 observations shows all via pagination; sort/filter works; bound-preview markers are never rendered as candidates; duplicate attempts link to one physical design with separate history.
5. **Selection:** A study with physically measured results displays a resolvable selected horn without clicking Propose; URL deep-link survives refresh, poll and phase transitions.
6. **Evidence truth:** Prediction intervals are never displayed as measured curves; screen and verify scores never silently merged; old studies without diagnostics say `not recorded` and offer a diagnostic action where possible. A study with only metadata doesn't show “invalid model” unless independently proven.
7. **Policy-specific:** Scalar has no fake frontier; TuRBO length/events correspond to the recorded state; Pareto charts use **coverage and ripple units** and the frozen policy reference, clicking any measured frontier point opens the correct design.
8. **Typology targets:** Flat and sloped brief target fixtures render different H/V target traces exactly as recorded, with objective identity. Missing target = missing, never a typology guess.
9. **Regression:** Ordinary CMA Runs, Elites, Evolution, Verify, Balloon and Sandbox still work; desktop/mobile, light/dark and screen-reader labels checked. Run existing tests `test_gui_bo_views.py`, `test_gui_study_solves_view.py`, `test_gui_study_index.py`, `test_gui_studies_qa_fixes.py`, `gui_study_lifecycle.mjs` plus new resolver/selection tests.
10. **Live-work safety:** Read `docs/CONTINUITY.md` and active night/queue status first; changing `hornlab_search/**/*.py` can affect study code pins. Never alter or interrupt running jobs, never quietly reprepare immutable packages, and never add a hidden GPU action to a visualization GET. Follow `AGENTS.md`/`CLAUDE.md` and update `CONTINUITY.md`, `ISSUES.md`, `INDEX.md`, `CODE_MAP.md` with relevant committed work.

## Minimum implementation outcome

For an existing completed BoTorch study, I should be able to open **Bayes > Studies > [study] > Results**, select any candidate from the full results list, rotate its existing mesh in 3D, inspect its original acoustic frequency/polar/beamwidth/loading plots and actual target overlay, compare screen to verified data, and read *why BoTorch picked it* without starting one additional BEM solve. This works across scalar, TuRBO and Pareto studies, with only their optimizer-specific diagnostics changing.

## Exact repository source links

- [`hornlab_search/studies/production.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/studies/production.py)
- [`hornlab_search/gui/data.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/data.py)
- [`hornlab_search/gui/data_bo.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/data_bo.py)
- [`hornlab_search/gui/data_studies.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/data_studies.py)
- [`hornlab_search/gui/study_jobs.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/study_jobs.py)
- [`hornlab_search/gui/server.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/server.py)
- [`hornlab_search/gui/static/studies.js`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/static/studies.js)
- [`hornlab_search/gui/static/study_charts.js`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/static/study_charts.js)
- [`hornlab_search/gui/static/view3d.js`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/static/view3d.js)
- [`hornlab_search/gui/static/balloon.js`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/static/balloon.js)
- [`hornlab_search/bo/diagnostics.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/bo/diagnostics.py)
- [`hornlab_search/bo/data.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/bo/data.py)
- [`docs/research/BO_GUI_DESIGN_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_DESIGN_2026-11-15.md)
- [`docs/research/BO_GUI_HANDOFF_2026-11-16.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_HANDOFF_2026-11-16.md)
- [`docs/research/BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md)
- [`AGENTS.md`](https://github.com/llevaachingada/Hornfab/blob/main/AGENTS.md)

## External method references

- [BoTorch: Models and posterior distributions](https://botorch.org/docs/models)
- [BoTorch: Acquisition functions](https://botorch.org/docs/acquisition)
- [BoTorch: TuRBO tutorial](https://botorch.org/docs/next/tutorials/turbo_1)
- [BoTorch: Multi-objective Bayesian optimization](https://botorch.org/docs/multi_objective)

**Research status:** Source paths and behavior verified read-only against public `main`. No live local BoTorch study files, browser interaction, benchmark or production GPU solve was run in this investigation; runtime-specific failures still require local fixture reproduction.
