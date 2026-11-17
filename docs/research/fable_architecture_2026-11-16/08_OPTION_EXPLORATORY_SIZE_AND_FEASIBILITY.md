# Optional architecture hypothesis: decouple acoustic discovery from product-size feasibility

**Status:** Candidate architecture/research direction, **not** a decision, authorization to change the 600 mm home envelope, or approval for GPU solves. Added in response to the owner's supplied proposal, `Pasted text.txt` (2026-11-16). Read with `03_FABLE_DISCOVERY.md`. **Fable must evaluate and may reject this option** after comparing its expected information gain with other priorities.

## The question worth asking

Could Hornfab be rejecting otherwise valid, acoustically promising designs because **a product packaging constraint** (e.g. 600 W × 480 H × 480 D mm for the home horn) is enforced before the solver? If so, would a *separate*, resource-controlled discovery campaign outside that product envelope generate valuable new physical data and design parents, or merely spend GPU time proving larger horns can perform differently?

Separate five things that sometimes get conflated: (1) mathematical/geometric validity; (2) correct driver/source connection and source assumptions; (3) mesh/numerical feasibility and available compute; (4) product/room/fabrication envelope; (5) acoustic merit. A design outside category (4) is not therefore invalid under (1), nor demonstrated acoustically good under (5).

## Repository evidence personally checked against remote `main` at `913c934d` (2026-11-16)

1. `hornlab_search/design/generators/registry.py:242-255,304-307`: a generator rejects depth and inner mouth sizes beyond its applied `brief.envelope`. Thus some oversized generated horns cannot reach meshing.
2. `hornlab_search/design/generated.py:180-203`: materialization catches generator exceptions as `_generator_error`; if materialization succeeds, an estimated outer-shell envelope overrun is represented as an `invalid_envelope` marker. Verify actual error taxonomy end-to-end because these paths can be classified differently.
3. `hornlab_search/search/evaluate.py:278-295,1190-1220,1424-1445`: the finished mesh is checked against the brief envelope, and an overrun can prevent the acoustic solve; not all routes use the same failure kind. **Do not assume all oversize rejections receive the graded penalty.**
4. `hornlab_search/bo/data.py:1068-1155`: the current finite BoTorch candidate pool applies a cheap envelope test and excludes failed candidates. `bo/data.py:871-910` rejects generic CAD/GRID canonical sampling except its supported rolled-family route. A geometry capable of BEM is not automatically BO-eligible.
5. `hornlab_search/design/generators/grid.py:2986-3016`: for the **generic** GRID radial-field route (not the special rolled-family or rows branches), `envelope_extents()` sets *both* outer width and height to twice the **maximum over azimuth** radius plus wall thickness. This is explicitly conservative and may overestimate the smaller axis on an asymmetric section. **Potential false refusals must still be demonstrated against a true resolved/meshed surface** rather than assumed from the formula alone. A naive change to horizontal/vertical meridian maxima could conversely miss oblique lobes and be nonconservative: use axis-projected extrema of the true surface.
6. `hornlab_search/search/outcomes.py:1-45` distinguishes geometric, envelope, resource, and transient failures, while `search/cma.py` supports graded/refusal and strict-resampling paths. `hornlab_search/dataset/identity_v2.py` explicitly distinguishes solve, analysis, score and study identity. These are existing foundations, **not missing-from-scratch features**.
7. Historical reports (`docs/status/2026-11-14/README.md`, `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md`, `docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md`) demonstrate appreciable refusals and prior configuration bias. They **do not** establish how the rejected oversize shapes would have sounded, or prove that opening the size bounds increases usable information per GPU-hour.

## Research route to compare against the broader architecture choices

**Option A: keep the product envelope hard.** Fix incorrect/conservative extent calculations, tighten the validity taxonomy, expand only evidence-limited *parameter* bounds, and optimize within the established product class. This is the low-risk control.

**Option B: separately versioned exploratory size study.** Preserve original brief and production search. Define a fresh exploratory run/brief with wider **product** limits, but keep geometric, throat/source, symmetry, mesh-resolution and GPU safeguards strict. Record actual W/H/D, volume (where meaningful), material/printability estimates, solve time/DOF, raw acoustic response, and scored metrics. Do not mix old and new scalar J or normalized search vectors without explicit compatibility and re-encoding.

**Option C: size-aware, multiobjective discovery.** Retain acoustic metrics and dimensions as distinct outputs; use Pareto/quality-diversity or constrained search to identify a menu of trade-offs. One *illustrative* size descriptor is `max(W/600, H/480, D/480)`, but a single ratio hides aspect, volume, depth, weight, clearance, manufacturing complexity and geometry-dependent numerical cost. Consider multiple explicit descriptors or a human-selected utility instead.

**Option D: no new solves initially.** Use existing valid histories and full responses to build an offline acoustic-vs-size landscape, locate near-envelope optima and assess expected out-of-envelope information value. Compare against the expected gains from geometry grammar, flexible briefs and failures first. This can be combined with A, B or C.

