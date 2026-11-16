# Bounded implementation slices

These are complete dispatch blocks for later implementation. This audit changes no production generator, objective, brief or queue. Full search campaigns remain held. The owner subsequently authorized a few isolated acoustic diagnostics; two spiral seed checks completed, and these prompts do not authorize any additional run. The senior parent owns driver/source, geometry construction, objective and acceptance decisions. Do not copy these prompts into a solve runner.

Parallel wave1: A (objective diagnostics), B (geometry witnesses), C (identity/replay) have disjoint owned code paths. D (GUI) waits for their contracts. E (domain/capability experiments) waits for B/C and the senior's driver decision. F (queue) waits for all acceptance gates and explicit hold release. Do not create worktrees or git commits in child lanes. Snapshot current dirty state first; never overwrite concurrent work. Read current AGENTS.md and the listed sources, including their caveats.

## A — objective diagnostics and honest score replay

```text
Model: gpt-6.1-terra, high. Senior review required for acoustic priorities.
Task: Implement read-only objective diagnostics, without changing v7 or any existing brief.
Repo: C:/Users/hunte/Hrns/hornlab-search. Preserve dirty work and all historical artifacts.
Read: AGENTS.md; docs/plan/01_CONTRACTS.md; docs/research/typologies/audit_2026-11-15/{READINESS,PRIMARY_OBJECTIVE_SOURCES,OBJECTIVE_OFFLINE,DRIVER_SOURCE}.md under docs/research/typologies.
Own: one new tools/analysis/rolled_objective_diagnostics.py and its numerical-reference tests only. Do not edit objective/**, metrics/**, config.py, frozen contracts, briefs or queue files.
Starting code: docs/research/typologies/audit_2026-11-15/objective_audit.py; objective/scalar_v7.py::_objective_v7; scalar_v4.py::_diag_term; scalar_v2.py::_objective_v3; metrics/di.py; metrics/diagonal.py; metrics/smoothness.py; search/evaluate.py::metrics_from_response.
Requirements:
1. Replay original scores with source/brief/response hashes and unweighted/weighted loss units; reject missing response provenance. Preserve score identities. Compute leave-term-out diagnostics across stored candidates, clearly label winner reselection versus same-design score changes.
2. Report full-sphere weighted balloon DI, cuts estimates separately, score-band actual sample endpoints, unweighted fitted slope in dB/dec and dB/oct, endpoint secant, residual variation and raw std(DI). Do not replace a0 or5 with an invented preferred slope.
3. Report Gaussian absolute-DI reference (~13.079574 dB for80x50),65-degree diagonal target, H/V outermost-crossing versus diagonal first-crossing semantics, no-crossing saturation and angular-grid sensitivity. Show same H/V crossings do not determine diagonal crossings.
4. Keep detrended flat and flat_cv behavior explicit. Do not call flat raw SPL std or distd detrended smoothness. Do not import full-system preference from bare-horn metrics or PIR mixture weights.
Acceptance: stored seed/winner score replay agrees within1e-9 on the32 audit response checks; deterministic synthetic cases cover linear DI rise versus residual roughness, unit conversions, multi-lobe crossing choice and missing balloon. No solver or engine fitting. Explain any mismatch without changing tolerances.
Deliver: script, tests, raw test output, replay delta summary and proposed metric contract questions. No production scoring changes or solves. Senior chooses any future objective; do not create a new schema/version unilaterally.
```

## B — explicit body and junction witnesses

```text
Model: gpt-6.1-terra, high. Senior makes the construction/physical diagnosis.
Task: Add a read-only full-boundary geometry audit using existing mesh/geometry libraries.
Repo: C:/Users/hunte/Hrns/hornlab-search; preserve dirty sources, original3 designs and all variants.
Read: AGENTS.md;01_CONTRACTS.md; docs/research/typologies/audit_2026-11-15/{READINESS,PRIMARY_GEOMETRY,GEOMETRY_CAPABILITY,DRIVER_SOURCE}.md and mesh_topology.json.
Own: new tools/analysis/rolled_surface_audit.py and numerical fixture tests only. No installed library edits, mesher/solver reimplementation, generator modifications or smoothing of source evidence.
Starting code: docs/research/typologies/audit_2026-11-15/mesh_topology.py; tools/render/render_views.py; native generators/rolled_family.py::resolve_grid; tools/geometry/crowe_panel.py::outer_points; private _crowe_section_v2.py; geometry_controls.py.
Requirements:
1. Preserve original mesh SHA256, indices, physical roles and source/recipe/config digest. Report degenerate/duplicate triangles, same-directed shared edges, nonmanifold incidence and symmetry boundaries. Raw normal angle0=smooth,180=opposed; signed convention must specify ordered edge and outward orientation. Do not equate a high angle to inverted winding.
2. Identify inner/outer/closure roles from resolver provenance; audit exact worst off-axis Crowe junctions at saved coordinates, including seed176.463deg and winner153.214deg. Render flat facets, normals, front/oblique/underside, H/V and22.5/45/67.5deg cuts. Keep visualization normalization separate from raw topology.
3. Use an existing reliable triangle-intersection/minimum-clearance method for nonadjacent surfaces, excluding only documented adjacency. If dependency support is missing, report a gap and a concrete dependency proposal; do not invent a mesher or claim zero intersections.
4. Compute true fixed-z aperture contours on the outward branch, preserving multiple return branches. Do not call a nonplanar ring's xy projection area an axial flow area. Analyze derivatives/curvature with physical arc length and source-neighborhood limiting tangent; separate surface sampling from spatial acoustic mesh refinement.
Acceptance: witness counts reproduce saved originals; a deliberately sharp but valid folded fixture does not falsely fail winding, and a known crossing fixture fails intersection. No fillet radius or body law selected from appearance. Supply source/model-labelled residuals and uncertainty.
Deliver: geometry witnesses and diagnosis options for senior review. A body repair, if justified, must be a separately versioned construction with old dispatch/data preserved; do not alter kernels during this slice. No solves.
```

