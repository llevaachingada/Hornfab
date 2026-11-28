# Research by topic

`docs/research/` holds the design, scoring and optimization research passes. This page is the
reading order. Each group lists the **current** dossier first (link plus its key conclusion), then
superseded or negative results kept for provenance. A superseded entry names its successor.

Link text is the repo-relative path; targets resolve from this file. For experiments rather than
research, start at [`docs/evidence/CATALOG.md`](../evidence/CATALOG.md); for queue mechanics see
[`docs/queue/README.md`](../queue/README.md).

## Scoring, objectives and acoustic truth

- [docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md](cd_metrics_2026-11-20/V11_CD_MATRIX.md) — 2026-11-20 — V11 adds v10 plus CD-brief-only `cd_lw`, `cd_di_std`, `cd_nacc` and `offaxis_smooth`; M1/M3 are report-only.
- [docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md](HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md) — 2026-11-17 — Stop spending scarce solves on poorly resolved goals; make the solver-bound surface and scoring fidelity measurable first.
- [docs/research/ONAXIS_WEIGHTING_2026-11-14.md](ONAXIS_WEIGHTING_2026-11-14.md) — 2026-11-14 — Do not just raise on-axis weight; fix flat to start at crossover and score the listening window.
- [docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md](OBJECTIVE_V8_PROPOSAL_2026-11-12.md) — 2026-11-12 — Do not register v8 or switch a brief; it is a different ruler needing a paired-seed A/B first.
- [docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md](LOADING_OBJECTIVES_RECONCILED_2026-11.md) — 2026-11-12 — Keep v6 for Le Cleac'h/rollback loading families and v7 for CD briefs; do not create a v8.
- [docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md](SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md) — 2026-10-27 — Ranking, not the solver, is the main reason a top-scoring horn may disappoint; J is blind to output and loading.
- [docs/research/V4_SCORING_REVIEW_2026-10-27.md](V4_SCORING_REVIEW_2026-10-27.md) — 2026-10-27 — Normalisation changes the winner in about 40% of cells; add DI constancy and a presence-band narrow-coverage penalty.
- [docs/research/V4_TOLERANCE_RESEARCH_2026-10-27.md](V4_TOLERANCE_RESEARCH_2026-10-27.md) — 2026-10-27 — Pattern constancy is best measured by DI spread and polar similarity; tolerances must be class-specific.

## Search math, optimizers and refusals

- [docs/research/optimizer_audit_2026-11-21/README.md](optimizer_audit_2026-11-21/README.md) — 2026-11-21 — Make the optimizer decision-capable first: fix CMA-MAE result-archive semantics, stop-rule identity and v10/v11 BO compatibility.
- [docs/research/S8_DISCOVERY_RESOLUTION_2026-11-13.md](S8_DISCOVERY_RESOLUTION_2026-11-13.md) — 2026-11-13 — Geometry coordinates come only from Design; scores cannot enter novelty; QD and Pareto answer different questions.
- [docs/research/REFUSALS_AND_OPTIMIZER_HANDOFF_2026-11-12.md](REFUSALS_AND_OPTIMIZER_HANDOFF_2026-11-12.md) — 2026-11-12 — Yes for plain CMA via resample plus valid budget; no simple config drop exists for CMA-ME.
- [docs/research/SEARCH_MATH_DOSSIER_2026-11.md](SEARCH_MATH_DOSSIER_2026-11.md) — undated — Refusals and seed variance dominate; screen cannot rank its own top-20, so verify finalists and rank by verify J.
- [docs/research/LEARNINGS_2026-10-26.md](LEARNINGS_2026-10-26.md) — 2026-10-26 — Boxes were the binding constraint; use physical-range boxes and graded refusals, never narrow a box.

## BO studies and the BoTorch GUI

- [docs/research/metric_bo_2026-11-22/12_HANDOFF_2026-11-24.md](metric_bo_2026-11-22/12_HANDOFF_2026-11-24.md) — 2026-11-24 — Acquisition evidence passes for an exploratory pilot (2/3 opens); the 81271 HOLD stands and the LMC arm is research-only.
- [docs/research/BO_GUI_CLOUD_HANDOFF_2026-11-16.md](BO_GUI_CLOUD_HANDOFF_2026-11-16.md) — 2026-11-16 — The cloud session never merges to main or runs solves; all checks are offline pytest with synthetic fixtures.
- [docs/research/BO_GUI_HANDOFF_2026-11-16.md](BO_GUI_HANDOFF_2026-11-16.md) — 2026-11-16 — The GUI served one study store; per-arm roots made all BoTorch studies invisible, the single bug behind the missing feature.
- [docs/research/BO_GUI_SOURCE_AUDIT_HANDOFF_2026-11-16.md](BO_GUI_SOURCE_AUDIT_HANDOFF_2026-11-16.md) — 2026-11-16 — Give BoTorch the same physical horn inspector as CMA while keeping Bayesian search diagnostics distinct.
- [docs/research/BO_GUI_DESIGN_2026-11-15.md](BO_GUI_DESIGN_2026-11-15.md) — 2026-11-15 — The browser never computes or ranks a score; BoTorch work stays in the Bayesian subprocess.
- [docs/research/bo_study/CONTINUATION_SLICE_MAP_2026-11-13.md](bo_study/CONTINUATION_SLICE_MAP_2026-11-13.md) — 2026-11-13 — M0/M1 are partially present but the M2 gate is not established; fix the manifest test collection break first.
- [docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md](BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md) — 2026-11-12 — Scalar, Pareto and trust-region variants are implemented; constraint and cost extensions are present but not wired into production.
- [docs/research/HORN_OPTIMIZATION_HARDENING_2026-11-12.md](HORN_OPTIMIZATION_HARDENING_2026-11-12.md) — 2026-11-12 — Put reusable data/rescoring and the knob-to-geometry-to-response-to-score explanation first; keep BoTorch in full scope.

