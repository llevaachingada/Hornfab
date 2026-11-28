# Docs index — topic catalog

Look up a topic, then open its catalog. This file is an index, not a feed: the pre-2026-11-25
newest-first feed is preserved verbatim at [history/INDEX_feed_through_2026-11-25.md](history/INDEX_feed_through_2026-11-25.md).

Status tags: **CURRENT** = use this; **REFERENCE** = useful background; **SUPERSEDED** = replaced, kept for provenance; **HISTORICAL** = archived, not current routing.

---

## Start

- [START_HERE.md](START_HERE.md) — task, then the first file to open. **CURRENT**
- [ACTIVE_STATE.md](ACTIVE_STATE.md) — current pointer: canonical checkout, active queues, how to verify. **CURRENT**
- [../AGENTS.md](../AGENTS.md) — binding rules for every agent, precedence and routing. **CURRENT**
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — commit and PR rules. **CURRENT**
- [CODE_MAP.md](CODE_MAP.md) — module and config-folder map. **CURRENT**
- [CONTINUITY.md](CONTINUITY.md) — living log, newest entry first (read the first 60–80 lines only). **CURRENT**
- [ISSUES.md](ISSUES.md) — open work, newest first (read the first 60–80 lines only). **CURRENT**
- [NEXT_DEV_PRIORITIES.md](NEXT_DEV_PRIORITIES.md) — next development round: priorities (after the beta). **CURRENT**
- [../NOTES_FOR_SENIOR.md](../NOTES_FOR_SENIOR.md) — append-only senior notes (read the last 60 lines only). **CURRENT**

## Acoustic knowledge

- [knowledge/README.md](knowledge/README.md) — canonical navigation and applicability guidance for acoustic, geometry, scoring and optimization decisions. **CURRENT**
- [knowledge/SOURCES.md](knowledge/SOURCES.md) — source catalog. **CURRENT**
- [knowledge/sources.yaml](knowledge/sources.yaml) — source metadata. **CURRENT**
- [knowledge/claims/KH-001_keele_mouth_heuristic.md](knowledge/claims/KH-001_keele_mouth_heuristic.md) — Keele mouth sizing is not universal. **CURRENT**
- [knowledge/contracts/README.md](knowledge/contracts/README.md) — scientific construction contracts (WP-K0 drafts, 2026-11-18). **REFERENCE**
- [knowledge/THROAT_HV_CONTROL_AUDIT_2026-11-18.md](knowledge/THROAT_HV_CONTROL_AUDIT_2026-11-18.md) — throat-region H/V control audit (read-only), 2026-11-18. **REFERENCE**
- [knowledge/AGENT_BENCHMARK_SPEC_2026-11-18.md](knowledge/AGENT_BENCHMARK_SPEC_2026-11-18.md) — agent science benchmark: specification (WP-K1, draft 2026-11-18). **REFERENCE**
- [knowledge/imported/HornFab_Research_Knowledge_Base_2026-11-16.md](knowledge/imported/HornFab_Research_Knowledge_Base_2026-11-16.md) — HornFab: consolidated horn research and source library (imported verbatim). **REFERENCE**
- [knowledge/templates/typology.md](knowledge/templates/typology.md) — family-card template. **REFERENCE**
- [knowledge/templates/claim.md](knowledge/templates/claim.md) — claim template. **REFERENCE**

## Scoring & briefs

