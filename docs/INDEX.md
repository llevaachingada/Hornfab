# Docs index

Start here. Code map: [`CODE_MAP.md`](CODE_MAP.md). Rules for agents: [`../CLAUDE.md`](../CLAUDE.md), [`../AGENTS.md`](../AGENTS.md).
Keep this file current: a new doc gets a line here in the same commit.

## Read first (current state)
| Doc | What it is |
|---|---|
| [CONTINUITY.md](CONTINUITY.md) | Status block + dated log, newest first. The source of truth for "where are we". |
| [ISSUES.md](ISSUES.md) | Open issues and the TO-DO list (next-round priorities at the top). |
| [FORKS.md](FORKS.md) | How we change Magnus's solver/mesher: pinned forks in `..\forks`, install by SHA, validation ladder (owner decision 2026-10-24). |
| [NEXT_DEV_PRIORITIES.md](NEXT_DEV_PRIORITIES.md) | Post-beta priorities: P1 fused CUDA assembly (DONE, M2), P2 12 kHz pass (DONE), P3 Metal backend, P4 grid-density ideas, P5 build-decision easy wins, P6 superformula campaign + GSA-vs-CMA-ES bake-off (proposals, owner-gated). |
| [HANDOFF_BETA.md](HANDOFF_BETA.md) | Current agent handoff: beta-readiness pass, items A–G, stop conditions. |
| [HANDOFF_COLLABORATOR_2026-10-23.md](HANDOFF_COLLABORATOR_2026-10-23.md) | For the collaborator pulling `main` on 2026-10-23: setup, what runs on the GPU box, files the owner edits tonight, rules, open questions. |
| [HANDOFF_BRIEF_DESIGN_2026-10-24.md](HANDOFF_BRIEF_DESIGN_2026-10-24.md) | NEXT PASS (after M3): study list + owner interview protocol + real-driver grounding → 2–4 real briefs + baseline settings; GPU = only the owner-approved POC (budget 20). |
| [BETA_QUICKSTART.md](BETA_QUICKSTART.md) | First loop for beta testers: brief → campaign → report → STEP. |
| [BETA_SESSION_PLAN.md](BETA_SESSION_PLAN.md) | Beta session agenda, GPU etiquette, known limits, what not to try. |
| [GUI_PLAN.md](GUI_PLAN.md) | Local web GUI: goals, constraints, views, API, prior art (waveguide-generator, Boundary Lab). |
| [BETA_SESSION_PLAN.md](BETA_SESSION_PLAN.md) | Beta-day agenda (if present; written by the beta pass). |

## Design and plans
| Doc | What it is |
|---|---|
| [plan/](plan/README.md) | **Frozen** original plan and contracts (`00_ORCHESTRATOR`, `01_CONTRACTS`, task files 02–12). Never edit. `12_RESEARCH_BASIS.md` additionally carries dated research appendices (§10 neural operators; §11 ATH superformula + GSA vs CMA-ES, added 2026-10-25 owner-directed — append-only). |
| [TYPOLOGY_PLAN.md](TYPOLOGY_PLAN.md) | v2: classical typologies as generators, hybrids, briefs, campaign tiers, verification ladder. |
| [GUI_CONTRAST_PLAN.md](GUI_CONTRAST_PLAN.md) | GUI contrast & form-visibility hardening (proposed 2026-10-24, Oracle-reviewed): measured baseline, six phases (tokens/type tiers, theme boot + `?theme=` capture, chart contrast, wallSection redraw, 3D light-gray horn + lighting/shadows, semantics/tests), acceptance criteria, risk register, rollback. Awaiting owner approval. |
| [GUI_INTEGRATION_PLAN_2026-10-25.md](GUI_INTEGRATION_PLAN_2026-10-25.md) | GUI integration plan for the implementation plan's capabilities (planning pass 2026-10-25 at M5): per-WP capability/status inventory, feature hooks, provenance badge matrix, workflow maps, new/extended API contracts (`available:false` honesty), phased build order G1-G6 with per-phase offline test recipes, in-flight WIP disclosure. Oracle pre-commit review completed before push (GO-with-fixes, all applied). |
| [SENIOR_ARCHITECTURE_REPORT_2026-10-22.md](SENIOR_ARCHITECTURE_REPORT_2026-10-22.md) | Where the repo sits vs Boundary Lab / HornLab; priority decisions. |
| [BOUNDARY_LAB_INTEGRATION_PLAN.md](BOUNDARY_LAB_INTEGRATION_PLAN.md) | Proposed Boundary Lab export / cross-check (not started). |
| [BL_LEARNINGS_IMPLEMENTATION.md](BL_LEARNINGS_IMPLEMENTATION.md) | Boundary Lab learnings implemented (mesh checks, phasor, provenance, SPDI). |
| [HIGH_FREQUENCY_OPTIONS.md](HIGH_FREQUENCY_OPTIONS.md) | Reaching 12 kHz on 8 GB: options and evidence. |
| [CLOUD_GPU_REPORT.md](CLOUD_GPU_REPORT.md) | Cloud GPU rental research. |
| [HANDOFF_LOCAL.md](HANDOFF_LOCAL.md), [HANDOFF.md](HANDOFF.md) | Older handoffs (CP-8, 6b test plan). Historical. |
| [SENIOR_REVIEW_2026-10-14.md](SENIOR_REVIEW_2026-10-14.md) | Surrogate-fix review. Historical. |