Superseded:

- [docs/research/BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md](BO_GUI_IMPLEMENTATION_PLAN_2026-11-16.md) — 2026-11-16 — superseded by `BO_GUI_CLOUD_HANDOFF_2026-11-16`; most work packages already exist on feat/bo-gui, but keep the diagnostics spec.
- [docs/research/BO_GUI_HANDOFF_2026-11-15.md](BO_GUI_HANDOFF_2026-11-15.md) — 2026-11-15 — superseded by `BO_GUI_HANDOFF_2026-11-16`; keep only for workflow and visualisation reasoning.

## Data, GA and compute allocation

- [docs/research/compute_study_2026-11-12/COMPUTE_STUDY.md](compute_study_2026-11-12/COMPUTE_STUDY.md) — 2026-11-12 — `atlas__core_law` is the highest-priority resume; seed variance is missing for all v4 atlas cells.
- [docs/research/COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md](COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md) — 2026-11-12 — Build reliable comparisons first, keep CMA as the baseline and BoTorch as an opt-in first-class proposal track.
- [docs/research/DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md](DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md) — 2026-11-12 — M0 preservation and rescoring come first; BoTorch adapter work can start in parallel once contracts freeze.

Superseded:

- [docs/research/COUNCIL_REVIEW_HANDOFF_2026-11-12.md](COUNCIL_REVIEW_HANDOFF_2026-11-12.md) — 2026-11-12 — superseded by `COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12`; its G-placeholder and 26-seed instructions are historical.
- [docs/research/DATA_GA_RESEARCH_PLAN_2026-11-12.md](DATA_GA_RESEARCH_PLAN_2026-11-12.md) — 2026-11-12 — superseded by `COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12`; preserved as the raw input, recommendations and execution order are historical.

## Queue planning, campaigns and evidence indexes

- [docs/research/FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md](FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md) — 2026-11-16 — On the home brief the wall is envelope/geometry, not GPU; the refusal taxonomy cannot be read as geometry versus envelope.
- [docs/research/fable_architecture_2026-11-16/README.md](fable_architecture_2026-11-16/README.md) — 2026-11-16 — Index and reading order only; the findings live in the 15 linked dossier files.
- [docs/research/QUEUE_PLAN_REV2_2026-11-13.md](QUEUE_PLAN_REV2_2026-11-13.md) — 2026-11-13 — Ablation before metrics_v2; J is not the readout — read raw cuts, balloon, off-axis peak and `z_throat`.
- [docs/research/NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md](NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md) — 2026-11-12 — Recommended 80x80/80x60 at 700 Hz with about a 5.5 kHz screen top; 50 degrees at 700 Hz is not reachable.
- [docs/research/campaign_2026-10-26/ORCH_FINDINGS.md](campaign_2026-10-26/ORCH_FINDINGS.md) — 2026-10-26 — Per-family mouth-times-fc constants differ: salmon rows about 3.23e5, Le Cleac'h 1.88e5; applying 1.88e5 to salmon seeds them about 1.7x too big.

## Typologies, geometry and published seeds

- [docs/research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md](typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md) — 2026-11-25 — Rolled `bb_h` 0.5 passes H 65.7 deg at 8 kHz and J 8.121 to 5.407; rolled 1.0 and both Lame doses fail.
- [docs/research/compact400_2026-11-19/README.md](compact400_2026-11-19/README.md) — 2026-11-19 — The 1.4-inch horn inside a 400 mm cube is the least-explored archive cell; floor is 0.1293 J.
- [docs/research/compact_horn_system_2026-11-19/candidate_register.md](compact_horn_system_2026-11-19/candidate_register.md) — 2026-11-19 — Under the crossover-aware identity `fold_warm` 1.0624 beats A3/A1/A2; no candidate has installed or exterior BEM.
- [docs/research/ATH_PUBLISHED_SEEDS_80x60_2026-11-16.md](ATH_PUBLISHED_SEEDS_80x60_2026-11-16.md) — 2026-11-16 — T1 Tritonia-H80 ranks first for 80x60; TwinRay-380 landscape first for 80x50; 80x60 is non-native, accept 85-90 H.
- [docs/research/CROWE_X_HORN_HANDOFF_2026-11-15.md](CROWE_X_HORN_HANDOFF_2026-11-15.md) — 2026-11-15 — `grid/osse_rollback` is the control-complete generator; test s 0.3-0.6 with longer L before showing the owner.
- [docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md](ATH_SUPERFORMULA_AND_GSA_2026-10-25.md) — 2026-10-25 — Not started and owner-gated; P6a may run even if P6b is declined.

