# Size-aware optimization and directivity, first implementation

2026-11-24, canonical checkout `C:/Users/hunte/Hrns/hornlab-search`, starting from `626a7c65` on `hornfab-all-2026-11-18`. The checkout already contained local metric BO, GUI, mesh and system work. This pass adds its changes to that checkout. Acoustic objectives and the historical dataset remain in place.

## Constraint and identity audit

| Route | Verified issue or contract | Implementation and remaining qualification |
|---|---|---|
| Brief and generated space | The owner approved an open candidate envelope. Standard FREEFORM and generic GRID still read raw product dimensions and clamped meridian length. | `config.envelope_policy` resolves production, exploration and discovery. `design/generated.py` and the registry use it. Generic GRID keeps the legacy geometry of old recipes. A newly uncapped surface has an explicit depth in its recipe when its geometry differs. |
| Specialized GRID, Crowe adapter and CAD | Versioned generators and plughorn/MEH had adapter-owned size checks. Source hashes include the versioned source bytes in several families. | The generator and mesher dispatchers pass effective limits to those adapters. The versioned kernels and their digests are unchanged. Existing `report_only` family metadata remains informational. The post-mesh gate still applies. Direct specialist calls that bypass the dispatchers are outside this integration. |
| CMA-ES and CMA-ME | Both use the normal evaluator. CMA's record-gate resample could shrink open campaigns against the product box. | Search records carry the resolved policy. The record gate reads effective mesh limits. In an opted-out campaign an approximate negative margin falls through to mesh validation. Legacy production preflight remains active. |
| Geometry inspection and evaluation | The inspection tool doubled the positive coordinate on both axes and used its own depth allowance, even for non-quarter meshes. GUI rows and plughorn previews used raw dimensions for candidate alerts. | `design/size.py` measures axis-projected mesh extents using the declared mirror planes. `tools/shape_check.py` uses the same final envelope decision as the evaluator. GUI previews use effective limits. Geometry-only results remain estimates. |
| Scalar BoTorch, TuRBO and selected candidate | Both proposal paths share `bo.data.geometry_checks`. The rolled resolver's earlier product check could reject an open candidate before this check. | Both paths use effective candidate limits, record analytic bounds separately from aperture estimates and recompute selected geometry. Rolled samples use both sheets. Formula-native samples use the inner sheet for cheap screening. The canonical mesh gate runs before acoustic dispatch. New scalar/TuRBO study artifacts bind the candidate policy to the pool and package. A changed policy requires a rebuilt pool and package. |
| Training eligibility | Rolled-family historical replay could refuse an otherwise compatible observation because of current product dimensions. | Replay relaxes size checks in an isolated config. It still checks recipe, throat, encoding bounds and cohort provenance. The manifest records product eligibility and oversized row IDs. The measured J and vector survive. Failed or out-of-domain records still carry exclusion reasons. |
| Pareto, resource and manufacture | Existing Pareto evaluates coverage and ripple. Mesh topology, source coupling, DOF caps, timeouts and GPU lock protect execution. Printer segmentation is a separate question. | Existing scorers, Pareto objectives and resource guards are retained. Product-fit fields use measured solver-box dimensions and an explicit reporting tolerance. Manufacturing remains unassessed. |

`enforce: true` keeps legacy production candidate tolerances (0.5 mm W/H, 15 mm depth at the mesh gate). `enforce: false` uses the absolute sanity ceiling, 1200 mm by default. Its optional `max_utilization` is a per-axis multiplier capped by the sanity ceiling. Use 1.0 for an exact-box benchmark and 1.05, 1.15 and 1.25 as experimental thresholds. Mesh and search metadata record the policy independently of the acoustic calculation.

New rows with a brief carry `size_feasibility`, including width/height/depth, signed product margins, maximum utilization, candidate fit, measured surface scope and descriptor ID. GRID also records the projected terminal inner rim. It is sensitive to the termination convention and can differ materially from the outer dimensions. Formula and CAD routes can leave aperture unknown. A solved mesh describes the surface presented to BEM, which may omit manufacturing features. Mounted product fit remains unknown. Actual DOF, timing and VRAM come from the existing evaluation row and queue records. On two CPU-meshed GRID controls, the legacy prematerialization estimate exceeded actual width and height by exactly 6 mm from its full wall allowance.