## C — canonical full-boundary identity across execution routes

```text
Model: gpt-6.1-terra, high. Senior owns migration decisions and acoustic interpretation.
Task: Make a concrete replay/parity implementation proposal for the three bridge-only home routes, then implement only additive approved dispatch mechanics.
Repo: C:/Users/hunte/Hrns/hornlab-search; no worktree or git mutations; preserve dirty work.
Read: AGENTS.md;01_CONTRACTS.md; docs/research/typologies/audit_2026-11-15/{READINESS,DOMAINS_AND_PATHS,domains_semantics,DRIVER_SOURCE}.md. Research existing canonical APIs before adding anything.
Own: additive native dispatch/private-kernel modules and dedicated parity tests; coordinate any shared grid.py/generated.py/mesh resolver edits with parent before writing. Do not touch GUI/objective/queue files or installed packages. Never replace the existing native v1 kernels or bridge recipe identities.
Starting code: generators/rolled_family.py with native dispatch; grid.py::resolve_grid_geometry; mesh/build.py::_build_grid_mesh; GeneratedSpace.knobs_for; existing rolled_rect_cli/crowe_panel_cli/rosse_rect_cli; tests/test_rolled_family_workers.py.
Requirements:
1. One resolver produces exact inner, outer and closure/source inputs; render, preflight, mesh, CMA, CMA-ME/MAE and fresh-process cold replay consume it. Migrate mechanics without changing physical points. If new recipe schema is necessary, propose it explicitly and keep old recipes readable under their pinned identity.
2. Identity includes normalized source/reference bytes, transitive dependency pins, inherited YAML, driver/source, fixed and active controls, sampling, full body, brief and mesh/solve policy. Distinguish recipe, physical geometry and acoustic observation IDs. Preserve historical hashes rather than retroactively assigning new ones.
3. Test source change, outer-only change, inactive-control change, duplicate/clipped proposals and fresh worker reconstruction. Do not silently admit generic grids to BO: user prohibits BO solves and production >=100 usable matched acoustic rows remains mandatory. Hash auditing is software work only.
4. Fail safely on a missing bridge in any subprocess. MAE boundary projection and duplicate handling must be explicit; no multiple physical rows from one clipped geometry. Do not weaken refusals or caps.
Acceptance: fixed seed and nontrivial boundary/interacting candidates produce array-identical inner+outer before meshing across every claimed path; selected real mesh check matches source/closure roles, without acoustics. Existing9 wrapper checks and61 native-path checks pass. A subprocess that uses only stock import must reconstruct a newly native recipe deterministically.
Deliver: complete parity table, limitations, raw CPU output and exact source manifests. No engine GP fitting, synthetic BO smoke, acoustic solves, dataset relabeling or queue launch.
```

## D — GUI exposure and readiness are separate

```text
Model: gpt-6.1-terra, medium.
Task: Reconcile catalog/preview/search eligibility after C; do not change physical laws or auto-launch anything.
Repo: C:/Users/hunte/Hrns/hornlab-search. Read AGENTS.md and docs/research/typologies/audit_2026-11-15/{READINESS,DOMAINS_AND_PATHS}.md plus gui_api_snapshot.json. Preserve concurrent GUI edits; refresh diff first.
Own: GUI catalog/data/preview/parameter metadata and focused GUI tests, assigned by parent to avoid overlaps. Do not edit generators, briefs or queues.
Requirements: label actual construction (Hypex, Keele-style biradial, section reconstruction, original spiral, OSSE hybrid, R-OSSE); retain historical IDs. Show preview-only versus executable versus physically ready separately. Do not use catalog visibility, compatibility=True or a passed seed gate as acoustic readiness. The observed three bridges are preview_only+disabled; section_pucker exposure remains separate. Existing suggested GUI budgets40-140 are not the owner's30-call plan: display a distinct reviewed pilot budget only after F, rather than silently changing global defaults or existing jobs. Preserve the owner solve hold.
Acceptance: API and UI agree for all26 audited cells where displayed; fresh preview inner/outer equals C's resolver; source-missing and preview-only states cannot launch. Browser review is required before claiming GUI completion. No solve action during tests.
Deliver: API snapshot, UI evidence under screenshot-evidence rules if screenshots are collected, focused tests and limitations. No acoustic runs.
```