Fable should be free to combine, modify, or dismiss these routes and propose an entirely different approach.

## Cheap-agent work before asking Fable to choose

1. **Trace every enforcement point and error code** across native, generated FREEFORM, generic GRID, rows, rolled-family, and CAD routes. Build a table: stage, precise formula, actual affected surface, status returned, optimizer treatment, and whether acoustic data are saved.
2. **Classify historical refusals with correct denominators.** Differentiate product oversize from flawed geometry, throat mismatch, max DOFs, source/mesher bugs and transient worker failures. Estimate how many were otherwise geometrically/mesh-feasible without claiming their acoustic merit. Identify apparent *false positives* separately.
3. **Test extent conservatism using read-only CPU geometry data**, if safe. Compare generic GRID's current estimate to axis-projected min/max extents of the resolved full inner/outer surface, with azimuthal refinement and independent final-mesh spot checks when feasible. Include off-axis petals, X folds and strong asymmetry so that a correction does not under-report dimensions. No GPU or production file mutations.
4. **Audit BO eligibility independently of size.** Enumerate geometry adapters, active/discrete parameters, pool filtering, and the consequences of widening bounds. State what data become newly eligible and why; never treat a refused geometry as a measured acoustic datum.
5. **Measure cost scaling** from historical mesh/solve records or a safe CPU-only estimator. Larger surfaces at the same highest frequency can increase DOFs and dense-BEM costs steeply; a 900 mm exploration must not be assumed cheap or feasible on the RTX 4060.
6. **Check the scoring premise.** Separate raw physical measurements from the current scalar v7 objective and its exact 80° × 50° target. It may be more valuable to vary *acoustic target* or geometry controls than to expand physical dimensions. Report any existing within-envelope control that distinguishes these explanations.
7. Produce `SIZE_FEASIBILITY_EVIDENCE.md` with source lines/run IDs, a refusal taxonomy, candidate studies, contradictory findings, and **the specific decision Fable would change**. Do not implement a new policy or launch a solve.

## Candidate experiment, only if Fable finds new solves justified

- Freeze common physical source, driver interface, frequency support, meshing accuracy, acoustic metrics and verification criteria where possible. Compare current product-size search against at least one modest exploratory domain. A proposed 750 × 650 × 600 mm intermediate and 900 × 800 × 700 mm extreme appeared in the owner's pasted proposal; **these are suggestions, not approved dimensions or an optimized sampling design**.
- A staged, bounded CPU-geometry/mesh reconnaissance comes first. Only propose GPU calls after observing feasibility, predicted DOF and meaningful comparison controls. Select candidates for information gain and diverse behavior, not simply the largest mouths. Define a stop rule and actual compute ceiling with the owner.
- Use true raw acoustics and frequency-resolved polar quality, loading and DI alongside realized W/H/D and solve cost. Keep product feasibility an independent final filter. A larger winner is not automatically a better 600 mm home horn.
- If adapting a large shape to smaller dimensions, **re-optimize and re-solve at the original HF1440 throat**, rather than assume whole-geometry geometric-similarity scaling preserves the 700 Hz behavior.
- Preserve old experiment identities and data. Widening parameter bounds changes `[0,1]` coordinates; re-encode from physical parameters and check actual geometry and score-policy identity. New acoustic metrics can be recomputed from historical responses only if the required fields, angles and frequency support really exist.

## Questions Fable must answer without being steered

- Is the dominant loss **incorrect false refusal**, **valid but above-envelope pruning**, **tight parameterization inside the envelope**, **poor acoustic objective**, or some combination?
- What is the expected scientific value *per marginal GPU-hour* of size exploration compared with better parameterization and flexible coverage goals?
- Should size be a hard, soft, report-only, constrained, or multiobjective quantity at different stages? Does the right answer differ by use case (home horn, larger-room/PA, theoretical dataset)?
- Would an optional discovery study benefit from CMA-ME, trust-region BO, feasible-region learning, cross-family transfer, a lower-cost physical model, or simply a designed offline/CPU pilot?
- What observations would **falsify** the benefit of relaxing the size envelope, and when should this option be dropped?

## Decision rule for this handoff

**Include this as one legitimate competing direction, not the architecture's default.** Fable should only recommend a policy change or dedicated size-discovery campaign if it identifies an evidential advantage, preservation path, resource ceiling, and a minimum experiment distinguishing this idea from the alternatives. Do not alter the existing 600 × 480 × 480 mm production home brief by editing it in place.

## v3 interaction with a proposed adaptive supervisor

If Fable recommends an experiment-allocation supervisor, explore whether it should occasionally **recommend** a separate oversize discovery study when existing-data evidence suggests the largest scientific gain is near or beyond a product-size wall. Do not allow a watchdog to silently turn a 600 mm *production* brief into an oversized one or to treat over-envelope refusal as acoustic evidence. Compare expected value per extra actual BEM-hour against fixing false geometry refusals, better shape controls and objective calibration. Any exploratory configuration must be new/versioned, cost-admitted and owner-approved; a policy may also legitimately decide to allocate **zero** GPU time to oversize work.