## Research
| Doc | What it is |
|---|---|
| [research/typologies/MESHER_TYPOLOGIES.md](research/typologies/MESHER_TYPOLOGIES.md) | What Magnus's mesher implements (OSSE, R-OSSE, ICW, FREEFORM, LOOKUP), file:line. |
| [research/typologies/SEARCH_LAYER_GAPS.md](research/typologies/SEARCH_LAYER_GAPS.md) | Search-layer coverage vs the mesher. |
| [research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md](research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md) | M4 grounding dossier (CITATION outcome): WP9 splice/throat_blend/spherical_salmon + WP9b per-azimuth Salmon rows + X-shape; C2 quarter/half symmetry basis; checkable properties; knob ranges; §5 carries the 2026-10-25 lecleach supersession note. |
| [research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md](research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md) | Le Cléac'h source verification (librarian, fetched): Fourcade 2015 PDF (eqs 10–27, 42–43, fig-7 reference case); the plan's included-vs-half angle bug found (phi0 = 4.0°); R9-J gate PASSED (width 0.00 mm) — lecleach live per the owner's 2026-10-25 directive. |
| [research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md](research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md) | JMLC-family variants research (lib-2, owner photo directive): fetched datasheets (E-JMLC-300/IWATA-300/JMLC-350); no published per-azimuth math exists — AR-stretch/torus/harmonic laws are labeled reconstructions; optimization conventions + knob surface. |
| [research/senior_pass_2026-10-24/](research/senior_pass_2026-10-24/README.md) | Senior pass 2026-10-24: objective/assumption audit, new typologies + multi-cell, 12 kHz routes, implementation plan (WP1–WP14). |
| [research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md](research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md) | **P6 IMPLEMENTATION PLAN v1.0** (rewritten from the research dossier, dossier content folded in): P6a superformula-family campaign (quarter-symmetry math, search box, degeneracy/curvature guards, configs, GPU + GUI) + P6b GSA-vs-CMA-ES bake-off (protocol, library audit → own ~120-line GSA, pre-registered decision rule) + parallel-lane structure with verbatim dispatch prompts. Owner-gated; runs after WP1–WP17 completes. Research basis in `plan/12_RESEARCH_BASIS.md` §11. |
| [research/TIME_DOMAIN_RINGING.md](research/TIME_DOMAIN_RINGING.md) | Ringing / waterfalls: what we can see, stage-2 design. |
| [BOUNDARY_LAB_0.5_RESEARCH.md](BOUNDARY_LAB_0.5_RESEARCH.md), [research/boundary_lab_0.5/](research/boundary_lab_0.5/) | Boundary Lab 0.5.0 findings and inventories. |