## Drivers and source modelling

- [docs/research/COMPRESSION_DRIVER_LIBRARY_2026-10-28.md](COMPRESSION_DRIVER_LIBRARY_2026-10-28.md) — 2026-10-28 — Catalogue only; no overall driver recommendation is stated (unclear).
- [docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md](HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md) — 2026-10-28 — Funktion-One publishes no mid-driver T/S; the driver must be measured, and the cone needs `source_motion: axial`.
- [docs/research/MEASUREMENT_CONE_DRIVER_2026-10-28.md](MEASUREMENT_CONE_DRIVER_2026-10-28.md) — 2026-10-28 — Protocol written, nothing measured yet; do not put an unmeasured number into a driver YAML.

Negative result:

- [docs/research/BUDGET_DRIVER_SHORTLIST_AUDIT_2026-11-19.md](BUDGET_DRIVER_SHORTLIST_AUDIT_2026-11-19.md) — 2026-11-19 — None of the five shortlisted drivers is evidenced; HF146R alone preserves the architecture but is unproven, and HF1460 is the measured reference.

## Solver, compute and test suite

- [docs/research/TEST_SUITE_OPTIMIZATION_2026-11-13.md](TEST_SUITE_OPTIMIZATION_2026-11-13.md) — 2026-11-13 — 41 tests (1.1%) carry 57% of test time; target 18 min to 2-3 min with every test still running.
- [docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md](TEST_SUITE_EFFICIENCY_2026-11-12.md) — 2026-11-12 — Tests are healthy; execution topology is wasteful, and fixing it is worth a 5-7x reduction.
- [docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md](MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md) — 2026-10-29 — At 5-6k dofs nothing is a 2x except quadrature order; port the existing order selector to CUDA before new solvers.
- [docs/research/CPU_SECOND_LANE_HARDENING_2026-10-28.md](CPU_SECOND_LANE_HARDENING_2026-10-28.md) — 2026-10-28 — About 1.5-1.7x more searches per night; the risk is cleanup code, not the solver.

## Acoustic physics, room and system

- [docs/research/favorites_2026-11-20/ROOM_TARGETS.md](favorites_2026-11-20/ROOM_TARGETS.md) — 2026-11-20 — H 90 degrees (corridor 75-105) is better than 80 for this room; 50-60 degrees V is enough.
- [docs/research/ripple_hf_2026-11-19/README.md](ripple_hf_2026-11-19/README.md) — 2026-11-19 — Rip is quartic detrended angular; the fixed-angle residual is largely redundant (rho=0.885), so it stays report-only.
- [docs/research/system_woofer_2026-11-18/FIRST_BEM_EVIDENCE.md](system_woofer_2026-11-18/FIRST_BEM_EVIDENCE.md) — 2026-11-18 — A real 3/3-frequency coupled solve exists; it is `installed_ideal_horn_reference`, not calibrated complete-speaker SPL.
- [docs/research/SIM_VS_REAL_HORN_2026-10-27.md](SIM_VS_REAL_HORN_2026-10-27.md) — 2026-10-27 — Ideal-source BEM ranks pattern shape above cutoff; it does not predict level, loading, cutoff peaks or distortion.
- [docs/research/THROAT_COUPLING_2026-10-27.md](THROAT_COUPLING_2026-10-27.md) — 2026-10-27 — The coupling plane must match the round driver exit exactly, with no shape change at z=0.
- [docs/research/TIME_DOMAIN_RINGING.md](TIME_DOMAIN_RINGING.md) — 2026-10-22 — The 12-36-point grids are too sparse; ringing analysis costs about 20x a screen and belongs on finalists.

## Integration and research indexes

- [docs/research/senior_pass_2026-10-24/README.md](senior_pass_2026-10-24/README.md) — 2026-10-24 — The objective often measures the wrong things; 12 kHz fits 1-inch horns, and PointGrid is a public geometry door.
- [docs/research/boundary_lab_0.5/bl_inventory.md](boundary_lab_0.5/bl_inventory.md) — 2026-10-21 — Rank 1 integration surface is project-file export plus the headless `blab project validate/solve` CLI.