## E — useful domains and source interface, before optimization

```text
Model: senior parent for physical/source decisions; gpt-6.1-terra high for disjoint numeric audit.
Task: Resolve source interface and per-family control capability without enlarging boxes or freezing useful controls to hide defects.
Repo: C:/Users/hunte/Hrns/hornlab-search. Read AGENTS.md; research skill; docs/research/typologies/audit_2026-11-15/{READINESS,DRIVER_SOURCE,PRIMARY_GEOMETRY,GEOMETRY_CAPABILITY,PARAMETER_DOMAINS,domains_semantics}.md and domains_proposed.json.
Own: new versioned research configurations/evidence and source-reference tests. No old kernel/config/brief/data mutations. Production law changes require senior-approved construction and new identity first.
Requirements:
1. Treat18mm/2deg as historical interface assumptions; Faital's HF1440 is35.8mm combined exit. Establish physical mating outline and credible source/wavefront evidence. Do not invent a replacement cone. Test the R-OSSE limiting tangent property and extended-throat entrance separately from nominal a0 and first-segment secants.
2. At seed plus coupled extremes vary each current and deliberately fixed potentially useful control: H/V flare, size/depth, loading factor, termination, pucker/window/junction. Measure true aperture progression, curvature/tangent/return and full outer boundary. Document inactive and duplicate controls. Full-rank vertex motion is not acceptance.
3. Preserve all current domains in the proposal; exact domain=recorded numeric interval intersection with explicit source, construction and full-body constraints. For biradial use rm>=r0+L*tan(a); for sections actual sweep constraints instead of empirical0.57W; for Crowe-X measure complete extent. No soft clipping or lowering useful flare angles to fit. Review fixed k/m/q/shape controls as untested choices, not sacred constants.
4. If an existing law cannot independently change required H/V development/termination, mark its acoustic domain empty pending a new mathematically specified law. Do not graft the published names together. Original spiral and reference section pilots can remain valuable controlled experiments without pretending to be broad coverage optimizers.
Acceptance before acoustics: each family has exact effective defaults, active/fixed rules, transforms, seeds/ranges, initial physical steps and coupled rejection regions; throat/source and topology gates pass; complete inner/outer deterministic identity; local/boundary geometry sensitivity robust to sampling. Propose acoustic contrasts and uncertainty needed to test useful directions after the hold lifts.
Deliver: revised exact domains and physical hypotheses, no solves. Parent chooses the first eligible family and any objective changes.
```

## F — replace the stale queue with a bounded pilot

```text
Model: gpt-6.1-terra, medium for manifest/accounting; senior parent for admission/order.
Task: Prepare a new, reviewable CMA-only pilot AFTER A-E evidence and explicit solve-hold release. Never resume E wholesale.
Repo: C:/Users/hunte/Hrns/hornlab-search. Read AGENTS.md; hornlab-night-queue and search-economy skills; docs/research/typologies/audit_2026-11-15/{READINESS,RUNS_AND_QUEUE,PARAMETER_DOMAINS}.md and QUEUE_REVIEW.json. Refresh live processes and preserve old manifests/history.
Own: new pilot configs/brief copies and a new non-live night manifest only; no controller launch, no original config edits, no study/cohort jobs. Default plan is30 acoustic candidate-evaluation calls per cell per RNG seed TOTAL, two seeds1234/5678. Reserve6 of30 for validation and use at most24 for discovery. Third seed9012 is optional only after senior review, never auto-chained. If30 search calls plus verification are wanted instead, expose the extra total explicitly before approval; do not hide it.
Requirements: one verified source/brief/identity per comparison; fresh versus cached evaluations separated; cap attempts/refusals/wall time and retries as well as acoustic calls. Plan per-cell physical steps from measured feasible local spread, not a guessed sigma. Paired treatment/control use same RNG seeds, starting geometry policy, objective, budget and validation; two cells cost120 calls total for2x30 each. Report active dimension count and generations possible. Treat short pilots as informative comparisons, not convergence proof.
Validation allocation: same design/frequency/angles at two genuinely finer spatial meshes; then frequency-only and angular-only refinement at fixed fine mesh; reserve remaining2 calls for runner-up/replication or a justified second representative. Do not let expensive validation change boundary geometry/source; record actual nodes, spacing, hashes and all changed axes. If these cannot be achieved within6, shrink pilot scope or expose the additional cost; never claim convergence from incomplete evidence.
Acceptance: no Bayesian/study/cohort job anywhere; all admission gates explicit and failing closed; dry-run runner prints bounded plan without invoking cleanup/solver; paused old E tail accounted for; parent can review exact command paths and total costs. Preserve >=100 usable MATCHED production acoustic rows plus all identity/quality gates for any future BO discussion, but no BO authorization now even if100 exists.
Deliver: non-live reviewed manifest and complete cost/admission table. Launch only on owner instruction lifting the current hold; this implementation prompt is not that instruction.
```