## Evidence (measured results; `evidence/README.md` explains the rules)
| Doc | What it is |
|---|---|
| [evidence/M6_WP12_2026-10-25.md](evidence/M6_WP12_2026-10-25.md) | WP12 enclosure mounting: brief.mounting → the mesher's OWN keys (plumbing + cache keys + all echoes; absent = byte-for-bit); measured on two finalists — dofs +199.4 % / +106.5 %, both under the UNCHANGED caps, J improves under the enclosure (different objective landscape — never rank across mountings), reference parity 2.91e-06 dB; focused 71/0/0; suite 1372/0/0/0; WP13 OWNER-DEFERRED; byte-check tools/evidence_bytecheck_m6.py 21/21. |
| [evidence/M5B_WP14_WP16_WP17_2026-10-25.md](evidence/M5B_WP14_WP16_WP17_2026-10-25.md) | M5B: WP14 multicell category (CAD→STEP route + solve keys + record honesty) + WP16 source plug + WP17 stage-1 fused-CUDA near correction — fork branches GPU-validated (Julia 46/46 incl. all four CUDA testsets; selftests 0.020/0.0390 dB; 3-arm A/B worst 4.94e-06 dB); fork HOSTED (github.com/llevaachingada/hornlab-beat-bem) + pin moved there → `test_mesh_pin` tripwire RESOLVED; suite **1325/0/0/0**; multicell physics DEFERRED (mouth-topology diagnosis + resume recipe inside); byte-check tools/evidence_bytecheck_m5b.py 33/33. |
| [evidence/M5_WP11_2026-10-25.md](evidence/M5_WP11_2026-10-25.md) | M5 WP11: restarts (IPOP/BIPOP mirroring pycma) + CMA-ME QD atlas (ribs 0.12.0; `archive.json`/`archive_heatmap.json` contract + read-only GUI atlas view); offline suite 1234/0/1/0 (intended tripwire; +40 additive) + 4 GPU screens proving budget exactness (fired run: 4 ES instances, BIPOP schedule visible, VRAM 430→2305 MiB [measured]); byte-check tools/evidence_bytecheck_m5.py 30/30. |
| [evidence/M4_SMOKE_2026-10-25.md](evidence/M4_SMOKE_2026-10-25.md) | M4 GPU smoke: 12 new-typology screens + conical reference (byte-checked verbatim logs; tools/evidence_bytecheck_m4.py); frozen-sculpt full-vs-quarter PASS (≤ 0.051° / 0.0043 dB vs the 0.1 dB/1° bar); WP10 zero-modulation compare honestly DIFFERENT (P-M4-1 proposal); final suite 1194/0/1/0 (intended tripwire only). |
| [evidence/SOLVER_VERIFY_2026-10-22.md](evidence/SOLVER_VERIFY_2026-10-22.md) | GPU tests, analytic sphere, GPU vs CPU cross-check. |
| [evidence/TYPOLOGY_VERIFY.md](evidence/TYPOLOGY_VERIFY.md) | Typology ladder V1–V5. |
| [evidence/TYPOLOGY_SCREEN_2026-10-22.md](evidence/TYPOLOGY_SCREEN_2026-10-22.md) | First fair screen campaigns + reading. Raw: `evidence/campaigns/`. |
| [evidence/BETA_READINESS.md](evidence/BETA_READINESS.md) | Beta pass audits (if present). |
| `evidence/TYPOLOGY_COMPARE_2026-10-23.md` | Compare tier (2 seeds): rankings that stand, bound-limited families, bound proposals. |
| [evidence/HANDOFF_6b.md](evidence/HANDOFF_6b.md), [evidence/BL_LEARNINGS_GPU.md](evidence/BL_LEARNINGS_GPU.md), [evidence/EARLY_REJECTION_REPLAY.md](evidence/EARLY_REJECTION_REPLAY.md) | FREEFORM sculpt tests; PR #15 GPU plan; early-rejection replay. |
| [evidence/CP-8a.md](evidence/CP-8a.md) … [CP-8d.md](evidence/CP-8d.md), `CP-8c_*.md` | CP-8 checkpoint outputs (dataset campaign, surrogate gates). |
| `evidence/runs/` + `manifest.sha256` | Summary layers of GPU runs (logs, not raw data). |
| `evidence/BETA_READINESS.md` | Beta readiness pass: SHAs/upstream, data integrity, physics audit (C2 epw 6 vs 8). |
| [evidence/OBJECTIVE_V2_RESCORE.md](evidence/OBJECTIVE_V2_RESCORE.md) | WP1 re-score: v1 vs v2 objective over 18,059 stored records; Spearman rho 0.989; both compare-tier claims survive; v1 drift 0. Per-record CSV local (regenerate with tools/rescore). |
| [evidence/HF12K_VERIFY_2026-10-23.md](evidence/HF12K_VERIFY_2026-10-23.md) | P2 12 kHz finalist verify pass: epw check at 12 kHz, beamwidth/DI to 12 kHz, VRAM; cross-mode caveat. |
| [evidence/CP-8d_retrain_2026-10-23.md](evidence/CP-8d_retrain_2026-10-23.md) | Surrogate retrain after the OSSE top-up: every gate vs threshold, held-out 463 < 500; model not used. |
| [evidence/FUSED_CUDA_2026-10-24.md](evidence/FUSED_CUDA_2026-10-24.md) | WP15 fused CUDA Burton-Miller (M2): analytic/cross-check/A-B ladders, flag-off determinism finding (1e-4 dB floor), VRAM ceiling → 12,000-dof caps; 12 kHz verify DONE on the flag. |
| [evidence/MEASUREMENT_PACK_2026-10-24.md](evidence/MEASUREMENT_PACK_2026-10-24.md) | M3 WP5/WP7/WP8 calibration on existing stored designs (17 GPU jobs, verbatim logs): distance 2/10/50 m from ONE traced solve, balloon 512→1035→2592, source_motion axial; WP7 rear_res_factor proposals 1.5/2.0 (owner-gated); WP8 band-split FAILS the CP-7f gate → no proposal; f11 = 7,914 Hz caveat printed at every 12 kHz number. |

## Elsewhere in the repo
`../README.md` (install, commands, known limits) · `../TOOLCHAIN.md` (pinned SHAs, measured machine numbers) ·
`../CONTRIBUTING.md` · `../NOTES_FOR_SENIOR.md` (append-only rulings and questions) · `../examples/catalog.yaml`.