Physical response keys remain geometry and solver based. The new uncapped GRID recipe differentiates changed geometry. Historical brief and catalog score hashes are unchanged. The existing catalog includes the full brief hash in its score and task identities, so changing the YAML envelope creates a separate provenance identity even when the acoustic calculation is identical. Crossing those identities needs explicit acoustic-parity evidence or common replay. No automatic merge of older cohorts was introduced. Historic mixed-fidelity M0 is still its explicitly declared reproduction case. New benchmark cohorts should be single fidelity.

This is a first slice. P0 does not yet pass the complete family-wide acceptance gate. Formula-native candidates lack a canonical sampled outer-build check, and generic GRID/CAD are not automatically eligible for scalar BO. For legacy production, existing approximate refusals remain possible near a boundary. The complete mounted, CAD flange, solid-volume and near-limit family suite is pending. Keep current size data as advisory when those pieces are unknown.

## Offline data and model evidence

[Offline frontiers and cohort counts](README.md) cover 55 Home Fold, 152 compact500 Crowe and 36 rolled screen observations in distinct identities. The controlled benchmark should start with the compact500 tradeoff and a Home Fold counterexample. The corpus is local and the analysis records the input hashes.

The synthetic boundary check used the installed BoTorch 0.18.1 `SingleTaskGP` and qLogNEI. A single fit kept observations on both sides of the product boundary. The production and 1.05 exploration pools obeyed their limits and selected near their known feasible optima. It covers candidate admission and acquisition behavior. The historical rolled fixture separately exercises native dataset admission. Live TuRBO promotion still needs a feasible initial measured center when the best historical point lies outside the active policy.

A real Home Fold geometry-only rehearsal reused the same 128 Sobol draws for each region. Production admitted 21, 1.05 admitted 36, 1.25 admitted 83 and discovery admitted 86. All arms had 42 geometry-resolution refusals. Production had 10 candidates with 0.95 ≤ R ≤ 1.00 by the sampled inner geometry and took 9.1 s. The production pool survived this seed with a 16% admission rate. Run more seeds and measure the published pool's near-boundary mesh acceptance before introducing stratified sampling. [Rehearsal record](pool_geometry.json)

The three Crowe finalists preserved their order on a common verify grid. The 490, 607 and 770 mm wide candidates scored 2.694, 1.976 and 1.608. Each used more geometry and compute than the previous one. [Sizes, timing and reproducible identity checks](README.md)