- [knowledge/SCORING_REFERENCE.md](knowledge/SCORING_REFERENCE.md) — scoring reference (objective v1–v11). **CURRENT**
- [Research: scoring, objectives and acoustic truth](research/README.md#scoring-objectives-and-acoustic-truth) — scoring, objectives and acoustic truth. **CURRENT**
- [TOOLS: re-score and replay](TOOLS.md#re-score-and-replay) — re-score and replay stored designs without a solver. **CURRENT**
- [TOOLS: check a config or shape](TOOLS.md#check-a-config-or-shape) — check a config or shape before spending GPU time. **CURRENT**

## Families

- [knowledge/FAMILY_LAWS.md](knowledge/FAMILY_LAWS.md) — FAMILY_LAWS — joint validity laws across generator families. **CURRENT**
- [biradial.md](knowledge/typologies/biradial.md) — Biradial. **REFERENCE**
- [cd_backbone.md](knowledge/typologies/cd_backbone.md) — CD wall-angle backbone (returned-lip hybrids). **CURRENT**
- [classical.md](knowledge/typologies/classical.md) — Classical profiles: conical, exponential, tractrix. **REFERENCE**
- [experimental_morphs.md](knowledge/typologies/experimental_morphs.md) — Experimental morphs and reconstructions. **REFERENCE**
- [favl_canonical.md](knowledge/typologies/favl_canonical.md) — favL / `osse_rollback` (FAV-001 canonical). **CURRENT**
- [klangfilm_lame.md](knowledge/typologies/klangfilm_lame.md) — Klangfilm–Lamé. **CURRENT**
- [lecleach_iwata.md](knowledge/typologies/lecleach_iwata.md) — Le Cléac'h / JMLC and Iwata: provisional family note. **REFERENCE**
- [meh.md](knowledge/typologies/meh.md) — Multiple-entry horns (MEH). **REFERENCE**
- [multicell.md](knowledge/typologies/multicell.md) — Multicell. **REFERENCE**
- [osse_ath.md](knowledge/typologies/osse_ath.md) — OS-SE / ATH. **REFERENCE**
- [rim_beak.md](knowledge/typologies/rim_beak.md) — Rim beak (freestanding mouth). **CURRENT**
- [rolled.md](knowledge/typologies/rolled.md) — Rolled family (rolled rectangle / Crowe-section relief). **CURRENT**
- [salmon.md](knowledge/typologies/salmon.md) — Salmon / hyperbolic expansion. **REFERENCE**
- [sculpted_rosse_crowe.md](knowledge/typologies/sculpted_rosse_crowe.md) — Sculpted R-OSSE meridians / Crowe-inspired sections. **CURRENT**
- [throat_sculpt.md](knowledge/typologies/throat_sculpt.md) — Throat sculpt (directional throat constriction / angular slot). **REFERENCE**

## Search & BO

- [TOOLS: plan a search](TOOLS.md#plan-a-search) — plan a search, check headroom and run CMA-ES. **CURRENT**
- [TOOLS: BO identity, encoding and metric-BO](TOOLS.md#bo-identity-encoding-and-metric-bo) — BO identity, encoding and metric-BO. **CURRENT**
- [Research: search math, optimizers and refusals](research/README.md#search-math-optimizers-and-refusals) — search math, optimizers and refusals. **CURRENT**
- [Research: BO studies and the BoTorch GUI](research/README.md#bo-studies-and-the-botorch-gui) — BO studies and the BoTorch GUI. **CURRENT**
- [.claude/skills/hornlab-search-economy/SKILL.md](../.claude/skills/hornlab-search-economy/SKILL.md) — prove a run has somewhere to go before spending GPU time; BO identity and snapped starts. **CURRENT**
- [.claude/skills/hornlab-generator-family/SKILL.md](../.claude/skills/hornlab-generator-family/SKILL.md) — generator identity: implementation digest, new-module registration, CRLF byte edits. **CURRENT**

## Nights/GPU

- [queue/README.md](queue/README.md) — nights and the queue directory: live vs committed copies, splice, operating rules. **CURRENT**
- [TOOLS: queue and monitor a night](TOOLS.md#queue-and-monitor-a-night) — queue and monitor a night. **CURRENT**
- [Evidence: campaigns, nights and artifacts](evidence/CATALOG.md#campaigns-nights-and-artifacts) — campaigns, nights and artifacts. **CURRENT**
- [.claude/skills/hornlab-night-queue/SKILL.md](../.claude/skills/hornlab-night-queue/SKILL.md) — unattended GPU solve queues: watchdog keys, exit 75, live-night splice. **CURRENT**
- [.claude/skills/hornlab-gpu-job/SKILL.md](../.claude/skills/hornlab-gpu-job/SKILL.md) — single GPU job mechanics: hygiene, log capture, verified shutdown. **CURRENT**

## Tools

- [TOOLS.md](TOOLS.md) — tools — a task-first catalog of every live entry point. **CURRENT**
- [TOOLS: check a config or shape](TOOLS.md#check-a-config-or-shape) — check a config or shape. **CURRENT**
- [TOOLS: analyse a cohort](TOOLS.md#analyse-a-cohort) — analyse a cohort: knob effects, sensitivity, convergence. **CURRENT**
- [TOOLS: verify and compare](TOOLS.md#verify-and-compare) — verify and compare. **CURRENT**
- [TOOLS: render and report](TOOLS.md#render-and-report) — render and report. **CURRENT**
- [TOOLS: data and archive](TOOLS.md#data-and-archive) — data and archive exports. **CURRENT**
- [TOOLS: historical tools](TOOLS.md#historical-tools) — dead and one-off tools kept for provenance. **HISTORICAL**

## Evidence by family

- [evidence/CATALOG.md](evidence/CATALOG.md) — one line per evidence folder, evidence document and committed queue copy. **CURRENT**
- [CD backbone](evidence/CATALOG.md#cd-backbone) — CD backbone. **CURRENT**
- [Coverage, constancy and room fit](evidence/CATALOG.md#coverage-constancy-and-room-fit) — Coverage, constancy and room fit. **CURRENT**
- [Compact 400, favL and size policy](evidence/CATALOG.md#compact-400-favl-and-size-policy) — Compact 400, favL and size policy. **CURRENT**
- [BO studies and GUI](evidence/CATALOG.md#bo-studies-and-gui) — BO studies and GUI. **CURRENT**
- [Rolled and Klangfilm-Lame families](evidence/CATALOG.md#rolled-and-klangfilm-lame-families) — Rolled and Klangfilm-Lame families. **CURRENT**
- [Sculpted / R-OSSE, ripple and HF](evidence/CATALOG.md#sculpted--rosse-ripple-and-hf) — Sculpted / R-OSSE, ripple and HF. **CURRENT**
- [System, mounting, measurement and MEH](evidence/CATALOG.md#system-mounting-measurement-and-meh) — System, mounting, measurement and MEH. **CURRENT**
- [Mesh, frequency and termination policy](evidence/CATALOG.md#mesh-frequency-and-termination-policy) — Mesh, frequency and termination policy. **CURRENT**
- [Scoring and objective versions](evidence/CATALOG.md#scoring-and-objective-versions) — Scoring and objective versions. **CURRENT**
- [Search, cohorts and verification](evidence/CATALOG.md#search-cohorts-and-verification) — Search, cohorts and verification. **CURRENT**
- [Typologies and geometry authority](evidence/CATALOG.md#typologies-and-geometry-authority) — Typologies and geometry authority. **CURRENT**
- [Crowe typology and geometry truth](evidence/CATALOG.md#crowe-typology-and-geometry-truth) — Crowe typology and geometry truth. **CURRENT**
- [Solver, compute and benchmarking](evidence/CATALOG.md#solver-compute-and-benchmarking) — Solver, compute and benchmarking. **CURRENT**
- [Committed queue configs](evidence/CATALOG.md#committed-queue-configs) — Committed queue configs. **CURRENT**

## Research by topic

- [research/README.md](research/README.md) — research by topic: current dossier first, superseded and negative results after. **CURRENT**
- [Scoring, objectives and acoustic truth](research/README.md#scoring-objectives-and-acoustic-truth) — Scoring, objectives and acoustic truth. **CURRENT**
- [Search math, optimizers and refusals](research/README.md#search-math-optimizers-and-refusals) — Search math, optimizers and refusals. **CURRENT**
- [BO studies and the BoTorch GUI](research/README.md#bo-studies-and-the-botorch-gui) — BO studies and the BoTorch GUI. **CURRENT**
- [Data, GA and compute allocation](research/README.md#data-ga-and-compute-allocation) — Data, GA and compute allocation. **CURRENT**
- [Queue planning, campaigns and evidence indexes](research/README.md#queue-planning-campaigns-and-evidence-indexes) — Queue planning, campaigns and evidence indexes. **CURRENT**
- [Typologies, geometry and published seeds](research/README.md#typologies-geometry-and-published-seeds) — Typologies, geometry and published seeds. **CURRENT**
- [Drivers and source modelling](research/README.md#drivers-and-source-modelling) — Drivers and source modelling. **CURRENT**
- [Solver, compute and test suite](research/README.md#solver-compute-and-test-suite) — Solver, compute and test suite. **CURRENT**
- [Acoustic physics, room and system](research/README.md#acoustic-physics-room-and-system) — Acoustic physics, room and system. **CURRENT**
- [Integration and research indexes](research/README.md#integration-and-research-indexes) — Integration and research indexes. **CURRENT**
- [research_view_2026-11-27/README.md](research/research_view_2026-11-27/README.md) — M1 read-only research snapshot (frozen manifest, cohort inventory, score attribution, findings); ADR + handback. **CURRENT**

## Guides

- [AGENT_BOOTSTRAP_CONTAINER.md](guides/AGENT_BOOTSTRAP_CONTAINER.md) — Agent bootstrap for the `Hrns` umbrella workspace. **CURRENT**
- [BAYESIAN_STUDIES_RUNBOOK.md](guides/BAYESIAN_STUDIES_RUNBOOK.md) — Bayesian design studies. **CURRENT**
- [BETA_QUICKSTART.md](guides/BETA_QUICKSTART.md) — Beta quickstart: from a target to a printable horn. **REFERENCE**
- [BRIEF_AND_SCORING_GUIDE_2026-10-25.md](guides/BRIEF_AND_SCORING_GUIDE_2026-10-25.md) — Brief and scoring guide — the S1a driver pass (2026-10-25). **REFERENCE**
- [CLOUD_GPU_RUNBOOK.md](guides/CLOUD_GPU_RUNBOOK.md) — Cloud GPU runbook (RunPod-first). **CURRENT**
- [COLLABORATOR_PULL_RUNBOOK_2026-11-02.md](guides/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md) — Runbook: pull the campaign solves (agent-executable, 2026-11-02). **CURRENT**
- [DRIVER_MODEL.md](guides/DRIVER_MODEL.md) — Horn loudness and the compression-driver model (P12, 2026-10-27). **CURRENT**
- [FORKS.md](guides/FORKS.md) — Forks of Magnus's packages: how we change the solver or mesher. **CURRENT**

## Handoffs

- [HANDBACK_CLOUD_2026-11-18.md](handoffs/HANDBACK_CLOUD_2026-11-18.md) — HANDBACK (cloud senior, 2026-11-18): G1-G6 done; what the local orchestrator runs next. **REFERENCE**
- [HANDBACK_LOCAL_2026-11-18.md](handoffs/HANDBACK_LOCAL_2026-11-18.md) — HANDBACK (local orchestrator, 2026-11-18 late evening): the Fable GPU chain landed — what the senior needs. **REFERENCE**
- [HANDOFF_2026-11-18.md](handoffs/HANDOFF_2026-11-18.md) — HANDOFF 2026-11-18: everything is on ONE branch, `hornfab-all-2026-11-18`. **REFERENCE**
- [HANDOFF_COLLABORATOR_2026-11-14.md](handoffs/HANDOFF_COLLABORATOR_2026-11-14.md) — Collaborator handoff, 2026-11-14: what was built, with the optimization side first. **REFERENCE**
- [HANDOFF_ROLLED_TERMINAL_2026-11-20.md](handoffs/HANDOFF_ROLLED_TERMINAL_2026-11-20.md) — HANDOFF — rolled H terminal / rollback geometry, width 500 + yellow C. **REFERENCE**
- [HANDOFF_SYSTEM_CLOSEOUT_2026-11-21.md](handoffs/HANDOFF_SYSTEM_CLOSEOUT_2026-11-21.md) — Horn + woofer system closeout — senior handoff (2026-11-21). **REFERENCE**
- [HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md](handoffs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md) — HornLab + Horn/Woofer System — Complete Senior Handoff Handbook. **REFERENCE**
- [REPO_FINDABILITY_HANDOFF_2026-11-25.md](handoffs/REPO_FINDABILITY_HANDOFF_2026-11-25.md) — Senior handoff: make existing tools, research and evidence findable (2026-11-25). **CURRENT**

## GUI

- [TOOLS: render and report](TOOLS.md#render-and-report) — render and report, including `hornlab-search gui`. **CURRENT**
- [Research: BO studies and the BoTorch GUI](research/README.md#bo-studies-and-the-botorch-gui) — BO studies and the BoTorch GUI. **CURRENT**
- [Evidence: BO studies and GUI](evidence/CATALOG.md#bo-studies-and-gui) — BO studies and GUI. **CURRENT**
- [CODE_MAP.md](CODE_MAP.md) — module map, including the GUI and system UI modules. **CURRENT**

## Data/archive

- [TOOLS: data and archive](TOOLS.md#data-and-archive) — data and archive exports. **CURRENT**
- [top_designs/README.md](top_designs/README.md) — top GPU-solved designs, by typology and score set. **CURRENT**
- [system_data/README.md](system_data/README.md) — system data export (HORN + VENTED-WOOFER). **CURRENT**
- [history/manifest.json](history/manifest.json) — rotation manifest: archived CONTINUITY/ISSUES sources, entry counts and sha256. **CURRENT**
- [Evidence: infrastructure, provenance and releases](evidence/CATALOG.md#infrastructure-provenance-and-releases) — infrastructure, provenance and releases. **CURRENT**

## Historical

- [history/INDEX_feed_through_2026-11-25.md](history/INDEX_feed_through_2026-11-25.md) — Docs index (the pre-rewrite newest-first feed, copied verbatim). **HISTORICAL**
- [CONTINUITY_2026-10-12_2026-10-22.md](history/CONTINUITY_2026-10-12_2026-10-22.md) — CONTINUITY 2026-10-12 to 2026-10-22. **HISTORICAL**
- [CONTINUITY_2026-10-23_2026-10-31.md](history/CONTINUITY_2026-10-23_2026-10-31.md) — CONTINUITY 2026-10-23 to 2026-10-31. **HISTORICAL**
- [ISSUES_closed.md](history/ISSUES_closed.md) — Closed GitHub issues (#1-#11). **HISTORICAL**
- [NOTES_FOR_SENIOR_resolved.md](history/NOTES_FOR_SENIOR_resolved.md) — NOTES FOR SENIOR - resolved blocks. **HISTORICAL**
- [AGENTS_historical_2026-11.md](history/AGENTS_historical_2026-11.md) — AGENTS / CLAUDE historical material (moved 2026-11-25). **HISTORICAL**
- [ACTIVE_STATE_history_2026-11.md](history/ACTIVE_STATE_history_2026-11.md) — ACTIVE_STATE — current pointer. **HISTORICAL**

**Archive 2026-10** — superseded plans, handoffs and reports (23 files).

- [BETA_SESSION_PLAN.md](archive/2026-10/BETA_SESSION_PLAN.md) — Beta session plan (2026-10-23, refreshed for the GUI). **HISTORICAL**
- [BL_LEARNINGS_IMPLEMENTATION.md](archive/2026-10/BL_LEARNINGS_IMPLEMENTATION.md) — Learning from Boundary Lab 0.5.0: implemented items and plan for the rest. **HISTORICAL**
- [BOUNDARY_LAB_0.5_RESEARCH.md](archive/2026-10/BOUNDARY_LAB_0.5_RESEARCH.md) — Boundary Lab 0.5.0: research findings for hornlab-search. **REFERENCE**
- [BOUNDARY_LAB_INTEGRATION_PLAN.md](archive/2026-10/BOUNDARY_LAB_INTEGRATION_PLAN.md) — Boundary Lab 0.5.0 integration plan for hornlab-search. **REFERENCE**
- [CLOUD_GPU_REPORT.md](archive/2026-10/CLOUD_GPU_REPORT.md) — Cloud GPU rental for hornlab-search: research and analysis. **REFERENCE**
- [CONE_SOURCE_MODEL_PLAN_2026-10-29.md](archive/2026-10/CONE_SOURCE_MODEL_PLAN_2026-10-29.md) — Cone source model plan — non-uniform cone velocity for the `cone_plughorn` mid. **HISTORICAL**
- [DATA_CONSOLIDATION_PLAN_2026-10-29.md](archive/2026-10/DATA_CONSOLIDATION_PLAN_2026-10-29.md) — Data consolidation plan — 2026-10-29. **HISTORICAL**
- [DATA_CONSOLIDATION_RESULT_2026-10-30.md](archive/2026-10/DATA_CONSOLIDATION_RESULT_2026-10-30.md) — Data consolidation — result, 2026-10-30. **HISTORICAL**
- [GUI_CONTRAST_PLAN.md](archive/2026-10/GUI_CONTRAST_PLAN.md) — GUI contrast & form-visibility plan (proposed, 2026-10-24). **HISTORICAL**
- [GUI_INTEGRATION_PLAN_2026-10-25.md](archive/2026-10/GUI_INTEGRATION_PLAN_2026-10-25.md) — GUI integration plan — planning pass (proposed, 2026-10-25). **HISTORICAL**
- [GUI_PLAN.md](archive/2026-10/GUI_PLAN.md) — Local web GUI for hornlab-search (plan, 2026-10-23). **HISTORICAL**
- [HANDOFF_BETA.md](archive/2026-10/HANDOFF_BETA.md) — HANDOFF: hornlab-search beta-readiness pass. **HISTORICAL**
- [HANDOFF_BRIEF_DESIGN_2026-10-24.md](archive/2026-10/HANDOFF_BRIEF_DESIGN_2026-10-24.md) — HANDOFF — Brief design & baseline-settings pass (owner goals → real briefs). **HISTORICAL**
- [HANDOFF_COLLABORATOR_2026-10-27.md](archive/2026-10/HANDOFF_COLLABORATOR_2026-10-27.md) — Handoff for the collaborator: pulling the repo and finding the optimization data. **SUPERSEDED**
- [HANDOFF_NEXT_RUNS_2026-10-30.md](archive/2026-10/HANDOFF_NEXT_RUNS_2026-10-30.md) — Handoff: next runs after the 2026-10-30 coverage atlas. **SUPERSEDED**
- [HIGH_FREQUENCY_OPTIONS.md](archive/2026-10/HIGH_FREQUENCY_OPTIONS.md) — Reaching 12 kHz on the 8 GB card: options and evidence. **REFERENCE**
- [IMPLEMENTATION_PLAN_2026-10-27.md](archive/2026-10/IMPLEMENTATION_PLAN_2026-10-27.md) — Implementation plan, 2026-10-27: after the campaign smoke night. **HISTORICAL**
- [SENIOR_ARCHITECTURE_REPORT_2026-10-22.md](archive/2026-10/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md) — Senior architecture report, 2026-10-22: where hornlab-search sits, and what to do next. **HISTORICAL**
- [SENIOR_REVIEW_2026-10-14.md](archive/2026-10/SENIOR_REVIEW_2026-10-14.md) — Senior review, 2026-10-14: PR #12 (`claude/wave-3-implementation-review-2dk4qe`). **HISTORICAL**
- [SOLVE_CAMPAIGN_PLAN_2026-10-26.md](archive/2026-10/SOLVE_CAMPAIGN_PLAN_2026-10-26.md) — Solve campaign plan v2 — 2026-10-26 (hardened rewrite). **HISTORICAL**
- [SWARM_PLAN_2026-10-30.md](archive/2026-10/SWARM_PLAN_2026-10-30.md) — Swarm implementation plan — 2026-10-30 (runs while night `n2_gapfill_2026-10-30` is live). **HISTORICAL**
- [TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md](archive/2026-10/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md) — Per-typology baseline settings (Phase D) — 2026-10-25. **REFERENCE**
- [TYPOLOGY_PLAN.md](archive/2026-10/TYPOLOGY_PLAN.md) — Typology plan v2: classical horns, Magnus's families, hybrids, and family selection. **HISTORICAL**

**Archive 2026-11** — superseded plans, handoffs and reports (13 files).

- [AGENT_ORCHESTRATION_REVIEW_2026-11-16.md](archive/2026-11/AGENT_ORCHESTRATION_REVIEW_2026-11-16.md) — Hornlab/HornFab — Agent Orchestration Performance Review. **HISTORICAL**
- [GUI_HANDOFF_2026-11-12.md](archive/2026-11/GUI_HANDOFF_2026-11-12.md) — GUI verify-view + UX pass: handoff (2026-11-12, 16:00 EST). **HISTORICAL**
- [GUI_UX_PASS_2026-11-14.md](archive/2026-11/GUI_UX_PASS_2026-11-14.md) — GUI / data-viz pass — 2026-11-14. **HISTORICAL**
- [GUI_VERIFY_ACCEPTANCE_2026-11-12.md](archive/2026-11/GUI_VERIFY_ACCEPTANCE_2026-11-12.md) — GUI verify-view + UX pass — live acceptance (2026-11-12). **HISTORICAL**
- [GUI_VERIFY_VIEW_PLAN_2026-11-12.md](archive/2026-11/GUI_VERIFY_VIEW_PLAN_2026-11-12.md) — GUI verify view + whole-GUI UX hardening — implementation plan (2026-11-12, v2). **HISTORICAL**
- [HANDOFF_ANALYSIS_PAGE_2026-11-12.md](archive/2026-11/HANDOFF_ANALYSIS_PAGE_2026-11-12.md) — Work order — make the GUI Analysis page a real visual report (2026-11-12). **HISTORICAL**
- [HANDOFF_S8_S7_GUI_2026-11-13.md](archive/2026-11/HANDOFF_S8_S7_GUI_2026-11-13.md) — Handoff — GUI architecture and planning for the S8 discovery and S7 surrogate-validation tools (2026-11-13). **HISTORICAL**
- [HORNFAB_SENIOR_DECISION_2026-11-19.md](archive/2026-11/HORNFAB_SENIOR_DECISION_2026-11-19.md) — HornFab — Senior Engineering Decision and Next-Stage Plan. **REFERENCE**
- [IMPLEMENTATION_PLAN_2026-11-12_DAY.md](archive/2026-11/IMPLEMENTATION_PLAN_2026-11-12_DAY.md) — Implementation plan, 2026-11-12 day: hardening and search improvements while the GPU + CPU lanes run. **HISTORICAL**
- [LOCAL_AGENT_PROMPT_2026-11-18.md](archive/2026-11/LOCAL_AGENT_PROMPT_2026-11-18.md) — LOCAL AGENT PROMPT — finish the Fable plan (written by the cloud senior, 2026-11-18). **HISTORICAL**
- [LOG_ARCHIVAL_PROPOSAL_2026-11-17.md](archive/2026-11/LOG_ARCHIVAL_PROPOSAL_2026-11-17.md) — Proposal — bounded living logs (rotation + manifest). **REFERENCE**
- [OPENCODE_HANDOFF_2026-11-12.md](archive/2026-11/OPENCODE_HANDOFF_2026-11-12.md) — OpenCode orchestrator handoff, night of 2026-11-12. **HISTORICAL**
- [SENIOR_PLAN_2026-11-12.md](archive/2026-11/SENIOR_PLAN_2026-11-12.md) — Senior plan, 2026-11-12: one main, one truth, then speed and the GUI. **HISTORICAL**

- [archive/2026-11-14/README.md](archive/2026-11-14/README.md) — batch not moved; these files now live under docs/guides, docs/handoffs, docs/archive/2026-10 and docs/archive/2026-11. **HISTORICAL**