Scalar BO uses fixed observation variance `1e-6 × sample variance` on the selected task. Screen/verify differences are paired fidelity differences. They do not justify inflating the noise parameter. Use `bo/diagnostics.py` for held-out/LOO calibration on frozen screen data and matched verify rows for the fidelity check. Keep hard known size constraints in the fixed candidate pool. [BoTorch parameter and outcome constraints](https://botorch.org/docs/next/constraints)

## Directivity evidence

[Matched rolled and Lamé verify results](DIRECTIVITY_VERIFY.md) compare both exact anchors and both body variants. The neutral adapters reproduce the original verify mesh bytes. Rolled front-load lowered verify J by 5.1%, while 8 kHz H narrowed to 53.9°. The Lamé gain raised verify J by 7.2%, with 8 kHz H narrowing to 43.1°. Keep the rolled result as a partial lead and hold the tested Lamé change. The two-inch source remains a separate driver/interface study.

## Verification status

The generator and CMA-ME regression batch passed 199 tests. The config, size and mesh batch passed 89, with BoTorch tests running separately in the 0.18.1 environment. The scalar/TuRBO regression batch passed 36, and the study/package batch passed 41 with the configured BoTorch interpreter and native Windows hard-link support. These batches overlap. Seven GPU verifies completed across the three queue files. The GPU lock was free and no project Julia worker remained after cleanup. The matched results test fixed designs and numerical settings. The multi-seed optimizer and spatial convergence gates remain open.

## Next implementation slices

### 1. Complete P0 geometry authority and validate proposal resume

**Suggested model: GPT-6.2 Astra, high reasoning.** This slice can run beside directivity attribution.

```text
Work in C:/Users/hunte/Hrns/hornlab-search. Read AGENTS.md and docs/evidence/size_aware_2026-11-24/HANDOFF.md. Use the canonical checkout and preserve concurrent changes and immutable historical artifacts. No GPU needed.

Use config.envelope_policy, design.size, mesh/build.py and mesh/grid_build.py as the current contract. Make authoritative outer dimensions source-aware for formula, GRID, CAD and mounted cases, including declared protrusions and a separately labeled mouth measurement. Mark shell, flange, mounting and material-volume uncertainty where canonical CAD or mesh evidence is absent. Preserve legacy enforce:true recipe/cache outputs. For opt-in exact limits, use lower/upper preflight evidence to admit, refuse or defer uncertain candidates to a CPU mesh check. Cover whole-horn and symmetry-plane inputs and exclude source/enclosure artifacts when legitimately separable. Do not modify frozen acoustic scoring.

Exercise production, epsilon 1.05 and discovery across CMA, CMA-ME, scalar and TuRBO, including journal resume with changed policy, oversize-compatible historical training, invalid topology, cap overflow and explicit pool exhaustion. Run CPU shape references that include genuine asymmetric/swept geometry, a native formula, Rolled and Lamé, and a CAD case if installed. Record false refusals, mesh discrepancy and aperture convention in evidence. Stop promotion where the measured check and available authority disagree.
```

### 2. Matched scalar and CMA benchmark

**Suggested model: GPT-6.2 Astra, high reasoning.** Prepare offline while slice 1 runs. Launch only after slice 1 verification.

```text
Work in C:/Users/hunte/Hrns/hornlab-search. Read AGENTS.md, docs/evidence/size_aware_2026-11-24/HANDOFF.md, README.md there, docs/BAYESIAN_STUDIES_RUNBOOK.md and the local newest metric BO handoff. Use the existing scalar qLogNEI/TuRBO and CMA machinery. Freeze a compatible Home Fold screen cohort and test Compact500 Crowe eligibility independently. Before pooling any two envelope arms, prove exact acoustic equivalence of target, weights, scorer, frequency/balloon grids, source, mounting, numerical fidelity and dependency identity. Bind candidate policy separately from historical physical/acoustic results or provide exact common replay.

Prepare paired seeds 4101, 4102 and 4103 with identical starting observations, bounds and mesh/solve settings. Keep discovery, exact product and near-envelope scalar arms, plus matching CMA-ES. Stratify epsilon 1.05/1.15/1.25 offline before selecting a near-envelope live arm. Begin with 8 new valid BEMs per seed per arm, paired wall-time limits and an explicit rejection-attempt cap. Predeclare fixed top product and near-frontier verification slots with identical verify geometry policy. Count unique measured solves, failures, actual wall and solver seconds and dedup/cache hits. Stop for pool exhaustion, gross refusal imbalance, incompatible fidelity or GPU uncertainty. Compare best verified product-fit J against cumulative GPU wall-hours, useful verified frontier coverage and calibration. Use existing queue infrastructure and one live GPU lock. The integrator releases the frozen queue after preflight.

If verified constrained scalar adds useful designs above its numerical uncertainty floor, promote it with reproducible evidence. Only after this baseline, test size-diversity CMA-ME or qLogNEHVI against equal budgets. Keep known dimensions exact in any acquisition and preserve the existing Pareto axes. Evaluate printer segmentation independently using actual part solids before claiming a fit.
```

### 3. Retained-return directivity attribution

**Suggested model: GPT-6.1 Terra, medium reasoning for CPU evidence. GPT-6.2 Astra, high reasoning for a new construction decision.**

```text
Work in C:/Users/hunte/Hrns/hornlab-search. Read AGENTS.md, docs/evidence/size_aware_2026-11-24/DIRECTIVITY_VERIFY.md and ANCHOR_GEOMETRY.md, and use the HornLab acoustic-grounding skill. Start with the saved exact neutral configs in that evidence folder. Produce CPU-cleared rolled H-only +10°/V 0° and H 0°/V-only +6° fixed controls. Hold the existing window, anchor knobs, source, termination and numerical specs. Reproduce the neutral mesh digest, then ask the integrator to release only those two matched verify jobs if attribution still addresses the observed H/V tradeoff. Compare the 4–8 kHz H corridor, midband width, V, diagonals, DI and loading. Stop extending the body law if it cannot improve high-frequency H without worsening the useful band beyond the numerical floor.

For Lamé, retain the exact rounded-square parent and return. Study a neutral-controlled intermediate/terminal wall law using the typology-research skill before code. Demonstrate return and source parity, topology, tangent continuity and authority before requesting a solve. A two-inch branch requires model-specific CP-850Nd exit geometry, the 7° convention, mounting and wavefront sensitivity. Use a separate source identity and matched experiments within that identity.
```
